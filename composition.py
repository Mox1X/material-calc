#!/usr/bin/env python3

import math
from typing import Dict

from alloy_validation import normalize_composition


def parse_composition(raw: str) -> Dict[str, float]:
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        raise ValueError("Empty composition. Example: Fe:0.7,Cr:0.2,C:0.1")

    comp: Dict[str, float] = {}
    for part in parts:
        if ":" not in part:
            raise ValueError(f"Bad token '{part}'. Use Symbol:fraction")
        sym, frac = part.split(":", 1)
        sym = sym.strip()
        frac = frac.strip()
        if not sym:
            raise ValueError(f"Bad token '{part}'. Symbol cannot be empty")
        if not frac:
            raise ValueError(f"Bad token '{part}'. Fraction cannot be empty")
        try:
            value = float(frac)
        except ValueError as exc:
            raise ValueError(f"Bad token '{part}'. Fraction must be numeric") from exc
        if not math.isfinite(value):
            raise ValueError(f"Fraction must be finite for {sym}")
        if value <= 0:
            raise ValueError(f"Fraction must be > 0 for {sym}")
        comp[sym] = comp.get(sym, 0.0) + value

    return normalize_composition(comp)
