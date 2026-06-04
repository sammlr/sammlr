import sqlite3
from flask import Flask, request, redirect, session
import json
from em24_data import build_em24
from wm26_data import build_wm26
from Database.database import current_user_id, get_db
from services.notifications import create_notification, unread_notifications
from urllib.parse import quote

app = Flask(__name__)
app.secret_key = "sammlr_dev_secret"





def init_db():
    con = get_db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

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

   

# --- Notification helper ---
def create_notification(con, user_id, title, body):
    con.execute(
        """
        INSERT INTO notifications (user_id, title, body, is_read)
        VALUES (?, ?, ?, 0)
        """,
        (user_id, title, body)
    )



def style():
    return '<link rel="stylesheet" href="/static/style.css">'


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
    freche_100er_namen = [
        "Pack-Pirat",
        "Klebekönig",
        "Album-Akrobat",
        "Sticker-Sprinter",
        "Glitzer-Gambler",
        "Tütchen-Taktiker",
        "Sammel-Satellit",
        "Karten-Kapitän",
        "Duplikat-Dompteur",
        "Album-Orakel",
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
    return [
        (1, "Erster Doppelgänger"),
        (5, "Doppelgänger"),
        (10, "Double Trouble"),
        (25, "Twincoolector"),
        (50, "Double Sieger"),
        (100, "Duplikat-Dealer"),
        (250, "Patch-Horter"),
        (500, "Doppelter Wahnsinn"),
    ]


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

    for ziel, titel in album_doppelte_trophaeen():
        if doppelte < ziel:
            candidates.append({
                "title": titel,
                "distance": ziel - doppelte,
                "text": f"Noch {ziel - doppelte} doppelte Sticker sammeln",
                "category": "Doppelte-Trophäe"
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

def erreichte_trophaeen(album_id):
    album, by_code, gesammelt, doppelte, prozent, total = lade_album(album_id)
    last, next_trophy, trophies = trophy_status(album_id, gesammelt, total)

    erreicht = [titel for ziel, titel in trophies if gesammelt >= ziel]

    for ziel, titel in album_doppelte_trophaeen():
        if doppelte >= ziel:
            erreicht.append(titel)

    if album_id == "em24":
        for titel, beschreibung, ok in em24_spezial_trophaeen(by_code):
            if ok:
                erreicht.append(titel)

    return erreicht


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

        return "Login fehlgeschlagen"

    return """
    <html>
    <body style="font-family:sans-serif;padding:40px;">
        <h1>Sammlr Login</h1>

        <form method="POST">
            <input name="username" placeholder="Benutzername"><br><br>
            <input name="password" type="password" placeholder="Passwort"><br><br>
            <button type="submit">Login</button>
        </form>
<br><br>
<a href="/register">Noch kein Konto? Jetzt registrieren</a>
    </body>
    </html>
    """
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        con = get_db()

        try:
            con.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
            )
            con.commit()
            con.close()

            return redirect("/login")

        except:
            con.close()
            return "Benutzer existiert bereits"

    return """
    <html>
    <body style="font-family:sans-serif;padding:40px;">
        <h1>Sammlr Registrierung</h1>

        <form method="POST">
            <input name="username" placeholder="Benutzername"><br><br>
            <input name="password" type="password" placeholder="Passwort"><br><br>
            <button type="submit">Registrieren</button>
        </form>

    </body>
    </html>
    """

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/")
def startseite():
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

    latest_transfers = con.execute(
        """
        SELECT trade_requests.*,
               sender.username AS sender_name,
               receiver.username AS receiver_name,
               albums.name AS album_name
        FROM trade_requests
        JOIN users sender ON sender.id = trade_requests.from_user_id
        JOIN users receiver ON receiver.id = trade_requests.to_user_id
        JOIN albums ON albums.id = trade_requests.album_id
        WHERE trade_requests.status='completed'
        ORDER BY trade_requests.created_at DESC
        LIMIT 5
        """
    ).fetchall()

    notifications = unread_notifications(con, current_user_id())
    con.close()

    infos = [
        (album, gesammelt, doppelte, prozent, total)
        for album, _, gesammelt, doppelte, prozent, total in (
            lade_album(album["id"]) for album in alben
        )
    ]

    html = f"""
    <html><head>{style()}</head><body><div class="container">
    """
    # Add transfer ticker block after hero-header
    ticker_items = []
    for transfer in latest_transfers:
        give_codes = json.loads(transfer["give_codes"])
        get_codes = json.loads(transfer["get_codes"])
        sticker_count = len(give_codes) + len(get_codes)
        ticker_items.append(
            f"+++ TRANSFERNEWS +++ {transfer['sender_name']} ↔ {transfer['receiver_name']}: {sticker_count} Sticker haben bei {transfer['album_name']} die Seiten gewechselt"
        )

    if ticker_items:
        ticker_text = "".join(f'<span class="ticker-item">{item}</span>' for item in ticker_items)
        html += f"""
        <div class="transfer-ticker">
            <div class="ticker-track">
                {ticker_text}
            </div>
        </div>
        """

    if notifications:
        html += """
        <div class="card">
            <h2>Neue Meldungen</h2>
        """
        for note in notifications:
            html += f"""
            <div class="notice notice-success">
                <h2>{note['title']}</h2>
                <p>{note['body']}</p>
                <a class="btn" href="/notifications/{note['id']}/read">Gelesen</a>
            </div>
            """
        html += "</div>"
    

    html += """
    <div class="home-intro">
        <h1>Meine Sammlung</h1>
        <p>Deine aktiven Alben, abgeschlossenen Sammlungen und kommenden Collectr-Welten.</p>
    </div>
    """

    if not infos:
        html += """
        <div class="card">
            <h2>Noch keine Alben</h2>
            <p>Füge dein erstes Album hinzu und starte deine Sammlung.</p>
            <a class="btn" href="/alben/hinzufuegen">Album hinzufügen</a>
        </div>
        """

    html += """
    <h2 class="home-section-title">Aktive Alben</h2>
    <p class="subline">Hier sammelst du gerade weiter.</p>
    """

    for album, gesammelt, doppelte, prozent, total in infos:
        if prozent < 100:
            html += album_card(album, gesammelt, prozent, total)

    html += """
    <h2 class="home-section-title">Vitrine</h2>
    <p class="subline">Abgeschlossene Alben, auf die man kurz stolz gucken darf.</p>
    """

    for album, gesammelt, doppelte, prozent, total in infos:
        if prozent == 100:
            html += album_card(album, gesammelt, prozent, total)

    
    html += """
    
    <script>
    function closePopup(){
        document.querySelectorAll('.trophy-popup-overlay').forEach(function(popup){
            popup.remove();
        });
    }
    </script>
    """
    
    html += "</div></body></html>"

    return html


def album_card(album, gesammelt, prozent, total):
    return f"""
    <div class="card">
        <a class="album-card" href="/album/{album['id']}">
            <div class="album-cover">{album['cover']}</div>
            <div>
                <h2>{album['name']}</h2>
                <p>{album['season']}</p>
                <div class="progress"><div class="progress-bar" style="width:{prozent}%;"></div></div>
                <p>{gesammelt} / {total} Sticker</p>
            </div>
            <div class="album-percent">
    <div class="album-percent-circle">
        {prozent}%
    </div>
</div>
        </a>
    </div>
    """



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
        trophy_popup = f"""
    if anzahl > 1:
        trophy_text = f"{anzahl} neue Trophäen freigeschaltet!"
    else:
        trophy_text = "Neue Trophäe freigeschaltet!"
        <div class="trophy-popup-overlay">
            <div class="trophy-popup">

                <div class="trophy-popup-patch">
                🏆
                </div>
 
                <h2>Neuer Patch erhalten</h2>

                <p>
                    {"<strong>Neuer Patch freigeschaltet</strong><br>" + trophy if "," not in trophy else f"{trophy_text}<br>{trophy.replace(',', '<br>')}"}
                </p>

                <div class="popup-actions">
                    <a href="/album/{album_id}" class="popup-button popup-secondary">
                        Okay
                    </a>

                    <a href="/album/{album_id}/trophaeen" class="popup-button">
                        Trophäenschrank
                    </a>
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
    last_trophy, next_trophy, trophies = trophy_status(album_id, gesammelt, total)
    nearest_trophy = nearest_album_trophy(album_id)

    html = f"""
    <html><head>{style()}</head><body><div class="container">
    <a class="btn" href="/">← Hauptmenü</a>
    <h1>{album['name']}</h1>
    <p class="subline">{album['season']}</p>

    {f'<div class="notice {"notice-error" if "nicht vorhanden" in message else "notice-duplicate" if "doppelt" in message else "notice-success"}"><h2>{message}</h2><p>Vertippt?</p><a class="btn gray" href="/undo">↩ Rückgängig machen</a></div>' if message and ("hinzugefügt" in message or "doppelt" in message or "entfernt" in message) else f'<div class="notice {"notice-error" if "nicht vorhanden" in message else "notice-duplicate" if "doppelt" in message else "notice-success"}"><h2>{message}</h2></div>' if message else ''}
    <div class="album-tools">

    """
    html += f"""
<div class="card">
    <h2>Sticker verwalten</h2>

    <div class="mode-switch">
        <a class="mode-pill btn green {'active' if mode == 'add' else ''}" href="/album/{album_id}?filter={filter_name}&mode=add">Hinzufügen</a>
        <a class="mode-pill btn gray {'active' if mode == 'remove' else ''}" href="/album/{album_id}?filter={filter_name}&mode=remove">Entfernen</a>
        <a class="mode-pill btn orange {'active' if mode == 'trade' else ''}" href="/album/{album_id}?filter={filter_name}&mode=trade">Tauschen</a>
    </div>
"""

    if mode == "add":
        html += f'''
        <form method="POST">
            <input type="hidden" name="filter" value="{filter_name}">
            <div class="smart-input-wrap">
                <span id="smart-sticker-ghost" class="smart-input-ghost"></span>
                <input id="smart-sticker-input" name="sticker" placeholder="Sticker ID hinzufügen" autocomplete="off" autofocus>
            </div>
            <button class="btn green" name="aktion" value="add" type="submit">Hinzufügen</button>
        </form>
        '''

    elif mode == "remove":
        html += f'''
        <form method="POST">
            <input type="hidden" name="filter" value="{filter_name}">
            <input name="sticker" placeholder="Sticker ID entfernen" autofocus>
            <button class="btn gray" name="aktion" value="remove" type="submit">Entfernen</button>
        </form>
        '''

    else:
        html += f'''
        <form method="POST">
            <input type="hidden" name="filter" value="{filter_name}">
            <input name="trade_out" placeholder="Sticker abgeben" autofocus>
            <input name="trade_in" placeholder="Sticker einsammeln">
            <button class="btn orange" name="aktion" value="trade" type="submit">Tausch speichern</button>
        </form>
        '''

    html += '</div>\n'

    if mode == "add":
        html += f'''
        <script>
        (function() {{
            const input = document.getElementById("smart-sticker-input");
            const ghost = document.getElementById("smart-sticker-ghost");
            if (!input || !ghost) return;

            const prefixKey = "sammlr_prefix_{album_id}";
            const smartActive = {str(smart_prefix_active).lower()};

            if (!smartActive) {{
                localStorage.removeItem(prefixKey);
            }}

            function getPrefix() {{
                return localStorage.getItem(prefixKey) || "";
            }}

            function updateGhost() {{
                const prefix = getPrefix();
                const value = input.value.trim().toUpperCase();

                if (!smartActive || !prefix) {{
                    ghost.style.display = "none";
                    input.style.paddingLeft = "16px";
                    input.style.color = "#1b1620";
                    input.placeholder = "Sticker ID hinzufügen";
                    return;
                }}

                if (value === "") {{
                    ghost.textContent = prefix;
                    ghost.style.display = "block";
                    input.placeholder = "";
                    input.style.paddingLeft = (ghost.offsetWidth + 20) + "px";
                    input.style.color = "#1b1620";
                    return;
                }}

                if (/^\\d+$/.test(value)) {{
                    ghost.textContent = prefix + value;
                    ghost.style.display = "block";
                    input.placeholder = "";
                    input.style.paddingLeft = "16px";
                    input.style.color = "transparent";
                    return;
                }}

                ghost.style.display = "none";
                input.style.paddingLeft = "16px";
                input.style.color = "#1b1620";
                input.placeholder = "Sticker ID hinzufügen";
            }}

            input.addEventListener("input", updateGhost);
            input.addEventListener("focus", updateGhost);

            input.form.addEventListener("submit", function() {{
                let value = input.value.trim().toUpperCase();
                const prefix = getPrefix();

                if (prefix && /^\\d+$/.test(value)) {{
                    value = prefix + value;
                    input.value = value;
                }}

                const match = value.match(/^([A-ZÄÖÜ]+)[\\s-]*\\d+$/);
                if (match) {{
                    localStorage.setItem(prefixKey, match[1]);
                }}
            }});

            updateGhost();
        }})();
        </script>
        '''

    html += f"""

    <a class="trophy-card" href="/album/{album_id}/trophaeen">
        <div class="card">
            <h2>🏆 Nächstes Ziel</h2>
            <p><strong>{nearest_trophy['title']}</strong></p>
            <p>{nearest_trophy['text']}</p>
            <p class="subline">{nearest_trophy['category']}</p>
        </div>
    </a>
    <a class="trophy-card" href="/album/{album_id}/trades">
        <div class="card">
            <h2>🤝 Trade-Matching</h2>
            <p>Finde Sammler mit passenden Stickern.</p>
            <p><strong>V1 Vorschau</strong></p>
        </div>
    </a>

</div>

    <div class="card">
        <h2>Albumübersicht</h2>
        <p>{gesammelt} / {total} Sticker gesammelt</p>
        <p>{doppelte} doppelte Sticker</p>
        <div class="progress"><div class="progress-bar" style="width:{prozent}%;"></div></div>
        <br>
        <a class="btn btn-all {'btn-active' if filter_name == 'all' else ''}" href="/album/{album_id}">Gesamtansicht</a>
        <a class="btn btn-missing {'btn-active' if filter_name == 'missing' else ''}" href="/album/{album_id}?filter=missing">Fehlende</a>
        <a class="btn btn-owned {'btn-active' if filter_name == 'owned' else ''}" href="/album/{album_id}?filter=owned">Vorhandene</a>
        <a class="btn btn-duplicate {'btn-active' if filter_name == 'duplicate' else ''}" href="/album/{album_id}?filter=duplicate">Doppelte</a>
        
    </div>


    <div class="card">
        <h2>Meine Sammlung</h2>

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
            html += f'<a class="slot {klasse}" href="/sticker/{album_id}/{code}">{text}</a>'
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
            html += f'<a class="slot {klasse}" href="/sticker/{album_id}/{code}">{text}</a>'
        html += "</div>"
    html += trophy_popup
    html += "</div></div></body></html>"
    return html


@app.route("/sticker/<album_id>/<path:code>")
def sticker_detail(album_id, code):
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
    <div class="card">
        <h1>Sticker {display_code(code)}</h1>
        <div class="slot {farbe}" style="width:130px;font-size:22px;margin-bottom:20px;">{display_code(code)}</div>
        <h2>{status}</h2>
        <p>Anzahl: {q}</p>
        <a class="btn" href="/add/{album_id}/{code}">+ Hinzufügen</a>
        <a class="btn" href="/remove/{album_id}/{code}">- Entfernen</a>
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
    code = data["code"]
    action = data["action"]
    current_filter = data.get("filter", "all")

    con = get_db()
    cur = con.cursor()

    row = con.execute(
        "SELECT * FROM stickers WHERE user_id=? AND album_id=? AND sticker_code=?",
        (current_user_id(), album_id, code)
    ).fetchone()

    if action == "add":
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

    elif action == "remove":
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

    session.pop("last_action", None)

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
    <h1>🤝 Trade-Matching</h1>
    <p class="subline">Andere Sammler mit möglichen Tauschaktionen in diesem Album.</p>
    """

    if not andere_user:
        html += """
        <div class="card">
            <h2>Noch keine weiteren Sammler für dieses Album</h2>
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

        bekommst_liste = ", ".join(display_code(code) for code in du_bekommst[:12]) or "Noch nichts Passendes"
        gibst_liste = ", ".join(display_code(code) for code in du_gibst[:12]) or "Noch nichts Passendes"

        if len(du_bekommst) > 12:
            bekommst_liste += f" … +{len(du_bekommst) - 12} weitere"

        if len(du_gibst) > 12:
            gibst_liste += f" … +{len(du_gibst) - 12} weitere"

        badge = f"🤝 {match_count} mögliche Trades" if match_count > 0 else "Noch kein direkter Match"

        html += f"""
        <div class="card">
            <h2>{user['username']}</h2>
            <p><strong>{badge}</strong></p>

            <div class="stat-grid-mini">
                <div class="mini-box">
                    <div class="mini-big">{len(du_bekommst)}</div>
                    <p>kannst du bekommen</p>
                </div>
                <div class="mini-box">
                    <div class="mini-big">{len(du_gibst)}</div>
                    <p>kannst du geben</p>
                </div>
            </div>

            <h3>Du bekommst</h3>
            <p>{bekommst_liste}</p>

            <h3>Du gibst</h3>
            <p>{gibst_liste}</p>
            <a class="btn" href="/album/{album_id}/trades/{user['id']}">Tradecenter öffnen</a>
        </div>
        """

    html += "</div></body></html>"
    con.close()
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
    filter_name = request.args.get("filter", "all")
    show_album = filter_name in ("all", "album")
    show_duplicates = filter_name in ("all", "duplicates")
    last_trophy, next_trophy, trophies = trophy_status(album_id, gesammelt, total)

    html = f"""
    <html><head>{style()}</head><body><div class="container">
    <a class="btn" href="/album/{album_id}">← Zurück</a>
    <h1>Album-Trophäen</h1>
<div class="filter-bar">
    <a href="?filter=all" class="filter-btn {'active' if filter_name == 'all' else ''}">Alle</a>
    <a href="?filter=album" class="filter-btn album-tab {'active' if filter_name == 'album' else ''}">Album-Trophäen</a>
    <a href="?filter=duplicates" class="filter-btn duplicate-tab {'active' if filter_name == 'duplicates' else ''}">Doppelte-Trophäen</a>
</div>
    <div class="notice">
        <h2>Letzte Auszeichnung: {last_trophy}</h2>
        <p>Nächste Trophäe: <strong>{next_trophy}</strong></p>
    </div>
    """
    if show_album:
        html += render_trophy_steps(trophies, gesammelt, "blue", "Sticker gesammelt")

    if show_duplicates:
        html += "<h2>Doppelte-Trophäen</h2>"
        html += render_trophy_steps(album_doppelte_trophaeen(), doppelte, "purple", "doppelte Sticker in diesem Album")

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
        duplicate_unlocked = len([t for t in album_doppelte_trophaeen() if doppelte >= t[0]])
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
    <a class="btn" href="/">← Zurück</a>
    <h1>Globaler Trophäenschrank</h1>

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

    html += "</div></body></html>"
    return html


@app.route("/statistik")
def statistik():
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

    trades = con.execute(
        """
        SELECT *
        FROM trade_requests
        WHERE from_user_id=? OR to_user_id=?
        """,
        (current_user_id(), current_user_id())
    ).fetchall()

    con.close()

    alben_gesamt = len(alben)
    alben_aktiv = 0
    alben_beendet = 0

    sticker_gesamt = sum(s["quantity"] for s in stickers)
    doppelte_gesamt = sum(s["duplicates"] for s in stickers)
    gesammelt_gesamt = 0
    fehlend_gesamt = 0

    album_trophies = 0
    doppelte_trophies = 0

    for album in alben:
        album_data, by_code, gesammelt, doppelt, prozent, total = lade_album(album["id"])

        gesammelt_gesamt += gesammelt
        fehlend_gesamt += total - gesammelt

        if prozent == 100:
            alben_beendet += 1
        else:
            alben_aktiv += 1

        _, _, trophies = trophy_status(album["id"], gesammelt, total)
        album_trophies += len([t for t in trophies if gesammelt >= t[0]])
        doppelte_trophies += len([t for t in album_doppelte_trophaeen() if doppelt >= t[0]])

    sticker_trophies = len([t for t in global_sticker_trophaeen() if sticker_gesamt >= t[0]])

    trades_erfolgreich = len([t for t in trades if t["status"] == "completed"])
    trades_geplatzt = len([t for t in trades if t["status"] in ("cancelled", "declined")])
    trade_trophies = len([t for t in global_trade_trophaeen() if trades_erfolgreich >= t[0]])

    sticker_erhalten = 0
    sticker_abgegeben = 0

    for trade in trades:
        if trade["status"] != "completed":
            continue

        give_codes = json.loads(trade["give_codes"])
        get_codes = json.loads(trade["get_codes"])

        if trade["from_user_id"] == current_user_id():
            sticker_abgegeben += len(give_codes)
            sticker_erhalten += len(get_codes)
        else:
            sticker_abgegeben += len(get_codes)
            sticker_erhalten += len(give_codes)

    trophies_gesamt = album_trophies + doppelte_trophies + sticker_trophies + trade_trophies

    html = f"""
    <html>
    <head>
    {style()}
    </head>

    <body>
    <div class="container">

    <div class="hero-header">
        <a class="hero-brand" href="/">
            <img src="/static/collectr_logo.png" class="hero-logo">
        </a>

        <div class="hero-actions">
            <a class="hero-link" href="/">🏠 Start</a>
            <a class="hero-link" href="/trophaeen">🏆 Trophäen</a>
        </div>
    </div>

    <h1>Statistikbüro</h1>
    <p class="subline">Deine Sammlerzentrale</p>

    <div class="card">
        <h2>📚 Alben</h2>
        <div class="big">{alben_gesamt}</div>
        <p>Alben gesamt</p>
        <p>
            <strong>{alben_aktiv}</strong> aktiv<br>
            <strong>{alben_beendet}</strong> beendet
        </p>
    </div>

    <div class="card">
        <h2>🎴 Gesamtsticker</h2>
        <div class="big">{sticker_gesamt}</div>
        <p>Sticker gesamt</p>
        <p>
            <strong>{gesammelt_gesamt}</strong> gesammelt<br>
            <strong>{doppelte_gesamt}</strong> doppelte<br>
            <strong>{fehlend_gesamt}</strong> fehlende
        </p>
    </div>

    <div class="card">
        <h2>🏆 Trophies</h2>
        <div class="big">{trophies_gesamt}</div>
        <p>Trophies gesamt</p>
        <p>
            <strong>{album_trophies}</strong> Album<br>
            <strong>{doppelte_trophies}</strong> Doppelte<br>
            <strong>{sticker_trophies}</strong> Sticker<br>
            <strong>{trade_trophies}</strong> Trades
        </p>
    </div>

    <div class="card">
        <h2>🤝 Trades</h2>
        <div class="big">{trades_erfolgreich}</div>
        <p>Durchgeführt</p>
        <p>
            <strong>{trades_geplatzt}</strong> geplatzt<br>
            <strong>{sticker_erhalten}</strong> erhalten<br>
            <strong>{sticker_abgegeben}</strong> abgegeben
        </p>
    </div>

    </div>
    </body>
    </html>
    """

    return html
init_db()

app.run(debug=True)