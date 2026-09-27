"""R3 pre-outcome confirmatory analysis implementation.

This module implements the R3 analysis that ``R3_PROTOCOL.md`` freezes, *before*
any R3 model outcome exists. It runs entirely on synthetic fixtures in R3.0; the
official run is a later, separately authorized step. It contains **no** model
loading and **no** measurement runner.

Primary quantity (cross-vs-raw, procedure-conditioned):

    C_d(F) = R_cross(A->B;F) - R_raw(B)

with Brier as the primary metric. The three baselines are always reported
together; a negative cross-vs-native delta is never interpreted as transport
success. The primary contrasts are the six factorial contrasts (feature,
regularization, interaction for each direction) on the PRIMARY model condition,
with a subject-stratified paired TEST bootstrap and Bonferroni multiplicity.

It reuses only the numerical kernel (``_solve_l2_logistic`` and
``_stable_sigmoid``) from the production package; it never constructs a
``CalibrationProfile``. Family ``L`` fails closed on exact 0/1 scores (no
clipping, no epsilon, no smoothing).
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from probvenance.calibration import _solve_l2_logistic, _stable_sigmoid
from probvenance.fingerprint import fingerprint

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


_protocol = _load_sibling("r3_protocol")
_population = _load_sibling("r3_population")
_integrity = _load_sibling("integrity")

#: The frozen raw-evidence status of a block that carries a recorded native winner.
_SCORED_STATUS = _integrity.MeasurementStatus.SCORED.value

R3_ANALYSIS_ARTIFACT_TYPE = "r3-confirmatory-analysis"
R3_ANALYSIS_VERSION = 1
R3_ANALYSIS_FINGERPRINT_VERSION = 1

R3_FITTED_CALIBRATOR_FINGERPRINT_VERSION = 1

MEASUREMENT_CAT = "CAT"
MEASUREMENT_OVR = "OVR"

DIRECTION_CAT_TO_OVR = "CAT->OVR"
DIRECTION_OVR_TO_CAT = "OVR->CAT"

EFFECT_FEATURE = "feature"
EFFECT_REGULARIZATION = "regularization"
EFFECT_INTERACTION = "interaction"

PRIMARY_PERCENTILES: tuple[float, ...] = (100.0 / 240.0, 50.0, 100.0 * 239.0 / 240.0)
NATIVE_PERCENTILES: tuple[float, ...] = (100.0 / 320.0, 50.0, 100.0 * 319.0 / 320.0)

RELIABILITY_BIN_COUNT = 10
QUANTILE_LOWER = 2.5
QUANTILE_UPPER = 97.5

# Frozen R3_PROTOCOL.md §17 unit: within each subject, resample exactly this
# many TRAIN item positions with replacement (the TRAIN pool itself has 8).
TRAIN_REFIT_DRAWS_PER_SUBJECT = 10

# Frozen R3_PROTOCOL.md §17 failure contract: a procedure/model block with any
# failed refit is INCOMPLETE and must never receive a successful-subset interval;
# unaffected procedure blocks remain reportable.
TRAIN_REFIT_STATUS_COMPLETE = "COMPLETE"
TRAIN_REFIT_STATUS_INCOMPLETE = "INCOMPLETE"

STATE_IMPROVEMENT = "NATIVE_IMPROVEMENT_SUPPORTED"
STATE_DEGRADATION = "NATIVE_DEGRADATION_SUPPORTED"
STATE_UNRESOLVED = "NATIVE_ADEQUACY_UNRESOLVED"


class AnalysisError(ValueError):
    """Raised when the R3 analysis input violates its frozen contract."""


class ProbabilityEndpointError(AnalysisError):
    """Raised when a Family L feature is an exact 0/1 probability."""


# --------------------------------------------------------------------------- #
# Losses
# --------------------------------------------------------------------------- #


def _logit(probability: float) -> float:
    if probability <= 0.0 or probability >= 1.0:
        raise ProbabilityEndpointError(
            f"exact probability endpoint {probability!r} cannot be transformed"
        )
    return math.log(probability / (1.0 - probability))


def feature_value(feature_id: str, probability: float) -> float:
    if feature_id == _protocol.FEATURE_P_ID:
        return probability
    if feature_id == _protocol.FEATURE_L_ID:
        return _logit(probability)
    raise AnalysisError(f"unknown feature id {feature_id!r}")


def brier(pairs: Sequence[tuple[float, float]]) -> float:
    return math.fsum((probability - label) ** 2 for probability, label in pairs) / len(pairs)


def brier_loss(probability: float, label: float) -> float:
    """The per-item Brier loss, exposed so callers need no inline lambda."""
    return (probability - label) ** 2


def exact_logloss(pairs: Sequence[tuple[float, float]]) -> float | None:
    total = 0.0
    for probability, label in pairs:
        if label == 1.0 and probability <= 0.0:
            return None
        if label == 0.0 and probability >= 1.0:
            return None
        total += -(label * math.log(probability) + (1.0 - label) * math.log(1.0 - probability))
    return total / len(pairs)


def loss_cell(value: float | None) -> dict[str, Any]:
    if value is None:
        return {"state": "positive_infinity"}
    return {"state": "finite", "value": value}


# --------------------------------------------------------------------------- #
# Calibrators and panel fitting
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class R3FittedCalibrator:
    procedure_label: str
    procedure_fingerprint: str
    source_measurement: str
    feature_id: str
    feature_version: int
    l2_strength: float
    slope: float
    intercept: float
    training_item_ids: tuple[str, ...]

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "fingerprint_version": R3_FITTED_CALIBRATOR_FINGERPRINT_VERSION,
            "procedure_label": self.procedure_label,
            "procedure_fingerprint": self.procedure_fingerprint,
            "source_measurement": self.source_measurement,
            "feature_id": self.feature_id,
            "feature_version": self.feature_version,
            "l2_strength": self.l2_strength,
            "slope": self.slope,
            "intercept": self.intercept,
            "training_item_ids": list(self.training_item_ids),
        }

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.canonical_payload())

    def apply(self, probability: float) -> float:
        return _stable_sigmoid(
            self.slope * feature_value(self.feature_id, probability) + self.intercept
        )


def fit_calibrator(
    procedure: Any,
    source_measurement: str,
    training_points: Sequence[tuple[str, float, float]],
) -> R3FittedCalibrator:
    """Fit ``F`` on one measurement's TRAIN scores; fail closed on L endpoints."""
    ordered = sorted(training_points, key=lambda point: point[0])
    rows: list[tuple[float, float]] = []
    for _, score, label in ordered:
        rows.append((feature_value(procedure.feature_id, score), label))
    slope, intercept = _solve_l2_logistic(rows, procedure.l2_strength)
    if not (math.isfinite(slope) and math.isfinite(intercept)):
        raise AnalysisError("calibrator parameters are not finite")
    return R3FittedCalibrator(
        procedure_label=procedure.label,
        procedure_fingerprint=procedure.fingerprint,
        source_measurement=source_measurement,
        feature_id=procedure.feature_id,
        feature_version=procedure.feature_version,
        l2_strength=procedure.l2_strength,
        slope=slope,
        intercept=intercept,
        training_item_ids=tuple(point[0] for point in ordered),
    )


