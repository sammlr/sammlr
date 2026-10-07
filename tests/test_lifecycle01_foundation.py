"""Synthetic-only LIFECYCLE-01 foundation tests, no application/real DB import."""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'App'))
from App.Database.migration_runner import migrate, rollback, current_version
from services.trade_contracts import trade_contract_type, require_trade_operation, TRADE_LIFECYCLE_V1_CONTRACT
from services.trade_lifecycle_foundation import LifecycleFoundation, RuleSnapshot, lifecycle_availability
from services.trade_v2_domain import TradeV2Domain
from services.inventory import InventoryReadService


class LifecycleFoundationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='lifecycle01-', dir='/private/tmp')
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'synthetic.db'
        self.db = self.connect()
        self.addCleanup(self.db.close)
        self.db.executescript((ROOT / 'App/Database/sammlr_reference_s00.sql').read_text())
        migrate(self.db, 22)
        self.db.execute('DELETE FROM stickers')
        self.db.executemany('INSERT INTO stickers(user_id,album_id,sticker_code,quantity,duplicates) VALUES (?,\'vfl\',?,?,?)',
                            [(1,'1',3,2),(2,'2',4,3)])
        self.db.commit()
        migrate(self.db, 23)
        self.db.execute('PRAGMA foreign_keys=ON')
        self.store = LifecycleFoundation(self.db)
        self.positions = [(1,2,'vfl','1',1),(2,1,'vfl','2',1)]

    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        return db

    def draft(self, store=None, kind='original'):
        store = store or self.store
        trade = store.create_identity(1,2)
        rev = store.append_revision(trade,1,self.positions,kind)
        return trade,rev

    def rules(self):
        return RuleSnapshot(1,2,'MANUAL',False,(('vfl',True,True,'SAME_ALBUM_ONLY','SAME_ALBUM_ONLY'),))

    def target(self, value=2):
        self.db.execute('INSERT INTO lifecycle_need_targets VALUES (1,\'vfl\',\'2\',?)',(value,))
        self.db.commit()

    def test_empty_base_to_latest_and_repeat(self):
        with sqlite3.connect(':memory:') as db:
            db.execute('PRAGMA foreign_keys=ON')
            db.executescript((ROOT/'App/Database/base_schema.sql').read_text())
            self.assertEqual(tuple(range(1,24)),migrate(db))
            self.assertEqual((),migrate(db))
            self.assertEqual([],db.execute('PRAGMA foreign_key_check').fetchall())

    def test_pre22_migration_preserves_legacy_data(self):
        rollback(self.db,22)
        request=self.db.execute("INSERT INTO trade_requests(album_id,from_user_id,to_user_id,give_codes,get_codes,status) VALUES ('vfl',1,2,'[\"1\"]','[\"2\"]','accepted')").lastrowid
        trade=self.db.execute("INSERT INTO trades(legacy_trade_request_id,requester_user_id,partner_user_id,lifecycle_state) VALUES (?,1,2,'accepted')",(request,)).lastrowid
        pos=self.db.execute("INSERT INTO trade_positions(trade_id,from_user_id,to_user_id,album_id,sticker_code,quantity) VALUES (?,1,2,'vfl','1',1)",(trade,)).lastrowid
        self.db.execute("INSERT INTO trade_reservations(trade_id,trade_position_id,user_id,album_id,sticker_code,quantity) VALUES (?,?,1,'vfl','1',1)",(trade,pos))
        self.db.commit()
        tables=('trade_requests','trades','trade_positions','trade_reservations','stickers')
        before={t:[tuple(r) for r in self.db.execute('SELECT * FROM '+t)] for t in tables}
        self.assertEqual((23,),migrate(self.db))
        self.assertEqual(before,{t:[tuple(r) for r in self.db.execute('SELECT * FROM '+t)] for t in tables})
        self.assertEqual('legacy',trade_contract_type(self.db,trade))
        self.assertEqual(0,self.db.execute('SELECT COUNT(*) FROM lifecycle_need_claims').fetchone()[0])

    def test_empty_rollback_roundtrip(self):
        self.assertEqual((23,),rollback(self.db,22))
        self.assertEqual((23,),migrate(self.db,23))
        self.assertEqual((),migrate(self.db,23))
        self.assertEqual([],self.db.execute('PRAGMA foreign_key_check').fetchall())

    def test_populated_rollback_fails_atomically(self):
        with self.store.transaction():trade,rev=self.draft()
        with self.assertRaises(sqlite3.IntegrityError):rollback(self.db,22)
        self.assertEqual(23,current_version(self.db))
        self.assertEqual(TRADE_LIFECYCLE_V1_CONTRACT,trade_contract_type(self.db,trade))

    def test_new_contract_immutable_and_not_old_request(self):
        with self.store.transaction():trade,rev=self.draft()
        self.assertEqual(TRADE_LIFECYCLE_V1_CONTRACT,trade_contract_type(self.db,trade))
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE lifecycle_contracts SET contract_type='legacy' WHERE trade_id=?",(trade,))
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute('UPDATE trades SET legacy_trade_request_id=42 WHERE id=?',(trade,))
        with self.assertRaises(ValueError):require_trade_operation(self.db,trade,'legacy')
        with self.assertRaises(ValueError):require_trade_operation(self.db,trade,'ship')
        self.assertEqual(TRADE_LIFECYCLE_V1_CONTRACT,require_trade_operation(self.db,trade,'foundation'))

    def test_legacy_cannot_be_reclassified(self):
        r=self.db.execute("INSERT INTO trade_requests(album_id,from_user_id,to_user_id,give_codes,get_codes,status) VALUES ('vfl',1,2,'[\"1\"]','[\"2\"]','accepted')").lastrowid
        t=self.db.execute("INSERT INTO trades(legacy_trade_request_id,requester_user_id,partner_user_id,lifecycle_state) VALUES (?,1,2,'foundation')",(r,)).lastrowid
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("INSERT INTO lifecycle_contracts(trade_id,origin,created_at) VALUES (?,'MANUAL','now')",(t,))
        self.assertEqual('legacy',trade_contract_type(self.db,t))

    def test_revision_immutable_and_counter_limit(self):
        with self.store.transaction():
            trade,rev=self.draft()
            counter=self.store.append_revision(trade,2,self.positions,'counter')
            self.db.execute('UPDATE lifecycle_contracts SET current_revision_id=? WHERE trade_id=?',(counter,trade))
        self.assertNotEqual(rev,counter)
        self.assertEqual([1,2],[r[0] for r in self.db.execute('SELECT number FROM lifecycle_revisions ORDER BY number')])
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute('UPDATE lifecycle_revisions SET sealed=0 WHERE id=?',(rev,))
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute('UPDATE lifecycle_revision_positions SET quantity=9 WHERE revision_id=?',(rev,))
        self.db.rollback()
        with self.assertRaises(sqlite3.IntegrityError):
            with self.store.transaction():self.store.append_revision(trade,1,self.positions,'counter')
        self.assertEqual(2,self.db.execute('SELECT COUNT(*) FROM lifecycle_revisions').fetchone()[0])
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("INSERT OR REPLACE INTO lifecycle_revisions(trade_id,number,author_user_id,kind,created_at) VALUES (?,3,1,'counter','changed')",(trade,))

    def test_revision_pointer_cannot_cross_trade(self):
        with self.store.transaction():
            a,ra=self.draft();b,rb=self.draft()
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute('UPDATE lifecycle_contracts SET current_revision_id=? WHERE trade_id=?',(rb,a))

    def test_accepted_pointer_requires_snapshot_and_consents(self):
        with self.store.transaction():trade,rev=self.draft()
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute('UPDATE lifecycle_contracts SET accepted_revision_id=? WHERE trade_id=?',(rev,trade))
        self.db.rollback()
        with self.store.transaction():
            self.store.store_rule_snapshot(rev,self.rules(),'2026-10-06T12:00:00Z')
            self.db.executemany('INSERT INTO lifecycle_consents VALUES (?,?,?)',[(rev,1,'now'),(rev,2,'now')])
            self.db.execute('UPDATE lifecycle_contracts SET accepted_revision_id=? WHERE trade_id=?',(rev,trade))
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute('UPDATE lifecycle_contracts SET accepted_revision_id=NULL WHERE trade_id=?',(trade,))

    def test_snapshot_roundtrip_and_global_change(self):
        with self.store.transaction():
            trade,rev=self.draft()
            self.store.store_rule_snapshot(rev,self.rules(),'2026-10-06T12:00:00Z')
        self.db.execute("UPDATE user_albums SET cross_album_mode='CROSS_ALBUM_ALLOWED'")
        payload=self.db.execute('SELECT payload_json FROM lifecycle_rule_snapshots').fetchone()[0]
        self.assertEqual(self.rules(),RuleSnapshot.loads(payload))
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE lifecycle_rule_snapshots SET payload_json='{}'")

    def test_snapshot_rejects_wrong_participants_and_balance(self):
        with self.store.transaction():trade,rev=self.draft()
        with self.assertRaises(ValueError):
            with self.store.transaction():self.store.store_rule_snapshot(rev,RuleSnapshot(2,1,'MANUAL',False,self.rules().albums),'now')
        with self.assertRaises(ValueError):self.rules().validate([(1,2,'vfl','1',1),(2,1,'vfl','2',2)])

    def test_need_two_claim_one_release_and_no_foreign_hold(self):
        self.target()
        before=TradeV2Domain(self.db).lifecycle_availability(2,'vfl','2').supply
        with self.store.transaction():
            trade,rev=self.draft()
            self.store.bind_pending_quantities(rev)
        a=TradeV2Domain(self.db).lifecycle_availability(1,'vfl','2')
        self.assertEqual((2,1,1),(a.target,a.pending,a.free_need))
        self.assertEqual(before,TradeV2Domain(self.db).lifecycle_availability(2,'vfl','2').supply)
        self.assertEqual(1,InventoryReadService(self.db).snapshot(1,'vfl',('1',)).sticker('1').available)
        self.db.rollback()
        with self.store.transaction():self.store.release_pending_quantities(rev)
        self.assertEqual(2,TradeV2Domain(self.db).lifecycle_availability(1,'vfl','2').free_need)
        self.assertEqual(2,InventoryReadService(self.db).snapshot(1,'vfl',('1',)).sticker('1').available)

    def test_insufficient_need_rolls_back_supply_and_identity(self):
        self.target(0)
        with self.assertRaises(ValueError):
            with self.store.transaction():
                t,r=self.draft();self.store.bind_pending_quantities(r)
        self.assertEqual(0,self.db.execute('SELECT COUNT(*) FROM lifecycle_contracts').fetchone()[0])
        self.assertEqual(0,self.db.execute('SELECT COUNT(*) FROM trade_reservations').fetchone()[0])

    def test_claim_not_boolean_and_multiple_claims(self):
        self.target()
        with self.store.transaction():
            t,r=self.draft();self.store.bind_pending_quantities(r)
            t2,r2=self.draft();self.store.bind_pending_quantities(r2)
        self.assertEqual(0,TradeV2Domain(self.db).lifecycle_availability(1,'vfl','2').free_need)
        self.assertEqual(2,self.db.execute("SELECT SUM(quantity) FROM lifecycle_need_claims WHERE state='pending'").fetchone()[0])

    def test_committed_claim_not_counted_twice(self):
        self.target()
        with self.store.transaction():
            t,r=self.draft();self.store.bind_pending_quantities(r)
            self.db.execute("UPDATE lifecycle_need_claims SET state='committed'")
        a=TradeV2Domain(self.db).lifecycle_availability(1,'vfl','2')
        self.assertEqual((0,1,1),(a.pending,a.committed,a.free_need))
        with self.assertRaises(ValueError):
            with self.store.transaction():self.store.release_pending_quantities(r)

    def test_negative_fractional_and_orphan_quantities_rejected(self):
        for q in (-1,0,1.5):
            with self.assertRaises((ValueError,sqlite3.IntegrityError)):
                with self.store.transaction():
                    t=self.store.create_identity(1,2)
                    self.store.append_revision(t,1,[(1,2,'vfl','1',q),(2,1,'vfl','2',1)])
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("INSERT INTO lifecycle_need_claims(revision_position_id,state,quantity,created_at) VALUES (999,'pending',1,'now')")

    def test_foreign_receiver_cannot_claim_before_consent(self):
        with self.store.transaction():t,r=self.draft()
        p=self.db.execute('SELECT id FROM lifecycle_revision_positions WHERE from_user_id=1').fetchone()[0]
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("INSERT INTO lifecycle_need_claims(revision_position_id,state,quantity,created_at) VALUES (?,'pending',1,'now')",(p,))

    def test_command_replay_and_payload_conflict(self):
        with self.store.transaction():
            t,r=self.draft()
            self.assertEqual({'id':r},self.store.record_command(t,1,'key','draft',{'a':1},{'id':r}))
            self.assertEqual({'id':r},self.store.record_command(t,1,'key','draft',{'a':1},{'id':99}))
        with self.assertRaises(ValueError):
            with self.store.transaction():self.store.record_command(t,1,'key','draft',{'a':2},{})
        self.assertEqual(1,self.db.execute('SELECT COUNT(*) FROM lifecycle_commands').fetchone()[0])

    def test_movement_unique_and_ownership(self):
        with self.store.transaction():t,r=self.draft()
        row=(t,1,'vfl','1','debit','physical-1',1,'inventory-key')
        self.db.execute('INSERT INTO lifecycle_movements VALUES (?,?,?,?,?,?,?,?)',row)
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute('INSERT INTO lifecycle_movements VALUES (?,?,?,?,?,?,?,?)',row)
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute('INSERT INTO lifecycle_movements VALUES (?,?,?,?,?,?,?,?)',(t,999,'vfl','1','debit','other',1,'other'))

    def test_concurrent_need_and_supply_admission(self):
        self.target(1)
        barrier=threading.Barrier(2);results=[]
        def attempt():
            db=self.connect();store=LifecycleFoundation(db)
            try:
                barrier.wait()
                with store.transaction():
                    t,r=self.draft(store);store.bind_pending_quantities(r)
                results.append('ok')
            except ValueError:results.append('unavailable')
            finally:db.close()
        threads=[threading.Thread(target=attempt) for _ in range(2)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertEqual(['ok','unavailable'],sorted(results))
        self.assertEqual(1,self.db.execute('SELECT COUNT(*) FROM trade_reservations').fetchone()[0])
        self.assertEqual([],self.db.execute('PRAGMA foreign_key_check').fetchall())

    def test_unit_of_work_required(self):
        with self.assertRaises(ValueError):self.store.create_identity(1,2)
        self.db.execute('BEGIN')
        with self.assertRaises(ValueError):
            with self.store.transaction():pass

    def test_legacy_accept_respects_new_shared_hold(self):
        from services.trade_reservations import TradeReservationService, TradeAcceptanceCode
        with self.store.transaction():
            t,r=self.draft();self.store.bind_pending_quantities(r)
        req=self.db.execute("INSERT INTO trade_requests(album_id,from_user_id,to_user_id,give_codes,get_codes,status) VALUES ('vfl',1,2,'[\"1\",\"1\"]','[\"2\"]','open')").lastrowid
        self.db.commit()
        result=TradeReservationService(self.db).accept(req,2)
        self.assertEqual(TradeAcceptanceCode.INSUFFICIENT_AVAILABLE,result.code)
        self.assertEqual(1,self.db.execute("SELECT SUM(quantity) FROM trade_reservations WHERE state='active'").fetchone()[0])

    def test_legacy_incoming_is_counted_without_backfill(self):
        from services.trade_reservations import TradeReservationService, TradeAcceptanceCode
        self.target(2)
        req=self.db.execute("INSERT INTO trade_requests(album_id,from_user_id,to_user_id,give_codes,get_codes,status) VALUES ('vfl',1,2,'[\"1\"]','[\"2\"]','open')").lastrowid
        self.db.commit()
        self.assertEqual(TradeAcceptanceCode.ACCEPTED,TradeReservationService(self.db).accept(req,2).code)
        a=TradeV2Domain(self.db).lifecycle_availability(1,'vfl','2')
        self.assertEqual((1,0,1),(a.committed,a.pending,a.free_need))
        self.assertEqual(0,self.db.execute('SELECT COUNT(*) FROM lifecycle_need_claims').fetchone()[0])
        with self.store.transaction():t,r=self.draft();self.store.bind_pending_quantities(r)
        self.assertEqual(0,TradeV2Domain(self.db).lifecycle_availability(1,'vfl','2').free_need)

    def test_release_only_owns_its_revision(self):
        self.target(2)
        with self.store.transaction():
            t,r=self.draft();self.store.bind_pending_quantities(r)
            t2,r2=self.draft();self.store.bind_pending_quantities(r2)
            self.store.release_pending_quantities(r)
        self.assertEqual(1,TradeV2Domain(self.db).lifecycle_availability(1,'vfl','2').pending)
        self.assertEqual(1,self.db.execute("SELECT SUM(quantity) FROM trade_reservations WHERE state='active'").fetchone()[0])

    def test_hold_mutation_and_double_binding_rejected(self):
        with self.store.transaction():t,r=self.draft();self.store.bind_pending_quantities(r)
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute('UPDATE trade_reservations SET quantity=2')
        self.db.rollback()
        with self.assertRaises((ValueError,sqlite3.IntegrityError)):
            with self.store.transaction():self.store.bind_pending_quantities(r)
        self.assertEqual(1,self.db.execute('SELECT COUNT(*) FROM trade_reservations').fetchone()[0])

    def test_foreign_revision_author_and_incomplete_revision_rejected(self):
        with self.store.transaction():t=self.store.create_identity(1,2)
        with self.assertRaises(sqlite3.IntegrityError):
            with self.store.transaction():self.store.append_revision(t,3,self.positions)
        with self.assertRaises(sqlite3.IntegrityError):
            with self.store.transaction():self.store.append_revision(t,1,self.positions[:1])
        self.assertEqual(0,self.db.execute('SELECT COUNT(*) FROM lifecycle_revisions').fetchone()[0])

    def test_migration_error_rolls_back_all_ddl(self):
        import shutil
        rollback(self.db,22)
        directory=Path(self.tmp.name)/'migrations';directory.mkdir()
        for p in (ROOT/'App/Database/migrations').iterdir():
            if p.suffix=='.sql':shutil.copy2(p,directory/p.name)
        up=directory/'0023_trade_lifecycle_foundation.up.sql'
        up.write_text(up.read_text()+'\nINSERT INTO deliberately_missing_table VALUES (1);\n')
        with self.assertRaises(sqlite3.OperationalError):migrate(self.db,23,directory)
        self.assertEqual(22,current_version(self.db))
        self.assertFalse(self.db.execute("SELECT 1 FROM sqlite_master WHERE name='lifecycle_contracts'").fetchone())

    def test_replace_cannot_overwrite_immutable_history(self):
        with self.store.transaction():
            t,r=self.draft()
            self.store.store_rule_snapshot(r,self.rules(),'original-time')
            self.store.record_command(t,1,'key','draft',{}, {'revision':r})
        statements=[
            ("INSERT OR REPLACE INTO lifecycle_contracts(trade_id,origin,created_at) VALUES (?,'SMARTDEAL','changed')",(t,)),
            ("INSERT OR REPLACE INTO lifecycle_revisions(id,trade_id,number,author_user_id,kind,created_at) VALUES (?,?,2,1,'counter','changed')",(r,t)),
            ("INSERT OR REPLACE INTO lifecycle_rule_snapshots VALUES (?,1,'{}','changed')",(r,)),
            ("INSERT OR REPLACE INTO lifecycle_commands VALUES (?,1,'key','other',?,'{}','changed')",(t,'a'*64)),
        ]
        for sql,args in statements:
            with self.assertRaises(sqlite3.IntegrityError):self.db.execute(sql,args)
        self.assertEqual('original-time',self.db.execute('SELECT accepted_at FROM lifecycle_rule_snapshots').fetchone()[0])

    def test_counter_snapshot_uses_counter_authors_perspective(self):
        with self.store.transaction():
            t,r=self.draft()
            counter=self.store.append_revision(t,2,self.positions,'counter')
            rules=RuleSnapshot(2,1,'MANUAL',False,self.rules().albums)
            self.store.store_rule_snapshot(counter,rules,'now')
        saved=self.db.execute('SELECT payload_json FROM lifecycle_rule_snapshots WHERE revision_id=?',(counter,)).fetchone()[0]
        self.assertEqual(2,RuleSnapshot.loads(saved).proposer)

    def test_released_projection_rebind_preserves_revision_history(self):
        self.target(2)
        with self.store.transaction():
            t,r=self.draft();self.store.bind_pending_quantities(r)
            self.store.release_pending_quantities(r)
            later=self.store.append_revision(t,1,self.positions,'reduction')
            self.store.bind_pending_quantities(later)
            # A stale release of the first revision must not touch the new head.
            self.store.release_pending_quantities(r)
        self.assertEqual(1,self.db.execute("SELECT COUNT(*) FROM trade_reservations WHERE state='active'").fetchone()[0])
        self.assertEqual([0,1],[r[0] for r in self.db.execute('SELECT is_current FROM lifecycle_supply_bindings ORDER BY revision_position_id')])
        self.assertEqual(4,self.db.execute('SELECT COUNT(*) FROM lifecycle_revision_positions').fetchone()[0])
        self.assertEqual((1,1),tuple(self.db.execute("SELECT SUM(state='pending'),SUM(state='released') FROM lifecycle_need_claims").fetchone()))

    def test_parallel_last_physical_copy_with_two_free_needs(self):
        self.target(2)
        self.db.execute("UPDATE stickers SET quantity=2,duplicates=1 WHERE user_id=1 AND sticker_code='1'")
        self.db.commit()
        barrier=threading.Barrier(2);results=[]
        def attempt():
            db=self.connect();store=LifecycleFoundation(db)
            try:
                barrier.wait()
                with store.transaction():
                    t,r=self.draft(store);store.bind_pending_quantities(r)
                results.append('ok')
            except ValueError:results.append('unavailable')
            finally:db.close()
        threads=[threading.Thread(target=attempt) for _ in range(2)]
        for thread in threads:thread.start()
        for thread in threads:thread.join()
        self.assertEqual(['ok','unavailable'],sorted(results))
        self.assertEqual(1,TradeV2Domain(self.db).lifecycle_availability(1,'vfl','2').free_need)


if __name__=='__main__':unittest.main()
