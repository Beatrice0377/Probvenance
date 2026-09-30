# Calibration Transport — R3→R4→Paper 总路线锚点

```text
STATUS: PLANNING AUTHORITY (路线锚点)

本文件是后续数轮工作的路线锚点。

它不替代、不覆盖、不修改任何 frozen R3 protocol / design / code / raw / result artifact。
它不构成对 R3 结果的科学解释权（解释权仍属人工）。
它不构成 R4 的设计冻结（R4 仍是 DRAFT / NOT FROZEN）。
```

## 本文件 authority hierarchy（冲突时按优先级）

```text
1. 已冻结并提交的 R3 protocol / design / code / raw / result artifacts
2. 已冻结的 R2 research conclusions and limitations
3. 本任务中人工明确写出的 review 结论与路线决策
4. 外部 reviewer 意见
5. literature
6. 本 agent 的推断
```

不得：用 reviewer 建议覆盖 frozen protocol；用 literature 重新解释 R3 设计；用 R3 结果反向改变 preregistered hypothesis；用直觉改写人工已接受/拒绝的路线。

## Epistemic status 标记约定

本文所有重要 statement 标注其认识论地位：

```text
[FROZEN FACT]          已冻结并提交的事实 / identity
[R3 RESULT]            从 frozen official R3 analysis artifact 读取的数值
[PLANNING DECISION]    人工已明确决定的路线
[REVIEWER SUGGESTION]  外部 reviewer 建议（尚未成为决定）
[LITERATURE FACT]      已独立核实或人工确认的文献事实
[PROPOSED R4 DESIGN]   R4 候选设计（未冻结）
[OPEN QUESTION]        尚未解决的设计问题
```

---

# A. Current scientific thesis [FROZEN FACT]

核心 thesis：

```text
A fitted calibration map is an empirical artifact tied to
a declared probability measurement and fitting population,
not an intrinsic property of a model.

Reusing it across measurement protocols is a directional,
population- and metric-dependent compatibility claim
that requires independent evidence.
```

中文：

```text
拟合出来的 calibration map 不是“模型本身固有的校准属性”。
它依赖 measurement、population、target event、loss、evaluation、fitting procedure F。

把一个 measurement 下拟合的 map 搬到另一个 measurement，
不是天然合法操作，
而是一个需要独立验证的 directional compatibility claim。
```

项目简写原则：

```text
Identity != compatibility
```

兼容性必须显式条件化：

```text
A --[M,P,T,L,E,F; ε]--> B
```

其中 M = measurement；P = population；T = target/event；L = loss；E = evaluation；F = calibration fitting procedure。

**本 thesis 明确不是：**

```text
“CAT 和 OVR 哪个更好”
“哪个 calibration method 最好”
“某个模型校准差”
```

核心问题始终是：

```text
calibration map transportability
under a fixed declared event,
and how that transportability depends on measurement
and calibration procedure.
```

---

# B. Frozen R3 identity [FROZEN FACT]

```text
execution code HEAD        = 0c16ca2460de8b18433a9c677b3e6989b0736f9f
official result commit     = c68c7e3ac725de1bc5db369cb7c951a810ed80f9
original receipt commit    = a069882b0bef39f347ae26032428a731be9c5970
receipt erratum commit     = b055890a402ccfc9c717fc3c780bbbbfca0f6742
```

official analysis artifact：

```text
experiments/calibration_transport/results/r3-confirmatory-analysis-v1.json
SHA256 = 27b945097a0b6156998a47112437c3b258037db2c9888cea20e97b52075be796
```

execution sidecar：

```text
experiments/calibration_transport/results/r3-confirmatory-analysis-execution-v1.json
SHA256 = 9992ceefba32f4d0f55e692a0c60472a05751bdca316993ed3f98e220b0f6deb
execution fingerprint = e738be013fd0f98a6b0ae635e09420e65de9c91b3b819aa11c1ff7ed2901f479
```

frozen scientific identity（继承自 R3 protocol / design）：

```text
protocol fingerprint          = 3ef63056ae16b18ad65d9c87d1fbec5b43550873a0e3e25ec0a323f954ee974d
population manifest fingerprint = 40cc9753a711314ff3b25ed6e234d0cbda11f3f60cd87f1d3915195a3d1780b8
measurement code commit       = 8b1ea40aee0e7518c2ab3b25a8cc6d4ec2d0f800
historical analysis code commit = 3a929a6931762a518498ad9df2e5f82cf6e6deed
raw evidence commit           = ba90a6c325b764347feaa5ba9cc5b8956d36cb21
primary model                 = openbmb/MiniCPM5-2B @ 12a3808a956f869c767195e9266b59c4d21d92e2
replication model             = Qwen/Qwen3.5-2B @ 15852e8c16360a2fea060d615a32b45270f8a8fc
population                    = cais/mmlu @ c30699e8356da336a370243923dbaf21066bb9fe
                              TRAIN 456 (8/subject) / TEST 1140 (20/subject) / AUDIT 0 / 57 subjects
```

## R3 execution attempt history [FROZEN FACT — 已关闭，不重新争论]

```text
attempt 1: 初始人工授权执行；externally terminated before artifact
attempt 2: pre-launch 人工授权 operational retry；externally terminated by Windows host reboot before artifact
attempt 3: operator initiated outside prior two-attempt contract；human continuation accepted after launch；completed exit 0

execution_attempt_count = 3
automatic_retry_count   = 0
```

attempt 1 / 2 的准确表述：

```text
没有 persisted / observable official statistical outcome
```

禁止声称“没有发生任何瞬时 computation”。

```text
result-driven retry = false
scientific validity impact = none identified
```

R3 不重新运行。

---

# C. Frozen R3 result summary [R3 RESULT]

数据来源：`r3-confirmatory-analysis-v1.json`（只读取、只复制，未做任何新统计）。

## C.1 Primary — MiniCPM5-2B（6 hypotheses：2 directions × 3 contrasts）

bootstrap = 20,000 subject-stratified paired；Bonferroni m=6，tails 1/240 / 239/240。

```text
CAT -> OVR
  FeatureEffect        point = +0.002390   interval [-0.00112614, +0.00606332]   excludes_zero = FALSE
  RegularizationEffect point = +0.002261   interval [+0.000453733, +0.00406603]  excludes_zero = TRUE
  Interaction          point = -0.003538   interval [-0.00703197, -0.00000529252] excludes_zero = TRUE

OVR -> CAT
  FeatureEffect        point = -0.005156   interval [-0.00935223, -0.000876384]  excludes_zero = TRUE
  RegularizationEffect point = +0.003837   interval [-0.000480188, +0.00835815]  excludes_zero = FALSE
  Interaction          point = -0.008056   interval [-0.0172034, +0.00065091]    excludes_zero = FALSE
```

