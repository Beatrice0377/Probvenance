"""Orchestrate the R2B stability / deconfounding round (research-only).

Fixed pipeline, no branching on outcomes:

1. build the frozen 150-item plan (pre-declared 6/4-per-cell split + anchors),
2. record the run provenance and FAIL CLOSED if the git working tree is dirty,
3. construct exactly one local backend (offline, pinned revision),
4. run 150 CAT evaluations and 450 OVR evaluations (600 total),
5. build the exact R1 paired dataset,
6. write the raw evidence artifact,
7. run the pre-declared stability analysis and write the analysis artifact.

There is no retry with an altered protocol, no model fallback, no lambda sweep,
no split change, and no anchor change. ``--plan-only`` prints the frozen plan
without touching a model or the git working tree.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from probvenance import Probvenance

_HARNESS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _HARNESS_DIR.parents[1]


def _load_sibling(name: str) -> Any:
    module = sys.modules.get(name)
    if module is not None:
        return module
    spec = importlib.util.spec_from_file_location(name, _HARNESS_DIR / f"{name}.py")
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load {name}.py from {_HARNESS_DIR}")
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


r2b_plan = _load_sibling("r2b_plan")
r2b_provenance = _load_sibling("r2b_provenance")
r2b_stability = _load_sibling("r2b_stability")
run_pilot = _load_sibling("run_pilot")
pilot_plan = run_pilot.pilot_plan
_integrity = run_pilot._integrity
PairedFixedDecisionDataset = _integrity.PairedFixedDecisionDataset

DEFAULT_MODEL = "Qwen/Qwen3.5-2B"
PINNED_MODEL_REVISION = "15852e8c16360a2fea060d615a32b45270f8a8fc"
DEFAULT_DTYPE = "bfloat16"
DEFAULT_RENDERING_CONFIG: dict[str, Any] = {"enable_thinking": False}
DEFAULT_TAG = "r2b-stability-qwen35-2b-v1"

RAW_ARTIFACT_TYPE = "calibration-transport-r2b-stability-raw"
R2B_RAW_ARTIFACT_VERSION = 1


def _run_cases_by_id(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Build the runner-facing case objects (question, context, candidates)."""
    question = str(payload["question"])
    candidates = r2b_plan.candidate_set(payload)
    return {
        case.item_id: pilot_plan.PilotCase(
            case_id=case.item_id,
            question=question,
            context=case.context,
            candidates=candidates,
        )
        for case in r2b_plan.r2b_cases(payload)
    }


