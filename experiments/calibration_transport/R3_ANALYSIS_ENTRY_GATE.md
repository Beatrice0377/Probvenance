# R3 Analysis-Entry Gate

Status of the R3 pre-analysis protocol-conformance closure.

This record is **append-only**. It does not modify the frozen R3 scientific
design, the frozen population, the frozen measurement code, or any raw
measurement artifact.

```text
raw evidence:                         PRESERVED / BYTE-FROZEN
model rerun:                          NOT REQUIRED
population rebuild:                   NOT REQUIRED
frozen protocol redesign:             NOT PERFORMED
official confirmatory statistical analysis:  NOT RUN
analysis implementation:              CORRECTED TO FROZEN SEMANTICS
analysis provenance omission:         CLOSED APPEND-ONLY
analysis-entry authorization:         STILL REQUIRES HUMAN RE-AUDIT
```

## 1. Why this gate exists

Official R3 raw measurements already exist (measurement code commit
`8b1ea40aee0e7518c2ab3b25a8cc6d4ec2d0f800`; raw-evidence commit
`ba90a6c325b764347feaa5ba9cc5b8956d36cb21`). Before any official confirmatory
statistical analysis is run, four pre-analysis implementation/provenance
mismatches against `R3_PROTOCOL.md` were identified and closed. No R3
statistical outcome was computed to make or verify these corrections.

## 2. Identities held fixed

```text
R3 protocol fingerprint:       3ef63056ae16b18ad65d9c87d1fbec5b43550873a0e3e25ec0a323f954ee974d
population manifest fingerprint: 40cc9753a711314ff3b25ed6e234d0cbda11f3f60cd87f1d3915195a3d1780b8
protocol design commit:        3a929a6931762a518498ad9df2e5f82cf6e6deed
pre-outcome population fix:    12f602a9527f0db4b1575abe6999235a40d55ef6
measurement code commit:       8b1ea40aee0e7518c2ab3b25a8cc6d4ec2d0f800
raw evidence commit:           ba90a6c325b764347feaa5ba9cc5b8956d36cb21
analysis conformance fix:      5829a8650c826c2521ce3287764d3f83b582f015
```

Raw artifact byte identities (unchanged, recomputed after correction):

```text
r3-raw-minicpm5-2b-mmlu-v1.json
  SHA256:               e7b45e921d35523f9fb6aabaefe10e585f43f35f25e5e4159bb2211cec8b999b
  evidence fingerprint: 726bb8340aecfa0c98e4d4b7fe1548278f3cc8ff391b9f6d14aa5215e84d7c71

r3-raw-qwen35-2b-mmlu-v1.json
  SHA256:               00a1d04e6cb308cf609ccf3cde69b761497c4a3a110704ea069f3e933cf9248a
  evidence fingerprint: 378b2676dad4b12be4d57c9030c9d44823df921dc62f4d9b7f73acf79f0d4887

r3-raw-evidence-index-v1.json
  SHA256:               b04351acd878161d21022f3e5f5f08da1443977a484f62c8ba465adba051c461
  internal fingerprint: 25fa4086e67a1cbd48cb8d857337092b132790ceb04925407649629c35d1bc51
```

Machine-readable closure record:
`experiments/calibration_transport/results/r3-analysis-entry-lineage-v1.json`.

## 3. Corrections (each recorded separately)

### 3.1 Missing historical analysis-code provenance

`R3_PROTOCOL.md` §20 requires official raw evidence provenance to record the
analysis code commit. The committed raw evidence and raw index omitted it.

A Git blob audit across the four commits `3a929a6`, `12f602a`, `8b1ea40`,
`ba90a6c` establishes that:

```text
experiments/calibration_transport/r3_analysis.py
  blob = bf527f71160cdc5c5501cbdb27a5b8edf3bc782f   (all four commits)

experiments/calibration_transport/tests/test_r3_analysis.py
  blob = 8c70ab202380bf61a74e6bd93b4045907503d0fa   (all four commits)
```

