#!/usr/bin/env python3

from typing import Dict, TypedDict

from alloy_models import ElementData
from config.tuning_defaults import CAST_IRON_PARAMS, REFRACTORY_BASES, UNSTABLE_SET
from physics_carbides import CarbideProfile


class TiAlIntermetallicEffect(TypedDict):
    active: float
    brittleness_add: float
    stoich_closeness: float


class CastIronGraphiteEffect(TypedDict):
    active: float
    graphite_index: float
    hv_multiplier: float
    brittleness_add: float
    castability_bonus: float


def ti_al_intermetallic_effect(composition: Dict[str, float]) -> TiAlIntermetallicEffect:
    ti = composition.get("Ti", 0.0)
    al = composition.get("Al", 0.0)
    total = ti + al
    if total < 0.35:
        return {"active": 0.0, "brittleness_add": 0.0, "stoich_closeness": 0.0}
    frac_ti = ti / total if total > 0 else 0.0
    closeness = max(0.0, 1.0 - abs(frac_ti - 0.5) / 0.35)
    active = 1.0 if ti >= 0.25 and al >= 0.20 else 0.0
    brittleness_add = active * (0.2 + 0.55 * closeness)
    return {"active": active, "brittleness_add": brittleness_add, "stoich_closeness": closeness}


def cast_iron_graphite_effect(base_symbol: str, composition: Dict[str, float]) -> CastIronGraphiteEffect:
    if base_symbol != "Fe":
        return {"active": 0.0, "graphite_index": 0.0, "hv_multiplier": 1.0, "brittleness_add": 0.0, "castability_bonus": 0.0}
    c = composition.get("C", 0.0)
    if c <= CAST_IRON_PARAMS["c_min"]:
        return {"active": 0.0, "graphite_index": 0.0, "hv_multiplier": 1.0, "brittleness_add": 0.0, "castability_bonus": 0.0}
    excess = max(0.0, c - CAST_IRON_PARAMS["c_min"])
    si = composition.get("Si", 0.0)
    p = composition.get("P", 0.0)
    s = composition.get("S", 0.0)
    graphitizers = max(0.0, min(CAST_IRON_PARAMS["graphitizer_cap"], si + 0.5 * p - 0.6 * s))
    graphite_index = min(
        1.0,
        excess / CAST_IRON_PARAMS["graphite_base_excess_div"] + CAST_IRON_PARAMS["graphite_graphitizer_coeff"] * graphitizers,
    )
    hv_multiplier = max(
        CAST_IRON_PARAMS["hv_multiplier_min"],
        CAST_IRON_PARAMS["hv_multiplier_base"] - CAST_IRON_PARAMS["hv_multiplier_graphite_coeff"] * graphite_index,
    )
    brittleness_add = CAST_IRON_PARAMS["brittleness_base"] + CAST_IRON_PARAMS["brittleness_graphite_coeff"] * graphite_index
    castability_bonus = CAST_IRON_PARAMS["castability_base"] + CAST_IRON_PARAMS["castability_graphite_coeff"] * graphite_index
    return {
        "active": 1.0,
        "graphite_index": graphite_index,
        "hv_multiplier": hv_multiplier,
        "brittleness_add": brittleness_add,
        "castability_bonus": castability_bonus,
    }


def detect_material_regime(
    base_symbol: str,
    composition: Dict[str, float],
    carbides: CarbideProfile,
    cast_iron_fx: CastIronGraphiteEffect,
) -> str:
    if cast_iron_fx["active"] > 0.5:
        return "cast_iron"
    if carbides["cermet_mode"] > 0.5:
        return "cermet"
    if base_symbol == "Fe":
        return "steel"
    if base_symbol in REFRACTORY_BASES and composition.get(base_symbol, 0.0) > 0.5:
        return "refractory"
    return "nonferrous"


def phase_fractions_estimate(
    regime: str,
    composition: Dict[str, float],
    carbides: CarbideProfile,
    cast_iron_fx: CastIronGraphiteEffect,
    ti_al_fx: TiAlIntermetallicEffect,
) -> Dict[str, float]:
    c = composition.get("C", 0.0)
    ni = composition.get("Ni", 0.0)
    cr = composition.get("Cr", 0.0)
    mn = composition.get("Mn", 0.0)
    ferrite = 0.0
    austenite = 0.0
    carbide = 0.0
    graphite = 0.0
    intermetallic = 0.0
    binder = 0.0

    if regime == "cermet" and carbides.get("cermet_mode", 0.0) > 0.5 and carbides.get("active", 0.0) > 0.5:
        binder = min(0.35, composition.get("Co", 0.0) + composition.get("Ni", 0.0))
        carbide = max(0.0, 1.0 - binder)
    elif regime == "cast_iron" and cast_iron_fx.get("active", 0.0) > 0.5:
        graphite = 0.08 + 0.35 * cast_iron_fx["graphite_index"]
        carbide = 0.05 + 0.15 * (1.0 - cast_iron_fx["graphite_index"])
        ferrite = max(0.0, 1.0 - graphite - carbide)
    elif regime == "steel":
        carbide = min(0.35, max(0.0, c * (5.0 + 8.0 * (composition.get("V", 0.0) + composition.get("W", 0.0) + composition.get("Mo", 0.0) + cr))))
        austenite = min(0.85, max(0.0, 0.15 + 1.8 * ni + 0.8 * mn + 0.4 * c - 0.7 * cr))
        ferrite = max(0.0, 1.0 - austenite - carbide)
    else:
        intermetallic = min(0.85, ti_al_fx["active"] * (0.25 + 0.55 * ti_al_fx["stoich_closeness"]))
        carbide = min(0.25, carbides["effective_carbide_fraction"] * 1.5)
        ferrite = max(0.0, 1.0 - intermetallic - carbide)

    total = ferrite + austenite + carbide + graphite + intermetallic + binder
    if total <= 0:
        return {
            "ferrite_matrix_fraction": 0.0,
            "austenite_fraction": 0.0,
            "carbide_fraction": 0.0,
            "graphite_fraction": 0.0,
            "intermetallic_fraction": 0.0,
            "binder_fraction": 0.0,
        }
    scale = 1.0 / total
    return {
        "ferrite_matrix_fraction": ferrite * scale,
        "austenite_fraction": austenite * scale,
        "carbide_fraction": carbide * scale,
        "graphite_fraction": graphite * scale,
        "intermetallic_fraction": intermetallic * scale,
        "binder_fraction": binder * scale,
    }


def confidence_index(composition: Dict[str, float], db: Dict[str, ElementData], regime: str) -> float:
    base_weighted_quality = sum(composition[s] * db[s].data_quality_score_0_1 for s in composition)
    complexity = max(0.0, (len(composition) - 3) * 0.035)
    unstable_penalty = sum(composition.get(s, 0.0) for s in UNSTABLE_SET) * 0.9
    regime_penalty = 0.12 if regime in {"cermet", "cast_iron"} else 0.0
    conf = base_weighted_quality - complexity - unstable_penalty - regime_penalty
    return max(0.05, min(0.99, conf))
