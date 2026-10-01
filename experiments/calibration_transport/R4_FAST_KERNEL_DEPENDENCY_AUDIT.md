# R4 Fast-Kernel Dependency Audit — Epoch 1 Execution Environment

```
artifact:            R4_FAST_KERNEL_DEPENDENCY_AUDIT.md
phase:               PHASE C (m04025)
date (machine UTC):  2026-10-01
status:              COMPLETE — AUDIT PASS
nature:              OPERATIONAL EXECUTION ENVIRONMENT AMENDMENT
                     (NOT a scientific protocol change)
scientific_semantics_changed:  false
```

## 0. Outcome firewall

This audit inspected **only** installed library source code, package metadata, import-time
decorator state, and the local model cache layout.

It read **no** R4 study item (no MMLU / HellaSwag / MedMCQA question), computed **no** model
score, **no** accuracy, **no** Brier, **no** LogLoss, and compared **no** model against any
other. The only model-touching operations were import-time introspection and (later, in
PHASE E/F) synthetic-only forwards on invented prompts.

## 1. Why this audit exists

Epoch 0 was aborted for a **predeclared operational performance reason**: `Falcon-H1-7B-Instruct`
executed through the reference/sequential Mamba path, giving ≈0.93 rows/s and making the frozen
workload impractical. The question this audit must answer mechanically is:

> Does the **exact installed** `transformers == 5.17.0` source contain fast-kernel paths for any
> of the six frozen models, and can those paths be activated **locally** without changing any
> protected core package, without `trust_remote_code`, and without changing measurement semantics?

## 2. Activation mechanism in `transformers == 5.17.0`

Source read (reference env, byte-identical in both envs):
`lib/python3.11/site-packages/transformers/integrations/hub_kernels.py`.

### 2.1 `use_kernel_func_from_hub_with_fallback`

`hub_kernels.py:829`:

```python
def use_kernel_func_from_hub_with_fallback(func_name: str, package: str, internal_path: str | None = None):
    kernel_wrapper_decorator = use_kernel_forward_from_hub(func_name)
    internal_path = _KERNELS_INTERNAL_PATH_MAPPINGS.get(func_name, internal_path)  # defaults
    full_func_path = func_name if internal_path is None else f"{internal_path}.{func_name}"
    full_module_path = package if internal_path is None else f"{package}.{internal_path}"

    def decorator(torch_function: Callable) -> Callable:
        implementation = None
        try:
            module = importlib.import_module(package)
            implementation = resolve_internal_import(module, full_func_path)
            if implementation is None and full_module_path != package:
                module = importlib.import_module(full_module_path)
                implementation = getattr(module, func_name, None)
        except Exception:
            implementation = torch_function
        finally:
            implementation = torch_function if implementation is None else implementation

        applicable_params = tuple(inspect.signature(implementation).parameters)
        is_new_implementation = implementation is not torch_function

        @functools.wraps(torch_function)
        def wrapped(*args, **kwargs):
            if is_new_implementation and is_torchdynamo_exporting():
                return torch_function(*args, **kwargs)
            if not is_new_implementation and not is_torchdynamo_compiling():
                distribution = _PACKAGE_TO_DISTRIBUTION.get(package, package)
                logger.warning_once(
                    f"`{func_name}` is falling back to its reference PyTorch implementation because "
                    f"`{distribution}` is not installed. This is correct but much slower; install "
                    f"`{distribution}` for the optimized kernel."
                )
            kwargs = {k: v for k, v in kwargs.items() if k in applicable_params}
            return implementation(*args, **kwargs)

        return kernel_wrapper_decorator(wrapped)

    return decorator
```

Three load-bearing consequences:

1. **Resolution happens at model-module IMPORT time.** `importlib.import_module(package)` plus
   `resolve_internal_import(module, full_func_path)` is executed when the model module is first
   imported. If the package is importable at that moment, the fast implementation is captured;
   otherwise the torch reference function is captured.
