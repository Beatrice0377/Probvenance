"""Offline tests for the R2B stability-round plan (fixture, split, anchors, GT).

No model, no GPU, no network. These tests lock the 150-item fixture, the
pre-declared 6/4-per-cell split, the shared R2A anchor protocol, and the reused
R2A ground-truth semantics against silent change.
"""

from __future__ import annotations

import copy
import importlib.util
import inspect
import json
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


r2b_plan = _load("r2b_plan")
pilot_plan = r2b_plan.pilot_plan
Split = r2b_plan.Split


def _payload() -> dict[str, Any]:
    return r2b_plan.load_case_set()


def _build_plan(payload: dict[str, Any]) -> Any:
    return r2b_plan.build_plan(
        payload, model_id="Qwen/Qwen3.5-2B", model_revision=r2b_plan.POPULATION_ID
    )


def test_fixture_is_exactly_the_frozen_150_item_structure() -> None:
    payload = _payload()
    assert payload["case_set_version"] == "calibration-transport-r2b-v1"
    r2b_plan.validate_case_set(payload)
    cases = r2b_plan.r2b_cases(payload)
    assert len(cases) == 150
    assert sum(1 for c in cases if c.expected_category == "billing") == 50
    assert sum(1 for c in cases if c.expected_category == "shipping") == 50
    assert sum(1 for c in cases if c.expected_category == "technical") == 50
    for stratum in r2b_plan.STRATA:
        assert sum(1 for c in cases if c.stratum == stratum) == 30
    for category in r2b_plan.CATEGORIES:
        for stratum in r2b_plan.STRATA:
            cell = [c for c in cases if c.expected_category == category and c.stratum == stratum]
            assert len(cell) == 10


def test_item_ids_are_opaque_and_complete() -> None:
    cases = r2b_plan.r2b_cases(_payload())
    ids = [c.item_id for c in cases]
    assert sorted(ids) == [f"r2b-{i:04d}" for i in range(1, 151)]
    assert len(set(ids)) == 150
    for item_id in ids:
        assert item_id.startswith("r2b-")
        assert item_id[4:].isdigit()
        for category in r2b_plan.CATEGORIES:
            assert category not in item_id


def test_contexts_are_unique_and_do_not_reuse_r2a() -> None:
    cases = r2b_plan.r2b_cases(_payload())
    contexts = [c.context for c in cases]
    assert len(set(contexts)) == 150
    reference = pilot_plan.load_case_set(pilot_plan.DEFAULT_CASES_PATH)
    reference_contexts = {str(case["context"]) for case in reference["three_way_cases"]}
    assert set(contexts).isdisjoint(reference_contexts)


def test_candidate_set_matches_r2a_exactly() -> None:
    payload = _payload()
    assert r2b_plan.candidate_set(payload) == pilot_plan.source_candidates(
        pilot_plan.load_case_set(pilot_plan.DEFAULT_CASES_PATH)
    )


def test_split_is_six_train_four_test_per_cell_and_disjoint() -> None:
    payload = _payload()
    mappings = r2b_plan.split_of(payload)
    cases = r2b_plan.r2b_cases(payload)
    assert list(mappings).__len__() == 150
    train = [c.item_id for c in cases if mappings[c.item_id] is Split.TRAIN]
    test = [c.item_id for c in cases if mappings[c.item_id] is Split.TEST]
    assert len(train) == 90
    assert len(test) == 60
    assert set(train).isdisjoint(test)
    for category in r2b_plan.CATEGORIES:
        for stratum in r2b_plan.STRATA:
            cell = [
                c.item_id for c in cases if (c.expected_category, c.stratum) == (category, stratum)
            ]
            cell_train = [i for i in cell if mappings[i] is Split.TRAIN]
            cell_test = [i for i in cell if mappings[i] is Split.TEST]
            assert len(cell_train) == 6
            assert len(cell_test) == 4
            # the first six fixture-ordered items are TRAIN, the last four TEST
            assert cell_train == cell[:6]
            assert cell_test == cell[6:]


def test_anchor_function_is_shared_with_r2a_and_ignores_labels() -> None:
    # The R2B plan must call the single-source R2A selector, not a copy.
    assert r2b_plan.pilot_plan.select_anchor is pilot_plan.select_anchor
    signature = inspect.signature(pilot_plan.select_anchor)
    assert list(signature.parameters) == ["case_id", "candidate_names"]


