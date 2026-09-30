"""R4 production calibration-family implementation (SYNTHETIC ENGINEERING ONLY).

This module holds the production implementations of the two frozen R4
family-extension procedures:

* ``I-isotonic`` — non-decreasing empirical least-squares step function:
  exact-score aggregation, weighted PAVA, piecewise-linear interpolation
  between observed thresholds, nearest-endpoint constant support extension.
* ``B-beta`` — three-parameter beta calibration
  ``f(s) = sigmoid(a * ln(s) + b * (-ln(1 - s)) + c)`` with ``a >= 0`` and
  ``b >= 0``, fitted by an active-set BFGS search over the four constraint
  faces plus a Karush-Kuhn-Tucker acceptance residual.

Scope boundaries
----------------

This file is IMPLEMENTATION / SOLVER PROVENANCE only. The scientific procedure
identities are frozen in
``experiments/calibration_transport/R4_CALIBRATION_FAMILY_FREEZE.md`` and are
recorded here as the constants ``ISOTONIC_SCIENTIFIC_FINGERPRINT`` and
``BETA_SCIENTIFIC_FINGERPRINT``. Nothing in this module changes the frozen
mathematics; a change to the mathematics would require a new scientific
fingerprint and a new human freeze gate.

Nothing here is a scientific result. This module never reads a study-dataset
row (MMLU / HellaSwag / MedMCQA), never loads a model or tokenizer, never uses
a GPU, and never computes Brier / LogLoss / transport / predictor outcomes.
Its only inputs are hand-written synthetic arrays.

The four frozen R3 continuity procedures (P-low, P-historical, L-low,
L-historical) are deliberately NOT reimplemented here. Their logistic
mathematics lives in ``src/probvenance/calibration.py`` and
``experiments/calibration_transport/r3_analysis.py`` and is left untouched;
this module only re-verifies their fingerprints indirectly through the frozen
semantic-candidate artifact.

Output policy: a calibrator may return the exact values ``0.0`` and ``1.0``.
Those exact outputs are preserved; this module performs no output truncation of
any kind.
"""

from __future__ import annotations

import bisect
import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy
import scipy
from scipy.optimize import minimize

from probvenance.fingerprint import fingerprint

__all__ = [
    "BETA_FIT_INELIGIBLE_INSUFFICIENT_DISTINCT_SCORES",
    "BETA_FIT_INELIGIBLE_MONOTONE_SEPARATION",
    "BETA_FIT_INELIGIBLE_SINGLE_CLASS",
    "BETA_IMPLEMENTATION_ID",
    "BETA_SCIENTIFIC_FINGERPRINT",
    "ELIGIBLE",
    "FACE_A0",
    "FACE_A0_B0",
    "FACE_B0",
    "FACE_INTERIOR",
    "INELIGIBLE_ENDPOINT",
    "ISOTONIC_IMPLEMENTATION_ID",
    "ISOTONIC_SCIENTIFIC_FINGERPRINT",
    "KKT_ACCEPTANCE_TOL",
    "BetaContractViolation",
    "BetaFit",
    "BetaFitIneligible",
    "BetaImplementationError",
    "IsotonicContractViolation",
    "IsotonicFit",
    "apply_beta_fixed_decision_probability",
    "apply_isotonic_fixed_decision_probability",
    "beta_alternative_start_audit",
    "beta_fit_eligibility",
    "beta_gradient",
    "beta_kkt_residual",
    "beta_objective",
    "fit_beta_fixed_decision_probability",
    "fit_isotonic_fixed_decision_probability",
    "require_beta_parameters",
]

# ---------------------------------------------------------------------------
# Frozen scientific identities (must match R4_CALIBRATION_FAMILY_FREEZE.md)
# ---------------------------------------------------------------------------

ISOTONIC_IMPLEMENTATION_ID = "r4-isotonic-pava-linear-v1"
ISOTONIC_IMPLEMENTATION_VERSION = 1
ISOTONIC_SCIENTIFIC_FINGERPRINT = "cd13bc07bf92f3375bcd16d57fa5f515cd40f68199b57181791f85c58be8c244"

BETA_IMPLEMENTATION_ID = "r4-beta-active-set-bfgs-kkt-v1"
BETA_IMPLEMENTATION_VERSION = 1
BETA_SCIENTIFIC_FINGERPRINT = "f4b710fb98f7c3056794aa709d53309f462a8f598cef8089d2f9c0ed6f7e37ff"

