from flask import Flask, request
import ast
import os

app = Flask(__name__)

# -----------------------------------
# ALBEN
# -----------------------------------

alben = {
    "vfl": {
        "name": "VfL Osnabrück",
        "season": "2024/25",
        "total": 250,
        "fehlende_datei": "fehlende.txt",
        "doppelte_datei": "doppelte.txt",
        "typ": "zahlen",
        "cover": "VfL",
        "komplett": False
    },

    "em24": {
        "name": "EURO 2024",
        "season": "Germany",
        "total": 728,
        "fehlende_datei": "em24_fehlende.txt",
        "doppelte_datei": "em24_doppelte.txt",
        "typ": "codes",
        "cover": "EURO",
        "komplett": True
    }
}


# -----------------------------------
# DATEIEN
# -----------------------------------

def lade_liste(dateiname):

    if not os.path.exists(dateiname):
        return []

    with open(dateiname, "r") as datei:

        inhalt = datei.read().strip()

    if inhalt == "":
        return []

    return ast.literal_eval(inhalt)


def speichere_liste(dateiname, liste):

    with open(dateiname, "w") as datei:

        datei.write(str(liste))


# -----------------------------------
# ALBUM LADEN
# -----------------------------------

def lade_album(album_id):

    album = alben[album_id]

    doppelte = lade_liste(
        album["doppelte_datei"]
    )

    if album["komplett"]:

        fehlende = []

    else:

        fehlende = lade_liste(
            album["fehlende_datei"]
        )

    gesammelt = album["total"] - len(fehlende)

    prozent = round(
        (gesammelt / album["total"]) * 100
    )

    return (
        album,
        fehlende,
        doppelte,
        gesammelt,
        prozent
    )


# -----------------------------------
# TROPHÄEN
# -----------------------------------

def auszeichnungen(total):

    liste = [
        (25, "Schulhoftauscher"),
        (50, "Kurvenkenner"),
        (75, "Stickerjäger"),
        (100, "Albumarbeiter"),
        (125, "Halbzeit"),
        (150, "Archivwart"),
        (175, "Sammelstratege"),
        (200, "Vollsortierer"),
        (225, "Endspurt"),
        (total, "Album vollendet")
    ]

    sauber = []

    for ziel, titel in liste:

        if ziel <= total:

            sauber.append(
                (ziel, titel)
            )

    return sauber


# -----------------------------------
# DESIGN
# -----------------------------------

def style():

    return """
    <style>

        body{
            margin:0;
            font-family:Arial,sans-serif;
            background:#f6f3ef;
            color:#19141f;
            padding:34px;
        }

        .container{
            max-width:1100px;
            margin:auto;
            padding-bottom:120px;
        }

        .brand{
            display:flex;
            align-items:center;
            gap:18px;
            margin-bottom:34px;
        }

        .logo{
            width:68px;
            height:68px;
            border-radius:22px;
            background:linear-gradient(
                145deg,
                #24112f,
                #7b3bb0
            );
            color:white;
            display:flex;
            align-items:center;
            justify-content:center;
            font-size:34px;
            font-weight:bold;
            box-shadow:
            0 16px 34px rgba(61,31,90,0.22);
        }

        .logo-text{
            font-size:34px;
            font-weight:800;
            letter-spacing:7px;
        }

        .subline{
            color:#746a80;
            margin-top:4px;
        }

        .card{
            background:white;
            border:1px solid #ebe5f0;
            border-radius:26px;
            padding:26px;
            margin-bottom:24px;
            box-shadow:
            0 12px 34px rgba(0,0,0,0.05);
        }

        .stats{
            display:grid;
            grid-template-columns:
            repeat(4,1fr);
            gap:16px;
        }

        .stat{
            background:#faf8fc;
            border:1px solid #eee7f4;
            border-radius:20px;
            padding:20px;
        }

        .big{
            font-size:36px;
            font-weight:800;
            color:#5d2f86;
        }

        .album-card{
            display:grid;
            grid-template-columns:
            100px 1fr 130px;
            gap:22px;
            align-items:center;
            color:#19141f;
            text-decoration:none;
        }

        .album-cover{
            width:92px;
            height:112px;
            border-radius:18px;
            background:linear-gradient(
                145deg,
                #24112f,
                #7b3bb0
            );
            color:white;
            display:flex;
            align-items:center;
            justify-content:center;
            font-weight:800;
            font-size:22px;
        }

        .progress{
            background:#ece5f3;
            height:24px;
            border-radius:20px;
            overflow:hidden;
            margin-top:12px;
        }

        .progress-bar{
            background:linear-gradient(
                90deg,
                #5d2f86,
                #b07ae0
            );
            height:100%;
        }

        .btn{
            display:inline-block;
            background:#5d2f86;
            color:white;
            text-decoration:none;
            padding:15px 20px;
            border-radius:16px;
            margin:6px;
            border:none;
            cursor:pointer;
            font-weight:bold;
        }

        .btn:hover{
            background:#7540a8;
        }

        .menu-grid{
            display:grid;
            grid-template-columns:
            repeat(2,1fr);
            gap:14px;
        }

        .grid{
            display:grid;
            grid-template-columns:
            repeat(auto-fill,minmax(120px,1fr));
            gap:12px;
        }

        .sticker-box{
            display:block;
            text-decoration:none;
            color:#19141f;
            background:#faf8fc;
            border:1px solid #eee7f4;
            border-radius:16px;
            padding:18px;
            text-align:center;
            font-weight:bold;
        }

        .sticker-box:hover{
            background:#efe6f7;
        }

        .trophy{
            background:white;
            border:1px solid #ebe5f0;
            border-radius:20px;
            padding:22px;
            margin-bottom:14px;
            box-shadow:
            0 10px 24px rgba(0,0,0,0.04);
        }

        .locked{
            opacity:0.35;
            filter:blur(1px);
        }

        input{
            padding:16px;
            border-radius:14px;
            border:1px solid #ddd3e8;
            width:240px;
            font-size:20px;
        }

        h1{
            font-size:42px;
            margin-bottom:8px;
        }

        h2{
            margin-top:0;
        }

    </style>
    """


