"""Real canonical matching on synthetic V20/V21 data; no private database input."""
from pathlib import Path
from contextlib import closing
import hashlib
import os
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'App'))
from App.Database.migration_runner import migrate
from trade_shell import read_connection, discovery


def fixture(path, partners=3):
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript((ROOT / 'App/Database/base_schema.sql').read_text())
        db.executescript((ROOT / 'App/Database/catalog_seed.sql').read_text())
        migrate(db, 20)
        for user in range(1, partners + 2):
            db.execute("INSERT INTO users(id,username,password,name) VALUES (?,?,?,?)",
                       (user, f'synthetic_{user}', 'synthetic-unused', f'Synthetic {user}'))
            db.execute("INSERT INTO user_albums(user_id,album_id,trade_pool_enabled) VALUES (?,'vfl',1)", (user,))
        for index in range(partners):
            for offset in range(5):
                give = str(1 + index * 10 + offset)
                receive = str(6 + index * 10 + offset)
                for user, code in [(1, give), (index + 2, receive)]:
                    db.execute("INSERT INTO stickers(user_id,album_id,sticker_code,quantity,duplicates) VALUES (?,'vfl',?,2,1)", (user, code))
        db.commit()


class Integration01Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bootstrap = tempfile.TemporaryDirectory(prefix='integration01-bootstrap-', dir='/private/tmp')
        cls.bootstrap_db = Path(cls.bootstrap.name) / 'synthetic.db'
        fixture(cls.bootstrap_db)
        cls.old_environment = dict(os.environ)
        os.environ.update(SAMMLR_ENV='testing', SAMMLR_SECRET_KEY='sammlr-explicit-testing-secret',
                          DATABASE_PATH=str(cls.bootstrap_db))
        import webapp
        cls.webapp = webapp
        cls.old_db = webapp.DB
        cls.old_testing = webapp.app.testing
        webapp.app.testing = True

    @classmethod
    def tearDownClass(cls):
        cls.webapp.DB = cls.old_db
        cls.webapp.app.testing = cls.old_testing
        os.environ.clear()
        os.environ.update(cls.old_environment)
        cls.bootstrap.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='integration01-', dir='/private/tmp')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'synthetic.db'
        fixture(self.path)
        self.webapp.DB = str(self.path)
        self.client = self.webapp.app.test_client()
        with self.client.session_transaction() as session:
            session['user_id'] = 1
            session['auth_version'] = 1

    def test_zero_one_two_three_real_proposals(self):
        for count in range(4):
            path = Path(self.temp.name) / f'count-{count}.db'
            fixture(path, count)
            self.webapp.DB = str(path)
            response = self.client.get('/tauschen')
            self.assertEqual(200, response.status_code)
            self.assertEqual(count, response.text.count('class="trade-proposal"'))
            self.assertNotIn('Fatima', response.text)

    def test_v20_projection_equals_v21_legacy_reader(self):
        # Compare real bindings/reservations, not only an empty legacy schema.
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT INTO trade_requests(id,album_id,from_user_id,to_user_id,status) VALUES (100,'vfl',1,2,'accepted')")
            db.execute("INSERT INTO trades(id,legacy_trade_request_id,requester_user_id,partner_user_id,lifecycle_state) VALUES (100,100,1,2,'accepted')")
            for position, giver, receiver, code in [(100, 1, 2, '1'), (101, 2, 1, '6')]:
                db.execute("INSERT INTO trade_positions(id,trade_id,from_user_id,to_user_id,album_id,sticker_code,quantity) VALUES (?,100,?,?,'vfl',?,1)", (position, giver, receiver, code))
                db.execute("INSERT INTO trade_reservations(trade_id,trade_position_id,user_id,album_id,sticker_code,quantity) VALUES (100,?,?,'vfl',?,1)", (position, giver, code))
        with read_connection(self.path) as db:
            before = discovery(db, 1)[:3]
        with closing(sqlite3.connect(self.path)) as db, db:
            migrate(db, 21)
        with read_connection(self.path) as db:
            after = discovery(db, 1)[:3]
        self.assertEqual(before, after)

    def test_all_routes_read_only_and_query_cannot_change_actor(self):
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        routes = ['/tauschen', '/tauschen/sammlr', '/tauschen/sammlr/2',
                  '/tauschen/vorschlag/2', '/tauschen/sammlr/2/smartdeal', '/tauschen/laufend']
        with patch('services.smartdeal_runtime.cleanup', side_effect=AssertionError('cleanup forbidden')):
            for route in routes:
                response = self.client.get(route)
                self.assertEqual(200, response.status_code, route)
                controlled = self.client.get(route + '?user=2&role=recipient&demo=1&scenario=shipped')
                self.assertEqual(response.data, controlled.data)
                self.assertIn(self.client.post(route).status_code, (403, 405))
                self.assertNotIn('sessionStorage', response.text)
        self.assertEqual(before, hashlib.sha256(self.path.read_bytes()).hexdigest())
        with read_connection(self.path) as db:
            for statement in ["DELETE FROM trade_requests", "INSERT INTO trade_requests(status) VALUES ('open')",
                              "UPDATE trade_requests SET status='accepted'", "CREATE TABLE forbidden(id)"]:
                with self.assertRaises(sqlite3.DatabaseError):
                    db.execute(statement)

    def test_auth_and_partner_eligibility(self):
        with self.client.session_transaction() as s:
            s.clear()
        self.assertEqual('/login', self.client.get('/tauschen?user=1').location)
        with self.client.session_transaction() as s:
            s['user_id'] = 1
            s['auth_version'] = 1
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('INSERT INTO blocks(blocker_user_id,blocked_user_id) VALUES (1,2)')
        self.assertEqual(404, self.client.get('/tauschen/sammlr/2').status_code)
        self.assertEqual(404, self.client.get('/tauschen/vorschlag/2').status_code)
        self.assertNotIn('synthetic_2', self.client.get('/tauschen/sammlr').text)

    def test_trade_pool_and_private_inventory_not_exposed(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('UPDATE user_albums SET trade_pool_enabled=0 WHERE user_id=2')
        self.assertEqual(404, self.client.get('/tauschen/sammlr/2').status_code)
        self.assertEqual(404, self.client.get('/tauschen/sammlr/1').status_code)
        self.assertEqual(404, self.client.get('/tauschen/sammlr/999').status_code)
        self.assertNotIn('synthetic_2', self.client.get('/tauschen/sammlr').text)

    def test_active_projection_only_own_existing_requests(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT INTO trade_requests(id,album_id,from_user_id,to_user_id,status) VALUES (100,'vfl',1,2,'open')")
            db.execute("INSERT INTO trade_requests(id,album_id,from_user_id,to_user_id,status) VALUES (101,'vfl',3,4,'accepted')")
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        html = self.client.get('/tauschen/laufend').text
        self.assertIn('Nr. 100', html)
        self.assertNotIn('Nr. 101', html)
        self.assertEqual(before, hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_wall_default_unchanged_and_trade_cap_ten(self):
        for quantity in (1, 2, 5, 6, 10, 15, 37):
            args = ('vfl', '1', {'1': {'quantity': quantity}}, None, 'owned', '')
            wall = self.webapp.sticker_wall_slot_html(*args, can_edit_inventory=False)
            trade = self.webapp.sticker_wall_slot_html(*args, can_edit_inventory=False, max_visible_layers=10)
            self.assertEqual(min(quantity, 5)-1, wall.count('data-stack-layer='))
            self.assertEqual(min(quantity, 10)-1, trade.count('data-stack-layer='))
        self.assertIn('href="/tauschen"', self.webapp.bottom_nav('tauschen'))