# Engineering candidate acceptance tolerance for the beta KKT residual. This is
# an implementation-level numerical threshold; it does not modify any score or
# prediction and is not part of the frozen scientific identity.
KKT_ACCEPTANCE_TOL = 1e-10

FACE_INTERIOR = "FACE_INTERIOR"
FACE_A0 = "FACE_A0"
FACE_B0 = "FACE_B0"
FACE_A0_B0 = "FACE_A0_B0"

# Fixed face preference order, used only to break an exact binary64 objective tie.
FACE_ORDER = (FACE_A0_B0, FACE_A0, FACE_B0, FACE_INTERIOR)

ELIGIBLE = "ELIGIBLE"
INELIGIBLE_ENDPOINT = "INELIGIBLE_ENDPOINT"
BETA_FIT_INELIGIBLE_SINGLE_CLASS = "BETA_FIT_INELIGIBLE_SINGLE_CLASS"
BETA_FIT_INELIGIBLE_INSUFFICIENT_DISTINCT_SCORES = (
    "BETA_FIT_INELIGIBLE_INSUFFICIENT_DISTINCT_SCORES"
)
BETA_FIT_INELIGIBLE_MONOTONE_SEPARATION = "BETA_FIT_INELIGIBLE_MONOTONE_SEPARATION"

SOLVER_SUCCESS = "SOLVER_SUCCESS"
SOLVER_WARNING_KKT_ACCEPTED = "SOLVER_WARNING_KKT_ACCEPTED"

# Deterministic BFGS settings. The gradient tolerance is set two orders of
# magnitude below the acceptance residual so that a genuine optimum can meet
# it; these are solver settings and do not modify any score or prediction.
_BFGS_GRADIENT_TOLERANCE = KKT_ACCEPTANCE_TOL / 100.0
_BFGS_OPTIONS: dict[str, float] = {"gtol": _BFGS_GRADIENT_TOLERANCE, "maxiter": 5000}

# Deterministic alternative starts, used only by the uniqueness audit.
_ALTERNATIVE_STARTS: dict[str, tuple[tuple[float, ...], ...]] = {
    FACE_INTERIOR: ((2.0, 2.0, 0.0), (0.5, 0.5, 0.0), (1.0, 1.0, -1.0), (1.0, 1.0, 1.0)),
    FACE_A0: ((1.0, 0.0), (0.5, 0.0), (2.0, 1.0)),
    FACE_B0: ((1.0, 0.0), (0.5, 0.0), (2.0, 1.0)),
    FACE_A0_B0: ((0.0,), (1.0,)),
}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class IsotonicContractViolation(ValueError):
    """The isotonic input violates the frozen structural contract."""


class BetaContractViolation(ValueError):
    """The beta input violates the frozen structural contract."""


class BetaFitIneligible(ValueError):
    """The beta training set fails a frozen fitting-eligibility gate."""

    def __init__(self, state: str) -> None:
        self.state = state
        super().__init__(state)


class BetaImplementationError(RuntimeError):
    """No constraint face produced an accepted optimum."""


# ---------------------------------------------------------------------------
# Shared numeric helpers
# ---------------------------------------------------------------------------


def _stable_sigmoid(z: float) -> float:
    if z >= 0.0:
        return 1.0 / (1.0 + math.exp(-z))
    exp_z = math.exp(z)
    return exp_z / (1.0 + exp_z)


def _stable_softplus(z: float) -> float:
    if z > 0.0:
        return z + math.log1p(math.exp(-z))
    return math.log1p(math.exp(z))


def _log_odds(probability: float) -> float:
    return math.log(probability / (1.0 - probability))


def _binary_label(value: object, *, exc: type[ValueError], context: str) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int) and value in (0, 1):
        return value
    raise exc(f"{context}: label must be binary 0/1, got {value!r}")


