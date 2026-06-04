from flask import Flask, request

app = Flask(__name__)

TOTAL = 250

ALBUM_NAME = "VfL Osnabrück"

ALBUM_SEASON = "2024/25"

def lade_liste(dateiname):

    with open(dateiname, "r") as datei:

        return eval(datei.read())

def speichere_liste(dateiname, liste):

    with open(dateiname, "w") as datei:

        datei.write(str(liste))

def basis_style():

    return """

    <style>

        body {

            margin: 0;

            font-family: Arial, sans-serif;

            background: linear-gradient(180deg, #16091f, #2b1238);

            color: white;

            min-height: 100vh;

            padding: 30px;

        }

        .container {

            max-width: 1000px;

            margin: auto;

            padding-bottom: 120px;

        }

        h1 {

            font-size: 44px;

            margin-bottom: 6px;

            letter-spacing: 1px;

        }

        h2 { margin-top: 0; }

        .subline {

            color: #d9c3e8;

            margin-bottom: 25px;

        }

        .logo {

            font-size: 34px;

            letter-spacing: 10px;

            font-weight: bold;

            margin-bottom: 6px;

        }

        .card {

            background: rgba(255,255,255,0.08);

            border: 1px solid rgba(255,255,255,0.14);

            border-radius: 24px;

            padding: 24px;

            margin-bottom: 22px;

            box-shadow: 0 16px 45px rgba(0,0,0,0.28);

        }

        .stats {

            display: grid;

            grid-template-columns: repeat(4, 1fr);

            gap: 14px;

        }

        .stat {

            background: rgba(255,255,255,0.07);

            border-radius: 18px;

            padding: 18px;

        }

        .big {

            font-size: 32px;

            font-weight: bold;

        }

        .btn {

            display: inline-block;

            text-align: center;

            text-decoration: none;

            background: #6b3a8e;

            color: white;

            padding: 18px 22px;

            border-radius: 18px;

            font-size: 18px;

            font-weight: bold;

            border: none;

            cursor: pointer;

            margin: 6px;

        }

        .btn:hover { background: #8750ad; }

        input {

            font-size: 22px;

            padding: 18px;

            border-radius: 16px;

            border: none;

            width: 230px;

            margin-right: 10px;

        }

        .album-card {

            display: grid;

            grid-template-columns: 90px 1fr 120px;

            gap: 20px;

            align-items: center;

            text-decoration: none;

            color: white;

        }

        .album-cover {

            width: 82px;

            height: 100px;

            border-radius: 14px;

            background: linear-gradient(145deg, #3a1450, #7b3fa0);

            display: flex;

            align-items: center;

            justify-content: center;

            font-weight: bold;

            font-size: 26px;

            box-shadow: 0 10px 25px rgba(0,0,0,0.35);

        }

        .progress {

            background: rgba(255,255,255,0.16);

            height: 26px;

            border-radius: 30px;

            overflow: hidden;

            margin: 14px 0;

        }

        .progress-bar {

            background: linear-gradient(90deg, #8e55b5, #d8b4f8);

            height: 100%;

        }

        .grid {

            display: grid;

            grid-template-columns: repeat(auto-fill, minmax(95px, 1fr));

            gap: 12px;

        }

        .sticker-box {

            background: rgba(255,255,255,0.09);

            border: 1px solid rgba(255,255,255,0.14);

            padding: 16px;

            border-radius: 16px;

            text-align: center;

            font-weight: bold;

            font-size: 18px;

        }

        .trophy {

            padding: 18px;

            border-radius: 16px;

            background: rgba(255,255,255,0.08);

            margin-bottom: 12px;

            border: 1px solid rgba(255,255,255,0.12);

        }

        .locked {

            opacity: 0.23;

            filter: blur(1px);

        }

    </style>

    """

def auszeichnungen(gesammelt):

    return [

        (25, "Schulhoftauscher", "Die ersten ernsthaften Tauschgeschäfte laufen."),

        (50, "Kurvenkenner", "Das Album nimmt Form an."),

        (75, "Albumarbeiter", "Du sammelst nicht mehr nebenbei, du ziehst durch."),

        (100, "Stickerjäger", "Dreistellig. Jetzt wird es ernst."),

        (125, "Halbzeit", "Die Hälfte ist geschafft."),

        (150, "Kaderplaner", "Du hast den Überblick über dein Album."),

        (175, "Sammelstratege", "Jeder Tausch zählt."),

        (200, "VfL-Chronist", "Das Album ist fast komplett."),

        (225, "Endspurt", "Nur noch die letzten Lücken."),

        (250, "Album vollendet", "Das Sammelalbum ist komplett.")

    ]

