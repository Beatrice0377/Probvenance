# R4 Measurement Implementation Engineering

```text
status : ENGINEERING RECORD (no study outcome was produced or read)
scope  : the formal R4 measurement runner, raw-evidence layer, and tests
```

本文件记录 R4 **formal measurement execution** 的实现工程事实。

它 **不** 包含任何正式 study outcome：

```text
NO real R4 CAT probability
NO real R4 OVR probability
NO real model logits on any study row
NO calibration fit
NO Brier
NO LogLoss
NO transport outcome
NO predictor value or correlation
```

---

## 1. Artifact block

| artifact | path | lines | sha256 |
|---|---|---|---|
| measurement contract (JSON) | `experiments/calibration_transport/R4_MEASUREMENT_EXECUTION_CONTRACT.json` | 479 | `c9d61ed3011a3d42c1455c8e6ff1c724d80a5ceebc2f507992e371d661e15e52` |
| measurement contract (MD) | `experiments/calibration_transport/R4_MEASUREMENT_EXECUTION_CONTRACT.md` | 418 | `7beb1e36192a286ea8410fe01111c746d74ea55130601a154d2830840644e401` |
| environment contract | `experiments/calibration_transport/R4_MEASUREMENT_EXECUTION_ENVIRONMENT.md` | 130 | `e794bddef9c909a7502fc6badd04f4805e350464aee0a34efb1fbacc858b01fd` |
| raw-evidence layer | `experiments/calibration_transport/r4_raw_evidence.py` | 452 | `12f1f037f0400dc7cbbf73e9f014e2ab735a341690e0431273281bdb6afe7dac` |
| measurement runner | `experiments/calibration_transport/run_r4_measurements.py` | 1028 | `2f6d59a06b1dbe869dfd1ec29e174d4246819e2d07ccb681db9fd6c681cc0601` |
| measurement tests | `tests/test_r4_measurements.py` | 1032 | `f36ddc56c11ab2587a8c74fd09e6db1345ffd3a2d3871334631a919bee337066` |

```text
measurement_contract_fingerprint = 7b126d300e774cb44d2c47fcb12513865d03c2b08ffd03a5ce409b2ea976e1e5
measurement_contract_status      = FROZEN
```

---

## 2. Measurement call contract

```text
measurement_call_contract_id = r4-fixed-event-two-forward-measurement
version                      = 1
```

每个 `model × population × item`：

```text
1 CAT forward
+
1 OVR forward for the frozen designated candidate D_i
=
2 model forward evaluations
```

R3 的历史契约（1 CAT + 4 OVR = 5 calls/item）被显式拒绝：

```text
r3_call_contract_inheritance = REJECTED
```

理由：R4 的 estimand 是外部冻结事件 `Y_i = 1[D_i = GT_i]`；CAT 与 OVR 都测量
`P(D_i correct)`，因此不需要重新构造 OVR winner，也不需要为其它三个候选做
OVR forward。

---

## 3. Environment contract

见 `R4_MEASUREMENT_EXECUTION_ENVIRONMENT.md`。要点：

```text
env path      : /root/rivermind-data/envs/probvenance-r4
python        : 3.11.13
torch         : 2.8.0+cu128
transformers  : 5.17.0
huggingface_hub : 1.32.0
dtype         : bfloat16
device        : cuda:0
batch size    : 1
GPU           : NVIDIA GeForce RTX 4090 (49140 MiB), driver 580.119.02
```

R3 的 environment gate（torch 2.14.0+cu130 / RTX 5060 Laptop）**不得** 被 R4
runner 继承。

本任务：

```text
NO pip install / upgrade / downgrade
```

---

## 4. Runner architecture

`experiments/calibration_transport/run_r4_measurements.py`：

```text
load frozen structural authority   -> load_frozen_authority()
verify Git state                   -> verify_git_state()
verify environment                 -> verify_environment()
verify offline environment         -> verify_offline_environment()
verify model cache                 -> verify_model_cache()
load one declared model condition  -> load_backend() / unload_backend()
verify verbalizers                 -> verify_verbalizers()
measure one declared population    -> run_cell() -> measure_item()
write one raw-evidence artifact    -> r4_raw_evidence.write_json()
validate artifact                  -> r4_raw_evidence.validate_raw_evidence()
```

runner **不**：

```text
fit calibrator
compute Brier
compute LogLoss
bootstrap
compute predictor
```

### 4.1 CLI

```text
--model-role / --model-id-key
--population
--output
--device          (仅当与 frozen contract 兼容)
--synthetic-preflight
```

scientific configuration（model revision、measurement semantics、verbalizers、
anchor rule、population manifest、TRAIN budget、TEST identity）**全部** 来自
frozen authority，不可由 CLI 任意修改。

