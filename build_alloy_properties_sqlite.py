#!/usr/bin/env python3
"""Batch-calculate alloy properties and persist them to SQLite."""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from alloy_engine import compatibility_report
from alloy_models import load_elements
from composition import parse_composition
from report_types import estimate_value


ALL_ALLOY_MARKS: List[str] = [
    "У8",
    "У10",
    "У12",
    "У8А",
    "У10А",
    "У12А",
    "45",
    "65Г",
    "9ХС",
    "ХВГ",
    "Х12МФ",
    "Х12Ф1",
    "4Х5МФС",
    "5ХНМ",
    "9ХФ",
    "ХВСГ",
    "6ХВ2С",
    "7Х3",
    "8Х3",
    "Х12",
    "9Х1",
    "Х6ВФ",
    "Р18",
    "Р6М5",
    "Р9",
    "Р12",
    "Р9Ф5",
    "Р18Ф2",
    "Р6М5К5",
    "Р9К5",
    "Р9М4К8",
    "Р12Ф3",
    "Р18К5Ф2",
    "Р6М5Ф3",
    "Р10К5Ф5",
    "Р9М4К8",
    "ВК8",
    "ВК6",
    "ВК4",
    "ВК10",
    "ВК15",
    "Т15К6",
    "Т5К10",
    "Т30К4",
    "Т14К8",
    "ТТ10К8Б",
    "ТТ7К12",
    "Л63",
    "ЛС59",
    "ЛС59-1",
    "Л96",
    "БрОФ6.5-0.15",
    "БрАЖ9-4",
    "БрОЦС5-5-5",
    "БрАМц9-2",
    "БрБ2",
    "Д16",
    "Д1",
    "АК12",
    "АК5М2",
    "СЧ15",
    "СЧ20",
    "СЧ25",
    "СЧ30",
    "СЧ35",
    "КЧ30-6",
    "КЧ35-10",
    "КЧ37-12",
    "ВЧ40",
    "ВЧ50",
    "15Х2НМФА",
    "30ХН3М2ФА",
    "40ХН2МА",
    "25Х2МФА",
    "14ХМНДФР",
    "10ГН2МФА",
    "30ХГСНА",
    "38Х2Н2МА",
    "45ХН2МФА",
    "18Х2Н4ВА",
    "35ХН3МФА",
]


