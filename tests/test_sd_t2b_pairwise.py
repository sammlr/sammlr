"""SD-T2b pure capacities and canonical batch-reader integration."""
from dataclasses import FrozenInstanceError, fields, replace
import hashlib
from pathlib import Path
import sqlite3
from contextlib import closing
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'App'))
from services.smartdeal_pairwise import SmartDealPairwiseService
from services.smartdeal_planning import (
    PairwisePlanningInputs, PartnerPlanningInventory, PlanningPiece,
    PlanningPartner, PlanningState, SmartDealPlanningService,
)
from tests import test_sd_t2a_planning_state as fixtures


def pieces(album, prefix, count, membership, quantity=1):
    return tuple(PlanningPiece(album, f'{prefix}{i:03}', membership, quantity) for i in range(count))


def inputs(outgoing=3, incoming=5, partners=(2,), albums=('vfl',)):
    give=tuple(p for a in albums for p in pieces(a,'G',outgoing,10,3))
    get=tuple(p for a in albums for p in pieces(a,'R',incoming,10))
    subject=PlanningState(1,get,get,give,(),tuple(PlanningPartner(p,albums) for p in partners),(),())
    others=tuple(PartnerPlanningInventory(p,
        tuple(replace(x,user_album_id=p*10,quantity=1) for x in give),
        tuple(replace(x,user_album_id=p*10,quantity=4) for x in get)) for p in partners)
    return PairwisePlanningInputs(subject,others)


class PairwiseContractTests(unittest.TestCase):
    def calculate(self,value):
        return SmartDealPairwiseService.from_planning_inputs(value)

    def test_three_out_five_in_retains_all_candidates(self):
        result=self.calculate(inputs())[0]
        self.assertEqual((3,5,3),(len(result.outgoing_candidates),len(result.incoming_candidates),result.max_equal_piece_count))

    def test_global_23_against_28_is_one_opportunity(self):
        value=inputs();subject=value.subject;partner=value.partners[0]
        outgoing=tuple(p for a,n in (('wm26',11),('em24',8),('buli07',4)) for p in pieces(a,'G',n,10))
        incoming=tuple(p for a,n in (('wm26',7),('em04',9),('buli09',12)) for p in pieces(a,'R',n,20))
        albums=('buli07','buli09','em04','em24','wm26')
        value=PairwisePlanningInputs(replace(subject,outgoing_supply=outgoing,needs=incoming,
            eligible_partners=(PlanningPartner(2,albums),)),
            (replace(partner,needs=outgoing,outgoing_supply=incoming),))
        result=self.calculate(value)
        self.assertEqual(1,len(result));self.assertEqual(23,result[0].max_equal_piece_count)
        self.assertEqual(28,len(result[0].incoming_candidates));self.assertEqual(albums,result[0].involved_albums)

    def test_isolated_partners_reuse_same_scarce_candidate(self):
        value=inputs(1,1,(3,2))
        result=self.calculate(value)
        self.assertEqual([2,3],[p.partner_id for p in result])
        self.assertEqual(result[0].outgoing_candidates[0].sticker_code,result[1].outgoing_candidates[0].sticker_code)
        self.assertEqual([1,1],[p.max_equal_piece_count for p in result])

    def test_supply_three_is_capped_by_binary_receiver_need(self):
        candidate=self.calculate(inputs(1,1))[0].outgoing_candidates[0]
        self.assertEqual(3,candidate.available_quantity);self.assertEqual(1,candidate.quantity)
        self.assertEqual((10,20),(candidate.giver_user_album_id,candidate.receiver_user_album_id))

    def test_one_way_is_not_an_opportunity(self):
        for out,inc in ((0,3),(3,0),(0,0)):
            self.assertEqual((),self.calculate(inputs(out,inc)))

    def test_one_by_one_is_kept_without_minimum(self):
        self.assertEqual(1,self.calculate(inputs(1,1))[0].max_equal_piece_count)

    def test_no_top_five_limit(self):
        self.assertEqual(7,len(self.calculate(inputs(1,1,tuple(range(2,9))))))

    def test_partner_id_order_is_not_size_ranking(self):
        value=inputs(4,4,(3,2));small=replace(value.partners[1],needs=value.partners[1].needs[:1])
        result=self.calculate(replace(value,partners=(value.partners[0],small)))
        self.assertEqual([(2,1),(3,4)],[(p.partner_id,p.max_equal_piece_count) for p in result])

    def test_same_codes_in_different_albums_are_distinct(self):
        result=self.calculate(inputs(1,1,albums=('em24','vfl')))[0]
        self.assertEqual(2,result.max_equal_piece_count);self.assertEqual(('em24','vfl'),result.involved_albums)

    def test_no_noneligible_partner_or_album(self):
        value=inputs(1,1,(2,3),('em24','vfl'))
        subject=replace(value.subject,eligible_partners=(PlanningPartner(2,('vfl',)),))
        result=self.calculate(replace(value,subject=subject))
        self.assertEqual([2],[p.partner_id for p in result]);self.assertEqual(('vfl',),result[0].involved_albums)

    def test_immutable_and_deterministic_under_input_permutation(self):
        value=inputs(3,5,(3,2),('vfl','em24'));expected=self.calculate(value)
        shuffled=replace(value,subject=replace(value.subject,
            needs=tuple(reversed(value.subject.needs)),outgoing_supply=tuple(reversed(value.subject.outgoing_supply)),
            eligible_partners=tuple(reversed(value.subject.eligible_partners))),partners=tuple(reversed(value.partners)))
        self.assertEqual(expected,self.calculate(shuffled))
        with self.assertRaises(FrozenInstanceError):expected[0].partner_id=99
        self.assertFalse({'score','rank','rating','distance','shipping_score'} & {f.name for f in fields(expected[0])})

    def test_missing_partner_input_fails_closed(self):
        with self.assertRaises(ValueError):self.calculate(replace(inputs(),partners=()))

    def test_multicopy_need_is_not_silently_introduced(self):
        value=inputs();other=value.partners[0]
        other=replace(other,needs=tuple(replace(p,quantity=2) for p in other.needs))
        with self.assertRaises(ValueError):self.calculate(replace(value,partners=(other,)))


