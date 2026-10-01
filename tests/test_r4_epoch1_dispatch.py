"""Operational tests for the R4 Epoch 1 execution-environment dispatcher.

These tests are operational only. They never load a model, never read a study
row, and never produce a scientific outcome. They assert the dispatch
invariants required before any formal Epoch 1 execution:

* every frozen cell maps to exactly one model and exactly one interpreter;
* one model uses one and only one environment across all of its populations;
* unknown models are rejected;
* the frozen ``legacy model x MMLU`` domain is rejected;
* the offline flags are always applied.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CAL_DIR = REPO_ROOT / "experiments" / "calibration_transport"
LAUNCH_PATH = CAL_DIR / "r4_epoch1_launch.py"
RUNNER_PATH = CAL_DIR / "run_r4_measurements.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


launcher = _load(LAUNCH_PATH, "r4_epoch1_launch")
runner = _load(RUNNER_PATH, "r4_epoch1_runner")

R0 = "/root/rivermind-data/envs/probvenance-r4/bin/python"
C1 = "/root/rivermind-data/envs/probvenance-r4-kernel-c1/bin/python"

DEFAULT_SELECTION = {
    "olmo-3-7b-instruct": ("R0", R0),
    "falcon-h1-7b-instruct": ("C1", C1),
    "granite-4-0-h-tiny": ("R0", R0),
    "qwen3-5-9b": ("R0", R0),
    "minicpm5-2b": ("R0", R0),
    "qwen3-5-2b": ("R0", R0),
}


def _entry(model_key, env, interpreter):
    return {
        "model_key": model_key,
        "selected_environment": env,
        "interpreter_path": interpreter,
    }


def _map_payload(selection=None):
    selection = DEFAULT_SELECTION if selection is None else selection
    return {
        "environment_map_id": "test",
        "models": [_entry(k, e, p) for k, (e, p) in selection.items()],
    }


@pytest.fixture()
def environment_map(tmp_path):
    path = tmp_path / "map.json"
    path.write_text(json.dumps(_map_payload()), encoding="utf-8")
    return launcher.load_environment_map(path)


def _frozen_cells():
    cells = []
    for model_key in runner.ALL_MODEL_KEYS:
        for population_key in runner.POPULATION_REGISTRY:
            try:
                runner.resolve_cell(model_key, population_key)
            except runner.R4MeasurementDomainError:
                continue
            cells.append((model_key, population_key))
    return cells


def test_frozen_grid_has_exactly_sixteen_cells():
    cells = _frozen_cells()
    assert len(cells) == 16
    assert len(set(cells)) == 16


def test_every_frozen_cell_maps_to_exactly_one_interpreter(environment_map):
    cells = launcher.enumerate_cells(environment_map)
    assert len(cells) == 16
    for cell in cells:
        assert cell["interpreter_path"]
        assert cell["selected_environment"] in {"R0", "C1", "C2", "C3"}


def test_same_model_across_populations_uses_one_environment(environment_map):
    cells = launcher.enumerate_cells(environment_map)
    per_model: dict[str, set[str]] = {}
    for cell in cells:
        per_model.setdefault(cell["model_key"], set()).add(cell["interpreter_path"])
    for model_key, interpreters in per_model.items():
        assert len(interpreters) == 1, f"{model_key} resolved to {interpreters}"


def test_resolve_cell_environment_is_population_independent(environment_map):
    for population_key in runner.POPULATION_REGISTRY:
        resolved = launcher.resolve_cell_environment(
            "falcon-h1-7b-instruct", population_key, environment_map
        )
        assert resolved == "C1"


def test_resolve_cell_environment_requires_a_population(environment_map):
    with pytest.raises(launcher.R4Epoch1DispatchError):
        launcher.resolve_cell_environment("falcon-h1-7b-instruct", "", environment_map)


def test_unknown_model_is_rejected(environment_map):
    with pytest.raises(launcher.R4Epoch1DispatchError):
        launcher.resolve_interpreter("not-a-model", environment_map)


def test_legacy_mmlu_cell_is_outside_the_frozen_domain(environment_map):
    cells = launcher.enumerate_cells(environment_map)
    legacy_mmlu = [
        c
        for c in cells
        if c["population_key"] == "mmlu" and c["model_key"] in runner.LEGACY_MODEL_KEYS
    ]
    assert legacy_mmlu == []
    for legacy in runner.LEGACY_MODEL_KEYS:
        with pytest.raises(runner.R4MeasurementDomainError):
            runner.resolve_cell(legacy, "mmlu")


def test_duplicate_model_key_is_rejected(tmp_path):
    payload = {
        "models": [
            _entry("qwen3-5-9b", "R0", R0),
            _entry("qwen3-5-9b", "C1", C1),
        ]
    }
    path = tmp_path / "dup.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(launcher.R4Epoch1DispatchError):
        launcher.load_environment_map(path)


def test_missing_interpreter_is_rejected(tmp_path):
    payload = {"models": [{"model_key": "qwen3-5-9b", "selected_environment": "R0"}]}
    path = tmp_path / "missing.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(launcher.R4Epoch1DispatchError):
        launcher.load_environment_map(path)


def test_empty_models_list_is_rejected(tmp_path):
    path = tmp_path / "empty.json"
    path.write_text(json.dumps({"models": []}), encoding="utf-8")
    with pytest.raises(launcher.R4Epoch1DispatchError):
        launcher.load_environment_map(path)


def test_offline_flags_are_applied():
    env = launcher.build_offline_environment({"PATH": "/usr/bin"})
    assert env["HF_HUB_OFFLINE"] == "1"
    assert env["TRANSFORMERS_OFFLINE"] == "1"
    assert env["HF_DATASETS_OFFLINE"] == "1"
    assert env["PATH"] == "/usr/bin"


def test_build_command_uses_the_frozen_runner_and_interpreter(environment_map):
    command = launcher.build_command(
        "falcon-h1-7b-instruct",
        environment_map,
        ["--population", "hellaswag", "--staging-root", "/tmp/x"],
    )
    assert command[0] == C1
    assert command[1] == str(RUNNER_PATH)
    assert command[2:] == ["--population", "hellaswag", "--staging-root", "/tmp/x"]


def test_reference_models_always_resolve_to_the_reference_environment(environment_map):
    for model_key in ("olmo-3-7b-instruct", "minicpm5-2b"):
        assert launcher.resolve_interpreter(model_key, environment_map) == R0
