"""R4 HellaSwag + MedMCQA dataset semantic-closure audit (structural only).

This is a DATASET STRUCTURAL / SEMANTIC gate. It is NOT a population manifest,
NOT a TRAIN/TEST freeze, and NOT an execution authorization.

What it does:
  * reads the exact-revision pinned local parquet snapshots of ``Rowan/hellaswag``
    and ``openlifescienceai/medmcqa``;
  * mechanically counts splits, schema, choice geometry, ground-truth validity,
    label balance, strata capacity, duplicates and cross-split overlap;
  * simulates ONE predeclared measurement-independent fixed-event anchor rule and
    reports its distribution as a structural diagnostic.

Hard prohibitions enforced here:
  * NO model / tokenizer import, NO GPU, NO forward, NO generation;
  * NO accuracy / Brier / LogLoss / calibration / transport / predictor outcome;
  * the anchor rule never sees a label, ground truth, question text, option text,
    or any model output;
  * only raw-exact and conservative-normalized exact keys are used (no case
    folding, no stemming, no fuzzy/embedding dedup).

Run:
    PYTHONPATH=/root/rivermind-data/r4-dataset-audit/pylibs \\
    /root/rivermind-data/envs/probvenance-r4/bin/python \\
        experiments/calibration_transport/r4_dataset_semantic_audit.py
"""

from __future__ import annotations

import json
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from probvenance.fingerprint import fingerprint

DATASETS_ROOT = Path("/root/rivermind-data/r4-datasets")
OUT_DIR = Path("/root/rivermind-data/r4-dataset-audit")

HELLASWAG_REPO = "Rowan/hellaswag"
HELLASWAG_REVISION = "218ec52e09a7e7462a5400043bb9a69a41d06b76"
MEDMCQA_REPO = "openlifescienceai/medmcqa"
MEDMCQA_REVISION = "91c6572c454088bf71b679ad90aa8dffcd0d5868"

# Predeclared fixed-event anchor feasibility rule (EXACTLY ONE rule is tested).
ANCHOR_PROTOCOL_ID = "r4-fixed-event-anchor-deterministic-source-index-hash"
ANCHOR_PROTOCOL_VERSION = 1

CAPACITY_THRESHOLDS = (5, 10, 20, 40)
SPARSE_THRESHOLDS = (5, 10, 20)
EXAMPLE_COUNT = 20


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def normalize_text(value: str) -> str:
    """Conservative exact normalization: NFC + newline normalization + outer strip.

    Deliberately no case folding, no punctuation removal, no semantic/fuzzy match.
    """
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    return unicodedata.normalize("NFC", text).strip()


