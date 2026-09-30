# R4 Design Draft — Calibration Transport Generalization Study

```text
STATUS:
DRAFT / NOT FROZEN / NOT EXECUTION-AUTHORIZED
```

```text
本文件是 R4 的设计草案（candidate design），不是 frozen protocol。
它不构成任何 execution authorization。
它不修改、不替代 frozen R3 protocol / design / raw / result。
所有内容必须经过后续 human design review 才能冻结。
```

authority：见 `docs/research/calibration-transport-r3-r4-paper-strategy.md`。冲突时，frozen R3 artifacts 优先。

Epistemic 标记：`[PLANNING DECISION]` / `[PROPOSED R4 DESIGN]` / `[OPEN QUESTION]` / `[REVIEWER SUGGESTION]` / `[R3 RESULT]` / `[FROZEN FACT]`。

---

## 1. Research question [PROPOSED R4 DESIGN]

推荐方向（不冻结措辞）：

```text
Does the deployment delta (R_cross - R_raw) remain measurably
procedure-dependent across broader model families,
model scales, and populations?

And can pre-transport score geometry provide
a preregistered target-label-free warning signal
for the deployment delta and/or the transport penalty
(R_cross - R_native)?
```

具体子问题：

```text
Q1. R3 在 2 × 2B + MMLU 上观察到的 F-conditioned deployment delta dependence
    （cross-vs-raw），在更大模型 / 不同 family / 非 MMLU population 上是否仍可测？

Q2. 三基线（raw / native / cross）的 directional pattern
    是否随 scale / family / population 系统性变化？

Q3. pre-transport、target-label-free 的 score-geometry 信号
    能否预测 deployment delta（R_cross - R_raw）与 transport penalty（R_cross - R_native）？
    两个 estimand 必须分开定义、分开假设、分开解释。
```

---

## 2. What R4 is NOT trying to do [PLANNING DECISION — 硬边界]

```text
R4 is not designed to rescue, strengthen, or overturn the R3 primary result.
R4 addresses independently identified external-validity and generalization questions.

不是：让 R3 更显著
不是：选“更容易复制结果”的模型 / dataset
不是：把 R3 某方向显著就只研究那个方向
不是：建立 universal claim / causal mechanism
不是：把 map-level 证据升级为 procedure-family universal compatibility
不是：新增 anchor-policy / metric / loss / prompt breadth（默认 defer）
```

R4 rationale 在读取 R3 详细结果之前已确定（external review + literature positioning + breadth concern），因此必须 outcome-independent。

---

## 3. Candidate model matrix [PROPOSED R4 DESIGN]

minimum：2 new 7–8B models（不得降回 1）。preferably different families；至少一个 family 不应只是现有 2B family 的简单放大版。

evidence grid：

```text
MMLU      : MiniCPM5-2B (frozen R3) + Qwen3.5-2B (frozen R3) + 2 × new 7–8B
Non-MMLU  : 同一 4 models
```

候选 shortlist（**不 freeze revision**；待 human model-selection gate）：

```text
[OPEN QUESTION] 具体候选清单需下一轮确定。
筛选维度（outcome-independent）：
  fixed revision availability / license / reproducibility /
  tokenizer stability / chat template stability /
  CAT probability extraction correctness / OVR probability extraction correctness /
  enable_thinking 等可控性 / local-offline feasibility /
  7–8B scale / GPU memory feasibility / family diversity / community relevance /
  not selected based on calibration outcome
```

原则：

```text
优先 2B family A + 2B family B + 7–8B family C + 7–8B family D
而非 2B + 2B + 70B
不因“更大模型”直接跳 70B（本研究主要不是 scale law）
```

### Current human planning decision — 2026-09-30 [PLANNING DECISION]

