#!/usr/bin/env python3

import unittest

from alloy_engine import compatibility_report
from alloy_models import load_elements
from composition import parse_composition


class MaterialModelingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.db = load_elements()

    def _report(self, composition: str, state: str = "raw") -> dict:
        return compatibility_report(
            parse_composition(composition),
            self.db,
            k_hardening=1.0,
            material_state=state,
            env="air",
            temperature_k=298.15,
            oxygen_activity=0.21,
            regime_override="auto",
        )

    def test_carbon_tool_steel_state_branch_changes_hardness(self) -> None:
        raw = self._report("Fe:98.2,C:1.2,Mn:0.35,Si:0.25", state="raw")
        quenched = self._report("Fe:98.2,C:1.2,Mn:0.35,Si:0.25", state="quenched")

        raw_hv = raw["predicted_properties"]["vickers_hardness_hv"]
        quenched_hv = quenched["predicted_properties"]["vickers_hardness_hv"]
        self.assertLess(raw_hv, 280.0)
        self.assertGreater(quenched_hv, raw_hv * 2.3)

    def test_high_speed_steel_state_branch_changes_hardness(self) -> None:
        raw = self._report("Fe:82.14,C:0.86,W:6.0,Mo:5.0,Cr:4.0,V:2.0", state="raw")
        tempered = self._report("Fe:82.14,C:0.86,W:6.0,Mo:5.0,Cr:4.0,V:2.0", state="tempered")

        raw_hv = raw["predicted_properties"]["vickers_hardness_hv"]
        tempered_hv = tempered["predicted_properties"]["vickers_hardness_hv"]
        self.assertGreater(raw_hv, 200.0)
        self.assertLess(raw_hv, 320.0)
        self.assertGreater(tempered_hv, 780.0)

    def test_cermet_density_uses_phase_mixture_rule(self) -> None:
        # Approximate VK8 composition derived from 92 wt.% WC + 8 wt.% Co.
        report = self._report("W:0.8636,C:0.0564,Co:0.08", state="raw")
        rho = report["predicted_properties"]["density_kg_m3"]
        self.assertEqual(report["model_context"]["material_regime"], "cermet")
        self.assertGreater(rho, 14000.0)
        self.assertLess(rho, 15200.0)


if __name__ == "__main__":
    unittest.main()
