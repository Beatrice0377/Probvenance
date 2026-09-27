"""Pre-measurement plan construction for the R2B stability/deconfounding round.

R2B is still an exploratory, hypothesis-generating round: it was designed after
seeing R2A, so it cannot be confirmatory evidence. This module does exactly one
phase and no more:

1. load the frozen ``r2b_cases.json`` 150-item fixture,
2. validate its declared structure (150 items, 50/category, 30/stratum,
   10/category-stratum cell, unique ids/contexts, no R2A context reuse),
3. apply the pre-declared six-train/four-test per-cell split (empty AUDIT),
4. compute the deterministic hash-selected anchor per item using the SAME
   single-source function R2A uses, and
5. build the R1 :class:`~integrity.PairedFixedDecisionPlan`.

It runs no model, looks at no measurement output, and never rebalances the
anchor or the split. Ground truth forms only the declared label
``anchor_correct``; it never enters anchor selection.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from probvenance.calibration import GROUND_TRUTH_SEMANTICS_FINGERPRINT_VERSION
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


pilot_plan = _load_sibling("pilot_plan")
_integrity = pilot_plan._integrity
Split = _integrity.Split
PlannedFixedDecisionItem = _integrity.PlannedFixedDecisionItem
PairedFixedDecisionPlan = _integrity.PairedFixedDecisionPlan

DEFAULT_CASES_PATH = _HARNESS_DIR / "r2b_cases.json"

R2B_CASE_SET_VERSION = "calibration-transport-r2b-v1"

SPLIT_PROTOCOL_ID = "r2b-five-strata-6-train-4-test-per-cell"
SPLIT_PROTOCOL_VERSION = 1

POPULATION_ID = "calibration-transport-r2b-three-way-stability"
POPULATION_VERSION = 1

CATEGORIES: tuple[str, ...] = ("billing", "shipping", "technical")
STRATA: tuple[str, ...] = (
    "direct",
    "indirect",
    "distractor",
    "mixed-primary",
    "contrast-negation",
)

ITEMS_PER_CELL = 10
TRAIN_PER_CELL = 6
TEST_PER_CELL = 4
TOTAL_ITEMS = len(CATEGORIES) * len(STRATA) * ITEMS_PER_CELL  # 150
TRAIN_TOTAL = len(CATEGORIES) * len(STRATA) * TRAIN_PER_CELL  # 90
TEST_TOTAL = len(CATEGORIES) * len(STRATA) * TEST_PER_CELL  # 60


@dataclass(frozen=True, slots=True)
class R2BCase:
    """One R2B source case in exact fixture order."""

    item_id: str
    stratum: str
    expected_category: str
    context: str


def load_case_set(path: Path | str = DEFAULT_CASES_PATH) -> dict[str, Any]:
    """Load the frozen R2B source case set as parsed JSON."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"case set must be a JSON object, got {type(payload).__name__}")
    return payload


def case_set_fingerprint(payload: Mapping[str, Any]) -> str:
    """The exact-JSON content fingerprint of the R2B source case set."""
    return fingerprint(dict(payload))


def candidate_set(payload: Mapping[str, Any]) -> tuple[tuple[str, str | None], ...]:
    """The R2B candidate set in exact declared order."""
    raw = payload["candidate_set"]
    candidates = tuple((str(c["name"]), c.get("description")) for c in raw)
    if len(candidates) < 2:
        raise ValueError("r2b candidate_set must contain at least two candidates")
    return candidates


def r2b_cases(payload: Mapping[str, Any]) -> tuple[R2BCase, ...]:
    """All R2B cases, in exact fixture order, as :class:`R2BCase` values."""
    return tuple(
        R2BCase(
            item_id=str(case["id"]),
            stratum=str(case["stratum"]),
            expected_category=str(case["expected_category"]),
            context=str(case["context"]),
        )
        for case in payload["cases"]
    )


def cell_key(case: R2BCase) -> tuple[str, str]:
    """The declared (category, stratum) cell of one case."""
    return (case.expected_category, case.stratum)


