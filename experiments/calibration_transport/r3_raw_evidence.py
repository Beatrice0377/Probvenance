"""R3 raw confirmatory evidence schema, fingerprint, and structural gates.

Research-only. This module defines the frozen raw-evidence artifact for the R3
official measurement round (R3.1) and the structural gates that verify it.

It fits no calibrator and computes no confirmatory statistic. It stores the raw
CAT/OVR measurements exactly as the frozen measurement layer produced them,
together with their provenance, and checks structural completeness only. The
frozen procedure panel, risk baselines, contrasts, and bootstrap live in
``r3_analysis`` and must never be invoked from the measurement path.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from probvenance.fingerprint import fingerprint

_HARNESS_DIR = Path(__file__).resolve().parent


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


_r3_population = _load_sibling("r3_population")
_measurements = _load_sibling("measurements")
integrity = _load_sibling("integrity")

R3_CANDIDATE_NAMES: tuple[str, ...] = _r3_population.R3_CANDIDATE_NAMES

#: Human-readable condition names == keys of r3_protocol_design.json["models"].
MODEL_CONDITION_PRIMARY = "primary"
MODEL_CONDITION_REPLICATION = "replication"
MODEL_CONDITIONS: tuple[str, ...] = (MODEL_CONDITION_PRIMARY, MODEL_CONDITION_REPLICATION)

R3_RAW_EVIDENCE_ARTIFACT_TYPE = "r3-raw-confirmatory-measurement"
R3_RAW_EVIDENCE_ARTIFACT_VERSION = 1
R3_RAW_EVIDENCE_FINGERPRINT_VERSION = 1

R3_RAW_EVIDENCE_INDEX_ARTIFACT_TYPE = "r3-raw-evidence-index"
R3_RAW_EVIDENCE_INDEX_VERSION = 1
R3_RAW_EVIDENCE_INDEX_FINGERPRINT_VERSION = 1

R3_RESEARCH_SPEC_ID = "calibration-transport-research-spec"
R3_RESEARCH_SPEC_VERSION = 2

#: The R3 protocol *semantic* commit (frozen before any outcome). Distinct from
#: the measurement-code commit and the later analysis commit; both are recorded.
R3_PROTOCOL_SEMANTIC_COMMIT = "12f602a9527f0db4b1575abe6999235a40d55ef6"

EXPECTED_ITEMS_PER_MODEL = _r3_population.DEFAULT_TOTAL
EXPECTED_CAT_EVALUATIONS = EXPECTED_ITEMS_PER_MODEL
EXPECTED_OVR_EVALUATIONS = EXPECTED_ITEMS_PER_MODEL * len(R3_CANDIDATE_NAMES)
EXPECTED_TOTAL_EVALUATIONS = EXPECTED_CAT_EVALUATIONS + EXPECTED_OVR_EVALUATIONS

#: Result-analysis field names that must NEVER appear as keys in raw evidence.
FORBIDDEN_RESULT_FIELDS: tuple[str, ...] = (
    "brier",
    "log_loss",
    "logloss",
    "delta",
    "native_risk",
    "cross_risk",
    "feature_effect",
    "regularization_effect",
    "interaction",
    "bootstrap",
    "confidence_interval",
    "native_adequacy",
)

_SCORED = integrity.MeasurementStatus.SCORED
_STATUS_ORDER: tuple[str, ...] = tuple(status.value for status in integrity.MeasurementStatus)
_STATUS_VALUES = frozenset(_STATUS_ORDER)


class RawEvidenceError(ValueError):
    """Raised when raw R3 evidence violates its frozen structural contract."""


# --------------------------------------------------------------------------- #
# Item-level evidence
# --------------------------------------------------------------------------- #


def _candidate_pairs(manifest_item: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    return _r3_population.candidate_set(manifest_item)


def build_item_evidence(
    *,
    manifest_item: Mapping[str, Any],
    anchor: str,
    ground_truth_value: str,
    anchor_correct: bool,
    cat: Mapping[str, Any],
    ovr: Mapping[str, Any],
) -> dict[str, Any]:
    """Assemble one item's raw evidence from the frozen measurement outputs.

    ``cat`` and ``ovr`` are blocks of the form
    ``{"status", "reason", "source_record_id", "record", "top_token"}`` where
    ``record`` is the verbatim ``measurements.build_*_raw_record`` output (or
    ``None`` when the status is not SCORED).
    """
    return {
        "item_id": manifest_item["item_id"],
        "subject": manifest_item["subject"],
        "split": manifest_item["split"],
        "source_split": manifest_item["source_split"],
        "source_row_index": manifest_item["source_row_index"],
        "anchor": anchor,
        "ground_truth_value": ground_truth_value,
        "anchor_correct": bool(anchor_correct),
        "candidate_order": list(R3_CANDIDATE_NAMES),
        "candidates": [
            {"candidate": name, "choice": description}
            for name, description in _candidate_pairs(manifest_item)
        ],
        "cat": dict(cat),
        "ovr": dict(ovr),
    }


def scored_cat_block(
    *,
    record: Mapping[str, Any],
    source_record_id: str,
    top_token: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "status": _SCORED.value,
        "reason": None,
        "source_record_id": source_record_id,
        "record": dict(record),
        "top_token": dict(top_token) if top_token is not None else None,
    }


def scored_ovr_block(
    *,
    record: Mapping[str, Any],
    source_record_id: str,
    candidate_scores: Mapping[str, float],
    top_tokens: Mapping[str, Mapping[str, Any] | None],
) -> dict[str, Any]:
    return {
        "status": _SCORED.value,
        "reason": None,
        "source_record_id": source_record_id,
        "record": dict(record),
        "candidate_scores": {name: float(value) for name, value in candidate_scores.items()},
        "top_tokens": {
            name: (dict(value) if value is not None else None) for name, value in top_tokens.items()
        },
    }


def unavailable_block(*, status: Any, reason: str, source_record_id: str) -> dict[str, Any]:
    """A structurally preserved MISSING/INELIGIBLE block (never a substitute row)."""
    return {
        "status": status.value,
        "reason": reason,
        "source_record_id": source_record_id,
        "record": None,
        "top_token": None,
        "candidate_scores": None,
        "top_tokens": None,
    }


# --------------------------------------------------------------------------- #
# Structural counts
# --------------------------------------------------------------------------- #


def structural_counts(items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    cat_counts = dict.fromkeys(_STATUS_ORDER, 0)
    ovr_counts = dict.fromkeys(_STATUS_ORDER, 0)
    for item in items:
        cat_counts[item["cat"]["status"]] += 1
        ovr_counts[item["ovr"]["status"]] += 1
    return {
        "items": len(items),
        "cat": cat_counts,
        "ovr": ovr_counts,
    }


# --------------------------------------------------------------------------- #
# Payload + fingerprint
# --------------------------------------------------------------------------- #


def canonical_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """The evidence payload without its own fingerprint (the committed content)."""
    return {key: value for key, value in payload.items() if key != "evidence_fingerprint"}


def evidence_fingerprint(payload: Mapping[str, Any]) -> str:
    return fingerprint(canonical_payload(payload))


def build_evidence_payload(
    *,
    model_condition: str,
    model_role: str,
    model_id: str,
    model_revision: str,
    child_plan_fingerprint: str,
    r3_protocol_fingerprint: str,
    population_manifest_fingerprint: str,
    measurement_code_commit: str,
    runtime: Mapping[str, Any],
    execution_provenance: Mapping[str, Any],
    paired_dataset_fingerprint: str,
    items: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build the canonical raw-evidence payload for ONE declared model condition.

    No timestamp, no wall-clock duration, and no machine-local cache path enter
    the payload or its fingerprint (the immutable revision is the portable
    identity).
    """
    payload: dict[str, Any] = {
        "artifact_type": R3_RAW_EVIDENCE_ARTIFACT_TYPE,
        "artifact_version": R3_RAW_EVIDENCE_ARTIFACT_VERSION,
        "fingerprint_version": R3_RAW_EVIDENCE_FINGERPRINT_VERSION,
        "research_spec": {
            "id": R3_RESEARCH_SPEC_ID,
            "version": R3_RESEARCH_SPEC_VERSION,
        },
        "r3_protocol_fingerprint": r3_protocol_fingerprint,
        "r3_protocol_git_commit": R3_PROTOCOL_SEMANTIC_COMMIT,
        "measurement_code_commit": measurement_code_commit,
        "population": {
            "manifest_fingerprint": population_manifest_fingerprint,
            "population_id": _r3_population.R3_POPULATION_ID,
            "population_version": _r3_population.R3_POPULATION_VERSION,
            "dataset_repository": _r3_population.MMLU_REPOSITORY,
            "dataset_revision": _r3_population.MMLU_REVISION,
        },
        "model_condition": {
            "condition": model_condition,
            "role": model_role,
            "model_id": model_id,
            "model_revision": model_revision,
            "child_plan_fingerprint": child_plan_fingerprint,
        },
        "runtime": dict(runtime),
        "execution_provenance": dict(execution_provenance),
        "measurement_identities": _measurement_identities(),
        "expected": {
            "items": EXPECTED_ITEMS_PER_MODEL,
            "cat_evaluations": EXPECTED_CAT_EVALUATIONS,
            "ovr_evaluations": EXPECTED_OVR_EVALUATIONS,
            "total_evaluations": EXPECTED_TOTAL_EVALUATIONS,
        },
        "structural_counts": structural_counts(items),
        "paired_dataset_fingerprint": paired_dataset_fingerprint,
        "items": [dict(item) for item in items],
    }
    payload["evidence_fingerprint"] = evidence_fingerprint(payload)
    return payload


