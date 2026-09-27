"""Offline tests for the R3 raw-evidence schema and structural gates.

No model, no GPU, no network. These tests build synthetic raw evidence, drive
it through the frozen structural gates, and lock the endpoint-preservation,
no-substitution, forbidden-field, and index contracts. No confirmatory metric
is computed anywhere in this module.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

HARNESS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = HARNESS_DIR.parents[1]
SRC = REPO_ROOT / "src"

for path in (str(SRC), str(HARNESS_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)


def _load(name: str) -> Any:
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, HARNESS_DIR / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


pilot_plan = _load("pilot_plan")
r3_population = _load("r3_population")
r3_raw_evidence = _load("r3_raw_evidence")
_integrity = pilot_plan._integrity
Split = _integrity.Split

PROTOCOL_FP = "3ef63056ae16b18ad65d9c87d1fbec5b43550873a0e3e25ec0a323f954ee974d"
CANDIDATES = list(r3_raw_evidence.R3_CANDIDATE_NAMES)


def _manifest_item(
    item_id: str, *, split: str, answer_index: int = 2, row: int = 0
) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "subject": "abstract_algebra",
        "split": split,
        "source_split": "validation" if split == "TRAIN" else "test",
        "source_row_index": row,
        "question": f"Question for {item_id}?",
        "choices": ["alpha", "beta", "gamma", "delta"],
        "answer_index": answer_index,
    }


def _manifest(items: list[dict[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "artifact_type": r3_population.R3_POPULATION_MANIFEST_ARTIFACT_TYPE,
        "artifact_version": r3_population.R3_POPULATION_MANIFEST_VERSION,
        "fingerprint_version": r3_population.R3_POPULATION_MANIFEST_FINGERPRINT_VERSION,
        "population_id": r3_population.R3_POPULATION_ID,
        "population_version": r3_population.R3_POPULATION_VERSION,
        "subject_count": 1,
        "items": items,
    }
    payload["manifest_fingerprint"] = r3_population.manifest_fingerprint(payload)
    return payload


def _plan(items: list[dict[str, Any]]) -> Any:
    plan_items = tuple(
        _integrity.PlannedFixedDecisionItem(
            item_id=item["item_id"],
            split=Split(item["split"].lower()),
            anchor_value="option-0",
            ground_truth_value=f"option-{item['answer_index']}",
            anchor_correct=(f"option-{item['answer_index']}" == "option-0"),
        )
        for item in items
    )
    return _integrity.PairedFixedDecisionPlan(
        model_id="synthetic-model",
        model_revision="0" * 40,
        population_id="synthetic-population",
        population_version=1,
        ground_truth_semantics_fingerprint="a" * 64,
        ground_truth_semantics_fingerprint_version=1,
        measurement_a=_integrity.MeasurementProtocolIdentity("synthetic-cat", 1),
        measurement_b=_integrity.MeasurementProtocolIdentity("synthetic-ovr", 1),
        anchor_selection_id="synthetic-anchor",
        anchor_selection_version=1,
        split_protocol_id="synthetic-split",
        split_protocol_version=1,
        items=plan_items,
    )


def _cat_record(item_id: str, anchor: str, probabilities: dict[str, float]) -> dict[str, Any]:
    return {
        "protocol": "direct-categorical-anchor-probability",
        "protocol_version": 1,
        "case_id": item_id,
        "item_id": item_id,
        "anchor": anchor,
        "anchor_score": float(probabilities[anchor]),
        "winner": CANDIDATES[1],
        "probabilities": {name: float(value) for name, value in probabilities.items()},
        "scoring_label_mass": 1.0,
        "scoring_label_token_probabilities": [0.25, 0.25, 0.25, 0.25],
        "resolved_token_ids": {"A": 1, "B": 2, "C": 3, "D": 4},
        "decision_fingerprint": "d" * 64,
        "plan_fingerprint": "p" * 64,
        "execution_fingerprint": "e" * 64,
        "trace_id": "t" * 64,
    }


def _ovr_record(item_id: str, anchor: str, scores: dict[str, float]) -> dict[str, Any]:
    return {
        "protocol": "independent-binary-anchor-probability",
        "protocol_version": 1,
        "proposition_id": "choice-candidate-correctness-binary-judgment",
        "proposition_version": 1,
        "case_id": item_id,
        "item_id": item_id,
        "anchor": anchor,
        "anchor_score": float(scores[anchor]),
        "winner": CANDIDATES[0],
        "candidate_score_sum": sum(scores.values()),
        "candidates": [
            {
                "candidate": name,
                "probability_true": float(scores[name]),
                "probability_true_ge_half": scores[name] >= 0.5,
                "verbalizer_mass": 0.9,
                "positive_token_probability": 0.7,
                "negative_token_probability": 0.2,
                "positive_token_id": 10,
                "negative_token_id": 20,
                "decision_fingerprint": "d" * 64,
                "plan_fingerprint": "p" * 64,
                "execution_fingerprint": "e" * 64,
                "trace_id": "t" * 64,
            }
            for name in CANDIDATES
        ],
    }


def _scored_evidence(
    manifest_item: dict[str, Any],
    *,
    cat_probabilities: dict[str, float] | None = None,
    ovr_scores: dict[str, float] | None = None,
) -> dict[str, Any]:
    item_id = manifest_item["item_id"]
    anchor = "option-0"
    probabilities = cat_probabilities or dict(zip(CANDIDATES, (0.7, 0.1, 0.1, 0.1), strict=True))
    scores = ovr_scores or dict(zip(CANDIDATES, (0.6, 0.4, 0.3, 0.2), strict=True))
    cat_record = _cat_record(item_id, anchor, probabilities)
    ovr_record = _ovr_record(item_id, anchor, scores)
    return r3_raw_evidence.build_item_evidence(
        manifest_item=manifest_item,
        anchor=anchor,
        ground_truth_value=f"option-{manifest_item['answer_index']}",
        anchor_correct=(anchor == f"option-{manifest_item['answer_index']}"),
        cat=r3_raw_evidence.scored_cat_block(
            record=cat_record,
            source_record_id="c" * 64,
            top_token={"token_id": 1, "probability": 0.9, "text": "A"},
        ),
        ovr=r3_raw_evidence.scored_ovr_block(
            record=ovr_record,
            source_record_id="o" * 64,
            candidate_scores=scores,
            top_tokens={name: None for name in CANDIDATES},
        ),
    )


def _payload(
    manifest: dict[str, Any], items: list[dict[str, Any]], **overrides: Any
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model_condition": "primary",
        "model_role": "primary-confirmatory",
        "model_id": "synthetic-model",
        "model_revision": "0" * 40,
        "child_plan_fingerprint": "f" * 64,
        "r3_protocol_fingerprint": PROTOCOL_FP,
        "population_manifest_fingerprint": manifest["manifest_fingerprint"],
        "measurement_code_commit": "a" * 40,
        "runtime": {"dtype": "bfloat16", "device": "cuda"},
        "execution_provenance": {"python_version": "3.11.14"},
        "paired_dataset_fingerprint": "9" * 64,
        "items": items,
    }
    kwargs.update(overrides)
    return r3_raw_evidence.build_evidence_payload(**kwargs)


def _valid_case() -> tuple[dict[str, Any], Any, dict[str, Any]]:
    manifest_items, manifest, plan = _two_item_case()
    items = [_scored_evidence(item) for item in manifest_items]
    return manifest, plan, _payload(manifest, items)


def _two_item_case() -> tuple[list[dict[str, Any]], dict[str, Any], Any]:
    manifest_items = [
        _manifest_item("r3-train-0001", split="TRAIN", row=0),
        _manifest_item("r3-test-0001", split="TEST", answer_index=2, row=1),
    ]
    manifest = _manifest(manifest_items)
    plan = _plan(manifest_items)
    return manifest_items, manifest, plan


# --------------------------------------------------------------------------- #
# Happy path + determinism
# --------------------------------------------------------------------------- #


def test_valid_payload_passes_all_structural_gates() -> None:
    manifest, plan, payload = _valid_case()
    r3_raw_evidence.validate_raw_evidence(
        payload, manifest=manifest, plan=plan, expected_protocol_fingerprint=PROTOCOL_FP
    )
    assert payload["evidence_fingerprint"] == r3_raw_evidence.evidence_fingerprint(payload)
    assert payload["structural_counts"] == {
        "items": 2,
        "cat": {"scored": 2, "missing": 0, "ineligible": 0},
        "ovr": {"scored": 2, "missing": 0, "ineligible": 0},
    }


def test_fingerprint_is_deterministic_and_sensitive_to_scores() -> None:
    manifest, _, payload_a = _valid_case()
    manifest_items = r3_population.manifest_items(manifest)
    items = [
        _scored_evidence(
            manifest_items[0],
            cat_probabilities=dict(zip(CANDIDATES, (0.6, 0.2, 0.1, 0.1), strict=True)),
        ),
        _scored_evidence(manifest_items[1]),
    ]
    payload_b = _payload(manifest, items)
    assert payload_a["evidence_fingerprint"] != payload_b["evidence_fingerprint"]
    assert r3_raw_evidence.canonical_payload(payload_a) == r3_raw_evidence.canonical_payload(
        _payload(manifest, [_scored_evidence(item) for item in manifest_items])
    )


def test_canonical_payload_has_no_timestamp_or_duration() -> None:
    _, _, payload = _valid_case()
    forbidden = {"timestamp", "start_time", "end_time", "duration", "duration_s", "run_id", "uuid"}
    keys = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                keys.add(str(key).lower())
                walk(value)
        elif isinstance(node, list):
            for entry in node:
                walk(entry)

    walk(r3_raw_evidence.canonical_payload(payload))
    assert keys.isdisjoint(forbidden)


# --------------------------------------------------------------------------- #
# Endpoint preservation (PART 36) — no clipping
# --------------------------------------------------------------------------- #


def test_exact_endpoint_scores_zero_and_one_are_preserved() -> None:
    manifest_items, manifest, plan = _two_item_case()

    # Anchor option-0 with a CAT mass of exactly 0.0 and an OVR score of 0.0.
    zero_cat = dict(zip(CANDIDATES, (0.0, 0.0, 0.0, 1.0), strict=True))
    zero_ovr = dict(zip(CANDIDATES, (0.0, 0.5, 0.5, 0.5), strict=True))

    evidence = _scored_evidence(manifest_items[0], cat_probabilities=zero_cat, ovr_scores=zero_ovr)
    assert evidence["cat"]["record"]["anchor_score"] == 0.0
    assert evidence["ovr"]["record"]["anchor_score"] == 0.0

    items = [evidence, _scored_evidence(manifest_items[1])]
    payload = _payload(manifest, items)
    r3_raw_evidence.validate_raw_evidence(
        payload, manifest=manifest, plan=plan, expected_protocol_fingerprint=PROTOCOL_FP
    )
    assert payload["items"][0]["ovr"]["record"]["candidates"][0]["candidate"] == CANDIDATES[0]


def test_endpoint_one_preserved_through_writer(tmp_path: Path) -> None:
    manifest_items, manifest, plan = _two_item_case()
    probabilities = dict(zip(CANDIDATES, (0.0, 0.0, 0.0, 1.0), strict=True))
    scores = dict(zip(CANDIDATES, (1.0, 0.0, 0.0, 0.0), strict=True))
    evidence = _scored_evidence(
        manifest_items[0], cat_probabilities=probabilities, ovr_scores=scores
    )
    items = [evidence, _scored_evidence(manifest_items[1])]
    payload = _payload(manifest, items)
    r3_raw_evidence.validate_raw_evidence(
        payload, manifest=manifest, plan=plan, expected_protocol_fingerprint=PROTOCOL_FP
    )
    target = r3_raw_evidence.write_json(tmp_path / "raw.json", payload)
    import json

    reloaded = json.loads(target.read_text(encoding="utf-8"))
    assert reloaded["items"][0]["cat"]["record"]["anchor_score"] == 0.0
    assert reloaded["items"][0]["ovr"]["record"]["anchor_score"] == 1.0
    assert reloaded["evidence_fingerprint"] == payload["evidence_fingerprint"]


# --------------------------------------------------------------------------- #
# Missing / ineligible (PART 27, 35) — no row substitution
# --------------------------------------------------------------------------- #


def test_missing_item_is_preserved_without_substitution() -> None:
    manifest_items = [
        _manifest_item("r3-train-0001", split="TRAIN"),
        _manifest_item("r3-test-0001", split="TEST"),
    ]
    manifest = _manifest(manifest_items)
    plan = _plan(manifest_items)
    good = _scored_evidence(manifest_items[0])
    bad = r3_raw_evidence.build_item_evidence(
        manifest_item=manifest_items[1],
        anchor="option-0",
        ground_truth_value=f"option-{manifest_items[1]['answer_index']}",
        anchor_correct=False,
        cat=r3_raw_evidence.unavailable_block(
            status=_integrity.MeasurementStatus.MISSING,
            reason="declared missing",
            source_record_id="m" * 64,
        ),
        ovr=r3_raw_evidence.unavailable_block(
            status=_integrity.MeasurementStatus.INELIGIBLE,
            reason="declared ineligible",
            source_record_id="i" * 64,
        ),
    )
    payload = _payload(manifest, [good, bad])
    r3_raw_evidence.validate_raw_evidence(
        payload, manifest=manifest, plan=plan, expected_protocol_fingerprint=PROTOCOL_FP
    )
    ids = [item["item_id"] for item in payload["items"]]
    assert ids == ["r3-train-0001", "r3-test-0001"]
    assert payload["items"][1]["cat"]["record"] is None
    assert payload["items"][1]["ovr"]["record"] is None
    assert payload["structural_counts"]["cat"]["missing"] == 1
    assert payload["structural_counts"]["ovr"]["ineligible"] == 1


# --------------------------------------------------------------------------- #
# Structural rejections (fail closed)
# --------------------------------------------------------------------------- #


def _expect_rejected(payload: dict[str, Any], manifest: dict[str, Any], plan: Any) -> None:
    import pytest

    with pytest.raises(r3_raw_evidence.RawEvidenceError):
        r3_raw_evidence.validate_raw_evidence(
            payload, manifest=manifest, plan=plan, expected_protocol_fingerprint=PROTOCOL_FP
        )


def test_duplicate_item_id_is_rejected() -> None:
    manifest, plan, payload = _valid_case()
    payload["items"][1]["item_id"] = payload["items"][0]["item_id"]
    _expect_rejected(payload, manifest, plan)


def test_missing_item_is_rejected() -> None:
    manifest, plan, payload = _valid_case()
    payload["items"] = [payload["items"][0]]
    _expect_rejected(payload, manifest, plan)


def test_wrong_item_order_is_rejected() -> None:
    manifest, plan, payload = _valid_case()
    payload["items"] = list(reversed(payload["items"]))
    _expect_rejected(payload, manifest, plan)


def test_anchor_disagreement_is_rejected() -> None:
    manifest, plan, payload = _valid_case()
    payload["items"][0]["anchor"] = CANDIDATES[2]
    _expect_rejected(payload, manifest, plan)


def test_cat_probability_sum_violation_is_rejected() -> None:
    manifest, plan, payload = _valid_case()
    record = payload["items"][0]["cat"]["record"]
    record["probabilities"][CANDIDATES[0]] = 0.5
    record["anchor_score"] = 0.5
    _expect_rejected(payload, manifest, plan)


def test_region_out_of_unit_interval_is_rejected() -> None:
    manifest, plan, payload = _valid_case()
    payload["items"][0]["ovr"]["record"]["candidates"][0]["probability_true"] = 1.5
    _expect_rejected(payload, manifest, plan)


def test_fingerprint_tamper_is_rejected() -> None:
    manifest, plan, payload = _valid_case()
    payload["evidence_fingerprint"] = "0" * 64
    _expect_rejected(payload, manifest, plan)


# --------------------------------------------------------------------------- #
# Forbidden result fields (PART 37)
# --------------------------------------------------------------------------- #


def test_valid_payload_has_no_forbidden_result_fields() -> None:
    _, _, payload = _valid_case()
    r3_raw_evidence.assert_no_result_fields(payload)


def test_injected_result_field_is_rejected() -> None:
    import pytest

    _, _, payload = _valid_case()
    result = r3_raw_evidence.canonical_payload(payload)
    result["brier"] = 0.1
    with pytest.raises(r3_raw_evidence.RawEvidenceError):
        r3_raw_evidence.assert_no_result_fields(result)
    nested = r3_raw_evidence.canonical_payload(payload)
    nested["items"][0]["native_risk"] = 0.2
    with pytest.raises(r3_raw_evidence.RawEvidenceError):
        r3_raw_evidence.assert_no_result_fields(nested)


# --------------------------------------------------------------------------- #
# Raw-evidence index (PART 45, 46)
# --------------------------------------------------------------------------- #


def _condition_entry(role: str, count: int, complete: bool) -> dict[str, Any]:
    return {
        "role": role,
        "model_id": "synthetic-model",
        "model_revision": "0" * 40,
        "artifact_filename": f"{role}.json",
        "file_sha256": "b" * 64,
        "evidence_fingerprint": "c" * 64,
        "expected_item_count": r3_raw_evidence.EXPECTED_ITEMS_PER_MODEL,
        "actual_item_count": count,
        "structural_status_counts": {"items": count},
        "structurally_complete": complete,
    }


def test_index_marks_both_conditions_complete_only_when_both_are() -> None:
    full = r3_raw_evidence.EXPECTED_ITEMS_PER_MODEL
    both = r3_raw_evidence.build_evidence_index(
        r3_protocol_fingerprint=PROTOCOL_FP,
        population_manifest_fingerprint="d" * 64,
        measurement_code_commit="a" * 40,
        conditions={
            "primary": _condition_entry("primary-confirmatory", full, True),
            "replication": _condition_entry("preregistered-replication", full, True),
        },
    )
    assert both["all_declared_conditions_complete"] is True
    assert both["index_fingerprint"] == r3_raw_evidence.index_fingerprint(both)

    one = r3_raw_evidence.build_evidence_index(
        r3_protocol_fingerprint=PROTOCOL_FP,
        population_manifest_fingerprint="d" * 64,
        measurement_code_commit="a" * 40,
        conditions={"primary": _condition_entry("primary-confirmatory", full, True)},
    )
    assert one["all_declared_conditions_complete"] is False


def test_index_contains_no_probabilities_or_metric() -> None:
    full = r3_raw_evidence.EXPECTED_ITEMS_PER_MODEL
    index = r3_raw_evidence.build_evidence_index(
        r3_protocol_fingerprint=PROTOCOL_FP,
        population_manifest_fingerprint="d" * 64,
        measurement_code_commit="a" * 40,
        conditions={
            "primary": _condition_entry("primary-confirmatory", full, True),
            "replication": _condition_entry("preregistered-replication", full, True),
        },
    )
    r3_raw_evidence.assert_no_result_fields(index)
    keys = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                keys.add(str(key).lower())
                walk(value)
        elif isinstance(node, list):
            for entry in node:
                walk(entry)

    walk(index)
    assert "probabilities" not in keys
    assert "anchor_score" not in keys
