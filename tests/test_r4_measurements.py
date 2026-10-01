"""Synthetic-only engineering tests for the R4 measurement runner.

These tests never load a model, never touch a study row, and never produce a
scientific outcome. They exercise the frozen measurement contract, the exactly
two-forward call rule, independent failure handling, the designated-only OVR
guard, verbalizer verification, evidence serialization/validation, the frozen
population registry, and determinism.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from probvenance.decisions import BoolDecision, ChoiceDecision
from probvenance.diagnostics import ChoiceScoringDiagnostics, ScoringDiagnostics
from probvenance.errors import ScoringLabelError
from probvenance.fingerprint import fingerprint
from probvenance.plans import ScoringStrategy
from probvenance.results import BoolResult, Certainty, ChoiceResult

REPO_ROOT = Path(__file__).resolve().parents[1]
CAL_DIR = REPO_ROOT / "experiments" / "calibration_transport"
RUNNER_PATH = CAL_DIR / "run_r4_measurements.py"

CAT_LABELS = ("A", "B", "C", "D")
CAT_TOKEN_IDS = (32, 33, 34, 35)
CAT_PROBABILITIES = (0.1, 0.2, 0.3, 0.4)
POSITIVE_TOKEN_ID = 9891
NEGATIVE_TOKEN_ID = 2201
OVR_PROBABILITY_TRUE = 0.7


def _load_runner():
    if "run_r4_measurements" in sys.modules:
        return sys.modules["run_r4_measurements"]
    spec = importlib.util.spec_from_file_location("run_r4_measurements", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_r4_measurements"] = module
    spec.loader.exec_module(module)
    return module


runner = _load_runner()
measurements = runner.measurements
r4_raw_evidence = runner.r4_raw_evidence
r4_staging = runner.r4_staging


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #


def _cat_evaluation(decision):
    names = list(decision.choice_names)
    assert len(names) == 4
    probabilities = {name: value for name, value in zip(names, CAT_PROBABILITIES, strict=True)}
    result = ChoiceResult(
        certainty=Certainty(entropy=0.5, margin=0.1),
        method="synthetic-cat",
        probabilities=probabilities,
    )
    diagnostics = ChoiceScoringDiagnostics(
        scoring_label_mass=1.0,
        scoring_label_token_probabilities=CAT_PROBABILITIES,
        top_token_id=CAT_TOKEN_IDS[3],
        top_token_probability=CAT_PROBABILITIES[3],
        top_token_text="D",
    )
    trace = SimpleNamespace(
        scoring_diagnostics=diagnostics,
        candidate_mapping=[
            SimpleNamespace(candidate_name=name, scoring_label=label)
            for name, label in zip(names, CAT_LABELS, strict=True)
        ],
        resolved_target_token_ids=list(zip(CAT_LABELS, CAT_TOKEN_IDS, strict=True)),
        decision_fingerprint="decision-cat",
        plan_fingerprint="plan-cat",
        execution_fingerprint="exec-cat",
        trace_id="trace-cat",
    )
    return SimpleNamespace(result=result, trace=trace)


def _ovr_evaluation(*, probability_true=OVR_PROBABILITY_TRUE):
    result = BoolResult(
        certainty=Certainty(entropy=0.5, margin=0.4),
        method="synthetic-ovr",
        probability_true=probability_true,
    )
    diagnostics = ScoringDiagnostics(
        verbalizer_mass=1.0,
        top_token_id=POSITIVE_TOKEN_ID,
        top_token_probability=probability_true,
        positive_token_probability=probability_true,
        negative_token_probability=1.0 - probability_true,
        top_token_text="yes",
    )
    trace = SimpleNamespace(
        scoring_diagnostics=diagnostics,
        positive_token_id=POSITIVE_TOKEN_ID,
        negative_token_id=NEGATIVE_TOKEN_ID,
        decision_fingerprint="decision-ovr",
        plan_fingerprint="plan-ovr",
        execution_fingerprint="exec-ovr",
        trace_id="trace-ovr",
    )
    return SimpleNamespace(result=result, trace=trace)


class FakeRuntime:
    """A runtime that records every decision and returns synthetic evidence."""

    def __init__(self, *, fail_cat=False, fail_ovr=False):
        self.fail_cat = fail_cat
        self.fail_ovr = fail_ovr
        self.calls: list[object] = []

    def evaluate_with_trace(self, decision):
        self.calls.append(decision)
        if isinstance(decision, BoolDecision):
            if self.fail_ovr:
                raise ScoringLabelError("synthetic OVR failure")
            return _ovr_evaluation()
        if not isinstance(decision, ChoiceDecision):
            raise TypeError(f"unexpected decision {type(decision).__name__}")
        if self.fail_cat:
            raise ScoringLabelError("synthetic CAT failure")
        return _cat_evaluation(decision)

    @property
    def cat_calls(self):
        return [call for call in self.calls if isinstance(call, ChoiceDecision)]

    @property
    def ovr_calls(self):
        return [call for call in self.calls if isinstance(call, BoolDecision)]


class FakeBackend:
    """A backend exposing capabilities plus one synthetic execute path."""

    def __init__(
        self, *, cat_ids=CAT_TOKEN_IDS, positive=POSITIVE_TOKEN_ID, negative=NEGATIVE_TOKEN_ID
    ):
        self.capabilities = SimpleNamespace(
            binary_token_logits=True, categorical_token_logits=True
        )
        self.cat_ids = cat_ids
        self.positive = positive
        self.negative = negative
        self._model = None
        self.load_report = {"missing": [], "unexpected": [], "dropped": []}

    def execute(self, plan):
        if plan.strategy is ScoringStrategy.CATEGORICAL_TOKEN_LOGITS:
            # Production exposes [label, token_id] pairs, not a flat id list
            # (src/probvenance/backends/transformers.py:273); mirror it exactly.
            pairs = [
                [label, token_id]
                for label, token_id in zip(plan.targets, self.cat_ids, strict=True)
            ]
            return SimpleNamespace(metadata={"resolved_target_token_ids": pairs})
        return SimpleNamespace(
            metadata={
                "positive_token_id": self.positive,
                "negative_token_id": self.negative,
                "rendered_input": "synthetic rendered input",
            }
        )


def _row(index, *, anchor_index_value):
    return {
        "item_id": f"synthetic-item-{index}",
        "source_split": "validation",
        "source_row_index": index,
        "split": "TEST",
        "stratum": f"synthetic-stratum-{index % 2}",
        "group_id": None,
        "question": f"Synthetic question number {index}?",
        "candidate_names": ["option-0", "option-1", "option-2", "option-3"],
        "candidate_descriptions": [f"synthetic-desc-{index}-{k}" for k in range(4)],
        "ground_truth_index": (index + 1) % 4,
        "anchor_index": anchor_index_value,
    }


def _rows():
    return [_row(index, anchor_index_value=index % 4) for index in range(4)]


def _model_meta():
    return {
        "model": "synthetic/model",
        "revision": "0" * 40,
        "dtype": "bfloat16",
        "rendering_config": {},
    }


def _measure(runtime, row, *, population_id="r4-synthetic", manifest_fingerprint="f" * 64):
    return runner.measure_item(
        runtime=runtime,
        row=row,
        model_meta=_model_meta(),
        population_id=population_id,
        population_manifest_fingerprint=manifest_fingerprint,
    )


def _payload(items):
    return r4_raw_evidence.build_evidence_payload(
        model_key="olmo-3-7b-instruct",
        model_id="allenai/Olmo-3-7B-Instruct",
        model_revision="6e5971d9eba42665f5bd5a0fcf047f299ce1dccc",
        model_role="current-generation",
        adapter="transformers_backend",
        population_id="r4-synthetic",
        population_manifest_fingerprint="f" * 64,
        dataset_id="synthetic/dataset",
        dataset_revision="0" * 40,
        train_budget="N456",
        planned_train_rows=2,
        planned_test_rows=2,
        measurement_contract_fingerprint="c" * 64,
        final_protocol_candidate_fingerprint="p" * 64,
        execution_manifest_candidate_fingerprint="m" * 64,
        measurement_code_commit="0" * 40,
        runtime={"device": "cpu", "dtype": "bfloat16"},
        items=items,
    )


# --------------------------------------------------------------------------- #
# Frozen measurement contract
# --------------------------------------------------------------------------- #


def test_measurement_contract_constants():
    assert r4_raw_evidence.MEASUREMENT_CALL_CONTRACT_ID == "r4-fixed-event-two-forward-measurement"
    assert r4_raw_evidence.MEASUREMENT_CALL_CONTRACT_VERSION == 1
    assert r4_raw_evidence.CAT_FORWARDS_PER_ITEM == 1
    assert r4_raw_evidence.OVR_FORWARDS_PER_ITEM == 1
    assert r4_raw_evidence.TOTAL_FORWARDS_PER_ITEM == 2
    assert r4_raw_evidence.OVR_SCOPE == "designated-candidate-only"


def test_frozen_authority_matches_the_frozen_artifacts():
    authority = runner.load_frozen_authority()
    assert authority["measurement_contract_status"] == "FROZEN"
    assert (
        authority["measurement_contract_fingerprint"]
        == "7b126d300e774cb44d2c47fcb12513865d03c2b08ffd03a5ce409b2ea976e1e5"
    )
    assert (
        authority["final_protocol_candidate_fingerprint"]
        == "f3a96b7c2847060b1b5422dae800d0871e5bdf6aa9b83ba88cb102c83e44a0b6"
    )
    assert (
        authority["execution_manifest_candidate_fingerprint"]
        == "2195d283b7666a37593a312f4f6abbf8b7d2bd3a4b88737c151255981057f724"
    )


def test_amended_candidate_records_the_frozen_call_contract():
    candidate = json.loads(runner.FINAL_PROTOCOL_CANDIDATE_PATH.read_text(encoding="utf-8"))
    workload = candidate["measurement_workload"]
    assert workload["call_count_contract_status"] == "FROZEN"
    assert (
        workload["call_count_contract_fingerprint"]
        == "7b126d300e774cb44d2c47fcb12513865d03c2b08ffd03a5ce409b2ea976e1e5"
    )
    assert workload["calls_per_item"] == {
        "cat_forwards_per_item": 1,
        "ovr_forwards_per_item": 1,
        "ovr_scope": "designated-candidate-only",
        "total_forwards_per_item": 2,
    }
    assert workload["r3_call_contract_inheritance"] == "REJECTED"
    assert workload["totals"]["required_total_forwards"] == 201456
    assert "r4_call_count_freeze_status" not in workload
    assert "cells" not in workload
    assert (
        candidate["execution_manifest_reference"]["manifest_fingerprint"]
        == "2195d283b7666a37593a312f4f6abbf8b7d2bd3a4b88737c151255981057f724"
    )


def test_amended_manifest_records_the_frozen_call_contract():
    manifest = json.loads(
        runner.EXECUTION_MANIFEST_CANDIDATE_PATH.read_text(encoding="utf-8")
    )
    workload = manifest["measurement_workload"]
    assert workload["call_count_contract_status"] == "FROZEN"
    assert workload["totals"]["required_unique_model_item_rows"] == 100728
    assert workload["grid"]["hellaswag_current_generation"]["unique_model_item_rows"] == 43816
    assert workload["legacy_n912_semantics"]["legacy_n912"] == (
        "NOT REQUIRED / NOT MEASURED IN THE FORMAL R4 PLAN"
    )


def test_measurement_contract_artifact_declares_two_forwards():
    contract = json.loads(runner.MEASUREMENT_CONTRACT_PATH.read_text(encoding="utf-8"))
    call = contract["measurement_call_contract"]
    assert call["cat_forwards_per_item"] == 1
    assert call["ovr_forwards_per_item"] == 1
    assert call["total_forwards_per_item"] == 2
    assert call["ovr_scope"] == "designated-candidate-only"
    assert call["r3_call_contract_inheritance"] == "REJECTED"
    assert contract["workload"]["totals"]["required_total_forwards"] == 201456
    assert contract["workload"]["totals"]["required_unique_model_item_rows"] == 100728
    assert contract["workload"]["totals"]["required_cat_forwards"] == 100728
    assert contract["workload"]["totals"]["required_ovr_forwards"] == 100728


# --------------------------------------------------------------------------- #
# Frozen registries
# --------------------------------------------------------------------------- #


def test_model_registry_shape():
    assert runner.CURRENT_GENERATION_MODEL_KEYS == (
        "olmo-3-7b-instruct",
        "falcon-h1-7b-instruct",
        "granite-4-0-h-tiny",
        "qwen3-5-9b",
    )
    assert runner.LEGACY_MODEL_KEYS == ("minicpm5-2b", "qwen3-5-2b")
    assert len(runner.ALL_MODEL_KEYS) == 6
    assert runner.MMLU_MODEL_KEYS == runner.CURRENT_GENERATION_MODEL_KEYS


def test_frozen_verbalizer_ids_are_encoded():
    expected = {
        "olmo-3-7b-instruct": (32, 33, 34, 35, 9891, 2201),
        "falcon-h1-7b-instruct": (1068, 1069, 1070, 1071, 5763, 3257),
        "granite-4-0-h-tiny": (32, 33, 34, 35, 9891, 2201),
        "qwen3-5-9b": (32, 33, 34, 35, 9405, 2083),
        "minicpm5-2b": (54, 55, 56, 57, 15876, 3707),
        "qwen3-5-2b": (32, 33, 34, 35, 9405, 2083),
    }
    for model_key, ids in expected.items():
        entry = runner.MODEL_REGISTRY[model_key]
        observed = (
            entry["expected_cat_ids"]["A"],
            entry["expected_cat_ids"]["B"],
            entry["expected_cat_ids"]["C"],
            entry["expected_cat_ids"]["D"],
            entry["expected_positive_token_id"],
            entry["expected_negative_token_id"],
        )
        assert observed == ids, model_key


def test_population_registry_manifest_fingerprints():
    assert (
        runner.POPULATION_REGISTRY["hellaswag"]["primary"]["manifest_fingerprint"]
        == "5c45043ba4f0ec436c16dcf494ff26be435c7857244bcbefa321d1678129c400"
    )
    assert (
        runner.POPULATION_REGISTRY["hellaswag"]["robustness912"]["manifest_fingerprint"]
        == "6817496f227d9cd57759bf55489cbf8a1dc4dfd27db0ae551e9223d21d02a096"
    )
    assert (
        runner.POPULATION_REGISTRY["medmcqa"]["primary"]["manifest_fingerprint"]
        == "4a4718438d46ab1ba27c59ca46806756ffb62efa05e6103981dffec4dc48c218"
    )
    assert (
        runner.POPULATION_REGISTRY["medmcqa"]["robustness912"]["manifest_fingerprint"]
        == "e48c37293f196e16d8fba42e7fc255e4ac2e77f81c270ed6f71320981968af12"
    )


@pytest.mark.parametrize(
    ("model_key", "population_key", "expected_budget"),
    [
        ("olmo-3-7b-instruct", "mmlu", "N456"),
        ("olmo-3-7b-instruct", "hellaswag", "N912"),
        ("olmo-3-7b-instruct", "medmcqa", "N912"),
        ("minicpm5-2b", "hellaswag", "N456"),
        ("qwen3-5-2b", "medmcqa", "N456"),
    ],
)
def test_train_budget_resolution(model_key, population_key, expected_budget):
    assert runner.resolve_train_budget(model_key, population_key) == expected_budget


@pytest.mark.parametrize("model_key", ["minicpm5-2b", "qwen3-5-2b"])
def test_legacy_mmlu_is_rejected_at_domain_level(model_key):
    with pytest.raises(runner.R4MeasurementDomainError, match="legacy \\+ MMLU"):
        runner.resolve_cell(model_key, "mmlu")


def test_unknown_model_and_population_are_rejected():
    with pytest.raises(runner.R4MeasurementDomainError, match="unknown model key"):
        runner.resolve_cell("not-a-model", "mmlu")
    with pytest.raises(runner.R4MeasurementDomainError, match="unknown population"):
        runner.resolve_cell("olmo-3-7b-instruct", "not-a-population")


@pytest.mark.parametrize(
    ("model_key", "population_key", "expected_rows"),
    [
        ("olmo-3-7b-instruct", "mmlu", 1596),
        ("olmo-3-7b-instruct", "hellaswag", 10954),
        ("olmo-3-7b-instruct", "medmcqa", 5074),
        ("minicpm5-2b", "hellaswag", 10498),
        ("minicpm5-2b", "medmcqa", 4618),
    ],
)
def test_resolve_cell_row_counts(model_key, population_key, expected_rows):
    cell = runner.resolve_cell(model_key, population_key)
    assert len(cell["required_rows"]) == expected_rows
    assert len(cell["train_rows"]) + len(cell["test_rows"]) == expected_rows
    assert [row["split"] for row in cell["train_rows"]] == ["TRAIN"] * len(cell["train_rows"])
    assert [row["split"] for row in cell["test_rows"]] == ["TEST"] * len(cell["test_rows"])


def test_current_generation_uses_the_n912_union_and_legacy_uses_n456():
    current = runner.resolve_cell("olmo-3-7b-instruct", "hellaswag")
    legacy = runner.resolve_cell("minicpm5-2b", "hellaswag")
    assert current["train_budget"] == "N912"
    assert len(current["train_rows"]) == 912
    assert legacy["train_budget"] == "N456"
    assert len(legacy["train_rows"]) == 456
    # The N456 subset must be nested inside the N912 union.
    current_ids = {row["item_id"] for row in current["train_rows"]}
    legacy_ids = {row["item_id"] for row in legacy["train_rows"]}
    assert legacy_ids <= current_ids


def test_frozen_workload_arithmetic_is_reproduced():
    total = 0
    for model_key in runner.ALL_MODEL_KEYS:
        for population_key in ("mmlu", "hellaswag", "medmcqa"):
            try:
                cell = runner.resolve_cell(model_key, population_key)
            except runner.R4MeasurementDomainError:
                continue
            total += len(cell["required_rows"])
    assert total == 100728
    assert total * 2 == 201456


def test_anchor_rule_reproduces_the_frozen_manifests():
    cells = (("hellaswag", "olmo-3-7b-instruct"), ("medmcqa", "olmo-3-7b-instruct"))
    for population_key, model_key in cells:
        cell = runner.resolve_cell(model_key, population_key)
        dataset_id = cell["dataset_id"]
        revision = cell["dataset_revision"]
        for row in cell["required_rows"][:25]:
            assert row["anchor_index"] == runner.anchor_index(
                dataset_id=dataset_id,
                revision=revision,
                source_split=row["source_split"],
                row_index=row["source_row_index"],
            )


def test_mmlu_rows_are_normalized_with_the_r4_anchor_rule():
    cell = runner.resolve_cell("olmo-3-7b-instruct", "mmlu")
    for row in cell["required_rows"][:25]:
        assert row["candidate_names"] == ["option-0", "option-1", "option-2", "option-3"]
        assert len(row["candidate_descriptions"]) == 4
        assert 0 <= row["ground_truth_index"] < 4
        assert row["anchor_index"] == runner.anchor_index(
            dataset_id="cais/mmlu",
            revision="c30699e8356da336a370243923dbaf21066bb9fe",
            source_split=row["source_split"],
            row_index=row["source_row_index"],
        )


# --------------------------------------------------------------------------- #
# Exactly two forwards, all anchor positions
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("anchor", [0, 1, 2, 3])
def test_exactly_two_calls_for_every_anchor_position(anchor):
    runtime = FakeRuntime()
    row = _row(0, anchor_index_value=anchor)
    item = _measure(runtime, row)
    assert len(runtime.calls) == 2
    assert len(runtime.cat_calls) == 1
    assert len(runtime.ovr_calls) == 1
    assert item["anchor"] == row["candidate_names"][anchor]
    assert item["cat"]["anchor_score"] == CAT_PROBABILITIES[anchor]
    assert item["cat"]["status"] == "scored"
    assert item["ovr"]["status"] == "scored"


def test_cat_call_precedes_the_ovr_call():
    runtime = FakeRuntime()
    _measure(runtime, _row(0, anchor_index_value=2))
    assert isinstance(runtime.calls[0], ChoiceDecision)
    assert isinstance(runtime.calls[1], BoolDecision)


def test_fixed_event_is_recomputed_from_anchor_and_ground_truth():
    runtime = FakeRuntime()
    row = _row(0, anchor_index_value=1)
    row["ground_truth_index"] = 1
    item = _measure(runtime, row)
    assert item["fixed_event"] == 1
    row_other = _row(1, anchor_index_value=0)
    row_other["ground_truth_index"] = 3
    item_other = _measure(FakeRuntime(), row_other)
    assert item_other["fixed_event"] == 0


# --------------------------------------------------------------------------- #
# Designated-only OVR guard
# --------------------------------------------------------------------------- #


def test_ovr_proposition_contains_only_the_designated_candidate():
    runtime = FakeRuntime()
    row = _row(0, anchor_index_value=2)
    _measure(runtime, row)
    proposition = runtime.ovr_calls[0]
    text = proposition.question
    anchor_name = row["candidate_names"][2]
    assert anchor_name in text
    assert row["candidate_descriptions"][2] in text
    for index, name in enumerate(row["candidate_names"]):
        if index == 2:
            continue
        assert name not in text
        assert row["candidate_descriptions"][index] not in text


def test_ovr_record_carries_exactly_one_candidate():
    runtime = FakeRuntime()
    item = _measure(runtime, _row(0, anchor_index_value=3))
    record = item["ovr"]["record"]
    assert len(record["candidates"]) == 1
    assert record["candidates"][0]["candidate"] == item["anchor"]
    assert item["ovr"]["designated_candidate"] == item["anchor"]


def test_no_extra_ovr_calls_are_made():
    runtime = FakeRuntime()
    for anchor in range(4):
        _measure(runtime, _row(anchor, anchor_index_value=anchor))
    assert len(runtime.ovr_calls) == 4


# --------------------------------------------------------------------------- #
# Independent failure handling
# --------------------------------------------------------------------------- #


def test_cat_failure_does_not_suppress_the_ovr_attempt():
    runtime = FakeRuntime(fail_cat=True)
    item = _measure(runtime, _row(0, anchor_index_value=0))
    assert len(runtime.calls) == 2
    assert item["cat"]["status"] == "ineligible"
    assert item["cat"]["reason"].startswith("ScoringLabelError")
    assert item["cat"]["record"] is None
    assert item["ovr"]["status"] == "scored"


def test_ovr_failure_does_not_invalidate_the_cat_evidence():
    runtime = FakeRuntime(fail_ovr=True)
    item = _measure(runtime, _row(0, anchor_index_value=0))
    assert len(runtime.calls) == 2
    assert item["cat"]["status"] == "scored"
    assert item["ovr"]["status"] == "ineligible"
    assert item["ovr"]["record"] is None


def test_failures_never_retry():
    runtime = FakeRuntime(fail_cat=True, fail_ovr=True)
    _measure(runtime, _row(0, anchor_index_value=1))
    assert len(runtime.calls) == 2


def test_unclassified_exceptions_propagate():
    class BoomRuntime(FakeRuntime):
        def evaluate_with_trace(self, decision):
            raise RuntimeError("not a classified measurement failure")

    with pytest.raises(RuntimeError, match="not a classified measurement failure"):
        _measure(BoomRuntime(), _row(0, anchor_index_value=0))


# --------------------------------------------------------------------------- #
# Verbalizer verification
# --------------------------------------------------------------------------- #


def test_verbalizer_verification_passes_for_the_frozen_ids():
    backend = FakeBackend()
    report = runner.verify_verbalizers(backend, "olmo-3-7b-instruct")
    assert report["cat_labels"] == ["A", "B", "C", "D"]
    assert report["cat_token_ids"] == [32, 33, 34, 35]
    assert report["positive_token_id"] == 9891
    assert report["negative_token_id"] == 2201
    assert report["synthetic_cat_forwards"] == 1
    assert report["synthetic_ovr_forwards"] == 1


def test_verbalizer_verification_detects_cat_drift():
    backend = FakeBackend(cat_ids=(32, 33, 34, 36))
    with pytest.raises(runner.R4VerbalizerIdentityDrift, match="CAT verbalizer drift"):
        runner.verify_verbalizers(backend, "olmo-3-7b-instruct")


def test_verbalizer_verification_detects_non_distinct_cat_ids():
    backend = FakeBackend(cat_ids=(32, 32, 34, 35))
    with pytest.raises(runner.R4VerbalizerIdentityDrift):
        runner.verify_verbalizers(backend, "olmo-3-7b-instruct")


def test_verbalizer_verification_detects_ovr_drift():
    backend = FakeBackend(positive=9892)
    with pytest.raises(runner.R4VerbalizerIdentityDrift, match="positive verbalizer drift"):
        runner.verify_verbalizers(backend, "olmo-3-7b-instruct")


def test_verbalizer_verification_detects_indistinct_yes_no():
    backend = FakeBackend(positive=9891, negative=9891)
    with pytest.raises(runner.R4VerbalizerIdentityDrift):
        runner.verify_verbalizers(backend, "olmo-3-7b-instruct")


def test_verbalizer_verification_uses_the_falcon_ids():
    backend = FakeBackend(cat_ids=(1068, 1069, 1070, 1071), positive=5763, negative=3257)
    report = runner.verify_verbalizers(backend, "falcon-h1-7b-instruct")
    assert report["cat_token_ids"] == [1068, 1069, 1070, 1071]


# --------------------------------------------------------------------------- #
# Evidence assembly, serialization, validation
# --------------------------------------------------------------------------- #


def test_evidence_serialization_round_trip(tmp_path):
    rows = _rows()
    runtime = FakeRuntime()
    items = [_measure(runtime, row) for row in rows]
    payload = _payload(items)
    path = tmp_path / "evidence.json"
    r4_raw_evidence.write_json(path, payload)
    reloaded = json.loads(path.read_text(encoding="utf-8"))
    assert reloaded["evidence_fingerprint"] == payload["evidence_fingerprint"]
    r4_raw_evidence.validate_raw_evidence(
        reloaded,
        required_items=rows,
        expected_contract_fingerprint="c" * 64,
        expected_model_key="olmo-3-7b-instruct",
        expected_population_id="r4-synthetic",
    )


def test_evidence_fingerprint_is_deterministic():
    rows = _rows()
    first = _payload([_measure(FakeRuntime(), row) for row in rows])
    second = _payload([_measure(FakeRuntime(), row) for row in rows])
    assert first["evidence_fingerprint"] == second["evidence_fingerprint"]
    assert fingerprint(r4_raw_evidence.canonical_payload(first)) == first["evidence_fingerprint"]


def test_planned_forward_counts_are_two_per_row():
    items = [_measure(FakeRuntime(), row) for row in _rows()]
    payload = _payload(items)
    assert payload["planned"]["rows"] == 4
    assert payload["planned"]["cat_forwards"] == 4
    assert payload["planned"]["ovr_forwards"] == 4
    assert payload["planned"]["total_forwards"] == 8


def test_structural_counts_and_paired_complete():
    items = [_measure(FakeRuntime(), row) for row in _rows()]
    counts = r4_raw_evidence.structural_counts(items)
    assert counts["items"] == 4
    assert counts["cat"]["scored"] == 4
    assert counts["ovr"]["scored"] == 4
    assert r4_raw_evidence.paired_complete_block(items) is True


def test_paired_complete_is_false_when_any_row_is_incomplete():
    rows = _rows()
    runtime = FakeRuntime(fail_cat=True)
    items = [_measure(runtime, row) for row in rows]
    assert r4_raw_evidence.paired_complete_block(items) is False
    counts = r4_raw_evidence.structural_counts(items)
    assert counts["cat"]["ineligible"] == 4
    assert counts["ovr"]["scored"] == 4


def test_validate_rejects_wrong_item_order():
    rows = _rows()
    items = [_measure(FakeRuntime(), row) for row in rows]
    payload = _payload(items)
    with pytest.raises(r4_raw_evidence.R4RawEvidenceError, match="item set/order"):
        r4_raw_evidence.validate_raw_evidence(
            payload,
            required_items=list(reversed(rows)),
            expected_contract_fingerprint="c" * 64,
            expected_model_key="olmo-3-7b-instruct",
            expected_population_id="r4-synthetic",
        )


def test_validate_rejects_a_contract_fingerprint_mismatch():
    items = [_measure(FakeRuntime(), row) for row in _rows()]
    payload = _payload(items)
    with pytest.raises(
        r4_raw_evidence.R4RawEvidenceError, match="measurement_contract_fingerprint"
    ):
        r4_raw_evidence.validate_raw_evidence(
            payload,
            required_items=_rows(),
            expected_contract_fingerprint="d" * 64,
            expected_model_key="olmo-3-7b-instruct",
            expected_population_id="r4-synthetic",
        )


def test_validate_rejects_a_model_key_mismatch():
    items = [_measure(FakeRuntime(), row) for row in _rows()]
    payload = _payload(items)
    with pytest.raises(r4_raw_evidence.R4RawEvidenceError, match="model_key mismatch"):
        r4_raw_evidence.validate_raw_evidence(
            payload,
            required_items=_rows(),
            expected_contract_fingerprint="c" * 64,
            expected_model_key="qwen3-5-9b",
            expected_population_id="r4-synthetic",
        )


def test_validate_rejects_an_anchor_mismatch():
    items = [_measure(FakeRuntime(), row) for row in _rows()]
    payload = _payload(items)
    payload["items"][0]["anchor"] = "option-1"
    with pytest.raises(r4_raw_evidence.R4RawEvidenceError):
        r4_raw_evidence.validate_raw_evidence(
            payload,
            required_items=_rows(),
            expected_contract_fingerprint="c" * 64,
            expected_model_key="olmo-3-7b-instruct",
            expected_population_id="r4-synthetic",
        )


def test_validate_rejects_forbidden_result_fields():
    items = [_measure(FakeRuntime(), row) for row in _rows()]
    payload = _payload(items)
    payload["items"][0]["brier"] = 0.1
    with pytest.raises(r4_raw_evidence.R4RawEvidenceError, match="forbidden result/analysis field"):
        r4_raw_evidence.validate_raw_evidence(
            payload,
            required_items=_rows(),
            expected_contract_fingerprint="c" * 64,
            expected_model_key="olmo-3-7b-instruct",
            expected_population_id="r4-synthetic",
        )


def test_validate_rejects_a_tampered_evidence_fingerprint():
    items = [_measure(FakeRuntime(), row) for row in _rows()]
    payload = _payload(items)
    payload["items"][0]["ovr"]["probability_true"] = 0.99
    with pytest.raises(r4_raw_evidence.R4RawEvidenceError):
        r4_raw_evidence.validate_raw_evidence(
            payload,
            required_items=_rows(),
            expected_contract_fingerprint="c" * 64,
            expected_model_key="olmo-3-7b-instruct",
            expected_population_id="r4-synthetic",
        )


def test_scored_ovr_block_requires_exactly_one_candidate():
    items = [_measure(FakeRuntime(), row) for row in _rows()]
    record = dict(items[0]["ovr"]["record"])
    record["candidates"] = list(record["candidates"]) * 4
    with pytest.raises(r4_raw_evidence.R4RawEvidenceError, match="exactly one candidate record"):
        r4_raw_evidence.scored_ovr_block(
            record=record, source_record_id="x" * 64, top_token=None
        )


def test_top_token_is_extracted_from_the_trace():
    evaluation = _cat_evaluation(
        measurements.build_cat_decision(
            "q?",
            None,
            [
                ("option-0", None),
                ("option-1", None),
                ("option-2", None),
                ("option-3", None),
            ],
        )
    )
    top = runner._top_token(evaluation)
    assert top == {"token_id": 35, "probability": 0.4, "text": "D"}


# --------------------------------------------------------------------------- #
# Full-cell integration with a fake backend (no model)
# --------------------------------------------------------------------------- #


def _patch_cell(monkeypatch, runtime, backend):
    tiny_rows = _rows()
    cell = {
        "model_key": "olmo-3-7b-instruct",
        "population_key": "hellaswag",
        "model": runner.MODEL_REGISTRY["olmo-3-7b-instruct"],
        "population": runner.POPULATION_REGISTRY["hellaswag"],
        "population_id": "r4-synthetic",
        "population_manifest_fingerprint": "f" * 64,
        "dataset_id": "Rowan/hellaswag",
        "dataset_revision": "218ec52e09a7e7462a5400043bb9a69a41d06b76",
        "train_budget": "N456",
        "train_rows": tiny_rows[:2],
        "test_rows": tiny_rows[2:],
        "required_rows": tiny_rows,
    }
    monkeypatch.setattr(runner, "resolve_cell", lambda *a, **k: cell)
    monkeypatch.setattr(runner, "load_backend", lambda *a, **k: backend)
    monkeypatch.setattr(runner, "unload_backend", lambda backend: None)
    monkeypatch.setattr(runner, "verify_model_cache", lambda model_key: {"snapshot_path": "fake"})
    monkeypatch.setattr(runner, "verify_environment", lambda *, device: {"device": device})
    monkeypatch.setattr(runner, "verify_offline_environment", lambda: {"HF_HUB_OFFLINE": "1"})
    monkeypatch.setattr(runner, "measurement_code_commit", lambda: "0" * 40)
    monkeypatch.setattr(runner, "Probvenance", lambda **kwargs: runtime)
    return cell


def test_run_cell_end_to_end_with_a_fake_backend(monkeypatch):
    runtime = FakeRuntime()
    cell = _patch_cell(monkeypatch, runtime, FakeBackend())
    authority = {
        "measurement_contract_fingerprint": "c" * 64,
        "final_protocol_candidate_fingerprint": "p" * 64,
        "execution_manifest_candidate_fingerprint": "m" * 64,
    }
    payload = runner.run_cell(
        model_key="olmo-3-7b-instruct",
        population_key="hellaswag",
        device="cpu",
        authority=authority,
    )
    assert payload["planned"]["rows"] == 4
    assert payload["planned"]["total_forwards"] == 8
    assert payload["paired_complete"] is True
    assert len(runtime.calls) == 8
    assert payload["population"]["population_id"] == "r4-synthetic"
    assert payload["model"]["model_key"] == "olmo-3-7b-instruct"
    r4_raw_evidence.validate_raw_evidence(
        payload,
        required_items=cell["required_rows"],
        expected_contract_fingerprint="c" * 64,
        expected_model_key="olmo-3-7b-instruct",
        expected_population_id="r4-synthetic",
    )


def test_run_cell_records_the_verbalizer_verification(monkeypatch):
    _patch_cell(monkeypatch, FakeRuntime(), FakeBackend())
    authority = {
        "measurement_contract_fingerprint": "c" * 64,
        "final_protocol_candidate_fingerprint": "p" * 64,
        "execution_manifest_candidate_fingerprint": "m" * 64,
    }
    payload = runner.run_cell(
        model_key="olmo-3-7b-instruct",
        population_key="hellaswag",
        device="cpu",
        authority=authority,
    )
    verbalizers = payload["runtime"]["verbalizers"]
    assert verbalizers["cat_token_ids"] == [32, 33, 34, 35]
    assert verbalizers["positive_token_id"] == 9891
    assert payload["runtime"]["batch_size"] == 1
    assert payload["runtime"]["dtype"] == "bfloat16"


def test_synthetic_preflight_runs_one_cat_and_one_ovr_per_model(monkeypatch):
    backend = FakeBackend()
    monkeypatch.setattr(runner, "load_backend", lambda *a, **k: backend)
    monkeypatch.setattr(runner, "unload_backend", lambda backend: None)
    monkeypatch.setattr(runner, "verify_model_cache", lambda model_key: {"snapshot_path": "fake"})
    report = runner.synthetic_preflight(model_keys=["olmo-3-7b-instruct"], device="cpu")
    assert len(report) == 1
    assert report[0]["synthetic_forwards"] == 2
    assert report[0]["status"] == "PASS"


# --------------------------------------------------------------------------- #
# Environment / offline / cache gates
# --------------------------------------------------------------------------- #


def test_environment_drift_is_detected(monkeypatch):
    monkeypatch.setattr(runner, "EXPECTED_TORCH_VERSION", "0.0.0+wrong")
    with pytest.raises(runner.R4MeasurementEnvironmentDrift, match="environment drift"):
        runner.verify_environment(device="cpu")


def test_environment_matches_the_frozen_contract():
    observed = runner.verify_environment(device="cpu")
    assert observed["python"] == "3.11"
    assert observed["torch"] == "2.8.0+cu128"
    assert observed["transformers"] == "5.17.0"
    assert observed["huggingface_hub"] == "1.32.0"


def test_offline_flags_are_required(monkeypatch):
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    with pytest.raises(runner.R4MeasurementEnvironmentDrift, match="offline environment flags"):
        runner.verify_offline_environment()


def test_offline_flags_pass_by_default():
    report = runner.verify_offline_environment()
    assert report["HF_HUB_OFFLINE"] == "1"


def test_missing_model_cache_is_reported(monkeypatch, tmp_path):
    monkeypatch.setenv("HUGGINGFACE_HUB_CACHE", str(tmp_path / "empty"))
    with pytest.raises(runner.R4ModelCacheMissing):
        runner.verify_model_cache("olmo-3-7b-instruct")


def test_incomplete_blobs_are_reported(monkeypatch, tmp_path):
    revision = runner.MODEL_REGISTRY["olmo-3-7b-instruct"]["revision"]
    cache = tmp_path / "hub"
    snapshot = cache / "models--allenai--Olmo-3-7B-Instruct" / "snapshots" / revision
    snapshot.mkdir(parents=True)
    (cache / "models--allenai--Olmo-3-7B-Instruct" / "blobs").mkdir()
    (cache / "models--allenai--Olmo-3-7B-Instruct" / "blobs" / "x.incomplete").write_text("x")
    monkeypatch.setenv("HUGGINGFACE_HUB_CACHE", str(cache))
    with pytest.raises(runner.R4ModelCacheMissing, match="incomplete blobs"):
        runner.verify_model_cache("olmo-3-7b-instruct")


def test_model_cache_is_found_when_present(monkeypatch, tmp_path):
    revision = runner.MODEL_REGISTRY["olmo-3-7b-instruct"]["revision"]
    cache = tmp_path / "hub"
    snapshot = cache / "models--allenai--Olmo-3-7B-Instruct" / "snapshots" / revision
    snapshot.mkdir(parents=True)
    monkeypatch.setenv("HUGGINGFACE_HUB_CACHE", str(cache))
    report = runner.verify_model_cache("olmo-3-7b-instruct")
    assert report["revision"] == revision
    assert report["incomplete_blobs"] == []


def test_cli_requires_a_full_formal_selection():
    with pytest.raises(SystemExit):
        runner.main(["--model-role", "olmo-3-7b-instruct"])


def test_synthetic_fixture_has_no_dataset_markers():
    runner._assert_synthetic_only()


def test_runner_has_no_analysis_vocabulary():
    source = RUNNER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc is not None:
                docstrings.add(doc)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value not in docstrings
        ):
            names.add(node.value)
    pattern = re.compile(r"brier|logloss|log_loss|bootstrap|predictor|wasserstein|isotonic")
    offending = sorted(name for name in names if pattern.search(name.lower()))
    assert offending == []


def test_determinism_across_two_processes(tmp_path):
    script = tmp_path / "determinism_probe.py"
    script.write_text(
        "\n".join(
            [
                "import sys",
                f"sys.path.insert(0, {str(Path(__file__).resolve().parent)!r})",
                "import test_r4_measurements as T",
                "rows = T._rows()",
                "items = [T._measure(T.FakeRuntime(), row) for row in rows]",
                "payload = T._payload(items)",
                "print(payload['evidence_fingerprint'])",
            ]
        ),
        encoding="utf-8",
    )
    outputs = []
    for _ in range(2):
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(REPO_ROOT),
        )
        outputs.append(result.stdout.strip())
    assert outputs[0] == outputs[1]
    assert len(outputs[0]) == 64


# --------------------------------------------------------------------------- #
# Crash-safe resume / staging semantics (operational, outcome-blind)
# --------------------------------------------------------------------------- #


def _authority():
    return {
        "measurement_contract_fingerprint": "c" * 64,
        "final_protocol_candidate_fingerprint": "p" * 64,
        "execution_manifest_candidate_fingerprint": "m" * 64,
        "final_protocol_fingerprint": "d" * 64,
        "execution_manifest_fingerprint": "e" * 64,
    }


class _FailOneCatRuntime(FakeRuntime):
    """Fails exactly one CAT forward (a terminal, classified failure state)."""

    def __init__(self, *, fail_on_index):
        super().__init__()
        self.fail_on_index = fail_on_index
        self.cat_seen = 0

    def evaluate_with_trace(self, decision):
        if isinstance(decision, ChoiceDecision):
            self.cat_seen += 1
            if self.cat_seen == self.fail_on_index:
                self.calls.append(decision)
                raise ScoringLabelError("synthetic CAT failure")
        return super().evaluate_with_trace(decision)


def _cell_dir(tmp_path, cell):
    return r4_staging.ensure_cell_dir(tmp_path, "olmo-3-7b-instruct", cell["population_id"])


def _write_runtime(directory, *, device="cpu"):
    """Mirror the runner's observed runtime so resume can match it exactly."""
    backend = FakeBackend()
    observed = {
        "device": device,
        "dtype": runner.DTYPE,
        "chat_template_kwargs": dict(runner.CHAT_TEMPLATE_KWARGS),
        "batch_size": 1,
        "environment": runner.verify_environment(device=device),
        "offline": runner.verify_offline_environment(),
        "cache": runner.verify_model_cache("olmo-3-7b-instruct"),
        "verbalizers": runner.verify_verbalizers(backend, "olmo-3-7b-instruct"),
    }
    return r4_staging.verify_or_write_runtime(directory, observed)


