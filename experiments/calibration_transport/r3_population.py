"""R3 confirmatory population: the frozen MMLU 57-subject manifest.

This module materializes the untouched confirmatory population for R3 from the
pinned ``cais/mmlu`` source archive. It is research-only and adds no project
dependency: the source archive is read with the standard library (``tarfile`` +
``csv``).

Design invariants (see ``R3_PROTOCOL.md`` and Research Specification v2):

- The 57 canonical MMLU subjects are all included; no subject is chosen by
  model behaviour, difficulty, or R2 similarity.
- ``validation`` is the calibration TRAIN source and ``test`` is the
  confirmatory TEST source. ``dev`` and ``auxiliary_train`` are unused.
- Selection has two stages, kept separate:

  * Stage A (primary deterministic rank). The ranking key depends only on the
    selection protocol id/version, the dataset revision, the subject, the
    source split, and the source row index. It is content-independent: it never
    depends on the answer, the question text, the choice text, the ground
    truth, or any model output.
  * Stage B (cross-split exact-duplicate guard). After TEST is selected and
    frozen, each TRAIN candidate is checked against the selected TEST items
    using the exact question plus the exact ordered choices only. A candidate
    that duplicates a selected TEST item is ineligible for TRAIN and is skipped
    in favour of the next-ranked validation candidate from the same subject.
    The guard never uses the answer, the anchor, the ground truth label, any
    model output, or any measurement score. If a candidate shares question +
    ordered choices with a selected TEST item but disagrees on the answer, the
    build stops for human review rather than silently deduplicating.
- Item ids are opaque with respect to the answer.
- The manifest is frozen before any R3 model outcome exists; validation runs
  offline against the committed manifest file.

The frozen per-subject TRAIN count is **8**, not 10: two of the 57 MMLU
subjects (``college_chemistry`` validation = 8 and
``high_school_computer_science`` validation = 9) cannot supply 10 validation
rows. This is an explicit, human-approved, non-silent deviation from the
originally drafted 10/subject; TEST remains 20/subject.
"""

from __future__ import annotations

import csv
import io
import json
import sys
import tarfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from probvenance.fingerprint import fingerprint

_HARNESS_DIR = Path(__file__).resolve().parent
_DEFAULT_DATA_DIR = _HARNESS_DIR / "data"

MMLU_REPOSITORY = "cais/mmlu"
MMLU_REVISION = "c30699e8356da336a370243923dbaf21066bb9fe"
MMLU_LICENSE = "MIT"
MMLU_SOURCE_ARCHIVE = "data.tar"
MMLU_SOURCE_URL = f"https://huggingface.co/datasets/{MMLU_REPOSITORY}/tree/{MMLU_REVISION}"

R3_POPULATION_MANIFEST_ARTIFACT_TYPE = "r3-mmlu-confirmatory-population-manifest"
R3_POPULATION_MANIFEST_VERSION = 1
R3_POPULATION_MANIFEST_FINGERPRINT_VERSION = 1
R3_POPULATION_ID = "r3-mmlu-57-subject-confirmatory"
R3_POPULATION_VERSION = 1

R3_SELECTION_PROTOCOL_ID = "mmlu-subject-balanced-source-index-hash-selection"
R3_SELECTION_PROTOCOL_VERSION = 1
R3_SELECTION_RULE = (
    "sort each subject x source-split rows by "
    "fingerprint(protocol_id, protocol_version, dataset_revision, subject, "
    "source_split, source_row_index) and take the first N; no RNG, no seed"
)
R3_OVERLAP_EXCLUSION_RULE = (
    "TEST is selected first (pristine); TRAIN then excludes any validation row "
    "whose question+choices content equals a selected TEST item and takes the "
    "first N remaining rows by rank (MMLU validation/test source overlap)"
)

R3_TRAIN_SOURCE_SPLIT = "validation"
R3_TEST_SOURCE_SPLIT = "test"
R3_UNUSED_SOURCE_SPLITS = ("dev", "auxiliary_train")

# Human-approved frozen counts. TRAIN=8 (not 10) because two subjects lack 10
# validation rows; TEST=20 is feasible for every subject.
R3_TRAIN_PER_SUBJECT = 8
R3_TEST_PER_SUBJECT = 20
R3_AUDIT_PER_SUBJECT = 0

