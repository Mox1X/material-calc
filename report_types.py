#!/usr/bin/env python3

from typing import Any, Dict, List, TypedDict


class BaseElementSection(TypedDict):
    symbol: str
    name: str
    fraction: float


class SizeFactorCheck(TypedDict):
    solute_symbol: str
    delta_percent: float
    classification: str
    solution_mode: str


class HumeRotherySection(TypedDict):
    size_factor_checks: List[SizeFactorCheck]
    electronegativity_weighted_delta: float
    brittle_phase_risk_index_0_1: float
    brittleness_index_0_1: float
    substitutional_compatibility: str
    interstitial_hardening_regime: str
    phase_instability_risk: str
    overall_compatibility: str


class PredictedPropertiesSection(TypedDict):
    vickers_hardness_hv: float
    hardening_interstitial_fraction: float
    hardening_substitutional_fraction: float
    hardening_interstitial_term: float
    hardening_substitutional_term: float
    titanium_alpha_beta_bonus: float
    precipitation_bonus_hv: float
    mg_alloy_bonus_hv: float
    refractory_composite_bonus_hv: float
    nickel_superalloy_bonus_hv: float
    carbide_bonus_hv: float
    carbide_bonus_hv_effective: float
    carbide_bonus_hv_raw: float
    carbide_index: float
    effective_carbide_fraction: float
    carbide_cermet_mode: bool
    intermetallic_tial_active: bool
    intermetallic_tial_stoich_closeness: float
    cast_iron_graphite_active: bool
    cast_iron_graphite_index: float
    castability_index_0_1: float
    material_state: str
    state_hardness_factor: float
    raw_hardness_hv_before_cap: float
    hardness_cap_hv: float
    effective_shear_gpa: float
    weighted_data_quality_0_1: float
    density_kg_m3: float
    estimated_melting_point_k: float
    eutectic_affinity_factor_0_1: float
    neutron_cross_section_barn: float


class PhaseEstimateSection(TypedDict):
    ferrite_matrix_fraction: float
    austenite_fraction: float
    carbide_fraction: float
    graphite_fraction: float
    intermetallic_fraction: float
    binder_fraction: float


class CorrosionSection(TypedDict):
    electrode_potential_spread_v: float
    corrosion_susceptibility_index_0_1: float
    halogen_pitting_risk_0_1: float
    passivation_multiplier: float
    ti_passivation_multiplier: float
    effective_cr_percent_for_passivation: float
    effective_free_cr_fraction: float
    protective_oxide_tendency_0_1: float
    environment: str
    temperature_k: float
    oxygen_activity_0_1: float


class ModelContextSection(TypedDict):
    material_regime: str
    confidence_index_0_1: float
    solid_phase_feasibility_0_1: float


class InputValiditySection(TypedDict):
    volatile_fraction_at_temperature: float
    noble_gas_fraction: float
    warnings: List[str]


class ImpurityEffectsSection(TypedDict):
    sulfur_fraction: float
    phosphorus_fraction: float
    manganese_fraction: float
    cold_shortness_active: bool
    hot_shortness_risk_0_1: float
    mn_antidote_active: bool


class EmpiricalReport(TypedDict):
    base_element: BaseElementSection
    composition_normalized: Dict[str, float]
    hume_rothery: HumeRotherySection
    predicted_properties: PredictedPropertiesSection
    phase_estimate: PhaseEstimateSection
    corrosion_and_oxidation: CorrosionSection
    model_context: ModelContextSection
    input_validity: InputValiditySection
    impurity_effects: ImpurityEffectsSection
    notes: List[str]


class Estimate(TypedDict):
    value: float | None
    range: list[float] | None
    unit: str
    method: str
    source: str
    assumptions: list[str]


class Diagnostic(TypedDict):
    code: str
    message: str


class Classification(TypedDict):
    kind: str
    family: str | None
    regime: str | None
    formula: str | None
    profile: str | None
    candidates: list[str]
    assumed_phase_mass_fractions: dict[str, float] | None
    basis: str


class Feasibility(TypedDict):
    status: str
    solid_phase_index: float | None


class ReportConditions(TypedDict):
    material_state: str
    environment: str
    temperature_k: float
    oxygen_activity: float


class RequiredReportFields(TypedDict):
    schema_version: int
    status: str
    composition_normalized: dict[str, float]
    conditions: ReportConditions | None
    classification: Classification
    feasibility: Feasibility
    properties: dict[str, Estimate | None]
    diagnostics: list[Diagnostic]


class CompatibilityReport(RequiredReportFields, total=False):
    model_details: dict[str, Any]
    calibration: dict[str, Any]


def estimate_value(report: CompatibilityReport, field: str) -> float | None:
    estimate = report["properties"].get(field)
    return estimate["value"] if estimate is not None else None
