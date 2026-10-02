import atexit
import hashlib
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "App"
REFERENCE_FIXTURE = APP_DIR / "Database" / "sammlr_reference_s00.db"
PRODUCTION_DB = APP_DIR / "Database" / "sammlr.db"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# webapp initializes its configured database at import time. Point that import
# at a disposable S00 copy before loading any application module.
_bootstrap_dir = tempfile.TemporaryDirectory(prefix="sammlr-s01-bootstrap-")
atexit.register(_bootstrap_dir.cleanup)
_bootstrap_db = Path(_bootstrap_dir.name) / "bootstrap.db"
shutil.copy2(REFERENCE_FIXTURE, _bootstrap_db)
os.environ["DATABASE_PATH"] = str(_bootstrap_db)
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP_DIR))

import webapp  # noqa: E402


if os.environ.get("SAMMLR_S01_MUTATE_QUANTITY") == "1":
    _reference_change_sticker_quantity = webapp.change_sticker_quantity

    def _mutated_change_sticker_quantity(
        connection, user_id, album_id, code, delta
    ):
        # S01 mutation proof only: an in-memory replacement for this process.
        # It deliberately applies one extra item and never edits webapp.py.
        return _reference_change_sticker_quantity(
            connection, user_id, album_id, code, delta + 1
        )

    webapp.change_sticker_quantity = _mutated_change_sticker_quantity


class InventoryRegressionTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.production_hash_before = sha256(PRODUCTION_DB)
        webapp.app.config.update(TESTING=True)

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory(prefix="sammlr-s01-test-")
        self.test_db = Path(self.test_dir.name) / "inventory.db"
        shutil.copy2(REFERENCE_FIXTURE, self.test_db)
        webapp.DB = str(self.test_db)
        self.client = webapp.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 1

    def tearDown(self):
        self.assertEqual(
            self.production_hash_before,
            sha256(PRODUCTION_DB),
            "The standard Sammlr database changed during an isolated S01 test.",
        )
        self.test_dir.cleanup()

    def db_row(self, code, user_id=1, album_id="vfl"):
        with sqlite3.connect(self.test_db) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(
                """
                SELECT *
                FROM stickers
                WHERE user_id=? AND album_id=? AND sticker_code=?
                """,
                (user_id, album_id, code),
            ).fetchone()

    def assert_sticker(self, code, quantity, duplicates):
        row = self.db_row(code)
        self.assertIsNotNone(row)
        self.assertEqual(quantity, row["quantity"])
        self.assertEqual(duplicates, row["duplicates"])
        self.assertEqual(max(quantity - 1, 0), row["duplicates"])

    def wall_classes(self, response_text, code):
        match = re.search(
            rf'<a class="([^"]*)"[^>]* data-code="{re.escape(code)}"',
            response_text,
        )
        self.assertIsNotNone(match, f"Sticker {code} fehlt in der Stickerwall.")
        return set(match.group(1).split())

    def test_add_existing_sticker_updates_quantity_and_duplicates(self):
        response = self.client.post("/add/vfl/1")

        self.assertEqual(302, response.status_code)
        self.assert_sticker("1", quantity=4, duplicates=3)

    def test_add_missing_sticker_creates_first_copy(self):
        self.assertIsNone(self.db_row("3"))

        response = self.client.post("/add/vfl/3")

        self.assertEqual(302, response.status_code)
        self.assert_sticker("3", quantity=1, duplicates=0)

    def test_remove_existing_sticker_updates_quantity_and_duplicates(self):
        response = self.client.post("/remove/vfl/1")

        self.assertEqual(302, response.status_code)
        self.assert_sticker("1", quantity=2, duplicates=1)

    def test_remove_last_copy_reaches_zero_by_deleting_row(self):
        self.assert_sticker("2", quantity=1, duplicates=0)

        response = self.client.post("/remove/vfl/2")

        self.assertEqual(302, response.status_code)
        self.assertIsNone(self.db_row("2"))

    def test_remove_missing_sticker_does_not_create_negative_stock(self):
        self.assertIsNone(self.db_row("3"))

        response = self.client.post("/remove/vfl/3")

        self.assertEqual(302, response.status_code)
        self.assertIsNone(self.db_row("3"))

    def test_inline_plus_updates_db_and_response_contract(self):
        response = self.client.post(
            "/album/vfl/sticker/1/quantity",
            data={"delta": "1"},
        )

        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(4, payload["quantity"])
        self.assertEqual(3, payload["duplicates"])
        self.assertEqual("duplicate", payload["statusClass"])
        self.assertIn("sammlr-retro-number variant-v3 wall-number", payload["cardHtml"])
        self.assertIn("sammlr-retro-digits-v3.svg#sammlr-digit-v3-1", payload["cardHtml"])
        self.assert_sticker("1", quantity=4, duplicates=3)

    def test_inline_plus_creates_missing_sticker(self):
        self.assertIsNone(self.db_row("3"))

        response = self.client.post(
            "/album/vfl/sticker/3/quantity",
            data={"delta": "1"},
        )

        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertEqual(1, payload["quantity"])
        self.assertEqual(0, payload["duplicates"])
        self.assertEqual("owned", payload["statusClass"])
        self.assert_sticker("3", quantity=1, duplicates=0)

    def test_inline_minus_updates_db_and_response_contract(self):
        response = self.client.post(
            "/album/vfl/sticker/1/quantity",
            data={"delta": "-1"},
        )

        self.assertEqual(200, response.status_code)
        payload = response.get_json()
        self.assertEqual(2, payload["quantity"])
        self.assertEqual(1, payload["duplicates"])
        self.assert_sticker("1", quantity=2, duplicates=1)

    def test_inline_minus_never_goes_below_zero(self):
        first_response = self.client.post(
            "/album/vfl/sticker/2/quantity",
            data={"delta": "-1"},
        )
        second_response = self.client.post(
            "/album/vfl/sticker/2/quantity",
            data={"delta": "-99"},
        )

        self.assertEqual(200, first_response.status_code)
        self.assertEqual(0, first_response.get_json()["quantity"])
        self.assertEqual(200, second_response.status_code)
        self.assertEqual(0, second_response.get_json()["quantity"])
        self.assertEqual(0, second_response.get_json()["duplicates"])
        self.assertIsNone(self.db_row("2"))

    def test_inline_quantity_round_trip_zero_one_two_one_zero(self):
        self.assertIsNone(self.db_row("3"))

        observed = []
        for delta in (1, 1, -1, -1):
            response = self.client.post(
                "/album/vfl/sticker/3/quantity",
                data={"delta": str(delta)},
            )
            self.assertEqual(200, response.status_code)
            payload = response.get_json()
            observed.append(
                (payload["quantity"], payload["duplicates"], payload["statusClass"])
            )

        self.assertEqual(
            [
                (1, 0, "owned"),
                (2, 1, "duplicate"),
                (1, 0, "owned"),
                (0, 0, "missing"),
            ],
            observed,
        )
        self.assertIsNone(self.db_row("3"))

    def test_wall_stack_layers_follow_exact_quantity(self):
        for quantity in (1, 2, 3, 4, 5, 6, 14):
            with sqlite3.connect(self.test_db) as connection:
                connection.execute(
                    "UPDATE stickers SET quantity=?, duplicates=? "
                    "WHERE user_id=1 AND album_id='vfl' AND sticker_code='1'",
                    (quantity, max(quantity - 1, 0)),
                )
            html = self.client.get("/album/vfl").get_data(as_text=True)
            frame = re.search(
                r'<div class="sticker-slot-frame" data-sticker-frame '
                r'data-stack-quantity="%d"[^>]*>(.*?)<a class="[^"]*"[^>]* data-code="1"' % quantity,
                html,
                re.S,
            )
            self.assertIsNotNone(frame, quantity)
            self.assertEqual(
                min(quantity, 5) - 1,
                frame.group(1).count("data-stack-layer="),
            )

    def test_initial_inventory_never_becomes_a_decrement_floor(self):
        for initial in (0, 4, 5, 7, 20):
            with self.subTest(initial=initial):
                with sqlite3.connect(self.test_db) as connection:
                    connection.execute("DELETE FROM stickers WHERE user_id=1 AND album_id='vfl' AND sticker_code='1'")
                    if initial:
                        connection.execute("INSERT INTO stickers (album_id,sticker_code,status,duplicates,quantity,user_id) VALUES ('vfl','1','owned',?,?,1)", (initial-1,initial))
                sequence = [1,2,3,4,3,2,1,0] if initial==0 else list(range(initial-1,-1,-1))
                current = initial
                for expected in sequence:
                    response = self.client.post('/album/vfl/sticker/1/quantity', data={'delta':str(expected-current)})
                    self.assertEqual(200, response.status_code)
                    payload = response.get_json()
                    self.assertEqual(expected, payload['quantity'])
                    self.assertEqual(max(expected-1,0), payload['duplicates'])
                    self.assertEqual('missing' if expected==0 else 'owned' if expected==1 else 'duplicate', payload['statusClass'])
                    self.assertEqual(int(expected>1), payload['cardHtml'].count('class="sticker-qty"'))
                    if expected>1:
                        self.assertIn(f'class="sticker-qty">{expected}</span>', payload['cardHtml'])
                    row = self.db_row('1')
                    self.assertEqual(expected, row['quantity'] if row else 0)
                    current = expected

    def test_inline_rejects_zero_and_non_numeric_delta_without_db_change(self):
        zero_response = self.client.post(
            "/album/vfl/sticker/1/quantity",
            data={"delta": "0"},
        )
        text_response = self.client.post(
            "/album/vfl/sticker/1/quantity",
            data={"delta": "not-a-number"},
        )

        self.assertEqual(400, zero_response.status_code)
        self.assertEqual(400, text_response.status_code)
        self.assert_sticker("1", quantity=3, duplicates=2)

    def test_stickerwall_filter_predicate_covers_all_states(self):
        _, by_code, _, _, _, _ = webapp.lade_album_for_user("vfl", 1)

        self.assertTrue(webapp.filter_ok("missing", "3", by_code))
        self.assertFalse(webapp.filter_ok("missing", "2", by_code))
        self.assertTrue(webapp.filter_ok("owned", "2", by_code))
        self.assertFalse(webapp.filter_ok("owned", "3", by_code))
        self.assertTrue(webapp.filter_ok("duplicate", "1", by_code))
        self.assertFalse(webapp.filter_ok("duplicate", "2", by_code))
        self.assertTrue(webapp.filter_ok("all", "1", by_code))
        self.assertTrue(webapp.filter_ok("all", "3", by_code))

    def test_stickerwall_routes_hide_nonmatching_cards(self):
        missing_html = self.client.get(
            "/album/vfl?filter=missing"
        ).get_data(as_text=True)
        owned_html = self.client.get(
            "/album/vfl?filter=owned"
        ).get_data(as_text=True)
        duplicate_html = self.client.get(
            "/album/vfl?filter=duplicate"
        ).get_data(as_text=True)

        self.assertNotIn("filter-hidden", self.wall_classes(missing_html, "3"))
        self.assertIn("filter-hidden", self.wall_classes(missing_html, "1"))
        self.assertNotIn("filter-hidden", self.wall_classes(owned_html, "2"))
        self.assertIn("filter-hidden", self.wall_classes(owned_html, "3"))
        self.assertNotIn("filter-hidden", self.wall_classes(duplicate_html, "1"))
        self.assertIn("filter-hidden", self.wall_classes(duplicate_html, "2"))

    def test_stickerwall_renders_inline_quantity_controls_and_separate_detail_link(self):
        html = self.client.get("/album/vfl").get_data(as_text=True)

        self.assertIn('data-sticker-frame data-stack-quantity="3"', html)
        self.assertIn('data-sticker-frame data-stack-quantity="0"', html)
        self.assertIn('data-quantity-delta="-1"', html)
        self.assertIn('data-quantity-delta="1"', html)
        self.assertIn('data-inline-quantity aria-live="polite">3</strong>', html)
        self.assertIn(
            'href="/sticker/vfl/1" class="sticker-inline-detail"', html
        )
        self.assertNotIn('id="stickerDetailModal"', html)
        self.assertNotIn(">Auswählen<", html)
        self.assertNotIn('id="smartAddBar"', html)
        self.assertNotIn('id="pendingReviewModal"', html)

    def test_stickerwall_keeps_client_side_filter_and_position_helpers(self):
        html = self.client.get("/album/vfl").get_data(as_text=True)

        self.assertIn("function currentWallAnchor()", html)
        self.assertIn("function restoreWallAnchor(anchor)", html)
        self.assertIn("window.history.replaceState", html)
        self.assertIn("openInlineStickerControl(slot)", html)
        self.assertIn("changeInlineStickerQuantity(quantitySlot", html)
        self.assertIn("function persistStickerWallPosition()", html)
        self.assertIn("function restoreStickerWallPosition()", html)
        self.assertIn("window.addEventListener('pagehide'", html)
        self.assertIn("stickerWallPositionKey", html)

    def test_stickerwall_chapters_start_open_and_restore_session_context(self):
        for album_id in ("em24", "vfl", "wm26"):
            html = self.client.get(f"/album/{album_id}").get_data(as_text=True)
            chapter_headings = re.findall(
                r'<h2[^>]*class="[^"]*album-chapter-title[^"]*"[^>]*>', html
            )
            self.assertTrue(chapter_headings, album_id)
            for heading in chapter_headings:
                self.assertNotIn("chapter-collapsed", heading)
                self.assertIn('aria-expanded="true"', heading)

        html = self.client.get("/album/wm26").get_data(as_text=True)
        self.assertIn("function restoreExpandedStickerWallChapters()", html)
        self.assertIn("function persistExpandedStickerWallChapters()", html)
        self.assertIn("function toggleStickerWallChapter(chapterTitle)", html)
        self.assertIn("window.sessionStorage", html)
        self.assertIn("titleTop", html)

    def test_stickerwall_search_quick_control_and_detail_return_contract(self):
        html = self.client.get("/album/wm26?filter=missing").get_data(as_text=True)
        detail_html = self.client.get(
            "/sticker/wm26/FWC%201?filter=missing"
        ).get_data(as_text=True)

        self.assertIn('id="stickerSearch"', html)
        self.assertIn("function matchesStickerSearch(slot, rawTerm)", html)
        self.assertIn("function updateStickerSearchFeedback(term)", html)
        self.assertIn("closeInlineStickerControl(slot)", html)
        self.assertIn("if(!event.target.closest('[data-inline-control]')) closeInlineStickerControl()", html)
        self.assertIn("persistStickerWallPosition();", html)
        self.assertIn('href="/album/wm26?filter=missing"', detail_html)

    def test_stickerwall_exposes_only_three_primary_filters(self):
        html = self.client.get("/album/vfl").get_data(as_text=True)

        self.assertEqual(3, html.count('class="sticker-filter-pill'))
        self.assertIn('data-filter="all">Alle</a>', html)
        self.assertIn('data-filter="missing">Fehlende</a>', html)
        self.assertIn('data-filter="duplicate">Doppelte</a>', html)
        self.assertNotIn('data-filter="owned"', html)
        self.assertIn("if(activeStickerFilter === 'owned')", html)

    def test_album_hero_uses_real_inventory_and_keeps_album_routes(self):
        album, _, collected, duplicates, percent, total = (
            webapp.lade_album_for_user("vfl", 1)
        )
        html = self.client.get("/album/vfl").get_data(as_text=True)
        css = (APP_DIR / "static" / "style.css").read_text(encoding="utf-8")

        self.assertIn('class="album-hero"', html)
        self.assertIn(f'id="albumHeroTitle">{album["name"]}</h1>', html)
        self.assertIn(f'id="albumHeroOwnedCount">{collected}</span>', html)
        self.assertIn(f'<small>/ {total} Sticker</small>', html)
        self.assertIn(f'id="albumProgressPercent">{percent}%</span>', html)
        self.assertIn(f'id="albumHeroMissingStat">{total - collected}</strong>', html)
        self.assertIn(f'id="albumHeroDuplicateStat">{duplicates}</strong>', html)
        self.assertIn('aria-valuenow="' + str(percent) + '"', html)
        self.assertNotIn('class="album-title-progress"', html)
        self.assertNotIn('class="card album-privacy-controls"', html)

        self.assertIn('href="/sammlung">← Zur Sammlung</a>', html)
        self.assertIn('href="/album/vfl/liste"', html)
        self.assertIn('href="/album/vfl/trades?', html)
        self.assertIn('href="/album/vfl/trophaeen"', html)
        self.assertIn('class="card sticker-wall-card"', html)
        self.assertIn(
            "albumHeroOwnedCount.textContent = payload.album.collected", html
        )
        self.assertIn(
            "albumHeroMissingStat.textContent = payload.album.missing", html
        )
        self.assertIn("@media (max-width:430px)", css)
        self.assertIn("@media (max-width:350px)", css)
        self.assertIn("width:min(430px, calc(100vw - 24px))", css)

    def test_stickerwall_po_layout_contract_keeps_controls_below_and_stack_above(self):
        css = (APP_DIR / "static" / "style.css").read_text(encoding="utf-8")
        html = self.client.get("/album/vfl").get_data(as_text=True)
        wm26_html = self.client.get("/album/wm26").get_data(as_text=True)

        self.assertIn("function syncStickerwallStickyOffsets()", html)
        self.assertIn("ResizeObserver(syncStickerwallStickyOffsets)", html)
        self.assertIn("--stickerwall-app-header-offset", css)
        self.assertIn("top:var(--stickerwall-app-header-offset) !important", css)
        self.assertIn("padding-top:18px !important", css)
        self.assertIn('--stack-step:2px', css)
        self.assertNotIn('--stack-drift', css)
        self.assertNotIn('--stack-rise', css)
        self.assertIn('calc(var(--stack-index) * var(--stack-step) * -1)', css)
        front = css.split('.s30-album-page .sticker-slot-frame .slot{', 1)[1].split('}', 1)[0]
        self.assertEqual(2, front.count('calc(var(--stack-index) * var(--stack-step) * -1)'))
        compact = (APP_DIR / "static" / "compact_sticker_stack.css").read_text()
        self.assertNotIn('.sticker-wall-stack-layer', compact)
        self.assertNotIn('compact_sticker_stack.css', css)
        self.assertNotIn(".sticker-slot-frame.stack-level-", css)
        self.assertIn("position:absolute;\n    top:calc(100% + 6px);", css)
        self.assertIn("inline-focus-active::after", css)
        self.assertIn("inline-control-above", css)
        self.assertIn("inline-control-align-left", css)
        self.assertIn("inline-control-align-right", css)
        self.assertIn("grid-template-rows:44px 19px auto", css)
        self.assertIn("backdrop-filter:blur(14px) saturate(1.08)", css)
        self.assertIn("keepActiveControlVisible", html)
        self.assertRegex(wm26_html, r"Gruppe [A-L] · [A-Z]{3}")

    def test_stickerwall_uses_one_measured_sticky_context_slot(self):
        css = (APP_DIR / "static" / "style.css").read_text(encoding="utf-8")
        html = self.client.get("/album/wm26").get_data(as_text=True)

        self.assertEqual(1, html.count('id="stickerWallStickyContext"'))
        self.assertIn("function syncStickerwallContext()", html)
        self.assertIn("function scheduleStickerwallContextSync()", html)
        self.assertIn("stickyOffsetObserver.observe(stickyControlbar)", html)
        self.assertIn("stickyOffsetObserver.observe(stickyAppHeader)", html)
        self.assertIn(
            "window.addEventListener('scroll', scheduleStickerwallContextSync, {passive:true})",
            html,
        )
        self.assertIn("source.classList.add('is-sticky-context-source')", html)
        self.assertIn("activeStickyContextSource.classList.remove('is-sticky-context-source')", html)
        self.assertIn(
            "top:calc(var(--stickerwall-app-header-offset) + var(--stickerwall-control-height) - 18px);",
            css,
        )
        self.assertIn("next.getBoundingClientRect().top - stickyTop - contextHeight", html)
        self.assertIn("context.style.transform = 'translateY('", html)
        self.assertIn(".s30-album-page .is-sticky-context-source", css)
        self.assertNotIn(".is-sticky-context-source{\n    min-height:0", css)
        self.assertRegex(
            css,
            r"\.s30-album-page \.album-chapter-title,\s*"
            r"\.s30-album-page \.album-section-progress-title\{\s*"
            r"(?:[^}]*)position:relative !important;",
        )
        self.assertRegex(
            css,
            r"\.s30-album-page \.team-title\{\s*position:relative !important;",
        )

    def test_stickerwall_uses_approved_v3_vector_number_identity(self):
        css = (APP_DIR / "static" / "style.css").read_text(encoding="utf-8")
        html = self.client.get("/album/wm26").get_data(as_text=True)

        self.assertIn("sammlr-retro-number variant-v3 wall-number", html)
        self.assertIn("sammlr-retro-digits-v3.svg#sammlr-digit-v3-", html)
        self.assertNotIn('class="sticker-number"', html)
        self.assertIn(
            ".s30-album-page .sticker-slot-frame .slot .sammlr-retro-number.wall-number",
            css,
        )
        self.assertIn("font-size:48px", css)
        self.assertIn("slot.missing .sammlr-retro-number.wall-number", css)
        for number in ("00", "10", "12", "14", "17", "20", "88"):
            number_html = webapp.sammlr_retro_number_svg(
                number, "wall-number", variant="v3"
            )
            self.assertEqual(
                len(number), number_html.count("sammlr-retro-digit-face")
            )
            self.assertIn(
                f'<span class="sammlr-retro-number-text">{number}</span>',
                number_html,
            )

    def test_retro_digit_lab_exposes_original_svg_set_without_wall_cutover(self):
        asset = (APP_DIR / "static" / "sammlr-retro-digits.svg").read_text(
            encoding="utf-8"
        )
        asset_v2 = (APP_DIR / "static" / "sammlr-retro-digits-v2.svg").read_text(
            encoding="utf-8"
        )
        asset_v3 = (APP_DIR / "static" / "sammlr-retro-digits-v3.svg").read_text(
            encoding="utf-8"
        )
        lab_html = self.client.get("/dev/retro-ziffern").get_data(as_text=True)
        wall_html = self.client.get("/album/wm26").get_data(as_text=True)

        self.assertEqual(
            "262d07f5b1ed755b4d7ce09c836175b397cefda733515b90f733129f434319c2",
            hashlib.sha256(asset.encode("utf-8")).hexdigest(),
        )
        self.assertEqual(
            "629a08ed6a6a28b27b4ea2320e2c4795d7c4733653c3fecfb08b8a5eadd1a877",
            hashlib.sha256(asset_v2.encode("utf-8")).hexdigest(),
        )
        self.assertEqual(
            "de2afa4ace51efe85399a21fe2884bb9973872f6c9c5ecf8c4e1926db794f3c1",
            hashlib.sha256(asset_v3.encode("utf-8")).hexdigest(),
        )
        self.assertEqual(10, asset.count('<symbol id="sammlr-digit-'))
        self.assertEqual(10, asset_v2.count('<symbol id="sammlr-digit-v2-'))
        self.assertEqual(10, asset_v3.count('<symbol id="sammlr-digit-v3-'))
        self.assertIn(">Entwurf 01</h1>", lab_html)
        self.assertIn(">Entwurf 02</h1>", lab_html)
        self.assertIn(">Entwurf 03</h1>", lab_html)
        for digit in "0123456789":
            self.assertIn(f'id="sammlr-digit-{digit}"', asset)
            self.assertIn(f'#sammlr-digit-{digit}', lab_html)
            self.assertIn(f'id="sammlr-digit-v2-{digit}"', asset_v2)
            self.assertIn(f'#sammlr-digit-v2-{digit}', lab_html)
            self.assertIn(f'id="sammlr-digit-v3-{digit}"', asset_v3)
            self.assertIn(f'#sammlr-digit-v3-{digit}', lab_html)

        def digit_path(asset_text, symbol_prefix, digit):
            match = re.search(
                rf'<symbol id="{symbol_prefix}{digit}"[^>]*>\s*'
                rf'<path[^>]* d="([^"]+)"',
                asset_text,
            )
            self.assertIsNotNone(match)
            return match.group(1)

        for digit in "0235689":
            self.assertEqual(
                digit_path(asset_v2, "sammlr-digit-v2-", digit),
                digit_path(asset_v3, "sammlr-digit-v3-", digit),
            )
        for digit in "147":
            self.assertNotEqual(
                digit_path(asset_v2, "sammlr-digit-v2-", digit),
                digit_path(asset_v3, "sammlr-digit-v3-", digit),
            )

        expected_accessible_counts = {
            "00": 3,
            "12": 3,
            "14": 6,
            "17": 3,
            "20": 3,
            "41": 3,
            "47": 3,
            "71": 3,
            "74": 3,
            "88": 3,
        }
        for number, expected_count in expected_accessible_counts.items():
            self.assertEqual(
                expected_count,
                lab_html.count(
                    f'<span class="sammlr-retro-number-text">{number}</span>'
                ),
            )
        for card_label in (
            "Sticker MEX 7",
            "Sticker MEX 14",
            "Sticker GER 19",
            "Sticker FWC 1",
        ):
            self.assertEqual(3, lab_html.count(f'aria-label="{card_label}"'))
        self.assertIn(
            'class="sammlr-retro-digit-depth" transform="translate(3 4)"',
            lab_html,
        )
        self.assertIn(
            'class="sammlr-retro-digit-depth" transform="translate(4 5)"',
            lab_html,
        )
        self.assertIn("sammlr-retro-number variant-v3 wall-number", wall_html)
        self.assertNotIn("sammlr-retro-number variant-v2 wall-number", wall_html)
        self.assertNotIn("sammlr-retro-digits.svg#sammlr-digit-", wall_html)
        self.assertIn(
            'class="sticker-number">1</span>',
            webapp.sticker_card_inner("vfl", "1", {}),
        )

    def test_album_progress_counts_unique_owned_codes_not_quantity(self):
        with sqlite3.connect(self.test_db) as connection:
            connection.execute(
                "UPDATE albums SET total=4 WHERE id='vfl'"
            )
            connection.commit()

        _, by_code, collected, duplicates, percent, total = (
            webapp.lade_album_for_user("vfl", 1)
        )
        self.assertEqual(3, collected)
        self.assertEqual(2, duplicates)
        self.assertEqual(75, percent)
        self.assertEqual(4, total)
        self.assertEqual(75, webapp.sticker_progress_percent(
            ["1", "2", "3", "4"], by_code
        ))

        response = self.client.post(
            "/album/vfl/sticker/3/quantity",
            data={"delta": "1"},
        )
        payload = response.get_json()
        self.assertEqual(4, payload["album"]["collected"])
        self.assertEqual(100, payload["album"]["percent"])

    def test_undo_restores_add_inventory_change(self):
        self.client.post("/add/vfl/1")
        self.assert_sticker("1", quantity=4, duplicates=3)

        response = self.client.post("/undo")

        self.assertEqual(302, response.status_code)
        self.assert_sticker("1", quantity=3, duplicates=2)
        with self.client.session_transaction() as session:
            self.assertNotIn("last_action", session)

    def test_undo_restores_remove_inventory_change(self):
        self.client.post("/remove/vfl/2")
        self.assertIsNone(self.db_row("2"))

        response = self.client.post("/undo")

        self.assertEqual(302, response.status_code)
        self.assert_sticker("2", quantity=1, duplicates=0)
        with self.client.session_transaction() as session:
            self.assertNotIn("last_action", session)

    def test_existing_sticker_code_resolution_is_unchanged(self):
        self.assertEqual("1", webapp.resolve_code("vfl", "1"))
        self.assertEqual("250", webapp.resolve_code("vfl", "250"))
        self.assertIsNone(webapp.resolve_code("vfl", "0"))
        self.assertIsNone(webapp.resolve_code("vfl", "251"))
        self.assertIsNone(webapp.resolve_code("vfl", "not-a-code"))


if __name__ == "__main__":
    unittest.main()