def _unit_interval_score(value: object, *, exc: type[ValueError], context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise exc(f"{context}: score must be a real number, got {value!r}")
    result = float(value)
    if not math.isfinite(result):
        raise exc(f"{context}: score must be finite, got {result!r}")
    if result < 0.0 or result > 1.0:
        raise exc(f"{context}: score must lie in [0, 1], got {result!r}")
    return result


def _training_data_fingerprint(scores: Sequence[float], labels: Sequence[int]) -> str:
    """Identify the training multiset, independent of the row order given."""
    pairs = sorted(zip(scores, labels, strict=True))
    payload = {
        "labels": [int(label) for _score, label in pairs],
        "scores": [float(score) for score, _label in pairs],
    }
    return fingerprint(payload)


# ---------------------------------------------------------------------------
# I-isotonic
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IsotonicFit:
    """Fitted non-decreasing step function plus its deterministic identity."""

    thresholds: tuple[float, ...]
    fitted_values: tuple[float, ...]
    training_data_fingerprint: str

    @property
    def scientific_fingerprint(self) -> str:
        return ISOTONIC_SCIENTIFIC_FINGERPRINT

    @property
    def implementation_id(self) -> str:
        return ISOTONIC_IMPLEMENTATION_ID

    def state_payload(self) -> dict[str, Any]:
        """Return the canonical, deterministic fitted-state payload."""
        return {
            "fitted_values": list(self.fitted_values),
            "implementation_id": ISOTONIC_IMPLEMENTATION_ID,
            "implementation_version": ISOTONIC_IMPLEMENTATION_VERSION,
            "scientific_fingerprint": ISOTONIC_SCIENTIFIC_FINGERPRINT,
            "thresholds": list(self.thresholds),
            "training_data_fingerprint": self.training_data_fingerprint,
        }

    def state_fingerprint(self) -> str:
        return fingerprint(self.state_payload())


def fit_isotonic_fixed_decision_probability(
    scores: Sequence[float], labels: Sequence[int]
) -> IsotonicFit:
    """Fit the frozen I-isotonic calibrator on synthetic paired scores/labels.

    Exact binary64 equal scores are aggregated (count / sum of labels / mean
    label) with no tolerance merging, then pooled with weighted PAVA while a
    left block mean strictly exceeds the next block mean. The fitted value is
    represented at every unique observed threshold.
    """
    if len(scores) != len(labels):
        raise IsotonicContractViolation("isotonic fitting requires paired scores and labels")
    if not scores:
        raise IsotonicContractViolation("isotonic fitting requires at least one training row")
    score_values = [
        _unit_interval_score(score, exc=IsotonicContractViolation, context="isotonic fitting")
        for score in scores
    ]
    label_values = [
        _binary_label(label, exc=IsotonicContractViolation, context="isotonic fitting")
        for label in labels
    ]

    aggregated: dict[float, list[int]] = {}
    for score, label in zip(score_values, label_values, strict=True):
        bucket = aggregated.setdefault(score, [0, 0])
        bucket[0] += 1
        bucket[1] += label

    blocks: list[tuple[int, int, float, list[float]]] = []
    for score in sorted(aggregated):
        count, positives = aggregated[score]
        blocks.append((count, positives, positives / count, [score]))
        while len(blocks) >= 2 and blocks[-2][2] > blocks[-1][2]:
            right = blocks.pop()
            left = blocks.pop()
            weight = left[0] + right[0]
            total = left[1] + right[1]
            blocks.append((weight, total, total / weight, left[3] + right[3]))

    thresholds: list[float] = []
    fitted_values: list[float] = []
    for _weight, _positives, mean, members in blocks:
        for member in members:
            thresholds.append(member)
            fitted_values.append(mean)

    return IsotonicFit(
        thresholds=tuple(thresholds),
        fitted_values=tuple(fitted_values),
        training_data_fingerprint=_training_data_fingerprint(score_values, label_values),
    )


def apply_isotonic_fixed_decision_probability(fit: IsotonicFit, score: float) -> float:
    """Apply a fitted isotonic map: piecewise-linear, constant outside support."""
    value = _unit_interval_score(score, exc=IsotonicContractViolation, context="isotonic apply")
    thresholds = fit.thresholds
    fitted_values = fit.fitted_values
    if value <= thresholds[0]:
        return fitted_values[0]
    if value >= thresholds[-1]:
        return fitted_values[-1]
    index = bisect.bisect_right(thresholds, value) - 1
    if thresholds[index] == value:
        return fitted_values[index]
    lower = thresholds[index]
    upper = thresholds[index + 1]
    fraction = (value - lower) / (upper - lower)
    return fitted_values[index] + (fitted_values[index + 1] - fitted_values[index]) * fraction


# ---------------------------------------------------------------------------
# B-beta
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BetaFit:
    """Fitted beta calibrator plus its deterministic solver provenance."""

    a: float
    b: float
    c: float
    active_face: str
    objective: float
    kkt_residual: float
    solver_status: str
    solver_status_class: str
    solver_message: str
    solver_nit: int
    solver_nfev: int
    solver_njev: int
    face_tie_break_used: bool
    training_data_fingerprint: str

    @property
    def scientific_fingerprint(self) -> str:
        return BETA_SCIENTIFIC_FINGERPRINT

    @property
    def implementation_id(self) -> str:
        return BETA_IMPLEMENTATION_ID

    @property
    def parameters(self) -> tuple[float, float, float]:
        return (self.a, self.b, self.c)

    def state_payload(self) -> dict[str, Any]:
        """Return the canonical, deterministic fitted-state payload."""
        return {
            "active_face": self.active_face,
            "face_tie_break_used": self.face_tie_break_used,
            "implementation_id": BETA_IMPLEMENTATION_ID,
            "implementation_version": BETA_IMPLEMENTATION_VERSION,
            "kkt_residual": self.kkt_residual,
            "kkt_tolerance": KKT_ACCEPTANCE_TOL,
            "numpy_version": numpy.__version__,
            "objective": self.objective,
            "parameters": {"a": self.a, "b": self.b, "c": self.c},
            "scientific_fingerprint": BETA_SCIENTIFIC_FINGERPRINT,
            "scipy_version": scipy.__version__,
            "solver_message": self.solver_message,
            "solver_nfev": self.solver_nfev,
            "solver_nit": self.solver_nit,
            "solver_njev": self.solver_njev,
            "solver_status": self.solver_status,
            "solver_status_class": self.solver_status_class,
            "training_data_fingerprint": self.training_data_fingerprint,
        }

    def state_fingerprint(self) -> str:
        return fingerprint(self.state_payload())


def require_beta_parameters(a: float, b: float, c: float) -> tuple[float, float, float]:
    """Validate the frozen parameter constraints ``a >= 0`` and ``b >= 0``."""
    for name, value in (("a", a), ("b", b), ("c", c)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise BetaContractViolation(
                f"beta parameter {name} must be a real number, got {value!r}"
            )
        if not math.isfinite(float(value)):
            raise BetaContractViolation(f"beta parameter {name} must be finite, got {value!r}")
    if a < 0.0 or b < 0.0:
        raise BetaContractViolation(
            f"beta parameters must satisfy a >= 0 and b >= 0, got a={a!r} b={b!r}"
        )
    return (float(a), float(b), float(c))


def beta_fit_eligibility(scores: Sequence[float], labels: Sequence[int]) -> str:
    """Return the frozen ordered eligibility state for a beta training set."""
    if len(scores) != len(labels):
        raise BetaContractViolation("beta fitting requires paired scores and labels")
    if not scores:
        raise BetaContractViolation("beta fitting requires at least one training row")
    score_values = [
        _unit_interval_score(score, exc=BetaContractViolation, context="beta fitting")
        for score in scores
    ]
    if any(score == 0.0 or score == 1.0 for score in score_values):
        return INELIGIBLE_ENDPOINT
    label_values = [
        _binary_label(label, exc=BetaContractViolation, context="beta fitting") for label in labels
    ]
    if len(set(label_values)) < 2:
        return BETA_FIT_INELIGIBLE_SINGLE_CLASS
    if len(set(score_values)) < 3:
        return BETA_FIT_INELIGIBLE_INSUFFICIENT_DISTINCT_SCORES
    negatives = [
        score for score, label in zip(score_values, label_values, strict=True) if label == 0
    ]
    positives = [
        score for score, label in zip(score_values, label_values, strict=True) if label == 1
    ]
    if max(negatives) <= min(positives):
        return BETA_FIT_INELIGIBLE_MONOTONE_SEPARATION
    return ELIGIBLE


def beta_transformed_features(score: float) -> tuple[float, float]:
    """Return ``(ln(s), -ln(1 - s))`` for a strictly interior score."""
    return (math.log(score), -math.log1p(-score))


def beta_objective(rows: Sequence[tuple[float, int]], a: float, b: float, c: float) -> float:
    """Return the mean Bernoulli negative log-likelihood for interior rows."""
    losses: list[float] = []
    for score, label in rows:
        x1, x2 = beta_transformed_features(score)
        z = a * x1 + b * x2 + c
        losses.append(_stable_softplus(-z) if label == 1 else _stable_softplus(z))
    return math.fsum(losses) / len(losses)


def beta_gradient(
    rows: Sequence[tuple[float, int]], a: float, b: float, c: float
) -> tuple[float, float, float]:
    """Return the analytic gradient of :func:`beta_objective`."""
    grad_a: list[float] = []
    grad_b: list[float] = []
    grad_c: list[float] = []
    for score, label in rows:
        x1, x2 = beta_transformed_features(score)
        residual = _stable_sigmoid(a * x1 + b * x2 + c) - label
        grad_a.append(residual * x1)
        grad_b.append(residual * x2)
        grad_c.append(residual)
    count = len(rows)
    return (
        math.fsum(grad_a) / count,
        math.fsum(grad_b) / count,
        math.fsum(grad_c) / count,
    )


def beta_kkt_residual(rows: Sequence[tuple[float, int]], a: float, b: float, c: float) -> float:
    """Return the KKT residual ``max(r_a, r_b, r_c)`` for the constrained problem."""
    grad_a, grad_b, grad_c = beta_gradient(rows, a, b, c)
    residual_a = abs(grad_a) if a > 0.0 else max(0.0, -grad_a)
    residual_b = abs(grad_b) if b > 0.0 else max(0.0, -grad_b)
    return max(residual_a, residual_b, abs(grad_c))


def _face_parameters(face: str, vector: Sequence[float]) -> tuple[float, float, float]:
    if face == FACE_INTERIOR:
        return (float(vector[0]), float(vector[1]), float(vector[2]))
    if face == FACE_A0:
        return (0.0, float(vector[0]), float(vector[1]))
    if face == FACE_B0:
        return (float(vector[0]), 0.0, float(vector[1]))
    return (0.0, 0.0, float(vector[0]))


def _face_gradient(
    face: str, rows: Sequence[tuple[float, int]], vector: Sequence[float]
) -> list[float]:
    a, b, c = _face_parameters(face, vector)
    grad_a, grad_b, grad_c = beta_gradient(rows, a, b, c)
    if face == FACE_INTERIOR:
        return [grad_a, grad_b, grad_c]
    if face == FACE_A0:
        return [grad_b, grad_c]
    if face == FACE_B0:
        return [grad_a, grad_c]
    return [grad_c]


def _face_start(face: str, rows: Sequence[tuple[float, int]]) -> list[float]:
    if face == FACE_INTERIOR:
        return [1.0, 1.0, 0.0]
    if face == FACE_A0:
        return [1.0, 0.0]
    if face == FACE_B0:
        return [1.0, 0.0]
    mean_label = math.fsum(label for _score, label in rows) / len(rows)
    return [_log_odds(mean_label)]


def _face_is_valid(face: str, a: float, b: float, c: float) -> bool:
    if face == FACE_INTERIOR:
        return a > 0.0 and b > 0.0
    if face == FACE_A0:
        return a == 0.0 and b > 0.0
    if face == FACE_B0:
        return b == 0.0 and a > 0.0
    return a == 0.0 and b == 0.0


def _solve_face(
    face: str, rows: Sequence[tuple[float, int]], start: Sequence[float]
) -> dict[str, Any]:
    def objective(vector: Sequence[float]) -> float:
        return beta_objective(rows, *_face_parameters(face, vector))

    def gradient(vector: Sequence[float]) -> list[float]:
        return _face_gradient(face, rows, vector)

    result = minimize(objective, list(start), jac=gradient, method="BFGS", options=_BFGS_OPTIONS)
    a, b, c = _face_parameters(face, result.x)
    objective_value = beta_objective(rows, a, b, c)
    residual = beta_kkt_residual(rows, a, b, c)
    accepted = (
        math.isfinite(a)
        and math.isfinite(b)
        and math.isfinite(c)
        and math.isfinite(objective_value)
        and _face_is_valid(face, a, b, c)
        and residual <= KKT_ACCEPTANCE_TOL
    )
    return {
        "accepted": accepted,
        "active_face": face,
        "kkt_residual": residual,
        "objective": objective_value,
        "parameters": (a, b, c),
        "solver_message": str(result.message),
        "solver_nfev": int(result.nfev),
        "solver_nit": int(result.nit),
        "solver_njev": int(getattr(result, "njev", 0)),
        "solver_status": str(result.status),
        "solver_status_class": SOLVER_SUCCESS if result.success else SOLVER_WARNING_KKT_ACCEPTED,
    }


def _accepted_candidates(rows: Sequence[tuple[float, int]]) -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for face in FACE_ORDER:
        candidate = _solve_face(face, rows, _face_start(face, rows))
        if candidate["accepted"]:
            candidates[face] = candidate
    return candidates


def fit_beta_fixed_decision_probability(
    scores: Sequence[float], labels: Sequence[int]
) -> BetaFit:
    """Fit the frozen B-beta calibrator by active-set BFGS with KKT acceptance."""
    state = beta_fit_eligibility(scores, labels)
    if state != ELIGIBLE:
        raise BetaFitIneligible(state)
    rows = tuple(
        (
            float(score),
            _binary_label(label, exc=BetaContractViolation, context="beta fitting"),
        )
        for score, label in zip(scores, labels, strict=True)
    )

    candidates = _accepted_candidates(rows)
    if not candidates:
        raise BetaImplementationError("no constraint face produced an accepted optimum")

    best_face = min(
        (face for face in FACE_ORDER if face in candidates),
        key=lambda face: candidates[face]["objective"],
    )
    best_objective = candidates[best_face]["objective"]
    tied = [
        face
        for face in FACE_ORDER
        if face in candidates and candidates[face]["objective"] == best_objective
    ]
    best = candidates[best_face]
    a, b, c = best["parameters"]
    return BetaFit(
        a=a,
        b=b,
        c=c,
        active_face=best_face,
        objective=best_objective,
        kkt_residual=best["kkt_residual"],
        solver_status=best["solver_status"],
        solver_status_class=best["solver_status_class"],
        solver_message=best["solver_message"],
        solver_nit=best["solver_nit"],
        solver_nfev=best["solver_nfev"],
        solver_njev=best["solver_njev"],
        face_tie_break_used=len(tied) > 1,
        training_data_fingerprint=_training_data_fingerprint(
            [score for score, _label in rows], [label for _score, label in rows]
        ),
    )


def apply_beta_fixed_decision_probability(fit: BetaFit, score: float) -> float:
    """Apply a fitted beta map, including the exact endpoint limits."""
    require_beta_parameters(fit.a, fit.b, fit.c)
    value = _unit_interval_score(score, exc=BetaContractViolation, context="beta apply")
    if value == 0.0:
        return 0.0 if fit.a > 0.0 else _stable_sigmoid(fit.c)
    if value == 1.0:
        return 1.0 if fit.b > 0.0 else _stable_sigmoid(fit.c)
    x1, x2 = beta_transformed_features(value)
    return _stable_sigmoid(fit.a * x1 + fit.b * x2 + fit.c)


def beta_alternative_start_audit(
    scores: Sequence[float], labels: Sequence[int]
) -> dict[str, Any]:
    """Audit the fitted optimum against deterministic alternative starts."""
    fit = fit_beta_fixed_decision_probability(scores, labels)
    rows = tuple(
        (
            float(score),
            _binary_label(label, exc=BetaContractViolation, context="beta audit"),
        )
        for score, label in zip(scores, labels, strict=True)
    )
    discrepancies: list[float] = []
    objective_discrepancies: list[float] = []
    for start in _ALTERNATIVE_STARTS[fit.active_face]:
        result = minimize(
            lambda vector: beta_objective(rows, *_face_parameters(fit.active_face, vector)),
            list(start),
            jac=lambda vector: _face_gradient(fit.active_face, rows, vector),
            method="BFGS",
            options=_BFGS_OPTIONS,
        )
        a, b, c = _face_parameters(fit.active_face, result.x)
        discrepancies.append(max(abs(a - fit.a), abs(b - fit.b), abs(c - fit.c)))
        objective_discrepancies.append(abs(beta_objective(rows, a, b, c) - fit.objective))
    return {
        "active_face": fit.active_face,
        "alternative_starts": list(_ALTERNATIVE_STARTS[fit.active_face]),
        "max_parameter_discrepancy": max(discrepancies),
        "max_objective_discrepancy": max(objective_discrepancies),
    }