2. **No loader flag is required.** Merely having the package importable locally is sufficient.
   `use_kernels=True` / `kernelize()` / HF hub kernels are a *separate, higher-priority* layer
   (priority order documented in the docstring: 1. HF kernels if requested, 2. original package,
   3. torch-only path). We deliberately do **not** use layer 1.
3. **`__module__` is useless as a probe.** `wrapped` is declared with
   `@functools.wraps(torch_function)`, so `__module__`, `__name__`, `__qualname__`, `__doc__`,
   `__dict__` and `__wrapped__` are all copied from the **torch fallback**. Any probe based on
   `__module__` (or on module-level attribute names matching the kernel `func_name`) yields a
   false `TORCH-FALLBACK` reading. The only reliable discriminators are (a) the closure cell
   `is_new_implementation`, (b) mechanical replication of the resolution, (c) the fallback
   warning text emitted at call time.

### 2.2 Package → distribution mapping

`hub_kernels.py:80`:

```python
_PACKAGE_TO_DISTRIBUTION = {"fla": "flash-linear-attention"}
```

### 2.3 Nested import mapping

`hub_kernels.py:67-77` (`_KERNELS_INTERNAL_PATH_MAPPINGS`), relevant entries:

| kernel `func_name` | internal path | resolved module |
| --- | --- | --- |
| `mamba_split_conv1d_scan_combined` | `ops.triton.ssd_combined` | `mamba_ssm.ops.triton.ssd_combined` |
| `mamba_chunk_scan_combined` | `ops.triton.ssd_combined` | `mamba_ssm.ops.triton.ssd_combined` |
| `selective_state_update` | `ops.triton.selective_state_update` | `mamba_ssm.ops.triton.selective_state_update` |
| `chunk_gated_delta_rule` | `ops.gated_delta_rule` | `fla.ops.gated_delta_rule` |
| `fused_recurrent_gated_delta_rule` | `ops.gated_delta_rule` | `fla.ops.gated_delta_rule` |
| `mamba_inner_fn`, `selective_scan_fn` | `ops.selective_scan_interface` | `mamba_ssm.ops.selective_scan_interface` |

### 2.4 Availability guards (`utils/import_utils.py`)

| guard | line | condition |
| --- | --- | --- |
| `is_triton_available()` | 805 | triton importable |
| `is_mamba_ssm_available()` | 959 | `is_torch_cuda_available() and _is_package_available("mamba_ssm")[0]` |
| `is_mamba_2_ssm_available()` | 966 | as above **and** `mamba_ssm >= 2.0.4` |
| `is_flash_linear_attention_available()` | 972 | package import name `fla` |
| `is_causal_conv1d_available()` | 983 | `is_torch_cuda_available() and _is_package_available("causal_conv1d")[0]` |

Note: the decorator at 2.1 does **not** consult these guards — it attempts the import directly.
The guards matter for the model's own branch decisions and for documentation.

### 2.5 `use_kernel_forward_from_hub` is a NO-OP without the `kernels` package

`hub_kernels.py:572` — when `kernels` is not installed, `_kernels_enabled = False` and:

```python
def use_kernel_forward_from_hub(*args, **kwargs):
    def decorator(cls):
        return cls
    return decorator
```

Verified: `is_kernels_available() == False` in **both** envs; `ALLOW_ALL_KERNELS == False` in both.
⇒ Any `@use_kernel_forward_from_hub("RMSNorm")` / `("rotary_pos_emb")` site is inert here, and
`use_kernels=True` is never enabled. This is the desired frozen behaviour (local-only, no Hub
kernel download, `trust_remote_code=False`).

## 3. Six-model dependency audit

