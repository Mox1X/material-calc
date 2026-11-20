#!/usr/bin/env python3

from typing import Any, Dict, Final, Tuple


DEFAULT_TUNING_PROFILE: Dict[str, Any] = {
    "thermal": {
        "delta_to_base_weight": 0.35,
        "quality_pull_to_base": 0.45,
        "affinity_penalty_strength": 0.75,
        "affinity_soft_penalty_strength": 0.12,
        "min_tm_fraction": 0.72,
        "regime_overrides": {
            "steel": {
                "affinity_penalty_strength": 0.24,
                "affinity_soft_penalty_strength": 0.06,
                "min_tm_fraction": 0.82,
            },
            "cast_iron": {
                "affinity_penalty_strength": 0.32,
                "affinity_soft_penalty_strength": 0.08,
                "min_tm_fraction": 0.80,
            },
            "cermet": {
                "affinity_penalty_strength": 0.68,
                "affinity_soft_penalty_strength": 0.12,
                "min_tm_fraction": 0.60,
            },
            "refractory": {
                "affinity_penalty_strength": 0.58,
                "affinity_soft_penalty_strength": 0.10,
                "min_tm_fraction": 0.68,
            },
        },
    },
    "hardness": {
        "delta_to_base_weight": 0.25,
        "quality_pull_to_base": 0.35,
        "superalloy_al_ti_threshold": 0.012,
    },
    "state_factors": {
        "high_carbide_steel_threshold": 1.0,
        "high_carbide_steel": {
            "raw": 0.22,
            "tempered": 0.68,
            "quenched": 0.88,
            "potential": 1.0,
            "default": 0.26,
        },
        "carbon_tool_steel_c_min": 0.006,
        "carbon_tool_steel_max_alloying": 0.05,
        "carbon_tool_steel_max_strong_alloying": 0.08,
        "carbon_tool_steel": {
            "raw": 0.78,
            "tempered": 1.55,
            "quenched": 2.20,
            "potential": 2.50,
            "default": 0.82,
        },
        "high_speed_steel_c_min": 0.006,
        "high_speed_steel_formers_min": 0.07,
        "high_speed_steel_alloy_score_min": 0.08,
        "high_speed_steel": {
            "raw": 0.32,
            "tempered": 1.28,
            "quenched": 1.38,
            "potential": 1.48,
            "default": 0.45,
        },
    },
}

SIZE_RADIUS_OVERRIDES_PM: Final[Dict[str, float]] = {
    "Cu": 128.0,
    "Ag": 144.0,
    "Au": 144.0,
}

PURE_HV_FLOORS: Final[Dict[str, float]] = {
    "Al": 25.0,
    "Cu": 35.0,
    "Ag": 25.0,
    "Au": 25.0,
    "Ti": 120.0,
    "Fe": 90.0,
}

SOLUTE_STRENGTH_EFFICIENCY: Final[Dict[str, float]] = {
    "W": 4.5,
    "Mo": 3.8,
    "V": 3.5,
    "Cr": 2.8,
    "Co": 2.4,
    "Nb": 2.6,
    "Ta": 2.8,
    "Ti": 2.3,
    "Al": 1.4,
    "Ni": 1.8,
    "Sn": 2.1,
    "Zn": 0.9,
    "Mg": 1.2,
    "Cu": 1.1,
}

CARBIDE_FORMER_AFFINITY: Final[Dict[str, float]] = {
    "Ti": 2.2,
    "V": 1.9,
    "W": 2.0,
    "Mo": 1.7,
    "Cr": 1.2,
    "Nb": 2.0,
    "Ta": 2.3,
}

TRACE_IMPURITY_SYMBOLS: Final[Tuple[str, ...]] = ("S", "P")
NOBLE_GASES: Final[Tuple[str, ...]] = ("He", "Ne", "Ar", "Kr", "Xe", "Rn", "Og")
LOW_MELT_SET: Final[Tuple[str, ...]] = ("Sn", "Pb", "Bi", "In", "Cd")
HALOGEN_SYMBOLS: Final[Tuple[str, ...]] = ("F", "Cl", "Br", "I")
REFRACTORY_BASES: Final[Tuple[str, ...]] = ("W", "Mo", "Ta", "Nb")
UNSTABLE_SET: Final[Tuple[str, ...]] = (
    "Rn",
    "Fr",
    "Po",
    "At",
    "Ra",
    "Ac",
    "Th",
    "Pa",
    "U",
    "Np",
    "Pu",
    "Am",
    "Cm",
    "Bk",
    "Cf",
)

CORROSION_ENV_FACTOR: Final[Dict[str, float]] = {
    "vacuum": 0.03,
    "air": 0.85,
    "water": 1.0,
    "acid": 1.35,
}

HALOGEN_ENV_FACTOR: Final[Dict[str, float]] = {
    "vacuum": 0.35,
    "air": 0.9,
    "water": 1.0,
    "acid": 1.15,
}

TITANIUM_ALPHA_BETA_PARAMS: Final[Dict[str, float]] = {
    "ti_min": 0.7,
    "al_v_al_min": 0.05,
    "al_v_v_min": 0.03,
    "al_only_min": 0.04,
    "al_v_multiplier": 3.0,
    "al_only_multiplier": 1.8,
    "o_min": 0.001,
    "o_max": 0.004,
    "o_multiplier": 1.15,
}

