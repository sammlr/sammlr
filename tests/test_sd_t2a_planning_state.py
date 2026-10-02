"""Global planning contracts on synthetic V21 databases; no V1 writer."""
from contextlib import closing
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'App'))
from App.Database.migration_runner import migrate
from services.smartdeal_planning import SmartDealPlanningService
from services.inventory import InventoryReadService

NOW = datetime(2026, 9, 10, 12, tzinfo=timezone.utc)
CATALOG = {'vfl': ('3', '2', '1'), 'em24': ('3', '2', '1')}


class PlanningStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='sdt2a-')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'state.db'
        self.db = sqlite3.connect(self.path)
        self.addCleanup(self.db.close)
        self.db.row_factory = sqlite3.Row
        self.db.executescript((ROOT / 'App/Database/sammlr_reference_s00.sql').read_text())
        migrate(self.db, 21)
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('DELETE FROM stickers')
        self.db.execute("DELETE FROM user_albums WHERE album_id='wm26'")
        for user in (1, 2):
            self.db.execute("INSERT OR IGNORE INTO user_albums(user_id,album_id) VALUES (?, 'em24')", (user,))
        self.db.execute('UPDATE user_albums SET trade_pool_enabled=1')
        self.quantity(1, 'vfl', '1', 5)
        self.quantity(2, 'vfl', '2', 3)
        self.db.commit()

    def quantity(self, user, album, code, quantity):
        self.db.execute('DELETE FROM stickers WHERE user_id=? AND album_id=? AND sticker_code=?', (user, album, code))
        self.db.execute('INSERT INTO stickers(user_id,album_id,sticker_code,quantity,duplicates) VALUES (?,?,?,?,?)', (user, album, code, quantity, max(quantity-1,0)))

    def build(self):
        return SmartDealPlanningService(self.db, lambda a: CATALOG[a], lambda: NOW).build(1)

    def pieces(self, values):
        return {(p.album_id, p.sticker_code): p.quantity for p in values}

    def bind(self, kind='legacy', status='accepted', created='2026-09-10 10:00:00'):
        request = self.db.execute('''INSERT INTO trade_requests
            (album_id,from_user_id,to_user_id,give_codes,get_codes,status,created_at,contract_type,binding_created_at)
            VALUES ('vfl',1,2,'["1"]','["2"]',?,?,?,?)''',
            (status, created, kind, created if kind == 'smartdeal_v1' else None)).lastrowid
        trade = self.db.execute('''INSERT INTO trades
            (legacy_trade_request_id,requester_user_id,partner_user_id,lifecycle_state)
            VALUES (?,1,2,?)''', (request, status)).lastrowid
        for giver, receiver, code in ((1, 2, '1'), (2, 1, '2')):
            position = self.db.execute('''INSERT INTO trade_positions
                (trade_id,from_user_id,to_user_id,album_id,sticker_code,quantity)
                VALUES (?,?,?,'vfl',?,1)''', (trade, giver, receiver, code)).lastrowid
            self.db.execute('''INSERT INTO trade_reservations
                (trade_id,trade_position_id,user_id,album_id,sticker_code,quantity)
                VALUES (?,?,?,'vfl',?,1)''', (trade, position, giver, code))
        self.db.execute('INSERT INTO trade_shipping_status(trade_id) VALUES (?)', (trade,))
        self.db.execute('INSERT INTO trade_receipt_status(trade_id) VALUES (?)', (trade,))
        return request, trade

    def test_global_multiple_albums_and_stable_membership_identity(self):
        state = self.build()
        self.assertEqual(('em24','vfl'), tuple(a.album_id for a in state.album_context))
        self.assertIn(('em24','1'), self.pieces(state.needs))
        self.assertIn(('vfl','2'), self.pieces(state.needs))
        memberships = {r['album_id']:r['id'] for r in self.db.execute('SELECT id,album_id FROM user_albums WHERE user_id=1')}
        for piece in state.needs + state.outgoing_supply:
            self.assertEqual(memberships[piece.album_id], piece.user_album_id)
        self.assertEqual(4, self.pieces(state.outgoing_supply)[('vfl','1')])

    def test_last_copy_never_supply(self):
        self.quantity(1,'vfl','1',1)
        self.assertNotIn(('vfl','1'), self.pieces(self.build().outgoing_supply))

    def test_two_reservations_leave_two_of_five(self):
        self.bind();self.bind()
        state = self.build()
        self.assertEqual(2,self.pieces(state.outgoing_supply)[('vfl','1')])
        self.assertEqual(2,sum(b.reserved_quantity for b in state.reservation_context if b.direction=='outgoing'))
        canonical = InventoryReadService(self.db).snapshot(1,'vfl',CATALOG['vfl'])
        self.assertEqual(canonical.stickers_by_code['1'].available,2)

    def test_undercoverage_never_negative_or_free(self):
        self.bind();self.bind();self.quantity(1,'vfl','1',1)
        self.assertNotIn(('vfl','1'), self.pieces(self.build().outgoing_supply))

    def test_accepted_incoming_is_not_free_need(self):
        self.bind()
        state = self.build()
        self.assertIn(('vfl','2'),self.pieces(state.missing))
        self.assertNotIn(('vfl','2'),self.pieces(state.needs))
        self.assertEqual(1,self.pieces(state.incoming_committed_needs)[('vfl','2')])

    def test_explicit_open_v1_binding_commits_need(self):
        self.bind('smartdeal_v1','open')
        state=self.build()
        self.assertNotIn(('vfl','2'),self.pieces(state.needs))
        self.assertTrue(all(b.contract_type=='smartdeal_v1' and b.valid for b in state.reservation_context))

    def test_exact_24h_expiry_releases_projection_without_writes(self):
        self.bind('smartdeal_v1','open','2026-09-09 12:00:00');self.db.commit()
        before=self.db.total_changes
        state=self.build()
        self.assertIn(('vfl','2'),self.pieces(state.needs))
        self.assertEqual(4,self.pieces(state.outgoing_supply)[('vfl','1')])
        self.assertTrue(all(not b.valid for b in state.reservation_context))
        self.assertEqual(before,self.db.total_changes)
        self.assertEqual(2,self.db.execute("SELECT COUNT(*) FROM trade_reservations WHERE state='active'").fetchone()[0])

    def test_terminal_v1_need_is_free(self):
        request,trade=self.bind('smartdeal_v1','open')
        for status in ('declined','cancelled','expired','obsolete','completed'):
            with self.subTest(status=status):
                self.db.execute('UPDATE trade_requests SET status=? WHERE id=?',(status,request))
                self.db.execute('UPDATE trades SET lifecycle_state=? WHERE id=?',(status,trade))
                self.assertIn(('vfl','2'),self.pieces(self.build().needs))

    def test_legacy_open_smart_has_no_fictional_binding_or_24h_rule(self):
        self.db.execute('''INSERT INTO trade_requests(album_id,from_user_id,to_user_id,give_codes,get_codes,from_confirmed,created_at)
            VALUES ('vfl',1,2,'["1"]','["2"]',-22,'2026-09-09 00:00:00')''')
        state=self.build()
        self.assertIn(('vfl','2'),self.pieces(state.needs))
        self.assertEqual((),state.reservation_context)
        self.assertEqual(4,self.pieces(state.outgoing_supply)[('vfl','1')])

    def test_old_accepted_legacy_does_not_expire(self):
        self.bind(created='2020-01-01 00:00:00')
        self.assertNotIn(('vfl','2'),self.pieces(self.build().needs))

    def test_shipped_incoming_still_committed_without_supply_reservation(self):
        _,trade=self.bind()
        self.db.execute("UPDATE trades SET lifecycle_state='partially_shipped' WHERE id=?",(trade,))
        self.db.execute("UPDATE trade_shipping_status SET partner_shipped=1,partner_shipped_at='2026-09-10 11:00:00' WHERE trade_id=?",(trade,))
        self.db.execute("UPDATE trade_reservations SET state='released',released_at='2026-09-10 11:00:00',release_reason='shipped' WHERE trade_id=? AND user_id=2",(trade,))
        state=self.build()
        self.assertIn(('vfl','2'),self.pieces(state.incoming_committed_needs))
        self.assertNotIn(('vfl','2'),self.pieces(state.needs))
        self.assertNotIn(('vfl','2'),self.pieces(state.outgoing_supply))

    def test_received_piece_is_neither_missing_nor_committed_need(self):
        _,trade=self.bind()
        self.quantity(1,'vfl','2',1)
        self.db.execute("UPDATE trade_receipt_status SET requester_received=1,requester_received_at='2026-09-10 11:00:00' WHERE trade_id=?",(trade,))
        state=self.build()
        self.assertNotIn(('vfl','2'),self.pieces(state.missing))
        self.assertNotIn(('vfl','2'),self.pieces(state.incoming_committed_needs))

    def test_blocks_both_directions_remove_partner(self):
        for a,b in ((1,2),(2,1)):
            self.db.execute('DELETE FROM blocks')
            self.db.execute('INSERT INTO blocks(blocker_user_id,blocked_user_id) VALUES (?,?)',(a,b))
            self.assertNotIn(2,[p.user_id for p in self.build().eligible_partners])

    def test_private_without_trade_permission_is_absent(self):
        self.db.execute("UPDATE users SET profile_privacy='private' WHERE id=2")
        self.db.execute("UPDATE user_albums SET visibility='private',trade_pool_enabled=0 WHERE user_id=2")
        self.assertNotIn(2,[p.user_id for p in self.build().eligible_partners])

    def test_private_with_explicit_pool_preserves_existing_trade_contract(self):
        self.db.execute("UPDATE users SET profile_privacy='private' WHERE id=2")
        self.db.execute("UPDATE user_albums SET visibility='private' WHERE user_id=2")
        self.assertIn(2,[p.user_id for p in self.build().eligible_partners])

    def test_deactivated_and_self_excluded(self):
        self.db.execute("UPDATE users SET account_state='deactivated' WHERE id=2")
        self.assertNotIn(2,[p.user_id for p in self.build().eligible_partners])
        self.assertNotIn(1,[p.user_id for p in self.build().eligible_partners])

    def test_inactive_subject_fails_closed(self):
        self.db.execute("UPDATE users SET account_state='deactivated' WHERE id=1")
        with self.assertRaises(ValueError):self.build()

    def test_pool_off_album_excluded_from_every_piece_list(self):
        self.db.execute("UPDATE user_albums SET trade_pool_enabled=0 WHERE user_id=1 AND album_id='em24'")
        state=self.build()
        self.assertEqual(('vfl',),tuple(a.album_id for a in state.album_context))
        self.assertTrue(all(p.album_id=='vfl' for p in state.needs+state.outgoing_supply))

    def test_deterministic_immutable_and_no_ranking_fields(self):
        first=self.build();second=self.build()
        self.assertEqual(first,second)
        self.assertEqual(sorted(p.user_id for p in first.eligible_partners),[p.user_id for p in first.eligible_partners])
        with self.assertRaises(FrozenInstanceError):first.user_id=2
        self.assertFalse({'score','deals','rank','top5'} & {f.name for f in fields(first)})
        reversed_catalog=SmartDealPlanningService(self.db,lambda a: tuple(reversed(CATALOG[a])),lambda: NOW).build(1)
        self.assertEqual(first,reversed_catalog)

    def test_read_only_database_hash_and_no_new_rows(self):
        self.bind();self.db.commit()
        digest=hashlib.sha256(self.path.read_bytes()).hexdigest();changes=self.db.total_changes
        self.build()
        self.assertEqual(changes,self.db.total_changes)
        self.assertEqual(digest,hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertFalse(self.db.in_transaction)

    def test_caller_transaction_is_not_committed_or_rolled_back(self):
        self.quantity(1,'vfl','1',6)
        self.assertTrue(self.db.in_transaction)
        self.assertEqual(5,self.pieces(self.build().outgoing_supply)[('vfl','1')])
        self.assertTrue(self.db.in_transaction)
        self.db.rollback()
        self.assertEqual(4,self.pieces(self.build().outgoing_supply)[('vfl','1')])

    def test_incomplete_v1_binding_fails_closed(self):
        _,trade=self.bind('smartdeal_v1','open')
        self.db.execute('DELETE FROM trade_reservations WHERE trade_id=? AND user_id=2',(trade,))
        with self.assertRaises(ValueError):self.build()

    def test_query_count_does_not_scale_with_sticker_count(self):
        counts=[]
        for n in (3,10000):
            statements=[];self.db.set_trace_callback(statements.append)
            SmartDealPlanningService(self.db,lambda a:tuple(str(i) for i in range(n)),lambda:NOW).build(1)
            self.db.set_trace_callback(None)
            counts.append(len(statements))
        self.assertEqual(counts[0],counts[1]);self.assertLessEqual(counts[1],20)

    def test_one_snapshot_during_concurrent_writer(self):
        self.db.commit();self.db.execute('PRAGMA journal_mode=WAL')
        fired=[]
        def trace(sql):
            if sql.startswith('SELECT album_id,sticker_code,quantity') and not fired:
                fired.append(True)
                with closing(sqlite3.connect(self.path)) as writer:
                    writer.execute("UPDATE stickers SET quantity=9,duplicates=8 WHERE user_id=1 AND album_id='vfl' AND sticker_code='1'")
                    writer.commit()
        self.db.set_trace_callback(trace)
        state=self.build();self.db.set_trace_callback(None)
        self.assertTrue(fired)
        self.assertEqual(4,self.pieces(state.outgoing_supply)[('vfl','1')])
        self.assertEqual(8,self.pieces(self.build().outgoing_supply)[('vfl','1')])

    def test_mixed_legacy_and_expired_v1_do_not_release_legacy_supply(self):
        self.bind('legacy','accepted','2020-01-01 00:00:00')
        self.bind('smartdeal_v1','open','2026-09-09 12:00:00')
        state=self.build()
        self.assertEqual(3,self.pieces(state.outgoing_supply)[('vfl','1')])
        self.assertNotIn(('vfl','2'),self.pieces(state.needs))
        self.assertEqual({'legacy','smartdeal_v1'},{b.contract_type for b in state.reservation_context})

    def test_terminal_problem_releases_incoming_need(self):
        request,trade=self.bind()
        self.db.execute("UPDATE trade_requests SET status='completed' WHERE id=?",(request,))
        self.db.execute("UPDATE trades SET lifecycle_state='closed_with_problem' WHERE id=?",(trade,))
        self.db.execute("UPDATE trade_reservations SET state='released',released_at='2026-09-10 11:00:00',release_reason='closed_with_problem' WHERE trade_id=?",(trade,))
        state=self.build()
        self.assertIn(('vfl','2'),self.pieces(state.needs))
        self.assertEqual(4,self.pieces(state.outgoing_supply)[('vfl','1')])

    def test_unrecognized_inventory_code_is_not_a_catalog_need_or_supply(self):
        self.quantity(1,'vfl','99999',10)
        self.assertNotIn(('vfl','99999'),self.pieces(self.build().outgoing_supply))

    def test_real_catalog_adapter_has_global_canonical_codes(self):
        state=SmartDealPlanningService(self.db,now_provider=lambda:NOW).build(1)
        vfl=next(a for a in state.album_context if a.album_id=='vfl')
        self.assertEqual(250,len(vfl.catalog_codes))
        self.assertEqual(('1','10','100'),vfl.catalog_codes[:3])

    def test_partner_count_does_not_add_per_partner_queries(self):
        counts=[]
        for size in (0,100):
            for i in range(size):
                user=self.db.execute("INSERT INTO users(username,password,name) VALUES (?, 'fixture-only', 'Synthetic')",(f'synthetic_extra_{i}',)).lastrowid
                self.db.execute("INSERT INTO user_albums(user_id,album_id,trade_pool_enabled) VALUES (?, 'vfl',1)",(user,))
            self.db.commit()
            statements=[];self.db.set_trace_callback(statements.append)
            state=self.build();self.db.set_trace_callback(None)
            counts.append(len(statements))
        self.assertEqual(counts[0],counts[1])
        self.assertGreaterEqual(len(state.eligible_partners),100)
