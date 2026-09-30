"""R4 target-label-free predictor infrastructure (research layer).

This module is the research-layer implementation of the frozen R4 predictor
semantics recorded in ``R4_PREDICTOR_FREEZE.md`` /
``R4_PREDICTOR_FREEZE.json``.

It is *statistical infrastructure*, not a study runner and not a result
loader. It never downloads datasets, never loads models, never opens a GPU,
never searches for score or result files, and never reads an official R4
artifact. Every entry point takes explicit in-memory records supplied by a
future authorized caller.

Hard rules encoded here:

* the predictor feature path is **target-label-free**: the X functions take only
  ``source_train_scores`` and ``target_test_scores`` and accept no label,
  calibrator, ground truth, native risk, cross risk or delta argument;
* raw predictor scores are validated to be finite and inside ``[0, 1]``; exact
  ``0`` and ``1`` are legal; invalid inputs raise ``PREDICTOR_INPUT_INVALID``
  and are never repaired;
* every draw reuses the frozen ``r4_inference`` deterministic TEST / TRAIN
  samplers, so predictor X and transport outcome Y share one TEST draw per
  population and replicate;
* the source TRAIN quantile thresholds are fixed at the full primary TRAIN and
  are never re-bootstrapped inside a TEST replicate;
* failures fail closed: an undefined replicate or an incomplete unit produces
  ``INCOMPLETE`` and never a successful-subset interval.

This module performs no formal R4 measurement, no calibration fitting, no
formal bootstrap execution on real study data and no Brier / LogLoss /
transport analysis. It is pre-outcome infrastructure engineering.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from itertools import pairwise
from typing import Any

from r4_inference import (
    HELLASWAG_POPULATION_ID,
    LOGISTIC_CORE_PROCEDURES,
    MEDMCQA_POPULATION_ID,
    MMLU_POPULATION_ID,
    STATUS_COMPLETE,
    STATUS_INCOMPLETE,
    BootstrapContractViolation,
    Interval,
    PopulationMetadata,
    R4InferenceRow,
    TestDraw,
    TrainRefitDraw,
    build_train_refit_draw,
    canonical_state_json,
    measurement_score,
    percentile_interval,
    percentile_rank,
    source_measurement,
    stable_rows,
    state_fingerprint,
    target_measurement,
)

from probvenance.fingerprint import fingerprint

# ---------------------------------------------------------------------------
# Frozen identities
# ---------------------------------------------------------------------------

PREDICTOR_FREEZE_ARTIFACT_TYPE = "r4-target-label-free-predictor-freeze"
PREDICTOR_FREEZE_ARTIFACT_VERSION = 1
PREDICTOR_FREEZE_STATUS = "FROZEN"
FINGERPRINT_VERSION = 1

PREDICTOR_FREEZE_FINGERPRINT = (
    "c856fcc161910497a3431593639606682905adcb50fc443455468dfc295d73a9"
)
PREDICTOR_CANDIDATE_FINGERPRINT = (
    "d3625912fadb5e6c68e20495256aa1f90b53686f13c9d25d1eb9ceb212dfbb06"
)
PREDICTOR_FREEZE_COMMIT = "bc2562104a7e84b52aaf76fec613b874c431760d"
PREDICTOR_CANDIDATE_COMMIT = "ed2ba62ffdae7b1c9890682e3550b54021df6c99"
R4_INFERENCE_FREEZE_FINGERPRINT = (
    "dcbb7ac9e931145fdee86ab984de1249c1b86ca36ee735b70dafc8cabc06c141"
)

PREDICTOR_IMPLEMENTATION_ID = "r4-predictor-range-exceedance-w1-spearman-v1"
PREDICTOR_IMPLEMENTATION_VERSION = 1

PRIMARY_PREDICTOR_ID = "r4-target-range-exceedance-warning"
PRIMARY_PREDICTOR_VERSION = 1
SECONDARY_PREDICTOR_ID = "r4-source-target-wasserstein1-warning"
SECONDARY_PREDICTOR_VERSION = 1

PRIMARY_OUTCOME_ID = "r4-core4-mean-transport-penalty"
PRIMARY_OUTCOME_VERSION = 1
SECONDARY_OUTCOME_ID = "r4-core4-mean-deployment-delta"
SECONDARY_OUTCOME_VERSION = 1

VALIDATION_PROTOCOL_ID = "r4-heldout-population-predictor-validation"
VALIDATION_PROTOCOL_VERSION = 1

SPEARMAN_STATISTIC_ID = "spearman-rank-correlation"
SPEARMAN_STATISTIC_VERSION = 1

# ---------------------------------------------------------------------------
# Frozen numeric contract
# ---------------------------------------------------------------------------

CORE4_PROCEDURES: tuple[str, ...] = LOGISTIC_CORE_PROCEDURES
CORE4_PROCEDURE_COUNT = 4

SOURCE_LOWER_LEVEL = Fraction(1, 40)
SOURCE_UPPER_LEVEL = Fraction(39, 40)
SOURCE_LOWER_RANK_AT_N456 = 12
SOURCE_UPPER_RANK_AT_N456 = 445
SOURCE_QUANTILE_RULE_ID = "nearest-rank-percentile"
SOURCE_QUANTILE_RULE_VERSION = 1

PREDICTOR_LOWER_TAIL = Fraction(1, 40)
PREDICTOR_MEDIAN_LEVEL = Fraction(1, 2)
PREDICTOR_UPPER_TAIL = Fraction(39, 40)
PREDICTOR_INTERVAL_N = 20000
PREDICTOR_INTERVAL_LOWER_RANK = 500
PREDICTOR_INTERVAL_MEDIAN_RANK = 10000
PREDICTOR_INTERVAL_UPPER_RANK = 19500
PREDICTOR_BOOTSTRAP_REPLICATES = 20000

TRAIN_STABILITY_REPLICATES = 2000

VALIDATION_MODEL_COUNT = 4
VALIDATION_POPULATION_COUNT = 2
VALIDATION_DIRECTION_COUNT = 2
PRIMARY_VALIDATION_UNIT_COUNT = 16
DEVELOPMENT_UNIT_COUNT = 8
LEGACY_EXTENSION_UNIT_COUNT = 8

# ---------------------------------------------------------------------------
# States and roles
# ---------------------------------------------------------------------------

PREDICTOR_INPUT_INVALID = "PREDICTOR_INPUT_INVALID"
SPEARMAN_UNDEFINED_CONSTANT_INPUT = "SPEARMAN_UNDEFINED_CONSTANT_INPUT"
PRIMARY_VALIDATION_INCOMPLETE = "PRIMARY_VALIDATION_INCOMPLETE"
CORE4_UNIT_INCOMPLETE = "CORE4_UNIT_INCOMPLETE"

PRIMARY_WARNING_SIGNAL_SUPPORTED = "PRIMARY_WARNING_SIGNAL_SUPPORTED"
PRIMARY_WARNING_SIGNAL_NOT_ESTABLISHED = "PRIMARY_WARNING_SIGNAL_NOT_ESTABLISHED"
PRIMARY_WARNING_SIGNAL_INCOMPLETE = "PRIMARY_WARNING_SIGNAL_INCOMPLETE"

ROLE_DEVELOPMENT = "DEVELOPMENT_CONTINUITY"
ROLE_PRIMARY_VALIDATION = "PRIMARY_VALIDATION"
ROLE_LEGACY_EXTENSION = "LEGACY_LINEAGE_EXTENSION"

N912_ROBUSTNESS_ROLE = "SECONDARY_ROBUSTNESS"
N912_CANNOT_RESCUE_PRIMARY = True

DIRECTIONS: tuple[str, ...] = ("CAT->OVR", "OVR->CAT")

VALIDATION_POPULATIONS: tuple[str, ...] = (
    HELLASWAG_POPULATION_ID,
    MEDMCQA_POPULATION_ID,
)
DEVELOPMENT_POPULATIONS: tuple[str, ...] = (MMLU_POPULATION_ID,)

CURRENT_GENERATION_MODELS: tuple[tuple[str, str], ...] = (
    ("allenai/Olmo-3-7B-Instruct", "6e5971d9eba42665f5bd5a0fcf047f299ce1dccc"),
    ("tiiuae/Falcon-H1-7B-Instruct", "41e72f27effbab80cd45b6e884688452253a3686"),
    ("ibm-granite/granite-4.0-h-tiny", "791e0d3d28c86e106c9b6e0b4cecdee0375b6124"),
    ("Qwen/Qwen3.5-9B", "c202236235762e1c871ad0ccb60c8ee5ba337b9a"),
)

LEGACY_MODELS: tuple[tuple[str, str], ...] = (
    ("openbmb/MiniCPM5-2B", "12a3808a956f869c767195e9266b59c4d21d92e2"),
    ("Qwen/Qwen3.5-2B", "15852e8c16360a2fea060d615a32b45270f8a8fc"),
)

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class PredictorError(Exception):
    """Base class for predictor contract violations."""


class PredictorInputInvalid(PredictorError, ValueError):
    """A predictor score is not a finite probability in ``[0, 1]``."""

    state = PREDICTOR_INPUT_INVALID


class PredictorContractViolation(PredictorError, ValueError):
    """A predictor structural contract was violated."""


class Core4Incomplete(PredictorError, ValueError):
    """A CORE4 outcome aggregate is missing at least one required procedure."""

    state = CORE4_UNIT_INCOMPLETE

    def __init__(self, missing: Sequence[str]) -> None:
        self.missing = tuple(missing)
        super().__init__(
            f"{CORE4_UNIT_INCOMPLETE}: missing CORE4 procedures {sorted(self.missing)}"
        )


class PrimaryValidationIncomplete(PredictorError, ValueError):
    """The frozen 16-unit primary validation panel is not complete."""

    state = PRIMARY_VALIDATION_INCOMPLETE


class PredictorRoleViolation(PredictorError, ValueError):
    """A unit was assigned to an analysis role it does not own."""


class SpearmanUndefined(PredictorError, ValueError):
    """The rank correlation is undefined because an input is constant."""

    state = SPEARMAN_UNDEFINED_CONSTANT_INPUT


# ---------------------------------------------------------------------------
# Score validation (no clipping)
# ---------------------------------------------------------------------------


def validate_predictor_score(value: Any, *, context: str = "score") -> float:
    """Validate one raw predictor score.

    Exact ``0`` and ``1`` are legal. Non-finite values, values below ``0`` and
    values above ``1`` raise ``PREDICTOR_INPUT_INVALID``. Nothing is repaired.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PredictorInputInvalid(f"{PREDICTOR_INPUT_INVALID}: {context} must be real")
    score = float(value)
    if not math.isfinite(score):
        raise PredictorInputInvalid(f"{PREDICTOR_INPUT_INVALID}: {context} must be finite")
    if score < 0.0 or score > 1.0:
        raise PredictorInputInvalid(
            f"{PREDICTOR_INPUT_INVALID}: {context} must lie in [0, 1], got {score!r}"
        )
    return score


