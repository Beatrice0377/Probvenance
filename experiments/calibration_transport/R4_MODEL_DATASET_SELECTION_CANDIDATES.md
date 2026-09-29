# R4 Model + Dataset Candidate Research

STATUS:
CANDIDATE RESEARCH / NOT FROZEN / NOT EXECUTION-AUTHORIZED

NO FINAL MODEL SELECTION
NO FINAL DATASET SELECTION

This memo researches candidates only. It does not freeze anything, does not run any
model inference, does not compute any calibration outcome, and does not create an R4
population manifest. Model and dataset revisions below are OBSERVED CANDIDATE REVISIONS
recorded during candidate research only — they are NOT frozen R4 revisions.

Authority: `docs/research/calibration-transport-r3-r4-paper-strategy.md` and
`experiments/calibration_transport/R4_DESIGN_DRAFT.md` (both STATUS DRAFT / NOT FROZEN /
NOT EXECUTION-AUTHORIZED).

---

## 1. Status / non-freeze declaration

- R3 is closed and frozen. Nothing in this memo re-runs, re-interprets, or modifies R3.
- No R3 identity is used here except to answer: what model family the existing models
  belong to, what engineering requirements the existing measurement interface imposes,
  whether a new model duplicates an existing one, and whether a new population keeps
  fixed-event semantics.
- No model weights were downloaded. No `model.forward()`, no generation, no CAT/OVR
  scoring, no GPU use. Only small metadata (config.json / tokenizer_config.json /
  generation_config.json / model + dataset cards) and dataset structural statistics were
  read.
- No benchmark accuracy / leaderboard / calibration outcome was used to rank any
  candidate.
- Evidence classes used below:
  `[VERIFIED PRIMARY SOURCE]`, `[VERIFIED PAPER]`, `[STATIC REPO INSPECTION]`,
  `[ENGINEERING INFERENCE]`, `[UNVERIFIED / NEEDS PROBE]`.

## 2. Selection principles

1. Model choice is outcome-independent. It is driven only by family diversity, scale,
   fixed-revision availability, licensing, reproducibility, local inference support,
   tokenizer / chat-template stability, probability-extraction feasibility,
   thinking-mode controllability, `trust_remote_code` requirement, precision
   feasibility, single-GPU feasibility, repository stability, and engineering complexity.
   NOT by "which model scores best" and NOT by "which model is most likely to reproduce
   R3".
2. Dataset choice must serve fixed-event calibration transport, not benchmark popularity.
3. `deployment delta != transport penalty`; `direction-specific detection pattern !=
   formal between-direction difference`; `target-label-free != no labels anywhere`;
   `predictor development evidence != independent predictor validation evidence`.
   (Guardrails carried from the strategy doc.)
4. No numerical weighted score / composite ranking. Decision categories only:
   STRONG CANDIDATE FOR ENGINEERING PROBE / VIABLE WITH OPEN QUESTIONS / BACKUP / DEFER /
   EXCLUDE.
5. `EXCLUDE` requires a concrete factual reason, never a subjective preference.
6. Shortlist != final selection. This memo produces HUMAN-REVIEW SHORTLISTS only.

## 3. Existing R3 measurement-interface constraints

Extracted by read-only inspection of the frozen R3 measurement path. These are the hard
requirements any new model must satisfy. Source files: `measurements.py`,
`run_r3_measurements.py`, `r3_raw_evidence.py`, `r3_protocol.py`, `r3_population.py`,
`pilot_plan.py`, `src/probvenance/backends/transformers.py`,
`src/probvenance/backends/verbalizers.py`, `src/probvenance/compiler.py`,
`src/probvenance/doctrine.py`, `src/probvenance/assembler.py`,
`src/probvenance/diagnostics.py`, `experiments/semantic_signal/qwen35_loader.py`.

### 3.1 Model loading contract
- `AutoTokenizer.from_pretrained(model, revision=..., trust_remote_code=..., local_files_only=True)`
  and `AutoModelForCausalLM.from_pretrained(..., torch_dtype=..., local_files_only=True)`.
  `[STATIC REPO INSPECTION]` `src/probvenance/backends/transformers.py:79-101`.
- R3 passes `trust_remote_code=False`, `local_files_only=True`, `dtype="bfloat16"`
  `[STATIC REPO INSPECTION]` `run_r3_measurements.py:262-289`.
- No `device_map`, no `attn_implementation`, no quantization, no `generation_config`
  usage anywhere in `src/`. `[STATIC REPO INSPECTION]`
- Forward signature fixed: `model(input_ids=...)` returning `.logits`; single sequence,
  batch size 1, no truncation, no padding. `[STATIC REPO INSPECTION]`
  `transformers.py:302-331`.
- Replication-only precedent: Qwen3.5-2B needed a harness-side adapter
  (`Qwen35TextBackend` in `experiments/semantic_signal/qwen35_loader.py`) because it is
  not plain-`AutoModelForCausalLM` loadable. `[STATIC REPO INSPECTION]`

### 3.2 Prompt / tokenization contract
- Prompts come from frozen doctrines; the OVR proposition template is
  `"For the original choice task, is the designated candidate the correct answer?\n\nOriginal question:\n{question}\n\nDesignated candidate:\n{candidate_name}\n\nCandidate description:\n{candidate_description}\n"`.
  `[STATIC REPO INSPECTION]` `measurements.py:81-92`.
- CAT maps the 4 choices to scoring labels `"A","B","C","D"` (scheme
  `categorical-labels-v1`, cap 8). `[STATIC REPO INSPECTION]` `compiler.py:51,56,207`.
- OVR verbalizers are literally `"yes"` / `"no"`. `[STATIC REPO INSPECTION]`
  `compiler.py:46-47`.
- Rendering uses `tokenizer.apply_chat_template(messages, tokenize=False,
  add_generation_prompt=True, **template_kwargs)` when `tokenizer.chat_template` exists;
  otherwise plain concatenation. `[STATIC REPO INSPECTION]` `verbalizers.py:97-131`.
- **Hard single-token rule**: each of `"A"`,`"B"`,`"C"`,`"D"` and each of `"yes"`,`"no"`
  must be an EXACT single-token continuation of the rendered prefix
  (`tokenizer(prefix+label, add_special_tokens=False)` must reproduce `prefix_ids`
  exactly and append exactly one token; net +1 with retokenized prefix is rejected), and
  the resolved ids must be pairwise distinct. No fallback, no multi-token summing, no
  leading-space variant substitution. `[STATIC REPO INSPECTION]`
  `verbalizers.py:160-227,268-273`, `transformers.py:194-201`.
  Violation → `ScoringLabelError` / `VerbalizerError` → measurement `INELIGIBLE`.

### 3.3 Thinking-mode contract
- `chat_template_kwargs={"enable_thinking": False}` is forwarded verbatim into
  `apply_chat_template`. `[STATIC REPO INSPECTION]` `run_r3_measurements.py:264`,
  `r3_protocol.py:115`. It is part of the frozen protocol identity and is recorded as
  `rendering_config` in every raw record.
- If a candidate's template does not accept unknown kwargs, this can break the run —
  `[UNVERIFIED / NEEDS PROBE]`.

### 3.4 Precision / offline contract
- dtype `"bfloat16"`; allowed set `{float32,float16,bfloat16}`; no quantization.
  `[STATIC REPO INSPECTION]`
- `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` required; snapshot must pre-exist in the
  local HF cache. `[STATIC REPO INSPECTION]`
- Fixed 4-candidate shape: `R3_ANSWER_LABELS=("A","B","C","D")`,
  `R3_CANDIDATE_NAMES=("option-0".."option-3")`, zipped `strict=True`.
  `[STATIC REPO INSPECTION]` `r3_population.py:92-93,589-592`.