```text
CURRENT HUMAN PLANNING DECISION:

current-generation panel target:
- allenai/Olmo-3-7B-Instruct
- tiiuae/Falcon-H1-7B-Instruct
- ibm-granite/granite-4.0-h-tiny
- Qwen/Qwen3.5-9B

Qwen3.5-9B role:
same-lineage scale continuity with R3 Qwen/Qwen3.5-2B
(a 2B -> 9B scale-continuity bridge, NOT a family-diversity candidate).

If the Qwen3.5-9B Phase 2D engineering probe passes,
all four current-generation candidates are intended
to remain in the R4 model panel
(no automatic down-selection to two).

This decision was made BEFORE any formal R4 target outcome.
It is a planning decision, NOT the final R4 freeze.
```

历史 rationale 保留：上文 "minimum 2 new 7–8B" 与 family-diversity 原则仍是历史设计记录；
human 已在其之上把 current-generation panel 扩为四个候选，并让 Qwen3.5-9B 承担 2B→9B scale continuity。
panel 内最终 scientific 角色仍需后续 formal design freeze gate。

---

## 4. Candidate population matrix [PROPOSED R4 DESIGN]

minimum：>= 1 truly non-MMLU population（不得删除）。

```text
retain MMLU (cais/mmlu @ c30699e8356da336a370243923dbaf21066bb9fe) 作为 R3 continuity
+ >= 1 non-MMLU multiple-choice / declared-answer population
```

minimum vs recommended target：

```text
hard minimum        : >= 1 truly non-MMLU population
recommended target  : 2 non-MMLU populations
                      if predictor validation is intended
                      as a major paper contribution
```

若最终只能实现 1 个 non-MMLU：model / population generalization 仍有价值，
但 predictor contribution 应降级为 secondary / exploratory predictive evidence，
而不是 headline validated predictor。

非 MMLU 候选筛选（outcome-independent）：

```text
multiple-choice / clearly declared answer event
stable public revision
licensing
enough items
enough subgroup / domain structure for paired or stratified resampling
deterministic ground truth
compatible with CAT / OVR measurement
contamination risk can be acknowledged
not selected based on observed transport outcome
```

[OPEN QUESTION] 具体非 MMLU dataset 待 dataset-selection gate。

### Current human planning decision — 2026-09-30 [PLANNING DECISION]

```text
CURRENT HUMAN PLANNING DECISION:

intended population panel:
1. MMLU      (R3 continuity population)
2. HellaSwag (non-MMLU / commonsense event-completion population)
3. MedMCQA   (non-MMLU / medical-domain population)

No plan to add ARC / OpenBookQA / CommonsenseQA / SciQ
unless dataset semantic closure exposes a substantive blocker.
```

仍未 freeze：exact dataset revisions / fixed-event semantics / strata /
TRAIN-TEST construction / population manifests 全部待 dataset semantic closure。
本 planning decision 不生成任何 manifest，也不下载或运行任何 dataset。

### 2026-09-30 Population construction decision — dataset source pins / strata / budgets [PLANNING DECISION]

