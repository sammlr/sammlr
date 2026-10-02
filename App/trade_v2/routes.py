"""GET-only fixture routes. No command endpoints, sessions or DB services."""
from flask import Blueprint, abort, render_template
from .manual_fixtures import manual_contexts, manual_lifecycle_stub
from .fixtures import ALBUMS, PARTNERS, TOP_IDS, partner_by_slug, deal_for, top_deals

preview = Blueprint('trade_v2', __name__, url_prefix='/trade-v2',
                    static_folder='assets', static_url_path='/assets')


def page(screen, **data):
    return render_template('manual.html' if screen == 'manual' else 'preview.html', screen=screen, data=data)


@preview.get('/')
def home():
    return page('home', deals=top_deals(), partners=PARTNERS)


@preview.get('/partners')
def partners():
    return page('partners', partners=PARTNERS, albums=ALBUMS)


@preview.get('/partners/<slug>')
def partner(slug):
    item = partner_by_slug(slug)
    if item is None:
        abort(404)
    return page('partner', partner=item)


@preview.get('/deals/<slug>')
def top_detail(slug):
    item = deal_for(slug, 'TOP_SUGGESTION')
    if item is None:
        abort(404)
    return page('deal', deal=item, back='/trade-v2/', back_label='Tauschen')


@preview.get('/partners/<slug>/smartdeal')
def smartdeal(slug):
    item = deal_for(slug, 'SMARTDEAL')
    if item is None:
        abort(404)
    return page('deal', deal=item, back=f'/trade-v2/partners/{slug}', back_label=item['partner'])


@preview.get('/partners/<slug>/manual')
def manual(slug):
    item = partner_by_slug(slug)
    if item is None:
        abort(404)
    return page('manual', partner=item, origin='MANUAL', contexts=manual_contexts(item))


@preview.get('/requests/<slug>')
def waiting(slug):
    item = lifecycle_deal(slug)
    if item is None:
        abort(404)
    return page('waiting', deal=item)


@preview.get('/requests/<slug>/next')
def next_step(slug):
    item = lifecycle_deal(slug)
    if item is None:
        abort(404)
    return page('next', deal=item)


@preview.get('/requests/<slug>/amendment')
def amendment(slug):
    item = lifecycle_deal(slug)
    if item is None:
        abort(404)
    return page('amendment', deal=item)


@preview.get('/requests/<slug>/shipping')
def shipping(slug):
    item = lifecycle_deal(slug)
    if item is None:
        abort(404)
    return page('shipping', deal=item)


@preview.get('/requests/<slug>/receipt')
def receipt(slug):
    item = lifecycle_deal(slug)
    if item is None:
        abort(404)
    return page('receipt', deal=item)


@preview.get('/active')
def active():
    return page('active', deals=[deal_for(p['slug'], 'SMARTDEAL') for p in PARTNERS])


def lifecycle_deal(slug):
    if slug.startswith('manual-'):
        partner = partner_by_slug(slug.removeprefix('manual-'))
        return manual_lifecycle_stub(partner) if partner else None
    return deal_for(slug, 'TOP_SUGGESTION' if slug in TOP_IDS else 'SMARTDEAL')


@preview.get('/partners/<slug>/manual/review')
def manual_review(slug):
    item = partner_by_slug(slug)
    if item is None:
        abort(404)
    return page('manual-review', partner=item, contexts=manual_contexts(item), deal=manual_lifecycle_stub(item),
                back=f'/trade-v2/partners/{slug}/manual', back_label='Auswahl bearbeiten')
