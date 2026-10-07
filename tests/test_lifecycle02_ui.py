"""Productive Flask routes and CSRF against synthetic migrated databases only."""
import re,json,sqlite3
from contextlib import closing
import unittest
from tests import test_integration01_trade_shell as integration
from App.Database.migration_runner import migrate


class RequestUITests(unittest.TestCase):
    setUpClass=classmethod(integration.Integration01Tests.setUpClass.__func__)
    tearDownClass=classmethod(integration.Integration01Tests.tearDownClass.__func__)
    def setUp(self):
        integration.Integration01Tests.setUp(self)
        with closing(sqlite3.connect(self.path)) as db:migrate(db,24)

    def login(self,user):
        with self.client.session_transaction() as session:
            session['user_id']=user;session['auth_version']=1

    def token(self):
        r=self.client.get('/tauschen/sammlr/2/smartdeal');self.assertEqual(200,r.status_code)
        return re.search('name="token" value="([^"]+)"',r.text).group(1)

    def test_smart_send_sender_recipient_and_reject(self):
        token=self.token()
        r=self.client.post('/tauschen/anfragen',data={'token':token})
        self.assertEqual(303,r.status_code);url=r.location
        self.assertIn('Anfrage offen',self.client.get(url).text)
        self.assertIn('72 Stunden',self.client.get(url).text)
        self.assertIn('Anfrage zurückziehen',self.client.get(url).text)
        self.assertEqual(url,self.client.post('/tauschen/anfragen',data={'token':token}).location)
        self.login(2);html=self.client.get('/tauschen/laufend').text
        self.assertIn('Anfrage von synthetic_1',html);self.assertIn('Anfrage ablehnen',html)
        self.assertNotIn('Annehmen',html)
        self.assertEqual(404,self.client.post(url+'/accepted').status_code)
        self.assertEqual(403,self.client.post(url+'/withdrawn').status_code)
        self.assertEqual(303,self.client.post(url+'/rejected').status_code)
        self.assertIn('Anfrage abgelehnt',self.client.get(url).text)
        self.login(1);self.assertEqual(200,self.client.get('/tauschen/sammlr/2/smartdeal').status_code)

    def test_manual_review_send_withdraw(self):
        r=self.client.get('/tauschen/sammlr/2/manual')
        data=json.loads(re.search(r'id="trade-data">(.*?)</script>',r.text,re.S).group(1))
        r=self.client.post(data['validation_url'],json=dict(give=['vfl::1'],receive=['vfl::6'],fingerprint=data['fingerprint']))
        self.assertTrue(r.json['ok']);review=self.client.get(r.json['review_url'])
        self.assertIn('Dein Deal mit synthetic_2',review.text)
        token=re.search('name="token" value="([^"]+)"',review.text).group(1)
        r=self.client.post('/tauschen/anfragen',data={'token':token});url=r.location
        self.assertEqual(303,r.status_code)
        self.client.post(url+'/withdrawn');self.assertIn('Anfrage zurückgezogen',self.client.get(url).text)

    def test_csrf_tamper_foreign_user_and_stale_deal(self):
        token=self.token()
        self.assertEqual(403,self.client.post('/tauschen/anfragen',data={'token':token},csrf_protect=False).status_code)
        self.assertEqual(400,self.client.post('/tauschen/anfragen',data={'token':token+'tamper'}).status_code)
        self.login(3);self.assertEqual(403,self.client.post('/tauschen/anfragen',data={'token':token}).status_code)
        self.login(1)
        with closing(sqlite3.connect(self.path)) as db,db:db.execute('UPDATE user_albums SET trade_pool_enabled=0 WHERE user_id=2')
        self.assertEqual(409,self.client.post('/tauschen/anfragen',data={'token':token}).status_code)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(0,db.execute('SELECT COUNT(*) FROM lifecycle_requests').fetchone()[0])

    def test_manual_multiple_copies_are_aggregated(self):
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute("UPDATE stickers SET quantity=3,duplicates=2 WHERE (user_id=1 AND sticker_code='1') OR (user_id=2 AND sticker_code='6')")
            db.execute("INSERT INTO lifecycle_need_targets VALUES (1,'vfl','6',2)")
            db.execute("INSERT INTO lifecycle_need_targets VALUES (2,'vfl','1',2)")
        r=self.client.get('/tauschen/sammlr/2/manual')
        data=json.loads(re.search(r'id="trade-data">(.*?)</script>',r.text,re.S).group(1))
        r=self.client.post(data['validation_url'],json=dict(give=['vfl::1','vfl::1::2'],receive=['vfl::6','vfl::6::2'],fingerprint=data['fingerprint']))
        self.assertTrue(r.json['ok']);review=self.client.get(r.json['review_url'])
        self.assertIn('× 2',review.text)
        token=re.search('name="token" value="([^"]+)"',review.text).group(1)
        self.assertEqual(303,self.client.post('/tauschen/anfragen',data={'token':token}).status_code)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual([(2,),(2,)],db.execute('SELECT quantity FROM lifecycle_revision_positions').fetchall())

    def test_unmigrated_gate_no_creation(self):
        path=self.path.parent/'v20.db';integration.fixture(path)
        self.webapp.DB=str(path)
        import hashlib
        before=hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertNotIn('name="token"',self.client.get('/tauschen/sammlr/2/smartdeal').text)
        self.assertEqual(503,self.client.get('/tauschen/anfragen/1').status_code)
        self.assertEqual(before,hashlib.sha256(path.read_bytes()).hexdigest())

if __name__=='__main__':unittest.main()
