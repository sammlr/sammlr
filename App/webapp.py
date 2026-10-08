import sqlite3
import os
import shutil
import re
import hashlib
import hmac
import secrets
import sys
import time
import threading
from pathlib import Path
from functools import lru_cache, wraps
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from flask import Flask, Response, abort, g, request, redirect, session, jsonify, send_from_directory, render_template
from flask.testing import FlaskClient
import json
from html import escape
from werkzeug.datastructures import Headers
from werkzeug.middleware.proxy_fix import ProxyFix
from em24_data import build_em24
from wm26_data import build_wm26
from profile_sticker import (
    PROFILE_STICKER_COLORS,
    PROFILE_STICKER_COUNTRIES,
    ProfileStickerSettings,
    ProfileStickerValidationError,
    SAFE_PORTRAIT_NAME,
    load_settings as load_profile_sticker_settings,
    remove_portrait,
    render_profile_sticker,
    save_settings as save_profile_sticker_settings,
    schema_available as profile_sticker_schema_available,
    store_portrait,
    validate_settings as validate_profile_sticker_settings,
)
from trophy_definitions import (
    GLOBAL_SCOPE,
    album_trophy_definitions,
    canonical_album_trophy_definitions,
)
from services.typed_notifications import (
    TypedNotificationService,
    typed_notification_schema_available,
)
from services.notification_history import (
    NotificationHistoryService,
    NotificationOpenCode,
)
from services.feed_events import FeedEventService, feed_event_schema_available
from services.collector_profiles import AccountSettingsService, CollectorProfileService
from services.successful_trade_projection import SuccessfulTradeProjectionService
from services.statistics_projection import StatisticsProjectionService
from services.album_privacy import (
    ALBUM_VISIBILITIES,
    AlbumPrivacyService,
    AlbumPrivacyUpdateCode,
)
from services.profile_privacy import (
    PROFILE_PRIVACIES,
    ProfilePrivacyService,
    ProfilePrivacyUpdateCode,
)
from services.inventory import InventoryReadService
from services.inventory_write import InventoryWriteService
from services.history_cutover import (
    AlbumHistoryCutoverService,
    HistoricalInventoryWriteService,
    cutover_schema_available,
)
from services.trophy_unlocks import (
    CanonicalTrophyUnlockService,
    canonical_trophy_schema_available,
)
from services.trade_reservations import (
    TradeAcceptanceCode,
    TradeReservationService,
    reservation_schema_available,
)
from services.trade_shipping import (
    TradeShippingCode,
    TradeShippingService,
    shipping_status_for_trade,
)
from services.trade_receipt import (
    TradeReceiptCode,
    TradeReceiptService,
    receipt_status_for_trade,
)
from services.trade_problems import (
    PartialReceiptInputDTO,
    TradeProblemCode,
    TradeProblemService,
    TradeProblemType,
    problem_reports_for_trade,
    problem_schema_available,
)
from services.top_match_optimization import TopMatchOptimizationService
from services.trade_coverage import TradeCoverageService
from services.executable_trade_matches import ExecutableTradeMatchService
from services.collection_projection import CollectionProjectionService
from services.trade_ratings import TradeRatingCode, TradeRatingService
from services.community import (
    CommunityMutationCode,
    CommunityService,
    UserActivityService,
    community_schema_available,
)
from services.smart_trade_requests import (
    SMART_ACCEPTED_EVENT,
    SMART_REQUEST_MARKER,
    SmartTradeRequestCode,
    SmartTradeRequestService,
    is_smart_trade_request,
)
from services.auth_security import (
    AuthSecurityService,
    AuthenticationCode,
    WERKZEUG_PASSWORD_SCHEME,
    auth_schema_available,
    canonical_password_hash,
)
from services.account_lifecycle import (
    ACTIVE,
    AccountLifecycleCode,
    AccountLifecycleService,
    account_lifecycle_schema_available,
)
from services.user_data_export import UserDataExportService
from services.observability import (
    JsonErrorTracker,
    REQUEST_ID_HEADER,
    pseudonymous_user_ref,
    safe_request_id,
    utc_timestamp,
    write_request_log,
)
from services.runtime_operations import (
    EXPECTED_SCHEMA_VERSION,
    TRADE_V2_COMPATIBLE_SCHEMA_VERSIONS,
    RuntimeConfigurationError,
    validate_database,
    validate_production_environment,
)
from urllib.parse import quote

from services.smartdeal_runtime import dispatch_request as dispatch_smartdeal_request, cleanup as cleanup_smartdeal_runtime


def smartdeal_request_boundary(connection, trade_id, action):
    """Route adapter only; domain services own all V1 transitions and transactions."""
    try:
        result = dispatch_smartdeal_request(connection, trade_id, current_user_id(), action,
                                          catalog_provider=all_codes)
    except (ValueError, sqlite3.DatabaseError):
        connection.close()
        return ('Trade action unavailable', 409)
    if result is None:
        return None
    connection.close()
    if result in ('ACCEPTED', 'ALREADY_ACCEPTED', 'RELEASED', 'ALREADY_RELEASED'):
        return redirect(f'/trades/{trade_id}')
    return ('Trade action unavailable', 403 if result == 'UNAUTHORIZED' else 409)


app = Flask(__name__)
SQLITE_PROJECTION_READ_LOCK = threading.RLock()
MAX_PROFILE_NAME_LENGTH = 120
MAX_USERNAME_LENGTH = 80
MAX_PASSWORD_LENGTH = 1024
MAX_QUERY_STRING_LENGTH = 8192


def serialized_sqlite_projection(function):
    """Avoid pathological SQLite read thrashing on the one-worker deployment."""

    @wraps(function)
    def wrapped(*args, **kwargs):
        with SQLITE_PROJECTION_READ_LOCK:
            return function(*args, **kwargs)
    return wrapped


def configure_flask_security(application, direct_development=False):
    configured_environment = os.environ.get("SAMMLR_ENV")
    environment = (
        configured_environment.strip().lower()
        if configured_environment is not None
        else ("development" if direct_development else "production")
    )
    if environment not in {"production", "development", "testing"}:
        raise RuntimeError("SAMMLR_ENV must be production, development, or testing")

    secret_key = os.environ.get("SAMMLR_SECRET_KEY")
    if not secret_key and environment == "development":
        secret_key = secrets.token_hex(32)
        print("Temporary development secret active – sessions reset on restart.")
    if not secret_key:
        raise RuntimeError(
            "SAMMLR_SECRET_KEY is required outside explicit development mode"
        )

    application.config.update(
        SECRET_KEY=secret_key,
        SAMMLR_ENV=environment,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=(environment == "production"),
        SESSION_COOKIE_DOMAIN=None,
        CSRF_ENABLED=True,
        TESTING_AUTH_VERSION_COMPAT=True,
        MAX_CONTENT_LENGTH=1024 * 1024,
        MAX_FORM_MEMORY_SIZE=256 * 1024,
        MAX_FORM_PARTS=100,
    )


configure_flask_security(app, direct_development=(__name__ == "__main__"))
app.config.setdefault(
    "PROFILE_PORTRAIT_DIR",
    os.environ.get("PROFILE_PORTRAIT_DIR") or (
        "/var/data/profile_portraits"
        if app.config["SAMMLR_ENV"] == "production"
        else os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", "profile_portraits")
    ),
)

app.config["ERROR_TRACKER"] = JsonErrorTracker()
if app.config["SAMMLR_ENV"] == "production":
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_port=0,
        x_prefix=0,
    )


class Http500Response(RuntimeError):
    """Sanitized marker for a route that returned HTTP 500 directly."""


def sanitized_flask_exception_log(exception_info):
    error = exception_info[1]
    tracker = app.config.get("ERROR_TRACKER") or JsonErrorTracker()
    tracker.capture_exception(
        error,
        request_id=getattr(g, "request_id", None),
        method=request.method,
        route=request.url_rule.rule if request.url_rule is not None else "<unmatched>",
    )
    g.error_tracked = True


app.log_exception = sanitized_flask_exception_log


def new_csrf_token():
    return secrets.token_hex(32)


def ensure_csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = new_csrf_token()
        session["csrf_token"] = token
    return token


class SammlrTestClient(FlaskClient):
    """Exercise real CSRF validation while keeping historical tests concise."""

    def open(self, *args, **kwargs):
        csrf_protect = kwargs.pop("csrf_protect", True)
        method = str(kwargs.get("method") or "GET").upper()
        if self.application.testing and method == "POST" and csrf_protect:
            with self.session_transaction() as test_session:
                token = test_session.get("csrf_token") or new_csrf_token()
                test_session["csrf_token"] = token
            headers = Headers(kwargs.get("headers"))
            headers.set("X-CSRF-Token", token)
            kwargs["headers"] = headers
        return super().open(*args, **kwargs)


app.test_client_class = SammlrTestClient

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
MASTER_ASSET_DIR = os.path.join(
    PROJECT_DIR,
    "Branding",
    "Design Bible",
    "01 Master Assets",
)
MASTER_LOGO_V1_FILENAME = "master_logo_v1.png"
MASTER_LOGO_V1_PATH = os.path.join(MASTER_ASSET_DIR, MASTER_LOGO_V1_FILENAME)
ALBUM_BRANDING_FILENAMES = {
    "vfl": "master_album_branding_vfl_v1.png",
    "wm26": "master_album_branding_wm_stamp_v1.png",
}
ALBUM_COVER_BRANDING_FILENAMES = {
    "vfl": "master_album_branding_vfl_v1.png",
    "wm26": "master_album_branding_wm_v1.png",
}


def preferred_master_asset(svg_filename, png_filename):
    if os.path.exists(os.path.join(MASTER_ASSET_DIR, svg_filename)):
        return svg_filename
    return png_filename


MASTER_TROPHY_ASSETS = {
    "album_empty": "master_album_open_empty_v1.svg",
    "album_full": "master_album_open_full_v1.svg",
    "crest_expert": "master_crest_expert_v2.png",
    "sticker_player": "master_sticker_player_v1.svg",
    "group_table": "master_group_table_v1.svg",
    "wm_history": preferred_master_asset("master_wm_history_v1.svg", "master_wm_history_v1.png"),
    "wm_teamphoto": "master_wm_teamphoto_v1.svg",
    "bottle_label": "master_bottle_label_v1.svg",
    "wm_champion_cup": preferred_master_asset("master_album_branding_wm_v2.svg", "master_album_branding_wm_v2.png"),
}
WM26_GROUP_ASSET_LETTERS = "abcdefghijkl"
DB = os.environ.get(
    "DATABASE_PATH",
    os.path.join(BASE_DIR, "Database", "sammlr.db")
)
SEED_DB = os.path.join(BASE_DIR, "Database", "sammlr.db")


if app.config["SAMMLR_ENV"] == "production":
    try:
        production_database = validate_production_environment(os.environ)
        validate_database(production_database, expected_version=EXPECTED_SCHEMA_VERSION,
                          compatible_versions=TRADE_V2_COMPATIBLE_SCHEMA_VERSIONS)
    except Exception as startup_error:
        app.config["ERROR_TRACKER"].capture_exception(
            startup_error,
            route="startup",
            method="STARTUP",
        )
        raise


def table_exists(con, table_name):
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    ).fetchone()
    return row is not None


def table_count(con, table_name):
    if not table_exists(con, table_name):
        return 0
    row = con.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
    return row["count"] if row else 0


def public_username_select(con, table_alias, output_alias):
    if account_lifecycle_schema_available(con):
        return (
            f"CASE WHEN {table_alias}.account_state='anonymized' "
            f"THEN 'Gelöschter Nutzer' ELSE {table_alias}.username END AS {output_alias}"
        )
    return f"{table_alias}.username AS {output_alias}"


def target_db_has_user_data(db_path):
    if not os.path.exists(db_path):
        return False

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        for table_name in ("stickers", "trade_requests", "notifications", "unlocked_trophies"):
            if table_count(con, table_name) > 0:
                return True


        return False
    finally:
        con.close()


def album_count_in_db(db_path):
    if not os.path.exists(db_path):
        return 0

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        return table_count(con, "albums")
    finally:
        con.close()


def initialize_render_database_from_seed():
    target_path = os.path.abspath(DB)
    seed_path = os.path.abspath(SEED_DB)

    if target_path != "/var/data/sammlr.db":
        return

    if not os.path.exists(seed_path):
        return

    needs_seed = (not os.path.exists(target_path)) or album_count_in_db(target_path) < 3
    if not needs_seed:
        return

    if target_db_has_user_data(target_path):
        return

    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    shutil.copy2(seed_path, target_path)


@app.route("/design-bible/master-assets/<path:filename>")
def design_bible_master_asset(filename):
    return send_from_directory(MASTER_ASSET_DIR, filename)


def current_user_id():
    return session.get("user_id", 1)


def get_db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def configured_friendship_checker():
    checker = app.config.get("FRIENDSHIP_CHECKER")
    return checker if callable(checker) else None


def album_privacy_service(connection):
    return AlbumPrivacyService(
        connection,
        friendship_checker=configured_friendship_checker(),
    )


def debug_db():
    db_exists = os.path.exists(DB)
    db_size = os.path.getsize(DB) if db_exists else 0
    cwd = os.getcwd()
    root_files = sorted(os.listdir("."))
    database_files = []
    database_error = None
    if os.path.isdir("Database"):
        database_files = sorted(os.listdir("Database"))
    else:
        database_error = "Database folder not found from current working directory"

    seed_exists = os.path.exists(SEED_DB)
    seed_size = os.path.getsize(SEED_DB) if seed_exists else 0

    con = get_db()

    tables = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    albums = con.execute(
        "SELECT id, name FROM albums ORDER BY id"
    ).fetchall()
    sticker_counts = con.execute(
        "SELECT album_id, COUNT(*) AS count FROM stickers GROUP BY album_id ORDER BY album_id"
    ).fetchall()
    user_albums = con.execute(
        "SELECT user_id, album_id FROM user_albums ORDER BY user_id, album_id"
    ).fetchall()
    con.close()

    def rows_to_dicts(rows):
        return [dict(row) for row in rows]

    debug_data = {
        "cwd": cwd,
        "root_files": root_files,
        "database_files": database_files,
        "database_error": database_error,
        "seed_db_path": SEED_DB,
        "seed_file_exists": seed_exists,
        "seed_file_size_bytes": seed_size,
        "db_path": DB,
        "file_exists": db_exists,
        "file_size_bytes": db_size,
        "tables": [row["name"] for row in tables],
        "albums": rows_to_dicts(albums),
        "sticker_counts_by_album": rows_to_dicts(sticker_counts),
        "user_albums": rows_to_dicts(user_albums),
    }

    return (
        "<pre>"
        + escape(json.dumps(debug_data, indent=2, ensure_ascii=False))
        + "</pre>"
        + '<form method="POST" action="/debug-seed-now">'
        + '<button type="submit">Development-Datenbank aus Seed ersetzen</button>'
        + "</form>"
    )


def debug_seed_now():
    target_path = os.path.abspath(DB)
    seed_path = os.path.abspath(SEED_DB)

    if not os.path.exists(seed_path):
        return "Seed database not found", 500

    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    shutil.copy2(seed_path, target_path)

    return redirect("/debug-db?fresh=seeded")


CEOKLAUE_VECTOR_DIR = os.path.join(
    PROJECT_DIR, "Branding", "CEOKlaue", "02_vectors", "glyphs"
)
CEOKLAUE_PREVIEW_DIR = os.path.join(
    PROJECT_DIR, "Branding", "CEOKlaue", "03_font", "preview"
)
CEOKLAUE_PREVIEW_FONT = "CEOKlaue-v0.2-preview.woff2"
CEOKLAUE_HARMONY_DIR = os.path.join(
    PROJECT_DIR, "Branding", "CEOKlaue", "04_harmony"
)
CEOKLAUE_HARMONY_MANIFEST = os.path.join(CEOKLAUE_HARMONY_DIR, "manifest.json")
CEOKLAUE_RUNTIME_MANIFEST = os.path.join(
    PROJECT_DIR, "Branding", "CEOKlaue", "05_runtime", "manifest.json"
)
CEOKLAUE_RUNTIME_MIXING_SEED = "sammlr-ceoklaue-stickerlist-v1"
CEOKLAUE_MARKER_MIXING_SEED = "sammlr-ceoklaue-stickerlist-markers-v1"
CEOKLAUE_FINAL_MINI_RESELECTION_MANIFEST = os.path.join(
    PROJECT_DIR, "Branding", "CEOKlaue", "final-mini-reselection-source-manifest.json"
)
CEOKLAUE_FINAL_MINI_RESELECTION_STORAGE_KEY = "sammlr.ceoklaue.finalMiniSelection.v01"
CEOKLAUE_ANALOG_UI_FINAL_MANIFEST = os.path.join(
    PROJECT_DIR, "Branding", "CEOKlaue", "analog-ui-final-source-manifest.json"
)
CEOKLAUE_ANALOG_UI_FINAL_STORAGE_KEY = "sammlr.ceoklaue.analogUiFinalSelection.v01"
CEOKLAUE_FINAL_FH_REPAIR_MANIFEST = os.path.join(
    PROJECT_DIR, "Branding", "CEOKlaue", "final-fh-repair-source-manifest.json"
)
CEOKLAUE_FINAL_FH_REPAIR_VECTOR_DIR = os.path.join(
    PROJECT_DIR, "Branding", "CEOKlaue", "02_vectors", "final_fh_repair"
)
CEOKLAUE_FINAL_FH_REPAIR_STORAGE_KEY = "sammlr.ceoklaue.finalFHRepairSelection.v02"
CEOKLAUE_BUTTON_BRACKET_MANIFEST = os.path.join(
    PROJECT_DIR, "Branding", "CEOKlaue", "button-bracket-source-manifest.json"
)
CEOKLAUE_BUTTON_BRACKET_MIXING_SEED = "sammlr-ceoklaue-button-brackets-v1"
CEOKLAUE_CURRENT_VARIANT = "03"
CEOKLAUE_TRIPLE_STORAGE_KEY = "sammlr.ceoklaue.tripleSelection.v03"
CEOKLAUE_TRIPLE_SLOT_ONE = {
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
CEOKLAUE_GLYPH_GROUPS = (
    (
        "Großbuchstaben",
        tuple((character, f"cap_{character}") for character in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    ),
    (
        "Kleinbuchstaben",
        tuple((character, f"lower_{character}") for character in "abcdefghijklmnopqrstuvwxyz"),
    ),
    ("Ziffern", tuple((character, character) for character in "0123456789")),
    (
        "Umlaute / Sonderzeichen",
        (
            ("ä", "adieresis"), ("ö", "odieresis"), ("ü", "udieresis"),
            ("Ä", "uni00C4"), ("Ö", "uni00D6"), ("Ü", "uni00DC"),
            ("ß", "germandbls"), (".", "period"), (",", "comma"),
            (":", "colon"), (";", ";"), ("!", "exclam"), ("?", "question"),
            ("-", "hyphen"), ("+", "plus"), ("/", "slash"),
            ("&", "ampersand"), ("%", "percent"),
            ("(", "parenleft"), (")", "parenright"),
        ),
    ),
)


def ceoklaue_development_only():
    if app.config.get("SAMMLR_ENV") not in {"development", "testing"}:
        abort(404)


@lru_cache(maxsize=1)
def ceoklaue_vector_catalog():
    catalog = {}
    for _group_label, glyphs in CEOKLAUE_GLYPH_GROUPS:
        for character, glyph_key in glyphs:
            glyph_directory = os.path.join(CEOKLAUE_VECTOR_DIR, glyph_key)
            variants = []
            if os.path.isdir(glyph_directory):
                for filename in sorted(os.listdir(glyph_directory)):
                    match = re.fullmatch(rf"{re.escape(glyph_key)}_(\d{{2}})\.svg", filename)
                    if not match:
                        continue
                    svg_path = os.path.join(glyph_directory, filename)
                    try:
                        with open(svg_path, encoding="utf-8") as source:
                            svg_source = source.read(512)
                    except OSError:
                        continue
                    viewbox_match = re.search(
                        r'viewBox="\s*[-\d.]+\s+[-\d.]+\s+([\d.]+)\s+([\d.]+)"',
                        svg_source,
                    )
                    if not viewbox_match:
                        continue
                    variants.append({
                        "number": match.group(1),
                        "filename": filename,
                        "width": float(viewbox_match.group(1)),
                        "height": float(viewbox_match.group(2)),
                    })
            catalog[glyph_key] = {"character": character, "variants": variants}
    return catalog


def ceoklaue_glyph_workbench_asset(glyph_key, filename):
    ceoklaue_development_only()
    catalog = ceoklaue_vector_catalog()
    glyph = catalog.get(glyph_key)
    allowed = {variant["filename"] for variant in glyph["variants"]} if glyph else set()
    if filename not in allowed:
        abort(404)
    response = send_from_directory(
        os.path.join(CEOKLAUE_VECTOR_DIR, glyph_key),
        filename,
        mimetype="image/svg+xml",
        max_age=0,
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


def ceoklaue_glyph_workbench():
    ceoklaue_development_only()
    catalog = ceoklaue_vector_catalog()
    sections = []
    character_count = 0
    source_character_count = 0
    variant_count = 0
    initial_counts = {0: 0, 1: 0, 2: 0, 3: 0}
    target_characters = []
    for group_label, glyphs in CEOKLAUE_GLYPH_GROUPS:
        character_blocks = []
        for character, glyph_key in glyphs:
            target_characters.append(character)
            variants = catalog.get(glyph_key, {}).get("variants", [])
            character_count += 1
            variant_count += len(variants)
            if variants:
                source_character_count += 1
            initial_selection = (
                [CEOKLAUE_TRIPLE_SLOT_ONE[character]]
                if character in CEOKLAUE_TRIPLE_SLOT_ONE else []
            )
            initial_counts[len(initial_selection)] += 1
            cards = []
            for variant in variants:
                number = variant["number"]
                selected_class = " is-selected" if number in initial_selection else ""
                selected_label = (
                    '<span class="glyph-selected-label">Ausgewählt ①</span>'
                    if number in initial_selection else
                    '<span class="glyph-selected-label"></span>'
                )
                rendered_width = max(1, round(variant["width"] * 3))
                rendered_height = max(1, round(variant["height"] * 3))
                asset_url = (
                    f"/dev/ceoklaue/glyph/{quote(glyph_key, safe='')}/"
                    f"{quote(variant['filename'], safe='')}"
                )
                cards.append(f"""
                <button class="glyph-variant{selected_class}" type="button"
                        data-character="{escape(character)}" data-variant="{number}"
                        aria-pressed="{'true' if number in initial_selection else 'false'}">
                    <span class="glyph-canvas">
                        <img src="{asset_url}" alt="{escape(character)} Variante {number}"
                             width="{rendered_width}" height="{rendered_height}">
                    </span>
                    <span class="glyph-variant-meta">
                        <strong>{number}</strong>
                        {selected_label}
                    </span>
                </button>
                """)
            slots = "".join(
                f'<li data-slot-index="{index}"><span>{symbol}</span><strong>{initial_selection[index] if index < len(initial_selection) else "–"}</strong></li>'
                for index, symbol in enumerate(("①", "②", "③"))
            )
            source_note = (
                "" if variants else
                '<p class="glyph-no-source">Keine extrahierte handschriftliche Vorlage vorhanden.</p>'
            )
            initial_count = len(initial_selection)
            initial_status = (
                "3/3 FERTIG" if initial_count == 3 else
                "2/3 FEHLT 1" if initial_count == 2 else
                "1/3 FEHLEN 2" if initial_count == 1 else
                "0/3 FEHLEN 3"
            )
            character_blocks.append(f"""
            <article class="glyph-character{' no-source' if not variants else ''}"
                     data-glyph="{escape(character)}" data-selection-count="{initial_count}">
                <div class="glyph-character-head">
                    <h3>{escape(character)}</h3>
                    <span class="glyph-status" data-count="{initial_count}">{initial_status}</span>
                </div>
                <ol class="glyph-slots" aria-label="Ausgewählte Slots">{slots}</ol>
                <p class="glyph-feedback" role="status" aria-live="polite"></p>
                <div class="glyph-variants">{''.join(cards)}</div>
                {source_note}
            </article>
            """)
        sections.append(f"""
        <section class="glyph-group">
            <h2>{escape(group_label)}</h2>
            {''.join(character_blocks)}
        </section>
        """)

    default_selection = {
        character: [variant]
        for character, variant in CEOKLAUE_TRIPLE_SLOT_ONE.items()
    }
    default_selection_json = json.dumps(
        default_selection, ensure_ascii=False, separators=(",", ":")
    )
    target_characters_json = json.dumps(
        target_characters, ensure_ascii=False, separators=(",", ":")
    )
    remaining_count = sum((3 - count) * amount for count, amount in initial_counts.items())

    html = f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>CEOKlaue v0.2 · Glyphen-Auswahlwerkbank</title>
<style>
:root{{--ink:#171419;--muted:#67616a;--line:#d9d5dc;--selected:#12633f}}
*{{box-sizing:border-box}}
body{{margin:0;color:var(--ink);background:#f2f2f3;font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
button{{font:inherit}}
.workbench{{width:min(100%,1600px);margin:auto;padding:28px}}
.workbench-head{{position:relative;z-index:20;margin:0 -12px 30px;padding:18px 12px;border-bottom:1px solid var(--line);background:#f2f2f3}}
.workbench-head h1{{margin:0 0 4px;font-size:28px}}
.workbench-head p{{margin:0;color:var(--muted)}}
.workbench-counts{{margin-top:8px;font-variant-numeric:tabular-nums}}
.inventory-stats{{display:flex;flex-wrap:wrap;gap:8px 18px;margin:14px 0 0;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:#fff;font-variant-numeric:tabular-nums}}
.inventory-stats span{{white-space:nowrap}}
.filters{{display:flex;flex-wrap:wrap;gap:7px;margin-top:12px}}
.filter-button{{padding:7px 11px;border:1px solid #aaa2ae;border-radius:999px;background:#fff;cursor:pointer}}
.filter-button[aria-pressed="true"]{{color:#fff;border-color:#2d2531;background:#2d2531}}
.export-tools{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:16px}}
.export-box{{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px}}
.export-box textarea{{width:100%;min-height:96px;padding:10px;border:1px solid #c9c4cd;border-radius:8px;resize:vertical;background:#fff;font:13px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace}}
.export-box button{{min-width:190px;padding:9px;border:0;border-radius:8px;color:#fff;background:#2d2531;font-weight:700;cursor:pointer}}
.glyph-group{{margin:0 0 42px}}
.glyph-group>h2{{margin:0 0 18px;padding-bottom:8px;border-bottom:2px solid #bdb7c2;font-size:19px;letter-spacing:.04em;text-transform:uppercase}}
.glyph-character{{margin:0 0 22px;padding:16px;border:1px solid var(--line);border-radius:10px;background:#fff}}
.glyph-character-head{{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:10px}}
.glyph-character h3{{margin:0;font:700 26px/1 ui-monospace,SFMono-Regular,Menlo,monospace}}
.glyph-status{{padding:4px 8px;border-radius:999px;color:#5c5360;background:#ebe8ed;font-size:12px;font-weight:700}}
.glyph-status[data-count="3"]{{color:#fff;background:var(--selected)}}
.glyph-slots{{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 8px;padding:0;list-style:none}}
.glyph-slots li{{min-width:70px;padding:5px 8px;border:1px solid #cfc9d2;border-radius:6px;background:#f7f7f8;font-variant-numeric:tabular-nums}}
.glyph-slots li span{{margin-right:5px;color:var(--muted)}}
.glyph-feedback{{min-height:20px;margin:0 0 5px;color:#825329;font-size:12px}}
.glyph-variants{{display:flex;flex-wrap:wrap;gap:12px}}
.glyph-variant{{width:286px;padding:8px;border:2px solid transparent;border-radius:9px;color:inherit;background:#f7f7f8;cursor:pointer}}
.glyph-variant:hover{{border-color:#b7afbc}}
.glyph-variant.is-selected{{border-color:var(--selected);box-shadow:0 0 0 2px rgba(18,99,63,.15)}}
.glyph-canvas{{width:266px;height:266px;display:flex;align-items:center;justify-content:center;overflow:hidden;border:1px solid #e1dee4;background:#fff}}
.glyph-canvas img{{display:block;width:70%;height:70%;object-fit:contain}}
.glyph-variant-meta{{min-height:46px;padding-top:7px;display:flex;align-items:center;justify-content:center;gap:8px;color:var(--muted);font-size:12px;text-transform:uppercase}}
.glyph-variant-meta strong{{color:var(--ink);font:700 14px/1 ui-monospace,SFMono-Regular,Menlo,monospace}}
.glyph-selected-label{{display:none;padding:3px 6px;border-radius:999px;color:#fff;background:var(--selected)}}
.glyph-variant.is-selected .glyph-selected-label{{display:inline}}
.glyph-no-source{{margin:10px 0 0;color:var(--muted);font-size:13px}}
[hidden]{{display:none!important}}
@media(max-width:850px){{.export-tools{{grid-template-columns:1fr}}}}
@media(max-width:700px){{.workbench{{padding:14px}}.export-box{{grid-template-columns:1fr}}.export-box button{{min-height:44px}}}}
</style>
</head>
<body><main class="workbench">
<header class="workbench-head">
    <h1>CEOKlaue · Triple-Glyph-Werkbank</h1>
    <p>Drei echte handschriftliche Varianten pro Zielzeichen. Auswahl bleibt ausschließlich in diesem Browser.</p>
    <p class="workbench-counts"><strong>{character_count}</strong> Zielzeichen · <strong>{source_character_count}</strong> mit Quellen · <strong>{variant_count}</strong> echte SVG-Varianten</p>
    <div class="inventory-stats" aria-label="CEOKlaue Glyphenbestand">
        <strong>CEOKlaue Glyphenbestand</strong>
        <span>3/3: <strong data-stat="3">{initial_counts[3]}</strong> Zeichen</span>
        <span>2/3: <strong data-stat="2">{initial_counts[2]}</strong> Zeichen</span>
        <span>1/3: <strong data-stat="1">{initial_counts[1]}</strong> Zeichen</span>
        <span>0/3: <strong data-stat="0">{initial_counts[0]}</strong> Zeichen</span>
        <span>Noch benötigte Varianten insgesamt: <strong id="remainingCount">{remaining_count}</strong></span>
    </div>
    <div class="filters" aria-label="Vollständigkeitsfilter">
        <button class="filter-button" type="button" data-filter="all" aria-pressed="true">Alle</button>
        <button class="filter-button" type="button" data-filter="3">Fertig 3/3</button>
        <button class="filter-button" type="button" data-filter="2">Fehlt 1</button>
        <button class="filter-button" type="button" data-filter="1">Fehlen 2</button>
        <button class="filter-button" type="button" data-filter="0">Fehlen 3</button>
    </div>
    <div class="export-tools">
        <div class="export-box">
            <textarea id="selectionSummary" readonly aria-label="Triple-Auswahl"></textarea>
            <button id="copySelection" type="button">Auswahl kopieren</button>
        </div>
        <div class="export-box">
            <textarea id="missingSummary" readonly aria-label="Fehlbestand"></textarea>
            <button id="copyMissing" type="button">Fehlende Glyphen kopieren</button>
        </div>
    </div>
</header>
{''.join(sections)}
</main>
<script>
(function(){{
    const storageKey={json.dumps(CEOKLAUE_TRIPLE_STORAGE_KEY)};
    const targetCharacters={target_characters_json};
    const defaults={default_selection_json};
    const slotSymbols=['①','②','③'];
    const cards=Array.from(document.querySelectorAll('.glyph-variant'));
    const characters=Array.from(document.querySelectorAll('.glyph-character'));
    const summary=document.getElementById('selectionSummary');
    const missingSummary=document.getElementById('missingSummary');
    let stored=null;
    try{{ stored=JSON.parse(localStorage.getItem(storageKey)||'null'); }}catch(error){{ stored=null; }}
    const selection={{}};
    targetCharacters.forEach(function(character){{
        const block=characters.find(function(item){{return item.dataset.glyph===character;}});
        const allowed=new Set(Array.from(block.querySelectorAll('.glyph-variant')).map(function(card){{return card.dataset.variant;}}));
        const candidate=stored && Object.prototype.hasOwnProperty.call(stored,character)
            ? stored[character] : (defaults[character]||[]);
        selection[character]=Array.from(new Set(Array.isArray(candidate)?candidate:[]))
            .filter(function(variant){{return allowed.has(variant);}}).slice(0,3);
    }});
    let activeFilter='all';

    function persist(){{
        localStorage.setItem(storageKey,JSON.stringify(selection));
    }}

    function statusText(count){{
        if(count===3) return '3/3 FERTIG';
        if(count===2) return '2/3 FEHLT 1';
        if(count===1) return '1/3 FEHLEN 2';
        return '0/3 FEHLEN 3';
    }}

    function renderFilter(){{
        characters.forEach(function(block){{
            const count=selection[block.dataset.glyph].length;
            block.hidden=activeFilter!=='all' && String(count)!==activeFilter;
        }});
        document.querySelectorAll('.glyph-group').forEach(function(group){{
            group.hidden=Array.from(group.querySelectorAll('.glyph-character')).every(function(block){{return block.hidden;}});
        }});
    }}

    function render(){{
        cards.forEach(function(card){{
            const slot=selection[card.dataset.character].indexOf(card.dataset.variant);
            card.classList.toggle('is-selected',slot!==-1);
            card.setAttribute('aria-pressed',slot!==-1?'true':'false');
            card.querySelector('.glyph-selected-label').textContent=slot===-1?'':'AUSGEWÄHLT '+slotSymbols[slot];
        }});
        const totals={{0:0,1:0,2:0,3:0}};
        let remaining=0;
        characters.forEach(function(block){{
            const selected=selection[block.dataset.glyph];
            const count=selected.length;
            totals[count]+=1;
            remaining+=3-count;
            block.dataset.selectionCount=String(count);
            const status=block.querySelector('.glyph-status');
            status.dataset.count=String(count);
            status.textContent=statusText(count);
            block.querySelectorAll('.glyph-slots strong').forEach(function(slot,index){{slot.textContent=selected[index]||'–';}});
        }});
        Object.keys(totals).forEach(function(count){{document.querySelector('[data-stat="'+count+'"]').textContent=String(totals[count]);}});
        document.getElementById('remainingCount').textContent=String(remaining);
        summary.value=targetCharacters.filter(function(character){{return selection[character].length;}})
            .map(function(character){{return character+'='+selection[character].join(',');}}).join('\\n');
        missingSummary.value=targetCharacters.filter(function(character){{return selection[character].length<3;}})
            .map(function(character){{
                const missing=3-selection[character].length;
                return character+': '+missing+' weitere '+(missing===1?'Variante':'Varianten')+' benötigt';
            }}).join('\\n');
        renderFilter();
    }}

    cards.forEach(function(card){{
        card.addEventListener('click',function(){{
            const selected=selection[card.dataset.character];
            const existing=selected.indexOf(card.dataset.variant);
            const feedback=card.closest('.glyph-character').querySelector('.glyph-feedback');
            feedback.textContent='';
            if(existing!==-1){{
                selected.splice(existing,1);
            }}else if(selected.length<3){{
                selected.push(card.dataset.variant);
            }}else{{
                feedback.textContent='Maximal 3 Varianten. Erst eine Auswahl entfernen.';
                return;
            }}
            persist();
            render();
        }});
    }});

    document.querySelectorAll('.filter-button').forEach(function(button){{
        button.addEventListener('click',function(){{
            activeFilter=button.dataset.filter;
            document.querySelectorAll('.filter-button').forEach(function(item){{item.setAttribute('aria-pressed',item===button?'true':'false');}});
            renderFilter();
        }});
    }});

    async function copyText(button,textarea){{
        try{{ await navigator.clipboard.writeText(textarea.value); }}catch(error){{
            textarea.focus(); textarea.select(); document.execCommand('copy');
        }}
        button.textContent='Kopiert';
        window.setTimeout(function(){{button.textContent=button.dataset.label;}},1200);
    }}
    document.getElementById('copySelection').dataset.label='Auswahl kopieren';
    document.getElementById('copyMissing').dataset.label='Fehlende Glyphen kopieren';
    document.getElementById('copySelection').addEventListener('click',function(){{copyText(this,summary);}});
    document.getElementById('copyMissing').addEventListener('click',function(){{copyText(this,missingSummary);}});
    render();
    if(!stored){{
        persist();
    }}
}})();
</script>
</body></html>"""
    response = Response(html, mimetype="text/html")
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@lru_cache(maxsize=1)
def ceoklaue_final_reselection_manifest():
    with open(CEOKLAUE_ANALOG_UI_FINAL_MANIFEST, encoding="utf-8") as source:
        manifest = json.load(source)
    if manifest.get("version") != "CEOKlaue analog UI final source import v1":
        raise RuntimeError("Unknown CEOKlaue analog UI final manifest")
    expected_selection = ["u", "A", ",", "middle_dot"]
    if [record["selection_key"] for record in manifest["selection_groups"]] != expected_selection:
        raise RuntimeError("CEOKlaue analog UI selection scope changed")
    totals = manifest.get("totals", {})
    expected_totals = {
        "new_u_candidates": 5,
        "new_A_candidates": 5,
        "new_comma_candidates": 5,
        "new_middle_dot_candidates": 5,
        "digit_2_replacements": 1,
        "back_arrows": 5,
        "wordmarks": 1,
        "phrase_assets": 10,
        "underlines": 6,
        "boxes": 6,
        "line_components": 12,
    }
    if any(totals.get(key) != value for key, value in expected_totals.items()):
        raise RuntimeError("CEOKlaue analog UI asset inventory changed")
    return manifest


def ceoklaue_final_reselection_asset(asset_kind, asset_key, filename):
    ceoklaue_development_only()
    manifest = ceoklaue_final_reselection_manifest()
    allowed = {}
    for record in manifest["selection_groups"] + manifest["fixed_assets"]:
        record_kind = "glyph" if record["asset_key"] in {"lower_u", "cap_A", "comma", "2"} else "analog"
        for output in record["outputs"]:
            svg_path = output["svg"]["path"]
            allowed[(record_kind, record["asset_key"], os.path.basename(svg_path))] = os.path.join(
                PROJECT_DIR, "Branding", "CEOKlaue", os.path.dirname(svg_path)
            )
    root = allowed.get((asset_kind, asset_key, filename))
    if root is None:
        abort(404)
    response = send_from_directory(
        root,
        filename,
        mimetype="image/svg+xml",
        max_age=0,
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


def ceoklaue_final_reselection():
    ceoklaue_development_only()
    manifest = ceoklaue_final_reselection_manifest()
    selection_blocks = []
    candidate_map = {}
    labels = {
        "u": ("u", "Exakt drei neue Varianten in finaler Reihenfolge wählen."),
        "A": ("A", "Exakt drei neue Varianten in finaler Reihenfolge wählen."),
        ",": ("Komma", "Exakt drei kräftige neue Kommas in finaler Reihenfolge wählen."),
        "middle_dot": ("Mittelpunkt ·", "Ein bis drei echte Mittelpunkt-Varianten wählen."),
    }

    def asset_url(record, output):
        kind = "glyph" if record["asset_key"] in {"lower_u", "cap_A", "comma", "2"} else "analog"
        filename = os.path.basename(output["svg"]["path"])
        return (
            f"/dev/ceoklaue/analog-ui-asset/{kind}/"
            f"{quote(record['asset_key'], safe='')}/{quote(filename, safe='')}"
        )

    for record in manifest["selection_groups"]:
        selection_key = record["selection_key"]
        title, instructions = labels[selection_key]
        candidate_map[selection_key] = record["new_variant_ids"]
        cards = []
        for output in record["outputs"]:
            variant = output["id"]
            url = asset_url(record, output)
            cards.append(f"""
                <button class="glyph-variant" type="button"
                        data-character="{escape(selection_key, quote=True)}" data-variant="{variant}"
                        aria-pressed="false">
                    <span class="asset-canvas"><img src="{url}" alt="{escape(title)} Variante {variant}"></span>
                    <span class="glyph-variant-meta"><strong>{variant}</strong><span class="glyph-selected-label"></span></span>
                </button>""")
        minimum = record["required_selection"]["min"]
        maximum = record["required_selection"]["max"]
        range_label = f"{minimum}" if minimum == maximum else f"{minimum}–{maximum}"
        selection_blocks.append(f"""
        <article class="glyph-character selection-group" data-group="{escape(selection_key, quote=True)}"
                 data-kind="selection" data-selection-count="0" data-min="{minimum}" data-max="{maximum}">
            <div class="glyph-character-head">
                <div><h3>{escape(title)}</h3><p>{escape(instructions)}</p></div>
                <span class="glyph-status is-invalid">0/{range_label} ausgewählt · ungültig</span>
            </div>
            <p class="glyph-feedback" role="status" aria-live="polite"></p>
            <div class="glyph-variants">{"".join(cards)}</div>
        </article>""")

    fixed_titles = {
        "digit_2_replacement_alt1": "Replacement for 2 / Alternate 1",
        "back_arrow": "Final PO Back Arrow",
        "wordmark_sammlr": "Final PO Edding Wordmark",
        "phrase_aktueller_tausch": "Post-it phrase · Aktueller Tausch",
        "phrase_du_gibst_ab": "Post-it phrase · Du gibst ab",
        "phrase_mehr_ellipsis": "Post-it phrase · mehr… (source wording)",
        "phrase_auswahl_pruefen": "Post-it phrase · Auswahl prüfen",
        "underline": "Freihändige Unterstreichungen",
        "box": "Komplette handgezeichnete Kästchen",
        "line_component_vertical": "Einzelstrich-Baukasten · vertikal",
        "line_component_horizontal": "Einzelstrich-Baukasten · horizontal",
    }

    def inventory_block(record, section_class=""):
        inventory_key = record.get("inventory_key", record["asset_key"])
        cards = []
        for output in record["outputs"]:
            width, height = output["mask_dimensions"]
            url = asset_url(record, output)
            cards.append(f"""
            <figure class="inventory-card" data-asset-key="{escape(record['asset_key'], quote=True)}"
                    data-source-region="{escape(output['source_region_id'], quote=True)}">
                <span class="asset-canvas fixed-canvas"><img src="{url}" alt="{escape(record['asset_key'])} {output['id']}"></span>
                <figcaption><strong>{escape(record['asset_key'])}_{output['id']}</strong>
                    <span>Quelle: {escape(record['source'])}</span>
                    <span>Region: {escape(output['source_region_id'])} · Crop {escape(str(output['oriented_crop']))}</span>
                    <span>Dimension: {width} × {height} px</span>
                </figcaption>
            </figure>""")
        return f"""
        <article class="inventory-group {section_class}" data-inventory-group="{escape(inventory_key, quote=True)}">
            <h3>{escape(fixed_titles[inventory_key])}</h3>
            <div class="inventory-grid">{"".join(cards)}</div>
        </article>"""

    replacement = next(
        record for record in manifest["fixed_assets"]
        if record.get("inventory_key") == "digit_2_replacement_alt1"
    )
    selection_blocks.append(inventory_block(replacement, "replacement-preview"))
    fixed_blocks = [
        inventory_block(record)
        for record in manifest["fixed_assets"]
        if record.get("inventory_key") != "digit_2_replacement_alt1"
    ]

    html = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>CEOKlaue · Final Analog Asset Workbench</title>
<style>
:root { --ink:#171419; --muted:#69626b; --line:#d9d5dc; --selected:#12633f; --invalid:#9a2f2f; }
* { box-sizing:border-box; }
html,body { max-width:100%; overflow-x:hidden; }
body { margin:0; color:var(--ink); background:#f2f2f3; font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
button { font:inherit; }
.workbench { width:min(100%,1540px); margin:auto; padding:28px; }
.workbench-head { margin:0 0 28px; padding:18px 0 24px; border-bottom:1px solid var(--line); }
.workbench-head h1 { margin:0 0 5px; font-size:clamp(27px,5vw,42px); }
.workbench-head>p { margin:0; color:var(--muted); }
.workbench-section { margin:0 0 40px; }
.workbench-section>h2 { margin:0 0 5px; font-size:clamp(22px,4vw,32px); }
.section-intro { margin:0 0 20px; color:var(--muted); }
.export-box { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:9px; margin-top:18px; }
.export-box textarea { width:100%; min-height:78px; padding:10px; border:1px solid #c9c4cd; border-radius:8px; resize:vertical; background:#fff; font:13px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace; }
.export-box button { min-width:180px; padding:10px; border:0; border-radius:8px; color:#fff; background:#2d2531; font-weight:700; cursor:pointer; }
.export-box button:disabled { opacity:.48; cursor:not-allowed; }
.export-validity { grid-column:1/-1; margin:0; color:var(--invalid); font-size:13px; font-weight:700; }
.export-validity.is-valid { color:var(--selected); }
.glyph-character,.inventory-group { margin:0 0 22px; padding:16px; border:1px solid var(--line); border-radius:10px; background:#fff; }
.glyph-character-head { display:flex; align-items:center; justify-content:space-between; gap:14px; margin-bottom:8px; }
.glyph-character-head h3,.inventory-group h3 { margin:0 0 8px; font-size:22px; }
.glyph-character-head p { margin:0; color:var(--muted); font-size:13px; }
.glyph-status { padding:5px 9px; border-radius:999px; color:#5c5360; background:#ebe8ed; font-size:12px; font-weight:700; white-space:nowrap; }
.glyph-status.is-complete { color:#fff; background:var(--selected); }
.glyph-status.is-invalid { color:#fff; background:var(--invalid); }
.glyph-feedback { min-height:20px; margin:0 0 5px; color:#825329; font-size:12px; }
.glyph-variants { display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr)); gap:12px; }
.glyph-variant { width:100%; min-width:0; padding:8px; border:2px solid transparent; border-radius:9px; color:inherit; background:#f7f7f8; cursor:pointer; }
.glyph-variant:hover { border-color:#b7afbc; }
.glyph-variant.is-selected { border-color:var(--selected); box-shadow:0 0 0 2px rgba(18,99,63,.15); }
.asset-canvas { width:100%; min-height:180px; aspect-ratio:4/3; padding:20px; display:flex; align-items:center; justify-content:center; overflow:hidden; border:1px solid #e1dee4; background-color:#fff; background-image:linear-gradient(45deg,#f0eef2 25%,transparent 25%),linear-gradient(-45deg,#f0eef2 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#f0eef2 75%),linear-gradient(-45deg,transparent 75%,#f0eef2 75%); background-size:20px 20px; background-position:0 0,0 10px,10px -10px,-10px 0; }
.asset-canvas img { display:block; max-width:100%; max-height:100%; width:100%; height:100%; object-fit:contain; }
.glyph-variant-meta { min-height:46px; padding-top:7px; display:flex; align-items:center; justify-content:center; gap:8px; color:var(--muted); font-size:12px; text-transform:uppercase; }
.glyph-variant-meta strong { color:var(--ink); font:700 14px/1 ui-monospace,SFMono-Regular,Menlo,monospace; }
.glyph-selected-label { display:none; padding:3px 6px; border-radius:999px; color:#fff; background:var(--selected); }
.glyph-variant.is-selected .glyph-selected-label { display:inline; }
.inventory-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr)); gap:12px; }
.inventory-card { min-width:0; margin:0; padding:8px; border-radius:9px; background:#f7f7f8; }
.inventory-card figcaption { display:grid; gap:3px; padding:9px 3px 2px; overflow-wrap:anywhere; color:var(--muted); font-size:12px; }
.inventory-card figcaption strong { color:var(--ink); font:700 13px/1.3 ui-monospace,SFMono-Regular,Menlo,monospace; }
.replacement-preview { border-color:#9d90aa; }
@media(max-width:700px) {
    .workbench { padding:14px; }
    .export-box { grid-template-columns:1fr; }
    .export-box button { min-height:44px; }
    .glyph-character-head { align-items:flex-start; flex-direction:column; }
    .asset-canvas { min-height:150px; padding:16px; }
}
</style>
</head>
<body><main class="workbench">
<header class="workbench-head">
    <h1>CEOKlaue – Final Analog Asset Workbench</h1>
    <p>Ausschließlich der letzte Source-Drop: neue Reparaturzeichen und vollständiges Analog-UI-Inventar. Keine Produktintegration.</p>
    <div class="export-box"><textarea id="selectionSummary" readonly aria-label="Finale Analog-Auswahl"></textarea><button id="copySelection" type="button" disabled>Auswahl kopieren</button><p id="exportValidity" class="export-validity" role="status">Export ungültig: u, A und Komma benötigen exakt 3; Mittelpunkt benötigt 1–3 Auswahlen.</p></div>
</header>
<section class="workbench-section" data-section="po-selection">
    <h2>1 · PO-Auswahl</h2>
    <p class="section-intro">Nur neue Kandidaten dieses Drops. Die 2 ist ausschließlich eine Replacement-Preview.</p>
    __SELECTION_BLOCKS__
</section>
<section class="workbench-section" data-section="fixed-analog-assets">
    <h2>2 · Feste Analog-Assets</h2>
    <p class="section-intro">Quelleninventar ohne Auswahl: vollständig, transparent und unverändert in seinen natürlichen Proportionen.</p>
    __FIXED_BLOCKS__
</section>
</main>
<script>
(function(){
    const storageKey=__STORAGE_KEY__;
    const candidates=__CANDIDATES__;
    const exportOrder=['u','A',',','middle_dot'];
    const limits={u:[3,3],A:[3,3],',':[3,3],middle_dot:[1,3]};
    const slotSymbols=['①','②','③'];
    let stored=null;
    try{ stored=JSON.parse(localStorage.getItem(storageKey)||'null'); }catch(error){ stored=null; }
    const selection={};
    exportOrder.forEach(function(group){
        const candidate=stored && Array.isArray(stored[group])?stored[group]:[];
        const allowed=new Set(candidates[group]);
        selection[group]=Array.from(new Set(candidate)).filter(function(variant){return allowed.has(variant);}).slice(0,limits[group][1]);
    });

    function persist(){ localStorage.setItem(storageKey,JSON.stringify(selection)); }
    function render(){
        document.querySelectorAll('.glyph-variant').forEach(function(card){
            const selected=selection[card.dataset.character];
            const index=selected.indexOf(card.dataset.variant);
            card.classList.toggle('is-selected',index!==-1);
            card.setAttribute('aria-pressed',index!==-1?'true':'false');
            card.querySelector('.glyph-selected-label').textContent=index===-1?'':'SLOT '+slotSymbols[index];
        });
        let valid=true;
        document.querySelectorAll('.selection-group').forEach(function(block){
            const group=block.dataset.group;
            const count=selection[group].length;
            const min=Number(block.dataset.min);
            const max=Number(block.dataset.max);
            const complete=count>=min && count<=max;
            valid=valid&&complete;
            block.dataset.selectionCount=String(count);
            const status=block.querySelector('.glyph-status');
            const range=min===max?String(max):(min+'–'+max);
            status.textContent=count+'/'+range+' ausgewählt'+(complete?'':' · ungültig');
            status.classList.toggle('is-complete',complete);
            status.classList.toggle('is-invalid',!complete);
        });
        document.getElementById('selectionSummary').value=exportOrder.map(function(group){
            return group+'='+(selection[group].length?selection[group].join(','):'UNGÜLTIG');
        }).join('\\n');
        const validity=document.getElementById('exportValidity');
        validity.textContent=valid?'Export gültig.':'Export ungültig: u, A und Komma benötigen exakt 3; Mittelpunkt benötigt 1–3 Auswahlen.';
        validity.classList.toggle('is-valid',valid);
        document.getElementById('copySelection').disabled=!valid;
    }

    document.querySelectorAll('.glyph-variant').forEach(function(card){
        card.addEventListener('click',function(){
            const selected=selection[card.dataset.character];
            const limit=limits[card.dataset.character][1];
            const index=selected.indexOf(card.dataset.variant);
            const feedback=card.closest('.glyph-character').querySelector('.glyph-feedback');
            feedback.textContent='';
            if(index!==-1){ selected.splice(index,1); }
            else if(selected.length<limit){ selected.push(card.dataset.variant); }
            else { feedback.textContent='Alle verfügbaren Auswahl-Slots sind belegt. Erst eine Auswahl entfernen.'; return; }
            persist(); render();
        });
    });
    document.getElementById('copySelection').addEventListener('click',async function(){
        const textarea=document.getElementById('selectionSummary');
        try{ await navigator.clipboard.writeText(textarea.value); }catch(error){ textarea.focus(); textarea.select(); document.execCommand('copy'); }
        this.textContent='Kopiert';
    });
    persist();
    render();
})();
</script>
</body></html>"""
    html = html.replace("__SELECTION_BLOCKS__", "".join(selection_blocks))
    html = html.replace("__FIXED_BLOCKS__", "".join(fixed_blocks))
    html = html.replace("__STORAGE_KEY__", json.dumps(CEOKLAUE_ANALOG_UI_FINAL_STORAGE_KEY))
    html = html.replace("__CANDIDATES__", json.dumps(candidate_map, ensure_ascii=False))
    response = Response(html, mimetype="text/html")
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@lru_cache(maxsize=1)
def ceoklaue_final_fh_repair_manifest():
    with open(CEOKLAUE_FINAL_FH_REPAIR_MANIFEST, encoding="utf-8") as source:
        manifest = json.load(source)
    if manifest.get("version") != "CEOKlaue final F/H repair source import v1":
        raise RuntimeError("Unknown CEOKlaue final F/H repair manifest")
    records = manifest.get("characters", [])
    if [record.get("character") for record in records] != ["F", "H"]:
        raise RuntimeError("CEOKlaue final F/H repair scope changed")
    for record in records:
        expected = [f"{record['character']}{index:02d}" for index in range(1, 6)]
        if record.get("new_candidate_ids") != expected or len(record.get("outputs", [])) != 5:
            raise RuntimeError(f"CEOKlaue {record['character']} repair inventory changed")
    return manifest


def ceoklaue_final_fh_repair_asset(filename):
    ceoklaue_development_only()
    manifest = ceoklaue_final_fh_repair_manifest()
    allowed = {
        os.path.basename(output["svg"]["path"])
        for record in manifest["characters"]
        for output in record["outputs"]
    }
    if filename not in allowed:
        abort(404)
    response = send_from_directory(
        CEOKLAUE_FINAL_FH_REPAIR_VECTOR_DIR,
        filename,
        mimetype="image/svg+xml",
        max_age=0,
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


def ceoklaue_final_fh_repair():
    ceoklaue_development_only()
    manifest = ceoklaue_final_fh_repair_manifest()
    contexts = {
        "F": ("FIFA", "FIFA World Cup 2026", "FWC1", "FWC18"),
        "H": ("H", "HAI2", "HAI10", "GHA19", "GHA20"),
    }
    candidate_map = {}
    sections = []

    def candidate_context(text, character, url, candidate_id):
        pieces = []
        for letter in text:
            if letter == character:
                pieces.append(
                    f'<img class="context-repair-glyph" src="{url}" alt="{escape(candidate_id)}" '
                    f'data-preview-candidate="{escape(candidate_id, quote=True)}">'
                )
            elif letter == " ":
                pieces.append('<span class="context-space" aria-hidden="true"></span>')
            else:
                pieces.append(f'<span class="context-runtime-glyph">{escape(letter)}</span>')
        return (
            f'<div class="candidate-context" data-context="{escape(text, quote=True)}" '
            f'data-candidate="{escape(candidate_id, quote=True)}">'
            f'<span class="sr-only">{escape(text)} mit Kandidat {escape(candidate_id)}</span>'
            f'<span class="context-visual" aria-hidden="true">{"".join(pieces)}</span></div>'
        )

    for record in manifest["characters"]:
        character = record["character"]
        candidate_map[character] = record["new_candidate_ids"]
        cards = []
        for output in record["outputs"]:
            candidate_id = output["id"]
            filename = os.path.basename(output["svg"]["path"])
            url = f"/dev/ceoklaue/fh-repair-asset/{quote(filename, safe='')}"
            preview_rows = "".join(
                candidate_context(text, character, url, candidate_id)
                for text in contexts[character]
            )
            cards.append(f"""
            <button class="repair-candidate" type="button" data-character="{character}"
                    data-candidate="{candidate_id}" aria-pressed="false">
                <span class="candidate-head"><strong>{candidate_id}</strong><span class="selection-slot"></span></span>
                <span class="candidate-glyph"><img src="{url}" alt="{candidate_id} – neuer handgeschriebener Kandidat"></span>
                <span class="candidate-contexts">{preview_rows}</span>
            </button>""")
        sections.append(f"""
        <section id="repair-{character}" class="repair-group" data-selection-group="{character}" data-selection-count="0">
            <header><div><h2>{character} – neue Kandidaten</h2><p>Exakt drei auswählen; Klickreihenfolge bestimmt Platz 1, 2 und 3.</p></div>
            <strong class="group-status is-invalid">0/3 ausgewählt</strong></header>
            <p class="group-feedback" role="status" aria-live="polite"></p>
            <div class="candidate-grid">{"".join(cards)}</div>
        </section>""")

    html = """<!doctype html>
<html lang="de"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>CEOKlaue · F/H Final Repair</title>
<style>
@font-face{font-family:CEOKlaueContext;src:url('/static/fonts/ceoklaue-final-alt1.woff2') format('woff2');font-display:swap}
:root{--ink:#171419;--muted:#69626b;--line:#d8d4db;--selected:#12633f;--invalid:#9a2f2f}
*{box-sizing:border-box}body{margin:0;background:#f2f2f3;color:var(--ink);font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
button{font:inherit}.workbench{width:min(100%,1500px);margin:auto;padding:28px}.workbench-head{margin-bottom:28px;padding-bottom:22px;border-bottom:1px solid var(--line)}
h1{margin:0 0 7px;font-size:clamp(28px,5vw,42px)}.workbench-head p,.repair-group header p{margin:0;color:var(--muted)}
.export-box{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:9px;margin-top:18px}.export-box textarea{min-height:70px;padding:10px;border:1px solid #c9c4cd;border-radius:8px;background:#fff;font:14px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace;resize:none}
.export-box button{min-width:180px;padding:10px;border:0;border-radius:8px;background:#2d2531;color:#fff;font-weight:700;cursor:pointer}.export-box button:disabled{opacity:.48;cursor:not-allowed}.export-validity{grid-column:1/-1;margin:0;color:var(--invalid);font-size:13px;font-weight:700}.export-validity.is-valid{color:var(--selected)}
.repair-group{margin:0 0 28px;padding:18px;border:1px solid var(--line);border-radius:12px;background:#fff}.repair-group>header{display:flex;align-items:flex-start;justify-content:space-between;gap:16px}.repair-group h2{margin:0 0 4px;font-size:clamp(23px,4vw,32px)}
.group-status{padding:6px 10px;border-radius:999px;background:var(--invalid);color:#fff;font-size:12px;white-space:nowrap}.group-status.is-complete{background:var(--selected)}.group-feedback{min-height:20px;margin:4px 0;color:#825329;font-size:12px}
.candidate-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,250px),1fr));gap:12px}.repair-candidate{min-width:0;padding:10px;border:2px solid transparent;border-radius:10px;background:#f7f7f8;color:inherit;text-align:left;cursor:pointer}.repair-candidate:hover{border-color:#b7afbc}.repair-candidate.is-selected{border-color:var(--selected);box-shadow:0 0 0 2px rgba(18,99,63,.15)}
.candidate-head{display:flex;align-items:center;justify-content:space-between;min-height:30px}.candidate-head strong{font:700 16px/1 ui-monospace,SFMono-Regular,Menlo,monospace}.selection-slot{display:none;padding:4px 7px;border-radius:999px;background:var(--selected);color:#fff;font-size:11px;font-weight:700}.repair-candidate.is-selected .selection-slot{display:block}
.candidate-glyph{display:flex;align-items:center;justify-content:center;height:170px;padding:22px;border:1px solid #e1dee4;background:#fff}.candidate-glyph img{display:block;width:100%;height:100%;object-fit:contain}
.candidate-contexts{display:grid;gap:6px;padding-top:10px}.candidate-context{min-height:36px;padding:6px 8px;border:1px solid #e4e1e6;border-radius:6px;background:#fff;overflow:hidden}.context-visual{display:flex;align-items:baseline;height:23px;white-space:nowrap}.context-repair-glyph{display:inline-block;width:auto;height:23px;object-fit:contain;align-self:center}.context-runtime-glyph{font:22px/1 CEOKlaueContext,system-ui,sans-serif}.context-space{display:inline-block;width:7px}
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
@media(max-width:700px){.workbench{padding:14px}.export-box{grid-template-columns:1fr}.export-box button{min-height:44px}.repair-group>header{flex-direction:column}.candidate-glyph{height:150px}}
</style></head><body><main class="workbench">
<header class="workbench-head"><h1>CEOKlaue – F/H Final Repair</h1><p>Nur die zehn neu extrahierten echten F/H-Kandidaten. Keine Produktintegration und keine automatische Empfehlung.</p>
<div class="export-box"><textarea id="selectionSummary" readonly aria-label="F/H-Auswahl"></textarea><button id="copySelection" type="button" disabled>Auswahl kopieren</button><p id="exportValidity" class="export-validity" role="status">Export ungültig: F und H benötigen jeweils exakt drei Kandidaten.</p></div></header>
__SECTIONS__
</main><script>
(function(){
const storageKey=__STORAGE_KEY__;const candidates=__CANDIDATES__;const groups=['F','H'];const slotLabels=['PLATZ 1','PLATZ 2','PLATZ 3'];let stored=null;
try{stored=JSON.parse(localStorage.getItem(storageKey)||'null')}catch(error){stored=null}
const selection={};groups.forEach(function(group){const allowed=new Set(candidates[group]);const values=stored&&Array.isArray(stored[group])?stored[group]:[];selection[group]=Array.from(new Set(values)).filter(function(value){return allowed.has(value)}).slice(0,3)});
function persist(){localStorage.setItem(storageKey,JSON.stringify(selection))}
function render(){let valid=true;document.querySelectorAll('.repair-candidate').forEach(function(card){const selected=selection[card.dataset.character];const index=selected.indexOf(card.dataset.candidate);card.classList.toggle('is-selected',index!==-1);card.setAttribute('aria-pressed',index!==-1?'true':'false');card.querySelector('.selection-slot').textContent=index===-1?'':slotLabels[index]});
groups.forEach(function(group){const section=document.querySelector('[data-selection-group="'+group+'"]');const count=selection[group].length;const complete=count===3;valid=valid&&complete;section.dataset.selectionCount=String(count);const status=section.querySelector('.group-status');status.textContent=count+'/3 ausgewählt'+(complete?'':' · ungültig');status.classList.toggle('is-complete',complete);status.classList.toggle('is-invalid',!complete)});
document.getElementById('selectionSummary').value=groups.map(function(group){return group+'='+(selection[group].length===3?selection[group].join(','):'UNGÜLTIG')}).join('\\n');const validity=document.getElementById('exportValidity');validity.textContent=valid?'Export gültig.':'Export ungültig: F und H benötigen jeweils exakt drei Kandidaten.';validity.classList.toggle('is-valid',valid);document.getElementById('copySelection').disabled=!valid}
document.querySelectorAll('.repair-candidate').forEach(function(card){card.addEventListener('click',function(){const selected=selection[card.dataset.character];const index=selected.indexOf(card.dataset.candidate);const feedback=card.closest('.repair-group').querySelector('.group-feedback');feedback.textContent='';if(index!==-1){selected.splice(index,1)}else if(selected.length<3){selected.push(card.dataset.candidate)}else{feedback.textContent='Drei Plätze sind belegt. Erst einen Kandidaten abwählen.';return}persist();render()})});
document.getElementById('copySelection').addEventListener('click',async function(){const textarea=document.getElementById('selectionSummary');try{await navigator.clipboard.writeText(textarea.value)}catch(error){textarea.focus();textarea.select();document.execCommand('copy')}this.textContent='Kopiert'});persist();render();
})();</script></body></html>"""
    html = html.replace("__SECTIONS__", "".join(sections))
    html = html.replace("__STORAGE_KEY__", json.dumps(CEOKLAUE_FINAL_FH_REPAIR_STORAGE_KEY))
    html = html.replace("__CANDIDATES__", json.dumps(candidate_map))
    response = Response(html, mimetype="text/html")
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


def ceoklaue_control_page():
    ceoklaue_development_only()
    runtime = ceoklaue_runtime_manifest()
    master = runtime["master"]["characters_manifest"]
    mappings = {
        record["character"]: [alternate["variant"] for alternate in record["alternates"]]
        for record in master
    }
    if mappings.get("F") != ["05", "02", "01"] or mappings.get("H") != ["01", "04", "05"]:
        raise RuntimeError("Final F/H control-page mapping is not binding")

    rows = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "abcdefghijklmnopqrstuvwxyz",
        "0123456789",
        "äöü ÄÖÜ ß",
        ". , : ; ! ? - + / & % ( )",
    )
    sample_sentence = "Franz holt zwölf große Sticker; Hannah prüft Größe, Abstand & Wirkung."
    alternate_sections = []
    for alternate in (1, 2, 3):
        lines = "".join(f'<p class="charset-line">{escape(row)}</p>' for row in rows)
        alternate_sections.append(f"""
        <article class="alternate-card" data-alternate="{alternate}">
          <h2>ALT {alternate}</h2><div class="font-alt-{alternate}">{lines}<p class="spacing-line">{escape(sample_sentence)}</p></div>
        </article>""")

    examples = (
        "FIFA World Cup 2026",
        "FWC1, FWC18, FWC26",
        "HAI2, HAI10, GHA19",
        "660 gesammelt · 332 fehlend · 108 doppelt",
        "Fehlende Sticker",
        "Doppelte Sticker",
        "Aktueller Tausch",
        "2 erhalten · 3 abgegeben",
        "Frische Fische hüpfen heute höher; zwölf größere Päckchen bleiben übrig.",
        "FWC1, FWC18, FWC26, HAI2, HAI10, GHA19, FWC1, HAI2, GHA20",
    )
    example_rows = "".join(
        f'<p class="mixed-example" data-example="{escape(text, quote=True)}">'
        f'{ceoklaue_runtime_run(text, f"ceoklaue-control-example-{index}")}</p>'
        for index, text in enumerate(examples)
    )
    action_examples = "".join(
        f'<button type="button" class="control-bracket-button">'
        f'{ceoklaue_bracket_button_content(label, "ceoklaue-control-actions", action, position)}</button>'
        for position, (label, action) in enumerate(
            (("Auswahl prüfen", "review"), ("Bearbeiten", "edit"), ("Bestätigen", "confirm"))
        )
    )

    pair_examples = "".join(
        f'<article class="pair-example" data-pair="{pair_id}"><h3>Pair {pair_id}</h3>'
        f'<button type="button" class="control-bracket-button">'
        f'{ceoklaue_bracket_button_content("Auswahl prüfen", "ceoklaue-control-pair", "explicit", int(pair_id), pair_id)}</button></article>'
        for pair_id in ("01", "02", "03", "04", "05")
    )
    mixed_buttons = []
    seen_pairs = set()
    mixed_labels = ("Auswahl prüfen", "Bearbeiten", "Bestätigen", "Leeren", "Weiter", "Zurück")
    for position in range(100):
        label = mixed_labels[position % len(mixed_labels)]
        context = f"ceoklaue-control-mixed-{position}"
        action = f"action-{position}"
        pair = ceoklaue_button_bracket_pair(context, action, label, position)
        if pair["id"] in seen_pairs:
            continue
        seen_pairs.add(pair["id"])
        mixed_buttons.append(
            f'<button type="button" class="control-bracket-button" data-mixed-pair="{pair["id"]}">'
            f'{ceoklaue_bracket_button_content(label, context, action, position)}</button>'
        )
        if len(seen_pairs) == 5:
            break
    if seen_pairs != {"01", "02", "03", "04", "05"}:
        raise RuntimeError("Deterministic bracket examples did not cover all five pairs")

    concept_button = ceoklaue_bracket_button_content(
        "Auswahl prüfen", "ceoklaue-control-milkglass", "review", 0
    )
    html = f"""<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">
<title>CEOKlaue · Final Control Page</title><style>
@font-face{{font-family:CEOKlaueAlt1;src:url('/static/fonts/ceoklaue-final-alt1.woff2') format('woff2')}}
@font-face{{font-family:CEOKlaueAlt2;src:url('/static/fonts/ceoklaue-final-alt2.woff2') format('woff2')}}
@font-face{{font-family:CEOKlaueAlt3;src:url('/static/fonts/ceoklaue-final-alt3.woff2') format('woff2')}}
:root{{--ink:#211d22;--purple:#7c3aed;--paper:#f5f3ed;--line:#d8d2dd}}*{{box-sizing:border-box}}body{{margin:0;background:#efedf1;color:var(--ink);font:15px/1.45 system-ui,sans-serif}}main{{width:min(1500px,100%);margin:auto;padding:28px}}header{{margin-bottom:28px}}h1{{margin:0;font-size:clamp(30px,5vw,48px)}}header p{{color:#68606b}}.alternate-grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}}.alternate-card,.control-section{{margin-bottom:22px;padding:18px;border:1px solid var(--line);border-radius:12px;background:#fff}}.alternate-card h2,.control-section h2{{margin:0 0 12px;color:var(--purple)}}.font-alt-1{{font-family:CEOKlaueAlt1}}.font-alt-2{{font-family:CEOKlaueAlt2}}.font-alt-3{{font-family:CEOKlaueAlt3}}.charset-line{{margin:5px 0;font-size:clamp(21px,2.1vw,31px);overflow-wrap:anywhere}}.spacing-line{{margin:16px 0 0;font-size:23px}}.mixed-example,.action-examples{{font-size:27px;margin:9px 0}}.ceoklaue-alt-1{{font-family:CEOKlaueAlt1}}.ceoklaue-alt-2{{font-family:CEOKlaueAlt2}}.ceoklaue-alt-3{{font-family:CEOKlaueAlt3}}.ceoklaue-space{{display:inline}}.pair-grid,.mixed-buttons{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}}.pair-example{{padding:12px;background:#f7f5f8;border-radius:8px}}.pair-example h3{{margin:0 0 8px}}.control-bracket-button{{border:0;padding:5px;background:transparent;color:var(--ink);font:25px/1 CEOKlaueAlt1;cursor:pointer}}.analog-bracket-content{{display:inline-flex;align-items:center;justify-content:center;gap:8px;max-width:100%}}.analog-bracket{{display:block;width:auto;height:1.55em;max-width:24px;object-fit:contain}}.analog-bracket-label{{display:inline-flex;white-space:nowrap}}.concept-stage{{position:relative;min-height:430px;overflow:hidden;border-radius:14px;background:linear-gradient(rgba(108,93,119,.18) 1px,transparent 1px),linear-gradient(90deg,rgba(108,93,119,.18) 1px,transparent 1px),var(--paper);background-size:24px 24px}}.concept-glass{{position:relative;z-index:3;height:94px;border-bottom:1px solid rgba(255,255,255,.9);background:rgba(255,255,255,.68);backdrop-filter:blur(12px) saturate(.9);box-shadow:0 5px 18px rgba(42,32,52,.12)}}.concept-codes{{position:absolute;inset:112px 22px 20px;font:27px/1.8 CEOKlaueAlt1;color:#211d22;word-spacing:13px}}.concept-postit{{position:absolute;z-index:4;left:50%;top:65px;width:min(280px,calc(100% - 36px));padding:20px 22px;transform:translateX(-50%) rotate(-1.1deg);background:rgba(245,221,98,.95);box-shadow:0 11px 25px rgba(40,28,23,.17);font:22px/1.35 CEOKlaueAlt1;color:var(--ink)}}.concept-postit h3,.concept-postit p{{margin:0 0 12px}}.concept-postit .control-bracket-button{{font-size:22px}}.concept-note{{margin-top:12px;color:#68606b}}@media(max-width:900px){{.alternate-grid{{grid-template-columns:1fr}}main{{padding:14px}}}}
</style></head><body><main data-control-page="final">
<header><h1>CEOKlaue – vollständige Kontrollseite</h1><p>Finale Runtime-Alternates, F/H, Satzzeichen, echte Button-Klammern und isolierter Development-Konzeptpreview.</p></header>
<section class="alternate-grid" id="control-alternates" aria-label="Alle drei Runtime-Alternates">{"".join(alternate_sections)}</section>
<section class="control-section" id="control-examples" data-section="realistic-examples"><h2>Beispielanwendungen · deterministic alternate mixing</h2>{example_rows}<div class="action-examples">{action_examples}</div></section>
<section class="control-section" id="control-brackets" data-section="bracket-pairs"><h2>Alle fünf echten Klammerpaare</h2><div class="pair-grid">{pair_examples}</div></section>
<section class="control-section" data-section="mixed-brackets"><h2>Deterministic mixed button examples</h2><div class="mixed-buttons">{"".join(mixed_buttons)}</div></section>
<section class="control-section" id="control-milkglass" data-section="milkglass-postit-preview"><h2>Milkglass/Post-it Concept Preview · Development only</h2><div class="concept-stage"><div class="concept-glass"></div><div class="concept-codes">FWC1 FWC18 HAI2 GHA19 FWC26 HAI10 GHA20 FWC5 FWC8 HAI4</div><article class="concept-postit"><h3>Aktueller Tausch</h3><p>2 erhalten · 3 abgegeben</p><button type="button" class="control-bracket-button">{concept_button}</button></article></div><p class="concept-note">Papierfläche 95 % opak; Text und echte Klammern 100 % opak. Kein produktiver Flow.</p></section>
</main></body></html>"""
    response = Response(html, mimetype="text/html")
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


def ceoklaue_preview_font():
    ceoklaue_development_only()
    response = send_from_directory(
        CEOKLAUE_PREVIEW_DIR,
        CEOKLAUE_PREVIEW_FONT,
        mimetype="font/woff2",
        max_age=0,
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@lru_cache(maxsize=1)
def ceoklaue_harmony_manifest():
    with open(CEOKLAUE_HARMONY_MANIFEST, encoding="utf-8") as source:
        manifest = json.load(source)
    if manifest.get("selected_characters") != 82 or manifest.get("selected_glyphs") != 246:
        raise RuntimeError("CEOKlaue Harmony manifest has an invalid selection inventory")
    if len(manifest.get("characters", [])) != 82:
        raise RuntimeError("CEOKlaue Harmony manifest must contain exactly 82 characters")
    for record in manifest["characters"]:
        if len(record.get("alternates", [])) != 3:
            raise RuntimeError(
                f"CEOKlaue Harmony character {record.get('character')} has no exact triple"
            )
    markers = manifest.get("selection_markers", {})
    if markers.get("selected_markers") != 10:
        raise RuntimeError("CEOKlaue Harmony manifest must contain ten final markers")
    if markers.get("normalization", {}).get("rotation_degrees") != -90:
        raise RuntimeError("CEOKlaue Harmony markers must all be rotated 90 degrees left")
    return manifest


def ceoklaue_harmony_asset(glyph_key, filename):
    ceoklaue_development_only()
    manifest = ceoklaue_harmony_manifest()
    allowed = {
        (record["glyph_key"], os.path.basename(alternate["asset"]))
        for record in manifest["characters"]
        for alternate in record["alternates"]
    }
    if (glyph_key, filename) not in allowed:
        abort(404)
    response = send_from_directory(
        os.path.join(CEOKLAUE_HARMONY_DIR, "glyphs", glyph_key),
        filename,
        mimetype="image/svg+xml",
        max_age=0,
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


def ceoklaue_harmony_marker_asset(family, filename):
    ceoklaue_development_only()
    manifest = ceoklaue_harmony_manifest()
    allowed = {
        (record["family"], os.path.basename(variant["asset"]))
        for record in manifest["selection_markers"]["families"]
        for variant in record["variants"]
    }
    if (family, filename) not in allowed:
        abort(404)
    response = send_from_directory(
        os.path.join(CEOKLAUE_HARMONY_DIR, "selection_marks", family),
        filename,
        mimetype="image/svg+xml",
        max_age=0,
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


def ceoklaue_harmony_mix_index(character, position, line_seed, seed):
    payload = f"{seed}\0{line_seed}\0{position}\0{character}".encode("utf-8")
    return int.from_bytes(hashlib.blake2s(payload, digest_size=4).digest(), "big") % 3


@lru_cache(maxsize=1)
def ceoklaue_runtime_manifest():
    with open(CEOKLAUE_RUNTIME_MANIFEST, encoding="utf-8") as source:
        manifest = json.load(source)
    master = manifest.get("master", {})
    runtime = manifest.get("runtime", {})
    if master.get("characters") != 82 or master.get("selected_glyphs") != 246:
        raise RuntimeError("CEOKlaue runtime master must contain exactly 82x3 glyphs")
    if len(runtime.get("assets", [])) != 3:
        raise RuntimeError("CEOKlaue runtime must contain exactly three bundled fonts")
    markers = manifest.get("selection_markers", {})
    if markers.get("selected_markers") != 10 or markers.get("rotation_degrees") != -90:
        raise RuntimeError("CEOKlaue runtime must contain ten final -90 degree markers")
    wordmark = manifest.get("header_wordmark", {})
    if (
        wordmark.get("text") != "sammlr."
        or wordmark.get("source_mode") != "single-connected-image"
        or not wordmark.get("connected_wordmark_preserved")
        or wordmark.get("letter_color") != "#211d22"
        or wordmark.get("period_color") != "#7C3AED"
    ):
        raise RuntimeError("CEOKlaue runtime has an invalid final header wordmark")
    return manifest


def ceoklaue_runtime_mix_index(
    text, character, position, context_seed, previous_character_index=None
):
    payload = (
        f"{CEOKLAUE_RUNTIME_MIXING_SEED}\0{context_seed}\0"
        f"{text}\0{position}\0{character}"
    )
    value = 2166136261
    for codepoint in payload:
        value ^= ord(codepoint)
        value = (value * 16777619) & 0xFFFFFFFF
    alternate = value % 3
    if previous_character_index is not None and alternate == previous_character_index:
        alternate = (alternate + 1 + ((value >> 8) & 1)) % 3
    return alternate


def ceoklaue_runtime_mix_sequence(text, context_seed):
    previous_alternates = {}
    sequence = []
    for position, character in enumerate(text):
        alternate = ceoklaue_runtime_mix_index(
            text,
            character,
            position,
            context_seed,
            previous_alternates.get(character),
        )
        previous_alternates[character] = alternate
        sequence.append(alternate)
    return sequence


def ceoklaue_runtime_run(text, context_seed):
    manifest = ceoklaue_runtime_manifest()
    supported = {
        record["character"] for record in manifest["master"]["characters_manifest"]
    }
    glyphs = []
    alternates = ceoklaue_runtime_mix_sequence(text, context_seed)
    for position, character in enumerate(text):
        if character == " ":
            glyphs.append('<span class="ceoklaue-space" aria-hidden="true"> </span>')
            continue
        if character not in supported:
            glyphs.append(
                f'<span class="ceoklaue-fallback" aria-hidden="true">{escape(character)}</span>'
            )
            continue
        alternate = alternates[position] + 1
        glyphs.append(
            f'<span class="ceoklaue-glyph ceoklaue-alt-{alternate}" '
            f'aria-hidden="true" data-character="{escape(character, quote=True)}" '
            f'data-alternate="{alternate}">{escape(character)}</span>'
        )
    return (
        f'<span class="ceoklaue-run" aria-label="{escape(text, quote=True)}" '
        f'data-ceoklaue-context="{escape(context_seed, quote=True)}">'
        f'{"".join(glyphs)}</span>'
    )


def ceoklaue_marker_mix_index(family, code, instance, context_seed):
    payload = (
        f"{CEOKLAUE_MARKER_MIXING_SEED}\0{context_seed}\0"
        f"{family}\0{code}\0{instance}"
    )
    value = 2166136261
    for codepoint in payload:
        value ^= ord(codepoint)
        value = (value * 16777619) & 0xFFFFFFFF
    return value % 5


def ceoklaue_marker_asset(family, code, instance, context_seed):
    markers = ceoklaue_runtime_manifest()["selection_markers"]
    record = next(
        (item for item in markers["families"] if item["family"] == family),
        None,
    )
    if record is None or len(record.get("variants", [])) != 5:
        raise RuntimeError(f"Unknown final CEOKlaue marker family: {family}")
    selected = record["variants"][
        ceoklaue_marker_mix_index(family, code, instance, context_seed)
    ]
    static_path = selected["runtime_asset"].removeprefix("App/static/")
    return {
        "variant": selected["variant"],
        "url": f"/static/{static_path}",
    }


@lru_cache(maxsize=1)
def ceoklaue_button_bracket_manifest():
    with open(CEOKLAUE_BUTTON_BRACKET_MANIFEST, encoding="utf-8") as source:
        manifest = json.load(source)
    if manifest.get("version") != "CEOKlaue button bracket source import v1":
        raise RuntimeError("Unknown CEOKlaue button-bracket manifest")
    pairs = manifest.get("pairs", [])
    if [pair.get("id") for pair in pairs] != [f"{index:02d}" for index in range(1, 6)]:
        raise RuntimeError("CEOKlaue button-bracket inventory must contain five pairs")
    for pair in pairs:
        pair_id = pair["id"]
        for side in ("left", "right"):
            expected = f"button_bracket_{pair_id}_{side}.svg"
            if os.path.basename(pair[side]["runtime_svg"]["path"]) != expected:
                raise RuntimeError(f"CEOKlaue button-bracket pair {pair_id} is mismatched")
    return manifest


def ceoklaue_button_bracket_mix_index(context, action, label, position=0):
    payload = (
        f"{CEOKLAUE_BUTTON_BRACKET_MIXING_SEED}\0{context}\0"
        f"{action}\0{label}\0{position}"
    )
    value = 2166136261
    for codepoint in payload:
        value ^= ord(codepoint)
        value = (value * 16777619) & 0xFFFFFFFF
    return value % 5


def ceoklaue_button_bracket_pair(context, action, label, position=0, pair_id=None):
    pairs = ceoklaue_button_bracket_manifest()["pairs"]
    if pair_id is None:
        pair = pairs[ceoklaue_button_bracket_mix_index(context, action, label, position)]
    else:
        pair = next((item for item in pairs if item["id"] == pair_id), None)
        if pair is None:
            raise RuntimeError(f"Unknown CEOKlaue button-bracket pair: {pair_id}")
    result = {"id": pair["id"]}
    for side in ("left", "right"):
        static_path = pair[side]["runtime_svg"]["path"].removeprefix("App/static/")
        result[side] = f"/static/{static_path}"
    return result


def ceoklaue_bracket_button_content(label, context, action, position=0, pair_id=None):
    pair = ceoklaue_button_bracket_pair(context, action, label, position, pair_id)
    ink = ceoklaue_runtime_run(label, f"{context}-{action}-{position}")
    return (
        f'<span class="analog-bracket-content" data-bracket-pair="{pair["id"]}">'
        f'<img class="analog-bracket analog-bracket-left" src="{pair["left"]}" alt="">'
        f'<span class="analog-bracket-label">{ink}</span>'
        f'<img class="analog-bracket analog-bracket-right" src="{pair["right"]}" alt="">'
        f'</span>'
    )


def ceoklaue_harmony_run(text, mode, line_seed, records, mixing_seed):
    glyphs = []
    for position, character in enumerate(text):
        if character == " ":
            glyphs.append('<span class="h-space" aria-hidden="true"></span>')
            continue
        if character == "·":
            glyphs.append('<span class="h-separator" aria-hidden="true">·</span>')
            continue
        if character not in records:
            raise RuntimeError(f"Unsupported Harmony sample character: {character!r}")
        alternate_index = (
            mode - 1 if isinstance(mode, int)
            else ceoklaue_harmony_mix_index(character, position, line_seed, mixing_seed)
        )
        record = records[character]
        alternate = record["alternates"][alternate_index]
        filename = os.path.basename(alternate["asset"])
        url = (
            "/dev/ceoklaue-harmony/glyph/"
            f"{quote(record['glyph_key'], safe='')}/{quote(filename, safe='')}"
        )
        glyphs.append(
            f'<img class="h-glyph" src="{url}" alt="" aria-hidden="true" '
            f'data-character="{escape(character, quote=True)}" '
            f'data-alternate="{alternate_index + 1}" '
            f'data-variant="{alternate["variant"]}">'
        )
    return (
        f'<span class="hand-run" role="img" aria-label="{escape(text, quote=True)}" '
        f'data-line-seed="{escape(line_seed, quote=True)}">{"".join(glyphs)}</span>'
    )


def ceoklaue_harmony():
    ceoklaue_development_only()
    manifest = ceoklaue_harmony_manifest()
    records = {record["character"]: record for record in manifest["characters"]}
    mixing_seed = manifest["mixing"]["seed"]
    rows = manifest["character_rows"]

    alphabet_cards = []
    for alternate in (1, 2, 3):
        lines = "".join(
            f'<div class="alphabet-row">{ceoklaue_harmony_run(row, alternate, f"alphabet-{alternate}-{index}", records, mixing_seed)}</div>'
            for index, row in enumerate(rows)
        )
        alphabet_cards.append(
            f'<section class="paper-card alphabet-card" data-section="alphabet-{alternate}" '
            f'data-fixed-alternate="{alternate}"><p class="eyebrow">Vollständiges Set</p>'
            f'<h2>Alphabet {alternate:02d}</h2>{lines}</section>'
        )

    mixed_lines = "".join(
        f'<div class="alphabet-row">{ceoklaue_harmony_run(row, "mixed", f"mixed-alphabet-{index}", records, mixing_seed)}</div>'
        for index, row in enumerate(rows)
    )
    mixed_card = (
        '<section class="paper-card alphabet-card mixed-card" data-section="mixed">'
        '<p class="eyebrow">Deterministisch durchmischt</p><h2>Gemischt</h2>'
        f'{mixed_lines}</section>'
    )

    word_samples = (
        "Sammlr.", "FIFA World Cup 2026", "Fehlende Sticker",
        "Doppelte Sticker", "Aktueller Tausch", "Du bekommst:",
        "Du gibst ab:", "Sticker suchen", "Zurück zum Album",
        "650 gesammelt", "342 fehlend", "110 doppelt",
        "3 erhalten · 2 abgegeben",
    )
    words = "".join(
        f'<div class="word-sample">{ceoklaue_harmony_run(sample, "mixed", f"word-{index}-{sample}", records, mixing_seed)}</div>'
        for index, sample in enumerate(word_samples)
    )
    word_card = (
        '<section class="paper-card word-card" data-section="words">'
        '<p class="eyebrow">Im Sammlr-Kontext</p><h2>Wortproben</h2>'
        f'<div class="word-list">{words}</div></section>'
    )

    code_groups = (
        ("Deutschland", ("GER13", "GER14", "GER15", "GER16", "GER17")),
        ("Brasilien", ("BRA9", "BRA11", "BRA14", "BRA15", "BRA18", "BRA19", "BRA20")),
        ("Marokko", ("MAR5", "MAR8", "MAR9", "MAR12", "MAR14", "MAR15", "MAR18", "MAR20")),
        ("Mexiko", ("MEX10", "MEX12")),
        ("USA", ("USA5", "USA6", "USA7", "USA9", "USA10", "USA11", "USA14", "USA15")),
        ("VFL", ("VFL149",)),
    )
    code_sections = []
    for group_index, (label, codes) in enumerate(code_groups):
        tokens = "".join(
            f'<span class="code-token">{ceoklaue_harmony_run(code, "mixed", f"code-{group_index}-{index}-{code}", records, mixing_seed)}</span>'
            for index, code in enumerate(codes)
        )
        code_sections.append(
            f'<div class="code-group"><h3>{escape(label)}</h3><div class="code-cloud">{tokens}</div></div>'
        )
    mar_rows = (
        "MAR1 MAR2 MAR3 MAR4 MAR5 MAR6 MAR7 MAR8 MAR9 MAR10",
        "MAR11 MAR12 MAR13 MAR14 MAR15 MAR16 MAR17 MAR18 MAR19 MAR20",
    )
    mar_series = "".join(
        f'<div class="mar-row">{ceoklaue_harmony_run(row, "mixed", f"mar-series-{index}", records, mixing_seed)}</div>'
        for index, row in enumerate(mar_rows)
    )
    code_card = (
        '<section class="paper-card code-card" data-section="codes">'
        '<p class="eyebrow">Wiederholung ohne Stempelgefühl</p><h2>Sticker-Codes</h2>'
        f'<div class="code-groups">{"".join(code_sections)}</div>'
        '<div class="mar-series"><h3>MAR 01–20</h3>'
        f'{mar_series}</div></section>'
    )

    marker_families = {
        record["family"]: record
        for record in manifest["selection_markers"]["families"]
    }

    def harmony_marker_url(family, variant):
        filename = os.path.basename(variant["asset"])
        return (
            f"/dev/ceoklaue-harmony/marker/{quote(family, safe='')}/"
            f"{quote(filename, safe='')}"
        )

    marker_cards = []
    for family, heading in (
        ("receive_circle", "Receive Marker"),
        ("give_cross", "Give Marker"),
    ):
        samples = "".join(
            f'<figure class="marker-sample" data-family="{family}" '
            f'data-variant="{variant["variant"]}" data-rotation-degrees="-90">'
            f'<img src="{harmony_marker_url(family, variant)}" alt="">'
            f'<figcaption>{escape(family)} · {variant["variant"]}</figcaption></figure>'
            for variant in marker_families[family]["variants"]
        )
        marker_cards.append(
            f'<section class="paper-card marker-card" data-section="{family.replace("_", "-")}">'
            f'<p class="eyebrow">Final · exakt 90° counterclockwise</p><h2>{heading}</h2>'
            f'<div class="marker-gallery">{samples}</div></section>'
        )

    context_specs = (
        ("GER13", None),
        ("BRA11", "receive_circle"),
        ("MAR5", "give_cross"),
        ("USA10", "receive_circle"),
        ("MEX12", "give_cross"),
        ("MAR20", None),
    )
    context_tokens = []
    for position, (code, family) in enumerate(context_specs):
        marker_html = ""
        family_attr = "none"
        variant_attr = ""
        if family:
            family_attr = family
            variants = marker_families[family]["variants"]
            variant = variants[
                ceoklaue_marker_mix_index(
                    family, code, 1, "harmony-marker-context"
                )
            ]
            variant_attr = f' data-marker-variant="{variant["variant"]}"'
            marker_html = (
                f'<img class="context-marker" src="{harmony_marker_url(family, variant)}" '
                f'alt="" aria-hidden="true">'
            )
        context_tokens.append(
            f'<span class="marker-context-token" data-marker-family="{family_attr}"{variant_attr}>'
            f'{ceoklaue_harmony_run(code, "mixed", f"marker-context-{position}-{code}", records, mixing_seed)}'
            f'{marker_html}</span>'
        )
    marker_context_card = (
        '<section class="paper-card marker-context-card" data-section="marker-context">'
        '<p class="eyebrow">Finale Größe und Lesbarkeit</p><h2>Marker im Kontext</h2>'
        f'<div class="marker-context-row">{"".join(context_tokens)}</div></section>'
    )
    final_ui_card = '''<section class="paper-card final-ui-card" data-section="final-ui-assets">
      <p class="eyebrow">Finale Produktbausteine</p><h2>Analog UI Lock</h2>
      <div class="final-ui-assets"><figure><img src="/static/ceoklaue-wordmark.svg" alt="sammlr."><figcaption>Original connected wordmark · IMG_7186</figcaption></figure><figure><img src="/static/ceoklaue-ui/back-arrow.svg" alt=""><figcaption>Gewählter echter Pfeil · 03</figcaption></figure></div>
      <div class="final-dot-row"><img src="/static/ceoklaue-ui/middle-dot-01.svg" alt=""><img src="/static/ceoklaue-ui/middle-dot-02.svg" alt=""><img src="/static/ceoklaue-ui/middle-dot-04.svg" alt=""></div>
      <div class="final-postit-row"><div class="final-postit yellow">Aktueller Tausch</div><div class="final-postit green">Du bekommst</div><div class="final-postit pink">Du gibst ab</div></div>
      <div class="final-line-assets"><img src="/static/ceoklaue-ui/underline.svg" alt="Echte Unterstreichung"><img src="/static/ceoklaue-ui/box.svg" alt="Echtes Kästchen"></div>
    </section>'''

    html = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>CEOKlaue · Final Style Harmony</title>
<style>
:root {
    --surround: #dedbe1;
    --paper: #f5f3ed;
    --paper-edge: #d7d2c8;
    --grid: rgba(105, 91, 115, .19);
    --ink: #211d22;
    --muted: #6a636c;
    --accent: #654873;
    --grid-size: 22px;
}
* { box-sizing: border-box; }
html, body { min-width: 0; }
body {
    margin: 0;
    color: var(--ink);
    background: var(--surround);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.harmony-shell { width: min(100% - 24px, 1180px); margin: 0 auto; padding: 30px 0 64px; }
.harmony-head { max-width: 760px; margin: 0 0 28px; padding: 0 8px; }
.harmony-head .kicker, .eyebrow {
    margin: 0 0 7px; color: var(--accent); font-size: 11px; font-weight: 800;
    letter-spacing: .12em; text-transform: uppercase;
}
.harmony-head h1 { margin: 0 0 10px; font-size: clamp(30px, 5vw, 54px); line-height: 1; letter-spacing: -.035em; }
.harmony-head p:last-child { margin: 0; color: var(--muted); font-size: 14px; line-height: 1.55; }
.paper-stack { display: grid; gap: clamp(18px, 3vw, 34px); }
.paper-card {
    position: relative; isolation: isolate; min-width: 0; overflow: hidden;
    padding: clamp(24px, 5vw, 58px);
    border: 1px solid var(--paper-edge); border-radius: 3px;
    background-color: var(--paper);
    background-image:
        linear-gradient(to right, var(--grid) 1px, transparent 1px),
        linear-gradient(to bottom, var(--grid) 1px, transparent 1px);
    background-size: var(--grid-size) var(--grid-size);
    box-shadow: 0 12px 30px rgba(46, 39, 49, .10);
}
.paper-card::after {
    content: ""; position: absolute; z-index: -1; inset: 0; pointer-events: none;
    background: linear-gradient(118deg, rgba(255,255,255,.18), transparent 42%, rgba(80,65,77,.025));
}
.paper-card h2 { margin: 0 0 24px; color: var(--accent); font-size: clamp(22px, 4vw, 34px); line-height: 1.05; }
.alphabet-row { min-width: 0; margin: 0 0 10px; font-size: clamp(29px, 5.1vw, 54px); line-height: 1.32; }
.hand-run { min-width: 0; }
.h-glyph { display: inline-block; width: auto; height: 1em; vertical-align: -.23em; }
.h-space { display: inline-block; width: .34em; height: 1em; }
.h-separator {
    display: inline-block; width: .42em; color: var(--ink); text-align: center;
    font: 700 .62em/1 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    vertical-align: .12em;
}
.word-list { display: grid; gap: 16px; }
.word-sample { min-width: 0; font-size: clamp(32px, 6vw, 66px); line-height: 1.25; overflow-wrap: anywhere; }
.word-sample:nth-child(n+6) { font-size: clamp(27px, 5vw, 52px); }
.code-groups { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 24px 34px; }
.code-group { min-width: 0; }
.code-group h3, .mar-series h3 { margin: 0 0 10px; color: var(--muted); font-size: 12px; letter-spacing: .08em; text-transform: uppercase; }
.code-cloud { display: flex; flex-wrap: wrap; gap: 10px 18px; min-width: 0; }
.code-token { display: inline-block; min-width: 0; font-size: clamp(31px, 4.8vw, 51px); line-height: 1.15; white-space: nowrap; }
.mar-series { margin-top: 34px; padding-top: 25px; border-top: 1px solid rgba(101,72,115,.22); }
.mar-row { min-width: 0; margin: 0 0 12px; font-size: clamp(25px, 4vw, 43px); line-height: 1.35; overflow-wrap: anywhere; }
.marker-gallery { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 14px; }
.marker-sample { min-width: 0; margin: 0; text-align: center; }
.marker-sample img { display: block; width: 100%; height: auto; aspect-ratio: 1000/620; object-fit: contain; }
.marker-sample figcaption { color: var(--muted); font: 700 11px/1.3 ui-monospace, monospace; }
.marker-context-row { display: flex; flex-wrap: wrap; align-items: center; gap: 20px 24px; }
.marker-context-token { position: relative; display: inline-flex; min-width: 0; padding: 4px; font-size: clamp(31px, 4.8vw, 51px); line-height: 1.15; white-space: nowrap; }
.marker-context-token .hand-run { position: relative; z-index: 2; }
.context-marker { position: absolute; top: 50%; left: 50%; z-index: 1; display: block; width: clamp(68px, calc(100% + 24px), 118px); height: auto; max-width: none; opacity: .66; translate: -50% -50%; pointer-events: none; }
.final-ui-assets,.final-postit-row,.final-line-assets{display:flex;flex-wrap:wrap;align-items:center;gap:24px}.final-ui-assets figure{margin:0}.final-ui-assets img{display:block;max-width:250px;max-height:90px}.final-ui-assets figcaption{margin-top:7px;color:var(--muted);font-size:12px}.final-dot-row{display:flex;gap:20px;margin:24px 0}.final-dot-row img{width:22px;height:22px;object-fit:contain}.final-postit{width:190px;min-height:170px;padding:24px;box-shadow:0 8px 20px rgba(20,15,20,.15);font-size:24px}.final-postit.yellow{background:#f5dd62}.final-postit.green{background:#cce8bd}.final-postit.pink{background:#efbdca}.final-line-assets{margin-top:28px}.final-line-assets img{width:190px;max-height:90px;object-fit:contain}
@media (max-width: 620px) {
    .harmony-shell { width: 100%; padding-top: 20px; }
    .harmony-head { padding: 0 16px; }
    .paper-stack { gap: 14px; }
    .paper-card { padding: 28px 16px 34px; border-left: 0; border-right: 0; }
    .code-groups { grid-template-columns: 1fr; gap: 22px; }
    .alphabet-row { margin-bottom: 7px; }
    .word-list { gap: 13px; }
    .marker-gallery { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
</head>
<body>
<main class="harmony-shell" data-selected-characters="82" data-selected-glyphs="246" data-mixing-seed="__MIXING_SEED__">
    <header class="harmony-head">
        <p class="kicker">Development Preview · nicht produktiv</p>
        <h1>CEOKlaue Harmony</h1>
        <p>Drei echte Handschrift-Alternates im direkten Stilvergleich – als ruhiger Sammlr-Designbogen auf klassischem Notizblockkaro.</p>
    </header>
    <div class="paper-stack">__CONTENT__</div>
</main>
</body>
</html>"""
    html = html.replace("__MIXING_SEED__", escape(mixing_seed, quote=True)).replace(
        "__CONTENT__", "".join(alphabet_cards) + mixed_card + word_card + code_card
        + "".join(marker_cards) + marker_context_card + final_ui_card
    )
    response = Response(html, mimetype="text/html")
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


def ceoklaue_preview():
    ceoklaue_development_only()
    return """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>CEOKlaue v0.2 Preview · Sammlr.</title>
<style>
@font-face {
    font-family: "CEOKlaue v0.2 Preview";
    src: url("/dev/ceoklaue-preview/font.woff2") format("woff2");
    font-display: block;
}
:root {
    --paper: #f7f4ec;
    --grid-line: rgba(105, 88, 122, .24);
    --grid-size: 24px;
    --ink: #171419;
    --muted: #675f6b;
}
* { box-sizing: border-box; }
body {
    margin: 0;
    color: var(--ink);
    background: #dfdce1;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.preview-note {
    width: min(100% - 32px, 1100px);
    margin: 20px auto 12px;
    color: #514b55;
    font-size: 13px;
}
.preview-note strong { color: var(--ink); }
.paper {
    width: min(100% - 32px, 1100px);
    margin: 0 auto 40px;
    padding: 58px clamp(24px, 6vw, 78px) 76px;
    overflow: hidden;
    background-color: var(--paper);
    background-image:
        linear-gradient(to right, var(--grid-line) 1px, transparent 1px),
        linear-gradient(to bottom, var(--grid-line) 1px, transparent 1px);
    background-size: var(--grid-size) var(--grid-size);
    box-shadow: 0 12px 38px rgba(41, 35, 45, .16);
}
.hand {
    font-family: "CEOKlaue v0.2 Preview", cursive;
    font-weight: 400;
    letter-spacing: .01em;
}
.brand { margin: 0 0 22px; font-size: 52px; line-height: 1; }
.back { margin: 0 0 42px; font-size: 24px; }
.album-title { margin: 0 0 10px; font-size: clamp(34px, 5vw, 52px); line-height: 1.12; }
.stats { margin: 0; font-size: 23px; line-height: 1.4; }
.example { margin-top: 64px; }
.example h2 { margin: 0 0 24px; font-size: 38px; line-height: 1.1; font-weight: 400; }
.sticker-lines { display: grid; gap: 17px; font-size: 25px; line-height: 1.42; }
.sticker-lines p { margin: 0; overflow-wrap: anywhere; }
.trade-summary { margin: -10px 0 28px; font-size: 23px; }
.trade-columns { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 38px; }
.trade-columns h3 { margin: 0 0 10px; font-size: 26px; font-weight: 400; }
.trade-columns p { margin: 0; white-space: pre-line; font-size: 27px; line-height: 1.45; }
.natural { display: flex; flex-wrap: wrap; gap: 14px 30px; font-size: 27px; line-height: 1.35; }
.natural span { white-space: nowrap; }
.character-check { margin-top: 72px; padding-top: 28px; border-top: 1px solid rgba(66, 55, 71, .28); }
.character-check h2 { margin: 0 0 18px; font: 700 13px/1.3 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; letter-spacing: .09em; text-transform: uppercase; }
.metric-board { margin: 0 0 28px; padding: 18px; border: 1px solid rgba(66,55,71,.28); background: rgba(247,244,236,.72); }
.metric-row { position: relative; min-height: 92px; padding: 16px 8px 12px; overflow: hidden; }
.metric-row::before, .metric-row::after { content: ""; position: absolute; z-index: 0; left: 0; right: 0; border-top: 1px solid rgba(105,88,122,.42); }
.metric-row::before { top: 15px; }
.metric-row::after { bottom: 14px; }
.metric-row.xheight::before { top: 30px; }
.metric-row .guide-label { position: absolute; z-index: 2; right: 5px; color: #746b78; background: var(--paper); font: 10px/1.2 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
.metric-row .guide-label.top { top: 2px; }
.metric-row .guide-label.base { bottom: 1px; }
.metric-sample { position: relative; z-index: 1; display: block; font-size: 54px; line-height: 64px; white-space: nowrap; }
.character-line { margin: 0 0 13px; font-size: clamp(25px, 4vw, 38px); line-height: 1.42; overflow-wrap: anywhere; }
.open-char { position: relative; padding: 0 .04em; border-bottom: 2px solid #74637c; }
.open-char::after { content: ""; position: absolute; right: -.03em; top: -.05em; width: 5px; height: 5px; border-radius: 50%; background: #74637c; }
.open-note { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px; font: 12px/1.35 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: var(--muted); }
.open-note span { padding: 5px 8px; border: 1px solid #9d92a2; border-radius: 999px; background: rgba(247,244,236,.75); }
@media (max-width: 650px) {
    .paper { width: 100%; margin-bottom: 0; padding: 38px 20px 54px; }
    .preview-note { width: calc(100% - 28px); }
    .brand { font-size: 42px; }
    .trade-columns { grid-template-columns: 1fr; }
    .sticker-lines, .natural { font-size: 22px; }
}
</style>
</head>
<body>
<p class="preview-note"><strong>Development Preview · nicht final.</strong> Vorläufige PO-Auswahl, optisch normalisierte Metriken, moderat kräftigere Kontur und gleichmäßiges Karopapier.</p>
<main class="paper hand" data-grid-size="24" data-preview-font="CEOKlaue-v0.2-preview">
    <header>
        <p class="brand">Sammlr.</p>
        <p class="back">← Zurück zum Album</p>
        <h1 class="album-title">FIFA World Cup 2026</h1>
        <p class="stats">650 gesammelt · 342 fehlend · 110 doppelt</p>
    </header>

    <section class="example">
        <h2>Fehlende Sticker</h2>
        <div class="sticker-lines">
            <p>MEX10<br>KOR20</p>
            <p>BRA9, BRA11, BRA14, BRA15, BRA18, BRA19, BRA20</p>
            <p>MAR5, MAR8, MAR9, MAR12, MAR14, MAR15, MAR18, MAR20</p>
            <p>MAI2, MAI5, MAI6, MAI7, MAI9, MAI10, MAI11, MAI12, MAI14</p>
            <p>SCO2, SCO4, SCO5, SCO6, SCO7, SCO9, SCO11, SCO12, SCO14</p>
            <p>USA5, USA6, USA7, USA9, USA10, USA11, USA14, USA15</p>
        </div>
    </section>

    <section class="example">
        <h2>Aktueller Tausch</h2>
        <p class="trade-summary">3 erhalten · 2 abgegeben</p>
        <div class="trade-columns">
            <div><h3>Du bekommst:</h3><p>GER13
MEX12
BRA18</p></div>
            <div><h3>Du gibst ab:</h3><p>VFL149
USA20</p></div>
        </div>
    </section>

    <section class="example natural" aria-label="Natürlicher Text">
        <span>Sticker suchen</span><span>Doppelte Sticker</span>
        <span>Zurück zum Album</span><span>World Cup 2026</span><span>Sammlr.</span>
    </section>

    <section class="character-check">
        <h2>Zeichen-Check</h2>
        <div class="metric-board" aria-label="Typografische Referenzlinien">
            <div class="metric-row caps"><span class="guide-label top">Cap-Height</span><span class="guide-label base">Baseline</span><span class="metric-sample">ABMNRTUVW</span></div>
            <div class="metric-row xheight"><span class="guide-label top">x-Height</span><span class="guide-label base">Baseline</span><span class="metric-sample">acemnorsuvwxz</span></div>
            <div class="metric-row digits"><span class="guide-label top">Ziffernhöhe</span><span class="guide-label base">Baseline</span><span class="metric-sample">0123456789</span></div>
        </div>
        <p class="character-line">ABCDEFGHIJ<span class="open-char" title="noch v0.1 / nicht ausgewählt">K</span>LMNO<span class="open-char" title="noch v0.1 / nicht ausgewählt">P</span>QRSTUVWXYZ</p>
        <p class="character-line">abcdefghij<span class="open-char" title="noch v0.1 / nicht ausgewählt">k</span>lmnopqrstuvwxyz</p>
        <p class="character-line"><span class="open-char" title="noch v0.1 / nicht ausgewählt">0</span>123456789</p>
        <p class="character-line">ä ö ü ß</p>
        <p class="character-line">. , : ! ? - + / ( )</p>
        <div class="open-note" aria-label="Offene Auswahl">
            <span>K · noch v0.1 / nicht ausgewählt</span>
            <span>P · noch v0.1 / nicht ausgewählt</span>
            <span>k · noch v0.1 / nicht ausgewählt</span>
            <span>0 · noch v0.1 / nicht ausgewählt</span>
        </div>
    </section>
</main>
</body>
</html>"""


if app.config["SAMMLR_ENV"] in {"development", "testing"}:
    app.add_url_rule("/debug-db", "debug_db", debug_db, methods=["GET"])
    app.add_url_rule(
        "/debug-seed-now",
        "debug_seed_now",
        debug_seed_now,
        methods=["POST"],
    )
    app.add_url_rule(
        "/dev/ceoklaue",
        "ceoklaue_final_reselection",
        ceoklaue_control_page,
        methods=["GET"],
    )
    app.add_url_rule(
        "/dev/ceoklaue/fh-repair-asset/<filename>",
        "ceoklaue_final_reselection_asset",
        ceoklaue_final_fh_repair_asset,
        methods=["GET"],
    )
    app.add_url_rule(
        "/dev/ceoklaue/glyph/<glyph_key>/<filename>",
        "ceoklaue_glyph_workbench_asset",
        ceoklaue_glyph_workbench_asset,
        methods=["GET"],
    )
    app.add_url_rule(
        "/dev/ceoklaue-preview",
        "ceoklaue_preview",
        ceoklaue_preview,
        methods=["GET"],
    )
    app.add_url_rule(
        "/dev/ceoklaue-preview/font.woff2",
        "ceoklaue_preview_font",
        ceoklaue_preview_font,
        methods=["GET"],
    )
    app.add_url_rule(
        "/dev/ceoklaue-harmony",
        "ceoklaue_harmony",
        ceoklaue_harmony,
        methods=["GET"],
    )
    app.add_url_rule(
        "/dev/ceoklaue-harmony/glyph/<glyph_key>/<filename>",
        "ceoklaue_harmony_asset",
        ceoklaue_harmony_asset,
        methods=["GET"],
    )
    app.add_url_rule(
        "/dev/ceoklaue-harmony/marker/<family>/<filename>",
        "ceoklaue_harmony_marker_asset",
        ceoklaue_harmony_marker_asset,
        methods=["GET"],
    )


def sammlr_feedback_html(message, undo_url=None):
    if not message:
        return ""

    title = message
    lines = []
    undoable = undo_url is not None

    if "Transfer durchgeführt:" in message:
        title = "Transfer gespeichert"
        detail = message.split(":", 1)[1].strip().rstrip(".")
        for part in detail.split(","):
            part = part.strip()
            if part:
                lines.append(part)
    elif "Transfer gespeichert:" in message:
        title = "Transfer gespeichert"
        detail = message.split(":", 1)[1].strip().rstrip(".")
        for part in detail.split(","):
            part = part.strip()
            if part:
                lines.append(part)
    elif "rückgängig" in message.lower():
        title = "Rückgängig"
        lines.append(message.rstrip("."))
    elif "hinzugefügt" in message or "doppelt" in message or "zur Sammlung hinzugefügt" in message:
        title = "Sticker eingeklebt"
        first_word = message.split(" ", 1)[0]
        count = first_word if first_word.isdigit() else "1"
        lines.append(f"+{count} Sticker hinzugefügt")
    elif "entfernt" in message:
        title = "Sticker entfernt"
        first_word = message.split(" ", 1)[0]
        count = first_word if first_word.isdigit() else "1"
        lines.append(f"{count} Sticker entfernt")
    else:
        lines.append(message)

    line_html = "".join(f"<p>{escape(line)}</p>" for line in lines)
    undo_html = (
        f'<form class="sammlr-feedback-undo" method="POST" action="{undo_url}">'
        '<button type="submit">Rückgängig</button></form>'
        if undoable else ""
    )
    normalized_message = message.lower()
    if any(word in normalized_message for word in ("nicht", "fehler", "geplatzt")):
        tone = " error"
    elif any(word in normalized_message for word in ("offen", "wartet", "aussteh")):
        tone = " warning"
    else:
        tone = " success"
    return f"""
    <div class="sammlr-feedback{tone}">
        <div>
            <strong>{escape(title)}</strong>
            {line_html}
        </div>
        {undo_html}
    </div>
    """


def collection_feedback_html(message):
    if not message:
        return ""

    undoable = "hinzugefügt" in message or "doppelt" in message or "entfernt" in message or "rückgängig" in message.lower()
    return sammlr_feedback_html(message, "/undo" if undoable and "rückgängig" not in message.lower() else None)


def confirm_selection_modal_html(
    modal_id,
    get_content_id,
    give_content_id,
    primary_text,
    primary_attributes,
    secondary_attributes,
    error_id=None,
    extra_class="",
    alternate_text=None,
    alternate_attributes="",
    subtitle_id=None,
    subtitle_text=""
):
    error_html = (
        f'<p id="{error_id}" class="sticker-list-error" style="display:none;"></p>'
        if error_id else ""
    )
    subtitle_html = (
        f'<p id="{subtitle_id}" class="sammlr-confirm-subtitle">{escape(subtitle_text)}</p>'
        if subtitle_id else ""
    )
    extra_class = f" {extra_class.strip()}" if extra_class.strip() else ""
    return f"""
    <div class="quick-action-modal review-modal confirm-selection-modal{extra_class}" id="{modal_id}" style="display:none;">
        <div class="quick-action-card review-card sammlr-confirm-card">
            <h3 class="sammlr-confirm-title">Auswahl prüfen</h3>
            {subtitle_html}
            <div class="sammlr-confirm-grid">
                <section class="sammlr-confirm-panel">
                    <h3>Du bekommst</h3>
                    <div class="sammlr-confirm-content" id="{get_content_id}"></div>
                </section>
                <section class="sammlr-confirm-panel">
                    <h3>Du gibst ab</h3>
                    <div class="sammlr-confirm-content" id="{give_content_id}"></div>
                </section>
            </div>
            {error_html}
            <div class="sammlr-confirm-actions{' has-three-actions' if alternate_text else ''}">
                <button type="button" class="sammlr-confirm-secondary" {secondary_attributes}>Bearbeiten</button>
                {f'<button type="button" class="sammlr-confirm-secondary sammlr-confirm-danger" {alternate_attributes}>{alternate_text}</button>' if alternate_text else ''}
                <button type="button" class="sammlr-confirm-primary" {primary_attributes}>{primary_text}</button>
            </div>
        </div>
    </div>
    """


def configured_auth_clock():
    provider = app.config.get("AUTH_CLOCK")
    return provider if callable(provider) else None


def configured_client_ip():
    provider = app.config.get("CLIENT_IP_PROVIDER")
    if callable(provider):
        return str(provider())
    return str(request.remote_addr or "unknown")


@app.before_request
def establish_request_observability():
    g.request_id = safe_request_id(request.headers.get(REQUEST_ID_HEADER))
    g.request_started = time.perf_counter()


@app.before_request
def security_and_login_guard():
    # Only private V1 control-photo uploads need a larger binary body. Keep all
    # other endpoints' existing 1 MB limit and CSRF/authentication unchanged.
    if request.endpoint == "trade_shell.preparation_command" and (request.view_args or {}).get("action") == "upload":
        from services.lifecycle_photos import MAX_BYTES
        request.max_content_length = MAX_BYTES + 64 * 1024
    if len(request.query_string) > MAX_QUERY_STRING_LENGTH:
        abort(414)
    if request.method == "POST" and app.config.get("CSRF_ENABLED", True):
        expected = session.get("csrf_token")
        supplied = request.form.get("_csrf_token") or request.headers.get(
            "X-CSRF-Token"
        )
        if not expected or not supplied or not hmac.compare_digest(expected, supplied):
            abort(403)

    if request.endpoint == "trade_visual_preview" and app.config.get("SAMMLR_ENV") in {"development", "testing"}:
        return None

    public_endpoints = {
        "login", "reactivate_account", "register", "healthz", "static",
        "debug_db", "debug_seed_now", "design_bible_master_asset",
        "ceoklaue_glyph_workbench", "ceoklaue_glyph_workbench_asset",
        "ceoklaue_final_reselection", "ceoklaue_final_reselection_asset",
        "ceoklaue_preview", "ceoklaue_preview_font",
        "ceoklaue_harmony", "ceoklaue_harmony_asset",
        "ceoklaue_harmony_marker_asset",
        "privacy_notice", "legal_notice", "data_export_notice",
    }

    if request.endpoint is None:
        return None

    if request.endpoint in public_endpoints:
        return None

    if "user_id" not in session:
        return redirect("/login")

    con = get_db()
    try:
        if auth_schema_available(con):
            state_select = ", account_state" if account_lifecycle_schema_available(con) else ""
            user = con.execute(
                f"""
                SELECT auth_version{state_select}, name, username,
                       (SELECT COUNT(*) FROM notifications
                        WHERE notifications.user_id=users.id AND is_read=0)
                       AS unread_count
                FROM users WHERE id=?
                """,
                (session["user_id"],),
            ).fetchone()
            expected_version = int(user["auth_version"]) if user else None
            account_state = user["account_state"] if user and state_select else ACTIVE
            session_version = session.get("auth_version")
            if (
                session_version is None
                and app.testing
                and app.config.get("TESTING_AUTH_VERSION_COMPAT", True)
                and expected_version is not None
            ):
                session["auth_version"] = expected_version
                session_version = expected_version
            if (
                expected_version is None
                or session_version != expected_version
                or account_state != ACTIVE
            ):
                session.clear()
                return redirect("/login")
            g.header_identity = (
                (user["name"] or user["username"] or "").strip()
                if user else ""
            )
            g.header_unread_count = int(user["unread_count"] or 0) if user else 0
    finally:
        con.close()

    return None


POST_FORM_PATTERN = re.compile(
    r'(<form\b(?=[^>]*\bmethod\s*=\s*["\']?POST["\']?)[^>]*>)',
    flags=re.IGNORECASE,
)


@app.after_request
def inject_csrf_into_html_forms(response):
    if not response.mimetype == "text/html" or response.direct_passthrough:
        return response
    html = response.get_data(as_text=True)
    if "<form" not in html.lower():
        return response
    token_field = (
        '<input type="hidden" name="_csrf_token" value="'
        + escape(ensure_csrf_token())
        + '">'
    )
    response.set_data(POST_FORM_PATTERN.sub(lambda match: match.group(1) + token_field, html))
    return response


@app.after_request
def finalize_request_observability(response):
    request_id = getattr(g, "request_id", safe_request_id(None))
    response.headers[REQUEST_ID_HEADER] = request_id
    configured_stream = app.config.get("REQUEST_LOG_STREAM")
    if app.config.get("SAMMLR_ENV") == "testing" and configured_stream is None:
        return response
    started = getattr(g, "request_started", time.perf_counter())
    payload = {
        "timestamp": utc_timestamp(),
        "level": "error" if response.status_code >= 500 else (
            "warning" if response.status_code >= 400 else "info"
        ),
        "request_id": request_id,
        "method": request.method,
        "path": request.url_rule.rule if request.url_rule is not None else "<unmatched>",
        "status": response.status_code,
        "duration_ms": round((time.perf_counter() - started) * 1000, 3),
    }
    if "user_id" in session:
        payload["user_ref"] = pseudonymous_user_ref(
            app.config["SECRET_KEY"], session["user_id"]
        )
    if response.status_code >= 500 and not getattr(g, "error_tracked", False):
        tracker = app.config.get("ERROR_TRACKER") or JsonErrorTracker()
        tracker.capture_exception(
            Http500Response(),
            request_id=request_id,
            method=request.method,
            route=request.url_rule.rule if request.url_rule is not None else "<unmatched>",
        )
        g.error_tracked = True
    write_request_log(payload, stream=configured_stream or sys.stdout)
    return response


@app.after_request
def apply_response_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if app.config.get("SAMMLR_ENV") == "production":
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
    return response


@app.errorhandler(500)
def track_unexpected_server_error(error):
    original = getattr(error, "original_exception", None) or error
    if getattr(error, "original_exception", None) is None:
        tracker = app.config.get("ERROR_TRACKER") or JsonErrorTracker()
        tracker.capture_exception(
            original,
            request_id=getattr(g, "request_id", None),
            method=request.method,
            route=request.url_rule.rule if request.url_rule is not None else "<unmatched>",
        )
        g.error_tracked = True
    return jsonify({"status": "error"}), 500


@app.errorhandler(403)
def controlled_forbidden_response(error):
    if (
        request.endpoint == "update_sticker_quantity_inline"
        or request.is_json
        or request.accept_mimetypes.best == "application/json"
    ):
        return jsonify({"status": "error", "code": "forbidden"}), 403

    return """
    <html lang="de"><head>""" + style() + """</head>
    <body class="s31-product-page s30-reference-page">
        <main class="container">
            <section class="card sammlr-empty-state" role="alert">
                <h1>Zugriff nicht möglich</h1>
                <p>Diese Anfrage konnte nicht ausgeführt werden.</p>
                <a class="btn" href="/">Zurück zu sammlr</a>
            </section>
        </main>
    </body></html>
    """, 403


@app.route("/healthz")
def healthz():
    try:
        validate_database(DB, expected_version=EXPECTED_SCHEMA_VERSION,
                          compatible_versions=TRADE_V2_COMPATIBLE_SCHEMA_VERSIONS)
    except RuntimeConfigurationError:
        return jsonify({"status": "unavailable"}), 503
    return jsonify({"status": "ok"})





def init_db():
    con = get_db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        favorite_album_id TEXT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS stickers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        album_id TEXT,
        sticker_code TEXT,
        status TEXT,
        duplicates INTEGER DEFAULT 0,
        quantity INTEGER DEFAULT 1,
        user_id INTEGER DEFAULT 1
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS albums (
        id TEXT PRIMARY KEY,
        name TEXT,
        season TEXT,
        total INTEGER,
        complete INTEGER,
        cover TEXT
    )
    """)
    try:
        cur.execute("ALTER TABLE users ADD COLUMN name TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE users ADD COLUMN favorite_album_id TEXT")
    except sqlite3.OperationalError:
        pass

    cur.execute("""
    CREATE TABLE IF NOT EXISTS unlocked_trophies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        album_id TEXT,
        trophy_name TEXT,
        unlocked_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, album_id, trophy_name)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_albums (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        album_id TEXT,
        UNIQUE(user_id, album_id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS trade_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        album_id TEXT,
        from_user_id INTEGER,
        to_user_id INTEGER,
        give_codes TEXT,
        get_codes TEXT,
        status TEXT DEFAULT 'open',
        from_confirmed INTEGER DEFAULT 0,
        to_confirmed INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    try:
        cur.execute("ALTER TABLE trade_requests ADD COLUMN from_confirmed INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE trade_requests ADD COLUMN to_confirmed INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    cur.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        body TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    try:
        cur.execute("ALTER TABLE stickers ADD COLUMN user_id INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass

    wm26_total = len(build_wm26())
    cur.execute("""
    INSERT OR IGNORE INTO albums (id, name, season, total, complete, cover)
    VALUES ('wm26', 'FIFA World Cup 2026', '2026', ?, ?, '🌍')
    """, (wm26_total, wm26_total))
    cur.execute(
        "UPDATE albums SET total=?, complete=? WHERE id='wm26'",
        (wm26_total, wm26_total)
    )

    con.commit()
    con.close()


def style():
    csrf_value = escape(ensure_csrf_token())
    return """
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="csrf-token" content="__SAMMLR_CSRF_TOKEN__">
    <link rel="stylesheet" href="/static/style.css">
    <script>
    function sammlrHistoryMutationId(){
        if(window.crypto && typeof window.crypto.randomUUID === 'function'){
            return window.crypto.randomUUID();
        }
        return Date.now().toString(36) + '-' + Math.random().toString(36).slice(2);
    }

    function syncBottomLayoutSpace(){
        const page = document.querySelector('.sticker-list-page');
        if(!page) return;

        const nav = page.querySelector('.bottom-nav:not(.album-bottom-nav)');
        const dock = page.querySelector('.sticker-list-tradebar');
        let navigationSpace = 0;
        if(nav && window.getComputedStyle(nav).display !== 'none'){
            const navBottom = parseFloat(window.getComputedStyle(nav).bottom) || 0;
            navigationSpace = Math.ceil(nav.getBoundingClientRect().height + navBottom);
        }
        const dockHeight = dock ? Math.ceil(dock.getBoundingClientRect().height) : 0;
        page.style.setProperty('--sammlr-bottom-nav-space', navigationSpace + 'px');
        page.style.setProperty('--sammlr-trade-dock-height', dockHeight + 'px');
    }

    document.addEventListener('DOMContentLoaded', function(){
        const bottomLayoutTargets = document.querySelectorAll(
            '.sticker-list-page .bottom-nav:not(.album-bottom-nav), ' +
            '.sticker-list-page .sticker-list-tradebar'
        );
        if('ResizeObserver' in window && bottomLayoutTargets.length){
            const bottomLayoutObserver = new ResizeObserver(syncBottomLayoutSpace);
            bottomLayoutTargets.forEach(function(target){
                bottomLayoutObserver.observe(target);
            });
        }
        window.addEventListener('resize', syncBottomLayoutSpace);
        if(window.visualViewport){
            window.visualViewport.addEventListener('resize', syncBottomLayoutSpace);
        }
        syncBottomLayoutSpace();

        document.querySelectorAll('.progress[data-progress]').forEach(function(progress){
            const raw = String(progress.dataset.progress || '').replace(',', '.');
            const match = raw.match(/\\d+(?:\\.\\d+)?/);
            const value = match ? parseFloat(match[0]) : NaN;
            if (!Number.isNaN(value)) {
                progress.classList.toggle('progress-text-on-fill', value >= 50);
            }
        });
        document.querySelectorAll('form').forEach(function(form){
            if(String(form.method || '').toUpperCase() !== 'POST') return;
            form.addEventListener('submit', function(){
                if(!form.querySelector('input[name="_history_mutation_id"]')){
                    const mutationId = document.createElement('input');
                    mutationId.type = 'hidden';
                    mutationId.name = '_history_mutation_id';
                    mutationId.value = sammlrHistoryMutationId();
                    form.appendChild(mutationId);
                }
                window.setTimeout(function(){
                    form.setAttribute('aria-busy', 'true');
                    form.querySelectorAll('button[type="submit"], input[type="submit"]').forEach(function(control){
                        control.disabled = true;
                        control.classList.add('is-submitting');
                    });
                }, 0);
            });
        });
    });
    </script>
    """.replace("__SAMMLR_CSRF_TOKEN__", csrf_value)


def history_request_event_key(scope, suffix=None):
    raw = (
        request.form.get("_history_mutation_id", "").strip()
        or request.headers.get("Idempotency-Key", "").strip()
        or secrets.token_urlsafe(18)
    )
    if re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", raw) is None:
        abort(400)
    key = f"{scope}:{current_user_id()}:{raw}"
    return f"{key}:{suffix}" if suffix is not None else key


def page_title(title=None, subtitle=None):
    title_html = f"<h1>{title}</h1>" if title else ""
    subtitle_html = f"<p>{subtitle}</p>" if subtitle else ""
    return f"""
    <section class="page-title">
        {title_html}
        {subtitle_html}
    </section>
    """


def header_avatar_initial():
    user_id = session.get("user_id")
    if user_id is None:
        return "S"

    identity = getattr(g, "header_identity", "")
    if not identity:
        con = get_db()
        user = con.execute(
            "SELECT name, username FROM users WHERE id=?",
            (user_id,),
        ).fetchone()
        con.close()
        if user:
            identity = (user["name"] or user["username"] or "").strip()
    return escape(identity[:1].upper() or "S")


def header_notification_badge():
    user_id = session.get("user_id")
    if user_id is None:
        return ""
    unread_count = getattr(g, "header_unread_count", None)
    if unread_count is None:
        con = get_db()
        unread_count = NotificationHistoryService(con).unread_count(user_id)
        con.close()
    if unread_count == 0:
        return ""
    label = str(unread_count) if unread_count <= 99 else "99+"
    return (
        f'<span class="notification-badge" aria-label="{unread_count} ungelesene '
        f'Benachrichtigungen">{label}</span>'
    )


def app_header_brand_wordmark():
    return (
        '<span class="app-header-brand-word">sammlr<span '
        'class="app-header-brand-dot">.</span></span>'
    )


def app_header(
    active_title=None,
    subtitle=None,
    variant="compact",
    foundation=False,
    own_profile_settings=False,
):
    if variant not in {"large", "compact"}:
        variant = "compact"
    title_block = page_title(active_title, subtitle) if active_title or subtitle else ""
    brand_html = app_header_brand_wordmark()
    bell_html = """
                    <svg class="app-header-bell app-header-bell-svg" viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"></path>
                        <path d="M10 21h4"></path>
                    </svg>
    """
    profile_action_html = f"""
            <a class="app-header-action app-header-profile" href="/profil" aria-label="Eigenes Profil öffnen">
                <span class="app-header-avatar" aria-hidden="true">{header_avatar_initial()}</span>
            </a>
    """
    if own_profile_settings:
        profile_action_html = """
            <a class="app-header-action app-header-settings" href="/account" aria-label="Account und Einstellungen öffnen">
                <svg class="app-header-settings-svg" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Z"></path>
                    <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.86 2.86-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6 1.7 1.7 0 0 0-.4 1.1V21H9.55v-.1A1.7 1.7 0 0 0 8.5 19.4a1.7 1.7 0 0 0-1.88.34l-.06.06-2.86-2.86.06-.06A1.7 1.7 0 0 0 4.1 15a1.7 1.7 0 0 0-.6-1 1.7 1.7 0 0 0-1.1-.4H2.3V9.55h.1A1.7 1.7 0 0 0 4.1 8.5a1.7 1.7 0 0 0-.34-1.88l-.06-.06L6.56 3.7l.06.06A1.7 1.7 0 0 0 8.5 4.1a1.7 1.7 0 0 0 1-.6 1.7 1.7 0 0 0 .4-1.1v-.1h4.05v.1A1.7 1.7 0 0 0 15 4.1a1.7 1.7 0 0 0 1.88-.34l.06-.06 2.86 2.86-.06.06A1.7 1.7 0 0 0 19.4 8.5a1.7 1.7 0 0 0 .6 1 1.7 1.7 0 0 0 1.1.4h.1v4.05h-.1A1.7 1.7 0 0 0 19.4 15Z"></path>
                </svg>
            </a>
        """
    actions_html = ""
    if session.get("user_id") is not None:
        actions_html = f"""
        <nav class="app-header-actions" aria-label="Globale Zugänge">
            <form class="app-header-notification-form" method="POST" action="/notifications">
                <button class="app-header-action app-header-notifications" type="submit" aria-label="Benachrichtigungen öffnen">
                    {bell_html}
                    {header_notification_badge()}
                </button>
            </form>
            {profile_action_html}
        </nav>
        """
    return f"""
    <header class="app-header">
        <span class="app-header-variant app-header-variant-{variant}" hidden></span>
        <a class="app-header-brand" href="/">
            {brand_html}
        </a>
        {actions_html}
    </header>
    {title_block}
    """


def compliance_links_html():
    return """
    <nav class="sammlr-compliance-links" aria-label="Rechtliche Informationen">
        <a href="/datenschutz">Datenschutz</a>
        <a href="/impressum">Impressum</a>
        <a href="/datenexport-hinweise">Exporthinweise</a>
    </nav>
    """


from services.albums import (
    compact,
    display_code,
    em_map,
    resolve_code,
    all_codes
)


def lade_album_for_user(album_id, user_id):
    con = get_db()
    album = con.execute("SELECT * FROM albums WHERE id=?", (album_id,)).fetchone()
    inventory = InventoryReadService(con).album(
        user_id, album_id, all_codes(album_id)
    )
    con.close()

    by_code = inventory.items_by_code
    if album_id == "em24":
        total = len(build_em24())
    elif album_id == "wm26":
        total = len(build_wm26())
    else:
        total = album["total"]

    progress = inventory.progress(all_codes(album_id), total)
    return (
        album,
        by_code,
        progress.collected,
        progress.duplicate_quantity,
        progress.percent,
        progress.total,
    )


def lade_album(album_id):
    return lade_album_for_user(album_id, current_user_id())


def lade_album_inventory(album_id):
    con = get_db()
    inventory = InventoryReadService(con).album(
        current_user_id(), album_id, all_codes(album_id)
    )
    con.close()
    return inventory


def format_sammlr_date(value):
    if not value:
        return ""

    from datetime import datetime

    raw_value = str(value).strip()
    for date_format in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw_value[:19], date_format).strftime("%d.%m.%Y")
        except ValueError:
            pass

    return raw_value[:10]


SAMMLR_TIMEZONE = ZoneInfo("Europe/Berlin")
TRADE_SHIPPING_BUSINESS_DAYS = 5
TRADE_RECEIPT_ATTENTION_DAYS = 14


def parse_sammlr_timestamp(value):
    if not value:
        return None
    raw_value = str(value).strip()
    for date_format in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            parsed = datetime.strptime(raw_value[:19], date_format)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def format_sammlr_timestamp(value):
    parsed = parse_sammlr_timestamp(value)
    if parsed is None:
        return ""
    local_time = parsed.astimezone(SAMMLR_TIMEZONE)
    return local_time.strftime("%d.%m.%Y|%H:%M")


def sammlr_time_html(value):
    formatted = format_sammlr_timestamp(value)
    if not formatted:
        return '<span class="trade-timeline-time legacy">Zeitpunkt nicht verfügbar</span>'
    date_label, time_label = formatted.split("|", 1)
    return (
        f'<time class="trade-timeline-time" datetime="{escape(str(value))}">'
        f'<span>{date_label}</span><span>{time_label}</span></time>'
    )


def add_business_days(value, days=TRADE_SHIPPING_BUSINESS_DAYS):
    current = parse_sammlr_timestamp(value)
    if current is None:
        return None
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def _row_value(row, key, default=None):
    if row is None:
        return default
    try:
        return row[key]
    except (KeyError, IndexError):
        return default


def trade_other_shipped_at(shipping_status, user_id):
    side = shipping_status.side_for(user_id)
    if side == "requester":
        return shipping_status.partner_shipped_at
    if side == "partner":
        return shipping_status.requester_shipped_at
    return None


def trade_other_received_at(receipt_status, user_id):
    side = receipt_status.side_for(user_id)
    if side == "requester":
        return receipt_status.partner_received_at
    if side == "partner":
        return receipt_status.requester_received_at
    return None


def trade_timeline_context(connection, trade_request_id):
    if not table_exists(connection, "trades"):
        return None
    lifecycle = connection.execute(
        "SELECT * FROM trades WHERE legacy_trade_request_id=?",
        (trade_request_id,),
    ).fetchone()
    if lifecycle is None:
        return None

    accepted_at = None
    if table_exists(connection, "trade_reservations"):
        row = connection.execute(
            "SELECT MIN(created_at) AS accepted_at FROM trade_reservations WHERE trade_id=?",
            (lifecycle["id"],),
        ).fetchone()
        accepted_at = row["accepted_at"] if row else None

    return {
        "lifecycle_trade_id": lifecycle["id"],
        "lifecycle_state": lifecycle["lifecycle_state"],
        "accepted_at": accepted_at,
        "completed_at": lifecycle["completed_at"],
    }


def trade_is_successfully_completed(
    trade,
    timeline_context=None,
    receipt_status=None,
    problem_reports=(),
):
    """Compatibility adapter to the canonical CB-010 success contract."""
    request_status = _row_value(trade, "status", "")
    if timeline_context is None:
        return SuccessfulTradeProjectionService.legacy_is_successful(
            request_status
        )
    has_open_problem_remainder = any(
        report.state == "open" or report.open_quantity > 0
        for report in problem_reports
    )
    return SuccessfulTradeProjectionService.lifecycle_is_successful(
        request_status,
        timeline_context.get("lifecycle_state"),
        receipt_status.requester_received if receipt_status else False,
        receipt_status.partner_received if receipt_status else False,
        has_open_problem_remainder,
    )


def trade_status_chip(label):
    normalized = str(label or "").strip()
    variants = {
        "Offen": "open",
        "Reserviert": "reserved",
        "Versand läuft": "shipping",
        "Beide Seiten haben versendet": "shipping",
        "Problem offen": "problem",
        "Trade mit Problem beendet": "problem-closed",
        "Problem nachträglich gelöst": "completed",
        "Teilweise erhalten": "partial",
        "Empfang vollständig": "received",
        "Abgeschlossen": "completed",
        "Abgelehnt": "muted",
        "Geplatzt": "muted",
        "Abgelaufen": "expired",
        "Obsolet": "obsolete",
    }
    variant = variants.get(normalized, "muted")
    return (
        f'<span class="trade-status-chip {variant}">'
        f'{escape(normalized)}</span>'
    )


def trade_timeline_items(
    trade,
    user_id,
    timeline_context=None,
    shipping_status=None,
    receipt_status=None,
    problem_reports=(), rating_state=None,
):
    items = [{
        "label": "Anfrage gesendet",
        "state": "done",
        "timestamp": _row_value(trade, "created_at"),
    }]
    status = _row_value(trade, "status", "")
    accepted_at = (
        timeline_context.get("accepted_at") if timeline_context else None
    )
    lifecycle_exists = timeline_context is not None

    if status == "open":
        items.extend((
            {"label": "Anfrage angenommen", "state": "pending", "timestamp": None},
            {"label": "Sticker reserviert", "state": "pending", "timestamp": None},
        ))
        return items
    if status in {"declined", "cancelled"} and not lifecycle_exists:
        items.append({
            "label": "Anfrage abgelehnt" if status == "declined" else "Anfrage beendet",
            "state": "muted",
            "timestamp": None,
        })
        return items

    items.extend((
        {"label": "Anfrage angenommen", "state": "done", "timestamp": accepted_at},
        {"label": "Sticker reserviert", "state": "done", "timestamp": accepted_at},
    ))

    if shipping_status is not None:
        items.extend((
            {
                "label": "Eigener Versand bestätigt",
                "state": "done" if shipping_status.shipped_for(user_id) else "pending",
                "timestamp": shipping_status.shipped_at_for(user_id),
            },
            {
                "label": "Gegenseite versendet",
                "state": "done" if shipping_status.other_shipped_for(user_id) else "pending",
                "timestamp": trade_other_shipped_at(shipping_status, user_id),
            },
        ))

    rating_added = False
    for report in problem_reports:
        owner = (
            "deiner Lieferung"
            if report.receiver_user_id == user_id
            else "der Lieferung der Gegenseite"
        )
        items.append({
            "label": f"Problem bei {owner} gemeldet",
            "state": "warning",
            "timestamp": report.created_at,
        })
        resolved_after_close = bool(report.resolved_after_close_at)
        items.append({
            "label": (
                "Problem offen"
                if resolved_after_close else
                ("Problem gelöst" if report.state == "resolved" else "Problem offen")
            ),
            "state": (
                "warning"
                if resolved_after_close else
                ("done" if report.state == "resolved" else "warning")
            ),
            "timestamp": None if resolved_after_close else report.resolved_at,
        })
        terminal_history = []
        if report.closed_at:
            terminal_history.append({
                "label": "Trade mit Problem beendet",
                "state": "done",
                "timestamp": report.closed_at,
            })
        if (
            not rating_added
            and rating_state is not None
            and rating_state.code == TradeRatingCode.ALREADY_RATED
            and rating_state.created_at
        ):
            terminal_history.append({
                "label": f"{rating_state.stars} Sterne vergeben",
                "state": "done",
                "timestamp": rating_state.created_at,
            })
            rating_added = True
        if report.resolved_after_close_at:
            terminal_history.append({
                "label": "Problem nachträglich gelöst",
                "state": "done",
                "timestamp": report.resolved_after_close_at,
            })
        terminal_history.sort(
            key=lambda item: (
                parse_sammlr_timestamp(item["timestamp"])
                or datetime.min.replace(tzinfo=timezone.utc)
            )
        )
        items.extend(terminal_history)

    if (
        not rating_added
        and rating_state is not None
        and rating_state.code == TradeRatingCode.ALREADY_RATED
        and rating_state.created_at
    ):
        items.append({
            "label": f"{rating_state.stars} Sterne vergeben",
            "state": "done",
            "timestamp": rating_state.created_at,
        })

    if receipt_status is not None:
        items.extend((
            {
                "label": "Eigener Empfang bestätigt",
                "state": "done" if receipt_status.received_for(user_id) else "pending",
                "timestamp": receipt_status.received_at_for(user_id),
            },
            {
                "label": "Gegenseite bestätigt",
                "state": "done" if receipt_status.other_received_for(user_id) else "pending",
                "timestamp": trade_other_received_at(receipt_status, user_id),
            },
        ))

    completed = trade_is_successfully_completed(
        trade,
        timeline_context,
        receipt_status,
        problem_reports,
    )
    completed_at = (
        timeline_context.get("completed_at") if timeline_context else None
    )
    lifecycle_state = (
        timeline_context.get("lifecycle_state") if timeline_context else None
    )
    terminal_problem_state = lifecycle_state in {
        "closed_with_problem",
        "problem_resolved_after_close",
    }
    completed_item = {
        "label": (
            "Trade operativ abgeschlossen"
            if terminal_problem_state else "Trade abgeschlossen"
        ),
        "state": "done" if completed or terminal_problem_state else "pending",
        "timestamp": completed_at,
    }
    if completed and all(item.get("timestamp") for item in items):
        items.sort(
            key=lambda item: (
                parse_sammlr_timestamp(item.get("timestamp"))
                or datetime.min.replace(tzinfo=timezone.utc)
            )
        )
    items.append(completed_item)
    return items


def trade_timeline_html(items, partner_name=None):
    """Render the canonical lifecycle as one collapsed/expanded component."""
    symbols = {"done": "✓", "pending": "○", "warning": "!", "muted": "–"}
    partner = str(partner_name or "Gegenseite").strip() or "Gegenseite"

    def projected_label(label):
        replacements = {
            "Eigener Versand bestätigt": "Dein Versand wurde bestätigt",
            "Gegenseite versendet": f"{partner} hat den Versand bestätigt",
            "Eigener Empfang bestätigt": "Du hast den Empfang bestätigt",
            "Gegenseite bestätigt": f"{partner} hat den Empfang bestätigt",
        }
        return replacements.get(label, label)

    occurred = [
        item for item in items
        if item.get("timestamp") or item.get("state") in {"done", "warning", "muted"}
    ]
    if not occurred and items:
        occurred = [items[0]]

    rendered = []
    for item in items:
        state = item["state"]
        timestamp = item.get("timestamp")
        source_label = str(item["label"])
        time_html = sammlr_time_html(timestamp) if timestamp or state == "done" else ""
        rendered.append(f"""
        <div class="trade-timeline-item {state} trade-product-timeline-event"
             role="listitem" data-source-label="{escape(source_label)}">
            <span class="trade-timeline-marker trade-product-step-icon" aria-hidden="true">{symbols[state]}</span>
            <div class="trade-timeline-content">
                <span class="trade-product-contract-state">{escape(source_label)}</span>
                <strong>{escape(projected_label(source_label))}</strong>
                {time_html}
            </div>
        </div>
        """)

    latest = occurred[-1] if occurred else {"label": "Status nicht verfügbar", "state": "muted"}
    latest_state = latest.get("state", "muted")
    latest_timestamp = latest.get("timestamp")
    latest_time_html = (
        sammlr_time_html(latest_timestamp)
        if latest_timestamp or latest_state == "done"
        else ""
    )
    pending_contract = " | ".join(
        str(item["label"]) for item in items if item not in occurred
    )
    latest_label_html = escape(projected_label(str(latest["label"]))).replace(
        "Trade abgeschlossen", "Trade&#32;abgeschlossen"
    )
    return f"""
    <section class="card trade-timeline"
             aria-label="Trade Timeline" data-pending-contract="{escape(pending_contract)}">
        <h2>Versandstatus</h2>
        <div class="trade-product-latest {escape(latest_state)}">
            <span class="trade-product-step-icon" aria-hidden="true">{symbols[latest_state]}</span>
            <div>
                <strong>{latest_label_html}</strong>
                {latest_time_html}
            </div>
        </div>
        <details class="trade-product-timeline">
            <summary>
                <span class="trade-product-show-label">Gesamten Verlauf anzeigen ↓</span>
                <span class="trade-product-hide-label">Verlauf ausblenden ↑</span>
            </summary>
            <div class="trade-product-timeline-items" role="list">
                {''.join(rendered)}
            </div>
        </details>
    </section>
    """


def trade_attention_html(
    user_id,
    timeline_context=None,
    shipping_status=None,
    receipt_status=None,
    problem_reports=(),
    now=None,
):
    if shipping_status is None:
        return ""
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    own_problem_open = any(
        report.receiver_user_id == user_id and report.state == "open"
        for report in problem_reports
    )
    if (
        shipping_status.other_shipped_for(user_id)
        and receipt_status is not None
        and not receipt_status.received_for(user_id)
        and not own_problem_open
    ):
        shipped_at = parse_sammlr_timestamp(
            trade_other_shipped_at(shipping_status, user_id)
        )
        if shipped_at is not None:
            elapsed_days = max((current_time - shipped_at).days, 0)
            if elapsed_days >= TRADE_RECEIPT_ATTENTION_DAYS:
                return f"""
                <aside class="trade-attention warning" role="status">
                    <strong>Empfang steht noch aus</strong>
                    <span>Versendet vor {elapsed_days} Tagen</span>
                </aside>
                """

    if not shipping_status.shipped_for(user_id) and timeline_context:
        due_at = add_business_days(timeline_context.get("accepted_at"))
        if due_at is not None and current_time > due_at:
            return f"""
            <aside class="trade-attention warning" role="status">
                <strong>Versand steht noch aus</strong>
                <span>Fällig seit {sammlr_time_html(due_at.strftime('%Y-%m-%d %H:%M:%S'))}</span>
            </aside>
            """
    return ""


def profile_trade_archive_html(user_id):
    con = get_db()
    albums = con.execute(
        "SELECT id, name FROM albums ORDER BY name COLLATE NOCASE"
    ).fetchall()
    successful_trades = SuccessfulTradeProjectionService(
        con
    ).trades_for_user(user_id)
    partner_ids = tuple(sorted({
        trade.partner_user_id for trade in successful_trades
    }))
    partner_names = {}
    if partner_ids:
        placeholders = ",".join("?" for _ in partner_ids)
        partner_name_select = public_username_select(
            con, "users", "partner_name"
        )
        partner_names = {
            row["id"]: row["partner_name"]
            for row in con.execute(
                f"SELECT users.id, {partner_name_select} "
                f"FROM users WHERE users.id IN ({placeholders})",
                partner_ids,
            ).fetchall()
        }
    con.close()

    archive_by_album = {
        album["id"]: {
            "name": album["name"],
            "trades": []
        }
        for album in albums
    }

    album_names = {album["id"]: album["name"] for album in albums}
    for trade in successful_trades:
        for album_id in trade.involved_album_ids:
            album_trade = SuccessfulTradeProjectionService.trade_for_album(
                trade, album_id
            )
            archive_by_album.setdefault(album_id, {
                "name": album_names.get(album_id, album_id),
                "trades": []
            })
            archive_local_timestamp = format_sammlr_timestamp(
                trade.completed_at
            )
            archive_by_album[album_id]["trades"].append({
                "id": trade.trade_request_id,
                "partner": partner_names.get(
                    trade.partner_user_id, "Gelöschter Nutzer"
                ),
                "date": (
                    archive_local_timestamp.split("|", 1)[0]
                    if archive_local_timestamp
                    else "Zeitpunkt nicht verfügbar"
                ),
                "received": album_trade.received_quantity_total,
                "given": album_trade.given_quantity_total,
            })

    def render_archive_trade(trade_item):
        return f"""
        <div class="profile-trade-row">
            <strong>{trade_item['partner']} · {trade_item['date']}</strong>
            <span>+{trade_item['received']} erhalten · -{trade_item['given']} gegeben</span>
            <a class="trade-detail-link" href="/trades/{trade_item['id']}">Ansehen</a>
        </div>
        """

    archive_html = ""
    for album_archive in archive_by_album.values():
        trades = album_archive["trades"]
        trade_count = len(trades)
        trade_word = "Trade" if trade_count == 1 else "Trades"
        visible_trades = "".join(render_archive_trade(item) for item in trades[:3])
        hidden_trades = "".join(render_archive_trade(item) for item in trades[3:])
        empty_html = """
        <div class="profile-trade-empty">
            Noch keine abgeschlossenen Trades.
        </div>
        """ if not trades else ""
        more_html = f"""
        <details class="profile-trade-more">
            <summary>Mehr anzeigen</summary>
            <div class="profile-trade-list">
                {hidden_trades}
            </div>
        </details>
        """ if hidden_trades else ""

        archive_html += f"""
        <section class="profile-trade-album">
            <div class="profile-trade-album-head">
                <span>{album_archive['name']}</span>
                <strong>{trade_count} {trade_word}</strong>
            </div>
            <div class="profile-trade-list">
                {visible_trades}
                {empty_html}
            </div>
            {more_html}
        </section>
        """

    return archive_html


def klasse_und_text(code, by_code):
    q = by_code[code]["quantity"] if code in by_code else 0
    if q == 0:
        return "missing", display_code(code)
    if q == 1:
        return "owned", display_code(code)
    return "duplicate", f"{display_code(code)}<br>{q}x"


def sticker_card_inner(
    album_id,
    code,
    by_code,
    incoming_transit=0,
    retro_variant=None,
    quantity_badge_multiplier=True,
):
    import re
    q = by_code[code]["quantity"] if code in by_code else 0
    display = display_code(code)
    canonical_code = str(code).strip()
    team = ""
    number = display

    if album_id == "vfl":
        team = "VfL"
        number = display
    else:
        match = re.match(r"^([A-Z]+(?:/[A-Z]+)?)\s+(.+)$", canonical_code)
        if not match:
            match = re.match(r"^([A-Z]+)(\d+)$", display)
        if match:
            team = match.group(1)
            number = match.group(2)

    team_class = "sticker-team" if team else "sticker-team empty"
    quantity_prefix = "×" if quantity_badge_multiplier else ""
    qty_html = (
        f'<span class="sticker-qty">{quantity_prefix}{q}</span>' if q > 1 else ""
    )
    if incoming_transit > 0:
        if q <= 0 and incoming_transit == 1:
            transit_label = "Unterwegs"
        elif q <= 0:
            transit_label = f"{incoming_transit} unterwegs"
        else:
            transit_label = f"+{incoming_transit} unterwegs"
        transit_html = f'<span class="sticker-transit-badge">{transit_label}</span>'
    else:
        transit_html = ""
    if retro_variant and number.isascii() and number.isdigit():
        number_html = sammlr_retro_number_svg(
            number, "wall-number", variant=retro_variant
        )
    elif number.isascii() and number.isdigit():
        number_html = f'<span class="sticker-number">{escape(number)}</span>'
    else:
        identifier_kind = (
            "sticker-identifier-slash"
            if re.fullmatch(r"\d+(?:/\d+)+", number)
            else "sticker-identifier-text"
        )
        identifier_length = (
            "short" if len(number) <= 2 else "medium" if len(number) == 3 else "long"
        )
        number_html = (
            f'<span class="sticker-number {identifier_kind} '
            f'sticker-identifier-{identifier_length}">'
            f'{escape(number)}</span>'
        )
    return f'<span class="{team_class}">{escape(team)}</span>{number_html}{qty_html}{transit_html}'


SAMMLR_RETRO_DIGIT_ASSET = "/static/sammlr-retro-digits.svg"
SAMMLR_RETRO_DIGIT_VARIANTS = {
    "v1": {
        "asset": SAMMLR_RETRO_DIGIT_ASSET,
        "symbol_prefix": "sammlr-digit-",
        "view_box": "0 0 64 104",
        "depth_offset": "3 4",
    },
    "v2": {
        "asset": "/static/sammlr-retro-digits-v2.svg",
        "symbol_prefix": "sammlr-digit-v2-",
        "view_box": "0 0 68 104",
        "depth_offset": "4 5",
    },
    "v3": {
        "asset": "/static/sammlr-retro-digits-v3.svg",
        "symbol_prefix": "sammlr-digit-v3-",
        "view_box": "0 0 68 104",
        "depth_offset": "4 5",
    },
}


def sammlr_retro_number_svg(value, modifier="", variant="v1"):
    number = str(value)
    if not number or not number.isascii() or not number.isdigit():
        raise ValueError("Sammlr retro numbers accept ASCII digits only.")
    if variant not in SAMMLR_RETRO_DIGIT_VARIANTS:
        raise ValueError("Unknown Sammlr retro digit variant.")
    variant_spec = SAMMLR_RETRO_DIGIT_VARIANTS[variant]
    modifier_class = f" {modifier.strip()}" if modifier.strip() else ""
    variant_class = f" variant-{variant}" if variant != "v1" else ""
    glyphs = "".join(
        f"""
        <svg class="sammlr-retro-digit" viewBox="{variant_spec['view_box']}" aria-hidden="true" focusable="false">
            <use class="sammlr-retro-digit-depth" transform="translate({variant_spec['depth_offset']})" href="{variant_spec['asset']}#{variant_spec['symbol_prefix']}{digit}"></use>
            <use class="sammlr-retro-digit-face" href="{variant_spec['asset']}#{variant_spec['symbol_prefix']}{digit}"></use>
        </svg>
        """
        for digit in number
    )
    return (
        f'<span class="sammlr-retro-number{variant_class}{modifier_class}">'
        f'<span class="sammlr-retro-number-text">{escape(number)}</span>'
        f'<span class="sammlr-retro-number-visual" aria-hidden="true">{glyphs}</span>'
        f'</span>'
    )


def sticker_wall_card_inner(album_id, code, by_code, incoming_transit=0):
    return sticker_card_inner(
        album_id,
        code,
        by_code,
        incoming_transit,
        retro_variant="v3",
        quantity_badge_multiplier=False,
    )


def retro_digit_version_html(variant, label, description):
    digit_samples = "".join(
        f'<figure class="retro-digit-sample">{sammlr_retro_number_svg(digit, variant=variant)}'
        f'<figcaption>{digit}</figcaption></figure>'
        for digit in "0123456789"
    )
    combination_samples = "".join(
        f'<figure class="retro-number-sample">{sammlr_retro_number_svg(number, variant=variant)}'
        f'<figcaption>{number}</figcaption></figure>'
        for number in ("00", "12", "14", "17", "20", "41", "47", "71", "74", "88")
    )
    card_specs = (
        ("MEX", "7", "owned", ""),
        ("MEX", "14", "duplicate", '<span class="retro-digit-card-qty">×3</span>'),
        ("GER", "19", "missing", ""),
        ("FWC", "1", "owned", ""),
    )
    card_samples = "".join(
        f"""
        <article class="retro-digit-card {status}" aria-label="Sticker {team} {number}">
            <span class="retro-digit-card-team">{team}</span>
            {sammlr_retro_number_svg(number, "on-card", variant=variant)}
            {quantity_badge}
        </article>
        """
        for team, number, status, quantity_badge in card_specs
    )
    return f"""
    <section class="retro-digit-version retro-digit-version-{variant}" aria-labelledby="retroVersionTitle-{variant}">
        <header class="retro-digit-version-heading">
            <p class="retro-digit-lab-kicker">Original Sammlr Vector Set</p>
            <h1 id="retroVersionTitle-{variant}">{label}</h1>
            <p>{description}</p>
        </header>
        <section class="retro-digit-lab-panel" aria-labelledby="retroDigitSetTitle-{variant}">
            <div class="retro-digit-lab-heading">
                <h2 id="retroDigitSetTitle-{variant}">Ziffern 0–9</h2>
            </div>
            <div class="retro-digit-grid">{digit_samples}</div>
        </section>
        <section class="retro-digit-lab-panel" aria-labelledby="retroCombinationsTitle-{variant}">
            <div class="retro-digit-lab-heading">
                <h2 id="retroCombinationsTitle-{variant}">Mehrstellige Kombinationen</h2>
            </div>
            <div class="retro-number-grid">{combination_samples}</div>
        </section>
        <section class="retro-digit-lab-panel" aria-labelledby="retroCardsTitle-{variant}">
            <div class="retro-digit-lab-heading">
                <h2 id="retroCardsTitle-{variant}">Test auf Kartengröße</h2>
            </div>
            <div class="retro-digit-card-grid">{card_samples}</div>
        </section>
    </section>
    """


@app.route("/dev/retro-ziffern")
def retro_digit_lab():
    version_one = retro_digit_version_html(
        "v1",
        "Entwurf 01",
        "Kantiger, technisch-geometrischer Ausgangsentwurf mit heller Tiefenkante.",
    )
    version_two = retro_digit_version_html(
        "v2",
        "Entwurf 02",
        "Kräftigere Evolution mit längeren Diagonalen, ruhigeren Übergängen und freieren Innenräumen.",
    )
    version_three = retro_digit_version_html(
        "v3",
        "Entwurf 03",
        "Typografischer Feinpass mit optisch leichteren Ziffern 1, 4 und 7; alle übrigen Formen entsprechen Entwurf 02.",
    )
    return f"""
    <html lang="de"><head>{style()}</head>
    <body class="s31-product-page retro-digit-lab-page"><main class="container">
        {app_header("Sammlr Retro-Ziffern · A/B/C", "Isolierter visueller Vergleich · noch nicht auf der Stickerwall aktiv")}
        <a class="sammlr-back-link" href="/sammlung">← Zurück zur Sammlung</a>
        {version_one}
        {version_two}
        {version_three}
    </main></body></html>
    """


def sticker_wall_slot_html(
    album_id,
    code,
    by_code,
    inventory,
    klasse,
    search_text,
    *,
    can_edit_inventory=True,
    detail_href=None,
    max_visible_layers=5,
):
    """Render the canonical wall slot; capabilities only affect its controls."""
    quantity = sticker_quantity_for_counter(by_code, code)
    incoming_transit = (
        inventory.availability_snapshot_for(code).incoming_transit
        if can_edit_inventory
        else 0
    )
    if max_visible_layers not in (5, 10):
        raise ValueError("Only canonical wall/trade caps are supported")
    visible_stack_layers = min(max(quantity, 0), max_visible_layers)
    backing_face = sticker_wall_card_inner(album_id, code, {code: {"quantity": 1}}, 0)
    stack_layers = "".join(
        f'<i class="sticker-wall-stack-layer" data-stack-layer="{layer}" '
        f'style="--stack-index:{layer}" aria-hidden="true">{backing_face}</i>'
        for layer in range(visible_stack_layers - 1)
    )
    display = display_code(code)
    detail_href = detail_href or f"/sticker/{album_id}/{code}"
    controls = ""
    if can_edit_inventory:
        controls = (
            f'<div class="sticker-inline-control" data-inline-control aria-label="Bestand für Sticker {display} ändern">'
            f'<button type="button" data-quantity-delta="-1" aria-label="Sticker {display} entfernen"'
            f'{" disabled" if quantity <= 0 else ""}>−</button>'
            f'<strong data-inline-quantity aria-live="polite">{quantity}</strong>'
            f'<button type="button" data-quantity-delta="1" aria-label="Sticker {display} hinzufügen">+</button>'
            f'<a href="/sticker/{album_id}/{code}" class="sticker-inline-detail" aria-label="Details zu Sticker {display}">Details</a>'
            f'<span class="sticker-inline-error" data-inline-error role="status"></span>'
            f'</div>'
        )
    return (
        f'<div class="sticker-slot-frame" data-sticker-frame '
        f'data-stack-quantity="{quantity}" data-visible-stack-layers="{visible_stack_layers}" '
        f'style="--stack-front-index:{max(visible_stack_layers - 1, 0)}">'
        f'{stack_layers}'
        f'<a class="slot {klasse}" style="--stack-index:{max(visible_stack_layers - 1, 0)}" data-code="{code}" '
        f'data-display="{display}" data-search="{search_text}" '
        f'data-quantity="{quantity}" data-incoming-transit="{incoming_transit}" '
        f'href="{detail_href}" aria-label="Sticker {display}, Bestand {quantity}">'
        f'{sticker_wall_card_inner(album_id, code, by_code, incoming_transit)}'
        f'</a>'
        f'{controls}</div>'
    )


def canonical_sticker_wall_html(
    album_id,
    by_code,
    inventory,
    filter_name,
    *,
    can_edit_inventory,
    trigger="",
    public_detail_base=None,
):
    """Shared owner/read-only chapter, team and slot rendering contract."""
    capability = "edit" if can_edit_inventory else "read-only"
    parts = [
        f'<div class="canonical-sticker-wall" data-sticker-wall-renderer="canonical" '
        f'data-wall-capability="{capability}">'
    ]

    def append_slot(code, context):
        klasse, text = klasse_und_text(code, by_code)
        if not filter_ok(filter_name, code, by_code):
            klasse += " filter-hidden"
        if trigger and compact(code) == compact(trigger):
            klasse += " trigger-slot"
        detail_href = None
        if public_detail_base is not None:
            detail_href = f'{public_detail_base}/sticker/{quote(str(code), safe="")}'
        search_text = f"{code} {text} {context}".lower()
        parts.append(
            sticker_wall_slot_html(
                album_id,
                code,
                by_code,
                inventory,
                klasse,
                search_text,
                can_edit_inventory=can_edit_inventory,
                detail_href=detail_href,
            )
        )

    if album_id == "em24":
        stickers = build_em24()
        section_codes = {}
        for sticker in stickers:
            section_codes.setdefault(sticker["section"], []).append(sticker["id"])
        current_section = None
        for sticker in stickers:
            section = sticker["section"]
            if section != current_section:
                if current_section is not None:
                    parts.append("</div></section>")
                current_section = section
                codes = section_codes[section]
                index = list(section_codes).index(section) + 1
                parts.append(
                    f'<section class="sticker-chapter-block" data-wall-chapter>'
                    f'<h2 id="chapter-em24-{index}" class="section-title album-section-progress-title album-chapter-title" '
                    f'role="button" tabindex="0" aria-expanded="true" {sticker_counter_data_attrs(codes, by_code)}>'
                    f'<i class="chapter-progress-track" aria-hidden="true"><i class="chapter-progress-fill" style="width:{sticker_progress_percent(codes, by_code)}%;"></i></i>'
                    f'<span>{section}</span><span>{sticker_counter_label(codes, by_code, filter_name)}</span></h2>'
                    f'<div class="wall">'
                )
            append_slot(sticker["id"], section)
        if current_section is not None:
            parts.append("</div></section>")

    elif album_id == "vfl":
        for chapter in vfl_wall_chapters():
            title = chapter["title"]
            codes = chapter["codes"]
            chapter_id = "chapter-" + title.lower().replace(" ", "-").replace("/", "-").replace("+", "plus")
            chapter_classes = "section-title album-chapter-title"
            if all(sticker_quantity_for_counter(by_code, code) > 0 for code in codes):
                chapter_classes += " chapter-complete"
            parts.append(
                f'<section class="sticker-chapter-block" data-wall-chapter>'
                f'<h2 id="{chapter_id}" class="{chapter_classes}" role="button" tabindex="0" '
                f'aria-expanded="true" {sticker_counter_data_attrs(codes, by_code)}>'
                f'<i class="chapter-progress-track" aria-hidden="true"><i class="chapter-progress-fill" style="width:{sticker_progress_percent(codes, by_code)}%;"></i></i>'
                f'<span>{title}</span><span>{sticker_counter_label(codes, by_code, filter_name)}</span></h2>'
                f'<div class="wall">'
            )
            for code in codes:
                append_slot(code, title)
            parts.append("</div></section>")

    elif album_id == "wm26":
        stickers = sorted(build_wm26(), key=wm26_wall_order)
        chapter_codes = {}
        team_codes = {}
        for sticker in stickers:
            chapter = wm26_chapter_for_wall(sticker)
            team = wm26_team_for_wall(sticker)
            chapter_codes.setdefault(chapter, []).append(sticker["id"])
            if team:
                team_codes.setdefault(team, []).append(sticker["id"])

        current_chapter = None
        current_team = None
        wall_open = False
        team_open = False
        for sticker in stickers:
            code = sticker["id"]
            chapter = wm26_chapter_for_wall(sticker)
            team = wm26_team_for_wall(sticker)
            if chapter != current_chapter:
                if wall_open:
                    parts.append("</div>")
                    wall_open = False
                if team_open:
                    parts.append("</div>")
                    team_open = False
                if current_chapter is not None:
                    parts.append("</section>")
                current_chapter = chapter
                current_team = None
                codes = chapter_codes[chapter]
                chapter_id = "chapter-" + chapter.lower().replace(" ", "-").replace("/", "-")
                parts.append(
                    f'<section class="sticker-chapter-block" data-wall-chapter>'
                    f'<h2 id="{chapter_id}" class="section-title album-chapter-title" role="button" '
                    f'tabindex="0" aria-expanded="true" {sticker_counter_data_attrs(codes, by_code)}>'
                    f'<i class="chapter-progress-track" aria-hidden="true"><i class="chapter-progress-fill" style="width:{sticker_progress_percent(codes, by_code)}%;"></i></i>'
                    f'<span>{chapter}</span><span>{sticker_counter_label(codes, by_code, filter_name)}</span></h2>'
                )
            if team and team != current_team:
                if wall_open:
                    parts.append("</div>")
                    wall_open = False
                if team_open:
                    parts.append("</div>")
                current_team = team
                team_id = "team-" + team.lower().replace(" ", "-").replace("/", "-")
                parts.append(
                    f'<div class="sticker-team-block"><h3 id="{team_id}" class="team-title" '
                    f'{sticker_counter_data_attrs(team_codes[team], by_code)}>'
                    f'<span>{chapter} · {team}</span>'
                    f'<span>{sticker_counter_label(team_codes[team], by_code, filter_name)}</span></h3>'
                )
                team_open = True
            if not wall_open:
                parts.append('<div class="wall">')
                wall_open = True
            append_slot(code, f"{chapter} {team or ''}")
        if wall_open:
            parts.append("</div>")
        if team_open:
            parts.append("</div>")
        if current_chapter is not None:
            parts.append("</section>")

    else:
        parts.append('<section class="sticker-chapter-block" data-wall-chapter><div class="wall">')
        for code in all_codes(album_id):
            append_slot(code, "")
        parts.append("</div></section>")

    parts.append("</div>")
    return "".join(parts)


def sticker_status_class_for_quantity(quantity):
    if quantity <= 0:
        return "missing"
    if quantity == 1:
        return "owned"
    return "duplicate"


def sticker_status_label_for_quantity(quantity):
    if quantity <= 0:
        return "Fehlt"
    if quantity == 1:
        return "Vorhanden"
    return "Doppelt"


def filter_ok(filter_name, code, by_code):
    q = by_code[code]["quantity"] if code in by_code else 0
    if filter_name == "missing":
        return q == 0
    if filter_name == "owned":
        return q >= 1
    if filter_name == "duplicate":
        return q >= 2
    return True


def album_trophy_preview(album_id, by_code, gesammelt, total):
    con = get_db()
    if canonical_trophy_schema_available(con):
        unlocks = CanonicalTrophyUnlockService(con).unlocks_for_user_album(
            current_user_id(), album_id
        )
        con.close()
        last_line = (
            f"Zuletzt: {unlocks[-1].trophy_name} abgestaubt"
            if unlocks else "Zuletzt: noch keine Trophy"
        )
        return "Weitere Trophäen bleiben geheim.", last_line
    con.close()
    return "Weitere Trophäen bleiben geheim.", "Zuletzt: noch keine Trophy"


def album_completion_title(album):
    labels = {
        "wm26": "WM26 vollendet",
        "em24": "EM24 vollendet",
        "vfl": "VfL vollendet",
    }
    return labels.get(album["id"], f"{album['name']} vollendet")


def album_portal_cards():
    con = get_db()
    albums = con.execute(
        """
        SELECT albums.*
        FROM albums
        JOIN user_albums ON user_albums.album_id = albums.id
        WHERE user_albums.user_id=?
        ORDER BY albums.season DESC, albums.name ASC
        """,
        (current_user_id(),)
    ).fetchall()
    con.close()

    cards = []
    for album in albums:
        _, _, gesammelt, _, _, total = lade_album(album["id"])
        percent = min(100, int((gesammelt / total) * 100)) if total else 0
        if total and gesammelt >= total:
            status = "complete"
            pill_text = "100%"
            status_text = f"Vollständig: {gesammelt} / {total}"
        elif gesammelt > 0:
            status = "active"
            pill_text = "Aktiv"
            status_text = f"Fortschritt: {gesammelt} / {total}"
        else:
            status = "not_started"
            pill_text = "Bereit"
            status_text = f"Noch nicht begonnen: 0 / {total}"

        cards.append({
            "album": album,
            "current": gesammelt,
            "total": total,
            "percent": percent,
            "status": status,
            "pill_text": pill_text,
            "status_text": status_text,
            "icon_key": "wm26_album" if album["id"] == "wm26" else ("vfl_album" if album["id"] == "vfl" else "album_generic"),
        })

    return cards


def render_album_portal_cards(cards):
    if not cards:
        return ""

    html = """
    <section class="sammlr-cabinet-section sammlr-cabinet-albums">
        <h2>Alben</h2>
        <div class="trophy-grid album-awards-grid album-portal-card-grid">
    """

    for card in cards:
        album = card["album"]
        card_class = "trophy-gold" if card["status"] == "complete" else ("trophy-unlocked" if card["status"] == "active" else "trophy-locked trophy-gold-muted")
        pill_class = "gold" if card["status"] == "complete" else ("purple" if card["status"] == "active" else "gray")

        html += f"""
        <a class="trophy trophy-link album-portal-card {card_class}" href="/album/{album['id']}/trophaeen">
            {trophy_icon_svg(card['icon_key'], album['name'], badge_type='sammlr', album_id=album['id'])}
            <h2>{escape(album['name'])}</h2>
            <span class="trophy-pill {pill_class}">{card['pill_text']}</span>
            <p>Album-Trophäenschrank</p>
            <div class="progress trophy-progress" data-progress="{card['percent']}%">
                <div class="progress-bar" style="width:{card['percent']}%;"></div>
            </div>
            <p class="subline">{card['status_text']}</p>
        </a>
        """

    html += "</div></section>"
    return html


def em24_gruppen_trophaeen(by_code):
    gruppen = ["Gruppe A", "Gruppe B", "Gruppe C", "Gruppe D", "Gruppe E", "Gruppe F"]
    result = []

    for gruppe in gruppen:
        sticker_der_gruppe = [s for s in build_em24() if s["section"] == gruppe]

        if not sticker_der_gruppe:
            continue

        erreicht = all(
            s["id"] in by_code and by_code[s["id"]]["quantity"] > 0
            for s in sticker_der_gruppe
        )

        result.append((gruppe, f"{gruppe} gemeistert", erreicht))

    return result

def em24_spezial_trophaeen(by_code):
    sticker = build_em24()

    checks = [
        ("Goldjäger", "Alle SP-Sticker gesammelt", lambda s: "SP" in s["id"]),
        ("Talentscout", "Alle PTW-Sticker gesammelt", lambda s: "PTW" in s["id"]),
        ("Topscout", "Alle TOP-Sticker gesammelt", lambda s: "TOP" in s["id"]),
        ("Legendenstatus", "Alle LEG-Sticker gesammelt", lambda s: "LEG" in s["id"]),
        ("Road to Berlin", "Alle EURO-Sticker gesammelt", lambda s: "EURO" in s["id"]),
    ]

    result = []

    for titel, beschreibung, regel in checks:
        passende = [s for s in sticker if regel(s)]

        if not passende:
            continue

        erreicht = all(
            s["id"] in by_code and by_code[s["id"]]["quantity"] > 0
            for s in passende
        )

        result.append((titel, beschreibung, erreicht))

    return result

def owned_count_for_codes(by_code, codes):
    return len([
        code for code in codes
        if code in by_code and by_code[code]["quantity"] > 0
    ])


def award_item(title, description, current, target, category="Albumziel", icon_key="album_generic"):
    percent = min(100, int((current / target) * 100)) if target else 0
    return {
        "title": title,
        "description": description,
        "current": current,
        "target": target,
        "percent": percent,
        "unlocked": current >= target,
        "category": category,
        "icon_key": icon_key,
    }


def award_item_for_codes(title, description, codes, by_code, category="Kapitel"):
    return award_item(title, description, owned_count_for_codes(by_code, codes), len(codes), category)


def trophy_category(definition):
    trigger_type = definition.get("trigger_type")
    if trigger_type in ("album_count", "album_complete"):
        return "Albumziel"
    if definition.get("name") in ("Wappenexperte", "Teamfotograf", "WM-Historie", "Etikettenknibbler", "The Last Dance", "Weltmeister", "DJ Matze"):
        return "Spezial"
    return "Kapitel"


def trophy_item_from_definition(definition, by_code, gesammelt, total, unlocked_at=None):
    trigger_type = definition["trigger_type"]
    target = definition.get("trigger_value") or len(definition.get("sticker_codes", []))

    if trigger_type in ("album_count", "album_complete"):
        current = gesammelt
    elif trigger_type == "codes":
        current = owned_count_for_codes(by_code, definition.get("sticker_codes", []))
    else:
        current = 0

    item = award_item(
        definition["name"],
        definition["description"],
        current,
        target,
        trophy_category(definition),
        definition.get("icon_key", "album_generic")
    )
    item["id"] = definition["id"]
    item["unlocked_at"] = unlocked_at
    return item


def album_award_items_v1(album_id, by_code, gesammelt, total):
    return [
        trophy_item_from_definition(definition, by_code, gesammelt, total)
        for definition in album_trophy_definitions(album_id, total)
    ]


def trophy_header_lines(icon_key="", label="", badge_type="sammlr"):
    label_text = str(label or "").strip()
    upper = label_text.upper()
    number = "".join(char for char in label_text if char.isdigit())[:5]

    if icon_key == "first_sticker":
        return ["ERSTER", "STICKER"]
    if icon_key == "half_circle" or upper == "HALBZEIT":
        return ["HALBZEIT"]
    if "ALBUM VOLLENDET" in upper or upper == "ALBUM VOLLENDET":
        return ["ALBUM", "VOLLENDET"]
    if icon_key == "global_sticker" and number:
        return [number, "STICKER"]
    if icon_key == "global_duplicates" and number:
        return [number, "DOPPELTE"]
    if icon_key == "global_trades" and number:
        return [number, "TRADE" if number == "1" else "TRADES"]
    if icon_key.startswith("group_") and len(icon_key) == len("group_a"):
        return ["GRUPPE", icon_key[-1].upper()]
    if icon_key == "crest_expert":
        return ["WAPPEN", "EXPERTE"]
    if icon_key == "wm_history":
        return ["WM", "HISTORIE"]
    if icon_key == "wm_champion_cup":
        return ["WELT", "MEISTER"]

    normalized = (
        upper.replace("STICKERJÄGER ", "")
        .replace("STICKERJAEGER ", "")
        .replace("TAUSCHMATERIAL ", "")
        .replace("TAUSCHGESCHÄFTE ", "")
        .replace("TAUSCHGESCHAEFTE ", "")
        .replace("-", " ")
    )
    words = [word for word in normalized.split() if word]

    if len(words) <= 1:
        return [normalized or "TROPHY"]
    if len(words) == 2:
        return words

    midpoint = (len(words) + 1) // 2
    return [" ".join(words[:midpoint]), " ".join(words[midpoint:])]


def trophy_header_text_svg(lines):
    header_axis_x = 1025
    text_attrs = (
        'fill="#6B3DF2" font-family="Inter, Arial, sans-serif" font-weight="900" '
        'letter-spacing="13" paint-order="stroke fill" stroke="#6B3DF2" '
        'stroke-width="1.8" stroke-linejoin="round" text-anchor="middle" '
        'dominant-baseline="middle"'
    )
    safe_lines = [escape(line) for line in lines[:2]]
    if len(safe_lines) == 1:
        text = safe_lines[0]
        font_size = 190 if len(text) > 10 else 220
        return f'<text {text_attrs} x="{header_axis_x}" y="625" font-size="{font_size}">{text}</text>'

    top, bottom = safe_lines
    longest = max(len(top), len(bottom))
    font_size = 188 if longest > 12 else 220
    return (
        f'<text {text_attrs} x="{header_axis_x}" y="500" font-size="{font_size}">{top}</text>'
        f'<text {text_attrs} x="{header_axis_x}" y="750" font-size="{font_size}">{bottom}</text>'
    )


def trophy_header_line_length(lines):
    safe_lines = [str(line or "").strip().upper() for line in lines[:2] if str(line or "").strip()]
    if not safe_lines:
        return 0

    longest = max(len(line) for line in safe_lines)
    font_size = 188 if longest > 12 else 220
    letter_spacing = 13
    glyph_widths = {
        "A": 0.66, "B": 0.65, "C": 0.65, "D": 0.68, "E": 0.59,
        "F": 0.55, "G": 0.69, "H": 0.68, "I": 0.29, "J": 0.43,
        "K": 0.64, "L": 0.53, "M": 0.86, "N": 0.69, "O": 0.71,
        "P": 0.61, "Q": 0.71, "R": 0.64, "S": 0.61, "T": 0.58,
        "U": 0.68, "V": 0.66, "W": 0.92, "X": 0.64, "Y": 0.63,
        "Z": 0.59, " ": 0.33, "-": 0.35,
    }

    def estimated_width(line):
        glyph_width = sum(glyph_widths.get(char, 0.62) for char in line) * font_size
        spacing_width = max(len(line) - 1, 0) * letter_spacing
        return glyph_width + spacing_width + 4

    widths = sorted((estimated_width(line) for line in safe_lines), reverse=True)
    effective_width = widths[0]
    if len(widths) > 1:
        effective_width += widths[1] * 0.15

    standard_length = 190
    minimum_length = 70
    available_length = min(standard_length, 740 - (effective_width / 2))
    if available_length >= standard_length - 1:
        return standard_length
    return round(available_length, 2) if available_length >= minimum_length else 0


def trophy_header_lines_svg(lines):
    line_length = trophy_header_line_length(lines)
    if not line_length:
        return ""

    left_outer = 120
    right_outer = 1930
    left_inner = left_outer + line_length
    right_inner = right_outer - line_length
    return f"""
                <g id="header_lines" transform="translate(0 625)">
                    <path d="M{left_outer} 0H{left_inner:g}" fill="none" stroke="#6B3DF2" stroke-width="13.2" stroke-linecap="square"/>
                    <path d="M{right_inner:g} 0H{right_outer}" fill="none" stroke="#6B3DF2" stroke-width="13.2" stroke-linecap="square"/>
                </g>
    """


def sammlr_emboss_svg():
    if not os.path.exists(MASTER_LOGO_V1_PATH):
        return f"""
        <g id="master_logo_missing_error">
            <rect x="360" y="714" width="304" height="64" rx="8" fill="#FFF4F4" stroke="#C00000" stroke-width="3"/>
            <text x="512" y="742" fill="#C00000" font-family="Inter, Arial, sans-serif" font-size="18" font-weight="900" text-anchor="middle">MASTERLOGO FEHLT</text>
            <text x="512" y="764" fill="#C00000" font-family="Inter, Arial, sans-serif" font-size="12" font-weight="700" text-anchor="middle">{escape(MASTER_LOGO_V1_FILENAME)}</text>
        </g>
        """

    return """
    <g id="master_logo_v1_blind_emboss" opacity="0.88">
        <image
            href="/design-bible/master-assets/master_logo_v1.png"
            x="425"
            y="708"
            width="174"
            height="174"
            filter="url(#sammlr_png_paper_emboss)"
            preserveAspectRatio="xMidYMid meet"
        />
        <image
            href="/design-bible/master-assets/master_logo_v1.png"
            x="425"
            y="708"
            width="174"
            height="174"
            filter="url(#sammlr_png_purple_dot)"
            preserveAspectRatio="xMidYMid meet"
        />
    </g>
    """


def album_branding_svg(album_id):
    branding_filename = ALBUM_BRANDING_FILENAMES.get(album_id)
    if not branding_filename:
        return ""

    branding_path = os.path.join(MASTER_ASSET_DIR, branding_filename)
    if not os.path.exists(branding_path):
        return f"""
        <g id="album_branding_missing_error">
            <rect x="350" y="714" width="324" height="64" rx="8" fill="#FFF4F4" stroke="#C00000" stroke-width="3"/>
            <text x="512" y="742" fill="#C00000" font-family="Inter, Arial, sans-serif" font-size="18" font-weight="900" text-anchor="middle">ALBUMBRANDING FEHLT</text>
            <text x="512" y="764" fill="#C00000" font-family="Inter, Arial, sans-serif" font-size="12" font-weight="700" text-anchor="middle">{escape(branding_filename)}</text>
        </g>
        """

    safe_filename = escape(branding_filename)
    if album_id == "wm26":
        return f"""
    <mask id="album_branding_{escape(album_id)}_stamp_mask" maskUnits="userSpaceOnUse" mask-type="alpha" x="437" y="720" width="150" height="150">
        <image
            href="/design-bible/master-assets/{safe_filename}"
            x="437"
            y="720"
            width="150"
            height="150"
            preserveAspectRatio="xMidYMid meet"
        />
    </mask>
    <g id="album_branding_{escape(album_id)}_blind_emboss" opacity="0.88">
        <rect
            x="437"
            y="720"
            width="150"
            height="150"
            fill="#4B2E83"
            filter="url(#album_branding_paper_emboss)"
            mask="url(#album_branding_{escape(album_id)}_stamp_mask)"
        />
    </g>
    """

    return f"""
    <g id="album_branding_{escape(album_id)}_blind_emboss" opacity="0.88" clip-path="url(#album_branding_slot_clip)">
        <image
            href="/design-bible/master-assets/{safe_filename}"
            x="440"
            y="704"
            width="340"
            height="355"
            filter="url(#album_branding_paper_emboss)"
            preserveAspectRatio="xMidYMid meet"
        />
    </g>
    """


def trophy_cover_icon_svg(icon_key, album_id=None):
    if icon_key not in ("vfl_album", "wm26_album"):
        return ""

    branding_filename = ALBUM_COVER_BRANDING_FILENAMES.get(album_id)
    if not branding_filename:
        return ""

    branding_path = os.path.join(MASTER_ASSET_DIR, branding_filename)
    if not os.path.exists(branding_path):
        return ""

    safe_filename = escape(branding_filename)
    icon_id = "vfl_album_cover_icon" if album_id == "vfl" else "wm_album_cover_icon"
    x, y, width, height = (382, 407, 620, 648) if album_id == "vfl" else (290, 390, 460, 310)
    clip_attr = ' clip-path="url(#vfl_cover_slot_clip)"' if album_id == "vfl" else ""
    filter_attr = ' filter="url(#vfl_cover_enamel)"' if album_id == "vfl" else ""
    blend_attr = ' style="mix-blend-mode:multiply"' if album_id == "wm26" else ""
    return f"""
    <g id="{icon_id}"{clip_attr}>
        <image
            href="/design-bible/master-assets/{safe_filename}"
            x="{x}"
            y="{y}"
            width="{width}"
            height="{height}"
            {filter_attr}
            {blend_attr}
            preserveAspectRatio="xMidYMid meet"
        />
    </g>
    """


def master_asset_image(filename, x, y, width, height, extra_attrs=""):
    safe_filename = escape(filename)
    return f"""
        <image
            href="/design-bible/master-assets/{safe_filename}"
            x="{x}"
            y="{y}"
            width="{width}"
            height="{height}"
            preserveAspectRatio="xMidYMid meet"
            {extra_attrs}
        />
    """


def wm26_group_table_asset(icon_key):
    if not icon_key.startswith("group_") or len(icon_key) != len("group_a"):
        return None

    group_letter = icon_key[-1].lower()
    if group_letter not in WM26_GROUP_ASSET_LETTERS:
        return None

    return f"master_group_table_{group_letter}_v1.svg"


def duplicate_stack_count(label):
    number = int("".join(char for char in str(label or "") if char.isdigit()) or "0")
    if number >= 10000:
        return 36
    if number >= 5000:
        return 30
    if number >= 2500:
        return 24
    if number >= 1000:
        return 18
    if number >= 500:
        return 12
    if number >= 250:
        return 8
    if number >= 100:
        return 5
    return 3


def duplicate_sticker_stack_svg(label):
    sticker_player = MASTER_TROPHY_ASSETS["sticker_player"]
    count = duplicate_stack_count(label)
    width = 142
    height = 199
    bottom_y = 675
    top_x = 441
    lower_x = top_x + 7
    layer_spacing = 1.5
    edge_depth = (count - 1) * layer_spacing
    top_y = bottom_y - height - edge_depth
    right_clip_id = f"duplicate_stack_right_edge_clip_{count}"
    bottom_clip_id = f"duplicate_stack_bottom_edge_clip_{count}"
    layers = []

    for index in range(count - 1):
        y = top_y + ((count - 1 - index) * layer_spacing)
        layers.append(master_asset_image(sticker_player, lower_x, y, width, height, f'clip-path="url(#{right_clip_id})"'))
        layers.append(master_asset_image(sticker_player, lower_x, y, width, height, f'clip-path="url(#{bottom_clip_id})"'))

    layers.append(master_asset_image(sticker_player, top_x, top_y, width, height))

    return f"""
        <g id="production_icon_duplicate_stack_{count}" filter="url(#production_icon_depth)" transform="matrix(1.002 0.065 -0.095 0.94 64 2)">
            <defs>
                <clipPath id="{right_clip_id}">
                    <rect x="{top_x + width - 5}" y="{top_y - 2}" width="{12 + edge_depth}" height="{height + edge_depth + 4}"/>
                </clipPath>
                <clipPath id="{bottom_clip_id}">
                    <rect x="{top_x}" y="{top_y + height - 5}" width="{width + 14}" height="{12 + edge_depth}"/>
                </clipPath>
            </defs>
            {''.join(layers)}
        </g>
    """


def trophy_production_icon_svg(icon_key):
    sticker_player = MASTER_TROPHY_ASSETS["sticker_player"]
    album_empty = MASTER_TROPHY_ASSETS["album_empty"]
    album_full = MASTER_TROPHY_ASSETS["album_full"]
    group_table = MASTER_TROPHY_ASSETS["group_table"]
    wm_history = MASTER_TROPHY_ASSETS["wm_history"]
    wm_teamphoto = MASTER_TROPHY_ASSETS["wm_teamphoto"]
    bottle_label = MASTER_TROPHY_ASSETS["bottle_label"]
    wm_champion_cup = MASTER_TROPHY_ASSETS["wm_champion_cup"]

    if icon_key == "first_sticker":
        return f"""
        <g id="production_icon_first_sticker">
            {master_asset_image(album_empty, 222, 330, 580, 386.667, 'filter="url(#production_icon_depth)"')}
            <g transform="translate(222 330) scale(0.483333) translate(235 208) rotate(2.8)">
                {master_asset_image(sticker_player, 0, 0, 72, 100.8)}
            </g>
        </g>
        """

    if icon_key == "half_circle":
        return f"""
        <g id="production_icon_album_half">
            {master_asset_image(album_empty, 222, 330, 580, 386.667, 'filter="url(#production_icon_depth)"')}
            <g clip-path="url(#production_album_half_clip)">
                {master_asset_image(album_full, 222, 330, 580, 386.667)}
            </g>
        </g>
        """

    if icon_key == "finish_line":
        return f"""
        <g id="production_icon_album_endspurt">
            {master_asset_image(album_full, 222, 330, 580, 386.667, 'filter="url(#production_icon_depth)"')}
            <g clip-path="url(#production_album_endspurt_clip)" opacity="0.98">
                {master_asset_image(album_empty, 222, 330, 580, 386.667)}
            </g>
        </g>
        """

    if icon_key == "album_generic":
        return f"""
        <g id="production_icon_album_complete">
            {master_asset_image(album_full, 222, 330, 580, 386.667, 'filter="url(#production_icon_depth)"')}
        </g>
        """

    if icon_key == "group":
        return f"""
        <g id="production_icon_group_table">
            {master_asset_image(group_table, 337, 405, 350, 252, 'filter="url(#production_icon_depth)"')}
        </g>
        """

    if icon_key == "wm_history":
        return f"""
        <g id="production_icon_wm_history">
            {master_asset_image(wm_history, 337, 393, 350, 280)}
        </g>
        """

    if icon_key == "wm_teamphoto":
        return f"""
        <g id="production_icon_wm_teamphoto">
            {master_asset_image(wm_teamphoto, 337, 393, 350, 280)}
        </g>
        """

    if icon_key == "bottle_label":
        return f"""
        <g id="production_icon_bottle_label">
            {master_asset_image(bottle_label, 337, 393, 350, 280)}
        </g>
        """

    if icon_key == "wm_champion_cup":
        return f"""
        <g id="production_icon_wm_champion_cup">
            {master_asset_image(wm_champion_cup, 337, 393, 350, 280)}
        </g>
        """

    group_table_asset = wm26_group_table_asset(icon_key)
    if group_table_asset:
        return f"""
        <g id="production_icon_group_table_{escape(icon_key[-1])}">
            {master_asset_image(group_table_asset, 319.5, 392.5, 385, 277, 'filter="url(#production_icon_depth)"')}
        </g>
        """

    return ""


def trophy_center_icon_svg(icon_key, label="", album_id=None, badge_type="sammlr"):
    cover_icon = trophy_cover_icon_svg(icon_key, album_id)
    if cover_icon:
        return cover_icon
    if badge_type == "sammlr" and icon_key == "global_duplicates":
        return duplicate_sticker_stack_svg(label)
    if badge_type == "album":
        return trophy_cover_icon_svg(icon_key, album_id) or trophy_production_icon_svg(icon_key)
    return ""


def trophy_icon_svg(icon_key, label="", badge_type="sammlr", album_id=None):
    header_text_lines = trophy_header_lines(icon_key, label, badge_type)
    header_text = trophy_header_text_svg(header_text_lines)
    center_icon = trophy_center_icon_svg(icon_key, label, album_id, badge_type)
    is_crest_expert = badge_type == "album" and icon_key == "crest_expert"
    patch_class = " trophy-patch-crest-expert" if is_crest_expert else ""
    crest_expert_img = ""
    if is_crest_expert:
        crest_filename = escape(MASTER_TROPHY_ASSETS["crest_expert"])
        crest_expert_img = f"""
        <img
            class="trophy-crest-expert-img"
            src="/design-bible/master-assets/{crest_filename}"
            alt=""
            draggable="false"
        />
        """
    header_lines = trophy_header_lines_svg(header_text_lines)
    if badge_type == "sammlr":
        bottom_branding = sammlr_emboss_svg()
    elif badge_type == "album":
        bottom_branding = album_branding_svg(album_id)
    else:
        bottom_branding = ""

    return f"""
    <div class="trophy-patch trophy-patch-master{patch_class}" aria-hidden="true">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" role="img" focusable="false">
            <defs>
                <linearGradient id="shield_surface" x1="0.18" y1="0.04" x2="0.82" y2="0.96">
                    <stop offset="0" stop-color="#FFFDF9"/>
                    <stop offset="0.48" stop-color="#FBF7F0"/>
                    <stop offset="0.84" stop-color="#F5EFE6"/>
                    <stop offset="1" stop-color="#FFFDF8"/>
                </linearGradient>
                <linearGradient id="shield_edge" x1="0.16" y1="0.06" x2="0.9" y2="0.96">
                    <stop offset="0" stop-color="#FFFFFF"/>
                    <stop offset="0.5" stop-color="#F4EFE8"/>
                    <stop offset="0.74" stop-color="#FFFDF8"/>
                    <stop offset="1" stop-color="#E8DFD6"/>
                </linearGradient>
                <linearGradient id="shield_inner_line" x1="0.2" y1="0.08" x2="0.8" y2="0.92">
                    <stop offset="0" stop-color="#9B72FF"/>
                    <stop offset="0.5" stop-color="#6B3DF2"/>
                    <stop offset="1" stop-color="#4C1EC8"/>
                </linearGradient>
                <filter id="shield_drop_shadow" x="-12%" y="-10%" width="124%" height="124%">
                    <feDropShadow dx="0" dy="22" stdDeviation="18.5" flood-color="#160536" flood-opacity="0.28"/>
                </filter>
                <filter id="shield_soft_depth" x="-3%" y="-3%" width="106%" height="106%">
                    <feDropShadow dx="0" dy="2.6" stdDeviation="3" flood-color="#FFFFFF" flood-opacity="0.32"/>
                    <feDropShadow dx="0" dy="-2.4" stdDeviation="3.6" flood-color="#D8D0C7" flood-opacity="0.06"/>
                </filter>
                <filter id="paper_texture" x="-2%" y="-2%" width="104%" height="104%">
                    <feTurbulence type="fractalNoise" baseFrequency="1.85" numOctaves="2" seed="27" result="paper_noise"/>
                    <feColorMatrix in="paper_noise" type="matrix" values="0 0 0 0 0.985 0 0 0 0 0.965 0 0 0 0 0.925 0 0 0 0.026 0" result="paper_fibers"/>
                    <feBlend in="SourceGraphic" in2="paper_fibers" mode="multiply"/>
                </filter>
                <clipPath id="album_branding_slot_clip">
                    <rect x="414" y="696" width="196" height="196"/>
                </clipPath>
                <clipPath id="vfl_cover_slot_clip">
                    <rect x="290" y="390" width="460" height="310"/>
                </clipPath>
                <clipPath id="production_album_half_clip">
                    <rect x="222" y="330" width="290" height="386.667"/>
                </clipPath>
                <clipPath id="production_album_endspurt_clip">
                    <rect x="592" y="552" width="45" height="62"/>
                    <rect x="638" y="552" width="45" height="62"/>
                </clipPath>
                <filter id="sammlr_png_paper_emboss" x="-12%" y="-12%" width="124%" height="124%" color-interpolation-filters="sRGB">
                    <feColorMatrix in="SourceGraphic" type="matrix" values="0 0 0 0 0.985 0 0 0 0 0.965 0 0 0 0 0.925 -0.35 -0.35 -0.35 0 1" result="paper_mark"/>
                    <feComponentTransfer in="paper_mark" result="paper_alpha">
                        <feFuncA type="linear" slope="0.63" intercept="-0.018"/>
                    </feComponentTransfer>
                    <feDropShadow in="paper_alpha" dx="0" dy="-1" stdDeviation="0.5" flood-color="#FFFFFF" flood-opacity="0.44" result="emboss_light"/>
                    <feDropShadow in="paper_alpha" dx="1" dy="1.5" stdDeviation="0.72" flood-color="#D8D0C7" flood-opacity="0.26" result="emboss_shadow"/>
                    <feMerge>
                        <feMergeNode in="emboss_shadow"/>
                        <feMergeNode in="paper_alpha"/>
                        <feMergeNode in="emboss_light"/>
                    </feMerge>
                </filter>
                <filter id="album_branding_paper_emboss" x="-12%" y="-12%" width="124%" height="124%" color-interpolation-filters="sRGB">
                    <feColorMatrix in="SourceGraphic" type="matrix" values="0 0 0 0 0.985 0 0 0 0 0.965 0 0 0 0 0.925 -0.425 -0.425 -0.425 0 1" result="paper_mark"/>
                    <feComponentTransfer in="paper_mark" result="paper_alpha">
                        <feFuncA type="linear" slope="0.677" intercept="-0.02"/>
                    </feComponentTransfer>
                    <feDropShadow in="paper_alpha" dx="0" dy="-1" stdDeviation="0.5" flood-color="#FFFFFF" flood-opacity="0.44" result="emboss_light"/>
                    <feDropShadow in="paper_alpha" dx="1" dy="1.5" stdDeviation="0.72" flood-color="#D8D0C7" flood-opacity="0.26" result="emboss_shadow"/>
                    <feMerge>
                        <feMergeNode in="emboss_shadow"/>
                        <feMergeNode in="paper_alpha"/>
                        <feMergeNode in="emboss_light"/>
                    </feMerge>
                </filter>
                <filter id="sammlr_png_purple_dot" x="-4%" y="-4%" width="108%" height="108%" color-interpolation-filters="sRGB">
                    <feColorMatrix in="SourceGraphic" type="matrix" values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 -1.45 0 1.55 0 -0.06" result="purple_only"/>
                    <feComponentTransfer in="purple_only">
                        <feFuncA type="linear" slope="1.8" intercept="-0.08"/>
                    </feComponentTransfer>
                </filter>
                <filter id="vfl_cover_enamel" x="-8%" y="-8%" width="116%" height="116%" color-interpolation-filters="sRGB">
                    <feColorMatrix in="SourceGraphic" type="matrix" values="0 0 0 0 0.42 0 0 0 0 0.24 0 0 0 0 0.95 -0.38 -0.38 -0.38 0 1" result="vfl_mark"/>
                    <feComponentTransfer in="vfl_mark" result="vfl_alpha">
                        <feFuncA type="linear" slope="1.2" intercept="-0.04"/>
                    </feComponentTransfer>
                    <feDropShadow in="vfl_alpha" dx="0" dy="-2" stdDeviation="1" flood-color="#FFFFFF" flood-opacity="0.34" result="top_light"/>
                    <feDropShadow in="vfl_alpha" dx="0" dy="4" stdDeviation="2.2" flood-color="#32106F" flood-opacity="0.2" result="relief_shadow"/>
                    <feMerge>
                        <feMergeNode in="relief_shadow"/>
                        <feMergeNode in="vfl_alpha"/>
                        <feMergeNode in="top_light"/>
                    </feMerge>
                </filter>
                <filter id="production_icon_depth" x="-10%" y="-12%" width="120%" height="126%">
                    <feDropShadow dx="0" dy="11" stdDeviation="8" flood-color="#1A063F" flood-opacity="0.18"/>
                </filter>
            </defs>
            <g id="master_shield_v1">
                <g id="shield_shadow" filter="url(#shield_drop_shadow)">
                    <path d="M217 72H807C847 72 879 104 879 144V184C879 193 886 200 895 200H936C972 200 1000 228 1000 264V360C1000 402 966 436 924 436H914C902 436 892 446 892 458V752C892 786 872 816 841 829L543 956C523 965 501 965 481 956L183 829C152 816 132 786 132 752V458C132 446 122 436 110 436H100C58 436 24 402 24 360V264C24 228 52 200 88 200H129C138 200 145 193 145 184V144C145 104 177 72 217 72Z" fill="#1A063F" opacity="0.155"/>
                </g>
                <g id="shield_outer" filter="url(#shield_soft_depth)">
                    <path d="M217 72H807C847 72 879 104 879 144V184C879 193 886 200 895 200H936C972 200 1000 228 1000 264V360C1000 402 966 436 924 436H914C902 436 892 446 892 458V752C892 786 872 816 841 829L543 956C523 965 501 965 481 956L183 829C152 816 132 786 132 752V458C132 446 122 436 110 436H100C58 436 24 402 24 360V264C24 228 52 200 88 200H129C138 200 145 193 145 184V144C145 104 177 72 217 72Z" fill="url(#shield_edge)"/>
                </g>
                <path d="M225 100H799C823 100 843 120 843 144V200C843 221 860 238 881 238H932C947 238 960 251 960 266V358C960 381 941 400 918 400H892C868 400 848 420 848 444V744C848 763 837 781 819 789L529 913C518 918 506 918 495 913L205 789C187 781 176 763 176 744V444C176 420 156 400 132 400H106C83 400 64 381 64 358V266C64 251 77 238 92 238H143C164 238 181 221 181 200V144C181 120 201 100 225 100Z" fill="url(#shield_surface)" filter="url(#paper_texture)"/>
                <path d="M229 164H795C812 164 826 178 826 195V219C826 238 841 253 860 253H919C929 253 937 261 937 271V361C937 371 929 379 919 379H891C856 379 828 407 828 442V727C828 747 816 765 798 773L528 888C518 892 506 892 496 888L226 773C208 765 196 747 196 727V442C196 407 168 379 133 379H105C95 379 87 371 87 361V271C87 261 95 253 105 253H164C183 253 198 238 198 219V195C198 178 212 164 229 164Z" fill="none" stroke="url(#shield_inner_line)" stroke-width="12" stroke-linejoin="round" stroke-linecap="round"/>
                <path d="M226 100H798C822 100 842 120 842 144" fill="none" stroke="#FFFFFF" stroke-width="10" stroke-linecap="round" opacity="0.2"/>
                <path d="M176 456V733C176 754 187 774 206 783" fill="none" stroke="#FFFFFF" stroke-width="8" stroke-linecap="round" opacity="0.12"/>
            </g>
            {center_icon}
            <g id="master_header_v1" transform="translate(143 86) scale(0.36)">
                {header_lines}
                <g id="header_text">{header_text}</g>
            </g>
            {bottom_branding}
        </svg>
        {crest_expert_img}
    </div>
    """


def trophy_definition_by_name(name, definitions):
    return next((definition for definition in definitions if definition["name"] == name), None)


def album_trophies(album_id, by_code, gesammelt, total):
    if album_id == "vfl":
        return vfl_album_award_items(by_code, gesammelt, total)
    if album_id == "wm26":
        return wm26_trophy_items(by_code, gesammelt, total)
    return album_award_items_v1(album_id, by_code, gesammelt, total)


def render_album_awards(items, album_id):
    visible_items = [item for item in items if item["unlocked"]]

    if not visible_items:
        return """
        <div class="card trade-empty-card">
            <h2>Noch keine Auszeichnung freigeschaltet.</h2>
            <p>Sammle weiter. Freigeschaltete Trophäen erscheinen automatisch hier.</p>
        </div>
        """

    html = """
    <section class="album-awards-section">
        <h2>Album-Trophäen</h2>
        <div class="trophy-grid album-awards-compact-grid">
    """

    for item in visible_items:
        unlocked_at = format_sammlr_date(item.get("unlocked_at"))
        detail_date = escape(unlocked_at or "Gerade eben")

        html += f"""
        <button type="button" class="trophy trophy-unlocked trophy-gold trophy-detail-trigger"
            data-title="{escape(item['title'])}"
            data-date="{detail_date}"
            data-description="{escape(item['description'])}">
            {trophy_icon_svg(item.get('icon_key', 'album_generic'), item['title'], badge_type='album', album_id=album_id)}
            <h2>{escape(item['title'])}</h2>
            <span class="trophy-pill gold">Abgestaubt</span>
        </button>
        """

    html += "</div></section>"

    html += """
    <div class="quick-action-modal trophy-detail-modal" id="trophyDetailModal" style="display:none;">
        <div class="quick-action-card trophy-detail-card">
            <h2 id="trophyDetailTitle"></h2>
            <p class="subline" id="trophyDetailDate"></p>
            <p id="trophyDetailDescription"></p>
            <button type="button" class="popup-button" onclick="document.getElementById('trophyDetailModal').style.display='none'">Schließen</button>
        </div>
    </div>
    <script>
    document.querySelectorAll('.trophy-detail-trigger').forEach(function(card){
        card.addEventListener('click', function(){
            document.getElementById('trophyDetailTitle').textContent = card.dataset.title || '';
            document.getElementById('trophyDetailDate').textContent = card.dataset.date || '';
            document.getElementById('trophyDetailDescription').textContent = card.dataset.description || '';
            document.getElementById('trophyDetailModal').style.display = 'flex';
        });
    });
    </script>
    """
    return html


def wm26_trophy_progress(title, description, codes, by_code, category="Kapitel"):
    current = owned_count_for_codes(by_code, codes)
    target = len(codes)
    percent = min(100, int((current / target) * 100)) if target else 0

    return {
        "title": title,
        "description": description,
        "current": current,
        "target": target,
        "percent": percent,
        "unlocked": current >= target,
        "started": current > 0,
        "description_visible": percent >= 25,
        "category": category,
    }


def wm26_album_trophy_progress(title, description, current, target, category="Albumziel"):
    percent = min(100, int((current / target) * 100)) if target else 0

    return {
        "title": title,
        "description": description,
        "current": current,
        "target": target,
        "percent": percent,
        "unlocked": current >= target,
        "started": current > 0,
        "description_visible": percent >= 25,
        "category": category,
    }


def wm26_trophy_items(by_code, gesammelt, total):
    return album_award_items_v1("wm26", by_code, gesammelt, total)


def render_wm26_trophy_items(items):
    html = ""

    for item in items:
        title = item["title"]
        description = item["description"]
        current = item["current"]
        target = item["target"]
        percent = item["percent"]
        unlocked = item["unlocked"]
        started = item["started"]
        description_visible = item["description_visible"]

        title_html = title if started or unlocked else '<span class="trophy-blurred-title">????????</span>'
        description_html = description if description_visible or unlocked else '<span class="trophy-blurred-title">Beschreibung verborgen</span>'
        card_class = "trophy-unlocked trophy-gold" if unlocked else "trophy-locked trophy-gold-muted"
        pill_class = "gold" if unlocked else "gray"
        pill_text = "Abgestaubt" if unlocked else "Offen"
        status_text = "Abgestaubt" if unlocked else f"{current} / {target}"

        html += f"""
        <div class="trophy {card_class}">
            <span class="trophy-pill {pill_class}">{pill_text}</span>
            <h2>{title_html}</h2>
            <p>{description_html}</p>
            <div class="progress trophy-progress" data-progress="{percent}%">
                <div class="progress-bar" style="width:{percent}%;"></div>
            </div>
            <p class="subline">{status_text}</p>
        </div>
        """

    return html

def erreichte_trophaeen(album_id):
    return erreichte_trophaeen_for_user(album_id, current_user_id())


def erreichte_trophaeen_for_user(album_id, user_id):
    con = get_db()
    if canonical_trophy_schema_available(con):
        unlocks = CanonicalTrophyUnlockService(con).unlocks_for_user_album(
            user_id, album_id
        )
        con.close()
        return [unlock.trophy_name for unlock in unlocks]
    con.close()
    return []


def record_trophy_unlocks(album_id, newly_reached, user_id=None, silent_reached=None, con=None):
    user_id = user_id or current_user_id()
    silent_reached = silent_reached or []
    own_connection = con is None
    con = con or get_db()

    if canonical_trophy_schema_available(con):
        canonical_names = {
            unlock.trophy_name
            for unlock in CanonicalTrophyUnlockService(
                con
            ).unlocks_for_user_album(user_id, album_id)
        } if album_id != GLOBAL_SCOPE else set()
        visible_new = [
            title for title in dict.fromkeys(newly_reached)
            if title and title in canonical_names
        ]
        if own_connection:
            con.close()
        return visible_new

    if own_connection:
        con.close()
    return []


def queue_trophy_popup(album_id, trophy_titles):
    trophy_titles = [title for title in dict.fromkeys(trophy_titles) if title]
    if not trophy_titles:
        return

    popups = session.get("pending_trophy_popups", [])
    if trophy_titles:
        popups.append({
            "album_id": album_id,
            "titles": trophy_titles
        })
    session["pending_trophy_popups"] = popups


def trophy_popup_html(album_id, trophy_titles):
    trophy_titles = [title for title in dict.fromkeys(trophy_titles) if title]
    if not trophy_titles:
        return ""

    trophy_text = "Neue Trophäe freigeschaltet!" if len(trophy_titles) == 1 else f"{len(trophy_titles)} neue Trophäen freigeschaltet!"
    trophy_lines = "<br>".join(escape(title) for title in trophy_titles)
    is_global_popup = album_id == GLOBAL_SCOPE
    is_weltmeister_popup = album_id == "wm26" and "Weltmeister" in trophy_titles
    trophy_link = "/trophaeen" if is_global_popup else f"/album/{album_id}/trophaeen"
    popup_icon = trophy_icon_svg(
        "wm_champion_cup" if is_weltmeister_popup else "album_generic",
        badge_type="sammlr" if is_global_popup else "album",
        album_id=None if is_global_popup else album_id
    )
    return f"""
    <div class="trophy-popup-overlay">
        <div class="trophy-popup">
            <div class="trophy-popup-patch">{popup_icon}</div>
            <h2>Neuer Patch erhalten</h2>
            <p><strong>{trophy_text}</strong><br>{trophy_lines}</p>
            <div class="popup-actions">
                <button type="button" class="popup-button popup-secondary" onclick="this.closest('.trophy-popup-overlay').remove()">Okay</button>
                <a href="{trophy_link}" class="popup-button">Trophäenschrank</a>
            </div>
        </div>
    </div>
    """


def consume_trophy_popup_html(fallback_album_id=None):
    popups = session.pop("pending_trophy_popups", [])
    if not popups:
        return ""

    album_id = popups[0].get("album_id") or fallback_album_id
    titles = []
    for popup in popups:
        titles.extend(popup.get("titles", []))

    if not album_id:
        return ""

    return trophy_popup_html(album_id, titles)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET" and "user_id" in session:
        return redirect("/")

    error = ""

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if (
            len(username) > MAX_USERNAME_LENGTH
            or len(password) > MAX_PASSWORD_LENGTH
        ):
            error = "Benutzername oder Passwort ist falsch."
            status_code = 200
            username = None

        if username is not None:
            con = get_db()
            result = AuthSecurityService(
                con, now_provider=configured_auth_clock()
            ).authenticate(username, password, configured_client_ip())
            con.close()

        if username is not None and result.code == AuthenticationCode.AUTHENTICATED:
            session.clear()
            session.permanent = False
            session["user_id"] = result.user_id
            session["username"] = result.username
            session["auth_version"] = result.auth_version
            session["csrf_token"] = new_csrf_token()
            return redirect("/")

        if username is not None and result.code == AuthenticationCode.REACTIVATION_REQUIRED:
            session.clear()
            session.permanent = False
            session["reactivation_user_id"] = result.user_id
            session["reactivation_username"] = result.username
            session["reactivation_auth_version"] = result.auth_version
            session["reactivation_verified_at"] = int(time.time())
            session["csrf_token"] = new_csrf_token()
            return redirect("/konto/reaktivieren")

        if username is not None and result.code == AuthenticationCode.THROTTLED:
            error = "Anmeldung momentan nicht möglich. Bitte versuche es später erneut."
            status_code = 429
        else:
            error = "Benutzername oder Passwort ist falsch."
            status_code = 200
    else:
        status_code = 200

    error_html = f'<div class="auth-error">{error}</div>' if error else ""

    return f"""
    <html><head>{style()}</head><body class="auth-page"><div class="auth-shell">
        {app_header("Einloggen", "Willkommen zurück bei Sammlr.")}

        <div class="auth-card">
            {error_html}
            <form method="POST" class="auth-form">
                <label>Benutzername</label>
                <input name="username" placeholder="Benutzername" autocomplete="username">

                <label>Passwort</label>
                <input name="password" type="password" placeholder="Passwort" autocomplete="current-password">

                <button type="submit" class="auth-submit">Einloggen</button>
            </form>

            <a class="auth-switch" href="/register">Noch kein Konto? Jetzt registrieren</a>
        </div>
        {compliance_links_html()}
        <div class="auth-watermark" aria-hidden="true">S</div>
    </div></body></html>
    """, status_code


@app.route("/konto/reaktivieren", methods=["GET", "POST"])
def reactivate_account():
    user_id = session.get("reactivation_user_id")
    auth_version = session.get("reactivation_auth_version")
    verified_at = session.get("reactivation_verified_at")
    if (
        user_id is None
        or auth_version is None
        or verified_at is None
        or int(time.time()) - int(verified_at) > 600
    ):
        session.clear()
        return redirect("/login")

    if request.method == "POST":
        con = get_db()
        result = AccountLifecycleService(con).reactivate(user_id, auth_version)
        con.close()
        if result.code != AccountLifecycleCode.REACTIVATED:
            session.clear()
            return redirect("/login")
        username = session.get("reactivation_username", "")
        session.clear()
        session.permanent = False
        session["user_id"] = user_id
        session["username"] = username
        session["auth_version"] = result.auth_version
        session["csrf_token"] = new_csrf_token()
        return redirect("/")

    return f"""
    <html><head>{style()}</head><body class="auth-page"><div class="auth-shell">
        {app_header("Konto reaktivieren", "Aktiviere dein Sammlr-Konto erneut.")}
        <div class="auth-card">
            <form method="POST" class="auth-form">
                <button type="submit" class="auth-submit">Konto reaktivieren</button>
            </form>
            <a class="auth-switch" href="/login">Abbrechen</a>
        </div>
    </div></body></html>
    """
@app.route("/register", methods=["GET", "POST"])
def register():
    error = ""

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password_repeat = request.form.get("password_repeat", "")

        if (
            not username
            or not password
            or password != password_repeat
            or len(name) > MAX_PROFILE_NAME_LENGTH
            or len(username) > MAX_USERNAME_LENGTH
            or len(password) > MAX_PASSWORD_LENGTH
            or len(password_repeat) > MAX_PASSWORD_LENGTH
        ):
            error = "Registrierung nicht möglich. Bitte prüfe deine Angaben."
        else:
            con = get_db()

            try:
                if not auth_schema_available(con):
                    raise sqlite3.IntegrityError("S32 auth schema unavailable")
                con.execute(
                    """
                    INSERT INTO users
                        (name, username, password, password_scheme, auth_version)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    (
                        name,
                        username,
                        canonical_password_hash(password),
                        WERKZEUG_PASSWORD_SCHEME,
                    )
                )
                con.commit()
                con.close()

                return redirect("/login")

            except sqlite3.IntegrityError:
                con.close()
                error = "Registrierung nicht möglich. Bitte prüfe deine Angaben."

    error_html = f'<div class="auth-error">{error}</div>' if error else ""

    return f"""
    <html><head>{style()}</head><body class="auth-page"><div class="auth-shell">
        {app_header("Registrieren", "Starte deine Sammlung mit einem Sammlr-Konto.")}

        <div class="auth-card">
            {error_html}
            <form method="POST" class="auth-form">
                <label>Name</label>
                <input name="name" placeholder="Name" autocomplete="name">

                <label>Benutzername</label>
                <input name="username" placeholder="Benutzername" autocomplete="username">

                <label>Passwort</label>
                <input name="password" type="password" placeholder="Passwort" autocomplete="new-password">

                <label>Passwort wiederholen</label>
                <input name="password_repeat" type="password" placeholder="Passwort wiederholen" autocomplete="new-password">

                <button type="submit" class="auth-submit">Registrieren</button>
            </form>

            <a class="auth-switch" href="/login">Schon registriert? Jetzt einloggen</a>
        </div>
        {compliance_links_html()}
        <div class="auth-watermark" aria-hidden="true">S</div>
    </div></body></html>
    """


@app.route("/datenschutz")
def privacy_notice():
    return f"""
    <html lang="de"><head>{style()}</head><body class="s31-product-page"><main class="container">
        {app_header("Datenschutzerklärung", "Technischer Stand für die Sammlr-Beta.")}
        <section class="card">
            <h2>Welche Daten Sammlr verarbeitet</h2>
            <p>Sammlr verarbeitet Account- und Profildaten, Alben und Stickerbestände,
               Tausch- und Problemhistorie, Bewertungen, Communitybeziehungen,
               Benachrichtigungen, Trophäen, Privacy-Einstellungen sowie technisch
               erforderliche Sicherheits- und Aktivitätsdaten.</p>
            <h2>Wofür die Daten verwendet werden</h2>
            <p>Die Daten werden ausschließlich benötigt, um Sammlung, Tauschaktionen,
               Communityfunktionen, Kontosicherheit und den sicheren Betrieb der
               Anwendung bereitzustellen.</p>
            <h2>Kontrolle über das Konto</h2>
            <p>Angemeldete Nutzer können ihre Daten als JSON exportieren, ihr Konto
               deaktivieren oder nach den geltenden Trade-Schutzregeln endgültig
               anonymisieren. Bestehende Retention- und Backupregeln bleiben bestehen.</p>
            <p><strong>Hinweis:</strong> Diese funktionale Fassung wird vor einer
               öffentlichen Freigabe juristisch final geprüft.</p>
        </section>
        {compliance_links_html()}
    </main></body></html>
    """


@app.route("/impressum")
def legal_notice():
    return f"""
    <html lang="de"><head>{style()}</head><body class="s31-product-page"><main class="container">
        {app_header("Impressum", "Technische Anbieterinformation.")}
        <section class="card">
            <p>Sammlr befindet sich in der Beta-Vorbereitung.</p>
            <p>Die vollständige Anbieterkennzeichnung und der rechtlich verbindliche
               Kontakt werden vor der öffentlichen Freigabe durch den Betreiber
               ergänzt und juristisch geprüft.</p>
            <p>Diese Seite ist eine funktionale technische Grundlage und keine
               juristische Endfassung.</p>
        </section>
        {compliance_links_html()}
    </main></body></html>
    """


@app.route("/datenexport-hinweise")
def data_export_notice():
    return f"""
    <html lang="de"><head>{style()}</head><body class="s31-product-page"><main class="container">
        {app_header("Exporthinweise", "Deine Sammlr-Daten als JSON.")}
        <section class="card">
            <p>Der Datenexport wird ausschließlich für einen angemeldeten Nutzer und
               erst nach erneuter Prüfung des aktuellen Passworts erstellt.</p>
            <p>Das einzelne UTF-8-JSON-Dokument enthält die eigenen Profil-, Account-,
               Sammlungs-, Trade-, Bewertungs-, Community-, Notification-, Trophy-,
               Privacy- und Aktivitätsdaten. Andere Nutzer erscheinen nur als bereits
               notwendige Referenz in eigenen Trades oder Communitybeziehungen.</p>
            <p>Passwort-Hashes, Sessions, CSRF-Token und Anwendungssecrets sind niemals
               Bestandteil des Exports. Der Export wird synchron übertragen und nicht
               als Exportdatei auf dem Server gespeichert.</p>
            <p>Der ausführbare Exportzugang befindet sich ausschließlich im eigenen,
               angemeldeten Profil.</p>
        </section>
        {compliance_links_html()}
    </main></body></html>
    """


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect("/login")


@app.route("/")
def startseite():
    user_id = current_user_id()
    con = get_db()
    feed_items = (
        FeedEventService(con).feed_for_user(user_id, limit=20)
        if feed_event_schema_available(con) else ()
    )

    favorite_row = con.execute(
        """
        SELECT albums.id, albums.name, albums.total
        FROM users
        JOIN user_albums
          ON user_albums.user_id=users.id
         AND user_albums.album_id=users.favorite_album_id
        JOIN albums ON albums.id=user_albums.album_id
        WHERE users.id=?
        """,
        (user_id,),
    ).fetchone()
    favorite_status = None
    if favorite_row is not None:
        album_id = favorite_row["id"]
        codes = all_codes(album_id)
        total = (
            len(codes)
            if album_id in {"em24", "wm26"}
            else int(favorite_row["total"])
        )
        progress = InventoryReadService(con).album(
            user_id, album_id, codes
        ).progress(codes, total)
        favorite_status = {
            "id": album_id,
            "name": favorite_row["name"],
            "collected": progress.collected,
            "total": progress.total,
            "percent": progress.percent,
        }
    con.close()

    def feed_target(item):
        if item.event_type == "sammlr_news":
            return item.news_target_path
        if item.actor_user_id == user_id:
            if item.event_type == "trophy_unlocked":
                return f'/album/{quote(item.album_id, safe="")}/trophaeen'
            return f'/album/{quote(item.album_id, safe="")}'
        if item.event_type == "trophy_unlocked":
            return f'/profil/{quote(item.actor_username, safe="")}'
        return (
            f'/profil/{quote(item.actor_username, safe="")}/album/'
            f'{quote(item.album_id, safe="")}'
        )

    def render_feed_item(item):
        if item.event_type == "sammlr_news":
            source = "Sammlr News"
            title = item.news_title
            description = item.news_body
        else:
            own_event = item.actor_user_id == user_id
            actor = "Du" if own_event else (
                item.actor_display_name or f"@{item.actor_username}"
            )
            source = "Deine Sammlerreise" if own_event else f"@{item.actor_username}"
            if item.event_type == "album_started":
                title = f"{actor} {'hast' if own_event else 'hat'} ein Album begonnen"
                description = item.album_name
            elif item.event_type == "album_completed":
                title = f"{actor} {'hast' if own_event else 'hat'} ein Album vervollständigt"
                description = item.album_name
            else:
                title = f"{actor} {'hast' if own_event else 'hat'} eine besondere Trophäe freigeschaltet"
                description = item.album_name
        body = f"""
            <span class="feed-card-source">{escape(source)}</span>
            <h2>{escape(title)}</h2>
            <p>{escape(description)}</p>
            <time datetime="{escape(item.occurred_at)}">{escape(format_sammlr_date(item.occurred_at))}</time>
        """
        target = feed_target(item)
        if target:
            return (
                f'<a class="feed-card" data-event-type="{escape(item.event_type)}" '
                f'href="{escape(target)}">{body}</a>'
            )
        return (
            f'<article class="feed-card" data-event-type="{escape(item.event_type)}">'
            f'{body}</article>'
        )

    feed_html = "".join(render_feed_item(item) for item in feed_items)
    feed_section = (
        f'<section class="home-current-feed" aria-label="Sammlermomente">'
        f'{feed_html}</section>'
        if feed_html else ""
    )

    favorite_html = ""
    if favorite_status is not None:
        favorite_html = f"""
        <article class="home-concept-card home-album-status-card">
          <div class="home-concept-card-heading">
            <span class="home-concept-eyebrow">Favoritenalbum</span>
            <span class="home-album-status-percent">{favorite_status['percent']}&nbsp;%</span>
          </div>
          <h2>{escape(favorite_status['name'])}</h2>
          <p>Dein Album ist zu {favorite_status['percent']}&nbsp;% komplett.</p>
          <div class="home-album-status-progress" role="progressbar"
               aria-label="Albumfortschritt" aria-valuemin="0" aria-valuemax="100"
               aria-valuenow="{favorite_status['percent']}">
            <span style="width:{favorite_status['percent']}%"></span>
          </div>
          <div class="home-album-status-meta">
            <span><strong>{favorite_status['collected']}</strong> von {favorite_status['total']} Stickern</span>
            <a href="/album/{quote(favorite_status['id'], safe='')}">Album öffnen</a>
          </div>
        </article>
        """

    html = f"""
    <html><head>{style()}</head><body class="s31-product-page s30-reference-page s30-home-page"><div class="container">

    {app_header("Für dich", "Was gerade passiert und was sich für dich lohnt.", variant="compact", foundation=True)}

    <main class="home-concept-shell" aria-label="Deine Sammlerwelt">
        {feed_section}
        <section class="home-concept-grid" aria-label="Für dich">
          <article class="home-concept-card home-opportunity-card">
            <div class="home-concept-card-copy">
              <span class="home-concept-eyebrow">Tauschchance</span>
              <h2>Finde Tauschpartner für deine fehlenden Sticker.</h2>
              <p>Finde Sammler, die dir bei deiner Sammlung weiterhelfen können.</p>
            </div>
            <a class="home-concept-primary-action" href="/trades">Tauschpartner ansehen</a>
          </article>
          {favorite_html}
        </section>
    </main>

    {bottom_nav("sammlr")}
    </div></body></html>
    """
    return html


@app.route("/home")
def home_compatibility_redirect():
    return redirect("/")


@app.route("/zentrale")
@app.route("/sammlr-zentrale")
def collection_compatibility_redirect():
    return redirect("/sammlung")


@app.route("/sammlung")
@serialized_sqlite_projection
def sammlung():
    favorite_album_id = current_favorite_album_id()
    con = get_db()
    projection = CollectionProjectionService(con).for_user(
        current_user_id(), current_user_id()
    )
    album_ids = [album.album_id for album in projection.current_albums]
    totals = {
        row["id"]: int(row["total"])
        for row in con.execute(
            f"SELECT id, total FROM albums WHERE id IN ({', '.join('?' for _ in album_ids)})",
            album_ids,
        ).fetchall()
    } if album_ids else {}
    catalogs = {album_id: all_codes(album_id) for album_id in album_ids}
    inventory_summaries = InventoryReadService(con).collection_summaries(
        current_user_id(), catalogs, totals
    )

    infos = []
    for projected_album in projection.current_albums:
        album = {
            "id": projected_album.album_id,
            "name": projected_album.name,
            "season": projected_album.season,
            "cover": projected_album.cover,
        }
        summary = inventory_summaries[album["id"]]
        progress = summary.progress
        tauschbare_luecken = tauschbare_luecken_count(
            album["id"], connection=con, subject_state=summary.matching_state
        )
        gesammelt = progress.collected
        doppelte = progress.duplicate_quantity
        prozent = progress.percent
        total = progress.total
        infos.append((album, gesammelt, doppelte, prozent, total, tauschbare_luecken))

    con.close()

    if favorite_album_id:
        infos.sort(key=lambda item: 0 if item[0]["id"] == favorite_album_id else 1)

    album_count = len(infos)
    album_count_label = f"{album_count} Album" if album_count == 1 else f"{album_count} Alben"
    html = f"""
    <html><head>{style()}</head><body class="s31-product-page s30-reference-page s30-collection-page uif-foundation uif-collection-page"><div class="container">

    {app_header("Sammlung", "Deine Alben und dein Fortschritt.", variant="compact", foundation=True)}
    {consume_trophy_popup_html(favorite_album_id)}

    <div class="home-section-toolbar collection-section-toolbar">
        <div class="collection-section-heading">
            <h2 class="home-section-title">Aktive Alben</h2>
            <span class="collection-album-count">{album_count_label}</span>
        </div>
        <a class="add-album-button" href="/alben/hinzufuegen"><span aria-hidden="true">+</span>Album hinzufügen</a>
    </div>
    <section class="collection-album-list" aria-label="Aktive Alben">
    """

    if not infos:
        html += """
        <section class="card sammlr-empty-state">
            <h2>Noch keine Alben.</h2>
            <p>Füge dein erstes Album hinzu und starte deine Sammlung.</p>
            <a class="btn" href="/alben/hinzufuegen">Album hinzufügen</a>
        </section>
        """

    for album, gesammelt, doppelte, prozent, total, tauschbare_luecken in infos:
        html += collection_album_card(
            album,
            gesammelt,
            doppelte,
            prozent,
            total,
            tauschbare_luecken,
            is_favorite=(album["id"] == favorite_album_id),
        )

    html += "</section>"

    if projection.historical_completions:
        html += """
        <h2 class="home-section-title">Abgeschlossene Alben</h2>
        """

        for completion in projection.historical_completions:
            html += historical_completion_card(completion)

    html += bottom_nav("sammlung")
    html += "</div></body></html>"
    return html


def historical_completion_card(completion):
    formatted = format_sammlr_timestamp(completion.completed_at)
    completed_date = (
        formatted.split("|", 1)[0]
        if formatted else "Datum nicht verfügbar"
    )
    return f"""
        <a class="card completed-album-card"
           href="/album/{quote(completion.album_id, safe='')}">
            <div>
                <h2>{escape(completion.name)}</h2>
                <p>{escape(str(completion.season))}</p>
            </div>
            <div>
                <strong>Vervollständigt</strong>
                <time datetime="{escape(completion.completed_at)}">
                    Abgeschlossen am {escape(completed_date)}
                </time>
            </div>
        </a>
    """



def current_favorite_album_id():
    con = get_db()
    row = con.execute(
        """
        SELECT users.favorite_album_id
        FROM users
        JOIN user_albums ON user_albums.album_id = users.favorite_album_id
        WHERE users.id=? AND user_albums.user_id=?
        """,
        (current_user_id(), current_user_id())
    ).fetchone()

    if not row:
        row = con.execute(
            "SELECT favorite_album_id FROM users WHERE id=?",
            (current_user_id(),)
        ).fetchone()

        if row and row["favorite_album_id"]:
            con.execute("UPDATE users SET favorite_album_id=NULL WHERE id=?", (current_user_id(),))
            con.commit()
            row = None

    con.close()

    return row["favorite_album_id"] if row and row["favorite_album_id"] else None


def raw_favorite_album_id():
    con = get_db()
    row = con.execute(
        "SELECT favorite_album_id FROM users WHERE id=?",
        (current_user_id(),)
    ).fetchone()
    con.close()

    return row["favorite_album_id"] if row and row["favorite_album_id"] else None


def user_album_rows():
    con = get_db()
    rows = con.execute(
        """
        SELECT albums.*
        FROM albums
        JOIN user_albums ON user_albums.album_id = albums.id
        WHERE user_albums.user_id=?
        ORDER BY albums.season DESC, albums.name ASC
        """,
        (current_user_id(),)
    ).fetchall()
    con.close()
    return rows


def tauschbare_luecken_count(album_id, connection=None, subject_state=None):
    con = connection or get_db()
    owns_connection = connection is None
    inventory = InventoryReadService(con)
    alle_codes = all_codes(album_id)
    if subject_state is None:
        subject_state = inventory.matching_states(
            (current_user_id(),), album_id, alle_codes
        )[current_user_id()]
    if not subject_state.missing_codes:
        if owns_connection:
            con.close()
        return 0
    privacy = album_privacy_service(con)
    pool_user_ids = set(privacy.trade_pool_user_ids(album_id))
    andere_user = con.execute(
        """
        SELECT users.id
        FROM users
        JOIN user_albums ON user_albums.user_id = users.id
        WHERE users.id != ? AND user_albums.album_id = ?
        """,
        (current_user_id(), album_id)
    ).fetchall()
    candidate_ids = {
        int(user["id"]) for user in andere_user
        if current_user_id() in pool_user_ids and user["id"] in pool_user_ids
    }
    interactable_ids = CommunityService(con).interactable_user_ids(
        current_user_id(), candidate_ids
    )
    andere_user = [
        user for user in andere_user if int(user["id"]) in interactable_ids
    ]

    availability_projection = inventory.album_market_projection(
        current_user_id(),
        [user["id"] for user in andere_user],
        album_id,
        alle_codes,
        subject_state=subject_state,
    )

    if owns_connection:
        con.close()
    return len(availability_projection.market_codes)


def album_trade_preview_counts(album_id):
    con = get_db()
    inventory = InventoryReadService(con)
    privacy = album_privacy_service(con)
    pool_user_ids = set(privacy.trade_pool_user_ids(album_id))
    andere_user = con.execute(
        """
        SELECT users.id
        FROM users
        JOIN user_albums ON user_albums.user_id = users.id
        WHERE users.id != ? AND user_albums.album_id = ?
        """,
        (current_user_id(), album_id)
    ).fetchall()
    andere_user = [
        user for user in andere_user
        if (
            current_user_id() in pool_user_ids
            and user["id"] in pool_user_ids
        )
    ]

    alle_codes = all_codes(album_id)
    availability_projection = inventory.album_market_projection(
        current_user_id(),
        [user["id"] for user in andere_user],
        album_id,
        alle_codes,
    )
    direct_partner_count = sum(
        bool(availability_projection.get_codes_by_user[user["id"]])
        and bool(availability_projection.give_codes_by_user[user["id"]])
        for user in andere_user
    )

    con.close()
    return len(availability_projection.market_codes), direct_partner_count


def album_card(album, gesammelt, doppelte, prozent, total, tauschbare_luecken, is_favorite=False):
    if tauschbare_luecken > 0:
        dritte_text = f"<strong>{tauschbare_luecken}</strong><span>fehlende erhältlich</span>"
    else:
        dritte_text = "<strong>Keine</strong><span>fehlenden erhältlich</span>"

    favorite_class = " is-favorite" if is_favorite else ""
    favorite_badge = '<span class="album-favorite-slot" aria-label="Favoritenalbum"></span>' if is_favorite else ""

    return f"""
        <a class="album-card home-album-card{favorite_class}" href="/album/{album['id']}">
            {favorite_badge}
            <div class="album-cover">{album['cover']}</div>
            <div class="home-album-main">
                <h2>{album['name']}</h2>
                <p class="album-season">{album['season']}</p>
                <div class="progress home-album-progress" data-progress="{prozent}%"><div class="progress-bar" style="width:{prozent}%;"></div></div>
                <div class="home-album-stats">
                    <div><strong>{gesammelt}/{total}</strong><span>Sticker</span></div>
                    <div><strong>{doppelte}</strong><span>Doppelte</span></div>
                    <div>{dritte_text}</div>
                </div>
            </div>
        </a>
    """


def collection_album_meta(album):
    """Return only an existing, clearly additional season label."""

    title = str(album.get("name") or "").strip()
    season = str(album.get("season") or "").strip()
    if not season or season.casefold() in title.casefold():
        return ""
    if not re.fullmatch(r"\d{4}\s*[/–-]\s*\d{2,4}", season):
        return ""
    return season


def collection_album_card(
    album,
    gesammelt,
    doppelte,
    prozent,
    total,
    tauschbare_luecken,
    is_favorite=False,
):
    album_id = quote(str(album["id"]), safe="")
    album_name = escape(str(album["name"]))
    meta = collection_album_meta(album)
    meta_html = (
        f'<p class="collection-album-meta">{escape(meta)}</p>' if meta else ""
    )
    favorite_class = " is-favorite" if is_favorite else ""
    favorite_label = (
        "Favoritenalbum ändern" if is_favorite else "Als Favoritenalbum auswählen"
    )
    favorite_icon = "★" if is_favorite else "☆"
    availability_html = (
        f"<strong>{tauschbare_luecken}</strong><span>fehlende verfügbar</span>"
        if tauschbare_luecken > 0
        else "<strong>Keine</strong><span>fehlenden erhältlich</span>"
    )
    progress_text = escape(str(prozent))

    return f"""
        <article class="collection-album-card-shell{favorite_class}">
            <a class="album-card home-album-card collection-album-card{favorite_class}" href="/album/{album_id}">
                <div class="album-cover collection-album-cover">{album['cover']}</div>
                <div class="home-album-main collection-album-main">
                    <div class="collection-album-heading">
                        <h2>{album_name}</h2>
                        {meta_html}
                    </div>
                    <div class="collection-progress-summary">
                        <span>{gesammelt} von {total} Stickern</span>
                        <strong>{progress_text}&nbsp;%</strong>
                    </div>
                    <div class="collection-progress" role="progressbar" aria-label="Albumfortschritt" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{progress_text}">
                        <span class="collection-progress-fill" style="width:{progress_text}%;"></span>
                    </div>
                    <div class="home-album-stats collection-album-stats">
                        <div><strong>{gesammelt}</strong><span>Sticker</span></div>
                        <div><strong>{doppelte}</strong><span>Doppelte</span></div>
                        <div>{availability_html}</div>
                    </div>
                </div>
            </a>
            <a class="collection-favorite-control{favorite_class}" href="/favorit?auswahl=1" aria-label="{favorite_label}" title="{favorite_label}">
                <span aria-hidden="true">{favorite_icon}</span>
            </a>
        </article>
    """


def favorite_album_choice_card(album, is_favorite=False):
    _, _, gesammelt, doppelte, prozent, total = lade_album(album["id"])
    tauschbare_luecken = tauschbare_luecken_count(album["id"])
    if tauschbare_luecken > 0:
        dritte_text = f"<strong>{tauschbare_luecken}</strong><span>fehlende erhältlich</span>"
    else:
        dritte_text = "<strong>Keine</strong><span>fehlenden erhältlich</span>"

    favorite_class = " is-favorite" if is_favorite else ""
    button_text = "Favorit entfernen" if is_favorite else "Als Favorit setzen"
    favorite_badge = '<span class="album-favorite-slot" aria-hidden="true"></span>' if is_favorite else ""

    return f"""
        <div class="album-card home-album-card favorite-choice-card{favorite_class}">
            <form class="favorite-choice-link" method="POST" action="/favorit/toggle/{album['id']}">
                <button class="favorite-choice-card-button" type="submit">
                {favorite_badge}
                <div class="album-cover">{album['cover']}</div>
                <div class="home-album-main">
                    <h2>{album['name']}</h2>
                    <p class="album-season">{album['season']}</p>
                    <div class="progress home-album-progress" data-progress="{prozent}%"><div class="progress-bar" style="width:{prozent}%;"></div></div>
                    <div class="home-album-stats">
                        <div><strong>{gesammelt}/{total}</strong><span>Sticker</span></div>
                        <div><strong>{doppelte}</strong><span>Doppelte</span></div>
                        <div>{dritte_text}</div>
                    </div>
                </div>
                </button>
            </form>
            <form class="favorite-choice-form" method="POST" action="/favorit/toggle/{album['id']}">
                <button type="submit" class="favorite-set-button">{button_text}</button>
            </form>
        </div>
    """


# --- Bottom Navigation ---
def trade_icon_svg(extra_class=""):
    extra_class = f" {extra_class}" if extra_class else ""
    return f"""
            <svg class="bottom-nav-icon bottom-nav-icon-handshake{extra_class}" viewBox="0 0 24 24" aria-hidden="true">
                <path class="trade-arrow-filled" d="M7 5.1h7.8V2.8l6.3 4.5-6.3 4.5V9.5H7Z"></path>
                <path d="M17 18.9H9.2v2.3l-6.3-4.5 6.3-4.5v2.3H17Z"></path>
            </svg>
        """


def bottom_nav(active="sammlr"):
    icons = {
        "sammlung": """
            <img class="bottom-nav-icon bottom-nav-icon-collection" src="/static/Stickeralbum.svg" alt="">
        """,
        "sammlr": """
            <svg class="bottom-nav-icon bottom-nav-icon-sammlr" viewBox="0 0 28 28" aria-hidden="true">
                <defs>
                    <mask id="sammlrBackCardMask">
                        <rect x="0" y="0" width="28" height="28" fill="white"></rect>
                        <rect x="7.35" y="6.05" width="16.7" height="17.6" rx="3.9" fill="black"></rect>
                    </mask>
                </defs>
                <rect class="sammlr-card-back" x="4.2" y="2.9" width="15.4" height="16.5" rx="3.2" transform="rotate(-10 11.9 11.15)" mask="url(#sammlrBackCardMask)"></rect>
                <rect class="sammlr-card-front" x="8.1" y="6.8" width="15.2" height="16.1" rx="3.2"></rect>
                <text class="sammlr-card-s" x="15.05" y="18.55" text-anchor="middle">S</text>
                <circle class="bottom-nav-icon-dot sammlr-card-dot" cx="19.25" cy="18.45" r="1.35"></circle>
            </svg>
        """,
        "tauschen": trade_icon_svg(),
    }
    items = [
        ("sammlung", "/sammlung", "Sammlung"),
        ("sammlr", "/", "sammlr"),
        ("tauschen", "/tauschen", "Tauschen"),
    ]

    links = ""
    for key, href, label in items:
        active_class = " active" if key == active else ""
        current_attribute = ' aria-current="page"' if key == active else ""
        label_html = '<span>sammlr<span class="bottom-nav-brand-dot">.</span></span>' if key == "sammlr" else f'<span>{label}</span>'
        links += f'<a class="bottom-nav-link{active_class}" href="{href}"{current_attribute}>{icons[key]}{label_html}</a>'

    return f"""
    <nav class="bottom-nav">{links}</nav>
    <script>
    function s31CloseOverlaysOnEscape(event){{
        if(event.key !== 'Escape') return;

        document.querySelectorAll('.quick-action-modal').forEach(function(modal){{
            if(modal.style.display && modal.style.display !== 'none'){{
                modal.style.display = 'none';
                modal.setAttribute('aria-hidden', 'true');
            }}
        }});

        const accountDialog = document.getElementById('accountDeleteDialog');
        if(accountDialog && accountDialog.classList.contains('active')){{
            accountDialog.classList.remove('active');
            accountDialog.setAttribute('aria-hidden', 'true');
        }}
    }}
    document.addEventListener('keydown', s31CloseOverlaysOnEscape);
    </script>
    """


@app.route("/favorit")
def favorit():
    favorite_album_id = current_favorite_album_id()
    show_selection = request.args.get("auswahl") == "1"
    alben = user_album_rows()
    favorite_alben = [album for album in alben if album["id"] == favorite_album_id]

    html = f"""
    <html><head>{style()}</head><body class="s31-product-page"><div class="container">
    {app_header("Favoritenalbum", "Dein schneller Zugriff auf ein Album.")}
    """

    if favorite_alben:
        html += """
        <div class="home-section-toolbar favorite-toolbar">
            <h2 class="home-section-title">Favoritenalbum</h2>
            <a class="favorite-change-button" href="/favorit?auswahl=1">Favorit ändern</a>
        </div>
        """
        album = favorite_alben[0]
        _, _, gesammelt, doppelte, prozent, total = lade_album(album["id"])
        html += album_card(album, gesammelt, doppelte, prozent, total, tauschbare_luecken_count(album["id"]), is_favorite=True)
    else:
        html += """
        <div class="home-section-toolbar favorite-toolbar">
            <h2 class="home-section-title">Kein Favoritenalbum ausgewählt</h2>
            <a class="favorite-change-button" href="/favorit?auswahl=1">Hinzufügen</a>
        </div>
        <div class="card favorite-placeholder">
            <p>Wähle ein Album aus, das du besonders schnell erreichen möchtest.</p>
        </div>
        """

    if show_selection and alben:
        html += '<h2 class="home-section-title">Favoritenalbum auswählen</h2>'
        html += '<div class="favorite-choice-grid">'
        for album in alben:
            html += favorite_album_choice_card(album, is_favorite=(album["id"] == favorite_album_id))
        html += '</div>'
    elif show_selection:
        html += """
        <div class="card favorite-placeholder">
            <h2>Noch keine Alben</h2>
            <p>Füge zuerst ein Album hinzu, bevor du ein Favoritenalbum setzt.</p>
            <a class="btn" href="/sammlung">Zurück zu Alben</a>
        </div>
        """

    html += bottom_nav("sammlung")
    html += "</div></body></html>"
    return html


@app.route("/favorit/toggle/<album_id>", methods=["POST"])
def favorit_toggle(album_id):
    con = get_db()
    album = con.execute(
        """
        SELECT albums.id
        FROM albums
        JOIN user_albums ON user_albums.album_id = albums.id
        WHERE albums.id=? AND user_albums.user_id=?
        """,
        (album_id, current_user_id())
    ).fetchone()
    current = con.execute(
        "SELECT favorite_album_id FROM users WHERE id=?",
        (current_user_id(),)
    ).fetchone()

    if album:
        next_value = None if current and current["favorite_album_id"] == album_id else album_id
        con.execute(
            "UPDATE users SET favorite_album_id=? WHERE id=?",
            (next_value, current_user_id())
        )
        con.commit()

    con.close()
    return redirect("/favorit")


@app.route("/favorit/setzen/<album_id>", methods=["POST"])
def favorit_setzen(album_id):
    con = get_db()
    album = con.execute(
        """
        SELECT albums.id
        FROM albums
        JOIN user_albums ON user_albums.album_id = albums.id
        WHERE albums.id=? AND user_albums.user_id=?
        """,
        (album_id, current_user_id())
    ).fetchone()

    if album:
        con.execute(
            "UPDATE users SET favorite_album_id=? WHERE id=?",
            (album_id, current_user_id())
        )
        con.commit()

    con.close()
    return redirect("/favorit")


def album_bottom_nav(album_id, active="uebersicht"):
    items = [
        ("uebersicht", f"/album/{album_id}", "Übersicht"),
        ("tauschen", f"/album/{album_id}/trades", "Tauschen"),
        ("trophaeen", f"/album/{album_id}/trophaeen", "Trophäen"),
        ("statistik", f"/album/{album_id}/statistik", "Statistik"),
    ]

    links = ""
    for key, href, label in items:
        active_class = " active" if key == active else ""
        links += f'<a class="bottom-nav-link{active_class}" href="{href}">{label}</a>'

    return f'<nav class="bottom-nav album-bottom-nav">{links}</nav>'



# Album hinzufügen Routen

@app.route("/alben/hinzufuegen")
def alben_hinzufuegen():
    con = get_db()
    alben = con.execute(
        """
        SELECT * FROM albums
        WHERE id NOT IN (
            SELECT album_id FROM user_albums WHERE user_id=?
        )
        """,
        (current_user_id(),)
    ).fetchall()
    con.close()

    html = f"""
    <html><head>{style()}</head><body class="s31-product-page"><div class="container">
    {app_header("Album hinzufügen", "Wähle ein Album aus der Sammlr-Liste.")}
    <a class="sammlr-back-link" href="/sammlung">← Zurück</a>
    """

    if not alben:
        html += """
        <div class="card">
            <h2>Alle verfügbaren Alben sind bereits hinzugefügt.</h2>
            <p>Neue Sammelwelten kommen später dazu.</p>
        </div>
        """

    for album in alben:
        html += f"""
        <div class="card">
            <h2>{album['cover']} {album['name']}</h2>
            <p>{album['season']}</p>
            <form method="POST" action="/alben/hinzufuegen/{album['id']}">
                <button class="btn" type="submit">Hinzufügen</button>
            </form>
        </div>
        """

    html += bottom_nav("sammlung")
    html += "</div></body></html>"
    return html


@app.route("/alben/hinzufuegen/<album_id>", methods=["POST"])
def album_hinzufuegen(album_id):
    con = get_db()
    try:
        if cutover_schema_available(con):
            AlbumHistoryCutoverService(con).add(current_user_id(), album_id)
        else:
            con.execute(
                "INSERT OR IGNORE INTO user_albums (user_id, album_id) VALUES (?, ?)",
                (current_user_id(), album_id),
            )
        con.commit()
    except Exception:
        con.rollback()
        con.close()
        raise
    con.close()
    return redirect("/sammlung")

WM26_TEAM_ORDER = [
    "MEX", "RSA", "KOR", "CZE",
    "CAN", "BIH", "QAT", "SUI",
    "BRA", "MAR", "HAI", "SCO",
    "USA", "PAR", "AUS", "TUR",
    "GER", "CUW", "CIV", "ECU",
    "NED", "JPN", "SWE", "TUN",
    "BEL", "EGY", "IRN", "NZL",
    "ESP", "CPV", "KSA", "URU",
    "FRA", "SEN", "IRQ", "NOR",
    "ARG", "ALG", "AUT", "JOR",
    "POR", "COD", "UZB", "COL",
    "ENG", "CRO", "GHA", "PAN",
]

WM26_GROUP_NAMES = [
    "Gruppe A", "Gruppe B", "Gruppe C", "Gruppe D",
    "Gruppe E", "Gruppe F", "Gruppe G", "Gruppe H",
    "Gruppe I", "Gruppe J", "Gruppe K", "Gruppe L",
]


def wm26_code_prefix(code):
    import re
    match = re.match(r"([A-Z]+)", code)
    return match.group(1) if match else ""


def wm26_code_number(code):
    import re
    match = re.search(r"(\d+)$", code)
    return int(match.group(1)) if match else 0


def wm26_team_code_for_wall(sticker):
    code = sticker["id"]
    return sticker.get("team") or wm26_code_prefix(code)


def wm26_wall_order(sticker):
    code = sticker["id"]

    if code == "00":
        return (0, 0)

    if code.startswith("FWC"):
        number = int(code.replace("FWC", ""))
        if number <= 8:
            return (0, number + 1)
        return (90, number)

    if code.startswith("CC"):
        number = int(code.replace("CC", ""))
        return (100, number)

    team_code = wm26_team_code_for_wall(sticker)
    number = wm26_code_number(code)

    if team_code in WM26_TEAM_ORDER:
        team_index = WM26_TEAM_ORDER.index(team_code)
        group_index = team_index // 4
        team_position = team_index % 4
        return (10 + group_index, team_position, number)

    return (80, team_code, number)


def wm26_chapter_for_wall(sticker):
    code = sticker["id"]

    if code == "00":
        return "World Cup 2026"

    if code.startswith("FWC"):
        number = int(code.replace("FWC", ""))
        return "World Cup 2026" if number <= 8 else "World Cup History"

    if code.startswith("CC"):
        return "Coca-Cola"

    team_code = wm26_team_code_for_wall(sticker)
    if team_code in WM26_TEAM_ORDER:
        group_index = WM26_TEAM_ORDER.index(team_code) // 4
        return WM26_GROUP_NAMES[group_index]

    group = sticker.get("group") or sticker.get("chapter") or sticker.get("section") or "Weitere Sticker"
    group = str(group).replace("Gruppe", "").strip()
    return f"Gruppe {group}"


def wm26_team_for_wall(sticker):
    code = sticker["id"]
    if code == "00" or code.startswith("FWC") or code.startswith("CC"):
        return ""

    return sticker.get("team_name") or wm26_team_code_for_wall(sticker)


def sticker_quantity_for_counter(by_code, code):
    return by_code[code]["quantity"] if code in by_code else 0


def sticker_counter_label(codes, by_code, filter_name):
    total = len(codes)
    owned = len([code for code in codes if sticker_quantity_for_counter(by_code, code) > 0])
    missing = total - owned
    duplicate_extra = sum(max(sticker_quantity_for_counter(by_code, code) - 1, 0) for code in codes)

    if filter_name == "missing":
        return f"{missing} fehlend"

    if filter_name == "owned":
        return f"{owned} vorhanden"

    if filter_name == "duplicate":
        return f"{duplicate_extra} doppelt"

    return f"{owned}/{total}"


def sticker_counter_data_attrs(codes, by_code):
    total = len(codes)
    owned = len([code for code in codes if sticker_quantity_for_counter(by_code, code) > 0])
    missing = total - owned
    duplicate_extra = sum(max(sticker_quantity_for_counter(by_code, code) - 1, 0) for code in codes)

    return (
        f'data-counter-total="{total}" '
        f'data-counter-owned="{owned}" '
        f'data-counter-missing="{missing}" '
        f'data-counter-duplicate="{duplicate_extra}"'
    )


def sticker_progress_percent(codes, by_code):
    if not codes:
        return 0

    owned = len([code for code in codes if sticker_quantity_for_counter(by_code, code) > 0])
    return min(100, int((owned / len(codes)) * 100))


VFL_WALL_CHAPTERS = [
    ("Intro", 1, 2),
    ("Kader", 3, 84),
    ("Rückblick", 85, 95),
    ("Schönste Tore der Saison", 96, 108),
    ("Bremer Brücke", 109, 139),
    ("Trikots", 140, 152),
    ("Choreos", 153, 170),
    ("Historie", 171, 183),
    ("Legendenelf", 184, 195),
    ("Große Spieler", 196, 198),
    ("90+6", 199, 213),
    ("Eules letzter Flug", 214, 225),
    ("Spiele für die Ewigkeit", 226, 243),
    ("Fanshop", 244, 250),
]


def vfl_chapter_codes(start, end):
    return [str(number) for number in range(start, end + 1)]


def vfl_wall_chapters():
    return [
        {
            "title": title,
            "codes": vfl_chapter_codes(start, end),
        }
        for title, start, end in VFL_WALL_CHAPTERS
    ]


def vfl_album_award_items(by_code, gesammelt, total):
    return album_award_items_v1("vfl", by_code, gesammelt, total)


def album_privacy_controls_html(album_id):
    con = get_db()
    service = album_privacy_service(con)
    access = service.access(current_user_id(), album_id)
    con.close()
    if access is None or not service.schema_available:
        return ""
    options = (
        ("private", "Privat"),
        ("friends", "Freunde"),
        ("public", "Öffentlich"),
    )
    option_html = "".join(
        f'<option value="{value}"'
        f'{" selected" if access.visibility == value else ""}>{label}</option>'
        for value, label in options
    )
    checked = " checked" if access.trade_pool_enabled else ""
    return f"""
    <dialog id="albumSettingsDialog" class="album-settings-dialog" aria-labelledby="album-settings-title">
        <div class="album-settings-dialog-head">
            <div>
                <p>Sichtbarkeit &amp; Tradepool</p>
                <h2 id="album-settings-title">Albumeinstellungen</h2>
            </div>
            <button type="button" class="album-settings-close" data-album-settings-close aria-label="Albumeinstellungen schließen">×</button>
        </div>
        <form class="album-privacy-controls" method="POST" action="/album/{quote(album_id, safe='')}/privacy">
            <label for="albumVisibility">Album-Sichtbarkeit</label>
            <select id="albumVisibility" name="visibility">{option_html}</select>
            <label class="album-trade-pool-toggle">
                <input type="checkbox" name="trade_pool_enabled" value="1"{checked}>
                <span>Im Tradepool verwenden</span>
            </label>
            <button class="btn album-settings-save" type="submit">Speichern</button>
        </form>
    </dialog>
    """


@app.route("/album/<album_id>/privacy", methods=["POST"])
def update_album_privacy(album_id):
    visibility = request.form.get("visibility", "")
    if visibility not in ALBUM_VISIBILITIES:
        abort(400)
    con = get_db()
    result = album_privacy_service(con).update(
        current_user_id(),
        current_user_id(),
        album_id,
        visibility,
        request.form.get("trade_pool_enabled") == "1",
    )
    if result.code == AlbumPrivacyUpdateCode.UPDATED:
        con.commit()
        con.close()
        return redirect(f"/album/{album_id}")
    con.rollback()
    con.close()
    if result.code == AlbumPrivacyUpdateCode.INVALID_VISIBILITY:
        abort(400)
    abort(404)

@app.route("/album/<album_id>", methods=["GET", "POST"])
def albumseite(album_id):
    filter_name = request.args.get("filter", "all")
    if filter_name not in ("all", "missing", "owned", "duplicate"):
        filter_name = "all"
    show_album = filter_name in ("all", "album")
    show_duplicates = filter_name in ("all", "duplicates")
    message = request.args.get("message", "")
    focus = request.args.get("focus", "add")
    mode = request.args.get("mode", focus)
    trophy = request.args.get("trophy", "")
    count = request.args.get("count", "1")
    try:
        anzahl = int(count)
    except ValueError:
        anzahl = 1
    trigger = request.args.get("trigger", "")
    smart_prefix_active = request.args.get("smart", "") == "1"
    trophy_popup = consume_trophy_popup_html(album_id)

    con = get_db()
    canonical_trophies = canonical_trophy_schema_available(con)
    con.close()
    if trophy and not canonical_trophies:
        trophy_popup += trophy_popup_html(album_id, trophy.split(",")[:anzahl])

    if request.method == "POST":
        aktion = request.form.get("aktion", "add")
        current_filter = request.form.get("filter", "all")

        if aktion == "trade":
            trade_out_raw = request.form.get("trade_out", "").strip()
            trade_in_raw = request.form.get("trade_in", "").strip()
            vorher_erreicht = erreichte_trophaeen(album_id)

            trade_out = resolve_code(album_id, trade_out_raw) if trade_out_raw else None
            trade_in = resolve_code(album_id, trade_in_raw) if trade_in_raw else None

            if trade_out is None or trade_in is None:
                return redirect(f"/album/{album_id}?filter={current_filter}&message=Tausch-Sticker%20nicht%20vorhanden.&focus=trade")

            con = get_db()
            mutation_key = history_request_event_key("album-paper-trade")

            outgoing = con.execute(
                "SELECT * FROM stickers WHERE user_id=? AND album_id=? AND sticker_code=?",
                (current_user_id(), album_id, trade_out)
            ).fetchone()

            if not outgoing or outgoing["quantity"] <= 0:
                con.close()
                return redirect(f"/album/{album_id}?filter={current_filter}&message=Du%20kannst%20nur%20Sticker%20abgeben,%20die%20du%20besitzt.&focus=trade")

            change_sticker_quantity(
                con, current_user_id(), album_id, trade_out, -1,
                history_event_key=f"{mutation_key}:give:{trade_out}",
                history_source_type="paper_trade",
            )
            change_sticker_quantity(
                con, current_user_id(), album_id, trade_in, 1,
                history_event_key=f"{mutation_key}:receive:{trade_in}",
                history_source_type="paper_trade",
            )

            con.commit()
            con.close()

            nachher_erreicht = erreichte_trophaeen(album_id)
            neue_trophies = record_trophy_unlocks(
                album_id,
                [t for t in nachher_erreicht if t not in vorher_erreicht],
                silent_reached=vorher_erreicht
            )
            queue_trophy_popup(album_id, neue_trophies)

            msg = f"Tausch gespeichert: {display_code(trade_out)} abgegeben, {display_code(trade_in)} eingesammelt."
            return redirect(f"/album/{album_id}?filter={current_filter}&message={quote(msg)}&focus=trade")

        raw = request.form.get("sticker", "").strip()

        if raw:
            code = resolve_code(album_id, raw)

            if code is None:
                return redirect(f"/album/{album_id}?filter={current_filter}&message=Sticker%20nicht%20vorhanden.&focus={aktion}")

            if aktion == "remove":
                return remove(album_id, code)

            return add(album_id, code)

    album, by_code, gesammelt, doppelte, prozent, total = lade_album(album_id)
    inventory = lade_album_inventory(album_id)
    market_missing_count, direct_partner_count = album_trade_preview_counts(album_id)
    incoming_trade_request_count = open_incoming_trade_request_count(album_id)
    trophy_next_line, trophy_last_line = album_trophy_preview(album_id, by_code, gesammelt, total)
    privacy_controls = album_privacy_controls_html(album_id)
    album_settings_trigger = (
        '<button type="button" class="album-settings-trigger" data-album-settings-open '
        'aria-haspopup="dialog" aria-controls="albumSettingsDialog" '
        'aria-label="Albumeinstellungen öffnen">•••</button>'
        if privacy_controls else ""
    )
    market_missing_line = (
        "1 fehlender auf dem Markt"
        if market_missing_count == 1
        else f"{market_missing_count} fehlende auf dem Markt"
    )
    direct_partner_line = (
        "1 direkter Tauschpartner"
        if direct_partner_count == 1
        else f"{direct_partner_count} direkte Tauschpartner"
    )
    trade_badge_html = f'<span class="album-quick-badge">{incoming_trade_request_count}</span>' if incoming_trade_request_count > 0 else ''
    collection_feedback = collection_feedback_html(message)
    html = f"""
    <html><head>{style()}</head><body class="s31-product-page s30-reference-page s30-album-page"><div class="container">
    {app_header()}
    <a class="sammlr-back-link" href="/sammlung">← Zur Sammlung</a>
    <section class="album-hero" aria-labelledby="albumHeroTitle">
        <div class="album-hero-head">
            <div>
                <p class="album-hero-eyebrow">Aktives Album</p>
                <h1 id="albumHeroTitle">{escape(album['name'])}</h1>
            </div>
            {album_settings_trigger}
        </div>
        <div class="album-hero-progress-summary">
            <strong><span id="albumHeroOwnedCount">{gesammelt}</span> <small>/ {total} Sticker</small></strong>
            <span id="albumProgressPercent">{prozent}%</span>
        </div>
        <div class="album-hero-progress" role="progressbar" aria-label="Albumfortschritt" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{prozent}">
            <i id="albumProgressFill" style="width:{prozent}%;"></i>
        </div>
        <div class="album-hero-inventory" aria-label="Album-Bestandsübersicht">
            <span><strong id="albumHeroMissingStat">{total - gesammelt}</strong> fehlen</span>
            <span><strong id="albumHeroDuplicateStat">{doppelte}</strong> doppelt</span>
        </div>
    </section>

    {privacy_controls}

    <script>
    (function(){{
        const dialog = document.getElementById('albumSettingsDialog');
        const openButton = document.querySelector('[data-album-settings-open]');
        const closeButton = document.querySelector('[data-album-settings-close]');
        if(!dialog || !openButton) return;

        openButton.addEventListener('click', function(){{
            if(typeof dialog.showModal === 'function') dialog.showModal();
            else dialog.setAttribute('open', '');
        }});
        if(closeButton) closeButton.addEventListener('click', function(){{
            if(typeof dialog.close === 'function') dialog.close();
            else dialog.removeAttribute('open');
        }});
        dialog.addEventListener('click', function(event){{
            if(event.target !== dialog) return;
            if(typeof dialog.close === 'function') dialog.close();
            else dialog.removeAttribute('open');
        }});
    }})();
    </script>

    {collection_feedback}
    <div class="album-quick-links">
        <a class="album-quick-card" href="/album/{album_id}/liste">
            <svg class="album-quick-icon album-quick-icon-list" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M6.4 4.8h8.8a2 2 0 0 1 2 2v8.8"></path>
                <path d="M5.4 6.2v11.1a2 2 0 0 0 2 2h7"></path>
                <path d="M8.4 9.1h5.6"></path>
                <path d="M8.4 12h4.1"></path>
                <path d="M14.6 18.8l4.4-4.4a1.4 1.4 0 0 1 2 2l-4.4 4.4-2.6.6.6-2.6Z"></path>
            </svg>
            <span class="album-quick-text">
                <strong>Stickerliste</strong>
                <span id="albumMissingQuickStat">{total - gesammelt} fehlend</span>
                <span id="albumDuplicateQuickStat">{doppelte} doppelt</span>
            </span>
        </a>
        <a class="album-quick-card {'has-badge' if incoming_trade_request_count > 0 else ''}" href="/album/{album_id}/trades?tab={'incoming' if incoming_trade_request_count > 0 else 'partners'}">
            {trade_badge_html}
            {trade_icon_svg("album-quick-icon album-quick-icon-trade")}
            <span class="album-quick-text">
                <strong>Tauschbörse</strong>
                <span>{market_missing_line}</span>
                <span>{direct_partner_line}</span>
            </span>
        </a>
        <a class="album-quick-card" href="/album/{album_id}/trophaeen">
            <svg class="album-quick-icon album-quick-icon-trophy" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M7.2 4.4h9.6v3.9a4.8 4.8 0 0 1-9.6 0Z"></path>
                <path d="M7.2 6.2H4.6v1.5a3.4 3.4 0 0 0 3.1 3.4"></path>
                <path d="M16.8 6.2h2.6v1.5a3.4 3.4 0 0 1-3.1 3.4"></path>
                <path d="M12 13.1v3.4"></path>
                <path d="M8.7 19.6h6.6"></path>
                <path d="M10 16.5h4"></path>
            </svg>
            <span class="album-quick-text">
                <strong>Trophäen</strong>
                <span>{trophy_next_line}</span>
                <span>{trophy_last_line}</span>
            </span>
        </a>
    </div>

    <div class="card sticker-wall-card">
    <div class="sticker-wall-controlbar">
        <div class="sticker-wall-headline">
            <h2>Stickerwand</h2>
        </div>
        <div class="sticker-filter-row">
            <a class="sticker-filter-pill {'active' if filter_name == 'all' else ''}" href="/album/{album_id}" data-filter="all">Alle</a>
            <a class="sticker-filter-pill missing {'active' if filter_name == 'missing' else ''}" href="/album/{album_id}?filter=missing" data-filter="missing">Fehlende</a>
            <a class="sticker-filter-pill duplicate {'active' if filter_name == 'duplicate' else ''}" href="/album/{album_id}?filter=duplicate" data-filter="duplicate">Doppelte</a>
        </div>
        <input id="stickerSearch" class="sticker-search" type="search" placeholder="Sticker suchen..." autocomplete="off">
    </div>
    <div id="searchDebugBox" class="search-debug-box" style="display:none;"></div>
    <span id="stickerDetailTransit" hidden aria-hidden="true"></span>

    <p>

        <strong id="visibleStickerCount">
        {total if filter_name == "all" else doppelte if filter_name == "duplicate" else gesammelt if filter_name == "owned" else total - gesammelt}
        </strong>
        Sticker
        </p>
    <div class="sticker-wall-sticky-anchor">
        <div class="sticker-wall-sticky-context" id="stickerWallStickyContext" hidden aria-hidden="true">
            <i class="chapter-progress-track" aria-hidden="true"><i class="chapter-progress-fill" data-sticky-context-progress></i></i>
            <span class="sticker-wall-context-label" data-sticky-context-label></span>
            <span class="sticker-wall-context-counter" data-sticky-context-counter></span>
        </div>
    </div>
    """


    html += canonical_sticker_wall_html(
        album_id,
        by_code,
        inventory,
        filter_name,
        can_edit_inventory=True,
        trigger=trigger,
    )
    html += f'''
    <script>
const stickerSearchInput = document.getElementById('stickerSearch');
const stickerWallAlbumId = '{album_id}';
const stickerWallChapterStateKey = 'sammlr:stickerwall:chapters:' + stickerWallAlbumId;
const stickerWallPositionKey = 'sammlr:stickerwall:position:' + stickerWallAlbumId;
let activeStickerFilter = '{filter_name if filter_name in ("all", "missing", "owned", "duplicate") else "all"}';
let activeInlineStickerSlot = null;
let inlineStickerBusy = false;
let activeStickyContextSource = null;
let stickyContextFrame = null;

function stickerwallStickyTop(){{
    const styles = window.getComputedStyle(document.body);
    const appHeaderOffset = parseFloat(styles.getPropertyValue('--stickerwall-app-header-offset')) || 0;
    const controlHeight = parseFloat(styles.getPropertyValue('--stickerwall-control-height')) || 0;
    return appHeaderOffset + controlHeight;
}}

function stickerwallContextSources(){{
    return Array.from(document.querySelectorAll('.album-chapter-title, .team-title')).filter(function(source){{
        if(source.closest('.collapse-section-hidden')) return false;
        const teamBlock = source.closest('.sticker-team-block');
        const chapterBlock = source.closest('.sticker-chapter-block');
        if(teamBlock && teamBlock.style.display === 'none') return false;
        if(chapterBlock && chapterBlock.style.display === 'none') return false;
        return source.offsetParent !== null || source === activeStickyContextSource;
    }});
}}

function setStickerwallStickyContext(source){{
    const context = document.getElementById('stickerWallStickyContext');
    if(!context || !source) return;

    const sourceChanged = source !== activeStickyContextSource;
    if(sourceChanged){{
        if(activeStickyContextSource){{
            activeStickyContextSource.classList.remove('is-sticky-context-source');
            activeStickyContextSource.removeAttribute('aria-hidden');
        }}

        activeStickyContextSource = source;
        source.classList.add('is-sticky-context-source');
        source.setAttribute('aria-hidden', 'true');
    }}

    const spans = source.querySelectorAll('span');
    const label = context.querySelector('[data-sticky-context-label]');
    const counter = context.querySelector('[data-sticky-context-counter]');
    const sourceProgress = source.querySelector('.chapter-progress-fill');
    const progress = context.querySelector('[data-sticky-context-progress]');
    if(label) label.textContent = spans[0] ? spans[0].textContent : '';
    if(counter) counter.textContent = spans.length ? spans[spans.length - 1].textContent : '';
    if(progress) progress.style.width = sourceProgress ? sourceProgress.style.width : '0%';
    context.classList.toggle('is-collapsible', source.classList.contains('album-chapter-title'));
    context.classList.toggle('chapter-collapsed', source.classList.contains('chapter-collapsed'));
    if(source.classList.contains('album-chapter-title')){{
        context.setAttribute('role', 'button');
        context.setAttribute('tabindex', '0');
        context.setAttribute('aria-expanded', source.getAttribute('aria-expanded') || 'true');
    }} else {{
        context.removeAttribute('role');
        context.removeAttribute('tabindex');
        context.removeAttribute('aria-expanded');
    }}
    context.hidden = false;
    context.setAttribute('aria-hidden', 'false');
}}

function syncStickerwallContext(){{
    stickyContextFrame = null;
    const sources = stickerwallContextSources();
    if(!sources.length){{
        const context = document.getElementById('stickerWallStickyContext');
        if(activeStickyContextSource){{
            activeStickyContextSource.classList.remove('is-sticky-context-source');
            activeStickyContextSource.removeAttribute('aria-hidden');
            activeStickyContextSource = null;
        }}
        if(context){{
            context.hidden = true;
            context.setAttribute('aria-hidden', 'true');
            context.style.transform = '';
        }}
        return;
    }}

    const stickyTop = stickerwallStickyTop();
    let current = sources[0];
    let currentIndex = 0;
    sources.forEach(function(source, index){{
        if(source.getBoundingClientRect().top <= stickyTop){{
            current = source;
            currentIndex = index;
        }}
    }});
    setStickerwallStickyContext(current);

    const context = document.getElementById('stickerWallStickyContext');
    const next = sources[currentIndex + 1];
    let pushOffset = 0;
    if(context && next){{
        const contextHeight = context.getBoundingClientRect().height;
        pushOffset = Math.min(0, next.getBoundingClientRect().top - stickyTop - contextHeight);
        pushOffset = Math.max(-contextHeight, pushOffset);
    }}
    if(context) context.style.transform = 'translateY(' + pushOffset + 'px)';
}}

function scheduleStickerwallContextSync(){{
    if(stickyContextFrame !== null) return;
    stickyContextFrame = requestAnimationFrame(syncStickerwallContext);
}}

function syncStickerwallStickyOffsets(){{
    const controlbar = document.querySelector('.sticker-wall-controlbar');
    if(!controlbar) return;
    const appHeader = document.querySelector('.app-header');
    const appHeaderStyle = appHeader ? window.getComputedStyle(appHeader) : null;
    const appHeaderTop = appHeaderStyle ? (parseFloat(appHeaderStyle.top) || 0) : 0;
    const appHeaderOffset = appHeader
        ? Math.ceil(appHeader.getBoundingClientRect().height + appHeaderTop + 6)
        : 0;
    const controlHeight = Math.ceil(controlbar.getBoundingClientRect().height);
    document.body.style.setProperty('--stickerwall-app-header-offset', appHeaderOffset + 'px');
    document.body.style.setProperty('--stickerwall-control-height', controlHeight + 'px');
    const activeFrame = document.querySelector('[data-sticker-frame].inline-active');
    if(activeFrame) positionInlineStickerControl(activeFrame);
    scheduleStickerwallContextSync();
}}

if('ResizeObserver' in window){{
    const stickyControlbar = document.querySelector('.sticker-wall-controlbar');
    const stickyAppHeader = document.querySelector('.app-header');
    const stickyOffsetObserver = new ResizeObserver(syncStickerwallStickyOffsets);
    if(stickyControlbar) stickyOffsetObserver.observe(stickyControlbar);
    if(stickyAppHeader) stickyOffsetObserver.observe(stickyAppHeader);
}}
window.addEventListener('resize', syncStickerwallStickyOffsets);
window.addEventListener('scroll', scheduleStickerwallContextSync, {{passive:true}});
syncStickerwallStickyOffsets();

function stickerQuantityFromSlot(slot){{
    const value = parseInt(slot.dataset.quantity || '0', 10);
    return Number.isNaN(value) ? 0 : value;
}}

function stickerStatusClassForQuantity(quantity){{
    if(quantity <= 0) return 'missing';
    if(quantity === 1) return 'owned';
    return 'duplicate';
}}

function stickerStatusLabelForQuantity(quantity){{
    if(quantity <= 0) return 'Fehlt';
    if(quantity === 1) return 'Vorhanden';
    return 'Doppelt';
}}

function stickerSlotByCode(code){{
    return Array.from(document.querySelectorAll('.slot[data-code]')).find(function(slot){{
        return slot.dataset.code === code;
    }});
}}

function closeInlineStickerControl(exceptSlot){{
    const wallAnchor = currentWallAnchor();
    let closedControl = false;
    document.querySelectorAll('[data-sticker-frame].inline-active').forEach(function(frame){{
        const slot = frame.querySelector('.slot[data-code]');
        if(slot === exceptSlot) return;
        frame.classList.remove('inline-active');
        closedControl = true;
        if(slot) slot.setAttribute('aria-expanded', 'false');
    }});
    if(activeInlineStickerSlot !== exceptSlot) activeInlineStickerSlot = null;
    const wallCard = document.querySelector('.sticker-wall-card');
    const stillActive = document.querySelector('[data-sticker-frame].inline-active');
    if(wallCard) wallCard.classList.toggle('inline-focus-active', Boolean(stillActive));
    if(closedControl){{
        refreshStickerVisibility();
        requestAnimationFrame(function(){{ restoreWallAnchor(wallAnchor); }});
    }}
}}

function positionInlineStickerControl(frame){{
    if(!frame) return;
    const control = frame.querySelector('[data-inline-control]');
    if(!control) return;
    frame.classList.remove(
        'inline-control-above',
        'inline-control-align-left',
        'inline-control-align-right'
    );
    let controlRect = control.getBoundingClientRect();
    if(controlRect.left < 8){{
        frame.classList.add('inline-control-align-left');
    }}else if(controlRect.right > document.documentElement.clientWidth - 8){{
        frame.classList.add('inline-control-align-right');
    }}
    const bottomNav = document.querySelector('.bottom-nav');
    const bottomNavVisible = bottomNav && window.getComputedStyle(bottomNav).display !== 'none';
    const safeBottom = bottomNavVisible
        ? bottomNav.getBoundingClientRect().top - 8
        : window.innerHeight - 8;
    controlRect = control.getBoundingClientRect();
    if(controlRect.bottom > safeBottom){{
        frame.classList.add('inline-control-above');
    }}
}}

function openInlineStickerControl(slot){{
    if(!slot) return;
    const frame = slot.closest('[data-sticker-frame]');
    if(!frame) return;
    const wasOpen = frame.classList.contains('inline-active');
    closeInlineStickerControl(slot);
    frame.classList.toggle('inline-active', !wasOpen);
    slot.setAttribute('aria-expanded', wasOpen ? 'false' : 'true');
    activeInlineStickerSlot = wasOpen ? null : slot;
    const wallCard = document.querySelector('.sticker-wall-card');
    if(wallCard) wallCard.classList.toggle('inline-focus-active', !wasOpen);
    if(wasOpen){{
        const wallAnchor = currentWallAnchor();
        refreshStickerVisibility();
        requestAnimationFrame(function(){{ restoreWallAnchor(wallAnchor); }});
    }}
    requestAnimationFrame(function(){{
        if(!wasOpen) positionInlineStickerControl(frame);
    }});
}}

function applyStickerPayload(payload){{
    const wallAnchor = currentWallAnchor();
    let slot = stickerSlotByCode(payload.code);
    if(slot){{
        const stackFrame = slot.closest('[data-sticker-frame]');
        const targetIndex = Math.max(Math.min(payload.quantity, 5) - 1, 0);
        let topIndex = Number(slot.style.getPropertyValue('--stack-index')) || 0;
        // Keep existing physical cards anchored; add only the new top card.
        while(stackFrame && topIndex < targetIndex){{
            const next = slot.cloneNode(false);
            slot.className = 'sticker-wall-stack-layer';
            slot.dataset.stackLayer = topIndex;
            slot.removeAttribute('data-code');
            slot.removeAttribute('href');
            slot.removeAttribute('aria-label');
            slot.removeAttribute('aria-expanded');
            slot.setAttribute('aria-hidden', 'true');
            slot.querySelectorAll('.sticker-qty').forEach(function(bubble){{ bubble.remove(); }});
            topIndex += 1;
            next.style.setProperty('--stack-index', topIndex);
            stackFrame.insertBefore(next, slot.nextSibling);
            if(activeInlineStickerSlot === slot) activeInlineStickerSlot = next;
            slot = next;
        }}
        while(stackFrame && topIndex > targetIndex){{
            const previous = stackFrame.querySelector('[data-stack-layer="' + (topIndex - 1) + '"]');
            const attributes = Array.from(slot.attributes);
            Array.from(previous.attributes).forEach(function(attr){{ previous.removeAttribute(attr.name); }});
            attributes.forEach(function(attr){{ previous.setAttribute(attr.name, attr.value); }});
            previous.style.setProperty('--stack-index', topIndex - 1);
            if(activeInlineStickerSlot === slot) activeInlineStickerSlot = previous;
            slot.remove();
            slot = previous;
            topIndex -= 1;
        }}
        slot.dataset.quantity = payload.quantity;
        slot.dataset.display = payload.display;
        slot.dataset.incomingTransit = payload.incomingTransit;
        slot.innerHTML = payload.cardHtml;
        slot.classList.remove('missing', 'owned', 'duplicate');
        slot.classList.add(payload.statusClass);
        slot.setAttribute('aria-label', 'Sticker ' + payload.display + ', Bestand ' + payload.quantity);
        const frame = slot.closest('[data-sticker-frame]');
        if(frame){{
            frame.dataset.stackQuantity = payload.quantity;
            frame.dataset.visibleStackLayers = Math.min(Math.max(payload.quantity, 0), 5);
            const quantityNode = frame.querySelector('[data-inline-quantity]');
            const minus = frame.querySelector('[data-quantity-delta="-1"]');
            if(quantityNode) quantityNode.textContent = payload.quantity;
            if(minus) minus.disabled = payload.quantity <= 0;
        }}
    }}

    if(payload.album){{
        const albumFill = document.getElementById('albumProgressFill');
        const albumPercent = document.getElementById('albumProgressPercent');
        const albumHeroProgress = document.querySelector('.album-hero-progress');
        const albumHeroOwnedCount = document.getElementById('albumHeroOwnedCount');
        const albumHeroMissingStat = document.getElementById('albumHeroMissingStat');
        const albumHeroDuplicateStat = document.getElementById('albumHeroDuplicateStat');
        const missingQuickStat = document.getElementById('albumMissingQuickStat');
        const duplicateQuickStat = document.getElementById('albumDuplicateQuickStat');
        if(albumFill) albumFill.style.width = payload.album.percent + '%';
        if(albumPercent) albumPercent.textContent = payload.album.percent + '%';
        if(albumHeroProgress) albumHeroProgress.setAttribute('aria-valuenow', payload.album.percent);
        if(albumHeroOwnedCount) albumHeroOwnedCount.textContent = payload.album.collected;
        if(albumHeroMissingStat) albumHeroMissingStat.textContent = payload.album.missing;
        if(albumHeroDuplicateStat) albumHeroDuplicateStat.textContent = payload.album.duplicates;
        if(missingQuickStat) missingQuickStat.textContent = payload.album.missing + ' fehlend';
        if(duplicateQuickStat) duplicateQuickStat.textContent = payload.album.duplicates + ' doppelt';
    }}

    recalculateStickerCounterData();
    refreshStickerVisibility();
    requestAnimationFrame(function(){{ restoreWallAnchor(wallAnchor); }});

    if(payload.trophyHtml){{
        const holder = document.createElement('div');
        holder.innerHTML = payload.trophyHtml;
        Array.from(holder.children).forEach(function(node){{
            document.body.appendChild(node);
        }});
    }}
}}

function changeInlineStickerQuantity(slot, delta){{
    if(!slot || inlineStickerBusy) return;
    const frame = slot.closest('[data-sticker-frame]');
    const error = frame ? frame.querySelector('[data-inline-error]') : null;
    inlineStickerBusy = true;
    if(frame) frame.classList.add('inline-busy');
    if(error) error.textContent = '';
    const body = new URLSearchParams();
    body.set('delta', String(delta));
    body.set('_history_mutation_id', sammlrHistoryMutationId());

    fetch('/album/{album_id}/sticker/' + encodeURIComponent(slot.dataset.code || '') + '/quantity', {{
        method: 'POST',
        headers: {{
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').content
        }},
        body: body.toString()
    }})
    .then(function(response){{
        if(!response.ok) throw new Error('Sticker konnte nicht aktualisiert werden.');
        return response.json();
    }})
    .then(function(payload){{
        if(payload && payload.ok){{
            applyStickerPayload(payload);
        }}
    }})
    .catch(function(){{
        if(error) error.textContent = 'Nicht gespeichert';
    }})
    .finally(function(){{
        inlineStickerBusy = false;
        if(frame) frame.classList.remove('inline-busy');
    }});
}}

function slotMatchesActiveFilter(slot){{
    if(activeStickerFilter === 'all') return true;
    if(activeStickerFilter === 'owned') return slot.classList.contains('owned') || slot.classList.contains('duplicate');
    return slot.classList.contains(activeStickerFilter);
}}

function updateVisibleStickerCount(){{
    const count = Array.from(document.querySelectorAll('.slot')).filter(slotIsVisible).length;
    const counter = document.getElementById('visibleStickerCount');
    if(counter) counter.textContent = count;
}}

function stickerCounterNumber(heading, key){{
    const value = parseInt(heading.dataset[key] || '0', 10);
    return Number.isNaN(value) ? 0 : value;
}}

function stickerCounterLabelForHeading(heading){{
    const total = stickerCounterNumber(heading, 'counterTotal');
    const owned = stickerCounterNumber(heading, 'counterOwned');
    const missing = stickerCounterNumber(heading, 'counterMissing');
    const duplicate = stickerCounterNumber(heading, 'counterDuplicate');

    if(activeStickerFilter === 'missing') return missing + ' fehlend';
    if(activeStickerFilter === 'owned') return owned + ' vorhanden';
    if(activeStickerFilter === 'duplicate') return duplicate + ' doppelt';
    return owned + '/' + total;
}}

function updateStickerCounterBadges(){{
    document.querySelectorAll('[data-counter-total]').forEach(function(heading){{
        const spans = heading.querySelectorAll('span');
        const badge = spans[spans.length - 1];
        if(!badge) return;

        badge.textContent = stickerCounterLabelForHeading(heading);
    }});
}}

function stickerWallStickyBottom(){{
    const controlbar = document.querySelector('.sticker-wall-controlbar');
    const stickyContext = document.getElementById('stickerWallStickyContext');
    const controlBottom = controlbar ? controlbar.getBoundingClientRect().bottom : 0;
    const contextBottom = stickyContext && !stickyContext.hidden
        ? stickyContext.getBoundingClientRect().bottom
        : 0;
    return Math.max(controlBottom, contextBottom) + 8;
}}

function wallSlotIsRendered(slot){{
    const frame = slot ? slot.closest('[data-sticker-frame]') : null;
    return Boolean(slot && slotIsVisible(slot) && frame && !frame.hidden && frame.offsetParent !== null);
}}

function currentWallAnchor(){{
    const stickyBottom = stickerWallStickyBottom();
    const allSlots = Array.from(document.querySelectorAll('.slot[data-code]'));
    const visibleSlots = allSlots.filter(wallSlotIsRendered);
    const slot = visibleSlots.find(function(candidate){{
        return candidate.getBoundingClientRect().bottom >= stickyBottom;
    }}) || visibleSlots[visibleSlots.length - 1];
    if(slot){{
        const chapter = slot.closest('.sticker-chapter-block');
        const team = slot.closest('.sticker-team-block');
        return {{
            node:slot,
            top:slot.getBoundingClientRect().top,
            offset:slot.getBoundingClientRect().top - stickyBottom,
            code:slot.dataset.code || '',
            chapterId:(chapter && chapter.querySelector('.album-chapter-title'))
                ? chapter.querySelector('.album-chapter-title').id : '',
            teamId:(team && team.querySelector('.team-title'))
                ? team.querySelector('.team-title').id : '',
            index:allSlots.indexOf(slot)
        }};
    }}

    const headings = Array.from(document.querySelectorAll('.album-chapter-title'))
        .filter(function(heading){{ return heading.offsetParent !== null; }});
    const heading = headings.find(function(candidate){{
        return candidate.getBoundingClientRect().bottom >= stickyBottom;
    }}) || headings[headings.length - 1];
    return heading ? {{
        node:heading,
        top:heading.getBoundingClientRect().top,
        offset:heading.getBoundingClientRect().top - stickyBottom,
        chapterId:heading.id || '',
        index:-1
    }} : null;
}}

function wallAnchorFallback(anchor){{
    if(anchor.code){{
        const exact = stickerSlotByCode(anchor.code);
        if(wallSlotIsRendered(exact)) return exact;
    }}

    const scopes = [anchor.teamId, anchor.chapterId];
    for(const scopeId of scopes){{
        const heading = scopeId ? document.getElementById(scopeId) : null;
        const scope = heading ? heading.parentElement : null;
        const scopedSlot = scope
            ? Array.from(scope.querySelectorAll('.slot[data-code]')).find(wallSlotIsRendered)
            : null;
        if(scopedSlot) return scopedSlot;
    }}

    const allSlots = Array.from(document.querySelectorAll('.slot[data-code]'));
    const visibleSlots = allSlots.filter(wallSlotIsRendered);
    if(visibleSlots.length && Number.isInteger(anchor.index) && anchor.index >= 0){{
        return visibleSlots.reduce(function(nearest, candidate){{
            return Math.abs(allSlots.indexOf(candidate) - anchor.index) < Math.abs(allSlots.indexOf(nearest) - anchor.index)
                ? candidate : nearest;
        }}, visibleSlots[0]);
    }}

    const chapter = anchor.chapterId ? document.getElementById(anchor.chapterId) : null;
    return chapter && chapter.offsetParent !== null ? chapter : null;
}}

function restoreWallAnchor(anchor){{
    if(!anchor) return;
    const currentNodeUsable = anchor.node && (
        anchor.node.matches('.slot[data-code]') ? wallSlotIsRendered(anchor.node) : anchor.node.offsetParent !== null
    );
    const node = currentNodeUsable ? anchor.node : wallAnchorFallback(anchor);
    if(!node) return;
    const targetTop = anchor.node === node && Number.isFinite(anchor.top)
        ? anchor.top
        : stickerWallStickyBottom() + (Number.isFinite(anchor.offset) ? anchor.offset : 8);
    window.scrollBy(0, node.getBoundingClientRect().top - targetTop);
}}

function readStickerWallSession(key){{
    try{{
        const value = window.sessionStorage.getItem(key);
        return value ? JSON.parse(value) : null;
    }}catch(error){{
        return null;
    }}
}}

function writeStickerWallSession(key, value){{
    try{{
        window.sessionStorage.setItem(key, JSON.stringify(value));
    }}catch(error){{
        return;
    }}
}}

function expandedStickerWallChapterIds(){{
    return Array.from(document.querySelectorAll('.album-chapter-title:not(.chapter-collapsed)'))
        .map(function(heading){{ return heading.id; }})
        .filter(Boolean);
}}

function restoreExpandedStickerWallChapters(){{
    const savedIds = readStickerWallSession(stickerWallChapterStateKey);
    if(!Array.isArray(savedIds)) return;
    const expandedIds = new Set(savedIds);
    document.querySelectorAll('.album-chapter-title').forEach(function(heading){{
        heading.classList.toggle('chapter-collapsed', !expandedIds.has(heading.id));
    }});
}}

function persistExpandedStickerWallChapters(){{
    writeStickerWallSession(stickerWallChapterStateKey, expandedStickerWallChapterIds());
}}

function persistStickerWallPosition(){{
    const anchor = currentWallAnchor();
    if(!anchor) return;
    writeStickerWallSession(stickerWallPositionKey, {{
        code:anchor.code || '',
        chapterId:anchor.chapterId || '',
        teamId:anchor.teamId || '',
        index:Number.isInteger(anchor.index) ? anchor.index : -1,
        offset:Number.isFinite(anchor.offset) ? anchor.offset : 8
    }});
}}

function restoreStickerWallPosition(){{
    const savedAnchor = readStickerWallSession(stickerWallPositionKey);
    if(savedAnchor) restoreWallAnchor(savedAnchor);
}}

function recalculateStickerCounterData(){{
    document.querySelectorAll('[data-counter-total]').forEach(function(heading){{
        const scope = heading.classList.contains('team-title')
            ? heading.closest('.sticker-team-block')
            : heading.closest('.sticker-chapter-block');
        if(!scope) return;

        const slots = Array.from(scope.querySelectorAll('.slot[data-code]'));
        const total = slots.length;
        const owned = slots.filter(function(slot){{
            return stickerQuantityFromSlot(slot) >= 1;
        }}).length;
        const duplicate = slots.reduce(function(sum, slot){{
            return sum + Math.max(stickerQuantityFromSlot(slot) - 1, 0);
        }}, 0);

        heading.dataset.counterTotal = total;
        heading.dataset.counterOwned = owned;
        heading.dataset.counterMissing = Math.max(total - owned, 0);
        heading.dataset.counterDuplicate = duplicate;

        const fill = heading.querySelector('.chapter-progress-fill');
        if(fill){{
            const percent = total > 0 ? Math.min(100, Math.floor((owned / total) * 100)) : 0;
            fill.style.width = percent + '%';
        }}
    }});

    updateStickerCounterBadges();
}}

function setActiveStickerFilter(nextFilter, options){{
    const anchor = currentWallAnchor();
    const allowedFilters = ['all', 'missing', 'owned', 'duplicate'];
    activeStickerFilter = allowedFilters.includes(nextFilter) ? nextFilter : 'all';

    document.querySelectorAll('.sticker-filter-pill[data-filter]').forEach(function(pill){{
        const isActive = pill.dataset.filter === activeStickerFilter;
        pill.classList.toggle('active', isActive);
        pill.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    }});

    refreshStickerVisibility();
    requestAnimationFrame(function(){{ restoreWallAnchor(anchor); }});

    const shouldUpdateUrl = !options || options.updateUrl !== false;
    if(shouldUpdateUrl && window.history && window.history.replaceState){{
        const url = new URL(window.location.href);
        if(activeStickerFilter === 'all'){{
            url.searchParams.delete('filter');
        }}else{{
            url.searchParams.set('filter', activeStickerFilter);
        }}
        window.history.replaceState({{}}, '', url.toString());
    }}
}}

function refreshStickerVisibility(){{
    const term = stickerSearchInput ? stickerSearchInput.value.trim() : '';

    document.querySelectorAll('.slot').forEach(function(slot){{
        const isSearchMatch = matchesStickerSearch(slot, term);
        const isFilterMatch = slotMatchesActiveFilter(slot);
        const frame = slot.closest('[data-sticker-frame]');
        const keepActiveControlVisible = slot === activeInlineStickerSlot
            && frame && frame.classList.contains('inline-active');
        slot.classList.toggle('search-hidden', !isSearchMatch);
        slot.classList.toggle('filter-hidden', !isFilterMatch && !keepActiveControlVisible);
        if(frame) frame.hidden = !isSearchMatch || (!isFilterMatch && !keepActiveControlVisible);
    }});

    document.querySelectorAll('.sticker-team-block').forEach(function(teamBlock){{
        const hasVisibleSlot = Array.from(teamBlock.querySelectorAll('.slot')).some(slotIsVisible);
        teamBlock.style.display = hasVisibleSlot ? '' : 'none';
    }});

    document.querySelectorAll('.sticker-chapter-block').forEach(function(chapterBlock){{
        const hasVisibleSlot = Array.from(chapterBlock.querySelectorAll('.slot')).some(slotIsVisible);
        chapterBlock.style.display = hasVisibleSlot ? '' : 'none';
    }});

    updateChapterCollapseVisibility();
    updateVisibleStickerCount();
    updateStickerCounterBadges();
    updateStickerSearchFeedback(term);
    scheduleStickerwallContextSync();
}}

function applyStickerVisibility(){{
    refreshStickerVisibility();
}}

function resetStickerSearch(){{
    if(!stickerSearchInput) return;

    stickerSearchInput.value = '';
    stickerSearchInput.placeholder = 'Sticker suchen...';
    stickerSearchInput.type = 'search';

    applyStickerVisibility();
}}

function clearStickerFilter(){{
    document.querySelectorAll('.slot').forEach(function(slot){{
        slot.classList.remove('search-hidden');
    }});

    refreshStickerVisibility();
}}

function normalizeQuery(value){{
    return String(value || '').trim().toUpperCase().replace(/[^A-Z0-9]/g, '');
}}

function normalizeStickerToken(value){{
    return normalizeQuery(value).toLowerCase();
}}

function getStickerNumber(code){{
    const match = normalizeQuery(code).match(/(\\d+)$/);
    return match ? match[1] : '';
}}

function hasLettersAndNumbers(value){{
    const normalizedValue = normalizeQuery(value);
    return /[A-Z]/.test(normalizedValue) && /\\d/.test(normalizedValue);
}}

function isOnlyNumbers(value){{
    const normalizedValue = normalizeQuery(value);
    return /^\\d+$/.test(normalizedValue);
}}

function stickerSearchAliases(slot){{
    const values = [
        slot.dataset.code || '',
        slot.dataset.display || '',
        slot.dataset.search || ''
    ];

    const aliases = [];

    values.forEach(function(value){{
        const raw = String(value || '').toUpperCase();
        const compact = normalizeQuery(raw);

        if(compact){{
            aliases.push(compact);
            aliases.push('STICKER' + compact);
            if(/^0+\\d+$/.test(compact)){{
                const withoutLeadingZero = String(parseInt(compact, 10));
                aliases.push(withoutLeadingZero);
                aliases.push('STICKER' + withoutLeadingZero);
            }}
        }}

        raw.split(/[^A-Z0-9]+/).forEach(function(part){{
            const normalizedPart = normalizeQuery(part);
            if(normalizedPart){{
                aliases.push(normalizedPart);
                aliases.push('STICKER' + normalizedPart);
                if(/^0+\\d+$/.test(normalizedPart)){{
                    const withoutLeadingZero = String(parseInt(normalizedPart, 10));
                    aliases.push(withoutLeadingZero);
                    aliases.push('STICKER' + withoutLeadingZero);
                }}
            }}
        }});
    }});

    return Array.from(new Set(aliases));
}}

function stickerSearchNumbers(slot){{
    const numbers = [];
    const values = [
        slot.dataset.code || '',
        slot.dataset.display || ''
    ];

    values.forEach(function(value){{
        const normalizedValue = normalizeQuery(value);
        const match = normalizedValue.match(/(\\d+)$/);
        if(match){{
            numbers.push(match[1]);
            numbers.push(String(parseInt(match[1], 10)));
        }}
    }});

    return Array.from(new Set(numbers));
}}

function matchesStickerSearch(slot, rawTerm){{
    const term = String(rawTerm || '').trim();
    if(!term) return true;

    const normalizedTerm = normalizeQuery(term);
    if(!normalizedTerm) return true;

    const queryIsOnlyNumbers = /^\\d+$/.test(normalizedTerm);
    const queryHasLetters = /[A-Z]/.test(normalizedTerm);
    const queryHasNumbers = /\\d/.test(normalizedTerm);

    if(queryIsOnlyNumbers){{
        return stickerSearchNumbers(slot).includes(normalizedTerm);
    }}

    if(queryHasLetters && queryHasNumbers){{
        return stickerSearchAliases(slot).includes(normalizedTerm);
    }}

    const search = slot.dataset.search || slot.dataset.display || slot.dataset.code || '';
    return normalizeQuery(search).includes(normalizedTerm);
}}

function updateStickerSearchFeedback(term){{
    const normalizedTerm = normalizeQuery(term);
    const box = document.getElementById('searchDebugBox');
    if(!box) return;

    if(!normalizedTerm){{
        box.style.display = 'none';
        box.textContent = '';
        return;
    }}

    const visibleCodes = Array.from(document.querySelectorAll('.slot'))
        .filter(slotIsVisible);

    const count = visibleCodes.length;

    box.style.display = 'block';
    box.textContent = count === 0 ? 'Kein Treffer' : count + ' Treffer';
}}

function findSlotByCode(code){{
    let foundSlot = null;
    const needle = normalizeQuery(code);
    if(!needle) return null;

    document.querySelectorAll('.slot').forEach(function(slot){{
        if(!foundSlot && stickerSearchAliases(slot).includes(needle)){{
            foundSlot = slot;
        }}
    }});

    return foundSlot;
}}

function slotIsVisible(slot){{
    return slot && !slot.classList.contains('search-hidden') && !slot.classList.contains('filter-hidden');
}}

function wallHasVisibleSlot(wall){{
    return Array.from(wall.querySelectorAll('.slot')).some(slotIsVisible);
}}

function clearHiddenStickerSections(){{
    document.querySelectorAll('.wall, .team-title, .section-title, .album-chapter-title, .sticker-team-block, .sticker-chapter-block').forEach(function(node){{
        node.classList.remove('search-section-hidden');
        node.classList.remove('collapse-section-hidden');
    }});
}}

function hasActiveStickerSearch(){{
    return stickerSearchInput && normalizeQuery(stickerSearchInput.value || '');
}}

function updateChapterCollapseVisibility(){{
    const searchActive = hasActiveStickerSearch();

    document.querySelectorAll('.collapse-section-hidden').forEach(function(node){{
        node.classList.remove('collapse-section-hidden');
    }});

    document.querySelectorAll('.album-chapter-title').forEach(function(chapterTitle){{
        if(searchActive || !chapterTitle.classList.contains('chapter-collapsed')){{
            chapterTitle.setAttribute('aria-expanded', 'true');
            return;
        }}

        chapterTitle.setAttribute('aria-expanded', 'false');
        const chapterBlock = chapterTitle.closest('.sticker-chapter-block');
        if(!chapterBlock) return;

        Array.from(chapterBlock.children).forEach(function(node){{
            if(node !== chapterTitle){{
                node.classList.add('collapse-section-hidden');
            }}
        }});
    }});
    scheduleStickerwallContextSync();
}}

function toggleStickerWallChapter(chapterTitle){{
    const titleTop = chapterTitle.getBoundingClientRect().top;
    chapterTitle.classList.toggle('chapter-collapsed');
    updateChapterCollapseVisibility();
    persistExpandedStickerWallChapters();
    requestAnimationFrame(function(){{
        window.scrollBy(0, chapterTitle.getBoundingClientRect().top - titleTop);
        scheduleStickerwallContextSync();
    }});
}}

function updateVisibleStickerSections(){{
    refreshStickerVisibility();
}}


if(stickerSearchInput){{
    stickerSearchInput.addEventListener('input', function(){{
        refreshStickerVisibility();
    }});
}}

document.querySelectorAll('.sticker-filter-pill[data-filter]').forEach(function(pill){{
    pill.setAttribute('role', 'button');
    pill.setAttribute('aria-pressed', pill.classList.contains('active') ? 'true' : 'false');
    pill.addEventListener('click', function(event){{
        if(event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
        event.preventDefault();
        setActiveStickerFilter(pill.dataset.filter || 'all');
    }});
}});

document.querySelectorAll('.album-chapter-title').forEach(function(chapterTitle){{
    chapterTitle.addEventListener('click', function(){{
        toggleStickerWallChapter(chapterTitle);
    }});

    chapterTitle.addEventListener('keydown', function(event){{
        if(event.key !== 'Enter' && event.key !== ' ') return;
        event.preventDefault();
        toggleStickerWallChapter(chapterTitle);
    }});
}});

const stickyContextControl = document.getElementById('stickerWallStickyContext');
if(stickyContextControl){{
    stickyContextControl.addEventListener('click', function(){{
        if(activeStickyContextSource && activeStickyContextSource.classList.contains('album-chapter-title')){{
            activeStickyContextSource.click();
            scheduleStickerwallContextSync();
        }}
    }});
    stickyContextControl.addEventListener('keydown', function(event){{
        if(event.key !== 'Enter' && event.key !== ' ') return;
        if(!activeStickyContextSource || !activeStickyContextSource.classList.contains('album-chapter-title')) return;
        event.preventDefault();
        activeStickyContextSource.click();
        scheduleStickerwallContextSync();
    }});
}}

restoreExpandedStickerWallChapters();
updateChapterCollapseVisibility();
setActiveStickerFilter(activeStickerFilter, {{updateUrl:false}});
scheduleStickerwallContextSync();
requestAnimationFrame(function(){{
    requestAnimationFrame(restoreStickerWallPosition);
}});

window.addEventListener('pagehide', function(){{
    persistExpandedStickerWallChapters();
    persistStickerWallPosition();
}});

document.addEventListener('click', function(event){{
    const quantityButton = event.target.closest('[data-quantity-delta]');
    if(quantityButton){{
        event.preventDefault();
        event.stopPropagation();
        const frame = quantityButton.closest('[data-sticker-frame]');
        const quantitySlot = frame ? frame.querySelector('.slot[data-code]') : null;
        changeInlineStickerQuantity(quantitySlot, parseInt(quantityButton.dataset.quantityDelta || '0', 10));
        return;
    }}

    const detailLink = event.target.closest('.sticker-inline-detail');
    if(detailLink){{
        persistExpandedStickerWallChapters();
        persistStickerWallPosition();
        const detailUrl = new URL(detailLink.href, window.location.href);
        if(activeStickerFilter === 'all') detailUrl.searchParams.delete('filter');
        else detailUrl.searchParams.set('filter', activeStickerFilter);
        detailLink.href = detailUrl.toString();
        return;
    }}

    const slot = event.target.closest('.slot[data-code]');
    if(!slot){{
        if(!event.target.closest('[data-inline-control]')) closeInlineStickerControl();
        return;
    }}

    if(event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
    event.preventDefault();
    openInlineStickerControl(slot);
}});

document.addEventListener('keydown', function(event){{
    if(event.key === 'Escape'){{
        closeInlineStickerControl();
    }}
}});
</script>
'''
    html += trophy_popup
    html += bottom_nav("sammlung")
    html += "</div></div></body></html>"
    return html


@app.route("/bulk_add/<album_id>", methods=["POST"])
def bulk_add(album_id):
    codes = request.form.getlist("codes")
    resolved_codes = []

    for raw_code in codes:
        code = resolve_code(album_id, raw_code)
        if code:
            resolved_codes.append(code)

    if not resolved_codes:
        return redirect(f"/album/{album_id}?message=Keine%20Sticker%20ausgewählt.&focus=add")

    vorher_erreicht = erreichte_trophaeen(album_id)
    mutation_key = history_request_event_key("bulk-add")

    con = get_db()

    for index, code in enumerate(resolved_codes):
        add_sticker_quantity(
            con, current_user_id(), album_id, code,
            history_event_key=f"{mutation_key}:{index}:{code}",
        )

    con.commit()
    con.close()

    nachher_erreicht = erreichte_trophaeen(album_id)
    neue_trophies = record_trophy_unlocks(
        album_id,
        [t for t in nachher_erreicht if t not in vorher_erreicht],
        silent_reached=vorher_erreicht
    )
    queue_trophy_popup(album_id, neue_trophies)

    session["last_action"] = {
        "action": "bulk_add",
        "album_id": album_id,
        "codes": resolved_codes,
        "filter": "all"
    }

    msg = f"{len(resolved_codes)} Sticker hinzugefügt."
    url = f"/album/{album_id}?message={quote(msg)}&focus=add"

    return redirect(url)


@app.route("/bulk_remove/<album_id>", methods=["POST"])
def bulk_remove(album_id):
    codes = request.form.getlist("codes")
    resolved_codes = []

    for raw_code in codes:
        code = resolve_code(album_id, raw_code)
        if code:
            resolved_codes.append(code)

    if not resolved_codes:
        return redirect(f"/album/{album_id}?message=Keine%20Sticker%20ausgewählt.&focus=remove")

    vorher_erreicht = erreichte_trophaeen(album_id)
    mutation_key = history_request_event_key("bulk-remove")

    con = get_db()

    for index, code in enumerate(resolved_codes):
        remove_sticker_quantity(
            con, current_user_id(), album_id, code,
            history_event_key=f"{mutation_key}:{index}:{code}",
        )

    con.commit()
    con.close()

    nachher_erreicht = erreichte_trophaeen(album_id)
    neue_trophies = record_trophy_unlocks(
        album_id,
        [t for t in nachher_erreicht if t not in vorher_erreicht],
        silent_reached=vorher_erreicht
    )
    queue_trophy_popup(album_id, neue_trophies)

    session["last_action"] = {
        "action": "bulk_remove",
        "album_id": album_id,
        "codes": resolved_codes,
        "filter": "all"
    }

    msg = f"{len(resolved_codes)} Sticker entfernt."
    return redirect(f"/album/{album_id}?message={quote(msg)}&focus=remove")


@app.route("/sticker/<album_id>/<path:code>", methods=["GET", "POST"])
def sticker_detail(album_id, code):
    current_filter = request.args.get("filter", "all")

    if request.method == "POST":
        vorher_erreicht = erreichte_trophaeen(album_id)
        raw_quantity = request.form.get("quantity", "0").strip()

        try:
            quantity = max(int(raw_quantity), 0)
        except ValueError:
            quantity = 0

        con = get_db()
        mutation_key = history_request_event_key("sticker-detail-set")
        if cutover_schema_available(con):
            HistoricalInventoryWriteService(con).set_quantity(
                current_user_id(), album_id, code, quantity,
                event_key=f"{mutation_key}:{code}",
            )
        else:
            InventoryWriteService(con).set_quantity(
                current_user_id(), album_id, code, quantity
            )

        con.commit()
        con.close()

        nachher_erreicht = erreichte_trophaeen(album_id)
        neue_trophies = record_trophy_unlocks(
            album_id,
            [t for t in nachher_erreicht if t not in vorher_erreicht],
            silent_reached=vorher_erreicht
        )
        queue_trophy_popup(album_id, neue_trophies)

        msg = f"Anzahl für Sticker {display_code(code)} auf {quantity} gesetzt."
        if quantity == 0:
            msg = f"Sticker {display_code(code)} aus deiner Sammlung entfernt."

        return redirect(f"/album/{album_id}?filter={current_filter}&message={quote(msg)}&focus=add&trigger={quote(code)}")

    album, by_code, gesammelt, doppelte, prozent, total = lade_album(album_id)
    inventory = lade_album_inventory(album_id)
    q = by_code[code]["quantity"] if code in by_code else 0
    incoming_transit = inventory.availability_snapshot_for(code).incoming_transit

    if q == 0:
        farbe, status = "missing", "Fehlt"
    elif q == 1:
        farbe, status = "owned", "Vorhanden"
    else:
        farbe, status = "duplicate", "Doppelt"

    return f"""
    <html><head>{style()}</head><body class="s31-product-page"><div class="container">
    {app_header("Sticker " + escape(display_code(code)))}
    <a class="sammlr-back-link" href="/album/{album_id}{'?filter=' + quote(current_filter) if current_filter != 'all' else ''}">← Zurück zum Album</a>
    <div class="card sticker-detail-card">
        <div class="sticker-detail-layout">
            <div class="sticker-detail-preview">
                <div class="sticker-detail-image-placeholder">
                    <div class="slot {farbe} sticker-detail-tile">{display_code(code)}</div>
                </div>
                <p>Stickerbild / Foto</p>
            </div>

            <div class="sticker-detail-content">
                <p class="sticker-detail-eyebrow">Sticker</p>
                <h1>{display_code(code)}</h1>
                <div class="sticker-detail-status {farbe}">{status}</div>
                {f'<div class="sticker-detail-transit">{incoming_transit} unterwegs</div>' if incoming_transit > 0 else ''}

                <div class="sticker-detail-meta">
                    <div>
                        <span>Anzahl</span>
                        <strong>{q}</strong>
                    </div>
                    <div>
                        <span>Doppelte</span>
                        <strong>{max(q - 1, 0)}</strong>
                    </div>
                </div>

                <form class="quantity-edit-form" method="POST" action="/sticker/{album_id}/{code}?filter={current_filter}">
                    <label for="stickerQuantity">Anzahl</label>
                    <div class="quantity-edit-row">
                        <input id="stickerQuantity" name="quantity" type="number" min="0" step="1" value="{q}">
                        <button type="submit" class="btn">Speichern</button>
                    </div>
                </form>

                <div class="sticker-detail-notes">
                    <h2>Notizen / Metadaten</h2>
                    <p>Platzhalter für Stickername, Varianten, Zustand oder persönliche Notizen.</p>
                </div>

                <div class="sticker-detail-actions">
                    <form method="POST" action="/add/{album_id}/{code}">
                        <input type="hidden" name="filter" value="{current_filter}">
                        <button class="btn" type="submit">+ Hinzufügen</button>
                    </form>
                    <form method="POST" action="/remove/{album_id}/{code}">
                        <input type="hidden" name="filter" value="{current_filter}">
                        <button class="btn gray" type="submit">- Entfernen</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
    {bottom_nav("sammlung")}
    </div></body></html>
    """


@app.route("/album/<album_id>/sticker/<path:code>/quantity", methods=["POST"])
def update_sticker_quantity_inline(album_id, code):
    resolved_code = resolve_code(album_id, code)
    if resolved_code is None:
        return jsonify({"ok": False, "message": "Sticker nicht vorhanden."}), 404

    try:
        delta = int(request.form.get("delta", "0"))
    except ValueError:
        delta = 0

    if delta == 0:
        return jsonify({"ok": False, "message": "Keine Änderung."}), 400

    con = get_db()
    album_access = con.execute(
        "SELECT 1 FROM user_albums WHERE user_id=? AND album_id=?",
        (current_user_id(), album_id),
    ).fetchone()
    if album_access is None:
        con.close()
        abort(403)

    vorher_erreicht = erreichte_trophaeen(album_id)
    mutation_key = history_request_event_key("inline-quantity")
    change_sticker_quantity(
        con, current_user_id(), album_id, resolved_code, delta,
        history_event_key=f"{mutation_key}:{resolved_code}",
    )
    con.commit()
    con.close()

    album, by_code, gesammelt, doppelte, prozent, total = lade_album(album_id)
    inventory = lade_album_inventory(album_id)
    quantity = sticker_quantity_for_counter(by_code, resolved_code)
    incoming_transit = inventory.availability_snapshot_for(resolved_code).incoming_transit
    status_class = sticker_status_class_for_quantity(quantity)
    nachher_erreicht = erreichte_trophaeen(album_id)
    neue_trophies = record_trophy_unlocks(
        album_id,
        [t for t in nachher_erreicht if t not in vorher_erreicht],
        silent_reached=vorher_erreicht
    )

    return jsonify({
        "ok": True,
        "code": resolved_code,
        "display": display_code(resolved_code),
        "quantity": quantity,
        "incomingTransit": incoming_transit,
        "duplicates": max(quantity - 1, 0),
        "statusClass": status_class,
        "statusLabel": sticker_status_label_for_quantity(quantity),
        "cardHtml": sticker_wall_card_inner(
            album_id, resolved_code, by_code, incoming_transit
        ),
        "album": {
            "collected": gesammelt,
            "duplicates": doppelte,
            "missing": total - gesammelt,
            "percent": prozent,
            "total": total
        },
        "trophyHtml": trophy_popup_html(album_id, neue_trophies)
    })


@app.route("/add/<album_id>/<path:code>", methods=["POST"])
def add(album_id, code):
    vorher_erreicht = erreichte_trophaeen(album_id)
    current_filter = request.form.get("filter") or request.args.get("filter", "all")

    con = get_db()
    mutation_key = history_request_event_key("add-sticker")
    if cutover_schema_available(con):
        mutation = HistoricalInventoryWriteService(con).add(
            current_user_id(), album_id, code,
            event_key=f"{mutation_key}:{code}",
        )
    else:
        mutation = InventoryWriteService(con).add(
            current_user_id(), album_id, code
        )
    neue_duplicates = mutation.duplicates

    con.commit()
    con.close()

    nachher_erreicht = erreichte_trophaeen(album_id)
    

    neue_trophies = record_trophy_unlocks(
        album_id,
        [t for t in nachher_erreicht if t not in vorher_erreicht],
        silent_reached=vorher_erreicht
    )
    queue_trophy_popup(album_id, neue_trophies)


    msg = f"Du hast Sticker {display_code(code)} doppelt." if neue_duplicates >= 1 else f"Du hast Sticker {display_code(code)} zur Sammlung hinzugefügt."

    url = f"/album/{album_id}?filter={current_filter}&message={quote(msg)}&focus=add&smart=1"

    session["last_action"] = {
        "action": "add",
        "album_id": album_id,
        "code": code,
        "filter": current_filter
    }
    return redirect(url)

    

@app.route("/undo", methods=["POST"])
def undo_last_action():
    data = session.get("last_action")

    if not data:
        return redirect("/sammlung")

    album_id = data["album_id"]
    action = data["action"]
    current_filter = data.get("filter", "all")
    code = data.get("code")
    codes = data.get("codes", [])
    get_codes = data.get("get_codes", [])
    give_codes = data.get("give_codes", [])

    con = get_db()
    mutation_key = history_request_event_key("undo-inventory")

    if action in ("add", "bulk_add"):
        undo_codes = codes if action == "bulk_add" else [code]

        for index, undo_code in enumerate(undo_codes):
            remove_sticker_quantity(
                con, current_user_id(), album_id, undo_code,
                history_event_key=f"{mutation_key}:remove:{index}:{undo_code}",
            )

    elif action in ("remove", "bulk_remove"):
        undo_codes = codes if action == "bulk_remove" else [code]

        for index, undo_code in enumerate(undo_codes):
            add_sticker_quantity(
                con, current_user_id(), album_id, undo_code,
                history_event_key=f"{mutation_key}:add:{index}:{undo_code}",
            )

    elif action == "transfer":
        for index, undo_code in enumerate(get_codes):
            remove_sticker_quantity(
                con, current_user_id(), album_id, undo_code,
                history_event_key=f"{mutation_key}:give-back:{index}:{undo_code}",
                history_source_type="paper_trade",
            )

        for index, undo_code in enumerate(give_codes):
            add_sticker_quantity(
                con, current_user_id(), album_id, undo_code,
                history_event_key=f"{mutation_key}:receive-back:{index}:{undo_code}",
                history_source_type="paper_trade",
            )

    con.commit()
    con.close()

    session.pop("last_action", None)

    if action == "bulk_add":
        msg = f"{len(codes)} hinzugefügte Sticker rückgängig gemacht."
    elif action == "bulk_remove":
        msg = f"{len(codes)} entfernte Sticker rückgängig gemacht."
    elif action == "transfer":
        msg = f"Transfer rückgängig gemacht: {len(get_codes)} erhalten, {len(give_codes)} abgegeben."
        return redirect(f"/album/{album_id}/liste?message={quote(msg)}")
    else:
        msg = f"Aktion für Sticker {display_code(code)} rückgängig gemacht."
    return redirect(f"/album/{album_id}?filter={current_filter}&message={quote(msg)}&focus=add")


@app.route("/remove/<album_id>/<path:code>", methods=["POST"])

def remove(album_id, code):
    vorher_erreicht = erreichte_trophaeen(album_id)
    con = get_db()
    current_filter = request.form.get("filter") or request.args.get("filter", "all")
    mutation_key = history_request_event_key("remove-sticker")
    remove_sticker_quantity(
        con, current_user_id(), album_id, code,
        history_event_key=f"{mutation_key}:{code}",
    )

    con.commit()
    con.close()
    nachher_erreicht = erreichte_trophaeen(album_id)
    neue_trophies = record_trophy_unlocks(
        album_id,
        [t for t in nachher_erreicht if t not in vorher_erreicht],
        silent_reached=vorher_erreicht
    )
    queue_trophy_popup(album_id, neue_trophies)
    session["last_action"] = {
        "action": "remove",
        "album_id": album_id,
        "code": code,
        "filter": current_filter
    }
    msg = f"Sticker {display_code(code)} wurde entfernt."
    return redirect(f"/album/{album_id}?filter={current_filter}&message={quote(msg)}&focus=remove")


def change_sticker_quantity(
    con,
    user_id,
    album_id,
    code,
    delta,
    *,
    history_event_key=None,
    history_source_type="inventory",
    occurred_at=None,
):
    if history_event_key is not None and cutover_schema_available(con):
        return HistoricalInventoryWriteService(con).change_quantity(
            user_id,
            album_id,
            code,
            delta,
            event_key=history_event_key,
            source_type=history_source_type,
            occurred_at=occurred_at,
        )
    return InventoryWriteService(con).change_quantity(
        user_id, album_id, code, delta
    )


def add_sticker_quantity(
    con,
    user_id,
    album_id,
    code,
    amount=1,
    *,
    history_event_key=None,
    history_source_type="inventory",
    occurred_at=None,
):
    return change_sticker_quantity(
        con,
        user_id,
        album_id,
        code,
        max(amount, 0),
        history_event_key=history_event_key,
        history_source_type=history_source_type,
        occurred_at=occurred_at,
    )


def remove_sticker_quantity(
    con,
    user_id,
    album_id,
    code,
    amount=1,
    *,
    history_event_key=None,
    history_source_type="inventory",
    occurred_at=None,
):
    return change_sticker_quantity(
        con,
        user_id,
        album_id,
        code,
        -max(amount, 0),
        history_event_key=history_event_key,
        history_source_type=history_source_type,
        occurred_at=occurred_at,
    )


def complete_trade(con, trade):
    give_codes = json.loads(trade["give_codes"])
    get_codes = json.loads(trade["get_codes"])
    album_id = trade["album_id"]
    from_user_id = trade["from_user_id"]
    to_user_id = trade["to_user_id"]

    mutation_key = f"legacy-trade-completion:{trade['id']}"
    for index, code in enumerate(give_codes):
        remove_sticker_quantity(
            con, from_user_id, album_id, code,
            history_event_key=f"{mutation_key}:from-give:{index}:{code}",
            history_source_type="trade_shipping",
        )
        add_sticker_quantity(
            con, to_user_id, album_id, code,
            history_event_key=f"{mutation_key}:to-receive:{index}:{code}",
            history_source_type="trade_receipt",
        )

    for index, code in enumerate(get_codes):
        add_sticker_quantity(
            con, from_user_id, album_id, code,
            history_event_key=f"{mutation_key}:from-receive:{index}:{code}",
            history_source_type="trade_receipt",
        )
        remove_sticker_quantity(
            con, to_user_id, album_id, code,
            history_event_key=f"{mutation_key}:to-give:{index}:{code}",
            history_source_type="trade_shipping",
        )


def complete_trade_if_ready(con, trade):
    latest = con.execute(
        "SELECT * FROM trade_requests WHERE id=? AND status='accepted'",
        (trade["id"],)
    ).fetchone()

    if not latest or latest["from_confirmed"] != 1 or latest["to_confirmed"] != 1:
        return False

    TradeReservationService(con).release(
        latest["id"], "completed", "completed"
    )
    complete_trade(con, latest)
    con.execute("UPDATE trade_requests SET status='completed' WHERE id=?", (latest["id"],))
    return True


def open_incoming_trade_request_count(album_id=None):
    con = get_db()
    if album_id:
        row = con.execute(
            """
            SELECT COUNT(*) AS count
            FROM trade_requests
            WHERE album_id=? AND to_user_id=? AND status='open'
            """,
            (album_id, current_user_id())
        ).fetchone()
    else:
        row = con.execute(
            """
            SELECT COUNT(*) AS count
            FROM trade_requests
            WHERE to_user_id=? AND status='open'
            """,
            (current_user_id(),)
        ).fetchone()
    con.close()
    return row["count"] if row else 0


def first_open_incoming_trade_request():
    con = get_db()
    row = con.execute(
        """
        SELECT album_id
        FROM trade_requests
        WHERE to_user_id=? AND status='open'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (current_user_id(),)
    ).fetchone()
    con.close()
    return row


def trade_code_summary(codes):
    if not codes:
        return "Keine Sticker"

    counts = {}
    for code in codes:
        counts[code] = counts.get(code, 0) + 1

    parts = []
    for code, amount in counts.items():
        label = display_code(code)
        parts.append(f"{label} ({amount}x)" if amount > 1 else label)

    if len(parts) > 10:
        return ", ".join(parts[:10]) + f" und {len(parts) - 10} weitere"

    return ", ".join(parts)


def trade_status_label(trade, is_receiver=False):
    status = trade["status"]

    if status == "open":
        return "Offen"
    if status == "completed":
        return "Abgeschlossen"
    if status == "failed":
        return "Geplatzt"
    if status == "declined":
        return "Abgelehnt"
    if status == "expired":
        return "Abgelaufen"
    if status == "obsolete":
        return "Nicht mehr verfügbar"
    if status == "accepted":
        my_confirmed = trade["to_confirmed"] if is_receiver else trade["from_confirmed"]
        other_confirmed = trade["from_confirmed"] if is_receiver else trade["to_confirmed"]
        if my_confirmed and not other_confirmed:
            return "Wartet auf andere Person"
        if other_confirmed and not my_confirmed:
            return "Andere Person hat bestätigt"
        return "Wartet auf Durchführung"

    return status


def trade_has_smart_origin(connection, trade):
    if is_smart_trade_request(trade):
        return True
    if not table_exists(connection, "trade_events"):
        return False
    row = connection.execute(
        """
        SELECT 1
        FROM trade_events event
        JOIN trades lifecycle ON lifecycle.id=event.trade_id
        WHERE lifecycle.legacy_trade_request_id=? AND event.event_type=?
        LIMIT 1
        """,
        (trade["id"], SMART_ACCEPTED_EVENT),
    ).fetchone()
    return row is not None


def smart_trade_badge_html(is_smart):
    if not is_smart:
        return ""
    return '<span class="trade-partner-status ready">Smart-Paket</span>'


def trade_request_type_badge_html(is_smart):
    label = "SmartMatch-Anfrage" if is_smart else "Manuelle Anfrage"
    variant = "smart" if is_smart else "manual"
    return (
        f'<span class="trade-request-type-badge {variant}">'
        f'{label}</span>'
    )


def trade_open_actions(trade):
    return f"""
    <div class="trade-request-actions">
        <form method="POST" action="/trade/{trade['id']}/accept">
            <button class="btn green" type="submit">Annehmen</button>
        </form>
        <form method="POST" action="/trade/{trade['id']}/decline">
            <button class="btn gray" type="submit">Ablehnen</button>
        </form>
    </div>
    """


def trade_shipping_status_label(
    shipping_status, receipt_status=None, problem_reports=()
):
    if any(report.state == "open" for report in problem_reports):
        return "Problem offen"
    if receipt_status is not None and receipt_status.both_received:
        return "Empfang vollständig"
    if receipt_status is not None and receipt_status.any_received:
        return "Teilweise erhalten"
    if shipping_status is None:
        return ""
    if shipping_status.both_shipped:
        return "Beide Seiten haben versendet"
    if shipping_status.any_shipped:
        return "Versand läuft"
    return "Reserviert"


TRADE_PROBLEM_LABELS = {
    "missing": "Fehlend / unvollständig",
    "wrong_sticker": "Falscher Sticker",
    "damaged": "Beschädigt",
    "shipment_lost": "Sendung verloren",
}


def trade_problem_history_html(problem_reports, user_id):
    if not problem_reports:
        return ""
    reports_html = []
    for report in problem_reports:
        owner = "Deine Lieferung" if report.receiver_user_id == user_id else "Lieferung der Gegenseite"
        if report.resolved_after_close_at:
            state_label = "Problem nachträglich gelöst"
        elif report.closed_at:
            state_label = "Trade mit Problem beendet"
        else:
            state_label = "Problem offen" if report.state == "open" else "Problem aufgelöst"
        positions_html = []
        for position in report.positions:
            problem_label = TRADE_PROBLEM_LABELS.get(
                position.problem_type, "Vollständig erhalten"
            )
            positions_html.append(f"""
            <li>
                <strong>{escape(display_code(position.sticker_code))}</strong>:
                erwartet {position.expected_quantity},
                bei erster Meldung erhalten {position.initial_received_quantity},
                später nachgeliefert {position.resolution_received_quantity},
                offen {position.open_quantity} – {escape(problem_label)}
            </li>
            """)
        resolution_line = (
            f"<p>Aufgelöst: {sammlr_time_html(report.resolved_at)}</p>"
            if report.resolved_at else ""
        )
        closure_line = (
            f"<p>Trade mit Problem beendet: {sammlr_time_html(report.closed_at)}</p>"
            if report.closed_at else ""
        )
        late_resolution_line = (
            "<p>Problem nachträglich gelöst: "
            f"{sammlr_time_html(report.resolved_after_close_at)}</p>"
            if report.resolved_after_close_at else ""
        )
        reports_html.append(f"""
        <article class="trade-completion-box">
            <h3>{owner}: {state_label}</h3>
            <p>Dokumentiert: {sammlr_time_html(report.created_at)}</p>
            <ul>{''.join(positions_html)}</ul>
            {closure_line}
            {resolution_line}
            {late_resolution_line}
            <p>Sammlr dokumentiert die physische Realität und entscheidet keine Schuldfrage.</p>
        </article>
        """)
    return f"""
    <section class="card" aria-label="Problemhistorie">
        <h3>Problemhistorie</h3>
        {''.join(reports_html)}
    </section>
    """


def trade_completion_actions(
    trade, partner_name, is_receiver=False, shipping_status=None,
    receipt_status=None, problem_reports=(),
):
    status = trade["status"]
    if status == "completed":
        return "<p><strong>Abgeschlossen:</strong> Die Sticker wurden automatisch gebucht.</p>"
    if status == "failed":
        return "<p><strong>Geplatzt:</strong> Keine Bestandsänderung.</p>"
    if status == "declined":
        return "<p><strong>Abgelehnt.</strong></p>"
    if status != "accepted":
        return ""

    if shipping_status is not None:
        return f"""
        <div class="trade-completion-box">
            <p><strong>{trade_shipping_status_label(shipping_status, receipt_status, problem_reports)}</strong></p>
            <a class="trade-detail-link" href="/trades/{trade['id']}?origin=trades">Versandstatus öffnen</a>
        </div>
        """

    my_confirmed = trade["to_confirmed"] if is_receiver else trade["from_confirmed"]
    other_confirmed = trade["from_confirmed"] if is_receiver else trade["to_confirmed"]

    if my_confirmed and not other_confirmed:
        return """
        <div class="trade-completion-box">
            <h3>Tausch durchgeführt?</h3>
            <p>Du hast den Tausch als durchgeführt markiert. Warte auf die Bestätigung der anderen Person.</p>
        </div>
        """

    other_hint = "<p>Die andere Person hat bereits bestätigt.</p>" if other_confirmed else ""
    return f"""
    <div class="trade-completion-box">
        <h3>Tausch durchgeführt?</h3>
        <p>Hast du deinen Tausch mit {partner_name} erfolgreich abgeschlossen?</p>
        {other_hint}
        <div class="trade-request-actions">
            <form method="POST" action="/trade/{trade['id']}/confirm">
                <button class="btn green" type="submit">Ja, durchgeführt</button>
            </form>
            <form method="POST" action="/trade/{trade['id']}/fail">
                <button class="btn gray" type="submit">Nein, Deal geplatzt</button>
            </form>
        </div>
    </div>
    """


def trade_detail_sticker_items(codes, mode):
    if not codes:
        return '<p class="trade-product-codes-empty">Keine Sticker.</p>'

    items = []
    for code in codes:
        label = display_code(code)
        items.append(f"""
        <span class="sticker-list-item trade-detail-sticker trade-product-code selected"
              data-list-mode="{mode}">{escape(label)}</span>
        """)
    return "".join(items)


def trade_product_status_html(
    trade, partner_name, is_receiver, status_label,
    shipping_status=None, receipt_status=None, problem_reports=(),
    successfully_completed=False, lifecycle_state=None,
):
    """Project existing trade truth into the approved UIF-005A hierarchy."""
    own_problem_open = any(
        report.receiver_user_id == current_user_id() and report.state == "open"
        for report in problem_reports
    )
    other_problem_open = any(
        report.receiver_user_id != current_user_id() and report.state == "open"
        for report in problem_reports
    )
    variant = "is-neutral"
    eyebrow = "Aktueller Stand"
    heading = status_label
    body = "Der gespeicherte Trade-Status wird hier unverändert dargestellt."
    icon = "•"

    if successfully_completed:
        variant = "is-success"
        eyebrow = "Erfolgreich beendet"
        heading = "Trade abgeschlossen"
        body = f"Du und {partner_name} habt den Tausch erfolgreich abgeschlossen."
        icon = "✓"
    elif lifecycle_state == "closed_with_problem":
        variant = "is-problem"
        eyebrow = "Terminal beendet"
        heading = "Trade mit Problem beendet"
        body = "Mindestens ein dokumentiertes Lieferproblem blieb offen."
        icon = "!"
    elif lifecycle_state == "problem_resolved_after_close":
        variant = "is-success"
        eyebrow = "Nachträglich dokumentiert"
        heading = "Problem nachträglich gelöst"
        body = "Der Trade bleibt endgültig abgeschlossen und nur noch lesbar."
        icon = "✓"
    elif trade["status"] == "open":
        variant = "is-attention" if is_receiver else "is-neutral"
        eyebrow = "Anfrage offen"
        heading = "Trade-Anfrage prüfen" if is_receiver else "Warte auf eine Antwort"
        body = (
            f"{partner_name} möchte diesen Tausch mit dir vereinbaren."
            if is_receiver else
            f"Deine Anfrage an {partner_name} wurde gesendet."
        )
        icon = "!" if is_receiver else "•"
    elif trade["status"] == "accepted" and shipping_status is not None:
        own_shipped = shipping_status.shipped_for(current_user_id())
        other_shipped = shipping_status.other_shipped_for(current_user_id())
        own_received = bool(
            receipt_status and receipt_status.received_for(current_user_id())
        )
        other_received = bool(
            receipt_status and receipt_status.other_received_for(current_user_id())
        )
        variant = "is-attention"
        eyebrow = "Nächster Schritt"
        icon = "!"
        if own_problem_open or other_problem_open:
            variant = "is-problem"
            eyebrow = "Problem gemeldet"
            heading = "Lieferproblem wird dokumentiert"
            body = "Der Trade bleibt entsprechend seinem kanonischen Lifecycle-Status geöffnet."
        elif other_shipped and not own_received:
            eyebrow = "Empfang ausstehend"
            heading = "Warte auf deine Empfangsbestätigung"
            body = f"{partner_name} hat seinen Versand bestätigt."
        elif not own_shipped:
            eyebrow = "Versand ausstehend"
            heading = "Bestätige deinen Versand"
            body = "Deine vereinbarten Sticker sind für diesen Trade reserviert."
        elif own_received and not other_received:
            heading = f"Warte auf {partner_name}s Empfangsbestätigung"
            body = "Du hast den Empfang deiner Sticker bereits bestätigt."
        elif own_shipped and not other_shipped:
            heading = f"Warte auf den Versand von {partner_name}"
            body = "Dein eigener Versand wurde bereits bestätigt."
        else:
            heading = "Beide Sendungen sind unterwegs"
            body = "Bestätigt den Empfang, sobald die Sticker angekommen sind."
    elif trade["status"] in {"declined", "failed", "expired", "obsolete"}:
        eyebrow = "Beendet"
        heading = status_label
        body = "Für diesen Trade ist keine weitere Aktion verfügbar."

    shipping_contract = ""
    if shipping_status is not None:
        shipping_contract = " | ".join((
            "Eigener Versand bestätigt" if shipping_status.shipped_for(current_user_id())
            else "Eigener Versand noch offen",
            "Gegenseite hat versendet" if shipping_status.other_shipped_for(current_user_id())
            else "Gegenseite hat noch nicht versendet",
            "Erwartete Sticker sind unterwegs" if shipping_status.other_shipped_for(current_user_id())
            else "Noch keine erwarteten Sticker unterwegs",
        ))

    return f"""
    <section class="trade-product-status {variant}"
             aria-labelledby="trade-product-status-heading"
             data-shipping-contract="{escape(shipping_contract)}">
        <span class="trade-product-status-icon" aria-hidden="true">{icon}</span>
        <div>
            <small>{escape(eyebrow)}</small>
            <h2 id="trade-product-status-heading">{escape(heading)}</h2>
            <p>{escape(body)}</p>
        </div>
        <span class="trade-product-contract-state">{trade_status_chip(status_label)}</span>
    </section>
    """


def trade_detail_primary_action(
    trade, is_receiver, shipping_status=None, receipt_status=None,
    problem_reports=(), problem_schema_enabled=False,
    successfully_completed=False, completed_at=None, lifecycle_state=None,
):
    own_problem = next(
        (
            report for report in problem_reports
            if report.receiver_user_id == current_user_id()
        ),
        None,
    )
    if lifecycle_state == "closed_with_problem":
        late_resolution = ""
        if (
            own_problem is not None
            and own_problem.state == "open"
            and own_problem.closed_by_user_id == current_user_id()
        ):
            late_resolution = f"""
            <form method="POST" action="/trade/{trade['id']}/problem/resolve"
                  onsubmit="return confirm('Die fehlende Restmenge ist jetzt physisch angekommen und wird eingebucht.')">
                <input type="hidden" name="confirm_physical_arrival" value="1">
                <button type="submit" class="sticker-list-check">Problem nachträglich gelöst</button>
            </form>
            """
        return f"""
        <section class="trade-completion-readonly" aria-label="Mit Problem beendeter Trade">
            <strong>Trade mit Problem beendet</strong>
            <p>Mindestens ein dokumentiertes Lieferproblem blieb offen.</p>
            {late_resolution}
        </section>
        """
    if lifecycle_state == "problem_resolved_after_close":
        return """
        <section class="trade-completion-readonly" aria-label="Nachträglich gelöster Problemtrade">
            <strong>Problem nachträglich gelöst</strong>
            <p>Der Trade bleibt endgültig abgeschlossen und nur noch lesbar.</p>
        </section>
        """
    if successfully_completed:
        return f"""
        <section class="trade-completion-readonly" aria-label="Abgeschlossener Trade">
            <strong>Trade abgeschlossen</strong>
            <span>{sammlr_time_html(completed_at)}</span>
            <p>Dieser Trade ist vollständig abgewickelt und nur noch lesbar.</p>
        </section>
        """
    if trade["status"] == "open" and is_receiver:
        return f"""
        <div class="trade-product-action-group">
            <form method="POST" action="/trade/{trade['id']}/accept">
                <button type="submit" class="sticker-list-check trade-product-primary">Transfer durchführen</button>
            </form>
            <form method="POST" action="/trade/{trade['id']}/decline">
                <button type="submit" class="trade-product-secondary">Ablehnen</button>
            </form>
        </div>
        """
    if trade["status"] == "accepted":
        if shipping_status is not None:
            actions = []
            receipt_is_next = bool(
                receipt_status is not None
                and shipping_status.other_shipped_for(current_user_id())
                and not receipt_status.received_for(current_user_id())
                and not (own_problem is not None and own_problem.state == "open")
            )
            if shipping_status.shipped_for(current_user_id()):
                actions.append(
                    '<button type="button" class="sticker-list-check" disabled>'
                    'Eigener Versand bestätigt</button>'
                )
            else:
                shipping_action_class = (
                    "trade-product-secondary" if receipt_is_next
                    else "sticker-list-check trade-product-primary"
                )
                actions.append(f"""
                <form method="POST" action="/trade/{trade['id']}/ship">
                    <button type="submit" class="{shipping_action_class}">Eigenen Versand bestätigen</button>
                </form>
                """)
            if receipt_status is not None and shipping_status.other_shipped_for(
                current_user_id()
            ):
                if receipt_status.received_for(current_user_id()):
                    actions.append(
                        '<button type="button" class="sticker-list-check" disabled>'
                        'Empfang bestätigt</button>'
                    )
                elif own_problem is not None and own_problem.state == "open":
                    actions.append(
                        '<button type="button" class="sticker-list-check" disabled>'
                        'Problem dokumentiert</button>'
                    )
                    actions.append(f"""
                    <form method="POST" action="/trade/{trade['id']}/problem/resolve"
                          onsubmit="return confirm('Die fehlende Restmenge ist jetzt physisch angekommen und wird eingebucht.')">
                        <input type="hidden" name="confirm_physical_arrival" value="1">
                        <button type="submit" class="sticker-list-check">Nachlieferung als angekommen bestätigen</button>
                    </form>
                    """)
                    actions.append(f"""
                    <button type="button" class="trade-detail-link"
                            onclick="document.getElementById('closeProblemTradeDialog').showModal()">
                        Trade mit Problem beenden
                    </button>
                    <dialog id="closeProblemTradeDialog" class="trade-problem-close-dialog">
                        <p>Nicht erhaltene Sticker werden nicht deiner Sammlung hinzugefügt.</p>
                        <p>Der Trade wird abgeschlossen.</p>
                        <p>Sollte die Lieferung später doch noch eintreffen, kann
                           das Problem anschließend weiterhin nachträglich gelöst werden.</p>
                        <div class="trade-request-actions">
                            <form method="dialog">
                                <button class="btn gray" type="submit">Abbrechen</button>
                            </form>
                            <form method="POST" action="/trade/{trade['id']}/problem/close">
                                <button class="btn" type="submit">Trade mit Problem beenden</button>
                            </form>
                        </div>
                    </dialog>
                    """)
                else:
                    actions.append(f"""
                    <form method="POST" action="/trade/{trade['id']}/receive">
                        <button type="submit" class="sticker-list-check trade-product-primary"
                                aria-label="Empfang bestätigen – Alles vollständig erhalten">Alles vollständig erhalten</button>
                    </form>
                    """)
                    if problem_schema_enabled:
                        actions.append(
                            f'<a class="trade-detail-link" href="/trades/{trade["id"]}/problem">'
                            'Problem melden / Lieferung unvollständig</a>'
                        )
            return "".join(actions)
        return f"""
        <form method="POST" action="/trade/{trade['id']}/confirm">
            <button type="submit" class="sticker-list-check trade-product-primary">Transfer durchführen</button>
        </form>
        """
    if trade["status"] == "open":
        return '<button type="button" class="sticker-list-check trade-product-primary" disabled>Wartet auf Antwort</button>'
    return '<p><strong>Keine Aktion verfügbar.</strong></p>'


TRADE_DETAIL_ORIGINS = frozenset({
    "home", "trades", "album_trades", "notifications"
})


def trade_detail_back_context(origin, album_id, back_tab):
    if origin == "home":
        return "/", "Home"
    if origin == "notifications":
        return "/notifications", "Benachrichtigungen"
    if origin == "album_trades":
        return f"/album/{album_id}/trades?tab={back_tab}", "Album-Tauschbörse"
    return f"/trades?tab={back_tab}", "Tauschbörse"


def trade_rating_html(rating_state):
    if rating_state is None:
        return ""
    if rating_state.code == TradeRatingCode.ALREADY_RATED:
        return """
        <section class="card trade-rating-card trade-product-rating" aria-label="Bewertung">
            <div>
                <small>Bewertung gespeichert</small>
                <h2>Danke für deine Bewertung</h2>
                <p>Du hast diesen Trade bereits bewertet.</p>
            </div>
        </section>
        """
    if rating_state.code == TradeRatingCode.NOT_QUALIFIED:
        return '<span class="trade-product-contract-state">Dieser Trade kann noch nicht bewertet werden.</span>'
    if rating_state.code != TradeRatingCode.READY:
        return ""
    stars = "".join(
        f'<label><input type="radio" name="stars" value="{value}" required>'
        f'<span>{value} ★</span></label>'
        for value in range(1, 6)
    )
    return f"""
    <section class="card trade-rating-card trade-product-rating" aria-labelledby="trade-rating-title">
        <div>
            <small>Deine Erfahrung</small>
            <h2 id="trade-rating-title">Wie war der Tausch?</h2>
            <p>Bewerte deinen Tauschpartner und hilf anderen Sammlern.</p>
        </div>
        <form method="POST" action="/trades/{rating_state.legacy_trade_request_id}/rating">
            <div class="trade-rating-stars">{stars}</div>
            <button class="trade-product-primary" type="submit">Bewertung speichern</button>
        </form>
    </section>
    """


@app.route("/trade/<int:trade_id>")
@app.route("/trades/<int:trade_id>")
def trade_detail(trade_id):
    con = get_db()
    cleanup_smartdeal_runtime(con)
    sender_name_select = public_username_select(con, "sender", "sender_name")
    receiver_name_select = public_username_select(con, "receiver", "receiver_name")
    trade = con.execute(
        f"""
        SELECT trade_requests.*,
               {sender_name_select},
               {receiver_name_select},
               albums.name AS album_name
        FROM trade_requests
        JOIN users sender ON sender.id = trade_requests.from_user_id
        JOIN users receiver ON receiver.id = trade_requests.to_user_id
        JOIN albums ON albums.id = trade_requests.album_id
        WHERE trade_requests.id=?
        AND (trade_requests.from_user_id=? OR trade_requests.to_user_id=?)
        """,
        (trade_id, current_user_id(), current_user_id())
    ).fetchone()
    smart_state = None
    smart_origin = trade_has_smart_origin(con, trade) if trade else False
    if trade and is_smart_trade_request(trade):
        smart_state = SmartTradeRequestService(con).inspect(
            trade_id,
            current_user_id(),
            recheck=True,
        )
        trade = con.execute(
            f"""
            SELECT trade_requests.*,
                   {sender_name_select},
                   {receiver_name_select},
                   albums.name AS album_name
            FROM trade_requests
            JOIN users sender ON sender.id = trade_requests.from_user_id
            JOIN users receiver ON receiver.id = trade_requests.to_user_id
            JOIN albums ON albums.id = trade_requests.album_id
            WHERE trade_requests.id=?
            AND (trade_requests.from_user_id=? OR trade_requests.to_user_id=?)
            """,
            (trade_id, current_user_id(), current_user_id()),
        ).fetchone()
    shipping_status = (
        shipping_status_for_trade(con, trade_id) if trade else None
    )
    receipt_status = (
        receipt_status_for_trade(con, trade_id) if trade else None
    )
    problem_schema_enabled = problem_schema_available(con)
    problem_reports = (
        problem_reports_for_trade(con, trade_id) if trade else ()
    )
    timeline_context = (
        trade_timeline_context(con, trade_id) if trade else None
    )
    rating_state = (
        TradeRatingService(con).state_for_request(
            trade_id, current_user_id()
        )
        if trade else None
    )
    partner_successful_trade_count = 0
    if trade:
        partner_user_id = (
            trade["from_user_id"]
            if trade["to_user_id"] == current_user_id()
            else trade["to_user_id"]
        )
        partner_successful_trade_count = SuccessfulTradeProjectionService(
            con
        ).count_for_user(partner_user_id)
    con.close()

    if not trade:
        return redirect("/trades?message=Tauschangebot%20nicht%20gefunden")

    album_id = trade["album_id"]
    album, by_code, gesammelt, doppelte, prozent, total = lade_album(album_id)
    missing_count = total - gesammelt
    is_receiver = trade["to_user_id"] == current_user_id()
    partner_name = trade["sender_name"] if is_receiver else trade["receiver_name"]
    give_codes = json.loads(trade["give_codes"] or "[]")
    get_codes = json.loads(trade["get_codes"] or "[]")
    du_bekommst = give_codes if is_receiver else get_codes
    du_gibst = get_codes if is_receiver else give_codes
    status_label = trade_status_label(trade, is_receiver)
    successfully_completed = trade_is_successfully_completed(
        trade,
        timeline_context,
        receipt_status,
        problem_reports,
    )
    if successfully_completed:
        status_label = "Abgeschlossen"
    if trade["status"] == "accepted" and shipping_status is not None:
        status_label = trade_shipping_status_label(
            shipping_status, receipt_status, problem_reports
        )
    lifecycle_state = (
        timeline_context.get("lifecycle_state") if timeline_context else None
    )
    if lifecycle_state == "closed_with_problem":
        status_label = "Trade mit Problem beendet"
    elif lifecycle_state == "problem_resolved_after_close":
        status_label = "Problem nachträglich gelöst"
    back_tab = "agreements" if trade["status"] == "accepted" else "requests"
    origin = request.args.get("origin", "").strip()
    safe_origin = origin if origin in TRADE_DETAIL_ORIGINS else ""
    back_href, back_label = trade_detail_back_context(safe_origin, album_id, back_tab)
    timeline_items = trade_timeline_items(
        trade,
        current_user_id(),
        timeline_context,
        shipping_status,
        receipt_status,
        problem_reports,
        rating_state,
    )
    primary_action_html = trade_detail_primary_action(
        trade,
        is_receiver,
        shipping_status,
        receipt_status,
        problem_reports,
        problem_schema_enabled,
        successfully_completed,
        timeline_context.get("completed_at") if timeline_context else None,
        lifecycle_state,
    )
    rating_html = trade_rating_html(rating_state)
    message_html = sammlr_feedback_html(request.args.get("message", ""))
    smart_notice_html = ""
    smart_deadline_html = (
        f"<p>Antwortfrist: {sammlr_time_html(smart_state.expires_at)}</p>"
        if smart_state and smart_state.expires_at else ""
    )
    if smart_state and smart_state.code in (
        SmartTradeRequestCode.PACKAGE_CHANGED,
        SmartTradeRequestCode.OBSOLETE,
        SmartTradeRequestCode.EXPIRED,
    ):
        if smart_state.code == SmartTradeRequestCode.PACKAGE_CHANGED:
            heading = "Paket nicht mehr vollständig verfügbar"
            body = (
                "Das ursprüngliche Smart-Paket bleibt unverändert gespeichert "
                "und kann nicht angenommen werden."
            )
        elif smart_state.code == SmartTradeRequestCode.OBSOLETE:
            heading = "Smart-Paket beendet"
            body = "Es ist kein bilaterales Paket mehr ausführbar."
        else:
            heading = "Smart-Anfrage abgelaufen"
            body = "Die 48-stündige Anfragefrist ist beendet."
        unavailable_html = ""
        if smart_state.recheck is not None:
            give_missing = ", ".join(
                f"{display_code(code)} ({amount}x)"
                for code, amount in smart_state.recheck.unavailable_give
            )
            get_missing = ", ".join(
                f"{display_code(code)} ({amount}x)"
                for code, amount in smart_state.recheck.unavailable_get
            )
            unavailable_parts = []
            if give_missing:
                unavailable_parts.append(
                    f"Beim Absender nicht mehr frei: {escape(give_missing)}"
                )
            if get_missing:
                unavailable_parts.append(
                    f"Beim Empfänger nicht mehr frei: {escape(get_missing)}"
                )
            if unavailable_parts:
                unavailable_html = "<p>" + "<br>".join(unavailable_parts) + "</p>"
        if trade["from_user_id"] == current_user_id():
            smart_options_html = f"""
                <a class="btn green" href="/album/{album_id}/smart-trades">Neu berechnen</a>
                <a class="btn gray" href="{back_href}">Abbrechen</a>
            """
        elif trade["status"] == "open":
            smart_options_html = f"""
                <form method="POST" action="/trade/{trade_id}/decline">
                    <button class="btn gray" type="submit">Abbrechen</button>
                </form>
                <p>Der Absender kann das Smart-Paket neu berechnen.</p>
            """
        else:
            smart_options_html = f'<a class="btn gray" href="{back_href}">Abbrechen</a>'
        smart_notice_html = f"""
        <section class="card" aria-label="Smart-Paket-Hinweis">
            <h3>{heading}</h3>
            <p>{body}</p>
            {unavailable_html}
            <div class="trade-request-actions">
                {smart_options_html}
            </div>
        </section>
        """
        primary_action_html = (
            '<button type="button" class="sticker-list-check trade-product-primary" disabled>'
            'Smart-Paket nicht annehmbar</button>'
        )

    status_html = trade_product_status_html(
        trade,
        partner_name,
        is_receiver,
        status_label,
        shipping_status,
        receipt_status,
        problem_reports,
        successfully_completed,
        lifecycle_state,
    )
    exchange_get_label = "Du hast bekommen" if successfully_completed else "Du bekommst"
    exchange_give_label = "Du hast gegeben" if successfully_completed else "Du gibst"
    action_section_html = (
        f"""
        <aside class="sticker-list-tradebar trade-detail-bar">
            <div class="trade-product-actions" aria-label="Nächste Aktion">
                {primary_action_html}
            </div>
        </aside>
        """
        if primary_action_html and not successfully_completed else ""
    )
    partner_initial = escape(partner_name[:1].upper() if partner_name else "?")

    html = f"""
    <html><head>{style()}</head><body class="s31-product-page sticker-list-page trade-detail-page trade-product-page s30-reference-page s30-deal-page"><div class="trade-product-shell trade-detail-shell">
    {app_header(variant="compact")}
    {consume_trophy_popup_html(album_id)}

    <main class="trade-product-main trade-detail-paper">
        <a class="sticker-list-back" href="{back_href}">← zurück zu {escape(back_label)}</a>

        <header class="trade-product-title sticker-list-header app-workflow-header">
            <div>
                <p>{escape(album['name'])}</p>
                <h1>Trade mit {escape(partner_name)}</h1>
            </div>
            <span class="trade-product-contract-state">
                <a class="trade-partner-profile-link" href="/profil/{quote(partner_name, safe='')}">{escape(partner_name)}</a>
            </span>
            <a class="trade-product-partner trade-partner-profile-link"
               href="/profil/{quote(partner_name, safe='')}"
               aria-label="Profil von {escape(partner_name)} öffnen">
                <span class="trade-product-avatar" aria-hidden="true">{partner_initial}</span>
                <span>
                    <strong>{escape(partner_name)}</strong>
                    <small>{partner_successful_trade_count} erfolgreiche Trades</small>
                </span>
            </a>
        </header>

        {message_html}
        {status_html}
        <div class="trade-product-meta">{smart_trade_badge_html(smart_origin)}{smart_deadline_html}</div>

        <section class="trade-product-card trade-product-exchange" aria-labelledby="trade-product-exchange-heading">
            <h2 id="trade-product-exchange-heading">Tauschinhalt</h2>
            <div class="trade-product-exchange-grid">
                <div aria-label="Erwartete Lieferung: {len(du_bekommst)} Sticker">
                    <span>{exchange_get_label}</span>
                    <div class="trade-product-codes">
                        {trade_detail_sticker_items(du_bekommst, "get")}
                    </div>
                </div>
                <div aria-label="Vereinbart abzugeben: {len(du_gibst)} Sticker">
                    <span>{exchange_give_label}</span>
                    <div class="trade-product-codes">
                        {trade_detail_sticker_items(du_gibst, "give")}
                    </div>
                </div>
            </div>
        </section>
        {smart_notice_html}
        {action_section_html}
        {rating_html}
        {trade_timeline_html(timeline_items, partner_name)}
        <div class="trade-product-problem-history">
            {trade_problem_history_html(problem_reports, current_user_id())}
        </div>
    </main>

    {bottom_nav("tauschen")}
    </div></body></html>
    """
    return html


@app.route("/trades/<int:trade_id>/rating", methods=["POST"])
def create_trade_rating(trade_id):
    raw_stars = request.form.get("stars", "")
    try:
        stars = int(raw_stars)
    except (TypeError, ValueError):
        abort(400)
    if str(stars) != raw_stars.strip():
        abort(400)

    con = get_db()
    result = TradeRatingService(con).create(
        trade_id, current_user_id(), stars
    )
    con.close()
    if result.code == TradeRatingCode.INVALID_STARS:
        abort(400)
    if result.code == TradeRatingCode.UNAUTHORIZED:
        abort(404)
    if result.code == TradeRatingCode.NOT_QUALIFIED:
        return redirect(
            f"/trades/{trade_id}?message="
            f"{quote('Dieser Trade kann noch nicht bewertet werden.')}"
        )
    return redirect(f"/trades/{trade_id}")


def trade_request_popup_html():
    incoming = first_open_incoming_trade_request()
    if not incoming:
        return ""

    album_id = incoming["album_id"]
    return f"""
    <div class="trade-request-popup" id="tradeRequestPopup">
        <div>
            <strong>Neue Tauschanfrage</strong>
            <p>In deiner Tauschbörse wartet eine offene Anfrage.</p>
        </div>
        <div class="trade-request-popup-actions">
            <a href="/album/{album_id}/trades?tab=incoming">Ansehen</a>
            <button type="button" onclick="document.getElementById('tradeRequestPopup').style.display='none'">Später</button>
        </div>
    </div>
    """


@app.route("/album/<album_id>/trades")
def album_trades(album_id):
    con = get_db()
    album = con.execute(
        "SELECT id, name FROM albums WHERE id=?",
        (album_id,),
    ).fetchone()
    if album is None:
        con.close()
        abort(404)
    availability_inventory = InventoryReadService(con)
    privacy = album_privacy_service(con)
    pool_user_ids = set(privacy.trade_pool_user_ids(album_id))
    tab = request.args.get("tab", "").strip()

    andere_user = con.execute(
        """
        SELECT users.id, users.username
        FROM users
        JOIN user_albums ON user_albums.user_id = users.id
        WHERE users.id != ? AND user_albums.album_id = ?
        """,
        (current_user_id(), album_id)
    ).fetchall()
    andere_user = [
        user for user in andere_user
        if (
            current_user_id() in pool_user_ids
            and user["id"] in pool_user_ids
        )
    ]

    alle_codes = all_codes(album_id)
    coverage_service = TradeCoverageService(availability_inventory, privacy)
    ranked_matches = ExecutableTradeMatchService(coverage_service).matches(
        current_user_id(),
        album_id,
        alle_codes,
        (user["id"] for user in andere_user),
    )
    users_by_id = {user["id"]: user for user in andere_user}

    incoming_requests = con.execute(
        """
        SELECT trade_requests.*, users.username AS sender_name
        FROM trade_requests
        JOIN users ON users.id = trade_requests.from_user_id
        WHERE trade_requests.album_id=? AND trade_requests.to_user_id=? AND trade_requests.status IN ('open', 'accepted')
        ORDER BY trade_requests.created_at DESC
        """,
        (album_id, current_user_id())
    ).fetchall()

    outgoing_requests = con.execute(
        """
        SELECT trade_requests.*, users.username AS receiver_name
        FROM trade_requests
        JOIN users ON users.id = trade_requests.to_user_id
        WHERE trade_requests.album_id=? AND trade_requests.from_user_id=? AND trade_requests.status IN ('open', 'accepted')
        ORDER BY trade_requests.created_at DESC
        """,
        (album_id, current_user_id())
    ).fetchall()

    incoming_open_requests = [trade for trade in incoming_requests if trade["status"] == "open"]
    outgoing_open_requests = [trade for trade in outgoing_requests if trade["status"] == "open"]
    accepted_requests = [trade for trade in incoming_requests + outgoing_requests if trade["status"] == "accepted"]
    incoming_count = len(incoming_open_requests)
    outgoing_count = len(outgoing_open_requests)
    request_count = incoming_count + outgoing_count

    if tab in ("incoming", "outgoing"):
        tab = "requests"
    if tab not in ("partners", "agreements", "requests"):
        tab = "requests" if incoming_count > 0 else "partners"

    request_badge = f'<span class="trade-tab-badge danger">{request_count}</span>' if request_count else ""
    agreement_badge = f'<span class="trade-tab-badge">{len(accepted_requests)}</span>' if accepted_requests else ""
    active_trade_partner_ids = {
        row["partner_id"] for row in con.execute(
            """
            SELECT
                CASE
                    WHEN from_user_id=? THEN to_user_id
                    ELSE from_user_id
                END AS partner_id
            FROM trade_requests
            WHERE album_id=?
            AND status IN ('open', 'accepted')
            AND (from_user_id=? OR to_user_id=?)
            """,
            (current_user_id(), album_id, current_user_id(), current_user_id())
        ).fetchall()
    }

    html = f"""
    <html><head>{style()}</head><body class="s31-product-page s30-reference-page r2-trade-journey-page r2-trade-hub-page"><div class="container">
    {app_header()}
    <main class="trade-concept-shell" aria-label="Albumbezogen tauschen">
    <a class="r2-trade-back" aria-label="Zurück zu {escape(album['name'])}" href="/album/{album_id}">← Zurück</a>
    <section class="trade-concept-intro r2-trade-intro">
        <p class="r2-trade-eyebrow">{escape(album['name'])}</p>
        <h1>Tauschen</h1>
        <p>{'Beantworte neue Anfragen oder finde den nächsten passenden Tausch.' if tab == 'requests' else 'Finde passende Sammler und schließe gezielt deine Lücken.' if tab == 'partners' else 'Behalte deine laufenden Trades für dieses Album im Blick.'}</p>
    </section>
    <div class="r2-trade-entry-actions" aria-label="Tauschwege">
        <a class="trade-concept-primary-action" href="/album/{album_id}/smart-trades">SmartMatch öffnen</a>
        <a class="trade-concept-secondary-action" href="/trades">Alle Trades</a>
    </div>

    <div class="trade-tabs">
    <nav class="trade-concept-tabs r2-album-trade-tabs" aria-label="Album-Tauschbereiche">
        <a class="{'is-active' if tab == 'partners' else ''}" href="/album/{album_id}/trades?tab=partners" {'aria-current="page"' if tab == 'partners' else ''}>
            Tauschpartner
        </a>
        <a class="{'is-active' if tab == 'agreements' else ''}" href="/album/{album_id}/trades?tab=agreements" {'aria-current="page"' if tab == 'agreements' else ''}>
            Trades {agreement_badge}
        </a>
        <a class="{'is-active' if tab == 'requests' else ''}" href="/album/{album_id}/trades?tab=requests" {'aria-current="page"' if tab == 'requests' else ''}>
            Anfragen {request_badge}
        </a>
    </nav>
    </div>
    <section class="trade-concept-content r2-album-trade-content">
    """

    if tab == "agreements":
        if not accepted_requests:
            html += """
            <div class="card trade-empty-card">
                <h2>Noch nichts offen.</h2>
                <p>Angenommene Tauschanfragen erscheinen hier.</p>
            </div>
            """

        for trade in accepted_requests:
            is_receiver = trade["to_user_id"] == current_user_id()
            is_smart_display = trade_has_smart_origin(con, trade)
            partner_name = trade["sender_name"] if is_receiver else trade["receiver_name"]
            give_codes = json.loads(trade["give_codes"] or "[]")
            get_codes = json.loads(trade["get_codes"] or "[]")
            shipping_status = shipping_status_for_trade(con, trade["id"])
            receipt_status = receipt_status_for_trade(con, trade["id"])
            problem_reports = problem_reports_for_trade(con, trade["id"])
            timeline_context = trade_timeline_context(con, trade["id"])
            status_label = (
                trade_shipping_status_label(
                    shipping_status, receipt_status, problem_reports
                )
                if shipping_status is not None
                else trade_status_label(trade, is_receiver)
            )
            request_actions = trade_completion_actions(
                trade, partner_name, is_receiver, shipping_status,
                receipt_status, problem_reports
            )
            attention_html = trade_attention_html(
                current_user_id(), timeline_context, shipping_status,
                receipt_status, problem_reports
            )
            received_count = len(give_codes) if is_receiver else len(get_codes)
            given_count = len(get_codes) if is_receiver else len(give_codes)

            html += f"""
            <article class="trade-person-card trade-request-card r2-trade-process-card">
                <div class="trade-partner-head">
                    <h2>{partner_name}</h2>
                    {trade_status_chip(status_label)}
                </div>
                <div class="trade-request-type-row">
                    {trade_request_type_badge_html(is_smart_display)}
                </div>
                <div class="trade-partner-stats">
                    <div>
                        <strong>{received_count}</strong>
                        <span>Du erhältst</span>
                    </div>
                    <div>
                        <strong>{given_count}</strong>
                        <span>Du gibst</span>
                    </div>
                </div>
                {attention_html}
                <a class="trade-detail-link" href="/trades/{trade['id']}?origin=album_trades">Ansehen</a>
                {request_actions}
            </article>
            """

    elif tab == "requests":
        if not incoming_open_requests and not outgoing_open_requests:
            html += """
            <div class="card trade-empty-card">
                <h2>Noch nichts offen.</h2>
                <p>Anfragen an dich und deine Anfragen erscheinen hier.</p>
            </div>
            """

        if incoming_open_requests:
            html += '<h2 class="global-trade-subtitle">Anfragen an dich</h2>'

        for trade in incoming_open_requests:
            give_codes = json.loads(trade["give_codes"] or "[]")
            get_codes = json.loads(trade["get_codes"] or "[]")
            is_receiver = True
            status_label = trade_status_label(trade, is_receiver)
            request_actions = trade_open_actions(trade)
            is_smart_display = trade_has_smart_origin(con, trade)

            html += f"""
            <article class="trade-person-card trade-request-card r2-trade-process-card">
                <div class="trade-partner-head">
                    <h2>{trade['sender_name']}</h2>
                    {trade_status_chip(status_label)}
                </div>
                <div class="trade-request-type-row">
                    {trade_request_type_badge_html(is_smart_display)}
                </div>
                <div class="trade-partner-stats">
                    <div>
                        <strong>{len(give_codes)}</strong>
                        <span>Du erhältst</span>
                    </div>
                    <div>
                        <strong>{len(get_codes)}</strong>
                        <span>Du gibst</span>
                    </div>
                </div>
                <div class="trade-request-summary">
                    <p><strong>Du erhältst:</strong> {trade_code_summary(give_codes)}</p>
                    <p><strong>Du gibst:</strong> {trade_code_summary(get_codes)}</p>
                </div>
                <a class="trade-detail-link" href="/trades/{trade['id']}?origin=album_trades">Ansehen</a>
                {request_actions}
            </article>
            """

        if outgoing_open_requests:
            html += '<h2 class="global-trade-subtitle">Deine Anfragen</h2>'

        for trade in outgoing_open_requests:
            give_codes = json.loads(trade["give_codes"] or "[]")
            get_codes = json.loads(trade["get_codes"] or "[]")
            is_receiver = False
            status_label = trade_status_label(trade, is_receiver)
            request_actions = '<p class="trade-request-waiting">Wartet auf Antwort</p>'
            is_smart_display = trade_has_smart_origin(con, trade)

            html += f"""
            <article class="trade-person-card trade-request-card r2-trade-process-card">
                <div class="trade-partner-head">
                    <h2>{trade['receiver_name']}</h2>
                    {trade_status_chip(status_label)}
                </div>
                <div class="trade-request-type-row">
                    {trade_request_type_badge_html(is_smart_display)}
                </div>
                <div class="trade-partner-stats">
                    <div>
                        <strong>{len(get_codes)}</strong>
                        <span>Du erhältst</span>
                    </div>
                    <div>
                        <strong>{len(give_codes)}</strong>
                        <span>Du gibst</span>
                    </div>
                </div>
                <div class="trade-request-summary">
                    <p><strong>Du erhältst:</strong> {trade_code_summary(get_codes)}</p>
                    <p><strong>Du gibst:</strong> {trade_code_summary(give_codes)}</p>
                </div>
                <a class="trade-detail-link" href="/trades/{trade['id']}?origin=album_trades">Ansehen</a>
                {request_actions}
            </article>
            """

    elif not andere_user:
        html += """
        <div class="card trade-empty-card">
            <h2>Noch keine passenden Sammler.</h2>
            <p>Sobald andere Nutzer dieses Album hinzufügen, erscheinen sie hier.</p>
        </div>
        """

    if tab == "partners":
        rendered_partner_count = 0
        for match in ranked_matches:
            user = users_by_id[match.partner_user_id]
            if match.partner_user_id in active_trade_partner_ids:
                continue
            du_suchst = sorted(
                match.receive_codes,
                key=lambda x: [int(part) if part.isdigit() else part for part in __import__('re').split(r'(\d+)', x)]
            )
            du_bietest_an = sorted(
                match.give_codes,
                key=lambda x: [int(part) if part.isdigit() else part for part in __import__('re').split(r'(\d+)', x)]
            )

            rendered_partner_count += 1
            match_count = match.executable_quantity

            username = escape(user["username"])
            username_path = quote(user["username"], safe="")
            partner_initial = escape((user["username"][:1] or "S").upper())
            html += f"""
            <article class="trade-person-card trade-partner-concept-card r2-album-partner-card">
                <a class="trade-person-identity" href="/profil/{username_path}"
                   aria-label="Profil von {username} öffnen">
                    <span class="trade-person-avatar" aria-hidden="true">{partner_initial}</span>
                    <span>
                        <strong>{username}</strong>
                        <small>Direkter Tausch möglich · {match_count}</small>
                    </span>
                </a>
                <div class="trade-directed-match" aria-label="Gerichtete Tauschmöglichkeit">
                    <p><strong>{username} hat <em>{len(du_suchst)} Sticker</em>, die dir fehlen.</strong></p>
                    <p><strong>Du hast <em>{len(du_bietest_an)} Sticker</em>, die {username} sucht.</strong></p>
                </div>
                <a class="trade-concept-primary-action" href="/album/{album_id}/trade/{user['id']}">Tausch starten</a>
            </article>
            """

        if rendered_partner_count == 0 and andere_user:
            html += """
            <div class="card trade-empty-card">
                <h2>Noch keine passenden Sammler.</h2>
                <p>Offene und angenommene Tauschanfragen findest du in den Anfrage-Bereichen.</p>
            </div>
            """

    html += "</section></main>"
    html += bottom_nav("tauschen")
    html += "</div></body></html>"
    con.close()
    return html

# --- Album Statistik Route ---

@app.route("/album/<album_id>/statistik")
def album_statistik(album_id):
    con = get_db()
    projection = StatisticsProjectionService(con).for_album(
        current_user_id(), album_id
    )
    con.close()
    if projection is None:
        abort(404)

    current = projection.current
    career = projection.career
    completion_line = (
        f"Erstmals abgeschlossen: {escape(format_sammlr_date(career.completed_at))}"
        if career.completed_at else "Noch kein kanonischer Abschluss erfasst"
    )
    duration_line = (
        f"Dauer bis zum ersten Abschluss: {career.first_completion_duration_days} Tage"
        if career.first_completion_duration_days is not None else ""
    )
    if career.history_available:
        history_html = f"""
        <p>{career.recorded_acquisition_quantity} Stickerzugänge seit Historienstart erfasst</p>
        <p>{career.successful_trades.received_quantity_total} über erfolgreiche Trades erhalten</p>
        <p>{career.successful_trades.given_quantity_total} über erfolgreiche Trades abgegeben</p>
        <p>{career.successful_trades.successful_trade_count} erfolgreiche Trades</p>
        <p>{career.valid_trophy_count or 0} gültige Trophäen</p>
        <p>{completion_line}</p>
        {f'<p>{duration_line}</p>' if duration_line else ''}
        <p class="statistics-history-note">Werte vor dem Historienstart sind unbekannt und wurden nicht rekonstruiert.</p>
        """
    else:
        history_html = """
        <p>Historische Werte sind auf diesem Datenstand nicht verfügbar.</p>
        <p class="statistics-history-note">Der heutige Bestand wird nicht als Karrierehistorie ausgegeben.</p>
        """

    html = f"""
    <html><head>{style()}</head><body class="s31-product-page"><div class="container">
    {app_header(escape(current.name), "Album-Statistik")}
    <a class="sammlr-back-link" href="/album/{album_id}">← Zurück zum Album</a>

    <div class="card">
        <h2>Aktueller Stand</h2>
        <div class="big">{current.percent}%</div>
        <div class="progress" data-progress="{current.percent}%">
            <div class="progress-bar" style="width:{current.percent}%;"></div>
        </div>
    </div>

    <div class="stats">
        <div class="stat">
            <div class="big">{current.collected}</div>
            <p>Gesammelt</p>
        </div>
        <div class="stat">
            <div class="big">{current.missing}</div>
            <p>Fehlend</p>
        </div>
        <div class="stat">
            <div class="big">{current.duplicate_quantity}</div>
            <p>Doppelte</p>
        </div>
        <div class="stat">
            <div class="big">{current.total}</div>
            <p>Gesamt</p>
        </div>
    </div>

    <div class="statistics-card">
        <div class="statistics-block">
            <h2>Karriere in diesem Album</h2>
            {history_html}
        </div>
    </div>

    {bottom_nav("sammlung")}
    </div></body></html>
    """
    return html

def code_sort_key(code):
    return [int(part) if part.isdigit() else part for part in __import__('re').split(r'(\d+)', code)]


def user_album_quantities(con, user_id, album_id):
    return InventoryReadService(con).album(
        user_id, album_id, all_codes(album_id)
    ).quantities


def user_album_inventory(con, user_id, album_id):
    return InventoryReadService(con).album(
        user_id, album_id, all_codes(album_id)
    )


def trade_search_text(code, section="", team=""):
    return f"{code} {display_code(code)} {section} {team}".lower()


def render_trade_wall(album_id, allowed_counts, mode):
    allowed_codes = set(allowed_counts.keys())
    slot_class = "missing trade-slot" if mode == "get" else "duplicate trade-slot"
    html = ""

    def render_slot(code, section="", team=""):
        max_count = allowed_counts.get(code, 0)
        if max_count <= 0:
            return ""

        display = display_code(code)
        search_text = trade_search_text(code, section, team)
        return (
            f'<button type="button" class="slot {slot_class}" '
            f'data-code="{code}" data-display="{display}" data-mode="{mode}" '
            f'data-max="{max_count}" data-search="{search_text}">'
            f'{sticker_card_inner(album_id, code, {})}</button>'
        )

    if album_id == "em24":
        current_section = ""
        open_wall = False

        for sticker in build_em24():
            code = sticker["id"]
            if code not in allowed_codes:
                continue

            section = sticker["section"]
            if section != current_section:
                if open_wall:
                    html += "</div>"
                current_section = section
                html += f'<h2 class="section-title">{current_section}</h2><div class="wall trade-wall">'
                open_wall = True

            html += render_slot(code, current_section)

        if open_wall:
            html += "</div>"

    elif album_id == "wm26":
        current_chapter = ""
        current_team = ""
        open_wall = False

        for sticker in sorted(build_wm26(), key=wm26_wall_order):
            code = sticker["id"]
            if code not in allowed_codes:
                continue

            chapter = wm26_chapter_for_wall(sticker)
            team_name = wm26_team_for_wall(sticker)

            if chapter != current_chapter:
                if open_wall:
                    html += "</div>"
                    open_wall = False

                current_chapter = chapter
                current_team = ""
                html += f'<h2 class="section-title album-chapter-title"><span>{current_chapter}</span></h2>'

            if team_name and team_name != current_team:
                if open_wall:
                    html += "</div>"
                    open_wall = False

                current_team = team_name
                html += f'<h3 class="team-title"><span>{current_team}</span></h3>'

            if not open_wall:
                html += '<div class="wall trade-wall">'
                open_wall = True

            html += render_slot(code, current_chapter, current_team)

        if open_wall:
            html += "</div>"

    else:
        html += '<div class="wall trade-wall">'
        for code in sorted(allowed_codes, key=code_sort_key):
            html += render_slot(code)
        html += "</div>"

    if not html:
        return '<div class="card trade-empty-card"><h2>Keine passenden Sticker</h2><p>Für diesen Schritt gibt es aktuell keine Treffer.</p></div>'

    return html


def trade_candidates(album_id, my_quantities, partner_quantities):
    codes = all_codes(album_id)

    get_counts = {}
    give_counts = {}

    for code in codes:
        my_quantity = my_quantities.get(code, 0)
        partner_quantity = partner_quantities.get(code, 0)

        if my_quantity == 0 and partner_quantity >= 2:
            get_counts[code] = partner_quantity - 1

        if my_quantity >= 2 and partner_quantity == 0:
            give_counts[code] = my_quantity - 1

    return get_counts, give_counts


def availability_trade_candidates(album_id, my_inventory, partner_inventory):
    get_counts = {}
    give_counts = {}

    for code in all_codes(album_id):
        mine = my_inventory.availability_snapshot_for(code)
        partner = partner_inventory.availability_snapshot_for(code)

        if mine.missing and partner.is_available:
            get_counts[code] = partner.effective_available

        if mine.is_available and partner.missing:
            give_counts[code] = mine.effective_available

    return get_counts, give_counts


@app.route("/album/<album_id>/trade/<int:other_user_id>")
@app.route("/album/<album_id>/trades/<int:other_user_id>")
def trade_center(album_id, other_user_id):
    con = get_db()
    message = request.args.get("message", "")
    privacy = album_privacy_service(con)

    if not (
        privacy.is_trade_pool_enabled(current_user_id(), album_id)
        and privacy.is_trade_pool_enabled(other_user_id, album_id)
        and CommunityService(con).can_start_interaction(
            current_user_id(), other_user_id
        )
    ):
        con.close()
        abort(404)

    other_user = con.execute(
        "SELECT * FROM users WHERE id=?",
        (other_user_id,)
    ).fetchone()

    if not other_user:
        con.close()
        return redirect(f"/album/{album_id}/trades")

    mein_bestand = user_album_inventory(con, current_user_id(), album_id)
    anderer_bestand = user_album_inventory(con, other_user_id, album_id)
    get_counts, give_counts = availability_trade_candidates(
        album_id, mein_bestand, anderer_bestand
    )

    du_bekommst = sorted(get_counts.keys(), key=code_sort_key)
    du_gibst = sorted(give_counts.keys(), key=code_sort_key)
    max_receive_count = sum(give_counts.values())
    receive_limit_text = (
        f"Du kannst bis zu {max_receive_count} fehlende Sticker auswählen."
        if max_receive_count > 0
        else "Du hast aktuell keine passenden Doppelten zum Anbieten."
    )
    get_wall = render_trade_wall(album_id, get_counts, "get")
    give_wall = render_trade_wall(album_id, give_counts, "give")
    error_html = sammlr_feedback_html(message) if message else ''

    html = f"""
    <html><head>{style()}</head><body class="s31-product-page s30-reference-page r2-trade-journey-page r2-trade-composer-page"><div class="container">
    {app_header()}
    <main class="trade-concept-shell r2-trade-composer" aria-label="Manuelle Tauschanfrage">
    <a class="r2-trade-back" href="/album/{album_id}/trades">← zurück zu Tauschpartner</a>
    <section class="trade-concept-intro r2-trade-intro">
        <p class="r2-trade-eyebrow">Manuelle Tauschanfrage</p>
        <h1>Tausch mit {escape(other_user['username'])}</h1>
        <p>Wähle deine fehlenden Sticker, biete passende Doppelte an und prüfe das Paket vor dem Senden.</p>
    </section>
    {error_html}

    <div class="trade-wizard" id="tradeWizard">
        <div class="trade-stepper">
            <button type="button" class="trade-step-pill active" data-step-label="get">1 Fehlende</button>
            <button type="button" class="trade-step-pill" data-step-label="give">2 Doppelte</button>
            <button type="button" class="trade-step-pill" data-step-label="final">3 Prüfen</button>
        </div>

        <section class="trade-step active trade-selection-step" id="tradeStepGet" data-step="get" data-mode="get">
            <div class="trade-step-head">
                <div>
                    <h2>Fehlende auswählen</h2>
                    <p>Suche die Sticker aus, die dir noch fehlen.</p>
                    <p class="trade-selection-hint">{receive_limit_text}</p>
                </div>
                <strong id="tradeGetCount">0</strong>
            </div>
            <div class="trade-search-row">
                <input class="sticker-search trade-search" type="search" placeholder="Sticker oder Team suchen..." autocomplete="off" data-trade-search="get">
                <button type="button" class="btn gray trade-add-visible-button" data-add-visible-trade="get">Alle hinzufügen</button>
            </div>
            <div class="pending-input-error" id="tradeReceiveLimitError" style="display:none;"></div>
            <div class="search-debug-box trade-search-feedback" data-trade-feedback="get" style="display:none;"></div>
            {get_wall}
        </section>

        <section class="trade-step trade-selection-step" id="tradeStepGive" data-step="give" data-mode="give">
            <div class="trade-step-head">
                <div>
                    <h2>Doppelte auswählen</h2>
                    <p>Wähle Sticker aus deinen Doppelten aus, die dein Tauschpartner gebrauchen kann.</p>
                </div>
                <strong id="tradeGiveCount">0</strong>
            </div>
            <div class="trade-search-row">
                <input class="sticker-search trade-search" type="search" placeholder="Sticker oder Team suchen..." autocomplete="off" data-trade-search="give">
                <button type="button" class="btn gray trade-add-visible-button" data-add-visible-trade="give">Alle hinzufügen</button>
            </div>
            <div class="search-debug-box trade-search-feedback" data-trade-feedback="give" style="display:none;"></div>
            {give_wall}
        </section>

        <section class="trade-step" id="tradeStepFinal" data-step="final">
            <div class="trade-step-head">
                <div>
                    <h2>Tauschanfrage prüfen</h2>
                    <p>Prüfe die Mengen vor der Anfrage.</p>
                </div>
            </div>
            <form method="POST" action="/album/{album_id}/trade/{other_user_id}/request" id="tradeRequestForm">
                <div class="trade-review-grid">
                    <div class="trade-review-panel">
                        <h3>Du suchst</h3>
                        <div class="pending-review-list" id="tradeGetReview"></div>
                    </div>
                    <div class="trade-review-panel">
                        <h3>Du bietest an</h3>
                        <div class="pending-review-list" id="tradeGiveReview"></div>
                    </div>
                </div>
                <div id="tradeHiddenInputs"></div>
                <div class="pending-input-error" id="tradeRuleError" style="display:none;"></div>
                <div class="trade-step-actions">
                    <button type="button" class="btn gray" data-next-step="give">Zurück</button>
                    <button class="btn green" type="submit" id="tradeSubmitButton">Tauschanfrage senden</button>
                </div>
            </form>
        </section>
    </div>

    <div class="smart-add-bar trade-selection-bar" id="tradeSelectionBar" style="display:none;">
        <div class="smart-add-count">
            <strong id="tradeActiveCount">0</strong> <span id="tradeActiveLabel">Sticker ausgewählt</span>
        </div>
        <div class="smart-add-actions">
            <a class="smart-add-secondary trade-cancel-link" href="/album/{album_id}/trades">Abbrechen</a>
            <button type="button" class="smart-add-primary" id="tradeReviewCurrentButton">Auswahl prüfen</button>
        </div>
    </div>

<script>
const tradeSelections = {{
    get: {{}},
    give: {{}}
}};
const maxReceiveSelection = {max_receive_count};
let activeTradeMode = 'get';

function tradeNormalizeQuery(value){{
    return String(value || '').trim().toUpperCase().replace(/[^A-Z0-9]/g, '');
}}

function tradeStickerNumber(code){{
    const match = tradeNormalizeQuery(code).match(/(\\d+)$/);
    return match ? match[1] : '';
}}

function tradeSlotAliases(slot){{
    const values = [
        slot.dataset.code || '',
        slot.dataset.display || '',
        slot.textContent || ''
    ];
    const aliases = [];

    values.forEach(function(value){{
        const compact = tradeNormalizeQuery(value);
        if(compact){{
            aliases.push(compact);
            aliases.push('STICKER' + compact);
            if(/^0+\\d+$/.test(compact)){{
                const withoutLeadingZero = String(parseInt(compact, 10));
                aliases.push(withoutLeadingZero);
                aliases.push('STICKER' + withoutLeadingZero);
            }}
        }}
    }});

    return Array.from(new Set(aliases));
}}

function tradeSlotNumbers(slot){{
    const numbers = [];
    tradeSlotAliases(slot).forEach(function(alias){{
        const match = alias.match(/(\\d+)$/);
        if(match){{
            numbers.push(match[1]);
            numbers.push(String(parseInt(match[1], 10)));
        }}
    }});
    return Array.from(new Set(numbers));
}}

function tradeMatchesSlot(slot, rawTerm){{
    const term = String(rawTerm || '').trim();
    if(!term) return true;

    const normalizedTerm = tradeNormalizeQuery(term);
    if(!normalizedTerm) return true;

    if(/^\\d+$/.test(normalizedTerm)){{
        return tradeSlotNumbers(slot).includes(normalizedTerm);
    }}

    if(/[A-Z]/.test(normalizedTerm) && /\\d/.test(normalizedTerm)){{
        return tradeSlotAliases(slot).includes(normalizedTerm);
    }}

    return tradeNormalizeQuery(slot.dataset.search || slot.textContent || '').includes(normalizedTerm);
}}

function tradeSlotIsVisible(slot){{
    return slot && !slot.classList.contains('trade-search-hidden');
}}

function tradeWallHasVisibleSlot(wall){{
    return Array.from(wall.querySelectorAll('.trade-slot')).some(tradeSlotIsVisible);
}}

function tradeAreaHasVisibleSlot(startNode, stopMatcher){{
    let node = startNode.nextElementSibling;
    while(node && !stopMatcher(node)){{
        if(node.classList.contains('wall') && tradeWallHasVisibleSlot(node)){{
            return true;
        }}
        node = node.nextElementSibling;
    }}
    return false;
}}

function updateTradeVisibleSections(panel){{
    panel.querySelectorAll('.wall').forEach(function(wall){{
        wall.classList.toggle('search-section-hidden', !tradeWallHasVisibleSlot(wall));
    }});

    panel.querySelectorAll('.team-title').forEach(function(teamTitle){{
        const hasVisibleSlot = tradeAreaHasVisibleSlot(teamTitle, function(node){{
            return node.classList.contains('team-title') || node.classList.contains('section-title');
        }});
        teamTitle.classList.toggle('search-section-hidden', !hasVisibleSlot);
    }});

    panel.querySelectorAll('.section-title').forEach(function(sectionTitle){{
        const hasVisibleSlot = tradeAreaHasVisibleSlot(sectionTitle, function(node){{
            return node.classList.contains('section-title');
        }});
        sectionTitle.classList.toggle('search-section-hidden', !hasVisibleSlot);
    }});
}}

function updateTradeSearch(panel, term){{
    panel.querySelectorAll('.trade-slot').forEach(function(slot){{
        slot.classList.toggle('trade-search-hidden', !tradeMatchesSlot(slot, term));
    }});
    updateTradeVisibleSections(panel);

    const feedback = panel.querySelector('.trade-search-feedback');
    if(!feedback) return;

    if(!tradeNormalizeQuery(term)){{
        feedback.style.display = 'none';
        feedback.textContent = '';
        return;
    }}

    const count = Array.from(panel.querySelectorAll('.trade-slot')).filter(tradeSlotIsVisible).length;
    feedback.style.display = 'block';
    feedback.textContent = count === 0 ? 'Kein Treffer' : count + ' Treffer';
}}

function tradeTotal(mode){{
    return Object.values(tradeSelections[mode]).reduce(function(total, count){{
        return total + count;
    }}, 0);
}}

function tradeDisplayCode(code){{
    const slot = Array.from(document.querySelectorAll('.trade-slot')).find(function(item){{
        return item.dataset.code === code;
    }});
    return slot ? (slot.dataset.display || code) : code;
}}

function activeTradePanel(){{
    return document.querySelector('.trade-selection-step[data-mode="' + activeTradeMode + '"]');
}}

function tradeFindSlotByCode(mode, rawCode){{
    const needle = tradeNormalizeQuery(rawCode);
    if(!needle) return null;

    return Array.from(document.querySelectorAll('.trade-slot[data-mode="' + mode + '"]')).find(function(slot){{
        return tradeSlotAliases(slot).includes(needle);
    }}) || null;
}}

function showTradeReceiveLimitError(){{
    const error = document.getElementById('tradeReceiveLimitError');
    if(!error) return;

    error.textContent = 'Du kannst nur so viele fehlende Sticker auswählen, wie du später doppelt anbieten kannst.';
    error.style.display = 'block';
}}

function clearTradeReceiveLimitError(){{
    const error = document.getElementById('tradeReceiveLimitError');
    if(!error) return;

    error.textContent = '';
    error.style.display = 'none';
}}

function syncTradeSlots(){{
    document.querySelectorAll('.trade-slot').forEach(function(slot){{
        const mode = slot.dataset.mode;
        const code = slot.dataset.code;
        const count = tradeSelections[mode][code] || 0;
        slot.dataset.pendingCount = count > 0 ? count : '';
        slot.dataset.tradeCount = count > 0 ? count : '';
        slot.classList.toggle('smart-selected', count > 0);
    }});

    const getCount = document.getElementById('tradeGetCount');
    const giveCount = document.getElementById('tradeGiveCount');
    if(getCount) getCount.textContent = tradeTotal('get');
    if(giveCount) giveCount.textContent = tradeTotal('give');
    updateTradeSelectionBar();
}}

function setTradeCount(mode, code, amount){{
    const slot = Array.from(document.querySelectorAll('.trade-slot')).find(function(item){{
        return item.dataset.mode === mode && item.dataset.code === code;
    }});
    if(!slot) return;

    const max = parseInt(slot.dataset.max, 10) || 1;
    let nextAmount = Math.max(Math.min(parseInt(amount, 10) || 0, max), 0);

    if(mode === 'give'){{
        nextAmount = nextAmount > 0 ? 1 : 0;
    }}

    if(mode === 'get'){{
        const currentAmount = tradeSelections[mode][code] || 0;
        const receiveTotalWithoutCode = tradeTotal('get') - currentAmount;
        const remainingReceiveCapacity = Math.max(maxReceiveSelection - receiveTotalWithoutCode, 0);

        if(nextAmount > remainingReceiveCapacity){{
            nextAmount = remainingReceiveCapacity;
            showTradeReceiveLimitError();
        }}else{{
            clearTradeReceiveLimitError();
        }}
    }}

    if(nextAmount === 0){{
        delete tradeSelections[mode][code];
    }}else{{
        tradeSelections[mode][code] = nextAmount;
    }}

    syncTradeSlots();
    renderTradeReview();
}}

function incrementTradeCode(mode, code){{
    if(mode === 'get' && tradeTotal('get') >= maxReceiveSelection){{
        showTradeReceiveLimitError();
        return;
    }}

    if(mode === 'give' && (tradeSelections.give[code] || 0) >= 1){{
        return;
    }}

    const current = tradeSelections[mode][code] || 0;
    setTradeCount(mode, code, current + 1);
}}

function addVisibleTradeSlots(mode){{
    const panel = document.querySelector('.trade-selection-step[data-mode="' + mode + '"]');
    if(!panel) return;

    if(mode === 'get' && maxReceiveSelection <= 0){{
        showTradeReceiveLimitError();
        return;
    }}

    const visibleSlots = Array.from(panel.querySelectorAll('.trade-slot[data-mode="' + mode + '"]'))
        .filter(tradeSlotIsVisible);

    let addedAny = false;

    visibleSlots.forEach(function(slot){{
        const code = slot.dataset.code;
        if(!code) return;

        if(mode === 'get'){{
            if(tradeSelections.get[code]) return;
            if(tradeTotal('get') >= maxReceiveSelection) return;
            setTradeCount('get', code, 1);
            addedAny = true;
            return;
        }}

        if(mode === 'give'){{
            if((tradeSelections.give[code] || 0) === 1) return;
            setTradeCount('give', code, 1);
            addedAny = true;
        }}
    }});

    if(mode === 'get' && !addedAny && tradeTotal('get') >= maxReceiveSelection){{
        showTradeReceiveLimitError();
    }}
}}

function decrementTradeCode(mode, code){{
    const current = tradeSelections[mode][code] || 0;
    setTradeCount(mode, code, current - 1);
}}

function renderTradeReviewList(mode, targetId){{
    const list = document.getElementById(targetId);
    if(!list) return;

    const codes = Object.keys(tradeSelections[mode]);
    list.innerHTML = '';

    if(codes.length === 0){{
        list.innerHTML = '<p class="pending-review-empty">Keine Sticker ausgewählt.</p>';
        return;
    }}

    codes.sort().forEach(function(code){{
        const row = document.createElement('div');
        row.className = 'pending-review-row';

        const codeText = document.createElement('strong');
        codeText.textContent = tradeDisplayCode(code);

        const controls = document.createElement('div');
        controls.className = 'pending-review-controls';

        const minusButton = document.createElement('button');
        minusButton.type = 'button';
        minusButton.textContent = '-';
        minusButton.addEventListener('click', function(){{ decrementTradeCode(mode, code); }});

        const amount = document.createElement('input');
        amount.type = 'number';
        amount.min = '0';
        amount.step = '1';
        if(mode === 'give') amount.max = '1';
        amount.value = tradeSelections[mode][code] || 0;
        amount.addEventListener('change', function(){{ setTradeCount(mode, code, amount.value); }});

        const plusButton = document.createElement('button');
        plusButton.type = 'button';
        plusButton.textContent = '+';
        if(mode === 'give') plusButton.disabled = true;
        plusButton.addEventListener('click', function(){{ incrementTradeCode(mode, code); }});

        controls.appendChild(minusButton);
        controls.appendChild(amount);
        controls.appendChild(plusButton);

        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.className = 'pending-review-remove';
        removeButton.textContent = '×';
        removeButton.addEventListener('click', function(){{ setTradeCount(mode, code, 0); }});

        row.appendChild(codeText);
        row.appendChild(controls);
        row.appendChild(removeButton);
        list.appendChild(row);
    }});
}}

function expandTradeCodes(mode){{
    const expanded = [];
    Object.keys(tradeSelections[mode]).forEach(function(code){{
        const count = tradeSelections[mode][code] || 0;
        for(let i = 0; i < count; i += 1){{
            expanded.push(code);
        }}
    }});
    return expanded;
}}

function renderTradeReview(){{
    renderTradeReviewList('get', 'tradeGetReview');
    renderTradeReviewList('give', 'tradeGiveReview');

    const hidden = document.getElementById('tradeHiddenInputs');
    if(hidden){{
        hidden.innerHTML = '';
        expandTradeCodes('get').forEach(function(code){{
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'get_codes';
            input.value = code;
            hidden.appendChild(input);
        }});
        expandTradeCodes('give').forEach(function(code){{
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'give_codes';
            input.value = code;
            hidden.appendChild(input);
        }});
    }}

    const error = document.getElementById('tradeRuleError');
    const submit = document.getElementById('tradeSubmitButton');
    const getTotal = tradeTotal('get');
    const giveTotal = tradeTotal('give');
    const invalid = getTotal === 0 || giveTotal === 0 || giveTotal < getTotal;

    if(error){{
        error.style.display = giveTotal < getTotal ? 'block' : 'none';
        error.textContent = 'Du musst mindestens so viele Sticker anbieten, wie du suchst.';
    }}
    if(submit) submit.disabled = invalid;
}}

function showTradeStep(step){{
    document.querySelectorAll('.trade-step').forEach(function(panel){{
        panel.classList.toggle('active', panel.dataset.step === step);
    }});
    document.querySelectorAll('.trade-step-pill').forEach(function(pill){{
        pill.classList.toggle('active', pill.dataset.stepLabel === step);
    }});
    if(step === 'get' || step === 'give'){{
        activeTradeMode = step;
    }}
    document.body.classList.toggle('pending-active', step === 'get' || step === 'give');
    document.body.classList.toggle('trade-pending-active', step === 'get' || step === 'give');
    updateTradeSelectionBar();
    if(step === 'final'){{
        renderTradeReview();
    }}
}}

function updateTradeSelectionBar(){{
    const bar = document.getElementById('tradeSelectionBar');
    const count = document.getElementById('tradeActiveCount');
    const label = document.getElementById('tradeActiveLabel');
    const primary = document.getElementById('tradeReviewCurrentButton');
    const panel = activeTradePanel();
    const isSelectionStep = panel && panel.classList.contains('active');

    if(!bar || !count || !label || !primary) return;

    const total = tradeTotal(activeTradeMode);
    count.textContent = total;
    label.textContent = 'Sticker ausgewählt';
    primary.textContent = activeTradeMode === 'get' ? 'Weiter zu deinen Doppelten' : 'Tauschanfrage prüfen';
    primary.disabled = total === 0;
    bar.style.display = isSelectionStep ? 'flex' : 'none';
}}

document.querySelectorAll('[data-next-step]').forEach(function(button){{
    button.addEventListener('click', function(){{
        showTradeStep(button.dataset.nextStep);
    }});
}});

document.querySelectorAll('[data-trade-search]').forEach(function(input){{
    input.addEventListener('input', function(){{
        updateTradeSearch(input.closest('.trade-step'), input.value);
    }});

    input.addEventListener('keydown', function(event){{
        if(event.key !== 'Enter') return;
        event.preventDefault();

        const mode = input.dataset.tradeSearch;
        const slot = tradeFindSlotByCode(mode, input.value);
        if(!slot) return;

        if(mode === 'get' && tradeTotal('get') >= maxReceiveSelection){{
            showTradeReceiveLimitError();
            return;
        }}

        if(mode === 'give' && (tradeSelections.give[slot.dataset.code] || 0) >= 1){{
            input.value = '';
            updateTradeSearch(input.closest('.trade-step'), '');
            input.focus();
            return;
        }}

        incrementTradeCode(mode, slot.dataset.code);
        input.value = '';
        updateTradeSearch(input.closest('.trade-step'), '');
        input.focus();
    }});
}});

document.querySelectorAll('[data-add-visible-trade]').forEach(function(button){{
    button.addEventListener('click', function(){{
        addVisibleTradeSlots(button.dataset.addVisibleTrade);
    }});
}});

document.getElementById('tradeReviewCurrentButton').addEventListener('click', function(){{
    if(tradeTotal(activeTradeMode) === 0) return;
    showTradeStep(activeTradeMode === 'get' ? 'give' : 'final');
}});

document.addEventListener('click', function(event){{
    const slot = event.target.closest('.trade-slot');
    if(!slot) return;

    if(slot.dataset.mode === 'get' && tradeTotal('get') >= maxReceiveSelection){{
        showTradeReceiveLimitError();
        return;
    }}

    if(slot.dataset.mode === 'give' && (tradeSelections.give[slot.dataset.code] || 0) >= 1){{
        return;
    }}

    incrementTradeCode(slot.dataset.mode, slot.dataset.code);
}});

document.getElementById('tradeRequestForm').addEventListener('submit', function(event){{
    renderTradeReview();
    if(tradeTotal('give') < tradeTotal('get') || tradeTotal('get') === 0 || tradeTotal('give') === 0){{
        event.preventDefault();
    }}
}});

syncTradeSlots();
showTradeStep('get');
document.querySelectorAll('.trade-step').forEach(function(panel){{
    updateTradeVisibleSections(panel);
}});
</script>

    </main>
    {bottom_nav("tauschen")}
    </div></body></html>
    """

    con.close()
    return html


def smart_trade_calculation(connection, album_id, excluded_partner_id=None):
    cleanup_smartdeal_runtime(connection)
    user_id = current_user_id()
    privacy = album_privacy_service(connection)
    partner_ids = [
        partner_id
        for partner_id in privacy.trade_pool_user_ids(
            album_id, excluded_user_id=user_id
        )
        if (
            privacy.is_trade_pool_enabled(user_id, album_id)
            and partner_id != excluded_partner_id
            and CommunityService(connection).can_start_interaction(
                user_id, partner_id
            )
        )
    ]
    inventory = InventoryReadService(connection)
    return TopMatchOptimizationService(
        inventory,
        TradeCoverageService(inventory, privacy),
    ).optimize(user_id, album_id, all_codes(album_id), partner_ids)


def expanded_smart_positions(positions):
    return tuple(
        position.sticker_code
        for position in positions
        for _ in range(position.quantity)
    )


@app.route("/album/<album_id>/smart-trades")
def album_smart_trades(album_id):
    con = get_db()
    album = con.execute("SELECT * FROM albums WHERE id=?", (album_id,)).fetchone()
    membership = con.execute(
        "SELECT 1 FROM user_albums WHERE user_id=? AND album_id=?",
        (current_user_id(), album_id),
    ).fetchone()
    if not album or not membership or not reservation_schema_available(con):
        con.close()
        return redirect(
            f"/album/{album_id}/trades?message="
            f"{quote('Smart Trades sind für dieses Album nicht verfügbar.')}"
        )

    raw_excluded = request.args.get("exclude_partner_id", "").strip()
    try:
        excluded_partner_id = int(raw_excluded) if raw_excluded else None
    except ValueError:
        excluded_partner_id = None
    if excluded_partner_id == current_user_id():
        excluded_partner_id = None

    result = smart_trade_calculation(con, album_id, excluded_partner_id)
    usernames = {
        row["id"]: row["username"]
        for row in con.execute("SELECT id, username FROM users").fetchall()
    }
    open_count = SmartTradeRequestService(con).open_count(current_user_id())
    history = con.execute(
        """
        SELECT request.*, users.username AS partner_name
        FROM trade_requests request
        JOIN users ON users.id=request.to_user_id
        WHERE request.from_user_id=? AND request.from_confirmed=?
          AND request.status IN ('expired', 'obsolete', 'declined')
        ORDER BY request.created_at DESC, request.id DESC
        LIMIT 10
        """,
        (current_user_id(), SMART_REQUEST_MARKER),
    ).fetchall()

    cards = []
    for package in result.packages:
        partner_name = usernames.get(
            package.partner_user_id, f"Sammler {package.partner_user_id}"
        )
        give_codes = expanded_smart_positions(package.give_positions)
        receive_codes = expanded_smart_positions(package.receive_positions)
        excluded_field = (
            f'<input type="hidden" name="exclude_partner_id" '
            f'value="{excluded_partner_id}">'
            if excluded_partner_id is not None else ""
        )
        cards.append(f"""
        <article class="trade-person-card r2-smart-match-card" data-smart-package="read-only">
            <div class="r2-smart-match-head">
                <a class="trade-person-identity" href="/profil/{quote(partner_name, safe='')}"
                   aria-label="Profil von {escape(partner_name)} öffnen">
                    <span class="trade-person-avatar" aria-hidden="true">{escape((partner_name[:1] or 'S').upper())}</span>
                    <span><strong>{escape(partner_name)}</strong><small>Passendes SmartMatch</small></span>
                </a>
                {smart_trade_badge_html(True)}
            </div>
            <div class="trade-request-quantities r2-smart-match-quantities">
                <p><span>Du erhältst</span><strong>{len(receive_codes)} Sticker</strong></p>
                <p><span>Du gibst</span><strong>{len(give_codes)} Sticker</strong></p>
            </div>
            <div class="r2-smart-match-codes">
                <p><strong>Du erhältst:</strong> {escape(trade_code_summary(receive_codes))}</p>
                <p><strong>Du gibst ab:</strong> {escape(trade_code_summary(give_codes))}</p>
                <p>Dieses optimierte Paket ist nicht editierbar.</p>
            </div>
            <div class="r2-smart-match-actions">
                <form method="POST" action="/album/{album_id}/smart-trades/{package.partner_user_id}/request">
                    <input type="hidden" name="result_id" value="{escape(result.result_id)}">
                    {excluded_field}
                    <button class="trade-concept-primary-action" type="submit">SmartMatch anfragen</button>
                </form>
                <a class="trade-concept-secondary-action" href="/album/{album_id}/smart-trades?exclude_partner_id={package.partner_user_id}">
                    Anderen Vorschlag zeigen
                </a>
            </div>
        </article>
        """)

    history_html = ""
    if history:
        history_items = "".join(
            f"<li>{escape(row['partner_name'])}: "
            f"{escape(trade_status_label(row))}</li>"
            for row in history
        )
        history_html = f"""
        <section class="card" aria-label="Smart-Anfragehistorie">
            <h2>Bisherige Smart-Anfragen</h2>
            <ul>{history_items}</ul>
        </section>
        """

    message = request.args.get("message", "")
    exclusion_hint = (
        "Ein Partner ist nur für diese Berechnung ausgeschlossen."
        if excluded_partner_id is not None else ""
    )
    html = f"""
    <html><head>{style()}</head><body class="s31-product-page s30-reference-page r2-trade-journey-page r2-smart-match-page"><div class="container">
    {app_header()}
    <main class="trade-concept-shell" aria-label="SmartMatch">
    <a class="r2-trade-back" href="/album/{album_id}/trades">← zurück zu Tauschpartner</a>
    {sammlr_feedback_html(message) if message else ''}
    <section class="trade-concept-intro r2-trade-intro">
        <p class="r2-trade-eyebrow">{escape(album['name'])}</p>
        <h1>SmartMatch</h1>
        <p>Sammlr stellt ausführbare Pakete aus euren freien Stickern zusammen. Du prüfst nur noch den Vorschlag.</p>
    </section>
    <div class="r2-smart-match-status" aria-label="SmartMatch-Status">
        <strong>{open_count} von 3</strong>
        <span>Smart-Anfragen global offen</span>
        {f'<small>{escape(exclusion_hint)}</small>' if exclusion_hint else ''}
    </div>
    <section class="trade-concept-content r2-smart-match-list" aria-label="SmartMatch-Vorschläge">
    {''.join(cards) if cards else '<div class="trade-requests-empty"><h2>Kein ausführbares SmartMatch</h2><p>Aktuell ist keine bilaterale Kombination verfügbar.</p></div>'}
    {history_html}
    </section>
    </main>
    {bottom_nav("tauschen")}
    </div></body></html>
    """
    con.close()
    return html


@app.route(
    "/album/<album_id>/smart-trades/<int:partner_user_id>/request",
    methods=["POST"],
)
def create_smart_trade_request(album_id, partner_user_id):
    con = get_db()
    if not reservation_schema_available(con):
        con.close()
        return redirect(
            f"/album/{album_id}/trades?message="
            f"{quote('Smart Trades benötigen die bestehende Reservierungsbasis.')}"
        )

    raw_excluded = request.form.get("exclude_partner_id", "").strip()
    try:
        excluded_partner_id = int(raw_excluded) if raw_excluded else None
    except ValueError:
        excluded_partner_id = None
    result = smart_trade_calculation(con, album_id, excluded_partner_id)
    expected_result_id = request.form.get("result_id", "").strip()
    package = next(
        (
            item for item in result.packages
            if item.partner_user_id == partner_user_id
        ),
        None,
    )
    recalculate_url = f"/album/{album_id}/smart-trades"
    if excluded_partner_id is not None:
        recalculate_url += f"?exclude_partner_id={excluded_partner_id}"
    if expected_result_id != result.result_id or package is None:
        con.close()
        separator = "&" if "?" in recalculate_url else "?"
        return redirect(
            f"{recalculate_url}{separator}message="
            f"{quote('Der Vorschlag hat sich geändert. Bitte neu berechnen.')}"
        )

    give_codes = expanded_smart_positions(package.give_positions)
    get_codes = expanded_smart_positions(package.receive_positions)
    def notify_partner(connection, _trade_request_id):
        if typed_notification_schema_available(connection):
            TypedNotificationService(connection).notify_request_created(
                _trade_request_id,
                current_user_id(),
                partner_user_id,
                smart=True,
            )

    result_state = SmartTradeRequestService(con).create(
        album_id,
        current_user_id(),
        partner_user_id,
        give_codes,
        get_codes,
        on_created=notify_partner,
    )
    if result_state.code == SmartTradeRequestCode.CREATED:
        trade_id = result_state.trade_request_id
        con.close()
        return redirect(f"/trades/{trade_id}?origin=album_trades")

    messages = {
        SmartTradeRequestCode.LIMIT_REACHED: (
            "Du hast bereits drei offene Smart-Anfragen."
        ),
        SmartTradeRequestCode.PACKAGE_CHANGED: (
            "Paket nicht mehr vollständig verfügbar. Bitte neu berechnen."
        ),
        SmartTradeRequestCode.OBSOLETE: (
            "Kein ausführbares Paket mehr vorhanden. Bitte neu berechnen."
        ),
        SmartTradeRequestCode.INVALID_REQUEST: "Ungültiges Smart-Paket.",
    }
    message = messages.get(result_state.code, "Smart-Anfrage nicht erstellt.")
    con.close()
    separator = "&" if "?" in recalculate_url else "?"
    return redirect(f"{recalculate_url}{separator}message={quote(message)}")


# --- Trade-Request routes ---

@app.route("/album/<album_id>/trade/<int:other_user_id>/request", methods=["POST"])
@app.route("/album/<album_id>/trades/<int:other_user_id>/request", methods=["POST"])
def create_trade_request(album_id, other_user_id):
    raw_give_codes = request.form.getlist("give_codes")
    raw_get_codes = request.form.getlist("get_codes")

    give_codes = [resolve_code(album_id, code) for code in raw_give_codes]
    get_codes = [resolve_code(album_id, code) for code in raw_get_codes]
    give_codes = [code for code in give_codes if code]
    get_codes = [code for code in get_codes if code]

    trade_url = f"/album/{album_id}/trade/{other_user_id}"

    con = get_db()
    if not CommunityService(con).can_start_interaction(
        current_user_id(), other_user_id
    ):
        con.close()
        return redirect(
            f"/album/{album_id}/trades?message="
            f"{quote('Mit diesem Nutzer ist derzeit keine Interaktion möglich.')}"
        )
    privacy = album_privacy_service(con)
    if not (
        privacy.is_trade_pool_enabled(current_user_id(), album_id)
        and privacy.is_trade_pool_enabled(other_user_id, album_id)
    ):
        con.close()
        abort(404)

    if not give_codes or not get_codes:
        con.close()
        return redirect(f"{trade_url}?message={quote('Bitte wähle auf beiden Seiten mindestens einen Sticker aus.')}")

    if len(give_codes) < len(get_codes):
        con.close()
        return redirect(f"{trade_url}?message={quote('Du musst mindestens so viele Sticker anbieten, wie du suchst.')}")

    partner = con.execute("SELECT id FROM users WHERE id=?", (other_user_id,)).fetchone()
    if not partner:
        con.close()
        return redirect(f"/album/{album_id}/trades")

    mein_bestand = user_album_inventory(con, current_user_id(), album_id)
    anderer_bestand = user_album_inventory(con, other_user_id, album_id)
    get_allowed, give_allowed = availability_trade_candidates(
        album_id, mein_bestand, anderer_bestand
    )

    def count_codes(codes):
        counts = {}
        for code in codes:
            counts[code] = counts.get(code, 0) + 1
        return counts

    get_requested = count_codes(get_codes)
    give_requested = count_codes(give_codes)

    for code, amount in get_requested.items():
        if amount > get_allowed.get(code, 0):
            con.close()
            return redirect(f"{trade_url}?message={quote('Ein ausgewählter Sticker ist nicht mehr verfügbar.')}")

    for code, amount in give_requested.items():
        if amount > give_allowed.get(code, 0):
            con.close()
            return redirect(f"{trade_url}?message={quote('Ein ausgewählter Sticker ist nicht mehr verfügbar.')}")

    cursor = con.execute(
        """
        INSERT INTO trade_requests (album_id, from_user_id, to_user_id, give_codes, get_codes, status)
        VALUES (?, ?, ?, ?, ?, 'open')
        """,
        (
            album_id,
            current_user_id(),
            other_user_id,
            json.dumps(give_codes),
            json.dumps(get_codes)
        )
    )

    UserActivityService(con).touch(current_user_id())

    if typed_notification_schema_available(con):
        TypedNotificationService(con).notify_request_created(
            cursor.lastrowid,
            current_user_id(),
            other_user_id,
            smart=False,
        )
    con.commit()
    con.close()

    return redirect(f"/trades?message=Tauschanfrage%20gesendet")


@app.route("/trade/<int:trade_id>/accept", methods=["POST"])
def accept_trade_request(trade_id):
    con = get_db()
    boundary = smartdeal_request_boundary(con, trade_id, 'accept')
    if boundary is not None:
        return boundary
    smart_trade = con.execute(
        "SELECT * FROM trade_requests WHERE id=?",
        (trade_id,),
    ).fetchone()
    is_smart = is_smart_trade_request(smart_trade)
    if is_smart:
        smart_state = SmartTradeRequestService(con).inspect(
            trade_id,
            current_user_id(),
            recheck=True,
        )
        if smart_state.code != SmartTradeRequestCode.READY:
            messages = {
                SmartTradeRequestCode.PACKAGE_CHANGED: (
                    "Paket nicht mehr vollständig verfügbar"
                ),
                SmartTradeRequestCode.OBSOLETE: "Smart-Paket nicht mehr ausführbar",
                SmartTradeRequestCode.EXPIRED: "Smart-Anfrage abgelaufen",
                SmartTradeRequestCode.UNAUTHORIZED: "Tauschanfrage nicht gefunden",
            }
            message = messages.get(
                smart_state.code, "Smart-Anfrage kann nicht angenommen werden"
            )
            con.close()
            return redirect(f"/trades/{trade_id}?message={quote(message)}")

    if reservation_schema_available(con):
        def record_smart_acceptance(connection, trade):
            if is_smart:
                lifecycle = connection.execute(
                    "SELECT id FROM trades WHERE legacy_trade_request_id=?",
                    (trade["id"],),
                ).fetchone()
                connection.execute(
                    """
                    INSERT INTO trade_events
                        (trade_id, event_type, actor_user_id, payload_json)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        lifecycle["id"],
                        SMART_ACCEPTED_EVENT,
                        current_user_id(),
                        json.dumps({"source": "s22_smart_request"}),
                    ),
                )

        result = TradeReservationService(con).accept(
            trade_id,
            current_user_id(),
            on_accepted=record_smart_acceptance,
        )
        con.close()
        messages = {
            TradeAcceptanceCode.ACCEPTED: "Tauschanfrage angenommen",
            TradeAcceptanceCode.ALREADY_ACCEPTED: "Tauschanfrage bereits angenommen",
            TradeAcceptanceCode.INSUFFICIENT_AVAILABLE: "Nicht mehr genügend Sticker verfügbar",
            TradeAcceptanceCode.INVALID_TRADE_STATE: "Tauschanfrage nicht mehr offen",
            TradeAcceptanceCode.UNAUTHORIZED: "Tauschanfrage nicht gefunden",
            TradeAcceptanceCode.TRANSACTION_ERROR: "Tauschanfrage konnte nicht angenommen werden",
        }
        fallback = f"/trades?message={quote(messages[result.code])}"
        return redirect(request.referrer or fallback)

    trade = con.execute(
        "SELECT * FROM trade_requests WHERE id=? AND to_user_id=? AND status='open'",
        (trade_id, current_user_id())
    ).fetchone()

    if trade:
        con.execute(
            "UPDATE trade_requests SET status='accepted', from_confirmed=0, to_confirmed=0 WHERE id=? AND to_user_id=? AND status='open'",
            (trade_id, current_user_id())
        )
        con.commit()

    con.close()
    return redirect(request.referrer or "/trades?message=Tauschanfrage%20angenommen")


@app.route("/trade/<int:trade_id>/ship", methods=["POST"])
def confirm_trade_shipping(trade_id):
    con = get_db()
    boundary = smartdeal_request_boundary(con, trade_id, 'ship')
    if boundary is not None:
        return boundary
    result = TradeShippingService(con).ship(
        trade_id, current_user_id()
    )
    con.close()
    messages = {
        TradeShippingCode.SHIPPED: "Eigener Versand bestätigt",
        TradeShippingCode.ALREADY_SHIPPED: "Eigener Versand bereits bestätigt",
        TradeShippingCode.INVALID_TRADE_STATE: "Trade nicht versandbereit",
        TradeShippingCode.UNAUTHORIZED: "Trade nicht gefunden",
        TradeShippingCode.MISSING_RESERVATIONS: "Reservierte Positionen fehlen",
        TradeShippingCode.TRANSACTION_ERROR: "Versand konnte nicht bestätigt werden",
    }
    fallback = f"/trades/{trade_id}?message={quote(messages[result.code])}"
    return redirect(request.referrer or fallback)


@app.route("/trade/<int:trade_id>/receive", methods=["POST"])
def confirm_trade_receipt(trade_id):
    con = get_db()
    boundary = smartdeal_request_boundary(con, trade_id, 'receive')
    if boundary is not None:
        return boundary
    trade = con.execute(
        """
        SELECT * FROM trade_requests
        WHERE id=? AND (from_user_id=? OR to_user_id=?)
        """,
        (trade_id, current_user_id(), current_user_id()),
    ).fetchone()

    before_current = []
    before_other = []
    other_user_id = None
    if trade is not None:
        other_user_id = (
            trade["to_user_id"]
            if trade["from_user_id"] == current_user_id()
            else trade["from_user_id"]
        )
        before_current = erreichte_trophaeen_for_user(
            trade["album_id"], current_user_id()
        )
        before_other = erreichte_trophaeen_for_user(
            trade["album_id"], other_user_id
        )

    result = TradeReceiptService(con).receive(
        trade_id,
        current_user_id(),
    )
    con.close()

    if result.received and result.completed and trade is not None:
        album_id = trade["album_id"]
        after_current = erreichte_trophaeen_for_user(
            album_id, current_user_id()
        )
        after_other = erreichte_trophaeen_for_user(album_id, other_user_id)
        current_new = record_trophy_unlocks(
            album_id,
            [title for title in after_current if title not in before_current],
            user_id=current_user_id(),
            silent_reached=before_current,
        )
        record_trophy_unlocks(
            album_id,
            [title for title in after_other if title not in before_other],
            user_id=other_user_id,
            silent_reached=before_other,
        )
        queue_trophy_popup(album_id, current_new)

    messages = {
        TradeReceiptCode.RECEIVED: (
            "Tausch abgeschlossen" if result.completed else "Empfang bestätigt"
        ),
        TradeReceiptCode.ALREADY_RECEIVED: "Empfang bereits bestätigt",
        TradeReceiptCode.NOT_SHIPPED: "Versand der Gegenseite noch offen",
        TradeReceiptCode.INVALID_TRADE_STATE: "Trade nicht empfangsbereit",
        TradeReceiptCode.UNAUTHORIZED: "Trade nicht gefunden",
        TradeReceiptCode.TRANSACTION_ERROR: "Empfang konnte nicht bestätigt werden",
    }
    fallback = f"/trades/{trade_id}?message={quote(messages[result.code])}"
    return redirect(request.referrer or fallback)


@app.route("/trades/<int:trade_id>/problem")
def trade_problem_form(trade_id):
    con = get_db()
    trade = con.execute(
        """
        SELECT r.*, t.id AS lifecycle_trade_id,
               t.requester_user_id, t.partner_user_id,
               s.requester_shipped, s.partner_shipped
        FROM trade_requests r
        JOIN trades t ON t.legacy_trade_request_id=r.id
        JOIN trade_shipping_status s ON s.trade_id=t.id
        WHERE r.id=? AND (r.from_user_id=? OR r.to_user_id=?)
        """,
        (trade_id, current_user_id(), current_user_id()),
    ).fetchone()
    if trade is None or not problem_schema_available(con):
        con.close()
        return redirect(f"/trades/{trade_id}?message=Problemweg%20nicht%20verfügbar")

    side = (
        "requester"
        if current_user_id() == trade["requester_user_id"]
        else "partner"
    )
    other_shipped = (
        trade["partner_shipped"] if side == "requester"
        else trade["requester_shipped"]
    )
    receipt_status = receipt_status_for_trade(con, trade_id)
    reports = problem_reports_for_trade(con, trade_id)
    own_report = next(
        (
            report for report in reports
            if report.receiver_user_id == current_user_id()
        ),
        None,
    )
    positions = con.execute(
        """
        SELECT id, album_id, sticker_code, quantity
        FROM trade_positions
        WHERE trade_id=? AND to_user_id=?
        ORDER BY id
        """,
        (trade["lifecycle_trade_id"], current_user_id()),
    ).fetchall()
    con.close()

    if (
        trade["status"] != "accepted"
        or not other_shipped
        or receipt_status is None
        or receipt_status.received_for(current_user_id())
        or own_report is not None
        or not positions
    ):
        return redirect(f"/trades/{trade_id}?message=Problemweg%20nicht%20verfügbar")

    position_fields = []
    for position in positions:
        position_fields.append(f"""
        <fieldset class="trade-completion-box">
            <legend><strong>{escape(display_code(position['sticker_code']))}</strong></legend>
            <p>Erwartet: {position['quantity']}</p>
            <label>Korrekt erhalten
                <input type="number" name="received_{position['id']}"
                       min="0" max="{position['quantity']}"
                       value="{position['quantity']}" required>
            </label>
            <label>Problem für die offene Menge
                <select name="problem_{position['id']}">
                    <option value="">Kein Problem</option>
                    <option value="missing">Fehlend / unvollständig</option>
                    <option value="wrong_sticker">Falscher Sticker</option>
                    <option value="damaged">Beschädigt</option>
                </select>
            </label>
        </fieldset>
        """)

    html = f"""
    <html><head>{style()}</head><body class="s31-product-page"><div class="page-shell">
    {app_header("Problem melden / Lieferung unvollständig", "Dokumentiere ausschließlich, was physisch korrekt angekommen ist.")}
    <main>
        <section class="card">
            <p><strong>Nur korrekt erhaltene erwartete Sticker werden eingebucht.</strong></p>
            <p>Falsche, beschädigte, fehlende oder verlorene Sticker bleiben ungebucht. Sammlr entscheidet keine Schuldfrage.</p>
            <form method="POST" action="/trade/{trade_id}/problem">
                {''.join(position_fields)}
                <label>
                    <input type="checkbox" name="shipment_lost" value="1">
                    Gesamte Sendung verloren – alle korrekt erhaltenen Mengen sind 0
                </label>
                <button class="btn green" type="submit">Physische Lieferung dokumentieren</button>
            </form>
            <a class="trade-detail-link" href="/trades/{trade_id}">Abbrechen und zurück zum Deal</a>
        </section>
    </main>
    {bottom_nav("tauschen")}
    </div></body></html>
    """
    return html


def _trade_problem_trophy_context(trade):
    if trade is None:
        return None
    actor = current_user_id()
    other_user_id = (
        trade["to_user_id"]
        if trade["from_user_id"] == actor
        else trade["from_user_id"]
    )
    return {
        "actor": actor,
        "other_user_id": other_user_id,
        "album_id": trade["album_id"],
        "before_actor": erreichte_trophaeen_for_user(trade["album_id"], actor),
        "before_other": erreichte_trophaeen_for_user(
            trade["album_id"], other_user_id
        ),
    }


def _apply_trade_problem_completion_trophies(context):
    if context is None:
        return
    album_id = context["album_id"]
    actor = context["actor"]
    other_user_id = context["other_user_id"]
    after_actor = erreichte_trophaeen_for_user(album_id, actor)
    after_other = erreichte_trophaeen_for_user(album_id, other_user_id)
    actor_new = record_trophy_unlocks(
        album_id,
        [title for title in after_actor if title not in context["before_actor"]],
        user_id=actor,
        silent_reached=context["before_actor"],
    )
    record_trophy_unlocks(
        album_id,
        [title for title in after_other if title not in context["before_other"]],
        user_id=other_user_id,
        silent_reached=context["before_other"],
    )
    queue_trophy_popup(album_id, actor_new)


@app.route("/trade/<int:trade_id>/problem", methods=["POST"])
def report_trade_problem(trade_id):
    con = get_db()
    boundary = smartdeal_request_boundary(con, trade_id, 'problem')
    if boundary is not None:
        return boundary
    trade = con.execute(
        """
        SELECT * FROM trade_requests
        WHERE id=? AND (from_user_id=? OR to_user_id=?)
        """,
        (trade_id, current_user_id(), current_user_id()),
    ).fetchone()
    context = _trade_problem_trophy_context(trade)
    positions = con.execute(
        """
        SELECT p.id, p.quantity
        FROM trade_positions p
        JOIN trades t ON t.id=p.trade_id
        WHERE t.legacy_trade_request_id=? AND p.to_user_id=?
        ORDER BY p.id
        """,
        (trade_id, current_user_id()),
    ).fetchall() if trade is not None else []
    shipment_lost = request.form.get("shipment_lost") == "1"
    inputs = []
    for position in positions:
        if shipment_lost:
            quantity = 0
            problem_type = TradeProblemType.SHIPMENT_LOST
        else:
            raw_quantity = request.form.get(f"received_{position['id']}", "")
            try:
                quantity = int(raw_quantity)
            except (TypeError, ValueError):
                quantity = raw_quantity
            problem_type = request.form.get(
                f"problem_{position['id']}", ""
            )
        inputs.append(
            PartialReceiptInputDTO(
                position["id"], quantity, problem_type
            )
        )

    result = TradeProblemService(con).report(
        trade_id,
        current_user_id(),
        inputs,
    )
    if result.changed:
        UserActivityService(con).touch(current_user_id())
        con.commit()
    con.close()
    if result.changed and result.completed:
        _apply_trade_problem_completion_trophies(context)

    messages = {
        TradeProblemCode.FULLY_RECEIVED: "Lieferung vollständig empfangen",
        TradeProblemCode.PARTIAL_RECEIPT_RECORDED: "Problem und erhaltene Mengen gespeichert",
        TradeProblemCode.ALREADY_IDENTICAL: "Identische Meldung bereits verarbeitet",
        TradeProblemCode.PROBLEM_RESOLVED: "Problem bereits aufgelöst",
        TradeProblemCode.CLOSED_WITH_PROBLEM: "Trade mit Problem beendet",
        TradeProblemCode.PROBLEM_RESOLVED_AFTER_CLOSE: "Problem nachträglich gelöst",
        TradeProblemCode.INVALID_QUANTITY: "Ungültige Empfangsmenge",
        TradeProblemCode.CONFLICTING_REPORT: "Widersprüchliche Meldung abgewiesen",
        TradeProblemCode.NOT_SHIPPED: "Versand der Gegenseite noch offen",
        TradeProblemCode.INVALID_TRADE_STATE: "Trade nicht dokumentierbar",
        TradeProblemCode.UNAUTHORIZED: "Trade nicht gefunden",
        TradeProblemCode.TRANSACTION_ERROR: "Problem konnte nicht gespeichert werden",
    }
    return redirect(
        f"/trades/{trade_id}?message={quote(messages[result.code])}"
    )


@app.route("/trade/<int:trade_id>/problem/close", methods=["POST"])
def close_trade_with_problem(trade_id):
    con = get_db()
    boundary = smartdeal_request_boundary(con, trade_id, 'close')
    if boundary is not None:
        return boundary
    result = TradeProblemService(con).close_with_problem(
        trade_id, current_user_id()
    )
    if result.changed:
        UserActivityService(con).touch(current_user_id())
        con.commit()
    con.close()
    messages = {
        TradeProblemCode.CLOSED_WITH_PROBLEM: "Trade mit Problem beendet",
        TradeProblemCode.ALREADY_IDENTICAL: "Trade bereits mit Problem beendet",
        TradeProblemCode.INVALID_TRADE_STATE: "Problemtrade nicht beendbar",
        TradeProblemCode.UNAUTHORIZED: "Trade nicht gefunden",
        TradeProblemCode.TRANSACTION_ERROR: "Problemtrade konnte nicht beendet werden",
    }
    return redirect(
        f"/trades/{trade_id}?message="
        f"{quote(messages.get(result.code, 'Problemtrade nicht beendbar'))}"
    )


@app.route("/trade/<int:trade_id>/problem/resolve", methods=["POST"])
def resolve_trade_problem(trade_id):
    if request.form.get("confirm_physical_arrival") != "1":
        return redirect(
            f"/trades/{trade_id}?message="
            f"{quote('Bitte die physische Nachlieferung ausdrücklich bestätigen')}"
        )
    con = get_db()
    boundary = smartdeal_request_boundary(con, trade_id, 'resolve')
    if boundary is not None:
        return boundary
    trade = con.execute(
        """
        SELECT * FROM trade_requests
        WHERE id=? AND (from_user_id=? OR to_user_id=?)
        """,
        (trade_id, current_user_id(), current_user_id()),
    ).fetchone()
    context = _trade_problem_trophy_context(trade)
    result = TradeProblemService(con).resolve(
        trade_id,
        current_user_id(),
    )
    if result.changed:
        UserActivityService(con).touch(current_user_id())
        con.commit()
    con.close()
    if result.changed and result.completed:
        _apply_trade_problem_completion_trophies(context)

    messages = {
        TradeProblemCode.PROBLEM_RESOLVED: (
            "Tausch abgeschlossen" if result.completed else "Problem aufgelöst"
        ),
        TradeProblemCode.PROBLEM_RESOLVED_AFTER_CLOSE: "Problem nachträglich gelöst",
        TradeProblemCode.CLOSED_WITH_PROBLEM: "Trade mit Problem beendet",
        TradeProblemCode.ALREADY_IDENTICAL: "Problem bereits aufgelöst",
        TradeProblemCode.NOT_SHIPPED: "Versand der Gegenseite noch offen",
        TradeProblemCode.INVALID_TRADE_STATE: "Problem nicht auflösbar",
        TradeProblemCode.UNAUTHORIZED: "Trade nicht gefunden",
        TradeProblemCode.TRANSACTION_ERROR: "Problemauflösung fehlgeschlagen",
        TradeProblemCode.FULLY_RECEIVED: "Lieferung vollständig empfangen",
        TradeProblemCode.PARTIAL_RECEIPT_RECORDED: "Problem gespeichert",
        TradeProblemCode.INVALID_QUANTITY: "Ungültige Empfangsmenge",
        TradeProblemCode.CONFLICTING_REPORT: "Widersprüchliche Meldung abgewiesen",
    }
    return redirect(
        f"/trades/{trade_id}?message={quote(messages[result.code])}"
    )


@app.route("/trade/<int:trade_id>/decline", methods=["POST"])
def decline_trade_request(trade_id):
    con = get_db()
    boundary = smartdeal_request_boundary(con, trade_id, 'decline')
    if boundary is not None:
        return boundary
    trade = con.execute(
        "SELECT * FROM trade_requests WHERE id=? AND to_user_id=? AND status='open'",
        (trade_id, current_user_id())
    ).fetchone()

    if trade and is_smart_trade_request(trade):
        smart_state = SmartTradeRequestService(con).inspect(
            trade_id,
            current_user_id(),
            recheck=False,
        )
        if smart_state.code == SmartTradeRequestCode.EXPIRED:
            con.close()
            return redirect(
                f"/trades/{trade_id}?message={quote('Smart-Anfrage abgelaufen')}"
            )

    if trade:
        updated = con.execute(
            "UPDATE trade_requests SET status='declined' WHERE id=? AND to_user_id=? AND status='open'",
            (trade_id, current_user_id())
        )
        if updated.rowcount == 1 and typed_notification_schema_available(con):
            TypedNotificationService(con).notify_request_declined(
                trade_id, current_user_id()
            )
        UserActivityService(con).touch(current_user_id())
        con.commit()

    con.close()
    return redirect(request.referrer or "/trades?message=Tauschanfrage%20abgelehnt")


@app.route("/trades")
@serialized_sqlite_projection
def trades_overview():
    message = request.args.get("message", "")
    con = get_db()
    cleanup_smartdeal_runtime(con)
    inventory = InventoryReadService(con)
    privacy = album_privacy_service(con)
    user_id = current_user_id()
    profile_privacy = ProfilePrivacyService(con)
    successful_trade_counts = {}

    def visible_successful_trade_count(partner_id):
        partner_id = int(partner_id)
        if partner_id in successful_trade_counts:
            return successful_trade_counts[partner_id]
        visible = (
            profile_privacy.can_view_collector_world(user_id, partner_id)
            if profile_privacy.schema_available else True
        )
        count = (
            SuccessfulTradeProjectionService(con).count_for_user(partner_id)
            if visible else None
        )
        successful_trade_counts[partner_id] = count
        return count

    albums = con.execute(
        "SELECT * FROM albums ORDER BY name COLLATE NOCASE"
    ).fetchall()
    album_ids = [album["id"] for album in albums]
    catalogs = {album_id: all_codes(album_id) for album_id in album_ids}
    subject_summaries = inventory.collection_summaries(
        user_id,
        catalogs,
        {album_id: len(catalogs[album_id]) for album_id in album_ids},
    )
    pool_users_by_album = privacy.trade_pool_user_ids_by_album(album_ids)
    active_partners_by_album = {album_id: set() for album_id in album_ids}
    for row in con.execute(
        """
        SELECT album_id,
               CASE WHEN from_user_id=? THEN to_user_id ELSE from_user_id END AS partner_id
        FROM trade_requests
        WHERE status IN ('open', 'accepted')
          AND (from_user_id=? OR to_user_id=?)
        """,
        (user_id, user_id, user_id),
    ).fetchall():
        active_partners_by_album.setdefault(row["album_id"], set()).add(
            int(row["partner_id"])
        )
    other_users_by_album = {album_id: [] for album_id in album_ids}
    if album_ids:
        placeholders = ", ".join("?" for _ in album_ids)
        for row in con.execute(
            f"""
            SELECT user_albums.album_id, users.id, users.username
            FROM users
            JOIN user_albums ON user_albums.user_id=users.id
            WHERE users.id != ? AND user_albums.album_id IN ({placeholders})
            ORDER BY user_albums.album_id, users.username COLLATE NOCASE, users.id
            """,
            (user_id, *album_ids),
        ).fetchall():
            other_users_by_album[row["album_id"]].append(row)

    album_sections = []
    for album in albums:
        album_id = album["id"]
        alle_codes = catalogs[album_id]
        pool_user_ids = set(pool_users_by_album[album_id])
        active_trade_partner_ids = active_partners_by_album[album_id]
        andere_user = other_users_by_album[album_id]
        andere_user = [
            other_user for other_user in andere_user
            if user_id in pool_user_ids and other_user["id"] in pool_user_ids
        ]

        availability_projection = inventory.album_market_projection(
            user_id,
            [other_user["id"] for other_user in andere_user],
            album_id,
            alle_codes,
            subject_state=subject_summaries[album_id].matching_state,
        )

        passende_sammler = []
        for other_user in andere_user:
            if other_user["id"] in active_trade_partner_ids:
                continue

            du_suchst_count = len(
                availability_projection.get_codes_by_user[other_user["id"]]
            )
            du_bietest_count = len(
                availability_projection.give_codes_by_user[other_user["id"]]
            )

            if du_suchst_count == 0:
                continue

            passende_sammler.append({
                "id": other_user["id"],
                "username": other_user["username"],
                "du_suchst": du_suchst_count,
                "du_bietest": du_bietest_count,
                "successful_trade_count": visible_successful_trade_count(
                    other_user["id"]
                ),
            })

        passende_sammler.sort(key=lambda item: (-item["du_suchst"], item["username"].lower()))
        album_sections.append({
            "album": album,
            "sammler": passende_sammler,
        })

    rows = con.execute(
        """
        SELECT trade_requests.*,
               sender.username AS sender_name,
               receiver.username AS receiver_name,
               albums.name AS album_name
        FROM trade_requests
        JOIN users sender ON sender.id = trade_requests.from_user_id
        JOIN users receiver ON receiver.id = trade_requests.to_user_id
        JOIN albums ON albums.id = trade_requests.album_id
        WHERE (trade_requests.from_user_id=? OR trade_requests.to_user_id=?)
        AND trade_requests.status IN ('open', 'accepted')
        ORDER BY trade_requests.created_at DESC
        """,
        (user_id, user_id)
    ).fetchall()

    accepted_rows = [trade for trade in rows if trade["status"] == "accepted"]
    incoming_rows = [trade for trade in rows if trade["status"] == "open" and trade["to_user_id"] == user_id]
    outgoing_rows = [trade for trade in rows if trade["status"] == "open" and trade["from_user_id"] == user_id]
    tab = request.args.get("tab", "partners").strip()
    if tab not in ("partners", "agreements", "requests"):
        tab = "partners"
    request_count = len(incoming_rows) + len(outgoing_rows)
    request_badge = f"<span>{request_count}</span>" if request_count else ""
    agreement_badge = f"<span>{len(accepted_rows)}</span>" if accepted_rows else ""
    tab_subtitles = {
        "partners": "Finde Menschen, mit denen du deine Sammlung weiterbringen kannst.",
        "agreements": "Behalte im Blick, was gerade zwischen dir und anderen Sammlern läuft.",
        "requests": "Hier siehst du, wer mit dir tauschen möchte.",
    }

    html = f"""
    <html><head>{style()}</head><body class="s31-product-page s30-reference-page s30-trade-page"><div class="container">
    {app_header()}
    {consume_trophy_popup_html()}
    {sammlr_feedback_html(message) if message else ''}

    <main class="trade-concept-shell" aria-label="Tauschen">
    <section class="trade-concept-intro">
        <h1>Tauschen</h1>
        <p>{tab_subtitles[tab]}</p>
    </section>

    <nav class="trade-concept-tabs" aria-label="Tauschen-Bereiche">
        <a class="{'is-active' if tab == 'partners' else ''}" href="/trades?tab=partners"
           {'aria-current="page"' if tab == 'partners' else ''}>Tauschpartner</a>
        <a class="{'is-active' if tab == 'agreements' else ''}" href="/trades?tab=agreements"
           {'aria-current="page"' if tab == 'agreements' else ''}>
            Trades {agreement_badge}
        </a>
        <a class="{'is-active' if tab == 'requests' else ''}" href="/trades?tab=requests"
           {'aria-current="page"' if tab == 'requests' else ''}>
            Anfragen {request_badge}
        </a>
    </nav>
    """

    if tab == "partners":
        matching_sections = [section for section in album_sections if section["sammler"]]
        empty_album_count = len(album_sections) - len(matching_sections)
        html += '<section class="trade-concept-content" aria-label="Tauschpartner">'
        for section in matching_sections:
            album = section["album"]
            sammler = section["sammler"]
            sammler_count = len(sammler)
            sammler_label = "1 Tauschpartner" if sammler_count == 1 else f"{sammler_count} Tauschpartner"
            visible_sammler = sammler[:3]
            hidden_count = max(sammler_count - 3, 0)

            html += f"""
            <section class="trade-current-group">
                <header class="trade-group-heading">
                    <div>
                        <h2>{escape(album['name'])}</h2>
                        <p>{sammler_label}</p>
                    </div>
                </header>
                <div class="trade-current-card-list">
            """
            for sammler_item in visible_sammler:
                username = escape(sammler_item["username"])
                username_path = quote(sammler_item["username"], safe="")
                trade_count = sammler_item["successful_trade_count"]
                trade_meta = (
                    "Sammlerprofil"
                    if trade_count is None else
                    ("1 erfolgreicher Trade" if trade_count == 1 else
                     f"{trade_count} erfolgreiche Trades")
                )
                html += f"""
                <article class="trade-person-card trade-partner-concept-card">
                    <a class="trade-person-identity" href="/profil/{username_path}"
                       aria-label="Profil von {username} öffnen">
                        <span class="trade-person-avatar" aria-hidden="true">{escape((sammler_item['username'][:1] or 'S').upper())}</span>
                        <span><strong>{username}</strong><small>{trade_meta}</small></span>
                    </a>
                    <div class="trade-directed-match" aria-label="Gerichtete Tauschmöglichkeit">
                        <p><strong>{username} hat <em>{sammler_item['du_suchst']} Sticker</em>, die dir fehlen.</strong></p>
                        <p><strong>Du hast <em>{sammler_item['du_bietest']} Sticker</em>, die {username} sucht.</strong></p>
                    </div>
                    <a class="trade-concept-primary-action"
                       href="/album/{quote(album['id'], safe='')}/trade/{sammler_item['id']}">Tausch starten</a>
                </article>
                """
            html += "</div>"

            if hidden_count > 0:
                html += f"""
                <a class="trade-current-more" href="/album/{quote(album['id'], safe='')}/trades">Mehr anzeigen</a>
                """

            html += "</section>"
        if not matching_sections:
            html += """
            <section class="trade-requests-empty" aria-labelledby="partners-empty-heading">
                <h2 id="partners-empty-heading">Aktuell keine passenden Tauschpartner</h2>
                <p>Sobald jemand passende Sticker anbietet, erscheint die Person hier.</p>
            </section>
            """
        elif empty_album_count:
            album_word = "Album" if empty_album_count == 1 else "Alben"
            html += (
                f'<p class="trade-compact-note">Für {empty_album_count} weitere {album_word} '
                'gibt es aktuell keine passenden Tauschpartner.</p>'
            )
        html += "</section>"

    def render_trade_board(segment_rows, mode):
        if not segment_rows:
            if mode == "agreements":
                title = "Keine laufenden Trades"
                copy = "Sobald ein Tausch angenommen wurde, erscheint er hier."
            else:
                title = "Keine offenen Anfragen"
                copy = "Sobald dir jemand einen Tausch vorschlägt, erscheint er hier."
            return f"""
            <section class="trade-requests-empty" aria-labelledby="trade-empty-heading">
                <h2 id="trade-empty-heading">{title}</h2>
                <p>{copy}</p>
            </section>
            """

        grouped = {}
        for trade in segment_rows:
            grouped.setdefault(trade["album_id"], []).append(trade)

        board_html = '<section class="trade-concept-content">'
        for album in albums:
            album_rows = grouped.get(album["id"], [])
            if not album_rows:
                continue

            row_count = len(album_rows)
            if mode == "agreements":
                group_label = "1 laufender Trade" if row_count == 1 else f"{row_count} laufende Trades"
                detail_tab = "agreements"
            else:
                group_label = "1 Anfrage" if row_count == 1 else f"{row_count} Anfragen"
                detail_tab = "requests"

            board_html += f"""
            <section class="trade-current-group">
                <header class="trade-group-heading"><div>
                    <h2>{escape(album['name'])}</h2><p>{group_label}</p>
                </div></header>
                <div class="trade-current-card-list">
            """

            for trade in album_rows[:3]:
                give_codes = json.loads(trade["give_codes"])
                get_codes = json.loads(trade["get_codes"])
                is_receiver = trade["to_user_id"] == user_id
                if is_receiver:
                    partner_name = trade["sender_name"]
                    du_bekommst = give_codes
                    du_gibst = get_codes
                else:
                    partner_name = trade["receiver_name"]
                    du_bekommst = get_codes
                    du_gibst = give_codes

                status_label = trade_status_label(trade, is_receiver)
                if mode == "agreements":
                    shipping_status = shipping_status_for_trade(con, trade["id"])
                    receipt_status = receipt_status_for_trade(con, trade["id"])
                    problem_reports = problem_reports_for_trade(con, trade["id"])
                    timeline_context = trade_timeline_context(con, trade["id"])
                    if shipping_status is not None:
                        status_label = trade_shipping_status_label(
                            shipping_status, receipt_status, problem_reports
                        )
                    attention_html = trade_attention_html(
                        user_id, timeline_context, shipping_status,
                        receipt_status, problem_reports
                    )
                    if status_label == "Teilweise erhalten" and not attention_html:
                        attention_html = """
                        <div class="trade-attention-copy">
                            <strong>Empfang noch nicht beidseitig bestätigt</strong>
                            <p>Bei diesem Tausch ist der Empfang noch nicht auf beiden Seiten vollständig.</p>
                        </div>
                        """
                else:
                    attention_html = ""

                partner_display = escape(partner_name)
                partner_path = quote(partner_name, safe="")
                identity_subline = (
                    "Dein Tauschpartner" if mode == "agreements" else
                    ("Anfrage an dich" if is_receiver else "Deine Anfrage")
                )
                identity = f"""
                    <a class="trade-person-identity" href="/profil/{partner_path}"
                       aria-label="Profil von {partner_display} öffnen">
                        <span class="trade-person-avatar" aria-hidden="true">{escape((partner_name[:1] or 'S').upper())}</span>
                        <span><strong>{partner_display}</strong><small>{identity_subline}</small></span>
                    </a>
                """
                if mode == "agreements":
                    board_html += f"""
                    <article class="trade-person-card trade-running-concept-card">
                        <div class="trade-running-head">{identity}{trade_status_chip(status_label)}</div>
                        <p class="trade-quantity-line"><strong>{len(du_bekommst)} erhalten</strong><span aria-hidden="true">·</span><strong>{len(du_gibst)} gesendet</strong></p>
                        {attention_html}
                        <a class="trade-concept-secondary-action" href="/trades/{trade['id']}?origin=trades">Versandstatus ansehen</a>
                    </article>
                    """
                else:
                    is_smart_display = trade_has_smart_origin(con, trade)
                    waiting_html = (
                        "" if is_receiver else
                        '<span class="trade-request-waiting">Wartet auf Antwort</span>'
                    )
                    board_html += f"""
                    <article class="trade-person-card trade-request-concept-card">
                        <div class="trade-request-concept-head">
                            {identity}
                            {trade_status_chip(status_label)}
                        </div>
                        <div class="trade-request-type-row">
                            {trade_request_type_badge_html(is_smart_display)}
                        </div>
                        <div class="trade-request-quantities">
                            <p><span>Du erhältst</span><strong>{len(du_bekommst)} Sticker</strong></p>
                            <p><span>Du gibst</span><strong>{len(du_gibst)} Sticker</strong></p>
                        </div>
                        <div class="trade-request-code-grid">
                            <p><span>Du erhältst</span><strong>{escape(trade_code_summary(du_bekommst))}</strong></p>
                            <p><span>Du gibst</span><strong>{escape(trade_code_summary(du_gibst))}</strong></p>
                        </div>
                        <div class="trade-request-card-footer">
                            <a class="trade-concept-primary-action" href="/trades/{trade['id']}?origin=trades">Ansehen</a>
                            {waiting_html}
                        </div>
                    </article>
                    """

            board_html += "</div>"
            if row_count > 3:
                board_html += f"""
                <a class="trade-current-more" href="/album/{quote(album['id'], safe='')}/trades?tab={detail_tab}">Mehr anzeigen</a>
                """

            board_html += "</section>"

        board_html += "</section>"
        return board_html

    if tab == "agreements":
        html += render_trade_board(accepted_rows, "agreements")
    elif tab == "requests":
        html += render_trade_board(incoming_rows + outgoing_rows, "requests")
    html += "</main>"
    html += bottom_nav("tauschen")
    html += "</div></body></html>"
    con.close()
    return html


@app.route("/trades/<int:trade_id>/accept", methods=["POST"])
def accept_trade(trade_id):
    return redirect("/trades?message=Bitte%20die%20Tauschanfrage%20%C3%BCber%20den%20Button%20annehmen.")


@app.route("/trade/<int:trade_id>/confirm", methods=["POST"])
def confirm_trade_done(trade_id):
    con = get_db()
    boundary = smartdeal_request_boundary(con, trade_id, 'complete')
    if boundary is not None:
        return boundary
    trade = con.execute(
        """
        SELECT * FROM trade_requests
        WHERE id=? AND status='accepted' AND (from_user_id=? OR to_user_id=?)
        """,
        (trade_id, current_user_id(), current_user_id())
    ).fetchone()

    if not trade:
        con.close()
        return redirect(request.referrer or "/trades?message=Tauschanfrage%20nicht%20gefunden")

    if shipping_status_for_trade(con, trade_id) is not None:
        con.close()
        return redirect(
            request.referrer
            or "/trades?message=Der%20neue%20Versandflow%20wartet%20auf%20Empfang"
        )

    album_id = trade["album_id"]
    current_user = current_user_id()
    other_user_id = trade["to_user_id"] if trade["from_user_id"] == current_user else trade["from_user_id"]
    before_current = erreichte_trophaeen_for_user(album_id, current_user)
    before_other = erreichte_trophaeen_for_user(album_id, other_user_id)

    if trade["from_user_id"] == current_user:
        con.execute("UPDATE trade_requests SET from_confirmed=1 WHERE id=?", (trade_id,))
    else:
        con.execute("UPDATE trade_requests SET to_confirmed=1 WHERE id=?", (trade_id,))

    completed = complete_trade_if_ready(con, trade)
    if completed:
        con.commit()
        con.close()

        after_current = erreichte_trophaeen_for_user(album_id, current_user)
        after_other = erreichte_trophaeen_for_user(album_id, other_user_id)
        current_new = record_trophy_unlocks(
            album_id,
            [t for t in after_current if t not in before_current],
            user_id=current_user,
            silent_reached=before_current
        )
        record_trophy_unlocks(
            album_id,
            [t for t in after_other if t not in before_other],
            user_id=other_user_id,
            silent_reached=before_other
        )
        queue_trophy_popup(album_id, current_new)
        return redirect("/trades?message=Tausch%20abgeschlossen")

    con.commit()
    con.close()
    return redirect(request.referrer or "/trades?message=Tausch%20vormarkiert")


@app.route("/trade/<int:trade_id>/fail", methods=["POST"])
def fail_trade_done(trade_id):
    con = get_db()
    boundary = smartdeal_request_boundary(con, trade_id, 'fail')
    if boundary is not None:
        return boundary
    trade = con.execute(
        """
        SELECT * FROM trade_requests
        WHERE id=? AND status='accepted' AND (from_user_id=? OR to_user_id=?)
        """,
        (trade_id, current_user_id(), current_user_id())
    ).fetchone()

    if not trade:
        con.close()
        return redirect(request.referrer or "/trades?message=Tauschanfrage%20nicht%20gefunden")

    shipping_status = shipping_status_for_trade(con, trade_id)
    if shipping_status is not None and shipping_status.any_shipped:
        con.close()
        return redirect(
            request.referrer
            or "/trades?message=Versendeter%20Trade%20kann%20nicht%20pauschal%20beendet%20werden"
        )

    TradeReservationService(con).release(
        trade_id, "failed", "failed"
    )
    con.execute(
        """
        UPDATE trade_requests
        SET status='failed'
        WHERE id=? AND status='accepted' AND (from_user_id=? OR to_user_id=?)
        """,
        (trade_id, current_user_id(), current_user_id())
    )
    UserActivityService(con).touch(current_user_id())
    con.commit()
    con.close()
    return redirect("/trades?message=Tausch%20geplatzt")



@app.route("/trades/<int:trade_id>/decline", methods=["POST"])
def decline_trade(trade_id):
    return redirect("/trades?message=Bitte%20die%20Tauschanfrage%20%C3%BCber%20den%20Button%20ablehnen.")


# --- Confirm/cancel trade routes ---

@app.route("/trades/<int:trade_id>/confirm", methods=["POST"])
def confirm_trade(trade_id):
    return redirect("/trades?message=Bitte%20den%20Tausch%20%C3%BCber%20den%20Button%20best%C3%A4tigen.")


@app.route("/trades/<int:trade_id>/cancel", methods=["POST"])
def cancel_trade(trade_id):
    con = get_db()
    boundary = smartdeal_request_boundary(con, trade_id, 'withdraw')
    if boundary is not None:
        return boundary
    con.close()
    return redirect("/trades?message=Bitte%20den%20Tausch%20%C3%BCber%20den%20Button%20als%20geplatzt%20markieren.")


# --- Notification routes ---

@app.route("/notifications", methods=["GET", "POST"])
def notifications_page():
    body_classes = "s31-product-page s30-reference-page s30-notifications-page"
    try:
        requested_page = int(request.args.get("page", "1"))
    except (TypeError, ValueError):
        requested_page = 1
    requested_page = max(1, requested_page)
    message = request.args.get("message", "")
    message_html = sammlr_feedback_html(message)
    if request.method == "GET":
        open_query = f"page={requested_page}"
        if message:
            open_query += "&message=" + quote(message)
        return f"""
        <html><head>{style()}</head><body class="{body_classes}"><div class="container">
        {app_header("Benachrichtigungen", "Deine Hinweise – ungelesen und historisch.")}
        {message_html}
        <section class="notification-shell" aria-label="Benachrichtigungen öffnen">
            <div class="card notification-open-gate">
                <h2>Inbox wird geöffnet …</h2>
                <p>Bestätige den sicheren Abruf, falls die Seite nicht automatisch fortfährt.</p>
                <form id="notification-inbox-open" method="POST" action="/notifications?{open_query}">
                    <button class="notification-open" type="submit">Inbox öffnen</button>
                </form>
            </div>
        </section>
        {bottom_nav("notifications")}
        </div><script>
        document.getElementById("notification-inbox-open").requestSubmit();
        </script></body></html>
        """

    con = get_db()
    history = NotificationHistoryService(con).open_page(
        current_user_id(), requested_page
    )
    con.close()
    g.header_unread_count = history.unread_count

    if history.items:
        notification_cards = []
        for notification in history.items:
            state_label = "Gelesen" if notification.is_read else "Ungelesen"
            state_class = "read" if notification.is_read else "unread"
            if notification.target_available:
                target_html = (
                    f'<form method="POST" action="/notifications/{notification.id}/open">'
                    '<button class="notification-open" type="submit">Öffnen</button>'
                    '</form>'
                )
            elif notification.is_legacy:
                target_html = '<span class="notification-target-note">Historischer Hinweis</span>'
            else:
                target_html = '<span class="notification-target-note unavailable">Ziel nicht mehr verfügbar</span>'
            timestamp = format_sammlr_timestamp(notification.created_at)
            timestamp_html = ""
            if timestamp:
                date_label, time_label = timestamp.split("|", 1)
                timestamp_html = (
                    f'<time datetime="{escape(notification.created_at)}">'
                    f'{date_label} · {time_label}</time>'
                )
            notification_cards.append(f"""
            <article class="card notification-history-item {state_class}" data-notification-id="{notification.id}">
                <div class="notification-history-meta">
                    <span class="notification-read-state">{state_label}</span>
                    {timestamp_html}
                </div>
                <h2>{escape(notification.title)}</h2>
                <p>{escape(notification.body)}</p>
                <div class="notification-history-actions">
                    {target_html}
                </div>
            </article>
            """)
        notification_html = "".join(notification_cards)
    else:
        notification_html = """
        <div class="card notification-shell-empty">
            <h2>Noch keine Benachrichtigungen.</h2>
            <p>Neue und gelesene Hinweise erscheinen gemeinsam in dieser Historie.</p>
            <a class="notification-open" href="/">Zur Startseite</a>
        </div>
        """

    pagination_links = []
    if history.has_previous:
        pagination_links.append(
            f'<form method="POST" action="/notifications?page={history.page - 1}">'
            '<button class="notification-page-link" type="submit">← Neuer</button></form>'
        )
    pagination_links.append(
        f'<span>Seite {history.page} von {history.total_pages}</span>'
    )
    if history.has_next:
        pagination_links.append(
            f'<form method="POST" action="/notifications?page={history.page + 1}">'
            '<button class="notification-page-link" type="submit">Älter →</button></form>'
        )
    pagination_html = "".join(pagination_links)

    return f"""
    <html><head>{style()}</head><body class="{body_classes}"><div class="container">
    {app_header("Benachrichtigungen", "Deine Hinweise – ungelesen und historisch.")}
    {message_html}
    <section class="notification-shell" aria-label="Benachrichtigungshistorie">
        {notification_html}
    </section>
    <nav class="notification-pagination" aria-label="Seiten der Benachrichtigungshistorie">
        {pagination_html}
    </nav>
    {bottom_nav("notifications")}
    </div></body></html>
    """


@app.route("/notifications/<int:notification_id>/open", methods=["POST"])
def open_notification(notification_id):
    con = get_db()
    result = NotificationHistoryService(con).open_target(
        notification_id, current_user_id()
    )
    con.close()
    if result.code == NotificationOpenCode.OPENED:
        separator = "&" if "?" in result.target_path else "?"
        return redirect(f"{result.target_path}{separator}origin=notifications")
    return redirect(
        "/notifications?message=" + quote("Ziel nicht mehr verfügbar")
    )


@app.route("/notifications/<int:notification_id>/read", methods=["POST"])
def mark_notification_read(notification_id):
    con = get_db()
    NotificationHistoryService(con).mark_read(
        notification_id, current_user_id()
    )
    con.close()
    try:
        page = max(1, int(request.args.get("page", "1")))
    except (TypeError, ValueError):
        page = 1
    return redirect(f"/notifications?page={page}")

@app.route("/album/<album_id>/trophaeen")
def album_trophaeen(album_id):
    album, by_code, gesammelt, doppelte, prozent, total = lade_album(album_id)

    con = get_db()
    if canonical_trophy_schema_available(con):
        definitions = canonical_album_trophy_definitions(album_id, total)
        unlocks = CanonicalTrophyUnlockService(con).unlocks_for_user_album(
            current_user_id(), album_id
        )
        by_definition = {
            unlock.trophy_definition_id: unlock for unlock in unlocks
        }
        award_items = [
            trophy_item_from_definition(
                definition,
                by_code,
                gesammelt,
                total,
                unlocked_at=(
                    by_definition[definition["id"]].unlocked_at
                    if definition["id"] in by_definition else None
                ),
            )
            for definition in definitions
        ]
        for item in award_items:
            item["unlocked"] = item["id"] in by_definition
    else:
        award_items = []
    con.close()

    html = f"""
    <html><head>{style()}</head><body class="s31-product-page"><div class="container">
    {app_header("Albumauszeichnungen", f"Auszeichnungen: {len([item for item in award_items if item['unlocked']])}")}
    <div class="trophy-nav-links">
        <a class="sammlr-back-link" href="/album/{album_id}">Zurück zum Album</a>
        <a class="sammlr-back-link" href="/trophaeen">Zum Sammlr-Schrank</a>
    </div>
    """

    html += render_album_awards(award_items, album_id)

    html += bottom_nav("sammlung")
    html += "</div></body></html>"
    return html


@app.route("/trophaeen")
def globale_trophaeen():
    con = get_db()
    canonical_count = (
        len(CanonicalTrophyUnlockService(con).unlocks_for_user(current_user_id()))
        if canonical_trophy_schema_available(con) else 0
    )
    con.close()
    return f"""
    <html><head>{style()}</head><body class="s31-product-page"><div class="container">
    {app_header("Sammlr-Schrank", f"Auszeichnungen: {canonical_count}")}
    {render_album_portal_cards(album_portal_cards())}
    {bottom_nav("profil")}
    </div></body></html>
    """

@app.route("/statistik")
def statistik():
    user_id = current_user_id()
    con = get_db()
    projection = StatisticsProjectionService(con).for_user(user_id)
    con.close()
    career = projection.career
    trades = career.successful_trades
    trade_word = "Tausch" if trades.successful_trade_count == 1 else "Tausche"
    largest_html = "<p>Noch kein erfolgreicher Trade erfasst</p>"
    if trades.largest_trade is not None:
        largest_html = (
            f"<p>Größter Trade: {trades.largest_trade.received_quantity_total} "
            "erhalten · "
            f"{trades.largest_trade.given_quantity_total} abgegeben</p>"
        )
    current_album_html = "".join(
        f"""
        <a class="album-quick-card" href="/album/{escape(album.album_id)}/statistik">
            <strong>{escape(album.name)}</strong>
            <span>{album.collected} von {album.total} · {album.percent}%</span>
            <span>{album.missing} fehlen · {album.duplicate_quantity} doppelt</span>
        </a>
        """
        for album in projection.current_albums
    ) or '<p class="statistics-empty">Noch kein aktives Album.</p>'
    if career.history_available:
        history_html = f"""
        <p>{career.recorded_acquisition_quantity} Stickerzugänge seit Historienstart erfasst</p>
        <p>{career.recorded_album_start_count} Alben seit Historienstart begonnen</p>
        <p>{career.completed_album_count} Alben historisch abgeschlossen</p>
        <p>{career.valid_trophy_count or 0} gültige Trophäen</p>
        <p class="statistics-history-note">Werte vor dem Historienstart sind unbekannt und wurden nicht rekonstruiert.</p>
        """
    else:
        history_html = """
        <p>Historische Sammlungswerte sind auf diesem Datenstand nicht verfügbar.</p>
        <p class="statistics-history-note">Der heutige Bestand wird nicht als Karrierehistorie ausgegeben.</p>
        """

    return f"""
    <html><head>{style()}</head><body class="s31-product-page"><div class="container">
    {app_header("Meine Statistik", "Aktueller Stand und Karriere.")}

    <a class="statistics-trophy-card album-quick-card" href="/trophaeen">
        <span class="statistics-trophy-icon">{trophy_icon_svg('album_generic')}</span>
        <strong>Trophäenschrank</strong>
        <span>{career.valid_trophy_count if career.valid_trophy_count is not None else 'Historie nicht verfügbar'} gültige Trophäen</span>
    </a>

    <div class="statistics-card">
        <div class="statistics-block">
            <h2>Aktueller Stand</h2>
            <p>{len(projection.current_albums)} aktive Alben</p>
            {current_album_html}
        </div>

        <div class="statistics-block">
            <h2>Karriere</h2>
            {history_html}
        </div>

        <div class="statistics-block">
            <h2>Erfolgreiche Trades</h2>
            <p>{trades.successful_trade_count} {trade_word} abgeschlossen</p>
            <p>{trades.received_quantity_total} Sticker erhalten</p>
            <p>{trades.given_quantity_total} Sticker abgegeben</p>
            <p>{trades.distinct_partner_count} unterschiedliche Tauschpartner</p>
            {largest_html}
        </div>
    </div>

    {bottom_nav("profil")}
    </div></body></html>
    """

def collector_profile_album_section(
    title, albums, is_own, empty_text, profile_username
):
    if albums:
        cards = []
        for album in albums:
            name = escape(album.name)
            if is_own:
                target = f'/album/{quote(album.album_id, safe="")}'
            else:
                target = (
                    f'/profil/{quote(profile_username, safe="")}/album/'
                    f'{quote(album.album_id, safe="")}'
                )
            content = (
                f'<a class="collector-profile-album" href="{target}">'
                f'<strong>{name}</strong></a>'
            )
            cards.append(content)
        content_html = "".join(cards)
    else:
        content_html = f'<p class="collector-profile-empty">{escape(empty_text)}</p>'
    return f"""
    <section class="collector-profile-section">
        <h2>{escape(title)}</h2>
        <div class="collector-profile-albums">{content_html}</div>
    </section>
    """


def collector_profile_owner_navigation():
    return """
    <div class="profile-link-list collector-profile-owner-links">
        <a class="profile-link-card" href="/sammlung">
            <strong>Meine Alben</strong>
            <span>Zur Sammlr Zentrale</span>
        </a>
        <a class="profile-link-card" href="/statistik">
            <strong>Meine Statistik</strong>
            <span>Zur persönlichen Statistik</span>
        </a>
        <a class="profile-link-card" href="/trophaeen">
            <strong>Meine Trophäen</strong>
            <span>Zum vollständigen Trophäenschrank</span>
        </a>
        <a class="profile-link-card" href="/profil/trade-archiv">
            <strong>Trade-Archiv</strong>
            <span>Abgeschlossene Tausche nach Album</span>
        </a>
        <a class="profile-link-card" href="/profil/freunde">
            <strong>Freunde</strong>
            <span>Anfragen, Suche und Freundesliste</span>
        </a>
        <a class="profile-link-card" href="/account">
            <strong>Account & Einstellungen</strong>
            <span>Profildaten, Sicherheit und Datenschutz</span>
        </a>
    </div>
    """


def account_settings_controls(account):
    privacy_label = (
        "Privat · nur bestätigte Freunde"
        if account.profile_privacy == "private" else "Öffentlich"
    )
    return f"""
    <section class="profile-card profile-pass-card" aria-label="Account-Identität">
        <h1>Account & Einstellungen</h1>
        <p><strong>@{escape(account.username)}</strong></p>
        <p>Profil-Sichtbarkeit: {escape(privacy_label)}</p>
    </section>

    <div class="profile-account-section" id="profileAccountPanel">
        <h2>Account verwalten</h2>
        <div class="profile-account-actions">
            <a class="profile-account-button" href="/profil/name">Name bearbeiten</a>
            <a class="profile-account-button" href="/profil/username">Benutzername bearbeiten</a>
            <a class="profile-account-button" href="/profil/password">Passwort ändern</a>
            <a class="profile-account-button" href="/profil/privacy">Profil-Sichtbarkeit</a>
            <a class="profile-account-button" href="/profil/datenexport">Daten exportieren</a>
            <a class="profile-account-button" href="/datenschutz">Datenschutz</a>
            <a class="profile-account-button" href="/impressum">Impressum</a>
            <form method="POST" action="/logout">
                <button type="submit" class="profile-account-button">Abmelden</button>
            </form>
            <form method="POST" action="/profil/deactivate" class="auth-form">
                <label for="accountDeactivateCurrentPassword">Aktuelles Passwort</label>
                <input id="accountDeactivateCurrentPassword" name="current_password"
                       type="password" autocomplete="current-password" required>
                <button type="submit" class="profile-account-button">Konto deaktivieren</button>
            </form>
            <button type="button" class="profile-account-button" onclick="openAccountDeleteDialog()">Sammlr-Konto löschen</button>
        </div>
    </div>

    <div class="account-delete-backdrop" id="accountDeleteDialog" aria-hidden="true">
        <div class="account-delete-dialog" role="dialog" aria-modal="true" aria-labelledby="accountDeleteTitle">
            <h2 id="accountDeleteTitle">Deinen Sammlr Account wirklich löschen?</h2>
            <p>Dein Konto wird dauerhaft anonymisiert. Historische Trades bleiben ohne Profilbezug erhalten.</p>
            <div class="account-delete-actions">
                <button type="button" class="btn gray" onclick="closeAccountDeleteDialog()">Abbrechen</button>
                <form method="POST" action="/profil/delete">
                    <label for="accountDeleteCurrentPassword">Aktuelles Passwort</label>
                    <input id="accountDeleteCurrentPassword" name="current_password"
                           type="password" autocomplete="current-password" required>
                    <label>
                        <input name="confirm_anonymization" type="checkbox" value="yes" required>
                        Ich verstehe, dass mein Sammlr-Konto dauerhaft anonymisiert wird und dieser Vorgang nicht rückgängig gemacht werden kann.
                    </label>
                    <button type="submit" class="btn danger">Account endgültig löschen</button>
                </form>
            </div>
        </div>
    </div>

    <script>
    function openAccountDeleteDialog(){{
        const dialog = document.getElementById('accountDeleteDialog');
        if(!dialog) return;
        dialog.classList.add('active');
        dialog.setAttribute('aria-hidden', 'false');
    }}

    function closeAccountDeleteDialog(){{
        const dialog = document.getElementById('accountDeleteDialog');
        if(!dialog) return;
        dialog.classList.remove('active');
        dialog.setAttribute('aria-hidden', 'true');
    }}
    </script>
    """


def profile_community_context(
    connection, profile_user_id, viewer_user_id, collector_world_visible=True
):
    community = CommunityService(connection)
    if not community.schema_available or profile_user_id == viewer_user_id:
        return None
    blocked = community.is_blocked_between(profile_user_id, viewer_user_id)
    friendship = community.are_friends(profile_user_id, viewer_user_id)
    outgoing = connection.execute(
        """SELECT id FROM friendship_requests
           WHERE requester_user_id=? AND recipient_user_id=? AND status='pending'""",
        (viewer_user_id, profile_user_id),
    ).fetchone()
    incoming = connection.execute(
        """SELECT id FROM friendship_requests
           WHERE requester_user_id=? AND recipient_user_id=? AND status='pending'""",
        (profile_user_id, viewer_user_id),
    ).fetchone()
    own_block = connection.execute(
        "SELECT 1 FROM blocks WHERE blocker_user_id=? AND blocked_user_id=?",
        (viewer_user_id, profile_user_id),
    ).fetchone() is not None
    activity = (
        UserActivityService(connection).label_for(
            profile_user_id, viewer_user_id
        )
        if collector_world_visible and not blocked else None
    )
    return {
        "blocked": blocked,
        "own_block": own_block,
        "friends": friendship,
        "outgoing_request_id": outgoing["id"] if outgoing else None,
        "incoming_request_id": incoming["id"] if incoming else None,
        "activity": activity,
        "collector_world_visible": bool(collector_world_visible),
    }


def collector_profile_community_html(profile, context):
    if not context:
        return ""
    username = quote(profile.username, safe="")
    if context["blocked"]:
        action = (
            f'<form method="POST" action="/profil/{username}/unblock">'
            '<button class="btn gray" type="submit">Blockierung aufheben</button></form>'
            if context["own_block"] else ""
        )
        return (
            '<section class="card collector-profile-community">'
            '<p><strong>Du kannst mit diesem Nutzer derzeit nicht interagieren.</strong></p>'
            f'{action}</section>'
        )
    if context["friends"]:
        relationship = (
            '<strong>Ihr seid befreundet.</strong>'
            f'<form method="POST" action="/profil/freunde/{profile.user_id}/remove">'
            '<button class="btn gray" type="submit">Freundschaft entfernen</button></form>'
        )
    elif context["incoming_request_id"]:
        request_id = context["incoming_request_id"]
        relationship = (
            '<strong>Freundschaftsanfrage offen.</strong>'
            f'<form method="POST" action="/profil/freunde/anfragen/{request_id}/accept">'
            '<button class="btn green" type="submit">Annehmen</button></form>'
            f'<form method="POST" action="/profil/freunde/anfragen/{request_id}/decline">'
            '<button class="btn gray" type="submit">Ablehnen</button></form>'
        )
    elif context["outgoing_request_id"]:
        relationship = '<strong>Freundschaftsanfrage gesendet.</strong>'
    else:
        relationship = (
            f'<form method="POST" action="/profil/freunde/anfragen/{profile.user_id}">'
            '<button class="btn green" type="submit">Freundschaft anfragen</button></form>'
        )
    activity = (
        f'<p>{escape(context["activity"])}</p>' if context["activity"] else ""
    )
    return f"""
    <section class="card collector-profile-community">
        <h2>Community</h2>{activity}{relationship}
        <form method="POST" action="/profil/{username}/block">
            <button class="btn gray" type="submit">Nutzer blockieren</button>
        </form>
    </section>
    """


def collector_profile_completion_section(profile, is_own):
    cards = []
    for completion in profile.historical_completions:
        target = (
            f'/album/{quote(completion.album_id, safe="")}'
            if is_own else
            f'/profil/{quote(profile.username, safe="")}/album/'
            f'{quote(completion.album_id, safe="")}'
        )
        completed_at = getattr(completion, "completed_at", None)
        date_html = (
            f'<time datetime="{escape(completed_at)}">'
            f'{escape(format_sammlr_date(completed_at))}</time>'
            if completed_at else ""
        )
        cards.append(
            f'<a class="collector-profile-album" href="{target}">'
            f'<strong>{escape(completion.name)}</strong>{date_html}</a>'
        )
    content = "".join(cards) or (
        '<p class="collector-profile-empty">Noch keine abgeschlossenen Alben.</p>'
    )
    return f"""
    <section class="collector-profile-section" aria-label="Abgeschlossene Alben">
        <h2>Abgeschlossene Alben</h2>
        <div class="collector-profile-albums">{content}</div>
    </section>
    """


def collector_profile_trophy_section(profile):
    album_names = {
        album.album_id: album.name for album in profile.current_albums
    }
    items = "".join(
        '<li><strong>' + escape(trophy.trophy_name) + '</strong>'
        + (f' · {escape(album_names[trophy.album_id])}'
           if trophy.album_id in album_names else '')
        + '</li>'
        for trophy in profile.valid_trophies
    ) or '<li>Noch keine gültigen Trophäen freigeschaltet.</li>'
    return f"""
    <section class="collector-profile-section" aria-label="Gültige Trophäen">
        <h2>Trophäen</h2>
        <ul class="collector-profile-trophies">{items}</ul>
    </section>
    """


def render_collector_profile(
    profile, is_own, community_context=None, feedback_message=""
):
    username = escape(profile.username)
    connection = get_db()
    try:
        sticker_row = None
        if (
            profile.collector_world_visible
            and profile_sticker_schema_available(connection)
        ):
            sticker_row = connection.execute(
                "SELECT 1 FROM user_profile_stickers WHERE user_id=?",
                (profile.user_id,),
            ).fetchone()
        progress = StatisticsProjectionService(
            connection
        ).current_albums_for_memberships(
            profile.user_id,
            (album.user_album_id for album in profile.current_albums),
        ) if profile.collector_world_visible else ()
        if sticker_row is not None:
            sticker_settings = load_profile_sticker_settings(
                connection,
                profile.user_id,
                profile.display_name or profile.username,
            )
        else:
            sticker_settings = None
    finally:
        connection.close()

    if sticker_settings is not None:
        portrait_url = None
        if sticker_settings.portrait_filename and not is_own:
            portrait_url = (
                f'/profil/{quote(profile.username, safe="")}/sticker/portrait/'
                f'{quote(sticker_settings.portrait_filename, safe="")}'
            )
        sticker_visual = (
            '<div class="collector-showcase-sticker-stage">'
            + render_profile_sticker(
                sticker_settings, editor=True, portrait_url=portrait_url
            )
            + '</div>'
        )
        sticker_action = (
            '<a class="collector-showcase-sticker-action" '
            'href="/profil/sticker/bearbeiten">Sticker bearbeiten</a>'
            if is_own else ""
        )
    else:
        blank_content = """
            <span class="collector-showcase-blank-mark" aria-hidden="true">S.</span>
            <span>Noch frei</span>
        """
        if is_own:
            sticker_visual = (
                '<a class="collector-showcase-blank-sticker" '
                'href="/profil/sticker/bearbeiten" aria-label="Sticker erstellen">'
                f'{blank_content}</a>'
            )
            sticker_action = (
                '<a class="collector-showcase-sticker-action" '
                'href="/profil/sticker/bearbeiten">Sticker erstellen</a>'
            )
        else:
            sticker_visual = (
                '<div class="collector-showcase-blank-sticker" '
                'aria-label="Kein Profilsticker">'
                f'{blank_content}</div>'
            )
            sticker_action = ""

    if not profile.collector_world_visible:
        rating_html = '<span class="collector-showcase-rating">Sammlerdaten nicht sichtbar</span>'
        rating_count = ""
        trade_count = ""
    elif profile.rating_count:
        rating_value = f"{profile.rating_average:.1f}".replace(".", ",")
        rating_html = f'<span class="collector-showcase-rating">★ {rating_value}</span>'
        rating_count = (
            f'{profile.rating_count} Bewertung'
            if profile.rating_count == 1
            else f'{profile.rating_count} Bewertungen'
        )
    else:
        rating_html = '<span class="collector-showcase-rating is-empty">Noch keine Bewertung</span>'
        rating_count = ""
    if profile.collector_world_visible:
        trade_count = (
            f'{profile.successful_trade_count} Tausch'
            if profile.successful_trade_count == 1
            else f'{profile.successful_trade_count} Tausche'
        )
    trust_separator = " · " if rating_count else ""

    progress_by_membership = {
        item.user_album_id: item for item in progress
    }
    active_cards = []
    covers_by_membership = {
        album.user_album_id: album.cover for album in profile.current_albums
    }
    for position, album in enumerate(profile.current_albums, start=1):
        stats = progress_by_membership.get(album.user_album_id)
        if stats is None:
            continue
        target = (
            f'/album/{quote(album.album_id, safe="")}'
            if is_own else
            f'/profil/{quote(profile.username, safe="")}/album/'
            f'{quote(album.album_id, safe="")}'
        )
        active_cards.append(f"""
            <a class="collector-showcase-album" href="{target}"
               data-profile-album-order="{position}">
                <span class="collector-showcase-cover" aria-hidden="true">
                    <strong>{escape(str(album.cover))}</strong>
                    <small>{escape(str(album.season))}</small>
                </span>
                <span class="collector-showcase-album-copy">
                    <strong>{escape(album.name)}</strong>
                    <span class="collector-showcase-progress-copy">
                        <span>{stats.collected} / {stats.total}</span><b>{stats.percent}&nbsp;%</b>
                    </span>
                    <span class="collector-showcase-progress" role="progressbar"
                          aria-label="Albumfortschritt" aria-valuemin="0"
                          aria-valuemax="100" aria-valuenow="{stats.percent}">
                        <span style="width:{stats.percent}%"></span>
                    </span>
                </span>
            </a>
        """)
    active_content = "".join(active_cards) or (
        '<p class="collector-showcase-empty">Keine aktiven Alben.</p>'
    )

    completion_cards = []
    for completion in profile.historical_completions:
        target = (
            f'/album/{quote(completion.album_id, safe="")}'
            if is_own else
            f'/profil/{quote(profile.username, safe="")}/album/'
            f'{quote(completion.album_id, safe="")}'
        )
        completion_cards.append(f"""
            <a class="collector-showcase-album is-complete" href="{target}">
                <span class="collector-showcase-cover" aria-hidden="true">
                    <strong>{escape(str(covers_by_membership.get(completion.user_album_id, completion.album_id.upper())))}</strong>
                    <small>{escape(str(completion.season))}</small>
                </span>
                <span class="collector-showcase-album-copy">
                    <strong>{escape(completion.name)}</strong>
                    <span class="collector-showcase-completed">Vervollständigt</span>
                    <time datetime="{escape(completion.completed_at)}">{escape(format_sammlr_date(completion.completed_at))}</time>
                </span>
            </a>
        """)
    completion_html = ""
    if completion_cards:
        completion_html = f"""
            <section class="collector-showcase-section" aria-labelledby="completed-albums-title">
                <h2 id="completed-albums-title">Abgeschlossene Alben</h2>
                <div class="collector-showcase-album-grid">{''.join(completion_cards)}</div>
            </section>
        """

    from profile_trade import profile_trade_html
    trade_html = profile_trade_html(DB, current_user_id(), profile) if not is_own else ""

    collector_world_html = f"""
        <section class="collector-showcase-section" aria-labelledby="active-albums-title">
            <h2 id="active-albums-title">Sammelt gerade</h2>
            <div class="collector-showcase-album-grid">{active_content}</div>
        </section>
        {trade_html}
        {completion_html}
    """ if profile.collector_world_visible else """
        <p class="collector-showcase-private" role="status">
            Dieses Profil ist privat.
        </p>
    """ + trade_html
    return f"""
    <html><head>{style()}
    <link rel="stylesheet" href="/static/profile_sticker.css">
    <link rel="stylesheet" href="/static/profile_v1.css">
    </head><body class="s31-product-page"><div class="container collector-showcase-page">
    {app_header(variant="compact", foundation=True, own_profile_settings=is_own and request.path == "/profil")}
    {sammlr_feedback_html(feedback_message)}
    <main class="collector-showcase" aria-label="Sammlervitrine">
        <section class="collector-showcase-header" aria-label="Sammlerprofil">
            <div class="collector-showcase-sticker">
                {sticker_visual}
                {sticker_action}
            </div>
            <div class="collector-showcase-identity">
                <div class="collector-showcase-identity-top">
                    <h1>@{username}</h1>
                </div>
                <div class="collector-showcase-trust">
                    {rating_html}
                    <span>{escape(rating_count)}{trust_separator}{trade_count}</span>
                </div>
            </div>
        </section>
        {collector_world_html}
    </main>
    {bottom_nav("profil")}
    </div></body></html>
    """


@app.route("/profil")
@serialized_sqlite_projection
def profil():
    con = get_db()
    profile = CollectorProfileService(
        con, configured_friendship_checker()
    ).by_user_id(current_user_id(), current_user_id())
    con.close()
    if profile is None:
        abort(404)
    return render_collector_profile(profile, True)


def profile_sticker_editor_response(settings, error="", status=200):
    countries = tuple(PROFILE_STICKER_COUNTRIES.values())
    colors = tuple(PROFILE_STICKER_COLORS.values())
    countries_json = json.dumps(
        {item.code: {"code": item.code, "label": item.label, "bands": item.flag_bands} for item in countries},
        ensure_ascii=False,
    )
    colors_json = json.dumps(
        {item.code: {"code": item.code, "label": item.label, "hex": item.hex_value, "contrast": item.contrast} for item in colors},
        ensure_ascii=False,
    )
    return render_template(
        "profile_sticker_edit.html",
        style_html=style(),
        header_html=app_header("Sticker bearbeiten", "Dein 70er-Profilsticker."),
        bottom_nav_html=bottom_nav("profil"),
        sticker_html=render_profile_sticker(settings, editor=True),
        settings=settings,
        countries=countries,
        colors=colors,
        countries_json=countries_json,
        colors_json=colors_json,
        error=error,
    ), status


@app.route("/profil/sticker/bearbeiten", methods=["GET", "POST"])
def profile_sticker_edit():
    user_id = current_user_id()
    connection = get_db()
    user = connection.execute("SELECT name, username FROM users WHERE id=?", (user_id,)).fetchone()
    if user is None:
        connection.close()
        abort(404)
    current = load_profile_sticker_settings(
        connection, user_id, user["name"] or user["username"] or "SAMMLR"
    )
    if request.method == "GET":
        connection.close()
        return profile_sticker_editor_response(current)
    if not profile_sticker_schema_available(connection):
        connection.close()
        abort(503)

    new_filename = None
    storage_dir = Path(app.config["PROFILE_PORTRAIT_DIR"])
    try:
        name, country, club, accent, crop_x, crop_y, crop_zoom = validate_profile_sticker_settings(
            request.form.get("display_name"), request.form.get("country_code"),
            request.form.get("club_name"), request.form.get("accent_color"),
            request.form.get("crop_x", current.crop_x), request.form.get("crop_y", current.crop_y),
            request.form.get("crop_zoom", current.crop_zoom),
        )
        portrait_filename, portrait_mime = current.portrait_filename, current.portrait_mime
        portrait_width, portrait_height = current.portrait_width, current.portrait_height
        uploaded = request.files.get("portrait")
        if uploaded is not None and uploaded.filename:
            payload = uploaded.stream.read(900 * 1024 + 1)
            new_filename, portrait_mime, portrait_width, portrait_height = store_portrait(payload, storage_dir)
            portrait_filename = new_filename
        updated = ProfileStickerSettings(
            user_id, name, country, club, accent, portrait_filename,
            portrait_mime, crop_x, crop_y, crop_zoom, portrait_width, portrait_height,
        )
        save_profile_sticker_settings(connection, updated)
        connection.commit()
    except ProfileStickerValidationError as error:
        connection.rollback()
        if new_filename:
            remove_portrait(storage_dir, new_filename)
        connection.close()
        return profile_sticker_editor_response(current, str(error), 400)
    except Exception:
        connection.rollback()
        if new_filename:
            remove_portrait(storage_dir, new_filename)
        connection.close()
        raise
    connection.close()
    if new_filename and current.portrait_filename != new_filename:
        remove_portrait(storage_dir, current.portrait_filename)
    return redirect("/profil")


@app.route("/profil/sticker/portrait/<filename>")
def profile_sticker_portrait(filename):
    if SAFE_PORTRAIT_NAME.fullmatch(filename) is None:
        abort(404)
    connection = get_db()
    row = connection.execute(
        "SELECT portrait_filename FROM user_profile_stickers WHERE user_id=?",
        (current_user_id(),),
    ).fetchone() if profile_sticker_schema_available(connection) else None
    connection.close()
    if row is None or row["portrait_filename"] != filename:
        abort(404)
    response = send_from_directory(app.config["PROFILE_PORTRAIT_DIR"], filename)
    response.headers["Cache-Control"] = "private, max-age=3600"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.route("/profil/<username>/sticker/portrait/<filename>")
def public_profile_sticker_portrait(username, filename):
    if SAFE_PORTRAIT_NAME.fullmatch(filename) is None:
        abort(404)
    connection = get_db()
    profile = CollectorProfileService(
        connection, configured_friendship_checker()
    ).by_username(username, current_user_id())
    row = None
    if (
        profile is not None
        and profile.collector_world_visible
        and profile_sticker_schema_available(connection)
    ):
        row = connection.execute(
            "SELECT portrait_filename FROM user_profile_stickers WHERE user_id=?",
            (profile.user_id,),
        ).fetchone()
    connection.close()
    if row is None or row["portrait_filename"] != filename:
        abort(404)
    response = send_from_directory(app.config["PROFILE_PORTRAIT_DIR"], filename)
    response.headers["Cache-Control"] = "private, max-age=3600"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.route("/account")
def account_settings():
    con = get_db()
    account = AccountSettingsService(con).for_owner(current_user_id())
    con.close()
    if account is None:
        abort(404)
    return f"""
    <html><head>{style()}</head><body class="s31-product-page"><div class="container">
    {app_header("Account & Einstellungen", "Interne Kontoverwaltung.")}
    <a class="sammlr-back-link" href="/profil">← Zurück zum Profil</a>
    {account_settings_controls(account)}
    {bottom_nav("profil")}
    </div></body></html>
    """


@app.route("/profil/<username>")
@serialized_sqlite_projection
def public_profile(username):
    con = get_db()
    profile = CollectorProfileService(
        con, configured_friendship_checker()
    ).by_username(username, current_user_id())
    if profile is None:
        con.close()
        abort(404)
    con.close()
    return render_collector_profile(
        profile,
        profile.user_id == current_user_id(),
        None,
        request.args.get("message", ""),
    )


@app.route("/profil/freunde")
def profile_friends():
    con = get_db()
    service = CommunityService(con)
    if not service.schema_available:
        con.close()
        abort(404)
    friends = service.friends(current_user_id())
    incoming, outgoing = service.pending_requests(current_user_id())
    query = request.args.get("q", "")
    results = service.search(current_user_id(), query)
    friend_html = "".join(
        f'<li><a href="/profil/{quote(friend.username, safe="")}">@{escape(friend.username)}</a>'
        f' · {escape(friend.activity_label or "")}</li>' for friend in friends
    ) or "<li>Noch keine Freunde.</li>"
    incoming_html = "".join(
        f'<li id="friend-request-{row["id"]}">@{escape(row["username"])} '
        f'<form method="POST" action="/profil/freunde/anfragen/{row["id"]}/accept"><button type="submit">Annehmen</button></form> '
        f'<form method="POST" action="/profil/freunde/anfragen/{row["id"]}/decline"><button type="submit">Ablehnen</button></form></li>'
        for row in incoming
    ) or "<li>Keine eingehenden Anfragen.</li>"
    outgoing_html = "".join(
        f'<li>@{escape(row["username"])} '
        f'<form method="POST" action="/profil/freunde/anfragen/{row["id"]}/cancel"><button type="submit">Zurückziehen</button></form></li>'
        for row in outgoing
    ) or "<li>Keine gesendeten Anfragen.</li>"
    result_html = "".join(
        f'<li><a href="/profil/{quote(user.username, safe="")}">@{escape(user.username)}</a>'
        + (' · Bereits befreundet' if user.already_friends else '') + '</li>'
        for user in results
    )
    if query.strip() and not result_html:
        result_html = '<li class="sammlr-empty-state">Keine Suchergebnisse.</li>'
    message_html = sammlr_feedback_html(request.args.get("message", ""))
    con.close()
    return f"""
    <html><head>{style()}</head><body class="s31-product-page"><div class="container">
    {app_header("Freunde", "Deine Sammlr-Verbindungen.")}
    {message_html}
    <section class="card"><h2>Freunde</h2><ul>{friend_html}</ul></section>
    <section class="card"><h2>Anfragen</h2><ul>{incoming_html}</ul><ul>{outgoing_html}</ul></section>
    <section class="card"><h2>Nutzer suchen</h2>
      <form method="GET"><input name="q" value="{escape(query)}" placeholder="Benutzername"><button type="submit">Suchen</button></form>
      <ul>{result_html}</ul>
    </section>{bottom_nav("profil")}</div></body></html>
    """


def _community_redirect_message(result):
    messages = {
        CommunityMutationCode.CREATED: "Freundschaftsanfrage gesendet",
        CommunityMutationCode.ACCEPTED: "Freundschaft bestätigt",
        CommunityMutationCode.DECLINED: "Freundschaftsanfrage abgelehnt",
        CommunityMutationCode.CANCELLED: "Freundschaftsanfrage zurückgezogen",
        CommunityMutationCode.REMOVED: "Freundschaft entfernt",
        CommunityMutationCode.BLOCKED: "Nutzer blockiert",
        CommunityMutationCode.UNBLOCKED: "Blockierung aufgehoben",
        CommunityMutationCode.BLOCKED_INTERACTION: "Interaktion derzeit nicht möglich",
    }
    return messages.get(result.code, "Aktion nicht möglich")


@app.route("/profil/freunde/anfragen/<int:user_id>", methods=["POST"])
def send_friend_request(user_id):
    con = get_db()
    result = CommunityService(con).send_request(current_user_id(), user_id)
    con.close()
    return redirect(f"/profil/freunde?message={quote(_community_redirect_message(result))}")


@app.route("/profil/freunde/anfragen/<int:request_id>/<action>", methods=["POST"])
def mutate_friend_request(request_id, action):
    con = get_db()
    service = CommunityService(con)
    handlers = {
        "accept": service.accept_request,
        "decline": service.decline_request,
        "cancel": service.cancel_request,
    }
    handler = handlers.get(action)
    if handler is None:
        con.close()
        abort(404)
    result = handler(request_id, current_user_id())
    con.close()
    return redirect(f"/profil/freunde?message={quote(_community_redirect_message(result))}")


@app.route("/profil/freunde/<int:user_id>/remove", methods=["POST"])
def remove_friend(user_id):
    con = get_db()
    result = CommunityService(con).remove_friendship(user_id, current_user_id())
    con.close()
    return redirect(f"/profil/freunde?message={quote(_community_redirect_message(result))}")


@app.route("/profil/<username>/block", methods=["POST"])
@app.route("/profil/<username>/unblock", methods=["POST"])
def mutate_user_block(username):
    con = get_db()
    user = con.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if user is None:
        con.close()
        abort(404)
    service = CommunityService(con)
    result = (
        service.unblock(current_user_id(), user["id"])
        if request.path.endswith("/unblock")
        else service.block(current_user_id(), user["id"])
    )
    con.close()
    return redirect(f"/profil/{quote(username, safe='')}?message={quote(_community_redirect_message(result))}")


def foreign_album_readmodel(username, album_id):
    con = get_db()
    owner = con.execute(
        "SELECT id, username FROM users WHERE username=?",
        (username,),
    ).fetchone()
    album = con.execute(
        "SELECT id, name, total FROM albums WHERE id=?",
        (album_id,),
    ).fetchone()
    if (
        owner is None
        or album is None
        or not album_privacy_service(con).can_view(
            current_user_id(), owner["id"], album_id
        )
    ):
        con.close()
        return None
    codes = tuple(all_codes(album_id))
    inventory = InventoryReadService(con).album(owner["id"], album_id, codes)
    total = len(codes) if album_id in {"em24", "wm26"} else int(album["total"])
    progress = inventory.progress(codes, total)
    con.close()
    return owner, album, codes, inventory, progress


@app.route("/profil/<username>/album/<album_id>")
def public_profile_album(username, album_id):
    readmodel = foreign_album_readmodel(username, album_id)
    if readmodel is None:
        abort(404)
    owner, album, codes, inventory, progress = readmodel
    potential_html = ""
    if owner["id"] != current_user_id():
        potential_connection = get_db()
        potential_privacy = album_privacy_service(potential_connection)
        if (
            CommunityService(potential_connection).can_start_interaction(
                current_user_id(), owner["id"]
            )
            and potential_privacy.is_trade_pool_enabled(current_user_id(), album_id)
            and potential_privacy.is_trade_pool_enabled(owner["id"], album_id)
        ):
            potential_html = (
                f'<a class="trade-partner-button" href="/album/{quote(album_id, safe="")}/smart-trades">'
                'Tauschpotenzial in TopMatch öffnen</a>'
            )
        potential_connection.close()
    filter_name = request.args.get("filter", "all")
    if filter_name not in {"all", "missing", "owned", "duplicate"}:
        filter_name = "all"
    base_path = (
        f'/profil/{quote(owner["username"], safe="")}/album/'
        f'{quote(album_id, safe="")}'
    )
    visible_count = sum(
        filter_ok(filter_name, code, inventory.items_by_code) for code in codes
    )
    wall = canonical_sticker_wall_html(
        album_id,
        inventory.items_by_code,
        inventory,
        filter_name,
        can_edit_inventory=False,
        public_detail_base=base_path,
    )
    public_wall_body_class = (
        "s31-product-page s30-reference-page s30-" +
        "album-page s30-public-album-page"
    )
    return f"""
    <html><head>{style()}<script defer src="/static/sticker_wall_read_only.js"></script></head>
    <body class="{public_wall_body_class}">
    <div class="container public-album-page">
    {app_header("Album von @" + owner["username"], album["name"])}
    <a class="sammlr-back-link" href="/profil/{quote(owner['username'], safe='')}">← Zum Profil</a>
    <div class="album-title-progress">
        <i class="chapter-progress-fill" style="width:{progress.percent}%;"></i>
        <span>{escape(album['name'])}</span>
        <span>{progress.percent}%</span>
    </div>
    <section class="card public-album-summary">
        <strong>{progress.collected} von {progress.total}</strong>
        <span>{progress.total - progress.collected} fehlend</span>
        <span>{progress.duplicate_quantity} doppelt</span>
    </section>
    {potential_html}
    <section class="card sticker-wall-card" aria-labelledby="public-wall-title">
        <div class="sticker-wall-controlbar">
            <div class="sticker-wall-headline"><h2 id="public-wall-title">Stickerwand</h2></div>
            <div class="sticker-filter-row">
                <a class="sticker-filter-pill{' active' if filter_name == 'all' else ''}" href="{base_path}" data-filter="all">Alle</a>
                <a class="sticker-filter-pill missing{' active' if filter_name == 'missing' else ''}" href="{base_path}?filter=missing" data-filter="missing">Fehlende</a>
                <a class="sticker-filter-pill duplicate{' active' if filter_name == 'duplicate' else ''}" href="{base_path}?filter=duplicate" data-filter="duplicate">Doppelte</a>
            </div>
            <input id="stickerSearch" class="sticker-search" type="search" placeholder="Sticker suchen..." autocomplete="off">
        </div>
        <div id="searchDebugBox" class="search-debug-box" style="display:none;"></div>
        <span id="stickerDetailTransit" hidden aria-hidden="true"></span>
        <p><strong id="visibleStickerCount">{visible_count}</strong> Sticker</p>
        <div class="sticker-wall-sticky-anchor">
            <div class="sticker-wall-sticky-context" id="stickerWallStickyContext" hidden aria-hidden="true">
                <i class="chapter-progress-track" aria-hidden="true"><i class="chapter-progress-fill" data-sticky-context-progress></i></i>
                <span class="sticker-wall-context-label" data-sticky-context-label></span>
                <span class="sticker-wall-context-counter" data-sticky-context-counter></span>
            </div>
        </div>
        {wall}
    </section>
    {bottom_nav("profil")}
    </div></body></html>
    """


@app.route("/profil/<username>/album/<album_id>/sticker/<path:code>")
def public_profile_sticker(username, album_id, code):
    readmodel = foreign_album_readmodel(username, album_id)
    if readmodel is None:
        abort(404)
    owner, album, codes, inventory, _progress = readmodel
    resolved = resolve_code(album_id, code)
    if resolved is None or resolved not in codes:
        abort(404)
    snapshot = inventory.availability_snapshot_for(resolved)
    status = sticker_status_label_for_quantity(snapshot.physical)
    return f"""
    <html><head>{style()}</head><body class="s31-product-page"><div class="container public-sticker-detail-page">
    {app_header("Sticker", album["name"])}
    <a class="sammlr-back-link" href="/profil/{quote(owner['username'], safe='')}/album/{quote(album_id, safe='')}">← Zur Stickerwand</a>
    <section class="card sticker-detail-card">
        <p>Stickercode</p>
        <h1>{escape(display_code(resolved))}</h1>
        <p>Status: <strong>{escape(status)}</strong></p>
        <p>Anzahl: <strong>{snapshot.physical}</strong></p>
        <p>Doppelte: <strong>{snapshot.duplicates}</strong></p>
    </section>
    {bottom_nav("profil")}
    </div></body></html>
    """


@app.route("/profil/trade-archiv")
def profil_trade_archiv():
    archive_html = profile_trade_archive_html(current_user_id())
    return f"""
    <html><head>{style()}</head><body class="s31-product-page"><div class="container">
    {app_header("Trade-Archiv", "Abgeschlossene Tausche nach Album.")}
    <a class="sammlr-back-link trade-back-link" href="/profil">← Zurück</a>

    <section class="profile-section profile-trade-archive profile-trade-archive-page">
        {archive_html}
    </section>

    {bottom_nav("profil")}
    </div></body></html>
    """


@app.route("/profil/name", methods=["GET", "POST"])
def profil_name():
    user_id = current_user_id()
    message = ""
    con = get_db()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if len(name) > MAX_PROFILE_NAME_LENGTH:
            message = "Name konnte nicht gespeichert werden."
        else:
            con.execute("UPDATE users SET name=? WHERE id=?", (name, user_id))
            con.commit()
            con.close()
            return redirect("/account")

    user = con.execute("SELECT name, username FROM users WHERE id=?", (user_id,)).fetchone()
    con.close()
    name = user["name"] if user and user["name"] else ""

    return f"""
    <html><head>{style()}</head><body class="s31-product-page"><div class="container">
    {app_header("Name bearbeiten")}
    <a class="sammlr-back-link" href="/account">← Zurück zum Account</a>
    <div class="profile-account-form">
        <h1>Name bearbeiten</h1>
        {f'<div class="auth-error">{message}</div>' if message else ''}
        <form method="POST" class="auth-form">
            <label>Name</label>
            <input name="name" value="{escape(name)}" maxlength="{MAX_PROFILE_NAME_LENGTH}" autocomplete="name">
            <button type="submit" class="auth-submit">Speichern</button>
        </form>
    </div>
    {bottom_nav("profil")}
    </div></body></html>
    """


@app.route("/profil/username", methods=["GET", "POST"])
def profil_username():
    user_id = current_user_id()
    error = ""
    con = get_db()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        if not username or len(username) > MAX_USERNAME_LENGTH:
            error = "Bitte gib einen Benutzernamen ein."
        else:
            try:
                con.execute("UPDATE users SET username=? WHERE id=?", (username, user_id))
                con.commit()
                session["username"] = username
                con.close()
                return redirect("/account")
            except sqlite3.IntegrityError:
                error = "Benutzername ist bereits vergeben."

    user = con.execute("SELECT username FROM users WHERE id=?", (user_id,)).fetchone()
    con.close()
    username = user["username"] if user and user["username"] else session.get("username", "")

    return f"""
    <html><head>{style()}</head><body class="s31-product-page"><div class="container">
    {app_header("Benutzername bearbeiten")}
    <a class="sammlr-back-link" href="/account">← Zurück zum Account</a>
    <div class="profile-account-form">
        <h1>Benutzername bearbeiten</h1>
        {f'<div class="auth-error">{error}</div>' if error else ''}
        <form method="POST" class="auth-form">
            <label>Benutzername</label>
            <input name="username" value="{escape(username)}" maxlength="{MAX_USERNAME_LENGTH}" autocomplete="username">
            <button type="submit" class="auth-submit">Speichern</button>
        </form>
    </div>
    {bottom_nav("profil")}
    </div></body></html>
    """


@app.route("/profil/password", methods=["GET", "POST"])
def profil_password():
    user_id = current_user_id()
    error = ""
    con = get_db()

    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        repeat_password = request.form.get("repeat_password", "")

        password_service = AuthSecurityService(con)
        if (
            len(current_password) > MAX_PASSWORD_LENGTH
            or len(new_password) > MAX_PASSWORD_LENGTH
            or len(repeat_password) > MAX_PASSWORD_LENGTH
        ):
            error = "Passwort konnte nicht bestätigt werden."
        elif not password_service.password_matches(user_id, current_password):
            error = "Passwort konnte nicht bestätigt werden."
        elif not new_password:
            error = "Bitte gib ein neues Passwort ein."
        elif new_password != repeat_password:
            error = "Passwörter stimmen nicht überein."
        else:
            next_version = password_service.change_password(
                user_id, current_password, new_password
            )
            if next_version is None:
                error = "Passwort konnte nicht bestätigt werden."
            else:
                con.close()
                session.clear()
                return redirect("/login")

    con.close()
    return f"""
    <html><head>{style()}</head><body class="s31-product-page"><div class="container">
    {app_header("Passwort ändern")}
    <a class="sammlr-back-link" href="/account">← Zurück zum Account</a>
    <div class="profile-account-form">
        <h1>Passwort ändern</h1>
        {f'<div class="auth-error">{error}</div>' if error else ''}
        <form method="POST" class="auth-form">
            <label>Aktuelles Passwort</label>
            <input name="current_password" type="password" autocomplete="current-password">
            <label>Neues Passwort</label>
            <input name="new_password" type="password" autocomplete="new-password">
            <label>Neues Passwort wiederholen</label>
            <input name="repeat_password" type="password" autocomplete="new-password">
            <button type="submit" class="auth-submit">Speichern</button>
        </form>
    </div>
    {bottom_nav("profil")}
    </div></body></html>
    """


@app.route("/profil/privacy", methods=["GET", "POST"])
def profile_privacy_settings():
    user_id = current_user_id()
    con = get_db()
    service = ProfilePrivacyService(con)
    if not service.schema_available:
        con.close()
        abort(404)
    if request.method == "POST":
        value = request.form.get("profile_privacy", "")
        if value not in PROFILE_PRIVACIES:
            con.close()
            abort(400)
        result = service.update(user_id, user_id, value)
        if result.code == ProfilePrivacyUpdateCode.UPDATED:
            con.commit()
            con.close()
            return redirect("/account")
        con.rollback()
        con.close()
        if result.code == ProfilePrivacyUpdateCode.INVALID_PRIVACY:
            abort(400)
        abort(404)

    value = service.privacy_for_user(user_id)
    con.close()
    if value not in PROFILE_PRIVACIES:
        abort(404)
    return f"""
    <html><head>{style()}</head><body class="s31-product-page"><div class="container">
    {app_header("Profil-Sichtbarkeit")}
    <a class="sammlr-back-link" href="/account">← Zurück zum Account</a>
    <section class="card profile-account-form">
        <h1>Profil-Sichtbarkeit</h1>
        <p>Lege fest, wer deine Sammlerwelt sehen darf. Album-Sichtbarkeit und Tradepool bleiben separat.</p>
        <form method="POST" class="auth-form">
            <label for="profilePrivacy">Profil</label>
            <select id="profilePrivacy" name="profile_privacy">
                <option value="public"{' selected' if value == 'public' else ''}>Öffentlich</option>
                <option value="private"{' selected' if value == 'private' else ''}>Privat · nur bestätigte Freunde</option>
            </select>
            <button type="submit" class="auth-submit">Speichern</button>
        </form>
    </section>
    {bottom_nav("profil")}
    </div></body></html>
    """


@app.route("/profil/datenexport", methods=["GET", "POST"])
def profile_data_export():
    user_id = current_user_id()
    if request.method == "POST":
        con = get_db()
        try:
            if not AuthSecurityService(con).password_matches(
                user_id, request.form.get("current_password", "")
            ):
                return "Passwort konnte nicht bestätigt werden.", 403
            export = UserDataExportService(con).export_for_user(user_id)
            if export is None:
                return "Datenexport konnte nicht erstellt werden.", 404
            payload = export.to_json_bytes()
        finally:
            con.close()
        response = Response(payload, content_type="application/json; charset=utf-8")
        response.headers["Content-Disposition"] = (
            f'attachment; filename="sammlr-datenexport-{int(user_id)}.json"'
        )
        response.headers["Content-Length"] = str(len(payload))
        return response

    return f"""
    <html lang="de"><head>{style()}</head><body class="s31-product-page"><main class="container">
        {app_header("Daten exportieren", "Lade deine Sammlr-Daten als JSON herunter.")}
        <a class="sammlr-back-link" href="/account">← Zurück zum Account</a>
        <section class="card profile-account-form">
            <p>Der Export enthält deine Account-, Profil-, Sammlungs-, Trade-,
               Bewertungs-, Community-, Notification-, Trophy-, Privacy- und
               Aktivitätsdaten. Er wird als einzelnes UTF-8-JSON-Dokument erzeugt.</p>
            <p>Zur Sicherheit musst du dein aktuelles Passwort erneut eingeben.</p>
            <form method="POST" class="auth-form">
                <label for="dataExportCurrentPassword">Aktuelles Passwort</label>
                <input id="dataExportCurrentPassword" name="current_password"
                       type="password" autocomplete="current-password" required>
                <button type="submit" class="auth-submit">JSON-Export erstellen</button>
            </form>
            <p><a href="/datenexport-hinweise">Vollständige Exporthinweise</a></p>
        </section>
        {compliance_links_html()}
        {bottom_nav("profil")}
    </main></body></html>
    """


@app.route("/profil/delete", methods=["POST"])
def profil_delete():
    user_id = current_user_id()
    con = get_db()
    result = AccountLifecycleService(con).anonymize(
        user_id,
        request.form.get("current_password", ""),
        request.form.get("confirm_anonymization") == "yes",
    )
    con.close()
    if result.code == AccountLifecycleCode.INVALID_PASSWORD:
        return "Passwort konnte nicht bestätigt werden.", 403
    if result.code == AccountLifecycleCode.CONFIRMATION_REQUIRED:
        return "Die dauerhafte Anonymisierung muss bestätigt werden.", 400
    if result.code == AccountLifecycleCode.RUNNING_TRADES:
        return (
            "Dein Konto besitzt noch laufende Tauschaktionen. Bitte schließe diese zuerst vollständig ab.",
            409,
        )
    if result.code != AccountLifecycleCode.ANONYMIZED:
        return "Konto konnte nicht anonymisiert werden.", 409
    session.clear()
    return redirect("/login")


@app.route("/profil/deactivate", methods=["POST"])
def profil_deactivate():
    user_id = current_user_id()
    con = get_db()
    result = AccountLifecycleService(con).deactivate(
        user_id, request.form.get("current_password", "")
    )
    con.close()
    if result.code == AccountLifecycleCode.INVALID_PASSWORD:
        return "Passwort konnte nicht bestätigt werden.", 403
    if result.code != AccountLifecycleCode.DEACTIVATED:
        return "Konto konnte nicht deaktiviert werden.", 409
    session.clear()
    return redirect("/login")


from sticker_list import register_sticker_list_routes


stickerliste, stickerliste_trade = register_sticker_list_routes(
    app,
    {
        "load_album": lade_album,
        "all_codes": all_codes,
        "display_code": display_code,
        "ceoklaue_run": ceoklaue_runtime_run,
        "ceoklaue_mix_index": ceoklaue_runtime_mix_index,
        "ceoklaue_marker_asset": ceoklaue_marker_asset,
        "bracket_button_content": ceoklaue_bracket_button_content,
        "feedback_html": sammlr_feedback_html,
        "consume_trophy_popup_html": consume_trophy_popup_html,
        "app_header_brand_wordmark": app_header_brand_wordmark,
        "global_head": style,
        "bottom_nav": bottom_nav,
        "resolve_code": resolve_code,
        "reached_trophies": erreichte_trophaeen,
        "history_request_event_key": history_request_event_key,
        "get_db": get_db,
        "current_user_id": current_user_id,
        "remove_sticker_quantity": remove_sticker_quantity,
        "add_sticker_quantity": add_sticker_quantity,
        "record_trophy_unlocks": record_trophy_unlocks,
        "queue_trophy_popup": queue_trophy_popup,
        "ceoklaue_mixing_seed": CEOKLAUE_RUNTIME_MIXING_SEED,
    },
)


from trade_visual_preview import register_trade_visual_preview

register_trade_visual_preview(app)


from trade_shell import register_trade_shell

register_trade_shell(
    app, database_path=lambda: DB, global_head=style, header=app_header,
    navigation=bottom_nav, render_slot=sticker_wall_slot_html,
    csrf_token=ensure_csrf_token,
)


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=8080)
