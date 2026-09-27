"""Offline tests for the R3 official measurement runner.

No model, no GPU, no network. A deterministic counting fake backend and the
REAL frozen MMLU manifest exercise the exact official call pattern. These tests
assert call counts, no row substitution, frozen model resolution, and that the
runner never imports the confirmatory analysis module. No confirmatory metric
is computed anywhere in this module.
"""

from __future__ import annotations

import importlib.util
import math
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from probvenance import BackendCapabilities, EvidenceKind, Probvenance, RawEvidence
from probvenance.errors import UnsupportedCapabilityError

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
r3_population = _load("r3_population")
r3_protocol = _load("r3_protocol")
r3_raw_evidence = _load("r3_raw_evidence")
runner = _load("run_r3_measurements")
_integrity = pilot_plan._integrity

CANDIDATES = list(r3_raw_evidence.R3_CANDIDATE_NAMES)
MODEL_META = {
    "model": "synthetic-model",
    "revision": "0" * 40,
    "dtype": "bfloat16",
    "rendering_config": {"enable_thinking": False},
}


class _CountingBackend:
    """Deterministic backend that counts CAT and OVR forwards; optional CAT failure."""

    def __init__(
        self, *, fail_first_cat: bool = False, fail_ovr_at_call: int | None = None
    ) -> None:
        self.capabilities = BackendCapabilities(
            binary_token_logits=True, categorical_token_logits=True
        )
        self.cat_calls = 0
        self.ovr_calls = 0
        self._fail_first_cat = fail_first_cat
        self._fail_ovr_at_call = fail_ovr_at_call

    def execute(self, plan: Any) -> RawEvidence:
        if plan.strategy.value == "binary_token_logits":
            self.ovr_calls += 1
            if self._fail_ovr_at_call is not None and self.ovr_calls == self._fail_ovr_at_call:
                raise UnsupportedCapabilityError("synthetic ineligible OVR proposition")
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
        self.cat_calls += 1
        if self._fail_first_cat and self.cat_calls == 1:
            raise UnsupportedCapabilityError("synthetic ineligible CAT decision")
        values = tuple(
            0.0 if label == "A" else math.log(3.0) if label == "B" else 0.0
            for label in plan.targets
        )
        resolved: list[Any] = [[label, 100 + index] for index, label in enumerate(plan.targets)]
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


def _fake_plan_item(item_id: str, *, anchor: str = "option-0", answer_index: int = 1) -> Any:
    truth = f"option-{answer_index}"
    return SimpleNamespace(
        item_id=item_id,
        anchor_value=anchor,
        ground_truth_value=truth,
        anchor_correct=(anchor == truth),
    )


def _synthetic_manifest_item(
    item_id: str, *, split: str = "TEST", answer_index: int = 1
) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "subject": "abstract_algebra",
        "split": split,
        "source_split": "test" if split == "TEST" else "validation",
        "source_row_index": 0,
        "question": f"Question for {item_id}?",
        "choices": ["alpha", "beta", "gamma", "delta"],
        "answer_index": answer_index,
    }


def _run_synthetic(count: int, backend: Any) -> tuple[list[dict[str, Any]], Any]:
    manifest_items = [
        _synthetic_manifest_item(f"r3-item-{index:04d}", split="TEST" if index else "TRAIN")
        for index in range(count)
    ]
    plan_items = tuple(_fake_plan_item(item["item_id"]) for item in manifest_items)
    plan = SimpleNamespace(items=plan_items)
    manifest_by_id = {item["item_id"]: item for item in manifest_items}
    runtime = Probvenance(backend=backend, capture_rendered_input=True)
    items, _outcomes_a, _outcomes_b = runner.run_condition(
        runtime, plan, manifest_by_id, model_meta=MODEL_META
    )
    return items, runtime


# --------------------------------------------------------------------------- #
# CLI / scientific-configuration guardrails (PART 11)
# --------------------------------------------------------------------------- #


def test_cli_requires_condition_and_output() -> None:
    with pytest.raises(SystemExit):
        runner.parse_args([])
    with pytest.raises(SystemExit):
        runner.parse_args(["--condition", "primary"])
    with pytest.raises(SystemExit):
        runner.parse_args(["--output", "/tmp/x.json"])


def test_cli_rejects_unknown_condition() -> None:
    with pytest.raises(SystemExit):
        runner.parse_args(["--condition", "tertiary", "--output", "/tmp/x.json"])


def test_cli_exposes_no_scientific_configuration() -> None:
    for forbidden in ("--model", "--revision", "--population", "--method", "--panel", "--split"):
        with pytest.raises(SystemExit):
            runner.parse_args(
                ["--condition", "primary", "--output", "/tmp/x.json", forbidden, "value"]
            )


def test_cli_accepts_only_condition_and_output() -> None:
    args = runner.parse_args(["--condition", "replication", "--output", "/tmp/x.json"])
    assert args.condition == "replication"
    assert args.output == "/tmp/x.json"


# --------------------------------------------------------------------------- #
# Frozen identity resolution (PART 3, 12)
# --------------------------------------------------------------------------- #


def test_resolve_condition_returns_exact_frozen_model() -> None:
    design = r3_protocol.load_design()
    primary = runner.resolve_condition(design, "primary")
    replication = runner.resolve_condition(design, "replication")
    assert primary["model_id"] == "openbmb/MiniCPM5-2B"
    assert primary["model_revision"] == "12a3808a956f869c767195e9266b59c4d21d92e2"
    assert replication["model_id"] == "Qwen/Qwen3.5-2B"
    assert replication["model_revision"] == "15852e8c16360a2fea060d615a32b45270f8a8fc"


