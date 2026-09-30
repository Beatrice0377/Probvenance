"""Synthetic-only engineering tests for the R4 inference + multiplicity infrastructure.

These tests exercise ``experiments/calibration_transport/r4_inference.py`` with
hand-written synthetic rows, synthetic draws and synthetic replicate samples.
They never read a study dataset, never load a model or tokenizer, never touch a
GPU, and never run a formal R4 bootstrap on real study outcomes.

The formal R4 execution remains unauthorized: every bootstrap in this file uses
either a tiny replicate count or an explicitly synthetic fixture.
"""

from __future__ import annotations

import importlib.util
import inspect
import itertools
import json
import math
import sys
from fractions import Fraction
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TRANSPORT_DIR = REPO_ROOT / "experiments" / "calibration_transport"
MODULE_PATH = TRANSPORT_DIR / "r4_inference.py"
FREEZE_JSON = TRANSPORT_DIR / "R4_INFERENCE_MULTIPLICITY_FREEZE.json"
FREEZE_MD = TRANSPORT_DIR / "R4_INFERENCE_MULTIPLICITY_FREEZE.md"
R3_DESIGN_JSON = TRANSPORT_DIR / "r3_protocol_design.json"
CALIBRATION_CANDIDATE_JSON = TRANSPORT_DIR / "R4_CALIBRATION_FAMILY_SEMANTIC_CANDIDATE.json"
CORE_CALIBRATION = REPO_ROOT / "src" / "probvenance" / "calibration.py"

spec = importlib.util.spec_from_file_location("r4_inference", MODULE_PATH)
inference = importlib.util.module_from_spec(spec)
sys.modules["r4_inference"] = inference
spec.loader.exec_module(inference)

from probvenance.fingerprint import fingerprint  # noqa: E402

TOL = 1e-12

MMLU = inference.MMLU_POPULATION_ID
HELLA = inference.HELLASWAG_POPULATION_ID
MED = inference.MEDMCQA_POPULATION_ID

MMLU_MODE = "subject-stratified-row"
MED_MODE = "subject_name-stratified-row"
HELLA_MODE = "activity-stratified-source_id-cluster"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def make_row(
    item_id: str,
    population_id: str,
    stratum: str,
    label: int,
    cat_score: float,
    ovr_score: float,
    cluster_id: str | None = None,
    anchor_index: int | None = None,
):
    return inference.R4InferenceRow(
        item_id=item_id,
        population_id=population_id,
        stratum=stratum,
        label=label,
        cat_score=cat_score,
        ovr_score=ovr_score,
        cluster_id=cluster_id,
        anchor_index=anchor_index,
    )


def make_metadata(
    population_id: str,
    *,
    mode: str,
    stratum_field: str,
    weighting: str,
    group_field: str | None = None,
    test_count: int = 0,
    train_count: int = 456,
    n912_train_count: int | None = None,
    population_fingerprint: str = "synthetic-population-fingerprint",
):
    return inference.PopulationMetadata(
        population_id=population_id,
        population_fingerprint=population_fingerprint,
        stratum_field=stratum_field,
        group_field=group_field,
        test_bootstrap_protocol_id=inference.TEST_BOOTSTRAP_PROTOCOL_ID,
        test_bootstrap_protocol_version=inference.TEST_BOOTSTRAP_PROTOCOL_VERSION,
        test_bootstrap_mode=mode,
        estimand_weighting=weighting,
        test_count=test_count,
        train_count=train_count,
        n912_train_count=n912_train_count,
    )


def mmlu_metadata(**kwargs):
    return make_metadata(
        MMLU,
        mode=MMLU_MODE,
        stratum_field="subject",
        weighting="equal-subject-mean-of-subject-means",
        **kwargs,
    )


def med_metadata(**kwargs):
    return make_metadata(
        MED,
        mode=MED_MODE,
        stratum_field="subject_name",
        weighting="row-weighted-mean",
        **kwargs,
    )


def hella_metadata(**kwargs):
    return make_metadata(
        HELLA,
        mode=HELLA_MODE,
        stratum_field="activity_label",
        group_field="source_id",
        weighting="row-weighted-mean",
        **kwargs,
    )


def synthetic_row_set(population_id: str, strata_sizes: dict[str, int], **kwargs):
    rows = []
    for stratum, size in strata_sizes.items():
        for index in range(size):
            rows.append(
                make_row(
                    f"{population_id}:{stratum}:{index}",
                    population_id,
                    stratum,
                    index % 2,
                    0.1 + 0.05 * index,
                    0.9 - 0.05 * index,
                    **kwargs,
                )
            )
    return rows


def hellaswag_cluster_rows():
    """Two activities: act-1 has a 1-row and a 5-row cluster, act-2 has a 2-row cluster."""
    rows = [make_row("c1-r1", HELLA, "act-1", 1, 0.2, 0.8, cluster_id="c1")]
    rows += [
        make_row(f"c2-r{i}", HELLA, "act-1", i % 2, 0.6 + 0.05 * i, 0.4, cluster_id="c2")
        for i in range(5)
    ]
    rows += [
        make_row(f"c3-r{i}", HELLA, "act-2", i, 0.3 + 0.1 * i, 0.7, cluster_id="c3")
        for i in range(2)
    ]
    return rows


def formal_mmlu_rows():
    rows = []
    for subject in range(inference.FORMAL_MMLU_SUBJECT_COUNT):
        for index in range(inference.FORMAL_MMLU_TEST_PER_SUBJECT):
            rows.append(
                make_row(
                    f"mmlu:s{subject}:{index}",
                    MMLU,
                    f"subject-{subject}",
                    index % 2,
                    0.25 + 0.01 * index,
                    0.75 - 0.01 * index,
                )
            )
    return rows


def formal_med_rows():
    total = inference.FORMAL_MEDMCQA_TEST_COUNT
    strata = inference.FORMAL_MEDMCQA_SUBJECT_COUNT
    base, remainder = divmod(total, strata)
    rows = []
    for subject in range(strata):
        size = base + (1 if subject < remainder else 0)
        for index in range(size):
            rows.append(
                make_row(
                    f"med:s{subject}:{index}",
                    MED,
                    f"subject_name-{subject}",
                    index % 2,
                    0.4,
                    0.6,
                )
            )
    return rows


def formal_hellaswag_rows():
    """8407 clusters over 192 activity labels with 10042 rows in total."""
    cluster_count = inference.FORMAL_HELLASWAG_SOURCE_ID_COUNT
    label_count = inference.FORMAL_HELLASWAG_ACTIVITY_LABEL_COUNT
    per_label, remainder = divmod(cluster_count, label_count)
    labels = []
    for label in range(label_count):
        labels.extend([f"activity-{label}"] * (per_label + (1 if label < remainder else 0)))
    assert len(labels) == cluster_count
    extra_clusters = inference.FORMAL_HELLASWAG_TEST_COUNT - cluster_count
    rows = []
    for cluster_index, label in enumerate(labels):
        rows_for_cluster = 2 if cluster_index < extra_clusters else 1
        for index in range(rows_for_cluster):
            rows.append(
                make_row(
                    f"hella:c{cluster_index}:{index}",
                    HELLA,
                    label,
                    index % 2,
                    0.5,
                    0.5,
                    cluster_id=f"source-{cluster_index}",
                )
            )
    return rows


def mmlu_train_rows(train_per_subject: int = inference.FORMAL_MMLU_TRAIN_PER_SUBJECT):
    rows = []
    for subject in range(inference.FORMAL_MMLU_SUBJECT_COUNT):
        for index in range(train_per_subject):
            rows.append(
                make_row(
                    f"mmlu-train:s{subject}:{index}",
                    MMLU,
                    f"subject-{subject}",
                    index % 2,
                    0.3,
                    0.7,
                )
            )
    return rows


def hellaswag_train_rows():
    """TRAIN is at most one selected row per source_id: a row bootstrap, not a cluster one."""
    return [
        make_row(f"hella-train:c{i}", HELLA, f"activity-{i % 7}", i % 2, 0.2, 0.8,
                 cluster_id=f"source-{i}")
        for i in range(30)
    ]


def med_train_rows():
    rows = []
    for subject in range(5):
        for index in range(4):
            rows.append(
                make_row(f"med-train:s{subject}:{index}", MED, f"subject_name-{subject}",
                         index % 2, 0.45, 0.55)
            )
    return rows


def fill_coverage(matrix, measurement: str, *, status: str = inference.AVAILABLE) -> None:
    for model in inference.PRIMARY_MODELS:
        for population in inference.PRIMARY_POPULATIONS:
            for procedure in inference.ALL_PROCEDURES:
                matrix.set(model, population, procedure, measurement, status)


# ---------------------------------------------------------------------------
# Freeze / candidate identity
# ---------------------------------------------------------------------------


def test_freeze_json_identity_matches_module_constants():
    freeze = _load(FREEZE_JSON)
    assert freeze["artifact_type"] == inference.FREEZE_ARTIFACT_TYPE
    assert freeze["artifact_version"] == inference.FREEZE_ARTIFACT_VERSION
    assert freeze["status"] == inference.FREEZE_STATUS == "FROZEN"
    assert freeze["fingerprint_version"] == inference.FINGERPRINT_VERSION
    assert freeze["candidate_artifact_identity"]["candidate_fingerprint"] == (
        inference.CANDIDATE_FINGERPRINT
    )
    assert freeze["candidate_commit"] == inference.CANDIDATE_COMMIT
    assert freeze["freeze_fingerprint"] == inference.R4_INFERENCE_FREEZE_FINGERPRINT


def test_freeze_fingerprint_is_self_consistent():
    freeze = _load(FREEZE_JSON)
    payload = {key: value for key, value in freeze.items() if key != "freeze_fingerprint"}
    assert fingerprint(payload) == freeze["freeze_fingerprint"]


def test_candidate_provenance_records_the_reviewed_candidate():
    freeze = _load(FREEZE_JSON)
    assert freeze["candidate_commit"] == "2ef9d31cda96dfc3bb326625dad0df061bb7063e"
    provenance = freeze["creation_provenance"]
    assert provenance["source_candidate_commit"] == inference.CANDIDATE_COMMIT
    assert provenance["source_candidate_fingerprint"] == inference.CANDIDATE_FINGERPRINT
    assert provenance["freeze_specific_metadata_only"] is True
    assert provenance["semantic_equivalence_audit"]["result"] == "EXACT_SEMANTIC_EQUIVALENCE"


def test_freeze_markdown_records_the_frozen_status_language():
    text = FREEZE_MD.read_text(encoding="utf-8")
    assert "FROZEN" in text
    assert "FORMAL EXECUTION AUTHORIZED" in text
    for family in ("12", "8", "6"):
        assert family in text
    assert inference.R4_INFERENCE_FREEZE_FINGERPRINT in text
    assert inference.CANDIDATE_FINGERPRINT in text


def test_r3_continuity_identities_match_the_frozen_r3_protocol():
    design = _load(R3_DESIGN_JSON)
    assert design["protocol_fingerprint"] == inference.R3_PROTOCOL_FINGERPRINT
    assert design["protocol_id"] == inference.R3_PROTOCOL_ID
    procedures = {entry["payload"]["label"]: entry["fingerprint"] for entry in design["procedures"]}
    for name in inference.LOGISTIC_CORE_PROCEDURES:
        assert procedures[name] == inference.PROCEDURE_FINGERPRINTS[name]
    for name in inference.STANDALONE_PROCEDURES:
        assert name not in procedures
        assert name not in inference.LOGISTIC_CORE_PROCEDURES
    assert len(procedures) == len(inference.LOGISTIC_CORE_PROCEDURES)