@dataclass(frozen=True, slots=True)
class R3PanelFit:
    """The four-procedure panel fitted on both measurements of one model."""

    calibrators: Mapping[tuple[str, str], R3FittedCalibrator]

    def get(self, procedure_label: str, measurement: str) -> R3FittedCalibrator:
        return self.calibrators[(procedure_label, measurement)]

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "fingerprint_version": R3_ANALYSIS_FINGERPRINT_VERSION,
            "calibrators": {
                f"{label}|{measurement}": calibrator.canonical_payload()
                for (label, measurement), calibrator in sorted(self.calibrators.items())
            },
        }


# --------------------------------------------------------------------------- #
# Item model
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class R3Item:
    """One paired TEST/TRAIN record for one model condition."""

    item_id: str
    subject: str
    label: float
    cat_score: float
    ovr_score: float


@dataclass(frozen=True, slots=True)
class R3WinnerRecord:
    """One row's recorded native winners and ground truth.

    Held separately from :class:`R3Item` so fixed-decision probability data and
    end-to-end winner data are never conflated. Every value is read verbatim from
    the frozen raw evidence; no winner is derived from an anchor score, a 0.5
    threshold, or a calibrated probability.
    """

    item_id: str
    ground_truth_value: str
    cat_winner: str
    ovr_winner: str


def fit_panel(
    train_items: Sequence[R3Item],
    procedures: Sequence[Any],
) -> R3PanelFit:
    calibrators: dict[tuple[str, str], R3FittedCalibrator] = {}
    for procedure in procedures:
        for measurement, score_of in (
            (MEASUREMENT_CAT, lambda item: item.cat_score),
            (MEASUREMENT_OVR, lambda item: item.ovr_score),
        ):
            points = [(item.item_id, score_of(item), item.label) for item in train_items]
            calibrators[(procedure.label, measurement)] = fit_calibrator(
                procedure, measurement, points
            )
    return R3PanelFit(calibrators)


def _direction_target(direction: str) -> str:
    return MEASUREMENT_OVR if direction == DIRECTION_CAT_TO_OVR else MEASUREMENT_CAT


def _direction_source(direction: str) -> str:
    return MEASUREMENT_CAT if direction == DIRECTION_CAT_TO_OVR else MEASUREMENT_OVR


