"""R4 calibration-family semantic audit (SYNTHETIC ONLY; no study fitting).

This script is a SEMANTIC AUDIT harness, not a production calibrator. It:

* re-verifies the four frozen R3 procedure identities (P-low, P-historical,
  L-low, L-historical) against ``r3_protocol_design.json``;
* builds the canonical candidate semantic payloads for the two R4
  family-extension procedures ``I-isotonic`` and ``B-beta`` and fingerprints
  them;
* evaluates manually specified maps and mathematical invariants on synthetic
  arrays only.

It is NOT a production implementation of any calibrator. It never imports
torch/transformers, never touches a GPU, never loads a model, never reads a
study-dataset row (MMLU / HellaSwag / MedMCQA), and never fits any calibrator
on real measurement scores. The tiny isotonic routine below is a deterministic
oracle used solely for synthetic contract tests; it must not be promoted to a
production fitter. No beta optimizer is implemented here at all: the declared
beta map is probed with manually supplied parameters, while the beta fitting
eligibility and failure rules (endpoint, single class, insufficient exact
distinct scores, increasing monotone separation, and the deliberate
non-treatment of reversed orientation) are audited as pure predicates.

No output is a scientific result: no Brier, no LogLoss, no transport outcome,
no predictor outcome.
"""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from probvenance.fingerprint import fingerprint

HARNESS_DIR = Path(__file__).resolve().parent
R3_DESIGN_PATH = HARNESS_DIR / "r3_protocol_design.json"
CANDIDATE_JSON_PATH = HARNESS_DIR / "R4_CALIBRATION_FAMILY_SEMANTIC_CANDIDATE.json"

CANDIDATE_ARTIFACT_TYPE = "r4-calibration-family-semantic-candidate"
CANDIDATE_ARTIFACT_VERSION = 1
CANDIDATE_STATUS = (
    "SEMANTIC CANDIDATE / NOT FROZEN / NO STUDY FITTING / NO EXECUTION AUTHORIZATION"
)

R3_EXPECTED_FINGERPRINTS: dict[str, str] = {
    "P-low": "7a8e13d51e131f2102cca4e00b172c8bbb2eb49e591acd3746aeb64d003c8857",
    "P-historical": "a44e9217dd43e5e29d859c8dd2dc510a5876db4d46a8e0cc2fd4f1df3121a423",
    "L-low": "91d7d506275aade7d4676c39722ac2c4d975de7967a25a808395c056307ad619",
    "L-historical": "23ec12bbf4a809ba2f419491df80d1f228d3fd778d848115839aab3697f9dd58",
}

FITTING_DATA_PROTOCOL_ID = "paired-frozen-decision-train"
FITTING_DATA_PROTOCOL_VERSION = 1
SELECTION_RULE_ID = "fixed-panel-no-selection"
SELECTION_RULE_VERSION = 1
FAILURE_RULE_ID = "structural-numerical-contract-violation"
FAILURE_RULE_VERSION = 1


class SemanticAuditError(RuntimeError):
    """Raised when a synthetic semantic invariant is violated."""


# --------------------------------------------------------------------------- #
# Candidate semantic payloads
# --------------------------------------------------------------------------- #