def _write_identity(tmp_path, cell, authority, *, measurement_code="0" * 40):
    directory = _cell_dir(tmp_path, cell)
    r4_staging.verify_or_write_identity(
        directory,
        runner.cell_identity_header(
            cell=cell, authority=authority, measurement_code=measurement_code
        ),
    )
    _write_runtime(directory)
    return directory


def _commit_row(directory, runtime, cell, row):
    item = runner.measure_item(
        runtime=runtime,
        row=row,
        model_meta=runner._cell_model_meta(cell),
        population_id=cell["population_id"],
        population_manifest_fingerprint=cell["population_manifest_fingerprint"],
    )
    r4_staging.commit_row(directory, item)
    return item


def _resume(tmp_path, *, resume=True):
    return runner.run_cell_resumable(
        model_key="olmo-3-7b-instruct",
        population_key="hellaswag",
        device="cpu",
        authority=_authority(),
        staging_root=tmp_path,
        resume=resume,
    )


def test_frozen_authority_exposes_the_freeze_fingerprints():
    authority = runner.load_frozen_authority()
    assert authority["final_protocol_status"] == "FROZEN"
    assert authority["execution_manifest_status"] == "FROZEN"
    assert (
        authority["final_protocol_fingerprint"]
        == "d1b56d702e1f260cef47eee05b7d878ace07a15168e89408e15e7eb741c0ad34"
    )
    assert (
        authority["execution_manifest_fingerprint"]
        == "f32381c51db24f5dbeb240b5e0fdf73c59a56a615c8607ad8979e2a7e2586775"
    )