@app.route("/")

def hauptmenue():

    fehlende = lade_liste("fehlende.txt")

    doppelte = lade_liste("doppelte.txt")

    gesammelt = TOTAL - len(fehlende)

    prozent = round((gesammelt / TOTAL) * 100)

    komplette_alben = 1 if gesammelt == TOTAL else 0

    angefangene_alben = 1 if gesammelt < TOTAL else 0

    return f"""

    <html>

    <head>{basis_style()}</head>

    <body>

    <div class="container">

        <div class="logo">COLLECTR</div>

        <p class="subline">Collect. Track. Trade.</p>

        <div class="card">

            <h2>Gesamtübersicht</h2>

            <div class="stats">

                <div class="stat">

                    <div class="big">1</div>

                    <p>Alben gesammelt</p>

                </div>

                <div class="stat">

                    <div class="big">{komplette_alben}</div>

                    <p>Komplett</p>

                </div>

                <div class="stat">

                    <div class="big">{prozent}%</div>

                    <p>Gesamtfortschritt</p>

                </div>

                <div class="stat">

                    <div class="big">{len(doppelte)}</div>

                    <p>Doppelte Sticker</p>

                </div>

            </div>

        </div>

        <h2>Meine Alben</h2>

        <div class="card">

            <a class="album-card" href="/album/vfl">

                <div class="album-cover">VfL</div>

                <div>

                    <h2>{ALBUM_NAME}</h2>

                    <p>{ALBUM_SEASON}</p>

                    <div class="progress">

                        <div class="progress-bar" style="width:{prozent}%;"></div>

                    </div>

                    <p>{gesammelt} / {TOTAL} Sticker</p>

                </div>

                <div>

                    <strong>{prozent}%</strong>

                    <p>öffnen →</p>

                </div>

            </a>

        </div>

        <a class="btn" href="#">+ Album hinzufügen</a>

    </div>

    </body>

    </html>

    """

@app.route("/album/vfl", methods=["GET", "POST"])

def album_vfl():

    meldung = ""

    fehlende = lade_liste("fehlende.txt")

    doppelte = lade_liste("doppelte.txt")

    if request.method == "POST":

        sticker = int(request.form["sticker"])

        if sticker in fehlende:

            fehlende.remove(sticker)

            meldung = f"Sticker {sticker} wurde ins Album eingetragen."

        else:

            doppelte.append(sticker)

            anzahl = doppelte.count(sticker)

            meldung = f"Sticker {sticker} ist doppelt. Du hast ihn jetzt {anzahl}x doppelt."

        speichere_liste("fehlende.txt", fehlende)

        speichere_liste("doppelte.txt", doppelte)

    gesammelt = TOTAL - len(fehlende)

    prozent = round((gesammelt / TOTAL) * 100)

    awards = auszeichnungen(gesammelt)

    erreicht = [a for a in awards if gesammelt >= a[0]]

    naechste = next((a for a in awards if gesammelt < a[0]), None)

    letzte_text = "Noch keine Auszeichnung erreicht."

    if erreicht:

        letzte_text = f"🏆 {erreicht[-1][1]}"

    naechste_text = "Alle Auszeichnungen erreicht."

    if naechste:

        naechste_text = f"Nächstes Ziel: {naechste[0]} Sticker - {naechste[1]}"

    return f"""

    <html>

    <head>{basis_style()}</head>

    <body>

    <div class="container">

        <a href="/">← Zurück zur Übersicht</a>

        <h1>{ALBUM_NAME}</h1>

        <p class="subline">{ALBUM_SEASON}</p>

        <div class="card">

            <h2>Sticker eintragen</h2>

            <form method="POST">

                <input name="sticker" placeholder="Nummer" autofocus>

                <button class="btn" type="submit">Eintragen</button>

            </form>

            <p>{meldung}</p>

        </div>

        <div class="card">

            <h2>Albumübersicht</h2>

            <p>Sticker gesamt: {gesammelt} / {TOTAL}</p>

            <p>Fehlende Sticker: {len(fehlende)}</p>

            <p>Doppelte Sticker: {len(doppelte)}</p>

            <div class="progress">

                <div class="progress-bar" style="width:{prozent}%;"></div>

            </div>

            <p>{prozent}% abgeschlossen</p>

        </div>

        <a class="btn" href="/album/vfl/fehlende">Fehlende</a>

        <a class="btn" href="/album/vfl/doppelte">Doppelte</a>

        <a class="btn" href="/album/vfl/auszeichnungen">Auszeichnungen</a>

        <div class="card">

            <h2>🏆 Letzte Auszeichnung</h2>

            <p>{letzte_text}</p>

            <p>{naechste_text}</p>

        </div>

    </div>

    </body>

    </html>

    """

