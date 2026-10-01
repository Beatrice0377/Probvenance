# R4 Clone-Instance Revalidation Audit

```text
status = PASS
scope  = operational (clone-instance integrity)
```

本文件记录 **服务器实例整体克隆之后** 的机械核对结果。clone 不能假设自动保持全部
运行时状态，因此在任何 further engineering action 之前必须重新验证 repo / branch /
remote / environment / GPU / filesystem / HF cache / frozen authority hashes。

本文件 **不是** scientific artifact，不参与任何 evidence fingerprint。

---

## 1. Git clone-state audit

```text
repo:                 /root/rivermind-data/Probvenance
branch:               main
HEAD:                 55a396a9e0339f29becb8fae2821d2bf8031a54a
HEAD^:                aaea894803d5b2981998554a04316033a1f867a8
origin/main:          55a396a9e0339f29becb8fae2821d2bf8031a54a
raw behind/ahead:     0 / 0
normalized ahead/behind: 0 / 0
merge-base --is-ancestor origin/main HEAD: exit 0
worktree:             clean
remote:               git@github.com:Beatrice0377/Probvenance.git
```

`HEAD`、`HEAD^`、`origin/main` 与 human / ChatGPT 已核验的 remote authority 完全一致。
未执行 pull / merge / rebase / reset / cherry-pick / stash / amend；`git fetch --prune`
仅用于核对 remote metadata。

```text
CLONE_GIT_STATE = PASS
```

---

## 2. Filesystem / path audit

```text
hostname:             jupyter-57dh93bsn4nfr6nt
                      （上一实例为 jupyter-catzwrjrv7td06p3 → 确认是 clone 后的新实例）
```

必需路径全部存在且可读：

```text
/root/rivermind-data                             exists
/root/rivermind-data/Probvenance                 exists
/root/rivermind-data/envs/probvenance-r4         exists
/root/rivermind-data/hf-cache                    exists
/root/rivermind-data/hf-cache/hub                exists
/root/rivermind-data/r4-population-candidates    exists（4 manifests 全部在位）
```

磁盘：

```text
/root/rivermind-data: total 246G  used 67G  available 179G  (28% used)
inodes:               total 16384000  used 1%
```

frozen population manifest 的实际路径 authority 未因 clone 变化，因此未做任何路径修改。

```text
CLONE_FILESYSTEM_LAYOUT = PASS
```

---

## 3. Python environment audit

```text
env:            /root/rivermind-data/envs/probvenance-r4
python:         3.11.13
torch:          2.8.0+cu128   (torch.version.cuda = 12.8)
transformers:   5.17.0
huggingface_hub: 1.32.0
scipy:          1.16.3
numpy:          2.3.2
cuda_available: True
device_count:   1
device_name:    NVIDIA GeForce RTX 4090
```

与 frozen R4 measurement environment 一致；未执行 pip install / upgrade / downgrade /
conda mutate。

```text
CLONE_RUNTIME_ENVIRONMENT = PASS
```

---

## 4. GPU audit

```text
nvidia-smi driver:        580.119.02
nvidia-smi CUDA compat:   13.0（驱动标称；torch runtime 仍为 cu128，两者不可混淆）
GPU:                      NVIDIA GeForce RTX 4090
VRAM total:               49140 MiB
VRAM used:                0 MiB（空闲）
running processes:        none
authorized device path:   cuda:0（单一 GPU）
```

未启用 multi-GPU / tensor parallel / CPU offload。

```text
CLONE_GPU = PASS
```

---

## 5. Frozen authority re-hash

重新计算 sha256，全部与 frozen authority 一致：

| artifact | sha256 |
|---|---|
| `R4_POPULATION_FREEZE.md` | `850b6b24…` |
| `R4_CALIBRATION_FAMILY_FREEZE.md` | `1fd06ad4…` |
| `R4_INFERENCE_MULTIPLICITY_FREEZE.json` | `fdc07904…` |
| `R4_PREDICTOR_FREEZE.json` | `423c5cda…` |
| `R4_MEASUREMENT_EXECUTION_CONTRACT.json` | `c9d61ed3…` |
| `R4_FINAL_PROTOCOL_FREEZE.json` | `8d105b20…` |
| `R4_EXECUTION_MANIFEST_FREEZE.json` | `8b56f62b…` |
| `r3_protocol.py` | `46a7c0ec…` |
| `r3_protocol_design.json` | `cb54090f…` |

关键 fingerprint 全部精确重算：

```text
measurement_contract_fingerprint  = 7b126d300e774cb44d2c47fcb12513865d03c2b08ffd03a5ce409b2ea976e1e5
final_protocol_fingerprint        = d1b56d702e1f260cef47eee05b7d878ace07a15168e89408e15e7eb741c0ad34
execution_manifest_fingerprint    = f32381c51db24f5dbeb240b5e0fdf73c59a56a615c8607ad8979e2a7e2586775
inference freeze_fingerprint      = dcbb7ac9e931145fdee86ab984de1249c1b86ca36ee735b70dafc8cabc06c141
predictor freeze_fingerprint      = c856fcc161910497a3431593639606682905adcb50fc443455468dfc295d73a9
```

```text
CLONE_FROZEN_AUTHORITY = PASS
```

---

## 6. Outcome firewall

本 audit 只读取结构 manifest 与 frozen identity；未读取或产生任何 real study
logits / probabilities、real CAT/OVR evidence、calibration fit、Brier、LogLoss、
delta、predictor value 或 official result。

```text
OUTCOME_FIREWALL = INTACT
```

---

## 7. Status

```text
R4 CLONE-INSTANCE REVALIDATION = PASS
```
