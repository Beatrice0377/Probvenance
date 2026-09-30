"""Synthetic-only engineering tests for the R4 calibration-family implementation.

These tests exercise ``experiments/calibration_transport/r4_calibration_families.py``
with hand-written synthetic arrays only.  They never read a study dataset, never
load a model or tokenizer, never touch a GPU, and never fit a real R4 population.
"""

from __future__ import annotations

import importlib.util
import itertools
import json
import math
import re
import sys
from pathlib import Path

import numpy
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
TRANSPORT_DIR = REPO_ROOT / "experiments" / "calibration_transport"
MODULE_PATH = TRANSPORT_DIR / "r4_calibration_families.py"
CANDIDATE_JSON = TRANSPORT_DIR / "R4_CALIBRATION_FAMILY_SEMANTIC_CANDIDATE.json"
FREEZE_DOC = TRANSPORT_DIR / "R4_CALIBRATION_FAMILY_FREEZE.md"
CORE_CALIBRATION = REPO_ROOT / "src" / "probvenance" / "calibration.py"

spec = importlib.util.spec_from_file_location("r4_calibration_families", MODULE_PATH)
families = importlib.util.module_from_spec(spec)
sys.modules["r4_calibration_families"] = families
spec.loader.exec_module(families)

from probvenance.fingerprint import canonical_json, fingerprint  # noqa: E402

MAX_GRADIENT_DISCREPANCY = 1e-6
MAX_ALTERNATIVE_START_DISCREPANCY = 1e-9

# Synthetic implementation-QA thresholds for the symmetric stress case (§13 of the
# provenance-amendment task).  They are engineering diagnostics only and never
# enter the scientific fingerprint.
SYMMETRIC_MAX_OBJECTIVE_SPREAD = 1e-12
SYMMETRIC_MAX_PREDICTION_SPREAD = 1e-8
# Raw-coordinate convergence bound on the exactly symmetric fixture.  This is NOT
# the production acceptance tolerance: two of the four deterministic starts stall
# above ``KKT_ACCEPTANCE_TOL`` while reaching the identical objective.
SYMMETRIC_MAX_START_KKT = 1e-8

# Source scan for score/output clipping logic (§38).  The ``KKT_ACCEPTANCE_TOL``
# engineering tolerance is deliberately NOT part of this list: it never modifies
# a score or a prediction.
FORBIDDEN_SOURCE_PATTERN = re.compile(r"\bepsilon\b|\beps\b|nextafter|clip|1e-6|1e-12")

# Synthetic fixtures whose constrained optimum lands on each active-set face.
INTERIOR_SCORES = [0.1, 0.15, 0.3, 0.35, 0.9]
INTERIOR_LABELS = [0, 0, 1, 0, 1]
A0_SCORES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
A0_LABELS = [1, 0, 1, 0, 1, 0, 1, 0, 1]
B0_SCORES = [0.02, 0.05, 0.08, 0.1, 0.2, 0.5, 0.9]
B0_LABELS = [0, 0, 1, 1, 1, 1, 0]
CORNER_SCORES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
CORNER_LABELS = [1, 1, 1, 0, 0, 0, 0, 0]
REVERSED_CORNER_SCORES = [0.05, 0.1, 0.2, 0.4, 0.6, 0.8, 0.95]
REVERSED_CORNER_LABELS = [1, 1, 1, 1, 0, 0, 0]
# SYMMETRIC NUMERICAL-CONDITIONING STRESS CASE.  The data below is exactly
# symmetric under ``score -> 1 - score`` together with ``label -> 1 - label``, so
# the objective is exactly invariant under the parameter involution
# ``(a, b, c) -> (b, a, -c)``.  The unique constrained optimum therefore has
# ``a == b`` and ``c == 0``; the low-curvature ``a - b`` direction only makes the
# frozen BFGS settings converge to ~1e-8 in raw coordinates.  The fixture is kept
# as a numerical stress case (it is NOT used for the ordinary uniqueness audit)
# and is characterised by the strict-convexity / Hessian diagnostics in
# ``test_beta_symmetric_stress_case_diagnostics``.
SYMMETRIC_SCORES = [0.2, 0.4, 0.6, 0.8]
SYMMETRIC_LABELS = [0, 1, 0, 1]


