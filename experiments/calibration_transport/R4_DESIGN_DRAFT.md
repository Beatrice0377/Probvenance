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