Therefore the pre-outcome analysis implementation existed at the R3 design
freeze and was committed unchanged through measurement and the raw-evidence
commit. The historical analysis code commit is:

```text
analysis_code_commit = 3a929a6931762a518498ad9df2e5f82cf6e6deed
```

The omission is closed **append-only**: the byte-frozen raw artifacts are not
rewritten; the value is recorded in the separate addendum.

### 3.2 Cross application semantics

Frozen R3 definition (§10): `R_cross(A->B;F) = loss(g_F^A(S_B_i), Y_i)`, i.e. the
SOURCE-fitted calibrator is applied to the TARGET measurement score.

The pre-correction implementation applied the SOURCE calibrator to the SOURCE
score (`g_A(S_A)`). This is corrected to `g_A(S_B)` at every cross prediction
path through one centralized helper. Audited and corrected paths: cross Brier
loss, cross exact LogLoss, cross reliability diagnostics, range-loss
decomposition, TEST bootstrap contrasts, and TRAIN-refit evaluation.

The correction does **not** erase legitimate source-score use: the SOURCE TRAIN
score distribution remains the source measurement for empirical score geometry
and for the range-decomposition boundary.

### 3.3 Empirical support / score geometry

Frozen R3 requires source TRAIN ranges and TARGET TEST fractions outside them.
The pre-correction implementation derived the supposed source range from TEST
data. This is corrected to SOURCE TRAIN observed `[min, max]` and the required
source TRAIN 2.5–97.5% empirical quantile range, with TARGET TEST fractions
outside both ranges. Range-loss decomposition now uses the SOURCE TRAIN observed
`[min, max]` boundary and the frozen cross prediction `g_SOURCE(S_TARGET)`; its
already-declared cross-vs-raw contrast basis is unchanged.

Quantile-rule disclosure: the R3 text preregistered the 2.5–97.5% diagnostic but
did not separately name a second interpolation algorithm; the implementation
reuses the already-frozen R3 `nearest-rank-percentile` v1 rule before any
confirmatory statistical analysis was run. This is a secondary diagnostic
execution clarification; it does not alter primary inference.

### 3.4 TRAIN-refit draw count

Frozen `R3_PROTOCOL.md` §17 requires, within each subject, resampling 10 TRAIN
item positions with replacement per replicate. The final R3 population has 8
TRAIN observations per subject, which does not prevent 10 draws because the
sampling is with replacement. The pre-correction implementation drew
`len(members)` = 8. It is corrected to exactly 10 draws per subject, with the
same deterministic frozen draw mechanism and the same resampled paired records
feeding CAT and OVR fitting.

## 4. Non-selection statement

None of these corrections was selected based on observed R3 statistical results.

No R3 Brier result, LogLoss result, calibration fit result, primary factorial
contrast, bootstrap interval, native-reference state, accuracy aggregate, or
probability-distribution summary was computed as part of this task.

## 5. Scope boundaries

The following remain unchanged and frozen: population, manifest membership,
dataset revision, model IDs and revisions, measurement identities, anchor
procedure, `Y` definition, target and input semantics, `F` panel, procedure
family, feature transforms, lambda values, objective, regularization rule,
endpoint policy, primary directions and baseline and estimands, the six primary
hypotheses, subject weighting, the TEST bootstrap protocol (20,000 replicates,
m=6 / m=8, Bonferroni tails), Qwen replication role, primary/replication
separation, missingness and failure policy, and the interpretation contract.

No new measurement family, model, population, `F`, lambda, hypothesis,
compatibility rule, primary metric, conditional-relation-shift hypothesis,
method selection, or post-hoc winner selection was introduced.

## 6. Gate outcome

```text
IMPLEMENTATION / LINEAGE CLOSURE COMPLETE

RAW EVIDENCE PRESERVED

OFFICIAL R3 CONFIRMATORY ANALYSIS:
NOT RUN

NEXT GATE:
HUMAN RE-AUDIT BEFORE ANALYSIS AUTHORIZATION
```

This record does not authorize the R3 confirmatory analysis. Analysis-entry
authorization still requires human re-audit.