def _resolved_device(backend: Any) -> str:
    explicit = getattr(backend, "device", None)
    if isinstance(explicit, str) and explicit:
        return explicit
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:  # pragma: no cover - defensive
        return "unknown"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--revision", default=PINNED_MODEL_REVISION)
    parser.add_argument("--dtype", default=DEFAULT_DTYPE)
    parser.add_argument("--device", default=None)
    parser.add_argument("--cases", default=str(r2b_plan.DEFAULT_CASES_PATH))
    parser.add_argument("--out-dir", default=str(_HARNESS_DIR / "results"))
    parser.add_argument("--tag", default=DEFAULT_TAG)
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="build and print the frozen plan without loading any model",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.revision:
        raise SystemExit("frozen R2B run requires an explicit --revision (never an unpinned main)")
    payload = r2b_plan.load_case_set(args.cases)
    case_set_fingerprint = r2b_plan.case_set_fingerprint(payload)
    plan = r2b_plan.build_plan(payload, model_id=args.model, model_revision=args.revision)

    if args.plan_only:
        print(
            json.dumps(
                {
                    "plan_fingerprint": plan.fingerprint,
                    "source_case_set_fingerprint": case_set_fingerprint,
                    "planned_n": len(plan.items),
                    "train_n": sum(1 for i in plan.items if i.split.value == "train"),
                    "test_n": sum(1 for i in plan.items if i.split.value == "test"),
                    "items": [
                        {
                            "item_id": item.item_id,
                            "split": item.split.value,
                            "anchor": item.anchor_value,
                            "ground_truth": item.ground_truth_value,
                            "anchor_correct": item.anchor_correct,
                        }
                        for item in plan.items
                    ],
                },
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                allow_nan=False,
            )
        )
        return 0

    git_commit, worktree_clean = r2b_provenance.git_code_provenance(_REPO_ROOT)
    if not worktree_clean:
        raise SystemExit(
            "R2B official measurement requires a clean git working tree before the first score"
        )
    provenance = r2b_provenance.build_r2b_run_provenance(
        source_case_set_version=r2b_plan.R2B_CASE_SET_VERSION,
        source_case_set_fingerprint=case_set_fingerprint,
        plan=plan,
        git_commit=git_commit,
        git_worktree_clean=True,
    )

    model_meta = {
        "model": args.model,
        "revision": args.revision,
        "dtype": args.dtype,
        "rendering_config": dict(DEFAULT_RENDERING_CONFIG),
    }
    backend = run_pilot.load_backend(args.model, args.revision, args.dtype, args.device)
    runtime = Probvenance(backend=backend, capture_rendered_input=True)
    cases_by_id = _run_cases_by_id(payload)

    started = time.time()
    cat_records, ovr_records, outcomes_a, outcomes_b = run_pilot.run_measurements(
        runtime, plan, cases_by_id, model_meta=model_meta
    )
    duration_s = time.time() - started

    dataset = PairedFixedDecisionDataset.create(plan, outcomes_a, outcomes_b)

    out_dir = Path(args.out_dir)
    raw_path = out_dir / f"{args.tag}.json"
    run_pilot._write_json(
        raw_path,
        {
            "artifact_type": RAW_ARTIFACT_TYPE,
            "artifact_version": R2B_RAW_ARTIFACT_VERSION,
            "research_spec_id": _integrity.RESEARCH_SPEC_ID,
            "research_spec_version": _integrity.RESEARCH_SPEC_VERSION,
            "source_case_set_version": r2b_plan.R2B_CASE_SET_VERSION,
            "source_case_set_fingerprint": case_set_fingerprint,
            "r2b_run_provenance_canonical_payload": provenance.canonical_payload(),
            "r2b_run_provenance_fingerprint": provenance.fingerprint,
            "pre_measurement_git_commit": git_commit,
            "git_worktree_clean": worktree_clean,
            "library_runtime": r2b_provenance.library_runtime_provenance(),
            "model_configuration": {
                "model": args.model,
                "revision": args.revision,
                "dtype": args.dtype,
                "requested_device": args.device or "auto",
                "resolved_device": _resolved_device(backend),
                "local_files_only": True,
            },
            "rendering_configuration": dict(DEFAULT_RENDERING_CONFIG),
            "evaluation_count": len(cat_records)
            + sum(len(record["candidates"]) for record in ovr_records),
            "duration_s": round(duration_s, 3),
            "plan_canonical_payload": plan.canonical_payload(),
            "plan_fingerprint": plan.fingerprint,
            "cat_raw_records": cat_records,
            "ovr_raw_records": ovr_records,
            "paired_dataset_canonical_payload": dataset.canonical_payload(),
            "paired_dataset_fingerprint": dataset.fingerprint,
        },
    )

    stratum_by_item = {case.item_id: case.stratum for case in r2b_plan.r2b_cases(payload)}
    artifact = r2b_stability.build_r2b_analysis_artifact(
        plan=plan,
        dataset=dataset,
        stratum_by_item=stratum_by_item,
        case_set_version=r2b_plan.R2B_CASE_SET_VERSION,
        case_set_fingerprint=case_set_fingerprint,
        run_provenance=provenance,
        cat_records=cat_records,
        ovr_records=ovr_records,
        outcomes_a=outcomes_a,
        outcomes_b=outcomes_b,
    )
    run_pilot._write_json(out_dir / f"{args.tag}-analysis.json", artifact)

    print(f"wrote {raw_path} and analysis artifact", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