- Per item: 1 CAT + 4 OVR forwards = 5 evaluations; 1596 items → 7980 forwards/model.
  `[STATIC REPO INSPECTION]` `r3_protocol.py:144`.

### 3.5 Probability-extraction compatibility classes
A candidate must be classified as one of:
- **STATICALLY COMPATIBLE** — native `AutoModelForCausalLM` in the pinned transformers
  version, bf16 safetensors, plain causal-LM logits.
- **LIKELY COMPATIBLE — NEEDS TOKENIZER PROBE** — loadable, but single-token resolution
  of `A/B/C/D` and `yes/no` under its chat template is unverified.
- **NEEDS MODEL ENGINEERING PROBE** — composite/VL/MoE checkpoint needing a
  `Qwen35TextBackend`-style adapter.
- **KNOWN INCOMPATIBLE** — quantized-only, encoder-decoder, `trust_remote_code`-required
  with no adapter, or absent from the local HF cache.

"Transformers can load it" is never by itself a compatibility claim.

## 4. Model hard filters

A model candidate must satisfy ALL of:
1. nominal 7–8B scale;
2. current accessible fixed revision (a full 40-hex SHA);
3. local logits accessible (open weights, causal LM, not API-only);
4. not obviously deprecated / superseded checkpoint;
5. clear license / model card;
6. `[ENGINEERING INFERENCE]` BF16 weight footprint plausibly fits a single 24–32 GB GPU;
7. `[UNVERIFIED / NEEDS PROBE]` its tokenizer can resolve `A/B/C/D` and `yes/no` as
   distinct single-token continuations under its chat template.

## 5. Model source-verification table

All SHAs are OBSERVED CANDIDATE REVISIONS / NOT FROZEN.
`[VERIFIED PRIMARY SOURCE]` = Hugging Face repository metadata / `config.json` /
`tokenizer_config.json` / `generation_config.json` / model card, read during this memo.

| id | org | family | scale | instruct | observed revision (main) | license | gated | BF16 shards (GiB) |
|---|---|---|---|---|---|---|---|---|
| M1 `mistralai/Mistral-7B-Instruct-v0.3` | Mistral AI | Mistral | 7B | yes | `c170c708c41dac9275d15a8fff4eca08d52bab71` | `apache-2.0` | no | 13.50 (3 shards) + duplicate `consolidated.safetensors` |
| M2 `allenai/OLMo-2-1124-7B-Instruct` | Allen AI | OLMo 2 | 7B | yes | `470b1fba1ae01581f270116362ee4aa1b97f4c84` | `apache-2.0` | no | 13.60 (3 shards) |
| M3 `meta-llama/Llama-3.1-8B-Instruct` | Meta | Llama 3.1 | 8B | yes | `0e9e39f249a16976918f6564b8830bc894c89659` | `llama3.1` (Meta Llama 3.1 Community License) | **manual (gated)** | 14.96 (4 shards) |
| M4 `Qwen/Qwen3-8B` | Alibaba | Qwen3 | 8B | yes | `b968826d9c46dd6066d109eabc6255188de91218` | `apache-2.0` | no | 15.26 (5 shards) |
| M5 `ibm-granite/granite-3.1-8b-instruct` | IBM | Granite 3.1 | 8B | yes | `4009206d5fc95d2e65a7b7633e159d6e97e25d35` | `apache-2.0` | no | 15.22 (4 shards) |
| M6 `tiiuae/Falcon3-7B-Instruct` | TII | Falcon3 | 7B | yes | `1e57a0ecd176c7c139f289c60a74e57f887c3dfb` | `other` → TII Falcon License (custom) | no | 13.89 (4 shards) |

## 6. Model candidate cards

### 6.1 M1 — `mistralai/Mistral-7B-Instruct-v0.3`
- canonical model_id: `mistralai/Mistral-7B-Instruct-v0.3`; org: Mistral AI.
- family: Mistral (base `mistralai/Mistral-7B-v0.3`) `[VERIFIED PRIMARY SOURCE]`.
- nominal scale: 7B; instruct/chat: yes.
- observed repository revision: `c170c708c41dac9275d15a8fff4eca08d52bab71`
  (lastModified 2025-12-03) — OBSERVED CANDIDATE REVISION / NOT FROZEN.
- license: `apache-2.0` `[VERIFIED PRIMARY SOURCE]`.
- architecture class: `MistralForCausalLM` (`model_type=mistral`), hidden 4096,
  32 layers, vocab 32768, 32 heads, 8 KV heads, max_position 32768
  `[VERIFIED PRIMARY SOURCE]` config.json.
- Transformers support: native `mistral` → `trust_remote_code` not required
  `[VERIFIED PRIMARY SOURCE]`.
- chat_template available: yes (v0.3 template, includes tool-calling) `[VERIFIED PRIMARY SOURCE]`.
- generation_config available: yes (bos 1, eos 2, pad None) `[VERIFIED PRIMARY SOURCE]`.
- thinking / reasoning mode: none `[VERIFIED PRIMARY SOURCE]`.
- local logits accessible: yes (causal LM) `[STATIC REPO INSPECTION]` + arch.
- safetensors: yes. BF16 declared: yes (`torch_dtype=bfloat16`) `[VERIFIED PRIMARY SOURCE]`.
- estimated BF16 footprint: 13.50 GiB for the 3 shards; repo also ships a
  `consolidated.safetensors` (13.50 GiB) which is a duplicate single-file copy — total
  27.00 GiB if both are fetched `[VERIFIED PRIMARY SOURCE]` file sizes.
- 24 GB single-GPU: plausible; 32 GB: plausible `[ENGINEERING INFERENCE]`.
- offline snapshot feasibility: yes `[ENGINEERING INFERENCE]`.
- tokenizer files: `tokenizer.json`, `tokenizer.model`, `tokenizer.model.v3`,
  `tokenizer_config.json`, `special_tokens_map.json` `[VERIFIED PRIMARY SOURCE]`.
- family overlap with MiniCPM: none. With Qwen: none.
- known reproducibility caveats: the model card demonstrates the
  `mistral-common` `MistralTokenizer` path (`tokenizer.model.v3`); the standard HF
  `LlamaTokenizer` path (`tokenizer.json`) is also present `[VERIFIED PRIMARY SOURCE]`.
  The two paths could in principle tokenize the scoring strings differently — probe.
- known model-card warnings: model card recommends `mistral-common`; `library_name` is
  `vllm` `[VERIFIED PRIMARY SOURCE]`.
- remaining engineering unknowns: `[UNVERIFIED / NEEDS PROBE]` single-token resolution
  of `A/B/C/D` and `yes/no` under its chat template; whether the template tolerates the
  unknown kwarg `enable_thinking=False`.

### 6.2 M2 — `allenai/OLMo-2-1124-7B-Instruct`
- canonical model_id: `allenai/OLMo-2-1124-7B-Instruct`; org: Allen AI.
- family: OLMo 2 (base chain `allenai/OLMo-2-1124-7B-DPO`) `[VERIFIED PRIMARY SOURCE]`.
- nominal scale: 7B; instruct/chat: yes.
- observed repository revision: `470b1fba1ae01581f270116362ee4aa1b97f4c84`
  (lastModified 2025-01-06) — OBSERVED CANDIDATE REVISION / NOT FROZEN.
- license: `apache-2.0` `[VERIFIED PRIMARY SOURCE]`.
- architecture class: `Olmo2ForCausalLM` (`model_type=olmo2`), hidden 4096, 32 layers,
  vocab 100352, 32 heads, 32 KV heads, max_position 4096 `[VERIFIED PRIMARY SOURCE]`.
- Transformers support: native `olmo2` → `trust_remote_code` not required
  `[VERIFIED PRIMARY SOURCE]`.
