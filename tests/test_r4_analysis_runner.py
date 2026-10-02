"""Synthetic-only engineering tests for the R4 integrated formal analysis runner.

These tests exercise ``experiments/calibration_transport/run_r4_analysis.py``
with invented fixtures and with the frozen *structure* of the real inputs. They
never fit a calibrator on a study row, never compute a study Brier/LogLoss/Delta,
never bootstrap a study resample and never produce a scientific outcome.

The structural ``--validate-only`` path is exercised against the real frozen raw
evidence, because that is exactly what the task requires it to do: verify
hashes, fingerprints, row identities, counts, schema, unit mapping and
dependency availability, and compute nothing.

Formal R4 calibration / inference / predictor validation remains unauthorized.
"""

from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TRANSPORT_DIR = REPO_ROOT / "experiments" / "calibration_transport"
RUNNER_PATH = TRANSPORT_DIR / "run_r4_analysis.py"

FORMAL_ANALYSIS_ROOT = Path("/root/rivermind-data/r4-formal-analysis")


def _load_runner():
    if "run_r4_analysis" in sys.modules:
        return sys.modules["run_r4_analysis"]
    spec = importlib.util.spec_from_file_location("run_r4_analysis", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_r4_analysis"] = module
    spec.loader.exec_module(module)
    return module


runner = _load_runner()


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def authority():
    return runner.load_frozen_authority()


@pytest.fixture(scope="module")
def cells():
    return runner.load_cells()


@pytest.fixture(scope="module")
def synthetic_primary(authority, cells):
    """An invented panel over the current-generation cells only."""
    current = [cell for cell in cells if cell.model_role == "current-generation"]
    return runner.build_synthetic_panel(authority, current)


@pytest.fixture(scope="module")
def synthetic_legacy(authority, cells):
    """An invented panel over the legacy-lineage cells only."""
    legacy = [cell for cell in cells if cell.model_role != "current-generation"]
    return runner.build_synthetic_panel(authority, legacy)


@pytest.fixture(scope="module")
def synthetic_all(synthetic_primary, synthetic_legacy):
    """The union panel: the frozen predictor spans every model role."""
    return runner.merge_panels(synthetic_primary, synthetic_legacy)


@pytest.fixture(scope="module")
def current_populations(cells):
    return tuple(
        dict.fromkeys(
            cell.population_id for cell in cells if cell.model_role == "current-generation"
        )
    )


@pytest.fixture(scope="module")
def legacy_populations(cells):
    return tuple(
        dict.fromkeys(
            cell.population_id for cell in cells if cell.model_role != "current-generation"
        )
    )


def _namespace(**kwargs) -> argparse.Namespace:
    base = {
        "validate_only": False,
        "synthetic_qualification": False,
        "execute_formal_analysis": False,
        "formal_root": str(FORMAL_ANALYSIS_ROOT),
        "qualification_root": str(runner.QUALIFICATION_ROOT),
        "evidence_root": str(runner.RAW_EVIDENCE_ROOT),
        "synthetic_replicates": 4,
    }
    base.update(kwargs)
    return argparse.Namespace(**base)


# --------------------------------------------------------------------------- #
# CLI surface and safe-by-default behaviour
# --------------------------------------------------------------------------- #


def test_parser_exposes_the_three_explicit_modes():
    parser = runner.build_parser()
    options = {action.dest for action in parser._actions}
    assert {"validate_only", "synthetic_qualification", "execute_formal_analysis"} <= options


def test_parser_defaults_are_safe():
    args = runner.build_parser().parse_args([])
    assert args.validate_only is False
    assert args.synthetic_qualification is False
    assert args.execute_formal_analysis is False


def test_parser_has_no_fixture_injection_option():
    parser = runner.build_parser()
    for action in parser._actions:
        assert "fixture" not in action.dest
        assert "evidence-root" not in str(action.option_strings) or action.dest == "evidence_root"


def test_main_without_a_mode_refuses_to_run():
    with pytest.raises(SystemExit) as excinfo:
        runner.main([])
    assert excinfo.value.code == 2


def test_main_refuses_two_modes_at_once():
    with pytest.raises(SystemExit) as excinfo:
        runner.main(["--validate-only", "--synthetic-qualification"])
    assert excinfo.value.code == 2


def test_main_refuses_formal_mode_combined_with_synthetic_mode():
    with pytest.raises(SystemExit) as excinfo:
        runner.main(["--execute-formal-analysis", "--synthetic-qualification"])
    assert excinfo.value.code == 2


def test_main_rejects_a_non_positive_synthetic_replicate_count():
    with pytest.raises(SystemExit) as excinfo:
        runner.main(["--synthetic-qualification", "--synthetic-replicates", "0"])
    assert excinfo.value.code == 2


def test_formal_mode_requires_the_explicit_flag_not_the_default():
    args = runner.build_parser().parse_args([])
    assert args.execute_formal_analysis is False


# --------------------------------------------------------------------------- #
# Real-input validate-only mode
# --------------------------------------------------------------------------- #


def test_validate_only_reports_the_frozen_structure(capsys):
    assert runner.validate_only(_namespace(validate_only=True)) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "PASS"
    assert payload["frozen_authority_verified"] is True
    assert payload["cells"] == 16
    assert payload["rows"] == 100728
    assert payload["current_directional_units"] == 24
    assert payload["legacy_directional_units"] == 8
    assert payload["problems"] == []


def test_validate_only_computes_no_scientific_output(capsys):
    assert runner.validate_only(_namespace(validate_only=True)) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["calibrator_fits"] == 0
    assert payload["metrics_computed"] == 0
    assert payload["bootstrap_draws"] == 0
    assert payload["predictor_values"] == 0
    assert payload["scientific_outputs_computed"] is False


def test_validate_only_never_fits_bootstraps_or_predicts(monkeypatch, capsys):
    """The outcome firewall: validate-only must not reach any statistics."""

    def forbidden(*args, **kwargs):
        raise AssertionError("validate-only attempted a scientific computation")

    for name in (
        "fit_procedure",
        "point_estimates",
        "run_test_bootstrap",
        "run_refit_blocks",
        "run_predictor_bootstrap",
        "build_predictor_measurements",
        "oracle_risk_matrix",
    ):
        monkeypatch.setattr(runner, name, forbidden)
    assert runner.validate_only(_namespace(validate_only=True)) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "PASS"


def test_validate_only_does_not_touch_the_formal_output_root():
    assert not FORMAL_ANALYSIS_ROOT.exists() or not any(FORMAL_ANALYSIS_ROOT.iterdir())


# --------------------------------------------------------------------------- #
# Frozen authority verification
# --------------------------------------------------------------------------- #


def test_frozen_authority_carries_the_frozen_identities(authority):
    assert authority.measurement_contract_fingerprint == runner.MEASUREMENT_CONTRACT_FINGERPRINT
    assert authority.final_protocol_fingerprint == runner.FINAL_PROTOCOL_FINGERPRINT
    assert authority.execution_manifest_fingerprint == runner.EXECUTION_MANIFEST_FINGERPRINT
    assert authority.ledger_fingerprint == runner.LEDGER_FINGERPRINT
    assert authority.registry_fingerprint == runner.ANALYSIS_REGISTRY_FINGERPRINT
    assert authority.dependency_graph_fingerprint == runner.ANALYSIS_DEPENDENCY_GRAPH_FINGERPRINT
    assert authority.raw_measurement_freeze_commit == runner.RAW_MEASUREMENT_FREEZE_COMMIT


def test_frozen_authority_preserves_the_frozen_orders(authority):
    assert authority.direction_order == ("CAT->OVR", "OVR->CAT")
    assert authority.procedure_order == (
        "P-low",
        "P-historical",
        "L-low",
        "L-historical",
        "I-isotonic",
        "B-beta",
    )
    assert len(authority.model_order) == 6
    assert len(authority.population_order) == 3


def test_frozen_authority_rejects_a_tampered_frozen_file(monkeypatch):
    tampered = dict(runner.FROZEN_FILES)
    tampered["R4_POPULATION_FREEZE.md"] = "0" * 64
    monkeypatch.setattr(runner, "FROZEN_FILES", tampered)
    with pytest.raises(runner.R4AnalysisAuthorityError):
        runner.load_frozen_authority()


def test_frozen_authority_rejects_a_tampered_frozen_implementation(monkeypatch):
    tampered = dict(runner.FROZEN_SCIENTIFIC_IMPLEMENTATIONS)
    tampered["r3_protocol.py"] = "0" * 64
    monkeypatch.setattr(runner, "FROZEN_SCIENTIFIC_IMPLEMENTATIONS", tampered)
    with pytest.raises(runner.R4AnalysisAuthorityError):
        runner.load_frozen_authority()


def test_frozen_authority_rejects_an_unknown_frozen_file(monkeypatch):
    tampered = dict(runner.FROZEN_FILES)
    tampered["NOT_A_FROZEN_ARTIFACT.json"] = "0" * 64
    monkeypatch.setattr(runner, "FROZEN_FILES", tampered)
    with pytest.raises(runner.R4AnalysisAuthorityError):
        runner.load_frozen_authority()


# --------------------------------------------------------------------------- #
# Frozen unit registry
# --------------------------------------------------------------------------- #


def test_registry_exposes_sixteen_cells(cells):
    assert len(cells) == 16
    assert {cell.train_budget for cell in cells} == {"N456", "N912"}


def test_registry_has_no_legacy_mmlu_cell(cells):
    legacy = [cell for cell in cells if cell.model_role != "current-generation"]
    assert len(legacy) == 4
    assert all(cell.population_key != "mmlu" for cell in legacy)


def test_unit_registry_is_twenty_four_current_and_eight_legacy(cells, authority):
    units = runner.enumerate_units(cells, authority)
    assert len(units) == 32
    current = runner.primary_units(units)
    legacy = runner.legacy_units(units)
    assert len(current) == 24
    assert len(legacy) == 8
    assert {unit.role for unit in current} == {"current-generation"}
    assert {unit.role for unit in legacy} == {"legacy-lineage"}


def test_current_units_are_four_models_by_three_populations_by_two_directions(cells, authority):
    units = runner.primary_units(runner.enumerate_units(cells, authority))
    assert len({unit.model_key for unit in units}) == 4
    assert len({unit.population_id for unit in units}) == 3
    assert {unit.direction_id for unit in units} == {"CAT->OVR", "OVR->CAT"}


def test_legacy_units_are_two_models_by_two_populations_by_two_directions(cells, authority):
    units = runner.legacy_units(runner.enumerate_units(cells, authority))
    assert len({unit.model_key for unit in units}) == 2
    assert len({unit.population_id for unit in units}) == 2
    assert {unit.direction_id for unit in units} == {"CAT->OVR", "OVR->CAT"}


def test_unit_ids_are_unique(cells, authority):
    units = runner.enumerate_units(cells, authority)
    assert len({unit.unit_id for unit in units}) == len(units)


def test_unit_order_is_deterministic(cells, authority):
    first = [unit.unit_id for unit in runner.enumerate_units(cells, authority)]
    second = [unit.unit_id for unit in runner.enumerate_units(cells, authority)]
    assert first == second


# --------------------------------------------------------------------------- #
# Raw-evidence structural loading
# --------------------------------------------------------------------------- #


def _smallest_cell(cells):
    return min(cells, key=lambda cell: sum(cell.split_counts.values()))


def test_cell_payload_hash_verification(cells):
    cell = _smallest_cell(cells)
    payload = runner.load_cell_payload(cell)
    assert payload["evidence_fingerprint"] == cell.evidence_fingerprint
    assert payload["structural_counts"]["items"] == sum(cell.split_counts.values())


def test_cell_payload_rejects_a_corrupted_hash(cells, monkeypatch):
    cell = _smallest_cell(cells)
    broken = cell.__class__(**{**cell.__dict__, "sha256": "0" * 64})
    with pytest.raises(runner.R4AnalysisInputError):
        runner.load_cell_payload(broken)


def test_rows_by_split_matches_the_registry_counts(cells):
    cell = _smallest_cell(cells)
    splits = runner.rows_by_split(runner.load_cell_payload(cell), cell)
    for split, expected in cell.split_counts.items():
        assert len(splits[split]) == expected


def test_item_to_row_maps_the_frozen_fields(cells):
    cell = _smallest_cell(cells)
    payload = runner.load_cell_payload(cell)
    item = next(iter(runner.iter_items(payload)))
    row = runner.item_to_row(item, cell, cell.population_id)
    assert row.item_id == item["item_id"]
    assert row.population_id == cell.population_id
    assert row.stratum == item["stratum"]
    assert row.label == item["fixed_event"]
    assert row.cat_score == item["cat"]["anchor_score"]
    assert row.ovr_score == item["ovr"]["probability_true"]
    assert row.anchor_index == int(item["candidate_order"].index(str(item["anchor"])))
    assert row.cluster_id == item["group_id"]


def test_structural_item_check_rejects_an_unscored_measurement(cells):
    cell = _smallest_cell(cells)
    payload = runner.load_cell_payload(cell)
    item = dict(next(iter(runner.iter_items(payload))))
    item["cat"] = {**item["cat"], "status": "unavailable"}
    with pytest.raises(runner.R4AnalysisInputError):
        runner.structural_item_check(item, cell.cell_id)


def test_structural_item_check_rejects_a_foreign_split(cells):
    cell = _smallest_cell(cells)
    payload = runner.load_cell_payload(cell)
    item = dict(next(iter(runner.iter_items(payload))))
    item["split"] = "OTHER"
    with pytest.raises(runner.R4AnalysisInputError):
        runner.structural_item_check(item, cell.cell_id)


# --------------------------------------------------------------------------- #
# Synthetic fixture identity
# --------------------------------------------------------------------------- #


def test_synthetic_panel_is_marked_synthetic(synthetic_all):
    assert runner.SYNTHETIC_FIXTURE_MARKER == "SYNTHETIC_ONLY_NOT_SCIENTIFIC_EVIDENCE"


def test_synthetic_panel_spans_every_cell_model_and_population(synthetic_all, cells):
    keys = set(synthetic_all.train_rows)
    expected = {(cell.model_key, cell.population_id) for cell in cells}
    assert keys == expected


def test_synthetic_scores_are_deterministic_and_invented(authority):
    first = runner._synthetic_score("model", "population", "item", "CAT")
    second = runner._synthetic_score("model", "population", "item", "CAT")
    third = runner._synthetic_score("model", "population", "other", "CAT")
    assert first == second
    assert first != third
    assert 0.0 < first < 1.0


def test_synthetic_rows_are_structurally_valid(synthetic_all):
    for rows in synthetic_all.train_rows.values():
        for row in rows:
            assert 0.0 < row.cat_score < 1.0
            assert 0.0 < row.ovr_score < 1.0
            assert row.label in (0, 1)
            assert 0 <= row.anchor_index < 4


def test_synthetic_metadata_never_reuses_a_study_count(authority):
    metadata = runner._synthetic_metadata(authority)
    for meta in metadata.values():
        strata = runner.SYNTHETIC_STRATA_PER_POPULATION
        assert meta.test_count == strata * runner.SYNTHETIC_TEST_PER_STRATUM
        assert meta.train_count == strata * runner.SYNTHETIC_TRAIN_PER_STRATUM
        assert meta.test_count != 10042
        assert meta.test_count != 1140


def test_merge_panels_rejects_an_empty_sequence():
    with pytest.raises(runner.R4AnalysisContractViolation):
        runner.merge_panels()


# --------------------------------------------------------------------------- #
# Calibration-family wiring
# --------------------------------------------------------------------------- #


def test_fit_procedure_covers_the_six_frozen_procedures(synthetic_all):
    procedures = {key[2].split("|")[0] for key in synthetic_all.fits}
    assert procedures == {
        "P-low",
        "P-historical",
        "L-low",
        "L-historical",
        "I-isotonic",
        "B-beta",
    }


def test_fit_procedure_marks_every_synthetic_fit_available(synthetic_all):
    assert {fit.status for fit in synthetic_all.fits.values()} == {runner.AVAILABLE}


def test_fit_procedure_rejects_an_unfrozen_procedure(synthetic_all):
    rows = next(iter(synthetic_all.train_rows.values()))
    with pytest.raises(runner.R4AnalysisUnfrozenChoice):
        runner.fit_procedure(procedure="temperature", train_rows=rows, measurement="CAT")


def test_available_procedures_is_fail_closed(synthetic_primary, cells, current_populations):
    models = runner._panel_models(synthetic_primary, current_populations)
    assert runner.available_procedures(
        synthetic_primary, models=models, populations=current_populations
    ) == runner.r4_inference.ALL_PROCEDURES


def test_available_procedures_drops_a_missing_procedure(synthetic_primary, current_populations):
    models = runner._panel_models(synthetic_primary, current_populations)
    stripped = runner.PanelInputs(
        authority=synthetic_primary.authority,
        model_keys=synthetic_primary.model_keys,
        train_rows=synthetic_primary.train_rows,
        test_rows=synthetic_primary.test_rows,
        fits={
            key: value
            for key, value in synthetic_primary.fits.items()
            if key[2] != "B-beta"
        },
        budget=synthetic_primary.budget,
    )
    available = runner.available_procedures(
        stripped, models=models, populations=current_populations
    )
    assert "B-beta" not in available
    assert set(available) == set(runner.r4_inference.LOGISTIC_CORE_PROCEDURES) | {"I-isotonic"}


# --------------------------------------------------------------------------- #
# Oracle equivalence (runner orchestration vs direct frozen calls)
# --------------------------------------------------------------------------- #


def test_point_estimates_match_the_direct_frozen_oracle(synthetic_primary, current_populations):
    models = runner._panel_models(synthetic_primary, current_populations)
    estimates = runner.point_estimates(
        synthetic_primary, models=models, populations=current_populations
    )
    checked = 0
    for model in models:
        for population in current_populations:
            for direction in synthetic_primary.authority.direction_order:
                for procedure in synthetic_primary.authority.procedure_order:
                    key = f"{model}|{population}|{direction}|{procedure}"
                    entry = estimates[key]
                    assert entry["status"] == runner.AVAILABLE
                    oracle = runner.oracle_risk_matrix(
                        synthetic_primary,
                        model_key=model,
                        population_id=population,
                        direction=direction,
                        procedure=procedure,
                    )
                    for field in (
                        "r_raw",
                        "r_native",
                        "r_cross",
                        "delta_native",
                        "delta_deploy",
                        "delta_transport",
                    ):
                        assert getattr(entry["risk_matrix"], field) == getattr(oracle, field)
                    checked += 1
    assert checked == 4 * len(current_populations) * 2 * 6


def test_isotonic_oracle_equivalence(synthetic_primary, current_populations):
    model = runner._panel_models(synthetic_primary, current_populations)[0]
    population = current_populations[0]
    for direction in synthetic_primary.authority.direction_order:
        key = f"{model}|{population}|{direction}|I-isotonic"
        entry = runner.point_estimates(
            synthetic_primary, models=(model,), populations=(population,)
        )[key]
        oracle = runner.oracle_risk_matrix(
            synthetic_primary,
            model_key=model,
            population_id=population,
            direction=direction,
            procedure="I-isotonic",
        )
        assert entry["risk_matrix"].delta_transport == oracle.delta_transport


def test_beta_oracle_equivalence(synthetic_primary, current_populations):
    model = runner._panel_models(synthetic_primary, current_populations)[0]
    population = current_populations[0]
    for direction in synthetic_primary.authority.direction_order:
        key = f"{model}|{population}|{direction}|B-beta"
        entry = runner.point_estimates(
            synthetic_primary, models=(model,), populations=(population,)
        )[key]
        oracle = runner.oracle_risk_matrix(
            synthetic_primary,
            model_key=model,
            population_id=population,
            direction=direction,
            procedure="B-beta",
        )
        assert entry["risk_matrix"].delta_deploy == oracle.delta_deploy


def test_metric_oracle_holds_the_extended_real_contract():
    checks = runner.oracle_metric_checks()
    assert checks["mean_brier"] == 0.28125
    assert checks["mean_logloss_state"] == "FINITE"
    assert checks["logloss_zero_mass_correct_state"] == "FINITE"
    assert checks["logloss_zero_mass_incorrect_state"] == "POSITIVE_INFINITY"
    assert checks["inf_minus_inf_state"] == "UNDEFINED_EXTENDED_REAL"
    assert checks["inf_plus_finite_state"] == "POSITIVE_INFINITY"
    assert checks["undefined_constant"] == "UNDEFINED_EXTENDED_REAL"


def test_metric_oracle_never_clips_the_zero_mass_logloss():
    assert runner.r4_inference.logloss_loss(0.0, 1).state == "POSITIVE_INFINITY"
    assert runner.r4_inference.logloss_loss(1.0, 0).state == "POSITIVE_INFINITY"


# --------------------------------------------------------------------------- #
# Bootstrap sharing / cluster integrity
# --------------------------------------------------------------------------- #


def test_shared_test_draw_is_identical_across_models(synthetic_primary, current_populations):
    metadata = synthetic_primary.authority.population_metadata
    for population in current_populations:
        payloads = {
            model: runner.r4_inference.build_test_draw(
                synthetic_primary.test_rows[(model, population)], metadata[population], 0
            ).draw_identity_payload()
            for model in runner._panel_models(synthetic_primary, (population,))
        }
        assert len(set(json.dumps(p, sort_keys=True) for p in payloads.values())) == 1


def test_cluster_integrity_holds_for_the_grouped_population(synthetic_primary, current_populations):
    metadata = synthetic_primary.authority.population_metadata
    grouped = [p for p in current_populations if metadata[p].group_field is not None]
    assert grouped
    for population in grouped:
        for model in runner._panel_models(synthetic_primary, (population,)):
            rows = synthetic_primary.test_rows[(model, population)]
            draw = runner.r4_inference.build_test_draw(rows, metadata[population], 3)
            assert runner.cluster_integrity(draw, rows) is True


def test_cluster_integrity_detects_a_split_cluster(synthetic_primary, current_populations):
    metadata = synthetic_primary.authority.population_metadata
    population = next(p for p in current_populations if metadata[p].group_field is not None)
    model = runner._panel_models(synthetic_primary, (population,))[0]
    rows = synthetic_primary.test_rows[(model, population)]
    draw = runner.r4_inference.build_test_draw(rows, metadata[population], 1)
    lookup = {row.item_id: row.cluster_id for row in rows}
    counts: dict[str, int] = {}
    for occurrence in draw.occurrences:
        cluster = lookup[occurrence.item_id]
        counts[cluster] = counts.get(cluster, 0) + 1
    target = next(cluster for cluster, count in counts.items() if count > 1)
    # Drop exactly one occurrence of a cluster the draw selected more than once.
    dropped = False
    trimmed = []
    for occurrence in draw.occurrences:
        if not dropped and lookup[occurrence.item_id] == target:
            dropped = True
            continue
        trimmed.append(occurrence)
    assert dropped
    broken = runner.TestDraw(
        population_id=draw.population_id,
        replicate_index=draw.replicate_index,
        protocol_id=draw.protocol_id,
        protocol_version=draw.protocol_version,
        mode=draw.mode,
        stratum_order=draw.stratum_order,
        per_stratum_occurrences=draw.per_stratum_occurrences,
        occurrences=tuple(trimmed),
        provenance=draw.provenance,
    )
    assert runner.cluster_integrity(broken, rows) is False


def test_reindexed_rows_follow_the_draw_occurrences(synthetic_primary, current_populations):
    metadata = synthetic_primary.authority.population_metadata
    population = current_populations[0]
    model = runner._panel_models(synthetic_primary, (population,))[0]
    rows = synthetic_primary.test_rows[(model, population)]
    draw = runner.r4_inference.build_test_draw(rows, metadata[population], 2)
    reindexed = runner._reindexed_rows(draw, rows)
    assert [row.item_id for row in reindexed] == [o.item_id for o in draw.occurrences]
    assert len(reindexed) == draw.expanded_row_count


def test_reindexed_rows_fail_closed_on_a_foreign_draw(synthetic_primary, current_populations):
    metadata = synthetic_primary.authority.population_metadata
    population = current_populations[0]
    models = runner._panel_models(synthetic_primary, (population,))
    draw = runner.r4_inference.build_test_draw(
        synthetic_primary.test_rows[(models[0], population)], metadata[population], 0
    )
    with pytest.raises(runner.R4AnalysisInputError):
        runner._reindexed_rows(draw, ())


# --------------------------------------------------------------------------- #
# Multiplicity / dependency propagation
# --------------------------------------------------------------------------- #


def test_full_panel_keeps_every_family_complete(synthetic_primary, current_populations):
    models = runner._panel_models(synthetic_primary, current_populations)
    bootstrap = runner.run_test_bootstrap(
        synthetic_primary,
        models=models,
        populations=current_populations,
        procedures=runner.r4_inference.ALL_PROCEDURES,
        replicates=4,
    )
    status = bootstrap.family_status()
    assert status["primary"]["family_size"] == 12
    assert status["primary"]["complete_count"] == 12
    assert status["secondary_extension"]["family_size"] == 8
    assert status["secondary_extension"]["complete_count"] == 8
    assert status["secondary_direction_difference"]["family_size"] == 6
    assert status["secondary_direction_difference"]["complete_count"] == 6
    assert status["secondary_native_reference"]["family_size"] == 12
    assert status["secondary_native_reference"]["complete_count"] == 12


def test_core4_only_keeps_primary_and_degrades_the_extensions(
    synthetic_primary, current_populations
):
    models = runner._panel_models(synthetic_primary, current_populations)
    bootstrap = runner.run_test_bootstrap(
        synthetic_primary,
        models=models,
        populations=current_populations,
        procedures=runner.r4_inference.LOGISTIC_CORE_PROCEDURES,
        replicates=4,
    )
    status = bootstrap.family_status()
    assert status["primary"]["complete_count"] == status["primary"]["family_size"] == 12
    assert (
        status["secondary_direction_difference"]["complete_count"]
        == status["secondary_direction_difference"]["family_size"]
        == 6
    )
    assert status["secondary_extension"]["complete_count"] == 0
    assert status["secondary_extension"]["incomplete_count"] == 8
    assert status["secondary_extension"]["family_size"] == 8
    assert status["secondary_native_reference"]["complete_count"] == 8
    assert status["secondary_native_reference"]["incomplete_count"] == 4


def test_families_are_never_shrunk_by_missing_members(synthetic_primary, current_populations):
    models = runner._panel_models(synthetic_primary, current_populations)
    bootstrap = runner.run_test_bootstrap(
        synthetic_primary,
        models=models,
        populations=current_populations,
        procedures=runner.r4_inference.LOGISTIC_CORE_PROCEDURES,
        replicates=4,
    )
    status = bootstrap.family_status()
    assert len(status["secondary_extension"]["members"]) == 8
    assert len(status["secondary_native_reference"]["members"]) == 12


def test_primary_contrasts_are_twelve(synthetic_primary, current_populations):
    models = runner._panel_models(synthetic_primary, current_populations)
    bootstrap = runner.run_test_bootstrap(
        synthetic_primary,
        models=models,
        populations=current_populations,
        procedures=runner.r4_inference.ALL_PROCEDURES,
        replicates=4,
    )
    assert len(bootstrap.primary_contrasts) == 12
    assert len(bootstrap.direction_differences) == 6
    assert len(bootstrap.extension_panel) == 8
    assert len(bootstrap.native_reference) == 12


# --------------------------------------------------------------------------- #
# TRAIN-refit block
# --------------------------------------------------------------------------- #


def test_refit_blocks_are_complete_on_the_synthetic_panel(synthetic_primary, current_populations):
    models = runner._panel_models(synthetic_primary, current_populations)
    blocks = runner.run_refit_blocks(
        synthetic_primary,
        models=models,
        populations=current_populations,
        procedures=runner.r4_inference.LOGISTIC_CORE_PROCEDURES,
        replicates=2,
    )
    assert blocks
    assert {block.status for block in blocks.values()} == {"COMPLETE"}
    assert all(block.interval is not None for block in blocks.values())


def test_refit_block_keys_cover_both_estimands(synthetic_primary, current_populations):
    models = runner._panel_models(synthetic_primary, current_populations)
    blocks = runner.run_refit_blocks(
        synthetic_primary,
        models=models,
        populations=current_populations,
        procedures=runner.r4_inference.LOGISTIC_CORE_PROCEDURES,
        replicates=2,
    )
    assert any("Delta_deploy" in key for key in blocks)
    assert any("Delta_transport" in key for key in blocks)


# --------------------------------------------------------------------------- #
# Predictor wiring
# --------------------------------------------------------------------------- #


def test_frozen_predictor_units_are_eight_sixteen_eight():
    units = runner.frozen_predictor_units()
    roles: dict[str, int] = {}
    for unit in units:
        roles[unit.analysis_role] = roles.get(unit.analysis_role, 0) + 1
    assert roles[runner.r4_predictor.ROLE_DEVELOPMENT] == 8
    assert roles[runner.r4_predictor.ROLE_PRIMARY_VALIDATION] == 16
    assert roles[runner.r4_predictor.ROLE_LEGACY_EXTENSION] == 8
    assert len(units) == 32


def test_predictor_measurements_cover_every_frozen_unit(synthetic_all):
    measurements = runner.build_predictor_measurements(synthetic_all)
    assert len(measurements) == 32
    assert {m.unit.unit_id for m in measurements} == {
        unit.unit_id for unit in runner.frozen_predictor_units()
    }


def test_predictor_measurements_carry_the_frozen_unit_roles(synthetic_all):
    measurements = runner.build_predictor_measurements(synthetic_all)
    roles: dict[str, int] = {}
    for measurement in measurements:
        role = measurement.unit.analysis_role
        roles[role] = roles.get(role, 0) + 1
    assert roles[runner.r4_predictor.ROLE_DEVELOPMENT] == 8
    assert roles[runner.r4_predictor.ROLE_PRIMARY_VALIDATION] == 16
    assert roles[runner.r4_predictor.ROLE_LEGACY_EXTENSION] == 8


def test_predictor_point_rows_are_sixteen_heldout_units(synthetic_all):
    rows = runner.predictor_point_rows(runner.build_predictor_measurements(synthetic_all))
    assert len(rows) == 16
    assert {row.unit.analysis_role for row in rows} == {
        runner.r4_predictor.ROLE_PRIMARY_VALIDATION
    }


def test_predictor_point_rows_use_strict_exceedance_and_wasserstein(synthetic_all):
    rows = runner.predictor_point_rows(runner.build_predictor_measurements(synthetic_all))
    for row in rows:
        assert 0.0 <= row.x_range <= 1.0
        assert row.x_wasserstein1 >= 0.0
        assert row.y_transport_core is not None
        assert row.y_deploy_core is not None


def test_predictor_point_statistic_matches_the_frozen_function(synthetic_all):
    rows = runner.predictor_point_rows(runner.build_predictor_measurements(synthetic_all))
    assert runner.r4_predictor.primary_statistic(rows) == runner.r4_predictor.primary_statistic(
        rows
    )


def test_predictor_bootstrap_shares_one_draw_between_x_and_y(synthetic_all):
    measurements = runner.build_predictor_measurements(synthetic_all)
    rows = runner.predictor_point_rows(measurements)
    point = runner.r4_predictor.primary_statistic(rows)
    populations = tuple(
        dict.fromkeys(m.unit.population_id for m in measurements)
    )
    model = next(iter(runner._panel_models(synthetic_all, populations)))
    first = runner.run_predictor_bootstrap(
        measurements=measurements,
        canonical_rows={p: synthetic_all.test_rows[(model, p)] for p in populations},
        metadata={p: synthetic_all.authority.population_metadata[p] for p in populations},
        replicates=4,
        point_estimate=point,
    )
    second = runner.run_predictor_bootstrap(
        measurements=measurements,
        canonical_rows={p: synthetic_all.test_rows[(model, p)] for p in populations},
        metadata={p: synthetic_all.authority.population_metadata[p] for p in populations},
        replicates=4,
        point_estimate=point,
    )
    assert first.payload() == second.payload()
    assert first.planned_replicates == 4
    assert first.tail_rule == "1/40/39/40"


def test_predictor_bootstrap_reports_complete_on_the_synthetic_panel(synthetic_all):
    measurements = runner.build_predictor_measurements(synthetic_all)
    rows = runner.predictor_point_rows(measurements)
    populations = tuple(dict.fromkeys(m.unit.population_id for m in measurements))
    model = next(iter(runner._panel_models(synthetic_all, populations)))
    result = runner.run_predictor_bootstrap(
        measurements=measurements,
        canonical_rows={p: synthetic_all.test_rows[(model, p)] for p in populations},
        metadata={p: synthetic_all.authority.population_metadata[p] for p in populations},
        replicates=8,
        point_estimate=runner.r4_predictor.primary_statistic(rows),
    )
    assert result.status in ("COMPLETE", "INCOMPLETE")
    if result.status == "COMPLETE":
        assert result.interval() is not None


def test_predictor_bootstrap_is_undefined_for_a_constant_predictor(synthetic_all, monkeypatch):
    measurements = runner.build_predictor_measurements(synthetic_all)
    populations = tuple(dict.fromkeys(m.unit.population_id for m in measurements))
    model = next(iter(runner._panel_models(synthetic_all, populations)))
    monkeypatch.setattr(
        runner.r4_predictor,
        "range_exceedance_warning",
        lambda source, target: runner.r4_predictor.RangeExceedanceResult(
            source_count=len(tuple(source)),
            target_count=len(tuple(target)),
            q_low=0.0,
            q_high=1.0,
            outside_count=0,
            fraction_outside=0.0,
        ),
    )
    result = runner.run_predictor_bootstrap(
        measurements=measurements,
        canonical_rows={p: synthetic_all.test_rows[(model, p)] for p in populations},
        metadata={p: synthetic_all.authority.population_metadata[p] for p in populations},
        replicates=4,
        point_estimate=0.0,
    )
    assert result.status == "INCOMPLETE"
    assert result.undefined_replicates > 0


# --------------------------------------------------------------------------- #
# Qualification report / determinism
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def synthetic_dag(authority, cells, current_populations, legacy_populations):
    """The full synthetic DagRun (primary + legacy + nested N912)."""
    current = [cell for cell in cells if cell.model_role == "current-generation"]
    legacy = [cell for cell in cells if cell.model_role != "current-generation"]
    n912_cells = [
        cell
        for cell in current
        if cell.population_id
        in (
            runner.r4_inference.HELLASWAG_POPULATION_ID,
            runner.r4_inference.MEDMCQA_POPULATION_ID,
        )
    ]
    return runner.DagRun(
        authority=authority,
        primary=runner.build_synthetic_panel(authority, current),
        legacy=runner.build_synthetic_panel(authority, legacy),
        n912=runner.build_synthetic_panel(
            authority,
            n912_cells,
            train_per_stratum=2 * runner.SYNTHETIC_TRAIN_PER_STRATUM,
        ),
        primary_populations=current_populations,
        legacy_populations=legacy_populations,
        fixture_marker=runner.SYNTHETIC_FIXTURE_MARKER,
    )


def _run_dag_engine(dag, *, replicates: int = 2):
    return runner.run_dag_engine(
        dag,
        test_replicates=replicates,
        refit_replicates=2,
        predictor_replicates=replicates,
    )


def test_qualification_report_is_deterministic(synthetic_dag):
    engine = _run_dag_engine(synthetic_dag)
    first = runner.qualification_report(engine, synthetic_dag, replicates=2, role="primary")
    second = runner.qualification_report(engine, synthetic_dag, replicates=2, role="primary")
    assert runner.canonical_json(first) == runner.canonical_json(second)


def test_qualification_report_matches_the_oracle(synthetic_dag):
    engine = _run_dag_engine(synthetic_dag)
    report = runner.qualification_report(engine, synthetic_dag, replicates=2, role="primary")
    assert report["fixture_marker"] == runner.SYNTHETIC_FIXTURE_MARKER
    assert report["point_estimate_oracle_equal"] is True
    assert report["point_estimate_mismatches"] == []
    assert report["shared_draw_identity_equal_across_models"] is True
    assert report["cluster_never_split"] is True


def test_qualification_report_uses_the_shared_formal_engine(synthetic_dag):
    """The qualification report must read the engine output, never re-run a DAG."""
    engine = _run_dag_engine(synthetic_dag)
    report = runner.qualification_report(engine, synthetic_dag, replicates=2, role="primary")
    assert report["bootstrap_primary_contrasts"] == len(engine["bootstrap"].primary_contrasts)
    assert report["refit_blocks"] == len(engine["refit"])
    assert report["n912_robustness"]["refit_blocks"] == len(engine["n912_refit"])
    assert report["predictor"]["units_total"] == 32
    assert report["predictor"]["development_units"] == 8
    assert report["predictor"]["validation_units"] == 16
    assert report["predictor"]["legacy_units"] == 8
    assert report["legacy"]["unit_estimates"] == len(engine["legacy_estimates"])


def test_legacy_role_report_never_enters_the_primary_family(synthetic_dag):
    engine = _run_dag_engine(synthetic_dag)
    report = runner.qualification_report(engine, synthetic_dag, replicates=2, role="legacy")
    assert report["role"] == "legacy"
    assert set(report["models"]) == set(engine["legacy_models"])
    assert "predictor" not in report
    assert "n912_robustness" not in report


def test_refit_scope_covers_all_six_procedures_and_both_estimands(synthetic_dag):
    engine = _run_dag_engine(synthetic_dag)
    assert set(engine["refit"]) and set(engine["legacy_refit"])
    procedures = {key.split("|")[3] for key in engine["refit"]}
    estimands = {key.split("|")[4] for key in engine["refit"]}
    assert procedures == set(synthetic_dag.authority.procedure_order)
    assert estimands == {"Delta_deploy", "Delta_transport"}
    assert "Delta_native" not in estimands
    assert engine["n912_refit"]
    n912_populations = {key.split("|")[1] for key in engine["n912_refit"]}
    assert runner.r4_inference.MMLU_POPULATION_ID not in n912_populations


def test_logloss_formal_path_is_wired_on_the_engine(synthetic_dag):
    engine = _run_dag_engine(synthetic_dag)
    logloss = engine["logloss"]
    assert logloss.replicates == 2
    assert logloss.series
    assert set(logloss.series) == set(logloss.intervals)
    assert set(logloss.intervals) == set(logloss.undefined_replicates)
    for key, interval in logloss.intervals.items():
        if logloss.undefined_replicates[key]:
            assert interval is None
        if interval is not None:
            assert all(value.is_finite for value in logloss.series[key])
    report = runner.qualification_report(engine, synthetic_dag, replicates=2, role="primary")
    assert report["logloss_contrasts"] == len(logloss.series)
    assert report["logloss_status"] in ("COMPLETE", "INCOMPLETE")
    for key in report["logloss_undefined_contrasts"]:
        assert logloss.undefined_replicates[tuple(key.split("|"))]


def test_one_undefined_logloss_replicate_withholds_the_whole_interval():
    """Frozen rule: an UNDEFINED replicate -> INCOMPLETE, never a subset interval."""
    finite = runner.r4_inference.ExtendedReal(value=0.25, state="FINITE")
    undefined = runner.r4_inference.ExtendedReal(
        value=None, state=runner.r4_inference.UNDEFINED_EXTENDED_REAL
    )
    interval, status = runner._logloss_interval(
        (finite, undefined, finite),
        lower_tail=runner.r4_inference.PRIMARY_LOWER_TAIL,
        upper_tail=runner.r4_inference.PRIMARY_UPPER_TAIL,
    )
    assert interval is None
    assert status == "INCOMPLETE_UNDEFINED_EXTENDED_REAL"
    good, good_status = runner._logloss_interval(
        (finite, finite, finite),
        lower_tail=runner.r4_inference.PRIMARY_LOWER_TAIL,
        upper_tail=runner.r4_inference.PRIMARY_UPPER_TAIL,
    )
    assert good is not None
    assert good_status == "COMPLETE"


def test_logloss_paired_contrast_uses_exact_extended_real_algebra():
    """+inf - +inf -> UNDEFINED, and a finite difference stays finite."""
    undefined = runner._logloss_paired_contrast([0.0], [0.0], [1])
    assert undefined.state == runner.r4_inference.UNDEFINED_EXTENDED_REAL
    finite = runner._logloss_paired_contrast([0.5], [0.25], [1])
    assert finite.state == "FINITE"
    assert finite.value < 0.0


def test_n912_formal_path_is_paired_and_cannot_rescue(synthetic_dag):
    engine = _run_dag_engine(synthetic_dag)
    n912 = engine["n912_robustness"]
    assert n912["role"] == runner.r4_inference.N912_ROBUSTNESS_ROLE
    assert n912["cannot_rescue_primary"] is True
    assert n912["shared_test_draw_paired_by_replicate"] is True
    assert n912["comparisons"]
    for comparison in n912["comparisons"].values():
        assert comparison["status"] == "COMPLETE"
        assert comparison["n456_replicates"] == 2
        assert comparison["n912_replicates"] == 2
    pairing = runner.validate_n912_panels(
        synthetic_dag.primary,
        synthetic_dag.n912,
        models=engine["primary_models"],
        populations=(
            runner.r4_inference.HELLASWAG_POPULATION_ID,
            runner.r4_inference.MEDMCQA_POPULATION_ID,
        ),
    )
    assert pairing
    assert all(
        entry["train_456_subset_of_train_912"] is True
        and entry["test_identity_identical"] is True
        and entry["extension_count"] > 0
        for entry in pairing.values()
    )


def test_predictor_formal_path_uses_the_merged_panel(synthetic_dag):
    engine = _run_dag_engine(synthetic_dag)
    predictor = engine["predictor"]
    assert predictor.planned_replicates == 2
    assert len(engine["predictor_point_rows"]) == 16
    assert {row.unit.analysis_role for row in engine["predictor_point_rows"]} == {
        runner.r4_predictor.ROLE_PRIMARY_VALIDATION
    }


def test_engine_covers_every_frozen_dag_block(synthetic_dag):
    seen: list[str] = []
    engine = runner.run_dag_engine(
        synthetic_dag,
        test_replicates=2,
        refit_replicates=2,
        predictor_replicates=2,
        on_block=lambda **kwargs: seen.append(kwargs["block"]),
    )
    assert engine["artifact"]
    assert set(seen) >= {
        "input_load",
        "point_estimates",
        "n912_robustness",
        "test_bootstrap",
        "train_refit",
        "predictor",
        "final_assembly",
    }
    assert not any(
        value == "NOT_EXECUTED_IN_THIS_INVOCATION"
        for value in runner.canonical_json(engine["artifact"]).split('"')[1::2]
    )


def test_final_assembly_records_the_n912_refit_blocks(synthetic_dag):
    engine = _run_dag_engine(synthetic_dag)
    provenance = engine["artifact"]["train_refit_provenance"]
    assert set(provenance["blocks"]) == set(engine["refit"])
    assert set(provenance["legacy_blocks"]) == set(engine["legacy_refit"])
    assert set(provenance["n912_blocks"]) == set(engine["n912_refit"])


def test_final_assembly_records_the_predictor_and_logloss(synthetic_dag):
    engine = _run_dag_engine(synthetic_dag)
    diagnostics = engine["artifact"]["secondary_diagnostics"]
    predictor = diagnostics["predictor"]
    assert predictor["validation_protocol_id"] == runner.r4_predictor.VALIDATION_PROTOCOL_ID
    assert predictor["units_total"] == 32
    assert predictor["development_units"] == 8
    assert predictor["validation_units"] == 16
    assert predictor["legacy_units"] == 8
    assert predictor["validation_rows"] == 16
    assert predictor["status"] == engine["predictor"].status
    assert predictor["interval"]["status"] == engine["predictor"].interval().status
    assert diagnostics["logloss_status"] == engine["logloss"].status
    assert diagnostics["legacy_secondary"]["unit_estimates"] == len(
        engine["legacy_estimates"]
    )


# --------------------------------------------------------------------------- #
# Dependency truth table and failure propagation
# --------------------------------------------------------------------------- #


def test_dependency_truth_table_is_frozen():
    assert runner.ESTIMAND_DEPENDENCIES == {
        "Delta_deploy": ("cross",),
        "Delta_native": ("native",),
        "Delta_transport": ("cross", "native"),
    }
    assert runner.REFIT_ESTIMANDS == ("Delta_deploy", "Delta_transport")
    assert runner._MEASUREMENTS == ("CAT", "OVR")


def _panel_key(synthetic_dag):
    models = runner._panel_models(synthetic_dag.primary, synthetic_dag.primary_populations)
    return models[0], synthetic_dag.primary_populations[0]


def _train_rows(synthetic_dag):
    return synthetic_dag.primary.train_rows[_panel_key(synthetic_dag)]


# --------------------------------------------------------------------------- #
# Canonical fitted-map identity
# --------------------------------------------------------------------------- #


def test_canonical_fit_identity_is_measurement_level(synthetic_primary, current_populations):
    """One scientific fit identity: model x population x budget x procedure x measurement."""
    models = runner._panel_models(synthetic_primary, current_populations)
    model = models[0]
    population = current_populations[0]
    expected = (
        len(models)
        * len(current_populations)
        * len(synthetic_primary.authority.procedure_order)
        * 2
    )
    assert len(synthetic_primary.fits) == expected == 144
    assert synthetic_primary.budget == "N456"
    for procedure in synthetic_primary.authority.procedure_order:
        for measurement in runner._MEASUREMENTS:
            key = runner.canonical_fit_key(model, population, procedure, measurement)
            assert key == (model, population, procedure, measurement)
            assert key in synthetic_primary.fits


def test_directional_planes_alias_onto_one_canonical_fit(synthetic_primary, current_populations):
    """CAT->OVR cross and OVR->CAT native resolve to the very same fitted map."""
    model, population = (
        runner._panel_models(synthetic_primary, current_populations)[0],
        current_populations[0],
    )
    procedure = "B-beta"
    cat_key = runner.canonical_fit_key(model, population, procedure, "CAT")
    ovr_key = runner.canonical_fit_key(model, population, procedure, "OVR")
    assert (
        runner.canonical_fit_key(
            model, population, procedure, runner.directional_measurement("CAT->OVR", "cross")
        )
        == cat_key
    )
    assert (
        runner.canonical_fit_key(
            model, population, procedure, runner.directional_measurement("OVR->CAT", "native")
        )
        == cat_key
    )
    assert (
        runner.canonical_fit_key(
            model, population, procedure, runner.directional_measurement("OVR->CAT", "cross")
        )
        == ovr_key
    )
    assert (
        runner.canonical_fit_key(
            model, population, procedure, runner.directional_measurement("CAT->OVR", "native")
        )
        == ovr_key
    )
    cross_cat, native_cat = runner._cross_native_fits(
        synthetic_primary, model=model, population=population, procedure=procedure,
        direction="CAT->OVR",
    )
    cross_ovr, native_ovr = runner._cross_native_fits(
        synthetic_primary, model=model, population=population, procedure=procedure,
        direction="OVR->CAT",
    )
    assert cross_cat is native_ovr
    assert native_cat is cross_ovr


def test_directional_reference_map_points_at_the_canonical_fit(
    synthetic_primary, current_populations
):
    mapping = runner.directional_reference_map(
        synthetic_primary,
        models=runner._panel_models(synthetic_primary, current_populations),
        populations=current_populations,
    )
    model = runner._panel_models(synthetic_primary, current_populations)[0]
    population = current_populations[0]
    reference = f"{model}|{population}"
    assert mapping[f"{reference}|CAT->OVR|B-beta|cross"] == (
        f"{reference}|N456|B-beta|CAT"
    )
    assert mapping[f"{reference}|OVR->CAT|B-beta|native"] == (
        f"{reference}|N456|B-beta|CAT"
    )
    assert mapping[f"{reference}|OVR->CAT|B-beta|cross"] == (
        f"{reference}|N456|B-beta|OVR"
    )
    assert mapping[f"{reference}|CAT->OVR|B-beta|native"] == (
        f"{reference}|N456|B-beta|OVR"
    )


def test_fit_procedure_is_called_once_per_measurement(authority, cells, monkeypatch):
    """A measurement is fitted exactly once, never once per directional role."""
    calls: list[tuple[str, str]] = []
    original = runner.fit_procedure

    def counting(**kwargs):
        calls.append((kwargs["procedure"], kwargs["measurement"]))
        return original(**kwargs)

    monkeypatch.setattr(runner, "fit_procedure", counting)
    current = [cell for cell in cells if cell.model_role == "current-generation"]
    panel = runner.build_synthetic_panel(authority, current)
    pairs = {(cell.model_key, cell.population_id) for cell in current}
    expected = len(pairs) * len(panel.authority.procedure_order) * 2
    counts = collections.Counter(calls)
    assert len(calls) == expected
    assert len(panel.fits) == expected
    assert len(counts) == len(panel.authority.procedure_order) * 2
    assert set(counts.values()) == {len(pairs)}


# --------------------------------------------------------------------------- #
# Measurement-level failure propagation
# --------------------------------------------------------------------------- #


def test_dependency_qualification_injects_a_canonical_measurement_failure(synthetic_dag):
    report = runner.dependency_qualification(synthetic_dag, replicates=2)
    identity = report["injected_fit_identity"]
    model, population = _panel_key(synthetic_dag)
    assert identity == {
        "model": model,
        "population": population,
        "budget": "N456",
        "procedure": "B-beta",
    }
    assert report["directional_aliasing"] == {
        "CAT->OVR|cross": "CAT",
        "CAT->OVR|native": "OVR",
        "OVR->CAT|cross": "OVR",
        "OVR->CAT|native": "CAT",
    }
    assert report["canonical_fit_count"] == report["expected_canonical_fit_count"] == 144
    assert report["cat_only_expected_matches"] is True
    assert report["ovr_only_expected_matches"] is True
    assert report["both_expected_matches"] is True
    assert report["cat_only_failed_fits"] == [
        f"{model}|{population}|N456|B-beta|CAT"
    ]
    assert report["ovr_only_failed_fits"] == [
        f"{model}|{population}|N456|B-beta|OVR"
    ]
    assert report["cat_only_failure_types"] == ["BetaImplementationError"]
    assert report["ovr_only_failure_types"] == ["BetaImplementationError"]
    assert report["both_measurements_failure_types"] == ["BetaImplementationError"]
    # A canonical measurement failure is reported ONCE, never once per role.
    assert len(report["cat_only_failed_fits"]) == 1
    assert len(report["ovr_only_failed_fits"]) == 1
    assert report["family_sizes_fixed"] == {
        "primary": 12,
        "secondary_extension": 8,
        "secondary_direction_difference": 6,
        "secondary_native_reference": 12,
    }


def test_cat_only_failure_propagates_to_both_directional_roles(synthetic_dag):
    report = runner.dependency_qualification(synthetic_dag, replicates=2)
    assert report["cat_only_direction_status"] == {
        "CAT->OVR": {
            "Delta_deploy": "INCOMPLETE",
            "Delta_native": "AVAILABLE",
            "Delta_transport": "INCOMPLETE",
        },
        "OVR->CAT": {
            "Delta_deploy": "AVAILABLE",
            "Delta_native": "INCOMPLETE",
            "Delta_transport": "INCOMPLETE",
        },
    }
    assert report["cat_only_expected"] == report["cat_only_direction_status"]


def test_ovr_only_failure_mirrors_the_cat_only_truth_table(synthetic_dag):
    report = runner.dependency_qualification(synthetic_dag, replicates=2)
    assert report["ovr_only_direction_status"] == {
        "CAT->OVR": {
            "Delta_deploy": "AVAILABLE",
            "Delta_native": "INCOMPLETE",
            "Delta_transport": "INCOMPLETE",
        },
        "OVR->CAT": {
            "Delta_deploy": "INCOMPLETE",
            "Delta_native": "AVAILABLE",
            "Delta_transport": "INCOMPLETE",
        },
    }
    assert report["ovr_only_expected"] == report["ovr_only_direction_status"]


def test_both_measurements_failure_removes_every_estimand_of_the_unit(synthetic_dag):
    report = runner.dependency_qualification(synthetic_dag, replicates=2)
    assert report["both_measurements_direction_status"] == {
        "CAT->OVR": {
            "Delta_deploy": "INCOMPLETE",
            "Delta_native": "INCOMPLETE",
            "Delta_transport": "INCOMPLETE",
        },
        "OVR->CAT": {
            "Delta_deploy": "INCOMPLETE",
            "Delta_native": "INCOMPLETE",
            "Delta_transport": "INCOMPLETE",
        },
    }
    assert report["both_measurements_failed_fits"] == [
        report["cat_only_failed_fits"][0],
        report["ovr_only_failed_fits"][0],
    ]
    assert report["both_expected"] == report["both_measurements_direction_status"]


def test_family_size_is_reported_apart_from_complete_count(synthetic_dag):
    """A fixed family keeps its size; only complete_count moves."""
    report = runner.dependency_qualification(synthetic_dag, replicates=2)
    assert report["baseline_families"] == {
        "primary": {
            "family_size": 12,
            "complete_count": 12,
            "incomplete_count": 0,
            "status": "COMPLETE",
        },
        "secondary_direction_difference": {
            "family_size": 6,
            "complete_count": 6,
            "incomplete_count": 0,
            "status": "COMPLETE",
        },
        "secondary_extension": {
            "family_size": 8,
            "complete_count": 8,
            "incomplete_count": 0,
            "status": "COMPLETE",
        },
        "secondary_native_reference": {
            "family_size": 12,
            "complete_count": 12,
            "incomplete_count": 0,
            "status": "COMPLETE",
        },
    }
    # CAT-only: one of four B-beta extension members survives; one of twelve
    # native-reference members is lost (the OVR->CAT native CAT map).
    assert report["cat_only_families"]["primary"] == {
        "family_size": 12,
        "complete_count": 12,
        "incomplete_count": 0,
        "status": "COMPLETE",
    }
    assert report["cat_only_families"]["secondary_direction_difference"] == {
        "family_size": 6,
        "complete_count": 6,
        "incomplete_count": 0,
        "status": "COMPLETE",
    }
    assert report["cat_only_families"]["secondary_extension"] == {
        "family_size": 8,
        "complete_count": 5,
        "incomplete_count": 3,
        "status": "INCOMPLETE",
    }
    assert report["cat_only_families"]["secondary_native_reference"] == {
        "family_size": 12,
        "complete_count": 11,
        "incomplete_count": 1,
        "status": "INCOMPLETE",
    }
    # Both measurements: every B-beta extension member of that unit vanishes.
    assert report["both_measurements_families"]["secondary_extension"] == {
        "family_size": 8,
        "complete_count": 4,
        "incomplete_count": 4,
        "status": "INCOMPLETE",
    }
    assert report["both_measurements_families"]["secondary_native_reference"] == {
        "family_size": 12,
        "complete_count": 10,
        "incomplete_count": 2,
        "status": "INCOMPLETE",
    }


def test_dependency_injection_keeps_core4_complete(synthetic_dag):
    report = runner.dependency_qualification(synthetic_dag, replicates=2)
    assert report["core4_primary_and_direction_complete_under_injection"] is True
    assert report["core4_only_extension_unaffected_by_standalone_failure"] is True


def test_canonical_failure_skips_only_its_own_refit_scope(synthetic_dag):
    report = runner.dependency_qualification(synthetic_dag, replicates=2)
    assert report["baseline_refit_blocks"] == 288
    # CAT failure blocks three of the injected unit's refit blocks; both blocks four.
    assert report["cat_only_refit_blocks"] == 285
    assert report["ovr_only_refit_blocks"] == 285
    assert report["both_measurements_refit_blocks"] == 284
    for label in ("cat_only", "ovr_only", "both_measurements"):
        assert set(report[f"{label}_refit_failure_types"]) <= {
            "BootstrapContractViolation"
        }


def test_fit_failure_propagates_as_incomplete_not_an_exception(
    synthetic_dag, current_populations
):
    """A frozen full-fit FAILED must never abort the DAG engine."""
    model, population = _panel_key(synthetic_dag)
    panel = runner._with_fit_failure(
        synthetic_dag.primary,
        model=model,
        population=population,
        procedure="B-beta",
        measurement="CAT",
        failure_type="BetaImplementationError",
        message="no constraint face produced an accepted optimum",
    )
    broken = runner.DagRun(
        authority=synthetic_dag.authority,
        primary=panel,
        legacy=synthetic_dag.legacy,
        n912=None,
        primary_populations=synthetic_dag.primary_populations,
        legacy_populations=synthetic_dag.legacy_populations,
        fixture_marker=runner.SYNTHETIC_FIXTURE_MARKER,
    )
    engine = _run_dag_engine(broken)
    registry = engine["coverage_registry"]
    failed = {key: entry for key, entry in registry.items() if entry["status"] == "FAILED"}
    assert len(failed) == 1
    assert all(entry["failure_type"] == "BetaImplementationError" for entry in failed.values())
    assert all(entry["budget"] == "N456" for entry in failed.values())
    assert all(
        entry["directional_references"]
        == [
            {"direction": "CAT->OVR", "side": "cross"},
            {"direction": "OVR->CAT", "side": "native"},
        ]
        for entry in failed.values()
    )
    status = engine["bootstrap"].family_status()
    assert status["primary"]["complete_count"] == 12
    assert status["secondary_direction_difference"]["complete_count"] == 6
    assert status["secondary_extension"]["family_size"] == 8
    assert status["secondary_native_reference"]["family_size"] == 12
    assert status["secondary_extension"]["complete_count"] < 8


# --------------------------------------------------------------------------- #
# Exception boundary: explicit whitelist only, unknown exceptions propagate
# --------------------------------------------------------------------------- #


def test_beta_implementation_error_maps_to_failed(synthetic_dag, monkeypatch):
    def exploding(scores, labels):
        raise runner.r4_calibration_families.BetaImplementationError(
            "no constraint face produced an accepted optimum"
        )

    monkeypatch.setattr(
        runner.r4_calibration_families, "fit_beta_fixed_decision_probability", exploding
    )
    fit = runner.fit_procedure(
        procedure="B-beta", train_rows=_train_rows(synthetic_dag), measurement="CAT"
    )
    assert fit.status == "FAILED"
    assert fit.failure_type == "BetaImplementationError"
    assert "no constraint face produced an accepted optimum" in fit.reason
    assert fit.calibrator is None


def test_beta_fit_ineligible_maps_to_ineligible(synthetic_dag, monkeypatch):
    def ineligible(scores, labels):
        raise runner.r4_calibration_families.BetaFitIneligible("single class")

    monkeypatch.setattr(
        runner.r4_calibration_families, "fit_beta_fixed_decision_probability", ineligible
    )
    fit = runner.fit_procedure(
        procedure="B-beta", train_rows=_train_rows(synthetic_dag), measurement="OVR"
    )
    assert fit.status == "INELIGIBLE"
    assert fit.failure_type is None


def test_beta_contract_violation_maps_to_failed(synthetic_dag, monkeypatch):
    def violation(scores, labels):
        raise runner.r4_calibration_families.BetaContractViolation("contract")

    monkeypatch.setattr(
        runner.r4_calibration_families, "fit_beta_fixed_decision_probability", violation
    )
    fit = runner.fit_procedure(
        procedure="B-beta", train_rows=_train_rows(synthetic_dag), measurement="CAT"
    )
    assert fit.status == "FAILED"
    assert fit.failure_type == "BetaContractViolation"


def test_isotonic_contract_violation_maps_to_failed(synthetic_dag, monkeypatch):
    def violation(scores, labels):
        raise runner.r4_calibration_families.IsotonicContractViolation("contract")

    monkeypatch.setattr(
        runner.r4_calibration_families, "fit_isotonic_fixed_decision_probability", violation
    )
    fit = runner.fit_procedure(
        procedure="I-isotonic", train_rows=_train_rows(synthetic_dag), measurement="CAT"
    )
    assert fit.status == "FAILED"
    assert fit.failure_type == "IsotonicContractViolation"


def test_beta_unexpected_runtime_error_propagates(synthetic_dag, monkeypatch):
    def exploding(scores, labels):
        raise RuntimeError("unexpected solver defect")

    monkeypatch.setattr(
        runner.r4_calibration_families, "fit_beta_fixed_decision_probability", exploding
    )
    with pytest.raises(RuntimeError):
        runner.fit_procedure(
            procedure="B-beta", train_rows=_train_rows(synthetic_dag), measurement="CAT"
        )


def test_isotonic_unexpected_runtime_error_propagates(synthetic_dag, monkeypatch):
    def exploding(scores, labels):
        raise RuntimeError("unexpected isotonic defect")

    monkeypatch.setattr(
        runner.r4_calibration_families, "fit_isotonic_fixed_decision_probability", exploding
    )
    with pytest.raises(RuntimeError):
        runner.fit_procedure(
            procedure="I-isotonic", train_rows=_train_rows(synthetic_dag), measurement="OVR"
        )


def test_unknown_keyerror_is_not_a_scientific_failure(synthetic_dag, monkeypatch):
    def exploding(scores, labels):
        raise KeyError("not-a-frozen-exception")

    monkeypatch.setattr(
        runner.r4_calibration_families, "fit_isotonic_fixed_decision_probability", exploding
    )
    with pytest.raises(KeyError):
        runner.fit_procedure(
            procedure="I-isotonic", train_rows=_train_rows(synthetic_dag), measurement="CAT"
        )


def test_unknown_fit_exception_escapes_the_panel_builder(authority, cells, monkeypatch):
    """An unknown fit defect must reach the formal execution boundary, un-mapped."""

    original = runner.fit_procedure

    def exploding(**kwargs):
        if kwargs["procedure"] == "I-isotonic":
            raise TypeError("unexpected fit defect")
        return original(**kwargs)

    monkeypatch.setattr(runner, "fit_procedure", exploding)
    current = [cell for cell in cells if cell.model_role == "current-generation"]
    with pytest.raises(TypeError):
        runner.build_synthetic_panel(authority, current)


# --------------------------------------------------------------------------- #
# Synthetic-input firewall guard
# --------------------------------------------------------------------------- #


def test_synthetic_guard_accepts_the_invented_fixture(synthetic_all):
    for role, panel in (
        ("primary", synthetic_all),
        ("legacy", synthetic_all),
    ):
        runner.assert_synthetic_inputs(panel, role=role)
    assert runner.SYNTHETIC_ITEM_PREFIX == "synthetic-"


def test_synthetic_guard_rejects_a_study_row(synthetic_primary):
    model, population = (
        runner._panel_models(synthetic_primary, ("r4-mmlu-57-subject",))[0],
        "r4-mmlu-57-subject",
    )
    key = (model, population)
    template = synthetic_primary.train_rows[key][0]
    poisoned_row = runner.r4_inference.R4InferenceRow(
        item_id="mmlu-train-000001",
        population_id=template.population_id,
        stratum=template.stratum,
        label=template.label,
        cat_score=template.cat_score,
        ovr_score=template.ovr_score,
        cluster_id=template.cluster_id,
        anchor_index=template.anchor_index,
    )
    train_rows = dict(synthetic_primary.train_rows)
    train_rows[key] = (poisoned_row,)
    poisoned = runner.PanelInputs(
        authority=synthetic_primary.authority,
        model_keys=synthetic_primary.model_keys,
        train_rows=train_rows,
        test_rows=synthetic_primary.test_rows,
        fits=synthetic_primary.fits,
        budget=synthetic_primary.budget,
    )
    with pytest.raises(runner.R4AnalysisOutcomeFirewallBreach):
        runner.assert_synthetic_inputs(poisoned, role="primary")


def test_refit_block_withholds_the_interval_when_a_replicate_fails(
    synthetic_dag, monkeypatch
):
    """Any single failed refit replicate -> INCOMPLETE with no subset interval."""
    models = runner._panel_models(synthetic_dag.primary, synthetic_dag.primary_populations)

    def exploding(*args, **kwargs):
        raise runner.r4_inference.BootstrapContractViolation("injected refit failure")

    monkeypatch.setattr(runner.r4_inference, "build_train_refit_draw", exploding)
    blocks = runner.run_refit_blocks(
        synthetic_dag.primary,
        models=models,
        populations=synthetic_dag.primary_populations,
        procedures=runner.r4_inference.LOGISTIC_CORE_PROCEDURES,
        replicates=2,
    )
    assert blocks
    for block in blocks.values():
        assert block.status == "INCOMPLETE"
        assert block.interval is None
        assert block.failures
        assert all(
            record.exception_type == "BootstrapContractViolation" for record in block.failures
        )


def test_synthetic_qualification_never_reads_the_formal_evidence(monkeypatch, tmp_path, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError("synthetic qualification touched the formal raw evidence")

    monkeypatch.setattr(runner, "load_cell_payload", forbidden)
    monkeypatch.setattr(runner, "build_panel_inputs", forbidden)
    args = _namespace(
        synthetic_qualification=True,
        qualification_root=str(tmp_path),
        synthetic_replicates=2,
    )
    assert runner.synthetic_qualification(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["deterministic_rerun"] is True
    assert payload["scientific_outputs_computed"] is False
    assert payload["mode"] == "synthetic-qualification"
    assert payload["fixture_marker"] == runner.SYNTHETIC_FIXTURE_MARKER
    assert (tmp_path / "synthetic-qualification.json").exists()


def test_synthetic_qualification_is_byte_identical_across_runs(monkeypatch, tmp_path):
    args = _namespace(
        synthetic_qualification=True,
        qualification_root=str(tmp_path),
        synthetic_replicates=2,
    )
    first_root = tmp_path / "a"
    second_root = tmp_path / "b"
    args.qualification_root = str(first_root)
    runner.synthetic_qualification(args)
    args.qualification_root = str(second_root)
    runner.synthetic_qualification(args)
    first = (first_root / "synthetic-qualification.json").read_bytes()
    second = (second_root / "synthetic-qualification.json").read_bytes()
    assert first == second


# --------------------------------------------------------------------------- #
# Formal-mode safety
# --------------------------------------------------------------------------- #


def test_formal_root_clean_accepts_a_missing_root(tmp_path):
    runner._assert_formal_root_clean(tmp_path / "absent", resume=False)


def test_formal_root_clean_rejects_unknown_entries(tmp_path):
    (tmp_path / "stray.txt").write_text("x", encoding="utf-8")
    with pytest.raises(runner.R4AnalysisFormalRootConflict):
        runner._assert_formal_root_clean(tmp_path, resume=True)


def test_formal_root_clean_rejects_a_non_empty_root_without_resume(tmp_path):
    (tmp_path / runner.CHECKPOINT_FILENAME).write_text("{}", encoding="utf-8")
    with pytest.raises(runner.R4AnalysisFormalRootConflict):
        runner._assert_formal_root_clean(tmp_path, resume=False)


def test_formal_root_clean_allows_a_resume_of_a_known_root(tmp_path):
    (tmp_path / runner.CHECKPOINT_FILENAME).write_text("{}", encoding="utf-8")
    runner._assert_formal_root_clean(tmp_path, resume=True)


def test_formal_mode_rejects_a_missing_authority(monkeypatch, tmp_path):
    def unavailable():
        raise runner.R4AnalysisAuthorityError("authority unavailable")

    monkeypatch.setattr(runner, "load_frozen_authority", unavailable)
    with pytest.raises(runner.R4AnalysisAuthorityError):
        runner.execute_formal_analysis(
            _namespace(execute_formal_analysis=True, formal_root=str(tmp_path))
        )


def test_formal_mode_rejects_a_dirty_formal_root(tmp_path):
    (tmp_path / "stray.txt").write_text("x", encoding="utf-8")
    with pytest.raises(runner.R4AnalysisFormalRootConflict):
        runner.execute_formal_analysis(
            _namespace(execute_formal_analysis=True, formal_root=str(tmp_path))
        )


def test_formal_mode_uses_the_real_evidence_path_not_the_synthetic_fixture(monkeypatch, tmp_path):
    class _Sentinel(Exception):
        pass

    def forbidden(*args, **kwargs):
        raise _Sentinel("formal mode reached the synthetic fixture")

    def reached_real_path(*args, **kwargs):
        raise _Sentinel("formal mode reached the real evidence path")

    monkeypatch.setattr(runner, "build_synthetic_panel", forbidden)
    monkeypatch.setattr(runner, "build_panel_inputs", reached_real_path)
    with pytest.raises(_Sentinel) as excinfo:
        runner.execute_formal_analysis(
            _namespace(execute_formal_analysis=True, formal_root=str(tmp_path))
        )
    assert "real evidence path" in str(excinfo.value)


def test_formal_mode_never_reuses_a_study_row_from_an_aborted_epoch():
    # The formal root must not exist or must be empty before formal execution.
    assert not FORMAL_ANALYSIS_ROOT.exists() or not any(FORMAL_ANALYSIS_ROOT.iterdir())


# --------------------------------------------------------------------------- #
# Operational checkpointing
# --------------------------------------------------------------------------- #


def test_checkpoint_store_records_and_reloads(tmp_path):
    store = runner.CheckpointStore(tmp_path)
    store.record("point_estimates", status="COMPLETE", identity="abc", output_fingerprint="def")
    reloaded = runner.CheckpointStore(tmp_path)
    completed = reloaded.completed()
    assert set(completed) == {"point_estimates"}
    assert completed["point_estimates"]["identity"] == "abc"
    assert completed["point_estimates"]["output_fingerprint"] == "def"


def test_checkpoint_store_rejects_an_unknown_block(tmp_path):
    store = runner.CheckpointStore(tmp_path)
    with pytest.raises(runner.R4AnalysisContractViolation):
        store.record("made_up_block", status="COMPLETE", identity="a", output_fingerprint=None)


def test_checkpoint_store_rejects_an_unknown_status(tmp_path):
    store = runner.CheckpointStore(tmp_path)
    with pytest.raises(runner.R4AnalysisContractViolation):
        store.record("point_estimates", status="MAYBE", identity="a", output_fingerprint=None)


def test_checkpoint_store_declares_every_analysis_block():
    assert runner.ANALYSIS_BLOCKS == (
        "authority_validation",
        "input_load",
        "point_estimates",
        "n912_robustness",
        "test_bootstrap",
        "train_refit",
        "predictor",
        "final_assembly",
    )


def test_checkpoint_store_never_keeps_a_partial_file(tmp_path):
    store = runner.CheckpointStore(tmp_path)
    store.record("input_load", status="COMPLETE", identity="a", output_fingerprint="b")
    text = (tmp_path / runner.CHECKPOINT_FILENAME).read_text(encoding="utf-8")
    json.loads(text)
    assert not any(path.suffix == ".tmp" for path in tmp_path.iterdir())


def test_checkpoint_store_incomplete_block_is_not_reported_complete(tmp_path):
    store = runner.CheckpointStore(tmp_path)
    store.record("predictor", status="INCOMPLETE", identity="a", output_fingerprint=None)
    assert runner.CheckpointStore(tmp_path).completed() == {}


def test_atomic_write_leaves_no_temporary_file(tmp_path):
    target = tmp_path / "artifact.json"
    runner.write_atomic(target, '{"a": 1}\n')
    assert json.loads(target.read_text(encoding="utf-8")) == {"a": 1}
    assert sorted(path.name for path in tmp_path.iterdir()) == ["artifact.json"]


def test_canonical_json_is_sorted_and_newline_terminated():
    text = runner.canonical_json({"b": 1, "a": [2, 3]})
    assert text == '{\n  "a": [\n    2,\n    3\n  ],\n  "b": 1\n}\n'


# --------------------------------------------------------------------------- #
# Frozen-implementation immutability
# --------------------------------------------------------------------------- #


def test_runner_does_not_modify_the_frozen_implementations():
    for name, digest in runner.FROZEN_SCIENTIFIC_IMPLEMENTATIONS.items():
        assert runner.sha256_file(TRANSPORT_DIR / name) == digest


def test_runner_never_imports_a_random_module():
    source = RUNNER_PATH.read_text(encoding="utf-8")
    for token in ("import random", "numpy.random", "import secrets", "time.time()"):
        assert token not in source


def test_runner_declares_itself_orchestration_only():
    source = RUNNER_PATH.read_text(encoding="utf-8")
    assert "orchestration" in source
