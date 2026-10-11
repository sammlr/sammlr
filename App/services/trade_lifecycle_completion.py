"""V1 final resolution and completion, composed inside the existing receipt transaction."""
from datetime import timedelta
import json

from services.trade_lifecycle_receipts import LifecycleReceipts
from services.trade_lifecycle_requests import instant
from services.typed_notifications import TypedNotificationService
from services.trade_ratings import TradeRatingService


def ready(db):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE name='lifecycle_completions'").fetchone())


def resolved(db, trade, sender):
    return ready(db) and db.execute('SELECT 1 FROM lifecycle_direction_resolutions WHERE trade_id=? AND from_user_id=?',
                                  (trade, sender)).fetchone() is not None


def event(service, row, name, actor, now, targets=(), **data):
    service._event_data(row, name, actor, now, **data)
    event_id = service.db.execute('SELECT last_insert_rowid()').fetchone()[0]
    for target in targets:
        TypedNotificationService(service.db).create(target, 'lifecycle_receipt_update',
            'Tausch aktualisiert', 'Abschluss oder Bewertungsstatus deines Tauschs wurde aktualisiert.',
            'trade', row['trade_id'], event_id)


def eligibility(service, trade, user, stamp):
    if not service.db.execute('SELECT 1 FROM lifecycle_rating_eligibility WHERE trade_id=? AND user_id=?', (trade, user)).fetchone():
        service.db.execute('INSERT INTO lifecycle_rating_eligibility VALUES (?,?,?)', (trade, user, stamp))


def complete_if_ready(service, row, now):
    trade = row['trade_id']
    if service.db.execute('SELECT 1 FROM lifecycle_completions WHERE trade_id=?', (trade,)).fetchone():
        return
    directions = service.db.execute('SELECT kind FROM lifecycle_direction_resolutions WHERE trade_id=?', (trade,)).fetchall()
    if len(directions) != 2:
        return
    had_problem = service.db.execute('SELECT 1 FROM lifecycle_delivery_problems WHERE trade_id=?', (trade,)).fetchone()
    outcome = 'completed' if all(d['kind'] == 'complete' for d in directions) and not had_problem else 'closed_with_problem'
    service.db.execute('INSERT INTO lifecycle_completions VALUES (?,?,?,?)',
                       (trade, row['accepted_revision_id'], outcome, now.isoformat()))
    service.db.execute("UPDATE lifecycle_contracts SET state='ended' WHERE trade_id=?", (trade,))
    service.db.execute('UPDATE trades SET lifecycle_state=?,completed_at=?,updated_at=? WHERE id=?',
                       (outcome, now.isoformat(), now.isoformat(), trade))
    event(service, row, 'TradeCompletedSuccessfully' if outcome == 'completed' else 'TradeCompletedWithProblem',
          None, now, (row['requester_user_id'], row['partner_user_id']))


def settle_receipts(service, row, now):
    """Same transaction as the last receipt; also catches up existing L07 evidence."""
    if not ready(service.db):
        return
    for receipt in service.db.execute('SELECT * FROM lifecycle_receipts WHERE trade_id=?', (row['trade_id'],)).fetchall():
        eligibility(service, row['trade_id'], receipt['receiver_id'], receipt['received_at'])
        if not receipt['has_problem'] and not resolved(service.db, row['trade_id'], receipt['from_user_id']):
            service.db.execute('INSERT INTO lifecycle_direction_resolutions VALUES (?,?,?,?,?,?,?)',
                (row['trade_id'], receipt['from_user_id'], receipt['revision_id'], receipt['receiver_id'],
                 'complete', None, receipt['received_at']))
            event(service, row, 'DirectionResolvedComplete', receipt['receiver_id'], instant(receipt['received_at']),
                  sender=receipt['from_user_id'])
    complete_if_ready(service, row, now)


