from flask import Flask, request, redirect
import sqlite3
from em24_data import build_em24

app = Flask(__name__)
DB = "collectr.db"


def get_db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def compact(text):
    return text.upper().replace(" ", "").replace("-", "")


def display_code(code):
    return code.replace(" ", "")


def em_map():
    mapping = {}
    for sticker in build_em24():
        mapping[compact(sticker["id"])] = sticker["id"]
        for slot in sticker["slots"]:
            mapping[compact(slot)] = sticker["id"]
    return mapping


def resolve_code(album_id, raw):

    value = raw.strip().upper()

    if album_id == "vfl":

        if not value.isdigit():
            return None

        if value not in all_codes("vfl"):
            return None

        return value

    mapping = em_map()

    cleaned = compact(value)

    if cleaned not in mapping:
        return None

    return mapping[cleaned]


def style():
    return """
    <style>
        body{margin:0;background:#f6f3ef;font-family:Arial;color:#1b1620;padding:30px;}
        .container{max-width:1200px;margin:auto;padding-bottom:120px;}
        .brand{display:flex;align-items:center;gap:20px;margin-bottom:40px;}
        .logo{width:72px;height:72px;border-radius:22px;background:linear-gradient(145deg,#251131,#7a3cb0);color:white;display:flex;align-items:center;justify-content:center;font-size:34px;font-weight:bold;}
        .logo-text{font-size:34px;font-weight:800;letter-spacing:7px;}
        .subline{color:#72697c;}
        .card{background:white;border-radius:28px;padding:28px;margin-bottom:24px;box-shadow:0 12px 34px rgba(0,0,0,.05);}
        .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;}
        .stat{background:#faf8fc;border-radius:20px;padding:20px;}
        .big{font-size:36px;font-weight:800;color:#5d2f86;}
        .btn{display:inline-block;background:#5d2f86;color:white;text-decoration:none;padding:14px 20px;border-radius:16px;margin:6px;border:none;font-weight:bold;cursor:pointer;}
        .btn:hover{background:#7540a8;}
        .btn-all{background:#5d2f86;}
        .btn-missing{background:#d9d5dc;color:#125226;}
        .btn-owned{background:#b7efc1;color:#125226;color:#125226;}
        .btn-duplicate{background:#c084fc;color:#125226;}
        .btn-active{
            transform:scale(1.06);
            box-shadow:0 10px 24px rgba(93,47,134,0.28);
            outline:3px solid rgba(93,47,134,0.25);
        }
        input{padding:16px;border-radius:14px;border:1px solid #ddd3e8;width:240px;font-size:18px;}
        .album-card{display:grid;grid-template-columns:110px 1fr 120px;gap:24px;align-items:center;text-decoration:none;color:#1b1620;}
        .album-cover{width:100px;height:120px;border-radius:18px;background:linear-gradient(145deg,#24112f,#7b3bb0);color:white;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:22px;}
        .progress{background:#ece5f3;height:22px;border-radius:20px;overflow:hidden;margin-top:12px;}
        .progress-bar{background:linear-gradient(90deg,#5d2f86,#b07ae0);height:100%;}
        .wall{display:grid;grid-template-columns:repeat(auto-fill,minmax(78px,1fr));gap:10px;overflow:visible;}
        .slot{border-radius:14px;padding:14px 6px;text-align:center;font-weight:bold;transition:.2s;display:flex;align-items:center;justify-content:center;min-height:46px;text-decoration:none;font-size:13px;line-height:1.15;overflow:hidden;word-break:break-word;}
        .slot:hover{
            transform:translateY(-4px) scale(1.06);
            box-shadow:0 12px 22px rgba(0,0,0,0.12);
            z-index:2;
        }
        .missing{background:#d9d5dc;color:#6b6570;}
        .owned{background:#b7efc1;color:#125226;}
        .duplicate{background:#d8b4fe;color:#4a166c;}
        .trophy{background:#faf8fc;border-radius:18px;padding:18px;margin-bottom:12px;}
.trophy-unlocked{
    cursor:pointer;
    transition:.2s;
}

.trophy-unlocked:hover{
    transform:translateY(-4px) scale(1.03);
    box-shadow:0 12px 22px rgba(0,0,0,0.12);
}

.trophy-locked{
    opacity:.42;
    filter:grayscale(1);
    cursor:not-allowed;
}

.trophy-detail{
    background:#fff7d6;
    border:2px solid #d4a017;
    border-radius:24px;
    padding:24px;
    margin-bottom:24px;
}
        .notice{background:#efe1ff;border:2px solid #5d2f86;border-radius:24px;padding:28px;margin-bottom:24px;}
.notice-success{background:#dff7e5;border:2px solid #2e8b57;}
.notice-duplicate{background:#efe1ff;border:2px solid #8b5cf6;}
.notice-error{background:#ffe3e3;border:2px solid #dc2626;}
        .album-tools{
    display:grid;
    grid-template-columns:2fr 1fr;
    gap:18px;
}
.trophy-card{
    text-decoration:none;
    color:inherit;
}
.trophy-card .card{
    height:100%;
}.section-title{margin-top:34px;color:#5d2f86;}
    </style>
    """


