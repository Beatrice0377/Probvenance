# R4 Calibration-Family Semantic Closure — Candidate

```text
STATUS:
SEMANTIC CANDIDATE
NOT FROZEN
NO STUDY FITTING
NO EXECUTION AUTHORIZATION
```

本 artifact 是 **human semantic-freeze review 的候选输入**，不是 frozen protocol，
不是 production calibrator 实现，不是 R4 execution authorization。

本 gate 不产生任何 scientific outcome：无 model load、无 model inference、
无 study-dataset row、无 real calibration fitting、无 Brier、无 LogLoss、
无 transport outcome、无 predictor outcome。

---

## 1. Scope

本 gate 机械保存 R3 四程序 continuity core，并给出两个 family-extension 程序
`I-isotonic` 与 `B-beta` 的完整候选 scientific semantics：

```text
R3 CONTINUITY CORE（不改动）:
  P-low
  P-historical
  L-low
  L-historical

FAMILY EXTENSIONS（新增候选）:
  I-isotonic
  B-beta
```

本 gate **不**新增 temperature scaling、histogram binning、spline calibration、
vector scaling、matrix scaling、Platt variants 或 beta variants；
也 **不**删除任何 R3 continuity 程序。

本 gate **不**构造假的 `3-family × regularization × feature` factorial。

---

## 2. Authority / inputs

只读引用（未修改）：

```text
experiments/calibration_transport/r3_protocol_design.json   （frozen R3 procedure identities）
experiments/calibration_transport/r3_protocol.py            （frozen R3 protocol construction）
experiments/calibration_transport/r3_analysis.py            （frozen R3 fitting/feature/loss code）
src/probvenance/calibration.py                              （L2-logistic fitting + application kernel）
experiments/calibration_transport/measurements.py           （fixed-decision decision builders）
experiments/calibration_transport/R4_POPULATION_FREEZE.md   （frozen population layer）
experiments/calibration_transport/R4_DESIGN_DRAFT.md        （§6 F panel，含待答 OPEN QUESTION）
docs/research/calibration-transport-r3-r4-paper-strategy.md （planning authority）
```

R3 procedure identity 的 canonical payload 来自 `r3_protocol.py`
`R3CalibrationProcedure.canonical_payload()`；fingerprint = `fingerprint(payload)`
（`probvenance.fingerprint`，sha256 over canonical JSON）。

---

## 3. R3 continuity hard gate

四个 frozen R3 procedure identity 已机械重算（读 `r3_protocol_design.json` 的 payload，
重算 `fingerprint(payload)`，并与 declared fingerprint 及预期值三方比对）：

| procedure | expected fingerprint | declared | actual | match |
| --- | --- | --- | --- | --- |
| P-low | `7a8e13d51e131f2102cca4e00b172c8bbb2eb49e591acd3746aeb64d003c8857` | same | same | YES |
| P-historical | `a44e9217dd43e5e29d859c8dd2dc510a5876db4d46a8e0cc2fd4f1df3121a423` | same | same | YES |
| L-low | `91d7d506275aade7d4676c39722ac2c4d975de7967a25a808395c056307ad619` | same | same | YES |
| L-historical | `23ec12bbf4a809ba2f419491df80d1f228d3fd778d848115839aab3697f9dd58` | same | same | YES |

`r3_continuity.all_match = true`。

### 3.1 Exact R3 semantics preserved

| procedure | feature | objective | L2 | endpoint policy |
| --- | --- | --- | --- | --- |
| P-low | identity-raw-probability v1 | mean-bernoulli-nll-plus-l2 v1 | 1e-4 | `exact-raw-probability-accepted` v1 |
| P-historical | identity-raw-probability v1 | mean-bernoulli-nll-plus-l2 v1 | 1e-2 | `exact-raw-probability-accepted` v1 |
| L-low | exact-logit-probability v1 | mean-bernoulli-nll-plus-l2 v1 | 1e-4 | `reject-exact-probability-endpoints` v1 |
| L-historical | exact-logit-probability v1 | mean-bernoulli-nll-plus-l2 v1 | 1e-2 | `reject-exact-probability-endpoints` v1 |

