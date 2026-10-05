"""Read-only SAP query projection; all eligibility and capacities come from TradeV2Domain."""
from dataclasses import dataclass
from datetime import datetime, timezone
import math
from urllib.parse import urlencode

from services.trade_v2_domain import TradeV2Domain
from services.trade_v2_rules import maximum_equal
from services.partner_trade import participating_album_count, profile_url
from services.trade_search_intent import resolve_search, code_key


@dataclass(frozen=True)
class SearchQuery:
    albums: frozenset | None = None
    text: str = ''
    sort: str = 'deal'
    page: int = 1

    @classmethod
    def parse(cls, args):
        try:
            page = max(1, int(args.get('page', '1')))
        except ValueError:
            page = 1
        return cls(frozenset(args.getlist('album')) if args.get('filtered') == '1' else None,
                   args.get('q', '').strip()[:240],
                   'deal', page)


def activity_key(value):
    try:
        date = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return date.replace(tzinfo=date.tzinfo or timezone.utc).timestamp()
    except (ValueError, TypeError, AttributeError, OverflowError):
        return 0


def search(db, actor, query):
    available = tuple((r['album_id'], r['name']) for r in db.execute('''
        SELECT ua.album_id,a.name FROM user_albums ua JOIN albums a ON a.id=ua.album_id
        WHERE ua.user_id=? AND ua.trade_pool_enabled=1 ORDER BY a.name,ua.album_id
    ''', (actor,)))
    selected = frozenset(a for a, _ in available)
    if query.albums is not None:
        selected &= query.albums
    market = TradeV2Domain(db).market(actor, selected)
    favorite = db.execute('SELECT favorite_album_id FROM users WHERE id=?', (actor,)).fetchone()[0]
    identities = {r['id']:r for r in db.execute('''
        SELECT u.id,u.username,a.last_active_at FROM users u
        LEFT JOIN user_activity a ON a.user_id=u.id
    ''')}
    intent=resolve_search(query.text,[(a,n) for a,n in available if a in selected],
                          market.inputs.subject.album_context,market.inputs.subject.needs,
                          (r['username'] for r in identities.values()))
    concrete=intent.kind=='stickers'
    targeted=intent.kind in {'stickers','album'}
    wanted=intent.targets
    inventories = {p.user_id:p for p in market.inputs.partners}
    regular, extra = [], []
    for pair in market.pairs:
        identity = identities[pair.partner_id]
        if intent.kind=='collector' and intent.collector not in identity['username'].casefold():
            continue
        feasible = TradeV2Domain.receivable_candidates(pair)
        feasible_keys = {(p.album_id,p.sticker_code) for p in feasible}
        permitted = {a for group in pair.balance_groups for a in group}
        supply = tuple(p for p in inventories[pair.partner_id].outgoing_supply if p.album_id in permitted)
        hits = feasible_keys & wanted
        possessed = {(p.album_id,p.sticker_code) for p in supply} & wanted
        if targeted and not possessed:
            continue
        hit_count=maximum_equal((p.album_id for p in pair.outgoing_candidates),
                                (a for a,c in hits),pair.balance_groups)
        # Favorite count is achievable, not inflated by unmatched restricted surplus.
        favorite_count = maximum_equal((p.album_id for p in pair.outgoing_candidates),
            (p.album_id for p in feasible if p.album_id == favorite), pair.balance_groups)
        row = dict(id=pair.partner_id, username=identity['username'], count=pair.max_equal_piece_count,
                   profile_url=profile_url(identity['username'],selected,pair.max_equal_piece_count),
                   album_count=participating_album_count(market,pair),
                   duplicates=sum(p.quantity for p in supply), relevant=len(feasible_keys),
                   hits=hit_count, target_count=len(wanted),
                   matched=', '.join(sorted({c for a,c in (hits or possessed)})))
        row['_rank'] = (-hit_count if targeted else 0, -row['count'],
                        -favorite_count, -row['relevant'], -activity_key(identity['last_active_at']), pair.partner_id)
        if row['count'] > 0 and (not targeted or hit_count):
            regular.append(row)
        elif concrete:
            extra.append(row)
    regular.sort(key=lambda r:r['_rank'])
    extra.sort(key=lambda r:(-len(r['matched'].split(', ')),r['id']))
    total = len(regular)+len(extra)
    page = min(query.page,max(1,math.ceil(total/50)))
    end = page*50
    params = [('filtered','1')]+[('album',a) for a in sorted(selected)]+[('q',query.text),('page',str(page+1))]
    return dict(albums=available, selected=selected, query=query, concrete=concrete,
                rows=regular[:end], extra=extra[:max(0,end-len(regular))], total=total,
                search_kind=intent.kind, ambiguous=intent.ambiguous, target_count=len(wanted),
                more='/tauschen?'+urlencode(params) if end<total else None)
