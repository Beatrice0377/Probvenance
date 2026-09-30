"""Synthetic-only engineering tests for the R4 target-label-free predictor.

These tests exercise ``experiments/calibration_transport/r4_predictor.py`` with
hand-written synthetic score vectors, synthetic rows and tiny synthetic draws.
They never read a study dataset, never load a model or tokenizer, never touch a
GPU, and never compute a real R4 predictor or transport outcome.

Formal R4 predictor validation remains unauthorized: every bootstrap here uses
either a tiny replicate count or an explicitly synthetic fixture.
"""

from __future__ import annotations

import ast
import importlib.util
import inspect
import itertools
import json
import math
import re
import sys
from fractions import Fraction
from itertools import pairwise
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TRANSPORT_DIR = REPO_ROOT / "experiments" / "calibration_transport"
INFERENCE_PATH = TRANSPORT_DIR / "r4_inference.py"
MODULE_PATH = TRANSPORT_DIR / "r4_predictor.py"
FREEZE_JSON = TRANSPORT_DIR / "R4_PREDICTOR_FREEZE.json"
FREEZE_MD = TRANSPORT_DIR / "R4_PREDICTOR_FREEZE.md"
CANDIDATE_JSON = TRANSPORT_DIR / "R4_PREDICTOR_SEMANTIC_CANDIDATE.json"

_inference_spec = importlib.util.spec_from_file_location("r4_inference", INFERENCE_PATH)
inference = importlib.util.module_from_spec(_inference_spec)
sys.modules["r4_inference"] = inference
_inference_spec.loader.exec_module(inference)

_predictor_spec = importlib.util.spec_from_file_location("r4_predictor", MODULE_PATH)
predictor = importlib.util.module_from_spec(_predictor_spec)
sys.modules["r4_predictor"] = predictor
_predictor_spec.loader.exec_module(predictor)

from probvenance.fingerprint import fingerprint  # noqa: E402

TOL = 1e-12
W1_TOL = 1e-12

HELLA = inference.HELLASWAG_POPULATION_ID
MED = inference.MEDMCQA_POPULATION_ID
MMLU = inference.MMLU_POPULATION_ID

HELLA_MODE = "activity-stratified-source_id-cluster"
MED_MODE = "subject_name-stratified-row"

PREDICTOR_SOURCE = MODULE_PATH.read_text(encoding="utf-8")

FORBIDDEN_FEATURE_PATTERN = re.compile(
    r"\bclip\(|\bnextafter\(|np\.clip|random\.Random|numpy\.random|"
    r"secrets\.|time\.time|hash\("
)