四者共享：

```text
family P = research-l2-logistic-fixed-decision-probability v1
family L = research-l2-logistic-logit-fixed-decision-probability v1
regularization_rule = fixed-l2-strength v1
fitting_data_protocol = paired-frozen-decision-train v1
selection_rule = fixed-panel-no-selection v1
```

P family：feature 是 raw fixed-decision probability `p`，exact `p=0` / `p=1` 被接受；
L family：feature 是 exact `logit(p)`，exact `p=0` / `p=1` 被拒绝
（`r3_analysis.py:112 _logit` 抛 `ProbabilityEndpointError`）。

### 3.2 R4 continuity identity rule

不创建“改良版 R4 P-low”。R4 continuity core 直接记录：

```text
inherits exact frozen R3 scientific procedure identity
```

即 same labels、same payload semantics、same procedure fingerprints。
R3 的 `r3-procedure-...` identifier 保持原样，不因命名美观而重建新 identity。

---

## 4. Fitting target and score semantics

六个 procedures 拟合同一目标：

```text
Y_i = 1[D_i = GT_i]
D_i = externally frozen fixed event / anchor
```

输入 score：

```text
s_i = P_measurement(D_i correct)
```

不是 winner confidence、不是 fresh argmax probability、不是 winner correctness、
不是 renormalized OVR winner score。

（R3 侧对应 `src/probvenance/calibration.py:1062 _selected_probability`：读取
recorded `selected_value` 的概率，不重算 winner、不重跑 tie-break；
R4 侧对应 frozen population layer 的 fixed-event anchor 协议。）

---

## 5. Source / native / cross semantics

对每个 `F`：

```text
Source fit      : 在 SOURCE-measurement TRAIN scores + TRAIN Y 上拟合 F
Cross apply     : 把 frozen source-fitted map 应用到 TARGET-measurement TEST scores
Native fit      : 在 TARGET-measurement TRAIN scores + TRAIN Y 上拟合同一 scientific F
Native apply    : 把 target-native map 应用到 TARGET-measurement TEST scores
Raw             : 未改动的 TARGET score
```

禁止：native 与 cross 使用不同 hyperparameter；按 direction 使用不同 F 定义；
target-outcome tuning。

---

## 6. Primary vs robustness fitting budget

```text
PRIMARY  : TRAIN N = 456
SECONDARY: TRAIN N = 912 = nested primary 456 + deterministic extension 456，same TEST，secondary only
```

六个 `F` 在同一个 budget 内必须使用完全相同的 fitting rows。
禁止给 isotonic 或 beta 更多数据；禁止 procedure-specific row selection。

---

## 7. I-isotonic — candidate specification

```text
label             : I-isotonic
procedure_id      : r4-procedure-I-isotonic
procedure_version : 1
family_id         : monotone-isotonic-fixed-decision-probability
family_version    : 1
candidate fingerprint : cd13bc07bf92f3375bcd16d57fa5f515cd40f68199b57181791f85c58be8c244
```

### 7.1 Input domain

```text
input    : raw fixed-decision probability s
domain   : [0, 1]
```

不做 logit transform、不做 epsilon clipping、不做 label smoothing、
不做 fit 前 score clipping。

### 7.2 Mathematical fitting problem

```text
min_f  (1/n) Σ_i (y_i - f(s_i))^2

subject to:  s_i <= s_j  =>  f(s_i) <= f(s_j)
```

每 item weight = 1；无 class weighting；无 regularization；无 hyperparameter tuning。

### 7.3 Tie handling

对每个 exact unique score `x`：

```text
weight(x)      = 满足 s_i == x 的 TRAIN row 数
target_mean(x) = 满足 s_i == x 的 row 的 Y 均值
```

