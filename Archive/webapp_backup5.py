from flask import Flask, request, redirect

app = Flask(__name__)

# -----------------------------

# ALBUM DATEN

# -----------------------------

alben = {

    "vfl": {

        "name": "VfL Osnabrück",

        "season": "2024/25",

        "total": 250,

        "fehlende_datei": "fehlende.txt",

        "doppelte_datei": "doppelte.txt",

        "typ": "zahlen"

    },

    "em24": {

        "name": "EURO 2024",

        "season": "Germany",

        "total": 728,

        "fehlende_datei": "em24_fehlende.txt",

        "doppelte_datei": "em24_doppelte.txt",

        "typ": "codes"

    }

}

# -----------------------------

# DATEIEN

# -----------------------------

def lade_liste(dateiname):

    with open(dateiname, "r") as datei:

        return eval(datei.read())

def speichere_liste(dateiname, liste):

    with open(dateiname, "w") as datei:

        datei.write(str(liste))

# -----------------------------

# ALBUM DATEN LADEN

# -----------------------------

def lade_album(album_id):

    album = alben[album_id]

    fehlende = lade_liste(album["fehlende_datei"])

    doppelte = lade_liste(album["doppelte_datei"])

    gesammelt = album["total"] - len(fehlende)

    prozent = round(

        (gesammelt / album["total"]) * 100

    )

    return album, fehlende, doppelte, gesammelt, prozent

# -----------------------------

# DESIGN

# -----------------------------

def style():

    return """

    <style>

        body {

            margin:0;

            font-family:Arial,sans-serif;

            background:linear-gradient(180deg,#16091f,#2a1238);

            color:white;

            padding:30px;

        }

        .container{

            max-width:1100px;

            margin:auto;

            padding-bottom:120px;

        }

        .logo-wrap{

            display:flex;

            align-items:center;

            gap:18px;

            margin-bottom:30px;

        }

        .logo-icon{

            width:65px;

            height:65px;

            border-radius:20px;

            background:linear-gradient(145deg,#6b3a8e,#d1a6ff);

            display:flex;

            align-items:center;

            justify-content:center;

            font-size:34px;

            font-weight:bold;

        }

        .logo-text{

            font-size:34px;

            font-weight:bold;

            letter-spacing:7px;

        }

        .subline{

            color:#d8c8e4;

        }

        .card{

            background:rgba(255,255,255,0.08);

            border:1px solid rgba(255,255,255,0.1);

            border-radius:24px;

            padding:24px;

            margin-bottom:24px;

            box-shadow:0 12px 35px rgba(0,0,0,0.28);

        }

        .btn{

            display:inline-block;

            background:#6b3a8e;

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

            background:#8750ad;

        }

        input{

            padding:16px;

            border-radius:14px;

            border:none;

            width:240px;

            font-size:20px;

        }

        .album-card{

            display:grid;

            grid-template-columns:100px 1fr 120px;

            gap:20px;

            align-items:center;

            color:white;

            text-decoration:none;

        }

        .album-cover{

            width:90px;

            height:110px;

            border-radius:18px;

            background:linear-gradient(145deg,#3a1450,#8b52b5);

            display:flex;

            align-items:center;

            justify-content:center;

            font-size:22px;

            font-weight:bold;

        }

        .progress{

            background:rgba(255,255,255,0.12);

            height:24px;

            border-radius:20px;

            overflow:hidden;

            margin-top:12px;

        }

        .progress-bar{

            background:linear-gradient(90deg,#9a63c7,#d8b4f8);

            height:100%;

        }

        .grid{

            display:grid;

            grid-template-columns:repeat(auto-fill,minmax(120px,1fr));

            gap:12px;

        }

        .sticker-box{

            display:block;

            color:white;

            text-decoration:none;

            background:rgba(255,255,255,0.09);

            border:1px solid rgba(255,255,255,0.12);

            border-radius:16px;

            padding:18px;

            text-align:center;

            font-weight:bold;

        }

        .sticker-box:hover{

            background:rgba(255,255,255,0.16);

        }

        .menu-grid{

            display:grid;

            grid-template-columns:repeat(2,1fr);

            gap:14px;

        }

    </style>

    """

# -----------------------------

# STARTSEITE

# -----------------------------

@app.route("/")