def validate_predictor_scores(
    scores: Sequence[float], *, context: str = "scores"
) -> tuple[float, ...]:
    """Validate a raw score sequence; the input order is preserved."""
    if not scores:
        raise PredictorInputInvalid(f"{PREDICTOR_INPUT_INVALID}: {context} is empty")
    return tuple(
        validate_predictor_score(value, context=f"{context}[{index}]")
        for index, value in enumerate(scores)
    )


# ---------------------------------------------------------------------------
# Primary predictor: X_range
# ---------------------------------------------------------------------------


def source_quantile_levels() -> dict[str, Any]:
    """The frozen SOURCE TRAIN nearest-rank quantile contract."""
    return {
        "rule_id": SOURCE_QUANTILE_RULE_ID,
        "rule_version": SOURCE_QUANTILE_RULE_VERSION,
        "lower_level": str(SOURCE_LOWER_LEVEL),
        "upper_level": str(SOURCE_UPPER_LEVEL),
        "lower_level_decimal": float(SOURCE_LOWER_LEVEL),
        "upper_level_decimal": float(SOURCE_UPPER_LEVEL),
        "lower_rank_at_n456": SOURCE_LOWER_RANK_AT_N456,
        "upper_rank_at_n456": SOURCE_UPPER_RANK_AT_N456,
        "rank_convention": "1-indexed nearest rank; rank = ceil(fraction * n)",
    }


