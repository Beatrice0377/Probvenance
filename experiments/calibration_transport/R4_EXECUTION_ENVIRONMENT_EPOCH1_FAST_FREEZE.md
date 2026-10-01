# R4 — Execution Environment, Epoch 1 (Fast-Kernel Qualification Record)

```text
STATUS: BLOCKED
FREEZE PERFORMED: NO
EPOCH 1 EXECUTION ENVIRONMENT: NOT ADOPTED
R4 EXECUTION READINESS — EPOCH 1: BLOCKED
FORMAL R4 EPOCH 1 EXECUTION: NOT AUTHORIZED
```

> **Naming note.** The amendment named this artifact
> `R4_EXECUTION_ENVIRONMENT_EPOCH1_FAST_FREEZE.json`. It is deliberately kept under
> that filename so the amendment's checklist can be followed item by item, but its
> status is **BLOCKED** and **no environment is frozen**. The proposed fast-kernel
> environment failed the predeclared numerical-equivalence gate and was **not**
> adopted. See `R4_FAST_KERNEL_NUMERICAL_EQUIVALENCE.md`.

This is an **outcome-blind operational artifact**. No scientific outcome was
inspected. No model, revision, population, manifest, anchor, ground truth, prompt,
verbalizer, measurement contract, calibration family, estimand, metric,
multiplicity rule or predictor semantic was changed.

---

## 1. What this artifact decides

The amendment proposed an isolated accelerated environment
(`probvenance-r4-fast`) to remove the throughput problem that caused the Epoch 0
abort. Adopting it would change the numbers that the frozen R4 protocol treats as
raw evidence, so the amendment predeclared a numerical-equivalence gate.

**The gate failed.** Therefore:

* no Epoch 1 execution environment is frozen;
* the formal reference environment remains the only qualified R4 execution
  environment, and it is preserved byte-identical;
* PHASE G (performance) and PHASE H (fast-environment preflight) were **not
  executed**, because the amendment conditions them on `PHASE F = PASS`;
* no Epoch 1 study row was executed.

## 2. Parent frozen authority (unchanged)

| fingerprint | value |
| --- | --- |
| `final_protocol_fingerprint` | `d1b56d702e1f260cef47eee05b7d878ace07a15168e89408e15e7eb741c0ad34` |
| `execution_manifest_fingerprint` | `f32381c51db24f5dbeb240b5e0fdf73c59a56a615c8607ad8979e2a7e2586775` |
| `measurement_contract_fingerprint` | `7b126d300e774cb44d2c47fcb12513865d03c2b08ffd03a5ce409b2ea976e1e5` |
| `predictor_freeze_fingerprint` | `c856fcc161910497a3431593639606682905adcb50fc443455468dfc295d73a9` |
| `inference_multiplicity_freeze_fingerprint` | `dcbb7ac9e931145fdee86ab984de1249c1b86ca36ee735b70dafc8cabc06c141` |

## 3. Environments

| | reference (frozen, retained) | candidate fast (not adopted) |
| --- | --- | --- |
| path | `/root/rivermind-data/envs/probvenance-r4` | `/root/rivermind-data/envs/probvenance-r4-fast` |
| package count | 183 | 188 |
| `pip freeze` sha256 | `649b919aa26184a94c5ed56711187d4042bea112be1a531774b8405b2bdf82ba` | `0ee0b8774c0ea5258d844526b042c0c6895842cc3a50373f5055c9c593f27f54` |
| receipt | `R4_REFERENCE_ENVIRONMENT_PACKAGE_RECEIPT.txt` (`a7d78012…`) | `R4_FAST_KERNEL_PACKAGE_LOCK.json` (`d68da19d…`) |

Protected core (identical in both, unchanged by this amendment): python 3.11.13,
torch 2.8.0+cu128 (cuda 12.8), transformers 5.17.0, tokenizers 0.23.2,
safetensors 0.8.0, numpy 2.3.2, scipy 1.16.3, huggingface_hub 1.32.0, triton 3.4.0.

Added in the fast env only: `causal-conv1d 1.7.0`, `mamba-ssm 2.3.1`,
`flash-linear-attention 0.5.2`, `fla-core 0.5.2`, `einops 0.8.2`.

GPU: `NVIDIA GeForce RTX 4090`, driver `580.119.02`, 49140 MiB, compute capability
8.9, device `cuda:0`, dtype `bfloat16`.

## 4. Fast-path activation matrix

