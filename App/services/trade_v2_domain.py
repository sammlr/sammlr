"""Server-side Trade-v2 market and concrete-deal validation on canonical inventory."""
from dataclasses import dataclass, replace

from services.smartdeal_planning import SmartDealPlanningService, PairwisePlanningInputs
from services.smartdeal_pairwise import PairwiseOpportunity, PairwiseCandidate
from services.smartdeal_optimizer import SmartDealOptimizer
from services.trade_planning_compat import LegacyPlanningReadAdapter
from services.trade_v2_preferences import TradeV2Preferences
from services.trade_v2_rules import balance_groups, maximum_equal, valid_balance


@dataclass(frozen=True)
class TradeV2Market:
    inputs: PairwisePlanningInputs
    pairs: tuple[PairwiseOpportunity, ...]  # Includes zero capacity for concrete SAP searches.

    @property
    def opportunities(self):
        return tuple(p for p in self.pairs if p.max_equal_piece_count > 0)


class TradeV2Domain:
    def __init__(self, connection):
        self.db = connection

    def market(self, actor, selected_albums=None, *, exclude_revision=None):
        own_transaction = not self.db.in_transaction
        if own_transaction:
            self.db.execute('BEGIN')
        try:
            inputs = SmartDealPlanningService(LegacyPlanningReadAdapter(self.db)).build_pairwise_inputs(actor)
            from services.lifecycle_planning import project
            inputs = project(self.db, inputs, exclude_revision)
            allowed = {a.album_id for a in inputs.subject.album_context}
            if selected_albums is not None:
                allowed &= set(selected_albums)
            subset = lambda pieces: tuple(p for p in pieces if p.album_id in allowed)
            subject = inputs.subject
            roster = tuple(replace(p, album_ids=tuple(a for a in p.album_ids if a in allowed))
                           for p in subject.eligible_partners if set(p.album_ids) & allowed)
            subject = replace(subject, missing=subset(subject.missing), needs=subset(subject.needs),
                              outgoing_supply=subset(subject.outgoing_supply),
                              incoming_committed_needs=subset(subject.incoming_committed_needs),
                              album_context=subset(subject.album_context), reservation_context=subset(subject.reservation_context),
                              eligible_partners=roster)
            ids = {p.user_id for p in roster}
            inventories = tuple(replace(p, needs=subset(p.needs), outgoing_supply=subset(p.outgoing_supply))
                                for p in inputs.partners if p.user_id in ids)
            inputs = PairwisePlanningInputs(subject, inventories)
            preferences = TradeV2Preferences(self.db).read(ids | {actor})
            by_id = {p.user_id: p for p in inventories}
            pairs = []
            for partner in roster:
                groups = balance_groups(partner.album_ids,
                    {a: preferences.get((actor, a)) for a in partner.album_ids},
                    {a: preferences.get((partner.user_id, a)) for a in partner.album_ids})
                inventory = by_id[partner.user_id]
                outgoing = self._candidates(subject.outgoing_supply, inventory.needs, partner.album_ids)
                incoming = self._candidates(inventory.outgoing_supply, subject.needs, partner.album_ids)
                maximum = maximum_equal((p.album_id for p in outgoing for _ in range(p.quantity)), (p.album_id for p in incoming for _ in range(p.quantity)), groups)
                pairs.append(PairwiseOpportunity(partner.user_id, outgoing, incoming, maximum,
                    tuple(sorted({p.album_id for p in outgoing + incoming})), groups))
            return TradeV2Market(inputs, tuple(pairs))
        finally:
            if own_transaction:
                self.db.rollback()

    @staticmethod
    def _candidates(supply, needs, albums):
        demand = {(p.album_id,p.sticker_code):p for p in needs}
        return tuple(sorted((PairwiseCandidate(p.album_id,p.sticker_code,min(p.quantity,n.quantity),
            p.quantity,p.user_album_id,n.user_album_id) for p in supply
            if p.album_id in albums and (n := demand.get((p.album_id,p.sticker_code))) is not None),
            key=lambda p:(p.album_id,p.sticker_code)))

    @staticmethod
    def receivable_candidates(pair):
        """Every candidate that can participate in at least one valid bilateral deal."""
        available = set()
        for group in pair.balance_groups:
            if any(p.album_id in group for p in pair.outgoing_candidates):
                available.update(group)
        return tuple(p for p in pair.incoming_candidates if p.album_id in available)

    @staticmethod
    def smartdeals(market):
        return SmartDealOptimizer.optimize(market.inputs.subject, market.opportunities, quantities=True)

    @staticmethod
    def validate_deal(market, partner_id, give, receive, *, balanced=False):
        """Validate from the proposer's perspective; voluntary Give>Receive is allowed.

        Use a fresh server-read market at a later binding boundary. No binding here.
        """
        pair = next((p for p in market.pairs if p.partner_id == partner_id), None)
        if pair is None:
            raise ValueError('Partner outside current permitted trade space')
        def validate(pieces, candidates):
            limits = {(p.album_id, p.sticker_code): p.quantity for p in candidates}
            keys, albums = set(), []
            for p in pieces:
                key = (p.album_id, p.sticker_code)
                if key in keys or type(p.quantity) is not int or not 0 < p.quantity <= limits.get(key, 0):
                    raise ValueError('Unavailable, duplicate, non-relevant or invalid piece')
                keys.add(key)
                albums.extend([p.album_id] * p.quantity)
            if not albums:
                raise ValueError('Both directions must contain relevant pieces')
            return albums
        outgoing = validate(give, pair.outgoing_candidates)
        incoming = validate(receive, pair.incoming_candidates)
        if not valid_balance(outgoing, incoming, pair.balance_groups, equal=balanced):
            raise ValueError('Receive exceeds permitted Give balance')
        return True

    def lifecycle_availability(self, actor, album_id, code):
        """Read quantity availability through the shared lifecycle foundation."""
        from services.trade_lifecycle_foundation import lifecycle_availability
        own_transaction = not self.db.in_transaction
        if own_transaction:
            self.db.execute('BEGIN')
        try:
            return lifecycle_availability(self.db, actor, album_id, code)
        finally:
            if own_transaction:
                self.db.rollback()