# -----------------------------------
# STARTSEITE
# -----------------------------------

@app.route("/")
def startseite():

    gesamt_alben = len(alben)

    komplett = 0

    doppelte_gesamt = 0

    fortschritt = 0

    trophäen = 0

    album_daten = []

    for album_id in alben:

        (
            album,
            fehlende,
            doppelte,
            gesammelt,
            prozent
        ) = lade_album(album_id)

        album_daten.append(
            (
                album_id,
                album,
                fehlende,
                doppelte,
                gesammelt,
                prozent
            )
        )

        if gesammelt == album["total"]:

            komplett += 1

        doppelte_gesamt += len(doppelte)

        fortschritt += prozent

        trophäen += len([
            t for t in
            auszeichnungen(album["total"])
            if gesammelt >= t[0]
        ])

    durchschnitt = round(
        fortschritt / gesamt_alben
    )

    html = f"""
    <html>

    <head>
    {style()}
    </head>

    <body>

    <div class="container">

        <div class="brand">

            <div class="logo">
                C
            </div>

            <div>

                <div class="logo-text">
                    COLLECTR
                </div>

                <div class="subline">
                    Collect. Track. Trade.
                </div>

            </div>

        </div>

        <a href="/gesamt"
        style="text-decoration:none;color:inherit;">

        <div class="card">

            <h2>Gesamtübersicht</h2>

            <div class="stats">

                <div class="stat">
                    <div class="big">
                        {gesamt_alben}
                    </div>

                    <p>Alben</p>
                </div>

                <div class="stat">
                    <div class="big">
                        {komplett}
                    </div>

                    <p>Komplett</p>
                </div>

                <div class="stat">
                    <div class="big">
                        {durchschnitt}%
                    </div>

                    <p>Fortschritt</p>
                </div>

                <div class="stat">
                    <div class="big">
                        {doppelte_gesamt}
                    </div>

                    <p>Doppelte</p>
                </div>

            </div>

        </div>

        </a>

        <h1>Meine Alben</h1>
    """

    album_daten = sorted(
        album_daten,
        key=lambda x: x[5],
        reverse=True
    )

    for (
        album_id,
        album,
        fehlende,
        doppelte,
        gesammelt,
        prozent
    ) in album_daten:

        html += f"""

        <div class="card">

            <a class="album-card"
            href="/album/{album_id}">

                <div class="album-cover">
                    {album["cover"]}
                </div>

                <div>

                    <h2>{album["name"]}</h2>

                    <p>{album["season"]}</p>

                    <div class="progress">

                        <div class="progress-bar"
                        style="width:{prozent}%;">
                        </div>

                    </div>

                    <p>
                    {gesammelt}
                    /
                    {album["total"]}
                    Sticker
                    </p>

                </div>

                <div>

                    <h2>{prozent}%</h2>

                </div>

            </a>

        </div>
        """

    html += """
    </div>
    </body>
    </html>
    """

    return html


# -----------------------------------
# GESAMTÜBERSICHT
# -----------------------------------

@app.route("/gesamt")
def gesamt():

    html = f"""
    <html>

    <head>
    {style()}
    </head>

    <body>

    <div class="container">

        <a class="btn" href="/">
            ← Zurück
        </a>

        <h1>Gesamtübersicht</h1>

        <div class="card">

            <h2>Sammlerprofil</h2>

            <p>Alben gesammelt: {len(alben)}</p>

            <p>Erfolgreiche Tausche: 0</p>

            <p>Mitglied seit: Heute 😄</p>

        </div>

        <a class="btn"
        href="/trophaeenschrank">

            🏆 Trophäenschrank

        </a>

    </div>

    </body>
    </html>
    """

    return html


# -----------------------------------
# TROPHÄENSCHRANK
# -----------------------------------