def test_cell_identity_header_records_the_frozen_identities(monkeypatch):
    cell = _patch_cell(monkeypatch, FakeRuntime(), FakeBackend())
    header = runner.cell_identity_header(
        cell=cell, authority=_authority(), measurement_code="0" * 40
    )
    assert header["final_protocol_fingerprint"] == "d" * 64
    assert header["execution_manifest_fingerprint"] == "e" * 64
    assert header["measurement_contract_fingerprint"] == "c" * 64
    assert header["model_revision"] == "6e5971d9eba42665f5bd5a0fcf047f299ce1dccc"
    assert header["expected_item_count"] == 4
    assert header["expected_item_ids"] == [row["item_id"] for row in cell["required_rows"]]


def test_cli_exposes_operational_staging_controls():
    args = runner.parse_args(
        [
            "--model-role",
            "olmo-3-7b-instruct",
            "--population",
            "hellaswag",
            "--staging-root",
            "/tmp/x",
            "--resume",
        ]
    )
    assert args.staging_root == "/tmp/x"
    assert args.resume is True


def test_pending_set_is_derived_only_from_transaction_state():
    plan = r4_staging.compute_pending(
        ordered_item_ids=["a", "b", "c", "d"],
        committed_ids={"a", "c"},
        inflight_ids={"b"},
    )
    assert plan["pending"] == ["b", "d"]
    assert plan["fresh"] == ["d"]
    assert plan["recovery_replay"] == ["b"]
    assert plan["committed"] == ["a", "c"]


