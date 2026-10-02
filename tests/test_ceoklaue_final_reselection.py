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
MANIFEST = WORK / "final-reselection-source-manifest.json"
os.environ.setdefault("SAMMLR_ENV", "testing")
os.environ.setdefault("SAMMLR_SECRET_KEY", "sammlr-explicit-testing-secret")
sys.dont_write_bytecode = True


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CEOKlaueFinalReselectionImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_two_new_originals_are_exact_archived_jpegs(self):
        expected = {
            "ceoklaue_final_reselection_01.jpg": "77fd1bf51a10098fc0076a57f94583d686647b74fa65cfa6baf402b1a6f0f9a3",
            "ceoklaue_final_reselection_02.jpg": "a2794ad5ca03a08843ed38d8ebf455ee6ef523a621b8bd9b3ab3f8d357ec4018",
        }
        self.assertEqual(set(expected), {source["filename"] for source in self.manifest["sources"]})
        for filename, sha256 in expected.items():
            path = RAW / filename
            self.assertEqual(sha256, digest(path))
            with Image.open(path) as image:
                self.assertEqual("JPEG", image.format)
                self.assertEqual((4032, 3024), image.size)

    def test_scope_counts_and_new_variant_ids_are_exact(self):
        manifest = self.manifest
        self.assertEqual("HZzxhDF2ß", manifest["open_characters"])
        self.assertEqual(
            {
                "characters": 9,
                "recognized_handwritten_sources": 44,
                "extracted_pngs": 44,
                "generated_svgs": 44,
                "discarded_sources": 0,
            },
            manifest["totals"],
        )
        expected = {
            "H": ["11", "12", "13", "14", "15"],
            "Z": ["06", "07", "08", "09", "10"],
            "z": ["06", "07", "08", "09", "10"],
            "x": ["06", "07", "08", "09", "10"],
            "h": ["06", "07", "08", "09"],
            "D": ["06", "07", "08", "09", "10"],
            "F": ["06", "07", "08", "09", "10"],
            "2": ["06", "07", "08", "09", "10"],
            "ß": ["11", "12", "13", "14", "15"],
        }
        records = {record["character"]: record for record in manifest["characters"]}
        self.assertEqual(expected, {character: record["new_variant_ids"] for character, record in records.items()})

    def test_import_is_append_only_and_every_output_hash_matches(self):
        manifest = self.manifest
        self.assertEqual(554, manifest["preexisting_inventory"]["png_count"])
        self.assertEqual(554, manifest["preexisting_inventory"]["svg_count"])
        imported = set()
        for record in manifest["characters"]:
            for output in record["outputs"]:
                for kind in ("png", "svg"):
                    path = WORK / output[kind]["path"]
                    imported.add(path)
                    self.assertTrue(path.is_file())
                    self.assertEqual(output[kind]["sha256"], digest(path))
        pngs = sorted((WORK / "01_extracted" / "glyphs").glob("*/*.png"))
        svgs = sorted((WORK / "02_vectors" / "glyphs").glob("*/*.svg"))
        self.assertEqual(644, len(pngs))
        self.assertEqual(644, len(svgs))
        mini_manifest = json.loads(
            (WORK / "final-mini-reselection-source-manifest.json").read_text(encoding="utf-8")
        )
        newer = {
            WORK / output[kind]["path"]
            for record in mini_manifest["characters"]
            for output in record["outputs"]
            for kind in ("png", "svg")
        }
        analog_ui = json.loads(
            (WORK / "analog-ui-final-source-manifest.json").read_text(encoding="utf-8")
        )
        newer.update({
            WORK / output[kind]["path"]
            for record in analog_ui["selection_groups"] + analog_ui["fixed_assets"]
            if record["asset_key"] in {"lower_u", "cap_A", "comma", "2"}
            for output in record["outputs"]
            for kind in ("png", "svg")
        })
        payload = "".join(
            f"{path.relative_to(WORK).as_posix()}\0{digest(path)}\n"
            for path in sorted(set(pngs + svgs) - imported - newer)
        )
        self.assertEqual(
            manifest["preexisting_inventory"]["sha256"],
            hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        )

    def test_every_new_raster_has_a_safe_ink_margin(self):
        for record in self.manifest["characters"]:
            for output in record["outputs"]:
                path = WORK / output["png"]["path"]
                with Image.open(path).convert("RGBA") as image:
                    bounds = image.getchannel("A").getbbox()
                    self.assertIsNotNone(bounds, path)
                    left, top, right, bottom = bounds
                    margins = (left, top, image.width - right, image.height - bottom)
                    self.assertGreaterEqual(min(margins), 6, path)

    def test_importer_is_idempotent_and_final_master_references_it_without_mutation(self):
        result = subprocess.run(
            [sys.executable, str(WORK / "import_final_reselection_sources.py")],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("already imported and verified", result.stdout)
        runtime = json.loads(
            (WORK / "05_runtime" / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            runtime["master"]["harmony_manifest_sha256"],
            digest(WORK / "04_harmony" / "manifest.json"),
        )
        self.assertFalse(self.manifest["policy"]["existing_variants_replaced"])
        self.assertFalse(self.manifest["policy"]["accepted_triple_sets_changed"])
        self.assertFalse(self.manifest["policy"]["automatic_selection"])
        self.assertFalse(self.manifest["policy"]["harmony_font_built"])
        self.assertEqual([], self.manifest["policy"]["product_assets_written"])


if __name__ == "__main__":
    unittest.main()