def test_calibration_family_identities_match_the_frozen_candidate():
    candidate = _load(CALIBRATION_CANDIDATE_JSON)
    labels = {
        entry["label"]: entry["fingerprint"] for entry in candidate["candidate_procedures"]
    }
    assert labels["I-isotonic"] == inference.PROCEDURE_FINGERPRINTS["I-isotonic"]
    assert labels["B-beta"] == inference.PROCEDURE_FINGERPRINTS["B-beta"]


def test_frozen_family_constants():
    assert inference.PRIMARY_FAMILY_SIZE == 12
    assert inference.EXTENSION_FAMILY_SIZE == 8
    assert inference.DIRECTION_DIFFERENCE_FAMILY_SIZE == 6
    assert inference.NATIVE_REFERENCE_FAMILY_SIZE == 12
    assert inference.FAMILY_SIZES == {
        "primary": 12,
        "secondary_extension": 8,
        "secondary_direction_difference": 6,
        "secondary_native_reference": 12,
    }
    assert inference.TEST_BOOTSTRAP_REPLICATES == 20000
    assert inference.TRAIN_REFIT_REPLICATES == 2000
    assert len(inference.PRIMARY_MODELS) == 4
    assert len(inference.PRIMARY_POPULATIONS) == 3
    assert len(inference.DIRECTIONS) == 2
    assert len(inference.ALL_PROCEDURES) == 6
    assert inference.PRIMARY_UNIT_COUNT == 24
    assert inference.PRIMARY_MODEL_POPULATION_CELL_COUNT == 12
    assert inference.LEGACY_SECONDARY_UNIT_COUNT == 8
    assert len(inference.LEGACY_MODELS) == 2
    assert len(inference.LEGACY_POPULATIONS) == 2


def test_structural_audit_constants_match_the_freeze():
    audit = _load(FREEZE_JSON)["frozen_semantic_payload"]["structural_audit"]
    assert audit["mmlu"]["subject_count"] == inference.FORMAL_MMLU_SUBJECT_COUNT
    assert audit["mmlu"]["test_per_subject"] == inference.FORMAL_MMLU_TEST_PER_SUBJECT
    assert audit["mmlu"]["train_per_subject"] == inference.FORMAL_MMLU_TRAIN_PER_SUBJECT
    assert audit["mmlu"]["test_count"] == inference.FORMAL_MMLU_TEST_COUNT
    assert audit["mmlu"]["train_count"] == inference.FORMAL_MMLU_TRAIN_COUNT
    assert audit["hellaswag"]["test_count"] == inference.FORMAL_HELLASWAG_TEST_COUNT
    assert audit["hellaswag"]["primary_train_count"] == inference.FORMAL_HELLASWAG_TRAIN_COUNT
    assert (
        audit["hellaswag"]["robustness912_train_count"]
        == inference.FORMAL_HELLASWAG_ROBUSTNESS_TRAIN_COUNT
    )
    assert (
        audit["hellaswag"]["test_activity_label_count"]
        == inference.FORMAL_HELLASWAG_ACTIVITY_LABEL_COUNT
    )
    assert audit["hellaswag"]["test_source_id_unique"] == inference.FORMAL_HELLASWAG_SOURCE_ID_COUNT
    assert audit["hellaswag"]["test_source_id_to_activity_label_conflicts"] == 0
    assert audit["medmcqa"]["test_count"] == inference.FORMAL_MEDMCQA_TEST_COUNT
    assert audit["medmcqa"]["test_subject_count"] == inference.FORMAL_MEDMCQA_SUBJECT_COUNT
    assert audit["medmcqa"]["topic_name_is_not_a_stratum"] is True


# ---------------------------------------------------------------------------
# Direction contract
# ---------------------------------------------------------------------------


def test_direction_measurement_table():
    assert inference.DIRECTION_MEASUREMENTS == {
        "CAT->OVR": ("CAT", "OVR"),
        "OVR->CAT": ("OVR", "CAT"),
    }
    assert inference.source_measurement("CAT->OVR") == "CAT"
    assert inference.target_measurement("CAT->OVR") == "OVR"
    assert inference.source_measurement("OVR->CAT") == "OVR"
    assert inference.target_measurement("OVR->CAT") == "CAT"
    with pytest.raises(inference.DirectionContractViolation):
        inference.direction_measurements("CAT->CAT")


def test_cross_map_uses_the_target_measurement_never_the_source():
    """Regression guard: the cross map is applied to S_target, never S_source."""
    rows = [
        make_row("i0", MMLU, "s", 1, cat_score=0.11, ovr_score=0.91),
        make_row("i1", MMLU, "s", 0, cat_score=0.22, ovr_score=0.82),
    ]
    scores, measurement = inference.cross_map_inputs(rows, "CAT->OVR")
    assert measurement == "OVR"
    assert scores == (0.91, 0.82)
    scores, measurement = inference.cross_map_inputs(rows, "OVR->CAT")
    assert measurement == "CAT"
    assert scores == (0.11, 0.22)
    assert inference.source_scores(rows, "CAT->OVR") == (0.11, 0.22)
    assert inference.target_scores(rows, "CAT->OVR") == (0.91, 0.82)


def test_measurement_score_rejects_unknown_measurement():
    row = make_row("i0", MMLU, "s", 1, 0.5, 0.5)
    with pytest.raises(inference.DirectionContractViolation):
        inference.measurement_score(row, "SCORE")


# ---------------------------------------------------------------------------
# Row contract
# ---------------------------------------------------------------------------


def test_row_contract_rejects_invalid_fields():
    with pytest.raises(inference.RowContractViolation):
        make_row("", MMLU, "s", 1, 0.5, 0.5)
    with pytest.raises(inference.RowContractViolation):
        make_row("i", "", "s", 1, 0.5, 0.5)
    with pytest.raises(inference.RowContractViolation):
        make_row("i", MMLU, "", 1, 0.5, 0.5)
    with pytest.raises(inference.RowContractViolation):
        make_row("i", MMLU, "s", 2, 0.5, 0.5)
    with pytest.raises(inference.RowContractViolation):
        make_row("i", MMLU, "s", 1, 1.5, 0.5)
    with pytest.raises(inference.RowContractViolation):
        make_row("i", MMLU, "s", 1, 0.5, float("nan"))
    with pytest.raises(inference.RowContractViolation):
        make_row("i", MMLU, "s", 1, 0.5, 0.5, anchor_index=1.5)


# ---------------------------------------------------------------------------
# Loss contract
# ---------------------------------------------------------------------------


def test_brier_loss_is_the_squared_error():
    assert inference.brier_loss(0.0, 0) == 0.0
    assert inference.brier_loss(1.0, 1) == 0.0
    assert inference.brier_loss(0.25, 1) == pytest.approx(0.5625, abs=TOL)
    assert inference.mean_brier([(0.0, 0), (1.0, 1)]) == 0.0
    with pytest.raises(inference.BootstrapContractViolation):
        inference.mean_brier([])


def test_logloss_zero_mass_is_exact_and_never_clipped():
    assert inference.logloss_loss(0.0, 0).state == inference.FINITE
    assert inference.logloss_loss(0.0, 0).value == 0.0
    assert inference.logloss_loss(1.0, 1).state == inference.FINITE
    assert inference.logloss_loss(1.0, 1).value == 0.0
    assert inference.logloss_loss(0.0, 1).state == inference.POSITIVE_INFINITY
    assert inference.logloss_loss(1.0, 0).state == inference.POSITIVE_INFINITY
    assert inference.logloss_loss(0.5, 1).value == pytest.approx(math.log(2.0), abs=TOL)
    assert inference.logloss_loss(0.5, 0).value == pytest.approx(math.log(2.0), abs=TOL)


def test_extended_real_state_contract():
    assert inference.ExtendedReal.finite(1.0).is_finite
    with pytest.raises(inference.ExtendedRealContractViolation):
        inference.ExtendedReal(inference.FINITE, None)
    with pytest.raises(inference.ExtendedRealContractViolation):
        inference.ExtendedReal(inference.POSITIVE_INFINITY, 1.0)
    with pytest.raises(inference.ExtendedRealContractViolation):
        inference.ExtendedReal("NOT_A_STATE")
    assert inference.ExtendedReal.finite(1.0).state_payload() == {"state": "FINITE", "value": 1.0}


def test_extended_real_difference_table_matches_the_freeze():
    finite = inference.ExtendedReal.finite(2.0)
    other = inference.ExtendedReal.finite(0.5)
    plus = inference.ExtendedReal.positive_infinity()
    minus = inference.ExtendedReal.negative_infinity()

    assert inference.extended_real_subtract(finite, other).value == pytest.approx(1.5, abs=TOL)
    assert inference.extended_real_subtract(plus, finite).state == inference.POSITIVE_INFINITY
    assert inference.extended_real_subtract(finite, plus).state == inference.NEGATIVE_INFINITY
    assert inference.extended_real_subtract(plus, plus).state == inference.UNDEFINED_EXTENDED_REAL
    assert inference.extended_real_subtract(minus, minus).state == inference.UNDEFINED_EXTENDED_REAL
    assert inference.extended_real_subtract(plus, minus).state == inference.POSITIVE_INFINITY
    assert (
        inference.extended_real_subtract(inference.ExtendedReal.undefined(), finite).state
        == inference.UNDEFINED_EXTENDED_REAL
    )


def test_extended_real_add_and_mean():
    finite = inference.ExtendedReal.finite(1.0)
    plus = inference.ExtendedReal.positive_infinity()
    assert inference.extended_real_add(finite, finite).value == 2.0
    assert inference.extended_real_add(finite, plus).state == inference.POSITIVE_INFINITY
    assert inference.extended_real_add(plus, plus).state == inference.POSITIVE_INFINITY
    assert (
        inference.extended_real_add(plus, inference.ExtendedReal.negative_infinity()).state
        == inference.UNDEFINED_EXTENDED_REAL
    )
    assert inference.extended_real_mean([finite, finite]).value == 1.0
    assert inference.extended_real_mean([finite, plus]).state == inference.POSITIVE_INFINITY
    with pytest.raises(inference.ExtendedRealContractViolation):
        inference.extended_real_mean([])


def test_mean_logloss_keeps_infinity_verbatim():
    result = inference.mean_logloss([(1.0, 1), (0.0, 1)])
    assert result.state == inference.POSITIVE_INFINITY
    result = inference.mean_logloss([(1.0, 1), (0.5, 0)])
    assert result.is_finite
    with pytest.raises(inference.BootstrapContractViolation):
        inference.mean_logloss([])


# ---------------------------------------------------------------------------
# Weighting
# ---------------------------------------------------------------------------


def test_row_weighted_mean():
    assert inference.row_weighted_mean([1.0, 2.0, 3.0]) == pytest.approx(2.0, abs=TOL)
    with pytest.raises(inference.PopulationContractViolation):
        inference.row_weighted_mean([])


def test_mmlu_weighting_is_not_a_naive_row_mean():
    """The equal-subject estimator must not collapse to a row mean."""
    strata = ["s0"] * 5 + ["s1"]
    values = [1.0] * 5 + [0.0]
    equal_subject = inference.equal_stratum_mean_of_stratum_means(strata, values)
    naive_row_mean = inference.row_weighted_mean(values)
    assert equal_subject == pytest.approx(0.5, abs=TOL)
    assert naive_row_mean == pytest.approx(5.0 / 6.0, abs=TOL)
    assert not math.isclose(equal_subject, naive_row_mean, abs_tol=1e-9)


def test_population_mean_dispatch_uses_the_frozen_estimator():
    strata = ["s0"] * 5 + ["s1"]
    values = [1.0] * 5 + [0.0]
    assert inference.population_mean_of_rows(mmlu_metadata(), strata, values) == pytest.approx(
        0.5, abs=TOL
    )
    assert inference.population_mean_of_rows(med_metadata(), strata, values) == pytest.approx(
        5.0 / 6.0, abs=TOL
    )
    assert inference.population_mean_of_rows(hella_metadata(), strata, values) == pytest.approx(
        5.0 / 6.0, abs=TOL
    )
    with pytest.raises(inference.PopulationContractViolation):
        inference.equal_stratum_mean_of_stratum_means(["s0"], [])