def isotonic_candidate_payload() -> dict[str, Any]:
    """Canonical candidate semantic identity of ``I-isotonic``.

    Input domain is the raw fixed-decision probability in ``[0, 1]``. The fit
    is the non-decreasing empirical least-squares step function obtained by
    exact-score aggregation followed by weighted PAVA, with unit item weights,
    no regularization, and no hyperparameter. Application inside the observed
    source TRAIN range is piecewise-linear between the fitted threshold points;
    outside it the nearest fitted boundary value is returned. Exact scores
    ``0`` and ``1`` are ordinary legal inputs.
    """
    return {
        "label": "I-isotonic",
        "procedure_id": "r4-procedure-I-isotonic",
        "procedure_version": 1,
        "family_id": "monotone-isotonic-fixed-decision-probability",
        "family_version": 1,
        "feature_id": "identity-raw-probability",
        "feature_version": 1,
        "objective_id": "mean-squared-error",
        "objective_version": 1,
        "regularization_rule_id": "no-regularization",
        "regularization_rule_version": 1,
        "l2_strength": None,
        "parameter_constraints_id": "non-decreasing-step-function",
        "parameter_constraints_version": 1,
        "monotone_direction": "increasing",
        "hyperparameter_rule_id": "no-hyperparameter",
        "hyperparameter_rule_version": 1,
        "tie_policy_id": "exact-score-aggregation-weighted-pava",
        "tie_policy_version": 1,
        "interpolation_policy_id": "piecewise-linear-between-thresholds",
        "interpolation_policy_version": 1,
        "endpoint_policy_id": "exact-raw-probability-accepted",
        "endpoint_policy_version": 1,
        "out_of_source_support_policy_id": "nearest-endpoint-constant-extension",
        "out_of_source_support_policy_version": 1,
        "fitting_data_protocol_id": FITTING_DATA_PROTOCOL_ID,
        "fitting_data_protocol_version": FITTING_DATA_PROTOCOL_VERSION,
        "selection_rule_id": SELECTION_RULE_ID,
        "selection_rule_version": SELECTION_RULE_VERSION,
        "failure_rule_id": FAILURE_RULE_ID,
        "failure_rule_version": FAILURE_RULE_VERSION,
    }


def beta_candidate_payload() -> dict[str, Any]:
    """Canonical candidate semantic identity of ``B-beta``.

    Interior map is ``f(s) = sigmoid(a * ln(s) - b * ln(1 - s) + c)`` with the
    monotonicity constraints ``a >= 0`` and ``b >= 0``. The fitting objective is
    the mean Bernoulli negative log-likelihood with no regularization and no
    hyperparameter. An exact TRAIN endpoint score (``0`` or ``1``) makes the
    fitting block ``INELIGIBLE_ENDPOINT``: the log features are not finite
    there and no epsilon substitution is permitted. A successfully fitted
    finite map is extended to the endpoints by its exact mathematical limits
    and is applied parametrically across the whole interior ``(0, 1)`` without
    clipping to the observed source TRAIN support.

    Fitting eligibility is completed by two further hard rules. First, the
    three-parameter design ``(1, ln s, -ln(1 - s))`` must be identifiable, so a
    fitting block with fewer than three exact distinct interior scores is
    ``BETA_FIT_INELIGIBLE_INSUFFICIENT_DISTINCT_SCORES``; the family is never
    silently reduced to a two-parameter beta, never has ``a`` or ``b`` fixed,
    and never falls back to logistic regression. Distinctness is exact binary64
    score equality: no tolerance merging, no rounding, no binning, no epsilon.
    Second, because the declared family is constrained to non-decreasing maps,
    an increasing monotone separation (``max{s : Y = 0} <= min{s : Y = 1}``)
    is ``BETA_FIT_INELIGIBLE_MONOTONE_SEPARATION``: an unregularized finite
    maximum-likelihood optimum is not guaranteed to exist there and no
    regularization rescue is applied. The reversed orientation
    (``max{s : Y = 1} <= min{s : Y = 0}``) is deliberately NOT that failure
    rule: it may still admit a finite boundary optimum with ``a = 0`` and/or
    ``b = 0`` and is left to the constrained optimizer. A successful fit is a
    unique finite constrained optimum with ``a >= 0`` and ``b >= 0``, accepted
    under the later frozen numerical KKT/convergence contract.
    """
    return {
        "label": "B-beta",
        "procedure_id": "r4-procedure-B-beta",
        "procedure_version": 1,
        "family_id": "full-monotone-beta-fixed-decision-probability",
        "family_version": 1,
        "feature_id": "log-odds-beta-pair",
        "feature_version": 1,
        "objective_id": "mean-bernoulli-nll",
        "objective_version": 1,
        "regularization_rule_id": "no-regularization",
        "regularization_rule_version": 1,
        "l2_strength": None,
        "parameter_constraints_id": "nonnegative-a-nonnegative-b",
        "parameter_constraints_version": 1,
        "monotone_direction": "increasing",
        "hyperparameter_rule_id": "no-hyperparameter",
        "hyperparameter_rule_version": 1,
        "train_endpoint_policy_id": "reject-exact-probability-endpoints",
        "train_endpoint_policy_version": 1,
        "application_endpoint_policy_id": "exact-limit-at-endpoints",
        "application_endpoint_policy_version": 1,
        "out_of_source_support_policy_id": "parametric-application-no-clipping",
        "out_of_source_support_policy_version": 1,
        "tie_policy_id": "not-applicable-continuous-map",
        "tie_policy_version": 1,
        "single_class_policy_id": "fit-ineligible-single-class",
        "single_class_policy_version": 1,
        "identifiability_rule_id": "full-three-parameter-design-no-reduction",
        "identifiability_rule_version": 1,
        "distinct_score_rule_id": "minimum-three-exact-distinct-interior-scores",
        "distinct_score_rule_version": 1,
        "distinct_score_equality_id": "exact-binary64-score-equality-no-tolerance",
        "distinct_score_equality_version": 1,
        "monotone_separation_rule_id": "reject-increasing-monotone-separation",
        "monotone_separation_rule_version": 1,
        "reversed_orientation_rule_id": "reversed-orientation-not-monotone-separation",
        "reversed_orientation_rule_version": 1,
        "finite_optimum_rule_id": (
            "unique-finite-constrained-optimum-under-frozen-kkt-convergence-contract"
        ),
        "finite_optimum_rule_version": 1,
        "fitting_data_protocol_id": FITTING_DATA_PROTOCOL_ID,
        "fitting_data_protocol_version": FITTING_DATA_PROTOCOL_VERSION,
        "selection_rule_id": SELECTION_RULE_ID,
        "selection_rule_version": SELECTION_RULE_VERSION,
        "failure_rule_id": FAILURE_RULE_ID,
        "failure_rule_version": FAILURE_RULE_VERSION,
    }


