from flask import Flask, request

app = Flask(__name__)

TOTAL_VFL = 250


def lade_liste(dateiname):
    with open(dateiname, "r") as datei:
        return eval(datei.read())


def speichere_liste(dateiname, liste):
    with open(dateiname, "w") as datei:
        datei.write(str(liste))


def style():
    return """
    <style>
        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: linear-gradient(180deg,#16091f,#2a1238);
            color: white;
            padding: 30px;
        }

        .container {
            max-width: 1050px;
            margin: auto;
            padding-bottom: 120px;
        }

        .logo-wrap {
            display: flex;
            align-items: center;
            gap: 18px;
            margin-bottom: 25px;
        }

        .logo-icon {
            width: 62px;
            height: 62px;
            border-radius: 18px;
            background: linear-gradient(145deg,#6b3a8e,#c79cff);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 34px;
            font-weight: bold;
        }

        .logo-text {
            font-size: 34px;
            font-weight: bold;
            letter-spacing: 7px;
        }

        .subline { color: #d8c8e4; }

        .card {
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 24px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 15px 40px rgba(0,0,0,0.28);
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(4,1fr);
            gap: 14px;
        }

        .stat {
            background: rgba(255,255,255,0.06);
            border-radius: 18px;
            padding: 18px;
        }

        .big {
            font-size: 34px;
            font-weight: bold;
        }

        .btn {
            display: inline-block;
            background: #6b3a8e;
            color: white;
            text-decoration: none;
            padding: 16px 20px;
            border-radius: 16px;
            margin: 6px;
            font-weight: bold;
            border: none;
            cursor: pointer;
            font-size: 17px;
        }

        .btn:hover { background: #8750ad; }

        input {
            font-size: 22px;
            padding: 16px;
            border-radius: 14px;
            border: none;
            width: 220px;
        }

        .album-card {
            display: grid;
            grid-template-columns: 100px 1fr 120px;
            gap: 20px;
            align-items: center;
            color: white;
            text-decoration: none;
        }

        .album-cover {
            width: 90px;
            height: 110px;
            border-radius: 18px;
            background: linear-gradient(145deg,#3a1450,#8b52b5);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 22px;
        }

        .progress {
            background: rgba(255,255,255,0.12);
            height: 24px;
            border-radius: 20px;
            overflow: hidden;
            margin-top: 12px;
        }

        .progress-bar {
            background: linear-gradient(90deg,#9a63c7,#d8b4f8);
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


def lade_vfl_daten():
    fehlende = lade_liste("fehlende.txt")
    doppelte = lade_liste("doppelte.txt")
    gesammelt = TOTAL_VFL - len(fehlende)
    prozent = round((gesammelt / TOTAL_VFL) * 100)
    return fehlende, doppelte, gesammelt, prozent


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
def startseite():
    fehlende, doppelte, gesammelt, prozent = lade_vfl_daten()

    return f"""
    <html><head>{style()}</head><body>
    <div class="container">

        <div class="logo-wrap">
            <div class="logo-icon">C</div>
            <div>
                <div class="logo-text">COLLECTR</div>
                <div class="subline">Collect. Track. Trade.</div>
            </div>
        </div>

        <a href="/gesamt" style="text-decoration:none;color:white;">
            <div class="card">
                <h2>Gesamtübersicht</h2>
                <div class="stats">
                    <div class="stat"><div class="big">2</div><p>Alben</p></div>
                    <div class="stat"><div class="big">0</div><p>Komplett</p></div>
                    <div class="stat"><div class="big">{prozent}%</div><p>Fortschritt</p></div>
                    <div class="stat"><div class="big">{len(doppelte)}</div><p>Doppelte</p></div>
                </div>
            </div>
        </a>

        <h2>Meine Alben</h2>

        <div class="card">
            <a class="album-card" href="/album/vfl">
                <div class="album-cover">VfL</div>
                <div>
                    <h2>VfL Osnabrück</h2>
                    <p>2024/25</p>
                    <div class="progress">
                        <div class="progress-bar" style="width:{prozent}%;"></div>
                    </div>
                    <p>{gesammelt} / {TOTAL_VFL} Sticker</p>
                </div>
                <div><strong>{prozent}%</strong><p>öffnen →</p></div>
            </a>
        </div>

        <div class="card">
            <a class="album-card" href="/album/em24">
                <div class="album-cover">EURO</div>
                <div>
                    <h2>EURO 2024</h2>
                    <p>Platzhalter</p>
                    <div class="progress">
                        <div class="progress-bar" style="width:0%;"></div>
                    </div>
                    <p>Noch nicht eingerichtet</p>
                </div>
                <div><strong>0%</strong><p>öffnen →</p></div>
            </a>
        </div>

        <a class="btn" href="/album-hinzufuegen">+ Album hinzufügen</a>

    </div>
    </body></html>
    """


@app.route("/gesamt")
def gesamt():
    fehlende, doppelte, gesammelt, prozent = lade_vfl_daten()

    return f"""
    <html><head>{style()}</head><body>
    <div class="container">
        <a class="btn" href="/">← Zurück</a>
        <h1>Gesamtübersicht</h1>

        <div class="card">
            <p>Alben gesammelt: 2</p>
            <p>Komplett abgeschlossen: 0</p>
            <p>Gesamtfortschritt: {prozent}%</p>
            <p>Doppelte Sticker gesamt: {len(doppelte)}</p>
            <p>Trophäen erhalten: {len([a for a in auszeichnungen(gesammelt) if gesammelt >= a[0]])}</p>
            <p>Erfolgreiche Tausche: 0</p>
        </div>
    </div>
    </body></html>
    """


@app.route("/album/vfl", methods=["GET", "POST"])
def album_vfl():
    meldung = ""
    fehlende, doppelte, gesammelt, prozent = lade_vfl_daten()

    if request.method == "POST":
        sticker = int(request.form["sticker"])

        if sticker in fehlende:
            fehlende.remove(sticker)
            meldung = f"Sticker {sticker} wurde ins Album eingetragen."
        else:
            doppelte.append(sticker)
            meldung = f"Sticker {sticker} ist doppelt. Du hast ihn jetzt {doppelte.count(sticker)}x doppelt."

        speichere_liste("fehlende.txt", fehlende)
        speichere_liste("doppelte.txt", doppelte)

        fehlende, doppelte, gesammelt, prozent = lade_vfl_daten()

    awards = auszeichnungen(gesammelt)
    erreicht = [a for a in awards if gesammelt >= a[0]]
    naechste = next((a for a in awards if gesammelt < a[0]), None)

    letzte = "Noch keine Auszeichnung erreicht."
    if erreicht:
        letzte = f"🏆 {erreicht[-1][1]}"

    naechste_text = "Alle Auszeichnungen erreicht."
    if naechste:
        naechste_text = f"Nächstes Ziel: {naechste[0]} Sticker - {naechste[1]}"

    return f"""
    <html><head>{style()}</head><body>
    <div class="container">
        <a class="btn" href="/">← Hauptmenü</a>

        <h1>VfL Osnabrück</h1>
        <p class="subline">2024/25</p>

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
            <p>Sticker gesamt: {gesammelt} / {TOTAL_VFL}</p>
            <p>Fehlende Sticker: {len(fehlende)}</p>
            <p>Doppelte Sticker: {len(doppelte)}</p>

            <div class="progress">
                <div class="progress-bar" style="width:{prozent}%;"></div>
            </div>
            <p>{prozent}% abgeschlossen</p>
        </div>

        <div class="card">
            <h2>Album-Menü</h2>
            <a class="btn" href="/album/vfl/fehlende">Fehlende</a>
            <a class="btn" href="/album/vfl/doppelte">Doppelte</a>
            <a class="btn" href="/album/vfl/auszeichnungen">Auszeichnungen</a>
        </div>

        <div class="card">
            <h2>Letzte Auszeichnung</h2>
            <p>{letzte}</p>
            <p>{naechste_text}</p>
        </div>
    </div>
    </body></html>
    """


@app.route("/album/vfl/fehlende")
def fehlende_anzeigen():
    fehlende = sorted(lade_liste("fehlende.txt"))

    html = f"""
    <html><head>{style()}</head><body>
    <div class="container">
        <a class="btn" href="/album/vfl">← Zurück zum Album</a>
        <h1>Fehlende Sticker</h1>
        <p class="subline">{len(fehlende)} Sticker fehlen noch.</p>
        <div class="card"><div class="grid">
    """

    for sticker in fehlende:
        html += f'<div class="sticker-box">#{sticker}</div>'

    html += """
        </div></div>
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
    <html><head>{style()}</head><body>
    <div class="container">
        <a class="btn" href="/album/vfl">← Zurück zum Album</a>
        <h1>Doppelte Sticker</h1>
        <p class="subline">{len(doppelte)} doppelte Sticker insgesamt.</p>

        <a class="btn" href="/album/vfl/doppelte?sort=nummer">Nach Nummer</a>
        <a class="btn" href="/album/vfl/doppelte?sort=anzahl">Nach Anzahl</a>

        <div class="card"><div class="grid">
    """

    for sticker, anzahl in liste:
        html += f'<div class="sticker-box">#{sticker}<br>{anzahl}x</div>'

    html += """
        </div></div>
    </div>
    </body></html>
    """
    return html


@app.route("/album/vfl/auszeichnungen")
def auszeichnungen_anzeigen():
    fehlende, doppelte, gesammelt, prozent = lade_vfl_daten()
    awards = auszeichnungen(gesammelt)
    naechste = next((a for a in awards if gesammelt < a[0]), None)

    html = f"""
    <html><head>{style()}</head><body>
    <div class="container">
        <a class="btn" href="/album/vfl">← Zurück zum Album</a>
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


@app.route("/album/em24")
def album_em24():
    return f"""
    <html><head>{style()}</head><body>
    <div class="container">
        <a class="btn" href="/">← Hauptmenü</a>
        <h1>EURO 2024</h1>
        <div class="card">
            <p>Dieses Album richten wir als Nächstes ein.</p>
        </div>
    </div>
    </body></html>
    """


@app.route("/album-hinzufuegen")
def album_hinzufuegen():
    return f"""
    <html><head>{style()}</head><body>
    <div class="container">
        <a class="btn" href="/">← Zurück</a>
        <h1>Album hinzufügen</h1>

        <div class="card">
            <h2>Aus Vorlage wählen</h2>
            <p>VfL Osnabrück 2024/25</p>
            <p>EURO 2024</p>
            <p>Bundesliga 2024/25</p>
        </div>

        <div class="card">
            <h2>Eigenes Album erstellen</h2>
            <p>Kommt als nächster Schritt: Name + Stickeranzahl.</p>
        </div>
    </div>
    </body></html>
    """


app.run(debug=True)