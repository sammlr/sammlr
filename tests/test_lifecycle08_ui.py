"""Authenticated V1 completion and blind-rating routes on synthetic fixtures."""
import re
import sqlite3
import unittest
from contextlib import closing
from tests import test_lifecycle07_ui as fixtures
from App.Database.migration_runner import migrate


class CompletionUITests(unittest.TestCase):
    setUpClass=classmethod(fixtures.ReceiptUITests.setUpClass.__func__)
    tearDownClass=classmethod(fixtures.ReceiptUITests.tearDownClass.__func__)
    for _name,_method in vars(fixtures.ReceiptUITests).items():
        if callable(_method) and not _name.startswith('_') and not _name.startswith('test_') and _name not in ('setUp','setUpClass','tearDownClass'):
            locals()[_name]=_method

    def setUp(self):
        fixtures.ReceiptUITests.setUp(self)
        self.login(1);self.release();self.login(2)
        with closing(sqlite3.connect(self.path)) as db:migrate(db,30)
        self.url8=self.receipt_url.replace('/empfang/','/abschluss/')

    def form8(self,html=None,suffix='rating'):
        html=html or self.client.get(self.url8).text
        body=re.search('<form method="post" action="'+re.escape(self.url8+'/'+suffix)+'">(.*?)</form>',html,re.S)
        self.assertIsNotNone(body,html)
        return dict(re.findall('name="([^"]+)" value="([^"]*)"',body.group(1)))

    def receive8(self,actor=2,problem=False):
        self.login(actor)
        form=self.receipt_form()
        if problem:
            r=self.client.post(self.receipt_url+'/review',data=form|{'mode':'problem'})
            data=self.receipt_form(r.text)
            for k in data:
                if k.startswith('missing_'):data[k]='1'
            r=self.client.post(self.receipt_url+'/review',data=data)
        else:r=self.client.post(self.receipt_url+'/review',data=form|{'mode':'complete'})
        self.assertEqual(200,r.status_code)
        r=self.client.post(self.receipt_url+'/confirm',data=self.receipt_form(r.text,'confirm'))
        self.assertEqual(303,r.status_code)

    def test_automatic_completion_and_final_view(self):
        self.receive8();self.receive8(actor=1)
        r=self.client.get(self.url8);self.assertEqual(200,r.status_code)
        self.assertIn('Tausch erfolgreich abgeschlossen',r.text)
        self.assertIn('name="stars"',r.text)
        self.assertEqual('private, no-store',r.headers['Cache-Control'])
        self.assertEqual(303,self.client.get(self.receipt_url).status_code)
        self.login(3);self.assertEqual(404,self.client.get(self.url8).status_code)
        self.assertEqual(404,self.client.get(self.receipt_url).status_code)

    def test_problem_accept_confirmation_releases_and_completes(self):
        self.receive8(actor=1);self.receive8(problem=True)
        data=self.form8(suffix='review')|{'mode':'problem_accepted'}
        review=self.client.post(self.url8+'/review',data=data);self.assertEqual(200,review.status_code)
        self.assertIn('später auftauchender Brief',review.text)
        with closing(sqlite3.connect(self.path)) as db:self.assertEqual(0,db.execute('SELECT COUNT(*) FROM lifecycle_completions').fetchone()[0])
        confirm=self.form8(review.text,'confirm')
        for _ in range(2):self.assertEqual(303,self.client.post(self.url8+'/confirm',data=confirm).status_code)
        self.assertIn('Tausch mit Lieferproblem abgeschlossen',self.client.get(self.url8).text)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(0,db.execute("SELECT COUNT(*) FROM lifecycle_need_claims c JOIN lifecycle_revision_positions p ON p.id=c.revision_position_id JOIN lifecycle_revisions r ON r.id=p.revision_id WHERE r.trade_id=? AND p.from_user_id=1 AND c.state='committed' AND c.received_quantity<c.quantity",(int(self.url8.rsplit('/',1)[1]),)).fetchone()[0])

    def test_blind_html_until_both_ratings_and_no_hidden_tags(self):
        self.receive8();self.receive8(actor=1);self.login(2)
        data=self.form8()|{'stars':'4','tags':'well_packed'}
        self.assertEqual(303,self.client.post(self.url8+'/rating',data=data).status_code)
        self.login(1);html=self.client.get(self.url8).text
        self.assertNotIn('data-visible-rating=',html);self.assertNotIn('4 von 5 Sternen',html)
        data=self.form8(html)|{'stars':'5'}
        self.assertEqual(303,self.client.post(self.url8+'/rating',data=data).status_code)
        html=self.client.get(self.url8).text
        self.assertIn('4 von 5 Sternen',html);self.assertIn('5 von 5 Sternen',html)
        self.assertIn('data-visible-rating="2"',html)

    def test_rating_csrf_actor_trade_token_and_extra_fields(self):
        self.receive8();data=self.form8()|{'stars':'5'}
        without={k:v for k,v in data.items() if k!='_csrf_token'}
        self.assertEqual(403,self.client.post(self.url8+'/rating',data=without,csrf_protect=False).status_code)
        self.assertEqual(400,self.client.post(self.url8+'/rating',data=data|{'token':'bad'}).status_code)
        self.assertEqual(400,self.client.post('/tauschen/abschluss/999/rating',data=data).status_code)
        for field in ('rated_user_id','eligibility_at','deadline','text'):
            self.assertEqual(409,self.client.post(self.url8+'/rating',data=data|{field:'forged'}).status_code)
        self.login(1);self.assertEqual(403,self.client.post(self.url8+'/rating',data=data).status_code)
        self.login(3);self.assertEqual(403,self.client.post(self.url8+'/rating',data=data).status_code)

    def test_problem_wait_cannot_be_forged_early_and_sender_cannot_close(self):
        self.receive8(problem=True);data=self.form8(suffix='review')
        self.assertEqual(409,self.client.post(self.url8+'/review',data=data|{'mode':'after_wait'}).status_code)
        self.login(1);self.assertEqual(403,self.client.post(self.url8+'/review',data=data|{'mode':'problem_accepted'}).status_code)
        self.assertNotIn('Problem akzeptieren und Empfang abschließen',self.client.get(self.url8).text)

    def test_unmigrated_completion_does_not_migrate_on_access(self):
        from tests.test_integration01_trade_shell import fixture
        import hashlib
        path=self.path.parent/'unmigrated-completion.db';fixture(path);self.webapp.DB=str(path)
        before=hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(503,self.client.get(self.url8).status_code)
        self.assertEqual(before,hashlib.sha256(path.read_bytes()).hexdigest())