R3_ANSWER_LABELS = ("A", "B", "C", "D")
R3_CANDIDATE_NAMES = ("option-0", "option-1", "option-2", "option-3")

R3_SPLIT_TRAIN = "TRAIN"
R3_SPLIT_TEST = "TEST"

_MMLU_CSV_DIRECTORY = {
    R3_TRAIN_SOURCE_SPLIT: "val",
    R3_TEST_SOURCE_SPLIT: "test",
    "dev": "dev",
}

MMLU_SUBJECTS: tuple[str, ...] = (
    "abstract_algebra",
    "anatomy",
    "astronomy",
    "business_ethics",
    "clinical_knowledge",
    "college_biology",
    "college_chemistry",
    "college_computer_science",
    "college_mathematics",
    "college_medicine",
    "college_physics",
    "computer_security",
    "conceptual_physics",
    "econometrics",
    "electrical_engineering",
    "elementary_mathematics",
    "formal_logic",
    "global_facts",
    "high_school_biology",
    "high_school_chemistry",
    "high_school_computer_science",
    "high_school_european_history",
    "high_school_geography",
    "high_school_government_and_politics",
    "high_school_macroeconomics",
    "high_school_mathematics",
    "high_school_microeconomics",
    "high_school_physics",
    "high_school_psychology",
    "high_school_statistics",
    "high_school_us_history",
    "high_school_world_history",
    "human_aging",
    "human_sexuality",
    "international_law",
    "jurisprudence",
    "logical_fallacies",
    "machine_learning",
    "management",
    "marketing",
    "medical_genetics",
    "miscellaneous",
    "moral_disputes",
    "moral_scenarios",
    "nutrition",
    "philosophy",
    "prehistory",
    "professional_accounting",
    "professional_law",
    "professional_medicine",
    "professional_psychology",
    "public_relations",
    "security_studies",
    "sociology",
    "us_foreign_policy",
    "virology",
    "world_religions",
)

DEFAULT_MANIFEST_PATH = _DEFAULT_DATA_DIR / "r3-mmlu-57-subject-manifest-v1.json"

DEFAULT_TRAIN_TOTAL = len(MMLU_SUBJECTS) * R3_TRAIN_PER_SUBJECT
DEFAULT_TEST_TOTAL = len(MMLU_SUBJECTS) * R3_TEST_PER_SUBJECT
DEFAULT_TOTAL = DEFAULT_TRAIN_TOTAL + DEFAULT_TEST_TOTAL


class PopulationError(ValueError):
    """Raised when the R3 population source or manifest violates its contract."""


def answer_index(label: str) -> int:
    """Map an MMLU answer label (``A``..``D``) to its source order index."""
    if label not in R3_ANSWER_LABELS:
        raise PopulationError(f"unexpected MMLU answer label {label!r}")
    return R3_ANSWER_LABELS.index(label)


def selection_fingerprint(*, subject: str, source_split: str, source_row_index: int) -> str:
    """Deterministic row-selection key: no answer, content, or model input."""
    return fingerprint(
        {
            "protocol_id": R3_SELECTION_PROTOCOL_ID,
            "protocol_version": R3_SELECTION_PROTOCOL_VERSION,
            "dataset_revision": MMLU_REVISION,
            "subject": subject,
            "source_split": source_split,
            "source_row_index": source_row_index,
        }
    )


def item_id(*, subject: str, source_split: str, source_row_index: int) -> str:
    """Opaque item id; deliberately excludes the answer and correctness."""
    digest = fingerprint(
        {
            "version": R3_POPULATION_MANIFEST_VERSION,
            "dataset_revision": MMLU_REVISION,
            "subject": subject,
            "source_split": source_split,
            "source_row_index": source_row_index,
        }
    )
    return f"r3-{digest}"


def content_fingerprint(*, question: str, choices: Sequence[str], answer_index_value: int) -> str:
    return fingerprint(
        {
            "question": question,
            "choices": list(choices),
            "answer_index": answer_index_value,
        }
    )


def question_choices_fingerprint(*, question: str, choices: Sequence[str]) -> str:
    """Cross-split exact-duplicate key: exact question + exact ordered choices only.

    This is the Stage-B contamination-guard key. It deliberately excludes the
    answer, the anchor, the ground truth, and any model output.
    """
    return fingerprint({"question": question, "choices": list(choices)})


