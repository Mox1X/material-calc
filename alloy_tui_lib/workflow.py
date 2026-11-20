#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from alloy_engine import compatibility_report
from alloy_models import ElementData
from alloy_validation import ensure_known_symbols, normalize_composition
from composition import parse_composition
from material_reference import MATERIAL_PROFILES, profile_composition
from report_types import estimate_value

from .common import (
    Ansi,
    BAR_EMPTY,
    bold,
    clamp01,
    clear_screen,
    colorize,
    fmt_delta,
    fmt_float,
    format_compact_table,
    format_percent,
    numeric,
    progress_bar,
    signed_bar,
    summary_value,
    warning_color,
)
from .models import CaseConfig, payload_to_case
from .storage import show_case_list


def render_dashboard(case: CaseConfig, report: Dict[str, Any], case_files: List[Path], last_error: str | None) -> None:
    clear_screen()
    print(bold("Alloy TUI Dashboard"))
    print(f"Case: {colorize(case.name, Ansi.CYAN)}    Saved cases: {len(case_files)}")
    print("-" * 88)

    details = report.get("model_details", {})
    phase = details.get("phase_estimate", {})
    classification = report["classification"]
    material = classification["profile"] or classification["formula"] or classification["regime"] or classification["kind"]
    hardness = report["properties"]["vickers_hardness_hv"]
    hv = estimate_value(report, "vickers_hardness_hv")
    if hardness is not None and hardness["range"] is not None:
        hardness_text = "–".join(fmt_float(limit, 0) for limit in hardness["range"])
    else:
        hardness_text = fmt_float(hv, 2)

    key_rows = [
        ["Material", material, "Status", report["status"]],
        ["Hardness (HV)", hardness_text, "Profile", case.material_profile or "n/a"],
        ["Corrosion susceptibility", fmt_float(estimate_value(report, "corrosion_susceptibility_index_0_1")), "Confidence", fmt_float(details.get("confidence_index_0_1"))],
        ["Melting point (K)", fmt_float(estimate_value(report, "melting_point_k"), 0), "Density (kg/m³)", fmt_float(estimate_value(report, "density_kg_m3"), 0)],
        ["Solidus (K)", fmt_float(estimate_value(report, "solidus_k"), 0), "Liquidus (K)", fmt_float(estimate_value(report, "liquidus_k"), 0)],
    ]
    for code, label in (("decomposition_k", "Decomposition (K)"), ("decomposition_or_sublimation_k", "Decomposition or sublimation (K)")):
        value = estimate_value(report, code)
        if value is not None:
            key_rows.append([label, fmt_float(value, 0), "", ""])
    print(bold("Key Metrics"))
    print(format_compact_table(key_rows))
    if classification["candidates"]:
        print("Candidates: " + ", ".join(classification["candidates"]))

    print()
    print(bold("Composition (Elements)"))
    comp_rows: List[List[str]] = [["Symbol", "Fraction", "Bar"]]
    for sym, frac in sorted(case.composition.items(), key=lambda kv: kv[1], reverse=True):
        comp_rows.append([sym, format_percent(frac), progress_bar(frac)])
    print(format_compact_table(comp_rows))

    print()
    if phase:
        print(bold("Estimated Phase Fractions"))
        phase_rows: List[List[str]] = [["Phase", "Fraction", "Bar"]]
        for key, frac in sorted(phase.items()):
            phase_name = key.replace("_fraction", "").replace("_", " ")
            fraction_text = "n/a" if frac is None else format_percent(frac)
            fraction_bar = "" if frac is None else progress_bar(frac)
            phase_rows.append([phase_name, fraction_text, fraction_bar])
        print(format_compact_table(phase_rows))

    print()
    print(bold("Diagnostics"))
    for item in report["diagnostics"]:
        message = item["message"]
        print(colorize(f"! {message}", warning_color(message)))

    if last_error:
        print()
        print(colorize(f"Last error: {last_error}", Ansi.RED))

    print()
    print(bold("Commands"))
    print(
        "recalc | edit-comp | edit-params | save | load | list | list-config | compare | contrib | new | help | quit"
    )


