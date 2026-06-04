from flask import Flask, request, redirect, session
import sqlite3
from em24_data import build_em24

from urllib.parse import quote

app = Flask(__name__)
app.secret_key = "sammlr_dev_secret"

CURRENT_USER_ID = 1

DB = "Database/collectr.db"

def get_db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


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

    try:
        cur.execute("ALTER TABLE stickers ADD COLUMN user_id INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass

    cur.execute("""
    INSERT OR IGNORE INTO users (id, username, password)
    VALUES (1, 'valentin', '1234')
    """)

    con.commit()
    con.close()

   


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
        .hero-header{
    display:flex;
    justify-content:space-between;
    align-items:center;
    background:linear-gradient(135deg,#12051f,#2b0f46);
    border:1px solid rgba(123,61,255,.28);
    border-radius:28px;
    padding:18px 24px;
    margin-bottom:32px;
    box-shadow:0 18px 40px rgba(45,15,86,.18);
}

.hero-logo{
    width:190px;
    display:block;
}

.hero-actions{
    display:flex;
    gap:8px;
    align-items:center;
}

.beta-pill,.hero-link{
    color:white;
    text-decoration:none;
    background:rgba(255,255,255,.08);
    border:1px solid rgba(255,255,255,.18);
    border-radius:999px;
    padding:10px 14px;
    font-weight:800;
    font-size:13px;
}

.hero-link:hover{
    transform:translateY(-2px);
    background:rgba(123,61,255,.28);
}
    transition:.25s;
    .main-logo:hover{
    transform:scale(1.02);
}
        .subline{color:#72697c;}
        .card{background:white;border-radius:28px;padding:28px;margin-bottom:24px;box-shadow:0 12px 34px rgba(0,0,0,.05);}
        .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;}
        .stat-album{
    background:white;
    border-radius:28px;
    padding:28px;
    margin-bottom:24px;
    box-shadow:0 12px 34px rgba(0,0,0,.05);
    border:1px solid rgba(93,47,134,.08);
}

.home-intro{
    background:linear-gradient(135deg,#ffffff,#f4eefb);
    border:1px solid rgba(93,47,134,.10);
    border-radius:32px;
    padding:34px;
    margin-bottom:28px;
    box-shadow:0 18px 42px rgba(0,0,0,.045);
}

.home-intro h1{
    margin:0 0 10px 0;
    font-size:38px;
    letter-spacing:-1px;
}

.home-intro p{
    margin:0;
    color:#72697c;
    font-size:17px;
}

.home-section-title{
    margin-top:34px;
    margin-bottom:6px;
    font-size:26px;
}
.stat-grid-mini{
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(120px,1fr));
    gap:14px;
    margin:18px 0;
}

.mini-box{
    background:#faf8fc;
    border-radius:20px;
    padding:18px;
    text-align:center;
}

.mini-big{
    font-size:30px;
    font-weight:900;
    color:#5d2f86;
}

.album-percent{
    display:flex;
    justify-content:flex-end;
}

.album-percent-circle{
    width:82px;
    height:82px;
    border-radius:50%;
    background:linear-gradient(145deg,#5d2f86,#b07ae0);
    color:white;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:22px;
    font-weight:900;
    box-shadow:
        0 10px 24px rgba(93,47,134,.22),
        inset 0 1px 0 rgba(255,255,255,.18);
}
.album-progress{
    height:14px;
    background:#ece5f3;
    border-radius:20px;
    overflow:hidden;
    margin-top:18px;
}

.album-progress-fill{
    height:100%;
    background:linear-gradient(90deg,#5d2f86,#b07ae0);
}

.trophy-popup-overlay{
    position:fixed;
    inset:0;
    background:rgba(12,8,18,.55);
    backdrop-filter:blur(10px);
    display:flex;
    align-items:center;
    justify-content:center;
    z-index:9999;
    animation:fadeIn .25s ease;
}

.trophy-popup{
    width:420px;
    max-width:90%;
    background:linear-gradient(145deg,#1a1024,#2b1742);
    border:1px solid rgba(176,122,224,.18);
    border-radius:34px;
    padding:34px;
    box-shadow:
        0 30px 70px rgba(0,0,0,.38),
        0 0 0 1px rgba(255,255,255,.03) inset;
    color:white;
    text-align:center;
    animation:popupUp .28s ease;
}

.trophy-popup-patch{
    width:92px;
    height:92px;
    border-radius:28px;
    margin:0 auto 20px auto;
    background:linear-gradient(145deg,#5d2f86,#b07ae0);
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:42px;
    box-shadow:
        0 14px 30px rgba(123,61,255,.35),
        inset 0 1px 0 rgba(255,255,255,.18);
}

.trophy-popup h2{
    margin:0;
    font-size:30px;
    letter-spacing:-1px;
}

.trophy-popup p{
    color:#d6cbe2;
    margin-top:12px;
    line-height:1.5;
}

.popup-button{
    margin-top:26px;
    background:white;
    color:#2b1742;
    border:none;
    border-radius:999px;
    padding:14px 22px;
    font-weight:800;
    cursor:pointer;
    transition:.2s;
    width:100%;
    font-family:Arial;
    text-align:center;
    text-decoration:none;
    display:block;
    box-sizing:border-box;
    font-size:18px;
    font-weight:800;
    position:relative;
    z-index:5;
}

.popup-button:hover{
    transform:translateY(-2px);
}

@keyframes popupUp{
    from{
        opacity:0;
        transform:translateY(18px) scale(.96);
    }
    to{
        opacity:1;
        transform:translateY(0) scale(1);
    }
}

@keyframes fadeIn{
    from{opacity:0;}
    to{opacity:1;}
}

.trophy-info{
    margin-top:16px;
    font-weight:800;
    color:#5d2f86;
}

.popup-actions{
    display:flex;
    flex-direction:column;
    gap:10px;
    margin-top:18px;
}

.popup-button{
    width:100%;
    font-family:Arial;
    text-align:center;
    text-decoration:none;
    display:block;
    box-sizing:border-box;
}

.popup-button:hover{
    transform:translateY(-3px) scale(1.02);
}
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
        .album-card{
    display:grid;
    grid-template-columns:120px 1fr 120px;
    gap:26px;
    align-items:center;
    text-decoration:none;
    color:#1b1620;
    background:linear-gradient(135deg,#ffffff,#faf7ff);
    border:1px solid rgba(93,47,134,.10);
    border-radius:26px;
    padding:18px;
    transition:.25s;
}

.album-card:hover{
    transform:translateY(-4px) scale(1.01);
    box-shadow:0 18px 42px rgba(93,47,134,.14);
}
        .album-cover{
    width:110px;
    height:140px;
    border-radius:24px;
    background:linear-gradient(145deg,#24112f,#7b3bdb);
    color:white;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:28px;
    font-weight:900;
    letter-spacing:-1px;
    box-shadow:
        0 12px 26px rgba(93,47,134,.25),
        inset 0 1px 0 rgba(255,255,255,.18);
    position:relative;
    overflow:hidden;
}

.album-cover::after{
    content:"";
    position:absolute;
    top:0;
    left:-40%;
    width:60%;
    height:100%;
    background:rgba(255,255,255,.10);
    transform:skewX(-20deg);
}
        .progress{background:#ece5f3;height:22px;border-radius:20px;overflow:hidden;margin-top:12px;}
        .progress-bar{background:linear-gradient(90deg,#5d2f86,#b07ae0);height:100%;}
        .wall{display:grid;grid-template-columns:repeat(auto-fill,minmax(78px,1fr));gap:10px;overflow:visible;}
        .slot{border-radius:14px;padding:14px 6px;text-align:center;font-weight:bold;transition:.2s;display:flex;align-items:center;justify-content:center;min-height:46px;text-decoration:none;font-size:13px;line-height:1.15;overflow:visible;word-break:break-word;position:relative;}
        .trigger-slot{
            animation:triggerGlow 1.2s ease;
            box-shadow:
                0 0 12px rgba(255,215,0,.7),
                0 0 28px rgba(168,85,247,.55);
            border:2px solid rgba(255,215,0,.75);
    }
.trigger-slot{
    animation:triggerGlow 1.2s ease;
    box-shadow:
        0 0 12px rgba(255,215,0,.7),
        0 0 28px rgba(168,85,247,.55);
    border:2px solid rgba(255,215,0,.75);
}
        .mini-patch{
            position:absolute;
            top:6px;
            right:6px;
            width:22px;
            height:22px;
            border-radius:999px;
            background:linear-gradient(145deg,#c084fc,#7c3aed);
            color:white;
            display:flex;
            align-items:center;
            justify-content:center;
            font-size:11px;
            box-shadow:0 6px 16px rgba(124,58,237,.28);
            animation:patchPop .45s ease;
            z-index:20;
    }

@keyframes patchPop{
    from{
        transform:scale(.4);
        opacity:0;
    }
    to{
        transform:scale(1);
        opacity:1;
    }
}
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

.filter-bar{
    display:flex;
    gap:12px;
    margin:18px 0 22px;
    flex-wrap:wrap;
}

.filter-btn{
    border-radius:18px;
    padding:12px 18px;
    font-weight:800;
    text-decoration:none;
    transition:.2s ease;
}

.filter-btn:hover{
    transform:translateY(-2px);
}

.filter-btn.active{
    background:#5b2a86;
    color:white;
    box-shadow:0 8px 22px rgba(91,42,134,.25);
}

.album-tab{
    background:#fff3c4;
    color:#4b3510;
}

.duplicate-tab{
    background:#ead7ff;
    color:#3c1466;
}
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

def album_doppelte_trophaeen():
    return [
     
        (5, "Doppelgänger"),
        (10, "Double Trouble"),
        (25, "Twincoolector"),
        (50, "Double Sieger"),
        (100, "Duplikat-Dealer"),
        (250, "Patch-Horter"),
        (500, "Doppelter Wahnsinn"),
        
    ]

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
    <div class="hero-header">
    <div class="hero-brand">
        <img src="/static/collectr_logo.png" class="hero-logo">
    </div>

    <div class="hero-actions">
    <span class="beta-pill">BETA</span>

    <a class="hero-link" href="/statistik">
        📊 Statistik
    </a>

    <a class="hero-link" href="/trophaeen">
        🏆 Trophäen
    </a>

    <a class="hero-link" href="#">
        👤 Profil
    </a>
</div>
</div>
"""
    

    html += """
    <div class="home-intro">
        <h1>Meine Sammlung</h1>
        <p>Deine aktiven Alben, abgeschlossenen Sammlungen und kommenden Collectr-Welten.</p>
    </div>

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


@app.route("/album/<album_id>", methods=["GET", "POST"])
def albumseite(album_id):
    filter_name = request.args.get("filter", "all")
    show_album = filter_name in ("all", "album")
    show_duplicates = filter_name in ("all", "duplicates")
    message = request.args.get("message", "")
    trophy = request.args.get("trophy", "")
    count = request.args.get("count", "1")
    anzahl = int(count)
    trigger = request.args.get("trigger", "")
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

    """
    html += f"""
<div class="card">
    <h2>Sticker verwalten</h2>

    <div class="sticker-action-grid">
        <form method="POST">
            <input name="sticker" placeholder="Sticker ID hinzufügen">
            <button class="btn green" name="aktion" value="add" type="submit">Hinzufügen</button>
        </form>

        <form method="POST">
            <input name="sticker" placeholder="Sticker ID entfernen">
            <button class="btn gray" name="aktion" value="remove" type="submit">Entfernen</button>
        </form>

        <form method="POST">
            <input name="sticker" placeholder="Sticker ID tauschen">
            <button class="btn orange" name="aktion" value="trade" type="submit">Tauschen</button>
        </form>
    </div>
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
            if trigger and compact(code) == compact(trigger):
                klasse += " trigger-slot"
            if trigger and compact(code) == compact(trigger):
                text = "🏆 " + text
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
            if trigger and compact(code) == compact(trigger):
                text = "🏆 " + text
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

    con = get_db()
    cur = con.cursor()

    daten = con.execute(
        "SELECT * FROM stickers WHERE user_id=? AND album_id=? AND sticker_code=?",
        (CURRENT_USER_ID, album_id, code)
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
            (CURRENT_USER_ID, album_id, code, neue_duplicates, neue_quantity)
        )

    con.commit()
    con.close()

    nachher_erreicht = erreichte_trophaeen(album_id)
    

    neue_trophies = [t for t in nachher_erreicht if t not in vorher_erreicht] 


    msg = f"Du hast Sticker {display_code(code)} doppelt." if neue_duplicates >= 1 else f"Du hast Sticker {display_code(code)} zur Sammlung hinzugefügt."

    url = f"/album/{album_id}?message={quote(msg)}"

    if neue_trophies:
        trophy_text = ", ".join(neue_trophies)
        url += f"&trophy={quote(trophy_text)}&count={len(neue_trophies)}&trigger={quote(code)}"

    print("FINAL URL:", url)

    return redirect(url)

    

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

    if show_duplicates:
        html += "<h2>Doppelte-Trophäen</h2>"

        for ziel, titel in album_doppelte_trophaeen():
            erreicht = doppelte >= ziel
            klasse = "trophy-unlocked" if erreicht else "trophy-locked"
            beschreibung = f"{ziel} doppelte Sticker in diesem Album"

            html += f"""
            <div class="trophy {klasse}">
                <h2>{'🏆' if erreicht else '🔒'} {titel}</h2>
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
    html += "</div></body></html>"
    return html

@app.route("/statistik")
def statistik():
    con = get_db()

    alben = con.execute("SELECT * FROM albums").fetchall()
    stickers = con.execute("SELECT * FROM stickers").fetchall()

    con.close()

    sticker_gesamt = sum(s["quantity"] for s in stickers)
    doppelte = sum(s["duplicates"] for s in stickers)
    fehlend = 0
    trophäen = 0

    album_cards = ""

    for album in alben:
        album_data, by_code, gesammelt, doppelt, prozent, total = lade_album(album["id"])

        fehlend_album = total - gesammelt
        fehlend += fehlend_album

        _, _, trophies = trophy_status(album["id"], gesammelt, total)

        erhalten = len([t for t in trophies if gesammelt >= t[0]])
        trophäen += erhalten

        album_cards += f"""
        <div class="stat-album">
            <h2>{album["name"]}</h2>

            <div class="stat-grid-mini">
                <div class="mini-box">
                    <div class="mini-big">{total}</div>
                    <p>Gesamt</p>
                </div>

                <div class="mini-box">
                    <div class="mini-big">{gesammelt}</div>
                    <p>Gesammelt</p>
                </div>

                <div class="mini-box">
                    <div class="mini-big">{doppelt}</div>
                    <p>Doppelte</p>
                </div>

                <div class="mini-box">
                    <div class="mini-big">{fehlend_album}</div>
                    <p>Fehlend</p>
                </div>
            </div>

            <div class="album-progress">
                <div class="album-progress-fill" style="width:{prozent}%"></div>
            </div>

            <p class="trophy-info">🏆 {erhalten} Trophäen erhalten</p>
        </div>
        """

    html = """
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

    <div class="stats">
        <div class="stat">
            <div class="big">{len(alben)}</div>
            <p>Alben</p>
        </div>

        <div class="stat">
            <div class="big">{sticker_gesamt}</div>
            <p>Sticker</p>
        </div>

        <div class="stat">
            <div class="big">{doppelte}</div>
            <p>Doppelte</p>
        </div>

        <div class="stat">
            <div class="big">{fehlend}</div>
            <p>Fehlend</p>
        </div>

        <div class="stat">
            <div class="big">{trophäen}</div>
            <p>Trophäen</p>
        </div>
    </div>

    <h1>Albumstatistiken</h1>

    {album_cards}

    </div>
    </body>
    </html>
    """

    return html
init_db()

app.run(debug=True)