def quantile(sorted_values: list[int], fraction: float) -> float:
    """Linear-interpolation quantile on an already sorted list (deterministic)."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    position = fraction * (len(sorted_values) - 1)
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def describe_sizes(counts: list[int]) -> dict[str, Any]:
    ordered = sorted(counts)
    total = len(ordered)
    out: dict[str, Any] = {
        "unique_strata": total,
        "min": ordered[0] if ordered else 0,
        "q1": quantile(ordered, 0.25),
        "median": quantile(ordered, 0.5),
        "q3": quantile(ordered, 0.75),
        "max": ordered[-1] if ordered else 0,
    }
    for threshold in SPARSE_THRESHOLDS:
        below = sum(1 for value in ordered if value < threshold)
        out[f"count_lt_{threshold}"] = below
        out[f"fraction_lt_{threshold}"] = (below / total) if total else 0.0
    return out


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


def duplicate_stats(keys: list[tuple[Any, ...]]) -> dict[str, Any]:
    counter = Counter(keys)
    duplicated = {key: count for key, count in counter.items() if count > 1}
    return {
        "rows": len(keys),
        "unique_keys": len(counter),
        "duplicate_keys": len(duplicated),
        "duplicate_rows": sum(duplicated.values()),
        "max_multiplicity": max(counter.values()) if counter else 0,
    }


def snapshot_dir(repo: str, revision: str) -> Path:
    return DATASETS_ROOT / f"datasets--{repo.replace('/', '--')}" / "snapshots" / revision


def read_rows(repo: str, revision: str, split: str) -> list[dict[str, Any]]:
    path = snapshot_dir(repo, revision) / "data" / f"{split}-00000-of-00001.parquet"
    table = pq.read_table(path)
    return table.to_pylist()


# --------------------------------------------------------------------------- #
# HellaSwag
# --------------------------------------------------------------------------- #


def _hs_item_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (row["ctx"], tuple(row["endings"]))


def _hs_norm_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (normalize_text(row["ctx"]), tuple(normalize_text(e) for e in row["endings"]))


def audit_hellaswag() -> dict[str, Any]:
    splits = ("train", "validation", "test")
    rows = {split: read_rows(HELLASWAG_REPO, HELLASWAG_REVISION, split) for split in splits}
    out: dict[str, Any] = {
        "artifact": "r4-dataset-semantic-audit",
        "dataset": "hellaswag",
        "repo_id": HELLASWAG_REPO,
        "revision": HELLASWAG_REVISION,
        "snapshot_path": str(snapshot_dir(HELLASWAG_REPO, HELLASWAG_REVISION)),
        "normalization": "NFC + CRLF/CR->LF + outer strip (raw-exact variant also reported)",
        "split_census": {split: len(rows[split]) for split in splits},
    }

    schema = pq.read_schema(
        snapshot_dir(HELLASWAG_REPO, HELLASWAG_REVISION) / "data" / "train-00000-of-00001.parquet"
    )
    out["schema"] = {field.name: str(field.type) for field in schema}

    # choice geometry
    geometry: dict[str, Any] = {}
    non_four: list[dict[str, Any]] = []
    for split in splits:
        counter = Counter(len(row["endings"]) for row in rows[split])
        geometry[split] = {str(k): v for k, v in sorted(counter.items())}
        for index, row in enumerate(rows[split]):
            if len(row["endings"]) != 4:
                non_four.append(
                    {
                        "split": split,
                        "source_row_index": index,
                        "source_id": row.get("source_id"),
                        "ending_count": len(row["endings"]),
                    }
                )
    out["choice_geometry"] = geometry
    out["choice_geometry_non_four"] = non_four

    # ground truth
    truth: dict[str, Any] = {}
    for split in splits:
        labels = [row["label"] for row in rows[split]]
        parsed = Counter()
        invalid = 0
        empty = 0
        for label in labels:
            text = label.strip()
            if text == "":
                empty += 1
                continue
            try:
                value = int(text)
            except ValueError:
                invalid += 1
                continue
            parsed[value if 0 <= value <= 3 else "out_of_range"] += 1
        truth[split] = {
            "rows": len(labels),
            "empty_label": empty,
            "unparseable_label": invalid,
            "label_counts": {
                str(k): v
                for k, v in sorted(parsed.items(), key=lambda kv: str(kv[0]))
            },
        }
    out["ground_truth"] = truth

    # label balance + anchor diagnostic (labeled splits only)
    balance: dict[str, Any] = {}
    anchor: dict[str, Any] = {}
    for split in ("train", "validation"):
        label_counter = Counter(int(row["label"]) for row in rows[split])
        balance[split] = {
            "counts": {str(k): label_counter.get(k, 0) for k in range(4)},
            "fractions": {str(k): label_counter.get(k, 0) / len(rows[split]) for k in range(4)},
        }
        anchor_counter = Counter()
        match = 0
        for index, row in enumerate(rows[split]):
            value = anchor_index(
                dataset_id=HELLASWAG_REPO,
                revision=HELLASWAG_REVISION,
                source_split=split,
                row_index=index,
            )
            anchor_counter[value] += 1
            match += int(value == int(row["label"]))
        anchor[split] = {
            "counts": {str(k): anchor_counter.get(k, 0) for k in range(4)},
            "fractions": {str(k): anchor_counter.get(k, 0) / len(rows[split]) for k in range(4)},
            "anchor_equals_ground_truth_fraction": match / len(rows[split]),
            "note": "structural diagnostic of the anchor rule; NOT a model accuracy",
        }
    out["label_balance"] = balance
    out["anchor_feasibility"] = anchor

    # strata
    strata: dict[str, Any] = {}
    for field in ("activity_label", "split_type"):
        per_split: dict[str, Any] = {}
        for split in splits:
            counter = Counter(row[field] for row in rows[split])
            per_split[split] = describe_sizes(list(counter.values()))
        strata[field] = per_split
    out["strata"] = strata
    out["split_type_values"] = {
        split: {str(k): v for k, v in sorted(Counter(r["split_type"] for r in rows[split]).items())}
        for split in splits
    }

    # activity_label x split_type cells (validation, and train for reference)
    cells: dict[str, Any] = {}
    for split in ("train", "validation"):
        counter = Counter((row["activity_label"], row["split_type"]) for row in rows[split])
        sizes = sorted(counter.values())
        cells[split] = {
            "cells": len(counter),
            "min": sizes[0] if sizes else 0,
            "median": quantile(sizes, 0.5),
            "max": sizes[-1] if sizes else 0,
            "cells_lt_5": sum(1 for value in sizes if value < 5),
            "cells_lt_10": sum(1 for value in sizes if value < 10),
        }
    out["activity_x_split_type_cells"] = cells

    # duplicates within split
    duplicates: dict[str, Any] = {}
    for split in splits:
        raw_keys = [_hs_item_key(row) for row in rows[split]]
        norm_keys = [_hs_norm_key(row) for row in rows[split]]
        source_ids = [row["source_id"] for row in rows[split]]
        source_counter = Counter(source_ids)
        duplicates[split] = {
            "raw_exact_item": duplicate_stats(raw_keys),
            "normalized_exact_item": duplicate_stats(norm_keys),
            "source_id": {
                "rows": len(source_ids),
                "unique_source_id": len(source_counter),
                "repeated_source_id": sum(1 for v in source_counter.values() if v > 1),
                "rows_in_repeated_source_id": sum(v for v in source_counter.values() if v > 1),
                "max_rows_per_source_id": max(source_counter.values()) if source_counter else 0,
            },
        }
    out["duplicates"] = duplicates

    # cross-split overlap train vs validation
    out["cross_split_overlap"] = _hs_overlap(rows["train"], rows["validation"])

    # conflicting-label duplicates inside train and inside validation
    out["conflicting_label_duplicates"] = {
        split: _hs_conflicts(rows[split]) for split in ("train", "validation")
    }

    # capacity
    out["strata_capacity"] = {
        field: _capacity(rows, field) for field in ("activity_label", "split_type")
    }

    # activity_label intersection
    train_labels = {row["activity_label"] for row in rows["train"]}
    val_labels = {row["activity_label"] for row in rows["validation"]}
    train_counter = Counter(row["activity_label"] for row in rows["train"])
    val_counter = Counter(row["activity_label"] for row in rows["validation"])
    shared = sorted(train_labels & val_labels)
    out["activity_label_intersection"] = {
        "train_unique": len(train_labels),
        "validation_unique": len(val_labels),
        "intersection": len(shared),
        "train_only": len(train_labels - val_labels),
        "validation_only": len(val_labels - train_labels),
        "shared_strata_min_train_count": min((train_counter[s] for s in shared), default=0),
        "shared_strata_min_validation_count": min((val_counter[s] for s in shared), default=0),
        "shared_strata": {
            name: {"train": train_counter[name], "validation": val_counter[name]}
            for name in shared
        },
        "train_only_labels": sorted(train_labels - val_labels),
        "validation_only_labels": sorted(val_labels - train_labels),
    }

    out["grouping_note"] = (
        "source_id groups rows that share a source context/video instance; "
        "no group-aware decision is made here"
    )
    return out


def _hs_overlap(train_rows: list[dict[str, Any]], val_rows: list[dict[str, Any]]) -> dict[str, Any]:
    def index(rows: list[dict[str, Any]], key_fn) -> dict[Any, list[int]]:
        result: dict[Any, list[int]] = {}
        for position, row in enumerate(rows):
            result.setdefault(key_fn(row), []).append(position)
        return result

    def conflict_report(train_index, val_index, labels_train, labels_val) -> dict[str, Any]:
        shared = sorted(set(train_index) & set(val_index), key=repr)
        same = 0
        conflict = 0
        for key in shared:
            train_labels = {labels_train[p] for p in train_index[key]}
            val_labels = {labels_val[p] for p in val_index[key]}
            if train_labels == val_labels:
                same += 1
            else:
                conflict += 1
        return {
            "shared_keys": len(shared),
            "shared_keys_same_label": same,
            "shared_keys_conflicting_label": conflict,
            "train_rows_involved": sum(len(train_index[k]) for k in shared),
            "validation_rows_involved": sum(len(val_index[k]) for k in shared),
        }

    train_labels = [int(r["label"]) for r in train_rows]
    val_labels = [int(r["label"]) for r in val_rows]

    item = conflict_report(
        index(train_rows, _hs_item_key), index(val_rows, _hs_item_key), train_labels, val_labels
    )
    norm = conflict_report(
        index(train_rows, _hs_norm_key), index(val_rows, _hs_norm_key), train_labels, val_labels
    )
    source = conflict_report(
        index(train_rows, lambda r: r["source_id"]),
        index(val_rows, lambda r: r["source_id"]),
        train_labels,
        val_labels,
    )
    return {
        "A_raw_exact_item": item,
        "B_source_id": source,
        "C_normalized_exact_item": norm,
    }


def _hs_conflicts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    seen: dict[Any, set[int]] = {}
    first_index: dict[Any, int] = {}
    for position, row in enumerate(rows):
        seen.setdefault(_hs_item_key(row), set()).add(int(row["label"]))
        first_index.setdefault(_hs_item_key(row), position)
    conflicting = [key for key, labels in seen.items() if len(labels) > 1]
    return {
        "duplicate_keys_with_conflicting_label": len(conflicting),
        "example_source_row_indexes": sorted(first_index[key] for key in conflicting[:5]),
    }


# --------------------------------------------------------------------------- #
# MedMCQA
# --------------------------------------------------------------------------- #


def _mm_item_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (row["question"], row["opa"], row["opb"], row["opc"], row["opd"])


def _mm_norm_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(normalize_text(row[field]) for field in ("question", "opa", "opb", "opc", "opd"))


def audit_medmcqa() -> dict[str, Any]:
    splits = ("train", "validation", "test")
    rows = {split: read_rows(MEDMCQA_REPO, MEDMCQA_REVISION, split) for split in splits}
    out: dict[str, Any] = {
        "artifact": "r4-dataset-semantic-audit",
        "dataset": "medmcqa",
        "repo_id": MEDMCQA_REPO,
        "revision": MEDMCQA_REVISION,
        "snapshot_path": str(snapshot_dir(MEDMCQA_REPO, MEDMCQA_REVISION)),
        "normalization": "NFC + CRLF/CR->LF + outer strip (raw-exact variant also reported)",
        "split_census": {split: len(rows[split]) for split in splits},
    }

    schema = pq.read_schema(
        snapshot_dir(MEDMCQA_REPO, MEDMCQA_REVISION) / "data" / "train-00000-of-00001.parquet"
    )
    out["schema"] = {field.name: str(field.type) for field in schema}

    # choice geometry / option integrity
    geometry: dict[str, Any] = {}
    for split in splits:
        missing = 0
        empty = 0
        duplicate_within = 0
        for row in rows[split]:
            options = [row["opa"], row["opb"], row["opc"], row["opd"]]
            if any(option is None for option in options):
                missing += 1
            if any(option is not None and option.strip() == "" for option in options):
                empty += 1
            if len({normalize_text(o) for o in options if o is not None}) != 4:
                duplicate_within += 1
        geometry[split] = {
            "rows": len(rows[split]),
            "missing_option": missing,
            "empty_option": empty,
            "duplicate_options_within_item": duplicate_within,
            "declared_option_count": 4,
        }
    out["choice_geometry"] = geometry

    # ground truth
    truth: dict[str, Any] = {}
    for split in splits:
        counter = Counter(row["cop"] for row in rows[split])
        invalid = sum(v for k, v in counter.items() if k not in (0, 1, 2, 3))
        truth[split] = {
            "rows": len(rows[split]),
            "cop_counts": {str(k): v for k, v in sorted(counter.items())},
            "cop_not_in_0_3": invalid,
        }
    out["ground_truth"] = truth

    # choice_type
    out["choice_type"] = {
        split: {
            str(k): v
            for k, v in sorted(Counter(r["choice_type"] for r in rows[split]).items())
        }
        for split in splits
    }

    # anchor diagnostic
    anchor: dict[str, Any] = {}
    for split in ("train", "validation"):
        counter = Counter()
        match = 0
        for index, row in enumerate(rows[split]):
            value = anchor_index(
                dataset_id=MEDMCQA_REPO,
                revision=MEDMCQA_REVISION,
                source_split=split,
                row_index=index,
            )
            counter[value] += 1
            match += int(value == row["cop"])
        anchor[split] = {
            "counts": {str(k): counter.get(k, 0) for k in range(4)},
            "fractions": {str(k): counter.get(k, 0) / len(rows[split]) for k in range(4)},
            "anchor_equals_ground_truth_fraction": match / len(rows[split]),
            "note": "structural diagnostic of the anchor rule; NOT a model accuracy",
        }
    out["anchor_feasibility"] = anchor

    # strata
    out["strata"] = {
        field: {
            split: describe_sizes(list(Counter(r[field] for r in rows[split]).values()))
            for split in splits
        }
        for field in ("subject_name", "topic_name")
    }
    out["strata_capacity"] = {
        field: _capacity(rows, field) for field in ("subject_name", "topic_name")
    }

    # duplicates within split
    out["duplicates"] = {
        split: {
            "raw_exact_item": duplicate_stats([_mm_item_key(r) for r in rows[split]]),
            "normalized_exact_item": duplicate_stats([_mm_norm_key(r) for r in rows[split]]),
            "question_only_raw": duplicate_stats([r["question"] for r in rows[split]]),
        }
        for split in splits
    }

    # cross-split overlap train vs validation
    out["cross_split_overlap"] = _mm_overlap(rows["train"], rows["validation"])

    # subject intersection
    train_subjects = {r["subject_name"] for r in rows["train"]}
    val_subjects = {r["subject_name"] for r in rows["validation"]}
    train_counter = Counter(r["subject_name"] for r in rows["train"])
    val_counter = Counter(r["subject_name"] for r in rows["validation"])
    shared = sorted(train_subjects & val_subjects)
    out["subject_intersection"] = {
        "train_unique": len(train_subjects),
        "validation_unique": len(val_subjects),
        "intersection": len(shared),
        "train_only": sorted(train_subjects - val_subjects),
        "validation_only": sorted(val_subjects - train_subjects),
        "shared_strata": {
            name: {"train": train_counter[name], "validation": val_counter[name]}
            for name in shared
        },
    }

    # deterministic examples for human semantic review of choice_type=multi
    out["choice_type_examples"] = {
        "multi": _mm_examples(rows["train"], "multi", EXAMPLE_COUNT),
        "single": _mm_examples(rows["train"], "single", EXAMPLE_COUNT),
    }
    out["grouping_note"] = (
        "id / subject_name / topic_name: no source-group identifier identified beyond "
        "subject/topic taxonomy; no grouping invented"
    )
    return out


def _mm_overlap(train_rows: list[dict[str, Any]], val_rows: list[dict[str, Any]]) -> dict[str, Any]:
    train_index: dict[Any, list[int]] = {}
    val_index: dict[Any, list[int]] = {}
    for position, row in enumerate(train_rows):
        train_index.setdefault(_mm_item_key(row), []).append(position)
    for position, row in enumerate(val_rows):
        val_index.setdefault(_mm_item_key(row), []).append(position)
    shared = sorted(set(train_index) & set(val_index), key=repr)
    same_label = 0
    conflict = 0
    for key in shared:
        train_labels = {train_rows[p]["cop"] for p in train_index[key]}
        val_labels = {val_rows[p]["cop"] for p in val_index[key]}
        if train_labels == val_labels:
            same_label += 1
        else:
            conflict += 1

    train_questions: dict[Any, list[int]] = {}
    val_questions: dict[Any, list[int]] = {}
    for position, row in enumerate(train_rows):
        train_questions.setdefault(row["question"], []).append(position)
    for position, row in enumerate(val_rows):
        val_questions.setdefault(row["question"], []).append(position)
    shared_questions = sorted(set(train_questions) & set(val_questions), key=repr)
    options_differ = 0
    for key in shared_questions:
        train_options = {_mm_item_key(train_rows[p])[1:] for p in train_questions[key]}
        val_options = {_mm_item_key(val_rows[p])[1:] for p in val_questions[key]}
        if train_options != val_options:
            options_differ += 1

    return {
        "raw_exact_item": {
            "shared_keys": len(shared),
            "shared_keys_same_label": same_label,
            "shared_keys_conflicting_label": conflict,
            "train_rows_involved": sum(len(train_index[k]) for k in shared),
            "validation_rows_involved": sum(len(val_index[k]) for k in shared),
        },
        "question_only_exact": {
            "shared_questions": len(shared_questions),
            "shared_questions_options_differ": options_differ,
        },
    }


def _mm_examples(rows: list[dict[str, Any]], choice_type: str, count: int) -> list[dict[str, Any]]:
    selected = [
        (index, row)
        for index, row in enumerate(rows)
        if row["choice_type"] == choice_type
    ]
    selected.sort(
        key=lambda pair: (
            fingerprint(
                {
                    "dataset_revision": MEDMCQA_REVISION,
                    "source_split": "train",
                    "source_row_index": pair[0],
                    "purpose": "choice-type-example-selection",
                }
            ),
            pair[0],
        )
    )
    return [
        {
            "source_row_index": index,
            "id": row["id"],
            "choice_type": row["choice_type"],
            "cop": row["cop"],
            "question": row["question"],
            "options": [row["opa"], row["opb"], row["opc"], row["opd"]],
            "subject_name": row["subject_name"],
            "topic_name": row["topic_name"],
        }
        for index, row in selected[:count]
    ]


# --------------------------------------------------------------------------- #
# shared capacity helper
# --------------------------------------------------------------------------- #


def _capacity(rows: dict[str, list[dict[str, Any]]], field: str) -> dict[str, Any]:
    counters = {
        split: Counter(row[field] for row in split_rows) for split, split_rows in rows.items()
    }
    train_values = list(counters.get("train", Counter()).values())
    validation_values = list(counters.get("validation", Counter()).values())
    result: dict[str, Any] = {}
    for threshold in CAPACITY_THRESHOLDS:
        result[f"N={threshold}"] = {
            "train_strata_supported": sum(1 for value in train_values if value >= threshold),
            "validation_strata_supported": sum(
                1 for value in validation_values if value >= threshold
            ),
        }
    result["train_strata_total"] = len(train_values)
    result["validation_strata_total"] = len(validation_values)
    return result


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, payload in (
        ("hellaswag", audit_hellaswag()),
        ("medmcqa", audit_medmcqa()),
    ):
        target = OUT_DIR / f"{name}_semantic_audit.json"
        target.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
            encoding="utf-8",
        )
        print(f"wrote {target} ({target.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
