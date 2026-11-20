#!/usr/bin/env python3

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from alloy_validation import normalize_composition
from composition import parse_composition
from report_types import estimate_value

from .common import clamp01, numeric


@dataclass
class CaseConfig:
    name: str
    composition: Dict[str, float]
    state: str
    env: str
    temperature_k: float
    oxygen_activity: float
    regime_override: str
    k_hardening: float
    material_profile: str | None = None


@dataclass
class CaseListItem:
    path: Path
    name: str
    saved_at: str
    material_regime: str
    vickers_hardness_hv: float | None
    corrosion_susceptibility_0_1: float | None
    brittleness_0_1: float | None
    load_error: str | None


def default_case() -> CaseConfig:
    return CaseConfig(
        name="untitled",
        composition={"Fe": 0.7, "Cr": 0.2, "C": 0.1},
        state="raw",
        env="air",
        temperature_k=298.15,
        oxygen_activity=0.21,
        regime_override="auto",
        k_hardening=1.0,
    )


def case_to_payload(case: CaseConfig, report: Dict[str, Any] | None = None) -> Dict[str, Any]:
    now_iso = datetime.now().isoformat(timespec="seconds")
    payload: Dict[str, Any] = {
        "saved_at": now_iso,
        "case": {
            "name": case.name,
            "composition": case.composition,
            "state": case.state,
            "env": case.env,
            "temperature_k": case.temperature_k,
            "oxygen_activity": case.oxygen_activity,
            "regime_override": case.regime_override,
            "k_hardening": case.k_hardening,
            "material_profile": case.material_profile,
        },
    }
    if isinstance(report, dict):
        classification = report["classification"]
        payload["summary"] = {
            "material_regime": classification["regime"] or classification["kind"],
            "vickers_hardness_hv": estimate_value(report, "vickers_hardness_hv"),
            "corrosion_susceptibility_0_1": estimate_value(report, "corrosion_susceptibility_index_0_1"),
            "brittleness_0_1": report.get("model_details", {}).get("hume_rothery", {}).get("brittleness_index_0_1"),
        }
    return payload


def payload_to_case(payload: Dict[str, Any]) -> CaseConfig:
    case = payload.get("case", payload)
    if not isinstance(case, dict):
        raise ValueError("Bad case payload format")

    composition_raw = case.get("composition", {})
    if isinstance(composition_raw, str):
        composition = parse_composition(composition_raw)
    elif isinstance(composition_raw, dict):
        composition_numeric = {str(k): float(v) for k, v in composition_raw.items()}
        composition = normalize_composition(composition_numeric)
    else:
        raise ValueError("Case composition must be a string or object")

    return CaseConfig(
        name=str(case.get("name", "untitled")),
        composition=composition,
        state=str(case.get("state", "raw")),
        env=str(case.get("env", "air")),
        temperature_k=numeric(case.get("temperature_k", 298.15), 298.15),
        oxygen_activity=clamp01(numeric(case.get("oxygen_activity", 0.21), 0.21)),
        regime_override=str(case.get("regime_override", "auto")),
        k_hardening=numeric(case.get("k_hardening", 1.0), 1.0),
        material_profile=case.get("material_profile"),
    )


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower())
    cleaned = cleaned.strip("-")
    return cleaned or "case"
