"""Authenticated read-only Trade shell; no preview state or lifecycle commands."""
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
import sqlite3

from flask import Blueprint, abort, render_template, session
from markupsafe import Markup

from services.smartdeal_planning import SmartDealPlanningService
from services.smartdeal_pairwise import SmartDealPairwiseService
from services.smartdeal_optimizer import SmartDealOptimizer


class LegacyPlanningReadAdapter:
    """Project the existing pre-V21 legacy defaults, without changing SQL storage.

    Only the three SELECT expressions absent on V20 are adapted. All eligibility,
    availability, reservation and incoming rules stay in the canonical reader.
    """
    def __init__(self, connection):
        self.connection = connection
        columns = {r['name'] for r in connection.execute('PRAGMA table_info(trade_requests)')}
        fields = {'contract_type', 'binding_created_at', 'accepted_at'}
        present = fields & columns
        if present and present != fields:
            raise ValueError('Incomplete request contract schema')
        self.legacy = not present

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def execute(self, sql, parameters=()):
        if self.legacy and 'q.contract_type' in sql:
            sql = sql.replace('q.contract_type', "'legacy' AS contract_type")
            sql = sql.replace('q.binding_created_at', 'NULL AS binding_created_at')
            sql = sql.replace('q.accepted_at', 'NULL AS accepted_at')
        return self.connection.execute(sql, parameters)


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
    inputs = SmartDealPlanningService(LegacyPlanningReadAdapter(connection)).build_pairwise_inputs(actor)
    opportunities = SmartDealPairwiseService.from_planning_inputs(inputs)
    plan = SmartDealOptimizer.optimize(inputs.subject, opportunities)
    users = {r['id']: r['username'] for r in connection.execute('SELECT id,username FROM users')}
    albums = {r['id']: r['name'] for r in connection.execute('SELECT id,name FROM albums')}
    return inputs, opportunities, plan, users, albums


def register_trade_shell(app, *, database_path, global_head, header, navigation, render_slot):
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
                                 'owned', '', can_edit_inventory=False,
                                 detail_href=href or '#', max_visible_layers=10))

    def decorated(deal, users, albums):
        return {'partner_id': deal.partner_id, 'username': users[deal.partner_id],
                'count': deal.piece_count, 'albums': [albums[a] for a in deal.involved_albums],
                'card': slot(deal.incoming_pieces[0], deal.piece_count,
                             f'/tauschen/vorschlag/{deal.partner_id}')}

    def deal_page(deal, users, albums):
        groups = []
        for side, pieces in [('Du bekommst', deal.incoming_pieces), ('Du gibst ab', deal.outgoing_pieces)]:
            for album_id in sorted({p.album_id for p in pieces}):
                group = [p for p in pieces if p.album_id == album_id]
                # Native details/summary is the interactive control, not a nested link.
                stack = str(slot(group[0], sum(p.quantity for p in group)))
                stack = stack.replace('<a class="slot ', '<span class="slot ').replace('</a>', '</span>').replace('href="#"', '')
                cards = [Markup(str(slot(p)).replace('<a class="slot ', '<span class="slot ').replace('</a>', '</span>').replace('href="#"', '')) for p in group]
                groups.append({'side': side, 'album': albums[album_id], 'count': len(group),
                               'stack': Markup(stack), 'cards': cards})
        return page('deal', f'Tausch mit {users[deal.partner_id]}',
                    deal=decorated(deal, users, albums), groups=groups)

    @shell.get('/tauschen')
    def home():
        with read_connection(database_path()) as db:
            _, _, plan, users, albums = discovery(db, actor())
            deals = [decorated(d, users, albums) for d in plan.deals[:3]]
        return page('home', 'Tauschen', deals=deals)

    @shell.get('/tauschen/sammlr')
    def partners():
        with read_connection(database_path()) as db:
            _, opportunities, _, users, albums = discovery(db, actor())
            rows = [{'id': p.partner_id, 'username': users[p.partner_id],
                     'count': p.max_equal_piece_count,
                     'albums': [albums[a] for a in p.involved_albums]}
                    for p in sorted(opportunities, key=lambda p: (-p.max_equal_piece_count, p.partner_id))]
        return page('partners', 'Alle Sammlr', partners=rows)

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
            inputs, opportunities, _, users, albums = discovery(db, actor())
            opportunity = next((p for p in opportunities if p.partner_id == partner_id), None)
            if opportunity is None or opportunity.max_equal_piece_count < 5:
                abort(404)
            # Run the unchanged optimizer on the exact selected eligible pair.
            state = replace(inputs.subject, eligible_partners=tuple(
                p for p in inputs.subject.eligible_partners if p.user_id == partner_id))
            plan = SmartDealOptimizer.optimize(state, (opportunity,))
            if not plan.deals:
                abort(404)
            return deal_page(plan.deals[0], users, albums)

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
        return page('active', 'Laufende Tausche', trades=rows)

    app.register_blueprint(shell)
