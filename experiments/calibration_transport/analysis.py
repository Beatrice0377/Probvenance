"""Research-only paired transport analysis for the R2 CAT/OVR pilot.

This module is deliberately NOT the production calibrator. It never constructs
a :class:`~probvenance.calibration.CalibrationObservation`, a
``CalibrationDataset``, or a ``CalibrationProfile``: the research object
``fixed-decision-correctness`` is not the frozen ``winner_correctness`` target,
and the research input ``fixed-decision-semantic-probability`` is not
``uncalibrated-selected-probability``.

It reuses only the numerical kernel (``_solve_l2_logistic`` and
``_stable_sigmoid``) so the pilot cannot quietly implement a second, drifting
optimizer. Reusing the numerical kernel is NOT reusing ``CalibrationProfile``
semantics.

The analysis contains no inferential statistics: with 9 training and 6 test
rows it reports descriptive effect direction and magnitude only.
"""

from __future__ import annotations

import importlib.util
import math
import statistics
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from probvenance.calibration import (
    _require_l2_strength,
    _solve_l2_logistic,
    _stable_sigmoid,
)

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


_integrity = _load_sibling("integrity")
Split = _integrity.Split
MeasurementStatus = _integrity.MeasurementStatus
RESEARCH_SPEC_ID = _integrity.RESEARCH_SPEC_ID
RESEARCH_SPEC_VERSION = _integrity.RESEARCH_SPEC_VERSION
FIXED_DECISION_TARGET_ID = _integrity.FIXED_DECISION_TARGET_ID
FIXED_DECISION_TARGET_VERSION = _integrity.FIXED_DECISION_TARGET_VERSION
FIXED_DECISION_INPUT_SCORE_ID = _integrity.FIXED_DECISION_INPUT_SCORE_ID
FIXED_DECISION_INPUT_SCORE_VERSION = _integrity.FIXED_DECISION_INPUT_SCORE_VERSION

PILOT_FITTED_CALIBRATOR_FINGERPRINT_VERSION = 1

RESEARCH_LOGISTIC_METHOD_ID = "research-l2-logistic-fixed-decision-probability"
RESEARCH_LOGISTIC_METHOD_VERSION = 1

#: The single pre-declared regularization strength for this exploratory pilot.
#: It is frozen before any test result is seen; there is no hyperparameter sweep.
PILOT_L2_STRENGTH = 0.01


@dataclass(frozen=True, slots=True)
class PairedPoint:
    """One paired-fit-eligible item's research scores and frozen label."""

    item_id: str
    y: float
    score_a: float
    score_b: float


@dataclass(frozen=True, slots=True)
class PilotFittedCalibrator:
    """A research-only frozen-decision calibrator (NOT a CalibrationProfile).

    Numerically ``q(p) = sigmoid(slope * p + intercept)`` over the research input
    ``fixed-decision-semantic-probability``. It is not storable in the production
    profile store, not selectable by the production selector, and applying it to
    another measurement's score is a deliberate research-only cross-identity
    operation.
    """

    source_measurement: Any
    target_id: str
    target_version: int
    input_score_id: str
    input_score_version: int
    method_id: str
    method_version: int
    l2_strength: float
    plan_fingerprint: str
    training_item_ids: tuple[str, ...]
    slope: float
    intercept: float

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "artifact": "pilot-fitted-calibrator",
            "fingerprint_version": PILOT_FITTED_CALIBRATOR_FINGERPRINT_VERSION,
            "research_spec_id": RESEARCH_SPEC_ID,
            "research_spec_version": RESEARCH_SPEC_VERSION,
            "source_measurement": {
                "measurement_id": self.source_measurement.measurement_id,
                "measurement_version": self.source_measurement.measurement_version,
            },
            "target_id": self.target_id,
            "target_version": self.target_version,
            "input_score_id": self.input_score_id,
            "input_score_version": self.input_score_version,
            "method_id": self.method_id,
            "method_version": self.method_version,
            "l2_strength": self.l2_strength,
            "plan_fingerprint": self.plan_fingerprint,
            "training_item_ids": list(self.training_item_ids),
            "slope": self.slope,
            "intercept": self.intercept,
        }

    @property
    def fingerprint(self) -> str:
        from probvenance.fingerprint import fingerprint

        return fingerprint(self.canonical_payload())

    def apply(self, score: float) -> float:
        """Apply the fixed calibrator to one raw semantic-probability score."""
        return _stable_sigmoid(self.slope * float(score) + self.intercept)


def paired_fit_eligible(row: Any) -> bool:
    """Frozen eligibility: both measurements SCORED, and nothing else.

    Winner agreement, anchor/winner equality, score magnitude, label mass,
    ground-truth class, and any transport result are deliberately NOT consulted.
    """
    return (
        row.outcome_a.status is MeasurementStatus.SCORED
        and row.outcome_b.status is MeasurementStatus.SCORED
    )


