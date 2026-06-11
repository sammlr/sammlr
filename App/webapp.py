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
    wm26_total = len(build_wm26())
    cur.execute("""
    INSERT OR IGNORE INTO albums (id, name, season, total, complete, cover)
    VALUES ('wm26', 'FIFA World Cup 2026', '2026', ?, ?, '🌍')
    """, (wm26_total, wm26_total))
    cur.execute(
        "UPDATE albums SET total=?, complete=? WHERE id='wm26'",
        (wm26_total, wm26_total)
    )

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


def render_global_trophy_grid(trophies, current_value, unit_text):
    html = '<div class="trophy-grid">'

    for ziel, titel in trophies:
        percent = min(100, int((current_value / ziel) * 100)) if ziel else 0
        unlocked = current_value >= ziel
        title_visible = percent > 0 or unlocked
        description_visible = percent >= 50 or unlocked

        title_html = titel if title_visible else '<span class="trophy-blurred-title">????????</span>'
        description = f"{ziel} {unit_text}"
        description_html = description if description_visible else '<span class="trophy-blurred-title">Beschreibung verborgen</span>'
        card_class = "trophy-unlocked trophy-gold" if unlocked else "trophy-locked trophy-gold-muted"
        pill_class = "gold" if unlocked else "gray"
        pill_text = "Abgestaubt" if unlocked else "Offen"
        status_text = "Abgestaubt" if unlocked else f"{current_value} / {ziel}"

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

    html += "</div>"
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
    {trade_request_popup_html()}

    <div class="home-section-toolbar">
        <h2 class="home-section-title">Aktive Alben</h2>
        <a class="add-album-button" href="/alben/hinzufuegen">Album hinzufügen</a>
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
        return f"{missing} fehlen"

    if filter_name == "duplicate":
        return f"{duplicate_extra} doppelt"

    return f"{owned}/{total}"


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
                return redirect(f"/album/{album_id}?filter={current_filter}&message=Tausch-Sticker%20nicht%20vorhanden.&focus=trade")

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

            msg = f"Tausch gespeichert: {display_code(trade_out)} abgegeben, {display_code(trade_in)} eingesammelt."
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
    incoming_trade_request_count = open_incoming_trade_request_count(album_id)
    trade_preview_line = (
        f"{incoming_trade_request_count} offene Anfrage{'n' if incoming_trade_request_count != 1 else ''} an dich"
        if incoming_trade_request_count > 0
        else f"{direct_partner_count} direkte Tauschpartner"
        if direct_partner_count > 0
        else "Noch keine direkten Tauschpartner"
    )
    trade_badge_html = f'<span class="album-quick-badge">{incoming_trade_request_count}</span>' if incoming_trade_request_count > 0 else ''

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

    </div>

    <div class="album-quick-links">
        <a class="album-quick-card" href="/album/{album_id}/trophaeen">
            <strong>Trophäen</strong>
            <span>Albumziele ansehen</span>
        </a>
        <a class="album-quick-card {'has-badge' if incoming_trade_request_count > 0 else ''}" href="/album/{album_id}/trades?tab={'incoming' if incoming_trade_request_count > 0 else 'partners'}">
            {trade_badge_html}
            <strong>Tauschbörse</strong>
            <span>{trade_preview_line}</span>
        </a>
    </div>

    <div class="card sticker-wall-card">
    <div class="sticker-wall-headline">
        <h2>Stickerwand</h2>
        <button type="button" class="smart-add-toggle" onclick="openQuickActions()">Hinzufügen</button>
            </div>
        <div class="sticker-filter-row">
        <a class="sticker-filter-pill {'active' if filter_name == 'all' else ''}" href="/album/{album_id}">Alle</a>
        <a class="sticker-filter-pill missing {'active' if filter_name == 'missing' else ''}" href="/album/{album_id}?filter=missing">Fehlende</a>
        <a class="sticker-filter-pill owned {'active' if filter_name == 'owned' else ''}" href="/album/{album_id}?filter=owned">Vorhandene</a>
        <a class="sticker-filter-pill duplicate {'active' if filter_name == 'duplicate' else ''}" href="/album/{album_id}?filter=duplicate">Doppelte</a>
    </div>
    <input id="stickerSearch" class="sticker-search" type="search" placeholder="Sticker oder Team suchen..." autocomplete="off">
    <div id="pendingInputError" class="pending-input-error" style="display:none;"></div>
    <div id="searchDebugBox" class="search-debug-box" style="display:none;"></div>

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

    elif album_id == "vfl":
        for chapter in vfl_wall_chapters():
            visible_codes = [code for code in chapter["codes"] if filter_ok(filter_name, code, by_code)]
            if not visible_codes:
                continue

            chapter_title = chapter["title"]
            chapter_id = "chapter-" + chapter_title.lower().replace(" ", "-").replace("/", "-").replace("+", "plus")
            chapter_counter = sticker_counter_label(chapter["codes"], by_code, filter_name)
            chapter_complete = all(sticker_quantity_for_counter(by_code, code) > 0 for code in chapter["codes"])
            chapter_classes = "section-title album-chapter-title"
            if chapter_complete:
                chapter_classes += " chapter-complete chapter-collapsed"
            chapter_expanded = "false" if chapter_complete else "true"
            html += f'<h2 id="{chapter_id}" class="{chapter_classes}" role="button" tabindex="0" aria-expanded="{chapter_expanded}"><span>{chapter_title}</span><span>{chapter_counter}</span></h2>'
            html += '<div class="wall">'

            for code in visible_codes:
                klasse, text = klasse_und_text(code, by_code)
                if trigger and compact(code) == compact(trigger):
                    klasse += " trigger-slot"
                search_text = f"{code} {text} {chapter_title}".lower()
                html += f'<a class="slot {klasse}" data-code="{code}" data-display="{display_code(code)}" data-search="{search_text}" href="/sticker/{album_id}/{code}">{text}</a>'

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
        slot.classList.remove('search-hidden');
    }});

    clearHiddenStickerSections();

    updateVisibleStickerSections();
    updateStickerSearchFeedback('');
}}