NOMINAL_WT_COMPOSITIONS: Dict[str, Dict[str, float]] = {
    # Carbon / low-alloy tool steels (nominal wt.% approximations)
    "У8": {"Fe": 98.6, "C": 0.8, "Mn": 0.35, "Si": 0.25},
    "У10": {"Fe": 98.4, "C": 1.0, "Mn": 0.35, "Si": 0.25},
    "У12": {"Fe": 98.2, "C": 1.2, "Mn": 0.35, "Si": 0.25},
    "У8А": {"Fe": 98.6, "C": 0.8, "Mn": 0.35, "Si": 0.25},
    "У10А": {"Fe": 98.4, "C": 1.0, "Mn": 0.35, "Si": 0.25},
    "У12А": {"Fe": 98.2, "C": 1.2, "Mn": 0.35, "Si": 0.25},
    "45": {"Fe": 98.65, "C": 0.45, "Mn": 0.65, "Si": 0.25},
    "65Г": {"Fe": 98.0, "C": 0.65, "Mn": 1.1, "Si": 0.25},
    "9ХС": {"Fe": 96.25, "C": 0.9, "Cr": 1.0, "Si": 1.2, "Mn": 0.35, "V": 0.3},
    "ХВГ": {"Fe": 95.5, "C": 1.0, "Cr": 1.0, "W": 1.2, "Mn": 1.0, "Si": 0.3},
    "Х12МФ": {"Fe": 85.0, "C": 1.55, "Cr": 12.0, "Mo": 0.6, "V": 0.25, "Mn": 0.3, "Si": 0.3},
    "Х12Ф1": {"Fe": 84.9, "C": 1.5, "Cr": 12.0, "V": 1.0, "Mn": 0.3, "Si": 0.3},
    "4Х5МФС": {"Fe": 91.4, "C": 0.4, "Cr": 5.0, "Mo": 1.3, "V": 0.5, "Si": 1.0, "Mn": 0.4},
    "5ХНМ": {"Fe": 96.1, "C": 0.5, "Cr": 0.8, "Ni": 1.6, "Mo": 0.3, "Mn": 0.4, "Si": 0.3},
    "9ХФ": {"Fe": 97.3, "C": 0.9, "Cr": 1.0, "V": 0.2, "Mn": 0.3, "Si": 0.3},
    "ХВСГ": {"Fe": 95.0, "C": 1.0, "Cr": 1.0, "W": 1.0, "Si": 1.0, "Mn": 1.0},
    "6ХВ2С": {"Fe": 95.0, "C": 0.6, "Cr": 1.0, "W": 2.0, "Si": 1.0, "Mn": 0.4},
    "7Х3": {"Fe": 95.6, "C": 0.7, "Cr": 3.0, "Mn": 0.4, "Si": 0.3},
    "8Х3": {"Fe": 95.5, "C": 0.8, "Cr": 3.0, "Mn": 0.4, "Si": 0.3},
    "Х12": {"Fe": 85.9, "C": 1.5, "Cr": 12.0, "Mn": 0.3, "Si": 0.3},
    "9Х1": {"Fe": 97.4, "C": 0.9, "Cr": 1.0, "Mn": 0.4, "Si": 0.3},
    "Х6ВФ": {"Fe": 90.7, "C": 1.0, "Cr": 6.0, "W": 1.2, "V": 0.5, "Mn": 0.3, "Si": 0.3},
    # High-speed steels (nominal wt.% approximations)
    "Р18": {"Fe": 76.22, "C": 0.78, "W": 18.0, "Cr": 4.0, "V": 1.0},
    "Р6М5": {"Fe": 82.14, "C": 0.86, "W": 6.0, "Mo": 5.0, "Cr": 4.0, "V": 2.0},
    "Р9": {"Fe": 84.15, "C": 0.85, "W": 9.0, "Cr": 4.0, "V": 2.0},
    "Р12": {"Fe": 81.65, "C": 0.85, "W": 12.0, "Cr": 4.0, "V": 1.5},
    "Р9Ф5": {"Fe": 81.1, "C": 0.9, "W": 9.0, "Cr": 4.0, "V": 5.0},
    "Р18Ф2": {"Fe": 75.2, "C": 0.8, "W": 18.0, "Cr": 4.0, "V": 2.0},
    "Р6М5К5": {"Fe": 77.1, "C": 0.9, "W": 6.0, "Mo": 5.0, "Cr": 4.0, "V": 2.0, "Co": 5.0},
    "Р9К5": {"Fe": 79.1, "C": 0.9, "W": 9.0, "Cr": 4.0, "V": 2.0, "Co": 5.0},
    "Р9М4К8": {"Fe": 72.1, "C": 0.9, "W": 9.0, "Mo": 4.0, "Cr": 4.0, "V": 2.0, "Co": 8.0},
    "Р12Ф3": {"Fe": 80.1, "C": 0.9, "W": 12.0, "Cr": 4.0, "V": 3.0},
    "Р18К5Ф2": {"Fe": 70.2, "C": 0.8, "W": 18.0, "Cr": 4.0, "V": 2.0, "Co": 5.0},
    "Р6М5Ф3": {"Fe": 81.1, "C": 0.9, "W": 6.0, "Mo": 5.0, "Cr": 4.0, "V": 3.0},
    "Р10К5Ф5": {"Fe": 75.1, "C": 0.9, "W": 10.0, "Cr": 4.0, "V": 5.0, "Co": 5.0},
    # Copper alloys
    "Л63": {"Cu": 63.0, "Zn": 37.0},
    "ЛС59": {"Cu": 59.0, "Zn": 40.0, "Pb": 1.0},
    "ЛС59-1": {"Cu": 59.0, "Zn": 40.0, "Pb": 1.0},
    "Л96": {"Cu": 96.0, "Zn": 4.0},
    "БрОФ6.5-0.15": {"Cu": 93.35, "Sn": 6.5, "P": 0.15},
    "БрАЖ9-4": {"Cu": 87.0, "Al": 9.0, "Fe": 4.0},
    "БрОЦС5-5-5": {"Cu": 85.0, "Sn": 5.0, "Zn": 5.0, "Pb": 5.0},
    "БрАМц9-2": {"Cu": 89.0, "Al": 9.0, "Mn": 2.0},
    "БрБ2": {"Cu": 98.0, "Be": 2.0},
    # Aluminum alloys
    "Д16": {"Al": 93.5, "Cu": 4.4, "Mg": 1.5, "Mn": 0.6},
    "Д1": {"Al": 94.5, "Cu": 4.3, "Mg": 0.6, "Mn": 0.6},
    "АК12": {"Al": 88.0, "Si": 12.0},
    "АК5М2": {"Al": 93.0, "Si": 5.0, "Cu": 2.0},
    # Cast irons (nominal wt.% approximations)
    "СЧ15": {"Fe": 93.37, "C": 3.5, "Si": 2.3, "Mn": 0.6, "P": 0.15, "S": 0.08},
    "СЧ20": {"Fe": 93.57, "C": 3.4, "Si": 2.1, "Mn": 0.7, "P": 0.15, "S": 0.08},
    "СЧ25": {"Fe": 93.81, "C": 3.3, "Si": 1.9, "Mn": 0.8, "P": 0.12, "S": 0.07},
    "СЧ30": {"Fe": 94.04, "C": 3.2, "Si": 1.7, "Mn": 0.9, "P": 0.1, "S": 0.06},
    "СЧ35": {"Fe": 94.27, "C": 3.1, "Si": 1.5, "Mn": 1.0, "P": 0.08, "S": 0.05},
    "КЧ30-6": {"Fe": 95.44, "C": 2.5, "Si": 1.3, "Mn": 0.6, "P": 0.12, "S": 0.04},
    "КЧ35-10": {"Fe": 95.66, "C": 2.4, "Si": 1.2, "Mn": 0.6, "P": 0.1, "S": 0.04},
    "КЧ37-12": {"Fe": 95.86, "C": 2.3, "Si": 1.1, "Mn": 0.6, "P": 0.1, "S": 0.04},
    "ВЧ40": {"Fe": 93.37, "C": 3.6, "Si": 2.5, "Mn": 0.4, "Mg": 0.05, "P": 0.06, "S": 0.02},
    "ВЧ50": {"Fe": 93.57, "C": 3.5, "Si": 2.4, "Mn": 0.4, "Mg": 0.06, "P": 0.05, "S": 0.02},
    # Structural alloy steels (nominal wt.% approximations)
    "15Х2НМФА": {"Fe": 95.4, "C": 0.15, "Cr": 2.0, "Ni": 1.0, "Mo": 0.5, "V": 0.15, "Mn": 0.5, "Si": 0.3},
    "30ХН3М2ФА": {"Fe": 92.7, "C": 0.3, "Cr": 1.0, "Ni": 3.0, "Mo": 2.0, "V": 0.2, "Mn": 0.5, "Si": 0.3},
    "40ХН2МА": {"Fe": 95.4, "C": 0.4, "Cr": 1.0, "Ni": 2.0, "Mo": 0.3, "Mn": 0.6, "Si": 0.3},
    "25Х2МФА": {"Fe": 96.3, "C": 0.25, "Cr": 2.0, "Mo": 0.5, "V": 0.15, "Mn": 0.5, "Si": 0.3},
    "14ХМНДФР": {
        "Fe": 95.857,
        "C": 0.14,
        "Cr": 1.0,
        "Mo": 0.5,
        "Ni": 1.0,
        "Cu": 0.5,
        "V": 0.1,
        "Mn": 0.6,
        "Si": 0.3,
        "B": 0.003,
    },
    "10ГН2МФА": {"Fe": 95.75, "C": 0.1, "Mn": 1.0, "Ni": 2.0, "Mo": 0.5, "V": 0.1, "Si": 0.25, "Cr": 0.3},
    "30ХГСНА": {"Fe": 95.7, "C": 0.3, "Cr": 1.0, "Mn": 1.0, "Si": 1.0, "Ni": 1.0},
    "38Х2Н2МА": {"Fe": 94.52, "C": 0.38, "Cr": 2.0, "Ni": 2.0, "Mo": 0.3, "Mn": 0.5, "Si": 0.3},
    "45ХН2МФА": {"Fe": 95.15, "C": 0.45, "Cr": 1.0, "Ni": 2.0, "Mo": 0.5, "V": 0.1, "Mn": 0.5, "Si": 0.3},
    "18Х2Н4ВА": {"Fe": 92.17, "C": 0.18, "Cr": 2.0, "Ni": 4.0, "W": 1.0, "V": 0.1, "Mn": 0.3, "Si": 0.25},
    "35ХН3МФА": {"Fe": 94.25, "C": 0.35, "Cr": 1.0, "Ni": 3.0, "Mo": 0.5, "V": 0.1, "Mn": 0.5, "Si": 0.3},
}


