"""Synthetic display fixtures, not a matching service or executable trade payload."""
from collections import Counter


def album(key, title, codes):
    instances = Counter()
    items = []
    for code in codes:
        instances[code] += 1
        items.append(dict(code=code, instance=instances[code],
                          key=f'{key}::{code}::{instances[code]}'))
    return dict(id=key, title=title, items=items)


def candidate(key, partner, receive, give):
    return dict(id=key, partner=partner, receive=receive, give=give,
                receive_count=sum(len(a['items']) for a in receive),
                give_count=sum(len(a['items']) for a in give),
                album_count=len({a['id'] for a in receive + give}))


TITLES = ('WM 2026', 'EM 2024', 'Bundesliga 07/08', 'EM 2004', 'Bundesliga 06/07', 'WM 2006')
INCOMING = (('ARG 17', 'ARG 42', 'BRA 8', 'BRA 31', 'GER 12', 'GER 64'),
            ('ESP 18', 'ESP 55', 'FRA 23', 'ITA 9'),
            ('BVB 12', 'HSV 8', 'VFB 21', 'BRE 16'),
            ('POR 7', 'GRE 12', 'NED 18'), ('FCB 4', 'S04 11', 'HSV 20'),
            ('ITA 10', 'FRA 7', 'GER 18'))
OUTGOING = (('ARG 3', 'BRA 12', 'GER 7', 'ESP 22', 'FRA 19', 'POR 6'),
            ('GER 10', 'ENG 11', 'NED 9', 'SUI 4'),
            ('FCB 9', 'S04 7', 'BVB 18', 'VFB 6'),
            ('ESP 8', 'ITA 14', 'FRA 3'), ('BVB 2', 'BRE 10', 'VFB 17'),
            ('BRA 9', 'ARG 11', 'POR 17'))


def groups(source, counts):
    return [album(f'album-{i}', TITLES[i], source[i][:n]) for i, n in enumerate(counts)]


CANDIDATES = (
    candidate('fatima', 'Fatima', groups(INCOMING, (6, 4, 4, 3, 3, 3)), groups(OUTGOING, (6, 4, 4, 3, 3, 3))),
    candidate('justus', 'Justus',
              [album('wm26', 'WM 2026', [f'ARG {n}' for n in range(1, 38)]),
               album('em24', 'EM 2024', ['GER 9', 'ENG 7', 'FRA 4', 'ITA 6']),
               album('buli', 'Bundesliga 07/08', ['BVB 3', 'HSV 6', 'VFB 8', 'BRE 9'])],
              [album('wm26', 'WM 2026', ['BRA 1', 'BRA 1'] + [f'BRA {n}' for n in range(2, 37)]),
               album('em24', 'EM 2024', ['GER 2', 'ENG 3', 'FRA 5', 'ITA 7']),
               album('buli', 'Bundesliga 07/08', ['FCB 2', 'S04 3', 'BVB 5', 'VFB 7'])]),
    candidate('marek', 'Marek', groups(INCOMING, (6, 4, 4, 3)), groups(OUTGOING, (6, 4, 4, 3))),
    candidate('luca', 'Luca', groups(INCOMING, (6, 4, 2)), groups(OUTGOING, (6, 4, 2))),
    candidate('amadou', 'Amadou', groups(INCOMING, (6, 3)), groups(OUTGOING, (6, 3))),
)
