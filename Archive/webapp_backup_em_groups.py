from flask import Flask, request, redirect
import sqlite3

app = Flask(__name__)
DB = "collectr.db"


def get_db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def style():
    return """
    <style>
        body{margin:0;background:#f6f3ef;font-family:Arial;color:#1b1620;padding:30px;}
        .container{max-width:1200px;margin:auto;padding-bottom:120px;}
        .brand{display:flex;align-items:center;gap:20px;margin-bottom:40px;}
        .logo{width:72px;height:72px;border-radius:22px;background:linear-gradient(145deg,#251131,#7a3cb0);color:white;display:flex;align-items:center;justify-content:center;font-size:34px;font-weight:bold;}
        .logo-text{font-size:34px;font-weight:800;letter-spacing:7px;}
        .subline{color:#72697c;}
        .card{background:white;border-radius:28px;padding:28px;margin-bottom:24px;box-shadow:0 12px 34px rgba(0,0,0,0.05);}
        .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;}
        .stat{background:#faf8fc;border-radius:20px;padding:20px;}
        .big{font-size:36px;font-weight:800;color:#5d2f86;}
        .btn{display:inline-block;background:#5d2f86;color:white;text-decoration:none;padding:14px 20px;border-radius:16px;margin:6px;border:none;font-weight:bold;cursor:pointer;}
        .btn:hover{background:#7540a8;}
        input{padding:16px;border-radius:14px;border:1px solid #ddd3e8;width:240px;font-size:18px;}
        .album-card{display:grid;grid-template-columns:110px 1fr 120px;gap:24px;align-items:center;text-decoration:none;color:#1b1620;}
        .album-cover{width:100px;height:120px;border-radius:18px;background:linear-gradient(145deg,#24112f,#7b3bb0);color:white;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:22px;}
        .progress{background:#ece5f3;height:22px;border-radius:20px;overflow:hidden;margin-top:12px;}
        .progress-bar{background:linear-gradient(90deg,#5d2f86,#b07ae0);height:100%;}
        .wall{display:grid;grid-template-columns:repeat(auto-fill,minmax(74px,1fr));gap:10px;}
        .slot{border-radius:14px;padding:18px 8px;text-align:center;font-weight:bold;transition:.2s;display:block;text-decoration:none;}
        .slot:hover{transform:scale(1.05);}
        .missing{background:#d9d5dc;color:#6b6570;}
        .owned{background:#b7efc1;color:#125226;}
        .duplicate{background:#d8b4fe;color:#4a166c;}
        .trophy{background:#faf8fc;border-radius:18px;padding:18px;margin-bottom:12px;}
        .notice{background:#efe1ff;border:2px solid #5d2f86;border-radius:24px;padding:28px;margin-bottom:24px;}
    </style>
    """


def lade_album(album_id):
    con = get_db()
    album = con.execute("SELECT * FROM albums WHERE id=?", (album_id,)).fetchone()
    sticker = con.execute("SELECT * FROM stickers WHERE album_id=?", (album_id,)).fetchall()
    con.close()

    status = {}
    gesammelt = 0
    doppelte = 0

    for s in sticker:
        code = s["sticker_code"]
        quantity = s["quantity"]
        gesammelt += 1

        if quantity >= 2:
            status[code] = "duplicate"
            doppelte += quantity - 1
        else:
            status[code] = "owned"

    if album["complete"] == 1:
        gesammelt = album["total"]

    prozent = round((gesammelt / album["total"]) * 100)
    return album, sticker, status, gesammelt, doppelte, prozent


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


def erreichte_trophaeen(gesammelt):
    return [t for t in vfl_trophaeen() if gesammelt >= t[0]]


def naechste_trophaee(gesammelt):
    for ziel, titel in vfl_trophaeen():
        if gesammelt < ziel:
            return ziel, titel
    return None


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
        album, sticker, status, gesammelt, doppelte, prozent = lade_album(a["id"])
        infos.append((album, gesammelt, doppelte, prozent))
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

    for album, gesammelt, doppelte, prozent in infos:
        if prozent < 100:
            html += album_card(album, gesammelt, prozent)

    html += "<h1>Vitrine</h1><p class='subline'>Vollständige Sammlungen</p>"

    for album, gesammelt, doppelte, prozent in infos:
        if prozent == 100:
            html += album_card(album, gesammelt, prozent)

    html += "</div></body></html>"
    return html


def album_card(album, gesammelt, prozent):
    return f"""
    <div class="card">
        <a class="album-card" href="/album/{album['id']}">
            <div class="album-cover">{album['cover']}</div>
            <div>
                <h2>{album['name']}</h2>
                <p>{album['season']}</p>
                <div class="progress"><div class="progress-bar" style="width:{prozent}%;"></div></div>
                <p>{gesammelt} / {album['total']} Sticker</p>
            </div>
            <div><h2>{prozent}%</h2></div>
        </a>
    </div>
    """


