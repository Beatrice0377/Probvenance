"""R4 formal raw measurement runner (measurement execution only).

For every frozen ``model x population x item`` cell this runner performs exactly
ONE categorical (CAT) forward and exactly ONE designated-candidate binary (OVR)
forward -- the frozen ``r4-fixed-event-two-forward-measurement`` contract -- and
writes ONE raw-evidence artifact per ``model x population`` block.

It deliberately does NOT fit a calibrator, compute Brier / LogLoss, run a
bootstrap, or compute predictor values. It loads frozen structural authority
only; it never reads a study outcome and never fabricates one.

The scientific configuration (model revision, population manifest, verbalizers,
anchor rule, TRAIN budget, TEST identity) comes from frozen authority. The CLI
only selects which already-frozen cell to measure and where to write it.
"""

from __future__ import annotations

import argparse
import contextlib
import gc
import importlib.util
import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

# Offline defaults must be in place before transformers / huggingface_hub are
# imported anywhere in this process. The formal runner never downloads.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_DATASETS_OFFLINE", "1")
os.environ.setdefault("HF_HOME", "/root/rivermind-data/hf-cache")
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", "/root/rivermind-data/hf-cache/hub")

REPO_ROOT = Path(__file__).resolve().parents[2]
CAL_DIR = Path(__file__).resolve().parent
SEMANTIC_SIGNAL_DIR = REPO_ROOT / "experiments" / "semantic_signal"
POPULATION_CANDIDATE_DIR = Path("/root/rivermind-data/r4-population-candidates")

from probvenance import Probvenance  # noqa: E402
from probvenance.compiler import BoolCompiler, ChoiceCompiler  # noqa: E402
from probvenance.fingerprint import fingerprint  # noqa: E402

DEVICE_DEFAULT = "cuda:0"
DTYPE = "bfloat16"
CHAT_TEMPLATE_KWARGS: dict[str, Any] = {"enable_thinking": False}

# Frozen measurement-execution authority (this task's closure).
MEASUREMENT_CONTRACT_PATH = CAL_DIR / "R4_MEASUREMENT_EXECUTION_CONTRACT.json"
FINAL_PROTOCOL_CANDIDATE_PATH = CAL_DIR / "R4_FINAL_PROTOCOL_SEMANTIC_CANDIDATE.json"
EXECUTION_MANIFEST_CANDIDATE_PATH = CAL_DIR / "R4_EXECUTION_MANIFEST_CANDIDATE.json"
FINAL_PROTOCOL_FREEZE_PATH = CAL_DIR / "R4_FINAL_PROTOCOL_FREEZE.json"
EXECUTION_MANIFEST_FREEZE_PATH = CAL_DIR / "R4_EXECUTION_MANIFEST_FREEZE.json"

# Operational staging (crash-safe resume). Never part of the scientific fingerprint.
# Mirrors r4_staging.DEFAULT_STAGING_ROOT (that module is loaded further below).
DEFAULT_STAGING_ROOT = "/root/rivermind-data/r4-formal-measurements"

# Frozen R4 anchor rule (see R4_FINAL_PROTOCOL_SEMANTIC_CANDIDATE.json anchor_identity).
ANCHOR_PROTOCOL_ID = "r4-fixed-event-anchor-deterministic-source-index-hash"
ANCHOR_PROTOCOL_VERSION = 1

SYNTH_QUESTION = "Synthetic runner check. Which option is the designated candidate?"
SYNTH_CANDIDATES: tuple[tuple[str, str | None], ...] = (
    ("Alpha", "First synthetic option."),
    ("Beta", "Second synthetic option."),
    ("Gamma", "Third synthetic option."),
    ("Delta", "Fourth synthetic option."),
)
_FORBIDDEN_DATASET_MARKERS = ("mmlu", "hellaswag", "medmcqa", "commonsenseqa", "arc_", "openbookqa")


class R4MeasurementError(RuntimeError):
    """Base error for the R4 measurement runner."""


class R4MeasurementDomainError(R4MeasurementError, ValueError):
    """The requested (model role, population) cell is outside the frozen R4 plan."""


class R4MeasurementEnvironmentDrift(R4MeasurementError):
    """The runtime does not match the frozen R4 measurement environment contract."""


class R4VerbalizerIdentityDrift(R4MeasurementError):
    """A tokenizer no longer resolves the frozen verbalizer identities."""


class R4MeasurementInterfaceDrift(R4MeasurementError):
    """The production measurement interface no longer matches the frozen contract."""


class R4ModelCacheMissing(R4MeasurementError):
    """The frozen model revision is not present in the local offline cache."""


def _load_sibling(name: str) -> Any:
    """Load a sibling harness module idempotently (stable class identity)."""
    module = sys.modules.get(name)
    if module is not None:
        return module
    spec = importlib.util.spec_from_file_location(name, CAL_DIR / f"{name}.py")
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load {name}.py from {CAL_DIR}")
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


def _load_semantic_module(name: str) -> Any:
    """Load a module from experiments/semantic_signal (e.g. qwen35_loader)."""
    module = sys.modules.get(name)
    if module is not None:
        return module
    spec = importlib.util.spec_from_file_location(name, SEMANTIC_SIGNAL_DIR / f"{name}.py")
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load {name}.py from {SEMANTIC_SIGNAL_DIR}")
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


r4_raw_evidence = _load_sibling("r4_raw_evidence")
r4_staging = _load_sibling("r4_staging")
measurements = r4_raw_evidence._measurements
integrity = r4_raw_evidence.integrity
MeasurementStatus = integrity.MeasurementStatus


# --------------------------------------------------------------------------- #
# Frozen registries
# --------------------------------------------------------------------------- #

