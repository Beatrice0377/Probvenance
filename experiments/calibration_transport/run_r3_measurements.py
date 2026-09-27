"""Official R3 raw confirmatory measurement runner (protocol-frozen).

Collects, for ONE declared model condition, exactly:

    1596 manifest items x (1 CAT + 4 OVR) = 7980 model evaluations

offline at the exact frozen revision, and writes ONE raw-evidence artifact.
It fits no calibrator and computes no confirmatory metric: Brier, LogLoss,
risk, contrasts, bootstrap, and adequacy states are strictly forbidden here.
The frozen procedure panel lives in ``r3_analysis`` and is deliberately never
imported by this module.

Scientific configuration is NOT exposed on the command line. The model id,
revision, dtype, rendering, population, measurement protocols, and plan all
come from the frozen R3 protocol; the only CLI is which declared condition to
run and where to write the raw artifact.
"""

from __future__ import annotations

import argparse
import importlib.metadata as importlib_metadata
import importlib.util
import os
import platform
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from probvenance import Probvenance
from probvenance.backends.transformers import TransformersBackend

_HARNESS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _HARNESS_DIR.parents[1]


def _load_sibling(name: str) -> Any:
    """Load a sibling harness module idempotently (stable class identity)."""
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


r3_population = _load_sibling("r3_population")
r3_protocol = _load_sibling("r3_protocol")
pilot_plan = _load_sibling("pilot_plan")
measurements = _load_sibling("measurements")
r3_raw_evidence = _load_sibling("r3_raw_evidence")
_integrity = pilot_plan._integrity
MeasurementStatus = _integrity.MeasurementStatus
MeasurementOutcome = _integrity.MeasurementOutcome
PairedFixedDecisionDataset = _integrity.PairedFixedDecisionDataset

#: Successful operational-preflight environment. Any drift STOPs before the
#: first official forward and is reported for human review.
EXPECTED_PYTHON_MAJOR_MINOR = "3.11"
EXPECTED_TORCH_VERSION = "2.14.0+cu130"
EXPECTED_CUDA_RUNTIME = "13.0"
EXPECTED_GPU_NAME = "NVIDIA GeForce RTX 5060 Laptop GPU"
EXPECTED_TRANSFORMERS_VERSION = "5.17.0"
EXPECTED_HUGGINGFACE_HUB_VERSION = "1.32.0"
EXPECTED_DTYPE = "bfloat16"

_REQUIRED_TRUE_OFFLINE_FLAGS = ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")
_REQUIRED_SET_OFFLINE_FLAGS = ("HF_DATASETS_OFFLINE",)


class GateError(RuntimeError):
    """Raised when a mandatory fail-closed startup gate fails."""


class EnvironmentDriftError(GateError):
    """Raised when the runtime environment no longer matches preflight."""


class AnchorMismatchError(GateError):
    """Raised when the frozen plan disagrees with the frozen manifest anchor/truth."""


# --------------------------------------------------------------------------- #
# Fail-closed startup gates
# --------------------------------------------------------------------------- #


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def verify_git_state() -> dict[str, str]:
    """Require branch == main and a clean working tree before any forward."""
    branch = _git("branch", "--show-current")
    if branch != "main":
        raise GateError(f"official R3 run requires branch 'main', found {branch!r}")
    status = _git("status", "--porcelain")
    if status:
        raise GateError(f"official R3 run requires a clean working tree:\n{status}")
    return {"branch": branch, "measurement_code_commit": _git("rev-parse", "HEAD")}


def _dist_version(name: str) -> str:
    try:
        return importlib_metadata.version(name)
    except importlib_metadata.PackageNotFoundError:  # pragma: no cover - defensive
        return "not_installed"