def _measurement_identities() -> dict[str, Any]:
    return {
        "cat": {
            "measurement_id": _measurements.CAT_MEASUREMENT_ID,
            "measurement_version": _measurements.CAT_MEASUREMENT_VERSION,
        },
        "ovr": {
            "measurement_id": _measurements.OVR_MEASUREMENT_ID,
            "measurement_version": _measurements.OVR_MEASUREMENT_VERSION,
        },
        "ovr_proposition": {
            "proposition_id": _measurements.OVR_PROPOSITION_ID,
            "proposition_version": _measurements.OVR_PROPOSITION_VERSION,
        },
        "anchor": {
            "anchor_selection_id": "sha256-case-id-candidate-set-anchor",
            "anchor_selection_version": 1,
        },
        "target": {
            "id": integrity.FIXED_DECISION_TARGET_ID,
            "version": integrity.FIXED_DECISION_TARGET_VERSION,
        },
        "input_score": {
            "id": integrity.FIXED_DECISION_INPUT_SCORE_ID,
            "version": integrity.FIXED_DECISION_INPUT_SCORE_VERSION,
        },
    }


# --------------------------------------------------------------------------- #
# Structural validation (fail closed) — NO confirmatory metric is computed
# --------------------------------------------------------------------------- #


def _iter_keys(node: Any):
    if isinstance(node, Mapping):
        for key, value in node.items():
            yield key
            yield from _iter_keys(value)
    elif isinstance(node, (list, tuple)):
        for entry in node:
            yield from _iter_keys(entry)


