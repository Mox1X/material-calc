#!/usr/bin/env python3

from typing import Dict, List

from alloy_models import ElementData
from engine_types import CorrosionComputation, HardnessComputation
from physics_carbides import CarbideProfile
from physics_phase_regime import CastIronGraphiteEffect, TiAlIntermetallicEffect
from report_types import EmpiricalReport


def build_empirical_report(
    composition: Dict[str, float],
    base: ElementData,
    base_symbol: str,
    material_state: str,
    material_regime: str,
    hardness: HardnessComputation,
    corrosion: CorrosionComputation,
    carbides_local: CarbideProfile,
    ti_al_fx: TiAlIntermetallicEffect,
    cast_iron_fx: CastIronGraphiteEffect,
    estimated_melting_point_k: float,
    eutectic_affinity: float,
    env: str,
    temperature_k: float,
    oxygen_activity: float,
    feasibility: float,
    input_validity_warnings: List[str],
) -> EmpiricalReport:
    return {
        "base_element": {"symbol": base.symbol, "name": base.name, "fraction": round(composition[base_symbol], 6)},
        "composition_normalized": {k: round(v, 6) for k, v in composition.items()},
        "hume_rothery": {
            "size_factor_checks": [
                {
                    "solute_symbol": d.symbol,
                    "delta_percent": round(d.delta_percent, 3),
                    "classification": d.classification,
                    "solution_mode": d.solution_mode,
                }
                for d in hardness.deltas
            ],
            "electronegativity_weighted_delta": round(corrosion.dchi_w, 4),
            "brittle_phase_risk_index_0_1": round(min(1.0, corrosion.brittle_phase_risk), 4),
            "brittleness_index_0_1": round(corrosion.brittleness, 4),
            "substitutional_compatibility": corrosion.sub_compat,
            "interstitial_hardening_regime": corrosion.interstitial_mode,
            "phase_instability_risk": corrosion.phase_instability,
            "overall_compatibility": corrosion.overall,
        },
        "predicted_properties": {
            "vickers_hardness_hv": round(hardness.hv_alloy, 2),
            "hardening_interstitial_fraction": round(hardness.interstitial_c, 4),
            "hardening_substitutional_fraction": round(hardness.substitutional_c, 4),
            "hardening_interstitial_term": round(hardness.interstitial_term, 4),
            "hardening_substitutional_term": round(hardness.substitutional_term, 4),
            "titanium_alpha_beta_bonus": round(hardness.ti_bonus, 4),
            "precipitation_bonus_hv": round(hardness.precip_bonus, 4),
            "mg_alloy_bonus_hv": round(hardness.mg_bonus, 4),
            "refractory_composite_bonus_hv": round(hardness.refractory_bonus, 4),
            "nickel_superalloy_bonus_hv": round(hardness.superalloy_bonus, 4),
            "carbide_bonus_hv": round(hardness.carbide_hv_bonus, 4),
            "carbide_bonus_hv_effective": round(hardness.carbide_hv_bonus, 4),
            "carbide_bonus_hv_raw": round(carbides_local["hardness_bonus_hv"], 4),
            "carbide_index": round(carbides_local["carbide_index"], 4),
            "effective_carbide_fraction": round(carbides_local["effective_carbide_fraction"], 4),
            "carbide_cermet_mode": bool(carbides_local["cermet_mode"] > 0.5),
            "intermetallic_tial_active": bool(ti_al_fx["active"] > 0.5),
            "intermetallic_tial_stoich_closeness": round(ti_al_fx["stoich_closeness"], 4),
            "cast_iron_graphite_active": bool(cast_iron_fx["active"] > 0.5),
            "cast_iron_graphite_index": round(cast_iron_fx["graphite_index"], 4),
            "castability_index_0_1": round(cast_iron_fx["castability_bonus"], 4),
            "material_state": material_state,
            "state_hardness_factor": round(hardness.state_factor, 4),
            "raw_hardness_hv_before_cap": round(hardness.raw_hv, 2),
            "hardness_cap_hv": round(hardness.hv_cap, 2),
            "effective_shear_gpa": round(hardness.weighted_shear, 3),
            "weighted_data_quality_0_1": round(hardness.weighted_quality, 4),
            "density_kg_m3": round(hardness.weighted_density, 2),
            "estimated_melting_point_k": round(estimated_melting_point_k, 2),
            "eutectic_affinity_factor_0_1": round(eutectic_affinity, 4),
            "neutron_cross_section_barn": round(hardness.weighted_neutron, 4),
        },
        "phase_estimate": {k: round(v, 4) for k, v in corrosion.phase_fractions.items()},
        "corrosion_and_oxidation": {
            "electrode_potential_spread_v": round(corrosion.ep_spread, 4),
            "corrosion_susceptibility_index_0_1": round(corrosion.corrosion_score, 4),
            "halogen_pitting_risk_0_1": round(corrosion.halogen_pitting_risk, 4),
            "passivation_multiplier": round(corrosion.passivation_multiplier, 4),
            "ti_passivation_multiplier": round(corrosion.ti_passivation_multiplier, 4),
            "effective_cr_percent_for_passivation": round(corrosion.effective_cr_percent, 4),
            "effective_free_cr_fraction": round(corrosion.free_cr, 4),
            "protective_oxide_tendency_0_1": round(corrosion.oxide_tendency, 4),
            "environment": env,
            "temperature_k": round(temperature_k, 2),
            "oxygen_activity_0_1": round(oxygen_activity, 4),
        },
        "model_context": {
            "material_regime": material_regime,
            "confidence_index_0_1": round(corrosion.confidence_index, 4),
            "solid_phase_feasibility_0_1": round(feasibility, 4),
        },
        "input_validity": {
            "volatile_fraction_at_temperature": round(hardness.volatile_fraction, 4),
            "noble_gas_fraction": round(hardness.noble_gas_fraction, 4),
            "warnings": input_validity_warnings,
        },
        "impurity_effects": {
            "sulfur_fraction": round(corrosion.s_frac, 6),
            "phosphorus_fraction": round(corrosion.p_frac, 6),
            "manganese_fraction": round(corrosion.mn_frac, 6),
            "cold_shortness_active": bool(corrosion.p_frac > 0.0005),
            "hot_shortness_risk_0_1": round(corrosion.hot_shortness_risk, 4),
            "mn_antidote_active": bool(corrosion.s_frac > 0 and corrosion.mn_frac > 0 and corrosion.mn_frac >= corrosion.s_frac * 5.0),
        },
        "notes": [
            "Model is heuristic and tuned for gameplay-prototyping; calibrate with your target balance.",
            "Use data_quality flags from element files to decide trust level per input property.",
        ],
    }
