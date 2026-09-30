# R4 Calibration-Family Implementation Engineering Record

Status: `SYNTHETIC-ONLY IMPLEMENTATION ENGINEERING / NOT A SCIENTIFIC RESULT`

This document records the production implementation engineering for the two R4
calibration families added on top of the frozen R3 continuity core:

```text
I-isotonic
B-beta
```

It is an engineering record. It contains no study-data result, no model
inference, no calibration fitting on a real R4 population, no Brier score, no
LogLoss, no transport result and no predictor result.

The frozen scientific semantics are recorded in
`experiments/calibration_transport/R4_CALIBRATION_FAMILY_FREEZE.md`. Nothing in
this document changes them.

---

## 1. Artifacts

```text
implementation:
experiments/calibration_transport/r4_calibration_families.py
lines:
660
SHA256:
e5b00548429b5b0999d5847db47e1f4c1ae113ee19854c053aeaca1058536ec3
```

```text
engineering tests:
tests/test_r4_calibration_families.py
lines:
703
tests:
53
SHA256:
e31f326d22a83678fd182f5847b82ba826f8d27d24c1c6008299603b0a95e5c1
```

```text
environment provenance:
experiments/calibration_transport/R4_CALIBRATION_IMPLEMENTATION_ENVIRONMENT.md
```

---

## 2. Frozen scientific identities

```text
I-isotonic scientific fingerprint:
cd13bc07bf92f3375bcd16d57fa5f515cd40f68199b57181791f85c58be8c244

B-beta scientific fingerprint:
f4b710fb98f7c3056794aa709d53309f462a8f598cef8089d2f9c0ed6f7e37ff
```

Both values are read back from the frozen semantic candidate artifact
`R4_CALIBRATION_FAMILY_SEMANTIC_CANDIDATE.json`, re-verified to hash from their
own payloads, and confirmed present in `R4_CALIBRATION_FAMILY_FREEZE.md`.

Implementation identity is deliberately separate from scientific identity:

```text
I-isotonic implementation id:
r4-isotonic-pava-linear-v1   (version 1)

B-beta implementation id:
r4-beta-active-set-bfgs-kkt-v1   (version 1)
```

SciPy version, NumPy version, CPU, iteration counts, wall-clock time and host
paths are recorded as implementation/solver provenance only. They are not part
of any frozen scientific fingerprint.

### 2.1 R3 continuity recheck

The four frozen R3 continuity fingerprints were mechanically recomputed from
the frozen R3 protocol definitions:

```text
protocol_id:
r3-confirmatory-procedure-conditioned-transport

protocol_fingerprint:
3ef63056ae16b18ad65d9c87d1fbec5b43550873a0e3e25ec0a323f954ee974d

all_match:
True
```

```text
P-low        7a8e13d51e131f2102cca4e00b172c8bbb2eb49e591acd3746aeb64d003c8857  match
P-historical a44e9217dd43e5e29d859c8dd2dc510a5876db4d46a8e0cc2fd4f1df3121a423  match
L-low        91d7d506275aade7d4676c39722ac2c4d975de7967a25a808395c056307ad619  match
L-historical 23ec12bbf4a809ba2f419491df80d1f228d3fd778d848115839aab3697f9dd58  match
```

R3 logistic mathematics was not cloned, refactored or reimplemented. The new
module neither imports nor rewrites the frozen R3 P/L kernels.

---

## 3. I-isotonic

```text
implementation id:
r4-isotonic-pava-linear-v1
```

### 3.1 Frozen semantics implemented

```text
raw score input
[0, 1] inclusive

item weighting
equal

monotone direction
increasing = True (hard)

tie handling
exact binary64 score equality aggregated; weight = count;
positive_count = sum(labels); mean = positive_count / count

aggregation order
deterministic ascending score order, no tolerance-based tie merge

fitting
weighted pool-adjacent-violators; adjacent blocks pooled while
left_mean > right_mean; pooled weight / positive_count / mean recomputed

thresholds
every unique observed score, ascending

application
below minimum  -> first fitted value (constant extension)
above maximum  -> last fitted value (constant extension)
exact threshold -> that threshold's fitted value
between        -> linear interpolation between consecutive thresholds

regularization
none

hyperparameters
none

output truncation
none
```

### 3.2 Validation behaviour

Accepted: exact score `0.0`, exact score `1.0`, all scores equal, all labels
`0`, all labels `1`, arbitrary row order.

Rejected with `IsotonicContractViolation`: empty dataset, length mismatch,
non-finite score (`nan`, `inf`), score below `0`, score above `1`, non-binary
label.