**exclude-zero pattern：3 / 6 exclude zero。**

```text
CAT->OVR: feature(F) / regularization(T) / interaction(T)
OVR->CAT: feature(T) / regularization(F) / interaction(F)
```

## C.2 Exact frozen-rule primary conclusion [R3 RESULT]

frozen decision rule（§7）：

```text
如果 >=1 adjusted interval excludes zero：
  允许：“confirmatory evidence that cross-vs-raw calibration risk
         depends on the predeclared F panel in the primary condition”
如果全部包含 0：
  允许：“did not detect dependence at the predeclared resolution”
```

应用结果：

```text
3 / 6 excludes zero  ->  >= 1  ->  走第一条分支
```

因此**唯一允许的 primary conclusion 是**：

```text
“confirmatory evidence that cross-vs-raw calibration risk
 depends on the predeclared F panel in the primary condition”
```

不得升级为：

```text
“某个具体 F 才是真正机制”
“interaction 是核心”
“某方向普遍成立”
```

（具体哪个 contrast 显著可以描述，但不能改写 hypothesis。）

---

# D. Qwen replication result [R3 RESULT]

角色：preregistered replication（不是 primary rescue）。

```text
CAT -> OVR
  FeatureEffect        interval [+0.00256751, +0.00856459]  excludes_zero = TRUE
  RegularizationEffect interval [+0.00365161, +0.0137069]   excludes_zero = TRUE
  Interaction          interval [-0.024748, -0.00640195]    excludes_zero = TRUE

OVR -> CAT
  FeatureEffect        interval [-0.0076031, +0.000388453]  excludes_zero = FALSE
  RegularizationEffect interval [-0.00562943, +0.00266056]  excludes_zero = FALSE
  Interaction          interval [+0.00079491, +0.0148054]   excludes_zero = TRUE
```

**exclude-zero pattern：4 / 6 exclude zero。**

```text
CAT->OVR: feature(T) / regularization(T) / interaction(T)
OVR->CAT: feature(F) / regularization(F) / interaction(T)
```

no-rescue statement：

```text
replication evidence != primary rescue
```

禁止：Qwen rescue MiniCPM；MiniCPM 不显著但 Qwen 显著 → 宣称 primary confirmed；把两模型 pooling；post-hoc meta-analysis；选模型汇报。

primary conclusion 只由 MiniCPM frozen primary rule 决定；Qwen 单独描述 replication pattern。

---

# E. Native-reference summary [R3 RESULT]

每模型 2 measurements × 4 F = 8 cells；Bonferroni m=8，tails 1/320 / 319/320。

状态只能取：`NATIVE_IMPROVEMENT_SUPPORTED` / `NATIVE_DEGRADATION_SUPPORTED` / `NATIVE_ADEQUACY_UNRESOLVED`。

## MiniCPM5-2B

```text
CAT: P-low IMPROVEMENT | P-historical IMPROVEMENT | L-low IMPROVEMENT | L-historical IMPROVEMENT
OVR: P-low IMPROVEMENT | P-historical IMPROVEMENT | L-low IMPROVEMENT | L-historical IMPROVEMENT
```

（8/8 = NATIVE_IMPROVEMENT_SUPPORTED；即 native 相对 raw 的风险差 interval 全部落在负侧、排除零。）

## Qwen3.5-2B

```text
CAT: P-low UNRESOLVED | P-historical DEGRADATION | L-low UNRESOLVED | L-historical UNRESOLVED
OVR: P-low IMPROVEMENT | P-historical IMPROVEMENT | L-low IMPROVEMENT | L-historical IMPROVEMENT
```

计数：IMPROVEMENT = 4，DEGRADATION = 1，UNRESOLVED = 3。

禁止把这些状态改写成 `significant` / `non-significant` / `good calibrator` / `bad calibrator`。

---

# F. TRAIN-refit completeness [R3 RESULT]

frozen：2,000 subject-stratified TRAIN bootstrap replicates；任何 solver/refit failure → 受影响 procedure/model block = INCOMPLETE；不得只对成功 subset 算 CI。

## MiniCPM5-2B

```text
P-low         INCOMPLETE   successful 1996 / 2000   failed 4
P-historical  COMPLETE     successful 2000 / 2000   failed 0
L-low         INCOMPLETE   successful 1985 / 2000   failed 15
L-historical  COMPLETE     successful 2000 / 2000   failed 0
```

## Qwen3.5-2B

```text
P-low         COMPLETE     successful 2000 / 2000   failed 0
P-historical  COMPLETE     successful 2000 / 2000   failed 0
L-low         INCOMPLETE   successful 1994 / 2000   failed 6
L-historical  COMPLETE     successful 2000 / 2000   failed 0
```

结论：稳定性诊断必须按 block 分别报告 COMPLETE / INCOMPLETE；INCOMPLETE block 的 interval 不作为可用证据。

---

# G. Secondary diagnostic status [R3 RESULT — 只能 descriptive]

以下均为 `secondary / descriptive / diagnostic`，**不得用来升级 primary claim**：

```text
exact LogLoss              （cross / native 均 finite；无 clipping）
10-bin reliability         （equal-width，空 bin 保留）
support / range geometry   （见下）
TRAIN-refit stability      （见 F）
end-to-end native winner diagnostics
```

support geometry（descriptive）：

```text
MiniCPM CAT->OVR : source CAT TRAIN (n=456); TARGET OVR TEST outside src min/max = 0.0000; outside src q2.5/q97.5 = 0.000877
MiniCPM OVR->CAT : source OVR TRAIN (n=456); TARGET CAT TEST outside src min/max = 0.0877; outside src q2.5/q97.5 = 0.2070
Qwen    CAT->OVR : source CAT TRAIN (n=456); outside src min/max = 0.0000; outside src q2.5/q97.5 = 0.0061
Qwen    OVR->CAT : source OVR TRAIN (n=456); outside src min/max = 0.2640; outside src q2.5/q97.5 = 0.4825
```

range-loss decomposition（descriptive）：

```text
MiniCPM CAT->OVR : n_in = 1140, n_out = 0
MiniCPM OVR->CAT : n_in = 1040, n_out = 100
```

三基线风险差（descriptive；注意 cross-vs-raw 与 cross-vs-native 符号可以不同）：