def _rows(scores, labels):
    return [(float(s), int(y)) for s, y in zip(scores, labels, strict=True)]


def _manual_beta_fit(a, b, c):
    """Build a hand-specified beta map for the application-path tests."""
    return families.BetaFit(
        a=a,
        b=b,
        c=c,
        active_face=families.FACE_INTERIOR,
        objective=0.0,
        kkt_residual=0.0,
        solver_status=0,
        solver_status_class=families.SOLVER_SUCCESS,
        solver_message="manual test fixture",
        solver_nit=0,
        solver_nfev=0,
        solver_njev=0,
        face_tie_break_used=False,
        training_data_fingerprint="manual-test-fixture",
    )


def _grid(low=0.001, high=0.999, steps=997):
    return [low + (high - low) * index / (steps - 1) for index in range(steps)]


def _max_monotonicity_violation(values):
    return max(
        (max(0.0, previous - current) for previous, current in itertools.pairwise(values)),
        default=0.0,
    )


# --------------------------------------------------------------------------
# Frozen identity continuity
# --------------------------------------------------------------------------


def test_implementation_fingerprints_match_frozen_candidate_json():
    payload = json.loads(CANDIDATE_JSON.read_text(encoding="utf-8"))
    procedures = {entry["label"]: entry for entry in payload["candidate_procedures"]}
    assert procedures["I-isotonic"]["fingerprint"] == families.ISOTONIC_SCIENTIFIC_FINGERPRINT
    assert procedures["B-beta"]["fingerprint"] == families.BETA_SCIENTIFIC_FINGERPRINT


def test_frozen_candidate_payloads_still_hash_to_their_fingerprints():
    payload = json.loads(CANDIDATE_JSON.read_text(encoding="utf-8"))
    for entry in payload["candidate_procedures"]:
        assert fingerprint(entry["payload"]) == entry["fingerprint"]


def test_frozen_fingerprints_are_recorded_in_the_freeze_document():
    text = FREEZE_DOC.read_text(encoding="utf-8")
    assert families.ISOTONIC_SCIENTIFIC_FINGERPRINT in text
    assert families.BETA_SCIENTIFIC_FINGERPRINT in text


def test_r3_continuity_block_is_declared_matching():
    payload = json.loads(CANDIDATE_JSON.read_text(encoding="utf-8"))
    continuity = payload["r3_continuity"]
    assert continuity["all_match"] is True
    for label in ("P-low", "P-historical", "L-low", "L-historical"):
        assert any(entry["label"] == label for entry in continuity["procedures"])


def test_implementation_identity_is_separate_from_scientific_identity():
    assert families.ISOTONIC_IMPLEMENTATION_ID == "r4-isotonic-pava-linear-v1"
    assert families.BETA_IMPLEMENTATION_ID == "r4-beta-active-set-bfgs-kkt-v1"
    assert families.ISOTONIC_SCIENTIFIC_FINGERPRINT != families.BETA_SCIENTIFIC_FINGERPRINT


# --------------------------------------------------------------------------
# I-isotonic
# --------------------------------------------------------------------------


def test_isotonic_strictly_increasing_fit():
    fit = families.fit_isotonic_fixed_decision_probability(
        [0.1, 0.2, 0.3, 0.4], [0, 0, 1, 1]
    )
    assert fit.thresholds == (0.1, 0.2, 0.3, 0.4)
    assert fit.fitted_values == (0.0, 0.0, 1.0, 1.0)
    assert families.apply_isotonic_fixed_decision_probability(fit, 0.1) == 0.0
    assert families.apply_isotonic_fixed_decision_probability(fit, 0.4) == 1.0


def test_isotonic_exact_tie_aggregation():
    fit = families.fit_isotonic_fixed_decision_probability(
        [0.2, 0.2, 0.4, 0.4], [1, 0, 1, 1]
    )
    assert fit.thresholds == (0.2, 0.4)
    assert fit.fitted_values == (0.5, 1.0)


