"""Shipping confirmation, privacy and replay through authenticated HTTP."""
import re
import sqlite3
import unittest
from contextlib import closing
from tests import test_lifecycle05_ui as fixtures
from App.Database.migration_runner import migrate


class ShippingUITests(unittest.TestCase):
    setUpClass=classmethod(fixtures.AddressUITests.setUpClass.__func__)
    tearDownClass=classmethod(fixtures.AddressUITests.tearDownClass.__func__)
    login=fixtures.AddressUITests.login
    token=fixtures.AddressUITests.token
    send=fixtures.AddressUITests.send
    command=fixtures.AddressUITests.command
    form=fixtures.AddressUITests.form
    post=fixtures.AddressUITests.post
    upload=fixtures.AddressUITests.upload
    both=fixtures.AddressUITests.both
    book_form=fixtures.AddressUITests.book_form
    create=fixtures.AddressUITests.create
    selection=fixtures.AddressUITests.selection
    confirm=fixtures.AddressUITests.confirm

    def setUp(self):
        fixtures.AddressUITests.setUp(self)
        with closing(sqlite3.connect(self.path)) as db:
            migrate(db,28)
        self.shipping_url=self.address_url.replace('/adressen/','/versand/')

    def release(self):
        self.create('Alice');self.confirm()
        self.login(2);self.create('Bob');self.confirm();self.login(1)

    def shipping_form(self,html):
        body=re.search(r'<form method="post" action="'+re.escape(self.shipping_url)+r'/[^\"]+">(.*?)</form>',html,re.S).group(1)
        return dict(re.findall('name="([^"]+)" value="([^"]*)"',body))

    def test_shipping_two_steps_replay_and_privacy(self):
        self.assertEqual(404,self.client.get(self.shipping_url).status_code)
        self.release()
        r=self.client.get(self.shipping_url)
        self.assertEqual('private, no-store',r.headers['Cache-Control'])
        data=self.shipping_form(r.text)
        self.assertEqual(400,self.client.post(self.shipping_url+'/confirm',data=data).status_code)
        r=self.client.post(self.shipping_url+'/review',data=data)
        self.assertEqual(200,r.status_code)
        self.assertIn('Hast du den Brief wirklich abgeschickt?',r.text)
        signed=self.shipping_form(r.text)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(0,db.execute('SELECT COUNT(*) FROM lifecycle_shipping').fetchone()[0])
        for _ in range(2):
            self.assertEqual(303,self.client.post(self.shipping_url+'/confirm',data=signed).status_code)
        self.assertIn('data-own-state="sent"',self.client.get(self.shipping_url).text)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(1,db.execute('SELECT COUNT(*) FROM lifecycle_shipping').fetchone()[0])
        self.login(3)
        r=self.client.get(self.shipping_url)
        self.assertEqual(404,r.status_code);self.assertNotIn('Fixture Road',r.text)
        self.assertEqual(403,self.client.post(self.shipping_url+'/confirm',data=signed).status_code)

    def test_shipping_csrf_and_tampered_token(self):
        self.release();data=self.shipping_form(self.client.get(self.shipping_url).text)
        data.pop('_csrf_token')
        self.assertEqual(403,self.client.post(self.shipping_url+'/review',data=data,csrf_protect=False).status_code)
        self.assertEqual(400,self.client.post(self.shipping_url+'/review',data=data|{'token':'tampered'}).status_code)
