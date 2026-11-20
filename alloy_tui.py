#!/usr/bin/env python3
"""Interactive terminal dashboard for alloy cases."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

from alloy_models import ElementData, load_elements
from alloy_tui_lib.common import Ansi, colorize
from alloy_tui_lib.models import default_case
from alloy_tui_lib.storage import list_case_files, load_case_interactive, save_case, show_case_list
from alloy_tui_lib.workflow import (
    compare_cases_interactive,
    edit_composition_interactive,
    edit_params_interactive,
    print_help,
    prompt_case_list_options,
    recalc_report,
    render_contributions_screen,
    render_dashboard,
)

DEFAULT_ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
DEFAULT_CASES_DIR = DEFAULT_ARTIFACTS_DIR / "cases"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Alloy constructor TUI")
    parser.add_argument("--profile", default="default", help="Reserved profile name")
    parser.add_argument("--cases-dir", default=str(DEFAULT_CASES_DIR), help="Directory for saved cases")
    parser.add_argument("--elements-dir", default="", help="Optional path to elements JSON directory")
    return parser


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    elements_dir = Path(args.elements_dir) if args.elements_dir else None
    db: Dict[str, ElementData] = load_elements(elements_dir) if elements_dir is not None else load_elements()
    cases_dir = Path(args.cases_dir)

    case = default_case()
    report = recalc_report(case, db)
    last_error: str | None = None
    list_filter = ""
    list_sort_key = "saved"
    list_descending = True

    while True:
        case_files = list_case_files(cases_dir)
        render_dashboard(case, report, case_files, last_error)
        raw = input("> ").strip().lower()
        if raw in {"quit", "q", "exit"}:
            break
        try:
            if raw in {"recalc", "r"}:
                report = recalc_report(case, db)
                last_error = None
            elif raw == "edit-comp":
                composition = edit_composition_interactive(case.composition, db)
                if composition != case.composition:
                    case.composition = composition
                    case.material_profile = None
                report = recalc_report(case, db)
                last_error = None
            elif raw == "edit-params":
                case = edit_params_interactive(case, db)
                report = recalc_report(case, db)
                last_error = None
            elif raw == "save":
                path = save_case(cases_dir, case, report)
                last_error = None
                print(colorize(f"Saved: {path}", Ansi.CYAN))
                input("Press Enter to continue...")
            elif raw == "load":
                case = load_case_interactive(
                    cases_dir,
                    filter_text=list_filter,
                    sort_key=list_sort_key,
                    descending=list_descending,
                )
                report = recalc_report(case, db)
                last_error = None
            elif raw == "list":
                show_case_list(
                    cases_dir,
                    filter_text=list_filter,
                    sort_key=list_sort_key,
                    descending=list_descending,
                )
                input("Press Enter to continue...")
            elif raw in {"list-config", "listcfg", "lcfg"}:
                list_filter, list_sort_key, list_descending = prompt_case_list_options(
                    list_filter,
                    list_sort_key,
                    list_descending,
                )
                show_case_list(
                    cases_dir,
                    filter_text=list_filter,
                    sort_key=list_sort_key,
                    descending=list_descending,
                )
                input("Press Enter to continue...")
            elif raw == "compare":
                compare_cases_interactive(
                    cases_dir,
                    db,
                    case,
                    report,
                    filter_text=list_filter,
                    sort_key=list_sort_key,
                    descending=list_descending,
                )
            elif raw in {"contrib", "contributions"}:
                render_contributions_screen(case, report, db)
            elif raw == "new":
                case = default_case()
                report = recalc_report(case, db)
                last_error = None
            elif raw == "help":
                print_help()
                input("Press Enter to continue...")
            elif raw == "":
                continue
            else:
                raise ValueError("Unknown command. Type 'help' to see available commands.")
        except Exception as exc:
            last_error = str(exc)


if __name__ == "__main__":
    main()
