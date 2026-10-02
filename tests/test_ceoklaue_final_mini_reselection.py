import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "Branding" / "CEOKlaue"
RAW = WORK / "00_raw"
MANIFEST = WORK / "final-mini-reselection-source-manifest.json"
os.environ.setdefault("SAMMLR_ENV", "testing")
os.environ.setdefault("SAMMLR_SECRET_KEY", "sammlr-explicit-testing-secret")
sys.dont_write_bytecode = True


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CEOKlaueFinalMiniImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_only_two_new_originals_are_byte_exact_archived_images(self):
        expected = {
            "ceoklaue_final_mini_reselection_glyphs_01.jpg": "4558e07c32715f40da6ff301ba7eef14f3c866f53aaee44f6b4af6dc8521431f",
            "ceoklaue_final_mini_reselection_marks_01.jpg": "b568ea40244c1a0852097837172ffbcb1e1bf4abf6ed2b8db15517cdab3bf9d7",
        }
        self.assertEqual(set(expected), {source["filename"] for source in self.manifest["sources"]})
        for filename, sha256 in expected.items():
            path = RAW / filename
            self.assertEqual(sha256, digest(path))
            with Image.open(path) as image:
                self.assertIn(image.format, {"JPEG", "MPO"})
                self.assertEqual((4032, 3024), image.size)

    def test_scope_counts_mapping_and_new_variant_ids_are_exact(self):
        manifest = self.manifest
        self.assertEqual("vwxVX:", manifest["open_characters"])
        self.assertEqual(["receive_circle", "give_cross"], manifest["marker_groups"])
        self.assertEqual(6, manifest["totals"]["font_characters"])
        self.assertEqual(30, manifest["totals"]["font_glyph_candidates"])
        self.assertEqual(10, manifest["totals"]["selection_mark_candidates"])
        expected = {
            "v": ["06", "07", "08", "09", "10"],
            "w": ["06", "07", "08", "09", "10"],
            "x": ["11", "12", "13", "14", "15"],
            "V": ["06", "07", "08", "09", "10"],
            "X": ["06", "07", "08", "09", "10"],
            ":": ["06", "07", "08", "09", "10"],
        }
        self.assertEqual(expected, {record["character"]: record["new_variant_ids"] for record in manifest["characters"]})
        self.assertEqual(
            {"receive_circle": ["01", "02", "03", "04", "05"], "give_cross": ["01", "02", "03", "04", "05"]},
            {record["mark_key"]: record["new_variant_ids"] for record in manifest["selection_marks"]},
        )

    def test_import_is_append_only_and_all_output_hashes_match(self):
        manifest = self.manifest
        self.assertEqual(598, manifest["preexisting_inventory"]["png_count"])
        self.assertEqual(598, manifest["preexisting_inventory"]["svg_count"])
        imported = set()
        for group in ("characters", "selection_marks"):
            for record in manifest[group]:
                for output in record["outputs"]:
                    for kind in ("png", "svg"):
                        path = WORK / output[kind]["path"]
                        imported.add(path)
                        self.assertTrue(path.is_file())
                        self.assertEqual(output[kind]["sha256"], digest(path))
        existing = sorted((WORK / "01_extracted" / "glyphs").glob("*/*.png"))
        existing += sorted((WORK / "02_vectors" / "glyphs").glob("*/*.svg"))
        analog_ui = json.loads(
            (WORK / "analog-ui-final-source-manifest.json").read_text(encoding="utf-8")
        )
        newer = {
            WORK / output[kind]["path"]
            for record in analog_ui["selection_groups"] + analog_ui["fixed_assets"]
            if record["asset_key"] in {"lower_u", "cap_A", "comma", "2"}
            for output in record["outputs"]
            for kind in ("png", "svg")
        }
        payload = "".join(
            f"{path.relative_to(WORK).as_posix()}\0{digest(path)}\n"
            for path in sorted(set(existing) - imported - newer)
        )
        self.assertEqual(
            manifest["preexisting_inventory"]["sha256"],
            hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        )
        self.assertFalse(manifest["policy"]["existing_variants_replaced"])
        self.assertFalse(manifest["policy"]["accepted_triple_sets_changed"])
        self.assertEqual([], manifest["policy"]["product_assets_written"])

    def test_every_new_raster_has_a_six_pixel_safe_margin(self):
        for group in ("characters", "selection_marks"):
            for record in self.manifest[group]:
                for output in record["outputs"]:
                    path = WORK / output["png"]["path"]
                    with Image.open(path).convert("RGBA") as image:
                        bounds = image.getchannel("A").getbbox()
                        self.assertIsNotNone(bounds, path)
                        left, top, right, bottom = bounds
                        margins = (left, top, image.width - right, image.height - bottom)
                        self.assertGreaterEqual(min(margins), 6, path)

    def test_importer_is_idempotent_and_product_assets_are_out_of_scope(self):
        result = subprocess.run(
            [sys.executable, str(WORK / "import_final_mini_reselection_sources.py")],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("already imported and verified", result.stdout)
        policy = self.manifest["policy"]
        self.assertFalse(policy["automatic_selection"])
        self.assertFalse(policy["harmony_assets_changed"])
        self.assertFalse(policy["runtime_fonts_changed"])
        self.assertFalse(policy["productive_sticker_assets_changed"])


if __name__ == "__main__":
    unittest.main()