```text
MiniCPM CAT->OVR : cross_vs_raw ~ -0.027（全部为负，cross 低于 raw）; cross_vs_native ~ +0.0004..+0.0044（为正）
MiniCPM OVR->CAT : cross_vs_raw ~ -0.012..-0.021（负）;              cross_vs_native ~ +0.003..+0.015（正）
Qwen    CAT->OVR : cross_vs_raw ~ -0.011..-0.027（负）;              cross_vs_native ~ +0.0013..+0.0244（正）
Qwen    OVR->CAT : cross_vs_raw ~ +0.014..+0.021（正，cross 高于 raw）; cross_vs_native ~ +0.011..+0.017（正）
```

end-to-end native winner diagnostics（descriptive）：

```text
MiniCPM: cat_own_winner_accuracy 0.5430 | ovr_own_winner_accuracy 0.4886 | winner_agreement 0.4649 (n=1140)
Qwen   : cat_own_winner_accuracy 0.5018 | ovr_own_winner_accuracy 0.4816 | winner_agreement 0.4851 (n=1140)
```

**关键 descriptive 观察（不是 claim）：** 三基线 comparators 可以给出不同的 sign pattern。

```text
Qwen OVR->CAT 是一个不同的 descriptive pattern：

  cross_vs_raw > 0
  cross_vs_native > 0

即 transferred calibrator 的 Brier risk 同时高于 raw target score
和 target-native calibrator。

For Qwen OVR->CAT, both cross-vs-raw and cross-vs-native are positive:
the transferred calibrator is worse than both the raw target score
and the target-native calibrator.
```

真正呈现 comparator sign disagreement（`cross_vs_raw < 0` 且 `cross_vs_native > 0`）的条件是：

```text
MiniCPM CAT->OVR
MiniCPM OVR->CAT
Qwen CAT->OVR
```

其准确含义是：

```text
transferred calibration improves over doing nothing / raw,
but still underperforms a calibrator fitted natively
on the target measurement.
```

这正说明 `transport succeeded / failed` 不能作为一个不带 comparator 的二元结论：必须区分「相对 raw 是否有部署改善」（deployment delta）与「相对 target-native 是否存在 transfer penalty」（transport penalty）。这正是三基线 contract 的存在理由，也是未来 predictor 必须区分二者的经验依据。

**不要**把 Qwen OVR->CAT 写成 cross-vs-raw 与 cross-vs-native 符号相反的例子——它不是。

## Vocabulary rule [PLANNING DECISION — 全文强制，防 estimand 漂移]

```text
deployment delta:
    Δ_raw(A->B;F) = R_cross(A->B;F) - R_raw(B)

transport penalty:
    Δ_native(A->B;F) = R_cross(A->B;F) - R_native(B;F)

These are distinct estimands and must never be used interchangeably.
```

- R3 primary 正式 hypothesis 测的是 `cross-vs-raw`，即 **deployment delta**，不是 `cross-vs-native` transport penalty。
- 因此 R3 的正式 primary 证据是 **deployment delta 的 F-conditioned dependence**，而不是一个模糊的 "all transport risk is F-dependent"。
- 全文若出现 `transport risk` 一词，必须立刻说明具体指哪个 estimand；更推荐直接不用模糊词，改用 `deployment delta` / `transport penalty`。
- R4 可以同时研究两个 estimand，但必须**分开定义、分开假设、分开解释**，不能混成一个 outcome。

术语不得混用（另一条防漂移规则）：

```text
native-reference
  = target-native calibration adequacy / improvement / degradation status
    对应 R_native - R_raw 的 TEST inference（R3 的 m=8 native-reference 家族）

TRAIN-refit stability
  = 对 resampled TRAIN 重拟合的 bootstrap 稳定性诊断
    对应 R3 §17 的 2000 TRAIN-refit diagnostic（INCOMPLETE / COMPLETE 记法）

二者不是同一件事，禁止把 native-reference 写成 native-refit。
```

---

# H. R3 allowed claims（claim ledger）[R3 RESULT]

以后 paper 只能从本 ledger 中取 R3 statement。

```text
A1. 在 primary condition（MiniCPM5-2B，MMLU，fixed-event CAT/OVR，predeclared F panel）下，
    cross-vs-raw calibration risk 依赖 predeclared F panel
    （>=1 of 6 adjusted intervals excludes zero）。

A2. 两个方向中被调整区间检出的 predeclared contrast pattern 不同：
    CAT->OVR 检出 regularization 与 interaction；
    OVR->CAT 检出 feature。

    这只是 direction-specific detection pattern 的描述，
    不是一个正式的 between-direction effect-difference test
    （R3 未预注册 contrast_CAT->OVR - contrast_OVR->CAT 的 between-direction hypothesis；
    significant in one direction + not significant in the other
    != significant difference between directions）。

A3. cross-vs-raw 与 cross-vs-native 是两个不同 comparator，
    在本数据中可以给出不同的方向/含义（R2 已提出，R3 复现其存在性）。

A4. 在 preregistered replication model（Qwen3.5-2B）上，
    观察到 4/6 adjusted intervals excludes zero 的 replication pattern
    （作为 replication evidence 单独陈述，不并入 primary）。

A5. native-reference（R_native - R_raw 的 target-native calibration adequacy status）
    在 MiniCPM 全部 8 cells 上为 IMPROVEMENT_SUPPORTED；
    在 Qwen 上呈现 CAT/OVR 不对称（CAT 多为 UNRESOLVED，OVR 全为 IMPROVEMENT）。

A6. TRAIN-refit stability 在不同 procedure 上不同：
    部分 block 因 solver failure 记为 INCOMPLETE（已在 F 节列出）。

A7. 描述性 support geometry 显示 OVR->CAT 方向的 target-outside-source-TRAIN 比例
    明显高于 CAT->OVR（descriptive only）。
```

---

# I. R3 forbidden claims [R3 RESULT — 硬边界]

无论结果长什么样，都禁止：

```text
CAT and OVR are universally incompatible
calibration maps never transport
transport failure is universal
one measurement is intrinsically better
one calibration family is universally superior
accuracy determines transportability
support mismatch causes transport failure
measurement protocol causally changes correctness
R3 proved the full thesis universally
R3 established a causal mechanism
R3 established a universal directional asymmetry
```

补充禁止（来自本任务）：

```text
“first study of fitted calibration map transfer across protocols”
把 R3 primary 说成“某具体 F 才是机制”
用 Qwen 显著来宣称 primary confirmed
用 secondary diagnostic 升级 primary claim
```

---

# J. External review decision ledger [REVIEWER SUGGESTION → 分类]

## ACCEPT

