"""SAP-02: canonical targets, capacity, freshness. Synthetic /private/tmp only."""
from types import SimpleNamespace as NS
from contextlib import closing
import sqlite3
import unittest
from tests import test_sap01_search as sap
from tests import test_profile_trade01 as profile
from services.trade_search_intent import resolve_search
from services.albums import all_codes


class SearchIntentTests(unittest.TestCase):
    def resolve(self,text,missing,count=5):
        ids=['wm26','em24']+[f'album{i}' for i in range(3,count+1)]
        albums=[NS(album_id=a,catalog_codes=('POR15','GER14','FRA3')) for a in ids]
        needs=[NS(album_id=a,sticker_code=c) for a,c in missing]
        return resolve_search(text,[(a,a.upper()) for a in ids],albums,needs,['Jens1'])

    def test_one_missing_out_of_five(self):
        r=self.resolve('POR15',[('wm26','POR15')]);self.assertEqual({('wm26','POR15')},r.targets);self.assertFalse(r.ambiguous)

    def test_two_missing_out_of_five_and_precise_album(self):
        needs=[('wm26','POR15'),('em24','POR15')]
        r=self.resolve('POR15',needs);self.assertEqual(set(needs),r.targets);self.assertEqual((('POR15',2),),r.ambiguous)
        self.assertEqual({('em24','POR15')},self.resolve('EM24 POR15',needs).targets)
        self.assertEqual({('wm26','POR15')},self.resolve('WM26 POR 15',needs).targets)

    def test_seventeen_album_targets_no_global_code_identity(self):
        needs=[('wm26','POR15'),('em24','POR15'),('album17','POR15')]
        self.assertEqual(set(needs),self.resolve('POR15',needs,17).targets)

    def test_or_separators_deduplication_and_username(self):
        needs=[('wm26','POR15'),('em24','GER14'),('wm26','FRA3')]
        self.assertEqual(set(needs),self.resolve('POR15, GER14 / FRA3; POR15',needs).targets)
        self.assertEqual('jens1',self.resolve('@Jens1',[]).collector)
        self.assertEqual('collector',self.resolve('Jens1',[]).kind)
        self.assertEqual('stickers',self.resolve('POR9999',[]).kind)


class SAP02DomainTests(unittest.TestCase):
    setUp=sap.SAPSearchTests.setUp
    inventory=sap.SAPSearchTests.inventory
    pair=sap.SAPSearchTests.pair
    results=sap.SAPSearchTests.results


def domain_test(method):
    setattr(SAP02DomainTests,method.__name__,method)
    return method


@domain_test
def test_hits_before_size_then_size_breaks_equal_hits(self):
    self.pair(12,3)
    self.inventory(3,'vfl',['31','32']+[str(c) for c in range(50,58)])
    self.inventory(4,'vfl',['31','32','33','80'])
    rows=self.results(text='31 32 33')['rows']
    self.assertEqual([4,2,3],[p['id'] for p in rows]);self.assertEqual([3,3,2],[p['hits'] for p in rows])
    self.assertEqual([4,3,10],[p['count'] for p in rows])


@domain_test
def test_simultaneous_hits_cannot_exceed_available_give(self):
    self.pair(2,6)
    r=self.results(text='31 32 33')['rows'][0]
    self.assertEqual(2,r['hits']);self.assertEqual(3,r['target_count']);self.assertEqual(2,r['count'])


@domain_test
def test_album_search_does_not_reduce_full_deal(self):
    self.pair();self.pair(5,4,album='em24')
    r=self.results(text='em24')['rows'][0];self.assertEqual(10,r['count']);self.assertEqual(4,r['hits'])
    self.assertEqual(4,self.results(text='em24',albums=frozenset({'em24'}))['rows'][0]['count'])
    name=self.db.execute("SELECT name FROM albums WHERE id='em24'").fetchone()[0]
    self.assertEqual(10,self.results(text=name)['rows'][0]['count'])


@domain_test
def test_real_album_code_formats_owned_needs_and_qualification(self):
    for user in (1,2):self.db.execute("INSERT INTO user_albums(user_id,album_id,trade_pool_enabled) VALUES (?,'wm26',1)",(user,))
    self.inventory(1,'wm26',['FWC1','FWC2']);self.inventory(2,'wm26',['POR15'])
    self.inventory(1,'em24',all_codes('em24')[:2]);self.inventory(2,'em24',['POR 15'])
    r=self.results(text='POR15');self.assertEqual(2,r['target_count']);self.assertEqual(2,r['rows'][0]['hits'])
    self.assertEqual(1,self.results(text='WM26 POR15')['target_count'])
    self.inventory(1,'em24',['POR 15'],quantity=1)
    r=self.results(text='POR15');self.assertEqual(1,r['target_count']);self.assertFalse(r['ambiguous'])


