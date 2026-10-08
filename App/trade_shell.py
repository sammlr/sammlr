"""Authenticated Trade shell with explicit, schema-gated request commands."""
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
import sqlite3

from flask import Blueprint, abort, render_template, session, request
from markupsafe import Markup

from services.trade_planning_compat import LegacyPlanningReadAdapter
from services.trade_v2_domain import TradeV2Domain
from services.smartdeal_optimizer import SmartDealOptimizer


@contextmanager
def read_connection(database):
    connection = sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA query_only=ON')
    allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION,
               sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_RECURSIVE}

    def authorize(action, first, second, database_name, trigger):
        if action in allowed or (action == sqlite3.SQLITE_PRAGMA and first == 'table_info'):
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    connection.set_authorizer(authorize)
    try:
        connection.execute('BEGIN')
        yield connection
    finally:
        connection.close()


def discovery(connection, actor):
    market = TradeV2Domain(connection).market(actor)
    inputs = market.inputs
    opportunities = market.opportunities
    plan = TradeV2Domain.smartdeals(market)
    users = {r['id']: r['username'] for r in connection.execute('SELECT id,username FROM users')}
    albums = {r['id']: r['name'] for r in connection.execute('SELECT id,name FROM albums')}
    return inputs, opportunities, plan, users, albums


def register_trade_shell(app, *, database_path, global_head, header, navigation, render_slot, csrf_token):
    shell = Blueprint('trade_shell', __name__, template_folder='templates')

    def actor():
        # Existing global auth guard validates identity/account/auth_version first.
        value = session.get('user_id')
        if type(value) is not int or value <= 0:
            abort(401)
        return value

    def page(screen, title, **data):
        return render_template('trade_shell.html', screen=screen, title=title,
                               head=Markup(global_head()), header=Markup(header()),
                               navigation=Markup(navigation('tauschen')), **data)

    def slot(piece, count=1, href=None):
        return Markup(render_slot(piece.album_id, piece.sticker_code,
                                 {piece.sticker_code: {'quantity': count}}, None,
                                 'duplicate' if count > 1 else 'owned', '', can_edit_inventory=False,
                                 detail_href=href or '#', max_visible_layers=10))

    def decorated(deal, users, albums):
        return {'partner_id': deal.partner_id, 'username': users[deal.partner_id],
                'count': deal.piece_count, 'albums': [albums[a] for a in deal.involved_albums],
                'card': slot(deal.incoming_pieces[0], deal.piece_count,
                             f'/tauschen/vorschlag/{deal.partner_id}')}

    def deal_page(deal, users, albums, notice=""):
        from services.trade_lifecycle_requests import ready
        from lifecycle_request_routes import draft_token
        with read_connection(database_path()) as db:
            token = draft_token(actor(),deal.partner_id,deal.outgoing_pieces,deal.incoming_pieces,"SMARTDEAL") if ready(db) else None
        groups = []
        for side, pieces in [('Du bekommst', deal.incoming_pieces), ('Du gibst ab', deal.outgoing_pieces)]:
            for album_id in sorted({p.album_id for p in pieces}):
                group = [p for p in pieces if p.album_id == album_id]
                # Native details/summary is the interactive control, not a nested link.
                stack = str(slot(group[0], sum(p.quantity for p in group)))
                stack = stack.replace('<a class="slot ', '<span class="slot ').replace('</a>', '</span>').replace('href="#"', '')
                cards = [Markup(str(slot(p,p.quantity)).replace('<a class="slot ', '<span class="slot ').replace('</a>', '</span>').replace('href="#"', '')) for p in group]
                groups.append({'side': side, 'album': albums[album_id], 'count': sum(p.quantity for p in group),
                               'stack': Markup(stack), 'cards': cards})
        return page('deal', f'Tausch mit {users[deal.partner_id]}',
                    deal=decorated(deal, users, albums), groups=groups, notice=notice, token=token, csrf=csrf_token())

    from trade_search_routes import register_search
    register_search(shell, database_path=database_path, read_connection=read_connection,
                    actor=actor, global_head=global_head, header=header, navigation=navigation)

    @shell.get('/tauschen/sammlr/<int:partner_id>')
    def partner(partner_id):
        with read_connection(database_path()) as db:
            _, opportunities, _, users, albums = discovery(db, actor())
            match = next((p for p in opportunities if p.partner_id == partner_id), None)
            if match is None:
                abort(404)
            data = {'id': partner_id, 'username': users[partner_id],
                    'count': match.max_equal_piece_count,
                    'receive': sum(p.quantity for p in match.incoming_candidates),
                    'give': sum(p.quantity for p in match.outgoing_candidates),
                    'albums': [albums[a] for a in match.involved_albums]}
        return page('partner', data['username'], partner=data)

    @shell.get('/tauschen/vorschlag/<int:partner_id>')
    def proposal(partner_id):
        with read_connection(database_path()) as db:
            _, _, plan, users, albums = discovery(db, actor())
            deal = next((d for d in plan.deals[:3] if d.partner_id == partner_id), None)
            if deal is None:
                abort(404)
            return deal_page(deal, users, albums)

    @shell.get('/tauschen/sammlr/<int:partner_id>/smartdeal')
    def partner_deal(partner_id):
        with read_connection(database_path()) as db:
            from services.partner_trade import partner_deal as project_deal, selected_albums, change_notice
            market=TradeV2Domain(db).market(actor(), selected_albums(request.args))
            opportunity=next((p for p in market.pairs if p.partner_id==partner_id),None)
            deal=project_deal(market,opportunity)
            current=opportunity.max_equal_piece_count if opportunity else 0
            notice=change_notice(request.args,current)
            if deal is None:
                if notice:
                    return page('changed','Tausch aktualisiert',notice=notice)
                abort(404)
            users={r['id']:r['username'] for r in db.execute('SELECT id,username FROM users')}
            albums={r['id']:r['name'] for r in db.execute('SELECT id,name FROM albums')}
            return deal_page(deal, users, albums, notice)

    @shell.get('/tauschen/laufend')
    def active():
        user = actor()
        with read_connection(database_path()) as db:
            rows = [dict(r) for r in db.execute('''
                SELECT q.id,q.status,u.username
                FROM trade_requests q JOIN users u ON u.id=
                    CASE WHEN q.from_user_id=? THEN q.to_user_id ELSE q.from_user_id END
                WHERE (q.from_user_id=? OR q.to_user_id=?) AND q.status IN ('open','accepted')
                ORDER BY q.id DESC
            ''', (user, user, user))]
        from services.trade_lifecycle_requests import ready, LifecycleRequests
        from lifecycle_request_routes import connection
        with read_connection(database_path()) as db:
            enabled = ready(db)
        lifecycle = []
        if enabled:
            with connection(database_path()) as db:
                from lifecycle_acceptance_routes import decorate
                lifecycle = decorate(db,LifecycleRequests(db).view(user),user)
        return page('active', 'Laufende Tausche', trades=rows, lifecycle=lifecycle,viewer=user,csrf=csrf_token())

    from profile_trade import register_manual
    register_manual(shell, database_path, actor, csrf_token)
    from lifecycle_request_routes import register_requests
    register_requests(shell,database_path,actor,page,csrf_token)
    from lifecycle_acceptance_routes import register_acceptance
    register_acceptance(shell,database_path,actor,page,csrf_token)
    from lifecycle_preparation_routes import register_preparation
    register_preparation(shell,database_path,actor,page,csrf_token)
    app.register_blueprint(shell)