def eligible_rows(dataset: Any, *, split: Any) -> tuple[Any, ...]:
    """Eligible rows for one split, sorted deterministically by item id."""
    rows = [row for row in dataset.rows if row.item.split is split and paired_fit_eligible(row)]
    return tuple(sorted(rows, key=lambda row: row.item.item_id))


def scored_points(dataset: Any, *, split: Any) -> tuple[PairedPoint, ...]:
    """Paired eligible points for one split (deterministic item-id order)."""
    points = []
    for row in eligible_rows(dataset, split=split):
        points.append(
            PairedPoint(
                item_id=row.item.item_id,
                y=1.0 if row.item.anchor_correct else 0.0,
                score_a=float(row.outcome_a.anchor_score),
                score_b=float(row.outcome_b.anchor_score),
            )
        )
    return tuple(points)


def fit_pilot_calibrator(
    *,
    source_measurement: Any,
    training_rows: Sequence[tuple[str, float, float]],
    plan_fingerprint: str,
    l2_strength: float = PILOT_L2_STRENGTH,
) -> PilotFittedCalibrator:
    """Fit the research-only L2 logistic calibrator on deterministic rows.

    ``training_rows`` are ``(item_id, score, y)`` tuples. They are sorted by
    ``item_id`` so the arithmetic input order is deterministic and independent
    of caller order. The rows for the two measurements must come from the SAME
    paired training item ids with the same ``y``.
    """
    ordered = sorted(training_rows, key=lambda row: row[0])
    if not ordered:
        raise ValueError("cannot fit a calibrator on zero training rows")
    rows = [(float(score), float(y)) for _item_id, score, y in ordered]
    strength = _require_l2_strength(l2_strength)
    slope, intercept = _solve_l2_logistic(rows, strength)
    if not math.isfinite(slope) or not math.isfinite(intercept):
        raise ValueError(
            f"fitted parameters must be finite, got slope={slope!r} intercept={intercept!r}"
        )
    return PilotFittedCalibrator(
        source_measurement=source_measurement,
        target_id=FIXED_DECISION_TARGET_ID,
        target_version=FIXED_DECISION_TARGET_VERSION,
        input_score_id=FIXED_DECISION_INPUT_SCORE_ID,
        input_score_version=FIXED_DECISION_INPUT_SCORE_VERSION,
        method_id=RESEARCH_LOGISTIC_METHOD_ID,
        method_version=RESEARCH_LOGISTIC_METHOD_VERSION,
        l2_strength=strength,
        plan_fingerprint=plan_fingerprint,
        training_item_ids=tuple(row[0] for row in ordered),
        slope=slope,
        intercept=intercept,
    )


def brier(pairs: Sequence[tuple[float, float]]) -> float:
    """Mean squared error between predicted correctness and label."""
    if not pairs:
        raise ValueError("brier requires at least one pair")
    return math.fsum((float(q) - float(y)) ** 2 for q, y in pairs) / len(pairs)


def _sample_logloss(q: float, y: float) -> float | None:
    """Exact Bernoulli log loss, or ``None`` for a mathematically infinite cell."""
    if y == 1.0:
        return None if q <= 0.0 else -math.log(q)
    return None if q >= 1.0 else -math.log1p(-q)


def exact_logloss(pairs: Sequence[tuple[float, float]]) -> float | None:
    """Exact mean Bernoulli log loss with NO clipping/smoothing.

    Returns ``None`` when any row is mathematically infinite (a prediction is
    exactly 0 or 1 on the wrong side), which the caller renders explicitly.
    """
    if not pairs:
        raise ValueError("exact_logloss requires at least one pair")
    terms: list[float] = []
    for q, y in pairs:
        term = _sample_logloss(float(q), float(y))
        if term is None:
            return None
        terms.append(term)
    return math.fsum(terms) / len(terms)


def loss_cell(value: float | None) -> dict[str, Any]:
    """JSON-safe structured loss cell (never a raw ``Infinity``/``NaN``)."""
    if value is None:
        return {"state": "positive_infinity"}
    return {"state": "finite", "value": value}


def _predict(
    points: Sequence[PairedPoint], calibrator: Any, *, score: str
) -> list[tuple[float, float]]:
    pairs = []
    for point in points:
        raw = point.score_a if score == "a" else point.score_b
        pairs.append((calibrator.apply(raw), point.y))
    return pairs


