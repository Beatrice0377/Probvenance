"""Offline tests for the R2C.1 low-regularization numerical closure.

No model, no GPU, no network. These tests lock the Decimal reference solver
(exact known optimum; agreement with the production binary64 solver on an
ordinary lambda), the exact binary64 feature semantics for both families,
deterministic bootstrap replay, and the frozen 15-failure set / source lineage.
They never run the full 4000-fit closure.
"""

from __future__ import annotations

import decimal
import hashlib
import importlib.util
import json
import math
import subprocess
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


r2c1 = _load("r2c1_numerical_closure")
r2c = _load("r2c_method_adequacy")

R2B_RAW = HARNESS_DIR / "results" / "r2b-stability-qwen35-2b-v1.json"
R2C_ANALYSIS = HARNESS_DIR / "results" / "r2c-method-adequacy-qwen35-2b-v1-analysis.json"
DESIGN = HARNESS_DIR / "r2c1_numerical_closure_design.json"

D = decimal.Decimal


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# PART 47-48: reference optimizer correctness.
# ---------------------------------------------------------------------------


def test_reference_reaches_exact_known_optimum() -> None:
    # All features zero and balanced labels make (0, 0) the unique optimum.
    rows = [(D(0), D(0)), (D(0), D(1)), (D(0), D(1)), (D(0), D(0))]
    fit = r2c1.reference_solve(rows)
    assert fit.slope == 0
    assert fit.intercept == 0
    assert fit.gap_upper_bound <= r2c1.REFERENCE_OBJECTIVE_GAP_TOLERANCE


def test_reference_matches_production_on_ordinary_lambda() -> None:
    from probvenance.calibration import _solve_l2_logistic, _stable_sigmoid

    xs = [0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 0.1, 0.9]
    ys = [0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1]
    prod_slope, prod_intercept = _solve_l2_logistic(
        [(x, float(y)) for x, y in zip(xs, ys, strict=True)], 0.01
    )
    rows = [(D.from_float(x), D.from_float(float(y))) for x, y in zip(xs, ys, strict=True)]
    fit = r2c1.reference_solve(rows, lam=D("0.01"))
    assert abs(prod_slope - float(fit.slope)) < 1e-8
    assert abs(prod_intercept - float(fit.intercept)) < 1e-8
    for x in xs:
        prod = _stable_sigmoid(prod_slope * x + prod_intercept)
        ref = float(r2c1._decimal_sigmoid(fit.slope * D.from_float(x) + fit.intercept))
        assert abs(prod - ref) < 1e-8


def test_reference_is_deterministic() -> None:
    rows = [
        (D.from_float(0.1), D(0)),
        (D.from_float(0.4), D(1)),
        (D.from_float(0.6), D(1)),
        (D.from_float(0.9), D(0)),
        (D.from_float(0.3), D(0)),
    ]
    first = r2c1.reference_solve(rows)
    second = r2c1.reference_solve(rows)
    assert first.slope == second.slope
    assert first.intercept == second.intercept
    assert first.gradient_norm == second.gradient_norm


def test_decimal_sigmoid_and_softplus_are_overflow_safe() -> None:
    for magnitude in (1, 100, 1000):
        positive = r2c1._decimal_sigmoid(D(magnitude))
        negative = r2c1._decimal_sigmoid(D(-magnitude))
        assert D(0) <= negative <= positive <= D(1)
        assert r2c1._decimal_softplus(D(magnitude)) >= D(magnitude)
        assert r2c1._decimal_softplus(D(-magnitude)) >= D(0)


# ---------------------------------------------------------------------------
# PART 49-50: exact binary64 feature semantics.
# ---------------------------------------------------------------------------


def test_family_p_feature_is_exact_binary64_float() -> None:
    probability = 0.123456789012345
    feature = r2c.feature_value(r2c.FEATURE_RAW_ID, probability)
    assert r2c1._dec(feature) == D.from_float(probability)
    # Must NOT be a fresh Decimal built from the JSON-looking literal.
    assert r2c1._dec(feature) != D(str(probability))


def test_family_l_feature_is_r2c_binary64_logit() -> None:
    probability = 0.3
    feature = r2c.feature_value(r2c.FEATURE_LOGIT_ID, probability)
    expected = D.from_float(math.log(probability / (1.0 - probability)))
    assert r2c1._dec(feature) == expected
    # The reference must not silently define its own higher-precision logit.
    higher_precision_logit = (D.from_float(probability) / (D(1) - D.from_float(probability))).ln()
    assert r2c1._dec(feature) != higher_precision_logit


# ---------------------------------------------------------------------------
# PART 51: deterministic bootstrap replay against the frozen R2C protocol.
# ---------------------------------------------------------------------------


