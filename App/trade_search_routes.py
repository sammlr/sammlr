"""SAP controller; authenticated actor and read-only connection supplied by the shell."""
from flask import render_template, request
from markupsafe import Markup
from services.trade_search import SearchQuery, search


def register_search(blueprint, *, database_path, read_connection, actor, global_head, header, navigation):
    @blueprint.get('/tauschen')
    @blueprint.get('/tauschen/sammlr')
    def partners():
        with read_connection(database_path()) as db:
            result = search(db, actor(), SearchQuery.parse(request.args))
        return render_template('trade_search.html', **result,
                               head=Markup(global_head()), header=Markup(header()),
                               navigation=Markup(navigation('tauschen')))
