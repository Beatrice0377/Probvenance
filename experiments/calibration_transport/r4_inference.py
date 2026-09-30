"""R4 inference + multiplicity statistical infrastructure (research layer).

This module is the research-layer implementation of the frozen R4 inference and
multiplicity semantics recorded in ``R4_INFERENCE_MULTIPLICITY_FREEZE.md`` /
``R4_INFERENCE_MULTIPLICITY_FREEZE.json``.

It is *statistical infrastructure*, not a study runner. It never downloads
datasets, never loads models, never opens a GPU, and never searches for result
files. Every entry point takes explicit in-memory records (or an explicit path
supplied by a future caller).

Hard rules encoded here:

* stdlib only (plus ``probvenance.fingerprint`` for the deterministic
  fingerprint convention);
* every draw is deterministic and reproducible from a frozen identity payload -
  ``random``, ``numpy.random``, ``secrets``, system entropy, wall-clock seeds
  and the Python builtin ``hash`` are never used for sampling;
* exact LogLoss is carried as an explicit extended-real state and is never
  clipped, smoothed, or repaired with ``nextafter``;
* failures fail closed: incomplete coverage, incomplete measurement pairing and
  failed refit replicates produce ``INCOMPLETE`` states, never a
  successful-subset substitute.

This module performs no formal R4 measurement, no calibration fitting on real
study scores, no formal bootstrap execution and no Brier / LogLoss / transport
analysis. It is pre-outcome infrastructure engineering.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from probvenance.fingerprint import canonical_json, fingerprint

# ---------------------------------------------------------------------------
# Frozen identities
# ---------------------------------------------------------------------------

FREEZE_ARTIFACT_TYPE = "r4-inference-multiplicity-freeze"
FREEZE_ARTIFACT_VERSION = 1
FREEZE_STATUS = "FROZEN"
FINGERPRINT_VERSION = 1

CANDIDATE_FINGERPRINT = "5e10be53c8151d10992b70f4940d0e6f6a7aa83dfe4d5cd49e62b485b0c5e267"
CANDIDATE_COMMIT = "2ef9d31cda96dfc3bb326625dad0df061bb7063e"
FREEZE_COMMIT = "8fc2f3ae465708aa12b108e838377e745e36116b"
R4_INFERENCE_FREEZE_FINGERPRINT = (
    "dcbb7ac9e931145fdee86ab984de1249c1b86ca36ee735b70dafc8cabc06c141"
)

TEST_BOOTSTRAP_PROTOCOL_ID = "r4-population-aware-paired-test-bootstrap"
TEST_BOOTSTRAP_PROTOCOL_VERSION = 1
TEST_BOOTSTRAP_REPLICATES = 20000

TRAIN_REFIT_PROTOCOL_ID = "r4-stratum-preserving-paired-train-refit-bootstrap"
TRAIN_REFIT_PROTOCOL_VERSION = 1
TRAIN_REFIT_REPLICATES = 2000

PANEL_AGGREGATION_PROTOCOL_ID = (
    "r4-equal-population-equal-current-model-panel-aggregation"
)
PANEL_AGGREGATION_PROTOCOL_VERSION = 1

MULTIPLICITY_CORRECTION_ID = "bonferroni-percentile-interval"
PERCENTILE_RULE_ID = "nearest-rank-percentile"

R3_PROTOCOL_ID = "r3-confirmatory-procedure-conditioned-transport"
R3_PROTOCOL_VERSION = 1
R3_PROTOCOL_FINGERPRINT = (
    "3ef63056ae16b18ad65d9c87d1fbec5b43550873a0e3e25ec0a323f954ee974d"
)

PROCEDURE_FINGERPRINTS: Mapping[str, str] = {
    "P-low": "7a8e13d51e131f2102cca4e00b172c8bbb2eb49e591acd3746aeb64d003c8857",
    "P-historical": "a44e9217dd43e5e29d859c8dd2dc510a5876db4d46a8e0cc2fd4f1df3121a423",
    "L-low": "91d7d506275aade7d4676c39722ac2c4d975de7967a25a808395c056307ad619",
    "L-historical": "23ec12bbf4a809ba2f419491df80d1f228d3fd778d848115839aab3697f9dd58",
    "I-isotonic": "cd13bc07bf92f3375bcd16d57fa5f515cd40f68199b57181791f85c58be8c244",
    "B-beta": "f4b710fb98f7c3056794aa709d53309f462a8f598cef8089d2f9c0ed6f7e37ff",
}

# ---------------------------------------------------------------------------
# Frozen panel / family constants
# ---------------------------------------------------------------------------

PRIMARY_MODELS: tuple[str, ...] = (
    "allenai/Olmo-3-7B-Instruct",
    "tiiuae/Falcon-H1-7B-Instruct",
    "ibm-granite/granite-4.0-h-tiny",
    "Qwen/Qwen3.5-9B",
)

LEGACY_MODELS: tuple[str, ...] = (
    "openbmb/MiniCPM5-2B",
    "Qwen/Qwen3.5-2B",
)

MMLU_POPULATION_ID = "r4-mmlu-57-subject"
HELLASWAG_POPULATION_ID = "r4-hellaswag-activity-primary"
MEDMCQA_POPULATION_ID = "r4-medmcqa-subject-primary"

PRIMARY_POPULATIONS: tuple[str, ...] = (
    MMLU_POPULATION_ID,
    HELLASWAG_POPULATION_ID,
    MEDMCQA_POPULATION_ID,
)

LEGACY_POPULATIONS: tuple[str, ...] = (
    HELLASWAG_POPULATION_ID,
    MEDMCQA_POPULATION_ID,
)

DIRECTIONS: tuple[str, ...] = ("CAT->OVR", "OVR->CAT")
DIRECTION_MEASUREMENTS: Mapping[str, tuple[str, str]] = {
    "CAT->OVR": ("CAT", "OVR"),
    "OVR->CAT": ("OVR", "CAT"),
}

MEASUREMENT_CAT = "CAT"
MEASUREMENT_OVR = "OVR"
MEASUREMENTS: tuple[str, ...] = (MEASUREMENT_CAT, MEASUREMENT_OVR)

LOGISTIC_CORE_PROCEDURES: tuple[str, ...] = (
    "P-low",
    "P-historical",
    "L-low",
    "L-historical",
)
STANDALONE_PROCEDURES: tuple[str, ...] = ("I-isotonic", "B-beta")
ALL_PROCEDURES: tuple[str, ...] = LOGISTIC_CORE_PROCEDURES + STANDALONE_PROCEDURES

FACTORIAL_EFFECTS: tuple[str, ...] = ("Feature", "Regularization", "Interaction")
PRIMARY_FAMILY_ESTIMANDS: tuple[str, ...] = ("Delta_deploy", "Delta_transport")
ESTIMANDS: tuple[str, ...] = ("Delta_deploy", "Delta_transport", "Delta_native")

PRIMARY_FAMILY_SIZE = 12
EXTENSION_FAMILY_SIZE = 8
DIRECTION_DIFFERENCE_FAMILY_SIZE = 6
NATIVE_REFERENCE_FAMILY_SIZE = 12

PRIMARY_UNIT_COUNT = 24
PRIMARY_MODEL_POPULATION_CELL_COUNT = 12
LEGACY_SECONDARY_UNIT_COUNT = 8

PRIMARY_LOWER_TAIL = Fraction(1, 480)
PRIMARY_UPPER_TAIL = Fraction(479, 480)
EXTENSION_LOWER_TAIL = Fraction(1, 320)
EXTENSION_UPPER_TAIL = Fraction(319, 320)
DIRECTION_LOWER_TAIL = Fraction(1, 240)
DIRECTION_UPPER_TAIL = Fraction(239, 240)
NATIVE_LOWER_TAIL = Fraction(1, 480)
NATIVE_UPPER_TAIL = Fraction(479, 480)

PRIMARY_AUDIT_LOWER_RANK = 42
PRIMARY_AUDIT_UPPER_RANK = 19959
EXTENSION_AUDIT_LOWER_RANK = 63
EXTENSION_AUDIT_UPPER_RANK = 19938
DIRECTION_AUDIT_LOWER_RANK = 84
DIRECTION_AUDIT_UPPER_RANK = 19917
NATIVE_AUDIT_LOWER_RANK = 42
NATIVE_AUDIT_UPPER_RANK = 19959

# TRAIN-refit interval levels, expressed as fractions of the replicate count
# (2.5 %, 50 %, 97.5 %).  The frozen nearest-rank rule takes a fraction, not a
# percentage, so ``ceil(level * n)`` reproduces the frozen audit ranks below.
REFIT_LOWER_LEVEL = Fraction(1, 40)
REFIT_MEDIAN_LEVEL = Fraction(1, 2)
REFIT_UPPER_LEVEL = Fraction(39, 40)
REFIT_AUDIT_LOWER_RANK = 50
REFIT_AUDIT_MEDIAN_RANK = 1000
REFIT_AUDIT_UPPER_RANK = 1950

FAMILY_SIZES: Mapping[str, int] = {
    "primary": PRIMARY_FAMILY_SIZE,
    "secondary_extension": EXTENSION_FAMILY_SIZE,
    "secondary_direction_difference": DIRECTION_DIFFERENCE_FAMILY_SIZE,
    "secondary_native_reference": NATIVE_REFERENCE_FAMILY_SIZE,
}

# Family selection is expressed through the ``procedures`` argument of
# ``run_panel_test_bootstrap``; these aliases name the two frozen selections.
# The primary logistic-core family never requires the standalone extensions.
PRIMARY_FAMILY_PROCEDURES: tuple[str, ...] = LOGISTIC_CORE_PROCEDURES
EXTENSION_FAMILY_PROCEDURES: tuple[str, ...] = STANDALONE_PROCEDURES

# Frozen formal population structures (used by formal-mode validators only).
FORMAL_MMLU_SUBJECT_COUNT = 57
FORMAL_MMLU_TEST_PER_SUBJECT = 20
FORMAL_MMLU_TRAIN_PER_SUBJECT = 8
FORMAL_MMLU_TEST_COUNT = 1140
FORMAL_MMLU_TRAIN_COUNT = 456

FORMAL_HELLASWAG_TEST_COUNT = 10042
FORMAL_HELLASWAG_TRAIN_COUNT = 456
FORMAL_HELLASWAG_ROBUSTNESS_TRAIN_COUNT = 912
FORMAL_HELLASWAG_ACTIVITY_LABEL_COUNT = 192
FORMAL_HELLASWAG_SOURCE_ID_COUNT = 8407

FORMAL_MEDMCQA_TEST_COUNT = 4162
FORMAL_MEDMCQA_TRAIN_COUNT = 456
FORMAL_MEDMCQA_ROBUSTNESS_TRAIN_COUNT = 912
FORMAL_MEDMCQA_SUBJECT_COUNT = 21

FORMAL_PRIMARY_TRAIN_COUNT = 456
FORMAL_SECONDARY_ROBUSTNESS_TRAIN_COUNT = 912

BUDGET_N456 = "N456"
BUDGET_N912 = "N912"

SPLIT_TYPE_VALUES: tuple[str, ...] = ("indomain", "zeroshot")

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class R4InferenceError(Exception):
    """Base class for every R4 inference infrastructure error."""


class RowContractViolation(R4InferenceError, ValueError):
    """An inference row violates the frozen row contract."""


class PopulationContractViolation(R4InferenceError, ValueError):
    """Population metadata or membership violates the frozen contract."""


class PanelIncomplete(R4InferenceError, ValueError):
    """A required model x population cell is missing from a panel aggregate."""


class FactorialContractViolation(R4InferenceError, ValueError):
    """The factorial transform received a non-logistic-core procedure set."""


class HellaswagClusterStratumAmbiguity(R4InferenceError, ValueError):
    """A HellaSwag source_id maps to more than one activity_label."""


class MeasurementIncompleteness(R4InferenceError, ValueError):
    """Paired fixed-event measurement completeness is not satisfied."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