def test_isotonic_pava_pooling():
    full_pool = families.fit_isotonic_fixed_decision_probability(
        [0.1, 0.2, 0.3, 0.4], [1, 1, 0, 0]
    )
    assert full_pool.fitted_values == (0.5, 0.5, 0.5, 0.5)
    partial_pool = families.fit_isotonic_fixed_decision_probability(
        [0.1, 0.2, 0.3, 0.4], [1, 0, 0, 1]
    )
    assert partial_pool.fitted_values[:3] == pytest.approx((1.0 / 3.0,) * 3)
    assert partial_pool.fitted_values[3] == 1.0


def test_isotonic_all_scores_equal():
    fit = families.fit_isotonic_fixed_decision_probability(
        [0.3, 0.3, 0.3, 0.3], [0, 1, 1, 0]
    )
    assert fit.thresholds == (0.3,)
    assert fit.fitted_values == (0.5,)
    assert families.apply_isotonic_fixed_decision_probability(fit, 0.0) == 0.5
    assert families.apply_isotonic_fixed_decision_probability(fit, 1.0) == 0.5


def test_isotonic_all_labels_zero_and_one():
    zeros = families.fit_isotonic_fixed_decision_probability([0.2, 0.5, 0.8], [0, 0, 0])
    ones = families.fit_isotonic_fixed_decision_probability([0.2, 0.5, 0.8], [1, 1, 1])
    assert zeros.fitted_values == (0.0, 0.0, 0.0)
    assert ones.fitted_values == (1.0, 1.0, 1.0)


def test_isotonic_accepts_exact_zero_and_one_scores():
    fit = families.fit_isotonic_fixed_decision_probability([0.0, 0.5, 1.0], [0, 1, 1])
    assert fit.thresholds == (0.0, 0.5, 1.0)
    assert fit.fitted_values == (0.0, 1.0, 1.0)


def test_isotonic_constant_support_extension_below_and_above():
    fit = families.fit_isotonic_fixed_decision_probability([0.2, 0.4, 0.6], [0, 1, 1])
    assert families.apply_isotonic_fixed_decision_probability(fit, 0.0) == fit.fitted_values[0]
    assert families.apply_isotonic_fixed_decision_probability(fit, 1.0) == fit.fitted_values[-1]
    assert families.apply_isotonic_fixed_decision_probability(fit, 0.05) == fit.fitted_values[0]
    assert families.apply_isotonic_fixed_decision_probability(fit, 0.95) == fit.fitted_values[-1]


def test_isotonic_linear_interior_interpolation():
    fit = families.fit_isotonic_fixed_decision_probability([0.2, 0.4], [0, 1])
    assert families.apply_isotonic_fixed_decision_probability(fit, 0.3) == pytest.approx(0.5)
    assert families.apply_isotonic_fixed_decision_probability(fit, 0.35) == pytest.approx(0.75)


def test_isotonic_rejects_invalid_inputs():
    with pytest.raises(families.IsotonicContractViolation):
        families.fit_isotonic_fixed_decision_probability([], [])
    with pytest.raises(families.IsotonicContractViolation):
        families.fit_isotonic_fixed_decision_probability([0.2, 0.4], [0])
    with pytest.raises(families.IsotonicContractViolation):
        families.fit_isotonic_fixed_decision_probability([0.2, float("nan")], [0, 1])
    with pytest.raises(families.IsotonicContractViolation):
        families.fit_isotonic_fixed_decision_probability([0.2, float("inf")], [0, 1])
    with pytest.raises(families.IsotonicContractViolation):
        families.fit_isotonic_fixed_decision_probability([-0.1, 0.4], [0, 1])
    with pytest.raises(families.IsotonicContractViolation):
        families.fit_isotonic_fixed_decision_probability([0.2, 1.1], [0, 1])
    with pytest.raises(families.IsotonicContractViolation):
        families.fit_isotonic_fixed_decision_probability([0.2, 0.4], [0, 2])
    with pytest.raises(families.IsotonicContractViolation):
        families.fit_isotonic_fixed_decision_probability([0.2, 0.4], [0, 1, 1])