MODEL_REGISTRY: dict[str, dict[str, Any]] = {
    "olmo-3-7b-instruct": {
        "model_id": "allenai/Olmo-3-7B-Instruct",
        "revision": "6e5971d9eba42665f5bd5a0fcf047f299ce1dccc",
        "role": "current-generation",
        "adapter": "transformers_backend",
        "expected_cat_ids": {"A": 32, "B": 33, "C": 34, "D": 35},
        "expected_positive_token_id": 9891,
        "expected_negative_token_id": 2201,
    },
    "falcon-h1-7b-instruct": {
        "model_id": "tiiuae/Falcon-H1-7B-Instruct",
        "revision": "41e72f27effbab80cd45b6e884688452253a3686",
        "role": "current-generation",
        "adapter": "transformers_backend",
        "expected_cat_ids": {"A": 1068, "B": 1069, "C": 1070, "D": 1071},
        "expected_positive_token_id": 5763,
        "expected_negative_token_id": 3257,
    },
    "granite-4-0-h-tiny": {
        "model_id": "ibm-granite/granite-4.0-h-tiny",
        "revision": "791e0d3d28c86e106c9b6e0b4cecdee0375b6124",
        "role": "current-generation",
        "adapter": "transformers_backend",
        "expected_cat_ids": {"A": 32, "B": 33, "C": 34, "D": 35},
        "expected_positive_token_id": 9891,
        "expected_negative_token_id": 2201,
    },
    "qwen3-5-9b": {
        "model_id": "Qwen/Qwen3.5-9B",
        "revision": "c202236235762e1c871ad0ccb60c8ee5ba337b9a",
        "role": "current-generation",
        "adapter": "qwen35_text",
        "expected_cat_ids": {"A": 32, "B": 33, "C": 34, "D": 35},
        "expected_positive_token_id": 9405,
        "expected_negative_token_id": 2083,
    },
    "minicpm5-2b": {
        "model_id": "openbmb/MiniCPM5-2B",
        "revision": "12a3808a956f869c767195e9266b59c4d21d92e2",
        "role": "legacy-lineage",
        "adapter": "transformers_backend",
        "expected_cat_ids": {"A": 54, "B": 55, "C": 56, "D": 57},
        "expected_positive_token_id": 15876,
        "expected_negative_token_id": 3707,
    },
    "qwen3-5-2b": {
        "model_id": "Qwen/Qwen3.5-2B",
        "revision": "15852e8c16360a2fea060d615a32b45270f8a8fc",
        "role": "legacy-lineage",
        "adapter": "qwen35_text",
        "expected_cat_ids": {"A": 32, "B": 33, "C": 34, "D": 35},
        "expected_positive_token_id": 9405,
        "expected_negative_token_id": 2083,
    },
}

CURRENT_GENERATION_MODEL_KEYS = (
    "olmo-3-7b-instruct",
    "falcon-h1-7b-instruct",
    "granite-4-0-h-tiny",
    "qwen3-5-9b",
)
LEGACY_MODEL_KEYS = ("minicpm5-2b", "qwen3-5-2b")
ALL_MODEL_KEYS = CURRENT_GENERATION_MODEL_KEYS + LEGACY_MODEL_KEYS

#: MMLU is measured only for the current-generation panel. The R3 legacy MMLU
#: cells are FROZEN_EXISTING / DO_NOT_RERUN and are not runnable in R4.
MMLU_MODEL_KEYS = CURRENT_GENERATION_MODEL_KEYS
#: The new populations are measured for the full six-model panel.
NEW_POPULATION_MODEL_KEYS = ALL_MODEL_KEYS

POPULATION_REGISTRY: dict[str, dict[str, Any]] = {
    "mmlu": {
        "population_id": "r4-mmlu-57-subject",
        "dataset_id": "cais/mmlu",
        "dataset_revision": "c30699e8356da336a370243923dbaf21066bb9fe",
        "source": "r3_manifest",
        "primary": {
            "manifest_fingerprint": (
                "40cc9753a711314ff3b25ed6e234d0cbda11f3f60cd87f1d3915195a3d1780b8"
            ),
            "train_rows": 456,
            "test_rows": 1140,
        },
    },
    "hellaswag": {
        "population_id": "r4-hellaswag-activity-primary",
        "dataset_id": "Rowan/hellaswag",
        "dataset_revision": "218ec52e09a7e7462a5400043bb9a69a41d06b76",
        "source": "manifest_file",
        "primary": {
            "path": str(POPULATION_CANDIDATE_DIR / "hellaswag_population_candidate.json"),
            "manifest_fingerprint": (
                "5c45043ba4f0ec436c16dcf494ff26be435c7857244bcbefa321d1678129c400"
            ),
            "train_rows": 456,
            "test_rows": 10042,
        },
        "robustness912": {
            "path": str(
                POPULATION_CANDIDATE_DIR / "hellaswag_population_robustness912_candidate.json"
            ),
            "manifest_fingerprint": (
                "6817496f227d9cd57759bf55489cbf8a1dc4dfd27db0ae551e9223d21d02a096"
            ),
            "train_rows": 912,
            "test_rows": 10042,
        },
    },
    "medmcqa": {
        "population_id": "r4-medmcqa-subject-primary",
        "dataset_id": "openlifescienceai/medmcqa",
        "dataset_revision": "91c6572c454088bf71b679ad90aa8dffcd0d5868",
        "source": "manifest_file",
        "primary": {
            "path": str(POPULATION_CANDIDATE_DIR / "medmcqa_population_candidate.json"),
            "manifest_fingerprint": (
                "4a4718438d46ab1ba27c59ca46806756ffb62efa05e6103981dffec4dc48c218"
            ),
            "train_rows": 456,
            "test_rows": 4162,
        },
        "robustness912": {
            "path": str(
                POPULATION_CANDIDATE_DIR / "medmcqa_population_robustness912_candidate.json"
            ),
            "manifest_fingerprint": (
                "e48c37293f196e16d8fba42e7fc255e4ac2e77f81c270ed6f71320981968af12"
            ),
            "train_rows": 912,
            "test_rows": 4162,
        },
    },
}

TRAIN_BUDGET_N456 = "N456"
TRAIN_BUDGET_N912 = "N912"

# Frozen R4 measurement environment contract (see
# R4_MEASUREMENT_EXECUTION_ENVIRONMENT.md). nvidia-smi CUDA compatibility is NOT
# the torch runtime and is deliberately not asserted here.
EXPECTED_PYTHON_MAJOR_MINOR = "3.11"
EXPECTED_TORCH_VERSION = "2.8.0+cu128"
EXPECTED_TRANSFORMERS_VERSION = "5.17.0"
EXPECTED_HUGGINGFACE_HUB_VERSION = "1.32.0"


# --------------------------------------------------------------------------- #
# Frozen identity helpers
# --------------------------------------------------------------------------- #


def anchor_index(*, dataset_id: str, revision: str, source_split: str, row_index: int) -> int:
    """Frozen R4 measurement-independent anchor (protocol + source coordinates)."""
    digest = fingerprint(
        {
            "protocol_id": ANCHOR_PROTOCOL_ID,
            "protocol_version": ANCHOR_PROTOCOL_VERSION,
            "dataset_id": dataset_id,
            "dataset_revision": revision,
            "source_split": source_split,
            "source_row_index": row_index,
        }
    )
    return int(digest[:16], 16) % 4


