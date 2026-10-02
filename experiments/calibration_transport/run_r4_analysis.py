"""R4 integrated formal analysis runner (orchestration only).

This module wires the ALREADY-FROZEN R4 statistical implementations into one
deterministic pipeline. It never re-implements calibration mathematics, risk or
Delta definitions, bootstrap statistics, multiplicity formulas, the Spearman
statistic or the Wasserstein-1 statistic. It performs only I/O, schema and
authority validation, dependency wiring, status propagation, checkpointing,
atomic writes and CLI dispatch.

The runner is safe by default:

* no flag, or ``--validate-only`` -> structural validation only;
* ``--synthetic-qualification`` -> invented synthetic fixtures only;
* ``--execute-formal-analysis`` -> the explicit, hard-to-trigger formal mode.

No formal R4 statistic is computed by this task. Formal analysis stays
unauthorized until a human / ChatGPT review authorizes it.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
CAL_DIR = Path(__file__).resolve().parent
POPULATION_CANDIDATE_DIR = Path("/root/rivermind-data/r4-population-candidates")

from probvenance.fingerprint import fingerprint  # noqa: E402

# --------------------------------------------------------------------------- #
# Frozen authority (paths, digests, fingerprints)
# --------------------------------------------------------------------------- #

FROZEN_FILES: dict[str, str] = {
    "R4_POPULATION_FREEZE.md": "850b6b24da61f416b76d0bac83a4ba2775d3002e94894f003fd2e0a5488fee2a",
    "R4_CALIBRATION_FAMILY_FREEZE.md": (
        "1fd06ad4804cb64cd9220cc86187e26f6d690fba977bd76918e057bab418cdff"
    ),
    "R4_INFERENCE_MULTIPLICITY_FREEZE.json": (
        "fdc07904056fd72bdd702e275743839eea741364324bd169ec2bf97504a45ad1"
    ),
    "R4_PREDICTOR_FREEZE.json": (
        "423c5cdaf68ce7cdbbb80cf704ed18f67692995e418d0dc8f707871322554f8c"
    ),
    "R4_MEASUREMENT_EXECUTION_CONTRACT.json": (
        "c9d61ed3011a3d42c1455c8e6ff1c724d80a5ceebc2f507992e371d661e15e52"
    ),
    "R4_FINAL_PROTOCOL_FREEZE.json": (
        "8d105b2010227b0b6467f3384ca471e536f2ae877ba351546bf4088f501d0fb6"
    ),
    "R4_EXECUTION_MANIFEST_FREEZE.json": (
        "8b56f62bfe053ddbc92518f92f7aac9da9f6b02af342699eb4db0ee12e61721d"
    ),
    "R4_EPOCH1_RAW_MEASUREMENT_EVIDENCE_LEDGER.json": (
        "146ad254dda64778cb684283e24ae1dca2987bc6827652c448739b75ae2e1a6a"
    ),
    "R4_FORMAL_ANALYSIS_INPUT_REGISTRY.json": (
        "cb3e7625ecfcb7ec6dd71431739969eaf7f05eb1ca6a262cd8e5d3276c632921"
    ),
    "R4_FORMAL_ANALYSIS_DEPENDENCY_GRAPH.json": (
        "fd1248052402de5c6b575957f7465b8f6094455851a16528ea92bc0242d16872"
    ),
}

FROZEN_SCIENTIFIC_IMPLEMENTATIONS: dict[str, str] = {
    "r4_calibration_families.py": (
        "e5b00548429b5b0999d5847db47e1f4c1ae113ee19854c053aeaca1058536ec3"
    ),
    "r3_protocol.py": "46a7c0ec8e5da95a37868d89f5fc110687e66e65599ee4ac3d0602100435197e",
}

MEASUREMENT_CONTRACT_FINGERPRINT = (
    "7b126d300e774cb44d2c47fcb12513865d03c2b08ffd03a5ce409b2ea976e1e5"
)
FINAL_PROTOCOL_FINGERPRINT = "d1b56d702e1f260cef47eee05b7d878ace07a15168e89408e15e7eb741c0ad34"
EXECUTION_MANIFEST_FINGERPRINT = (
    "f32381c51db24f5dbeb240b5e0fdf73c59a56a615c8607ad8979e2a7e2586775"
)
LEDGER_FINGERPRINT = "2ed383f67be4476024d12a03c26699a1a50ed8656d75bb089986ce558d1be541"
ENVIRONMENT_MAP_FINGERPRINT = (
    "aebeb528b6db1d09d23c83ff8078e5a9cb0b779c8fbada0f19617c878cfb45eb"
)
ANALYSIS_REGISTRY_FINGERPRINT = (
    "b0051d96eaeea693a37a0116ced4eecc7e7a7fcd34d93049b074a7010c8cb355"
)
ANALYSIS_DEPENDENCY_GRAPH_FINGERPRINT = (
    "449c9b19d61e4edbe95ea856b1d13e3b373765f8a9d05931f20e4d12bf28ed9f"
)
ANALYSIS_PREFLIGHT_FINGERPRINT = (
    "500ae1cb5ee19d030dad6c27a164b84650adbd79d81451f416126892d2e48873"
)
RAW_MEASUREMENT_FREEZE_COMMIT = "3aae4528a131ba32582fb015bd2f6a4d201da457"
PRODUCTION_CODE_EQUIVALENCE_ANCHOR = "65eb75ceabecbd5f30c07135b62c184d028b4f0f"
MEASUREMENT_CODE_COMMIT = "100c918345ff829dd6fdb96bf99cd14285d6472f"

FORMAL_ANALYSIS_ROOT = Path("/root/rivermind-data/r4-formal-analysis")
QUALIFICATION_ROOT = Path("/root/rivermind-data/r4-analysis-runner-qualification")
RAW_EVIDENCE_ROOT = Path("/root/rivermind-data/r4-formal-measurements")

RUNNER_ID = "r4-integrated-formal-analysis-runner"
RUNNER_VERSION = 1
RUNNER_CONTRACT_ID = "r4-formal-analysis-runner-contract"
ANALYSIS_RESULT_FINGERPRINT_VERSION = 1

RUNNER_SOURCE_PATH = CAL_DIR / "run_r4_analysis.py"

# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #


class R4AnalysisError(RuntimeError):
    """Base error for the R4 analysis runner."""


class R4AnalysisAuthorityError(R4AnalysisError):
    """A frozen authority artifact or implementation drifted."""


class R4AnalysisInputError(R4AnalysisError):
    """The frozen raw-evidence input is structurally unusable."""


class R4AnalysisContractViolation(R4AnalysisError):
    """The runner contract is violated."""


class R4AnalysisOutcomeFirewallBreach(R4AnalysisError):
    """A mode touched formal outcomes it must not touch."""


class R4AnalysisFormalRootConflict(R4AnalysisError):
    """The formal output root is not fresh and holds no resumable checkpoint."""


class R4AnalysisUnfrozenChoice(R4AnalysisError):
    """A required scientific choice has no frozen authority."""


# --------------------------------------------------------------------------- #
# Sibling module loading
# --------------------------------------------------------------------------- #


def _load_sibling(name: str) -> Any:
    module = sys.modules.get(name)
    if module is not None:
        return module
    spec = importlib.util.spec_from_file_location(name, CAL_DIR / f"{name}.py")
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load {name}.py from {CAL_DIR}")
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


r4_inference = _load_sibling("r4_inference")
r4_predictor = _load_sibling("r4_predictor")
r4_calibration_families = _load_sibling("r4_calibration_families")
r3_protocol = _load_sibling("r3_protocol")
r3_analysis = _load_sibling("r3_analysis")

R4InferenceRow = r4_inference.R4InferenceRow
PopulationMetadata = r4_inference.PopulationMetadata
TestDraw = r4_inference.TestDraw


# --------------------------------------------------------------------------- #
# Hashing helpers
# --------------------------------------------------------------------------- #


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def write_atomic(path: Path, text: str) -> None:
    """Temp-write, fsync and atomically rename (never a partial file)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
# Frozen authority loading
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class FrozenAuthority:
    measurement_contract_fingerprint: str
    final_protocol_fingerprint: str
    execution_manifest_fingerprint: str
    ledger_fingerprint: str
    environment_map_fingerprint: str
    registry_fingerprint: str
    dependency_graph_fingerprint: str
    preflight_fingerprint: str
    raw_measurement_freeze_commit: str
    measurement_code_commit: str
    population_metadata: Mapping[str, PopulationMetadata]
    model_order: tuple[str, ...]
    population_order: tuple[str, ...]
    direction_order: tuple[str, ...]
    procedure_order: tuple[str, ...]


def _verify_frozen_file(name: str) -> Path:
    path = CAL_DIR / name
    if not path.is_file():
        raise R4AnalysisAuthorityError(f"missing frozen authority file {name}")
    expected = FROZEN_FILES[name]
    actual = sha256_file(path)
    if actual != expected:
        raise R4AnalysisAuthorityError(f"frozen file {name} drifted: {actual} != {expected}")
    return path


def _verify_frozen_implementation(name: str) -> Path:
    path = CAL_DIR / name
    expected = FROZEN_SCIENTIFIC_IMPLEMENTATIONS[name]
    actual = sha256_file(path)
    if actual != expected:
        raise R4AnalysisAuthorityError(
            f"frozen statistical implementation {name} drifted: {actual} != {expected}"
        )
    return path


def load_frozen_authority() -> FrozenAuthority:
    """Verify every frozen authority and derive the canonical orders."""
    for name in FROZEN_FILES:
        _verify_frozen_file(name)
    for name in FROZEN_SCIENTIFIC_IMPLEMENTATIONS:
        _verify_frozen_implementation(name)

    registry = json.loads(
        (CAL_DIR / "R4_FORMAL_ANALYSIS_INPUT_REGISTRY.json").read_text(encoding="utf-8")
    )
    if registry["registry_fingerprint"] != ANALYSIS_REGISTRY_FINGERPRINT:
        raise R4AnalysisAuthorityError("analysis input registry fingerprint drifted")
    ledger = json.loads(
        (CAL_DIR / "R4_EPOCH1_RAW_MEASUREMENT_EVIDENCE_LEDGER.json").read_text(encoding="utf-8")
    )
    if ledger["ledger_fingerprint"] != LEDGER_FINGERPRINT:
        raise R4AnalysisAuthorityError("raw-evidence ledger fingerprint drifted")
    if ledger["environment_map_fingerprint"] != ENVIRONMENT_MAP_FINGERPRINT:
        raise R4AnalysisAuthorityError("environment map fingerprint drifted")
    if ledger["measurement_code_commit"] != MEASUREMENT_CODE_COMMIT:
        raise R4AnalysisAuthorityError("measurement code commit drifted")
    inference = json.loads(
        (CAL_DIR / "R4_INFERENCE_MULTIPLICITY_FREEZE.json").read_text(encoding="utf-8")
    )["frozen_semantic_payload"]
    panel = inference["prospective_primary_panel"]

    populations: dict[str, PopulationMetadata] = {}
    for block in panel["populations"]:
        n912 = block["n912_manifest"] or {}
        populations[block["population_id"]] = PopulationMetadata(
            population_id=block["population_id"],
            population_fingerprint=block["manifest_fingerprint"],
            stratum_field=block["stratum_field"],
            group_field=block["group_field"],
            test_bootstrap_protocol_id=block["test_bootstrap_protocol_id"],
            test_bootstrap_protocol_version=block["test_bootstrap_protocol_version"],
            test_bootstrap_mode=block["test_bootstrap_mode"],
            estimand_weighting=block["estimand_weighting"],
            test_count=block["test_count"],
            train_count=block["train_count"],
            n912_manifest_fingerprint=n912.get("manifest_fingerprint"),
            n912_train_count=n912.get("train_count"),
        )

    model_order = tuple(block["model_id"] for block in panel["models"]) + tuple(
        block["model_id"] for block in inference["legacy_secondary_panel"]["models"]
    )
    population_order = tuple(block["population_id"] for block in panel["populations"])
    return FrozenAuthority(
        measurement_contract_fingerprint=MEASUREMENT_CONTRACT_FINGERPRINT,
        final_protocol_fingerprint=FINAL_PROTOCOL_FINGERPRINT,
        execution_manifest_fingerprint=EXECUTION_MANIFEST_FINGERPRINT,
        ledger_fingerprint=LEDGER_FINGERPRINT,
        environment_map_fingerprint=ENVIRONMENT_MAP_FINGERPRINT,
        registry_fingerprint=ANALYSIS_REGISTRY_FINGERPRINT,
        dependency_graph_fingerprint=ANALYSIS_DEPENDENCY_GRAPH_FINGERPRINT,
        preflight_fingerprint=ANALYSIS_PREFLIGHT_FINGERPRINT,
        raw_measurement_freeze_commit=RAW_MEASUREMENT_FREEZE_COMMIT,
        measurement_code_commit=MEASUREMENT_CODE_COMMIT,
        population_metadata=populations,
        model_order=model_order,
        population_order=population_order,
        direction_order=tuple(r4_inference.DIRECTIONS),
        procedure_order=tuple(r4_inference.ALL_PROCEDURES),
    )


# --------------------------------------------------------------------------- #
# Cell registry and directional units
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class AnalysisCell:
    cell_id: str
    model_key: str
    model_id: str
    model_revision: str
    model_role: str
    population_key: str
    population_id: str
    population_manifest_fingerprint: str
    dataset_id: str
    dataset_revision: str
    train_budget: str
    stratum_field: str
    group_id_field: str | None
    path: Path
    sha256: str
    evidence_fingerprint: str
    split_counts: Mapping[str, int]


@dataclass(frozen=True)
class AnalysisUnit:
    unit_id: str
    model_key: str
    model_id: str
    model_revision: str
    population_key: str
    population_id: str
    direction_id: str
    cell_id: str
    role: str


