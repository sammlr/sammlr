import sqlite3

db = sqlite3.connect("collectr.db")
cursor = db.cursor()

cursor.execute("""
SELECT id, duplicates
FROM stickers
""")

daten = cursor.fetchall()

for eintrag in daten:

    sticker_id = eintrag[0]

    duplicates = eintrag[1]

    quantity = duplicates + 1

    cursor.execute("""

    UPDATE stickers
    SET quantity = ?
    WHERE id = ?

    """, (
        quantity,
        sticker_id
    ))

db.commit()

print("Quantity System aktiv 😄🏆")