function clearStickerFilter(){{
    document.querySelectorAll('.slot').forEach(function(slot){{
        slot.classList.remove('search-hidden');
    }});

    clearHiddenStickerSections();
    updateVisibleStickerSections();
    updateStickerSearchFeedback('');
}}

function getPendingCounts(){{
    const counts = {{}};

    selectedStickers.forEach(function(code){{
        counts[code] = (counts[code] || 0) + 1;
    }});

    return counts;
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
        slot.textContent || ''
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

    stickerSearchAliases(slot).forEach(function(alias){{
        const match = alias.match(/(\d+)$/);
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

    const queryIsOnlyNumbers = /^\d+$/.test(normalizedTerm);
    const queryHasLetters = /[A-Z]/.test(normalizedTerm);
    const queryHasNumbers = /\d/.test(normalizedTerm);

    if(queryIsOnlyNumbers){{
        return stickerSearchNumbers(slot).includes(normalizedTerm);
    }}

    if(queryHasLetters && queryHasNumbers){{
        return stickerSearchAliases(slot).includes(normalizedTerm);
    }}

    const search = slot.dataset.search || slot.textContent || '';
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

function slotIsVisible(slot){{
    return slot && !slot.classList.contains('search-hidden');
}}

function wallHasVisibleSlot(wall){{
    return Array.from(wall.querySelectorAll('.slot')).some(slotIsVisible);
}}

function clearHiddenStickerSections(){{
    document.querySelectorAll('.wall, .team-title, .section-title, .album-chapter-title').forEach(function(node){{
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
        let node = chapterTitle.nextElementSibling;
        while(node && !node.classList.contains('album-chapter-title') && !node.classList.contains('section-title')){{
            node.classList.add('collapse-section-hidden');
            node = node.nextElementSibling;
        }}
    }});
}}

function followingAreaHasVisibleSlot(startNode, stopMatcher){{
    let node = startNode.nextElementSibling;

    while(node && !stopMatcher(node)){{
        if(node.classList.contains('wall') && wallHasVisibleSlot(node)){{
            return true;
        }}

        node = node.nextElementSibling;
    }}

    return false;
}}

function updateVisibleStickerSections(){{
    document.querySelectorAll('.wall').forEach(function(wall){{
        wall.classList.toggle('search-section-hidden', !wallHasVisibleSlot(wall));
    }});

    document.querySelectorAll('.team-title').forEach(function(teamTitle){{
        const hasVisibleSlot = followingAreaHasVisibleSlot(teamTitle, function(node){{
            return node.classList.contains('team-title') || node.classList.contains('section-title');
        }});

        teamTitle.classList.toggle('search-section-hidden', !hasVisibleSlot);
    }});

    document.querySelectorAll('.section-title').forEach(function(sectionTitle){{
        const hasVisibleSlot = followingAreaHasVisibleSlot(sectionTitle, function(node){{
            return node.classList.contains('section-title');
        }});

        sectionTitle.classList.toggle('search-section-hidden', !hasVisibleSlot);
    }});

    updateChapterCollapseVisibility();
}}


if(stickerSearchInput){{
    stickerSearchInput.addEventListener('input', function(){{
        const term = this.value.trim();
        const slots = Array.from(document.querySelectorAll('.slot'));

        slots.forEach(function(slot){{
            const isMatch = matchesStickerSearch(slot, term);
            slot.classList.toggle('search-hidden', !isMatch);
        }});

        updateVisibleStickerSections();
        updateStickerSearchFeedback(term);
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

document.querySelectorAll('.album-chapter-title').forEach(function(chapterTitle){{
    chapterTitle.addEventListener('click', function(){{
        chapterTitle.classList.toggle('chapter-collapsed');
        updateChapterCollapseVisibility();
    }});

    chapterTitle.addEventListener('keydown', function(event){{
        if(event.key !== 'Enter' && event.key !== ' ') return;
        event.preventDefault();
        chapterTitle.classList.toggle('chapter-collapsed');
        updateChapterCollapseVisibility();
    }});
}});

updateChapterCollapseVisibility();

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


def add_sticker_quantity(con, user_id, album_id, code, amount=1):
    change_sticker_quantity(con, user_id, album_id, code, max(amount, 0))


def remove_sticker_quantity(con, user_id, album_id, code, amount=1):
    change_sticker_quantity(con, user_id, album_id, code, -max(amount, 0))


def complete_trade(con, trade):
    give_codes = json.loads(trade["give_codes"])
    get_codes = json.loads(trade["get_codes"])
    album_id = trade["album_id"]
    from_user_id = trade["from_user_id"]
    to_user_id = trade["to_user_id"]

    for code in give_codes:
        remove_sticker_quantity(con, from_user_id, album_id, code)
        add_sticker_quantity(con, to_user_id, album_id, code)

    for code in get_codes:
        add_sticker_quantity(con, from_user_id, album_id, code)
        remove_sticker_quantity(con, to_user_id, album_id, code)


def complete_trade_if_ready(con, trade):
    latest = con.execute(
        "SELECT * FROM trade_requests WHERE id=? AND status='accepted'",
        (trade["id"],)
    ).fetchone()

    if not latest or latest["from_confirmed"] != 1 or latest["to_confirmed"] != 1:
        return False

    complete_trade(con, latest)
    con.execute("UPDATE trade_requests SET status='completed' WHERE id=?", (latest["id"],))
    create_notification(
        con,
        latest["from_user_id"],
        "Tausch abgeschlossen",
        "Euer Tausch wurde in euren Sammlungen verbucht."
    )
    create_notification(
        con,
        latest["to_user_id"],
        "Tausch abgeschlossen",
        "Euer Tausch wurde in euren Sammlungen verbucht."
    )
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
        return "Anfrage offen"
    if status == "completed":
        return "Abgeschlossen"
    if status == "failed":
        return "Geplatzt"
    if status == "declined":
        return "Abgelehnt"
    if status == "accepted":
        my_confirmed = trade["to_confirmed"] if is_receiver else trade["from_confirmed"]
        other_confirmed = trade["from_confirmed"] if is_receiver else trade["to_confirmed"]
        if my_confirmed and not other_confirmed:
            return "Wartet auf andere Person"
        if other_confirmed and not my_confirmed:
            return "Andere Person hat bestätigt"
        return "Wartet auf Durchführung"

    return status


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


def trade_completion_actions(trade, partner_name, is_receiver=False):
    status = trade["status"]
    if status == "completed":
        return "<p><strong>Abgeschlossen:</strong> Die Sticker wurden automatisch gebucht.</p>"
    if status == "failed":
        return "<p><strong>Geplatzt:</strong> Keine Bestandsänderung.</p>"
    if status == "declined":
        return "<p><strong>Abgelehnt.</strong></p>"
    if status != "accepted":
        return ""

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

    meine_sticker = con.execute(
        "SELECT sticker_code, quantity FROM stickers WHERE user_id=? AND album_id=?",
        (current_user_id(), album_id)
    ).fetchall()

    meine_mengen = {s["sticker_code"]: s["quantity"] for s in meine_sticker}
    alle_codes = all_codes(album_id)

    meine_fehlenden = {code for code in alle_codes if meine_mengen.get(code, 0) == 0}
    meine_doppelten = {code for code in alle_codes if meine_mengen.get(code, 0) >= 2}

    incoming_requests = con.execute(
        """
        SELECT trade_requests.*, users.username AS sender_name
        FROM trade_requests
        JOIN users ON users.id = trade_requests.from_user_id
        WHERE trade_requests.album_id=? AND trade_requests.to_user_id=? AND trade_requests.status IN ('open', 'accepted', 'completed', 'failed', 'declined')
        ORDER BY trade_requests.created_at DESC
        """,
        (album_id, current_user_id())
    ).fetchall()

    outgoing_requests = con.execute(
        """
        SELECT trade_requests.*, users.username AS receiver_name
        FROM trade_requests
        JOIN users ON users.id = trade_requests.to_user_id
        WHERE trade_requests.album_id=? AND trade_requests.from_user_id=? AND trade_requests.status IN ('open', 'accepted', 'completed', 'failed', 'declined')
        ORDER BY trade_requests.created_at DESC
        """,
        (album_id, current_user_id())
    ).fetchall()

    incoming_count = len([trade for trade in incoming_requests if trade["status"] == "open"])
    outgoing_count = len([trade for trade in outgoing_requests if trade["status"] == "open"])

    if tab not in ("partners", "incoming", "outgoing"):
        tab = "incoming" if incoming_count > 0 else "partners"

    incoming_badge = f'<span class="trade-tab-badge danger">{incoming_count}</span>' if incoming_count else ""
    outgoing_badge = f'<span class="trade-tab-badge">{outgoing_count}</span>' if outgoing_count else ""
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
    <html><head>{style()}</head><body><div class="container">
    <a class="btn" href="/album/{album_id}">← Zurück</a>
    <h1>Tauschbörse</h1>
    <p class="subline">Finde Sammler, mit denen du Lücken schließen kannst.</p>

    <div class="trade-tabs">
        <a class="trade-tab-card {'active' if tab == 'partners' else ''}" href="/album/{album_id}/trades?tab=partners">
            <strong>Tauschpartner</strong>
        </a>
        <a class="trade-tab-card {'active' if tab == 'incoming' else ''}" href="/album/{album_id}/trades?tab=incoming">
            <strong>Anfragen an dich</strong>{incoming_badge}
        </a>
        <a class="trade-tab-card {'active' if tab == 'outgoing' else ''}" href="/album/{album_id}/trades?tab=outgoing">
            <strong>Deine Anfragen</strong>{outgoing_badge}
        </a>
    </div>
    """

    if tab == "incoming":
        if not incoming_requests:
            html += """
            <div class="card trade-empty-card">
                <h2>Keine offenen Anfragen an dich.</h2>
                <p>Neue Tauschanfragen erscheinen hier.</p>
            </div>
            """

        for trade in incoming_requests:
            give_codes = json.loads(trade["give_codes"] or "[]")
            get_codes = json.loads(trade["get_codes"] or "[]")
            is_receiver = True
            status_label = trade_status_label(trade, is_receiver)
            request_actions = trade_open_actions(trade) if trade["status"] == "open" else trade_completion_actions(
                trade,
                trade["sender_name"],
                is_receiver
            )

            html += f"""
            <div class="trade-partner-card trade-request-card">
                <div class="trade-partner-head">
                    <h2>{trade['sender_name']}</h2>
                    <span class="trade-partner-status ready">{status_label}</span>
                </div>
                <div class="trade-partner-stats">
                    <div>
                        <strong>{len(give_codes)}</strong>
                        <span>Du erhältst</span>
                    </div>
                    <div>
                        <strong>{len(get_codes)}</strong>
                        <span>Du gibst ab</span>
                    </div>
                </div>
                <div class="trade-request-summary">
                    <p><strong>Du erhältst:</strong> {trade_code_summary(give_codes)}</p>
                    <p><strong>Du gibst ab:</strong> {trade_code_summary(get_codes)}</p>
                    <p><strong>Status:</strong> {status_label}</p>
                </div>
                {request_actions}
            </div>
            """

    elif tab == "outgoing":
        if not outgoing_requests:
            html += """
            <div class="card trade-empty-card">
                <h2>Keine offenen gesendeten Anfragen.</h2>
                <p>Deine gestarteten Tauschanfragen erscheinen hier.</p>
            </div>
            """

        for trade in outgoing_requests:
            give_codes = json.loads(trade["give_codes"] or "[]")
            get_codes = json.loads(trade["get_codes"] or "[]")
            is_receiver = False
            status_label = trade_status_label(trade, is_receiver)
            request_actions = trade_completion_actions(trade, trade["receiver_name"], is_receiver)

            html += f"""
            <div class="trade-partner-card trade-request-card">
                <div class="trade-partner-head">
                    <h2>{trade['receiver_name']}</h2>
                    <span class="trade-partner-status muted">{status_label}</span>
                </div>
                <div class="trade-partner-stats">
                    <div>
                        <strong>{len(get_codes)}</strong>
                        <span>Du suchst</span>
                    </div>
                    <div>
                        <strong>{len(give_codes)}</strong>
                        <span>Du bietest an</span>
                    </div>
                </div>
                <div class="trade-request-summary">
                    <p><strong>Du suchst:</strong> {trade_code_summary(get_codes)}</p>
                    <p><strong>Du bietest an:</strong> {trade_code_summary(give_codes)}</p>
                    <p><strong>Status:</strong> {status_label}</p>
                </div>
                {request_actions}
            </div>
            """

    elif not andere_user:
        html += """
        <div class="card trade-empty-card">
            <h2>Noch keine Tauschpartner für dieses Album.</h2>
            <p>Sobald andere Nutzer dieses Album hinzufügen, erscheinen sie hier.</p>
        </div>
        """

    if tab == "partners":
        rendered_partner_count = 0
        for user in andere_user:
            if user["id"] in active_trade_partner_ids:
                continue

            andere_sticker = con.execute(
                "SELECT sticker_code, quantity FROM stickers WHERE user_id=? AND album_id=?",
                (user["id"], album_id)
            ).fetchall()

            andere_mengen = {s["sticker_code"]: s["quantity"] for s in andere_sticker}
            andere_fehlenden = {code for code in alle_codes if andere_mengen.get(code, 0) == 0}
            andere_doppelten = {code for code in alle_codes if andere_mengen.get(code, 0) >= 2}

            du_suchst = sorted(
                meine_fehlenden.intersection(andere_doppelten),
                key=lambda x: [int(part) if part.isdigit() else part for part in __import__('re').split(r'(\d+)', x)]
            )
            du_bietest_an = sorted(
                meine_doppelten.intersection(andere_fehlenden),
                key=lambda x: [int(part) if part.isdigit() else part for part in __import__('re').split(r'(\d+)', x)]
            )

            if len(du_suchst) == 0:
                continue

            rendered_partner_count += 1
            match_count = min(len(du_suchst), len(du_bietest_an))

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
                        <strong>{len(du_suchst)}</strong>
                        <span>Du suchst</span>
                    </div>
                    <div>
                        <strong>{len(du_bietest_an)}</strong>
                        <span>Du bietest an</span>
                    </div>
                </div>

                <a class="trade-partner-button" href="/album/{album_id}/trade/{user['id']}">Tausch starten</a>
            </div>
            """

        if rendered_partner_count == 0 and andere_user:
            html += """
            <div class="card trade-empty-card">
                <h2>Keine weiteren Tauschpartner.</h2>
                <p>Offene und angenommene Tauschanfragen findest du in den Anfrage-Bereichen.</p>
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

def code_sort_key(code):
    return [int(part) if part.isdigit() else part for part in __import__('re').split(r'(\d+)', code)]


def user_album_quantities(con, user_id, album_id):
    rows = con.execute(
        "SELECT sticker_code, quantity FROM stickers WHERE user_id=? AND album_id=?",
        (user_id, album_id)
    ).fetchall()
    return {row["sticker_code"]: row["quantity"] for row in rows}


def trade_search_text(code, section="", team=""):
    return f"{code} {display_code(code)} {section} {team}".lower()


def render_trade_wall(album_id, allowed_counts, mode):
    allowed_codes = set(allowed_counts.keys())
    slot_class = "missing trade-slot"
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
            f'<span>{display}</span></button>'
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


@app.route("/album/<album_id>/trade/<int:other_user_id>")
@app.route("/album/<album_id>/trades/<int:other_user_id>")
def trade_center(album_id, other_user_id):
    con = get_db()
    message = request.args.get("message", "")

    other_user = con.execute(
        "SELECT * FROM users WHERE id=?",
        (other_user_id,)
    ).fetchone()

    if not other_user:
        con.close()
        return redirect(f"/album/{album_id}/trades")

    meine_mengen = user_album_quantities(con, current_user_id(), album_id)
    andere_mengen = user_album_quantities(con, other_user_id, album_id)
    get_counts, give_counts = trade_candidates(album_id, meine_mengen, andere_mengen)

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
    error_html = f'<div class="notice notice-error"><h2>{message}</h2></div>' if message else ''

    html = f"""
    <html><head>{style()}</head><body><div class="container">
    <a class="btn" href="/album/{album_id}/trades">← Zurück</a>
    <h1>Tauschanfrage</h1>
    <p class="subline">Tauschen mit {other_user['username']}</p>
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

        <section class="trade-step" id="tradeStepGetReview" data-step="getReview">
            <div class="quick-action-card trade-inline-review">
                <h2>Du suchst</h2>
                <p class="trade-review-subline" id="tradeGetStepReviewCount">0 Sticker ausgewählt</p>
                <div class="pending-review-list" id="tradeGetStepReview"></div>
                <div class="pending-review-actions">
                    <button type="button" class="btn gray" data-next-step="get">Bearbeiten</button>
                    <button type="button" class="btn" data-confirm-step="get">Weiter zu deinen Doppelten</button>
                </div>
            </div>
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

        <section class="trade-step" id="tradeStepGiveReview" data-step="giveReview">
            <div class="quick-action-card trade-inline-review">
                <h2>Du bietest an</h2>
                <p class="trade-review-subline" id="tradeGiveStepReviewCount">0 Sticker ausgewählt</p>
                <div class="pending-review-list" id="tradeGiveStepReview"></div>
                <div class="pending-review-actions">
                    <button type="button" class="btn gray" data-next-step="give">Bearbeiten</button>
                    <button type="button" class="btn" data-confirm-step="give">Tauschanfrage prüfen</button>
                </div>
            </div>
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
        amount.value = tradeSelections[mode][code] || 0;
        amount.addEventListener('change', function(){{ setTradeCount(mode, code, amount.value); }});

        const plusButton = document.createElement('button');
        plusButton.type = 'button';
        plusButton.textContent = '+';
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
    renderTradeReviewList('get', 'tradeGetStepReview');
    renderTradeReviewList('give', 'tradeGiveStepReview');
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
    const getStepCount = document.getElementById('tradeGetStepReviewCount');
    const giveStepCount = document.getElementById('tradeGiveStepReviewCount');
    const getTotal = tradeTotal('get');
    const giveTotal = tradeTotal('give');
    const invalid = getTotal === 0 || giveTotal === 0 || giveTotal < getTotal;

    if(getStepCount) getStepCount.textContent = getTotal + ' Sticker ausgewählt';
    if(giveStepCount) giveStepCount.textContent = giveTotal + ' Sticker ausgewählt';

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
        const label = step === 'getReview' ? 'get' : step === 'giveReview' ? 'give' : step;
        pill.classList.toggle('active', pill.dataset.stepLabel === label);
    }});
    if(step === 'get' || step === 'give'){{
        activeTradeMode = step;
    }}
    document.body.classList.toggle('pending-active', step === 'get' || step === 'give');
    document.body.classList.toggle('trade-pending-active', step === 'get' || step === 'give');
    updateTradeSelectionBar();
    if(step === 'getReview' || step === 'giveReview' || step === 'final'){{
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
    primary.disabled = total === 0;
    bar.style.display = isSelectionStep ? 'flex' : 'none';
}}

document.querySelectorAll('[data-next-step]').forEach(function(button){{
    button.addEventListener('click', function(){{
        showTradeStep(button.dataset.nextStep);
    }});
}});

document.querySelectorAll('[data-confirm-step]').forEach(function(button){{
    button.addEventListener('click', function(){{
        if(button.dataset.confirmStep === 'get'){{
            showTradeStep('give');
            return;
        }}
        showTradeStep('final');
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
    showTradeStep(activeTradeMode === 'get' ? 'getReview' : 'giveReview');
}});

document.addEventListener('click', function(event){{
    const slot = event.target.closest('.trade-slot');
    if(!slot) return;

    if(slot.dataset.mode === 'get' && tradeTotal('get') >= maxReceiveSelection){{
        showTradeReceiveLimitError();
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

    </div></body></html>
    """

    con.close()
    return html


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

    if not give_codes or not get_codes:
        return redirect(f"{trade_url}?message={quote('Bitte wähle auf beiden Seiten mindestens einen Sticker aus.')}")

    if len(give_codes) < len(get_codes):
        return redirect(f"{trade_url}?message={quote('Du musst mindestens so viele Sticker anbieten, wie du suchst.')}")

    con = get_db()
    partner = con.execute("SELECT id FROM users WHERE id=?", (other_user_id,)).fetchone()
    if not partner:
        con.close()
        return redirect(f"/album/{album_id}/trades")

    meine_mengen = user_album_quantities(con, current_user_id(), album_id)
    andere_mengen = user_album_quantities(con, other_user_id, album_id)
    get_allowed, give_allowed = trade_candidates(album_id, meine_mengen, andere_mengen)

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
        "Neue Tauschanfrage",
        f"{sender['username']} möchte mit dir tauschen."
    )
    con.commit()
    con.close()

    return redirect(f"/trades?message=Tauschanfrage%20gesendet")


@app.route("/trade/<int:trade_id>/accept", methods=["POST"])
def accept_trade_request(trade_id):
    con = get_db()
    trade = con.execute(
        "SELECT * FROM trade_requests WHERE id=? AND to_user_id=? AND status='open'",
        (trade_id, current_user_id())
    ).fetchone()

    if trade:
        con.execute(
            "UPDATE trade_requests SET status='accepted', from_confirmed=0, to_confirmed=0 WHERE id=? AND to_user_id=? AND status='open'",
            (trade_id, current_user_id())
        )
        receiver = con.execute("SELECT username FROM users WHERE id=?", (current_user_id(),)).fetchone()
        create_notification(
            con,
            trade["from_user_id"],
            "Tauschanfrage angenommen",
            f"{receiver['username']} hat deine Tauschanfrage angenommen."
        )
        con.commit()

    con.close()
    return redirect(request.referrer or "/trades?message=Tauschanfrage%20angenommen")


@app.route("/trade/<int:trade_id>/decline", methods=["POST"])
def decline_trade_request(trade_id):
    con = get_db()
    trade = con.execute(
        "SELECT * FROM trade_requests WHERE id=? AND to_user_id=? AND status='open'",
        (trade_id, current_user_id())
    ).fetchone()

    if trade:
        con.execute(
            "UPDATE trade_requests SET status='declined' WHERE id=? AND to_user_id=? AND status='open'",
            (trade_id, current_user_id())
        )
        receiver = con.execute("SELECT username FROM users WHERE id=?", (current_user_id(),)).fetchone()
        create_notification(
            con,
            trade["from_user_id"],
            "Tauschanfrage abgelehnt",
            f"{receiver['username']} hat deine Tauschanfrage abgelehnt."
        )
        con.commit()

    con.close()
    return redirect(request.referrer or "/trades?message=Tauschanfrage%20abgelehnt")


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
    <h1>🤝 Offene Tauschanfragen</h1>
    <p class="subline">Anfragen, die später nach echtem Treffen abgeschlossen werden.</p>
    {f'<div class="notice notice-success"><h2>{message}</h2></div>' if message else ''}
    """

    if not rows:
        html += """
        <div class="card">
            <h2>Noch keine Tauschanfragen</h2>
            <p>Öffne ein Album und starte über die Tauschbörse eine Anfrage.</p>
        </div>
        """

    for trade in rows:
        give_codes = json.loads(trade["give_codes"])
        get_codes = json.loads(trade["get_codes"])
        is_receiver = trade["to_user_id"] == current_user_id()
        status = trade["status"]

        if is_receiver:
            headline = f"{trade['sender_name']} möchte mit dir tauschen"
            partner_name = trade["sender_name"]
            du_bekommst = give_codes
            du_gibst = get_codes
        else:
            headline = f"Anfrage an {trade['receiver_name']}"
            partner_name = trade["receiver_name"]
            du_bekommst = get_codes
            du_gibst = give_codes

        status_label = trade_status_label(trade, is_receiver)
        actions = ""
        if is_receiver and status == "open":
            actions = trade_open_actions(trade)
        elif status in ("accepted", "completed", "failed", "declined"):
            actions = trade_completion_actions(trade, partner_name, is_receiver)
        else:
            actions = "<p><strong>Wartet auf Antwort</strong></p>"

        html += f"""
        <div class="card">
            <h2>{headline}</h2>
            <p><strong>Album:</strong> {trade['album_name']}</p>
            <p><strong>Status:</strong> {status_label}</p>

            <h3>Du suchst</h3>
            <p>{', '.join(display_code(c) for c in du_bekommst)}</p>

            <h3>Du bietest an</h3>
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
    return redirect("/trades?message=Bitte%20die%20Tauschanfrage%20%C3%BCber%20den%20Button%20annehmen.")


@app.route("/trade/<int:trade_id>/confirm", methods=["POST"])
def confirm_trade_done(trade_id):
    con = get_db()
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

    if trade["from_user_id"] == current_user_id():
        con.execute("UPDATE trade_requests SET from_confirmed=1 WHERE id=?", (trade_id,))
    else:
        con.execute("UPDATE trade_requests SET to_confirmed=1 WHERE id=?", (trade_id,))

    if complete_trade_if_ready(con, trade):
        con.commit()
        con.close()
        return redirect("/trades?message=Tausch%20abgeschlossen")

    con.commit()
    con.close()
    return redirect(request.referrer or "/trades?message=Tausch%20vormarkiert")


@app.route("/trade/<int:trade_id>/fail", methods=["POST"])
def fail_trade_done(trade_id):
    con = get_db()
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

    con.execute(
        """
        UPDATE trade_requests
        SET status='failed'
        WHERE id=? AND status='accepted' AND (from_user_id=? OR to_user_id=?)
        """,
        (trade_id, current_user_id(), current_user_id())
    )
    canceller = con.execute("SELECT username FROM users WHERE id=?", (current_user_id(),)).fetchone()
    other_user_id = trade["to_user_id"] if trade["from_user_id"] == current_user_id() else trade["from_user_id"]
    create_notification(
        con,
        other_user_id,
        "Tausch geplatzt",
        f"{canceller['username']} hat den Tausch als geplatzt markiert."
    )
    con.commit()
    con.close()
    return redirect("/trades?message=Tausch%20geplatzt")



@app.route("/trades/<int:trade_id>/decline")
def decline_trade(trade_id):
    return redirect("/trades?message=Bitte%20die%20Tauschanfrage%20%C3%BCber%20den%20Button%20ablehnen.")


# --- Confirm/cancel trade routes ---

@app.route("/trades/<int:trade_id>/confirm")
def confirm_trade(trade_id):
    return redirect("/trades?message=Bitte%20den%20Tausch%20%C3%BCber%20den%20Button%20best%C3%A4tigen.")


@app.route("/trades/<int:trade_id>/cancel")
def cancel_trade(trade_id):
    return redirect("/trades?message=Bitte%20den%20Tausch%20%C3%BCber%20den%20Button%20als%20geplatzt%20markieren.")


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
    con = get_db()

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

    html = f"""
    <html><head>{style()}</head><body><div class="container">
    {app_header("Trophäenschrank", "Deine abgestaubten Sammlr-Ziele.")}
    """

    html += render_global_trophy_grid(global_sticker_trophaeen(), sticker_gesamt, "gesammelte Sticker")
    html += render_global_trophy_grid(global_duplicate_trophaeen(), doppelte_gesamt, "doppelte Sticker")
    html += render_global_trophy_grid(global_trade_trophaeen(), completed_trades, "abgeschlossene Tausche")

    html += bottom_nav("trophaeen")
    html += "</div></body></html>"
    return html

@app.route("/statistik")
def statistik():
    user_id = current_user_id()
    con = get_db()

    alben = con.execute(
        """
        SELECT albums.*
        FROM albums
        JOIN user_albums ON user_albums.album_id = albums.id
        WHERE user_albums.user_id=?
        """,
        (user_id,)
    ).fetchall()

    stickers = con.execute(
        "SELECT sticker_code, quantity, duplicates FROM stickers WHERE user_id=?",
        (user_id,)
    ).fetchall()

    completed_trades = con.execute(
        """
        SELECT give_codes, get_codes
        FROM trade_requests
        WHERE status='completed' AND (from_user_id=? OR to_user_id=?)
        """,
        (user_id, user_id)
    ).fetchall()

    con.close()

    album_started = len(alben)
    album_finished = 0
    missing_total = 0
    album_trophies = 0

    for album in alben:
        _, _, gesammelt, _, _, total = lade_album(album["id"])
        if gesammelt >= total:
            album_finished += 1

        missing_total += max(total - gesammelt, 0)
        _, _, trophies = trophy_status(album["id"], gesammelt, total)
        album_trophies += len([t for t in trophies if gesammelt >= t[0]])

    sticker_total = sum(row["quantity"] for row in stickers)
    duplicate_total = sum(row["duplicates"] for row in stickers)
    completed_trade_count = len(completed_trades)
    traded_sticker_count = 0

    for trade in completed_trades:
        traded_sticker_count += len(json.loads(trade["give_codes"] or "[]"))
        traded_sticker_count += len(json.loads(trade["get_codes"] or "[]"))

    global_trophies = (
        len([t for t in global_trade_trophaeen() if completed_trade_count >= t[0]]) +
        len([t for t in global_sticker_trophaeen() if sticker_total >= t[0]]) +
        len([t for t in global_duplicate_trophaeen() if duplicate_total >= t[0]])
    )
    trophy_total = album_trophies + global_trophies
    trade_word = "Tausch" if completed_trade_count == 1 else "Tausche"

    return f"""
    <html><head>{style()}</head><body><div class="container">
    {app_header("Meine Statistik", "Dein Sammlr-Zwischenstand.")}

    <div class="statistics-card">
        <div class="statistics-block">
            <h2>Alben</h2>
            <p>{album_started} begonnen</p>
            <p>{album_finished} beendet</p>
        </div>

        <div class="statistics-block">
            <h2>Sticker</h2>
            <p>{sticker_total} gesammelt</p>
            <p>{missing_total} fehlen</p>
            <p>{duplicate_total} doppelt</p>
        </div>

        <div class="statistics-block">
            <h2>Tauschbörse</h2>
            <p>{completed_trade_count} {trade_word} abgeschlossen</p>
            <p>{traded_sticker_count} Sticker getauscht</p>
        </div>

        <div class="statistics-block">
            <h2>Trophäen</h2>
            <p>{trophy_total} abgestaubt</p>
        </div>
    </div>

    {bottom_nav("statistik")}
    </div></body></html>
    """

@app.route("/profil")
def profil():
    user_id = current_user_id()
    con = get_db()

    user = con.execute(
        "SELECT username, name FROM users WHERE id=?",
        (user_id,)
    ).fetchone()

    username = user["username"] if user and user["username"] else session.get("username", "Unbekannt")
    name = user["name"] if user and user["name"] else username
    initial = (name or username or "S").strip()[:1].upper()

    con.close()

    return f"""
    <html><head>{style()}</head><body><div class="container">
    <div class="profile-header">
        <div>
            <h1>Profil</h1>
            <p>Dein Sammlr-Ausweis.</p>
        </div>
        <a class="profile-logout" href="/logout">Abmelden</a>
    </div>

    <div class="profile-card profile-pass-card">
        <div class="profile-identity">
            <div class="profile-avatar"><span>{initial}</span></div>
            <div class="profile-name">
                <h2>{name}</h2>
                <p>@{username}</p>
            </div>
        </div>
    </div>

    <div class="profile-link-list">
        <a class="profile-link-card" href="/">
            <strong>Meine Alben</strong>
            <span>Zur Sammlr Zentrale</span>
        </a>
        <a class="profile-link-card" href="/statistik">
            <strong>Meine Statistik</strong>
            <span>Sticker, Doppelte und Trades</span>
        </a>
        <a class="profile-link-card" href="/trophaeen">
            <strong>Meine Trophäen</strong>
            <span>Abgestaubte Ziele und nächste Meilensteine</span>
        </a>
    </div>

    <div class="profile-account-section">
        <h2>Konto</h2>
        <div class="profile-account-actions">
            <a class="profile-account-button" href="/profil/name">Name bearbeiten</a>
            <a class="profile-account-button" href="/profil/username">Benutzername bearbeiten</a>
            <a class="profile-account-button" href="/profil/password">Passwort ändern</a>
        </div>
    </div>

    <div class="profile-account-section profile-danger-section">
        <h2>Gefahrenzone</h2>
        <button type="button" class="profile-account-button danger" onclick="openAccountDeleteDialog()">Account löschen</button>
    </div>

    <div class="account-delete-backdrop" id="accountDeleteDialog" aria-hidden="true">
        <div class="account-delete-dialog" role="dialog" aria-modal="true" aria-labelledby="accountDeleteTitle">
            <h2 id="accountDeleteTitle">Deinen Sammlr Account wirklich löschen?</h2>
            <p>Alle Alben<br>Alle Sticker<br>Alle Trophäen<br>Alle Tauschanfragen</p>
            <p>werden dauerhaft entfernt.</p>
            <div class="account-delete-actions">
                <button type="button" class="btn gray" onclick="closeAccountDeleteDialog()">Abbrechen</button>
                <form method="POST" action="/profil/delete">
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
        con.execute("UPDATE users SET name=? WHERE id=?", (name, user_id))
        con.commit()
        con.close()
        return redirect("/profil")

    user = con.execute("SELECT name, username FROM users WHERE id=?", (user_id,)).fetchone()
    con.close()
    name = user["name"] if user and user["name"] else ""

    return f"""
    <html><head>{style()}</head><body><div class="container">
    <a class="btn" href="/profil">← Zurück</a>
    <div class="profile-account-form">
        <h1>Name bearbeiten</h1>
        {f'<div class="auth-error">{message}</div>' if message else ''}
        <form method="POST" class="auth-form">
            <label>Name</label>
            <input name="name" value="{name}" autocomplete="name">
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
        if not username:
            error = "Bitte gib einen Benutzernamen ein."
        else:
            try:
                con.execute("UPDATE users SET username=? WHERE id=?", (username, user_id))
                con.commit()
                session["username"] = username
                con.close()
                return redirect("/profil")
            except sqlite3.IntegrityError:
                error = "Benutzername ist bereits vergeben."

    user = con.execute("SELECT username FROM users WHERE id=?", (user_id,)).fetchone()
    con.close()
    username = user["username"] if user and user["username"] else session.get("username", "")

    return f"""
    <html><head>{style()}</head><body><div class="container">
    <a class="btn" href="/profil">← Zurück</a>
    <div class="profile-account-form">
        <h1>Benutzername bearbeiten</h1>
        {f'<div class="auth-error">{error}</div>' if error else ''}
        <form method="POST" class="auth-form">
            <label>Benutzername</label>
            <input name="username" value="{username}" autocomplete="username">
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
        user = con.execute("SELECT password FROM users WHERE id=?", (user_id,)).fetchone()

        if not user or user["password"] != current_password:
            error = "Aktuelles Passwort stimmt nicht."
        elif not new_password:
            error = "Bitte gib ein neues Passwort ein."
        elif new_password != repeat_password:
            error = "Passwörter stimmen nicht überein."
        else:
            con.execute("UPDATE users SET password=? WHERE id=?", (new_password, user_id))
            con.commit()
            con.close()
            return redirect("/profil")

    con.close()
    return f"""
    <html><head>{style()}</head><body><div class="container">
    <a class="btn" href="/profil">← Zurück</a>
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


@app.route("/profil/delete", methods=["POST"])
def profil_delete():
    user_id = current_user_id()
    con = get_db()

    con.execute("DELETE FROM stickers WHERE user_id=?", (user_id,))
    con.execute("DELETE FROM user_albums WHERE user_id=?", (user_id,))
    con.execute("DELETE FROM unlocked_trophies WHERE user_id=?", (user_id,))
    con.execute("DELETE FROM trade_requests WHERE from_user_id=? OR to_user_id=?", (user_id, user_id))
    con.execute("DELETE FROM notifications WHERE user_id=?", (user_id,))
    con.execute("UPDATE users SET favorite_album_id=NULL WHERE favorite_album_id IS NOT NULL AND id=?", (user_id,))
    con.execute("DELETE FROM users WHERE id=?", (user_id,))
    con.commit()
    con.close()

    session.clear()
    return redirect("/login")


init_db()
app.run(debug=True, host="0.0.0.0", port=8080)
