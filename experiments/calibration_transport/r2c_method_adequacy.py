"""R2C calibration-method adequacy sensitivity (research-only, exploratory).

R2C answers exactly one question about the already-frozen R2B evidence: whether
the observed native-calibration degradation (every fitted native calibrator had
a HIGHER held-out Brier than its raw measurement) is specific to the current
``raw-p logistic + lambda = 0.01`` configuration, or whether it also appears
under a small, pre-declared sensitivity grid.

It is analysis-only. It never loads a model, never touches a GPU, never uses the
network, and never re-collects a single measurement. Everything is derived from
one committed R2B raw artifact.

Two fitted families are compared, both reusing the production numerical kernel
``probvenance.calibration._solve_l2_logistic`` and ``_stable_sigmoid``:

- **Family P** (``research-l2-logistic-fixed-decision-probability`` v1): the
  existing ``q(p) = sigmoid(a * p + b)`` raw-probability feature.
- **Family L** (``research-l2-logistic-logit-fixed-decision-probability`` v1):
  ``q(p) = sigmoid(a * logit(p) + b)``. The identity map is a member of this
  function family (``a = 1, b = 0``), but the L2 penalty does not specially
  prefer it.

R2C selects no winner, recommends no method, and does not authorize R3. It is
deliberately NOT confirmatory: it reuses R2B held-out data after R2B results
were already seen.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from probvenance.calibration import _solve_l2_logistic, _stable_sigmoid
from probvenance.fingerprint import fingerprint

_HARNESS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _HARNESS_DIR.parent.parent

DEFAULT_DESIGN_PATH = _HARNESS_DIR / "r2c_method_adequacy_design.json"


def _load_sibling(name: str) -> Any:
    module = sys.modules.get(name)
    if module is not None:
        return module
    spec = importlib.util.spec_from_file_location(name, _HARNESS_DIR / f"{name}.py")
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load {name}.py from {_HARNESS_DIR}")
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


analysis = _load_sibling("analysis")
r2b_plan = _load_sibling("r2b_plan")
r2b_stability = _load_sibling("r2b_stability")
measurements = _load_sibling("measurements")
_integrity = analysis._integrity
Split = _integrity.Split
PairedFixedDecisionDataset = _integrity.PairedFixedDecisionDataset

R2C_ANALYSIS_ARTIFACT_TYPE = "calibration-transport-r2c-method-adequacy-analysis"
R2C_ANALYSIS_ARTIFACT_VERSION = 1
R2C_DESIGN_ARTIFACT_TYPE = "calibration-transport-r2c-method-adequacy-design"
R2C_DESIGN_ARTIFACT_VERSION = 1

ROUND_ID = "calibration-method-adequacy-sensitivity"
ROUND_VERSION = 1

FAMILY_P_ID = "research-l2-logistic-fixed-decision-probability"
FAMILY_P_VERSION = 1
FAMILY_L_ID = "research-l2-logistic-logit-fixed-decision-probability"
FAMILY_L_VERSION = 1
RAW_ID = "raw-identity"
RAW_VERSION = 1

FEATURE_RAW_ID = "identity-raw-probability"
FEATURE_RAW_VERSION = 1
FEATURE_LOGIT_ID = "exact-logit-probability"
FEATURE_LOGIT_VERSION = 1
ENDPOINT_POLICY_ID = "reject-exact-probability-endpoints"
ENDPOINT_POLICY_VERSION = 1
OBJECTIVE_ID = "mean-bernoulli-nll-plus-l2"
OBJECTIVE_VERSION = 1

TARGET_ID = "fixed-decision-correctness"
TARGET_VERSION = 1
INPUT_SCORE_ID = "fixed-decision-semantic-probability"
INPUT_SCORE_VERSION = 1

LAMBDA_GRID: tuple[float, ...] = (1e-06, 0.0001, 0.01, 0.1, 1.0)

PAIRED_TEST_BOOTSTRAP_PROTOCOL_ID = "sha256-r2c-paired-test-bootstrap"
PAIRED_TEST_BOOTSTRAP_PROTOCOL_VERSION = 1
PAIRED_TEST_BOOTSTRAP_REPLICATES = 2000

PAIRED_TRAIN_REFIT_BOOTSTRAP_PROTOCOL_ID = "sha256-r2c-paired-train-refit-bootstrap"
PAIRED_TRAIN_REFIT_BOOTSTRAP_PROTOCOL_VERSION = 1
PAIRED_TRAIN_REFIT_BOOTSTRAP_REPLICATES = 1000

PERCENTILE_RULE_ID = "nearest-rank-percentile"
PERCENTILE_RULE_VERSION = 1


class R2CError(RuntimeError):
    """Base class for R2C research-analysis contract violations."""


class ProbabilityEndpointError(R2CError):
    """Raised when a Family L feature would require an exact 0 or 1 probability."""


class DesignMismatchError(R2CError):
    """Raised when a design manifest disagrees with the frozen code contract."""


@dataclass(frozen=True)
class R2CMethodConfig:
    """One pre-declared fitted calibration configuration."""

    family_id: str
    family_version: int
    feature_id: str
    feature_version: int
    l2_strength: float
    label: str

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "family_id": self.family_id,
            "family_version": self.family_version,
            "feature_id": self.feature_id,
            "feature_version": self.feature_version,
            "l2_strength": self.l2_strength,
            "label": self.label,
        }


def method_configs() -> tuple[R2CMethodConfig, ...]:
    """The exact pre-declared grid: 5 Family P + 5 Family L configurations."""
    configs: list[R2CMethodConfig] = []
    for l2 in LAMBDA_GRID:
        configs.append(
            R2CMethodConfig(
                family_id=FAMILY_P_ID,
                family_version=FAMILY_P_VERSION,
                feature_id=FEATURE_RAW_ID,
                feature_version=FEATURE_RAW_VERSION,
                l2_strength=l2,
                label=f"P:{l2!r}",
            )
        )
    for l2 in LAMBDA_GRID:
        configs.append(
            R2CMethodConfig(
                family_id=FAMILY_L_ID,
                family_version=FAMILY_L_VERSION,
                feature_id=FEATURE_LOGIT_ID,
                feature_version=FEATURE_LOGIT_VERSION,
                l2_strength=l2,
                label=f"L:{l2!r}",
            )
        )
    return tuple(configs)


def _require_probability(value: Any) -> float:
    probability = float(value)
    if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
        raise R2CError(f"probability {probability!r} is not a finite value in [0, 1]")
    return probability


def _logit(probability: float) -> float:
    """Exact logit; endpoints are rejected, never clipped or smoothed."""
    value = _require_probability(probability)
    if value <= 0.0 or value >= 1.0:
        raise ProbabilityEndpointError(
            f"Family L requires an interior probability; got exact endpoint {value!r}. "
            "Endpoint policy 'reject-exact-probability-endpoints' v1 forbids clipping, "
            "epsilon substitution, and endpoint smoothing."
        )
    return math.log(value / (1.0 - value))


def feature_value(feature_id: str, probability: float) -> float:
    """Map a raw probability to the family's logistic feature."""
    if feature_id == FEATURE_RAW_ID:
        return _require_probability(probability)
    if feature_id == FEATURE_LOGIT_ID:
        return _logit(probability)
    raise R2CError(f"unknown feature id {feature_id!r}")