# --------------------------------------------------------------------------- #
# Numeric helpers
# --------------------------------------------------------------------------- #


def _sigmoid(z: float) -> float:
    if z >= 0.0:
        return 1.0 / (1.0 + math.exp(-z))
    exp_z = math.exp(z)
    return exp_z / (1.0 + exp_z)


def require_probability(value: float) -> float:
    """Validate a finite probability in ``[0, 1]`` (exact endpoints allowed)."""
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise SemanticAuditError(f"score must be a finite value in [0, 1], got {value!r}")
    return value


# --------------------------------------------------------------------------- #
# I-isotonic synthetic oracle
# --------------------------------------------------------------------------- #


def _aggregate_exact_scores(
    scores: Sequence[float], labels: Sequence[float]
) -> list[tuple[float, float, int]]:
    """Aggregate exact equal scores into ``(score, mean_label, count)``.

    Row order is irrelevant because rows are bucketed by exact score value.
    """
    buckets: dict[float, list[float]] = {}
    for score, label in zip(scores, labels, strict=True):
        entry = buckets.setdefault(require_probability(score), [0.0, 0.0])
        entry[0] += label
        entry[1] += 1.0
    return [
        (score, buckets[score][0] / buckets[score][1], int(buckets[score][1]))
        for score in sorted(buckets)
    ]


