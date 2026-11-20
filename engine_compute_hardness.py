#!/usr/bin/env python3

import math
from typing import Any, Dict, List

from alloy_models import ElementData
from config.tuning_defaults import NOBLE_GASES
from engine_types import DeltaRecord, HardnessComputation
from physics_carbides import CarbideProfile
from physics_hardness import (
    al_precipitation_bonus_hv,
    classify_size_delta,
    estimate_hv_from_shear,
    hardness_state_factor,
    is_trace_impurity,
    lattice_hardening_factor,
    mg_alloy_bonus_hv,
    nickel_superalloy_bonus_hv,
    pure_hv_floor,
    refractory_composite_bonus_hv,
    size_radius_pm,
    solute_strength_efficiency,
    substitution_or_interstitial,
    substitutional_hardening_weight,
    titanium_alpha_beta_bonus,
)
from physics_phase_regime import CastIronGraphiteEffect

CERMET_MONOCARBIDE_C_PER_METAL = {
    "W": 12.011 / 183.84,  # WC
    "Ti": 12.011 / 47.867,  # TiC
    "Ta": 12.011 / 180.94788,  # TaC
    "Nb": 12.011 / 92.90637,  # NbC
}

CERMET_MONOCARBIDE_DENSITY_KG_M3 = {
    "W": 15630.0,  # WC
    "Ti": 4930.0,  # TiC
    "Ta": 14450.0,  # TaC
    "Nb": 7820.0,  # NbC
}


def _estimate_cermet_density_kg_m3(
    composition: Dict[str, float],
    db: Dict[str, ElementData],
    fallback_density_kg_m3: float,
) -> float:
    carbon_available = composition.get("C", 0.0)
    if carbon_available <= 0.0:
        return fallback_density_kg_m3

    carbide_demand: Dict[str, float] = {}
    for symbol, c_per_metal in CERMET_MONOCARBIDE_C_PER_METAL.items():
        metal_fraction = composition.get(symbol, 0.0)
        if metal_fraction > 0.0:
            carbide_demand[symbol] = metal_fraction * c_per_metal
    total_carbon_demand = sum(carbide_demand.values())
    if total_carbon_demand <= 0.0:
        return fallback_density_kg_m3

    carbon_scale = min(1.0, carbon_available / total_carbon_demand)

    phase_masses: List[tuple[float, float]] = []
    used_carbon = 0.0
    for symbol, demand in carbide_demand.items():
        metal_fraction = composition[symbol]
        carbon_used = demand * carbon_scale
        used_carbon += carbon_used
        phase_mass = metal_fraction + carbon_used
        phase_density = CERMET_MONOCARBIDE_DENSITY_KG_M3[symbol]
        phase_masses.append((phase_mass, phase_density))

    binder_fraction = composition.get("Co", 0.0) + composition.get("Ni", 0.0)
    if binder_fraction > 0.0:
        binder_density = 0.0
        if composition.get("Co", 0.0) > 0.0:
            binder_density += composition["Co"] * db["Co"].density_solid_kg_m3
        if composition.get("Ni", 0.0) > 0.0:
            binder_density += composition["Ni"] * db["Ni"].density_solid_kg_m3
        binder_density = binder_density / binder_fraction if binder_density > 0.0 else 8900.0
        phase_masses.append((binder_fraction, binder_density))

    modeled_mass = sum(mass for mass, _ in phase_masses)
    if modeled_mass < 1.0:
        phase_masses.append((1.0 - modeled_mass, fallback_density_kg_m3))

    inv_density = 0.0
    for phase_mass, phase_density in phase_masses:
        if phase_density > 0.0 and phase_mass > 0.0:
            inv_density += phase_mass / phase_density
    if inv_density <= 0.0:
        return fallback_density_kg_m3
    return 1.0 / inv_density


