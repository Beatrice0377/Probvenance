"""Offline tests for the R3 pre-outcome analysis implementation.

No model, no GPU, no network. These lock the required algebraic invariants and
oracles from the R3 protocol: raw Brier, the cross/native and cross/raw
invariants, the factorial-contrast oracle, subject weighting, paired and shared
bootstrap behaviour, multiplicity tails, and the independent calculation path.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from collections import Counter
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


analysis = _load("r3_analysis")
protocol = _load("r3_protocol")

PROCEDURES = protocol.procedure_panel()


def _item(item_id: str, subject: str, label: float, cat: float, ovr: float) -> Any:
    return analysis.R3Item(item_id, subject, label, cat, ovr)


def _fixture() -> tuple[list[Any], list[Any]]:
    train = [
        _item("a0", "s1", 1.0, 0.70, 0.62),
        _item("a1", "s1", 0.0, 0.20, 0.44),
        _item("a2", "s1", 1.0, 0.61, 0.71),
        _item("a3", "s1", 0.0, 0.31, 0.38),
        _item("b0", "s2", 1.0, 0.80, 0.66),
        _item("b1", "s2", 0.0, 0.15, 0.35),
        _item("b2", "s2", 1.0, 0.55, 0.58),
        _item("b3", "s2", 0.0, 0.42, 0.47),
    ]
    test = [
        _item("c0", "s1", 1.0, 0.66, 0.60),
        _item("c1", "s1", 0.0, 0.28, 0.41),
        _item("d0", "s2", 1.0, 0.72, 0.64),
        _item("d1", "s2", 0.0, 0.33, 0.52),
    ]
    return train, test


class TestRawBrierInvariant:
    def test_raw_brier_is_the_mean_squared_error(self) -> None:
        pairs = [(0.8, 1.0), (0.2, 0.0), (0.5, 1.0)]
        expected = ((0.8 - 1.0) ** 2 + (0.2 - 0.0) ** 2 + (0.5 - 1.0) ** 2) / 3
        assert analysis.brier(pairs) == expected

    def test_brier_loss_single_item(self) -> None:
        assert analysis.brier_loss(0.8, 1.0) == (0.8 - 1.0) ** 2
        assert analysis.brier_loss(0.3, 0.0) == 0.09


class TestContrastInvariants:
    def test_cross_native_invariant(self) -> None:
        train, test = _fixture()
        panel = analysis.fit_panel(train, PROCEDURES)
        procedure = PROCEDURES[0]
        direction = analysis.DIRECTION_CAT_TO_OVR
        cross = analysis.subject_weighted_mean(
            test,
            lambda item: analysis._cross_loss(
                item, panel, procedure.label, direction, analysis.brier_loss
            ),
        )
        native = analysis.subject_weighted_mean(
            test,
            lambda item: analysis._native_loss(
                item, panel, procedure.label, direction, analysis.brier_loss
            ),
        )
        delta = analysis.subject_weighted_mean(
            test,
            lambda item: (
                analysis._cross_loss(item, panel, procedure.label, direction, analysis.brier_loss)
                - analysis._native_loss(
                    item, panel, procedure.label, direction, analysis.brier_loss
                )
            ),
        )
        assert math.isclose(delta, cross - native, rel_tol=0.0, abs_tol=1e-12)

    def test_cross_raw_invariant(self) -> None:
        train, test = _fixture()
        panel = analysis.fit_panel(train, PROCEDURES)
        procedure = PROCEDURES[2]
        direction = analysis.DIRECTION_OVR_TO_CAT
        cross = analysis.subject_weighted_mean(
            test,
            lambda item: analysis._cross_loss(
                item, panel, procedure.label, direction, analysis.brier_loss
            ),
        )
        raw = analysis.subject_weighted_mean(
            test, lambda item: analysis._raw_loss(item, direction, analysis.brier_loss)
        )
        delta = analysis.subject_weighted_mean(
            test,
            lambda item: (
                analysis._cross_loss(item, panel, procedure.label, direction, analysis.brier_loss)
                - analysis._raw_loss(item, direction, analysis.brier_loss)
            ),
        )
        assert math.isclose(delta, cross - raw, rel_tol=0.0, abs_tol=1e-12)


class TestFactorialOracle:
    def test_factorial_contrasts_match_hand_calculation(self) -> None:
        values = {
            protocol.PROCEDURE_P_LOW: 0.10,
            protocol.PROCEDURE_P_HISTORICAL: 0.20,
            protocol.PROCEDURE_L_LOW: 0.05,
            protocol.PROCEDURE_L_HISTORICAL: 0.30,
        }
        contrasts = analysis.factorial_contrasts(values)
        assert math.isclose(contrasts["feature"], 0.5 * (0.05 + 0.30 - 0.10 - 0.20), abs_tol=1e-15)
        assert math.isclose(
            contrasts["regularization"], 0.5 * (0.10 + 0.05 - 0.20 - 0.30), abs_tol=1e-15
        )
        assert math.isclose(contrasts["interaction"], (0.05 - 0.10) - (0.30 - 0.20), abs_tol=1e-15)

    def test_zero_effect_oracle(self) -> None:
        values = {
            protocol.PROCEDURE_P_LOW: 0.5,
            protocol.PROCEDURE_P_HISTORICAL: 0.5,
            protocol.PROCEDURE_L_LOW: 0.5,
            protocol.PROCEDURE_L_HISTORICAL: 0.5,
        }
        contrasts = analysis.factorial_contrasts(values)
        assert all(math.isclose(value, 0.0, abs_tol=1e-15) for value in contrasts.values())


class TestSubjectWeighting:
    def test_subject_weighted_mean_is_mean_of_subject_means(self) -> None:
        items = [
            _item("x0", "big", 1.0, 0.2, 0.2),
            _item("x1", "big", 1.0, 0.4, 0.4),
            _item("x2", "big", 1.0, 0.6, 0.6),
            _item("y0", "small", 1.0, 1.0, 1.0),
        ]
        value_of = lambda item: item.cat_score  # noqa: E731 - simple lookup
        subject_weighted = analysis.subject_weighted_mean(items, value_of)
        pooled = sum(value_of(item) for item in items) / len(items)
        assert math.isclose(subject_weighted, (0.4 + 1.0) / 2, abs_tol=1e-15)
        assert not math.isclose(subject_weighted, pooled, abs_tol=1e-9)


class TestBootstrapPairing:
    def test_paired_bootstrap_preserves_the_record(self) -> None:
        _train, test = _fixture()
        samples = analysis.bootstrap_subject_statistic(
            test,
            lambda item: item.cat_score * item.ovr_score,
            replicates=50,
            protocol_id=protocol.TEST_BOOTSTRAP_ID,
            protocol_version=protocol.TEST_BOOTSTRAP_VERSION,
        )
        independent = _independent_legs_bootstrap(test, replicates=50)
        assert samples != independent

    def test_bootstrap_is_deterministic(self) -> None:
        _train, test = _fixture()
        first = analysis.bootstrap_subject_statistic(
            test,
            lambda item: item.cat_score,
            replicates=30,
            protocol_id=protocol.TEST_BOOTSTRAP_ID,
            protocol_version=protocol.TEST_BOOTSTRAP_VERSION,
        )
        second = analysis.bootstrap_subject_statistic(
            test,
            lambda item: item.cat_score,
            replicates=30,
            protocol_id=protocol.TEST_BOOTSTRAP_ID,
            protocol_version=protocol.TEST_BOOTSTRAP_VERSION,
        )
        assert first == second

    def test_shared_draw_rule_matches_manual_recomputation(self) -> None:
        _train, test = _fixture()
        marker = "c0"
        samples = analysis.bootstrap_subject_statistic(
            test,
            lambda item: 1.0 if item.item_id == marker else 0.0,
            replicates=5,
            protocol_id=protocol.TEST_BOOTSTRAP_ID,
            protocol_version=protocol.TEST_BOOTSTRAP_VERSION,
        )
        grouped = analysis._grouped_by_subject(test)
        subjects = sorted(grouped)
        expected = []
        for replicate in range(5):
            subject_means = []
            for subject in subjects:
                members = grouped[subject]
                hits = 0
                for draw in range(len(members)):
                    index = analysis._draw_index(
                        protocol_id=protocol.TEST_BOOTSTRAP_ID,
                        protocol_version=protocol.TEST_BOOTSTRAP_VERSION,
                        replicate=replicate,
                        subject=subject,
                        draw=draw,
                        item_count=len(members),
                    )
                    hits += 1.0 if members[index].item_id == marker else 0.0
                subject_means.append(hits / len(members))
            expected.append(math.fsum(subject_means) / len(subject_means))
        assert samples == expected


def _independent_legs_bootstrap(items: list[Any], *, replicates: int) -> list[float]:
    grouped = analysis._grouped_by_subject(items)
    subjects = sorted(grouped)
    samples = []
    for replicate in range(replicates):
        subject_means = []
        for subject in subjects:
            members = grouped[subject]
            total = 0.0
            for draw in range(len(members)):
                cat_index = analysis._draw_index(
                    protocol_id="independent-cat",
                    protocol_version=1,
                    replicate=replicate,
                    subject=subject,
                    draw=draw,
                    item_count=len(members),
                )
                ovr_index = analysis._draw_index(
                    protocol_id="independent-ovr",
                    protocol_version=1,
                    replicate=replicate,
                    subject=subject,
                    draw=draw,
                    item_count=len(members),
                )
                total += members[cat_index].cat_score * members[ovr_index].ovr_score
            subject_means.append(total / len(members))
        samples.append(math.fsum(subject_means) / len(subject_means))
    return samples


class TestMultiplicity:
    def test_primary_tails(self) -> None:
        ordered = [float(index) for index in range(240)]
        assert analysis.nearest_rank_percentile(ordered, 100.0 / 240.0) == 0.0
        assert analysis.nearest_rank_percentile(ordered, 100.0 * 239.0 / 240.0) == 238.0

    def test_native_tails(self) -> None:
        ordered = [float(index) for index in range(320)]
        assert analysis.nearest_rank_percentile(ordered, 100.0 / 320.0) == 0.0
        assert analysis.nearest_rank_percentile(ordered, 100.0 * 319.0 / 320.0) == 318.0

    def test_interval_excludes_zero_flag(self) -> None:
        positive = analysis._interval([1.0, 2.0, 3.0], analysis.PRIMARY_PERCENTILES)
        straddling = analysis._interval([-1.0, 0.0, 1.0], analysis.PRIMARY_PERCENTILES)
        assert positive["excludes_zero"] is True
        assert straddling["excludes_zero"] is False

    def test_interval_is_ordered(self) -> None:
        samples = [math.sin(index) for index in range(400)]
        interval = analysis._interval(samples, analysis.PRIMARY_PERCENTILES)
        assert interval["lower"] <= interval["median"] <= interval["upper"]


class TestIndependentPaths:
    def test_risk_matrix_and_per_item_paths_agree(self) -> None:
        train, test = _fixture()
        panel = analysis.fit_panel(train, PROCEDURES)
        for direction in protocol.PRIMARY_DIRECTIONS:
            path1 = analysis.risk_matrix(test, panel, PROCEDURES, direction)
            path2 = analysis.cross_vs_raw_values(test, panel, PROCEDURES, direction)
            for procedure in PROCEDURES:
                assert math.isclose(
                    path1["cross_vs_raw"][procedure.label],
                    path2[procedure.label],
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )


class TestEndpointPolicy:
    def test_family_l_fails_closed_on_exact_endpoint(self) -> None:
        train = [
            _item("a0", "s1", 1.0, 1.0, 0.62),
            _item("a1", "s1", 0.0, 0.20, 0.44),
            _item("b0", "s2", 1.0, 0.80, 0.66),
            _item("b1", "s2", 0.0, 0.15, 0.35),
        ]
        try:
            analysis.fit_panel(train, PROCEDURES)
        except analysis.ProbabilityEndpointError:
            return
        raise AssertionError("Family L must fail closed on an exact probability endpoint")

    def test_unknown_feature_is_rejected(self) -> None:
        try:
            analysis.feature_value("not-a-feature", 0.5)
        except analysis.AnalysisError:
            return
        raise AssertionError("unknown feature must be rejected")


class TestNoSelectionLeakage:
    def test_analysis_has_no_method_selection_surface(self) -> None:
        for name in dir(analysis):
            assert "selected_method" not in name
            assert "winner_method" not in name
            assert "best_lambda" not in name


class TestArtifactAssembly:
    def test_build_analysis_artifact_runs_on_synthetic(self) -> None:
        train, test = _fixture()
        design = protocol.build_design(__import__("r3_population").load_manifest())
        payload = analysis.build_analysis_artifact(
            protocol_design=design,
            conditions=[
                {
                    "model_id": protocol.PRIMARY_MODEL_ID,
                    "model_revision": protocol.PRIMARY_MODEL_REVISION,
                    "train_items": train,
                    "test_items": test,
                }
            ],
            test_replicates=40,
            train_refit_replicates=8,
        )
        assert payload["artifact_type"] == analysis.R3_ANALYSIS_ARTIFACT_TYPE
        assert payload["protocol_fingerprint"] == design["protocol_fingerprint"]
        block = payload["models"][0]
        assert len(block["native_reference"]) == 8
        assert len(block["directions"]) == 2


_STUB_CAT_SLOPE = 2.0
_STUB_CAT_INTERCEPT = 0.10
_STUB_OVR_SLOPE = 3.0
_STUB_OVR_INTERCEPT = 0.20


def _g_cat(score: float) -> float:
    return _STUB_CAT_SLOPE * score + _STUB_CAT_INTERCEPT


def _g_ovr(score: float) -> float:
    return _STUB_OVR_SLOPE * score + _STUB_OVR_INTERCEPT


class _AffineStub:
    """A deterministic calibrator with distinct CAT/OVR output ranges."""

    def __init__(self, slope: float, intercept: float) -> None:
        self._slope = slope
        self._intercept = intercept

    def apply(self, score: float) -> float:
        return self._slope * score + self._intercept


class _SpyStub:
    """A calibrator that records the exact score it is applied to."""

    def __init__(self) -> None:
        self.calls: list[float] = []

    def apply(self, score: float) -> float:
        self.calls.append(score)
        return 0.5


def _stub_panel(procedures: tuple[Any, ...]) -> Any:
    calibrators: dict[tuple[str, str], Any] = {}
    for procedure in procedures:
        calibrators[(procedure.label, analysis.MEASUREMENT_CAT)] = _AffineStub(
            _STUB_CAT_SLOPE, _STUB_CAT_INTERCEPT
        )
        calibrators[(procedure.label, analysis.MEASUREMENT_OVR)] = _AffineStub(
            _STUB_OVR_SLOPE, _STUB_OVR_INTERCEPT
        )
    return analysis.R3PanelFit(calibrators)


def _skewed_fixture() -> tuple[list[Any], list[Any]]:
    """Items whose CAT and OVR scores never coincide (2 subjects, 4 TEST rows)."""
    train = [
        _item("t0", "s1", 1.0, 0.62, 0.41),
        _item("t1", "s1", 0.0, 0.31, 0.58),
        _item("t2", "s2", 1.0, 0.77, 0.49),
        _item("t3", "s2", 0.0, 0.24, 0.66),
    ]
    test = [
        _item("q0", "s1", 1.0, 0.71, 0.38),
        _item("q1", "s1", 0.0, 0.29, 0.61),
        _item("q2", "s2", 1.0, 0.65, 0.44),
        _item("q3", "s2", 0.0, 0.35, 0.57),
    ]
    return train, test


class TestCrossApplicationSemantics:
    """Direct oracles: cross prediction is g_SOURCE(S_TARGET), not g_SOURCE(S_SOURCE)."""

    def test_cat_to_ovr_uses_target_ovr_score(self) -> None:
        _train, test = _skewed_fixture()
        panel = _stub_panel((PROCEDURES[0],))
        label = PROCEDURES[0].label
        for item in test:
            prediction = analysis._cross_prediction(
                item, panel, label, analysis.DIRECTION_CAT_TO_OVR
            )
            assert prediction == _g_cat(item.ovr_score)
            assert prediction != _g_cat(item.cat_score)

    def test_ovr_to_cat_uses_target_cat_score(self) -> None:
        _train, test = _skewed_fixture()
        panel = _stub_panel((PROCEDURES[0],))
        label = PROCEDURES[0].label
        for item in test:
            prediction = analysis._cross_prediction(
                item, panel, label, analysis.DIRECTION_OVR_TO_CAT
            )
            assert prediction == _g_ovr(item.cat_score)
            assert prediction != _g_ovr(item.ovr_score)

    def test_cross_brier_uses_target_score(self) -> None:
        _train, test = _skewed_fixture()
        panel = _stub_panel((PROCEDURES[0],))
        label = PROCEDURES[0].label
        item = test[0]
        loss = analysis._cross_loss(
            item, panel, label, analysis.DIRECTION_CAT_TO_OVR, analysis.brier_loss
        )
        assert loss == (_g_cat(item.ovr_score) - item.label) ** 2
        assert loss != (_g_cat(item.cat_score) - item.label) ** 2

    def test_cross_logloss_predictions_use_target_score(self) -> None:
        _train, test = _skewed_fixture()
        panel = _stub_panel((PROCEDURES[0],))
        label = PROCEDURES[0].label
        pairs = analysis._cross_predictions(test, panel, label, analysis.DIRECTION_CAT_TO_OVR)
        expected = [(_g_cat(item.ovr_score), item.label) for item in test]
        buggy = [(_g_cat(item.cat_score), item.label) for item in test]
        assert pairs == expected
        assert pairs != buggy
        assert analysis.exact_logloss(pairs) == analysis.exact_logloss(expected)

    def test_cross_reliability_uses_target_score(self) -> None:
        _train, test = _skewed_fixture()
        cat_spy = _SpyStub()
        ovr_spy = _SpyStub()
        label = PROCEDURES[0].label
        panel = analysis.R3PanelFit(
            {
                (label, analysis.MEASUREMENT_CAT): cat_spy,
                (label, analysis.MEASUREMENT_OVR): ovr_spy,
            }
        )
        analysis.reliability_diagnostics(
            test, panel, (PROCEDURES[0],), analysis.DIRECTION_CAT_TO_OVR
        )
        assert cat_spy.calls == [item.ovr_score for item in test]
        assert cat_spy.calls != [item.cat_score for item in test]


class TestCrossGeometrySupport:
    def _fixture(self) -> tuple[list[Any], list[Any]]:
        train = [
            _item("t0", "s1", 1.0, 0.10, 0.90),
            _item("t1", "s1", 0.0, 0.20, 0.95),
            _item("t2", "s2", 1.0, 0.30, 0.99),
            _item("t3", "s2", 0.0, 0.40, 0.85),
            _item("t4", "s2", 1.0, 0.50, 0.80),
        ]
        test = [
            _item("q0", "s1", 1.0, 0.60, 0.30),
            _item("q1", "s1", 0.0, 0.70, 0.35),
            _item("q2", "s2", 1.0, 0.80, 0.45),
            _item("q3", "s2", 0.0, 0.90, 0.25),
        ]
        return train, test

    def test_range_decomposition_uses_source_train_boundary_and_target_prediction(self) -> None:
        train, test = self._fixture()
        panel = _stub_panel((PROCEDURES[0],))
        label = PROCEDURES[0].label
        block = analysis.range_loss_decomposition(
            train, test, panel, (PROCEDURES[0],), analysis.DIRECTION_CAT_TO_OVR
        )[label]
        assert block["source_train_min"] == 0.10
        assert block["source_train_max"] == 0.50
        assert block["n_in"] == 4
        assert block["n_out"] == 0
        expected_in = [
            (_g_cat(item.ovr_score) - item.label) ** 2 - (item.ovr_score - item.label) ** 2
            for item in test
        ]
        buggy_in = [
            (_g_cat(item.cat_score) - item.label) ** 2 - (item.ovr_score - item.label) ** 2
            for item in test
        ]
        assert math.isclose(block["mean_in"], math.fsum(expected_in) / 4, abs_tol=1e-12)
        assert not math.isclose(block["mean_in"], math.fsum(buggy_in) / 4, abs_tol=1e-12)

    def test_test_derived_boundary_would_disagree(self) -> None:
        _train, test = self._fixture()
        test_source = [item.cat_score for item in test]
        assert all(not (min(test_source) <= item.ovr_score <= max(test_source)) for item in test)


class TestScoreGeometry:
    def _fixture(self) -> tuple[list[Any], list[Any]]:
        train = [_item(f"t{i}", "s1", 1.0, (i + 1) / 100.0, 0.50) for i in range(40)]
        test = [
            _item("q0", "s2", 1.0, 0.85, 0.005),
            _item("q1", "s2", 1.0, 0.86, 0.20),
            _item("q2", "s2", 1.0, 0.87, 0.395),
            _item("q3", "s2", 1.0, 0.88, 0.45),
        ]
        return train, test

    def test_geometry_uses_source_train_and_target_test(self) -> None:
        train, test = self._fixture()
        geo = analysis.score_geometry(train, test, analysis.DIRECTION_CAT_TO_OVR)
        assert geo["source_train_count"] == 40
        assert geo["target_test_count"] == 4
        assert geo["source_train_min"] == 0.01
        assert geo["source_train_max"] == 0.40
        assert geo["source_train_q2_5"] == 0.01
        assert geo["source_train_q97_5"] == 0.39
        assert math.isclose(geo["target_test_fraction_outside_source_train_min_max"], 0.5)
        assert math.isclose(geo["target_test_fraction_outside_source_train_q2_5_q97_5"], 0.75)

    def test_geometry_source_boundary_is_not_test_derived(self) -> None:
        train, test = self._fixture()
        geo = analysis.score_geometry(train, test, analysis.DIRECTION_CAT_TO_OVR)
        assert geo["source_train_min"] == min(item.cat_score for item in train)
        assert geo["source_train_min"] < min(item.cat_score for item in test)

    def test_geometry_quantile_uses_nearest_rank_rule(self) -> None:
        train, test = self._fixture()
        geo = analysis.score_geometry(train, test, analysis.DIRECTION_CAT_TO_OVR)
        ordered = sorted(item.cat_score for item in train)
        assert geo["source_train_q2_5"] == analysis.nearest_rank_percentile(ordered, 2.5)
        assert geo["source_train_q97_5"] == analysis.nearest_rank_percentile(ordered, 97.5)


class TestTrainRefitDrawUnit:
    def test_resample_draws_ten_per_subject_with_replacement(self) -> None:
        train, _test = _skewed_fixture()
        resampled = analysis.resample_train_multiset(train, replicate=0)
        counts = Counter(item.subject for item in resampled)
        assert counts == {"s1": 10, "s2": 10}
        assert len(resampled) == 20

    def test_resample_is_deterministic(self) -> None:
        train, _test = _skewed_fixture()
        first = analysis.resample_train_multiset(train, replicate=5)
        second = analysis.resample_train_multiset(train, replicate=5)
        assert [item.item_id for item in first] == [item.item_id for item in second]

    def test_resample_draw_ordinals_are_zero_through_nine(self) -> None:
        train, _test = _skewed_fixture()
        calls: list[dict[str, Any]] = []
        original = analysis._draw_index

        def recorder(**kwargs: Any) -> int:
            calls.append(kwargs)
            return original(**kwargs)

        analysis._draw_index = recorder
        try:
            analysis.resample_train_multiset(train, replicate=2)
        finally:
            analysis._draw_index = original
        assert sorted({call["draw"] for call in calls}) == list(range(10))
        assert Counter(call["subject"] for call in calls) == {"s1": 10, "s2": 10}
        assert all(call["item_count"] == 2 for call in calls)
        assert all(call["protocol_id"] == protocol.TRAIN_REFIT_BOOTSTRAP_ID for call in calls)
        assert all(call["replicate"] == 2 for call in calls)

    def test_same_resampled_records_feed_cat_and_ovr(self) -> None:
        train, _test = _skewed_fixture()
        resampled = analysis.resample_train_multiset(train, replicate=3)
        panel = analysis.fit_panel(resampled, PROCEDURES)
        cat_ids = panel.get(PROCEDURES[0].label, analysis.MEASUREMENT_CAT).training_item_ids
        ovr_ids = panel.get(PROCEDURES[0].label, analysis.MEASUREMENT_OVR).training_item_ids
        assert cat_ids == ovr_ids

    def test_train_refit_stability_resamples_ten_per_subject(self) -> None:
        train, test = _skewed_fixture()
        calls: list[dict[str, Any]] = []
        original = analysis._draw_index

        def recorder(**kwargs: Any) -> int:
            calls.append(kwargs)
            return original(**kwargs)

        analysis._draw_index = recorder
        try:
            analysis._train_refit_stability(train, test, PROCEDURES, replicates=2)
        finally:
            analysis._draw_index = original
        train_calls = [
            call for call in calls if call["protocol_id"] == protocol.TRAIN_REFIT_BOOTSTRAP_ID
        ]
        per_replicate_subject = Counter(
            (call["replicate"], call["subject"]) for call in train_calls
        )
        assert all(count == 10 for count in per_replicate_subject.values())
        assert sorted({call["draw"] for call in train_calls}) == list(range(10))


class TestTrainRefitFailureContract:
    """Frozen §17: a procedure-level refit failure makes only that block INCOMPLETE."""

    _TARGET_INDEX = 1

    def _inject_failure(self, target_label: str, *, fail_first: int = 1) -> Any:
        real = analysis.fit_panel
        seen = {"count": 0}

        def fake(items: Any, procedures: Any) -> Any:
            labels = [procedure.label for procedure in procedures]
            if labels == [target_label]:
                seen["count"] += 1
                if seen["count"] <= fail_first:
                    raise analysis.AnalysisError("synthetic procedure refit failure")
            return real(items, procedures)

        return fake

    def test_failed_procedure_incomplete_others_complete(self) -> None:
        train, test = _skewed_fixture()
        target = PROCEDURES[self._TARGET_INDEX].label
        real = analysis.fit_panel
        analysis.fit_panel = self._inject_failure(target)
        try:
            result = analysis._train_refit_stability(train, test, PROCEDURES, replicates=3)
        finally:
            analysis.fit_panel = real
        blocks = result["procedures"]

        failed = blocks[target]
        assert failed["status"] == "INCOMPLETE"
        assert failed["planned_replicates"] == 3
        assert failed["failed_replicates"] >= 1
        assert failed["successful_replicates"] == 3 - failed["failed_replicates"]
        assert failed["successful_replicates"] > 0
        assert len(failed["failures"]) == failed["failed_replicates"]
        record = failed["failures"][0]
        assert record["replicate"] == 0
        assert record["procedure_label"] == target
        assert record["error_type"] == "AnalysisError"
        assert "synthetic" in record["message"]
        for direction in protocol.PRIMARY_DIRECTIONS:
            assert failed["directions"][direction]["interval"] is None

        for procedure in PROCEDURES:
            if procedure.label == target:
                continue
            healthy = blocks[procedure.label]
            assert healthy["status"] == "COMPLETE"
            assert healthy["failed_replicates"] == 0
            assert healthy["successful_replicates"] == 3
            assert healthy["failures"] == []
            for direction in protocol.PRIMARY_DIRECTIONS:
                assert healthy["directions"][direction]["interval"] is not None

    def test_incomplete_procedure_never_calls_interval(self) -> None:
        train, test = _skewed_fixture()
        target = PROCEDURES[self._TARGET_INDEX].label
        real_fit_panel = analysis.fit_panel
        real_interval = analysis._interval
        interval_sizes: list[int] = []

        def spy_interval(samples: Any, percentiles: Any) -> Any:
            interval_sizes.append(len(samples))
            return real_interval(samples, percentiles)

        analysis.fit_panel = self._inject_failure(target)
        analysis._interval = spy_interval
        try:
            result = analysis._train_refit_stability(train, test, PROCEDURES, replicates=3)
        finally:
            analysis.fit_panel = real_fit_panel
            analysis._interval = real_interval

        complete = [procedure.label for procedure in PROCEDURES if procedure.label != target]
        assert len(interval_sizes) == len(complete) * len(protocol.PRIMARY_DIRECTIONS)
        assert all(size == 3 for size in interval_sizes)
        assert (
            result["procedures"][target]["directions"][analysis.DIRECTION_CAT_TO_OVR]["interval"]
            is None
        )
        assert (
            result["procedures"][target]["directions"][analysis.DIRECTION_OVR_TO_CAT]["interval"]
            is None
        )

    def test_one_resample_per_replicate_reused_across_procedures(self) -> None:
        train, test = _skewed_fixture()
        resamples: list[tuple[int, Any]] = []
        refit_inputs: list[tuple[str, int]] = []
        real_resample = analysis.resample_train_multiset
        real_fit_panel = analysis.fit_panel

        def spy_resample(items: Any, *, replicate: int, draws_per_subject: int = 10) -> Any:
            resampled = real_resample(
                items, replicate=replicate, draws_per_subject=draws_per_subject
            )
            resamples.append((replicate, resampled))
            return resampled

        def spy_fit_panel(items: Any, procedures: Any) -> Any:
            labels = [procedure.label for procedure in procedures]
            if len(labels) == 1:
                refit_inputs.append((labels[0], id(items)))
            return real_fit_panel(items, procedures)

        analysis.resample_train_multiset = spy_resample
        analysis.fit_panel = spy_fit_panel
        try:
            analysis._train_refit_stability(train, test, PROCEDURES, replicates=3)
        finally:
            analysis.resample_train_multiset = real_resample
            analysis.fit_panel = real_fit_panel

        assert [replicate for replicate, _ in resamples] == [0, 1, 2]
        width = len(PROCEDURES)
        assert len(refit_inputs) == 3 * width
        expected_labels = {procedure.label for procedure in PROCEDURES}
        for index, (_replicate, resampled) in enumerate(resamples):
            group = refit_inputs[index * width : (index + 1) * width]
            assert {label for label, _ in group} == expected_labels
            assert all(object_id == id(resampled) for _label, object_id in group)

    def test_zero_failures_yields_complete_with_interval(self) -> None:
        train, test = _skewed_fixture()
        result = analysis._train_refit_stability(train, test, PROCEDURES, replicates=3)
        assert result["replicates"] == 3
        for procedure in PROCEDURES:
            block = result["procedures"][procedure.label]
            assert block["status"] == "COMPLETE"
            assert block["planned_replicates"] == 3
            assert block["successful_replicates"] == 3
            assert block["failed_replicates"] == 0
            assert block["failures"] == []
            for direction in protocol.PRIMARY_DIRECTIONS:
                cell = block["directions"][direction]
                assert cell["interval"] is not None
                assert cell["interval"]["n"] == 3
                assert isinstance(cell["point"], float)
