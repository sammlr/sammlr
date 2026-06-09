import sqlite3
import os
from flask import Flask, request, redirect, session
import json
from em24_data import build_em24
from wm26_data import build_wm26
from services.notifications import create_notification, unread_notifications
from urllib.parse import quote

app = Flask(__name__)
app.secret_key = "sammlr_dev_secret"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "Database", "collectr.db")


def current_user_id():
    return session.get("user_id", 1)


def get_db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


@app.before_request
def require_login():
    public_endpoints = {"login", "register", "static"}

    if request.endpoint in public_endpoints:
        return None

    if "user_id" not in session:
        return redirect("/login")

    return None





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

    cur.execute("""
    INSERT OR IGNORE INTO users (id, username, password)
    VALUES (1, 'valentin', '1234')
    """)
    cur.execute("""
    INSERT OR IGNORE INTO albums (id, name, season, total, complete, cover)
    VALUES ('wm26', 'FIFA World Cup 2026', '2026', 991, 991, '🌍')
    """)

    cur.execute("""
    INSERT OR IGNORE INTO user_albums (user_id, album_id)
    SELECT 1, id FROM albums
    WHERE id IN ('em24', 'vfl')
    """)

    con.commit()
    con.close()


def style():
    return '<meta name="viewport" content="width=device-width, initial-scale=1.0"><link rel="stylesheet" href="/static/style.css">'


def app_header(active_title=None, subtitle=None):
    title_html = f"<h1>{active_title}</h1>" if active_title else ""
    subtitle_html = f'<p>{subtitle}</p>' if subtitle else ""

    return f"""
    <header class="app-header">
        <a class="app-header-brand" href="/">
            <span class="app-header-mark">S</span>
            <span>Sammlr</span>
        </a>
        {title_html}
        {subtitle_html}
    </header>
    """


from services.albums import (
    compact,
    display_code,
    em_map,
    resolve_code,
    all_codes
)

def lade_album(album_id):
    con = get_db()
    album = con.execute("SELECT * FROM albums WHERE id=?", (album_id,)).fetchone()
    sticker = con.execute(
        "SELECT * FROM stickers WHERE user_id=? AND album_id=?",
        (current_user_id(), album_id)
    ).fetchall()
    con.close()

    by_code = {s["sticker_code"]: s for s in sticker}
    gesammelt = 0
    doppelte = 0
    if album_id == "em24":
        total = len(build_em24())
    elif album_id == "wm26":
        total = len(build_wm26())
    else:
        total = album["total"]

    for code in all_codes(album_id):
        q = by_code[code]["quantity"] if code in by_code else 0
        if q > 0:
            gesammelt += 1
        if q > 1:
            doppelte += q - 1

    prozent = int((gesammelt / total) * 100)
    return album, by_code, gesammelt, doppelte, prozent, total


def klasse_und_text(code, by_code):
    q = by_code[code]["quantity"] if code in by_code else 0
    if q == 0:
        return "missing", display_code(code)
    if q == 1:
        return "owned", display_code(code)
    return "duplicate", f"{display_code(code)}<br>{q}x"


def filter_ok(filter_name, code, by_code):
    q = by_code[code]["quantity"] if code in by_code else 0
    if filter_name == "missing":
        return q == 0
    if filter_name == "owned":
        return q >= 1
    if filter_name == "duplicate":
        return q >= 2
    return True


def vfl_trophaeen():
    return [
        (25, "Anfänger"),
        (50, "Schulhof-Tauscher"),
        (75, "Stickerjäger"),
        (125, "Halbzeit"),
        (150, "Experte"),
        (200, "Sammelstratege"),
        (250, "Album vollendet")
    ]
def em24_trophaeen(total):
    halbzeit = total // 2

    return [
        (100, "Erste Packs"),
        (200, "Sammeltalent"),
        (halbzeit, "Halbzeit"),
        (500, "Lückenfüller"),
        (600, "Fast komplett"),
        (700, "Die letzten Sticker"),
        (total, "EURO 2024 vollendet"),
    ]


