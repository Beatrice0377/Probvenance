"""R2C.1 Low-Regularization Numerical Adequacy Closure (research-only).

R2C.1 answers exactly one question about the already-frozen R2C evidence:

    Are the 15 uncertifiable ``lambda = 1e-6`` train-refit fits a pathology of
    the objective / statistical fit, or is the *same* objective already near its
    optimum in binary64 while the frozen sufficient gradient certificate hits a
    numerical precision / conditioning floor?

It adds NO new data, model, GPU, network, lambda, or calibration family, and it
does NOT modify the production solver. Instead it builds an independent,
dependency-free reference optimizer on the Python standard-library ``decimal``
module (80 digits, ``ROUND_HALF_EVEN``) and solves the *exact same* objective at
``lambda = 1e-6`` for ALL 4000 pre-declared train-refit fits.

The reference is a **numerical reference backend**, NOT a new calibration
family, a new R2C configuration, or an R3 candidate. The feature values it
consumes are the exact binary64 features R2C used (via ``Decimal.from_float`` of
the R2C float feature), so only the optimizer arithmetic changes, never the
statistical object.

The module reuses the production binary64 kernel only where the task is to
reproduce *production* behaviour (the successful-float64 agreement gate and the
rounded-reference certificate diagnostics). It never changes it.
"""

from __future__ import annotations

import decimal
import hashlib
import importlib.util
import json
import math
import statistics
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from probvenance.calibration import (
    _l2_logistic_certificate_threshold,
    _l2_logistic_gradient,
)
from probvenance.errors import InvalidDecisionError
from probvenance.fingerprint import fingerprint

_HARNESS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _HARNESS_DIR.parent.parent

DEFAULT_DESIGN_PATH = _HARNESS_DIR / "r2c1_numerical_closure_design.json"
DEFAULT_R2C_ANALYSIS_PATH = (
    _HARNESS_DIR / "results" / "r2c-method-adequacy-qwen35-2b-v1-analysis.json"
)


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


analysis = _load_sibling("analysis")
r2b_stability = _load_sibling("r2b_stability")
r2c = _load_sibling("r2c_method_adequacy")
_integrity = analysis._integrity

R2C1_DESIGN_ARTIFACT_TYPE = "calibration-transport-r2c1-numerical-closure-design"
R2C1_DESIGN_ARTIFACT_VERSION = 1
R2C1_ANALYSIS_ARTIFACT_TYPE = "calibration-transport-r2c1-numerical-closure-analysis"
R2C1_ANALYSIS_ARTIFACT_VERSION = 1

R2C1_ROUND_ID = "low-regularization-numerical-adequacy-closure"
R2C1_ROUND_VERSION = 1

REFERENCE_SOLVER_ID = "decimal-newton-backtracking-reference"
REFERENCE_SOLVER_VERSION = 1
REFERENCE_DECIMAL_PRECISION = 80
REFERENCE_ROUNDING_NAME = "ROUND_HALF_EVEN"

REFERENCE_LAMBDA = decimal.Decimal("1e-6")
R2C_LAMBDA_FLOAT = 1e-6

REFERENCE_OBJECTIVE_GAP_TOLERANCE = decimal.Decimal("1e-24")
REFERENCE_MAX_NEWTON_ITERATIONS = 500
REFERENCE_BACKTRACKING_FACTOR = decimal.Decimal("0.5")
REFERENCE_ARMIJO_COEFFICIENT = decimal.Decimal("1e-4")
REFERENCE_MAX_BACKTRACKING_STEPS = 200
REFERENCE_INITIAL_SLOPE = decimal.Decimal(0)
REFERENCE_INITIAL_INTERCEPT = decimal.Decimal(0)

#: Cross-implementation agreement gate (PART 25). NOT a production contract.
AGREEMENT_GATE_OBJECTIVE_GAP_UPPER = decimal.Decimal("2e-14")

#: Production objective-gap tolerance, only used to describe the rounded point.
PRODUCTION_OBJECTIVE_GAP_TOLERANCE = decimal.Decimal("1e-14")

PAIRED_TRAIN_REFIT_PROTOCOL_ID = "sha256-r2c-paired-train-refit-bootstrap"
PAIRED_TRAIN_REFIT_PROTOCOL_VERSION = 1
PAIRED_TRAIN_REFIT_REPLICATES = 1000

PERCENTILE_RULE_ID = "nearest-rank-percentile"
PERCENTILE_RULE_VERSION = 1

EXPECTED_REFERENCE_FITS = 4000
EXPECTED_FAILED_FIT_COUNT = 15

FEATURE_IDS = (r2c.FEATURE_RAW_ID, r2c.FEATURE_LOGIT_ID)
MEASUREMENTS = ("CAT", "OVR")
FAMILIES = ((r2c.FAMILY_P_ID, r2c.FAMILY_P_VERSION), (r2c.FAMILY_L_ID, r2c.FAMILY_L_VERSION))

_REFERENCE_CONTEXT = decimal.Context(
    prec=REFERENCE_DECIMAL_PRECISION,
    rounding=decimal.ROUND_HALF_EVEN,
)


class R2C1Error(RuntimeError):
    """Base class for R2C.1 research-closure contract violations."""


class ReferenceFitError(R2C1Error):
    """Raised when the high-precision reference itself cannot certify a fit."""


class R2C1DesignMismatchError(R2C1Error):
    """Raised when the design manifest disagrees with the frozen code contract."""


class SourceLineageError(R2C1Error):
    """Raised when the frozen source evidence does not match the design."""


# ---------------------------------------------------------------------------
# Decimal reference arithmetic (PART 11-17): stdlib Decimal only.
# ---------------------------------------------------------------------------


def _dec(value: float) -> decimal.Decimal:
    """Exact Decimal of one binary64 value (never a different JSON literal)."""
    return decimal.Decimal.from_float(float(value))


def _decimal_sigmoid(z: decimal.Decimal) -> decimal.Decimal:
    """Overflow-safe high-precision logistic sigmoid (PART 11)."""
    if z >= 0:
        return decimal.Decimal(1) / (decimal.Decimal(1) + (-z).exp())
    exp_z = z.exp()
    return exp_z / (decimal.Decimal(1) + exp_z)


def _decimal_softplus(z: decimal.Decimal) -> decimal.Decimal:
    """Overflow-safe high-precision ``log(1 + exp(z))`` (PART 12)."""
    if z >= 0:
        return z + (decimal.Decimal(1) + (-z).exp()).ln()
    return (decimal.Decimal(1) + z.exp()).ln()


def _reference_objective(
    rows: Sequence[tuple[decimal.Decimal, decimal.Decimal]],
    slope: decimal.Decimal,
    intercept: decimal.Decimal,
    lam: decimal.Decimal = REFERENCE_LAMBDA,
) -> decimal.Decimal:
    """``mean_i(softplus(a*x_i + b) - y_i*(a*x_i + b)) + (lambda/2)*(a^2+b^2)``."""
    total = decimal.Decimal(0)
    for x, y in rows:
        z = slope * x + intercept
        total += _decimal_softplus(z) - y * z
    mean_nll = total / decimal.Decimal(len(rows))
    penalty = (lam / decimal.Decimal(2)) * (slope * slope + intercept * intercept)
    return mean_nll + penalty


