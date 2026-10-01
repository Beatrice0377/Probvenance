"""R4 measurement staging: crash-safe, deterministic, outcome-blind resume.

This module is an OPERATIONAL execution policy only. It does not define or
change any scientific estimand: the anchor ``D_i``, ``Y_i``, CAT semantics, OVR
semantics, model revision, population, row set, row order, verbalizers and the
frozen measurement contract are all untouched.

It provides the durable primitives the formal runner needs for a long
(100,728 row / 201,456 logical forward) run:

* an immutable per-cell identity header,
* one atomic committed row file per frozen item,
* an outcome-blind pending set derived only from transaction state,
* recovery replay of an interrupted, uncommitted row (never a partial merge),
* a single-writer ``fcntl.flock`` cell lock,
* atomic finalization of the cell raw-evidence artifact,
* an operational sidecar that is deliberately NOT part of the scientific
  evidence fingerprint.

Nothing here reads a score, a probability, ``Y``, correctness or CAT/OVR
agreement, so resume can never become score-dependent.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

RESUME_POLICY_ID = "r4-measurement-resume-policy"
RESUME_POLICY_VERSION = 1

DEFAULT_STAGING_ROOT = "/root/rivermind-data/r4-formal-measurements"

ROWS_DIRNAME = "rows"
IDENTITY_FILENAME = "cell_identity.json"
RUNTIME_FILENAME = "runtime_provenance.json"
LOCK_FILENAME = "LOCK"
FINAL_FILENAME = "raw-evidence.json"
OPERATIONS_FILENAME = "operations.json"

_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9._-]+$")


class R4StagingError(RuntimeError):
    """Base error for the R4 staging / resume layer."""


class R4CellLockedError(R4StagingError):
    """A second writer tried to open a cell that is already locked."""


class R4ResumeIdentityMismatch(R4StagingError):
    """The existing staging does not match the expected immutable cell identity."""


class R4DuplicateCommittedRow(R4StagingError):
    """More than one committed row exists for the same frozen item identity."""


class R4ExistingFinalArtifactConflict(R4StagingError):
    """A final artifact exists but does not match the expected identity/fingerprint."""


# --------------------------------------------------------------------------- #
# Canonical serialization / atomic writes
# --------------------------------------------------------------------------- #


def dump_canonical(payload: Mapping[str, Any]) -> str:
    """Canonical JSON (stable key order, UTF-8, no NaN) with a trailing newline."""
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    )


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _fsync_dir(path: Path) -> None:
    try:
        descriptor = os.open(str(path), os.O_RDONLY)
    except OSError:  # pragma: no cover - defensive
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_atomic(path: str | Path, text: str) -> None:
    """Write ``text`` durably: temp -> flush -> fsync -> atomic replace -> fsync dir."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, tmp_name = tempfile.mkstemp(
        dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, target)
        _fsync_dir(target.parent)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #


def _safe_component(value: object, *, field: str) -> str:
    text = str(value)
    if not _SAFE_COMPONENT.match(text):
        raise R4StagingError(f"unsafe staging path component for {field}: {text!r}")
    return text


def cell_dir_name(model_key: str, population_id: str) -> str:
    """Deterministic staging directory name for one frozen cell (never outcome-named)."""
    model_component = _safe_component(model_key, field="model_key")
    population_component = _safe_component(population_id, field="population_id")
    return f"{model_component}__{population_component}"


def cell_dir(staging_root: str | Path, model_key: str, population_id: str) -> Path:
    return Path(staging_root) / cell_dir_name(model_key, population_id)


def rows_dir(directory: str | Path) -> Path:
    return Path(directory) / ROWS_DIRNAME


def row_path(directory: str | Path, item_id: str) -> Path:
    return rows_dir(directory) / f"{_safe_component(item_id, field='item_id')}.json"


def inflight_path(directory: str | Path, item_id: str) -> Path:
    return rows_dir(directory) / f"{_safe_component(item_id, field='item_id')}.inflight"


def final_path(directory: str | Path) -> Path:
    return Path(directory) / FINAL_FILENAME


def identity_path(directory: str | Path) -> Path:
    return Path(directory) / IDENTITY_FILENAME


def runtime_path(directory: str | Path) -> Path:
    return Path(directory) / RUNTIME_FILENAME


def operations_path(directory: str | Path) -> Path:
    return Path(directory) / OPERATIONS_FILENAME


def ensure_cell_dir(staging_root: str | Path, model_key: str, population_id: str) -> Path:
    directory = cell_dir(staging_root, model_key, population_id)
    rows_dir(directory).mkdir(parents=True, exist_ok=True)
    return directory


# --------------------------------------------------------------------------- #
# Single-writer cell lock
# --------------------------------------------------------------------------- #