- chat_template available: yes `[VERIFIED PRIMARY SOURCE]`.
- generation_config available: yes (eos 100257, pad 100277, bos None) `[VERIFIED PRIMARY SOURCE]`.
- thinking / reasoning mode: none `[VERIFIED PRIMARY SOURCE]`.
- local logits accessible: yes.
- safetensors: yes. BF16 declared: yes `[VERIFIED PRIMARY SOURCE]`.
- estimated BF16 footprint: 13.60 GiB (3 shards) `[VERIFIED PRIMARY SOURCE]`.
- 24 GB: plausible; 32 GB: plausible `[ENGINEERING INFERENCE]`.
- offline snapshot feasibility: yes.
- tokenizer files: `tokenizer.json`, `vocab.json`, `merges.txt`, `tokenizer_config.json`
  (GPT2-style BPE, vocab 100352) `[VERIFIED PRIMARY SOURCE]`.
- family overlap with MiniCPM: none. With Qwen: none.
- known reproducibility caveats: model card `NOTE: 1/3/2025 UPDATE` — the original
  post-trained OLMo-2 models did not share the base pre-tokenization logic; Allen AI
  retrained the post-trained models and re-published them **under the same names**, moving
  the originals to a `-preview` suffix `[VERIFIED PRIMARY SOURCE]`. Therefore the same
  model name refers to different weights across time — revision pinning is mandatory.
- known model-card warnings: max context 4096 (short, but our prompts are short)
  `[VERIFIED PRIMARY SOURCE]`; tokenizer update history is the main caveat.
- remaining engineering unknowns: `[UNVERIFIED / NEEDS PROBE]` single-token resolution of
  `A/B/C/D` and `yes/no` (GPT2-style BPE with a large vocab can merge or split these);
  template tolerance of `enable_thinking=False`.

### 6.3 M3 — `meta-llama/Llama-3.1-8B-Instruct`
- canonical model_id: `meta-llama/Llama-3.1-8B-Instruct`; org: Meta.
- family: Llama 3.1.
- nominal scale: 8B; instruct/chat: yes.
- observed repository revision: `0e9e39f249a16976918f6564b8830bc894c89659`
  (lastModified 2024-09-25) — OBSERVED CANDIDATE REVISION / NOT FROZEN.
- license: `llama3.1` = Meta Llama 3.1 Community License `[VERIFIED PRIMARY SOURCE]`;
  repository contains `LICENSE` and `USE_POLICY.md`.
- gated: **manual** — requires HF access approval + token `[VERIFIED PRIMARY SOURCE]`;
  `config.json` / `tokenizer_config.json` were NOT retrievable without auth.
- architecture class: `[UNVERIFIED / NEEDS PROBE]` (config gated). Publicly this is an
  8B `LlamaForCausalLM`, but the config-derived fields were not verified in this memo.
- Transformers support: expected native `llama` `[ENGINEERING INFERENCE]` (unverified here).
- chat_template available: `[UNVERIFIED / NEEDS PROBE]` (gated). Note the default
  Llama-3.1 template injects a "Cutting Knowledge Date" / "Today Date" system preamble
  `[UNVERIFIED / NEEDS PROBE]` — a prompt-level difference to check against the R3
  doctrine.
- thinking / reasoning mode: none `[ENGINEERING INFERENCE]` (unverified).
- local logits accessible: yes (open weights, causal LM) `[ENGINEERING INFERENCE]`.
- safetensors: yes (4 shards). BF16: expected `[ENGINEERING INFERENCE]`.
- estimated BF16 footprint: 14.96 GiB (4 shards) `[VERIFIED PRIMARY SOURCE]` file sizes.
- 24 GB: plausible; 32 GB: plausible `[ENGINEERING INFERENCE]`.
- offline snapshot feasibility: yes once access is granted.
- tokenizer files: `tokenizer.json`, `tokenizer_config.json`, `special_tokens_map.json`
  `[VERIFIED PRIMARY SOURCE]` file listing.
- family overlap with MiniCPM: none. With Qwen: none.
- known reproducibility caveats: gated access (approval latency, token dependency);
  custom community license with an acceptable-use policy; 8B/128k class.
- known model-card warnings: license is NOT Apache-2.0 — it is the Meta Llama 3.1
  Community License; this must never be written as "open source".
- remaining engineering unknowns: `[UNVERIFIED / NEEDS PROBE]` config, chat template
  (including the knowledge-date preamble), tokenizer single-token resolution.

### 6.4 M4 — `Qwen/Qwen3-8B`
- canonical model_id: `Qwen/Qwen3-8B`; org: Alibaba Qwen.
- family: Qwen3 (base `Qwen/Qwen3-8B-Base`).
- nominal scale: 8B; instruct/chat: yes.
- observed repository revision: `b968826d9c46dd6066d109eabc6255188de91218`
  (lastModified 2025-07-26) — OBSERVED CANDIDATE REVISION / NOT FROZEN.
- license: `apache-2.0` `[VERIFIED PRIMARY SOURCE]`.
- architecture class: `Qwen3ForCausalLM` (`model_type=qwen3`), hidden 4096, 36 layers,
  vocab 151936, 32 heads, 8 KV heads, max_position 40960 `[VERIFIED PRIMARY SOURCE]`.
- Transformers support: native `qwen3` → `trust_remote_code` not required
  `[VERIFIED PRIMARY SOURCE]`.
- chat_template available: yes; template contains `enable_thinking` / `thinking`
  `[VERIFIED PRIMARY SOURCE]`.
- generation_config available: yes (eos [151645, 151643], pad 151643) `[VERIFIED PRIMARY SOURCE]`.
- thinking / reasoning mode: yes — thinking and non-thinking within one model; can be
  disabled via `enable_thinking=False` `[VERIFIED PRIMARY SOURCE]` (this is exactly the
  R3 mechanism).
- local logits accessible: yes.
- safetensors: yes. BF16: yes `[VERIFIED PRIMARY SOURCE]`.
- estimated BF16 footprint: 15.26 GiB (5 shards) `[VERIFIED PRIMARY SOURCE]`.
- 24 GB: plausible; 32 GB: plausible `[ENGINEERING INFERENCE]`.
- offline snapshot feasibility: yes.
- tokenizer files: `tokenizer.json`, `vocab.json`, `merges.txt`, `tokenizer_config.json`
  (`Qwen2Tokenizer`, vocab 151936) `[VERIFIED PRIMARY SOURCE]`.
- family overlap with MiniCPM: none. **With Qwen: HIGH** — the existing replication model
  is `Qwen/Qwen3.5-2B`, same broad Qwen lineage/vendor family.
- known reproducibility caveats: none major; thinking mode is controllable via the
  official template kwarg.
- known model-card warnings: none blocking.
- remaining engineering unknowns: `[UNVERIFIED / NEEDS PROBE]` single-token resolution
  (Qwen tokenizers usually resolve these cleanly, but it must be probed, not assumed).
- special positioning: this is a **same-broad-lineage scale-control candidate**, NOT a
  family-diversity candidate. It must not be counted as the strongest diversity option.

### 6.5 M5 — `ibm-granite/granite-3.1-8b-instruct` (additional candidate)
- canonical model_id: `ibm-granite/granite-3.1-8b-instruct`; org: IBM.
- family: Granite 3.1.
- nominal scale: 8B; instruct/chat: yes.
- observed repository revision: `4009206d5fc95d2e65a7b7633e159d6e97e25d35`
  (lastModified 2025-04-16) — OBSERVED CANDIDATE REVISION / NOT FROZEN.
- license: `apache-2.0` `[VERIFIED PRIMARY SOURCE]`.
- architecture class: `GraniteForCausalLM` (`model_type=granite`), hidden 4096, 40 layers,
  vocab 49155, 8 KV heads, max_position 131072 `[VERIFIED PRIMARY SOURCE]`.
- Transformers support: native `granite` → `trust_remote_code` not required
  `[VERIFIED PRIMARY SOURCE]`.
