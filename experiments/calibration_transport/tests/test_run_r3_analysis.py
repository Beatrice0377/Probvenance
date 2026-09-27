"""Offline tests for the R3 raw -> analysis ingestion / execution runner.

No model, no GPU, no network, no official R3 outcome. Synthetic fixtures and
monkeypatched collaborators exercise the byte/structural/wiring gates, the
CAT/OVR/Y adapters, the TRAIN/TEST partition, the cross-condition pairing, and
the strict separation between validate-only preflight and the frozen kernel.
No confirmatory statistic is computed anywhere in this module.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

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


r3_population = _load("r3_population")
r3_protocol = _load("r3_protocol")
r3_raw_evidence = _load("r3_raw_evidence")
r3_analysis = _load("r3_analysis")
runner = _load("run_r3_analysis")

#: Result/metric field names that must never appear in the preflight summary.
FORBIDDEN_KEYS = {
    "brier",
    "logloss",
    "log_loss",
    "risk",
    "delta",
    "feature_effect",
    "regularization_effect",
    "interaction",
    "bootstrap",
    "interval",
    "accuracy",
    "winner_agreement",
    "native_adequacy",
    "calibrator",
    "slope",
    "intercept",
    "score_min",
    "score_max",
    "score_mean",
    "support_fraction",
}

RELAXED = runner.PopulationContract(
    total=3, train=1, test=2, subjects=1, train_per_subject=None, test_per_subject=None
)


# --------------------------------------------------------------------------- #
# Synthetic fixtures
# --------------------------------------------------------------------------- #


def _evidence_item(
    item_id: str,
    *,
    subject: str = "abstract_algebra",
    split: str = "TEST",
    anchor: str = "option-0",
    ground_truth_value: str = "option-1",
    anchor_correct: bool | None = None,
    cat_score: float = 0.17,
    ovr_score: float = 0.83,
    cat_status: str = "scored",
    ovr_status: str = "scored",
    cat_winner: str = "option-0",
    ovr_winner: str = "option-0",
    cat_record: bool = True,
    ovr_record: bool = True,
) -> dict[str, Any]:
    if anchor_correct is None:
        anchor_correct = anchor == ground_truth_value
    cat_block: dict[str, Any] = {"status": cat_status, "record": None}
    if cat_status == "scored" and cat_record:
        cat_block["record"] = {"anchor_score": cat_score, "winner": cat_winner}
    ovr_block: dict[str, Any] = {"status": ovr_status, "record": None}
    if ovr_status == "scored" and ovr_record:
        ovr_block["record"] = {"anchor_score": ovr_score, "winner": ovr_winner}
    return {
        "item_id": item_id,
        "subject": subject,
        "split": split,
        "anchor": anchor,
        "ground_truth_value": ground_truth_value,
        "anchor_correct": anchor_correct,
        "cat": cat_block,
        "ovr": ovr_block,
    }


def _valid_index_payload() -> dict[str, Any]:
    conditions: dict[str, Any] = {}
    for name in runner.EXPECTED_CONDITIONS:
        spec = runner.CONDITION_SPECS[name]
        conditions[name] = {
            "actual_item_count": runner.EXPECTED_TOTAL_ITEMS,
            "child_plan_fingerprint": "0" * 64,
            "evidence_fingerprint": spec["evidence_fingerprint"],
            "expected_item_count": runner.EXPECTED_TOTAL_ITEMS,
            "file_sha256": spec["raw_sha256"],
            "model_id": spec["model_id"],
            "model_revision": spec["model_revision"],
            "model_role": spec["role"],
            "raw_artifact_filename": spec["raw_filename"],
            "structural_status_counts": runner._expected_structural_counts(),
            "structurally_complete": True,
        }
    payload: dict[str, Any] = {
        "artifact_type": "r3-raw-evidence-index",
        "artifact_version": 1,
        "fingerprint_version": 1,
        "r3_protocol_fingerprint": runner.EXPECTED_PROTOCOL_FINGERPRINT,
        "population_manifest_fingerprint": runner.EXPECTED_POPULATION_MANIFEST_FINGERPRINT,
        "measurement_code_commit": runner.EXPECTED_MEASUREMENT_CODE_COMMIT,
        "conditions": conditions,
        "all_declared_conditions_complete": True,
    }
    payload["index_fingerprint"] = r3_raw_evidence.index_fingerprint(payload)
    return payload


def _valid_raw_payload(condition: str) -> dict[str, Any]:
    spec = runner.CONDITION_SPECS[condition]
    return {
        "artifact_type": "r3-raw-confirmatory-measurement",
        "artifact_version": 1,
        "fingerprint_version": 1,
        "r3_protocol_fingerprint": runner.EXPECTED_PROTOCOL_FINGERPRINT,
        "measurement_code_commit": runner.EXPECTED_MEASUREMENT_CODE_COMMIT,
        "population": {"manifest_fingerprint": runner.EXPECTED_POPULATION_MANIFEST_FINGERPRINT},
        "model_condition": {
            "condition": condition,
            "role": spec["role"],
            "model_id": spec["model_id"],
            "model_revision": spec["model_revision"],
        },
        "evidence_fingerprint": spec["evidence_fingerprint"],
        "structural_counts": runner._expected_structural_counts(),
        "items": [],
    }


def _synthetic_manifest(n_items: int = 2) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for index in range(n_items):
        split = "TRAIN" if index == 0 else "TEST"
        items.append(
            {
                "item_id": f"r3-item-{index:04d}",
                "subject": "abstract_algebra",
                "split": split,
                "source_split": "validation" if split == "TRAIN" else "test",
                "source_row_index": index,
                "question": f"Question {index}?",
                "choices": ["alpha", "beta", "gamma", "delta"],
                "answer_index": 1,
            }
        )
    return {"items": items}


def _design_for(manifest: dict[str, Any], condition: str = "primary") -> dict[str, Any]:
    spec = runner.CONDITION_SPECS[condition]
    plan = r3_protocol.build_child_plan(
        manifest, model_id=spec["model_id"], model_revision=spec["model_revision"]
    )
    return {"models": {condition: {"child_plan_fingerprint": plan.fingerprint}}}


def _synthetic_prepared() -> Any:
    conditions = tuple(
        {
            "model_id": runner.CONDITION_SPECS[name]["model_id"],
            "model_revision": runner.CONDITION_SPECS[name]["model_revision"],
            "train_items": (),
            "test_items": (),
            "test_winner_records": (),
        }
        for name in runner.EXPECTED_CONDITIONS
    )
    provenance_base = {
        "protocol_fingerprint": runner.EXPECTED_PROTOCOL_FINGERPRINT,
        "population_manifest_fingerprint": runner.EXPECTED_POPULATION_MANIFEST_FINGERPRINT,
        "measurement_code_commit": runner.EXPECTED_MEASUREMENT_CODE_COMMIT,
        "raw_index": {
            "filename": runner.EXPECTED_INDEX_FILENAME,
            "sha256": "0" * 64,
            "fingerprint": "0" * 64,
        },
        "raw_inputs": {},
        "analysis_kernel": {"file": "r3_analysis.py", "file_sha256": "0" * 64},
        "analysis_runner": {"file": "run_r3_analysis.py", "file_sha256": "0" * 64},
        "execution_environment": {"python_version": "3.11.0", "platform": "test"},
        "test_bootstrap_replicates": 20000,
        "train_refit_bootstrap_replicates": 2000,
    }
    preflight = {
        "artifact_type": runner.PREFLIGHT_ARTIFACT_TYPE,
        "artifact_version": 1,
        "protocol_fingerprint": runner.EXPECTED_PROTOCOL_FINGERPRINT,
        "population_manifest_fingerprint": runner.EXPECTED_POPULATION_MANIFEST_FINGERPRINT,
        "raw_index_sha256": "0" * 64,
        "raw_index_fingerprint": "0" * 64,
        "conditions": {name: {"total_items": 0} for name in runner.EXPECTED_CONDITIONS},
        "cross_condition_population_pairing": True,
        "official_confirmatory_statistical_outcome_computed": False,
    }
    return runner.PreparedInputs(
        design={"protocol_fingerprint": runner.EXPECTED_PROTOCOL_FINGERPRINT},
        conditions=conditions,
        provenance_base=provenance_base,
        preflight=preflight,
    )


def _all_keys(node: Any):
    if isinstance(node, dict):
        for key, value in node.items():
            yield str(key)
            yield from _all_keys(value)
    elif isinstance(node, list):
        for value in node:
            yield from _all_keys(value)


# --------------------------------------------------------------------------- #
# CLI surface (PART 7, 32, 49)
# --------------------------------------------------------------------------- #


class TestCliSurface:
    def test_cli_requires_a_mode(self) -> None:
        with pytest.raises(SystemExit):
            runner.parse_args([])

    def test_cli_rejects_both_modes(self) -> None:
        with pytest.raises(SystemExit):
            runner.parse_args(["--validate-inputs-only", "--execute-official-r3"])

    def test_cli_accepts_each_mode(self) -> None:
        assert runner.parse_args(["--validate-inputs-only"]).validate_inputs_only is True
        assert runner.parse_args(["--execute-official-r3"]).execute_official_r3 is True

    def test_cli_exposes_no_scientific_configuration(self) -> None:
        for forbidden in (
            "--model",
            "--condition",
            "--primary-model",
            "--replication-model",
            "--procedure",
            "--family",
            "--feature",
            "--lambda",
            "--regularization",
            "--test-replicates",
            "--train-refit-replicates",
            "--bootstrap",
            "--metric",
            "--loss",
            "--direction",
            "--population",
            "--manifest",
            "--dataset",
            "--raw-file",
            "--primary-raw",
            "--replication-raw",
            "--protocol",
            "--protocol-design",
        ):
            with pytest.raises(SystemExit):
                runner.parse_args(["--validate-inputs-only", forbidden, "value"])

    def test_cli_option_surface_is_exactly_the_two_modes(self) -> None:
        options = {o for action in runner.build_parser()._actions for o in action.option_strings}
        assert options == {"-h", "--help", "--validate-inputs-only", "--execute-official-r3"}


# --------------------------------------------------------------------------- #
# Index / provenance gates (PART 43)
# --------------------------------------------------------------------------- #


class TestIndexValidation:
    def _ok(self, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
        payload = _valid_index_payload()
        monkeypatch.setattr(runner, "EXPECTED_INDEX_FINGERPRINT", payload["index_fingerprint"])
        return payload

    def test_good_index_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        runner.validate_index(self._ok(monkeypatch))

    def test_wrong_index_fingerprint_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = self._ok(monkeypatch)
        payload["index_fingerprint"] = "f" * 64
        with pytest.raises(runner.RunnerError):
            runner.validate_index(payload)

    def test_wrong_protocol_fingerprint_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = self._ok(monkeypatch)
        payload["r3_protocol_fingerprint"] = "f" * 64
        with pytest.raises(runner.RunnerError):
            runner.validate_index(payload)

    def test_wrong_manifest_fingerprint_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = self._ok(monkeypatch)
        payload["population_manifest_fingerprint"] = "f" * 64
        with pytest.raises(runner.RunnerError):
            runner.validate_index(payload)

    def test_wrong_measurement_code_commit_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = self._ok(monkeypatch)
        payload["measurement_code_commit"] = "f" * 40
        with pytest.raises(runner.RunnerError):
            runner.validate_index(payload)

    def test_missing_condition_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = self._ok(monkeypatch)
        del payload["conditions"]["primary"]
        with pytest.raises(runner.RunnerError):
            runner.validate_index(payload)

    def test_extra_condition_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = self._ok(monkeypatch)
        payload["conditions"]["tertiary"] = dict(payload["conditions"]["primary"])
        with pytest.raises(runner.RunnerError):
            runner.validate_index(payload)

    def test_incomplete_flag_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = self._ok(monkeypatch)
        payload["all_declared_conditions_complete"] = False
        with pytest.raises(runner.RunnerError):
            runner.validate_index(payload)

    def test_wrong_primary_model_id_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = self._ok(monkeypatch)
        payload["conditions"]["primary"]["model_id"] = "openbmb/Other"
        with pytest.raises(runner.RunnerError):
            runner.validate_index(payload)

    def test_wrong_primary_revision_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = self._ok(monkeypatch)
        payload["conditions"]["primary"]["model_revision"] = "0" * 40
        with pytest.raises(runner.RunnerError):
            runner.validate_index(payload)

    def test_wrong_replication_model_id_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = self._ok(monkeypatch)
        payload["conditions"]["replication"]["model_id"] = "Qwen/Other"
        with pytest.raises(runner.RunnerError):
            runner.validate_index(payload)

    def test_wrong_replication_revision_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = self._ok(monkeypatch)
        payload["conditions"]["replication"]["model_revision"] = "0" * 40
        with pytest.raises(runner.RunnerError):
            runner.validate_index(payload)

    def test_wrong_role_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = self._ok(monkeypatch)
        payload["conditions"]["primary"]["model_role"] = "exploratory"
        with pytest.raises(runner.RunnerError):
            runner.validate_index(payload)

    def test_wrong_raw_filename_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = self._ok(monkeypatch)
        payload["conditions"]["primary"]["raw_artifact_filename"] = "other.json"
        with pytest.raises(runner.RunnerError):
            runner.validate_index(payload)

    def test_wrong_item_count_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = self._ok(monkeypatch)
        payload["conditions"]["primary"]["actual_item_count"] = 1
        with pytest.raises(runner.RunnerError):
            runner.validate_index(payload)

    def test_malformed_structural_completeness_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = self._ok(monkeypatch)
        payload["conditions"]["primary"]["structurally_complete"] = False
        with pytest.raises(runner.RunnerError):
            runner.validate_index(payload)
        payload = self._ok(monkeypatch)
        payload["conditions"]["primary"]["structural_status_counts"] = {"items": 1596}
        with pytest.raises(runner.RunnerError):
            runner.validate_index(payload)


class TestIndexBytes:
    def test_load_index_verifies_sha_before_trust(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        payload = _valid_index_payload()
        target = tmp_path / "index.json"
        target.write_text(json.dumps(payload), encoding="utf-8")
        sha = hashlib.sha256(target.read_bytes()).hexdigest()
        monkeypatch.setattr(runner, "EXPECTED_INDEX_FINGERPRINT", payload["index_fingerprint"])
        monkeypatch.setattr(runner, "EXPECTED_INDEX_SHA256", sha)
        loaded, loaded_sha = runner.load_index(target)
        assert loaded_sha == sha
        assert loaded["artifact_type"] == "r3-raw-evidence-index"

    def test_load_index_rejects_wrong_sha(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        target = tmp_path / "index.json"
        target.write_text(json.dumps(_valid_index_payload()), encoding="utf-8")
        monkeypatch.setattr(runner, "EXPECTED_INDEX_SHA256", "0" * 64)
        with pytest.raises(runner.RunnerError):
            runner.load_index(target)


class TestPathTraversalGuard:
    def test_expected_filename_resolves_inside_results(self) -> None:
        filename = runner.CONDITION_SPECS["primary"]["raw_filename"]
        resolved = runner.guard_raw_filename(filename, expected_filename=filename)
        assert resolved.parent == runner._RESULTS_DIR.resolve()

    def test_parent_traversal_rejected(self) -> None:
        with pytest.raises(runner.RunnerError):
            runner.guard_raw_filename("../evil.json", expected_filename="../evil.json")

    def test_subdirectory_rejected(self) -> None:
        with pytest.raises(runner.RunnerError):
            runner.guard_raw_filename("sub/evil.json", expected_filename="sub/evil.json")

    def test_absolute_path_rejected(self) -> None:
        with pytest.raises(runner.RunnerError):
            runner.guard_raw_filename("/etc/passwd", expected_filename="/etc/passwd")

    def test_wrong_filename_rejected(self) -> None:
        expected = runner.CONDITION_SPECS["primary"]["raw_filename"]
        with pytest.raises(runner.RunnerError):
            runner.guard_raw_filename("r3-raw-other.json", expected_filename=expected)


# --------------------------------------------------------------------------- #
# Raw byte / identity / structural gates (PART 44, 15)
# --------------------------------------------------------------------------- #


class TestRawGates:
    def test_load_raw_artifact_verifies_sha(self, tmp_path: Path) -> None:
        target = tmp_path / "raw.json"
        target.write_text(json.dumps({"items": []}), encoding="utf-8")
        sha = hashlib.sha256(target.read_bytes()).hexdigest()
        payload, loaded_sha = runner.load_raw_artifact(target, expected_sha256=sha)
        assert loaded_sha == sha
        assert payload == {"items": []}
        with pytest.raises(runner.RunnerError):
            runner.load_raw_artifact(target, expected_sha256="0" * 64)

    @pytest.mark.parametrize("condition", ["primary", "replication"])
    def test_verify_raw_identity_accepts_frozen_metadata(self, condition: str) -> None:
        runner.verify_raw_identity(_valid_raw_payload(condition), condition=condition)

    def test_verify_raw_identity_rejects_model_id_mismatch(self) -> None:
        payload = _valid_raw_payload("primary")
        payload["model_condition"]["model_id"] = "openbmb/Other"
        with pytest.raises(runner.RunnerError):
            runner.verify_raw_identity(payload, condition="primary")

    def test_verify_raw_identity_rejects_role_mismatch(self) -> None:
        payload = _valid_raw_payload("replication")
        payload["model_condition"]["role"] = "exploratory"
        with pytest.raises(runner.RunnerError):
            runner.verify_raw_identity(payload, condition="replication")

    def test_verify_raw_identity_rejects_evidence_fingerprint_mismatch(self) -> None:
        payload = _valid_raw_payload("primary")
        payload["evidence_fingerprint"] = "0" * 64
        with pytest.raises(runner.RunnerError):
            runner.verify_raw_identity(payload, condition="primary")

    def test_verify_raw_identity_rejects_structural_counts_mismatch(self) -> None:
        payload = _valid_raw_payload("primary")
        payload["structural_counts"] = {"items": 1}
        with pytest.raises(runner.RunnerError):
            runner.verify_raw_identity(payload, condition="primary")

    def test_child_plan_verification_matches_frozen_design(self) -> None:
        design = r3_protocol.load_design()
        manifest = r3_population.load_manifest()
        for condition in runner.EXPECTED_CONDITIONS:
            expected = design["models"][condition]["child_plan_fingerprint"]
            plan = runner.verify_child_plan(
                manifest, condition=condition, expected_fingerprint=expected
            )
            assert plan.fingerprint == expected

    def test_child_plan_verification_rejects_wrong_fingerprint(self) -> None:
        manifest = r3_population.load_manifest()
        with pytest.raises(runner.RunnerError):
            runner.verify_child_plan(manifest, condition="primary", expected_fingerprint="0" * 64)

    def test_mapping_blocked_when_validation_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        manifest = _synthetic_manifest()
        design = _design_for(manifest)
        raw = {"items": [_evidence_item("r3-item-0000"), _evidence_item("r3-item-0001")]}
        mapped: list[Any] = []

        def _boom(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("structural validation failed")

        monkeypatch.setattr(runner.r3_raw_evidence, "validate_raw_evidence", _boom)
        monkeypatch.setattr(runner, "r3_item_from_evidence", lambda item: mapped.append(item))
        with pytest.raises(RuntimeError):
            runner.map_validated_condition("primary", raw, manifest=manifest, design=design)
        assert mapped == []

    def test_mapping_runs_after_validation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        manifest = _synthetic_manifest()
        design = _design_for(manifest)
        raw = {
            "items": [_evidence_item("r3-item-0000", split="TRAIN"), _evidence_item("r3-item-0001")]
        }
        monkeypatch.setattr(runner.r3_raw_evidence, "validate_raw_evidence", lambda *a, **k: None)
        pair_contract = runner.PopulationContract(
            total=2, train=1, test=1, subjects=1, train_per_subject=None, test_per_subject=None
        )
        train, test, winners = runner.map_validated_condition(
            "primary", raw, manifest=manifest, design=design, contract=pair_contract
        )
        assert [item.item_id for item in train] == ["r3-item-0000"]
        assert [item.item_id for item in test] == ["r3-item-0001"]
        assert [record.item_id for record in winners] == ["r3-item-0001"]

    def test_prepare_rejects_traversal_filename(self, monkeypatch: pytest.MonkeyPatch) -> None:
        payload = {
            "conditions": {
                "primary": {"raw_artifact_filename": "../evil.json"},
                "replication": {},
            }
        }
        monkeypatch.setattr(runner, "load_index", lambda path: (payload, "0" * 64))
        monkeypatch.setattr(
            runner, "verify_protocol_identity", lambda design: runner.EXPECTED_PROTOCOL_FINGERPRINT
        )
        monkeypatch.setattr(
            runner,
            "verify_manifest_identity",
            lambda manifest: runner.EXPECTED_POPULATION_MANIFEST_FINGERPRINT,
        )
        with pytest.raises(runner.RunnerError):
            runner.prepare_official_inputs(design={}, manifest={})

    def test_prepare_rejects_index_child_plan_mismatch(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        primary = runner.CONDITION_SPECS["primary"]
        payload = {
            "conditions": {
                "primary": {
                    "raw_artifact_filename": primary["raw_filename"],
                    "file_sha256": primary["raw_sha256"],
                    "child_plan_fingerprint": "0" * 64,
                },
                "replication": {},
            }
        }
        monkeypatch.setattr(runner, "load_index", lambda path: (payload, "0" * 64))
        monkeypatch.setattr(
            runner, "verify_protocol_identity", lambda design: runner.EXPECTED_PROTOCOL_FINGERPRINT
        )
        monkeypatch.setattr(
            runner,
            "verify_manifest_identity",
            lambda manifest: runner.EXPECTED_POPULATION_MANIFEST_FINGERPRINT,
        )
        monkeypatch.setattr(
            runner, "load_raw_artifact", lambda path, *, expected_sha256: ({}, "0" * 64)
        )
        monkeypatch.setattr(runner, "verify_raw_identity", lambda payload, *, condition: None)
        design = {
            "models": {
                "primary": {"child_plan_fingerprint": "1" * 64},
                "replication": {"child_plan_fingerprint": "1" * 64},
            }
        }
        with pytest.raises(runner.RunnerError):
            runner.prepare_official_inputs(design=design, manifest={})


# --------------------------------------------------------------------------- #
# Semantic adapter (PART 16, 18, 19, 45)
# --------------------------------------------------------------------------- #


class TestSemanticAdapter:
    def test_cat_and_ovr_scores_are_not_swapped(self) -> None:
        item = runner.r3_item_from_evidence(_evidence_item("i", cat_score=0.17, ovr_score=0.83))
        assert item.cat_score == 0.17
        assert item.ovr_score == 0.83

    def test_label_is_zero_when_anchor_incorrect_even_if_winners_correct(self) -> None:
        item = runner.r3_item_from_evidence(
            _evidence_item(
                "i",
                anchor="option-0",
                ground_truth_value="option-1",
                anchor_correct=False,
                cat_winner="option-1",
                ovr_winner="option-1",
            )
        )
        assert item.label == 0.0

    def test_label_is_one_when_anchor_correct(self) -> None:
        item = runner.r3_item_from_evidence(
            _evidence_item(
                "i", anchor="option-1", ground_truth_value="option-1", anchor_correct=True
            )
        )
        assert item.label == 1.0

    def test_anchor_correct_must_agree_with_anchor_vs_truth(self) -> None:
        bad = _evidence_item(
            "i", anchor="option-0", ground_truth_value="option-1", anchor_correct=True
        )
        with pytest.raises(runner.RunnerError):
            runner.r3_item_from_evidence(bad)

    def test_non_scored_block_blocks_mapping(self) -> None:
        with pytest.raises(runner.RunnerError):
            runner.r3_item_from_evidence(_evidence_item("i", cat_status="missing"))
        with pytest.raises(runner.RunnerError):
            runner.r3_item_from_evidence(_evidence_item("i", ovr_status="ineligible"))

    def test_missing_record_blocks_mapping(self) -> None:
        with pytest.raises(runner.RunnerError):
            runner.r3_item_from_evidence(_evidence_item("i", cat_record=False))
        with pytest.raises(runner.RunnerError):
            runner.r3_item_from_evidence(_evidence_item("i", ovr_record=False))

    def test_invalid_anchor_probability_blocks_mapping(self) -> None:
        with pytest.raises(runner.RunnerError):
            runner.r3_item_from_evidence(_evidence_item("i", cat_score=1.5))
        with pytest.raises(runner.RunnerError):
            runner.r3_item_from_evidence(_evidence_item("i", ovr_score=-0.1))
        with pytest.raises(runner.RunnerError):
            runner.r3_item_from_evidence(_evidence_item("i", cat_score=True))

    def test_winner_mapping_uses_recorded_winners_not_scores(self) -> None:
        item = _evidence_item(
            "i",
            cat_score=0.99,
            ovr_score=0.99,
            cat_winner="option-2",
            ovr_winner="option-3",
        )
        record = r3_analysis.winner_record_from_evidence(item)
        assert record.cat_winner == "option-2"
        assert record.ovr_winner == "option-3"
        assert record.item_id == "i"
        assert record.ground_truth_value == "option-1"

    def test_winner_mapping_requires_recorded_winner(self) -> None:
        item = _evidence_item("i")
        del item["cat"]["record"]["winner"]
        with pytest.raises(r3_analysis.AnalysisError):
            r3_analysis.winner_record_from_evidence(item)


# --------------------------------------------------------------------------- #
# Splits (PART 21, 22, 46)
# --------------------------------------------------------------------------- #


class TestSplits:
    def _population(self) -> list[dict[str, Any]]:
        return [
            _evidence_item("a", split="TRAIN"),
            _evidence_item("b", split="TEST"),
            _evidence_item("c", split="TEST"),
        ]

    def test_split_preserves_order_and_partitions(self) -> None:
        population = self._population()
        train, test = runner.partition_evidence_items(population, contract=RELAXED)
        assert [item["item_id"] for item in train] == ["a"]
        assert [item["item_id"] for item in test] == ["b", "c"]
        assert len(train) + len(test) == len(population)

    def test_audit_split_is_rejected(self) -> None:
        population = self._population()
        population.append(_evidence_item("d", split="AUDIT"))
        with pytest.raises(runner.RunnerError):
            runner.partition_evidence_items(population, contract=RELAXED)

    def test_counts_are_enforced(self) -> None:
        population = self._population()
        with pytest.raises(runner.RunnerError):
            runner.partition_evidence_items(
                population,
                contract=runner.PopulationContract(
                    total=4,
                    train=1,
                    test=2,
                    subjects=1,
                    train_per_subject=None,
                    test_per_subject=None,
                ),
            )
        with pytest.raises(runner.RunnerError):
            runner.partition_evidence_items(
                population,
                contract=runner.PopulationContract(
                    total=3,
                    train=2,
                    test=1,
                    subjects=1,
                    train_per_subject=None,
                    test_per_subject=None,
                ),
            )

    def test_subject_count_is_enforced(self) -> None:
        population = self._population()
        with pytest.raises(runner.RunnerError):
            runner.partition_evidence_items(
                population,
                contract=runner.PopulationContract(
                    total=3,
                    train=1,
                    test=2,
                    subjects=2,
                    train_per_subject=None,
                    test_per_subject=None,
                ),
            )

    def test_test_winner_records_cover_test_rows(self) -> None:
        _train, test = runner.partition_evidence_items(self._population(), contract=RELAXED)
        records = runner.build_test_winner_records(test)
        assert [record.item_id for record in records] == ["b", "c"]


# --------------------------------------------------------------------------- #
# Cross-model pairing (PART 23, 47)
# --------------------------------------------------------------------------- #


class TestCrossModelPairing:
    def test_identical_structure_passes_despite_different_scores_and_winners(self) -> None:
        primary = [
            _evidence_item("a", cat_score=0.11, ovr_score=0.22, cat_winner="option-0"),
            _evidence_item("b", cat_score=0.33, ovr_score=0.44, cat_winner="option-1"),
        ]
        replication = [
            _evidence_item("a", cat_score=0.91, ovr_score=0.82, cat_winner="option-3"),
            _evidence_item("b", cat_score=0.73, ovr_score=0.64, cat_winner="option-2"),
        ]
        runner.verify_cross_condition_pairing(primary, replication)

    def test_mismatch_in_any_structure_field_fails(self) -> None:
        primary = [_evidence_item("a"), _evidence_item("b")]
        variants = [
            _evidence_item("c"),
            _evidence_item("b", subject="anatomy"),
            _evidence_item("b", split="TRAIN"),
            _evidence_item("b", anchor="option-2"),
            _evidence_item("b", ground_truth_value="option-2"),
            _evidence_item("b", anchor_correct=True),
        ]
        for variant in variants:
            replication = [_evidence_item("a"), variant]
            with pytest.raises(runner.RunnerError):
                runner.verify_cross_condition_pairing(primary, replication)

    def test_order_mismatch_fails(self) -> None:
        primary = [_evidence_item("a"), _evidence_item("b")]
        replication = [_evidence_item("b"), _evidence_item("a")]
        with pytest.raises(runner.RunnerError):
            runner.verify_cross_condition_pairing(primary, replication)

    def test_row_count_mismatch_fails(self) -> None:
        with pytest.raises(runner.RunnerError):
            runner.verify_cross_condition_pairing([_evidence_item("a")], [])


# --------------------------------------------------------------------------- #
# Validate-only vs execute isolation (PART 27, 30, 31, 41, 48)
# --------------------------------------------------------------------------- #


class TestValidateOnlyIsolation:
    def test_validate_only_never_calls_analysis_kernel(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        prepared = _synthetic_prepared()
        monkeypatch.setattr(runner, "prepare_official_inputs", lambda **kwargs: prepared)
        monkeypatch.setattr(
            runner,
            "verify_git_state",
            lambda *, require_synchronized: {
                "branch": "main",
                "head": "a" * 40,
                "origin_main": "a" * 40,
                "ahead": 0,
                "behind": 0,
            },
        )

        def _boom(*args: Any, **kwargs: Any) -> Any:
            raise AssertionError("STATISTICAL ANALYSIS MUST NOT BE CALLED")

        monkeypatch.setattr(runner.r3_analysis, "build_analysis_artifact", _boom)
        monkeypatch.setattr(runner.r3_analysis, "fit_panel", _boom)
        monkeypatch.setattr(runner.r3_analysis, "analyze_model_condition", _boom)
        assert runner.main(["--validate-inputs-only"]) == 0
        summary = json.loads(capsys.readouterr().out)
        assert summary["official_confirmatory_statistical_outcome_computed"] is False

    def test_validate_only_enforces_clean_main(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            runner, "prepare_official_inputs", lambda **kwargs: _synthetic_prepared()
        )
        responses = {"branch --show-current": "main", "status --porcelain": " M x"}
        monkeypatch.setattr(runner, "_git", lambda *args: responses.get(" ".join(args), ""))
        with pytest.raises(runner.RunnerError):
            runner.main(["--validate-inputs-only"])

    def test_validate_only_records_git_state(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setattr(
            runner, "prepare_official_inputs", lambda **kwargs: _synthetic_prepared()
        )
        state = {
            "branch": "main",
            "head": "a" * 40,
            "origin_main": "b" * 40,
            "ahead": 3,
            "behind": 0,
        }
        monkeypatch.setattr(runner, "verify_git_state", lambda *, require_synchronized: state)
        assert runner.main(["--validate-inputs-only"]) == 0
        summary = json.loads(capsys.readouterr().out)
        assert summary["git"] == state

    def test_preflight_summary_has_no_result_keys(self) -> None:
        preflight = _synthetic_prepared().preflight
        keys = {key.lower() for key in _all_keys(preflight)}
        assert keys & FORBIDDEN_KEYS == set()

    def test_validate_only_allows_unpushed_candidate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        responses = {
            "branch --show-current": "main",
            "status --porcelain": "",
            "rev-parse HEAD": "a" * 40,
            "rev-parse origin/main": "b" * 40,
            "rev-list --left-right --count HEAD...origin/main": "3\t0",
        }
        monkeypatch.setattr(runner, "_git", lambda *args: responses[" ".join(args)])
        state = runner.verify_git_state(require_synchronized=False)
        assert state["ahead"] == 3

    def test_execute_requires_synchronized_main(self, monkeypatch: pytest.MonkeyPatch) -> None:
        responses = {
            "branch --show-current": "main",
            "status --porcelain": "",
            "rev-parse HEAD": "a" * 40,
            "rev-parse origin/main": "b" * 40,
            "rev-list --left-right --count HEAD...origin/main": "3\t0",
        }
        monkeypatch.setattr(runner, "_git", lambda *args: responses[" ".join(args)])
        with pytest.raises(runner.RunnerError):
            runner.verify_git_state(require_synchronized=True)

    def test_git_gate_rejects_dirty_tree(self, monkeypatch: pytest.MonkeyPatch) -> None:
        responses = {
            "branch --show-current": "main",
            "status --porcelain": " M x",
            "rev-parse HEAD": "a" * 40,
            "rev-parse origin/main": "a" * 40,
            "rev-list --left-right --count HEAD...origin/main": "0\t0",
        }
        monkeypatch.setattr(runner, "_git", lambda *args: responses[" ".join(args)])
        with pytest.raises(runner.RunnerError):
            runner.verify_git_state(require_synchronized=False)

    def test_git_gate_rejects_non_main_branch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        responses = {
            "branch --show-current": "dev",
            "status --porcelain": "",
            "rev-parse HEAD": "a" * 40,
            "rev-parse origin/main": "a" * 40,
            "rev-list --left-right --count HEAD...origin/main": "0\t0",
        }
        monkeypatch.setattr(runner, "_git", lambda *args: responses[" ".join(args)])
        with pytest.raises(runner.RunnerError):
            runner.verify_git_state(require_synchronized=False)


class TestExecuteControlFlow:
    def _patched_git(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            runner,
            "verify_git_state",
            lambda *, require_synchronized: {
                "branch": "main",
                "head": "a" * 40,
                "origin_main": "a" * 40,
                "ahead": 0,
                "behind": 0,
            },
        )

    def test_execute_calls_builder_once_with_primary_first(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        prepared = _synthetic_prepared()
        self._patched_git(monkeypatch)
        calls: list[dict[str, Any]] = []

        def fake_builder(**kwargs: Any) -> dict[str, Any]:
            calls.append(kwargs)
            return {"artifact_type": "r3-confirmatory-analysis"}

        out = tmp_path / "analysis.json"
        prov = tmp_path / "execution.json"
        result = runner.execute_official_r3(
            prepared, output_path=out, provenance_path=prov, builder=fake_builder
        )
        assert len(calls) == 1
        assert "test_replicates" not in calls[0]
        assert "train_refit_replicates" not in calls[0]
        assert [c["model_id"] for c in calls[0]["conditions"]] == [
            runner.CONDITION_SPECS["primary"]["model_id"],
            runner.CONDITION_SPECS["replication"]["model_id"],
        ]
        assert out.exists() and prov.exists()
        assert result["analysis_output_sha256"] == hashlib.sha256(out.read_bytes()).hexdigest()

    def test_execute_refuses_existing_output(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        prepared = _synthetic_prepared()
        self._patched_git(monkeypatch)
        out = tmp_path / "analysis.json"
        out.write_text("existing", encoding="utf-8")
        with pytest.raises(runner.RunnerError):
            runner.execute_official_r3(
                prepared,
                output_path=out,
                provenance_path=tmp_path / "execution.json",
                builder=lambda **kwargs: {},
            )

    def test_analysis_exception_leaves_no_output(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        prepared = _synthetic_prepared()
        self._patched_git(monkeypatch)

        def _boom(**kwargs: Any) -> dict[str, Any]:
            raise RuntimeError("kernel failed")

        out = tmp_path / "analysis.json"
        prov = tmp_path / "execution.json"
        with pytest.raises(RuntimeError):
            runner.execute_official_r3(
                prepared, output_path=out, provenance_path=prov, builder=_boom
            )
        assert not out.exists() and not prov.exists()

    def test_write_pair_cleans_up_when_second_finalize_fails(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        first = tmp_path / "a.json"
        second = tmp_path / "b.json"
        real_replace = runner.os.replace
        state = {"calls": 0}

        def flaky(src: Any, dst: Any) -> None:
            state["calls"] += 1
            if state["calls"] == 2:
                raise OSError("synthetic finalize failure")
            real_replace(src, dst)

        monkeypatch.setattr(runner.os, "replace", flaky)
        with pytest.raises(OSError):
            runner._write_text_pair(first, "one\n", second, "two\n")
        assert not first.exists() and not second.exists()
        assert not (tmp_path / "a.json.tmp").exists()
        assert not (tmp_path / "b.json.tmp").exists()

    def test_write_pair_refuses_existing(self, tmp_path: Path) -> None:
        first = tmp_path / "a.json"
        first.write_text("existing", encoding="utf-8")
        with pytest.raises(runner.RunnerError):
            runner._write_text_pair(first, "one\n", tmp_path / "b.json", "two\n")
