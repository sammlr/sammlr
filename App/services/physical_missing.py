"""D06 supply quarantine; overlap credits only its concrete reservation."""

def available(db):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE name='physical_missing_holds'").fetchone())


def extras(db, *, enabled=None):
    if not (available(db) if enabled is None else enabled):
        return {}
    return {(r[0],r[1],r[2]):r[3] for r in db.execute('''SELECT m.user_id,m.album_id,m.sticker_code,
        SUM(m.quantity-CASE WHEN h.state='active' THEN MIN(m.overlap_quantity,h.quantity) ELSE 0 END)
        FROM physical_missing_holds m JOIN trade_reservations h ON h.id=m.reservation_id
        WHERE m.resolved_at IS NULL GROUP BY m.user_id,m.album_id,m.sticker_code''')}


def overlap(db, reservation):
    if not available(db):
        return 0
    return db.execute('''SELECT COALESCE(SUM(overlap_quantity),0) FROM physical_missing_holds
        WHERE reservation_id=? AND resolved_at IS NULL''',(reservation,)).fetchone()[0]
