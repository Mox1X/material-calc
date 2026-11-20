#!/usr/bin/env python3

import unittest

from alloy_engine import compatibility_report
from alloy_models import load_elements
from composition import parse_composition


class InputValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.db = load_elements()

    def test_parse_composition_rejects_non_finite_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "finite"):
            parse_composition("Fe:nan,Cr:1")
        with self.assertRaisesRegex(ValueError, "finite"):
            parse_composition("Fe:inf,Cr:1")

    def test_compatibility_report_rejects_empty_composition(self) -> None:
        with self.assertRaisesRegex(ValueError, "Composition is empty"):
            compatibility_report({}, self.db, 1.0, "raw")

    def test_cermet_override_reverts_when_auto_candidate_is_false(self) -> None:
        report = compatibility_report(
            parse_composition("Fe:0.7,Cr:0.2,C:0.1"),
            self.db,
            1.0,
            "raw",
            regime_override="cermet",
        )
        self.assertNotEqual(report["model_context"]["material_regime"], "cermet")
        warnings = report["input_validity"]["warnings"]
        self.assertTrue(any("Requested regime 'cermet'" in w for w in warnings))

    def test_compatibility_report_rejects_negative_temperature(self) -> None:
        with self.assertRaisesRegex(ValueError, "temperature_k"):
            compatibility_report(
                parse_composition("Fe:0.7,Cr:0.2,C:0.1"),
                self.db,
                1.0,
                "raw",
                temperature_k=-1.0,
            )

    def test_compatibility_report_rejects_invalid_material_state(self) -> None:
        with self.assertRaisesRegex(ValueError, "material_state"):
            compatibility_report(
                parse_composition("Fe:0.7,Cr:0.2,C:0.1"),
                self.db,
                1.0,
                "annealed",
            )

    def test_compatibility_report_rejects_invalid_env(self) -> None:
        with self.assertRaisesRegex(ValueError, "env"):
            compatibility_report(
                parse_composition("Fe:0.7,Cr:0.2,C:0.1"),
                self.db,
                1.0,
                "raw",
                env="lava",
            )

    def test_compatibility_report_rejects_invalid_regime_override(self) -> None:
        with self.assertRaisesRegex(ValueError, "regime_override"):
            compatibility_report(
                parse_composition("Fe:0.7,Cr:0.2,C:0.1"),
                self.db,
                1.0,
                "raw",
                regime_override="wtf",
            )


if __name__ == "__main__":
    unittest.main()