| model | architecture (resolved class) | reference implementation | candidate fast implementation | required package(s) | currently installed? | auto-activation? | core-package mutation required? | eligible? | decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `allenai/Olmo-3-7B-Instruct` @ `6e5971d9…` | `Olmo3ForCausalLM` | plain attention + RMSNorm/rotary | — (only inert hub-kernel decorators) | none | n/a | n/a | no | n/a | **UNAFFECTED — no action** |
| `tiiuae/Falcon-H1-7B-Instruct` @ `41e72f27…` | `FalconH1ForCausalLM` | sequential/reference Mamba + `F.conv1d` | `causal_conv1d_fn`, `causal_conv1d_update`, `mamba_split_conv1d_scan_combined`, `mamba_chunk_scan_combined`, `selective_state_update` | `causal_conv1d`, `mamba_ssm` | NO (before) | YES (import-time) | no | YES | **INSTALL + QUALIFY** |
| `ibm-granite/granite-4.0-h-tiny` @ `791e0d3d…` | `GraniteMoeHybridForCausalLM` | same reference Mamba path | same 5 kernels | `causal_conv1d`, `mamba_ssm` | NO (before) | YES | no | YES | **INSTALL + QUALIFY** |
| `Qwen/Qwen3.5-9B` @ `c2022362…` | `Qwen3_5ForCausalLM` | reference Gated DeltaNet + `F.conv1d` | `causal_conv1d_fn`, `causal_conv1d_update`, `chunk_gated_delta_rule`, `fused_recurrent_gated_delta_rule` | `causal_conv1d`, `fla` (`flash-linear-attention`) | NO (before) | YES | no | YES | **INSTALL + QUALIFY** |
| `openbmb/MiniCPM5-2B` @ `12a3808a…` | `LlamaForCausalLM` | plain attention | — | none | n/a | n/a | no | n/a | **UNAFFECTED — no action** |
| `Qwen/Qwen3.5-2B` @ `15852e8c…` | `Qwen3_5ForCausalLM` | same as Qwen3.5-9B | same 4 kernels | `causal_conv1d`, `fla` | NO (before) | YES | no | YES | **INSTALL + QUALIFY** |

## 4. Per-model detail

### 4.1 `FalconH1ForCausalLM` — `transformers/models/falcon_h1/modeling_falcon_h1.py`

Import: line 36 `from ...integrations import use_kernel_forward_from_hub, use_kernel_func_from_hub_with_fallback, use_kernelized_func`

| line | kernel `func_name` | package | decorated python function (module-level attribute) |
| --- | --- | --- | --- |
| 351 | `causal_conv1d_update` | `causal_conv1d` | `causal_conv1d_update` |
| 371 | `causal_conv1d_fn` | `causal_conv1d` | `causal_conv1d_fn` |
| 394 | `mamba_split_conv1d_scan_combined` | `mamba_ssm` | `mamba2_split_conv1d_scan_combined` |
| 419 | `selective_state_update` | `mamba_ssm` | `mamba2_selective_state_update` |
| 481 | `mamba_chunk_scan_combined` | `mamba_ssm` | `mamba2_chunk_scan` |

Reference bodies are readable torch: `causal_conv1d_update` uses `F.conv1d` with a state copy
(lines 363-368); `mamba2_split_conv1d_scan_combined` is a stub `return None` (line 416) — i.e. the
reference path only works because the caller falls back to the chunked path.

### 4.2 `GraniteMoeHybridForCausalLM` — `transformers/models/granitemoehybrid/modeling_granitemoehybrid.py`

| line | kernel `func_name` | package | module-level attribute |
| --- | --- | --- | --- |
| 257 | `causal_conv1d_update` | `causal_conv1d` | `causal_conv1d_update` |
| 277 | `causal_conv1d_fn` | `causal_conv1d` | `causal_conv1d_fn` |
| 300 | `mamba_split_conv1d_scan_combined` | `mamba_ssm` | `mamba2_split_conv1d_scan_combined` |
| 325 | `selective_state_update` | `mamba_ssm` | `mamba2_selective_state_update` |
| 387 | `mamba_chunk_scan_combined` | `mamba_ssm` | `mamba2_chunk_scan` |