class LifecycleCompletion(LifecycleReceipts):
    def refresh_for_actor(self, actor):
        """Catch up only outstanding L08 evidence for an authorized portfolio.

        Ordinary reads do not load each trade's detail model. No receipt, claim
        or inventory command is called; settlement/reveal use the existing L08
        primitives under their original transaction boundary.
        """
        self._actor(actor)
        if not ready(self.db):
            return
        with self.store.transaction():
            now = instant(self.clock())
            rows = self.db.execute('''SELECT c.*,t.requester_user_id,t.partner_user_id
                FROM lifecycle_contracts c JOIN trades t ON t.id=c.trade_id
                WHERE ? IN(t.requester_user_id,t.partner_user_id) AND c.accepted_revision_id IS NOT NULL
                AND (EXISTS(SELECT 1 FROM lifecycle_receipts r WHERE r.trade_id=c.trade_id
                    AND (NOT EXISTS(SELECT 1 FROM lifecycle_rating_eligibility e WHERE e.trade_id=r.trade_id AND e.user_id=r.receiver_id)
                    OR (r.has_problem=0 AND NOT EXISTS(SELECT 1 FROM lifecycle_direction_resolutions d WHERE d.trade_id=r.trade_id AND d.from_user_id=r.from_user_id))))
                OR EXISTS(SELECT 1 FROM trade_ratings r WHERE r.trade_id=c.trade_id
                    AND NOT EXISTS(SELECT 1 FROM lifecycle_rating_publications p WHERE p.rating_id=r.id)
                    AND (EXISTS(SELECT 1 FROM trade_ratings other WHERE other.trade_id=r.trade_id AND other.rater_user_id=r.rated_user_id)
                    OR EXISTS(SELECT 1 FROM lifecycle_rating_eligibility e WHERE e.trade_id=r.trade_id AND e.user_id=r.rated_user_id
                        AND julianday(e.eligible_at)+14<=julianday(?)))))''', (actor, now.isoformat())).fetchall()
            for row in rows:
                settle_receipts(self, row, now)
                self._publish_ratings(row, now)

    def _completion_binding(self, trade, actor, revision=None):
        self._actor(actor)
        if not ready(self.db):
            raise ValueError('Completion schema unavailable')
        row = self.db.execute('''SELECT c.*,t.requester_user_id,t.partner_user_id FROM lifecycle_contracts c
            JOIN trades t ON t.id=c.trade_id WHERE c.trade_id=? AND c.accepted_revision_id IS NOT NULL
            AND (c.state='accepted' OR EXISTS(SELECT 1 FROM lifecycle_completions x WHERE x.trade_id=c.trade_id))''', (trade,)).fetchone()
        if row is None or actor not in (row['requester_user_id'], row['partner_user_id']):
            raise ValueError('Trade participant required')
        if revision is not None and (type(revision) is not int or revision != row['accepted_revision_id']):
            raise ValueError('Stale revision')
        return row

    def resolve_problem(self, trade, actor, sender, revision, problem_id, mode, key):
        payload = dict(sender=sender, revision=revision, problem=problem_id, mode=mode)
        with self.store.transaction():
            row = self._completion_binding(trade, actor, revision)
            direction = self.db.execute('SELECT * FROM lifecycle_directions WHERE trade_id=? AND from_user_id=?', (trade, sender)).fetchone()
            if type(sender) is not int or direction is None or direction['to_user_id'] != actor:
                raise ValueError('Actual receiver required')
            old = self._command(trade, actor, key, 'resolve_problem', payload)
            if old is not None:
                return old
            if mode not in ('problem_accepted', 'after_wait') or type(problem_id) is not int:
                raise ValueError('Invalid resolution')
            existing = self.db.execute('SELECT * FROM lifecycle_direction_resolutions WHERE trade_id=? AND from_user_id=?', (trade, sender)).fetchone()
            if existing:
                if existing['kind'] != mode or existing['problem_id'] != problem_id:
                    raise ValueError('Resolution is final')
                return self.store.record_command(trade, actor, key, 'resolve_problem', payload, dict(existing))
            problem = self.db.execute('SELECT * FROM lifecycle_delivery_problems WHERE id=? AND trade_id=? AND from_user_id=? AND revision_id=?',
                                      (problem_id, trade, sender, revision)).fetchone()
            if row['state'] != 'accepted' or problem is None:
                raise ValueError('Active problem required')
            receipt = self._receipt(trade, sender)
            if problem['kind'] == 'non_arrival' and (receipt or mode != 'after_wait'):
                raise ValueError('Non-arrival requires final wait and no later receipt')
            if problem['kind'] == 'inspection' and (not receipt or not receipt['has_problem']):
                raise ValueError('Problem inspection required')
            now = instant(self.clock())
            if mode == 'after_wait' and now < instant(problem['reported_at']) + timedelta(days=14):
                raise ValueError('Fourteen full days after problem report required')
            self.db.execute('INSERT INTO lifecycle_direction_resolutions VALUES (?,?,?,?,?,?,?)',
                            (trade, sender, revision, actor, mode, problem_id, now.isoformat()))
            self.store.release_received_remainder(trade, sender, revision, now.isoformat())
            eligibility(self, trade, actor, receipt['received_at'] if receipt else now.isoformat())
            event(self, row, 'DirectionResolvedProblemAccepted' if mode == 'problem_accepted' else 'DirectionResolvedAfterWait',
                  actor, now, (sender,), sender=sender, problem=problem_id)
            settle_receipts(self, row, now)
            result = dict(self.db.execute('SELECT * FROM lifecycle_direction_resolutions WHERE trade_id=? AND from_user_id=?', (trade, sender)).fetchone())
            return self.store.record_command(trade, actor, key, 'resolve_problem', payload, result)

    def submit_rating(self, trade, actor, revision, stars, tags, key):
        payload = dict(revision=revision, stars=stars, tags=tags)
        with self.store.transaction():
            row = self._completion_binding(trade, actor, revision)
            old = self._command(trade, actor, key, 'rating', payload)
            if old is not None:
                return old
            now = instant(self.clock())
            settle_receipts(self, row, now)
            ratings = TradeRatingService(self.db)
            result, created = ratings.create_lifecycle(row, actor, stars, tags, now)
            if created:
                # Never put stars or tags into general history, notifications or command results.
                event(self, row, 'RatingSubmitted', actor, now)
            self._publish_ratings(row, now)
            return self.store.record_command(trade, actor, key, 'rating', payload, result)

    def _publish_ratings(self, row, now):
        ratings = TradeRatingService(self.db)
        for rating in self.db.execute('SELECT * FROM trade_ratings WHERE trade_id=?', (row['trade_id'],)).fetchall():
            stamp = ratings.lifecycle_reveal_at(rating, now)
            if stamp is not None and not self.db.execute('SELECT 1 FROM lifecycle_rating_publications WHERE rating_id=?', (rating['id'],)).fetchone():
                self.db.execute('INSERT INTO lifecycle_rating_publications VALUES (?,?)', (rating['id'], stamp.isoformat()))
                event(self, row, 'RatingRevealed', None, stamp,
                      (row['requester_user_id'], row['partner_user_id']), rating=rating['id'])

    def completion_view(self, trade, actor):
        with self.store.transaction():
            row = self._completion_binding(trade, actor)
            now = instant(self.clock())
            settle_receipts(self, row, now)
            self._publish_ratings(row, now)
            completion = self.db.execute('SELECT * FROM lifecycle_completions WHERE trade_id=?', (trade,)).fetchone()
            directions = []
            for d in self.db.execute('SELECT * FROM lifecycle_directions WHERE trade_id=? ORDER BY from_user_id', (trade,)).fetchall():
                item = dict(d)
                receipt = self._receipt(trade, d['from_user_id'])
                resolution = self.db.execute('SELECT * FROM lifecycle_direction_resolutions WHERE trade_id=? AND from_user_id=?', (trade, d['from_user_id'])).fetchone()
                item.update(receipt=dict(receipt) if receipt else None, resolution=dict(resolution) if resolution else None,
                    positions=[dict(p) for p in self._positions(row['accepted_revision_id']) if p['from_user_id']==d['from_user_id']],
                    inspection=json.loads(receipt['inspection_json']) if receipt else [], problems=[])
                for p in self.db.execute('''SELECT p.*,r.response,r.responded_at FROM lifecycle_delivery_problems p
                    LEFT JOIN lifecycle_delivery_responses r ON r.problem_id=p.id
                    WHERE p.trade_id=? AND p.from_user_id=? ORDER BY p.id''', (trade, d['from_user_id'])):
                    superseded = bool(p['kind']=='non_arrival' and receipt)
                    deadline = instant(p['reported_at']) + timedelta(days=14)
                    item['problems'].append(dict(p, superseded=superseded, deadline=deadline.isoformat(),
                        can_accept=bool(not resolution and not superseded and p['kind']=='inspection' and d['to_user_id']==actor),
                        can_close=bool(not resolution and not superseded and now>=deadline and d['to_user_id']==actor)))
                directions.append(item)
            return dict(trade=trade, revision=row['accepted_revision_id'], actor=actor,
                completion=dict(completion) if completion else None, directions=directions,
                ratings=TradeRatingService(self.db).lifecycle_view(row, actor, now))