```text
DATASET SOURCE PIN（source identity freeze；不是 FULL R4 FREEZE）：

HellaSwag   Rowan/hellaswag            @ 218ec52e09a7e7462a5400043bb9a69a41d06b76
MedMCQA     openlifescienceai/medmcqa  @ 91c6572c454088bf71b679ad90aa8dffcd0d5868

HellaSwag
  calibration TRAIN source : train
  evaluation  TEST  source : validation
  primary population       : FULL LABELED VALIDATION（不只保留 indomain）
  primary stratum metadata : activity_label
  source cluster identity  : source_id（MUST BE PRESERVED；后续 inferential / bootstrap
                             设计 MUST BE GROUP-AWARE；exact bootstrap algorithm 暂不冻结）
  split_type               : SECONDARY SUBGROUP DIAGNOSTIC only（indomain / zeroshot）
                             NOT primary strata，NOT independent population
                             不得根据 outcome 改变 subgroup role

MedMCQA
  calibration TRAIN source : train
  evaluation  TEST  source : validation
  primary strata           : subject_name
  topic_name               : REJECTED as cross-split strata
  choice_type              : KEEP ALL（single 与 multi 都保留）
                             条件：exactly four structurally distinct candidate option
                             strings + one unique ground-truth index
  duplicate-option items   : STRUCTURALLY INELIGIBLE
                             exclusion 只看 candidate strings，不读 cop / correctness /
                             model output / score

CALIBRATION TRAIN N = 456（两个新 population 相同）
  理由：match frozen R3 calibration fitting budget，避免同时改变 population 与
        calibration data volume；456 由所有 calibration families 共享
        （P-low / P-historical / L-low / L-historical / isotonic / beta），
        isotonic / beta 不得单独获得更多 TRAIN data

EVALUATION TEST = all eligible labeled validation rows（不因算力截断）
  HellaSwag : all eligible labeled validation rows
  MedMCQA   : all eligible labeled validation rows，先做 duplicate-option structural exclusion
  禁止 subsample to 1140 / 2000

R3-style overlap guard 保留：TEST 先声明且 pristine；TRAIN candidate 若与 TEST item
exact question + exact ordered candidate strings 重复则排除并顺延；若 same event 但
ground truth 冲突则 STOP FOR HUMAN REVIEW，不得 silent dedup。

anchor protocol：见 §5。
```

本 decision 先于任何 R4 model outcome。R4 仍为 DRAFT / NOT FROZEN / NOT EXECUTION-AUTHORIZED。

---

## 5. Fixed-event measurement semantics [PLANNING DECISION]

必须保持 R3 的 fixed-event construction：

```text
D_i 在 measurement 之前由外部冻结
Y_i = 1[D_i correct]
CAT 与 OVR 都测同一个外部声明事件 D_i
```

对新 population 同样必须能自然定义：

```text
externally frozen decision D_i
ground truth GT_i
Y_i = 1[D_i = GT_i]
```

且 CAT / OVR 都能测 `P(D_i correct)`。不能为了 dataset 强行改变 target semantics。

[OPEN QUESTION] 新 population 上 D_i 的具体构造（candidate-anchor 语义如何移植）待 design review。

### 2026-09-30 Fixed-event construction decision for the new populations [PLANNING DECISION]

```text
HellaSwag
  question                : ctx
  candidate names         : option-0 / option-1 / option-2 / option-3
  candidate descriptions  : endings[0] / endings[1] / endings[2] / endings[3]
  ground truth            : label

MedMCQA
  question                : question
  candidate names         : option-0 / option-1 / option-2 / option-3
  candidate descriptions  : opa / opb / opc / opd
  ground truth            : cop

source order 不得改变（no permutation）。

PLANNED R4 FIXED-EVENT ANCHOR PROTOCOL
  ANCHOR_PROTOCOL_ID      = r4-fixed-event-anchor-deterministic-source-index-hash
  ANCHOR_PROTOCOL_VERSION = 1
  anchor_index            = int(fingerprint({
                              protocol_id, protocol_version,
                              dataset_id, dataset_revision,
                              source_split, source_row_index})[:16], 16) % 4

anchor 输入禁止包含：
  ground truth / label / cop / question text / candidate text /
  model output / CAT score / OVR score
```

状态：PLANNED protocol，用于 population candidate construction；
在 final R4 protocol freeze 前仍需 manifest fingerprint closure。
不得写 R4 EXECUTION AUTHORIZED。

---

## 6. Candidate F panel [PROPOSED R4 DESIGN]

retain R3 continuity：

```text
P-low / P-historical / L-low / L-historical
（logistic calibration × feature geometry × regularization）
```

认真评估加入：

```text
isotonic calibration（non-parametric family）
beta calibration（distinct parametric family）
```

**DESIGN CANDIDATE ONLY。** freeze 前必须明确：