def test_aggregate_population_rows_uses_row_strata():
    rows = synthetic_row_set(MMLU, {"s0": 5, "s1": 1})
    values = [1.0] * 5 + [0.0]
    assert inference.aggregate_population_rows(mmlu_metadata(), rows, values) == pytest.approx(
        0.5, abs=TOL
    )
    with pytest.raises(inference.PopulationContractViolation):
        inference.aggregate_population_rows(mmlu_metadata(), rows, [1.0])


# ---------------------------------------------------------------------------
# Panel aggregation
# ---------------------------------------------------------------------------


def test_population_mean_requires_every_expected_model():
    per_model = {model: 1.0 for model in inference.PRIMARY_MODELS}
    assert inference.population_mean(per_model) == pytest.approx(1.0, abs=TOL)
    del per_model[inference.PRIMARY_MODELS[0]]
    with pytest.raises(inference.PanelIncomplete):
        inference.population_mean(per_model)
    with pytest.raises(inference.PanelIncomplete):
        inference.population_mean({**per_model, "extra/model": 1.0})


def test_panel_mean_requires_every_expected_population():
    per_population = {population: 2.0 for population in inference.PRIMARY_POPULATIONS}
    assert inference.panel_mean(per_population) == pytest.approx(2.0, abs=TOL)
    del per_population[MMLU]
    with pytest.raises(inference.PanelIncomplete):
        inference.panel_mean(per_population)


def test_panel_aggregate_fails_closed_on_a_missing_cell():
    values = {
        (model, population): 1.0
        for model in inference.PRIMARY_MODELS
        for population in inference.PRIMARY_POPULATIONS
    }
    assert inference.panel_aggregate(values) == pytest.approx(1.0, abs=TOL)
    del values[(inference.PRIMARY_MODELS[0], HELLA)]
    with pytest.raises(inference.PanelIncomplete):
        inference.panel_aggregate(values)


def test_panel_weighting_is_equal_per_population_and_per_model():
    values = {}
    for model in inference.PRIMARY_MODELS:
        values[(model, MMLU)] = 100.0
        values[(model, HELLA)] = 0.0
        values[(model, MED)] = 0.0
    assert inference.panel_aggregate(values) == pytest.approx(100.0 / 3.0, abs=TOL)
    values[(inference.PRIMARY_MODELS[0], HELLA)] = 4.0
    assert inference.panel_aggregate(values) == pytest.approx(100.0 / 3.0 + 1.0 / 3.0, abs=TOL)


# ---------------------------------------------------------------------------
# Risk matrix and the three estimands
# ---------------------------------------------------------------------------


def test_risk_matrix_separates_the_three_estimands():
    rows = [
        make_row("i0", MMLU, "s", 1, 0.2, 0.9),
        make_row("i1", MMLU, "s", 0, 0.3, 0.8),
        make_row("i2", MMLU, "s", 1, 0.4, 0.7),
        make_row("i3", MMLU, "s", 0, 0.5, 0.6),
    ]
    def cross(score):
        return min(1.0, score + 0.05)

    def native(score):
        return max(0.0, score - 0.05)

    matrix = inference.risk_matrix(rows, "CAT->OVR", cross, native)
    assert matrix.r_raw == inference.risk_raw(rows, "OVR")
    assert matrix.r_native == inference.risk_native(rows, "OVR", native)
    assert matrix.r_cross == inference.risk_cross(rows, "CAT->OVR", cross)
    assert matrix.delta_deploy == inference.delta_deploy(rows, "CAT->OVR", cross)
    assert matrix.delta_native == inference.delta_native(rows, "CAT->OVR", native)
    assert matrix.delta_transport == inference.delta_transport(rows, "CAT->OVR", cross, native)


def test_cross_path_numerical_audit_matches_paired_aggregation():
    """Path A (risk subtraction) and Path B (paired per-row differences) agree."""
    rows = [
        make_row(f"i{i}", MMLU, "s", i % 2, 0.05 * i, 0.9 - 0.04 * i) for i in range(20)
    ]

    def cross(score):
        return min(1.0, score * 1.1)

    def native(score):
        return score * 0.9

    matrix = inference.risk_matrix(rows, "CAT->OVR", cross, native)
    target_scores = [row.score("OVR") for row in rows]
    labels = [row.label for row in rows]
    raw_losses = [
        inference.brier_loss(score, label)
        for score, label in zip(target_scores, labels, strict=True)
    ]
    cross_losses = [
        inference.brier_loss(cross(score), label)
        for score, label in zip(target_scores, labels, strict=True)
    ]
    native_losses = [
        inference.brier_loss(native(score), label)
        for score, label in zip(target_scores, labels, strict=True)
    ]

    assert matrix.delta_deploy == pytest.approx(
        inference.mean_paired_difference(cross_losses, raw_losses), abs=TOL
    )
    assert matrix.delta_native == pytest.approx(
        inference.mean_paired_difference(native_losses, raw_losses), abs=TOL
    )
    assert matrix.delta_transport == pytest.approx(
        inference.mean_paired_difference(cross_losses, native_losses), abs=TOL
    )
    assert matrix.delta_deploy == pytest.approx(matrix.r_cross - matrix.r_raw, abs=TOL)
    assert matrix.delta_native == pytest.approx(matrix.r_native - matrix.r_raw, abs=TOL)
    assert matrix.delta_transport == pytest.approx(matrix.r_cross - matrix.r_native, abs=TOL)


def test_algebraic_identity_between_the_three_deltas():
    rows = [
        make_row(f"i{i}", MMLU, "s", i % 2, 0.05 * i, 0.9 - 0.05 * i) for i in range(18)
    ]
    def cross(score):
        return min(1.0, score + 0.07)

    def native(score):
        return max(0.0, score - 0.03)

    matrix = inference.risk_matrix(rows, "OVR->CAT", cross, native)
    assert matrix.delta_deploy == pytest.approx(
        matrix.delta_transport + matrix.delta_native, abs=TOL
    )


def test_paired_difference_requires_matching_lengths():
    with pytest.raises(inference.BootstrapContractViolation):
        inference.mean_paired_difference([1.0], [1.0, 2.0])
    with pytest.raises(inference.BootstrapContractViolation):
        inference.mean_paired_difference([], [])


# ---------------------------------------------------------------------------
# Factorial contrasts
# ---------------------------------------------------------------------------


def test_factorial_contrasts_formula():
    values = {"P-low": 1.0, "P-historical": 2.0, "L-low": 3.0, "L-historical": 4.0}
    contrasts = inference.factorial_contrasts(values)
    assert contrasts["Feature"] == pytest.approx(0.5 * (3.0 + 4.0 - 1.0 - 2.0), abs=TOL)
    assert contrasts["Regularization"] == pytest.approx(0.5 * (1.0 + 3.0 - 2.0 - 4.0), abs=TOL)
    assert contrasts["Interaction"] == pytest.approx((3.0 - 1.0) - (4.0 - 2.0), abs=TOL)


def test_factorial_rejects_standalone_procedures():
    with pytest.raises(inference.FactorialContractViolation):
        inference.factorial_contrasts(
            {
                "P-low": 1.0,
                "P-historical": 2.0,
                "L-low": 3.0,
                "L-historical": 4.0,
                "I-isotonic": 5.0,
            }
        )
    with pytest.raises(inference.FactorialContractViolation):
        inference.factorial_contrasts({"P-low": 1.0, "P-historical": 2.0, "L-low": 3.0})
    assert "I-isotonic" not in inference.LOGISTIC_CORE_PROCEDURES
    assert "B-beta" not in inference.LOGISTIC_CORE_PROCEDURES
    assert set(inference.LOGISTIC_CORE_PROCEDURES) == {
        "P-low",
        "P-historical",
        "L-low",
        "L-historical",
    }


def test_factorial_transform_is_linear_across_estimands():
    deploy = {"P-low": 1.0, "P-historical": 2.0, "L-low": 3.0, "L-historical": 4.0}
    transport = {"P-low": 0.5, "P-historical": 0.5, "L-low": 0.25, "L-historical": 0.25}
    native = {
        key: deploy[key] - transport[key] for key in inference.LOGISTIC_CORE_PROCEDURES
    }
    deploy_contrasts = inference.factorial_contrasts(deploy)
    transport_contrasts = inference.factorial_contrasts(transport)
    native_contrasts = inference.factorial_contrasts(native)
    for effect in inference.FACTORIAL_EFFECTS:
        assert deploy_contrasts[effect] == pytest.approx(
            transport_contrasts[effect] + native_contrasts[effect], abs=TOL
        )


# ---------------------------------------------------------------------------
# Deterministic draw kernel and ordering
# ---------------------------------------------------------------------------


def test_deterministic_index_matches_the_frozen_rule():
    identity = {"a": 1, "b": "x"}
    assert inference.deterministic_index(identity, 7) == int(fingerprint(identity)[:16], 16) % 7
    assert 0 <= inference.deterministic_index(identity, 7) < 7
    with pytest.raises(inference.BootstrapContractViolation):
        inference.deterministic_index(identity, 0)


def test_row_draw_identity_fields_match_the_freeze():
    audit = _load(FREEZE_JSON)["frozen_semantic_payload"]["test_bootstrap"][
        "deterministic_identity"
    ]
    identity = inference.row_draw_identity(
        protocol_id="p",
        protocol_version=1,
        population_id=MMLU,
        population_fingerprint="fp",
        replicate_index=3,
        stratum="s",
        draw_index=2,
        pool_size=20,
    )
    assert sorted(identity) == sorted(audit["row_draw_identity_fields"])
    clustered = inference.row_draw_identity(
        protocol_id="p",
        protocol_version=1,
        population_id=HELLA,
        population_fingerprint="fp",
        replicate_index=3,
        stratum="s",
        draw_index=2,
        pool_size=20,
        cluster_mode_marker="source_id-cluster",
    )
    assert "cluster_mode_marker" in clustered
    assert "cluster_mode_marker" in audit["cluster_draw_identity_extra"]


def test_stable_ordering_helpers():
    rows = synthetic_row_set(MMLU, {"s1": 2, "s0": 3})
    assert inference.stable_strata(rows) == ("s0", "s1")
    ordered = inference.stable_rows(rows)
    assert [row.item_id for row in ordered] == sorted(row.item_id for row in rows)
    with pytest.raises(inference.PopulationContractViolation):
        inference.stable_clusters(rows)
    cluster_rows = hellaswag_cluster_rows()
    assert inference.stable_clusters(cluster_rows) == ("c1", "c2", "c3")


def test_draw_is_invariant_under_input_order_permutation():
    rows = synthetic_row_set(MMLU, {"s0": 4, "s1": 3})
    metadata = mmlu_metadata()
    reference = inference.build_test_draw(rows, metadata, 5)
    shuffled = list(reversed(rows))
    rotated = rows[3:] + rows[:3]
    for candidate in (shuffled, rotated):
        draw = inference.build_test_draw(candidate, metadata, 5)
        assert draw.occurrences == reference.occurrences
        assert draw.stratum_order == reference.stratum_order


def test_draw_identity_excludes_the_model_label():
    rows = synthetic_row_set(MMLU, {"s0": 4, "s1": 3})
    metadata = mmlu_metadata()
    first = inference.build_test_draw(rows, metadata, 4, model_label="model-a")
    second = inference.build_test_draw(rows, metadata, 4, model_label="model-b")
    assert first.occurrences == second.occurrences
    assert first.draw_identity_payload() == second.draw_identity_payload()
    assert first.provenance["model_label"] == "model-a"
    assert second.provenance["model_label"] == "model-b"
    assert "model_label" not in first.draw_identity_payload()