def _cell_ordinals(cases: Sequence[R2BCase]) -> dict[str, int]:
    """Cell-local ordinal (0-based, exact fixture order) for every item id."""
    seen: dict[tuple[str, str], int] = {}
    ordinals: dict[str, int] = {}
    for case in cases:
        key = cell_key(case)
        ordinals[case.item_id] = seen.get(key, 0)
        seen[key] = seen.get(key, 0) + 1
    return ordinals


def split_of(payload: Mapping[str, Any]) -> dict[str, Any]:
    """The frozen split membership of every item id, keyed by cell-local ordinal.

    Within each declared (category, stratum) cell, the first ``TRAIN_PER_CELL``
    items are TRAIN and the last ``TEST_PER_CELL`` items are TEST. This is an
    explicit pre-measurement split: no shuffle, no seed, no score peeking.
    """
    cases = r2b_cases(payload)
    ordinals = _cell_ordinals(cases)
    mapping: dict[str, Any] = {}
    for case in cases:
        ordinal = ordinals[case.item_id]
        if ordinal < TRAIN_PER_CELL:
            mapping[case.item_id] = Split.TRAIN
        elif ordinal < TRAIN_PER_CELL + TEST_PER_CELL:
            mapping[case.item_id] = Split.TEST
        else:  # pragma: no cover - blocked by structural validation
            raise ValueError(f"cell ordinal {ordinal} exceeds the declared cell size")
    return mapping


def predeclared_split(item_id: str, payload: Mapping[str, Any]) -> Any:
    """The frozen split for one item id."""
    mapping = split_of(payload)
    if item_id not in mapping:
        raise ValueError(f"item id {item_id!r} is not part of the frozen R2B case set")
    return mapping[item_id]


def ground_truth_semantics() -> Any:
    """The declared ground-truth semantics identity, reused from R2A.

    R2B studies the same semantic correctness object as R2A (a hand-written
    expected routing category), so it reuses the R2A-declared labeling rule and
    taxonomy rather than inventing a new identity.
    """
    return pilot_plan.ground_truth_semantics()


def _reference_cases_path(reference_cases_path: str | Path | None) -> Path:
    if reference_cases_path is not None:
        return Path(reference_cases_path)
    return Path(pilot_plan.DEFAULT_CASES_PATH)