def brier_matrix(points: Sequence[PairedPoint], g_a: Any, g_b: Any) -> dict[str, Any]:
    """The full 2x2 Brier matrix plus both empirical transport excess risks.

    Orientation: ``fit_a_eval_b`` is ``g_a`` (fitted on measurement A) applied to
    measurement B's held-out scores. The signs are only descriptive.
    """
    fit_a_eval_a = brier(_predict(points, g_a, score="a"))
    fit_a_eval_b = brier(_predict(points, g_a, score="b"))
    fit_b_eval_a = brier(_predict(points, g_b, score="a"))
    fit_b_eval_b = brier(_predict(points, g_b, score="b"))
    raw_a = brier([(p.score_a, p.y) for p in points])
    raw_b = brier([(p.score_b, p.y) for p in points])
    return {
        "fit_a_eval_a": fit_a_eval_a,
        "fit_a_eval_b": fit_a_eval_b,
        "fit_b_eval_a": fit_b_eval_a,
        "fit_b_eval_b": fit_b_eval_b,
        "raw_a": raw_a,
        "raw_b": raw_b,
        "delta_a_to_b": fit_a_eval_b - fit_b_eval_b,
        "delta_b_to_a": fit_b_eval_a - fit_a_eval_a,
    }


def logloss_matrix(points: Sequence[PairedPoint], g_a: Any, g_b: Any) -> dict[str, Any]:
    """The full 2x2 exact-LogLoss matrix, rendered as structured JSON-safe cells."""
    return {
        "fit_a_eval_a": loss_cell(exact_logloss(_predict(points, g_a, score="a"))),
        "fit_a_eval_b": loss_cell(exact_logloss(_predict(points, g_a, score="b"))),
        "fit_b_eval_a": loss_cell(exact_logloss(_predict(points, g_b, score="a"))),
        "fit_b_eval_b": loss_cell(exact_logloss(_predict(points, g_b, score="b"))),
        "raw_a": loss_cell(exact_logloss([(p.score_a, p.y) for p in points])),
        "raw_b": loss_cell(exact_logloss([(p.score_b, p.y) for p in points])),
    }


def _range_summary(values: Sequence[float]) -> dict[str, Any]:
    ordered = sorted(float(v) for v in values)
    summary: dict[str, Any] = {
        "n": len(ordered),
        "min": ordered[0],
        "max": ordered[-1],
        "median": statistics.median(ordered),
    }
    if len(ordered) >= 2:
        q1, _q2, q3 = statistics.quantiles(ordered, n=4, method="inclusive")
        summary["q25"] = q1
        summary["q75"] = q3
    return summary


def observed_range_diagnostics(
    train_points: Sequence[PairedPoint],
    test_points: Sequence[PairedPoint],
) -> dict[str, Any]:
    """Empirical observed-range diagnostics (NOT a support theorem).

    Cross application ``A->B`` applies a calibrator fitted on A to B scores, so
    the relevant question is how far B's test scores move outside A's observed
    TRAIN range, and symmetrically for ``B->A``.
    """
    train_a = [p.score_a for p in train_points]
    train_b = [p.score_b for p in train_points]
    test_a = [p.score_a for p in test_points]
    test_b = [p.score_b for p in test_points]

    def outside(values: Sequence[float], lo: float, hi: float) -> float:
        if not values:
            return 0.0
        count = sum(1 for v in values if v < lo or v > hi)
        return count / len(values)

    return {
        "train_a": _range_summary(train_a),
        "train_b": _range_summary(train_b),
        "test_a": _range_summary(test_a),
        "test_b": _range_summary(test_b),
        "test_b_outside_train_a_range_fraction": outside(test_b, min(train_a), max(train_a)),
        "test_a_outside_train_b_range_fraction": outside(test_a, min(train_b), max(train_b)),
    }


def winner_diagnostics(
    *,
    truth_by_item: Mapping[str, str],
    winner_a_by_item: Mapping[str, str],
    winner_b_by_item: Mapping[str, str],
) -> dict[str, Any]:
    """End-to-end descriptive winner diagnostics (secondary, not the estimand)."""
    item_ids = sorted(truth_by_item)
    if not item_ids:
        raise ValueError("winner_diagnostics requires at least one item")
    correct_a = sum(1 for i in item_ids if winner_a_by_item[i] == truth_by_item[i])
    correct_b = sum(1 for i in item_ids if winner_b_by_item[i] == truth_by_item[i])
    agree = sum(1 for i in item_ids if winner_a_by_item[i] == winner_b_by_item[i])
    return {
        "n": len(item_ids),
        "winner_a_accuracy": correct_a / len(item_ids),
        "winner_b_accuracy": correct_b / len(item_ids),
        "winner_agreement_fraction": agree / len(item_ids),
    }


def ovr_non_simplex_diagnostics(
    candidate_score_sums: Sequence[float], over_half_counts: Sequence[int]
) -> dict[str, Any]:
    """Measurement-semantics diagnostic: OVR scores are not a simplex distribution."""
    if not candidate_score_sums:
        raise ValueError("ovr_non_simplex_diagnostics requires at least one item")
    return {
        "n": len(candidate_score_sums),
        "candidate_score_sum_min": min(candidate_score_sums),
        "candidate_score_sum_mean": math.fsum(candidate_score_sums) / len(candidate_score_sums),
        "candidate_score_sum_max": max(candidate_score_sums),
        "items_with_multiple_candidates_over_half": sum(
            1 for count in over_half_counts if count > 1
        ),
    }