def test_plan_anchors_are_the_hash_selection_of_opaque_ids() -> None:
    payload = _payload()
    plan = _build_plan(payload)
    candidate_names = [name for name, _ in r2b_plan.candidate_set(payload)]
    expected_category = {c.item_id: c.expected_category for c in r2b_plan.r2b_cases(payload)}
    for item in plan.items:
        anchor = pilot_plan.select_anchor(item.item_id, candidate_names)
        assert item.anchor_value == anchor
        assert item.ground_truth_value == expected_category[item.item_id]
        assert item.anchor_correct == (anchor == expected_category[item.item_id])


def test_plan_identity_is_r2b_and_reuses_r2a_ground_truth_semantics() -> None:
    payload = _payload()
    plan = _build_plan(payload)
    assert plan.population_id == "calibration-transport-r2b-three-way-stability"
    assert plan.population_version == 1
    assert plan.split_protocol_id == "r2b-five-strata-6-train-4-test-per-cell"
    assert plan.split_protocol_version == 1
    assert plan.anchor_selection_id == pilot_plan.ANCHOR_SELECTION_ID
    assert plan.anchor_selection_version == pilot_plan.ANCHOR_SELECTION_VERSION
    assert plan.measurement_a == r2b_plan._load_sibling("measurements").cat_identity()
    assert plan.measurement_b == r2b_plan._load_sibling("measurements").ovr_identity()
    assert (
        plan.ground_truth_semantics_fingerprint == pilot_plan.ground_truth_semantics().fingerprint
    )


def test_anchor_and_plan_are_deterministic_and_not_rebalanced() -> None:
    payload = _payload()
    plan_a = _build_plan(payload)
    plan_b = _build_plan(copy.deepcopy(payload))
    assert plan_a.fingerprint == plan_b.fingerprint
    # No ID reroll / anchor rebalance: Y counts are whatever the frozen ids give.
    train = [i for i in plan_a.items if i.split is Split.TRAIN]
    test = [i for i in plan_a.items if i.split is Split.TEST]
    assert sum(1 for i in train if i.anchor_correct) == 32
    assert sum(1 for i in train if not i.anchor_correct) == 58
    assert sum(1 for i in test if i.anchor_correct) == 23
    assert sum(1 for i in test if not i.anchor_correct) == 37


def test_cell_ordinals_are_computed_from_fixture_order() -> None:
    payload = _payload()
    ordinals = r2b_plan._cell_ordinals(r2b_plan.r2b_cases(payload))
    assert ordinals["r2b-0001"] == 0
    assert ordinals["r2b-0010"] == 9
    assert ordinals["r2b-0011"] == 0
    assert ordinals["r2b-0150"] == 9


def test_validation_fails_closed_on_count_drift() -> None:
    payload = _payload()
    payload["cases"] = payload["cases"][:-1]
    try:
        r2b_plan.validate_case_set(payload)
    except ValueError as exc:
        assert "150" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("validate_case_set accepted a 149-item fixture")


def test_validation_fails_closed_on_duplicate_context() -> None:
    payload = _payload()
    payload["cases"][1]["context"] = payload["cases"][0]["context"]
    try:
        r2b_plan.validate_case_set(payload)
    except ValueError as exc:
        assert "unique" in str(exc) or "duplicate" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("validate_case_set accepted duplicate contexts")


def test_validation_fails_closed_on_candidate_description_drift() -> None:
    payload = _payload()
    payload["candidate_set"][0]["description"] = "anything goes"
    try:
        r2b_plan.validate_case_set(payload)
    except ValueError as exc:
        assert "candidate set" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("validate_case_set accepted a drifted candidate description")


def test_validation_fails_closed_on_category_in_id() -> None:
    payload = _payload()
    payload["cases"][0]["id"] = "r2b-billing-0001"
    try:
        r2b_plan.validate_case_set(payload)
    except ValueError as exc:
        assert "opaque" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("validate_case_set accepted a category-bearing item id")


def test_fixture_json_roundtrips() -> None:
    path = r2b_plan.DEFAULT_CASES_PATH
    reparsed = json.loads(path.read_text(encoding="utf-8"))
    assert r2b_plan.case_set_fingerprint(reparsed) == r2b_plan.case_set_fingerprint(_payload())