def load_cells() -> tuple[AnalysisCell, ...]:
    registry = json.loads(
        (CAL_DIR / "R4_FORMAL_ANALYSIS_INPUT_REGISTRY.json").read_text(encoding="utf-8")
    )
    cells: list[AnalysisCell] = []
    for block in registry["cell_artifacts"]:
        cells.append(
            AnalysisCell(
                cell_id=block["cell_id"],
                model_key=block["model_key"],
                model_id=block["model_id"],
                model_revision=block["model_revision"],
                model_role=block["model_role"],
                population_key=block["population_key"],
                population_id=block["population_id"],
                population_manifest_fingerprint=block["population_manifest_fingerprint"],
                dataset_id=block["dataset_id"],
                dataset_revision=block["dataset_revision"],
                train_budget=block["train_budget"],
                stratum_field=block["stratum_field"],
                group_id_field=block["group_id_field"],
                path=Path(block["path"]),
                sha256=block["sha256"],
                evidence_fingerprint=block["evidence_fingerprint"],
                split_counts=block["split_counts"],
            )
        )
    cells.sort(key=lambda cell: cell.cell_id)
    return tuple(cells)


def enumerate_units(
    cells: Sequence[AnalysisCell], authority: FrozenAuthority
) -> tuple[AnalysisUnit, ...]:
    """24 current-generation primary units + 8 legacy secondary units."""
    units: list[AnalysisUnit] = []
    for cell in cells:
        for direction in authority.direction_order:
            units.append(
                AnalysisUnit(
                    unit_id=f"{cell.model_key}|{cell.population_id}|{direction}",
                    model_key=cell.model_key,
                    model_id=cell.model_id,
                    model_revision=cell.model_revision,
                    population_key=cell.population_key,
                    population_id=cell.population_id,
                    direction_id=direction,
                    cell_id=cell.cell_id,
                    role=cell.model_role,
                )
            )
    model_rank = {model: index for index, model in enumerate(authority.model_order)}
    population_rank = {
        population: index for index, population in enumerate(authority.population_order)
    }
    direction_rank = {direction: index for index, direction in enumerate(authority.direction_order)}
    units.sort(
        key=lambda unit: (
            model_rank[unit.model_id],
            population_rank[unit.population_id],
            direction_rank[unit.direction_id],
        )
    )
    return tuple(units)


def primary_units(units: Sequence[AnalysisUnit]) -> tuple[AnalysisUnit, ...]:
    return tuple(unit for unit in units if unit.role == "current-generation")


def legacy_units(units: Sequence[AnalysisUnit]) -> tuple[AnalysisUnit, ...]:
    return tuple(unit for unit in units if unit.role != "current-generation")


# --------------------------------------------------------------------------- #
# Raw-evidence loading and row adaptation
# --------------------------------------------------------------------------- #

REQUIRED_ITEM_KEYS = (
    "item_id",
    "split",
    "stratum",
    "anchor",
    "fixed_event",
    "group_id",
    "cat",
    "ovr",
)


def load_cell_payload(cell: AnalysisCell, *, verify_hash: bool = True) -> Mapping[str, Any]:
    if not cell.path.is_file():
        raise R4AnalysisInputError(f"missing raw-evidence artifact {cell.path}")
    if verify_hash:
        actual = sha256_file(cell.path)
        if actual != cell.sha256:
            raise R4AnalysisInputError(f"raw-evidence sha256 drifted for {cell.cell_id}: {actual}")
    payload = json.loads(cell.path.read_text(encoding="utf-8"))
    if payload.get("evidence_fingerprint") != cell.evidence_fingerprint:
        raise R4AnalysisInputError(f"evidence fingerprint drifted for {cell.cell_id}")
    items = payload.get("items")
    if not isinstance(items, list):
        raise R4AnalysisInputError(f"raw evidence for {cell.cell_id} has no items list")
    return payload