| model | architecture | hub-kernel sites | fast dep installed | fast path active |
| --- | --- | --- | --- | --- |
| `olmo-3-7b-instruct` | `Olmo3ForCausalLM` | 0 | n/a | no |
| `falcon-h1-7b-instruct` | `FalconH1ForCausalLM` | 5 | yes | **yes** |
| `granite-4-0-h-tiny` | `GraniteMoeHybridForCausalLM` | 5 | yes | **yes** |
| `qwen3-5-9b` | `Qwen3_5ForCausalLM` | 4 | yes | **yes** |
| `minicpm5-2b` | `LlamaForCausalLM` | 0 | n/a | no |
| `qwen3-5-2b` | `Qwen3_5ForCausalLM` | 4 | yes | **yes** |

Activation was proven by reading the decorator closure free variable
`is_new_implementation` (14/14 sites `True` in the fast env, `False` in the
reference env) and by the presence/absence of the transformers fallback warnings.
`__module__` cannot be used: `functools.wraps` copies it from the torch fallback.

## 5. Numerical equivalence (predeclared thresholds)

Thresholds, fixed before any fast result was seen: max abs restricted-probability
difference ≤ 0.005; max abs designated-score difference ≤ 0.005; max abs centered
restricted-logit difference ≤ 0.10; total variation distance ≤ 0.01; all values
finite.

| model | affected | max prob | max designated | max centered logit | max TV | status |
| --- | --- | --- | --- | --- | --- | --- |
| `olmo-3-7b-instruct` | no | 0 | 0 | 0 | 0 | PASS |
| `falcon-h1-7b-instruct` | yes | 6.437e-02 | 6.437e-02 | 4.121e-01 | 6.437e-02 | **FAIL** |
| `granite-4-0-h-tiny` | yes | 1.493e-01 | 1.306e-01 | 1.062e+00 | 1.493e-01 | **FAIL** |
| `qwen3-5-9b` | yes | 3.328e-02 | 3.328e-02 | 1.875e-01 | 3.328e-02 | **FAIL** |
| `minicpm5-2b` | no | 0 | 0 | 0 | 0 | PASS |
| `qwen3-5-2b` | yes | 2.976e-02 | 2.979e-02 | 1.250e-01 | 3.030e-02 | **FAIL** |

Battery `r4-fast-kernel-synthetic-equivalence-battery` v1, fingerprint
`c1e9d6488ec68cb44afb4d32d7468dc6b4acb70822f8f019389183cc1e4699bd`; synthetic only,
zero study rows. Rendered inputs, resolved token ids, snapshot paths, revisions and
`verify_verbalizers` reports were mechanically confirmed identical across the two
environments for all six models ⇒ the divergence is purely numerical.

Controls: reference-vs-reference-repeat PASS (bit-exact, all zeros);
fast-vs-fast-repeat FAIL (Falcon-H1 and granite non-deterministic run-to-run);
reference-repeat-vs-fast-repeat FAIL (the failure reproduces).

## 6. Not executed

| item | status | reason |
| --- | --- | --- |
| PHASE G performance qualification | NOT EXECUTED | conditioned on PHASE F PASS |
| PHASE H fast-env six-model preflight | NOT EXECUTED | conditioned on PHASE F PASS |
| Epoch 1 formal study rows | NOT EXECUTED | formal execution not authorized |

Host-memory gate was incidentally satisfied during the PHASE F captures: the
cgroup-v2-aware available memory (58.00 GiB limit) stayed ≈34 GiB, far above the
12 GiB floor. `/proc/meminfo` `MemAvailable` is host-wide and was not used as the
gate measure.

## 7. Epoch 1 status

| field | value |
| --- | --- |
| Epoch 0 | ABORTED / `DO_NOT_USE`, quarantined |
| Epoch 1 execution environment | **NOT ADOPTED — no environment frozen** |
| Epoch 1 readiness | **BLOCKED** |
| Epoch 1 staging root | `/root/rivermind-data/r4-formal-measurements` (empty, no cell directories) |
| Epoch 1 workload | unchanged: 100728 unique model×item rows, 100728 CAT, 100728 OVR, 201456 planned logical forwards |
| formal Epoch 1 execution | **NOT AUTHORIZED** |
| Epoch 1 real study rows executed | 0 |

## 8. Decision required

The next decision belongs to the human reviewer. The two mechanically available
options:

* **A** — run formal R4 Epoch 1 on the *frozen reference* environment (torch
  fallback), accepting the throughput that caused the Epoch 0 abort; or
* **B** — amend the predeclared numerical-equivalence contract and re-run PHASE F
  before any Epoch 1 row.

This artifact does not choose between them. No threshold was relaxed, no failing
prompt was dropped, no passing model was selected, no additional speculative
kernel library was installed, `trust_remote_code` was not enabled, and no
quantization / CPU offload / dtype change was used to force a pass.
