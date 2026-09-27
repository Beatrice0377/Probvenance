"""Offline tests for the frozen R3 MMLU population manifest.

No model, no GPU, no network. These lock the 57-subject membership, the 8/20
per-subject split, the opaque item ids, the deterministic selection, and the
content-disjointness gate against silent change.
"""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from typing import Any

HARNESS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = HARNESS_DIR.parents[1]
SRC = REPO_ROOT / "src"

for path in (str(SRC), str(HARNESS_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)


def _load(name: str) -> Any:
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, HARNESS_DIR / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


population = _load("r3_population")

TAMPER_ERROR = population.PopulationError


def _synthetic_reader(table: dict[tuple[str, str], list[tuple[str, list[str], int]]]):
    def read(_path: str, subject: str, source_split: str):
        return copy.deepcopy(table[(subject, source_split)])

    return read


def _rows(count: int, *, choices_prefix: str = "choice") -> list[tuple[str, list[str], int]]:
    return [
        (f"q{index}", [f"{choices_prefix}{index}-{option}" for option in range(4)], index % 4)
        for index in range(count)
    ]


class TestCommittedManifest:
    def test_manifest_loads_and_validates(self) -> None:
        manifest = population.load_manifest()
        population.validate_manifest(manifest)

    def test_frozen_counts(self) -> None:
        manifest = population.load_manifest()
        counts = manifest["counts"]
        assert counts["subjects"] == 57
        assert counts["train"] == 456
        assert counts["test"] == 1140
        assert counts["audit"] == 0
        assert counts["total"] == 1596

    def test_subject_list_is_the_canonical_57(self) -> None:
        manifest = population.load_manifest()
        assert manifest["subjects"] == list(population.MMLU_SUBJECTS)
        assert len(manifest["subjects"]) == 57

    def test_per_subject_split_counts(self) -> None:
        manifest = population.load_manifest()
        per_subject: dict[tuple[str, str], int] = {}
        for item in manifest["items"]:
            key = (item["subject"], item["split"])
            per_subject[key] = per_subject.get(key, 0) + 1
        for subject in population.MMLU_SUBJECTS:
            assert per_subject[(subject, "TRAIN")] == 8
            assert per_subject[(subject, "TEST")] == 20

    def test_item_ids_and_coordinates_are_unique(self) -> None:
        manifest = population.load_manifest()
        ids = [item["item_id"] for item in manifest["items"]]
        coordinates = [
            (item["subject"], item["source_split"], item["source_row_index"])
            for item in manifest["items"]
        ]
        assert len(ids) == len(set(ids))
        assert len(coordinates) == len(set(coordinates))

    def test_train_and_test_are_question_choices_disjoint(self) -> None:
        manifest = population.load_manifest()
        train_content = {
            population.question_choices_fingerprint(
                question=item["question"], choices=item["choices"]
            )
            for item in manifest["items"]
            if item["split"] == "TRAIN"
        }
        test_content = {
            population.question_choices_fingerprint(
                question=item["question"], choices=item["choices"]
            )
            for item in manifest["items"]
            if item["split"] == "TEST"
        }
        assert not (train_content & test_content)

    def test_item_shape(self) -> None:
        manifest = population.load_manifest()
        for item in manifest["items"]:
            assert item["question"].strip()
            assert len(item["choices"]) == 4
            assert all(choice.strip() for choice in item["choices"])
            assert item["answer_index"] in (0, 1, 2, 3)
            assert item["split"] in ("TRAIN", "TEST")
            assert item["source_split"] in ("validation", "test")

    def test_dataset_pins_full_revision(self) -> None:
        manifest = population.load_manifest()
        revision = manifest["dataset"]["revision"]
        assert revision == "c30699e8356da336a370243923dbaf21066bb9fe"
        assert len(revision) == 40
        assert manifest["dataset"]["repository"] == "cais/mmlu"


class TestSelectionIndependence:
    def test_selection_key_ignores_answer_and_content(self) -> None:
        base = _rows(30)
        mutated = [
            (f"DIFFERENT {index}", [f"x{index}-{option}" for option in range(4)], (index + 2) % 4)
            for index in range(30)
        ]
        left = {
            index
            for index, _ in population.select_rows(
                base, subject="s", source_split="validation", count=8
            )
        }
        right = {
            index
            for index, _ in population.select_rows(
                mutated, subject="s", source_split="validation", count=8
            )
        }
        assert left == right

    def test_selection_key_inputs_are_declared_fields_only(self) -> None:
        first = population.selection_fingerprint(
            subject="s", source_split="validation", source_row_index=3
        )
        second = population.selection_fingerprint(
            subject="s", source_split="validation", source_row_index=3
        )
        assert first == second
        assert first != population.selection_fingerprint(
            subject="s", source_split="validation", source_row_index=4
        )

    def test_item_id_is_opaque_to_answer(self) -> None:
        identifier = population.item_id(subject="s", source_split="validation", source_row_index=1)
        assert identifier.startswith("r3-")
        assert identifier == population.item_id(
            subject="s", source_split="validation", source_row_index=1
        )


class TestOverlapExclusion:
    def test_train_excludes_content_duplicated_in_test(self) -> None:
        # The first validation row duplicates the first test row by content.
        duplicate = ("shared question", ["a", "b", "c", "d"], 1)
        table = {
            ("s", "validation"): [
                duplicate,
                *[(f"v{i}", ["a", "b", "c", "d"], 0) for i in range(11)],
            ],
            ("s", "test"): [duplicate],
        }
        manifest = population.build_manifest(
            "unused",
            subjects=["s"],
            train_per_subject=3,
            test_per_subject=1,
            source_reader=_synthetic_reader(table),
        )
        train_rows = [item for item in manifest["items"] if item["split"] == "TRAIN"]
        assert len(train_rows) == 3
        assert all(item["question"] != "shared question" for item in train_rows)
        assert manifest["counts"]["overlap_excluded_train_rows"] == 1

    def test_overlap_guard_uses_question_and_choices_not_answer(self) -> None:
        test_row = ("shared question", ["a", "b", "c", "d"], 1)
        train_duplicate = ("shared question", ["a", "b", "c", "d"], 3)
        table = {
            ("s", "validation"): [
                train_duplicate,
                *[(f"v{i}", ["a", "b", "c", "d"], 0) for i in range(11)],
            ],
            ("s", "test"): [test_row],
        }
        try:
            population.build_manifest(
                "unused",
                subjects=["s"],
                train_per_subject=3,
                test_per_subject=1,
                source_reader=_synthetic_reader(table),
            )
        except TAMPER_ERROR as exc:
            assert "STOP FOR HUMAN REVIEW" in str(exc)
            return
        raise AssertionError("expected a differing-answer duplicate to stop the build")

    def test_overlap_guard_requires_identical_ordered_choices(self) -> None:
        test_row = ("shared question", ["a", "b", "c", "d"], 1)
        same_question_different_choices = ("shared question", ["a", "b", "c", "e"], 1)
        table = {
            ("s", "validation"): [
                same_question_different_choices,
                *[(f"v{i}", ["a", "b", "c", "d"], 0) for i in range(11)],
            ],
            ("s", "test"): [test_row],
        }
        manifest = population.build_manifest(
            "unused",
            subjects=["s"],
            train_per_subject=1,
            test_per_subject=1,
            source_reader=_synthetic_reader(table),
        )
        assert manifest["counts"]["overlap_excluded_train_rows"] == 0


class TestValidationGates:
    def test_tampered_content_changes_fingerprint_and_fails(self) -> None:
        manifest = population.load_manifest()
        tampered = copy.deepcopy(manifest)
        tampered["items"][0]["question"] = "tampered"
        try:
            population.validate_manifest(tampered)
        except TAMPER_ERROR:
            return
        raise AssertionError("expected tampering to fail validation")

    def test_missing_item_fails(self) -> None:
        manifest = population.load_manifest()
        tampered = copy.deepcopy(manifest)
        tampered["items"] = tampered["items"][:-1]
        tampered["manifest_fingerprint"] = population.manifest_fingerprint(tampered)
        try:
            population.validate_manifest(tampered)
        except TAMPER_ERROR:
            return
        raise AssertionError("expected count mismatch to fail validation")

    def test_wrong_subject_set_fails(self) -> None:
        manifest = population.load_manifest()
        tampered = copy.deepcopy(manifest)
        tampered["subjects"] = tampered["subjects"][:-1]
        try:
            population.validate_manifest(tampered)
        except TAMPER_ERROR:
            return
        raise AssertionError("expected subject mismatch to fail validation")


class TestDeterminism:
    def test_synthetic_build_is_deterministic(self) -> None:
        table = {
            ("s", "validation"): _rows(12, choices_prefix="v"),
            ("s", "test"): _rows(25, choices_prefix="t"),
        }
        reader = _synthetic_reader(table)
        first = population.build_manifest(
            "unused", subjects=["s"], train_per_subject=4, test_per_subject=5, source_reader=reader
        )
        second = population.build_manifest(
            "unused", subjects=["s"], train_per_subject=4, test_per_subject=5, source_reader=reader
        )
        assert first["manifest_fingerprint"] == second["manifest_fingerprint"]
        assert first["items"] == second["items"]

    def test_candidate_set_preserves_source_order(self) -> None:
        item = {"choices": ["one", "two", "three", "four"]}
        assert population.candidate_set(item) == (
            ("option-0", "one"),
            ("option-1", "two"),
            ("option-2", "three"),
            ("option-3", "four"),
        )