```text
J1. 研究问题有效、精确、可证伪（总体评价）              [ACCEPT]
J2. model / dataset breadth 不足                       [ACCEPT]
J3. 扩大 calibration family（当前 F panel 偏窄）        [ACCEPT]
J4. support-overlap predictor 作为高优先 R4 candidate   [ACCEPT AS HIGH-PRIORITY R4 CANDIDATE]
J5. interaction scale 的 presentation caution           [ACCEPT AS PRESENTATION CAUTION]
J6. story 太 cautionary，需要 positive contribution     [ACCEPT]
```

## PARTIALLY ACCEPT

```text
J7. random anchor concern：                                  [PARTIALLY ACCEPT]
    externally frozen random anchor 不是 deployment policy，
    但它有明确实验目的（切断 measurement → winner/event selection → correctness label 的混淆），
    因此 internal measurement validity 很强、deployment external validity 有限制。

J8. native calibration adequacy：                            [PARTIALLY ACCEPT]
    R3 calibrator 不是每个 subject 只用 8 samples fit，
    而是 456 TRAIN items pooled fit（8/subject 是 balancing / resampling structure）。
    但 native degradation / instability 是真实风险，native-reference audit 继续重要。
```

## DEFER

```text
J9.  anchor-policy factorial（random anchor vs model winner vs other）  [DEFER]
     会引发 experiment matrix explosion；除非 human review 认为是核心 blocker。

J10. sign-flip / permutation（用于 R4）                        [DEFER TO PREREGISTRATION]
     若确有必要，必须在结果前 freeze。
```

## REJECT

```text
J11. sign-flip / permutation 去重解释 R3                      [REJECT AS POST-HOC ADDITION]
```

---

# K. Kim & Kang positioning [LITERATURE FACT]

## K.1 已独立核实的 bibliographic metadata（本任务通过网络核实）

```text
arXiv:2605.27752 (cs.AI)

Current title (v3):
  "Same Answer, Different Confidence: Protocol Sensitivity in LLM Confidence Calibration"

Authors: Hankyeol Kim, Pilsung Kang

v1: 26 May 2026  (title: "Asking Is Not Enough: Protocol Sensitivity in LLM Confidence Calibration")
v2: 1 Jun 2026
v3: 7 Aug 2026   (retitled "Same Answer, Different Confidence: ...")
```

v3 abstract 要点（已核实）：fix one prediction event per question = **the model's own answer together with its correctness label**；score that same answer under a plain query and inside the confidence prompt，holding answer and label fixed；四个 QA datasets，三个 7–8B Instruct models；比较 verbalized confidence vs token likelihood，ECE/AUROC 对 protocol choices 敏感；AUROC 对单调变换不变但 item ordering 改变。

## K.2 human-confirmed literature fact（本任务未再次独立核实其附录内容）

```text
[HUMAN-CONFIRMED LITERATURE FACT]
该工作不只是“不同 prompt confidence 不一样”；
它已接近本项目：固定同一 prediction event，
在 source protocol/context fit calibrator，转移到 target protocol/context，比较 calibration transfer behavior；
其 Appendix / Table 8 存在 cross-context calibration transfer 分析，
其 calibration 包含 isotonic 与 Platt-style calibration。
```

## K.3 由此产生的硬性定位规则

```text
绝对禁止宣称：
  “first study of fitted calibration map transfer across protocols”

也禁止把 Kim & Kang 弱化成 strawman：
  “Kim & Kang only study confidence variation”
  “Kim & Kang do not study calibration transfer”
  “Kim & Kang study a completely different problem”
```

正确立场：**complement + distinction**，不是否定对方。

---

# L. Novelty claim correction [PLANNING DECISION]

novelty 必须 narrowed + accurately repositioned，不是 abandoned。

```text
不得写：We are the first to study calibration transfer.
推荐写：We study calibration transport under an externally fixed event,
        with explicit raw/native/cross baselines and a preregistered
        procedure-conditioned analysis.
```

novelty moat 应建立在：

```text
N1. event construction：D_i 在 measurement 之前由外部冻结；Y_i = 1[D_i correct]；
    CAT 与 OVR 都测同一个外部声明事件 D_i
    -> 切断 measurement → winner/event selection → correctness label 的混淆

N2. three-baseline contract：R_raw / R_native / R_cross 强制同时报告；
    cross = source measurement 上 fit 的 calibrator 应用于 target score

N3. F-conditioned transport：不是只问“map transfer 好不好”，
    而是问 deployment delta（R_cross - R_raw）是否依赖 predeclared calibration procedure F
    （feature geometry × regularization 的预声明 factorial probe）

N4. confirmatory design：untouched confirmatory TEST population、
    new transport-model condition、frozen multiplicity、frozen decision rule、
    frozen raw evidence、primary / replication 区分

N5. (future) pre-transport predictive diagnostic：support/geometry risk signal
```

与 Kim & Kang 的精确差异（event construction）：

```text
本项目：D_i 在 measurement 之前由外部冻结，与模型自身 winner 解耦。
Kim & Kang：固定 model-generated answer / prediction event across protocol/context。
二者接近，但不相同。必须准确表述。
```

---

# M. Kim & Kang differentiation table [LITERATURE FACT + PLANNING DECISION]

