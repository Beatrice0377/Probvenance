"""Offline tests for the R2 research-only transport analysis.

No model, no GPU, no network. Eligibility, calibrator determinism, matrix
orientation, exact log loss, and observed-range diagnostics are locked here.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path
from typing import Any

from probvenance.calibration import GROUND_TRUTH_SEMANTICS_FINGERPRINT_VERSION

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
measurements = _load("measurements")
analysis = _load("analysis")
_integrity = pilot_plan._integrity

Split = _integrity.Split
Status = _integrity.MeasurementStatus


def _plan(items: tuple[Any, ...]) -> Any:
    return _integrity.PairedFixedDecisionPlan(
        model_id="m",
        model_revision=None,
        population_id="p",
        population_version=1,
        ground_truth_semantics_fingerprint="fp",
        ground_truth_semantics_fingerprint_version=GROUND_TRUTH_SEMANTICS_FINGERPRINT_VERSION,
        measurement_a=measurements.cat_identity(),
        measurement_b=measurements.ovr_identity(),
        anchor_selection_id="a",
        anchor_selection_version=1,
        split_protocol_id="s",
        split_protocol_version=1,
        items=items,
    )


def _item(item_id: str, split: Any, *, correct: bool) -> Any:
    return _integrity.PlannedFixedDecisionItem(
        item_id=item_id,
        split=split,
        anchor_value="shipping",
        ground_truth_value="shipping" if correct else "billing",
        anchor_correct=correct,
    )


def _outcome(item_id: str, status: Any, score: float | None, *, winner: str = "billing") -> Any:
    if status is Status.SCORED:
        return _integrity.MeasurementOutcome(
            item_id=item_id,
            status=status,
            anchor_score=score,
            winner_value=winner,
            source_record_id=f"src-{item_id}",
            reason=None,
        )
    return _integrity.MeasurementOutcome(
        item_id=item_id,
        status=status,
        anchor_score=None,
        winner_value=None,
        source_record_id=f"src-{item_id}",
        reason=f"declared {status.value}",
    )


def _dataset(rows: list[dict[str, Any]], *, with_test: bool = True) -> Any:
    all_rows = list(rows)
    if with_test and not any(row["item"].split is Split.TEST for row in rows):
        all_rows.append(_row("zz-test-item", split=Split.TEST))
    items = tuple(row["item"] for row in all_rows)
    plan = _plan(items)
    outcomes_a = tuple(row["a"] for row in all_rows)
    outcomes_b = tuple(row["b"] for row in all_rows)
    return _integrity.PairedFixedDecisionDataset.create(plan, outcomes_a, outcomes_b)


def _row(
    item_id: str,
    *,
    split: Any = Split.TRAIN,
    correct: bool = True,
    a_status: Any = Status.SCORED,
    a_score: float | None = 0.5,
    b_status: Any = Status.SCORED,
    b_score: float | None = 0.5,
    winner: str = "billing",
) -> dict[str, Any]:
    return {
        "item": _item(item_id, split, correct=correct),
        "a": _outcome(item_id, a_status, a_score, winner=winner),
        "b": _outcome(item_id, b_status, b_score, winner=winner),
    }


def _cal(slope: float, intercept: float, *, measurement: Any = None) -> Any:
    return analysis.PilotFittedCalibrator(
        source_measurement=measurement or measurements.cat_identity(),
        target_id="fixed-decision-correctness",
        target_version=1,
        input_score_id="fixed-decision-semantic-probability",
        input_score_version=1,
        method_id=analysis.RESEARCH_LOGISTIC_METHOD_ID,
        method_version=1,
        l2_strength=0.01,
        plan_fingerprint="plan-fp",
        training_item_ids=("i1",),
        slope=slope,
        intercept=intercept,
    )


# --------------------------------------------------------------------------- #
# Eligibility
# --------------------------------------------------------------------------- #


def test_paired_fit_eligibility_requires_both_scored_only() -> None:
    dataset = _dataset(
        [
            _row("i1", a_status=Status.SCORED, b_status=Status.SCORED),
            _row("i2", a_status=Status.SCORED, b_status=Status.MISSING),
            _row("i3", a_status=Status.INELIGIBLE, b_status=Status.SCORED),
            _row("i4", a_status=Status.MISSING, b_status=Status.MISSING),
        ]
    )
    eligible = analysis.eligible_rows(dataset, split=Split.TRAIN)
    assert [row.item.item_id for row in eligible] == ["i1"]


def test_eligibility_ignores_winner_agreement_and_label() -> None:
    dataset = _dataset(
        [
            _row("i1", correct=False, winner="technical"),
            _row("i2", correct=True, winner="billing"),
        ]
    )
    eligible = analysis.eligible_rows(dataset, split=Split.TRAIN)
    assert [row.item.item_id for row in eligible] == ["i1", "i2"]


def test_scored_points_are_sorted_and_carry_anchor_correctness() -> None:
    dataset = _dataset(
        [
            _row("i2", correct=False, a_score=0.9, b_score=0.1),
            _row("i1", correct=True, a_score=0.2, b_score=0.8),
        ]
    )
    points = analysis.scored_points(dataset, split=Split.TRAIN)
    assert [p.item_id for p in points] == ["i1", "i2"]
    assert [(p.y, p.score_a, p.score_b) for p in points] == [
        (1.0, 0.2, 0.8),
        (0.0, 0.9, 0.1),
    ]


# --------------------------------------------------------------------------- #
# Calibrator determinism / content addressing
# --------------------------------------------------------------------------- #


def test_fit_is_order_independent_and_deterministic() -> None:
    rows = [("i1", 0.2, 1.0), ("i2", 0.8, 0.0), ("i3", 0.5, 1.0)]
    first = analysis.fit_pilot_calibrator(
        source_measurement=measurements.cat_identity(),
        training_rows=rows,
        plan_fingerprint="plan-fp",
    )
    second = analysis.fit_pilot_calibrator(
        source_measurement=measurements.cat_identity(),
        training_rows=list(reversed(rows)),
        plan_fingerprint="plan-fp",
    )
    assert first.slope == second.slope
    assert first.intercept == second.intercept
    assert first.fingerprint == second.fingerprint
    assert first.training_item_ids == ("i1", "i2", "i3")


def test_calibrator_fingerprint_changes_with_identity_and_configuration() -> None:
    rows = [("i1", 0.2, 1.0), ("i2", 0.8, 0.0)]
    base = analysis.fit_pilot_calibrator(
        source_measurement=measurements.cat_identity(),
        training_rows=rows,
        plan_fingerprint="plan-fp",
    )
    other_measurement = analysis.fit_pilot_calibrator(
        source_measurement=measurements.ovr_identity(),
        training_rows=rows,
        plan_fingerprint="plan-fp",
    )
    other_strength = analysis.fit_pilot_calibrator(
        source_measurement=measurements.cat_identity(),
        training_rows=rows,
        plan_fingerprint="plan-fp",
        l2_strength=0.5,
    )
    other_rows = analysis.fit_pilot_calibrator(
        source_measurement=measurements.cat_identity(),
        training_rows=[("i9", 0.2, 1.0), ("i8", 0.8, 0.0)],
        plan_fingerprint="plan-fp",
    )
    fprints = {
        base.fingerprint,
        other_measurement.fingerprint,
        other_strength.fingerprint,
        other_rows.fingerprint,
    }
    assert len(fprints) == 4


def test_apply_never_clips_and_handles_endpoints() -> None:
    cal = _cal(10.0, -5.0)
    low = cal.apply(0.0)
    high = cal.apply(1.0)
    assert 0.0 < low < 1.0
    assert 0.0 < high < 1.0
    assert low < high


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #


def test_brier_and_exact_logloss_values() -> None:
    assert analysis.brier([(0.5, 1.0)]) == 0.25
    assert analysis.exact_logloss([(1.0, 0.0)]) is None
    assert analysis.exact_logloss([(0.5, 0.0)]) == math.log(2.0)
    assert analysis.loss_cell(None) == {"state": "positive_infinity"}
    assert analysis.loss_cell(0.5) == {"state": "finite", "value": 0.5}


def _points() -> list[Any]:
    return [
        analysis.PairedPoint(item_id="i1", y=1.0, score_a=0.9, score_b=0.1),
        analysis.PairedPoint(item_id="i2", y=0.0, score_a=0.1, score_b=0.9),
    ]


def test_brier_matrix_orientation_is_not_swapped() -> None:
    points = _points()
    g_a = _cal(10.0, -5.0, measurement=measurements.cat_identity())
    g_b = _cal(10.0, 5.0, measurement=measurements.ovr_identity())
    matrix = analysis.brier_matrix(points, g_a, g_b)

    expected_aa = analysis.brier([(g_a.apply(0.9), 1.0), (g_a.apply(0.1), 0.0)])
    expected_ab = analysis.brier([(g_a.apply(0.1), 1.0), (g_a.apply(0.9), 0.0)])
    expected_ba = analysis.brier([(g_b.apply(0.9), 1.0), (g_b.apply(0.1), 0.0)])
    expected_bb = analysis.brier([(g_b.apply(0.1), 1.0), (g_b.apply(0.9), 0.0)])

    assert matrix["fit_a_eval_a"] == expected_aa
    assert matrix["fit_a_eval_b"] == expected_ab
    assert matrix["fit_b_eval_a"] == expected_ba
    assert matrix["fit_b_eval_b"] == expected_bb
    # A swap would have made fit_a_eval_b equal expected_aa; require they differ here.
    assert matrix["fit_a_eval_b"] != expected_aa
    assert matrix["delta_a_to_b"] == matrix["fit_a_eval_b"] - matrix["fit_b_eval_b"]
    assert matrix["delta_b_to_a"] == matrix["fit_b_eval_a"] - matrix["fit_a_eval_a"]


def test_logloss_matrix_marks_infinite_cells_explicitly() -> None:
    points = [
        analysis.PairedPoint(item_id="i1", y=0.0, score_a=1.0, score_b=1.0),
    ]
    # A calibrator with a huge positive slope drives the prediction to exactly 1.0.
    g = _cal(1000.0, 1000.0)
    matrix = analysis.logloss_matrix(points, g, g)
    assert matrix["fit_a_eval_a"] == {"state": "positive_infinity"}


# --------------------------------------------------------------------------- #
# Diagnostics
# --------------------------------------------------------------------------- #


def test_observed_range_diagnostics_fractions() -> None:
    train = [
        analysis.PairedPoint(item_id="t1", y=1.0, score_a=0.2, score_b=0.3),
        analysis.PairedPoint(item_id="t2", y=0.0, score_a=0.8, score_b=0.7),
    ]
    test = [
        analysis.PairedPoint(item_id="e1", y=1.0, score_a=0.1, score_b=0.9),
        analysis.PairedPoint(item_id="e2", y=0.0, score_a=0.5, score_b=0.5),
    ]
    diagnostics = analysis.observed_range_diagnostics(train, test)
    assert diagnostics["train_a"]["min"] == 0.2
    assert diagnostics["train_a"]["max"] == 0.8
    assert diagnostics["test_b_outside_train_a_range_fraction"] == 0.5
    assert diagnostics["test_a_outside_train_b_range_fraction"] == 0.5


def test_winner_and_non_simplex_diagnostics() -> None:
    winners = analysis.winner_diagnostics(
        truth_by_item={"i1": "billing", "i2": "shipping"},
        winner_a_by_item={"i1": "billing", "i2": "billing"},
        winner_b_by_item={"i1": "billing", "i2": "shipping"},
    )
    assert winners == {
        "n": 2,
        "winner_a_accuracy": 0.5,
        "winner_b_accuracy": 1.0,
        "winner_agreement_fraction": 0.5,
    }
    non_simplex = analysis.ovr_non_simplex_diagnostics([1.7, 1.2], [2, 1])
    assert non_simplex["candidate_score_sum_min"] == 1.2
    assert non_simplex["candidate_score_sum_max"] == 1.7
    assert non_simplex["items_with_multiple_candidates_over_half"] == 1


def test_fit_rejects_empty_rows() -> None:
    try:
        analysis.fit_pilot_calibrator(
            source_measurement=measurements.cat_identity(),
            training_rows=[],
            plan_fingerprint="p",
        )
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("zero training rows must be rejected")