def resolve_train_budget(model_key: str, population_key: str) -> str:
    """The frozen TRAIN budget for one cell (current N912 union, legacy N456)."""
    entry = MODEL_REGISTRY[model_key]
    if population_key == "mmlu":
        return TRAIN_BUDGET_N456
    if entry["role"] == "current-generation":
        return TRAIN_BUDGET_N912
    return TRAIN_BUDGET_N456


def _require_model(model_key: str) -> dict[str, Any]:
    if model_key not in MODEL_REGISTRY:
        raise R4MeasurementDomainError(f"unknown model key {model_key!r}")
    return MODEL_REGISTRY[model_key]


def _require_population(population_key: str) -> dict[str, Any]:
    if population_key not in POPULATION_REGISTRY:
        raise R4MeasurementDomainError(f"unknown population {population_key!r}")
    return POPULATION_REGISTRY[population_key]


def resolve_cell(model_key: str, population_key: str) -> dict[str, Any]:
    """Resolve one frozen (model, population) cell to its required row identity."""
    entry = _require_model(model_key)
    population = _require_population(population_key)
    if population_key == "mmlu" and entry["role"] != "current-generation":
        raise R4MeasurementDomainError(
            "legacy + MMLU is outside the frozen R4 plan (R3 legacy MMLU cells are "
            "FROZEN_EXISTING / DO_NOT_RERUN)"
        )
    budget = resolve_train_budget(model_key, population_key)
    if budget == TRAIN_BUDGET_N912:
        if "robustness912" not in population:
            raise R4MeasurementDomainError(
                f"{population_key} has no N912 robustness manifest for {model_key}"
            )
        manifest_ref = population["robustness912"]
    else:
        manifest_ref = population["primary"]
    train_rows, test_rows = _load_population_rows(population_key, manifest_ref)
    expected_train = int(manifest_ref["train_rows"])
    expected_test = int(manifest_ref["test_rows"])
    if len(train_rows) != expected_train:
        raise R4MeasurementDomainError(
            f"{population_key}: expected {expected_train} TRAIN rows, got {len(train_rows)}"
        )
    if len(test_rows) != expected_test:
        raise R4MeasurementDomainError(
            f"{population_key}: expected {expected_test} TEST rows, got {len(test_rows)}"
        )
    required_rows = list(train_rows) + list(test_rows)
    return {
        "model_key": model_key,
        "population_key": population_key,
        "model": entry,
        "population": population,
        "population_id": population["population_id"],
        "population_manifest_fingerprint": str(manifest_ref["manifest_fingerprint"]),
        "dataset_id": population["dataset_id"],
        "dataset_revision": population["dataset_revision"],
        "train_budget": budget,
        "train_rows": train_rows,
        "test_rows": test_rows,
        "required_rows": required_rows,
    }