def source_thresholds(source_train_scores: Sequence[float]) -> tuple[float, float]:
    """Nearest-rank 2.5th / 97.5th percentiles of the SOURCE TRAIN scores."""
    scores = validate_predictor_scores(source_train_scores, context="source_train_scores")
    ordered = sorted(scores)
    lower = ordered[percentile_rank(SOURCE_LOWER_LEVEL, len(ordered)) - 1]
    upper = ordered[percentile_rank(SOURCE_UPPER_LEVEL, len(ordered)) - 1]
    return float(lower), float(upper)


@dataclass(frozen=True)
class RangeExceedanceResult:
    """The frozen primary predictor value plus its deterministic provenance."""

    source_count: int
    target_count: int
    q_low: float
    q_high: float
    outside_count: int
    fraction_outside: float
    predictor_id: str = PRIMARY_PREDICTOR_ID
    predictor_version: int = PRIMARY_PREDICTOR_VERSION

    def payload(self) -> dict[str, Any]:
        return {
            "predictor_id": self.predictor_id,
            "predictor_version": self.predictor_version,
            "source_count": self.source_count,
            "target_count": self.target_count,
            "q_low": self.q_low,
            "q_high": self.q_high,
            "outside_count": self.outside_count,
            "fraction_outside": self.fraction_outside,
        }


def range_exceedance_warning(
    source_train_scores: Sequence[float],
    target_test_scores: Sequence[float],
) -> RangeExceedanceResult:
    """The frozen primary predictor ``X_range``.

    ``X_range`` is the fraction of TARGET TEST raw scores that fall strictly
    outside the SOURCE TRAIN nearest-rank 2.5th / 97.5th percentile band.
    Equality with either threshold counts as INSIDE.

    The signature takes only raw scores; it accepts no label, calibrator,
    ground truth, native risk, cross risk or delta value.
    """
    source = validate_predictor_scores(source_train_scores, context="source_train_scores")
    target = validate_predictor_scores(target_test_scores, context="target_test_scores")
    q_low, q_high = source_thresholds(source)
    outside = sum(1 for score in target if score < q_low or score > q_high)
    return RangeExceedanceResult(
        source_count=len(source),
        target_count=len(target),
        q_low=q_low,
        q_high=q_high,
        outside_count=outside,
        fraction_outside=outside / len(target),
    )


# ---------------------------------------------------------------------------
# Secondary predictor: exact empirical Wasserstein-1
# ---------------------------------------------------------------------------


def exact_empirical_wasserstein1(
    source_scores: Sequence[float], target_scores: Sequence[float]
) -> float:
    """Exact one-dimensional empirical Wasserstein-1 distance.

    Computed as ``integral |F_mu(t) - F_nu(t)| dt`` over the merged sorted
    support. Both empirical measures carry equal row mass. No histogram,
    binning, quantile grid or subsampling approximation is used.
    """
    left = sorted(validate_predictor_scores(source_scores, context="source_scores"))
    right = sorted(validate_predictor_scores(target_scores, context="target_scores"))
    support = sorted(set(left) | set(right))
    if len(support) < 2:
        return 0.0
    total = 0.0
    for lower, upper in pairwise(support):
        left_cdf = _count_at_most(left, lower) / len(left)
        right_cdf = _count_at_most(right, lower) / len(right)
        total += abs(left_cdf - right_cdf) * (upper - lower)
    return total


def _count_at_most(ordered: Sequence[float], value: float) -> int:
    """Count of entries ``<= value`` in an ascending sequence (binary search)."""
    low, high = 0, len(ordered)
    while low < high:
        middle = (low + high) // 2
        if ordered[middle] <= value:
            low = middle + 1
        else:
            high = middle
    return low


