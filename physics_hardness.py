#!/usr/bin/env python3

import math
from typing import Dict, List, Tuple

from alloy_models import ElementData
from config.tuning_defaults import (
    AFFINITY_PARAMS,
    AL_PRECIPITATION_PARAMS,
    MG_ALLOY_PARAMS,
    NICKEL_SUPERALLOY_PARAMS,
    PURE_HV_FLOORS,
    REFRACTORY_COMPOSITE_PARAMS,
    SIZE_CLASS_LIMITS,
    SIZE_RADIUS_OVERRIDES_PM,
    SOLUTE_STRENGTH_EFFICIENCY,
    TITANIUM_ALPHA_BETA_PARAMS,
    TRACE_IMPURITY_SYMBOLS,
)


def estimate_hv_from_shear(shear_gpa: float) -> float:
    return 1.2 * shear_gpa


def size_radius_pm(el: ElementData) -> float:
    return SIZE_RADIUS_OVERRIDES_PM.get(el.symbol, el.atomic_radius_pm)


def lattice_hardening_factor(crystal_structure: str) -> float:
    cs = (crystal_structure or "").upper()
    if cs in {"HCP", "HEX"}:
        return 2.5
    if cs in {"FCC"}:
        return 1.25
    return 1.0


def titanium_alpha_beta_bonus(composition: Dict[str, float]) -> float:
    if composition.get("Ti", 0.0) < TITANIUM_ALPHA_BETA_PARAMS["ti_min"]:
        return 1.0
    al = composition.get("Al", 0.0)
    v = composition.get("V", 0.0)
    o = composition.get("O", 0.0)

    bonus = 1.0
    if al >= TITANIUM_ALPHA_BETA_PARAMS["al_v_al_min"] and v >= TITANIUM_ALPHA_BETA_PARAMS["al_v_v_min"]:
        bonus *= TITANIUM_ALPHA_BETA_PARAMS["al_v_multiplier"]
    elif al >= TITANIUM_ALPHA_BETA_PARAMS["al_only_min"]:
        bonus *= TITANIUM_ALPHA_BETA_PARAMS["al_only_multiplier"]
    if TITANIUM_ALPHA_BETA_PARAMS["o_min"] <= o <= TITANIUM_ALPHA_BETA_PARAMS["o_max"]:
        bonus *= TITANIUM_ALPHA_BETA_PARAMS["o_multiplier"]
    return bonus


def pure_hv_floor(symbol: str) -> float:
    return PURE_HV_FLOORS.get(symbol, 0.0)


def al_precipitation_bonus_hv(base_symbol: str, composition: Dict[str, float]) -> float:
    if base_symbol != "Al":
        return 0.0
    cu = composition.get("Cu", 0.0)
    mg = composition.get("Mg", 0.0)
    si = composition.get("Si", 0.0)

    bonus = 0.0
    if cu >= AL_PRECIPITATION_PARAMS["cu_min"] and mg >= AL_PRECIPITATION_PARAMS["mg_for_cu_min"]:
        bonus += AL_PRECIPITATION_PARAMS["cu_mg_bonus"] * min(
            AL_PRECIPITATION_PARAMS["bonus_cap_scale"],
            (cu / AL_PRECIPITATION_PARAMS["cu_scale"]) * (mg / AL_PRECIPITATION_PARAMS["mg_scale"]) ** 0.5,
        )
    if mg >= AL_PRECIPITATION_PARAMS["mg_min"] and si >= AL_PRECIPITATION_PARAMS["si_min"]:
        bonus += AL_PRECIPITATION_PARAMS["mg_si_bonus"] * min(
            AL_PRECIPITATION_PARAMS["bonus_cap_scale"],
            (mg / AL_PRECIPITATION_PARAMS["mg_scale"]) * (si / AL_PRECIPITATION_PARAMS["si_scale"]) ** 0.5,
        )
    return bonus