def all_codes(album_id):
    if album_id == "vfl":
        return [str(i) for i in range(1, 251)]
    return [s["id"] for s in build_em24()]


def lade_album(album_id):
    con = get_db()
    album = con.execute("SELECT * FROM albums WHERE id=?", (album_id,)).fetchone()
    sticker = con.execute("SELECT * FROM stickers WHERE album_id=?", (album_id,)).fetchall()
    con.close()

    by_code = {s["sticker_code"]: s for s in sticker}
    gesammelt = 0
    doppelte = 0
    total = len(build_em24()) if album_id == "em24" else album["total"]

    for code in all_codes(album_id):
        q = by_code[code]["quantity"] if code in by_code else 0
        if q > 0:
            gesammelt += 1
        if q > 1:
            doppelte += q - 1

    prozent = round((gesammelt / total) * 100)
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


def trophy_status(album_id, gesammelt, total):
    if album_id != "vfl" and album_id != "em24":
        return "Album vollendet", "Alle Trophäen erhalten", [(total, "Album vollendet")]

    if album_id == "vfl":
        trophies = vfl_trophaeen()
    elif album_id == "em24":
        trophies = em24_trophaeen(total)
    else:
        trophies = [(total, "Album vollendet")]

    reached = [t for t in trophies if gesammelt >= t[0]]
    next_one = next((t for t in trophies if gesammelt < t[0]), None)

    last = reached[-1][1] if reached else "Noch keine Auszeichnung"
    nxt = f"{next_one[1]} bei {next_one[0]} Stickern" if next_one else "Alle Trophäen erhalten"

    return last, nxt, trophies


@app.route("/")
def startseite():
    con = get_db()
    alben = con.execute("SELECT * FROM albums").fetchall()
    con.close()

    infos = []
    doppelte_gesamt = 0
    komplett = 0
    prozent_summe = 0

    for a in alben:
        album, by_code, gesammelt, doppelte, prozent, total = lade_album(a["id"])
        infos.append((album, gesammelt, doppelte, prozent, total))
        doppelte_gesamt += doppelte
        prozent_summe += prozent
        if prozent == 100:
            komplett += 1

    schnitt = round(prozent_summe / len(infos))

    html = f"""
    <html><head>{style()}</head><body><div class="container">
    <div class="brand"><div class="logo">C</div><div><div class="logo-text">COLLECTR</div><div class="subline">Collect. Track. Trade.</div></div></div>

    <div class="card">
        <h2>Gesamtübersicht</h2>
        <div class="stats">
            <div class="stat"><div class="big">{len(infos)}</div><p>Alben</p></div>
            <div class="stat"><div class="big">{komplett}</div><p>Komplett</p></div>
            <div class="stat"><div class="big">{schnitt}%</div><p>Fortschritt</p></div>
            <div class="stat"><div class="big">{doppelte_gesamt}</div><p>Doppelte</p></div>
        </div>
        <br>
        <a class="btn" href="/trophaeen">Trophäenschrank</a>
        <a class="btn" href="/statistik">Statistik</a>
    </div>

    <h1>Kollektion</h1><p class="subline">Aktive Sammlungen</p>
    """

    for album, gesammelt, doppelte, prozent, total in infos:
        if prozent < 100:
            html += album_card(album, gesammelt, prozent, total)

    html += "<h1>Vitrine</h1><p class='subline'>Vollständige Sammlungen</p>"

    for album, gesammelt, doppelte, prozent, total in infos:
        if prozent == 100:
            html += album_card(album, gesammelt, prozent, total)

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
            <div><h2>{prozent}%</h2></div>
        </a>
    </div>
    """


@app.route("/album/<album_id>", methods=["GET", "POST"])
def albumseite(album_id):
    filter_name = request.args.get("filter", "all")
    message = request.args.get("message", "")

    if request.method == "POST":
        raw = request.form["sticker"].strip()

        if raw:
            code = resolve_code(album_id, raw)

            if code is None:
                return redirect(f"/album/{album_id}?message=Sticker%20nicht%20vorhanden.")

            return redirect(f"/add/{album_id}/{code}")

    album, by_code, gesammelt, doppelte, prozent, total = lade_album(album_id)
    last_trophy, next_trophy, trophies = trophy_status(album_id, gesammelt, total)

    html = f"""
    <html><head>{style()}</head><body><div class="container">
    <a class="btn" href="/">← Hauptmenü</a>
    <h1>{album['name']}</h1>
    <p class="subline">{album['season']}</p>

    {f'<div class="notice {"notice-error" if "nicht vorhanden" in message else "notice-duplicate" if "doppelt" in message else "notice-success"}"><h2>{message}</h2></div>' if message else ''}
    <div class="album-tools">

    <div class="card">
        <h2>Sticker eintragen</h2>
        <form method="POST">
            <input name="sticker" placeholder="Sticker ID" autofocus>
            <button class="btn">Eintragen</button>
        </form>
    </div>

    <a class="trophy-card" href="/album/{album_id}/trophaeen">
        <div class="card">
            <h2>🏆 Trophäenschrank</h2>
            <p>Letzte: <strong>{last_trophy}</strong></p>
            <p>Nächste: <strong>{next_trophy}</strong></p>
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
            html += f'<a class="slot {klasse}" href="/sticker/{album_id}/{code}">{text}</a>'
        if open_wall:
            html += "</div>"
    else:
        html += '<div class="wall">'
        for code in all_codes(album_id):
            if not filter_ok(filter_name, code, by_code):
                continue
            klasse, text = klasse_und_text(code, by_code)
            html += f'<a class="slot {klasse}" href="/sticker/{album_id}/{code}">{text}</a>'
        html += "</div>"

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
    con = get_db()
    cur = con.cursor()
    daten = con.execute("SELECT * FROM stickers WHERE album_id=? AND sticker_code=?", (album_id, code)).fetchone()

    if daten:
        neue_quantity = daten["quantity"] + 1
        neue_duplicates = max(neue_quantity - 1, 0)
        cur.execute("UPDATE stickers SET quantity=?, duplicates=? WHERE id=?", (neue_quantity, neue_duplicates, daten["id"]))
    else:
        neue_quantity = 1
        neue_duplicates = 0
        cur.execute("""
        INSERT INTO stickers (album_id, sticker_code, status, duplicates, quantity)
        VALUES (?, ?, 'owned', ?, ?)
        """, (album_id, code, neue_duplicates, neue_quantity))

    con.commit()
    con.close()

    msg = f"Du hast Sticker {display_code(code)} doppelt." if neue_duplicates == 1 else f"Du hast Sticker {display_code(code)} jetzt {neue_duplicates}x doppelt."
    if neue_duplicates == 0:
        msg = f"Du hast Sticker {display_code(code)} zur Sammlung hinzugefügt."

    return redirect(f"/album/{album_id}?message={msg}")