然后对 `(unique score, target_mean, count weight)` 做 weighted monotone PAVA，
使 row order 无关。禁止 random tie breaking、jitter、epsilon perturbation、sort-by-label。

### 7.4 Monotonic direction

```text
increasing = True（hard fixed）
```

不得使用 `increasing="auto"`、Spearman sign selection 或 decreasing isotonic；
即使 TRAIN sample correlation 为负也不改变。

### 7.5 Fitted range

labels 为 binary 且 PAVA 使用 empirical block means，故 output range 保持 `[0, 1]`。
无 pseudo-count smoothing、无 Laplace correction、无 post-fit shrinkage。
exact fitted value `0` 或 `1` 允许。

### 7.6 Interpolation

```text
piecewise-linear monotone interpolation between fitted isotonic threshold points
```

要求：每个 threshold 处取 exact fitted threshold value；相邻 threshold 之间连续；
处处 non-decreasing。无 spline；无 nearest-neighbor interior step function。

### 7.7 Out-of-source-support behavior

```text
target score < source TRAIN minimum  -> return fitted value at source minimum
target score > source TRAIN maximum  -> return fitted value at source maximum
```

即 nearest-endpoint constant extension（`out_of_bounds = clip-to-fitted-boundary`）。
注意：clip 的是 **INPUT SUPPORT POSITION**，不是把 calibrated probability clip 到任意 epsilon。

### 7.8 Endpoint behavior

输入 `s=0` 与 `s=1` 是普通合法 score：若在 TRAIN 中出现则正常拟合；
若 target 中出现则按 normal interpolation / boundary extension 应用。无 endpoint rejection。

### 7.9 Degenerate cases

```text
所有 score 相等   -> valid fit，map 为 TRAIN empirical positive fraction 处的常数
所有 label 为 0   -> valid constant 0 map
所有 label 为 1   -> valid constant 1 map
```

无自动 smoothing。

### 7.10 Failure rule

仅对 structural / numerical contract violation 失败：

```text
empty fitting set
non-finite score
score outside [0, 1]
non-binary Y
non-deterministic reconstruction
invalid monotone output
```

不因 unique score 值少、map 为常数、或 output 达到 0/1 而宣告失败。

### 7.11 Regularization / hyperparameter

```text
regularization_rule : no-regularization v1   (l2_strength = null)
hyperparameter_rule : no-hyperparameter v1
```

---

## 8. B-beta — candidate specification

```text
label             : B-beta
procedure_id      : r4-procedure-B-beta
procedure_version : 1
family_id         : full-monotone-beta-fixed-decision-probability
family_version    : 1
candidate fingerprint : d7ee7aa9b4c611866ddedfcf66cf8735882324f4f20be9706a8637291feddfb5
```

### 8.1 Mathematical map

interior score `0 < s < 1`：

```text
z(s) = a * ln(s) - b * ln(1 - s) + c
f(s) = sigmoid(z(s))

features:  x1 = ln(s)     x2 = -ln(1 - s)
           z  = a*x1 + b*x2 + c
```

### 8.2 Parameters and constraints

```text
a >= 0
b >= 0
c ∈ R
```

hard monotonicity constraints `a >= 0`、`b >= 0` 属于 scientific procedure identity。
无 unconstrained-fit-then-hope；无 sign-based model-selection fallback。

### 8.3 Identity-map inclusion

```text
a = 1, b = 1, c = 0  =>  f(s) = s   for interior s
```

（semantic invariant；synthetic probe 实测 max abs error = 1.11e-16。）

### 8.4 Fitting objective

```text
mean Bernoulli negative log-likelihood on TRAIN rows
```

无 L2 / L1 regularization；无 class weighting；无 pseudo-count；无 hyperparameter search。

### 8.5 Why no R3-style L2 axis

`B-beta` 是单一 family-extension procedure，**不**与 `low` / `historical` 交叉，
不创建 `B-low` / `B-historical`。R4 family-extension 目标是 distinct parametric family，
不是另一个 factorial。

