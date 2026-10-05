"""Partner-specific projection of the existing central market and SmartDeal path."""
from dataclasses import replace
from urllib.parse import urlencode, quote
from services.smartdeal_optimizer import SmartDealOptimizer
from services.trade_v2_domain import TradeV2Domain


def selected_albums(args):
    return frozenset(args.getlist('trade_album')) if args.get('trade_context') == '1' else None


def context_query(albums):
    if albums is None:
        return ''
    return urlencode([('trade_context','1')]+[('trade_album',a) for a in sorted(albums)])


def profile_url(username, albums=None, seen=None):
    query=context_query(albums)
    if seen is not None:query+=(('&' if query else '')+urlencode({'trade_seen':seen}))
    return '/profil/'+quote(username,safe='')+('?' + query if query else '')


def partner_deal(market, pair):
    if pair is None or pair.max_equal_piece_count < 5:
        return None
    state=replace(market.inputs.subject,eligible_partners=tuple(
        p for p in market.inputs.subject.eligible_partners if p.user_id == pair.partner_id))
    deals=SmartDealOptimizer.optimize(state,(pair,)).deals
    return deals[0] if deals else None


def participating_album_count(market, pair):
    deal=partner_deal(market,pair)
    if deal:
        return len(deal.involved_albums)
    # Sub-minimum manual capacity: show the albums in one exact maximal balanced
    # projection, not every theoretically relevant album. No SmartDeal below five.
    albums=set()
    for group in pair.balance_groups:
        give=[p for p in pair.outgoing_candidates if p.album_id in group]
        receive=[p for p in pair.incoming_candidates if p.album_id in group]
        size=min(len(give),len(receive))
        albums.update(p.album_id for p in give[:size]+receive[:size])
    return len(albums)


def manual_context(market,pair,names,username):
    feasible=TradeV2Domain.receivable_candidates(pair)
    live_groups=[g for g in pair.balance_groups if any(p.album_id in g for p in feasible)]
    albums=[]
    for album in sorted({a for g in live_groups for a in g}):
        cross=any(album in g and len(g)>1 for g in live_groups)
        def pieces(sequence):
            return [dict(key=p.album_id+'::'+p.sticker_code,code=p.sticker_code,
                         instance=1,supply=p.available_quantity,need=p.quantity)
                    for p in sequence if p.album_id==album]
        albums.append(dict(id=album,title=names[album],me=dict(tradeEnabled=True,crossAlbum=cross),
                           partner=dict(tradeEnabled=True,crossAlbum=cross),
                           receive=pieces(feasible),give=pieces(pair.outgoing_candidates)))
    return dict(partner_id=pair.partner_id,partner=username,profile_slug=str(pair.partner_id),albums=albums)


def change_notice(args,current):
    try:
        previous=int(args.get('trade_seen',''))
    except (ValueError,TypeError):
        return ''
    if previous < 0 or previous == current:return ''
    if current == 0:return 'Die Tauschmöglichkeit hat sich geändert. Aktuell ist kein Tausch möglich.'
    return f'Die Tauschmöglichkeit hat sich geändert. Aktuell sind {current} Sticker möglich.'