def test_resumable_fresh_run_completes_the_cell(monkeypatch, tmp_path):
    runtime = FakeRuntime()
    cell = _patch_cell(monkeypatch, runtime, FakeBackend())
    summary = _resume(tmp_path, resume=False)
    assert summary["status"] == "COMPLETE"
    assert summary["new_forwards"] == 8
    assert len(runtime.calls) == 8
    final = r4_staging.load_final(_cell_dir(tmp_path, cell))
    assert final["paired_complete"] is True
    assert len(final["items"]) == 4


def test_already_complete_cell_is_not_rerun(monkeypatch, tmp_path):
    runtime = FakeRuntime()
    _patch_cell(monkeypatch, runtime, FakeBackend())
    _resume(tmp_path, resume=False)
    calls_after_first = len(runtime.calls)
    second = _resume(tmp_path, resume=True)
    assert second["status"] == "ALREADY_COMPLETE"
    assert second["new_forwards"] == 0
    assert len(runtime.calls) == calls_after_first


def test_resume_after_committed_rows_skips_them(monkeypatch, tmp_path):
    runtime = FakeRuntime()
    cell = _patch_cell(monkeypatch, runtime, FakeBackend())
    directory = _write_identity(tmp_path, cell, _authority())
    _commit_row(directory, runtime, cell, cell["required_rows"][0])
    _commit_row(directory, runtime, cell, cell["required_rows"][1])
    runtime.calls.clear()
    summary = _resume(tmp_path, resume=True)
    assert summary["new_forwards"] == 4
    assert len(runtime.calls) == 4
    assert summary["committed_rows"] == 4


