"""Pure AC24 package identity. No authorization, revalidation or persistence.

A digest is only a lookup key. Compare identity objects (complete canonical
content) for semantic equality, including when digest strings happen to match.
"""
from dataclasses import dataclass, field
import hashlib
import json
from typing import TYPE_CHECKING

from services.trade_contracts import SMARTDEAL_V1_CONTRACT

if TYPE_CHECKING:
    from services.smartdeal_optimizer import SmartDealCandidate


class SmartDealIdentityError(ValueError):
    """Malformed canonical participant or V1 piece representation."""


def _user_id(value):
    if type(value) is not int or value <= 0:
        raise SmartDealIdentityError('Canonical positive integer user ID required')
    return value


def _positions(values):
    quantities = {}
    for value in values:
        if not isinstance(value, (tuple, list)) or len(value) != 3:
            raise SmartDealIdentityError('Expected album, sticker code and quantity')
        album, code, quantity = value
        if type(album) is not str or type(code) is not str:
            raise SmartDealIdentityError('Canonical album/code strings required')
        if type(quantity) is not int or quantity <= 0:
            raise SmartDealIdentityError('Positive integer piece quantity required')
        key = (album, code)
        quantities[key] = quantities.get(key, 0) + quantity
        if quantities[key] > 1:
            raise SmartDealIdentityError('V1 receiver need is at most one per album/sticker')
    return tuple((album, code, quantity) for (album, code), quantity in sorted(quantities.items()))


@dataclass(frozen=True)
class SmartDealOpportunityIdentity:
    """Canonical full content is equality; SHA-256 is never equality alone.

    Direct construction requires numerical low/high order. Use from_view for
    either viewing direction. Rank, time and occurrence ID are deliberately absent.
    This value does not assert balance, top eligibility or current executability.
    """
    low_user_id: int
    high_user_id: int
    low_to_high: tuple[tuple[str, str, int], ...]
    high_to_low: tuple[tuple[str, str, int], ...]
    contract_type: str = field(default=SMARTDEAL_V1_CONTRACT, init=False)
    canonical_payload: str = field(init=False, compare=False, repr=False)
    digest: str = field(init=False, compare=False)

    def __post_init__(self):
        if _user_id(self.low_user_id) >= _user_id(self.high_user_id):
            raise SmartDealIdentityError('Distinct participants in numerical ASC order required')
        low = _positions(self.low_to_high)
        high = _positions(self.high_to_low)
        payload = json.dumps({
            'contract_type': self.contract_type,
            'participants': [self.low_user_id, self.high_user_id],
            'low_to_high': low,
            'high_to_low': high,
        }, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
        try:
            encoded = payload.encode('utf-8')
        except UnicodeEncodeError as error:
            raise SmartDealIdentityError('Canonical identities must be valid UTF-8 text') from error
        object.__setattr__(self, 'low_to_high', low)
        object.__setattr__(self, 'high_to_low', high)
        object.__setattr__(self, 'canonical_payload', payload)
        object.__setattr__(self, 'digest', hashlib.sha256(encoded).hexdigest())

    @property
    def lookup_key(self):
        """Full 256-bit digest with domain/algorithm label; not a GO token."""
        return f'{SMARTDEAL_V1_CONTRACT}:sha256:{self.digest}'


class SmartDealIdentityService:
    @staticmethod
    def from_view(user_id, partner_id, outgoing_pieces, incoming_pieces):
        """Map each delivered piece to its supplier before canonicalization.

        Consume canonical piece objects with album_id/sticker_code/quantity.
        No normalization, live-state lookup, ranking, truncation or balancing.
        """
        user_id, partner_id = _user_id(user_id), _user_id(partner_id)
        try:
            outgoing = tuple((p.album_id, p.sticker_code, p.quantity) for p in outgoing_pieces)
            incoming = tuple((p.album_id, p.sticker_code, p.quantity) for p in incoming_pieces)
        except (AttributeError, TypeError) as error:
            raise SmartDealIdentityError('Canonical piece objects required') from error
        if user_id < partner_id:
            return SmartDealOpportunityIdentity(user_id, partner_id, outgoing, incoming)
        return SmartDealOpportunityIdentity(partner_id, user_id, incoming, outgoing)

    @staticmethod
    def from_deal(user_id: int, deal: 'SmartDealCandidate') -> SmartDealOpportunityIdentity:
        """Additive T3b adapter: identify the final package without recomputation.

        Caller supplies the owner of the T3b plan. The identity cannot authenticate
        that owner; later GO validation must establish actor and executability.
        """
        return SmartDealIdentityService.from_view(
            user_id, deal.partner_id, deal.outgoing_pieces, deal.incoming_pieces,
        )