- chat_template available: yes (no thinking) `[VERIFIED PRIMARY SOURCE]`.
- generation_config available: yes `[VERIFIED PRIMARY SOURCE]` (present in repo).
- thinking / reasoning mode: none `[VERIFIED PRIMARY SOURCE]`.
- local logits accessible: yes.
- safetensors: yes. BF16: yes `[VERIFIED PRIMARY SOURCE]`.
- estimated BF16 footprint: 15.22 GiB (4 shards) `[VERIFIED PRIMARY SOURCE]`.
- 24 GB: plausible; 32 GB: plausible `[ENGINEERING INFERENCE]`.
- offline snapshot feasibility: yes.
- tokenizer files: `tokenizer.json`, `vocab.json`, `merges.txt`, `added_tokens.json`
  (GPT2-style, vocab 49155) `[VERIFIED PRIMARY SOURCE]`.
- family overlap with MiniCPM: none. With Qwen: none.
- known reproducibility caveats: none identified; Apache-2.0 and non-gated.
- remaining engineering unknowns: `[UNVERIFIED / NEEDS PROBE]` tokenizer single-token
  resolution for `A/B/C/D` and `yes/no`.

### 6.6 M6 — `tiiuae/Falcon3-7B-Instruct` (additional candidate)
- canonical model_id: `tiiuae/Falcon3-7B-Instruct`; org: TII.
- family: Falcon3.
- nominal scale: 7B; instruct/chat: yes.
- observed repository revision: `1e57a0ecd176c7c139f289c60a74e57f887c3dfb`
  (lastModified 2025-05-31) — OBSERVED CANDIDATE REVISION / NOT FROZEN.
- license: `other` → TII Falcon License (custom, not OSI) `[VERIFIED PRIMARY SOURCE]`
  (`license_name=falcon-llm-license`, license link `https://falconllm.tii.ae/falcon-terms-and-conditions.html`).
- architecture class: `LlamaForCausalLM` (`model_type=llama`), hidden 3072, 28 layers,
  vocab 131072, 4 KV heads, max_position 32768 `[VERIFIED PRIMARY SOURCE]`.
- Transformers support: native `llama` → `trust_remote_code` not required
  `[VERIFIED PRIMARY SOURCE]`.
- chat_template available: yes (no thinking) `[VERIFIED PRIMARY SOURCE]`.
- thinking / reasoning mode: none.
- local logits accessible: yes.
- safetensors: yes. BF16: yes `[VERIFIED PRIMARY SOURCE]`.
- estimated BF16 footprint: 13.89 GiB (4 shards) `[VERIFIED PRIMARY SOURCE]`.
- 24 GB: plausible; 32 GB: plausible `[ENGINEERING INFERENCE]`.
- tokenizer files: `tokenizer.json`, `tokenizer_config.json`, `special_tokens_map.json`
  (`PreTrainedTokenizerFast`, vocab 131072) `[VERIFIED PRIMARY SOURCE]`.
- family overlap with MiniCPM: none. With Qwen: none. Architecture-class note: it uses the
  `LlamaForCausalLM` architecture class, so it shares the *architecture class* with M3
  while being a different training lineage `[VERIFIED PRIMARY SOURCE]`.
- known reproducibility caveats: custom TII Falcon License — not Apache-2.0/MIT; must be
  recorded accurately and evaluated for reproducibility/redistribution comfort.
- remaining engineering unknowns: `[UNVERIFIED / NEEDS PROBE]` tokenizer single-token
  resolution.

## 7. Model pair trade-offs

Evaluated on family diversity, license simplicity, reproducibility, measurement-interface
risk, thinking-mode complexity, same-family scale continuity, GPU feasibility, and
scientific interpretability. No composite score.

### 7.1 Mistral + OLMo
- family diversity: high (two unrelated families). `[ENGINEERING INFERENCE]`
- license: both `apache-2.0`, both non-gated — simplest pair.
- reproducibility: strong; both revision-pinnable; OLMo name-reuse caveat requires pinning.
- measurement-interface risk: both `[UNVERIFIED / NEEDS PROBE]` on tokenizer single-token
  resolution; neither has thinking mode (no thinking-control complexity).
- scale continuity: none within-family (both new families).
- GPU: both ~13.5–13.6 GiB BF16 → comfortable on 24 GB.
- interpretability: two clean, independent families; no vendor overlap with R3 models.

### 7.2 Mistral + Llama
- family diversity: high.
- license: Mistral Apache-2.0 vs Llama community license → asymmetric.
- reproducibility: Llama gated (approval + token) → friction; Mistral clean.
- measurement-interface risk: Llama config/template unverified (gated); knowledge-date
  preamble to reconcile with the R3 doctrine.
- GPU: both comfortable.

### 7.3 OLMo + Llama
- family diversity: high.
- license: Apache-2.0 vs community license.
- reproducibility: OLMo clean + Llama gated → mixed.
- measurement-interface risk: both need tokenizer probe; Llama additionally needs config
  probe.

### 7.4 Qwen3-8B + one non-Qwen family (e.g. Mistral, OLMo, or Granite)
- family diversity: reduced — Qwen3-8B is same broad lineage as the existing Qwen3.5-2B.
- scale continuity: Qwen3-8B provides an 8B point in the Qwen lineage (2B → 8B).
- license: Apache-2.0 + Apache-2.0 (if paired with Mistral/OLMo/Granite) — simple.
- thinking-mode complexity: Qwen3-8B has thinking mode; controllable via
  `enable_thinking=False` (already the R3 mechanism), so risk is low but non-zero.
- interpretability: confounds "family" with "scale" — must be reported as a
  scale-control, not a diversity gain.

### 7.5 Granite + Mistral (or Granite + OLMo)
- family diversity: high (IBM Granite vs Mistral/OLMo).
- license: both Apache-2.0, both non-gated → cleanest licensing.
- reproducibility: strong.
- measurement-interface risk: both need tokenizer probe.
- GPU: 15.22 + 13.50 GiB — comfortable.

### 7.6 Falcon3 + Mistral
- family diversity: high (TII lineage).
- license: TII Falcon License (custom) → reproducibility/licensing friction.
- reproducibility: non-gated but custom terms.

## 8. Human-review model shortlist (NOT FINAL)

Maximum three for the next engineering probe. Explicitly NOT a final selection.

- **STRONG CANDIDATE FOR ENGINEERING PROBE — M1 Mistral-7B-Instruct-v0.3.**
  Different family, Apache-2.0, non-gated, native Transformers, no thinking mode,
  comfortable GPU footprint.
- **STRONG CANDIDATE FOR ENGINEERING PROBE — M2 OLMo-2-1124-7B-Instruct.**
  Different family, Apache-2.0, non-gated, open-science lineage; main caveat is the
  1/3/2025 name-reuse/tokenizer-history event → pin the revision.
- **STRONG CANDIDATE FOR ENGINEERING PROBE — M5 granite-3.1-8b-instruct.**
  Different family (IBM Granite), Apache-2.0, non-gated, no thinking mode.

Then, for the record:
- **VIABLE WITH OPEN QUESTIONS — M3 Llama-3.1-8B-Instruct** (gated access, community
  license, unverified config/template).
- **VIABLE WITH OPEN QUESTIONS — M4 Qwen3-8B** (scale continuity, but family-redundant
  with the existing Qwen3.5-2B; thinking-mode control is already the R3 mechanism).
- **BACKUP — M6 Falcon3-7B-Instruct** (custom TII license).

Note: the human planning decision "2 × new 7–8B models" is not changed by this memo; the
shortlist of three gives room to pick two after the engineering probe.

## 9. Dataset hard filters

A dataset candidate must satisfy ALL of:
1. truly non-MMLU (not an MMLU derivative; MMLU-Pro does not automatically satisfy the
   non-MMLU breadth requirement — its lineage is too close);
