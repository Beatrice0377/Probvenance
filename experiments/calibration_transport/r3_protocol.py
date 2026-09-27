"""R3 confirmatory protocol: the frozen parent identity.

This module builds the R3 parent research protocol that governs the future
confirmatory study described by ``R3_PROTOCOL.md`` and Research Specification
v2. It is research-only and performs **no model measurement**.

The parent protocol commits Research Spec v2, the frozen population manifest,
the two model conditions, the measurement identities, the fixed four-procedure
calibration panel ``F``, the estimands, the inference and multiplicity contract,
and the non-claims. The R1 ``PairedFixedDecisionPlan`` artifacts remain
historical Research Spec v1 child structures; the protocol merely commits their
fingerprints.

The statistical procedure identity ``F`` deliberately excludes the numerical
solver, arithmetic precision, device, and library versions: those are execution
provenance recorded by a future run, not part of the statistical procedure.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from probvenance.calibration import GroundTruthProvenance, GroundTruthSemanticsIdentity
from probvenance.fingerprint import fingerprint

_HARNESS_DIR = Path(__file__).resolve().parent


def _load_sibling(name: str) -> Any:
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


_pilot = _load_sibling("pilot_plan")
_population = _load_sibling("r3_population")
_measurements = _load_sibling("measurements")
_integrity = _pilot._integrity
Split = _integrity.Split

R3_RESEARCH_SPEC_ID = "calibration-transport-research-spec"
R3_RESEARCH_SPEC_VERSION = 2

R3_PROTOCOL_ARTIFACT_TYPE = "r3-confirmatory-protocol"
R3_PROTOCOL_VERSION = 1
R3_PROTOCOL_FINGERPRINT_VERSION = 1
R3_PROTOCOL_ID = "r3-confirmatory-procedure-conditioned-transport"
R3_PROTOCOL_NAME = "R3 confirmatory procedure-conditioned calibration transport"

R3_SPLIT_PROTOCOL_ID = "r3-mmlu-subject-balanced-train8-test20"
R3_SPLIT_PROTOCOL_VERSION = 1

# --- Calibration-procedure panel F ----------------------------------------- #
FAMILY_P_ID = "research-l2-logistic-fixed-decision-probability"
FAMILY_P_VERSION = 1
FAMILY_L_ID = "research-l2-logistic-logit-fixed-decision-probability"
FAMILY_L_VERSION = 1
FEATURE_P_ID = "identity-raw-probability"
FEATURE_P_VERSION = 1
FEATURE_L_ID = "exact-logit-probability"
FEATURE_L_VERSION = 1
ENDPOINT_P_ID = "exact-raw-probability-accepted"
ENDPOINT_P_VERSION = 1
ENDPOINT_L_ID = "reject-exact-probability-endpoints"
ENDPOINT_L_VERSION = 1
OBJECTIVE_ID = "mean-bernoulli-nll-plus-l2"
OBJECTIVE_VERSION = 1
REGULARIZATION_RULE_ID = "fixed-l2-strength"
REGULARIZATION_RULE_VERSION = 1
FITTING_DATA_PROTOCOL_ID = "paired-frozen-decision-train"
FITTING_DATA_PROTOCOL_VERSION = 1
SELECTION_RULE_ID = "fixed-panel-no-selection"
SELECTION_RULE_VERSION = 1

L2_LOW = 1e-4
L2_HISTORICAL = 1e-2

PROCEDURE_P_LOW = "P-low"
PROCEDURE_P_HISTORICAL = "P-historical"
PROCEDURE_L_LOW = "L-low"
PROCEDURE_L_HISTORICAL = "L-historical"
R3_PROCEDURE_LABELS: tuple[str, ...] = (
    PROCEDURE_P_LOW,
    PROCEDURE_P_HISTORICAL,
    PROCEDURE_L_LOW,
    PROCEDURE_L_HISTORICAL,
)

# --- Ground truth ---------------------------------------------------------- #
R3_GT_LABEL_SOURCE = "pinned cais/mmlu answer field"
R3_GT_LABELING_RULE = "mmlu-answer-index-to-source-option"
R3_GT_AMBIGUITY_POLICY = "pinned-dataset-answer-key-as-authoritative"
R3_GT_TAXONOMY_ID = "mmlu-four-option-answer-key"
R3_GT_TAXONOMY_VERSION = 1

# --- Model conditions ------------------------------------------------------ #
PRIMARY_MODEL_ID = "openbmb/MiniCPM5-2B"
PRIMARY_MODEL_REVISION = "12a3808a956f869c767195e9266b59c4d21d92e2"
REPLICATION_MODEL_ID = "Qwen/Qwen3.5-2B"
REPLICATION_MODEL_REVISION = "15852e8c16360a2fea060d615a32b45270f8a8fc"
MODEL_DTYPE = "bfloat16"
MODEL_RENDERING_CONFIG: dict[str, Any] = {"enable_thinking": False}

# --- Inference and multiplicity -------------------------------------------- #
TEST_BOOTSTRAP_ID = "sha256-r3-subject-stratified-paired-test-bootstrap"
TEST_BOOTSTRAP_VERSION = 1
TEST_BOOTSTRAP_REPLICATES = 20000
TRAIN_REFIT_BOOTSTRAP_ID = "sha256-r3-subject-stratified-paired-train-refit-bootstrap"
TRAIN_REFIT_BOOTSTRAP_VERSION = 1
TRAIN_REFIT_BOOTSTRAP_REPLICATES = 2000
PERCENTILE_RULE_ID = "nearest-rank-percentile"
PERCENTILE_RULE_VERSION = 1

PRIMARY_FAMILY_SIZE = 6
PRIMARY_ALPHA = 0.05
PRIMARY_LOWER_TAIL = "1/240"
PRIMARY_UPPER_TAIL = "239/240"
NATIVE_REFERENCE_FAMILY_SIZE = 8
NATIVE_LOWER_TAIL = "1/320"
NATIVE_UPPER_TAIL = "319/320"

PRIMARY_DIRECTIONS: tuple[str, ...] = ("CAT->OVR", "OVR->CAT")
PRIMARY_EFFECTS: tuple[str, ...] = ("feature", "regularization", "interaction")

NATIVE_REFERENCE_STATES: tuple[str, ...] = (
    "NATIVE_IMPROVEMENT_SUPPORTED",
    "NATIVE_DEGRADATION_SUPPORTED",
    "NATIVE_ADEQUACY_UNRESOLVED",
)

EXPECTED_EVALUATIONS_PER_ITEM = 5  # 1 CAT + 4 independent OVR

R3_NON_CLAIMS: tuple[str, ...] = (
    "R3 does not establish global CAT/OVR compatibility.",
    "R3 does not establish universal calibration-procedure superiority.",
    "R3 does not establish a causal effect of score-range mismatch.",
    "R3 does not establish contamination-free MMLU generalization.",
    "R3 does not authorize production cross-identity profile reuse.",
    "R3 does not establish transitivity or symmetry of the conditioned relation.",
    "R3 does not establish all-model procedure-level generalization.",
)

DEFAULT_MANIFEST_PATH = _population.DEFAULT_MANIFEST_PATH
DEFAULT_DESIGN_PATH = _HARNESS_DIR / "r3_protocol_design.json"


class ProtocolError(ValueError):
    """Raised when the R3 protocol violates its freeze contract."""


@dataclass(frozen=True, slots=True)
class R3CalibrationProcedure:
    """Immutable statistical procedure identity ``F`` (no solver provenance)."""

    label: str
    procedure_id: str
    procedure_version: int
    family_id: str
    family_version: int
    feature_id: str
    feature_version: int
    objective_id: str
    objective_version: int
    regularization_rule_id: str
    regularization_rule_version: int
    l2_strength: float
    endpoint_policy_id: str
    endpoint_policy_version: int
    fitting_data_protocol_id: str
    fitting_data_protocol_version: int
    selection_rule_id: str
    selection_rule_version: int

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "procedure_id": self.procedure_id,
            "procedure_version": self.procedure_version,
            "family_id": self.family_id,
            "family_version": self.family_version,
            "feature_id": self.feature_id,
            "feature_version": self.feature_version,
            "objective_id": self.objective_id,
            "objective_version": self.objective_version,
            "regularization_rule_id": self.regularization_rule_id,
            "regularization_rule_version": self.regularization_rule_version,
            "l2_strength": self.l2_strength,
            "endpoint_policy_id": self.endpoint_policy_id,
            "endpoint_policy_version": self.endpoint_policy_version,
            "fitting_data_protocol_id": self.fitting_data_protocol_id,
            "fitting_data_protocol_version": self.fitting_data_protocol_version,
            "selection_rule_id": self.selection_rule_id,
            "selection_rule_version": self.selection_rule_version,
        }

    @property
    def fingerprint(self) -> str:
        return fingerprint(self.canonical_payload())


def _procedure(
    label: str,
    *,
    family: str,
    family_version: int,
    feature: str,
    feature_version: int,
    endpoint: str,
    endpoint_version: int,
    l2_strength: float,
) -> R3CalibrationProcedure:
    return R3CalibrationProcedure(
        label=label,
        procedure_id=f"r3-procedure-{label}",
        procedure_version=1,
        family_id=family,
        family_version=family_version,
        feature_id=feature,
        feature_version=feature_version,
        objective_id=OBJECTIVE_ID,
        objective_version=OBJECTIVE_VERSION,
        regularization_rule_id=REGULARIZATION_RULE_ID,
        regularization_rule_version=REGULARIZATION_RULE_VERSION,
        l2_strength=l2_strength,
        endpoint_policy_id=endpoint,
        endpoint_policy_version=endpoint_version,
        fitting_data_protocol_id=FITTING_DATA_PROTOCOL_ID,
        fitting_data_protocol_version=FITTING_DATA_PROTOCOL_VERSION,
        selection_rule_id=SELECTION_RULE_ID,
        selection_rule_version=SELECTION_RULE_VERSION,
    )


def procedure_panel() -> tuple[R3CalibrationProcedure, ...]:
    """The frozen 2x2 fixed panel: {raw-p, logit-p} x {1e-4, 1e-2}."""
    return (
        _procedure(
            PROCEDURE_P_LOW,
            family=FAMILY_P_ID,
            family_version=FAMILY_P_VERSION,
            feature=FEATURE_P_ID,
            feature_version=FEATURE_P_VERSION,
            endpoint=ENDPOINT_P_ID,
            endpoint_version=ENDPOINT_P_VERSION,
            l2_strength=L2_LOW,
        ),
        _procedure(
            PROCEDURE_P_HISTORICAL,
            family=FAMILY_P_ID,
            family_version=FAMILY_P_VERSION,
            feature=FEATURE_P_ID,
            feature_version=FEATURE_P_VERSION,
            endpoint=ENDPOINT_P_ID,
            endpoint_version=ENDPOINT_P_VERSION,
            l2_strength=L2_HISTORICAL,
        ),
        _procedure(
            PROCEDURE_L_LOW,
            family=FAMILY_L_ID,
            family_version=FAMILY_L_VERSION,
            feature=FEATURE_L_ID,
            feature_version=FEATURE_L_VERSION,
            endpoint=ENDPOINT_L_ID,
            endpoint_version=ENDPOINT_L_VERSION,
            l2_strength=L2_LOW,
        ),
        _procedure(
            PROCEDURE_L_HISTORICAL,
            family=FAMILY_L_ID,
            family_version=FAMILY_L_VERSION,
            feature=FEATURE_L_ID,
            feature_version=FEATURE_L_VERSION,
            endpoint=ENDPOINT_L_ID,
            endpoint_version=ENDPOINT_L_VERSION,
            l2_strength=L2_HISTORICAL,
        ),
    )


def ground_truth_semantics() -> GroundTruthSemanticsIdentity:
    provenance = GroundTruthProvenance(
        label_source=R3_GT_LABEL_SOURCE,
        labeling_rule=R3_GT_LABELING_RULE,
        adjudicated=False,
        ambiguity_policy=R3_GT_AMBIGUITY_POLICY,
        taxonomy_id=R3_GT_TAXONOMY_ID,
        taxonomy_version=R3_GT_TAXONOMY_VERSION,
    )
    return GroundTruthSemanticsIdentity.from_provenance(provenance)


def build_child_plan(
    manifest: Mapping[str, Any],
    *,
    model_id: str,
    model_revision: str,
) -> Any:
    """Build the R1 paired structural plan for one model condition."""
    items = []
    for item in _population.manifest_items(manifest):
        anchor = _pilot.select_anchor(item["item_id"], list(_population.R3_CANDIDATE_NAMES))
        correct = f"option-{item['answer_index']}"
        r3_split = Split.TRAIN if item["split"] == _population.R3_SPLIT_TRAIN else Split.TEST
        items.append(
            _integrity.PlannedFixedDecisionItem(
                item_id=item["item_id"],
                split=r3_split,
                anchor_value=anchor,
                ground_truth_value=correct,
                anchor_correct=(anchor == correct),
            )
        )
    identity = ground_truth_semantics()
    return _integrity.PairedFixedDecisionPlan(
        model_id=model_id,
        model_revision=model_revision,
        population_id=_population.R3_POPULATION_ID,
        population_version=_population.R3_POPULATION_VERSION,
        ground_truth_semantics_fingerprint=identity.fingerprint,
        ground_truth_semantics_fingerprint_version=1,
        measurement_a=_integrity.MeasurementProtocolIdentity(
            _measurements.CAT_MEASUREMENT_ID, _measurements.CAT_MEASUREMENT_VERSION
        ),
        measurement_b=_integrity.MeasurementProtocolIdentity(
            _measurements.OVR_MEASUREMENT_ID, _measurements.OVR_MEASUREMENT_VERSION
        ),
        anchor_selection_id=_pilot.ANCHOR_SELECTION_ID,
        anchor_selection_version=_pilot.ANCHOR_SELECTION_VERSION,
        split_protocol_id=R3_SPLIT_PROTOCOL_ID,
        split_protocol_version=R3_SPLIT_PROTOCOL_VERSION,
        items=tuple(items),
    )


def build_protocol(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Build the frozen R3 parent protocol payload (no fingerprint yet)."""
    _population.validate_manifest(manifest)
    primary_plan = build_child_plan(
        manifest, model_id=PRIMARY_MODEL_ID, model_revision=PRIMARY_MODEL_REVISION
    )
    replication_plan = build_child_plan(
        manifest, model_id=REPLICATION_MODEL_ID, model_revision=REPLICATION_MODEL_REVISION
    )
    identity = ground_truth_semantics()
    panel = procedure_panel()
    counts = manifest["counts"]
    items_total = counts["total"]

    primary_contrasts = [
        {"direction": direction, "effect": effect}
        for direction in PRIMARY_DIRECTIONS
        for effect in PRIMARY_EFFECTS
    ]

    payload: dict[str, Any] = {
        "artifact_type": R3_PROTOCOL_ARTIFACT_TYPE,
        "artifact_version": R3_PROTOCOL_VERSION,
        "fingerprint_version": R3_PROTOCOL_FINGERPRINT_VERSION,
        "protocol_id": R3_PROTOCOL_ID,
        "protocol_name": R3_PROTOCOL_NAME,
        "research_spec": {"id": R3_RESEARCH_SPEC_ID, "version": R3_RESEARCH_SPEC_VERSION},
        "population": {
            "population_id": manifest["population_id"],
            "population_version": manifest["population_version"],
            "manifest_artifact_type": manifest["artifact_type"],
            "manifest_fingerprint": manifest["manifest_fingerprint"],
            "dataset_repository": manifest["dataset"]["repository"],
            "dataset_revision": manifest["dataset"]["revision"],
            "selection_protocol_id": manifest["selection_protocol"]["id"],
            "selection_protocol_version": manifest["selection_protocol"]["version"],
        },
        "partition": {
            "train": counts["train"],
            "test": counts["test"],
            "audit": counts["audit"],
            "total": items_total,
            "train_per_subject": manifest["selection_protocol"]["train_per_subject"],
            "test_per_subject": manifest["selection_protocol"]["test_per_subject"],
        },
        "ground_truth_semantics": {
            "fingerprint": identity.fingerprint,
            "fingerprint_version": 1,
            "provenance": {
                "label_source": R3_GT_LABEL_SOURCE,
                "labeling_rule": R3_GT_LABELING_RULE,
                "adjudicated": False,
                "ambiguity_policy": R3_GT_AMBIGUITY_POLICY,
                "taxonomy_id": R3_GT_TAXONOMY_ID,
                "taxonomy_version": R3_GT_TAXONOMY_VERSION,
            },
        },
        "anchor": {
            "id": _pilot.ANCHOR_SELECTION_ID,
            "version": _pilot.ANCHOR_SELECTION_VERSION,
            "input": "item_id + candidate semantic names only",
        },
        "measurement_a": {
            "measurement_id": _measurements.CAT_MEASUREMENT_ID,
            "measurement_version": _measurements.CAT_MEASUREMENT_VERSION,
        },
        "measurement_b": {
            "measurement_id": _measurements.OVR_MEASUREMENT_ID,
            "measurement_version": _measurements.OVR_MEASUREMENT_VERSION,
        },
        "target": {
            "id": _integrity.FIXED_DECISION_TARGET_ID,
            "version": _integrity.FIXED_DECISION_TARGET_VERSION,
        },
        "input_score": {
            "id": _integrity.FIXED_DECISION_INPUT_SCORE_ID,
            "version": _integrity.FIXED_DECISION_INPUT_SCORE_VERSION,
        },
        "models": {
            "primary": {
                "model_id": PRIMARY_MODEL_ID,
                "model_revision": PRIMARY_MODEL_REVISION,
                "role": "primary-confirmatory",
                "child_plan_fingerprint": primary_plan.fingerprint,
            },
            "replication": {
                "model_id": REPLICATION_MODEL_ID,
                "model_revision": REPLICATION_MODEL_REVISION,
                "role": "preregistered-replication",
                "child_plan_fingerprint": replication_plan.fingerprint,
            },
        },
        "runtime": {
            "dtype": MODEL_DTYPE,
            "rendering": dict(MODEL_RENDERING_CONFIG),
            "local_files_only": True,
        },
        "procedures": [
            {"fingerprint": procedure.fingerprint, "payload": procedure.canonical_payload()}
            for procedure in panel
        ],
        "baselines": {
            "raw": "R_raw(B) = loss(S_B_i, Y_i)",
            "native": "R_native(B;F) = loss(g_F^B(S_B_i), Y_i)",
            "cross": "R_cross(A->B;F) = loss(g_F^A(S_B_i), Y_i)",
            "contrasts": [
                "Delta_native/raw = R_native(B;F) - R_raw(B)",
                "Delta_cross/raw = R_cross(A->B;F) - R_raw(B)",
                "Delta_cross/native = R_cross(A->B;F) - R_native(B;F)",
            ],
        },
        "primary_estimand": {
            "id": "cross-vs-raw-procedure-conditioned-transport-risk",
            "version": 1,
            "definition": "C_d(F) = R_cross(A->B;F) - R_raw(B), primary metric Brier",
        },
        "primary_contrasts": primary_contrasts,
        "primary_hypothesis_family": {
            "size": PRIMARY_FAMILY_SIZE,
            "null": "effect = 0",
            "alternative": "effect != 0 (two-sided)",
        },
        "bootstrap": {
            "test": {
                "id": TEST_BOOTSTRAP_ID,
                "version": TEST_BOOTSTRAP_VERSION,
                "replicates": TEST_BOOTSTRAP_REPLICATES,
            },
            "train_refit": {
                "id": TRAIN_REFIT_BOOTSTRAP_ID,
                "version": TRAIN_REFIT_BOOTSTRAP_VERSION,
                "replicates": TRAIN_REFIT_BOOTSTRAP_REPLICATES,
            },
            "percentile_rule": {"id": PERCENTILE_RULE_ID, "version": PERCENTILE_RULE_VERSION},
            "shared_draws": True,
        },
        "multiplicity": {
            "primary": {
                "alpha": PRIMARY_ALPHA,
                "family_size": PRIMARY_FAMILY_SIZE,
                "correction": "bonferroni-percentile-interval",
                "lower_tail": PRIMARY_LOWER_TAIL,
                "upper_tail": PRIMARY_UPPER_TAIL,
            },
            "native_reference": {
                "alpha": PRIMARY_ALPHA,
                "family_size": NATIVE_REFERENCE_FAMILY_SIZE,
                "correction": "bonferroni-percentile-interval",
                "lower_tail": NATIVE_LOWER_TAIL,
                "upper_tail": NATIVE_UPPER_TAIL,
            },
        },
        "native_reference_states": list(NATIVE_REFERENCE_STATES),
        "completeness_rule": {
            "requires": (
                "100% paired measurement completeness "
                "(CAT=SCORED and OVR=SCORED) for every selected item"
            ),
            "row_substitution": False,
            "winner_agreement_filter": False,
        },
        "expected_evaluations": {
            "evaluations_per_item": EXPECTED_EVALUATIONS_PER_ITEM,
            "items_per_model": items_total,
            "per_model": items_total * EXPECTED_EVALUATIONS_PER_ITEM,
            "total_two_models": 2 * items_total * EXPECTED_EVALUATIONS_PER_ITEM,
        },
        "secondary_diagnostics": [
            "exact-logloss",
            "equal-width-reliability-10-bin",
            "observed-score-range",
            "source-quantile-range-coverage",
            "range-loss-decomposition",
            "end-to-end-winner-diagnostics",
        ],
        "non_claims": list(R3_NON_CLAIMS),
    }
    return payload