ATOMIC_WEIGHTS = {
    "C": 12.011,
    "Co": 58.933194,
    "Nb": 92.90637,
    "Ta": 180.94788,
    "Ti": 47.867,
    "W": 183.84,
}

CARBIDES = {
    "WC": {"W": 1.0, "C": 1.0},
    "TiC": {"Ti": 1.0, "C": 1.0},
    "TaC": {"Ta": 1.0, "C": 1.0},
    "NbC": {"Nb": 1.0, "C": 1.0},
}


@dataclass
class BatchRow:
    input_order: int
    alloy_mark: str
    source_composition_wt_json: str
    composition_normalized_json: str
    base_element_symbol: str
    material_regime: str | None
    schema_version: int
    status: str
    vickers_hardness_hv: float | None
    melting_point_k: float | None
    solidus_k: float | None
    liquidus_k: float | None
    density_kg_m3: float | None
    neutron_cross_section_barn: float | None
    brittleness_index_0_1: float | None
    corrosion_susceptibility_index_0_1: float | None
    confidence_index_0_1: float | None
    solid_phase_feasibility_0_1: float | None
    castability_index_0_1: float | None
    carbide_index: float | None
    carbide_bonus_hv: float | None
    warnings_json: str
    full_report_json: str
    created_at_utc: str


