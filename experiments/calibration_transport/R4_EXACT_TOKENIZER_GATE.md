# R4 Exact Frozen-Doctrine Tokenizer Gate

STATUS:

```
PRE-FREEZE ENGINEERING GATE

TOKENIZER / TEMPLATE ONLY

NO MODEL FORWARD
NO MODEL WEIGHTS
NO MODEL OUTCOMES
NO FINAL MODEL SELECTION
NO R4 FREEZE
```

This document records a **tokenizer / chat-template semantic gate** for five
current-generation R4 model candidates. It is **not** a model-quality
benchmark, **not** a model inference run, **not** a calibration experiment, and
**not** a final model selection. Candidate search is **closed for this gate**;
no new models were searched for.

---

## 1. Scope and authority

Authority documents (read, unmodified):

- `docs/research/calibration-transport-r3-r4-paper-strategy.md`
- `experiments/calibration_transport/R4_DESIGN_DRAFT.md`
- `experiments/calibration_transport/R4_MODEL_DATASET_SELECTION_CANDIDATES.md`

The question answered here is narrow and mechanical:

> Under the **actual, frozen production measurement doctrine** and the **actual
> production chat-template scoring boundary**, are the target verbalizers
> `A/B/C/D` (CAT) and `yes/no` (OVR) still strict, unambiguous, single-token
> probability events for each candidate?

A candidate that cannot satisfy this is `TOKENIZER_INELIGIBLE` for the current
R4 design. The doctrine is **not** adjusted to make a candidate pass: no extra
spaces, no leading-space variants, no capitalisation changes, no multi-token
summation, no tokenizer special-casing.

The distinction enforced throughout:

- **CURRENT IMPLEMENTATION CONTRACT** — `AutoTokenizer` +
  `AutoModelForCausalLM` + `apply_chat_template` + next-token logits.
- **SCIENTIFIC MEASUREMENT REQUIREMENT** — the ability to define the target
  verbalizer's next-token probability *deterministically and reproducibly* at a
  frozen textual scoring boundary.

A non-`AutoModelForCausalLM` architecture is therefore **not** automatically
scientifically ineligible; conversely, "newer/stronger" never overrides
measurement exactness.

---

## 2. Repo / environment identity

| item | value |
|---|---|
| repository | `Beatrice0377/Probvenance` |
| branch | `main` |
| repo HEAD at gate time | `17a8bdb08d62609c4c214010d5792d1353a01b90` |
| origin/main at gate time | `17a8bdb08d62609c4c214010d5792d1353a01b90` |
| ahead/behind | `0 / 0` |
| working tree at gate start | clean |
| Python | `3.11.14` |
| transformers | `5.17.0` |
| tokenizers | `0.23.2` |
| huggingface_hub | `1.32.0` |
| dtype contract (R3) | `bfloat16` |
| rendering kwargs (R3) | `{"enable_thinking": False}` |

`transformers == 5.17.0` was required and confirmed; the environment was **not**
modified (no install / upgrade / lockfile change).

---

## 3. Production measurement path

The gate calls the **real production functions**, not re-implementations.

**CAT (`ChoiceDecision` → categorical token logits):**

1. `measurements.build_cat_decision(question, context, candidates)`
   → `ChoiceDecision` — `experiments/calibration_transport/measurements.py:105`
2. `compiler.ChoiceCompiler().compile(decision, BackendCapabilities(categorical_token_logits=True))`
   → `InferencePlan` with `targets = ("A","B","C","D")` — `src/probvenance/compiler.py:163`
3. `doctrine.CATEGORICAL_SEMANTIC_JUDGMENT_V1.render(...)`
   — `src/probvenance/doctrine.py:215`
4. `backends.verbalizers.render_input_text(tokenizer, system_prompt=…, user_prompt=…, template_kwargs=…)`
   — `src/probvenance/backends/verbalizers.py:97`
5. `backends.verbalizers.resolve_exact_single_token_continuation(...)` per label
   — `src/probvenance/backends/verbalizers.py:160`

**OVR (`BoolDecision` → binary token logits):**

1. `measurements.build_ovr_proposition(question, context, candidate_name, candidate_description)`
   → `BoolDecision` — `experiments/calibration_transport/measurements.py:138`
