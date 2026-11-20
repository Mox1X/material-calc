#!/usr/bin/env python3
"""Backward-compatible API layer and legacy entrypoint.

Primary CLI implementation now lives in ``alloy_cli.py``.
"""

from alloy_calibration import fit_k_hardening, load_calibration_cases
from alloy_engine import compatibility_report
from alloy_models import ElementData, load_elements
from composition import parse_composition

# Re-export stable API for existing local scripts.
__all__ = [
    'ElementData',
    'parse_composition',
    'load_elements',
    'compatibility_report',
    'load_calibration_cases',
    'fit_k_hardening',
]


def main() -> None:
    from alloy_cli import main as cli_main

    cli_main()


if __name__ == '__main__':
    main()