def test_metadata_rejects_inconsistent_modes():
    with pytest.raises(inference.PopulationContractViolation):
        make_metadata(MMLU, mode="unknown", stratum_field="subject", weighting="row-weighted-mean")
    with pytest.raises(inference.PopulationContractViolation):
        make_metadata(HELLA, mode=HELLA_MODE, stratum_field="activity_label",
                      weighting="row-weighted-mean", group_field=None)
    with pytest.raises(inference.PopulationContractViolation):
        make_metadata(MED, mode=MED_MODE, stratum_field="topic_name",
                      weighting="row-weighted-mean")
    with pytest.raises(inference.PopulationContractViolation):
        make_metadata(MMLU, mode=MMLU_MODE, stratum_field="topic_name",
                      weighting="row-weighted-mean")


# ---------------------------------------------------------------------------
# Population TEST samplers
# ---------------------------------------------------------------------------


def test_mmlu_test_sampler_draws_the_original_subject_row_count():
    rows = synthetic_row_set(MMLU, {"s0": 2, "s1": 3})
    draw = inference.build_test_draw(rows, mmlu_metadata(), 0)
    assert draw.stratum_order == ("s0", "s1")
    assert len(draw.rows_for_stratum("s0")) == 2
    assert len(draw.rows_for_stratum("s1")) == 3
    assert draw.expanded_row_count == 5
    assert all(row.population_id == MMLU for row in draw.occurrences)


def test_med_test_sampler_is_subject_name_stratified_and_row_weighted():
    rows = synthetic_row_set(MED, {"subject_name-0": 3, "subject_name-1": 2})
    metadata = med_metadata()
    draw = inference.build_test_draw(rows, metadata, 1)
    assert draw.stratum_order == ("subject_name-0", "subject_name-1")
    assert len(draw.rows_for_stratum("subject_name-0")) == 3
    assert len(draw.rows_for_stratum("subject_name-1")) == 2
    assert metadata.estimand_weighting == "row-weighted-mean"
    assert metadata.stratum_field == "subject_name"


def test_hellaswag_cluster_sampler_never_splits_a_cluster():
    rows = hellaswag_cluster_rows()
    metadata = hella_metadata()
    sizes = {"c1": 1, "c2": 5, "c3": 2}
    saw_duplicate = False
    saw_different_total = False
    for replicate in range(40):
        draw = inference.build_test_draw(rows, metadata, replicate)
        counts: dict[str, int] = {}
        for row in draw.occurrences:
            counts[row.cluster_id] = counts.get(row.cluster_id, 0) + 1
        for cluster, count in counts.items():
            assert count % sizes[cluster] == 0
            if count // sizes[cluster] > 1:
                saw_duplicate = True
        if draw.expanded_row_count != len(rows):
            saw_different_total = True
        for stratum in draw.stratum_order:
            stratum_rows = draw.rows_for_stratum(stratum)
            cluster_blocks = [row.cluster_id for row in stratum_rows]
            for cluster in set(cluster_blocks):
                assert cluster_blocks.count(cluster) % sizes[cluster] == 0
    assert saw_duplicate
    assert saw_different_total


def test_hellaswag_activity_with_a_single_cluster_draws_it_once():
    rows = [make_row("only-r1", HELLA, "solo", 1, 0.2, 0.8, cluster_id="only")]
    draw = inference.build_test_draw(rows, hella_metadata(), 3)
    assert draw.occurrences == tuple(rows)


def test_hellaswag_cluster_stratum_conflict_is_a_structural_error():
    rows = [
        make_row("a", HELLA, "act-1", 1, 0.2, 0.8, cluster_id="shared"),
        make_row("b", HELLA, "act-2", 0, 0.3, 0.7, cluster_id="shared"),
    ]
    with pytest.raises(inference.HellaswagClusterStratumAmbiguity):
        inference.validate_hellaswag_cluster_stratum(rows)
    with pytest.raises(inference.HellaswagClusterStratumAmbiguity):
        inference.build_test_draw(rows, hella_metadata(), 0)
    assert (
        inference.validate_hellaswag_cluster_stratum(hellaswag_cluster_rows())["status"] == "PASS"
    )


def test_hellaswag_cluster_sampler_rejects_missing_cluster_ids():
    rows = [make_row("a", HELLA, "act-1", 1, 0.2, 0.8)]
    with pytest.raises(inference.PopulationContractViolation):
        inference.build_test_draw(rows, hella_metadata(), 0)


def test_cluster_resampling_unit_and_row_weighting_are_both_honoured():
    """The resampling unit is the source_id cluster; the statistic unit is the row."""
    rows = hellaswag_cluster_rows()
    sizes = {"c1": 1, "c2": 5}
    for replicate in range(60):
        draw = inference.build_test_draw(rows, hella_metadata(), replicate)
        act_one = [row for row in draw.occurrences if row.stratum == "act-1"]
        per_cluster: dict[str, list[float]] = {}
        for row in act_one:
            per_cluster.setdefault(row.cluster_id, []).append(row.cat_score)
        if set(per_cluster) != set(sizes):
            continue
        if any(len(values) != sizes[cluster] for cluster, values in per_cluster.items()):
            continue
        row_mean = inference.row_weighted_mean([row.cat_score for row in act_one])
        cluster_mean = math.fsum(
            inference.row_weighted_mean(values) for values in per_cluster.values()
        ) / len(per_cluster)
        assert row_mean == pytest.approx(0.6166666666666667)
        assert cluster_mean == pytest.approx(0.45)
        assert row_mean != pytest.approx(cluster_mean, abs=1e-6)
        return
    pytest.fail("no replicate drew both act-1 clusters exactly once")


# ---------------------------------------------------------------------------
# Formal population validators
# ---------------------------------------------------------------------------


def test_formal_mmlu_population_validates():
    rows = formal_mmlu_rows()
    assert len(rows) == inference.FORMAL_MMLU_TEST_COUNT
    report = inference.validate_formal_population(rows, mmlu_metadata())
    assert report["stratum_count"] == inference.FORMAL_MMLU_SUBJECT_COUNT
    assert report["test_count"] == inference.FORMAL_MMLU_TEST_COUNT
    with pytest.raises(inference.PopulationContractViolation):
        inference.validate_formal_population(rows[:-1], mmlu_metadata())


def test_formal_medmcqa_population_validates():
    rows = formal_med_rows()
    assert len(rows) == inference.FORMAL_MEDMCQA_TEST_COUNT
    report = inference.validate_formal_population(rows, med_metadata())
    assert report["stratum_count"] == inference.FORMAL_MEDMCQA_SUBJECT_COUNT
    assert report["test_count"] == inference.FORMAL_MEDMCQA_TEST_COUNT
    with pytest.raises(inference.PopulationContractViolation):
        inference.validate_formal_population(rows[:-1], med_metadata())


def test_formal_hellaswag_population_validates():
    rows = formal_hellaswag_rows()
    assert len(rows) == inference.FORMAL_HELLASWAG_TEST_COUNT
    report = inference.validate_formal_population(rows, hella_metadata())
    assert report["cluster_count"] == inference.FORMAL_HELLASWAG_SOURCE_ID_COUNT
    assert report["stratum_count"] == inference.FORMAL_HELLASWAG_ACTIVITY_LABEL_COUNT
    assert report["test_count"] == inference.FORMAL_HELLASWAG_TEST_COUNT
    with pytest.raises(inference.PopulationContractViolation):
        inference.validate_formal_population(rows[:-1], hella_metadata())


def test_validate_formal_population_rejects_an_unknown_population():
    rows = synthetic_row_set("other", {"s": 1})
    with pytest.raises(inference.PopulationContractViolation):
        inference.validate_formal_population(rows, mmlu_metadata())


# ---------------------------------------------------------------------------
# TRAIN-refit sampler
# ---------------------------------------------------------------------------


def test_mmlu_train_refit_preserves_total_n_and_stratum_counts():
    rows = mmlu_train_rows()
    assert len(rows) == inference.FORMAL_MMLU_TRAIN_COUNT
    draw = inference.build_train_refit_draw(rows, mmlu_metadata(), 0)
    assert draw.total_n == inference.FORMAL_MMLU_TRAIN_COUNT
    counts = inference.mmlu_refit_draw_counts(draw)
    assert len(counts) == inference.FORMAL_MMLU_SUBJECT_COUNT
    assert set(counts.values()) == {inference.FORMAL_MMLU_TRAIN_PER_SUBJECT}
    inference.validate_train_total_n(draw, mmlu_metadata(), inference.FORMAL_MMLU_TRAIN_COUNT)


def test_mmlu_refit_draw_count_is_eight_not_ten():
    """Regression guard against reusing the R3 historical 10-per-subject rule."""
    draw = inference.build_train_refit_draw(mmlu_train_rows(), mmlu_metadata(), 0)
    counts = inference.mmlu_refit_draw_counts(draw)
    assert set(counts.values()) == {8}
    assert 10 not in counts.values()
    assert inference.FORMAL_MMLU_TRAIN_PER_SUBJECT == 8


def test_n912_budget_preserves_the_larger_total():
    rows = mmlu_train_rows(train_per_subject=16)
    assert len(rows) == 912
    metadata = mmlu_metadata(train_count=456, n912_train_count=912)
    draw = inference.build_train_refit_draw(
        rows, metadata, 2, budget_identity=inference.BUDGET_N912
    )
    assert draw.total_n == 912
    inference.validate_train_total_n(draw, metadata, 912)
    with pytest.raises(inference.BootstrapContractViolation):
        inference.build_train_refit_draw(rows, metadata, 2, budget_identity="N100")
    with pytest.raises(inference.BootstrapContractViolation):
        inference.validate_train_total_n(draw, metadata, 500)


def test_hellaswag_train_refit_is_a_row_bootstrap_not_a_cluster_bootstrap():
    rows = hellaswag_train_rows()
    draw = inference.build_train_refit_draw(rows, hella_metadata(), 1)
    assert draw.total_n == len(rows)
    assert {row.cluster_id for row in draw.occurrences} <= {row.cluster_id for row in rows}
    cluster_sizes: dict[str, int] = {}
    for row in rows:
        cluster_sizes[row.cluster_id] = cluster_sizes.get(row.cluster_id, 0) + 1
    assert set(cluster_sizes.values()) == {1}


def test_med_train_refit_is_subject_name_stratified():
    rows = med_train_rows()
    draw = inference.build_train_refit_draw(rows, med_metadata(), 3)
    assert draw.stratum_order == ("subject_name-0", "subject_name-1", "subject_name-2",
                                 "subject_name-3", "subject_name-4")
    assert draw.total_n == len(rows)
    assert {row.stratum for row in draw.occurrences} == set(draw.stratum_order)


def test_refit_draw_has_no_model_or_procedure_dependency():
    parameters = set(inspect.signature(inference.build_train_refit_draw).parameters)
    assert "model" not in parameters
    assert "model_label" not in parameters
    assert "procedure" not in parameters
    rows = mmlu_train_rows()
    first = inference.build_train_refit_draw(rows, mmlu_metadata(), 7)
    second = inference.build_train_refit_draw(rows, mmlu_metadata(), 7)
    assert first.occurrences == second.occurrences
    other_budget = inference.build_train_refit_draw(
        rows, mmlu_metadata(train_count=456, n912_train_count=912), 7,
        budget_identity=inference.BUDGET_N912,
    )
    assert other_budget.occurrences != first.occurrences


def test_refit_draw_is_invariant_under_input_order_permutation():
    rows = mmlu_train_rows(train_per_subject=2)
    reference = inference.build_train_refit_draw(rows, mmlu_metadata(), 4)
    shuffled = list(reversed(rows))
    assert inference.build_train_refit_draw(shuffled, mmlu_metadata(), 4).occurrences == (
        reference.occurrences
    )


# ---------------------------------------------------------------------------
# Nearest-rank percentile
# ---------------------------------------------------------------------------