def _weighted_pava(
    aggregated: Sequence[tuple[float, float, int]],
) -> list[tuple[float, float]]:
    """Weighted pool-adjacent-violators over ascending unique scores.

    Returns the fitted threshold points ``(score, fitted_value)`` in ascending
    score order. Integer counts are the block weights; every item has weight 1.
    """
    blocks: list[list[Any]] = []
    for score, mean, weight in aggregated:
        blocks.append([mean * weight, float(weight), [score]])
        while len(blocks) >= 2 and blocks[-2][0] / blocks[-2][1] > blocks[-1][0] / blocks[-1][1]:
            right = blocks.pop()
            left = blocks.pop()
            blocks.append([left[0] + right[0], left[1] + right[1], left[2] + right[2]])
    thresholds: list[tuple[float, float]] = []
    for weighted_sum, weight, scores in blocks:
        value = weighted_sum / weight
        thresholds.extend((score, value) for score in scores)
    thresholds.sort(key=lambda point: point[0])
    return thresholds


def isotonic_fit(
    scores: Sequence[float], labels: Sequence[float]
) -> list[tuple[float, float]]:
    """Deterministic isotonic oracle: aggregate exact scores, then weighted PAVA."""
    if not scores:
        raise SemanticAuditError("isotonic fitting set must not be empty")
    for label in labels:
        if label not in (0.0, 1.0):
            raise SemanticAuditError(f"isotonic labels must be binary 0/1, got {label!r}")
    return _weighted_pava(_aggregate_exact_scores(scores, labels))


def isotonic_apply(thresholds: Sequence[tuple[float, float]], score: float) -> float:
    """Apply the fitted isotonic map with boundary extension and linear interior."""
    require_probability(score)
    if score <= thresholds[0][0]:
        return thresholds[0][1]
    if score >= thresholds[-1][0]:
        return thresholds[-1][1]
    for index in range(1, len(thresholds)):
        low_score, low_value = thresholds[index - 1]
        high_score, high_value = thresholds[index]
        if score <= high_score:
            if high_score == low_score:
                return high_value
            fraction = (score - low_score) / (high_score - low_score)
            return low_value + fraction * (high_value - low_value)
    return thresholds[-1][1]


# --------------------------------------------------------------------------- #
# B-beta declared map
# --------------------------------------------------------------------------- #


def require_beta_parameters(a: float, b: float, c: float) -> tuple[float, float, float]:
    """Validate the declared monotonicity constraints ``a >= 0`` and ``b >= 0``."""
    for name, value in (("a", a), ("b", b), ("c", c)):
        if not math.isfinite(value):
            raise SemanticAuditError(f"beta parameter {name} must be finite, got {value!r}")
    if a < 0.0 or b < 0.0:
        raise SemanticAuditError(
            "beta parameters must satisfy a >= 0 and b >= 0 for a non-decreasing map, "
            f"got a={a!r}, b={b!r}"
        )
    return a, b, c


def beta_map(a: float, b: float, c: float, score: float) -> float:
    """Declared beta map with exact endpoint limits and no clipping."""
    require_beta_parameters(a, b, c)
    require_probability(score)
    if score == 0.0:
        return 0.0 if a > 0.0 else _sigmoid(c)
    if score == 1.0:
        return 1.0 if b > 0.0 else _sigmoid(c)
    return _sigmoid(a * math.log(score) - b * math.log(1.0 - score) + c)


def beta_objective(
    pairs: Sequence[tuple[float, float]], a: float, b: float, c: float
) -> float:
    """Mean Bernoulli NLL of manually supplied parameters on interior scores."""
    require_beta_parameters(a, b, c)
    if not pairs:
        raise SemanticAuditError("beta objective requires a non-empty fitting set")
    terms = []
    for score, label in pairs:
        require_probability(score)
        if score in (0.0, 1.0):
            raise SemanticAuditError(
                "INELIGIBLE_ENDPOINT: an exact TRAIN endpoint score has no finite "
                f"beta feature transform, got {score!r}"
            )
        if label not in (0.0, 1.0):
            raise SemanticAuditError(f"beta labels must be binary 0/1, got {label!r}")
        probability = beta_map(a, b, c, score)
        if label == 1.0:
            terms.append(-math.log(probability))
        else:
            terms.append(-math.log(1.0 - probability))
    return math.fsum(terms) / len(terms)