2. `compiler.BoolCompiler().compile(decision, BackendCapabilities(binary_token_logits=True))`
   → `InferencePlan` with `positive_verbalizer="yes"`, `negative_verbalizer="no"`
   — `src/probvenance/compiler.py:60`
3. `doctrine.BINARY_SEMANTIC_JUDGMENT_V1.render(...)` — `src/probvenance/doctrine.py:102`
4. `render_input_text(...)` — same as CAT
5. `backends.verbalizers.resolve_verbalizers(...)`
   — `src/probvenance/backends/verbalizers.py:230`

The production backend validates labels **before** any forward pass
(`src/probvenance/backends/transformers.py:151` `_plan_target_token_ids`,
`:113` `_plan_verbalizers`). This gate exercises exactly that validation path,
so a PASS here means the same validation that runs before a real model call.

---

## 4. Hard verbalizer contract

Frozen and **not relaxed**:

- CAT labels: `A`, `B`, `C`, `D`
- OVR verbalizers: `yes`, `no`
- exact continuation: `tokenizer(prefix + label) == tokenizer(prefix) + [label_token]`
  (the concatenated text must reproduce the rendered prefix tokenisation
  **exactly** and append exactly one token; a net delta of one is insufficient)
- CAT `A/B/C/D` ids pairwise **distinct**
- OVR `yes`/`no` ids **distinct**
- no multi-token summation, no alternative spelling, no leading-space fallback,
  no case fallback, no heuristic verbalizer replacement

Any violation ⇒ `TOKENIZER_INELIGIBLE`. The prefix is tokenised with
`add_special_tokens=False` (matching `resolve_exact_single_token_continuation`),
and the check is performed on the **production-rendered prefix**, never as an
isolated `tokenizer("A")`.

---

## 5. Candidate revisions

These are **probe reproducibility pins only** — `OBSERVED CANDIDATE REVISION`,
`NOT FROZEN`.

| # | canonical model id | observed revision |
|---|---|---|
| R1 | `allenai/Olmo-3-7B-Instruct` | `6e5971d9eba42665f5bd5a0fcf047f299ce1dccc` |
| R2 | `ibm-granite/granite-4.0-h-tiny` | `791e0d3d28c86e106c9b6e0b4cecdee0375b6124` |
| R3 | `mistralai/Ministral-3-8B-Instruct-2512` | `5b26027e7b19eeb4b7352e1fed3926375dd2cb4d` |
| R4 | `Qwen/Qwen3.5-9B` | `c202236235762e1c871ad0ccb60c8ee5ba337b9a` |
| R5 | `tiiuae/Falcon-H1-7B-Instruct` | `41e72f27effbab80cd45b6e884688452253a3686` |

All five revisions resolved successfully; no `revision="main"` fallback was
used and no substitution to a newer SHA occurred.

---

## 6. Synthetic fixtures

Non-study fixtures only (no MMLU / HellaSwag / MedMCQA / CommonsenseQA / ARC /
OpenBookQA item). No ground truth, no `Y`, no correctness — these fixtures test
**text rendering and token-continuation semantics only**.

| id | question | A | B | C | D |
|---|---|---|---|---|---|
| SYNTH-1 | "Synthetic probe one. Which option is explicitly named as the target symbol?" | Alpha | Beta | Gamma | Delta |
| SYNTH-2 | "Synthetic probe two. This item exists only to test probability-token boundaries." | red square | blue circle | green triangle | yellow star |
| SYNTH-3 | "Synthetic probe three. The strings below are arbitrary and are not benchmark data." | item 17 | item 204 | item 3.5 | item forty |

Shared synthetic context: `"Synthetic context block. Engineering compatibility
probe only."` Each OVR proposition is built per candidate (4 propositions per
fixture).

---

## 7. Probe method

| item | value |
|---|---|
| temp script | `/tmp/probvenance_r4_exact_tokenizer_gate.py` |
| script SHA256 | `d31ff1ead2127bc06a125995bd3a623d4b995289062a4256ca641fcd9a478db1` |
| raw probe output | `/tmp/r4_exact_tokenizer_gate_results.json` (58 947 bytes) |
| imports | `AutoTokenizer`, `AutoProcessor` only |
| model classes imported | **none** (script asserts `"AutoModelForCausalLM" not in sys.modules`) |
| network | tokenizer/template metadata only (`AutoTokenizer.from_pretrained`) |
| GPU | not used |