@dataclass(frozen=True)
class R2CFittedCalibrator:
    """A fitted research-only source-measurement calibrator (not a Phase 4C profile)."""

    method_id: str
    method_version: int
    feature_id: str
    feature_version: int
    endpoint_policy_id: str | None
    endpoint_policy_version: int | None
    l2_strength: float
    source_measurement: str
    plan_fingerprint: str
    training_item_ids: tuple[str, ...]
    slope: float
    intercept: float

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "method_id": self.method_id,
            "method_version": self.method_version,
            "feature_id": self.feature_id,
            "feature_version": self.feature_version,
            "endpoint_policy_id": self.endpoint_policy_id,
            "endpoint_policy_version": self.endpoint_policy_version,
            "l2_strength": self.l2_strength,
            "source_measurement": self.source_measurement,
            "target_id": TARGET_ID,
            "target_version": TARGET_VERSION,
            "input_score_id": INPUT_SCORE_ID,
            "input_score_version": INPUT_SCORE_VERSION,
            "plan_fingerprint": self.plan_fingerprint,
            "training_item_ids": list(self.training_item_ids),
            "slope": self.slope,
            "intercept": self.intercept,
        }

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.canonical_payload())

    def apply(self, probability: float) -> float:
        return _stable_sigmoid(
            self.slope * feature_value(self.feature_id, probability) + self.intercept
        )