# --------------------------------------------------------------------------- #
# Source archive ingestion (standard library only)
# --------------------------------------------------------------------------- #


def _csv_member_name(subject: str, source_split: str) -> str:
    directory = _MMLU_CSV_DIRECTORY[source_split]
    return f"data/{directory}/{subject}_{directory}.csv"


def read_source_rows(
    data_tar_path: str | Path, subject: str, source_split: str
) -> list[tuple[str, list[str], int]]:
    """Return ``(question, [choice0..choice3], answer_index)`` per source row."""
    if source_split not in _MMLU_CSV_DIRECTORY:
        raise PopulationError(f"unsupported source split {source_split!r}")
    member = _csv_member_name(subject, source_split)
    with tarfile.open(data_tar_path, "r") as archive:
        try:
            extracted = archive.extractfile(member)
        except KeyError as exc:  # pragma: no cover - defensive
            raise PopulationError(f"source archive lacks {member}") from exc
        if extracted is None:  # pragma: no cover - defensive
            raise PopulationError(f"source archive entry {member} is not a regular file")
        text = extracted.read().decode("utf-8")
    rows: list[tuple[str, list[str], int]] = []
    for record in csv.reader(io.StringIO(text)):
        if not record:
            continue
        if len(record) != 6:
            raise PopulationError(
                f"{member} row has {len(record)} columns, expected 6 (question, A..D, answer)"
            )
        question = record[0]
        choices = record[1:5]
        index = answer_index(record[5].strip())
        rows.append((question, choices, index))
    return rows


def rank_rows(
    rows: Sequence[tuple[str, list[str], int]],
    *,
    subject: str,
    source_split: str,
) -> list[tuple[int, tuple[str, list[str], int]]]:
    """Return every ``(source_row_index, row)`` in deterministic rank order."""
    keyed = [
        (selection_fingerprint(subject=subject, source_split=source_split, source_row_index=i), i)
        for i in range(len(rows))
    ]
    # Tie-break on the source row index so the order is total and deterministic.
    keyed.sort(key=lambda pair: (pair[0], pair[1]))
    return [(index, rows[index]) for _, index in keyed]


def select_rows(
    rows: Sequence[tuple[str, list[str], int]],
    *,
    subject: str,
    source_split: str,
    count: int,
) -> list[tuple[int, tuple[str, list[str], int]]]:
    """Deterministically select ``count`` rows by the selection fingerprint."""
    if count > len(rows):
        raise PopulationError(
            f"{subject}/{source_split} has {len(rows)} rows, cannot select {count}"
        )
    return rank_rows(rows, subject=subject, source_split=source_split)[:count]


# --------------------------------------------------------------------------- #
# Manifest construction
# --------------------------------------------------------------------------- #

SourceReader = Callable[[str | Path, str, str], list[tuple[str, list[str], int]]]