def test_isotonic_order_invariance():
    scores = [0.4, 0.2, 0.8, 0.2, 0.6, 0.4]
    labels = [1, 0, 1, 1, 0, 0]
    base = families.fit_isotonic_fixed_decision_probability(scores, labels)
    reversed_fit = families.fit_isotonic_fixed_decision_probability(
        list(reversed(scores)), list(reversed(labels))
    )
    permutation = [3, 0, 5, 1, 4, 2]
    permuted_fit = families.fit_isotonic_fixed_decision_probability(
        [scores[i] for i in permutation], [labels[i] for i in permutation]
    )
    assert base.state_payload() == reversed_fit.state_payload()
    assert base.state_payload() == permuted_fit.state_payload()
    assert base.state_fingerprint() == permuted_fit.state_fingerprint()


def test_isotonic_monotonicity_over_grid_including_endpoints():
    fit = families.fit_isotonic_fixed_decision_probability(
        [0.1, 0.3, 0.35, 0.5, 0.5, 0.7, 0.9], [1, 0, 1, 1, 0, 0, 1]
    )
    values = [
        families.apply_isotonic_fixed_decision_probability(fit, s) for s in _grid(0.0, 1.0, 1001)
    ]
    assert _max_monotonicity_violation(values) == 0.0


def test_isotonic_serialization_determinism():
    scores = [0.4, 0.2, 0.8, 0.2, 0.6, 0.4]
    labels = [1, 0, 1, 1, 0, 0]
    first = families.fit_isotonic_fixed_decision_probability(scores, labels)
    second = families.fit_isotonic_fixed_decision_probability(scores, labels)
    assert canonical_json(first.state_payload()) == canonical_json(second.state_payload())
    assert first.state_fingerprint() == second.state_fingerprint()


# --------------------------------------------------------------------------
# B-beta structural eligibility
# --------------------------------------------------------------------------


def test_beta_eligibility_accepts_interleaved_labels():
    assert families.beta_fit_eligibility(INTERIOR_SCORES, INTERIOR_LABELS) == families.ELIGIBLE


def test_beta_eligibility_rejects_empty_and_mismatched_inputs():
    with pytest.raises(families.BetaContractViolation):
        families.beta_fit_eligibility([], [])
    with pytest.raises(families.BetaContractViolation):
        families.beta_fit_eligibility([0.2, 0.4], [0])


def test_beta_eligibility_rejects_non_finite_and_out_of_range_scores():
    with pytest.raises(families.BetaContractViolation):
        families.beta_fit_eligibility([0.2, float("nan")], [0, 1])
    with pytest.raises(families.BetaContractViolation):
        families.beta_fit_eligibility([0.2, float("inf")], [0, 1])
    with pytest.raises(families.BetaContractViolation):
        families.beta_fit_eligibility([-0.1, 0.4], [0, 1])
    with pytest.raises(families.BetaContractViolation):
        families.beta_fit_eligibility([0.2, 1.1], [0, 1])


def test_beta_eligibility_rejects_non_binary_labels():
    with pytest.raises(families.BetaContractViolation):
        families.beta_fit_eligibility([0.2, 0.4], [0, 2])


def test_beta_eligibility_rejects_exact_endpoint_scores():
    assert (
        families.beta_fit_eligibility([0.0, 0.3, 0.6], [0, 1, 1])
        == families.INELIGIBLE_ENDPOINT
    )
    assert (
        families.beta_fit_eligibility([0.3, 0.6, 1.0], [0, 1, 1])
        == families.INELIGIBLE_ENDPOINT
    )


def test_beta_eligibility_rejects_single_class():
    assert (
        families.beta_fit_eligibility([0.2, 0.4, 0.6], [1, 1, 1])
        == families.BETA_FIT_INELIGIBLE_SINGLE_CLASS
    )


def test_beta_eligibility_rejects_insufficient_distinct_scores():
    assert (
        families.beta_fit_eligibility([0.3, 0.3, 0.3], [0, 1, 1])
        == families.BETA_FIT_INELIGIBLE_INSUFFICIENT_DISTINCT_SCORES
    )
    assert (
        families.beta_fit_eligibility([0.3, 0.3, 0.7, 0.7], [0, 1, 1, 0])
        == families.BETA_FIT_INELIGIBLE_INSUFFICIENT_DISTINCT_SCORES
    )
    assert families.beta_fit_eligibility([0.3, 0.5, 0.7], [0, 1, 0]) == families.ELIGIBLE