def _fit_calibrator(
    *,
    config: R2CMethodConfig,
    source_measurement: str,
    training_rows: Sequence[tuple[str, float, float]],
    plan_fingerprint: str,
) -> R2CFittedCalibrator:
    """Deterministically fit one calibrator on one measurement's training rows.

    ``training_rows`` are ``(item_id, score, y)``; they are sorted by ``item_id``
    to make the arithmetic row-order independent.
    """
    ordered = sorted(training_rows, key=lambda row: row[0])
    rows = [(feature_value(config.feature_id, score), y) for _item_id, score, y in ordered]
    slope, intercept = _solve_l2_logistic(rows, config.l2_strength)
    if not (math.isfinite(slope) and math.isfinite(intercept)):
        raise R2CError(
            f"fit for {config.label} on {source_measurement} returned a non-finite parameter pair"
        )
    endpoint_policy_id: str | None = None
    endpoint_policy_version: int | None = None
    if config.feature_id == FEATURE_LOGIT_ID:
        endpoint_policy_id = ENDPOINT_POLICY_ID
        endpoint_policy_version = ENDPOINT_POLICY_VERSION
    return R2CFittedCalibrator(
        method_id=config.family_id,
        method_version=config.family_version,
        feature_id=config.feature_id,
        feature_version=config.feature_version,
        endpoint_policy_id=endpoint_policy_id,
        endpoint_policy_version=endpoint_policy_version,
        l2_strength=config.l2_strength,
        source_measurement=source_measurement,
        plan_fingerprint=plan_fingerprint,
        training_item_ids=tuple(row[0] for row in ordered),
        slope=slope,
        intercept=intercept,
    )


def _require_interior_endpoints(config: R2CMethodConfig, points: Sequence[Any]) -> None:
    """Fail closed if a Family L configuration would see an exact 0 or 1 score."""
    if config.feature_id != FEATURE_LOGIT_ID:
        return
    for point in points:
        for value in (point.score_a, point.score_b):
            if float(value) <= 0.0 or float(value) >= 1.0:
                raise ProbabilityEndpointError(
                    f"{config.label} requires interior probabilities, but item "
                    f"{point.item_id!r} has a score of exactly {float(value)!r}"
                )


def _brier_of(points: Sequence[Any], scores: Sequence[float]) -> float:
    pairs = [(float(score), float(point.y)) for point, score in zip(points, scores, strict=True)]
    return analysis.brier(pairs)


def _logloss_of(points: Sequence[Any], scores: Sequence[float]) -> float | None:
    pairs = [(float(score), float(point.y)) for point, score in zip(points, scores, strict=True)]
    return analysis.exact_logloss(pairs)


def _native_block(
    *,
    train_points: Sequence[Any],
    test_points: Sequence[Any],
    calibrator: R2CFittedCalibrator,
    train_scores: Sequence[float],
    test_scores: Sequence[float],
) -> dict[str, Any]:
    raw_train = [float(s) for s in train_scores]
    raw_test = [float(s) for s in test_scores]
    calibrated_train = [calibrator.apply(s) for s in train_scores]
    calibrated_test = [calibrator.apply(s) for s in test_scores]
    test_brier = _brier_of(test_points, calibrated_test)
    raw_test_brier = _brier_of(test_points, raw_test)
    train_brier = _brier_of(train_points, calibrated_train)
    raw_train_brier = _brier_of(train_points, raw_train)
    test_logloss = _logloss_of(test_points, calibrated_test)
    raw_test_logloss = _logloss_of(test_points, raw_test)
    train_logloss = _logloss_of(train_points, calibrated_train)
    raw_train_logloss = _logloss_of(train_points, raw_train)
    shifts = [abs(float(c) - float(s)) for c, s in zip(calibrated_test, raw_test, strict=True)]
    return {
        "test_brier": test_brier,
        "raw_test_brier": raw_test_brier,
        "native_minus_raw_brier": test_brier - raw_test_brier,
        "train_brier": train_brier,
        "raw_train_brier": raw_train_brier,
        "test_logloss": test_logloss,
        "raw_test_logloss": raw_test_logloss,
        "test_logloss_minus_raw": _finite_difference(test_logloss, raw_test_logloss),
        "train_logloss": train_logloss,
        "raw_train_logloss": raw_train_logloss,
        "map_shift_mean_abs_test": math.fsum(shifts) / len(shifts),
        "map_shift_max_abs_test": max(shifts),
    }


def _finite_difference(left: float | None, right: float | None) -> dict[str, Any]:
    if left is None or right is None:
        return {"state": "positive_infinity"}
    return {"state": "finite", "value": left - right}


def _per_item_native_diff(
    points: Sequence[Any], scores: Sequence[float], raw_scores: Sequence[float]
) -> list[float]:
    return [
        (float(cal) - float(point.y)) ** 2 - (float(raw) - float(point.y)) ** 2
        for point, cal, raw in zip(points, scores, raw_scores, strict=True)
    ]


def _per_item_transport_diff(
    points: Sequence[Any], left_scores: Sequence[float], right_scores: Sequence[float]
) -> list[float]:
    return [
        (float(left) - float(point.y)) ** 2 - (float(right) - float(point.y)) ** 2
        for point, left, right in zip(points, left_scores, right_scores, strict=True)
    ]


def _mean(values: Sequence[float]) -> float:
    return math.fsum(values) / len(values)