2. publicly accessible with a stable revision;
3. clear license / usage status;
4. deterministic ground truth;
5. a single declared correct option;
6. CAT/OVR compatible (a fixed event D_i and a probability P(D_i correct) can be defined);
7. sufficient labeled data: enough for TRAIN calibrator fitting and enough untouched TEST;
8. natural or defensible strata (or an explicit statement that none exist);
9. documented choice structure;
10. fixed-event D_i construction natural;
11. not selected based on our model's outcome.

Choice-count is a first-class design factor: fixed 4 options has continuity with R3
(MMLU 4-option); fixed 5 options is usable but changes choice-set geometry and must be
recorded as a design difference; variable choice count increases measurement-semantics /
adapter complexity and must be evaluated explicitly.

## 10. Dataset source-verification table

All SHAs are OBSERVED CANDIDATE REVISIONS / NOT FROZEN.

| id | canonical dataset_id | config | observed revision (main) | license | task | choices | labeled splits |
|---|---|---|---|---|---|---|---|
| D1 | `Rowan/hellaswag` | default | `218ec52e09a7e7462a5400043bb9a69a41d06b76` | MIT | 4-way completion | fixed 4 | train, validation (test unlabeled) |
| D2 | `openlifescienceai/medmcqa` | default | `91c6572c454088bf71b679ad90aa8dffcd0d5868` | `apache-2.0` | medical MC | fixed 4 | train, validation (test unlabeled) |
| D3 | `tau/commonsense_qa` | default | `94630fe30dad47192a8546eb75f094926d47e155` | `mit` | commonsense MC | fixed 5 | train, validation (test unlabeled) |
| D4 | `allenai/ai2_arc` | ARC-Challenge / ARC-Easy | `210d026faf9955653af8916fad021475a3f00453` | `cc-by-sa-4.0` | science MC | variable (mostly 4; some 3/5) | train, validation, test |
| D5 | `allenai/openbookqa` | main | `388097ea7776314e93a529163e0fea805b8a6454` | HF card `unknown`; upstream repo Apache-2.0 (discrepancy) | science MC | fixed 4 | train, validation, test |
| D6 | `allenai/sciq` | default | `2c94ad3e1aafab77146f384e23536f97a4849815` | `cc-by-nc-3.0` (non-commercial) | science MC | 4 (assembled) | train, validation, test |

## 11. Dataset structural audit

Computed by reading the datasets (structural metadata only; no model outcome).
`[VERIFIED PRIMARY SOURCE]` / `[STATIC REPO INSPECTION]` of the dataset rows.

### 11.1 D1 HellaSwag
- splits: train 39905, validation 10042, test 10003 `[VERIFIED PRIMARY SOURCE]`.
- choice-count distribution: exactly 4 endings for 100% of rows in every split
  `[STATIC REPO INSPECTION]`.
- ground-truth field: `label` (integer 0–3); label distribution roughly uniform in
  train/validation `[STATIC REPO INSPECTION]`.
- label availability: train yes, validation yes, **test NO** (all test `label == ""`)
  `[STATIC REPO INSPECTION]`.
- `split_type`: train all `indomain`; validation `indomain` 5001 / `zeroshot` 5041;
  test 5002 / 5001 `[STATIC REPO INSPECTION]`.
- `activity_label`: train 178 strata (min 16, median 90.5, max 3962, 0% of strata < 5);
  validation 192 strata (8.85% < 5); test 207 `[STATIC REPO INSPECTION]`.
- `source_id`: 32220 unique of 39905 rows in train (some sharing) `[STATIC REPO INSPECTION]`.
- candidate TRAIN source: train; candidate TEST source: validation (test is unlabeled).

### 11.2 D2 MedMCQA
- splits: train 182822, validation 4183, test 6150 `[VERIFIED PRIMARY SOURCE]`.
- choice structure: `opa/opb/opc/opd` → exactly 4 options `[STATIC REPO INSPECTION]`.
- ground-truth field: `cop` ∈ {0,1,2,3}; train/validation have valid `cop`; **test `cop == -1`**
  (unlabeled) `[STATIC REPO INSPECTION]`.
- `choice_type`: train `single` 120765 / `multi` 62057; validation `single` 2816 /
  `multi` 1367; test `single` 4134 / `multi` 2016 `[STATIC REPO INSPECTION]`.
  **Clarification** `[VERIFIED PRIMARY SOURCE]` (dataset card): `single` = "Single-choice
  question, where each choice contains a single option"; `multi` = "Multi-choice question,
  where each choice contains a combination of multiple suboptions". It does NOT mean
  multiple correct answers; `cop` remains a single unique answer index.
- strata: `subject_name` — train 21 strata (min 1771, median 8282, max 17887, 0% < 5);
  validation 21 strata (min 2, median 129, max 1318, 4.76% < 5) `[STATIC REPO INSPECTION]`.
  `topic_name` — train 2389 strata, 26.41% < 5 → too sparse `[STATIC REPO INSPECTION]`.
- candidate TRAIN source: train; candidate TEST source: validation (test is unlabeled).

### 11.3 D3 CommonsenseQA
- splits: train 9741, validation 1221, test 1140 `[VERIFIED PRIMARY SOURCE]`.
- choice-count distribution: exactly 5 for 100% of rows `[STATIC REPO INSPECTION]`.
- ground truth: `answerKey` (A–E); train/validation labeled, **test unlabeled**
  `[STATIC REPO INSPECTION]`.
- `question_concept`: train 2151 strata (71.92% < 5); validation 785 strata (97.2% < 5);
  test 766 strata (98.04% < 5) → far too sparse for stratified resampling
  `[STATIC REPO INSPECTION]`.
- candidate TRAIN source: train; candidate TEST source: validation (1221; small).

### 11.4 D4 ARC
- ARC-Challenge: train 1119, validation 299, test 1172. ARC-Easy: train 2251,
  validation 570, test 2376 `[VERIFIED PRIMARY SOURCE]`.
- choice-count distribution (variable) `[STATIC REPO INSPECTION]`:
  - ARC-Challenge train {3:1, 4:1117, 5:1}; validation {3:3, 4:295, 5:1};
    test {3:4, 4:1165, 5:3}.
  - ARC-Easy train {3:6, 4:2241, 5:4}; validation {3:1, 4:567, 5:2};
    test {3:7, 4:2365, 5:4}.
- ground truth: `answerKey` (label string); present in ALL splits including test
  `[STATIC REPO INSPECTION]`.
- strata: no natural stratum field (columns are `id, question, choices, answerKey`)
  `[STATIC REPO INSPECTION]`.
- candidate TRAIN source: train; candidate TEST source: test (labels available) or
  validation (small).

### 11.5 D5 OpenBookQA (main config)
- splits: train 4957, validation 500, test 500 `[VERIFIED PRIMARY SOURCE]`.
- choice-count distribution: exactly 4 for 100% of rows `[STATIC REPO INSPECTION]`.
- ground truth: `answerKey`; present in ALL splits `[STATIC REPO INSPECTION]`.
- strata: no natural stratum field in `main` (`id, question_stem, choices, answerKey`)
  `[STATIC REPO INSPECTION]`; the `additional` config carries extra science facts but no
  obvious grouping field.
- candidate TRAIN source: train; candidate TEST source: test (500) — small.

### 11.6 D6 sciq
- splits: train 11679, validation 1000, test 1000 `[VERIFIED PRIMARY SOURCE]`.
- structure: fields `question, distractor1, distractor2, distractor3, correct_answer,
  support`; options must be assembled (correct + 3 distractors) → 4 choices
  `[STATIC REPO INSPECTION]`.
- ground truth: `correct_answer` (free text); present in all splits `[STATIC REPO INSPECTION]`.
- strata: none `[STATIC REPO INSPECTION]`.
- license: `cc-by-nc-3.0` (non-commercial) `[VERIFIED PRIMARY SOURCE]`.