### 4.3 `Qwen3_5ForCausalLM` — `transformers/models/qwen3_5/modeling_qwen3_5.py`

Shared by **both** `Qwen/Qwen3.5-9B` and `Qwen/Qwen3.5-2B` (same modeling module).

| line | kernel `func_name` | package | module-level attribute |
| --- | --- | --- | --- |
| 249 | `causal_conv1d_update` | `causal_conv1d` | `causal_conv1d_update` |
| 269 | `causal_conv1d_fn` | `causal_conv1d` | `causal_conv1d_fn` |
| 300 | `chunk_gated_delta_rule` | `fla` | `torch_chunk_gated_delta_rule` |
| 437 | `fused_recurrent_gated_delta_rule` | `fla` | `torch_recurrent_gated_delta_rule` |

### 4.4 `Olmo3ForCausalLM` — unaffected

`transformers/models/olmo3/modeling_olmo3.py` contains only:
line 44 `@use_kernel_forward_from_hub("RMSNorm")`, line 102 `@use_kernel_forward_from_hub("rotary_pos_emb")`.
Both are inert no-op stubs without the `kernels` package (§2.5). No `use_kernel_func_from_hub_with_fallback`
site exists. ⇒ **no optional acceleration package applies.**

### 4.5 `LlamaForCausalLM` (MiniCPM5-2B) — unaffected

`transformers/models/llama/modeling_llama.py` contains only:
line 52 `@use_kernel_forward_from_hub("RMSNorm")`, line 137 `@use_kernel_forward_from_hub("rotary_pos_emb")`.
Same inert-stub situation. ⇒ **no optional acceleration package applies.**

## 5. Activation proof (PHASE E)

Because `__module__`-based probing is provably invalid (§2.1 point 3), activation was proven by
reading the **closure cell** `is_new_implementation` of each decorated module attribute, in both
envs, plus mechanical replication of the decorator's own resolution.

### 5.1 Mechanical replication of the decorator resolution (fast env)

For every (package, `func_name`) pair, replicating exactly
`importlib.import_module(package)` + `resolve_internal_import(module, full_func_path)`
(+ the nested-module fallback) returned a non-`None` implementation:

```
falcon   causal_conv1d  causal_conv1d_update             -> causal_conv1d.causal_conv1d_interface.causal_conv1d_update
falcon   causal_conv1d  causal_conv1d_fn                 -> causal_conv1d.causal_conv1d_interface.causal_conv1d_fn
falcon   mamba_ssm      mamba_split_conv1d_scan_combined  -> mamba_ssm.ops.triton.ssd_combined.mamba_split_conv1d_scan_combined
falcon   mamba_ssm      selective_state_update           -> mamba_ssm.ops.triton.selective_state_update.selective_state_update
falcon   mamba_ssm      mamba_chunk_scan_combined        -> mamba_ssm.ops.triton.ssd_combined.mamba_chunk_scan_combined
granite  (identical to falcon for all 5 pairs)
qwen3_5  causal_conv1d  causal_conv1d_update             -> causal_conv1d.causal_conv1d_interface.causal_conv1d_update
qwen3_5  causal_conv1d  causal_conv1d_fn                 -> causal_conv1d.causal_conv1d_interface.causal_conv1d_fn
qwen3_5  fla            chunk_gated_delta_rule           -> fla.ops.gated_delta_rule.chunk.chunk_gated_delta_rule
qwen3_5  fla            fused_recurrent_gated_delta_rule -> fla.ops.gated_delta_rule.fused_recurrent.fused_recurrent_gated_delta_rule
```

### 5.2 Closure probe — reference env vs fast env

Probe: import the model module, walk each decorated module attribute, read the free variables
`is_new_implementation` / `implementation` from `__closure__` (and through `__wrapped__`).