FORBIDDEN_FEATURE_VOCABULARY = (
    "ground_truth",
    "correctness",
    "brier",
    "logloss",
    "delta_transport",
    "delta_deploy",
    "calibrator",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _med_metadata(
    *,
    test_count: int = 4,
    train_count: int = 4,
    population_fingerprint: str = "med-fingerprint",
) -> object:
    return inference.PopulationMetadata(
        population_id=MED,
        population_fingerprint=population_fingerprint,
        stratum_field="subject_name",
        group_field=None,
        test_bootstrap_protocol_id=(
            "r4-medmcqa-subject-stratified-paired-test-bootstrap"
        ),
        test_bootstrap_protocol_version=1,
        test_bootstrap_mode=MED_MODE,
        estimand_weighting="row-weighted-mean",
        test_count=test_count,
        train_count=train_count,
    )


def _hella_metadata(
    *,
    test_count: int = 6,
    train_count: int = 6,
    population_fingerprint: str = "hella-fingerprint",
) -> object:
    return inference.PopulationMetadata(
        population_id=HELLA,
        population_fingerprint=population_fingerprint,
        stratum_field="activity_label",
        group_field="source_id",
        test_bootstrap_protocol_id=(
            "r4-hellaswag-activity-stratified-source-cluster-test-bootstrap"
        ),
        test_bootstrap_protocol_version=1,
        test_bootstrap_mode=HELLA_MODE,
        estimand_weighting="row-weighted-mean",
        test_count=test_count,
        train_count=train_count,
    )


def _row(
    item_id: str,
    *,
    population_id: str,
    stratum: str,
    cat: float,
    ovr: float,
    cluster_id: str | None = None,
) -> object:
    return inference.R4InferenceRow(
        item_id=item_id,
        population_id=population_id,
        stratum=stratum,
        label=0,
        cat_score=cat,
        ovr_score=ovr,
        cluster_id=cluster_id,
        anchor_index=0,
    )


def _med_rows() -> tuple:
    return (
        _row("m-1", population_id=MED, stratum="s1", cat=0.1, ovr=0.9),
        _row("m-2", population_id=MED, stratum="s1", cat=0.2, ovr=0.8),
        _row("m-3", population_id=MED, stratum="s2", cat=0.3, ovr=0.7),
        _row("m-4", population_id=MED, stratum="s2", cat=0.4, ovr=0.6),
    )


def _hella_rows() -> tuple:
    return (
        _row("h-1", population_id=HELLA, stratum="a1", cat=0.1, ovr=0.9, cluster_id="c1"),
        _row("h-2", population_id=HELLA, stratum="a1", cat=0.2, ovr=0.8, cluster_id="c1"),
        _row("h-3", population_id=HELLA, stratum="a1", cat=0.3, ovr=0.7, cluster_id="c2"),
        _row("h-4", population_id=HELLA, stratum="a2", cat=0.4, ovr=0.6, cluster_id="c3"),
        _row("h-5", population_id=HELLA, stratum="a2", cat=0.5, ovr=0.5, cluster_id="c4"),
        _row("h-6", population_id=HELLA, stratum="a2", cat=0.6, ovr=0.4, cluster_id="c4"),
    )


def _med_draw(replicate_index: int, rows: tuple | None = None) -> object:
    return inference.build_test_draw(
        rows if rows is not None else _med_rows(),
        _med_metadata(),
        replicate_index,
    )


def _hella_draw(replicate_index: int, rows: tuple | None = None) -> object:
    return inference.build_test_draw(
        rows if rows is not None else _hella_rows(),
        _hella_metadata(),
        replicate_index,
    )


def _reference_w1_quantile(left, right) -> float:
    """Independent exact W1 path: quantile-coupling integral on [0, 1]."""
    x = sorted(float(value) for value in left)
    y = sorted(float(value) for value in right)
    n, m = len(x), len(y)
    breaks = {Fraction(k, n) for k in range(1, n)}
    breaks |= {Fraction(k, m) for k in range(1, m)}
    points = [Fraction(0), *sorted(breaks), Fraction(1)]
    total = 0.0
    for lower, upper in pairwise(points):
        if upper <= lower:
            continue
        midpoint = (lower + upper) / 2
        total += float(upper - lower) * abs(
            x[_ceil_rank(midpoint, n) - 1] - y[_ceil_rank(midpoint, m) - 1]
        )
    return total


def _ceil_rank(fraction: Fraction, n: int) -> int:
    value = fraction * n
    return min(max(-(-value.numerator // value.denominator), 1), n)


def _synthetic_validation_rows() -> tuple:
    """A complete synthetic 16-unit primary validation table."""
    units = predictor.primary_validation_units()
    rows = []
    for index, unit in enumerate(units):
        x_range = (index + 1) / 20.0
        rows.append(
            predictor.PredictorValidationRow(
                unit=unit,
                x_range=x_range,
                x_wasserstein1=1.0 - x_range,
                y_transport_core=x_range,
                y_deploy_core=0.5 * x_range,
            )
        )
    return tuple(rows)


def _measurement(unit, *, y_transport, y_deploy, rows, source) -> object:
    def provider(draw):
        return y_transport, y_deploy

    return predictor.PredictorUnitMeasurement(
        unit=unit,
        source_train_scores=source,
        target_test_rows=rows,
        y_provider=provider,
    )


def _panel_measurements(*, vary_outcomes: bool = False) -> tuple:
    """Build 16 synthetic measurements with per-unit sources.

    ``vary_outcomes=False`` keeps a constant synthetic outcome vector, which
    makes every replicate rank correlation undefined (used by the fail-closed
    tests). ``vary_outcomes=True`` varies X and Y across units so that the
    synthetic panel yields a defined correlation.
    """
    units = predictor.primary_validation_units()
    measurements = []
    for index, unit in enumerate(units):
        rows = _med_rows() if unit.population_id == MED else _hella_rows()
        source = tuple(0.05 + 0.01 * index + 0.2 * step for step in range(4))
        if vary_outcomes:
            y_transport = 0.1 + 0.01 * index
            y_deploy = 0.2 + 0.01 * index
        else:
            y_transport = 0.1
            y_deploy = 0.1
        measurements.append(
            _measurement(
                unit,
                y_transport=y_transport,
                y_deploy=y_deploy,
                rows=rows,
                source=source,
            )
        )
    return tuple(measurements)


# ---------------------------------------------------------------------------
# Frozen identity continuity
# ---------------------------------------------------------------------------


def test_frozen_fingerprints_match_the_freeze_artifact():
    freeze = _load(FREEZE_JSON)
    assert freeze["status"] == predictor.PREDICTOR_FREEZE_STATUS
    assert freeze["artifact_type"] == predictor.PREDICTOR_FREEZE_ARTIFACT_TYPE
    assert freeze["freeze_fingerprint"] == predictor.PREDICTOR_FREEZE_FINGERPRINT
    assert (
        freeze["candidate_artifact_identity"]["candidate_fingerprint"]
        == predictor.PREDICTOR_CANDIDATE_FINGERPRINT
    )
    payload = {k: v for k, v in freeze.items() if k != "freeze_fingerprint"}
    assert fingerprint(payload) == predictor.PREDICTOR_FREEZE_FINGERPRINT


def test_inference_freeze_fingerprint_continuity():
    assert predictor.R4_INFERENCE_FREEZE_FINGERPRINT == (
        "dcbb7ac9e931145fdee86ab984de1249c1b86ca36ee735b70dafc8cabc06c141"
    )
    inference_freeze = _load(TRANSPORT_DIR / "R4_INFERENCE_MULTIPLICITY_FREEZE.json")
    assert inference_freeze["freeze_fingerprint"] == (
        predictor.R4_INFERENCE_FREEZE_FINGERPRINT
    )


def test_freeze_document_records_the_frozen_identities():
    text = FREEZE_MD.read_text(encoding="utf-8")
    for token in (
        predictor.PREDICTOR_FREEZE_FINGERPRINT,
        predictor.PREDICTOR_CANDIDATE_FINGERPRINT,
        predictor.PRIMARY_PREDICTOR_ID,
        predictor.SECONDARY_PREDICTOR_ID,
        predictor.PRIMARY_OUTCOME_ID,
        predictor.SECONDARY_OUTCOME_ID,
        predictor.VALIDATION_PROTOCOL_ID,
        predictor.SPEARMAN_UNDEFINED_CONSTANT_INPUT,
        "The predictor validation bootstrap quantifies",
        "It does NOT resample models, populations, or directions.",
    ):
        assert token in text


def test_candidate_semantic_payload_is_unchanged_by_the_freeze():
    candidate = _load(CANDIDATE_JSON)
    freeze = _load(FREEZE_JSON)
    identity = {
        "artifact_type",
        "artifact_version",
        "status",
        "candidate_fingerprint",
        "fingerprint_version",
    }
    candidate_body = {k: v for k, v in candidate.items() if k not in identity}
    frozen_body = freeze["frozen_semantic_payload"]
    assert candidate_body == frozen_body
    audit = freeze["creation_provenance"]["semantic_equivalence_audit"]
    assert audit["result"] == "EXACT_SEMANTIC_EQUIVALENCE"
    assert audit["differing_keys"] == []


# ---------------------------------------------------------------------------
# Label firewall
# ---------------------------------------------------------------------------


def test_feature_signatures_take_only_raw_scores():
    for function in (
        predictor.range_exceedance_warning,
        predictor.wasserstein1_warning,
    ):
        parameters = list(inspect.signature(function).parameters)
        assert parameters == ["source_train_scores", "target_test_scores"]
        for forbidden in ("label", "y", "ground_truth", "calibrator", "risk", "delta"):
            assert all(forbidden not in name.lower() for name in parameters)


def test_source_scan_has_no_sampling_or_clipping_tokens():
    assert FORBIDDEN_FEATURE_PATTERN.search(PREDICTOR_SOURCE) is None


def test_feature_path_has_no_label_or_outcome_vocabulary():
    """Only the outcome-aggregation half may name outcomes; X code must not."""
    names = {
        "validate_predictor_score",
        "validate_predictor_scores",
        "source_quantile_levels",
        "source_thresholds",
        "range_exceedance_warning",
        "exact_empirical_wasserstein1",
        "wasserstein1_warning",
        "_count_at_most",
    }
    chunks: list[str] = []
    for node in ast.walk(ast.parse(PREDICTOR_SOURCE)):
        if isinstance(node, ast.FunctionDef) and node.name in names:
            for statement in node.body:
                if (
                    isinstance(statement, ast.Expr)
                    and isinstance(statement.value, ast.Constant)
                    and isinstance(statement.value.value, str)
                ):
                    continue
                chunks.append(ast.get_source_segment(PREDICTOR_SOURCE, statement) or "")
    code = "\n".join(chunks).lower()
    assert code
    for token in FORBIDDEN_FEATURE_VOCABULARY:
        assert token not in code


# ---------------------------------------------------------------------------
# Score validation
# ---------------------------------------------------------------------------


def test_exact_endpoint_scores_are_legal():
    assert predictor.validate_predictor_score(0) == 0.0
    assert predictor.validate_predictor_score(1) == 1.0
    assert predictor.validate_predictor_scores([0.0, 1.0]) == (0.0, 1.0)


@pytest.mark.parametrize(
    "bad",
    [float("nan"), float("inf"), float("-inf"), -0.5, 1.5],
)
def test_invalid_scores_raise_the_invalid_state(bad):
    with pytest.raises(predictor.PredictorInputInvalid) as excinfo:
        predictor.validate_predictor_score(bad)
    assert excinfo.value.state == predictor.PREDICTOR_INPUT_INVALID


def test_invalid_scores_are_never_repaired():
    with pytest.raises(predictor.PredictorInputInvalid):
        predictor.range_exceedance_warning([1.5, 0.2], [0.5])
    with pytest.raises(predictor.PredictorInputInvalid):
        predictor.wasserstein1_warning([0.1], [float("nan")])


def test_empty_score_vector_is_rejected():
    with pytest.raises(predictor.PredictorInputInvalid):
        predictor.validate_predictor_scores([])


# ---------------------------------------------------------------------------
# Source quantiles
# ---------------------------------------------------------------------------


def test_source_quantile_ranks_at_n456_are_frozen():
    levels = predictor.source_quantile_levels()
    assert levels["lower_rank_at_n456"] == 12
    assert levels["upper_rank_at_n456"] == 445
    assert inference.percentile_rank(Fraction(1, 40), 456) == 12
    assert inference.percentile_rank(Fraction(39, 40), 456) == 445


def test_source_thresholds_use_the_nearest_rank_rule():
    scores = [index / 456 for index in range(1, 457)]
    q_low, q_high = predictor.source_thresholds(scores)
    ordered = sorted(scores)
    assert q_low == ordered[11]
    assert q_high == ordered[444]


# ---------------------------------------------------------------------------
# X_range
# ---------------------------------------------------------------------------


def test_range_boundary_rules():
    source = [0.1, 0.25, 0.5, 0.75, 0.9]
    q_low, q_high = predictor.source_thresholds(source)
    assert (q_low, q_high) == (0.1, 0.9)
    result = predictor.range_exceedance_warning(
        source, [0.05, q_low, 0.5, q_high, 0.95]
    )
    assert result.outside_count == 2
    assert result.fraction_outside == pytest.approx(0.4)
    assert result.q_low == q_low
    assert result.q_high == q_high


def test_range_equality_counts_as_inside():
    source = [0.0, 0.5, 1.0]
    q_low, q_high = predictor.source_thresholds(source)
    result = predictor.range_exceedance_warning(source, [q_low, q_high])
    assert result.outside_count == 0
    assert result.fraction_outside == 0.0


def test_range_is_order_invariant():
    source = [0.1, 0.2, 0.3, 0.4, 0.5]
    target = [0.05, 0.15, 0.55, 0.35, 0.45]
    baseline = predictor.range_exceedance_warning(source, target)
    for permutation in itertools.islice(itertools.permutations(target), 6):
        result = predictor.range_exceedance_warning(source, list(permutation))
        assert result.fraction_outside == baseline.fraction_outside
        assert result.outside_count == baseline.outside_count


def test_range_payload_records_the_frozen_identity():
    result = predictor.range_exceedance_warning([0.2, 0.4, 0.6], [0.1, 0.9])
    payload = result.payload()
    assert payload["predictor_id"] == predictor.PRIMARY_PREDICTOR_ID
    assert payload["predictor_version"] == predictor.PRIMARY_PREDICTOR_VERSION
    assert payload["source_count"] == 3
    assert payload["target_count"] == 2


# ---------------------------------------------------------------------------
# Exact empirical Wasserstein-1
# ---------------------------------------------------------------------------


def test_w1_identical_distributions_is_zero():
    assert predictor.exact_empirical_wasserstein1([0.2, 0.4], [0.4, 0.2]) == 0.0


def test_w1_singletons():
    assert predictor.exact_empirical_wasserstein1([0.0], [1.0]) == 1.0


def test_w1_translation():
    value = predictor.exact_empirical_wasserstein1([0.1, 0.2], [0.2, 0.3])
    assert value == pytest.approx(0.1, abs=W1_TOL)


def test_w1_unequal_sample_counts():
    assert predictor.exact_empirical_wasserstein1([0.0, 0.0], [1.0]) == pytest.approx(1.0)


def test_w1_ties_and_endpoints():
    assert predictor.exact_empirical_wasserstein1([0.0, 0.0], [0.0, 1.0]) == pytest.approx(0.5)
    assert predictor.exact_empirical_wasserstein1([1.0], [1.0]) == 0.0


def test_w1_is_order_invariant():
    left = [0.1, 0.3, 0.7]
    right = [0.2, 0.25, 0.9, 0.95]
    baseline = predictor.exact_empirical_wasserstein1(left, right)
    for permutation in itertools.islice(itertools.permutations(right), 5):
        assert predictor.exact_empirical_wasserstein1(left, list(permutation)) == pytest.approx(
            baseline, abs=W1_TOL
        )


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ([0.0], [1.0]),
        ([0.1, 0.2], [0.2, 0.3]),
        ([0.0, 0.0], [1.0]),
        ([0.0, 0.5, 1.0], [0.25, 0.75]),
        ([0.2, 0.4, 0.6, 0.8], [0.1, 0.15, 0.9]),
        ([0.05, 0.1, 0.9, 0.95], [0.2, 0.3, 0.4, 0.5, 0.6, 0.7]),
        ([0.5, 0.5, 0.5], [0.5, 0.5]),
    ],
)
def test_w1_independent_reference_audit(left, right):
    primary = predictor.exact_empirical_wasserstein1(left, right)
    reference = _reference_w1_quantile(left, right)
    assert abs(primary - reference) <= W1_TOL


# ---------------------------------------------------------------------------
# Spearman
# ---------------------------------------------------------------------------


def test_average_ranks_handles_ties():
    ranks = predictor.average_ranks([1.0, 2.0, 2.0, 3.0])
    assert ranks == (1.0, 2.5, 2.5, 4.0)


def test_spearman_perfect_increasing_and_decreasing():
    assert predictor.spearman_fixed_units([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert predictor.spearman_fixed_units([1, 2, 3, 4], [40, 30, 20, 10]) == pytest.approx(-1.0)


def test_spearman_with_ties_matches_hand_computation():
    value = predictor.spearman_fixed_units([1, 2, 2, 3], [10, 20, 30, 40])
    expected = 4.5 / math.sqrt(4.5 * 5.0)
    assert value == pytest.approx(expected, abs=TOL)


def test_spearman_constant_input_state():
    with pytest.raises(predictor.SpearmanUndefined) as excinfo:
        predictor.spearman_fixed_units([1, 1, 1, 1], [1, 2, 3, 4])
    assert excinfo.value.state == predictor.SPEARMAN_UNDEFINED_CONSTANT_INPUT
    with pytest.raises(predictor.SpearmanUndefined):
        predictor.spearman_fixed_units([1, 2, 3, 4], [5, 5, 5, 5])


def test_spearman_permutation_invariance():
    left = [0.1, 0.4, 0.6, 0.9]
    right = [0.2, 0.3, 0.8, 0.95]
    baseline = predictor.spearman_fixed_units(left, right)
    order = [2, 0, 3, 1]
    assert predictor.spearman_fixed_units(
        [left[index] for index in order], [right[index] for index in order]
    ) == pytest.approx(baseline, abs=TOL)


# ---------------------------------------------------------------------------
# CORE4 outcomes
# ---------------------------------------------------------------------------


def test_core4_aggregates_the_frozen_four():
    values = {
        "P-low": 0.1,
        "P-historical": 0.2,
        "L-low": 0.3,
        "L-historical": 0.4,
    }
    assert predictor.core4_mean_transport_penalty(values) == pytest.approx(0.25)
    assert predictor.core4_mean_deployment_delta(values) == pytest.approx(0.25)


def test_core4_missing_procedure_is_incomplete():
    values = {"P-low": 0.1, "P-historical": 0.2, "L-low": 0.3}
    with pytest.raises(predictor.Core4Incomplete) as excinfo:
        predictor.core4_mean_transport_penalty(values)
    assert excinfo.value.state == predictor.CORE4_UNIT_INCOMPLETE
    assert excinfo.value.missing == ("L-historical",)
    status = predictor.core4_completeness(values)
    assert status["status"] == inference.STATUS_INCOMPLETE


def test_core4_ignores_extra_procedures():
    base = {"P-low": 0.1, "P-historical": 0.2, "L-low": 0.3, "L-historical": 0.4}
    extra = dict(base, **{"I-isotonic": 99.0, "B-beta": -99.0})
    assert predictor.core4_mean_transport_penalty(extra) == predictor.core4_mean_transport_penalty(
        base
    )
    status = predictor.core4_completeness(extra)
    assert status["ignored_extra_procedures"] == ["B-beta", "I-isotonic"]


# ---------------------------------------------------------------------------
# Unit registries
# ---------------------------------------------------------------------------


def test_registry_sizes_and_cartesian_product():
    development = predictor.development_units()
    validation = predictor.primary_validation_units()
    legacy = predictor.legacy_extension_units()
    assert len(development) == predictor.DEVELOPMENT_UNIT_COUNT == 8
    assert len(validation) == predictor.PRIMARY_VALIDATION_UNIT_COUNT == 16
    assert len(legacy) == predictor.LEGACY_EXTENSION_UNIT_COUNT == 8
    expected = {
        (model, population, direction)
        for model, _ in predictor.CURRENT_GENERATION_MODELS
        for population in predictor.VALIDATION_POPULATIONS
        for direction in predictor.DIRECTIONS
    }
    assert {
        (unit.model_id, unit.population_id, unit.direction_id) for unit in validation
    } == expected
    assert {unit.population_id for unit in development} == {MMLU}
    assert len({unit.unit_id for unit in validation}) == 16


def test_unit_id_is_answer_independent_and_deterministic():
    unit = predictor.primary_validation_units()[0]
    again = predictor.predictor_unit_id(
        unit.model_id, unit.population_id, unit.direction_id
    )
    assert again == unit.unit_id
    assert fingerprint(
        {
            "protocol_id": predictor.VALIDATION_PROTOCOL_ID,
            "protocol_version": predictor.VALIDATION_PROTOCOL_VERSION,
            "model_id": unit.model_id,
            "population_id": unit.population_id,
            "direction_id": unit.direction_id,
        }
    ) == unit.unit_id


# ---------------------------------------------------------------------------
# Primary validation table
# ---------------------------------------------------------------------------


def test_primary_validation_table_is_complete():
    audit = predictor.validate_primary_validation_table(_synthetic_validation_rows())
    assert audit["status"] == inference.STATUS_COMPLETE
    assert audit["unit_count"] == 16
    assert audit["population_counts"] == {HELLA: 8, MED: 8}
    assert audit["direction_counts"] == {"CAT->OVR": 8, "OVR->CAT": 8}


def test_primary_statistic_over_the_synthetic_panel():
    value = predictor.primary_statistic(_synthetic_validation_rows())
    assert value == pytest.approx(1.0, abs=TOL)


def test_missing_unit_is_incomplete():
    rows = _synthetic_validation_rows()[:-1]
    with pytest.raises(predictor.PrimaryValidationIncomplete) as excinfo:
        predictor.validate_primary_validation_table(rows)
    assert excinfo.value.state == predictor.PRIMARY_VALIDATION_INCOMPLETE


def test_duplicate_unit_is_incomplete():
    rows = _synthetic_validation_rows()
    with pytest.raises(predictor.PrimaryValidationIncomplete):
        predictor.validate_primary_validation_table((*rows, rows[0]))


def test_incomplete_unit_is_incomplete():
    rows = list(_synthetic_validation_rows())
    rows[3] = predictor.PredictorValidationRow(
        unit=rows[3].unit,
        x_range=None,
        x_wasserstein1=rows[3].x_wasserstein1,
        y_transport_core=rows[3].y_transport_core,
        y_deploy_core=rows[3].y_deploy_core,
    )
    with pytest.raises(predictor.PrimaryValidationIncomplete):
        predictor.validate_primary_validation_table(tuple(rows))


def test_development_unit_cannot_enter_primary_validation():
    development = predictor.development_units()[0]
    with pytest.raises(predictor.PredictorRoleViolation):
        predictor.require_primary_validation_unit(development)


def test_legacy_model_cannot_enter_primary_validation():
    legacy = predictor.legacy_extension_units()[0]
    with pytest.raises(predictor.PredictorRoleViolation):
        predictor.require_primary_validation_unit(legacy)


def test_legacy_extension_units_are_their_own_role():
    for unit in predictor.legacy_extension_units():
        predictor.require_legacy_extension_unit(unit)
    for unit in predictor.development_units():
        predictor.require_development_unit(unit)


# ---------------------------------------------------------------------------
# Secondary statistics and support state
# ---------------------------------------------------------------------------


def test_secondary_statistics_are_reported_separately():
    rows = _synthetic_validation_rows()
    secondary = predictor.secondary_statistics(rows)
    assert secondary["role"] == "SECONDARY"
    assert secondary["can_rescue_primary"] is False
    assert secondary["rho_range_deploy"]["value"] is not None


def test_secondary_cannot_modify_the_primary_state():
    rows = list(_synthetic_validation_rows())
    baseline = predictor.primary_statistic(tuple(rows))
    for index in range(16):
        rows[index] = predictor.PredictorValidationRow(
            unit=rows[index].unit,
            x_range=rows[index].x_range,
            x_wasserstein1=0.0,
            y_transport_core=rows[index].y_transport_core,
            y_deploy_core=-1.0,
        )
    secondary = predictor.secondary_statistics(tuple(rows))
    assert secondary["rho_W1_transport"]["status"] in (
        inference.STATUS_COMPLETE,
        predictor.SPEARMAN_UNDEFINED_CONSTANT_INPUT,
    )
    assert predictor.primary_statistic(tuple(rows)) == pytest.approx(baseline, abs=TOL)


def test_primary_support_rule_states():
    complete = inference.percentile_interval(
        [0.1, 0.2, 0.3],
        lower_tail=Fraction(1, 40),
        upper_tail=Fraction(39, 40),
        point_estimate=0.2,
    )
    assert (
        predictor.primary_support_state(0.2, complete)
        == predictor.PRIMARY_WARNING_SIGNAL_SUPPORTED
    )
    assert (
        predictor.primary_support_state(-0.1, complete)
        == predictor.PRIMARY_WARNING_SIGNAL_NOT_ESTABLISHED
    )
    incomplete = inference.Interval(
        n=0,
        point_estimate=0.2,
        bootstrap_median=None,
        lower=None,
        upper=None,
        tail_rule="1/40/39/40",
        excludes_zero=None,
        status=inference.STATUS_INCOMPLETE,
    )
    assert (
        predictor.primary_support_state(0.2, incomplete)
        == predictor.PRIMARY_WARNING_SIGNAL_INCOMPLETE
    )


# ---------------------------------------------------------------------------
# Shared-draw predictor bootstrap
# ---------------------------------------------------------------------------


def _draws(replicates):
    draws = {}
    for replicate_index in range(replicates):
        draws[(MED, replicate_index)] = _med_draw(replicate_index)
        draws[(HELLA, replicate_index)] = _hella_draw(replicate_index)
    return draws


def test_predictor_bootstrap_reuses_one_shared_draw_per_population():
    replicates = 5
    measurements = _panel_measurements(vary_outcomes=True)
    draws = _draws(replicates)

    seen: dict[tuple[str, int], list[int]] = {}

    rewritten = []
    for index, measurement in enumerate(measurements):

        def provider(draw, unit=measurement.unit, y=0.1 + 0.01 * index):
            seen.setdefault((unit.population_id, draw.replicate_index), []).append(id(draw))
            assert draw is draws[(unit.population_id, draw.replicate_index)]
            return y, y + 0.1

        rewritten.append(
            predictor.PredictorUnitMeasurement(
                unit=measurement.unit,
                source_train_scores=measurement.source_train_scores,
                target_test_rows=measurement.target_test_rows,
                y_provider=provider,
            )
        )
    result = predictor.run_predictor_test_bootstrap(
        measurements=tuple(rewritten), draws=draws, replicates=replicates, point_estimate=0.0
    )
    assert result.status in (inference.STATUS_COMPLETE, inference.STATUS_INCOMPLETE)
    assert len(seen) == 2 * replicates
    for _key, identities in seen.items():
        assert len(set(identities)) == 1


def test_predictor_x_and_y_share_the_same_draw():
    replicates = 3
    measurements = _panel_measurements(vary_outcomes=True)
    draws = _draws(replicates)

    recorded: list[tuple[str, str, int, tuple[float, ...]]] = []

    def make_provider(unit):
        def provider(draw):
            scores = tuple(
                inference.measurement_score(
                    row, inference.target_measurement(unit.direction_id)
                )
                for row in draw.occurrences
            )
            recorded.append(
                (unit.population_id, unit.direction_id, draw.replicate_index, scores)
            )
            return 0.1, 0.2

        return provider

    rewritten = tuple(
        predictor.PredictorUnitMeasurement(
            unit=measurement.unit,
            source_train_scores=measurement.source_train_scores,
            target_test_rows=measurement.target_test_rows,
            y_provider=make_provider(measurement.unit),
        )
        for measurement in measurements
    )
    predictor.run_predictor_test_bootstrap(
        measurements=rewritten, draws=draws, replicates=replicates, point_estimate=0.0
    )
    assert recorded
    for population_id, direction_id, replicate_index, scores in recorded:
        draw = draws[(population_id, replicate_index)]
        expected = tuple(
            inference.measurement_score(row, inference.target_measurement(direction_id))
            for row in draw.occurrences
        )
        assert scores == expected


def test_predictor_bootstrap_only_resamples_test_rows():
    replicates = 4
    measurements = _panel_measurements(vary_outcomes=True)
    draws = _draws(replicates)
    result = predictor.run_predictor_test_bootstrap(
        measurements=measurements, draws=draws, replicates=replicates, point_estimate=0.0
    )
    assert result.planned_replicates == replicates
    for replicate_index in range(replicates):
        hella = draws[(HELLA, replicate_index)]
        assert hella.stratum_order == ("a1", "a2")
        for row in hella.occurrences:
            assert row.population_id == HELLA
        med = draws[(MED, replicate_index)]
        assert med.stratum_order == ("s1", "s2")
        for row in med.occurrences:
            assert row.population_id == MED


def test_hella_cluster_draw_never_splits_a_source_id():
    rows = _hella_rows()
    for replicate_index in range(6):
        draw = _hella_draw(replicate_index, rows)
        counts: dict[str, int] = {}
        for row in draw.occurrences:
            counts[row.cluster_id] = counts.get(row.cluster_id, 0) + 1
        for cluster_id, count in counts.items():
            total = sum(1 for row in rows if row.cluster_id == cluster_id)
            assert count % total == 0


def test_undefined_replicate_fails_closed():
    replicates = 3
    measurements = _panel_measurements()
    draws = _draws(replicates)
    result = predictor.run_predictor_test_bootstrap(
        measurements=measurements, draws=draws, replicates=replicates, point_estimate=0.5
    )
    assert result.undefined_replicates == replicates
    assert result.status == inference.STATUS_INCOMPLETE
    interval = result.interval()
    assert interval.status == inference.STATUS_INCOMPLETE
    assert interval.lower is None and interval.upper is None
    assert result.samples == ()
    payload = result.payload()
    assert payload["undefined_indices"] == [0, 1, 2]


def test_incomplete_outcome_replicate_fails_closed():
    replicates = 2
    draws = _draws(replicates)
    units = predictor.primary_validation_units()
    measurements = tuple(
        predictor.PredictorUnitMeasurement(
            unit=unit,
            source_train_scores=(0.1, 0.2, 0.3, 0.4),
            target_test_rows=_med_rows() if unit.population_id == MED else _hella_rows(),
            y_provider=(lambda draw: (None, None))
            if unit.model_id.startswith("allenai")
            else (lambda draw: (0.1, 0.2)),
        )
        for unit in units
    )
    result = predictor.run_predictor_test_bootstrap(
        measurements=measurements, draws=draws, replicates=replicates, point_estimate=0.0
    )
    assert result.incomplete_replicates == replicates
    assert result.status == inference.STATUS_INCOMPLETE
    assert result.interval().status == inference.STATUS_INCOMPLETE


def test_missing_shared_draw_is_a_contract_violation():
    with pytest.raises(inference.BootstrapContractViolation):
        predictor.run_predictor_test_bootstrap(
            measurements=_panel_measurements(),
            draws={},
            replicates=1,
        )


# ---------------------------------------------------------------------------
# TRAIN stability
# ---------------------------------------------------------------------------


def test_train_stability_x_only_is_complete():
    measurements = _panel_measurements()
    metadata = {MED: _med_metadata(), HELLA: _hella_metadata()}
    rows = {MED: _med_rows(), HELLA: _hella_rows()}
    result = predictor.run_predictor_train_stability(
        measurements=measurements,
        train_rows_by_population=rows,
        metadata_by_population=metadata,
        replicates=3,
    )
    assert result.status == inference.STATUS_COMPLETE
    assert result.role == "SECONDARY_STABILITY_ONLY"
    assert result.failed_replicates == 0


def test_train_stability_y_failure_is_incomplete():
    measurements = _panel_measurements()
    metadata = {MED: _med_metadata(), HELLA: _hella_metadata()}
    rows = {MED: _med_rows(), HELLA: _hella_rows()}
    fixed = {unit.unit_id: 0.1 for unit in predictor.primary_validation_units()}
    fixed.pop(predictor.primary_validation_units()[0].unit_id)
    result = predictor.run_predictor_train_stability(
        measurements=measurements,
        train_rows_by_population=rows,
        metadata_by_population=metadata,
        replicates=2,
        fixed_outcomes=fixed,
    )
    assert result.status == inference.STATUS_INCOMPLETE
    assert result.failed_indices == (0, 1)


# ---------------------------------------------------------------------------
# N912 robustness
# ---------------------------------------------------------------------------


def test_n912_robustness_cannot_rescue_primary():
    comparison = predictor.n912_predictor_difference(0.2, 0.25)
    assert comparison["difference"] == pytest.approx(0.05)
    assert comparison["role"] == predictor.N912_ROBUSTNESS_ROLE
    assert comparison["cannot_rescue_primary"] is True
    assert predictor.N912_CANNOT_RESCUE_PRIMARY is True


# ---------------------------------------------------------------------------
# Synthetic full fixture and artifact
# ---------------------------------------------------------------------------


def test_synthetic_full_fixture_end_to_end():
    rows = _synthetic_validation_rows()
    audit = predictor.validate_primary_validation_table(rows)
    point = predictor.primary_statistic(rows)
    secondary = predictor.secondary_statistics(rows)
    artifact = predictor.build_predictor_validation_artifact_skeleton(
        unit_predictor_values={row.unit.unit_id: row.x_range for row in rows},
        outcome_summaries={row.unit.unit_id: row.y_transport_core for row in rows},
        point_statistics={"rho_primary": point},
        bootstrap_provenance={"replicates": 0, "note": "synthetic"},
    )
    assert audit["unit_count"] == 16
    assert point == pytest.approx(1.0, abs=TOL)
    assert secondary["rho_W1_transport"]["value"] == pytest.approx(-1.0, abs=TOL)
    assert artifact["predictor_freeze_fingerprint"] == predictor.PREDICTOR_FREEZE_FINGERPRINT
    assert artifact["inference_freeze_fingerprint"] == (
        predictor.R4_INFERENCE_FREEZE_FINGERPRINT
    )
    assert "artifact_fingerprint" in artifact


def test_artifact_composite_keys_are_stringified():
    artifact = predictor.build_predictor_validation_artifact_skeleton(
        unit_predictor_values={("m-1", MED, "CAT->OVR"): 0.25},
        outcome_summaries={},
        point_statistics={},
        bootstrap_provenance={},
    )
    assert list(artifact["unit_predictor_values"]) == ["m-1|r4-medmcqa-subject-primary|CAT->OVR"]
    assert json.dumps(artifact, sort_keys=True)


def test_synthetic_20000_replicate_smoke():
    replicates = 20000
    measurements = _panel_measurements(vary_outcomes=True)
    draws = _draws(replicates)
    rows = _synthetic_validation_rows()
    result = predictor.run_predictor_test_bootstrap(
        measurements=measurements,
        draws=draws,
        replicates=replicates,
        point_estimate=predictor.primary_statistic(rows),
    )
    assert result.planned_replicates == replicates
    assert result.status in (inference.STATUS_COMPLETE, inference.STATUS_INCOMPLETE)


def test_determinism_of_the_predictor_state():
    rows = _synthetic_validation_rows()
    payload = {
        "unit_predictor_values": {row.unit.unit_id: row.x_range for row in rows},
        "point_statistics": {"rho_primary": predictor.primary_statistic(rows)},
    }
    first = predictor.predictor_canonical_json(payload)
    second = predictor.predictor_canonical_json(payload)
    assert first == second
    assert predictor.predictor_state_fingerprint(payload) == (
        predictor.predictor_state_fingerprint(payload)
    )