# --- Generische Album-Trophäen für beliebige Alben ---
def generische_album_trophaeen(total):
    halbzeit = total // 2

    return [
        (1, "Erster Sticker"),
        (halbzeit, "Halbzeit"),
        (max(total - 10, 1), "Endspurt"),
        (total, "Album vollendet"),
    ]

    trophies = []

    for ziel in range(100, total + 1, 100):
        name = freche_100er_namen[((ziel // 100) - 1) % len(freche_100er_namen)]
        trophies.append((ziel, f"{name} ({ziel})"))

    halbzeit = total // 2
    trophies.append((halbzeit, "Halbzeit-Held"))

    if total > 15:
        trophies.append((total - 15, "Endspurt-Energie"))

    if total > 3:
        trophies.append((total - 3, "Letzte-Drei-Legende"))

    trophies.append((total, "Album vollendet"))

    unique = {}
    for ziel, titel in trophies:
        if ziel > 0 and ziel <= total:
            unique[ziel] = titel

    return sorted(unique.items(), key=lambda item: item[0])

def album_doppelte_trophaeen():
    return []


# --- Trophy helper functions for nearest/next ---
def nearest_album_trophy(album_id):
    album, by_code, gesammelt, doppelte, prozent, total = lade_album(album_id)
    last, next_trophy, trophies = trophy_status(album_id, gesammelt, total)

    candidates = []

    for ziel, titel in trophies:
        if gesammelt < ziel:
            candidates.append({
                "title": titel,
                "distance": ziel - gesammelt,
                "text": f"Noch {ziel - gesammelt} Sticker sammeln",
                "category": "Album-Trophäe"
            })


    if not candidates:
        return {
            "title": "Alle Albumziele erreicht",
            "distance": 0,
            "text": "Für dieses Album ist gerade alles abgestaubt.",
            "category": "Vollendet"
        }

    return sorted(candidates, key=lambda item: item["distance"])[0]


def global_trade_trophaeen():
    return [
        (1, "Erster Wechsel"),
        (5, "Transfertelefon"),
        (10, "Handschlag-Dealer"),
        (25, "Transferexpress"),
        (50, "Deadline-Day-Profi"),
        (100, "Sportdirektor"),
    ]


def global_sticker_trophaeen():
    return [
        (100, "100 gesammelte Sticker"),
        (200, "200 gesammelte Sticker"),
        (300, "300 gesammelte Sticker"),
        (500, "500 gesammelte Sticker"),
        (750, "750 gesammelte Sticker"),
        (1000, "1000 gesammelte Sticker"),
        (1500, "1500 gesammelte Sticker"),
        (2000, "2000 gesammelte Sticker"),
        (3000, "3000 gesammelte Sticker"),
        (5000, "5000 gesammelte Sticker"),
        (10000, "10000 gesammelte Sticker"),
    ]


def global_duplicate_trophaeen():
    return [
        (1, "Erster doppelter Sticker"),
        (25, "25 doppelte Sticker"),
        (50, "50 doppelte Sticker"),
        (100, "100 doppelte Sticker"),
        (250, "250 doppelte Sticker"),
        (500, "500 doppelte Sticker"),
        (1000, "1000 doppelte Sticker"),
        (2500, "2500 doppelte Sticker"),
        (5000, "5000 doppelte Sticker"),
    ]


# Helper to render trophy steps (for future use)
def render_trophy_steps(trophies, current_value, color_class, unit_text):
    html = ""
    locked_seen = 0

    for ziel, titel in trophies:
        erreicht = current_value >= ziel
        if erreicht:
            beschreibung = f"{ziel} / {ziel} {unit_text}"
        else:
            beschreibung = f"{current_value} / {ziel} {unit_text}"

        if erreicht:
            html += f"""
            <div class="trophy trophy-unlocked {color_class}">
                <span class="trophy-pill {color_class}">Abgestaubt</span>
                <h2>{titel}</h2>
                <p>{beschreibung}</p>
            </div>
            """
        else:
            locked_seen += 1

            if locked_seen == 1:
                html += f"""
                <div class="trophy trophy-locked">
                    <span class="trophy-pill gray">Nächstes Ziel</span>
                    <h2>{titel}</h2>
                    <p>{beschreibung}</p>
                </div>
                """
            elif locked_seen == 2:
                html += f"""
                <div class="trophy trophy-secret">
                    <span class="trophy-pill gray">Danach</span>
                    <h2><span class="trophy-blurred-title">{titel}</span></h2>
                    <p>{beschreibung}</p>
                </div>
                """
                break

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


def wm26_trophy_progress(title, description, codes, by_code):
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
    }


def wm26_album_trophy_progress(title, description, current, target):
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
    }


def wm26_trophy_items(by_code, gesammelt, total):
    intro_codes = [f"FWC{i}" for i in range(1, 9)]
    history_codes = [f"FWC{i}" for i in range(9, 20)]
    cc_codes = [f"CC{i}" for i in range(1, 13)]
    wappen_codes = [team + "1" for team in WM26_TEAM_ORDER]
    teamfoto_codes = [team + "13" for team in WM26_TEAM_ORDER]
    last_dance_codes = ["ARG20", "POR20"]

    items = [
        wm26_album_trophy_progress("Erster Sticker", "Sammle deinen ersten Sticker in diesem Album.", gesammelt, 1),
        wm26_trophy_progress("Intro", "Sammle alle World-Cup-Intro-Sticker FWC1 bis FWC8.", intro_codes, by_code),
        wm26_trophy_progress("Wappenkunde", "Sammle alle Nummer-1-Sticker der Teams.", wappen_codes, by_code),
        wm26_trophy_progress("Teamfotograf", "Sammle alle Teamfotos, also alle Nummer-13-Sticker.", teamfoto_codes, by_code),
    ]

    for group_index, group_name in enumerate(WM26_GROUP_NAMES):
        group_teams = WM26_TEAM_ORDER[group_index * 4:(group_index + 1) * 4]
        group_codes = []
        for team in group_teams:
            group_codes.extend([f"{team}{i}" for i in range(1, 21)])

        items.append(
            wm26_trophy_progress(
                f"{group_name} gemeistert",
                f"Sammle alle Sticker aus {group_name}.",
                group_codes,
                by_code
            )
        )

    items.extend([
        wm26_trophy_progress("Historiker", "Sammle alle World-Cup-History-Sticker FWC9 bis FWC19.", history_codes, by_code),
        wm26_trophy_progress("Etikettenknibbler", "Sammle alle Coca-Cola-Sticker CC1 bis CC12.", cc_codes, by_code),
        wm26_trophy_progress("Last Dance", "Sammle Messi und Ronaldo.", last_dance_codes, by_code),
        wm26_album_trophy_progress("Halbzeit", "Erreiche die Hälfte dieses Albums.", gesammelt, total // 2),
        wm26_album_trophy_progress("Endspurt", "Dir fehlen nur noch 10 Sticker bis zur Vollendung.", gesammelt, max(total - 10, 1)),
        wm26_album_trophy_progress("WM 2026 vollendet", "Sammle alle Sticker dieses Albums.", gesammelt, total),
    ])

    return items


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
    album, by_code, gesammelt, doppelte, prozent, total = lade_album(album_id)
    last, next_trophy, trophies = trophy_status(album_id, gesammelt, total)

    erreicht = [titel for ziel, titel in trophies if gesammelt >= ziel]

    if album_id == "em24":
        for titel, beschreibung, ok in em24_spezial_trophaeen(by_code):
            if ok:
                erreicht.append(titel)

    if album_id == "wm26":
        for item in wm26_trophy_items(by_code, gesammelt, total):
            if item["unlocked"]:
                erreicht.append(item["title"])

    return list(dict.fromkeys(erreicht))


def trophy_status(album_id, gesammelt, total):
    if album_id == "vfl":
        trophies = vfl_trophaeen()
    elif album_id == "em24":
        trophies = em24_trophaeen(total)
    else:
        trophies = generische_album_trophaeen(total)

    reached = [t for t in trophies if gesammelt >= t[0]]
    next_one = next((t for t in trophies if gesammelt < t[0]), None)

    last = reached[-1][1] if reached else "Noch keine Auszeichnung"
    nxt = f"{next_one[1]} bei {next_one[0]} Stickern" if next_one else "Alle Trophäen erhalten"

    return last, nxt, trophies

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET" and "user_id" in session:
        return redirect("/")

    error = ""

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        con = get_db()
        user = con.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        con.close()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/")

        error = "Login fehlgeschlagen. Bitte prüfe Benutzername und Passwort."

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
        <div class="auth-watermark" aria-hidden="true">S</div>
    </div></body></html>
    """
@app.route("/register", methods=["GET", "POST"])
def register():
    error = ""

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username")
        password = request.form.get("password")
        password_repeat = request.form.get("password_repeat")

        if password != password_repeat:
            error = "Passwörter stimmen nicht überein."
        else:
            con = get_db()

            try:
                con.execute(
                    "INSERT INTO users (name, username, password) VALUES (?, ?, ?)",
                    (name, username, password)
                )
                con.commit()
                con.close()

                return redirect("/login")

            except sqlite3.IntegrityError:
                con.close()
                error = "Benutzername ist bereits vergeben."

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
        <div class="auth-watermark" aria-hidden="true">S</div>
    </div></body></html>
    """

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/")
def startseite():
    favorite_album_id = current_favorite_album_id()
    con = get_db()
    alben = con.execute(
        """
        SELECT albums.*
        FROM albums
        JOIN user_albums ON user_albums.album_id = albums.id
        WHERE user_albums.user_id=?
        """,
        (current_user_id(),)
    ).fetchall()
    con.close()

    infos = []
    for album in alben:
        _, _, gesammelt, doppelte, prozent, total = lade_album(album["id"])
        tauschbare_luecken = tauschbare_luecken_count(album["id"])
        infos.append((album, gesammelt, doppelte, prozent, total, tauschbare_luecken))

    html = f"""
    <html><head>{style()}</head><body><div class="container">

    {app_header("Sammlr Zentrale", "Deine Alben, Fortschritte und nächsten Sammelziele.")}

    <div class="home-section-toolbar">
        <h2 class="home-section-title">Aktive Alben</h2>
        <a class="add-album-button" href="/alben/hinzufuegen"><span>+</span> Album hinzufügen</a>
    </div>
    """

    for album, gesammelt, doppelte, prozent, total, tauschbare_luecken in infos:
        if prozent < 100:
            html += album_card(album, gesammelt, doppelte, prozent, total, tauschbare_luecken, is_favorite=(album["id"] == favorite_album_id))

    html += """
    <h2 class="home-section-title">Vitrine</h2>
    """

    for album, gesammelt, doppelte, prozent, total, tauschbare_luecken in infos:
        if prozent == 100:
            html += album_card(album, gesammelt, doppelte, prozent, total, tauschbare_luecken, is_favorite=(album["id"] == favorite_album_id))

    html += bottom_nav("sammlr")
    html += "</div></body></html>"
    return html
    


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


def tauschbare_luecken_count(album_id):
    con = get_db()
    meine_sticker = con.execute(
        "SELECT sticker_code, quantity FROM stickers WHERE user_id=? AND album_id=?",
        (current_user_id(), album_id)
    ).fetchall()
    andere_user = con.execute(
        """
        SELECT users.id
        FROM users
        JOIN user_albums ON user_albums.user_id = users.id
        WHERE users.id != ? AND user_albums.album_id = ?
        """,
        (current_user_id(), album_id)
    ).fetchall()

    meine_mengen = {s["sticker_code"]: s["quantity"] for s in meine_sticker}
    meine_fehlenden = {code for code in all_codes(album_id) if meine_mengen.get(code, 0) == 0}
    tauschbar = set()

    for user in andere_user:
        andere_sticker = con.execute(
            "SELECT sticker_code, quantity FROM stickers WHERE user_id=? AND album_id=?",
            (user["id"], album_id)
        ).fetchall()
        andere_doppelte = {s["sticker_code"] for s in andere_sticker if s["quantity"] >= 2}
        tauschbar.update(meine_fehlenden.intersection(andere_doppelte))

    con.close()
    return len(tauschbar)


def album_trade_preview_counts(album_id):
    con = get_db()
    meine_sticker = con.execute(
        "SELECT sticker_code, quantity FROM stickers WHERE user_id=? AND album_id=?",
        (current_user_id(), album_id)
    ).fetchall()
    andere_user = con.execute(
        """
        SELECT users.id
        FROM users
        JOIN user_albums ON user_albums.user_id = users.id
        WHERE users.id != ? AND user_albums.album_id = ?
        """,
        (current_user_id(), album_id)
    ).fetchall()

    meine_mengen = {s["sticker_code"]: s["quantity"] for s in meine_sticker}
    alle_codes = all_codes(album_id)
    meine_fehlenden = {code for code in alle_codes if meine_mengen.get(code, 0) == 0}
    meine_doppelten = {code for code in alle_codes if meine_mengen.get(code, 0) >= 2}

    market_codes = set()
    direct_partner_count = 0

    for user in andere_user:
        andere_sticker = con.execute(
            "SELECT sticker_code, quantity FROM stickers WHERE user_id=? AND album_id=?",
            (user["id"], album_id)
        ).fetchall()

        andere_mengen = {s["sticker_code"]: s["quantity"] for s in andere_sticker}
        andere_fehlenden = {code for code in alle_codes if andere_mengen.get(code, 0) == 0}
        andere_doppelten = {code for code in alle_codes if andere_mengen.get(code, 0) >= 2}

        du_bekommst = meine_fehlenden.intersection(andere_doppelten)
        du_gibst = meine_doppelten.intersection(andere_fehlenden)

        market_codes.update(du_bekommst)
        if du_bekommst and du_gibst:
            direct_partner_count += 1

    con.close()
    return len(market_codes), direct_partner_count


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
            <a class="favorite-choice-link" href="/favorit/toggle/{album['id']}">
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
            <form class="favorite-choice-form" method="POST" action="/favorit/toggle/{album['id']}">
                <button type="submit" class="favorite-set-button">{button_text}</button>
            </form>
        </div>
    """


# --- Bottom Navigation ---
def bottom_nav(active="sammlr"):
    items = [
        ("profil", "/profil", "Profil"),
        ("favorit", "/favorit", "Favorit"),
        ("sammlr", "/", "Sammlr"),
        ("trophaeen", "/trophaeen", "Trophäen"),
        ("statistik", "/statistik", "Statistik"),
    ]

    links = ""
    for key, href, label in items:
        active_class = " active" if key == active else ""
        links += f'<a class="bottom-nav-link{active_class}" href="{href}">{label}</a>'

    return f'<nav class="bottom-nav">{links}</nav>'


@app.route("/favorit")
def favorit():
    favorite_album_id = current_favorite_album_id()
    show_selection = request.args.get("auswahl") == "1"
    alben = user_album_rows()
    favorite_alben = [album for album in alben if album["id"] == favorite_album_id]

    html = f"""
    <html><head>{style()}</head><body><div class="container">
    {app_header("Favoritenalbum", "Dein schneller Zugriff auf ein Album.")}
    """

    if favorite_alben:
        html += """
        <div class="home-section-toolbar favorite-toolbar">
            <h2 class="home-section-title">Favoritenalbum</h2>
            <a class="favorite-change-button" href="/favorit?auswahl=1">+ Favorit ändern</a>
        </div>
        """
        album = favorite_alben[0]
        _, _, gesammelt, doppelte, prozent, total = lade_album(album["id"])
        html += album_card(album, gesammelt, doppelte, prozent, total, tauschbare_luecken_count(album["id"]), is_favorite=True)
    else:
        html += """
        <div class="home-section-toolbar favorite-toolbar">
            <h2 class="home-section-title">Kein Favoritenalbum ausgewählt</h2>
            <a class="favorite-change-button" href="/favorit?auswahl=1">+</a>
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
            <a class="btn" href="/">Zurück zu Alben</a>
        </div>
        """

    html += bottom_nav("favorit")
    html += "</div></body></html>"
    return html


@app.route("/favorit/toggle/<album_id>", methods=["POST", "GET"])
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


@app.route("/favorit/setzen/<album_id>", methods=["POST", "GET"])
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
    <html><head>{style()}</head><body><div class="container">
    <a class="btn" href="/">← Zurück</a>
    <h1>Album hinzufügen</h1>
    <p class="subline">Wähle ein Album aus der Sammlr-Liste.</p>
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
            <a class="btn" href="/alben/hinzufuegen/{album['id']}">Hinzufügen</a>
        </div>
        """

    html += bottom_nav("sammlr")
    html += "</div></body></html>"
    return html


@app.route("/alben/hinzufuegen/<album_id>")
def album_hinzufuegen(album_id):
    con = get_db()
    con.execute(
        "INSERT OR IGNORE INTO user_albums (user_id, album_id) VALUES (?, ?)",
        (current_user_id(), album_id)
    )
    con.commit()
    con.close()
    return redirect("/")

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

    if code.startswith("FWC"):
        number = int(code.replace("FWC", ""))
        if number <= 8:
            return (0, number)
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
    if code.startswith("FWC") or code.startswith("CC"):
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
        return f"{missing} fehlen"

    if filter_name == "duplicate":
        return f"{duplicate_extra} doppelt"

    return f"{owned}/{total}"

@app.route("/album/<album_id>", methods=["GET", "POST"])
def albumseite(album_id):
    filter_name = request.args.get("filter", "all")
    show_album = filter_name in ("all", "album")
    show_duplicates = filter_name in ("all", "duplicates")
    message = request.args.get("message", "")
    focus = request.args.get("focus", "add")
    mode = request.args.get("mode", focus)
    trophy = request.args.get("trophy", "")
    count = request.args.get("count", "1")
    anzahl = int(count)
    trigger = request.args.get("trigger", "")
    smart_prefix_active = request.args.get("smart", "") == "1"
    print("TRIGGER =", trigger)
    trophy_popup = ""

    if trophy:
        trophy_text = "Neue Trophäe freigeschaltet!" if anzahl == 1 else f"{anzahl} neue Trophäen freigeschaltet!"
        trophy_lines = trophy.replace(",", "<br>")
        trophy_popup = f"""
        <div class="trophy-popup-overlay">
            <div class="trophy-popup">
                <div class="trophy-popup-patch">🏆</div>
                <h2>Neuer Patch erhalten</h2>
                <p><strong>{trophy_text}</strong><br>{trophy_lines}</p>
                <div class="popup-actions">
                    <a href="/album/{album_id}" class="popup-button popup-secondary">Okay</a>
                    <a href="/album/{album_id}/trophaeen" class="popup-button">Trophäenschrank</a>
                </div>
            </div>
        </div>
        """

    if request.method == "POST":
        aktion = request.form.get("aktion", "add")
        current_filter = request.form.get("filter", "all")

        if aktion == "trade":
            trade_out_raw = request.form.get("trade_out", "").strip()
            trade_in_raw = request.form.get("trade_in", "").strip()

            trade_out = resolve_code(album_id, trade_out_raw) if trade_out_raw else None
            trade_in = resolve_code(album_id, trade_in_raw) if trade_in_raw else None

            if trade_out is None or trade_in is None:
                return redirect(f"/album/{album_id}?filter={current_filter}&message=Trade-Sticker%20nicht%20vorhanden.&focus=trade")

            con = get_db()
            cur = con.cursor()

            outgoing = con.execute(
                "SELECT * FROM stickers WHERE user_id=? AND album_id=? AND sticker_code=?",
                (current_user_id(), album_id, trade_out)
            ).fetchone()

            if not outgoing or outgoing["quantity"] <= 0:
                con.close()
                return redirect(f"/album/{album_id}?filter={current_filter}&message=Du%20kannst%20nur%20Sticker%20abgeben,%20die%20du%20besitzt.&focus=trade")

            neue_out_quantity = max(outgoing["quantity"] - 1, 0)
            neue_out_duplicates = max(neue_out_quantity - 1, 0)

            if neue_out_quantity == 0:
                cur.execute("DELETE FROM stickers WHERE id=?", (outgoing["id"],))
            else:
                cur.execute(
                    "UPDATE stickers SET quantity=?, duplicates=? WHERE id=?",
                    (neue_out_quantity, neue_out_duplicates, outgoing["id"])
                )

            incoming = con.execute(
                "SELECT * FROM stickers WHERE user_id=? AND album_id=? AND sticker_code=?",
                (current_user_id(), album_id, trade_in)
            ).fetchone()

            if incoming:
                neue_in_quantity = incoming["quantity"] + 1
                neue_in_duplicates = max(neue_in_quantity - 1, 0)
                cur.execute(
                    "UPDATE stickers SET quantity=?, duplicates=? WHERE id=?",
                    (neue_in_quantity, neue_in_duplicates, incoming["id"])
                )
            else:
                cur.execute(
                    """
                    INSERT INTO stickers (user_id, album_id, sticker_code, status, duplicates, quantity)
                    VALUES (?, ?, ?, "owned", 0, 1)
                    """,
                    (current_user_id(), album_id, trade_in)
                )

            con.commit()
            con.close()

            msg = f"Trade gespeichert: {display_code(trade_out)} abgegeben, {display_code(trade_in)} eingesammelt."
            return redirect(f"/album/{album_id}?filter={current_filter}&message={quote(msg)}&focus=trade")

        raw = request.form.get("sticker", "").strip()

        if raw:
            code = resolve_code(album_id, raw)

            if code is None:
                return redirect(f"/album/{album_id}?filter={current_filter}&message=Sticker%20nicht%20vorhanden.&focus={aktion}")

            if aktion == "remove":
                return redirect(f"/remove/{album_id}/{code}?filter={current_filter}")

            return redirect(f"/add/{album_id}/{code}?filter={current_filter}")

    album, by_code, gesammelt, doppelte, prozent, total = lade_album(album_id)
    market_missing_count, direct_partner_count = album_trade_preview_counts(album_id)
    trade_preview_line = (
        f"{direct_partner_count} direkte Tauschpartner"
        if direct_partner_count > 0
        else "Noch keine direkten Tauschpartner"
    )

    html = f"""
    <html><head>{style()}</head><body><div class="container">
    {app_header(album['name'], album['season'])}

    {f'<div class="notice {"notice-error" if "nicht vorhanden" in message else "notice-duplicate" if "doppelt" in message else "notice-success"}"><h2>{message}</h2><p>Vertippt?</p><a class="btn gray" href="/undo">↩ Rückgängig machen</a></div>' if message and ("hinzugefügt" in message or "doppelt" in message or "entfernt" in message) else f'<div class="notice {"notice-error" if "nicht vorhanden" in message else "notice-duplicate" if "doppelt" in message else "notice-success"}"><h2>{message}</h2></div>' if message else ''}
    <div class="album-collection-head">
        <div class="album-collection-progress">
            <div>
                <span>{gesammelt} / {total}</span>
                <strong>{prozent}%</strong>
            </div>
            <div class="progress" data-progress="{prozent}%"><div class="progress-bar" style="width:{prozent}%;"></div></div>
        </div>

        <div class="album-primary-actions">
            <button type="button" class="album-primary-action main" onclick="openQuickActions()">Sticker hinzufügen</button>
            <a class="album-primary-action" href="/album/{album_id}/trades">Tauschen</a>
        </div>
    </div>

    <a class="trade-preview-card" href="/album/{album_id}/trades">
        <div class="trade-preview-main">
            <div>
                <span class="trade-preview-title">Tauschbörse</span>
                <strong>{market_missing_count}</strong>
                <p>deiner fehlenden Sticker auf dem Markt</p>
            </div>
            <span class="trade-preview-cta">Öffnen</span>
        </div>
        <div class="trade-preview-subline">{trade_preview_line}</div>
    </a>

    <div class="card sticker-wall-card">
    <div class="sticker-wall-headline">
        <h2>Stickerwand</h2>
        <button type="button" class="smart-add-toggle" onclick="openQuickActions()">+</button>
            </div>
        <div class="sticker-filter-row">
        <a class="sticker-filter-pill {'active' if filter_name == 'all' else ''}" href="/album/{album_id}">Alle</a>
        <a class="sticker-filter-pill missing {'active' if filter_name == 'missing' else ''}" href="/album/{album_id}?filter=missing">Fehlende</a>
        <a class="sticker-filter-pill owned {'active' if filter_name == 'owned' else ''}" href="/album/{album_id}?filter=owned">Vorhandene</a>
        <a class="sticker-filter-pill duplicate {'active' if filter_name == 'duplicate' else ''}" href="/album/{album_id}?filter=duplicate">Doppelte</a>
    </div>
    <input id="stickerSearch" class="sticker-search" type="search" placeholder="Sticker oder Team suchen..." autocomplete="off">
    <div id="pendingInputError" class="pending-input-error" style="display:none;"></div>

    <p>
        
        <strong>
        {total if filter_name == "all" else doppelte if filter_name == "duplicate" else gesammelt if filter_name == "owned" else total - gesammelt}
        </strong>
        Sticker
        </p>
    """


    if album_id == "em24":
        current_section = ""
        open_wall = False

        for sticker in build_em24():
            code = sticker["id"]
            if not filter_ok(filter_name, code, by_code):
                continue

            if sticker["section"] != current_section:
                if open_wall:
                    html += "</div>"

                current_section = sticker["section"]
                html += f'<h2 class="section-title">{current_section}</h2><div class="wall">'
                open_wall = True

            klasse, text = klasse_und_text(code, by_code)
            if trigger and compact(code) == compact(trigger):
                klasse += " trigger-slot"
            search_text = f"{code} {text} {current_section}".lower()
            html += f'<a class="slot {klasse}" data-code="{code}" data-display="{display_code(code)}" data-search="{search_text}" href="/sticker/{album_id}/{code}">{text}</a>'
        if open_wall:
            html += "</div>"

    elif album_id == "wm26":
        current_chapter = ""
        current_team = ""
        open_wall = False

        wm26_stickers = sorted(build_wm26(), key=wm26_wall_order)
        chapter_codes = {}
        team_codes = {}

        for counter_sticker in wm26_stickers:
            counter_code = counter_sticker["id"]
            counter_chapter = wm26_chapter_for_wall(counter_sticker)
            counter_team = wm26_team_for_wall(counter_sticker)

            chapter_codes.setdefault(counter_chapter, []).append(counter_code)
            if counter_team:
                team_codes.setdefault(counter_team, []).append(counter_code)

        for sticker in wm26_stickers:
            code = sticker["id"]
            if not filter_ok(filter_name, code, by_code):
                continue

            chapter = wm26_chapter_for_wall(sticker)
            team_name = wm26_team_for_wall(sticker)

            if chapter != current_chapter:
                if open_wall:
                    html += "</div>"
                    open_wall = False

                current_chapter = chapter
                current_team = ""
                chapter_id = "chapter-" + current_chapter.lower().replace(" ", "-").replace("/", "-")
                chapter_counter = sticker_counter_label(chapter_codes[current_chapter], by_code, filter_name)
                html += f'<h2 id="{chapter_id}" class="section-title album-chapter-title"><span>{current_chapter}</span><span>{chapter_counter}</span></h2>'

            if team_name and team_name != current_team:
                if open_wall:
                    html += "</div>"
                    open_wall = False

                current_team = team_name
                team_id = "team-" + current_team.lower().replace(" ", "-").replace("/", "-")
                team_counter = sticker_counter_label(team_codes[current_team], by_code, filter_name)
                html += f'<h3 id="{team_id}" class="team-title"><span>{current_team}</span><span>{team_counter}</span></h3>'
            if not open_wall:
                html += '<div class="wall">'
                open_wall = True

            klasse, text = klasse_und_text(code, by_code)
            if trigger and compact(code) == compact(trigger):
                klasse += " trigger-slot"
            search_text = f"{code} {text} {current_chapter} {current_team}".lower()
            html += f'<a class="slot {klasse}" data-code="{code}" data-display="{display_code(code)}" data-search="{search_text}" href="/sticker/{album_id}/{code}">{text}</a>'

        if open_wall:
            html += "</div>"

    else:
        html += '<div class="wall">'
        for code in all_codes(album_id):
            if not filter_ok(filter_name, code, by_code):
                continue
            klasse, text = klasse_und_text(code, by_code)
            if trigger and compact(code) == compact(trigger):
                klasse += " trigger-slot"
            search_text = f"{code} {text}".lower()
            html += f'<a class="slot {klasse}" data-code="{code}" data-display="{display_code(code)}" data-search="{search_text}" href="/sticker/{album_id}/{code}">{text}</a>'
        html += "</div>"
    html += f'''
<div class="quick-action-modal" id="quickActionModal" style="display:none;">
    <div class="quick-action-card">
        <div id="quickActionStep1">
            <h3>Sticker verwalten</h3>
            <button type="button" class="btn green" onclick="chooseAction('add')">Sticker hinzufügen</button>
            <button type="button" class="btn gray" onclick="chooseAction('remove')">Sticker entfernen</button>
            <button type="button" class="btn gray" onclick="closeQuickActions()">Abbrechen</button>
        </div>

        <div id="quickActionStep2" style="display:none;">
            <h3 id="quickActionTitle">Sticker hinzufügen</h3>
            <button type="button" class="btn" onclick="chooseMode('input')">Sticker eintragen</button>
            <button type="button" class="btn" onclick="chooseMode('select')">Sticker auswählen</button>
            <button type="button" class="btn gray" onclick="closeQuickActions()">Abbrechen</button>
        </div>
    </div>
</div>
<div class="smart-add-bar" id="smartAddBar" style="display:none;">
    <div class="smart-add-count">
        <strong id="smartAddCount">0</strong> <span id="smartAddLabel">Sticker ausgewählt</span>
    </div>
    <div class="smart-add-actions">
        <button type="button" class="smart-add-secondary" onclick="cancelSmartAdd()">Abbrechen</button>
        <button type="button" class="smart-add-primary" id="smartAddPrimary" onclick="submitSmartAdd()">Auswahl prüfen</button>
    </div>
</div>
<div class="quick-action-modal review-modal" id="pendingReviewModal" style="display:none;">
    <div class="quick-action-card review-card">
        <h3 id="pendingReviewTitle">Auswahl prüfen</h3>
        <div class="pending-review-list" id="pendingReviewList"></div>
        <div class="pending-review-actions">
            <button type="button" class="btn gray" onclick="closePendingReview()">Bearbeiten</button>
            <button type="button" class="btn" onclick="confirmSmartAdd('add')">Hinzufügen</button>
            <button type="button" class="btn gray" onclick="confirmSmartAdd('remove')">Entfernen</button>
        </div>
    </div>
</div>

<script>
let smartAddMode = false;
let selectedStickers = [];
let smartActionMode = null;
let keyboardInputMode = false;

const stickerSearchInput = document.getElementById('stickerSearch');

function resetStickerSearch(){{
    if(!stickerSearchInput) return;

    stickerSearchInput.value = '';
    stickerSearchInput.placeholder = 'Sticker oder Team suchen...';
    stickerSearchInput.type = 'search';

    document.querySelectorAll('.slot').forEach(function(slot){{
        slot.style.display = '';
    }});

    updateVisibleStickerSections();
}}

function clearStickerFilter(){{
    document.querySelectorAll('.slot').forEach(function(slot){{
        slot.style.display = '';
    }});

    updateVisibleStickerSections();
}}

function getPendingCounts(){{
    const counts = {{}};

    selectedStickers.forEach(function(code){{
        counts[code] = (counts[code] || 0) + 1;
    }});

    return counts;
}}

function normalize(value){{
    return String(value || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
}}

function normalizeStickerToken(value){{
    return normalize(value).toLowerCase();
}}

function getCodeNumber(code){{
    const match = normalize(code).match(/(\\d+)$/);
    return match ? match[1] : '';
}}

function isOnlyNumber(term){{
    return /^\\d+$/.test(term);
}}

function hasLettersAndNumbers(term){{
    return /[A-Z]/.test(term) && /\\d/.test(term);
}}

function slotMatchesSearch(slot, term){{
    const rawTerm = String(term || '').trim();
    if(!rawTerm) return true;

    const code = slot.dataset.code || '';
    const display = slot.dataset.display || '';
    const search = slot.dataset.search || slot.textContent || '';

    const normalizedTerm = normalize(rawTerm);
    const normalizedCode = normalize(code);
    const normalizedDisplay = normalize(display);

    const queryIsOnlyNumber = /^\d+$/.test(normalizedTerm);
    const queryHasLetters = /[A-Z]/.test(normalizedTerm);
    const queryHasNumbers = /\d/.test(normalizedTerm);

    // Exact code/number checks must run before fuzzy data-search,
    // otherwise terms like "mex2" also match the MEX team text.
    if(queryIsOnlyNumber){{
        return getCodeNumber(code) === normalizedTerm || getCodeNumber(display) === normalizedTerm;
    }}

    if(queryHasLetters && queryHasNumbers){{
        return normalizedCode === normalizedTerm || normalizedDisplay === normalizedTerm;
    }}

    return search.toLowerCase().includes(rawTerm.toLowerCase());
}}

function findSlotByCode(code){{
    let foundSlot = null;
    const needle = normalizeStickerToken(code);
    if(!needle) return null;

    document.querySelectorAll('.slot').forEach(function(slot){{
        const codeKey = normalizeStickerToken(slot.dataset.code || '');
        const displayKey = normalizeStickerToken(slot.dataset.display || '');

        if(!foundSlot && (codeKey === needle || displayKey === needle)){{
            foundSlot = slot;
        }}
    }});

    return foundSlot;
}}

function canonicalCodeFromInput(rawCode){{
    const slot = findSlotByCode(rawCode);
    return slot ? (slot.dataset.code || rawCode) : null;
}}

function displayCodeForPending(code){{
    const slot = findSlotByCode(code);
    return slot ? (slot.dataset.display || code) : code;
}}

function updatePendingSlotBadges(){{
    const counts = getPendingCounts();

    document.querySelectorAll('.slot').forEach(function(slot){{
        const code = slot.dataset.code || '';
        const count = counts[code] || 0;

        slot.dataset.pendingCount = count > 0 ? count : '';
        if(count > 0){{
            slot.classList.add('smart-selected');
        }}else{{
            slot.classList.remove('smart-selected');
        }}
    }});
}}

function syncPendingUi(){{
    updatePendingSlotBadges();
    updateSmartAddBar();
    renderPendingReview();
}}

function setPendingCount(code, amount){{
    const nextAmount = Math.max(parseInt(amount, 10) || 0, 0);
    const remaining = selectedStickers.filter(function(item){{
        return item !== code;
    }});

    for(let i = 0; i < nextAmount; i += 1){{
        remaining.push(code);
    }}

    selectedStickers = remaining;
    syncPendingUi();
}}

function incrementPendingCode(code){{
    selectedStickers.push(code);
    syncPendingUi();
}}

function decrementPendingCode(code){{
    const index = selectedStickers.indexOf(code);
    if(index >= 0){{
        selectedStickers.splice(index, 1);
    }}

    syncPendingUi();
}}

function removePendingCode(code){{
    selectedStickers = selectedStickers.filter(function(item){{
        return item !== code;
    }});

    syncPendingUi();
}}

function showPendingInputError(message){{
    const error = document.getElementById('pendingInputError');
    if(!error) return;

    error.textContent = message;
    error.style.display = 'block';
}}

function clearPendingInputError(){{
    const error = document.getElementById('pendingInputError');
    if(!error) return;

    error.textContent = '';
    error.style.display = 'none';
}}

function updateVisibleStickerSections(){{
    document.querySelectorAll('.team-title').forEach(function(teamTitle){{
        let node = teamTitle.nextElementSibling;
        let hasVisibleSlot = false;

        while(node && !node.classList.contains('team-title') && !node.classList.contains('album-chapter-title')){{
            if(node.classList.contains('wall')){{
                node.querySelectorAll('.slot').forEach(function(slot){{
                    if(slot.style.display !== 'none'){{
                        hasVisibleSlot = true;
                    }}
                }});
            }}
            node = node.nextElementSibling;
        }}

        teamTitle.style.display = hasVisibleSlot ? '' : 'none';
    }});

    document.querySelectorAll('.album-chapter-title').forEach(function(chapterTitle){{
        let node = chapterTitle.nextElementSibling;
        let hasVisibleSlot = false;

        while(node && !node.classList.contains('album-chapter-title')){{
            if(node.classList.contains('wall')){{
                node.querySelectorAll('.slot').forEach(function(slot){{
                    if(slot.style.display !== 'none'){{
                        hasVisibleSlot = true;
                    }}
                }});
            }}
            node = node.nextElementSibling;
        }}

        chapterTitle.style.display = hasVisibleSlot ? '' : 'none';
    }});

    document.querySelectorAll('.wall').forEach(function(wall){{
        let hasVisibleSlot = false;

        wall.querySelectorAll('.slot').forEach(function(slot){{
            if(slot.style.display !== 'none'){{
                hasVisibleSlot = true;
            }}
        }});

        wall.style.display = hasVisibleSlot ? 'grid' : 'none';
    }});
}}


if(stickerSearchInput){{
    stickerSearchInput.addEventListener('input', function(){{
        const term = this.value.trim();
        const slots = Array.from(document.querySelectorAll('.slot'));

        slots.forEach(function(slot){{
            const isMatch = slotMatchesSearch(slot, term);
            slot.style.display = isMatch ? '' : 'none';
        }});

        updateVisibleStickerSections();
    }});

    stickerSearchInput.addEventListener('keydown', function(event){{
        if(!smartAddMode) return;

        if(event.key === 'Enter'){{
            event.preventDefault();

            const code = stickerSearchInput.value.trim();
            if(!code) return;

            const canonicalCode = canonicalCodeFromInput(code);
            if(!canonicalCode){{
                showPendingInputError('Sticker nicht gefunden: ' + code);
                stickerSearchInput.value = '';
                clearStickerFilter();
                stickerSearchInput.focus();
                return;
            }}

            incrementPendingCode(canonicalCode);
            stickerSearchInput.value = '';
            clearStickerFilter();
            clearPendingInputError();
        }}

        if(event.key === 'Escape'){{
            cancelSmartAdd();
        }}
    }});
}}

function openQuickActions(){{
    startNeutralPendingMode();
}}

function closeQuickActions(){{
    const modal = document.getElementById('quickActionModal');
    if(modal) modal.style.display = 'none';
}}

function chooseAction(action){{
    const step1 = document.getElementById('quickActionStep1');
    const step2 = document.getElementById('quickActionStep2');
    const title = document.getElementById('quickActionTitle');

    window.selectedQuickAction = action;
    if(step1) step1.style.display = 'none';
    if(step2) step2.style.display = 'block';
    if(title) title.textContent = action === 'remove' ? 'Sticker entfernen' : 'Sticker hinzufügen';
}}

function chooseMode(mode){{
    closeQuickActions();

    if(mode === 'select'){{
        if(window.selectedQuickAction === 'remove'){{
            toggleSmartRemove();
        }}else{{
            toggleSmartAdd();
        }}
        return;
    }}

    if(window.selectedQuickAction === 'remove'){{
        showKeyboardInput('remove');
    }}else{{
        showKeyboardInput('add');
    }}
}}

function showKeyboardInput(mode){{
    smartActionMode = null;
    smartAddMode = true;
    keyboardInputMode = true;
    selectedStickers = [];
    document.body.classList.remove('smart-add-active');
    document.body.classList.add('pending-active');
    document.body.classList.add('keyboard-input-active');

    const input = document.getElementById('stickerSearch');
    if(input){{
        input.value = '';
        input.type = 'text';
        input.placeholder = mode === "remove" ? "Sticker-Code eintragen und Enter drücken" : "Sticker-Code eintragen und Enter drücken";
        input.focus();
    }}

    clearPendingInputError();
    updateSmartAddBar();
}}

function toggleSmartRemove(){{
    startNeutralPendingMode();
}}

function toggleSmartAdd(){{
    startNeutralPendingMode();
}}

function startNeutralPendingMode(){{
    smartActionMode = null;
    smartAddMode = true;
    keyboardInputMode = true;
    selectedStickers = [];
    document.body.classList.add('smart-add-active');
    document.body.classList.add('pending-active');
    document.body.classList.add('keyboard-input-active');
    resetStickerSearch();
    clearPendingInputError();

    const input = document.getElementById('stickerSearch');
    if(input){{
        input.type = 'text';
        input.placeholder = 'Sticker suchen oder Code eingeben...';
        input.focus();
    }}

    updatePendingSlotBadges();
    updateSmartAddBar();
}}


function updateSmartAddBar(){{
    const bar = document.getElementById('smartAddBar');
    const count = document.getElementById('smartAddCount');
    const label = document.getElementById('smartAddLabel');
    const primary = document.getElementById('smartAddPrimary');

    if(!bar || !count || !label || !primary) return;

    count.textContent = selectedStickers.length;
    primary.disabled = selectedStickers.length === 0;
    label.textContent = 'Sticker ausgewählt';
    primary.textContent = 'Auswahl prüfen';
    bar.classList.remove('remove-mode');

    bar.style.display = smartAddMode ? 'flex' : 'none';
    updatePendingSlotBadges();
}}

function cancelSmartAdd(){{
    smartAddMode = false;
    keyboardInputMode = false;
    selectedStickers = [];
    document.body.classList.remove('smart-add-active');
    document.body.classList.remove('pending-active');
    document.body.classList.remove('keyboard-input-active');
    closePendingReview();
    clearPendingInputError();

    updatePendingSlotBadges();
    resetStickerSearch();
    updateSmartAddBar();
}}

function submitSmartAdd(){{
    if(selectedStickers.length === 0) return;

    openPendingReview();
}}

function renderPendingReview(){{
    const list = document.getElementById('pendingReviewList');
    const title = document.getElementById('pendingReviewTitle');
    if(!list || !title) return;

    const counts = getPendingCounts();
    const codes = Object.keys(counts);

    title.textContent = 'Auswahl prüfen';
    list.innerHTML = '';

    if(codes.length === 0){{
        list.innerHTML = '<p class="pending-review-empty">Keine Sticker vorgemerkt.</p>';
        return;
    }}

    codes.forEach(function(code){{
        const row = document.createElement('div');
        row.className = 'pending-review-row';

        const codeText = document.createElement('strong');
        codeText.textContent = displayCodeForPending(code);

        const controls = document.createElement('div');
        controls.className = 'pending-review-controls';

        const minusButton = document.createElement('button');
        minusButton.type = 'button';
        minusButton.textContent = '-';
        minusButton.setAttribute('aria-label', displayCodeForPending(code) + ' reduzieren');
        minusButton.addEventListener('click', function(){{
            decrementPendingCode(code);
        }});

        const amount = document.createElement('input');
        amount.type = 'number';
        amount.min = '0';
        amount.step = '1';
        amount.value = counts[code];
        amount.setAttribute('aria-label', 'Menge fuer ' + displayCodeForPending(code));
        amount.addEventListener('change', function(){{
            setPendingCount(code, amount.value);
        }});

        const plusButton = document.createElement('button');
        plusButton.type = 'button';
        plusButton.textContent = '+';
        plusButton.setAttribute('aria-label', displayCodeForPending(code) + ' erhoehen');
        plusButton.addEventListener('click', function(){{
            incrementPendingCode(code);
        }});

        controls.appendChild(minusButton);
        controls.appendChild(amount);
        controls.appendChild(plusButton);

        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.className = 'pending-review-remove';
        removeButton.textContent = '×';
        removeButton.setAttribute('aria-label', displayCodeForPending(code) + ' entfernen');
        removeButton.addEventListener('click', function(){{
            removePendingCode(code);
        }});

        row.appendChild(codeText);
        row.appendChild(controls);
        row.appendChild(removeButton);
        list.appendChild(row);
    }});
}}

function openPendingReview(){{
    const modal = document.getElementById('pendingReviewModal');
    if(!modal) return;

    renderPendingReview();
    modal.style.display = 'flex';
}}

function closePendingReview(){{
    const modal = document.getElementById('pendingReviewModal');
    if(modal) modal.style.display = 'none';
}}

function confirmSmartAdd(action){{
    if(selectedStickers.length === 0) return;

    smartActionMode = action === 'remove' ? 'remove' : 'add';

    const form = document.createElement('form');
    form.method = 'POST';
    form.action = smartActionMode === "remove" ? '/bulk_remove/{album_id}' : '/bulk_add/{album_id}';
    selectedStickers.forEach(function(code){{
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'codes';
        input.value = code;
        form.appendChild(input);
    }});

    document.body.appendChild(form);
    form.submit();
}}

document.addEventListener('click', function(event){{
    const slot = event.target.closest('.slot');
    if(!smartAddMode || !slot) return;

    event.preventDefault();

    const code = slot.dataset.code || decodeURIComponent(slot.getAttribute('href').split('/').pop());

    incrementPendingCode(code);
}});
</script>
'''
    html += trophy_popup
    html += bottom_nav("sammlr")
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

    con = get_db()
    cur = con.cursor()

    for code in resolved_codes:
        row = con.execute(
            "SELECT * FROM stickers WHERE user_id=? AND album_id=? AND sticker_code=?",
            (current_user_id(), album_id, code)
        ).fetchone()

        if row:
            neue_quantity = row["quantity"] + 1
            neue_duplicates = max(neue_quantity - 1, 0)
            cur.execute(
                "UPDATE stickers SET quantity=?, duplicates=? WHERE id=?",
                (neue_quantity, neue_duplicates, row["id"])
            )
        else:
            cur.execute(
                """
                INSERT INTO stickers (user_id, album_id, sticker_code, status, duplicates, quantity)
                VALUES (?, ?, ?, "owned", 0, 1)
                """,
                (current_user_id(), album_id, code)
            )

    con.commit()
    con.close()

    nachher_erreicht = erreichte_trophaeen(album_id)
    neue_trophies = [t for t in nachher_erreicht if t not in vorher_erreicht]

    session["last_action"] = {
        "action": "bulk_add",
        "album_id": album_id,
        "codes": resolved_codes,
        "filter": "all"
    }

    msg = f"{len(resolved_codes)} Sticker hinzugefügt."
    url = f"/album/{album_id}?message={quote(msg)}&focus=add"

    if neue_trophies:
        trophy_text = ", ".join(neue_trophies)
        url += f"&trophy={quote(trophy_text)}&count={len(neue_trophies)}"

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

    con = get_db()
    cur = con.cursor()

    for code in resolved_codes:
        row = con.execute(
            "SELECT * FROM stickers WHERE user_id=? AND album_id=? AND sticker_code=?",
            (current_user_id(), album_id, code)
        ).fetchone()

        if not row:
            continue

        neue_quantity = max(row["quantity"] - 1, 0)
        neue_duplicates = max(neue_quantity - 1, 0)

        if neue_quantity == 0:
            cur.execute("DELETE FROM stickers WHERE id=?", (row["id"],))
        else:
            cur.execute(
                "UPDATE stickers SET quantity=?, duplicates=? WHERE id=?",
                (neue_quantity, neue_duplicates, row["id"])
            )

    con.commit()
    con.close()

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
        raw_quantity = request.form.get("quantity", "0").strip()

        try:
            quantity = max(int(raw_quantity), 0)
        except ValueError:
            quantity = 0

        duplicates = max(quantity - 1, 0)
        con = get_db()
        cur = con.cursor()

        daten = con.execute(
            "SELECT * FROM stickers WHERE user_id=? AND album_id=? AND sticker_code=?",
            (current_user_id(), album_id, code)
        ).fetchone()

        if quantity == 0:
            if daten:
                cur.execute("DELETE FROM stickers WHERE id=?", (daten["id"],))
        elif daten:
            cur.execute(
                "UPDATE stickers SET quantity=?, duplicates=? WHERE id=?",
                (quantity, duplicates, daten["id"])
            )
        else:
            cur.execute(
                """
                INSERT INTO stickers (user_id, album_id, sticker_code, status, duplicates, quantity)
                VALUES (?, ?, ?, "owned", ?, ?)
                """,
                (current_user_id(), album_id, code, duplicates, quantity)
            )

        con.commit()
        con.close()

        msg = f"Anzahl für Sticker {display_code(code)} auf {quantity} gesetzt."
        if quantity == 0:
            msg = f"Sticker {display_code(code)} aus deiner Sammlung entfernt."

        return redirect(f"/album/{album_id}?filter={current_filter}&message={quote(msg)}&focus=add&trigger={quote(code)}")

    album, by_code, gesammelt, doppelte, prozent, total = lade_album(album_id)
    q = by_code[code]["quantity"] if code in by_code else 0

    if q == 0:
        farbe, status = "missing", "Fehlt"
    elif q == 1:
        farbe, status = "owned", "Vorhanden"
    else:
        farbe, status = "duplicate", "Doppelt"

    return f"""
    <html><head>{style()}</head><body><div class="container">
    <a class="btn" href="/album/{album_id}">← Zurück</a>
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
                    <a class="btn" href="/add/{album_id}/{code}">+ Hinzufügen</a>
                    <a class="btn gray" href="/remove/{album_id}/{code}">- Entfernen</a>
                </div>
            </div>
        </div>
    </div>
    </div></body></html>
    """


@app.route("/add/<album_id>/<path:code>")
def add(album_id, code):
    vorher_erreicht = erreichte_trophaeen(album_id)
    current_filter = request.args.get("filter", "all")

    con = get_db()
    cur = con.cursor()

    daten = con.execute(
        "SELECT * FROM stickers WHERE user_id=? AND album_id=? AND sticker_code=?",
        (current_user_id(), album_id, code)
    ).fetchone()

    if daten:
        neue_quantity = daten["quantity"] + 1
        neue_duplicates = max(neue_quantity - 1, 0)

        cur.execute(
            "UPDATE stickers SET quantity=?, duplicates=? WHERE id=?",
            (neue_quantity, neue_duplicates, daten["id"])
        )
    else:
        neue_quantity = 1
        neue_duplicates = 0

        cur.execute(
            """
            INSERT INTO stickers (user_id, album_id, sticker_code, status, duplicates, quantity)
            VALUES (?, ?, ?, "owned", ?, ?)
            """,
            (current_user_id(), album_id, code, neue_duplicates, neue_quantity)
        )

    con.commit()
    con.close()

    nachher_erreicht = erreichte_trophaeen(album_id)
    

    neue_trophies = [t for t in nachher_erreicht if t not in vorher_erreicht] 


    msg = f"Du hast Sticker {display_code(code)} doppelt." if neue_duplicates >= 1 else f"Du hast Sticker {display_code(code)} zur Sammlung hinzugefügt."

    url = f"/album/{album_id}?filter={current_filter}&message={quote(msg)}&focus=add&smart=1"

    if neue_trophies:
        trophy_text = ", ".join(neue_trophies)
        url += f"&trophy={quote(trophy_text)}&count={len(neue_trophies)}&trigger={quote(code)}"

    session["last_action"] = {
        "action": "add",
        "album_id": album_id,
        "code": code,
        "filter": current_filter
    }
    print("FINAL URL:", url)

    return redirect(url)

    

@app.route("/undo")
def undo_last_action():
    data = session.get("last_action")

    if not data:
        return redirect("/")

    album_id = data["album_id"]
    action = data["action"]
    current_filter = data.get("filter", "all")
    code = data.get("code")
    codes = data.get("codes", [])

    con = get_db()
    cur = con.cursor()

    if action in ("add", "bulk_add"):
        undo_codes = codes if action == "bulk_add" else [code]

        for undo_code in undo_codes:
            row = con.execute(
                "SELECT * FROM stickers WHERE user_id=? AND album_id=? AND sticker_code=?",
                (current_user_id(), album_id, undo_code)
            ).fetchone()

            if row:
                neue_quantity = max(row["quantity"] - 1, 0)
                neue_duplicates = max(neue_quantity - 1, 0)

                if neue_quantity == 0:
                    cur.execute("DELETE FROM stickers WHERE id=?", (row["id"],))
                else:
                    cur.execute(
                        "UPDATE stickers SET quantity=?, duplicates=? WHERE id=?",
                        (neue_quantity, neue_duplicates, row["id"])
                    )

    elif action in ("remove", "bulk_remove"):
        undo_codes = codes if action == "bulk_remove" else [code]

        for undo_code in undo_codes:
            row = con.execute(
                "SELECT * FROM stickers WHERE user_id=? AND album_id=? AND sticker_code=?",
                (current_user_id(), album_id, undo_code)
            ).fetchone()

            if row:
                neue_quantity = row["quantity"] + 1
                neue_duplicates = max(neue_quantity - 1, 0)
                cur.execute(
                    "UPDATE stickers SET quantity=?, duplicates=? WHERE id=?",
                    (neue_quantity, neue_duplicates, row["id"])
                )
            else:
                cur.execute(
                    """
                    INSERT INTO stickers (user_id, album_id, sticker_code, status, duplicates, quantity)
                    VALUES (?, ?, ?, "owned", 0, 1)
                    """,
                    (current_user_id(), album_id, undo_code)
                )

    con.commit()
    con.close()

    session.pop("last_action", None)

    if action == "bulk_add":
        msg = f"{len(codes)} hinzugefügte Sticker rückgängig gemacht."
    elif action == "bulk_remove":
        msg = f"{len(codes)} entfernte Sticker rückgängig gemacht."
    else:
        msg = f"Aktion für Sticker {display_code(code)} rückgängig gemacht."
    return redirect(f"/album/{album_id}?filter={current_filter}&message={quote(msg)}&focus=add")


@app.route("/remove/<album_id>/<path:code>")

def remove(album_id, code):
    con = get_db()
    current_filter = request.args.get("filter", "all")
    cur = con.cursor()
    daten = con.execute(
        "SELECT * FROM stickers WHERE user_id=? AND album_id=? AND sticker_code=?",
        (current_user_id(), album_id, code)
    ).fetchone()

    if daten:
        neue_quantity = max(daten["quantity"] - 1, 0)
        neue_duplicates = max(neue_quantity - 1, 0)

        if neue_quantity == 0:
            cur.execute("DELETE FROM stickers WHERE id=?", (daten["id"],))
        else:
            cur.execute("UPDATE stickers SET quantity=?, duplicates=? WHERE id=?", (neue_quantity, neue_duplicates, daten["id"]))

    con.commit()
    con.close()
    session["last_action"] = {
        "action": "remove",
        "album_id": album_id,
        "code": code,
        "filter": current_filter
    }
    msg = f"Sticker {display_code(code)} wurde entfernt."
    return redirect(f"/album/{album_id}?filter={current_filter}&message={quote(msg)}&focus=remove")


# --- Trade/Sticker helper functions for trade completion ---
def change_sticker_quantity(con, user_id, album_id, code, delta):
    cur = con.cursor()
    row = con.execute(
        "SELECT * FROM stickers WHERE user_id=? AND album_id=? AND sticker_code=?",
        (user_id, album_id, code)
    ).fetchone()

    if row:
        new_quantity = max(row["quantity"] + delta, 0)
        new_duplicates = max(new_quantity - 1, 0)

        if new_quantity == 0:
            cur.execute("DELETE FROM stickers WHERE id=?", (row["id"],))
        else:
            cur.execute(
                "UPDATE stickers SET quantity=?, duplicates=? WHERE id=?",
                (new_quantity, new_duplicates, row["id"])
            )
    elif delta > 0:
        cur.execute(
            """
            INSERT INTO stickers (user_id, album_id, sticker_code, status, duplicates, quantity)
            VALUES (?, ?, ?, "owned", 0, ?)
            """,
            (user_id, album_id, code, delta)
        )


def complete_trade(con, trade):
    give_codes = json.loads(trade["give_codes"])
    get_codes = json.loads(trade["get_codes"])
    album_id = trade["album_id"]
    from_user_id = trade["from_user_id"]
    to_user_id = trade["to_user_id"]

    for code in give_codes:
        change_sticker_quantity(con, from_user_id, album_id, code, -1)
        change_sticker_quantity(con, to_user_id, album_id, code, 1)

    for code in get_codes:
        change_sticker_quantity(con, to_user_id, album_id, code, -1)
        change_sticker_quantity(con, from_user_id, album_id, code, 1)


@app.route("/album/<album_id>/trades")
def album_trades(album_id):
    con = get_db()

    andere_user = con.execute(
        """
        SELECT users.id, users.username
        FROM users
        JOIN user_albums ON user_albums.user_id = users.id
        WHERE users.id != ? AND user_albums.album_id = ?
        """,
        (current_user_id(), album_id)
    ).fetchall()

    meine_sticker = con.execute(
        "SELECT sticker_code, quantity FROM stickers WHERE user_id=? AND album_id=?",
        (current_user_id(), album_id)
    ).fetchall()

    meine_mengen = {s["sticker_code"]: s["quantity"] for s in meine_sticker}
    alle_codes = all_codes(album_id)

    meine_fehlenden = {code for code in alle_codes if meine_mengen.get(code, 0) == 0}
    meine_doppelten = {code for code in alle_codes if meine_mengen.get(code, 0) >= 2}

    html = f"""
    <html><head>{style()}</head><body><div class="container">
    <a class="btn" href="/album/{album_id}">← Zurück</a>
    <h1>Tauschbörse</h1>
    <p class="subline">Finde Sammler, mit denen du Lücken schließen kannst.</p>
    """

    if not andere_user:
        html += """
        <div class="card trade-empty-card">
            <h2>Noch keine Tauschpartner für dieses Album.</h2>
            <p>Sobald andere Nutzer dieses Album hinzufügen, erscheinen sie hier.</p>
        </div>
        """

    for user in andere_user:
        andere_sticker = con.execute(
            "SELECT sticker_code, quantity FROM stickers WHERE user_id=? AND album_id=?",
            (user["id"], album_id)
        ).fetchall()

        andere_mengen = {s["sticker_code"]: s["quantity"] for s in andere_sticker}
        andere_fehlenden = {code for code in alle_codes if andere_mengen.get(code, 0) == 0}
        andere_doppelten = {code for code in alle_codes if andere_mengen.get(code, 0) >= 2}

        du_bekommst = sorted(
            meine_fehlenden.intersection(andere_doppelten),
            key=lambda x: [int(part) if part.isdigit() else part for part in __import__('re').split(r'(\d+)', x)]
        )
        du_gibst = sorted(
            meine_doppelten.intersection(andere_fehlenden),
            key=lambda x: [int(part) if part.isdigit() else part for part in __import__('re').split(r'(\d+)', x)]
        )
        match_count = min(len(du_bekommst), len(du_gibst))

        badge = "Direkter Tausch möglich" if match_count > 0 else "Noch kein direkter Tausch möglich"
        badge_class = "ready" if match_count > 0 else "muted"

        html += f"""
        <div class="trade-partner-card">
            <div class="trade-partner-head">
                <h2>{user['username']}</h2>
                <span class="trade-partner-status {badge_class}">{badge}</span>
            </div>

            <div class="trade-partner-stats">
                <div>
                    <strong>{len(du_bekommst)}</strong>
                    <span>Du bekommst</span>
                </div>
                <div>
                    <strong>{len(du_gibst)}</strong>
                    <span>Du gibst</span>
                </div>
            </div>

            <a class="trade-partner-button" href="/album/{album_id}/trades/{user['id']}">Tradecenter öffnen</a>
        </div>
        """

    html += bottom_nav("sammlr")
    html += "</div></body></html>"
    con.close()
    return html

# --- Album Statistik Route ---

@app.route("/album/<album_id>/statistik")
def album_statistik(album_id):
    album, by_code, gesammelt, doppelte, prozent, total = lade_album(album_id)

    html = f"""
    <html><head>{style()}</head><body><div class="container">
    <a class="btn" href="/album/{album_id}">← Zurück</a>
    <h1>{album['name']}</h1>
    <p class="subline">Album-Statistik</p>

    <div class="card">
        <h2>Fortschritt</h2>
        <div class="big">{prozent}%</div>
        <div class="progress" data-progress="{prozent}%">
            <div class="progress-bar" style="width:{prozent}%;"></div>
        </div>
    </div>

    <div class="stats">
        <div class="stat">
            <div class="big">{gesammelt}</div>
            <p>Gesammelt</p>
        </div>
        <div class="stat">
            <div class="big">{total - gesammelt}</div>
            <p>Fehlend</p>
        </div>
        <div class="stat">
            <div class="big">{doppelte}</div>
            <p>Doppelte</p>
        </div>
        <div class="stat">
            <div class="big">{total}</div>
            <p>Gesamt</p>
        </div>
    </div>

    {bottom_nav("statistik")}
    </div></body></html>
    """
    return html

@app.route("/album/<album_id>/trades/<int:other_user_id>")
def trade_center(album_id, other_user_id):
    con = get_db()

    other_user = con.execute(
        "SELECT * FROM users WHERE id=?",
        (other_user_id,)
    ).fetchone()

    if not other_user:
        con.close()
        return redirect(f"/album/{album_id}/trades")

    alle_codes = all_codes(album_id)

    meine = con.execute(
        "SELECT sticker_code, quantity FROM stickers WHERE user_id=? AND album_id=?",
        (current_user_id(), album_id)
    ).fetchall()

    andere = con.execute(
        "SELECT sticker_code, quantity FROM stickers WHERE user_id=? AND album_id=?",
        (other_user_id, album_id)
    ).fetchall()

    meine_mengen = {s['sticker_code']: s['quantity'] for s in meine}
    andere_mengen = {s['sticker_code']: s['quantity'] for s in andere}

    meine_fehlenden = {c for c in alle_codes if meine_mengen.get(c, 0) == 0}
    meine_doppelten = {c for c in alle_codes if meine_mengen.get(c, 0) >= 2}

    andere_fehlenden = {c for c in alle_codes if andere_mengen.get(c, 0) == 0}
    andere_doppelten = {c for c in alle_codes if andere_mengen.get(c, 0) >= 2}

    du_bekommst = sorted(
        meine_fehlenden.intersection(andere_doppelten),
        key=lambda x: [int(part) if part.isdigit() else part for part in __import__('re').split(r'(\d+)', x)]
    )
    du_gibst = sorted(
        meine_doppelten.intersection(andere_fehlenden),
        key=lambda x: [int(part) if part.isdigit() else part for part in __import__('re').split(r'(\d+)', x)]
    )
    trade_limit = min(len(du_bekommst), len(du_gibst))

    if trade_limit == 0:
        trade_builder = """
        <div class="card">
            <h2>Noch kein ausgeglichener Trade möglich</h2>
            <p>Ein Trade braucht auf beiden Seiten mindestens einen passenden Sticker.</p>
        </div>
        """
    elif len(du_bekommst) == len(du_gibst):
        hidden_get = "".join(f'<input type="hidden" name="get_codes" value="{code}">' for code in du_bekommst)
        hidden_give = "".join(f'<input type="hidden" name="give_codes" value="{code}">' for code in du_gibst)
        trade_builder = f"""
        <div class="card">
            <h2>Trade-Vorschlag</h2>
            <p>Beide Seiten haben gleich viele passende Sticker. Alle können vorgeschlagen werden.</p>
            <p><strong>Maximaler Trade:</strong> {trade_limit} Sticker</p>
            <form method="POST" action="/album/{album_id}/trades/{other_user_id}/request">
                {hidden_get}
                {hidden_give}
                <button class="btn" type="submit">Trade anfragen</button>
            </form>
        </div>
        """
    elif len(du_bekommst) < len(du_gibst):
        optionen = "".join(
            f'<option value="{code}">{display_code(code)}</option>'
            for code in du_gibst
        )
        selects = "".join(
            f'<select name="give_codes">{optionen}</select><br><br>'
            for i in range(trade_limit)
        )
        hidden_get = "".join(f'<input type="hidden" name="get_codes" value="{code}">' for code in du_bekommst)
        automatisch = ", ".join(display_code(code) for code in du_bekommst)

        trade_builder = f"""
        <div class="card">
            <h2>Trade zusammenstellen</h2>
            <p><strong>Maximaler Trade:</strong> {trade_limit} Sticker</p>
            <p>Du bekommst automatisch: <strong>{automatisch}</strong></p>
            <p>Wähle aus, welche deiner passenden Doppelten du dafür abgeben möchtest.</p>
            <form method="POST" action="/album/{album_id}/trades/{other_user_id}/request">
                {hidden_get}
                {selects}
                <button class="btn" type="submit">Trade anfragen</button>
            </form>
        </div>
        """
    else:
        optionen = "".join(
            f'<option value="{code}">{display_code(code)}</option>'
            for code in du_bekommst
        )
        selects = "".join(
            f'<select name="get_codes">{optionen}</select><br><br>'
            for i in range(trade_limit)
        )
        hidden_give = "".join(f'<input type="hidden" name="give_codes" value="{code}">' for code in du_gibst)
        automatisch = ", ".join(display_code(code) for code in du_gibst)

        trade_builder = f"""
        <div class="card">
            <h2>Trade zusammenstellen</h2>
            <p><strong>Maximaler Trade:</strong> {trade_limit} Sticker</p>
            <p>Du gibst automatisch: <strong>{automatisch}</strong></p>
            <p>Wähle aus, welche passenden Sticker du dafür bekommen möchtest.</p>
            <form method="POST" action="/album/{album_id}/trades/{other_user_id}/request">
                {hidden_give}
                {selects}
                <button class="btn" type="submit">Trade anfragen</button>
            </form>
        </div>
        """

    html = f"""
    <html><head>{style()}</head><body><div class="container">
    <a class="btn" href="/album/{album_id}/trades">← Zurück</a>
    <h1>🤝 Tradecenter</h1>
    <p class="subline">Mögliche Trades mit {other_user['username']}</p>

    <div class="card">
        <h2>Du bekommst ({len(du_bekommst)})</h2>
        <p>{', '.join(display_code(x) for x in du_bekommst[:30]) or 'Keine Treffer'}</p>
    </div>

    <div class="card">
        <h2>Du gibst ({len(du_gibst)})</h2>
        <p>{', '.join(display_code(x) for x in du_gibst[:30]) or 'Keine Treffer'}</p>
    </div>

    {trade_builder}

    </div></body></html>
    """

    con.close()
    return html


# --- Trade-Request routes ---

@app.route("/album/<album_id>/trades/<int:other_user_id>/request", methods=["POST"])
def create_trade_request(album_id, other_user_id):
    give_codes = request.form.getlist("give_codes")
    get_codes = request.form.getlist("get_codes")

    give_codes = list(dict.fromkeys(give_codes))
    get_codes = list(dict.fromkeys(get_codes))

    if not give_codes or not get_codes:
        return redirect(f"/album/{album_id}/trades/{other_user_id}")

    con = get_db()
    con.execute(
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

    sender = con.execute("SELECT username FROM users WHERE id=?", (current_user_id(),)).fetchone()
    album = con.execute("SELECT name FROM albums WHERE id=?", (album_id,)).fetchone()
    create_notification(
        con,
        other_user_id,
        "Neue Trade-Anfrage",
        f"{sender['username']} möchte mit dir bei {album['name']} tauschen."
    )
    con.commit()
    con.close()

    return redirect(f"/trades?message=Trade-Anfrage%20gesendet")


@app.route("/trades")
def trades_overview():
    message = request.args.get("message", "")
    con = get_db()

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
        WHERE trade_requests.from_user_id=? OR trade_requests.to_user_id=?
        ORDER BY trade_requests.created_at DESC
        """,
        (current_user_id(), current_user_id())
    ).fetchall()

    html = f"""
    <html><head>{style()}</head><body><div class="container">
    <a class="btn" href="/">← Zurück</a>
    <h1>🤝 Offene Trades</h1>
    <p class="subline">Trade-Anfragen, die später nach echtem Treffen abgeschlossen werden.</p>
    {f'<div class="notice notice-success"><h2>{message}</h2></div>' if message else ''}
    """

    if not rows:
        html += """
        <div class="card">
            <h2>Noch keine Trade-Anfragen</h2>
            <p>Öffne ein Album und starte über das Trade-Matching eine Anfrage.</p>
        </div>
        """

    for trade in rows:
        give_codes = json.loads(trade["give_codes"])
        get_codes = json.loads(trade["get_codes"])
        is_receiver = trade["to_user_id"] == current_user_id()
        status = trade["status"]

        if is_receiver:
            headline = f"{trade['sender_name']} möchte mit dir tauschen"
            du_bekommst = give_codes
            du_gibst = get_codes
        else:
            headline = f"Anfrage an {trade['receiver_name']}"
            du_bekommst = get_codes
            du_gibst = give_codes

        actions = ""
        if is_receiver and status == "open":
            actions = f"""
            <a class="btn green" href="/trades/{trade['id']}/accept">Annehmen</a>
            <a class="btn gray" href="/trades/{trade['id']}/decline">Ablehnen</a>
            """
        elif status == "accepted":
            my_confirmed = trade["to_confirmed"] if is_receiver else trade["from_confirmed"]
            other_confirmed = trade["from_confirmed"] if is_receiver else trade["to_confirmed"]
            confirm_text = "Du hast den Wechsel bestätigt." if my_confirmed else "Bestätige nach der echten Übergabe den Wechsel."
            other_text = "Die Gegenseite hat bestätigt." if other_confirmed else "Wartet noch auf Bestätigung der Gegenseite."
            actions = f"""
            <p><strong>Angenommen:</strong> Verabredet euch per WhatsApp zum Tauschen.</p>
            <p>{confirm_text}<br>{other_text}</p>
            <a class="btn green" href="/trades/{trade['id']}/confirm">🤝 Wechsel bestätigen</a>
            <a class="btn gray" href="/trades/{trade['id']}/cancel">💥 Deal geplatzt</a>
            """
        elif status == "completed":
            actions = "<p><strong>🤝 Wechsel bestätigt:</strong> Die Sticker wurden automatisch gebucht.</p>"
        elif status == "cancelled":
            actions = "<p><strong>💥 Deal geplatzt:</strong> Keine Bestandsänderung. Der Match kann neu angefragt werden.</p>"
        elif status == "declined":
            actions = "<p><strong>Abgelehnt</strong></p>"
        else:
            actions = "<p><strong>Wartet auf Antwort</strong></p>"

        html += f"""
        <div class="card">
            <h2>{headline}</h2>
            <p><strong>Album:</strong> {trade['album_name']}</p>
            <p><strong>Status:</strong> {status}</p>

            <h3>Du bekommst</h3>
            <p>{', '.join(display_code(c) for c in du_bekommst)}</p>

            <h3>Du gibst</h3>
            <p>{', '.join(display_code(c) for c in du_gibst)}</p>

            {actions}
        </div>
        """

    html += bottom_nav("sammlr")
    html += "</div></body></html>"
    con.close()
    return html


@app.route("/trades/<int:trade_id>/accept")
def accept_trade(trade_id):
    con = get_db()
    trade = con.execute(
        "SELECT * FROM trade_requests WHERE id=? AND to_user_id=?",
        (trade_id, current_user_id())
    ).fetchone()

    if trade:
        con.execute(
            "UPDATE trade_requests SET status='accepted', from_confirmed=0, to_confirmed=0 WHERE id=? AND to_user_id=?",
            (trade_id, current_user_id())
        )
        receiver = con.execute("SELECT username FROM users WHERE id=?", (current_user_id(),)).fetchone()
        create_notification(
            con,
            trade["from_user_id"],
            "Trade angenommen",
            f"{receiver['username']} hat deine Trade-Anfrage angenommen. Jetzt könnt ihr euch verabreden."
        )
        con.commit()
    con.close()
    return redirect("/trades?message=Trade%20angenommen")



@app.route("/trades/<int:trade_id>/decline")
def decline_trade(trade_id):
    con = get_db()
    trade = con.execute(
        "SELECT * FROM trade_requests WHERE id=? AND to_user_id=?",
        (trade_id, current_user_id())
    ).fetchone()

    if trade:
        con.execute(
            "UPDATE trade_requests SET status='declined' WHERE id=? AND to_user_id=?",
            (trade_id, current_user_id())
        )
        receiver = con.execute("SELECT username FROM users WHERE id=?", (current_user_id(),)).fetchone()
        create_notification(
            con,
            trade["from_user_id"],
            "Trade abgelehnt",
            f"{receiver['username']} hat deine Trade-Anfrage abgelehnt."
        )
        con.commit()
    con.close()
    return redirect("/trades?message=Trade%20abgelehnt")


# --- Confirm/cancel trade routes ---

@app.route("/trades/<int:trade_id>/confirm")
def confirm_trade(trade_id):
    con = get_db()
    trade = con.execute(
        "SELECT * FROM trade_requests WHERE id=? AND status='accepted' AND (from_user_id=? OR to_user_id=?)",
        (trade_id, current_user_id(), current_user_id())
    ).fetchone()

    if not trade:
        con.close()
        return redirect("/trades?message=Trade%20nicht%20gefunden")

    if trade["from_user_id"] == current_user_id():
        con.execute("UPDATE trade_requests SET from_confirmed=1 WHERE id=?", (trade_id,))
        confirmer = con.execute("SELECT username FROM users WHERE id=?", (current_user_id(),)).fetchone()
        create_notification(
            con,
            trade["to_user_id"],
            "Wechsel vorgemerkt",
            f"{confirmer['username']} hat den Wechsel bestätigt. Jetzt fehlt noch deine Bestätigung."
        )
    elif trade["to_user_id"] == current_user_id():
        con.execute("UPDATE trade_requests SET to_confirmed=1 WHERE id=?", (trade_id,))
        confirmer = con.execute("SELECT username FROM users WHERE id=?", (current_user_id(),)).fetchone()
        create_notification(
            con,
            trade["from_user_id"],
            "Wechsel vorgemerkt",
            f"{confirmer['username']} hat den Wechsel bestätigt. Jetzt fehlt noch deine Bestätigung."
        )

    con.commit()

    updated = con.execute("SELECT * FROM trade_requests WHERE id=?", (trade_id,)).fetchone()

    if updated["from_confirmed"] == 1 and updated["to_confirmed"] == 1:
        complete_trade(con, updated)
        con.execute("UPDATE trade_requests SET status='completed' WHERE id=?", (trade_id,))
        create_notification(
            con,
            updated["from_user_id"],
            "Wechsel bestätigt",
            "Der Trade wurde von beiden Seiten bestätigt und automatisch gebucht."
        )
        create_notification(
            con,
            updated["to_user_id"],
            "Wechsel bestätigt",
            "Der Trade wurde von beiden Seiten bestätigt und automatisch gebucht."
        )
        con.commit()
        con.close()
        return redirect("/trades?message=Wechsel%20best%C3%A4tigt")

    con.close()
    return redirect("/trades?message=Wechsel%20vormarkiert")


@app.route("/trades/<int:trade_id>/cancel")
def cancel_trade(trade_id):
    con = get_db()
    trade = con.execute(
        "SELECT * FROM trade_requests WHERE id=? AND status='accepted' AND (from_user_id=? OR to_user_id=?)",
        (trade_id, current_user_id(), current_user_id())
    ).fetchone()

    if trade:
        con.execute(
            "UPDATE trade_requests SET status='cancelled' WHERE id=? AND status='accepted' AND (from_user_id=? OR to_user_id=?)",
            (trade_id, current_user_id(), current_user_id())
        )
        other_user_id = trade["to_user_id"] if trade["from_user_id"] == current_user_id() else trade["from_user_id"]
        canceller = con.execute("SELECT username FROM users WHERE id=?", (current_user_id(),)).fetchone()
        create_notification(
            con,
            other_user_id,
            "Deal geplatzt",
            f"{canceller['username']} hat den Deal platzen lassen. Der Match kann neu angefragt werden."
        )
        con.commit()
    con.close()
    return redirect("/trades?message=Deal%20geplatzt")


# --- Notification routes ---

@app.route("/notifications/<int:notification_id>/read")
def mark_notification_read(notification_id):
    con = get_db()
    con.execute(
        "UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?",
        (notification_id, current_user_id())
    )
    con.commit()
    con.close()
    return redirect("/")

@app.route("/album/<album_id>/trophaeen")
def album_trophaeen(album_id):
    album, by_code, gesammelt, doppelte, prozent, total = lade_album(album_id)
    last_trophy, next_trophy, trophies = trophy_status(album_id, gesammelt, total)

    if album_id == "wm26":
        trophy_items = wm26_trophy_items(by_code, gesammelt, total)
        unlocked_count = len([item for item in trophy_items if item["unlocked"]])
        next_item = next((item for item in trophy_items if not item["unlocked"]), None)
        next_trophy = next_item["title"] if next_item else "Alle Trophäen erhalten"

        html = f"""
        <html><head>{style()}</head><body><div class="container">
        <a class="btn" href="/album/{album_id}">← Zurück</a>
        <h1>Trophäenschrank</h1>
        <p class="subline">{album['name']}</p>

        <div class="notice">
            <h2>{unlocked_count} Trophäen abgestaubt</h2>
            <p>Nächstes Ziel: <strong>{next_trophy}</strong></p>
        </div>
        """

        html += render_wm26_trophy_items(trophy_items)
        html += bottom_nav("trophaeen")
        html += "</div></body></html>"
        return html

    html = f"""
    <html><head>{style()}</head><body><div class="container">
    <a class="btn" href="/album/{album_id}">← Zurück</a>
    <h1>Album-Trophäen</h1>
    <p class="subline">{album['name']}</p>

    <div class="notice">
        <h2>Letzte Auszeichnung: {last_trophy}</h2>
        <p>Nächste Trophäe: <strong>{next_trophy}</strong></p>
    </div>
    """

    html += render_trophy_steps(trophies, gesammelt, "blue", "Sticker gesammelt")

    html += bottom_nav("trophaeen")
    html += "</div></body></html>"
    return html


@app.route("/trophaeen")
def globale_trophaeen():
    filter_name = request.args.get("filter", "all")
    show_albums = filter_name in ("all", "albums")
    show_trades = filter_name in ("all", "trades")
    show_stickers = filter_name in ("all", "stickers")
    show_duplicates = filter_name in ("all", "duplicates")

    con = get_db()

    alben = con.execute(
        """
        SELECT albums.*
        FROM albums
        JOIN user_albums ON user_albums.album_id = albums.id
        WHERE user_albums.user_id=?
        """,
        (current_user_id(),)
    ).fetchall()

    stickers = con.execute(
        "SELECT * FROM stickers WHERE user_id=?",
        (current_user_id(),)
    ).fetchall()

    completed_trades = con.execute(
        """
        SELECT COUNT(*) AS count
        FROM trade_requests
        WHERE status='completed' AND (from_user_id=? OR to_user_id=?)
        """,
        (current_user_id(), current_user_id())
    ).fetchone()["count"]

    con.close()

    sticker_gesamt = sum(s["quantity"] for s in stickers)
    doppelte_gesamt = sum(s["duplicates"] for s in stickers)

    unlocked_total = 0
    album_unlocked_total = 0
    next_candidates = []
    album_blocks = ""

    for album in alben:
        album_data, by_code, gesammelt, doppelte, prozent, total = lade_album(album["id"])
        _, _, trophies = trophy_status(album["id"], gesammelt, total)
        album_unlocked = len([t for t in trophies if gesammelt >= t[0]])
        duplicate_unlocked = 0
        album_unlocked_total += album_unlocked + duplicate_unlocked
        unlocked_total += album_unlocked + duplicate_unlocked

        nearest = nearest_album_trophy(album["id"])
        next_candidates.append((nearest["distance"], f"{album['name']}: {nearest['title']}", nearest["text"]))

        album_card_class = "global-album-complete" if prozent == 100 else "global-album-active"
        album_pill_class = "gold" if prozent == 100 else "gray"
        album_status = "Vollendet" if prozent == 100 else f"{prozent}% komplett"

        album_blocks += f"""
        <a class="global-album-card" href="/album/{album['id']}/trophaeen">
            <div class="trophy {album_card_class}">
                <span class="trophy-pill {album_pill_class}">{album_status}</span>
                <h2>{album['cover']} {album['name']}</h2>
                <p>{gesammelt}/{total} Sticker gesammelt</p>
                <p>{album_unlocked + duplicate_unlocked} Trophäen abgestaubt</p>
                <p><strong>Nächstes Ziel:</strong> {nearest['title']}</p>
            </div>
        </a>
        """

    trade_unlocked = len([t for t in global_trade_trophaeen() if completed_trades >= t[0]])
    sticker_unlocked = len([t for t in global_sticker_trophaeen() if sticker_gesamt >= t[0]])
    duplicate_global_unlocked = len([t for t in global_duplicate_trophaeen() if doppelte_gesamt >= t[0]])
    unlocked_total += trade_unlocked + sticker_unlocked + duplicate_global_unlocked

    for ziel, titel in global_trade_trophaeen():
        if completed_trades < ziel:
            next_candidates.append((ziel - completed_trades, titel, f"Noch {ziel - completed_trades} abgeschlossene Trades"))
            break

    for ziel, titel in global_sticker_trophaeen():
        if sticker_gesamt < ziel:
            next_candidates.append((ziel - sticker_gesamt, titel, f"Noch {ziel - sticker_gesamt} Gesamtsticker"))
            break

    for ziel, titel in global_duplicate_trophaeen():
        if doppelte_gesamt < ziel:
            next_candidates.append((ziel - doppelte_gesamt, titel, f"Noch {ziel - doppelte_gesamt} globale Doppelte"))
            break

    if next_candidates:
        _, next_title, next_text = sorted(next_candidates, key=lambda item: item[0])[0]
    else:
        next_title = "Alles abgestaubt"
        next_text = "Gerade ist keine nächste Trophäe offen. Wild."

    html = f"""
    <html><head>{style()}</head><body><div class="container">
    {app_header("Trophäen", "Globale Ziele und Auszeichnungen.")}

    <div class="card">
        <h2>{unlocked_total} Trophäen abgestaubt</h2>
        <p class="subline">Album, Doppelte, Trades und globale Sammlerziele.</p>

        <div class="trophy-family-grid">
            <div class="trophy-summary-card">
                <h2>{album_unlocked_total}</h2>
                <p>Alben</p>
            </div>
            <div class="trophy-summary-card">
                <h2>{trade_unlocked}</h2>
                <p>Trades</p>
            </div>
            <div class="trophy-summary-card">
                <h2>{sticker_unlocked}</h2>
                <p>Gesamtsticker</p>
            </div>
            <div class="trophy-summary-card">
                <h2>{duplicate_global_unlocked}</h2>
                <p>Doppelte</p>
            </div>
        </div>
    </div>

    <div class="notice notice-success">
        <h2>Nächstes globales Ziel</h2>
        <p><strong>{next_title}</strong></p>
        <p>{next_text}</p>
    </div>

    <div class="filter-bar">
        <a href="?filter=all" class="filter-btn {'active' if filter_name == 'all' else ''}">Alle</a>
        <a href="?filter=albums" class="filter-btn album-tab {'active' if filter_name == 'albums' else ''}">Alben</a>
        <a href="?filter=trades" class="filter-btn trade-tab {'active' if filter_name == 'trades' else ''}">Trades</a>
        <a href="?filter=stickers" class="filter-btn sticker-tab {'active' if filter_name == 'stickers' else ''}">Gesamtsticker</a>
        <a href="?filter=duplicates" class="filter-btn duplicate-tab {'active' if filter_name == 'duplicates' else ''}">Doppelte</a>
    </div>
    """

    if show_albums:
        html += f"""
        <h2>🏆 Alben</h2>
        {album_blocks}
        """

    if show_trades:
        html += """
        <h2>🤝 Trades</h2>
        """
        html += render_trophy_steps(global_trade_trophaeen(), completed_trades, "orange", "abgeschlossene Trades")

    if show_stickers:
        html += """
        <h2>📚 Gesamtsticker</h2>
        """
        html += render_trophy_steps(
            global_sticker_trophaeen(),
            sticker_gesamt,
            "blue",
            "gesammelte Sticker insgesamt"
        )

    if show_duplicates:
        html += """
        <h2>🟣 Doppelte</h2>
        """

        html += render_trophy_steps(
            global_duplicate_trophaeen(),
            doppelte_gesamt,
            "purple",
            "doppelte Sticker insgesamt"
        )

    html += bottom_nav("trophaeen")
    html += "</div></body></html>"
    return html

@app.route("/statistik")
def statistik():
    return f"""
    <html><head>{style()}</head><body><div class="container">
    {app_header("Statistik", "Zahlen, Fortschritt und Sammlungsauswertung.")}

    <div class="card">
        <h2>Kommt zurück</h2>
        <p>Statistikseite ist vorübergehend stabilisiert.</p>
    </div>

    {bottom_nav("statistik")}
    </div></body></html>
    """

@app.route("/profil")
def profil():
    return f"""
    <html><head>{style()}</head><body><div class="container">
    {app_header("Profil", "Konto und Sitzung.")}
    <div class="card">
        <p><strong>Benutzer:</strong> {session.get("username", "Unbekannt")}</p>
        <a class="btn gray" href="/logout">Abmelden</a>
    </div>
    {bottom_nav("profil")}
    </div></body></html>
    """


init_db()
app.run(debug=True, host="0.0.0.0", port=8080)
