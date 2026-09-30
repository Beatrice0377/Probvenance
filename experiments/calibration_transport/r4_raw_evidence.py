"""R4 raw fixed-event evidence schema, fingerprint, and structural gates.

Research-only. This module defines the R4 raw-evidence artifact for one
``model x population`` measurement block under the frozen
``r4-fixed-event-two-forward-measurement`` contract: one CAT forward and one
designated-candidate-only OVR forward per item.

It deliberately does NOT modify or reuse the frozen R3 raw-evidence schema
(``r3_raw_evidence.py``): R3 stores four independent OVR candidate records per
item, R4 stores exactly one designated OVR record. Only the *shape* of the R4
artifact is defined here.

It fits no calibrator, computes no Brier/LogLoss/transport/predictor value, runs
no model, and reads no study row by itself. It stores raw CAT/OVR measurements
exactly as the frozen measurement layer produced them plus their provenance, and
checks structural completeness only.
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


_measurements = _load_sibling("measurements")
integrity = _load_sibling("integrity")

MeasurementStatus = integrity.MeasurementStatus

R4_RAW_EVIDENCE_ARTIFACT_TYPE = "r4-raw-fixed-event-measurement"
R4_RAW_EVIDENCE_ARTIFACT_VERSION = 1
R4_RAW_EVIDENCE_FINGERPRINT_VERSION = 1

#: The frozen R4 measurement call contract (see R4_MEASUREMENT_EXECUTION_CONTRACT.json).
MEASUREMENT_CALL_CONTRACT_ID = "r4-fixed-event-two-forward-measurement"
MEASUREMENT_CALL_CONTRACT_VERSION = 1
CAT_FORWARDS_PER_ITEM = 1
OVR_FORWARDS_PER_ITEM = 1
TOTAL_FORWARDS_PER_ITEM = 2
OVR_SCOPE = "designated-candidate-only"

R4_MEASUREMENT_EXECUTION_CONTRACT_PATH = (
    "experiments/calibration_transport/R4_MEASUREMENT_EXECUTION_CONTRACT.json"
)

#: Result/analysis vocabulary that must never appear inside a raw artifact.
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


class R4RawEvidenceError(ValueError):
    """A structural violation of the R4 raw-evidence contract."""


def _require_non_empty_str(value: object, *, field: str) -> str:
    if isinstance(value, bool) or not isinstance(value, str) or not value.strip():
        raise R4RawEvidenceError(f"{field} must be a non-empty str, got {value!r}")
    return value


def fixed_event_value(anchor: str, ground_truth_value: str) -> int:
    """``Y_i = 1[D_i = GT_i]`` computed from candidate identities only."""
    _require_non_empty_str(anchor, field="anchor")
    _require_non_empty_str(ground_truth_value, field="ground_truth_value")
    return 1 if anchor == ground_truth_value else 0


def _assert_no_result_fields(value: object, *, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            lowered = str(key).lower()
            for forbidden in FORBIDDEN_RESULT_FIELDS:
                if forbidden in lowered:
                    raise R4RawEvidenceError(
                        f"forbidden result/analysis field {key!r} at {path}; "
                        "raw evidence must never contain analysis vocabulary"
                    )
            _assert_no_result_fields(item, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _assert_no_result_fields(item, path=f"{path}[{index}]")


def scored_cat_block(
    *,
    record: Mapping[str, Any],
    source_record_id: str,
    top_token: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """The R4 scored CAT block (one CAT forward, four restricted label scores)."""
    anchor_score = float(record["anchor_score"])
    return {
        "status": MeasurementStatus.SCORED.value,
        "reason": None,
        "source_record_id": _require_non_empty_str(source_record_id, field="source_record_id"),
        "anchor_score": anchor_score,
        "record": dict(record),
        "top_token": dict(top_token) if top_token is not None else None,
    }


def scored_ovr_block(
    *,
    record: Mapping[str, Any],
    source_record_id: str,
    top_token: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """The R4 scored designated-only OVR block (exactly one candidate record)."""
    candidates = record.get("candidates")
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)):
        raise R4RawEvidenceError("OVR record must carry a candidates list")
    if len(candidates) != 1:
        raise R4RawEvidenceError(
            f"R4 designated-only OVR requires exactly one candidate record, got {len(candidates)}"
        )
    entry = candidates[0]
    if not isinstance(entry, Mapping):
        raise R4RawEvidenceError("OVR candidate record must be a mapping")
    probability_true = float(entry["probability_true"])
    positive = float(entry["positive_token_probability"])
    negative = float(entry["negative_token_probability"])
    mass = positive + negative
    if mass <= 0.0:
        raise R4RawEvidenceError("OVR verbalizer mass must be positive")
    probability_false = negative / mass
    return {
        "status": MeasurementStatus.SCORED.value,
        "reason": None,
        "source_record_id": _require_non_empty_str(source_record_id, field="source_record_id"),
        "designated_candidate": str(entry["candidate"]),
        "anchor_score": float(record["anchor_score"]),
        "probability_true": probability_true,
        "probability_false": probability_false,
        "positive_verbalizer_token_id": int(entry["positive_token_id"]),
        "negative_verbalizer_token_id": int(entry["negative_token_id"]),
        "record": dict(record),
        "top_token": dict(top_token) if top_token is not None else None,
    }


def unavailable_block(
    *,
    status: Any,
    reason: str,
    source_record_id: str,
) -> dict[str, Any]:
    """A declared missing/ineligible block (no silent success state)."""
    if status is MeasurementStatus.SCORED:
        raise R4RawEvidenceError("unavailable_block requires a non-scored status")
    if not isinstance(status, MeasurementStatus):
        raise R4RawEvidenceError(f"status must be a MeasurementStatus, got {type(status).__name__}")
    return {
        "status": status.value,
        "reason": _require_non_empty_str(reason, field="reason"),
        "source_record_id": _require_non_empty_str(source_record_id, field="source_record_id"),
        "anchor_score": None,
        "record": None,
        "top_token": None,
    }


def build_item_evidence(
    *,
    manifest_item: Mapping[str, Any],
    population_id: str,
    population_manifest_fingerprint: str,
    split: str,
    anchor: str,
    ground_truth_value: str,
    cat: Mapping[str, Any],
    ovr: Mapping[str, Any],
) -> dict[str, Any]:
    """Assemble one R4 row: frozen population identity + CAT + designated OVR."""
    item_id = _require_non_empty_str(manifest_item["item_id"], field="item_id")
    candidate_order = [str(name) for name in manifest_item["candidate_names"]]
    descriptions = [str(desc) for desc in manifest_item["candidate_descriptions"]]
    if anchor not in candidate_order:
        raise R4RawEvidenceError(f"anchor {anchor!r} is not in candidate_order {candidate_order}")
    if ground_truth_value not in candidate_order:
        raise R4RawEvidenceError(
            f"ground truth {ground_truth_value!r} is not in candidate_order {candidate_order}"
        )
    if str(ovr.get("designated_candidate", anchor)) != anchor:
        raise R4RawEvidenceError("OVR block designated_candidate must equal the frozen anchor D_i")
    return {
        "item_id": item_id,
        "population_id": _require_non_empty_str(population_id, field="population_id"),
        "population_manifest_fingerprint": _require_non_empty_str(
            population_manifest_fingerprint, field="population_manifest_fingerprint"
        ),
        "source_split": str(manifest_item["source_split"]),
        "source_row_index": int(manifest_item["source_row_index"]),
        "split": _require_non_empty_str(split, field="split"),
        "stratum": str(manifest_item["stratum"]),
        "group_id": manifest_item.get("group_id"),
        "anchor": anchor,
        "ground_truth_value": ground_truth_value,
        "fixed_event": fixed_event_value(anchor, ground_truth_value),
        "candidate_order": candidate_order,
        "candidates": [
            {"candidate": name, "choice": description}
            for name, description in zip(candidate_order, descriptions, strict=True)
        ],
        "cat": dict(cat),
        "ovr": dict(ovr),
    }


def structural_counts(items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Explicit per-block status counts (no silent success state)."""
    cat_counts = {status.value: 0 for status in MeasurementStatus}
    ovr_counts = {status.value: 0 for status in MeasurementStatus}
    for item in items:
        cat_counts[str(item["cat"]["status"])] += 1
        ovr_counts[str(item["ovr"]["status"])] += 1
    return {"items": len(items), "cat": cat_counts, "ovr": ovr_counts}


