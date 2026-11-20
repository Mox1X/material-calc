#!/usr/bin/env python3
"""Compatibility re-export module.

Physics logic is split across:
- physics_hardness.py
- physics_carbides.py
- physics_corrosion.py
- physics_phase_regime.py
"""

from physics_hardness import (
    affinity_factor,
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
from physics_carbides import CarbideProfile, carbide_profile
from physics_corrosion import corrosion_risk_score, oxide_protection_indicator
from physics_phase_regime import (
    CastIronGraphiteEffect,
    TiAlIntermetallicEffect,
    cast_iron_graphite_effect,
    confidence_index,
    detect_material_regime,
    phase_fractions_estimate,
    ti_al_intermetallic_effect,
)

__all__ = [
    'affinity_factor',
    'al_precipitation_bonus_hv',
    'classify_size_delta',
    'estimate_hv_from_shear',
    'hardness_state_factor',
    'is_trace_impurity',
    'lattice_hardening_factor',
    'mg_alloy_bonus_hv',
    'nickel_superalloy_bonus_hv',
    'pure_hv_floor',
    'refractory_composite_bonus_hv',
    'size_radius_pm',
    'solute_strength_efficiency',
    'substitution_or_interstitial',
    'substitutional_hardening_weight',
    'titanium_alpha_beta_bonus',
    'CarbideProfile',
    'carbide_profile',
    'corrosion_risk_score',
    'oxide_protection_indicator',
    'CastIronGraphiteEffect',
    'TiAlIntermetallicEffect',
    'cast_iron_graphite_effect',
    'confidence_index',
    'detect_material_regime',
    'phase_fractions_estimate',
    'ti_al_intermetallic_effect',
]
