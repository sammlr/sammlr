import hashlib
from html import unescape
import json
import os
from pathlib import Path
import re
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "App"
WORK = ROOT / "Branding" / "CEOKlaue"
HARMONY = WORK / "04_harmony"
HARMONY_BUILDER = HARMONY / "build_harmony_assets.py"
os.environ.setdefault("SAMMLR_ENV", "testing")
os.environ.setdefault("SAMMLR_SECRET_KEY", "sammlr-explicit-testing-secret")
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402


EXPECTED_SELECTION_TEXT = """
A=07,08,09
B=05,01,03
C=01,03,02
D=09,01,05
E=03,05,01
F=05,02,01
G=01,09,07
H=01,04,05
I=01,02,04
J=10,07,06
K=06,08,07
L=07,06,09
M=03,06,07
N=03,08,07
O=07,08,10
P=06,08,09
Q=07,10,08
R=06,07,08
S=06,09,08
T=02,01,03
U=04,01,08
V=07,09,10
W=06,08,09
X=06,09,10
Y=03,01,04
Z=08,09,10
a=03,02,04
b=05,04,02
c=04,02,03
d=02,01,04
e=01,08,10
f=05,03,02
g=03,02,01
h=05,01,08
i=04,03,05
j=05,01,02
k=06,09,08
l=03,04,05
m=02,01,04
n=05,01,03
o=04,01,02
p=02,01,05
q=05,01,04
r=03,01,05
s=03,02,05
t=04,01,02
u=06,08,10
v=07,09,08
w=08,10,09
x=12,11,13
y=02,03,01
z=07,08,10
0=06,09,08
1=01,07,09
2=11,09,10
3=01,07,09
4=02,07,06
5=02,01,03
6=07,08,10
7=05,03,01
8=03,06,10
9=05,01,02
ä=04,03,05
ö=07,08,09
ü=06,08,07
Ä=04,01,03
Ö=02,05,03
Ü=02,04,05
ß=12,13,14
.=03,05,02
,=06,08,09
:=07,09,10
;=03,04,02
!=05,04,01
?=07,06,09
-=04,03,02
+=02,04,03
/=03,01,04
&=06,08,09
%=06,07,08
(=06,07,09
)=04,01,02
""".strip()
EXPECTED = {
    line.split("=", 1)[0]: tuple(line.split("=", 1)[1].split(","))
    for line in EXPECTED_SELECTION_TEXT.splitlines()
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def section(html, name):
    match = re.search(
        rf'<section class="[^"]+" data-section="{re.escape(name)}".*?</section>',
        html,
        re.DOTALL,
    )
    if not match:
        raise AssertionError(f"Missing Harmony section {name}")
    return match.group(0)


def glyph_data(html):
    return [
        (unescape(character), int(alternate), variant)
        for character, alternate, variant in re.findall(
            r'data-character="([^"]+)" data-alternate="([123])" data-variant="(\d{2})"',
            html,
        )
    ]


class CEOKlaueHarmonyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        webapp.app.config.update(TESTING=True, SAMMLR_ENV="testing")
        webapp.ceoklaue_harmony_manifest.cache_clear()
        cls.client = webapp.app.test_client()
        cls.manifest = json.loads((HARMONY / "manifest.json").read_text(encoding="utf-8"))

    def setUp(self):
        webapp.app.config["SAMMLR_ENV"] = "testing"

    def page(self):
        response = self.client.get("/dev/ceoklaue-harmony")
        self.assertEqual(200, response.status_code)
        self.assertEqual("no-store", response.headers["Cache-Control"])
        self.assertEqual("noindex, nofollow", response.headers["X-Robots-Tag"])
        return response.get_data(as_text=True)

    def test_manifest_contains_exactly_the_binding_po_triples(self):
        records = {record["character"]: record for record in self.manifest["characters"]}
        self.assertEqual(82, self.manifest["selected_characters"])
        self.assertEqual(246, self.manifest["selected_glyphs"])
        self.assertEqual(set(EXPECTED), set(records))
        for character, variants in EXPECTED.items():
            self.assertEqual(
                variants,
                tuple(alternate["variant"] for alternate in records[character]["alternates"]),
            )
            self.assertEqual([1, 2, 3], [a["alternate"] for a in records[character]["alternates"]])

    def test_all_sources_and_private_assets_are_hash_verified(self):
        assets = []
        for record in self.manifest["characters"]:
            for alternate in record["alternates"]:
                source = WORK / alternate["source"]
                asset = HARMONY / alternate["asset"]
                self.assertEqual(alternate["source_sha256"], digest(source))
                self.assertEqual(alternate["asset_sha256"], digest(asset))
                assets.append(asset)
        self.assertEqual(246, len(assets))
        self.assertEqual(246, len(list((HARMONY / "glyphs").glob("*/*.svg"))))
        payload = "".join(
            f"{path.relative_to(WORK).as_posix()}\0{digest(path)}\n" for path in sorted(assets)
        )
        self.assertEqual(
            self.manifest["asset_inventory_sha256"],
            hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        )

    def test_harmonization_is_adaptive_bounded_and_topology_preserving(self):
        normalization = self.manifest["normalization"]
        self.assertEqual("adaptive normalized thickness and ink-density corridor", normalization["stroke_strategy"])
        self.assertTrue(normalization["aspect_ratio_preserved"])
        for forbidden in ("rotation", "baseline_jitter", "size_jitter", "blur"):
            self.assertFalse(normalization[forbidden])
        operations = set()
        for record in self.manifest["characters"]:
            for alternate in record["alternates"]:
                audit = alternate["stroke_audit"]
                operations.add(audit["operation"])
                self.assertTrue(audit["ink_density_considered"])
                self.assertLessEqual(audit["steps"], 8)
                self.assertEqual(audit["topology_before"], audit["topology_after"])
        self.assertEqual({"none", "dilate", "erode"}, operations)

    def test_fixed_alphabets_use_only_their_declared_alternate(self):
        html = self.page()
        for alternate in (1, 2, 3):
            data = glyph_data(section(html, f"alphabet-{alternate}"))
            self.assertEqual(82, len(data))
            self.assertEqual({alternate}, {item[1] for item in data})
            self.assertEqual(
                [EXPECTED[character][alternate - 1] for character in self.manifest["character_order"]],
                [variant for _character, _alternate, variant in data],
            )

    def test_mixed_samples_use_all_alternates_without_simple_periodicity(self):
        html = self.page()
        mixed = glyph_data(section(html, "mixed"))
        self.assertEqual(82, len(mixed))
        sequence = [alternate for _character, alternate, _variant in mixed]
        self.assertEqual({1, 2, 3}, set(sequence))
        self.assertNotEqual([index % 3 + 1 for index in range(len(sequence))], sequence)
        for name in ("words", "codes"):
            self.assertEqual({1, 2, 3}, {item[1] for item in glyph_data(section(html, name))})

    def test_every_rendered_asset_is_selected_and_mixing_is_reload_stable(self):
        first = self.page()
        second = self.page()
        self.assertEqual(first, second)
        rendered = glyph_data(first)
        self.assertGreater(len(rendered), 246)
        for character, alternate, variant in rendered:
            self.assertEqual(EXPECTED[character][alternate - 1], variant)
        self.assertIsNone(re.search(r"(?:^|[;{])\s*transform\s*:", first, re.MULTILINE))
        self.assertIsNone(re.search(r"(?:^|[;{])\s*filter\s*:", first, re.MULTILINE))
        self.assertNotIn("dashed", first)
        self.assertNotIn("dotted", first)
        self.assertIn("background-size: var(--grid-size) var(--grid-size)", first)

    def test_words_codes_and_mar_series_are_present(self):
        html = self.page()
        for sample in (
            "Sammlr.", "FIFA World Cup 2026", "Fehlende Sticker",
            "Doppelte Sticker", "Aktueller Tausch", "Du bekommst:",
            "Du gibst ab:", "Sticker suchen", "Zurück zum Album",
            "650 gesammelt", "342 fehlend", "110 doppelt",
            "3 erhalten · 2 abgegeben", "GER13", "BRA20", "MAR20",
            "MEX12", "USA15", "VFL149",
        ):
            self.assertIn(f'aria-label="{sample}"', html)
        self.assertIn('aria-label="MAR1 MAR2 MAR3 MAR4 MAR5 MAR6 MAR7 MAR8 MAR9 MAR10"', html)
        repeated = re.search(
            r'<span class="hand-run" role="img" aria-label="Sticker suchen".*?</span>',
            html,
            re.DOTALL,
        ).group(0)
        repeated_alternates = [
            alternate for character, alternate, _variant in glyph_data(repeated) if character in "Stekr"
        ]
        self.assertGreater(len(set(repeated_alternates)), 1)

    def test_final_markers_are_rotated_left_and_visible_in_final_control_sections(self):
        markers = self.manifest["selection_markers"]
        self.assertEqual(10, markers["selected_markers"])
        self.assertEqual(-90, markers["normalization"]["rotation_degrees"])
        self.assertEqual("counterclockwise", markers["normalization"]["rotation_direction"])
        expected = {
            "receive_circle": ["01", "02", "04", "03", "05"],
            "give_cross": ["05", "03", "04", "01", "02"],
        }
        self.assertEqual(
            expected,
            {record["family"]: record["selected_variants"] for record in markers["families"]},
        )
        builder_source = HARMONY_BUILDER.read_text(encoding="utf-8")
        self.assertIn("cv2.ROTATE_90_COUNTERCLOCKWISE", builder_source)
        for record in markers["families"]:
            for variant in record["variants"]:
                self.assertEqual(-90, variant["rotation_degrees"])
                self.assertEqual("counterclockwise", variant["rotation_direction"])
                self.assertEqual(variant["source_sha256"], digest(WORK / variant["source"]))
                self.assertEqual(variant["asset_sha256"], digest(HARMONY / variant["asset"]))
        html = self.page()
        self.assertEqual(10, html.count('class="marker-sample"'))
        self.assertIn('data-section="receive-circle"', html)
        self.assertIn('data-section="give-cross"', html)
        self.assertIn('data-section="marker-context"', html)
        self.assertEqual(6, html.count('class="marker-context-token"'))

    def test_assets_are_allowlisted_private_and_production_fails_closed(self):
        selected = self.client.get("/dev/ceoklaue-harmony/glyph/cap_G/cap_G_09.svg")
        self.assertEqual(200, selected.status_code)
        self.assertEqual("image/svg+xml", selected.mimetype)
        self.assertEqual("no-store", selected.headers["Cache-Control"])
        self.assertEqual(404, self.client.get("/dev/ceoklaue-harmony/glyph/cap_G/cap_G_05.svg").status_code)
        marker = self.client.get(
            "/dev/ceoklaue-harmony/marker/receive_circle/receive_circle_01.svg"
        )
        self.assertEqual(200, marker.status_code)
        self.assertEqual("image/svg+xml", marker.mimetype)
        self.assertEqual(
            404,
            self.client.get(
                "/dev/ceoklaue-harmony/marker/receive_circle/receive_circle_99.svg"
            ).status_code,
        )
        self.assertEqual(404, self.client.get("/Branding/CEOKlaue/04_harmony/glyphs/cap_G/cap_G_09.svg").status_code)
        webapp.app.config["SAMMLR_ENV"] = "production"
        try:
            self.assertEqual(404, self.client.get("/dev/ceoklaue-harmony").status_code)
            self.assertEqual(404, self.client.get("/dev/ceoklaue-harmony/glyph/cap_G/cap_G_09.svg").status_code)
            self.assertEqual(
                404,
                self.client.get(
                    "/dev/ceoklaue-harmony/marker/receive_circle/receive_circle_01.svg"
                ).status_code,
            )
        finally:
            webapp.app.config["SAMMLR_ENV"] = "testing"


if __name__ == "__main__":
    unittest.main()
