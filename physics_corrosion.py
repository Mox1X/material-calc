#!/usr/bin/env python3

from typing import Dict, Tuple

from alloy_models import ElementData
from config.tuning_defaults import CORROSION_ENV_FACTOR, CORROSION_PARAMS, HALOGEN_ENV_FACTOR, HALOGEN_SYMBOLS


def corrosion_risk_score(
    composition: Dict[str, float],
    db: Dict[str, ElementData],
    env: str,
    temperature_k: float,
    oxygen_activity: float,
) -> Tuple[float, float, float, float, float, float]:
    vals = [db[s].standard_potential_v for s in composition]
    spread = max(vals) - min(vals)
    galvanic = min(1.0, spread / CORROSION_PARAMS["spread_norm_v"])
    e0_avg = sum(composition[s] * db[s].standard_potential_v for s in composition)
    intrinsic = min(1.0, max(0.0, (-e0_avg) / CORROSION_PARAMS["intrinsic_norm_v"]))
    score = min(1.0, CORROSION_PARAMS["galvanic_weight"] * galvanic + CORROSION_PARAMS["intrinsic_weight"] * intrinsic)

    passivation_multiplier = 1.0
    effective_cr_percent = 0.0
    if composition.get("Fe", 0.0) > 0.0:
        cr_percent = composition.get("Cr", 0.0) * 100.0
        c_percent = composition.get("C", 0.0) * 100.0
        effective_cr_percent = max(0.0, cr_percent - (CORROSION_PARAMS["cr_carbide_tie_coeff"] * c_percent))
        if effective_cr_percent > CORROSION_PARAMS["effective_cr_threshold"] and c_percent <= CORROSION_PARAMS["low_c_threshold"]:
            passivation_multiplier = CORROSION_PARAMS["passivation_low"]
        elif effective_cr_percent > CORROSION_PARAMS["effective_cr_threshold"] and c_percent <= CORROSION_PARAMS["mid_c_threshold"]:
            passivation_multiplier = CORROSION_PARAMS["passivation_mid"]

    ti_passivation_multiplier = 1.0
    if composition.get("Ti", 0.0) >= 0.5:
        ti_passivation_multiplier = CORROSION_PARAMS["ti_passivation"]
        if composition.get("O", 0.0) <= CORROSION_PARAMS["ti_oxygen_threshold"]:
            ti_passivation_multiplier *= CORROSION_PARAMS["ti_oxygen_multiplier"]
        if composition.get("Pd", 0.0) >= CORROSION_PARAMS["ti_pd_threshold"]:
            ti_passivation_multiplier *= CORROSION_PARAMS["ti_pd_multiplier"]

    al_passivation_multiplier = 1.0
    if composition.get("Al", 0.0) >= 0.5:
        al_passivation_multiplier = CORROSION_PARAMS["al_passivation"]
        if composition.get("Mg", 0.0) + composition.get("Si", 0.0) > CORROSION_PARAMS["al_mgsi_threshold"]:
            al_passivation_multiplier *= CORROSION_PARAMS["al_mgsi_multiplier"]

    symbols = list(composition.keys())
    if symbols:
        noble_like = all((db[s].electronegativity >= 1.9) or (db[s].standard_potential_v >= 0.3) for s in symbols)
        if noble_like:
            score *= CORROSION_PARAMS["noble_like_multiplier"]

    combined = passivation_multiplier * ti_passivation_multiplier * al_passivation_multiplier
    env_factor = CORROSION_ENV_FACTOR.get(env, 1.0)
    temp_factor = min(
        CORROSION_PARAMS["temp_factor_max"],
        max(CORROSION_PARAMS["temp_factor_min"], (temperature_k / 298.15) ** CORROSION_PARAMS["temp_factor_exp"]),
    )
    if env == "vacuum":
        oxy_factor = min(CORROSION_PARAMS["vacuum_oxygen_max"], max(0.0, oxygen_activity))
    else:
        oxy_factor = min(
            CORROSION_PARAMS["other_oxygen_max"],
            max(CORROSION_PARAMS["other_oxygen_min"], CORROSION_PARAMS["other_oxygen_offset"] + oxygen_activity),
        )
    score = min(1.0, score * combined * env_factor * temp_factor * oxy_factor)

    halogen_frac = sum(composition.get(sym, 0.0) for sym in HALOGEN_SYMBOLS)
    halogen_env = HALOGEN_ENV_FACTOR.get(env, 1.0)
    halogen_pitting_risk = (
        min(1.0, (CORROSION_PARAMS["halogen_base"] + CORROSION_PARAMS["halogen_coeff"] * halogen_frac) * halogen_env)
        if halogen_frac > 0
        else 0.0
    )
    score = min(1.0, max(score, halogen_pitting_risk))
    return spread, score, combined, effective_cr_percent, ti_passivation_multiplier, halogen_pitting_risk


def oxide_protection_indicator(base: ElementData, composition: Dict[str, float], db: Dict[str, ElementData]) -> float:
    gain = 0.0
    for sym, c in composition.items():
        if sym == base.symbol:
            continue
        if db[sym].oxide_energy_kj_mol < base.oxide_energy_kj_mol:
            gain += c
    return min(1.0, gain)
