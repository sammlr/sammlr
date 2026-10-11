"""Real authenticated navigation, SAP cutover and privacy on synthetic DBs."""
import re,sqlite3,unittest
from contextlib import closing
from tests import test_lifecycle03_ui as fixtures
from tests import test_lifecycle08_ui as completion_fixtures
from App.Database.migration_runner import migrate


class CenterUITests(unittest.TestCase):
    setUpClass=classmethod(fixtures.AcceptanceUITests.setUpClass.__func__)
    tearDownClass=classmethod(fixtures.AcceptanceUITests.tearDownClass.__func__)
    login=fixtures.AcceptanceUITests.login
    token=fixtures.AcceptanceUITests.token
    send=fixtures.AcceptanceUITests.send
    command=fixtures.AcceptanceUITests.command
    counter=fixtures.AcceptanceUITests.counter

    def setUp(self):
        fixtures.AcceptanceUITests.setUp(self)
        with closing(sqlite3.connect(self.path)) as db:migrate(db,30)

    def test_three_navigation_destinations_and_empty_states(self):
        r=self.client.get('/zentrale');self.assertEqual(200,r.status_code)
        nav=re.search('<nav class="bottom-nav">(.*?)</nav>',r.text,re.S).group(1)
        self.assertEqual(3,nav.count('class="bottom-nav-link'))
        self.assertIn('href="/zentrale" aria-current="page"',nav)
        for path in ('/sammlung','/tauschen'):self.assertIn('href="'+path+'"',nav);self.assertEqual(200,self.client.get(path).status_code)
        for text in ('Meine To-dos','Meine Sendungen','Meine Eingänge','Alles erledigt.','Du hast aktuell keine offenen Sendungen.','Du erwartest gerade keine Sticker.'):
            self.assertIn(text,r.text)
        self.assertEqual(3,r.text.count('class="center-all"'))
        self.assertEqual('private, no-store',r.headers['Cache-Control'])

    def test_accepted_request_moves_from_sap_to_center_and_direct_preparation(self):
        url=self.send();trade=int(url.rsplit('/',1)[1]);self.login(2)
        self.assertIn('data-status="open"',self.client.get('/tauschen/laufend').text)
        r=self.client.post(url+'/accept',data=self.command(url,'accept'))
        self.assertEqual('/tauschen/vorbereitung/'+str(trade),r.location)
        self.assertNotIn('data-status="accepted"',self.client.get('/tauschen/laufend').text)
        html=self.client.get('/zentrale').text
        self.assertIn('data-trade="'+str(trade)+'"',html)
        self.assertIn('href="/tauschen/vorbereitung/'+str(trade)+'"',html)
        self.assertIn('href="/zentrale" aria-current="page"',self.client.get(r.location).text)
        self.login(3);self.assertNotIn('data-trade=',self.client.get('/zentrale').text)
        self.assertEqual(404,self.client.get(r.location).status_code)

    def test_counteroffer_remains_in_sap(self):
        url=self.send();self.login(2);self.counter(url)
        self.login(1);html=self.client.get('/tauschen/laufend').text
        self.assertIn('Gegenangebot',html);self.assertIn('data-status="open"',html)
        self.assertNotIn('data-trade=',self.client.get('/zentrale').text)

    def test_invalid_pages_and_no_client_owner_override(self):
        for path in ('/zentrale?page=-1','/zentrale/todos?page=x','/zentrale/todos?page=100001'):
            self.assertEqual(400,self.client.get(path).status_code)
        self.assertEqual(404,self.client.get('/zentrale/999').status_code)
        self.assertEqual(405,self.client.post('/zentrale').status_code)
        self.assertEqual(self.client.get('/zentrale').text,self.client.get('/zentrale?user_id=999&trade_id=999').text)

    def test_user_fields_escaped_no_lists_of_private_data(self):
        url=self.send();self.login(2);self.client.post(url+'/accept',data=self.command(url,'accept'));self.login(1)
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute("UPDATE users SET username=? WHERE id=2",('<script>sentinel()</script>',))
        html=self.client.get('/zentrale').text
        self.assertNotIn('<script>sentinel()</script>',html);self.assertIn('&lt;script&gt;sentinel()',html)
        self.assertNotIn('/fotos/',html);self.assertNotIn('/snapshots/',html)


class CenterArchiveUITests(unittest.TestCase):
    setUpClass=classmethod(completion_fixtures.CompletionUITests.setUpClass.__func__)
    tearDownClass=classmethod(completion_fixtures.CompletionUITests.tearDownClass.__func__)
    for name in ('login','token','send','command','form','post','upload','both','book_form','create','selection','confirm','release','receipt_form','receive8','form8'):
        locals()[name]=getattr(completion_fixtures.CompletionUITests,name)
    def setUp(self):completion_fixtures.CompletionUITests.setUp(self)

    def test_closed_trade_archived_rating_todo_and_blind_details(self):
        self.receive8();self.receive8(actor=1)
        for section in ('sendungen','eingaenge'):self.assertNotIn('data-trade=',self.client.get('/zentrale/'+section).text)
        html=self.client.get('/zentrale/archiv').text;self.assertIn('Erfolgreich abgeschlossen',html)
        self.assertIn('Bewertung abgeben',self.client.get('/zentrale/todos').text)
        self.login(2);data=self.form8()|{'stars':'4','tags':'well_packed'}
        self.client.post(self.url8+'/rating',data=data);self.login(1)
        for path in ('/zentrale','/zentrale/archiv',self.url8):self.assertNotIn('4 von 5 Sternen',self.client.get(path).text)
        data=self.form8()|{'stars':'5'};self.client.post(self.url8+'/rating',data=data)
        self.assertIn('4 von 5 Sternen',self.client.get(self.url8).text)
        self.assertIn('Alles erledigt.',self.client.get('/zentrale').text)