def test_bootstrap_multiset_replay_is_deterministic_and_matches_protocol() -> None:
    raw = json.loads(R2B_RAW.read_text(encoding="utf-8"))
    _plan, _dataset, train_points, _test_points = r2c.load_frozen_evidence(raw)
    draws_first = r2c1._train_refit_draws(train_points, 126)
    draws_second = r2c1._train_refit_draws(train_points, 126)
    assert draws_first == draws_second
    assert r2c1.PAIRED_TRAIN_REFIT_PROTOCOL_ID == "sha256-r2c-paired-train-refit-bootstrap"
    assert r2c1.PAIRED_TRAIN_REFIT_PROTOCOL_VERSION == 1
    item_count = len(train_points)
    replicate = 125
    direct_positions = [
        r2c1.r2b_stability._draw_index(
            protocol_id=r2c1.PAIRED_TRAIN_REFIT_PROTOCOL_ID,
            protocol_version=r2c1.PAIRED_TRAIN_REFIT_PROTOCOL_VERSION,
            replicate=replicate,
            draw=position,
            item_count=item_count,
        )
        for position in range(item_count)
    ]
    direct = [train_points[index] for index in direct_positions]
    replayed = [train_points[index] for index in draws_first[replicate]]
    assert r2c1._multiset_fingerprint(direct) == r2c1._multiset_fingerprint(replayed)


# ---------------------------------------------------------------------------
# PART 52: the frozen 15-failure set and source lineage.
# ---------------------------------------------------------------------------


def test_design_matches_frozen_contract() -> None:
    design = json.loads(DESIGN.read_text(encoding="utf-8"))
    r2c1.validate_design(design)  # raises on any drift
    assert len(design["exact_failed_fit_set"]) == 15
    assert r2c1.REFERENCE_DECIMAL_PRECISION == 80
    assert D("1e-24") == r2c1.REFERENCE_OBJECTIVE_GAP_TOLERANCE
    assert r2c1.REFERENCE_MAX_NEWTON_ITERATIONS == 500
    assert r2c1.EXPECTED_REFERENCE_FITS == 4000


def test_design_source_sha256_matches_committed_sources() -> None:
    design = json.loads(DESIGN.read_text(encoding="utf-8"))
    assert design["source_r2b_raw"]["file_sha256"] == _sha256(R2B_RAW)
    assert design["source_r2c_analysis"]["file_sha256"] == _sha256(R2C_ANALYSIS)


def test_design_failed_set_equals_committed_r2c_artifact() -> None:
    design = json.loads(DESIGN.read_text(encoding="utf-8"))
    artifact = json.loads(R2C_ANALYSIS.read_text(encoding="utf-8"))
    artifact_failed: set[tuple[str, str, int]] = set()
    for block in artifact["configurations"]:
        label = block["label"]
        train_block = block["train_refit_bootstrap"]
        if train_block["status"] == "complete":
            continue
        for failure in train_block["failures"]:
            artifact_failed.add((block["family_id"], failure["measurement"], failure["replicate"]))
        assert label in {"P:1e-06", "L:1e-06"}
    assert artifact_failed == r2c1._design_failed_set(design)
    assert artifact["train_refit_bootstrap"]["failed_fits"] == 15


# ---------------------------------------------------------------------------
# PART 33 + final closure: preregistered taxonomy vs the observed result.
# ---------------------------------------------------------------------------


def _diag(*, gap_meets: bool, certificate_met: bool) -> dict[str, bool]:
    return {
        "rounded_reference_actual_gap_meets_objective_tolerance": gap_meets,
        "production_certificate_met_at_rounded": certificate_met,
    }


def test_observed_pattern_has_no_exact_match_and_falsifies_a_submechanism() -> None:
    result = r2c1.classify_failed_fits(
        reference_attempted=4000,
        reference_failed=0,
        violations=[],
        failed_diagnostics=[_diag(gap_meets=True, certificate_met=True)] * 15,
    )
    block = result["predeclared_classification_result"]
    assert block["exact_match"] is None
    assert block["closest_family"] == "A"
    assert block["preregistered_a_submechanism_supported"] is False
    assert result["observed_mechanism"]["id"] == r2c1.OBSERVED_MECHANISM_SOLVER_PATH_ID
    assert result["observed_mechanism"]["version"] == 1


def test_preregistered_a_pattern_is_an_exact_match() -> None:
    result = r2c1.classify_failed_fits(
        reference_attempted=4000,
        reference_failed=0,
        violations=[],
        failed_diagnostics=[_diag(gap_meets=True, certificate_met=False)] * 15,
    )
    block = result["predeclared_classification_result"]
    assert block["exact_match"] == "A"
    assert block["closest_family"] == "A"
    assert block["preregistered_a_submechanism_supported"] is True
    assert result["observed_mechanism"]["id"] == r2c1.PREREGISTERED_A_MECHANISM_ID


