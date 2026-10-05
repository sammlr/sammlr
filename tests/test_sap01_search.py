"""SAP-01 integration assertions on SQL-generated synthetic databases only."""
from contextlib import closing
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
import hashlib
import sqlite3
import sys
import tempfile
import unittest
from werkzeug.datastructures import MultiDict

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'App'))
from tests.test_integration01_trade_shell import fixture
from services.trade_search import SearchQuery, search
from services.albums import all_codes
from services.trade_v2_preferences import TradeV2Preferences
from App.Database.migration_runner import migrate
from trade_shell import read_connection


class SAPSearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='sap01-',dir='/private/tmp')
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'synthetic.db'
        fixture(self.path,3)
        self.db=sqlite3.connect(self.path);self.db.row_factory=sqlite3.Row
        self.addCleanup(self.db.close)
        for user in range(1,5):
            self.db.execute("INSERT INTO user_albums(user_id,album_id,trade_pool_enabled) VALUES (?,'em24',1)",(user,))
        self.db.execute('DELETE FROM stickers');self.db.commit()

    def inventory(self,user,album,codes,quantity=2):
        for code in codes:
            self.db.execute('INSERT INTO stickers(user_id,album_id,sticker_code,quantity,duplicates) VALUES (?,?,?,?,?)',
                            (user,album,code,quantity,quantity-1))
        self.db.commit()

    def pair(self, own=8, other=6, user=2, album='vfl', quantity=2):
        codes=all_codes(album)
        self.inventory(1,album,codes[:own])
        self.inventory(user,album,codes[30:30+other],quantity)

    def results(self, **kw):
        with read_connection(self.path) as db:
            return search(db,1,SearchQuery(**kw))

    def test_default_all_and_none_and_invalid_filter(self):
        self.pair()
        r=self.results();self.assertEqual({'vfl','em24'},r['selected'])
        self.assertEqual('deal',r['query'].sort);self.assertEqual(6,r['rows'][0]['count'])
        for albums in (frozenset(),frozenset({'unknown'})):
            self.assertEqual([],self.results(albums=albums)['rows'])

    def test_album_removed_from_both_directions_counts_and_search(self):
        self.pair();self.pair(5,4,album='em24')
        self.assertEqual(10,self.results()['rows'][0]['count'])
        r=self.results(albums=frozenset({'vfl'}));self.assertEqual(6,r['rows'][0]['count']);self.assertEqual(1,r['rows'][0]['album_count'])
        token=all_codes('em24')[30]
        self.assertEqual([],self.results(albums=frozenset({'vfl'}),text=token)['rows'])
        self.assertEqual([],self.results(albums=frozenset({'vfl'}),text=token)['extra'])

    def test_partner_pool_and_own_pool_intersection(self):
        self.pair();self.pair(5,4,album='em24')
        self.db.execute("UPDATE user_albums SET trade_pool_enabled=0 WHERE user_id=2 AND album_id='em24'");self.db.commit()
        self.assertEqual(6,self.results()['rows'][0]['count'])
        self.db.execute("UPDATE user_albums SET trade_pool_enabled=0 WHERE user_id=1 AND album_id='em24'");self.db.commit()
        self.assertEqual({'vfl'},self.results()['selected'])

    def test_maximum_beats_activity_and_oversupply(self):
        self.pair(30,21)
        self.inventory(3,'vfl',all_codes('vfl')[70:100])
        self.db.execute("INSERT INTO user_activity(user_id,last_active_at) VALUES (2,'2099-01-01 00:00:00')");self.db.commit()
        r=self.results()['rows'];self.assertEqual([3,2],[p['id'] for p in r]);self.assertEqual([30,21],[p['count'] for p in r])

    def test_duplicates_count_available_copies_only_in_intersection(self):
        self.pair(8,6,quantity=4)
        self.inventory(3,'vfl',all_codes('vfl')[50:55],quantity=2)
        self.inventory(3,'em24',all_codes('em24')[:20],quantity=100)
        r=self.results(albums=frozenset({'vfl'}),sort='duplicates')['rows']
        self.assertEqual([2,3],[p['id'] for p in r]);self.assertEqual(18,r[0]['duplicates']);self.assertEqual(6,r[0]['relevant'])

    def test_single_multiple_separators_name_and_combined_sort(self):
        self.pair();self.inventory(3,'vfl',all_codes('vfl')[30:32])
        self.db.execute("UPDATE users SET username='Jens1' WHERE id=2");self.db.commit()
        code=all_codes('vfl')[30];second=all_codes('vfl')[34]
        r=self.results(text=code)['rows'];self.assertEqual([2,3],[p['id'] for p in r])
        r=self.results(text=f' {code}; {second} / {code} ',sort='duplicates')['rows']
        self.assertEqual([2,1],[p['hits'] for p in r]);self.assertEqual([2,3],[p['id'] for p in r])
        self.assertEqual([2],[p['id'] for p in self.results(text='jEnS1')['rows']])
        self.assertEqual([],self.results(text='no such person')['rows'])

    def test_prefixed_search_with_internal_space_and_unknown_code(self):
        self.pair(album='em24')
        code=all_codes('em24')[30]
        import re
        query=re.sub(r'([A-Z]+)(\d+)',r'\1 \2',code)
        self.assertEqual(1,self.results(text=query)['rows'][0]['hits'])
        self.assertEqual([],self.results(text='POR99999')['rows'])

    def test_favorite_only_breaks_equal_sizes_then_overlap_activity_id(self):
        self.pair(10,3);self.pair(10,7,album='em24')
        self.inventory(3,'vfl',all_codes('vfl')[50:57]);self.inventory(3,'em24',all_codes('em24')[50:53])
        self.db.execute("UPDATE users SET favorite_album_id='em24' WHERE id=1");self.db.commit()
        self.assertEqual([2,3],[p['id'] for p in self.results()['rows']])
        self.inventory(3,'vfl',[all_codes('vfl')[57]])
        self.assertEqual([3,2],[p['id'] for p in self.results()['rows']])

    def test_overlap_then_activity_then_stable_id(self):
        self.pair(4,5)
        self.inventory(3,'vfl',all_codes('vfl')[50:56])
        self.assertEqual([3,2],[p['id'] for p in self.results()['rows']])
        self.inventory(2,'vfl',[all_codes('vfl')[35]])
        self.assertEqual([2,3],[p['id'] for p in self.results()['rows']])
        self.db.execute("INSERT INTO user_activity(user_id,last_active_at) VALUES (3,'2026-10-01 12:00:00')")
        self.db.commit()
        self.assertEqual([3,2],[p['id'] for p in self.results()['rows']])

    def test_search_cannot_smuggle_a_restricted_album_into_other_deal(self):
        self.pair()
        self.inventory(2,'em24',[all_codes('em24')[30]])
        r=self.results(text=all_codes('em24')[30])
        self.assertFalse(r['rows'])
        self.assertEqual([2],[p['id'] for p in r['extra']])
        self.assertEqual(6,self.results()['rows'][0]['count'])
        self.assertEqual(1,self.results()['rows'][0]['album_count'])

    def test_no_deal_only_visible_in_separate_concrete_search(self):
        self.inventory(2,'em24',all_codes('em24')[30:33])
        self.assertEqual([],self.results()['rows']);self.assertEqual([],self.results(text='synthetic')['rows'])
        r=self.results(text=all_codes('em24')[30]);self.assertFalse(r['rows']);self.assertEqual([2],[p['id'] for p in r['extra']])

    def test_bilateral_cross_and_restricted_search_candidate(self):
        self.inventory(1,'vfl',all_codes('vfl')[:8]);self.inventory(2,'em24',all_codes('em24')[30:36])
        self.assertFalse(self.results()['rows'])
        migrate(self.db,22);prefs=TradeV2Preferences(self.db)
        for album in ('vfl','em24'):prefs.set_mode(1,album,'CROSS_ALBUM_ALLOWED')
        self.db.commit();self.assertFalse(self.results()['rows'])
        for album in ('vfl','em24'):prefs.set_mode(2,album,'CROSS_ALBUM_ALLOWED')
        self.db.commit();self.assertEqual(6,self.results()['rows'][0]['count'])
        self.assertFalse(self.results(albums=frozenset({'em24'}))['rows'])

    def test_fifty_limit_and_more_preserves_full_query(self):
        self.pair()
        for user in range(5,60):
            self.db.execute("INSERT INTO users(id,username,password) VALUES (?,?,?)",(user,f'synthetic_{user}','synthetic-unused'))
            self.db.execute("INSERT INTO user_albums(user_id,album_id,trade_pool_enabled) VALUES (?,'vfl',1)",(user,))
            self.inventory(user,'vfl',all_codes('vfl')[30:36])
        r=self.results(albums=frozenset({'vfl'}),text='synthetic',sort='duplicates')
        self.assertEqual(50,len(r['rows']));self.assertEqual(56,r['total'])
        params=parse_qs(urlsplit(r['more']).query)
        q=SearchQuery.parse(MultiDict([(k,v) for k,values in params.items() for v in values]))
        self.assertEqual(frozenset({'vfl'}),q.albums);self.assertEqual('synthetic',q.text);self.assertEqual('deal',q.sort);self.assertNotIn('sort',params)
        r=search(self.db,1,q);self.assertEqual(56,len(r['rows']));self.assertIsNone(r['more'])

    def test_reservations_are_subtracted_and_reads_never_write(self):
        self.pair(8,6)
        self.db.execute("INSERT INTO trade_requests(id,album_id,from_user_id,to_user_id,status) VALUES (100,'vfl',1,2,'accepted')")
        self.db.execute("INSERT INTO trades(id,legacy_trade_request_id,requester_user_id,partner_user_id,lifecycle_state) VALUES (100,100,1,2,'accepted')")
        code=all_codes('vfl')[30]
        self.db.execute("INSERT INTO trade_positions(id,trade_id,from_user_id,to_user_id,album_id,sticker_code,quantity) VALUES (100,100,2,1,'vfl',?,1)",(code,))
        self.db.execute("INSERT INTO trade_reservations(trade_id,trade_position_id,user_id,album_id,sticker_code,quantity) VALUES (100,100,2,'vfl',?,1)",(code,));self.db.commit()
        before=hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.assertEqual(5,self.results()['rows'][0]['count'])
        self.assertFalse(self.results(text=code)['rows']);self.assertFalse(self.results(text=code)['extra'])
        self.assertEqual(before,hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_legacy_sort_ignored_search_hits_rank_before_deal_size(self):
        self.pair(8,2,quantity=100)
        self.inventory(3,'vfl',all_codes('vfl')[30:36])
        q=SearchQuery.parse(MultiDict([('sort','duplicates')]))
        self.assertEqual('deal',q.sort)
        self.assertEqual([3,2],[p['id'] for p in search(self.db,1,q)['rows']])
        # SAP-02: more fulfilled search targets outrank a larger full deal.
        self.inventory(2,'vfl',[all_codes('vfl')[40]],quantity=100)
        q=SearchQuery(text=','.join([all_codes('vfl')[30],all_codes('vfl')[40]]))
        self.assertEqual([2,3],[p['id'] for p in search(self.db,1,q)['rows']])

    def test_query_defaults_and_bad_page_are_safe(self):
        q=SearchQuery.parse(MultiDict([('sort','unsupported'),('page','bad')]))
        self.assertEqual(SearchQuery(),q)
        self.assertEqual(frozenset(),SearchQuery.parse(MultiDict([('filtered','1')])).albums)