def print_help() -> None:
    print("Commands:")
    print("  recalc      Recalculate the current report")
    print("  edit-comp   Edit composition by set/remove/full string")
    print("  edit-params Edit state, environment, regime, conditions, or material profile")
    print("  save        Save current case under --cases-dir/*.json")
    print("  load        Load a saved case by number")
    print("  list        Show saved case list")
    print("  list-config Configure list filter/sort/order")
    print("  compare     Compare two cases side-by-side (0 = current case)")
    print("  contrib     Element/property contribution screen")
    print("  new         Reset to default case")
    print("  help        Show this help")
    print("  quit        Exit")


def edit_composition_interactive(current: Dict[str, float], db: Dict[str, ElementData]) -> Dict[str, float]:
    comp = dict(current)
    while True:
        print()
        print(bold("Composition editor"))
        rows: List[List[str]] = [["Symbol", "Fraction", "Bar"]]
        for sym, frac in sorted(comp.items(), key=lambda kv: kv[1], reverse=True):
            rows.append([sym, format_percent(frac), progress_bar(frac)])
        print(format_compact_table(rows))
        print("Input:")
        print("  set <SYMBOL> <percent>     (example: set W 12.5)")
        print("  remove <SYMBOL>")
        print("  full <composition-string>  (example: full Fe:0.7,Cr:0.2,C:0.1)")
        print("  done")
        raw = input("comp> ").strip()
        if raw in {"done", "d", "exit"}:
            ensure_known_symbols(comp, db, source_name="elements/")
            return normalize_composition(comp)
        if not raw:
            continue
        parts = raw.split()
        try:
            if parts[0] == "set" and len(parts) == 3:
                sym = parts[1].strip()
                pct = float(parts[2])
                if pct <= 0:
                    raise ValueError("Percent must be > 0")
                comp[sym] = pct / 100.0
                comp = normalize_composition(comp)
            elif parts[0] == "remove" and len(parts) == 2:
                sym = parts[1].strip()
                if sym not in comp:
                    raise ValueError(f"Symbol '{sym}' is not in composition")
                del comp[sym]
                comp = normalize_composition(comp)
            elif parts[0] == "full" and len(parts) >= 2:
                comp = parse_composition(" ".join(parts[1:]))
                ensure_known_symbols(comp, db, source_name="elements/")
            else:
                print(colorize("Unknown command for composition editor.", Ansi.YELLOW))
        except Exception as exc:
            print(colorize(f"Error: {exc}", Ansi.RED))


def edit_params_interactive(case: CaseConfig, db: Dict[str, ElementData]) -> CaseConfig:
    print()
    print(bold("Edit parameters (press Enter to keep current value)"))

    name = input(f"name [{case.name}]: ").strip() or case.name
    state = input(f"state raw|tempered|quenched|potential [{case.state}]: ").strip() or case.state
    env = input(f"env air|water|acid|vacuum [{case.env}]: ").strip() or case.env
    regime = (
        input(f"regime auto|steel|cast_iron|cermet|refractory|nonferrous [{case.regime_override}]: ").strip()
        or case.regime_override
    )

    temp_raw = input(f"temperature_k [{case.temperature_k}]: ").strip()
    oxy_raw = input(f"oxygen_activity 0..1 [{case.oxygen_activity}]: ").strip()
    k_raw = input(f"k_hardening [{case.k_hardening}]: ").strip()

    print("Material profiles: " + ", ".join(MATERIAL_PROFILES))
    profile_input = input(f"material profile [{case.material_profile or 'none'}] (none to clear): ").strip()
    profile = case.material_profile
    if profile_input:
        profile = None if profile_input == "none" else profile_input
    composition = dict(case.composition)
    if profile and profile != case.material_profile:
        composition = profile_composition(profile, db)

    updated = CaseConfig(
        name=name,
        composition=composition,
        state=state,
        env=env,
        temperature_k=case.temperature_k,
        oxygen_activity=case.oxygen_activity,
        regime_override=regime,
        k_hardening=case.k_hardening,
        material_profile=profile,
    )
    if temp_raw:
        updated.temperature_k = numeric(temp_raw, case.temperature_k)
    if oxy_raw:
        updated.oxygen_activity = clamp01(numeric(oxy_raw, case.oxygen_activity))
    if k_raw:
        updated.k_hardening = numeric(k_raw, case.k_hardening)
    return updated


