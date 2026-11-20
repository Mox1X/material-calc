#!python
"""Enrich element JSON files from multiple scientific sources.

Sources:
- mendeleev (python package)
- periodictable (python package)
- pymatgen (optional python package)
- Materials Project (mp-api, optional python package + API key)
- PubChem PUG REST Periodic Table endpoint
"""

from __future__ import annotations

import argparse
import json
import math
import os
import ssl
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import urlopen

MODULE_DIR = Path(__file__).resolve().parent
DEFAULT_ELEMENTS_DIR = MODULE_DIR / "elements"
DEFAULT_REPORT_FILE = MODULE_DIR / "artifacts" / "reports" / "enrich_report.json"


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError, OverflowError):
        return None


def _safe_json(url: str, timeout: int = 20, allow_insecure_tls: bool = False) -> Any:
    try:
        with urlopen(url, timeout=timeout) as r:
            return json.load(r)
    except ssl.SSLCertVerificationError:
        if not allow_insecure_tls:
            raise
        insecure_ctx = ssl._create_unverified_context()
        with urlopen(url, timeout=timeout, context=insecure_ctx) as r:
            return json.load(r)


def _normalize_value_to_si(field: str, value: Any) -> Tuple[Any, Optional[str]]:
    """Normalize known fields to SI/expected units used by this project.

    Returns: (normalized_value, conversion_note_or_none)
    """
    v = _to_float(value)
    if v is None:
        return value, None

    # Atomic number must stay integer.
    if field == "identification.atomic_number":
        iv = _to_int(v)
        return iv if iv is not None else value, None

    # Density expected in kg/m3. Common source unit: g/cm3.
    if field == "identification.density_solid_kg_m3":
        if 0.01 < v < 50.0:
            return v * 1000.0, "g/cm3 -> kg/m3 (x1000)"
        return v, None

    # Heat capacity expected in J/(kg*K). Common source unit: J/(g*K).
    if field == "thermal.specific_heat_capacity_J_kgK":
        if 0.01 < v < 20.0:
            return v * 1000.0, "J/(g*K) -> J/(kg*K) (x1000)"
        return v, None

    # Atomic/covalent radius expected in pm. Common alternative: Angstrom.
    if field in {"geometry.atomic_radius_pm", "geometry.covalent_radius_pm"}:
        if 0.1 < v < 10.0:
            return v * 100.0, "angstrom -> pm (x100)"
        return v, None

    # Elastic constants expected in GPa. Common alternative: MPa.
    if field in {"elastic.young_GPa", "elastic.shear_GPa", "elastic.bulk_GPa"}:
        if v > 1000.0:
            return v / 1000.0, "MPa -> GPa (/1000)"
        return v, None

    # Resistivity expected in Ohm*m. Common alternative: microOhm*cm.
    if field == "electrical.electrical_resistivity_Ohm_m":
        # Typical microOhm*cm values for conductors are often in 1..1e3 range.
        if 1.0 <= v <= 1e5:
            return v * 1e-8, "microOhm*cm -> Ohm*m (x1e-8)"
        return v, None

    return v, None


