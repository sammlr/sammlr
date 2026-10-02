"""Disposable V2 visual fixture. No database or domain dependencies."""
from flask import abort, current_app, render_template

ALBUMS = (
    ('WM 2026', ('ARG 17', 'ARG 42', 'BRA 8', 'BRA 31', 'GER 12', 'GER 64')),
    ('EM 2024', ('ESP 18', 'ESP 55', 'FRA 23', 'ITA 9')),
    ('Bundesliga 07/08', ('BVB 12', 'HSV 8', 'VFB 21', 'BRE 16')),
    ('EM 2004', ('POR 7', 'GRE 12', 'NED 18')),
    ('Bundesliga 06/07', ('FCB 4', 'S04 11', 'HSV 20')),
    ('WM 2006', ('ITA 10', 'FRA 7', 'GER 18')),
)
GIVE = (
    ('WM 2026', ('ARG 3', 'BRA 12', 'GER 7', 'ESP 22', 'FRA 19', 'POR 6')),
    ('EM 2024', ('GER 10', 'ENG 11', 'NED 9', 'SUI 4')),
    ('Bundesliga 07/08', ('FCB 9', 'S04 7', 'BVB 18', 'VFB 6')),
    ('EM 2004', ('ESP 8', 'ITA 14', 'FRA 3')),
    ('Bundesliga 06/07', ('BVB 2', 'BRE 10', 'VFB 17')),
    ('WM 2006', ('BRA 9', 'ARG 11', 'POR 17')),
)
DEALS = (('Fatima', 23, 6), ('Justus', 17, 4), ('Marek', 12, 3), ('Luca', 9, 2), ('Amadou', 6, 2))
PARTNERS = (('Fatima', '4,8', 31, 29, 'sie', 6), ('Justus', '4,9', 37, 24, 'ihn', 5), ('Marek', '4,7', 18, 15, 'ihn', 3))


# Explicit fixture quantities, not an optimizer or a domain-derived package.
PACK_COUNTS = ((6, 4, 4, 3, 3, 3), (6, 4, 4, 3), (6, 4, 2), (6, 3), (4, 2))
PACKS = tuple(dict(name=name, size=size, albums=albums,
                  incoming=tuple((ALBUMS[i][0], ALBUMS[i][1][:count]) for i, count in enumerate(counts)),
                  outgoing=tuple((GIVE[i][0], GIVE[i][1][:count]) for i, count in enumerate(counts)))
              for (name, size, albums), counts in zip(DEALS, PACK_COUNTS))


def register_trade_visual_preview(app):
    if app.config.get('SAMMLR_ENV') not in {'development', 'testing'}:
        return

    def preview(partners_page=False, journey_page=False):
        if current_app.config.get('SAMMLR_ENV') not in {'development', 'testing'}:
            abort(404)
        if journey_page:
            return render_template('sammlrpax_journey_v1.html', incoming=ALBUMS, outgoing=GIVE)
        return render_template('trade_visual_preview.html', packs=PACKS,
                               partners=PARTNERS, partners_page=partners_page)

    app.add_url_rule('/preview/trades-v1', 'trade_visual_preview', preview, methods=['GET'])
    app.add_url_rule('/preview/trades-v1/partners', 'trade_visual_preview', preview,
                     defaults={'partners_page': True}, methods=['GET'])

    app.add_url_rule('/preview/sammlrpax-journey-v1', 'trade_visual_preview', preview,
                     defaults={'journey_page': True}, methods=['GET'])