def recalc_report(case: CaseConfig, db: Dict[str, ElementData]) -> Dict[str, Any]:
    comp = normalize_composition(case.composition)
    ensure_known_symbols(comp, db, source_name="elements/")
    case.composition = comp
    return compatibility_report(
        comp,
        db,
        k_hardening=case.k_hardening,
        material_state=case.state,
        env=case.env,
        temperature_k=case.temperature_k,
        oxygen_activity=case.oxygen_activity,
        regime_override=case.regime_override,
        material_profile=case.material_profile,
    )


def prompt_case_list_options(
    filter_text: str,
    sort_key: str,
    descending: bool,
) -> tuple[str, str, bool]:
    print("List view options (press Enter to keep current):")
    filter_raw = input(f"filter text [{filter_text or '*'}]: ").strip()
    sort_raw = input(f"sort by saved|name|hv|regime|corrosion|brittleness [{sort_key}]: ").strip().lower()
    order_default = "desc" if descending else "asc"
    order_raw = input(f"order asc|desc [{order_default}]: ").strip().lower()

    next_filter = filter_raw if filter_raw != "" else filter_text
    next_sort = sort_raw if sort_raw in {"saved", "name", "hv", "regime", "corrosion", "brittleness"} else sort_key
    if order_raw in {"asc", "desc"}:
        next_desc = order_raw == "desc"
    else:
        next_desc = descending
    return next_filter, next_sort, next_desc


def render_compare_cases(
    left_label: str,
    left_case: CaseConfig,
    left_report: Dict[str, Any],
    right_label: str,
    right_case: CaseConfig,
    right_report: Dict[str, Any],
) -> None:
    clear_screen()
    print(bold("Case Comparison"))
    print(f"Left:  {colorize(left_label, Ansi.CYAN)}")
    print(f"Right: {colorize(right_label, Ansi.CYAN)}")
    print("-" * 88)

    left_regime = str(left_report["classification"]["regime"] or left_report["classification"]["kind"])
    right_regime = str(right_report["classification"]["regime"] or right_report["classification"]["kind"])

    metrics = [
        (
            "Hardness HV",
            estimate_value(left_report, "vickers_hardness_hv"),
            estimate_value(right_report, "vickers_hardness_hv"),
            False,
            2,
        ),
        (
            "Melt Temp K",
            estimate_value(left_report, "melting_point_k"),
            estimate_value(right_report, "melting_point_k"),
            False,
            2,
        ),
        (
            "Corrosion susceptibility 0..1",
            estimate_value(left_report, "corrosion_susceptibility_index_0_1"),
            estimate_value(right_report, "corrosion_susceptibility_index_0_1"),
            True,
            4,
        ),
        (
            "Brittleness 0..1",
            summary_value(left_report, "hume_rothery", "brittleness_index_0_1"),
            summary_value(right_report, "hume_rothery", "brittleness_index_0_1"),
            True,
            4,
        ),
        (
            "Confidence 0..1",
            summary_value(left_report, "model_context", "confidence_index_0_1"),
            summary_value(right_report, "model_context", "confidence_index_0_1"),
            False,
            4,
        ),
        (
            "Density kg/m3",
            estimate_value(left_report, "density_kg_m3"),
            estimate_value(right_report, "density_kg_m3"),
            False,
            2,
        ),
    ]

    rows: List[List[str]] = [["Metric", "Left", "Right", "Delta (R-L)"]]
    rows.append(["Regime", left_regime, right_regime, "n/a"])
    rows.append(["Status", left_report["status"], right_report["status"], "n/a"])
    for field, label in (("solidus_k", "Solidus K"), ("liquidus_k", "Liquidus K"), ("decomposition_k", "Decomposition K"), ("decomposition_or_sublimation_k", "Decomposition or sublimation K")):
        left_value = estimate_value(left_report, field)
        right_value = estimate_value(right_report, field)
        if left_value is not None or right_value is not None:
            metrics.append((label, left_value, right_value, False, 0))
    for label, left_v, right_v, risk_delta, prec in metrics:
        delta = None if left_v is None or right_v is None else right_v - left_v
        rows.append(
            [
                label,
                fmt_float(left_v, prec),
                fmt_float(right_v, prec),
                fmt_delta(delta, higher_is_risk=risk_delta, precision=prec),
            ]
        )
    print(bold("Key Metrics"))
    print(format_compact_table(rows))

    print()
    print(bold("Composition Delta"))
    sym_union = sorted(set(left_case.composition) | set(right_case.composition))
    comp_rows: List[List[str]] = [["Symbol", "Left %", "Right %", "Delta"]]
    for sym in sym_union:
        left_frac = left_case.composition.get(sym, 0.0)
        right_frac = right_case.composition.get(sym, 0.0)
        comp_rows.append(
            [
                sym,
                format_percent(left_frac) if left_frac is not None else "n/a",
                format_percent(right_frac) if right_frac is not None else "n/a",
                fmt_delta(delta, precision=2) + "%" if delta is not None else "n/a",
            ]
        )
    print(format_compact_table(comp_rows))

    print()
    print(bold("Phase Delta"))
    left_phase = left_report.get("model_details", {}).get("phase_estimate", {})
    right_phase = right_report.get("model_details", {}).get("phase_estimate", {})
    phase_keys = sorted(set(left_phase.keys()) | set(right_phase.keys()))
    phase_rows: List[List[str]] = [["Phase", "Left %", "Right %", "Delta"]]
    for key in phase_keys:
        left_frac = left_phase.get(key)
        right_frac = right_phase.get(key)
        delta = None if left_frac is None or right_frac is None else (right_frac - left_frac) * 100.0
        phase_rows.append(
            [
                key.replace("_fraction", "").replace("_", " "),
                format_percent(left_frac) if left_frac is not None else "n/a",
                format_percent(right_frac) if right_frac is not None else "n/a",
                fmt_delta(delta, precision=2) + "%" if delta is not None else "n/a",
            ]
        )
    print(format_compact_table(phase_rows))