def _normalize_field_map_to_si(
    source_name: str,
    values: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    normalized: Dict[str, Any] = {}
    conversions: Dict[str, str] = {}
    for field, value in values.items():
        nv, note = _normalize_value_to_si(field, value)
        normalized[field] = nv
        if note:
            conversions[field] = f"{source_name}: {note}"
    return normalized, conversions


def _load_pubchem_periodic_table(allow_insecure_tls: bool = False) -> Dict[str, Dict[str, Any]]:
    url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/periodictable/JSON"
    data = _safe_json(url, allow_insecure_tls=allow_insecure_tls)
    table = data.get("Table", {})
    columns = table.get("Columns", {}).get("Column", [])
    rows = table.get("Row", [])
    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        cells = row.get("Cell", [])
        if len(cells) != len(columns):
            continue
        item = dict(zip(columns, cells))
        sym = item.get("Symbol")
        if not sym:
            continue
        out[str(sym)] = item
    return out


def collect_mendeleev(symbol: str) -> Tuple[Dict[str, Any], Dict[str, str]]:
    from mendeleev import element as md_element

    src: Dict[str, Any] = {}
    q: Dict[str, str] = {}
    el = md_element(symbol)

    src["identification.atomic_number"] = _to_int(getattr(el, "atomic_number", None))
    src["identification.atomic_mass"] = _to_float(getattr(el, "atomic_weight", None))
    dens = _to_float(getattr(el, "density", None))
    if dens is not None:
        src["identification.density_solid_kg_m3"] = dens * 1000.0
    src["geometry.atomic_radius_pm"] = _to_float(getattr(el, "atomic_radius", None))
    src["geometry.covalent_radius_pm"] = _to_float(getattr(el, "covalent_radius_cordero", None))
    lattice = getattr(el, "lattice_structure", None)
    if lattice:
        text = str(lattice).upper()
        mapping = {
            "BCC": "BCC",
            "FCC": "FCC",
            "HCP": "HEX",
            "HEXAGONAL": "HEX",
            "DIAMOND": "DIA",
        }
        src["crystallography.crystal_structure_rt"] = mapping.get(text, text)
    src["thermal.melting_point_K"] = _to_float(getattr(el, "melting_point", None))
    src["thermal.boiling_point_K"] = _to_float(getattr(el, "boiling_point", None))
    src["thermal.thermal_conductivity_W_mK"] = _to_float(getattr(el, "thermal_conductivity", None))
    src["thermal.specific_heat_capacity_J_kgK"] = _to_float(getattr(el, "specific_heat_capacity", None))
    src["chemical.electronegativity_pauling"] = _to_float(getattr(el, "en_pauling", None))

    oxidation = getattr(el, "oxistates", None)
    if oxidation is None:
        oxidation_states: List[int] = []
    else:
        oxidation_states = []
        for o in oxidation:
            v = _to_int(getattr(o, "oxidation_state", o))
            if v is not None:
                oxidation_states.append(v)
        oxidation_states = sorted(set(oxidation_states))
    if oxidation_states:
        src["chemical.valence_states"] = oxidation_states

    for k, v in list(src.items()):
        if v is None:
            del src[k]
        else:
            q[k] = "reference"
    return src, q


def collect_periodictable(symbol: str) -> Tuple[Dict[str, Any], Dict[str, str]]:
    import periodictable as pt

    src: Dict[str, Any] = {}
    q: Dict[str, str] = {}

    el = getattr(pt, symbol, None)
    if el is None:
        return src, q

    src["identification.atomic_number"] = _to_int(getattr(el, "number", None))
    src["identification.atomic_mass"] = _to_float(getattr(el, "mass", None))
    dens = _to_float(getattr(el, "density", None))
    if dens is not None:
        src["identification.density_solid_kg_m3"] = dens * 1000.0
    melt = _to_float(getattr(el, "melting_point", None))
    boil = _to_float(getattr(el, "boiling_point", None))
    if melt is not None:
        src["thermal.melting_point_K"] = melt
    if boil is not None:
        src["thermal.boiling_point_K"] = boil

    neutron = None
    neutron_obj = getattr(el, "neutron", None)
    if neutron_obj is not None:
        neutron = _to_float(getattr(neutron_obj, "absorption", None))
    if neutron is not None:
        src["nuclear.neutron_cross_section_barn"] = neutron

    for k, v in list(src.items()):
        if v is None:
            del src[k]
        else:
            q[k] = "reference"
    return src, q


def collect_pymatgen(symbol: str) -> Tuple[Dict[str, Any], Dict[str, str]]:
    from pymatgen.core import Element as PMElement

    src: Dict[str, Any] = {}
    q: Dict[str, str] = {}

    el = PMElement(symbol)
    x = _to_float(getattr(el, "X", None))
    if x is not None:
        src["chemical.electronegativity_pauling"] = x

    ar = _to_float(getattr(el, "atomic_radius", None))
    if ar is not None:
        src["geometry.atomic_radius_pm"] = ar * 100.0
    cr = _to_float(getattr(el, "atomic_radius_calculated", None))
    if cr is not None:
        src["geometry.covalent_radius_pm"] = cr * 100.0

    ox = getattr(el, "common_oxidation_states", None) or getattr(el, "oxidation_states", None)
    if ox:
        vals = sorted({int(v) for v in ox})
        src["chemical.valence_states"] = vals

    for k in src:
        q[k] = "reference"
    return src, q


def collect_mp_api(symbol: str, api_key: str) -> Tuple[Dict[str, Any], Dict[str, str]]:
    from mp_api.client import MPRester

    src: Dict[str, Any] = {}
    q: Dict[str, str] = {}

    with MPRester(api_key=api_key, mute_progress_bars=True) as mpr:
        docs = mpr.materials.summary.search(
            elements=[symbol],
            num_elements=(1, 1),
            theoretical=False,
            fields=["formula_pretty", "symmetry", "density", "energy_above_hull"],
        )
    docs = [d for d in docs if str(getattr(d, "formula_pretty", "")) == symbol]
    docs.sort(key=lambda d: float(getattr(d, "energy_above_hull", 999.0) or 999.0))
    if not docs:
        return src, q
    best = docs[0]

    dens = _to_float(getattr(best, "density", None))
    if dens is not None:
        src["identification.density_solid_kg_m3"] = dens * 1000.0
        q["identification.density_solid_kg_m3"] = "reference"

    symm = getattr(best, "symmetry", None)
    crystal = None
    if symm is not None:
        crystal = getattr(symm, "crystal_system", None) or getattr(symm, "symbol", None)
    if crystal:
        text = str(crystal).upper()
        mapping = {
            "CUBIC": "BCC",
            "HEXAGONAL": "HEX",
            "TRIGONAL": "HEX",
            "TETRAGONAL": "BCT",
            "ORTHORHOMBIC": "ORT",
            "MONOCLINIC": "MON",
            "TRICLINIC": "TRI",
        }
        src["crystallography.crystal_structure_rt"] = mapping.get(text, text)
        q["crystallography.crystal_structure_rt"] = "estimated"

    return src, q


def collect_pubchem(symbol: str, table: Dict[str, Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, str]]:
    src: Dict[str, Any] = {}
    q: Dict[str, str] = {}
    row = table.get(symbol)
    if not row:
        return src, q

    src["identification.atomic_number"] = _to_int(row.get("AtomicNumber"))
    src["identification.atomic_mass"] = _to_float(row.get("AtomicMass"))
    src["chemical.electronegativity_pauling"] = _to_float(row.get("Electronegativity"))
    src["geometry.atomic_radius_pm"] = _to_float(row.get("AtomicRadius"))
    src["thermal.melting_point_K"] = _to_float(row.get("MeltingPoint"))
    src["thermal.boiling_point_K"] = _to_float(row.get("BoilingPoint"))
    dens = _to_float(row.get("Density"))
    if dens is not None:
        src["identification.density_solid_kg_m3"] = dens * 1000.0

    ox = row.get("OxidationStates")
    if isinstance(ox, str) and ox.strip():
        vals: List[int] = []
        for part in ox.split(","):
            part = part.strip().replace("+", "")
            v = _to_int(part)
            if v is not None:
                vals.append(v)
        vals = sorted(set(vals))
        if vals:
            src["chemical.valence_states"] = vals

    for k, v in list(src.items()):
        if v is None:
            del src[k]
        else:
            q[k] = "reference"
    return src, q


def _set_nested(d: Dict[str, Any], dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    cur = d
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value


def _update_quality(d: Dict[str, Any], dotted_key: str, quality: str) -> None:
    qroot = d.setdefault("data_quality", {})
    parts = dotted_key.split(".")
    cur = qroot
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = quality


def apply_updates(
    payload: Dict[str, Any],
    field_values: Dict[str, Any],
    field_quality: Dict[str, str],
    field_sources: Dict[str, str],
) -> Tuple[Dict[str, Any], int]:
    updated = json.loads(json.dumps(payload))
    count = 0
    for field, value in field_values.items():
        if value is None:
            continue
        _set_nested(updated, field, value)
        _update_quality(updated, field, field_quality.get(field, "estimated"))
        count += 1
    notes = updated.setdefault("source_notes", {})
    notes["field_sources"] = field_sources
    return updated, count


def merge_by_priority(
    collectors: List[Tuple[str, Dict[str, Any], Dict[str, str]]]
) -> Tuple[Dict[str, Any], Dict[str, str], Dict[str, str], Dict[str, str]]:
    values: Dict[str, Any] = {}
    quality: Dict[str, str] = {}
    sources: Dict[str, str] = {}
    conversions: Dict[str, str] = {}
    for source_name, src_values, src_quality in collectors:
        src_values, src_conversions = _normalize_field_map_to_si(source_name, src_values)
        conversions.update(src_conversions)
        for k, v in src_values.items():
            if v is None or k in values:
                continue
            values[k] = v
            quality[k] = src_quality.get(k, "estimated")
            sources[k] = source_name
    return values, quality, sources, conversions


def process_element_file(
    path: Path,
    pubchem_table: Dict[str, Dict[str, Any]],
    mp_api_key: Optional[str],
) -> Tuple[Dict[str, Any], int, List[str], Dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    symbol = payload.get("symbol")
    if not symbol:
        return payload, 0, ["missing symbol"], {}

    errors: List[str] = []
    collectors: List[Tuple[str, Dict[str, Any], Dict[str, str]]] = []

    try:
        v, q = collect_mendeleev(symbol)
        collectors.append(("mendeleev", v, q))
    except Exception as exc:
        errors.append(f"mendeleev: {type(exc).__name__}: {exc}")

    try:
        v, q = collect_pymatgen(symbol)
        collectors.append(("pymatgen", v, q))
    except Exception as exc:
        errors.append(f"pymatgen: {type(exc).__name__}: {exc}")

    try:
        v, q = collect_periodictable(symbol)
        collectors.append(("periodictable", v, q))
    except Exception as exc:
        errors.append(f"periodictable: {type(exc).__name__}: {exc}")

    try:
        v, q = collect_pubchem(symbol, pubchem_table)
        collectors.append(("pubchem", v, q))
    except Exception as exc:
        errors.append(f"pubchem: {type(exc).__name__}: {exc}")

    if mp_api_key:
        try:
            v, q = collect_mp_api(symbol, mp_api_key)
            collectors.append(("mp_api", v, q))
        except Exception as exc:
            errors.append(f"mp_api: {type(exc).__name__}: {exc}")

    values, quality, sources, conversions = merge_by_priority(collectors)
    updated, count = apply_updates(payload, values, quality, sources)
    return updated, count, errors, conversions


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich element JSON files from external sources")
    parser.add_argument("--elements-dir", type=Path, default=DEFAULT_ELEMENTS_DIR)
    parser.add_argument("--output-dir", type=Path, default=None, help="Write updated files to this directory")
    parser.add_argument("--write", action="store_true", help="Enable write mode (otherwise dry-run)")
    parser.add_argument("--symbols", type=str, default="", help="Comma-separated symbols filter, e.g. Fe,C,Ti")
    parser.add_argument("--mp-api-key", type=str, default="", help="Materials Project API key")
    parser.add_argument("--report-file", type=Path, default=DEFAULT_REPORT_FILE)
    parser.add_argument(
        "--insecure-tls",
        action="store_true",
        help="Allow insecure TLS fallback for source downloads (not recommended)",
    )
    args = parser.parse_args()

    elements_dir: Path = args.elements_dir
    if not elements_dir.exists():
        raise FileNotFoundError(f"Elements directory not found: {elements_dir}")

    symbols_filter = {s.strip() for s in args.symbols.split(",") if s.strip()}
    mp_api_key = args.mp_api_key or os.getenv("MP_API_KEY") or ""

    pubchem_table: Dict[str, Dict[str, Any]] = {}
    pubchem_error = None
    try:
        pubchem_table = _load_pubchem_periodic_table(allow_insecure_tls=bool(args.insecure_tls))
    except Exception as exc:
        pubchem_error = f"{type(exc).__name__}: {exc}"

    files = sorted(elements_dir.glob("*.json"))
    if symbols_filter:
        filtered = []
        for p in files:
            try:
                symbol = json.loads(p.read_text(encoding="utf-8")).get("symbol")
            except Exception:
                symbol = None
            if symbol in symbols_filter:
                filtered.append(p)
        files = filtered

    output_dir = args.output_dir
    if args.write and output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

    report: Dict[str, Any] = {
        "elements_dir": str(elements_dir),
        "output_dir": str(output_dir) if output_dir else None,
        "write_mode": bool(args.write),
        "pubchem_loaded": bool(pubchem_table),
        "pubchem_error": pubchem_error,
        "insecure_tls": bool(args.insecure_tls),
        "mp_api_enabled": bool(mp_api_key),
        "elements_processed": 0,
        "elements_written": 0,
        "updated_fields_total": 0,
        "converted_fields_total": 0,
        "items": [],
    }

    for path in files:
        updated, count, errors, conversions = process_element_file(path, pubchem_table, mp_api_key if mp_api_key else None)
        report["elements_processed"] += 1
        report["updated_fields_total"] += count
        report["converted_fields_total"] += len(conversions)
        item = {
            "file": str(path),
            "updated_fields": count,
            "converted_fields": len(conversions),
            "conversions": conversions,
            "errors": errors,
        }
        report["items"].append(item)

        if not args.write:
            continue
        if output_dir is None:
            target = path
        else:
            target = output_dir / path.name
        target.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["elements_written"] += 1

    args.report_file.parent.mkdir(parents=True, exist_ok=True)
    args.report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "elements_processed": report["elements_processed"],
                "elements_written": report["elements_written"],
                "updated_fields_total": report["updated_fields_total"],
                "converted_fields_total": report["converted_fields_total"],
                "report_file": str(args.report_file),
                "write_mode": bool(args.write),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