### 8.6 TRAIN endpoint policy

exact TRAIN score `s == 0` 或 `s == 1` 使该 fitting block 状态为
`INELIGIBLE_ENDPOINT`（`ln(s)` / `ln(1-s)` feature 在 exact endpoint 不 finite）。
硬禁止：epsilon clipping、`nextafter` replacement、`1e-6` / `1e-12` substitution、row dropping。
fitting data 中一个 exact endpoint 即足以让该 fit block 失败。

### 8.7 Application endpoint policy

成功拟合的 finite beta map 由其 exact mathematical limits 扩展到 `[0, 1]`：

```text
s = 0:  a > 0  -> f(0) = 0
        a == 0 -> f(0) = sigmoid(c)
s = 1:  b > 0  -> f(1) = 1
        b == 0 -> f(1) = sigmoid(c)
```

无 epsilon approximation。

### 8.8 Out-of-source-support behavior

与 isotonic 不同：`B-beta` **不** clip 到 observed source TRAIN min/max。
任何 `0 < s < 1` 都直接套用 fitted parametric formula，即使 `s < min(source TRAIN)`
或 `s > max(source TRAIN)`。这是 parametric extrapolation inside `[0,1]`，属于 F identity。

### 8.9 Fitting eligibility（ordered hard gates）

B-beta fitting eligibility 按下列**固定顺序**判定；任何一步失败即返回对应状态，
无 fallback：

```text
1. fitting set 非空
2. score finite 且位于概率域 [0, 1]
3. score 严格 interior（0 < s < 1），否则 INELIGIBLE_ENDPOINT
4. label 为 binary 0/1
5. 同时存在 Y=0 与 Y=1，否则 BETA_FIT_INELIGIBLE_SINGLE_CLASS
6. exact distinct interior score 数量 >= 3，
   否则 BETA_FIT_INELIGIBLE_INSUFFICIENT_DISTINCT_SCORES
7. 无 increasing monotone separation，
   否则 BETA_FIT_INELIGIBLE_MONOTONE_SEPARATION
8. constrained optimization
9. unique finite accepted optimum
```

**8.9.1 Identifiability。** 三参数 transformed design `(1, ln s, -ln(1 - s))` 必须
可识别，因此 distinct score 数量必须 `>= 3`。**禁止** silent reduction 到
two-parameter beta、固定 `a` 或 `b`、或 fallback 到 logistic regression。

**8.9.2 Distinctness 是 exact。** distinctness 定义为 exact binary64 score
equality。无 tolerance-based merging、无 rounding、无 binning、无 epsilon。
Isotonic 的 tie rules 独立且不变。

**8.9.3 Monotone separation。** 在确认 both classes 存在且 `>= 3` distinct
interior scores 之后计算：

```text
max_negative = max{s_i : Y_i = 0}
min_positive = min{s_i : Y_i = 1}
```

若 `max_negative <= min_positive`，则 `BETA_FIT_INELIGIBLE_MONOTONE_SEPARATION`。
理由：在 `a >= 0, b >= 0` 下 beta map non-decreasing，该条件代表 family 所能
表达方向上的 complete / quasi-complete monotone separation，unregularized finite
MLE 不保证存在。无 regularization rescue。

**8.9.4 Reversed orientation 不是同一 failure rule。** **不得**仅因为
`max_positive <= min_negative` 就宣告 monotone-separation failure。这是反向
orientation；由于声明的 family 约束为 increasing calibration map，它不能通过
负斜率利用 decreasing separator。此类数据仍可能产生 finite boundary optimum
（例如 `a = 0` 和/或 `b = 0`），必须交给 constrained optimizer 处理。

### 8.10 Finite optimum requirement

valid fitted procedure 要求 finite `a`、finite `b`、finite `c`，`a >= 0`、`b >= 0`，
且存在 **a unique finite constrained optimum accepted under the later frozen
numerical KKT/convergence contract**。若不存在：`FIT_FAILURE`。无 fallback 到
regularized beta、ordinary logistic、`beta[a=b]`、identity 或 constant map。