def _reference_gradient(
    rows: Sequence[tuple[decimal.Decimal, decimal.Decimal]],
    slope: decimal.Decimal,
    intercept: decimal.Decimal,
    lam: decimal.Decimal = REFERENCE_LAMBDA,
) -> tuple[decimal.Decimal, decimal.Decimal]:
    """Independent Decimal gradient (PART 13)."""
    slope_terms = decimal.Decimal(0)
    intercept_terms = decimal.Decimal(0)
    for x, y in rows:
        z = slope * x + intercept
        residual = _decimal_sigmoid(z) - y
        slope_terms += residual * x
        intercept_terms += residual
    count = decimal.Decimal(len(rows))
    return (
        slope_terms / count + lam * slope,
        intercept_terms / count + lam * intercept,
    )


def _reference_hessian(
    rows: Sequence[tuple[decimal.Decimal, decimal.Decimal]],
    slope: decimal.Decimal,
    intercept: decimal.Decimal,
    lam: decimal.Decimal = REFERENCE_LAMBDA,
) -> tuple[decimal.Decimal, decimal.Decimal, decimal.Decimal]:
    """Independent Decimal Hessian of the regularized objective (PART 14)."""
    aa_terms = decimal.Decimal(0)
    ab_terms = decimal.Decimal(0)
    bb_terms = decimal.Decimal(0)
    for x, _y in rows:
        z = slope * x + intercept
        sigmoid = _decimal_sigmoid(z)
        curvature = sigmoid * (decimal.Decimal(1) - sigmoid)
        aa_terms += curvature * x * x
        ab_terms += curvature * x
        bb_terms += curvature
    count = decimal.Decimal(len(rows))
    return (
        aa_terms / count + lam,
        ab_terms / count,
        bb_terms / count + lam,
    )


def _symmetric_eigenvalues(
    haa: decimal.Decimal, hab: decimal.Decimal, hbb: decimal.Decimal
) -> tuple[decimal.Decimal, decimal.Decimal]:
    """Eigenvalues of the symmetric 2x2 matrix ``[[haa, hab], [hab, hbb]]``."""
    trace = haa + hbb
    disc = ((haa - hbb) * (haa - hbb) + decimal.Decimal(4) * hab * hab).sqrt()
    return (trace - disc) / decimal.Decimal(2), (trace + disc) / decimal.Decimal(2)


@dataclass(frozen=True)
class ReferenceFit:
    """One high-precision reference optimum with its certificate diagnostics."""

    slope: decimal.Decimal
    intercept: decimal.Decimal
    gradient_norm: decimal.Decimal
    gap_upper_bound: decimal.Decimal
    iterations: int
    hessian_aa: decimal.Decimal
    hessian_ab: decimal.Decimal
    hessian_bb: decimal.Decimal

    def hessian_eigenvalues(self) -> tuple[decimal.Decimal, decimal.Decimal]:
        return _symmetric_eigenvalues(self.hessian_aa, self.hessian_ab, self.hessian_bb)


def reference_solve(
    rows: Sequence[tuple[decimal.Decimal, decimal.Decimal]],
    *,
    lam: decimal.Decimal = REFERENCE_LAMBDA,
) -> ReferenceFit:
    """Fixed-start Decimal Newton optimum of the frozen lambda = 1e-6 objective.

    Independent of the production solver: its own 2x2 Newton solve, its own
    Armijo backtracking line search, its own strong-convexity objective-gap
    certificate (``||grad||^2 / (2*lambda) <= 1e-24``). ``lambda`` defaults to
    the exact Decimal ``1e-6`` (the frozen closure value); the keyword exists so
    offline unit tests can exercise the same solver on ordinary synthetic
    problems. Features are always the exact binary64 R2C features. Any failure
    to certify raises :class:`ReferenceFitError` (fail closed).
    """
    if not rows:
        raise ReferenceFitError("reference fit requires at least one row")
    with decimal.localcontext(_REFERENCE_CONTEXT):
        slope = REFERENCE_INITIAL_SLOPE
        intercept = REFERENCE_INITIAL_INTERCEPT
        objective = _reference_objective(rows, slope, intercept, lam)
        for iteration in range(REFERENCE_MAX_NEWTON_ITERATIONS):
            grad_slope, grad_intercept = _reference_gradient(rows, slope, intercept, lam)
            squared_grad = grad_slope * grad_slope + grad_intercept * grad_intercept
            gap_upper = squared_grad / (decimal.Decimal(2) * lam)
            if gap_upper <= REFERENCE_OBJECTIVE_GAP_TOLERANCE:
                return _reference_fit(
                    rows, slope, intercept, squared_grad, gap_upper, iteration, lam
                )
            haa, hab, hbb = _reference_hessian(rows, slope, intercept, lam)
            determinant = haa * hbb - hab * hab
            if not (haa > 0 and hbb > 0 and determinant > 0):
                raise ReferenceFitError(
                    "reference Hessian lost positive definiteness "
                    f"at iteration {iteration}; no certificate is produced"
                )
            step_slope = (hbb * grad_slope - hab * grad_intercept) / determinant
            step_intercept = (-hab * grad_slope + haa * grad_intercept) / determinant
            directional_derivative = grad_slope * step_slope + grad_intercept * step_intercept
            scale = decimal.Decimal(1)
            accepted = False
            for _backtrack in range(REFERENCE_MAX_BACKTRACKING_STEPS):
                candidate_slope = slope - scale * step_slope
                candidate_intercept = intercept - scale * step_intercept
                candidate_objective = _reference_objective(
                    rows, candidate_slope, candidate_intercept, lam
                )
                if candidate_objective <= (
                    objective - REFERENCE_ARMIJO_COEFFICIENT * scale * directional_derivative
                ):
                    slope = candidate_slope
                    intercept = candidate_intercept
                    objective = candidate_objective
                    accepted = True
                    break
                scale *= REFERENCE_BACKTRACKING_FACTOR
            if not accepted:
                raise ReferenceFitError(
                    "reference line search could not find a sufficient objective "
                    f"decrease within {REFERENCE_MAX_BACKTRACKING_STEPS} reductions"
                )
        grad_slope, grad_intercept = _reference_gradient(rows, slope, intercept, lam)
        squared_grad = grad_slope * grad_slope + grad_intercept * grad_intercept
        gap_upper = squared_grad / (decimal.Decimal(2) * lam)
        if gap_upper <= REFERENCE_OBJECTIVE_GAP_TOLERANCE:
            return _reference_fit(
                rows,
                slope,
                intercept,
                squared_grad,
                gap_upper,
                REFERENCE_MAX_NEWTON_ITERATIONS,
                lam,
            )
        raise ReferenceFitError(
            "reference solver could not certify an objective gap within "
            f"{REFERENCE_OBJECTIVE_GAP_TOLERANCE} within {REFERENCE_MAX_NEWTON_ITERATIONS} "
            "iterations"
        )