def test_mid_row_crash_recovery_replays_the_whole_row(monkeypatch, tmp_path):
    runtime = FakeRuntime()
    cell = _patch_cell(monkeypatch, runtime, FakeBackend())
    directory = _write_identity(tmp_path, cell, _authority())
    _commit_row(directory, runtime, cell, cell["required_rows"][0])
    crashed_id = cell["required_rows"][1]["item_id"]
    r4_staging.mark_inflight(directory, crashed_id)
    runtime.calls.clear()
    summary = _resume(tmp_path, resume=True)
    assert summary["recovery_replay"] == [crashed_id]
    assert summary["new_forwards"] == 6
    rows = r4_staging.load_committed_rows(directory)
    assert [row["item_id"] for row in rows] == [
        row["item_id"] for row in cell["required_rows"]
    ]
    replayed = next(row for row in rows if row["item_id"] == crashed_id)
    # the whole row was replayed: both blocks come from the same fresh attempt
    assert replayed["cat"]["status"] == "scored"
    assert replayed["ovr"]["status"] == "scored"
    assert r4_staging.load_inflight_item_ids(directory) == set()


def test_finalize_after_crash_uses_zero_new_forwards(monkeypatch, tmp_path):
    runtime = FakeRuntime()
    cell = _patch_cell(monkeypatch, runtime, FakeBackend())
    directory = _write_identity(tmp_path, cell, _authority())
    for row in cell["required_rows"]:
        _commit_row(directory, runtime, cell, row)
    runtime.calls.clear()
    summary = _resume(tmp_path, resume=True)
    assert summary["status"] == "COMPLETE"
    assert summary["new_forwards"] == 0
    assert runtime.calls == []


