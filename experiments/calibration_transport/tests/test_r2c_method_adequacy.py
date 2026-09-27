"""Offline tests for the R2C calibration-method adequacy sensitivity.

No model, no GPU, no network. These tests lock the frozen lambda grid and the
two fitted families, the Family L identity-map property, exact endpoint
rejection (no clipping), the fail-closed endpoint policy, artifact determinism,
and the reproduction of the committed R2B current configuration (Family P,
lambda = 1e-2) from the frozen R2B raw evidence.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace
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


analysis = _load("analysis")
r2c = _load("r2c_method_adequacy")

R2B_RAW = HARNESS_DIR / "results" / "r2b-stability-qwen35-2b-v1.json"
R2B_ANALYSIS = HARNESS_DIR / "results" / "r2b-stability-qwen35-2b-v1-analysis.json"


def _fake_plan(fingerprint: str = "planfp") -> Any:
    return SimpleNamespace(fingerprint=fingerprint)


def _raw_stub() -> dict[str, Any]:
    return {
        "source_case_set_version": "x",
        "source_case_set_fingerprint": "csf",
        "plan_fingerprint": "planfp",
        "paired_dataset_fingerprint": "dsf",
        "r2b_run_provenance_fingerprint": "pf",
    }


def _synthetic_points() -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    train = tuple(
        analysis.PairedPoint(f"t{i:02d}", float(i % 2), 0.1 + 0.05 * i, 0.3 + 0.03 * i)
        for i in range(12)
    )
    test = tuple(
        analysis.PairedPoint(f"u{i:02d}", float(i % 2), 0.15 + 0.05 * i, 0.35 + 0.02 * i)
        for i in range(6)
    )
    return train, test


def _build_synthetic() -> dict[str, Any]:
    train, test = _synthetic_points()
    design = r2c.load_design()
    return r2c.build_r2c_analysis_artifact(
        raw=_raw_stub(),
        design=design,
        plan=_fake_plan(),
        train_points=train,
        test_points=test,
        provenance=None,
        test_bootstrap_replicates=5,
        train_refit_replicates=4,
    )


# --- design manifest ---------------------------------------------------------


def test_lambda_grid_is_exactly_frozen() -> None:
    configs = r2c.method_configs()
    assert [c.label for c in configs] == [
        "P:1e-06",
        "P:0.0001",
        "P:0.01",
        "P:0.1",
        "P:1.0",
        "L:1e-06",
        "L:0.0001",
        "L:0.01",
        "L:0.1",
        "L:1.0",
    ]
    assert [c.l2_strength for c in configs[:5]] == list(r2c.LAMBDA_GRID)
    assert [c.l2_strength for c in configs[5:]] == list(r2c.LAMBDA_GRID)
    assert {c.family_id for c in configs} == {r2c.FAMILY_P_ID, r2c.FAMILY_L_ID}
    assert 0.0 not in r2c.LAMBDA_GRID


def test_design_manifest_loads_and_validates() -> None:
    design = r2c.load_design()
    r2c.validate_design(design)
    assert r2c.design_fingerprint(design) == r2c.design_fingerprint(design)
    assert design["no_model_rerun"] is True


@pytest.mark.skipif(not R2B_RAW.exists(), reason="frozen R2B artifact is not present")
def test_design_pins_the_frozen_r2b_sha256() -> None:
    design = r2c.load_design()
    assert design["source_r2b_raw"]["file_sha256"] == r2c.file_sha256(R2B_RAW)


@pytest.mark.parametrize(
    "mutate",
    [
        {"artifact_version": 2},
        {"round_version": 2},
        {"lambda_grid": [1e-06, 1e-04, 1e-03, 1e-01, 1.0]},
        {"no_model_rerun": False},
    ],
)
def test_design_validation_fails_closed_on_tampering(mutate: dict[str, Any]) -> None:
    design = dict(r2c.load_design())
    design.update(mutate)
    with pytest.raises(r2c.DesignMismatchError):
        r2c.validate_design(design)


def test_design_validation_rejects_bootstrap_replicates_change() -> None:
    design = json.loads(json.dumps(r2c.load_design()))
    design["paired_test_bootstrap"]["replicates"] = 10
    with pytest.raises(r2c.DesignMismatchError):
        r2c.validate_design(design)
    design = json.loads(json.dumps(r2c.load_design()))
    design["paired_train_refit_bootstrap"]["replicates"] = 10
    with pytest.raises(r2c.DesignMismatchError):
        r2c.validate_design(design)


def test_design_validation_rejects_family_change() -> None:
    design = json.loads(json.dumps(r2c.load_design()))
    for entry in design["method_families"]:
        if entry["id"] == r2c.FAMILY_L_ID:
            entry["endpoint_policy"]["id"] = "clip"
    with pytest.raises(r2c.DesignMismatchError):
        r2c.validate_design(design)


# --- function families -------------------------------------------------------


def test_family_p_feature_is_the_identity() -> None:
    for p in (0.0, 0.01, 0.2, 0.5, 0.8, 0.99, 1.0):
        assert r2c.feature_value(r2c.FEATURE_RAW_ID, p) == p


def test_family_l_identity_map_property() -> None:
    for p in (0.01, 0.2, 0.5, 0.8, 0.99):
        mapped = r2c._stable_sigmoid(1.0 * r2c.feature_value(r2c.FEATURE_LOGIT_ID, p) + 0.0)
        assert mapped == pytest.approx(p, abs=1e-12)


def test_family_l_rejects_exact_endpoints_without_clipping() -> None:
    for endpoint in (0.0, 1.0):
        with pytest.raises(r2c.ProbabilityEndpointError):
            r2c.feature_value(r2c.FEATURE_LOGIT_ID, endpoint)
        with pytest.raises(r2c.ProbabilityEndpointError):
            r2c._logit(endpoint)


def test_family_p_tolerates_endpoints_but_family_l_fails_closed() -> None:
    points = tuple(
        analysis.PairedPoint(f"t{i:02d}", float(i % 2), float(i % 2), 0.4 + 0.01 * i)
        for i in range(6)
    )
    plan_fp = "planfp"
    family_p = next(c for c in r2c.method_configs() if c.family_id == r2c.FAMILY_P_ID)
    # Family P accepts a raw-p endpoint.
    r2c._compute_config(family_p, train_points=points, test_points=points, plan_fingerprint=plan_fp)
    family_l = next(c for c in r2c.method_configs() if c.family_id == r2c.FAMILY_L_ID)
    with pytest.raises(r2c.ProbabilityEndpointError):
        r2c._compute_config(
            family_l, train_points=points, test_points=points, plan_fingerprint=plan_fp
        )


# --- artifact structure / determinism ---------------------------------------


def test_synthetic_artifact_is_deterministic_and_json_safe() -> None:
    first = _build_synthetic()
    second = _build_synthetic()
    text_a = json.dumps(first, sort_keys=True, allow_nan=False)
    text_b = json.dumps(second, sort_keys=True, allow_nan=False)
    assert text_a == text_b


def test_artifact_reports_all_configs_and_sign_counts() -> None:
    artifact = _build_synthetic()
    assert artifact["configuration_order"] == [c.label for c in r2c.method_configs()]
    assert len(artifact["configurations"]) == 10
    counts = artifact["transport_sign_counts"]
    assert (
        counts["cat_to_ovr_negative"] + counts["cat_to_ovr_positive"] + counts["cat_to_ovr_zero"]
        == 10
    )
    assert (
        counts["ovr_to_cat_negative"] + counts["ovr_to_cat_positive"] + counts["ovr_to_cat_zero"]
        == 10
    )
    assert set(counts) == {
        "cat_to_ovr_negative",
        "cat_to_ovr_positive",
        "cat_to_ovr_zero",
        "ovr_to_cat_negative",
        "ovr_to_cat_positive",
        "ovr_to_cat_zero",
    }


def test_artifact_contains_no_method_winner_selection() -> None:
    artifact = _build_synthetic()
    banned = {"winner_config", "selected_lambda", "selected_method", "production_default"}
    assert banned.isdisjoint(artifact.keys())
    text = json.dumps(artifact, sort_keys=True)
    assert "winner_config" not in text
    assert "selected_lambda" not in text


def test_artifact_records_excluded_families_and_limitations() -> None:
    artifact = _build_synthetic()
    report = artifact["limitations"]
    assert "isotonic" in report["excluded_methods"]
    assert "full-3-parameter-beta" in report["excluded_methods"]
    assert "exploratory" in report["statement"]
    assert artifact["round_status"] == "complete"
    assert artifact["train_refit_bootstrap"]["failed_fits"] == 0


def test_train_refit_failure_is_recorded_and_cell_marked_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    train, test = _synthetic_points()
    design = r2c.load_design()
    real_fit = r2c._fit_calibrator
    calls: dict[tuple[str, str], int] = {}

    def flaky(
        *, config: Any, source_measurement: str, training_rows: Any, plan_fingerprint: str
    ) -> Any:
        key = (config.label, source_measurement)
        calls[key] = calls.get(key, 0) + 1
        # The first call per key is the full-train fit; later calls are refits.
        if key == ("P:0.01", "OVR") and calls[key] > 1:
            raise r2c.InvalidDecisionError("forced uncertified refit")
        return real_fit(
            config=config,
            source_measurement=source_measurement,
            training_rows=training_rows,
            plan_fingerprint=plan_fingerprint,
        )

    monkeypatch.setattr(r2c, "_fit_calibrator", flaky)
    artifact = r2c.build_r2c_analysis_artifact(
        raw=_raw_stub(),
        design=design,
        plan=_fake_plan(),
        train_points=train,
        test_points=test,
        provenance=None,
        test_bootstrap_replicates=3,
        train_refit_replicates=4,
    )
    assert artifact["round_status"] == "incomplete"
    assert artifact["train_refit_bootstrap"]["status"] == "incomplete"
    assert artifact["train_refit_bootstrap"]["failed_fits"] == 4
    failed = artifact["train_refit_bootstrap"]["per_configuration"]["P:0.01"]
    assert failed["status"] == "failed"
    assert failed["failed_fit_count"] == 4
    assert len(failed["failures"]) == 4
    assert failed["failures"][0]["measurement"] == "OVR"
    # No subset interval is computed over the surviving replicates.
    assert "native_cat" not in failed
    assert "transport_cat_to_ovr" not in failed
    assert artifact["train_refit_bootstrap"]["per_configuration"]["P:1e-06"]["status"] == "complete"


# --- R2B current-configuration reproduction ---------------------------------


@pytest.mark.skipif(
    not (R2B_RAW.exists() and R2B_ANALYSIS.exists()),
    reason="frozen R2B artifacts are not present",
)
def test_family_p_lambda_0_01_reproduces_committed_r2b() -> None:
    raw = json.loads(R2B_RAW.read_text())
    plan, _dataset, train, test = r2c.load_frozen_evidence(raw)
    config = next(c for c in r2c.method_configs() if c.label == "P:0.01")
    block = r2c._config_result_block(
        r2c._compute_config(
            config, train_points=train, test_points=test, plan_fingerprint=plan.fingerprint
        ),
        train_points=train,
        test_points=test,
    )
    r2b = json.loads(R2B_ANALYSIS.read_text())
    assert block["transport"]["brier_matrix"] == r2b["brier_matrix"]
    assert block["calibrators"]["cat"]["slope"] == r2b["calibrator_a"]["slope"]
    assert block["calibrators"]["cat"]["intercept"] == r2b["calibrator_a"]["intercept"]
    assert block["calibrators"]["ovr"]["slope"] == r2b["calibrator_b"]["slope"]
    assert block["calibrators"]["ovr"]["intercept"] == r2b["calibrator_b"]["intercept"]
    assert block["native"]["cat"]["native_minus_raw_brier"] == pytest.approx(
        r2b["raw_relative_brier_changes"]["cat_self_minus_raw_cat"], abs=1e-15
    )
    assert block["native"]["ovr"]["native_minus_raw_brier"] == pytest.approx(
        r2b["raw_relative_brier_changes"]["ovr_self_minus_raw_ovr"], abs=1e-15
    )


def test_frozen_evidence_has_expected_shape() -> None:
    if not R2B_RAW.exists():
        pytest.skip("frozen R2B artifact is not present")
    raw = json.loads(R2B_RAW.read_text())
    _plan, _dataset, train, test = r2c.load_frozen_evidence(raw)
    assert len(train) == 90
    assert len(test) == 60
    for point in train + test:
        assert 0.0 <= point.score_a <= 1.0
        assert 0.0 <= point.score_b <= 1.0
        assert point.y in (0.0, 1.0)


@pytest.mark.skipif(not R2B_RAW.exists(), reason="frozen R2B artifact is not present")
def test_transport_point_matches_brier_matrix_delta() -> None:
    raw = json.loads(R2B_RAW.read_text())
    plan, _dataset, train, test = r2c.load_frozen_evidence(raw)
    for config in r2c.method_configs():
        computation = r2c._compute_config(
            config, train_points=train, test_points=test, plan_fingerprint=plan.fingerprint
        )
        block = r2c._config_result_block(computation, train_points=train, test_points=test)
        matrix = block["transport"]["brier_matrix"]
        assert computation.transport_cat_to_ovr_point == pytest.approx(
            matrix["delta_a_to_b"], abs=1e-15
        )
        assert computation.transport_ovr_to_cat_point == pytest.approx(
            matrix["delta_b_to_a"], abs=1e-15
        )
        assert block["transport"]["transport_delta_cat_to_ovr"] == pytest.approx(
            matrix["delta_a_to_b"], abs=1e-15
        )
        assert block["transport"]["transport_delta_ovr_to_cat"] == pytest.approx(
            matrix["delta_b_to_a"], abs=1e-15
        )


def test_feature_transforms_keep_probabilities_interior() -> None:
    assert math.isfinite(r2c._logit(1e-9))
    assert math.isfinite(r2c._logit(1 - 1e-9))
