"""One serialized acceptance boundary for original offers and the single counter."""
from dataclasses import replace
from datetime import timedelta
import hashlib
import json

from services.trade_lifecycle_requests import LifecycleRequests, instant
from services.trade_lifecycle_foundation import RuleSnapshot, _json
from services.trade_v2_domain import TradeV2Domain
from services.trade_v2_preferences import TradeV2Preferences
from services.smartdeal_optimizer import SmartDealPiece, SmartDealOptimizer


def ready(db):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE name='lifecycle_acceptances'").fetchone())


class LifecycleAcceptance(LifecycleRequests):
    def _command(self, trade, actor, key, operation, payload):
        if not ready(self.db):
            raise ValueError('Acceptance schema unavailable')
        self._actor(actor)
        if not isinstance(key,str) or not 1 <= len(key) <= 200:
            raise ValueError('Command identity required')
        row=self.db.execute('''SELECT operation,payload_digest,result_json FROM lifecycle_commands
            WHERE trade_id=? AND actor_user_id=? AND command_key=?''',(trade,actor,key)).fetchone()
        if row:
            if (row[0],row[1]) != (operation,hashlib.sha256(_json(payload).encode()).hexdigest()):
                raise ValueError('Command key conflicts with previous payload')
            return json.loads(row[2])
        return None

    def _positions(self, revision):
        return self.db.execute('''SELECT id,from_user_id,to_user_id,album_id,sticker_code,quantity
            FROM lifecycle_revision_positions WHERE revision_id=? ORDER BY from_user_id,album_id,sticker_code''',(revision,)).fetchall()

    def _offer(self, trade, actor, expected):
        row=self._row(trade)
        if type(expected) is not int or expected != row['revision_id']:
            raise ValueError('Stale offer revision')
        if actor != row['partner_user_id']:
            raise ValueError('Only the current recipient may accept or counter')
        return row

    def _verify_sender_bindings(self,row):
        for p in self._positions(row['revision_id']):
            if p['from_user_id']==row['sender_user_id']:
                hold=self.db.execute('''SELECT h.quantity,h.state FROM lifecycle_supply_bindings b
                    JOIN trade_reservations h ON h.id=b.reservation_id
                    WHERE b.revision_position_id=? AND b.is_current=1''',(p['id'],)).fetchone()
                if hold is None or tuple(hold)!=(p['quantity'],'active'):
                    raise ValueError('Sender hold is missing or inconsistent')
            else:
                claim=self.db.execute('SELECT quantity,state FROM lifecycle_need_claims WHERE revision_position_id=?',(p['id'],)).fetchone()
                if claim is None or tuple(claim)!=(p['quantity'],'pending'):
                    raise ValueError('Sender need claim is missing or inconsistent')

    def _validate(self,row):
        self._actor(row['sender_user_id']);self._actor(row['partner_user_id'])
        self._verify_sender_bindings(row)
        positions=self._positions(row['revision_id'])
        give=tuple(SmartDealPiece(p['album_id'],p['sticker_code'],p['quantity']) for p in positions if p['from_user_id']==row['sender_user_id'])
        receive=tuple(SmartDealPiece(p['album_id'],p['sticker_code'],p['quantity']) for p in positions if p['to_user_id']==row['sender_user_id'])
        market=TradeV2Domain(self.db).market(row['sender_user_id'],exclude_revision=row['revision_id'])
        TradeV2Domain.validate_deal(market,row['partner_user_id'],give,receive,balanced=row['origin']=='SMARTDEAL')
        albums=sorted({p['album_id'] for p in positions})
        modes=TradeV2Preferences(self.db).read((row['sender_user_id'],row['partner_user_id']))
        # The fresh market already proved both memberships/pools/eligibility.
        snapshot=RuleSnapshot(row['sender_user_id'],row['partner_user_id'],row['origin'],row['origin']=='SMARTDEAL',
            tuple((a,True,True,modes[(row['sender_user_id'],a)],modes[(row['partner_user_id'],a)]) for a in albums))
        return positions,snapshot

    def accept(self, trade, actor, expected, key):
        payload={'revision':expected}
        with self.store.transaction():
            old=self._command(trade,actor,key,'accept',payload)
            if old is not None:return old
            row=self._offer(trade,actor,expected)
            now=instant(self.clock())
            def finish(status):
                return self.store.record_command(trade,actor,key,'accept',payload,{'status':status,'revision':expected})
            if row['status']=='accepted':return finish('already_accepted')
            if row['status']!='open':return finish(row['status'])
            if now>=instant(row['expires_at']):
                return finish(self._end(row,'expired',None,now))
            self._expire(now)
            try:
                positions,snapshot=self._validate(row)
            except ValueError:
                kind=self.db.execute('SELECT kind FROM lifecycle_revisions WHERE id=?',(expected,)).fetchone()[0]
                if kind=='counter':
                    return finish(self._end(row,'invalidated',actor,now))
                return finish('not_possible')
            # No mutation was made before the whole exact offer validated.
            for p in positions:
                if p['from_user_id']==actor:
                    self.store.bind_supply_position(p['id'])
                if p['to_user_id']==actor:
                    self.db.execute('''INSERT INTO lifecycle_need_claims(revision_position_id,state,quantity,created_at)
                        VALUES (?,'committed',?,?)''',(p['id'],p['quantity'],now.isoformat()))
                else:
                    self.db.execute("UPDATE lifecycle_need_claims SET state='committed' WHERE revision_position_id=? AND state='pending'",(p['id'],))
            self.store.store_rule_snapshot(expected,snapshot,now.isoformat())
            for user in (row['sender_user_id'],actor):
                # Sender's explicit offer and recipient's acceptance reference this same revision.
                consent_time=row['created_at'] if user==row['sender_user_id'] else now.isoformat()
                self.db.execute('INSERT INTO lifecycle_consents VALUES (?,?,?)',(expected,user,consent_time))
            self.db.execute("UPDATE lifecycle_contracts SET state='accepted',accepted_revision_id=? WHERE trade_id=?",(expected,trade))
            self.db.execute('INSERT INTO lifecycle_acceptances VALUES (?,?,?,?)',(trade,expected,actor,now.isoformat()))
            self.db.execute("UPDATE lifecycle_requests SET status='accepted',ended_at=? WHERE revision_id=?",(now.isoformat(),expected))
            self.db.execute("UPDATE trades SET lifecycle_state='accepted',updated_at=? WHERE id=?",(now.isoformat(),trade))
            self.db.execute("UPDATE lifecycle_directions SET preparation_state='ready' WHERE trade_id=?",(trade,))
            kind=self.db.execute('SELECT kind FROM lifecycle_revisions WHERE id=?',(expected,)).fetchone()[0]
            self._event(trade,expected,'CounterAccepted' if kind=='counter' else 'OfferAccepted',actor,now)
            return finish('accepted')

    def _counter_deal(self,row,actor):
        self._verify_sender_bindings(row)
        if self.db.execute("SELECT 1 FROM lifecycle_revisions WHERE trade_id=? AND kind='counter'",(row['trade_id'],)).fetchone():
            raise ValueError('Only one counteroffer is allowed')
        market=TradeV2Domain(self.db).market(actor,exclude_revision=row['revision_id'])
        pair=next((p for p in market.pairs if p.partner_id==row['sender_user_id'] and p.max_equal_piece_count>0),None)
        if pair is None:raise ValueError('No current counteroffer is possible')
        subject=replace(market.inputs.subject,eligible_partners=tuple(p for p in market.inputs.subject.eligible_partners if p.user_id==pair.partner_id))
        # Initial automatic offers retain minimum five. A counter retains origin,
        # but can be smaller; use the same exact solver with a one-piece floor.
        plan=SmartDealOptimizer.optimize(subject,(pair,),quantities=True,minimum=1)
        if not plan.deals:raise ValueError('No current counteroffer is possible')
        deal=plan.deals[0]
        return {'give':[(p.album_id,p.sticker_code,p.quantity) for p in deal.outgoing_pieces],
                'receive':[(p.album_id,p.sticker_code,p.quantity) for p in deal.incoming_pieces]}

    def preview_counter(self,trade,actor,expected):
        with self.store.transaction():
            self._actor(actor);row=self._offer(trade,actor,expected)
            now=instant(self.clock())
            if row['status']!='open':raise ValueError('Open original offer required')
            if now>=instant(row['expires_at']):
                self._end(row,'expired',None,now)
                return {'status':'expired'}
            self._expire(now)
            return {'status':'preview','revision':expected,**self._counter_deal(row,actor)}

    def counter(self,trade,actor,expected,key,proposal):
        payload={'revision':expected,'proposal':proposal}
        with self.store.transaction():
            old=self._command(trade,actor,key,'counter',payload)
            if old is not None:return old
            row=self._offer(trade,actor,expected);now=instant(self.clock())
            if row['status']!='open':raise ValueError('Open original offer required')
            if now>=instant(row['expires_at']):
                status=self._end(row,'expired',None,now)
                return self.store.record_command(trade,actor,key,'counter',payload,{'status':status,'revision':expected})
            self._expire(now)
            count=self.db.execute("SELECT COUNT(*) FROM lifecycle_requests WHERE sender_user_id=? AND status='open'",(actor,)).fetchone()[0]
            if count>=3:raise ValueError('Maximal drei eigene offene Anfragen sind möglich.')
            current=self._counter_deal(row,actor)
            if _json(proposal)!=_json(current):raise ValueError('Counter preview changed; review again')
            self.store.release_pending_quantities(expected)
            self.db.execute("UPDATE lifecycle_requests SET status='superseded',ended_at=? WHERE revision_id=?",(now.isoformat(),expected))
            positions=[(actor,row['sender_user_id'],a,c,n) for a,c,n in current['give']]
            positions += [(row['sender_user_id'],actor,a,c,n) for a,c,n in current['receive']]
            revision=self.store.append_revision(trade,actor,positions,'counter')
            self.db.execute('UPDATE lifecycle_contracts SET current_revision_id=? WHERE trade_id=?',(revision,trade))
            # Validate the new proposer perspective after releasing old bindings,
            # still within the same lock/transaction; any failure restores all old state.
            market=TradeV2Domain(self.db).market(actor)
            TradeV2Domain.validate_deal(market,row['sender_user_id'],tuple(SmartDealPiece(*p) for p in current['give']),
                tuple(SmartDealPiece(*p) for p in current['receive']),balanced=row['origin']=='SMARTDEAL')
            self.store.bind_pending_quantities(revision)
            self.db.execute('''INSERT INTO lifecycle_requests
                (trade_id,revision_id,sender_user_id,command_key,payload_digest,created_at,expires_at)
                VALUES (?,?,?,?,?,?,?)''',(trade,revision,actor,'counter:'+str(trade)+':'+hashlib.sha256(key.encode()).hexdigest(),hashlib.sha256(_json(payload).encode()).hexdigest(),
                    now.isoformat(),(now+timedelta(hours=72)).isoformat()))
            self._event(trade,revision,'OfferCountered',actor,now)
            return self.store.record_command(trade,actor,key,'counter',payload,{'status':'open','revision':revision})