| Dimension | Our work | Kim & Kang | Overlap | Difference | What we can claim |
|---|---|---|---|---|---|
| declared event | 外部冻结的 D_i（measurement 之前），与模型 winner 解耦 | 模型自身生成的 answer + 其 correctness label，跨 context 固定 | 都固定同一 prediction event | 事件来源不同：外部声明 vs 模型生成 | 我们研究“外部声明事件”下的 transport |
| how event is fixed | 由设计预先声明，CAT/OVR 都测同一 D_i | 由模型输出确定，之后跨 protocol 保持固定 | 都强调 event 必须固定 | 固定时机与来源不同 | 我们切断 event-selection 混淆 |
| measurement axis | CAT（candidate-anchor token prob）vs OVR（option-value probability） | conditioning context / scored string / token readout / elicitation provenance | 都研究“measurement 变化” | 轴不同：CAT/OVR vs prompt/context | 我们的 axis 是同一 event 的两种 probability 赋值 |
| fitting population | frozen TRAIN 456（MMLU，8/subject） | 各 dataset/protocol setting | 都需要 fitting data | population 显式冻结 + subject-stratified | 我们的 fit population 是 preregistered |
| calibrator family | logistic（feature geometry × λ）F panel | isotonic + Platt-style（附录 transfer） | 都用参数/非参数 calibrator | 我们做 F-conditioned factorial；他们做 transfer 比较 | 我们问“transport 是否依赖 F” |
| transfer estimand | R_cross(A->B;F) 相对 R_raw / R_native 的 directional contrast | cross-context calibration transfer behavior | 都关心 transfer | estimand 与 comparator 结构不同 | 我们给出三基线 directional estimand |
| baseline comparator | 强制 raw + native + cross 三者 | 未以三基线 contract 组织 | 都可能比较多种条件 | 三基线 contract 是显式差异 | 我们主张三基线报告契约 |
| role of F | 核心变量（predeclared factorial probe） | calibrator 是分析工具之一 | 都涉及 calibrator choice | F 是否是 estimand 的核心不同 | 我们把 F 提升为条件化变量 |
| model breadth | 2 × 2B（R3），计划 4 models（R4） | 3 × 7–8B Instruct（+ Qwen2.5 robustness） | 都多模型 | 我们当前更小、更少 | 我们当前 breadth 是 limitation |
| dataset breadth | MMLU（R3），计划 +1 非 MMLU（R4） | 四个 QA datasets | 都多 dataset | 我们当前单一 dataset | 我们当前 dataset breadth 是 limitation |
| inference / preregistration | frozen multiplicity、decision rule、primary/replication | 主要是描述性 protocol-sensitivity | 都关注 protocol 影响 | 我们有 confirmatory 结构 | 我们的 confirmatory 结构是差异 |
| claim scope | directional, population/metric-dependent compatibility | protocol-dependent behavioral measurement | 都反对“固定属性”观点 | claim 形式与 formalization 不同 | 我们 formalize directional compatibility relation |

---

# N. Literature 分层 [LITERATURE FACT]

```text
Tier 1: direct protocol / confidence / calibration-transfer work
        -> Kim & Kang（直接近邻）

Tier 2: probability elicitation / scoring protocol work
        -> verbalized confidence、token-probability readout、scoring protocol

Tier 3: distribution-shift calibration literature
        -> Ovadia 等

Tier 4: general calibration methods
        -> Platt / isotonic / beta / temperature scaling 等
```

关键纪律：

```text
不能说 distribution shift = measurement protocol shift
```

paper 保留的概念句（可润色，含义不丢）：

```text
Distribution shift changes the population presented to a predictor;

measurement-protocol shift changes how probability is assigned
to the same declared event.
```

---

# O. Current evidence gaps [PLANNING DECISION]

```text
G1. 只有 2 个 2B 模型（scale / family breadth 不足）
G2. 只有 MMLU 一个 population
G3. F panel 仍主要是 logistic geometry × λ（family breadth 不足）
G4. 尚无 pre-transport predictive diagnostic 的实证
G5. public MMLU contamination cannot be excluded
G6. bootstrap / refit 目前主要单 CPU core（工程效率，不是科学缺陷）
```

---

# P. R4 goals [PLANNING DECISION]

R4 research question（推荐方向，不冻结措辞）：

```text
Does the deployment delta (R_cross - R_raw) remain measurably
procedure-dependent across broader model families,
model scales, and populations?

And can pre-transport score geometry provide
a preregistered target-label-free warning signal
for the deployment delta and/or the transport penalty
(R_cross - R_native)?
```

**R4 is not designed to rescue, strengthen, or overturn the R3 primary result.**
R4 addresses independently identified external-validity and generalization questions。

## R3 continuity claim 必须绑定 deployment delta [PLANNING DECISION]

```text
R3 confirmed F-dependence of deployment delta
in the MiniCPM primary condition
under the frozen decision rule.
```

不得写成 `R3 confirmed all forms of transport penalty / transport risk are F-dependent`。
R4 的 continuity 部分只能继承上面这一条精确表述。

## R4 rationale 在读取 R3 详细结果之前就已确定 [PLANNING DECISION — 防 HARKing]

以下方向由 external review + literature positioning + breadth concern 提出，**先于**正式读取 R3 详细结果：

```text
- 2 × 7–8B models
- 至少 1 个真正非 MMLU population
- 新 calibration families（isotonic / beta）
- support-overlap predictor
```

因此 R4 设计必须 outcome-independent。

## R4 minimum breadth target（不得由 agent 自行下调）

```text
models    : 2 new 7–8B（不得降回 1）
population: >= 1 truly non-MMLU（不得删除）
family    : retain R3 P/L continuity panel + isotonic candidate + beta candidate
predictor : support-overlap diagnostic（high-priority，不得由 agent 自行删除；未冻结）
```

### population target：minimum vs recommended [PLANNING DECISION]

```text
hard minimum        : >= 1 truly non-MMLU population
recommended target  : 2 non-MMLU populations
                      if predictor validation is intended
                      as a major paper contribution
```

理由：predictor 的有效独立单位不是「每个 F」，而更接近 `model × population × direction`。
若只有一个新 population，独立 validation units 数量仍然有限，且不得靠把多个 F 当独立样本来虚增 n。

若最终只能实现 1 个 non-MMLU：

```text
不要把研究判为失败——model / population generalization 仍然有价值；
但 predictor contribution 应更保守，定位为
secondary / exploratory predictive evidence，
而不是 headline validated predictor。
```

---

# Q. R4 candidate evidence matrix [PROPOSED R4 DESIGN]

优先评估的设计：

```text
MMLU:
  existing R3: 2 × 2B frozen results
  R4 new measurement: 2 × 7–8B

new non-MMLU population:
  run all 4 models（2 existing 2B + 2 new 7–8B）
```

最终 evidence grid：

```text
MMLU      : 4 models total（2 frozen R3 + 2 new R4）
Non-MMLU  : 4 models
```

优点：

```text
model-scale generalization
model-family generalization
population generalization
```

三者能相互连接。**不要直接 freeze；要比较其科学价值 / cost / complexity。**

---

# R. R4 model-selection principles [PLANNING DECISION]

outcome-independent 评估标准：

```text
fixed revision availability
license / reproducibility
tokenizer stability
chat template stability
CAT probability extraction correctness
OVR probability extraction correctness
enable_thinking / equivalent controllability
local/offline execution feasibility
7–8B scale
GPU memory feasibility
family diversity
community relevance
not selected based on calibration outcome
```

原则：

```text
preferably different model families
至少一个 family 不应只是现有 2B family 的简单放大版
禁止根据 R3 outcome 挑“更容易复制结果”的模型
```

本任务只给 shortlist，**不正式 freeze model revision**（留待下一轮 human model-selection gate）。

## 优先 diversity 而非极端参数量