@app.route("/remove/<album_id>/<path:code>")
def remove(album_id, code):
    con = get_db()
    cur = con.cursor()
    daten = con.execute("SELECT * FROM stickers WHERE album_id=? AND sticker_code=?", (album_id, code)).fetchone()

    if daten:
        neue_quantity = max(daten["quantity"] - 1, 0)
        neue_duplicates = max(neue_quantity - 1, 0)

        if neue_quantity == 0:
            cur.execute("DELETE FROM stickers WHERE id=?", (daten["id"],))
        else:
            cur.execute("UPDATE stickers SET quantity=?, duplicates=? WHERE id=?", (neue_quantity, neue_duplicates, daten["id"]))

    con.commit()
    con.close()
    return redirect(f"/sticker/{album_id}/{code}")


@app.route("/album/<album_id>/trophaeen")
def album_trophaeen(album_id):
    album, by_code, gesammelt, doppelte, prozent, total = lade_album(album_id)
    last_trophy, next_trophy, trophies = trophy_status(album_id, gesammelt, total)

    html = f"""
    <html><head>{style()}</head><body><div class="container">
    <a class="btn" href="/album/{album_id}">← Zurück</a>
    <h1>Album-Trophäen</h1>
    <div class="notice">
        <h2>Letzte Auszeichnung: {last_trophy}</h2>
        <p>Nächste Trophäe: <strong>{next_trophy}</strong></p>
    </div>
    """

    for ziel, titel in trophies:
        erreicht = gesammelt >= ziel
        klasse = "trophy-unlocked" if erreicht else "trophy-locked"
        beschreibung = f"{ziel} Sticker gesammelt"

        html += f"""
        <div class="trophy {klasse}">
            <h2>{"🏆" if erreicht else "🔒"} {titel}</h2>
            <p>{beschreibung}</p>
        </div>
        """

    html += "</div></body></html>"
    return html

@app.route("/trophaeen")
def globale_trophaeen():
    return f"""
    <html><head>{style()}</head><body><div class="container">
    <a class="btn" href="/">← Zurück</a>
    <h1>Trophäenschrank</h1>
    <div class="trophy"><h2>🏆 1 Album vollendet</h2><p>EURO 2024 abgeschlossen.</p></div>
    </div></body></html>
    """


@app.route("/statistik")
def statistik():
    con = get_db()
    sticker_gesamt = con.execute("SELECT SUM(quantity) FROM stickers").fetchone()[0] or 0
    doppelte = con.execute("SELECT SUM(duplicates) FROM stickers").fetchone()[0] or 0
    alben = con.execute("SELECT COUNT(*) FROM albums").fetchone()[0]
    con.close()

    return f"""
    <html><head>{style()}</head><body><div class="container">
    <a class="btn" href="/">← Zurück</a>
    <h1>Statistik</h1>
    <div class="card">
        <div class="stats">
            <div class="stat"><div class="big">{alben}</div><p>Alben</p></div>
            <div class="stat"><div class="big">{sticker_gesamt}</div><p>Sticker insgesamt</p></div>
            <div class="stat"><div class="big">{doppelte}</div><p>Doppelte</p></div>
            <div class="stat"><div class="big">0</div><p>Tausche</p></div>
        </div>
    </div>
    </div></body></html>
    """


app.run(debug=True)