from flask import Flask, request
import sqlite3

app = Flask(__name__)

# -----------------------------------
# DATENBANK
# -----------------------------------

db = sqlite3.connect(
    "collectr.db",
    check_same_thread=False
)

cursor = db.cursor()

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
        }

        .logo-text{
            font-size:34px;
            font-weight:800;
            letter-spacing:7px;
        }

        .subline{
            color:#746a80;
        }

        .card{
            background:white;
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
            100px 1fr 120px;
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
            font-size:22px;
            font-weight:800;
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

        .grid{
            display:grid;
            grid-template-columns:
            repeat(auto-fill,minmax(120px,1fr));
            gap:12px;
        }

        .sticker{
            background:#faf8fc;
            border-radius:16px;
            padding:18px;
            text-align:center;
            font-weight:bold;
        }

        input{
            padding:16px;
            border-radius:14px;
            border:1px solid #ddd3e8;
            width:240px;
            font-size:20px;
        }

    </style>
    """


# -----------------------------------
# ALBUM LADEN
# -----------------------------------

def lade_album(album_id):

    cursor.execute("""

    SELECT *
    FROM albums
    WHERE id = ?

    """, (album_id,))

    daten = cursor.fetchone()

    album = {
        "id": daten[0],
        "name": daten[1],
        "season": daten[2],
        "total": daten[3],
        "complete": daten[4]
    }

    cursor.execute("""

    SELECT *
    FROM stickers
    WHERE album_id = ?

    """, (album_id,))

    sticker = cursor.fetchall()

    gesammelt = 0

    doppelte = []

    for eintrag in sticker:

        gesammelt += 1

        for i in range(eintrag[4]):

            doppelte.append(
                eintrag[2]
            )

    if album["complete"]:

        gesammelt = album["total"]

    prozent = round(
        (gesammelt / album["total"]) * 100
    )

    return (
        album,
        sticker,
        doppelte,
        gesammelt,
        prozent
    )


# -----------------------------------
# STARTSEITE
# -----------------------------------

@app.route("/")
def startseite():

    cursor.execute("""
    SELECT * FROM albums
    """)

    alle_alben = cursor.fetchall()

    kollektion = []

    vitrine = []

    for daten in alle_alben:

        album_id = daten[0]

        (
            album,
            sticker,
            doppelte,
            gesammelt,
            prozent
        ) = lade_album(album_id)

        datenpaket = (
            album_id,
            album,
            gesammelt,
            prozent,
            doppelte
        )

        if prozent >= 100:

            vitrine.append(datenpaket)

        else:

            kollektion.append(datenpaket)

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

        <div class="card">

            <h2>Gesamtübersicht</h2>

            <div class="stats">

                <div class="stat">
                    <div class="big">
                        {len(alle_alben)}
                    </div>

                    <p>Alben</p>
                </div>

                <div class="stat">
                    <div class="big">
                        {len(vitrine)}
                    </div>

                    <p>Komplett</p>
                </div>

                <div class="stat">
                    <div class="big">
                        {len(kollektion)}
                    </div>

                    <p>Aktiv</p>
                </div>

                <div class="stat">
                    <div class="big">
                        🏆
                    </div>

                    <p>Trophäenschrank</p>
                </div>

            </div>

        </div>

        <h1>📚 Kollektion</h1>

        <p class="subline">
        Aktive Sammlungen
        </p>
    """

    for (
        album_id,
        album,
        gesammelt,
        prozent,
        doppelte
    ) in kollektion:

        html += f"""

        <div class="card">

            <a class="album-card"
            href="/album/{album_id}">

                <div class="album-cover">
                    {album["name"][:4]}
                </div>

                <div>

                    <h2>
                    {album["name"]}
                    </h2>

                    <p>
                    {album["season"]}
                    </p>

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

                    <h2>
                    {prozent}%
                    </h2>

                </div>

            </a>

        </div>
        """

    html += """

        <h1>🏛 Vitrine</h1>

        <p class="subline">
        Vollständige Sammlungen
        </p>
    """

    for (
        album_id,
        album,
        gesammelt,
        prozent,
        doppelte
    ) in vitrine:

        html += f"""

        <div class="card">

            <a class="album-card"
            href="/album/{album_id}">

                <div class="album-cover">
                    ✓
                </div>

                <div>

                    <h2>
                    {album["name"]}
                    </h2>

                    <p>
                    Vollständig
                    </p>

                    <div class="progress">

                        <div class="progress-bar"
                        style="width:100%;">
                        </div>

                    </div>

                    <p>
                    {album["total"]}
                    /
                    {album["total"]}
                    Sticker
                    </p>

                </div>

                <div>

                    <h2>
                    100%
                    </h2>

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
# ALBUM
# -----------------------------------

@app.route(
    "/album/<album_id>",
    methods=["GET", "POST"]
)
def album(album_id):

    (
        album,
        sticker,
        doppelte,
        gesammelt,
        prozent
    ) = lade_album(album_id)

    meldung = ""

    if request.method == "POST":

        code = request.form["sticker"]

        cursor.execute("""

        SELECT *
        FROM stickers
        WHERE album_id = ?
        AND sticker_code = ?

        """, (album_id, code))

        vorhanden = cursor.fetchone()

        if vorhanden:

            neue_anzahl = vorhanden[4] + 1

            cursor.execute("""

            UPDATE stickers
            SET duplicates = ?
            WHERE id = ?

            """, (
                neue_anzahl,
                vorhanden[0]
            ))

            meldung = f"""
            {code}
            doppelt erhöht.
            """

        else:

            cursor.execute("""

            INSERT INTO stickers (
                album_id,
                sticker_code,
                status,
                duplicates
            )

            VALUES (?, ?, ?, ?)

            """, (
                album_id,
                code,
                "owned",
                0
            ))

            meldung = f"""
            {code}
            eingetragen.
            """

        db.commit()

        (
            album,
            sticker,
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
        href="/">
            ← Hauptmenü
        </a>

        <h1>
        {album["name"]}
        </h1>

        <p class="subline">
        {album["season"]}
        </p>

        <div class="card">

            <h2>
            Sticker eintragen
            </h2>

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
            {len(doppelte)}
            doppelte Sticker
            </p>

            <div class="progress">

                <div class="progress-bar"
                style="width:{prozent}%;">
                </div>

            </div>

        </div>

        <div class="card">

            <h2>Doppelte Sticker</h2>

            <div class="grid">
    """

    zaehler = {}

    for stickercode in doppelte:

        zaehler[stickercode] = (
            zaehler.get(stickercode, 0) + 1
        )

    for code in zaehler:

        html += f"""

        <div class="sticker">

            {code}
            <br><br>
            {zaehler[code]}x

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