### 4.2 Model registry

```text
current generation : olmo-3-7b-instruct, falcon-h1-7b-instruct,
                     granite-4-0-h-tiny, qwen3-5-9b
legacy secondary   : minicpm5-2b, qwen3-5-2b
```

Hella/Med 的 TRAIN 需求不同：

```text
current generation -> frozen N912 union
legacy secondary   -> N456
```

MMLU legacy：

```text
NOT RUNNABLE IN R4 / DO_NOT_RERUN
```

`resolve_cell()` 对 `legacy + MMLU` 在 domain level 拒绝
（`R4MeasurementDomainError`）。

### 4.3 Population registry

```text
mmlu        : primary + test identities
hellaswag   : primary + robustness912
medmcqa     : primary + robustness912
```

`resolve_cell()` 机械验证 required grid：

```text
total unique model x item rows = 100728
```

---

## 5. Raw-evidence schema

`experiments/calibration_transport/r4_raw_evidence.py`（research layer；**不修改**
frozen R3 schema `r3_raw_evidence.py`）。

一个 artifact = one `model × population` block，覆盖该 block 的 required frozen
TRAIN union + TEST。

每 item 至少：

```text
item_id
source split
source row identity/index
population identity
population manifest identity
anchor D_i
ground-truth candidate identity
Y = 1[D_i = GT_i]        (fixed_event)
CAT block
OVR block
```

### 5.1 CAT block

```text
status
anchor_score
restricted candidate probabilities (sum ~ 1)
resolved verbalizer token ids
top-token diagnostic
source-record fingerprint
```

fixed-event analysis 只消费 `anchor_score`。

### 5.2 OVR block（designated-only）

```text
designated_candidate = D_i
status
probability_true
probability_false
positive_token_id / negative_token_id
source-record fingerprint
```

**不** 要求 four-candidate OVR table，**不** 要求 OVR winner。

### 5.3 禁止字段

`r4_raw_evidence._assert_no_result_fields` 递归拒绝分析词汇：

```text
brier, log_loss, logloss, delta, native_risk, cross_risk, feature_effect,
regularization_effect, interaction, bootstrap, confidence_interval,
native_adequacy
```

### 5.4 Paired completeness

Calibration fitting / TEST inference 只能消费：

```text
CAT = SCORED AND OVR = SCORED
```

任何 missing ⇒ 该 `model × population` block = INCOMPLETE。禁止 drop row、
replace row、或只使用成功的 pair。

### 5.5 确定性

wall-clock timing **不进入** fingerprinted artifact（只在 stderr 报告），因此
相同 synthetic input 的 canonical evidence bytes 可复现：

```text
SYNTHETIC_R4_RAW_EVIDENCE_STATE_SHA256 = 2c3a714571d6a2b6d6064fe14843af61586f14c4fee22bc0384a71b89fc2b17d
evidence_fingerprint                    = 7fa1723d5508f4bf499b467e51366c1dfe54c8f1af148643caf37d5e86750ef5
```

两个独立进程输出 byte-identical。

---

## 6. Verbalizer verification

`verify_verbalizers()` 对每个模型执行一次 synthetic CAT + 一次 synthetic
designated OVR，重新解析 exact token ids，并与 frozen registry 比较：

```text
CAT  : exact single-token continuation, four distinct ids
OVR  : exact single-token yes/no, two distinct ids
```

任何 drift：

```text
STOP / VERBALIZER_IDENTITY_DRIFT
STOP / MEASUREMENT_INTERFACE_DRIFT
```

禁止 leading-space fallback、capitalization fallback、multi-token sum、alternate
verbalizer、generation、monkey-patch。

### 6.1 生产 metadata 形状（本任务发现并修复的 bug）

`src/probvenance/backends/transformers.py:273` 暴露：

```python
"resolved_target_token_ids": [[label, token_id] for label, token_id in resolved]
```

即 **`[label, token_id]` pair 列表**，而不是扁平 id 列表。第一版
`verify_verbalizers` 按扁平列表处理，导致四个真实模型全部抛出：

```text
TypeError: int() argument must be a string, a bytes-like object or a real number, not 'list'
```

unit test 未捕获该 bug，因为 `FakeBackend` 返回的是 hand-built 扁平 metadata。
修复：

1. `verify_verbalizers` 改为 `{str(label): int(token_id) for label, token_id in ...}`；
2. `FakeBackend` 改为返回与生产完全一致的 `[label, token_id]` pair 列表。

---

## 7. Exact call-count rule

`measure_item()` 每个 item 恰好两次 `runtime.evaluate_with_trace`：