```text
family definition / parameterization / objective / regularization /
hyperparameter selection / endpoint behavior / out-of-support behavior /
ties / fitting protocol / selection rule / failure rule
```

F identity 完整定义：

```text
F includes: family / transform / objective / regularization / hyperparameter rule /
            endpoint treatment / fitting-data protocol / selection rule
solver / precision / device / library 属于 provenance，不是 scientific F，
除非其变化会改变算法定义。
```

不得把“isotonic 没有 λ”当成 F 不完整，也不得强行构造假的 2×2 factorial。

[OPEN QUESTION] isotonic / beta 的 endpoint 与 out-of-support 行为定义，及 failure rule。

### Current human planning decision — 2026-09-30 [PLANNING DECISION]

```text
PLANNED FAMILY PANEL:

continuity core (retained from R3):
  P-low / P-historical / L-low / L-historical
  (logistic calibration x feature geometry x regularization)

family extension (human-selected planned families):
  isotonic calibration (non-parametric monotone family)
  beta calibration     (distinct parametric calibration family)
```

R3 logistic factorial 仍为 continuity confirmatory core；
isotonic / beta 为 predeclared family-extension hypotheses，不构造假的统一 factorial。

full semantic specification pending（见上文 [OPEN QUESTION]）：
isotonic / beta 目前是 HUMAN-SELECTED PLANNED FAMILIES，
但尚不是 FULLY SPECIFIED / FROZEN F。

---

## 7. Candidate inferential architectures [PROPOSED R4 DESIGN]

## Candidate A

```text
保持 R3 factorial panel 作为 continuity confirmatory core
isotonic / beta 作为独立 preregistered family-extension hypotheses
```

## Candidate B

```text
重新定义更 general 的 F heterogeneity estimand 用于跨 family panel
R3 factorial contrasts 保留作 continuity secondary
```

比较维度（不 freeze）：

```text
interpretability / multiplicity burden / continuity with R3 / risk of post-hoc flexibility
```

反 HARKing：不得因 R3 某 contrast 显著而只保留该 contrast / 该方向。

---

## 8. Candidate support predictor [PROPOSED R4 DESIGN]

高优先 candidate；只能 predictive diagnostic，不得 causal。

target-label-free 约束：

```text
"target-label-free" means that predictor construction and application
require no target outcome labels.

允许：source TRAIN scores / source TRAIN labels（仅通过 source calibrator fitting 等
      source-side procedure 使用）/ target unlabeled score distribution /
      fitted source calibrator geometry

禁止：target Y / target correctness labels / target Brier / target LogLoss /
      任何由 target outcome label 派生的 feature
```

候选 metrics（下一轮 predeclare 1 primary + small secondary set）：

```text
fraction target outside source min/max
fraction target outside source q2.5/q97.5
1D Wasserstein distance
CDF / KS-style discrepancy
```

outcome 必须区分：

```text
transport penalty  : R_cross - R_native
deployment delta   : R_cross - R_raw
```

避免 pseudo-replication：以 `model × population × direction` 为 grouped unit；F-specific predictor 必须 group-aware。

两个 architectures：

```text
Architecture 1: support mismatch -> mean/max predeclared transport penalty across F
Architecture 2: support mismatch + fitted map sensitivity/extrapolation -> F-specific transport penalty
```

[OPEN QUESTION] primary predictor 的选择与 group-aware inference 方案。

### Current human planning decision — 2026-09-30 [PLANNING DECISION]

```text
PRIMARY planned predictor:
  fraction of target scores outside
  source TRAIN q2.5 / q97.5 interval
  (q2.5-q97.5 support-exceedance fraction)

SECONDARY planned diagnostic:
  1D Wasserstein distance between
  the source-TRAIN score distribution
  and the target score distribution
```

约束不变：target-label-free；grouped unit = model × population × direction；
F-specific predictor 必须 group-aware；不得使用任何 R4 target outcome 调参。
R3 model × MMLU × direction cells 仍仅为 development / hypothesis-generation evidence。

