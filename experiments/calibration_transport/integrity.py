"""Paired experiment-integrity harness for calibration transport research (R1).

This module implements the research-only structural layer described by
``docs/research/calibration-transport-research-spec-v1.md``. It is deliberately
*not* a transport analysis: it fits no calibrator, computes no Brier or LogLoss
transport metric, and knows nothing about CAT or OVR. Its single job is to make
a paired frozen-decision study mechanically auditable before any measurement
data exists.

The harness ships two research artifacts:

``PairedFixedDecisionPlan``
    A pre-measurement declaration of *what* a paired frozen-decision study
    compares: the model, the population, the ground-truth semantics reference,
    the two declared measurement identities, the anchor-selection and
    split-protocol identities, and every planned item with its frozen anchor,
    ground-truth value, split membership, and declared correctness label.

``PairedFixedDecisionDataset``
    The explicit A/B outcomes for one exact plan. Every planned item must have
    exactly one ``MeasurementOutcome`` per side. A measurement that produced no
    score is recorded as ``MISSING`` or ``INELIGIBLE`` -- never dropped.

The frozen-decisions research semantics (``fixed-decision-correctness`` and
``fixed-decision-semantic-probability``) are research-layer identifiers only.
They do not reuse the frozen Phase 4C ``winner_correctness`` target or the
``uncalibrated-selected-probability`` input score, and this module must never be
imported by the production ``probvenance`` package.

Trust boundaries this module preserves:

- It structurally separates the frozen plan from later measurement outcomes and
  fingerprints the declared plan. It does **not** attest how the caller
  generated the plan, and it cannot prove the caller never peeked at A/B
  outcomes before constructing the plan.
- It enforces exact item-ID disjointness across splits. It makes no statistical
  independence claim beyond that.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypeAlias

from probvenance.fingerprint import JSONValue, fingerprint

RESEARCH_SPEC_ID = "calibration-transport-research-spec"
RESEARCH_SPEC_VERSION = 1

FIXED_DECISION_TARGET_ID = "fixed-decision-correctness"
FIXED_DECISION_TARGET_VERSION = 1

FIXED_DECISION_INPUT_SCORE_ID = "fixed-decision-semantic-probability"
FIXED_DECISION_INPUT_SCORE_VERSION = 1

PAIRED_FIXED_DECISION_PLAN_FINGERPRINT_VERSION = 1
PAIRED_FIXED_DECISION_DATASET_FINGERPRINT_VERSION = 1

# A research anchor / ground-truth semantic value is a small, JSON-compatible
# scalar. ``bool`` is listed for the boolean anchor case; ``int`` / ``float`` /
# ``str`` cover choice candidates and numeric semantic values. ``None``,
# collections, bytes, and arbitrary objects are rejected.
ResearchSemanticValue: TypeAlias = bool | int | float | str


class ResearchIntegrityError(ValueError):
    """Raised when research experiment-integrity input is structurally invalid.

    This is a research-local error type. Production error taxonomies are not
    reused or polluted by the research harness; every supported validation
    failure converges here instead of leaking ``TypeError``, ``KeyError``, or
    similar.
    """


class Split(StrEnum):
    """The three research splits. Membership is declared, never auto-assigned."""

    TRAIN = "train"
    AUDIT = "audit"
    TEST = "test"


class MeasurementStatus(StrEnum):
    """The explicit outcome status of one measurement for one planned item."""

    SCORED = "scored"
    MISSING = "missing"
    INELIGIBLE = "ineligible"


def _require_non_empty_str(value: object, *, field_name: str) -> str:
    if isinstance(value, bool) or not isinstance(value, str):
        raise ResearchIntegrityError(f"{field_name} must be a str, got {type(value).__name__}")
    if not value.strip():
        raise ResearchIntegrityError(f"{field_name} must be a non-empty str")
    return value


def _require_declared_version(value: object, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ResearchIntegrityError(f"{field_name} must be an int, got {type(value).__name__}")
    if value < 1:
        raise ResearchIntegrityError(f"{field_name} must be >= 1, got {value}")
    return value


def _require_semantic_value(value: object, *, field_name: str) -> ResearchSemanticValue:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ResearchIntegrityError(f"{field_name} must be finite, got {value!r}")
        return value
    if isinstance(value, str):
        return value
    raise ResearchIntegrityError(
        f"{field_name} must be a bool, int, finite float, or str; got {type(value).__name__}"
    )


@dataclass(frozen=True, slots=True)
class MeasurementProtocolIdentity:
    """A declared probability-measurement identity.

    The harness only provides the container. R1 deliberately does not decide
    what the final CAT or OVR measurement identity is.
    """

    measurement_id: str
    measurement_version: int

    def __post_init__(self) -> None:
        _require_non_empty_str(self.measurement_id, field_name="measurement_id")
        _require_declared_version(self.measurement_version, field_name="measurement_version")


@dataclass(frozen=True, slots=True)
class PlannedFixedDecisionItem:
    """One planned item with its pre-frozen anchor, truth, split, and label.

    ``anchor_correct`` is a *declared* label. The harness records it but does
    not reinvent it: correctness meaning belongs to the declared ground-truth
    semantics, so R1 does not recompute ``anchor_value == ground_truth_value``.
    """

    item_id: str
    split: Split
    anchor_value: ResearchSemanticValue
    ground_truth_value: ResearchSemanticValue
    anchor_correct: bool

    def __post_init__(self) -> None:
        _require_non_empty_str(self.item_id, field_name="item_id")
        if not isinstance(self.split, Split):
            raise ResearchIntegrityError(
                f"split must be a Split member, got {type(self.split).__name__}"
            )
        _require_semantic_value(self.anchor_value, field_name="anchor_value")
        _require_semantic_value(self.ground_truth_value, field_name="ground_truth_value")
        if not isinstance(self.anchor_correct, bool):
            raise ResearchIntegrityError(
                f"anchor_correct must be a real bool, got {type(self.anchor_correct).__name__}"
            )


@dataclass(frozen=True, slots=True)
class PairedFixedDecisionPlan:
    """A pre-measurement structural declaration of a paired study.

    The plan is intentionally expressed before any measurement outcome exists.
    It does not accept A/B scores or winners, so it cannot condition anchor
    selection on them at the structural level.
    """

    model_id: str
    model_revision: str | None
    population_id: str
    population_version: int
    ground_truth_semantics_fingerprint: str
    ground_truth_semantics_fingerprint_version: int
    measurement_a: MeasurementProtocolIdentity
    measurement_b: MeasurementProtocolIdentity
    anchor_selection_id: str
    anchor_selection_version: int
    split_protocol_id: str
    split_protocol_version: int
    items: tuple[PlannedFixedDecisionItem, ...]

    def __post_init__(self) -> None:
        _require_non_empty_str(self.model_id, field_name="model_id")
        if self.model_revision is not None:
            # ``None`` means "unknown / not declared"; it is not a wildcard.
            _require_non_empty_str(self.model_revision, field_name="model_revision")
        _require_non_empty_str(self.population_id, field_name="population_id")
        _require_declared_version(self.population_version, field_name="population_version")
        _require_non_empty_str(
            self.ground_truth_semantics_fingerprint,
            field_name="ground_truth_semantics_fingerprint",
        )
        _require_declared_version(
            self.ground_truth_semantics_fingerprint_version,
            field_name="ground_truth_semantics_fingerprint_version",
        )
        if not isinstance(self.measurement_a, MeasurementProtocolIdentity):
            raise ResearchIntegrityError("measurement_a must be a MeasurementProtocolIdentity")
        if not isinstance(self.measurement_b, MeasurementProtocolIdentity):
            raise ResearchIntegrityError("measurement_b must be a MeasurementProtocolIdentity")
        if self.measurement_a == self.measurement_b:
            raise ResearchIntegrityError(
                "measurement_a and measurement_b must be distinct declared measurement identities"
            )
        _require_non_empty_str(self.anchor_selection_id, field_name="anchor_selection_id")
        _require_declared_version(
            self.anchor_selection_version, field_name="anchor_selection_version"
        )
        _require_non_empty_str(self.split_protocol_id, field_name="split_protocol_id")
        _require_declared_version(self.split_protocol_version, field_name="split_protocol_version")

        if not isinstance(self.items, tuple):
            raise ResearchIntegrityError(
                "items must be a tuple of PlannedFixedDecisionItem, "
                f"got {type(self.items).__name__}"
            )
        if not self.items:
            raise ResearchIntegrityError("items must contain at least one planned item")

        seen: set[str] = set()
        train_count = 0
        test_count = 0
        for item in self.items:
            if not isinstance(item, PlannedFixedDecisionItem):
                raise ResearchIntegrityError(
                    f"every item must be a PlannedFixedDecisionItem, got {type(item).__name__}"
                )
            if item.item_id in seen:
                raise ResearchIntegrityError(
                    f"item_id {item.item_id!r} is duplicated; item_id must be globally unique "
                    "across the whole plan"
                )
            seen.add(item.item_id)
            if item.split is Split.TRAIN:
                train_count += 1
            elif item.split is Split.TEST:
                test_count += 1
        if train_count == 0:
            raise ResearchIntegrityError("plan must contain at least one TRAIN item")
        if test_count == 0:
            raise ResearchIntegrityError("plan must contain at least one TEST item")

    def _sorted_items(self) -> tuple[PlannedFixedDecisionItem, ...]:
        return tuple(sorted(self.items, key=lambda item: item.item_id))

    def canonical_payload(self) -> dict[str, JSONValue]:
        return {
            "artifact": "paired-fixed-decision-plan",
            "fingerprint_version": PAIRED_FIXED_DECISION_PLAN_FINGERPRINT_VERSION,
            "research_spec_id": RESEARCH_SPEC_ID,
            "research_spec_version": RESEARCH_SPEC_VERSION,
            "target_id": FIXED_DECISION_TARGET_ID,
            "target_version": FIXED_DECISION_TARGET_VERSION,
            "input_score_id": FIXED_DECISION_INPUT_SCORE_ID,
            "input_score_version": FIXED_DECISION_INPUT_SCORE_VERSION,
            "model_id": self.model_id,
            "model_revision": self.model_revision,
            "population_id": self.population_id,
            "population_version": self.population_version,
            "ground_truth_semantics_fingerprint": self.ground_truth_semantics_fingerprint,
            "ground_truth_semantics_fingerprint_version": (
                self.ground_truth_semantics_fingerprint_version
            ),
            "measurement_a": _identity_payload(self.measurement_a),
            "measurement_b": _identity_payload(self.measurement_b),
            "anchor_selection_id": self.anchor_selection_id,
            "anchor_selection_version": self.anchor_selection_version,
            "split_protocol_id": self.split_protocol_id,
            "split_protocol_version": self.split_protocol_version,
            "items": [_planned_item_payload(item) for item in self._sorted_items()],
        }

    @property
    def fingerprint(self) -> str:
        """Deterministic SHA-256 over the canonical plan payload."""
        return fingerprint(self.canonical_payload())


@dataclass(frozen=True, slots=True)
class MeasurementOutcome:
    """One measurement's explicit outcome for one planned item.

    ``anchor_score`` is *this* measurement's score for the already-frozen anchor
    ``D_i``. It is never the measurement's own winner score. ``winner_value`` is
    diagnostic only and never affects row inclusion.
    """

    item_id: str
    status: MeasurementStatus
    anchor_score: float | None
    winner_value: ResearchSemanticValue | None
    source_record_id: str
    reason: str | None

    def __post_init__(self) -> None:
        _require_non_empty_str(self.item_id, field_name="item_id")
        if not isinstance(self.status, MeasurementStatus):
            raise ResearchIntegrityError(
                f"status must be a MeasurementStatus, got {type(self.status).__name__}"
            )
        _require_non_empty_str(self.source_record_id, field_name="source_record_id")
        if self.winner_value is not None:
            _require_semantic_value(self.winner_value, field_name="winner_value")

        if self.status is MeasurementStatus.SCORED:
            if isinstance(self.anchor_score, bool) or not isinstance(self.anchor_score, float):
                raise ResearchIntegrityError(
                    "SCORED outcome requires a float anchor_score, "
                    f"got {type(self.anchor_score).__name__}"
                )
            if not math.isfinite(self.anchor_score):
                raise ResearchIntegrityError("anchor_score must be finite; no clipping is applied")
            if not 0.0 <= self.anchor_score <= 1.0:
                raise ResearchIntegrityError(
                    f"anchor_score must be within [0, 1], got {self.anchor_score!r}"
                )
            if self.reason is not None:
                raise ResearchIntegrityError("SCORED outcome must not carry a reason")
            return

        # MISSING / INELIGIBLE: no score, and an explicit non-empty reason.
        if self.anchor_score is not None:
            raise ResearchIntegrityError(
                f"{self.status.value} outcome must not carry an anchor_score"
            )
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ResearchIntegrityError(f"{self.status.value} outcome requires a non-empty reason")


@dataclass(frozen=True, slots=True)
class PairedFixedDecisionRow:
    """A deterministic pairing of one planned item with its A and B outcomes."""

    item: PlannedFixedDecisionItem
    outcome_a: MeasurementOutcome
    outcome_b: MeasurementOutcome

    def canonical_payload(self) -> dict[str, JSONValue]:
        return {
            "item": _planned_item_payload(self.item),
            "a": _outcome_payload(self.outcome_a),
            "b": _outcome_payload(self.outcome_b),
        }


@dataclass(frozen=True, slots=True)
class PairedFixedDecisionDataset:
    """The explicit A/B outcomes for one exact plan.

    Every planned item must appear exactly once in ``outcomes_a`` and exactly
    once in ``outcomes_b``. Missing or ineligible measurements are preserved as
    rows; the dataset never silently shrinks the analyzed item universe and
    exposes no complete-case or eligible-only filtering.
    """

    plan: PairedFixedDecisionPlan
    outcomes_a: tuple[MeasurementOutcome, ...]
    outcomes_b: tuple[MeasurementOutcome, ...]
    rows: tuple[PairedFixedDecisionRow, ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.plan, PairedFixedDecisionPlan):
            raise ResearchIntegrityError("plan must be a PairedFixedDecisionPlan")
        index_a = _index_outcomes(self.outcomes_a, side="a")
        index_b = _index_outcomes(self.outcomes_b, side="b")
        planned_ids = {item.item_id for item in self.plan.items}
        _require_exact_item_set(index_a, planned_ids, side="a")
        _require_exact_item_set(index_b, planned_ids, side="b")
        rows = tuple(
            PairedFixedDecisionRow(
                item=item,
                outcome_a=index_a[item.item_id],
                outcome_b=index_b[item.item_id],
            )
            for item in self.plan._sorted_items()
        )
        object.__setattr__(self, "rows", rows)

    @classmethod
    def create(
        cls,
        plan: PairedFixedDecisionPlan,
        outcomes_a: tuple[MeasurementOutcome, ...],
        outcomes_b: tuple[MeasurementOutcome, ...],
    ) -> PairedFixedDecisionDataset:
        """Build a dataset that pairs outcomes by exact ``item_id``."""
        return cls(plan=plan, outcomes_a=outcomes_a, outcomes_b=outcomes_b)

    def canonical_payload(self) -> dict[str, JSONValue]:
        return {
            "artifact": "paired-fixed-decision-dataset",
            "fingerprint_version": PAIRED_FIXED_DECISION_DATASET_FINGERPRINT_VERSION,
            "plan": self.plan.canonical_payload(),
            "rows": [row.canonical_payload() for row in self.rows],
        }

    @property
    def fingerprint(self) -> str:
        """Deterministic SHA-256 over the canonical dataset payload."""
        return fingerprint(self.canonical_payload())


def _identity_payload(identity: MeasurementProtocolIdentity) -> dict[str, JSONValue]:
    return {
        "measurement_id": identity.measurement_id,
        "measurement_version": identity.measurement_version,
    }


def _planned_item_payload(item: PlannedFixedDecisionItem) -> dict[str, JSONValue]:
    return {
        "item_id": item.item_id,
        "split": item.split.value,
        "anchor_value": item.anchor_value,
        "ground_truth_value": item.ground_truth_value,
        "anchor_correct": item.anchor_correct,
    }


def _outcome_payload(outcome: MeasurementOutcome) -> dict[str, JSONValue]:
    return {
        "item_id": outcome.item_id,
        "status": outcome.status.value,
        "anchor_score": outcome.anchor_score,
        "winner_value": outcome.winner_value,
        "source_record_id": outcome.source_record_id,
        "reason": outcome.reason,
    }


def _index_outcomes(outcomes: object, *, side: str) -> dict[str, MeasurementOutcome]:
    if not isinstance(outcomes, tuple):
        raise ResearchIntegrityError(
            f"outcomes_{side} must be a tuple of MeasurementOutcome, got {type(outcomes).__name__}"
        )
    index: dict[str, MeasurementOutcome] = {}
    for outcome in outcomes:
        if not isinstance(outcome, MeasurementOutcome):
            raise ResearchIntegrityError(
                f"every outcomes_{side} element must be a MeasurementOutcome, "
                f"got {type(outcome).__name__}"
            )
        if outcome.item_id in index:
            raise ResearchIntegrityError(
                f"outcomes_{side} contains a duplicate item_id {outcome.item_id!r}"
            )
        index[outcome.item_id] = outcome
    return index


def _require_exact_item_set(
    index: dict[str, MeasurementOutcome],
    planned_ids: set[str],
    *,
    side: str,
) -> None:
    present = set(index)
    missing = planned_ids - present
    if missing:
        raise ResearchIntegrityError(
            f"outcomes_{side} is missing planned item(s): {sorted(missing)!r}; a missing "
            "measurement must be recorded explicitly as MISSING or INELIGIBLE"
        )
    extra = present - planned_ids
    if extra:
        raise ResearchIntegrityError(
            f"outcomes_{side} contains unplanned item(s): {sorted(extra)!r}"
        )