def test_nearest_rank_percentile_definition():
    ordered = [float(value) for value in range(1, 20001)]
    assert inference.nearest_rank_percentile(ordered, Fraction(1, 2)) == 10000.0
    assert inference.nearest_rank_percentile(ordered, Fraction(1, 480)) == 42.0
    assert inference.nearest_rank_percentile(ordered, Fraction(479, 480)) == 19959.0
    with pytest.raises(inference.BootstrapContractViolation):
        inference.nearest_rank_percentile([], Fraction(1, 2))
    with pytest.raises(inference.BootstrapContractViolation):
        inference.nearest_rank_percentile(ordered, Fraction(50))


def test_mandatory_percentile_ranks():
    n = 20000
    assert inference.percentile_rank(Fraction(1, 480), n) == 42
    assert inference.percentile_rank(Fraction(479, 480), n) == 19959
    assert inference.percentile_rank(Fraction(1, 320), n) == 63
    assert inference.percentile_rank(Fraction(319, 320), n) == 19938
    assert inference.percentile_rank(Fraction(1, 240), n) == 84
    assert inference.percentile_rank(Fraction(239, 240), n) == 19917
    n = 2000
    assert inference.percentile_rank(inference.REFIT_LOWER_LEVEL, n) == 50
    assert inference.percentile_rank(inference.REFIT_MEDIAN_LEVEL, n) == 1000
    assert inference.percentile_rank(inference.REFIT_UPPER_LEVEL, n) == 1950
    assert inference.REFIT_AUDIT_LOWER_RANK == 50
    assert inference.REFIT_AUDIT_MEDIAN_RANK == 1000
    assert inference.REFIT_AUDIT_UPPER_RANK == 1950


def test_refit_level_representation_is_normalization_only():
    """The refit levels are fractions of the replicate count, not percentages.

    ``1/40``, ``1/2`` and ``39/40`` are numerically identical to 2.5 %, 50 % and
    97.5 %; this is a representation normalization with no frozen semantic change.
    """
    assert Fraction(1, 40) == Fraction(25, 1000)
    assert float(Fraction(1, 40)) == 0.025
    assert float(Fraction(1, 2)) == 0.5
    assert float(Fraction(39, 40)) == 0.975
    assert Fraction(25, 1000) == inference.REFIT_LOWER_LEVEL
    assert Fraction(500, 1000) == inference.REFIT_MEDIAN_LEVEL
    assert Fraction(975, 1000) == inference.REFIT_UPPER_LEVEL
    assert inference.percentile_rank(inference.REFIT_LOWER_LEVEL, 2000) == 50
    assert inference.percentile_rank(inference.REFIT_MEDIAN_LEVEL, 2000) == 1000
    assert inference.percentile_rank(inference.REFIT_UPPER_LEVEL, 2000) == 1950
    # The confirmatory family tail is a fraction and must never be read as a
    # percentage: Fraction(1, 480) is rank 42 of 20000, not rank 1.
    assert Fraction(1, 480) == inference.PRIMARY_LOWER_TAIL
    assert inference.percentile_rank(inference.PRIMARY_LOWER_TAIL, 20000) == 42


def test_interval_structure_keeps_point_estimate_separate_from_the_median():
    samples = [float(value) for value in range(20000)]
    interval = inference.percentile_interval(
        samples,
        lower_tail=inference.PRIMARY_LOWER_TAIL,
        upper_tail=inference.PRIMARY_UPPER_TAIL,
        point_estimate=123.5,
    )
    assert interval.n == 20000
    assert interval.point_estimate == 123.5
    assert interval.bootstrap_median == 9999.0
    assert interval.lower == 41.0
    assert interval.upper == 19958.0
    assert interval.tail_rule == "1/480/479/480"
    assert interval.excludes_zero is True
    assert interval.status == inference.STATUS_COMPLETE
    payload = interval.payload()
    assert sorted(payload) == [
        "bootstrap_median",
        "excludes_zero",
        "lower",
        "n",
        "point_estimate",
        "status",
        "tail_rule",
        "upper",
    ]


def test_empty_interval_is_incomplete():
    interval = inference.percentile_interval(
        [],
        lower_tail=inference.PRIMARY_LOWER_TAIL,
        upper_tail=inference.PRIMARY_UPPER_TAIL,
        point_estimate=1.0,
    )
    assert interval.n == 0
    assert interval.lower is None
    assert interval.upper is None
    assert interval.status == inference.STATUS_INCOMPLETE


def test_excludes_zero_boundaries():
    assert inference.excludes_zero(0.1, 0.2) is True
    assert inference.excludes_zero(-0.2, -0.1) is True
    assert inference.excludes_zero(-0.1, 0.2) is False
    assert inference.excludes_zero(0.0, 0.2) is False
    assert inference.excludes_zero(-0.1, 0.0) is False


# ---------------------------------------------------------------------------
# Direct contrast rule
# ---------------------------------------------------------------------------


def test_contrast_per_replicate_is_direct_and_paired():
    left = [1.0, 2.0, 3.0]
    right = [0.5, 0.5, 0.5]
    assert inference.contrast_per_replicate(left, right) == (0.5, 1.5, 2.5)
    with pytest.raises(inference.BootstrapContractViolation):
        inference.contrast_per_replicate(left, right[:-1])


def test_contrast_interval_is_not_endpoint_subtraction():
    n = 2000
    left = [1.0 + 0.05 * math.sin(i) for i in range(n)]
    right = [1.0 + 0.05 * math.cos(i * 1.7) for i in range(n)]
    tails = {
        "lower_tail": inference.DIRECTION_LOWER_TAIL,
        "upper_tail": inference.DIRECTION_UPPER_TAIL,
    }
    cat = inference.percentile_interval(left, **tails)
    ovr = inference.percentile_interval(right, **tails)
    difference = inference.percentile_interval(
        inference.contrast_per_replicate(left, right), **tails
    )
    assert cat.excludes_zero is True
    assert ovr.excludes_zero is True
    assert difference.excludes_zero is False
    naive_lower = cat.lower - ovr.upper
    naive_upper = cat.upper - ovr.lower
    assert not (
        math.isclose(difference.lower, naive_lower, abs_tol=1e-9)
        and math.isclose(difference.upper, naive_upper, abs_tol=1e-9)
    )


# ---------------------------------------------------------------------------
# Hypothesis registries
# ---------------------------------------------------------------------------


def test_primary_registry_is_exactly_twelve():
    hypotheses = inference.primary_hypotheses()
    assert len(hypotheses) == inference.PRIMARY_FAMILY_SIZE == 12
    assert len({item.hypothesis_id for item in hypotheses}) == 12
    expected = {
        (estimand, direction, effect)
        for estimand in inference.PRIMARY_FAMILY_ESTIMANDS
        for direction in inference.DIRECTIONS
        for effect in inference.FACTORIAL_EFFECTS
    }
    observed = {
        (item.components["estimand"], item.components["direction"], item.components["effect"])
        for item in hypotheses
    }
    assert observed == expected
    for item in hypotheses:
        assert item.lower_tail == Fraction(1, 480)
        assert item.upper_tail == Fraction(479, 480)
        assert item.audit_lower_rank == 42
        assert item.audit_upper_rank == 19959
        assert item.replicates == 20000
        assert item.correction == "bonferroni-percentile-interval"
        assert item.percentile_rule == "nearest-rank-percentile"
        assert item.payload()["lower_tail"] == "1/480"
        assert item.payload()["upper_tail"] == "479/480"


def test_extension_registry_is_exactly_eight():
    hypotheses = inference.extension_hypotheses()
    assert len(hypotheses) == inference.EXTENSION_FAMILY_SIZE == 8
    assert len({item.hypothesis_id for item in hypotheses}) == 8
    expected = {
        (procedure, direction, estimand)
        for procedure in inference.STANDALONE_PROCEDURES
        for direction in inference.DIRECTIONS
        for estimand in inference.PRIMARY_FAMILY_ESTIMANDS
    }
    observed = {
        (item.components["procedure"], item.components["direction"], item.components["estimand"])
        for item in hypotheses
    }
    assert observed == expected
    primary_ids = {item.hypothesis_id for item in inference.primary_hypotheses()}
    assert not primary_ids & {item.hypothesis_id for item in hypotheses}
    for item in hypotheses:
        assert item.lower_tail == Fraction(1, 320)
        assert item.upper_tail == Fraction(319, 320)
        assert item.audit_lower_rank == 63
        assert item.audit_upper_rank == 19938


def test_direction_difference_registry_is_exactly_six():
    hypotheses = inference.direction_difference_hypotheses()
    assert len(hypotheses) == inference.DIRECTION_DIFFERENCE_FAMILY_SIZE == 6
    assert len({item.hypothesis_id for item in hypotheses}) == 6
    expected = {
        (effect, estimand)
        for effect in inference.FACTORIAL_EFFECTS
        for estimand in inference.PRIMARY_FAMILY_ESTIMANDS
    }
    observed = {
        (item.components["effect"], item.components["estimand"]) for item in hypotheses
    }
    assert observed == expected
    for item in hypotheses:
        assert item.lower_tail == Fraction(1, 240)
        assert item.upper_tail == Fraction(239, 240)
        assert item.audit_lower_rank == 84
        assert item.audit_upper_rank == 19917


def test_native_reference_registry_is_exactly_twelve():
    hypotheses = inference.native_reference_hypotheses()
    assert len(hypotheses) == inference.NATIVE_REFERENCE_FAMILY_SIZE == 12
    assert len({item.hypothesis_id for item in hypotheses}) == 12
    expected = {
        (direction, procedure)
        for direction in inference.DIRECTIONS
        for procedure in inference.ALL_PROCEDURES
    }
    observed = {
        (item.components["direction"], item.components["procedure"]) for item in hypotheses
    }
    assert observed == expected
    for item in hypotheses:
        assert item.lower_tail == Fraction(1, 480)
        assert item.upper_tail == Fraction(479, 480)
        assert item.audit_lower_rank == 42
        assert item.audit_upper_rank == 19959


def test_native_reference_state_boundaries_are_unresolved():
    assert (
        inference.native_reference_state(-0.2, -0.1)
        == inference.NATIVE_IMPROVEMENT_SUPPORTED
    )
    assert (
        inference.native_reference_state(0.1, 0.2) == inference.NATIVE_DEGRADATION_SUPPORTED
    )
    assert inference.native_reference_state(-0.1, 0.0) == inference.NATIVE_ADEQUACY_UNRESOLVED
    assert inference.native_reference_state(0.0, 0.1) == inference.NATIVE_ADEQUACY_UNRESOLVED
    assert inference.native_reference_state(-0.1, 0.1) == inference.NATIVE_ADEQUACY_UNRESOLVED


# ---------------------------------------------------------------------------
# Bootstrap engines (synthetic only)
# ---------------------------------------------------------------------------


def test_run_test_bootstrap_reuses_one_draw_per_population_and_replicate():
    rows = synthetic_row_set(MMLU, {"s0": 3, "s1": 2})
    metadata = {MMLU: mmlu_metadata()}
    seen: list[tuple[str, int]] = []

    def statistic(population_id, draw):
        seen.append((population_id, draw.replicate_index))
        return float(draw.expanded_row_count)

    result = inference.run_test_bootstrap(
        rows_by_population={MMLU: rows},
        metadata_by_population=metadata,
        statistic=statistic,
        replicates=5,
        model_label="synthetic",
    )
    assert result.replicates == 5
    assert result.protocol_id == inference.TEST_BOOTSTRAP_PROTOCOL_ID
    assert len(result.samples[MMLU]) == 5
    assert seen == [(MMLU, index) for index in range(5)]
    assert all(value == 5.0 for value in result.samples[MMLU])
    interval = result.interval(
        MMLU,
        lower_tail=inference.PRIMARY_LOWER_TAIL,
        upper_tail=inference.PRIMARY_UPPER_TAIL,
    )
    assert interval.n == 5
    with pytest.raises(inference.BootstrapContractViolation):
        inference.run_test_bootstrap(
            rows_by_population={MMLU: rows},
            metadata_by_population=metadata,
            statistic=statistic,
            replicates=0,
        )


