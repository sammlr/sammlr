"""Synthetic preparation, D06, immutable reduction and concurrency contracts."""
import base64
import json
import sqlite3
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from tests import test_lifecycle03_acceptance as fixtures
from services.trade_lifecycle_preparation import LifecyclePreparation
from services.inventory import InventoryReadService
from services.physical_missing import extras
from App.Database.migration_runner import migrate,rollback

import struct,zlib

def chunk(kind,data):
    return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
PNG=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0\xff\xff\xff'))+chunk(b'IEND',b'')


class PreparationTests(unittest.TestCase):
    connect=fixtures.AcceptanceTests.connect
    send=fixtures.AcceptanceTests.send
    stock=fixtures.AcceptanceTests.stock
    target=fixtures.AcceptanceTests.target
    race=fixtures.AcceptanceTests.race
    def setUp(self):
        fixtures.AcceptanceTests.setUp(self)
        migrate(self.db,26)
        self.s=LifecyclePreparation(self.db,lambda:self.now)
        self.t=self.send();self.rev=self.service._row(self.t)['revision_id']
        self.acceptance.accept(self.t,2,self.rev,'accept')
        self.storage=Path(self.tmp.name)/'photos';self.seq=0

    def view(self,actor=1):return self.s.view(self.t,actor)
    def call(self,action,actor=1,data=None,key=None,model=None):
        v=model or self.view(actor);self.seq+=1
        return self.s.command(self.t,actor,v['revision'],v['basis'],key or str(self.seq),action,data)
    def photo(self,actor=1,key=None):
        v=self.view(actor);self.seq+=1
        return self.s.upload(self.t,actor,v['revision'],v['basis'],key or str(self.seq),PNG,self.storage)['photo']
    def both(self):
        for a in (1,2):self.photo(a);self.call('complete',a)
    def ready(self):
        self.both();self.call('approve');self.call('approve',2)
    def larger(self,n=23):
        # Separate accepted trade with synthetic quantity targets.
        self.stock(1,'11',n+1);self.stock(3,'16',n+1)
        self.target(1,'16',n);self.target(3,'11',n)
        self.t=self.send('large',partner=3,quantity=n);self.rev=self.service._row(self.t)['revision_id']
        self.acceptance.accept(self.t,3,self.rev,'accept-large')
    def reduction(self,n=22,actor=1):
        ps=[[p[k] for k in ('from_user_id','to_user_id','album_id','sticker_code')]+[n] for p in self.view()['positions']]
        self.call('reduction_propose',actor,{'positions':ps})
        return self.view()['pending']['revision_id']
    def supply(self,u,c):return InventoryReadService(self.db).snapshot(u,'vfl',(c,)).sticker(c).available

    def test_deadline_packlist_inventory_unchanged(self):
        before=[tuple(r) for r in self.db.execute('SELECT * FROM stickers')]
        v=self.view();self.assertEqual((self.now+timedelta(hours=72)).isoformat(),v['deadline'])
        self.assertEqual(2,len(v['positions']));self.assertEqual([1,1],[p['quantity'] for p in v['positions']])
        self.both();self.assertEqual(before,[tuple(r) for r in self.db.execute('SELECT * FROM stickers')])

    def test_mandatory_multiple_photos_and_frozen_complete(self):
        with self.assertRaises(ValueError):self.call('complete')
        p=self.photo();q=self.photo();self.assertNotEqual(p,q)
        v=self.view();self.call('complete',key='same',model=v);self.call('complete',key='same',model=v)
        with self.assertRaises(ValueError):self.photo()
        with self.assertRaises(ValueError):self.call('remove_photo',data={'photo':p})
        self.assertEqual(1,self.db.execute("SELECT COUNT(*) FROM trade_events WHERE event_type='PreparationConfirmed'").fetchone()[0])

    def test_blind_barrier_and_private_direct_access(self):
        p=self.photo();q=self.photo(2);self.call('complete')
        self.assertEqual(p,self.s.photo(self.t,1,p)['id'])
        for actor,photo in ((2,p),(1,q),(3,p)):
            with self.assertRaises(ValueError):self.s.photo(self.t,actor,photo)
        self.call('complete',2)
        self.assertEqual(p,self.s.photo(self.t,2,p)['id']);self.assertEqual(q,self.s.photo(self.t,1,q)['id'])
        with self.assertRaises(ValueError):self.s.photo(999,1,p)
        with self.assertRaises(ValueError):self.s.photo(self.t,1,999)

    def test_both_approvals_ready_no_address_shipping(self):
        self.both();self.call('approve');self.assertEqual('photo_review',self.view()['state'])
        self.call('approve',2);self.assertEqual('ready_for_address_release',self.view()['state'])
        self.assertEqual({'not_sent'},set(r[0] for r in self.db.execute('SELECT shipping_state FROM lifecycle_directions')))
        self.assertNotIn('address',self.view())

    def test_review_before_reveal_and_foreign_actor_forbidden(self):
        with self.assertRaises(ValueError):self.call('approve')
        with self.assertRaises(ValueError):self.view(3)
        with self.assertRaises(ValueError):self.s.command(self.t,3,self.rev,self.view()['basis'],'foreign','complete')

    def test_problem_correction_invalidates_exact_package(self):
        self.both();self.call('approve',2);self.call('problem',data={'reason':'NOT_RECOGNIZABLE'})
        self.assertEqual('photo_problem',self.view()['state']);old=self.view();oldphoto=old['cycles'][1]['photos'][0]['id']
        self.call('correct',2)
        with self.assertRaises(ValueError):self.s.photo(self.t,1,oldphoto)
        with self.assertRaises(ValueError):self.call('approve',model=old)
        self.photo(2);self.call('complete',2)
        self.assertEqual('approved',self.view()['cycles'][0]['review_state'])
        self.call('approve');self.assertEqual('ready_for_address_release',self.view()['state'])

    def test_all_problem_reasons_and_quantity_validation(self):
        for reason in ('MISSING_STICKER','WRONG_STICKER','CONDITION_PROBLEM','NOT_RECOGNIZABLE'):
            self.both() if reason=='MISSING_STICKER' else None
            self.call('problem',data={'reason':reason});self.call('correct',2);self.photo(2);self.call('complete',2)
        with self.assertRaises(ValueError):self.call('problem',data={'reason':'OTHER'})
        with self.assertRaises(ValueError):self.call('problem',data={'reason':'MISSING_STICKER','position':self.view()['positions'][0]['id'],'quantity':1})

    def test_overdue_event_once_no_cancel_or_hold_release(self):
        self.now+=timedelta(hours=72)
        self.view();self.view()
        self.assertEqual(2,self.db.execute("SELECT COUNT(*) FROM trade_events WHERE event_type='PackingOverdue'").fetchone()[0])
        self.assertEqual(2,self.db.execute("SELECT COUNT(*) FROM trade_reservations WHERE state='active'").fetchone()[0])
        self.both();self.call('approve');self.call('approve',2)
        self.assertEqual('ready_for_address_release',self.view()['state'])

    def test_review_has_no_deadline(self):
        self.both();self.now+=timedelta(days=99);self.view()
        self.assertEqual(0,self.db.execute("SELECT COUNT(*) FROM trade_events WHERE event_type='PackingOverdue'").fetchone()[0])
        self.call('approve');self.call('approve',2)
        self.assertEqual('ready_for_address_release',self.view()['state'])

    def test_reduction_bilateral_exact_immutable_and_resources(self):
        self.larger();old=self.rev;before=[tuple(p) for p in self.s._positions(old)];due=self.view()['deadline']
        r=self.reduction();self.assertEqual(old,self.view()['revision']);self.assertEqual('reduction_pending',self.view()['state'])
        with self.assertRaises(ValueError):self.call('reduction_approve',data={'proposal':r})
        self.call('reduction_approve',3,{'proposal':r})
        self.assertEqual(r,self.view()['revision']);self.assertEqual(due,self.view()['deadline'])
        self.assertEqual(before,[tuple(p) for p in self.s._positions(old)])
        self.assertEqual([22,22],[p['quantity'] for p in self.s._positions(r)])
        self.assertEqual(44,self.db.execute('SELECT SUM(quantity) FROM trade_reservations WHERE trade_id=? AND state=\'active\'',(self.t,)).fetchone()[0])
        self.assertEqual(1,self.supply(1,'11'))
        self.assertEqual(44,self.db.execute("SELECT SUM(c.quantity) FROM lifecycle_need_claims c JOIN lifecycle_revision_positions p ON p.id=c.revision_position_id WHERE p.revision_id=? AND c.state='committed'",(r,)).fetchone()[0])

    def test_reduction_reject_retains_binding_and_no_cancel(self):
        self.larger();r=self.reduction();self.call('reduction_reject',3,{'proposal':r})
        self.assertEqual(self.rev,self.view()['revision']);self.assertEqual(0,self.supply(1,'11'))
        self.assertEqual('accepted',self.db.execute('SELECT state FROM lifecycle_contracts WHERE trade_id=?',(self.t,)).fetchone()[0])

    def test_expansion_empty_and_new_sticker_rejected(self):
        self.larger()
        for n in (23,24,0):
            with self.assertRaises(ValueError):self.reduction(n)
        ps=[[1,3,'vfl','new',1],[3,1,'vfl','16',1]]
        with self.assertRaises(ValueError):self.call('reduction_propose',data={'positions':ps})

    def test_reduction_resets_completed_photos_reviews(self):
        self.larger()
        for a in (1,3):self.photo(a);self.call('complete',a)
        self.call('approve');self.call('approve',3);v=self.view()
        p=v['cycles'][0]['photos'][0]['id'];r=self.reduction();self.call('reduction_approve',3,{'proposal':r})
        self.assertEqual('preparation',self.view()['state'])
        with self.assertRaises(ValueError):self.s.photo(self.t,1,p)
        with self.assertRaises(ValueError):self.call('approve',model=v)

    def test_missing_overlap_no_double_subtraction_and_survives_reduction(self):
        self.larger();self.stock(1,'11',26);p=self.view()['positions'][0]['id'];before=self.supply(1,'11')
        v=self.view();self.call('missing',data={'position':p,'quantity':1},key='missing',model=v)
        self.call('missing',data={'position':p,'quantity':1},key='missing',model=v)
        self.assertEqual(before,self.supply(1,'11'));self.assertEqual(1,self.db.execute('SELECT COUNT(*) FROM physical_missing_holds').fetchone()[0])
        r=self.reduction();self.call('reduction_approve',3,{'proposal':r})
        self.assertEqual(before,self.supply(1,'11'));self.assertEqual(1,extras(self.db)[(1,'vfl','11')])
        self.assertEqual(26,self.db.execute("SELECT quantity FROM stickers WHERE user_id=1 AND sticker_code='11'").fetchone()[0])
        self.now+=timedelta(days=999);self.view();self.assertEqual(1,extras(self.db)[(1,'vfl','11')])

    def test_missing_rejected_reduction_preserves_both_holds(self):
        self.larger();p=self.view()['positions'][0]['id'];self.call('missing',data={'position':p,'quantity':1})
        r=self.reduction();self.call('reduction_reject',3,{'proposal':r})
        self.assertEqual((1,1,None),tuple(self.db.execute('SELECT quantity,overlap_quantity,resolved_at FROM physical_missing_holds').fetchone()))
        self.assertEqual('physical_missing',self.view()['state'])
        self.photo()
        with self.assertRaises(ValueError):self.call('complete')

    def test_missing_found_and_atomic_stock_correction(self):
        self.larger();p=self.view()['positions'][0]['id'];self.call('missing',data={'position':p,'quantity':1})
        h=self.db.execute('SELECT id FROM physical_missing_holds').fetchone()[0]
        with self.assertRaises(ValueError):self.s.resolve_missing(self.t,3,'foreign',h,'found')
        with self.assertRaises(ValueError):self.s.resolve_missing(self.t,1,'early',h,'corrected')
        self.s.resolve_missing(self.t,1,'found',h,'found');self.s.resolve_missing(self.t,1,'found',h,'found')
        self.assertEqual(24,self.db.execute("SELECT quantity FROM stickers WHERE user_id=1 AND sticker_code='11'").fetchone()[0])
        self.call('missing',data={'position':p,'quantity':1});h=self.db.execute('SELECT MAX(id) FROM physical_missing_holds').fetchone()[0]
        r=self.reduction();self.call('reduction_approve',3,{'proposal':r})
        self.s.resolve_missing(self.t,1,'correct',h,'corrected')
        self.assertEqual(23,self.db.execute("SELECT quantity FROM stickers WHERE user_id=1 AND sticker_code='11'").fetchone()[0])
        self.assertEqual(0,self.supply(1,'11'));self.assertEqual({},extras(self.db))

    def test_missing_foreign_position_and_invalid_quantities(self):
        positions=self.view()['positions']
        for position,n in ((positions[1]['id'],1),(positions[0]['id'],2),(positions[0]['id'],0)):
            with self.assertRaises(ValueError):self.call('missing',data={'position':position,'quantity':n})

    def test_upload_idempotency_and_invalid_payload(self):
        p=self.photo(key='upload');self.assertEqual(p,self.photo(key='upload'));self.assertEqual(1,len(list(self.storage.iterdir())))
        v=self.view()
        with self.assertRaises(ValueError):self.s.upload(self.t,1,self.rev,v['basis'],'bad',b'<svg/>',self.storage)

    def test_draft_removal_requires_owner(self):
        p=self.photo();self.call('remove_photo',data={'photo':p})
        with self.assertRaises(ValueError):self.s.photo(self.t,1,p)
        q=self.photo(2)
        with self.assertRaises(ValueError):self.call('remove_photo',data={'photo':q})

    def test_double_complete_and_review_races(self):
        self.photo();self.photo(2);v=self.view()
        def command(a,action,key):
            return lambda request:LifecyclePreparation(request.db,lambda:self.now).command(self.t,a,self.rev,v['basis'],key,action)
        result=self.race([command(1,'complete','a'),command(2,'complete','b')]);self.assertEqual(['ok','ok'],sorted(r[0] for r in result))
        self.assertEqual(1,self.db.execute("SELECT COUNT(*) FROM trade_events WHERE event_type='BothPackagesVisible'").fetchone()[0])
        result=self.race([command(1,'approve','c'),command(2,'approve','d')]);self.assertEqual(['ok','ok'],sorted(r[0] for r in result))
        self.assertEqual('ready_for_address_release',self.view()['state'])

    def test_reduction_approve_reject_race(self):
        self.larger();r=self.reduction();v=self.view(3)
        functions=[lambda request,a=a:LifecyclePreparation(request.db,lambda:self.now).command(self.t,3,self.rev,v['basis'],a,a,{'proposal':r}) for a in ('reduction_approve','reduction_reject')]
        result=self.race(functions);self.assertEqual(['conflict','ok'],sorted(r[0] for r in result))

    def test_atomic_rollback_during_activation(self):
        self.larger();r=self.reduction()
        before=[tuple(r) for r in self.db.execute('SELECT * FROM trade_reservations')]
        with patch.object(self.s.store,'bind_supply_position',side_effect=ValueError('injected')):
            with self.assertRaises(ValueError):self.call('reduction_approve',3,{'proposal':r})
        self.assertEqual(before,[tuple(r) for r in self.db.execute('SELECT * FROM trade_reservations')]);self.assertEqual(self.rev,self.view()['revision'])

    def test_frozen_cross_album_reduction_after_global_settings_change(self):
        from services.smartdeal_optimizer import SmartDealPiece as Piece
        for user in (1,2):self.db.execute("INSERT INTO user_albums(user_id,album_id,trade_pool_enabled,cross_album_mode) VALUES (?,'em24',1,'CROSS_ALBUM_ALLOWED')",(user,))
        self.db.execute("UPDATE user_albums SET cross_album_mode='CROSS_ALBUM_ALLOWED'")
        self.db.execute("INSERT INTO stickers(user_id,album_id,sticker_code,quantity,duplicates) VALUES (2,'em24','TOPPS 1',4,3)")
        self.db.execute("INSERT INTO lifecycle_need_targets VALUES (1,'em24','TOPPS 1',3)")
        self.db.commit();self.stock(1,'1',5);self.target(2,'1',4)
        self.t=self.service.create(1,2,(Piece('vfl','1',3),),(Piece('em24','TOPPS 1',3),),'cross')
        self.rev=self.service._row(self.t)['revision_id'];self.acceptance.accept(self.t,2,self.rev,'cross-accept')
        snapshot=self.db.execute('SELECT payload_json FROM lifecycle_rule_snapshots WHERE revision_id=?',(self.rev,)).fetchone()[0]
        self.db.execute("UPDATE user_albums SET cross_album_mode='SAME_ALBUM_ONLY',trade_pool_enabled=0");self.db.commit()
        r=self.reduction(2);self.call('reduction_approve',2,{'proposal':r})
        self.assertEqual(snapshot,self.db.execute('SELECT payload_json FROM lifecycle_rule_snapshots WHERE revision_id=?',(r,)).fetchone()[0])

    def test_wrong_album_and_asymmetric_frozen_balance(self):
        from services.trade_lifecycle_foundation import RuleSnapshot
        snapshot=RuleSnapshot(1,2,'MANUAL',False,(('vfl',True,True,'SAME_ALBUM_ONLY','SAME_ALBUM_ONLY'),('em24',True,True,'SAME_ALBUM_ONLY','SAME_ALBUM_ONLY')))
        snapshot.validate([(1,2,'vfl','1',3),(2,1,'vfl','2',2)])
        with self.assertRaises(ValueError):snapshot.validate([(1,2,'vfl','1',2),(2,1,'em24','2',2)])
        with self.assertRaises(ValueError):snapshot.validate([(1,2,'vfl','1',2),(2,1,'vfl','2',3)])

    def test_all_availability_readers_exclude_only_missing_quantity(self):
        self.larger();self.stock(1,'11',26);p=self.view()['positions'][0]['id']
        self.call('missing',data={'position':p,'quantity':2})
        r=self.reduction(21);self.call('reduction_approve',3,{'proposal':r})
        inv=InventoryReadService(self.db);self.assertEqual(2,self.supply(1,'11'))
        self.assertTrue(inv.snapshot(1,'vfl').sticker('11').balance_is_valid)
        self.assertIn('11',inv.matching_states((1,),'vfl',('11',))[1].available_codes)
        self.assertEqual(2,inv.collection_summaries(1,{'vfl':('11',)},{'vfl':1})['vfl'].progress.duplicate_quantity)
        from services.trade_v2_domain import TradeV2Domain
        m=TradeV2Domain(self.db).market(1)
        supply=next(p for p in m.inputs.subject.outgoing_supply if p.sticker_code=='11')
        self.assertEqual(2,supply.quantity)
        self.stock(1,'11',24)
        self.assertNotIn('11',inv.matching_states((1,),'vfl',('11',))[1].available_codes)
        self.assertNotIn('11',inv.album_market_projection(3,(1,),'vfl',('11',)).get_codes_by_user[1])

    def test_missing_cumulative_then_new_revision_declaration(self):
        self.larger();p=self.view()['positions'][0]['id']
        self.call('missing',data={'position':p,'quantity':1});self.call('missing',data={'position':p,'quantity':2})
        self.assertEqual(1,self.db.execute('SELECT COUNT(*) FROM physical_missing_holds').fetchone()[0])
        r=self.reduction(21);self.call('reduction_approve',3,{'proposal':r})
        p=self.view()['positions'][0]['id'];self.call('missing',data={'position':p,'quantity':1})
        self.assertEqual([(2,0),(1,1)],[tuple(r) for r in self.db.execute('SELECT quantity,overlap_quantity FROM physical_missing_holds ORDER BY id')])

    def test_completed_missing_declaration_invalidates_readiness(self):
        self.ready();p=self.view()['positions'][0]['id'];self.call('missing',data={'position':p,'quantity':1})
        self.assertEqual('physical_missing',self.view()['state'])
        h=self.db.execute('SELECT id FROM physical_missing_holds').fetchone()[0]
        self.s.resolve_missing(self.t,1,'found',h,'found')
        self.assertEqual('preparation',self.view()['state'])

    def test_upload_complete_race_preserves_frozen_package(self):
        self.photo();v=self.view()
        functions=[lambda q:LifecyclePreparation(q.db,lambda:self.now).command(self.t,1,self.rev,v['basis'],'complete','complete'),
                   lambda q:LifecyclePreparation(q.db,lambda:self.now).upload(self.t,1,self.rev,v['basis'],'upload',PNG,self.storage)]
        results=self.race(functions)
        self.assertIn('ok',[r[0] for r in results]);self.assertIsNotNone(self.view()['cycles'][0]['completed_at'])
        self.assertIn(self.db.execute('SELECT COUNT(*) FROM lifecycle_control_photos').fetchone()[0],(1,2))

    def test_complete_reduction_proposal_race(self):
        self.larger();self.photo();v=self.view()
        positions=[[p[k] for k in ('from_user_id','to_user_id','album_id','sticker_code')]+[22] for p in v['positions']]
        results=self.race([lambda q:LifecyclePreparation(q.db,lambda:self.now).command(self.t,1,self.rev,v['basis'],'complete','complete'),
            lambda q:LifecyclePreparation(q.db,lambda:self.now).command(self.t,3,self.rev,v['basis'],'reduce','reduction_propose',{'positions':positions})])
        self.assertIn('ok',[r[0] for r in results]);self.assertEqual('reduction_pending',self.view()['state'])

    def test_review_approve_problem_race(self):
        self.both();v=self.view()
        results=self.race([lambda q,a=a:LifecyclePreparation(q.db,lambda:self.now).command(self.t,1,self.rev,v['basis'],a,a,{'reason':'NOT_RECOGNIZABLE'} if a=='problem' else {}) for a in ('approve','problem')])
        self.assertEqual(['conflict','ok'],sorted(r[0] for r in results))

    def test_correction_upload_stale_review_race(self):
        self.both();old=self.view();self.call('correct',2);v=self.view()
        results=self.race([lambda q:LifecyclePreparation(q.db,lambda:self.now).upload(self.t,2,self.rev,v['basis'],'correct-photo',PNG,self.storage),
            lambda q:LifecyclePreparation(q.db,lambda:self.now).command(self.t,1,self.rev,old['basis'],'stale-review','approve')])
        self.assertEqual(['conflict','ok'],sorted(r[0] for r in results))
        self.assertEqual('preparation',self.view()['state'])

    def test_reduction_inventory_write_race(self):
        from services.inventory_write import InventoryWriteService
        self.larger();r=self.reduction();v=self.view(3)
        def inventory(q):
            with q.store.transaction():
                result=InventoryWriteService(q.db).set_quantity(1,'vfl','11',22)
                if not result.allowed:raise ValueError('Bound inventory')
                return result.quantity
        results=self.race([inventory,lambda q:LifecyclePreparation(q.db,lambda:self.now).command(self.t,3,self.rev,v['basis'],'approve','reduction_approve',{'proposal':r})])
        self.assertEqual(['conflict','ok'],sorted(r[0] for r in results));self.assertEqual(r,self.view()['revision'])

    def test_reduction_reject_after_reviews_never_ready(self):
        self.larger()
        for a in (1,3):self.photo(a);self.call('complete',a)
        self.call('approve');self.call('approve',3)
        r=self.reduction();self.call('reduction_reject',3,{'proposal':r})
        self.assertEqual('reduction_rejected',self.view()['state'])

    def test_schema_upgrade_and_guarded_downgrade(self):
        self.assertEqual([],self.db.execute('PRAGMA foreign_key_check').fetchall())
        self.assertEqual('ok',self.db.execute('PRAGMA integrity_check').fetchone()[0])
        self.view()
        with self.assertRaises(sqlite3.IntegrityError):rollback(self.db,25)
        self.db.rollback()
        self.assertTrue(self.db.execute("SELECT 1 FROM sqlite_master WHERE name='lifecycle_preparation_cycles'").fetchone())

    def test_migration_26_preserves_existing_acceptance_and_empty_roundtrip(self):
        before=[tuple(r) for r in self.db.execute('SELECT * FROM lifecycle_acceptances')]
        self.assertEqual((26,),rollback(self.db,25))
        self.assertEqual((26,),migrate(self.db,26))
        self.assertEqual(before,[tuple(r) for r in self.db.execute('SELECT * FROM lifecycle_acceptances')])
        self.assertEqual(self.rev,self.view()['revision'])

    def test_legacy_trade_cannot_enter_preparation(self):
        legacy=self.db.execute("INSERT INTO trades(requester_user_id,partner_user_id,lifecycle_state) VALUES (1,2,'accepted')").lastrowid
        self.db.commit()
        with self.assertRaises(ValueError):self.s.view(legacy,1)
        self.assertEqual(0,self.db.execute('SELECT COUNT(*) FROM lifecycle_preparation_cycles WHERE trade_id=?',(legacy,)).fetchone()[0])

    def test_missing_hold_survives_trade_end_and_can_be_found_explicitly(self):
        self.larger();p=self.view()['positions'][0]['id'];self.call('missing',data={'position':p,'quantity':1})
        r=self.reduction();self.call('reduction_approve',3,{'proposal':r})
        h=self.db.execute('SELECT id FROM physical_missing_holds').fetchone()[0]
        self.db.execute("UPDATE lifecycle_contracts SET state='ended' WHERE trade_id=?",(self.t,));self.db.commit()
        self.assertEqual(1,extras(self.db)[(1,'vfl','11')])
        self.s.resolve_missing(self.t,1,'found-after-end',h,'found')
        self.assertEqual({},extras(self.db))

    def test_live_reservation_cannot_consume_quarantined_supply(self):
        self.larger();p=self.view()['positions'][0]['id'];self.call('missing',data={'position':p,'quantity':1})
        r=self.reduction();self.call('reduction_approve',3,{'proposal':r})
        from services.smartdeal_optimizer import SmartDealPiece as Piece
        self.target(2,'11',1)
        with self.assertRaises(ValueError):self.service.create(1,2,(Piece('vfl','11'),),(Piece('vfl','7'),),'phantom')
        self.assertEqual(0,self.supply(1,'11'))

if __name__=='__main__':unittest.main()
