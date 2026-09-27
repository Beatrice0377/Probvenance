"""Offline tests for the R2B stability analysis (bootstraps + decomposition).

No model, no GPU, no network. These tests lock the deterministic percentile
rule, the paired resampling (same item position carries Y/S_A/S_B together),
the paired train-refit resampling (same multiset for both calibrators), the
fail-closed solver behaviour, the observed-range loss decomposition, and the
analysis-artifact determinism.
"""

from __future__ import annotations

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


r2b_plan = _load("r2b_plan")
r2b_provenance = _load("r2b_provenance")
r2b_stability = _load("r2b_stability")
analysis = r2b_stability.analysis
_integrity = analysis._integrity
PairedPoint = analysis.PairedPoint


def _calibrator(slope: float, intercept: float, measurement: str = "m") -> Any:
    return analysis.PilotFittedCalibrator(
        source_measurement=_integrity.MeasurementProtocolIdentity(measurement, 1),
        target_id=analysis.FIXED_DECISION_TARGET_ID,
        target_version=analysis.FIXED_DECISION_TARGET_VERSION,
        input_score_id=analysis.FIXED_DECISION_INPUT_SCORE_ID,
        input_score_version=analysis.FIXED_DECISION_INPUT_SCORE_VERSION,
        method_id=analysis.RESEARCH_LOGISTIC_METHOD_ID,
        method_version=analysis.RESEARCH_LOGISTIC_METHOD_VERSION,
        l2_strength=analysis.PILOT_L2_STRENGTH,
        plan_fingerprint="fp",
        training_item_ids=(),
        slope=slope,
        intercept=intercept,
    )


def _points(pairs: list[tuple[float, float, float]]) -> tuple[Any, ...]:
    return tuple(
        PairedPoint(item_id=f"i{index:03d}", y=y, score_a=sa, score_b=sb)
        for index, (sa, sb, y) in enumerate(pairs)
    )


def test_nearest_rank_percentile_v1() -> None:
    values = [1.0, 2.0, 3.0, 4.0]
    assert r2b_stability.nearest_rank_percentile(values, 25.0) == 1.0
    assert r2b_stability.nearest_rank_percentile(values, 50.0) == 2.0
    assert r2b_stability.nearest_rank_percentile(values, 75.0) == 3.0
    assert r2b_stability.nearest_rank_percentile(values, 100.0) == 4.0


def test_paired_test_bootstrap_is_deterministic_and_matches_point_estimate() -> None:
    points = _points([(0.2, 0.5, 1.0), (0.8, 0.4, 0.0), (0.6, 0.9, 1.0), (0.3, 0.2, 0.0)])
    g_a = _calibrator(1.0, 0.0, "cat")
    g_b = _calibrator(0.5, 0.25, "ovr")
    first = r2b_stability.paired_test_bootstrap(points, g_a, g_b, replicates=200)
    second = r2b_stability.paired_test_bootstrap(points, g_a, g_b, replicates=200)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    matrix = analysis.brier_matrix(points, g_a, g_b)
    assert first["delta_cat_to_ovr"]["point_estimate"] == matrix["delta_a_to_b"]
    assert first["delta_ovr_to_cat"]["point_estimate"] == matrix["delta_b_to_a"]
    for key in ("delta_cat_to_ovr", "delta_ovr_to_cat"):
        interval = first[key]["interval"]
        assert interval["p2_5"] <= interval["median"] <= interval["p97_5"]


def test_paired_test_bootstrap_uses_the_paired_design() -> None:
    # S_A == S_B for every item, so the two calibrators are the same object and
    # every paired difference is zero regardless of how items are resampled.
    points = _points([(0.3, 0.3, 1.0), (0.3, 0.3, 0.0), (0.3, 0.3, 1.0), (0.3, 0.3, 0.0)])
    g = _calibrator(1.0, 0.0)
    result = r2b_stability.paired_test_bootstrap(points, g, g, replicates=100)
    assert result["delta_cat_to_ovr"]["point_estimate"] == 0.0
    assert result["delta_ovr_to_cat"]["point_estimate"] == 0.0
    assert result["delta_cat_to_ovr"]["interval"]["p97_5"] == 0.0
    assert result["delta_ovr_to_cat"]["interval"]["p97_5"] == 0.0


