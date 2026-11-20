#!/usr/bin/env python3

from typing import Any, Dict, List

from alloy_models import ElementData
from alloy_tuning import resolve_tuning
from alloy_validation import ensure_known_symbols, validate_composition_values, validate_runtime_context
from engine_build_report import build_report
from engine_compute_corrosion import compute_corrosion
from engine_compute_hardness import compute_hardness
from engine_compute_thermal import compute_thermal
from physics_carbides import CarbideProfile, carbide_profile
from physics_phase_regime import CastIronGraphiteEffect, cast_iron_graphite_effect, detect_material_regime, ti_al_intermetallic_effect
from report_types import CompatibilityReport


def _validate_composition_symbols(composition: Dict[str, float], db: Dict[str, ElementData]) -> None:
    validate_composition_values(composition)
    ensure_known_symbols(composition, db)


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

    return material_regime, carbides_local, cast_iron_fx, ti_al_fx, regime_validity_warnings


def compatibility_report(
    composition: Dict[str, float],
    db: Dict[str, ElementData],
    k_hardening: float,
    material_state: str,
    env: str = 'air',
    temperature_k: float = 298.15,
    oxygen_activity: float = 0.21,
    regime_override: str = 'auto',
    tuning: Dict[str, Any] | None = None,
) -> CompatibilityReport:
    temperature_k, oxygen_activity = validate_runtime_context(
        material_state=material_state,
        env=env,
        regime_override=regime_override,
        temperature_k=temperature_k,
        oxygen_activity=oxygen_activity,
    )
    _validate_composition_symbols(composition, db)

    base_symbol = max(composition.items(), key=lambda kv: kv[1])[0]
    base = db[base_symbol]

    material_regime, carbides_local, cast_iron_fx, ti_al_fx, regime_validity_warnings = _resolve_regime_context(
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

    return build_report(
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