def test_beta_eligibility_rejects_complete_and_quasi_monotone_separation():
    assert (
        families.beta_fit_eligibility([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1])
        == families.BETA_FIT_INELIGIBLE_MONOTONE_SEPARATION
    )
    assert (
        families.beta_fit_eligibility([0.1, 0.2, 0.2, 0.8, 0.9], [0, 0, 0, 1, 1])
        == families.BETA_FIT_INELIGIBLE_MONOTONE_SEPARATION
    )


def test_beta_eligibility_gate_order_endpoint_before_single_class():
    assert (
        families.beta_fit_eligibility([0.0, 0.5, 0.5], [1, 1, 1])
        == families.INELIGIBLE_ENDPOINT
    )


def test_beta_eligibility_gate_order_single_class_before_insufficient_support():
    assert (
        families.beta_fit_eligibility([0.5, 0.5, 0.5], [1, 1, 1])
        == families.BETA_FIT_INELIGIBLE_SINGLE_CLASS
    )


def test_beta_eligibility_gate_order_insufficient_support_before_separation():
    assert (
        families.beta_fit_eligibility([0.2, 0.2, 0.2], [0, 0, 1])
        == families.BETA_FIT_INELIGIBLE_INSUFFICIENT_DISTINCT_SCORES
    )


def test_beta_eligibility_reversed_orientation_is_not_pre_rejected():
    assert (
        families.beta_fit_eligibility(REVERSED_CORNER_SCORES, REVERSED_CORNER_LABELS)
        == families.ELIGIBLE
    )


def test_beta_eligibility_row_order_invariance():
    scores = INTERIOR_SCORES
    labels = INTERIOR_LABELS
    reversed_state = families.beta_fit_eligibility(
        list(reversed(scores)), list(reversed(labels))
    )
    permutation = [2, 0, 3, 1]
    permuted_state = families.beta_fit_eligibility(
        [scores[i] for i in permutation], [labels[i] for i in permutation]
    )
    assert reversed_state == families.ELIGIBLE
    assert permuted_state == families.ELIGIBLE


# --------------------------------------------------------------------------
# B-beta active-set fitting
# --------------------------------------------------------------------------


def test_beta_interior_face_fit():
    fit = families.fit_beta_fixed_decision_probability(INTERIOR_SCORES, INTERIOR_LABELS)
    assert fit.active_face == families.FACE_INTERIOR
    assert fit.a > 0.0 and fit.b > 0.0
    assert fit.kkt_residual <= families.KKT_ACCEPTANCE_TOL
    assert math.isfinite(fit.objective)
    assert fit.face_tie_break_used is False


def test_beta_a0_boundary_face_fit():
    fit = families.fit_beta_fixed_decision_probability(A0_SCORES, A0_LABELS)
    assert fit.active_face == families.FACE_A0
    assert fit.a == 0.0
    assert fit.b > 0.0
    assert fit.kkt_residual <= families.KKT_ACCEPTANCE_TOL


def test_beta_b0_boundary_face_fit():
    fit = families.fit_beta_fixed_decision_probability(B0_SCORES, B0_LABELS)
    assert fit.active_face == families.FACE_B0
    assert fit.b == 0.0
    assert fit.a > 0.0
    assert fit.kkt_residual <= families.KKT_ACCEPTANCE_TOL


def test_beta_corner_face_fit():
    fit = families.fit_beta_fixed_decision_probability(CORNER_SCORES, CORNER_LABELS)
    assert fit.active_face == families.FACE_A0_B0
    assert fit.a == 0.0
    assert fit.b == 0.0
    assert fit.kkt_residual <= families.KKT_ACCEPTANCE_TOL


def test_beta_reversed_orientation_corner_fit_is_accepted():
    fit = families.fit_beta_fixed_decision_probability(
        REVERSED_CORNER_SCORES, REVERSED_CORNER_LABELS
    )
    assert fit.a == 0.0
    assert fit.b == 0.0
    assert fit.kkt_residual <= families.KKT_ACCEPTANCE_TOL


