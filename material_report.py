"""Assemble versioned assessments and track the provenance of estimates."""

import math
from collections.abc import Callable
from typing import Any

from material_reference import MATERIAL_PROFILES, PHASES
from report_types import CompatibilityReport, EmpiricalReport, Estimate, ReportConditions

EMPIRICAL_SOURCE = "material-calc empirical gameplay model"
FE_C_SOURCE = "https://www.gotrawama.eu/Siderurgia/The%20C-Fe%20%28Carbon-Iron%29%20System.pdf"
CAST_IRON_SOURCE = "https://doi.org/10.2320/matertrans.F-M2019829"

PROPERTY_UNITS = {
    "vickers_hardness_hv": "HV",
    "density_kg_m3": "kg/m³",
    "melting_point_k": "K",
    "solidus_k": "K",
    "liquidus_k": "K",
    "decomposition_k": "K",
    "decomposition_or_sublimation_k": "K",
    "effective_shear_gpa": "GPa",
    "neutron_cross_section_barn": "barn",
    "corrosion_susceptibility_index_0_1": "1",
    "galvanic_corrosion_risk_index_0_1": "1",
}


def make_report(
    composition: dict[str, float] | None = None,
    conditions: ReportConditions | None = None,
) -> CompatibilityReport:
    return {
        "schema_version": 2,
        "status": "invalid",
        "composition_normalized": composition or {},
        "conditions": conditions,
        "classification": {
            "kind": "unknown", "family": None, "regime": None, "formula": None,
            "profile": None, "candidates": [], "assumed_phase_mass_fractions": None, "basis": "unresolved",
        },
        "feasibility": {"status": "undetermined", "solid_phase_index": None},
        "properties": dict.fromkeys(PROPERTY_UNITS),
        "diagnostics": [],
    }


def diagnose(report: CompatibilityReport, code: str, message: str) -> None:
    report["diagnostics"].append({"code": code, "message": message})


def record_estimate(
    report: CompatibilityReport,
    field: str,
    value: float,
    method: str,
    source: str,
    *assumptions: str,
    value_range: tuple[float, float] | None = None,
) -> None:
    if not math.isfinite(value) or (value_range is not None and not all(map(math.isfinite, value_range))):
        if report["status"] == "ok":
            report["status"] = "partial"
        diagnose(report, "non_finite_estimate", f"{field} could not be estimated with a finite value.")
        return
    estimate: Estimate = {
        "value": value,
        "range": list(value_range) if value_range is not None else None,
        "unit": PROPERTY_UNITS[field],
        "method": method,
        "source": source,
        "assumptions": list(assumptions),
    }
    report["properties"][field] = estimate


def phase_report(report: CompatibilityReport, formula: str) -> None:
    phase = PHASES[formula]
    report["classification"].update(
        kind="compound", family=phase.family, formula=formula,
        basis="stoichiometric_match", assumed_phase_mass_fractions={formula: 1.0},
    )
    report["status"] = "partial"
    report["feasibility"]["status"] = "conditional"
    assumption = f"{formula} is assumed from the mass fractions; the phase was not measured."
    diagnose(report, "phase_assumed", assumption)
    if phase.density:
        value, source, conditions = phase.density
        record_estimate(report, "density_kg_m3", value, "reference", source, assumption, conditions)
    else:
        diagnose(report, "density_unavailable", "No applicable phase density is available.")
    if phase.transition:
        field, value, source, conditions = phase.transition
        record_estimate(report, field, value, "reference", source, assumption, conditions, value_range=phase.transition_range_k)
    else:
        diagnose(report, "thermal_data_unavailable", "No applicable phase transition data is available.")
    diagnose(report, "hardness_requires_microstructure", "Hardness needs phase-specific data for the material's microstructure and processing.")
    diagnose(report, "other_properties_unavailable", "No applicable elastic, neutron or corrosion model is configured for this phase.")


def blend_report(report: CompatibilityReport, profile_id: str) -> None:
    report["status"] = "partial"
    phases = MATERIAL_PROFILES[profile_id]
    report["classification"].update(
        kind="mixture", family="ceramic", profile=profile_id, basis="selected_profile",
        assumed_phase_mass_fractions=dict(phases),
    )
    report["feasibility"]["status"] = "conditional"
    densities = [(mass, PHASES[formula].density) for formula, mass in phases.items()]
    if all(density for _, density in densities):
        inverse_density = sum(mass / density[0] for mass, density in densities if density)
        sources = "; ".join(dict.fromkeys(density[1] for _, density in densities if density))
        record_estimate(
            report, "density_kg_m3", round(1 / inverse_density), "phase_mixture", sources,
            "Nominal mass fractions, zero porosity and additive volumes of unreacted starting oxides.",
        )
    diagnose(report, "phases_unconfirmed", "The selected blend specifies nominal starting oxides; phases after processing are unconfirmed.")
    diagnose(report, "other_properties_unavailable", "Thermal, mechanical and corrosion estimates need data for the processed material.")


def _interpolate(x: float, points: tuple[tuple[float, float], ...]) -> float:
    for (left, a), (right, b) in zip(points, points[1:]):
        if left <= x <= right:
            return a + (b - a) * (x - left) / (right - left)
    raise ValueError("Composition outside interpolation domain")


