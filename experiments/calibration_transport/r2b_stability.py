"""R2B stability / deconfounding analysis (research-only, exploratory).

This module answers one question that R2A could not: whether the directional
transport structure R2A observed was mostly an artifact of fitting two
calibrators on nine rows and evaluating them on six.

It is deliberately NOT confirmatory evidence. The paired bootstrap procedures
below are **exploratory stability diagnostics**: deterministic percentile
intervals, never frequentist coverage claims, never p-values.

It reuses the R2A research analysis helpers (eligibility, the frozen research
L2-logistic calibrator, Brier/LogLoss, observed-range diagnostics) and the
production numerical kernel. It never constructs a Phase 4C ``CalibrationProfile``
and never reuses ``winner_correctness`` / ``uncalibrated-selected-probability``.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from probvenance.fingerprint import fingerprint

_HARNESS_DIR = Path(__file__).resolve().parent


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
r2b_provenance = _load_sibling("r2b_provenance")
_integrity = analysis._integrity
Split = _integrity.Split
MeasurementStatus = _integrity.MeasurementStatus

R2B_ANALYSIS_ARTIFACT_TYPE = "calibration-transport-r2b-stability-analysis"
R2B_ANALYSIS_ARTIFACT_VERSION = 1

PAIRED_TEST_BOOTSTRAP_PROTOCOL_ID = "sha256-paired-test-bootstrap"
PAIRED_TEST_BOOTSTRAP_PROTOCOL_VERSION = 1
PAIRED_TEST_BOOTSTRAP_REPLICATES = 2000

PAIRED_TRAIN_REFIT_BOOTSTRAP_PROTOCOL_ID = "sha256-paired-train-refit-bootstrap"
PAIRED_TRAIN_REFIT_BOOTSTRAP_PROTOCOL_VERSION = 1
PAIRED_TRAIN_REFIT_BOOTSTRAP_REPLICATES = 1000

PERCENTILE_RULE_ID = "nearest-rank-percentile"
PERCENTILE_RULE_VERSION = 1

_BOOTSTRAP_PERCENTILES = (2.5, 50.0, 97.5)


def _draw_index(
    *, protocol_id: str, protocol_version: int, replicate: int, draw: int, item_count: int
) -> int:
    """One deterministic paired draw index from a content fingerprint.

    The draw depends only on the protocol identity, the replicate, the draw
    position, and the item count. It uses no global RNG, no numpy RNG, and no
    Python ``random`` implementation detail, so the same code and data always
    generate a byte-identical bootstrap artifact.
    """
    digest = fingerprint(
        {
            "protocol_id": protocol_id,
            "protocol_version": protocol_version,
            "replicate": replicate,
            "draw": draw,
            "item_count": item_count,
        }
    )
    return int(digest, 16) % item_count


def nearest_rank_percentile(ordered_values: Sequence[float], percentile: float) -> float:
    """Nearest-rank percentile (``nearest-rank-percentile`` v1).

    ``rank = ceil(percentile/100 * n)`` clamped to ``[1, n]``; the value is the
    element at that 1-based rank of the ascending sequence.
    """
    if not ordered_values:
        raise ValueError("nearest_rank_percentile requires at least one value")
    if not 0.0 <= percentile <= 100.0:
        raise ValueError(f"percentile must be within [0, 100], got {percentile!r}")
    n = len(ordered_values)
    rank = math.ceil(percentile / 100.0 * n)
    rank = min(max(rank, 1), n)
    return float(ordered_values[rank - 1])


def _interval(values: Sequence[float]) -> dict[str, Any]:
    ordered = sorted(float(v) for v in values)
    return {
        "n": len(ordered),
        "p2_5": nearest_rank_percentile(ordered, 2.5),
        "median": nearest_rank_percentile(ordered, 50.0),
        "p97_5": nearest_rank_percentile(ordered, 97.5),
    }


def _sample_brier(q: float, y: float) -> float:
    return (float(q) - float(y)) ** 2


def _per_item_l1z(point: Any, g_a: Any, g_b: Any, *, direction: str) -> float:
    """Per-item paired Brier loss DIFFERENCE for one transport direction.

    ``cat_to_ovr`` uses measurement B's held-out score for both calibrators;
    ``ovr_to_cat`` uses measurement A's. Both legs are evaluated on the SAME
    frozen anchor label ``y``.
    """
    if direction == "cat_to_ovr":
        return _sample_brier(g_a.apply(point.score_b), point.y) - _sample_brier(
            g_b.apply(point.score_b), point.y
        )
    if direction == "ovr_to_cat":
        return _sample_brier(g_b.apply(point.score_a), point.y) - _sample_brier(
            g_a.apply(point.score_a), point.y
        )
    raise ValueError(f"unknown direction {direction!r}")


def paired_test_bootstrap(
    test_points: Sequence[Any],
    g_a: Any,
    g_b: Any,
    *,
    replicates: int = PAIRED_TEST_BOOTSTRAP_REPLICATES,
    protocol_id: str = PAIRED_TEST_BOOTSTRAP_PROTOCOL_ID,
    protocol_version: int = PAIRED_TEST_BOOTSTRAP_PROTOCOL_VERSION,
) -> dict[str, Any]:
    """Exploratory paired test bootstrap over the held-out paired items.

    Each replicate resamples TEST item POSITIONS with replacement; a drawn
    position carries its ``Y``, ``S_A``, and ``S_B`` together. CAT and OVR are
    never resampled separately. The intervals are exploratory percentile
    intervals, not confirmatory confidence intervals.
    """
    if not test_points:
        raise ValueError("paired_test_bootstrap requires at least one test point")
    n = len(test_points)
    diffs_a = [_per_item_l1z(p, g_a, g_b, direction="cat_to_ovr") for p in test_points]
    diffs_b = [_per_item_l1z(p, g_a, g_b, direction="ovr_to_cat") for p in test_points]
    point_a = analysis.brier([(g_a.apply(p.score_b), p.y) for p in test_points]) - analysis.brier(
        [(g_b.apply(p.score_b), p.y) for p in test_points]
    )
    point_b = analysis.brier([(g_b.apply(p.score_a), p.y) for p in test_points]) - analysis.brier(
        [(g_a.apply(p.score_a), p.y) for p in test_points]
    )

    delta_a_samples: list[float] = []
    delta_b_samples: list[float] = []
    for replicate in range(replicates):
        delta_a_total = 0.0
        delta_b_total = 0.0
        for draw in range(n):
            index = _draw_index(
                protocol_id=protocol_id,
                protocol_version=protocol_version,
                replicate=replicate,
                draw=draw,
                item_count=n,
            )
            delta_a_total += diffs_a[index]
            delta_b_total += diffs_b[index]
        delta_a_samples.append(delta_a_total / n)
        delta_b_samples.append(delta_b_total / n)

    return {
        "protocol_id": protocol_id,
        "protocol_version": protocol_version,
        "replicates": replicates,
        "item_count": n,
        "delta_cat_to_ovr": {
            "point_estimate": point_a,
            "interval": _interval(delta_a_samples),
        },
        "delta_ovr_to_cat": {
            "point_estimate": point_b,
            "interval": _interval(delta_b_samples),
        },
    }


def train_refit_bootstrap(
    train_points: Sequence[Any],
    test_points: Sequence[Any],
    *,
    plan: Any,
    l2_strength: float = analysis.PILOT_L2_STRENGTH,
    replicates: int = PAIRED_TRAIN_REFIT_BOOTSTRAP_REPLICATES,
    protocol_id: str = PAIRED_TRAIN_REFIT_BOOTSTRAP_PROTOCOL_ID,
    protocol_version: int = PAIRED_TRAIN_REFIT_BOOTSTRAP_PROTOCOL_VERSION,
) -> dict[str, Any]:
    """Paired train-refit bootstrap: training-composition sensitivity.

    Each replicate resamples TRAIN item positions with replacement and uses the
    SAME sampled multiset to refit BOTH ``g_A`` and ``g_B``. The refitted pair is
    evaluated on the original fixed TEST items. A solver failure raises instead
    of being silently dropped.
    """
    if not train_points:
        raise ValueError("train_refit_bootstrap requires at least one train point")
    if not test_points:
        raise ValueError("train_refit_bootstrap requires at least one test point")
    n = len(train_points)
    slope_a: list[float] = []
    intercept_a: list[float] = []
    slope_b: list[float] = []
    intercept_b: list[float] = []
    cells = {"fit_a_eval_a": [], "fit_a_eval_b": [], "fit_b_eval_a": [], "fit_b_eval_b": []}
    delta_a: list[float] = []
    delta_b: list[float] = []

    for replicate in range(replicates):
        indices = [
            _draw_index(
                protocol_id=protocol_id,
                protocol_version=protocol_version,
                replicate=replicate,
                draw=draw,
                item_count=n,
            )
            for draw in range(n)
        ]
        sampled = [train_points[index] for index in indices]
        rows_a = [(p.item_id, p.score_a, p.y) for p in sampled]
        rows_b = [(p.item_id, p.score_b, p.y) for p in sampled]
        try:
            g_a_r = analysis.fit_pilot_calibrator(
                source_measurement=plan.measurement_a,
                training_rows=rows_a,
                plan_fingerprint=plan.fingerprint,
                l2_strength=l2_strength,
            )
            g_b_r = analysis.fit_pilot_calibrator(
                source_measurement=plan.measurement_b,
                training_rows=rows_b,
                plan_fingerprint=plan.fingerprint,
                l2_strength=l2_strength,
            )
        except Exception as exc:  # fail closed: never silently drop a replicate
            raise ValueError(
                f"train-refit bootstrap replicate {replicate} failed to fit: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        cell = analysis.brier_matrix(test_points, g_a_r, g_b_r)
        slope_a.append(g_a_r.slope)
        intercept_a.append(g_a_r.intercept)
        slope_b.append(g_b_r.slope)
        intercept_b.append(g_b_r.intercept)
        for name in cells:
            cells[name].append(cell[name])
        delta_a.append(cell["delta_a_to_b"])
        delta_b.append(cell["delta_b_to_a"])

    return {
        "protocol_id": protocol_id,
        "protocol_version": protocol_version,
        "replicates": replicates,
        "failed_refits": 0,
        "train_item_count": n,
        "test_item_count": len(test_points),
        "calibrator_a": {
            "slope": _interval(slope_a),
            "intercept": _interval(intercept_a),
        },
        "calibrator_b": {
            "slope": _interval(slope_b),
            "intercept": _interval(intercept_b),
        },
        "brier_cells": {name: _interval(values) for name, values in cells.items()},
        "delta_cat_to_ovr": _interval(delta_a),
        "delta_ovr_to_cat": _interval(delta_b),
    }


def observed_range_loss_decomposition(
    train_points: Sequence[Any], test_points: Sequence[Any], g_a: Any, g_b: Any
) -> dict[str, Any]:
    """Per-region transport-loss decomposition against the SOURCE TRAIN range.

    For ``SOURCE -> TARGET``, each TARGET TEST row contributes
    ``d_i = Brier(g_SOURCE(S_TARGET), Y) - Brier(g_TARGET(S_TARGET), Y)``; its
    mean is the empirical transport excess risk. Rows are labeled
    ``empirical_in_range`` / ``empirical_outside_range`` by whether the target
    score falls inside the SOURCE TRAIN observed ``[min, max]``. This is an
    empirical diagnostic, not a support theorem.
    """
    train_a = [p.score_a for p in train_points]
    train_b = [p.score_b for p in train_points]

    def direction(*, target: str) -> dict[str, Any]:
        if target == "ovr":
            lo, hi = min(train_a), max(train_a)
            diffs = [
                _sample_brier(g_a.apply(p.score_b), p.y) - _sample_brier(g_b.apply(p.score_b), p.y)
                for p in test_points
            ]
            scores = [p.score_b for p in test_points]
            label = "cat_to_ovr"
        else:
            lo, hi = min(train_b), max(train_b)
            diffs = [
                _sample_brier(g_b.apply(p.score_a), p.y) - _sample_brier(g_a.apply(p.score_a), p.y)
                for p in test_points
            ]
            scores = [p.score_a for p in test_points]
            label = "ovr_to_cat"
        n_total = len(test_points)
        in_idx = [i for i, s in enumerate(scores) if lo <= s <= hi]
        out_idx = [i for i, s in enumerate(scores) if s < lo or s > hi]
        in_sum = math.fsum(diffs[i] for i in in_idx)
        out_sum = math.fsum(diffs[i] for i in out_idx)
        overall = math.fsum(diffs) / n_total if n_total else None
        in_contribution = in_sum / n_total if n_total else None
        out_contribution = out_sum / n_total if n_total else None
        return {
            "direction": label,
            "source_train_min": lo,
            "source_train_max": hi,
            "n_total": n_total,
            "n_in_range": len(in_idx),
            "n_outside_range": len(out_idx),
            "fraction_outside_range": (len(out_idx) / n_total) if n_total else None,
            "mean_transport_loss_difference_in_range": (in_sum / len(in_idx) if in_idx else None),
            "mean_transport_loss_difference_outside_range": (
                out_sum / len(out_idx) if out_idx else None
            ),
            "in_range_contribution": in_contribution,
            "outside_range_contribution": out_contribution,
            "overall_transport_delta": overall,
        }

    result = {"cat_to_ovr": direction(target="ovr"), "ovr_to_cat": direction(target="cat")}
    for label, entry in result.items():
        if entry["in_range_contribution"] is None or entry["outside_range_contribution"] is None:
            continue
        summed = entry["in_range_contribution"] + entry["outside_range_contribution"]
        if abs(summed - entry["overall_transport_delta"]) > 1e-9:
            raise ValueError(f"observed-range decomposition for {label!r} does not add up")
    return result


def strata_summary(
    *,
    plan: Any,
    dataset: Any,
    stratum_by_item: Mapping[str, str],
    cat_records: Sequence[Mapping[str, Any]],
    ovr_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Descriptive per-stratum summaries (never separate per-stratum fits)."""
    test_points = analysis.scored_points(dataset, split=Split.TEST)
    truth_by_item = {item.item_id: str(item.ground_truth_value) for item in plan.items}
    cat_winner = analysis.winner_by_item(cat_records)
    ovr_winner = analysis.winner_by_item(ovr_records)
    strata = sorted({stratum_by_item[p.item_id] for p in test_points})
    summary: dict[str, Any] = {}
    for stratum in strata:
        points = [p for p in test_points if stratum_by_item[p.item_id] == stratum]
        if not points:
            continue
        n = len(points)
        cat_acc = sum(1 for p in points if cat_winner.get(p.item_id) == truth_by_item[p.item_id])
        ovr_acc = sum(1 for p in points if ovr_winner.get(p.item_id) == truth_by_item[p.item_id])
        summary[stratum] = {
            "n": n,
            "raw_cat_brier": analysis.brier([(p.score_a, p.y) for p in points]),
            "raw_ovr_brier": analysis.brier([(p.score_b, p.y) for p in points]),
            "mean_cat_anchor_score": math.fsum(p.score_a for p in points) / n,
            "mean_ovr_anchor_score": math.fsum(p.score_b for p in points) / n,
            "cat_winner_accuracy": cat_acc / n,
            "ovr_winner_accuracy": ovr_acc / n,
        }
    return summary