def beta_fit_eligibility(pairs: Sequence[tuple[float, float]]) -> str:
    """Return ``ELIGIBLE`` or the exact B-beta fitting ineligibility state.

    The ordered gates are: non-empty; finite probability-domain score; score
    strictly interior to ``(0, 1)`` (exact ``0``/``1`` is
    ``INELIGIBLE_ENDPOINT``); binary label; both classes present; at least three
    exact distinct interior scores; and no increasing monotone separation.
    Distinctness is exact binary64 equality. Every failure is returned as a
    state string; a structural contract violation raises instead.
    """
    if not pairs:
        raise SemanticAuditError("beta fitting set must not be empty")
    for score, _ in pairs:
        require_probability(score)
        if score in (0.0, 1.0):
            return "INELIGIBLE_ENDPOINT"
    for _, label in pairs:
        if label not in (0.0, 1.0):
            raise SemanticAuditError(f"beta labels must be binary 0/1, got {label!r}")
    negatives = [score for score, label in pairs if label == 0.0]
    positives = [score for score, label in pairs if label == 1.0]
    if not positives or not negatives:
        return "BETA_FIT_INELIGIBLE_SINGLE_CLASS"
    if len({score for score, _ in pairs}) < 3:
        return "BETA_FIT_INELIGIBLE_INSUFFICIENT_DISTINCT_SCORES"
    if max(negatives) <= min(positives):
        return "BETA_FIT_INELIGIBLE_MONOTONE_SEPARATION"
    return "ELIGIBLE"


# --------------------------------------------------------------------------- #
# Synthetic semantic probes
# --------------------------------------------------------------------------- #


def _isotonic_probes() -> dict[str, Any]:
    results: dict[str, Any] = {}

    increasing_scores = [0.1, 0.2, 0.3, 0.4, 0.5]
    increasing_labels = [0.0, 0.0, 1.0, 1.0, 1.0]
    increasing = isotonic_fit(increasing_scores, increasing_labels)
    results["strictly_increasing_distinct_scores"] = {
        "thresholds": [list(point) for point in increasing],
        "non_decreasing": all(
            increasing[i][1] <= increasing[i + 1][1] for i in range(len(increasing) - 1)
        ),
    }

    repeated_scores = [0.2, 0.2, 0.2, 0.6, 0.6]
    repeated_labels = [1.0, 0.0, 1.0, 1.0, 1.0]
    repeated = isotonic_fit(repeated_scores, repeated_labels)
    results["repeated_exact_scores"] = {
        "thresholds": [list(point) for point in repeated],
        "first_threshold_is_exact_mean": math.isclose(repeated[0][1], 2.0 / 3.0, rel_tol=1e-12),
    }

    violating_scores = [0.1, 0.2, 0.3, 0.4]
    violating_labels = [1.0, 0.0, 0.0, 0.0]
    violating = isotonic_fit(violating_scores, violating_labels)
    results["monotonicity_violation_requires_pooling"] = {
        "thresholds": [list(point) for point in violating],
        "pooled_into_single_value": len({value for _, value in violating}) == 1,
    }

    flat = isotonic_fit([0.4, 0.4, 0.4], [1.0, 0.0, 1.0])
    results["all_scores_equal"] = {
        "thresholds": [list(point) for point in flat],
        "constant_at_positive_fraction": math.isclose(flat[0][1], 2.0 / 3.0, rel_tol=1e-12),
    }

    all_zero = isotonic_fit([0.2, 0.5, 0.9], [0.0, 0.0, 0.0])
    results["all_labels_zero"] = {
        "thresholds": [list(point) for point in all_zero],
        "constant_zero": all(value == 0.0 for _, value in all_zero),
    }

    all_one = isotonic_fit([0.2, 0.5, 0.9], [1.0, 1.0, 1.0])
    results["all_labels_one"] = {
        "thresholds": [list(point) for point in all_one],
        "constant_one": all(value == 1.0 for _, value in all_one),
    }

    thresholds = isotonic_fit([0.3, 0.6], [0.0, 1.0])
    results["boundary_extension_and_interior"] = {
        "thresholds": [list(point) for point in thresholds],
        "below_train_min_constant": isotonic_apply(thresholds, 0.1) == thresholds[0][1],
        "above_train_max_constant": isotonic_apply(thresholds, 0.9) == thresholds[-1][1],
        "exact_input_zero_constant": isotonic_apply(thresholds, 0.0) == thresholds[0][1],
        "exact_input_one_constant": isotonic_apply(thresholds, 1.0) == thresholds[-1][1],
        "interior_is_linear_midpoint": math.isclose(
            isotonic_apply(thresholds, 0.45), 0.5, rel_tol=1e-12
        ),
        "no_parametric_extrapolation": isotonic_apply(thresholds, 0.1) != 0.1,
    }

    grid = [index / 100.0 for index in range(101)]
    applied = [isotonic_apply(increasing, score) for score in grid]
    results["grid_monotonicity_and_range"] = {
        "non_decreasing_on_grid": all(
            applied[i] <= applied[i + 1] for i in range(len(applied) - 1)
        ),
        "output_within_unit_interval": all(0.0 <= value <= 1.0 for value in applied),
    }
    return results


