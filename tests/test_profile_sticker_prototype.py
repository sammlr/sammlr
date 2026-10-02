import atexit
import base64
import hashlib
import io
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest
from html.parser import HTMLParser


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "App"
REFERENCE_DB = APP / "Database" / "sammlr_reference_s00.db"
LOCAL_DB = APP / "Database" / "sammlr.db"
PROTECTED = tuple(APP / name for name in (
    "sticker_list.py", "templates/sticker_list.html",
    "static/sticker_list.css", "static/sticker_list.js",
))
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class StickerMarkupParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.nation_colors = []
        self.nation_separators = 0
        self.series_marks = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = set(attributes.get("class", "").split())
        if tag == "path" and "profile-sticker-nation-color" in classes:
            self.nation_colors.append(attributes.get("style"))
        if tag == "path" and "profile-sticker-nation-separator" in classes:
            self.nation_separators += 1
        if tag == "img" and "profile-sticker-series-mark" in classes:
            self.series_marks.append(attributes)


bootstrap = tempfile.TemporaryDirectory(prefix="sammlr-profile-sticker-bootstrap-")
atexit.register(bootstrap.cleanup)
bootstrap_db = Path(bootstrap.name) / "bootstrap.db"
shutil.copy2(REFERENCE_DB, bootstrap_db)
os.environ["DATABASE_PATH"] = str(bootstrap_db)
os.environ.setdefault("SAMMLR_ENV", "testing")
os.environ.setdefault("SAMMLR_SECRET_KEY", "profile-sticker-test-secret")
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP))

import webapp  # noqa: E402
from App.Database.migration_runner import migrate  # noqa: E402
from profile_sticker import (  # noqa: E402
    PROFILE_STICKER_COLORS, PROFILE_STICKER_COUNTRIES, PROFILE_STICKER_NATION_LIGHT_BLUE,
    ProfileStickerValidationError, inspect_portrait, validate_settings,
)