def direction_scores(item: R3Item, direction: str) -> tuple[float, float]:
    """Return ``(target_measurement_score, source_measurement_score)``.

    The TARGET leg ``S_B`` is the measurement a risk is evaluated on; the SOURCE
    leg ``S_A`` is the measurement whose calibrator ``g_A`` was fitted.
    """
    if direction == DIRECTION_CAT_TO_OVR:
        return item.ovr_score, item.cat_score
    return item.cat_score, item.ovr_score


def _target_score(item: R3Item, direction: str) -> float:
    return direction_scores(item, direction)[0]


def _source_score(item: R3Item, direction: str) -> float:
    return direction_scores(item, direction)[1]


def _cross_prediction(
    item: R3Item,
    panel: R3PanelFit,
    procedure_label: str,
    direction: str,
) -> float:
    """The frozen cross application ``g_F^A(S_B)``.

    ``R_cross(A->B;F) = loss(g_F^A(S_B_i), Y_i)``: the SOURCE-fitted calibrator
    ``g_A`` is applied to the TARGET measurement score ``S_B``, never to the
    source score ``S_A``. Every cross prediction path routes through here.
    """
    source = _direction_source(direction)
    return panel.get(procedure_label, source).apply(_target_score(item, direction))


def _cross_predictions(
    items: Sequence[R3Item],
    panel: R3PanelFit,
    procedure_label: str,
    direction: str,
) -> list[tuple[float, float]]:
    return [
        (_cross_prediction(item, panel, procedure_label, direction), item.label) for item in items
    ]


def _raw_loss(item: R3Item, direction: str, loss: Callable[..., float]) -> float:
    return loss(_target_score(item, direction), item.label)


def _native_loss(
    item: R3Item,
    panel: R3PanelFit,
    procedure_label: str,
    direction: str,
    loss: Callable[..., float],
) -> float:
    target = _direction_target(direction)
    prediction = panel.get(procedure_label, target).apply(_target_score(item, direction))
    return loss(prediction, item.label)


def _cross_loss(
    item: R3Item,
    panel: R3PanelFit,
    procedure_label: str,
    direction: str,
    loss: Callable[..., float],
) -> float:
    return loss(_cross_prediction(item, panel, procedure_label, direction), item.label)


# --------------------------------------------------------------------------- #
# Subject-weighted means and contrasts
# --------------------------------------------------------------------------- #


def _per_subject_means(
    items: Sequence[R3Item], value_of: Callable[[R3Item], float]
) -> dict[str, float]:
    grouped: dict[str, list[float]] = {}
    for item in items:
        grouped.setdefault(item.subject, []).append(value_of(item))
    return {subject: math.fsum(values) / len(values) for subject, values in grouped.items()}


def subject_weighted_mean(items: Sequence[R3Item], value_of: Callable[[R3Item], float]) -> float:
    """Equal-subject mean of per-subject means (the frozen weighting contract)."""
    means = _per_subject_means(items, value_of)
    return math.fsum(means.values()) / len(means)


def procedure_labels(procedures: Sequence[Any]) -> tuple[str, ...]:
    return tuple(procedure.label for procedure in procedures)


def cross_vs_raw_values(
    items: Sequence[R3Item], panel: R3PanelFit, procedures: Sequence[Any], direction: str
) -> dict[str, float]:
    """``C_d(F)`` per procedure (per-item loss diff, subject-weighted)."""
    return {
        procedure.label: subject_weighted_mean(
            items,
            lambda item, procedure=procedure: (
                _cross_loss(item, panel, procedure.label, direction, brier_loss)
                - _raw_loss(item, direction, brier_loss)
            ),
        )
        for procedure in procedures
    }


def factorial_contrasts(cross_values: Mapping[str, float]) -> dict[str, float]:
    p_low = cross_values[_protocol.PROCEDURE_P_LOW]
    p_hist = cross_values[_protocol.PROCEDURE_P_HISTORICAL]
    l_low = cross_values[_protocol.PROCEDURE_L_LOW]
    l_hist = cross_values[_protocol.PROCEDURE_L_HISTORICAL]
    return {
        EFFECT_FEATURE: 0.5 * (l_low + l_hist - p_low - p_hist),
        EFFECT_REGULARIZATION: 0.5 * (p_low + l_low - p_hist - l_hist),
        EFFECT_INTERACTION: (l_low - p_low) - (l_hist - p_hist),
    }


def risk_matrix(
    items: Sequence[R3Item], panel: R3PanelFit, procedures: Sequence[Any], direction: str
) -> dict[str, Any]:
    """Risk-matrix path (independent calculation path 1): risks, then contrasts."""
    raw = subject_weighted_mean(items, lambda item: _raw_loss(item, direction, brier_loss))
    cross = {
        procedure.label: subject_weighted_mean(
            items,
            lambda item, procedure=procedure: _cross_loss(
                item, panel, procedure.label, direction, brier_loss
            ),
        )
        for procedure in procedures
    }
    cross_values = {label: cross[label] - raw for label in cross}
    return {"raw": raw, "cross": cross, "cross_vs_raw": cross_values}