def test_terminal_failure_row_is_never_retried(monkeypatch, tmp_path):
    runtime = _FailOneCatRuntime(fail_on_index=1)
    cell = _patch_cell(monkeypatch, runtime, FakeBackend())
    first = _resume(tmp_path, resume=False)
    assert first["new_forwards"] == 8
    directory = _cell_dir(tmp_path, cell)
    rows = {row["item_id"]: row for row in r4_staging.load_committed_rows(directory)}
    failed_id = cell["required_rows"][0]["item_id"]
    assert rows[failed_id]["cat"]["status"] != "scored"
    calls_after_first = len(runtime.calls)
    second = _resume(tmp_path, resume=True)
    assert second["status"] == "ALREADY_COMPLETE"
    assert second["new_forwards"] == 0
    assert len(runtime.calls) == calls_after_first


def test_fresh_run_refuses_to_inherit_partial_staging(monkeypatch, tmp_path):
    runtime = FakeRuntime()
    cell = _patch_cell(monkeypatch, runtime, FakeBackend())
    directory = _write_identity(tmp_path, cell, _authority())
    _commit_row(directory, runtime, cell, cell["required_rows"][0])
    with pytest.raises(r4_staging.R4StagingError, match="committed rows"):
        _resume(tmp_path, resume=False)