def test_resolve_condition_rejects_unknown() -> None:
    with pytest.raises(runner.GateError):
        runner.resolve_condition(r3_protocol.load_design(), "tertiary")


def test_verify_frozen_identities_matches_declared_fingerprints() -> None:
    design = r3_protocol.load_design()
    manifest = r3_population.load_manifest()
    identities = runner.verify_frozen_identities(design=design, manifest=manifest)
    assert identities["protocol_fingerprint"] == (
        "3ef63056ae16b18ad65d9c87d1fbec5b43550873a0e3e25ec0a323f954ee974d"
    )
    assert identities["population_manifest_fingerprint"] == (
        "40cc9753a711314ff3b25ed6e234d0cbda11f3f60cd87f1d3915195a3d1780b8"
    )
    assert manifest["counts"]["total"] == r3_raw_evidence.EXPECTED_ITEMS_PER_MODEL


def test_verify_anchors_passes_on_the_frozen_plan() -> None:
    design = r3_protocol.load_design()
    manifest = r3_population.load_manifest()
    primary = runner.resolve_condition(design, "primary")
    plan = r3_protocol.build_child_plan(
        manifest, model_id=primary["model_id"], model_revision=primary["model_revision"]
    )
    assert plan.fingerprint == primary["child_plan_fingerprint"]
    manifest_by_id = {item["item_id"]: item for item in r3_population.manifest_items(manifest)}
    runner.verify_anchors(plan, manifest_by_id)


# --------------------------------------------------------------------------- #
# Call counts (PART 33, 34)
# --------------------------------------------------------------------------- #


def test_measure_item_issues_one_cat_and_four_ovr() -> None:
    backend = _CountingBackend()
    items, _runtime = _run_synthetic(1, backend)
    assert backend.cat_calls == 1
    assert backend.ovr_calls == 4
    assert backend.cat_calls + backend.ovr_calls == 5
    assert items[0]["cat"]["status"] == "scored"
    assert items[0]["ovr"]["status"] == "scored"


def test_three_item_manifest_issues_exactly_fifteen_evaluations() -> None:
    backend = _CountingBackend()
    _run_synthetic(3, backend)
    assert backend.cat_calls == 3
    assert backend.ovr_calls == 12
    assert backend.cat_calls + backend.ovr_calls == 15


def test_all_four_ovr_are_attempted_even_when_one_is_ineligible() -> None:
    # The third OVR forward raises; the runner must still attempt all four.
    backend = _CountingBackend(fail_ovr_at_call=3)
    items, _runtime = _run_synthetic(1, backend)
    assert backend.ovr_calls == 4
    assert backend.cat_calls == 1
    assert items[0]["ovr"]["status"] == "ineligible"
    assert items[0]["ovr"]["record"] is None


def test_full_manifest_logical_call_contract() -> None:
    design = r3_protocol.load_design()
    manifest = r3_population.load_manifest()
    primary = runner.resolve_condition(design, "primary")
    plan = r3_protocol.build_child_plan(
        manifest, model_id=primary["model_id"], model_revision=primary["model_revision"]
    )
    manifest_by_id = {item["item_id"]: item for item in r3_population.manifest_items(manifest)}
    backend = _CountingBackend()
    runtime = Probvenance(backend=backend, capture_rendered_input=True)
    items, outcomes_a, outcomes_b = runner.run_condition(
        runtime, plan, manifest_by_id, model_meta=MODEL_META
    )
    assert backend.cat_calls == 1596
    assert backend.ovr_calls == 6384
    assert backend.cat_calls + backend.ovr_calls == 7980
    assert len(items) == 1596
    assert len(outcomes_a) == 1596
    assert len(outcomes_b) == 1596
    assert [item["item_id"] for item in items] == [
        item["item_id"] for item in r3_population.manifest_items(manifest)
    ]


# --------------------------------------------------------------------------- #
# No row substitution (PART 35)
# --------------------------------------------------------------------------- #


def test_ineligible_cat_retains_the_same_item_without_substitution() -> None:
    backend = _CountingBackend(fail_first_cat=True)
    items, _runtime = _run_synthetic(3, backend)
    assert [item["item_id"] for item in items] == ["r3-item-0000", "r3-item-0001", "r3-item-0002"]
    assert items[0]["cat"]["status"] == "ineligible"
    assert items[0]["cat"]["record"] is None
    assert items[1]["cat"]["status"] == "scored"
    # The failing item is retained in place; no substitute item appears.
    assert len(items) == 3


# --------------------------------------------------------------------------- #
# Isolation from confirmatory analysis (PART 15)
# --------------------------------------------------------------------------- #


def test_runner_never_imports_confirmatory_analysis() -> None:
    runner_path = HARNESS_DIR / "run_r3_measurements.py"
    script = (
        "import importlib.util, sys;"
        "spec = importlib.util.spec_from_file_location("
        f"'run_r3_measurements', {str(runner_path)!r});"
        "mod = importlib.util.module_from_spec(spec);"
        "sys.modules['run_r3_measurements'] = mod;"
        "spec.loader.exec_module(mod);"
        "assert 'r3_analysis' not in sys.modules, sorted(sys.modules);"
        "print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "PYTHONPATH": str(SRC)},
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_runner_does_not_reference_the_analysis_module_by_name() -> None:
    source = (HARNESS_DIR / "run_r3_measurements.py").read_text(encoding="utf-8")
    for line in source.splitlines():
        stripped = line.strip()
        assert not stripped.startswith("import r3_analysis")
        assert not stripped.startswith("from r3_analysis")
        assert '_load_sibling("r3_analysis")' not in stripped