# --------------------------------------------------------------------------- #
# Deterministic bootstrap
# --------------------------------------------------------------------------- #


def _draw_index(
    *,
    protocol_id: str,
    protocol_version: int,
    replicate: int,
    subject: str,
    draw: int,
    item_count: int,
) -> int:
    digest = fingerprint(
        {
            "protocol_id": protocol_id,
            "protocol_version": protocol_version,
            "replicate": replicate,
            "subject": subject,
            "draw": draw,
            "item_count": item_count,
        }
    )
    return int(digest, 16) % item_count


def _grouped_by_subject(items: Sequence[R3Item]) -> dict[str, list[R3Item]]:
    grouped: dict[str, list[R3Item]] = {}
    for item in items:
        grouped.setdefault(item.subject, []).append(item)
    return grouped


def bootstrap_subject_statistic(
    items: Sequence[R3Item],
    value_of: Callable[[R3Item], float],
    *,
    replicates: int,
    protocol_id: str,
    protocol_version: int,
) -> list[float]:
    """Subject-stratified paired bootstrap of an equal-subject mean."""
    grouped = _grouped_by_subject(items)
    subjects = sorted(grouped)
    sizes = {subject: len(grouped[subject]) for subject in subjects}
    values = {subject: [value_of(item) for item in grouped[subject]] for subject in subjects}
    samples: list[float] = []
    for replicate in range(replicates):
        subject_means: list[float] = []
        for subject in subjects:
            count = sizes[subject]
            total = 0.0
            for draw in range(count):
                index = _draw_index(
                    protocol_id=protocol_id,
                    protocol_version=protocol_version,
                    replicate=replicate,
                    subject=subject,
                    draw=draw,
                    item_count=count,
                )
                total += values[subject][index]
            subject_means.append(total / count)
        samples.append(math.fsum(subject_means) / len(subject_means))
    return samples


def nearest_rank_percentile(ordered_values: Sequence[float], percentile: float) -> float:
    if not ordered_values:
        raise AnalysisError("cannot take a percentile of an empty sample")
    rank = math.ceil(percentile / 100.0 * len(ordered_values))
    rank = min(max(rank, 1), len(ordered_values))
    return ordered_values[rank - 1]


def _interval(samples: Sequence[float], percentiles: Sequence[float]) -> dict[str, float]:
    ordered = sorted(samples)
    lower, median, upper = (
        nearest_rank_percentile(ordered, percentiles[0]),
        nearest_rank_percentile(ordered, percentiles[1]),
        nearest_rank_percentile(ordered, percentiles[2]),
    )
    return {
        "n": len(samples),
        "lower": lower,
        "median": median,
        "upper": upper,
        "excludes_zero": (lower > 0.0) or (upper < 0.0),
    }


# --------------------------------------------------------------------------- #
# Secondary diagnostics
# --------------------------------------------------------------------------- #


def reliability_diagnostics(
    items: Sequence[R3Item], panel: R3PanelFit, procedures: Sequence[Any], direction: str
) -> dict[str, Any]:
    target = _direction_target(direction)

    def bins_of(predictor: Callable[[R3Item], float]) -> list[dict[str, Any]]:
        buckets: list[list[tuple[float, float]]] = [[] for _ in range(RELIABILITY_BIN_COUNT)]
        for item in items:
            probability = predictor(item)
            index = min(int(probability * RELIABILITY_BIN_COUNT), RELIABILITY_BIN_COUNT - 1)
            buckets[index].append((probability, item.label))
        result = []
        for index, bucket in enumerate(buckets):
            if bucket:
                mean_probability = math.fsum(p for p, _ in bucket) / len(bucket)
                mean_label = math.fsum(y for _, y in bucket) / len(bucket)
            else:
                mean_probability = None
                mean_label = None
            result.append(
                {
                    "bin": index,
                    "count": len(bucket),
                    "mean_probability": mean_probability,
                    "mean_label": mean_label,
                }
            )
        return result

    return {
        "raw": bins_of(lambda item: _target_score(item, direction)),
        "native": {
            procedure.label: bins_of(
                lambda item, procedure=procedure: panel.get(procedure.label, target).apply(
                    _target_score(item, direction)
                )
            )
            for procedure in procedures
        },
        "cross": {
            procedure.label: bins_of(
                lambda item, procedure=procedure: _cross_prediction(
                    item, panel, procedure.label, direction
                )
            )
            for procedure in procedures
        },
    }


