#!/usr/bin/env python3

import math
from typing import Dict, TypedDict

from config.tuning_defaults import CARBIDE_FORMER_AFFINITY, CARBIDE_PARAMS


class CarbideProfile(TypedDict):
    active: float
    carbide_index: float
    effective_carbide_fraction: float
    hardness_bonus_hv: float
    brittleness_add: float
    cermet_mode: float
    auto_cermet_candidate: float
    chromium_tied_fraction: float


def _carbide_hardness_bonus(
    composition: Dict[str, float],
    carbide_index: float,
    saturation: float,
    cermet_mode: bool,
    binder: float,
) -> float:
    if cermet_mode:
        vol_binder = min(0.35, max(0.0, binder))
        vol_carbide = max(0.0, min(0.97, 1.0 - vol_binder))
        hv_carbide = CARBIDE_PARAMS["hardness_cermet_hv_base"] + CARBIDE_PARAMS["hardness_cermet_ti_ta_coeff"] * min(
            1.0,
            composition.get("Ti", 0.0) + composition.get("Ta", 0.0),
        )
        hv_binder = CARBIDE_PARAMS["hardness_cermet_binder_hv_base"] + CARBIDE_PARAMS["hardness_cermet_binder_hv_coeff"] * min(
            CARBIDE_PARAMS["hardness_cermet_binder_cap"],
            binder,
        )
        mixed_hv = vol_carbide * hv_carbide + vol_binder * hv_binder
        return mixed_hv * (
            CARBIDE_PARAMS["hardness_cermet_mix_low"] + CARBIDE_PARAMS["hardness_cermet_mix_high"] * saturation
        )
    return (
        CARBIDE_PARAMS["hardness_non_cermet_coeff"]
        * math.sqrt(min(CARBIDE_PARAMS["hardness_non_cermet_index_cap"], max(carbide_index, 0.0)))
        * (CARBIDE_PARAMS["hardness_non_cermet_mix_low"] + CARBIDE_PARAMS["hardness_non_cermet_mix_high"] * saturation)
    )


def _carbide_brittleness_add(carbide_index: float, cermet_mode: bool, binder: float) -> float:
    brittleness_add = CARBIDE_PARAMS["brittleness_sqrt_coeff"] * math.sqrt(max(carbide_index, 0.0))
    if cermet_mode:
        brittleness_add += CARBIDE_PARAMS["brittleness_cermet_add"]
    brittleness_add -= CARBIDE_PARAMS["brittleness_binder_relief"] * binder
    return max(0.0, min(CARBIDE_PARAMS["brittleness_cap"], brittleness_add))


def carbide_profile(
    base_symbol: str,
    composition: Dict[str, float],
    force_cermet_mode: bool | None = None,
) -> CarbideProfile:
    _ = base_symbol
    c = composition.get("C", 0.0)
    if c <= 0.0:
        return {
            "active": 0.0,
            "carbide_index": 0.0,
            "effective_carbide_fraction": 0.0,
            "hardness_bonus_hv": 0.0,
            "brittleness_add": 0.0,
            "cermet_mode": 0.0,
            "auto_cermet_candidate": 0.0,
            "chromium_tied_fraction": 0.0,
        }

    potential = sum(composition.get(s, 0.0) * a for s, a in CARBIDE_FORMER_AFFINITY.items())
    if potential <= 0.0:
        return {
            "active": 0.0,
            "carbide_index": 0.0,
            "effective_carbide_fraction": 0.0,
            "hardness_bonus_hv": 0.0,
            "brittleness_add": min(CARBIDE_PARAMS["low_potential_brittleness_cap"], c * CARBIDE_PARAMS["low_potential_brittleness_c_coeff"]),
            "cermet_mode": 0.0,
            "auto_cermet_candidate": 0.0,
            "chromium_tied_fraction": 0.0,
        }

    sum_formers = sum(composition.get(s, 0.0) for s in CARBIDE_FORMER_AFFINITY)
    effective_carbide_fraction = min(c * CARBIDE_PARAMS["effective_carbide_c_scale"], sum_formers)
    saturation = 0.0 if sum_formers <= 0 else min(1.0, effective_carbide_fraction / sum_formers)
    carbide_index = effective_carbide_fraction * potential * CARBIDE_PARAMS["index_multiplier"]
    w_ti_ta = composition.get("W", 0.0) + composition.get("Ti", 0.0) + composition.get("Ta", 0.0)
    binder = composition.get("Co", 0.0) + composition.get("Ni", 0.0)
    auto_cermet = (
        c >= CARBIDE_PARAMS["auto_cermet_c_min"]
        and w_ti_ta >= CARBIDE_PARAMS["auto_cermet_w_ti_ta_min"]
        and binder > 0.0
    )
    cermet_mode = auto_cermet if force_cermet_mode is None else bool(force_cermet_mode)

    hardness_bonus = _carbide_hardness_bonus(
        composition=composition,
        carbide_index=carbide_index,
        saturation=saturation,
        cermet_mode=cermet_mode,
        binder=binder,
    )
    brittleness_add = _carbide_brittleness_add(carbide_index=carbide_index, cermet_mode=cermet_mode, binder=binder)

    cr = composition.get("Cr", 0.0)
    v_w_mo = composition.get("V", 0.0) + composition.get("W", 0.0) + composition.get("Mo", 0.0)
    chromium_tied = min(
        cr,
        c
        * (
            CARBIDE_PARAMS["chromium_tied_c_coeff"]
            + CARBIDE_PARAMS["chromium_tied_vwm_coeff"] * v_w_mo
            + CARBIDE_PARAMS["chromium_tied_cr_coeff"] * cr
        ),
    )

    return {
        "active": 1.0,
        "carbide_index": carbide_index,
        "effective_carbide_fraction": effective_carbide_fraction,
        "hardness_bonus_hv": hardness_bonus,
        "brittleness_add": brittleness_add,
        "cermet_mode": 1.0 if cermet_mode else 0.0,
        "auto_cermet_candidate": 1.0 if auto_cermet else 0.0,
        "chromium_tied_fraction": chromium_tied,
    }