| model | module attribute | reference env | fast env |
| --- | --- | --- | --- |
| falcon | `causal_conv1d_update` | `False` → `…modeling_falcon_h1.causal_conv1d_update` | **`True`** → `causal_conv1d.causal_conv1d_interface.causal_conv1d_update` |
| falcon | `causal_conv1d_fn` | `False` | **`True`** → `causal_conv1d.causal_conv1d_interface.causal_conv1d_fn` |
| falcon | `mamba2_split_conv1d_scan_combined` | `False` | **`True`** → `mamba_ssm.ops.triton.ssd_combined.mamba_split_conv1d_scan_combined` |
| falcon | `mamba2_selective_state_update` | `False` | **`True`** → `mamba_ssm.ops.triton.selective_state_update.selective_state_update` |
| falcon | `mamba2_chunk_scan` | `False` | **`True`** → `mamba_ssm.ops.triton.ssd_combined.mamba_chunk_scan_combined` |
| granite | `causal_conv1d_update` | `False` | **`True`** |
| granite | `causal_conv1d_fn` | `False` | **`True`** |
| granite | `mamba2_split_conv1d_scan_combined` | `False` | **`True`** |
| granite | `mamba2_selective_state_update` | `False` | **`True`** |
| granite | `mamba2_chunk_scan` | `False` | **`True`** |
| qwen3_5 | `causal_conv1d_update` | `False` | **`True`** |
| qwen3_5 | `causal_conv1d_fn` | `False` | **`True`** |
| qwen3_5 | `torch_chunk_gated_delta_rule` | `False` | **`True`** → `fla.ops.gated_delta_rule.chunk.chunk_gated_delta_rule` |
| qwen3_5 | `torch_recurrent_gated_delta_rule` | `False` | **`True`** → `fla.ops.gated_delta_rule.fused_recurrent.fused_recurrent_gated_delta_rule` |

⇒ **14/14 decorated sites are on the torch reference path in the reference env and on the
optimised package path in the fast env.** The reference env is the negative control and
discriminates cleanly.

### 5.3 Availability guards (fast env)

```
is_triton_available                 = True
is_causal_conv1d_available          = True
is_mamba_ssm_available              = True
is_mamba_2_ssm_available            = True     (requires mamba_ssm >= 2.0.4; installed 2.3.1)
is_flash_linear_attention_available = True
```

### 5.4 Fast-path activation matrix

| model | reference fallback before? | fast dependency installed? | fast path actually active? | activation evidence |
| --- | --- | --- | --- | --- |
| Falcon-H1-7B-Instruct | YES (5/5 sites) | YES | **YES (5/5)** | closure `is_new_implementation=True`; resolution replicated; no fallback warning |
| granite-4.0-h-tiny | YES (5/5 sites) | YES | **YES (5/5)** | same |
| Qwen3.5-9B | YES (4/4 sites) | YES | **YES (4/4)** | same |
| Qwen3.5-2B | YES (4/4 sites) | YES | **YES (4/4)** | same module as Qwen3.5-9B |
| Olmo-3-7B-Instruct | n/a | n/a | **NO — unaffected** | no `use_kernel_func_from_hub_with_fallback` site |
| MiniCPM5-2B | n/a | n/a | **NO — unaffected** | no `use_kernel_func_from_hub_with_fallback` site |

## 6. Package decision

### 6.1 Installed

| package | version | why this version | rejection rationale |
| --- | --- | --- | --- |
| `causal-conv1d` | `1.7.0` | latest; deps only `torch`, `packaging`, `ninja`; exports `causal_conv1d_fn` / `causal_conv1d_update` matching the falcon_h1 / granitemoehybrid / qwen3_5 call sites | older `1.6.1`/`1.5.0.post8` export the same symbols; no reason to prefer them |
| `mamba-ssm` | `2.3.1` | deps `torch`, `triton` (unpinned), `ninja`, `einops`, `transformers`, `packaging`, `setuptools>=61.0.0` — no protected-core mutation | **`2.3.2.post1` REJECTED**: requires `tilelang==0.1.8`, `apache-tvm-ffi<=0.1.9`, `quack-kernels>=0.3.4`, `triton>=3.5.0`, which would force a triton upgrade away from the torch-pinned `3.4.0` |
| `flash-linear-attention` | `0.5.2` | shim package; requires `fla-core==0.5.2` + `transformers>=4.45.0` | pure-python, no compilation |
| `fla-core` | `0.5.2` | supplies `fla/ops` (`chunk_gated_delta_rule`, `fused_recurrent_gated_delta_rule`) | pure-python |
| `einops` | `0.8.2` | required by `mamba-ssm` and `fla-core`; **the only genuinely-new external dependency** | pure-python |