def build_r2b_analysis_artifact(
    *,
    plan: Any,
    dataset: Any,
    stratum_by_item: Mapping[str, str],
    case_set_version: str,
    case_set_fingerprint: str,
    run_provenance: Any,
    cat_records: Sequence[Mapping[str, Any]],
    ovr_records: Sequence[Mapping[str, Any]],
    outcomes_a: Sequence[Any],
    outcomes_b: Sequence[Any],
    l2_strength: float = analysis.PILOT_L2_STRENGTH,
    test_bootstrap_replicates: int = PAIRED_TEST_BOOTSTRAP_REPLICATES,
    train_refit_replicates: int = PAIRED_TRAIN_REFIT_BOOTSTRAP_REPLICATES,
) -> dict[str, Any]:
    """Assemble the R2B analysis artifact from one frozen measurement run."""
    train_points = analysis.scored_points(dataset, split=Split.TRAIN)
    test_points = analysis.scored_points(dataset, split=Split.TEST)
    g_a = analysis.fit_pilot_calibrator(
        source_measurement=plan.measurement_a,
        training_rows=[(p.item_id, p.score_a, p.y) for p in train_points],
        plan_fingerprint=plan.fingerprint,
        l2_strength=l2_strength,
    )
    g_b = analysis.fit_pilot_calibrator(
        source_measurement=plan.measurement_b,
        training_rows=[(p.item_id, p.score_b, p.y) for p in train_points],
        plan_fingerprint=plan.fingerprint,
        l2_strength=l2_strength,
    )
    truth_by_item = {item.item_id: str(item.ground_truth_value) for item in plan.items}
    test_ids = {p.item_id for p in test_points}
    cat_winners = analysis.winner_by_item([r for r in cat_records if r["item_id"] in test_ids])
    ovr_winners = analysis.winner_by_item([r for r in ovr_records if r["item_id"] in test_ids])
    winner_diag = analysis.winner_diagnostics(
        truth_by_item={i: truth_by_item[i] for i in sorted(cat_winners)},
        winner_a_by_item=cat_winners,
        winner_b_by_item=ovr_winners,
    )
    non_simplex = analysis.ovr_non_simplex_diagnostics(
        candidate_score_sums=[float(r["candidate_score_sum"]) for r in ovr_records],
        over_half_counts=[
            sum(1 for c in r["candidates"] if c["probability_true"] > 0.5) for r in ovr_records
        ],
    )
    return {
        "artifact_type": R2B_ANALYSIS_ARTIFACT_TYPE,
        "artifact_version": R2B_ANALYSIS_ARTIFACT_VERSION,
        "research_spec_id": _integrity.RESEARCH_SPEC_ID,
        "research_spec_version": _integrity.RESEARCH_SPEC_VERSION,
        "source_case_set_version": case_set_version,
        "source_case_set_fingerprint": case_set_fingerprint,
        "plan_fingerprint": plan.fingerprint,
        "paired_dataset_fingerprint": dataset.fingerprint,
        "r2b_run_provenance_fingerprint": run_provenance.fingerprint,
        "measurement_a": plan.measurement_a.measurement_id,
        "measurement_b": plan.measurement_b.measurement_id,
        "l2_strength": l2_strength,
        "numerical_kernel": r2b_provenance.numerical_kernel_provenance(l2_strength=l2_strength),
        "percentile_rule": {"id": PERCENTILE_RULE_ID, "version": PERCENTILE_RULE_VERSION},
        "completeness": {
            "planned_n": len(plan.items),
            "train_planned_n": sum(1 for i in plan.items if i.split is Split.TRAIN),
            "test_planned_n": sum(1 for i in plan.items if i.split is Split.TEST),
            "cat_scored": sum(1 for o in outcomes_a if o.status is MeasurementStatus.SCORED),
            "ovr_scored": sum(1 for o in outcomes_b if o.status is MeasurementStatus.SCORED),
            "paired_scored_train_n": len(train_points),
            "paired_scored_test_n": len(test_points),
            "train_y1": sum(1 for p in train_points if p.y == 1.0),
            "train_y0": sum(1 for p in train_points if p.y == 0.0),
            "test_y1": sum(1 for p in test_points if p.y == 1.0),
            "test_y0": sum(1 for p in test_points if p.y == 0.0),
        },
        "train_item_ids": [p.item_id for p in train_points],
        "test_item_ids": [p.item_id for p in test_points],
        "calibrator_a": g_a.canonical_payload(),
        "calibrator_a_fingerprint": g_a.fingerprint,
        "calibrator_b": g_b.canonical_payload(),
        "calibrator_b_fingerprint": g_b.fingerprint,
        "brier_matrix": analysis.brier_matrix(test_points, g_a, g_b),
        "raw_relative_brier_changes": analysis.raw_relative_brier_changes(test_points, g_a, g_b),
        "logloss_matrix": analysis.logloss_matrix(test_points, g_a, g_b),
        "observed_range_diagnostics": analysis.observed_range_diagnostics(
            train_points, test_points
        ),
        "observed_range_loss_decomposition": observed_range_loss_decomposition(
            train_points, test_points, g_a, g_b
        ),
        "paired_test_bootstrap": paired_test_bootstrap(
            test_points, g_a, g_b, replicates=test_bootstrap_replicates
        ),
        "train_refit_bootstrap": train_refit_bootstrap(
            train_points,
            test_points,
            plan=plan,
            l2_strength=l2_strength,
            replicates=train_refit_replicates,
        ),
        "strata_summary": strata_summary(
            plan=plan,
            dataset=dataset,
            stratum_by_item=stratum_by_item,
            cat_records=cat_records,
            ovr_records=ovr_records,
        ),
        "winner_diagnostics": winner_diag,
        "ovr_non_simplex_diagnostics": non_simplex,
    }


