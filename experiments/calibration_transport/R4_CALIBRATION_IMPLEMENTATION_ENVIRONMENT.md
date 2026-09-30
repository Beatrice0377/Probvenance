# R4 Calibration Implementation Environment Provenance

Status: `ENVIRONMENT PROVENANCE RECORD / NOT A SCIENTIFIC ARTIFACT`

This document records the environment change that the R4 calibration-family
implementation engineering gate required. It is provenance for the
implementation only.

```text
SciPy is implementation provenance.
It does not change frozen scientific procedure semantics.
```

The frozen calibration-family scientific semantics are recorded in
`experiments/calibration_transport/R4_CALIBRATION_FAMILY_FREEZE.md` and are
unchanged by anything in this document. No frozen fingerprint depends on a
SciPy version, a NumPy version, a CPU, an iteration count, a wall-clock time or
a host path (see `R4_CALIBRATION_FAMILY_FREEZE.md` §4).

---

## 1. Environment identity

```text
environment path:
/root/rivermind-data/envs/probvenance-r4

environment python:
/root/rivermind-data/envs/probvenance-r4/bin/python
```

```text
Python:
3.11.13
```

The environment is the dedicated R4 environment already used by the completed
R4 model engineering probes. It was not recreated and not rebuilt.

---

## 2. Baseline before mutation

Recorded before any package change:

```text
NumPy:
2.3.2

SciPy:
absent
```

```text
baseline pip freeze:
/root/rivermind-data/r4-env-pre-scipy-freeze.txt

lines:
182

SHA256:
3aedfdeb6d460d3e22c504b871db08914eebe0cb3cf62b15d4409e65db7425c2
```

The baseline freeze file lives on the data disk, outside the repository.

---

## 3. Authorized mutation

Human authority for this task was exactly:

```text
ADD:
scipy==1.16.3
```

No other dependency mutation was requested or performed. In particular,
`scikit-learn`, `pandas`, `statsmodels`, `jax` and `cvxpy` were not installed,
`pip` was not upgraded, and the environment was not recreated.

### 3.1 Dry run

```bash
/root/rivermind-data/envs/probvenance-r4/bin/python \
  -m pip install \
  --dry-run \
  "scipy==1.16.3"
```

Observed proposal:

```text
Would install scipy-1.16.3
```

The existing `numpy 2.3.2` was recognised as already satisfying the SciPy
dependency (`numpy<2.6,>=1.25.2`). No upgrade, downgrade or replacement of any
existing package was proposed.

### 3.2 Binary wheel requirement

```text
installation must use a binary wheel
no source build of SciPy
```

```bash
/root/rivermind-data/envs/probvenance-r4/bin/python \
  -m pip install \
  --only-binary=:all: \
  "scipy==1.16.3"
```

Observed:

```text
Successfully installed scipy-1.16.3

wheel:
scipy-1.16.3-cp311-cp311-manylinux2014_x86_64.manylinux_2_17_x86_64.whl

wheel size:
35.9 MB

exit code:
0
```

---

## 4. Post-install audit

```text
NumPy:
2.3.2

SciPy:
1.16.3

SciPy path:
/root/rivermind-data/envs/probvenance-r4/lib/python3.11/site-packages/scipy/__init__.py
```

```text
post-install pip freeze:
/root/rivermind-data/r4-env-post-scipy-freeze.txt

lines:
183

SHA256:
2c29a961648f3c6450f030ca2f6a9761405e4cc1d1750d3f3286c9315d75fd03
```

---

## 5. Package diff

```text
diff pre-install -> post-install
```

```text
151a152
> scipy==1.16.3
```

The diff is exactly one added line. No existing package version changed, no
package was removed, and no package was replaced.

```text
EXISTING PACKAGE VERSIONS CHANGED:
NO
```

---

## 6. Why SciPy is needed

The frozen B-beta procedure requires a constrained numerical optimum over the
active-set faces `FACE_INTERIOR`, `FACE_A0`, `FACE_B0`, `FACE_A0_B0`, solved
with deterministic BFGS from fixed starts. SciPy supplies that deterministic
optimiser.

SciPy is used only inside

```text
experiments/calibration_transport/r4_calibration_families.py
```

It is deliberately NOT imported by the frozen core calibration module
`src/probvenance/calibration.py`. That module remains free of SciPy, NumPy,
scikit-learn, torch and transformers imports, and the existing repository test
that asserts this boundary still passes.

---

## 7. Reproduction

```bash
/root/rivermind-data/envs/probvenance-r4/bin/python -V
/root/rivermind-data/envs/probvenance-r4/bin/python -c \
  "import numpy, scipy; print(numpy.__version__, scipy.__version__)"
/root/rivermind-data/envs/probvenance-r4/bin/python -m pip freeze
```

---

## 8. Status

```text
SCIPY IMPLEMENTATION PROVENANCE:
RECORDED

FROZEN SCIENTIFIC PROCEDURE SEMANTICS CHANGED:
NO

R4 EXECUTION:
NOT AUTHORIZED
```