### Predictor development / validation isolation [PLANNING DECISION — 硬边界]

```text
R3 model × MMLU × direction cells
are development / hypothesis-generation evidence only
for the future predictor.

They must not be counted as independent confirmatory
validation units for R4 predictor performance.

Only R4 target outcomes generated after the formal predictor
specification is frozen may enter preregistered predictor validation.

No predictor metric, feature set, threshold, coefficient,
aggregation rule, or selection rule
may be tuned using R4 target outcomes.
All such choices must be frozen before target-outcome inspection.
```

---

## 9. Calibration train/test protocol [PROPOSED R4 DESIGN]

保持 R3 的 subject-stratified paired 结构：

```text
TRAIN 用于 fitting；TEST 用于 evaluation；两者 disjoint。
bootstrap 单位 = within-subject resample（TEST paired；TRAIN-refit 按 frozen 规则）。
```

新 population 必须提前规划：

```text
足够 calibration TRAIN sample size
明确 strata
明确 refit stability
isotonic 需要足够样本支撑 stepwise fit
```

不能到正式执行才发现训练集过小。

[OPEN QUESTION] 新 population 的 TRAIN/TEST 划分比例与 strata 定义。

### 2026-09-30 Calibration train/test budget decision for the new populations [PLANNING DECISION]

```text
CALIBRATION TRAIN N = 456   （HellaSwag 与 MedMCQA 相同）

  rationale: match frozen R3 calibration fitting budget
             避免同时改变 population 与 calibration data volume
  456 由所有 calibration families 共享：
     P-low / P-historical / L-low / L-historical / isotonic / beta
  isotonic / beta 不得获得更多 TRAIN data

EVALUATION TEST = all structurally eligible labeled validation rows
  HellaSwag : all eligible labeled validation rows
  MedMCQA   : all eligible labeled validation rows（先做 duplicate-option structural exclusion）
  不做 subsample to 1140 / 2000；不做 compute-driven truncation
  目的：在固定 calibration fitting budget 的前提下最大化 evaluation precision

predictor validation unit 保持不变：model × population × direction
  HellaSwag split_type subgroup 不是独立 predictor validation unit
  MedMCQA subject_name 也不是独立 predictor unit

HellaSwag TRAIN 额外约束：at most one selected row per source_id
  （rank 遇到已选 source_id 时 skip 并取下一个 ranked row；quota 无法满足则
   STOP / NEEDS_REVIEW，不得跨 strata 偷补）
```

本 decision 先于任何 R4 model outcome。

---

## 10. Multiplicity options [PROPOSED R4 DESIGN]

必须 predeclare，不得后调。

候选：

```text
Option 1: 沿用 R3 风格 Bonferroni-percentile-interval，family size 按最终 hypothesis 数冻结
Option 2: 分层 multiplicity（continuity core 与 family-extension 各自独立 family）
```

[OPEN QUESTION] 与 §7 architecture 的耦合；final family size 取决于 freeze 时 hypothesis 集合。

---

## 11. Confirmatory structure（primary / replication 治理原则）[PLANNING DECISION]

R4 inherits the governance principles of primary-vs-replication separation：

```text
- no rescue
- no selective reporting
- no post-hoc pooling
- no outcome-driven reassignment
```

```text
primary conclusion 由 primary model frozen rule 决定
replication 单独描述，不 rescue、不 pooling、不 post-hoc meta-analysis、不选模型汇报
```

However, the exact R4 confirmatory structure
（single primary model vs multi-condition confirmatory family）
remains an OPEN QUESTION and is not frozen here。

R4 的研究问题更偏 cross-model / cross-family / cross-population generalization，
最终可能更适合 predeclared multi-condition confirmatory family。

[OPEN QUESTION] R4 的 primary model 身份（是否仍是 MiniCPM5-2B，或新增 7–8B 作为 primary）
与 overall confirmatory structure 待 design review。

