from flask import Flask, request

app = Flask(__name__)

TOTAL = 250


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

        .vfl-bg {
            position: fixed;
            inset: 0;
            opacity: 0.035;
            pointer-events: none;
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 35px;
            padding: 40px;
            z-index: 0;
        }

        .vfl-shield {
            width: 72px;
            height: 86px;
            border: 4px solid #d8b4f8;
            border-radius: 18px 18px 34px 34px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            color: #d8b4f8;
            transform: rotate(-6deg);
        }

        .container {
            position: relative;
            z-index: 2;
            max-width: 950px;
            margin: auto;
            padding-bottom: 190px;
        }

        h1 {
            font-size: 42px;
            margin-bottom: 6px;
        }

        h2 {
            margin-top: 0;
        }

        .subline {
            color: #d9c3e8;
            margin-bottom: 25px;
        }

        .card {
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.14);
            border-radius: 24px;
            padding: 24px;
            margin-bottom: 22px;
            box-shadow: 0 16px 45px rgba(0,0,0,0.28);
            backdrop-filter: blur(6px);
        }

        .top-actions {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 14px;
            margin: 22px 0;
        }

        .btn {
            display: block;
            text-align: center;
            text-decoration: none;
            background: #6b3a8e;
            color: white;
            padding: 20px;
            border-radius: 18px;
            font-size: 20px;
            font-weight: bold;
            border: none;
            cursor: pointer;
        }

        .btn:hover {
            background: #8750ad;
        }

        input {
            font-size: 22px;
            padding: 18px;
            border-radius: 16px;
            border: none;
            width: 230px;
            margin-right: 10px;
        }

        .progress {
            background: rgba(255,255,255,0.16);
            height: 30px;
            border-radius: 30px;
            overflow: hidden;
            margin: 18px 0;
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

        .stadion {
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            height: 170px;
            opacity: 0.30;
            pointer-events: none;
            z-index: 1;
        }

        .mast {
            position: absolute;
            bottom: 28px;
            width: 14px;
            height: 128px;
            background: #050309;
        }

        .mast.left { left: 8%; transform: rotate(-6deg); }
        .mast.right { right: 8%; transform: rotate(6deg); }

        .licht {
            position: absolute;
            top: -12px;
            left: -26px;
            width: 66px;
            height: 22px;
            background: #050309;
            border-radius: 5px;
        }

        .tribuene {
            position: absolute;
            bottom: 0;
            left: 16%;
            width: 68%;
            height: 62px;
            background: #050309;
            border-radius: 100px 100px 0 0;
        }

        .dach {
            position: absolute;
            bottom: 62px;
            left: 20%;
            width: 60%;
            height: 10px;
            background: #050309;
        }

        a { color: white; }
    </style>

    <div class="vfl-bg">
        <div class="vfl-shield">VfL</div><div class="vfl-shield">VfL</div><div class="vfl-shield">VfL</div>
        <div class="vfl-shield">VfL</div><div class="vfl-shield">VfL</div><div class="vfl-shield">VfL</div>
        <div class="vfl-shield">VfL</div><div class="vfl-shield">VfL</div><div class="vfl-shield">VfL</div>
        <div class="vfl-shield">VfL</div><div class="vfl-shield">VfL</div><div class="vfl-shield">VfL</div>
    </div>

    <div class="stadion">
        <div class="mast left"><div class="licht"></div></div>
        <div class="mast right"><div class="licht"></div></div>
        <div class="dach"></div>
        <div class="tribuene"></div>
    </div>
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


@app.route("/", methods=["GET", "POST"])
def startseite():
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

        <h1>VfL Stickeralbum</h1>
        <p class="subline">Digitales Sammel- und Tauschheft.</p>

        <div class="card">
            <h2>Sticker eintragen</h2>
            <form method="POST">
                <input name="sticker" placeholder="Nummer" autofocus>
                <button class="btn" type="submit" style="display:inline-block;width:auto;">Eintragen</button>
            </form>
            <p>{meldung}</p>
        </div>

        <div class="top-actions">
            <a class="btn" href="/fehlende">Fehlende</a>
            <a class="btn" href="/doppelte">Doppelte</a>
            <a class="btn" href="/auszeichnungen">Auszeichnungen</a>
        </div>

        <div class="card">
            <h2>Übersicht</h2>
            <p>Sticker gesamt: {gesammelt} / {TOTAL}</p>
            <p>Fehlende Sticker: {len(fehlende)}</p>
            <p>Doppelte Sticker: {len(doppelte)}</p>

            <div class="progress">
                <div class="progress-bar" style="width:{prozent}%;"></div>
            </div>

            <p>{prozent}% abgeschlossen</p>
        </div>

        <div class="card">
            <h2>🏆 Letzte Auszeichnung</h2>
            <p>{letzte_text}</p>
            <p>{naechste_text}</p>
        </div>

    </div>
    </body>
    </html>
    """


@app.route("/fehlende")
def fehlende_anzeigen():
    fehlende = sorted(lade_liste("fehlende.txt"))

    html = f"""
    <html><head>{basis_style()}</head><body>
    <div class="container">
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

        <a class="btn" href="/">Zurück</a>
    </div>
    </body></html>
    """
    return html


@app.route("/doppelte")
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
        <h1>Doppelte Sticker</h1>
        <p class="subline">{len(doppelte)} doppelte Sticker insgesamt.</p>

        <div class="top-actions">
            <a class="btn" href="/doppelte?sort=nummer">Nach Nummer</a>
            <a class="btn" href="/doppelte?sort=anzahl">Nach Anzahl</a>
            <a class="btn" href="/">Zurück</a>
        </div>

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


@app.route("/auszeichnungen")
def auszeichnungen_anzeigen():
    fehlende = lade_liste("fehlende.txt")
    gesammelt = TOTAL - len(fehlende)
    awards = auszeichnungen(gesammelt)
    naechste = next((a for a in awards if gesammelt < a[0]), None)

    html = f"""
    <html><head>{basis_style()}</head><body>
    <div class="container">
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
        <a class="btn" href="/">Zurück</a>
    </div>
    </body></html>
    """
    return html


app.run(debug=True)