```text
优先：2B family A + 2B family B + 7–8B family C + 7–8B family D
而非：2B + 2B + 70B
```

不要为了“更大模型”直接跳 70B（本研究主要不是 scale law）。

经费不是主要约束：正式 7–8B 可用租赁 4090 / 5090 / 80GB GPU；scientific value > 省算力。硬件不是 scientific contribution。

---

# S. R4 dataset-selection principles [PLANNING DECISION]

至少新增 1 个真正非 MMLU population（不是 MMLU 轻微变体）。

必须适配 fixed-event semantics：能够自然定义

```text
externally frozen decision D_i
ground truth GT_i
Y_i = 1[D_i = GT_i]
```

且 CAT / OVR 都能测 `P(D_i correct)`。不能为了 dataset 强行改变 target semantics。

筛选标准：

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

---

# T. R4 calibration-family expansion [PROPOSED R4 DESIGN]

R3 panel（保留 continuity）：

```text
P-low / P-historical / L-low / L-historical
= logistic calibration × feature geometry × regularization
```

认真评估加入：

```text
isotonic calibration  作为 non-parametric family
beta calibration      作为 distinct parametric family
```

**DESIGN CANDIDATE ONLY。** 正式冻结前必须明确：

```text
family definition
parameterization
objective
regularization
hyperparameter selection
endpoint behavior
out-of-support behavior
ties
fitting protocol
selection rule
failure rule
```

F identity 完整定义（R4 继续坚持）：

```text
F includes: family / transform / objective / regularization / hyperparameter rule /
            endpoint treatment / fitting-data protocol / selection rule
solver / precision / device / library 一般属于 provenance，不是 scientific F，
除非其变化会改变算法定义。
```

不要把“isotonic 没有 λ”当成 F 不完整：isotonic 自身 family + fitting rule + endpoint/extrapolation rule 就构成独立 procedure；不能强行构造假的 2×2 factorial。

---

# U. Support-overlap predictive diagnostic [PROPOSED R4 DESIGN]

高优先 R4 candidate；可让论文从“transport may fail”升级为“we can identify risk before deployment”。

硬性边界：

```text
只能 predictive diagnostic，不得 causal mechanism
不得写“support mismatch causes transport failure”
```

target-label-free 约束（若目标是 pre-transport diagnostic）：

```text
"target-label-free" means that predictor construction and application
require no target outcome labels.

允许：
  source TRAIN scores
  source TRAIN labels（仅通过 source calibrator fitting 等 source-side procedure 使用）
  target unlabeled score distribution
  fitted source calibrator geometry

禁止：
  target Y / target correctness labels
  target Brier / target LogLoss
  任何由 target outcome label 派生的 feature
```

候选 support metrics（下一轮需 predeclare 1 primary predictor + small secondary diagnostic set，不要一次上十几个）：

```text
fraction target outside source min/max
fraction target outside source q2.5/q97.5
1D Wasserstein distance
CDF / KS-style discrepancy
```

必须区分两种 outcome：

```text
transport penalty  : R_cross - R_native
deployment delta   : R_cross - R_raw
```

不能混成一个（R2 已证明二者可以方向不同；R3 descriptive 亦复现）。

## 避免 pseudo-replication

不能把同一 model × population × direction 下的多个 F cell 当独立样本做 Pearson correlation。必须考虑 dependence。

candidate unit：优先 `model × population × direction` 作为 grouped unit；若需要 F-specific predictor，必须 group-aware inference / resampling。

## 两个 predictor architectures（本轮仅设计）

```text
Architecture 1（measurement-pair level）:
  support mismatch -> mean/max predeclared transport penalty across F
  优点：避免 F-level pseudo-replication

Architecture 2（F-specific target-label-free diagnostic）:
  support mismatch + fitted map sensitivity / extrapolation behavior
  -> F-specific transport penalty
  必须 grouped inference
```

## Predictor development / validation isolation [PLANNING DECISION — 硬边界]

R3 的 support geometry 已经被我们看过，因此：

```text
R3 model × MMLU × direction cells
are development / hypothesis-generation evidence only
for the future predictor.

They must not be counted as independent confirmatory
validation units for R4 predictor performance.
```

只有 formal predictor specification 冻结之后新产生的 R4 target outcomes，
才可以进入 preregistered predictor validation。

```text
No predictor metric, feature set, threshold,
coefficient, aggregation rule, or selection rule
may be tuned using R4 target outcomes.

All such choices must be frozen before target-outcome inspection.
```

grouped unit 继续保持：`model × population × direction`；
禁止把同一个 grouped unit 中多个 F cell 当成独立样本。

---

# V. Candidate R4 inference architectures [PROPOSED R4 DESIGN]

随 family 增加，R3 的 2×2 factorial contrasts 可能不再覆盖全部 F。至少两种 candidate：

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

比较维度（不得现在 freeze）：

```text
interpretability
multiplicity burden
continuity with R3
risk of post-hoc flexibility
```

## 反 HARKing 约束

禁止：

```text
R3 interaction 显著 -> R4 只研究 interaction
某方向强 -> R4 只保留这个方向
```

R4 breadth expansion 的动机已在读取详细 R3 结果之前存在。

---

# W. Engineering improvements [PLANNING DECISION]

R3 正式分析显示 bootstrap / refit implementation 主要单 CPU core。R4 前可优化为 deterministic multi-process CPU parallelism，**必须在 freeze 前完成**，且满足：

```text
replicate index 唯一确定 bootstrap draw
worker count 不改变 scientific result
aggregation order fixed
single-worker 与 multi-worker numerically equivalent（或按声明契约 byte-equivalent）
failure semantics identical
```

不能在正式 R4 运行中途临时换并行方案。

GPU：正式 7–8B 可用租赁 4090 / 5090 / 80GB GPU；本地 5060 Laptop 已能跑当前小模型。

## audit expansion 到此为止

除以下情况，不要继续增加 audit-of-audit-of-audit 文档：

```text
新模型 adapter correctness
新 dataset population integrity
新 calibration family oracle tests
新 deterministic parallel implementation correctness
new provenance necessary for reproducibility
```

---

# X. Paper contribution structure [PLANNING DECISION]

## Supported NOW by frozen R3

```text
C1. formal compatibility relation：A --[M,P,T,L,E,F]--> B（formulation）
C2. three-baseline reporting contract：raw / native / cross
C3. confirmatory evidence that cross-vs-raw risk depends on predeclared F panel（primary condition）
C4. R2 constructive counterexamples + R3 confirmatory evidence 的组合
```

## Potential AFTER successful R4