@domain_test
def test_give_and_receive_reservations_reduce_both_counts(self):
    self.pair(3,3)
    self.db.execute("INSERT INTO trade_requests(id,album_id,from_user_id,to_user_id,status) VALUES (100,'vfl',1,2,'accepted')")
    self.db.execute("INSERT INTO trades(id,legacy_trade_request_id,requester_user_id,partner_user_id,lifecycle_state) VALUES (100,100,1,2,'accepted')")
    for pos,giver,receiver,code in [(100,1,2,'1'),(101,2,1,'31')]:
        self.db.execute("INSERT INTO trade_positions(id,trade_id,from_user_id,to_user_id,album_id,sticker_code,quantity) VALUES (?,100,?,?,'vfl',?,1)",(pos,giver,receiver,code))
        self.db.execute("INSERT INTO trade_reservations(trade_id,trade_position_id,user_id,album_id,sticker_code,quantity) VALUES (100,?,?,'vfl',?,1)",(pos,giver,code))
    self.db.commit()
    r=self.results(text='31 32 33');self.assertEqual(2,r['target_count']);self.assertEqual(2,r['rows'][0]['hits']);self.assertEqual(2,r['rows'][0]['count'])


class SAP02FreshnessTests(unittest.TestCase):
    setUpClass=classmethod(profile.ProfileTradeTests.setUpClass.__func__)
    tearDownClass=classmethod(profile.ProfileTradeTests.tearDownClass.__func__)
    setUp=profile.ProfileTradeTests.setUp

    def test_home_alias_is_same_sap_no_top_three(self):
        a=self.client.get('/tauschen');b=self.client.get('/tauschen/sammlr')
        self.assertEqual(a.data,b.data);self.assertIn('sap-search',a.text);self.assertNotIn('class="trade-stage',a.text)
        self.assertNotIn('Alle Sammlr',a.text)

    def test_profile_auto_manual_communicate_fresh_size(self):
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute("INSERT INTO stickers(user_id,album_id,sticker_code,quantity,duplicates) VALUES (2,'vfl','200',2,1),(2,'vfl','201',2,1)")
        self.assertIn('7 Sticker',self.client.get('/profil/synthetic_2').text)
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute("DELETE FROM stickers WHERE user_id=2 AND sticker_code='201'")
        for route in ['/profil/synthetic_2','/tauschen/sammlr/2/smartdeal','/tauschen/sammlr/2/manual']:
            response=self.client.get(route+'?trade_seen=7')
            self.assertEqual(200,response.status_code);self.assertIn('Aktuell sind 6 Sticker möglich.',response.text)
        with closing(sqlite3.connect(self.path)) as db,db:db.execute('UPDATE user_albums SET trade_pool_enabled=0 WHERE user_id=2')
        for route in ['/profil/synthetic_2','/tauschen/sammlr/2/smartdeal','/tauschen/sammlr/2/manual']:
            response=self.client.get(route+'?trade_seen=6')
            self.assertEqual(200,response.status_code);self.assertIn('kein Tausch möglich',response.text)

    def test_private_collection_is_not_an_ineligible_trade_album(self):
        with closing(sqlite3.connect(self.path)) as db,db:db.execute("UPDATE user_albums SET visibility='private' WHERE user_id=2")
        response=self.client.get('/profil/synthetic_2')
        self.assertNotIn('/profil/synthetic_2/album/vfl',response.text)
        self.assertIn('Tauschfreigaben gelten separat',response.text)
        self.assertEqual(200,self.client.get('/tauschen/sammlr/2/manual').status_code)


@domain_test
def test_five_and_seventeen_real_memberships_filter_both_directions(self):
    self.pair()
    for index in range(3,18):
        album=f'fixture{index}'
        self.db.execute("INSERT INTO albums(id,name,total) VALUES (?,?,728)",(album,f'Testalbum {index}'))
        for user in (1,2):
            self.db.execute("INSERT INTO user_albums(user_id,album_id,trade_pool_enabled) VALUES (?,?,1)",(user,album))
    self.db.commit()
    self.pair(2,2,album='fixture3')
    for count in (1,5,17):
        albums=['vfl','em24']+[f'fixture{i}' for i in range(3,18)]
        result=self.results(albums=frozenset(albums[:count]))
        self.assertEqual(count,len(result['selected']))
        self.assertEqual(6 if count==1 else 8,result['rows'][0]['count'])
    self.assertEqual(6,self.results(albums=frozenset({'vfl'}))['rows'][0]['count'])