class N912ContractViolation(R4InferenceError, ValueError):
    """The N456 / N912 nestedness or TEST identity contract is violated."""


class DirectionContractViolation(R4InferenceError, ValueError):
    """A direction contract was violated (e.g. source applied to source)."""


class ExtendedRealContractViolation(R4InferenceError, ValueError):
    """An extended-real value violates its frozen state contract."""


class BootstrapContractViolation(R4InferenceError, ValueError):
    """A bootstrap engine precondition is violated."""


DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"


class DependencyUnavailable(R4InferenceError):
    """A required scientific dependency is unavailable.

    This is an *expected domain state* (a frozen family member is INELIGIBLE, or
    was not requested) and never a programming bug.  A raw ``KeyError`` escaping
    a formal API would be a bug; this class is deliberately **not** a
    ``KeyError`` subclass so that the two are machine-distinguishable::

        isinstance(exc, DependencyUnavailable)  ->  expected incompleteness
        isinstance(exc, KeyError)               ->  programming bug
    """

    code = DEPENDENCY_UNAVAILABLE

    def __init__(
        self, *, family: str, dependency: str, message: str | None = None
    ) -> None:
        self.family = family
        self.dependency = dependency
        text = message or f"{family} requires unavailable dependency {dependency!r}"
        super().__init__(text)

    def payload(self) -> dict[str, str]:
        return {
            "code": self.code,
            "family": self.family,
            "dependency": self.dependency,
            "message": str(self),
        }


# ---------------------------------------------------------------------------
# Extended-real arithmetic (exact LogLoss carrier)
# ---------------------------------------------------------------------------

FINITE = "FINITE"
POSITIVE_INFINITY = "POSITIVE_INFINITY"
NEGATIVE_INFINITY = "NEGATIVE_INFINITY"
UNDEFINED_EXTENDED_REAL = "UNDEFINED_EXTENDED_REAL"

EXTENDED_REAL_STATES: tuple[str, ...] = (
    FINITE,
    POSITIVE_INFINITY,
    NEGATIVE_INFINITY,
    UNDEFINED_EXTENDED_REAL,
)


@dataclass(frozen=True)
class ExtendedReal:
    """An explicit extended-real value.

    ``value`` is populated if and only if ``state`` is :data:`FINITE`. The
    frozen LogLoss policy requires this explicit carrier instead of raw
    ``float("inf")`` values that could be subtracted carelessly.
    """

    state: str
    value: float | None = None

    def __post_init__(self) -> None:
        if self.state not in EXTENDED_REAL_STATES:
            raise ExtendedRealContractViolation(f"unknown extended-real state {self.state!r}")
        if self.state == FINITE:
            if self.value is None or not math.isfinite(self.value):
                raise ExtendedRealContractViolation("FINITE requires a finite value")
        elif self.value is not None:
            raise ExtendedRealContractViolation(
                f"{self.state} must not carry a finite value"
            )

    @classmethod
    def finite(cls, value: float) -> ExtendedReal:
        return cls(FINITE, float(value))

    @classmethod
    def positive_infinity(cls) -> ExtendedReal:
        return cls(POSITIVE_INFINITY)

    @classmethod
    def negative_infinity(cls) -> ExtendedReal:
        return cls(NEGATIVE_INFINITY)

    @classmethod
    def undefined(cls) -> ExtendedReal:
        return cls(UNDEFINED_EXTENDED_REAL)

    @property
    def is_finite(self) -> bool:
        return self.state == FINITE

    def negated(self) -> ExtendedReal:
        if self.state == FINITE:
            return ExtendedReal.finite(-self.value)  # type: ignore[arg-type]
        if self.state == POSITIVE_INFINITY:
            return ExtendedReal.negative_infinity()
        if self.state == NEGATIVE_INFINITY:
            return ExtendedReal.positive_infinity()
        return ExtendedReal.undefined()

    def add(self, other: ExtendedReal) -> ExtendedReal:
        if self.state == UNDEFINED_EXTENDED_REAL or other.state == UNDEFINED_EXTENDED_REAL:
            return ExtendedReal.undefined()
        if self.state == FINITE and other.state == FINITE:
            return ExtendedReal.finite(self.value + other.value)  # type: ignore[operator]
        if self.state == FINITE:
            return other
        if other.state == FINITE:
            return self
        if self.state == other.state:
            return self
        return ExtendedReal.undefined()

    def subtract(self, other: ExtendedReal) -> ExtendedReal:
        return self.add(other.negated())

    def state_payload(self) -> dict[str, Any]:
        return {"state": self.state, "value": self.value}


def extended_real_add(left: ExtendedReal, right: ExtendedReal) -> ExtendedReal:
    return left.add(right)


def extended_real_subtract(left: ExtendedReal, right: ExtendedReal) -> ExtendedReal:
    """Subtraction under the frozen extended-real difference table.

    The frozen table pins ``finite - finite``, ``+inf - finite``,
    ``finite - +inf`` and ``+inf - +inf``. The remaining combinations are the
    natural total extension of the same algebra and are documented as such.
    """
    return left.subtract(right)


def extended_real_sum(values: Sequence[ExtendedReal]) -> ExtendedReal:
    total = ExtendedReal.finite(0.0)
    for value in values:
        total = total.add(value)
    return total


def extended_real_mean(values: Sequence[ExtendedReal]) -> ExtendedReal:
    if not values:
        raise ExtendedRealContractViolation("mean of an empty extended-real sequence")
    total = extended_real_sum(values)
    if total.state == FINITE:
        return ExtendedReal.finite(total.value / len(values))  # type: ignore[operator]
    return total


# ---------------------------------------------------------------------------
# Row model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class R4InferenceRow:
    """One frozen fixed-event measurement row for one model x population.

    ``cat_score`` is the CAT (direct categorical anchor) fixed-decision
    semantic probability and ``ovr_score`` is the OVR (independent binary
    anchor) fixed-decision semantic probability. Both are exact probabilities
    in ``[0, 1]``; they are never clipped.
    """

    item_id: str
    population_id: str
    stratum: str
    label: int
    cat_score: float
    ovr_score: float
    cluster_id: str | None = None
    anchor_index: int | None = None

    def __post_init__(self) -> None:
        if not self.item_id:
            raise RowContractViolation("item_id must be a non-empty string")
        if not self.population_id:
            raise RowContractViolation("population_id must be a non-empty string")
        if not self.stratum:
            raise RowContractViolation("stratum must be a non-empty string")
        if self.label not in (0, 1):
            raise RowContractViolation(f"label must be 0 or 1, got {self.label!r}")
        for name, score in (("cat_score", self.cat_score), ("ovr_score", self.ovr_score)):
            if not isinstance(score, (int, float)) or isinstance(score, bool):
                raise RowContractViolation(f"{name} must be a real number")
            if not math.isfinite(float(score)):
                raise RowContractViolation(f"{name} must be finite")
            if not 0.0 <= float(score) <= 1.0:
                raise RowContractViolation(f"{name} must lie in [0, 1]")
        if self.anchor_index is not None and not isinstance(self.anchor_index, int):
            raise RowContractViolation("anchor_index must be an int when present")

    def score(self, measurement: str) -> float:
        return measurement_score(self, measurement)


@dataclass(frozen=True)
class FrozenItemReference:
    """The frozen identity of one selected item (no model outcome involved)."""

    item_id: str
    label: int
    anchor_index: int


@dataclass(frozen=True)
class PopulationMetadata:
    """Frozen population identity plus its sampler and estimator contract."""

    population_id: str
    population_fingerprint: str
    stratum_field: str
    group_field: str | None
    test_bootstrap_protocol_id: str
    test_bootstrap_protocol_version: int
    test_bootstrap_mode: str
    estimand_weighting: str
    test_count: int
    train_count: int
    n912_manifest_fingerprint: str | None = None
    n912_train_count: int | None = None

    def __post_init__(self) -> None:
        if self.test_bootstrap_mode not in (
            "subject-stratified-row",
            "subject_name-stratified-row",
            "activity-stratified-source_id-cluster",
        ):
            raise PopulationContractViolation(
                f"unknown test_bootstrap_mode {self.test_bootstrap_mode!r}"
            )
        if self.estimand_weighting not in (
            "equal-subject-mean-of-subject-means",
            "row-weighted-mean",
        ):
            raise PopulationContractViolation(
                f"unknown estimand_weighting {self.estimand_weighting!r}"
            )
        if self.test_bootstrap_mode == "activity-stratified-source_id-cluster" and (
            self.group_field != "source_id"
        ):
            raise PopulationContractViolation(
                "cluster mode requires group_field == 'source_id'"
            )
        if self.test_bootstrap_mode == "subject_name-stratified-row" and (
            self.stratum_field != "subject_name"
        ):
            raise PopulationContractViolation(
                "MedMCQA mode requires stratum_field == 'subject_name'"
            )
        if self.test_bootstrap_mode == "subject-stratified-row" and (
            self.stratum_field != "subject"
        ):
            raise PopulationContractViolation(
                "MMLU mode requires stratum_field == 'subject'"
            )


# ---------------------------------------------------------------------------
# Direction contract
# ---------------------------------------------------------------------------


def direction_measurements(direction_id: str) -> tuple[str, str]:
    """Return ``(source_measurement, target_measurement)`` for a direction."""
    try:
        return DIRECTION_MEASUREMENTS[direction_id]
    except KeyError as exc:  # pragma: no cover - defensive
        raise DirectionContractViolation(f"unknown direction {direction_id!r}") from exc


def source_measurement(direction_id: str) -> str:
    return direction_measurements(direction_id)[0]


