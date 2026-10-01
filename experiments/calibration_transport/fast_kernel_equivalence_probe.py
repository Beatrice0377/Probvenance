"""Synthetic-only reference-vs-fast kernel numerical equivalence probe (PHASE F).

This module performs **no** R4 study measurement. It builds a deterministic,
invented synthetic battery and pushes it through the *production* measurement
primitives (`measurements.build_cat_decision` / `build_ovr_proposition` +
`Probvenance.evaluate_with_trace` + `measurements.build_*_raw_record`), i.e. the
same objects `run_r4_measurements.measure_cat` / `measure_ovr` build. One
invocation in the reference environment and one in the fast environment produce
the two capture files; `--mode compare` then evaluates the predeclared
equivalence thresholds.

Outcome firewall: no MMLU / HellaSwag / MedMCQA item, no ground truth, and no
study score is read or produced here. The battery is invented text only.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

CAL_DIR = Path(__file__).resolve().parent

# --------------------------------------------------------------------------- #
# Predeclared equivalence thresholds (fixed BEFORE any fast-kernel result was seen)
# --------------------------------------------------------------------------- #

MAX_RESTRICTED_PROB_DIFF = 0.005
MAX_DESIGNATED_SCORE_DIFF = 0.005
MAX_CENTERED_LOGIT_DIFF = 0.10
MAX_TV_DISTANCE = 0.01

THRESHOLDS = {
    "max_abs_restricted_probability_difference": MAX_RESTRICTED_PROB_DIFF,
    "max_abs_designated_score_difference": MAX_DESIGNATED_SCORE_DIFF,
    "max_abs_centered_restricted_logit_difference": MAX_CENTERED_LOGIT_DIFF,
    "max_total_variation_distance": MAX_TV_DISTANCE,
}

BATTERY_ID = "r4-fast-kernel-synthetic-equivalence-battery"
BATTERY_VERSION = 1


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


runner = _load_sibling("run_r4_measurements")
measurements = runner.measurements

CANDIDATE_NAMES = ["option-0", "option-1", "option-2", "option-3"]

# --------------------------------------------------------------------------- #
# Deterministic invented battery: 12 items, anchors balanced 0/1/2/3
# --------------------------------------------------------------------------- #

_BATTERY_SPECS: list[tuple[str, str, list[str]]] = [
    (
        "short-plain",
        "The invented traveller paused at the gate and reached for",
        [
            "a warm loaf wrapped in cloth",
            "a thin reed cut from the marsh",
            "a pale stone marked with chalk",
            "a dry leaf caught in the hinge",
        ],
    ),
    (
        "medium-narrative",
        "In a made-up harbour town the lamplighter began his round, "
        "and by the second street he noticed that the fog had swallowed the pier.",
        [
            "he turned back toward the customs house",
            "he kept walking and counted the posts aloud",
            "he sat down on a bollard and waited",
            "he called out a name nobody answered",
        ],
    ),
    (
        "long-descriptive",
        "Consider an entirely invented workshop where every bench is covered with "
        "offcuts of copper wire, folded patterns of thin paper, small brass screws, "
        "half-finished frames, jars of cloudy solvent, blunt pencils, and a single "
        "unfinished clock whose hands have never been fitted.",
        [
            "the clock was left exactly as it was found",
            "the clock was moved to the window ledge",
            "the clock was wrapped in the folded paper",
            "the clock was taken apart screw by screw",
        ],
    ),
    (
        "repeated-tokens",
        "repeat repeat repeat the invented line runs on and on and on until the "
        "listener loses the thread of repeat repeat repeat",
        [
            "the sentence simply stops there",
            "the sentence doubles back on itself",
            "the sentence opens a new paragraph",
            "the sentence names the listener",
        ],
    ),
    (
        "punctuation-heavy",
        "Well -- then? Yes; no... perhaps! (The invented speaker shrugged.)",
        [
            "the room stayed quiet, and nobody spoke",
            "the room filled with a sudden argument",
            "the room was emptied before noon",
            "the room was locked from the outside",
        ],
    ),
    (
        "yes-no-neutral",
        "An invented report states that the ferry did not sail and that the market "
        "stayed shut for the whole of the invented day.",
        [
            "the report says the ferry stayed in port",
            "the report says the ferry left at dawn",
            "the report says the market opened early",
            "the report says the market moved inland",
        ],
    ),
    (
        "numeric",
        "An invented ledger records 17 crates, 4 lanterns, 90 metres of rope, and 3 "
        "spare wheels delivered on the 21st day of the 8th month.",
        [
            "the ledger records 3 spare wheels",
            "the ledger records 17 lanterns",
            "the ledger records 90 crates",
            "the ledger records 4 metres of rope",
        ],
    ),
    (
        "mixed-case",
        "The Invented Notice Reads: ALL Visitors MUST Sign The Book BEFORE Noon.",
        [
            "the notice asks visitors to sign in",
            "the notice asks visitors to leave",
            "the notice asks visitors to pay",
            "the notice asks visitors to wait outside",
        ],
    ),
    (
        "whitespace-dense",
        "An invented line     with    irregular      spacing between    the    words",
        [
            "the spacing was intentional in the invented text",
            "the spacing was a copying mistake",
            "the spacing hides a second message",
            "the spacing marks the end of a page",
        ],
    ),
    (
        "dashes-and-digits",
        "Item 12-4B (rev. 07) -- an invented part -- was listed as out of stock",
        [
            "the part could not be ordered that day",
            "the part arrived earlier than planned",
            "the part was replaced by another",
            "the part was never listed at all",
        ],
    ),
    (
        "dialogue",
        "\"Did you lock the invented shed?\" she asked. \"I think so,\" he said, "
        "\"but the wind was loud and I may have been mistaken.\"",
        [
            "he was not certain about the shed",
            "he was certain the shed was locked",
            "she had locked the shed herself",
            "the shed had no lock at all",
        ],
    ),
    (
        "abstract",
        "An invented argument claims that a rule which cannot be stated plainly "
        "should not be enforced at all.",
        [
            "the argument opposes unclear rules",
            "the argument supports stricter rules",
            "the argument ignores the question",
            "the argument repeats itself",
        ],
    ),
]

_FORBIDDEN_DATASET_MARKERS = (
    "mmlu",
    "hellaswag",
    "medmcqa",
    "commonsenseqa",
    "arc_",
    "openbookqa",
)


def build_battery() -> list[dict[str, Any]]:
    """Deterministic 12-item invented battery; anchors balanced 0/1/2/3."""
    items: list[dict[str, Any]] = []
    for index, (tag, question, descriptions) in enumerate(_BATTERY_SPECS):
        if len(descriptions) != 4:
            raise ValueError(f"battery item {tag!r} must carry exactly four descriptions")
        items.append(
            {
                "item_id": f"synthetic-{tag}",
                "tag": tag,
                "question": question,
                "candidate_names": list(CANDIDATE_NAMES),
                "candidate_descriptions": list(descriptions),
                "anchor_index": index % 4,
            }
        )
    _assert_synthetic_only(items)
    return items


def _assert_synthetic_only(items: list[dict[str, Any]]) -> None:
    blob = json.dumps(items, ensure_ascii=False).lower()
    for marker in _FORBIDDEN_DATASET_MARKERS:
        if marker in blob:
            raise ValueError(f"synthetic battery unexpectedly references {marker!r}")


def battery_fingerprint(items: list[dict[str, Any]]) -> str:
    payload = {"battery_id": BATTERY_ID, "battery_version": BATTERY_VERSION, "items": items}
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def dump_canonical(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


# --------------------------------------------------------------------------- #
# Capture
# --------------------------------------------------------------------------- #


def _model_meta(model_key: str) -> dict[str, Any]:
    entry = runner._require_model(model_key)
    return {
        "model": entry["model_id"],
        "revision": entry["revision"],
        "dtype": runner.DTYPE,
        "rendering_config": dict(runner.CHAT_TEMPLATE_KWARGS),
    }


def _capture_item(runtime: Any, item: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    names = list(item["candidate_names"])
    descriptions = list(item["candidate_descriptions"])
    anchor = names[int(item["anchor_index"])]
    candidates = list(zip(names, descriptions, strict=True))
    item_id = str(item["item_id"])

    cat_decision = measurements.build_cat_decision(item["question"], None, candidates)
    cat_evaluation = runtime.evaluate_with_trace(cat_decision)
    cat_record = measurements.build_cat_raw_record(
        cat_evaluation, case_id=item_id, item_id=item_id, anchor=anchor, model_meta=meta
    )

    ovr_proposition = measurements.build_ovr_proposition(
        item["question"], None, anchor, descriptions[int(item["anchor_index"])]
    )
    ovr_evaluation = runtime.evaluate_with_trace(ovr_proposition)
    ovr_record = measurements.build_ovr_raw_record(
        case_id=item_id,
        item_id=item_id,
        anchor=anchor,
        candidate_order=[anchor],
        evaluations={anchor: ovr_evaluation},
        model_meta=meta,
    )
    ovr_entry = ovr_record["candidates"][0]

    return {
        "item_id": item_id,
        "tag": item["tag"],
        "anchor_index": int(item["anchor_index"]),
        "anchor": anchor,
        "cat_candidate_order": list(cat_record["candidate_order"]),
        "cat_probabilities": {
            str(name): float(value) for name, value in cat_record["probabilities"].items()
        },
        "cat_resolved_token_ids": {
            str(label): int(token_id)
            for label, token_id in cat_record["resolved_token_ids"].items()
        },
        "cat_anchor_score": float(cat_record["anchor_score"]),
        "cat_decision_fingerprint": str(cat_record["decision_fingerprint"]),
        "cat_plan_fingerprint": str(cat_record["plan_fingerprint"]),
        "cat_rendered_input": cat_evaluation.trace.rendered_input,
        "ovr_designated_candidate": str(ovr_record["anchor"]),
        "ovr_probability_true": float(ovr_entry["probability_true"]),
        "ovr_positive_token_probability": float(ovr_entry["positive_token_probability"]),
        "ovr_negative_token_probability": float(ovr_entry["negative_token_probability"]),
        "ovr_positive_token_id": int(ovr_entry["positive_token_id"]),
        "ovr_negative_token_id": int(ovr_entry["negative_token_id"]),
        "ovr_decision_fingerprint": str(ovr_entry["decision_fingerprint"]),
        "ovr_plan_fingerprint": str(ovr_entry["plan_fingerprint"]),
        "ovr_rendered_input": ovr_evaluation.trace.rendered_input,
    }


def capture_model(model_key: str, *, device: str) -> dict[str, Any]:
    from probvenance import Probvenance

    items = build_battery()
    meta = _model_meta(model_key)
    cache = runner.verify_model_cache(model_key)
    backend = runner.load_backend(model_key, device=device)
    try:
        verbalizers = runner.verify_verbalizers(backend, model_key)
        runtime = Probvenance(backend=backend, capture_rendered_input=True)
        records = [_capture_item(runtime, item, meta) for item in items]
    finally:
        runner.unload_backend(backend)
    return {
        "model_key": model_key,
        "model_id": meta["model"],
        "model_revision": meta["revision"],
        "cache": cache,
        "verbalizers": verbalizers,
        "records": records,
    }


def run_capture(model_keys: list[str], *, device: str, output: Path) -> dict[str, Any]:
    items = build_battery()
    payload = {
        "probe_id": "r4-fast-kernel-numerical-equivalence-probe",
        "probe_version": 1,
        "mode": "capture",
        "battery_id": BATTERY_ID,
        "battery_version": BATTERY_VERSION,
        "battery_fingerprint": battery_fingerprint(items),
        "battery_items": items,
        "thresholds": THRESHOLDS,
        "device": device,
        "dtype": runner.DTYPE,
        "synthetic_only": True,
        "study_items_used": 0,
        "models": [capture_model(model_key, device=device) for model_key in model_keys],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(dump_canonical(payload), encoding="utf-8")
    return payload


# --------------------------------------------------------------------------- #
# Compare
# --------------------------------------------------------------------------- #


def _centered_logits(probabilities: dict[str, float]) -> dict[str, float]:
    logs = {name: math.log(value) for name, value in probabilities.items()}
    mean = math.fsum(logs.values()) / len(logs)
    return {name: value - mean for name, value in logs.items()}


def _tv_distance(left: dict[str, float], right: dict[str, float]) -> float:
    return 0.5 * math.fsum(abs(left[name] - right[name]) for name in left)


def compare(reference_path: Path, fast_path: Path, *, output: Path) -> dict[str, Any]:
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    fast = json.loads(fast_path.read_text(encoding="utf-8"))

    if reference["battery_fingerprint"] != fast["battery_fingerprint"]:
        raise SystemExit("STOP: battery fingerprint mismatch between the two captures")
    if reference["thresholds"] != fast["thresholds"]:
        raise SystemExit("STOP: predeclared thresholds differ between the two captures")

    fast_by_model = {entry["model_key"]: entry for entry in fast["models"]}
    per_model: list[dict[str, Any]] = []
    for ref_model in reference["models"]:
        model_key = ref_model["model_key"]
        if model_key not in fast_by_model:
            raise SystemExit(f"STOP: fast capture is missing model {model_key!r}")
        fast_model = fast_by_model[model_key]
        fast_by_item = {record["item_id"]: record for record in fast_model["records"]}

        max_prob_diff = 0.0
        max_designated_diff = 0.0
        max_logit_diff = 0.0
        max_tv = 0.0
        render_mismatches: list[str] = []
        token_mismatches: list[str] = []
        plan_mismatches: list[str] = []
        non_finite: list[str] = []
        per_item: list[dict[str, Any]] = []

        for ref_record in ref_model["records"]:
            item_id = ref_record["item_id"]
            fast_record = fast_by_item.get(item_id)
            if fast_record is None:
                raise SystemExit(f"STOP: fast capture is missing item {item_id!r} of {model_key!r}")

            if ref_record["cat_rendered_input"] != fast_record["cat_rendered_input"]:
                render_mismatches.append(f"{item_id}:cat")
            if ref_record["ovr_rendered_input"] != fast_record["ovr_rendered_input"]:
                render_mismatches.append(f"{item_id}:ovr")
            if ref_record["cat_resolved_token_ids"] != fast_record["cat_resolved_token_ids"]:
                token_mismatches.append(f"{item_id}:cat")
            if (
                ref_record["ovr_positive_token_id"] != fast_record["ovr_positive_token_id"]
                or ref_record["ovr_negative_token_id"] != fast_record["ovr_negative_token_id"]
            ):
                token_mismatches.append(f"{item_id}:ovr")
            for key in (
                "cat_decision_fingerprint",
                "cat_plan_fingerprint",
                "ovr_decision_fingerprint",
                "ovr_plan_fingerprint",
            ):
                if ref_record[key] != fast_record[key]:
                    plan_mismatches.append(f"{item_id}:{key}")

            order = ref_record["cat_candidate_order"]
            ref_probs = {name: ref_record["cat_probabilities"][name] for name in order}
            fast_probs = {name: fast_record["cat_probabilities"][name] for name in order}
            for name in order:
                for value in (ref_probs[name], fast_probs[name]):
                    if not math.isfinite(value):
                        non_finite.append(f"{item_id}:cat:{name}")

            prob_diff = max(abs(ref_probs[name] - fast_probs[name]) for name in order)
            ref_logits = _centered_logits(ref_probs)
            fast_logits = _centered_logits(fast_probs)
            logit_diff = max(abs(ref_logits[name] - fast_logits[name]) for name in order)
            tv = _tv_distance(ref_probs, fast_probs)

            designated_diff = abs(ref_record["cat_anchor_score"] - fast_record["cat_anchor_score"])
            designated_diff = max(
                designated_diff,
                abs(ref_record["ovr_probability_true"] - fast_record["ovr_probability_true"]),
            )

            max_prob_diff = max(max_prob_diff, prob_diff)
            max_logit_diff = max(max_logit_diff, logit_diff)
            max_tv = max(max_tv, tv)
            max_designated_diff = max(max_designated_diff, designated_diff)

            per_item.append(
                {
                    "item_id": item_id,
                    "tag": ref_record["tag"],
                    "max_restricted_probability_difference": prob_diff,
                    "max_centered_logit_difference": logit_diff,
                    "total_variation_distance": tv,
                    "designated_score_difference": designated_diff,
                }
            )

        passed = (
            not non_finite
            and not render_mismatches
            and not token_mismatches
            and not plan_mismatches
            and max_prob_diff <= MAX_RESTRICTED_PROB_DIFF
            and max_designated_diff <= MAX_DESIGNATED_SCORE_DIFF
            and max_logit_diff <= MAX_CENTERED_LOGIT_DIFF
            and max_tv <= MAX_TV_DISTANCE
        )
        per_model.append(
            {
                "model_key": model_key,
                "items": len(per_item),
                "synthetic_cat_forwards": len(per_item),
                "synthetic_ovr_forwards": len(per_item),
                "max_abs_restricted_probability_difference": max_prob_diff,
                "max_abs_designated_score_difference": max_designated_diff,
                "max_abs_centered_restricted_logit_difference": max_logit_diff,
                "max_total_variation_distance": max_tv,
                "non_finite_values": non_finite,
                "rendered_input_mismatches": render_mismatches,
                "resolved_token_id_mismatches": token_mismatches,
                "plan_fingerprint_mismatches": plan_mismatches,
                "status": "PASS" if passed else "FAIL",
                "per_item": per_item,
            }
        )

    overall = "PASS" if all(entry["status"] == "PASS" for entry in per_model) else "FAIL"
    payload = {
        "probe_id": "r4-fast-kernel-numerical-equivalence-probe",
        "probe_version": 1,
        "mode": "compare",
        "battery_fingerprint": reference["battery_fingerprint"],
        "thresholds": THRESHOLDS,
        "reference_capture": str(reference_path),
        "fast_capture": str(fast_path),
        "models": per_model,
        "overall_status": overall,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(dump_canonical(payload), encoding="utf-8")
    return payload


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="R4 fast-kernel numerical equivalence probe")
    parser.add_argument("--mode", choices=("capture", "compare"), required=True)
    parser.add_argument("--model-key", action="append", default=None)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--output", required=True)
    parser.add_argument("--reference", default=None)
    parser.add_argument("--fast", default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output = Path(args.output)
    if args.mode == "capture":
        model_keys = args.model_key or list(runner.MODEL_REGISTRY)
        payload = run_capture(model_keys, device=args.device, output=output)
        print(
            json.dumps(
                {
                    "mode": "capture",
                    "battery_fingerprint": payload["battery_fingerprint"],
                    "models": [entry["model_key"] for entry in payload["models"]],
                    "output": str(output),
                },
                indent=2,
            )
        )
        return 0
    if not args.reference or not args.fast:
        raise SystemExit("--mode compare requires --reference and --fast")
    payload = compare(Path(args.reference), Path(args.fast), output=output)
    summary = {"overall_status": payload["overall_status"], "output": str(output)}
    print(json.dumps(summary, indent=2))
    return 0 if payload["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