def _beta_probes() -> dict[str, Any]:
    results: dict[str, Any] = {}

    identity_grid = [0.05, 0.25, 0.5, 0.75, 0.95]
    identity_errors = [
        abs(beta_map(1.0, 1.0, 0.0, score) - score) for score in identity_grid
    ]
    results["identity_map"] = {
        "max_abs_error": max(identity_errors),
        "identity_holds": max(identity_errors) < 1e-12,
    }

    grid = [index / 200.0 for index in range(1, 200)]
    monotone_ok = True
    for a, b, c in ((1.5, 0.7, -0.2), (0.0, 2.0, 0.4), (3.0, 0.0, -1.0), (0.0, 0.0, 0.5)):
        values = [beta_map(a, b, c, score) for score in grid]
        monotone_ok = monotone_ok and all(
            values[i] <= values[i + 1] for i in range(len(values) - 1)
        )
    results["monotonicity_under_constraints"] = {"non_decreasing": monotone_ok}

    results["endpoint_limits"] = {
        "a_positive_maps_zero_to_zero": beta_map(1.0, 1.0, 0.0, 0.0) == 0.0,
        "b_positive_maps_one_to_one": beta_map(1.0, 1.0, 0.0, 1.0) == 1.0,
        "a_zero_maps_zero_to_sigmoid_c": beta_map(0.0, 2.0, 0.4, 0.0) == _sigmoid(0.4),
        "b_zero_maps_one_to_sigmoid_c": beta_map(3.0, 0.0, -1.0, 1.0) == _sigmoid(-1.0),
    }

    train_min, train_max = 0.2, 0.8
    low_inside = beta_map(1.0, 1.0, 0.0, train_min)
    low_outside = beta_map(1.0, 1.0, 0.0, 0.05)
    high_outside = beta_map(1.0, 1.0, 0.0, 0.95)
    results["parametric_extrapolation_no_clipping"] = {
        "train_range": [train_min, train_max],
        "value_at_train_min": low_inside,
        "value_below_train_min": low_outside,
        "value_above_train_max": high_outside,
        "no_clip_below": low_outside != low_inside,
        "no_clip_above": high_outside != beta_map(1.0, 1.0, 0.0, train_max),
        "equals_identity_outside": abs(low_outside - 0.05) < 1e-12
        and abs(high_outside - 0.95) < 1e-12,
    }

    rejected = []
    for a, b in ((-0.1, 1.0), (1.0, -0.1)):
        try:
            beta_map(a, b, 0.0, 0.5)
        except SemanticAuditError:
            rejected.append([a, b])
    results["negative_parameters_rejected"] = {
        "rejected_pairs": rejected,
        "all_rejected": len(rejected) == 2,
    }

    valid_pairs = [(0.3, 1.0), (0.5, 0.0), (0.7, 1.0), (0.9, 0.0)]
    results["objective_finite_for_interior_inputs"] = {
        "objective": beta_objective(valid_pairs, 1.0, 1.0, 0.0),
        "finite": math.isfinite(beta_objective(valid_pairs, 1.0, 1.0, 0.0)),
    }

    endpoint_states = []
    for score in (0.0, 1.0):
        try:
            beta_objective([(score, 1.0)], 1.0, 1.0, 0.0)
        except SemanticAuditError as error:
            endpoint_states.append({"score": score, "state": str(error).split(":")[0]})
    results["train_endpoint_ineligible"] = {
        "states": endpoint_states,
        "both_ineligible": len(endpoint_states) == 2,
    }

    results["single_class_rule"] = {
        "all_zero": beta_fit_eligibility([(0.3, 0.0), (0.6, 0.0)]),
        "all_one": beta_fit_eligibility([(0.3, 1.0), (0.6, 1.0)]),
        "mixed_two_distinct_scores": beta_fit_eligibility([(0.3, 0.0), (0.6, 1.0)]),
    }

    results["insufficient_distinct_scores"] = {
        "one_distinct_interior_score": beta_fit_eligibility([(0.5, 0.0), (0.5, 1.0)]),
        "two_distinct_interior_scores": beta_fit_eligibility([(0.4, 0.0), (0.6, 1.0)]),
        "three_distinct_interior_scores_eligible": beta_fit_eligibility(
            [(0.2, 0.0), (0.5, 1.0), (0.8, 0.0)]
        ),
    }

    increasing_complete = [(0.1, 0.0), (0.2, 0.0), (0.8, 1.0), (0.9, 1.0)]
    increasing_quasi = [(0.2, 0.0), (0.5, 0.0), (0.5, 1.0), (0.8, 1.0)]
    reversed_orientation = [(0.1, 1.0), (0.2, 1.0), (0.8, 0.0), (0.9, 0.0)]
    results["monotone_separation"] = {
        "increasing_complete_separation": beta_fit_eligibility(increasing_complete),
        "increasing_quasi_separation_shared_boundary_score": beta_fit_eligibility(
            increasing_quasi
        ),
        "reversed_orientation_state": beta_fit_eligibility(reversed_orientation),
        "reversed_orientation_not_pre_rejected": (
            beta_fit_eligibility(reversed_orientation) == "ELIGIBLE"
        ),
        "interleaved_labels_eligible": beta_fit_eligibility(valid_pairs) == "ELIGIBLE",
    }

    results["eligibility_gate_order"] = {
        "endpoint_before_single_class": beta_fit_eligibility([(0.0, 0.0), (0.0, 0.0)]),
        "single_class_before_insufficient_support": beta_fit_eligibility(
            [(0.3, 0.0), (0.6, 0.0)]
        ),
        "insufficient_support_before_separation": beta_fit_eligibility(
            [(0.4, 0.0), (0.6, 1.0)]
        ),
    }
    return results


