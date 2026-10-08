"""HTTP ownership, CSRF and no premature address payloads in any response."""
import re,sqlite3,unittest
from contextlib import closing
from tests import test_lifecycle04_ui as fixtures
from tests.test_lifecycle05_addresses import address
from App.Database.migration_runner import migrate

class AddressUITests(unittest.TestCase):
    setUpClass=classmethod(fixtures.PreparationUITests.setUpClass.__func__)
    tearDownClass=classmethod(fixtures.PreparationUITests.tearDownClass.__func__)
    login=fixtures.PreparationUITests.login
    token=fixtures.PreparationUITests.token
    send=fixtures.PreparationUITests.send
    command=fixtures.PreparationUITests.command
    form=fixtures.PreparationUITests.form
    post=fixtures.PreparationUITests.post
    upload=fixtures.PreparationUITests.upload
    both=fixtures.PreparationUITests.both
    def setUp(self):
        fixtures.PreparationUITests.setUp(self)
        with closing(sqlite3.connect(self.path)) as db:migrate(db,27)
        self.both();self.post('approve');self.login(1);self.post('approve')
        self.address_url=self.url.replace('/vorbereitung/','/adressen/')
    def book_form(self,operation,entry=None):
        html=self.client.get('/tauschen/adressbuch').text
        if entry:
            html=re.search(r'<section class="card" data-address-id="'+str(entry)+r'">(.*?)</section>',html,re.S).group(1)
        body=re.search('<form method="post" action="/tauschen/adressbuch/'+operation+'">(.*?)</form>',html,re.S).group(1)
        return dict(re.findall('name="([^"]+)" value="([^"]*)"',body))
    def create(self,tag):
        r=self.client.post('/tauschen/adressbuch/create',data=self.book_form('create')|address(tag))
        self.assertEqual(303,r.status_code)
        with closing(sqlite3.connect(self.path)) as db:return db.execute('SELECT MAX(id) FROM lifecycle_address_book').fetchone()[0]
    def selection(self):
        html=self.client.get(self.address_url).text
        form=re.search('<form method="post" action="'+re.escape(self.address_url+'/confirm')+'">(.*?)</form>',html,re.S).group(1)
        return dict(re.findall('name="([^"]+)" value="([^"]*)"',form))
    def confirm(self):
        r=self.client.post(self.address_url+'/confirm',data=self.selection());self.assertEqual(303,r.status_code)
        with closing(sqlite3.connect(self.path)) as db:return db.execute('SELECT MAX(id) FROM lifecycle_address_snapshots').fetchone()[0]

    def test_happy_path_json_direct_barrier_no_private_labels(self):
        self.create('Alice');snapshot=self.confirm();r=self.client.get(self.address_url)
        self.assertEqual('private, no-store',r.headers['Cache-Control']);self.assertIn('Fixture Road Alice',r.text)
        self.login(2)
        for url in (self.address_url,self.url,'/tauschen/laufend','/tauschen/adressbuch?user_id=1',self.address_url+'/snapshots/'+str(snapshot)):
            r=self.client.get(url);self.assertNotIn('Fixture Road Alice',r.text);self.assertNotIn('Private Alice',r.text)
        self.create('Bob');self.confirm();r=self.client.get(self.address_url)
        self.assertIn('Fixture Road Alice',r.text);self.assertIn('Versandbereit',r.text);self.assertNotIn('Private Alice',r.text)
        data=self.client.get(self.address_url+'/snapshots/'+str(snapshot)).json
        self.assertEqual('Fixture Road Alice',data['street']);self.assertNotIn('label',data)
        self.login(1);self.assertIn('Fixture Road Bob',self.client.get(self.address_url).text)
        self.assertNotIn('name="shipping',r.text)

    def test_third_user_manipulated_routes_ids_and_csrf(self):
        entry=self.create('Alice');signed=self.selection();snapshot=self.confirm()
        self.login(2);self.create('Bob');self.confirm()
        self.login(3)
        for url in (self.address_url,self.address_url+'/snapshots/'+str(snapshot),'/tauschen/adressen/999/snapshots/'+str(snapshot)):
            r=self.client.get(url);self.assertEqual(404,r.status_code);self.assertNotIn('Fixture Road',r.text)
        self.assertNotIn('Fixture Road Alice',self.client.get('/tauschen/adressbuch?user_id=1').text)
        self.assertEqual(403,self.client.post(self.address_url+'/confirm',data=signed).status_code)
        self.login(1);data=self.book_form('delete',entry);data.pop('_csrf_token',None)
        self.assertEqual(403,self.client.post('/tauschen/adressbuch/delete',data=data,csrf_protect=False).status_code)
        self.assertEqual(400,self.client.post('/tauschen/adressbuch/delete',data=data|{'token':data['token']+'tampered'}).status_code)

    def test_address_book_edit_delete_after_release_trade_fixed(self):
        entry=self.create('Alice');self.confirm();self.login(2);self.create('Bob');self.confirm();self.login(1)
        r=self.client.post('/tauschen/adressbuch/edit',data=self.book_form('edit',entry)|address('Changed'));self.assertEqual(303,r.status_code)
        r=self.client.post('/tauschen/adressbuch/delete',data=self.book_form('delete',entry));self.assertEqual(303,r.status_code)
        self.login(2);html=self.client.get(self.address_url).text;self.assertIn('Fixture Road Alice',html);self.assertNotIn('Fixture Road Changed',html)
        self.assertNotIn('Diese Adresse verbindlich bestätigen',html)

    def test_stale_book_token_and_revision_correction_cannot_release(self):
        entry=self.create('Alice');data=self.selection()
        self.client.post('/tauschen/adressbuch/edit',data=self.book_form('edit',entry)|address('Changed'))
        self.assertEqual(409,self.client.post(self.address_url+'/confirm',data=data).status_code)
        data=self.selection();self.post('correct')
        self.assertEqual(409,self.client.post(self.address_url+'/confirm',data=data).status_code)

    def test_invalid_address_does_not_echo_fields(self):
        r=self.client.post('/tauschen/adressbuch/create',data=self.book_form('create')|address('NoEcho',postal_code=' '))
        self.assertEqual(409,r.status_code);self.assertNotIn('Fixture Road NoEcho',r.text)
        with closing(sqlite3.connect(self.path)) as db:self.assertEqual(0,db.execute('SELECT COUNT(*) FROM lifecycle_address_book').fetchone()[0])

    def test_no_address_schema_no_activation_or_migration(self):
        from tests.test_integration01_trade_shell import fixture
        path=self.path.parent/'unmigrated.db';fixture(path);self.webapp.DB=str(path)
        import hashlib
        before=hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual(503,self.client.get('/tauschen/adressbuch').status_code)
        self.assertEqual(before,hashlib.sha256(path.read_bytes()).hexdigest())

if __name__=='__main__':unittest.main()
