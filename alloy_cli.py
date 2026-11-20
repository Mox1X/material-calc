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
from material_report import diagnose, make_report
from composition import parse_composition


def fraction_0_1(value: str) -> float:
    v = float(value)
    if not (0.0 <= v <= 1.0):
        raise argparse.ArgumentTypeError('Value must be in range [0..1]')
    return v


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Alloy compatibility constructor', exit_on_error=False)
    parser.add_argument('--composition', help='Example: Fe:0.7,Cr:0.2,C:0.1')
    parser.add_argument('--material-profile', help='Select a nominal reference profile by ID')
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

    duplicates = find_duplicate_symbols(args.composition or '')
    composition = parse_composition(args.composition) if args.composition is not None else None
    db = load_elements(Path(args.elements_dir)) if args.elements_dir else load_elements()
    tuning = load_tuning_file(Path(args.tuning_file)) if args.tuning_file else None
    k_used = args.k_hardening
    calibration_meta: Optional[Dict[str, Any]] = None

    if args.fit_k_hardening:
        if not args.calibration_file:
            raise ValueError('--fit-k-hardening requires --calibration-file')
        cases = load_calibration_cases(Path(args.calibration_file))
        skipped_cases: list[int] = []
        k_used, fit_error = fit_k_hardening(
            db,
            cases,
            material_state=args.state,
            env=args.env,
            temperature_k=args.temperature_k,
            oxygen_activity=oxygen_activity,
            tuning=tuning,
            skipped_cases=skipped_cases,
        )
        calibration_meta = {
            'cases': len(cases),
            'cases_without_hv_estimate': skipped_cases,
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
        material_profile=args.material_profile,
    )
    if duplicates:
        diagnose(result, 'duplicate_symbols', 'Repeated element fractions were added before normalization: ' + ', '.join(duplicates))
    if args.env == 'vacuum' and args.oxygen_activity is None:
        diagnose(result, 'vacuum_default', 'Vacuum mode sets oxygen activity to 0.0 by default.')
    if calibration_meta:
        result['calibration'] = calibration_meta

    return result


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    pretty = False
    try:
        args = parser.parse_args(argv)
        pretty = args.pretty
        result = run_cli(args)
    except (argparse.ArgumentError, ValueError, OSError) as error:
        result = make_report()
        diagnose(result, "invalid_input", str(error))
    print(json.dumps(result, indent=2 if pretty else None, ensure_ascii=False, allow_nan=False))
    if result["status"] == "invalid":
        raise SystemExit(2)


if __name__ == '__main__':
    main()
