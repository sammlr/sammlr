"""Single pure Trade-v2 balance policy shared by planning and validation."""
from collections import Counter

SAME_ALBUM_ONLY = 'SAME_ALBUM_ONLY'
CROSS_ALBUM_ALLOWED = 'CROSS_ALBUM_ALLOWED'


def mode(value):
    if value is None:
        return SAME_ALBUM_ONLY
    if value not in (SAME_ALBUM_ONLY, CROSS_ALBUM_ALLOWED):
        raise ValueError('Unknown cross-album preference')
    return value


def balance_groups(albums, own, partner):
    restricted, pooled = [], []
    for album in sorted(set(albums)):
        if mode(own.get(album)) == mode(partner.get(album)) == CROSS_ALBUM_ALLOWED:
            pooled.append(album)
        else:
            restricted.append((album,))
    return tuple(restricted + ([tuple(pooled)] if pooled else []))


def group_totals(outgoing_albums, incoming_albums, groups):
    give, receive = Counter(outgoing_albums), Counter(incoming_albums)
    flat = [a for group in groups for a in group]
    if any(not group for group in groups) or len(flat) != len(set(flat)):
        raise ValueError('Balance groups must be a disjoint partition')
    if (give.keys() | receive.keys()) - set(flat):
        raise ValueError('Piece outside permitted balance groups')
    return tuple((sum(give[a] for a in group), sum(receive[a] for a in group)) for group in groups)


def maximum_equal(outgoing_albums, incoming_albums, groups):
    return sum(min(g, r) for g, r in group_totals(outgoing_albums, incoming_albums, groups))


def valid_balance(outgoing_albums, incoming_albums, groups, *, equal=False):
    return all(r == g if equal else r <= g for g, r in group_totals(outgoing_albums, incoming_albums, groups))