@dataclass(frozen=True)
class Wasserstein1Result:
    """The frozen secondary predictor value plus its deterministic provenance."""

    source_count: int
    target_count: int
    wasserstein1: float
    predictor_id: str = SECONDARY_PREDICTOR_ID
    predictor_version: int = SECONDARY_PREDICTOR_VERSION

    def payload(self) -> dict[str, Any]:
        return {
            "predictor_id": self.predictor_id,
            "predictor_version": self.predictor_version,
            "source_count": self.source_count,
            "target_count": self.target_count,
            "wasserstein1": self.wasserstein1,
        }


def wasserstein1_warning(
    source_train_scores: Sequence[float],
    target_test_scores: Sequence[float],
) -> Wasserstein1Result:
    """The frozen secondary predictor ``X_W1``.

    The signature takes only raw scores; it accepts no label, calibrator,
    ground truth, native risk, cross risk or delta value.
    """
    source = validate_predictor_scores(source_train_scores, context="source_train_scores")
    target = validate_predictor_scores(target_test_scores, context="target_test_scores")
    return Wasserstein1Result(
        source_count=len(source),
        target_count=len(target),
        wasserstein1=exact_empirical_wasserstein1(source, target),
    )


# ---------------------------------------------------------------------------
# CORE4 outcome aggregation
# ---------------------------------------------------------------------------


def core4_completeness(values: Mapping[str, float]) -> dict[str, Any]:
    """Report which frozen CORE4 procedures are present in a unit outcome map."""
    present = tuple(
        procedure for procedure in CORE4_PROCEDURES if procedure in values
    )
    missing = tuple(
        procedure for procedure in CORE4_PROCEDURES if procedure not in values
    )
    ignored = tuple(sorted(key for key in values if key not in CORE4_PROCEDURES))
    return {
        "status": STATUS_COMPLETE if not missing else STATUS_INCOMPLETE,
        "present": list(present),
        "missing": list(missing),
        "ignored_extra_procedures": list(ignored),
    }


def _core4_mean(values: Mapping[str, float], *, label: str) -> float:
    missing = [procedure for procedure in CORE4_PROCEDURES if procedure not in values]
    if missing:
        raise Core4Incomplete(missing)
    total = math.fsum(
        validate_predictor_float(values[procedure], context=f"{label}[{procedure}]")
        for procedure in CORE4_PROCEDURES
    )
    return total / CORE4_PROCEDURE_COUNT