### 3.3 Engineering evidence

```text
synthetic cases exercised
strictly increasing fit, exact tie aggregation, full PAVA pooling,
partial PAVA pooling, all scores equal, all labels 0, all labels 1,
exact 0.0 and 1.0 inputs, constant extension below and above support,
linear interior interpolation, row reverse, fixed permutation,
invalid-input rejection, grid monotonicity, serialization determinism

max monotonicity violation over the audit grid (1001 points, 0.0 to 1.0)
0.0

fitted-state serialization
deterministic canonical payload

serialization determinism
two independent processes produced identical state bytes
```

---

## 4. B-beta

```text
implementation id:
r4-beta-active-set-bfgs-kkt-v1
```

```text
SciPy:
1.16.3

NumPy:
2.3.2

KKT acceptance tolerance (engineering candidate, not a change to scientific F):
1e-10
```

### 4.1 Frozen structural eligibility gates

Evaluated in exactly this order; the failure labels preserve the frozen names:

```text
1  non-empty dataset
2  finite score
3  0 < score < 1                       (exact 0 / 1 -> INELIGIBLE_ENDPOINT)
4  binary label
5  both classes present                 -> BETA_FIT_INELIGIBLE_SINGLE_CLASS
6  at least 3 exact distinct scores     -> BETA_FIT_INELIGIBLE_INSUFFICIENT_DISTINCT_SCORES
7  max{s : Y=0} <= min{s : Y=1}        -> BETA_FIT_INELIGIBLE_MONOTONE_SEPARATION
8  constrained numerical fit
9  unique finite accepted optimum
```

Reversed orientation (`max{s : Y=1} <= min{s : Y=0}`) is explicitly NOT the
monotone-separation rule and is not pre-rejected; it is accepted and is solved
as an ordinary constrained fit, which may land on a boundary optimum.

### 4.2 Frozen map

```text
interior score s
x1 = ln(s)
x2 = -ln(1 - s)
z  = a * x1 + b * x2 + c
f  = sigmoid(z)

constraints
a >= 0
b >= 0
```

```text
objective
mean Bernoulli negative log-likelihood, stable softplus per row
(softplus(-z) for Y=1, softplus(z) for Y=0), accumulated with math.fsum

regularization
none
```

```text
analytic gradient
residual r = sigmoid(z) - y
g_a = mean(r * x1)
g_b = mean(r * x2)
g_c = mean(r)
```

### 4.3 Active-set faces, fixed starts and solver

```text
FACE_INTERIOR   a free, b free, c free
FACE_A0         a = 0,    b free, c free
FACE_B0         b = 0,    a free, c free
FACE_A0_B0      a = 0,    b = 0,    c free
```

Exact zeros remain exactly `0.0`; tiny positive values are never snapped to
zero.

```text
fixed starts
FACE_INTERIOR  a=1, b=1, c=0
FACE_A0        b=1, c=0
FACE_B0        a=1, c=0
FACE_A0_B0     c = logit(mean of labels)

solver
scipy.optimize.minimize(method="BFGS", jac=analytic_gradient)

solver options
gtol = KKT_ACCEPTANCE_TOL / 100.0 = 1e-12
maxiter = 5000

no SLSQP, no Nelder-Mead, no stochastic optimisation, no random starts
```

The gradient tolerance is deliberately two orders of magnitude below the KKT
acceptance residual. This is a solver setting; it does not modify any score or
any prediction. Without it, BFGS's default `gtol` stops far short of the
acceptance residual and genuine optima are misclassified as rejected.

### 4.4 Acceptance, KKT residual and face selection

```text
KKT residual
r_a = abs(g_a)          if a > 0
r_a = max(0, -g_a)      if a == 0
r_b = abs(g_b)          if b > 0
r_b = max(0, -g_b)      if b == 0
r_c = abs(g_c)
residual = max(r_a, r_b, r_c)
```

A face candidate is accepted only if all parameters and the recomputed
objective are finite, the face validity holds, and the KKT residual is
`<= 1e-10`. `result.success` alone is never sufficient.

```text
solver status classification
SOLVER_SUCCESS                    -> SciPy reported success
SOLVER_WARNING_KKT_ACCEPTED       -> SciPy reported failure/precision loss
                                     but the candidate still meets the KKT threshold

face selection
lowest recomputed binary64 mean NLL among accepted faces

exact binary64 objective tie order
FACE_A0_B0 -> FACE_A0 -> FACE_B0 -> FACE_INTERIOR
```