def test_run_test_bootstrap_default_replicate_count_is_formal():
    parameters = inspect.signature(inference.run_test_bootstrap).parameters
    assert parameters["replicates"].default == 20000


def test_panel_test_bootstrap_full_panel_fixture():
    """Tiny synthetic fixture covering 4 models x 3 populations x 2 directions x 6 procedures."""
    models = ("m-1", "m-2", "m-3", "m-4")
    populations = ("pop-a", "pop-b", "pop-c")
    rows_by_population = {
        population: synthetic_row_set(population, {"s0": 3, "s1": 2})
        for population in populations
    }
    metadata_by_population = {
        population: make_metadata(
            population,
            mode=MMLU_MODE,
            stratum_field="subject",
            weighting="row-weighted-mean",
            population_fingerprint=f"fp-{population}",
        )
        for population in populations
    }
    base = {"pop-a": 1.0, "pop-b": 2.0, "pop-c": 3.0}
    model_offset = {"m-1": 0.0, "m-2": 0.1, "m-3": 0.2, "m-4": 0.3}
    procedure_offset = {
        name: 0.01 * index for index, name in enumerate(inference.ALL_PROCEDURES)
    }

    def unit_estimator(population, model, direction, procedure, draw):
        direction_offset = 0.0 if direction == "CAT->OVR" else 0.5
        value = (
            base[population]
            + model_offset[model]
            + direction_offset
            + procedure_offset[procedure]
        )
        return {
            "Delta_deploy": value,
            "Delta_transport": value / 2.0,
            "Delta_native": value / 4.0,
        }

    result = inference.run_panel_test_bootstrap(
        rows_by_population=rows_by_population,
        metadata_by_population=metadata_by_population,
        unit_estimator=unit_estimator,
        replicates=3,
        models=models,
        populations=populations,
    )
    assert len(result.primary_contrasts) == 12
    assert len(result.direction_differences) == 6
    assert len(result.extension_panel) == 8
    assert len(result.native_reference) == 12
    assert len(result.unit_values) == 4 * 3 * 2 * 6
    for samples in result.primary_contrasts.values():
        assert len(samples) == 3
    interval = result.primary_interval("CAT->OVR", "Delta_deploy", "Feature")
    assert interval.n == 3
    assert interval.tail_rule == "1/480/479/480"
    native = result.native_interval("CAT->OVR", "I-isotonic")
    assert native.n == 3
    assert native.tail_rule == "1/480/479/480"
    extension = result.extension_interval("B-beta", "OVR->CAT", "Delta_transport")
    assert extension.n == 3
    assert extension.tail_rule == "1/320/319/320"
    direction = result.direction_interval("Delta_transport", "Interaction")
    assert direction.n == 3
    assert direction.tail_rule == "1/240/239/240"


def test_panel_test_bootstrap_uses_hierarchical_equal_weighting():
    models = ("m-1", "m-2", "m-3", "m-4")
    populations = ("pop-a", "pop-b", "pop-c")
    rows_by_population = {
        population: synthetic_row_set(population, {"s0": 2, "s1": 1})
        for population in populations
    }
    metadata_by_population = {
        population: make_metadata(
            population,
            mode=MMLU_MODE,
            stratum_field="subject",
            weighting="row-weighted-mean",
            population_fingerprint=f"fp-{population}",
        )
        for population in populations
    }
    base = {"pop-a": 10.0, "pop-b": 0.0, "pop-c": 0.0}
    model_offset = {"m-1": 0.0, "m-2": 1.0, "m-3": 2.0, "m-4": 3.0}

    def unit_estimator(population, model, direction, procedure, draw):
        value = base[population] + model_offset[model]
        return {"Delta_deploy": value, "Delta_transport": value, "Delta_native": value}

    result = inference.run_panel_test_bootstrap(
        rows_by_population=rows_by_population,
        metadata_by_population=metadata_by_population,
        unit_estimator=unit_estimator,
        replicates=2,
        models=models,
        populations=populations,
    )
    for index in range(2):
        population_means = []
        for population in populations:
            per_model = [
                result.unit_values[(model, population, "CAT->OVR", "P-low")]["Delta_deploy"][
                    index
                ]
                for model in models
            ]
            population_means.append(math.fsum(per_model) / 4.0)
        expected = math.fsum(population_means) / 3.0
        observed = result.panel_values[("CAT->OVR", "P-low")]["Delta_deploy"][index]
        assert observed == pytest.approx(expected, abs=TOL)
        assert observed == pytest.approx((10.0 + 1.5 + 1.5 + 1.5) / 3.0, abs=TOL)


def test_panel_test_bootstrap_primary_contrast_matches_factorial_transform():
    models = ("m-1", "m-2")
    populations = ("pop-a", "pop-b", "pop-c")
    rows_by_population = {
        population: synthetic_row_set(population, {"s0": 2}) for population in populations
    }
    metadata_by_population = {
        population: make_metadata(
            population,
            mode=MMLU_MODE,
            stratum_field="subject",
            weighting="row-weighted-mean",
            population_fingerprint=f"fp-{population}",
        )
        for population in populations
    }
    offsets = {name: float(index) for index, name in enumerate(inference.ALL_PROCEDURES)}

    def unit_estimator(population, model, direction, procedure, draw):
        value = offsets.get(procedure, 0.0)
        return {"Delta_deploy": value, "Delta_transport": value, "Delta_native": value}

    result = inference.run_panel_test_bootstrap(
        rows_by_population=rows_by_population,
        metadata_by_population=metadata_by_population,
        unit_estimator=unit_estimator,
        replicates=2,
        models=models,
        populations=populations,
        procedures=inference.ALL_PROCEDURES,
    )
    for index in range(2):
        per_procedure = {
            procedure: result.panel_values[("CAT->OVR", procedure)]["Delta_deploy"][index]
            for procedure in inference.LOGISTIC_CORE_PROCEDURES
        }
        expected = inference.factorial_contrasts(per_procedure)
        for effect in inference.FACTORIAL_EFFECTS:
            assert result.primary_contrasts[("CAT->OVR", "Delta_deploy", effect)][
                index
            ] == pytest.approx(expected[effect], abs=TOL)


def test_panel_test_bootstrap_direction_difference_is_paired():
    models = ("m-1",)
    populations = ("pop-a", "pop-b", "pop-c")
    rows_by_population = {
        population: synthetic_row_set(population, {"s0": 2}) for population in populations
    }
    metadata_by_population = {
        population: make_metadata(
            population,
            mode=MMLU_MODE,
            stratum_field="subject",
            weighting="row-weighted-mean",
            population_fingerprint=f"fp-{population}",
        )
        for population in populations
    }

    offsets = {name: float(index) for index, name in enumerate(inference.ALL_PROCEDURES)}

    def unit_estimator(population, model, direction, procedure, draw):
        value = offsets[procedure]
        if direction == "OVR->CAT":
            value = 3.0 - value
        return {"Delta_deploy": value, "Delta_transport": value, "Delta_native": value}

    result = inference.run_panel_test_bootstrap(
        rows_by_population=rows_by_population,
        metadata_by_population=metadata_by_population,
        unit_estimator=unit_estimator,
        replicates=4,
        models=models,
        populations=populations,
        procedures=inference.ALL_PROCEDURES,
    )
    for estimand in inference.PRIMARY_FAMILY_ESTIMANDS:
        for effect in inference.FACTORIAL_EFFECTS:
            cat = result.primary_contrasts[("CAT->OVR", estimand, effect)]
            ovr = result.primary_contrasts[("OVR->CAT", estimand, effect)]
            expected = inference.contrast_per_replicate(cat, ovr)
            assert result.direction_differences[(estimand, effect)] == expected
    assert any(
        any(value != 0.0 for value in result.direction_differences[(estimand, effect)])
        for estimand in inference.PRIMARY_FAMILY_ESTIMANDS
        for effect in inference.FACTORIAL_EFFECTS
    )


# ---------------------------------------------------------------------------
# Dependency isolation amendment (primary never blocked by I/B availability)
# ---------------------------------------------------------------------------


def _dependency_panel(
    models: tuple[str, ...] = ("m-1", "m-2"),
    populations: tuple[str, ...] = ("pop-a", "pop-b", "pop-c"),
):
    rows_by_population = {
        population: synthetic_row_set(population, {"s0": 2, "s1": 1})
        for population in populations
    }
    metadata_by_population = {
        population: make_metadata(
            population,
            mode=MMLU_MODE,
            stratum_field="subject",
            weighting="row-weighted-mean",
            population_fingerprint=f"fp-{population}",
        )
        for population in populations
    }
    return rows_by_population, metadata_by_population


def _offset_unit_estimator(offsets):
    def unit_estimator(population, model, direction, procedure, draw):
        value = offsets.get(procedure, 0.0)
        if direction == "OVR->CAT":
            value = value + 10.0
        return {
            "Delta_deploy": value,
            "Delta_transport": value / 2.0,
            "Delta_native": value / 4.0,
        }

    return unit_estimator


def test_primary_bootstrap_does_not_require_extension_procedures():
    rows_by_population, metadata_by_population = _dependency_panel()
    offsets = {
        name: float(index)
        for index, name in enumerate(inference.LOGISTIC_CORE_PROCEDURES)
    }
    result = inference.run_panel_test_bootstrap(
        rows_by_population=rows_by_population,
        metadata_by_population=metadata_by_population,
        unit_estimator=_offset_unit_estimator(offsets),
        replicates=3,
        models=("m-1", "m-2"),
        populations=("pop-a", "pop-b", "pop-c"),
        procedures=inference.LOGISTIC_CORE_PROCEDURES,
    )
    assert len(result.primary_contrasts) == 12
    assert len(result.direction_differences) == 6
    assert len(result.extension_panel) == 0
    assert len(result.native_reference) == 8  # 2 directions x 4 core procedures
    interval = result.primary_interval("CAT->OVR", "Delta_deploy", "Feature")
    assert interval.n == 3
    assert interval.tail_rule == "1/480/479/480"
    status = result.family_status()
    assert status["primary"]["family_size"] == 12
    assert status["primary"]["status"] == inference.STATUS_COMPLETE
    assert status["secondary_extension"]["family_size"] == 8
    assert status["secondary_extension"]["status"] == inference.STATUS_INCOMPLETE
    assert status["secondary_extension"]["incomplete_count"] == 8
    assert status["secondary_native_reference"]["family_size"] == 12
    assert status["secondary_native_reference"]["incomplete_count"] == 4
    assert result.native_interval("CAT->OVR", "P-low").n == 3


def test_extension_incompleteness_does_not_block_primary():
    rows_by_population, metadata_by_population = _dependency_panel()
    offsets = {
        name: float(index)
        for index, name in enumerate(inference.LOGISTIC_CORE_PROCEDURES)
    }
    result = inference.run_panel_test_bootstrap(
        rows_by_population=rows_by_population,
        metadata_by_population=metadata_by_population,
        unit_estimator=_offset_unit_estimator(offsets),
        replicates=2,
        models=("m-1", "m-2"),
        populations=("pop-a", "pop-b", "pop-c"),
        procedures=inference.LOGISTIC_CORE_PROCEDURES,
    )
    # Only the four core procedures were ever evaluated: no fake I/B value.
    assert {
        key[3] for key in result.unit_values
    } == set(inference.LOGISTIC_CORE_PROCEDURES)
    for procedure in inference.STANDALONE_PROCEDURES:
        for direction in inference.DIRECTIONS:
            for estimand in inference.PRIMARY_FAMILY_ESTIMANDS:
                with pytest.raises(inference.DependencyUnavailable):
                    result.extension_interval(procedure, direction, estimand)
    for direction in inference.DIRECTIONS:
        for effect in inference.FACTORIAL_EFFECTS:
            assert result.primary_interval(direction, "Delta_transport", effect).n == 2


