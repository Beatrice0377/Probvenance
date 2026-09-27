"""Offline tests for the R2B run provenance (parent identity + code provenance).

No model, no GPU, no network. These tests lock that the run provenance commits
the source population CONTENT, the plan, the model, both measurement identities,
the protocols, the research target/input-score identities, and the code commit —
and that it contains no wall-clock timestamp and rejects a dirty tree.
"""

from __future__ import annotations

import importlib.util
import json
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


r2b_plan = _load("r2b_plan")
r2b_provenance = _load("r2b_provenance")

_REVISION = "15852e8c16360a2fea060d615a32b45270f8a8fc"


def _provenance(payload: dict[str, Any], *, clean: bool = True) -> Any:
    plan = r2b_plan.build_plan(payload, model_id="Qwen/Qwen3.5-2B", model_revision=_REVISION)
    return r2b_provenance.build_r2b_run_provenance(
        source_case_set_version=r2b_plan.R2B_CASE_SET_VERSION,
        source_case_set_fingerprint=r2b_plan.case_set_fingerprint(payload),
        plan=plan,
        git_commit="a" * 40,
        git_worktree_clean=clean,
    )


def test_provenance_commits_the_required_parent_identity() -> None:
    payload = r2b_plan.load_case_set()
    provenance = _provenance(payload)
    canonical = provenance.canonical_payload()
    for key in (
        "artifact",
        "provenance_version",
        "research_spec_id",
        "research_spec_version",
        "round_id",
        "round_version",
        "source_case_set_version",
        "source_case_set_fingerprint",
        "plan",
        "plan_fingerprint",
        "model_id",
        "model_revision",
        "measurement_a",
        "measurement_b",
        "anchor_protocol_id",
        "anchor_protocol_version",
        "split_protocol_id",
        "split_protocol_version",
        "fixed_decision_target_id",
        "fixed_decision_target_version",
        "fixed_decision_input_score_id",
        "fixed_decision_input_score_version",
        "code_provenance",
    ):
        assert key in canonical
    assert canonical["round_id"] == "r2b"
    assert canonical["fixed_decision_target_id"] == "fixed-decision-correctness"
    assert canonical["fixed_decision_input_score_id"] == "fixed-decision-semantic-probability"
    assert canonical["model_revision"] == _REVISION
    assert canonical["code_provenance"] == {"git_commit": "a" * 40, "git_worktree_clean": True}


def test_provenance_has_no_wall_clock_identity() -> None:
    canonical = _provenance(r2b_plan.load_case_set()).canonical_payload()
    text = json.dumps(canonical, sort_keys=True)
    for forbidden in ("timestamp", "duration", "created_at", "wall_time", "elapsed"):
        assert forbidden not in text


def test_provenance_fingerprint_is_deterministic() -> None:
    payload = r2b_plan.load_case_set()
    assert _provenance(payload).fingerprint == _provenance(payload).fingerprint


def test_source_content_change_changes_the_run_identity() -> None:
    payload_a = r2b_plan.load_case_set()
    payload_b = r2b_plan.load_case_set()
    # Same item ids and labels, different question/context content.
    payload_b["cases"][0]["context"] = payload_b["cases"][0]["context"] + " Please help."
    assert r2b_plan.case_set_fingerprint(payload_a) != r2b_plan.case_set_fingerprint(payload_b)
    assert _provenance(payload_a).fingerprint != _provenance(payload_b).fingerprint


def test_dirty_working_tree_is_rejected() -> None:
    try:
        _provenance(r2b_plan.load_case_set(), clean=False)
    except ValueError as exc:
        assert "clean" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("run provenance accepted a dirty working tree")


def test_numerical_kernel_provenance_records_the_frozen_kernel() -> None:
    kernel = r2b_provenance.numerical_kernel_provenance(l2_strength=0.01)
    assert kernel["objective"] == {"id": "mean-bernoulli-nll-plus-l2", "version": 1}
    assert kernel["solver"] == {"id": "newton-backtracking", "version": 2}
    assert kernel["input_transform"] == {"id": "identity-selected-probability", "version": 1}
    assert kernel["endpoint_policy"] == {"id": "exact-raw-selected-probability", "version": 1}
    assert kernel["convergence"] == {"id": "strong-convexity-objective-gap", "version": 1}
    assert kernel["l2_strength"] == 0.01
    assert kernel["regularized_parameters"] == ["slope", "intercept"]


def test_git_code_provenance_reads_head_and_cleanliness() -> None:
    commit, clean = r2b_provenance.git_code_provenance(REPO_ROOT)
    assert len(commit) == 40
    assert all(c in "0123456789abcdef" for c in commit)
    assert isinstance(clean, bool)