class ProfileSticker70Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local_hash = digest(LOCAL_DB)
        cls.protected_hashes = {path: digest(path) for path in PROTECTED}
        webapp.app.config.update(TESTING=True, CSRF_ENABLED=True)

    @classmethod
    def tearDownClass(cls):
        assert cls.local_hash == digest(LOCAL_DB)
        assert cls.protected_hashes == {path: digest(path) for path in PROTECTED}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sammlr-profile-sticker-")
        root = Path(self.temp.name)
        self.database = root / "test.db"
        self.portraits = root / "portraits"
        shutil.copy2(REFERENCE_DB, self.database)
        with sqlite3.connect(self.database) as connection:
            migrate(connection, 20)
        webapp.DB = str(self.database)
        webapp.app.config["PROFILE_PORTRAIT_DIR"] = str(self.portraits)
        self.client = webapp.app.test_client()
        with self.client.session_transaction() as session:
            session["user_id"] = 1

    def tearDown(self):
        self.temp.cleanup()

    def post(self, **changes):
        data = {
            "display_name": "VALENTIN", "country_code": "DE", "club_name": "",
            "accent_color": "purple", "crop_x": "0", "crop_y": "0", "crop_zoom": "1",
        }
        data.update(changes)
        return self.client.post("/profil/sticker/bearbeiten", data=data)

    def test_profile_default_and_editor_are_70s_only_and_asset_isolated(self):
        blank = self.client.get("/profil").get_data(as_text=True)
        self.assertIn("Sticker erstellen", blank)
        self.assertNotIn('data-profile-sticker-era="70s"', blank)
        self.post()
        profile = self.client.get("/profil").get_data(as_text=True)
        self.assertIn('data-profile-sticker-era="70s"', profile)
        self.assertIn("Sticker bearbeiten", profile)
        self.assertNotIn("90s", profile)
        self.assertNotIn("sticker_list.css", profile)
        editor = self.client.get("/profil/sticker/bearbeiten").get_data(as_text=True)
        for text in ("Live-Vorschau", "Foto aufnehmen", "Foto auswählen", "Nation", "Verein", "Farbe"):
            self.assertIn(text, editor)
        self.assertIn("profile_sticker.js", editor)
        self.assertIn("getUserMedia", (APP / "static/profile_sticker.js").read_text())

    def test_existing_sticker_is_shared_readonly_on_foreign_profile(self):
        self.post(display_name="SHOWCASE")
        with self.client.session_transaction() as session:
            session["user_id"] = 2
        html = self.client.get("/profil/fixture_user_1").get_data(as_text=True)
        self.assertIn('data-profile-sticker-era="70s"', html)
        self.assertIn("SHOWCASE", html)
        self.assertNotIn("Sticker bearbeiten", html)
        self.assertNotIn("Sticker erstellen", html)
        self.assertNotIn('class="collector-showcase-settings"', html)

    def test_persistence_country_club_color_crop_and_empty_club(self):
        response = self.post(
            display_name="MAX MUSTERMANN", country_code="NL", club_name="Borussia Dortmund",
            accent_color="yellow", crop_x="12", crop_y="-7", crop_zoom="1.42",
        )
        self.assertEqual(302, response.status_code)
        html = self.client.get("/profil").get_data(as_text=True)
        for value in ("MAX MUSTERMANN", "NIEDERLANDE", "BORUSSIA DORTMUND", "#F2C84B"):
            self.assertIn(value, html)
        self.assertIn("--crop-x:12.0%", html)
        self.post(display_name="MAX", club_name="")
        html = self.client.get("/profil").get_data(as_text=True)
        self.assertIn('profile-sticker-club is-empty', html)
        self.assertNotIn("TESTVEREIN", html)

    def test_country_and_color_contracts_are_curated_and_validated(self):
        self.assertEqual(("#171717", "#D22630", "#F4C430"), PROFILE_STICKER_COUNTRIES["DE"].flag_bands)
        self.assertEqual(("#AE1C28", "#FFFFFF", "#21468B"), PROFILE_STICKER_COUNTRIES["NL"].flag_bands)
        self.assertEqual(("#0055A4", "#FFFFFF", "#EF4135"), PROFILE_STICKER_COUNTRIES["FR"].flag_bands)
        self.assertEqual("dark", PROFILE_STICKER_COLORS["cream"].contrast)
        self.assertEqual("light", PROFILE_STICKER_COLORS["black"].contrast)
        with self.assertRaises(ProfileStickerValidationError):
            validate_settings("Max", "US", "", "purple", 0, 0, 1)
        with self.assertRaises(ProfileStickerValidationError):
            validate_settings("Max", "DE", "", "pink", 0, 0, 1)
        with self.assertRaises(ProfileStickerValidationError):
            validate_settings("Max", "DE", "", "purple", 36, 0, 1)
        self.assertEqual(400, self.post(country_code="US").status_code)

    def test_all_countries_share_three_diagonal_bands_and_two_separators(self):
        expected = {
            "DE": ("#171717", "#D22630", "#F4C430"),
            "NL": ("#AE1C28", "#FFFFFF", "#21468B"),
            "FR": ("#0055A4", "#FFFFFF", "#EF4135"),
            "IT": ("#009246", "#FFFFFF", "#CE2B37"),
            "BE": ("#171717", "#F9D616", "#EF3340"),
            "IE": ("#169B62", "#FFFFFF", "#FF883E"),
            "RO": ("#002B7F", "#FCD116", "#CE1126"),
            "AT": ("#ED2939", "#FFFFFF", "#ED2939"),
            "ES": ("#AA151B", "#F1BF00", "#AA151B"),
            "AR": ("#5DA9D6", "#FFFFFF", "#5DA9D6"),
            "EG": ("#CE1126", "#FFFFFF", "#171717"),
            "HU": ("#CE2939", "#FFFFFF", "#477050"),
            "BG": ("#FFFFFF", "#00966E", "#D62612"),
            "LU": ("#EF3340", "#FFFFFF", "#5DA9D6"),
            "RU": ("#FFFFFF", "#0039A6", "#D52B1E"),
            "CO": ("#FCD116", "#003893", "#CE1126"),
            "MX": ("#006847", "#FFFFFF", "#CE1126"),
            "PE": ("#D91023", "#FFFFFF", "#D91023"),
            "TH": ("#A51931", "#FFFFFF", "#2D2A4A"),
        }
        self.assertEqual(19, len(PROFILE_STICKER_COUNTRIES))
        self.assertEqual("#5DA9D6", PROFILE_STICKER_NATION_LIGHT_BLUE)
        geometries = set()
        for country_code, colors in expected.items():
            settings = validate_settings("VALENTIN", country_code, "VfL Osnabrück", "purple", 0, 0, 1)
            self.post(
                display_name=settings[0], country_code=settings[1], club_name=settings[2],
                accent_color=settings[3], crop_x=settings[4], crop_y=settings[5], crop_zoom=settings[6],
            )
            html = self.client.get("/profil").get_data(as_text=True)
            parser = StickerMarkupParser()
            parser.feed(html)
            self.assertEqual([f"--nation-band:{color}" for color in colors], parser.nation_colors)
            self.assertEqual(2, parser.nation_separators)
            geometries.add(tuple(
                value.split('d="', 1)[1].split('"', 1)[0]
                for value in html.split("profile-sticker-nation-")[1:]
                if ' d="' in value
            ))
            self.assertIn("--sticker-accent:#6F35A5", html)
        self.assertEqual(1, len(geometries))

    def test_all_nineteen_country_options_and_german_labels_are_rendered(self):
        expected_labels = {
            "DE": "DEUTSCHLAND", "NL": "NIEDERLANDE", "FR": "FRANKREICH",
            "IT": "ITALIEN", "BE": "BELGIEN", "IE": "IRLAND", "RO": "RUMÄNIEN",
            "AT": "ÖSTERREICH", "ES": "SPANIEN", "AR": "ARGENTINIEN",
            "EG": "ÄGYPTEN", "HU": "UNGARN", "BG": "BULGARIEN",
            "LU": "LUXEMBURG", "RU": "RUSSLAND", "CO": "KOLUMBIEN",
            "MX": "MEXIKO", "PE": "PERU", "TH": "THAILAND",
        }
        self.assertEqual(expected_labels, {
            code: country.label for code, country in PROFILE_STICKER_COUNTRIES.items()
        })
        editor = self.client.get("/profil/sticker/bearbeiten").get_data(as_text=True)
        for code, label in expected_labels.items():
            self.assertIn(f'<option value="{code}"', editor)
            self.assertIn(label.title(), editor)

    def test_country_constraint_migration_preserves_rows_and_accepts_only_catalog(self):
        with tempfile.TemporaryDirectory(prefix="sammlr-profile-country-migration-") as directory:
            database = Path(directory) / "migration.db"
            shutil.copy2(REFERENCE_DB, database)
            with sqlite3.connect(database) as connection:
                connection.execute("PRAGMA foreign_keys=ON")
                migrate(connection, 19)
                old_codes = ("DE", "NL", "FR", "IT", "BE", "IE", "RO")
                for user_id, code in enumerate(old_codes, 1):
                    if user_id > 3:
                        connection.execute(
                            "INSERT INTO users (id, username, password, name) VALUES (?, ?, 'x', ?)",
                            (user_id, f"country_fixture_{user_id}", f"Country Fixture {user_id}"),
                        )
                    connection.execute(
                        "INSERT INTO user_profile_stickers (user_id, display_name, country_code) VALUES (?, ?, ?)",
                        (user_id, f"PROFILE {user_id}", code),
                    )
                before = connection.execute(
                    "SELECT * FROM user_profile_stickers ORDER BY user_id"
                ).fetchall()
                self.assertEqual((20,), migrate(connection, 20))
                after = connection.execute(
                    "SELECT * FROM user_profile_stickers ORDER BY user_id"
                ).fetchall()
                self.assertEqual(before, after)
                for code in PROFILE_STICKER_COUNTRIES:
                    connection.execute(
                        "UPDATE user_profile_stickers SET country_code=? WHERE user_id=1", (code,)
                    )
                    self.assertEqual(code, connection.execute(
                        "SELECT country_code FROM user_profile_stickers WHERE user_id=1"
                    ).fetchone()[0])
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        "UPDATE user_profile_stickers SET country_code='XX' WHERE user_id=1"
                    )
                self.assertEqual("ok", connection.execute("PRAGMA integrity_check").fetchone()[0])
                self.assertEqual([], connection.execute("PRAGMA foreign_key_check").fetchall())

    def test_photo_surface_meets_info_line_without_cream_interstitial(self):
        css = (APP / "static/profile_sticker.css").read_text()
        self.assertIn("inset:0 0 calc(25% - 1px)", css)
        self.assertIn("height:25%", css)
        self.assertIn("bottom:25%", css)
        self.assertNotIn("inset:0 0 30%", css)

    def test_final_series_mark_is_a_local_transparent_png_without_text_glyph_fallback(self):
        self.post()
        html = self.client.get("/profil").get_data(as_text=True)
        parser = StickerMarkupParser()
        parser.feed(html)
        self.assertEqual(1, len(parser.series_marks))
        self.assertEqual("/static/profile-sticker/sammlr-70-signet-final.png", parser.series_marks[0]["src"])
        self.assertNotIn('class="profile-sticker-s"', html)
        asset = (APP / "static/profile-sticker/sammlr-70-signet-final.png").read_bytes()
        self.assertEqual(b"\x89PNG\r\n\x1a\n", asset[:8])
        self.assertEqual(6, asset[25])

    def test_upload_is_magic_validated_randomly_stored_and_owner_only(self):
        response = self.post(
            display_name="FOTO", portrait=(io.BytesIO(PNG), "portrait.exe"),
            crop_x="3", crop_y="4", crop_zoom="1.2",
        )
        self.assertEqual(302, response.status_code)
        with sqlite3.connect(self.database) as connection:
            filename = connection.execute(
                "SELECT portrait_filename FROM user_profile_stickers WHERE user_id=1"
            ).fetchone()[0]
        self.assertRegex(filename, r"^[a-f0-9]{32}\.png$")
        self.assertTrue((self.portraits / filename).is_file())
        self.assertEqual(200, self.client.get(f"/profil/sticker/portrait/{filename}").status_code)
        with self.client.session_transaction() as session:
            session["user_id"] = 2
        self.assertEqual(404, self.client.get(f"/profil/sticker/portrait/{filename}").status_code)
        self.assertEqual(200, self.client.get(
            f"/profil/fixture_user_1/sticker/portrait/{filename}"
        ).status_code)
        with sqlite3.connect(self.database) as connection:
            connection.execute(
                "UPDATE users SET profile_privacy='private' WHERE id=1"
            )
        self.assertEqual(404, self.client.get(
            f"/profil/fixture_user_1/sticker/portrait/{filename}"
        ).status_code)
        self.assertEqual(400, self.post(portrait=(io.BytesIO(b"not an image"), "fake.jpg")).status_code)
        with self.assertRaises(ProfileStickerValidationError):
            inspect_portrait(b"x" * (900 * 1024 + 1))

    def test_auth_and_csrf_guard_editor_mutation(self):
        with self.client.session_transaction() as session:
            session.clear()
        self.assertEqual(302, self.client.get("/profil/sticker/bearbeiten").status_code)
        with self.client.session_transaction() as session:
            session["user_id"] = 1
        response = self.client.post(
            "/profil/sticker/bearbeiten",
            data={"display_name": "NOPE"},
            csrf_protect=False,
        )
        self.assertEqual(403, response.status_code)
        with sqlite3.connect(self.database) as connection:
            self.assertIsNone(connection.execute("SELECT 1 FROM user_profile_stickers").fetchone())

    def test_long_name_has_deterministic_fit_class(self):
        self.post(display_name="MAXIMILIAN ALEXANDER MUSTER")
        html = self.client.get("/profil").get_data(as_text=True)
        self.assertIn("profile-sticker-70 is-extra-long", html)
        css = (APP / "static/profile_sticker.css").read_text()
        self.assertIn("white-space:nowrap", css)
        self.assertIn("overflow:hidden", css)


if __name__ == "__main__":
    unittest.main()