## 12. Dataset candidate cards

### 12.1 D1 — `Rowan/hellaswag`
- canonical dataset_id: `Rowan/hellaswag`; config: default.
- observed revision: `218ec52e09a7e7462a5400043bb9a69a41d06b76` — OBSERVED CANDIDATE
  REVISION / NOT FROZEN.
- license: MIT `[VERIFIED PRIMARY SOURCE]` (dataset card "Licensing Information: MIT").
- task type: 4-way multiple-choice sentence/event completion.
- number of choices: 4; fixed or variable: fixed (100%).
- ground-truth field: `label` (0–3). Unique correct answer: yes.
- split names: train / validation / test; split sizes 39905 / 10042 / 10003.
- which splits expose labels: train, validation (test unlabeled).
- candidate TRAIN source: train; candidate TEST source: validation.
- natural strata fields: `activity_label` (also `split_type`). Number of strata: 178 (train).
  min/median/max items per stratum: 16 / 90.5 / 3962; fraction sparse (<5): 0% in train.
- fixed-event D_i construction: choose a single designated ending as the anchor candidate
  by a deterministic, measurement-independent rule (e.g. the existing sha256 anchor rule),
  then D_i = "the designated ending is the correct continuation".
- CAT compatibility: yes (4-way restricted softmax).
- OVR compatibility: yes (each ending is a binary candidate).
- population semantics vs MMLU: shared "pick one of fixed options" form; different
  domain (commonsense event completion), different context structure (ctx + 4 endings).
- contamination considerations: public benchmark; cannot exclude contamination; HellaSwag
  is old and widely used as a training target → elevated contamination risk
  `[ENGINEERING INFERENCE]`.
- known legal/licensing issue: none identified (MIT).
- known data-quality issue: test split is unlabeled in this mirror; some `source_id`
  sharing; validation contains `zeroshot` items whose endings are machine-generated
  `[ENGINEERING INFERENCE]`.
- engineering complexity: low (list of 4 endings + integer label).
- remaining unknowns: whether to use `activity_label` directly or a coarser activity
  family; how to handle duplicate `source_id`; `[UNVERIFIED / NEEDS PROBE]` whether the
  validation strata distribution supports grouped resampling (8.85% sparse).

### 12.2 D2 — `openlifescienceai/medmcqa`
- canonical dataset_id: `openlifescienceai/medmcqa`; config: default.
- observed revision: `91c6572c454088bf71b679ad90aa8dffcd0d5868` — OBSERVED CANDIDATE
  REVISION / NOT FROZEN.
- license: `apache-2.0` `[VERIFIED PRIMARY SOURCE]`.
- task type: 4-option medical multiple choice.
- number of choices: 4; fixed or variable: fixed.
- ground-truth field: `cop` (0–3). Unique correct answer: yes (also for `choice_type=multi`
  — see §11.2).
- split names: train / validation / test; sizes 182822 / 4183 / 6150.
- which splits expose labels: train, validation (test `cop=-1`).
- candidate TRAIN source: train; candidate TEST source: validation.
- natural strata fields: `subject_name` (preferred), `topic_name` (too sparse).
  `subject_name` train 21 strata, min/median/max 1771 / 8282 / 17887, 0% sparse.
- fixed-event D_i construction: designate one of `opa/opb/opc/opd` deterministically;
  D_i = "the designated option is the correct option".
- CAT compatibility: yes.
- OVR compatibility: yes.
- population semantics vs MMLU: shared 4-option form; different domain (professional
  medical QA), different item style (longer, exam-style), `choice_type=multi` items have
  composite choices.
- contamination considerations: public; cannot exclude; medical QA may be less saturated
  in general-purpose models `[ENGINEERING INFERENCE]`.
- known legal/licensing issue: none identified (Apache-2.0).
- known data-quality issue: `choice_type=multi` composite-choice items; `exp` field
  present; test unlabeled.
- engineering complexity: low–medium (4 separate option fields; strata via `subject_name`).
- remaining unknowns: whether to restrict to `choice_type=single`; whether composite
  `multi` items change fixed-event semantics; `[UNVERIFIED / NEEDS PROBE]` validation
  stratum sizes (min 2).

### 12.3 D3 — `tau/commonsense_qa`
- canonical dataset_id: `tau/commonsense_qa`; config: default.
- observed revision: `94630fe30dad47192a8546eb75f094926d47e155` — OBSERVED CANDIDATE
  REVISION / NOT FROZEN.
- license: `mit` `[VERIFIED PRIMARY SOURCE]`.
- task type: 5-way commonsense MC.
- number of choices: 5; fixed (100%) → choice-set geometry differs from R3's 4-choice.
- ground-truth field: `answerKey` (A–E). Unique correct answer: yes.
- splits: train 9741 / validation 1221 / test 1140; labels in train, validation (test
  unlabeled).
- candidate TRAIN source: train; candidate TEST source: validation (1221).
- natural strata fields: `question_concept` — far too sparse (train 72% < 5; validation
  97% < 5) → not usable as strata `[STATIC REPO INSPECTION]`.
- fixed-event D_i construction: designate one of the 5 choices deterministically.
- CAT/OVR compatibility: yes, but 5-way geometry.
- population semantics vs MMLU: different domain (commonsense), 5-choice geometry.
- contamination considerations: public; cannot exclude.
- known legal/licensing issue: none identified (MIT).
- known data-quality issue: none major; no usable strata.
- engineering complexity: low (choices dict), but 5-choice + no strata are the two
  design frictions.
- remaining unknowns: whether a 5-choice population is acceptable as a non-MMLU breadth
  population given the geometry change.

### 12.4 D4 — `allenai/ai2_arc` (ARC-Challenge / ARC-Easy)
- canonical dataset_id: `allenai/ai2_arc`; configs: ARC-Challenge, ARC-Easy.
- observed revision: `210d026faf9955653af8916fad021475a3f00453` — OBSERVED CANDIDATE
  REVISION / NOT FROZEN.
- license: `cc-by-sa-4.0` (share-alike) `[VERIFIED PRIMARY SOURCE]` → derivative
  redistribution obligations to record.
- task type: science MC.
- number of choices: variable (mostly 4; some 3, some 5) `[STATIC REPO INSPECTION]`.
- ground-truth field: `answerKey`; unique correct answer: yes.
- splits (sizes): ARC-Challenge 1119 / 299 / 1172; ARC-Easy 2251 / 570 / 2376.
- labels: all splits labeled (including test).
- candidate TRAIN source: train; candidate TEST source: test.
- natural strata: none.
- fixed-event D_i construction: designate one choice deterministically; but variable
  choice count complicates the "fixed 4-option" measurement contract.
- CAT/OVR compatibility: yes, but variable cardinality conflicts with the fixed-4
  contract unless filtered.
- population semantics vs MMLU: science MC, closest in flavor to MMLU among the
  candidates → lower population breadth value `[ENGINEERING INFERENCE]`.
- contamination: public; cannot exclude.
- known legal/licensing issue: `cc-by-sa-4.0` share-alike.
- known data-quality issue: variable choice count; no strata.
- engineering complexity: medium (variable cardinality).
- remaining unknowns: whether to filter to the 4-choice subset (changes the population
  definition) or to support variable cardinality.

### 12.5 D5 — `allenai/openbookqa` (main)
- canonical dataset_id: `allenai/openbookqa`; config: main.
- observed revision: `388097ea7776314e93a529163e0fea805b8a6454` — OBSERVED CANDIDATE
  REVISION / NOT FROZEN.
- license: **discrepancy** — HF dataset card declares `unknown`; the upstream
  `allenai/OpenBookQA` repository LICENSE is Apache-2.0 `[VERIFIED PRIMARY SOURCE]`
  (upstream repo). Needs human confirmation before use.
