"""Foreign profile trade integration; only synthetic /private/tmp databases."""
import hashlib
import json
import re
import sqlite3
from contextlib import closing
from tests import test_integration01_trade_shell as integration
from tests.test_sap01_search import SearchQuery,search
from trade_shell import read_connection
import unittest


class ProfileTradeTests(unittest.TestCase):
    setUpClass=classmethod(integration.Integration01Tests.setUpClass.__func__)
    tearDownClass=classmethod(integration.Integration01Tests.tearDownClass.__func__)
    def setUp(self):
        integration.Integration01Tests.setUp(self)
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute("UPDATE user_albums SET visibility='public'")

    def data(self,path='/tauschen/sammlr/2/manual'):
        response=self.client.get(path);self.assertEqual(200,response.status_code)
        return json.loads(re.search(r'id="trade-data">(.*?)</script>',response.text,re.S).group(1))

    def test_sap_links_existing_profile_with_explicit_context(self):
        r=self.client.get('/tauschen/sammlr?filtered=1&album=vfl')
        self.assertIn('/profil/synthetic_2?trade_context=1&amp;trade_album=vfl',r.text)
        with read_connection(self.path) as db:row=search(db,1,SearchQuery())['rows'][0]
        r=self.client.get(row['profile_url'])
        self.assertEqual(200,r.status_code)
        self.assertIn(f'<strong>{row["count"]} Sticker</strong> · {row["album_count"]} Album',r.text)

    def test_collection_not_filtered_own_profile_no_trade_block(self):
        with closing(sqlite3.connect(self.path)) as db,db:
            for user in (1,2):db.execute("INSERT INTO user_albums(user_id,album_id,trade_pool_enabled) VALUES (?,'em24',1)",(user,))
            db.execute("UPDATE user_albums SET visibility='public'")
        normal=self.client.get('/profil/synthetic_2').text
        filtered=self.client.get('/profil/synthetic_2?trade_context=1&trade_album=vfl').text
        for content in (normal,filtered):
            self.assertIn('/profil/synthetic_2/album/em24',content)
            self.assertIn('/profil/synthetic_2/album/vfl',content)
        self.assertIn('1 Album ausgewählt',filtered)
        self.assertNotIn('profile-trade-title',self.client.get('/profil').text)
        self.assertNotIn('profile-trade-title',self.client.get('/profil/synthetic_1').text)

    def test_empty_context_keeps_collection_but_no_fake_deal(self):
        response=self.client.get('/profil/synthetic_2?trade_context=1')
        self.assertIn('Aktuell kein Tausch möglich.',response.text)
        self.assertIn('/profil/synthetic_2/album/vfl',response.text)
        self.assertNotIn('Besten Tausch zusammenstellen',response.text)
        self.assertEqual(404,self.client.get('/tauschen/sammlr/2/smartdeal?trade_context=1').status_code)
        self.assertEqual(404,self.client.get('/tauschen/sammlr/2/manual?trade_context=1').status_code)

    def test_existing_auto_deal_path_is_identical_unfiltered(self):
        a=self.client.get('/tauschen/sammlr/2/smartdeal')
        b=self.client.get('/tauschen/sammlr/2/smartdeal?trade_context=1&trade_album=vfl')
        self.assertEqual(200,a.status_code);self.assertEqual(a.data,b.data)
        profile=self.client.get('/profil/synthetic_2?trade_context=1&trade_album=vfl')
        self.assertIn('/tauschen/sammlr/2/smartdeal?trade_context=1&amp;trade_album=vfl',profile.text)

    def test_live_manual_reuses_template_and_validates_server_side_without_write(self):
        before=hashlib.sha256(self.path.read_bytes()).hexdigest()
        data=self.data();context=data['contexts']['same']
        self.assertTrue(data['live']);self.assertEqual(2,context['partner_id'])
        g=context['albums'][0]['give'][0]['key'];r=context['albums'][0]['receive'][0]['key']
        payload=dict(give=[g],receive=[r],fingerprint=data['fingerprint'])
        response=self.client.post(data['validation_url'],json=payload)
        self.assertEqual(200,response.status_code);self.assertTrue(response.json['ok'])
        for values in [dict(give=[],receive=[r]),dict(give=[g],receive=[r,r]),dict(give=[g],receive=['vfl::99999'])]:
            self.assertEqual(400,self.client.post(data['validation_url'],json=dict(values,fingerprint=data['fingerprint'])).status_code)
        self.assertEqual(before,hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_stale_draft_and_pool_disable_fail_closed(self):
        data=self.data()
        with closing(sqlite3.connect(self.path)) as db,db:db.execute("UPDATE stickers SET quantity=1,duplicates=0 WHERE user_id=2 AND sticker_code='6'")
        response=self.client.post(data['validation_url'],json=dict(give=['vfl::1'],receive=['vfl::6'],fingerprint=data['fingerprint']))
        self.assertEqual(409,response.status_code)
        with closing(sqlite3.connect(self.path)) as db,db:db.execute('UPDATE user_albums SET trade_pool_enabled=0 WHERE user_id=2')
        self.assertIn('Aktuell kein Tausch möglich.',self.client.get('/profil/synthetic_2').text)
        self.assertEqual(404,self.client.get('/tauschen/sammlr/2/manual').status_code)

    def test_profile_privacy_is_preserved_separately_from_pool(self):
        with closing(sqlite3.connect(self.path)) as db,db:db.execute("UPDATE users SET profile_privacy='private' WHERE id=2")
        r=self.client.get('/profil/synthetic_2')
        self.assertIn('Dieses Profil ist privat.',r.text)
        self.assertNotIn('/profil/synthetic_2/album/vfl',r.text)
        self.assertIn('Mit synthetic_2 tauschen',r.text) # Pool consent is independent.

    def test_live_manual_bilateral_cross_only_and_independent_privacy(self):
        from App.Database.migration_runner import migrate
        from services.albums import all_codes
        code=all_codes('em24')[30]
        with closing(sqlite3.connect(self.path)) as db,db:
            migrate(db,22)
            for user in (1,2):db.execute("INSERT INTO user_albums(user_id,album_id,trade_pool_enabled) VALUES (?,'em24',1)",(user,))
            db.execute('DELETE FROM stickers WHERE user_id=2')
            for c in all_codes('em24')[30:35]:db.execute("INSERT INTO stickers(user_id,album_id,sticker_code,quantity,duplicates) VALUES (2,'em24',?,2,1)",(c,))
            db.execute("UPDATE user_albums SET cross_album_mode='CROSS_ALBUM_ALLOWED' WHERE user_id=1")
        self.assertEqual(404,self.client.get('/tauschen/sammlr/2/manual').status_code)
        with closing(sqlite3.connect(self.path)) as db,db:db.execute("UPDATE user_albums SET cross_album_mode='CROSS_ALBUM_ALLOWED' WHERE user_id=2")
        data=self.data()
        self.assertTrue(all(a['me']['crossAlbum'] and a['partner']['crossAlbum'] for a in data['contexts']['same']['albums']))
        response=self.client.post(data['validation_url'],json=dict(give=['vfl::1'],receive=['em24::'+code],fingerprint=data['fingerprint']))
        self.assertEqual(200,response.status_code)
        self.assertEqual(404,self.client.get('/tauschen/sammlr/2/manual?trade_context=1&trade_album=em24').status_code)

    def test_asset_allowlist_and_identity(self):
        for name in ['manual.css','manual_ink.js','manual_rules.js','manual_view.js']:
            self.assertEqual(200,self.client.get('/tauschen/manual-assets/'+name).status_code)
        self.assertEqual(404,self.client.get('/tauschen/manual-assets/requests.js').status_code)
        self.assertEqual(404,self.client.get('/tauschen/sammlr/1/manual').status_code)
        self.assertEqual(404,self.client.get('/tauschen/sammlr/999/manual').status_code)