class PairwiseIntegrationTests(unittest.TestCase):
    setUp=fixtures.PlanningStateTests.setUp
    quantity=fixtures.PlanningStateTests.quantity
    bind=fixtures.PlanningStateTests.bind

    def planner(self):
        return SmartDealPlanningService(self.db,lambda a:fixtures.CATALOG[a],lambda:fixtures.NOW)

    def calculate(self):
        return SmartDealPairwiseService(self.planner()).build(1)

    def test_batch_partner_pieces_equal_individual_canonical_states(self):
        batch=self.planner().build_pairwise_inputs(1)
        self.assertEqual(self.planner().build(1),batch.subject)
        for partner in batch.partners:
            full=self.planner().build(partner.user_id)
            albums=next(p.album_ids for p in batch.subject.eligible_partners if p.user_id==partner.user_id)
            self.assertEqual(tuple(p for p in full.needs if p.album_id in albums),partner.needs)
            self.assertEqual(tuple(p for p in full.outgoing_supply if p.album_id in albums),partner.outgoing_supply)

    def test_committed_incoming_and_reserved_supply_are_excluded(self):
        self.bind()
        self.assertEqual((),self.calculate())
        self.quantity(1,'vfl','1',1)
        self.assertEqual((),self.calculate())

    def test_partner_committed_need_is_respected(self):
        self.bind('smartdeal_v1','open')
        batch=self.planner().build_pairwise_inputs(1)
        other=next(p for p in batch.partners if p.user_id==2)
        self.assertNotIn(('vfl','1'),{(p.album_id,p.sticker_code) for p in other.needs})
        self.assertEqual((),self.calculate())

    def test_partner_supply_fully_reserved_is_not_available(self):
        self.bind();self.bind()
        batch=self.planner().build_pairwise_inputs(1)
        other=next(p for p in batch.partners if p.user_id==2)
        self.assertNotIn(('vfl','2'),{(p.album_id,p.sticker_code) for p in other.outgoing_supply})

    def test_expired_v1_does_not_block_either_direction(self):
        self.bind('smartdeal_v1','open','2026-09-09 12:00:00')
        result=self.calculate()
        self.assertEqual([(2,1)],[(p.partner_id,p.max_equal_piece_count) for p in result])

    def test_blocked_and_pool_disabled_partner_absent(self):
        self.db.execute('INSERT INTO blocks(blocker_user_id,blocked_user_id) VALUES (2,1)')
        self.assertEqual((),self.calculate())
        self.db.execute('DELETE FROM blocks')
        self.db.execute('UPDATE user_albums SET trade_pool_enabled=0 WHERE user_id=2')
        self.assertEqual((),self.calculate())

    def test_no_writes_and_pure_calculation_uses_zero_queries(self):
        self.db.commit();digest=hashlib.sha256(self.path.read_bytes()).hexdigest();changes=self.db.total_changes
        batch=self.planner().build_pairwise_inputs(1)
        sql=[];self.db.set_trace_callback(sql.append)
        result=SmartDealPairwiseService.from_planning_inputs(batch)
        self.db.set_trace_callback(None)
        self.assertEqual([],sql);self.assertTrue(result)
        self.assertEqual(changes,self.db.total_changes);self.assertEqual(digest,hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_query_count_constant_for_one_hundred_partners(self):
        counts=[]
        for size in (0,100):
            for i in range(size):
                user=self.db.execute("INSERT INTO users(username,password,name) VALUES (?, 'fixture-only', 'Synthetic')",(f'pairwise_{i}',)).lastrowid
                self.db.execute("INSERT INTO user_albums(user_id,album_id,trade_pool_enabled) VALUES (?, 'vfl',1)",(user,))
                self.quantity(user,'vfl','2',2)
            self.db.commit();sql=[];self.db.set_trace_callback(sql.append)
            result=self.calculate();self.db.set_trace_callback(None);counts.append(len(sql))
        self.assertEqual(counts[0],counts[1]);self.assertLessEqual(counts[1],21)
        self.assertEqual(101,len(result))

    def test_batch_snapshot_survives_concurrent_partner_write(self):
        self.db.commit();self.db.execute('PRAGMA journal_mode=WAL');fired=[]
        def trace(sql):
            if sql.startswith('SELECT user_id,album_id,sticker_code,quantity') and not fired:
                fired.append(True)
                with closing(sqlite3.connect(self.path)) as writer:
                    writer.execute("DELETE FROM stickers WHERE user_id=2 AND album_id='vfl' AND sticker_code='2'")
                    writer.commit()
        self.db.set_trace_callback(trace);result=self.calculate();self.db.set_trace_callback(None)
        self.assertTrue(fired);self.assertEqual(1,len(result));self.assertEqual((),self.calculate())