def test_reference_failure_and_violations_stay_exact_matches() -> None:
    assert (
        r2c1.classify_failed_fits(
            reference_attempted=4000, reference_failed=1, violations=[], failed_diagnostics=[]
        )["predeclared_classification_result"]["exact_match"]
        == "C"
    )
    assert (
        r2c1.classify_failed_fits(
            reference_attempted=4000,
            reference_failed=0,
            violations=[{"x": 1}],
            failed_diagnostics=[],
        )["predeclared_classification_result"]["exact_match"]
        == "D"
    )
    assert (
        r2c1.classify_failed_fits(
            reference_attempted=4000,
            reference_failed=0,
            violations=[],
            failed_diagnostics=[_diag(gap_meets=False, certificate_met=False)],
        )["predeclared_classification_result"]["exact_match"]
        == "B"
    )


def test_no_post_hoc_category_is_invented() -> None:
    for diagnostics in (
        [_diag(gap_meets=True, certificate_met=True)] * 3,
        [_diag(gap_meets=True, certificate_met=False)] * 3,
        [_diag(gap_meets=False, certificate_met=False)] * 3,
        [],
    ):
        block = r2c1.classify_failed_fits(
            reference_attempted=4000,
            reference_failed=0,
            violations=[],
            failed_diagnostics=diagnostics,
        )["predeclared_classification_result"]
        assert block["exact_match"] in (None, "A", "B", "C", "D")
        assert block["closest_family"] in (None, "A", "B", "C", "D")


def test_numerical_projection_ignores_classification_metadata() -> None:
    payload = {
        "reference_fit_summary": {"attempted": 4000, "failed": 0},
        "classification": {"category": "A"},
        "predeclared_classification_result": {"exact_match": "A"},
        "observed_mechanism": {"id": "x", "version": 1},
        "limitations": {"statement": "a"},
    }
    assert r2c1.numerical_projection(payload) == {
        "reference_fit_summary": {"attempted": 4000, "failed": 0}
    }


def test_reclassify_artifact_changes_only_classification_metadata() -> None:
    artifact_path = HARNESS_DIR / "results" / "r2c1-low-reg-numerical-closure-v1-analysis.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    updated = r2c1.reclassify_artifact(artifact)
    assert r2c1.numerical_projection(updated) == r2c1.numerical_projection(artifact)
    block = updated["predeclared_classification_result"]
    assert block["exact_match"] is None
    assert block["closest_family"] == "A"
    assert block["preregistered_a_submechanism_supported"] is False
    assert updated["observed_mechanism"]["id"] == r2c1.OBSERVED_MECHANISM_SOLVER_PATH_ID
    assert "classification" not in updated


def test_committed_artifact_projection_matches_parent_commit() -> None:
    result = subprocess.run(
        [
            "git",
            "show",
            "eb69ddc:experiments/calibration_transport/results/"
            "r2c1-low-reg-numerical-closure-v1-analysis.json",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip("parent commit artifact is not available in this checkout")
    old = json.loads(result.stdout)
    current = json.loads(
        (HARNESS_DIR / "results" / "r2c1-low-reg-numerical-closure-v1-analysis.json").read_text(
            encoding="utf-8"
        )
    )
    assert r2c1.numerical_projection(old) == r2c1.numerical_projection(current)
    assert old["reference_fit_summary"] == current["reference_fit_summary"]
    assert old["failed_fit_diagnostics"] == current["failed_fit_diagnostics"]
    assert old["completed_train_refit_summaries"] == current["completed_train_refit_summaries"]


def test_raw_brier_is_plain_squared_error() -> None:
    assert r2c1._raw_brier([D("0.998")], [D(1)]) == (D("0.998") - D(1)) ** 2
    assert r2c1._raw_brier([D("0.2")], [D(0)]) == (D("0.2") - D(0)) ** 2


def test_reference_native_delta_matches_r2c_point_estimate() -> None:
    raw = json.loads(R2B_RAW.read_text(encoding="utf-8"))
    _plan, _dataset, train_points, test_points = r2c.load_frozen_evidence(raw)
    artifact = json.loads(R2C_ANALYSIS.read_text(encoding="utf-8"))
    block = next(entry for entry in artifact["configurations"] if entry["label"] == "P:0.01")
    expected = block["native"]["cat"]["native_minus_raw_brier"]
    cat_group = next(
        group
        for group in r2c1._groups()
        if group.family_id == r2c.FAMILY_P_ID and group.measurement == "CAT"
    )
    reference = r2c1.reference_solve(r2c1._decimal_rows(train_points, cat_group), lam=D("0.01"))
    labels = [r2c1._dec(point.y) for point in test_points]
    features = [r2c1._dec(r2c1._measurement_feature(point, cat_group)) for point in test_points]
    raw_a = [r2c1._dec(point.score_a) for point in test_points]
    with decimal.localcontext(r2c1._REFERENCE_CONTEXT):
        calibrated = r2c1._reference_brier(features, reference, labels)
        baseline = r2c1._raw_brier(raw_a, labels)
        delta = float(calibrated - baseline)
    assert abs(delta - expected) < 1e-9
