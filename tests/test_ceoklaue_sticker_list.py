import hashlib
import re
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from fontTools.ttLib import TTFont


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "App"
CSS = APP_DIR / "static" / "sticker_list.css"
FONTS = tuple(
    APP_DIR / "static" / "fonts" / f"ceoklaue-final-alt{alternate}.woff2"
    for alternate in (1, 2, 3)
)
MANIFEST = ROOT / "Branding" / "CEOKlaue" / "05_runtime" / "manifest.json"
BUILDER = MANIFEST.parent / "build_runtime_assets.py"
WEBAPP = APP_DIR / "webapp.py"
STICKER_LIST_MODULE = APP_DIR / "sticker_list.py"
STICKER_LIST_TEMPLATE = APP_DIR / "templates" / "sticker_list.html"
STICKER_LIST_JS = APP_DIR / "static" / "sticker_list.js"
FEATURE_SOURCE = "\n".join(
    path.read_text(encoding="utf-8")
    for path in (STICKER_LIST_MODULE, STICKER_LIST_TEMPLATE, STICKER_LIST_JS)
)
WORDMARK = APP_DIR / "static" / "ceoklaue-wordmark.svg"
os.environ.setdefault("SAMMLR_ENV", "testing")
os.environ.setdefault("SAMMLR_SECRET_KEY", "sammlr-explicit-testing-secret")
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CEOKlaueStickerListTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        webapp.ceoklaue_runtime_manifest.cache_clear()
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_final_master_is_exactly_82_by_3_with_all_binding_replacements(self):
        master = self.manifest["master"]
        self.assertEqual(82, master["characters"])
        self.assertEqual(246, master["selected_glyphs"])
        records = {
            record["character"]: tuple(
                alternate["variant"] for alternate in record["alternates"]
            )
            for record in master["characters_manifest"]
        }
        self.assertEqual(
            {
                "v": ("07", "09", "08"),
                "w": ("08", "10", "09"),
                "x": ("12", "11", "13"),
                "V": ("07", "09", "10"),
                "X": ("06", "09", "10"),
                ":": ("07", "09", "10"),
            },
            {character: records[character] for character in "vwxVX:"},
        )
        self.assertEqual(("06", "08", "10"), records["u"])
        self.assertEqual(("07", "08", "09"), records["A"])
        self.assertEqual(("05", "02", "01"), records["F"])
        self.assertEqual(("01", "04", "05"), records["H"])
        self.assertEqual(("11", "09", "10"), records["2"])
        self.assertEqual(("06", "08", "09"), records[","])

    def test_three_local_bundled_fonts_cover_the_full_final_charset(self):
        self.assertFalse((APP_DIR / "static" / "fonts" / "ceoklaue-v0.1.woff2").exists())
        expected_charset = {
            record["character"] for record in self.manifest["master"]["characters_manifest"]
        }
        hashes = set()
        for path in FONTS:
            self.assertEqual(b"wOF2", path.read_bytes()[:4])
            cmap = TTFont(path).getBestCmap()
            self.assertEqual(expected_charset, {chr(codepoint) for codepoint in cmap if codepoint != 32})
            hashes.add(digest(path))
        self.assertEqual(3, len(hashes))
        self.assertEqual([], self.manifest["runtime"]["external_assets"])

    def test_runtime_builder_is_reproducible(self):
        marker_paths = tuple(
            ROOT / variant["runtime_asset"]
            for family in self.manifest["selection_markers"]["families"]
            for variant in family["variants"]
        )
        generated_paths = FONTS + marker_paths + (WORDMARK, MANIFEST)
        before = {path: digest(path) for path in generated_paths}
        subprocess.run([sys.executable, str(BUILDER)], cwd=ROOT, check=True, capture_output=True)
        self.assertEqual(before, {path: digest(path) for path in generated_paths})

    def test_deterministic_context_mixing_uses_all_three_without_periodicity(self):
        text = "MAR1 MAR2 MAR3 MAR4 MAR5 MAR6 MAR7 MAR8 MAR9 MAR10"
        first = [
            webapp.ceoklaue_runtime_mix_index(text, character, position, "codes") + 1
            for position, character in enumerate(text)
            if character != " "
        ]
        second = [
            webapp.ceoklaue_runtime_mix_index(text, character, position, "codes") + 1
            for position, character in enumerate(text)
            if character != " "
        ]
        self.assertEqual(first, second)
        self.assertEqual({1, 2, 3}, set(first))
        self.assertNotEqual([index % 3 + 1 for index in range(len(first))], first)
        other = [
            webapp.ceoklaue_runtime_mix_index(text, character, position, "other-codes") + 1
            for position, character in enumerate(text)
            if character != " "
        ]
        self.assertNotEqual(first, other)

    def test_repeated_characters_deterministically_avoid_their_previous_alternate(self):
        samples = ("FIFA", "BRA11", "MEX15 MEX15", "MISSISSIPPI")
        all_alternates = set()
        for text in samples:
            first = webapp.ceoklaue_runtime_mix_sequence(text, "anti-repeat-test")
            second = webapp.ceoklaue_runtime_mix_sequence(text, "anti-repeat-test")
            self.assertEqual(first, second)
            previous = {}
            for character, alternate in zip(text, first):
                if character in previous:
                    self.assertNotEqual(previous[character], alternate)
                previous[character] = alternate
                if character != " ":
                    all_alternates.add(alternate + 1)
        self.assertEqual({1, 2, 3}, all_alternates)
        self.assertNotEqual(
            [index % 3 + 1 for index in range(len(samples[-1]))],
            [alternate + 1 for alternate in webapp.ceoklaue_runtime_mix_sequence(samples[-1], "anti-repeat-test")],
        )
        source = FEATURE_SOURCE
        self.assertNotIn('text == "FIFA"', source)
        self.assertTrue(self.manifest["mixing"]["repeated_character_anti_repetition"])

    def test_css_is_uniform_grid_and_strictly_sticker_list_scoped(self):
        css = CSS.read_text(encoding="utf-8")
        final = css[css.index("/* CEOKlaue Final"):]
        for alternate in (1, 2, 3):
            self.assertIn(f"ceoklaue-final-alt{alternate}.woff2", final)
            self.assertIn(f".ceoklaue-alt-{alternate}", final)
        self.assertIn("--ceoklaue-grid-size:24px", final)
        self.assertIn("background-size:var(--ceoklaue-grid-size) var(--ceoklaue-grid-size)", final)
        self.assertNotIn("120px", final)
        self.assertNotIn("dashed", final)
        self.assertNotIn("dotted", final)
        self.assertNotIn("rotate(17deg)", final)
        self.assertIn("animation:none !important", final)
        self.assertNotIn('body{font-family:"CEOKlaue Final', final.replace(" ", ""))
        self.assertIn("padding-top:48px !important", final)
        self.assertIn("padding:0 !important", final)
        self.assertIn("background:transparent !important", final)
        self.assertIn("backdrop-filter:none !important", final)
        self.assertIn("transform:translate3d(0,calc(-100% + 32px),0)", final)
        self.assertIn("background:rgba(245,243,237,.50)", final)

    def test_final_header_wordmark_uses_the_connected_individual_source(self):
        wordmark = self.manifest["header_wordmark"]
        self.assertEqual("sammlr.", wordmark["text"])
        self.assertNotIn("e", wordmark["text"])
        self.assertEqual("single-connected-image", wordmark["source_mode"])
        self.assertTrue(wordmark["source"].endswith("ceoklaue_product_wordmark_final_01.jpg"))
        self.assertTrue(wordmark["connected_wordmark_preserved"])
        self.assertEqual("#211d22", wordmark["letter_color"])
        self.assertEqual("#7C3AED", wordmark["period_color"])
        self.assertEqual(wordmark["asset_sha256"], digest(WORDMARK))
        svg = WORDMARK.read_text(encoding="utf-8")
        self.assertIn('data-text="sammlr."', svg)
        self.assertIn('data-source-mode="single-connected-image"', svg)
        self.assertEqual(1, svg.count('data-wordmark-part="letters"'))
        self.assertEqual(1, svg.count('data-wordmark-part="period"'))
        self.assertIn('data-wordmark-part="letters"', svg)
        self.assertIn('fill="#211d22"', svg)
        self.assertIn('data-wordmark-part="period"', svg)
        self.assertIn('fill="#7C3AED"', svg)
        self.assertIn('src="/static/ceoklaue-wordmark.svg"', FEATURE_SOURCE)

    def test_product_fonts_have_bounded_topology_preserving_twenty_percent_weight_pass(self):
        adjustment = self.manifest["runtime"]["body_stroke_adjustment"]
        self.assertEqual(1.2, adjustment["factor"])
        self.assertFalse(adjustment["browser_synthetic_bold"])
        self.assertEqual(3, len(adjustment["audits"]))
        for alternate_audits in adjustment["audits"]:
            self.assertEqual(82, len(alternate_audits))
            for audit in alternate_audits:
                self.assertEqual(audit["topology_before"], audit["topology_after"])

    def test_final_marker_runtime_is_local_rotated_and_deterministically_mixed(self):
        self.assertEqual(["sticker-list-page"], self.manifest["scope"])
        markers = self.manifest["selection_markers"]
        self.assertEqual(10, markers["selected_markers"])
        self.assertEqual(-90, markers["rotation_degrees"])
        self.assertEqual("counterclockwise", markers["rotation_direction"])
        self.assertEqual(
            {
                "receive_circle": ["01", "02", "04", "03", "05"],
                "give_cross": ["05", "03", "04", "01", "02"],
            },
            {record["family"]: record["selected_variants"] for record in markers["families"]},
        )
        self.assertEqual([], self.manifest["runtime"]["external_assets"])
        for record in markers["families"]:
            expected_color = "#7C3AED" if record["family"] == "receive_circle" else "#211d22"
            expected_factor = 1.7
            self.assertEqual(expected_color, record["runtime_color"])
            self.assertEqual(expected_factor, record["stroke_factor"])
            for variant in record["variants"]:
                path = ROOT / variant["runtime_asset"]
                source = ROOT / "Branding" / "CEOKlaue" / variant["source"]
                self.assertEqual(-90, variant["rotation_degrees"])
                self.assertEqual(variant["runtime_asset_sha256"], digest(path))
                self.assertEqual(variant["source_sha256"], digest(source))
                self.assertIn('data-rotation-degrees="-90"', path.read_text(encoding="utf-8"))
                self.assertIn(f'fill="{expected_color}"', path.read_text(encoding="utf-8"))

        sequence = [
            webapp.ceoklaue_marker_mix_index(
                "receive_circle", f"MAR{position}", 1, "album-wm26"
            )
            for position in range(1, 61)
        ]
        self.assertEqual(set(range(5)), set(sequence))
        self.assertNotEqual([index % 5 for index in range(len(sequence))], sequence)
        self.assertEqual(
            sequence,
            [
                webapp.ceoklaue_marker_mix_index(
                    "receive_circle", f"MAR{position}", 1, "album-wm26"
                )
                for position in range(1, 61)
            ],
        )

    def test_sticker_list_uses_real_marker_images_without_artificial_selected_marks(self):
        source = FEATURE_SOURCE
        self.assertIn("function stickerListCeoklaueIndex", source)
        self.assertIn("ceoklaue_marker_asset(", source)
        self.assertIn('class="sticker-selection-marker"', source)
        self.assertNotIn('@app.route("/ceoklaue', source.lower())
        css = CSS.read_text(encoding="utf-8")
        final = css[css.index("/* CEOKlaue Final"):]
        self.assertIn(".sticker-list-item.selected .sticker-selection-marker", final)
        self.assertIn("content:none !important", final)
        self.assertNotIn("border-radius:48%", final)
        self.assertNotIn("rotate(17deg)", final)
        self.assertIn('data-marker-rendering="static"', source)
        self.assertNotIn("marker-draw-circle", source)
        self.assertIn("marker-draw-one", source)
        self.assertIn("marker-draw-two", source)
        self.assertIn("top-left-to-bottom-right-then-top-right-to-bottom-left", source)
        self.assertNotIn("marker-draw-circle", final)
        self.assertNotIn("animation:ceoklaue-marker-draw .34s", final)
        self.assertIn("animation:ceoklaue-marker-draw .17s linear forwards", final)
        self.assertIn("animation:ceoklaue-marker-draw .17s linear .17s forwards", final)

    def test_final_header_and_postit_assets_are_real_and_locally_scoped(self):
        source = FEATURE_SOURCE
        self.assertIn('/static/ceoklaue-ui/back-arrow.svg', source)
        self.assertNotIn("ink('← Zurück zum Album'", source)
        for variant in ("01", "02", "04"):
            self.assertTrue((APP_DIR / "static" / "ceoklaue-ui" / f"middle-dot-{variant}.svg").is_file())
        self.assertIn("trade-postit-control", source)
        self.assertIn("trade-postit-get", source)
        self.assertIn("trade-postit-give", source)
        self.assertIn("tradebar.hidden = !canReview", source)
        self.assertIn("CEOKLAUE_STICKER_LIST_STORAGE_KEY", source)

    def test_semantic_commas_have_no_trailing_separator_or_visual_line_hacks(self):
        source = FEATURE_SOURCE
        self.assertIn("def list_item(code, mode, instance=1, separator=False):", source)
        self.assertIn("if separator", source)
        self.assertIn('else ""', source)
        self.assertIn('class="sticker-list-entry"', source)
        self.assertIn('data-semantic-separator="{\'after\' if separator else \'none\'}"', source)
        self.assertIn("item_index < len(items) - 1", source)
        self.assertIn("position < len(sorted_missing_codes) - 1", source)
        self.assertIn("position < len(duplicate_items) - 1", source)
        self.assertNotIn("visual_line", source)
        self.assertNotIn("line_end", source)

    def test_sticker_list_actions_use_real_deterministic_bracket_pairs(self):
        source = FEATURE_SOURCE
        for label in ("Auswahl prüfen", "Bearbeiten", "Bestätigen"):
            self.assertIn(label, source)
        self.assertIn("class=\"analog-bracket-button\"", source)
        self.assertIn("deps.bracket_button_content(", source)
        css = CSS.read_text(encoding="utf-8")
        final = css[css.index("/* CEOKlaue Final"):]
        self.assertIn(".analog-bracket-content", final)
        self.assertIn("height:1.55em !important", final)
        self.assertNotIn("border-image:url('/static/ceoklaue-ui/box.svg')", final)

    def test_review_uses_fixed_sixteen_then_twenty_spot_notes_without_overflow_link(self):
        source = FEATURE_SOURCE
        self.assertIn("STICKER_LIST_REVIEW_FIRST_COLUMN_CAPACITY = 8", source)
        self.assertIn("STICKER_LIST_REVIEW_FIRST_NOTE_CAPACITY = 16", source)
        self.assertIn("STICKER_LIST_REVIEW_CONTINUATION_COLUMN_CAPACITY = 10", source)
        self.assertIn("STICKER_LIST_REVIEW_CONTINUATION_NOTE_CAPACITY = 20", source)
        self.assertIn("Math.max(0, items.length - STICKER_LIST_REVIEW_FIRST_NOTE_CAPACITY)", source)
        self.assertIn("const noteCount = 1 + continuationCount", source)
        self.assertIn("const chunk = items.slice(start, start + capacity)", source)
        self.assertIn("chunk.length > columnCapacity", source)
        self.assertIn("data-review-continuation", source)
        self.assertIn("label.className = 'sticker-list-review-code'", source)
        self.assertIn("stickerListWriteCeoklaue(", source)
        self.assertNotIn("more.addEventListener('click', stickerListOpenDetail)", source)
        self.assertNotIn("items.length - visibleLimit", source)
        css = CSS.read_text(encoding="utf-8")
        final = css[css.index("/* CEOKlaue Final"):]
        self.assertIn(".trade-postit .pending-review-row", final)
        self.assertIn("background:transparent !important", final)
        self.assertIn("--review-paper-color:rgba(245,221,98,.99)", final)
        self.assertIn("--review-paper-color:rgba(204,232,189,.99)", final)
        self.assertIn("--review-paper-color:rgba(239,189,202,.99)", final)
        self.assertIn("@media(min-width:560px)", final)
        self.assertIn("grid-template-columns:repeat(2,224px)", final)
        self.assertIn("grid-template-columns:repeat(2,minmax(0,1fr))", final)
        self.assertIn("grid-template-rows:repeat(8,20px)", final)
        self.assertIn("grid-template-rows:repeat(10,20px)", final)
        self.assertIn("grid-auto-flow:column", final)
        self.assertIn("max-height:160px;overflow:hidden", final)
        self.assertIn("max-height:200px", final)
        self.assertNotIn("repeat(3,minmax(0,1fr))", final)
        self.assertIn(".sticker-list-review-note-column{", final)
        self.assertIn("gap:24px", final)
        self.assertIn("margin-top:30px", final)
        self.assertNotIn("give_cross", final)

    def test_review_capacity_boundaries_and_distribution_are_fixed(self):
        source = FEATURE_SOURCE
        first_capacity = int(re.search(r"FIRST_NOTE_CAPACITY = (\d+)", source).group(1))
        continuation_capacity = int(re.search(r"CONTINUATION_NOTE_CAPACITY = (\d+)", source).group(1))
        self.assertEqual((16, 20), (first_capacity, continuation_capacity))

        def split(count):
            chunks = [min(count, first_capacity)]
            remaining = count - chunks[0]
            while remaining:
                chunks.append(min(remaining, continuation_capacity))
                remaining -= chunks[-1]
            return chunks

        self.assertEqual({16: [16], 17: [16, 1], 36: [16, 20],
                          37: [16, 20, 1], 56: [16, 20, 20]},
                         {count: split(count) for count in (16, 17, 36, 37, 56)})
        self.assertIn("const start = isContinuation", source)
        self.assertIn("target.classList.toggle('is-two-column', chunk.length > columnCapacity)", source)
        self.assertNotIn("weitere …", source)

    def test_po_acceptance_visual_polish_contract(self):
        source = FEATURE_SOURCE
        css = CSS.read_text(encoding="utf-8")
        final = css[css.index("/* CEOKlaue Final"):]
        self.assertIn("width:200px", final)
        self.assertIn("font-size:30px", final)
        self.assertIn("width:224px !important;\n    height:224px !important", final)
        self.assertIn("width:224px;\n    height:224px", final)
        self.assertIn("min-width:224px", final)
        self.assertIn("min-height:224px", final)
        self.assertIn("max-width:224px", final)
        self.assertIn("max-height:224px", final)
        self.assertIn("transform:translateX(-50%) rotate(-1.05deg)", final)
        self.assertIn("color:#211d22 !important", final)
        self.assertIn("font:400 20px/24px", final)
        self.assertIn("grid-template-columns:repeat(2,224px)", final)
        self.assertIn("function stickerListSizePostitUnderlines", source)
        self.assertIn("getBoundingClientRect().width + 6", source)
        self.assertIn("deps.bracket_button_content(", source)
        self.assertNotIn('src="/static/ceoklaue-ui/box.svg"', source)
        self.assertNotIn("border-image:url('/static/ceoklaue-ui/box.svg')", final)
        self.assertNotIn(".sticker-list-trade-head strong::after", final)

    def test_receive_micro_adjustment_give_stays_fixed_and_review_uses_local_milk_glass(self):
        css = CSS.read_text(encoding="utf-8")
        final = css[css.index("/* CEOKlaue Final"):]
        self.assertIn("width:clamp(51px, calc(100% + 25px), 111px)", final)
        self.assertIn("opacity:.45", final)
        self.assertIn("width:clamp(46px, calc(100% + 16px), 98px)", final)
        self.assertIn("opacity:.72", final)
        self.assertIn("background:rgba(245,243,237,.60) !important", final)
        self.assertIn("-webkit-backdrop-filter:blur(8px) saturate(.92)", final)
        self.assertIn("backdrop-filter:blur(8px) saturate(.92)", final)
        self.assertNotIn("background:rgba(28,22,32", final)
        source = FEATURE_SOURCE
        self.assertNotIn("if(event.target === event.currentTarget)", source)
        self.assertIn("stickerListCloseReview();", source)

    def test_final_glassboard_interaction_and_material_contract(self):
        source = FEATURE_SOURCE
        css = CSS.read_text(encoding="utf-8")
        final = css[css.index("/* CEOKlaue Final"):]

        self.assertIn('data-glassboard-state="list"', source)
        self.assertIn('class="sticker-list-glass-engraving"', source)
        self.assertIn("STICKER_LIST_GLASSBOARD_MOTION_MS = 400", source)
        self.assertIn("function stickerListLockPageScroll", source)
        self.assertIn("document.body.style.position = 'fixed'", source)
        self.assertIn("document.body.style.top = '-' + stickerListLockedScrollY + 'px'", source)
        self.assertIn("window.scrollTo(0, restoreY)", source)
        self.assertIn("deltaY < -56", source)
        self.assertIn("stickerListIsFreeGlassTarget", source)
        self.assertNotIn("stickerListGlassboard.addEventListener('click'", source)
        self.assertIn("stickerListSelections", source)

        clear_markup = source[source.index('class="sticker-list-clear"'):source.index('</button>', source.index('class="sticker-list-clear"'))]
        self.assertIn("{{ clear_label|safe }}", clear_markup)
        self.assertIn('clear_label=ink("Leeren", "clear")', source)
        self.assertNotIn("bracket(", clear_markup)
        self.assertNotIn("analog-bracket-button", clear_markup)
        self.assertNotIn("data-bracket", clear_markup)
        self.assertIn(
            "document.getElementById('stickerListClear').addEventListener('click'",
            source,
        )
        self.assertEqual(1, source.count('class="sticker-list-tradebar is-idle"'))

        rendered_clear = webapp.ceoklaue_runtime_run(
            "Leeren", "sticker-list-wm26-clear"
        )
        self.assertEqual(0, rendered_clear.count("analog-bracket-left"))
        self.assertEqual(0, rendered_clear.count("analog-bracket-right"))
        self.assertNotIn("button_bracket_", rendered_clear)
        self.assertNotIn("data-bracket", rendered_clear)

        rendered_review = webapp.ceoklaue_bracket_button_content(
            "Auswahl prüfen",
            "sticker-list-wm26-review-button",
            "open-review",
        )
        self.assertEqual(1, rendered_review.count("analog-bracket-left"))
        self.assertEqual(1, rendered_review.count("analog-bracket-right"))

        self.assertIn("height:100dvh", final)
        self.assertIn("calc(-100% + 32px)", final)
        self.assertIn("400ms cubic-bezier(.22,.76,.28,1)", final)
        self.assertIn("top:calc(100% - 24px) !important", final)
        self.assertIn("bottom:auto !important", final)
        self.assertNotIn("bottom:calc(var(--sammlr-bottom-nav-space)", final)
        self.assertIn("left:69% !important", final)
        self.assertIn("translateX(-50%) rotate(-1.05deg)", final)
        self.assertIn("rgba(245,221,98,.99)", final)
        self.assertIn("rgba(245,221,98,.95)", final)
        self.assertIn("rgba(204,232,189,.99)", final)
        self.assertIn("rgba(239,189,202,.99)", final)
        self.assertIn("top:16px", final)
        self.assertIn("left:16px", final)
        webapp_source = WEBAPP.read_text(encoding="utf-8")
        self.assertIn("def app_header_brand_wordmark():", webapp_source)
        self.assertIn("brand_html = app_header_brand_wordmark()", webapp_source)
        self.assertIn('{{ wordmark|safe }}</div>', source)
        self.assertNotIn('font:600 13px/1 "Helvetica Neue",Arial,sans-serif', final)
        self.assertIn(".sticker-list-glass-engraving .app-header-brand-word", final)
        self.assertIn(".trade-postit-control{display:flex;flex-direction:column", final)
        self.assertIn("translate(-5px,0) rotate(-1.35deg)", final)
        self.assertIn("translate(6px,3px) rotate(1.25deg)", final)
        self.assertIn("translate(0,6px) rotate(-.7deg)", final)
        self.assertIn("gap:24px", final)
        self.assertIn(".trade-postit-actions{display:grid;gap:4px;margin-top:auto}", final)
        self.assertIn(".trade-postit-content .postit-underline{height:8px;margin:0 0 4px}", final)
        self.assertIn("font-size:20px !important;\n    line-height:24px !important", final)
        self.assertIn("align-self:center;\n    margin-top:auto", final)
        engraving_index = source.index('class="sticker-list-glass-engraving"')
        scroller_index = source.index('class="sticker-list-review-postits"')
        groups_index = source.index('class="sticker-list-review-note-groups"')
        self.assertLess(scroller_index, engraving_index)
        self.assertLess(engraving_index, groups_index)
        engraving_rule = final[final.index(".sticker-list-page .sticker-list-glass-engraving{"):]
        engraving_rule = engraving_rule[:engraving_rule.index("}")]
        self.assertIn("position:absolute", engraving_rule)
        self.assertNotIn("position:sticky", engraving_rule)
        self.assertNotIn("position:fixed", engraving_rule)
        self.assertIn("body.sticker-list-glassboard-locked", final)
        self.assertIn("overscroll-behavior:none !important", final)
        self.assertIn("--sticker-list-review-safe-bottom:calc(var(--sammlr-bottom-nav-space, 92px) + 10px)", final)
        self.assertIn("height:calc(100% - var(--sticker-list-review-safe-bottom))", final)
        self.assertIn("inset:54px 14px var(--sticker-list-review-safe-bottom)", final)
        self.assertIn("overflow-y:auto", final)
        self.assertIn("overscroll-behavior:contain", final)
        self.assertIn("z-index:9000", final)
        self.assertIn("background:rgba(245,243,237,.50)", final)
        self.assertIn("backdrop-filter:blur(11px) saturate(.92)", final)

        template = STICKER_LIST_TEMPLATE.read_text(encoding="utf-8")
        self.assertLess(
            template.index('</form>'),
            template.index('class="sticker-list-review-layer"'),
        )
        self.assertIn(".sticker-list-entry", final)
        self.assertIn("white-space:nowrap", final)
        self.assertNotIn("dashed", final)
        self.assertNotIn("dotted", final)


if __name__ == "__main__":
    unittest.main()
