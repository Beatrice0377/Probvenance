"""Offline tests for the R2 CAT/OVR measurement adapters.

No model, no GPU, no network. A tiny deterministic fake backend exercises the
REAL runtime path; pure unit tests lock the frozen anchor-score semantics.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path
from typing import Any

from probvenance import (
    BackendCapabilities,
    Certainty,
    ChoiceResult,
    EvidenceKind,
    Probvenance,
    RawEvidence,
)
from probvenance.errors import UnsupportedCapabilityError
from probvenance.fingerprint import fingerprint

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


pilot_plan = _load("pilot_plan")
measurements = _load("measurements")
_integrity = pilot_plan._integrity


class _FakeBackend:
    """Deterministic backend with honest metadata for both strategies."""

    def __init__(self) -> None:
        self.capabilities = BackendCapabilities(
            binary_token_logits=True, categorical_token_logits=True
        )

    def execute(self, plan: Any) -> RawEvidence:
        if plan.strategy.value == "binary_token_logits":
            return RawEvidence(
                kind=EvidenceKind.LOGITS,
                labels=("false", "true"),
                values=(0.0, math.log(3.0)),
                plan_fingerprint=plan.fingerprint,
                metadata={
                    "vocab_logsumexp": math.log(4.0),
                    "top_token_id": 9642,
                    "top_token_logit": math.log(3.0),
                    "positive_token_id": 9642,
                    "negative_token_id": 3134,
                },
            )
        values = tuple(
            0.0 if label == "A" else math.log(3.0) if label == "B" else 0.0
            for label in plan.targets
        )
        resolved = [[label, 100 + index] for index, label in enumerate(plan.targets)]
        metadata: dict[str, Any] = {
            "vocab_logsumexp": math.log(6.0),
            "top_token_id": 101,
            "top_token_logit": math.log(3.0),
            "resolved_target_token_ids": resolved,
        }
        return RawEvidence(
            kind=EvidenceKind.LOGITS,
            labels=plan.targets,
            values=values,
            plan_fingerprint=plan.fingerprint,
            metadata=metadata,
        )


def _candidate_set() -> tuple[tuple[str, str | None], ...]:
    return pilot_plan.source_candidates(pilot_plan.load_case_set())


# --------------------------------------------------------------------------- #
# Pure anchor-score semantics
# --------------------------------------------------------------------------- #


def _choice_result(probabilities: dict[str, float]) -> ChoiceResult:
    return ChoiceResult(
        certainty=Certainty.from_probabilities(list(probabilities.values())),
        method="test",
        probabilities=probabilities,
    )


def test_cat_anchor_score_is_the_anchor_mass_not_the_winner_mass() -> None:
    result = _choice_result({"billing": 0.6, "shipping": 0.3, "technical": 0.1})
    assert measurements.cat_winner(result) == "billing"
    assert measurements.cat_anchor_score(result, "shipping") == 0.3
    assert measurements.cat_anchor_score(result, "shipping") != 0.6


def test_ovr_anchor_score_is_the_anchor_score_not_the_winner_score() -> None:
    scores = {"billing": 0.8, "shipping": 0.7, "technical": 0.2}
    order = ["billing", "shipping", "technical"]
    assert measurements.ovr_winner(scores, order) == "billing"
    assert measurements.ovr_anchor_score(scores, "shipping") == 0.7


def test_ovr_scores_are_never_renormalized() -> None:
    scores = {"billing": 0.8, "shipping": 0.7, "technical": 0.2}
    order = ["billing", "shipping", "technical"]
    raw = {name: measurements.ovr_anchor_score(scores, name) for name in order}
    assert raw == {"billing": 0.8, "shipping": 0.7, "technical": 0.2}
    assert math.fsum(raw.values()) == 1.7
    assert raw != {
        "billing": 0.47058823529411764,
        "shipping": 0.4117647058823529,
        "technical": 0.11764705882352941,
    }


def test_ovr_winner_tie_break_follows_candidate_order() -> None:
    scores = {"billing": 0.5, "shipping": 0.5, "technical": 0.1}
    assert measurements.ovr_winner(scores, ["billing", "shipping", "technical"]) == "billing"
    assert measurements.ovr_winner(scores, ["shipping", "billing", "technical"]) == "shipping"


# --------------------------------------------------------------------------- #
# OVR proposition determinism and isolation
# --------------------------------------------------------------------------- #


def test_ovr_proposition_is_deterministic_and_candidate_sensitive() -> None:
    question = "Which team should handle this request?"
    context = "The app crashes on launch."
    first = measurements.build_ovr_proposition(question, context, "technical", "Software")
    second = measurements.build_ovr_proposition(question, context, "technical", "Software")
    other = measurements.build_ovr_proposition(question, context, "billing", "Software")
    assert first.fingerprint == second.fingerprint
    assert first.fingerprint != other.fingerprint


def test_ovr_proposition_isolates_ground_truth_and_other_candidates() -> None:
    proposition = measurements.build_ovr_proposition(
        "Which team should handle this request?",
        "My parcel is late.",
        "shipping",
        "Delivery, tracking, and logistics",
    )
    text = proposition.question
    assert "Original question:" in text
    assert "shipping" in text
    assert "billing" not in text
    assert "technical" not in text


def test_ovr_proposition_renders_none_description_and_has_no_outcome_params() -> None:
    import inspect

    proposition = measurements.build_ovr_proposition("Q?", None, "billing", None)
    assert "(none)" in proposition.question
    assert list(inspect.signature(measurements.build_ovr_proposition).parameters) == [
        "question",
        "context",
        "candidate_name",
        "candidate_description",
    ]


# --------------------------------------------------------------------------- #
# Integration through the real runtime
# --------------------------------------------------------------------------- #


def test_run_measurements_end_to_end_on_the_frozen_plan() -> None:
    import run_pilot

    payload = pilot_plan.load_case_set()
    plan = pilot_plan.build_plan(payload, model_id="fake-model", model_revision="rev-1")
    cases_by_id = {case.case_id: case for case in pilot_plan.pilot_cases(payload)}
    runtime = Probvenance(backend=_FakeBackend(), capture_rendered_input=True)
    model_meta = {
        "model": "fake-model",
        "revision": "rev-1",
        "dtype": "float32",
        "rendering_config": {},
    }
    cat_records, ovr_records, outcomes_a, outcomes_b = run_pilot.run_measurements(
        runtime, plan, cases_by_id, model_meta=model_meta
    )
    assert len(cat_records) == 15
    assert len(ovr_records) == 15
    assert sum(len(record["candidates"]) for record in ovr_records) == 45
    assert all(outcome.status is _integrity.MeasurementStatus.SCORED for outcome in outcomes_a)
    assert all(outcome.status is _integrity.MeasurementStatus.SCORED for outcome in outcomes_b)

    dataset = _integrity.PairedFixedDecisionDataset.create(plan, outcomes_a, outcomes_b)
    assert len(dataset.rows) == 15
    # A dataset is content-addressed and order-stable.
    assert (
        dataset.fingerprint
        == _integrity.PairedFixedDecisionDataset.create(plan, outcomes_a, outcomes_b).fingerprint
    )


def test_ovr_raw_record_keeps_raw_scores_and_non_simplex_sum() -> None:
    import run_pilot

    payload = pilot_plan.load_case_set()
    plan = pilot_plan.build_plan(payload, model_id="fake-model", model_revision=None)
    cases_by_id = {case.case_id: case for case in pilot_plan.pilot_cases(payload)}
    runtime = Probvenance(backend=_FakeBackend())
    model_meta = {
        "model": "fake-model",
        "revision": None,
        "dtype": "float32",
        "rendering_config": {},
    }
    _cat, ovr_records, _a, _b = run_pilot.run_measurements(
        runtime, plan, cases_by_id, model_meta=model_meta
    )
    for record in ovr_records:
        scores = {c["candidate"]: c["probability_true"] for c in record["candidates"]}
        assert record["candidate_score_sum"] == math.fsum(scores.values())
        assert record["anchor_score"] == scores[record["anchor"]]


def test_outcome_source_record_id_is_content_addressed() -> None:
    import run_pilot

    payload = pilot_plan.load_case_set()
    plan = pilot_plan.build_plan(payload, model_id="fake-model", model_revision=None)
    cases_by_id = {case.case_id: case for case in pilot_plan.pilot_cases(payload)}
    runtime = Probvenance(backend=_FakeBackend())
    model_meta = {
        "model": "fake-model",
        "revision": None,
        "dtype": "float32",
        "rendering_config": {},
    }
    cat_records, ovr_records, outcomes_a, outcomes_b = run_pilot.run_measurements(
        runtime, plan, cases_by_id, model_meta=model_meta
    )
    assert outcomes_a[0].source_record_id == fingerprint(dict(cat_records[0]))
    assert outcomes_b[0].source_record_id == fingerprint(dict(ovr_records[0]))


def test_classify_measurement_exception_fails_fast_on_unknown_errors() -> None:
    classified = measurements.classify_measurement_exception(
        UnsupportedCapabilityError("no binary capability")
    )
    assert classified is not None
    assert classified[0] is _integrity.MeasurementStatus.INELIGIBLE
    assert measurements.classify_measurement_exception(ValueError("bug")) is None