- task type: 4-choice science MC.
- number of choices: 4; fixed (100%).
- ground-truth field: `answerKey`; all splits labeled.
- splits: train 4957 / validation 500 / test 500 → TEST only 500.
- candidate TRAIN source: train; candidate TEST source: test (500) or validation+test
  (1000).
- natural strata: none.
- fixed-event D_i construction: natural (4-choice).
- CAT/OVR compatibility: yes.
- population semantics vs MMLU: science MC, MMLU-adjacent → lower breadth value.
- contamination: public; cannot exclude.
- known legal/licensing issue: license discrepancy (card unknown vs upstream Apache-2.0).
- known data-quality issue: small TEST (500).
- engineering complexity: low.
- remaining unknowns: license confirmation; whether 500 TEST items are enough for the R4
  bootstrap / TRAIN-refit contract.

### 12.6 D6 — `allenai/sciq` (additional candidate)
- canonical dataset_id: `allenai/sciq`; config: default.
- observed revision: `2c94ad3e1aafab77146f384e23536f97a4849815` — OBSERVED CANDIDATE
  REVISION / NOT FROZEN.
- license: `cc-by-nc-3.0` (non-commercial) `[VERIFIED PRIMARY SOURCE]` → licensing
  concern for open reproducibility.
- task type: 4-choice science MC (options assembled from `correct_answer` + 3 distractors).
- number of choices: 4 (constructed); fixed.
- ground truth: `correct_answer` (free text); all splits labeled.
- splits: train 11679 / validation 1000 / test 1000.
- strata: none.
- CAT/OVR compatibility: yes (after assembling a 4-choice list).
- engineering complexity: low–medium (option assembly).
- known legal/licensing issue: non-commercial license.
- remaining unknowns: whether NC licensing is acceptable.

## 13. Fixed-event D_i feasibility

For each serious candidate, the fixed event must be frozen BEFORE measurement and must be
measurement-independent (never chosen from a model winner, CAT/OVR agreement, or
correctness).

- D1 HellaSwag: feasible. Designate one ending as the anchor candidate via a deterministic,
  measurement-independent rule; D_i = "designated ending is the correct continuation".
- D2 MedMCQA: feasible. Designate one of `opa..opd`; D_i = "designated option is the
  correct option". Composite `choice_type=multi` items still have a unique `cop`.
- D3 CommonsenseQA: feasible. Designate one of 5 choices.
- D4 ARC: feasible but variable cardinality; requires either filtering to 4-choice or
  supporting variable cardinality (a semantics decision, not made here).
- D5 OpenBookQA: feasible (4-choice).
- D6 sciq: feasible (assemble 4 choices; designate one).

Continuity note: R3 uses a deterministic sha256 candidate-anchor rule
(`sha256-case-id-candidate-set-anchor`). Keeping a measurement-independent deterministic
rule (the same style, or a dataset-natural deterministic rule) is preferred. Do NOT
mechanically copy R3's random anchor if a dataset-natural measurement-independent rule is
more defensible — but nothing is frozen here.

## 14. Strata feasibility

Strata matter because R4 grouped resampling / predictor validation must not discover at
execution time that no reasonable strata exist.

- D1 HellaSwag: `activity_label` is a genuine stratification variable — 178 strata in
  train, 0% sparse; validation has 8.85% sparse strata (needs a minimum-count rule)
  `[STATIC REPO INSPECTION]`.
- D2 MedMCQA: `subject_name` is a genuine stratification variable — 21 strata in train,
  0% sparse; validation 4.76% sparse. `topic_name` is too sparse (26.41% < 5)
  `[STATIC REPO INSPECTION]`.
- D3 CommonsenseQA: `question_concept` is far too sparse (72–98% < 5) → not usable.
- D4 ARC: no natural strata.
- D5 OpenBookQA: no natural strata.
- D6 sciq: no natural strata.

Strata need not be the same across datasets; each dataset may use its own defensible
stratum definition, with an explicit justification of why the strata are scientifically
meaningful for that population. Sparse strata require a predeclared minimum-count rule.

## 15. Dataset pair trade-offs

### 15.1 HellaSwag + MedMCQA (analyzed in both directions, per §54)
Possible strengths:
- both truly non-MMLU;
- both near fixed-option multiple choice (HellaSwag fixed-4 endings; MedMCQA fixed-4
  options);
- strongly different population types (commonsense/event-completion vs professional
  medical QA);
- both have plausible natural strata (`activity_label` / `subject_name`);
- large samples (HellaSwag 39905+10042; MedMCQA 182822+4183).
Potential weaknesses (must be recorded):
- HellaSwag is old and widely used → elevated contamination/saturation risk
  `[ENGINEERING INFERENCE]`;
- HellaSwag validation has 8.85% sparse activity strata; MedMCQA validation has 4.76%
  sparse subject strata (min 2);
- MedMCQA validation (candidate TEST) is only 4183 items; MedMCQA `choice_type=multi`
  items have composite choices;
- HellaSwag TEST must come from validation because test is unlabeled.
Verdict: strong on paper; not auto-selected.

### 15.2 HellaSwag + CommonsenseQA
- both commonsense-flavored → less population diversity;
- CommonsenseQA is 5-choice (geometry change) and has no usable strata.
Verdict: weaker than 15.1.

### 15.3 MedMCQA + CommonsenseQA
- good domain diversity (medical vs commonsense);
- CommonsenseQA 5-choice + no strata remain the friction.
Verdict: viable but strata-poor on one leg.

### 15.4 HellaSwag + ARC
- HellaSwag good strata; ARC variable choice count + no strata + cc-by-sa + MMLU-adjacent
  flavor.
Verdict: weaker on strata/geometry/licensing.

### 15.5 MedMCQA + ARC
- same ARC friction; MedMCQA strong.
Verdict: viable but ARC-heavy friction.

### 15.6 OpenBookQA as backup
- 4-choice, all splits labeled, but TEST only 500 and license discrepancy.
Verdict: BACKUP.

## 16. Predictor-validation implications

- Hard minimum: `>= 1` truly non-MMLU population. Recommended target: `2` non-MMLU
  populations if the support predictor is to become a major contribution.
- Default grouped unit: `model × population × direction`. Multiple F values within the
  same grouped unit must NOT be treated as independent samples.
- D1+D2 (HellaSwag + MedMCQA) would provide two independent non-MMLU populations, each
  with its own strata, across both directions and multiple models → the most meaningful
  set of independent grouped validation units among the candidates examined.
- D3/D4/D5/D6 individually provide a non-MMLU population but with strata/geometry/licensing
  frictions; they are better as backups or as third populations than as the core pair.

## 17. Human-review dataset shortlist (NOT FINAL)

Maximum three for the next semantic/structural gate. Explicitly NOT a final selection.

- **STRONG CANDIDATE FOR NEXT GATE — D1 Rowan/hellaswag** (non-MMLU, fixed-4, usable
  activity strata, MIT; caveat: old/contamination, sparse validation strata).
- **STRONG CANDIDATE FOR NEXT GATE — D2 openlifescienceai/medmcqa** (non-MMLU, fixed-4,
  excellent subject strata, Apache-2.0, large; caveats: composite `multi` items, small
  validation TEST, sparse validation strata).
- **VIABLE WITH OPEN QUESTIONS — D4 allenai/ai2_arc (ARC-Easy / ARC-Challenge)**
  (non-MMLU, labels in all splits; caveats: variable choice count, no strata,
  cc-by-sa-4.0, MMLU-adjacent flavor).

Then, for the record:
- **BACKUP — D5 allenai/openbookqa** (4-choice, all splits labeled; caveats: TEST 500,
  license discrepancy).
- **BACKUP — D3 tau/commonsense_qa** (5-choice, no strata).
- **DEFER — D6 allenai/sciq** (non-commercial license).

The `>= 1` non-MMLU hard minimum is satisfied by any of D1–D5; the `2` recommended target
is best satisfied by D1+D2.

