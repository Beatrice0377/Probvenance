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
import json
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

#: Shared analysis-artifact identity, kept identical to the run orchestrator's
#: artifact so a regenerated artifact is byte-comparable with a freshly written one.
ANALYSIS_ARTIFACT_TYPE = "calibration-transport-frozen-decision-pilot-analysis"
PILOT_ARTIFACT_VERSION = 1

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
    the relevant question is how far B's TEST scores move outside A's observed
    TRAIN range, and symmetrically for ``B->A``. The SOURCE is the fitting
    measurement's TRAIN scores; the TARGET is the other measurement's TEST
    scores. In the R2 CAT/OVR pilot ``A = CAT`` and ``B = OVR``, so:

    - ``A->B`` (``test_b_outside_train_a_range_fraction``) checks OVR TEST scores
      against the CAT TRAIN range;
    - ``B->A`` (``test_a_outside_train_b_range_fraction``) checks CAT TEST scores
      against the OVR TRAIN range.

    The two directions are NOT symmetric and must never be swapped. The
    explicitly named alias keys restate the same numbers without relying on the
    reader mapping A/B to CAT/OVR.
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

    outside_b_vs_a = outside(test_b, min(train_a), max(train_a))
    outside_a_vs_b = outside(test_a, min(train_b), max(train_b))
    return {
        "train_a": _range_summary(train_a),
        "train_b": _range_summary(train_b),
        "test_a": _range_summary(test_a),
        "test_b": _range_summary(test_b),
        "test_b_outside_train_a_range_fraction": outside_b_vs_a,
        "test_a_outside_train_b_range_fraction": outside_a_vs_b,
        # Direction-explicit aliases (A = CAT, B = OVR): TARGET TEST scores that
        # fall outside the SOURCE TRAIN observed range.
        "cat_to_ovr_target_test_outside_source_train_fraction": outside_b_vs_a,
        "ovr_to_cat_target_test_outside_source_train_fraction": outside_a_vs_b,
    }