Gate A 之前的措辞为 "certified finite constrained optimum"；该措辞过于宽泛，
现按上述精确语言记录。solver 与 tolerance 的具体数值仍属于 implementation
provenance（见 §8.11 与 Gate C）。

### 8.11 Solver status

本 gate **不**选择最终 numerical optimizer。Scientific identity 只固定
objective、constraints、parameters、endpoint policy、failure behavior。
后续 implementation gate 必须在 study execution 前选定并冻结 deterministic solver +
convergence certificate。solver choice 属于 provenance，除非其变化改变声明的优化问题。

### 8.12 Regularization / hyperparameter

```text
regularization_rule : no-regularization v1   (l2_strength = null)
hyperparameter_rule : no-hyperparameter v1
```

---

## 9. Exact output clipping rule — all six procedures

无 post-calibration epsilon clipping。任何 calibrator 若数学/数值上返回 `0.0` 或 `1.0`，
该 exact output 被保留。Brier 对 `q ∈ [0,1]` 永远 finite。
Exact LogLoss（secondary）在 prediction 对 observed outcome 赋零概率时
为 `+infinity`，**不得**用 epsilon clipping 替换。

## 10. LogLoss role

```text
PRIMARY metric   : Brier
SECONDARY metric : exact LogLoss
```

若后续遇到 infinite exact LogLoss，必须 exact 报告，不得触发 hidden clipping 或结果删除。

---

## 11. Procedure-family architecture

```text
CONTINUITY CORE : P-low / P-historical / L-low / L-historical（保留 R3 2×2 结构）
FAMILY EXTENSIONS: I-isotonic / B-beta（standalone predeclared procedures）
```

不构造假的 `3-family × regularization × feature` factorial。

## 12. Estimands remain unchanged

```text
Deployment delta  = R_cross - R_raw
Transport penalty = R_cross - R_native
```

两者保持区分，不合并为 transport success / transport failure。

## 13. Multiplicity is NOT frozen in this task

本 gate 不决定 Bonferroni family size、alpha split、bootstrap tail probability、
omnibus testing 或 meta-analysis。本 gate 只声明：

```text
R3 four-logistic continuity core 与两个 standalone family-extension procedures
不得被静默 pool 进一个假 factorial。
```

## 14. TRAIN-refit stability doctrine

沿用 R3 conservative principle：对任意 procedure / model / population / measurement block，
若后续 preregistered TRAIN-refit bootstrap 出现 fitting failures，
**不得**只从 successful subset 计算 interval；受影响 block 状态为 `INCOMPLETE`。
exact bootstrap design/count 留待后续 inference closure。

## 15. No rescue rules

若 `I-isotonic` 或 `B-beta` 在 primary N=456 上失败，不得自动改用 N=912 作为 primary；
912 角色固定为 `SECONDARY SAMPLE-SIZE ROBUSTNESS`。同样，beta 失败不提升 isotonic，
反之亦然。

---

## 16. Candidate machine-readable spec

`experiments/calibration_transport/R4_CALIBRATION_FAMILY_SEMANTIC_CANDIDATE.json`

结构：

```text
artifact_type = r4-calibration-family-semantic-candidate
artifact_version = 1
status = SEMANTIC CANDIDATE / NOT FROZEN / NO STUDY FITTING / NO EXECUTION AUTHORIZATION
r3_continuity   : design path / protocol id / protocol fingerprint / 四个 procedure entry
                  （expected + declared + actual fingerprint + match + exact inherited payload）
candidate_procedures : I-isotonic、B-beta（fingerprint + complete candidate payload）
semantic_probes : isotonic / beta / row_order_determinism
```

无 timestamp、无 host/path metadata、无 random id → 重复运行 byte-identical。

candidate fingerprints（Gate A 完成后）：