def build_manifest(
    data_tar_path: str | Path,
    *,
    subjects: Sequence[str] = MMLU_SUBJECTS,
    train_per_subject: int = R3_TRAIN_PER_SUBJECT,
    test_per_subject: int = R3_TEST_PER_SUBJECT,
    source_reader: SourceReader = read_source_rows,
) -> dict[str, Any]:
    """Build the canonical R3 population manifest from the pinned archive.

    TEST is selected first and kept pristine. TRAIN is then selected excluding
    any validation row whose content equals a selected TEST item (MMLU has a
    small validation/test source overlap; see ``R3_OVERLAP_EXCLUSION_RULE``).
    """
    items: list[dict[str, Any]] = []
    counts = {"train": 0, "test": 0}

    test_question_choices: dict[str, int] = {}
    test_selection: dict[str, list[tuple[int, tuple[str, list[str], int]]]] = {}
    for subject in subjects:
        test_rows = source_reader(data_tar_path, subject, R3_TEST_SOURCE_SPLIT)
        chosen = select_rows(
            test_rows,
            subject=subject,
            source_split=R3_TEST_SOURCE_SPLIT,
            count=test_per_subject,
        )
        test_selection[subject] = chosen
        for _, (question, choices, index_answer) in chosen:
            test_question_choices[
                question_choices_fingerprint(question=question, choices=choices)
            ] = index_answer

    def _append(
        r3_split: str, source_split: str, index: int, row: tuple[str, list[str], int]
    ) -> None:
        question, choices, index_answer = row
        key = "train" if r3_split == R3_SPLIT_TRAIN else "test"
        counts[key] += 1
        items.append(
            {
                "item_id": item_id(
                    subject=subject, source_split=source_split, source_row_index=index
                ),
                "subject": subject,
                "split": r3_split,
                "source_split": source_split,
                "source_row_index": index,
                "question": question,
                "choices": list(choices),
                "answer_index": index_answer,
                "source_record_content_fingerprint": content_fingerprint(
                    question=question, choices=choices, answer_index_value=index_answer
                ),
                "selection_fingerprint": selection_fingerprint(
                    subject=subject, source_split=source_split, source_row_index=index
                ),
            }
        )

    overlap_excluded: list[dict[str, Any]] = []
    for subject in subjects:
        for index, row in test_selection[subject]:
            _append(R3_SPLIT_TEST, R3_TEST_SOURCE_SPLIT, index, row)

        train_rows = source_reader(data_tar_path, subject, R3_TRAIN_SOURCE_SPLIT)
        ranked = rank_rows(train_rows, subject=subject, source_split=R3_TRAIN_SOURCE_SPLIT)
        kept: list[tuple[int, tuple[str, list[str], int]]] = []
        for index, (question, choices, index_answer) in ranked:
            duplicate_key = question_choices_fingerprint(question=question, choices=choices)
            if duplicate_key in test_question_choices:
                if test_question_choices[duplicate_key] != index_answer:
                    raise PopulationError(
                        "cross-split question+choices duplicate with a differing answer "
                        f"field (subject={subject!r}, validation row {index}); "
                        "STOP FOR HUMAN REVIEW"
                    )
                overlap_excluded.append(
                    {
                        "subject": subject,
                        "source_split": R3_TRAIN_SOURCE_SPLIT,
                        "source_row_index": index,
                        "source_record_content_fingerprint": content_fingerprint(
                            question=question, choices=choices, answer_index_value=index_answer
                        ),
                    }
                )
                continue
            kept.append((index, (question, choices, index_answer)))
        if len(kept) < train_per_subject:
            raise PopulationError(
                f"{subject} has only {len(kept)} non-overlapping validation rows, "
                f"cannot select {train_per_subject} TRAIN rows"
            )
        for index, row in kept[:train_per_subject]:
            _append(R3_SPLIT_TRAIN, R3_TRAIN_SOURCE_SPLIT, index, row)

    # Items are stored in a deterministic canonical order.
    items.sort(key=lambda item: item["item_id"])
    overlap_excluded.sort(key=lambda entry: (entry["subject"], entry["source_row_index"]))
    payload: dict[str, Any] = {
        "artifact_type": R3_POPULATION_MANIFEST_ARTIFACT_TYPE,
        "artifact_version": R3_POPULATION_MANIFEST_VERSION,
        "fingerprint_version": R3_POPULATION_MANIFEST_FINGERPRINT_VERSION,
        "population_id": R3_POPULATION_ID,
        "population_version": R3_POPULATION_VERSION,
        "dataset": {
            "repository": MMLU_REPOSITORY,
            "revision": MMLU_REVISION,
            "license": MMLU_LICENSE,
            "source_archive": MMLU_SOURCE_ARCHIVE,
            "source_url": MMLU_SOURCE_URL,
            "train_source_split": R3_TRAIN_SOURCE_SPLIT,
            "test_source_split": R3_TEST_SOURCE_SPLIT,
            "unused_source_splits": list(R3_UNUSED_SOURCE_SPLITS),
        },
        "selection_protocol": {
            "id": R3_SELECTION_PROTOCOL_ID,
            "version": R3_SELECTION_PROTOCOL_VERSION,
            "rule": R3_SELECTION_RULE,
            "overlap_exclusion_rule": R3_OVERLAP_EXCLUSION_RULE,
            "train_per_subject": train_per_subject,
            "test_per_subject": test_per_subject,
            "audit_per_subject": R3_AUDIT_PER_SUBJECT,
        },
        "candidate_semantics": {
            "names": list(R3_CANDIDATE_NAMES),
            "description_rule": "exact-source-choice-string-in-source-order",
        },
        "subjects": list(subjects),
        "counts": {
            "subjects": len(subjects),
            "train": counts["train"],
            "test": counts["test"],
            "audit": 0,
            "total": counts["train"] + counts["test"],
            "overlap_excluded_train_rows": len(overlap_excluded),
        },
        "overlap_excluded_train_coordinates": overlap_excluded,
        "items": items,
    }
    payload["manifest_fingerprint"] = manifest_fingerprint(payload)
    return payload