```text
C5. pre-transport predictive diagnostic（support / geometry risk signal）
    只有 R4 真正成功后才能成为 empirical contribution；现在只能写 planned R4 contribution
C6. broader model scale/family/population generalization
```

禁止把未来计划写成已完成贡献。

## Paper north-star statement（候选，可润色）

```text
Calibration compatibility is not a property of a model alone.

It is a directional relation conditioned on
how probability is measured,
where the map is fitted,
what event is declared,
how loss is defined,
and which calibration procedure is used.
```

## Comparator-dependent story [PLANNING DECISION — 防 overclaim]

```text
Calibration transport is procedure-conditioned
and comparator-dependent.

A transferred map may improve over doing nothing
without matching a target-fitted calibrator.
```

中文：

```text
校准迁移不能用一个不带 comparator 的「成功 / 失败」标签概括。

一个 transferred calibrator
可能比 raw target score 更好，
但仍明显差于 target-native calibrator。
```

不要把论文写成 `calibration transfer is bad` / `calibration transport fails`。
正确 thesis：compatibility is conditional，且 operational conclusion
取决于声明了哪个 comparator 与哪个 fitting procedure。

## 结果可以影响 narrative emphasis，但不能制造 hypothesis

```text
允许：若 R3 primary detected F dependence，paper foreground procedure-conditioned transport
      （因为该 interpretation 是 predeclared）
禁止：看到具体某个 F 最强 -> 事后宣布那才是核心 hypothesis
```

---

# Y. Paper skeleton [PLANNING DECISION]

```text
1. Introduction
2. Problem formulation
   - declared event / measurement / calibration map / compatibility relation
3. Why identity is not compatibility
   - R2 counterexamples / three-baseline distinction
4. Fixed-event paired design
   - D_i / Y_i / CAT / OVR
5. R3 confirmatory study
   - preregistration / models / MMLU / F panel / inference
6. R3 results
7. Transport diagnostics
   - support / train-refit / native adequacy
8. R4 generalization study
   - only once executed
9. Related work
   - Kim & Kang / elicitation / scoring / distribution-shift calibration
10. Discussion
    - map-level vs procedure-level / limitations / deployment relevance
11. Conclusion
```

R4 未运行时：第 8 节只能写 planned / future study，不能伪装成已有结果。

## R2 的角色不要被 R3 吞掉

```text
R2 = conceptual / empirical counterexample foundation
R3 = frozen confirmatory evidence
R4 = breadth + prediction
```

R2 限制继续有效，不得说：

```text
R2 proved universal CAT/OVR incompatibility
R2 proved directional failure universally
R2 proved support mechanism
R2 proved accuracy determines transportability
```

## map-level != procedure-level

```text
g_(A,F,D) 是某个 measurement A、某个 procedure F、某个 fitting population D 得到的 empirical map。
单个 map 的 transport result 不能自动升级为 procedure family universally compatible / incompatible。
```

---

# Z. Limitation ledger [PLANNING DECISION]

paper limitations 必须主动写：

```text
L1. R3 only two 2B models
L2. R3 only MMLU
L3. R3 narrow F panel（logistic geometry × λ）
L4. fixed random anchor is experimental measurement design, not deployment decision policy
L5. public benchmark contamination cannot be excluded（R4 加非 MMLU 可降低单一 benchmark 依赖，但不能自动声称彻底排除 contamination）
L6. map-level evidence does not imply universal procedure compatibility
L7. bootstrap inference is finite-sample and design-dependent
L8. no causal mechanism claim
```

R4 成功后只能说减弱 L1/L2/L3，不能说 universality established。

---

# AA. 结论性 guardrail [PLANNING DECISION]

后续任何 agent 若提出：

```text
“为了更完整再给 R3 加一个检验”          -> NO
“再加十个 measurement protocol”          -> DEFER
“因为 R3 某方向结果漂亮，所以 R4 只跑那个方向” -> NO
“Kim & Kang 已经做了 transfer，所以我们没 novelty” -> NO（narrowed + repositioned，不是 abandoned）
“Kim & Kang 没做 transfer，所以完全不相关”      -> NO（factually too weak）
```

正确方向：

```text
更精准的 novelty
+ 更广的 evidence
+ 更少的 audit overgrowth
+ 更明确的 positive contribution
```

---

# AB. Next gates [PLANNING DECISION]

**Gate order 原则（硬性）：** 模型、dataset、fixed-event semantics、calibration family、
inference、predictor、multiplicity、execution semantics 都是 scientific design 本身，
必须在**最终 R4 freeze 之前**全部关闭。不得出现「模型还没选，R4 已经 freeze」。

```text
1.  human review of R3 interpretation（本文件 C–I 节）
2.  human review of R4 / paper strategy（本文件 P–Y 节 + R4_DESIGN_DRAFT.md）
3.  Model-selection gate
4.  Dataset-selection gate
5.  Fixed-event semantics closure for new population
6.  Calibration-family semantic + oracle closure
      - R3 P/L continuity
      - isotonic
      - beta
7.  Inferential architecture closure
8.  Target-label-free predictor specification closure
9.  Multiplicity / hypothesis-family closure
10. Primary / replication or multi-condition structure closure
11. Deterministic parallel implementation
12. Single-worker vs multi-worker equivalence verification
13. Model-adapter / dataset-integrity / calibration-family engineering tests
14. Final R4 protocol + implementation freeze
15. Execution-entry gate
16. Official R4 raw measurement
17. Official frozen R4 analysis
18. Paper integration
```

预期路线：

```text
R3 frozen result
↓
human scientific interpretation
↓
paper-positioning / Kim & Kang differentiation
↓
human review of corrected R3/R4 strategy
↓
Model-selection gate
↓
Dataset-selection gate
↓
Fixed-event semantics closure for new population
↓
Calibration-family semantic + oracle closure（R3 P/L continuity / isotonic / beta）
↓
Inferential architecture closure
↓
Target-label-free predictor specification closure
↓
Multiplicity / hypothesis-family closure
↓
Primary / replication or multi-condition structure closure
↓
Deterministic parallel implementation
↓
Single-worker vs multi-worker equivalence verification
↓
Model-adapter / dataset-integrity / calibration-family engineering tests
↓
Final R4 protocol + implementation freeze
↓
Execution-entry gate
↓
Official R4 raw measurement
↓
Official frozen R4 analysis
↓
Paper integration
```

**Guardrail（analysis implementation）：**

```text
R4 的 outcome-dependent analysis definitions
和正式 analysis implementation
必须在查看正式 R4 target outcomes 之前冻结。

不得留下「看完 R4 raw/result 再实现 inferential rule」的空间。
```