def mg_alloy_bonus_hv(base_symbol: str, composition: Dict[str, float]) -> float:
    if base_symbol != "Mg":
        return 0.0
    al = composition.get("Al", 0.0)
    zn = composition.get("Zn", 0.0)
    mn = composition.get("Mn", 0.0)
    bonus = 0.0
    if al >= MG_ALLOY_PARAMS["al_min"] and zn >= MG_ALLOY_PARAMS["zn_min"]:
        bonus += MG_ALLOY_PARAMS["al_zn_bonus"] * min(
            MG_ALLOY_PARAMS["bonus_cap_scale"],
            (al / MG_ALLOY_PARAMS["al_scale"]) * (zn / MG_ALLOY_PARAMS["zn_scale"]) ** 0.5,
        )
    if mn >= MG_ALLOY_PARAMS["mn_min"]:
        bonus += MG_ALLOY_PARAMS["mn_flat_bonus"]
    return bonus


def substitutional_hardening_weight(base_symbol: str, solute_symbol: str) -> float:
    if base_symbol == "Cu":
        if solute_symbol == "Sn":
            return 2.2
        if solute_symbol == "Zn":
            return 0.85
    return 1.0


def solute_strength_efficiency(symbol: str) -> float:
    return SOLUTE_STRENGTH_EFFICIENCY.get(symbol, 1.0)


def refractory_composite_bonus_hv(base_symbol: str, composition: Dict[str, float]) -> float:
    if base_symbol != "W":
        return 0.0
    w = composition.get("W", 0.0)
    binder = composition.get("Co", 0.0) + composition.get("Ni", 0.0)
    if w < REFRACTORY_COMPOSITE_PARAMS["w_min"] or binder < REFRACTORY_COMPOSITE_PARAMS["binder_min"]:
        return 0.0
    return (
        REFRACTORY_COMPOSITE_PARAMS["core_multiplier"]
        * (w ** REFRACTORY_COMPOSITE_PARAMS["w_power"])
        * (binder ** REFRACTORY_COMPOSITE_PARAMS["binder_power"])
    )


def nickel_superalloy_bonus_hv(
    base_symbol: str,
    composition: Dict[str, float],
    al_ti_threshold: float = 0.02,
) -> float:
    if base_symbol != "Ni" or composition.get("Ni", 0.0) < NICKEL_SUPERALLOY_PARAMS["ni_min"]:
        return 0.0
    cr = composition.get("Cr", 0.0)
    al_ti = composition.get("Al", 0.0) + composition.get("Ti", 0.0)
    refractory = composition.get("W", 0.0) + composition.get("Mo", 0.0) + composition.get("Co", 0.0)
    if cr < NICKEL_SUPERALLOY_PARAMS["cr_min"] or al_ti < al_ti_threshold:
        return 0.0
    core = (
        NICKEL_SUPERALLOY_PARAMS["base_bonus"]
        + NICKEL_SUPERALLOY_PARAMS["al_ti_coeff"] * al_ti
        + NICKEL_SUPERALLOY_PARAMS["refractory_coeff"] * min(NICKEL_SUPERALLOY_PARAMS["refractory_cap"], refractory)
    )
    return min(NICKEL_SUPERALLOY_PARAMS["bonus_cap"], core)