def test_duplicate_committed_row_fails_closed(monkeypatch, tmp_path):
    runtime = FakeRuntime()
    cell = _patch_cell(monkeypatch, runtime, FakeBackend())
    directory = _write_identity(tmp_path, cell, _authority())
    item = _commit_row(directory, runtime, cell, cell["required_rows"][0])
    duplicate = r4_staging.rows_dir(directory) / "duplicate.json"
    r4_staging.write_atomic(duplicate, r4_staging.dump_canonical(item))
    with pytest.raises(r4_staging.R4DuplicateCommittedRow):
        _resume(tmp_path, resume=True)


def test_identity_mismatch_fails_closed(monkeypatch, tmp_path):
    runtime = FakeRuntime()
    cell = _patch_cell(monkeypatch, runtime, FakeBackend())
    directory = _write_identity(tmp_path, cell, _authority())
    stored = r4_staging.read_json(r4_staging.identity_path(directory))
    stored["model_revision"] = "f" * 40
    r4_staging.write_atomic(
        r4_staging.identity_path(directory), r4_staging.dump_canonical(stored)
    )
    with pytest.raises(r4_staging.R4ResumeIdentityMismatch):
        _resume(tmp_path, resume=True)


def test_single_writer_lock_blocks_a_second_writer(monkeypatch, tmp_path):
    runtime = FakeRuntime()
    cell = _patch_cell(monkeypatch, runtime, FakeBackend())
    directory = _write_identity(tmp_path, cell, _authority())
    lock = r4_staging.acquire_cell_lock(directory)
    try:
        with pytest.raises(r4_staging.R4CellLockedError):
            _resume(tmp_path, resume=True)
    finally:
        r4_staging.release_cell_lock(lock)