def iter_items(payload: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    return payload["items"]


def structural_item_check(item: Mapping[str, Any], cell_id: str) -> None:
    for key in REQUIRED_ITEM_KEYS:
        if key not in item:
            raise R4AnalysisInputError(f"{cell_id}: item missing key {key!r}")
    if item["split"] not in ("TRAIN", "TEST"):
        raise R4AnalysisInputError(f"{cell_id}: unknown split {item['split']!r}")
    if int(item["fixed_event"]) not in (0, 1):
        raise R4AnalysisInputError(f"{cell_id}: fixed_event outside {{0, 1}}")
    for block in ("cat", "ovr"):
        if item[block].get("status") != "scored":
            raise R4AnalysisInputError(f"{cell_id}: {block} status is not scored")


def item_to_row(
    item: Mapping[str, Any], cell: AnalysisCell, population_id: str
) -> R4InferenceRow:
    return R4InferenceRow(
        item_id=str(item["item_id"]),
        population_id=population_id,
        stratum=str(item["stratum"]),
        label=int(item["fixed_event"]),
        cat_score=float(item["cat"]["anchor_score"]),
        ovr_score=float(item["ovr"]["probability_true"]),
        cluster_id=(None if item["group_id"] is None else str(item["group_id"])),
        anchor_index=int(item["candidate_order"].index(str(item["anchor"]))),
    )


def rows_by_split(
    payload: Mapping[str, Any], cell: AnalysisCell
) -> dict[str, tuple[R4InferenceRow, ...]]:
    buckets: dict[str, list[R4InferenceRow]] = {"TRAIN": [], "TEST": []}
    for item in iter_items(payload):
        structural_item_check(item, cell.cell_id)
        buckets[item["split"]].append(item_to_row(item, cell, cell.population_id))
    return {
        split: tuple(sorted(rows, key=lambda row: row.item_id))
        for split, rows in buckets.items()
    }


def primary_train_item_ids(cell: AnalysisCell) -> frozenset[str] | None:
    """The frozen N456 nested TRAIN subset of a 912-row new-population cell."""
    if cell.train_budget != "N912":
        return None
    manifests = {
        "hellaswag": (
            "hellaswag_population_candidate.json",
            "5c45043ba4f0ec436c16dcf494ff26be435c7857244bcbefa321d1678129c400",
        ),
        "medmcqa": (
            "medmcqa_population_candidate.json",
            "4a4718438d46ab1ba27c59ca46806756ffb62efa05e6103981dffec4dc48c218",
        ),
    }
    entry = manifests.get(cell.population_key)
    if entry is None:
        return None
    name, expected = entry
    path = POPULATION_CANDIDATE_DIR / name
    if not path.is_file():
        raise R4AnalysisInputError(f"missing frozen primary population manifest {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("manifest_fingerprint") != expected:
        raise R4AnalysisInputError(f"primary population manifest drifted: {path.name}")
    return frozenset(str(item["item_id"]) for item in payload["train"])


def select_train_rows(
    cell: AnalysisCell, rows: Sequence[R4InferenceRow], budget: str
) -> tuple[R4InferenceRow, ...]:
    """Apply the frozen TRAIN budget (N456 primary, N912 nested robustness)."""
    if budget == "N912":
        if cell.train_budget != "N912":
            raise R4AnalysisContractViolation(
                f"cell {cell.cell_id} has no frozen N912 robustness budget"
            )
        if len(rows) != 912:
            raise R4AnalysisContractViolation(
                f"cell {cell.cell_id} N912 TRAIN has {len(rows)} rows"
            )
        return tuple(rows)
    if budget != "N456":
        raise R4AnalysisContractViolation(f"unknown TRAIN budget {budget!r}")
    if len(rows) == 456:
        return tuple(rows)
    subset = primary_train_item_ids(cell)
    if subset is None:
        raise R4AnalysisContractViolation(f"cell {cell.cell_id} N456 subset is not derivable")
    chosen = tuple(row for row in rows if row.item_id in subset)
    if len(chosen) != 456:
        raise R4AnalysisContractViolation(
            f"cell {cell.cell_id} N456 subset has {len(chosen)} rows"
        )
    return chosen


# --------------------------------------------------------------------------- #
# Calibration wiring (frozen implementations only)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ProcedureFit:
    procedure: str
    status: str
    calibrator: Callable[[float], float] | None
    reason: str | None
    state_fingerprint: str | None
    failure_type: str | None = None


AVAILABLE = "AVAILABLE"
INELIGIBLE = "INELIGIBLE"
FAILED = "FAILED"

# Frozen dependency truth table: which fitted map each frozen estimand needs.
# Delta_deploy = R_cross - R_raw  -> cross (source-fitted) map only
# Delta_native = R_native - R_raw -> native (target-fitted) map only
# Delta_transport = R_cross - R_native -> both maps
ESTIMAND_DEPENDENCIES: Mapping[str, tuple[str, ...]] = {
    "Delta_deploy": ("cross",),
    "Delta_native": ("native",),
    "Delta_transport": ("cross", "native"),
}

REFIT_ESTIMANDS: tuple[str, ...] = ("Delta_deploy", "Delta_transport")


def _applicator(apply: Callable[[Any, float], float], fit: Any) -> Callable[[float], float]:
    """Bind a frozen calibration applicator to one fitted state."""

    def bound(score: float) -> float:
        return apply(fit, score)

    return bound


def _training_points(
    rows: Sequence[R4InferenceRow], measurement: str
) -> list[tuple[str, float, float]]:
    return [
        (row.item_id, r4_inference.measurement_score(row, measurement), float(row.label))
        for row in rows
    ]


def fit_procedure(
    *,
    procedure: str,
    train_rows: Sequence[R4InferenceRow],
    measurement: str,
) -> ProcedureFit:
    """Fit one frozen procedure. Never clips, never falls back."""
    scores = [r4_inference.measurement_score(row, measurement) for row in train_rows]
    labels = [int(row.label) for row in train_rows]
    if procedure in r4_inference.LOGISTIC_CORE_PROCEDURES:
        spec = {p.label: p for p in r3_protocol.procedure_panel()}[procedure]
        try:
            fit = r3_analysis.fit_calibrator(
                spec, measurement, _training_points(train_rows, measurement)
            )
        except r3_analysis.ProbabilityEndpointError as exc:
            return ProcedureFit(procedure, INELIGIBLE, None, f"endpoint: {exc}", None)
        except r3_analysis.AnalysisError as exc:  # pragma: no cover - defensive
            return ProcedureFit(
                procedure, FAILED, None, str(exc), None, failure_type=type(exc).__name__
            )
        return ProcedureFit(procedure, AVAILABLE, fit.apply, None, fit.fingerprint)
    if procedure == "I-isotonic":
        try:
            fit = r4_calibration_families.fit_isotonic_fixed_decision_probability(scores, labels)
        except r4_calibration_families.IsotonicContractViolation as exc:
            return ProcedureFit(
                procedure, FAILED, None, str(exc), None, failure_type=type(exc).__name__
            )
        return ProcedureFit(
            procedure,
            AVAILABLE,
            _applicator(r4_calibration_families.apply_isotonic_fixed_decision_probability, fit),
            None,
            fit.state_fingerprint(),
        )
    if procedure == "B-beta":
        try:
            fit = r4_calibration_families.fit_beta_fixed_decision_probability(scores, labels)
        except r4_calibration_families.BetaFitIneligible as exc:
            return ProcedureFit(procedure, INELIGIBLE, None, f"ineligible: {exc}", None)
        except r4_calibration_families.BetaContractViolation as exc:
            return ProcedureFit(
                procedure, FAILED, None, str(exc), None, failure_type=type(exc).__name__
            )
        except r4_calibration_families.BetaImplementationError as exc:
            # Frozen fitting gate 9 ("unique finite accepted optimum") not met.
            # A frozen FULL-FIT FAILED state, never a process exception and never
            # a DEPENDENCY_UNAVAILABLE: the exact class and message are retained.
            return ProcedureFit(
                procedure,
                FAILED,
                None,
                f"{type(exc).__name__}: {exc}",
                None,
                failure_type=type(exc).__name__,
            )
        return ProcedureFit(
            procedure,
            AVAILABLE,
            _applicator(r4_calibration_families.apply_beta_fixed_decision_probability, fit),
            None,
            fit.state_fingerprint(),
        )
    raise R4AnalysisUnfrozenChoice(f"procedure {procedure!r} has no frozen implementation")


# --------------------------------------------------------------------------- #
# Panel analysis (point estimates, TEST bootstrap, TRAIN refit)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class PanelInputs:
    authority: FrozenAuthority
    model_keys: Mapping[str, str]
    train_rows: Mapping[tuple[str, str], tuple[R4InferenceRow, ...]]
    test_rows: Mapping[tuple[str, str], tuple[R4InferenceRow, ...]]
    fits: Mapping[tuple[str, str, str], ProcedureFit]


def build_panel_inputs(
    authority: FrozenAuthority,
    cells: Sequence[AnalysisCell],
    *,
    population_ids: Sequence[str],
    budget: str,
) -> PanelInputs:
    """Load every cell of the declared population panel and fit all procedures."""
    wanted = set(population_ids)
    train: dict[tuple[str, str], tuple[R4InferenceRow, ...]] = {}
    test: dict[tuple[str, str], tuple[R4InferenceRow, ...]] = {}
    fits: dict[tuple[str, str, str], ProcedureFit] = {}
    model_keys: dict[str, str] = {}
    for cell in cells:
        if cell.population_id not in wanted:
            continue
        payload = load_cell_payload(cell)
        splits = rows_by_split(payload, cell)
        test[(cell.model_key, cell.population_id)] = splits["TEST"]
        selected = select_train_rows(cell, splits["TRAIN"], budget)
        train[(cell.model_key, cell.population_id)] = selected
        model_keys[cell.model_id] = cell.model_key
        for direction in authority.direction_order:
            source = r4_inference.source_measurement(direction)
            target = r4_inference.target_measurement(direction)
            for procedure in authority.procedure_order:
                cross_key = (cell.model_key, cell.population_id, f"{procedure}|{direction}|cross")
                native_key = (cell.model_key, cell.population_id, f"{procedure}|{direction}|native")
                fits[cross_key] = fit_procedure(
                    procedure=procedure, train_rows=selected, measurement=source
                )
                fits[native_key] = fit_procedure(
                    procedure=procedure, train_rows=selected, measurement=target
                )
    return PanelInputs(
        authority=authority,
        model_keys=model_keys,
        train_rows=train,
        test_rows=test,
        fits=fits,
    )


def available_procedures(
    inputs: PanelInputs, *, models: Sequence[str], populations: Sequence[str]
) -> tuple[str, ...]:
    """Procedures available for EVERY panel member (fail-closed, no shrinking)."""
    out: list[str] = []
    for procedure in inputs.authority.procedure_order:
        ok = True
        for model in models:
            for population in populations:
                for direction in inputs.authority.direction_order:
                    for side in ("cross", "native"):
                        key = (model, population, f"{procedure}|{direction}|{side}")
                        fit = inputs.fits.get(key)
                        if fit is None or fit.status != AVAILABLE:
                            ok = False
                            break
                    if not ok:
                        break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            out.append(procedure)
    return tuple(out)


def _reindexed_rows(draw: TestDraw, rows: Sequence[R4InferenceRow]) -> tuple[R4InferenceRow, ...]:
    """Apply a shared draw selection to one model's own rows (same item ids)."""
    lookup = {row.item_id: row for row in rows}
    try:
        return tuple(lookup[row.item_id] for row in draw.occurrences)
    except KeyError as exc:  # pragma: no cover - defensive
        raise R4AnalysisInputError(f"draw references unknown item {exc}") from exc


def _cross_native_fits(
    inputs: PanelInputs, *, model: str, population: str, procedure: str, direction: str
) -> tuple[ProcedureFit, ProcedureFit]:
    """The SOURCE-fitted (cross) and TARGET-fitted (native) fits of one cell."""
    return (
        inputs.fits[(model, population, f"{procedure}|{direction}|cross")],
        inputs.fits[(model, population, f"{procedure}|{direction}|native")],
    )


def unit_estimand_keys(
    inputs: PanelInputs,
    *,
    models: Sequence[str],
    populations: Sequence[str],
    direction: str,
    procedure: str,
) -> tuple[str, ...]:
    """Estimands computable for EVERY model and population of a panel (fail-closed).

    The frozen shared-draw engine requires one consistent estimand key set per
    ``(direction, procedure)`` across every model and population, so an estimand is
    offered only when every model of every population of the panel can compute it
    from its own AVAILABLE fitted maps. A member that cannot be computed is absent,
    and the frozen family block reports the fixed-size family as INCOMPLETE instead
    of shrinking it.
    """
    keys: list[str] = []
    for estimand, dependencies in ESTIMAND_DEPENDENCIES.items():
        ok = True
        for model in models:
            for population in populations:
                cross, native = _cross_native_fits(
                    inputs,
                    model=model,
                    population=population,
                    procedure=procedure,
                    direction=direction,
                )
                for dependency in dependencies:
                    fit = cross if dependency == "cross" else native
                    if fit.status != AVAILABLE:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            keys.append(estimand)
    return tuple(keys)


def unit_estimator_factory(
    inputs: PanelInputs, *, models: Sequence[str], populations: Sequence[str]
) -> Callable[[str, str, str, str, TestDraw], Mapping[str, float]]:
    """Return the frozen ``unit_estimator`` callback for the panel bootstrap."""
    cache: dict[tuple[str, str], tuple[str, ...]] = {}

    def keys_for(direction: str, procedure: str) -> tuple[str, ...]:
        key = (direction, procedure)
        if key not in cache:
            cache[key] = unit_estimand_keys(
                inputs,
                models=models,
                populations=populations,
                direction=direction,
                procedure=procedure,
            )
        return cache[key]

    def unit_estimator(
        population: str, model: str, direction: str, procedure: str, draw: TestDraw
    ) -> Mapping[str, float]:
        rows = _reindexed_rows(draw, inputs.test_rows[(model, population)])
        cross, native = _cross_native_fits(
            inputs, model=model, population=population, procedure=procedure, direction=direction
        )
        out: dict[str, float] = {}
        for estimand in keys_for(direction, procedure):
            if estimand == "Delta_deploy":
                out[estimand] = float(
                    r4_inference.delta_deploy(rows, direction, cross.calibrator)
                )
            elif estimand == "Delta_native":
                out[estimand] = float(
                    r4_inference.delta_native(rows, direction, native.calibrator)
                )
            else:
                out[estimand] = float(
                    r4_inference.delta_transport(
                        rows, direction, cross.calibrator, native.calibrator
                    )
                )
        return out

    return unit_estimator


def point_estimates(
    inputs: PanelInputs, *, models: Sequence[str], populations: Sequence[str]
) -> dict[str, Any]:
    """Full-TRAIN fitted point estimates (no bootstrap, no multiplicity).

    Every frozen estimand follows its own dependency rule: ``Delta_deploy`` needs
    only the SOURCE-fitted map, ``Delta_native`` only the TARGET-fitted map and
    ``Delta_transport`` both. A failed or ineligible fit never removes the other
    estimands of the same cell.
    """
    out: dict[str, Any] = {}
    for model in models:
        for population in populations:
            for direction in inputs.authority.direction_order:
                rows = inputs.test_rows[(model, population)]
                for procedure in inputs.authority.procedure_order:
                    cross, native = _cross_native_fits(
                        inputs,
                        model=model,
                        population=population,
                        procedure=procedure,
                        direction=direction,
                    )
                    key = f"{model}|{population}|{direction}|{procedure}"
                    entry: dict[str, Any] = {
                        "cross_status": cross.status,
                        "native_status": native.status,
                        "cross_reason": cross.reason,
                        "native_reason": native.reason,
                        "cross_failure_type": cross.failure_type,
                        "native_failure_type": native.failure_type,
                        "estimands": {},
                    }
                    if cross.status == AVAILABLE:
                        entry["estimands"]["Delta_deploy"] = float(
                            r4_inference.delta_deploy(rows, direction, cross.calibrator)
                        )
                    if native.status == AVAILABLE:
                        entry["estimands"]["Delta_native"] = float(
                            r4_inference.delta_native(rows, direction, native.calibrator)
                        )
                    if cross.status == AVAILABLE and native.status == AVAILABLE:
                        entry["estimands"]["Delta_transport"] = float(
                            r4_inference.delta_transport(
                                rows, direction, cross.calibrator, native.calibrator
                            )
                        )
                        entry["risk_matrix"] = r4_inference.risk_matrix(
                            rows, direction, cross.calibrator, native.calibrator
                        )
                        entry["status"] = AVAILABLE
                    elif cross.status == FAILED or native.status == FAILED:
                        entry["status"] = FAILED
                    else:
                        entry["status"] = INELIGIBLE
                    out[key] = entry
    return out


def _empty_panel_bootstrap(
    *, replicates: int, models: Sequence[str], populations: Sequence[str],
    directions: Sequence[str], procedures: Sequence[str],
) -> Any:
    return r4_inference.PanelBootstrapResult(
        replicates=replicates,
        models=tuple(models),
        populations=tuple(populations),
        directions=tuple(directions),
        procedures=tuple(procedures),
        unit_values={},
        population_values={},
        panel_values={},
        primary_contrasts={},
        direction_differences={},
        extension_panel={},
        native_reference={},
    )


def _merge_panel_bootstraps(
    results: Sequence[Any],
    *,
    replicates: int,
    models: Sequence[str],
    populations: Sequence[str],
    directions: Sequence[str],
    procedures: Sequence[str],
) -> Any:
    """Merge dependency-safe sub-calls. Draws are replicate-index deterministic."""
    merged: dict[str, dict[Any, Any]] = {
        field: {}
        for field in (
            "unit_values",
            "population_values",
            "panel_values",
            "primary_contrasts",
            "direction_differences",
            "extension_panel",
            "native_reference",
        )
    }
    for result in results:
        for field, target in merged.items():
            target.update(getattr(result, field))
    return r4_inference.PanelBootstrapResult(
        replicates=replicates,
        models=tuple(models),
        populations=tuple(populations),
        directions=tuple(directions),
        procedures=tuple(procedures),
        **merged,
    )


def run_test_bootstrap(
    inputs: PanelInputs,
    *,
    models: Sequence[str],
    populations: Sequence[str],
    procedures: Sequence[str],
    replicates: int,
) -> Any:
    """Frozen shared-draw TEST bootstrap over the declared panel.

    Dependency sets are determined first, so the frozen engine is never handed a
    ``(direction, procedure)`` group whose estimands cannot be computed for every
    model and population.  A group that is computable for only one direction is
    run separately; every sub-call uses the same replicate-index-deterministic
    draws, so the shared-draw contract is preserved.  An entirely unavailable
    group contributes nothing and its fixed-size family members report INCOMPLETE.
    """
    directions = tuple(inputs.authority.direction_order)
    keys = {
        (direction, procedure): unit_estimand_keys(
            inputs,
            models=models,
            populations=populations,
            direction=direction,
            procedure=procedure,
        )
        for direction in directions
        for procedure in procedures
    }
    rows_by_population = {p: inputs.test_rows[(models[0], p)] for p in populations}
    metadata_by_population = {
        p: inputs.authority.population_metadata[p] for p in populations
    }
    unit_estimator = unit_estimator_factory(
        inputs, models=models, populations=populations
    )

    def call(direction_subset: Sequence[str], procedure_subset: Sequence[str]) -> Any:
        return r4_inference.run_panel_test_bootstrap(
            rows_by_population=rows_by_population,
            metadata_by_population=metadata_by_population,
            unit_estimator=unit_estimator,
            replicates=replicates,
            models=models,
            populations=populations,
            directions=direction_subset,
            procedures=procedure_subset,
        )

    results: list[Any] = []
    fully_available = tuple(
        procedure
        for procedure in procedures
        if all(keys[(direction, procedure)] for direction in directions)
    )
    if fully_available:
        results.append(call(directions, fully_available))
    for procedure in procedures:
        if procedure in fully_available:
            continue
        partial = tuple(
            direction for direction in directions if keys[(direction, procedure)]
        )
        if partial:
            results.append(call(partial, (procedure,)))
    if not results:
        return _empty_panel_bootstrap(
            replicates=replicates,
            models=models,
            populations=populations,
            directions=directions,
            procedures=procedures,
        )
    return _merge_panel_bootstraps(
        results,
        replicates=replicates,
        models=models,
        populations=populations,
        directions=directions,
        procedures=procedures,
    )


def run_refit_blocks(
    inputs: PanelInputs,
    *,
    models: Sequence[str],
    populations: Sequence[str],
    procedures: Sequence[str],
    replicates: int,
) -> dict[str, Any]:
    """Frozen TRAIN-refit blocks (one per unit x procedure x estimand).

    Every frozen estimand follows its own dependency rule, and every frozen
    required procedure is covered: a block is only skipped when the frozen
    dependency truth table says it cannot exist. Any single failed refit
    replicate makes that block INCOMPLETE with ``interval = None``; no
    successful-subset interval is ever produced.
    """
    out: dict[str, Any] = {}
    for model in models:
        for population in populations:
            for direction in inputs.authority.direction_order:
                for procedure in procedures:
                    cross, native = _cross_native_fits(
                        inputs,
                        model=model,
                        population=population,
                        procedure=procedure,
                        direction=direction,
                    )
                    for estimand in REFIT_ESTIMANDS:
                        dependencies = ESTIMAND_DEPENDENCIES[estimand]
                        if any(
                            (cross if dependency == "cross" else native).status != AVAILABLE
                            for dependency in dependencies
                        ):
                            continue
                        key = f"{model}|{population}|{direction}|{procedure}|{estimand}"

                        def fit_and_evaluate(
                            replicate_index: int,
                            *,
                            model=model,
                            population=population,
                            direction=direction,
                            procedure=procedure,
                            estimand=estimand,
                        ) -> float:
                            train_rows = inputs.train_rows[(model, population)]
                            draw = r4_inference.build_train_refit_draw(
                                train_rows,
                                inputs.authority.population_metadata[population],
                                replicate_index,
                            )
                            resampled = draw.occurrences
                            source = r4_inference.source_measurement(direction)
                            target = r4_inference.target_measurement(direction)
                            new_cross = fit_procedure(
                                procedure=procedure, train_rows=resampled, measurement=source
                            )
                            new_native = fit_procedure(
                                procedure=procedure, train_rows=resampled, measurement=target
                            )
                            if new_cross.status != AVAILABLE or new_native.status != AVAILABLE:
                                raise r4_inference.BootstrapContractViolation(
                                    "refit calibrator is unavailable: "
                                    f"cross={new_cross.reason!r} native={new_native.reason!r}"
                                )
                            rows = inputs.test_rows[(model, population)]
                            if estimand == "Delta_deploy":
                                return float(
                                    r4_inference.delta_deploy(
                                        rows, direction, new_cross.calibrator
                                    )
                                )
                            return float(
                                r4_inference.delta_transport(
                                    rows, direction, new_cross.calibrator, new_native.calibrator
                                )
                            )

                        out[key] = r4_inference.run_train_refit_block(
                            replicate_indices=tuple(range(replicates)),
                            procedure=procedure,
                            model=model,
                            population=population,
                            measurement_dependency=r4_inference.target_measurement(direction),
                            direction_dependency=direction,
                            fit_and_evaluate=fit_and_evaluate,
                        )
    return out


# --------------------------------------------------------------------------- #
# Predictor wiring
# --------------------------------------------------------------------------- #


def frozen_predictor_units() -> tuple[Any, ...]:
    """Every frozen predictor unit (8 development + 16 validation + 8 legacy)."""
    return (
        *r4_predictor.development_units(),
        *r4_predictor.primary_validation_units(),
        *r4_predictor.legacy_extension_units(),
    )


def model_key_by_model_id(inputs: PanelInputs) -> dict[str, str]:
    return dict(inputs.model_keys)


def core4_means(
    inputs: PanelInputs,
    *,
    model_key: str,
    population_id: str,
    direction: str,
    rows: Sequence[R4InferenceRow],
) -> tuple[float | None, float | None]:
    """The frozen CORE4-mean transport penalty / deployment delta for one draw."""
    transport: dict[str, float] = {}
    deploy: dict[str, float] = {}
    for procedure in r4_predictor.CORE4_PROCEDURES:
        cross = inputs.fits[(model_key, population_id, f"{procedure}|{direction}|cross")]
        native = inputs.fits[(model_key, population_id, f"{procedure}|{direction}|native")]
        if cross.calibrator is None or native.calibrator is None:
            return (None, None)
        matrix = r4_inference.risk_matrix(rows, direction, cross.calibrator, native.calibrator)
        transport[procedure] = float(matrix.delta_transport)
        deploy[procedure] = float(matrix.delta_deploy)
    return (
        float(r4_predictor.core4_mean_transport_penalty(transport)),
        float(r4_predictor.core4_mean_deployment_delta(deploy)),
    )


def build_predictor_measurements(inputs: PanelInputs) -> tuple[Any, ...]:
    """Build the frozen ``PredictorUnitMeasurement`` for every frozen unit."""
    keys = model_key_by_model_id(inputs)
    measurements: list[Any] = []
    for unit in frozen_predictor_units():
        model_key = keys[unit.model_id]
        train_rows = inputs.train_rows[(model_key, unit.population_id)]
        test_rows = inputs.test_rows[(model_key, unit.population_id)]
        source = r4_inference.source_measurement(unit.direction_id)
        source_scores = tuple(
            r4_inference.measurement_score(row, source) for row in train_rows
        )

        def y_provider(
            draw: TestDraw,
            *,
            model_key: str = model_key,
            population_id: str = unit.population_id,
            direction: str = unit.direction_id,
            test_rows: tuple[R4InferenceRow, ...] = test_rows,
        ) -> tuple[float | None, float | None]:
            return core4_means(
                inputs,
                model_key=model_key,
                population_id=population_id,
                direction=direction,
                rows=_reindexed_rows(draw, test_rows),
            )

        measurements.append(
            r4_predictor.PredictorUnitMeasurement(
                unit=unit,
                source_train_scores=source_scores,
                target_test_rows=test_rows,
                y_provider=y_provider,
            )
        )
    return tuple(measurements)


def predictor_point_rows(measurements: Sequence[Any]) -> tuple[Any, ...]:
    """Full-data (unresampled) predictor validation rows for the 16 heldout units."""
    out: list[Any] = []
    for measurement in sorted(measurements, key=lambda item: item.unit.unit_id):
        if measurement.unit.analysis_role != r4_predictor.ROLE_PRIMARY_VALIDATION:
            continue
        direction = measurement.unit.direction_id
        target = r4_inference.target_measurement(direction)
        target_scores = tuple(
            r4_inference.measurement_score(row, target)
            for row in measurement.target_test_rows
        )
        x_range = float(
            r4_predictor.range_exceedance_warning(
                measurement.source_train_scores, target_scores
            ).fraction_outside
        )
        x_w1 = float(
            r4_predictor.exact_empirical_wasserstein1(
                measurement.source_train_scores, target_scores
            )
        )
        transport, deploy = core4_means_on_rows(measurement)
        out.append(
            r4_predictor.PredictorValidationRow(
                unit=measurement.unit,
                x_range=x_range,
                x_wasserstein1=x_w1,
                y_transport_core=transport,
                y_deploy_core=deploy,
            )
        )
    return tuple(out)


def core4_means_on_rows(measurement: Any) -> tuple[float | None, float | None]:
    """CORE4 means on the untouched TARGET TEST rows of one unit measurement."""
    provider = measurement.y_provider
    draw = _full_test_draw(measurement)
    return provider(draw)


def _full_test_draw(measurement: Any) -> TestDraw:
    """A synthetic draw that reproduces the untouched TEST rows exactly."""
    rows = measurement.target_test_rows
    return TestDraw(
        population_id=measurement.unit.population_id,
        replicate_index=0,
        protocol_id="r4-runner-full-test-reference",
        protocol_version=1,
        mode="full-test-reference",
        stratum_order=tuple(sorted({row.stratum for row in rows})),
        per_stratum_occurrences={},
        occurrences=tuple(rows),
        provenance={"purpose": "full-TEST point estimate, no resampling"},
    )


def run_predictor_bootstrap(
    *,
    measurements: Sequence[Any],
    canonical_rows: Mapping[str, tuple[R4InferenceRow, ...]],
    metadata: Mapping[str, PopulationMetadata],
    replicates: int,
    point_estimate: float | None = None,
) -> Any:
    """Predictor TEST bootstrap composed from the frozen primitives.

    The frozen ``run_predictor_test_bootstrap`` composite derives X from the row
    objects stored in the single shared ``TestDraw`` per ``(population,
    replicate)`` and therefore cannot express the frozen per-unit
    (model x population x direction) panel. The runner composes the identical
    statistic from the frozen primitives instead: one shared draw identity per
    ``(population, replicate)``, re-indexed onto each unit's own rows, the frozen
    ``range_exceedance_warning`` for X, the frozen ``spearman_fixed_units`` for
    rho, and the frozen ``percentile_interval`` for the interval.
    """
    ordered = tuple(sorted(measurements, key=lambda item: item.unit.unit_id))
    samples: list[float] = []
    undefined: list[int] = []
    incomplete: list[int] = []
    for replicate_index in range(replicates):
        draws = {
            population: r4_inference.build_test_draw(
                canonical_rows[population], metadata[population], replicate_index
            )
            for population in canonical_rows
        }
        x_values: list[float] = []
        y_values: list[float] = []
        failed = False
        for measurement in ordered:
            population = measurement.unit.population_id
            draw = draws[population]
            target_scores = tuple(
                r4_inference.measurement_score(
                    row, r4_inference.target_measurement(measurement.unit.direction_id)
                )
                for row in _reindexed_rows(draw, measurement.target_test_rows)
            )
            x_values.append(
                float(
                    r4_predictor.range_exceedance_warning(
                        measurement.source_train_scores, target_scores
                    ).fraction_outside
                )
            )
            transport, _deploy = measurement.y_provider(draw)
            if transport is None:
                failed = True
                break
            y_values.append(float(transport))
        if failed:
            incomplete.append(replicate_index)
            continue
        try:
            samples.append(r4_predictor.spearman_fixed_units(x_values, y_values))
        except r4_predictor.SpearmanUndefined:
            undefined.append(replicate_index)
    status = (
        "COMPLETE"
        if not undefined and not incomplete
        else "INCOMPLETE"
    )
    return r4_predictor.PredictorBootstrapResult(
        planned_replicates=replicates,
        successful_replicates=len(samples),
        undefined_replicates=len(undefined),
        undefined_indices=tuple(undefined),
        incomplete_replicates=len(incomplete),
        incomplete_indices=tuple(incomplete),
        status=status,
        samples=tuple(samples),
        point_estimate=point_estimate,
        tail_rule=f"{r4_predictor.PREDICTOR_LOWER_TAIL}/{r4_predictor.PREDICTOR_UPPER_TAIL}",
    )


# --------------------------------------------------------------------------- #
# Exact LogLoss secondary path (ExtendedReal carriers, never clipped)
# --------------------------------------------------------------------------- #

LOG_LOSS_ESTIMANDS: tuple[str, ...] = (
    "Delta_deploy",
    "Delta_native",
    "Delta_transport",
)


@dataclass(frozen=True)
class LogLossPanelBootstrap:
    """Secondary exact-LogLoss bootstrap over the same frozen shared TEST draws."""

    replicates: int
    series: Mapping[tuple[str, str, str], tuple[Any, ...]]
    intervals: Mapping[tuple[str, str, str], Any]
    undefined_replicates: Mapping[tuple[str, str, str], tuple[int, ...]]
    status: str


def _logloss_paired_contrast(
    left: Sequence[float], right: Sequence[float], labels: Sequence[int]
) -> Any:
    """``mean(LL(left) - LL(right))`` in exact extended-real arithmetic.

    ``+inf - +inf`` is ``UNDEFINED_EXTENDED_REAL``; no clipping, no epsilon, no
    ``nextafter``, no smoothing and no row removal ever happens here.
    """
    if len(left) != len(right) or len(left) != len(labels):
        raise r4_inference.BootstrapContractViolation(
            "paired LogLoss contrast requires equal lengths"
        )
    differences = [
        r4_inference.extended_real_subtract(
            r4_inference.logloss_loss(prediction_a, label),
            r4_inference.logloss_loss(prediction_b, label),
        )
        for prediction_a, prediction_b, label in zip(left, right, labels, strict=True)
    ]
    return r4_inference.extended_real_mean(differences)


def _logloss_unit_values(
    rows: Sequence[R4InferenceRow],
    direction: str,
    cross: ProcedureFit,
    native: ProcedureFit,
    keys: Sequence[str],
) -> dict[str, Any]:
    target = r4_inference.target_measurement(direction)
    scores = [r4_inference.measurement_score(row, target) for row in rows]
    labels = [int(row.label) for row in rows]
    out: dict[str, Any] = {}
    if "Delta_deploy" in keys:
        out["Delta_deploy"] = _logloss_paired_contrast(
            [cross.calibrator(score) for score in scores], scores, labels
        )
    if "Delta_native" in keys:
        out["Delta_native"] = _logloss_paired_contrast(
            [native.calibrator(score) for score in scores], scores, labels
        )
    if "Delta_transport" in keys:
        out["Delta_transport"] = _logloss_paired_contrast(
            [cross.calibrator(score) for score in scores],
            [native.calibrator(score) for score in scores],
            labels,
        )
    return out


def _logloss_interval(
    series: Sequence[Any], *, lower_tail: Any, upper_tail: Any
) -> tuple[Any, str]:
    """Frozen rule: an UNDEFINED replicate makes the whole interval INCOMPLETE."""
    undefined = tuple(
        index
        for index, value in enumerate(series)
        if value.state == r4_inference.UNDEFINED_EXTENDED_REAL
    )
    if undefined:
        return None, "INCOMPLETE_UNDEFINED_EXTENDED_REAL"
    try:
        interval = r4_inference.percentile_interval(
            [value.value for value in series],
            lower_tail=lower_tail,
            upper_tail=upper_tail,
        )
    except Exception:  # pragma: no cover - fail closed, never a subset interval
        return None, "INCOMPLETE_NON_FINITE_SERIES"
    return interval, "COMPLETE"


def run_logloss_panel_bootstrap(
    inputs: PanelInputs,
    *,
    models: Sequence[str],
    populations: Sequence[str],
    procedures: Sequence[str],
    replicates: int,
    lower_tail: Any = None,
    upper_tail: Any = None,
) -> LogLossPanelBootstrap:
    """Exact-LogLoss secondary bootstrap on the SAME frozen shared TEST draws."""
    if lower_tail is None:
        lower_tail = r4_inference.PRIMARY_LOWER_TAIL
    if upper_tail is None:
        upper_tail = r4_inference.PRIMARY_UPPER_TAIL
    panel_values: dict[tuple[str, str], dict[str, list[Any]]] = {}
    directions = tuple(inputs.authority.direction_order)
    # One consistent key set per (direction, procedure) across every model and
    # population, so a member with a missing dependency is absent everywhere and
    # the fixed-size family reports INCOMPLETE instead of raising.
    global_keys = {
        (direction, procedure): unit_estimand_keys(
            inputs,
            models=models,
            populations=populations,
            direction=direction,
            procedure=procedure,
        )
        for direction in directions
        for procedure in procedures
    }
    for replicate_index in range(replicates):
        draws = {
            population: r4_inference.build_test_draw(
                inputs.test_rows[(models[0], population)],
                inputs.authority.population_metadata[population],
                replicate_index,
            )
            for population in populations
        }
        for direction in directions:
            for procedure in procedures:
                keys = global_keys[(direction, procedure)]
                if not keys:
                    continue
                per_population: dict[str, Any] = {}
                for population in populations:
                    draw = draws[population]
                    per_model: dict[str, Any] = {}
                    for model in models:
                        cross, native = _cross_native_fits(
                            inputs,
                            model=model,
                            population=population,
                            procedure=procedure,
                            direction=direction,
                        )
                        rows = _reindexed_rows(draw, inputs.test_rows[(model, population)])
                        values = _logloss_unit_values(
                            rows, direction, cross, native, keys
                        )
                        for estimand, value in values.items():
                            per_model.setdefault(estimand, []).append(value)
                    for estimand in keys:
                        per_population.setdefault(estimand, []).append(
                            r4_inference.extended_real_mean(per_model[estimand])
                        )
                for estimand in keys:
                    panel_values.setdefault((direction, procedure), {}).setdefault(
                        estimand, []
                    ).append(r4_inference.extended_real_mean(per_population[estimand]))

    series: dict[tuple[str, str, str], tuple[Any, ...]] = {}
    intervals: dict[tuple[str, str, str], Any] = {}
    undefined: dict[tuple[str, str, str], tuple[int, ...]] = {}
    statuses: set[str] = set()
    for (direction, procedure), bucket in panel_values.items():
        for estimand, values in bucket.items():
            key = (direction, procedure, estimand)
            series[key] = tuple(values)
            undefined_indices = tuple(
                index
                for index, value in enumerate(values)
                if value.state == r4_inference.UNDEFINED_EXTENDED_REAL
            )
            undefined[key] = undefined_indices
            interval, status = _logloss_interval(
                values, lower_tail=lower_tail, upper_tail=upper_tail
            )
            intervals[key] = interval
            statuses.add(status)
    return LogLossPanelBootstrap(
        replicates=replicates,
        series=series,
        intervals=intervals,
        undefined_replicates=undefined,
        status="COMPLETE" if statuses <= {"COMPLETE"} else "INCOMPLETE",
    )


# --------------------------------------------------------------------------- #
# Full-fit coverage registry
# --------------------------------------------------------------------------- #


def build_fit_coverage(
    inputs: PanelInputs, *, models: Sequence[str], populations: Sequence[str]
) -> tuple[Any, dict[str, Any]]:
    """Frozen ``CoverageMatrix`` plus the exact per-fit failure registry."""
    matrix = r4_inference.CoverageMatrix()
    registry: dict[str, Any] = {}
    for model in models:
        for population in populations:
            for direction in inputs.authority.direction_order:
                for procedure in inputs.authority.procedure_order:
                    for side, measurement in (
                        ("cross", r4_inference.source_measurement(direction)),
                        ("native", r4_inference.target_measurement(direction)),
                    ):
                        fit = inputs.fits[(model, population, f"{procedure}|{direction}|{side}")]
                        matrix.set(model, population, procedure, measurement, fit.status)
                        registry[
                            f"{model}|{population}|{procedure}|{direction}|{side}"
                        ] = {
                            "model": model,
                            "population": population,
                            "procedure": procedure,
                            "measurement": measurement,
                            "direction": direction,
                            "side": side,
                            "status": fit.status,
                            "failure_type": fit.failure_type,
                            "reason": fit.reason,
                        }
    return matrix, registry


# --------------------------------------------------------------------------- #
# N912 nested robustness (secondary; can never rescue the N456 primary)
# --------------------------------------------------------------------------- #


def run_n912_robustness(
    primary_inputs: PanelInputs,
    n912_inputs: PanelInputs,
    *,
    models: Sequence[str],
    populations: Sequence[str],
    procedures: Sequence[str],
    replicates: int,
) -> dict[str, Any]:
    """N456 vs nested N912 on the SAME shared TEST draws, paired by replicate."""
    n456 = run_test_bootstrap(
        primary_inputs,
        models=models,
        populations=populations,
        procedures=procedures,
        replicates=replicates,
    )
    n912 = run_test_bootstrap(
        n912_inputs,
        models=models,
        populations=populations,
        procedures=procedures,
        replicates=replicates,
    )
    comparisons: dict[str, Any] = {}
    for (direction, procedure), bucket in sorted(n912.panel_values.items()):
        for estimand, values_912 in sorted(bucket.items()):
            values_456 = n456.panel_values.get((direction, procedure), {}).get(estimand)
            if values_456 is None:
                comparisons[f"{direction}|{procedure}|{estimand}"] = {
                    "status": "INCOMPLETE",
                    "reason": "N456 counterpart unavailable",
                }
                continue
            difference = r4_inference.n912_minus_n456(values_912, values_456)
            comparisons[f"{direction}|{procedure}|{estimand}"] = {
                "status": "COMPLETE",
                "n456_replicates": len(values_456),
                "n912_replicates": len(values_912),
                "n912_minus_n456_mean": (
                    sum(difference) / len(difference) if difference else None
                ),
            }
    return {
        "role": r4_inference.N912_ROBUSTNESS_ROLE,
        "cannot_rescue_primary": r4_inference.N912_CANNOT_RESCUE_PRIMARY,
        "shared_test_draw_paired_by_replicate": True,
        "comparisons": comparisons,
    }


def validate_n912_panels(
    primary_inputs: PanelInputs,
    n912_inputs: PanelInputs,
    *,
    models: Sequence[str],
    populations: Sequence[str],
) -> dict[str, Any]:
    """Frozen TRAIN_456 subset TRAIN_912 + identical TEST identity validator."""
    report: dict[str, Any] = {}
    for model in models:
        for population in populations:
            train_456 = tuple(
                r4_inference.FrozenItemReference(row.item_id, row.label, row.anchor_index)
                for row in primary_inputs.train_rows[(model, population)]
            )
            train_912 = tuple(
                r4_inference.FrozenItemReference(row.item_id, row.label, row.anchor_index)
                for row in n912_inputs.train_rows[(model, population)]
            )
            test_456 = tuple(
                r4_inference.FrozenItemReference(row.item_id, row.label, row.anchor_index)
                for row in primary_inputs.test_rows[(model, population)]
            )
            test_912 = tuple(
                r4_inference.FrozenItemReference(row.item_id, row.label, row.anchor_index)
                for row in n912_inputs.test_rows[(model, population)]
            )
            report[f"{model}|{population}"] = r4_inference.validate_n912_pairing(
                train_456=train_456,
                train_912=train_912,
                test_456=test_456,
                test_912=test_912,
            )
    return report


# --------------------------------------------------------------------------- #
# Shared formal-DAG engine (used by BOTH formal and synthetic qualification)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class DagRun:
    """The complete frozen-DAG input bundle for one invocation."""

    authority: FrozenAuthority
    primary: PanelInputs
    legacy: PanelInputs
    n912: PanelInputs | None
    primary_populations: tuple[str, ...]
    legacy_populations: tuple[str, ...]
    fixture_marker: str | None


def _noop_block(**kwargs: Any) -> None:
    """Default block recorder: the synthetic path records no operational state."""
    return None


def run_dag_engine(
    dag: DagRun,
    *,
    test_replicates: int,
    refit_replicates: int,
    predictor_replicates: int,
    on_block: Callable[..., None] = _noop_block,
) -> dict[str, Any]:
    """The single frozen formal-DAG engine.

    Formal execution and synthetic formal-DAG qualification call this exact
    function; they differ only in input source, replicate counts, output root and
    the fixture marker. Every frozen DAG node is covered here.
    """
    authority = dag.authority
    primary = dag.primary
    legacy = dag.legacy
    primary_populations = dag.primary_populations
    legacy_populations = dag.legacy_populations
    primary_models = _panel_models(primary, primary_populations)
    legacy_models = _panel_models(legacy, legacy_populations)

    # --- directional_train_source / directional_train_target / directional_test
    on_block(
        block="input_load",
        status="COMPLETE",
        identity=authority.ledger_fingerprint,
        output_fingerprint=fingerprint(
            {
                "primary_models": list(primary_models),
                "legacy_models": list(legacy_models),
                "primary_populations": list(primary_populations),
                "legacy_populations": list(legacy_populations),
            }
        ),
    )

    # --- core4_fit / ib_extension_fit coverage
    coverage, coverage_registry = build_fit_coverage(
        primary, models=primary_models, populations=primary_populations
    )
    legacy_coverage, legacy_coverage_registry = build_fit_coverage(
        legacy, models=legacy_models, populations=legacy_populations
    )

    # --- raw_risk / native_risk / cross_risk / delta_native / delta_deploy /
    #     delta_transport (point estimates)
    estimates = point_estimates(
        primary, models=primary_models, populations=primary_populations
    )
    legacy_estimates = point_estimates(
        legacy, models=legacy_models, populations=legacy_populations
    )
    on_block(
        block="point_estimates",
        status="COMPLETE",
        identity=authority.final_protocol_fingerprint,
        output_fingerprint=fingerprint({"units": sorted(estimates)}),
    )

    # --- n912_robustness
    n912_report: dict[str, Any]
    # N912 is defined only on the frozen new-population 912 manifests
    # (HellaSwag, MedMCQA); MMLU has no nested 912 budget.
    n912_populations: tuple[str, ...] = ()
    if dag.n912 is not None:
        n912_populations = tuple(
            population
            for population in primary_populations
            if (primary_models[0], population) in dag.n912.test_rows
        )
    if dag.n912 is None:
        n912_report = {
            "role": r4_inference.N912_ROBUSTNESS_ROLE,
            "cannot_rescue_primary": r4_inference.N912_CANNOT_RESCUE_PRIMARY,
            "status": "INCOMPLETE",
            "reason": "no frozen N912 nested budget in this panel",
        }
    else:
        n912_report = run_n912_robustness(
            primary,
            dag.n912,
            models=primary_models,
            populations=n912_populations,
            procedures=authority.procedure_order,
            replicates=test_replicates,
        )
        n912_report["pairing"] = validate_n912_panels(
            primary,
            dag.n912,
            models=primary_models,
            populations=n912_populations,
        )
    on_block(
        block="n912_robustness",
        status="COMPLETE",
        identity=r4_inference.N912_ROBUSTNESS_ROLE,
        output_fingerprint=fingerprint({"comparisons": sorted(n912_report["comparisons"])})
        if "comparisons" in n912_report
        else None,
    )

    # --- primary12 / extension8 / direction6 / native12 (shared TEST draws)
    bootstrap = run_test_bootstrap(
        primary,
        models=primary_models,
        populations=primary_populations,
        procedures=authority.procedure_order,
        replicates=test_replicates,
    )
    legacy_bootstrap = run_test_bootstrap(
        legacy,
        models=legacy_models,
        populations=legacy_populations,
        procedures=authority.procedure_order,
        replicates=test_replicates,
    )
    logloss = run_logloss_panel_bootstrap(
        primary,
        models=primary_models,
        populations=primary_populations,
        procedures=authority.procedure_order,
        replicates=test_replicates,
    )
    on_block(
        block="test_bootstrap",
        status="COMPLETE",
        identity=r4_inference.TEST_BOOTSTRAP_PROTOCOL_ID,
        output_fingerprint=fingerprint(
            {"contrasts": len(bootstrap.primary_contrasts)}
        ),
    )

    # --- full TRAIN-refit scope: every frozen required procedure
    refit = run_refit_blocks(
        primary,
        models=primary_models,
        populations=primary_populations,
        procedures=authority.procedure_order,
        replicates=refit_replicates,
    )
    legacy_refit = run_refit_blocks(
        legacy,
        models=legacy_models,
        populations=legacy_populations,
        procedures=authority.procedure_order,
        replicates=refit_replicates,
    )
    # Secondary-robustness TRAIN-refit blocks on the frozen nested N912 budget
    # (frozen new-population 912 manifests only). Never a new multiplicity family.
    n912_refit: dict[str, Any] = {}
    if dag.n912 is not None:
        n912_refit = run_refit_blocks(
            dag.n912,
            models=primary_models,
            populations=n912_populations,
            procedures=authority.procedure_order,
            replicates=refit_replicates,
        )
    on_block(
        block="train_refit",
        status="COMPLETE",
        identity=r4_inference.TRAIN_REFIT_PROTOCOL_ID,
        output_fingerprint=fingerprint(
            {
                "blocks": sorted(refit),
                "legacy_blocks": sorted(legacy_refit),
                "n912_blocks": sorted(n912_refit),
            }
        ),
    )

    # --- predictor_development8 / predictor_validation16 / predictor_legacy8
    merged = merge_panels(primary, legacy)
    measurements = build_predictor_measurements(merged)
    point_rows = predictor_point_rows(measurements)
    predictor = run_predictor_bootstrap(
        measurements=measurements,
        canonical_rows=_canonical_predictor_rows(merged),
        metadata={
            population: authority.population_metadata[population]
            for population in (*primary_populations, *legacy_populations)
        },
        replicates=predictor_replicates,
        point_estimate=r4_predictor.primary_statistic(point_rows) if point_rows else None,
    )
    on_block(
        block="predictor",
        status=predictor.status,
        identity=r4_predictor.VALIDATION_PROTOCOL_ID,
        output_fingerprint=fingerprint({"rows": len(point_rows)}),
    )

    incompleteness = tuple(
        sorted(
            [
                f"fit|{key}|{entry['status']}"
                for key, entry in coverage_registry.items()
                if entry["status"] != AVAILABLE
            ]
            + [
                f"legacy-fit|{key}|{entry['status']}"
                for key, entry in legacy_coverage_registry.items()
                if entry["status"] != AVAILABLE
            ]
        )
    )

    # --- final assembly
    skeleton = r4_inference.build_analysis_artifact_skeleton(
        population_fingerprints={
            population: authority.population_metadata[population].population_fingerprint
            for population in (*primary_populations, *legacy_populations)
        },
        calibration_fingerprints=dict(r4_inference.PROCEDURE_FINGERPRINTS),
        model_identities={
            model_key: model_key for model_key in (*primary_models, *legacy_models)
        },
        measurement_provenance={
            "raw_measurement_freeze_commit": authority.raw_measurement_freeze_commit,
            "measurement_code_commit": authority.measurement_code_commit,
            "ledger_fingerprint": authority.ledger_fingerprint,
        },
        full_fit_coverage={
            "primary": coverage.matrix(),
            "legacy": legacy_coverage.matrix(),
            "incomplete_cells": coverage.incomplete_cells(),
            "legacy_incomplete_cells": legacy_coverage.incomplete_cells(),
        },
        unit_estimates={key: value["status"] for key, value in estimates.items()},
        panel_estimates=bootstrap.family_status(),
        test_bootstrap_provenance={
            "protocol_id": r4_inference.TEST_BOOTSTRAP_PROTOCOL_ID,
            "protocol_version": r4_inference.TEST_BOOTSTRAP_PROTOCOL_VERSION,
            "replicates": test_replicates,
        },
        train_refit_provenance={
            "protocol_id": r4_inference.TRAIN_REFIT_PROTOCOL_ID,
            "protocol_version": r4_inference.TRAIN_REFIT_PROTOCOL_VERSION,
            "replicates": refit_replicates,
            "blocks": {key: block.status for key, block in refit.items()},
            "legacy_blocks": {key: block.status for key, block in legacy_refit.items()},
            "n912_blocks": {key: block.status for key, block in n912_refit.items()},
        },
        multiplicity_families={
            "primary": len(bootstrap.primary_contrasts),
            "extension": len(bootstrap.extension_panel),
            "direction_difference": len(bootstrap.direction_differences),
            "native_reference": len(bootstrap.native_reference),
        },
        n912_robustness=n912_report,
        secondary_diagnostics={
            "logloss_status": logloss.status,
            "logloss_intervals": {
                "|".join(key): (
                    None if interval is None else interval.payload()
                )
                for key, interval in logloss.intervals.items()
            },
            "logloss_undefined_replicates": {
                "|".join(key): list(value)
                for key, value in logloss.undefined_replicates.items()
            },
            "predictor": {
                "validation_protocol_id": r4_predictor.VALIDATION_PROTOCOL_ID,
                "status": predictor.status,
                "planned_replicates": predictor.planned_replicates,
                "successful_replicates": predictor.successful_replicates,
                "undefined_replicates": predictor.undefined_replicates,
                "undefined_indices": list(predictor.undefined_indices),
                "incomplete_replicates": predictor.incomplete_replicates,
                "incomplete_indices": list(predictor.incomplete_indices),
                "point_estimate": predictor.point_estimate,
                "tail_rule": predictor.tail_rule,
                "interval": predictor.interval().payload(),
                "units_total": len(measurements),
                "development_units": sum(
                    1
                    for measurement in measurements
                    if measurement.unit.analysis_role == r4_predictor.ROLE_DEVELOPMENT
                ),
                "validation_units": sum(
                    1
                    for measurement in measurements
                    if measurement.unit.analysis_role
                    == r4_predictor.ROLE_PRIMARY_VALIDATION
                ),
                "legacy_units": sum(
                    1
                    for measurement in measurements
                    if measurement.unit.analysis_role == r4_predictor.ROLE_LEGACY_EXTENSION
                ),
                "validation_rows": len(point_rows),
            },
            "legacy_secondary": {
                "models": list(legacy_models),
                "populations": list(legacy_populations),
                "unit_estimates": len(legacy_estimates),
                "bootstrap_family_status": legacy_bootstrap.family_status(),
                "refit_blocks": len(legacy_refit),
            },
        },
        incompleteness=incompleteness,
    )
    skeleton["runner"] = {
        "runner_id": RUNNER_ID,
        "runner_version": RUNNER_VERSION,
        "runner_source_sha256": sha256_file(RUNNER_SOURCE_PATH),
        "runner_contract_id": RUNNER_CONTRACT_ID,
        "result_fingerprint_version": ANALYSIS_RESULT_FINGERPRINT_VERSION,
        "fixture_marker": dag.fixture_marker,
    }
    on_block(
        block="final_assembly",
        status="COMPLETE",
        identity=authority.execution_manifest_fingerprint,
        output_fingerprint=fingerprint(skeleton),
    )
    return {
        "artifact": skeleton,
        "primary_models": primary_models,
        "legacy_models": legacy_models,
        "estimates": estimates,
        "legacy_estimates": legacy_estimates,
        "bootstrap": bootstrap,
        "legacy_bootstrap": legacy_bootstrap,
        "logloss": logloss,
        "refit": refit,
        "legacy_refit": legacy_refit,
        "n912_refit": n912_refit,
        "n912_robustness": n912_report,
        "predictor": predictor,
        "predictor_point_rows": point_rows,
        "coverage": coverage,
        "coverage_registry": coverage_registry,
        "legacy_coverage_registry": legacy_coverage_registry,
    }


def _canonical_predictor_rows(inputs: PanelInputs) -> dict[str, tuple[R4InferenceRow, ...]]:
    """One canonical row set per population (draw identity is model-independent)."""
    out: dict[str, tuple[R4InferenceRow, ...]] = {}
    for model_key, population in inputs.test_rows:
        out.setdefault(population, inputs.test_rows[(model_key, population)])
    return out


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_r4_analysis",
        description="R4 integrated formal analysis runner (orchestration only).",
    )
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--synthetic-qualification", action="store_true")
    parser.add_argument("--execute-formal-analysis", action="store_true")
    parser.add_argument("--formal-root", default=str(FORMAL_ANALYSIS_ROOT))
    parser.add_argument("--qualification-root", default=str(QUALIFICATION_ROOT))
    parser.add_argument("--evidence-root", default=str(RAW_EVIDENCE_ROOT))
    parser.add_argument("--synthetic-replicates", type=int, default=64)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    modes = [args.validate_only, args.synthetic_qualification, args.execute_formal_analysis]
    if sum(1 for mode in modes if mode) > 1:
        parser.error("choose exactly one mode")
    if not any(modes):
        parser.error(
            "no analysis mode selected; pass --validate-only, --synthetic-qualification "
            "or --execute-formal-analysis"
        )
    if args.synthetic_replicates <= 0:
        parser.error("--synthetic-replicates must be positive")
    if args.execute_formal_analysis:
        return execute_formal_analysis(args)
    if args.synthetic_qualification:
        return synthetic_qualification(args)
    return validate_only(args)


def validate_only(args: argparse.Namespace) -> int:
    """Structural validation of the frozen inputs; computes no statistic."""
    authority = load_frozen_authority()
    cells = load_cells()
    units = enumerate_units(cells, authority)
    problems: list[str] = []
    total_rows = 0
    for cell in cells:
        payload = load_cell_payload(cell)
        splits = rows_by_split(payload, cell)
        total_rows += len(splits["TRAIN"]) + len(splits["TEST"])
        for split, rows in splits.items():
            expected = cell.split_counts.get(split)
            if expected is not None and len(rows) != expected:
                problems.append(f"{cell.cell_id}/{split}: {len(rows)} != {expected}")
    summary = {
        "runner_id": RUNNER_ID,
        "runner_version": RUNNER_VERSION,
        "mode": "validate-only",
        "frozen_authority_verified": True,
        "cells": len(cells),
        "rows": total_rows,
        "current_directional_units": len(primary_units(units)),
        "legacy_directional_units": len(legacy_units(units)),
        "calibrator_fits": 0,
        "metrics_computed": 0,
        "bootstrap_draws": 0,
        "predictor_values": 0,
        "scientific_outputs_computed": False,
        "problems": problems,
        "status": "PASS" if not problems else "FAIL",
    }
    print(canonical_json(summary), end="")
    return 0 if not problems else 1


SYNTHETIC_FIXTURE_MARKER = "SYNTHETIC_ONLY_NOT_SCIENTIFIC_EVIDENCE"
SYNTHETIC_STRATA_PER_POPULATION = 6
SYNTHETIC_TRAIN_PER_STRATUM = 12
SYNTHETIC_TEST_PER_STRATUM = 12
SYNTHETIC_CLUSTERS_PER_STRATUM = 3


def _synthetic_digest(*parts: str) -> str:
    return fingerprint({"fixture": SYNTHETIC_FIXTURE_MARKER, "parts": list(parts)})


def _synthetic_score(*parts: str) -> float:
    """A deterministic invented probability in (0, 1); never a study value."""
    value = int(_synthetic_digest(*parts)[:12], 16) % 1000003
    return 0.001 + 0.998 * (value / 1000003.0)


def _synthetic_label(*parts: str) -> int:
    return int(_synthetic_digest(*parts)[12:14], 16) % 2


def _synthetic_rows(
    *,
    model_key: str,
    population_id: str,
    split: str,
    grouped: bool,
    per_stratum: int,
) -> tuple[R4InferenceRow, ...]:
    rows: list[R4InferenceRow] = []
    for index in range(SYNTHETIC_STRATA_PER_POPULATION):
        stratum = f"synthetic-stratum-{index}"
        for position in range(per_stratum):
            item_id = f"synthetic-{split.lower()}-{population_id}-{index}-{position}"
            cluster = (
                f"synthetic-cluster-{index}-{position % SYNTHETIC_CLUSTERS_PER_STRATUM}"
                if grouped
                else None
            )
            cat_score = _synthetic_score(model_key, population_id, item_id, "CAT")
            ovr_score = _synthetic_score(model_key, population_id, item_id, "OVR")
            # Non-separable invented labels: a smooth monotone signal plus a
            # deterministic flip, so every frozen fitting contract is exercised.
            signal = cat_score + ovr_score
            label = 1 if signal > 1.0 else 0
            if _synthetic_label(model_key, population_id, item_id) == 1:
                label = 1 - label
            rows.append(
                R4InferenceRow(
                    item_id=item_id,
                    population_id=population_id,
                    stratum=stratum,
                    label=label,
                    cat_score=cat_score,
                    ovr_score=ovr_score,
                    cluster_id=cluster,
                    anchor_index=int(_synthetic_digest(item_id, "anchor")[:2], 16) % 4,
                )
            )
    return tuple(rows)


def _synthetic_metadata(
    authority: FrozenAuthority, *, train_per_stratum: int = SYNTHETIC_TRAIN_PER_STRATUM
) -> dict[str, PopulationMetadata]:
    out: dict[str, PopulationMetadata] = {}
    for population_id, meta in authority.population_metadata.items():
        out[population_id] = PopulationMetadata(
            population_id=meta.population_id,
            population_fingerprint=meta.population_fingerprint,
            stratum_field=meta.stratum_field,
            group_field=meta.group_field,
            test_bootstrap_protocol_id=meta.test_bootstrap_protocol_id,
            test_bootstrap_protocol_version=meta.test_bootstrap_protocol_version,
            test_bootstrap_mode=meta.test_bootstrap_mode,
            estimand_weighting=meta.estimand_weighting,
            test_count=SYNTHETIC_STRATA_PER_POPULATION * SYNTHETIC_TEST_PER_STRATUM,
            train_count=SYNTHETIC_STRATA_PER_POPULATION * train_per_stratum,
        )
    return out


def build_synthetic_panel(
    authority: FrozenAuthority,
    cells: Sequence[AnalysisCell],
    *,
    train_per_stratum: int = SYNTHETIC_TRAIN_PER_STRATUM,
) -> PanelInputs:
    """Build an invented panel with the frozen structure; no study value enters.

    ``train_per_stratum`` is only ever doubled for the synthetic N912 nested
    robustness fixture (positions 0..k are a strict prefix, so the N456 TRAIN set
    is a subset of the N912 TRAIN set and the TEST rows are byte-identical).
    """
    metadata = _synthetic_metadata(authority, train_per_stratum=train_per_stratum)
    model_keys = {cell.model_id: cell.model_key for cell in cells}
    train: dict[tuple[str, str], tuple[R4InferenceRow, ...]] = {}
    test: dict[tuple[str, str], tuple[R4InferenceRow, ...]] = {}
    fits: dict[tuple[str, str, str], ProcedureFit] = {}
    for cell in cells:
        grouped = cell.group_id_field is not None
        train[(cell.model_key, cell.population_id)] = _synthetic_rows(
            model_key=cell.model_key,
            population_id=cell.population_id,
            split="TRAIN",
            grouped=grouped,
            per_stratum=train_per_stratum,
        )
        test[(cell.model_key, cell.population_id)] = _synthetic_rows(
            model_key=cell.model_key,
            population_id=cell.population_id,
            split="TEST",
            grouped=grouped,
            per_stratum=SYNTHETIC_TEST_PER_STRATUM,
        )
    synthetic_authority = FrozenAuthority(
        measurement_contract_fingerprint=authority.measurement_contract_fingerprint,
        final_protocol_fingerprint=authority.final_protocol_fingerprint,
        execution_manifest_fingerprint=authority.execution_manifest_fingerprint,
        ledger_fingerprint=authority.ledger_fingerprint,
        environment_map_fingerprint=authority.environment_map_fingerprint,
        registry_fingerprint=authority.registry_fingerprint,
        dependency_graph_fingerprint=authority.dependency_graph_fingerprint,
        preflight_fingerprint=authority.preflight_fingerprint,
        raw_measurement_freeze_commit=authority.raw_measurement_freeze_commit,
        measurement_code_commit=authority.measurement_code_commit,
        population_metadata=metadata,
        model_order=authority.model_order,
        population_order=authority.population_order,
        direction_order=authority.direction_order,
        procedure_order=authority.procedure_order,
    )
    for key, rows in train.items():
        model_key, population_id = key
        for direction in synthetic_authority.direction_order:
            for procedure in synthetic_authority.procedure_order:
                for side, measurement in (
                    ("cross", r4_inference.source_measurement(direction)),
                    ("native", r4_inference.target_measurement(direction)),
                ):
                    fit_key = (model_key, population_id, f"{procedure}|{direction}|{side}")
                    fits[fit_key] = fit_procedure(
                        procedure=procedure, train_rows=rows, measurement=measurement
                    )
    return PanelInputs(
        authority=synthetic_authority,
        model_keys=model_keys,
        train_rows=train,
        test_rows=test,
        fits=fits,
    )


def _panel_models(inputs: PanelInputs, populations: Sequence[str]) -> tuple[str, ...]:
    ordered: list[str] = []
    for model_key, population_id in inputs.train_rows:
        if population_id in populations and model_key not in ordered:
            ordered.append(model_key)
    return tuple(sorted(ordered))


def merge_panels(*panels: PanelInputs) -> PanelInputs:
    """Union several panels into one (the frozen predictor spans all roles)."""
    if not panels:
        raise R4AnalysisContractViolation("merge_panels requires at least one panel")
    authority = panels[0].authority
    model_keys: dict[str, str] = {}
    train: dict[tuple[str, str], tuple[R4InferenceRow, ...]] = {}
    test: dict[tuple[str, str], tuple[R4InferenceRow, ...]] = {}
    fits: dict[tuple[str, str, str], ProcedureFit] = {}
    for panel in panels:
        other = panel.authority
        if other is not authority and other.registry_fingerprint != authority.registry_fingerprint:
            raise R4AnalysisContractViolation("merge_panels requires identical frozen authority")
        model_keys.update(panel.model_keys)
        train.update(panel.train_rows)
        test.update(panel.test_rows)
        fits.update(panel.fits)
    return PanelInputs(
        authority=authority, model_keys=model_keys, train_rows=train, test_rows=test, fits=fits
    )


# --------------------------------------------------------------------------- #
# Direct frozen-call oracle (qualification only)
# --------------------------------------------------------------------------- #


def oracle_risk_matrix(
    inputs: PanelInputs,
    *,
    model_key: str,
    population_id: str,
    direction: str,
    procedure: str,
    rows: Sequence[R4InferenceRow] | None = None,
) -> Any:
    """Recompose the frozen risk matrix without any runner helper."""
    train_rows = inputs.train_rows[(model_key, population_id)]
    target_rows = inputs.test_rows[(model_key, population_id)] if rows is None else rows
    source = r4_inference.source_measurement(direction)
    target = r4_inference.target_measurement(direction)
    if procedure in r4_inference.LOGISTIC_CORE_PROCEDURES:
        spec = {item.label: item for item in r3_protocol.procedure_panel()}[procedure]
        cross_fit: Any = r3_analysis.fit_calibrator(
            spec,
            source,
            [
                (row.item_id, r4_inference.measurement_score(row, source), float(row.label))
                for row in train_rows
            ],
        )
        native_fit: Any = r3_analysis.fit_calibrator(
            spec,
            target,
            [
                (row.item_id, r4_inference.measurement_score(row, target), float(row.label))
                for row in train_rows
            ],
        )
        cross_map: Any = cross_fit.apply
        native_map: Any = native_fit.apply
    else:
        source_scores = [r4_inference.measurement_score(row, source) for row in train_rows]
        target_scores = [r4_inference.measurement_score(row, target) for row in train_rows]
        labels = [int(row.label) for row in train_rows]
        if procedure == "I-isotonic":
            cross_iso = r4_calibration_families.fit_isotonic_fixed_decision_probability(
                source_scores, labels
            )
            native_iso = r4_calibration_families.fit_isotonic_fixed_decision_probability(
                target_scores, labels
            )
            cross_map = _applicator(
                r4_calibration_families.apply_isotonic_fixed_decision_probability, cross_iso
            )
            native_map = _applicator(
                r4_calibration_families.apply_isotonic_fixed_decision_probability, native_iso
            )
        elif procedure == "B-beta":
            cross_beta = r4_calibration_families.fit_beta_fixed_decision_probability(
                source_scores, labels
            )
            native_beta = r4_calibration_families.fit_beta_fixed_decision_probability(
                target_scores, labels
            )
            cross_map = _applicator(
                r4_calibration_families.apply_beta_fixed_decision_probability, cross_beta
            )
            native_map = _applicator(
                r4_calibration_families.apply_beta_fixed_decision_probability, native_beta
            )
        else:
            raise R4AnalysisUnfrozenChoice(procedure)
    return r4_inference.risk_matrix(target_rows, direction, cross_map, native_map)


def oracle_metric_checks() -> dict[str, Any]:
    """Direct frozen-call checks of the metric / extended-real contract."""
    pairs = [(0.0, 0), (1.0, 1), (0.25, 1), (0.75, 0)]
    inf = r4_inference.ExtendedReal.positive_infinity()
    finite = r4_inference.ExtendedReal.finite(0.5)
    undefined = r4_inference.extended_real_subtract(inf, inf)
    return {
        "mean_brier": r4_inference.mean_brier(pairs),
        "mean_logloss_state": r4_inference.mean_logloss(pairs).state,
        "logloss_zero_mass_correct_state": r4_inference.logloss_loss(0.0, 0).state,
        "logloss_zero_mass_incorrect_state": r4_inference.logloss_loss(0.0, 1).state,
        "inf_minus_inf_state": undefined.state,
        "inf_plus_finite_state": r4_inference.extended_real_add(inf, finite).state,
        "undefined_constant": r4_inference.ExtendedReal.undefined().state,
    }


def cluster_integrity(draw: TestDraw, rows: Sequence[R4InferenceRow]) -> bool:
    """Every Hella source_id cluster must appear 0 or k whole times in a draw."""
    lookup = {row.item_id: row for row in rows}
    sizes: dict[str, int] = {}
    for row in rows:
        sizes[row.cluster_id] = sizes.get(row.cluster_id, 0) + 1
    seen: dict[str, int] = {}
    for occurrence in draw.occurrences:
        cluster = lookup[occurrence.item_id].cluster_id
        seen[cluster] = seen.get(cluster, 0) + 1
    return all(count % sizes[cluster] == 0 for cluster, count in seen.items())


# --------------------------------------------------------------------------- #
# Operational checkpointing (never scientific state)
# --------------------------------------------------------------------------- #


CHECKPOINT_FILENAME = "runner-checkpoints.json"

ANALYSIS_BLOCKS = (
    "authority_validation",
    "input_load",
    "point_estimates",
    "n912_robustness",
    "test_bootstrap",
    "train_refit",
    "predictor",
    "final_assembly",
)


@dataclass(frozen=True)
class CheckpointStore:
    """Operational block-level checkpointing with atomic writes.

    Never stores floating-point draws: a block is either absent or complete, and
    a crash inside a block discards the whole block so it is recomputed from the
    identical frozen inputs and the identical frozen randomness authority.
    """

    root: Path

    @property
    def path(self) -> Path:
        return self.root / CHECKPOINT_FILENAME

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"blocks": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def completed(self) -> dict[str, Any]:
        blocks = self.load()["blocks"]
        return {name: block for name, block in blocks.items() if block["status"] == "COMPLETE"}

    def record(
        self,
        block: str,
        *,
        status: str,
        identity: str,
        output_fingerprint: str | None,
    ) -> dict[str, Any]:
        if block not in ANALYSIS_BLOCKS:
            raise R4AnalysisContractViolation(f"unknown analysis block {block!r}")
        if status not in ("COMPLETE", "INCOMPLETE"):
            raise R4AnalysisContractViolation(f"unknown block status {status!r}")
        state = self.load()
        state["blocks"][block] = {
            "block": block,
            "status": status,
            "identity": identity,
            "output_fingerprint": output_fingerprint,
        }
        self.root.mkdir(parents=True, exist_ok=True)
        write_atomic(self.path, canonical_json(state))
        return state["blocks"][block]


# --------------------------------------------------------------------------- #
# Qualification harness
# --------------------------------------------------------------------------- #


def predictor_report(inputs: PanelInputs, *, replicates: int) -> dict[str, Any]:
    """Qualify the predictor wiring on the synthetic panel (merged-panel safe)."""
    measurements = build_predictor_measurements(inputs)
    point_rows = predictor_point_rows(measurements)
    point_estimate = r4_predictor.primary_statistic(point_rows) if point_rows else None
    units = (m.unit for m in measurements)
    populations = tuple(dict.fromkeys(unit.population_id for unit in units))
    predictor = run_predictor_bootstrap(
        measurements=measurements,
        canonical_rows=_canonical_predictor_rows(inputs),
        metadata={p: inputs.authority.population_metadata[p] for p in populations},
        replicates=replicates,
        point_estimate=point_estimate,
    )
    return {
        "units_total": len(measurements),
        "development_units": sum(
            1 for m in measurements if m.unit.analysis_role == r4_predictor.ROLE_DEVELOPMENT
        ),
        "validation_units": sum(
            1 for m in measurements if m.unit.analysis_role == r4_predictor.ROLE_PRIMARY_VALIDATION
        ),
        "legacy_units": sum(
            1 for m in measurements if m.unit.analysis_role == r4_predictor.ROLE_LEGACY_EXTENSION
        ),
        "validation_rows": len(point_rows),
        "point_estimate": point_estimate,
        "status": predictor.status,
        "successful_replicates": predictor.successful_replicates,
        "planned_replicates": predictor.planned_replicates,
        "tail_rule": predictor.tail_rule,
    }


def qualification_report(
    engine: Mapping[str, Any], dag: DagRun, *, replicates: int, role: str = "primary"
) -> dict[str, Any]:
    """Qualify the frozen-DAG engine output on the synthetic panel.

    This reads the SAME engine output that formal execution produces; it never
    re-implements the DAG. ``role`` selects the primary (current-generation) or
    the legacy secondary panel.
    """
    if role == "primary":
        inputs = dag.primary
        populations = dag.primary_populations
        models = engine["primary_models"]
        estimates = engine["estimates"]
        bootstrap = engine["bootstrap"]
        refit = engine["refit"]
    elif role == "legacy":
        inputs = dag.legacy
        populations = dag.legacy_populations
        models = engine["legacy_models"]
        estimates = engine["legacy_estimates"]
        bootstrap = engine["legacy_bootstrap"]
        refit = engine["legacy_refit"]
    else:  # pragma: no cover - defensive
        raise R4AnalysisContractViolation(f"unknown qualification role {role!r}")
    procedures = inputs.authority.procedure_order
    report: dict[str, Any] = {
        "fixture_marker": SYNTHETIC_FIXTURE_MARKER,
        "role": role,
        "models": list(models),
        "populations": list(populations),
    }

    # 1. point estimates + direct-call oracle equivalence
    mismatches: list[str] = []
    for model in models:
        for population in populations:
            for direction in inputs.authority.direction_order:
                for procedure in procedures:
                    key = f"{model}|{population}|{direction}|{procedure}"
                    entry = estimates[key]
                    if "risk_matrix" not in entry:
                        continue
                    oracle = oracle_risk_matrix(
                        inputs,
                        model_key=model,
                        population_id=population,
                        direction=direction,
                        procedure=procedure,
                    )
                    runner_matrix = entry["risk_matrix"]
                    for field in (
                        "r_raw",
                        "r_native",
                        "r_cross",
                        "delta_native",
                        "delta_deploy",
                        "delta_transport",
                    ):
                        if getattr(runner_matrix, field) != getattr(oracle, field):
                            mismatches.append(f"{key}:{field}")
    report["point_estimate_mismatches"] = mismatches
    report["point_estimate_oracle_equal"] = not mismatches

    # 2. metric / extended-real contract
    report["metric_oracle"] = oracle_metric_checks()

    # 3. shared-draw TEST bootstrap (primary12 / extension8 / direction6 / native12)
    report["bootstrap_family_status"] = bootstrap.family_status()
    report["bootstrap_primary_contrasts"] = len(bootstrap.primary_contrasts)
    report["bootstrap_direction_differences"] = len(bootstrap.direction_differences)
    report["bootstrap_extension_panel"] = len(bootstrap.extension_panel)
    report["bootstrap_native_reference"] = len(bootstrap.native_reference)

    # 4. dependency-unavailable propagation: CORE4 alone keeps primary + direction
    core_only = run_test_bootstrap(
        inputs,
        models=models,
        populations=populations,
        procedures=r4_inference.LOGISTIC_CORE_PROCEDURES,
        replicates=replicates,
    )
    report["core4_only_primary_contrasts"] = len(core_only.primary_contrasts)
    report["core4_only_extension_panel"] = len(core_only.extension_panel)
    report["core4_only_family_status"] = core_only.family_status()

    # 5. draw sharing and cluster integrity
    metadata = inputs.authority.population_metadata
    sharing_ok = True
    cluster_ok = True
    for population in populations:
        reference = None
        for model in models:
            draw = r4_inference.build_test_draw(
                inputs.test_rows[(model, population)], metadata[population], 0
            )
            payload = draw.draw_identity_payload()
            if reference is None:
                reference = payload
            elif payload != reference:
                sharing_ok = False
            if metadata[population].group_field is not None and not cluster_integrity(
                draw, inputs.test_rows[(model, population)]
            ):
                cluster_ok = False
    report["shared_draw_identity_equal_across_models"] = sharing_ok
    report["cluster_never_split"] = cluster_ok

    # 6. full-scope TRAIN refit (every frozen required procedure)
    report["refit_blocks"] = len(refit)
    report["refit_statuses"] = sorted({block.status for block in refit.values()})
    report["refit_procedures"] = sorted({key.split("|")[3] for key in refit})
    report["refit_estimands"] = sorted({key.split("|")[4] for key in refit})
    report["refit_incomplete_blocks"] = sorted(
        key for key, block in refit.items() if block.status != "COMPLETE"
    )
    report["refit_failure_records"] = sorted(
        {
            f"{block.procedure}|{record.exception_type}|{record.message}"
            for block in refit.values()
            for record in block.failures
        }
    )
    report["refit_intervals_withheld"] = sum(
        1 for block in refit.values() if block.interval is None
    )

    # 7. full-fit coverage registry
    registry = (
        engine["coverage_registry"] if role == "primary" else engine["legacy_coverage_registry"]
    )
    report["fit_coverage"] = {
        "entries": len(registry),
        "failed": sorted(key for key, entry in registry.items() if entry["status"] == FAILED),
        "ineligible": sorted(
            key for key, entry in registry.items() if entry["status"] == INELIGIBLE
        ),
    }
    report["available_procedures"] = available_procedures(
        inputs, models=models, populations=populations
    )

    if role != "primary":
        return report

    # 8. exact-LogLoss secondary path (primary panel only)
    logloss = engine["logloss"]
    report["logloss_status"] = logloss.status
    report["logloss_contrasts"] = len(logloss.series)
    report["logloss_undefined_contrasts"] = sorted(
        "|".join(key) for key, value in logloss.undefined_replicates.items() if value
    )

    # 9. N912 nested robustness (secondary; never rescues the N456 primary)
    n912 = engine["n912_robustness"]
    report["n912_robustness"] = {
        "role": n912.get("role"),
        "cannot_rescue_primary": n912.get("cannot_rescue_primary"),
        "shared_test_draw_paired_by_replicate": n912.get("shared_test_draw_paired_by_replicate"),
        "comparisons": len(n912.get("comparisons", {})),
        "refit_blocks": len(engine.get("n912_refit", {})),
        "refit_statuses": sorted(
            {block.status for block in engine.get("n912_refit", {}).values()}
        ),
    }

    # 10. legacy secondary path
    report["legacy"] = {
        "models": list(engine["legacy_models"]),
        "populations": list(dag.legacy_populations),
        "unit_estimates": len(engine["legacy_estimates"]),
        "bootstrap_family_status": engine["legacy_bootstrap"].family_status(),
        "refit_blocks": len(engine["legacy_refit"]),
    }

    # 11. predictor 8 / 16 / 8 on the merged panel
    merged_measurements = build_predictor_measurements(merge_panels(dag.primary, dag.legacy))
    report["predictor"] = {
        "units_total": len(merged_measurements),
        "development_units": sum(
            1
            for m in merged_measurements
            if m.unit.analysis_role == r4_predictor.ROLE_DEVELOPMENT
        ),
        "validation_units": sum(
            1
            for m in merged_measurements
            if m.unit.analysis_role == r4_predictor.ROLE_PRIMARY_VALIDATION
        ),
        "legacy_units": sum(
            1
            for m in merged_measurements
            if m.unit.analysis_role == r4_predictor.ROLE_LEGACY_EXTENSION
        ),
        "status": engine["predictor"].status,
        "successful_replicates": engine["predictor"].successful_replicates,
        "planned_replicates": engine["predictor"].planned_replicates,
        "validation_rows": len(engine["predictor_point_rows"]),
        "point_estimate": (
            r4_predictor.primary_statistic(engine["predictor_point_rows"])
            if engine["predictor_point_rows"]
            else None
        ),
        "tail_rule": engine["predictor"].tail_rule,
    }
    return report


def _with_fit_failure(
    panel: PanelInputs,
    *,
    model: str,
    population: str,
    procedure: str,
    direction: str,
    side: str,
    failure_type: str,
    message: str,
) -> PanelInputs:
    """Return a copy of ``panel`` with one fit forced into the FAILED state.

    Used only by the synthetic formal-DAG qualification: it injects exactly the
    frozen full-fit FAILED semantics without touching any frozen module.
    """
    fits = dict(panel.fits)
    fits[(model, population, f"{procedure}|{direction}|{side}")] = ProcedureFit(
        procedure=procedure,
        status=FAILED,
        calibrator=None,
        reason=f"{failure_type}: {message}",
        state_fingerprint=None,
        failure_type=failure_type,
    )
    return PanelInputs(
        authority=panel.authority,
        model_keys=panel.model_keys,
        train_rows=panel.train_rows,
        test_rows=panel.test_rows,
        fits=fits,
    )


def _estimands_of(engine: Mapping[str, Any], key: str) -> tuple[str, ...]:
    return tuple(sorted(engine["estimates"][key]["estimands"]))


def dependency_qualification(dag: DagRun, *, replicates: int) -> dict[str, Any]:
    """Frozen dependency truth table + failure-propagation qualification.

    Injects a frozen B-beta gate-9 FULL-FIT failure (and cross-only / native-only
    / both-side variants) and checks that the engine never crashes, that the exact
    failure class is retained, that only the dependent estimands disappear, and
    that every fixed-size family keeps its size.
    """
    models = _panel_models(dag.primary, dag.primary_populations)
    model = models[0]
    population = dag.primary_populations[0]
    direction = dag.authority.direction_order[0]
    procedure = "B-beta"
    key = f"{model}|{population}|{direction}|{procedure}"
    message = "no constraint face produced an accepted optimum"

    def run(panel: PanelInputs) -> Mapping[str, Any]:
        return run_dag_engine(
            DagRun(
                authority=dag.authority,
                primary=panel,
                legacy=dag.legacy,
                n912=None,
                primary_populations=dag.primary_populations,
                legacy_populations=dag.legacy_populations,
                fixture_marker=SYNTHETIC_FIXTURE_MARKER,
            ),
            test_replicates=replicates,
            refit_replicates=max(2, replicates // 4),
            predictor_replicates=replicates,
        )

    out: dict[str, Any] = {"injected_unit": key, "injected_message": message}

    # (a) cross/source fit FAILED only -> Delta_deploy and Delta_transport vanish
    cross_only = run(
        _with_fit_failure(
            dag.primary,
            model=model,
            population=population,
            procedure=procedure,
            direction=direction,
            side="cross",
            failure_type="BetaImplementationError",
            message=message,
        )
    )
    out["cross_only_estimands"] = _estimands_of(cross_only, key)
    out["cross_only_failure_type"] = cross_only["estimates"][key]["cross_failure_type"]
    out["cross_only_status"] = cross_only["estimates"][key]["status"]
    out["cross_only_reason"] = cross_only["estimates"][key]["cross_reason"]
    out["cross_only_family_sizes"] = {
        "primary": len(cross_only["bootstrap"].primary_contrasts),
        "extension": len(cross_only["bootstrap"].extension_panel),
        "direction": len(cross_only["bootstrap"].direction_differences),
        "native": len(cross_only["bootstrap"].native_reference),
    }

    # (b) native/target fit FAILED only -> Delta_native and Delta_transport vanish
    native_only = run(
        _with_fit_failure(
            dag.primary,
            model=model,
            population=population,
            procedure=procedure,
            direction=direction,
            side="native",
            failure_type="BetaImplementationError",
            message=message,
        )
    )
    out["native_only_estimands"] = _estimands_of(native_only, key)

    # (c) both sides FAILED -> every estimand of that unit vanishes
    both = dag.primary
    for side in ("cross", "native"):
        both = _with_fit_failure(
            both,
            model=model,
            population=population,
            procedure=procedure,
            direction=direction,
            side=side,
            failure_type="BetaImplementationError",
            message=message,
        )
    both_engine = run(both)
    out["both_estimands"] = _estimands_of(both_engine, key)
    out["both_family_sizes"] = {
        "primary": len(both_engine["bootstrap"].primary_contrasts),
        "extension": len(both_engine["bootstrap"].extension_panel),
        "direction": len(both_engine["bootstrap"].direction_differences),
        "native": len(both_engine["bootstrap"].native_reference),
    }
    out["both_failed_fits"] = sorted(
        name
        for name, entry in both_engine["coverage_registry"].items()
        if entry["status"] == FAILED
    )
    out["both_failure_types"] = sorted(
        {
            entry["failure_type"]
            for entry in both_engine["coverage_registry"].values()
            if entry["failure_type"] is not None
        }
    )

    # (d) CORE4 must stay COMPLETE under an injected B-beta gate-9 failure
    core4_ok = True
    for family, members in both_engine["bootstrap"].family_status().items():
        if family in ("primary", "direction_difference"):
            core4_ok = core4_ok and members.get("status") == "COMPLETE"
    out["core4_primary_and_direction_complete_under_injection"] = core4_ok
    out["dependency_truth_table"] = {
        estimand: list(dependencies)
        for estimand, dependencies in ESTIMAND_DEPENDENCIES.items()
    }
    out["family_sizes_fixed"] = {
        "primary": 12,
        "extension": 8,
        "direction_difference": 6,
        "native_reference": 12,
    }
    return out


def synthetic_qualification(args: argparse.Namespace) -> int:
    """Qualify the frozen-DAG engine on invented fixtures only.

    The synthetic path calls the exact same ``run_dag_engine`` that formal
    execution calls; only the input source, replicate counts, output root and the
    fixture marker differ.
    """
    authority = load_frozen_authority()
    cells = load_cells()
    current_cells = [cell for cell in cells if cell.model_role == "current-generation"]
    legacy_cells = [cell for cell in cells if cell.model_role != "current-generation"]
    primary_populations = tuple(dict.fromkeys(cell.population_id for cell in current_cells))
    legacy_populations = tuple(dict.fromkeys(cell.population_id for cell in legacy_cells))
    replicates = args.synthetic_replicates

    def build_dag() -> DagRun:
        primary = build_synthetic_panel(authority, current_cells)
        legacy = build_synthetic_panel(authority, legacy_cells)
        n912_cells = [
            cell
            for cell in current_cells
            if cell.population_id
            in (
                r4_inference.HELLASWAG_POPULATION_ID,
                r4_inference.MEDMCQA_POPULATION_ID,
            )
        ]
        n912 = build_synthetic_panel(
            authority, n912_cells, train_per_stratum=2 * SYNTHETIC_TRAIN_PER_STRATUM
        )
        return DagRun(
            authority=primary.authority,
            primary=primary,
            legacy=legacy,
            n912=n912,
            primary_populations=primary_populations,
            legacy_populations=legacy_populations,
            fixture_marker=SYNTHETIC_FIXTURE_MARKER,
        )

    def run_once() -> dict[str, Any]:
        dag = build_dag()
        engine = run_dag_engine(
            dag,
            test_replicates=replicates,
            refit_replicates=max(2, replicates // 4),
            predictor_replicates=replicates,
        )
        return {
            "fixture_marker": SYNTHETIC_FIXTURE_MARKER,
            "primary": qualification_report(engine, dag, replicates=replicates, role="primary"),
            "legacy": qualification_report(engine, dag, replicates=replicates, role="legacy"),
            "dependency": dependency_qualification(dag, replicates=max(2, replicates // 2)),
            "engine_blocks": sorted(
                {
                    "input_load",
                    "point_estimates",
                    "n912_robustness",
                    "test_bootstrap",
                    "train_refit",
                    "predictor",
                    "final_assembly",
                }
            ),
            "primary_units": len(engine["primary_models"]) * len(primary_populations) * 2,
            "legacy_units": len(engine["legacy_models"]) * len(legacy_populations) * 2,
        }

    first = run_once()
    second = run_once()
    deterministic = canonical_json(first) == canonical_json(second)
    first["deterministic_rerun"] = deterministic
    first["scientific_outputs_computed"] = False
    first["mode"] = "synthetic-qualification"
    first["runner_source_sha256"] = sha256_file(RUNNER_SOURCE_PATH)
    root = Path(args.qualification_root)
    root.mkdir(parents=True, exist_ok=True)
    write_atomic(root / "synthetic-qualification.json", canonical_json(first))
    print(canonical_json(first), end="")
    return 0 if deterministic else 1


# --------------------------------------------------------------------------- #
# Formal execution (not authorized by this task)
# --------------------------------------------------------------------------- #


def _assert_formal_root_clean(root: Path, *, resume: bool) -> None:
    """Formal mode never overwrites unknown content in the formal output root."""
    if not root.exists():
        return
    entries = {path.name for path in root.iterdir()}
    allowed = {CHECKPOINT_FILENAME, "analysis-result.json"}
    unknown = entries - allowed
    if unknown:
        raise R4AnalysisFormalRootConflict(
            f"formal root {root} holds unknown entries: {sorted(unknown)}"
        )
    if not resume and entries:
        raise R4AnalysisFormalRootConflict(
            f"formal root {root} is not empty: {sorted(entries)}"
        )


def execute_formal_analysis(args: argparse.Namespace) -> int:
    """Run the frozen DAG over the frozen raw evidence. Requires the explicit flag."""
    authority = load_frozen_authority()
    cells = load_cells()
    root = Path(args.formal_root)
    store = CheckpointStore(root)
    _assert_formal_root_clean(root, resume=bool(store.load()["blocks"]))
    store.record(
        "authority_validation",
        status="COMPLETE",
        identity=authority.registry_fingerprint,
        output_fingerprint=authority.measurement_contract_fingerprint,
    )

    current_cells = [cell for cell in cells if cell.model_role == "current-generation"]
    legacy_cells = [cell for cell in cells if cell.model_role != "current-generation"]
    primary_populations = tuple(authority.population_order)
    legacy_populations = tuple(dict.fromkeys(cell.population_id for cell in legacy_cells))
    n912_populations = tuple(
        population
        for population in (
            r4_inference.HELLASWAG_POPULATION_ID,
            r4_inference.MEDMCQA_POPULATION_ID,
        )
        if population in primary_populations
    )

    primary = build_panel_inputs(
        authority, current_cells, population_ids=primary_populations, budget="N456"
    )
    legacy = build_panel_inputs(
        authority, legacy_cells, population_ids=legacy_populations, budget="N456"
    )
    n912 = (
        build_panel_inputs(
            authority, current_cells, population_ids=n912_populations, budget="N912"
        )
        if n912_populations
        else None
    )

    dag = DagRun(
        authority=authority,
        primary=primary,
        legacy=legacy,
        n912=n912,
        primary_populations=primary_populations,
        legacy_populations=legacy_populations,
        fixture_marker=None,
    )
    engine = run_dag_engine(
        dag,
        test_replicates=r4_inference.TEST_BOOTSTRAP_REPLICATES,
        refit_replicates=r4_inference.TRAIN_REFIT_REPLICATES,
        predictor_replicates=r4_predictor.PREDICTOR_BOOTSTRAP_REPLICATES,
        on_block=store.record,
    )

    skeleton = engine["artifact"]
    skeleton["runner"] = {
        "runner_id": RUNNER_ID,
        "runner_version": RUNNER_VERSION,
        "runner_source_sha256": sha256_file(RUNNER_SOURCE_PATH),
        "runner_contract_id": RUNNER_CONTRACT_ID,
        "result_fingerprint_version": ANALYSIS_RESULT_FINGERPRINT_VERSION,
        "checkpoints": store.completed(),
    }
    write_atomic(root / "analysis-result.json", canonical_json(skeleton))
    print(
        canonical_json(
            {
                "status": "COMPLETE",
                "root": str(root),
                "units": len(engine["estimates"]),
                "legacy_units": len(engine["legacy_estimates"]),
            }
        ),
        end="",
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