def analyze_r2b_raw_artifact(
    raw: Mapping[str, Any], *, cases_path: str | Path | None = None
) -> dict[str, Any]:
    """Deterministically rebuild the R2B analysis artifact from a frozen raw one.

    No model is loaded and no network is touched. The plan, dataset, and outcomes
    are rebuilt from the raw artifact and their fingerprints re-checked against
    the recorded lineage; any mismatch fails closed.
    """
    r2b_plan = _load_sibling("r2b_plan")
    measurements = _load_sibling("measurements")
    payload = r2b_plan.load_case_set(cases_path or r2b_plan.DEFAULT_CASES_PATH)
    if r2b_plan.case_set_fingerprint(payload) != raw["source_case_set_fingerprint"]:
        raise ValueError("case set fingerprint does not match the raw artifact lineage")
    config = raw["model_configuration"]
    plan = r2b_plan.build_plan(payload, model_id=config["model"], model_revision=config["revision"])
    if plan.fingerprint != raw["plan_fingerprint"]:
        raise ValueError("plan fingerprint does not match the raw artifact lineage")
    cat_records = raw["cat_raw_records"]
    ovr_records = raw["ovr_raw_records"]
    outcomes_a = tuple(measurements.cat_outcome(record) for record in cat_records)
    outcomes_b = tuple(measurements.ovr_outcome(record) for record in ovr_records)
    dataset = _integrity.PairedFixedDecisionDataset.create(plan, outcomes_a, outcomes_b)
    if dataset.fingerprint != raw["paired_dataset_fingerprint"]:
        raise ValueError("paired dataset fingerprint does not match the raw artifact lineage")
    provenance = r2b_provenance.R2BRunProvenance(
        source_case_set_version=raw["source_case_set_version"],
        source_case_set_fingerprint=raw["source_case_set_fingerprint"],
        plan=plan,
        git_commit=raw["r2b_run_provenance_canonical_payload"]["code_provenance"]["git_commit"],
        git_worktree_clean=raw["git_worktree_clean"],
    )
    if provenance.fingerprint != raw["r2b_run_provenance_fingerprint"]:
        raise ValueError("run provenance fingerprint does not match the raw artifact lineage")
    stratum_by_item = {case.item_id: case.stratum for case in r2b_plan.r2b_cases(payload)}
    return build_r2b_analysis_artifact(
        plan=plan,
        dataset=dataset,
        stratum_by_item=stratum_by_item,
        case_set_version=raw["source_case_set_version"],
        case_set_fingerprint=raw["source_case_set_fingerprint"],
        run_provenance=provenance,
        cat_records=cat_records,
        ovr_records=ovr_records,
        outcomes_a=outcomes_a,
        outcomes_b=outcomes_b,
    )


def _main(argv: Sequence[str]) -> int:
    """Regenerate the derived R2B analysis artifact from a frozen raw artifact."""
    if len(argv) != 2:
        print("usage: r2b_stability.py <raw-artifact.json>", file=sys.stderr)
        return 2
    raw_path = Path(argv[1])
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    artifact = analyze_r2b_raw_artifact(raw)
    out_path = raw_path.with_name(raw_path.stem + "-analysis.json")
    text = json.dumps(artifact, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
    out_path.write_text(text + "\n", encoding="utf-8")
    print(f"wrote {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