def _require_finite_probability(value: Any, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RawEvidenceError(f"{field} must be a number, got {type(value).__name__}")
    number = float(value)
    if not (0.0 <= number <= 1.0):
        raise RawEvidenceError(f"{field} must lie in [0,1], got {number!r}")
    return number


def assert_no_result_fields(payload: Mapping[str, Any]) -> None:
    """No confirmatory result field may appear as a key anywhere in the payload."""
    for key in _iter_keys(payload):
        lowered = str(key).lower()
        if lowered in FORBIDDEN_RESULT_FIELDS:
            raise RawEvidenceError(f"raw evidence contains forbidden result field {key!r}")


def validate_raw_evidence(
    payload: Mapping[str, Any],
    *,
    manifest: Mapping[str, Any],
    plan: Any,
    expected_protocol_fingerprint: str,
) -> None:
    """Validate raw R3 evidence against every frozen structural gate.

    Structural linkage and completeness only: this never computes Brier,
    LogLoss, accuracy, risk, a contrast, or a bootstrap interval.
    """
    if payload.get("artifact_type") != R3_RAW_EVIDENCE_ARTIFACT_TYPE:
        raise RawEvidenceError("raw evidence artifact_type mismatch")
    if payload.get("artifact_version") != R3_RAW_EVIDENCE_ARTIFACT_VERSION:
        raise RawEvidenceError("raw evidence artifact_version mismatch")
    if payload.get("fingerprint_version") != R3_RAW_EVIDENCE_FINGERPRINT_VERSION:
        raise RawEvidenceError("raw evidence fingerprint_version mismatch")
    if payload.get("r3_protocol_fingerprint") != expected_protocol_fingerprint:
        raise RawEvidenceError("raw evidence r3_protocol_fingerprint mismatch")
    population = payload.get("population", {})
    if population.get("manifest_fingerprint") != manifest.get("manifest_fingerprint"):
        raise RawEvidenceError("raw evidence population manifest fingerprint mismatch")

    assert_no_result_fields(payload)

    manifest_items = _r3_population.manifest_items(manifest)
    manifest_by_id = {item["item_id"]: item for item in manifest_items}
    manifest_order = [item["item_id"] for item in manifest_items]
    plan_by_id = {item.item_id: item for item in plan.items}
    if set(plan_by_id) != set(manifest_by_id):
        raise RawEvidenceError("plan item set does not equal the frozen manifest item set")

    items = list(payload.get("items", []))
    if len(items) != len(manifest_items):
        raise RawEvidenceError(
            f"raw evidence has {len(items)} items, expected {len(manifest_items)}"
        )
    seen: set[str] = set()
    for position, item in enumerate(items):
        item_id = item.get("item_id")
        if item_id in seen:
            raise RawEvidenceError(f"duplicate item id {item_id}")
        seen.add(item_id)
        if item_id not in manifest_by_id:
            raise RawEvidenceError(f"unexpected item id {item_id}")
        if manifest_order[position] != item_id:
            raise RawEvidenceError(
                f"item order must follow the frozen manifest order at position {position}"
            )
        _validate_item(
            item,
            manifest_item=manifest_by_id[item_id],
            plan_item=plan_by_id[item_id],
        )
    if seen != set(manifest_by_id):
        raise RawEvidenceError("raw evidence item id coverage does not match the manifest")

    expected_counts = structural_counts(items)
    if payload.get("structural_counts") != expected_counts:
        raise RawEvidenceError("declared structural_counts disagree with the item records")

    if payload.get("evidence_fingerprint") != evidence_fingerprint(payload):
        raise RawEvidenceError("raw evidence fingerprint does not match its content")


def _validate_item(
    item: Mapping[str, Any],
    *,
    manifest_item: Mapping[str, Any],
    plan_item: Any,
) -> None:
    item_id = item["item_id"]
    for field in ("subject", "split", "source_split", "source_row_index"):
        if item.get(field) != manifest_item[field]:
            raise RawEvidenceError(f"item {item_id} field {field} disagrees with the manifest")
    if item.get("candidate_order") != list(R3_CANDIDATE_NAMES):
        raise RawEvidenceError(f"item {item_id} candidate_order is not the frozen candidate set")
    expected_candidates = [
        {"candidate": name, "choice": description}
        for name, description in _candidate_pairs(manifest_item)
    ]
    if item.get("candidates") != expected_candidates:
        raise RawEvidenceError(f"item {item_id} candidates disagree with the manifest choices")

    ground_truth_value = f"option-{manifest_item['answer_index']}"
    if item.get("anchor") != plan_item.anchor_value:
        raise RawEvidenceError(f"item {item_id} anchor disagrees with the frozen plan")
    if item.get("ground_truth_value") != ground_truth_value:
        raise RawEvidenceError(f"item {item_id} ground truth disagrees with the manifest")
    if item.get("ground_truth_value") != plan_item.ground_truth_value:
        raise RawEvidenceError(f"item {item_id} ground truth disagrees with the frozen plan")
    if bool(item.get("anchor_correct")) != bool(plan_item.anchor_correct):
        raise RawEvidenceError(f"item {item_id} anchor_correct disagrees with the frozen plan")

    _validate_cat(item, item_id=item_id)
    _validate_ovr(item, item_id=item_id)


def _validate_cat(item: Mapping[str, Any], *, item_id: str) -> None:
    block = item.get("cat")
    if not isinstance(block, Mapping):
        raise RawEvidenceError(f"item {item_id} lacks a cat block")
    status = block.get("status")
    if status not in _STATUS_VALUES:
        raise RawEvidenceError(f"item {item_id} cat status {status!r} is not a frozen status")
    if not isinstance(block.get("source_record_id"), str) or not block["source_record_id"]:
        raise RawEvidenceError(f"item {item_id} cat source_record_id is missing")
    if status != _SCORED.value:
        if block.get("record") is not None:
            raise RawEvidenceError(f"item {item_id} non-scored cat must not carry a record")
        return
    record = block.get("record")
    if not isinstance(record, Mapping):
        raise RawEvidenceError(f"item {item_id} scored cat lacks its raw record")
    if record.get("item_id") != item_id:
        raise RawEvidenceError(f"item {item_id} cat record item_id mismatch")
    probabilities = record.get("probabilities")
    if not isinstance(probabilities, Mapping) or set(probabilities) != set(R3_CANDIDATE_NAMES):
        raise RawEvidenceError(f"item {item_id} cat probabilities must cover the candidate set")
    total = 0.0
    for name in R3_CANDIDATE_NAMES:
        total += _require_finite_probability(
            probabilities[name], field=f"item {item_id} cat probability {name}"
        )
    if abs(total - 1.0) > 1e-6:
        raise RawEvidenceError(f"item {item_id} cat probabilities sum to {total!r}, not 1")
    anchor_score = _require_finite_probability(
        record.get("anchor_score"), field=f"item {item_id} cat anchor_score"
    )
    if anchor_score != float(probabilities[item["anchor"]]):
        raise RawEvidenceError(f"item {item_id} cat anchor_score != probabilities[anchor]")
    if record.get("winner") not in R3_CANDIDATE_NAMES:
        raise RawEvidenceError(f"item {item_id} cat winner is not a candidate")
    for linkage in (
        "trace_id",
        "decision_fingerprint",
        "plan_fingerprint",
        "execution_fingerprint",
    ):
        if not record.get(linkage):
            raise RawEvidenceError(f"item {item_id} cat record lacks {linkage}")
    if not record.get("resolved_token_ids"):
        raise RawEvidenceError(f"item {item_id} cat record lacks resolved_token_ids")


def _validate_ovr(item: Mapping[str, Any], *, item_id: str) -> None:
    block = item.get("ovr")
    if not isinstance(block, Mapping):
        raise RawEvidenceError(f"item {item_id} lacks an ovr block")
    status = block.get("status")
    if status not in _STATUS_VALUES:
        raise RawEvidenceError(f"item {item_id} ovr status {status!r} is not a frozen status")
    if not isinstance(block.get("source_record_id"), str) or not block["source_record_id"]:
        raise RawEvidenceError(f"item {item_id} ovr source_record_id is missing")
    if status != _SCORED.value:
        if block.get("record") is not None:
            raise RawEvidenceError(f"item {item_id} non-scored ovr must not carry a record")
        return
    record = block.get("record")
    if not isinstance(record, Mapping):
        raise RawEvidenceError(f"item {item_id} scored ovr lacks its raw record")
    if record.get("item_id") != item_id:
        raise RawEvidenceError(f"item {item_id} ovr record item_id mismatch")
    candidates = record.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != len(R3_CANDIDATE_NAMES):
        raise RawEvidenceError(
            f"item {item_id} ovr must carry exactly {len(R3_CANDIDATE_NAMES)} candidate records"
        )
    observed_order = [entry.get("candidate") for entry in candidates]
    if observed_order != list(R3_CANDIDATE_NAMES):
        raise RawEvidenceError(f"item {item_id} ovr candidate order mismatch")
    candidate_scores: dict[str, float] = {}
    for entry in candidates:
        name = entry["candidate"]
        candidate_scores[name] = _require_finite_probability(
            entry.get("probability_true"), field=f"item {item_id} ovr {name} probability_true"
        )
        for token_field in ("positive_token_id", "negative_token_id"):
            token_id = entry.get(token_field)
            if isinstance(token_id, bool) or not isinstance(token_id, int):
                raise RawEvidenceError(f"item {item_id} ovr {name} lacks {token_field}")
        for probability_field in (
            "positive_token_probability",
            "negative_token_probability",
            "verbalizer_mass",
        ):
            _require_finite_probability(
                entry.get(probability_field),
                field=f"item {item_id} ovr {name} {probability_field}",
            )
    if block.get("candidate_scores") != candidate_scores:
        raise RawEvidenceError(f"item {item_id} ovr candidate_scores disagree with the record")
    anchor_score = _require_finite_probability(
        record.get("anchor_score"), field=f"item {item_id} ovr anchor_score"
    )
    if anchor_score != candidate_scores[item["anchor"]]:
        raise RawEvidenceError(f"item {item_id} ovr anchor_score != candidate_scores[anchor]")
    if record.get("winner") not in R3_CANDIDATE_NAMES:
        raise RawEvidenceError(f"item {item_id} ovr winner is not a candidate")


# --------------------------------------------------------------------------- #
# Raw-evidence index
# --------------------------------------------------------------------------- #


def index_canonical_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "index_fingerprint"}


