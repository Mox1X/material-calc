#!/usr/bin/env python3

import json
import subprocess
import sys
import unittest

from alloy_engine import compatibility_report
from alloy_models import load_elements
from composition import parse_composition


class InputValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.db = load_elements()

    def test_parse_composition_rejects_non_finite_values(self) -> None:
        for raw in ("Fe:nan,Cr:1", "Fe:inf,Cr:1", "Fe:1e308,Cr:1e308"):
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, "finite"):
                parse_composition(raw)

    def test_invalid_input_returns_structured_result(self) -> None:
        for composition, k, state, conditions, message in (
            ({}, 1.0, "raw", {}, "at least one element"),
            ({"Fe": 1.0}, 1.0, "raw", {"temperature_k": -1}, "temperature_k"),
            ({"Fe": 1.0}, 1.0, "annealed", {}, "material_state"),
            ({"Fe": 1.0}, 1.0, "raw", {"env": "lava"}, "env"),
            ({"Fe": 1.0}, 1.0, "raw", {"regime_override": "invalid"}, "regime_override"),
            ({"Fe": 1.0}, float("inf"), "raw", {}, "k_hardening"),
        ):
            with self.subTest(message=message):
                report = compatibility_report(composition, self.db, k, state, **conditions)
                self.assertEqual(report["status"], "invalid")
                self.assertIn(message, report["diagnostics"][0]["message"])
                json.dumps(report, allow_nan=False)

    def test_cermet_override_reverts_when_auto_candidate_is_false(self) -> None:
        report = compatibility_report(
            parse_composition("Fe:0.7,Cr:0.2,C:0.1"),
            self.db, 1.0, "raw", regime_override="cermet",
        )
        self.assertNotEqual(report["classification"]["regime"], "cermet")
        self.assertTrue(any("Requested regime 'cermet'" in d["message"] for d in report["diagnostics"]))

    def test_large_unbound_gas_fractions_never_use_metal_model(self) -> None:
        for composition in (
            "Fe:50,He:50", "Fe:40,Ne:30,Ar:30", "U:30,Th:30,He:40",
            "Ce:25,Nd:25,La:25,Ar:25", "Fe:0.5,He:0.5", "Fe:50,Cl:50",
        ):
            with self.subTest(composition=composition):
                report = compatibility_report(parse_composition(composition), self.db, 1.0, "raw", regime_override="steel")
                self.assertEqual(report["status"], "unsupported")
                self.assertIsNone(report["classification"]["regime"])
                self.assertTrue(all(value is None for value in report["properties"].values()))
                json.dumps(report, allow_nan=False)

    def test_trace_gas_with_missing_element_data_remains_serializable(self) -> None:
        composition = parse_composition("Fe:99.99,He:0.01")
        report = compatibility_report(composition, self.db, 1.0, "raw")
        self.assertEqual(report["status"], "partial")
        self.assertIsNone(report["model_details"]["hume_rothery"]["electronegativity_weighted_delta"])
        self.assertTrue(any(d["code"] == "electronegativity_missing" for d in report["diagnostics"]))
        json.dumps(report, allow_nan=False)

    def test_cli_returns_strict_json_and_distinct_exit_codes(self) -> None:
        for composition, code, status in (("Fe:nan", 2, "invalid"), ("Fe:50,He:50", 0, "unsupported")):
            with self.subTest(status=status):
                result = subprocess.run(
                    [sys.executable, "alloy_cli.py", "--composition", composition],
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(result.returncode, code)
                self.assertEqual(json.loads(result.stdout)["status"], status)
                self.assertEqual(result.stderr, "")
