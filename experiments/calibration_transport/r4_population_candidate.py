"""R4 deterministic population construction CANDIDATE (structural only).

Status produced by this script:

    POPULATION CONSTRUCTION CANDIDATE / READY FOR HUMAN FREEZE REVIEW

This is NOT a FINAL POPULATION MANIFEST, NOT a TRAIN/TEST freeze, and NOT an
execution authorization. R4 remains DRAFT / NOT FROZEN / NOT EXECUTION-AUTHORIZED.

What it does:
  * reads the exact-revision pinned local parquet snapshots of ``Rowan/hellaswag``
    and ``openlifescienceai/medmcqa``;
  * builds a deterministic, content-independent CALIBRATION TRAIN population of
    N = 456 per dataset by Hamilton / largest-remainder proportional allocation
    over a predeclared stratum field;
  * declares the evaluation TEST population first (pristine) as every structurally
    eligible labeled validation row;
  * applies the R3-style overlap guard (TRAIN row excluded when its exact
    question + exact ordered candidate strings duplicate a TEST row; a conflicting
    ground truth for the same event raises ``PopulationError`` / STOP);
  * assigns a measurement-independent anchor index and a deterministic,
    answer-independent ``item_id``;
  * additionally builds a NESTED secondary sample-size-robustness candidate of
    N = 912 per dataset (frozen primary 456 + a 456-row Hamilton residual
    extension over the remaining eligible source-train rows).  The 912 candidate
    is a strict item-id superset of the primary 456 and REUSES the primary TEST
    unchanged, so the only thing that changes is the calibration TRAIN sample
    size.  The primary manifests are never modified and are protected by an
    expected-manifest-fingerprint guard;
  * writes candidate manifests OUTSIDE the repo to
    ``/root/rivermind-data/r4-population-candidates/``.

Hard prohibitions enforced here:
  * NO model / tokenizer import, NO GPU, NO forward, NO generation;
  * NO calibration fitting (no logistic / isotonic / beta), NO Brier, NO LogLoss,
    NO transport, NO predictor outcome;
  * every selection / ranking / id / anchor input is derived from protocol
    identity plus source coordinates only: never ground truth, never question or
    candidate text, never a model output;
  * ground-truth and anchor distributions are reported as STRUCTURAL DIAGNOSTICS
    only and are never used to modify a selection rule.

Run:
    PYTHONPATH=/root/rivermind-data/r4-dataset-audit/pylibs \\
    /root/rivermind-data/envs/probvenance-r4/bin/python \\
        experiments/calibration_transport/r4_population_candidate.py
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from probvenance.fingerprint import fingerprint

DATASETS_ROOT = Path("/root/rivermind-data/r4-datasets")
OUT_DIR = Path("/root/rivermind-data/r4-population-candidates")

HELLASWAG_REPO = "Rowan/hellaswag"
HELLASWAG_REVISION = "218ec52e09a7e7462a5400043bb9a69a41d06b76"
MEDMCQA_REPO = "openlifescienceai/medmcqa"
MEDMCQA_REVISION = "91c6572c454088bf71b679ad90aa8dffcd0d5868"

POPULATION_PROTOCOL_ID = "r4-stratified-population-construction"
POPULATION_PROTOCOL_VERSION = 1
SELECTION_PROTOCOL_ID = "r4-stratified-source-index-hash-selection"
SELECTION_PROTOCOL_VERSION = 1
ANCHOR_PROTOCOL_ID = "r4-fixed-event-anchor-deterministic-source-index-hash"
ANCHOR_PROTOCOL_VERSION = 1
EXTENSION_PROTOCOL_ID = "r4-nested-residual-extension"
EXTENSION_PROTOCOL_VERSION = 1

CALIBRATION_TRAIN_N = 456
ROBUSTNESS_TRAIN_N = 912
ROBUSTNESS_EXTENSION_N = ROBUSTNESS_TRAIN_N - CALIBRATION_TRAIN_N
CANDIDATE_NAMES = ("option-0", "option-1", "option-2", "option-3")
NORMALIZATION = "Unicode NFC + CRLF/CR->LF + outer strip (no case folding, no stemming)"

STATUS = "POPULATION CONSTRUCTION CANDIDATE / READY FOR HUMAN FREEZE REVIEW"
ROBUSTNESS_ROLE = "secondary-sample-size-robustness"
ROBUSTNESS_STATUS = (
    "POPULATION CONSTRUCTION CANDIDATE / SECONDARY SAMPLE-SIZE ROBUSTNESS / "
    "READY FOR HUMAN FREEZE REVIEW"
)

# Frozen primary identities: any drift means the primary population was altered.
EXPECTED_PRIMARY_MANIFEST_FINGERPRINT = {
    "hellaswag": "5c45043ba4f0ec436c16dcf494ff26be435c7857244bcbefa321d1678129c400",
    "medmcqa": "4a4718438d46ab1ba27c59ca46806756ffb62efa05e6103981dffec4dc48c218",
}


class PopulationError(RuntimeError):
    """Raised when a predeclared structural rule cannot be satisfied."""


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def normalize_text(value: str) -> str:
    """Conservative exact normalization: NFC + newline normalization + outer strip."""
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    return unicodedata.normalize("NFC", text).strip()


def anchor_index(*, dataset_id: str, revision: str, source_split: str, row_index: int) -> int:
    """Measurement-independent anchor: protocol identity + source coordinates only."""
    digest = fingerprint(
        {
            "protocol_id": ANCHOR_PROTOCOL_ID,
            "protocol_version": ANCHOR_PROTOCOL_VERSION,
            "dataset_id": dataset_id,
            "dataset_revision": revision,
            "source_split": source_split,
            "source_row_index": row_index,
        }
    )
    return int(digest[:16], 16) % 4


def item_id(*, dataset_id: str, revision: str, source_split: str, row_index: int) -> str:
    """Deterministic, answer-independent item identity (never exposes correctness)."""
    return fingerprint(
        {
            "population_protocol_id": POPULATION_PROTOCOL_ID,
            "population_protocol_version": POPULATION_PROTOCOL_VERSION,
            "dataset_id": dataset_id,
            "dataset_revision": revision,
            "source_split": source_split,
            "source_row_index": row_index,
        }
    )


def selection_rank(
    *,
    dataset_id: str,
    revision: str,
    source_split: str,
    stratum: str,
    row_index: int,
) -> str:
    """Within-stratum ranking key: no ground truth, no content, no model output."""
    return fingerprint(
        {
            "selection_protocol_id": SELECTION_PROTOCOL_ID,
            "selection_protocol_version": SELECTION_PROTOCOL_VERSION,
            "dataset_id": dataset_id,
            "dataset_revision": revision,
            "source_split": source_split,
            "stratum": stratum,
            "source_row_index": row_index,
        }
    )


def hamilton_quota(weights: dict[str, int], total: int) -> dict[str, int]:
    """Hamilton / largest-remainder allocation with a deterministic tie-break.

    Ties on the fractional remainder are broken by stratum name (ascending), which
    is independent of ground truth, content and model output.
    """
    grand = sum(weights.values())
    if grand <= 0:
        raise PopulationError("cannot allocate quotas from an empty eligible pool")
    if total > grand:
        raise PopulationError(f"requested N={total} exceeds eligible pool size {grand}")
    exact = {name: total * weight / grand for name, weight in weights.items()}
    quota = {name: int(value) for name, value in exact.items()}
    remaining = total - sum(quota.values())
    order = sorted(exact, key=lambda name: (-(exact[name] - quota[name]), name))
    for name in order[:remaining]:
        quota[name] += 1
    return quota


def snapshot_dir(repo: str, revision: str) -> Path:
    return DATASETS_ROOT / f"datasets--{repo.replace('/', '--')}" / "snapshots" / revision


def read_rows(repo: str, revision: str, split: str) -> list[dict[str, Any]]:
    path = snapshot_dir(repo, revision) / "data" / f"{split}-00000-of-00001.parquet"
    return pq.read_table(path).to_pylist()


def _distribution(values: list[int], expected: int = 4) -> dict[str, Any]:
    counter = Counter(values)
    size = len(values)
    return {
        "counts": {str(index): counter.get(index, 0) for index in range(expected)},
        "fractions": {
            str(index): (counter.get(index, 0) / size if size else 0.0)
            for index in range(expected)
        },
    }


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _rank_entries(
    pool: list[tuple[int, dict[str, Any]]],
    *,
    dataset_id: str,
    revision: str,
    stratum_of: Callable[[dict[str, Any]], str],
) -> dict[str, list[tuple[int, dict[str, Any]]]]:
    """Group eligible source-train rows by stratum and sort by the rank doctrine."""
    by_stratum: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for index, row in pool:
        by_stratum.setdefault(stratum_of(row), []).append((index, row))
    for entries in by_stratum.values():
        entries.sort(
            key=lambda pair: (
                selection_rank(
                    dataset_id=dataset_id,
                    revision=revision,
                    source_split="train",
                    stratum=stratum_of(pair[1]),
                    row_index=pair[0],
                ),
                pair[0],
            )
        )
    return by_stratum


def _stratified_select(
    ranked: dict[str, list[tuple[int, dict[str, Any]]]],
    quota: dict[str, int],
    *,
    test_keys: set[Any],
    key_of: Callable[[dict[str, Any]], Any],
    group_of: Callable[[dict[str, Any]], str | None],
    used_groups: set[str],
    used_indices: set[int],
    label: str,
    test_truth_by_key: dict[Any, set[Any]] | None = None,
    truth_of: Callable[[dict[str, Any]], Any] | None = None,
) -> tuple[list[tuple[int, dict[str, Any]]], int, int]:
    """Shared stratified selection: quota, TEST overlap guard, optional group guard.

    ``used_groups`` / ``used_indices`` are mutated in place and may be pre-seeded
    with an already-frozen selection so that a later extension cannot reuse them.
    """
    selected: list[tuple[int, dict[str, Any]]] = []
    overlap_excluded = 0
    group_skipped = 0
    for name in sorted(ranked):
        need = quota.get(name, 0)
        taken = 0
        for index, row in ranked[name]:
            if taken >= need:
                break
            if index in used_indices:
                continue
            key = key_of(row)
            if key in test_keys:
                if (
                    test_truth_by_key is not None
                    and truth_of is not None
                    and test_truth_by_key[key] != {truth_of(row)}
                ):
                    raise PopulationError(
                        "cross-split question + ordered candidates duplicate with a "
                        f"conflicting ground truth (source_row_index {index}); "
                        "STOP FOR HUMAN REVIEW"
                    )
                overlap_excluded += 1
                continue
            group = group_of(row)
            if group is not None and group in used_groups:
                group_skipped += 1
                continue
            if group is not None:
                used_groups.add(group)
            used_indices.add(index)
            selected.append((index, row))
            taken += 1
        if taken < need:
            raise PopulationError(
                f"{label} {name!r}: quota {need} not satisfiable "
                f"(selected {taken}); STOP / NEEDS_REVIEW"
            )
    return selected, overlap_excluded, group_skipped


def _nestedness_audit(
    primary_train: list[dict[str, Any]], train_items: list[dict[str, Any]]
) -> dict[str, Any]:
    """Mechanically prove TRAIN_456 subset of TRAIN_912 with 456 new unique ids."""
    primary_ids = {item["item_id"] for item in primary_train}
    train_ids = {item["item_id"] for item in train_items}
    extension_ids = train_ids - primary_ids
    audit = {
        "primary_train_count": len(primary_train),
        "primary_unique_item_ids": len(primary_ids),
        "train_count": len(train_items),
        "train_unique_item_ids": len(train_ids),
        "extension_unique_item_ids": len(extension_ids),
        "primary_ids_missing_from_train": len(primary_ids - train_ids),
        "nested_primary": primary_ids <= train_ids,
    }
    if not audit["nested_primary"]:
        raise PopulationError("TRAIN_456 is not a subset of TRAIN_912; BLOCKED")
    if audit["primary_ids_missing_from_train"] != 0:
        raise PopulationError("primary TRAIN item ids missing from TRAIN_912; BLOCKED")
    if audit["primary_unique_item_ids"] != CALIBRATION_TRAIN_N:
        raise PopulationError("primary TRAIN item ids are not unique; BLOCKED")
    if audit["train_count"] != ROBUSTNESS_TRAIN_N:
        raise PopulationError(
            f"TRAIN_912 count is {audit['train_count']}, expected {ROBUSTNESS_TRAIN_N}; BLOCKED"
        )
    if audit["extension_unique_item_ids"] != ROBUSTNESS_EXTENSION_N:
        raise PopulationError(
            f"extension added {audit['extension_unique_item_ids']} unique ids, "
            f"expected {ROBUSTNESS_EXTENSION_N}; BLOCKED"
        )
    return audit


# --------------------------------------------------------------------------- #
# HellaSwag
# --------------------------------------------------------------------------- #


def _hs_eligible(row: dict[str, Any]) -> bool:
    endings = row["endings"]
    if not isinstance(endings, list) or len(endings) != 4:
        return False
    if not all(isinstance(ending, str) for ending in endings):
        return False
    label = row["label"]
    if not isinstance(label, str) or label.strip() == "":
        return False
    try:
        value = int(label.strip())
    except ValueError:
        return False
    if value not in (0, 1, 2, 3):
        return False
    return bool(str(row["source_id"]).strip()) and bool(str(row["activity_label"]).strip())


def _hs_item(row: dict[str, Any], index: int, *, split: str) -> dict[str, Any]:
    source_split = "train" if split == "TRAIN" else "validation"
    return {
        "dataset_id": HELLASWAG_REPO,
        "dataset_revision": HELLASWAG_REVISION,
        "source_split": source_split,
        "source_row_index": index,
        "item_id": item_id(
            dataset_id=HELLASWAG_REPO,
            revision=HELLASWAG_REVISION,
            source_split=source_split,
            row_index=index,
        ),
        "split": split,
        "stratum": row["activity_label"],
        "group_id": row["source_id"],
        "split_type": row["split_type"],
        "question": row["ctx"],
        "candidate_names": list(CANDIDATE_NAMES),
        "candidate_descriptions": list(row["endings"]),
        "ground_truth_index": int(row["label"].strip()),
        "anchor_index": anchor_index(
            dataset_id=HELLASWAG_REPO,
            revision=HELLASWAG_REVISION,
            source_split=source_split,
            row_index=index,
        ),
    }


def build_hellaswag() -> dict[str, Any]:
    train_rows = read_rows(HELLASWAG_REPO, HELLASWAG_REVISION, "train")
    val_rows = read_rows(HELLASWAG_REPO, HELLASWAG_REVISION, "validation")

    # TEST is declared first and stays pristine: every labeled validation row.
    ineligible_test = [index for index, row in enumerate(val_rows) if not _hs_eligible(row)]
    if ineligible_test:
        raise PopulationError(
            "HellaSwag validation contains structurally ineligible rows "
            f"(source_row_index {ineligible_test[:5]}); STOP FOR HUMAN REVIEW"
        )
    test_items = [_hs_item(row, index, split="TEST") for index, row in enumerate(val_rows)]
    test_keys = {(row["ctx"], tuple(row["endings"])) for row in val_rows}

    pool = [(index, row) for index, row in enumerate(train_rows) if _hs_eligible(row)]
    weights = dict(Counter(row["activity_label"] for _, row in pool))
    quota = hamilton_quota(weights, CALIBRATION_TRAIN_N)

    by_stratum: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for index, row in pool:
        by_stratum.setdefault(row["activity_label"], []).append((index, row))
    for entries in by_stratum.values():
        entries.sort(
            key=lambda pair: (
                selection_rank(
                    dataset_id=HELLASWAG_REPO,
                    revision=HELLASWAG_REVISION,
                    source_split="train",
                    stratum=pair[1]["activity_label"],
                    row_index=pair[0],
                ),
                pair[0],
            )
        )

    used_source_ids: set[str] = set()
    train_items: list[dict[str, Any]] = []
    overlap_excluded = 0
    source_id_skipped = 0
    for name in sorted(by_stratum):
        need = quota.get(name, 0)
        taken = 0
        for index, row in by_stratum[name]:
            if taken >= need:
                break
            if (row["ctx"], tuple(row["endings"])) in test_keys:
                overlap_excluded += 1
                continue
            if row["source_id"] in used_source_ids:
                source_id_skipped += 1
                continue
            used_source_ids.add(row["source_id"])
            train_items.append(_hs_item(row, index, split="TRAIN"))
            taken += 1
        if taken < need:
            raise PopulationError(
                f"HellaSwag activity_label {name!r}: quota {need} not satisfiable "
                f"(selected {taken}); STOP / NEEDS_REVIEW"
            )

    train_source_ids = {item["group_id"] for item in train_items}
    test_source_ids = {item["group_id"] for item in test_items}
    shared_source_ids = train_source_ids & test_source_ids
    test_group_counter = Counter(item["group_id"] for item in test_items)

    train_stratum_counter = Counter(item["stratum"] for item in train_items)
    test_stratum_counter = Counter(item["stratum"] for item in test_items)
    per_stratum = {
        name: {
            "eligible_train_rows": weights.get(name, 0),
            "train_quota": quota.get(name, 0),
            "train_selected": train_stratum_counter.get(name, 0),
            "test_rows": test_stratum_counter.get(name, 0),
        }
        for name in sorted(set(weights) | set(test_stratum_counter))
    }

    test_split_type: dict[str, Any] = {}
    for subgroup in ("indomain", "zeroshot"):
        members = [item for item in test_items if item["split_type"] == subgroup]
        test_split_type[subgroup] = {
            "rows": len(members),
            "anchor": _distribution([item["anchor_index"] for item in members]),
            "ground_truth": _distribution([item["ground_truth_index"] for item in members]),
            "anchor_equals_ground_truth_fraction": (
                sum(item["anchor_index"] == item["ground_truth_index"] for item in members)
                / len(members)
                if members
                else 0.0
            ),
        }

    train_anchor = _distribution([item["anchor_index"] for item in train_items])
    test_anchor = _distribution([item["anchor_index"] for item in test_items])
    train_truth = _distribution([item["ground_truth_index"] for item in train_items])
    test_truth = _distribution([item["ground_truth_index"] for item in test_items])

    statistics: dict[str, Any] = {
        "train_count": len(train_items),
        "test_count": len(test_items),
        "calibration_train_n": CALIBRATION_TRAIN_N,
        "stratum_field": "activity_label",
        "train_stratum_count": len(train_stratum_counter),
        "test_stratum_count": len(test_stratum_counter),
        "per_stratum": per_stratum,
        "allocation": "Hamilton / largest-remainder on eligible source-train row counts",
        "group_field": "source_id",
        "group": {
            "train_unique_source_id": len(train_source_ids),
            "test_unique_source_id": len(test_source_ids),
            "test_rows_in_repeated_source_id": sum(
                count for count in test_group_counter.values() if count > 1
            ),
            "test_repeated_source_id": sum(
                1 for count in test_group_counter.values() if count > 1
            ),
            "test_max_rows_per_source_id": (
                max(test_group_counter.values()) if test_group_counter else 0
            ),
            "train_test_source_id_intersection": len(shared_source_ids),
        },
        "anchor": {
            "train": train_anchor,
            "test": test_anchor,
            "train_anchor_equals_ground_truth_fraction": (
                sum(item["anchor_index"] == item["ground_truth_index"] for item in train_items)
                / len(train_items)
            ),
            "test_anchor_equals_ground_truth_fraction": (
                sum(item["anchor_index"] == item["ground_truth_index"] for item in test_items)
                / len(test_items)
            ),
            "note": "structural diagnostic of the anchor rule; NOT a model accuracy",
        },
        "ground_truth": {
            "train": train_truth,
            "test": test_truth,
            "note": "structural diagnostic only; never used to modify the selection rule",
        },
        "split_type": {
            "test": test_split_type,
            "role": "secondary subgroup diagnostic, NOT primary strata",
        },
        "structural_exclusions": {
            "test_ineligible_rows": len(ineligible_test),
            "train_ineligible_rows": len(train_rows) - len(pool),
        },
        "overlap_exclusions": {
            "train_rows_excluded_by_test_overlap": overlap_excluded,
            "train_rows_skipped_for_source_id_reuse": source_id_skipped,
        },
    }

    return {
        "artifact": "r4-population-construction-candidate",
        "status": STATUS,
        "dataset_id": HELLASWAG_REPO,
        "dataset_revision": HELLASWAG_REVISION,
        "snapshot_path": str(snapshot_dir(HELLASWAG_REPO, HELLASWAG_REVISION)),
        "population_protocol_id": POPULATION_PROTOCOL_ID,
        "population_protocol_version": POPULATION_PROTOCOL_VERSION,
        "selection_protocol_id": SELECTION_PROTOCOL_ID,
        "selection_protocol_version": SELECTION_PROTOCOL_VERSION,
        "anchor_protocol_id": ANCHOR_PROTOCOL_ID,
        "anchor_protocol_version": ANCHOR_PROTOCOL_VERSION,
        "normalization": NORMALIZATION,
        "candidate_names": list(CANDIDATE_NAMES),
        "calibration_train_source_split": "train",
        "evaluation_test_source_split": "validation",
        "selection_rule": (
            "per-activity_label Hamilton quota on eligible train rows; within stratum "
            "ranked by selection_rank fingerprint; at most one selected row per "
            "source_id (skip and take next ranked); skip any row whose ctx + ordered "
            "endings exactly duplicates a TEST row"
        ),
        "train": train_items,
        "test": test_items,
        "statistics": statistics,
    }


def build_hellaswag_robustness912() -> dict[str, Any]:
    """Nested secondary sample-size-robustness candidate (TRAIN 912, same TEST)."""
    primary = build_hellaswag()
    primary_train = primary["train"]
    primary_stats = primary["statistics"]

    train_rows = read_rows(HELLASWAG_REPO, HELLASWAG_REVISION, "train")
    val_rows = read_rows(HELLASWAG_REPO, HELLASWAG_REVISION, "validation")
    test_keys = {(row["ctx"], tuple(row["endings"])) for row in val_rows}

    used_indices = {item["source_row_index"] for item in primary_train}
    used_groups = {item["group_id"] for item in primary_train}

    remaining = [
        (index, row)
        for index, row in enumerate(train_rows)
        if _hs_eligible(row) and index not in used_indices
    ]
    weights = dict(Counter(row["activity_label"] for _, row in remaining))
    quota = hamilton_quota(weights, ROBUSTNESS_EXTENSION_N)
    ranked = _rank_entries(
        remaining,
        dataset_id=HELLASWAG_REPO,
        revision=HELLASWAG_REVISION,
        stratum_of=lambda row: row["activity_label"],
    )
    selected, overlap_excluded, group_skipped = _stratified_select(
        ranked,
        quota,
        test_keys=test_keys,
        key_of=lambda row: (row["ctx"], tuple(row["endings"])),
        group_of=lambda row: row["source_id"],
        used_groups=used_groups,
        used_indices=used_indices,
        label="HellaSwag extension activity_label",
    )
    extension = [_hs_item(row, index, split="TRAIN") for index, row in selected]
    train_items = primary_train + extension
    nestedness = _nestedness_audit(primary_train, train_items)

    primary_counter = Counter(item["stratum"] for item in primary_train)
    extension_counter = Counter(item["stratum"] for item in extension)
    train_counter = Counter(item["stratum"] for item in train_items)
    test_counter = Counter(item["stratum"] for item in primary["test"])
    primary_per_stratum = primary_stats["per_stratum"]
    per_stratum = {
        name: {
            "eligible_train_rows": primary_per_stratum.get(name, {}).get(
                "eligible_train_rows", 0
            ),
            "primary_train_selected": primary_counter.get(name, 0),
            "eligible_remaining_rows": weights.get(name, 0),
            "extension_quota": quota.get(name, 0),
            "extension_selected": extension_counter.get(name, 0),
            "train_912_selected": train_counter.get(name, 0),
            "test_rows": test_counter.get(name, 0),
        }
        for name in sorted(set(primary_per_stratum) | set(extension_counter))
    }

    train_groups = Counter(item["group_id"] for item in train_items)
    test_groups = Counter(item["group_id"] for item in primary["test"])
    group = {
        "field": "source_id",
        "train_unique_source_id": len(train_groups),
        "train_max_rows_per_source_id": max(train_groups.values()) if train_groups else 0,
        "test_unique_source_id": len(test_groups),
        "test_rows_in_repeated_source_id": sum(
            count for count in test_groups.values() if count > 1
        ),
        "test_repeated_source_id": sum(1 for count in test_groups.values() if count > 1),
        "test_max_rows_per_source_id": max(test_groups.values()) if test_groups else 0,
        "train_test_source_id_intersection": len(set(train_groups) & set(test_groups)),
        "note": "at most one row per source_id across the entire 912",
    }

    statistics: dict[str, Any] = {
        "train_count": len(train_items),
        "test_count": len(primary["test"]),
        "train_budget": ROBUSTNESS_TRAIN_N,
        "parent_primary_budget": CALIBRATION_TRAIN_N,
        "role": ROBUSTNESS_ROLE,
        "stratum_field": "activity_label",
        "train_stratum_count": len(train_counter),
        "test_stratum_count": primary_stats["test_stratum_count"],
        "per_stratum": per_stratum,
        "allocation": (
            "nested residual extension: Hamilton / largest-remainder on the remaining "
            "eligible source-train row counts after removing the frozen primary-456 rows"
        ),
        "group": group,
        "anchor": {
            "train": _distribution([item["anchor_index"] for item in train_items]),
            "test": primary_stats["anchor"]["test"],
            "train_anchor_equals_ground_truth_fraction": (
                sum(item["anchor_index"] == item["ground_truth_index"] for item in train_items)
                / len(train_items)
            ),
            "test_anchor_equals_ground_truth_fraction": primary_stats["anchor"][
                "test_anchor_equals_ground_truth_fraction"
            ],
            "note": "structural diagnostic of the anchor rule; NOT a model accuracy",
        },
        "ground_truth": {
            "train": _distribution([item["ground_truth_index"] for item in train_items]),
            "test": primary_stats["ground_truth"]["test"],
            "note": "structural diagnostic only; never used to modify the selection rule",
        },
        "split_type": primary_stats["split_type"],
        "structural_exclusions": primary_stats["structural_exclusions"],
        "overlap_exclusions": {
            "extension_rows_excluded_by_test_overlap": overlap_excluded,
            "extension_rows_skipped_for_source_id_reuse": group_skipped,
        },
        "nestedness": nestedness,
    }

    return {
        "artifact": "r4-population-robustness912-candidate",
        "status": ROBUSTNESS_STATUS,
        "role": ROBUSTNESS_ROLE,
        "parent_primary_budget": CALIBRATION_TRAIN_N,
        "train_budget": ROBUSTNESS_TRAIN_N,
        "nested_primary": True,
        "parent_primary_manifest_fingerprint": fingerprint(primary),
        "parent_primary_train_item_id_fingerprint": fingerprint(
            [item["item_id"] for item in primary_train]
        ),
        "extension_protocol_id": EXTENSION_PROTOCOL_ID,
        "extension_protocol_version": EXTENSION_PROTOCOL_VERSION,
        "extension_count": len(extension),
        "extension_item_ids": [item["item_id"] for item in extension],
        "dataset_id": HELLASWAG_REPO,
        "dataset_revision": HELLASWAG_REVISION,
        "snapshot_path": str(snapshot_dir(HELLASWAG_REPO, HELLASWAG_REVISION)),
        "population_protocol_id": POPULATION_PROTOCOL_ID,
        "population_protocol_version": POPULATION_PROTOCOL_VERSION,
        "selection_protocol_id": SELECTION_PROTOCOL_ID,
        "selection_protocol_version": SELECTION_PROTOCOL_VERSION,
        "anchor_protocol_id": ANCHOR_PROTOCOL_ID,
        "anchor_protocol_version": ANCHOR_PROTOCOL_VERSION,
        "normalization": NORMALIZATION,
        "candidate_names": list(CANDIDATE_NAMES),
        "calibration_train_source_split": "train",
        "evaluation_test_source_split": "validation",
        "selection_rule": (
            primary["selection_rule"]
            + "; the 912 robustness TRAIN is the frozen primary 456 plus a nested "
            "residual extension selected with the same rank doctrine over the "
            "remaining eligible rows"
        ),
        "train": train_items,
        "test": primary["test"],
        "statistics": statistics,
    }


# --------------------------------------------------------------------------- #
# MedMCQA
# --------------------------------------------------------------------------- #


def _mm_options(row: dict[str, Any]) -> list[Any]:
    return [row["opa"], row["opb"], row["opc"], row["opd"]]


def _mm_eligible(row: dict[str, Any]) -> tuple[bool, str]:
    options = _mm_options(row)
    if any(not isinstance(option, str) or option.strip() == "" for option in options):
        return False, "option-missing-or-empty"
    if len({normalize_text(option) for option in options}) != 4:
        return False, "duplicate-option-string"
    if row["cop"] not in (0, 1, 2, 3):
        return False, "invalid-ground-truth"
    return True, "eligible"


def _mm_item(row: dict[str, Any], index: int, *, split: str) -> dict[str, Any]:
    source_split = "train" if split == "TRAIN" else "validation"
    return {
        "dataset_id": MEDMCQA_REPO,
        "dataset_revision": MEDMCQA_REVISION,
        "source_split": source_split,
        "source_row_index": index,
        "item_id": item_id(
            dataset_id=MEDMCQA_REPO,
            revision=MEDMCQA_REVISION,
            source_split=source_split,
            row_index=index,
        ),
        "split": split,
        "stratum": row["subject_name"],
        "group_id": None,
        "choice_type": row["choice_type"],
        "question": row["question"],
        "candidate_names": list(CANDIDATE_NAMES),
        "candidate_descriptions": _mm_options(row),
        "ground_truth_index": row["cop"],
        "anchor_index": anchor_index(
            dataset_id=MEDMCQA_REPO,
            revision=MEDMCQA_REVISION,
            source_split=source_split,
            row_index=index,
        ),
    }


def build_medmcqa() -> dict[str, Any]:
    train_rows = read_rows(MEDMCQA_REPO, MEDMCQA_REVISION, "train")
    val_rows = read_rows(MEDMCQA_REPO, MEDMCQA_REVISION, "validation")

    # TEST declared first and pristine: every structurally eligible validation row.
    test_items: list[dict[str, Any]] = []
    test_exclusions = Counter()
    for index, row in enumerate(val_rows):
        ok, reason = _mm_eligible(row)
        if not ok:
            test_exclusions[reason] += 1
            continue
        test_items.append(_mm_item(row, index, split="TEST"))
    test_keys = {
        (row["question"], tuple(_mm_options(row)))
        for row in val_rows
        if _mm_eligible(row)[0]
    }
    test_truth_by_key: dict[Any, set[Any]] = {}
    for row in val_rows:
        if _mm_eligible(row)[0]:
            test_truth_by_key.setdefault((row["question"], tuple(_mm_options(row))), set()).add(
                row["cop"]
            )

    pool: list[tuple[int, dict[str, Any]]] = []
    train_exclusions = Counter()
    for index, row in enumerate(train_rows):
        ok, reason = _mm_eligible(row)
        if not ok:
            train_exclusions[reason] += 1
            continue
        pool.append((index, row))

    weights = dict(Counter(row["subject_name"] for _, row in pool))
    quota = hamilton_quota(weights, CALIBRATION_TRAIN_N)

    by_stratum: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for index, row in pool:
        by_stratum.setdefault(row["subject_name"], []).append((index, row))
    for entries in by_stratum.values():
        entries.sort(
            key=lambda pair: (
                selection_rank(
                    dataset_id=MEDMCQA_REPO,
                    revision=MEDMCQA_REVISION,
                    source_split="train",
                    stratum=pair[1]["subject_name"],
                    row_index=pair[0],
                ),
                pair[0],
            )
        )

    train_items: list[dict[str, Any]] = []
    overlap_excluded = 0
    for name in sorted(by_stratum):
        need = quota.get(name, 0)
        taken = 0
        for index, row in by_stratum[name]:
            if taken >= need:
                break
            key = (row["question"], tuple(_mm_options(row)))
            if key in test_keys:
                truths = test_truth_by_key[key]
                if truths != {row["cop"]}:
                    raise PopulationError(
                        "cross-split question + ordered options duplicate with a "
                        f"conflicting ground truth (train source_row_index {index}); "
                        "STOP FOR HUMAN REVIEW"
                    )
                overlap_excluded += 1
                continue
            train_items.append(_mm_item(row, index, split="TRAIN"))
            taken += 1
        if taken < need:
            raise PopulationError(
                f"MedMCQA subject_name {name!r}: quota {need} not satisfiable "
                f"(selected {taken}); STOP / NEEDS_REVIEW"
            )

    train_stratum_counter = Counter(item["stratum"] for item in train_items)
    test_stratum_counter = Counter(item["stratum"] for item in test_items)
    per_stratum = {
        name: {
            "eligible_train_rows": weights.get(name, 0),
            "train_quota": quota.get(name, 0),
            "train_selected": train_stratum_counter.get(name, 0),
            "test_rows": test_stratum_counter.get(name, 0),
        }
        for name in sorted(set(weights) | set(test_stratum_counter))
    }

    train_choice_type = Counter(item["choice_type"] for item in train_items)
    test_choice_type = Counter(item["choice_type"] for item in test_items)
    train_excluded_choice_type = Counter(
        row["choice_type"] for row in train_rows if not _mm_eligible(row)[0]
    )
    test_excluded_choice_type = Counter(
        row["choice_type"] for row in val_rows if not _mm_eligible(row)[0]
    )

    statistics: dict[str, Any] = {
        "train_count": len(train_items),
        "test_count": len(test_items),
        "calibration_train_n": CALIBRATION_TRAIN_N,
        "stratum_field": "subject_name",
        "train_stratum_count": len(train_stratum_counter),
        "test_stratum_count": len(test_stratum_counter),
        "per_stratum": per_stratum,
        "allocation": "Hamilton / largest-remainder on eligible source-train row counts",
        "choice_type": {
            "train": {str(k): v for k, v in sorted(train_choice_type.items())},
            "test": {str(k): v for k, v in sorted(test_choice_type.items())},
        },
        "anchor": {
            "train": _distribution([item["anchor_index"] for item in train_items]),
            "test": _distribution([item["anchor_index"] for item in test_items]),
            "train_anchor_equals_ground_truth_fraction": (
                sum(item["anchor_index"] == item["ground_truth_index"] for item in train_items)
                / len(train_items)
            ),
            "test_anchor_equals_ground_truth_fraction": (
                sum(item["anchor_index"] == item["ground_truth_index"] for item in test_items)
                / len(test_items)
            ),
            "note": "structural diagnostic of the anchor rule; NOT a model accuracy",
        },
        "ground_truth": {
            "train": _distribution([item["ground_truth_index"] for item in train_items]),
            "test": _distribution([item["ground_truth_index"] for item in test_items]),
            "note": "structural diagnostic only; never used to modify the selection rule",
        },
        "structural_exclusions": {
            "train_rows": {
                "total": sum(train_exclusions.values()),
                "by_reason": {str(k): v for k, v in sorted(train_exclusions.items())},
                "duplicate_option_by_choice_type": {
                    str(k): v for k, v in sorted(train_excluded_choice_type.items())
                },
            },
            "test_rows": {
                "total": sum(test_exclusions.values()),
                "by_reason": {str(k): v for k, v in sorted(test_exclusions.items())},
                "duplicate_option_by_choice_type": {
                    str(k): v for k, v in sorted(test_excluded_choice_type.items())
                },
            },
        },
        "overlap_exclusions": {
            "train_rows_excluded_by_test_overlap": overlap_excluded,
        },
    }

    return {
        "artifact": "r4-population-construction-candidate",
        "status": STATUS,
        "dataset_id": MEDMCQA_REPO,
        "dataset_revision": MEDMCQA_REVISION,
        "snapshot_path": str(snapshot_dir(MEDMCQA_REPO, MEDMCQA_REVISION)),
        "population_protocol_id": POPULATION_PROTOCOL_ID,
        "population_protocol_version": POPULATION_PROTOCOL_VERSION,
        "selection_protocol_id": SELECTION_PROTOCOL_ID,
        "selection_protocol_version": SELECTION_PROTOCOL_VERSION,
        "anchor_protocol_id": ANCHOR_PROTOCOL_ID,
        "anchor_protocol_version": ANCHOR_PROTOCOL_VERSION,
        "normalization": NORMALIZATION,
        "candidate_names": list(CANDIDATE_NAMES),
        "calibration_train_source_split": "train",
        "evaluation_test_source_split": "validation",
        "selection_rule": (
            "per-subject_name Hamilton quota on structurally eligible train rows; within "
            "stratum ranked by selection_rank fingerprint; skip any row whose question + "
            "ordered options exactly duplicates a TEST row"
        ),
        "train": train_items,
        "test": test_items,
        "statistics": statistics,
    }


def build_medmcqa_robustness912() -> dict[str, Any]:
    """Nested secondary sample-size-robustness candidate (TRAIN 912, same TEST)."""
    primary = build_medmcqa()
    primary_train = primary["train"]
    primary_stats = primary["statistics"]

    train_rows = read_rows(MEDMCQA_REPO, MEDMCQA_REVISION, "train")
    val_rows = read_rows(MEDMCQA_REPO, MEDMCQA_REVISION, "validation")

    test_keys: set[Any] = set()
    test_truth_by_key: dict[Any, set[Any]] = {}
    for row in val_rows:
        if not _mm_eligible(row)[0]:
            continue
        key = (row["question"], tuple(_mm_options(row)))
        test_keys.add(key)
        test_truth_by_key.setdefault(key, set()).add(row["cop"])

    used_indices = {item["source_row_index"] for item in primary_train}

    remaining = [
        (index, row)
        for index, row in enumerate(train_rows)
        if _mm_eligible(row)[0] and index not in used_indices
    ]
    weights = dict(Counter(row["subject_name"] for _, row in remaining))
    quota = hamilton_quota(weights, ROBUSTNESS_EXTENSION_N)
    ranked = _rank_entries(
        remaining,
        dataset_id=MEDMCQA_REPO,
        revision=MEDMCQA_REVISION,
        stratum_of=lambda row: row["subject_name"],
    )
    selected, overlap_excluded, _ = _stratified_select(
        ranked,
        quota,
        test_keys=test_keys,
        key_of=lambda row: (row["question"], tuple(_mm_options(row))),
        group_of=lambda row: None,
        used_groups=set(),
        used_indices=used_indices,
        label="MedMCQA extension subject_name",
        test_truth_by_key=test_truth_by_key,
        truth_of=lambda row: row["cop"],
    )
    extension = [_mm_item(row, index, split="TRAIN") for index, row in selected]
    train_items = primary_train + extension
    nestedness = _nestedness_audit(primary_train, train_items)

    primary_counter = Counter(item["stratum"] for item in primary_train)
    extension_counter = Counter(item["stratum"] for item in extension)
    train_counter = Counter(item["stratum"] for item in train_items)
    test_counter = Counter(item["stratum"] for item in primary["test"])
    primary_per_stratum = primary_stats["per_stratum"]
    per_stratum = {
        name: {
            "eligible_train_rows": primary_per_stratum.get(name, {}).get(
                "eligible_train_rows", 0
            ),
            "primary_train_selected": primary_counter.get(name, 0),
            "eligible_remaining_rows": weights.get(name, 0),
            "extension_quota": quota.get(name, 0),
            "extension_selected": extension_counter.get(name, 0),
            "train_912_selected": train_counter.get(name, 0),
            "test_rows": test_counter.get(name, 0),
        }
        for name in sorted(set(primary_per_stratum) | set(extension_counter))
    }

    train_choice_type = Counter(item["choice_type"] for item in train_items)
    test_choice_type = Counter(item["choice_type"] for item in primary["test"])
    extension_choice_type = Counter(item["choice_type"] for item in extension)

    statistics: dict[str, Any] = {
        "train_count": len(train_items),
        "test_count": len(primary["test"]),
        "train_budget": ROBUSTNESS_TRAIN_N,
        "parent_primary_budget": CALIBRATION_TRAIN_N,
        "role": ROBUSTNESS_ROLE,
        "stratum_field": "subject_name",
        "train_stratum_count": len(train_counter),
        "test_stratum_count": primary_stats["test_stratum_count"],
        "per_stratum": per_stratum,
        "allocation": (
            "nested residual extension: Hamilton / largest-remainder on the remaining "
            "eligible source-train row counts after removing the frozen primary-456 rows"
        ),
        "choice_type": {
            "train": {str(k): v for k, v in sorted(train_choice_type.items())},
            "test": {str(k): v for k, v in sorted(test_choice_type.items())},
            "extension": {str(k): v for k, v in sorted(extension_choice_type.items())},
        },
        "anchor": {
            "train": _distribution([item["anchor_index"] for item in train_items]),
            "test": primary_stats["anchor"]["test"],
            "train_anchor_equals_ground_truth_fraction": (
                sum(item["anchor_index"] == item["ground_truth_index"] for item in train_items)
                / len(train_items)
            ),
            "test_anchor_equals_ground_truth_fraction": primary_stats["anchor"][
                "test_anchor_equals_ground_truth_fraction"
            ],
            "note": "structural diagnostic of the anchor rule; NOT a model accuracy",
        },
        "ground_truth": {
            "train": _distribution([item["ground_truth_index"] for item in train_items]),
            "test": primary_stats["ground_truth"]["test"],
            "note": "structural diagnostic only; never used to modify the selection rule",
        },
        "structural_exclusions": primary_stats["structural_exclusions"],
        "overlap_exclusions": {
            "extension_rows_excluded_by_test_overlap": overlap_excluded,
        },
        "nestedness": nestedness,
    }

    return {
        "artifact": "r4-population-robustness912-candidate",
        "status": ROBUSTNESS_STATUS,
        "role": ROBUSTNESS_ROLE,
        "parent_primary_budget": CALIBRATION_TRAIN_N,
        "train_budget": ROBUSTNESS_TRAIN_N,
        "nested_primary": True,
        "parent_primary_manifest_fingerprint": fingerprint(primary),
        "parent_primary_train_item_id_fingerprint": fingerprint(
            [item["item_id"] for item in primary_train]
        ),
        "extension_protocol_id": EXTENSION_PROTOCOL_ID,
        "extension_protocol_version": EXTENSION_PROTOCOL_VERSION,
        "extension_count": len(extension),
        "extension_item_ids": [item["item_id"] for item in extension],
        "dataset_id": MEDMCQA_REPO,
        "dataset_revision": MEDMCQA_REVISION,
        "snapshot_path": str(snapshot_dir(MEDMCQA_REPO, MEDMCQA_REVISION)),
        "population_protocol_id": POPULATION_PROTOCOL_ID,
        "population_protocol_version": POPULATION_PROTOCOL_VERSION,
        "selection_protocol_id": SELECTION_PROTOCOL_ID,
        "selection_protocol_version": SELECTION_PROTOCOL_VERSION,
        "anchor_protocol_id": ANCHOR_PROTOCOL_ID,
        "anchor_protocol_version": ANCHOR_PROTOCOL_VERSION,
        "normalization": NORMALIZATION,
        "candidate_names": list(CANDIDATE_NAMES),
        "calibration_train_source_split": "train",
        "evaluation_test_source_split": "validation",
        "selection_rule": (
            primary["selection_rule"]
            + "; the 912 robustness TRAIN is the frozen primary 456 plus a nested "
            "residual extension selected with the same rank doctrine over the "
            "remaining eligible rows"
        ),
        "train": train_items,
        "test": primary["test"],
        "statistics": statistics,
    }


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = (
        ("hellaswag", build_hellaswag, "hellaswag_population_candidate.json"),
        ("medmcqa", build_medmcqa, "medmcqa_population_candidate.json"),
        (
            "hellaswag",
            build_hellaswag_robustness912,
            "hellaswag_population_robustness912_candidate.json",
        ),
        (
            "medmcqa",
            build_medmcqa_robustness912,
            "medmcqa_population_robustness912_candidate.json",
        ),
    )
    for name, builder, filename in outputs:
        payload = builder()
        payload["manifest_fingerprint"] = fingerprint(payload)
        if filename.endswith("_population_candidate.json"):
            expected = EXPECTED_PRIMARY_MANIFEST_FINGERPRINT[name]
            if payload["manifest_fingerprint"] != expected:
                raise PopulationError(
                    f"{name} primary manifest fingerprint drifted "
                    f"({payload['manifest_fingerprint']} != {expected}); BLOCKED"
                )
        text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
        (OUT_DIR / filename).write_text(text, encoding="utf-8")
        print(f"{filename}: train={len(payload['train'])} test={len(payload['test'])}")
        print(f"{filename}: manifest_fingerprint={payload['manifest_fingerprint']}")
        print(f"{filename}: file_sha256={_sha256(text)}")
        print(f"{filename}: bytes={len(text.encode('utf-8'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