## 18. Model × dataset compatibility matrix

Evaluates semantic compatibility, engineering compatibility, and scientific
complementarity only — NOT outcome. Cells are qualitative.

| | D1 HellaSwag | D2 MedMCQA | D4 ARC | D5 OpenBookQA | D3 CommonsenseQA |
|---|---|---|---|---|---|
| M1 Mistral-7B-Instruct-v0.3 | high (4-choice, commonsense) | high (4-choice, medical) | medium (variable choice) | high (4-choice) | medium (5-choice) |
| M2 OLMo-2-1124-7B-Instruct | high | high | medium | high | medium |
| M3 Llama-3.1-8B-Instruct | high | high | medium | high | medium |
| M4 Qwen3-8B | high | high | medium | high | medium |
| M5 granite-3.1-8b-instruct | high | high | medium | high | medium |
| M6 Falcon3-7B-Instruct | high | high | medium | high | medium |

Reading the matrix:
- Semantic compatibility with D1/D2/D5 is uniformly high because they are fixed-4
  multiple choice, matching the R3 4-choice measurement contract.
- D4 is medium because variable choice cardinality requires either filtering or adapter
  work.
- D3 is medium because 5-choice changes choice-set geometry.
- Engineering compatibility is model-side (tokenizer single-token resolution) and is
  `[UNVERIFIED / NEEDS PROBE]` for every model; it does not depend on the dataset.
- Scientific complementarity is maximized by pairing a diverse model pair (e.g.
  Mistral+OLMo or Mistral+Granite) with D1+D2.

## 19. Explicit exclusions / deferrals

Models:
- `google/gemma-2-9b-it` — **DEFER**: gated (manual), 9B (above the 7–8B band), and a
  non-OSI Gemma license `[VERIFIED PRIMARY SOURCE]`. Recorded for completeness; not a
  shortlist candidate.
- M3 Llama-3.1-8B-Instruct — not excluded; VIABLE WITH OPEN QUESTIONS (gated, community
  license, unverified config/template).
- M6 Falcon3-7B-Instruct — not excluded; BACKUP (custom TII license).
- M4 Qwen3-8B — not excluded; VIABLE WITH OPEN QUESTIONS, but classified as a
  same-broad-lineage scale-control, not a diversity candidate.

Datasets:
- `allenai/quartz` — **DEFER**: 2-choice geometry (changes the choice-set contract
  substantially) `[STATIC REPO INSPECTION]`.
- D6 sciq — **DEFER**: `cc-by-nc-3.0` non-commercial license.
- MMLU-Pro / MMLU derivatives — **EXCLUDE as a non-MMLU answer**: lineage too close to
  MMLU; does not satisfy the external-review non-MMLU breadth requirement.
- D4 ARC — not excluded; kept as VIABLE WITH OPEN QUESTIONS despite variable cardinality
  and cc-by-sa.

## 20. Unknowns requiring engineering probe

All of the following are `[UNVERIFIED / NEEDS PROBE]` and require a future, separately
authorized probe (tokenizer-only, and only later optionally a weights/forward probe). No
probe was run in this memo.

1. For every model: whether `"A"`,`"B"`,`"C"`,`"D"` and `"yes"`,`"no"` each resolve to a
   distinct single token as an exact continuation of the rendered chat-template prefix
   (the decisive, GPU-free tokenizer probe).
2. For every model: whether its chat template tolerates the unknown kwarg
   `enable_thinking=False` (M4 Qwen3-8B supports it by design; others unknown).
3. M3 Llama-3.1-8B-Instruct: config-derived fields, chat template (including any
   knowledge-date preamble), and tokenizer resolution — blocked by gating.
4. M1 Mistral: whether the HF `LlamaTokenizer` path and the `mistral-common` v3 path agree
   on the scoring strings.
5. D2 MedMCQA: whether to restrict to `choice_type=single`; effect of composite `multi`
   items on fixed-event semantics.
6. D1 HellaSwag: whether `activity_label` should be used directly or grouped into coarser
   activity families; duplicate-`source_id` handling.
7. D4 ARC: whether to filter to the 4-choice subset or support variable cardinality.
8. License confirmations: OpenBookQA (card `unknown` vs upstream Apache-2.0); HellaSwag
   MIT link (card states MIT, but the raw LICENSE path returned 404 during this memo).

## 21. Next-gate proposal

Proposed next gate (human decision): **HUMAN MODEL + DATASET SHORTLIST REVIEW**.

Suggested review decisions to make:
- Q1. Which models truly satisfy the R3 measurement interface (pending tokenizer probe)?
- Q2. Which pair best maximizes family diversity (e.g. Mistral+OLMo, Mistral+Granite,
  OLMo+Granite)?
- Q3. Is Qwen3-8B's scale continuity worth the family redundancy with Qwen3.5-2B?
- Q4. Which datasets truly provide fixed-event semantics, enough samples, reasonable
  strata, and low adapter complexity (D1 and D2 are the leading answers)?
- Q5. If the predictor becomes a major contribution, which two non-MMLU populations give
  the most meaningful independent validation units (D1+D2 leading)?

Only after that gate should an engineering-probe round be authorized. R4 design freeze
remains a later gate.

## 22. Sources

Model cards / repositories (primary):
- `https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3` (config.json, tokenizer_config.json, README.md)
- `https://huggingface.co/allenai/OLMo-2-1124-7B-Instruct` (config.json, tokenizer_config.json, README.md)
- `https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct` (metadata only; gated)
- `https://huggingface.co/Qwen/Qwen3-8B` (config.json, tokenizer_config.json, README.md)
- `https://huggingface.co/ibm-granite/granite-3.1-8b-instruct` (config.json, tokenizer_config.json)
- `https://huggingface.co/tiiuae/Falcon3-7B-Instruct` (config.json, tokenizer_config.json)
- `https://huggingface.co/google/gemma-2-9b-it` (metadata only; gated)
- License sources: Mistral `apache-2.0` (card); OLMo `apache-2.0` (card + LICENSE);
  Llama `llama3.1` (card + LICENSE/USE_POLICY.md); Qwen `apache-2.0` (LICENSE);
  Granite `apache-2.0` (card); Falcon3 `falcon-llm-license`
  (`https://falconllm.tii.ae/falcon-terms-and-conditions.html`).

Dataset cards / repositories (primary):
- `https://huggingface.co/datasets/Rowan/hellaswag` (card: MIT; `https://github.com/rowanz/hellaswag`)
- `https://huggingface.co/datasets/openlifescienceai/medmcqa` (card: apache-2.0; choice_type definition)
- `https://huggingface.co/datasets/tau/commonsense_qa` (card: mit)
- `https://huggingface.co/datasets/allenai/ai2_arc` (card: cc-by-sa-4.0)
- `https://huggingface.co/datasets/allenai/openbookqa` (card: license unknown) and
  `https://github.com/allenai/OpenBookQA` (LICENSE: Apache-2.0)
- `https://huggingface.co/datasets/allenai/sciq` (card: cc-by-nc-3.0)
- `https://huggingface.co/datasets/allenai/quartz` (2-choice; deferred)

Repository-internal authority:
- `docs/research/calibration-transport-r3-r4-paper-strategy.md`
- `experiments/calibration_transport/R4_DESIGN_DRAFT.md`
- Frozen R3 measurement path (read-only): `measurements.py`, `run_r3_measurements.py`,
  `r3_raw_evidence.py`, `r3_protocol.py`, `r3_population.py`, `pilot_plan.py`,
  `src/probvenance/backends/transformers.py`, `src/probvenance/backends/verbalizers.py`,
  `src/probvenance/compiler.py`, `src/probvenance/doctrine.py`,
  `src/probvenance/assembler.py`, `src/probvenance/diagnostics.py`,
  `experiments/semantic_signal/qwen35_loader.py`.
