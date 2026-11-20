#!/usr/bin/env python3

from __future__ import annotations

import math
import os
import sys
from typing import Any, Dict, List


class Ansi:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    WHITE = "\033[37m"
    CYAN = "\033[36m"


def enable_ansi() -> bool:
    if os.name != "nt":
        return True
    try:
        import ctypes  # type: ignore

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)) == 0:
            return False
        if kernel32.SetConsoleMode(handle, mode.value | 0x0004) == 0:
            return False
        return True
    except Exception:
        return False


def select_bar_charset() -> tuple[str, str]:
    encoding = sys.stdout.encoding or "utf-8"
    try:
        "█".encode(encoding)
        "░".encode(encoding)
        return "█", "░"
    except Exception:
        return "#", "."


ANSI_ENABLED = sys.stdout.isatty() and enable_ansi()
BAR_FILLED, BAR_EMPTY = select_bar_charset()


def colorize(text: str, color: str) -> str:
    if not ANSI_ENABLED:
        return text
    return f"{color}{text}{Ansi.RESET}"


def bold(text: str) -> str:
    if not ANSI_ENABLED:
        return text
    return f"{Ansi.BOLD}{text}{Ansi.RESET}"


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def format_percent(value: float) -> str:
    return f"{value * 100.0:6.2f}%"


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def progress_bar(value: float, width: int = 20) -> str:
    ratio = clamp01(value)
    filled = int(round(ratio * width))
    return f"[{BAR_FILLED * filled}{BAR_EMPTY * (width - filled)}] {ratio * 100.0:5.1f}%"


def numeric(value: Any, default: float = 0.0) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(x):
        return default
    return x


def risk_color(value_0_1: float) -> str:
    value = clamp01(value_0_1)
    if value >= 0.66:
        return Ansi.RED
    if value >= 0.33:
        return Ansi.YELLOW
    return Ansi.WHITE


def warning_color(message: str) -> str:
    msg = message.lower()
    if any(x in msg for x in ("infeasible", "missing", "error", "failed", "strongly limited")):
        return Ansi.RED
    return Ansi.YELLOW


def format_compact_table(rows: List[List[str]], min_gap: int = 2) -> str:
    if not rows:
        return ""
    col_count = max(len(row) for row in rows)
    widths = [0] * col_count
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))
    lines: List[str] = []
    for row in rows:
        padded: List[str] = []
        for idx in range(col_count):
            cell = row[idx] if idx < len(row) else ""
            if idx == col_count - 1:
                padded.append(cell)
            else:
                padded.append(cell.ljust(widths[idx] + min_gap))
        lines.append("".join(padded).rstrip())
    return "\n".join(lines)


def fmt_float(value: float | None, precision: int = 3) -> str:
    if value is None:
        return "n/a"
    if precision == 0:
        return f"{value:,.0f}"
    return f"{value:,.{precision}f}"


def fmt_delta(delta: float | None, higher_is_risk: bool = False, precision: int = 3) -> str:
    if delta is None:
        return "n/a"
    text = f"{delta:+.{precision}f}"
    if higher_is_risk:
        if delta > 0:
            return colorize(text, Ansi.RED)
        if delta < 0:
            return colorize(text, Ansi.GREEN)
        return colorize(text, Ansi.WHITE)
    if delta > 0:
        return colorize(text, Ansi.GREEN)
    if delta < 0:
        return colorize(text, Ansi.RED)
    return colorize(text, Ansi.WHITE)


def summary_value(report: Dict[str, Any], block: str, field: str) -> float | None:
    node = report.get(block, {})
    if not isinstance(node, dict):
        return None
    raw = node.get(field)
    value = numeric(raw, float("nan"))
    if not math.isfinite(value):
        return None
    return value


def signed_bar(value: float, max_abs: float, width: int = 14) -> str:
    if max_abs <= 0:
        return "[" + (BAR_EMPTY * width) + "]"
    ratio = min(1.0, abs(value) / max_abs)
    filled = int(round(ratio * width))
    return f"[{BAR_FILLED * filled}{BAR_EMPTY * (width - filled)}]"