def _add_component(target: Dict[str, float], symbol: str, wt_percent: float) -> None:
    if wt_percent <= 0:
        return
    target[symbol] = target.get(symbol, 0.0) + wt_percent


def _expand_carbide_formula(phase: str, wt_percent: float) -> Dict[str, float]:
    formula = CARBIDES[phase]
    molar_mass = sum(ATOMIC_WEIGHTS[sym] * count for sym, count in formula.items())
    expanded: Dict[str, float] = {}
    for sym, count in formula.items():
        mass_share = (ATOMIC_WEIGHTS[sym] * count) / molar_mass
        expanded[sym] = wt_percent * mass_share
    return expanded


def _make_hardmetal_from_phase_mix(phases: Dict[str, float]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for phase, wt_percent in phases.items():
        if phase == "Co":
            _add_component(out, "Co", wt_percent)
            continue
        expanded = _expand_carbide_formula(phase, wt_percent)
        for sym, part in expanded.items():
            _add_component(out, sym, part)
    return out


def hardmetal_composition(mark: str) -> Dict[str, float]:
    if mark.startswith("ВК"):
        co = float(mark[2:])
        if not (0.0 < co < 100.0):
            raise ValueError(f"Bad VK cobalt value in mark '{mark}'")
        return _make_hardmetal_from_phase_mix({"WC": 100.0 - co, "Co": co})

    if mark == "Т15К6":
        return _make_hardmetal_from_phase_mix({"WC": 79.0, "TiC": 15.0, "Co": 6.0})
    if mark == "Т5К10":
        return _make_hardmetal_from_phase_mix({"WC": 85.0, "TiC": 5.0, "Co": 10.0})
    if mark == "Т30К4":
        return _make_hardmetal_from_phase_mix({"WC": 66.0, "TiC": 30.0, "Co": 4.0})
    if mark == "Т14К8":
        return _make_hardmetal_from_phase_mix({"WC": 78.0, "TiC": 14.0, "Co": 8.0})
    if mark == "ТТ10К8Б":
        return _make_hardmetal_from_phase_mix({"WC": 82.0, "TiC": 6.0, "TaC": 3.0, "NbC": 1.0, "Co": 8.0})
    if mark == "ТТ7К12":
        return _make_hardmetal_from_phase_mix({"WC": 81.0, "TiC": 4.0, "TaC": 3.0, "Co": 12.0})

    raise KeyError(mark)


def nominal_wt_composition(mark: str) -> Dict[str, float]:
    if mark in NOMINAL_WT_COMPOSITIONS:
        return dict(NOMINAL_WT_COMPOSITIONS[mark])
    try:
        return hardmetal_composition(mark)
    except KeyError as exc:
        raise KeyError(f"No nominal composition mapping for alloy mark '{mark}'") from exc


def composition_to_string(comp_wt: Dict[str, float]) -> str:
    return ",".join(f"{sym}:{value:.8g}" for sym, value in sorted(comp_wt.items()))


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS alloy_properties")
    conn.execute("DROP TABLE IF EXISTS alloy_property_failures")
    conn.execute(
        """
        CREATE TABLE alloy_properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            input_order INTEGER NOT NULL,
            alloy_mark TEXT NOT NULL,
            source_composition_wt_json TEXT NOT NULL,
            composition_normalized_json TEXT NOT NULL,
            base_element_symbol TEXT NOT NULL,
            material_regime TEXT,
            schema_version INTEGER NOT NULL,
            status TEXT NOT NULL,
            vickers_hardness_hv REAL,
            melting_point_k REAL,
            solidus_k REAL,
            liquidus_k REAL,
            density_kg_m3 REAL,
            neutron_cross_section_barn REAL,
            brittleness_index_0_1 REAL,
            corrosion_susceptibility_index_0_1 REAL,
            confidence_index_0_1 REAL,
            solid_phase_feasibility_0_1 REAL,
            castability_index_0_1 REAL,
            carbide_index REAL,
            carbide_bonus_hv REAL,
            warnings_json TEXT NOT NULL,
            full_report_json TEXT NOT NULL,
            created_at_utc TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE alloy_property_failures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            input_order INTEGER NOT NULL,
            alloy_mark TEXT NOT NULL,
            error_text TEXT NOT NULL,
            created_at_utc TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX idx_alloy_properties_mark ON alloy_properties(alloy_mark)")


def serialize(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def calculate_rows(
    alloy_marks: Iterable[str],
    *,
    state: str,
    env: str,
    temperature_k: float,
    oxygen_activity: float,
    regime: str,
    k_hardening: float,
) -> Tuple[List[BatchRow], List[Tuple[int, str, str, str]]]:
    element_db = load_elements()
    created_at = utc_now_iso()
    rows: List[BatchRow] = []
    failures: List[Tuple[int, str, str, str]] = []

    for idx, mark in enumerate(alloy_marks, start=1):
        try:
            wt_comp = nominal_wt_composition(mark)
            composition = parse_composition(composition_to_string(wt_comp))
            report = compatibility_report(
                composition,
                element_db,
                k_hardening=k_hardening,
                material_state=state,
                env=env,
                temperature_k=temperature_k,
                oxygen_activity=oxygen_activity,
                regime_override=regime,
            )
            if report["status"] == "invalid":
                raise ValueError(report["diagnostics"][0]["message"])
            details = report.get("model_details", {})
            hardness_model = details.get("hardness_model", {})
            rows.append(
                BatchRow(
                    input_order=idx,
                    alloy_mark=mark,
                    source_composition_wt_json=serialize(wt_comp),
                    composition_normalized_json=serialize(report["composition_normalized"]),
                    base_element_symbol=max(sorted(composition), key=composition.get),
                    material_regime=report["classification"]["regime"],
                    schema_version=report["schema_version"],
                    status=report["status"],
                    vickers_hardness_hv=estimate_value(report, "vickers_hardness_hv"),
                    melting_point_k=estimate_value(report, "melting_point_k"),
                    solidus_k=estimate_value(report, "solidus_k"),
                    liquidus_k=estimate_value(report, "liquidus_k"),
                    density_kg_m3=estimate_value(report, "density_kg_m3"),
                    neutron_cross_section_barn=estimate_value(report, "neutron_cross_section_barn"),
                    brittleness_index_0_1=details.get("hume_rothery", {}).get("brittleness_index_0_1"),
                    corrosion_susceptibility_index_0_1=estimate_value(report, "corrosion_susceptibility_index_0_1"),
                    confidence_index_0_1=details.get("confidence_index_0_1"),
                    solid_phase_feasibility_0_1=report["feasibility"]["solid_phase_index"],
                    castability_index_0_1=hardness_model.get("castability_index_0_1"),
                    carbide_index=hardness_model.get("carbide_index"),
                    carbide_bonus_hv=hardness_model.get("carbide_bonus_hv"),
                    warnings_json=serialize(report["diagnostics"]),
                    full_report_json=serialize(report),
                    created_at_utc=created_at,
                )
            )
        except Exception as exc:
            failures.append((idx, mark, str(exc), created_at))

    return rows, failures


def write_rows(conn: sqlite3.Connection, rows: List[BatchRow], failures: List[Tuple[int, str, str, str]]) -> None:
    conn.executemany(
        """
        INSERT INTO alloy_properties (
            input_order,
            alloy_mark,
            source_composition_wt_json,
            composition_normalized_json,
            base_element_symbol,
            material_regime,
            schema_version,
            status,
            vickers_hardness_hv,
            melting_point_k,
            solidus_k,
            liquidus_k,
            density_kg_m3,
            neutron_cross_section_barn,
            brittleness_index_0_1,
            corrosion_susceptibility_index_0_1,
            confidence_index_0_1,
            solid_phase_feasibility_0_1,
            castability_index_0_1,
            carbide_index,
            carbide_bonus_hv,
            warnings_json,
            full_report_json,
            created_at_utc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row.input_order,
                row.alloy_mark,
                row.source_composition_wt_json,
                row.composition_normalized_json,
                row.base_element_symbol,
                row.material_regime,
                row.schema_version,
                row.status,
                row.vickers_hardness_hv,
                row.melting_point_k,
                row.solidus_k,
                row.liquidus_k,
                row.density_kg_m3,
                row.neutron_cross_section_barn,
                row.brittleness_index_0_1,
                row.corrosion_susceptibility_index_0_1,
                row.confidence_index_0_1,
                row.solid_phase_feasibility_0_1,
                row.castability_index_0_1,
                row.carbide_index,
                row.carbide_bonus_hv,
                row.warnings_json,
                row.full_report_json,
                row.created_at_utc,
            )
            for row in rows
        ],
    )
    conn.executemany(
        """
        INSERT INTO alloy_property_failures (
            input_order,
            alloy_mark,
            error_text,
            created_at_utc
        ) VALUES (?, ?, ?, ?)
        """,
        failures,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build SQLite table with calculated properties for predefined alloy marks.")
    parser.add_argument("--db", default="artifacts/alloy_properties.sqlite", help="Target SQLite file path.")
    parser.add_argument("--state", choices=["raw", "tempered", "quenched", "potential"], default="raw")
    parser.add_argument("--env", choices=["air", "water", "acid", "vacuum"], default="air")
    parser.add_argument("--temperature-k", type=float, default=298.15)
    parser.add_argument("--oxygen-activity", type=float, default=0.21)
    parser.add_argument(
        "--regime",
        choices=["auto", "steel", "cast_iron", "cermet", "refractory", "nonferrous"],
        default="auto",
    )
    parser.add_argument("--k-hardening", type=float, default=1.0)
    parser.add_argument("--dedupe", action="store_true", help="Drop duplicate marks from the source list before calculations.")
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    oxygen_activity = max(0.0, min(1.0, args.oxygen_activity))

    alloy_marks = list(dict.fromkeys(ALL_ALLOY_MARKS)) if args.dedupe else list(ALL_ALLOY_MARKS)

    rows, failures = calculate_rows(
        alloy_marks,
        state=args.state,
        env=args.env,
        temperature_k=args.temperature_k,
        oxygen_activity=oxygen_activity,
        regime=args.regime,
        k_hardening=args.k_hardening,
    )

    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        init_db(conn)
        write_rows(conn, rows, failures)

    print(f"SQLite DB: {db_path.resolve()}")
    print(f"Requested marks: {len(alloy_marks)}")
    print(f"Calculated rows: {len(rows)}")
    print(f"Failures: {len(failures)}")
    if failures:
        print("Failed marks:")
        for idx, mark, error_text, _ in failures:
            print(f"  {idx:>3} {mark}: {error_text}")


if __name__ == "__main__":
    main()