def validate_case_set(
    payload: Mapping[str, Any], *, reference_cases_path: str | Path | None = None
) -> None:
    """Structural validation of the R2B fixture; fails closed on any drift.

    Checks the exact 150-item structure, per-category/per-stratum/per-cell
    counts, id and context uniqueness, opaque id shape, declared categories and
    strata, candidate-set equality with the R2A three-way set, and zero exact
    context overlap with the R2A fixture.
    """
    cases = r2b_cases(payload)
    if len(cases) != TOTAL_ITEMS:
        raise ValueError(f"R2B case set must contain {TOTAL_ITEMS} cases, got {len(cases)}")

    if list(payload.get("strata", [])) != list(STRATA):
        raise ValueError(f"R2B strata must be exactly {list(STRATA)}")
    if payload.get("case_set_version") != R2B_CASE_SET_VERSION:
        raise ValueError(f"R2B case_set_version must be {R2B_CASE_SET_VERSION!r}")

    ids = [case.item_id for case in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("R2B item ids must be unique")
    for item_id in ids:
        if len(item_id) != 8 or not item_id.startswith("r2b-") or not item_id[4:].isdigit():
            raise ValueError(
                f"R2B item id {item_id!r} must be an opaque r2b-NNNN identifier "
                "(the ground-truth category must not appear in the id)"
            )

    contexts = [case.context for case in cases]
    if len(set(contexts)) != len(contexts):
        raise ValueError("R2B contexts must be unique")

    expected_ids = [f"r2b-{index:04d}" for index in range(1, TOTAL_ITEMS + 1)]
    if sorted(ids) != expected_ids:
        raise ValueError("R2B item ids must be exactly r2b-0001..r2b-0150")

    per_category: dict[str, int] = {name: 0 for name in CATEGORIES}
    per_stratum: dict[str, int] = {name: 0 for name in STRATA}
    per_cell: dict[tuple[str, str], int] = {}
    for case in cases:
        if case.expected_category not in CATEGORIES:
            raise ValueError(
                f"expected_category {case.expected_category!r} is not in {list(CATEGORIES)}"
            )
        if case.stratum not in STRATA:
            raise ValueError(f"stratum {case.stratum!r} is not in {list(STRATA)}")
        per_category[case.expected_category] += 1
        per_stratum[case.stratum] += 1
        key = cell_key(case)
        per_cell[key] = per_cell.get(key, 0) + 1

    for name, count in per_category.items():
        if count != 50:
            raise ValueError(f"category {name!r} must have 50 items, got {count}")
    for name, count in per_stratum.items():
        if count != 30:
            raise ValueError(f"stratum {name!r} must have 30 items, got {count}")
    for category in CATEGORIES:
        for stratum in STRATA:
            count = per_cell.get((category, stratum), 0)
            if count != ITEMS_PER_CELL:
                raise ValueError(
                    f"cell ({category!r}, {stratum!r}) must have "
                    f"{ITEMS_PER_CELL} items, got {count}"
                )

    declared = candidate_set(payload)
    reference_payload = pilot_plan.load_case_set(_reference_cases_path(reference_cases_path))
    reference_candidates = pilot_plan.source_candidates(reference_payload)
    if declared != reference_candidates:
        raise ValueError(
            "R2B candidate set (names and descriptions) must equal the R2A three_way set exactly"
        )

    reference_contexts = {str(case["context"]) for case in reference_payload["three_way_cases"]}
    overlap = [case.item_id for case in cases if case.context in reference_contexts]
    if overlap:
        raise ValueError(f"R2B contexts must not duplicate R2A contexts exactly: {overlap!r}")


def build_plan(
    payload: Mapping[str, Any],
    *,
    model_id: str,
    model_revision: str | None,
    reference_cases_path: str | Path | None = None,
) -> Any:
    """Build the exact R1 plan for the frozen R2B fixture.

    Ground truth is used only to form the declared correctness label
    ``anchor_correct = (anchor_value == expected_category)``; anchor selection is
    computed independently by the shared R2A ``pilot_plan.select_anchor`` from the
    opaque item id and the candidate set.
    """
    validate_case_set(payload, reference_cases_path=reference_cases_path)
    cases = r2b_cases(payload)
    splits = split_of(payload)
    candidate_names = [name for name, _description in candidate_set(payload)]
    semantics = ground_truth_semantics()
    items: list[Any] = []
    for case in cases:
        anchor = pilot_plan.select_anchor(case.item_id, candidate_names)
        items.append(
            PlannedFixedDecisionItem(
                item_id=case.item_id,
                split=splits[case.item_id],
                anchor_value=anchor,
                ground_truth_value=case.expected_category,
                anchor_correct=(anchor == case.expected_category),
            )
        )
    return PairedFixedDecisionPlan(
        model_id=model_id,
        model_revision=model_revision,
        population_id=POPULATION_ID,
        population_version=POPULATION_VERSION,
        ground_truth_semantics_fingerprint=semantics.fingerprint,
        ground_truth_semantics_fingerprint_version=GROUND_TRUTH_SEMANTICS_FINGERPRINT_VERSION,
        measurement_a=_load_sibling("measurements").cat_identity(),
        measurement_b=_load_sibling("measurements").ovr_identity(),
        anchor_selection_id=pilot_plan.ANCHOR_SELECTION_ID,
        anchor_selection_version=pilot_plan.ANCHOR_SELECTION_VERSION,
        split_protocol_id=SPLIT_PROTOCOL_ID,
        split_protocol_version=SPLIT_PROTOCOL_VERSION,
        items=tuple(items),
    )
