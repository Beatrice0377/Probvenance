"""Synthetic-only single-model performance probe (PHASE G).

One model per process (the PHASE G contract is a fresh process per affected
model). The workload is the *same* invented 12-item synthetic battery used by
`fast_kernel_equivalence_probe.py`, so the reference and fast environments are
compared on identical text. Warmup items are fixed in advance (3) and are not
counted; measured items are fixed in advance (12).

No R4 study item, no ground truth, and no study probability is read or produced.
The only outputs are operational timing / memory numbers.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import resource
import statistics
import sys
import time
from pathlib import Path
from typing import Any

CAL_DIR = Path(__file__).resolve().parent

WARMUP_ITEMS = 3
MEASURED_ITEMS = 12
BATCH_SIZE = 1
LOGICAL_FORWARDS_PER_ITEM = 2  # 1 CAT + 1 designated-only OVR


def _load_sibling(name: str) -> Any:
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


probe = _load_sibling("fast_kernel_equivalence_probe")
runner = probe.runner


def _mem_available_kb() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1])
    raise RuntimeError("MemAvailable not found in /proc/meminfo")


def _peak_host_rss_kb() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def run_benchmark(model_key: str, *, device: str) -> dict[str, Any]:
    import torch

    from probvenance import Probvenance

    items = probe.build_battery()
    warmup = items[:WARMUP_ITEMS]
    measured = items[WARMUP_ITEMS : WARMUP_ITEMS + MEASURED_ITEMS]
    if len(measured) != MEASURED_ITEMS:
        raise ValueError("synthetic battery does not carry enough items for the measured count")

    meta = probe._model_meta(model_key)
    mem_before = _mem_available_kb()

    load_start = time.perf_counter()
    backend = runner.load_backend(model_key, device=device)
    model_load_seconds = time.perf_counter() - load_start
    try:
        runner.verify_verbalizers(backend, model_key)
        runtime = Probvenance(backend=backend, capture_rendered_input=True)

        # Warmup (not counted).
        for item in warmup:
            probe._capture_item(runtime, item, meta)

        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
        per_row_seconds: list[float] = []
        wall_start = time.perf_counter()
        for item in measured:
            row_start = time.perf_counter()
            probe._capture_item(runtime, item, meta)
            torch.cuda.synchronize()
            per_row_seconds.append(time.perf_counter() - row_start)
        elapsed = time.perf_counter() - wall_start

        peak_gpu_allocated = int(torch.cuda.max_memory_allocated())
        gpu_total = int(torch.cuda.get_device_properties(0).total_memory)
    finally:
        runner.unload_backend(backend)

    mem_after = _mem_available_kb()
    rows = len(measured)
    logical_forwards = rows * LOGICAL_FORWARDS_PER_ITEM
    return {
        "probe_id": "r4-fast-kernel-performance-probe",
        "probe_version": 1,
        "model_key": model_key,
        "model_id": meta["model"],
        "model_revision": meta["revision"],
        "python_prefix": sys.prefix,
        "python_executable": sys.executable,
        "torch": torch.__version__,
        "device": device,
        "dtype": runner.DTYPE,
        "batch_size": BATCH_SIZE,
        "eval_mode": True,
        "inference_mode": True,
        "battery_id": probe.BATTERY_ID,
        "battery_fingerprint": probe.battery_fingerprint(items),
        "warmup_items": WARMUP_ITEMS,
        "measured_items": rows,
        "measured_logical_forwards": logical_forwards,
        "model_load_seconds": model_load_seconds,
        "elapsed_seconds": elapsed,
        "rows_per_second": rows / elapsed if elapsed > 0 else None,
        "logical_forwards_per_second": logical_forwards / elapsed if elapsed > 0 else None,
        "median_seconds_per_row": statistics.median(per_row_seconds),
        "mean_seconds_per_row": statistics.fmean(per_row_seconds),
        "min_seconds_per_row": min(per_row_seconds),
        "max_seconds_per_row": max(per_row_seconds),
        "per_row_seconds": per_row_seconds,
        "peak_host_rss_kb": _peak_host_rss_kb(),
        "peak_gpu_allocated_bytes": peak_gpu_allocated,
        "gpu_total_bytes": gpu_total,
        "mem_available_before_kb": mem_before,
        "mem_available_after_kb": mem_after,
        "synthetic_only": True,
        "study_items_used": 0,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="R4 fast-kernel synthetic performance probe")
    parser.add_argument("--model-key", required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = run_benchmark(args.model_key, device=args.device)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(probe.dump_canonical(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "model_key": payload["model_key"],
                "python_prefix": payload["python_prefix"],
                "rows_per_second": payload["rows_per_second"],
                "median_seconds_per_row": payload["median_seconds_per_row"],
                "output": str(output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