SciPy status, message, `nit`, `nfev`, `njev`, KKT residual and whether the tie
order was used are all recorded on the fitted state.

### 4.5 Endpoint and out-of-support application

```text
s = 0
a > 0 -> 0.0
a == 0 -> sigmoid(c)

s = 1
b > 0 -> 1.0
b == 0 -> sigmoid(c)

interior
direct formula

outside the training source support
parametric evaluation, no truncation to the source support
```

No post-calibration truncation of any kind is applied. Exact `0.0` and `1.0`
are preserved as legal outputs; the downstream Brier score may therefore take
an exact `0` or `1`, and the exact LogLoss may be `+infinity`. That is the
frozen output policy.

### 4.6 Engineering evidence

All fixtures below are hand-written synthetic arrays. No study row, no model,
no tokenizer and no GPU was involved.

```text
FACE_INTERIOR   scores [0.1, 0.15, 0.3, 0.35, 0.9]
                labels [0, 0, 1, 0, 1]
                a = 2.9379782731120363
                b = 0.885530867495907
                c = 2.80443857132249
                objective = 0.3539425913910375
                KKT residual = 6.908201e-13
                solver status class = SOLVER_SUCCESS   (nit 29)

FACE_A0         scores [0.1 .. 0.9, 9 points]
                labels [1, 0, 1, 0, 1, 0, 1, 0, 1]
                a = 0.0
                b = 0.25916987152388365
                c = -0.0028993652297505555
                objective = 0.6832272871874611
                KKT residual = 1.474870e-13
                solver status class = SOLVER_SUCCESS   (nit 11)

FACE_B0         scores [0.02, 0.05, 0.08, 0.1, 0.2, 0.5, 0.9]
                labels [0, 0, 1, 1, 1, 1, 0]
                a = 0.38625223941502823
                b = 0.0
                c = 1.0848269083081472
                objective = 0.6571609025680762
                KKT residual = 1.053054e-12
                solver status class = SOLVER_WARNING_KKT_ACCEPTED
                (SciPy: "Desired error not necessarily achieved due to
                precision loss.", nit 12, accepted because KKT holds)

FACE_A0_B0      scores [0.1 .. 0.8, 8 points]
                labels [1, 1, 1, 0, 0, 0, 0, 0]
                a = 0.0
                b = 0.0
                c = -0.5108256237659907
                objective = 0.6615632381579821
                KKT residual = 3.469447e-17
                solver status class = SOLVER_SUCCESS   (nit 0)
```

```text
maximum accepted KKT residual across the four faces
1.053054e-12   (<= 1e-10)

face tie-break exercised
NO

analytic gradient vs central finite difference
step 1e-5, three manually chosen interior parameter vectors
max absolute discrepancy = 6.922060e-12   (criterion <= 1e-6)

alternative deterministic starts (uniqueness audit)
FACE_INTERIOR 4 starts  max parameter discrepancy 2.980993e-11
FACE_A0       3 starts  max parameter discrepancy 5.022982e-12
FACE_B0       3 starts  max parameter discrepancy 3.768852e-11
FACE_A0_B0    2 starts  max parameter discrepancy 5.107026e-14
max parameter discrepancy = 3.768852e-11   (criterion <= 1e-9)
max objective discrepancy = 1.110223e-16

monotonicity audit over the grid [0.001, 0.999], 997 points, per accepted face
max monotonicity violation = 0.0

identity-map application check
a = 1, b = 1, c = 0 applied at 0.25 returns 0.25

endpoint application checks
a > 0 -> f(0) = 0.0 ; b > 0 -> f(1) = 1.0
a == 0 -> f(0) = sigmoid(c) ; b == 0 -> f(1) = sigmoid(c)

out-of-support application check
fitted interior map evaluated at 0.001 and 0.999 returns the parametric
value, not the clamped support endpoint value

serialization determinism
two independent processes produced identical fitted-state bytes
```

### 4.7 Symmetric numerical-conditioning stress case

The fixture

```text
scores [0.2, 0.4, 0.6, 0.8]
labels [0, 1, 0, 1]
```

is exactly invariant under `score -> 1 - score` together with
`label -> 1 - label`. The objective is therefore exactly invariant under the
parameter involution `(a, b, c) -> (b, a, -c)`, and the unique constrained
optimum has `a == b` and `c == 0`.

This is a **SYMMETRIC NUMERICAL-CONDITIONING STRESS CASE**. It is not a
non-identifiable model, not a multiple-optimum case, and not a scientifically
degenerate beta fit. It is retained unchanged and is deliberately **not** used for
the ordinary uniqueness audit.

