import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "Branding" / "CEOKlaue"
RAW = WORK / "00_raw"
MANIFEST = WORK / "analog-ui-final-source-manifest.json"
os.environ.setdefault("SAMMLR_ENV", "testing")
os.environ.setdefault("SAMMLR_SECRET_KEY", "sammlr-explicit-testing-secret")
sys.dont_write_bytecode = True


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CEOKlaueAnalogUIFinalImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_seven_new_originals_are_byte_exact_archived_and_documented(self):
        expected = {
            "ceoklaue_analog_ui_final_01.jpg": "499da63b20d435d1cb15aa0537d269add64e597854dc3820a5b41b971fcb2ed9",
            "ceoklaue_analog_ui_final_02.jpg": "c1953532155354337422769f81489e0b89f7ee3d432ecc10ce437b20aa311efc",
            "ceoklaue_analog_ui_final_03.jpg": "06bd6f9fb4907d61ef99ed3e561ac14a20aa9049f61b45cf4bec2352c578c958",
            "ceoklaue_analog_ui_final_04.jpg": "33ee48f38b5a658a20f4d9582d14103892bc9794dc3da44a6675bd533eee96e5",
            "ceoklaue_analog_ui_final_05.jpg": "47067a154ecc82b47e36379205dccd61e1cdeac512d0150c12c57acb64a2f754",
            "ceoklaue_analog_ui_final_06.jpg": "44686d072d1b32bf3e340c6c50cbbbc461c8facb90d79762201bc8890ff971fd",
            "ceoklaue_analog_ui_final_07.jpg": "a99cc75dadf25c57e7437621d34ecd05245ce58539db66d5176d77f72cb73f19",
        }
        self.assertEqual(set(expected), {source["filename"] for source in self.manifest["sources"]})
        self.assertEqual(
            [f"IMG_{number}.JPG" for number in range(7178, 7185)],
            [source["original_filename"] for source in self.manifest["sources"]],
        )
        for filename, sha256 in expected.items():
            path = RAW / filename
            self.assertEqual(sha256, digest(path))
            with Image.open(path) as image:
                self.assertIn(image.format, {"JPEG", "MPO"})
                self.assertEqual((4032, 3024), image.size)

    def test_scope_counts_and_append_only_variant_ids_are_exact(self):
        expected_groups = {
            "u": ("lower_u", ["06", "07", "08", "09", "10"]),
            "A": ("cap_A", ["06", "07", "08", "09", "10"]),
            ",": ("comma", ["06", "07", "08", "09", "10"]),
            "middle_dot": ("middle_dot", ["01", "02", "03", "04", "05"]),
        }
        self.assertEqual(
            expected_groups,
            {
                record["selection_key"]: (record["asset_key"], record["new_variant_ids"])
                for record in self.manifest["selection_groups"]
            },
        )
        totals = self.manifest["totals"]
        expected_counts = {
            "digit_2_replacements": 1,
            "back_arrows": 5,
            "wordmarks": 1,
            "phrase_assets": 10,
            "underlines": 6,
            "boxes": 6,
            "line_components": 12,
            "extracted_pngs": 61,
            "generated_svgs": 61,
        }
        for key, value in expected_counts.items():
            self.assertEqual(value, totals[key], key)
        replacement = next(
            record for record in self.manifest["fixed_assets"]
            if record.get("inventory_key") == "digit_2_replacement_alt1"
        )
        self.assertEqual("2", replacement["asset_key"])
        self.assertEqual(["11"], replacement["new_variant_ids"])
        self.assertEqual(
            ["phrase_du_bekommst", "phrase_mehr_anzeigen"],
            self.manifest["not_found_in_new_sources"],
        )

    def test_every_output_hash_and_safe_transparent_margin_matches(self):
        imported = set()
        for record in self.manifest["selection_groups"] + self.manifest["fixed_assets"]:
            for output in record["outputs"]:
                for kind in ("png", "svg"):
                    path = WORK / output[kind]["path"]
                    imported.add(path)
                    self.assertTrue(path.is_file())
                    self.assertEqual(output[kind]["sha256"], digest(path))
                with Image.open(WORK / output["png"]["path"]).convert("RGBA") as image:
                    left, top, right, bottom = image.getchannel("A").getbbox()
                    self.assertGreaterEqual(min(left, top, image.width - right, image.height - bottom), 8)

        preexisting = sorted((WORK / "01_extracted" / "glyphs").glob("*/*.png"))
        preexisting += sorted((WORK / "02_vectors" / "glyphs").glob("*/*.svg"))
        payload = "".join(
            f"{path.relative_to(WORK).as_posix()}\0{digest(path)}\n"
            for path in sorted(set(preexisting) - imported)
        )
        self.assertEqual(
            self.manifest["preexisting_glyph_inventory"]["sha256"],
            hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        )

    def test_import_is_idempotent_and_product_scope_is_locked(self):
        result = subprocess.run(
            [sys.executable, str(WORK / "import_analog_ui_final_sources.py")],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("already imported and verified", result.stdout)
        policy = self.manifest["policy"]
        self.assertTrue(policy["append_only"])
        for key in (
            "automatic_selection", "product_integration", "accepted_82x3_masterset_changed",
            "harmony_changed", "runtime_changed", "sticker_list_changed", "sticker_wall_changed",
        ):
            self.assertFalse(policy[key], key)
        self.assertEqual([], policy["product_assets_written"])

    def test_database_is_unchanged_and_final_master_shape_is_preserved(self):
        expected = {
            "App/Database/sammlr.db": "df9a4887f3e29f81f5897020c1058e9e8b98d86d3fe9e8dc878057df39923fbe",
        }
        for relative, sha256 in expected.items():
            self.assertEqual(sha256, digest(ROOT / relative), relative)
        harmony = json.loads((WORK / "04_harmony" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(82, len(harmony["characters"]))
        self.assertTrue(all(len(record["alternates"]) == 3 for record in harmony["characters"]))

        marker_hashes = {
            "receive_circle_01.svg": "15392d8958c32075c289c7e5425b9e7b3408ada862a2ef66941161141be2b187",
            "receive_circle_02.svg": "1875d45adf1b060091a5658011d66f33d8d412d8542a27a7d304d5a20b2fdce9",
            "receive_circle_03.svg": "9af9edd51adc78a510daeb4ab5c880e4cb6bfbc9de08d28f3d20d541026de07a",
            "receive_circle_04.svg": "7c21af09d5bbe6784b9700f36856e435d748b50209787ec6576e5ec538cf7c23",
            "receive_circle_05.svg": "f09b2e8d32e6756c1301aa341c257d64838825fe9e358b0ae6ffb0b7a3e5dbc6",
        }
        for family in ("receive_circle",):
            for path in sorted((ROOT / "App" / "static" / "ceoklaue-markers" / family).glob("*.svg")):
                self.assertEqual(marker_hashes[path.name], digest(path), path.name)

    def test_release_master_shape_and_marker_hashes(self):
        harmony = json.loads((WORK / "04_harmony" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(82, len(harmony["characters"]))
        self.assertTrue(all(len(record["alternates"]) == 3 for record in harmony["characters"]))

        marker_hashes = {
            "receive_circle_01.svg": "15392d8958c32075c289c7e5425b9e7b3408ada862a2ef66941161141be2b187",
            "receive_circle_02.svg": "1875d45adf1b060091a5658011d66f33d8d412d8542a27a7d304d5a20b2fdce9",
            "receive_circle_03.svg": "9af9edd51adc78a510daeb4ab5c880e4cb6bfbc9de08d28f3d20d541026de07a",
            "receive_circle_04.svg": "7c21af09d5bbe6784b9700f36856e435d748b50209787ec6576e5ec538cf7c23",
            "receive_circle_05.svg": "f09b2e8d32e6756c1301aa341c257d64838825fe9e358b0ae6ffb0b7a3e5dbc6",
        }
        for family in ("receive_circle",):
            for path in sorted((ROOT / "App" / "static" / "ceoklaue-markers" / family).glob("*.svg")):
                self.assertEqual(marker_hashes[path.name], digest(path), path.name)

    def test_database_integrity_and_foreign_keys(self):
        with sqlite3.connect(ROOT / "App" / "Database" / "sammlr.db") as connection:
            self.assertEqual("ok", connection.execute("PRAGMA integrity_check").fetchone()[0])
            self.assertEqual([], connection.execute("PRAGMA foreign_key_check").fetchall())


if __name__ == "__main__":
    unittest.main()