def _row_order_determinism() -> dict[str, Any]:
    scores = [0.7, 0.2, 0.2, 0.9, 0.4, 0.2, 0.4]
    labels = [1.0, 0.0, 1.0, 1.0, 0.0, 0.0, 1.0]
    orderings = {
        "as_given": list(range(len(scores))),
        "reversed": list(reversed(range(len(scores)))),
        "rotated": [3, 4, 5, 6, 0, 1, 2],
    }
    reference: list[tuple[float, float]] | None = None
    predictions: dict[str, list[float]] = {}
    beta_eligibility: dict[str, str] = {}
    identical = True
    for name, order in orderings.items():
        permuted_scores = [scores[index] for index in order]
        permuted_labels = [labels[index] for index in order]
        thresholds = isotonic_fit(permuted_scores, permuted_labels)
        beta_eligibility[name] = beta_fit_eligibility(
            list(zip(permuted_scores, permuted_labels, strict=True))
        )
        if reference is None:
            reference = thresholds
        elif thresholds != reference:
            identical = False
        predictions[name] = [
            isotonic_apply(thresholds, score) for score in (0.0, 0.2, 0.45, 0.9, 1.0)
        ]
    payload_fingerprints = {
        name: fingerprint(isotonic_candidate_payload()) for name in orderings
    }
    return {
        "thresholds_identical_across_orderings": identical,
        "thresholds": [list(point) for point in (reference or [])],
        "predictions": predictions,
        "beta_eligibility": beta_eligibility,
        "beta_eligibility_identical": len(set(beta_eligibility.values())) == 1,
        "candidate_fingerprint_identical": len(set(payload_fingerprints.values())) == 1,
    }