def _load_population_rows(
    population_key: str, manifest_ref: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if population_key == "mmlu":
        return _mmlu_rows()
    manifest = json.loads(Path(str(manifest_ref["path"])).read_text(encoding="utf-8"))
    if str(manifest["manifest_fingerprint"]) != str(manifest_ref["manifest_fingerprint"]):
        raise R4MeasurementDomainError(f"{population_key}: population manifest fingerprint drift")
    dataset_id = str(manifest["dataset_id"])
    revision = str(manifest["dataset_revision"])
    train_rows = [_normalize_manifest_row(row, dataset_id=dataset_id, revision=revision)
                  for row in manifest["train"]]
    test_rows = [_normalize_manifest_row(row, dataset_id=dataset_id, revision=revision)
                 for row in manifest["test"]]
    return train_rows, test_rows


def _normalize_manifest_row(
    row: Mapping[str, Any], *, dataset_id: str, revision: str
) -> dict[str, Any]:
    """Re-verify the frozen anchor and expose the fields the evidence layer needs."""
    expected_anchor = anchor_index(
        dataset_id=dataset_id,
        revision=revision,
        source_split=str(row["source_split"]),
        row_index=int(row["source_row_index"]),
    )
    if int(row["anchor_index"]) != expected_anchor:
        raise R4MeasurementDomainError(
            f"anchor drift for item {row['item_id']}: manifest {row['anchor_index']} "
            f"vs recomputed {expected_anchor}"
        )
    return {
        "item_id": str(row["item_id"]),
        "source_split": str(row["source_split"]),
        "source_row_index": int(row["source_row_index"]),
        "split": str(row["split"]),
        "stratum": str(row["stratum"]),
        "group_id": row.get("group_id"),
        "question": str(row["question"]),
        "candidate_names": [str(name) for name in row["candidate_names"]],
        "candidate_descriptions": [str(desc) for desc in row["candidate_descriptions"]],
        "ground_truth_index": int(row["ground_truth_index"]),
        "anchor_index": expected_anchor,
    }


def _mmlu_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Normalize the frozen R3 MMLU manifest into the R4 fixed-event row shape."""
    r3_population = _load_sibling("r3_population")
    manifest = r3_population.load_manifest()
    dataset_id = str(r3_population.MMLU_REPOSITORY)
    revision = str(r3_population.MMLU_REVISION)
    train_rows: list[dict[str, Any]] = []
    test_rows: list[dict[str, Any]] = []
    for item in r3_population.manifest_items(manifest):
        row = {
            "item_id": str(item["item_id"]),
            "source_split": str(item["source_split"]),
            "source_row_index": int(item["source_row_index"]),
            "split": str(item["split"]),
            "stratum": str(item["subject"]),
            "group_id": None,
            "question": str(item["question"]),
            "candidate_names": list(r3_population.R3_CANDIDATE_NAMES),
            "candidate_descriptions": [str(choice) for choice in item["choices"]],
            "ground_truth_index": int(item["answer_index"]),
            "anchor_index": anchor_index(
                dataset_id=dataset_id,
                revision=revision,
                source_split=str(item["source_split"]),
                row_index=int(item["source_row_index"]),
            ),
        }
        if row["split"] == "TRAIN":
            train_rows.append(row)
        else:
            test_rows.append(row)
    return train_rows, test_rows


# --------------------------------------------------------------------------- #
# Frozen authority loading
# --------------------------------------------------------------------------- #


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_frozen_authority() -> dict[str, Any]:
    """Read the frozen measurement/protocol/manifest fingerprints (structural only)."""
    contract = _read_json(MEASUREMENT_CONTRACT_PATH)
    protocol = _read_json(FINAL_PROTOCOL_CANDIDATE_PATH)
    manifest = _read_json(EXECUTION_MANIFEST_CANDIDATE_PATH)
    protocol_freeze = _read_json(FINAL_PROTOCOL_FREEZE_PATH)
    manifest_freeze = _read_json(EXECUTION_MANIFEST_FREEZE_PATH)
    return {
        "measurement_contract_fingerprint": str(contract["measurement_contract_fingerprint"]),
        "measurement_contract_status": str(contract["status"]),
        "final_protocol_candidate_fingerprint": str(protocol["candidate_fingerprint"]),
        "execution_manifest_candidate_fingerprint": str(manifest["manifest_fingerprint"]),
        "final_protocol_fingerprint": str(protocol_freeze["final_protocol_fingerprint"]),
        "final_protocol_status": str(protocol_freeze["status"]),
        "execution_manifest_fingerprint": str(
            manifest_freeze["execution_manifest_fingerprint"]
        ),
        "execution_manifest_status": str(manifest_freeze["status"]),
    }


def measurement_code_commit() -> str:
    """The current Git HEAD, recorded as measurement-code provenance."""
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            check=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:  # pragma: no cover - host only
        raise R4MeasurementError(f"cannot read the measurement-code commit: {exc}") from exc
    return result.stdout.strip()


def verify_git_state(*, require_clean: bool) -> dict[str, Any]:
    """Record the Git state; formal measurement requires branch main + clean tree."""
    branch = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "branch", "--show-current"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    head = measurement_code_commit()
    porcelain = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "status", "--porcelain"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout
    clean = porcelain.strip() == ""
    if branch != "main":
        raise R4MeasurementError(f"formal measurement requires branch main, found {branch!r}")
    if require_clean and not clean:
        raise R4MeasurementError("formal measurement requires a clean worktree")
    return {"branch": branch, "head": head, "worktree_clean": clean}


def verify_environment(*, device: str) -> dict[str, Any]:
    """Assert the frozen R4 measurement environment contract (no mutation)."""
    import huggingface_hub
    import torch
    import transformers

    observed = {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "torch": str(torch.__version__),
        "cuda_runtime": str(torch.version.cuda),
        "transformers": str(transformers.__version__),
        "huggingface_hub": str(huggingface_hub.__version__),
        "device": device,
        "dtype": DTYPE,
    }
    expected = {
        "python": EXPECTED_PYTHON_MAJOR_MINOR,
        "torch": EXPECTED_TORCH_VERSION,
        "transformers": EXPECTED_TRANSFORMERS_VERSION,
        "huggingface_hub": EXPECTED_HUGGINGFACE_HUB_VERSION,
    }
    drift = {
        key: {"expected": value, "observed": observed[key]}
        for key, value in expected.items()
        if observed[key] != value
    }
    if drift:
        raise R4MeasurementEnvironmentDrift(f"R4 measurement environment drift: {drift}")
    if device.startswith("cuda") and not torch.cuda.is_available():
        raise R4MeasurementEnvironmentDrift("torch.cuda.is_available() is False")
    return observed


def verify_offline_environment() -> dict[str, Any]:
    """The formal runner must be fully offline."""
    required = ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE")
    missing = [name for name in required if os.environ.get(name) != "1"]
    if missing:
        raise R4MeasurementEnvironmentDrift(f"offline environment flags not set: {missing}")
    return {
        "HF_HUB_OFFLINE": os.environ["HF_HUB_OFFLINE"],
        "TRANSFORMERS_OFFLINE": os.environ["TRANSFORMERS_OFFLINE"],
        "HF_DATASETS_OFFLINE": os.environ["HF_DATASETS_OFFLINE"],
        "HF_HOME": os.environ.get("HF_HOME"),
        "HUGGINGFACE_HUB_CACHE": os.environ.get("HUGGINGFACE_HUB_CACHE"),
    }


def verify_model_cache(model_key: str) -> dict[str, Any]:
    """Confirm the frozen revision is present locally (no download)."""
    entry = _require_model(model_key)
    cache_root = Path(os.environ.get("HUGGINGFACE_HUB_CACHE", ""))
    repo_dir = cache_root / f"models--{entry['model_id'].replace('/', '--')}"
    snapshots = repo_dir / "snapshots"
    if not snapshots.is_dir():
        raise R4ModelCacheMissing(f"no local snapshot for {entry['model_id']} under {snapshots}")
    revision = str(entry["revision"])
    exact = snapshots / revision
    if not exact.is_dir():
        raise R4ModelCacheMissing(
            f"frozen revision {revision} is not present locally for {entry['model_id']}"
        )
    incomplete = [p.name for p in repo_dir.rglob("*.incomplete")]
    if incomplete:
        raise R4ModelCacheMissing(f"incomplete blobs for {entry['model_id']}: {incomplete}")
    return {"snapshot_path": str(exact), "revision": revision, "incomplete_blobs": incomplete}


def _assert_synthetic_only() -> None:
    text = f"{SYNTH_QUESTION} {' '.join(name for name, _ in SYNTH_CANDIDATES)}".lower()
    for marker in _FORBIDDEN_DATASET_MARKERS:
        if marker in text:
            raise R4MeasurementError(f"synthetic fixture unexpectedly references {marker!r}")


# --------------------------------------------------------------------------- #
# Model loading
# --------------------------------------------------------------------------- #


def load_backend(model_key: str, *, device: str) -> Any:
    """Load one frozen model condition with the frozen runtime contract."""
    entry = _require_model(model_key)
    rendering = dict(CHAT_TEMPLATE_KWARGS)
    if str(entry["adapter"]) == "qwen35_text":
        if str(SEMANTIC_SIGNAL_DIR) not in sys.path:
            sys.path.insert(0, str(SEMANTIC_SIGNAL_DIR))
        qwen35_loader = _load_semantic_module("qwen35_loader")
        return qwen35_loader.Qwen35TextBackend(
            model=entry["model_id"],
            revision=entry["revision"],
            dtype=DTYPE,
            device=device,
            local_files_only=True,
            chat_template_kwargs=rendering,
        )
    from probvenance.backends.transformers import TransformersBackend

    return TransformersBackend(
        entry["model_id"],
        revision=entry["revision"],
        device=device,
        dtype=DTYPE,
        trust_remote_code=False,
        local_files_only=True,
        chat_template_kwargs=rendering,
    )


def unload_backend(backend: Any) -> None:
    """Release the model and the GPU memory it held."""
    model = getattr(backend, "_model", None)
    if model is not None:
        with contextlib.suppress(Exception):  # pragma: no cover - best-effort release
            model.to("cpu")
    del backend
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:  # pragma: no cover - best-effort release
        pass


def _top_token(evaluation: Any) -> dict[str, Any]:
    diagnostics = evaluation.trace.scoring_diagnostics
    return {
        "token_id": int(diagnostics.top_token_id),
        "probability": float(diagnostics.top_token_probability),
        "text": diagnostics.top_token_text,
    }


def verify_verbalizers(backend: Any, model_key: str) -> dict[str, Any]:
    """One synthetic CAT + one synthetic designated OVR to re-resolve exact ids."""
    entry = _require_model(model_key)
    capabilities = backend.capabilities
    cat_plan = ChoiceCompiler().compile(
        measurements.build_cat_decision(SYNTH_QUESTION, None, SYNTH_CANDIDATES),
        capabilities,
    )
    cat_evaluation = backend.execute(cat_plan)
    # The production backend exposes resolved_target_token_ids as a list of
    # [label, token_id] pairs (src/probvenance/backends/transformers.py:273),
    # not as a flat id list.
    resolved_pairs = cat_evaluation.metadata["resolved_target_token_ids"]
    observed_cat = {str(label): int(token_id) for label, token_id in resolved_pairs}
    labels = [str(label) for label in cat_plan.targets]
    resolved = [observed_cat[label] for label in labels]
    expected_cat = {str(k): int(v) for k, v in entry["expected_cat_ids"].items()}
    if observed_cat != expected_cat:
        raise R4VerbalizerIdentityDrift(
            f"{model_key}: CAT verbalizer drift, expected {expected_cat}, observed {observed_cat}"
        )
    if len(set(resolved)) != len(resolved):
        raise R4VerbalizerIdentityDrift(f"{model_key}: CAT labels do not resolve to distinct ids")

    anchor_name, anchor_description = SYNTH_CANDIDATES[2]
    ovr_plan = BoolCompiler().compile(
        measurements.build_ovr_proposition(SYNTH_QUESTION, None, anchor_name, anchor_description),
        capabilities,
    )
    ovr_evaluation = backend.execute(ovr_plan)
    positive_id = int(ovr_evaluation.metadata["positive_token_id"])
    negative_id = int(ovr_evaluation.metadata["negative_token_id"])
    if positive_id != int(entry["expected_positive_token_id"]):
        raise R4VerbalizerIdentityDrift(
            f"{model_key}: positive verbalizer drift, expected "
            f"{entry['expected_positive_token_id']}, observed {positive_id}"
        )
    if negative_id != int(entry["expected_negative_token_id"]):
        raise R4VerbalizerIdentityDrift(
            f"{model_key}: negative verbalizer drift, expected "
            f"{entry['expected_negative_token_id']}, observed {negative_id}"
        )
    if positive_id == negative_id:
        raise R4VerbalizerIdentityDrift(f"{model_key}: yes/no verbalizers are not distinct")
    if not ovr_evaluation.metadata.get("rendered_input"):
        raise R4MeasurementInterfaceDrift(
            f"{model_key}: the production path did not expose a rendered OVR input"
        )
    return {
        "model_key": model_key,
        "cat_labels": labels,
        "cat_token_ids": resolved,
        "positive_token_id": positive_id,
        "negative_token_id": negative_id,
        "synthetic_cat_forwards": 1,
        "synthetic_ovr_forwards": 1,
    }


# --------------------------------------------------------------------------- #
# Measurement
# --------------------------------------------------------------------------- #


def _unavailable_block(*, protocol: str, item_id: str, status: Any, reason: str) -> dict[str, Any]:
    return r4_raw_evidence.unavailable_block(
        status=status,
        reason=reason,
        source_record_id=measurements.failure_source_record_id(
            protocol=protocol,
            item_id=item_id,
            status=status,
            reason=reason,
        ),
    )


def measure_cat(
    *, runtime: Any, question: str, candidates: Sequence[tuple[str, str | None]],
    anchor: str, item_id: str, model_meta: Mapping[str, Any],
) -> dict[str, Any]:
    """Exactly one CAT forward; an independent failure never blocks the OVR call."""
    decision = measurements.build_cat_decision(question, None, candidates)
    try:
        evaluation = runtime.evaluate_with_trace(decision)
    except Exception as exc:  # classified below, else re-raised
        classified = measurements.classify_measurement_exception(exc)
        if classified is None:
            raise
        status, reason = classified
        return _unavailable_block(
            protocol=measurements.CAT_MEASUREMENT_ID,
            item_id=item_id,
            status=status,
            reason=reason,
        )
    record = measurements.build_cat_raw_record(
        evaluation, case_id=item_id, item_id=item_id, anchor=anchor, model_meta=model_meta
    )
    return r4_raw_evidence.scored_cat_block(
        record=record,
        source_record_id=fingerprint(record),
        top_token=_top_token(evaluation),
    )


def measure_ovr(
    *, runtime: Any, question: str, anchor: str, anchor_description: str, item_id: str,
    model_meta: Mapping[str, Any],
) -> dict[str, Any]:
    """Exactly one designated-candidate OVR forward (never the other three)."""
    proposition = measurements.build_ovr_proposition(question, None, anchor, anchor_description)
    try:
        evaluation = runtime.evaluate_with_trace(proposition)
    except Exception as exc:  # classified below, else re-raised
        classified = measurements.classify_measurement_exception(exc)
        if classified is None:
            raise
        status, reason = classified
        return _unavailable_block(
            protocol=measurements.OVR_MEASUREMENT_ID,
            item_id=item_id,
            status=status,
            reason=reason,
        )
    record = measurements.build_ovr_raw_record(
        case_id=item_id,
        item_id=item_id,
        anchor=anchor,
        candidate_order=[anchor],
        evaluations={anchor: evaluation},
        model_meta=model_meta,
    )
    return r4_raw_evidence.scored_ovr_block(
        record=record,
        source_record_id=fingerprint(record),
        top_token=_top_token(evaluation),
    )


def measure_item(
    *, runtime: Any, row: Mapping[str, Any], model_meta: Mapping[str, Any],
    population_id: str, population_manifest_fingerprint: str,
) -> dict[str, Any]:
    """One item = one CAT forward + one designated-only OVR forward (2 total)."""
    names = [str(name) for name in row["candidate_names"]]
    descriptions = [str(description) for description in row["candidate_descriptions"]]
    candidates = list(zip(names, descriptions, strict=True))
    anchor = names[int(row["anchor_index"])]
    ground_truth = names[int(row["ground_truth_index"])]
    item_id = str(row["item_id"])
    question = str(row["question"])
    cat_block = measure_cat(
        runtime=runtime,
        question=question,
        candidates=candidates,
        anchor=anchor,
        item_id=item_id,
        model_meta=model_meta,
    )
    ovr_block = measure_ovr(
        runtime=runtime,
        question=question,
        anchor=anchor,
        anchor_description=descriptions[int(row["anchor_index"])],
        item_id=item_id,
        model_meta=model_meta,
    )
    return r4_raw_evidence.build_item_evidence(
        manifest_item=row,
        population_id=population_id,
        population_manifest_fingerprint=population_manifest_fingerprint,
        split=str(row["split"]),
        anchor=anchor,
        ground_truth_value=ground_truth,
        cat=cat_block,
        ovr=ovr_block,
    )


def run_cell(
    *, model_key: str, population_key: str, device: str, authority: Mapping[str, Any],
    verify_environment_contract: bool = True,
) -> dict[str, Any]:
    """Measure one frozen cell and return its validated raw-evidence payload."""
    cell = resolve_cell(model_key, population_key)
    entry = cell["model"]
    model_meta = {
        "model": entry["model_id"],
        "revision": entry["revision"],
        "dtype": DTYPE,
        "rendering_config": dict(CHAT_TEMPLATE_KWARGS),
    }
    cache = verify_model_cache(model_key)
    environment = verify_environment(device=device) if verify_environment_contract else None
    offline = verify_offline_environment()
    backend = load_backend(model_key, device=device)
    started = time.time()
    try:
        verbalizers = verify_verbalizers(backend, model_key)
        runtime = Probvenance(backend=backend, capture_rendered_input=True)
        items = [
            measure_item(
                runtime=runtime,
                row=row,
                model_meta=model_meta,
                population_id=cell["population_id"],
                population_manifest_fingerprint=cell["population_manifest_fingerprint"],
            )
            for row in cell["required_rows"]
        ]
    finally:
        unload_backend(backend)
    elapsed = time.time() - started
    # Wall-clock timing is operational, not scientific evidence: it is reported
    # on stderr and deliberately excluded from the fingerprinted artifact so the
    # raw-evidence bytes stay reproducible (task section 46).
    print(
        f"[r4] measured {model_key}/{population_key} in {elapsed:.3f}s",
        file=sys.stderr,
    )
    runtime_provenance = {
        "device": device,
        "dtype": DTYPE,
        "chat_template_kwargs": dict(CHAT_TEMPLATE_KWARGS),
        "batch_size": 1,
        "environment": environment,
        "offline": offline,
        "cache": cache,
        "verbalizers": verbalizers,
    }
    payload = r4_raw_evidence.build_evidence_payload(
        model_key=model_key,
        model_id=entry["model_id"],
        model_revision=entry["revision"],
        model_role=entry["role"],
        adapter=entry["adapter"],
        population_id=cell["population_id"],
        population_manifest_fingerprint=cell["population_manifest_fingerprint"],
        dataset_id=cell["dataset_id"],
        dataset_revision=cell["dataset_revision"],
        train_budget=cell["train_budget"],
        planned_train_rows=len(cell["train_rows"]),
        planned_test_rows=len(cell["test_rows"]),
        measurement_contract_fingerprint=str(authority["measurement_contract_fingerprint"]),
        final_protocol_candidate_fingerprint=str(
            authority["final_protocol_candidate_fingerprint"]
        ),
        execution_manifest_candidate_fingerprint=str(
            authority["execution_manifest_candidate_fingerprint"]
        ),
        measurement_code_commit=measurement_code_commit(),
        runtime=runtime_provenance,
        items=items,
    )
    r4_raw_evidence.validate_raw_evidence(
        payload,
        required_items=cell["required_rows"],
        expected_contract_fingerprint=str(authority["measurement_contract_fingerprint"]),
        expected_model_key=model_key,
        expected_population_id=cell["population_id"],
    )
    return payload


def _cell_model_meta(cell: Mapping[str, Any]) -> dict[str, Any]:
    entry = cell["model"]
    return {
        "model": entry["model_id"],
        "revision": entry["revision"],
        "dtype": DTYPE,
        "rendering_config": dict(CHAT_TEMPLATE_KWARGS),
    }


def _build_cell_payload(
    *,
    cell: Mapping[str, Any],
    authority: Mapping[str, Any],
    runtime_provenance: Mapping[str, Any],
    items: Sequence[Mapping[str, Any]],
    measurement_code: str,
) -> dict[str, Any]:
    entry = cell["model"]
    return r4_raw_evidence.build_evidence_payload(
        model_key=str(cell["model_key"]),
        model_id=entry["model_id"],
        model_revision=entry["revision"],
        model_role=entry["role"],
        adapter=entry["adapter"],
        population_id=cell["population_id"],
        population_manifest_fingerprint=cell["population_manifest_fingerprint"],
        dataset_id=cell["dataset_id"],
        dataset_revision=cell["dataset_revision"],
        train_budget=cell["train_budget"],
        planned_train_rows=len(cell["train_rows"]),
        planned_test_rows=len(cell["test_rows"]),
        measurement_contract_fingerprint=str(authority["measurement_contract_fingerprint"]),
        final_protocol_candidate_fingerprint=str(
            authority["final_protocol_candidate_fingerprint"]
        ),
        execution_manifest_candidate_fingerprint=str(
            authority["execution_manifest_candidate_fingerprint"]
        ),
        measurement_code_commit=measurement_code,
        runtime=runtime_provenance,
        items=items,
    )


_REQUIRED_ROW_KEYS = (
    "item_id",
    "population_id",
    "population_manifest_fingerprint",
    "split",
    "anchor",
    "ground_truth_value",
    "fixed_event",
    "cat",
    "ovr",
)


def _validate_row_shape(item: Mapping[str, Any]) -> Mapping[str, Any]:
    """A row becomes COMMITTED only once its schema is structurally complete."""
    missing = [key for key in _REQUIRED_ROW_KEYS if key not in item]
    if missing:
        raise r4_staging.R4StagingError(f"measured row is missing required keys {missing}")
    for block in ("cat", "ovr"):
        if "status" not in item[block]:
            raise r4_staging.R4StagingError(f"measured row {block!r} block has no status")
    return item


def cell_identity_header(
    *,
    cell: Mapping[str, Any],
    authority: Mapping[str, Any],
    measurement_code: str,
) -> dict[str, Any]:
    """The immutable per-cell identity every resume must match exactly."""
    entry = cell["model"]
    ordered = [str(row["item_id"]) for row in cell["required_rows"]]
    return {
        "resume_policy_id": r4_staging.RESUME_POLICY_ID,
        "resume_policy_version": r4_staging.RESUME_POLICY_VERSION,
        "final_protocol_fingerprint": str(authority["final_protocol_fingerprint"]),
        "execution_manifest_fingerprint": str(authority["execution_manifest_fingerprint"]),
        "measurement_contract_fingerprint": str(authority["measurement_contract_fingerprint"]),
        "measurement_code_commit": str(measurement_code),
        "model_key": str(cell["model_key"]),
        "model_id": str(entry["model_id"]),
        "model_revision": str(entry["revision"]),
        "model_role": str(entry["role"]),
        "adapter": str(entry["adapter"]),
        "population_key": str(cell["population_key"]),
        "population_id": str(cell["population_id"]),
        "population_manifest_fingerprint": str(cell["population_manifest_fingerprint"]),
        "dataset_id": str(cell["dataset_id"]),
        "dataset_revision": str(cell["dataset_revision"]),
        "required_train_budget": str(cell["train_budget"]),
        "required_test_identity": "frozen population manifest TEST rows (all eligible)",
        "expected_item_count": len(ordered),
        "expected_item_ids": ordered,
    }


def _verify_existing_final(
    final: Mapping[str, Any], identity: Mapping[str, Any], directory: str | Path
) -> None:
    """Fail closed when a published final artifact does not match the frozen cell."""
    if str(final.get("evidence_fingerprint")) != str(
        r4_raw_evidence.evidence_fingerprint(final)
    ):
        raise r4_staging.R4ExistingFinalArtifactConflict(
            f"existing final artifact fingerprint does not recompute: {directory}"
        )
    checks = (
        ("model", "model_revision", "model_revision"),
        ("population", "population_id", "population_id"),
        ("population", "population_manifest_fingerprint", "population_manifest_fingerprint"),
    )
    for section, key, identity_key in checks:
        if str(final.get(section, {}).get(key)) != str(identity[identity_key]):
            raise r4_staging.R4ExistingFinalArtifactConflict(
                f"existing final artifact {section}.{key} does not match identity: {directory}"
            )
    if str(final.get("measurement_contract_fingerprint")) != str(
        identity["measurement_contract_fingerprint"]
    ):
        raise r4_staging.R4ExistingFinalArtifactConflict(
            f"existing final artifact measurement contract mismatch: {directory}"
        )
    if len(final.get("items", [])) != int(identity["expected_item_count"]):
        raise r4_staging.R4ExistingFinalArtifactConflict(
            f"existing final artifact item count mismatch: {directory}"
        )


def run_cell_resumable(
    *,
    model_key: str,
    population_key: str,
    device: str,
    authority: Mapping[str, Any],
    staging_root: str | Path = DEFAULT_STAGING_ROOT,
    resume: bool = True,
    verify_environment_contract: bool = True,
) -> dict[str, Any]:
    """Measure (or crash-safely resume) one frozen cell under durable staging.

    Crash-safe, deterministic and outcome-blind: the pending set is derived only
    from transaction state (committed / inflight), never from any score.
    """
    cell = resolve_cell(model_key, population_key)
    directory = r4_staging.ensure_cell_dir(staging_root, model_key, cell["population_id"])
    lock = r4_staging.acquire_cell_lock(directory)
    try:
        measurement_code = measurement_code_commit()
        identity = cell_identity_header(
            cell=cell, authority=authority, measurement_code=measurement_code
        )
        r4_staging.verify_or_write_identity(directory, identity)

        existing_final = r4_staging.load_final(directory)
        if existing_final is not None:
            _verify_existing_final(existing_final, identity, directory)
            return {
                "status": "ALREADY_COMPLETE",
                "model_key": model_key,
                "population_id": cell["population_id"],
                "staging_dir": str(directory),
                "evidence_fingerprint": str(existing_final["evidence_fingerprint"]),
                "committed_rows": len(identity["expected_item_ids"]),
                "new_forwards": 0,
            }

        committed = r4_staging.committed_item_ids(directory)
        expected = set(identity["expected_item_ids"])
        unknown = committed - expected
        if unknown:
            raise r4_staging.R4ResumeIdentityMismatch(
                f"staging holds rows outside the frozen item set: {sorted(unknown)[:3]}"
            )
        if committed and not resume:
            raise r4_staging.R4StagingError(
                f"staging already holds committed rows; pass --resume: {directory}"
            )

        inflight = r4_staging.load_inflight_item_ids(directory)
        plan = r4_staging.compute_pending(
            ordered_item_ids=identity["expected_item_ids"],
            committed_ids=committed,
            inflight_ids=inflight,
        )
        operations = r4_staging.load_operations(directory)
        operations["planned_logical_forwards"] = 2 * len(identity["expected_item_ids"])
        operations["recovery_replay_count"] += len(plan["recovery_replay"])
        r4_staging.save_operations(directory, operations)

        runtime_provenance = r4_staging.load_runtime(directory)
        if plan["pending"]:
            cache = verify_model_cache(model_key)
            environment = (
                verify_environment(device=device) if verify_environment_contract else None
            )
            offline = verify_offline_environment()
            backend = load_backend(model_key, device=device)
            try:
                verbalizers = verify_verbalizers(backend, model_key)
                observed_runtime = {
                    "device": device,
                    "dtype": DTYPE,
                    "chat_template_kwargs": dict(CHAT_TEMPLATE_KWARGS),
                    "batch_size": 1,
                    "environment": environment,
                    "offline": offline,
                    "cache": cache,
                    "verbalizers": verbalizers,
                }
                if runtime_provenance is None:
                    runtime_provenance = r4_staging.verify_or_write_runtime(
                        directory, observed_runtime
                    )
                elif runtime_provenance != observed_runtime:
                    raise r4_staging.R4ResumeIdentityMismatch(
                        f"observed runtime does not match the staged runtime: {directory}"
                    )
                rows_by_id = {str(row["item_id"]): row for row in cell["required_rows"]}
                runtime = Probvenance(backend=backend, capture_rendered_input=True)
                for item_id in plan["pending"]:
                    # Mark inflight before measuring: if the process dies mid-row the
                    # marker makes the whole row a RECOVERY_REPLAY on resume.
                    r4_staging.mark_inflight(directory, item_id)
                    try:
                        item = measure_item(
                            runtime=runtime,
                            row=rows_by_id[item_id],
                            model_meta=_cell_model_meta(cell),
                            population_id=cell["population_id"],
                            population_manifest_fingerprint=cell[
                                "population_manifest_fingerprint"
                            ],
                        )
                        _validate_row_shape(item)
                        r4_staging.commit_row(directory, item)
                    finally:
                        r4_staging.clear_inflight(directory, item_id)
                    operations["operational_attempts"] += 2
            finally:
                unload_backend(backend)
            r4_staging.save_operations(directory, operations)
        if runtime_provenance is None:  # pragma: no cover - defensive
            raise r4_staging.R4StagingError(
                f"no runtime provenance available for {directory}"
            )

        rows_by_id = {
            str(row["item_id"]): row for row in r4_staging.load_committed_rows(directory)
        }
        items = [rows_by_id[item_id] for item_id in identity["expected_item_ids"]]
        payload = _build_cell_payload(
            cell=cell,
            authority=authority,
            runtime_provenance=runtime_provenance,
            items=items,
            measurement_code=measurement_code,
        )
        r4_raw_evidence.validate_raw_evidence(
            payload,
            required_items=cell["required_rows"],
            expected_contract_fingerprint=str(authority["measurement_contract_fingerprint"]),
            expected_model_key=model_key,
            expected_population_id=cell["population_id"],
        )
        r4_staging.publish_final(directory, payload)
        operations["finalizations"] += 1
        r4_staging.save_operations(directory, operations)
        return {
            "status": "COMPLETE",
            "model_key": model_key,
            "population_id": cell["population_id"],
            "staging_dir": str(directory),
            "evidence_fingerprint": str(payload["evidence_fingerprint"]),
            "committed_rows": len(items),
            "new_forwards": 2 * len(plan["pending"]),
            "recovery_replay": list(plan["recovery_replay"]),
        }
    finally:
        r4_staging.release_cell_lock(lock)


def synthetic_preflight(*, model_keys: Sequence[str], device: str) -> list[dict[str, Any]]:
    """Synthetic-only real-model check: 1 CAT + 1 OVR forward per frozen model.

    Each model is attempted independently: a model whose pinned snapshot is absent
    is recorded as BLOCKED (``MODEL_CACHE_MISSING``) instead of aborting the run,
    so the caller can see the whole panel state in one pass.
    """
    _assert_synthetic_only()
    results: list[dict[str, Any]] = []
    for model_key in model_keys:
        entry = _require_model(model_key)
        record: dict[str, Any] = {
            "model_key": model_key,
            "model_id": entry["model_id"],
            "model_revision": entry["revision"],
            "adapter": entry["adapter"],
        }
        try:
            cache = verify_model_cache(model_key)
            backend = load_backend(model_key, device=device)
            try:
                verification = verify_verbalizers(backend, model_key)
                model = getattr(backend, "_model", None)
                tokenizer = getattr(backend, "_tokenizer", None)
                config = getattr(model, "config", None)
                record.update(
                    {
                        "resolved_snapshot": cache["snapshot_path"],
                        "model_class": type(model).__name__,
                        "tokenizer_class": type(tokenizer).__name__,
                        "model_type": getattr(config, "model_type", None),
                        "dtype": str(getattr(model, "dtype", None)),
                        "load_report": getattr(backend, "load_report", None),
                        "cat_labels": verification["cat_labels"],
                        "cat_token_ids": verification["cat_token_ids"],
                        "positive_token_id": verification["positive_token_id"],
                        "negative_token_id": verification["negative_token_id"],
                        "synthetic_forwards": 2,
                        "status": "PASS",
                    }
                )
            finally:
                unload_backend(backend)
        except Exception as exc:
            record.update(
                {
                    "resolved_snapshot": None,
                    "synthetic_forwards": 0,
                    "status": "BLOCKED",
                    "blocker": type(exc).__name__,
                    "detail": str(exc),
                }
            )
        results.append(record)
    return results


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-role", choices=tuple(MODEL_REGISTRY), default=None)
    parser.add_argument("--population", choices=tuple(POPULATION_REGISTRY), default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument(
        "--staging-root",
        default=None,
        help=(
            "crash-safe staging root for the formal run (enables durable per-row "
            "commits and resume); selects the resumable execution path"
        ),
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="resume an existing staged cell instead of refusing to inherit partial state",
    )
    parser.add_argument("--device", default=DEVICE_DEFAULT)
    parser.add_argument(
        "--synthetic-preflight",
        action="store_true",
        help="run the synthetic-only 1 CAT + 1 OVR check for the frozen six-model panel",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.synthetic_preflight:
        verify_environment(device=args.device)
        verify_offline_environment()
        report = synthetic_preflight(model_keys=ALL_MODEL_KEYS, device=args.device)
        print(json.dumps({"synthetic_preflight": report}, ensure_ascii=False, indent=2))
        return 0
    if not args.model_role or not args.population or not (args.output or args.staging_root):
        raise SystemExit(
            "formal measurement requires --model-role, --population and either "
            "--staging-root (crash-safe formal path) or --output (single-shot path) "
            "(or use --synthetic-preflight)"
        )
    verify_git_state(require_clean=True)
    authority = load_frozen_authority()
    if authority["measurement_contract_status"] != "FROZEN":
        raise R4MeasurementError("the measurement execution contract is not frozen")
    if (
        authority["final_protocol_status"] != "FROZEN"
        or authority["execution_manifest_status"] != "FROZEN"
    ):
        raise R4MeasurementError(
            "the final protocol / execution manifest freeze is not FROZEN"
        )
    if args.staging_root:
        summary = run_cell_resumable(
            model_key=args.model_role,
            population_key=args.population,
            device=args.device,
            authority=authority,
            staging_root=args.staging_root,
            resume=args.resume,
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    payload = run_cell(
        model_key=args.model_role,
        population_key=args.population,
        device=args.device,
        authority=authority,
    )
    r4_raw_evidence.write_json(args.output, payload)
    print(
        json.dumps(
            {
                "model_key": args.model_role,
                "population": args.population,
                "output": args.output,
                "planned_rows": payload["planned"]["rows"],
                "total_forwards": payload["planned"]["total_forwards"],
                "paired_complete": payload["paired_complete"],
                "evidence_fingerprint": payload["evidence_fingerprint"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - entry point
    raise SystemExit(main())
