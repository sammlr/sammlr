import atexit
import hashlib
import os
from pathlib import Path
import re
import shutil
import tempfile
from types import SimpleNamespace
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "App"
LOCAL_DB = APP_DIR / "Database" / "sammlr.db"
REFERENCE_DB = APP_DIR / "Database" / "sammlr_reference_s00.db"
STYLE_PATH = APP_DIR / "static" / "style.css"
READ_ONLY_SCRIPT_PATH = APP_DIR / "static" / "sticker_wall_read_only.js"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-wall-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_DB, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
os.sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402


class ReadOnlyInventory:
    def availability_snapshot_for(self, _code):
        return SimpleNamespace(incoming_transit=0)


class StickerWallProductIslandTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = sha256(LOCAL_DB)
        cls.style = STYLE_PATH.read_text(encoding="utf-8")
        cls.read_only_script = READ_ONLY_SCRIPT_PATH.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == sha256(LOCAL_DB)

    def render_pair(self, album_id):
        codes = tuple(webapp.all_codes(album_id))
        quantities = {
            code: {"quantity": index % 3}
            for index, code in enumerate(codes[:9])
        }
        inventory = ReadOnlyInventory()
        owner = webapp.canonical_sticker_wall_html(
            album_id,
            quantities,
            inventory,
            "all",
            can_edit_inventory=True,
        )
        public = webapp.canonical_sticker_wall_html(
            album_id,
            quantities,
            inventory,
            "all",
            can_edit_inventory=False,
            public_detail_base=f"/profil/public/album/{album_id}",
        )
        return codes, owner, public

    def test_owner_and_public_share_renderer_geometry_order_and_retro_digits(self):
        for album_id in ("em24", "wm26"):
            with self.subTest(album_id=album_id):
                codes, owner, public = self.render_pair(album_id)
                owner_codes = re.findall(r'data-code="([^"]+)"', owner)
                public_codes = re.findall(r'data-code="([^"]+)"', public)
                self.assertEqual(owner_codes, public_codes)
                self.assertEqual(set(codes), set(public_codes))
                self.assertEqual(len(codes), len(public_codes))
                self.assertEqual(len(codes), len(set(public_codes)))
                self.assertEqual(
                    re.findall(r'<h[23] id="([^"]+)"', owner),
                    re.findall(r'<h[23] id="([^"]+)"', public),
                )
                self.assertEqual(owner.count("variant-v3"), public.count("variant-v3"))
                self.assertIn('data-sticker-wall-renderer="canonical"', owner)
                self.assertIn('data-sticker-wall-renderer="canonical"', public)

    def test_capability_contract_keeps_owner_controls_out_of_public_wall(self):
        _codes, owner, public = self.render_pair("wm26")
        self.assertIn('data-wall-capability="edit"', owner)
        self.assertIn("data-quantity-delta", owner)
        self.assertIn("sticker-inline-control", owner)
        self.assertIn('data-wall-capability="read-only"', public)
        self.assertNotIn("data-quantity-delta", public)
        self.assertNotIn("sticker-inline-control", public)
        self.assertNotIn("<form", public.lower())
        self.assertNotIn("fetch(", self.read_only_script)
        self.assertNotIn("method:", self.read_only_script)

    def test_public_large_albums_use_chapters_not_a_flat_legacy_wall(self):
        for album_id in ("em24", "wm26"):
            with self.subTest(album_id=album_id):
                codes, _owner, public = self.render_pair(album_id)
                self.assertGreater(public.count('data-wall-chapter'), 1)
                self.assertEqual(len(codes), public.count('data-sticker-frame'))
                self.assertNotIn("public-sticker-wall", public)
                self.assertNotIn("chapter-collapsed", public)
                self.assertIn('aria-expanded="true"', public)
        _codes, _owner, wm26_public = self.render_pair("wm26")
        self.assertIn("sticker-team-block", wm26_public)

    def test_missing_wall_border_is_explicitly_solid(self):
        rule = re.search(
            r"\.s30-album-page \.sticker-slot-frame \.slot\.missing\{([^}]+)\}",
            self.style,
        )
        self.assertIsNotNone(rule)
        self.assertIn("border-style:solid", rule.group(1))
        self.assertNotRegex(rule.group(1), r"\b(?:dashed|dotted)\b")

    def test_code_grammar_splits_prefix_and_identifier_without_hardcodes(self):
        cases = (
            ("NED 15", "NED", "15", "variant-v3"),
            ("NED PTW", "NED", "PTW", "sticker-identifier-text"),
            ("NED SP", "NED", "SP", "sticker-identifier-text"),
            ("WAL 1", "WAL", "1", "variant-v3"),
            ("WAL 2/3", "WAL", "2/3", "sticker-identifier-slash"),
            ("EST 2/3", "EST", "2/3", "sticker-identifier-slash"),
            ("POL/WAL SP", "POL/WAL", "SP", "sticker-identifier-text"),
            ("EST/FIN SP", "EST/FIN", "SP", "sticker-identifier-text"),
        )
        for code, prefix, identifier, marker in cases:
            with self.subTest(code=code):
                html = webapp.sticker_wall_card_inner(
                    "em24", code, {code: {"quantity": 1}}
                )
                self.assertIn(f'<span class="sticker-team">{prefix}</span>', html)
                self.assertIn(marker, html)
                self.assertIn(identifier, html)
                self.assertNotIn(f">{code}</span>", html)

    def test_stack_caps_at_five_layers_without_changing_real_badge_quantity(self):
        inventory = ReadOnlyInventory()
        for quantity in (0, 1, 2, 3, 4, 5, 7, 14):
            with self.subTest(quantity=quantity):
                by_code = {"NED PTW": {"quantity": quantity}}
                html = webapp.sticker_wall_slot_html(
                    "em24",
                    "NED PTW",
                    by_code,
                    inventory,
                    "missing" if quantity == 0 else "duplicate" if quantity > 1 else "owned",
                    "NED PTW",
                    can_edit_inventory=False,
                )
                self.assertIn(f'data-stack-quantity="{quantity}"', html)
                visible_layers = min(quantity, 5)
                self.assertIn(
                    f'data-visible-stack-layers="{visible_layers}"', html
                )
                self.assertEqual(max(visible_layers - 1, 0), html.count("data-stack-layer="))
                if quantity <= 1:
                    self.assertNotIn('class="sticker-qty"', html)
                else:
                    self.assertIn(f'<span class="sticker-qty">{quantity}</span>', html)
                    self.assertNotIn(f'<span class="sticker-qty">×{quantity}</span>', html)

        self.assertIn('--stack-step:2px', self.style)
        self.assertNotIn('--stack-drift', self.style)
        self.assertNotIn('--stack-rise', self.style)
        self.assertIn('calc(var(--stack-index) * var(--stack-step) * -1)', self.style)
        front = self.style.split('.s30-album-page .sticker-slot-frame .slot{', 1)[1].split('}', 1)[0]
        self.assertEqual(2, front.count('calc(var(--stack-index) * var(--stack-step) * -1)'))
        compact = (APP_DIR / "static" / "compact_sticker_stack.css").read_text()
        self.assertNotIn('.sticker-wall-stack-layer', compact)
        self.assertNotIn('compact_sticker_stack.css', self.style)
        self.assertIn("z-index:calc(var(--stack-index) + 1)", self.style)
        self.assertIn("z-index:calc(var(--stack-index) + 1)", front)
        self.assertNotIn(".sticker-slot-frame.stack-level-", self.style)

    def test_uniform_back_cards_have_no_quantity_specific_geometry(self):
        self.assertNotIn('[data-stack-quantity="2"]', self.style)
        layer = self.style.split('.sticker-wall-stack-layer{', 1)[1].split('}', 1)[0]
        for declaration in ('inset:0;', 'box-sizing:border-box;', 'background:#fff;',
                            'box-shadow:none;', 'border-radius:14px;',
                            'z-index:calc(var(--stack-index) + 1);'):
            self.assertIn(declaration, layer)
        self.assertEqual(2, layer.count('calc(var(--stack-index) * var(--stack-step) * -1)'))

    def test_real_top_card_has_no_shadow_gap_in_stack_state(self):
        # Copies are placed ON TOP; only identical 2px card edges separate them.
        front = self.style.split('.s30-album-page .sticker-slot-frame .slot.duplicate{', 1)[1].split('}', 1)[0]
        layer = self.style.split('.sticker-wall-stack-layer{', 1)[1].split('}', 1)[0]
        self.assertIn('box-shadow:none !important;', front)
        self.assertIn('box-shadow:none;', layer)
        color = 'color-mix(in srgb, var(--color-accent) 42%, var(--color-border))'
        self.assertIn(color, front)
        self.assertIn(color, layer)

    def test_every_physical_copy_has_the_same_face_and_only_top_has_bubble(self):
        from html.parser import HTMLParser
        class Cards(HTMLParser):
            def __init__(self):
                super().__init__()
                self.faces = 0
                self.bubbles = 0
            def handle_starttag(self, tag, attrs):
                classes = dict(attrs).get('class', '').split()
                self.faces += 'sammlr-retro-number' in classes
                self.bubbles += 'sticker-qty' in classes
        for quantity in (1, 2, 3, 4, 5, 6, 7, 20, 89):
            html = webapp.sticker_wall_slot_html('wm26', 'FWC2',
                {'FWC2': {'quantity': quantity}}, ReadOnlyInventory(),
                'owned' if quantity == 1 else 'duplicate', 'FWC2')
            cards = Cards()
            cards.feed(html)
            self.assertEqual(min(quantity, 5), cards.faces)
            self.assertEqual(int(quantity > 1), cards.bubbles)
            backs = re.findall(r'<i class="sticker-wall-stack-layer"[^>]*>(.*?)</i>', html, re.S)
            expected_face = webapp.sticker_wall_card_inner('wm26', 'FWC2', {'FWC2': {'quantity': 1}}, 0)
            self.assertEqual(max(min(quantity, 5)-1, 0), len(backs))
            for face in backs:
                self.assertEqual(expected_face, face)
                self.assertIn('FWC', face)
                self.assertIn('sammlr-retro-number-text">2<', face)
                self.assertNotIn('sticker-qty', face)
            self.assertIn(f'--stack-index:{min(quantity,5)-1}', html)


    def test_section_header_has_only_the_progress_bottom_line(self):
        rule = re.search(
            r"\.s30-album-page \.album-chapter-title,\s*"
            r"\.s30-album-page \.album-section-progress-title\{([^}]+)\}",
            self.style,
        )
        self.assertIsNotNone(rule)
        self.assertIn("border-bottom:0", rule.group(1))
        self.assertIn("--chapter-outline-width:1px", self.style)
        self.assertIn("var(--chapter-outline-radius,11px) - var(--chapter-outline-width,1px)", self.style)
        self.assertIn('class="chapter-progress-track"', self.render_pair("em24")[1])

    def test_text_identifier_fit_classes_are_generic_by_length(self):
        cases = {
            "GER SP": "short",
            "SCO P1": "short",
            "GER PTW": "medium",
            "GER TOP1": "long",
            "GER TOP2": "long",
            "WAL 2/3": "medium",
        }
        for code, length in cases.items():
            with self.subTest(code=code):
                html = webapp.sticker_wall_card_inner(
                    "em24", code, {code: {"quantity": 1}}
                )
                self.assertIn(f"sticker-identifier-{length}", html)
        self.assertIn("max-width:calc(100% - 12px)", self.style)
        self.assertIn("white-space:nowrap", self.style)


if __name__ == "__main__":
    unittest.main()
