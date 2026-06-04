from flask import Flask, request, redirect
import sqlite3

app = Flask(__name__)

db = sqlite3.connect(
    "collectr.db",
    check_same_thread=False
)

db.row_factory = sqlite3.Row

cursor = db.cursor()


# -----------------------------------
# DESIGN
# -----------------------------------

def style():

    return """
    <style>

    body{
        margin:0;
        background:#f6f3ef;
        font-family:Arial;
        color:#1b1620;
        padding:30px;
    }

    .container{
        max-width:1200px;
        margin:auto;
        padding-bottom:120px;
    }

    .brand{
        display:flex;
        align-items:center;
        gap:20px;
        margin-bottom:40px;
    }

    .logo{
        width:72px;
        height:72px;
        border-radius:22px;
        background:linear-gradient(
            145deg,
            #251131,
            #7a3cb0
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
        color:#72697c;
    }

    .card{
        background:white;
        border-radius:28px;
        padding:28px;
        margin-bottom:24px;
        box-shadow:
        0 12px 34px rgba(0,0,0,0.05);
    }

    .stats{
        display:grid;
        grid-template-columns:
        repeat(4,1fr);
        gap:18px;
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

    .btn{
        display:inline-block;
        background:#5d2f86;
        color:white;
        text-decoration:none;
        padding:14px 20px;
        border-radius:16px;
        margin:6px;
        font-weight:bold;
    }

    .btn:hover{
        background:#7540a8;
    }

    .album-card{
        display:grid;
        grid-template-columns:
        110px 1fr 120px;
        gap:24px;
        align-items:center;
        text-decoration:none;
        color:#1b1620;
    }

    .album-cover{
        width:100px;
        height:120px;
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
        height:22px;
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

    .wall{
        display:grid;
        grid-template-columns:
        repeat(auto-fill,minmax(70px,1fr));
        gap:10px;
    }

    .slot{
        border-radius:14px;
        padding:18px 8px;
        text-align:center;
        font-weight:bold;
        transition:0.2s;
    }

    .slot:hover{
        transform:scale(1.05);
    }

    .missing{
        background:#d9d5dc;
        color:#6b6570;
    }

    .owned{
        background:#b7efc1;
        color:#125226;
    }

    .duplicate{
        background:#d8b4fe;
        color:#4a166c;
    }

    input{
        padding:16px;
        border-radius:14px;
        border:1px solid #ddd3e8;
        width:220px;
        font-size:18px;
    }

    .sticker-big{
        width:140px;
        padding:30px;
        text-align:center;
        font-size:28px;
        margin-bottom:24px;
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
        "id": daten["id"],
        "name": daten["name"],
        "season": daten["season"],
        "total": daten["total"],
        "complete": daten["complete"]
    }

    cursor.execute("""
    SELECT *
    FROM stickers
    WHERE album_id = ?
    """, (album_id,))

    sticker = cursor.fetchall()

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

    if album["complete"]:

        gesammelt = album["total"]

    prozent = round(
        (gesammelt / album["total"]) * 100
    )

    return (
        album,
        status,
        gesammelt,
        doppelte,
        prozent
    )


# -----------------------------------
# START
# -----------------------------------

@app.route("/")
def startseite():

    cursor.execute("""
    SELECT *
    FROM albums
    """)

    daten = cursor.fetchall()

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
    """

    for albumdaten in daten:

        album_id = albumdaten["id"]

        (
            album,
            status,
            gesammelt,
            doppelte,
            prozent
        ) = lade_album(album_id)

        html += f"""

        <div class="stat">

            <div class="big">
                {prozent}%
            </div>

            <p>
                {album["name"]}
            </p>

        </div>
        """

    html += """

            </div>

            <br>

            <a class="btn"
            href="/trophaeen">
                🏆 Trophäenschrank
            </a>

            <a class="btn"
            href="/statistik">
                📊 Statistik
            </a>

        </div>

        <h1>📚 Kollektion</h1>
    """

    for albumdaten in daten:

        album_id = albumdaten["id"]

        (
            album,
            status,
            gesammelt,
            doppelte,
            prozent
        ) = lade_album(album_id)

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

    </div>

    </body>

    </html>
    """

    return html


# -----------------------------------
# ALBUM
# -----------------------------------

@app.route("/album/<album_id>")
def album(album_id):

    (
        album,
        status,
        gesammelt,
        doppelte,
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

            <h2>Albumübersicht</h2>

            <p>
            {gesammelt}
            /
            {album["total"]}
            Sticker gesammelt
            </p>

            <p>
            {doppelte}
            doppelte Sticker
            </p>

            <div class="progress">

                <div class="progress-bar"
                style="width:{prozent}%;">
                </div>

            </div>

        </div>

        <div class="card">

            <h2>Sammlung</h2>

            <div class="wall">
    """

    for nummer in range(
        1,
        album["total"] + 1
    ):

        code = str(nummer)

        klasse = "missing"

        if code in status:

            klasse = status[code]

        html += f"""

        <a
        href="/sticker/{album_id}/{code}"
        style="text-decoration:none;">

            <div class="slot {klasse}">
                {code}
            </div>

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


# -----------------------------------
# STICKER DETAIL
# -----------------------------------

@app.route("/sticker/<album_id>/<code>")
def sticker(album_id, code):

    cursor.execute("""

    SELECT *
    FROM stickers
    WHERE album_id = ?
    AND sticker_code = ?

    """, (album_id, code))

    daten = cursor.fetchone()

    quantity = 0

    if daten:

        quantity = daten["quantity"]

    if quantity == 0:

        farbe = "missing"
        status = "Fehlt"

    elif quantity == 1:

        farbe = "owned"
        status = "Vorhanden"

    else:

        farbe = "duplicate"
        status = "Doppelt"

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

        <div class="card">

            <h1>
            Sticker {code}
            </h1>

            <div class="slot sticker-big {farbe}">
                {code}
            </div>

            <h2>
            {status}
            </h2>

            <p>
            Anzahl:
            {quantity}
            </p>

            <br>

            <a class="btn"
            href="/add/{album_id}/{code}">
                ➕ Hinzufügen
            </a>

            <a class="btn"
            href="/remove/{album_id}/{code}">
                ➖ Entfernen
            </a>

        </div>

    </div>

    </body>

    </html>
    """

    return html


