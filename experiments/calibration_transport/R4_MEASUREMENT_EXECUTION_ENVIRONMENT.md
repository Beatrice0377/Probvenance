# R4 Measurement Execution Environment

```text
status : EXACT ENVIRONMENT CONTRACT (verified on disk at task time)
scope  : the environment in which formal R4 measurement execution must run
```

本文件记录 **R4 formal measurement execution 的 exact environment contract** 及其来源。

它 **不** 使用 R3 historical environment 作为 R4 execution authority。

---

## 1. Why R3 environment is NOT the R4 authority

`experiments/calibration_transport/run_r3_measurements.py` 的 environment gate 是
**R3-only**，绑定了另一台机器：

```text
EXPECTED_TORCH_VERSION          = "2.14.0+cu130"
EXPECTED_CUDA_RUNTIME           = "13.0"
EXPECTED_GPU_NAME               = "NVIDIA GeForce RTX 5060 Laptop GPU"
EXPECTED_TRANSFORMERS_VERSION   = "5.17.0"
EXPECTED_HUGGINGFACE_HUB_VERSION= "1.32.0"
EXPECTED_PYTHON_MAJOR_MINOR     = "3.11"
EXPECTED_DTYPE                  = "bfloat16"
```

该 gate **不得** 被 R4 runner 继承。R4 的 authority 来自
**R4 engineering probe artifacts**（`R4_SMALL_FORWARD_ENGINEERING_PROBE.md`）
与 **R4 calibration implementation environment**（`R4_CALIBRATION_IMPLEMENTATION_ENVIRONMENT.md`）。

---

## 2. R4 execution environment contract

```text
env path      : /root/rivermind-data/envs/probvenance-r4
python        : 3.11.13
executable    : /root/rivermind-data/envs/probvenance-r4/bin/python
torch         : 2.8.0+cu128
torch cuda runtime : 12.8  (cu128)
transformers  : 5.17.0
huggingface_hub : 1.32.0
tokenizers    : 0.23.2
safetensors   : 0.8.0
numpy         : 2.3.2
scipy         : 1.16.3
dtype         : bfloat16
device        : cuda:0
batch size    : 1
```

GPU：

```text
device name   : NVIDIA GeForce RTX 4090
driver        : 580.119.02
capability    : (8, 9)
bf16 supported: True
VRAM total    : 49140 MiB
```

注意：

```text
nvidia-smi reported CUDA compatibility : 13.0
torch runtime CUDA                     : 12.8 (cu128)
```

两者 **不得混淆**。

---

## 3. Sources of the contract

| fact | source |
|---|---|
| torch 2.8.0+cu128 | `experiments/calibration_transport/R4_SMALL_FORWARD_ENGINEERING_PROBE.md:49, 395, 694, 1069` |
| transformers 5.17.0 | `R4_SMALL_FORWARD_ENGINEERING_PROBE.md:50, 396, 695, 1070` |
| huggingface_hub 1.32.0 | `R4_SMALL_FORWARD_ENGINEERING_PROBE.md:51, 397, 696, 1071` |
| device NVIDIA GeForce RTX 4090 | `R4_SMALL_FORWARD_ENGINEERING_PROBE.md:55, 1076` |
| dtype torch.bfloat16 / device cuda:0 | `R4_SMALL_FORWARD_ENGINEERING_PROBE.md:116-117, 459-460, 767-768, 1157-1158` |
| no multi-GPU / no CPU offload / no compile | `R4_SMALL_FORWARD_ENGINEERING_PROBE.md:127` |
| scipy 1.16.3 pin (additive only) | `experiments/calibration_transport/R4_CALIBRATION_IMPLEMENTATION_ENVIRONMENT.md` |
| python 3.11.13 | `R4_SMALL_FORWARD_ENGINEERING_PROBE.md` environment blocks; verified on disk |

---

## 4. R3 → R4 adapter continuity

| fact | R3 path | R4 path | match |
|---|---|---|---|
| backend constructor | `run_r3_measurements.py load_backend` | `r4_small_forward_probe.py` | different driver, same adapter |
| dtype | bfloat16 | bfloat16 | YES |
| rendering | `{"enable_thinking": False}` | `{"enable_thinking": False}` | YES |
| Qwen3.5 adapter | `Qwen35TextBackend` | `Qwen35TextBackend` | YES |

`EXPECTED_DTYPE = "bfloat16"`（`run_r3_measurements.py:72`）for `Qwen/Qwen3.5-2B`
（见 `R4_SMALL_FORWARD_ENGINEERING_PROBE.md:1427-1438`）。

---

## 5. No environment mutation

本任务：

```text
NO pip install
NO upgrade
NO downgrade
```

若现环境不满足上述 contract：

```text
STOP / R4_MEASUREMENT_ENVIRONMENT_DRIFT
```

不得自行修环境。

---

## 6. Offline policy

```text
local_files_only = True
formal run 时禁止自动下载模型
cache 缺失 -> STOP / MODEL_CACHE_MISSING
```