#### 4.7.1 Strict-convexity diagnostic (transformed design)

```text
X = [ln(s), -ln(1 - s), 1]  (4 rows)

X =
[[-1.60943791  0.22314355  1.        ]
 [-0.91629073  0.51082562  1.        ]
 [-0.51082562  0.91629073  1.        ]
 [-0.22314355  1.60943791  1.        ]]

rank              = 3
singular values   = 3.059393218692451, 1.444373223777695, 0.18742744523723226
condition number  = 16.32308019148471
```

Because `rank(X) == 3`, the finite Bernoulli-logistic objective has the
positive-definite Hessian `H = X^T W X / n` with `W_i = q_i (1 - q_i)` at any
finite accepted solution, and is therefore strictly convex. On the convex
feasible set `a >= 0, b >= 0` the finite constrained minimiser is unique. The
small parameter spread across alternative starts is numerical convergence
variation, not evidence of multiple scientific optima.

#### 4.7.2 Hessian at the production accepted solution

```text
active face        FACE_INTERIOR
a                  = 1.101790346363985
b                  = 1.101790346363985
c                  = -7.964413944055447e-17
objective          = 0.5688637414432074
KKT residual       = 7.929768e-14          (<= KKT_ACCEPTANCE_TOL)

H =
[[ 0.16219269 -0.08200017 -0.15203262]
 [-0.08200017  0.16219269  0.15203262]
 [-0.15203262  0.15203262  0.19224325]]

eigenvalues        = 0.001648138467019268, 0.0801925258700257, 0.43478797021646903
minimum eigenvalue = 0.001648138467019268   (> 0)
condition number   = 263.80548656376425
```

These are synthetic implementation-QA diagnostics; they never enter the
scientific fingerprint.

#### 4.7.3 Deterministic alternative starts

Frozen production start list for `FACE_INTERIOR`:
`(2.0, 2.0, 0.0)`, `(0.5, 0.5, 0.0)`, `(1.0, 1.0, -1.0)`, `(1.0, 1.0, 1.0)`.

```text
start (2.0, 2.0, 0.0)
  a = 1.1017903463649834   b = 1.1017903463649832   c =  1.969426e-16
  objective = 0.5688637414432074   KKT = 7.754214e-16   ACCEPTED

start (0.5, 0.5, 0.0)
  a = 1.1017903463649728   b = 1.1017903463649728   c = -6.937375e-17
  objective = 0.5688637414432074   KKT = 9.887924e-17   ACCEPTED

start (1.0, 1.0, -1.0)
  a = 1.1017903473938917   b = 1.1017903456589921   c =  2.082177e-09
  objective = 0.5688637414432074   KKT = 1.365231e-10   NOT ACCEPTED
  (SciPy: "Desired error not necessarily achieved due to precision loss.")

start (1.0, 1.0, 1.0)
  a = 1.1017903814663836   b = 1.1017903400191780   c =  2.179749e-08
  objective = 0.5688637414432074   KKT = 2.899619e-09   NOT ACCEPTED
  (SciPy: "Desired error not necessarily achieved due to precision loss.")

max objective spread across all four starts                = 0.0
max prediction spread across production-accepted starts,
  frozen grid [0.001, 0.999] (997 points)                 = 2.331468e-15
max prediction spread across all four starts (auxiliary)   = 5.332176e-09
  attained between the two starts the acceptance rule rejects,
  (1.0, 1.0, -1.0) and (1.0, 1.0, 1.0)
max raw parameter spread (preserved fact)                  = 3.510240e-08
  max over a, b, c of (max - min) across the four deterministic
  starts and the production accepted solution
max raw parameter spread across the four starts only       = 3.510141e-08
max KKT residual across all four starts (auxiliary)        = 2.899619e-09
```

#### 4.7.4 Gate results

The authoritative requirement is that the KKT threshold applies to the
**solutions the frozen production acceptance rule admits**:

```text
every production-accepted deterministic alternative solution:
    KKT residual <= 1e-10
```

It does not require every deterministic starting point to be driven to that
threshold.

Required gates:

```text
design rank == 3                                          PASS    (3)
Hessian minimum eigenvalue > 0                             PASS    (1.648138e-03)
production accepted solution KKT <= 1e-10                  PASS    (7.929768e-14)
every production-accepted alternative start KKT <= 1e-10   PASS    (2 accepted:
                                                                   7.754214e-16,
                                                                   9.887924e-17)
max objective spread across deterministic starts <= 1e-12  PASS    (0.0)
max prediction spread (production-accepted solutions)
  on the frozen grid <= 1e-8                               PASS    (2.331468e-15)
```