AL_PRECIPITATION_PARAMS: Final[Dict[str, float]] = {
    "cu_min": 0.02,
    "mg_for_cu_min": 0.003,
    "cu_scale": 0.04,
    "mg_scale": 0.01,
    "cu_mg_bonus": 85.0,
    "mg_min": 0.005,
    "si_min": 0.003,
    "si_scale": 0.006,
    "mg_si_bonus": 55.0,
    "bonus_cap_scale": 1.5,
}

MG_ALLOY_PARAMS: Final[Dict[str, float]] = {
    "al_min": 0.06,
    "zn_min": 0.005,
    "al_scale": 0.09,
    "zn_scale": 0.01,
    "al_zn_bonus": 35.0,
    "bonus_cap_scale": 1.2,
    "mn_min": 0.001,
    "mn_flat_bonus": 6.0,
}

REFRACTORY_COMPOSITE_PARAMS: Final[Dict[str, float]] = {
    "w_min": 0.7,
    "binder_min": 0.03,
    "core_multiplier": 3000.0,
    "w_power": 1.2,
    "binder_power": 0.35,
}

NICKEL_SUPERALLOY_PARAMS: Final[Dict[str, float]] = {
    "ni_min": 0.5,
    "cr_min": 0.12,
    "base_bonus": 90.0,
    "al_ti_coeff": 400.0,
    "refractory_coeff": 250.0,
    "refractory_cap": 0.2,
    "bonus_cap": 300.0,
}

SIZE_CLASS_LIMITS: Final[Dict[str, float]] = {
    "excellent_max": 8.0,
    "limited_max": 15.0,
    "interstitial_ratio_max": 0.59,
}

AFFINITY_PARAMS: Final[Dict[str, float]] = {
    "trace_multiplier": 0.15,
    "size_norm": 0.15,
    "interstitial_size_multiplier": 1.8,
    "chi_weight": 0.35,
    "size_weight": 0.9,
    "aff_cap": 0.5,
    "noble_like_multiplier": 0.1,
}

CARBIDE_PARAMS: Final[Dict[str, float]] = {
    "effective_carbide_c_scale": 5.0,
    "index_multiplier": 100.0,
    "auto_cermet_c_min": 0.04,
    "auto_cermet_w_ti_ta_min": 0.5,
    "hardness_cermet_hv_base": 1800.0,
    "hardness_cermet_ti_ta_coeff": 500.0,
    "hardness_cermet_binder_hv_base": 180.0,
    "hardness_cermet_binder_hv_coeff": 120.0,
    "hardness_cermet_binder_cap": 0.2,
    "hardness_cermet_mix_low": 0.65,
    "hardness_cermet_mix_high": 0.35,
    "hardness_non_cermet_coeff": 220.0,
    "hardness_non_cermet_index_cap": 2.0,
    "hardness_non_cermet_mix_low": 0.7,
    "hardness_non_cermet_mix_high": 0.3,
    "brittleness_sqrt_coeff": 0.25,
    "brittleness_cermet_add": 0.35,
    "brittleness_binder_relief": 0.8,
    "brittleness_cap": 0.85,
    "low_potential_brittleness_c_coeff": 4.0,
    "low_potential_brittleness_cap": 0.2,
    "chromium_tied_c_coeff": 4.0,
    "chromium_tied_vwm_coeff": 10.0,
    "chromium_tied_cr_coeff": 2.0,
}

CAST_IRON_PARAMS: Final[Dict[str, float]] = {
    "c_min": 0.0214,
    "graphitizer_cap": 0.05,
    "graphite_base_excess_div": 0.035,
    "graphite_graphitizer_coeff": 6.0,
    "hv_multiplier_base": 1.0,
    "hv_multiplier_graphite_coeff": 0.82,
    "hv_multiplier_min": 0.30,
    "brittleness_base": 0.25,
    "brittleness_graphite_coeff": 0.45,
    "castability_base": 0.30,
    "castability_graphite_coeff": 0.70,
}

CORROSION_PARAMS: Final[Dict[str, float]] = {
    "spread_norm_v": 0.5,
    "galvanic_weight": 0.75,
    "intrinsic_weight": 0.45,
    "intrinsic_norm_v": 1.2,
    "cr_carbide_tie_coeff": 8.0,
    "effective_cr_threshold": 12.5,
    "low_c_threshold": 0.08,
    "mid_c_threshold": 0.3,
    "passivation_low": 0.1,
    "passivation_mid": 0.35,
    "ti_passivation": 0.2,
    "ti_oxygen_threshold": 0.005,
    "ti_oxygen_multiplier": 0.8,
    "ti_pd_threshold": 0.001,
    "ti_pd_multiplier": 0.35,
    "al_passivation": 0.35,
    "al_mgsi_threshold": 0.005,
    "al_mgsi_multiplier": 0.85,
    "noble_like_multiplier": 0.01,
    "temp_factor_min": 0.6,
    "temp_factor_max": 1.6,
    "temp_factor_exp": 0.25,
    "vacuum_oxygen_max": 0.2,
    "other_oxygen_min": 0.4,
    "other_oxygen_max": 1.3,
    "other_oxygen_offset": 0.6,
    "halogen_base": 0.35,
    "halogen_coeff": 45.0,
}