---

## 12. Deterministic execution requirements [PLANNING DECISION]

```text
replicate index 唯一确定 bootstrap draw
worker count 不改变 scientific result
aggregation order fixed
single-worker 与 multi-worker numerically equivalent（或按声明契约 byte-equivalent）
failure semantics identical
不得在正式 R4 运行中途临时换并行方案
```

---

## 13. GPU / CPU execution plan [PLANNING DECISION]

```text
GPU: 正式 7–8B 可用租赁 4090 / 5090 / 80GB GPU；硬件不是 scientific contribution。
CPU: 将 bootstrap / refit 从单核优化为 deterministic multi-process CPU parallelism，
     必须在 freeze 前完成并验证 equivalence。
```

---

## 14. Pre-freeze engineering tests [PROPOSED R4 DESIGN]

```text
新模型 adapter correctness（CAT / OVR probability extraction）
新 dataset population integrity（D_i / GT_i / Y_i / counts / strata）
新 calibration family oracle tests（isotonic / beta 语义与 endpoint）
deterministic parallel implementation correctness（single vs multi worker equivalence）
new provenance necessary for reproducibility
```

除以上，不继续增加 audit-of-audit-of-audit 文档。

---

## 15. Contamination / external-validity limitations [PLANNING DECISION]

```text
public benchmark contamination cannot be excluded
加入非 MMLU 可降低单一 benchmark 依赖，但不能自动声称彻底排除 contamination
fixed random anchor 是 experimental measurement design，不是 deployment decision policy
```

---

## 16. Explicit non-goals [PLANNING DECISION]

```text
不新增 anchor-policy factorial（默认 defer）
不扩大 metric（ECE / ACE / NLL variants 默认不扩）
不扩大 measurement axis（不新增 verbalized confidence / self-consistency /
                          sampling confidence / temperature prompting）
不新增 prompt/doctrine breadth
不建立 causal mechanism
不建立 universal claim
不为“让 R3 更显著”而设计
不根据 R3 outcome 选择模型 / dataset / contrast / direction
```

---

## 17. Unresolved design decisions [OPEN QUESTION]

```text
U1. 两个 7–8B 的具体模型与 revision
U2. 非 MMLU population 的具体 dataset 与 revision
U3. 新 population 上 D_i 的构造与 CAT/OVR 语义移植
U4. isotonic / beta 的完整 F 定义与 failure rule
U5. §7 inferential architecture（A vs B）
U6. §8 primary predictor 选择与 group-aware inference
U7. §10 multiplicity 方案与 family size
U8. §11 R4 primary model 身份
U9. §9 新 population 的 TRAIN/TEST 划分与 strata
U10. deterministic parallel 的具体实现契约（numerical vs byte equivalence）
```

---

## 18. Freeze checklist [PLANNING DECISION]

R4 可进入 freeze 前必须全部满足（selection / closure before freeze）：

```text
[ ] human design review 完成
[ ] §17 所有 unresolved decision 关闭
[ ] model-selection gate 通过（outcome-independent 记录）
[ ] dataset-selection gate 通过（outcome-independent 记录）
[ ] fixed-event semantics 在新 population 上验证
[ ] calibration-family 语义 / oracle closure 完成（R3 P/L continuity / isotonic / beta）
[ ] inferential architecture 冻结
[ ] target-label-free predictor specification 冻结
[ ] multiplicity / hypothesis 集合冻结
[ ] confirmatory structure 冻结（primary/replication 或 multi-condition）
[ ] deterministic parallel 等价性验证完成
[ ] pre-freeze engineering tests 通过
[ ] provenance 契约（含 analysis code commit）定义
[ ] contamination limitation 明确写入
[ ] non-goals 明确写入
```

**Gate-order rule：** model-selection / dataset-selection / fixed-event semantics /
calibration-family / inference / predictor / multiplicity / execution semantics
都必须在最终 freeze 之前关闭。不得出现「模型还没选，R4 已经 freeze」。

