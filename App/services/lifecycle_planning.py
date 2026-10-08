"""Contract-aware additive projection; the legacy reader remains unchanged."""
from dataclasses import replace
from datetime import datetime, timezone
from services.smartdeal_planning import PlanningPiece
from services.trade_lifecycle_foundation import lifecycle_availability


def project(db, inputs, exclude_revision=None):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='lifecycle_requests'").fetchone():
        return inputs
    # Only touched quantities need overlay; ordinary catalogs retain canonical reads.
    keys = {}
    for row in db.execute('''SELECT user_id,album_id,sticker_code FROM lifecycle_need_targets
        UNION SELECT p.to_user_id,p.album_id,p.sticker_code FROM lifecycle_need_claims c
          JOIN lifecycle_revision_positions p ON p.id=c.revision_position_id
        UNION SELECT p.from_user_id,p.album_id,p.sticker_code FROM lifecycle_requests q
          JOIN lifecycle_revision_positions p ON p.revision_id=q.revision_id
          WHERE p.from_user_id=q.sender_user_id'''):
        keys.setdefault(row[0],set()).add((row[1],row[2]))
    now = datetime.now(timezone.utc)
    from services.trade_lifecycle_requests import instant
    expired_holds = {}
    for user,album,code,quantity,deadline in db.execute("""SELECT h.user_id,h.album_id,h.sticker_code,h.quantity,q.expires_at
        FROM lifecycle_requests q JOIN lifecycle_revision_positions p ON p.revision_id=q.revision_id
        JOIN lifecycle_supply_bindings b ON b.revision_position_id=p.id AND b.is_current=1
        JOIN trade_reservations h ON h.id=b.reservation_id
        WHERE q.status='open' AND h.state='active'"""):
        if now >= instant(deadline):
            key = (user,album,code)
            expired_holds[key] = expired_holds.get(key,0)+quantity
    credits = {}
    if exclude_revision is not None:
        for user,album,code,quantity,reservation in db.execute("""SELECT h.user_id,h.album_id,h.sticker_code,h.quantity,h.id
            FROM lifecycle_supply_bindings b JOIN trade_reservations h ON h.id=b.reservation_id
            JOIN lifecycle_revision_positions p ON p.id=b.revision_position_id
            WHERE p.revision_id=? AND b.is_current=1 AND h.state='active'""",(exclude_revision,)):
            from services.physical_missing import overlap
            credits[(user,album,code)] = quantity-overlap(db,reservation)
    contexts = {a.album_id:a for a in inputs.subject.album_context}
    memberships = {(r[0],r[1]):r[2] for r in db.execute('SELECT user_id,album_id,id FROM user_albums')}
    def overlay(state):
        needs = {(p.album_id,p.sticker_code):p for p in state.needs}
        supply = {(p.album_id,p.sticker_code):p for p in state.outgoing_supply}
        for album,code in keys.get(state.user_id,()):
            context = contexts.get(album)
            membership = memberships.get((state.user_id,album))
            if not context or code not in context.catalog_codes or membership is None:
                continue
            a = lifecycle_availability(db,state.user_id,album,code,now=now,exclude_revision=exclude_revision)
            # Preserve the legacy reader's effective-hold policy. Add back only
            # this contract's expired holds; never reinterpret old reservations.
            original = supply.get((album,code))
            free_supply = (original.quantity if original else 0)+expired_holds.get((state.user_id,album,code),0)+credits.get((state.user_id,album,code),0)
            for mapping,quantity in ((needs,a.free_need),(supply,free_supply)):
                mapping.pop((album,code),None)
                if quantity:
                    mapping[(album,code)] = PlanningPiece(album,code,membership,quantity)
        result = replace(state,needs=tuple(sorted(needs.values())),outgoing_supply=tuple(sorted(supply.values())))
        return result
    return replace(inputs,subject=overlay(inputs.subject),partners=tuple(overlay(p) for p in inputs.partners))