def score_geometry(
    train_items: Sequence[R3Item], test_items: Sequence[R3Item], direction: str
) -> dict[str, Any]:
    """Observed SOURCE TRAIN vs TARGET TEST empirical score geometry.

    The SOURCE is the fitting measurement's TRAIN scores; the TARGET is the
    other measurement's TEST scores. Source support is never inferred from TEST,
    and the 2.5-97.5% range reuses the already-frozen R3
    ``nearest-rank-percentile`` v1 rule. Empirical diagnostic, not a support
    theorem.
    """
    source_train_scores = sorted(float(_source_score(item, direction)) for item in train_items)
    if not source_train_scores:
        raise AnalysisError("score geometry requires at least one SOURCE TRAIN item")
    target_test_scores = [_target_score(item, direction) for item in test_items]
    source_min, source_max = source_train_scores[0], source_train_scores[-1]
    source_q2_5 = nearest_rank_percentile(source_train_scores, QUANTILE_LOWER)
    source_q97_5 = nearest_rank_percentile(source_train_scores, QUANTILE_UPPER)
    return {
        "direction": direction,
        "source_measurement": _direction_source(direction),
        "target_measurement": _direction_target(direction),
        "source_train_count": len(source_train_scores),
        "source_train_min": source_min,
        "source_train_max": source_max,
        "source_train_q2_5": source_q2_5,
        "source_train_q97_5": source_q97_5,
        "target_test_count": len(target_test_scores),
        "target_test_fraction_outside_source_train_min_max": _fraction_outside(
            target_test_scores, source_min, source_max
        ),
        "target_test_fraction_outside_source_train_q2_5_q97_5": _fraction_outside(
            target_test_scores, source_q2_5, source_q97_5
        ),
    }


def _fraction_outside(values: Sequence[float], low: float, high: float) -> float:
    outside = sum(1 for value in values if value < low or value > high)
    return outside / len(values)


def range_loss_decomposition(
    train_items: Sequence[R3Item],
    test_items: Sequence[R3Item],
    panel: R3PanelFit,
    procedures: Sequence[Any],
    direction: str,
) -> dict[str, Any]:
    """Decompose the declared cross-vs-raw contrast by SOURCE TRAIN range.

    The region boundary is the SOURCE TRAIN observed ``[min, max]`` and each
    TARGET TEST row is scored with the frozen cross prediction
    ``g_SOURCE(S_TARGET)``. The decomposed risk difference basis (cross vs raw)
    is unchanged; only the boundary source and the cross application are brought
    into conformance with the frozen protocol. Empirical, not causal.
    """
    source_train_scores = [_source_score(item, direction) for item in train_items]
    if not source_train_scores:
        raise AnalysisError("range decomposition requires at least one SOURCE TRAIN item")
    low, high = min(source_train_scores), max(source_train_scores)
    result: dict[str, Any] = {}
    for procedure in procedures:
        inside: list[float] = []
        outside: list[float] = []
        for item in test_items:
            target_score = _target_score(item, direction)
            prediction = _cross_prediction(item, panel, procedure.label, direction)
            diff = brier_loss(prediction, item.label) - brier_loss(target_score, item.label)
            (inside if low <= target_score <= high else outside).append(diff)
        result[procedure.label] = {
            "source_train_min": low,
            "source_train_max": high,
            "n_in": len(inside),
            "n_out": len(outside),
            "mean_in": (math.fsum(inside) / len(inside)) if inside else None,
            "mean_out": (math.fsum(outside) / len(outside)) if outside else None,
            "in_contribution": math.fsum(inside) / len(test_items),
            "out_contribution": math.fsum(outside) / len(test_items),
        }
    return result


def _recorded_native_winner(evidence_item: Mapping[str, Any], measurement: str) -> str:
    item_id = evidence_item.get("item_id")
    block = evidence_item.get(measurement)
    if not isinstance(block, Mapping):
        raise AnalysisError(f"item {item_id} lacks a {measurement} evidence block")
    if block.get("status") != _SCORED_STATUS:
        raise AnalysisError(
            f"item {item_id} {measurement} is not SCORED; no native winner is available"
        )
    record = block.get("record")
    if not isinstance(record, Mapping) or not record.get("winner"):
        raise AnalysisError(f"item {item_id} SCORED {measurement} lacks its recorded native winner")
    return str(record["winner"])


def winner_record_from_evidence(evidence_item: Mapping[str, Any]) -> R3WinnerRecord:
    """Map one frozen raw-evidence item onto its winner-diagnostic record.

    The CAT/OVR winners are read verbatim from ``cat.record.winner`` and
    ``ovr.record.winner`` together with the recorded ``ground_truth_value``; the
    anchor score, any candidate-score threshold, and any calibrated probability
    are never consulted. A structurally SCORED block whose recorded winner is
    missing is an integrity error and fails closed.
    """
    return R3WinnerRecord(
        item_id=str(evidence_item.get("item_id")),
        ground_truth_value=str(evidence_item.get("ground_truth_value")),
        cat_winner=_recorded_native_winner(evidence_item, "cat"),
        ovr_winner=_recorded_native_winner(evidence_item, "ovr"),
    )


