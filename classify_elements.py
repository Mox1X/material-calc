#!/usr/bin/env python3
"""Classify element storage/render form factors using deterministic rules.

Output schema:
{
  "meta": {...},
  "counts_by_form_factor": {...},
  "elements": {
    "Fe": {
      "symbol": "Fe",
      "name": "Iron",
      "form_factor": "ingot",
      "phase_at_temperature": "solid",
      "tags": ["metal"],
      "confidence_0_1": 0.93,
      "candidate_forms": ["ingot"],
      "reasons": [...],
      "inputs": {...}
    }
  }
}
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


MODULE_DIR = Path(__file__).resolve().parent
DEFAULT_ELEMENTS_DIR = MODULE_DIR / "elements"
DEFAULT_OUTPUT_FILE = MODULE_DIR / "artifacts" / "element_categories.json"


# Chemistry-based rule groups (intentionally explicit for auditability).
NOBLE_GASES = {"He", "Ne", "Ar", "Kr", "Xe", "Rn"}
HALOGENS = {"F", "Cl", "Br", "I", "At", "Ts"}
ALKALI_METALS = {"Li", "Na", "K", "Rb", "Cs", "Fr"}
POWDER_GROUP = {"Li", "Na", "K", "Rb", "Cs", "Ca", "Sr", "Ba", "Ra", "P", "S"}
BRITTLE_GROUP = {"B", "C", "Si", "Ge", "As", "Sb", "Te", "Se", "Bi", "I"}
METALLOIDS = {"B", "Si", "Ge", "As", "Sb", "Te", "Po"}
AMPULE_NEAR_ROOM_TEMP = {"Hg", "Ga"}
CANISTER_OVERRIDE = {"Br"}

# Radioactivity heuristic for gameplay tagging.
RADIOACTIVE_ALWAYS = {"Tc", "Pm"}


QUALITY_SCORES = {
    "reference": 1.0,
    "estimated": 0.65,
    "unknown": 0.30,
}


def _quality_score(label: str) -> float:
    return QUALITY_SCORES.get((label or "").strip().lower(), 0.5)


def _phase_at_temperature(melting_point_k: float, boiling_point_k: float, temperature_k: float) -> str:
    if boiling_point_k <= temperature_k:
        return "gas"
    if melting_point_k <= temperature_k:
        return "liquid"
    return "solid"


def _radioactive_tag(symbol: str, atomic_number: int) -> bool:
    if symbol in RADIOACTIVE_ALWAYS:
        return True
    return atomic_number >= 84


def _load_element(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _classify_one(payload: Dict[str, Any], temperature_k: float) -> Dict[str, Any]:
    symbol = str(payload.get("symbol", "")).strip()
    name = str(payload.get("name", symbol)).strip()
    identification = payload.get("identification", {})
    thermal = payload.get("thermal", {})
    crystallography = payload.get("crystallography", {})
    quality = payload.get("data_quality", {})
    field_sources = payload.get("source_notes", {}).get("field_sources", {})

    atomic_number = int(identification.get("atomic_number", 0) or 0)
    melting_point_k = float(thermal.get("melting_point_K", 0.0) or 0.0)
    boiling_point_k = float(thermal.get("boiling_point_K", 0.0) or 0.0)
    crystal_structure_rt = str(crystallography.get("crystal_structure_rt", "") or "")

    mp_quality_label = str(quality.get("thermal", {}).get("melting_point_K", "unknown"))
    bp_quality_label = str(quality.get("thermal", {}).get("boiling_point_K", "unknown"))
    mp_quality = _quality_score(mp_quality_label)
    bp_quality = _quality_score(bp_quality_label)

    phase = _phase_at_temperature(melting_point_k, boiling_point_k, temperature_k)
    candidate_forms: List[str] = []
    reasons: List[str] = []

    if phase == "gas":
        candidate_forms.append("canister")
        reasons.append(f"Phase at {temperature_k:.2f} K is gas (bp={boiling_point_k:.2f} K).")
    elif phase == "liquid":
        candidate_forms.append("ampule")
        reasons.append(f"Phase at {temperature_k:.2f} K is liquid (mp={melting_point_k:.2f} K, bp={boiling_point_k:.2f} K).")

    if symbol in CANISTER_OVERRIDE:
        candidate_forms.append("canister")
        reasons.append("Explicit containment override (volatile liquid / sealed storage).")

    if symbol in AMPULE_NEAR_ROOM_TEMP:
        candidate_forms.append("ampule")
        reasons.append("Near room-temperature melt handling override.")

    if symbol in POWDER_GROUP and phase == "solid":
        candidate_forms.append("powder")
        reasons.append("Reactive/fragile bulk handling group prefers powder/granules.")

    if symbol in BRITTLE_GROUP and phase == "solid":
        candidate_forms.append("brittle_chunk")
        reasons.append("Brittle/metalloid-like handling group prefers chunk/crystal.")

    if not candidate_forms:
        candidate_forms.append("ingot")
        reasons.append("Default solid metallic handling route.")

    # Priority to avoid ambiguous outputs.
    if "canister" in candidate_forms:
        form_factor = "canister"
    elif "ampule" in candidate_forms:
        form_factor = "ampule"
    elif "powder" in candidate_forms:
        form_factor = "powder"
    elif "brittle_chunk" in candidate_forms:
        form_factor = "brittle_chunk"
    else:
        form_factor = "ingot"

    tags: List[str] = []
    if _radioactive_tag(symbol, atomic_number):
        tags.append("radioactive")
    if symbol in ALKALI_METALS:
        tags.append("alkali")
        tags.append("reactive")
    if symbol in HALOGENS:
        tags.append("halogen")
    if symbol in NOBLE_GASES:
        tags.append("noble_gas")
    if symbol in METALLOIDS:
        tags.append("metalloid")
    if symbol in {"Hg", "Ga", "Br"}:
        tags.append("sealed_handling")
    if phase == "gas":
        tags.append("gas_at_target_temp")
    elif phase == "liquid":
        tags.append("liquid_at_target_temp")
    else:
        tags.append("solid_at_target_temp")

    # Confidence: confidence in measured phase data + small penalties for conflict/overrides.
    phase_conf = 0.55 + 0.45 * min(mp_quality, bp_quality)
    confidence = phase_conf
    if symbol in AMPULE_NEAR_ROOM_TEMP or symbol in CANISTER_OVERRIDE:
        confidence -= 0.08
    if len(set(candidate_forms)) > 1:
        confidence -= 0.10
    confidence = max(0.10, min(0.99, confidence))

    return {
        "symbol": symbol,
        "name": name,
        "form_factor": form_factor,
        "phase_at_temperature": phase,
        "tags": sorted(set(tags)),
        "confidence_0_1": round(confidence, 3),
        "candidate_forms": sorted(set(candidate_forms)),
        "reasons": reasons,
        "inputs": {
            "atomic_number": atomic_number,
            "melting_point_K": round(melting_point_k, 5),
            "boiling_point_K": round(boiling_point_k, 5),
            "crystal_structure_rt": crystal_structure_rt,
            "data_quality": {
                "melting_point_K": mp_quality_label,
                "boiling_point_K": bp_quality_label,
            },
            "field_sources": {
                "melting_point_K": field_sources.get("thermal.melting_point_K", ""),
                "boiling_point_K": field_sources.get("thermal.boiling_point_K", ""),
                "crystal_structure_rt": field_sources.get("crystallography.crystal_structure_rt", ""),
            },
        },
    }


def classify_elements(elements_dir: Path, temperature_k: float) -> Dict[str, Any]:
    elements: Dict[str, Any] = {}
    counts = Counter()
    for path in sorted(elements_dir.glob("*.json")):
        payload = _load_element(path)
        item = _classify_one(payload, temperature_k)
        symbol = item["symbol"]
        elements[symbol] = item
        counts[item["form_factor"]] += 1

    return {
        "meta": {
            "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "classifier_version": "rules-v1",
            "temperature_k": round(temperature_k, 5),
            "elements_dir": str(elements_dir.resolve()),
            "total_elements": len(elements),
        },
        "counts_by_form_factor": dict(sorted(counts.items())),
        "elements": dict(sorted(elements.items())),
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Classify element form factors using deterministic rules")
    p.add_argument("--elements-dir", default=str(DEFAULT_ELEMENTS_DIR), help="Path to elements JSON directory")
    p.add_argument("--temperature-k", type=float, default=298.15, help="Temperature for phase-based categorization")
    p.add_argument("--output", default=str(DEFAULT_OUTPUT_FILE), help="Output JSON path")
    return p


def main() -> None:
    args = build_parser().parse_args()
    elements_dir = Path(args.elements_dir)
    output_path = Path(args.output)

    if args.temperature_k <= 0:
        raise ValueError("--temperature-k must be > 0")
    if not elements_dir.is_dir():
        raise FileNotFoundError(f"Elements directory not found: {elements_dir}")

    result = classify_elements(elements_dir, float(args.temperature_k))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Classified elements: {result['meta']['total_elements']}")
    print(f"Output: {output_path.resolve()}")
    print("Counts by form factor:")
    for key, value in result["counts_by_form_factor"].items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