def test_missing_core_blocks_primary_but_not_complete_extension():
    rows_by_population, metadata_by_population = _dependency_panel()
    offsets = {name: float(index) for index, name in enumerate(inference.ALL_PROCEDURES)}
    procedures = ("P-low", "P-historical", "L-low", "I-isotonic", "B-beta")
    assert "L-historical" not in procedures
    result = inference.run_panel_test_bootstrap(
        rows_by_population=rows_by_population,
        metadata_by_population=metadata_by_population,
        unit_estimator=_offset_unit_estimator(offsets),
        replicates=3,
        models=("m-1", "m-2"),
        populations=("pop-a", "pop-b", "pop-c"),
        procedures=procedures,
    )
    assert len(result.primary_contrasts) == 0
    assert len(result.direction_differences) == 0
    assert len(result.extension_panel) == 8
    status = result.family_status()
    assert status["primary"]["status"] == inference.STATUS_INCOMPLETE
    assert status["primary"]["complete_count"] == 0
    assert status["secondary_direction_difference"]["status"] == inference.STATUS_INCOMPLETE
    assert status["secondary_extension"]["status"] == inference.STATUS_COMPLETE
    assert result.extension_interval("I-isotonic", "CAT->OVR", "Delta_deploy").n == 3
    with pytest.raises(inference.DependencyUnavailable):
        result.primary_interval("CAT->OVR", "Delta_deploy", "Feature")
    # Unrelated descriptive risk cells remain reportable.
    assert result.unit_values[("m-1", "pop-a", "CAT->OVR", "P-low")]["Delta_deploy"]
    assert result.panel_values[("CAT->OVR", "P-low")]["Delta_deploy"]


def test_native_reference_preserves_fixed_family_when_member_incomplete():
    rows_by_population, metadata_by_population = _dependency_panel()
    offsets = {
        name: float(index)
        for index, name in enumerate(inference.LOGISTIC_CORE_PROCEDURES)
    }
    result = inference.run_panel_test_bootstrap(
        rows_by_population=rows_by_population,
        metadata_by_population=metadata_by_population,
        unit_estimator=_offset_unit_estimator(offsets),
        replicates=2,
        models=("m-1", "m-2"),
        populations=("pop-a", "pop-b", "pop-c"),
        procedures=inference.LOGISTIC_CORE_PROCEDURES,
    )
    status = result.family_status()["secondary_native_reference"]
    assert status["family_size"] == 12
    assert status["incomplete_count"] == 4
    assert set(status["members"]) == {
        f"native-reference::{direction}::{procedure}"
        for direction in inference.DIRECTIONS
        for procedure in inference.ALL_PROCEDURES
    }
    assert result.native_interval("OVR->CAT", "L-low").n == 2
    with pytest.raises(inference.DependencyUnavailable):
        result.native_interval("OVR->CAT", "B-beta")


def test_missing_dependency_uses_domain_state_not_keyerror():
    rows_by_population, metadata_by_population = _dependency_panel()
    offsets = {
        name: float(index)
        for index, name in enumerate(inference.LOGISTIC_CORE_PROCEDURES)
    }
    result = inference.run_panel_test_bootstrap(
        rows_by_population=rows_by_population,
        metadata_by_population=metadata_by_population,
        unit_estimator=_offset_unit_estimator(offsets),
        replicates=2,
        models=("m-1", "m-2"),
        populations=("pop-a", "pop-b", "pop-c"),
        procedures=inference.LOGISTIC_CORE_PROCEDURES,
    )
    with pytest.raises(inference.DependencyUnavailable) as excinfo:
        result.extension_interval("I-isotonic", "CAT->OVR", "Delta_deploy")
    assert not isinstance(excinfo.value, KeyError)
    assert excinfo.value.code == "DEPENDENCY_UNAVAILABLE"
    assert excinfo.value.family == "standalone-i-isotonic-b-beta-extension"
    assert "I-isotonic" in excinfo.value.dependency
    assert excinfo.value.payload()["code"] == "DEPENDENCY_UNAVAILABLE"
    bootstrap = inference.run_test_bootstrap(
        rows_by_population={MMLU: synthetic_row_set(MMLU, {"s0": 2})},
        metadata_by_population={MMLU: mmlu_metadata()},
        statistic=lambda population_id, draw: 1.0,
        replicates=2,
    )
    with pytest.raises(inference.DependencyUnavailable):
        bootstrap.interval(
            HELLA,
            lower_tail=inference.PRIMARY_LOWER_TAIL,
            upper_tail=inference.PRIMARY_UPPER_TAIL,
        )


def test_twenty_thousand_replicate_smoke_on_a_tiny_synthetic_pool():
    rows = synthetic_row_set(MMLU, {"s0": 2, "s1": 2})
    result = inference.run_test_bootstrap(
        rows_by_population={MMLU: rows},
        metadata_by_population={MMLU: mmlu_metadata()},
        statistic=lambda population_id, draw: float(draw.expanded_row_count),
        replicates=inference.TEST_BOOTSTRAP_REPLICATES,
    )
    assert len(result.samples[MMLU]) == 20000
    assert set(result.samples[MMLU]) == {4.0}


# ---------------------------------------------------------------------------
# Coverage, failure records and fail-closed refits
# ---------------------------------------------------------------------------


def test_coverage_matrix_defaults_to_ineligible():
    matrix = inference.CoverageMatrix()
    assert matrix.status("m", "p", "P-low", "OVR") == inference.INELIGIBLE
    assert matrix.is_available("m", "p", "P-low", "OVR") is False
    assert matrix.incomplete_cells() == []
    with pytest.raises(inference.BootstrapContractViolation):
        matrix.set("m", "p", "P-low", "OVR", "MAYBE")


def test_primary_hypothesis_status_fails_closed_on_a_missing_procedure():
    matrix = inference.CoverageMatrix()
    fill_coverage(matrix, "OVR")
    fill_coverage(matrix, "CAT")
    assert matrix.primary_hypothesis_status("CAT->OVR", "Delta_deploy") == inference.STATUS_COMPLETE
    matrix.set(
        inference.PRIMARY_MODELS[0],
        MMLU,
        "L-historical",
        "OVR",
        inference.FAILED,
    )
    assert (
        matrix.primary_hypothesis_status("CAT->OVR", "Delta_deploy") == inference.STATUS_INCOMPLETE
    )
    assert matrix.primary_hypothesis_status("OVR->CAT", "Delta_deploy") == inference.STATUS_COMPLETE
    assert len(matrix.incomplete_cells()) == 1


def test_extension_hypothesis_status_needs_all_twelve_primary_cells():
    matrix = inference.CoverageMatrix()
    fill_coverage(matrix, "OVR")
    assert (
        matrix.extension_hypothesis_status("I-isotonic", "CAT->OVR", "Delta_deploy")
        == inference.STATUS_COMPLETE
    )
    matrix.set(inference.PRIMARY_MODELS[3], MED, "I-isotonic", "OVR", inference.INELIGIBLE)
    assert (
        matrix.extension_hypothesis_status("I-isotonic", "CAT->OVR", "Delta_deploy")
        == inference.STATUS_INCOMPLETE
    )
    assert (
        matrix.extension_hypothesis_status("B-beta", "CAT->OVR", "Delta_deploy")
        == inference.STATUS_COMPLETE
    )
    assert matrix.primary_hypothesis_status("CAT->OVR", "Delta_deploy") == inference.STATUS_COMPLETE


def test_incomplete_coverage_leaves_unrelated_blocks_reportable():
    matrix = inference.CoverageMatrix()
    fill_coverage(matrix, "OVR")
    fill_coverage(matrix, "CAT")
    matrix.set(inference.PRIMARY_MODELS[1], HELLA, "P-historical", "OVR", inference.FAILED)
    assert (
        matrix.primary_hypothesis_status("CAT->OVR", "Delta_deploy") == inference.STATUS_INCOMPLETE
    )
    assert (
        matrix.extension_hypothesis_status("I-isotonic", "CAT->OVR", "Delta_deploy")
        == inference.STATUS_COMPLETE
    )
    assert (
        matrix.extension_hypothesis_status("B-beta", "OVR->CAT", "Delta_transport")
        == inference.STATUS_COMPLETE
    )
    assert (
        matrix.primary_hypothesis_status("OVR->CAT", "Delta_transport")
        == inference.STATUS_COMPLETE
    )
    assert matrix.matrix()


def test_train_refit_block_fails_closed_on_one_failed_replicate():
    replicate_indices = list(range(10))

    def fit_and_evaluate(replicate_index):
        if replicate_index == 7:
            raise RuntimeError("synthetic solver failure")
        return float(replicate_index)

    block = inference.run_train_refit_block(
        replicate_indices=replicate_indices,
        procedure="L-low",
        model="m-1",
        population=MMLU,
        measurement_dependency="OVR",
        direction_dependency="CAT->OVR",
        fit_and_evaluate=fit_and_evaluate,
    )
    assert block.planned_replicates == 10
    assert block.successful_replicates == 9
    assert block.failed_replicates == 1
    assert block.status == inference.STATUS_INCOMPLETE
    assert block.interval is None
    assert len(block.failures) == 1
    failure = block.failures[0]
    assert failure.replicate == 7
    assert failure.procedure == "L-low"
    assert failure.model == "m-1"
    assert failure.population == MMLU
    assert failure.measurement_dependency == "OVR"
    assert failure.direction_dependency == "CAT->OVR"
    assert failure.error_code == "TRAIN_REFIT_REPLICATE_FAILED"
    assert failure.exception_type == "RuntimeError"
    assert failure.message == "synthetic solver failure"
    assert failure.payload()["replicate"] == 7
    assert block.payload()["interval"] is None


def test_train_refit_block_complete_has_an_interval():
    block = inference.run_train_refit_block(
        replicate_indices=list(range(2000)),
        procedure="P-low",
        model="m-1",
        population=MMLU,
        measurement_dependency="OVR",
        direction_dependency=None,
        fit_and_evaluate=lambda replicate_index: float(replicate_index),
    )
    assert block.status == inference.STATUS_COMPLETE
    assert block.failed_replicates == 0
    assert block.interval is not None
    assert block.interval.n == 2000
    assert block.interval.tail_rule == "1/40/39/40"
    assert block.interval.bootstrap_median == 999.0
    assert block.interval.lower == 49.0
    assert block.interval.upper == 1949.0


def test_one_failing_refit_block_does_not_affect_another():
    def failing(replicate_index):
        raise ValueError("synthetic")

    failed = inference.run_train_refit_block(
        replicate_indices=[0, 1],
        procedure="B-beta",
        model="m-1",
        population=MED,
        measurement_dependency="OVR",
        direction_dependency=None,
        fit_and_evaluate=failing,
    )
    complete = inference.run_train_refit_block(
        replicate_indices=[0, 1],
        procedure="P-low",
        model="m-1",
        population=MED,
        measurement_dependency="OVR",
        direction_dependency=None,
        fit_and_evaluate=lambda replicate_index: 1.0,
    )
    assert failed.status == inference.STATUS_INCOMPLETE
    assert failed.interval is None
    assert complete.status == inference.STATUS_COMPLETE
    assert complete.interval is not None


# ---------------------------------------------------------------------------
# Measurement completeness
# ---------------------------------------------------------------------------


def expected_references():
    return [
        inference.FrozenItemReference(item_id=f"i{index}", label=index % 2, anchor_index=index % 4)
        for index in range(3)
    ]