def test_beta_ineligible_fit_raises_with_frozen_state():
    with pytest.raises(families.BetaFitIneligible) as excinfo:
        families.fit_beta_fixed_decision_probability([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1])
    assert excinfo.value.state == families.BETA_FIT_INELIGIBLE_MONOTONE_SEPARATION


def test_beta_face_validity_of_every_accepted_fit():
    for scores, labels in (
        (INTERIOR_SCORES, INTERIOR_LABELS),
        (A0_SCORES, A0_LABELS),
        (B0_SCORES, B0_LABELS),
        (CORNER_SCORES, CORNER_LABELS),
    ):
        fit = families.fit_beta_fixed_decision_probability(scores, labels)
        rows = _rows(scores, labels)
        residual = families.beta_kkt_residual(rows, fit.a, fit.b, fit.c)
        assert residual <= families.KKT_ACCEPTANCE_TOL
        assert abs(residual - fit.kkt_residual) < 1e-15


def test_beta_objective_is_minimised_over_the_active_set():
    fit = families.fit_beta_fixed_decision_probability(INTERIOR_SCORES, INTERIOR_LABELS)
    rows = _rows(INTERIOR_SCORES, INTERIOR_LABELS)
    assert fit.objective == pytest.approx(families.beta_objective(rows, fit.a, fit.b, fit.c))


def test_beta_face_selection_uses_lowest_objective_and_fixed_tie_order():
    assert families.FACE_ORDER == (
        families.FACE_A0_B0,
        families.FACE_A0,
        families.FACE_B0,
        families.FACE_INTERIOR,
    )
    fit = families.fit_beta_fixed_decision_probability(CORNER_SCORES, CORNER_LABELS)
    assert fit.face_tie_break_used is False


def test_beta_parameter_validation_rejects_negative_manual_parameters():
    with pytest.raises(families.BetaContractViolation):
        families.require_beta_parameters(-1.0, 1.0, 0.0)
    with pytest.raises(families.BetaContractViolation):
        families.require_beta_parameters(1.0, -0.5, 0.0)
    with pytest.raises(families.BetaContractViolation):
        families.require_beta_parameters(float("nan"), 1.0, 0.0)
    assert families.require_beta_parameters(0.0, 2.0, -3.0) == (0.0, 2.0, -3.0)


def test_beta_apply_rejects_negative_manual_parameters():
    with pytest.raises(families.BetaContractViolation):
        families.apply_beta_fixed_decision_probability(_manual_beta_fit(-1.0, 1.0, 0.0), 0.5)


# --------------------------------------------------------------------------
# B-beta application path
# --------------------------------------------------------------------------


def test_beta_identity_map_application():
    fit = _manual_beta_fit(1.0, 1.0, 0.0)
    for score in (0.001, 0.25, 0.5, 0.75, 0.999):
        assert families.apply_beta_fixed_decision_probability(fit, score) == pytest.approx(score)


def test_beta_endpoint_application_uses_limits():
    interior = _manual_beta_fit(1.0, 1.0, 0.0)
    assert families.apply_beta_fixed_decision_probability(interior, 0.0) == 0.0
    assert families.apply_beta_fixed_decision_probability(interior, 1.0) == 1.0
    a0 = _manual_beta_fit(0.0, 2.0, 0.25)
    assert families.apply_beta_fixed_decision_probability(a0, 0.0) == pytest.approx(
        1.0 / (1.0 + math.exp(-0.25))
    )
    b0 = _manual_beta_fit(2.0, 0.0, -0.25)
    assert families.apply_beta_fixed_decision_probability(b0, 1.0) == pytest.approx(
        1.0 / (1.0 + math.exp(0.25))
    )
    corner = _manual_beta_fit(0.0, 0.0, 0.5)
    assert families.apply_beta_fixed_decision_probability(corner, 0.0) == pytest.approx(
        1.0 / (1.0 + math.exp(-0.5))
    )
    assert families.apply_beta_fixed_decision_probability(corner, 1.0) == pytest.approx(
        1.0 / (1.0 + math.exp(-0.5))
    )