No model weights were fetched. The HF cache entries created for the five repos
contain only metadata / tokenizer files:

```
Olmo-3-7B-Instruct          : added_tokens.json, tokenizer.model, tokenizer_config.json, ...
granite-4.0-h-tiny          : added_tokens.json, tokenizer.model, tokenizer_config.json, ...
Ministral-3-8B-Instruct-2512: added_tokens.json, tokenizer.model, chat_template.json, special_tokens_map.json, audio_tokenizer_config.json, ...
Qwen3.5-9B                  : added_tokens.json, chat_template.json, special_tokens_map.json, processor_config.json, audio_tokenizer_config.json, ...
Falcon-H1-7B-Instruct       : added_tokens.json, tokenizer.model, tokenizer_config.json, ...
```

A filesystem scan for `*.safetensors|*.bin|*.pt|*.pth|*.gguf|*.onnx` under the
HF cache returned **empty**.

---

## 8. CAT exact-token matrix

Per candidate: 3 fixtures × 4 labels = **12 CAT exact-continuation checks**.
All 5 candidates passed all 12 (60 / 60 overall). Resolved ids are stable across
all fixtures.

| candidate | tokenizer class | SYNTH-1 A/B/C/D | SYNTH-2 A/B/C/D | SYNTH-3 A/B/C/D | result |
|---|---|---|---|---|---|
| R1 Olmo-3-7B-Instruct | TokenizersBackend | 32/33/34/35 | 32/33/34/35 | 32/33/34/35 | `CAT_EXACT_TOKEN_PASS` |
| R2 granite-4.0-h-tiny | TokenizersBackend | 32/33/34/35 | 32/33/34/35 | 32/33/34/35 | `CAT_EXACT_TOKEN_PASS` |
| R3 Ministral-3-8B-Instruct-2512 | TokenizersBackend | 1065/1066/1067/1068 | 1065/1066/1067/1068 | 1065/1066/1067/1068 | `CAT_EXACT_TOKEN_PASS` |
| R4 Qwen3.5-9B | Qwen2Tokenizer | 32/33/34/35 | 32/33/34/35 | 32/33/34/35 | `CAT_EXACT_TOKEN_PASS` |
| R5 Falcon-H1-7B-Instruct | TokenizersBackend | 1068/1069/1070/1071 | 1068/1069/1070/1071 | 1068/1069/1070/1071 | `CAT_EXACT_TOKEN_PASS` |

All ids pairwise distinct within each prefix. No multi-token label, no
retokenised prefix, no fallback.

## 9. OVR exact-token matrix

Per candidate: 3 fixtures × 4 candidate propositions = **12 OVR prefixes**,
each scored for `yes` and `no` = **24 exact-continuation checks per candidate**
(**120 / 120** overall).

| candidate | SYNTH-1 yes/no | SYNTH-2 yes/no | SYNTH-3 yes/no | result |
|---|---|---|---|---|
| R1 Olmo-3-7B-Instruct | 9891/2201 | 9891/2201 | 9891/2201 | `OVR_EXACT_TOKEN_PASS` |
| R2 granite-4.0-h-tiny | 9891/2201 | 9891/2201 | 9891/2201 | `OVR_EXACT_TOKEN_PASS` |
| R3 Ministral-3-8B-Instruct-2512 | 13059/2649 | 13059/2649 | 13059/2649 | `OVR_EXACT_TOKEN_PASS` |
| R4 Qwen3.5-9B | 9405/2083 | 9405/2083 | 9405/2083 | `OVR_EXACT_TOKEN_PASS` |
| R5 Falcon-H1-7B-Instruct | 5763/3257 | 5763/3257 | 5763/3257 | `OVR_EXACT_TOKEN_PASS` |

`yes` and `no` resolve to distinct single tokens in every proposition of every
fixture. The resolved ids are identical across all four propositions within a
fixture (the proposition body does not alter the label continuation), and
identical across fixtures.

**Context-dependent token-id audit (§21):** no candidate showed a token id that
varied with the prefix. `context_dependent = False` for all five.

---

## 10. Template-kwarg audit

`render_input_text` forwards `{"enable_thinking": False}` into
`apply_chat_template(..., add_generation_prompt=True, **kwargs)` for **every**
candidate (the kwarg is never dropped per-model).