def provided_rows():
    return [
        make_row(f"i{index}", MMLU, "s", index % 2, 0.5, 0.5, anchor_index=index % 4)
        for index in range(3)
    ]


def test_measurement_completeness_accepts_a_complete_pairing():
    inference.validate_measurement_completeness(
        expected=expected_references(),
        provided=provided_rows(),
        population_id=MMLU,
        model_id="m-1",
    )


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda rows: rows[:1], "MISSING_ROW"),
        (
            lambda rows: [*rows, make_row("i9", MMLU, "s", 0, 0.5, 0.5, anchor_index=0)],
            "EXTRA_ROW",
        ),
        (lambda rows: [rows[0], rows[0], rows[2]], "DUPLICATE_PROVIDED_ITEM"),
        (lambda rows: [rows[0], rows[1], make_row("i2", MED, "s", 0, 0.5, 0.5, anchor_index=2)],
         "POPULATION_MISMATCH"),
        (lambda rows: [rows[0], rows[1], make_row("i2", MMLU, "s", 1, 0.5, 0.5, anchor_index=2)],
         "MISMATCHED_LABEL"),
        (lambda rows: [rows[0], rows[1], make_row("i2", MMLU, "s", 0, 0.5, 0.5)], "MISSING_ANCHOR"),
        (lambda rows: [rows[0], rows[1], make_row("i2", MMLU, "s", 0, 0.5, 0.5, anchor_index=3)],
         "MISMATCHED_ANCHOR"),
    ],
)
def test_measurement_completeness_fails_closed(mutation, code):
    rows = mutation(provided_rows())
    with pytest.raises(inference.MeasurementIncompleteness) as excinfo:
        inference.validate_measurement_completeness(
            expected=expected_references(),
            provided=rows,
            population_id=MMLU,
            model_id="m-1",
        )
    assert excinfo.value.code == code


def test_measurement_completeness_rejects_duplicate_expected_items():
    references = expected_references()
    duplicated = [*references, references[0]]
    with pytest.raises(inference.MeasurementIncompleteness) as excinfo:
        inference.validate_measurement_completeness(
            expected=duplicated,
            provided=provided_rows(),
            population_id=MMLU,
            model_id="m-1",
        )
    assert excinfo.value.code == "DUPLICATE_EXPECTED_ITEM"


def test_measurement_incompleteness_carries_its_code():
    error = inference.MeasurementIncompleteness("MISSING_CAT", "detail")
    assert error.code == "MISSING_CAT"
    assert "MISSING_CAT: detail" in str(error)


# ---------------------------------------------------------------------------
# N912 robustness infrastructure
# ---------------------------------------------------------------------------


def test_n912_pairing_validates_nestedness_and_test_identity():
    train_456 = expected_references()
    train_912 = [
        *train_456,
        inference.FrozenItemReference(item_id="i3", label=1, anchor_index=3),
        inference.FrozenItemReference(item_id="i4", label=0, anchor_index=0),
    ]
    test = [
        inference.FrozenItemReference(item_id=f"t{index}", label=index % 2, anchor_index=index % 4)
        for index in range(5)
    ]
    report = inference.validate_n912_pairing(
        train_456=train_456, train_912=train_912, test_456=test, test_912=list(test)
    )
    assert report["train_456_count"] == 3
    assert report["train_912_count"] == 5
    assert report["extension_count"] == 2
    assert report["test_count"] == 5
    assert report["train_456_subset_of_train_912"] is True
    assert report["test_identity_identical"] is True


def test_n912_rejects_a_broken_subset_and_a_changed_test():
    train_456 = expected_references()
    with pytest.raises(inference.N912ContractViolation):
        inference.validate_n912_pairing(
            train_456=train_456,
            train_912=train_456[:2],
            test_456=[],
            test_912=[],
        )
    test = [inference.FrozenItemReference(item_id="t0", label=0, anchor_index=0)]
    with pytest.raises(inference.N912ContractViolation):
        inference.validate_n912_pairing(
            train_456=train_456,
            train_912=train_456,
            test_456=test,
            test_912=[inference.FrozenItemReference(item_id="t1", label=0, anchor_index=0)],
        )


def test_n912_minus_n456_is_a_paired_difference():
    assert inference.n912_minus_n456([2.0, 4.0], [1.0, 1.0]) == (1.0, 3.0)
    with pytest.raises(inference.BootstrapContractViolation):
        inference.n912_minus_n456([1.0], [1.0, 2.0])
    assert inference.N912_ROBUSTNESS_ROLE == "SECONDARY_ROBUSTNESS"
    assert inference.N912_CANNOT_RESCUE_PRIMARY is True


# ---------------------------------------------------------------------------
# Reliability, subgroup diagnostics and forbidden interfaces
# ---------------------------------------------------------------------------


def test_reliability_is_descriptive_equal_width_ten_bins():
    table = inference.equal_width_reliability_10_bins([0.05, 0.95], [0, 1])
    assert len(table) == inference.RELIABILITY_BIN_COUNT == 10
    assert table[0]["count"] == 1
    assert table[0]["mean_prediction"] == pytest.approx(0.05, abs=TOL)
    assert table[0]["mean_label"] == 0.0
    assert table[9]["count"] == 1
    assert table[1]["count"] == 0
    assert table[1]["mean_prediction"] is None
    assert table[1]["mean_label"] is None
    assert table[0]["lower"] == 0.0
    assert table[0]["upper"] == 0.1
    with pytest.raises(inference.BootstrapContractViolation):
        inference.equal_width_reliability_10_bins([0.5], [0, 1])
    with pytest.raises(inference.BootstrapContractViolation):
        inference.equal_width_reliability_10_bins([1.5], [0])


def test_reliability_boundary_prediction_lands_in_the_last_bin():
    table = inference.equal_width_reliability_10_bins([1.0], [1])
    assert table[9]["count"] == 1


def test_split_type_diagnostic_is_descriptive_secondary():
    rows = [
        make_row("i0", HELLA, "act", 1, 0.2, 0.8, cluster_id="c0"),
        make_row("i1", HELLA, "act", 0, 0.4, 0.6, cluster_id="c1"),
    ]
    report = inference.split_type_diagnostic(
        rows, split_type_by_item={"i0": "indomain", "i1": "zeroshot"}
    )
    assert report["role"] == inference.SPLIT_TYPE_DIAGNOSTIC_ROLE == "DESCRIPTIVE_SECONDARY"
    assert report["is_independent_population"] is False
    assert report["primary_population_count"] == 3
    assert report["subgroups"]["indomain"]["count"] == 1
    assert report["subgroups"]["zeroshot"]["count"] == 1
    assert inference.SPLIT_TYPE_VALUES == ("indomain", "zeroshot")


def test_no_iid_cell_inference_interfaces_are_exposed():
    for name in ("t_test_over_units", "random_effects_meta_analysis", "naive_cell_standard_error"):
        assert not hasattr(inference, name)


def test_primary_population_registry_stays_exactly_three():
    assert len(inference.PRIMARY_POPULATIONS) == 3
    assert set(inference.PRIMARY_POPULATIONS) == {MMLU, HELLA, MED}
    assert len(inference.PRIMARY_MODELS) == 4
    assert inference.PRIMARY_UNIT_COUNT == 4 * 3 * 2


# ---------------------------------------------------------------------------
# Analysis artifact skeleton and determinism
# ---------------------------------------------------------------------------


def synthetic_artifact():
    return inference.build_analysis_artifact_skeleton(
        population_fingerprints={MMLU: "fp-mmlu"},
        calibration_fingerprints={"I-isotonic": "fp-iso"},
        model_identities={inference.PRIMARY_MODELS[0]: "rev-1"},
        measurement_provenance={"protocol": "synthetic"},
        full_fit_coverage={"m-1,r4-mmlu-57-subject,P-low,OVR": inference.AVAILABLE},
        unit_estimates={("m-1", MMLU, "CAT->OVR", "P-low"): {"Delta_deploy": 0.1}},
        panel_estimates={"Delta_deploy": 0.1},
        test_bootstrap_provenance={"protocol_id": inference.TEST_BOOTSTRAP_PROTOCOL_ID},
        train_refit_provenance={"protocol_id": inference.TRAIN_REFIT_PROTOCOL_ID},
        multiplicity_families={"primary": 12},
        n912_robustness={"role": inference.N912_ROBUSTNESS_ROLE},
        secondary_diagnostics={"reliability": "descriptive"},
        incompleteness=[],
    )


def test_analysis_artifact_skeleton_records_the_frozen_identities():
    payload = synthetic_artifact()
    assert payload["artifact_type"] == "r4-inference-analysis"
    assert payload["freeze_fingerprint"] == inference.R4_INFERENCE_FREEZE_FINGERPRINT
    assert payload["candidate_fingerprint"] == inference.CANDIDATE_FINGERPRINT
    assert payload["fingerprint_version"] == inference.FINGERPRINT_VERSION
    assert payload["incompleteness"] == []
    assert "m-1|r4-mmlu-57-subject|CAT->OVR|P-low" in payload["unit_estimates"]
    assert payload["artifact_fingerprint"] == fingerprint(
        {key: value for key, value in payload.items() if key != "artifact_fingerprint"}
    )


def test_analysis_artifact_serialization_is_deterministic():
    first = synthetic_artifact()
    second = synthetic_artifact()
    assert inference.canonical_state_json(first) == inference.canonical_state_json(second)
    assert inference.state_fingerprint(first) == inference.state_fingerprint(second)
    assert first["artifact_fingerprint"] == second["artifact_fingerprint"]


# ---------------------------------------------------------------------------
# Source-level guards
# ---------------------------------------------------------------------------


def test_implementation_is_stdlib_only_and_deterministic():
    source = MODULE_PATH.read_text(encoding="utf-8")
    docstring_end = source.index('"""', source.index('"""') + 3) + 3
    body = source[docstring_end:]
    for forbidden in ("import random", "import secrets", "import time", "import numpy",
                      "import scipy", "import torch", "import transformers"):
        assert forbidden not in source
    assert "hash(" not in source
    for token in ("nextafter(", "clip(", "np.clip", "random.Random", "secrets.", "time.time"):
        assert token not in body
    assert "probvenance.fingerprint" in source


def test_core_calibration_module_has_no_scipy_or_numpy_import():
    source = CORE_CALIBRATION.read_text(encoding="utf-8")
    for forbidden in ("import scipy", "import numpy", "import torch", "import transformers"):
        assert forbidden not in source


def test_no_outcome_loading_interfaces_are_exposed():
    source = MODULE_PATH.read_text(encoding="utf-8")
    for forbidden in ("snapshot_download", "from_pretrained", "AutoModel", "AutoTokenizer",
                      "torch.cuda", "glob.glob", "rglob"):
        assert forbidden not in source


def test_module_never_imports_the_standalone_calibration_families():
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "r4_calibration_families" not in source
    assert "import scipy" not in source


def test_frozen_authority_files_are_untouched_by_this_module():
    """The infrastructure module must not rewrite any frozen artifact."""
    for path in (FREEZE_JSON, FREEZE_MD, R3_DESIGN_JSON, CALIBRATION_CANDIDATE_JSON):
        assert path.exists()
    freeze = _load(FREEZE_JSON)
    assert freeze["status"] == "FROZEN"
    assert "formal R4 bootstrap execution" in freeze["freeze_scope"]["not_frozen"]


def test_estimand_names_are_never_collapsed():
    assert inference.ESTIMANDS == ("Delta_deploy", "Delta_transport", "Delta_native")
    assert inference.PRIMARY_FAMILY_ESTIMANDS == ("Delta_deploy", "Delta_transport")
    assert "Delta_native" not in inference.PRIMARY_FAMILY_ESTIMANDS
    assert len(set(inference.ESTIMANDS)) == 3
    assert len(list(itertools.combinations(inference.ESTIMANDS, 2))) == 3