def end_to_end_diagnostics(records: Sequence[R3WinnerRecord]) -> dict[str, Any]:
    """Frozen §16 end-to-end winner diagnostics on the recorded native winners.

    Each protocol's own-winner accuracy compares its recorded native winner with
    the ground truth, and winner agreement compares the two recorded native
    winners directly. No anchor probability, threshold, or calibrated score
    participates: this is decision behaviour, not the per-item estimand.
    """
    if not records:
        raise AnalysisError("end-to-end winner diagnostics require at least one record")
    count = len(records)
    cat_correct = sum(1 for row in records if row.cat_winner == row.ground_truth_value)
    ovr_correct = sum(1 for row in records if row.ovr_winner == row.ground_truth_value)
    agreement = sum(1 for row in records if row.cat_winner == row.ovr_winner)
    return {
        "n": count,
        "cat_own_winner_accuracy": cat_correct / count,
        "ovr_own_winner_accuracy": ovr_correct / count,
        "winner_agreement": agreement / count,
    }


def _require_winner_population(
    test_items: Sequence[R3Item], winner_records: Sequence[R3WinnerRecord]
) -> None:
    """Frozen §16: winner diagnostics use exactly the eligible fixed TEST rows."""
    item_ids = [item.item_id for item in test_items]
    winner_ids = [record.item_id for record in winner_records]
    if len(winner_ids) != len(item_ids) or set(winner_ids) != set(item_ids):
        raise AnalysisError("winner records must cover exactly the fixed TEST item population")


# --------------------------------------------------------------------------- #
# Assembled analysis
# --------------------------------------------------------------------------- #


def analyze_model_condition(
    *,
    model_id: str,
    model_revision: str,
    train_items: Sequence[R3Item],
    test_items: Sequence[R3Item],
    test_winner_records: Sequence[R3WinnerRecord],
    procedures: Sequence[Any],
    test_replicates: int = _protocol.TEST_BOOTSTRAP_REPLICATES,
    train_refit_replicates: int = _protocol.TRAIN_REFIT_BOOTSTRAP_REPLICATES,
) -> dict[str, Any]:
    """Full predeclared analysis for one model condition (synthetic-runnable)."""
    _require_winner_population(test_items, test_winner_records)
    panel = fit_panel(train_items, procedures)
    labels = procedure_labels(procedures)

    directions: dict[str, Any] = {}
    for direction in _protocol.PRIMARY_DIRECTIONS:
        path1 = risk_matrix(test_items, panel, procedures, direction)
        path2 = cross_vs_raw_values(test_items, panel, procedures, direction)
        for label in labels:
            if not math.isclose(
                path1["cross_vs_raw"][label], path2[label], rel_tol=0.0, abs_tol=1e-12
            ):
                raise AnalysisError("independent calculation paths disagree on cross-vs-raw")
        cross_values = {label: path2[label] for label in labels}
        contrasts = factorial_contrasts(cross_values)
        direction_block: dict[str, Any] = {
            "raw_risk_brier": path1["raw"],
            "cross_risk_brier": path1["cross"],
            "cross_vs_raw": cross_values,
            "factorial_contrasts": contrasts,
            "cross_vs_native": {
                label: subject_weighted_mean(
                    test_items,
                    lambda item, label=label, direction=direction: (
                        _cross_loss(item, panel, label, direction, brier_loss)
                        - _native_loss(item, panel, label, direction, brier_loss)
                    ),
                )
                for label in labels
            },
            "native_vs_raw": {
                label: subject_weighted_mean(
                    test_items,
                    lambda item, label=label, direction=direction: (
                        _native_loss(item, panel, label, direction, brier_loss)
                        - _raw_loss(item, direction, brier_loss)
                    ),
                )
                for label in labels
            },
            "exact_logloss": {
                "raw": loss_cell(
                    exact_logloss(
                        [(_target_score(item, direction), item.label) for item in test_items]
                    )
                ),
                "native": {
                    label: loss_cell(
                        exact_logloss(
                            [
                                (
                                    panel.get(label, _direction_target(direction)).apply(
                                        _target_score(item, direction)
                                    ),
                                    item.label,
                                )
                                for item in test_items
                            ]
                        )
                    )
                    for label in labels
                },
                "cross": {
                    label: loss_cell(
                        exact_logloss(_cross_predictions(test_items, panel, label, direction))
                    )
                    for label in labels
                },
            },
            "bootstrap_contrast_intervals": _bootstrap_contrasts(
                test_items, panel, procedures, direction, replicates=test_replicates
            ),
            "score_geometry": score_geometry(train_items, test_items, direction),
            "range_loss_decomposition": range_loss_decomposition(
                train_items, test_items, panel, procedures, direction
            ),
            "reliability": reliability_diagnostics(test_items, panel, procedures, direction),
        }
        directions[direction] = direction_block

    native_reference = _native_reference(test_items, panel, procedures, replicates=test_replicates)
    train_refit = _train_refit_stability(
        train_items, test_items, procedures, replicates=train_refit_replicates
    )

    return {
        "model_id": model_id,
        "model_revision": model_revision,
        "panel": panel.canonical_payload(),
        "directions": directions,
        "native_reference": native_reference,
        "train_refit_stability": train_refit,
        "end_to_end": end_to_end_diagnostics(test_winner_records),
    }


