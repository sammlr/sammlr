"""Real signed HTML commands, explicit summary, ownership and CSRF."""
import re
import sqlite3
import unittest
from contextlib import closing
from tests import test_lifecycle06_ui as fixtures
from App.Database.migration_runner import migrate


class ReceiptUITests(unittest.TestCase):
    setUpClass=classmethod(fixtures.ShippingUITests.setUpClass.__func__)
    tearDownClass=classmethod(fixtures.ShippingUITests.tearDownClass.__func__)
    for _name in ('login','token','send','command','form','post','upload','both','book_form','create','selection','confirm','release'):
        locals()[_name]=getattr(fixtures.ShippingUITests,_name)

    def setUp(self):
        fixtures.ShippingUITests.setUp(self)
        with closing(sqlite3.connect(self.path)) as db:migrate(db,29)
        self.receipt_url=self.url.replace('/vorbereitung/','/empfang/')
        self.login(2)

    def receipt_form(self, html=None, suffix='review'):
        html=html or self.client.get(self.receipt_url).text
        body=re.search('<form method="post" action="'+re.escape(self.receipt_url+'/'+suffix)+'">(.*?)</form>',html,re.S)
        self.assertIsNotNone(body,html)
        return dict(re.findall('name="([^"]+)" value="([^"]*)"',body.group(1)))

    def test_complete_confirmation_retry_and_systemic_source(self):
        self.login(1);self.release();self.login(2)
        response=self.client.get(self.receipt_url)
        self.assertEqual('private, no-store',response.headers['Cache-Control'])
        data=self.receipt_form(response.text)
        self.assertEqual(400,self.client.post(self.receipt_url+'/confirm',data=data).status_code)
        review=self.client.post(self.receipt_url+'/review',data=data|{'mode':'complete'})
        self.assertEqual(200,review.status_code);self.assertIn('Gutschrift: 1',review.text)
        signed=self.receipt_form(review.text,'confirm')
        with closing(sqlite3.connect(self.path)) as db:self.assertEqual(0,db.execute('SELECT COUNT(*) FROM lifecycle_receipts').fetchone()[0])
        for _ in range(2):self.assertEqual(303,self.client.post(self.receipt_url+'/confirm',data=signed).status_code)
        self.assertIn('received_complete',self.client.get(self.receipt_url).text)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(1,db.execute('SELECT COUNT(*) FROM lifecycle_receipts').fetchone()[0])
            self.assertEqual(('RECEIPT_EVIDENCE',None),db.execute('SELECT source,sender_confirmed_at FROM lifecycle_shipping').fetchone())

    def test_structured_summary_missing_and_sender_response(self):
        self.login(1);self.release();self.login(2)
        data=self.receipt_form();form=self.client.post(self.receipt_url+'/review',data=data|{'mode':'problem'})
        self.assertEqual(200,form.status_code);data=self.receipt_form(form.text)
        for k in data:
            if k.startswith('missing_'):data[k]='1'
        review=self.client.post(self.receipt_url+'/review',data=data)
        self.assertEqual(200,review.status_code);self.assertIn('Gutschrift: 0',review.text)
        self.assertEqual(303,self.client.post(self.receipt_url+'/confirm',data=self.receipt_form(review.text,'confirm')).status_code)
        self.login(1);data=self.receipt_form(suffix='response')|{'response':'acknowledge'}
        self.assertEqual(303,self.client.post(self.receipt_url+'/response',data=data).status_code)
        self.assertIn('Problem anerkannt',self.client.get(self.receipt_url).text)
        self.assertEqual(409,self.client.post(self.receipt_url+'/response',data=data|{'response':'sent_correctly'}).status_code)

    def test_invalid_partition_extra_position_and_tampered_token(self):
        self.login(1);self.release();self.login(2)
        original=self.receipt_form()
        self.assertEqual(400,self.client.post(self.receipt_url+'/review',data=original|{'token':'tampered','mode':'complete'}).status_code)
        form=self.client.post(self.receipt_url+'/review',data=original|{'mode':'problem'});data=self.receipt_form(form.text)
        for changes in ({},{'correct_999':'1'}):
            self.assertEqual(409,self.client.post(self.receipt_url+'/review',data=data|changes).status_code)
        with closing(sqlite3.connect(self.path)) as db:self.assertEqual(0,db.execute('SELECT COUNT(*) FROM lifecycle_receipts').fetchone()[0])

    def test_csrf_foreign_actor_and_trade_id(self):
        self.login(1);self.release();self.login(2)
        data=self.receipt_form()|{'mode':'complete'}
        no_csrf={k:v for k,v in data.items() if k!='_csrf_token'}
        self.assertEqual(403,self.client.post(self.receipt_url+'/review',data=no_csrf,csrf_protect=False).status_code)
        self.assertEqual(400,self.client.post('/tauschen/empfang/999/review',data=data).status_code)
        self.login(3);self.assertEqual(404,self.client.get(self.receipt_url).status_code)
        self.assertEqual(403,self.client.post(self.receipt_url+'/review',data=data).status_code)
        self.login(1);self.assertEqual(403,self.client.post(self.receipt_url+'/review',data=data).status_code)

    def test_stale_signed_revision_rejected(self):
        self.login(1);self.release();self.login(2)
        from lifecycle_request_routes import serializer
        data=self.receipt_form()
        with self.webapp.app.test_request_context():
            payload=serializer().loads(data['token']);payload['revision']=999;data['token']=serializer().dumps(payload)
        self.assertEqual(409,self.client.post(self.receipt_url+'/review',data=data|{'mode':'complete'}).status_code)

    def test_nonarrival_not_available_before_seven_days_and_direct_post_rejected(self):
        self.login(1);self.release();self.login(2)
        self.assertNotIn('Brief nicht angekommen',self.client.get(self.receipt_url).text)
        from lifecycle_request_routes import serializer
        data=self.receipt_form()
        with self.webapp.app.test_request_context():
            payload=serializer().loads(data['token']);payload['operation']='non_arrival';data['token']=serializer().dumps(payload)
        self.assertEqual(409,self.client.post(self.receipt_url+'/non-arrival',data=data).status_code)

    def test_unmigrated_database_not_migrated_on_access(self):
        self.login(1);self.release();self.login(2)
        import hashlib
        from tests.test_integration01_trade_shell import fixture
        path=self.path.parent/'unmigrated-receipt.db';fixture(path);self.webapp.DB=str(path)
        before=hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(503,self.client.get(self.receipt_url).status_code)
        self.assertEqual(before,hashlib.sha256(path.read_bytes()).hexdigest())

    def test_browser_injected_transport_fields_keep_receipt_identity_signed(self):
        self.login(1);self.release();self.login(2)
        from werkzeug.datastructures import MultiDict
        form=self.client.post(self.receipt_url+'/review',data=self.receipt_form()|{'mode':'problem'})
        data=self.receipt_form(form.text)
        for k in data:
            if k.startswith('correct_'):data[k]='1'
        browser=MultiDict(data);browser.add('_csrf_token',data['_csrf_token']);browser.add('_history_mutation_id','browser-transport-only')
        self.assertEqual(200,self.client.post(self.receipt_url+'/review',data=browser).status_code)
        browser.add(next(k for k in data if k.startswith('correct_')),'1')
        self.assertEqual(409,self.client.post(self.receipt_url+'/review',data=browser).status_code)

    def test_signed_direct_confirm_before_release_rejected_then_same_command_succeeds(self):
        from lifecycle_request_routes import serializer
        html = self.client.get(self.receipt_url).text
        self.assertNotIn('name="mode" value="complete"', html)
        self.assertIn('Empfang ist nach beidseitiger Vorbereitung', html)
        with closing(sqlite3.connect(self.path)) as db:
            trade = int(self.receipt_url.rsplit('/', 1)[1])
            revision = db.execute('SELECT accepted_revision_id FROM lifecycle_contracts WHERE trade_id=?', (trade,)).fetchone()[0]
            before = list(db.iterdump())
        with self.webapp.app.test_request_context():
            signed = serializer().dumps(dict(actor=2, trade=trade, revision=revision,
                sender=1, operation='receipt_confirm', key='early-signed', inspection=None))
        # A valid actor-bound signature must not bypass the command guard.
        data = {'token':signed}
        self.assertEqual(409, self.client.post(self.receipt_url+'/confirm', data=data).status_code)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(before, list(db.iterdump()))
        self.login(1);self.release();self.login(2)
        self.assertEqual(303, self.client.post(self.receipt_url+'/confirm', data=data).status_code)
