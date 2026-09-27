"""CAT and OVR probability-measurement definitions for the R2 pilot.

Research-only measurement adapters. Given one pre-frozen anchor decision
``D_i`` from a :class:`~integrity.PairedFixedDecisionPlan`, they produce two
scores for that SAME anchor:

- **CAT** (``direct-categorical-anchor-probability`` v1): the anchor
  candidate's probability mass in the mutually-exclusive categorical
  restricted-softmax distribution. This is ``probability[anchor]``, never the
  categorical winner's mass.
- **OVR** (``independent-binary-anchor-probability`` v1): the anchor
  candidate's raw ``probability_true`` from its OWN independent binary semantic
  judgment. This is ``p_true(anchor)``, never the OVR winner's score, and it is
  never renormalized across the candidate set.

Neither adapter reuses ``winner_correctness`` or
``uncalibrated-selected-probability``. They run no model and fit nothing: they
build the exact decisions/records and translate caller-provided evaluations
into the R1 outcome contract.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from probvenance import (
    BoolDecision,
    BoolResult,
    Choice,
    ChoiceDecision,
    ChoiceResult,
)
from probvenance.diagnostics import ChoiceScoringDiagnostics, ScoringDiagnostics
from probvenance.errors import (
    ScoringLabelError,
    UnsupportedCapabilityError,
    UnsupportedDecisionError,
)
from probvenance.fingerprint import fingerprint
from probvenance.runtime import Evaluation

_HARNESS_DIR = Path(__file__).resolve().parent


def _load_integrity() -> Any:
    module = sys.modules.get("integrity")
    if module is not None:
        return module
    spec = importlib.util.spec_from_file_location("integrity", _HARNESS_DIR / "integrity.py")
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load integrity.py from {_HARNESS_DIR}")
    loaded = importlib.util.module_from_spec(spec)
    sys.modules["integrity"] = loaded
    spec.loader.exec_module(loaded)
    return loaded


_integrity = _load_integrity()
MeasurementStatus = _integrity.MeasurementStatus
MeasurementOutcome = _integrity.MeasurementOutcome
MeasurementProtocolIdentity = _integrity.MeasurementProtocolIdentity

CAT_MEASUREMENT_ID = "direct-categorical-anchor-probability"
CAT_MEASUREMENT_VERSION = 1

OVR_MEASUREMENT_ID = "independent-binary-anchor-probability"
OVR_MEASUREMENT_VERSION = 1

OVR_PROPOSITION_ID = "choice-candidate-correctness-binary-judgment"
OVR_PROPOSITION_VERSION = 1

#: The fixed research-only OVR proposition template. It renders ONLY the
#: original question, the original context, and the one designated candidate.
#: It deliberately does not include ground truth, other candidates' scores, or
#: any CAT output, so the binary judgment is independent of the categorical one.
_OVR_PROPOSITION_TEMPLATE = (
    "For the original choice task, is the designated candidate the correct answer?\n"
    "\n"
    "Original question:\n"
    "{question}\n"
    "\n"
    "Designated candidate:\n"
    "{candidate_name}\n"
    "\n"
    "Candidate description:\n"
    "{candidate_description}\n"
)


def cat_identity() -> Any:
    """The frozen CAT measurement identity (v1)."""
    return MeasurementProtocolIdentity(CAT_MEASUREMENT_ID, CAT_MEASUREMENT_VERSION)


def ovr_identity() -> Any:
    """The frozen OVR measurement identity (v1)."""
    return MeasurementProtocolIdentity(OVR_MEASUREMENT_ID, OVR_MEASUREMENT_VERSION)


def build_cat_decision(
    question: str,
    context: Any,
    candidates: Sequence[tuple[str, str | None]],
) -> ChoiceDecision:
    """Build the ordinary CAT ChoiceDecision in exact source candidate order.

    No label permutation, no candidate paraphrase, and no extra candidate are
    applied; the runtime compiles the natural scoring-label scheme.
    """
    return ChoiceDecision(
        question,
        context=context,
        choices=tuple(Choice(name, description) for name, description in candidates),
    )


def cat_anchor_score(result: ChoiceResult, anchor: str) -> float:
    """``S_CAT = result.probabilities[anchor]`` (never the winner's mass)."""
    probabilities = result.probabilities
    if anchor not in probabilities:
        raise ValueError(
            f"anchor {anchor!r} is not a candidate of the CAT result "
            f"(candidates: {sorted(probabilities)})"
        )
    return float(probabilities[anchor])


def cat_winner(result: ChoiceResult) -> str:
    """The CAT measurement's own winner, diagnostic only."""
    return result.value


def build_ovr_proposition(
    question: str,
    context: Any,
    candidate_name: str,
    candidate_description: str | None,
) -> BoolDecision:
    """Build the deterministic research-only OVR binary proposition.

    Only the original question, the original context, and the one designated
    candidate enter the proposition. A ``None`` description renders as ``(none)``.
    """
    text = _OVR_PROPOSITION_TEMPLATE.format(
        question=question,
        candidate_name=candidate_name,
        candidate_description="(none)" if candidate_description is None else candidate_description,
    )
    return BoolDecision(text, context=context)


def ovr_anchor_score(candidate_scores: Mapping[str, float], anchor: str) -> float:
    """``S_OVR = candidate_scores[anchor]`` (raw, never renormalized)."""
    if anchor not in candidate_scores:
        raise ValueError(
            f"anchor {anchor!r} is not a scored candidate (candidates: {sorted(candidate_scores)})"
        )
    return float(candidate_scores[anchor])


def ovr_winner(candidate_scores: Mapping[str, float], candidate_order: Sequence[str]) -> str:
    """Deterministic argmax over raw OVR scores with candidate-order tie-break.

    Diagnostic only: it never changes the frozen anchor score and never decides
    row inclusion. The OVR scores are independent binary measurements, so this
    argmax is not a categorical distribution over the candidate set.
    """
    best_name: str | None = None
    best_score = float("-inf")
    for name in candidate_order:
        score = float(candidate_scores[name])
        if best_name is None or score > best_score:
            best_name = name
            best_score = score
    if best_name is None:
        raise ValueError("candidate_order must contain at least one candidate")
    return best_name


def classify_measurement_exception(exc: BaseException) -> tuple[Any, str] | None:
    """Classify a DECLARED measurement inability, or return ``None`` to fail fast.

    Only an explicit, named capability/semantic inability is returned as
    ``(MeasurementStatus.INELIGIBLE, reason)``. Any other exception returns
    ``None`` so the caller re-raises it: an unknown exception is an
    implementation failure and must never be silently recorded as research data.
    """
    if isinstance(exc, (ScoringLabelError, UnsupportedCapabilityError, UnsupportedDecisionError)):
        return MeasurementStatus.INELIGIBLE, f"{type(exc).__name__}: {exc}"
    return None


def failure_source_record_id(*, protocol: str, item_id: str, status: Any, reason: str) -> str:
    """Content-addressed id for a missing/ineligible outcome record."""
    return fingerprint(
        {
            "protocol": protocol,
            "item_id": item_id,
            "status": status.value,
            "reason": reason,
        }
    )


def _model_meta_fields(model_meta: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "model": model_meta["model"],
        "revision": model_meta.get("revision"),
        "dtype": model_meta.get("dtype"),
        "rendering_config": dict(model_meta.get("rendering_config", {})),
    }


def build_cat_raw_record(
    evaluation: Evaluation,
    *,
    case_id: str,
    item_id: str,
    anchor: str,
    model_meta: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the exact CAT raw record (content-addressed evidence)."""
    result = evaluation.result
    trace = evaluation.trace
    if not isinstance(result, ChoiceResult):
        raise TypeError(f"CAT requires a ChoiceResult, got {type(result).__name__}")
    diagnostics = trace.scoring_diagnostics
    if not isinstance(diagnostics, ChoiceScoringDiagnostics):
        raise TypeError(f"CAT requires ChoiceScoringDiagnostics, got {type(diagnostics).__name__}")
    return {
        "protocol": CAT_MEASUREMENT_ID,
        "protocol_version": CAT_MEASUREMENT_VERSION,
        "case_id": case_id,
        "item_id": item_id,
        "anchor": anchor,
        "anchor_score": cat_anchor_score(result, anchor),
        "winner": cat_winner(result),
        "candidate_order": [entry.candidate_name for entry in trace.candidate_mapping],
        "mapping": {entry.candidate_name: entry.scoring_label for entry in trace.candidate_mapping},
        "labels": [entry.scoring_label for entry in trace.candidate_mapping],
        "probabilities": {name: float(value) for name, value in result.probabilities.items()},
        "scoring_label_mass": float(diagnostics.scoring_label_mass),
        "scoring_label_token_probabilities": [
            float(value) for value in diagnostics.scoring_label_token_probabilities
        ],
        "resolved_token_ids": {
            label: int(token_id) for label, token_id in trace.resolved_target_token_ids
        },
        "decision_fingerprint": trace.decision_fingerprint,
        "plan_fingerprint": trace.plan_fingerprint,
        "execution_fingerprint": trace.execution_fingerprint,
        "trace_id": trace.trace_id,
        **_model_meta_fields(model_meta),
    }


def build_ovr_raw_record(
    *,
    case_id: str,
    item_id: str,
    anchor: str,
    candidate_order: Sequence[str],
    evaluations: Mapping[str, Evaluation],
    model_meta: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the exact OVR raw record from one independent binary judgment per candidate."""
    per_candidate: list[dict[str, Any]] = []
    candidate_scores: dict[str, float] = {}
    for name in candidate_order:
        evaluation = evaluations[name]
        result = evaluation.result
        trace = evaluation.trace
        diagnostics = trace.scoring_diagnostics
        if not isinstance(result, BoolResult):
            raise TypeError(f"OVR requires a BoolResult, got {type(result).__name__}")
        if not isinstance(diagnostics, ScoringDiagnostics):
            raise TypeError(f"OVR requires ScoringDiagnostics, got {type(diagnostics).__name__}")
        score = float(result.probability_true)
        candidate_scores[name] = score
        per_candidate.append(
            {
                "candidate": name,
                "probability_true": score,
                "probability_true_ge_half": score >= 0.5,
                "verbalizer_mass": float(diagnostics.verbalizer_mass),
                "positive_token_probability": float(diagnostics.positive_token_probability),
                "negative_token_probability": float(diagnostics.negative_token_probability),
                "positive_token_id": int(trace.positive_token_id),
                "negative_token_id": int(trace.negative_token_id),
                "decision_fingerprint": trace.decision_fingerprint,
                "plan_fingerprint": trace.plan_fingerprint,
                "execution_fingerprint": trace.execution_fingerprint,
                "trace_id": trace.trace_id,
            }
        )
    return {
        "protocol": OVR_MEASUREMENT_ID,
        "protocol_version": OVR_MEASUREMENT_VERSION,
        "proposition_id": OVR_PROPOSITION_ID,
        "proposition_version": OVR_PROPOSITION_VERSION,
        "case_id": case_id,
        "item_id": item_id,
        "anchor": anchor,
        "anchor_score": ovr_anchor_score(candidate_scores, anchor),
        "winner": ovr_winner(candidate_scores, candidate_order),
        "candidate_score_sum": math.fsum(candidate_scores[name] for name in candidate_order),
        "candidates": per_candidate,
        **_model_meta_fields(model_meta),
    }


def cat_outcome(record: Mapping[str, Any]) -> Any:
    """Translate a CAT raw record into an R1 SCORED outcome."""
    return MeasurementOutcome(
        item_id=str(record["item_id"]),
        status=MeasurementStatus.SCORED,
        anchor_score=float(record["anchor_score"]),
        winner_value=str(record["winner"]),
        source_record_id=fingerprint(dict(record)),
        reason=None,
    )


def ovr_outcome(record: Mapping[str, Any]) -> Any:
    """Translate an OVR raw record into an R1 SCORED outcome."""
    return MeasurementOutcome(
        item_id=str(record["item_id"]),
        status=MeasurementStatus.SCORED,
        anchor_score=float(record["anchor_score"]),
        winner_value=str(record["winner"]),
        source_record_id=fingerprint(dict(record)),
        reason=None,
    )