@app.route("/trophaeenschrank")
def trophaeenschrank():

    html = f"""
    <html>

    <head>
    {style()}
    </head>

    <body>

    <div class="container">

        <a class="btn"
        href="/gesamt">
            ← Zurück
        </a>

        <h1>Trophäenschrank</h1>

        <p class="subline">
            Albumübergreifende Auszeichnungen
        </p>
    """

    for album_id in alben:

        (
            album,
            fehlende,
            doppelte,
            gesammelt,
            prozent
        ) = lade_album(album_id)

        trophäen = auszeichnungen(
            album["total"]
        )

        for ziel, titel in trophäen:

            if gesammelt >= ziel:

                html += f"""

                <div class="trophy">

                    <h2>
                    🏆 {titel}
                    </h2>

                    <p>
                    Album:
                    {album["name"]}
                    </p>

                    <p>
                    {ziel}
                    Sticker gesammelt
                    </p>

                </div>
                """

    html += """
    </div>
    </body>
    </html>
    """

    return html


# -----------------------------------
# ALBUM
# -----------------------------------

@app.route(
    "/album/<album_id>",
    methods=["GET", "POST"]
)
def album(album_id):

    (
        album,
        fehlende,
        doppelte,
        gesammelt,
        prozent
    ) = lade_album(album_id)

    meldung = ""

    if request.method == "POST":

        sticker = request.form["sticker"]

        if album["typ"] == "zahlen":

            sticker = int(sticker)

        if sticker in fehlende:

            fehlende.remove(sticker)

            meldung = f"""
            {sticker}
            wurde eingetragen.
            """

        else:

            doppelte.append(sticker)

            meldung = f"""
            {sticker}
            ist doppelt.
            """

        speichere_liste(
            album["fehlende_datei"],
            fehlende
        )

        speichere_liste(
            album["doppelte_datei"],
            doppelte
        )

    return f"""
    <html>

    <head>
    {style()}
    </head>

    <body>

    <div class="container">

        <a class="btn"
        href="/">
            ← Hauptmenü
        </a>

        <h1>{album["name"]}</h1>

        <p class="subline">
            {album["season"]}
        </p>

        <div class="card">

            <h2>Sticker eintragen</h2>

            <form method="POST">

                <input
                name="sticker"
                placeholder="Sticker">

                <button class="btn">
                    Eintragen
                </button>

            </form>

            <p>{meldung}</p>

        </div>

        <div class="card">

            <h2>Albumübersicht</h2>

            <p>
            {gesammelt}
            /
            {album["total"]}
            Sticker gesammelt
            </p>

            <p>
            {len(fehlende)}
            fehlend
            </p>

            <p>
            {len(doppelte)}
            doppelt
            </p>

            <div class="progress">

                <div class="progress-bar"
                style="width:{prozent}%;">
                </div>

            </div>

        </div>

        <div class="card">

            <h2>Album-Menü</h2>

            <div class="menu-grid">

                <a class="btn"
                href="/album/{album_id}/fehlende">
                    Fehlende
                </a>

                <a class="btn"
                href="/album/{album_id}/doppelte">
                    Doppelte
                </a>

            </div>

        </div>

    </div>

    </body>
    </html>
    """


# -----------------------------------
# FEHLENDE
# -----------------------------------

@app.route("/album/<album_id>/fehlende")
def fehlende(album_id):

    (
        album,
        fehlende,
        doppelte,
        gesammelt,
        prozent
    ) = lade_album(album_id)

    html = f"""
    <html>

    <head>
    {style()}
    </head>

    <body>

    <div class="container">

        <a class="btn"
        href="/album/{album_id}">
            ← Zurück
        </a>

        <h1>Fehlende Sticker</h1>

        <div class="card">

            <div class="grid">
    """

    for sticker in sorted(
        fehlende,
        key=str
    ):

        html += f"""

        <div class="sticker-box">

            {sticker}

        </div>
        """

    html += """
            </div>
        </div>
    </div>
    </body>
    </html>
    """

    return html


# -----------------------------------
# DOPPELTE
# -----------------------------------

@app.route("/album/<album_id>/doppelte")
def doppelte(album_id):

    (
        album,
        fehlende,
        doppelte,
        gesammelt,
        prozent
    ) = lade_album(album_id)

    gezaehlt = {}

    for sticker in doppelte:

        gezaehlt[sticker] = (
            gezaehlt.get(sticker, 0) + 1
        )

    html = f"""
    <html>

    <head>
    {style()}
    </head>

    <body>

    <div class="container">

        <a class="btn"
        href="/album/{album_id}">
            ← Zurück
        </a>

        <h1>Doppelte Sticker</h1>

        <div class="card">

            <div class="grid">
    """

    for sticker in gezaehlt:

        html += f"""

        <div class="sticker-box">

            {sticker}
            <br><br>
            {gezaehlt[sticker]}x

        </div>
        """

    html += """
            </div>
        </div>
    </div>
    </body>
    </html>
    """

    return html


app.run(debug=True)