```text
I-isotonic : cd13bc07bf92f3375bcd16d57fa5f515cd40f68199b57181791f85c58be8c244
             （Gate A 前后不变）

B-beta     : f4b710fb98f7c3056794aa709d53309f462a8f598cef8089d2f9c0ed6f7e37ff
             （Gate A 前为 d7ee7aa9b4c611866ddedfcf66cf8735882324f4f20be9706a8637291feddfb5，
              因新增 identifiability / distinct-score / monotone-separation /
              reversed-orientation / finite-optimum 语义而必须改变）
```

## 17. Synthetic semantic probes

全部使用 synthetic arrays，无 benchmark-derived number。

### 17.1 Isotonic

| probe | 结果 |
| --- | --- |
| strictly increasing distinct scores | non_decreasing = true |
| repeated exact scores | first threshold 恰为 exact mean（2/3）= true |
| monotonicity violation requiring pooling | 全部 pool 成单值 = true |
| all scores equal | constant at positive fraction（2/3）= true |
| all Y = 0 | constant 0 = true |
| all Y = 1 | constant 1 = true |
| target below TRAIN min | constant at boundary = true |
| target above TRAIN max | constant at boundary = true |
| exact input 0 | constant at boundary = true |
| exact input 1 | constant at boundary = true |
| interior midpoint | piecewise-linear 0.5 = true |
| no parametric extrapolation | true |
| grid monotonicity / range | non_decreasing = true；output ∈ [0,1] = true |

### 17.2 Beta

| probe | 结果 |
| --- | --- |
| identity map `a=1,b=1,c=0` | identity_holds = true（max abs error 1.11e-16） |
| monotonicity under `a>=0,b>=0` | non_decreasing = true |
| endpoint limits | 四种情形全部成立（`a>0→0`；`a==0→sigmoid(c)`；`b>0→1`；`b==0→sigmoid(c)`） |
| parametric application outside synthetic TRAIN range | no_clip_below = true；no_clip_above = true |
| negative `a` / `b` rejected | 两对均被 candidate validation 拒绝 = true |
| objective finite for interior inputs | finite = true（objective 1.1390950054546647） |
| endpoint TRAIN inputs rejected | `0.0` 与 `1.0` 均为 `INELIGIBLE_ENDPOINT` = true |
| single-class eligibility | all-zero / all-one → `BETA_FIT_INELIGIBLE_SINGLE_CLASS`；mixed（仅 2 distinct scores）→ `BETA_FIT_INELIGIBLE_INSUFFICIENT_DISTINCT_SCORES` |
| insufficient distinct support | 1 distinct interior score → `BETA_FIT_INELIGIBLE_INSUFFICIENT_DISTINCT_SCORES`；2 distinct → 同；3 distinct → `ELIGIBLE` |
| increasing complete separation | → `BETA_FIT_INELIGIBLE_MONOTONE_SEPARATION` |
| increasing quasi separation（共享边界 score 同时含两类） | → `BETA_FIT_INELIGIBLE_MONOTONE_SEPARATION` |
| reversed orientation | state = `ELIGIBLE`；not pre-rejected = true |
| interleaved labels | → `ELIGIBLE` |
| eligibility gate order | endpoint 先于 single-class；single-class 先于 insufficient-support；insufficient-support 先于 separation |

### 17.3 Row-order determinism

synthetic input 以 as-given / reversed / rotated 三种固定排列输入：

```text
thresholds identical across orderings = true
candidate fingerprint identical       = true
predictions identical                 = true
beta eligibility identical            = true
```

（无 RNG；仅显式固定排列。）

---

## 18. Literature cross-check

```text
LITERATURE FACT
```

Beta：

```text
Kull, Silva Filho & Flach (AISTATS 2017)，full beta calibration map
features ln(s) 与 -ln(1-s)，三个参数 a, b, c，monotonicity 通过 a, b >= 0
```

Isotonic：

```text
non-decreasing 1D isotonic regression，PAVA-compatible empirical fit
```

