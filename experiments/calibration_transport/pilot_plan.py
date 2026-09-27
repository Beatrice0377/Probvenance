"""Pre-measurement plan construction for the R2 frozen-decision CAT/OVR pilot.

This module does exactly one phase of the experiment, and no more:

1. load the frozen ``choice_signal`` three-way fixture,
2. declare the pre-declared 9/6 TRAIN/TEST split (empty AUDIT),
3. compute the deterministic hash-selected anchor per item,
4. declare the synthetic ground-truth semantics, and
5. build the R1 :class:`~integrity.PairedFixedDecisionPlan`.

It runs no model, looks at no measurement output, fits no calibrator, and picks
no anchor from any label or score. That keeps "plan before outcomes" true in the
code structure itself.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from probvenance.calibration import (
    GROUND_TRUTH_SEMANTICS_FINGERPRINT_VERSION,
    GroundTruthProvenance,
    GroundTruthSemanticsIdentity,
)
from probvenance.fingerprint import JSONValue, fingerprint

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
_measurements = _load_sibling("measurements")
Split = _integrity.Split
PlannedFixedDecisionItem = _integrity.PlannedFixedDecisionItem
PairedFixedDecisionPlan = _integrity.PairedFixedDecisionPlan

DEFAULT_CASES_PATH = _HARNESS_DIR.parent / "choice_signal" / "cases.json"

CASE_SET_VERSION = "choice-signal-v1"

SPLIT_PROTOCOL_ID = "three-way-synthetic-3-train-2-test-per-category"
SPLIT_PROTOCOL_VERSION = 1

ANCHOR_SELECTION_ID = "sha256-case-id-candidate-set-anchor"
ANCHOR_SELECTION_VERSION = 1

POPULATION_ID = "choice-signal-three-way-frozen-decision-pilot"
POPULATION_VERSION = 1

GT_LABELING_RULE_ID = "choice-signal-handwritten-expected-category-v1"
GT_AMBIGUITY_POLICY_ID = "predeclared-resolved-three-way-synthetic-pilot-v1"
GT_LABEL_SOURCE = "choice-signal-handwritten-expected-category"
GT_TAXONOMY_ID = "choice-signal-routing-three-way"
GT_TAXONOMY_VERSION = 1

#: The pre-declared split, frozen before any measurement runs. Splits are keyed
#: by exact source case id, never inferred from a score.
TRAIN_CASE_IDS: tuple[str, ...] = (
    "3w-billing-01",
    "3w-billing-02",
    "3w-billing-03",
    "3w-shipping-01",
    "3w-shipping-02",
    "3w-shipping-03",
    "3w-technical-01",
    "3w-technical-02",
    "3w-technical-03",
)
TEST_CASE_IDS: tuple[str, ...] = (
    "3w-billing-04",
    "3w-billing-05",
    "3w-shipping-04",
    "3w-shipping-05",
    "3w-technical-04",
    "3w-technical-05",
)
AUDIT_CASE_IDS: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PilotCase:
    """One three-way source case in exact source order."""

    case_id: str
    question: str
    context: str
    candidates: tuple[tuple[str, str | None], ...]


def load_case_set(path: Path | str = DEFAULT_CASES_PATH) -> dict[str, Any]:
    """Load the frozen source case set as parsed JSON."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"case set must be a JSON object, got {type(payload).__name__}")
    return payload


def case_set_fingerprint(payload: Mapping[str, Any]) -> str:
    """The exact-JSON content fingerprint of the source case set."""
    return fingerprint(dict(payload))


def source_candidates(payload: Mapping[str, Any]) -> tuple[tuple[str, str | None], ...]:
    """The ``three_way`` candidate set in exact source semantic order."""
    raw = payload["candidate_sets"]["three_way"]
    candidates = tuple((str(c["name"]), c.get("description")) for c in raw)
    if len(candidates) < 2:
        raise ValueError("three_way candidate set must contain at least two candidates")
    return candidates


def pilot_cases(payload: Mapping[str, Any]) -> tuple[PilotCase, ...]:
    """All three-way cases, in exact source order, as :class:`PilotCase` values."""
    question = str(payload["question"])
    candidates = source_candidates(payload)
    return tuple(
        PilotCase(
            case_id=str(case["id"]),
            question=question,
            context=str(case["context"]),
            candidates=candidates,
        )
        for case in payload["three_way_cases"]
    )


