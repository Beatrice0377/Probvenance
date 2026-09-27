"""Offline tests for the R2 frozen pilot plan (fixture, split, anchors, GT).

No model, no GPU, no network. The plan is the pre-measurement declaration, so
these tests lock the fixture, the split, the anchor protocol, and the declared
ground-truth semantics against silent change.
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


pilot_plan = _load("pilot_plan")
_split = pilot_plan._integrity.Split


def _payload() -> dict[str, Any]:
    return pilot_plan.load_case_set()


def test_fixture_is_exactly_the_fifteen_three_way_cases() -> None:
    payload = _payload()
    assert payload["case_set_version"] == "choice-signal-v1"
    cases = pilot_plan.pilot_cases(payload)
    assert len(cases) == 15
    assert [c.case_id for c in cases] == [
        "3w-billing-01",
        "3w-billing-02",
        "3w-billing-03",
        "3w-billing-04",
        "3w-billing-05",
        "3w-shipping-01",
        "3w-shipping-02",
        "3w-shipping-03",
        "3w-shipping-04",
        "3w-shipping-05",
        "3w-technical-01",
        "3w-technical-02",
        "3w-technical-03",
        "3w-technical-04",
        "3w-technical-05",
    ]


def test_candidate_order_is_exact_source_order() -> None:
    candidates = pilot_plan.source_candidates(_payload())
    assert [name for name, _ in candidates] == ["billing", "shipping", "technical"]


def test_source_case_set_fingerprint_is_deterministic() -> None:
    payload = _payload()
    first = pilot_plan.case_set_fingerprint(payload)
    second = pilot_plan.case_set_fingerprint(payload)
    assert first == second
    assert len(first) == 64
    assert first == __import__("probvenance.fingerprint", fromlist=["fingerprint"]).fingerprint(
        json.loads(json.dumps(payload))
    )


def test_frozen_split_is_exactly_nine_train_six_test_zero_audit() -> None:
    payload = _payload()
    assert len(pilot_plan.TRAIN_CASE_IDS) == 9
    assert len(pilot_plan.TEST_CASE_IDS) == 6
    assert pilot_plan.AUDIT_CASE_IDS == ()
    assert set(pilot_plan.TRAIN_CASE_IDS).isdisjoint(pilot_plan.TEST_CASE_IDS)
    assert set(pilot_plan.TRAIN_CASE_IDS) | set(pilot_plan.TEST_CASE_IDS) == {
        case.case_id for case in pilot_plan.pilot_cases(payload)
    }
    assert pilot_plan.predeclared_split("3w-billing-01") is _split.TRAIN
    assert pilot_plan.predeclared_split("3w-billing-05") is _split.TEST
    assert pilot_plan.predeclared_split("3w-technical-03") is _split.TRAIN
    assert pilot_plan.predeclared_split("3w-shipping-04") is _split.TEST


def test_predeclared_split_rejects_unknown_case() -> None:
    try:
        pilot_plan.predeclared_split("3w-billing-99")
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("unknown case id must be rejected")


def test_anchor_selection_consumes_only_case_id_and_candidate_names() -> None:
    signature = inspect.signature(pilot_plan.select_anchor)
    assert list(signature.parameters) == ["case_id", "candidate_names"]


def test_anchor_is_deterministic_and_within_candidate_set() -> None:
    names = ["billing", "shipping", "technical"]
    for case in pilot_plan.pilot_cases(_payload()):
        first = pilot_plan.select_anchor(case.case_id, names)
        second = pilot_plan.select_anchor(case.case_id, names)
        assert first == second
        assert first in names


def test_anchor_is_unchanged_by_simulated_measurement_output() -> None:
    names = ["billing", "shipping", "technical"]
    case_id = "3w-shipping-02"
    before = pilot_plan.select_anchor(case_id, names)
    # Simulate arbitrary CAT/OVR outputs that a naive implementation might peek at.
    _simulated = {"cat": {"billing": 0.9}, "ovr": {"billing": 0.8}, "winner": "billing"}
    after = pilot_plan.select_anchor(case_id, names)
    assert before == after


def test_plan_has_fifteen_items_and_two_distinct_measurements() -> None:
    plan = pilot_plan.build_plan(_payload(), model_id="fake-model", model_revision="rev-1")
    assert len(plan.items) == 15
    assert plan.measurement_a.measurement_id == "direct-categorical-anchor-probability"
    assert plan.measurement_a.measurement_version == 1
    assert plan.measurement_b.measurement_id == "independent-binary-anchor-probability"
    assert plan.measurement_b.measurement_version == 1
    assert plan.measurement_a != plan.measurement_b
    assert plan.anchor_selection_id == "sha256-case-id-candidate-set-anchor"
    assert plan.split_protocol_id == "three-way-synthetic-3-train-2-test-per-category"
    assert sum(1 for i in plan.items if i.split is _split.TRAIN) == 9
    assert sum(1 for i in plan.items if i.split is _split.TEST) == 6


def test_plan_anchor_correct_is_derived_only_from_declared_truth() -> None:
    payload = _payload()
    truth = {c["id"]: c["expected_category"] for c in payload["three_way_cases"]}
    plan = pilot_plan.build_plan(payload, model_id="fake-model", model_revision=None)
    for item in plan.items:
        assert item.anchor_correct == (item.anchor_value == truth[item.item_id])
        assert item.ground_truth_value == truth[item.item_id]


def test_plan_fingerprint_is_deterministic_and_revision_sensitive() -> None:
    payload = _payload()
    first = pilot_plan.build_plan(payload, model_id="m", model_revision=None)
    second = pilot_plan.build_plan(payload, model_id="m", model_revision=None)
    other = pilot_plan.build_plan(payload, model_id="m", model_revision="rev-2")
    assert first.fingerprint == second.fingerprint
    assert first.fingerprint != other.fingerprint


def test_ground_truth_semantics_is_declared_and_stable() -> None:
    semantics = pilot_plan.ground_truth_semantics()
    assert semantics.labeling_rule == "choice-signal-handwritten-expected-category-v1"
    assert semantics.ambiguity_policy == "predeclared-resolved-three-way-synthetic-pilot-v1"
    assert semantics.taxonomy_id == "choice-signal-routing-three-way"
    assert semantics.taxonomy_version == 1
    assert semantics.fingerprint == pilot_plan.ground_truth_semantics().fingerprint


def test_plan_rejects_a_mutated_fixture() -> None:
    payload = copy.deepcopy(_payload())
    payload["three_way_cases"] = payload["three_way_cases"][:-1]
    try:
        pilot_plan.build_plan(payload, model_id="m", model_revision=None)
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("a mutated fixture must be rejected")


def test_pinned_model_revision_is_fixed_and_used_by_default() -> None:
    run_pilot = _load("run_pilot")
    assert run_pilot.PINNED_MODEL_REVISION == "15852e8c16360a2fea060d615a32b45270f8a8fc"
    assert run_pilot.parse_args([]).revision == run_pilot.PINNED_MODEL_REVISION
    try:
        run_pilot.main(["--revision", ""])
    except SystemExit:
        pass
    else:  # pragma: no cover
        raise AssertionError("an unpinned revision must be rejected")


def test_pinned_revision_changes_plan_fingerprint_not_schema() -> None:
    run_pilot = _load("run_pilot")
    payload = _payload()
    unpinned = pilot_plan.build_plan(payload, model_id="m", model_revision=None)
    pinned = pilot_plan.build_plan(
        payload, model_id="m", model_revision=run_pilot.PINNED_MODEL_REVISION
    )
    assert pinned.fingerprint != unpinned.fingerprint
    assert pilot_plan._integrity.PAIRED_FIXED_DECISION_PLAN_FINGERPRINT_VERSION == 1