```text
CAT decision  -> ChoiceDecision  -> 1 call
OVR decision  -> BoolDecision    -> 1 call
```

无论 anchor index 为 0/1/2/3，call count 恒为 2。

### 7.1 Failure handling

```text
CAT failure  -> OVR still attempted
OVR failure  -> CAT evidence retained
```

两次调用互相独立；downstream paired completeness 仍要求两者均成功。禁止 retry、
fallback verbalizer、row substitution、fresh anchor、fresh candidate。

### 7.2 Non-designated OVR guard

OVR renderer 只接受 `question/context + designated candidate D_i`；regression test
验证 rendered OVR input 不包含其它三个候选描述，且每 item 不存在 3 次额外 OVR
调用。

---

## 8. Synthetic unit tests

`tests/test_r4_measurements.py` = **71 tests**，全部使用 fake/synthetic backend：

```text
CAT probability extraction
OVR probability extraction
fixed D_i
all anchor positions (0/1/2/3)
exactly two calls
failure independence (CAT-first, OVR-second)
non-designated OVR guard
verbalizer id verification
evidence serialization
evidence validation
population registry
legacy-MMLU rejection
N456/N912 row registry
determinism
frozen-authority / amended-candidate consistency
```

运行：

```text
python -m py_compile experiments/calibration_transport/r4_raw_evidence.py \
    experiments/calibration_transport/run_r4_measurements.py \
    tests/test_r4_measurements.py
ruff check (同上三个文件)
pytest -q tests/test_r4_measurements.py
```

全部 PASS。

---

## 9. Real-model synthetic preflight

在 unit tests 与 environment gate 全部 PASS 后执行（**synthetic-only**：不使用任何
frozen study row，不使用任何 MMLU / HellaSwag / MedMCQA 题目）。

```text
python experiments/calibration_transport/run_r4_measurements.py \
    --synthetic-preflight --device cuda:0
```

结果：

| model | class | adapter | CAT ids | yes / no | forwards | status |
|---|---|---|---|---|---|---|
| olmo-3-7b-instruct | `Olmo3ForCausalLM` | transformers_backend | 32/33/34/35 | 9891 / 2201 | 2 | PASS |
| falcon-h1-7b-instruct | `FalconH1ForCausalLM` | transformers_backend | 1068/1069/1070/1071 | 5763 / 3257 | 2 | PASS |
| granite-4-0-h-tiny | `GraniteMoeHybridForCausalLM` | transformers_backend | 32/33/34/35 | 9891 / 2201 | 2 | PASS |
| qwen3-5-9b | `Qwen3_5ForCausalLM` | qwen35_text | 32/33/34/35 | 9405 / 2083 | 2 | PASS |
| minicpm5-2b | — | transformers_backend | — | — | 0 | BLOCKED (`R4ModelCacheMissing`) |
| qwen3-5-2b | — | qwen35_text | — | — | 0 | BLOCKED (`R4ModelCacheMissing`) |

四个 current-generation 模型的 exact revision、model class、tokenizer class、
verbalizer ids 全部与 frozen registry 一致，且 `synthetic_forwards == 2`。

### 9.1 Legacy cache blocker

两个 legacy 模型在本地 HF cache 中 **不存在**：

```text
/root/rivermind-data/hf-cache/hub/models--openbmb--MiniCPM5-2B/snapshots   -> absent
/root/rivermind-data/hf-cache/hub/models--Qwen--Qwen3.5-2B/snapshots       -> absent
```

`/root/rivermind-data/hf-cache/hub` 只有 4 个 snapshot：

```text
models--allenai--Olmo-3-7B-Instruct
models--tiiuae--Falcon-H1-7B-Instruct
models--ibm-granite--granite-4.0-h-tiny
models--Qwen--Qwen3.5-9B
```

本任务禁止下载（§12）且禁止跳过模型后宣称 ready（§43），因此 6-model panel 的
preflight **不能** 全 PASS。这是一个 **operational blocker**，不是科学变更。

---

## 10. Formal outcome firewall

本任务：

```text
NO real R4 CAT probability
NO real R4 OVR probability
NO real model logits on study rows
NO calibration fit
NO Brier / LogLoss
NO transport outcome
NO predictor value / correlation
NO official R4 result
```

synthetic preflight 只报告 engineering facts（revision、class、verbalizer ids、
finite normalized probability、forward count = 2），不保存或讨论概率数值作为科学
结论。

---

## 11. Non-claims

```text
NOT a model-selection decision
NOT a population change
NOT a calibration-family change
NOT an inference change
NOT a predictor change
NOT an execution authorization
```

本文件只描述 engineering implementation。
