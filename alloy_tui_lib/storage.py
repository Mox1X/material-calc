#!/usr/bin/env python3

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import List

from .common import Ansi, bold, colorize, format_compact_table, numeric
from .models import CaseConfig, CaseListItem, case_to_payload, payload_to_case, slugify


def list_case_files(cases_dir: Path) -> List[Path]:
    if not cases_dir.exists():
        return []
    return sorted(cases_dir.glob("*.json"))


def load_case_list_items(cases_dir: Path) -> List[CaseListItem]:
    items: List[CaseListItem] = []
    for path in list_case_files(cases_dir):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            case_block = payload.get("case", {})
            summary = payload.get("summary", {})
            hv_raw = summary.get("vickers_hardness_hv")
            corrosion_raw = summary.get("corrosion_susceptibility_0_1", summary.get("corrosion_risk_0_1"))
            brittleness_raw = summary.get("brittleness_0_1")

            hv = numeric(hv_raw, float("nan")) if hv_raw is not None else float("nan")
            corrosion = numeric(corrosion_raw, float("nan")) if corrosion_raw is not None else float("nan")
            brittleness = numeric(brittleness_raw, float("nan")) if brittleness_raw is not None else float("nan")

            items.append(
                CaseListItem(
                    path=path,
                    name=str(case_block.get("name", path.stem)),
                    saved_at=str(payload.get("saved_at", "")),
                    material_regime=str(summary.get("material_regime", "n/a")),
                    vickers_hardness_hv=hv if math.isfinite(hv) else None,
                    corrosion_susceptibility_0_1=corrosion if math.isfinite(corrosion) else None,
                    brittleness_0_1=brittleness if math.isfinite(brittleness) else None,
                    load_error=None,
                )
            )
        except Exception as exc:
            items.append(
                CaseListItem(
                    path=path,
                    name=path.stem,
                    saved_at="",
                    material_regime="n/a",
                    vickers_hardness_hv=None,
                    corrosion_susceptibility_0_1=None,
                    brittleness_0_1=None,
                    load_error=str(exc),
                )
            )
    return items


def filter_case_items(items: List[CaseListItem], filter_text: str) -> List[CaseListItem]:
    needle = filter_text.strip().lower()
    if not needle:
        return list(items)
    out: List[CaseListItem] = []
    for item in items:
        fields = [
            item.name.lower(),
            item.path.name.lower(),
            item.material_regime.lower(),
            item.saved_at.lower(),
        ]
        if any(needle in field for field in fields):
            out.append(item)
    return out


def sort_case_items(items: List[CaseListItem], sort_key: str, descending: bool) -> List[CaseListItem]:
    key = sort_key.strip().lower()
    if key == "name":
        fn = lambda x: x.name.lower()
    elif key == "hv":
        fn = lambda x: x.vickers_hardness_hv if x.vickers_hardness_hv is not None else float("-inf")
    elif key == "regime":
        fn = lambda x: x.material_regime.lower()
    elif key == "corrosion":
        fn = lambda x: x.corrosion_susceptibility_0_1 if x.corrosion_susceptibility_0_1 is not None else float("-inf")
    elif key == "brittleness":
        fn = lambda x: x.brittleness_0_1 if x.brittleness_0_1 is not None else float("-inf")
    else:
        fn = lambda x: x.saved_at
    return sorted(items, key=fn, reverse=descending)


def show_case_list(
    cases_dir: Path,
    filter_text: str = "",
    sort_key: str = "saved",
    descending: bool = True,
) -> List[CaseListItem]:
    items = load_case_list_items(cases_dir)
    items = filter_case_items(items, filter_text)
    items = sort_case_items(items, sort_key, descending)
    if not items:
        print("No saved cases for current filter.")
        return []
    order = "desc" if descending else "asc"
    print(bold(f"Saved cases (sort={sort_key}:{order}, filter='{filter_text or '*'}')"))
    rows: List[List[str]] = [["#", "Name", "Regime", "HV", "Saved", "File"]]
    for idx, item in enumerate(items, start=1):
        hv_text = f"{item.vickers_hardness_hv:.2f}" if item.vickers_hardness_hv is not None else "n/a"
        saved_text = item.saved_at if item.saved_at else "n/a"
        rows.append([str(idx), item.name, item.material_regime, hv_text, saved_text, item.path.name])
    print(format_compact_table(rows))
    for idx, item in enumerate(items, start=1):
        if item.load_error:
            print(colorize(f"! #{idx} parse warning: {item.load_error}", Ansi.YELLOW))
    return items


def save_case(cases_dir: Path, case: CaseConfig, report: dict) -> Path:
    cases_dir.mkdir(parents=True, exist_ok=True)
    base = slugify(case.name)
    target = cases_dir / f"{base}.json"
    if target.exists():
        suffix = datetime.now().strftime("%Y%m%d-%H%M%S")
        target = cases_dir / f"{base}-{suffix}.json"
    payload = case_to_payload(case, report=report)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return target


def load_case_interactive(
    cases_dir: Path,
    filter_text: str = "",
    sort_key: str = "saved",
    descending: bool = True,
) -> CaseConfig:
    items = show_case_list(cases_dir, filter_text=filter_text, sort_key=sort_key, descending=descending)
    if not items:
        raise ValueError("No saved cases found.")
    raw = input("load index> ").strip()
    if not raw:
        raise ValueError("Load cancelled.")
    idx = int(raw)
    if idx < 1 or idx > len(items):
        raise ValueError("Index out of range.")
    payload = json.loads(items[idx - 1].path.read_text(encoding="utf-8"))
    return payload_to_case(payload)
