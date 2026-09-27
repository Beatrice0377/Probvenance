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
