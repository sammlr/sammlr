import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "App"
WORK = ROOT / "Branding" / "CEOKlaue"
RAW = WORK / "00_raw"
MANIFEST = WORK / "completion-source-manifest.json"
os.environ.setdefault("SAMMLR_ENV", "testing")
os.environ.setdefault("SAMMLR_SECRET_KEY", "sammlr-explicit-testing-secret")
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CEOKlaueCompletionImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_raw_sources_are_exact_archived_original_jpegs(self):
        expected = {
            "ceoklaue_completion_caps_lower_01.jpeg": "24b74b7fc4b3addc646452686977830a3525fa53450e548a716802d1a9a8f630",
            "ceoklaue_completion_numbers_umlauts_01.jpeg": "202b5fa8201ab20775771db719516b85aaf6e6b54f6118941be9c61e134412c9",
            "ceoklaue_completion_symbols_01.jpeg": "a9821df92b78a3cfc626efb489004549cfb25beb17ae918b539f02bd99f283f3",
        }
        archived = {source["filename"] for source in self.manifest["sources"]}
        self.assertEqual(set(expected), archived)
        for filename, sha256 in expected.items():
            path = RAW / filename
            self.assertEqual(sha256, digest(path))
            with Image.open(path) as image:
                self.assertEqual("JPEG", image.format)
                self.assertEqual((4032, 3024), image.size)

    def test_manifest_records_exact_append_only_completion_inventory(self):
        manifest = self.manifest
        self.assertEqual("CEOKlaue final completion source import v1", manifest["version"])
        self.assertEqual(
            {
                "characters": 33,
                "recognized_handwritten_sources": 165,
                "extracted_pngs": 165,
                "generated_svgs": 165,
                "discarded_sources": 0,
            },
            manifest["totals"],
        )
        self.assertEqual(389, manifest["preexisting_inventory"]["png_count"])
        self.assertEqual(389, manifest["preexisting_inventory"]["svg_count"])
        records = {record["character"]: record for record in manifest["characters"]}
        self.assertEqual(set("GHJKLMNOPQRSUWek013468öüÄÖÜß(&%?;"), set(records))
        for character, record in records.items():
            expected_ids = ["01", "02", "03", "04", "05"] if character in "ÄÖÜ;" else ["06", "07", "08", "09", "10"]
            self.assertEqual(expected_ids, record["new_variant_ids"])
            self.assertEqual(5, record["recognized_handwritten_sources"])
            self.assertEqual(5, len(record["outputs"]))

    def test_outputs_exist_match_hashes_and_preserve_old_inventory(self):
        imported = set()
        for record in self.manifest["characters"]:
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
        reselection = json.loads(
            (WORK / "final-reselection-source-manifest.json").read_text(encoding="utf-8")
        )
        later_imported = {
            WORK / output[kind]["path"]
            for record in reselection["characters"]
            for output in record["outputs"]
            for kind in ("png", "svg")
        }
        mini_reselection = json.loads(
            (WORK / "final-mini-reselection-source-manifest.json").read_text(encoding="utf-8")
        )
        later_imported.update({
            WORK / output[kind]["path"]
            for record in mini_reselection["characters"]
            for output in record["outputs"]
            for kind in ("png", "svg")
        })
        analog_ui = json.loads(
            (WORK / "analog-ui-final-source-manifest.json").read_text(encoding="utf-8")
        )
        later_imported.update({
            WORK / output[kind]["path"]
            for record in analog_ui["selection_groups"] + analog_ui["fixed_assets"]
            if record["asset_key"] in {"lower_u", "cap_A", "comma", "2"}
            for output in record["outputs"]
            for kind in ("png", "svg")
        })
        payload = "".join(
            f"{path.relative_to(WORK).as_posix()}\0{digest(path)}\n"
            for path in sorted(set(pngs + svgs) - imported - later_imported)
        )
        self.assertEqual(
            self.manifest["preexisting_inventory"]["sha256"],
            hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        )

    def test_importer_is_idempotent_and_catalog_exposes_every_variant(self):
        result = subprocess.run(
            [sys.executable, str(WORK / "import_completion_sources.py")],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("already imported and verified", result.stdout)
        webapp.ceoklaue_vector_catalog.cache_clear()
        catalog = webapp.ceoklaue_vector_catalog()
        self.assertEqual(82, len(catalog))
        self.assertEqual(
            644, sum(len(entry["variants"]) for entry in catalog.values())
        )
        self.assertEqual(
            [f"cap_G_{index:02d}.svg" for index in range(1, 11)],
            [variant["filename"] for variant in catalog["cap_G"]["variants"]],
        )
        self.assertEqual(
            [f"uni00C4_{index:02d}.svg" for index in range(1, 6)],
            [variant["filename"] for variant in catalog["uni00C4"]["variants"]],
        )


if __name__ == "__main__":
    unittest.main()