# -----------------------------------
# ADD
# -----------------------------------

@app.route("/add/<album_id>/<code>")
def add(album_id, code):

    cursor.execute("""

    SELECT *
    FROM stickers
    WHERE album_id = ?
    AND sticker_code = ?

    """, (album_id, code))

    daten = cursor.fetchone()

    if daten:

        neue_quantity = daten["quantity"] + 1

        neue_duplicates = max(
            neue_quantity - 1,
            0
        )

        cursor.execute("""

        UPDATE stickers
        SET quantity = ?,
            duplicates = ?
        WHERE id = ?

        """, (
            neue_quantity,
            neue_duplicates,
            daten["id"]
        ))

    else:

        cursor.execute("""

        INSERT INTO stickers (
            album_id,
            sticker_code,
            status,
            duplicates,
            quantity
        )

        VALUES (?, ?, ?, ?, ?)

        """, (
            album_id,
            code,
            "owned",
            0,
            1
        ))

    db.commit()

    return redirect(
        f"/sticker/{album_id}/{code}"
    )


# -----------------------------------
# REMOVE
# -----------------------------------

@app.route("/remove/<album_id>/<code>")
def remove(album_id, code):

    cursor.execute("""

    SELECT *
    FROM stickers
    WHERE album_id = ?
    AND sticker_code = ?

    """, (album_id, code))

    daten = cursor.fetchone()

    if daten:

        neue_quantity = max(
            daten["quantity"] - 1,
            0
        )

        neue_duplicates = max(
            neue_quantity - 1,
            0
        )

        if neue_quantity == 0:

            cursor.execute("""

            DELETE FROM stickers
            WHERE id = ?

            """, (daten["id"],))

        else:

            cursor.execute("""

            UPDATE stickers
            SET quantity = ?,
                duplicates = ?
            WHERE id = ?

            """, (
                neue_quantity,
                neue_duplicates,
                daten["id"]
            ))

        db.commit()

    return redirect(
        f"/sticker/{album_id}/{code}"
    )


# -----------------------------------
# TROPHÄEN
# -----------------------------------

@app.route("/trophaeen")
def trophaeen():

    return f"""
    <html>

    <head>
    {style()}
    </head>

    <body>

    <div class="container">

        <a class="btn"
        href="/">
            ← Zurück
        </a>

        <div class="card">

            <h1>
            🏆 Trophäenschrank
            </h1>

            <p>
            EURO 2024 abgeschlossen
            </p>

            <p>
            Weitere Trophäen folgen 😄
            </p>

        </div>

    </div>

    </body>

    </html>
    """


# -----------------------------------
# STATISTIK
# -----------------------------------

@app.route("/statistik")
def statistik():

    cursor.execute("""
    SELECT COUNT(*)
    FROM stickers
    """)

    gesammelt = cursor.fetchone()[0]

    cursor.execute("""
    SELECT SUM(duplicates)
    FROM stickers
    """)

    doppelte = cursor.fetchone()[0]

    if doppelte is None:

        doppelte = 0

    return f"""
    <html>

    <head>
    {style()}
    </head>

    <body>

    <div class="container">

        <a class="btn"
        href="/">
            ← Zurück
        </a>

        <div class="card">

            <h1>
            📊 Statistik
            </h1>

            <div class="stats">

                <div class="stat">

                    <div class="big">
                        {gesammelt}
                    </div>

                    <p>
                    Gesammelte Sticker
                    </p>

                </div>

                <div class="stat">

                    <div class="big">
                        {doppelte}
                    </div>

                    <p>
                    Doppelte Sticker
                    </p>

                </div>

            </div>

        </div>

    </div>

    </body>

    </html>
    """


app.run(debug=True)