class _PlanStub:
    def __init__(self) -> None:
        self.measurement_a = _integrity.MeasurementProtocolIdentity("cat", 1)
        self.measurement_b = _integrity.MeasurementProtocolIdentity("ovr", 1)
        self.fingerprint = "stub-plan-fingerprint"


def test_train_refit_bootstrap_uses_one_paired_multiset() -> None:
    # S_A == S_B: the same sampled multiset must refit identical calibrators.
    train = _points([(0.2, 0.2, 1.0), (0.7, 0.7, 0.0), (0.5, 0.5, 1.0), (0.9, 0.9, 0.0)])
    test = _points([(0.4, 0.4, 1.0), (0.6, 0.6, 0.0)])
    result = r2b_stability.train_refit_bootstrap(train, test, plan=_PlanStub(), replicates=50)
    assert result["failed_refits"] == 0
    assert result["delta_cat_to_ovr"]["p2_5"] == 0.0
    assert result["delta_cat_to_ovr"]["p97_5"] == 0.0
    assert result["calibrator_a"]["slope"]["median"] == result["calibrator_b"]["slope"]["median"]
    assert (
        result["calibrator_a"]["intercept"]["median"]
        == result["calibrator_b"]["intercept"]["median"]
    )


def test_train_refit_bootstrap_is_deterministic() -> None:
    train = _points([(0.2, 0.5, 1.0), (0.7, 0.4, 0.0), (0.5, 0.9, 1.0), (0.9, 0.2, 0.0)])
    test = _points([(0.4, 0.6, 1.0), (0.6, 0.3, 0.0)])
    plan = _PlanStub()
    first = r2b_stability.train_refit_bootstrap(train, test, plan=plan, replicates=50)
    second = r2b_stability.train_refit_bootstrap(train, test, plan=plan, replicates=50)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_train_refit_bootstrap_fails_closed_on_solver_failure(monkeypatch: Any) -> None:
    train = _points([(0.2, 0.5, 1.0), (0.7, 0.4, 0.0)])
    test = _points([(0.4, 0.6, 1.0)])
    calls = {"n": 0}
    original = analysis.fit_pilot_calibrator

    def flaky(*args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 3:
            raise ValueError("simulated solver failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(analysis, "fit_pilot_calibrator", flaky)
    try:
        r2b_stability.train_refit_bootstrap(train, test, plan=_PlanStub(), replicates=5)
    except ValueError as exc:
        assert "replicate" in str(exc)
        assert "simulated solver failure" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("a failed refit was silently dropped")


def test_observed_range_loss_decomposition_is_asymmetric_and_adds_up() -> None:
    # A train spans [0, 1]; B train is narrow [0.4, 0.6]. B test stays inside A's
    # range (0% outside); A test escapes B's narrow range.
    train = _points([(0.0, 0.4, 1.0), (1.0, 0.6, 0.0), (0.5, 0.5, 1.0)])
    test = _points([(0.2, 0.5, 1.0), (0.8, 0.45, 0.0), (0.3, 0.55, 1.0), (0.7, 0.5, 0.0)])
    g_a = _calibrator(1.0, 0.0, "cat")
    g_b = _calibrator(0.5, 0.25, "ovr")
    result = r2b_stability.observed_range_loss_decomposition(train, test, g_a, g_b)
    assert result["cat_to_ovr"]["fraction_outside_range"] == 0.0
    assert result["ovr_to_cat"]["fraction_outside_range"] == 1.0
    for entry in result.values():
        summed = entry["in_range_contribution"] + entry["outside_range_contribution"]
        assert abs(summed - entry["overall_transport_delta"]) < 1e-9


def _synthetic_run() -> tuple[Any, Any, Any, Any, Any, Any, Any]:
    payload = r2b_plan.load_case_set()
    plan = r2b_plan.build_plan(
        payload,
        model_id="Qwen/Qwen3.5-2B",
        model_revision="15852e8c16360a2fea060d615a32b45270f8a8fc",
    )
    from probvenance.fingerprint import fingerprint

    cat_records: list[dict[str, Any]] = []
    ovr_records: list[dict[str, Any]] = []
    outcomes_a: list[Any] = []
    outcomes_b: list[Any] = []
    for item in plan.items:
        digest = int(fingerprint({"item": item.item_id}), 16)
        score_a = round((digest % 997) / 996.0, 6)
        score_b = round(((digest // 997) % 991) / 990.0, 6)
        winner_a = item.anchor_value if item.anchor_correct else "billing"
        winner_b = item.anchor_value if (digest % 2 == 0) else "shipping"
        cat_record = {
            "item_id": item.item_id,
            "anchor_score": score_a,
            "winner": winner_a,
        }
        ovr_record = {
            "item_id": item.item_id,
            "anchor_score": score_b,
            "winner": winner_b,
            "candidate_score_sum": 1.0,
            "candidates": [{"candidate": "billing", "probability_true": score_b}],
        }
        cat_records.append(cat_record)
        ovr_records.append(ovr_record)
        outcomes_a.append(r2b_stability._load_sibling("measurements").cat_outcome(cat_record))
        outcomes_b.append(r2b_stability._load_sibling("measurements").ovr_outcome(ovr_record))
    dataset = _integrity.PairedFixedDecisionDataset.create(
        plan, tuple(outcomes_a), tuple(outcomes_b)
    )
    provenance = r2b_provenance.build_r2b_run_provenance(
        source_case_set_version=r2b_plan.R2B_CASE_SET_VERSION,
        source_case_set_fingerprint=r2b_plan.case_set_fingerprint(payload),
        plan=plan,
        git_commit="b" * 40,
        git_worktree_clean=True,
    )
    stratum_by_item = {c.item_id: c.stratum for c in r2b_plan.r2b_cases(payload)}
    return (
        plan,
        dataset,
        stratum_by_item,
        provenance,
        cat_records,
        ovr_records,
        (outcomes_a, outcomes_b),
    )


def test_analysis_artifact_schema_and_determinism() -> None:
    plan, dataset, stratum_by_item, provenance, cat_records, ovr_records, outcomes = (
        _synthetic_run()
    )
    outcomes_a, outcomes_b = outcomes
    kwargs = dict(
        plan=plan,
        dataset=dataset,
        stratum_by_item=stratum_by_item,
        case_set_version=r2b_plan.R2B_CASE_SET_VERSION,
        case_set_fingerprint=r2b_plan.case_set_fingerprint(r2b_plan.load_case_set()),
        run_provenance=provenance,
        cat_records=cat_records,
        ovr_records=ovr_records,
        outcomes_a=outcomes_a,
        outcomes_b=outcomes_b,
        test_bootstrap_replicates=100,
        train_refit_replicates=50,
    )
    first = r2b_stability.build_r2b_analysis_artifact(**kwargs)
    second = r2b_stability.build_r2b_analysis_artifact(**kwargs)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    for key in (
        "brier_matrix",
        "raw_relative_brier_changes",
        "logloss_matrix",
        "observed_range_diagnostics",
        "observed_range_loss_decomposition",
        "paired_test_bootstrap",
        "train_refit_bootstrap",
        "strata_summary",
        "winner_diagnostics",
        "ovr_non_simplex_diagnostics",
        "numerical_kernel",
        "r2b_run_provenance_fingerprint",
    ):
        assert key in first
    completeness = first["completeness"]
    assert completeness["planned_n"] == 150
    assert completeness["paired_scored_train_n"] == 90
    assert completeness["paired_scored_test_n"] == 60
    assert first["paired_test_bootstrap"]["replicates"] == 100
    assert first["train_refit_bootstrap"]["replicates"] == 50


def test_analyze_raw_artifact_reproduces_the_committed_analysis() -> None:
    """Regenerating from the frozen raw artifact must reproduce the analysis artifact.

    This locks the analyze-from-raw path (its raw-artifact key names and its
    fail-closed lineage checks). It skips before the empirical R2B run exists,
    because no raw artifact is committed until then.
    """
    raw_path = HARNESS_DIR / "results" / "r2b-stability-qwen35-2b-v1.json"
    analysis_path = HARNESS_DIR / "results" / "r2b-stability-qwen35-2b-v1-analysis.json"
    if not raw_path.is_file() or not analysis_path.is_file():
        pytest.skip("R2B raw/analysis artifacts are not committed yet")
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    regenerated = r2b_stability.analyze_r2b_raw_artifact(raw)
    committed = json.loads(analysis_path.read_text(encoding="utf-8"))
    assert json.dumps(regenerated, sort_keys=True) == json.dumps(committed, sort_keys=True)
