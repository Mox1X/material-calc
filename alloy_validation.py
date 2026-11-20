#!/usr/bin/env python3

from __future__ import annotations

import math
from typing import Dict, Iterable, List, Mapping

ALLOWED_MATERIAL_STATES = frozenset({"raw", "tempered", "quenched", "potential"})
ALLOWED_ENVIRONMENTS = frozenset({"air", "water", "acid", "vacuum"})
ALLOWED_REGIME_OVERRIDES = frozenset({"auto", "steel", "cast_iron", "cermet", "refractory", "nonferrous"})


def _allowed_list(values: Iterable[str]) -> str:
    return ", ".join(sorted(values))


def validate_runtime_context(
    *,
    material_state: str,
    env: str,
    regime_override: str,
    temperature_k: float,
    oxygen_activity: float,
) -> tuple[float, float]:
    if material_state not in ALLOWED_MATERIAL_STATES:
        raise ValueError(
            f"Invalid material_state '{material_state}'. Allowed values: {_allowed_list(ALLOWED_MATERIAL_STATES)}"
        )
    if env not in ALLOWED_ENVIRONMENTS:
        raise ValueError(f"Invalid env '{env}'. Allowed values: {_allowed_list(ALLOWED_ENVIRONMENTS)}")
    if regime_override not in ALLOWED_REGIME_OVERRIDES:
        raise ValueError(
            f"Invalid regime_override '{regime_override}'. Allowed values: {_allowed_list(ALLOWED_REGIME_OVERRIDES)}"
        )

    t = float(temperature_k)
    if not math.isfinite(t):
        raise ValueError("temperature_k must be finite")
    if t < 0.0:
        raise ValueError("temperature_k must be >= 0 K")

    oxy = float(oxygen_activity)
    if not math.isfinite(oxy):
        raise ValueError("oxygen_activity must be finite")
    oxy = min(1.0, max(0.0, oxy))
    return t, oxy


def validate_composition_values(
    composition: Mapping[str, float],
    *,
    empty_message: str = "Composition is empty. Example: Fe:0.7,Cr:0.2,C:0.1",
) -> None:
    if not composition:
        raise ValueError(empty_message)

    for sym, value in composition.items():
        v = float(value)
        if not math.isfinite(v):
            raise ValueError(f"Composition fraction for {sym} must be finite")
        if v <= 0.0:
            raise ValueError(f"Composition fraction for {sym} must be > 0")


def normalize_composition(
    composition: Mapping[str, float],
    *,
    drop_invalid: bool = False,
) -> Dict[str, float]:
    if not composition:
        raise ValueError("Composition must contain at least one element fraction.")

    compact: Dict[str, float] = {}
    total = 0.0
    for sym, raw_value in composition.items():
        key = str(sym)
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            if drop_invalid:
                continue
            raise ValueError(f"Composition fraction for {key} must be numeric")

        if not math.isfinite(value):
            if drop_invalid:
                continue
            raise ValueError(f"Composition fraction for {key} must be finite")
        if value <= 0.0:
            if drop_invalid:
                continue
            raise ValueError(f"Composition fraction for {key} must be > 0")

        compact[key] = compact.get(key, 0.0) + value
        total += value

    if total <= 0.0:
        raise ValueError("Composition must contain at least one positive finite fraction.")

    normalized: Dict[str, float] = {}
    for sym, value in compact.items():
        normalized[sym] = value / total
    return normalized


def ensure_known_symbols(
    composition: Mapping[str, float],
    known_symbols: Mapping[str, object] | Iterable[str],
    *,
    source_name: str = "elements/",
) -> None:
    keys = known_symbols.keys() if isinstance(known_symbols, Mapping) else known_symbols
    known = set(keys)
    missing = sorted(sym for sym in composition if sym not in known)
    if missing:
        raise ValueError(f"Missing symbols in {source_name}: {', '.join(missing)}")


def find_duplicate_symbols(raw: str) -> List[str]:
    seen: Dict[str, int] = {}
    for token in [part.strip() for part in raw.split(",") if part.strip()]:
        if ":" not in token:
            continue
        sym = token.split(":", 1)[0].strip()
        if not sym:
            continue
        seen[sym] = seen.get(sym, 0) + 1
    return sorted([sym for sym, count in seen.items() if count > 1])
