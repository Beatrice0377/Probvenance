"""Operational-only Epoch 1 execution-environment dispatcher.

This module is **operational**. It is not part of the R4 scientific evidence
fingerprint and it changes no scientific semantic. It does exactly four things:

1. resolve a frozen ``model_key`` to exactly one frozen Python interpreter path;
2. build the offline environment flags used by the formal runbook;
3. refuse unknown models and refuse the frozen ``legacy model x MMLU`` domain;
4. delegate to the frozen scientific runner ``run_r4_measurements.py``.

It never reads, computes, or exposes scores, probabilities, outcomes, Brier,
LogLoss, calibration, bootstrap, or predictor values.

The scientific runner is deliberately **not** modified. The environment is
selected purely by which interpreter executes it.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

CAL_DIR = Path(__file__).resolve().parent

ENVIRONMENT_MAP_PATH = CAL_DIR / "R4_EPOCH1_MODEL_EXECUTION_ENVIRONMENT_MAP.json"
RUNNER_PATH = CAL_DIR / "run_r4_measurements.py"

OFFLINE_ENVIRONMENT = {
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "HF_DATASETS_OFFLINE": "1",
}


class R4Epoch1DispatchError(RuntimeError):
    """Raised when a model key or cell cannot be dispatched to exactly one environment."""


def load_environment_map(path: Path | str = ENVIRONMENT_MAP_PATH) -> dict:
    """Load and minimally validate the frozen model -> environment map."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    models = payload.get("models")
    if not isinstance(models, list) or not models:
        raise R4Epoch1DispatchError("environment map has no 'models' list")
    seen: set[str] = set()
    for entry in models:
        key = entry.get("model_key")
        if not key:
            raise R4Epoch1DispatchError("environment map entry without model_key")
        if key in seen:
            raise R4Epoch1DispatchError(f"environment map has duplicate model_key {key!r}")
        seen.add(key)
        if not entry.get("selected_environment"):
            raise R4Epoch1DispatchError(f"model {key!r} has no selected_environment")
        if not entry.get("interpreter_path"):
            raise R4Epoch1DispatchError(f"model {key!r} has no interpreter_path")
    return payload


def _models_by_key(environment_map: dict) -> dict[str, dict]:
    return {entry["model_key"]: entry for entry in environment_map["models"]}


def resolve_interpreter(model_key: str, environment_map: dict) -> str:
    """Return the single frozen interpreter path for ``model_key``."""
    entry = _models_by_key(environment_map).get(model_key)
    if entry is None:
        raise R4Epoch1DispatchError(f"unknown model key {model_key!r}")
    return entry["interpreter_path"]


def resolve_environment_name(model_key: str, environment_map: dict) -> str:
    entry = _models_by_key(environment_map).get(model_key)
    if entry is None:
        raise R4Epoch1DispatchError(f"unknown model key {model_key!r}")
    return entry["selected_environment"]


def resolve_cell_environment(model_key: str, population_key: str, environment_map: dict) -> str:
    """Every population of one model must resolve to the same environment.

    The map is keyed by model only, so this is structural: there is no way to
    express a per-population environment. The function exists so the invariant
    is testable and is asserted explicitly.
    """
    if not population_key:
        raise R4Epoch1DispatchError("population_key is required")
    return resolve_environment_name(model_key, environment_map)


def build_offline_environment(base: dict | None = None) -> dict:
    env = dict(os.environ if base is None else base)
    env.update(OFFLINE_ENVIRONMENT)
    return env


def build_command(model_key: str, environment_map: dict, runner_args: list[str]) -> list[str]:
    interpreter = resolve_interpreter(model_key, environment_map)
    return [interpreter, str(RUNNER_PATH), *runner_args]


def enumerate_cells(environment_map: dict) -> list[dict]:
    """Return the frozen 16-cell grid with the resolved interpreter per cell.

    The grid comes from the frozen runner registries so that this dispatcher can
    never disagree with the scientific runner about which cells exist.
    """
    runner = _load_runner()
    cells: list[dict] = []
    for model_key in runner.ALL_MODEL_KEYS:
        for population_key in runner.POPULATION_REGISTRY:
            try:
                cell = runner.resolve_cell(model_key, population_key)
            except runner.R4MeasurementDomainError:
                continue
            cells.append(
                {
                    "model_key": model_key,
                    "population_key": population_key,
                    "population_id": cell["population_id"],
                    "train_budget": cell["train_budget"],
                    "interpreter_path": resolve_interpreter(model_key, environment_map),
                    "selected_environment": resolve_environment_name(model_key, environment_map),
                }
            )
    return cells


def _load_runner():
    import importlib.util

    spec = importlib.util.spec_from_file_location("r4_epoch1_runner", RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="R4 Epoch 1 execution-environment dispatcher")
    parser.add_argument("--environment-map", default=str(ENVIRONMENT_MAP_PATH))
    parser.add_argument("--model-key")
    parser.add_argument("--list-cells", action="store_true")
    parser.add_argument("--print-interpreter", action="store_true")
    parser.add_argument("runner_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    environment_map = load_environment_map(args.environment_map)

    if args.list_cells:
        for cell in enumerate_cells(environment_map):
            print(
                f"{cell['model_key']:24s} {cell['population_key']:10s} "
                f"{cell['selected_environment']:4s} {cell['interpreter_path']}"
            )
        return 0

    if not args.model_key:
        parser.error("--model-key is required unless --list-cells is given")

    if args.print_interpreter:
        print(resolve_interpreter(args.model_key, environment_map))
        return 0

    runner_args = list(args.runner_args)
    if runner_args and runner_args[0] == "--":
        runner_args = runner_args[1:]
    if not runner_args:
        parser.error("no runner arguments given after '--'")

    command = build_command(args.model_key, environment_map, runner_args)
    selected = resolve_environment_name(args.model_key, environment_map)
    print(f"# dispatching {args.model_key} -> {selected}")
    print("# " + " ".join(command))
    return subprocess.call(command, env=build_offline_environment())


if __name__ == "__main__":
    sys.exit(main())
