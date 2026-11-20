#!/usr/bin/env python3

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class DeltaRecord:
    symbol: str
    delta_percent: float
    classification: str
    solution_mode: str


@dataclass(frozen=True)
class HardnessComputation:
    weighted_tm: float
    weighted_shear: float
    weighted_neutron: float
    weighted_density: float
    weighted_quality: float
    volatile_fraction: float
    noble_gas_fraction: float
    deltas: List[DeltaRecord]
    interstitial_c: float
    substitutional_c: float
    interstitial_term: float
    substitutional_term: float
    sub_weighted_delta: float
    ti_bonus: float
    precip_bonus: float
    mg_bonus: float
    refractory_bonus: float
    superalloy_bonus: float
    carbide_hv_bonus: float
    state_factor: float
    raw_hv: float
    hv_cap: float
    hv_alloy: float


@dataclass(frozen=True)
class ThermalComputation:
    eutectic_affinity: float
    estimated_melting_point_k: float


@dataclass(frozen=True)
class CorrosionComputation:
    dchi_w: float
    brittle_phase_risk: float
    brittleness: float
    sub_compat: str
    interstitial_mode: str
    phase_instability: str
    overall: str
    phase_fractions: Dict[str, float]
    confidence_index: float
    ep_spread: float
    corrosion_score: float
    passivation_multiplier: float
    effective_cr_percent: float
    ti_passivation_multiplier: float
    halogen_pitting_risk: float
    oxide_tendency: float
    free_cr: float
    p_frac: float
    s_frac: float
    mn_frac: float
    hot_shortness_risk: float
