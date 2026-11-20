#!/usr/bin/env python3
"""Generate tinted item icons from a grayscale base texture.

Examples:
  python generate_tinted_items.py --layer0 assets/item_ingot_base.png --out-dir out/items
  python generate_tinted_items.py --layer0 assets/item_ingot_base.png --layer1 assets/item_ingot_overlay.png --out-dir out/items
  python generate_tinted_items.py --layer0 assets/item_ingot_base.png --mode composition --composition Fe:0.7,Cr:0.2,C:0.1 --name alloy_preview
"""

import argparse
import colorsys
import json
import math
import os
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image
from alloy_engine import compatibility_report
from composition import parse_composition
from alloy_models import load_elements

DEFAULT_ELEMENTS_DIR = Path(__file__).resolve().parent / "elements"
DEFAULT_OUT_DIR = Path(__file__).resolve().parent / "artifacts" / "generated_items"
DEFAULT_DOTENV_PATH = Path(__file__).resolve().parent / ".env"


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def env_float(name: str, fallback: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return float(fallback)
    try:
        return float(raw)
    except ValueError:
        return float(fallback)


def clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def srgb_to_linear_u8(v: int) -> float:
    x = v / 255.0
    if x <= 0.04045:
        return x / 12.92
    return ((x + 0.055) / 1.055) ** 2.4


def linear_to_srgb_u8(v: float) -> int:
    x = clamp01(v)
    if x <= 0.0031308:
        y = 12.92 * x
    else:
        y = 1.055 * (x ** (1.0 / 2.4)) - 0.055
    return int(round(clamp01(y) * 255.0))


def load_element_visuals(elements_dir: Path) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for path in elements_dir.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        sym = data.get("symbol")
        if not sym:
            continue
        visual = data.get("visual", {})
        out[sym] = {
            "name": data.get("name", sym),
            "atomic_number": int(data.get("identification", {}).get("atomic_number", 0) or 0),
            "file_stem": path.stem,
            "color_rgb": visual.get("color_rgb", [195, 200, 208]),
            "color_power": float(visual.get("color_power", 1.0)),
            "darkening_power": float(visual.get("darkening_power", 0.0)),
            "whitening_power": float(visual.get("whitening_power", 0.0)),
            "luster_group": str(visual.get("luster_group", "satin")),
            "is_colorless": bool(visual.get("is_colorless", False)),
            "container_tint_rgb": visual.get("container_tint_rgb", [210, 220, 235]),
        }
    return out


def normalize_rgb(rgb: List[int]) -> Tuple[int, int, int]:
    if len(rgb) != 3:
        return (195, 200, 208)
    return (
        int(max(0, min(255, rgb[0]))),
        int(max(0, min(255, rgb[1]))),
        int(max(0, min(255, rgb[2]))),
    )


def blend_rgb(a: Tuple[int, int, int], b: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    tt = clamp01(t)
    return (
        int(round(a[0] * (1.0 - tt) + b[0] * tt)),
        int(round(a[1] * (1.0 - tt) + b[1] * tt)),
        int(round(a[2] * (1.0 - tt) + b[2] * tt)),
    )


def rgb_distance(a: Tuple[int, int, int], b: Tuple[int, int, int]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def derived_default_color(symbol: str, atomic_number: int, luster_group: str) -> Tuple[int, int, int]:
    # Deterministic fallback for elements that still have neutral placeholder color.
    seed = atomic_number if atomic_number > 0 else sum(ord(c) for c in symbol)
    hue = ((seed * 37) % 360) / 360.0
    sat_base = {
        "mirror": 0.28,
        "satin": 0.34,
        "dull": 0.22,
        "greasy": 0.14,
    }.get(luster_group, 0.30)
    val_base = {
        "mirror": 0.88,
        "satin": 0.80,
        "dull": 0.66,
        "greasy": 0.52,
    }.get(luster_group, 0.78)
    sat = max(0.1, min(0.5, sat_base + ((seed % 7) - 3) * 0.02))
    val = max(0.42, min(0.92, val_base + ((seed % 5) - 2) * 0.03))
    r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
    return (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))


def effective_base_color(
    symbol: str,
    v: dict,
    neutral_identity_threshold: float = 0.0,
    neutral_identity_strength: float = 0.0,
) -> Tuple[int, int, int]:
    default_rgb = (195, 200, 208)
    base_rgb = normalize_rgb(v["container_tint_rgb"] if v.get("is_colorless") else v["color_rgb"])
    # If element keeps placeholder-neutral color, generate a deterministic distinct tint.
    if not v.get("is_colorless", False) and rgb_distance(base_rgb, default_rgb) < 6.0:
        return derived_default_color(symbol, int(v.get("atomic_number", 0) or 0), str(v.get("luster_group", "satin")))

    # Optional subtle identity for low-saturation metals (still mostly gray).
    if not v.get("is_colorless", False):
        thr = clamp01(float(neutral_identity_threshold))
        strength = max(0.0, float(neutral_identity_strength))
        if thr > 0.0 and strength > 0.0:
            _, sat, _ = colorsys.rgb_to_hsv(base_rgb[0] / 255.0, base_rgb[1] / 255.0, base_rgb[2] / 255.0)
            if sat < thr:
                identity_rgb = derived_default_color(
                    symbol,
                    int(v.get("atomic_number", 0) or 0),
                    str(v.get("luster_group", "satin")),
                )
                blend_t = strength * (thr - sat) / thr
                base_rgb = blend_rgb(base_rgb, identity_rgb, blend_t)
    return base_rgb


def apply_darkening_whitening(rgb: Tuple[int, int, int], darkening: float, whitening: float) -> Tuple[int, int, int]:
    r, g, b = rgb
    rd, gd, bd = [srgb_to_linear_u8(x) for x in (r, g, b)]
    dark = clamp01(darkening)
    white = clamp01(whitening)

    # darkening: blend toward black in linear space
    rd *= (1.0 - 0.65 * dark)
    gd *= (1.0 - 0.65 * dark)
    bd *= (1.0 - 0.65 * dark)

    # whitening: blend toward neutral white in linear space
    rd = rd * (1.0 - 0.45 * white) + 1.0 * (0.45 * white)
    gd = gd * (1.0 - 0.45 * white) + 1.0 * (0.45 * white)
    bd = bd * (1.0 - 0.45 * white) + 1.0 * (0.45 * white)

    return (linear_to_srgb_u8(rd), linear_to_srgb_u8(gd), linear_to_srgb_u8(bd))


def apply_saturation(
    rgb: Tuple[int, int, int],
    saturation_multiplier: float,
    vibrance: float = 0.0,
    neutral_floor: float = 0.0,
    neutral_threshold: float = 0.12,
    soft_cap: float = 1.0,
    vivid_protect_threshold: float = 0.92,
) -> Tuple[int, int, int]:
    sat = max(0.0, float(saturation_multiplier))
    vib = max(0.0, float(vibrance))
    floor = clamp01(float(neutral_floor))
    thr = clamp01(float(neutral_threshold))
    cap = clamp01(float(soft_cap))
    vivid_thr = clamp01(float(vivid_protect_threshold))

    if (
        abs(sat - 1.0) < 1e-9
        and vib <= 0.0
        and floor <= 0.0
        and abs(cap - 1.0) < 1e-9
    ):
        return rgb

    h, s, v = colorsys.rgb_to_hsv(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
    s0 = s

    # Give near-neutral colors a small identity before global saturation is applied.
    if floor > 0.0 and s < thr and thr > 0.0:
        target = max(s, floor)
        lift_strength = (thr - s) / thr
        s = s + (target - s) * lift_strength

    # Saturation multiplier: stronger effect on dull colors, softer on already vivid ones.
    if sat >= 1.0:
        adaptive_gain = 0.35 + 0.65 * ((1.0 - s0) ** 1.2)
        s = s * (1.0 + (sat - 1.0) * adaptive_gain)
    else:
        s = s * sat

    # Vibrance boosts low-s colors more aggressively while barely touching vivid tones.
    if vib > 0.0:
        s = s + (1.0 - s) * vib * ((1.0 - s0) ** 1.1)

    # Soft-cap only for non-vivid source colors to avoid acid tones.
    if cap < 1.0 and s0 < vivid_thr and s > cap:
        s = cap + (s - cap) * 0.2

    s = clamp01(s)
    rr, gg, bb = colorsys.hsv_to_rgb(h, s, v)
    return (int(round(rr * 255.0)), int(round(gg * 255.0)), int(round(bb * 255.0)))


def mix_composition_color(
    comp: Dict[str, float],
    visuals: Dict[str, dict],
    neutral_identity_threshold: float = 0.0,
    neutral_identity_strength: float = 0.0,
    alpha: float = 0.75,
) -> Tuple[Tuple[int, int, int], dict]:
    weighted = []
    darkening = 0.0
    whitening = 0.0
    luster_score = {"mirror": 0.0, "satin": 0.0, "dull": 0.0, "greasy": 0.0}
    for sym, frac in comp.items():
        if sym not in visuals:
            continue
        v = visuals[sym]
        base_rgb = effective_base_color(
            sym,
            v,
            neutral_identity_threshold=neutral_identity_threshold,
            neutral_identity_strength=neutral_identity_strength,
        )
        power = max(0.01, float(v.get("color_power", 1.0)))
        w = (frac ** alpha) * power
        weighted.append((base_rgb, w, frac))
        darkening += frac * float(v.get("darkening_power", 0.0))
        whitening += frac * float(v.get("whitening_power", 0.0))
        lg = str(v.get("luster_group", "satin"))
        if lg in luster_score:
            luster_score[lg] += frac

    if not weighted:
        return (195, 200, 208), {
            "luster_group": "satin",
            "darkening_power": 0.0,
            "whitening_power": 0.0,
            "color_source": "element_visual_mix",
        }

    sw = sum(w for _, w, _ in weighted)
    lr = sum(srgb_to_linear_u8(rgb[0]) * w for rgb, w, _ in weighted) / sw
    lg = sum(srgb_to_linear_u8(rgb[1]) * w for rgb, w, _ in weighted) / sw
    lb = sum(srgb_to_linear_u8(rgb[2]) * w for rgb, w, _ in weighted) / sw

    mixed = (linear_to_srgb_u8(lr), linear_to_srgb_u8(lg), linear_to_srgb_u8(lb))
    mixed = apply_darkening_whitening(mixed, darkening, whitening)
    dominant_luster = max(luster_score.items(), key=lambda kv: kv[1])[0]
    color_source = "element_visual_mix"
    if comp.keys() == {"Cu", "Zn"} and 0.685 <= comp["Cu"] <= 0.715:
        # C26000 natural color is yellow. The RGB is an authored texture swatch.
        mixed = (213, 179, 85)
        dominant_luster = "satin"
        color_source = "C26000_yellow_brass_swatch"
    return mixed, {
        "luster_group": dominant_luster,
        "darkening_power": round(darkening, 4),
        "whitening_power": round(whitening, 4),
        "color_source": color_source,
    }


def validate_composition_symbols(comp: Dict[str, float], visuals: Dict[str, dict], db: Dict[str, object]) -> None:
    missing_visuals = sorted(sym for sym in comp if sym not in visuals)
    missing_db = sorted(sym for sym in comp if sym not in db)
    messages: List[str] = []
    if missing_visuals:
        messages.append("Missing visual metadata for symbols: " + ", ".join(missing_visuals))
    if missing_db:
        messages.append("Missing physical model data for symbols: " + ", ".join(missing_db))
    if messages:
        raise ValueError("; ".join(messages))


def tint_layer0(layer0: Image.Image, tint_rgb: Tuple[int, int, int]) -> Image.Image:
    img = layer0.convert("RGBA")
    px = img.load()
    tr, tg, tb = [srgb_to_linear_u8(x) for x in tint_rgb]
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            # preserve shading from grayscale base by multiplying in linear space
            gray = (r + g + b) / 3.0
            gl = srgb_to_linear_u8(int(gray))
            rr = linear_to_srgb_u8(gl * tr)
            gg = linear_to_srgb_u8(gl * tg)
            bb = linear_to_srgb_u8(gl * tb)
            px[x, y] = (rr, gg, bb, a)
    return img


def build_icon(layer0_path: Path, layer1_path: Path | None, out_path: Path, tint_rgb: Tuple[int, int, int]) -> None:
    base = Image.open(layer0_path).convert("RGBA")
    tinted = tint_layer0(base, tint_rgb)
    if layer1_path is not None and layer1_path.is_file():
        overlay = Image.open(layer1_path).convert("RGBA")
        tinted.alpha_composite(overlay)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tinted.save(out_path)


def main() -> None:
    load_dotenv(DEFAULT_DOTENV_PATH)

    default_saturation = env_float("TEXTURE_SATURATION", 1.0)
    default_vibrance = env_float("TEXTURE_VIBRANCE", 0.0)
    default_neutral_floor = env_float("TEXTURE_NEUTRAL_FLOOR", 0.0)
    default_neutral_threshold = env_float("TEXTURE_NEUTRAL_THRESHOLD", 0.12)
    default_sat_soft_cap = env_float("TEXTURE_SAT_SOFT_CAP", 1.0)
    default_vivid_protect = env_float("TEXTURE_VIVID_PROTECT_THRESHOLD", 0.92)
    default_neutral_identity_threshold = env_float("TEXTURE_NEUTRAL_IDENTITY_THRESHOLD", 0.0)
    default_neutral_identity_strength = env_float("TEXTURE_NEUTRAL_IDENTITY_STRENGTH", 0.0)

    parser = argparse.ArgumentParser(description="Generate tinted item icons from grayscale template")
    parser.add_argument("--elements-dir", default=str(DEFAULT_ELEMENTS_DIR), help="Path to elements JSON directory")
    parser.add_argument("--layer0", required=True, help="Base grayscale texture path (tinted)")
    parser.add_argument("--layer1", default="", help="Optional overlay texture path (not tinted)")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory")
    parser.add_argument("--mode", choices=["elements", "composition"], default="elements")
    parser.add_argument("--composition", default="", help="Composition string, e.g. Fe:0.7,Cr:0.2,C:0.1")
    parser.add_argument("--name", default="alloy_preview", help="Output filename stem for composition mode")
    parser.add_argument(
        "--saturation",
        type=float,
        default=default_saturation,
        help="Final tint saturation multiplier (overridable via TEXTURE_SATURATION in .env)",
    )
    parser.add_argument(
        "--vibrance",
        type=float,
        default=default_vibrance,
        help="Adaptive boost for low-saturation colors (TEXTURE_VIBRANCE)",
    )
    parser.add_argument(
        "--neutral-floor",
        type=float,
        default=default_neutral_floor,
        help="Minimum saturation target for near-neutral colors (TEXTURE_NEUTRAL_FLOOR)",
    )
    parser.add_argument(
        "--neutral-threshold",
        type=float,
        default=default_neutral_threshold,
        help="What is considered near-neutral for --neutral-floor logic (TEXTURE_NEUTRAL_THRESHOLD)",
    )
    parser.add_argument(
        "--sat-soft-cap",
        type=float,
        default=default_sat_soft_cap,
        help="Soft cap for saturation of non-vivid source colors (TEXTURE_SAT_SOFT_CAP)",
    )
    parser.add_argument(
        "--vivid-protect-threshold",
        type=float,
        default=default_vivid_protect,
        help="Source saturation above this is treated as vivid (TEXTURE_VIVID_PROTECT_THRESHOLD)",
    )
    parser.add_argument(
        "--neutral-identity-threshold",
        type=float,
        default=default_neutral_identity_threshold,
        help="Apply subtle per-element hue identity below threshold (TEXTURE_NEUTRAL_IDENTITY_THRESHOLD)",
    )
    parser.add_argument(
        "--neutral-identity-strength",
        type=float,
        default=default_neutral_identity_strength,
        help="Blend strength for neutral identity tint (TEXTURE_NEUTRAL_IDENTITY_STRENGTH)",
    )
    parser.add_argument("--env", choices=["air", "water", "acid", "vacuum"], default="air", help="Environment for composition material assessment")
    parser.add_argument("--temperature-k", type=float, default=298.15, help="Temperature for composition material assessment")
    parser.add_argument("--oxygen-activity", type=float, default=0.21, help="Oxygen activity for composition material assessment")
    args = parser.parse_args()

    elements_dir = Path(args.elements_dir)
    layer0 = Path(args.layer0)
    layer1 = Path(args.layer1) if args.layer1 else None
    out_dir = Path(args.out_dir)
    if not layer0.exists():
        raise FileNotFoundError(f"Missing layer0 texture: {layer0}")

    visuals = load_element_visuals(elements_dir)
    db = load_elements(elements_dir)
    manifest = {}

    if args.mode == "elements":
        for sym, v in visuals.items():
            rgb = effective_base_color(
                sym,
                v,
                neutral_identity_threshold=args.neutral_identity_threshold,
                neutral_identity_strength=args.neutral_identity_strength,
            )
            rgb = apply_darkening_whitening(rgb, float(v.get("darkening_power", 0.0)), float(v.get("whitening_power", 0.0)))
            rgb = apply_saturation(
                rgb,
                args.saturation,
                vibrance=args.vibrance,
                neutral_floor=args.neutral_floor,
                neutral_threshold=args.neutral_threshold,
                soft_cap=args.sat_soft_cap,
                vivid_protect_threshold=args.vivid_protect_threshold,
            )
            out_name = f"{v['file_stem']}.png"
            out_path = out_dir / out_name
            build_icon(layer0, layer1, out_path, rgb)
            manifest[sym] = {
                "file": out_name,
                "rgb": list(rgb),
                "hex": "#{:02X}{:02X}{:02X}".format(*rgb),
                "luster_group": v.get("luster_group", "satin"),
                "is_colorless": bool(v.get("is_colorless", False)),
                "saturation_multiplier": float(args.saturation),
                "vibrance": float(args.vibrance),
                "neutral_floor": float(args.neutral_floor),
                "neutral_threshold": float(args.neutral_threshold),
                "sat_soft_cap": float(args.sat_soft_cap),
                "vivid_protect_threshold": float(args.vivid_protect_threshold),
                "neutral_identity_threshold": float(args.neutral_identity_threshold),
                "neutral_identity_strength": float(args.neutral_identity_strength),
            }
    else:
        if not args.composition:
            raise ValueError("--composition is required when --mode composition")
        comp = parse_composition(args.composition)
        validate_composition_symbols(comp, visuals, db)
        report = compatibility_report(
            comp, db, 1.0, "raw",
            env=args.env,
            temperature_k=args.temperature_k,
            oxygen_activity=args.oxygen_activity,
        )
        if report["status"] == "invalid":
            raise ValueError(report["diagnostics"][0]["message"])
        rgb, details = mix_composition_color(
            comp,
            visuals,
            neutral_identity_threshold=args.neutral_identity_threshold,
            neutral_identity_strength=args.neutral_identity_strength,
        )
        rgb = apply_saturation(
            rgb,
            args.saturation,
            vibrance=args.vibrance,
            neutral_floor=args.neutral_floor,
            neutral_threshold=args.neutral_threshold,
            soft_cap=args.sat_soft_cap,
            vivid_protect_threshold=args.vivid_protect_threshold,
        )
        out_name = f"{args.name}.png"
        out_path = out_dir / out_name
        build_icon(layer0, layer1, out_path, rgb)
        manifest["composition"] = {
            "input": comp,
            "file": out_name,
            "rgb": list(rgb),
            "hex": "#{:02X}{:02X}{:02X}".format(*rgb),
            "luster_group": details["luster_group"],
            "darkening_power": details["darkening_power"],
            "whitening_power": details["whitening_power"],
            "material_status": report["status"],
            "color_source": details["color_source"],
            "saturation_multiplier": float(args.saturation),
            "vibrance": float(args.vibrance),
            "neutral_floor": float(args.neutral_floor),
            "neutral_threshold": float(args.neutral_threshold),
            "sat_soft_cap": float(args.sat_soft_cap),
            "vivid_protect_threshold": float(args.vivid_protect_threshold),
            "neutral_identity_threshold": float(args.neutral_identity_threshold),
            "neutral_identity_strength": float(args.neutral_identity_strength),
        }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "tint_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Generated {len(manifest)} icon(s) in: {out_dir}")


if __name__ == "__main__":
    main()