def manifest_canonical_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """The manifest payload without its own fingerprint (the committed content)."""
    return {key: value for key, value in payload.items() if key != "manifest_fingerprint"}


def manifest_fingerprint(payload: Mapping[str, Any]) -> str:
    return fingerprint(manifest_canonical_payload(payload))


# --------------------------------------------------------------------------- #
# Validation (fail closed)
# --------------------------------------------------------------------------- #


def validate_manifest(payload: Mapping[str, Any]) -> None:
    """Validate the manifest against every frozen structural gate."""
    if payload.get("artifact_type") != R3_POPULATION_MANIFEST_ARTIFACT_TYPE:
        raise PopulationError("manifest artifact_type mismatch")
    if payload.get("artifact_version") != R3_POPULATION_MANIFEST_VERSION:
        raise PopulationError("manifest artifact_version mismatch")
    if payload.get("fingerprint_version") != R3_POPULATION_MANIFEST_FINGERPRINT_VERSION:
        raise PopulationError("manifest fingerprint_version mismatch")
    dataset = payload.get("dataset", {})
    if dataset.get("repository") != MMLU_REPOSITORY:
        raise PopulationError("manifest dataset.repository mismatch")
    if dataset.get("revision") != MMLU_REVISION:
        raise PopulationError("manifest dataset.revision mismatch")

    subjects = list(payload.get("subjects", []))
    if subjects != list(MMLU_SUBJECTS):
        raise PopulationError("manifest subjects must be exactly the 57 canonical MMLU subjects")

    items = list(payload.get("items", []))
    counts = {
        R3_SPLIT_TRAIN: sum(1 for item in items if item.get("split") == R3_SPLIT_TRAIN),
        R3_SPLIT_TEST: sum(1 for item in items if item.get("split") == R3_SPLIT_TEST),
    }
    declared = payload.get("counts", {})
    if counts[R3_SPLIT_TRAIN] != DEFAULT_TRAIN_TOTAL:
        raise PopulationError(
            f"manifest TRAIN count {counts[R3_SPLIT_TRAIN]} != {DEFAULT_TRAIN_TOTAL}"
        )
    if counts[R3_SPLIT_TEST] != DEFAULT_TEST_TOTAL:
        raise PopulationError(
            f"manifest TEST count {counts[R3_SPLIT_TEST]} != {DEFAULT_TEST_TOTAL}"
        )
    if (
        declared.get("train") != counts[R3_SPLIT_TRAIN]
        or declared.get("test") != counts[R3_SPLIT_TEST]
    ):
        raise PopulationError("manifest declared counts disagree with item split counts")
    if declared.get("audit") not in (0, None):
        raise PopulationError("manifest AUDIT count must be 0")

    item_ids: set[str] = set()
    coordinates: set[tuple[str, str, int]] = set()
    train_ids: set[str] = set()
    test_ids: set[str] = set()
    train_content: dict[str, str] = {}
    test_content: dict[str, str] = {}
    per_subject: dict[tuple[str, str], int] = {}
    for item in items:
        item_identifier = item["item_id"]
        if item_identifier in item_ids:
            raise PopulationError(f"duplicate item id {item_identifier}")
        item_ids.add(item_identifier)
        coordinate = (item["subject"], item["source_split"], item["source_row_index"])
        if coordinate in coordinates:
            raise PopulationError(f"duplicate source coordinate {coordinate}")
        coordinates.add(coordinate)
        if item["subject"] not in MMLU_SUBJECTS:
            raise PopulationError(f"unknown subject {item['subject']}")
        question = item.get("question")
        if not isinstance(question, str) or not question.strip():
            raise PopulationError(f"item {item_identifier} question must be non-empty")
        choices = item.get("choices")
        if not isinstance(choices, list) or len(choices) != 4:
            raise PopulationError(f"item {item_identifier} must have exactly 4 choices")
        if any(not isinstance(choice, str) or not choice.strip() for choice in choices):
            raise PopulationError(f"item {item_identifier} has an empty choice")
        if item.get("answer_index") not in (0, 1, 2, 3):
            raise PopulationError(f"item {item_identifier} answer_index out of range")
        key = (item["subject"], item["split"])
        per_subject[key] = per_subject.get(key, 0) + 1
        duplicate_key = question_choices_fingerprint(question=question, choices=choices)
        if item["split"] == R3_SPLIT_TRAIN:
            train_ids.add(item_identifier)
            train_content.setdefault(duplicate_key, item_identifier)
        else:
            test_ids.add(item_identifier)
            test_content.setdefault(duplicate_key, item_identifier)

    if train_ids & test_ids:
        raise PopulationError("TRAIN and TEST item ids must be disjoint")
    if item_ids and item_ids != train_ids | test_ids:
        raise PopulationError("every item must be assigned to TRAIN or TEST")
    shared = set(train_content) & set(test_content)
    if shared:
        raise PopulationError(
            "an identical question+choices content appears in both TRAIN and TEST: "
            f"train {train_content[next(iter(shared))]} / test {test_content[next(iter(shared))]}"
        )
    for subject in MMLU_SUBJECTS:
        if per_subject.get((subject, R3_SPLIT_TRAIN)) != R3_TRAIN_PER_SUBJECT:
            raise PopulationError(f"{subject} TRAIN count must be {R3_TRAIN_PER_SUBJECT}")
        if per_subject.get((subject, R3_SPLIT_TEST)) != R3_TEST_PER_SUBJECT:
            raise PopulationError(f"{subject} TEST count must be {R3_TEST_PER_SUBJECT}")

    if payload.get("manifest_fingerprint") != manifest_fingerprint(payload):
        raise PopulationError("manifest fingerprint does not match its content")


