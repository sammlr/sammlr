import hashlib
import io
import json
import os
from pathlib import Path
import sys
import unittest

from fontTools.ttLib import TTFont


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "App"
PREVIEW_DIR = ROOT / "Branding" / "CEOKlaue" / "03_font" / "preview"
os.environ.setdefault("SAMMLR_ENV", "testing")
os.environ.setdefault("SAMMLR_SECRET_KEY", "sammlr-explicit-testing-secret")
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402


EXPECTED_PO_SELECTIONS = {
    "A": "03", "B": "05", "C": "01", "D": "04", "E": "03", "F": "03",
    "G": "01", "H": "01", "I": "01", "J": "04", "L": "04", "M": "03",
    "N": "03", "O": "05", "Q": "04", "R": "02", "S": "05", "T": "02",
    "U": "04", "V": "03", "W": "02", "X": "05", "Y": "03", "Z": "01",
    "a": "03", "b": "05", "c": "04", "d": "02", "e": "03", "f": "05",
    "g": "03", "h": "05", "i": "04", "j": "05", "l": "03", "m": "02",
    "n": "05", "o": "04", "p": "02", "q": "05", "r": "03", "s": "03",
    "t": "04", "u": "05", "v": "02", "w": "05", "x": "05", "y": "02",
    "z": "02", "1": "01", "2": "03", "3": "01", "4": "02", "5": "02",
    "6": "01", "7": "05", "8": "03", "9": "05", "ä": "04", "ö": "05",
    "ü": "04", "ß": "05", ".": "03", ",": "03", ":": "05", "!": "05",
    "?": "01", "-": "04", "+": "02", "/": "03", "(": "04", ")": "04",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CEOKlauePreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        webapp.app.config.update(TESTING=True, SAMMLR_ENV="testing")
        cls.client = webapp.app.test_client()
        cls.manifest = json.loads((PREVIEW_DIR / "build-manifest.json").read_text())

    def setUp(self):
        webapp.app.config["SAMMLR_ENV"] = "testing"

    def test_preview_and_private_font_are_available_only_through_dev_routes(self):
        page = self.client.get("/dev/ceoklaue-preview")
        font = self.client.get("/dev/ceoklaue-preview/font.woff2")
        self.assertEqual(200, page.status_code)
        self.assertEqual(200, font.status_code)
        self.assertEqual("font/woff2", font.mimetype)
        self.assertEqual("no-store", font.headers["Cache-Control"])
        self.assertEqual("noindex, nofollow", font.headers["X-Robots-Tag"])
        self.assertEqual(
            404,
            self.client.get(
                "/Branding/CEOKlaue/03_font/preview/CEOKlaue-v0.2-preview.woff2"
            ).status_code,
        )

    def test_preview_fails_closed_in_production(self):
        webapp.app.config["SAMMLR_ENV"] = "production"
        try:
            self.assertEqual(404, self.client.get("/dev/ceoklaue-preview").status_code)
            self.assertEqual(
                404,
                self.client.get("/dev/ceoklaue-preview/font.woff2").status_code,
            )
        finally:
            webapp.app.config["SAMMLR_ENV"] = "testing"

    def test_manifest_contains_the_exact_provisional_selection(self):
        self.assertEqual(EXPECTED_PO_SELECTIONS, self.manifest["po_selections"])
        self.assertEqual(72, len(self.manifest["po_selections"]))
        self.assertEqual(
            {"K": "03", "P": "03", "k": "03", "0": "03"},
            self.manifest["open_selections_using_v0.1_variant_03"],
        )
        self.assertEqual("ÄÖÜ;", self.manifest["missing_source_backed_characters"])

    def test_preview_font_is_separate_and_contains_the_expected_character_set(self):
        response = self.client.get("/dev/ceoklaue-preview/font.woff2")
        font = TTFont(io.BytesIO(response.data))
        cmap = font.getBestCmap()
        for character in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789äöüß.,:!?-+/()":
            self.assertIn(ord(character), cmap)
        for character in "ÄÖÜ;":
            self.assertNotIn(ord(character), cmap)
        names = font["name"].names
        decoded = {record.toUnicode() for record in names}
        self.assertIn("CEOKlaue v0.2 Preview", decoded)
        self.assertNotEqual(
            digest(PREVIEW_DIR / "CEOKlaue-v0.2-preview.woff2"),
            digest(APP_DIR / "static" / "fonts" / "ceoklaue-final-alt1.woff2"),
        )

    def test_contour_expansion_is_moderate_and_preserves_critical_counters(self):
        thickening = self.manifest["contour_thickening"]
        self.assertEqual("binary mask dilation before vectorization", thickening["method"])
        self.assertEqual([3, 3], thickening["kernel"])
        self.assertEqual("ellipse", thickening["kernel_shape"])
        self.assertEqual(1, thickening["iterations"])
        audit = self.manifest["critical_counter_audit"]
        self.assertEqual(set("ea68BR"), set(audit))
        for counts in audit.values():
            self.assertGreater(counts["before"], 0)
            self.assertGreaterEqual(counts["after"], counts["before"])

    def test_optical_normalization_and_font_metrics_are_declared_and_bounded(self):
        normalization = self.manifest["normalization"]
        self.assertEqual(
            "uniform optical outlier scaling with preserved group variation",
            normalization["strategy"],
        )
        self.assertEqual(1.30, normalization["factors"]["U"])
        self.assertEqual(45, normalization["side_bearing_units"])
        self.assertEqual(500, normalization["cap_height_units"])
        self.assertEqual(390, normalization["x_height_units"])

        font = TTFont(PREVIEW_DIR / "CEOKlaue-v0.2-preview.ttf")
        cmap = font.getBestCmap()
        glyphs = font["glyf"]

        def heights(characters):
            return [
                glyphs[cmap[ord(character)]].yMax - glyphs[cmap[ord(character)]].yMin
                for character in characters
            ]

        for reference_group, maximum_ratio in (
            ("ABMNRTUVW", 1.15),
            ("acemnorsuvwxz", 1.20),
            ("0123456789", 1.14),
        ):
            measured = heights(reference_group)
            self.assertLessEqual(max(measured) / min(measured), maximum_ratio)

        self.assertEqual(500, font["OS/2"].sCapHeight)
        self.assertEqual(390, font["OS/2"].sxHeight)
        for character in self.manifest["character_order"]:
            glyph_name = cmap[ord(character)]
            self.assertEqual(45, font["hmtx"].metrics[glyph_name][1])

    def test_preview_uses_uniform_grid_and_marks_only_open_selections(self):
        html = self.client.get("/dev/ceoklaue-preview").get_data(as_text=True)
        self.assertIn("--paper: #f7f4ec", html)
        self.assertIn("--grid-line: rgba(105, 88, 122, .24)", html)
        self.assertIn("--grid-size: 24px", html)
        self.assertIn("background-size: var(--grid-size) var(--grid-size)", html)
        self.assertNotIn("radial-gradient", html)
        self.assertIn("Typografische Referenzlinien", html)
        self.assertIn("ABMNRTUVW", html)
        self.assertIn("acemnorsuvwxz", html)
        self.assertEqual(4, html.count('class="open-char"'))
        for character in "KPk0":
            self.assertIn(f">{character} · noch v0.1 / nicht ausgewählt</span>", html)
        self.assertIn("FIFA World Cup 2026", html)
        self.assertIn("Aktueller Tausch", html)
        self.assertIn("ABCDEFGHIJKLMNOPQRSTUVWXYZ", html.replace(
            '<span class="open-char" title="noch v0.1 / nicht ausgewählt">', ""
        ).replace("</span>", ""))

    def test_preview_requests_do_not_change_product_or_database_files(self):
        protected = [
            APP_DIR / "static" / "fonts" / "ceoklaue-final-alt1.woff2",
            APP_DIR / "static" / "fonts" / "ceoklaue-final-alt2.woff2",
            APP_DIR / "static" / "fonts" / "ceoklaue-final-alt3.woff2",
            APP_DIR / "static" / "style.css",
            APP_DIR / "Database" / "sammlr.db",
        ]
        before = {path: digest(path) for path in protected}
        self.client.get("/dev/ceoklaue-preview")
        self.client.get("/dev/ceoklaue-preview/font.woff2")
        self.assertEqual(before, {path: digest(path) for path in protected})


if __name__ == "__main__":
    unittest.main()
