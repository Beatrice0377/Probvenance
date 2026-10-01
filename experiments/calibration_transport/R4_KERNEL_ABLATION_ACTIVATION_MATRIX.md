# R4 — Bounded Kernel Ablation: Activation Matrix (PHASE A)

```text
STATUS: COMPLETE
NATURE: OUTCOME-BLIND OPERATIONAL EVIDENCE
STUDY ROWS USED: 0
```

Companion machine-readable artifact:
`experiments/calibration_transport/R4_KERNEL_ABLATION_ACTIVATION_MATRIX.json`
(`matrix_fingerprint ab43db8fcabd3f7e064e184889d51de583a1e5702429fa2c018afb65de8c14ca`).

---

## 1. What this artifact proves

Which optional acceleration kernel is *actually invoked* in each candidate
execution environment, for each of the six frozen R4 models. It is the
mechanical precondition for the ablation: without it, a "candidate" could be
numerically identical to the reference simply because its kernel never
activated.

## 2. Detection method

The transformer hub-kernel decorator is
`transformers/integrations/hub_kernels.py:829
use_kernel_func_from_hub_with_fallback(func_name, package, internal_path=None)`.
It builds `wrapped` as

```python
@functools.wraps(torch_function)
def wrapped(*args, **kwargs): ...
```

`functools.wraps` copies `__module__`, `__name__`, `__qualname__`, `__doc__`,
`__dict__` and `__wrapped__` from the **torch fallback**, so any metadata-based
probe (`__module__`, `__name__`) can never distinguish a fast kernel from the
fallback. The only reliable discriminator is the decorator's own closure free
variable:

```text
is_new_implementation = implementation is not torch_function
```

This matrix was produced by reading `is_new_implementation` (and
`implementation`) out of each decorated module attribute's closure. A second,
independent signal is the loader warning
``… is falling back to its reference PyTorch implementation because
`<distribution>` is not installed``, which is emitted only when
`is_new_implementation` is false.

A third artefact worth recording: the *decorated Python name* frequently differs
from the *kernel `func_name`*. In `modeling_falcon_h1.py`, for example,
`use_kernel_func_from_hub_with_fallback("mamba_chunk_scan_combined", "mamba_ssm")`
decorates `def mamba2_chunk_scan(...)`. Module-level attribute names are
therefore `mamba2_*`, not the kernel names.

## 3. Candidate environments

| id | path | added packages | role |
| --- | --- | --- | --- |
| `R0` | `/root/rivermind-data/envs/probvenance-r4` | — | reference |
| `C1` | `/root/rivermind-data/envs/probvenance-r4-kernel-c1` | `causal-conv1d==1.7.0` | ablation candidate |
| `C2` | `/root/rivermind-data/envs/probvenance-r4-kernel-c2` | `causal-conv1d==1.7.0`, `mamba-ssm==2.3.1` | ablation candidate (degenerate) |
| `C3` | `/root/rivermind-data/envs/probvenance-r4-kernel-c3` | `causal-conv1d==1.7.0`, `flash-linear-attention==0.5.2`, `fla-core==0.5.2`, `einops==0.8.2` | ablation candidate |
| `F0` | `/root/rivermind-data/envs/probvenance-r4-fast` | all five | historical control, `REJECTED_AND_REMAINS_REJECTED` |

## 4. Availability guards (from `transformers/utils/import_utils.py`)

| guard | R0 | C1 | C2 | C3 |
| --- | --- | --- | --- | --- |
| `is_triton_available` | True | True | True | True |
| `is_causal_conv1d_available` | False | True | True | True |
| `is_mamba_ssm_available` | False | False | **True** | False |
| `is_mamba_2_ssm_available` | False | False | **True** | False |
| `is_flash_linear_attention_available` | False | False | False | True |

## 5. Per-model activation

### falcon-h1-7b-instruct — `transformers.models.falcon_h1.modeling_falcon_h1`

| site | R0 | C1 | C2 | C3 |
| --- | --- | --- | --- | --- |
| `causal_conv1d_fn` | fallback | **fast** | **fast** | **fast** |
| `causal_conv1d_update` | fallback | **fast** | **fast** | **fast** |
| `mamba2_split_conv1d_scan_combined` | fallback | fallback | fallback | fallback |
| `mamba2_selective_state_update` | fallback | fallback | fallback | fallback |
| `mamba2_chunk_scan` | fallback | fallback | fallback | fallback |

### granite-4-0-h-tiny — `transformers.models.granitemoehybrid.modeling_granitemoehybrid`

Identical pattern to Falcon-H1 (same five sites, same activation).

### qwen3-5-9b / qwen3-5-2b — `transformers.models.qwen3_5.modeling_qwen3_5`

| site | R0 | C1 | C2 | C3 |
| --- | --- | --- | --- | --- |
| `causal_conv1d_fn` | fallback | **fast** | **fast** | **fast** |
| `causal_conv1d_update` | fallback | **fast** | **fast** | **fast** |
| `torch_chunk_gated_delta_rule` | fallback | fallback | fallback | **fast** |
| `torch_recurrent_gated_delta_rule` | fallback | fallback | fallback | **fast** |

### olmo-3-7b-instruct (`models/olmo3/modeling_olmo3.py`) and minicpm5-2b (`models/llama/modeling_llama.py`)

**Zero hub-kernel sites in every environment.** Both modules only use
`@use_kernel_forward_from_hub("RMSNorm")` and `@use_kernel_forward_from_hub("rotary_pos_emb")`,
and `use_kernel_forward_from_hub` is an inert stub (`def decorator(cls): return cls`)
whenever `kernels` is not installed — which it is not, in any of the four
environments. No optional acceleration package can affect these two models.

## 6. Findings

1. `causal_conv1d` activates in **C1, C2 and C3** for Falcon-H1, Granite-4 and
   both Qwen3.5 models.
2. **C2 does not activate any mamba kernel.** `is_mamba_ssm_available()` reports
   `True` in C2, yet `importlib.import_module("mamba_ssm")` raises
   `ModuleNotFoundError: No module named 'einops'`, so the decorator's
   `try/except` silently keeps the torch fallback. The guard is a
   presence check that does not exercise the import. C2 is therefore
   **functionally identical to C1**.
3. `flash-linear-attention` activates only in **C3**, and only for the two
   Qwen3.5 gated-delta-rule sites.
4. Two of the six frozen models (Olmo-3, MiniCPM5-2B) have no acceleration
   surface at all; they can only ever run on R0.

## 7. Decision

```text
R4 KERNEL ABLATION ACTIVATION MATRIX = COMPLETE
C2 ACTIVATION = DEGENERATE (IDENTICAL TO C1) — INELIGIBLE / DIAGNOSTIC_ONLY / NOT_SELECTABLE
```
