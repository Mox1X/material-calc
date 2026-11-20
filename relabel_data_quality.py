#!python
"""Relabel data_quality in element JSON files.

Rule:
- Set all existing data_quality leaf values to `unknown`.
- For fields listed in source_notes.field_sources, set quality to `reference`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

DEFAULT_ELEMENTS_DIR = Path(__file__).resolve().parent / "elements"


def _set_all_quality_unknown(node: Any) -> Any:
    if isinstance(node, dict):
        out: Dict[str, Any] = {}
        for k, v in node.items():
            if isinstance(v, dict):
                out[k] = _set_all_quality_unknown(v)
            else:
                out[k] = "unknown"
        return out
    return {}


def _set_quality_leaf(payload: Dict[str, Any], dotted_key: str, value: str) -> None:
    qroot = payload.setdefault("data_quality", {})
    parts = dotted_key.split(".")
    cur = qroot
    for p in parts[:-1]:
        nxt = cur.get(p)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[p] = nxt
        cur = nxt
    cur[parts[-1]] = value


def process_file(path: Path) -> tuple[int, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    original_dq = data.get("data_quality", {})
    data["data_quality"] = _set_all_quality_unknown(original_dq)

    sources = data.get("source_notes", {}).get("field_sources", {})
    verified = 0
    if isinstance(sources, dict):
        for dotted_key in sources.keys():
            if not isinstance(dotted_key, str) or "." not in dotted_key:
                continue
            _set_quality_leaf(data, dotted_key, "reference")
            verified += 1

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unknown_total = 0

    def count_unknown(node: Any) -> None:
        nonlocal unknown_total
        if isinstance(node, dict):
            for v in node.values():
                count_unknown(v)
        elif node == "unknown":
            unknown_total += 1

    count_unknown(data.get("data_quality", {}))
    return unknown_total, verified


def main() -> None:
    parser = argparse.ArgumentParser(description="Relabel element data_quality based on source_notes")
    parser.add_argument("--elements-dir", type=Path, default=DEFAULT_ELEMENTS_DIR)
    args = parser.parse_args()

    files = sorted(args.elements_dir.glob("*.json"))
    processed = 0
    total_unknown = 0
    total_verified = 0
    for p in files:
        u, v = process_file(p)
        processed += 1
        total_unknown += u
        total_verified += v

    print(
        json.dumps(
            {
                "processed_files": processed,
                "unknown_labels_total": total_unknown,
                "verified_labels_total": total_verified,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
