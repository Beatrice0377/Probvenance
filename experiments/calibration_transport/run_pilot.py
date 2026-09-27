"""Orchestrate the R2 minimal frozen-decision CAT/OVR transport pilot.

Fixed pipeline, no branching on outcomes:

1. build the frozen plan (pre-declared split + hash anchors + declared truth),
2. construct exactly one local backend,
3. run 15 CAT evaluations and 45 OVR evaluations (60 total),
4. build the exact R1 paired dataset,
5. write the raw evidence artifact,
6. run the pre-declared exploratory analysis,
7. write the analysis artifact.

There is no retry with an altered protocol, no model fallback, no lambda sweep,
no split change, and no anchor change. ``--plan-only`` prints the frozen plan
without touching a model.
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


pilot_plan = _load_sibling("pilot_plan")
measurements = _load_sibling("measurements")
analysis = _load_sibling("analysis")
_integrity = pilot_plan._integrity
Split = _integrity.Split
MeasurementStatus = _integrity.MeasurementStatus
MeasurementOutcome = _integrity.MeasurementOutcome
PairedFixedDecisionDataset = _integrity.PairedFixedDecisionDataset

DEFAULT_MODEL = "Qwen/Qwen3.5-2B"
# Exact commit the first empirical pilot is frozen at. The previous environment
# failure resolved ``main`` to this commit before any measurement ran, so the
# pilot pins it and never silently follows a newer ``main``. ``model_revision``
# is part of plan identity: pinning changes the plan fingerprint as a value
# change, not an R1 schema change.
PINNED_MODEL_REVISION = "15852e8c16360a2fea060d615a32b45270f8a8fc"
DEFAULT_DTYPE = "bfloat16"
DEFAULT_RENDERING_CONFIG: dict[str, Any] = {"enable_thinking": False}
DEFAULT_TAG = "frozen-decision-cat-ovr-qwen35-2b"

RAW_ARTIFACT_TYPE = "calibration-transport-frozen-decision-pilot-raw"
PILOT_ARTIFACT_VERSION = 1


def load_backend(model: str, revision: str | None, dtype: str, device: str | None) -> Any:
    """Load the experiment-side Qwen3.5 text-tower backend, offline at a pinned revision."""
    loader_path = _HARNESS_DIR.parent / "semantic_signal" / "qwen35_loader.py"
    spec = importlib.util.spec_from_file_location("qwen35_loader", loader_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load qwen35_loader.py from {loader_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["qwen35_loader"] = module
    spec.loader.exec_module(module)
    return module.Qwen35TextBackend(
        model=model,
        revision=revision,
        dtype=dtype,
        device=device,
        local_files_only=True,
        chat_template_kwargs=DEFAULT_RENDERING_CONFIG,
    )


def _ineligible_outcome(item_id: str, protocol: str, status: Any, reason: str) -> Any:
    return MeasurementOutcome(
        item_id=item_id,
        status=status,
        anchor_score=None,
        winner_value=None,
        source_record_id=measurements.failure_source_record_id(
            protocol=protocol, item_id=item_id, status=status, reason=reason
        ),
        reason=reason,
    )


def run_measurements(
    runtime: Probvenance,
    plan: Any,
    cases_by_id: Mapping[str, Any],
    *,
    model_meta: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], tuple[Any, ...], tuple[Any, ...]]:
    """Run every planned CAT and OVR measurement and translate to R1 outcomes."""
    cat_records: list[dict[str, Any]] = []
    ovr_records: list[dict[str, Any]] = []
    outcomes_a: list[Any] = []
    outcomes_b: list[Any] = []

    for item in plan.items:
        case = cases_by_id[item.item_id]

        try:
            cat_evaluation = runtime.evaluate_with_trace(
                measurements.build_cat_decision(case.question, case.context, case.candidates)
            )
            cat_record = measurements.build_cat_raw_record(
                cat_evaluation,
                case_id=case.case_id,
                item_id=item.item_id,
                anchor=item.anchor_value,
                model_meta=model_meta,
            )
        except Exception as exc:  # classified below, else re-raised
            classified = measurements.classify_measurement_exception(exc)
            if classified is None:
                raise
            status, reason = classified
            outcomes_a.append(
                _ineligible_outcome(item.item_id, measurements.CAT_MEASUREMENT_ID, status, reason)
            )
        else:
            cat_records.append(cat_record)
            outcomes_a.append(measurements.cat_outcome(cat_record))

        candidate_order = [name for name, _description in case.candidates]
        evaluations: dict[str, Any] = {}
        failure: tuple[Any, str] | None = None
        for name, description in case.candidates:
            try:
                proposition = measurements.build_ovr_proposition(
                    case.question, case.context, name, description
                )
                evaluations[name] = runtime.evaluate_with_trace(proposition)
            except Exception as exc:  # classified below, else re-raised
                classified = measurements.classify_measurement_exception(exc)
                if classified is None:
                    raise
                failure = classified
                break

        if failure is None and len(evaluations) == len(candidate_order):
            ovr_record = measurements.build_ovr_raw_record(
                case_id=case.case_id,
                item_id=item.item_id,
                anchor=item.anchor_value,
                candidate_order=candidate_order,
                evaluations=evaluations,
                model_meta=model_meta,
            )
            ovr_records.append(ovr_record)
            outcomes_b.append(measurements.ovr_outcome(ovr_record))
        else:
            status, reason = (
                failure
                if failure is not None
                else (
                    MeasurementStatus.MISSING,
                    "not every candidate produced an independent binary judgment",
                )
            )
            outcomes_b.append(
                _ineligible_outcome(item.item_id, measurements.OVR_MEASUREMENT_ID, status, reason)
            )

    return cat_records, ovr_records, tuple(outcomes_a), tuple(outcomes_b)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
    path.write_text(text + "\n", encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--revision", default=PINNED_MODEL_REVISION)
    parser.add_argument("--dtype", default=DEFAULT_DTYPE)
    parser.add_argument("--device", default=None)
    parser.add_argument("--cases", default=str(pilot_plan.DEFAULT_CASES_PATH))
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
        raise SystemExit("frozen pilot requires an explicit --revision (never an unpinned main)")
    payload = pilot_plan.load_case_set(args.cases)
    case_set_fingerprint = pilot_plan.case_set_fingerprint(payload)
    cases = pilot_plan.pilot_cases(payload)
    cases_by_id = {case.case_id: case for case in cases}
    plan = pilot_plan.build_plan(payload, model_id=args.model, model_revision=args.revision)

    if args.plan_only:
        print(
            json.dumps(
                {
                    "plan_fingerprint": plan.fingerprint,
                    "source_case_set_fingerprint": case_set_fingerprint,
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

    model_meta = {
        "model": args.model,
        "revision": args.revision,
        "dtype": args.dtype,
        "rendering_config": dict(DEFAULT_RENDERING_CONFIG),
    }
    backend = load_backend(args.model, args.revision, args.dtype, args.device)
    runtime = Probvenance(backend=backend, capture_rendered_input=True)

    started = time.time()
    cat_records, ovr_records, outcomes_a, outcomes_b = run_measurements(
        runtime, plan, cases_by_id, model_meta=model_meta
    )
    duration_s = time.time() - started

    dataset = PairedFixedDecisionDataset.create(plan, outcomes_a, outcomes_b)

    out_dir = Path(args.out_dir)
    raw_path = out_dir / f"{args.tag}.json"
    _write_json(
        raw_path,
        {
            "artifact_type": RAW_ARTIFACT_TYPE,
            "artifact_version": PILOT_ARTIFACT_VERSION,
            "research_spec_id": _integrity.RESEARCH_SPEC_ID,
            "research_spec_version": _integrity.RESEARCH_SPEC_VERSION,
            "source_case_set_version": pilot_plan.CASE_SET_VERSION,
            "source_case_set_fingerprint": case_set_fingerprint,
            "model_configuration": {
                "model": args.model,
                "revision": args.revision,
                "dtype": args.dtype,
                "device": args.device or "auto",
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

    artifact = analysis.build_analysis_artifact(
        plan=plan,
        dataset=dataset,
        case_set_fingerprint=case_set_fingerprint,
        cat_records=cat_records,
        ovr_records=ovr_records,
        outcomes_a=outcomes_a,
        outcomes_b=outcomes_b,
    )
    _write_json(out_dir / f"{args.tag}-analysis.json", artifact)

    print(f"wrote {raw_path} and analysis artifact", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