def test_beta_application_outside_source_support_is_not_truncated():
    fit = families.fit_beta_fixed_decision_probability(INTERIOR_SCORES, INTERIOR_LABELS)
    lowest = families.apply_beta_fixed_decision_probability(fit, min(INTERIOR_SCORES))
    highest = families.apply_beta_fixed_decision_probability(fit, max(INTERIOR_SCORES))
    assert families.apply_beta_fixed_decision_probability(fit, 0.001) != lowest
    assert families.apply_beta_fixed_decision_probability(fit, 0.999) != highest


def test_beta_monotonicity_over_grid():
    for scores, labels in (
        (INTERIOR_SCORES, INTERIOR_LABELS),
        (A0_SCORES, A0_LABELS),
        (B0_SCORES, B0_LABELS),
        (CORNER_SCORES, CORNER_LABELS),
    ):
        fit = families.fit_beta_fixed_decision_probability(scores, labels)
        values = [families.apply_beta_fixed_decision_probability(fit, s) for s in _grid()]
        assert _max_monotonicity_violation(values) == 0.0


# --------------------------------------------------------------------------
# Numerical audits
# --------------------------------------------------------------------------


def test_beta_analytic_gradient_matches_central_finite_difference():
    rows = _rows([0.05, 0.18, 0.33, 0.41, 0.57, 0.72, 0.88], [0, 1, 0, 1, 1, 0, 1])
    step = 1e-5
    for a, b, c in ((1.0, 1.0, 0.0), (0.4, 1.7, -0.6), (2.5, 0.3, 1.1)):
        analytic = families.beta_gradient(rows, a, b, c)
        numeric = []
        for position in range(3):
            plus = [a, b, c]
            minus = [a, b, c]
            plus[position] += step
            minus[position] -= step
            numeric.append(
                (
                    families.beta_objective(rows, *plus)
                    - families.beta_objective(rows, *minus)
                )
                / (2.0 * step)
            )
        discrepancy = max(
            abs(left - right) for left, right in zip(analytic, numeric, strict=True)
        )
        assert discrepancy <= MAX_GRADIENT_DISCREPANCY


def test_beta_alternative_start_audit_finds_a_single_optimum():
    for scores, labels in (
        (INTERIOR_SCORES, INTERIOR_LABELS),
        (A0_SCORES, A0_LABELS),
        (B0_SCORES, B0_LABELS),
        (CORNER_SCORES, CORNER_LABELS),
    ):
        audit = families.beta_alternative_start_audit(scores, labels)
        assert audit["max_parameter_discrepancy"] <= MAX_ALTERNATIVE_START_DISCREPANCY
        assert audit["max_objective_discrepancy"] <= MAX_ALTERNATIVE_START_DISCREPANCY


def test_beta_alternative_start_audit_reports_the_symmetric_stress_spread():
    audit = families.beta_alternative_start_audit(SYMMETRIC_SCORES, SYMMETRIC_LABELS)
    assert audit["active_face"] == families.FACE_INTERIOR
    # The objective is flat to machine precision while the raw parameters are only
    # identified to the conditioning of the ``a - b`` direction.  This is a
    # SYMMETRIC NUMERICAL-CONDITIONING STRESS CASE, not a second optimum.
    assert audit["max_objective_discrepancy"] <= 1e-15
    assert audit["max_parameter_discrepancy"] > MAX_ALTERNATIVE_START_DISCREPANCY


def _beta_alternative_start_records(scores, labels):
    """Solve the frozen active face from every deterministic alternative start."""
    rows = _rows(scores, labels)
    fit = families.fit_beta_fixed_decision_probability(scores, labels)
    records = []
    for start in families._ALTERNATIVE_STARTS[fit.active_face]:
        candidate = families._solve_face(fit.active_face, rows, start)
        a, b, c = candidate["parameters"]
        records.append(
            {
                "start": tuple(start),
                "parameters": (a, b, c),
                "objective": candidate["objective"],
                "kkt_residual": candidate["kkt_residual"],
                "accepted": candidate["accepted"],
                "predictions": [
                    families.apply_beta_fixed_decision_probability(
                        _manual_beta_fit(a, b, c), score
                    )
                    for score in _grid()
                ],
            }
        )
    return fit, records