def _draw_matrix(
    *, protocol_id: str, protocol_version: int, replicates: int, draw: int, item_count: int
) -> list[list[int]]:
    return [
        [
            r2b_stability._draw_index(
                protocol_id=protocol_id,
                protocol_version=protocol_version,
                replicate=replicate,
                draw=position,
                item_count=item_count,
            )
            for position in range(draw)
        ]
        for replicate in range(replicates)
    ]


def _bootstrap_means(draws: Sequence[Sequence[int]], per_item: Sequence[float]) -> list[float]:
    return [_mean([per_item[index] for index in row]) for row in draws]


@dataclass(frozen=True)
class _ConfigComputation:
    config: R2CMethodConfig
    calibrator_cat: R2CFittedCalibrator
    calibrator_ovr: R2CFittedCalibrator
    native_cat_diff: list[float]
    native_ovr_diff: list[float]
    transport_cat_to_ovr_diff: list[float]
    transport_ovr_to_cat_diff: list[float]
    native_cat_point: float
    native_ovr_point: float
    transport_cat_to_ovr_point: float
    transport_ovr_to_cat_point: float


def _compute_config(
    config: R2CMethodConfig,
    *,
    train_points: Sequence[Any],
    test_points: Sequence[Any],
    plan_fingerprint: str,
) -> _ConfigComputation:
    _require_interior_endpoints(config, train_points)
    _require_interior_endpoints(config, test_points)
    train_rows = [(p.item_id, p.score_a, p.y) for p in train_points]
    train_rows_b = [(p.item_id, p.score_b, p.y) for p in train_points]
    g_cat = _fit_calibrator(
        config=config,
        source_measurement="CAT",
        training_rows=train_rows,
        plan_fingerprint=plan_fingerprint,
    )
    g_ovr = _fit_calibrator(
        config=config,
        source_measurement="OVR",
        training_rows=train_rows_b,
        plan_fingerprint=plan_fingerprint,
    )
    cat_test = [g_cat.apply(p.score_a) for p in test_points]
    ovr_test = [g_ovr.apply(p.score_b) for p in test_points]
    raw_a = [float(p.score_a) for p in test_points]
    raw_b = [float(p.score_b) for p in test_points]
    native_cat = _per_item_native_diff(test_points, cat_test, raw_a)
    native_ovr = _per_item_native_diff(test_points, ovr_test, raw_b)
    transport_cat_to_ovr = _per_item_transport_diff(test_points, cat_test, ovr_test)
    transport_ovr_to_cat = _per_item_transport_diff(test_points, ovr_test, cat_test)
    return _ConfigComputation(
        config=config,
        calibrator_cat=g_cat,
        calibrator_ovr=g_ovr,
        native_cat_diff=native_cat,
        native_ovr_diff=native_ovr,
        transport_cat_to_ovr_diff=transport_cat_to_ovr,
        transport_ovr_to_cat_diff=transport_ovr_to_cat,
        native_cat_point=_mean(native_cat),
        native_ovr_point=_mean(native_ovr),
        transport_cat_to_ovr_point=_mean(transport_cat_to_ovr),
        transport_ovr_to_cat_point=_mean(transport_ovr_to_cat),
    )


def _config_result_block(
    computation: _ConfigComputation,
    *,
    train_points: Sequence[Any],
    test_points: Sequence[Any],
) -> dict[str, Any]:
    config = computation.config
    g_cat = computation.calibrator_cat
    g_ovr = computation.calibrator_ovr
    matrix = analysis.brier_matrix(test_points, g_cat, g_ovr)
    logloss_matrix = analysis.logloss_matrix(test_points, g_cat, g_ovr)
    native_cat = _native_block(
        train_points=train_points,
        test_points=test_points,
        calibrator=g_cat,
        train_scores=[p.score_a for p in train_points],
        test_scores=[p.score_a for p in test_points],
    )
    native_ovr = _native_block(
        train_points=train_points,
        test_points=test_points,
        calibrator=g_ovr,
        train_scores=[p.score_b for p in train_points],
        test_scores=[p.score_b for p in test_points],
    )
    return {
        "label": config.label,
        "family_id": config.family_id,
        "family_version": config.family_version,
        "feature_id": config.feature_id,
        "feature_version": config.feature_version,
        "l2_strength": config.l2_strength,
        "native": {"cat": native_cat, "ovr": native_ovr},
        "transport": {
            "brier_matrix": matrix,
            "transport_delta_cat_to_ovr": matrix["delta_a_to_b"],
            "transport_delta_ovr_to_cat": matrix["delta_b_to_a"],
            "cat_to_ovr_minus_raw_ovr": matrix["fit_a_eval_b"] - matrix["raw_b"],
            "ovr_to_cat_minus_raw_cat": matrix["fit_b_eval_a"] - matrix["raw_a"],
        },
        "logloss_matrix": logloss_matrix,
        "calibrators": {
            "cat": _calibrator_block(g_cat),
            "ovr": _calibrator_block(g_ovr),
        },
    }


