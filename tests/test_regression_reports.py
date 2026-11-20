#!/usr/bin/env python3

import json
import unittest
from pathlib import Path
from typing import Any, Dict, List

from alloy_engine import compatibility_report
from alloy_models import load_elements
from composition import parse_composition


class CompatibilityRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.db = load_elements()
        fixture_path = Path(__file__).resolve().parent / "golden_reports.json"
        cls.cases: List[Dict[str, Any]] = json.loads(fixture_path.read_text(encoding="utf-8"))

    def test_golden_reports(self) -> None:
        for item in self.cases:
            case = item["case"]
            expected = item["expected"]
            with self.subTest(case_id=case["id"]):
                report = compatibility_report(
                    parse_composition(case["composition"]),
                    self.db,
                    k_hardening=1.0,
                    material_state=case["material_state"],
                    env=case["env"],
                    temperature_k=case["temperature_k"],
                    oxygen_activity=case["oxygen_activity"],
                    regime_override=case["regime_override"],
                    tuning=None,
                )
                self.assertEqual(report, expected)


if __name__ == "__main__":
    unittest.main()
