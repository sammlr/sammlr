"""Synthetic-only request admission, releases, projection and serialized races."""
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'App'))
from tests.test_integration01_trade_shell import fixture
from App.Database.migration_runner import migrate,rollback,current_version
from services.trade_lifecycle_requests import LifecycleRequests
from services.trade_lifecycle_foundation import lifecycle_availability
from services.smartdeal_optimizer import SmartDealPiece as Piece
from services.trade_v2_domain import TradeV2Domain
from services.trade_contracts import trade_contract_type


class RequestsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='lifecycle02-',dir='/private/tmp')
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'synthetic.db'
        fixture(self.path,4)
        self.db=self.connect();self.addCleanup(self.db.close)
        migrate(self.db,24)
        self.now=datetime(2040,3,25,12,0,0,123456,tzinfo=timezone.utc)
        self.service=LifecycleRequests(self.db,lambda:self.now)

    def connect(self):
        db=sqlite3.connect(self.path,timeout=10);db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON');return db

    def send(self,key='one',partner=2,quantity=1,actor=1,service=None):
        offset=(partner-2)*10
        return (service or self.service).create(actor,partner,(Piece('vfl',str(1+offset),quantity),),
            (Piece('vfl',str(6+offset),quantity),),key)

    def target(self,user,code,quantity):
        self.db.execute('INSERT OR REPLACE INTO lifecycle_need_targets VALUES (?,\'vfl\',?,?)',(user,code,quantity));self.db.commit()

    def stock(self,user,code,quantity):
        self.db.execute("UPDATE stickers SET quantity=?,duplicates=? WHERE user_id=? AND sticker_code=?",(quantity,quantity-1,user,code));self.db.commit()

    def counts(self):
        return tuple(self.db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in
                     ('trades','lifecycle_requests','lifecycle_revisions','trade_reservations','lifecycle_need_claims','trade_events'))

    def available(self):return lifecycle_availability(self.db,1,'vfl','6',now=self.now)

    def race(self,functions):
        barrier=threading.Barrier(len(functions));results=[]
        def run(fn):
            db=self.connect()
            try:
                barrier.wait();results.append(('ok',fn(LifecycleRequests(db,lambda:self.now))))
            except ValueError:results.append(('conflict',None))
            finally:db.close()
        ts=[threading.Thread(target=run,args=(fn,)) for fn in functions]
        for t in ts:t.start()
        for t in ts:t.join(20);self.assertFalse(t.is_alive())
        self.assertEqual(len(functions),len(results));return results

    def test_create_exact_atomic_and_no_recipient_hold(self):
        before=[tuple(r) for r in self.db.execute('SELECT * FROM stickers')]
        t=self.send();q=self.db.execute('SELECT * FROM lifecycle_requests').fetchone()
        self.assertEqual('trade_lifecycle_v1',trade_contract_type(self.db,t))
        self.assertEqual(t,q['trade_id']);self.assertEqual('open',q['status'])
        self.assertEqual(timedelta(hours=72),datetime.fromisoformat(q['expires_at'])-datetime.fromisoformat(q['created_at']))
        self.assertEqual((1,1,1,1,1,1),self.counts())
        self.assertEqual([(1,1)],[tuple(r) for r in self.db.execute('SELECT user_id,quantity FROM trade_reservations')])
        self.assertEqual(before,[tuple(r) for r in self.db.execute('SELECT * FROM stickers')])
        self.assertEqual(0,self.db.execute('SELECT COUNT(*) FROM lifecycle_rule_snapshots').fetchone()[0])

    def test_invalid_deals_are_atomic(self):
        for give,receive in [([],[]),([Piece('vfl','6')],[Piece('vfl','1')]),([Piece('vfl','1',2)],[Piece('vfl','6',2)]),([Piece('vfl','1')],[Piece('vfl','6',2)]),([Piece('vfl','1',True)],[Piece('vfl','6')])]:
            with self.assertRaises(ValueError):self.service.create(1,2,give,receive,'bad')
            self.assertEqual((0,)*6,self.counts())

    def test_self_inactive_and_foreign_actor(self):
        with self.assertRaises(ValueError):self.send(partner=1)
        with self.assertRaises(ValueError):self.send(actor=999)
        self.db.execute("UPDATE users SET account_state='anonymized' WHERE id=2");self.db.commit()
        with self.assertRaises(ValueError):self.send()
        self.assertEqual((0,)*6,self.counts())

    def test_pool_and_need_revalidated(self):
        self.target(1,'6',0)
        with self.assertRaises(ValueError):self.send()
        self.target(1,'6',1)
        self.db.execute('UPDATE user_albums SET trade_pool_enabled=0 WHERE user_id=2');self.db.commit()
        with self.assertRaises(ValueError):self.send()

    def test_quantities_release_projection(self):
        self.target(1,'6',2);self.target(2,'1',3)
        self.stock(1,'1',4);self.stock(2,'6',4)
        a=self.send('a');b=self.service.create(1,2,(Piece('vfl','1',2),),(Piece('vfl','6'),),'b')
        self.assertEqual(0,self.available().free_need)
        with self.assertRaises(ValueError):self.send('extra')
        self.assertEqual('withdrawn',self.service.transition(a,1,'withdrawn'))
        self.assertEqual(1,self.available().free_need)
        pair=next(p for p in TradeV2Domain(self.db).market(1).pairs if p.partner_id==2)
        self.assertEqual(1,next(p.quantity for p in pair.incoming_candidates if p.sticker_code=='6'))
        self.assertEqual('rejected',self.service.transition(b,2,'rejected'))
        self.assertEqual(2,self.available().free_need)
        pair=next(p for p in TradeV2Domain(self.db).market(1).pairs if p.partner_id==2)
        self.assertEqual(2,next(p.quantity for p in pair.incoming_candidates if p.sticker_code=='6'))

    def test_three_limit_and_release(self):
        ids=[self.send(str(p),p) for p in (2,3,4)]
        with self.assertRaisesRegex(ValueError,'drei'):self.send('four',5)
        self.service.transition(ids[0],1,'withdrawn');self.send('four',5)
        self.assertEqual(3,self.db.execute("SELECT COUNT(*) FROM lifecycle_requests WHERE status='open'").fetchone()[0])

    def test_expiry_deadline_and_read_projection(self):
        t=self.send()
        self.now+=timedelta(hours=72)
        self.assertEqual('expired',self.service.transition(t,1,'withdrawn'))
        self.assertEqual(0,self.service.expire());self.assertEqual(1,self.available().free_need)
        self.assertEqual(2,self.db.execute('SELECT COUNT(*) FROM trade_events').fetchone()[0])

    def test_just_before_expiry(self):
        t=self.send();self.now+=timedelta(hours=72,microseconds=-1)
        self.assertEqual('rejected',self.service.transition(t,2,'rejected'))

    def test_lazy_read_and_idempotent_expiry(self):
        t=self.send();self.now+=timedelta(hours=73)
        self.assertEqual('expired',self.service.view(2,t)[0]['status'])
        self.assertEqual(0,self.service.expire())
        self.assertEqual('expired',self.service.transition(t,2,'rejected'))

    def test_roles_no_accept_and_private_read(self):
        t=self.send()
        for actor,action in [(2,'withdrawn'),(1,'rejected'),(3,'rejected'),(1,'accepted')]:
            with self.assertRaises(ValueError):self.service.transition(t,actor,action)
        with self.assertRaises(ValueError):self.service.view(3,t)
        self.assertEqual('open',self.service.view(2,t)[0]['status'])

    def test_double_send_retry_conflict(self):
        t=self.send();self.assertEqual(t,self.send())
        with self.assertRaises(ValueError):self.send(partner=3)
        self.service.transition(t,1,'withdrawn');self.assertEqual(t,self.send())
        self.assertEqual(1,self.counts()[0])

    def test_double_release_no_stock_change(self):
        before=[tuple(r) for r in self.db.execute('SELECT * FROM stickers')]
        t=self.send();self.service.transition(t,2,'rejected');self.service.transition(t,2,'rejected')
        self.assertEqual('rejected',self.service.transition(t,1,'withdrawn'))
        self.assertEqual(2,self.counts()[-1]);self.assertEqual(1,self.available().free_need)
        self.assertEqual(before,[tuple(r) for r in self.db.execute('SELECT * FROM stickers')])

    def test_recipient_can_use_supply_without_changing_request(self):
        t=self.send();before=[tuple(r) for r in self.db.execute('SELECT * FROM lifecycle_revision_positions')]
        self.stock(2,'6',1)
        self.assertEqual('open',self.service.view(1,t)[0]['status'])
        self.assertEqual(before,[tuple(r) for r in self.db.execute('SELECT * FROM lifecycle_revision_positions')])

    def test_parallel_same_key(self):
        r=self.race([lambda s:self.send(service=s),lambda s:self.send(service=s)])
        self.assertEqual(1,len({t for status,t in r}));self.assertEqual(1,self.counts()[0])

    def test_parallel_last_need(self):
        self.stock(1,'1',3);self.target(2,'1',2)
        r=self.race([lambda s:self.send('a',service=s),lambda s:self.send('b',service=s)])
        self.assertEqual(['conflict','ok'],sorted(x[0] for x in r))

    def test_parallel_last_supply(self):
        self.target(1,'6',2)
        r=self.race([lambda s:self.send('a',service=s),lambda s:self.send('b',service=s)])
        self.assertEqual(['conflict','ok'],sorted(x[0] for x in r))

    def test_parallel_third_fourth(self):
        self.send('a',2);self.send('b',3)
        r=self.race([lambda s:self.send('c',4,service=s),lambda s:self.send('d',5,service=s)])
        self.assertEqual(['conflict','ok'],sorted(x[0] for x in r));self.assertEqual(3,self.counts()[0])

    def test_parallel_terminal(self):
        t=self.send()
        r=self.race([lambda s:s.transition(t,1,'withdrawn'),lambda s:s.transition(t,2,'rejected')])
        self.assertEqual(1,len({v for _,v in r}));self.assertEqual(2,self.counts()[-1])

    def test_parallel_expiry_withdraw_reject(self):
        t=self.send();self.now+=timedelta(hours=72)
        r=self.race([lambda s:s.expire(),lambda s:s.transition(t,1,'withdrawn'),lambda s:s.transition(t,2,'rejected')])
        self.assertEqual('expired',self.service.view(1,t)[0]['status']);self.assertEqual(2,self.counts()[-1])

    def test_mid_command_failure_rolls_back(self):
        with patch.object(self.service,'_event',side_effect=RuntimeError('synthetic failure')):
            with self.assertRaises(RuntimeError):self.send()
        self.assertEqual((0,)*6,self.counts())

    def test_legacy_not_in_quota_or_expiry(self):
        for _ in range(5):self.db.execute("INSERT INTO trade_requests(album_id,from_user_id,to_user_id,status,created_at) VALUES ('vfl',1,2,'open','2000-01-01')")
        self.db.commit();self.send();self.service.expire()
        self.assertEqual(5,self.db.execute("SELECT COUNT(*) FROM trade_requests WHERE status='open'").fetchone()[0])

    def test_migration_preserves_and_refuses_populated_rollback(self):
        self.send()
        with self.assertRaises(sqlite3.IntegrityError):rollback(self.db,23)
        self.assertEqual(24,current_version(self.db));self.assertEqual([],self.db.execute('PRAGMA foreign_key_check').fetchall())

    def test_quantity_optimizer_and_global_need(self):
        for code in ['6','7','8','9','10']:self.target(1,code,2);self.stock(2,code,3)
        for code in ['1','2','3','4','5']:self.target(2,code,2);self.stock(1,code,3)
        market=TradeV2Domain(self.db).market(1)
        from services.partner_trade import partner_deal
        pair=next(p for p in market.pairs if p.partner_id==2)
        self.assertEqual(10,pair.max_equal_piece_count)
        deal=partner_deal(market,pair);self.assertEqual(10,deal.piece_count)
        self.assertTrue(all(p.quantity==2 for p in deal.incoming_pieces))
        t=self.service.create(1,2,deal.outgoing_pieces,deal.incoming_pieces,'smart',origin='SMARTDEAL')
        self.assertEqual(0,self.available().free_need)
        self.service.transition(t,2,'rejected');self.assertEqual(2,self.available().free_need)

    def test_incoming_requests_do_not_count_towards_own_limit(self):
        for n in range(3):
            self.service.create(2,1,(Piece('vfl',str(6+n)),),(Piece('vfl',str(1+n)),),str(n))
        for partner in (3,4,5):self.send(str(partner),partner)
        self.assertEqual(6,self.counts()[0])

    def test_four_incoming_allowed_and_expired_requests_free_quota(self):
        for sender in (2,3,4,5):
            offset=(sender-2)*10
            self.service.create(sender,1,(Piece('vfl',str(6+offset)),),(Piece('vfl',str(1+offset)),),str(sender))
        self.assertEqual(4,len(self.service.view(1)))
        for partner in (2,3,4):
            offset=(partner-2)*10
            self.service.create(1,partner,(Piece('vfl',str(2+offset)),),(Piece('vfl',str(7+offset)),),str(partner))
        self.now+=timedelta(hours=72)
        self.send('after-expiry',5)
        self.assertEqual(1,self.db.execute("SELECT COUNT(*) FROM lifecycle_requests WHERE status='open'").fetchone()[0])
        self.assertEqual(7,self.db.execute("SELECT COUNT(*) FROM lifecycle_requests WHERE status='expired'").fetchone()[0])

    def test_cross_album_requires_both_parties(self):
        for user in (1,2):
            self.db.execute("INSERT INTO user_albums(user_id,album_id,trade_pool_enabled) VALUES (?,'em24',1)",(user,))
        self.db.execute("INSERT INTO stickers(user_id,album_id,sticker_code,quantity,duplicates) VALUES (2,'em24','TOPPS 1',2,1)")
        self.db.commit()
        def send():return self.service.create(1,2,(Piece('vfl','1'),),(Piece('em24','TOPPS 1'),),'cross')
        with self.assertRaises(ValueError):send()
        self.db.execute("UPDATE user_albums SET cross_album_mode='CROSS_ALBUM_ALLOWED' WHERE user_id=1");self.db.commit()
        with self.assertRaises(ValueError):send()
        self.db.execute("UPDATE user_albums SET cross_album_mode='CROSS_ALBUM_ALLOWED' WHERE user_id=2");self.db.commit()
        self.assertGreater(send(),0)

    def test_expired_projection_read_only_then_sweep(self):
        self.now=datetime.now(timezone.utc)-timedelta(hours=73)
        t=self.send()
        before=self.path.read_bytes()
        market=TradeV2Domain(self.db).market(1)
        pair=next(p for p in market.pairs if p.partner_id==2)
        self.assertIn('6',[p.sticker_code for p in pair.incoming_candidates])
        self.assertIn('1',[p.sticker_code for p in pair.outgoing_candidates])
        self.assertEqual(before,self.path.read_bytes())
        self.now+=timedelta(hours=73)
        self.assertEqual(1,self.service.expire())
        self.assertEqual('expired',self.service.view(1,t)[0]['status'])

    def test_supply_three_holds_one_plus_two_then_release_one(self):
        self.target(1,'6',4);self.target(2,'1',4)
        self.stock(1,'1',4);self.stock(2,'6',5)
        a=self.send('a');self.send('b',quantity=2)
        self.assertEqual(0,lifecycle_availability(self.db,1,'vfl','1',now=self.now).supply)
        with self.assertRaises(ValueError):self.send('c')
        self.service.transition(a,1,'withdrawn')
        self.assertEqual(1,lifecycle_availability(self.db,1,'vfl','1',now=self.now).supply)

    def test_release_error_rolls_back_status_and_both_bindings(self):
        t=self.send()
        with patch.object(self.service,'_event',side_effect=RuntimeError('synthetic failure')):
            with self.assertRaises(RuntimeError):self.service.transition(t,1,'withdrawn')
        self.assertEqual('open',self.service.view(1,t)[0]['status'])
        self.assertEqual(0,self.available().free_need)
        self.assertEqual('active',self.db.execute('SELECT state FROM trade_reservations').fetchone()[0])

    def test_request_identity_and_deadline_immutable(self):
        t=self.send()
        for sql in ["UPDATE lifecycle_requests SET expires_at=created_at", "DELETE FROM lifecycle_requests",
                    "UPDATE lifecycle_requests SET sender_user_id=2"]:
            with self.assertRaises(sqlite3.IntegrityError):self.db.execute(sql)
            self.db.rollback()
        self.assertEqual('open',self.service.view(1,t)[0]['status'])

    def test_empty_upgrade_and_down_roundtrip(self):
        self.assertEqual((24,),rollback(self.db,23))
        before=[tuple(r) for r in self.db.execute('SELECT * FROM users')]
        self.assertEqual((24,),migrate(self.db,24));self.assertEqual((),migrate(self.db,24))
        self.assertEqual(before,[tuple(r) for r in self.db.execute('SELECT * FROM users')])

if __name__=='__main__':unittest.main()
