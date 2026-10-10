"""Physical V1 inspection: one atomic debit/credit boundary, immutable evidence."""
import json
from datetime import timedelta

from services.trade_lifecycle_shipping import LifecycleShipping
from services.trade_lifecycle_requests import instant
from services.trade_lifecycle_foundation import _json
from services.inventory import InventoryReadService
from services.history_cutover import HistoricalInventoryWriteService, canonical_utc_timestamp
from services.typed_notifications import TypedNotificationService
from services.smartdeal_planning import all_codes


COUNTS = ('correct', 'missing', 'wrong', 'damaged_accepted', 'damaged_rejected')


def ready(db):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE name='lifecycle_receipts'").fetchone())


class LifecycleReceipts(LifecycleShipping):
    def _receipt_entry_ready(self, row):
        """Read the current bilateral release basis without creating preparation cycles."""
        release = self._released(row['trade_id'])
        if not release or release['revision_id'] != row['accepted_revision_id']:
            return False
        cycles = self.db.execute('''SELECT * FROM lifecycle_preparation_cycles
            WHERE trade_id=? AND is_current=1 ORDER BY owner_id''', (row['trade_id'],)).fetchall()
        participants = {row['requester_user_id'], row['partner_user_id']}
        if len(cycles) != 2 or {c['owner_id'] for c in cycles} != participants:
            return False
        if release['basis_json'] != _json([c['id'] for c in cycles]) or any(
            c['revision_id'] != row['accepted_revision_id'] or not c['completed_at']
            or not c['revealed_at'] or c['review_state'] != 'approved' for c in cycles
        ):
            return False
        directions = self.db.execute('SELECT * FROM lifecycle_directions WHERE trade_id=?',
                                     (row['trade_id'],)).fetchall()
        return (len(directions) == 2 and {d['from_user_id'] for d in directions} == participants
                and all(d['preparation_state'] == 'ready_to_ship' for d in directions)
                and not self._pending(row['trade_id']))

    def _require_receipt_entry(self, row):
        if not self._receipt_entry_ready(row):
            raise ValueError('Current bilateral preparation, photo approval and address release required')

    def _receipt_binding(self, trade, actor, sender, revision=None, *, receiving=True):
        if not ready(self.db):
            raise ValueError('Receipt schema unavailable')
        row = self._binding(trade, actor, revision)
        direction = self.db.execute('SELECT * FROM lifecycle_directions WHERE trade_id=? AND from_user_id=?',
                                    (trade, sender)).fetchone()
        if type(sender) is not int or direction is None or actor != direction['to_user_id' if receiving else 'from_user_id']:
            raise ValueError('Direction ownership required')
        return row, direction

    def _receipt(self, trade, sender):
        return self.db.execute('SELECT * FROM lifecycle_receipts WHERE trade_id=? AND from_user_id=?', (trade, sender)).fetchone()

    def _inspection(self, row, sender, inspection):
        positions = [dict(p) for p in self._positions(row['accepted_revision_id']) if p['from_user_id'] == sender]
        if inspection is None:
            inspection = [dict(position=p['id'], correct=p['quantity'], missing=0, wrong=0,
                               damaged_accepted=0, damaged_rejected=0, wrong_code='') for p in positions]
        if not isinstance(inspection, list) or len(inspection) != len(positions):
            raise ValueError('Every expected position must be classified')
        by_id = {}
        for item in inspection:
            if not isinstance(item, dict) or set(item) != {'position', 'wrong_code', *COUNTS}:
                raise ValueError('Invalid inspection fields')
            if type(item['position']) is not int or item['position'] in by_id:
                raise ValueError('Invalid or repeated position')
            by_id[item['position']] = item
        if set(by_id) != {p['id'] for p in positions}:
            raise ValueError('Foreign or stale position')
        result = []
        for p in positions:
            item = by_id[p['id']]
            if any(type(item[k]) is not int or not 0 <= item[k] <= p['quantity'] for k in COUNTS):
                raise ValueError('Nonnegative integral quantities required')
            if sum(item[k] for k in COUNTS) != p['quantity']:
                raise ValueError('Expected quantity must be partitioned exactly')
            code = item['wrong_code']
            if not isinstance(code, str) or len(code) > 100:
                raise ValueError('Invalid received code')
            code = code.strip()
            if code and (not item['wrong'] or code == p['sticker_code'] or code not in all_codes(p['album_id'])):
                raise ValueError('Received code must belong to the expected album catalog')
            result.append(dict(item, wrong_code=code))
        return positions, result

    def review_receipt(self, trade, actor, sender, revision, inspection=None):
        with self.store.transaction():
            row, _ = self._receipt_binding(trade, actor, sender, revision)
            self._require_receipt_entry(row)
            if self._receipt(trade, sender):
                raise ValueError('Receipt already confirmed')
            if self._pending(trade):
                raise ValueError('Reduction unresolved')
            return self._inspection(row, sender, inspection)

    def _notify_receipt(self, row, actor, target, event, now, **data):
        self._event_data(row, event, actor, now, **data)
        event_id = self.db.execute('SELECT last_insert_rowid()').fetchone()[0]
        title = {'ReceiptComplete': 'Empfang bestätigt', 'ReceiptPartial': 'Teilempfang bestätigt',
                 'ReceiptProblemReported': 'Problem mit Lieferung', 'NonArrivalReported': 'Brief nicht angekommen',
                 'LateArrivalReported': 'Brief später angekommen', 'SenderProblemResponse': 'Absender hat reagiert'}[event]
        TypedNotificationService(self.db).create(target, 'lifecycle_receipt_update', title,
            'Die Empfangskontrolle deines Tauschs wurde aktualisiert.', 'trade', row['trade_id'], event_id)

    def _problem(self, row, sender, kind, now):
        cursor = self.db.execute('''INSERT INTO lifecycle_delivery_problems
            (trade_id,from_user_id,revision_id,kind,reported_at) VALUES (?,?,?,?,?)''',
            (row['trade_id'], sender, row['accepted_revision_id'], kind, now.isoformat()))
        return cursor.lastrowid

    def confirm_receipt(self, trade, actor, sender, revision, key, inspection=None):
        payload = dict(sender=sender, revision=revision, inspection=inspection)
        with self.store.transaction():
            row, direction = self._receipt_binding(trade, actor, sender, revision)
            self._require_receipt_entry(row)
            old_command = self._command(trade, actor, key, 'receipt', payload)
            if old_command is not None:
                return old_command
            positions, classified = self._inspection(row, sender, inspection)
            serialized = _json(classified)
            old = self._receipt(trade, sender)
            if old:
                if old['inspection_json'] != serialized:
                    raise ValueError('Confirmed inspection cannot be changed')
                return self.store.record_command(trade, actor, key, 'receipt', payload, dict(old))
            if self._pending(trade):
                raise ValueError('Reduction unresolved')
            now = instant(self.clock())
            # L07 requires the exact binding Give package even for partial receipt.
            # Reuse L06's only debit path; any later failure also rolls it back.
            self.finalize_direction_sent(trade, sender, revision, actor=actor, source='RECEIPT_EVIDENCE')
            problem = any(any(item[k] for k in COUNTS if k != 'correct') for item in classified)
            for p, item in zip(positions, classified):
                accepted = item['correct'] + item['damaged_accepted']
                claim = self.db.execute('SELECT * FROM lifecycle_need_claims WHERE revision_position_id=?', (p['id'],)).fetchone()
                if claim is None or claim['state'] != 'committed' or claim['quantity'] != p['quantity'] or claim['received_quantity']:
                    raise ValueError('Exact unconsumed committed need binding required')
                if accepted:
                    movement = f"lifecycle-receipt:{trade}:{sender}:{p['id']}"
                    before = InventoryReadService(self.db).snapshot(actor, p['album_id'], (p['sticker_code'],)).sticker(p['sticker_code'])
                    if not before.balance_is_valid:
                        raise ValueError('Receiver inventory requires reconciliation')
                    result = HistoricalInventoryWriteService(self.db).set_quantity(actor, p['album_id'], p['sticker_code'], before.physical + accepted,
                        event_key=movement, source_type='trade_receipt', occurred_at=canonical_utc_timestamp(now))
                    if not result.allowed or result.quantity != result.previous_quantity + accepted:
                        raise ValueError('Receipt credit failed')
                    self.db.execute("INSERT INTO lifecycle_movements VALUES (?,?,?,?,'credit',?,?,?)",
                        (trade, sender, p['album_id'], p['sticker_code'], 'inspection', accepted, movement))
                # Outstanding problem quantities remain committed under contract §3a.
                self.db.execute('UPDATE lifecycle_need_claims SET received_quantity=? WHERE id=?', (accepted, claim['id']))
            self.db.execute('INSERT INTO lifecycle_receipts VALUES (?,?,?,?,?,?,?)',
                (trade, sender, revision, actor, now.isoformat(), serialized, int(problem)))
            state = 'received_with_problem' if problem else 'received_complete'
            self.db.execute('UPDATE lifecycle_directions SET receipt_state=? WHERE trade_id=? AND from_user_id=?', (state, trade, sender))
            late = self.db.execute("SELECT id FROM lifecycle_delivery_problems WHERE trade_id=? AND from_user_id=? AND kind='non_arrival'", (trade, sender)).fetchone()
            if late:
                self._notify_receipt(row, actor, sender, 'LateArrivalReported', now, sender=sender, previous_problem=late['id'])
            partial = any(item['correct'] + item['damaged_accepted'] < p['quantity'] for p, item in zip(positions, classified))
            self._notify_receipt(row, actor, sender, 'ReceiptPartial' if partial else 'ReceiptComplete', now, sender=sender)
            if problem:
                problem_id = self._problem(row, sender, 'inspection', now)
                self._notify_receipt(row, actor, sender, 'ReceiptProblemReported', now, sender=sender, problem=problem_id)
            result = dict(self._receipt(trade, sender))
            return self.store.record_command(trade, actor, key, 'receipt', payload, result)

    def report_non_arrival(self, trade, actor, sender, revision, key):
        payload = dict(sender=sender, revision=revision)
        with self.store.transaction():
            row, _ = self._receipt_binding(trade, actor, sender, revision)
            old = self._command(trade, actor, key, 'non_arrival', payload)
            if old is not None:
                return old
            if self._receipt(trade, sender):
                raise ValueError('Already received')
            sent = self._sent(trade, sender)
            now = instant(self.clock())
            if not sent or sent['source'] != 'SENDER_CONFIRMATION' or now < instant(sent['sent_at']) + timedelta(days=7):
                raise ValueError('Seven full days after confirmed shipping required')
            problem = self.db.execute("SELECT id FROM lifecycle_delivery_problems WHERE trade_id=? AND from_user_id=? AND kind='non_arrival'", (trade, sender)).fetchone()
            if problem:
                result = dict(problem=problem['id'])
            else:
                problem_id = self._problem(row, sender, 'non_arrival', now)
                self.db.execute("UPDATE lifecycle_directions SET receipt_state='non_arrival_reported' WHERE trade_id=? AND from_user_id=?", (trade, sender))
                self._notify_receipt(row, actor, sender, 'NonArrivalReported', now, sender=sender, problem=problem_id)
                result = dict(problem=problem_id)
            return self.store.record_command(trade, actor, key, 'non_arrival', payload, result)

    def respond(self, trade, actor, sender, revision, problem_id, response, key):
        payload = dict(sender=sender, revision=revision, problem=problem_id, response=response)
        with self.store.transaction():
            row, direction = self._receipt_binding(trade, actor, sender, revision, receiving=False)
            old = self._command(trade, actor, key, 'receipt_response', payload)
            if old is not None:
                return old
            problem = self.db.execute('SELECT * FROM lifecycle_delivery_problems WHERE id=? AND trade_id=? AND from_user_id=? AND revision_id=?',
                (problem_id, trade, sender, revision)).fetchone()
            if type(problem_id) is not int or problem is None or response not in ('acknowledge', 'sent_correctly'):
                raise ValueError('Invalid problem response')
            existing = self.db.execute('SELECT * FROM lifecycle_delivery_responses WHERE problem_id=?', (problem_id,)).fetchone()
            if existing:
                if existing['response'] != response:
                    raise ValueError('Response already fixed')
                result = dict(existing)
            else:
                if problem['kind'] == 'non_arrival' and self._receipt(trade, sender):
                    raise ValueError('Non-arrival superseded by physical receipt')
                now = instant(self.clock())
                self.db.execute('INSERT INTO lifecycle_delivery_responses VALUES (?,?,?,?)', (problem_id, actor, response, now.isoformat()))
                self._notify_receipt(row, actor, direction['to_user_id'], 'SenderProblemResponse', now, sender=sender, problem=problem_id, response=response)
                result = dict(self.db.execute('SELECT * FROM lifecycle_delivery_responses WHERE problem_id=?', (problem_id,)).fetchone())
            return self.store.record_command(trade, actor, key, 'receipt_response', payload, result)

    def receipt_view(self, trade, actor):
        with self.store.transaction():
            row = self._binding(trade, actor)
            if not ready(self.db):
                raise ValueError('Receipt schema unavailable')
            now = instant(self.clock())
            directions = []
            for d in self.db.execute('SELECT * FROM lifecycle_directions WHERE trade_id=? ORDER BY from_user_id', (trade,)):
                item = dict(d)
                sent = self._sent(trade, d['from_user_id'])
                receipt = self._receipt(trade, d['from_user_id'])
                item.update(sent=dict(sent) if sent else None, receipt=dict(receipt) if receipt else None,
                    positions=[dict(p) for p in self._positions(row['accepted_revision_id']) if p['from_user_id'] == d['from_user_id']],
                    inspection=json.loads(receipt['inspection_json']) if receipt else [],
                    can_non_arrival=bool(not receipt and sent and sent['source'] == 'SENDER_CONFIRMATION' and now >= instant(sent['sent_at']) + timedelta(days=7)))
                item['problems'] = []
                for p in self.db.execute('SELECT p.*,r.response,r.responded_at FROM lifecycle_delivery_problems p LEFT JOIN lifecycle_delivery_responses r ON r.problem_id=p.id WHERE p.trade_id=? AND p.from_user_id=? ORDER BY p.id', (trade, d['from_user_id'])):
                    item['problems'].append(dict(p, superseded=bool(p['kind'] == 'non_arrival' and receipt)))
                directions.append(item)
            return dict(trade=trade, revision=row['accepted_revision_id'], actor=actor, directions=directions,
                        receipt_enabled=self._receipt_entry_ready(row))
