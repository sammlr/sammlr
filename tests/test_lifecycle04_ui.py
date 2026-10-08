"""Private HTTP preparation endpoints with authenticated synthetic users."""
import io,re,sqlite3,unittest
from contextlib import closing
from tests import test_lifecycle03_ui as fixtures
from tests.test_lifecycle04_preparation import PNG,chunk
from App.Database.migration_runner import migrate

class PreparationUITests(unittest.TestCase):
    setUpClass=classmethod(fixtures.AcceptanceUITests.setUpClass.__func__)
    tearDownClass=classmethod(fixtures.AcceptanceUITests.tearDownClass.__func__)
    login=fixtures.AcceptanceUITests.login
    token=fixtures.AcceptanceUITests.token
    send=fixtures.AcceptanceUITests.send
    command=fixtures.AcceptanceUITests.command
    def setUp(self):
        fixtures.AcceptanceUITests.setUp(self)
        with closing(sqlite3.connect(self.path)) as db:migrate(db,26)
        self.webapp.app.config['LIFECYCLE_PHOTO_DIR']=str(self.path.parent/'photos')
        url=self.send();self.login(2)
        self.client.post(url+'/accept',data=self.command(url,'accept'))
        self.url=url.replace('/anfragen/','/vorbereitung/');self.login(1)
    def form(self,action):
        html=self.client.get(self.url).text
        form=re.search('<form method="post" action="'+re.escape(self.url+'/'+action)+'"[^>]*>(.*?)</form>',html,re.S)
        self.assertIsNotNone(form,html)
        return dict(re.findall('name="([^"]+)" value="([^"]*)"',form.group(1)))
    def post(self,action,**data):return self.client.post(self.url+'/'+action,data=self.form(action)|data)
    def upload(self):
        response=self.post('upload',photo=(io.BytesIO(PNG),'proof.png'));self.assertEqual(303,response.status_code)
        return re.findall(r'src="([^"]+/fotos/\d+)"',self.client.get(self.url).text)[-1]
    def both(self):
        for a in (1,2):self.login(a);self.upload();self.assertEqual(303,self.post('complete').status_code)
    def test_photos_direct_auth_barrier_headers_and_multiple(self):
        p=self.upload();self.upload();self.post('complete')
        self.assertEqual(200,self.client.get(p).status_code)
        self.login(2);self.assertEqual(404,self.client.get(p).status_code)
        self.upload();self.post('complete');r=self.client.get(p)
        self.assertEqual(200,r.status_code);self.assertEqual('private, no-store',r.headers['Cache-Control'])
        self.login(3);self.assertEqual(404,self.client.get(p).status_code);self.assertEqual(404,self.client.get(self.url).status_code)
        self.login(1);self.assertEqual(404,self.client.get(p.replace('/fotos/','/fotos/999')).status_code)
    def test_happy_path_no_address_payload_or_shipping_control(self):
        self.both();self.post('approve');self.login(1);self.post('approve')
        html=self.client.get(self.url).text
        self.assertIn('data-preparation-state="ready_for_address_release"',html)
        self.assertNotIn('name="address',html);self.assertNotIn('name="shipping',html)
        self.assertIn('Vorbereitung öffnen',self.client.get('/tauschen/laufend').text)
    def test_csrf_token_actor_and_action_tampering(self):
        data=self.form('complete');data.pop('_csrf_token')
        self.assertEqual(403,self.client.post(self.url+'/complete',data=data,csrf_protect=False).status_code)
        self.assertEqual(400,self.client.post(self.url+'/upload',data=data).status_code)
        self.login(2);self.assertEqual(403,self.client.post(self.url+'/complete',data=data).status_code)
    def test_correction_problem_and_new_photo_review(self):
        self.both();self.login(1);self.post('problem',reason='NOT_RECOGNIZABLE')
        self.login(2);self.post('correct');self.upload();self.post('complete')
        self.login(1);self.post('approve');self.login(2);self.post('approve')
        self.assertIn('ready_for_address_release',self.client.get(self.url).text)
    def test_reduction_diff_accept_and_old_request_still_visible(self):
        html=self.client.get(self.url).text
        names=re.findall(r'name="(quantity_\d+)"',html)
        data={name:('0' if i in (0,5) else '1') for i,name in enumerate(names)}
        self.assertEqual(303,self.post('reduction_propose',**data).status_code)
        self.login(2);self.assertIn('→ 0',self.client.get(self.url).text)
        self.assertEqual(303,self.post('reduction_approve').status_code)
        self.assertIn('Vorbereitung öffnen',self.client.get('/tauschen/laufend').text)
        self.assertEqual(200,self.client.get(self.url.replace('/vorbereitung/','/anfragen/')).status_code)
    def test_reject_keeps_contract_blocked(self):
        names=re.findall(r'name="(quantity_\d+)"',self.client.get(self.url).text)
        self.post('reduction_propose',**{name:('0' if i in (0,5) else '1') for i,name in enumerate(names)})
        self.login(2);self.post('reduction_reject')
        self.assertIn('reduction_rejected',self.client.get(self.url).text)

    def test_control_photo_body_limit_is_scoped_and_realistic(self):
        # Valid PNG ancillary metadata takes the input above the global 1 MB
        # limit; sanitization strips it before storage.
        large=PNG[:-12]+chunk(b'tEXt',b'Comment\0'+b'x'*(1100*1024))+PNG[-12:]
        self.assertEqual(303,self.post('upload',photo=(io.BytesIO(large),'large.png')).status_code)
        too_large=PNG+b'x'*(13*1024*1024)
        self.assertEqual(413,self.post('upload',photo=(io.BytesIO(too_large),'too-large.png')).status_code)
        self.assertEqual(1024*1024,self.webapp.app.config['MAX_CONTENT_LENGTH'])

if __name__=='__main__':unittest.main()
