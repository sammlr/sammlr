import sqlite3
from em24_data import build_em24

DB = "collectr.db"

db = sqlite3.connect(DB)
cursor = db.cursor()

# EM als vollständiges Album markieren
cursor.execute("""
UPDATE albums
SET complete = 1
WHERE id = 'em24'
""")

# alte EM-Sticker entfernen
cursor.execute("""
DELETE FROM stickers
WHERE album_id = 'em24'
""")

# alle 707 physischen EM-Sticker einmal vorhanden eintragen
for sticker in build_em24():
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
        "em24",
        sticker["id"],
        "owned",
        0,
        1
    ))

db.commit()
db.close()

print("EURO 2024 wurde vollständig eingetragen 🏆")