def protocol_canonical_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "protocol_fingerprint"}


def protocol_fingerprint(payload: Mapping[str, Any]) -> str:
    return fingerprint(protocol_canonical_payload(payload))


def validate_protocol(payload: Mapping[str, Any]) -> None:
    """Validate the R3 protocol against the frozen semantic contract."""
    if payload.get("artifact_type") != R3_PROTOCOL_ARTIFACT_TYPE:
        raise ProtocolError("protocol artifact_type mismatch")
    if payload.get("artifact_version") != R3_PROTOCOL_VERSION:
        raise ProtocolError("protocol artifact_version mismatch")
    if payload.get("research_spec") != {"id": R3_RESEARCH_SPEC_ID, "version": 2}:
        raise ProtocolError("protocol must commit Research Spec v2")
    procedures = payload.get("procedures", [])
    labels = [entry["payload"]["label"] for entry in procedures]
    if labels != list(R3_PROCEDURE_LABELS):
        raise ProtocolError(
            "protocol must freeze exactly the four fixed procedures P/L x low/historical"
        )
    for entry in procedures:
        procedure = entry["payload"]
        if procedure["selection_rule_id"] != SELECTION_RULE_ID:
            raise ProtocolError("every procedure must declare fixed-panel-no-selection")
        if procedure["l2_strength"] not in (L2_LOW, L2_HISTORICAL):
            raise ProtocolError("procedure l2 strength outside the frozen panel")
    if len(payload.get("primary_contrasts", [])) != PRIMARY_FAMILY_SIZE:
        raise ProtocolError("protocol must declare exactly six primary contrasts")
    if payload["multiplicity"]["primary"]["lower_tail"] != PRIMARY_LOWER_TAIL:
        raise ProtocolError("primary multiplicity tail mismatch")
    if payload["multiplicity"]["native_reference"]["family_size"] != NATIVE_REFERENCE_FAMILY_SIZE:
        raise ProtocolError("native-reference family size mismatch")
    if payload.get("protocol_fingerprint") != protocol_fingerprint(payload):
        raise ProtocolError("protocol fingerprint does not match its content")


def build_design(manifest: Mapping[str, Any]) -> dict[str, Any]:
    payload = build_protocol(manifest)
    payload["protocol_fingerprint"] = protocol_fingerprint(payload)
    validate_protocol(payload)
    return payload


def load_design(path: str | Path = DEFAULT_DESIGN_PATH) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_protocol(payload)
    return payload


def write_design(payload: Mapping[str, Any], path: str | Path = DEFAULT_DESIGN_PATH) -> Path:
    target = Path(path)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    return target


def _main(argv: Sequence[str]) -> int:
    manifest = _population.load_manifest(argv[1] if len(argv) > 1 else DEFAULT_MANIFEST_PATH)
    design = build_design(manifest)
    target = write_design(design, argv[2] if len(argv) > 2 else DEFAULT_DESIGN_PATH)
    print(
        f"wrote {target} (protocol_fingerprint={design['protocol_fingerprint']} "
        f"primary_plan={design['models']['primary']['child_plan_fingerprint']})"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(_main(sys.argv))