def test_atomic_finalization_leaves_no_partial_json(monkeypatch, tmp_path):
    runtime = FakeRuntime()
    cell = _patch_cell(monkeypatch, runtime, FakeBackend())
    _resume(tmp_path, resume=False)
    directory = _cell_dir(tmp_path, cell)
    assert [p.name for p in directory.iterdir() if p.name.endswith(".tmp")] == []
    rows_dir = r4_staging.rows_dir(directory)
    assert [p.name for p in rows_dir.iterdir() if p.name.endswith(".tmp")] == []
    assert list(rows_dir.glob("*.inflight")) == []
    final = r4_staging.load_final(directory)
    assert final["evidence_fingerprint"] == r4_raw_evidence.evidence_fingerprint(final)


def test_resume_is_deterministic(monkeypatch, tmp_path):
    def _run(root):
        runtime = FakeRuntime()
        cell = _patch_cell(monkeypatch, runtime, FakeBackend())
        directory = _write_identity(root, cell, _authority())
        _commit_row(directory, runtime, cell, cell["required_rows"][0])
        r4_staging.mark_inflight(directory, cell["required_rows"][1]["item_id"])
        runner.run_cell_resumable(
            model_key="olmo-3-7b-instruct",
            population_key="hellaswag",
            device="cpu",
            authority=_authority(),
            staging_root=root,
            resume=True,
        )
        return r4_staging.dump_canonical(r4_staging.load_final(directory))

    assert _run(tmp_path / "a") == _run(tmp_path / "b")


# --------------------------------------------------------------------------- #
# Pre-row1 defect closure: population adapter -> measurement row contract
#
# The formal Epoch 1 launch was blocked before the first study forward by
# `KeyError: 'question'`: the MMLU adapter `_mmlu_rows()` omitted the frozen
# `question` field that `measure_item()` requires. HellaSwag / MedMCQA go
# through `_normalize_manifest_row()`, which already carried it. These tests
# pin the shared row contract for every population so a schema-adapter
# omission is caught before any model is loaded.
# --------------------------------------------------------------------------- #

MEASUREMENT_REQUIRED_ROW_FIELDS = (
    "item_id",
    "question",
    "candidate_names",
    "candidate_descriptions",
    "anchor_index",
    "ground_truth_index",
    "split",
)


def _r3_mmlu_source_items():
    r3_population = runner._load_sibling("r3_population")
    manifest = r3_population.load_manifest()
    return {str(item["item_id"]): item for item in r3_population.manifest_items(manifest)}


def test_mmlu_normalized_rows_carry_the_frozen_question():
    source = _r3_mmlu_source_items()
    train_rows, test_rows = runner._mmlu_rows()
    assert len(train_rows) == 456
    assert len(test_rows) == 1140
    for row in [*train_rows[:10], *test_rows[:10]]:
        assert "question" in row
        assert isinstance(row["question"], str)
        assert row["question"] != ""
        assert row["question"] == source[row["item_id"]]["question"]


def test_mmlu_normalized_rows_are_structurally_complete():
    train_rows, test_rows = runner._mmlu_rows()
    assert len(train_rows) == 456
    assert len(test_rows) == 1140
    for row in [*train_rows, *test_rows]:
        assert isinstance(row["question"], str)
        assert row["question"] != ""
        assert isinstance(row["item_id"], str)
        assert row["item_id"] != ""
        assert isinstance(row["source_split"], str)
        assert row["source_split"] != ""
        assert row["split"] in {"TRAIN", "TEST"}
        assert row["candidate_names"] == ["option-0", "option-1", "option-2", "option-3"]
        assert len(row["candidate_descriptions"]) == 4
        assert all(isinstance(desc, str) and desc for desc in row["candidate_descriptions"])
        assert 0 <= int(row["anchor_index"]) < 4
        assert 0 <= int(row["ground_truth_index"]) < 4


def test_mmlu_normalized_row_order_and_identity_are_stable():
    source = _r3_mmlu_source_items()
    train_rows, test_rows = runner._mmlu_rows()
    assert [row["item_id"] for row in train_rows] == [
        str(item["item_id"])
        for item in runner._load_sibling("r3_population").manifest_items(
            runner._load_sibling("r3_population").load_manifest()
        )
        if str(item["split"]) == "TRAIN"
    ]
    for row in [*train_rows, *test_rows]:
        item = source[row["item_id"]]
        assert row["candidate_descriptions"] == [str(c) for c in item["choices"]]
        assert row["ground_truth_index"] == int(item["answer_index"])
        assert row["stratum"] == str(item["subject"])
        assert row["source_row_index"] == int(item["source_row_index"])


@pytest.mark.parametrize("population_key", ["mmlu", "hellaswag", "medmcqa"])
def test_every_population_adapter_exposes_the_measurement_row_contract(population_key):
    cell = runner.resolve_cell("olmo-3-7b-instruct", population_key)
    assert cell["required_rows"]
    for row in cell["required_rows"][:5]:
        for field in MEASUREMENT_REQUIRED_ROW_FIELDS:
            assert field in row, (population_key, field)
        assert isinstance(row["question"], str)
        assert row["question"] != ""
        assert len(row["candidate_names"]) == 4
        assert len(row["candidate_descriptions"]) == 4


def test_mmlu_normalized_row_measures_through_the_fake_backend():
    """The original defect raised KeyError before any forward; pin the closure."""
    train_rows, _ = runner._mmlu_rows()
    row = dict(train_rows[0])
    runtime = FakeRuntime()
    item = _measure(runtime, row, population_id="r4-mmlu-57-subject")
    assert len(runtime.calls) == 2
    assert len(runtime.cat_calls) == 1
    assert len(runtime.ovr_calls) == 1
    assert item["item_id"] == row["item_id"]
    assert item["anchor"] == row["candidate_names"][int(row["anchor_index"])]