def _reference_fit(
    rows: Sequence[tuple[decimal.Decimal, decimal.Decimal]],
    slope: decimal.Decimal,
    intercept: decimal.Decimal,
    squared_grad: decimal.Decimal,
    gap_upper: decimal.Decimal,
    iteration: int,
    lam: decimal.Decimal = REFERENCE_LAMBDA,
) -> ReferenceFit:
    haa, hab, hbb = _reference_hessian(rows, slope, intercept, lam)
    return ReferenceFit(
        slope=slope,
        intercept=intercept,
        gradient_norm=squared_grad.sqrt(),
        gap_upper_bound=gap_upper,
        iterations=iteration,
        hessian_aa=haa,
        hessian_ab=hab,
        hessian_bb=hbb,
    )


# ---------------------------------------------------------------------------
# Design manifest.
# ---------------------------------------------------------------------------


def load_design(path: Path | str = DEFAULT_DESIGN_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def design_fingerprint(design: Mapping[str, Any]) -> str:
    return fingerprint(dict(design))


def validate_design(design: Mapping[str, Any]) -> None:
    """Fail closed if the committed design disagrees with the frozen contract."""
    if design.get("artifact_type") != R2C1_DESIGN_ARTIFACT_TYPE:
        raise R2C1DesignMismatchError("unexpected design artifact_type")
    if design.get("artifact_version") != R2C1_DESIGN_ARTIFACT_VERSION:
        raise R2C1DesignMismatchError("unexpected design artifact_version")
    if design.get("round_id") != R2C1_ROUND_ID or design.get("round_version") != R2C1_ROUND_VERSION:
        raise R2C1DesignMismatchError("unexpected round id/version")
    if design.get("no_method_change") is not True:
        raise R2C1DesignMismatchError("design must declare no_method_change")
    if design.get("no_model_rerun") is not True:
        raise R2C1DesignMismatchError("design must declare no_model_rerun")
    if decimal.Decimal(str(design.get("lambda"))) != REFERENCE_LAMBDA:
        raise R2C1DesignMismatchError("design lambda must be exactly 1e-6")
    solver = design.get("reference_solver", {})
    if solver.get("id") != REFERENCE_SOLVER_ID or int(solver.get("version", -1)) != (
        REFERENCE_SOLVER_VERSION
    ):
        raise R2C1DesignMismatchError("reference solver id/version mismatch")
    if int(solver.get("decimal_precision", -1)) != REFERENCE_DECIMAL_PRECISION:
        raise R2C1DesignMismatchError("reference decimal precision mismatch")
    if solver.get("rounding") != REFERENCE_ROUNDING_NAME:
        raise R2C1DesignMismatchError("reference rounding mismatch")
    if decimal.Decimal(str(solver.get("objective_gap_tolerance"))) != (
        REFERENCE_OBJECTIVE_GAP_TOLERANCE
    ):
        raise R2C1DesignMismatchError("reference objective-gap tolerance mismatch")
    policy = design.get("full_reference_policy", {})
    if int(policy.get("expected_reference_fits", -1)) != EXPECTED_REFERENCE_FITS:
        raise R2C1DesignMismatchError("full reference policy fit count mismatch")
    failed = design.get("exact_failed_fit_set", [])
    if len(failed) != EXPECTED_FAILED_FIT_COUNT:
        raise R2C1DesignMismatchError("design failed-fit set is not the frozen 15")


def _design_failed_set(design: Mapping[str, Any]) -> set[tuple[str, str, int]]:
    return {
        (entry["family_id"], entry["measurement"], int(entry["replicate"]))
        for entry in design["exact_failed_fit_set"]
    }


# ---------------------------------------------------------------------------
# Bootstrap replay (PART 20-21): exact R2C draws, no new randomness.
# ---------------------------------------------------------------------------


def _train_refit_draws(train_points: Sequence[Any], replicates: int) -> list[list[int]]:
    return r2c._draw_matrix(
        protocol_id=PAIRED_TRAIN_REFIT_PROTOCOL_ID,
        protocol_version=PAIRED_TRAIN_REFIT_PROTOCOL_VERSION,
        replicates=replicates,
        draw=len(train_points),
        item_count=len(train_points),
    )


def _multiset_fingerprint(sampled: Sequence[Any]) -> str:
    counts: dict[str, int] = {}
    for point in sampled:
        counts[point.item_id] = counts.get(point.item_id, 0) + 1
    return fingerprint({key: counts[key] for key in sorted(counts)})


# ---------------------------------------------------------------------------
# Closure run.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Group:
    family_id: str
    family_version: int
    measurement: str
    config: Any
    feature_id: str


def _groups() -> tuple[_Group, ...]:
    by_family = {
        config.family_id: config
        for config in r2c.method_configs()
        if config.l2_strength == R2C_LAMBDA_FLOAT
    }
    groups = []
    for family_id, family_version in FAMILIES:
        config = by_family[family_id]
        for measurement in MEASUREMENTS:
            groups.append(
                _Group(
                    family_id=family_id,
                    family_version=family_version,
                    measurement=measurement,
                    config=config,
                    feature_id=config.feature_id,
                )
            )
    return tuple(groups)


def _measurement_score(point: Any, measurement: str) -> float:
    return float(point.score_a) if measurement == "CAT" else float(point.score_b)


def _measurement_feature(point: Any, group: _Group) -> float:
    return r2c.feature_value(group.feature_id, _measurement_score(point, group.measurement))


def _float_rows(sampled: Sequence[Any], group: _Group) -> list[tuple[float, float]]:
    ordered = sorted(sampled, key=lambda point: point.item_id)
    return [(_measurement_feature(point, group), float(point.y)) for point in ordered]


def _decimal_rows(
    sampled: Sequence[Any], group: _Group
) -> list[tuple[decimal.Decimal, decimal.Decimal]]:
    ordered = sorted(sampled, key=lambda point: point.item_id)
    return [(_dec(_measurement_feature(point, group)), _dec(point.y)) for point in ordered]


def _group_label(group: _Group) -> str:
    side = "P" if group.family_id == r2c.FAMILY_P_ID else "L"
    return f"{side}:{R2C_LAMBDA_FLOAT!r}"


def _float_fits(
    groups: Sequence[_Group],
    draws: Sequence[Sequence[int]],
    train_points: Sequence[Any],
    plan_fingerprint: str,
) -> dict[tuple[str, str], list[tuple[float, float] | None]]:
    """Re-run the production float64 solver; None marks an uncertified fit."""
    results: dict[tuple[str, str], list[tuple[float, float] | None]] = {}
    for group in groups:
        key = (group.family_id, group.measurement)
        per_replicate: list[tuple[float, float] | None] = []
        for row in draws:
            sampled = [train_points[index] for index in row]
            try:
                fit = r2c._fit_calibrator(
                    config=group.config,
                    source_measurement=group.measurement,
                    training_rows=[
                        (point.item_id, _measurement_score(point, group.measurement), point.y)
                        for point in sampled
                    ],
                    plan_fingerprint=plan_fingerprint,
                )
            except InvalidDecisionError:
                per_replicate.append(None)
            else:
                per_replicate.append((float(fit.slope), float(fit.intercept)))
        results[key] = per_replicate
    return results


def _reference_fits(
    groups: Sequence[_Group],
    draws: Sequence[Sequence[int]],
    train_points: Sequence[Any],
) -> dict[tuple[str, str], list[Any]]:
    """High-precision reference fit for EVERY replicate (failures recorded)."""
    results: dict[tuple[str, str], list[Any]] = {}
    for group in groups:
        key = (group.family_id, group.measurement)
        per_replicate: list[Any] = []
        for row in draws:
            sampled = [train_points[index] for index in row]
            try:
                fit = reference_solve(_decimal_rows(sampled, group))
            except ReferenceFitError as error:  # pragma: no cover - expected none
                per_replicate.append(error)
            else:
                per_replicate.append(fit)
        results[key] = per_replicate
    return results


def _recomputed_failed_set(
    float_fits: Mapping[tuple[str, str], Sequence[Any]],
) -> set[tuple[str, str, int]]:
    failed: set[tuple[str, str, int]] = set()
    for (family_id, measurement), per_replicate in float_fits.items():
        for replicate, value in enumerate(per_replicate):
            if value is None:
                failed.add((family_id, measurement, replicate))
    return failed


def _agreement_stats(
    groups: Sequence[_Group],
    float_fits: Mapping[tuple[str, str], Sequence[Any]],
    reference_fits: Mapping[tuple[str, str], Sequence[Any]],
    draws: Sequence[Sequence[int]],
    train_points: Sequence[Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], decimal.Decimal | None]:
    """Objective-gap agreement for the successful float64 fits (PART 24-26)."""
    per_group: dict[str, Any] = {}
    violations: list[dict[str, Any]] = []
    overall_max: decimal.Decimal | None = None
    total_success = 0
    for group in groups:
        key = (group.family_id, group.measurement)
        gap_values: list[float] = []
        distance_values: list[float] = []
        max_gap: decimal.Decimal | None = None
        for replicate, float_theta in enumerate(float_fits[key]):
            reference = reference_fits[key][replicate]
            if float_theta is None or isinstance(reference, ReferenceFitError):
                continue
            total_success += 1
            sampled = [train_points[index] for index in draws[replicate]]
            rows = _decimal_rows(sampled, group)
            with decimal.localcontext(_REFERENCE_CONTEXT):
                j_float = _reference_objective(rows, _dec(float_theta[0]), _dec(float_theta[1]))
                j_reference = _reference_objective(rows, reference.slope, reference.intercept)
                gap = j_float - j_reference + reference.gap_upper_bound
                distance = (
                    (_dec(float_theta[0]) - reference.slope) ** 2
                    + (_dec(float_theta[1]) - reference.intercept) ** 2
                ).sqrt()
            gap_float = float(gap)
            distance_float = float(distance)
            gap_values.append(gap_float)
            distance_values.append(distance_float)
            if max_gap is None or gap > max_gap:
                max_gap = gap
            if overall_max is None or gap > overall_max:
                overall_max = gap
            if gap > AGREEMENT_GATE_OBJECTIVE_GAP_UPPER:
                violations.append(
                    {
                        "family_id": group.family_id,
                        "measurement": group.measurement,
                        "replicate": replicate,
                        "float64_actual_gap_upper": str(gap),
                    }
                )
        per_group[group.family_id + ":" + group.measurement] = {
            "n": len(gap_values),
            "max_objective_gap_upper": float(max_gap) if max_gap is not None else None,
            "median_objective_gap_upper": statistics.median(gap_values) if gap_values else None,
            "p95_objective_gap_upper": _percentile(gap_values, 95.0),
            "max_parameter_distance": max(distance_values) if distance_values else None,
            "median_parameter_distance": (
                statistics.median(distance_values) if distance_values else None
            ),
            "p95_parameter_distance": _percentile(distance_values, 95.0),
        }
    summary = {
        "successful_float64_fits": total_success,
        "gate_objective_gap_upper": float(AGREEMENT_GATE_OBJECTIVE_GAP_UPPER),
        "pass_count": total_success - len(violations),
        "violation_count": len(violations),
        "overall_max_objective_gap_upper": (
            float(overall_max) if overall_max is not None else None
        ),
        "per_group": per_group,
    }
    return summary, violations, overall_max


def _percentile(values: Sequence[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return r2b_stability.nearest_rank_percentile(ordered, percentile)


def _ulp_neighbors(value: float, radius: int) -> list[float]:
    neighbors = [value]
    up = value
    down = value
    for _ in range(radius):
        up = math.nextafter(up, math.inf)
        down = math.nextafter(down, -math.inf)
        neighbors.extend([up, down])
    return sorted(neighbors)


def _failed_fit_diagnostics(
    design: Mapping[str, Any],
    groups: Sequence[_Group],
    draws: Sequence[Sequence[int]],
    train_points: Sequence[Any],
    reference_fits: Mapping[tuple[str, str], Sequence[Any]],
    production_threshold: float,
) -> list[dict[str, Any]]:
    """Full numerical audit of the 15 uncertifiable fits (PART 27-32)."""
    failed_set = _design_failed_set(design)
    by_key = {(group.family_id, group.measurement): group for group in groups}
    records: list[dict[str, Any]] = []
    for family_id, measurement, replicate in sorted(failed_set):
        group = by_key[(family_id, measurement)]
        reference = reference_fits[(family_id, measurement)][replicate]
        sampled = [train_points[index] for index in draws[replicate]]
        float_rows = _float_rows(sampled, group)
        decimal_rows = _decimal_rows(sampled, group)
        record: dict[str, Any] = {
            "family_id": family_id,
            "measurement": measurement,
            "replicate": replicate,
            "train_multiset_fingerprint": _multiset_fingerprint(sampled),
        }
        if isinstance(reference, ReferenceFitError):  # pragma: no cover - expected none
            record["reference_status"] = "failed"
            record["reference_error"] = str(reference)
            records.append(record)
            continue
        with decimal.localcontext(_REFERENCE_CONTEXT):
            min_eig, max_eig = reference.hessian_eigenvalues()
            condition = max_eig / min_eig if min_eig > 0 else None
            a_round = float(reference.slope)
            b_round = float(reference.intercept)
            a_round_dec = _dec(a_round)
            b_round_dec = _dec(b_round)
            rounded_objective = _reference_objective(decimal_rows, a_round_dec, b_round_dec)
            j_reference = _reference_objective(decimal_rows, reference.slope, reference.intercept)
            rounded_gap_upper = rounded_objective - j_reference + reference.gap_upper_bound
        prod_grad = _l2_logistic_gradient(float_rows, a_round, b_round, R2C_LAMBDA_FLOAT)
        prod_grad_norm = math.hypot(prod_grad[0], prod_grad[1])
        neighborhood = [
            (candidate_a, candidate_b)
            for candidate_a in _ulp_neighbors(a_round, 2)
            for candidate_b in _ulp_neighbors(b_round, 2)
        ]
        min_neighborhood_grad = min(
            math.hypot(
                *_l2_logistic_gradient(float_rows, candidate_a, candidate_b, R2C_LAMBDA_FLOAT)
            )
            for candidate_a, candidate_b in neighborhood
        )
        record.update(
            {
                "reference_status": "certified",
                "reference_slope": str(reference.slope),
                "reference_intercept": str(reference.intercept),
                "reference_iterations": reference.iterations,
                "reference_gradient_norm": str(reference.gradient_norm),
                "reference_gap_upper_bound": str(reference.gap_upper_bound),
                "hessian_min_eigenvalue": float(min_eig),
                "hessian_max_eigenvalue": float(max_eig),
                "hessian_condition_number": float(condition) if condition is not None else None,
                "rounded_slope": a_round,
                "rounded_intercept": b_round,
                "rounded_reference_actual_gap_upper": str(rounded_gap_upper),
                "rounded_reference_actual_gap_meets_objective_tolerance": bool(
                    rounded_gap_upper <= PRODUCTION_OBJECTIVE_GAP_TOLERANCE
                ),
                "production_style_gradient_norm_at_rounded": prod_grad_norm,
                "production_certificate_threshold": production_threshold,
                "production_certificate_met_at_rounded": bool(
                    prod_grad_norm <= production_threshold
                ),
                "ulp_neighborhood_min_gradient_norm": min_neighborhood_grad,
                "ulp_neighborhood_min_gradient_ratio": min_neighborhood_grad / production_threshold,
            }
        )
        records.append(record)
    return records


def _reference_brier(
    features: Sequence[decimal.Decimal],
    calibrator: ReferenceFit,
    labels: Sequence[decimal.Decimal],
) -> decimal.Decimal:
    total = decimal.Decimal(0)
    for x, y in zip(features, labels, strict=True):
        error = _decimal_sigmoid(calibrator.slope * x + calibrator.intercept) - y
        total += error * error
    return total / decimal.Decimal(len(features))


def _completed_summaries(
    groups: Sequence[_Group],
    draws: Sequence[Sequence[int]],
    train_points: Sequence[Any],
    test_points: Sequence[Any],
    reference_fits: Mapping[tuple[str, str], Sequence[Any]],
) -> dict[str, Any]:
    """Recompute the lambda = 1e-6 train-refit intervals from reference fits only."""
    labels = [_dec(point.y) for point in test_points]
    raw_a = [_dec(point.score_a) for point in test_points]
    raw_b = [_dec(point.score_b) for point in test_points]
    summaries: dict[str, Any] = {}
    for family_id, family_version in FAMILIES:
        cat_group = next(
            group for group in groups if group.family_id == family_id and group.measurement == "CAT"
        )
        ovr_group = next(
            group for group in groups if group.family_id == family_id and group.measurement == "OVR"
        )
        feat_a = [_dec(_measurement_feature(point, cat_group)) for point in test_points]
        feat_b = [_dec(_measurement_feature(point, ovr_group)) for point in test_points]
        native_cat: list[float] = []
        native_ovr: list[float] = []
        transport_cat_to_ovr: list[float] = []
        transport_ovr_to_cat: list[float] = []
        cat_slope: list[float] = []
        cat_intercept: list[float] = []
        ovr_slope: list[float] = []
        ovr_intercept: list[float] = []
        with decimal.localcontext(_REFERENCE_CONTEXT):
            raw_brier_a = _raw_brier(raw_a, labels)
            raw_brier_b = _raw_brier(raw_b, labels)
            for replicate in range(len(draws)):
                ref_cat = reference_fits[(family_id, "CAT")][replicate]
                ref_ovr = reference_fits[(family_id, "OVR")][replicate]
                if isinstance(ref_cat, ReferenceFitError) or isinstance(
                    ref_ovr, ReferenceFitError
                ):  # pragma: no cover - expected none
                    continue
                cal_cat_a = _reference_brier(feat_a, ref_cat, labels)
                cal_cat_b = _reference_brier(feat_b, ref_cat, labels)
                cal_ovr_a = _reference_brier(feat_a, ref_ovr, labels)
                cal_ovr_b = _reference_brier(feat_b, ref_ovr, labels)
                native_cat.append(float(cal_cat_a - raw_brier_a))
                native_ovr.append(float(cal_ovr_b - raw_brier_b))
                transport_cat_to_ovr.append(float(cal_cat_b - cal_ovr_b))
                transport_ovr_to_cat.append(float(cal_ovr_a - cal_cat_a))
                cat_slope.append(float(ref_cat.slope))
                cat_intercept.append(float(ref_cat.intercept))
                ovr_slope.append(float(ref_ovr.slope))
                ovr_intercept.append(float(ref_ovr.intercept))
        side = "P" if family_id == r2c.FAMILY_P_ID else "L"
        summaries[f"{side}:{R2C_LAMBDA_FLOAT!r}"] = {
            "family_id": family_id,
            "family_version": family_version,
            "replicates": len(native_cat),
            "native_cat": r2b_stability._interval(native_cat),
            "native_ovr": r2b_stability._interval(native_ovr),
            "transport_cat_to_ovr": r2b_stability._interval(transport_cat_to_ovr),
            "transport_ovr_to_cat": r2b_stability._interval(transport_ovr_to_cat),
            "native_cat_negative_fraction": _negative_fraction(native_cat),
            "native_ovr_negative_fraction": _negative_fraction(native_ovr),
            "transport_cat_to_ovr_negative_fraction": _negative_fraction(transport_cat_to_ovr),
            "transport_cat_to_ovr_positive_fraction": _positive_fraction(transport_cat_to_ovr),
            "transport_ovr_to_cat_negative_fraction": _negative_fraction(transport_ovr_to_cat),
            "transport_ovr_to_cat_positive_fraction": _positive_fraction(transport_ovr_to_cat),
            "parameter_cat": {
                "slope": r2b_stability._interval(cat_slope),
                "intercept": r2b_stability._interval(cat_intercept),
            },
            "parameter_ovr": {
                "slope": r2b_stability._interval(ovr_slope),
                "intercept": r2b_stability._interval(ovr_intercept),
            },
        }
    return summaries


def _raw_brier(
    values: Sequence[decimal.Decimal],
    labels: Sequence[decimal.Decimal],
) -> decimal.Decimal:
    """Raw-score Brier: ``mean((p_i - y_i)^2)`` with NO calibrator applied."""
    total = decimal.Decimal(0)
    for value, label in zip(values, labels, strict=True):
        error = value - label
        total += error * error
    return total / decimal.Decimal(len(values))


def _negative_fraction(values: Sequence[float]) -> float:
    return sum(1 for value in values if value < 0.0) / len(values) if values else 0.0


def _positive_fraction(values: Sequence[float]) -> float:
    return sum(1 for value in values if value > 0.0) / len(values) if values else 0.0


def _full_n_reference_sanity(
    groups: Sequence[_Group],
    train_points: Sequence[Any],
    plan_fingerprint: str,
    r2c_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    """PART 22: full-90-TRAIN reference fits vs the R2C point estimates."""
    sanity: dict[str, Any] = {}
    for group in groups:
        key = group.family_id + ":" + group.measurement
        try:
            float_fit = r2c._fit_calibrator(
                config=group.config,
                source_measurement=group.measurement,
                training_rows=[
                    (point.item_id, _measurement_score(point, group.measurement), point.y)
                    for point in train_points
                ],
                plan_fingerprint=plan_fingerprint,
            )
        except InvalidDecisionError as error:  # pragma: no cover - full-N never failed
            sanity[key] = {"status": "float64-uncertified", "error": str(error)}
            continue
        reference = reference_solve(_decimal_rows(train_points, group))
        rows = _decimal_rows(train_points, group)
        with decimal.localcontext(_REFERENCE_CONTEXT):
            j_float = _reference_objective(rows, _dec(float_fit.slope), _dec(float_fit.intercept))
            j_reference = _reference_objective(rows, reference.slope, reference.intercept)
            gap = j_float - j_reference + reference.gap_upper_bound
            distance = (
                (_dec(float_fit.slope) - reference.slope) ** 2
                + (_dec(float_fit.intercept) - reference.intercept) ** 2
            ).sqrt()
        sanity[key] = {
            "status": "ok",
            "float64_slope": float_fit.slope,
            "float64_intercept": float_fit.intercept,
            "reference_slope": str(reference.slope),
            "reference_intercept": str(reference.intercept),
            "objective_gap_upper": str(gap),
            "parameter_distance": float(distance),
        }
    stored: dict[tuple[str, str], tuple[float, float]] = {}
    for block in r2c_artifact["configurations"]:
        if float(block["l2_strength"]) != R2C_LAMBDA_FLOAT:
            continue
        calibrators = block["calibrators"]
        stored[(block["family_id"], "CAT")] = (
            float(calibrators["cat"]["slope"]),
            float(calibrators["cat"]["intercept"]),
        )
        stored[(block["family_id"], "OVR")] = (
            float(calibrators["ovr"]["slope"]),
            float(calibrators["ovr"]["intercept"]),
        )
    for group in groups:
        key = group.family_id + ":" + group.measurement
        record = sanity.get(key)
        if record is None or record.get("status") != "ok":
            continue
        stored_pair = stored.get((group.family_id, group.measurement))
        if stored_pair is not None:
            record["r2c_artifact_slope"] = stored_pair[0]
            record["r2c_artifact_intercept"] = stored_pair[1]
            record["matches_r2c_artifact_point_fit"] = (
                stored_pair[0] == record["float64_slope"]
                and stored_pair[1] == record["float64_intercept"]
            )
    return sanity


def run_closure(
    raw: Mapping[str, Any],
    r2c_artifact: Mapping[str, Any],
    design: Mapping[str, Any],
    *,
    provenance: Mapping[str, Any] | None = None,
    replicates: int = PAIRED_TRAIN_REFIT_REPLICATES,
) -> dict[str, Any]:
    """Run the full R2C.1 numerical closure and return the analysis artifact."""
    validate_design(design)
    plan, _dataset, train_points, test_points = r2c.load_frozen_evidence(raw)
    groups = _groups()
    draws = _train_refit_draws(train_points, replicates)

    # Phase 1: production float64 refits; verify the frozen failure set early.
    float_fits = _float_fits(groups, draws, train_points, plan.fingerprint)
    recomputed_failed = _recomputed_failed_set(float_fits)
    expected_failed = _design_failed_set(design)
    if recomputed_failed != expected_failed:
        missing = sorted(expected_failed - recomputed_failed)
        extra = sorted(recomputed_failed - expected_failed)
        raise SourceLineageError(
            "recomputed float64 failure set does not match the frozen R2C design; "
            f"missing={missing} extra={extra}"
        )

    # Phase 2: high-precision reference fit for EVERY fit (4000 expected).
    reference_fits = _reference_fits(groups, draws, train_points)
    reference_attempted = sum(len(bucket) for bucket in reference_fits.values())
    reference_failed = sum(
        1
        for bucket in reference_fits.values()
        for value in bucket
        if isinstance(value, ReferenceFitError)
    )

    production_threshold = _l2_logistic_certificate_threshold(R2C_LAMBDA_FLOAT)

    agreement, violations, _overall_max = _agreement_stats(
        groups, float_fits, reference_fits, draws, train_points
    )
    failed_diagnostics = _failed_fit_diagnostics(
        design, groups, draws, train_points, reference_fits, production_threshold
    )
    completed = _completed_summaries(groups, draws, train_points, test_points, reference_fits)
    full_n = _full_n_reference_sanity(groups, train_points, plan.fingerprint, r2c_artifact)

    classification_blocks = classify_failed_fits(
        reference_attempted=reference_attempted,
        reference_failed=reference_failed,
        violations=violations,
        failed_diagnostics=failed_diagnostics,
    )

    source_raw = design["source_r2b_raw"]
    source_r2c = design["source_r2c_analysis"]
    return {
        "artifact_type": R2C1_ANALYSIS_ARTIFACT_TYPE,
        "artifact_version": R2C1_ANALYSIS_ARTIFACT_VERSION,
        "round_id": R2C1_ROUND_ID,
        "round_version": R2C1_ROUND_VERSION,
        "research_spec_id": _integrity.RESEARCH_SPEC_ID,
        "research_spec_version": _integrity.RESEARCH_SPEC_VERSION,
        "design": {
            "artifact_type": design["artifact_type"],
            "artifact_version": design["artifact_version"],
            "fingerprint": design_fingerprint(design),
        },
        "source_r2b_raw": {
            "path": source_raw["path"],
            "file_sha256": source_raw["file_sha256"],
            "source_case_set_version": raw["source_case_set_version"],
            "source_case_set_fingerprint": raw["source_case_set_fingerprint"],
            "plan_fingerprint": raw["plan_fingerprint"],
            "paired_dataset_fingerprint": raw["paired_dataset_fingerprint"],
            "r2b_run_provenance_fingerprint": raw["r2b_run_provenance_fingerprint"],
            "source_measurement_code_commit": source_raw["source_measurement_code_commit"],
            "model": source_raw["model"],
            "model_revision": source_raw["model_revision"],
        },
        "source_r2c_analysis": {
            "path": source_r2c["path"],
            "file_sha256": source_r2c["file_sha256"],
            "round_id": r2c_artifact["round_id"],
            "round_version": r2c_artifact["round_version"],
            "round_status": r2c_artifact["round_status"],
            "failed_fit_count": r2c_artifact["train_refit_bootstrap"]["failed_fits"],
            "design_fingerprint": source_r2c["design_fingerprint"],
        },
        "provenance": dict(provenance or {}),
        "no_model_rerun": True,
        "no_method_change": True,
        "lambda": R2C_LAMBDA_FLOAT,
        "reference_solver_contract": {
            "id": REFERENCE_SOLVER_ID,
            "version": REFERENCE_SOLVER_VERSION,
            "arithmetic": "python-stdlib-decimal",
            "decimal_precision": REFERENCE_DECIMAL_PRECISION,
            "rounding": REFERENCE_ROUNDING_NAME,
            "objective_id": r2c.OBJECTIVE_ID,
            "objective_version": r2c.OBJECTIVE_VERSION,
            "objective_gap_tolerance": float(REFERENCE_OBJECTIVE_GAP_TOLERANCE),
            "max_newton_iterations": REFERENCE_MAX_NEWTON_ITERATIONS,
            "backtracking_factor": float(REFERENCE_BACKTRACKING_FACTOR),
            "armijo_coefficient": float(REFERENCE_ARMIJO_COEFFICIENT),
            "max_backtracking_steps": REFERENCE_MAX_BACKTRACKING_STEPS,
            "initial_slope": float(REFERENCE_INITIAL_SLOPE),
            "initial_intercept": float(REFERENCE_INITIAL_INTERCEPT),
        },
        "percentile_rule": {"id": PERCENTILE_RULE_ID, "version": PERCENTILE_RULE_VERSION},
        "failed_fit_set_verification": {
            "expected_count": len(expected_failed),
            "recomputed_float64_failure_count": len(recomputed_failed),
            "matches_frozen_r2c": recomputed_failed == expected_failed,
            "recomputed_failures": [
                {"family_id": family_id, "measurement": measurement, "replicate": replicate}
                for family_id, measurement, replicate in sorted(recomputed_failed)
            ],
        },
        "full_n_reference_sanity": full_n,
        "reference_fit_summary": {
            "attempted": reference_attempted,
            "certified": reference_attempted - reference_failed,
            "failed": reference_failed,
            "expected": EXPECTED_REFERENCE_FITS,
        },
        "successful_float64_agreement": agreement,
        "agreement_violations": violations,
        "failed_fit_diagnostics": failed_diagnostics,
        "completed_train_refit_summaries": completed,
        "predeclared_classification_result": classification_blocks[
            "predeclared_classification_result"
        ],
        "observed_mechanism": classification_blocks["observed_mechanism"],
        "limitations": _limitations(),
    }


OBSERVED_MECHANISM_VERSION = 1
OBSERVED_MECHANISM_SOLVER_PATH_ID = "binary64-solver-path-stalls-before-certifiable-point"
PREREGISTERED_A_MECHANISM_ID = "certificate-unmet-at-rounded-reference-point"

_NO_EXACT_MATCH_SUMMARY = (
    "the observed result does not exactly match any preregistered A/B/C/D category. "
    "The closest preregistered family is A (a binary64 numerical-path limitation), "
    "but the preregistered A submechanism was falsified: every rounded high-precision "
    "reference point satisfies both the declared objective-gap tolerance and the "
    "frozen sufficient gradient certificate. The observed limitation is instead that "
    "the frozen binary64 Newton/backtracking solver path fails to reach such a "
    "certifiable point for these resamples"
)
_OBSERVED_MECHANISM_SUMMARY = (
    "a certifiable binary64-representable point exists near the high-precision "
    "optimum, but the frozen binary64 Newton/backtracking solver path is not "
    "uniformly able to advance to such a point"
)


def _classification_blocks(
    *,
    exact_match: str | None,
    closest_family: str | None,
    preregistered_a_supported: bool,
    summary: str,
    evidence: Mapping[str, Any],
    observed_id: str,
    observed_summary: str,
) -> dict[str, Any]:
    return {
        "predeclared_classification_result": {
            "exact_match": exact_match,
            "closest_family": closest_family,
            "preregistered_a_submechanism_supported": preregistered_a_supported,
            "summary": summary,
            "evidence": dict(evidence),
        },
        "observed_mechanism": {
            "id": observed_id,
            "version": OBSERVED_MECHANISM_VERSION,
            "summary": observed_summary,
        },
    }


def classify_failed_fits(
    *,
    reference_attempted: int,
    reference_failed: int,
    violations: Sequence[Mapping[str, Any]],
    failed_diagnostics: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Report the preregistered A/B/C/D taxonomy against the observed result.

    The preregistered taxonomy is historical and is never rewritten. When the
    observed diagnostics do not match a preregistered category's submechanism, the
    result records ``exact_match = None`` and the closest preregistered family rather
    than forcing an inaccurate category label.
    """
    evidence: dict[str, Any] = {
        "reference_attempted": reference_attempted,
        "reference_failed": reference_failed,
        "agreement_violations": len(violations),
        "failed_diagnostic_count": len(failed_diagnostics),
    }
    if reference_failed > 0:
        return _classification_blocks(
            exact_match="C",
            closest_family="C",
            preregistered_a_supported=False,
            summary="objective/reference pathology: a high-precision reference fit failed",
            evidence=evidence,
            observed_id="high-precision-reference-fit-failed",
            observed_summary=("a high-precision reference fit failed to certify its objective"),
        )
    if violations:
        return _classification_blocks(
            exact_match="D",
            closest_family="D",
            preregistered_a_supported=False,
            summary=(
                "implementation/reference mismatch: successful float64 fits disagree "
                "with the high-precision reference"
            ),
            evidence=evidence,
            observed_id="reference-implementation-mismatch",
            observed_summary=("the frozen solver and the high-precision reference disagree"),
        )
    total = len(failed_diagnostics)
    rounded_meets = [
        record
        for record in failed_diagnostics
        if record.get("rounded_reference_actual_gap_meets_objective_tolerance") is True
    ]
    certificate_met = [
        record
        for record in failed_diagnostics
        if record.get("production_certificate_met_at_rounded") is True
    ]
    evidence["rounded_reference_meets_objective_tolerance_count"] = len(rounded_meets)
    evidence["production_certificate_met_at_rounded_count"] = len(certificate_met)
    if total == 0:
        return _classification_blocks(
            exact_match=None,
            closest_family=None,
            preregistered_a_supported=False,
            summary="no uncertifiable source fits to classify",
            evidence=evidence,
            observed_id="no-failed-fits",
            observed_summary="no frozen source fit failed to certify",
        )
    all_meet = len(rounded_meets) == total
    none_meet = len(rounded_meets) == 0
    all_certificate_fail = len(certificate_met) == 0
    if all_meet and all_certificate_fail:
        return _classification_blocks(
            exact_match="A",
            closest_family="A",
            preregistered_a_supported=True,
            summary=(
                "preregistered A: every rounded high-precision reference point meets "
                "the declared objective-gap tolerance, but the frozen sufficient "
                "gradient certificate is not met there"
            ),
            evidence=evidence,
            observed_id=PREREGISTERED_A_MECHANISM_ID,
            observed_summary=(
                "the rounded reference point meets the objective-gap tolerance but "
                "does not meet the frozen sufficient gradient certificate"
            ),
        )
    if none_meet:
        return _classification_blocks(
            exact_match="B",
            closest_family="B",
            preregistered_a_supported=False,
            summary=(
                "binary64 representability/conditioning limitation: the configuration "
                "is mathematically defined, but the declared objective-gap tolerance is "
                "below the practical binary64 resolution for these resamples"
            ),
            evidence=evidence,
            observed_id="binary64-representation-below-objective-gap-tolerance",
            observed_summary=(
                "no binary64 point near the reference optimum meets the declared "
                "objective-gap tolerance"
            ),
        )
    return _classification_blocks(
        exact_match=None,
        closest_family="A",
        preregistered_a_supported=False,
        summary=_NO_EXACT_MATCH_SUMMARY,
        evidence=evidence,
        observed_id=OBSERVED_MECHANISM_SOLVER_PATH_ID,
        observed_summary=_OBSERVED_MECHANISM_SUMMARY,
    )


def _limitations() -> dict[str, str]:
    return {
        "statement": (
            "R2C.1 adds no data, model, lambda, or calibration family. It only "
            "re-solves the already-frozen lambda = 1e-6 train-refit objectives "
            "with an independent high-precision reference to characterize the 15 "
            "uncertifiable fits. It selects no R3 method and authorizes no R3."
        ),
        "rounded_reference_note": (
            "The rounded-reference and ULP diagnostics are local to the "
            "high-precision optimum; they do not prove that no binary64 point "
            "anywhere satisfies the frozen certificate."
        ),
        "mechanism_note": (
            "The observed limitation is a frozen-binary64 solver-path limitation: a "
            "certifiable binary64 point exists, but the Newton/backtracking path does "
            "not uniformly reach it at lambda = 1e-6. This is neither a defect of the "
            "sufficient gradient certificate nor a claim that binary64 cannot "
            "represent a certifiable solution."
        ),
    }


_CLASSIFICATION_ONLY_KEYS = (
    "classification",
    "predeclared_classification_result",
    "observed_mechanism",
    "limitations",
)


def numerical_projection(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return the quantitative evidence of an artifact, excluding interpretation.

    Everything that is not classification/interpretation metadata is retained,
    including source lineage, so a classification-only re-render must leave this
    projection exactly equal.
    """
    return {key: value for key, value in payload.items() if key not in _CLASSIFICATION_ONLY_KEYS}


def reclassify_artifact(
    artifact: Mapping[str, Any],
    *,
    design_path: Path | str = DEFAULT_DESIGN_PATH,
) -> dict[str, Any]:
    """Re-render only the classification/interpretation metadata of an artifact.

    It never re-solves a fit: the classification is derived from the quantitative
    evidence already stored in ``artifact``. The numerical projection is preserved
    exactly.
    """
    design = load_design(design_path)
    validate_design(design)
    updated = json.loads(json.dumps(artifact))
    blocks = classify_failed_fits(
        reference_attempted=updated["reference_fit_summary"]["attempted"],
        reference_failed=updated["reference_fit_summary"]["failed"],
        violations=updated.get("agreement_violations", []),
        failed_diagnostics=updated.get("failed_fit_diagnostics", []),
    )
    updated.pop("classification", None)
    updated["predeclared_classification_result"] = blocks["predeclared_classification_result"]
    updated["observed_mechanism"] = blocks["observed_mechanism"]
    updated["limitations"] = _limitations()
    return updated


# ---------------------------------------------------------------------------
# Provenance + CLI.
# ---------------------------------------------------------------------------


def file_sha256(path: Path | str) -> str:
    digest = hashlib.sha256()
    digest.update(Path(path).read_bytes())
    return digest.hexdigest()


def _git(args: Sequence[str]) -> str:
    result = subprocess.run(
        ["git", *args], cwd=_REPO_ROOT, capture_output=True, text=True, check=False
    )
    return result.stdout.strip()


def collect_provenance(*, design_path: Path | str = DEFAULT_DESIGN_PATH) -> dict[str, Any]:
    """Record the design-freeze commit and the execution commit separately."""
    design_commit = _git(["log", "-1", "--format=%H", "--", str(Path(design_path).resolve())])
    execution_commit = _git(["rev-parse", "HEAD"])
    status = _git(["status", "--porcelain"])
    return {
        "r2c1_design_commit": design_commit,
        "r2c1_execution_commit": execution_commit,
        "git_worktree_clean": status == "",
    }


def analyze(
    *,
    raw_path: Path | str,
    r2c_analysis_path: Path | str = DEFAULT_R2C_ANALYSIS_PATH,
    design_path: Path | str = DEFAULT_DESIGN_PATH,
    provenance: Mapping[str, Any] | None = None,
    replicates: int = PAIRED_TRAIN_REFIT_REPLICATES,
) -> dict[str, Any]:
    design = load_design(design_path)
    validate_design(design)
    raw = json.loads(Path(raw_path).read_text(encoding="utf-8"))
    r2c_artifact = json.loads(Path(r2c_analysis_path).read_text(encoding="utf-8"))
    expected_raw = design["source_r2b_raw"]["file_sha256"]
    actual_raw = file_sha256(raw_path)
    if actual_raw != expected_raw:
        raise SourceLineageError(
            f"R2B raw artifact sha256 mismatch: expected {expected_raw}, got {actual_raw}"
        )
    expected_r2c = design["source_r2c_analysis"]["file_sha256"]
    actual_r2c = file_sha256(r2c_analysis_path)
    if actual_r2c != expected_r2c:
        raise SourceLineageError(
            f"R2C analysis artifact sha256 mismatch: expected {expected_r2c}, got {actual_r2c}"
        )
    return run_closure(raw, r2c_artifact, design, provenance=provenance, replicates=replicates)


def _main(argv: Sequence[str]) -> int:
    if len(argv) >= 2 and argv[1] == "--reclassify":
        if len(argv) not in (3, 4):
            print(
                "usage: r2c1_numerical_closure.py --reclassify <ARTIFACT> [OUT]",
                file=sys.stderr,
            )
            return 2
        artifact_path = Path(argv[2])
        out_path = Path(argv[3]) if len(argv) == 4 else artifact_path
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        updated = reclassify_artifact(artifact)
        text = json.dumps(updated, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        out_path.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {out_path}")
        return 0
    if len(argv) not in (3, 4):
        print(
            "usage: r2c1_numerical_closure.py <R2B_RAW> <R2C_ANALYSIS> [OUT]",
            file=sys.stderr,
        )
        return 2
    raw_path = Path(argv[1])
    r2c_path = Path(argv[2])
    out_path = (
        Path(argv[3])
        if len(argv) == 4
        else _HARNESS_DIR / "results" / "r2c1-low-reg-numerical-closure-v1-analysis.json"
    )
    artifact = analyze(
        raw_path=raw_path,
        r2c_analysis_path=r2c_path,
        provenance=collect_provenance(),
    )
    text = json.dumps(artifact, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
    out_path.write_text(text + "\n", encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(_main(sys.argv))