def target_measurement(direction_id: str) -> str:
    return direction_measurements(direction_id)[1]


def measurement_score(row: R4InferenceRow, measurement: str) -> float:
    if measurement == MEASUREMENT_CAT:
        return float(row.cat_score)
    if measurement == MEASUREMENT_OVR:
        return float(row.ovr_score)
    raise DirectionContractViolation(f"unknown measurement {measurement!r}")


def source_scores(rows: Sequence[R4InferenceRow], direction_id: str) -> tuple[float, ...]:
    measurement = source_measurement(direction_id)
    return tuple(measurement_score(row, measurement) for row in rows)


def target_scores(rows: Sequence[R4InferenceRow], direction_id: str) -> tuple[float, ...]:
    """The cross map input: the TARGET measurement score ``S_B``.

    The frozen estimand definition applies the source-fitted map to the target
    measurement score. It is never applied to ``S_A``.
    """
    measurement = target_measurement(direction_id)
    return tuple(measurement_score(row, measurement) for row in rows)


def cross_map_inputs(
    rows: Sequence[R4InferenceRow], direction_id: str
) -> tuple[tuple[float, ...], str]:
    """Return the cross-map input scores and the measurement they came from."""
    measurement = target_measurement(direction_id)
    scores = tuple(measurement_score(row, measurement) for row in rows)
    return scores, measurement


# ---------------------------------------------------------------------------
# Losses
# ---------------------------------------------------------------------------


def brier_loss(probability: float, label: int) -> float:
    return (float(probability) - float(label)) ** 2


def logloss_loss(probability: float, label: int) -> ExtendedReal:
    """Exact LogLoss with no clipping and no smoothing.

    ``log(0)`` is never evaluated: the zero-mass cases branch explicitly and
    return the exact infinity state.
    """
    p = float(probability)
    if p == 0.0:
        return ExtendedReal.finite(0.0) if label == 0 else ExtendedReal.positive_infinity()
    if p == 1.0:
        return ExtendedReal.finite(0.0) if label == 1 else ExtendedReal.positive_infinity()
    return ExtendedReal.finite(-math.log(p) if label == 1 else -math.log1p(-p))


def mean_brier(pairs: Sequence[tuple[float, int]]) -> float:
    if not pairs:
        raise BootstrapContractViolation("mean Brier over an empty sequence")
    return math.fsum(brier_loss(p, y) for p, y in pairs) / len(pairs)


def mean_logloss(pairs: Sequence[tuple[float, int]]) -> ExtendedReal:
    if not pairs:
        raise BootstrapContractViolation("mean LogLoss over an empty sequence")
    return extended_real_mean([logloss_loss(p, y) for p, y in pairs])


# ---------------------------------------------------------------------------
# Weighting
# ---------------------------------------------------------------------------


def row_weighted_mean(values: Sequence[float]) -> float:
    if not values:
        raise PopulationContractViolation("row-weighted mean over an empty sequence")
    return math.fsum(float(value) for value in values) / len(values)


def equal_stratum_mean_of_stratum_means(
    strata: Sequence[str], values: Sequence[float]
) -> float:
    """Equal-stratum mean of stratum means (MMLU equal-subject estimator).

    The result is deliberately NOT reduced to a row mean: with unequal stratum
    sizes the two differ.
    """
    if len(strata) != len(values):
        raise PopulationContractViolation("strata and values must have equal length")
    if not values:
        raise PopulationContractViolation("equal-stratum mean over an empty sequence")
    buckets: dict[str, list[float]] = {}
    for stratum, value in zip(strata, values, strict=True):
        buckets.setdefault(stratum, []).append(float(value))
    stratum_means = [row_weighted_mean(bucket) for bucket in buckets.values()]
    return math.fsum(stratum_means) / len(stratum_means)


def population_mean_of_rows(
    metadata: PopulationMetadata,
    strata: Sequence[str],
    values: Sequence[float],
) -> float:
    """Apply the frozen estimator for the given population."""
    if metadata.estimand_weighting == "equal-subject-mean-of-subject-means":
        return equal_stratum_mean_of_stratum_means(strata, values)
    return row_weighted_mean(values)


def aggregate_population_rows(
    metadata: PopulationMetadata,
    rows: Sequence[R4InferenceRow],
    values: Sequence[float],
) -> float:
    if len(rows) != len(values):
        raise PopulationContractViolation("rows and values must have equal length")
    strata = [row.stratum for row in rows]
    return population_mean_of_rows(metadata, strata, values)


# ---------------------------------------------------------------------------
# Risk matrix
# ---------------------------------------------------------------------------

Calibrator = Callable[[float], float]


def risk_raw(rows: Sequence[R4InferenceRow], measurement: str) -> float:
    return mean_brier([(measurement_score(row, measurement), row.label) for row in rows])


def risk_native(
    rows: Sequence[R4InferenceRow], measurement: str, native_map: Calibrator
) -> float:
    return mean_brier(
        [(native_map(measurement_score(row, measurement)), row.label) for row in rows]
    )


def risk_cross(rows: Sequence[R4InferenceRow], direction_id: str, cross_map: Calibrator) -> float:
    """Cross risk: the source-fitted map applied to the TARGET measurement score."""
    scores, _measurement = cross_map_inputs(rows, direction_id)
    labels = [row.label for row in rows]
    return mean_brier(
        [(cross_map(score), label) for score, label in zip(scores, labels, strict=True)]
    )


