#!/usr/bin/env python3

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

from config.tuning_defaults import DEFAULT_TUNING_PROFILE
DEFAULT_TUNING: Dict[str, Any] = deepcopy(DEFAULT_TUNING_PROFILE)


def _require_mapping(node: Any, path: str) -> Dict[str, Any]:
    if not isinstance(node, dict):
        raise ValueError(f"Tuning section '{path}' must be a JSON object")
    return node


def _require_number(node: Any, path: str) -> float:
    try:
        return float(node)
    except (TypeError, ValueError):
        raise ValueError(f"Tuning value '{path}' must be numeric")


def validate_tuning_profile(profile: Dict[str, Any]) -> None:
    if not isinstance(profile, dict):
        raise ValueError("Tuning profile must be a JSON object")

    if "thermal" in profile:
        section = _require_mapping(profile.get("thermal"), "thermal")
        for key in (
            "delta_to_base_weight",
            "quality_pull_to_base",
            "affinity_penalty_strength",
            "affinity_soft_penalty_strength",
            "min_tm_fraction",
        ):
            if key in section:
                _require_number(section[key], f"thermal.{key}")

    if "hardness" in profile:
        section = _require_mapping(profile.get("hardness"), "hardness")
        for key in (
            "delta_to_base_weight",
            "quality_pull_to_base",
            "superalloy_al_ti_threshold",
        ):
            if key in section:
                _require_number(section[key], f"hardness.{key}")

    if "state_factors" in profile:
        section = _require_mapping(profile.get("state_factors"), "state_factors")
        if "high_carbide_steel_threshold" in section:
            _require_number(section["high_carbide_steel_threshold"], "state_factors.high_carbide_steel_threshold")
        if "high_carbide_steel" in section:
            table = _require_mapping(section["high_carbide_steel"], "state_factors.high_carbide_steel")
            for state, value in table.items():
                if not isinstance(state, str):
                    raise ValueError("Tuning state_factors.high_carbide_steel keys must be strings")
                _require_number(value, f"state_factors.high_carbide_steel.{state}")


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def resolve_tuning(override: Dict[str, Any] | None) -> Dict[str, Any]:
    if override is None:
        return deepcopy(DEFAULT_TUNING)
    validate_tuning_profile(override)
    if not override:
        return deepcopy(DEFAULT_TUNING)
    return _deep_merge(DEFAULT_TUNING, override)


def load_tuning_file(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("Tuning file must be a JSON object")
    validate_tuning_profile(payload)
    return payload