**Analysis-freeze rule：**

```text
R4 的 outcome-dependent analysis definitions 与正式 analysis implementation
必须在查看正式 R4 target outcomes 之前冻结。
```

在 freeze checklist 全部完成前：

```text
R4 STATUS = DRAFT / NOT FROZEN / NOT EXECUTION-AUTHORIZED
```

---

## 19. 2026-09-30 Population construction planning decision（consolidated）[PLANNING DECISION]

本节汇总 human 在 dataset semantic closure 之后、任何 R4 model outcome 之前做出的
population construction planning decisions。逐条对应 §4 / §5 / §9 中的 dated block。

```text
D1  dataset source pins
      HellaSwag  Rowan/hellaswag            @ 218ec52e09a7e7462a5400043bb9a69a41d06b76
      MedMCQA    openlifescienceai/medmcqa  @ 91c6572c454088bf71b679ad90aa8dffcd0d5868
    status: R4 DATASET SOURCE PIN（source identity freeze；不是 FULL R4 FREEZE）

D2  calibration TRAIN budget N = 456（两个新 population），match frozen R3 fitting budget

D3  evaluation TEST = all eligible labeled validation rows（不做算力截断）

D4  HellaSwag primary stratum metadata = activity_label

D5  HellaSwag source cluster identity = source_id（保留；后续 inference group-aware）

D6  HellaSwag split_type = secondary subgroup diagnostic（indomain / zeroshot），
    不是 primary strata，不是 independent population

D7  MedMCQA primary strata = subject_name

D8  MedMCQA topic_name rejected as cross-split strata

D9  MedMCQA choice_type = KEEP ALL（single 与 multi 均保留）

D10 MedMCQA duplicate-option rows structurally excluded（TRAIN pool 与 TEST population 都排除）

D11 R3-style overlap guard 保留（TEST pristine；TRAIN 排除 exact TEST duplicate；
    conflicting ground truth => STOP FOR HUMAN REVIEW）

D12 anchor protocol v1
      ANCHOR_PROTOCOL_ID      = r4-fixed-event-anchor-deterministic-source-index-hash
      ANCHOR_PROTOCOL_VERSION = 1
```

状态语言（不得升级）：

```text
DATASET SOURCE / POPULATION CONSTRUCTION PLANNING DECISION
R4 STATUS = DRAFT / NOT FROZEN / NOT EXECUTION-AUTHORIZED
```

```text
decision made before any R4 model outcome
本 decision 不产生任何 R4 outcome、不产生任何 scientific selection、
不构成 R4 freeze、不构成 R4 execution authorization。
```

---

## 20. 2026-09-30 Calibration-sample-size robustness decision（nested 912）[PLANNING DECISION]

本节记录 human 在 Gate C primary population candidate 之后、任何 R4 model outcome 之前
做出的 calibration-sample-size robustness planning decision。