def mean_paired_difference(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise BootstrapContractViolation("paired difference requires equal lengths")
    if not left:
        raise BootstrapContractViolation("paired difference over an empty sequence")
    return math.fsum(a - b for a, b in zip(left, right, strict=True)) / len(left)


def _paired_brier(predictions: Sequence[float], labels: Sequence[int]) -> list[float]:
    return [
        brier_loss(prediction, label)
        for prediction, label in zip(predictions, labels, strict=True)
    ]


def delta_deploy(
    rows: Sequence[R4InferenceRow], direction_id: str, cross_map: Calibrator
) -> float:
    scores = target_scores(rows, direction_id)
    labels = [row.label for row in rows]
    cross = _paired_brier([cross_map(score) for score in scores], labels)
    raw = _paired_brier(scores, labels)
    return mean_paired_difference(cross, raw)


def delta_native(
    rows: Sequence[R4InferenceRow], direction_id: str, native_map: Calibrator
) -> float:
    scores = target_scores(rows, direction_id)
    labels = [row.label for row in rows]
    native = _paired_brier([native_map(score) for score in scores], labels)
    raw = _paired_brier(scores, labels)
    return mean_paired_difference(native, raw)


def delta_transport(
    rows: Sequence[R4InferenceRow],
    direction_id: str,
    cross_map: Calibrator,
    native_map: Calibrator,
) -> float:
    scores = target_scores(rows, direction_id)
    labels = [row.label for row in rows]
    cross = _paired_brier([cross_map(score) for score in scores], labels)
    native = _paired_brier([native_map(score) for score in scores], labels)
    return mean_paired_difference(cross, native)


@dataclass(frozen=True)
class RiskMatrix:
    direction_id: str
    r_raw: float
    r_native: float
    r_cross: float
    delta_native: float
    delta_deploy: float
    delta_transport: float


def risk_matrix(
    rows: Sequence[R4InferenceRow],
    direction_id: str,
    cross_map: Calibrator,
    native_map: Calibrator,
) -> RiskMatrix:
    measurement = target_measurement(direction_id)
    return RiskMatrix(
        direction_id=direction_id,
        r_raw=risk_raw(rows, measurement),
        r_native=risk_native(rows, measurement, native_map),
        r_cross=risk_cross(rows, direction_id, cross_map),
        delta_native=delta_native(rows, direction_id, native_map),
        delta_deploy=delta_deploy(rows, direction_id, cross_map),
        delta_transport=delta_transport(rows, direction_id, cross_map, native_map),
    )


# ---------------------------------------------------------------------------
# Panel aggregation
# ---------------------------------------------------------------------------


def population_mean(
    per_model: Mapping[str, float], expected_models: Sequence[str] = PRIMARY_MODELS
) -> float:
    missing = [model for model in expected_models if model not in per_model]
    if missing:
        raise PanelIncomplete(f"missing model cells: {sorted(missing)}")
    extra = [model for model in per_model if model not in expected_models]
    if extra:
        raise PanelIncomplete(f"unexpected model cells: {sorted(extra)}")
    return math.fsum(float(per_model[model]) for model in expected_models) / len(expected_models)


def panel_mean(
    per_population: Mapping[str, float],
    expected_populations: Sequence[str] = PRIMARY_POPULATIONS,
) -> float:
    missing = [pop for pop in expected_populations if pop not in per_population]
    if missing:
        raise PanelIncomplete(f"missing population cells: {sorted(missing)}")
    extra = [pop for pop in per_population if pop not in expected_populations]
    if extra:
        raise PanelIncomplete(f"unexpected population cells: {sorted(extra)}")
    return math.fsum(float(per_population[pop]) for pop in expected_populations) / len(
        expected_populations
    )


def panel_aggregate(
    values: Mapping[tuple[str, str], float],
    *,
    models: Sequence[str] = PRIMARY_MODELS,
    populations: Sequence[str] = PRIMARY_POPULATIONS,
) -> float:
    """Aggregate a ``(model, population) -> value`` mapping hierarchically."""
    per_population: dict[str, float] = {}
    for population in populations:
        per_model = {
            model: values[(model, population)]
            for model in models
            if (model, population) in values
        }
        per_population[population] = population_mean(per_model, models)
    return panel_mean(per_population, populations)


# ---------------------------------------------------------------------------
# Factorial contrasts
# ---------------------------------------------------------------------------


def factorial_contrasts(values: Mapping[str, float]) -> dict[str, float]:
    """The frozen 2x2 logistic-core factorial transform.

    Only the four logistic-core procedures may be supplied. I-isotonic and
    B-beta are standalone extensions and are never part of the factorial.
    """
    keys = set(values)
    expected = set(LOGISTIC_CORE_PROCEDURES)
    if keys != expected:
        unexpected = sorted(keys - expected)
        missing = sorted(expected - keys)
        raise FactorialContractViolation(
            f"factorial requires exactly the four logistic-core procedures; "
            f"unexpected={unexpected} missing={missing}"
        )
    p_low = float(values["P-low"])
    p_hist = float(values["P-historical"])
    l_low = float(values["L-low"])
    l_hist = float(values["L-historical"])
    return {
        "Feature": 0.5 * (l_low + l_hist - p_low - p_hist),
        "Regularization": 0.5 * (p_low + l_low - p_hist - l_hist),
        "Interaction": (l_low - p_low) - (l_hist - p_hist),
    }


# ---------------------------------------------------------------------------
# Deterministic draw kernel
# ---------------------------------------------------------------------------


def deterministic_index(identity: Mapping[str, Any], pool_size: int) -> int:
    """Map a frozen identity payload onto a pool position deterministically."""
    if pool_size <= 0:
        raise BootstrapContractViolation("pool_size must be positive")
    digest = fingerprint(dict(identity))
    return int(digest[:16], 16) % pool_size


def row_draw_identity(
    *,
    protocol_id: str,
    protocol_version: int,
    population_id: str,
    population_fingerprint: str,
    replicate_index: int,
    stratum: str,
    draw_index: int,
    pool_size: int,
    cluster_mode_marker: str | None = None,
) -> dict[str, Any]:
    identity: dict[str, Any] = {
        "protocol_id": protocol_id,
        "protocol_version": protocol_version,
        "population_id": population_id,
        "population_fingerprint": population_fingerprint,
        "replicate_index": replicate_index,
        "stratum": stratum,
        "draw_index": draw_index,
        "pool_size": pool_size,
    }
    if cluster_mode_marker is not None:
        identity["cluster_mode_marker"] = cluster_mode_marker
    return identity


def train_refit_identity(
    *,
    protocol_id: str,
    protocol_version: int,
    population_id: str,
    population_fingerprint: str,
    budget_identity: str,
    replicate_index: int,
    stratum: str,
    draw_index: int,
    pool_size: int,
) -> dict[str, Any]:
    return {
        "protocol_id": protocol_id,
        "protocol_version": protocol_version,
        "population_id": population_id,
        "population_fingerprint": population_fingerprint,
        "budget_identity": budget_identity,
        "replicate_index": replicate_index,
        "stratum": stratum,
        "draw_index": draw_index,
        "pool_size": pool_size,
    }


def stable_strata(rows: Sequence[R4InferenceRow]) -> tuple[str, ...]:
    return tuple(sorted({row.stratum for row in rows}))


def stable_rows(rows: Sequence[R4InferenceRow]) -> tuple[R4InferenceRow, ...]:
    return tuple(sorted(rows, key=lambda row: row.item_id))


def stable_clusters(rows: Sequence[R4InferenceRow]) -> tuple[str, ...]:
    clusters = {row.cluster_id for row in rows}
    if None in clusters:
        raise PopulationContractViolation("cluster rows must carry a cluster_id")
    return tuple(sorted(cluster for cluster in clusters if cluster is not None))


# ---------------------------------------------------------------------------
# TEST samplers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TestDraw:
    """A shared TEST resampling draw.

    The draw depends only on the frozen population identity and the replicate
    index. It is independent of model, procedure, direction and outcome value.
    """

    population_id: str
    replicate_index: int
    protocol_id: str
    protocol_version: int
    mode: str
    stratum_order: tuple[str, ...]
    per_stratum_occurrences: Mapping[str, tuple[R4InferenceRow, ...]]
    occurrences: tuple[R4InferenceRow, ...]
    provenance: Mapping[str, Any]

    @property
    def expanded_row_count(self) -> int:
        return len(self.occurrences)

    def rows_for_stratum(self, stratum: str) -> tuple[R4InferenceRow, ...]:
        return self.per_stratum_occurrences.get(stratum, ())

    def draw_identity_payload(self) -> dict[str, Any]:
        """The identity fields that determine this draw (model label excluded)."""
        return {
            "population_id": self.population_id,
            "replicate_index": self.replicate_index,
            "protocol_id": self.protocol_id,
            "protocol_version": self.protocol_version,
            "mode": self.mode,
            "stratum_order": list(self.stratum_order),
        }


def _stratified_row_occurrences(
    rows: Sequence[R4InferenceRow],
    metadata: PopulationMetadata,
    replicate_index: int,
) -> tuple[tuple[str, ...], dict[str, tuple[R4InferenceRow, ...]]]:
    per_stratum: dict[str, tuple[R4InferenceRow, ...]] = {}
    stratum_order = stable_strata(rows)
    for stratum in stratum_order:
        pool = stable_rows([row for row in rows if row.stratum == stratum])
        draws: list[R4InferenceRow] = []
        for draw_index in range(len(pool)):
            identity = row_draw_identity(
                protocol_id=metadata.test_bootstrap_protocol_id,
                protocol_version=metadata.test_bootstrap_protocol_version,
                population_id=metadata.population_id,
                population_fingerprint=metadata.population_fingerprint,
                replicate_index=replicate_index,
                stratum=stratum,
                draw_index=draw_index,
                pool_size=len(pool),
            )
            draws.append(pool[deterministic_index(identity, len(pool))])
        per_stratum[stratum] = tuple(draws)
    return stratum_order, per_stratum


def validate_hellaswag_cluster_stratum(
    rows: Sequence[R4InferenceRow],
) -> dict[str, Any]:
    """Structural audit: every cluster_id maps to exactly one stratum."""
    mapping: dict[str, str] = {}
    conflicts: dict[str, set[str]] = {}
    for row in rows:
        if row.cluster_id is None:
            raise PopulationContractViolation("cluster rows must carry a cluster_id")
        previous = mapping.setdefault(row.cluster_id, row.stratum)
        if previous != row.stratum:
            conflicts.setdefault(row.cluster_id, {previous}).add(row.stratum)
    if conflicts:
        raise HellaswagClusterStratumAmbiguity(
            "HELLASWAG_CLUSTER_STRATUM_AMBIGUITY: "
            + "; ".join(
                f"{cluster}->{sorted(strata)}" for cluster, strata in sorted(conflicts.items())
            )
        )
    return {
        "cluster_count": len(mapping),
        "conflicts": 0,
        "status": "PASS",
    }


def _cluster_occurrences(
    rows: Sequence[R4InferenceRow],
    metadata: PopulationMetadata,
    replicate_index: int,
) -> tuple[tuple[str, ...], dict[str, tuple[R4InferenceRow, ...]]]:
    validate_hellaswag_cluster_stratum(rows)
    per_stratum: dict[str, tuple[R4InferenceRow, ...]] = {}
    stratum_order = stable_strata(rows)
    for stratum in stratum_order:
        stratum_rows = [row for row in rows if row.stratum == stratum]
        clusters = stable_clusters(stratum_rows)
        cluster_rows = {
            cluster: stable_rows([row for row in stratum_rows if row.cluster_id == cluster])
            for cluster in clusters
        }
        expanded: list[R4InferenceRow] = []
        for draw_index in range(len(clusters)):
            identity = row_draw_identity(
                protocol_id=metadata.test_bootstrap_protocol_id,
                protocol_version=metadata.test_bootstrap_protocol_version,
                population_id=metadata.population_id,
                population_fingerprint=metadata.population_fingerprint,
                replicate_index=replicate_index,
                stratum=stratum,
                draw_index=draw_index,
                pool_size=len(clusters),
                cluster_mode_marker="source_id-cluster",
            )
            chosen = clusters[deterministic_index(identity, len(clusters))]
            expanded.extend(cluster_rows[chosen])
        per_stratum[stratum] = tuple(expanded)
    return stratum_order, per_stratum


def build_test_draw(
    rows: Sequence[R4InferenceRow],
    metadata: PopulationMetadata,
    replicate_index: int,
    *,
    model_label: str | None = None,
) -> TestDraw:
    """Build the shared TEST draw for one population and replicate.

    ``model_label`` is recorded as provenance only. It never enters the draw
    identity, so the same population/replicate draw is reused by every model,
    procedure and direction.
    """
    if replicate_index < 0:
        raise BootstrapContractViolation("replicate_index must be non-negative")
    if metadata.test_bootstrap_mode == "activity-stratified-source_id-cluster":
        stratum_order, per_stratum = _cluster_occurrences(rows, metadata, replicate_index)
    else:
        stratum_order, per_stratum = _stratified_row_occurrences(rows, metadata, replicate_index)
    occurrences = tuple(row for stratum in stratum_order for row in per_stratum[stratum])
    return TestDraw(
        population_id=metadata.population_id,
        replicate_index=replicate_index,
        protocol_id=metadata.test_bootstrap_protocol_id,
        protocol_version=metadata.test_bootstrap_protocol_version,
        mode=metadata.test_bootstrap_mode,
        stratum_order=stratum_order,
        per_stratum_occurrences=per_stratum,
        occurrences=occurrences,
        provenance={"model_label": model_label},
    )


def validate_formal_population(
    rows: Sequence[R4InferenceRow], metadata: PopulationMetadata
) -> dict[str, Any]:
    """Validate the frozen formal population structure (no outcome involved)."""
    strata = stable_strata(rows)
    if metadata.population_id == MMLU_POPULATION_ID:
        per_stratum = {
            stratum: sum(1 for row in rows if row.stratum == stratum)
            for stratum in strata
        }
        if len(strata) != FORMAL_MMLU_SUBJECT_COUNT:
            raise PopulationContractViolation(
                f"MMLU formal subject count {len(strata)} != {FORMAL_MMLU_SUBJECT_COUNT}"
            )
        wrong = {
            stratum: count
            for stratum, count in per_stratum.items()
            if count != FORMAL_MMLU_TEST_PER_SUBJECT
        }
        if wrong:
            raise PopulationContractViolation(f"MMLU formal per-subject counts invalid: {wrong}")
        if len(rows) != FORMAL_MMLU_TEST_COUNT:
            raise PopulationContractViolation("MMLU formal TEST count mismatch")
        return {
            "population_id": metadata.population_id,
            "stratum_count": len(strata),
            "test_count": len(rows),
        }
    if metadata.population_id == HELLASWAG_POPULATION_ID:
        audit = validate_hellaswag_cluster_stratum(rows)
        if len(rows) != FORMAL_HELLASWAG_TEST_COUNT:
            raise PopulationContractViolation("HellaSwag formal TEST count mismatch")
        if len(strata) != FORMAL_HELLASWAG_ACTIVITY_LABEL_COUNT:
            raise PopulationContractViolation("HellaSwag formal activity-label count mismatch")
        if audit["cluster_count"] != FORMAL_HELLASWAG_SOURCE_ID_COUNT:
            raise PopulationContractViolation("HellaSwag formal source_id count mismatch")
        return {
            "population_id": metadata.population_id,
            "stratum_count": len(strata),
            "test_count": len(rows),
            "cluster_count": audit["cluster_count"],
        }
    if metadata.population_id == MEDMCQA_POPULATION_ID:
        if len(strata) != FORMAL_MEDMCQA_SUBJECT_COUNT:
            raise PopulationContractViolation("MedMCQA formal subject count mismatch")
        if len(rows) != FORMAL_MEDMCQA_TEST_COUNT:
            raise PopulationContractViolation("MedMCQA formal TEST count mismatch")
        return {
            "population_id": metadata.population_id,
            "stratum_count": len(strata),
            "test_count": len(rows),
        }
    raise PopulationContractViolation(f"unknown population {metadata.population_id!r}")


# ---------------------------------------------------------------------------
# TRAIN-refit sampler
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrainRefitDraw:
    population_id: str
    replicate_index: int
    protocol_id: str
    protocol_version: int
    budget_identity: str
    stratum_order: tuple[str, ...]
    per_stratum_occurrences: Mapping[str, tuple[R4InferenceRow, ...]]
    occurrences: tuple[R4InferenceRow, ...]

    @property
    def total_n(self) -> int:
        return len(self.occurrences)


def build_train_refit_draw(
    rows: Sequence[R4InferenceRow],
    metadata: PopulationMetadata,
    replicate_index: int,
    *,
    budget_identity: str = BUDGET_N456,
) -> TrainRefitDraw:
    """Stratum-preserving paired TRAIN-refit draw (total N preserved)."""
    if budget_identity not in (BUDGET_N456, BUDGET_N912):
        raise BootstrapContractViolation(f"unknown budget identity {budget_identity!r}")
    stratum_order = stable_strata(rows)
    per_stratum: dict[str, tuple[R4InferenceRow, ...]] = {}
    for stratum in stratum_order:
        pool = stable_rows([row for row in rows if row.stratum == stratum])
        draws: list[R4InferenceRow] = []
        for draw_index in range(len(pool)):
            identity = train_refit_identity(
                protocol_id=TRAIN_REFIT_PROTOCOL_ID,
                protocol_version=TRAIN_REFIT_PROTOCOL_VERSION,
                population_id=metadata.population_id,
                population_fingerprint=metadata.population_fingerprint,
                budget_identity=budget_identity,
                replicate_index=replicate_index,
                stratum=stratum,
                draw_index=draw_index,
                pool_size=len(pool),
            )
            draws.append(pool[deterministic_index(identity, len(pool))])
        per_stratum[stratum] = tuple(draws)
    occurrences = tuple(row for stratum in stratum_order for row in per_stratum[stratum])
    return TrainRefitDraw(
        population_id=metadata.population_id,
        replicate_index=replicate_index,
        protocol_id=TRAIN_REFIT_PROTOCOL_ID,
        protocol_version=TRAIN_REFIT_PROTOCOL_VERSION,
        budget_identity=budget_identity,
        stratum_order=stratum_order,
        per_stratum_occurrences=per_stratum,
        occurrences=occurrences,
    )


def validate_train_total_n(
    draw: TrainRefitDraw, metadata: PopulationMetadata, expected_n: int
) -> None:
    if draw.total_n != expected_n:
        raise BootstrapContractViolation(
            f"TRAIN-refit total N {draw.total_n} != expected {expected_n}"
        )
    if expected_n not in (metadata.train_count, metadata.n912_train_count):
        raise BootstrapContractViolation(
            f"expected N {expected_n} is not a frozen TRAIN budget of {metadata.population_id}"
        )


def mmlu_refit_draw_counts(draw: TrainRefitDraw) -> dict[str, int]:
    """Per-subject refit draw counts; the R4 rule is 8, never the R3 10."""
    return {stratum: len(rows) for stratum, rows in draw.per_stratum_occurrences.items()}


# ---------------------------------------------------------------------------
# Nearest-rank percentile
# ---------------------------------------------------------------------------


def nearest_rank_percentile(ordered_values: Sequence[float], percentile: Fraction) -> float:
    """The frozen nearest-rank percentile rule.

    ``percentile`` is a fraction of the sample (for example ``Fraction(1, 480)``),
    not a percentage.  ``rank = ceil(percentile * n)`` clamped to ``[1, n]``; the
    returned value is ``ordered_values[rank - 1]``.  No interpolation is performed.
    """
    n = len(ordered_values)
    if n == 0:
        raise BootstrapContractViolation("nearest-rank percentile of an empty sample")
    return float(ordered_values[percentile_rank(percentile, n) - 1])


def percentile_rank(percentile: Fraction, n: int) -> int:
    if n <= 0:
        raise BootstrapContractViolation("sample size must be positive")
    fraction = Fraction(percentile)
    if not 0 < fraction <= 1:
        raise BootstrapContractViolation(
            f"percentile must be a fraction in (0, 1], got {percentile!r}"
        )
    return min(max(math.ceil(fraction * n), 1), n)


def excludes_zero(lower: float, upper: float) -> bool:
    return lower > 0.0 or upper < 0.0


@dataclass(frozen=True)
class Interval:
    n: int
    point_estimate: float | None
    bootstrap_median: float | None
    lower: float | None
    upper: float | None
    tail_rule: str
    excludes_zero: bool | None
    status: str

    def payload(self) -> dict[str, Any]:
        return {
            "n": self.n,
            "point_estimate": self.point_estimate,
            "bootstrap_median": self.bootstrap_median,
            "lower": self.lower,
            "upper": self.upper,
            "tail_rule": self.tail_rule,
            "excludes_zero": self.excludes_zero,
            "status": self.status,
        }


STATUS_COMPLETE = "COMPLETE"
STATUS_INCOMPLETE = "INCOMPLETE"


def percentile_interval(
    samples: Sequence[float],
    *,
    lower_tail: Fraction,
    upper_tail: Fraction,
    median_level: Fraction = Fraction(1, 2),
    point_estimate: float | None = None,
    status: str = STATUS_COMPLETE,
) -> Interval:
    ordered = sorted(float(value) for value in samples)
    tail_rule = f"{lower_tail}/{upper_tail}"
    if not ordered:
        return Interval(
            n=0,
            point_estimate=point_estimate,
            bootstrap_median=None,
            lower=None,
            upper=None,
            tail_rule=tail_rule,
            excludes_zero=None,
            status=STATUS_INCOMPLETE,
        )
    lower = nearest_rank_percentile(ordered, lower_tail)
    upper = nearest_rank_percentile(ordered, upper_tail)
    median = nearest_rank_percentile(ordered, median_level)
    return Interval(
        n=len(ordered),
        point_estimate=point_estimate,
        bootstrap_median=median,
        lower=lower,
        upper=upper,
        tail_rule=tail_rule,
        excludes_zero=excludes_zero(lower, upper),
        status=status,
    )


# ---------------------------------------------------------------------------
# Hypothesis registries
# ---------------------------------------------------------------------------

NATIVE_IMPROVEMENT_SUPPORTED = "NATIVE_IMPROVEMENT_SUPPORTED"
NATIVE_DEGRADATION_SUPPORTED = "NATIVE_DEGRADATION_SUPPORTED"
NATIVE_ADEQUACY_UNRESOLVED = "NATIVE_ADEQUACY_UNRESOLVED"


@dataclass(frozen=True)
class Hypothesis:
    hypothesis_id: str
    family: str
    components: Mapping[str, str]
    unit: str
    lower_tail: Fraction
    upper_tail: Fraction
    audit_lower_rank: int
    audit_upper_rank: int
    replicates: int
    correction: str = MULTIPLICITY_CORRECTION_ID
    percentile_rule: str = PERCENTILE_RULE_ID

    def payload(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "family": self.family,
            "components": dict(self.components),
            "unit": self.unit,
            "lower_tail": f"{self.lower_tail}",
            "upper_tail": f"{self.upper_tail}",
            "audit_lower_rank": self.audit_lower_rank,
            "audit_upper_rank": self.audit_upper_rank,
            "replicates": self.replicates,
            "correction": self.correction,
            "percentile_rule": self.percentile_rule,
        }


def primary_hypotheses() -> tuple[Hypothesis, ...]:
    """The 12 primary prospective confirmatory hypotheses."""
    out: list[Hypothesis] = []
    for estimand in PRIMARY_FAMILY_ESTIMANDS:
        for direction in DIRECTIONS:
            for effect in FACTORIAL_EFFECTS:
                out.append(
                    Hypothesis(
                        hypothesis_id=f"primary::{estimand}::{direction}::{effect}",
                        family="primary-prospective-confirmatory",
                        components={
                            "estimand": estimand,
                            "direction": direction,
                            "effect": effect,
                        },
                        unit="R4PanelMean factorial contrast (hierarchically equal-weighted)",
                        lower_tail=PRIMARY_LOWER_TAIL,
                        upper_tail=PRIMARY_UPPER_TAIL,
                        audit_lower_rank=PRIMARY_AUDIT_LOWER_RANK,
                        audit_upper_rank=PRIMARY_AUDIT_UPPER_RANK,
                        replicates=TEST_BOOTSTRAP_REPLICATES,
                    )
                )
    return tuple(out)


def extension_hypotheses() -> tuple[Hypothesis, ...]:
    """The 8 standalone I-isotonic / B-beta extension hypotheses."""
    out: list[Hypothesis] = []
    for procedure in STANDALONE_PROCEDURES:
        for direction in DIRECTIONS:
            for estimand in PRIMARY_FAMILY_ESTIMANDS:
                out.append(
                    Hypothesis(
                        hypothesis_id=f"extension::{procedure}::{direction}::{estimand}",
                        family="standalone-i-isotonic-b-beta-extension",
                        components={
                            "procedure": procedure,
                            "direction": direction,
                            "estimand": estimand,
                        },
                        unit="R4PanelMean delta (not a factorial effect)",
                        lower_tail=EXTENSION_LOWER_TAIL,
                        upper_tail=EXTENSION_UPPER_TAIL,
                        audit_lower_rank=EXTENSION_AUDIT_LOWER_RANK,
                        audit_upper_rank=EXTENSION_AUDIT_UPPER_RANK,
                        replicates=TEST_BOOTSTRAP_REPLICATES,
                    )
                )
    return tuple(out)


def direction_difference_hypotheses() -> tuple[Hypothesis, ...]:
    """The 6 formal between-direction contrast hypotheses."""
    out: list[Hypothesis] = []
    for effect in FACTORIAL_EFFECTS:
        for estimand in PRIMARY_FAMILY_ESTIMANDS:
            out.append(
                Hypothesis(
                    hypothesis_id=f"direction-difference::{estimand}::{effect}",
                    family="formal-between-direction-contrast",
                    components={"estimand": estimand, "effect": effect},
                    unit="R4PanelMean_CAT->OVR - R4PanelMean_OVR->CAT",
                    lower_tail=DIRECTION_LOWER_TAIL,
                    upper_tail=DIRECTION_UPPER_TAIL,
                    audit_lower_rank=DIRECTION_AUDIT_LOWER_RANK,
                    audit_upper_rank=DIRECTION_AUDIT_UPPER_RANK,
                    replicates=TEST_BOOTSTRAP_REPLICATES,
                )
            )
    return tuple(out)


def native_reference_hypotheses() -> tuple[Hypothesis, ...]:
    """The 12 native-reference hypotheses (2 target directions x 6 procedures)."""
    out: list[Hypothesis] = []
    for direction in DIRECTIONS:
        for procedure in ALL_PROCEDURES:
            out.append(
                Hypothesis(
                    hypothesis_id=f"native-reference::{direction}::{procedure}",
                    family="native-reference",
                    components={"direction": direction, "procedure": procedure},
                    unit="R4PanelMean Delta_native(d,F)",
                    lower_tail=NATIVE_LOWER_TAIL,
                    upper_tail=NATIVE_UPPER_TAIL,
                    audit_lower_rank=NATIVE_AUDIT_LOWER_RANK,
                    audit_upper_rank=NATIVE_AUDIT_UPPER_RANK,
                    replicates=TEST_BOOTSTRAP_REPLICATES,
                )
            )
    return tuple(out)


def native_reference_state(lower: float, upper: float) -> str:
    """Native-reference state with the exact-zero boundary left UNRESOLVED."""
    if upper < 0.0:
        return NATIVE_IMPROVEMENT_SUPPORTED
    if lower > 0.0:
        return NATIVE_DEGRADATION_SUPPORTED
    return NATIVE_ADEQUACY_UNRESOLVED


# ---------------------------------------------------------------------------
# Contrast rule
# ---------------------------------------------------------------------------


def contrast_per_replicate(
    left: Sequence[float], right: Sequence[float]
) -> tuple[float, ...]:
    """Direct replicate-level contrast; endpoint subtraction is forbidden."""
    if len(left) != len(right):
        raise BootstrapContractViolation("contrast requires equal replicate counts")
    return tuple(a - b for a, b in zip(left, right, strict=True))


# ---------------------------------------------------------------------------
# Bootstrap engines
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TestBootstrapResult:
    replicates: int
    protocol_id: str
    protocol_version: int
    samples: Mapping[str, tuple[float, ...]]
    draws: Mapping[tuple[str, int], TestDraw]

    def interval(
        self,
        population_id: str,
        *,
        lower_tail: Fraction,
        upper_tail: Fraction,
        point_estimate: float | None = None,
    ) -> Interval:
        samples = self.samples.get(population_id)
        if samples is None:
            raise DependencyUnavailable(
                family="test-bootstrap-population-sample",
                dependency=population_id,
                message=(
                    f"no TEST bootstrap sample for population {population_id!r}; "
                    "the population was not part of this bootstrap run"
                ),
            )
        return percentile_interval(
            samples,
            lower_tail=lower_tail,
            upper_tail=upper_tail,
            point_estimate=point_estimate,
        )


def run_test_bootstrap(
    *,
    rows_by_population: Mapping[str, Sequence[R4InferenceRow]],
    metadata_by_population: Mapping[str, PopulationMetadata],
    statistic: Callable[[str, TestDraw], float],
    replicates: int = TEST_BOOTSTRAP_REPLICATES,
    model_label: str | None = None,
) -> TestBootstrapResult:
    """Generic shared-draw TEST bootstrap engine."""
    if replicates <= 0:
        raise BootstrapContractViolation("replicates must be positive")
    population_ids = tuple(sorted(rows_by_population))
    samples: dict[str, list[float]] = {population: [] for population in population_ids}
    draws: dict[tuple[str, int], TestDraw] = {}
    for replicate_index in range(replicates):
        for population_id in population_ids:
            metadata = metadata_by_population[population_id]
            draw = build_test_draw(
                rows_by_population[population_id],
                metadata,
                replicate_index,
                model_label=model_label,
            )
            draws[(population_id, replicate_index)] = draw
            samples[population_id].append(float(statistic(population_id, draw)))
    return TestBootstrapResult(
        replicates=replicates,
        protocol_id=TEST_BOOTSTRAP_PROTOCOL_ID,
        protocol_version=TEST_BOOTSTRAP_PROTOCOL_VERSION,
        samples={population: tuple(values) for population, values in samples.items()},
        draws=draws,
    )


def _family_block(expected_size: int, members: Mapping[str, str]) -> dict[str, Any]:
    """Frozen-size family block; an unavailable member is INCOMPLETE, not dropped."""
    if len(members) != expected_size:
        raise BootstrapContractViolation(
            f"frozen family size {expected_size} != declared members {len(members)}"
        )
    complete = sum(1 for status in members.values() if status == STATUS_COMPLETE)
    return {
        "family_size": len(members),
        "complete_count": complete,
        "incomplete_count": len(members) - complete,
        "status": STATUS_COMPLETE if complete == len(members) else STATUS_INCOMPLETE,
        "members": dict(members),
    }


@dataclass(frozen=True)
class PanelBootstrapResult:
    replicates: int
    models: tuple[str, ...]
    populations: tuple[str, ...]
    directions: tuple[str, ...]
    procedures: tuple[str, ...]
    unit_values: Mapping[tuple[str, str, str, str], Mapping[str, tuple[float, ...]]]
    population_values: Mapping[tuple[str, str, str], Mapping[str, tuple[float, ...]]]
    panel_values: Mapping[tuple[str, str], Mapping[str, tuple[float, ...]]]
    primary_contrasts: Mapping[tuple[str, str, str], tuple[float, ...]]
    direction_differences: Mapping[tuple[str, str], tuple[float, ...]]
    extension_panel: Mapping[tuple[str, str, str], tuple[float, ...]]
    native_reference: Mapping[tuple[str, str], tuple[float, ...]]

    # -- dependency presence (never a KeyError) ------------------------------
    def has_primary_contrast(self, direction: str, estimand: str, effect: str) -> bool:
        return (direction, estimand, effect) in self.primary_contrasts

    def has_direction_difference(self, estimand: str, effect: str) -> bool:
        return (estimand, effect) in self.direction_differences

    def has_extension_panel(self, procedure: str, direction: str, estimand: str) -> bool:
        return (procedure, direction, estimand) in self.extension_panel

    def has_native_reference(self, direction: str, procedure: str) -> bool:
        return (direction, procedure) in self.native_reference

    # -- interval accessors --------------------------------------------------
    def primary_interval(
        self,
        direction: str,
        estimand: str,
        effect: str,
        *,
        point_estimate: float | None = None,
    ) -> Interval:
        key = (direction, estimand, effect)
        if key not in self.primary_contrasts:
            raise DependencyUnavailable(
                family="primary-prospective-confirmatory",
                dependency=f"{direction}/{estimand}/{effect}",
                message=(
                    "primary factorial contrast requires the four logistic-core "
                    f"procedures; unavailable member {direction}/{estimand}/{effect}"
                ),
            )
        return percentile_interval(
            self.primary_contrasts[key],
            lower_tail=PRIMARY_LOWER_TAIL,
            upper_tail=PRIMARY_UPPER_TAIL,
            point_estimate=point_estimate,
        )

    def extension_interval(
        self,
        procedure: str,
        direction: str,
        estimand: str,
        *,
        point_estimate: float | None = None,
    ) -> Interval:
        key = (procedure, direction, estimand)
        if key not in self.extension_panel:
            raise DependencyUnavailable(
                family="standalone-i-isotonic-b-beta-extension",
                dependency=f"{procedure}/{direction}/{estimand}",
                message=(
                    f"standalone extension {procedure!r} is unavailable for "
                    f"{direction}/{estimand}"
                ),
            )
        return percentile_interval(
            self.extension_panel[key],
            lower_tail=EXTENSION_LOWER_TAIL,
            upper_tail=EXTENSION_UPPER_TAIL,
            point_estimate=point_estimate,
        )

    def direction_interval(
        self, estimand: str, effect: str, *, point_estimate: float | None = None
    ) -> Interval:
        key = (estimand, effect)
        if key not in self.direction_differences:
            raise DependencyUnavailable(
                family="formal-between-direction-contrast",
                dependency=f"{estimand}/{effect}",
                message=(
                    "between-direction contrast requires both target directions; "
                    f"unavailable member {estimand}/{effect}"
                ),
            )
        return percentile_interval(
            self.direction_differences[key],
            lower_tail=DIRECTION_LOWER_TAIL,
            upper_tail=DIRECTION_UPPER_TAIL,
            point_estimate=point_estimate,
        )

    def native_interval(
        self, direction: str, procedure: str, *, point_estimate: float | None = None
    ) -> Interval:
        key = (direction, procedure)
        if key not in self.native_reference:
            raise DependencyUnavailable(
                family="native-reference",
                dependency=f"{direction}/{procedure}",
                message=(
                    f"native-reference hypothesis requires procedure {procedure!r} "
                    f"for direction {direction}"
                ),
            )
        return percentile_interval(
            self.native_reference[key],
            lower_tail=NATIVE_LOWER_TAIL,
            upper_tail=NATIVE_UPPER_TAIL,
            point_estimate=point_estimate,
        )

    # -- per-family member status -------------------------------------------
    def family_status(self) -> dict[str, Any]:
        """Availability of every frozen family member.

        Family sizes are the frozen constants (12 / 8 / 6 / 12); an unavailable
        member is reported as :data:`STATUS_INCOMPLETE` and is never dropped, so
        the multiplicity family never silently shrinks.
        """
        primary_members = {
            f"primary::{estimand}::{direction}::{effect}": (
                STATUS_COMPLETE
                if self.has_primary_contrast(direction, estimand, effect)
                else STATUS_INCOMPLETE
            )
            for estimand in PRIMARY_FAMILY_ESTIMANDS
            for direction in DIRECTIONS
            for effect in FACTORIAL_EFFECTS
        }
        direction_members = {
            f"direction-difference::{estimand}::{effect}": (
                STATUS_COMPLETE
                if self.has_direction_difference(estimand, effect)
                else STATUS_INCOMPLETE
            )
            for estimand in PRIMARY_FAMILY_ESTIMANDS
            for effect in FACTORIAL_EFFECTS
        }
        extension_members = {
            f"extension::{procedure}::{direction}::{estimand}": (
                STATUS_COMPLETE
                if self.has_extension_panel(procedure, direction, estimand)
                else STATUS_INCOMPLETE
            )
            for procedure in STANDALONE_PROCEDURES
            for direction in DIRECTIONS
            for estimand in PRIMARY_FAMILY_ESTIMANDS
        }
        native_members = {
            f"native-reference::{direction}::{procedure}": (
                STATUS_COMPLETE
                if self.has_native_reference(direction, procedure)
                else STATUS_INCOMPLETE
            )
            for direction in DIRECTIONS
            for procedure in ALL_PROCEDURES
        }
        return {
            "primary": _family_block(PRIMARY_FAMILY_SIZE, primary_members),
            "secondary_extension": _family_block(
                EXTENSION_FAMILY_SIZE, extension_members
            ),
            "secondary_direction_difference": _family_block(
                DIRECTION_DIFFERENCE_FAMILY_SIZE, direction_members
            ),
            "secondary_native_reference": _family_block(
                NATIVE_REFERENCE_FAMILY_SIZE, native_members
            ),
        }


UnitEstimator = Callable[
    [str, str, str, str, TestDraw], Mapping[str, float]
]


def run_panel_test_bootstrap(
    *,
    rows_by_population: Mapping[str, Sequence[R4InferenceRow]],
    metadata_by_population: Mapping[str, PopulationMetadata],
    unit_estimator: UnitEstimator,
    replicates: int = TEST_BOOTSTRAP_REPLICATES,
    models: Sequence[str] = PRIMARY_MODELS,
    populations: Sequence[str] = PRIMARY_POPULATIONS,
    directions: Sequence[str] = DIRECTIONS,
    procedures: Sequence[str] = ALL_PROCEDURES,
) -> PanelBootstrapResult:
    """Panel-level shared-draw TEST bootstrap.

    One draw per population per replicate is applied to every model, direction
    and procedure; population means use equal model weights and the panel mean
    uses equal population weights.
    """
    if replicates <= 0:
        raise BootstrapContractViolation("replicates must be positive")
    unit_values: dict[tuple[str, str, str, str], dict[str, list[float]]] = {}
    population_values: dict[tuple[str, str, str], dict[str, list[float]]] = {}
    panel_values: dict[tuple[str, str], dict[str, list[float]]] = {}

    for replicate_index in range(replicates):
        draws = {
            population: build_test_draw(
                rows_by_population[population],
                metadata_by_population[population],
                replicate_index,
            )
            for population in populations
        }
        per_replicate_units: dict[tuple[str, str, str, str], Mapping[str, float]] = {}
        for population in populations:
            draw = draws[population]
            for model in models:
                for direction in directions:
                    for procedure in procedures:
                        values = unit_estimator(
                            population, model, direction, procedure, draw
                        )
                        key = (model, population, direction, procedure)
                        per_replicate_units[key] = values
                        bucket = unit_values.setdefault(key, {})
                        for estimand, value in values.items():
                            bucket.setdefault(estimand, []).append(float(value))
            for direction in directions:
                for procedure in procedures:
                    estimands = sorted(
                        {
                            estimand
                            for model in models
                            for estimand in per_replicate_units[
                                (model, population, direction, procedure)
                            ]
                        }
                    )
                    for estimand in estimands:
                        per_model = {
                            model: per_replicate_units[
                                (model, population, direction, procedure)
                            ][estimand]
                            for model in models
                        }
                        value = population_mean(per_model, models)
                        key = (population, direction, procedure)
                        population_values.setdefault(key, {}).setdefault(estimand, []).append(value)

        for direction in directions:
            for procedure in procedures:
                estimands = sorted(
                    {
                        estimand
                        for population in populations
                        for estimand in population_values[
                            (population, direction, procedure)
                        ]
                    }
                )
                for estimand in estimands:
                    per_population = {
                        population: population_values[(population, direction, procedure)][
                            estimand
                        ][-1]
                        for population in populations
                    }
                    value = panel_mean(per_population, populations)
                    panel_values.setdefault((direction, procedure), {}).setdefault(
                        estimand, []
                    ).append(value)

    primary_contrasts: dict[tuple[str, str, str], tuple[float, ...]] = {}
    direction_differences: dict[tuple[str, str], tuple[float, ...]] = {}
    extension_panel: dict[tuple[str, str, str], tuple[float, ...]] = {}
    native_reference: dict[tuple[str, str], tuple[float, ...]] = {}

    # Dependency-aware assembly.  A missing member is simply absent from the
    # corresponding mapping (reported as INCOMPLETE by ``family_status``); the
    # primary logistic-core family is never blocked by an unavailable standalone
    # extension, and an unavailable core procedure never blocks the extensions.
    for direction in directions:
        for estimand in PRIMARY_FAMILY_ESTIMANDS:
            core: dict[str, tuple[float, ...]] = {}
            for procedure in LOGISTIC_CORE_PROCEDURES:
                series = panel_values.get((direction, procedure), {}).get(estimand)
                if series is None:
                    break
                core[procedure] = series
            if len(core) != len(LOGISTIC_CORE_PROCEDURES):
                continue
            for effect in FACTORIAL_EFFECTS:
                primary_contrasts[(direction, estimand, effect)] = tuple(
                    factorial_contrasts(
                        {procedure: core[procedure][index] for procedure in core}
                    )[effect]
                    for index in range(replicates)
                )
    for estimand in PRIMARY_FAMILY_ESTIMANDS:
        for effect in FACTORIAL_EFFECTS:
            cat = primary_contrasts.get(("CAT->OVR", estimand, effect))
            ovr = primary_contrasts.get(("OVR->CAT", estimand, effect))
            if cat is None or ovr is None:
                continue
            direction_differences[(estimand, effect)] = contrast_per_replicate(cat, ovr)
    for procedure in STANDALONE_PROCEDURES:
        for direction in directions:
            for estimand in PRIMARY_FAMILY_ESTIMANDS:
                series = panel_values.get((direction, procedure), {}).get(estimand)
                if series is None:
                    continue
                extension_panel[(procedure, direction, estimand)] = tuple(series)
    for direction in directions:
        for procedure in procedures:
            series = panel_values.get((direction, procedure), {}).get("Delta_native")
            if series is None:
                continue
            native_reference[(direction, procedure)] = tuple(series)

    return PanelBootstrapResult(
        replicates=replicates,
        models=tuple(models),
        populations=tuple(populations),
        directions=tuple(directions),
        procedures=tuple(procedures),
        unit_values={
            key: {estimand: tuple(values) for estimand, values in bucket.items()}
            for key, bucket in unit_values.items()
        },
        population_values={
            key: {estimand: tuple(values) for estimand, values in bucket.items()}
            for key, bucket in population_values.items()
        },
        panel_values={
            key: {estimand: tuple(values) for estimand, values in bucket.items()}
            for key, bucket in panel_values.items()
        },
        primary_contrasts=primary_contrasts,
        direction_differences=direction_differences,
        extension_panel=extension_panel,
        native_reference=native_reference,
    )


# ---------------------------------------------------------------------------
# Coverage, failure records and TRAIN-refit blocks
# ---------------------------------------------------------------------------

AVAILABLE = "AVAILABLE"
INELIGIBLE = "INELIGIBLE"
FAILED = "FAILED"

COVERAGE_STATUSES: tuple[str, ...] = (AVAILABLE, INELIGIBLE, FAILED)


@dataclass(frozen=True)
class FailureRecord:
    replicate: int
    procedure: str
    model: str
    population: str
    measurement_dependency: str
    direction_dependency: str | None
    error_code: str
    exception_type: str
    message: str

    def payload(self) -> dict[str, Any]:
        return {
            "replicate": self.replicate,
            "procedure": self.procedure,
            "model": self.model,
            "population": self.population,
            "measurement_dependency": self.measurement_dependency,
            "direction_dependency": self.direction_dependency,
            "error_code": self.error_code,
            "exception_type": self.exception_type,
            "message": self.message,
        }


class CoverageMatrix:
    """Full-fit eligibility coverage matrix: model x population x procedure x measurement."""

    def __init__(self) -> None:
        self._status: dict[tuple[str, str, str, str], str] = {}

    def set(
        self,
        model: str,
        population: str,
        procedure: str,
        measurement: str,
        status: str,
    ) -> None:
        if status not in COVERAGE_STATUSES:
            raise BootstrapContractViolation(f"unknown coverage status {status!r}")
        self._status[(model, population, procedure, measurement)] = status

    def status(
        self, model: str, population: str, procedure: str, measurement: str
    ) -> str:
        return self._status.get((model, population, procedure, measurement), INELIGIBLE)

    def is_available(
        self, model: str, population: str, procedure: str, measurement: str
    ) -> bool:
        return self.status(model, population, procedure, measurement) == AVAILABLE

    def matrix(self) -> dict[str, str]:
        return {",".join(key): value for key, value in sorted(self._status.items())}

    def primary_hypothesis_status(self, direction: str, estimand: str) -> str:
        """The primary factorial hypothesis depends on the four logistic-core procedures."""
        measurement = target_measurement(direction)
        for model in PRIMARY_MODELS:
            for population in PRIMARY_POPULATIONS:
                for procedure in LOGISTIC_CORE_PROCEDURES:
                    if not self.is_available(model, population, procedure, measurement):
                        return STATUS_INCOMPLETE
        return STATUS_COMPLETE

    def extension_hypothesis_status(
        self, procedure: str, direction: str, estimand: str
    ) -> str:
        """The I/B extension hypothesis needs the procedure in all 12 primary cells."""
        measurement = target_measurement(direction)
        for model in PRIMARY_MODELS:
            for population in PRIMARY_POPULATIONS:
                if not self.is_available(model, population, procedure, measurement):
                    return STATUS_INCOMPLETE
        return STATUS_COMPLETE

    def incomplete_cells(self) -> list[tuple[str, str, str, str]]:
        return sorted(
            key for key in self._status if self._status[key] != AVAILABLE
        )


@dataclass(frozen=True)
class RefitBlockResult:
    procedure: str
    model: str
    population: str
    measurement_dependency: str
    planned_replicates: int
    successful_replicates: int
    failed_replicates: int
    status: str
    failures: tuple[FailureRecord, ...]
    interval: Interval | None
    samples: tuple[float, ...]

    def payload(self) -> dict[str, Any]:
        return {
            "procedure": self.procedure,
            "model": self.model,
            "population": self.population,
            "measurement_dependency": self.measurement_dependency,
            "planned_replicates": self.planned_replicates,
            "successful_replicates": self.successful_replicates,
            "failed_replicates": self.failed_replicates,
            "status": self.status,
            "failures": [failure.payload() for failure in self.failures],
            "interval": None if self.interval is None else self.interval.payload(),
        }


def run_train_refit_block(
    *,
    replicate_indices: Sequence[int],
    procedure: str,
    model: str,
    population: str,
    measurement_dependency: str,
    direction_dependency: str | None,
    fit_and_evaluate: Callable[[int], float],
    lower_tail: Fraction = REFIT_LOWER_LEVEL,
    upper_tail: Fraction = REFIT_UPPER_LEVEL,
) -> RefitBlockResult:
    """Run one TRAIN-refit block with fail-closed dependency handling."""
    samples: list[float] = []
    failures: list[FailureRecord] = []
    for replicate_index in replicate_indices:
        try:
            samples.append(float(fit_and_evaluate(replicate_index)))
        except Exception as exc:  # failures must be recorded, not hidden
            failures.append(
                FailureRecord(
                    replicate=int(replicate_index),
                    procedure=procedure,
                    model=model,
                    population=population,
                    measurement_dependency=measurement_dependency,
                    direction_dependency=direction_dependency,
                    error_code="TRAIN_REFIT_REPLICATE_FAILED",
                    exception_type=type(exc).__name__,
                    message=str(exc),
                )
            )
    planned = len(replicate_indices)
    successful = len(samples)
    failed = len(failures)
    status = STATUS_INCOMPLETE if failed > 0 else STATUS_COMPLETE
    interval = None
    if status == STATUS_COMPLETE:
        interval = percentile_interval(
            samples,
            lower_tail=lower_tail,
            upper_tail=upper_tail,
            status=STATUS_COMPLETE,
        )
    return RefitBlockResult(
        procedure=procedure,
        model=model,
        population=population,
        measurement_dependency=measurement_dependency,
        planned_replicates=planned,
        successful_replicates=successful,
        failed_replicates=failed,
        status=status,
        failures=tuple(failures),
        interval=interval,
        samples=tuple(samples),
    )


# ---------------------------------------------------------------------------
# Measurement completeness
# ---------------------------------------------------------------------------


def validate_measurement_completeness(
    *,
    expected: Sequence[FrozenItemReference],
    provided: Sequence[R4InferenceRow],
    population_id: str,
    model_id: str,
) -> None:
    """Fail-closed paired fixed-event measurement completeness validator."""
    expected_by_id = {reference.item_id: reference for reference in expected}
    if len(expected_by_id) != len(expected):
        raise MeasurementIncompleteness(
            "DUPLICATE_EXPECTED_ITEM",
            f"expected item ids are not unique for {model_id}/{population_id}",
        )
    seen: set[str] = set()
    for row in provided:
        if row.population_id != population_id:
            raise MeasurementIncompleteness(
                "POPULATION_MISMATCH",
                f"row {row.item_id} declares population {row.population_id!r}",
            )
        if row.item_id in seen:
            raise MeasurementIncompleteness(
                "DUPLICATE_PROVIDED_ITEM", f"duplicate row for item {row.item_id}"
            )
        seen.add(row.item_id)
        reference = expected_by_id.get(row.item_id)
        if reference is None:
            raise MeasurementIncompleteness(
                "EXTRA_ROW", f"row {row.item_id} is not a frozen selected item"
            )
        if row.label != reference.label:
            raise MeasurementIncompleteness(
                "MISMATCHED_LABEL",
                f"item {row.item_id} label {row.label} != frozen {reference.label}",
            )
        if row.anchor_index is None:
            raise MeasurementIncompleteness(
                "MISSING_ANCHOR", f"item {row.item_id} has no frozen anchor index"
            )
        if row.anchor_index != reference.anchor_index:
            raise MeasurementIncompleteness(
                "MISMATCHED_ANCHOR",
                f"item {row.item_id} anchor {row.anchor_index} != frozen "
                f"{reference.anchor_index}",
            )
        if row.cat_score is None:
            raise MeasurementIncompleteness("MISSING_CAT", f"item {row.item_id} has no CAT score")
        if row.ovr_score is None:
            raise MeasurementIncompleteness("MISSING_OVR", f"item {row.item_id} has no OVR score")
    missing = sorted(set(expected_by_id) - seen)
    if missing:
        raise MeasurementIncompleteness(
            "MISSING_ROW", f"missing frozen rows: {missing[:8]}"
        )


# ---------------------------------------------------------------------------
# N912 robustness
# ---------------------------------------------------------------------------


def validate_n912_pairing(
    *,
    train_456: Sequence[FrozenItemReference],
    train_912: Sequence[FrozenItemReference],
    test_456: Sequence[FrozenItemReference],
    test_912: Sequence[FrozenItemReference],
) -> dict[str, Any]:
    """Validate TRAIN_456 subset TRAIN_912 and identical TEST identity."""
    ids_456 = {reference.item_id for reference in train_456}
    ids_912 = {reference.item_id for reference in train_912}
    missing = sorted(ids_456 - ids_912)
    if missing:
        raise N912ContractViolation(f"TRAIN_456 not a subset of TRAIN_912: {missing[:8]}")
    test_ids_456 = [reference.item_id for reference in test_456]
    test_ids_912 = [reference.item_id for reference in test_912]
    if test_ids_456 != test_ids_912:
        raise N912ContractViolation("TEST identity differs between the 456 and 912 manifests")
    return {
        "train_456_count": len(ids_456),
        "train_912_count": len(ids_912),
        "extension_count": len(ids_912 - ids_456),
        "test_count": len(test_ids_456),
        "train_456_subset_of_train_912": True,
        "test_identity_identical": True,
    }


def n912_minus_n456(
    samples_912: Sequence[float], samples_456: Sequence[float]
) -> tuple[float, ...]:
    """Paired N912 - N456 difference within the same shared TEST replicate."""
    return contrast_per_replicate(samples_912, samples_456)


N912_ROBUSTNESS_ROLE = "SECONDARY_ROBUSTNESS"
N912_CANNOT_RESCUE_PRIMARY = True


# ---------------------------------------------------------------------------
# Reliability diagnostics (descriptive only)
# ---------------------------------------------------------------------------

RELIABILITY_BIN_COUNT = 10


def equal_width_reliability_10_bins(
    predictions: Sequence[float], labels: Sequence[int]
) -> list[dict[str, Any]]:
    """Descriptive equal-width 10-bin reliability table (no ECE / ACE)."""
    if len(predictions) != len(labels):
        raise BootstrapContractViolation("predictions and labels must have equal length")
    bins: list[list[tuple[float, int]]] = [[] for _ in range(RELIABILITY_BIN_COUNT)]
    for prediction, label in zip(predictions, labels, strict=True):
        value = float(prediction)
        if not 0.0 <= value <= 1.0:
            raise BootstrapContractViolation("prediction must lie in [0, 1]")
        index = min(int(value * RELIABILITY_BIN_COUNT), RELIABILITY_BIN_COUNT - 1)
        bins[index].append((value, int(label)))
    table: list[dict[str, Any]] = []
    for index, bucket in enumerate(bins):
        lower = index / RELIABILITY_BIN_COUNT
        upper = (index + 1) / RELIABILITY_BIN_COUNT
        if bucket:
            mean_prediction: float | None = math.fsum(p for p, _ in bucket) / len(bucket)
            mean_label: float | None = math.fsum(y for _, y in bucket) / len(bucket)
        else:
            mean_prediction = None
            mean_label = None
        table.append(
            {
                "bin_index": index,
                "lower": lower,
                "upper": upper,
                "count": len(bucket),
                "mean_prediction": mean_prediction,
                "mean_label": mean_label,
            }
        )
    return table


# ---------------------------------------------------------------------------
# HellaSwag split_type subgroup diagnostic
# ---------------------------------------------------------------------------

SPLIT_TYPE_DIAGNOSTIC_ROLE = "DESCRIPTIVE_SECONDARY"


def split_type_diagnostic(
    rows: Sequence[R4InferenceRow],
    *,
    split_type_by_item: Mapping[str, str],
) -> dict[str, Any]:
    """Descriptive indomain / zeroshot subgroup diagnostic (never a population)."""
    out: dict[str, dict[str, Any]] = {}
    for value in SPLIT_TYPE_VALUES:
        subset = [
            row for row in rows if split_type_by_item.get(row.item_id) == value
        ]
        out[value] = {
            "count": len(subset),
            "mean_cat_score": (
                row_weighted_mean([row.cat_score for row in subset]) if subset else None
            ),
            "mean_ovr_score": (
                row_weighted_mean([row.ovr_score for row in subset]) if subset else None
            ),
        }
    return {
        "role": SPLIT_TYPE_DIAGNOSTIC_ROLE,
        "is_independent_population": False,
        "primary_population_count": len(PRIMARY_POPULATIONS),
        "subgroups": out,
    }


# ---------------------------------------------------------------------------
# Determinism helpers and analysis artifact skeleton
# ---------------------------------------------------------------------------


def state_fingerprint(payload: Mapping[str, Any]) -> str:
    return fingerprint(dict(payload))


def canonical_state_json(payload: Mapping[str, Any]) -> str:
    return canonical_json(dict(payload))


def _artifact_key(key: Any) -> str:
    """Canonical string form of a mapping key used inside an analysis artifact.

    Composite keys (for example ``(model, population, direction, procedure)``)
    are joined with ``"|"`` so that the artifact stays JSON- and
    fingerprint-compatible without dropping the composite identity.
    """
    if isinstance(key, str):
        return key
    if isinstance(key, tuple):
        return "|".join(_artifact_key(part) for part in key)
    return str(key)


def _artifact_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {_artifact_key(key): _artifact_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_artifact_value(item) for item in value]
    return value


def build_analysis_artifact_skeleton(
    *,
    population_fingerprints: Mapping[str, str],
    calibration_fingerprints: Mapping[str, str],
    model_identities: Mapping[str, str],
    measurement_provenance: Mapping[str, Any],
    full_fit_coverage: Mapping[str, str],
    unit_estimates: Mapping[str, Any],
    panel_estimates: Mapping[str, Any],
    test_bootstrap_provenance: Mapping[str, Any],
    train_refit_provenance: Mapping[str, Any],
    multiplicity_families: Mapping[str, Any],
    n912_robustness: Mapping[str, Any],
    secondary_diagnostics: Mapping[str, Any],
    incompleteness: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Schema skeleton for a future formal R4 analysis artifact.

    The skeleton never loads or produces real study outcomes. A future caller
    supplies the values after formal execution authorization.
    """
    payload: dict[str, Any] = {
        "artifact_type": "r4-inference-analysis",
        "artifact_version": 1,
        "fingerprint_version": FINGERPRINT_VERSION,
        "freeze_fingerprint": R4_INFERENCE_FREEZE_FINGERPRINT,
        "candidate_fingerprint": CANDIDATE_FINGERPRINT,
        "population_fingerprints": _artifact_value(population_fingerprints),
        "calibration_fingerprints": _artifact_value(calibration_fingerprints),
        "model_identities": _artifact_value(model_identities),
        "measurement_provenance_references": _artifact_value(measurement_provenance),
        "full_fit_coverage": _artifact_value(full_fit_coverage),
        "unit_estimates": _artifact_value(unit_estimates),
        "panel_estimates": _artifact_value(panel_estimates),
        "test_bootstrap_provenance": _artifact_value(test_bootstrap_provenance),
        "train_refit_provenance": _artifact_value(train_refit_provenance),
        "multiplicity_families": _artifact_value(multiplicity_families),
        "n912_robustness": _artifact_value(n912_robustness),
        "secondary_diagnostics": _artifact_value(secondary_diagnostics),
        "incompleteness": [_artifact_value(item) for item in incompleteness],
    }
    payload["artifact_fingerprint"] = fingerprint(payload)
    return payload
