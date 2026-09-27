"""Official R3 raw -> analysis ingestion and execution runner (frozen candidate).

This harness is the only sanctioned bridge between the byte-frozen R3 raw
confirmatory evidence and the already-frozen R3 analysis kernel
(``r3_analysis``). It loads the frozen protocol design, the frozen population
manifest, the committed raw-evidence index, and the two byte-frozen raw
artifacts; it verifies bytes, fingerprints, and structure; it maps each raw row
onto exactly one ``R3Item`` and, for the fixed TEST population, exactly one
``R3WinnerRecord``; and it assembles the two declared model conditions in frozen
order.

It reimplements no statistic. Brier, LogLoss, calibration fitting, the factorial
contrasts, the TEST bootstrap, the native-reference assessment, the TRAIN-refit
stability, and the winner/support diagnostics live exclusively in
``r3_analysis``. The runner transports the kernel's artifact; it never
interprets it.

Two mutually exclusive modes exist:

* ``--validate-inputs-only`` performs byte / structural / wiring preflight and
  emits a STRUCTURAL-ONLY summary. It never enters statistical code.
* ``--execute-official-r3`` is the eventual official execution path. It calls
  ``r3_analysis.build_analysis_artifact`` exactly once, after every fail-closed
  input gate passes, and writes the canonical analysis artifact plus its
  execution-provenance sidecar. It is NOT authorized by this task.

Scientific configuration is NOT exposed on the command line. The model
conditions, procedures, population, replicate counts, and output paths are all
frozen constants; there is no user-selectable scientific knob.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import platform
import sys
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from probvenance.fingerprint import fingerprint

_HARNESS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _HARNESS_DIR.parents[1]
_RESULTS_DIR = _HARNESS_DIR / "results"


def _load_sibling(name: str) -> Any:
    """Load a sibling harness module idempotently (stable class identity)."""
    module = sys.modules.get(name)
    if module is not None:
        return module
    spec = importlib.util.spec_from_file_location(name, _HARNESS_DIR / f"{name}.py")
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load {name}.py from {_HARNESS_DIR}")
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


r3_population = _load_sibling("r3_population")
r3_protocol = _load_sibling("r3_protocol")
r3_raw_evidence = _load_sibling("r3_raw_evidence")
r3_analysis = _load_sibling("r3_analysis")
_integrity = _load_sibling("integrity")

_SCORED_STATUS = _integrity.MeasurementStatus.SCORED.value
_SPLIT_TRAIN = r3_population.R3_SPLIT_TRAIN
_SPLIT_TEST = r3_population.R3_SPLIT_TEST

# --------------------------------------------------------------------------- #
# Frozen identities (PART 9)
# --------------------------------------------------------------------------- #

EXPECTED_PROTOCOL_FINGERPRINT = "3ef63056ae16b18ad65d9c87d1fbec5b43550873a0e3e25ec0a323f954ee974d"
EXPECTED_POPULATION_MANIFEST_FINGERPRINT = (
    "40cc9753a711314ff3b25ed6e234d0cbda11f3f60cd87f1d3915195a3d1780b8"
)
EXPECTED_MEASUREMENT_CODE_COMMIT = "8b1ea40aee0e7518c2ab3b25a8cc6d4ec2d0f800"

EXPECTED_INDEX_FILENAME = "r3-raw-evidence-index-v1.json"
EXPECTED_INDEX_SHA256 = "b04351acd878161d21022f3e5f5f08da1443977a484f62c8ba465adba051c461"
EXPECTED_INDEX_FINGERPRINT = "25fa4086e67a1cbd48cb8d857337092b132790ceb04925407649629c35d1bc51"

EXPECTED_CONDITIONS: tuple[str, ...] = ("primary", "replication")

CONDITION_SPECS: dict[str, dict[str, str]] = {
    "primary": {
        "condition": "primary",
        "role": "primary-confirmatory",
        "model_id": r3_protocol.PRIMARY_MODEL_ID,
        "model_revision": r3_protocol.PRIMARY_MODEL_REVISION,
        "raw_filename": "r3-raw-minicpm5-2b-mmlu-v1.json",
        "raw_sha256": "e7b45e921d35523f9fb6aabaefe10e585f43f35f25e5e4159bb2211cec8b999b",
        "evidence_fingerprint": (
            "726bb8340aecfa0c98e4d4b7fe1548278f3cc8ff391b9f6d14aa5215e84d7c71"
        ),
    },
    "replication": {
        "condition": "replication",
        "role": "preregistered-replication",
        "model_id": r3_protocol.REPLICATION_MODEL_ID,
        "model_revision": r3_protocol.REPLICATION_MODEL_REVISION,
        "raw_filename": "r3-raw-qwen35-2b-mmlu-v1.json",
        "raw_sha256": "00a1d04e6cb308cf609ccf3cde69b761497c4a3a110704ea069f3e933cf9248a",
        "evidence_fingerprint": (
            "378b2676dad4b12be4d57c9030c9d44823df921dc62f4d9b7f73acf79f0d4887"
        ),
    },
}

# --------------------------------------------------------------------------- #
# Frozen population contract and fixed paths
# --------------------------------------------------------------------------- #

EXPECTED_TOTAL_ITEMS = r3_population.DEFAULT_TOTAL
EXPECTED_TRAIN_ITEMS = r3_population.DEFAULT_TRAIN_TOTAL
EXPECTED_TEST_ITEMS = r3_population.DEFAULT_TEST_TOTAL
EXPECTED_SUBJECTS = len(r3_population.MMLU_SUBJECTS)
EXPECTED_TRAIN_PER_SUBJECT = r3_population.R3_TRAIN_PER_SUBJECT
EXPECTED_TEST_PER_SUBJECT = r3_population.R3_TEST_PER_SUBJECT

DEFAULT_INDEX_PATH = _RESULTS_DIR / EXPECTED_INDEX_FILENAME
DEFAULT_DESIGN_PATH = r3_protocol.DEFAULT_DESIGN_PATH
DEFAULT_MANIFEST_PATH = r3_population.DEFAULT_MANIFEST_PATH

OFFICIAL_ANALYSIS_OUTPUT_PATH = _RESULTS_DIR / "r3-confirmatory-analysis-v1.json"
OFFICIAL_EXECUTION_PROVENANCE_PATH = _RESULTS_DIR / "r3-confirmatory-analysis-execution-v1.json"

PREFLIGHT_ARTIFACT_TYPE = "r3-analysis-input-preflight"
PREFLIGHT_ARTIFACT_VERSION = 1
EXECUTION_ARTIFACT_TYPE = "r3-confirmatory-analysis-execution"
EXECUTION_ARTIFACT_VERSION = 1
EXECUTION_FINGERPRINT_VERSION = 1

#: Frozen replicate counts, recorded as provenance statements, never runtime knobs.
TEST_BOOTSTRAP_REPLICATES = r3_protocol.TEST_BOOTSTRAP_REPLICATES
TRAIN_REFIT_BOOTSTRAP_REPLICATES = r3_protocol.TRAIN_REFIT_BOOTSTRAP_REPLICATES


class RunnerError(RuntimeError):
    """Raised when a fail-closed ingestion / execution gate fails."""


# --------------------------------------------------------------------------- #
# Small utilities
# --------------------------------------------------------------------------- #


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: str | Path) -> str:
    return _sha256_bytes(Path(path).read_bytes())


def _canonical_text(payload: Mapping[str, Any]) -> str:
    """The established repository JSON convention, in memory."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def _relative(path: str | Path) -> str:
    target = Path(path).resolve()
    try:
        return str(target.relative_to(_REPO_ROOT))
    except ValueError:  # pragma: no cover - defensive
        return str(target)