def compare_cases_interactive(
    cases_dir: Path,
    db: Dict[str, ElementData],
    current_case: CaseConfig,
    current_report: Dict[str, Any],
    filter_text: str,
    sort_key: str,
    descending: bool,
) -> None:
    items = show_case_list(cases_dir, filter_text=filter_text, sort_key=sort_key, descending=descending)
    print(" 0. <current case>")
    if not items:
        print("Only current case is available for comparison.")
    left_raw = input("left index (0=current)> ").strip()
    right_raw = input("right index (0=current)> ").strip()
    if not left_raw or not right_raw:
        raise ValueError("Compare cancelled.")
    left_idx = int(left_raw)
    right_idx = int(right_raw)

    def resolve(index: int) -> tuple[str, CaseConfig, Dict[str, Any]]:
        if index == 0:
            return current_case.name, current_case, current_report
        if index < 1 or index > len(items):
            raise ValueError(f"Index {index} out of range.")
        payload = json.loads(items[index - 1].path.read_text(encoding="utf-8"))

        cfg = payload_to_case(payload)
        rep = recalc_report(cfg, db)
        return cfg.name, cfg, rep

    left_label, left_case, left_report = resolve(left_idx)
    right_label, right_case, right_report = resolve(right_idx)
    render_compare_cases(left_label, left_case, left_report, right_label, right_case, right_report)
    input("Press Enter to continue...")


def compute_element_contributions(
    case: CaseConfig,
    db: Dict[str, ElementData],
    baseline_report: Dict[str, Any],
) -> List[Dict[str, Any]]:
    base_hv = estimate_value(baseline_report, "vickers_hardness_hv")
    transition = "liquidus_k" if baseline_report["properties"]["liquidus_k"] is not None else "melting_point_k"
    base_tm = estimate_value(baseline_report, transition)
    base_cor = estimate_value(baseline_report, "corrosion_susceptibility_index_0_1")
    base_brit = summary_value(baseline_report, "hume_rothery", "brittleness_index_0_1")

    rows: List[Dict[str, Any]] = []
    for sym, frac in sorted(case.composition.items(), key=lambda kv: kv[1], reverse=True):
        reduced = {k: v for k, v in case.composition.items() if k != sym}
        if not reduced:
            rows.append(
                {
                    "symbol": sym,
                    "fraction": frac,
                    "delta_hv": None,
                    "delta_tm": None,
                    "delta_corrosion": None,
                    "delta_brittleness": None,
                }
            )
            continue

        reduced_norm = normalize_composition(reduced)
        reduced_report = compatibility_report(
            reduced_norm,
            db,
            k_hardening=case.k_hardening,
            material_state=case.state,
            env=case.env,
            temperature_k=case.temperature_k,
            oxygen_activity=case.oxygen_activity,
            regime_override=case.regime_override,
        )

        reduced_hv = estimate_value(reduced_report, "vickers_hardness_hv")
        reduced_tm = estimate_value(reduced_report, transition)
        reduced_cor = estimate_value(reduced_report, "corrosion_susceptibility_index_0_1")
        reduced_brit = summary_value(reduced_report, "hume_rothery", "brittleness_index_0_1")

        rows.append(
            {
                "symbol": sym,
                "fraction": frac,
                "delta_hv": None if base_hv is None or reduced_hv is None else base_hv - reduced_hv,
                "delta_tm": None if base_tm is None or reduced_tm is None else base_tm - reduced_tm,
                "delta_corrosion": None if base_cor is None or reduced_cor is None else base_cor - reduced_cor,
                "delta_brittleness": None if base_brit is None or reduced_brit is None else base_brit - reduced_brit,
            }
        )
    return rows


