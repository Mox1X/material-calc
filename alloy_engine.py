#!/usr/bin/env python3

import math
from typing import Any, Dict, List

from alloy_models import ElementData
from alloy_tuning import resolve_tuning
from alloy_validation import ensure_known_symbols, normalize_composition, validate_runtime_context
from config.tuning_defaults import HALOGEN_SYMBOLS, NOBLE_GASES
from engine_build_report import build_empirical_report
from engine_compute_corrosion import compute_corrosion
from engine_compute_hardness import compute_hardness
from engine_compute_thermal import compute_thermal
from physics_carbides import CarbideProfile, carbide_profile
from physics_phase_regime import CastIronGraphiteEffect, cast_iron_graphite_effect, detect_material_regime, ti_al_intermetallic_effect
from report_types import CompatibilityReport
from material_reference import composition_matches, profile_composition, reference_candidates
from material_report import add_empirical_properties, blend_report, diagnose, make_report, phase_report


def _resolve_regime_context(
    composition: Dict[str, float],
    base_symbol: str,
    regime_override: str,
) -> tuple[str, CarbideProfile, CastIronGraphiteEffect, Dict[str, float], List[str]]:
    carbides_auto = carbide_profile(base_symbol, composition, force_cermet_mode=None)
    ti_al_fx = ti_al_intermetallic_effect(composition)
    cast_iron_fx = cast_iron_graphite_effect(base_symbol, composition)
    auto_regime = detect_material_regime(base_symbol, composition, carbides_auto, cast_iron_fx)

    requested_override = regime_override if regime_override != 'auto' else None
    material_regime = auto_regime if requested_override is None else requested_override
    requested_cermet = material_regime == 'cermet'
    requested_cast_iron = material_regime == 'cast_iron'

    carbides_local = carbides_auto
    cermet_force: bool | None = None
    if requested_override is not None:
        cermet_force = requested_cermet
        carbides_local = carbide_profile(base_symbol, composition, force_cermet_mode=cermet_force)
    cermet_active = bool(carbides_local['cermet_mode'] > 0.5 and carbides_local['active'] > 0.5)

    regime_validity_warnings: List[str] = []
    cermet_feasible = bool(carbides_auto.get('auto_cermet_candidate', 0.0) > 0.5 and carbides_auto['active'] > 0.5)
    if requested_cermet and (not cermet_feasible or not cermet_active):
        material_regime = auto_regime
        carbides_local = carbides_auto
        cermet_active = bool(carbides_local['cermet_mode'] > 0.5 and carbides_local['active'] > 0.5)
        regime_validity_warnings.append(
            "Requested regime 'cermet' is chemically infeasible for this composition; reverted to auto regime."
        )

    if requested_cast_iron and cast_iron_fx.get('active', 0.0) <= 0.5:
        material_regime = auto_regime
        carbides_local = carbides_auto
        cermet_active = bool(carbides_local['cermet_mode'] > 0.5 and carbides_local['active'] > 0.5)
        regime_validity_warnings.append(
            "Requested regime 'cast_iron' is chemically infeasible for this composition; reverted to auto regime."
        )

    if material_regime != 'cast_iron':
        cast_iron_fx = {
            'active': 0.0,
            'graphite_index': 0.0,
            'hv_multiplier': 1.0,
            'brittleness_add': 0.0,
            'castability_bonus': 0.0,
        }

    return auto_regime, material_regime, carbides_local, cast_iron_fx, ti_al_fx, regime_validity_warnings