def compute_hardness(
    composition: Dict[str, float],
    db: Dict[str, ElementData],
    base: ElementData,
    base_symbol: str,
    material_state: str,
    cast_iron_fx: CastIronGraphiteEffect,
    carbides_local: CarbideProfile,
    cermet_active: bool,
    k_hardening: float,
    resolved_tuning: Dict[str, Any],
    temperature_k: float,
) -> HardnessComputation:
    component_hv = 0.0
    weighted_tm = 0.0
    weighted_shear = 0.0
    weighted_neutron = 0.0
    weighted_density = 0.0
    weighted_quality = 0.0
    volatile_fraction = 0.0
    noble_gas_fraction = 0.0
    deltas: List[DeltaRecord] = []

    base_hv = estimate_hv_from_shear(base.shear_gpa)
    for sym, c in composition.items():
        el = db[sym]
        el_hv = estimate_hv_from_shear(el.shear_gpa)
        component_hv += c * el_hv
        weighted_tm += c * el.melting_point_k
        weighted_shear += c * el.shear_gpa
        weighted_neutron += c * el.neutron_cross_section_barn
        weighted_density += c * el.density_solid_kg_m3
        weighted_quality += c * el.data_quality_score_0_1
        if el.melting_point_k <= temperature_k:
            volatile_fraction += c
        if sym in NOBLE_GASES:
            noble_gas_fraction += c
        if sym == base_symbol:
            continue
        base_r = size_radius_pm(base)
        sol_r = size_radius_pm(el)
        delta = abs(base_r - sol_r) / base_r * 100.0
        size_class = classify_size_delta(delta)
        mode = substitution_or_interstitial(sol_r, base_r)
        if is_trace_impurity(sym, c):
            size_class = "trace_impurity"
        if base.symbol == "Ti" and sym == "O" and c <= 0.005:
            size_class = "alpha_stabilizing_interstitial"
        deltas.append(DeltaRecord(sym, delta, size_class, mode))

    if cermet_active:
        weighted_density = _estimate_cermet_density_kg_m3(composition, db, weighted_density)

    interstitial_c = 0.0
    substitutional_c = 0.0
    substitutional_effective_c = 0.0
    distortion_boost = 0.0
    interstitial_effective_c = 0.0
    strengthening_power = 0.0
    for delta_item in deltas:
        sym = delta_item.symbol
        c = composition[sym]
        delta_pct = delta_item.delta_percent
        delta = delta_pct / 100.0
        distortion_boost += delta * c
        strengthening_power += c * solute_strength_efficiency(sym) * (1.0 + delta_pct / 10.0)
        if delta_item.solution_mode == "interstitial":
            interstitial_c += c
            weight = 1.0
            if base.symbol == "Ti" and sym == "O" and c <= 0.005:
                weight = 3.0
            elif sym in {"C", "N", "B", "O"}:
                weight = 1.4
            interstitial_effective_c += c * weight
        else:
            substitutional_c += c
            substitutional_effective_c += c * substitutional_hardening_weight(base.symbol, sym)

    interstitial_term = 6.0 * (1.0 - math.exp(-25.0 * interstitial_effective_c))
    sub_weighted_delta = 0.0
    if substitutional_c > 0:
        for delta_item in deltas:
            if delta_item.solution_mode == "substitutional":
                sub_weighted_delta += composition[delta_item.symbol] * delta_item.delta_percent
        sub_weighted_delta = sub_weighted_delta / substitutional_c
    substitutional_term = 1.2 * (max(substitutional_effective_c, 0.0) ** 0.5) * (1.0 + sub_weighted_delta / 10.0)

    hv_solution = (
        base.shear_gpa
        * lattice_hardening_factor(base.crystal_structure)
        * (interstitial_term + substitutional_term + 1.2 * distortion_boost)
        * (1.0 + 1.5 * strengthening_power)
    )
    ti_bonus = titanium_alpha_beta_bonus(composition)
    hv_solution *= ti_bonus

    precip_bonus = al_precipitation_bonus_hv(base_symbol, composition)
    mg_bonus = mg_alloy_bonus_hv(base_symbol, composition)
    refractory_bonus = refractory_composite_bonus_hv(base_symbol, composition)
    if cermet_active:
        refractory_bonus = 0.0
    superalloy_bonus = nickel_superalloy_bonus_hv(
        base_symbol,
        composition,
        al_ti_threshold=float(resolved_tuning["hardness"]["superalloy_al_ti_threshold"]),
    )
    carbide_hv_bonus = carbides_local["hardness_bonus_hv"]
    if cast_iron_fx["active"] > 0.5:
        carbide_hv_bonus *= 0.35

    hv_delta_mix_weight = min(1.0, max(0.0, float(resolved_tuning["hardness"]["delta_to_base_weight"])))
    hv_quality_pull = min(1.0, max(0.0, float(resolved_tuning["hardness"]["quality_pull_to_base"])))
    component_hv_mixed = (1.0 - hv_delta_mix_weight) * component_hv + hv_delta_mix_weight * base_hv
    hv_low_quality_factor = hv_quality_pull * (1.0 - weighted_quality)
    component_hv_stable = (1.0 - hv_low_quality_factor) * component_hv_mixed + hv_low_quality_factor * base_hv

    raw_hv = component_hv_stable + k_hardening * hv_solution + precip_bonus + mg_bonus + refractory_bonus + superalloy_bonus + carbide_hv_bonus
    state_cfg = resolved_tuning["state_factors"]
    state_factor = hardness_state_factor(
        material_state,
        base_symbol,
        composition,
        carbides_local,
        high_carbide_threshold=float(state_cfg["high_carbide_steel_threshold"]),
        high_carbide_table=state_cfg.get("high_carbide_steel"),
        carbon_tool_c_min=float(state_cfg.get("carbon_tool_steel_c_min", 0.006)),
        carbon_tool_max_alloying=float(state_cfg.get("carbon_tool_steel_max_alloying", 0.05)),
        carbon_tool_max_strong_alloying=float(state_cfg.get("carbon_tool_steel_max_strong_alloying", 0.08)),
        carbon_tool_table=state_cfg.get("carbon_tool_steel"),
        high_speed_c_min=float(state_cfg.get("high_speed_steel_c_min", 0.006)),
        high_speed_formers_min=float(state_cfg.get("high_speed_steel_formers_min", 0.07)),
        high_speed_alloy_score_min=float(state_cfg.get("high_speed_steel_alloy_score_min", 0.08)),
        high_speed_table=state_cfg.get("high_speed_steel"),
    )
    raw_hv *= state_factor

    hv_floor = pure_hv_floor(base_symbol)
    hv_cap = 1900.0 if cermet_active else 1800.0
    hv_alloy = hv_cap * math.tanh(max(raw_hv, hv_floor) / hv_cap)
    if cermet_active:
        binder = composition.get("Co", 0.0) + composition.get("Ni", 0.0)
        hv_alloy *= max(0.75, 1.0 - 0.9 * binder)
    if cast_iron_fx["active"] > 0.5:
        hv_alloy *= cast_iron_fx["hv_multiplier"]
    hv_alloy = max(hv_alloy, hv_floor)

    return HardnessComputation(
        weighted_tm=weighted_tm,
        weighted_shear=weighted_shear,
        weighted_neutron=weighted_neutron,
        weighted_density=weighted_density,
        weighted_quality=weighted_quality,
        volatile_fraction=volatile_fraction,
        noble_gas_fraction=noble_gas_fraction,
        deltas=deltas,
        interstitial_c=interstitial_c,
        substitutional_c=substitutional_c,
        interstitial_term=interstitial_term,
        substitutional_term=substitutional_term,
        sub_weighted_delta=sub_weighted_delta,
        ti_bonus=ti_bonus,
        precip_bonus=precip_bonus,
        mg_bonus=mg_bonus,
        refractory_bonus=refractory_bonus,
        superalloy_bonus=superalloy_bonus,
        carbide_hv_bonus=carbide_hv_bonus,
        state_factor=state_factor,
        raw_hv=raw_hv,
        hv_cap=hv_cap,
        hv_alloy=hv_alloy,
    )
