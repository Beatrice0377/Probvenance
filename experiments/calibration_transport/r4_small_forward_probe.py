"""R4 single-candidate real-forward engineering probe (Phase 2A Olmo / Phase 2B Falcon /
Phase 2C granite / Phase 2D Qwen3.5-9B).

Scope (engineering compatibility facts ONLY; no scientific outcome):

  * exact-revision snapshot provenance of the selected candidate
  * offline, local_files_only, BF16, cuda:0, trust_remote_code=False load
  * the REAL production path:
        measurements.build_cat_decision -> ChoiceCompiler
        measurements.build_ovr_proposition -> BoolCompiler
        -> TransformersBackend.execute -> logits[:, -1, :]
  * CAT (A/B/C/D) and OVR (yes/no) target logits on synthetic fixtures only
  * determinism (repeated forwards), memory, latency, load time, cleanup

Hard prohibitions enforced here:
  * NO generation / sampling / decoding of model output
  * NO study datasets (synthetic fixtures only)
  * NO accuracy / Brier / LogLoss / calibration / transport / winner agreement
  * trust_remote_code is hard-pinned False
  * the exact revision is hard-pinned and asserted

Run (candidate defaults to "olmo"; pass "falcon", "granite" or "qwen", or set PROBE_CANDIDATE):
    HF_HOME=/root/rivermind-data/hf-cache \
    HUGGINGFACE_HUB_CACHE=/root/rivermind-data/hf-cache/hub \
    HF_HUB_OFFLINE=1 \
    python experiments/calibration_transport/r4_small_forward_probe.py falcon
"""

from __future__ import annotations

import gc
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
CAL_DIR = REPO_ROOT / "experiments" / "calibration_transport"
sys.path.insert(0, str(CAL_DIR))
# Existing R3 Qwen3.5 text-tower adapter (checkpoint adaptation only; no scoring logic).
sys.path.insert(0, str(REPO_ROOT / "experiments" / "semantic_signal"))

# Offline by default: the probe must reproduce from the existing snapshot alone.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HOME", "/root/rivermind-data/hf-cache")
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", "/root/rivermind-data/hf-cache/hub")
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import measurements  # noqa: E402  (loaded from experiments/calibration_transport via sys.path)

# Candidate configs. Each revision is hard-pinned; each expected token id sets comes
# from the frozen R4 exact-tokenizer gate evidence.
CANDIDATES: dict[str, dict[str, Any]] = {
    "olmo": {
        "repo_id": "allenai/Olmo-3-7B-Instruct",
        "revision": "6e5971d9eba42665f5bd5a0fcf047f299ce1dccc",
        "expected_cat_ids": {"A": 32, "B": 33, "C": 34, "D": 35},
        "expected_yes_id": 9891,
        "expected_no_id": 2201,
        "phase": "2A-olmo",
        "out_json": "/root/rivermind-data/r4-forward-probe-runs/olmo_forward_probe_results.json",
    },
    "falcon": {
        "repo_id": "tiiuae/Falcon-H1-7B-Instruct",
        "revision": "41e72f27effbab80cd45b6e884688452253a3686",
        "expected_cat_ids": {"A": 1068, "B": 1069, "C": 1070, "D": 1071},
        "expected_yes_id": 5763,
        "expected_no_id": 3257,
        "phase": "2B-falcon",
        "out_json": "/root/rivermind-data/r4-forward-probe-runs/falcon_forward_probe_results.json",
    },
    "granite": {
        "repo_id": "ibm-granite/granite-4.0-h-tiny",
        "revision": "791e0d3d28c86e106c9b6e0b4cecdee0375b6124",
        "expected_cat_ids": {"A": 32, "B": 33, "C": 34, "D": 35},
        "expected_yes_id": 9891,
        "expected_no_id": 2201,
        "phase": "2C-granite",
        "out_json": "/root/rivermind-data/r4-forward-probe-runs/granite_forward_probe_results.json",
    },
    "qwen": {
        "repo_id": "Qwen/Qwen3.5-9B",
        "revision": "c202236235762e1c871ad0ccb60c8ee5ba337b9a",
        "expected_cat_ids": {"A": 32, "B": 33, "C": 34, "D": 35},
        "expected_yes_id": 9405,
        "expected_no_id": 2083,
        "phase": "2D-qwen35-9b",
        "adapter": "qwen35_text",
        "out_json": (
            "/root/rivermind-data/r4-forward-probe-runs/qwen35_9b_forward_probe_results.json"
        ),
    },
}