def _git(*args: str) -> str:
    import subprocess

    result = subprocess.run(
        ["git", *args],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def verify_git_state(*, require_synchronized: bool) -> dict[str, Any]:
    """Fail closed unless the repository state is appropriate for the mode.

    Validate-only mode requires ``main`` and a clean tree but may run on an
    unpushed local candidate commit. Official execute mode additionally requires
    ``HEAD == origin/main`` with ``0/0`` ahead/behind. The runner never fetches.
    """
    branch = _git("branch", "--show-current")
    if branch != "main":
        raise RunnerError(f"R3 analysis runner requires branch 'main', found {branch!r}")
    status = _git("status", "--porcelain")
    if status:
        raise RunnerError(f"R3 analysis runner requires a clean working tree:\n{status}")
    head = _git("rev-parse", "HEAD")
    origin_main = _git("rev-parse", "origin/main")
    counts = _git("rev-list", "--left-right", "--count", "HEAD...origin/main").split()
    ahead, behind = int(counts[0]), int(counts[1])
    if require_synchronized and (head != origin_main or ahead != 0 or behind != 0):
        raise RunnerError(
            "official R3 analysis execution requires HEAD == origin/main at 0/0; "
            f"found head={head} origin_main={origin_main} ahead={ahead} behind={behind}"
        )
    return {
        "branch": branch,
        "head": head,
        "origin_main": origin_main,
        "ahead": ahead,
        "behind": behind,
    }


def _git_summary(state: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "branch": state["branch"],
        "head": state["head"],
        "origin_main": state["origin_main"],
        "ahead": state["ahead"],
        "behind": state["behind"],
    }


# --------------------------------------------------------------------------- #
# Frozen identity verification (protocol / manifest)
# --------------------------------------------------------------------------- #


def verify_protocol_identity(design: Mapping[str, Any]) -> str:
    recomputed = r3_protocol.protocol_fingerprint(design)
    if recomputed != EXPECTED_PROTOCOL_FINGERPRINT:
        raise RunnerError("recomputed R3 protocol fingerprint is not the frozen identity")
    if design.get("protocol_fingerprint") != EXPECTED_PROTOCOL_FINGERPRINT:
        raise RunnerError("R3 design protocol_fingerprint is not the frozen identity")
    return recomputed


def verify_manifest_identity(manifest: Mapping[str, Any]) -> str:
    recomputed = r3_population.manifest_fingerprint(manifest)
    if recomputed != EXPECTED_POPULATION_MANIFEST_FINGERPRINT:
        raise RunnerError("recomputed R3 population manifest fingerprint is not frozen")
    if manifest.get("manifest_fingerprint") != EXPECTED_POPULATION_MANIFEST_FINGERPRINT:
        raise RunnerError("R3 population manifest fingerprint is not the frozen identity")
    return recomputed


# --------------------------------------------------------------------------- #
# Raw-evidence index validation (PART 10, 11)
# --------------------------------------------------------------------------- #


def load_index(path: str | Path = DEFAULT_INDEX_PATH) -> tuple[dict[str, Any], str]:
    """Read the index bytes, verify its SHA256, then parse. Bytes before trust."""
    raw = Path(path).read_bytes()
    sha256 = _sha256_bytes(raw)
    if sha256 != EXPECTED_INDEX_SHA256:
        raise RunnerError(f"raw-evidence index SHA256 {sha256} != frozen {EXPECTED_INDEX_SHA256}")
    payload = json.loads(raw.decode("utf-8"))
    validate_index(payload)
    return payload, sha256


def _expected_structural_counts() -> dict[str, Any]:
    return {
        "items": EXPECTED_TOTAL_ITEMS,
        "cat": {"scored": EXPECTED_TOTAL_ITEMS, "missing": 0, "ineligible": 0},
        "ovr": {"scored": EXPECTED_TOTAL_ITEMS, "missing": 0, "ineligible": 0},
    }


def validate_index(payload: Mapping[str, Any]) -> None:
    """Validate the committed raw-evidence index against the frozen contract."""
    if payload.get("artifact_type") != r3_raw_evidence.R3_RAW_EVIDENCE_INDEX_ARTIFACT_TYPE:
        raise RunnerError("raw-evidence index artifact_type mismatch")
    if payload.get("artifact_version") != r3_raw_evidence.R3_RAW_EVIDENCE_INDEX_VERSION:
        raise RunnerError("raw-evidence index artifact_version mismatch")
    if (
        payload.get("fingerprint_version")
        != r3_raw_evidence.R3_RAW_EVIDENCE_INDEX_FINGERPRINT_VERSION
    ):
        raise RunnerError("raw-evidence index fingerprint_version mismatch")
    if payload.get("r3_protocol_fingerprint") != EXPECTED_PROTOCOL_FINGERPRINT:
        raise RunnerError("raw-evidence index protocol fingerprint mismatch")
    if payload.get("population_manifest_fingerprint") != EXPECTED_POPULATION_MANIFEST_FINGERPRINT:
        raise RunnerError("raw-evidence index population manifest fingerprint mismatch")
    if payload.get("measurement_code_commit") != EXPECTED_MEASUREMENT_CODE_COMMIT:
        raise RunnerError("raw-evidence index measurement_code_commit mismatch")
    if payload.get("index_fingerprint") != EXPECTED_INDEX_FINGERPRINT:
        raise RunnerError("raw-evidence index declared fingerprint is not the frozen identity")
    if r3_raw_evidence.index_fingerprint(payload) != EXPECTED_INDEX_FINGERPRINT:
        raise RunnerError("recomputed raw-evidence index fingerprint is not frozen")
    if payload.get("all_declared_conditions_complete") is not True:
        raise RunnerError("raw-evidence index does not declare every condition complete")

    conditions = payload.get("conditions")
    if not isinstance(conditions, Mapping):
        raise RunnerError("raw-evidence index lacks a conditions mapping")
    if set(conditions) != set(EXPECTED_CONDITIONS):
        raise RunnerError(
            f"raw-evidence index condition keys {sorted(conditions)} != {list(EXPECTED_CONDITIONS)}"
        )
    for name in EXPECTED_CONDITIONS:
        _validate_index_condition(name, conditions[name])


def _validate_index_condition(name: str, entry: Mapping[str, Any]) -> None:
    spec = CONDITION_SPECS[name]
    for entry_field, spec_field in (
        ("model_id", "model_id"),
        ("model_revision", "model_revision"),
        ("model_role", "role"),
    ):
        if entry.get(entry_field) != spec[spec_field]:
            raise RunnerError(f"raw-evidence index {name} {entry_field} mismatch")
    if entry.get("raw_artifact_filename") != spec["raw_filename"]:
        raise RunnerError(f"raw-evidence index {name} raw_artifact_filename mismatch")
    if entry.get("file_sha256") != spec["raw_sha256"]:
        raise RunnerError(f"raw-evidence index {name} file_sha256 mismatch")
    if entry.get("evidence_fingerprint") != spec["evidence_fingerprint"]:
        raise RunnerError(f"raw-evidence index {name} evidence_fingerprint mismatch")
    if entry.get("expected_item_count") != EXPECTED_TOTAL_ITEMS:
        raise RunnerError(f"raw-evidence index {name} expected_item_count mismatch")
    if entry.get("actual_item_count") != EXPECTED_TOTAL_ITEMS:
        raise RunnerError(f"raw-evidence index {name} actual_item_count mismatch")
    if entry.get("structurally_complete") is not True:
        raise RunnerError(f"raw-evidence index {name} is not structurally complete")
    if entry.get("structural_status_counts") != _expected_structural_counts():
        raise RunnerError(f"raw-evidence index {name} structural_status_counts mismatch")


def guard_raw_filename(filename: Any, *, expected_filename: str) -> Path:
    """Reject traversal / alternate filenames; resolve inside the results dir."""
    if not isinstance(filename, str) or not filename:
        raise RunnerError("raw artifact filename must be a non-empty string")
    if filename != expected_filename:
        raise RunnerError(f"raw artifact filename {filename!r} != expected {expected_filename!r}")
    if filename != Path(filename).name or filename in {".", ".."}:
        raise RunnerError(f"raw artifact filename {filename!r} must be a plain basename")
    if any(sep and sep in filename for sep in (os.sep, os.altsep)):
        raise RunnerError(f"raw artifact filename {filename!r} must not contain separators")
    results_root = _RESULTS_DIR.resolve()
    candidate = (results_root / filename).resolve()
    if candidate.parent != results_root:
        raise RunnerError(f"raw artifact {filename!r} escapes the results directory")
    return candidate


# --------------------------------------------------------------------------- #
# Raw artifact byte identity (PART 13)
# --------------------------------------------------------------------------- #


def load_raw_artifact(path: str | Path, *, expected_sha256: str) -> tuple[dict[str, Any], str]:
    """Read exact bytes, verify SHA256, then parse. Bytes before trust."""
    raw = Path(path).read_bytes()
    sha256 = _sha256_bytes(raw)
    if sha256 != expected_sha256:
        raise RunnerError(f"raw artifact SHA256 {sha256} != frozen {expected_sha256}")
    payload = json.loads(raw.decode("utf-8"))
    return payload, sha256


def verify_raw_identity(payload: Mapping[str, Any], *, condition: str) -> None:
    """Verify the raw payload's own declared condition/model/provenance metadata."""
    spec = CONDITION_SPECS[condition]
    if payload.get("artifact_type") != r3_raw_evidence.R3_RAW_EVIDENCE_ARTIFACT_TYPE:
        raise RunnerError(f"{condition} raw artifact_type mismatch")
    if payload.get("artifact_version") != r3_raw_evidence.R3_RAW_EVIDENCE_ARTIFACT_VERSION:
        raise RunnerError(f"{condition} raw artifact_version mismatch")
    if payload.get("fingerprint_version") != r3_raw_evidence.R3_RAW_EVIDENCE_FINGERPRINT_VERSION:
        raise RunnerError(f"{condition} raw fingerprint_version mismatch")
    if payload.get("r3_protocol_fingerprint") != EXPECTED_PROTOCOL_FINGERPRINT:
        raise RunnerError(f"{condition} raw protocol fingerprint mismatch")
    if payload.get("measurement_code_commit") != EXPECTED_MEASUREMENT_CODE_COMMIT:
        raise RunnerError(f"{condition} raw measurement_code_commit mismatch")
    population = payload.get("population", {})
    if population.get("manifest_fingerprint") != EXPECTED_POPULATION_MANIFEST_FINGERPRINT:
        raise RunnerError(f"{condition} raw population manifest fingerprint mismatch")
    model_condition = payload.get("model_condition")
    if not isinstance(model_condition, Mapping):
        raise RunnerError(f"{condition} raw lacks a model_condition block")
    if model_condition.get("condition") != spec["condition"]:
        raise RunnerError(f"{condition} raw model_condition.condition mismatch")
    if model_condition.get("role") != spec["role"]:
        raise RunnerError(f"{condition} raw model_condition.role mismatch")
    if model_condition.get("model_id") != spec["model_id"]:
        raise RunnerError(f"{condition} raw model_id mismatch")
    if model_condition.get("model_revision") != spec["model_revision"]:
        raise RunnerError(f"{condition} raw model_revision mismatch")
    if payload.get("evidence_fingerprint") != spec["evidence_fingerprint"]:
        raise RunnerError(f"{condition} raw evidence_fingerprint mismatch")
    if payload.get("structural_counts") != _expected_structural_counts():
        raise RunnerError(f"{condition} raw structural_counts mismatch")


def verify_child_plan(
    manifest: Mapping[str, Any], *, condition: str, expected_fingerprint: str
) -> Any:
    """Rebuild the child plan through the existing official measurement path."""
    spec = CONDITION_SPECS[condition]
    plan = r3_protocol.build_child_plan(
        manifest, model_id=spec["model_id"], model_revision=spec["model_revision"]
    )
    if plan.fingerprint != expected_fingerprint:
        raise RunnerError(
            f"{condition} recomputed child plan fingerprint {plan.fingerprint!r} != "
            f"{expected_fingerprint!r}"
        )
    return plan


# --------------------------------------------------------------------------- #
# Raw -> R3Item adapter (PART 16, 17)
# --------------------------------------------------------------------------- #


def _scored_anchor_score(evidence_item: Mapping[str, Any], *, measurement: str) -> float:
    item_id = evidence_item.get("item_id")
    block = evidence_item.get(measurement)
    if not isinstance(block, Mapping):
        raise RunnerError(f"item {item_id} lacks a {measurement} block")
    if block.get("status") != _SCORED_STATUS:
        raise RunnerError(f"item {item_id} {measurement} is not SCORED")
    record = block.get("record")
    if not isinstance(record, Mapping):
        raise RunnerError(f"item {item_id} SCORED {measurement} lacks its record")
    score = record.get("anchor_score")
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise RunnerError(f"item {item_id} {measurement} anchor_score must be a number")
    value = float(score)
    if not math.isfinite(value) or not (0.0 <= value <= 1.0):
        raise RunnerError(f"item {item_id} {measurement} anchor_score must lie in [0,1]")
    return value


def r3_item_from_evidence(evidence_item: Mapping[str, Any]) -> Any:
    """Map one frozen raw-evidence item onto exactly one ``R3Item``.

    ``Y_i`` is the frozen externally selected anchor's correctness
    (``anchor_correct``); it is never derived from a winner, a candidate
    probability, an argmax, or a threshold.
    """
    item_id = evidence_item.get("item_id")
    if not isinstance(item_id, str) or not item_id:
        raise RunnerError("raw item_id must be a non-empty string")
    subject = evidence_item.get("subject")
    if not isinstance(subject, str) or not subject:
        raise RunnerError(f"item {item_id} subject must be a non-empty string")
    anchor_correct = evidence_item.get("anchor_correct")
    if not isinstance(anchor_correct, bool):
        raise RunnerError(f"item {item_id} anchor_correct must be a bool")
    anchor = evidence_item.get("anchor")
    ground_truth_value = evidence_item.get("ground_truth_value")
    if (anchor == ground_truth_value) != anchor_correct:
        raise RunnerError(f"item {item_id} anchor_correct disagrees with anchor vs ground truth")
    return r3_analysis.R3Item(
        item_id=item_id,
        subject=subject,
        label=1.0 if anchor_correct else 0.0,
        cat_score=_scored_anchor_score(evidence_item, measurement="cat"),
        ovr_score=_scored_anchor_score(evidence_item, measurement="ovr"),
    )


# --------------------------------------------------------------------------- #
# TRAIN / TEST partition contract (PART 21, 22, 46)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class PopulationContract:
    """Structural expectations. The official CLI always uses the frozen values."""

    total: int = EXPECTED_TOTAL_ITEMS
    train: int = EXPECTED_TRAIN_ITEMS
    test: int = EXPECTED_TEST_ITEMS
    subjects: int = EXPECTED_SUBJECTS
    train_per_subject: int | None = EXPECTED_TRAIN_PER_SUBJECT
    test_per_subject: int | None = EXPECTED_TEST_PER_SUBJECT


OFFICIAL_POPULATION = PopulationContract()


def partition_evidence_items(
    evidence_items: Sequence[Mapping[str, Any]],
    *,
    contract: PopulationContract = OFFICIAL_POPULATION,
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    """Split validated raw rows into TRAIN/TEST, preserving source order."""
    train: list[Mapping[str, Any]] = []
    test: list[Mapping[str, Any]] = []
    for item in evidence_items:
        split = item.get("split")
        if split == _SPLIT_TRAIN:
            train.append(item)
        elif split == _SPLIT_TEST:
            test.append(item)
        else:
            raise RunnerError(
                f"item {item.get('item_id')} has unexpected split {split!r}; "
                "the frozen R3 population contains only TRAIN and TEST"
            )
    if len(evidence_items) != contract.total:
        raise RunnerError(f"population has {len(evidence_items)} rows, expected {contract.total}")
    if len(train) != contract.train:
        raise RunnerError(f"TRAIN has {len(train)} rows, expected {contract.train}")
    if len(test) != contract.test:
        raise RunnerError(f"TEST has {len(test)} rows, expected {contract.test}")
    subjects = {item.get("subject") for item in evidence_items}
    if len(subjects) != contract.subjects:
        raise RunnerError(f"population has {len(subjects)} subjects, expected {contract.subjects}")
    if contract.train_per_subject is not None:
        train_counts = Counter(item.get("subject") for item in train)
        if any(train_counts[subject] != contract.train_per_subject for subject in subjects):
            raise RunnerError(
                f"every subject must contribute {contract.train_per_subject} TRAIN rows"
            )
    if contract.test_per_subject is not None:
        test_counts = Counter(item.get("subject") for item in test)
        if any(test_counts[subject] != contract.test_per_subject for subject in subjects):
            raise RunnerError(
                f"every subject must contribute {contract.test_per_subject} TEST rows"
            )
    return train, test


def build_test_winner_records(test_evidence_items: Sequence[Mapping[str, Any]]) -> tuple[Any, ...]:
    """Map TEST rows through the audited winner adapter; never reimplemented here."""
    return tuple(r3_analysis.winner_record_from_evidence(item) for item in test_evidence_items)


def _structure_signature(item: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        item.get("item_id"),
        item.get("subject"),
        item.get("split"),
        item.get("anchor"),
        item.get("ground_truth_value"),
        bool(item.get("anchor_correct")),
    )


def verify_cross_condition_pairing(
    primary_items: Sequence[Mapping[str, Any]],
    replication_items: Sequence[Mapping[str, Any]],
) -> None:
    """Require identical frozen population structure (scores/winners may differ)."""
    if len(primary_items) != len(replication_items):
        raise RunnerError("primary and replication row counts differ")
    for position, (primary_item, replication_item) in enumerate(
        zip(primary_items, replication_items, strict=True)
    ):
        if _structure_signature(primary_item) != _structure_signature(replication_item):
            raise RunnerError(
                f"primary and replication frozen population structure differ at position {position}"
            )


# --------------------------------------------------------------------------- #
# Condition assembly (PART 14, 15, 24, 25)
# --------------------------------------------------------------------------- #


def map_validated_condition(
    condition: str,
    raw_payload: Mapping[str, Any],
    *,
    manifest: Mapping[str, Any],
    design: Mapping[str, Any],
    contract: PopulationContract = OFFICIAL_POPULATION,
    validator: Callable[..., None] | None = None,
) -> tuple[tuple[Any, ...], tuple[Any, ...], tuple[Any, ...]]:
    """Validate raw structure, THEN map rows. Never map before validation."""
    model = design["models"][condition]
    plan = verify_child_plan(
        manifest,
        condition=condition,
        expected_fingerprint=str(model["child_plan_fingerprint"]),
    )
    (validator or r3_raw_evidence.validate_raw_evidence)(
        raw_payload,
        manifest=manifest,
        plan=plan,
        expected_protocol_fingerprint=EXPECTED_PROTOCOL_FINGERPRINT,
    )
    evidence_items = list(raw_payload["items"])
    train_evidence, test_evidence = partition_evidence_items(evidence_items, contract=contract)
    train_items = tuple(r3_item_from_evidence(item) for item in train_evidence)
    test_items = tuple(r3_item_from_evidence(item) for item in test_evidence)
    test_winner_records = build_test_winner_records(test_evidence)
    return train_items, test_items, test_winner_records


@dataclass(frozen=True, slots=True)
class PreparedInputs:
    """Fully gated official inputs, ready for the kernel (or a structural summary)."""

    design: Mapping[str, Any]
    conditions: tuple[Mapping[str, Any], ...]
    provenance_base: Mapping[str, Any]
    preflight: Mapping[str, Any]


def prepare_official_inputs(
    *,
    index_path: str | Path = DEFAULT_INDEX_PATH,
    design: Mapping[str, Any] | None = None,
    manifest: Mapping[str, Any] | None = None,
    contract: PopulationContract = OFFICIAL_POPULATION,
) -> PreparedInputs:
    """Run every fail-closed ingestion gate and assemble the two conditions."""
    resolved_design: Mapping[str, Any] = design if design is not None else r3_protocol.load_design()
    resolved_manifest: Mapping[str, Any] = (
        manifest if manifest is not None else r3_population.load_manifest()
    )
    protocol_fingerprint = verify_protocol_identity(resolved_design)
    manifest_fingerprint = verify_manifest_identity(resolved_manifest)

    index_payload, index_sha256 = load_index(index_path)

    conditions: list[Mapping[str, Any]] = []
    preflight_conditions: dict[str, Any] = {}
    raw_inputs: dict[str, Any] = {}
    structural_signatures: dict[str, list[Mapping[str, Any]]] = {}

    for condition in EXPECTED_CONDITIONS:
        index_entry = index_payload["conditions"][condition]
        expected_filename = str(index_entry["raw_artifact_filename"])
        raw_path = guard_raw_filename(expected_filename, expected_filename=expected_filename)
        raw_payload, raw_sha256 = load_raw_artifact(
            raw_path, expected_sha256=str(index_entry["file_sha256"])
        )
        verify_raw_identity(raw_payload, condition=condition)
        design_child_plan = str(resolved_design["models"][condition]["child_plan_fingerprint"])
        if str(index_entry["child_plan_fingerprint"]) != design_child_plan:
            raise RunnerError(
                f"{condition} raw-evidence index child_plan_fingerprint disagrees with "
                "the frozen protocol design"
            )
        train_items, test_items, test_winner_records = map_validated_condition(
            condition,
            raw_payload,
            manifest=resolved_manifest,
            design=resolved_design,
            contract=contract,
        )
        conditions.append(
            {
                "model_id": CONDITION_SPECS[condition]["model_id"],
                "model_revision": CONDITION_SPECS[condition]["model_revision"],
                "train_items": train_items,
                "test_items": test_items,
                "test_winner_records": test_winner_records,
            }
        )
        raw_inputs[condition] = {
            "filename": expected_filename,
            "sha256": raw_sha256,
            "evidence_fingerprint": str(index_entry["evidence_fingerprint"]),
            "model_id": CONDITION_SPECS[condition]["model_id"],
            "model_revision": CONDITION_SPECS[condition]["model_revision"],
            "child_plan_fingerprint": str(index_entry["child_plan_fingerprint"]),
        }
        structural_signatures[condition] = list(raw_payload["items"])
        preflight_conditions[condition] = {
            "model_id": CONDITION_SPECS[condition]["model_id"],
            "model_revision": CONDITION_SPECS[condition]["model_revision"],
            "model_role": CONDITION_SPECS[condition]["role"],
            "child_plan_fingerprint": str(index_entry["child_plan_fingerprint"]),
            "raw_filename": expected_filename,
            "raw_sha256": raw_sha256,
            "evidence_fingerprint": str(index_entry["evidence_fingerprint"]),
            "total_items": len(raw_payload["items"]),
            "train_items": len(train_items),
            "test_items": len(test_items),
            "subjects": len({item.subject for item in train_items}),
            "test_winner_records": len(test_winner_records),
        }

    verify_cross_condition_pairing(
        structural_signatures["primary"], structural_signatures["replication"]
    )

    preflight: dict[str, Any] = {
        "artifact_type": PREFLIGHT_ARTIFACT_TYPE,
        "artifact_version": PREFLIGHT_ARTIFACT_VERSION,
        "protocol_fingerprint": protocol_fingerprint,
        "population_manifest_fingerprint": manifest_fingerprint,
        "raw_index_sha256": index_sha256,
        "raw_index_fingerprint": str(index_payload["index_fingerprint"]),
        "conditions": preflight_conditions,
        "cross_condition_population_pairing": True,
        "official_confirmatory_statistical_outcome_computed": False,
    }

    provenance_base: dict[str, Any] = {
        "protocol_fingerprint": protocol_fingerprint,
        "population_manifest_fingerprint": manifest_fingerprint,
        "measurement_code_commit": EXPECTED_MEASUREMENT_CODE_COMMIT,
        "raw_index": {
            "filename": EXPECTED_INDEX_FILENAME,
            "sha256": index_sha256,
            "fingerprint": str(index_payload["index_fingerprint"]),
        },
        "raw_inputs": raw_inputs,
        "analysis_kernel": {
            "file": _relative(_HARNESS_DIR / "r3_analysis.py"),
            "file_sha256": _sha256_file(_HARNESS_DIR / "r3_analysis.py"),
        },
        "analysis_runner": {
            "file": _relative(Path(__file__)),
            "file_sha256": _sha256_file(Path(__file__)),
        },
        "execution_environment": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        "test_bootstrap_replicates": TEST_BOOTSTRAP_REPLICATES,
        "train_refit_bootstrap_replicates": TRAIN_REFIT_BOOTSTRAP_REPLICATES,
    }

    return PreparedInputs(
        design=resolved_design,
        conditions=tuple(conditions),
        provenance_base=provenance_base,
        preflight=preflight,
    )


# --------------------------------------------------------------------------- #
# Execution provenance + safe two-file write (PART 34-39)
# --------------------------------------------------------------------------- #


def _require_absent(path: str | Path) -> None:
    if Path(path).exists():
        raise RunnerError(f"refusing to overwrite existing file {path}")


def build_execution_provenance(
    prepared: PreparedInputs,
    *,
    git_state: Mapping[str, Any],
    output_path: str | Path,
    analysis_sha256: str,
) -> dict[str, Any]:
    """Assemble the execution-provenance sidecar (no wall-clock, no interpretation)."""
    payload: dict[str, Any] = {
        "artifact_type": EXECUTION_ARTIFACT_TYPE,
        "artifact_version": EXECUTION_ARTIFACT_VERSION,
        "fingerprint_version": EXECUTION_FINGERPRINT_VERSION,
        "git": {
            "branch": git_state["branch"],
            "head": git_state["head"],
            "origin_main": git_state["origin_main"],
        },
        **prepared.provenance_base,
        "analysis_output_filename": Path(output_path).name,
        "analysis_output_sha256": analysis_sha256,
    }
    payload["execution_fingerprint"] = fingerprint(payload)
    return payload


def _write_text_pair(
    first_path: str | Path,
    first_text: str,
    second_path: str | Path,
    second_text: str,
) -> None:
    """Write two files via same-directory temp + rename, cleaning up on failure."""
    first_final = Path(first_path)
    second_final = Path(second_path)
    _require_absent(first_final)
    _require_absent(second_final)
    first_tmp = first_final.with_name(first_final.name + ".tmp")
    second_tmp = second_final.with_name(second_final.name + ".tmp")
    temps: list[Path] = []
    finals: list[Path] = []
    try:
        for tmp, final, text in (
            (first_tmp, first_final, first_text),
            (second_tmp, second_final, second_text),
        ):
            tmp.write_text(text, encoding="utf-8")
            temps.append(tmp)
            os.replace(tmp, final)
            finals.append(final)
            temps.remove(tmp)
    except Exception:
        for path in (*temps, *finals):
            path.unlink(missing_ok=True)
        raise


def execute_official_r3(
    prepared: PreparedInputs,
    *,
    output_path: str | Path = OFFICIAL_ANALYSIS_OUTPUT_PATH,
    provenance_path: str | Path = OFFICIAL_EXECUTION_PROVENANCE_PATH,
    builder: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Call the frozen kernel exactly once and write the result pair.

    The kernel is invoked with frozen defaults only: the runner never passes
    ``test_replicates`` or ``train_refit_replicates``.
    """
    active_builder: Callable[..., dict[str, Any]] = (
        r3_analysis.build_analysis_artifact if builder is None else builder
    )
    git_state = verify_git_state(require_synchronized=True)
    _require_absent(output_path)
    _require_absent(provenance_path)

    analysis_payload = active_builder(
        protocol_design=prepared.design,
        conditions=list(prepared.conditions),
    )
    analysis_text = _canonical_text(analysis_payload)
    analysis_sha256 = _sha256_bytes(analysis_text.encode("utf-8"))
    provenance = build_execution_provenance(
        prepared,
        git_state=git_state,
        output_path=output_path,
        analysis_sha256=analysis_sha256,
    )
    provenance_text = _canonical_text(provenance)

    _require_absent(output_path)
    _require_absent(provenance_path)
    _write_text_pair(output_path, analysis_text, provenance_path, provenance_text)
    return {
        "artifact_type": EXECUTION_ARTIFACT_TYPE,
        "analysis_output_filename": Path(output_path).name,
        "analysis_output_sha256": analysis_sha256,
        "execution_provenance_filename": Path(provenance_path).name,
        "execution_fingerprint": provenance["execution_fingerprint"],
    }


# --------------------------------------------------------------------------- #
# CLI (PART 6, 7, 32)
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument(
        "--validate-inputs-only",
        action="store_true",
        help="byte / structural / wiring preflight only; never enters statistical code",
    )
    modes.add_argument(
        "--execute-official-r3",
        action="store_true",
        help="eventual official execution path (calls the frozen kernel exactly once)",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.validate_inputs_only:
        git_state = verify_git_state(require_synchronized=False)
        prepared = prepare_official_inputs()
        summary = dict(prepared.preflight)
        summary["git"] = _git_summary(git_state)
        print(_canonical_text(summary), end="")
        return 0
    prepared = prepare_official_inputs()
    result = execute_official_r3(prepared)
    print(_canonical_text(result), end="")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