而不是：继续无限扩 R3 audit。

---

# AC. 2026-09-30 PRE-OUTCOME HUMAN BREADTH DECISION [PLANNING DECISION]

**时序声明（关键）：** 本节的全部决定，由 human 在**任何正式 R4 target outcome 出现之前**作出，
并且是在 Qwen3.5-9B engineering probe（Phase 2D）**之前**记录。
本节只把 design decision 固化进 planning authority，不产生任何 R4 measurement、不产生任何 scientific outcome。

**状态不变：**

```text
R4:                          DRAFT
R4:                          NOT FROZEN
R4:                          NOT OFFICIALLY EXECUTION-AUTHORIZED
FINAL R4 MODEL PAIR:         NOT SELECTED
FINAL R4 DATASET:            NOT SELECTED
```

本节是 human planning decision 的 append-only 记录，**不是** R4 freeze，也不得被解读为 freeze。

## AC.1 Model breadth decision [PLANNING DECISION]

当前 intended current-generation R4 model panel 扩为四个：

```text
1. allenai/Olmo-3-7B-Instruct
2. tiiuae/Falcon-H1-7B-Instruct
3. ibm-granite/granite-4.0-h-tiny
4. Qwen/Qwen3.5-9B
```

Qwen3.5-9B 的角色明确为：

```text
SAME-LINEAGE SCALE-CONTINUITY BRIDGE
R3: Qwen/Qwen3.5-2B  ->  R4: Qwen/Qwen3.5-9B
```

它不是 family-diversity 主力，而是 2B→9B 的 scale-continuity condition。

若 Phase 2D engineering PASS，当前计划是：

```text
四个 current-generation models 全部进入后续 R4 design
（不再从四个里自动选两个）
```

但：

```text
这仍不是 R4 FINAL FREEZE。
后续必须还有 formal design freeze gate。
```

## AC.2 Population decision [PLANNING DECISION]

当前 intended population panel：

```text
1. MMLU      (R3 continuity population)
2. HellaSwag (non-MMLU / commonsense event-completion population)
3. MedMCQA   (non-MMLU / medical-domain population)
```

当前不计划增加 ARC / OpenBookQA / CommonsenseQA / SciQ，
除非 dataset semantic closure 暴露 substantive blocker。

本任务不下载、不运行任何正式 dataset；exact dataset revisions、fixed-event semantics、
strata、TRAIN/TEST construction、population manifests 仍全部待 closure。

## AC.3 Intended evidence grid [PLANNING DECISION]

MMLU：

```text
frozen R3 evidence : MiniCPM5-2B, Qwen3.5-2B
  不得重跑，不得重新定义。

R4 新增            : Olmo-3, Falcon-H1, Granite-4, Qwen3.5-9B
最终结构           : 2 frozen R3 models + 4 current-generation R4 models
```

但：

```text
R3 model × MMLU cells
只能作为 predictor development / hypothesis-generation evidence，
不能冒充新的 R4 independent predictor-validation units。
```

HellaSwag / MedMCQA（2 个新 non-MMLU population）：

```text
MiniCPM5-2B
Qwen3.5-2B
Olmo-3
Falcon-H1
Granite-4
Qwen3.5-9B
即 6 models × 2 new non-MMLU populations
```

该 evidence grid 仍需 dataset semantic closure / fixed-event D_i closure / strata closure /
TRAIN-TEST split closure 后才能 freeze。

## AC.4 Calibration-family decision [PLANNING DECISION]

R4 planned F panel：

```text
continuity core（保留 R3）:
  P-low / P-historical / L-low / L-historical
  (logistic calibration × feature geometry × regularization)

family extension（human-selected planned families）:
  isotonic calibration  (non-parametric monotone family)
  beta calibration      (distinct parametric calibration family)
```

治理原则：

```text
R3 logistic factorial      = continuity confirmatory core
isotonic + beta            = predeclared family-extension hypotheses
不构造假的统一 factorial
```

仍未 freeze：exact family definition / parameterization / objective / regularization /
hyperparameter rule / endpoint behavior / out-of-support behavior / tie handling /
fitting protocol / selection rule / failure rule。

因此：

```text
isotonic / beta = HUMAN-SELECTED PLANNED FAMILIES
但不是 FULLY SPECIFIED / FROZEN F YET
```

## AC.5 Metric decision [PLANNING DECISION]

```text
primary evaluation metric     : Brier risk
secondary                     : exact LogLoss
descriptive only              : reliability diagnostics / reliability diagram
```

当前明确不因 “breadth” 额外加入 ECE family / ACE family / multiple NLL variants，
除非后续 human 明确重新打开 metric gate。不扩大 metric zoo。

## AC.6 Predictor decision [PLANNING DECISION]

R4 target-label-free warning signal：

```text
PRIMARY planned predictor:
  fraction of target scores outside source TRAIN q2.5 / q97.5 interval
  (q2.5-q97.5 support-exceedance fraction)

SECONDARY planned diagnostic:
  1D Wasserstein distance between source-TRAIN score distribution
  and target score distribution
```

target-label-free 定义仍然严格：

```text
允许: source TRAIN scores / source-side fitting information /
      source TRAIN labels（仅通过 source calibration procedure）/
      target unlabeled score distribution / fitted source calibrator geometry

禁止: target correctness labels / target Y / target Brier / target LogLoss /
      任何由 target-outcome 派生的 feature
```

## AC.7 Predictor inference unit [PLANNING DECISION]

```text
默认 grouped unit: model × population × direction
```

禁止把同一个 group 内不同 F 当成独立样本虚增 n。
若未来使用 F-specific predictor，必须使用 group-aware inference / grouped resampling。

```text
R3 model × MMLU × direction
只允许 development / hypothesis-generation，
不能算作新的 R4 confirmatory predictor validation。
```

## AC.8 Model search stopping rule [PLANNING DECISION]

若 Qwen3.5-9B Phase 2D PASS：

```text
CURRENT MODEL EXPANSION: CLOSED
model panel: Olmo / Falcon / Granite / Qwen3.5-9B
Ministral:   DEFERRED
```

不再搜索第五个模型、不再下载 Ministral、不再下载任意新 candidate，
除非后续出现 substantive scientific design blocker。

## AC.9 Guardrail [PLANNING DECISION]

```text
本节 decision 先于正式 R4 target outcomes。
本节不产生任何 R4 outcome、不产生任何 scientific selection。
R4 仍为 DRAFT / NOT FROZEN / NOT EXECUTION-AUTHORIZED。
```