def raw_relative_brier_changes(
    points: Sequence[PairedPoint], g_a: Any, g_b: Any
) -> dict[str, float]:
    """Held-out fitted-vs-RAW-target Brier changes (A = CAT, B = OVR).

    This answers a DIFFERENT question than :func:`brier_matrix`. Here the
    baseline is the RAW target measurement score, not the target self-fitted
    calibrator. Sign convention: ``positive`` means the fitted application has
    HIGHER held-out Brier risk than the raw target score (worse on this held-out
    set); ``negative`` means lower risk (better on this held-out set). It is a
    descriptive held-out comparison only, never a guaranteed improvement.
    """
    fit_a_eval_a = brier(_predict(points, g_a, score="a"))
    fit_a_eval_b = brier(_predict(points, g_a, score="b"))
    fit_b_eval_a = brier(_predict(points, g_b, score="a"))
    fit_b_eval_b = brier(_predict(points, g_b, score="b"))
    raw_a = brier([(p.score_a, p.y) for p in points])
    raw_b = brier([(p.score_b, p.y) for p in points])
    return {
        "cat_self_minus_raw_cat": fit_a_eval_a - raw_a,
        "ovr_self_minus_raw_ovr": fit_b_eval_b - raw_b,
        "cat_to_ovr_minus_raw_ovr": fit_a_eval_b - raw_b,
        "ovr_to_cat_minus_raw_cat": fit_b_eval_a - raw_a,
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


def winner_by_item(records: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    """Map item id to a measurement's own winner (end-to-end diagnostic only)."""
    return {str(record["item_id"]): str(record["winner"]) for record in records}


def build_analysis_artifact(
    *,
    plan: Any,
    dataset: Any,
    case_set_fingerprint: str,
    cat_records: Sequence[Mapping[str, Any]],
    ovr_records: Sequence[Mapping[str, Any]],
    outcomes_a: Sequence[Any],
    outcomes_b: Sequence[Any],
) -> dict[str, Any]:
    """Assemble the R2 analysis artifact from one frozen measurement run.

    Pure function of (plan, dataset, raw records): it fits nothing that depends
    on test rows and consults no model, so the artifact is a deterministic
    function of the frozen raw evidence.
    """
    train_points = scored_points(dataset, split=Split.TRAIN)
    test_points = scored_points(dataset, split=Split.TEST)
    g_a = fit_pilot_calibrator(
        source_measurement=plan.measurement_a,
        training_rows=[(p.item_id, p.score_a, p.y) for p in train_points],
        plan_fingerprint=plan.fingerprint,
    )
    g_b = fit_pilot_calibrator(
        source_measurement=plan.measurement_b,
        training_rows=[(p.item_id, p.score_b, p.y) for p in train_points],
        plan_fingerprint=plan.fingerprint,
    )
    truth_by_item = {item.item_id: str(item.ground_truth_value) for item in plan.items}
    test_ids = {p.item_id for p in test_points}
    cat_winners = winner_by_item([r for r in cat_records if r["item_id"] in test_ids])
    ovr_winners = winner_by_item([r for r in ovr_records if r["item_id"] in test_ids])
    winner_diag = winner_diagnostics(
        truth_by_item={i: truth_by_item[i] for i in sorted(cat_winners)},
        winner_a_by_item=cat_winners,
        winner_b_by_item=ovr_winners,
    )
    non_simplex = ovr_non_simplex_diagnostics(
        candidate_score_sums=[float(r["candidate_score_sum"]) for r in ovr_records],
        over_half_counts=[
            sum(1 for c in r["candidates"] if c["probability_true"] > 0.5) for r in ovr_records
        ],
    )
    return {
        "artifact_type": ANALYSIS_ARTIFACT_TYPE,
        "artifact_version": PILOT_ARTIFACT_VERSION,
        "research_spec_id": RESEARCH_SPEC_ID,
        "research_spec_version": RESEARCH_SPEC_VERSION,
        "source_case_set_fingerprint": case_set_fingerprint,
        "plan_fingerprint": plan.fingerprint,
        "paired_dataset_fingerprint": dataset.fingerprint,
        "measurement_a": plan.measurement_a.measurement_id,
        "measurement_b": plan.measurement_b.measurement_id,
        "l2_strength": PILOT_L2_STRENGTH,
        "completeness": {
            "planned_n": len(plan.items),
            "train_planned_n": sum(1 for i in plan.items if i.split is Split.TRAIN),
            "test_planned_n": sum(1 for i in plan.items if i.split is Split.TEST),
            "cat_scored": sum(1 for o in outcomes_a if o.status is MeasurementStatus.SCORED),
            "ovr_scored": sum(1 for o in outcomes_b if o.status is MeasurementStatus.SCORED),
            "paired_scored_train_n": len(train_points),
            "paired_scored_test_n": len(test_points),
            "train_y1": sum(1 for p in train_points if p.y == 1.0),
            "train_y0": sum(1 for p in train_points if p.y == 0.0),
            "test_y1": sum(1 for p in test_points if p.y == 1.0),
            "test_y0": sum(1 for p in test_points if p.y == 0.0),
        },
        "train_item_ids": [p.item_id for p in train_points],
        "test_item_ids": [p.item_id for p in test_points],
        "calibrator_a": g_a.canonical_payload(),
        "calibrator_a_fingerprint": g_a.fingerprint,
        "calibrator_b": g_b.canonical_payload(),
        "calibrator_b_fingerprint": g_b.fingerprint,
        "brier_matrix": brier_matrix(test_points, g_a, g_b),
        "raw_relative_brier_changes": raw_relative_brier_changes(test_points, g_a, g_b),
        "logloss_matrix": logloss_matrix(test_points, g_a, g_b),
        "observed_range_diagnostics": observed_range_diagnostics(train_points, test_points),
        "winner_diagnostics": winner_diag,
        "ovr_non_simplex_diagnostics": non_simplex,
    }


def analyze_raw_artifact(
    raw: Mapping[str, Any], *, cases_path: str | Path | None = None
) -> dict[str, Any]:
    """Deterministically rebuild the analysis artifact from a frozen raw artifact.

    No model is loaded and no network is touched: the plan, dataset, and
    outcomes are rebuilt from the raw artifact's own records, and their
    fingerprints are re-checked against the recorded lineage. Any mismatch
    fails closed instead of silently re-deriving a different measurement.
    """
    pilot_plan = _load_sibling("pilot_plan")
    measurements = _load_sibling("measurements")
    payload = pilot_plan.load_case_set(cases_path or pilot_plan.DEFAULT_CASES_PATH)
    if pilot_plan.case_set_fingerprint(payload) != raw["source_case_set_fingerprint"]:
        raise ValueError("case set fingerprint does not match the raw artifact lineage")
    config = raw["model_configuration"]
    plan = pilot_plan.build_plan(
        payload, model_id=config["model"], model_revision=config["revision"]
    )
    if plan.fingerprint != raw["plan_fingerprint"]:
        raise ValueError("plan fingerprint does not match the raw artifact lineage")
    cat_records = raw["cat_raw_records"]
    ovr_records = raw["ovr_raw_records"]
    outcomes_a = tuple(measurements.cat_outcome(record) for record in cat_records)
    outcomes_b = tuple(measurements.ovr_outcome(record) for record in ovr_records)
    dataset = _integrity.PairedFixedDecisionDataset.create(plan, outcomes_a, outcomes_b)
    if dataset.fingerprint != raw["paired_dataset_fingerprint"]:
        raise ValueError("paired dataset fingerprint does not match the raw artifact lineage")
    return build_analysis_artifact(
        plan=plan,
        dataset=dataset,
        case_set_fingerprint=raw["source_case_set_fingerprint"],
        cat_records=cat_records,
        ovr_records=ovr_records,
        outcomes_a=outcomes_a,
        outcomes_b=outcomes_b,
    )


def _main(argv: Sequence[str]) -> int:
    """Regenerate the derived analysis artifact from a frozen raw artifact."""
    if len(argv) != 2:
        print("usage: analysis.py <raw-artifact.json>", file=sys.stderr)
        return 2
    raw_path = Path(argv[1])
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    artifact = analyze_raw_artifact(raw)
    out_path = raw_path.with_name(raw_path.stem + "-analysis.json")
    text = json.dumps(artifact, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
    out_path.write_text(text + "\n", encoding="utf-8")
    print(f"wrote {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