| candidate | `apply_chat_template` with `enable_thinking=False` | official thinking mode | render effect of `enable_thinking=False` |
|---|---|---|---|
| R1 Olmo-3 | accepted | no | `NOT_APPLICABLE` (ignored) |
| R2 granite-4.0-h-tiny | accepted | no | `NOT_APPLICABLE` (ignored) |
| R3 Ministral-3 | accepted | no (instruct checkpoint) | `NOT_APPLICABLE` (ignored) |
| R4 Qwen3.5-9B | accepted | **yes** | `EFFECTIVE` (render changes) |
| R5 Falcon-H1 | accepted | no | `NOT_APPLICABLE` (ignored) |

**Qwen3.5-9B thinking verification.** Metadata-only render comparison on a
synthetic message:

| render | length |
|---|---|
| `enable_thinking=False` | 78 |
| `enable_thinking=True` | 67 |
| default (no kwarg) | 67 |

`False` differs from both `True` and default ⇒ the flag is **honoured** and is
the deterministic official disable path. The resulting prefix tail is
`…<|im_start|>assistant\n thinking\n\n</think>\n\n` — the official empty
reasoning block, i.e. thinking disabled. It contains **no** generated answer
content. This is the interface the R3 `Qwen35TextBackend` precedent already
uses.

**Template auto-fill check (§42).** Rendered prefix tails end at the generation
marker, with no auto-generated answer:

| candidate | CAT prefix tail | OVR prefix tail |
|---|---|---|
| R1 | `…Answer with exactly one scoring label from the list above.\n<|im_end|>\n<|im_start|>assistant\n` | `…"yes" or "no".\n<|im_end|>\n<|im_start|>assistant\n` |
| R2 | `…<|end_of_text|>\n<|start_of_role|>assistant<|end_of_role|>` | same marker, no answer |
| R3 | `…Answer with exactly one scoring label from the list above.\n[/INST]` | `…"yes" or "no".\n[/INST]` |
| R4 | `…<|im_start|>assistant\n thinking\n\n</think>\n\n` | same, no answer |
| R5 | `…Answer with exactly one scoring label from the list above.\n<|im_end|>\n<|im_start|>assistant\n` | same marker, no answer |

No template injects `A/B/C/D` or `yes/no` after the scoring boundary. No
`TEMPLATE BLOCKER`.

Different families render different system/role markers — this is expected and
is **not** a failure, because the scientific message content and the scoring
boundary are unchanged.

---

## 11. Model-specific caveats

### Olmo-3 (`allenai/Olmo-3-7B-Instruct`)
Clean `EXACT_TOKENIZER_PASS`. `TokenizersBackend`, chat template present, kwarg
tolerated. `A/B/C/D = 32/33/34/35`, `yes/no = 9891/2201`, all stable.

### Granite-4 (`ibm-granite/granite-4.0-h-tiny`)
Clean `EXACT_TOKENIZER_PASS`. The MoE/hybrid **forward** path is irrelevant to
the tokenizer gate and remains `FORWARD / HYBRID ENGINEERING UNVERIFIED` — the
gate verdict is not lowered because of MoE, and is not raised either.

### Ministral-3 (`mistralai/Ministral-3-8B-Instruct-2512`)
`EXACT_TOKENIZER_PASS`. transformers emits a tokenizer warning:

> "The tokenizer you are loading … with an incorrect regex pattern … This will
> lead to incorrect tokenization. You should set the `fix_mistral_regex=True`
> flag when loading this tokenizer to fix this issue."

**Dual-path comparison (§34/§35):**

| path | description | CAT | OVR | ids |
|---|---|---|---|---|
| A (current implementation-style) | `AutoTokenizer.from_pretrained(revision=…)` — R3 backend passes no regex flag | PASS 12/12 | PASS 24/24 | `A/B/C/D = 1065/1066/1067/1068`; `yes/no = 13059/2649` |
| B (official recommended) | `AutoTokenizer.from_pretrained(…, fix_mistral_regex=True)` | PASS 12/12 | PASS 24/24 | **identical** to path A |

`A PASS / B PASS` and A ≡ B on the frozen-doctrine prefixes ⇒ the current path
is adequate for the exact-token contract. The regex warning concerns
**arbitrary-text** tokenization and is recorded as a **documented engineering
caveat**, not a tokenizer-gate failure; whether to adopt `fix_mistral_regex=True`
is an engineering-probe / human-review question, not a semantic one.