_selected = sys.argv[1].strip().lower() if len(sys.argv) > 1 else os.environ.get(
    "PROBE_CANDIDATE", "olmo"
).strip().lower()
if _selected not in CANDIDATES:
    raise SystemExit(f"unknown candidate {_selected!r}; choose from {sorted(CANDIDATES)}")
CFG = CANDIDATES[_selected]

REPO_ID = CFG["repo_id"]
REVISION = CFG["revision"]
DEVICE = "cuda:0"
DTYPE = "bfloat16"
CHAT_TEMPLATE_KWARGS = {"enable_thinking": False}

# Frozen tokenizer-gate reference ids (R4_EXACT_TOKENIZER_GATE.md §8/§9).
EXPECTED_CAT_IDS = CFG["expected_cat_ids"]
EXPECTED_YES_ID = CFG["expected_yes_id"]
EXPECTED_NO_ID = CFG["expected_no_id"]

OUT_PATH = Path(CFG["out_json"])

# --- synthetic fixtures only (no study dataset) -----------------------------
_FORBIDDEN_DATASET_MARKERS = (
    "mmlu", "hellaswag", "medmcqa", "commonsenseqa", "arc_", "openbookqa",
)

SYNTH_QUESTION = (
    "Synthetic probe one. Which option is explicitly named as the target symbol?"
)
SYNTH_CONTEXT = "Synthetic context block. Engineering compatibility probe only."
SYNTH_CANDIDATES: list[tuple[str, str | None]] = [
    ("Alpha", None),
    ("Beta", None),
    ("Gamma", None),
    ("Delta", None),
]


def assert_synthetic_only() -> None:
    blob = (SYNTH_QUESTION + " " + SYNTH_CONTEXT).lower()
    for marker in _FORBIDDEN_DATASET_MARKERS:
        if marker in blob:
            raise SystemExit(f"REFUSING TO RUN: study-dataset marker {marker!r} in fixture")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def all_finite(values: Any) -> bool:
    import math

    return all(math.isfinite(float(v)) for v in values)


def nvidia_smi_used_mib() -> int | None:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=30, check=True,
        )
        return int(out.stdout.strip().splitlines()[0])
    except Exception:
        return None


def cuda_mem() -> dict[str, Any]:
    import torch

    if not torch.cuda.is_available():
        return {}
    return {
        "allocated_bytes": int(torch.cuda.memory_allocated()),
        "reserved_bytes": int(torch.cuda.memory_reserved()),
        "peak_allocated_bytes": int(torch.cuda.max_memory_allocated()),
        "peak_reserved_bytes": int(torch.cuda.max_memory_reserved()),
        "nvidia_smi_used_mib": nvidia_smi_used_mib(),
    }


def snapshot_provenance() -> dict[str, Any]:
    base = Path(os.environ["HUGGINGFACE_HUB_CACHE"]) / f"models--{REPO_ID.replace('/', '--')}"
    snaps = base / "snapshots"
    snapdirs = sorted(p for p in snaps.iterdir() if p.is_dir()) if snaps.is_dir() else []
    info: dict[str, Any] = {
        "repo_id": REPO_ID,
        "requested_revision": REVISION,
        "cache_model_dir": str(base),
        "snapshot_dirs": [p.name for p in snapdirs],
        "endpoint": os.environ.get("HF_ENDPOINT"),
        "hub_cache": os.environ.get("HUGGINGFACE_HUB_CACHE"),
    }
    if snapdirs:
        snap = snapdirs[0]
        info["snapshot_path"] = str(snap)
        info["resolved_revision"] = snap.name
        info["basename_matches_requested"] = snap.name == REVISION
        files = sorted(p.name for p in snap.iterdir())
        info["files"] = files
        info["weight_shards"] = [f for f in files if f.endswith(".safetensors")]
        info["shard_count"] = len(info["weight_shards"])
        info["has_incomplete"] = any(f.endswith(".incomplete") for f in files)
        info["has_config"] = "config.json" in files
        info["has_tokenizer_config"] = "tokenizer_config.json" in files
        total = sum(p.stat().st_size for p in snap.rglob("*") if p.is_file())
        info["snapshot_size_bytes"] = total
        info["snapshot_size_gib"] = round(total / (1024**3), 2)
    return info