# --------------------------------------------------------------------------- #
# Persistence
# --------------------------------------------------------------------------- #


def write_manifest(payload: Mapping[str, Any], path: str | Path = DEFAULT_MANIFEST_PATH) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    return target


def load_manifest(path: str | Path = DEFAULT_MANIFEST_PATH) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_manifest(payload)
    return payload


def manifest_items(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    return list(payload["items"])


def candidate_set(item: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    """Return the four ``(candidate_name, exact_source_choice)`` pairs in order."""
    choices = item["choices"]
    return tuple(zip(R3_CANDIDATE_NAMES, choices, strict=True))


# --------------------------------------------------------------------------- #
# CLI materialization
# --------------------------------------------------------------------------- #


def _default_data_tar() -> Path:
    return (
        Path.home()
        / ".cache"
        / "huggingface"
        / "hub"
        / "datasets--cais--mmlu"
        / "snapshots"
        / MMLU_REVISION
        / MMLU_SOURCE_ARCHIVE
    )


def materialize(
    *,
    data_tar_path: str | Path | None = None,
    output_path: str | Path = DEFAULT_MANIFEST_PATH,
) -> Path:
    source = Path(data_tar_path) if data_tar_path is not None else _default_data_tar()
    if not source.exists():
        raise PopulationError(
            f"MMLU source archive not found at {source}; "
            f"download {MMLU_SOURCE_ARCHIVE} at revision {MMLU_REVISION} first"
        )
    payload = build_manifest(source)
    validate_manifest(payload)
    return write_manifest(payload, output_path)


def _main(argv: Sequence[str]) -> int:
    if len(argv) > 3:
        print("usage: r3_population.py [DATA_TAR] [OUTPUT_JSON]", file=sys.stderr)
        return 2
    data_tar = argv[1] if len(argv) > 1 else None
    output = argv[2] if len(argv) > 2 else DEFAULT_MANIFEST_PATH
    target = materialize(data_tar_path=data_tar, output_path=output)
    payload = load_manifest(target)
    print(
        f"wrote {target} "
        f"(subjects={payload['counts']['subjects']} "
        f"train={payload['counts']['train']} test={payload['counts']['test']} "
        f"fingerprint={payload['manifest_fingerprint']})"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(_main(sys.argv))