def startseite():

    html = f"""

    <html>

    <head>{style()}</head>

    <body>

    <div class="container">

        <div class="logo-wrap">

            <div class="logo-icon">

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

        <h1>Meine Alben</h1>

    """

    for album_id in alben:

        album, fehlende, doppelte, gesammelt, prozent = lade_album(album_id)

        html += f"""

        <div class="card">

            <a class="album-card"

            href="/album/{album_id}">

                <div class="album-cover">

                    {album_id.upper()}

                </div>

                <div>

                    <h2>{album['name']}</h2>

                    <p>{album['season']}</p>

                    <div class="progress">

                        <div class="progress-bar"

                        style="width:{prozent}%;">

                        </div>

                    </div>

                    <p>

                    {gesammelt} / {album['total']} Sticker

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

# -----------------------------

# ALBUM

# -----------------------------

@app.route("/album/<album_id>", methods=["GET", "POST"])

def album(album_id):

    album, fehlende, doppelte, gesammelt, prozent = lade_album(album_id)

    meldung = ""

    if request.method == "POST":

        sticker = request.form["sticker"]

        if album["typ"] == "zahlen":

            sticker = int(sticker)

        if sticker in fehlende:

            fehlende.remove(sticker)

            meldung = f"{sticker} wurde eingetragen."

        else:

            doppelte.append(sticker)

            meldung = f"{sticker} ist doppelt."

        speichere_liste(

            album["fehlende_datei"],

            fehlende

        )

        speichere_liste(

            album["doppelte_datei"],

            doppelte

        )

        album, fehlende, doppelte, gesammelt, prozent = lade_album(album_id)

    return f"""

    <html>

    <head>{style()}</head>

    <body>

    <div class="container">

        <a class="btn" href="/">

            ← Hauptmenü

        </a>

        <h1>{album['name']}</h1>

        <p class="subline">

            {album['season']}

        </p>

        <div class="card">

            <h2>Sticker eintragen</h2>

            <form method="POST">

                <input

                name="sticker"

                placeholder="Sticker ID">

                <button class="btn">

                    Eintragen

                </button>

            </form>

            <p>{meldung}</p>

        </div>

        <div class="card">

            <h2>Albumübersicht</h2>

            <p>

            Sticker gesamt:

            {gesammelt} / {album['total']}

            </p>

            <p>

            Fehlende Sticker:

            {len(fehlende)}

            </p>

            <p>

            Doppelte Sticker:

            {len(doppelte)}

            </p>

            <div class="progress">

                <div class="progress-bar"

                style="width:{prozent}%;">

                </div>

            </div>

            <p>{prozent}% abgeschlossen</p>

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

# -----------------------------

# FEHLENDE

# -----------------------------

@app.route("/album/<album_id>/fehlende")

def fehlende(album_id):

    album, fehlende, doppelte, gesammelt, prozent = lade_album(album_id)

    html = f"""

    <html>

    <head>{style()}</head>

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

    for sticker in sorted(fehlende, key=str):

        html += f"""

        <a class="sticker-box"

        href="/album/{album_id}/sticker/{sticker}">

            {sticker}

        </a>

        """

    html += """

            </div>

        </div>

    </div>

    </body>

    </html>

    """

    return html

# -----------------------------

# DOPPELTE

# -----------------------------

@app.route("/album/<album_id>/doppelte")

def doppelte(album_id):

    album, fehlende, doppelte, gesammelt, prozent = lade_album(album_id)

    gezaehlt = {}

    for sticker in doppelte:

        gezaehlt[sticker] = gezaehlt.get(sticker, 0) + 1

    html = f"""

    <html>

    <head>{style()}</head>

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

        <a class="sticker-box"

        href="/album/{album_id}/sticker/{sticker}">

            {sticker}

            <br><br>

            {gezaehlt[sticker]}x

        </a>

        """

    html += """

            </div>

        </div>

    </div>

    </body>

    </html>

    """

    return html

# -----------------------------

# STICKER DETAIL

# -----------------------------

@app.route("/album/<album_id>/sticker/<sticker>")

def sticker(album_id, sticker):

    album, fehlende, doppelte, gesammelt, prozent = lade_album(album_id)

    doppelt = doppelte.count(sticker)

    status = "Vorhanden"

    if sticker in fehlende:

        status = "Fehlt"

    return f"""

    <html>

    <head>{style()}</head>

    <body>

    <div class="container">

        <a class="btn"

        href="/album/{album_id}">

            ← Zurück

        </a>

        <h1>{sticker}</h1>

        <div class="card">

            <p>Status: {status}</p>

            <p>Doppelt: {doppelt}x</p>

        </div>

        <div class="card">

            <a class="btn"

            href="/album/{album_id}/remove_missing/{sticker}">

                Aus fehlende entfernen

            </a>

            <a class="btn"

            href="/album/{album_id}/remove_double/{sticker}">

                Einmal aus doppelte entfernen

            </a>

        </div>

    </div>

    </body>

    </html>

    """

# -----------------------------

# REMOVE

# -----------------------------

@app.route("/album/<album_id>/remove_missing/<sticker>")

def remove_missing(album_id, sticker):

    album = alben[album_id]

    fehlende = lade_liste(

        album["fehlende_datei"]

    )

    if album["typ"] == "zahlen":

        sticker = int(sticker)

    if sticker in fehlende:

        fehlende.remove(sticker)

        speichere_liste(

            album["fehlende_datei"],

            fehlende

        )

    return redirect(

        f"/album/{album_id}"

    )

@app.route("/album/<album_id>/remove_double/<sticker>")

def remove_double(album_id, sticker):

    album = alben[album_id]

    doppelte = lade_liste(

        album["doppelte_datei"]

    )

    if album["typ"] == "zahlen":

        sticker = int(sticker)

    if sticker in doppelte:

        doppelte.remove(sticker)

        speichere_liste(

            album["doppelte_datei"],

            doppelte

        )

    return redirect(

        f"/album/{album_id}"

    )

app.run(debug=True)