def metallic_transitions(report: CompatibilityReport, empirical: EmpiricalReport) -> None:
    composition = report["composition_normalized"]
    carbon_pct = composition.get("C", 0.0) * 100
    regime = report["classification"]["regime"]
    if composition.keys() == {"Fe", "C"} and carbon_pct <= 4.3:
        liquidus = _interpolate(carbon_pct, ((0, 1538), (0.53, 1493), (4.3, 1147)))
        solidus = _interpolate(carbon_pct, ((0, 1538), (0.09, 1493), (0.16, 1493), (2.14, 1147), (4.3, 1147)))
        assumption = "Approximate interpolation of the metastable Fe–Fe3C diagram at atmospheric pressure."
        for key, celsius in (("solidus_k", solidus), ("liquidus_k", liquidus)):
            record_estimate(report, key, round(celsius + 273.15), "phase_diagram_interpolation", FE_C_SOURCE, assumption)
        return
    if regime == "cast_iron":
        coefficients = {"C": -110, "Si": -25, "Mn": 3, "P": -35, "S": -71, "Ni": -2, "Cr": -7}
        liquidus = 1625 + sum(100 * composition.get(symbol, 0) * coefficient for symbol, coefficient in coefficients.items())
        if (
            composition.keys() <= coefficients.keys() | {"Fe"}
            and 2.5 <= carbon_pct <= 3.8
            and composition.get("Si", 0) <= 0.03
            and composition.get("Mn", 0) <= 0.01
            and composition.get("P", 0) <= 0.002
            and composition.get("S", 0) <= 0.002
            and composition.get("Ni", 0) <= 0.01
            and composition.get("Cr", 0) <= 0.01
            and 1147 <= liquidus <= 1250
        ):
            record_estimate(
                report, "liquidus_k", round(liquidus + 273.15), "reference_correlation", CAST_IRON_SOURCE,
                "Restricted to low-alloy hypoeutectic cast irons in this implementation.",
            )
            return
    elif regime != "cermet":
        record_estimate(
            report, "melting_point_k", round(empirical["predicted_properties"]["estimated_melting_point_k"], 0),
            "empirical", EMPIRICAL_SOURCE, "Gameplay approximation; solidus and liquidus are unresolved.",
        )
        return
    report["status"] = "partial"
    diagnose(report, "thermal_model_unavailable", "No applicable thermal transition model is available for this composition.")


def _finite_details(node: Any, unavailable: Callable[[], None]) -> Any:
    if isinstance(node, dict):
        return {key: _finite_details(value, unavailable) for key, value in node.items()}
    if isinstance(node, list):
        return [_finite_details(value, unavailable) for value in node]
    if isinstance(node, float) and not math.isfinite(node):
        unavailable()
        return None
    return node


def add_empirical_properties(
    report: CompatibilityReport, empirical: EmpiricalReport, state: str, regime: str,
) -> None:
    context = empirical["model_context"]
    prop = empirical["predicted_properties"]
    corrosion = empirical["corrosion_and_oxidation"]
    hv = prop["vickers_hardness_hv"]
    classification = report["classification"]
    classification["regime"] = regime
    if regime == "cermet":
        classification.update(kind="mixture", family="cermet")
    if regime == "cast_iron":
        classification["candidates"] = ["gray_cast_iron", "white_cast_iron", "ductile_cast_iron", "compacted_graphite_cast_iron"]
        diagnose(report, "cast_iron_microstructure_unresolved", "Cast-iron subtype requires graphite morphology, processing or measured phase data.")
    report["status"] = "ok"
    report["feasibility"]["status"] = "conditional"
    if regime == "cermet":
        diagnose(report, "cermet_phases_assumed", "Carbide and binder fractions are estimated from the composition.")
    score = context["solid_phase_feasibility_0_1"]
    report["feasibility"]["solid_phase_index"] = score if math.isfinite(score) else None
    if regime in {"cast_iron", "cermet"} or (regime == "steel" and prop["state_hardness_factor"] != 1):
        report["status"] = "partial"
        diagnose(report, "hardness_requires_microstructure", "Hardness for this material needs a microstructure or a calibrated processing profile.")
    else:
        record_estimate(
            report, "vickers_hardness_hv", hv, "empirical", EMPIRICAL_SOURCE,
            f"State: {state}; microstructure is not measured.",
        )
    density_method = "empirical_phase_mixture" if regime == "cermet" else "empirical"
    density_assumption = "Estimated carbide and binder fractions; zero porosity." if regime == "cermet" else "Element-weighted density estimate."
    record_estimate(report, "density_kg_m3", round(prop["density_kg_m3"], 0), density_method, EMPIRICAL_SOURCE, density_assumption)
    for field in ("effective_shear_gpa", "neutron_cross_section_barn"):
        record_estimate(report, field, prop[field], "empirical", EMPIRICAL_SOURCE)
    record_estimate(
        report, "corrosion_susceptibility_index_0_1", corrosion["corrosion_susceptibility_index_0_1"],
        "empirical", EMPIRICAL_SOURCE, "Heuristic for the declared environment, temperature and oxygen activity.",
    )
    metallic_transitions(report, empirical)

    details = {
        "base_element": empirical["base_element"],
        "model_regime": context["material_regime"],
        "hume_rothery": empirical["hume_rothery"],
        "confidence_index_0_1": context["confidence_index_0_1"],
        "phase_estimate": empirical["phase_estimate"],
        "impurity_effects": empirical["impurity_effects"],
        "hardness_model": {
            key: value for key, value in prop.items()
            if key not in PROPERTY_UNITS and key != "estimated_melting_point_k"
            and (report["properties"]["vickers_hardness_hv"] is not None or key != "raw_hardness_hv_before_cap")
        },
    }
    missing_numeric = False

    def mark_unavailable() -> None:
        nonlocal missing_numeric
        missing_numeric = True

    report["model_details"] = _finite_details(details, mark_unavailable)
    if missing_numeric:
        report["status"] = "partial"
        diagnose(report, "non_finite_model_detail", "At least one model diagnostic is unavailable because it was non-finite.")