@app.route("/album/vfl/fehlende")

def fehlende_anzeigen():

    fehlende = sorted(lade_liste("fehlende.txt"))

    html = f"""

    <html><head>{basis_style()}</head><body>

    <div class="container">

        <a href="/album/vfl">← Zurück zum Album</a>

        <h1>Fehlende Sticker</h1>

        <p class="subline">{len(fehlende)} Sticker fehlen noch.</p>

        <div class="card">

            <div class="grid">

    """

    for sticker in fehlende:

        html += f'<div class="sticker-box">#{sticker}</div>'

    html += """

            </div>

        </div>

    </div>

    </body></html>

    """

    return html

@app.route("/album/vfl/doppelte")

def doppelte_anzeigen():

    doppelte = lade_liste("doppelte.txt")

    gezaehlt = {}

    for sticker in doppelte:

        gezaehlt[sticker] = gezaehlt.get(sticker, 0) + 1

    sortierung = request.args.get("sort", "nummer")

    if sortierung == "anzahl":

        liste = sorted(gezaehlt.items(), key=lambda item: item[1], reverse=True)

    else:

        liste = sorted(gezaehlt.items())

    html = f"""

    <html><head>{basis_style()}</head><body>

    <div class="container">

        <a href="/album/vfl">← Zurück zum Album</a>

        <h1>Doppelte Sticker</h1>

        <p class="subline">{len(doppelte)} doppelte Sticker insgesamt.</p>

        <a class="btn" href="/album/vfl/doppelte?sort=nummer">Nach Nummer</a>

        <a class="btn" href="/album/vfl/doppelte?sort=anzahl">Nach Anzahl</a>

        <div class="card">

            <div class="grid">

    """

    for sticker, anzahl in liste:

        html += f'<div class="sticker-box">#{sticker}<br>{anzahl}x</div>'

    html += """

            </div>

        </div>

    </div>

    </body></html>

    """

    return html

@app.route("/album/vfl/auszeichnungen")

def auszeichnungen_anzeigen():

    fehlende = lade_liste("fehlende.txt")

    gesammelt = TOTAL - len(fehlende)

    awards = auszeichnungen(gesammelt)

    naechste = next((a for a in awards if gesammelt < a[0]), None)

    html = f"""

    <html><head>{basis_style()}</head><body>

    <div class="container">

        <a href="/album/vfl">← Zurück zum Album</a>

        <h1>Auszeichnungen</h1>

        <p class="subline">Erhaltene Auszeichnungen und kommende Ziele.</p>

    """

    for ziel, name, beschreibung in awards:

        if gesammelt >= ziel:

            html += f"""

            <div class="trophy">

                <h2>🏆 {name}</h2>

                <p>{ziel} Sticker gesammelt</p>

                <p>{beschreibung}</p>

            </div>

            """

        elif naechste and ziel == naechste[0]:

            html += f"""

            <div class="trophy">

                <h2>🏆 Nächstes Ziel: {name}</h2>

                <p>{ziel} Sticker</p>

                <p>{beschreibung}</p>

            </div>

            """

        else:

            html += """

            <div class="trophy locked">

                <h2>🏆 ?????</h2>

                <p>Diese Auszeichnung ist noch verborgen.</p>

            </div>

            """

    html += """

    </div>

    </body></html>

    """

    return html

app.run(debug=True)