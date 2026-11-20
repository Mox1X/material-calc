#!/usr/bin/env python3

import json
import unittest

from alloy_calibration import fit_k_hardening
from alloy_engine import compatibility_report
from alloy_models import load_elements
from alloy_tui_lib.models import case_to_payload, payload_to_case
from alloy_tui_lib.workflow import recalc_report
from composition import parse_composition
from report_types import estimate_value


class MaterialModelingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.db = load_elements()

    def report(self, composition: str | None, state: str = "raw", **kwargs) -> dict:
        return compatibility_report(
            parse_composition(composition) if composition else None,
            self.db, 1.0, state, **kwargs,
        )

    def test_unknown_microstructure_leaves_hardness_unavailable(self) -> None:
        for composition in (
            "Fe:98.2,C:1.2,Mn:0.35,Si:0.25",
            "Fe:82.14,C:0.86,W:6,Mo:5,Cr:4,V:2",
            "Fe:93.9,C:3.4,Si:2.2,Mn:0.5",
        ):
            for state in ("raw", "quenched", "tempered"):
                with self.subTest(composition=composition, state=state):
                    report = self.report(composition, state)
                    self.assertIsNone(estimate_value(report, "vickers_hardness_hv"))
                    self.assertIn("hardness_requires_microstructure", {d["code"] for d in report["diagnostics"]})

    def test_cermet_density_uses_phase_mixture_rule(self) -> None:
        report = self.report("W:0.8636,C:0.0564,Co:0.08")
        self.assertEqual(report["classification"]["regime"], "cermet")
        density = report["properties"]["density_kg_m3"]
        self.assertEqual(density["method"], "empirical_phase_mixture")
        self.assertGreater(density["value"], 14000.0)
        self.assertLess(density["value"], 15200.0)
        self.assertIsNone(estimate_value(report, "melting_point_k"))

    def test_stoichiometry_routes_oxides_and_carbides_to_reference_model(self) -> None:
        fixtures = (
            ("Al:52.93,O:47.07", "Al2O3", 3970, "melting_point_k", 2327),
            ("Ti:79.94,C:20.06", "TiC", 4910, "melting_point_k", 3326),
            ("Si:70.04,C:29.96", "SiC", 3210, "decomposition_or_sublimation_k", 3281),
        )
        for composition, formula, density, thermal_property, transition in fixtures:
            with self.subTest(formula=formula):
                report = self.report(composition)
                self.assertEqual(report["classification"]["formula"], formula)
                self.assertEqual(report["classification"]["basis"], "stoichiometric_match")
                self.assertEqual(report["properties"]["density_kg_m3"]["method"], "reference")
                self.assertEqual(estimate_value(report, "density_kg_m3"), density)
                self.assertEqual(estimate_value(report, thermal_property), transition)
                self.assertNotIn("model_warning", {d["code"] for d in report["diagnostics"]})
                if formula == "SiC":
                    self.assertIsNone(estimate_value(report, "melting_point_k"))

    def test_oxide_blend_requires_explicit_profile_for_density(self) -> None:
        nominal = "Al:42.34,Zr:14.81,O:42.85"
        profile = "alumina-zirconia-80-20"
        suggested = self.report(nominal)
        self.assertEqual(suggested["classification"]["candidates"], [profile])
        self.assertIsNone(estimate_value(suggested, "density_kg_m3"))
        selected = self.report(nominal, material_profile=profile)
        self.assertEqual(selected["classification"]["profile"], profile)
        density = selected["properties"]["density_kg_m3"]
        self.assertEqual(density["method"], "phase_mixture")
        self.assertIn("zero porosity", density["assumptions"][0])
        self.assertIsNone(estimate_value(selected, "melting_point_k"))
        self.assertEqual(self.report("Fe:100", material_profile=profile)["status"], "invalid")

    def test_thermal_routes_use_liquidus_for_binary_steel_and_ordinary_cast_iron(self) -> None:
        low = self.report("Fe:99.9,C:0.1")
        high = self.report("Fe:99.2,C:0.8")
        self.assertGreater(estimate_value(low, "liquidus_k"), estimate_value(high, "liquidus_k"))
        self.assertLess(estimate_value(high, "solidus_k"), estimate_value(high, "liquidus_k"))
        cast_iron = self.report("Fe:93.9,C:3.4,Si:2.2,Mn:0.5")
        self.assertEqual(cast_iron["classification"]["regime"], "cast_iron")
        self.assertTrue(1423 <= estimate_value(cast_iron, "liquidus_k") <= 1523)
        self.assertIsNone(estimate_value(cast_iron, "melting_point_k"))
        alloyed = self.report("Fe:69.9,C:2.8,Cr:25,Mo:1,Si:0.8,Mn:0.5")
        self.assertIsNone(estimate_value(alloyed, "liquidus_k"))

    def test_galvanic_risk_is_unavailable_without_contact_context(self) -> None:
        report = self.report("Fe:98,Cr:2")
        self.assertIsNotNone(estimate_value(report, "corrosion_susceptibility_index_0_1"))
        self.assertIsNone(estimate_value(report, "galvanic_corrosion_risk_index_0_1"))

    def test_legacy_case_loads_and_profile_round_trips(self) -> None:
        legacy = payload_to_case({"case": {"composition": "Fe:98,Cr:2"}, "summary": {"corrosion_risk_0_1": 0.4}})
        self.assertIsNone(legacy.material_profile)
        self.assertIn("corrosion_susceptibility_0_1", case_to_payload(legacy, recalc_report(legacy, self.db))["summary"])
        profile = "zirconia-yttria-92-8"
        report = self.report(None, material_profile=profile)
        saved = payload_to_case({"case": {"composition": report["composition_normalized"], "material_profile": profile}})
        restored = payload_to_case(json.loads(json.dumps(case_to_payload(saved, report), allow_nan=False)))
        self.assertEqual(recalc_report(restored, self.db)["classification"]["profile"], profile)

    def test_calibration_skips_cases_without_hardness(self) -> None:
        cases = [{"composition": "Fe:50,He:50", "target": {"hv": 150}}]
        conditions = dict(material_state="raw", env="air", temperature_k=298.15, oxygen_activity=0.21)
        with self.assertRaisesRegex(ValueError, "No calibration case"):
            fit_k_hardening(self.db, cases, **conditions)
        skipped = []
        fit_k_hardening(self.db, [*cases, {"composition": "Fe:100", "target": {"hv": 120}}], skipped_cases=skipped, **conditions)
        self.assertEqual(skipped, [1])