def hardness_state_factor(
    material_state: str,
    base_symbol: str,
    composition: Dict[str, float],
    carbides: Dict[str, float],
    high_carbide_threshold: float = 1.0,
    high_carbide_table: Dict[str, float] | None = None,
    carbon_tool_c_min: float = 0.006,
    carbon_tool_max_alloying: float = 0.05,
    carbon_tool_max_strong_alloying: float = 0.08,
    carbon_tool_table: Dict[str, float] | None = None,
    high_speed_c_min: float = 0.006,
    high_speed_formers_min: float = 0.07,
    high_speed_alloy_score_min: float = 0.08,
    high_speed_table: Dict[str, float] | None = None,
) -> float:
    high_carbide = high_carbide_table or {
        "raw": 0.22,
        "tempered": 0.68,
        "quenched": 0.88,
        "potential": 1.0,
        "default": 0.26,
    }
    carbon_tool = carbon_tool_table or {
        "raw": 0.78,
        "tempered": 1.55,
        "quenched": 2.20,
        "potential": 2.50,
        "default": 0.82,
    }
    high_speed = high_speed_table or {
        "raw": 0.32,
        "tempered": 1.28,
        "quenched": 1.38,
        "potential": 1.48,
        "default": 0.45,
    }
    if base_symbol != "Fe":
        return 1.0

    c = composition.get("C", 0.0)
    w = composition.get("W", 0.0)
    mo = composition.get("Mo", 0.0)
    v = composition.get("V", 0.0)
    co = composition.get("Co", 0.0)
    cr = composition.get("Cr", 0.0)
    ni = composition.get("Ni", 0.0)
    total_alloying = max(0.0, 1.0 - composition.get("Fe", 0.0) - c)
    strong_alloying = w + mo + v + cr + ni + co
    hss_formers = w + mo + v
    hss_alloy_score = hss_formers + 0.5 * co

    if c >= high_speed_c_min and hss_formers >= high_speed_formers_min and hss_alloy_score >= high_speed_alloy_score_min:
        return float(high_speed.get(material_state, high_speed.get("default", 0.45)))

    if c >= carbon_tool_c_min and total_alloying <= carbon_tool_max_alloying and strong_alloying <= carbon_tool_max_strong_alloying:
        return float(carbon_tool.get(material_state, carbon_tool.get("default", 0.82)))

    if (
        carbides["active"] > 0.5
        and carbides["cermet_mode"] < 0.5
        and carbides.get("carbide_index", 0.0) >= high_carbide_threshold
    ):
        return float(high_carbide.get(material_state, high_carbide.get("default", 0.26)))
    return 1.0


def classify_size_delta(delta_pct: float) -> str:
    if delta_pct < SIZE_CLASS_LIMITS["excellent_max"]:
        return "excellent"
    if delta_pct < SIZE_CLASS_LIMITS["limited_max"]:
        return "limited"
    return "incompatible"


def substitution_or_interstitial(r_solute: float, r_base: float) -> str:
    ratio = r_solute / r_base
    return "interstitial" if ratio < SIZE_CLASS_LIMITS["interstitial_ratio_max"] else "substitutional"


def is_trace_impurity(symbol: str, fraction: float) -> bool:
    return symbol in TRACE_IMPURITY_SYMBOLS and fraction < 0.001


def affinity_factor(
    base: ElementData,
    composition: Dict[str, float],
    db: Dict[str, ElementData],
    deltas: List[Tuple[str, float, str, str]],
) -> float:
    chi_acc = 0.0
    size_acc = 0.0
    for sym, c in composition.items():
        if sym == base.symbol:
            continue
        dchi = abs(base.electronegativity - db[sym].electronegativity)
        if is_trace_impurity(sym, c):
            dchi *= AFFINITY_PARAMS["trace_multiplier"]
        chi_acc += c * min(dchi / 2.0, 1.0)

    for sym, delta_pct, _, mode in deltas:
        c = composition[sym]
        size_term = min((delta_pct / 100.0) / AFFINITY_PARAMS["size_norm"], 1.0)
        if is_trace_impurity(sym, c):
            size_term *= AFFINITY_PARAMS["trace_multiplier"]
        if mode == "interstitial":
            size_term *= AFFINITY_PARAMS["interstitial_size_multiplier"]
        size_acc += c * size_term

    aff = min(AFFINITY_PARAMS["aff_cap"], AFFINITY_PARAMS["chi_weight"] * chi_acc + AFFINITY_PARAMS["size_weight"] * size_acc)
    symbols = list(composition.keys())
    noble_like = all((db[s].electronegativity >= 1.9) or (db[s].standard_potential_v >= 0.3) for s in symbols)
    if noble_like:
        aff *= AFFINITY_PARAMS["noble_like_multiplier"]
    return aff