def verify_environment(*, dtype: str) -> dict[str, Any]:
    """Require the runtime to match the successful operational preflight exactly."""
    import torch

    observed = {
        "python_version": platform.python_version(),
        "python_major_minor": ".".join(platform.python_version().split(".")[:2]),
        "torch_version": torch.__version__,
        "torch_cuda_version": torch.version.cuda,
        "transformers_version": _dist_version("transformers"),
        "huggingface_hub_version": _dist_version("huggingface_hub"),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "dtype": dtype,
    }
    expected = {
        "python_major_minor": EXPECTED_PYTHON_MAJOR_MINOR,
        "torch_version": EXPECTED_TORCH_VERSION,
        "torch_cuda_version": EXPECTED_CUDA_RUNTIME,
        "transformers_version": EXPECTED_TRANSFORMERS_VERSION,
        "huggingface_hub_version": EXPECTED_HUGGINGFACE_HUB_VERSION,
        "gpu_name": EXPECTED_GPU_NAME,
        "dtype": EXPECTED_DTYPE,
    }
    drift = {
        field: (expected[field], observed[field])
        for field in expected
        if observed[field] != expected[field]
    }
    if drift:
        raise EnvironmentDriftError(
            "runtime environment drifted from the frozen preflight environment; "
            f"STOP FOR HUMAN REVIEW: {drift}"
        )
    if not torch.cuda.is_available():
        raise GateError("CUDA must be available for the official R3 run")
    return observed


def verify_offline_environment() -> dict[str, str]:
    for flag in _REQUIRED_TRUE_OFFLINE_FLAGS:
        if os.environ.get(flag) != "1":
            raise GateError(f"offline flag {flag} must be set to '1' before any official forward")
    for flag in _REQUIRED_SET_OFFLINE_FLAGS:
        if not os.environ.get(flag):
            raise GateError(f"offline flag {flag} must be set before any official forward")
    return {
        flag: os.environ.get(flag, "")
        for flag in (*_REQUIRED_TRUE_OFFLINE_FLAGS, *_REQUIRED_SET_OFFLINE_FLAGS)
    }


def _config_commit_hash(model: str, revision: str) -> str | None:
    from transformers import AutoConfig

    try:
        config = AutoConfig.from_pretrained(
            model, revision=revision, local_files_only=True, trust_remote_code=False
        )
    except Exception:  # pragma: no cover - provenance best-effort, never invents a value
        return None
    return getattr(config, "_commit_hash", None)


def _tokenizer_commit_hash(model: str, revision: str) -> str | None:
    from transformers import AutoTokenizer

    try:
        tokenizer = AutoTokenizer.from_pretrained(
            model, revision=revision, local_files_only=True, trust_remote_code=False
        )
    except Exception:  # pragma: no cover - provenance best-effort, never invents a value
        return None
    return getattr(tokenizer, "_commit_hash", None)


def resolve_condition(design: Mapping[str, Any], condition: str) -> Mapping[str, Any]:
    """Resolve ``primary``/``replication`` to the exact frozen model identity."""
    models = design.get("models", {})
    if condition not in models:
        raise GateError(f"unknown R3 condition {condition!r}; expected one of {sorted(models)}")
    entry = models[condition]
    if not entry.get("model_id") or not entry.get("model_revision"):
        raise GateError(f"R3 condition {condition!r} lacks a fully pinned model identity")
    return entry