```text
E1  PRIMARY CALIBRATION TRAIN BUDGET = 456
    保持不变，且为唯一 primary、R3-continuity fitting budget。
    禁止 resample / 改 quota / 改 rank / 改 selected rows / 改 anchor balance。

E2  HellaSwag quota-zero strata ACCEPTED
    Home,Categories / Knitting / Spread mulch / Windsurfing 配额为 0，接受。
    不强制 minimum-one allocation：
    primary TRAIN 目标是 proportional / row-weighted source-train population sampling，
    强制 minimum-one 会不成比例地过采样极小的 activity strata。

E3  14 个 validation-only activity labels RETAINED IN PRIMARY TEST
    准确语义：14 个 validation-only activity labels 在 source train split 中不存在，
    它们是 target-only semantic strata，
    不是 "train strata with zero eligible rows"。
    train unique = 178 / validation unique = 192 / shared = 178 /
    validation-only = 14 / train-only = 0。
    不得为了让 TRAIN/TEST strata 完全相同而删除。

E4  HellaSwag primary TEST = FULL eligible validation（indomain + zeroshot）保持。
    split_type = SECONDARY PREDECLARED SUBGROUP DIAGNOSTIC，
    不是 primary strata，不是 independent population。

E5  HellaSwag source_id = cluster/group identity 保持。
    primary TRAIN at most one selected row per source_id；
    未来 TEST inference must be group-aware by source_id
    （本任务不冻结具体 bootstrap implementation）。

E6  NO ANCHOR-BALANCE OPTIMIZATION
    不得因 anchor==GT 的观测值（例如 MedMCQA TRAIN ≈ 0.188596）
    而 resample / rebalance / 改 hash / 改 anchor protocol / 改 row selection。
    理由：selection 与 anchor 均在未读取 ground truth 的前提下冻结；
    事后平衡会引入 ground-truth-conditioned selection。

E7  SECONDARY NESTED CALIBRATION-SAMPLE-SIZE ROBUSTNESS TRAIN N = 912
    角色：SECONDARY ROBUSTNESS ONLY。
    不是 primary，不是 rescue analysis，不是 N=456 的替代。

E8  NESTEDNESS hard requirement
    TRAIN_456 ⊂ TRAIN_912（exact item-id subset）。
    禁止独立重采样 912；禁止修改 primary 456。
    additional rows = 456；456 primary + 456 extension = 912 total。
    extension 来自 same pinned revision / same source TRAIN split /
    same structural eligibility rules，并排除全部 primary-456 selected rows。
    HellaSwag 继续 at most one row per source_id（across the entire 912）。
    allocation 使用 nested residual extension：
    primary 456 冻结 → 对剩余 eligible pool 的 strata counts 做
    Hamilton / largest-remainder → 分配 additional 456 → within stratum 相同 rank doctrine → append。

E9  ROBUSTNESS TEST = SAME PRIMARY TEST
    HellaSwag TEST = same 10042 rows；MedMCQA TEST = same 4162 rows。
    禁止另建 robustness TEST。
    唯一改变的主要因素 = calibration TRAIN sample size。

E10 Governance
    N=456 remains the sole primary R3-continuity fitting budget。
    N=912 cannot rescue, override, or redefine the primary conclusion。
    用途：assess calibration-sample-size sensitivity，
    尤其是 higher-variance calibration families（如 isotonic）。
    禁止在看过 calibration outcome 之后才决定是否报告 912。
```

状态语言（不得升级）：

```text
CALIBRATION-SAMPLE-SIZE ROBUSTNESS PLANNING DECISION
R4 STATUS = DRAFT / NOT FROZEN / NOT EXECUTION-AUTHORIZED
```

```text
decision made before any R4 model outcome
本 decision 不产生任何 R4 outcome、不产生任何 scientific selection、
不构成 R4 freeze、不构成 R4 execution authorization。
```

---

## 21. 2026-09-30 R4 population layer freeze [FREEZE NOTICE]

The R4 population layer is now frozen.

frozen scope：

```text
dataset source identity
population construction protocol
primary TRAIN 456 identities
secondary nested TRAIN 912 identities
fixed-event population-layer anchor protocol
```

仍 open：

```text
calibration-family semantics
predictor inferential specification
multiplicity
formal execution protocol
```

因此：

```text
R4 POPULATION LAYER : FROZEN
R4 OVERALL          : NOT FULLY FROZEN
R4 EXECUTION        : NOT AUTHORIZED
R4 STATUS           = DRAFT / NOT FULLY FROZEN / NOT EXECUTION-AUTHORIZED
```

冻结身份记录见 `experiments/calibration_transport/R4_POPULATION_FREEZE.md`。
本 notice 只冻结 population layer，不构成 calibration-family 语义冻结、
不构成 predictor inference 规范冻结、不构成 R4 execution authorization。