def compatibility_report(
    composition: Dict[str, float] | None,
    db: Dict[str, ElementData],
    k_hardening: float,
    material_state: str,
    env: str = 'air',
    temperature_k: float = 298.15,
    oxygen_activity: float = 0.21,
    regime_override: str = 'auto',
    tuning: Dict[str, Any] | None = None,
    *,
    material_profile: str | None = None,
) -> CompatibilityReport:
    report = make_report()
    try:
        temperature_k, oxygen_activity = validate_runtime_context(
            material_state=material_state,
            env=env,
            regime_override=regime_override,
            temperature_k=temperature_k,
            oxygen_activity=oxygen_activity,
        )
        if not math.isfinite(k_hardening) or k_hardening <= 0:
            raise ValueError("k_hardening must be finite and greater than zero")
        report["conditions"] = {
            "material_state": material_state,
            "environment": env,
            "temperature_k": temperature_k,
            "oxygen_activity": oxygen_activity,
        }
        if composition is not None:
            composition = normalize_composition(composition)
            report["composition_normalized"] = composition
            ensure_known_symbols(composition, db)
        if material_profile:
            nominal = profile_composition(material_profile, db)
            if composition is not None and not composition_matches(composition, nominal):
                raise ValueError(f"Composition does not match material profile '{material_profile}'")
            if composition is None:
                composition = nominal
                report["composition_normalized"] = composition
        if composition is None:
            raise ValueError("Specify a composition or a material profile")
    except (TypeError, ValueError, OverflowError) as error:
        diagnose(report, "invalid_input", str(error))
        return report

    if material_profile:
        blend_report(report, material_profile)
        return report

    phases, profiles = reference_candidates(composition, db)
    report["classification"]["candidates"] = phases + profiles
    if len(phases) == 1 and not profiles:
        phase_report(report, phases[0])
        return report

    volatile_unbound = sum(composition.get(symbol, 0.0) for symbol in (*NOBLE_GASES, *HALOGEN_SYMBOLS))
    if volatile_unbound >= 0.02:
        report["classification"].update(kind="mixture", basis="elemental_composition")
        report["status"] = "unsupported"
        report["feasibility"]["status"] = "outside_model_domain"
        diagnose(report, "unresolved_gases_or_halogens", "At least 2 wt% is noble gas or halogen without an identified bound phase; outside the alloy model domain.")
        return report

    if profiles or len(phases) > 1 or sum(composition.get(symbol, 0) for symbol in ("O", "N")) >= 0.02:
        report["classification"].update(kind="compound_or_mixture", family="ceramic", basis="composition_candidates")
        report["status"] = "partial"
        diagnose(report, "phase_assembly_required", "The elemental composition may describe a compound or a phase mixture; select a matching profile or specify the phases.")
        diagnose(report, "properties_unavailable", "Thermal, density, hardness and corrosion estimates need the material's phases.")
        return report

    base_symbol = max(sorted(composition), key=composition.get)
    base = db[base_symbol]
    if base_symbol in {"B", "C", "N", "O", "P", "S", "Se"}:
        report["classification"].update(kind="element" if len(composition) == 1 else "mixture", basis="elemental_composition")
        report["status"] = "unsupported"
        report["feasibility"]["status"] = "outside_model_domain"
        diagnose(report, "nonmetallic_material_unresolved", "No reference phase or applicable metallic model for this composition.")
        return report

    report["classification"].update(kind="element" if len(composition) == 1 else "alloy", basis="empirical_classification")
    missing_electronegativity = any(db[symbol].electronegativity is None for symbol in composition)
    if missing_electronegativity:
        diagnose(report, "electronegativity_missing", "Unknown electronegativity was omitted from the chemical differences.")
    diagnose(report, "galvanic_context_required", "Galvanic corrosion requires the contacting material, electrolyte and contact conditions.")

    auto_regime, material_regime, carbides_local, cast_iron_fx, ti_al_fx, regime_validity_warnings = _resolve_regime_context(
        composition,
        base_symbol,
        regime_override,
    )
    cermet_active = bool(carbides_local['cermet_mode'] > 0.5 and carbides_local['active'] > 0.5)

    resolved_tuning = resolve_tuning(tuning)

    hardness = compute_hardness(
        composition=composition,
        db=db,
        base=base,
        base_symbol=base_symbol,
        material_state=material_state,
        cast_iron_fx=cast_iron_fx,
        carbides_local=carbides_local,
        cermet_active=cermet_active,
        k_hardening=k_hardening,
        resolved_tuning=resolved_tuning,
        temperature_k=temperature_k,
    )

    delta_tuples = [(d.symbol, d.delta_percent, d.classification, d.solution_mode) for d in hardness.deltas]

    thermal = compute_thermal(
        composition=composition,
        db=db,
        base=base,
        material_regime=material_regime,
        deltas=delta_tuples,
        interstitial_c=hardness.interstitial_c,
        sub_weighted_delta=hardness.sub_weighted_delta,
        weighted_tm=hardness.weighted_tm,
        weighted_quality=hardness.weighted_quality,
        resolved_tuning=resolved_tuning,
    )

    corrosion = compute_corrosion(
        composition=composition,
        db=db,
        base=base,
        material_state=material_state,
        material_regime=material_regime,
        cast_iron_fx=cast_iron_fx,
        carbides_local=carbides_local,
        ti_al_fx=ti_al_fx,
        deltas=delta_tuples,
        interstitial_c=hardness.interstitial_c,
        env=env,
        temperature_k=temperature_k,
        oxygen_activity=oxygen_activity,
    )

    feasibility = 1.0
    feasibility *= max(0.0, 1.0 - 1.8 * hardness.volatile_fraction)
    feasibility *= max(0.0, 1.0 - 2.2 * hardness.noble_gas_fraction)

    input_validity_warnings: List[str] = []
    if hardness.volatile_fraction > 0.02:
        input_validity_warnings.append(
            f'Composition includes {hardness.volatile_fraction:.3f} fraction of elements likely non-solid at {temperature_k:.2f} K.'
        )
    if hardness.noble_gas_fraction > 0.0:
        input_validity_warnings.append(
            f'Composition includes noble gases fraction {hardness.noble_gas_fraction:.3f}; alloy feasibility is strongly limited.'
        )
    input_validity_warnings.extend(regime_validity_warnings)

    empirical = build_empirical_report(
        composition=composition,
        base=base,
        base_symbol=base_symbol,
        material_state=material_state,
        material_regime=material_regime,
        hardness=hardness,
        corrosion=corrosion,
        carbides_local=carbides_local,
        ti_al_fx=ti_al_fx,
        cast_iron_fx=cast_iron_fx,
        estimated_melting_point_k=thermal.estimated_melting_point_k,
        eutectic_affinity=thermal.eutectic_affinity,
        env=env,
        temperature_k=temperature_k,
        oxygen_activity=oxygen_activity,
        feasibility=feasibility,
        input_validity_warnings=input_validity_warnings,
    )
    add_empirical_properties(report, empirical, material_state, auto_regime)
    if missing_electronegativity:
        report["status"] = "partial"
        report["model_details"]["hume_rothery"]["electronegativity_weighted_delta"] = None
    for warning in input_validity_warnings:
        diagnose(report, "model_warning", warning)
    return report
