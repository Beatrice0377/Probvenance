"""Offline tests for the R1 paired experiment-integrity harness.

No model, no GPU, no network. Every record is hand-constructed so the
structural invariants cannot quietly change meaning.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

HARNESS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = HARNESS_DIR.parents[1]
SRC = REPO_ROOT / "src"

for path in (str(SRC), str(HARNESS_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)


def _load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, HARNESS_DIR / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


integrity = _load("integrity")

Split = integrity.Split
Status = integrity.MeasurementStatus
Err = integrity.ResearchIntegrityError


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #


def _identity(measurement_id: str = "cat-baseline", version: int = 1) -> Any:
    return integrity.MeasurementProtocolIdentity(measurement_id, version)


def _item(
    item_id: str,
    split: Any,
    *,
    anchor: Any = "a",
    truth: Any = "a",
    correct: bool = True,
) -> Any:
    return integrity.PlannedFixedDecisionItem(
        item_id=item_id,
        split=split,
        anchor_value=anchor,
        ground_truth_value=truth,
        anchor_correct=correct,
    )


def _default_items() -> tuple[Any, ...]:
    return (
        _item("i-train-1", Split.TRAIN, anchor="shipping", truth="shipping", correct=True),
        _item("i-test-1", Split.TEST, anchor="returns", truth="returns", correct=True),
        _item("i-audit-1", Split.AUDIT, anchor="billing", truth="shipping", correct=False),
    )


def _plan(**overrides: Any) -> Any:
    kwargs: dict[str, Any] = {
        "model_id": "model-x",
        "model_revision": "rev-1",
        "population_id": "pop-1",
        "population_version": 1,
        "ground_truth_semantics_fingerprint": "gt-fp-1",
        "ground_truth_semantics_fingerprint_version": 1,
        "measurement_a": _identity("cat-baseline", 1),
        "measurement_b": _identity("ovr-baseline", 1),
        "anchor_selection_id": "anchor-proto",
        "anchor_selection_version": 1,
        "split_protocol_id": "split-proto",
        "split_protocol_version": 1,
        "items": _default_items(),
    }
    kwargs.update(overrides)
    return integrity.PairedFixedDecisionPlan(**kwargs)


def _scored(item_id: str, score: float = 0.5, *, winner: Any = None, source: str = "rec-1") -> Any:
    return integrity.MeasurementOutcome(
        item_id=item_id,
        status=Status.SCORED,
        anchor_score=score,
        winner_value=winner,
        source_record_id=source,
        reason=None,
    )


def _missing(item_id: str, *, reason: str = "no score", source: str = "rec-1") -> Any:
    return integrity.MeasurementOutcome(
        item_id=item_id,
        status=Status.MISSING,
        anchor_score=None,
        winner_value=None,
        source_record_id=source,
        reason=reason,
    )


def _ineligible(item_id: str, *, reason: str = "cannot score anchor", source: str = "rec-1") -> Any:
    return integrity.MeasurementOutcome(
        item_id=item_id,
        status=Status.INELIGIBLE,
        anchor_score=None,
        winner_value=None,
        source_record_id=source,
        reason=reason,
    )


def _outcomes_for(
    plan: Any,
    *,
    missing: tuple[str, ...] = (),
    ineligible: tuple[str, ...] = (),
    score: float = 0.5,
) -> tuple[Any, ...]:
    rows = []
    for item in plan.items:
        if item.item_id in missing:
            rows.append(_missing(item.item_id))
        elif item.item_id in ineligible:
            rows.append(_ineligible(item.item_id))
        else:
            rows.append(_scored(item.item_id, score))
    return tuple(rows)


def _dataset(plan: Any, *, score: float = 0.5) -> Any:
    return integrity.PairedFixedDecisionDataset.create(
        plan,
        _outcomes_for(plan, score=score),
        _outcomes_for(plan, score=score),
    )


# --------------------------------------------------------------------------- #
# Construction / error taxonomy
# --------------------------------------------------------------------------- #


class TestErrorTaxonomy:
    def test_research_error_is_a_value_error(self) -> None:
        assert issubclass(integrity.ResearchIntegrityError, ValueError)

    def test_identities_are_str_enums(self) -> None:
        assert Split.TRAIN.value == "train"
        assert Status.SCORED.value == "scored"

    def test_research_version_constants_are_frozen(self) -> None:
        assert integrity.RESEARCH_SPEC_ID == "calibration-transport-research-spec"
        assert integrity.RESEARCH_SPEC_VERSION == 1
        assert integrity.FIXED_DECISION_TARGET_ID == "fixed-decision-correctness"
        assert integrity.FIXED_DECISION_TARGET_VERSION == 1
        assert integrity.FIXED_DECISION_INPUT_SCORE_ID == "fixed-decision-semantic-probability"
        assert integrity.FIXED_DECISION_INPUT_SCORE_VERSION == 1
        assert integrity.PAIRED_FIXED_DECISION_PLAN_FINGERPRINT_VERSION == 1
        assert integrity.PAIRED_FIXED_DECISION_DATASET_FINGERPRINT_VERSION == 1

    def test_does_not_reuse_phase4c_names(self) -> None:
        assert integrity.FIXED_DECISION_TARGET_ID != "winner_correctness"
        assert integrity.FIXED_DECISION_INPUT_SCORE_ID != "uncalibrated-selected-probability"


# --------------------------------------------------------------------------- #
# Plan validation
# --------------------------------------------------------------------------- #


class TestPlanValidation:
    def test_valid_plan_constructs(self) -> None:
        plan = _plan()
        assert len(plan.items) == 3
        assert len(plan.fingerprint) == 64

    def test_model_revision_none_is_allowed(self) -> None:
        assert _plan(model_revision=None).model_revision is None

    @pytest.mark.parametrize(
        "field_name",
        [
            "model_id",
            "population_id",
            "ground_truth_semantics_fingerprint",
            "anchor_selection_id",
            "split_protocol_id",
        ],
    )
    def test_empty_strings_rejected(self, field_name: str) -> None:
        with pytest.raises(Err):
            _plan(**{field_name: "   "})

    @pytest.mark.parametrize("field_name", ["model_id", "population_id"])
    def test_non_str_identifiers_rejected(self, field_name: str) -> None:
        with pytest.raises(Err):
            _plan(**{field_name: 5})

    @pytest.mark.parametrize(
        "field_name",
        [
            "population_version",
            "ground_truth_semantics_fingerprint_version",
            "anchor_selection_version",
            "split_protocol_version",
        ],
    )
    def test_bool_version_rejected(self, field_name: str) -> None:
        with pytest.raises(Err):
            _plan(**{field_name: True})

    @pytest.mark.parametrize(
        "field_name",
        ["population_version", "anchor_selection_version", "split_protocol_version"],
    )
    def test_zero_or_negative_version_rejected(self, field_name: str) -> None:
        with pytest.raises(Err):
            _plan(**{field_name: 0})
        with pytest.raises(Err):
            _plan(**{field_name: -3})

    def test_measurement_a_equals_b_rejected(self) -> None:
        with pytest.raises(Err):
            _plan(measurement_a=_identity("same", 1), measurement_b=_identity("same", 1))

    def test_same_measurement_id_different_version_allowed(self) -> None:
        plan = _plan(measurement_a=_identity("m", 1), measurement_b=_identity("m", 2))
        assert plan.measurement_a != plan.measurement_b

    def test_items_must_be_tuple(self) -> None:
        with pytest.raises(Err):
            _plan(items=list(_default_items()))

    def test_empty_items_rejected(self) -> None:
        with pytest.raises(Err):
            _plan(items=())

    def test_duck_typed_item_rejected(self) -> None:
        class Fake:
            item_id = "x"
            split = Split.TRAIN
            anchor_value = "a"
            ground_truth_value = "a"
            anchor_correct = True

        with pytest.raises(Err):
            _plan(items=(Fake(),))  # type: ignore[arg-type]

    def test_duplicate_item_id_same_split_rejected(self) -> None:
        items = (_item("dup", Split.TRAIN), _item("dup", Split.TRAIN), _item("t", Split.TEST))
        with pytest.raises(Err):
            _plan(items=items)

    def test_duplicate_item_id_across_splits_rejected(self) -> None:
        items = (_item("dup", Split.TRAIN), _item("dup", Split.TEST))
        with pytest.raises(Err):
            _plan(items=items)

    def test_no_train_rejected(self) -> None:
        with pytest.raises(Err):
            _plan(items=(_item("t", Split.TEST),))

    def test_no_test_rejected(self) -> None:
        with pytest.raises(Err):
            _plan(items=(_item("t", Split.TRAIN),))

    def test_train_and_test_without_audit_allowed(self) -> None:
        plan = _plan(items=(_item("t", Split.TRAIN), _item("e", Split.TEST)))
        assert len(plan.items) == 2

    def test_invalid_split_type_rejected(self) -> None:
        with pytest.raises(Err):
            _item("x", "train")  # type: ignore[arg-type]

    def test_empty_item_id_rejected(self) -> None:
        with pytest.raises(Err):
            _item("  ", Split.TRAIN)

    def test_non_bool_anchor_correct_rejected(self) -> None:
        with pytest.raises(Err):
            _item("x", Split.TRAIN, correct=1)  # type: ignore[arg-type]


class TestSemanticValues:
    @pytest.mark.parametrize("value", [True, False, 0, 1, -5, 0.0, 1.5, "shipping"])
    def test_valid_semantic_values(self, value: Any) -> None:
        assert _item("x", Split.TRAIN, anchor=value).anchor_value == value

    @pytest.mark.parametrize(
        "value",
        [None, [1], {"a": 1}, (1,), {1}, b"x", object()],
    )
    def test_invalid_semantic_values_rejected(self, value: Any) -> None:
        with pytest.raises(Err):
            _item("x", Split.TRAIN, anchor=value)

    @pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_float_rejected(self, value: float) -> None:
        with pytest.raises(Err):
            _item("x", Split.TRAIN, anchor=value)

    def test_bool_is_not_accepted_as_version(self) -> None:
        with pytest.raises(Err):
            integrity.MeasurementProtocolIdentity("m", True)

    def test_empty_measurement_id_rejected(self) -> None:
        with pytest.raises(Err):
            integrity.MeasurementProtocolIdentity("", 1)


# --------------------------------------------------------------------------- #
# Plan fingerprint
# --------------------------------------------------------------------------- #


class TestPlanFingerprint:
    def test_item_tuple_order_does_not_change_fingerprint(self) -> None:
        forward = _plan(items=_default_items())
        backward = _plan(items=tuple(reversed(_default_items())))
        assert forward.fingerprint == backward.fingerprint
        assert forward.canonical_payload() == backward.canonical_payload()

    def test_split_change_changes_fingerprint(self) -> None:
        base = _plan()
        changed = _plan(
            items=(
                _item("i-train-1", Split.TRAIN, anchor="shipping", truth="shipping"),
                _item("i-test-1", Split.TEST, anchor="returns", truth="returns"),
                _item("i-audit-1", Split.TRAIN, anchor="billing", truth="shipping", correct=False),
            )
        )
        assert base.fingerprint != changed.fingerprint

    def test_anchor_change_changes_fingerprint(self) -> None:
        base = _plan()
        changed = _plan(
            items=(
                _item("i-train-1", Split.TRAIN, anchor="billing", truth="shipping"),
                _item("i-test-1", Split.TEST, anchor="returns", truth="returns"),
                _item("i-audit-1", Split.AUDIT, anchor="billing", truth="shipping", correct=False),
            )
        )
        assert base.fingerprint != changed.fingerprint

    def test_anchor_correct_change_changes_fingerprint(self) -> None:
        base = _plan()
        changed = _plan(
            items=(
                _item("i-train-1", Split.TRAIN, anchor="shipping", truth="shipping", correct=False),
                _item("i-test-1", Split.TEST, anchor="returns", truth="returns"),
                _item("i-audit-1", Split.AUDIT, anchor="billing", truth="shipping", correct=False),
            )
        )
        assert base.fingerprint != changed.fingerprint

    def test_ground_truth_change_changes_fingerprint(self) -> None:
        base = _plan()
        changed = _plan(
            items=(
                _item("i-train-1", Split.TRAIN, anchor="shipping", truth="returns"),
                _item("i-test-1", Split.TEST, anchor="returns", truth="returns"),
                _item("i-audit-1", Split.AUDIT, anchor="billing", truth="shipping", correct=False),
            )
        )
        assert base.fingerprint != changed.fingerprint

    def test_measurement_a_change_changes_fingerprint(self) -> None:
        base = _plan()
        changed = _plan(measurement_a=_identity("cat-v2", 2))
        assert base.fingerprint != changed.fingerprint

    def test_measurement_role_swap_changes_fingerprint(self) -> None:
        base = _plan(measurement_a=_identity("cat", 1), measurement_b=_identity("ovr", 1))
        swapped = _plan(measurement_a=_identity("ovr", 1), measurement_b=_identity("cat", 1))
        assert base.fingerprint != swapped.fingerprint

    def test_model_revision_change_changes_fingerprint(self) -> None:
        base = _plan()
        assert base.fingerprint != _plan(model_revision=None).fingerprint
        assert base.fingerprint != _plan(model_revision="rev-2").fingerprint

    def test_population_change_changes_fingerprint(self) -> None:
        assert _plan().fingerprint != _plan(population_id="pop-2").fingerprint
        assert _plan().fingerprint != _plan(population_version=2).fingerprint

    def test_anchor_protocol_change_changes_fingerprint(self) -> None:
        assert _plan().fingerprint != _plan(anchor_selection_id="other").fingerprint
        assert _plan().fingerprint != _plan(anchor_selection_version=2).fingerprint

    def test_split_protocol_change_changes_fingerprint(self) -> None:
        assert _plan().fingerprint != _plan(split_protocol_id="other").fingerprint

    def test_payload_commits_target_and_input_identity(self) -> None:
        payload = _plan().canonical_payload()
        assert payload["target_id"] == "fixed-decision-correctness"
        assert payload["target_version"] == 1
        assert payload["input_score_id"] == "fixed-decision-semantic-probability"
        assert payload["input_score_version"] == 1
        assert payload["research_spec_id"] == "calibration-transport-research-spec"

    def test_fingerprint_is_order_independent_for_items(self) -> None:
        a = _plan(items=_default_items())
        b = _plan(items=(_default_items()[2], _default_items()[0], _default_items()[1]))
        assert a.fingerprint == b.fingerprint


# --------------------------------------------------------------------------- #
# Outcome state machine
# --------------------------------------------------------------------------- #


class TestOutcomeStateMachine:
    @pytest.mark.parametrize("score", [0.0, 0.5, 1.0])
    def test_scored_valid(self, score: float) -> None:
        assert _scored("i", score).anchor_score == score

    def test_scored_winner_value_optional(self) -> None:
        assert _scored("i", 0.5, winner="shipping").winner_value == "shipping"
        assert _scored("i", 0.5, winner=None).winner_value is None

    def test_scored_does_not_require_winner_to_equal_anchor(self) -> None:
        # The anchor is "shipping"; the measurement's own winner is "returns".
        assert _scored("i", 0.5, winner="returns").anchor_score == 0.5

    @pytest.mark.parametrize("score", [None, True, 1, "0.5"])
    def test_scored_non_float_score_rejected(self, score: Any) -> None:
        with pytest.raises(Err):
            _scored("i", score)  # type: ignore[arg-type]

    @pytest.mark.parametrize("score", [-0.1, 1.1, 2.0])
    def test_scored_out_of_range_rejected(self, score: float) -> None:
        with pytest.raises(Err):
            _scored("i", score)

    @pytest.mark.parametrize("score", [float("nan"), float("inf"), float("-inf")])
    def test_scored_non_finite_rejected(self, score: float) -> None:
        with pytest.raises(Err):
            _scored("i", score)

    def test_scored_with_reason_rejected(self) -> None:
        with pytest.raises(Err):
            integrity.MeasurementOutcome(
                item_id="i",
                status=Status.SCORED,
                anchor_score=0.5,
                winner_value=None,
                source_record_id="rec",
                reason="why",
            )

    def test_missing_with_score_rejected(self) -> None:
        with pytest.raises(Err):
            integrity.MeasurementOutcome(
                item_id="i",
                status=Status.MISSING,
                anchor_score=0.5,
                winner_value=None,
                source_record_id="rec",
                reason="why",
            )

    def test_missing_without_reason_rejected(self) -> None:
        with pytest.raises(Err):
            integrity.MeasurementOutcome(
                item_id="i",
                status=Status.MISSING,
                anchor_score=None,
                winner_value=None,
                source_record_id="rec",
                reason=None,
            )

    def test_missing_empty_reason_rejected(self) -> None:
        with pytest.raises(Err):
            _missing("i", reason="   ")

    def test_ineligible_with_score_rejected(self) -> None:
        with pytest.raises(Err):
            integrity.MeasurementOutcome(
                item_id="i",
                status=Status.INELIGIBLE,
                anchor_score=0.5,
                winner_value=None,
                source_record_id="rec",
                reason="why",
            )

    def test_ineligible_without_reason_rejected(self) -> None:
        with pytest.raises(Err):
            _ineligible("i", reason="")

    @pytest.mark.parametrize("builder", [_scored, _missing, _ineligible])
    def test_empty_source_record_id_rejected(self, builder: Any) -> None:
        with pytest.raises(Err):
            builder("i", source="")

    def test_empty_item_id_rejected(self) -> None:
        with pytest.raises(Err):
            _scored("")

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(Err):
            integrity.MeasurementOutcome(
                item_id="i",
                status="scored",  # type: ignore[arg-type]
                anchor_score=0.5,
                winner_value=None,
                source_record_id="rec",
                reason=None,
            )

    def test_invalid_winner_value_rejected(self) -> None:
        with pytest.raises(Err):
            _scored("i", 0.5, winner=["x"])

    def test_no_clipping(self) -> None:
        with pytest.raises(Err):
            _scored("i", 1.1)


# --------------------------------------------------------------------------- #
# Dataset exact item-set contract
# --------------------------------------------------------------------------- #


class TestDatasetItemSetContract:
    def test_valid_dataset_constructs(self) -> None:
        plan = _plan()
        dataset = _dataset(plan)
        assert len(dataset.rows) == len(plan.items)

    def test_missing_a_outcome_rejected(self) -> None:
        plan = _plan()
        with pytest.raises(Err):
            integrity.PairedFixedDecisionDataset.create(
                plan, _outcomes_for(plan)[:-1], _outcomes_for(plan)
            )

    def test_missing_b_outcome_rejected(self) -> None:
        plan = _plan()
        with pytest.raises(Err):
            integrity.PairedFixedDecisionDataset.create(
                plan, _outcomes_for(plan), _outcomes_for(plan)[:-1]
            )

    def test_extra_a_item_rejected(self) -> None:
        plan = _plan()
        with pytest.raises(Err):
            integrity.PairedFixedDecisionDataset.create(
                plan, (*_outcomes_for(plan), _scored("unplanned")), _outcomes_for(plan)
            )

    def test_extra_b_item_rejected(self) -> None:
        plan = _plan()
        with pytest.raises(Err):
            integrity.PairedFixedDecisionDataset.create(
                plan, _outcomes_for(plan), (*_outcomes_for(plan), _scored("unplanned"))
            )

    def test_duplicate_a_item_rejected(self) -> None:
        plan = _plan()
        dup = (*_outcomes_for(plan), _outcomes_for(plan)[0])
        with pytest.raises(Err):
            integrity.PairedFixedDecisionDataset.create(plan, dup, _outcomes_for(plan))

    def test_duplicate_b_item_rejected(self) -> None:
        plan = _plan()
        dup = (*_outcomes_for(plan), _outcomes_for(plan)[0])
        with pytest.raises(Err):
            integrity.PairedFixedDecisionDataset.create(plan, _outcomes_for(plan), dup)

    def test_outcomes_must_be_tuple(self) -> None:
        plan = _plan()
        with pytest.raises(Err):
            integrity.PairedFixedDecisionDataset.create(
                plan,
                list(_outcomes_for(plan)),
                _outcomes_for(plan),  # type: ignore[arg-type]
            )

    def test_duck_typed_plan_rejected(self) -> None:
        class FakePlan:
            items: tuple[Any, ...] = ()

        with pytest.raises(Err):
            integrity.PairedFixedDecisionDataset.create(FakePlan(), (), ())  # type: ignore[arg-type]

    def test_pairing_is_by_item_id_not_position(self) -> None:
        plan = _plan()
        a = _outcomes_for(plan, score=0.25)
        b = tuple(reversed(_outcomes_for(plan, score=0.75)))
        dataset = integrity.PairedFixedDecisionDataset.create(plan, a, b)
        by_id = {row.item.item_id: row for row in dataset.rows}
        assert by_id["i-train-1"].outcome_a.anchor_score == 0.25
        assert by_id["i-train-1"].outcome_b.anchor_score == 0.75


# --------------------------------------------------------------------------- #
# Missing / ineligible preservation
# --------------------------------------------------------------------------- #


class TestMissingPreservation:
    def test_missing_and_ineligible_rows_are_preserved(self) -> None:
        plan = _plan()
        a = _outcomes_for(plan, missing=("i-train-1",))
        b = _outcomes_for(plan, ineligible=("i-test-1",))
        dataset = integrity.PairedFixedDecisionDataset.create(plan, a, b)
        assert len(dataset.rows) == len(plan.items)
        statuses = {
            (row.item.item_id, row.outcome_a.status, row.outcome_b.status) for row in dataset.rows
        }
        assert ("i-train-1", Status.MISSING, Status.SCORED) in statuses
        assert ("i-test-1", Status.SCORED, Status.INELIGIBLE) in statuses

    def test_ten_items_always_ten_rows(self) -> None:
        train = tuple(_item(f"tr-{i}", Split.TRAIN) for i in range(5))
        test = tuple(_item(f"te-{i}", Split.TEST) for i in range(5))
        plan = _plan(items=train + test)
        a_ids = tuple(item.item_id for item in plan.items)
        a = tuple(
            _missing(i) if idx % 3 == 0 else _ineligible(i) if idx % 3 == 1 else _scored(i, 0.5)
            for idx, i in enumerate(a_ids)
        )
        b = _outcomes_for(plan, missing=("tr-0",))
        dataset = integrity.PairedFixedDecisionDataset.create(plan, a, b)
        assert len(dataset.rows) == 10

    def test_no_analysis_policy_helpers_exposed(self) -> None:
        for name in ("drop_missing", "eligible_only", "complete_cases", "analysis_ready"):
            assert not hasattr(integrity.PairedFixedDecisionDataset, name)


# --------------------------------------------------------------------------- #
# Winner / anchor equality never affects inclusion
# --------------------------------------------------------------------------- #


class TestWinnerEqualityDoesNotAffectInclusion:
    @pytest.mark.parametrize(
        "winner_a,winner_b",
        [
            ("shipping", "returns"),  # anchor == winner_A only
            ("returns", "shipping"),  # anchor == winner_B only
            ("shipping", "shipping"),  # anchor == both
            ("returns", "billing"),  # anchor == neither
        ],
    )
    def test_all_equality_patterns_valid(self, winner_a: str, winner_b: str) -> None:
        plan = _plan()
        a = tuple(_scored(item.item_id, 0.4, winner=winner_a) for item in plan.items)
        b = tuple(_scored(item.item_id, 0.6, winner=winner_b) for item in plan.items)
        dataset = integrity.PairedFixedDecisionDataset.create(plan, a, b)
        assert len(dataset.rows) == len(plan.items)

    def test_equality_does_not_change_dataset_identity(self) -> None:
        plan = _plan()
        a_equal = tuple(_scored(item.item_id, 0.4, winner="shipping") for item in plan.items)
        a_diff = tuple(_scored(item.item_id, 0.4, winner="billing") for item in plan.items)
        b = tuple(_scored(item.item_id, 0.6, winner="returns") for item in plan.items)
        equal = integrity.PairedFixedDecisionDataset.create(plan, a_equal, b)
        different = integrity.PairedFixedDecisionDataset.create(plan, a_diff, b)
        # Equality changes the (diagnostic) winner value, hence the fingerprint,
        # but it never drops a row on either side.
        assert len(equal.rows) == len(different.rows) == len(plan.items)
        assert equal.fingerprint != different.fingerprint


# --------------------------------------------------------------------------- #
# Dataset fingerprint
# --------------------------------------------------------------------------- #


class TestDatasetFingerprint:
    def test_outcome_order_does_not_change_fingerprint(self) -> None:
        plan = _plan()
        a = _outcomes_for(plan)
        b = _outcomes_for(plan)
        d1 = integrity.PairedFixedDecisionDataset.create(plan, a, b)
        d2 = integrity.PairedFixedDecisionDataset.create(
            plan, tuple(reversed(a)), tuple(reversed(b))
        )
        assert d1.fingerprint == d2.fingerprint
        assert d1.canonical_payload() == d2.canonical_payload()

    def test_score_change_changes_fingerprint(self) -> None:
        plan = _plan()
        d1 = _dataset(plan, score=0.5)
        d2 = _dataset(plan, score=0.6)
        assert d1.fingerprint != d2.fingerprint

    def test_status_change_changes_fingerprint(self) -> None:
        plan = _plan()
        base = _dataset(plan)
        with_missing = integrity.PairedFixedDecisionDataset.create(
            plan, _outcomes_for(plan, missing=("i-train-1",)), _outcomes_for(plan)
        )
        assert base.fingerprint != with_missing.fingerprint

    def test_missing_and_ineligible_are_identity_distinct(self) -> None:
        plan = _plan()
        missing = integrity.PairedFixedDecisionDataset.create(
            plan, _outcomes_for(plan, missing=("i-train-1",)), _outcomes_for(plan)
        )
        ineligible = integrity.PairedFixedDecisionDataset.create(
            plan, _outcomes_for(plan, ineligible=("i-train-1",)), _outcomes_for(plan)
        )
        assert missing.fingerprint != ineligible.fingerprint

    def test_reason_change_changes_fingerprint(self) -> None:
        plan = _plan()
        d1 = integrity.PairedFixedDecisionDataset.create(
            plan, _outcomes_for(plan, missing=("i-train-1",)), _outcomes_for(plan)
        )

        def _alt(plan: Any) -> tuple[Any, ...]:
            return tuple(
                _missing(item.item_id, reason="different reason")
                if item.item_id == "i-train-1"
                else _scored(item.item_id)
                for item in plan.items
            )

        d2 = integrity.PairedFixedDecisionDataset.create(plan, _alt(plan), _outcomes_for(plan))
        assert d1.fingerprint != d2.fingerprint

    def test_winner_change_changes_fingerprint(self) -> None:
        plan = _plan()
        d1 = integrity.PairedFixedDecisionDataset.create(
            plan,
            tuple(_scored(i.item_id, 0.5, winner="a") for i in plan.items),
            _outcomes_for(plan),
        )
        d2 = integrity.PairedFixedDecisionDataset.create(
            plan,
            tuple(_scored(i.item_id, 0.5, winner="b") for i in plan.items),
            _outcomes_for(plan),
        )
        assert d1.fingerprint != d2.fingerprint

    def test_source_record_change_changes_fingerprint(self) -> None:
        plan = _plan()
        d1 = integrity.PairedFixedDecisionDataset.create(
            plan,
            tuple(_scored(i.item_id, 0.5, source="rec-1") for i in plan.items),
            _outcomes_for(plan),
        )
        d2 = integrity.PairedFixedDecisionDataset.create(
            plan,
            tuple(_scored(i.item_id, 0.5, source="rec-2") for i in plan.items),
            _outcomes_for(plan),
        )
        assert d1.fingerprint != d2.fingerprint

    def test_plan_content_change_changes_dataset_fingerprint(self) -> None:
        plan = _plan()
        other = _plan(measurement_b=_identity("ovr-v2", 2))
        assert _dataset(plan).fingerprint != _dataset(other).fingerprint

    def test_dataset_payload_embeds_plan_payload(self) -> None:
        plan = _plan()
        payload = _dataset(plan).canonical_payload()
        assert payload["plan"] == plan.canonical_payload()

    def test_measurement_role_swap_changes_dataset_fingerprint(self) -> None:
        ab = _plan(measurement_a=_identity("cat", 1), measurement_b=_identity("ovr", 1))
        ba = _plan(measurement_a=_identity("ovr", 1), measurement_b=_identity("cat", 1))
        assert _dataset(ab).fingerprint != _dataset(ba).fingerprint


# --------------------------------------------------------------------------- #
# Scope guards
# --------------------------------------------------------------------------- #


class TestScopeGuards:
    @pytest.mark.parametrize(
        "name",
        [
            "TransportGraph",
            "TransportEdge",
            "CalibrationExperimentRun",
            "TransportAudit",
            "CompatibilityRegistry",
            "ResearchStore",
        ],
    )
    def test_forbidden_artifact_classes_absent(self, name: str) -> None:
        assert not hasattr(integrity, name)

    @pytest.mark.parametrize(
        "name",
        ["fit", "fit_calibrator", "brier", "log_loss", "transport_regret", "split_items"],
    )
    def test_no_analysis_or_split_functions_absent(self, name: str) -> None:
        assert not hasattr(integrity, name)
