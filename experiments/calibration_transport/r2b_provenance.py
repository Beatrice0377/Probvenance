"""R2B run-level parent provenance (research-only).

R1's :class:`~integrity.PairedFixedDecisionPlan` fingerprint commits the frozen
decisions (model, identities, protocols, items) but not the source population
CONTENT (the question, contexts, and candidate descriptions). R2A's evidence
chain stays intact because it also records a ``source_case_set_fingerprint``.

R2B strengthens that parent identity with an experiment-local run provenance
that commits the exact source case-set content fingerprint, the exact R1 plan,
the model, both measurement identities, the anchor/split protocols, the research
target/input-score identities, and the pre-measurement code provenance (git
commit + clean working tree). This is a research-run identity, not a production
artifact, and it deliberately contains no wall-clock timestamp.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from probvenance.fingerprint import JSONValue, fingerprint

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


pilot_plan = _load_sibling("pilot_plan")
# Derive the integrity module from pilot_plan (the single source the R2A
# research modules use) instead of loading ``integrity`` by name, so a test
# loader that re-registers ``integrity`` cannot split the class identity.
_integrity = pilot_plan._integrity
RESEARCH_SPEC_ID = _integrity.RESEARCH_SPEC_ID
RESEARCH_SPEC_VERSION = _integrity.RESEARCH_SPEC_VERSION
FIXED_DECISION_TARGET_ID = _integrity.FIXED_DECISION_TARGET_ID
FIXED_DECISION_TARGET_VERSION = _integrity.FIXED_DECISION_TARGET_VERSION
FIXED_DECISION_INPUT_SCORE_ID = _integrity.FIXED_DECISION_INPUT_SCORE_ID
FIXED_DECISION_INPUT_SCORE_VERSION = _integrity.FIXED_DECISION_INPUT_SCORE_VERSION

R2B_RUN_PROVENANCE_VERSION = 1
R2B_ROUND_ID = "r2b"
R2B_ROUND_VERSION = 1


def _require_non_empty_str(value: object, *, field_name: str) -> str:
    if isinstance(value, bool) or not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty str")
    return value


@dataclass(frozen=True, slots=True)
class R2BRunProvenance:
    """The parent research identity of one R2B run (no timestamp, no secrets)."""

    source_case_set_version: str
    source_case_set_fingerprint: str
    plan: Any
    git_commit: str
    git_worktree_clean: bool

    def __post_init__(self) -> None:
        _require_non_empty_str(self.source_case_set_version, field_name="source_case_set_version")
        _require_non_empty_str(
            self.source_case_set_fingerprint, field_name="source_case_set_fingerprint"
        )
        if not isinstance(self.plan, _integrity.PairedFixedDecisionPlan):
            raise ValueError("plan must be a PairedFixedDecisionPlan")
        _require_non_empty_str(self.git_commit, field_name="git_commit")
        if self.git_worktree_clean is not True:
            raise ValueError(
                "code provenance requires a clean git working tree before the first measurement"
            )

    def canonical_payload(self) -> dict[str, JSONValue]:
        plan = self.plan
        return {
            "artifact": "r2b-run-provenance",
            "provenance_version": R2B_RUN_PROVENANCE_VERSION,
            "research_spec_id": RESEARCH_SPEC_ID,
            "research_spec_version": RESEARCH_SPEC_VERSION,
            "round_id": R2B_ROUND_ID,
            "round_version": R2B_ROUND_VERSION,
            "source_case_set_version": self.source_case_set_version,
            "source_case_set_fingerprint": self.source_case_set_fingerprint,
            "plan": plan.canonical_payload(),
            "plan_fingerprint": plan.fingerprint,
            "model_id": plan.model_id,
            "model_revision": plan.model_revision,
            "measurement_a": {
                "measurement_id": plan.measurement_a.measurement_id,
                "measurement_version": plan.measurement_a.measurement_version,
            },
            "measurement_b": {
                "measurement_id": plan.measurement_b.measurement_id,
                "measurement_version": plan.measurement_b.measurement_version,
            },
            "anchor_protocol_id": plan.anchor_selection_id,
            "anchor_protocol_version": plan.anchor_selection_version,
            "split_protocol_id": plan.split_protocol_id,
            "split_protocol_version": plan.split_protocol_version,
            "fixed_decision_target_id": FIXED_DECISION_TARGET_ID,
            "fixed_decision_target_version": FIXED_DECISION_TARGET_VERSION,
            "fixed_decision_input_score_id": FIXED_DECISION_INPUT_SCORE_ID,
            "fixed_decision_input_score_version": FIXED_DECISION_INPUT_SCORE_VERSION,
            "code_provenance": {
                "git_commit": self.git_commit,
                "git_worktree_clean": self.git_worktree_clean,
            },
        }

    @property
    def fingerprint(self) -> str:
        """Deterministic SHA-256 over the run-provenance canonical payload."""
        return fingerprint(self.canonical_payload())


def build_r2b_run_provenance(
    *,
    source_case_set_version: str,
    source_case_set_fingerprint: str,
    plan: Any,
    git_commit: str,
    git_worktree_clean: bool,
) -> R2BRunProvenance:
    """Build the R2B run provenance; requires a clean pre-measurement tree."""
    return R2BRunProvenance(
        source_case_set_version=source_case_set_version,
        source_case_set_fingerprint=source_case_set_fingerprint,
        plan=plan,
        git_commit=git_commit,
        git_worktree_clean=git_worktree_clean,
    )


def numerical_kernel_provenance(*, l2_strength: float) -> dict[str, Any]:
    """Identity of the reused production numerical kernel (research record only).

    R2B reuses the production L2-logistic numerical kernel so the pilot cannot
    quietly implement a second, drifting optimizer. Recording the kernel identity
    is provenance, NOT reusing ``CalibrationProfile`` semantics: the research
    semantic input stays ``fixed-decision-semantic-probability`` v1.
    """
    from probvenance.calibration import (
        _L2_LOGISTIC_CONVERGENCE_ID,
        _L2_LOGISTIC_CONVERGENCE_VERSION,
        _L2_LOGISTIC_ENDPOINT_POLICY_ID,
        _L2_LOGISTIC_ENDPOINT_POLICY_VERSION,
        _L2_LOGISTIC_INPUT_TRANSFORM_ID,
        _L2_LOGISTIC_INPUT_TRANSFORM_VERSION,
        _L2_LOGISTIC_OBJECTIVE_ID,
        _L2_LOGISTIC_OBJECTIVE_VERSION,
        _L2_LOGISTIC_SOLVER_ID,
        _L2_LOGISTIC_SOLVER_VERSION,
        L2_LOGISTIC_SELECTED_PROBABILITY_METHOD_ID,
        L2_LOGISTIC_SELECTED_PROBABILITY_METHOD_VERSION,
    )

    return {
        "method_id": L2_LOGISTIC_SELECTED_PROBABILITY_METHOD_ID,
        "method_version": L2_LOGISTIC_SELECTED_PROBABILITY_METHOD_VERSION,
        "objective": {"id": _L2_LOGISTIC_OBJECTIVE_ID, "version": _L2_LOGISTIC_OBJECTIVE_VERSION},
        "solver": {"id": _L2_LOGISTIC_SOLVER_ID, "version": _L2_LOGISTIC_SOLVER_VERSION},
        "input_transform": {
            "id": _L2_LOGISTIC_INPUT_TRANSFORM_ID,
            "version": _L2_LOGISTIC_INPUT_TRANSFORM_VERSION,
        },
        "endpoint_policy": {
            "id": _L2_LOGISTIC_ENDPOINT_POLICY_ID,
            "version": _L2_LOGISTIC_ENDPOINT_POLICY_VERSION,
        },
        "convergence": {
            "id": _L2_LOGISTIC_CONVERGENCE_ID,
            "version": _L2_LOGISTIC_CONVERGENCE_VERSION,
        },
        "l2_strength": float(l2_strength),
        "regularized_parameters": ["slope", "intercept"],
    }


def library_runtime_provenance() -> dict[str, Any]:
    """Best-effort library/runtime metadata for the raw artifact (no secrets).

    Package versions are read from installed distribution metadata; CUDA details
    are read only if ``torch`` is importable. Missing values are recorded as
    ``None`` rather than omitted, so the provenance shape is stable.
    """
    import platform
    from importlib import metadata

    def version(name: str) -> str | None:
        try:
            return metadata.version(name)
        except Exception:
            return None

    provenance: dict[str, Any] = {
        "python": platform.python_version(),
        "torch": version("torch"),
        "transformers": version("transformers"),
        "huggingface_hub": version("huggingface_hub"),
        "safetensors": version("safetensors"),
        "torch_cuda_version": None,
        "cuda_available": False,
        "gpu_name": None,
    }
    try:
        import torch

        provenance["torch_cuda_version"] = getattr(torch.version, "cuda", None)
        provenance["cuda_available"] = bool(torch.cuda.is_available())
        if torch.cuda.is_available():
            provenance["gpu_name"] = torch.cuda.get_device_name(0)
    except Exception:
        pass
    return provenance


def git_code_provenance(repo_root: str | Path) -> tuple[str, bool]:
    """Return ``(HEAD commit SHA, is working tree clean)`` for one repository.

    Uses ``git rev-parse HEAD`` and ``git status --porcelain``. Raises on failure
    so the official runner can fail closed before the first measurement.
    """
    import subprocess

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(repo_root),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(repo_root),
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return commit, status.strip() == ""