def verify_frozen_identities(
    *,
    design: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> dict[str, str]:
    protocol_fingerprint = r3_protocol.protocol_fingerprint(design)
    if protocol_fingerprint != design.get("protocol_fingerprint"):
        raise GateError("R3 protocol fingerprint does not match the frozen design")
    manifest_fingerprint = r3_population.manifest_fingerprint(manifest)
    if manifest_fingerprint != manifest.get("manifest_fingerprint"):
        raise GateError("R3 population manifest fingerprint does not match its content")
    if manifest.get("counts", {}).get("total") != r3_raw_evidence.EXPECTED_ITEMS_PER_MODEL:
        raise GateError("R3 population manifest item count does not match the frozen protocol")
    return {
        "protocol_fingerprint": protocol_fingerprint,
        "population_manifest_fingerprint": manifest_fingerprint,
    }


def verify_anchors(
    plan: Any,
    manifest_by_id: Mapping[str, Mapping[str, Any]],
) -> None:
    """Verify the frozen plan's anchors/truth against manifest recomputation."""
    for item in plan.items:
        manifest_item = manifest_by_id[item.item_id]
        recomputed_anchor = pilot_plan.select_anchor(
            item.item_id, list(r3_raw_evidence.R3_CANDIDATE_NAMES)
        )
        if item.anchor_value != recomputed_anchor:
            raise AnchorMismatchError(
                f"item {item.item_id} anchor {item.anchor_value!r} != recomputed "
                f"{recomputed_anchor!r}; STOP BEFORE SCORING"
            )
        expected_truth = f"option-{manifest_item['answer_index']}"
        if item.ground_truth_value != expected_truth:
            raise AnchorMismatchError(
                f"item {item.item_id} ground truth {item.ground_truth_value!r} != "
                f"{expected_truth!r} from the manifest; STOP BEFORE SCORING"
            )
        if bool(item.anchor_correct) != (item.anchor_value == expected_truth):
            raise AnchorMismatchError(
                f"item {item.item_id} anchor_correct disagrees with anchor vs truth; "
                "STOP BEFORE SCORING"
            )


# --------------------------------------------------------------------------- #
# Backend
# --------------------------------------------------------------------------- #


def load_backend(condition: str, model_id: str, revision: str, *, device: str | None) -> Any:
    """Construct exactly one local backend for the declared condition (offline)."""
    rendering = {"enable_thinking": False}
    if condition == r3_raw_evidence.MODEL_CONDITION_REPLICATION:
        loader_path = _HARNESS_DIR.parent / "semantic_signal" / "qwen35_loader.py"
        spec = importlib.util.spec_from_file_location("qwen35_loader", loader_path)
        if spec is None or spec.loader is None:  # pragma: no cover - defensive
            raise ImportError(f"cannot load qwen35_loader.py from {loader_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules["qwen35_loader"] = module
        spec.loader.exec_module(module)
        return module.Qwen35TextBackend(
            model=model_id,
            revision=revision,
            dtype=EXPECTED_DTYPE,
            device=device,
            local_files_only=True,
            chat_template_kwargs=rendering,
        )
    return TransformersBackend(
        model_id,
        revision=revision,
        device=device,
        dtype=EXPECTED_DTYPE,
        trust_remote_code=False,
        local_files_only=True,
        chat_template_kwargs=rendering,
    )


# --------------------------------------------------------------------------- #
# Measurement
# --------------------------------------------------------------------------- #


def _top_token(evaluation: Any) -> dict[str, Any]:
    diagnostics = evaluation.trace.scoring_diagnostics
    return {
        "token_id": int(diagnostics.top_token_id),
        "probability": float(diagnostics.top_token_probability),
        "text": diagnostics.top_token_text,
    }


def _unavailable_outcome(item_id: str, protocol: str, status: Any, reason: str) -> Any:
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


def measure_item(
    runtime: Probvenance,
    *,
    manifest_item: Mapping[str, Any],
    plan_item: Any,
    model_meta: Mapping[str, Any],
) -> tuple[dict[str, Any], Any, Any]:
    """Evaluate exactly one CAT and four independent OVR judgments for one item."""
    item_id = plan_item.item_id
    question = manifest_item["question"]
    candidates = r3_population.candidate_set(manifest_item)
    candidate_order = [name for name, _description in candidates]

    cat_outcome: Any
    try:
        cat_evaluation = runtime.evaluate_with_trace(
            measurements.build_cat_decision(question, None, candidates)
        )
        cat_record = measurements.build_cat_raw_record(
            cat_evaluation,
            case_id=item_id,
            item_id=item_id,
            anchor=plan_item.anchor_value,
            model_meta=model_meta,
        )
    except Exception as exc:  # classified below, else re-raised
        classified = measurements.classify_measurement_exception(exc)
        if classified is None:
            raise
        status, reason = classified
        cat_outcome = _unavailable_outcome(item_id, measurements.CAT_MEASUREMENT_ID, status, reason)
        cat_block = r3_raw_evidence.unavailable_block(
            status=status, reason=reason, source_record_id=cat_outcome.source_record_id
        )
    else:
        cat_outcome = measurements.cat_outcome(cat_record)
        cat_block = r3_raw_evidence.scored_cat_block(
            record=cat_record,
            source_record_id=cat_outcome.source_record_id,
            top_token=_top_token(cat_evaluation),
        )

    # Always attempt all four independent OVR judgments: the official call count
    # is deterministic (one CAT + four OVR per item) regardless of item outcome.
    evaluations: dict[str, Any] = {}
    top_tokens: dict[str, Any] = {}
    ovr_failure: tuple[Any, str] | None = None
    for name, description in candidates:
        try:
            proposition = measurements.build_ovr_proposition(question, None, name, description)
            evaluation = runtime.evaluate_with_trace(proposition)
        except Exception as exc:  # classified below, else re-raised
            classified = measurements.classify_measurement_exception(exc)
            if classified is None:
                raise
            if ovr_failure is None:
                ovr_failure = classified
            continue
        evaluations[name] = evaluation
        top_tokens[name] = _top_token(evaluation)

    if ovr_failure is None and len(evaluations) == len(candidate_order):
        ovr_record = measurements.build_ovr_raw_record(
            case_id=item_id,
            item_id=item_id,
            anchor=plan_item.anchor_value,
            candidate_order=candidate_order,
            evaluations=evaluations,
            model_meta=model_meta,
        )
        ovr_outcome = measurements.ovr_outcome(ovr_record)
        candidate_scores = {
            entry["candidate"]: float(entry["probability_true"])
            for entry in ovr_record["candidates"]
        }
        ovr_block = r3_raw_evidence.scored_ovr_block(
            record=ovr_record,
            source_record_id=ovr_outcome.source_record_id,
            candidate_scores=candidate_scores,
            top_tokens=top_tokens,
        )
    else:
        status, reason = (
            ovr_failure
            if ovr_failure is not None
            else (
                MeasurementStatus.MISSING,
                "not every candidate produced an independent binary judgment",
            )
        )
        ovr_outcome = _unavailable_outcome(item_id, measurements.OVR_MEASUREMENT_ID, status, reason)
        ovr_block = r3_raw_evidence.unavailable_block(
            status=status, reason=reason, source_record_id=ovr_outcome.source_record_id
        )

    evidence = r3_raw_evidence.build_item_evidence(
        manifest_item=manifest_item,
        anchor=plan_item.anchor_value,
        ground_truth_value=plan_item.ground_truth_value,
        anchor_correct=plan_item.anchor_correct,
        cat=cat_block,
        ovr=ovr_block,
    )
    return evidence, cat_outcome, ovr_outcome


def run_condition(
    runtime: Probvenance,
    plan: Any,
    manifest_by_id: Mapping[str, Mapping[str, Any]],
    *,
    model_meta: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], tuple[Any, ...], tuple[Any, ...]]:
    """Run every planned item's CAT and OVR measurements, in frozen order."""
    items: list[dict[str, Any]] = []
    outcomes_a: list[Any] = []
    outcomes_b: list[Any] = []
    for plan_item in plan.items:
        evidence, cat_outcome, ovr_outcome = measure_item(
            runtime,
            manifest_item=manifest_by_id[plan_item.item_id],
            plan_item=plan_item,
            model_meta=model_meta,
        )
        items.append(evidence)
        outcomes_a.append(cat_outcome)
        outcomes_b.append(ovr_outcome)
    return items, tuple(outcomes_a), tuple(outcomes_b)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--condition", required=True, choices=list(r3_raw_evidence.MODEL_CONDITIONS)
    )
    parser.add_argument(
        "--output", required=True, help="external staging path for the raw artifact"
    )
    parser.add_argument("--device", default=None, help="operational device override (default cuda)")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    design = r3_protocol.load_design()
    manifest = r3_population.load_manifest()
    identities = verify_frozen_identities(design=design, manifest=manifest)
    git_state = verify_git_state()
    environment = verify_environment(dtype=EXPECTED_DTYPE)
    offline = verify_offline_environment()

    condition = args.condition
    model = resolve_condition(design, condition)
    model_id = str(model["model_id"])
    model_revision = str(model["model_revision"])
    model_role = str(model["role"])
    runtime_config = design["runtime"]

    manifest_by_id = {item["item_id"]: item for item in r3_population.manifest_items(manifest)}
    plan = r3_protocol.build_child_plan(manifest, model_id=model_id, model_revision=model_revision)
    if plan.fingerprint != model["child_plan_fingerprint"]:
        raise GateError(
            "recomputed child plan fingerprint does not match the frozen protocol "
            f"({plan.fingerprint!r} != {model['child_plan_fingerprint']!r})"
        )
    verify_anchors(plan, manifest_by_id)

    model_meta = {
        "model": model_id,
        "revision": model_revision,
        "dtype": runtime_config["dtype"],
        "rendering_config": dict(runtime_config["rendering"]),
    }

    backend = load_backend(condition, model_id, model_revision, device=args.device)
    runtime = Probvenance(backend=backend, capture_rendered_input=True)

    started = time.time()
    items, outcomes_a, outcomes_b = run_condition(
        runtime, plan, manifest_by_id, model_meta=model_meta
    )
    duration_s = time.time() - started

    dataset = PairedFixedDecisionDataset.create(plan, outcomes_a, outcomes_b)

    runtime_provenance = {
        "dtype": runtime_config["dtype"],
        "device": args.device or "cuda",
        "rendering": dict(runtime_config["rendering"]),
        "local_files_only": True,
        "hf_hub_offline": offline["HF_HUB_OFFLINE"],
        "transformers_offline": offline["TRANSFORMERS_OFFLINE"],
        "hf_datasets_offline": offline["HF_DATASETS_OFFLINE"],
    }
    execution_provenance = {
        "python_version": environment["python_version"],
        "torch_version": environment["torch_version"],
        "torch_cuda_version": environment["torch_cuda_version"],
        "transformers_version": environment["transformers_version"],
        "huggingface_hub_version": environment["huggingface_hub_version"],
        "gpu_name": environment["gpu_name"],
        "dtype": runtime_config["dtype"],
        "device": args.device or "cuda",
        "local_files_only": True,
        "requested_model": model_id,
        "requested_revision": model_revision,
        "model_config_commit_hash": _config_commit_hash(model_id, model_revision),
        "tokenizer_commit_hash": _tokenizer_commit_hash(model_id, model_revision),
    }

    payload = r3_raw_evidence.build_evidence_payload(
        model_condition=condition,
        model_role=model_role,
        model_id=model_id,
        model_revision=model_revision,
        child_plan_fingerprint=plan.fingerprint,
        r3_protocol_fingerprint=identities["protocol_fingerprint"],
        population_manifest_fingerprint=identities["population_manifest_fingerprint"],
        measurement_code_commit=git_state["measurement_code_commit"],
        runtime=runtime_provenance,
        execution_provenance=execution_provenance,
        paired_dataset_fingerprint=dataset.fingerprint,
        items=items,
    )
    r3_raw_evidence.validate_raw_evidence(
        payload,
        manifest=manifest,
        plan=plan,
        expected_protocol_fingerprint=identities["protocol_fingerprint"],
    )
    output_path = r3_raw_evidence.write_json(args.output, payload)
    counts = payload["structural_counts"]
    total_evaluations = counts["cat"]["scored"] + sum(
        counts["ovr"][status] * len(r3_raw_evidence.R3_CANDIDATE_NAMES) for status in counts["ovr"]
    )
    print(
        f"condition={condition} model={model_id}@{model_revision} "
        f"items={counts['items']} cat_scored={counts['cat']['scored']} "
        f"ovr_scored={counts['ovr']['scored']} logical_evaluations={total_evaluations} "
        f"duration_s={duration_s:.1f} output={output_path}",
        file=sys.stderr,
    )
    print(f"evidence_fingerprint={payload['evidence_fingerprint']}", file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