def select_anchor(case_id: str, candidate_names: Sequence[str]) -> str:
    """Deterministically select the frozen anchor for one item.

    The selection consumes ONLY the case id and the sorted candidate names. It
    takes no ground-truth, no CAT/OVR score, and no winner, so it structurally
    cannot condition on the compared A/B outcomes.
    """
    if not candidate_names:
        raise ValueError("candidate_names must be non-empty")
    sorted_names = sorted(candidate_names)
    frozen_names: list[JSONValue] = [name for name in sorted_names]
    payload: dict[str, JSONValue] = {
        "v": 1,
        "anchor_selection_id": ANCHOR_SELECTION_ID,
        "anchor_selection_version": ANCHOR_SELECTION_VERSION,
        "case_id": case_id,
        "candidate_names": frozen_names,
    }
    digest = fingerprint(payload)
    return sorted_names[int(digest, 16) % len(sorted_names)]


def predeclared_split(case_id: str) -> Any:
    """The frozen split membership for one source case id."""
    if case_id in TRAIN_CASE_IDS:
        return Split.TRAIN
    if case_id in TEST_CASE_IDS:
        return Split.TEST
    if case_id in AUDIT_CASE_IDS:  # pragma: no cover - empty by construction
        return Split.AUDIT
    raise ValueError(f"case id {case_id!r} is not part of the frozen pilot split")


def ground_truth_semantics() -> GroundTruthSemanticsIdentity:
    """The declared synthetic-pilot ground-truth semantics identity.

    This declares what the correctness label MEANS. It is not a claim that the
    labels are objectively correct; the fixture is hand-written synthetic data.
    """
    provenance = GroundTruthProvenance(
        label_source=GT_LABEL_SOURCE,
        labeling_rule=GT_LABELING_RULE_ID,
        adjudicated=False,
        ambiguity_policy=GT_AMBIGUITY_POLICY_ID,
        taxonomy_id=GT_TAXONOMY_ID,
        taxonomy_version=GT_TAXONOMY_VERSION,
    )
    return GroundTruthSemanticsIdentity.from_provenance(provenance)


def _require_frozen_case_set(payload: Mapping[str, Any]) -> tuple[PilotCase, ...]:
    cases = pilot_cases(payload)
    ids = tuple(case.case_id for case in cases)
    expected = TRAIN_CASE_IDS + TEST_CASE_IDS + AUDIT_CASE_IDS
    if len(ids) != len(expected) or set(ids) != set(expected):
        raise ValueError(
            "the three-way fixture no longer matches the frozen pilot case set: "
            f"got {len(ids)} cases {ids}, expected {len(expected)} {expected}"
        )
    return cases


def build_plan(
    payload: Mapping[str, Any],
    *,
    model_id: str,
    model_revision: str | None,
) -> Any:
    """Build the exact R1 plan for the frozen three-way pilot fixture.

    Ground truth is used only to FORM the declared correctness label
    ``anchor_correct = (anchor_value == expected_category)``; it never enters
    anchor selection, which is computed independently from the case id and the
    candidate set.
    """
    cases = _require_frozen_case_set(payload)
    source_by_id = {str(case["id"]): case for case in payload["three_way_cases"]}
    candidate_names = [name for name, _ in source_candidates(payload)]
    semantics = ground_truth_semantics()
    items: list[Any] = []
    for case in cases:
        raw = source_by_id[case.case_id]
        expected_category = str(raw["expected_category"])
        anchor = select_anchor(case.case_id, candidate_names)
        items.append(
            PlannedFixedDecisionItem(
                item_id=case.case_id,
                split=predeclared_split(case.case_id),
                anchor_value=anchor,
                ground_truth_value=expected_category,
                anchor_correct=(anchor == expected_category),
            )
        )
    return PairedFixedDecisionPlan(
        model_id=model_id,
        model_revision=model_revision,
        population_id=POPULATION_ID,
        population_version=POPULATION_VERSION,
        ground_truth_semantics_fingerprint=semantics.fingerprint,
        ground_truth_semantics_fingerprint_version=GROUND_TRUTH_SEMANTICS_FINGERPRINT_VERSION,
        measurement_a=_measurements.cat_identity(),
        measurement_b=_measurements.ovr_identity(),
        anchor_selection_id=ANCHOR_SELECTION_ID,
        anchor_selection_version=ANCHOR_SELECTION_VERSION,
        split_protocol_id=SPLIT_PROTOCOL_ID,
        split_protocol_version=SPLIT_PROTOCOL_VERSION,
        items=tuple(items),
    )