def main() -> int:
    import torch

    assert_synthetic_only()

    result: dict[str, Any] = {
        "probe": "r4_small_forward_probe",
        "candidate": _selected,
        "phase": CFG["phase"],
        "generation_used": False,
        "study_dataset_used": False,
    }

    result["snapshot"] = snapshot_provenance()
    result["env"] = {
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "transformers": __import__("transformers").__version__,
        "huggingface_hub": __import__("huggingface_hub").__version__,
        "cuda_available": torch.cuda.is_available(),
        "device_count": torch.cuda.device_count(),
        "bf16_supported": torch.cuda.is_bf16_supported(),
        "device_name": torch.cuda.get_device_name(0),
    }
    result["pre_load_memory"] = cuda_mem()

    # --- load through the REAL production backend ---------------------------
    from probvenance.backends.transformers import TransformersBackend

    torch.cuda.reset_peak_memory_stats()
    t0 = time.perf_counter()
    if CFG.get("adapter") == "qwen35_text":
        # Qwen3.5-9B ships as a multimodal composite checkpoint
        # (Qwen3_5ForConditionalGeneration). The existing R3 Qwen35TextBackend
        # rebuilds the text-only Qwen3_5ForCausalLM from text_config and rewrites
        # the text-tower key prefix; only checkpoint loading differs. Rendering,
        # verbalizer resolution, scoring and diagnostics stay TransformersBackend.
        from qwen35_loader import Qwen35TextBackend

        backend = Qwen35TextBackend(
            REPO_ID,
            revision=REVISION,
            device=DEVICE,
            dtype=DTYPE,
            trust_remote_code=False,
            local_files_only=True,
            chat_template_kwargs=CHAT_TEMPLATE_KWARGS,
        )
    else:
        backend = TransformersBackend(
            REPO_ID,
            revision=REVISION,
            device=DEVICE,
            dtype=DTYPE,
            trust_remote_code=False,
            local_files_only=True,
            chat_template_kwargs=CHAT_TEMPLATE_KWARGS,
        )
    load_seconds = time.perf_counter() - t0
    model = backend._model
    tokenizer = backend._tokenizer
    param = next(model.parameters())

    result["model_identity"] = {
        "model_class": type(model).__name__,
        "config_class": type(model.config).__name__,
        "model_type": getattr(model.config, "model_type", None),
        "config_commit_hash": getattr(model.config, "_commit_hash", None),
        "dtype": str(getattr(model, "dtype", None)),
        "param_dtype_sample": str(param.dtype),
        "device": str(param.device),
        "trust_remote_code": False,
        "local_files_only": True,
        "offline": os.environ.get("HF_HUB_OFFLINE"),
        "load_seconds": round(load_seconds, 3),
        "tokenizer_class": type(tokenizer).__name__,
        "tokenizer_has_chat_template": bool(getattr(tokenizer, "chat_template", None)),
    }
    # --- checkpoint-adapter report (populated only when an adapter is used) ---
    result["checkpoint_adapter"] = {
        "adapter": CFG.get("adapter", "transformers"),
        "backend_class": type(backend).__name__,
        "load_report": getattr(backend, "load_report", None),
    }
    if CFG.get("adapter") == "qwen35_text":
        from transformers import AutoConfig

        composite = AutoConfig.from_pretrained(
            REPO_ID, revision=REVISION, trust_remote_code=False, local_files_only=True
        )
        text_cfg = getattr(composite, "text_config", None)
        result["checkpoint_adapter"].update({
            "composite_config_class": type(composite).__name__,
            "composite_architectures": list(getattr(composite, "architectures", []) or []),
            "composite_model_type": getattr(composite, "model_type", None),
            "text_config_class": type(text_cfg).__name__ if text_cfg is not None else None,
            "text_model_type": (
                getattr(text_cfg, "model_type", None) if text_cfg is not None else None
            ),
            "text_tower_prefix": "model.language_model.",
            "non_text_prefixes": ["model.visual.", "mtp."],
        })
    result["post_load_memory"] = cuda_mem()

    caps = backend.capabilities

    # --- CAT production path -------------------------------------------------
    from probvenance.compiler import BoolCompiler, ChoiceCompiler

    cat_decision = measurements.build_cat_decision(SYNTH_QUESTION, SYNTH_CONTEXT, SYNTH_CANDIDATES)
    cat_plan = ChoiceCompiler().compile(cat_decision, caps)
    cat_ev = backend.execute(cat_plan)
    cat_ids = dict(cat_ev.metadata["resolved_target_token_ids"])
    cat_record = {
        "strategy": str(cat_plan.strategy),
        "labels": list(cat_ev.labels),
        "resolved_target_token_ids": cat_ev.metadata["resolved_target_token_ids"],
        "input_token_count": cat_ev.metadata["input_token_count"],
        "scoring_position": "logits[:, -1, :] (last input position)",
        "rendered_input_sha256": sha256_text(cat_ev.metadata["rendered_input"]),
        "rendered_input": cat_ev.metadata["rendered_input"],
        "rendered_input_tail": cat_ev.metadata["rendered_input"][-200:],
        "chat_template_kwargs": dict(CHAT_TEMPLATE_KWARGS),
        "values_order": list(cat_ev.labels),
        "logits": {lab: float(v) for lab, v in zip(cat_ev.labels, cat_ev.values, strict=True)},
        "all_finite": all_finite(cat_ev.values),
        "ids_match_frozen_gate": all(cat_ids.get(k) == v for k, v in EXPECTED_CAT_IDS.items()),
        "resolved_dtype": cat_ev.metadata.get("dtype"),
        "model_revision_reported": cat_ev.metadata.get("model_revision"),
    }
    result["cat"] = cat_record

    # --- OVR production path (4 synthetic propositions) ----------------------
    ovr_records = []
    ovr_plan_for_determinism = None
    for name, desc in SYNTH_CANDIDATES:
        decision = measurements.build_ovr_proposition(SYNTH_QUESTION, SYNTH_CONTEXT, name, desc)
        plan = BoolCompiler().compile(decision, caps)
        ev = backend.execute(plan)
        if ovr_plan_for_determinism is None:
            ovr_plan_for_determinism = plan
        ovr_records.append({
            "candidate": name,
            "labels": list(ev.labels),
            "positive_verbalizer": ev.metadata["positive_verbalizer"],
            "negative_verbalizer": ev.metadata["negative_verbalizer"],
            "yes_token_id": ev.metadata["positive_token_id"],
            "no_token_id": ev.metadata["negative_token_id"],
            "input_token_count": ev.metadata["input_token_count"],
            "rendered_input_sha256": sha256_text(ev.metadata["rendered_input"]),
            "logit_no_false": float(ev.values[0]),
            "logit_yes_true": float(ev.values[1]),
            "all_finite": all_finite(ev.values),
        })
    result["ovr"] = {
        "propositions": ovr_records,
        "yes_id_matches_frozen_gate": all(
            r["yes_token_id"] == EXPECTED_YES_ID for r in ovr_records
        ),
        "no_id_matches_frozen_gate": all(
            r["no_token_id"] == EXPECTED_NO_ID for r in ovr_records
        ),
    }

    # --- memory at forward peak ---------------------------------------------
    torch.cuda.reset_peak_memory_stats()
    backend.execute(cat_plan)
    result["forward_peak_memory_cat"] = cuda_mem()

    # --- latency -------------------------------------------------------------
    def timed(be: Any, plan: Any, runs: int) -> list[float]:
        for _ in range(2):  # warmup
            be.execute(plan)
        torch.cuda.synchronize()
        out = []
        for _ in range(runs):
            torch.cuda.synchronize()
            t = time.perf_counter()
            be.execute(plan)
            torch.cuda.synchronize()
            out.append(round((time.perf_counter() - t) * 1000.0, 2))
        return out

    cat_lat = timed(backend, cat_plan, 5)
    ovr_lat = timed(backend, ovr_plan_for_determinism, 5)
    result["latency_ms"] = {
        "note": "ENGINEERING INFORMATION ONLY",
        "cat_runs": cat_lat,
        "cat_median": sorted(cat_lat)[len(cat_lat) // 2],
        "ovr_runs": ovr_lat,
        "ovr_median": sorted(ovr_lat)[len(ovr_lat) // 2],
    }

    # --- determinism (identical input, repeated forward) ---------------------
    def repeat_values(be: Any, plan: Any, n: int) -> list[list[float]]:
        runs = []
        for _ in range(n):
            ev = be.execute(plan)
            runs.append([float(v) for v in ev.values])
        return runs

    cat_runs = repeat_values(backend, cat_plan, 3)
    ovr_runs = repeat_values(backend, ovr_plan_for_determinism, 3)

    def diff_report(runs: list[list[float]]) -> dict[str, Any]:
        exact = all(r == runs[0] for r in runs)
        max_abs = max(
            (abs(a - b) for r in runs for a, b in zip(r, runs[0], strict=True)), default=0.0
        )
        return {"runs": runs, "exact_equality": exact, "max_abs_diff": max_abs}

    result["determinism"] = {
        "cat": diff_report(cat_runs),
        "ovr_representative_candidate": ovr_records[0]["candidate"],
        "ovr": diff_report(ovr_runs),
    }

    # --- cleanup -------------------------------------------------------------
    del backend, model, tokenizer
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.synchronize()
    result["post_cleanup_memory"] = cuda_mem()

    result["scientific_guardrail_audit"] = {
        "generation_used": False,
        "accuracy_computed": False,
        "brier_computed": False,
        "logloss_computed": False,
        "calibration_computed": False,
        "calibration_transport_computed": False,
        "winner_agreement_computed": False,
        "study_dataset_used": False,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    print(f"\nWROTE {OUT_PATH}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