**Ministral multimodal processor:** `AutoProcessor.from_pretrained` **failed**
in this environment (`PixtralProcessor requires the Torchvision library`). This
is an environment-metadata limitation for the *processor* route only; the
`AutoTokenizer` route used by production works. The environment was **not**
modified. Recorded as `PROCESSOR PATH NEEDS ENV/PROBE`, not a gate failure.

### Qwen3.5-9B (`Qwen/Qwen3.5-9B`)
`EXACT_TOKENIZER_PASS`. `Qwen2Tokenizer`, chat template present, thinking
disable verified effective (see §10). Independent verification was performed —
the existence of the R3 `Qwen3.5-2B` precedent was **not** treated as an
automatic PASS.

**Qwen3.5-9B multimodal processor:** `AutoProcessor.from_pretrained` **failed**
(`Qwen2VLImageProcessor requires the PIL library` / Torchvision). Same
environment-metadata limitation; the tokenizer route works and defines the
text-only scoring boundary. Recorded as `PROCESSOR PATH NEEDS ENV/PROBE`.

### Falcon-H1 (`tiiuae/Falcon-H1-7B-Instruct`)
Clean `EXACT_TOKENIZER_PASS`. The hybrid Mamba/Transformer **forward** path does
not affect the tokenizer gate. License friction (custom TII Falcon License) is
**not** a tokenizer-gate exclusion; it remains a final-selection trade-off.

---

## 12. Current-path vs official-path comparison

| candidate | current implementation path | official recommended path | agreement |
|---|---|---|---|
| Olmo-3 | PASS | n/a (no alternate official tokenizer flag) | n/a |
| granite-4.0-h-tiny | PASS | n/a | n/a |
| Ministral-3 | PASS | `fix_mistral_regex=True` → PASS | **identical ids** |
| Qwen3.5-9B | PASS | `enable_thinking=False` (already used) | official disable path in use |
| Falcon-H1 | PASS | n/a | n/a |

No candidate requires `EXACT_TOKENIZER_PASS_WITH_ENGINEERING_CHANGE` to satisfy
the exact-token contract.

---

## 13. Final tokenizer-gate classifications

| candidate | classification | forward-probe requirement |
|---|---|---|
| R1 Olmo-3-7B-Instruct | `EXACT_TOKENIZER_PASS` | model load / logits / memory / determinism |
| R2 granite-4.0-h-tiny | `EXACT_TOKENIZER_PASS` | MoE/hybrid forward still unverified |
| R3 Ministral-3-8B-Instruct-2512 | `EXACT_TOKENIZER_PASS` (regex caveat documented) | multimodal/`ForConditionalGeneration` forward + `fix_mistral_regex` decision |
| R4 Qwen3.5-9B | `EXACT_TOKENIZER_PASS` | multimodal forward / text-only logits path |
| R5 Falcon-H1-7B-Instruct | `EXACT_TOKENIZER_PASS` | hybrid forward; license is a selection trade-off |

No candidate is `TEMPLATE_BLOCKED`, `TOKENIZER_INELIGIBLE`, `ACCESS_BLOCKED`, or
`ENVIRONMENT_BLOCKED` at the tokenizer layer.

---

## 14. Candidates eligible for forward probe

All five passed the tokenizer gate. The **forward-probe shortlist** (≤ 4, **NOT
FINAL**, not ranked by benchmark strength) proposes:

1. `allenai/Olmo-3-7B-Instruct` — current-generation family diversity, clean gate
2. `ibm-granite/granite-4.0-h-tiny` — current-generation family diversity, clean gate (forward/hybrid unverified)
3. `mistralai/Ministral-3-8B-Instruct-2512` — current-generation family diversity; needs light adapter work for the multimodal class
4. `Qwen/Qwen3.5-9B` — scale-continuity candidate (2B → ~9B), clean gate

`tiiuae/Falcon-H1-7B-Instruct` is a **fully tokenizer-eligible alternate** held
in reserve (family diversity, clean gate, license friction).

This shortlist is a **decision aid only**. No final model pair is selected. The
scale-continuity role of Qwen3.5-9B does not silently widen the "2 × 7–8B"
planning minimum; any change to that minimum is a separate human gate.