def _bootstrap_contrasts(
    test_items: Sequence[R3Item],
    panel: R3PanelFit,
    procedures: Sequence[Any],
    direction: str,
    *,
    replicates: int,
) -> dict[str, Any]:
    cross_samples: dict[str, list[float]] = {}
    for label in procedure_labels(procedures):
        cross_samples[label] = bootstrap_subject_statistic(
            test_items,
            lambda item, label=label, direction=direction: _cross_loss(
                item, panel, label, direction, brier_loss
            ),
            replicates=replicates,
            protocol_id=_protocol.TEST_BOOTSTRAP_ID,
            protocol_version=_protocol.TEST_BOOTSTRAP_VERSION,
        )
    feature: list[float] = []
    regularization: list[float] = []
    interaction: list[float] = []
    for index in range(replicates):
        values = {label: samples[index] for label, samples in cross_samples.items()}
        contrasts = factorial_contrasts(values)
        feature.append(contrasts[EFFECT_FEATURE])
        regularization.append(contrasts[EFFECT_REGULARIZATION])
        interaction.append(contrasts[EFFECT_INTERACTION])
    by_effect = {
        EFFECT_FEATURE: feature,
        EFFECT_REGULARIZATION: regularization,
        EFFECT_INTERACTION: interaction,
    }
    return {
        effect: _interval(samples, PRIMARY_PERCENTILES) for effect, samples in by_effect.items()
    }


