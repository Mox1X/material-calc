#!/usr/bin/env python3
"""Alloy compatibility constructor CLI."""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from alloy_calibration import fit_k_hardening, load_calibration_cases
from alloy_engine import compatibility_report
from alloy_models import load_elements
from alloy_tuning import load_tuning_file
from alloy_validation import find_duplicate_symbols
from composition import parse_composition


def fraction_0_1(value: str) -> float:
    v = float(value)
    if not (0.0 <= v <= 1.0):
        raise argparse.ArgumentTypeError('Value must be in range [0..1]')
    return v


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Alloy compatibility constructor')
    parser.add_argument('--composition', required=True, help='Example: Fe:0.7,Cr:0.2,C:0.1')
    parser.add_argument(
        '--k-hardening',
        type=float,
        default=1.0,
        help='Solid-solution hardening multiplier (1.0 keeps base formula scale)',
    )
    parser.add_argument(
        '--state',
        choices=['raw', 'tempered', 'quenched', 'potential'],
        default='raw',
        help='Material state for hardness evaluation',
    )
    parser.add_argument(
        '--env',
        choices=['air', 'water', 'acid', 'vacuum'],
        default='air',
        help='Corrosion environment context',
    )
    parser.add_argument(
        '--temperature-k',
        type=float,
        default=298.15,
        help='Process/environment temperature in Kelvin for corrosion context',
    )
    parser.add_argument(
        '--oxygen-activity',
        type=fraction_0_1,
        default=None,
        help='Oxygen activity proxy in range [0..1]',
    )
    parser.add_argument(
        '--regime',
        choices=['auto', 'steel', 'cast_iron', 'cermet', 'refractory', 'nonferrous'],
        default='auto',
        help='Material regime selector (auto-detected by default)',
    )
    parser.add_argument(
        '--calibration-file',
        type=str,
        default='',
        help='Path to JSON list of calibration cases',
    )
    parser.add_argument(
        '--tuning-file',
        type=str,
        default='',
        help='Path to JSON tuning profile with model weights',
    )
    parser.add_argument(
        '--fit-k-hardening',
        action='store_true',
        help='Auto-fit k-hardening using --calibration-file cases',
    )
    parser.add_argument(
        '--elements-dir',
        type=str,
        default='',
        help='Optional path to elements JSON directory (defaults to project elements/ near script)',
    )
    parser.add_argument('--pretty', action='store_true', help='Pretty-print JSON output')
    return parser


def run_cli(args: argparse.Namespace) -> Dict[str, Any]:
    oxygen_activity = args.oxygen_activity
    if oxygen_activity is None:
        oxygen_activity = 0.0 if args.env == 'vacuum' else 0.21

    duplicates = find_duplicate_symbols(args.composition)

    composition = parse_composition(args.composition)
    db = load_elements(Path(args.elements_dir)) if args.elements_dir else load_elements()
    tuning = load_tuning_file(Path(args.tuning_file)) if args.tuning_file else None
    k_used = args.k_hardening
    calibration_meta: Optional[Dict[str, Any]] = None

    if args.fit_k_hardening:
        if not args.calibration_file:
            raise ValueError('--fit-k-hardening requires --calibration-file')
        cases = load_calibration_cases(Path(args.calibration_file))
        k_used, fit_error = fit_k_hardening(
            db,
            cases,
            material_state=args.state,
            env=args.env,
            temperature_k=args.temperature_k,
            oxygen_activity=oxygen_activity,
            tuning=tuning,
        )
        calibration_meta = {
            'cases': len(cases),
            'fitted_k_hardening': round(k_used, 4),
            'fit_mse': round(fit_error, 8),
        }

    result = compatibility_report(
        composition,
        db,
        k_hardening=k_used,
        material_state=args.state,
        env=args.env,
        temperature_k=args.temperature_k,
        oxygen_activity=oxygen_activity,
        regime_override=args.regime,
        tuning=tuning,
    )
    input_validity = result.get('input_validity')
    if not isinstance(input_validity, dict):
        input_validity = {}
        result['input_validity'] = input_validity
    warnings = input_validity.get('warnings')
    if not isinstance(warnings, list):
        warnings = []
        input_validity['warnings'] = warnings
    if duplicates:
        warnings.append(
            'Duplicate symbols detected in input composition and were summed before normalization: '
            + ', '.join(duplicates)
        )
    if args.env == 'vacuum' and args.oxygen_activity is None:
        warnings.append('Vacuum mode auto-set oxygen_activity to 0.0 (override with --oxygen-activity if needed).')
    if calibration_meta:
        result['calibration'] = calibration_meta

    return result


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = run_cli(args)
    try:
        if args.pretty:
            print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        else:
            print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    except ValueError as exc:
        raise ValueError("Result contains non-finite numeric values and cannot be serialized as strict JSON") from exc


if __name__ == '__main__':
    main()
