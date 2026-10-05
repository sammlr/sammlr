"""Trade-v2 preferences: synthetic SQL only, protected DBs are never opened."""
from contextlib import closing
from dataclasses import replace
from itertools import product
from pathlib import Path
import hashlib
import random
import sqlite3
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'App'))
from App.Database.migration_runner import migrate, rollback, current_version
from tests.test_integration01_trade_shell import fixture
from services.trade_v2_domain import TradeV2Domain
from services.trade_v2_preferences import TradeV2Preferences
from services.trade_v2_rules import SAME_ALBUM_ONLY as SAME, CROSS_ALBUM_ALLOWED as CROSS, balance_groups
from services.smartdeal_optimizer import SmartDealPiece
from services._smartdeal_flow import PartnerEdges, allocate
from services._trade_v2_flow import ScopedSubsetNetwork
from services.runtime_operations import validate_database, TRADE_V2_COMPATIBLE_SCHEMA_VERSIONS


class TradeV2PreferencesTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='integration02a-',dir='/private/tmp')
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'synthetic.db'
        fixture(self.path,1)
        self.db=sqlite3.connect(self.path)
        self.db.row_factory=sqlite3.Row
        self.addCleanup(self.db.close)
        # Two users, three enabled albums. Build catalog-valid disjoint inventories.
        for user in (1,2):
            for album in ('em24','wm26'):
                self.db.execute('INSERT INTO user_albums(user_id,album_id,trade_pool_enabled) VALUES (?,?,1)',(user,album))
        self.db.execute('DELETE FROM stickers')
        self.db.commit()
        self.domain=TradeV2Domain(self.db)

    def populate(self, own, partner):
        from services.albums import all_codes
        self.db.execute('DELETE FROM stickers')
        for album in ('vfl','em24','wm26'):
            codes=all_codes(album)
            for user,start,count in [(1,0,own.get(album,0)),(2,30,partner.get(album,0))]:
                for code in codes[start:start+count]:
                    self.db.execute('INSERT INTO stickers(user_id,album_id,sticker_code,quantity,duplicates) VALUES (?,?,?,2,1)',(user,album,code))
        self.db.commit()

    def modes(self, own, partner):
        migrate(self.db,22)
        preferences=TradeV2Preferences(self.db)
        for user,values in [(1,own),(2,partner)]:
            for album,value in values.items():preferences.set_mode(user,album,value)
        self.db.commit()

    def maximum(self):
        market=self.domain.market(1)
        return market.pairs[0].max_equal_piece_count

    def test_a_b_c_d_bilateral_modes_and_missing_default(self):
        self.populate({'vfl':7},{'wm26':7})
        self.assertEqual(0,self.maximum()) # V20 absence is SAME, without any write.
        for a,b,wanted in [(SAME,SAME,0),(CROSS,SAME,0),(SAME,CROSS,0),(CROSS,CROSS,7)]:
            with self.subTest(a=a,b=b):
                self.modes(dict.fromkeys(('vfl','wm26'),a),dict.fromkeys(('vfl','wm26'),b))
                market=self.domain.market(1)
                self.assertEqual(wanted,market.pairs[0].max_equal_piece_count)
                plan=self.domain.smartdeals(market)
                self.assertEqual(wanted,sum(d.piece_count for d in plan.deals))

    def test_mixed_groups_cannot_use_restricted_surplus(self):
        self.populate({'vfl':8,'em24':7},{'vfl':2,'wm26':6})
        self.modes({'vfl':SAME,'em24':CROSS,'wm26':CROSS},dict.fromkeys(('vfl','em24','wm26'),CROSS))
        market=self.domain.market(1)
        self.assertEqual(8,market.pairs[0].max_equal_piece_count)
        plan=self.domain.smartdeals(market)
        self.assertEqual(8,plan.deals[0].piece_count)
        self.assertTrue(self.domain.validate_deal(market,2,plan.deals[0].outgoing_pieces,plan.deals[0].incoming_pieces,balanced=True))
        self.assertEqual(2,sum(p.album_id=='vfl' for p in plan.deals[0].outgoing_pieces))

    def test_pool_intersection_and_selected_albums_remove_both_directions(self):
        self.populate({'vfl':6,'em24':5},{'vfl':6,'em24':5})
        self.assertEqual(11,self.maximum())
        market=self.domain.market(1,{'vfl'})
        self.assertEqual(6,market.pairs[0].max_equal_piece_count)
        self.assertTrue(all(p.album_id=='vfl' for p in market.pairs[0].incoming_candidates+market.pairs[0].outgoing_candidates))
        for user in (1,2):
            self.db.execute("UPDATE user_albums SET trade_pool_enabled=0 WHERE user_id=? AND album_id='em24'",(user,));self.db.commit()
            self.assertEqual(6,self.maximum())
        self.assertFalse(self.domain.market(1,set()).pairs)

    def test_manual_asymmetric_and_invalid_deals(self):
        self.populate({'vfl':3},{'vfl':3})
        market=self.domain.market(1);pair=market.pairs[0]
        pieces=lambda seq:tuple(SmartDealPiece(p.album_id,p.sticker_code,1) for p in seq)
        give=pieces(pair.outgoing_candidates);receive=pieces(pair.incoming_candidates)
        self.assertTrue(self.domain.validate_deal(market,2,give,receive[:2]))
        for g,r in [(give[:2],receive),(give,receive+(receive[0],)),((),receive),(give,(replace(receive[0],quantity=2),)),(give,(SmartDealPiece('vfl','249'),))]:
            with self.assertRaises(ValueError):self.domain.validate_deal(market,2,g,r)
        with self.assertRaises(ValueError):self.domain.validate_deal(market,999,give,receive)
        with self.assertRaises(ValueError):self.domain.validate_deal(market,2,give,receive[:2],balanced=True)

    def test_manual_cross_album_rejected_until_bilateral_consent(self):
        self.populate({'vfl':3},{'em24':2})
        market=self.domain.market(1);pair=market.pairs[0]
        g=tuple(SmartDealPiece(p.album_id,p.sticker_code) for p in pair.outgoing_candidates)
        r=tuple(SmartDealPiece(p.album_id,p.sticker_code) for p in pair.incoming_candidates)
        with self.assertRaises(ValueError):self.domain.validate_deal(market,2,g,r)
        self.modes(dict.fromkeys(('vfl','em24'),CROSS),dict.fromkeys(('vfl','em24'),CROSS))
        self.assertTrue(self.domain.validate_deal(self.domain.market(1),2,g,r))

    def test_migration_preserves_every_existing_value_and_defaults(self):
        self.populate({'vfl':5},{'vfl':5})
        self.db.execute("UPDATE users SET favorite_album_id='em24' WHERE id=1")
        self.db.execute("UPDATE user_albums SET trade_pool_enabled=0 WHERE user_id=2 AND album_id='wm26'")
        self.db.commit();migrate(self.db,21)
        tables=[r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name <> 'schema_migrations'")]
        columns={t:[r[1] for r in self.db.execute(f'PRAGMA table_info({t})')] for t in tables}
        before={t:[tuple(r) for r in self.db.execute(f'SELECT * FROM {t} ORDER BY rowid')] for t in tables}
        migrate(self.db,22)
        after={t:[tuple(r) for r in self.db.execute(f'SELECT {",".join(columns[t])} FROM {t} ORDER BY rowid')] for t in tables}
        self.assertEqual(before,after)
        self.assertEqual({SAME},{r[0] for r in self.db.execute('SELECT cross_album_mode FROM user_albums')})
        self.assertEqual((),migrate(self.db,22))
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE user_albums SET cross_album_mode='invalid'")
        self.db.rollback()
        self.assertEqual('ok',self.db.execute('PRAGMA integrity_check').fetchone()[0])
        self.assertEqual([],self.db.execute('PRAGMA foreign_key_check').fetchall())
        validate_database(self.path,compatible_versions=TRADE_V2_COMPATIBLE_SCHEMA_VERSIONS)
        rollback(self.db,21)
        self.assertEqual(21,current_version(self.db))
        self.assertEqual(before,{t:[tuple(r) for r in self.db.execute(f'SELECT * FROM {t} ORDER BY rowid')] for t in tables})

    def test_explicit_cross_prevents_silent_backout_and_hook_does_not_commit(self):
        migrate(self.db,22)
        preferences=TradeV2Preferences(self.db)
        preferences.set_mode(1,'vfl',CROSS)
        self.db.rollback()
        self.assertEqual(SAME,preferences.read([1])[(1,'vfl')])
        preferences.set_mode(1,'vfl',CROSS);self.db.commit()
        with self.assertRaises(sqlite3.IntegrityError):rollback(self.db,21)
        self.db.rollback()
        self.assertEqual(22,current_version(self.db))
        self.assertEqual(CROSS,preferences.read([1])[(1,'vfl')])
        with self.assertRaises(ValueError):preferences.set_mode(99,'vfl',SAME)

    def test_read_only_no_schema_or_data_mutation_and_legacy_unchanged(self):
        self.populate({'vfl':5},{'vfl':5})
        before=hashlib.sha256(self.path.read_bytes()).hexdigest()
        with closing(sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True)) as db:
            db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
            market=TradeV2Domain(db).market(1)
            self.assertEqual(5,TradeV2Domain.smartdeals(market).deals[0].piece_count)
            with self.assertRaises(ValueError):TradeV2Preferences(db).set_mode(1,'vfl',CROSS)
        self.assertEqual(before,hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_all_cross_reuses_legacy_optimizer_without_ranking_change(self):
        from services.smartdeal_pairwise import SmartDealPairwiseService
        from services.smartdeal_optimizer import SmartDealOptimizer
        self.populate({'vfl':8,'em24':7},{'vfl':2,'wm26':6})
        self.modes(dict.fromkeys(('vfl','em24','wm26'),CROSS),dict.fromkeys(('vfl','em24','wm26'),CROSS))
        market=self.domain.market(1)
        legacy=SmartDealPairwiseService.from_planning_inputs(market.inputs)
        self.assertEqual(SmartDealOptimizer.optimize(market.inputs.subject,legacy).deals,
                         self.domain.smartdeals(market).deals)

    def test_unknown_preference_fails_closed_and_default_is_central(self):
        self.assertEqual((('a',),('b',)),balance_groups(['a','b'],{},{}))
        with self.assertRaises(ValueError):balance_groups(['a'],{'a':'unknown'},{})


class ScopedFlowOracleTests(unittest.TestCase):
    def test_exhaustive_binary_allocations_against_independent_oracle(self):
        # No minimum-five constraint in this oracle: inspect the feasibility kernel.
        # 60 deterministic graphs, all partner lower/exact size combinations.
        rng=random.Random(20261004)
        keys=(('a','1'),('a','2'),('b','1'))
        checks=0
        for _ in range(60):
            partners=tuple(PartnerEdges(pid,tuple(k for k in keys if rng.randrange(2)),tuple(k for k in keys if rng.randrange(2)),(('a',),('b',))) for pid in (2,3))
            supply={k:rng.randint(1,2) for k in keys}
            options=[]
            for p in partners:
                local=[]
                for outs in product((0,1),repeat=len(p.outgoing)):
                    for ins in product((0,1),repeat=len(p.incoming)):
                        o=tuple(k for k,on in zip(p.outgoing,outs) if on);i=tuple(k for k,on in zip(p.incoming,ins) if on)
                        if all(sum(k[0]==a for k in o)==sum(k[0]==a for k in i) for a in ('a','b')):local.append((o,i))
                options.append(local)
            for requested in product(range(3),repeat=2):
                sizes={p.partner_id:(n,n) for p,n in zip(partners,requested)}
                expected=any(all(len(choice[j][0])==requested[j] for j in range(2)) and all(sum(k in c[0] for c in choice)<=supply[k] and sum(k in c[1] for c in choice)<=1 for k in keys) for choice in product(*options))
                counters=dict(flow_checks=0,cache_hits=0)
                network=ScopedSubsetNetwork(partners,supply,counters)
                self.assertEqual(expected,network.feasible(sizes,(sum(requested),sum(requested))))
                checks+=1
            for trial in range(6):
                sizes={p.partner_id:(rng.randrange(2),rng.randrange(2,4)) for p in partners}
                total=(rng.randrange(2),rng.randrange(2,5))
                fixed={}
                for p in partners:
                    for direction,sequence in [('out',p.outgoing),('in',p.incoming)]:
                        for k in sequence:
                            if rng.randrange(3)==0:
                                value=rng.randrange(2)
                                fixed[(direction,p.partner_id,k)]=(value,value)
                def acceptable(choice):
                    if not total[0]<=sum(len(c[0]) for c in choice)<=total[1]:return False
                    if not all(sizes[p.partner_id][0]<=len(c[0])<=sizes[p.partner_id][1] for p,c in zip(partners,choice)):return False
                    if not all(sum(k in c[0] for c in choice)<=supply[k] and sum(k in c[1] for c in choice)<=1 for k in keys):return False
                    for p,c in zip(partners,choice):
                        for direction,seq in [('out',c[0]),('in',c[1])]:
                            for k in keys:
                                bounds=fixed.get((direction,p.partner_id,k))
                                if bounds and int(k in seq)!=bounds[0]:return False
                    return True
                expected=any(acceptable(choice) for choice in product(*options))
                network=ScopedSubsetNetwork(partners,supply,dict(flow_checks=0,cache_hits=0))
                self.assertEqual(expected,network.feasible(sizes,total,fixed))
                checks+=1
        self.assertEqual(900,checks)

    def test_global_optimizer_keeps_resources_and_exact_group_balance(self):
        keys=tuple((a,str(i)) for a in ('a','b') for i in range(4))
        partners=(PartnerEdges(2,keys,keys,(('a',),('b',))),PartnerEdges(3,keys,keys,(('a',),('b',))))
        allocations,_=allocate(dict.fromkeys(keys,2),partners)
        self.assertEqual(8,sum(len(a.incoming) for a in allocations))
        self.assertEqual(1,len(allocations)) # Existing efficiency objective, unchanged.
        self.assertEqual(2,allocations[0].partner_id) # Existing deterministic tie-break.
        for a in allocations:
            for album in ('a','b'):self.assertEqual(sum(k[0]==album for k in a.incoming),sum(k[0]==album for k in a.outgoing))