def acquire_cell_lock(directory: str | Path) -> Any:
    """Take the exclusive single-writer lock for one cell (non-blocking)."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    handle = open(directory / LOCK_FILENAME, "w", encoding="utf-8")  # noqa: SIM115 - lock held by fd
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        handle.close()
        raise R4CellLockedError(f"cell staging is already locked: {directory}") from exc
    return handle


def release_cell_lock(handle: Any) -> None:
    if handle is None:
        return
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


# --------------------------------------------------------------------------- #
# Immutable identity header
# --------------------------------------------------------------------------- #


def verify_or_write_identity(directory: str | Path, identity: Mapping[str, Any]) -> dict[str, Any]:
    """Write the immutable identity once, then require exact equality on every resume."""
    path = identity_path(directory)
    if path.exists():
        existing = read_json(path)
        if existing != dict(identity):
            raise R4ResumeIdentityMismatch(
                "existing cell staging identity does not match the expected identity: "
                f"{path}"
            )
        return existing
    write_atomic(path, dump_canonical(identity))
    return dict(identity)


# --------------------------------------------------------------------------- #
# Runtime provenance (written once, after the model + verbalizers are verified)
# --------------------------------------------------------------------------- #


def verify_or_write_runtime(directory: str | Path, runtime: Mapping[str, Any]) -> dict[str, Any]:
    path = runtime_path(directory)
    if path.exists():
        existing = read_json(path)
        if existing != dict(runtime):
            raise R4ResumeIdentityMismatch(
                f"existing runtime provenance does not match the observed runtime: {path}"
            )
        return existing
    write_atomic(path, dump_canonical(runtime))
    return dict(runtime)


def load_runtime(directory: str | Path) -> dict[str, Any] | None:
    path = runtime_path(directory)
    return read_json(path) if path.exists() else None


# --------------------------------------------------------------------------- #
# Committed rows
# --------------------------------------------------------------------------- #


def commit_row(directory: str | Path, item: Mapping[str, Any]) -> None:
    """Atomically commit one fully measured, schema-validated row."""
    write_atomic(row_path(directory, str(item["item_id"])), dump_canonical(item))


def load_committed_rows(directory: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(rows_dir(directory).glob("*.json")):
        rows.append(read_json(path))
    seen: set[str] = set()
    for row in rows:
        item_id = str(row["item_id"])
        if item_id in seen:
            raise R4DuplicateCommittedRow(f"duplicate committed row for item {item_id!r}")
        seen.add(item_id)
    return rows


def committed_item_ids(directory: str | Path) -> set[str]:
    return {str(row["item_id"]) for row in load_committed_rows(directory)}


# --------------------------------------------------------------------------- #
# Interrupted-row markers (recovery replay accounting)
# --------------------------------------------------------------------------- #


def mark_inflight(directory: str | Path, item_id: str) -> None:
    write_atomic(
        inflight_path(directory, item_id),
        dump_canonical({"item_id": str(item_id), "state": "inflight"}),
    )


def clear_inflight(directory: str | Path, item_id: str) -> None:
    path = inflight_path(directory, item_id)
    try:
        path.unlink()
    except FileNotFoundError:
        return
    _fsync_dir(rows_dir(directory))


def load_inflight_item_ids(directory: str | Path) -> set[str]:
    ids: set[str] = set()
    for path in sorted(rows_dir(directory).glob("*.inflight")):
        ids.add(str(read_json(path)["item_id"]))
    return ids


# --------------------------------------------------------------------------- #
# Outcome-blind pending set
# --------------------------------------------------------------------------- #


def compute_pending(
    *,
    ordered_item_ids: Sequence[str],
    committed_ids: set[str],
    inflight_ids: set[str],
) -> dict[str, Any]:
    """Derive the pending set from transaction state only (never from any score)."""
    ordered = [str(item_id) for item_id in ordered_item_ids]
    pending = [item_id for item_id in ordered if item_id not in committed_ids]
    recovery_replay = [item_id for item_id in pending if item_id in inflight_ids]
    fresh = [item_id for item_id in pending if item_id not in inflight_ids]
    committed_ordered = [item_id for item_id in ordered if item_id in committed_ids]
    return {
        "pending": pending,
        "fresh": fresh,
        "recovery_replay": recovery_replay,
        "committed": committed_ordered,
    }


# --------------------------------------------------------------------------- #
# Atomic finalization
# --------------------------------------------------------------------------- #


def publish_final(directory: str | Path, payload: Mapping[str, Any]) -> None:
    write_atomic(final_path(directory), dump_canonical(payload))


def load_final(directory: str | Path) -> dict[str, Any] | None:
    path = final_path(directory)
    return read_json(path) if path.exists() else None


# --------------------------------------------------------------------------- #
# Operational sidecar (NOT part of the scientific evidence fingerprint)
# --------------------------------------------------------------------------- #


def load_operations(directory: str | Path) -> dict[str, Any]:
    path = operations_path(directory)
    if not path.exists():
        return {
            "resume_policy_id": RESUME_POLICY_ID,
            "resume_policy_version": RESUME_POLICY_VERSION,
            "planned_logical_forwards": 0,
            "operational_attempts": 0,
            "recovery_replay_count": 0,
            "finalizations": 0,
            "runs": [],
        }
    return read_json(path)


def save_operations(directory: str | Path, operations: Mapping[str, Any]) -> None:
    write_atomic(operations_path(directory), dump_canonical(operations))