## 15. Candidates blocked / ineligible

None at the tokenizer layer.

---

## 16. No-outcome / no-weight attestation

- model weights downloaded: **none**
- `model.from_pretrained` called: **no**
- model forward / generation: **none**
- GPU used: **no**
- study dataset item loaded: **no** (synthetic fixtures only)
- model outcome produced: **none**
- calibration / Brier / LogLoss / accuracy / transport: **none**
- repo working tree at gate start: **clean**

Only token ids and template-render facts (compatibility provenance) are
recorded.

---

## 17. Next gate

```
Exact Frozen-Doctrine Tokenizer Gate   (this document)
        ↓
HUMAN TOKENIZER-GATE REVIEW
        ↓
SMALL FORWARD ENGINEERING PROBE
  (real model load / next-token logits / memory / determinism)
        ↓
HUMAN FINAL MODEL-SELECTION GATE
```

A tokenizer PASS does **not** authorize a direct freeze of a model pair.

## 18. Unresolved issues

1. **Ministral-3 regex configuration** — current path and
   `fix_mistral_regex=True` agree on the frozen-doctrine prefixes, but the
   warning concerns arbitrary-text tokenization; human/engineering review
   required before freezing the adapter.
2. **Multimodal processor routes** — Ministral-3 and Qwen3.5-9B `AutoProcessor`
   loading needs `PIL` / `torchvision`, which the pinned environment lacks.
   Whether the text-only tokenizer route is sufficient for the forward probe, or
   the environment must be extended, is an engineering decision (environment was
   **not** changed here).
3. **Forward correctness** — logits, memory feasibility (24 GB / 32 GB), and
   determinism for all five candidates remain `NEEDS FORWARD PROBE`.
4. **Falcon-H1 license** — custom TII Falcon License; a final-selection
   trade-off, not a tokenizer issue.

---

## Sources

- `allenai/Olmo-3-7B-Instruct` — https://huggingface.co/allenai/Olmo-3-7B-Instruct
  (revision `6e5971d9eba42665f5bd5a0fcf047f299ce1dccc`), license Apache-2.0.
- `ibm-granite/granite-4.0-h-tiny` — https://huggingface.co/ibm-granite/granite-4.0-h-tiny
  (revision `791e0d3d28c86e106c9b6e0b4cecdee0375b6124`), license Apache-2.0.
- `mistralai/Ministral-3-8B-Instruct-2512` — https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512
  (revision `5b26027e7b19eeb4b7352e1fed3926375dd2cb4d`), license Apache-2.0.
- `Qwen/Qwen3.5-9B` — https://huggingface.co/Qwen/Qwen3.5-9B
  (revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a`), license Apache-2.0.
- `tiiuae/Falcon-H1-7B-Instruct` — https://huggingface.co/tiiuae/Falcon-H1-7B-Instruct
  (revision `41e72f27effbab80cd45b6e884688452253a3686`), license `other`
  (TII Falcon License).
- Production doctrine sources (SHA256 at gate time):
  - `src/probvenance/backends/verbalizers.py` — `f7abc7a862a29f517d78f944f04f912ba38f8cdc69bacdfa72830fab46e8e808`
  - `src/probvenance/backends/transformers.py` — `ff23f1ac5f0313935888d3b90af6d6c964ee0636f7270441fde78393b0f93c5c`
  - `src/probvenance/compiler.py` — `53d38f47a9137ba9820b4c934ef49080941da33478d3ac4ace151319e876fe12`
  - `src/probvenance/doctrine.py` — `602b365d3dae6bbccea603d6a355aba6f12cf3f03ab02ee5d8459e568aaac4f7`
  - `src/probvenance/assembler.py` — `d9b7aaf3b33e73195fd4b0c9af9c75ad652f52841cba761ee823637926053f7f`
  - `experiments/calibration_transport/measurements.py` — `e4436015576cc9944b7b60e6458f03ee80aad05bab0a369f3e2ace6f5de696b5`
  - `experiments/calibration_transport/run_r3_measurements.py` — `8100341f05654fe19c3278ad8edb454d1b41c6b0ac2bde426a3e1cf1ae6a03bf`
  - `experiments/calibration_transport/r3_protocol.py` — `46a7c0ec8e5da95a37868d89f5fc110687e66e65599ee4ac3d0602100435197e`