Literature 只提供 candidate design 依据，**不**override frozen R3 identity。

### 18.1 LITERATURE FACT vs R4 CANDIDATE DESIGN CHOICE

以下为 **R4 CANDIDATE DESIGN CHOICE**，不是“所有文献都如此规定”的断言：

```text
piecewise-linear isotonic interpolation
nearest-boundary support extension
beta endpoint fitting rejection
exact beta endpoint limit application
no beta regularization
no probability clipping
```

---

## 19. Static R3 preservation audit

未修改任何 frozen R3 artifact：

```text
experiments/calibration_transport/r3_protocol.py        UNCHANGED
experiments/calibration_transport/r3_protocol_design.json UNCHANGED
experiments/calibration_transport/r3_analysis.py        UNCHANGED
src/probvenance/calibration.py                          UNCHANGED
R3 result artifacts                                     UNCHANGED
```

`git diff --name-only` 与 `git diff --cached --name-only` 均为空。

## 20. No population modification

未修改 `R4_POPULATION_FREEZE.md`、population manifests 或 `r4_population_candidate.py`。

## 21. No study-data access

本 gate 不需要任何 R4 dataset row：未读 MMLU / HellaSwag / MedMCQA row，
未读 model measurement output。仅允许读取 population identity metadata。

---

## 22. Tests

```text
py_compile  : PASS（exit 0）
ruff check  : All checks passed!（exit 0）
pytest -q   : PASS（exit 0）
```

## 23. Key invariants

```text
Does beta contain identity map?                    YES
Is beta monotone under declared constraints?       YES
Does beta clip to source support?                  NO

Does isotonic accept p=0/1?                        YES
Does isotonic extrapolate parametrically?          NO
Does isotonic use constant support-boundary extension? YES

Does beta require >= 3 exact distinct interior scores? YES
Is beta distinctness tolerance-based?              NO（exact binary64 equality）
Does beta reject increasing monotone separation?   YES
Does beta treat reversed orientation as that failure? NO
Is beta silently reduced to a 2-parameter family?  NO

Is any epsilon clipping used?                      NO
Is any procedure given extra fitting data?         NO
```

## 24. Scientific guardrails

```text
model load                : NO
model inference           : NO
study dataset rows        : NO
real calibration fitting  : NO
Brier result              : NO
LogLoss result            : NO
transport result          : NO
predictor result          : NO
R3 modification           : NO
population modification   : NO
```

## 25. Open items after this gate

本 gate 不自动解决：

```text
final numerical beta solver
solver convergence tolerance
production isotonic implementation
TRAIN-refit bootstrap count
TEST bootstrap architecture
cluster bootstrap
multiplicity
family-extension hypothesis adjustment
predictor inference
```

这些需要后续 human-reviewed gates。

## 26. Gate conclusion

```text
CALIBRATION-FAMILY SEMANTIC CANDIDATE:
PASS

R3 CONTINUITY:
EXACT

I-ISOTONIC:
SEMANTICALLY SPECIFIED

B-BETA:
SEMANTICALLY SPECIFIED
（Gate A 完成：identifiability / distinct-score / monotone-separation /
reversed-orientation / precise finite-optimum 语言已补齐）

READY FOR HUMAN SEMANTIC-FREEZE REVIEW

NOT FROZEN
NO STUDY FITTING
NO COMMIT
NO PUSH
```

## 27. Artifact hashes

```text
experiments/calibration_transport/r4_calibration_family_semantic_audit.py
  lines  = 694
  sha256 = 5111d16504de9627a859ab4a4d305f8329cded0f817142b1e8b7ec485941f13d

experiments/calibration_transport/R4_CALIBRATION_FAMILY_SEMANTIC_CANDIDATE.json
  lines  = 469
  sha256 = 41eaf954cfd29eb870d75e59feae34a1af1700b0c0ba3f3984d713bbcc549fe4
```

本报告自身的 sha256 不在文件内自引用（self-reference 不稳定），在最终汇报中给出。