def validate_predictor_float(value: Any, *, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PredictorContractViolation(f"{context} must be a real number")
    number = float(value)
    if not math.isfinite(number):
        raise PredictorContractViolation(f"{context} must be finite")
    return number


def core4_mean_transport_penalty(values: Mapping[str, float]) -> float:
    """``Y_transport_core``: the mean CORE4 ``Delta_transport``.

    Every CORE4 procedure must be present. Extra standalone procedures are
    ignored and can never change the aggregate. A missing procedure raises
    ``CORE4_UNIT_INCOMPLETE``; the remaining three are never averaged.
    """
    return _core4_mean(values, label="Delta_transport")


def core4_mean_deployment_delta(values: Mapping[str, float]) -> float:
    """``Y_deploy_core``: the mean CORE4 ``Delta_deploy`` (secondary)."""
    return _core4_mean(values, label="Delta_deploy")


# ---------------------------------------------------------------------------
# Rank correlation
# ---------------------------------------------------------------------------


def average_ranks(values: Sequence[float]) -> tuple[float, ...]:
    """Ascending average ranks (1-indexed); tied values share their mean rank."""
    indexed = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    position = 0
    while position < len(indexed):
        end = position
        while (
            end + 1 < len(indexed)
            and values[indexed[end + 1]] == values[indexed[position]]
        ):
            end += 1
        average = (position + end) / 2.0 + 1.0
        for index in range(position, end + 1):
            ranks[indexed[index]] = average
        position = end + 1
    return tuple(ranks)


def spearman_fixed_units(
    left: Sequence[float], right: Sequence[float]
) -> float:
    """Spearman rank correlation: the Pearson correlation of average ranks.

    A constant input raises ``SPEARMAN_UNDEFINED_CONSTANT_INPUT``; ``0`` and a
    silent ``NaN`` are never returned.
    """
    if len(left) != len(right):
        raise PredictorContractViolation("rank vectors must have equal length")
    if len(left) < 2:
        raise PredictorContractViolation("rank correlation needs at least two units")
    left_ranks = average_ranks([float(value) for value in left])
    right_ranks = average_ranks([float(value) for value in right])
    return _pearson(left_ranks, right_ranks)


def _pearson(left: Sequence[float], right: Sequence[float]) -> float:
    n = len(left)
    left_mean = math.fsum(left) / n
    right_mean = math.fsum(right) / n
    covariance = math.fsum(
        (left[index] - left_mean) * (right[index] - right_mean)
        for index in range(n)
    )
    left_variance = math.fsum((value - left_mean) ** 2 for value in left)
    right_variance = math.fsum((value - right_mean) ** 2 for value in right)
    if left_variance == 0.0 or right_variance == 0.0:
        raise SpearmanUndefined(
            f"{SPEARMAN_UNDEFINED_CONSTANT_INPUT}: a rank vector is constant"
        )
    return covariance / math.sqrt(left_variance * right_variance)


# ---------------------------------------------------------------------------
# Unit registries
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PredictorUnit:
    """One ``model x population x direction`` predictor observation."""

    model_id: str
    model_revision: str
    population_id: str
    direction_id: str
    analysis_role: str

    @property
    def unit_id(self) -> str:
        return predictor_unit_id(
            self.model_id, self.population_id, self.direction_id
        )

    def payload(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "model_id": self.model_id,
            "model_revision": self.model_revision,
            "population_id": self.population_id,
            "direction_id": self.direction_id,
            "analysis_role": self.analysis_role,
        }


def predictor_unit_id(model_id: str, population_id: str, direction_id: str) -> str:
    """Deterministic, answer-independent unit identity."""
    return fingerprint(
        {
            "protocol_id": VALIDATION_PROTOCOL_ID,
            "protocol_version": VALIDATION_PROTOCOL_VERSION,
            "model_id": model_id,
            "population_id": population_id,
            "direction_id": direction_id,
        }
    )


def _units(
    models: Sequence[tuple[str, str]],
    populations: Sequence[str],
    role: str,
) -> tuple[PredictorUnit, ...]:
    return tuple(
        PredictorUnit(
            model_id=model_id,
            model_revision=revision,
            population_id=population_id,
            direction_id=direction_id,
            analysis_role=role,
        )
        for model_id, revision in models
        for population_id in populations
        for direction_id in DIRECTIONS
    )


def development_units() -> tuple[PredictorUnit, ...]:
    """The 8 R4 current-generation MMLU development / continuity units."""
    return _units(CURRENT_GENERATION_MODELS, DEVELOPMENT_POPULATIONS, ROLE_DEVELOPMENT)


def primary_validation_units() -> tuple[PredictorUnit, ...]:
    """The 16 frozen primary held-out validation units."""
    return _units(
        CURRENT_GENERATION_MODELS, VALIDATION_POPULATIONS, ROLE_PRIMARY_VALIDATION
    )


def legacy_extension_units() -> tuple[PredictorUnit, ...]:
    """The 8 frozen secondary legacy lineage-continuity units."""
    return _units(LEGACY_MODELS, VALIDATION_POPULATIONS, ROLE_LEGACY_EXTENSION)


# ---------------------------------------------------------------------------
# Role firewall
# ---------------------------------------------------------------------------


def require_primary_validation_unit(unit: PredictorUnit) -> None:
    """Reject any unit that is not one of the frozen 16 validation units."""
    if unit.analysis_role != ROLE_PRIMARY_VALIDATION:
        raise PredictorRoleViolation(
            f"unit {unit.unit_id} has role {unit.analysis_role!r}, "
            "not primary validation"
        )
    if unit.population_id not in VALIDATION_POPULATIONS:
        raise PredictorRoleViolation(
            f"population {unit.population_id!r} is not a held-out validation population"
        )
    if unit.model_id not in {model for model, _ in CURRENT_GENERATION_MODELS}:
        raise PredictorRoleViolation(
            f"model {unit.model_id!r} is not a current-generation validation model"
        )
    if unit not in primary_validation_units():
        raise PredictorRoleViolation(f"unit {unit.unit_id} is not a frozen validation unit")


def require_development_unit(unit: PredictorUnit) -> None:
    if unit.analysis_role != ROLE_DEVELOPMENT:
        raise PredictorRoleViolation(
            f"unit {unit.unit_id} has role {unit.analysis_role!r}, not development"
        )
    if unit.population_id not in DEVELOPMENT_POPULATIONS:
        raise PredictorRoleViolation(
            f"population {unit.population_id!r} is not a development population"
        )


def require_legacy_extension_unit(unit: PredictorUnit) -> None:
    if unit.analysis_role != ROLE_LEGACY_EXTENSION:
        raise PredictorRoleViolation(
            f"unit {unit.unit_id} has role {unit.analysis_role!r}, not legacy extension"
        )
    if unit.model_id not in {model for model, _ in LEGACY_MODELS}:
        raise PredictorRoleViolation(
            f"model {unit.model_id!r} is not a legacy-lineage model"
        )


# ---------------------------------------------------------------------------
# Primary validation table
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PredictorValidationRow:
    """One unit's predictor X values and CORE4 outcome summaries."""

    unit: PredictorUnit
    x_range: float | None
    x_wasserstein1: float | None
    y_transport_core: float | None
    y_deploy_core: float | None

    def payload(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit.unit_id,
            "model_id": self.unit.model_id,
            "population_id": self.unit.population_id,
            "direction_id": self.unit.direction_id,
            "x_range": self.x_range,
            "x_wasserstein1": self.x_wasserstein1,
            "y_transport_core": self.y_transport_core,
            "y_deploy_core": self.y_deploy_core,
        }


def validate_primary_validation_table(
    rows: Sequence[PredictorValidationRow],
) -> dict[str, Any]:
    """Validate the frozen 16-unit primary held-out validation table.

    Duplicate, missing and extra units are rejected; a unit with incomplete
    predictor X or incomplete outcome Y makes the panel
    ``PRIMARY_VALIDATION_INCOMPLETE``. Complete-case correlation is never used.
    """
    expected = {unit.unit_id: unit for unit in primary_validation_units()}
    seen: dict[str, int] = {}
    for row in rows:
        require_primary_validation_unit(row.unit)
        seen[row.unit.unit_id] = seen.get(row.unit.unit_id, 0) + 1
    duplicates = sorted(unit_id for unit_id, count in seen.items() if count > 1)
    missing = sorted(set(expected) - set(seen))
    extra = sorted(set(seen) - set(expected))
    if duplicates or missing or extra:
        raise PrimaryValidationIncomplete(
            f"{PRIMARY_VALIDATION_INCOMPLETE}: duplicates={duplicates} "
            f"missing={missing} extra={extra}"
        )
    incomplete = sorted(
        row.unit.unit_id
        for row in rows
        if row.x_range is None
        or row.x_wasserstein1 is None
        or row.y_transport_core is None
        or row.y_deploy_core is None
    )
    if incomplete:
        raise PrimaryValidationIncomplete(
            f"{PRIMARY_VALIDATION_INCOMPLETE}: incomplete units {incomplete}"
        )
    return {
        "status": STATUS_COMPLETE,
        "unit_count": len(rows),
        "population_counts": {
            population: sum(
                1 for row in rows if row.unit.population_id == population
            )
            for population in VALIDATION_POPULATIONS
        },
        "direction_counts": {
            direction: sum(
                1 for row in rows if row.unit.direction_id == direction
            )
            for direction in DIRECTIONS
        },
    }


def primary_statistic(rows: Sequence[PredictorValidationRow]) -> float:
    """``rho_primary`` over exactly the 16 frozen held-out units."""
    validate_primary_validation_table(rows)
    ordered = _ordered_primary_rows(rows)
    return spearman_fixed_units(
        [row.x_range for row in ordered],
        [row.y_transport_core for row in ordered],
    )


def _ordered_primary_rows(
    rows: Sequence[PredictorValidationRow],
) -> tuple[PredictorValidationRow, ...]:
    return tuple(sorted(rows, key=lambda row: row.unit.unit_id))


def secondary_statistics(rows: Sequence[PredictorValidationRow]) -> dict[str, Any]:
    """The two frozen secondary rank correlations.

    They are reported separately and can never modify the primary support
    state.
    """
    validate_primary_validation_table(rows)
    ordered = _ordered_primary_rows(rows)
    x_w1 = [row.x_wasserstein1 for row in ordered]
    x_range = [row.x_range for row in ordered]
    y_transport = [row.y_transport_core for row in ordered]
    y_deploy = [row.y_deploy_core for row in ordered]
    return {
        "rho_W1_transport": _optional_spearman(x_w1, y_transport),
        "rho_range_deploy": _optional_spearman(x_range, y_deploy),
        "role": "SECONDARY",
        "can_rescue_primary": False,
    }


def _optional_spearman(
    left: Sequence[float], right: Sequence[float]
) -> dict[str, Any]:
    try:
        value = spearman_fixed_units(left, right)
    except SpearmanUndefined as exc:
        return {"status": exc.state, "value": None}
    return {"status": STATUS_COMPLETE, "value": value}


# ---------------------------------------------------------------------------
# Primary support rule
# ---------------------------------------------------------------------------


def primary_support_state(point_estimate: float | None, interval: Interval) -> str:
    """The frozen primary support state; secondary results are never consulted."""
    if interval.status != STATUS_COMPLETE or point_estimate is None:
        return PRIMARY_WARNING_SIGNAL_INCOMPLETE
    if interval.lower is None or interval.upper is None:
        return PRIMARY_WARNING_SIGNAL_INCOMPLETE
    if point_estimate > 0.0 and interval.lower > 0.0:
        return PRIMARY_WARNING_SIGNAL_SUPPORTED
    return PRIMARY_WARNING_SIGNAL_NOT_ESTABLISHED


# ---------------------------------------------------------------------------
# Shared-draw predictor TEST bootstrap
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PredictorUnitMeasurement:
    """One unit's frozen SOURCE TRAIN scores, TARGET TEST rows and Y provider.

    ``source_train_scores`` is the full primary TRAIN score vector; it is fixed
    for every replicate. ``target_test_rows`` are the frozen TEST rows whose
    target-measurement scores are resampled. ``y_provider`` returns the unit's
    ``(Y_transport_core, Y_deploy_core)`` computed from the *same* draw.
    """

    unit: PredictorUnit
    source_train_scores: tuple[float, ...]
    target_test_rows: tuple[R4InferenceRow, ...]
    y_provider: Callable[[TestDraw], tuple[float | None, float | None]]


@dataclass(frozen=True)
class PredictorBootstrapResult:
    """The frozen predictor TEST-bootstrap state."""

    planned_replicates: int
    successful_replicates: int
    undefined_replicates: int
    undefined_indices: tuple[int, ...]
    incomplete_replicates: int
    incomplete_indices: tuple[int, ...]
    status: str
    samples: tuple[float, ...]
    point_estimate: float | None
    tail_rule: str

    def interval(self) -> Interval:
        if self.status != STATUS_COMPLETE:
            return Interval(
                n=len(self.samples),
                point_estimate=self.point_estimate,
                bootstrap_median=None,
                lower=None,
                upper=None,
                tail_rule=self.tail_rule,
                excludes_zero=None,
                status=STATUS_INCOMPLETE,
            )
        return percentile_interval(
            self.samples,
            lower_tail=PREDICTOR_LOWER_TAIL,
            upper_tail=PREDICTOR_UPPER_TAIL,
            median_level=PREDICTOR_MEDIAN_LEVEL,
            point_estimate=self.point_estimate,
        )

    def payload(self) -> dict[str, Any]:
        return {
            "planned_replicates": self.planned_replicates,
            "successful_replicates": self.successful_replicates,
            "undefined_replicates": self.undefined_replicates,
            "undefined_indices": list(self.undefined_indices),
            "incomplete_replicates": self.incomplete_replicates,
            "incomplete_indices": list(self.incomplete_indices),
            "status": self.status,
            "point_estimate": self.point_estimate,
            "tail_rule": self.tail_rule,
            "interval": self.interval().payload(),
        }


def _shared_draw_lookup(
    draws: Mapping[tuple[str, int], TestDraw],
    population_id: str,
    replicate_index: int,
) -> TestDraw:
    key = (population_id, replicate_index)
    try:
        return draws[key]
    except KeyError as exc:
        raise BootstrapContractViolation(
            f"missing shared TEST draw for {key}"
        ) from exc


def run_predictor_test_bootstrap(
    *,
    measurements: Sequence[PredictorUnitMeasurement],
    draws: Mapping[tuple[str, int], TestDraw],
    replicates: int = PREDICTOR_BOOTSTRAP_REPLICATES,
    point_estimate: float | None = None,
) -> PredictorBootstrapResult:
    """Run the frozen predictor TEST bootstrap over the fixed 16-unit panel.

    Each replicate uses one already frozen shared TEST draw per population. The
    same draw supplies both the predictor X and the transport outcome Y, and the
    SOURCE TRAIN thresholds stay fixed at the full primary TRAIN. Models,
    populations and directions are never resampled: only TEST rows / clusters
    are.
    """
    if replicates <= 0:
        raise BootstrapContractViolation("replicates must be positive")
    ordered_measurements = tuple(
        sorted(measurements, key=lambda measurement: measurement.unit.unit_id)
    )
    samples: list[float] = []
    undefined: list[int] = []
    incomplete: list[int] = []
    for replicate_index in range(replicates):
        x_values: list[float] = []
        y_values: list[float] = []
        replicate_incomplete = False
        for measurement in ordered_measurements:
            draw = _shared_draw_lookup(
                draws, measurement.unit.population_id, replicate_index
            )
            target_scores = _draw_target_scores(draw, measurement.unit.direction_id)
            result = range_exceedance_warning(
                measurement.source_train_scores, target_scores
            )
            y_transport, _ = measurement.y_provider(draw)
            if y_transport is None:
                replicate_incomplete = True
                break
            x_values.append(result.fraction_outside)
            y_values.append(float(y_transport))
        if replicate_incomplete:
            incomplete.append(replicate_index)
            continue
        try:
            samples.append(spearman_fixed_units(x_values, y_values))
        except SpearmanUndefined:
            undefined.append(replicate_index)
    status = STATUS_INCOMPLETE if undefined or incomplete else STATUS_COMPLETE
    return PredictorBootstrapResult(
        planned_replicates=replicates,
        successful_replicates=len(samples),
        undefined_replicates=len(undefined),
        undefined_indices=tuple(undefined),
        incomplete_replicates=len(incomplete),
        incomplete_indices=tuple(incomplete),
        status=status,
        samples=tuple(samples),
        point_estimate=point_estimate,
        tail_rule=f"{PREDICTOR_LOWER_TAIL}/{PREDICTOR_UPPER_TAIL}",
    )


def _draw_target_scores(draw: TestDraw, direction_id: str) -> tuple[float, ...]:
    """TARGET measurement scores of the draw's expanded row multiset."""
    measurement = target_measurement(direction_id)
    return tuple(measurement_score(row, measurement) for row in draw.occurrences)


# ---------------------------------------------------------------------------
# TRAIN stability
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PredictorTrainStabilityResult:
    """The frozen predictor TRAIN-stability state."""

    planned_replicates: int
    successful_replicates: int
    failed_replicates: int
    failed_indices: tuple[int, ...]
    status: str
    samples: tuple[float, ...]
    role: str = "SECONDARY_STABILITY_ONLY"

    def payload(self) -> dict[str, Any]:
        return {
            "planned_replicates": self.planned_replicates,
            "successful_replicates": self.successful_replicates,
            "failed_replicates": self.failed_replicates,
            "failed_indices": list(self.failed_indices),
            "status": self.status,
            "role": self.role,
        }


def run_predictor_train_stability(
    *,
    measurements: Sequence[PredictorUnitMeasurement],
    train_rows_by_population: Mapping[str, Sequence[R4InferenceRow]],
    metadata_by_population: Mapping[str, PopulationMetadata],
    replicates: int = TRAIN_STABILITY_REPLICATES,
    fixed_outcomes: Mapping[str, float] | None = None,
    budget_identity: str = "N456",
) -> PredictorTrainStabilityResult:
    """TRAIN-refit stability of the predictor X (and optionally of rho).

    Each replicate rebuilds the SOURCE TRAIN draw with the frozen
    ``r4_inference`` refit sampler, recomputes the SOURCE quantile thresholds,
    and recomputes ``X_range`` on the unchanged full TARGET TEST. When
    ``fixed_outcomes`` is supplied the replicate's rank correlation is formed
    against those frozen outcomes; a failed refit draw makes the whole block
    ``INCOMPLETE`` and no successful-subset interval is produced.
    """
    if replicates <= 0:
        raise BootstrapContractViolation("replicates must be positive")
    ordered = tuple(sorted(measurements, key=lambda item: item.unit.unit_id))
    samples: list[float] = []
    failed: list[int] = []
    for replicate_index in range(replicates):
        x_values: list[float] = []
        y_values: list[float] = []
        replicate_failed = False
        for measurement in ordered:
            population_id = measurement.unit.population_id
            rows = train_rows_by_population.get(population_id)
            metadata = metadata_by_population.get(population_id)
            if rows is None or metadata is None:
                replicate_failed = True
                break
            try:
                draw = build_train_refit_draw(
                    stable_rows(rows),
                    metadata,
                    replicate_index,
                    budget_identity=budget_identity,
                )
            except BootstrapContractViolation:
                replicate_failed = True
                break
            source_scores = _draw_source_scores(draw, measurement.unit.direction_id)
            target_scores = _unit_target_scores(measurement)
            result = range_exceedance_warning(source_scores, target_scores)
            x_values.append(result.fraction_outside)
            if fixed_outcomes is not None:
                outcome = fixed_outcomes.get(measurement.unit.unit_id)
                if outcome is None:
                    replicate_failed = True
                    break
                y_values.append(float(outcome))
        if replicate_failed:
            failed.append(replicate_index)
            continue
        if fixed_outcomes is None:
            continue
        try:
            samples.append(spearman_fixed_units(x_values, y_values))
        except SpearmanUndefined:
            failed.append(replicate_index)
    status = STATUS_INCOMPLETE if failed else STATUS_COMPLETE
    return PredictorTrainStabilityResult(
        planned_replicates=replicates,
        successful_replicates=len(samples),
        failed_replicates=len(failed),
        failed_indices=tuple(failed),
        status=status,
        samples=tuple(samples),
    )


def _draw_source_scores(draw: TrainRefitDraw, direction_id: str) -> tuple[float, ...]:
    measurement = source_measurement(direction_id)
    return tuple(measurement_score(row, measurement) for row in draw.occurrences)


def _unit_target_scores(measurement: PredictorUnitMeasurement) -> tuple[float, ...]:
    measurement_name = target_measurement(measurement.unit.direction_id)
    return tuple(
        measurement_score(row, measurement_name)
        for row in measurement.target_test_rows
    )


# ---------------------------------------------------------------------------
# N912 robustness
# ---------------------------------------------------------------------------


def n912_predictor_difference(
    predictor_456: float, predictor_912: float
) -> dict[str, Any]:
    """Report an N456 vs N912 predictor comparison.

    The N912 budget is a secondary robustness reading only: it cannot replace,
    rescue or retune the primary N456 predictor.
    """
    return {
        "x_456": float(predictor_456),
        "x_912": float(predictor_912),
        "difference": float(predictor_912) - float(predictor_456),
        "role": N912_ROBUSTNESS_ROLE,
        "cannot_rescue_primary": N912_CANNOT_RESCUE_PRIMARY,
    }


# ---------------------------------------------------------------------------
# Deterministic artifact skeleton
# ---------------------------------------------------------------------------


def build_predictor_validation_artifact_skeleton(
    *,
    unit_predictor_values: Mapping[str, Any],
    outcome_summaries: Mapping[str, Any],
    point_statistics: Mapping[str, Any],
    bootstrap_provenance: Mapping[str, Any],
    status: str = "SYNTHETIC_ENGINEERING_ONLY",
    incompleteness: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Schema skeleton for a future formal R4 predictor validation artifact.

    The skeleton never loads or produces real study outcomes; a future
    authorized caller supplies the values after formal execution.
    """
    payload: dict[str, Any] = {
        "artifact_type": "r4-predictor-validation",
        "artifact_version": 1,
        "fingerprint_version": FINGERPRINT_VERSION,
        "predictor_freeze_fingerprint": PREDICTOR_FREEZE_FINGERPRINT,
        "predictor_candidate_fingerprint": PREDICTOR_CANDIDATE_FINGERPRINT,
        "inference_freeze_fingerprint": R4_INFERENCE_FREEZE_FINGERPRINT,
        "validation_protocol_id": VALIDATION_PROTOCOL_ID,
        "validation_protocol_version": VALIDATION_PROTOCOL_VERSION,
        "implementation_id": PREDICTOR_IMPLEMENTATION_ID,
        "implementation_version": PREDICTOR_IMPLEMENTATION_VERSION,
        "unit_predictor_values": _canonical(value=unit_predictor_values),
        "outcome_summaries": _canonical(value=outcome_summaries),
        "point_statistics": _canonical(value=point_statistics),
        "bootstrap_provenance": _canonical(value=bootstrap_provenance),
        "status": status,
        "incompleteness": [_canonical(value=item) for item in incompleteness],
    }
    payload["artifact_fingerprint"] = fingerprint(payload)
    return payload


def _canonical(value: Any) -> Any:
    """Recursively stringify composite keys and normalize tuples to lists."""
    if isinstance(value, Mapping):
        return {_canonical_key(key): _canonical(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    return value


def _canonical_key(key: Any) -> str:
    if isinstance(key, str):
        return key
    if isinstance(key, tuple):
        return "|".join(_canonical_key(part) for part in key)
    return str(key)


def predictor_state_fingerprint(payload: Mapping[str, Any]) -> str:
    """Deterministic fingerprint of a predictor state payload."""
    return state_fingerprint(payload)


def predictor_canonical_json(payload: Mapping[str, Any]) -> str:
    """Deterministic canonical JSON of a predictor state payload."""
    return canonical_state_json(payload)
