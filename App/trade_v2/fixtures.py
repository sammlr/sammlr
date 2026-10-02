"""Synthetic UX fixtures, never executable proposals or an optimizer.

Preselected demo pieces share one structure for all origins. No inventory,
contract type, request, reservation or capacity state is manufactured here.
"""
from copy import deepcopy

ORIGINS = ('TOP_SUGGESTION', 'SMARTDEAL', 'MANUAL')
ALBUMS = (
    ('wm26', 'WM 2026'), ('em24', 'EM 2024'), ('buli07', 'Bundesliga 07/08'),
    ('em04', 'EM 2004'), ('buli06', 'Bundesliga 06/07'), ('wm06', 'WM 2006'),
)
# Deliberately not sorted by potential: the browser must sort actual data.
SPECS = (
    ('fatima', 'Fatima', 31, 23, 6, 728, 23),
    ('luca', 'Luca', 16, 12, 3, 412, 12),
    ('karlheinz', 'Karlheinz', 84, 37, 6, 4603, 37),
    ('amadou', 'Amadou', 9, 15, 2, 830, 9),
    ('justus', 'Justus', 52, 45, 3, 1826, 45),
    ('nora', 'Nora', 28, 34, 4, 680, 28),
    ('marek', 'Marek', 25, 17, 4, 951, 17),
    ('aylin', 'Aylin', 46, 33, 5, 1230, 33),
    ('ben', 'Ben', 8, 11, 2, 205, 8),
    ('sofia', 'Sofia', 21, 26, 3, 1104, 21),
    ('jonas', 'Jonas', 14, 18, 2, 362, 14),
    ('mila', 'Mila', 35, 30, 5, 1505, 30),
)
TOP_IDS = ('fatima', 'justus', 'marek', 'luca', 'amadou')


def pieces(album_id, prefix, count, start):
    return [dict(code=f'{prefix} {start+i}', instance=1,
                 key=f'{album_id}::{prefix} {start+i}::1') for i in range(count)]


def groups(count, album_count, prefix, start, deep=False):
    # Fixture authoring only, not matching or selection against user inventory.
    counts = [count // album_count + (i < count % album_count) for i in range(album_count)]
    if deep:
        counts = [37, 4, 4]  # Exercise the existing 16 / 20 / 1 note continuation.
    return [dict(id=key, title=title, items=pieces(key, prefix, n, start))
            for (key, title), n in zip(ALBUMS, counts)]


PARTNERS = []
DEALS = {}
for i, (slug, name, for_me, from_me, albums, duplicates, size) in enumerate(SPECS):
    PARTNERS.append(dict(id=100+i, slug=slug, display_name=name,
                         for_me=for_me, from_me=from_me,
                         max_swap=min(for_me, from_me),
                         albums=[dict(id=k, title=t) for k, t in ALBUMS[:albums]],
                         total_duplicates=duplicates))
    receive = groups(size, albums, ('BRA', 'ARG', 'GER', 'ESP', 'FRA', 'POR', 'ITA', 'ENG', 'NED', 'SUI', 'CRO', 'URU')[i], 1, slug == 'justus')
    give = groups(size, albums, ('MEX', 'USA', 'CAN', 'JPN', 'KOR', 'GHA', 'SEN', 'MAR', 'TUN', 'AUS', 'NZL', 'RSA')[i], 1, slug == 'justus')
    DEALS[slug] = dict(id=f'demo-{slug}', partner_id=100+i, partner=name,
                       partner_slug=slug, origin='SMARTDEAL',
                       receive=receive, give=give, receive_count=size,
                       give_count=size, album_count=albums)


def partner_by_slug(slug):
    return next((p for p in PARTNERS if p['slug'] == slug), None)


def deal_for(slug, origin):
    if slug not in DEALS or origin not in ORIGINS:
        return None
    # MANUAL has no completed fixture: only the explicit TRADE-02 end state.
    if origin == 'MANUAL' or (origin == 'TOP_SUGGESTION' and slug not in TOP_IDS):
        return None
    deal = deepcopy(DEALS[slug])
    deal['origin'] = origin
    return deal


def top_deals():
    return [deal_for(slug, 'TOP_SUGGESTION') for slug in TOP_IDS]
