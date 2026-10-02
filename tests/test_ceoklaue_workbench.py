import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "App"
WORK = ROOT / "Branding" / "CEOKlaue"
BRACKET_MANIFEST = WORK / "button-bracket-source-manifest.json"
RUNTIME_MANIFEST = WORK / "05_runtime" / "manifest.json"
os.environ.setdefault("SAMMLR_ENV", "testing")
os.environ.setdefault("SAMMLR_SECRET_KEY", "sammlr-explicit-testing-secret")
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CEOKlaueFinalControlPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        webapp.app.config.update(TESTING=True, SAMMLR_ENV="testing")
        webapp.ceoklaue_runtime_manifest.cache_clear()
        webapp.ceoklaue_button_bracket_manifest.cache_clear()
        cls.client = webapp.app.test_client()
        cls.brackets = json.loads(BRACKET_MANIFEST.read_text(encoding="utf-8"))
        cls.runtime = json.loads(RUNTIME_MANIFEST.read_text(encoding="utf-8"))

    def setUp(self):
        webapp.app.config["SAMMLR_ENV"] = "testing"

    def page(self):
        response = self.client.get("/dev/ceoklaue")
        self.assertEqual(200, response.status_code)
        self.assertEqual("no-store", response.headers["Cache-Control"])
        self.assertEqual("noindex, nofollow", response.headers["X-Robots-Tag"])
        return response.get_data(as_text=True)

    def test_final_f_h_mapping_uses_the_new_po_sources(self):
        records = {record["character"]: record for record in self.runtime["master"]["characters_manifest"]}
        self.assertEqual(["05", "02", "01"], [item["variant"] for item in records["F"]["alternates"]])
        self.assertEqual(["01", "04", "05"], [item["variant"] for item in records["H"]["alternates"]])
        for character in ("F", "H"):
            for alternate in records[character]["alternates"]:
                self.assertIn("01_extracted/final_fh_repair/cap_", alternate["source"])
                self.assertEqual(alternate["source_sha256"], digest(WORK / alternate["source"]))

    def test_button_source_and_all_five_real_pairs_are_integral(self):
        source = self.brackets["source"]
        self.assertEqual("IMG_7192.JPG", source["original_filename"])
        self.assertEqual([4032, 3024], source["pixel_dimensions"])
        self.assertEqual("ff3216183427dc96f85fe88b3fa595d46c0f1c3a04f6f38fbefc110dda39d3db", source["sha256"])
        self.assertEqual({"pairs": 5, "left_assets": 5, "right_assets": 5}, self.brackets["totals"])
        self.assertEqual([f"{index:02d}" for index in range(1, 6)], [pair["id"] for pair in self.brackets["pairs"]])
        for pair in self.brackets["pairs"]:
            for side in ("left", "right"):
                output = pair[side]
                self.assertEqual(f"button_bracket_{pair['id']}_{side}", output["candidate_key"])
                for kind in ("png", "svg", "runtime_svg"):
                    path = ROOT / output[kind]["path"]
                    self.assertTrue(path.is_file())
                    self.assertEqual(output[kind]["sha256"], digest(path))

    def test_button_import_is_idempotent(self):
        result = subprocess.run(
            [sys.executable, str(WORK / "import_button_bracket_sources.py")],
            cwd=ROOT, check=True, capture_output=True, text=True,
        )
        self.assertIn("already imported and verified", result.stdout)

    def test_deterministic_bracket_selection_is_stable_mixed_and_never_frankensteined(self):
        first = [
            webapp.ceoklaue_button_bracket_pair("route-a", f"action-{index}", f"Label {index}", index)
            for index in range(80)
        ]
        second = [
            webapp.ceoklaue_button_bracket_pair("route-a", f"action-{index}", f"Label {index}", index)
            for index in range(80)
        ]
        self.assertEqual(first, second)
        self.assertEqual({"01", "02", "03", "04", "05"}, {pair["id"] for pair in first})
        for pair in first:
            self.assertIn(f"button_bracket_{pair['id']}_left.svg", pair["left"])
            self.assertIn(f"button_bracket_{pair['id']}_right.svg", pair["right"])

    def test_complete_control_page_contains_all_required_sections(self):
        html = self.page()
        self.assertEqual(["1", "2", "3"], re.findall(r'class="alternate-card" data-alternate="([123])"', html))
        for text in (
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz", "0123456789", "äöü ÄÖÜ ß",
            ". , : ; ! ? - + / &amp; % ( )", "FIFA World Cup 2026", "FWC1, FWC18, FWC26",
            "HAI2, HAI10, GHA19", "660 gesammelt · 332 fehlend · 108 doppelt",
            "Fehlende Sticker", "Doppelte Sticker", "Aktueller Tausch",
            "2 erhalten · 3 abgegeben", "Deterministic mixed button examples",
            "Milkglass/Post-it Concept Preview · Development only",
        ):
            self.assertIn(text, html)
        for pair_id in ("01", "02", "03", "04", "05"):
            self.assertIn(f"Pair {pair_id}", html)
            self.assertIn(f'data-mixed-pair="{pair_id}"', html)
        self.assertIn("background:rgba(245,221,98,.95)", html)
        self.assertNotIn("F – neue Kandidaten", html)
        self.assertNotIn("H – neue Kandidaten", html)

    def test_production_control_page_is_404(self):
        webapp.app.config["SAMMLR_ENV"] = "production"
        try:
            self.assertEqual(404, self.client.get("/dev/ceoklaue").status_code)
        finally:
            webapp.app.config["SAMMLR_ENV"] = "testing"


if __name__ == "__main__":
    unittest.main()