def index_fingerprint(payload: Mapping[str, Any]) -> str:
    return fingerprint(index_canonical_payload(payload))


def build_evidence_index(
    *,
    r3_protocol_fingerprint: str,
    population_manifest_fingerprint: str,
    measurement_code_commit: str,
    conditions: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Lineage/completeness metadata only: no probabilities, no metric, no verdict."""
    normalized = {name: dict(entry) for name, entry in conditions.items()}
    complete = all(
        name in normalized
        and normalized[name].get("actual_item_count") == EXPECTED_ITEMS_PER_MODEL
        and normalized[name].get("structurally_complete") is True
        for name in MODEL_CONDITIONS
    )
    payload: dict[str, Any] = {
        "artifact_type": R3_RAW_EVIDENCE_INDEX_ARTIFACT_TYPE,
        "artifact_version": R3_RAW_EVIDENCE_INDEX_VERSION,
        "fingerprint_version": R3_RAW_EVIDENCE_INDEX_FINGERPRINT_VERSION,
        "r3_protocol_fingerprint": r3_protocol_fingerprint,
        "population_manifest_fingerprint": population_manifest_fingerprint,
        "measurement_code_commit": measurement_code_commit,
        "conditions": normalized,
        "all_declared_conditions_complete": complete,
    }
    payload["index_fingerprint"] = index_fingerprint(payload)
    return payload


# --------------------------------------------------------------------------- #
# Persistence
# --------------------------------------------------------------------------- #


def write_json(path: str | Path, payload: Mapping[str, Any]) -> Path:
    """Canonical UTF-8 JSON: sorted keys, stable order, no NaN, trailing newline."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
    target.write_text(text + "\n", encoding="utf-8")
    return target
