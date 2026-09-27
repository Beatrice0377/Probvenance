"""Offline tests for the frozen R3 confirmatory protocol identity.

No model, no GPU, no network. These lock the four-procedure fixed panel, the
solver boundary, the Research Spec v2 commitment, the six primary contrasts,
the multiplicity tails, and the child-plan sharing contract.
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


protocol = _load("r3_protocol")
population = _load("r3_population")


def _manifest() -> dict[str, Any]:
    return population.load_manifest()


def _walk_keys(payload: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            keys.add(key)
            keys |= _walk_keys(value)
    elif isinstance(payload, list):
        for entry in payload:
            keys |= _walk_keys(entry)
    return keys


class TestFrozenPanel:
    def test_exactly_four_procedures(self) -> None:
        panel = protocol.procedure_panel()
        assert [procedure.label for procedure in panel] == list(protocol.R3_PROCEDURE_LABELS)
        assert len(panel) == 4

    def test_factorial_grid(self) -> None:
        panel = {procedure.label: procedure for procedure in protocol.procedure_panel()}
        assert panel["P-low"].feature_id == protocol.FEATURE_P_ID
        assert panel["P-historical"].feature_id == protocol.FEATURE_P_ID
        assert panel["L-low"].feature_id == protocol.FEATURE_L_ID
        assert panel["L-historical"].feature_id == protocol.FEATURE_L_ID
        assert panel["P-low"].l2_strength == protocol.L2_LOW
        assert panel["P-historical"].l2_strength == protocol.L2_HISTORICAL
        assert panel["L-low"].l2_strength == protocol.L2_LOW
        assert panel["L-historical"].l2_strength == protocol.L2_HISTORICAL

    def test_lambda_1e6_is_not_in_the_panel(self) -> None:
        strengths = {procedure.l2_strength for procedure in protocol.procedure_panel()}
        assert 1e-6 not in strengths
        assert 0.1 not in strengths and 1.0 not in strengths

    def test_solver_is_not_part_of_the_statistical_procedure(self) -> None:
        for procedure in protocol.procedure_panel():
            keys = set(procedure.canonical_payload())
            assert not any("solver" in key for key in keys)
            assert not any("device" in key for key in keys)
            assert not any("library" in key for key in keys)

    def test_family_l_endpoint_policy_keeps_fail_closed(self) -> None:
        panel = {procedure.label: procedure for procedure in protocol.procedure_panel()}
        assert panel["L-low"].endpoint_policy_id == protocol.ENDPOINT_L_ID
        assert panel["L-low"].feature_id == protocol.FEATURE_L_ID

    def test_every_procedure_uses_fixed_panel_no_selection(self) -> None:
        for procedure in protocol.procedure_panel():
            assert procedure.selection_rule_id == protocol.SELECTION_RULE_ID

    def test_raw_is_not_counted_as_a_procedure(self) -> None:
        labels = {procedure.label for procedure in protocol.procedure_panel()}
        assert "RAW" not in labels
        assert "raw" not in labels


class TestProtocolDesign:
    def test_commits_research_spec_v2(self) -> None:
        design = protocol.build_design(_manifest())
        assert design["research_spec"] == {"id": protocol.R3_RESEARCH_SPEC_ID, "version": 2}

    def test_exactly_six_primary_contrasts(self) -> None:
        design = protocol.build_design(_manifest())
        contrasts = design["primary_contrasts"]
        assert len(contrasts) == 6
        assert {entry["direction"] for entry in contrasts} == {"CAT->OVR", "OVR->CAT"}
        assert {entry["effect"] for entry in contrasts} == {
            "feature",
            "regularization",
            "interaction",
        }

    def test_no_method_selection_leakage(self) -> None:
        design = protocol.build_design(_manifest())
        keys = _walk_keys(design)
        for forbidden in ("selected_method", "winner_method", "best_lambda", "selected_lambda"):
            assert forbidden not in keys
        for entry in design["procedures"]:
            assert entry["payload"]["selection_rule_id"] == "fixed-panel-no-selection"

    def test_primary_and_replication_models(self) -> None:
        design = protocol.build_design(_manifest())
        assert design["models"]["primary"]["model_id"] == protocol.PRIMARY_MODEL_ID
        assert design["models"]["primary"]["model_revision"] == protocol.PRIMARY_MODEL_REVISION
        assert design["models"]["replication"]["model_id"] == protocol.REPLICATION_MODEL_ID
        assert (
            design["models"]["replication"]["model_revision"] == protocol.REPLICATION_MODEL_REVISION
        )

    def test_model_revisions_are_full_shas(self) -> None:
        assert len(protocol.PRIMARY_MODEL_REVISION) == 40
        assert len(protocol.REPLICATION_MODEL_REVISION) == 40

    def test_multiplicity_tails(self) -> None:
        design = protocol.build_design(_manifest())
        assert design["multiplicity"]["primary"]["lower_tail"] == "1/240"
        assert design["multiplicity"]["primary"]["upper_tail"] == "239/240"
        assert design["multiplicity"]["native_reference"]["lower_tail"] == "1/320"
        assert design["multiplicity"]["native_reference"]["upper_tail"] == "319/320"

    def test_protocol_fingerprint_deterministic(self) -> None:
        first = protocol.build_design(_manifest())
        second = protocol.build_design(_manifest())
        assert first["protocol_fingerprint"] == second["protocol_fingerprint"]

    def test_completeness_rule_requires_full_pairing(self) -> None:
        design = protocol.build_design(_manifest())
        assert design["completeness_rule"]["row_substitution"] is False
        assert design["completeness_rule"]["winner_agreement_filter"] is False

    def test_expected_evaluation_budget(self) -> None:
        design = protocol.build_design(_manifest())
        assert design["expected_evaluations"]["items_per_model"] == 1596
        assert design["expected_evaluations"]["per_model"] == 1596 * 5
        assert design["expected_evaluations"]["total_two_models"] == 2 * 1596 * 5

    def test_ground_truth_semantics_is_mmlu_specific(self) -> None:
        identity = protocol.ground_truth_semantics()
        payload = identity.canonical_payload()
        assert payload["taxonomy_id"] == protocol.R3_GT_TAXONOMY_ID
        assert payload["taxonomy_id"] != "choice-signal-routing-three-way"
        assert payload["labeling_rule"] == protocol.R3_GT_LABELING_RULE


class TestChildPlans:
    def test_child_plans_share_items_anchors_and_labels(self) -> None:
        manifest = _manifest()
        primary = protocol.build_child_plan(
            manifest,
            model_id=protocol.PRIMARY_MODEL_ID,
            model_revision=protocol.PRIMARY_MODEL_REVISION,
        )
        replication = protocol.build_child_plan(
            manifest,
            model_id=protocol.REPLICATION_MODEL_ID,
            model_revision=protocol.REPLICATION_MODEL_REVISION,
        )
        assert primary.items == replication.items
        assert primary.anchor_selection_id == replication.anchor_selection_id
        assert (
            primary.ground_truth_semantics_fingerprint
            == replication.ground_truth_semantics_fingerprint
        )
        assert primary.fingerprint != replication.fingerprint

    def test_child_plan_item_count_and_splits(self) -> None:
        manifest = _manifest()
        plan = protocol.build_child_plan(
            manifest,
            model_id=protocol.PRIMARY_MODEL_ID,
            model_revision=protocol.PRIMARY_MODEL_REVISION,
        )
        assert len(plan.items) == 1596
        split_counts = {"train": 0, "test": 0}
        for item in plan.items:
            split_counts[item.split.value] += 1
        assert split_counts == {"train": 456, "test": 1140}

    def test_anchor_uses_candidate_names_only(self) -> None:
        manifest = _manifest()
        plan = protocol.build_child_plan(
            manifest,
            model_id=protocol.PRIMARY_MODEL_ID,
            model_revision=protocol.PRIMARY_MODEL_REVISION,
        )
        for item in plan.items[:5]:
            assert item.anchor_value in population.R3_CANDIDATE_NAMES


class TestValidation:
    def test_validate_protocol_accepts_the_design(self) -> None:
        protocol.validate_protocol(protocol.build_design(_manifest()))

    def test_validate_protocol_rejects_tampering(self) -> None:
        design = protocol.build_design(_manifest())
        tampered = copy.deepcopy(design)
        tampered["protocol_fingerprint"] = "0" * 64
        try:
            protocol.validate_protocol(tampered)
        except protocol.ProtocolError:
            return
        raise AssertionError("expected tampered protocol to fail validation")

    def test_validate_protocol_rejects_wrong_family_size(self) -> None:
        design = protocol.build_design(_manifest())
        tampered = copy.deepcopy(design)
        tampered["primary_contrasts"] = tampered["primary_contrasts"][:-1]
        try:
            protocol.validate_protocol(tampered)
        except protocol.ProtocolError:
            return
        raise AssertionError("expected wrong contrast count to fail validation")
