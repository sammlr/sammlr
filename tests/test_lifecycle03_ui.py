"""Productive handshake routes, synthetic /private/tmp databases only."""
import re,sqlite3,unittest
from contextlib import closing
from tests import test_lifecycle02_ui as fixtures
from App.Database.migration_runner import migrate


class AcceptanceUITests(unittest.TestCase):
    setUpClass=classmethod(fixtures.RequestUITests.setUpClass.__func__)
    tearDownClass=classmethod(fixtures.RequestUITests.tearDownClass.__func__)
    login=fixtures.RequestUITests.login
    token=fixtures.RequestUITests.token
    def setUp(self):
        fixtures.RequestUITests.setUp(self)
        with closing(sqlite3.connect(self.path)) as db:migrate(db,25)

    def send(self):
        r=self.client.post('/tauschen/anfragen',data={'token':self.token()})
        self.assertEqual(303,r.status_code);return r.location

    def command(self,url,action):
        html=self.client.get(url).text
        form=re.search(r'<form method="post" action="'+re.escape(url+'/'+action)+r'">(.*?)</form>',html,re.S)
        self.assertIsNotNone(form,html)
        return {name:value for name,value in re.findall('name="([^"]+)" value="([^"]*)"',form.group(1))}

    def counter(self,url):
        r=self.client.post(url+'/counter-preview',data=self.command(url,'counter-preview'))
        self.assertEqual(200,r.status_code);self.assertIn('Gegenangebot prüfen',r.text)
        token=re.search('name="token" value="([^"]+)"',r.text).group(1)
        return self.client.post(url+'/counter',data={'token':token})

    def test_accept_and_binding_display(self):
        url=self.send();self.login(2)
        r=self.client.post(url+'/accept',data=self.command(url,'accept'))
        self.assertEqual(303,r.status_code)
        html=self.client.get(url).text
        self.assertIn('Tausch angenommen',html);self.assertIn('Als Nächstes: Sticker vorbereiten',html)
        self.assertNotIn('Anfrage ablehnen',html);self.assertNotIn('Anfrage zurückziehen',html)
        self.login(1);self.assertIn('Tausch angenommen',self.client.get(url).text)
        self.assertEqual(403,self.client.post(url+'/withdrawn').status_code)

    def test_invalid_original_then_counter_accept(self):
        url=self.send();self.login(2)
        with closing(sqlite3.connect(self.path)) as db,db:db.execute("UPDATE stickers SET quantity=1,duplicates=0 WHERE user_id=2 AND sticker_code='6'")
        r=self.client.post(url+'/accept',data=self.command(url,'accept'))
        self.assertEqual(409,r.status_code);self.assertIn('nicht mehr vollständig möglich',r.text)
        self.assertIn('Tausch neu berechnen',r.text)
        self.assertEqual(303,self.counter(url).status_code)
        self.login(1);html=self.client.get(url).text
        self.assertIn('Gegenangebot von synthetic_2',html)
        self.assertNotIn('Tausch neu berechnen',html)
        self.assertEqual(303,self.client.post(url+'/accept',data=self.command(url,'accept')).status_code)
        self.assertIn('Tausch angenommen',self.client.get(url).text)

    def test_invalid_counter_ends_without_third_offer(self):
        url=self.send();self.login(2);self.counter(url)
        with closing(sqlite3.connect(self.path)) as db,db:db.execute("UPDATE stickers SET quantity=1,duplicates=0 WHERE user_id=1 AND sticker_code='1'")
        self.login(1);self.client.post(url+'/accept',data=self.command(url,'accept'))
        html=self.client.get(url).text
        self.assertIn('Verhandlung beendet',html);self.assertIn('neuen Tausch starten',html)
        self.assertNotIn('Tausch neu berechnen',html);self.assertNotIn('>Annehmen<',html)

    def test_csrf_foreign_token_and_unsupported_old_schema(self):
        url=self.send();self.login(2);data=self.command(url,'accept')
        data.pop('_csrf_token',None)
        self.assertEqual(403,self.client.post(url+'/accept',data=data,csrf_protect=False).status_code)
        self.login(3);self.assertEqual(403,self.client.post(url+'/accept',data=data).status_code)
        self.assertEqual(404,self.client.get(url).status_code)

    def test_counter_preview_is_not_send(self):
        url=self.send();self.login(2)
        r=self.client.post(url+'/counter-preview',data=self.command(url,'counter-preview'))
        self.assertEqual(200,r.status_code)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(1,db.execute('SELECT COUNT(*) FROM lifecycle_revisions').fetchone()[0])
            self.assertEqual(1,db.execute("SELECT sender_user_id FROM lifecycle_requests WHERE status='open'").fetchone()[0])

if __name__=='__main__':unittest.main()
