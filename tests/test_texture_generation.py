import colorsys
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(importlib.util.find_spec("PIL"), "Pillow is required for texture integration tests")
class TextureGenerationTests(unittest.TestCase):
    def test_brass_is_yellow_and_unsupported_alloys_still_generate_textures(self) -> None:
        with tempfile.TemporaryDirectory() as output:
            for composition, status in (("Cu:70,Zn:30", "ok"), ("Fe:50,He:50", "unsupported")):
                with self.subTest(composition=composition):
                    subprocess.run(
                        [
                            sys.executable, "generate_tinted_items.py", "--mode", "composition",
                            "--composition", composition, "--layer0", "bolvanki/__ingot.png",
                            "--out-dir", output, "--name", status,
                        ],
                        capture_output=True, text=True, check=True,
                    )
                    manifest = json.loads((Path(output) / "tint_manifest.json").read_text())["composition"]
                    self.assertEqual(manifest["material_status"], status)
                    self.assertTrue((Path(output) / manifest["file"]).is_file())
                    if composition.startswith("Cu:"):
                        hue, _, _ = colorsys.rgb_to_hsv(*(channel / 255 for channel in manifest["rgb"]))
                        self.assertTrue(40 <= hue * 360 <= 65)
                        self.assertEqual(manifest["color_source"], "C26000_yellow_brass_swatch")