# --------------------------------------------------------------------------- #
# R3 continuity verification
# --------------------------------------------------------------------------- #


def _r3_continuity() -> dict[str, Any]:
    design = json.loads(R3_DESIGN_PATH.read_text(encoding="utf-8"))
    entries = []
    all_match = True
    for entry in design["procedures"]:
        payload = entry["payload"]
        label = payload["label"]
        actual = fingerprint(payload)
        expected = R3_EXPECTED_FINGERPRINTS[label]
        match = actual == expected and actual == entry["fingerprint"]
        all_match = all_match and match
        entries.append(
            {
                "label": label,
                "expected_fingerprint": expected,
                "declared_fingerprint": entry["fingerprint"],
                "actual_fingerprint": actual,
                "match": match,
                "payload": payload,
            }
        )
    return {
        "design_path": str(R3_DESIGN_PATH.relative_to(HARNESS_DIR.parent.parent)),
        "protocol_id": design["protocol_id"],
        "protocol_fingerprint": design["protocol_fingerprint"],
        "procedures": entries,
        "all_match": all_match,
    }


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def build_candidate() -> dict[str, Any]:
    """Build the full candidate artifact payload (no fingerprint yet)."""
    r3_continuity = _r3_continuity()
    if not r3_continuity["all_match"]:
        raise SemanticAuditError("R3 procedure identity mismatch; TASK STOP")

    isotonic_payload = isotonic_candidate_payload()
    beta_payload = beta_candidate_payload()

    return {
        "artifact_type": CANDIDATE_ARTIFACT_TYPE,
        "artifact_version": CANDIDATE_ARTIFACT_VERSION,
        "status": CANDIDATE_STATUS,
        "r3_continuity": r3_continuity,
        "candidate_procedures": [
            {
                "label": "I-isotonic",
                "fingerprint": fingerprint(isotonic_payload),
                "payload": isotonic_payload,
            },
            {
                "label": "B-beta",
                "fingerprint": fingerprint(beta_payload),
                "payload": beta_payload,
            },
        ],
        "semantic_probes": {
            "isotonic": _isotonic_probes(),
            "beta": _beta_probes(),
            "row_order_determinism": _row_order_determinism(),
        },
    }


def main() -> int:
    candidate = build_candidate()
    canonical = json.dumps(candidate, ensure_ascii=False, sort_keys=True, indent=2)
    CANDIDATE_JSON_PATH.write_text(canonical + "\n", encoding="utf-8")
    labels = [entry["label"] for entry in candidate["candidate_procedures"]]
    print(f"wrote {CANDIDATE_JSON_PATH.name}")
    print(f"r3_continuity_all_match={candidate['r3_continuity']['all_match']}")
    for entry in candidate["candidate_procedures"]:
        print(f"{entry['label']} fingerprint={entry['fingerprint']}")
    print(f"candidate_labels={labels}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
