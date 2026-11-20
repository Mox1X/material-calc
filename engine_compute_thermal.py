#!/usr/bin/env python3

from typing import Any, Dict, List, Tuple

from alloy_models import ElementData
from config.tuning_defaults import LOW_MELT_SET
from engine_types import ThermalComputation
from physics_hardness import affinity_factor, is_trace_impurity


def compute_thermal(
    composition: Dict[str, float],
    db: Dict[str, ElementData],
    base: ElementData,
    material_regime: str,
    deltas: List[Tuple[str, float, str, str]],
    interstitial_c: float,
    sub_weighted_delta: float,
    weighted_tm: float,
    weighted_quality: float,
    resolved_tuning: Dict[str, Any],
) -> ThermalComputation:
    aff_base = affinity_factor(base, composition, db, deltas)
    n_comp = sum(1 for s, c in composition.items() if c >= 0.001 and not is_trace_impurity(s, c))
    n_comp = max(2, n_comp)
    complexity_bonus = max(0.0, (n_comp - 2) * 0.08)
    aff = min(0.38, aff_base + complexity_bonus)
    if set(composition.keys()).issubset(LOW_MELT_SET):
        aff *= 0.45

    tm_delta_mix_weight = min(1.0, max(0.0, float(resolved_tuning["thermal"]["delta_to_base_weight"])))
    tm_quality_pull = min(1.0, max(0.0, float(resolved_tuning["thermal"]["quality_pull_to_base"])))
    weighted_tm_mixed = (1.0 - tm_delta_mix_weight) * weighted_tm + tm_delta_mix_weight * base.melting_point_k
    tm_low_quality_factor = tm_quality_pull * (1.0 - weighted_quality)
    tm_stable = (1.0 - tm_low_quality_factor) * weighted_tm_mixed + tm_low_quality_factor * base.melting_point_k

    thermal_cfg = resolved_tuning["thermal"]
    regime_cfg = thermal_cfg.get("regime_overrides", {}).get(material_regime, {})
    aff_strength = min(1.0, max(0.0, float(regime_cfg.get("affinity_penalty_strength", thermal_cfg["affinity_penalty_strength"]))))
    soft_aff_strength = min(
        1.0,
        max(0.0, float(regime_cfg.get("affinity_soft_penalty_strength", thermal_cfg["affinity_soft_penalty_strength"]))),
    )
    min_tm_fraction = min(1.0, max(0.5, float(regime_cfg.get("min_tm_fraction", thermal_cfg["min_tm_fraction"]))))

    dchi_w = 0.0
    for sym, c in composition.items():
        if sym == base.symbol:
            continue
        dchi_w += c * abs(base.electronegativity - db[sym].electronegativity)

    if dchi_w < 0.2 and sub_weighted_delta < 8.0 and interstitial_c < 0.01:
        t_melt = tm_stable * (1.0 - soft_aff_strength * aff)
    else:
        t_melt = tm_stable * (1.0 - aff_strength * aff)
    t_melt = max(t_melt, tm_stable * min_tm_fraction)
    return ThermalComputation(eutectic_affinity=aff, estimated_melting_point_k=t_melt)
