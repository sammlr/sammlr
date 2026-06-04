import sqlite3
import ast
import os

DB = "collectr.db"

def lade_txt(dateiname):
    if not os.path.exists(dateiname):
        return []
    with open(dateiname, "r") as datei:
        inhalt = datei.read().strip()
    if inhalt == "":
        return []
    return ast.literal_eval(inhalt)

db = sqlite3.connect(DB)
cursor = db.cursor()

fehlende = lade_txt("fehlende.txt")
doppelte = lade_txt("doppelte.txt")

cursor.execute("DELETE FROM stickers WHERE album_id = 'vfl'")

gezaehlt = {}

for sticker in doppelte:
    sticker = str(sticker)
    gezaehlt[sticker] = gezaehlt.get(sticker, 0) + 1

for nummer in range(1, 251):
    code = str(nummer)

    if nummer in fehlende:
        continue

    doppelt = gezaehlt.get(code, 0)
    quantity = 1 + doppelt

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
        "vfl",
        code,
        "owned",
        doppelt,
        quantity
    ))

db.commit()
db.close()

print("VfL Daten wurden repariert 🏆")