def render_contributions_screen(
    case: CaseConfig,
    report: Dict[str, Any],
    db: Dict[str, ElementData],
) -> None:
    clear_screen()
    print(bold("Element Contributions"))
    print(f"Case: {colorize(case.name, Ansi.CYAN)}")
    print("-" * 88)

    contrib_rows = compute_element_contributions(case, db, report)
    max_abs_hv = max((abs(r["delta_hv"]) for r in contrib_rows if isinstance(r.get("delta_hv"), float)), default=0.0)

    print(bold("Leave-One-Out Effect (full model minus model without element)"))
    table: List[List[str]] = [["Sym", "Frac", "dHV", "HV Impact", "dThermal(K)", "dCor", "dBrit"]]
    for row in contrib_rows:
        delta_hv = row["delta_hv"]
        delta_tm = row["delta_tm"]
        delta_cor = row["delta_corrosion"]
        delta_brit = row["delta_brittleness"]
        if isinstance(delta_hv, float):
            hv_text = fmt_delta(delta_hv, higher_is_risk=False, precision=2)
            hv_bar = signed_bar(delta_hv, max_abs_hv)
        else:
            hv_text = "n/a"
            hv_bar = "[" + BAR_EMPTY * 14 + "]"
        tm_text = fmt_delta(delta_tm, higher_is_risk=False, precision=2) if isinstance(delta_tm, float) else "n/a"
        cor_text = fmt_delta(delta_cor, higher_is_risk=True, precision=4) if isinstance(delta_cor, float) else "n/a"
        brit_text = fmt_delta(delta_brit, higher_is_risk=True, precision=4) if isinstance(delta_brit, float) else "n/a"
        table.append(
            [
                str(row["symbol"]),
                f"{float(row['fraction']) * 100.0:5.2f}%",
                hv_text,
                hv_bar,
                tm_text,
                cor_text,
                brit_text,
            ]
        )
    print(format_compact_table(table))

    print()
    print(bold("Hardness Components"))
    hard_rows = [
        [
            "Interstitial term",
            fmt_float(summary_value(report, "hardness_model", "hardening_interstitial_term"), 4),
        ],
        [
            "Substitutional term",
            fmt_float(summary_value(report, "hardness_model", "hardening_substitutional_term"), 4),
        ],
        [
            "Precipitation bonus HV",
            fmt_float(summary_value(report, "hardness_model", "precipitation_bonus_hv"), 2),
        ],
        ["Mg alloy bonus HV", fmt_float(summary_value(report, "hardness_model", "mg_alloy_bonus_hv"), 2)],
        [
            "Refractory bonus HV",
            fmt_float(summary_value(report, "hardness_model", "refractory_composite_bonus_hv"), 2),
        ],
        [
            "Ni superalloy bonus HV",
            fmt_float(summary_value(report, "hardness_model", "nickel_superalloy_bonus_hv"), 2),
        ],
        ["Carbide bonus HV", fmt_float(summary_value(report, "hardness_model", "carbide_bonus_hv"), 2)],
        ["State hardness factor", fmt_float(summary_value(report, "hardness_model", "state_hardness_factor"), 4)],
        [
            "Raw hardness before cap",
            fmt_float(summary_value(report, "hardness_model", "raw_hardness_hv_before_cap"), 2),
        ],
        ["Final hardness HV", fmt_float(estimate_value(report, "vickers_hardness_hv"), 2)],
    ]
    print(format_compact_table(hard_rows))

    print()
    print("Note: contributions are local leave-one-out deltas in a nonlinear model, not strict additive shares.")
    input("Press Enter to continue...")
