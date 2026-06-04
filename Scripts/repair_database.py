import sqlite3
import ast
import os

db = sqlite3.connect("collectr.db")
cursor = db.cursor()

def lade_txt(dateiname):
    if not os.path.exists(dateiname):
        return []
    with open(dateiname, "r") as datei:
        inhalt = datei.read().strip()
    if inhalt == "":
        return []
    return ast.literal_eval(inhalt)

# VfL alte Daten laden
fehlende = lade_txt("fehlende.txt")
doppelte = lade_txt("doppelte.txt")

# alte VfL Sticker aus DB löschen
cursor.execute("DELETE FROM stickers WHERE album_id = 'vfl'")

# vorhandene VfL Sticker berechnen
for nummer in range(1, 251):
    if nummer not in fehlende:
        cursor.execute("""
        INSERT INTO stickers (album_id, sticker_code, status, duplicates)
        VALUES (?, ?, ?, ?)
        """, ("vfl", str(nummer), "owned", 0))

# doppelte zählen
gezaehlt = {}

for sticker in doppelte:
    sticker = str(sticker)
    gezaehlt[sticker] = gezaehlt.get(sticker, 0) + 1

for sticker, anzahl in gezaehlt.items():
    cursor.execute("""
    SELECT * FROM stickers
    WHERE album_id = ? AND sticker_code = ?
    """, ("vfl", sticker))

    vorhanden = cursor.fetchone()

    if vorhanden:
        cursor.execute("""
        UPDATE stickers
        SET duplicates = ?
        WHERE album_id = ? AND sticker_code = ?
        """, (anzahl, "vfl", sticker))
    else:
        cursor.execute("""
        INSERT INTO stickers (album_id, sticker_code, status, duplicates)
        VALUES (?, ?, ?, ?)
        """, ("vfl", sticker, "owned", anzahl))

db.commit()
db.close()

print("VfL Datenbank wurde aktualisiert 🏆")