def _calibrator_block(calibrator: R2CFittedCalibrator) -> dict[str, Any]:
    return {
        "slope": calibrator.slope,
        "intercept": calibrator.intercept,
        "fingerprint": calibrator.fingerprint,
        "training_item_ids": list(calibrator.training_item_ids),
    }


def load_design(path: Path | str = DEFAULT_DESIGN_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def design_fingerprint(design: Mapping[str, Any]) -> str:
    return fingerprint(dict(design))


def validate_design(design: Mapping[str, Any]) -> None:
    """Fail closed if the committed design disagrees with the frozen code contract."""
    if design.get("artifact_type") != R2C_DESIGN_ARTIFACT_TYPE:
        raise DesignMismatchError("unexpected design artifact_type")
    if design.get("artifact_version") != R2C_DESIGN_ARTIFACT_VERSION:
        raise DesignMismatchError("unexpected design artifact_version")
    if design.get("round_id") != ROUND_ID or design.get("round_version") != ROUND_VERSION:
        raise DesignMismatchError("unexpected round id/version")
    if design.get("no_model_rerun") is not True:
        raise DesignMismatchError("design must declare no_model_rerun")
    grid = [float(value) for value in design.get("lambda_grid", [])]
    if grid != [float(value) for value in LAMBDA_GRID]:
        raise DesignMismatchError("design lambda_grid does not match the frozen grid")
    families = {entry["id"]: entry for entry in design.get("method_families", [])}
    if set(families) != {RAW_ID, FAMILY_P_ID, FAMILY_L_ID}:
        raise DesignMismatchError("design method_families do not match the frozen families")
    if families[FAMILY_L_ID]["feature"]["id"] != FEATURE_LOGIT_ID:
        raise DesignMismatchError("Family L feature id mismatch")
    if families[FAMILY_L_ID]["endpoint_policy"]["id"] != ENDPOINT_POLICY_ID:
        raise DesignMismatchError("Family L endpoint policy mismatch")
    test_bootstrap = design.get("paired_test_bootstrap", {})
    if test_bootstrap.get("protocol_id") != PAIRED_TEST_BOOTSTRAP_PROTOCOL_ID:
        raise DesignMismatchError("paired test bootstrap protocol mismatch")
    if int(test_bootstrap.get("replicates", -1)) != PAIRED_TEST_BOOTSTRAP_REPLICATES:
        raise DesignMismatchError("paired test bootstrap replicates mismatch")
    train_bootstrap = design.get("paired_train_refit_bootstrap", {})
    if train_bootstrap.get("protocol_id") != PAIRED_TRAIN_REFIT_BOOTSTRAP_PROTOCOL_ID:
        raise DesignMismatchError("paired train-refit bootstrap protocol mismatch")
    if int(train_bootstrap.get("replicates", -1)) != PAIRED_TRAIN_REFIT_BOOTSTRAP_REPLICATES:
        raise DesignMismatchError("paired train-refit bootstrap replicates mismatch")


def load_frozen_evidence(
    raw: Mapping[str, Any], *, cases_path: Path | str | None = None
) -> tuple[Any, Any, tuple[Any, ...], tuple[Any, ...]]:
    """Rebuild the frozen plan/dataset/TRAIN/TEST paired points from a raw artifact."""
    payload = r2b_plan.load_case_set(cases_path or r2b_plan.DEFAULT_CASES_PATH)
    if r2b_plan.case_set_fingerprint(payload) != raw["source_case_set_fingerprint"]:
        raise R2CError("case-set fingerprint does not match the raw artifact")
    if payload.get("case_set_version") != raw["source_case_set_version"]:
        raise R2CError("case-set version does not match the raw artifact")
    config = raw["model_configuration"]
    plan = r2b_plan.build_plan(payload, model_id=config["model"], model_revision=config["revision"])
    if plan.fingerprint != raw["plan_fingerprint"]:
        raise R2CError("rebuilt plan fingerprint does not match the raw artifact")
    outcomes_a = tuple(measurements.cat_outcome(record) for record in raw["cat_raw_records"])
    outcomes_b = tuple(measurements.ovr_outcome(record) for record in raw["ovr_raw_records"])
    dataset = PairedFixedDecisionDataset.create(plan, outcomes_a, outcomes_b)
    if dataset.fingerprint != raw["paired_dataset_fingerprint"]:
        raise R2CError("rebuilt dataset fingerprint does not match the raw artifact")
    train_points = analysis.scored_points(dataset, split=Split.TRAIN)
    test_points = analysis.scored_points(dataset, split=Split.TEST)
    return plan, dataset, train_points, test_points


def _raw_baseline_block(
    *, train_points: Sequence[Any], test_points: Sequence[Any]
) -> dict[str, Any]:
    raw_a_train = [float(p.score_a) for p in train_points]
    raw_b_train = [float(p.score_b) for p in train_points]
    raw_a_test = [float(p.score_a) for p in test_points]
    raw_b_test = [float(p.score_b) for p in test_points]
    return {
        "brier": {
            "cat": _brier_of(test_points, raw_a_test),
            "ovr": _brier_of(test_points, raw_b_test),
        },
        "logloss": {
            "cat": _logloss_of(test_points, raw_a_test),
            "ovr": _logloss_of(test_points, raw_b_test),
        },
        "train_brier": {
            "cat": _brier_of(train_points, raw_a_train),
            "ovr": _brier_of(train_points, raw_b_train),
        },
    }


def _train_refit_bootstrap(
    computations: Sequence[_ConfigComputation],
    *,
    train_points: Sequence[Any],
    test_points: Sequence[Any],
    plan_fingerprint: str,
    replicates: int,
) -> dict[str, Any]:
    """Paired train-refit bootstrap with one shared resample per replicate.

    Every configuration and both measurements reuse the SAME resampled training
    multiset per replicate. Any fit failure propagates: R2C fails closed rather
    than reporting an interval over an implicitly selected subset.
    """
    draws = _draw_matrix(
        protocol_id=PAIRED_TRAIN_REFIT_BOOTSTRAP_PROTOCOL_ID,
        protocol_version=PAIRED_TRAIN_REFIT_BOOTSTRAP_PROTOCOL_VERSION,
        replicates=replicates,
        draw=len(train_points),
        item_count=len(train_points),
    )
    series: dict[str, dict[str, list[float]]] = {
        computation.config.label: {
            "native_cat": [],
            "native_ovr": [],
            "transport_cat_to_ovr": [],
            "transport_ovr_to_cat": [],
            "cat_slope": [],
            "cat_intercept": [],
            "ovr_slope": [],
            "ovr_intercept": [],
        }
        for computation in computations
    }
    for row in draws:
        sampled = [train_points[index] for index in row]
        rows_a = [(p.item_id, p.score_a, p.y) for p in sampled]
        rows_b = [(p.item_id, p.score_b, p.y) for p in sampled]
        for computation in computations:
            config = computation.config
            g_cat = _fit_calibrator(
                config=config,
                source_measurement="CAT",
                training_rows=rows_a,
                plan_fingerprint=plan_fingerprint,
            )
            g_ovr = _fit_calibrator(
                config=config,
                source_measurement="OVR",
                training_rows=rows_b,
                plan_fingerprint=plan_fingerprint,
            )
            bucket = series[config.label]
            bucket["cat_slope"].append(g_cat.slope)
            bucket["cat_intercept"].append(g_cat.intercept)
            bucket["ovr_slope"].append(g_ovr.slope)
            bucket["ovr_intercept"].append(g_ovr.intercept)
            cat_test = [g_cat.apply(p.score_a) for p in test_points]
            ovr_test = [g_ovr.apply(p.score_b) for p in test_points]
            raw_a = [float(p.score_a) for p in test_points]
            raw_b = [float(p.score_b) for p in test_points]
            bucket["native_cat"].append(_mean(_per_item_native_diff(test_points, cat_test, raw_a)))
            bucket["native_ovr"].append(_mean(_per_item_native_diff(test_points, ovr_test, raw_b)))
            bucket["transport_cat_to_ovr"].append(
                _mean(_per_item_transport_diff(test_points, cat_test, ovr_test))
            )
            bucket["transport_ovr_to_cat"].append(
                _mean(_per_item_transport_diff(test_points, ovr_test, cat_test))
            )
    return {
        "protocol_id": PAIRED_TRAIN_REFIT_BOOTSTRAP_PROTOCOL_ID,
        "protocol_version": PAIRED_TRAIN_REFIT_BOOTSTRAP_PROTOCOL_VERSION,
        "replicates": replicates,
        "failed_fits": 0,
        "per_configuration": {
            label: {
                "native_cat": r2b_stability._interval(bucket["native_cat"]),
                "native_ovr": r2b_stability._interval(bucket["native_ovr"]),
                "transport_cat_to_ovr": r2b_stability._interval(bucket["transport_cat_to_ovr"]),
                "transport_ovr_to_cat": r2b_stability._interval(bucket["transport_ovr_to_cat"]),
                "native_cat_negative_fraction": _negative_fraction(bucket["native_cat"]),
                "native_ovr_negative_fraction": _negative_fraction(bucket["native_ovr"]),
                "parameter_cat": {
                    "slope": r2b_stability._interval(bucket["cat_slope"]),
                    "intercept": r2b_stability._interval(bucket["cat_intercept"]),
                },
                "parameter_ovr": {
                    "slope": r2b_stability._interval(bucket["ovr_slope"]),
                    "intercept": r2b_stability._interval(bucket["ovr_intercept"]),
                },
            }
            for label, bucket in series.items()
        },
    }


def _negative_fraction(values: Sequence[float]) -> float:
    return sum(1 for value in values if value < 0.0) / len(values)


def _paired_test_bootstrap(
    computations: Sequence[_ConfigComputation],
    *,
    test_points: Sequence[Any],
    replicates: int,
) -> dict[str, Any]:
    """Paired TEST bootstrap with one shared set of resampled positions."""
    draws = _draw_matrix(
        protocol_id=PAIRED_TEST_BOOTSTRAP_PROTOCOL_ID,
        protocol_version=PAIRED_TEST_BOOTSTRAP_PROTOCOL_VERSION,
        replicates=replicates,
        draw=len(test_points),
        item_count=len(test_points),
    )
    per_config: dict[str, Any] = {}
    for computation in computations:
        per_config[computation.config.label] = {
            "native_cat": r2b_stability._interval(
                _bootstrap_means(draws, computation.native_cat_diff)
            ),
            "native_ovr": r2b_stability._interval(
                _bootstrap_means(draws, computation.native_ovr_diff)
            ),
            "transport_cat_to_ovr": r2b_stability._interval(
                _bootstrap_means(draws, computation.transport_cat_to_ovr_diff)
            ),
            "transport_ovr_to_cat": r2b_stability._interval(
                _bootstrap_means(draws, computation.transport_ovr_to_cat_diff)
            ),
        }
    return {
        "protocol_id": PAIRED_TEST_BOOTSTRAP_PROTOCOL_ID,
        "protocol_version": PAIRED_TEST_BOOTSTRAP_PROTOCOL_VERSION,
        "replicates": replicates,
        "per_configuration": per_config,
    }


def _transport_sign_counts(results: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    deltas = [
        (
            float(result["transport"]["transport_delta_cat_to_ovr"]),
            float(result["transport"]["transport_delta_ovr_to_cat"]),
        )
        for result in results
    ]
    return {
        "cat_to_ovr_negative": sum(1 for a, _ in deltas if a < 0.0),
        "cat_to_ovr_positive": sum(1 for a, _ in deltas if a > 0.0),
        "cat_to_ovr_zero": sum(1 for a, _ in deltas if a == 0.0),
        "ovr_to_cat_negative": sum(1 for _, b in deltas if b < 0.0),
        "ovr_to_cat_positive": sum(1 for _, b in deltas if b > 0.0),
        "ovr_to_cat_zero": sum(1 for _, b in deltas if b == 0.0),
    }


def build_r2c_analysis_artifact(
    *,
    raw: Mapping[str, Any],
    design: Mapping[str, Any],
    plan: Any,
    train_points: Sequence[Any],
    test_points: Sequence[Any],
    provenance: Mapping[str, Any] | None = None,
    test_bootstrap_replicates: int = PAIRED_TEST_BOOTSTRAP_REPLICATES,
    train_refit_replicates: int = PAIRED_TRAIN_REFIT_BOOTSTRAP_REPLICATES,
) -> dict[str, Any]:
    configs = method_configs()
    computations = [
        _compute_config(
            config,
            train_points=train_points,
            test_points=test_points,
            plan_fingerprint=plan.fingerprint,
        )
        for config in configs
    ]
    config_results = [
        _config_result_block(computation, train_points=train_points, test_points=test_points)
        for computation in computations
    ]
    test_bootstrap = _paired_test_bootstrap(
        computations, test_points=test_points, replicates=test_bootstrap_replicates
    )
    train_refit = _train_refit_bootstrap(
        computations,
        train_points=train_points,
        test_points=test_points,
        plan_fingerprint=plan.fingerprint,
        replicates=train_refit_replicates,
    )
    for result in config_results:
        label = result["label"]
        result["paired_test_bootstrap"] = test_bootstrap["per_configuration"][label]
        result["train_refit_bootstrap"] = train_refit["per_configuration"][label]

    joint = [
        r["label"]
        for r in config_results
        if r["native"]["cat"]["native_minus_raw_brier"] < 0.0
        and r["native"]["ovr"]["native_minus_raw_brier"] < 0.0
    ]
    cat_better = [
        r["label"] for r in config_results if r["native"]["cat"]["native_minus_raw_brier"] < 0.0
    ]
    ovr_better = [
        r["label"] for r in config_results if r["native"]["ovr"]["native_minus_raw_brier"] < 0.0
    ]
    source = design["source_r2b_raw"]
    return {
        "artifact_type": R2C_ANALYSIS_ARTIFACT_TYPE,
        "artifact_version": R2C_ANALYSIS_ARTIFACT_VERSION,
        "round_id": ROUND_ID,
        "round_version": ROUND_VERSION,
        "research_spec_id": _integrity.RESEARCH_SPEC_ID,
        "research_spec_version": _integrity.RESEARCH_SPEC_VERSION,
        "design": {
            "artifact_type": design["artifact_type"],
            "artifact_version": design["artifact_version"],
            "fingerprint": design_fingerprint(design),
        },
        "source": {
            "path": source["path"],
            "file_sha256": source["file_sha256"],
            "source_case_set_version": raw["source_case_set_version"],
            "source_case_set_fingerprint": raw["source_case_set_fingerprint"],
            "plan_fingerprint": raw["plan_fingerprint"],
            "paired_dataset_fingerprint": raw["paired_dataset_fingerprint"],
            "r2b_run_provenance_fingerprint": raw["r2b_run_provenance_fingerprint"],
            "source_measurement_code_commit": source["source_measurement_code_commit"],
            "model": source["model"],
            "model_revision": source["model_revision"],
        },
        "provenance": dict(provenance or {}),
        "no_model_rerun": True,
        "lambda_grid": list(LAMBDA_GRID),
        "percentile_rule": {"id": PERCENTILE_RULE_ID, "version": PERCENTILE_RULE_VERSION},
        "raw_baseline": _raw_baseline_block(train_points=train_points, test_points=test_points),
        "configuration_order": [config.label for config in configs],
        "configurations": config_results,
        "paired_test_bootstrap": test_bootstrap,
        "train_refit_bootstrap": train_refit,
        "joint_native_improvement_configs": joint,
        "native_improvement_cat_configs": cat_better,
        "native_improvement_ovr_configs": ovr_better,
        "transport_sign_counts": _transport_sign_counts(config_results),
        "limitations": {
            "status": "exploratory",
            "statement": (
                "R2C reuses R2B held-out data after R2B results were already observed; "
                "it is an exploratory method-sensitivity study, not an independent "
                "confirmation of any selected calibration method."
            ),
            "excluded_methods": [
                "isotonic",
                "full-3-parameter-beta",
                "temperature-only-scaling",
                "other-nonlinear-nonparametric",
            ],
        },
    }


def analyze_raw_artifact(
    raw: Mapping[str, Any],
    *,
    design_path: Path | str = DEFAULT_DESIGN_PATH,
    cases_path: Path | str | None = None,
    provenance: Mapping[str, Any] | None = None,
    test_bootstrap_replicates: int = PAIRED_TEST_BOOTSTRAP_REPLICATES,
    train_refit_replicates: int = PAIRED_TRAIN_REFIT_BOOTSTRAP_REPLICATES,
) -> dict[str, Any]:
    design = load_design(design_path)
    validate_design(design)
    plan, _dataset, train_points, test_points = load_frozen_evidence(raw, cases_path=cases_path)
    return build_r2c_analysis_artifact(
        raw=raw,
        design=design,
        plan=plan,
        train_points=train_points,
        test_points=test_points,
        provenance=provenance,
        test_bootstrap_replicates=test_bootstrap_replicates,
        train_refit_replicates=train_refit_replicates,
    )


def file_sha256(path: Path | str) -> str:
    digest = hashlib.sha256()
    digest.update(Path(path).read_bytes())
    return digest.hexdigest()


def collect_provenance(*, design_path: Path | str = DEFAULT_DESIGN_PATH) -> dict[str, Any]:
    """Record design-freeze and execution commits as distinct provenance fields."""
    design_commit = _git(["log", "-1", "--format=%H", "--", str(Path(design_path).resolve())])
    execution_commit = _git(["rev-parse", "HEAD"])
    status = _git(["status", "--porcelain"])
    return {
        "r2c_analysis_design_commit": design_commit,
        "r2c_analysis_execution_commit": execution_commit,
        "git_worktree_clean": status == "",
    }


def _git(args: Sequence[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def _main(argv: Sequence[str]) -> int:
    if len(argv) not in (2, 3):
        print("usage: r2c_method_adequacy.py <R2B_RAW_ARTIFACT> [OUT]", file=sys.stderr)
        return 2
    raw_path = Path(argv[1])
    out_path = (
        Path(argv[2])
        if len(argv) == 3
        else raw_path.with_name("r2c-method-adequacy-qwen35-2b-v1-analysis.json")
    )
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    expected = load_design()["source_r2b_raw"]["file_sha256"]
    actual = file_sha256(raw_path)
    if actual != expected:
        raise R2CError(
            f"R2B raw artifact sha256 mismatch: expected {expected}, got {actual}; "
            "refusing to analyze tampered evidence"
        )
    artifact = analyze_raw_artifact(raw, provenance=collect_provenance())
    text = json.dumps(artifact, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
    out_path.write_text(text + "\n", encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(_main(sys.argv))