def _native_reference(
    test_items: Sequence[R3Item], panel: R3PanelFit, procedures: Sequence[Any], *, replicates: int
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for measurement in (MEASUREMENT_CAT, MEASUREMENT_OVR):
        direction = DIRECTION_CAT_TO_OVR if measurement == MEASUREMENT_OVR else DIRECTION_OVR_TO_CAT
        for procedure in procedures:
            values = [
                _native_loss(item, panel, procedure.label, direction, brier_loss)
                - _raw_loss(item, direction, brier_loss)
                for item in test_items
            ]
            by_item = {item.item_id: value for item, value in zip(test_items, values, strict=True)}
            value_of = lambda item, by_item=by_item: by_item[item.item_id]  # noqa: E731 - bound lookup
            point = subject_weighted_mean(test_items, value_of)
            samples = bootstrap_subject_statistic(
                test_items,
                value_of,
                replicates=replicates,
                protocol_id=_protocol.TEST_BOOTSTRAP_ID,
                protocol_version=_protocol.TEST_BOOTSTRAP_VERSION,
            )
            interval = _interval(samples, NATIVE_PERCENTILES)
            if interval["upper"] < 0.0:
                state = STATE_IMPROVEMENT
            elif interval["lower"] > 0.0:
                state = STATE_DEGRADATION
            else:
                state = STATE_UNRESOLVED
            result[f"{procedure.label}|{measurement}"] = {
                "point": point,
                "interval": interval,
                "state": state,
            }
    return result


def resample_train_multiset(
    train_items: Sequence[R3Item],
    *,
    replicate: int,
    draws_per_subject: int = TRAIN_REFIT_DRAWS_PER_SUBJECT,
) -> list[R3Item]:
    """Deterministically resample the frozen TRAIN pool for one replicate.

    Within each subject, draw exactly ``draws_per_subject`` item positions with
    replacement from that subject's frozen TRAIN members (the frozen R3 §17
    unit). The returned multiset is the single paired record list that feeds
    both CAT and OVR, and all four ``F`` refits, for the replicate.
    """
    grouped = _grouped_by_subject(train_items)
    resampled: list[R3Item] = []
    for subject in sorted(grouped):
        members = grouped[subject]
        for draw in range(draws_per_subject):
            index = _draw_index(
                protocol_id=_protocol.TRAIN_REFIT_BOOTSTRAP_ID,
                protocol_version=_protocol.TRAIN_REFIT_BOOTSTRAP_VERSION,
                replicate=replicate,
                subject=subject,
                draw=draw,
                item_count=len(members),
            )
            resampled.append(members[index])
    return resampled


def _train_refit_stability(
    train_items: Sequence[R3Item],
    test_items: Sequence[R3Item],
    procedures: Sequence[Any],
    *,
    replicates: int,
) -> dict[str, Any]:
    """Frozen §17 TRAIN-refit stability under a procedure-level fail-closed contract.

    One deterministic resampled TRAIN multiset is drawn per replicate and reused
    for every procedure. Each procedure is refit independently (its CAT and OVR
    calibrators together); a procedure refit failure is recorded against that
    procedure alone and never suppresses another procedure. Any nonzero failure
    count makes the affected procedure block INCOMPLETE and forbids a
    successful-subset interval; the full-TRAIN reference point is retained.
    """
    reference = fit_panel(train_items, procedures)
    labels = [procedure.label for procedure in procedures]
    directions = _protocol.PRIMARY_DIRECTIONS
    samples: dict[str, dict[str, list[float]]] = {
        label: {direction: [] for direction in directions} for label in labels
    }
    failures: dict[str, list[dict[str, Any]]] = {label: [] for label in labels}
    successful: dict[str, int] = {label: 0 for label in labels}
    for replicate in range(replicates):
        resampled = resample_train_multiset(train_items, replicate=replicate)
        for procedure in procedures:
            try:
                refit = fit_panel(resampled, (procedure,))
            except Exception as exc:  # recorded exactly; never substituted or retried
                failures[procedure.label].append(
                    {
                        "replicate": replicate,
                        "procedure_label": procedure.label,
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                    }
                )
                continue
            successful[procedure.label] += 1
            for direction in directions:
                samples[procedure.label][direction].append(
                    subject_weighted_mean(
                        test_items,
                        lambda item, procedure=procedure, refit=refit, direction=direction: (
                            _cross_loss(item, refit, procedure.label, direction, brier_loss)
                            - _raw_loss(item, direction, brier_loss)
                        ),
                    )
                )
    blocks: dict[str, Any] = {}
    for label in labels:
        failed = len(failures[label])
        status = TRAIN_REFIT_STATUS_COMPLETE if failed == 0 else TRAIN_REFIT_STATUS_INCOMPLETE
        direction_blocks: dict[str, Any] = {}
        for direction in directions:
            point = subject_weighted_mean(
                test_items,
                lambda item, label=label, direction=direction: (
                    _cross_loss(item, reference, label, direction, brier_loss)
                    - _raw_loss(item, direction, brier_loss)
                ),
            )
            # Any nonzero failure count invalidates the preregistered interval for
            # the affected procedure: no success-subset interval is ever emitted.
            interval = (
                _interval(samples[label][direction], (2.5, 50.0, 97.5)) if failed == 0 else None
            )
            direction_blocks[direction] = {"point": point, "interval": interval}
        blocks[label] = {
            "status": status,
            "planned_replicates": replicates,
            "successful_replicates": successful[label],
            "failed_replicates": failed,
            "failures": failures[label],
            "directions": direction_blocks,
        }
    return {
        "replicates": replicates,
        "reference_panel": reference.canonical_payload(),
        "procedures": blocks,
    }


def build_analysis_artifact(
    *,
    protocol_design: Mapping[str, Any],
    conditions: Sequence[Mapping[str, Any]],
    test_replicates: int = _protocol.TEST_BOOTSTRAP_REPLICATES,
    train_refit_replicates: int = _protocol.TRAIN_REFIT_BOOTSTRAP_REPLICATES,
) -> dict[str, Any]:
    """Assemble the full R3 analysis artifact from per-model conditions."""
    _protocol.validate_protocol(protocol_design)
    procedures = _protocol.procedure_panel()
    model_blocks = [
        analyze_model_condition(
            model_id=condition["model_id"],
            model_revision=condition["model_revision"],
            train_items=condition["train_items"],
            test_items=condition["test_items"],
            test_winner_records=condition["test_winner_records"],
            procedures=procedures,
            test_replicates=test_replicates,
            train_refit_replicates=train_refit_replicates,
        )
        for condition in conditions
    ]
    payload: dict[str, Any] = {
        "artifact_type": R3_ANALYSIS_ARTIFACT_TYPE,
        "artifact_version": R3_ANALYSIS_VERSION,
        "fingerprint_version": R3_ANALYSIS_FINGERPRINT_VERSION,
        "protocol_fingerprint": protocol_design["protocol_fingerprint"],
        "population_manifest_fingerprint": protocol_design["population"]["manifest_fingerprint"],
        "primary_model_id": _protocol.PRIMARY_MODEL_ID,
        "replication_model_id": _protocol.REPLICATION_MODEL_ID,
        "primary_contrasts": protocol_design["primary_contrasts"],
        "multiplicity": protocol_design["multiplicity"],
        "models": model_blocks,
    }
    return payload


def _main(argv: Sequence[str]) -> int:
    if len(argv) != 2:
        print("usage: r3_analysis.py PROTOCOL_DESIGN_JSON", file=sys.stderr)
        return 2
    design = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    _protocol.validate_protocol(design)
    raise SystemExit(
        "r3_analysis.py has no official measurement runner; R3 measurement is not authorized. "
        "Use analyze_model_condition / build_analysis_artifact with pre-measured data."
    )


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(_main(sys.argv))
