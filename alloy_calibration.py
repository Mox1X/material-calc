#!/usr/bin/env python3

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

from alloy_engine import compatibility_report
from alloy_models import ElementData
from composition import parse_composition
from report_types import estimate_value


def load_calibration_cases(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(payload, list):
        raise ValueError('Calibration file must be a JSON list')
    return payload


def _as_float(value: Any, field_path: str) -> float:
    try:
        number = float(value)
        if not math.isfinite(number):
            raise ValueError
        return number
    except (TypeError, ValueError):
        raise ValueError(f"Calibration field '{field_path}' must be numeric")


def _prepare_calibration_cases(
    cases: List[Dict[str, Any]],
    material_state: str,
    env: str,
    temperature_k: float,
    oxygen_activity: float,
) -> List[Dict[str, Any]]:
    prepared: List[Dict[str, Any]] = []
    hv_target_found = False
    for idx, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            raise ValueError(f'Calibration case #{idx} must be a JSON object')
        if 'composition' not in case:
            raise ValueError(f"Calibration case #{idx} is missing required field 'composition'")

        composition_raw = case.get('composition')
        if not isinstance(composition_raw, str) or not composition_raw.strip():
            raise ValueError(f"Calibration case #{idx} field 'composition' must be a non-empty string")
        try:
            composition = parse_composition(composition_raw)
        except ValueError as exc:
            raise ValueError(f'Calibration case #{idx} has invalid composition: {exc}')

        target = case.get('target', {})
        if target is None:
            target = {}
        if not isinstance(target, dict):
            raise ValueError(f"Calibration case #{idx} field 'target' must be an object")

        target_hv = None
        if 'hv' in target:
            target_hv = _as_float(target.get('hv'), f'case[{idx}].target.hv')
            if target_hv <= 0:
                raise ValueError(f"Calibration case #{idx} field 'target.hv' must be > 0")
            hv_target_found = True

        weight = _as_float(case.get('weight', 1.0), f'case[{idx}].weight')
        if weight <= 0:
            raise ValueError(f"Calibration case #{idx} field 'weight' must be > 0")

        case_temperature_k = _as_float(case.get('temperature_k', temperature_k), f'case[{idx}].temperature_k')
        case_oxygen_activity = _as_float(case.get('oxygen_activity', oxygen_activity), f'case[{idx}].oxygen_activity')
        case_oxygen_activity = max(0.0, min(1.0, case_oxygen_activity))

        prepared.append(
            {
                'index': idx,
                'composition': composition,
                'target_hv': target_hv,
                'weight': weight,
                'state': str(case.get('state', material_state)),
                'env': str(case.get('env', env)),
                'temperature_k': case_temperature_k,
                'oxygen_activity': case_oxygen_activity,
            }
        )

    if not hv_target_found:
        raise ValueError('Calibration requires at least one target.hv entry')
    return prepared


def fit_k_hardening(
    db: Dict[str, ElementData],
    cases: List[Dict[str, Any]],
    material_state: str,
    env: str,
    temperature_k: float,
    oxygen_activity: float,
    tuning: Dict[str, Any] | None = None,
    *,
    skipped_cases: list[int] | None = None,
) -> Tuple[float, float]:
    prepared_cases = _prepare_calibration_cases(cases, material_state, env, temperature_k, oxygen_activity)

    def hardness(case: dict, k: float) -> float | None:
        report = compatibility_report(
            case["composition"], db, k, case["state"],
            env=case["env"], temperature_k=case["temperature_k"],
            oxygen_activity=case["oxygen_activity"], tuning=tuning,
        )
        return estimate_value(report, "vickers_hardness_hv")

    usable = []
    skipped = []
    for case in prepared_cases:
        if case["target_hv"] is None:
            continue
        if hardness(case, 1.0) is None:
            skipped.append(case["index"])
        else:
            usable.append(case)
    if skipped_cases is not None:
        skipped_cases.extend(skipped)
    if not usable:
        raise ValueError("No calibration case has an applicable HV estimate. Skipped cases: " + ", ".join(map(str, skipped)))

    best_k = 1.0
    best_err = math.inf
    weight_sum = sum(case["weight"] for case in usable)
    for i in range(10, 401):
        k = i / 100.0
        error = 0.0
        for case in usable:
            prediction = hardness(case, k)
            if prediction is None:
                error = math.inf
                break
            target = case["target_hv"]
            error += case["weight"] * ((prediction - target) / max(1.0, target)) ** 2
        error /= weight_sum
        if error < best_err:
            best_err = error
            best_k = k

    if not math.isfinite(best_err):
        raise ValueError("No finite fit found for the applicable calibration cases")
    return best_k, best_err