### 6.2 Why prebuilt wheels (not source builds)

`nvcc` is **not on PATH**, there is no `/usr/local/cuda*`, and `CUDA_HOME` is unset on this
instance. A local CUDA-extension build would first require installing an `nvcc` wheel and is
therefore strictly worse than using the upstream prebuilt wheels that already match this exact
ABI.

### 6.3 ABI match

```
torch                       2.8.0+cu128
torch._C._GLIBCXX_USE_CXX11_ABI = True
python                      3.11.13
machine                     x86_64
⇒ wheel flavour            cu12torch2.8cxx11abiTRUE-cp311-cp311-linux_x86_64
```

Both compiled wheels were obtained in exactly that flavour from the upstream GitHub releases
(`Dao-AILab/causal-conv1d` v1.7.0 and `state-spaces/mamba` v2.3.1) and verified against the
authoritative GitHub API per-asset `digest` field. See `R4_FAST_KERNEL_PACKAGE_LOCK.json`.

### 6.4 Explicitly NOT installed

`flash-attn`, `xformers`, `bitsandbytes`, `kernels`, and any `use_kernels=True` / Hub-kernel
route. Attention backend remains whatever PyTorch SDPA selects internally; it was not touched.

## 7. Protected-core protection

| protected core | reference env | fast env | changed? |
| --- | --- | --- | --- |
| python | 3.11.13 | 3.11.13 | NO |
| torch | 2.8.0+cu128 | 2.8.0+cu128 | NO |
| transformers | 5.17.0 | 5.17.0 | NO |
| huggingface_hub | 1.32.0 | 1.32.0 | NO |
| numpy | 2.3.2 | 2.3.2 | NO |
| scipy | 1.16.3 | 1.16.3 | NO |
| tokenizers | 0.23.2 | 0.23.2 | NO |
| safetensors | 0.8.0 | 0.8.0 | NO |
| triton | 3.4.0 | 3.4.0 | NO |
| `probvenance` source | `5654f799…` | `5654f799…` | NO |

`pip freeze` package count: reference `183` → fast `188`; the diff is **exactly** the five new
local-wheel lines. The reference env `pip freeze` sha256 is unchanged
(`649b919aa26184a94c5ed56711187d4042bea112be1a531774b8405b2bdf82ba`), proving the reference
env was never mutated.

## 8. Decision

```
R4 FAST-KERNEL DEPENDENCY AUDIT = PASS
```

Four frozen model entries are on the optimised path in the isolated fast env
(Falcon-H1, granite-4.0-h-tiny, Qwen3.5-9B, Qwen3.5-2B); two are provably unaffected
(Olmo-3, MiniCPM5-2B). No protected core package was changed, no `trust_remote_code` was used,
no Hub kernel was downloaded, and no attention backend was altered.

## 9. Open items (must pass before Epoch 1 may start)

1. PHASE F — synthetic reference-vs-fast numerical equivalence (thresholds predeclared in
   `R4_FAST_KERNEL_NUMERICAL_EQUIVALENCE.md`).
2. PHASE G — synthetic performance qualification (Falcon-H1 speed-up ≥ 2.0×; no affected model
   more than 10 % slower).
3. PHASE H — 6/6 synthetic preflight in the fast env.
4. PHASE I — targeted + full test suite in the fast env.
5. PHASE J — Epoch 1 execution-environment freeze.