def paired_complete_block(items: Sequence[Mapping[str, Any]]) -> bool:
    """True iff every row is CAT=SCORED and OVR=SCORED (the consumption gate)."""
    scored = MeasurementStatus.SCORED.value
    return all(
        item["cat"]["status"] == scored and item["ovr"]["status"] == scored for item in items
    )


def canonical_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """The payload without its own ``evidence_fingerprint``."""
    return {key: value for key, value in payload.items() if key != "evidence_fingerprint"}


def evidence_fingerprint(payload: Mapping[str, Any]) -> str:
    return fingerprint(canonical_payload(payload))


def build_evidence_payload(
    *,
    model_key: str,
    model_id: str,
    model_revision: str,
    model_role: str,
    adapter: str,
    population_id: str,
    population_manifest_fingerprint: str,
    dataset_id: str,
    dataset_revision: str,
    train_budget: str,
    planned_train_rows: int,
    planned_test_rows: int,
    measurement_contract_fingerprint: str,
    final_protocol_candidate_fingerprint: str,
    execution_manifest_candidate_fingerprint: str,
    measurement_code_commit: str,
    runtime: Mapping[str, Any],
    items: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build the R4 raw-evidence artifact for one ``model x population`` block."""
    planned_rows = planned_train_rows + planned_test_rows
    payload: dict[str, Any] = {
        "artifact_type": R4_RAW_EVIDENCE_ARTIFACT_TYPE,
        "artifact_version": R4_RAW_EVIDENCE_ARTIFACT_VERSION,
        "fingerprint_version": R4_RAW_EVIDENCE_FINGERPRINT_VERSION,
        "measurement_call_contract": {
            "contract_id": MEASUREMENT_CALL_CONTRACT_ID,
            "contract_version": MEASUREMENT_CALL_CONTRACT_VERSION,
            "cat_forwards_per_item": CAT_FORWARDS_PER_ITEM,
            "ovr_forwards_per_item": OVR_FORWARDS_PER_ITEM,
            "total_forwards_per_item": TOTAL_FORWARDS_PER_ITEM,
            "ovr_scope": OVR_SCOPE,
        },
        "measurement_contract_fingerprint": _require_non_empty_str(
            measurement_contract_fingerprint, field="measurement_contract_fingerprint"
        ),
        "final_protocol_candidate_fingerprint": _require_non_empty_str(
            final_protocol_candidate_fingerprint, field="final_protocol_candidate_fingerprint"
        ),
        "execution_manifest_candidate_fingerprint": _require_non_empty_str(
            execution_manifest_candidate_fingerprint,
            field="execution_manifest_candidate_fingerprint",
        ),
        "measurement_code_commit": _require_non_empty_str(
            measurement_code_commit, field="measurement_code_commit"
        ),
        "model": {
            "model_key": model_key,
            "model_id": model_id,
            "model_revision": model_revision,
            "role": model_role,
            "adapter": adapter,
        },
        "population": {
            "population_id": population_id,
            "population_manifest_fingerprint": population_manifest_fingerprint,
            "dataset_id": dataset_id,
            "dataset_revision": dataset_revision,
            "train_budget": train_budget,
            "planned_train_rows": planned_train_rows,
            "planned_test_rows": planned_test_rows,
        },
        "runtime": dict(runtime),
        "planned": {
            "rows": planned_rows,
            "cat_forwards": planned_rows * CAT_FORWARDS_PER_ITEM,
            "ovr_forwards": planned_rows * OVR_FORWARDS_PER_ITEM,
            "total_forwards": planned_rows * TOTAL_FORWARDS_PER_ITEM,
        },
        "structural_counts": structural_counts(items),
        "paired_complete": paired_complete_block(items),
        "items": [dict(item) for item in items],
    }
    payload["evidence_fingerprint"] = evidence_fingerprint(payload)
    return payload


def _validate_cat_block(block: Mapping[str, Any], *, item_id: str) -> None:
    if block["status"] != MeasurementStatus.SCORED.value:
        return
    record = block["record"]
    probabilities = record["probabilities"]
    total = sum(float(value) for value in probabilities.values())
    if abs(total - 1.0) > 1e-6:
        raise R4RawEvidenceError(
            f"CAT restricted probabilities must sum to ~1 for {item_id}: {total}"
        )
    anchor = record["anchor"]
    if anchor not in probabilities:
        raise R4RawEvidenceError(f"CAT anchor {anchor!r} missing from probabilities for {item_id}")
    if abs(float(block["anchor_score"]) - float(probabilities[anchor])) > 1e-12:
        raise R4RawEvidenceError(f"CAT anchor_score mismatch for {item_id}")
    token_ids = record["resolved_token_ids"]
    if len(set(int(value) for value in token_ids.values())) != len(token_ids):
        raise R4RawEvidenceError(f"CAT label token ids must be distinct for {item_id}")


def _validate_ovr_block(block: Mapping[str, Any], *, item_id: str, anchor: str) -> None:
    if block["status"] != MeasurementStatus.SCORED.value:
        return
    if str(block["designated_candidate"]) != anchor:
        raise R4RawEvidenceError(f"OVR designated_candidate mismatch for {item_id}")
    record = block["record"]
    candidates = record["candidates"]
    if len(candidates) != 1:
        raise R4RawEvidenceError(
            f"R4 OVR must carry exactly one candidate record for {item_id}, got {len(candidates)}"
        )
    entry = candidates[0]
    if int(entry["positive_token_id"]) == int(entry["negative_token_id"]):
        raise R4RawEvidenceError(f"OVR yes/no token ids must differ for {item_id}")
    if abs(float(block["anchor_score"]) - float(entry["probability_true"])) > 1e-12:
        raise R4RawEvidenceError(f"OVR anchor_score mismatch for {item_id}")
    if abs(float(block["probability_true"]) + float(block["probability_false"]) - 1.0) > 1e-9:
        raise R4RawEvidenceError(
            f"OVR probability_true + probability_false must be ~1 for {item_id}"
        )


def validate_raw_evidence(
    payload: Mapping[str, Any],
    *,
    required_items: Sequence[Mapping[str, Any]],
    expected_contract_fingerprint: str,
    expected_model_key: str,
    expected_population_id: str,
) -> None:
    """Structural gates for one R4 raw-evidence artifact (no analysis)."""
    if payload.get("artifact_type") != R4_RAW_EVIDENCE_ARTIFACT_TYPE:
        raise R4RawEvidenceError(f"unexpected artifact_type {payload.get('artifact_type')!r}")
    if payload.get("artifact_version") != R4_RAW_EVIDENCE_ARTIFACT_VERSION:
        raise R4RawEvidenceError(f"unexpected artifact_version {payload.get('artifact_version')!r}")
    if payload.get("fingerprint_version") != R4_RAW_EVIDENCE_FINGERPRINT_VERSION:
        raise R4RawEvidenceError(
            f"unexpected fingerprint_version {payload.get('fingerprint_version')!r}"
        )
    if payload.get("measurement_contract_fingerprint") != expected_contract_fingerprint:
        raise R4RawEvidenceError("measurement_contract_fingerprint mismatch")
    if payload["model"]["model_key"] != expected_model_key:
        raise R4RawEvidenceError("model_key mismatch")
    if payload["population"]["population_id"] != expected_population_id:
        raise R4RawEvidenceError("population_id mismatch")
    _assert_no_result_fields(payload)

    items = payload["items"]
    expected_ids = [str(item["item_id"]) for item in required_items]
    actual_ids = [str(item["item_id"]) for item in items]
    if actual_ids != expected_ids:
        raise R4RawEvidenceError("item set/order must equal the required frozen row order")
    if len(actual_ids) != len(set(actual_ids)):
        raise R4RawEvidenceError("duplicate item_id in raw evidence")

    by_id = {str(item["item_id"]): item for item in required_items}
    for item in items:
        item_id = str(item["item_id"])
        source = by_id[item_id]
        if str(item["anchor"]) != str(source["candidate_names"][int(source["anchor_index"])]):
            raise R4RawEvidenceError(
                f"anchor must equal the frozen anchor_index candidate for {item_id}"
            )
        expected_gt = str(source["candidate_names"][int(source["ground_truth_index"])])
        if str(item["ground_truth_value"]) != expected_gt:
            raise R4RawEvidenceError(f"ground_truth_value mismatch for {item_id}")
        recomputed = fixed_event_value(str(item["anchor"]), str(item["ground_truth_value"]))
        if int(item["fixed_event"]) != recomputed:
            raise R4RawEvidenceError(f"fixed_event mismatch for {item_id}")
        _validate_cat_block(item["cat"], item_id=item_id)
        _validate_ovr_block(item["ovr"], item_id=item_id, anchor=str(item["anchor"]))

    if structural_counts(items) != payload["structural_counts"]:
        raise R4RawEvidenceError("structural_counts do not match the items")
    if paired_complete_block(items) != payload["paired_complete"]:
        raise R4RawEvidenceError("paired_complete does not match the items")
    if evidence_fingerprint(payload) != payload.get("evidence_fingerprint"):
        raise R4RawEvidenceError("evidence_fingerprint mismatch")


def write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    """Write canonical R4 raw evidence (no NaN, stable key order)."""
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
    Path(path).write_text(text + "\n", encoding="utf-8")