def test_beta_symmetric_stress_case_diagnostics():
    """Strict-convexity, Hessian and convergence diagnostics for the stress case.

    The objective is exactly invariant under ``(a, b, c) -> (b, a, -c)``, so the
    unique constrained optimum has ``a == b`` and ``c == 0``.  The transformed
    design ``[ln(s), -ln(1 - s), 1]`` has full column rank, which makes the finite
    Bernoulli-logistic objective strictly convex on the feasible quadrant; the
    ``a - b`` direction is merely ill-conditioned, so raw-coordinate spread across
    alternative starts is numerical convergence variation, not a second optimum.
    """
    fit, records = _beta_alternative_start_records(SYMMETRIC_SCORES, SYMMETRIC_LABELS)
    assert fit.active_face == families.FACE_INTERIOR
    # The production fixed-start accepted solution meets the frozen acceptance rule.
    assert fit.kkt_residual <= families.KKT_ACCEPTANCE_TOL

    rows = _rows(SYMMETRIC_SCORES, SYMMETRIC_LABELS)
    design = numpy.array(
        [[math.log(s), -math.log1p(-s), 1.0] for s, _ in rows], dtype=float
    )
    assert int(numpy.linalg.matrix_rank(design)) == 3

    probabilities = numpy.array(
        [families.apply_beta_fixed_decision_probability(fit, s) for s, _ in rows],
        dtype=float,
    )
    weights = probabilities * (1.0 - probabilities)
    hessian = (design.T @ numpy.diag(weights) @ design) / len(rows)
    assert float(numpy.linalg.eigvalsh(hessian).min()) > 0.0

    # Every deterministic alternative start lands on the same objective value.
    objectives = [record["objective"] for record in records]
    assert max(objectives) - min(objectives) <= SYMMETRIC_MAX_OBJECTIVE_SPREAD

    # Every start the frozen acceptance rule admits satisfies KKT <= 1e-10.
    accepted = [record for record in records if record["accepted"]]
    assert accepted
    for record in accepted:
        assert record["kkt_residual"] <= families.KKT_ACCEPTANCE_TOL

    # Accepted solutions agree across the whole dense prediction grid.
    for left, right in itertools.combinations(accepted, 2):
        spread = max(
            abs(p - q) for p, q in zip(left["predictions"], right["predictions"], strict=True)
        )
        assert spread <= SYMMETRIC_MAX_PREDICTION_SPREAD

    # Raw-coordinate convergence bound on the ill-conditioned symmetric fixture.
    # Under the frozen solver settings two of the four deterministic starts stall
    # above the production acceptance tolerance while the objective is identical
    # to machine precision; the solver contract is deliberately left unchanged.
    assert max(record["kkt_residual"] for record in records) <= SYMMETRIC_MAX_START_KKT


def test_beta_serialization_determinism():
    for scores, labels in (
        (INTERIOR_SCORES, INTERIOR_LABELS),
        (A0_SCORES, A0_LABELS),
        (B0_SCORES, B0_LABELS),
        (CORNER_SCORES, CORNER_LABELS),
    ):
        first = families.fit_beta_fixed_decision_probability(scores, labels)
        second = families.fit_beta_fixed_decision_probability(scores, labels)
        assert canonical_json(first.state_payload()) == canonical_json(second.state_payload())
        assert first.state_fingerprint() == second.state_fingerprint()


# --------------------------------------------------------------------------
# Source-level and boundary guards
# --------------------------------------------------------------------------


def test_implementation_source_contains_no_clipping_logic():
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert FORBIDDEN_SOURCE_PATTERN.search(source) is None


def test_core_calibration_module_still_has_no_scipy_or_numpy_import():
    source = CORE_CALIBRATION.read_text(encoding="utf-8")
    assert "scipy" not in source
    assert "numpy" not in source


def test_solver_settings_are_deterministic_and_tolerance_derived():
    assert families._BFGS_OPTIONS["gtol"] == families.KKT_ACCEPTANCE_TOL / 100.0
    assert families._BFGS_OPTIONS["maxiter"] == 5000
