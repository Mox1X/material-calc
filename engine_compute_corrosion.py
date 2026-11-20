#!/usr/bin/env python3

from typing import Dict, List, Tuple

from alloy_models import ElementData
from engine_types import CorrosionComputation
from physics_carbides import CarbideProfile
from physics_corrosion import corrosion_risk_score, oxide_protection_indicator
from physics_hardness import is_trace_impurity, size_radius_pm, substitution_or_interstitial
from physics_phase_regime import CastIronGraphiteEffect, TiAlIntermetallicEffect, confidence_index, phase_fractions_estimate


def compute_corrosion(
    composition: Dict[str, float],
    db: Dict[str, ElementData],
    base: ElementData,
    material_state: str,
    material_regime: str,
    cast_iron_fx: CastIronGraphiteEffect,
    carbides_local: CarbideProfile,
    ti_al_fx: TiAlIntermetallicEffect,
    deltas: List[Tuple[str, float, str, str]],
    interstitial_c: float,
    env: str,
    temperature_k: float,
    oxygen_activity: float,
) -> CorrosionComputation:
    noble_like_alloy = all((db[s].electronegativity >= 1.9) or (db[s].standard_potential_v >= 0.3) for s in composition)

    dchi_w = 0.0
    brittle_phase_risk = 0.0
    brittleness = 0.0
    for sym, c in composition.items():
        if sym == base.symbol:
            continue
        el = db[sym]
        dchi = abs(base.electronegativity - db[sym].electronegativity)
        dchi_w += c * dchi
        if dchi > 0.4 and not noble_like_alloy:
            brittle_phase_risk += c
            brittleness += 0.4 * c
        mode = substitution_or_interstitial(size_radius_pm(el), size_radius_pm(base))
        if mode == "interstitial":
            if base.symbol == "Ti" and sym == "O" and c <= 0.005:
                brittleness += 0.05 * c
            else:
                brittleness += 0.6 * c
                if c > 0.03:
                    brittleness += min(0.5, (c - 0.03) * 5.0)
        delta_pct = abs(size_radius_pm(base) - size_radius_pm(el)) / size_radius_pm(base) * 100.0
        if delta_pct > 15.0:
            excess = min(1.0, (delta_pct - 15.0) / 20.0)
            brittleness += c * (0.5 + 0.5 * excess)

    p_frac = composition.get("P", 0.0)
    if p_frac > 0.0005:
        brittleness *= 1.5
    s_frac = composition.get("S", 0.0)
    mn_frac = composition.get("Mn", 0.0)
    hot_shortness_risk = 0.0
    if s_frac > 0.0:
        mn_guard = mn_frac >= s_frac * 5.0
        if not mn_guard:
            hot_shortness_risk = min(1.0, (s_frac * 800.0) * (1.5 if material_state == "quenched" else 1.0))
            brittleness += 0.25 * hot_shortness_risk

    brittleness = min(1.0, brittleness)
    brittleness = min(1.0, brittleness + carbides_local["brittleness_add"])
    brittleness = min(1.0, brittleness + ti_al_fx["brittleness_add"] + cast_iron_fx["brittleness_add"])

    ep_spread, corrosion_score, passivation_multiplier, effective_cr_percent, ti_passivation_multiplier, halogen_pitting_risk = corrosion_risk_score(
        composition,
        db,
        env=env,
        temperature_k=temperature_k,
        oxygen_activity=oxygen_activity,
    )
    oxide_tendency = oxide_protection_indicator(base, composition, db)
    if composition.get("Cr", 0.0) >= 0.12:
        oxide_tendency = max(oxide_tendency, 0.8)
    free_cr = max(0.0, composition.get("Cr", 0.0) - carbides_local["chromium_tied_fraction"])
    if composition.get("Cr", 0.0) >= 0.12 and free_cr < 0.12:
        oxide_tendency = min(oxide_tendency, 0.45)
        corrosion_score = min(1.0, corrosion_score * 1.35)
    corrosion_score *= max(0.2, 1.0 - 0.75 * oxide_tendency)
    corrosion_score = min(1.0, corrosion_score)

    phase_fracs = phase_fractions_estimate(material_regime, composition, carbides_local, cast_iron_fx, ti_al_fx)
    conf = confidence_index(composition, db, material_regime)

    limited = sum(1 for _, _, cl, _ in deltas if cl == "limited")
    incompatible = 0
    for sym, _, cl, mode in deltas:
        if cl not in {"incompatible"}:
            continue
        if mode == "interstitial" and composition[sym] <= 0.03:
            continue
        if is_trace_impurity(sym, composition[sym]):
            continue
        incompatible += 1

    if incompatible > 0:
        overall = "phase_separation_or_intermetallic_likely"
    elif limited > 0:
        overall = "limited_solid_solution"
    else:
        overall = "good_solid_solution"
    if ti_al_fx["active"] > 0.5 and ti_al_fx["stoich_closeness"] > 0.5:
        overall = "intermetallic_dominant"

    substitutional_incompatible = sum(
        1
        for sym, _, cl, mode in deltas
        if cl == "incompatible" and mode == "substitutional" and not is_trace_impurity(sym, composition[sym])
    )
    if substitutional_incompatible > 0:
        sub_compat = "limited_or_phase_split"
    elif limited > 0:
        sub_compat = "limited"
    else:
        sub_compat = "good"

    interstitial_mode = "neutral"
    if interstitial_c >= 0.015:
        interstitial_mode = "strong_hardening"
    elif interstitial_c >= 0.004:
        interstitial_mode = "moderate_hardening"

    if brittleness > 0.55:
        phase_instability = "high"
    elif brittleness > 0.25 or brittle_phase_risk > 0.1:
        phase_instability = "medium"
    else:
        phase_instability = "low"

    return CorrosionComputation(
        dchi_w=dchi_w,
        brittle_phase_risk=brittle_phase_risk,
        brittleness=brittleness,
        sub_compat=sub_compat,
        interstitial_mode=interstitial_mode,
        phase_instability=phase_instability,
        overall=overall,
        phase_fractions=phase_fracs,
        confidence_index=conf,
        ep_spread=ep_spread,
        corrosion_score=corrosion_score,
        passivation_multiplier=passivation_multiplier,
        effective_cr_percent=effective_cr_percent,
        ti_passivation_multiplier=ti_passivation_multiplier,
        halogen_pitting_risk=halogen_pitting_risk,
        oxide_tendency=oxide_tendency,
        free_cr=free_cr,
        p_frac=p_frac,
        s_frac=s_frac,
        mn_frac=mn_frac,
        hot_shortness_risk=hot_shortness_risk,
    )