Auxiliary numerical-stress diagnostic — **NOT a production acceptance gate**:

```text
all-four-start maximum returned KKT          = 2.899619e-09
accepted starts                              = 2
rejected starts                              = 2
max raw parameter spread                     = 3.510240e-08
max prediction spread across all four starts = 5.332176e-09
```

The two rejected starts, `(1.0, 1.0, -1.0)` (`KKT = 1.365231e-10`) and
`(1.0, 1.0, 1.0)` (`KKT = 2.899619e-09`), are honestly recorded as rejected by
the frozen acceptance rule. That rejection is the frozen rule operating as
designed, not a closure failure: the frozen solver settings (`gtol`,
`maxiter`), the frozen deterministic start list, the frozen acceptance
tolerance and the fixture itself were all left unchanged, and no rejected
solution was relabelled as accepted. Both rejected starts still reach the
identical objective (`spread = 0.0`) and agree with the production accepted
solution to `5.296873e-09`.

The ordinary (non-symmetric, nondegenerate) uniqueness audit is unaffected and
still meets `<= 1e-9` (aggregate maximum parameter discrepancy
`3.768852e-11`). No acceptance tolerance, no scientific semantics and no
fixture were changed in order to make any audit pass.

---

## 5. No-clipping source scan

The implementation source was scanned for score/output clipping logic:

```text
tokens searched
epsilon, eps (word-bounded), nextafter, clip, 1e-6, 1e-12

matches
NONE
```

The `1e-10` KKT acceptance tolerance is deliberately excluded from the scan
because it never modifies a score or a prediction.

---

## 6. Determinism

```text
targeted implementation suite
run twice -> 53 passed both times

fitted-state serialization
10 fitted states (6 isotonic, 4 beta) serialised canonically in two
independent processes

combined state SHA256
d7e3b8f2194c0118c6befbb9db3b7454e9f2956f1d1b7d3c72e65c832127ae67
(identical across both processes)
```

---

## 7. Tests

```text
py_compile
PASS

ruff check (implementation and test file)
All checks passed!

targeted suite, tests/test_r4_calibration_families.py
53 passed, run twice

full repository suite
exit 0, no failures (1977 tests collected)
```

---

## 8. Scientific guardrails

```text
study dataset rows:                  NO
model load:                          NO
model inference:                     NO
real R4 calibration fitting:         NO
Brier:                               NO
LogLoss:                             NO
transport:                           NO
predictor:                           NO
population modification:             NO
scientific F modification:           NO
```

---

## 9. Import boundary

SciPy is imported only by
`experiments/calibration_transport/r4_calibration_families.py`.

`src/probvenance/calibration.py` remains free of `scipy` and `numpy` imports,
and the existing repository test that asserts this boundary still passes.

---

## 10. Status

```text
CALIBRATION-FAMILY SCIENTIFIC SEMANTICS:
FROZEN

I-ISOTONIC IMPLEMENTATION ENGINEERING:
PASS

B-BETA IMPLEMENTATION ENGINEERING:
PASS

SYMMETRIC STRESS CASE:
PASS   (required gates met under the accepted-solution interpretation;
        see 4.7.4.  The all-four-start KKT maximum 2.899619e-09, the
        accepted/rejected start counts 2/2 and the raw parameter spread
        3.510240e-08 are retained as an AUXILIARY NUMERICAL-STRESS
        DIAGNOSTIC, NOT a production acceptance gate.)

SCIPY IMPLEMENTATION PROVENANCE:
RECORDED

PRODUCTION IMPLEMENTATION:
READY FOR HUMAN PROVENANCE CLOSURE

R4 OVERALL:
NOT FULLY FROZEN

R4 EXECUTION:
NOT AUTHORIZED
```

The production implementation is unchanged by the provenance amendment and by
this closure: no solver setting, no acceptance tolerance, no fixed start, no
scientific semantic and no frozen artifact was modified. Only the synthetic
engineering test suite and this record were extended.

The KKT threshold in 4.7.4 is applied to the production-accepted solutions, as
adjudicated. The two starts that the frozen acceptance rule rejects remain
recorded as rejected, with their exact returned parameters, objective and KKT
residual; no rejected solution was relabelled as accepted.

The provenance closure commit records this record together with the
implementation and its synthetic engineering tests. No push is performed by
this task.