@app.route("/album/<album_id>", methods=["GET", "POST"])
def albumseite(album_id):
    trophy = request.args.get("trophy")

    if request.method == "POST":
        code = request.form["sticker"].strip()
        if code:
            return redirect(f"/add/{album_id}/{code}")

    album, sticker, status, gesammelt, doppelte, prozent = lade_album(album_id)

    html = f"""
    <html><head>{style()}</head><body><div class="container">
    <a class="btn" href="/">← Hauptmenü</a>
    <h1>{album['name']}</h1>
    <p class="subline">{album['season']}</p>
    """

    if trophy:
        html += f"""
        <div class="notice">
            <h1>🏆 Trophäe freigeschaltet</h1>
            <h2>{trophy}</h2>
            <p>Starker Fortschritt in deinem Album.</p>
            <a class="btn" href="/album/{album_id}">Verstanden</a>
        </div>
        """

    html += f"""
    <div class="card">
        <h2>Sticker eintragen</h2>
        <form method="POST">
            <input name="sticker" placeholder="Sticker ID" autofocus>
            <button class="btn">Eintragen</button>
        </form>
    </div>

    <div class="card">
        <h2>Albumübersicht</h2>
        <p>{gesammelt} / {album['total']} Sticker gesammelt</p>
        <p>{doppelte} doppelte Sticker</p>
        <div class="progress"><div class="progress-bar" style="width:{prozent}%;"></div></div>
        <br>
        <a class="btn" href="/album/{album_id}/trophaeen">Album-Trophäen</a>
    </div>
    """

    if album_id == "vfl":
        next_trophy = naechste_trophaee(gesammelt)
        if next_trophy:
            ziel, titel = next_trophy
            fehlen_bis_trophy = ziel - gesammelt
            html += f"""
            <div class="card">
                <h2>Nächste Trophäe</h2>
                <p><strong>{titel}</strong> bei {ziel} Stickern</p>
                <p>Noch {fehlen_bis_trophy} Sticker bis zur nächsten Auszeichnung.</p>
            </div>
            """

    html += """
    <div class="card">
        <h2>Sammlung</h2>
        <div class="wall">
    """

    if album_id == "vfl":
        codes = [str(n) for n in range(1, album["total"] + 1)]
    else:
        codes = [s["sticker_code"] for s in sticker]

    for code in codes:
        klasse = status.get(code, "missing")
        text = code
        if code in status and status[code] == "duplicate":
            q = next(s["quantity"] for s in sticker if s["sticker_code"] == code)
            text = f"{code}<br>{q}x"
        html += f'<a class="slot {klasse}" href="/sticker/{album_id}/{code}">{text}</a>'

    html += "</div></div></div></body></html>"
    return html


@app.route("/sticker/<album_id>/<code>")
def sticker_detail(album_id, code):
    con = get_db()
    daten = con.execute("SELECT * FROM stickers WHERE album_id=? AND sticker_code=?", (album_id, code)).fetchone()
    con.close()

    quantity = daten["quantity"] if daten else 0

    if quantity == 0:
        farbe = "missing"
        status = "Fehlt"
    elif quantity == 1:
        farbe = "owned"
        status = "Vorhanden"
    else:
        farbe = "duplicate"
        status = "Doppelt"

    return f"""
    <html><head>{style()}</head><body><div class="container">
    <a class="btn" href="/album/{album_id}">← Zurück</a>
    <div class="card">
        <h1>Sticker {code}</h1>
        <div class="slot {farbe}" style="width:130px;font-size:26px;margin-bottom:20px;">{code}</div>
        <h2>{status}</h2>
        <p>Anzahl: {quantity}</p>
        <a class="btn" href="/add/{album_id}/{code}">+ Hinzufügen</a>
        <a class="btn" href="/remove/{album_id}/{code}">- Entfernen</a>
    </div>
    </div></body></html>
    """


@app.route("/add/<album_id>/<code>")
def add(album_id, code):
    vor_album, _, _, vor_gesammelt, _, _ = lade_album(album_id)
    vorher_trophaeen = erreichte_trophaeen(vor_gesammelt) if album_id == "vfl" else []

    con = get_db()
    cur = con.cursor()
    daten = con.execute("SELECT * FROM stickers WHERE album_id=? AND sticker_code=?", (album_id, code)).fetchone()

    if daten:
        neue_quantity = daten["quantity"] + 1
        neue_duplicates = max(neue_quantity - 1, 0)
        cur.execute("UPDATE stickers SET quantity=?, duplicates=? WHERE id=?", (neue_quantity, neue_duplicates, daten["id"]))
    else:
        cur.execute("""
        INSERT INTO stickers (album_id, sticker_code, status, duplicates, quantity)
        VALUES (?, ?, 'owned', 0, 1)
        """, (album_id, code))

    con.commit()
    con.close()

    nach_album, _, _, nach_gesammelt, _, _ = lade_album(album_id)
    nachher_trophaeen = erreichte_trophaeen(nach_gesammelt) if album_id == "vfl" else []

    if album_id == "vfl" and len(nachher_trophaeen) > len(vorher_trophaeen):
        neue_trophy = nachher_trophaeen[-1][1]
        return redirect(f"/album/{album_id}?trophy={neue_trophy}")

    return redirect(f"/sticker/{album_id}/{code}")


@app.route("/remove/<album_id>/<code>")
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
    album, sticker, status, gesammelt, doppelte, prozent = lade_album(album_id)

    html = f"""
    <html><head>{style()}</head><body><div class="container">
    <a class="btn" href="/album/{album_id}">← Zurück</a>
    <h1>Album-Trophäen</h1>
    """

    if album_id == "vfl":
        for ziel, titel in vfl_trophaeen():
            erreicht = gesammelt >= ziel
            html += f"""
            <div class="trophy">
                <h2>{'🏆' if erreicht else '🔒'} {titel}</h2>
                <p>{ziel} Sticker gesammelt</p>
            </div>
            """
    else:
        html += """
        <div class="trophy">
            <h2>🏆 Trophäenschrank Platzhalter</h2>
            <p>Die EURO-Trophäen führen wir später ein.</p>
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
    <div class="trophy"><h2>🏆 500 Sticker gesammelt</h2><p>Globale Collectr-Trophäen bauen wir später sauber aus.</p></div>
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