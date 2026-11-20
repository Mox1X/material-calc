#!/usr/bin/env python3

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from composition import parse_composition

MODULE_DIR = Path(__file__).resolve().parent
ELEMENTS_DIR = MODULE_DIR / 'elements'


@dataclass
class ElementData:
    symbol: str
    name: str
    atomic_radius_pm: float
    electronegativity: float | None
    melting_point_k: float
    shear_gpa: float
    standard_potential_v: float
    oxide_energy_kj_mol: float
    neutron_cross_section_barn: float
    crystal_structure: str
    covalent_radius_pm: float
    density_solid_kg_m3: float
    data_quality_score_0_1: float
    atomic_mass: float = 0.0


def electronegativity_gap(base: ElementData, solute: ElementData) -> float | None:
    if base.electronegativity is None or solute.electronegativity is None:
        return None
    return abs(base.electronegativity - solute.electronegativity)


QUALITY_WEIGHTS = {
    'reference': 1.0,
    'estimated': 0.65,
    'unknown': 0.35,
    'missing': 0.2,
}


def to_float(value: Any, default: Any = 0.0) -> Any:
    try:
        if value is None:
            return default
        number = float(value)
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def iter_quality_values(node: Any) -> List[str]:
    out: List[str] = []
    if isinstance(node, dict):
        for v in node.values():
            out.extend(iter_quality_values(v))
    elif isinstance(node, str):
        out.append(node.strip().lower())
    return out


def data_quality_score(data: Dict[str, Any]) -> float:
    values = iter_quality_values(data.get('data_quality', {}))
    if not values:
        return 0.5
    weights = [QUALITY_WEIGHTS.get(v, 0.5) for v in values]
    return max(0.0, min(1.0, sum(weights) / len(weights)))


def load_elements(elements_dir: Path | str | None = None) -> Dict[str, ElementData]:
    out: Dict[str, ElementData] = {}
    target_dir = Path(elements_dir) if elements_dir is not None else ELEMENTS_DIR
    if not target_dir.exists() or not target_dir.is_dir():
        raise FileNotFoundError(f'Elements directory not found: {target_dir}')

    for path in sorted(target_dir.glob('*.json')):
        data = json.loads(path.read_text(encoding='utf-8'))
        sym = data['symbol']
        out[sym] = ElementData(
            symbol=sym,
            name=data['name'],
            atomic_radius_pm=to_float(data['geometry'].get('atomic_radius_pm'), 140.0),
            electronegativity=to_float(data['chemical'].get('electronegativity_pauling'), None),
            melting_point_k=to_float(data['thermal'].get('melting_point_K'), 1000.0),
            shear_gpa=to_float(data['elastic'].get('shear_GPa'), 30.0),
            standard_potential_v=to_float(data['chemical'].get('standard_electrode_potential_V'), 0.0),
            oxide_energy_kj_mol=to_float(data['chemical'].get('oxide_formation_energy_kJ_mol'), -200.0),
            neutron_cross_section_barn=to_float(data['nuclear'].get('neutron_cross_section_barn'), 1.0),
            crystal_structure=str(data['crystallography']['crystal_structure_rt']),
            covalent_radius_pm=to_float(data['geometry'].get('covalent_radius_pm'), 120.0),
            density_solid_kg_m3=to_float(data['identification'].get('density_solid_kg_m3'), 5000.0),
            data_quality_score_0_1=data_quality_score(data),
            atomic_mass=to_float(data['identification'].get('atomic_mass')),
        )

    return out
