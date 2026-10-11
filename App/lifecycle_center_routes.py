"""Authenticated center projections; all mutations remain in L01–08 routes."""
from flask import abort, request, make_response, redirect
from lifecycle_request_routes import connection
from services.lifecycle_center import LifecycleCenter, LABELS, EMPTY


def register_center(shell, database_path, actor, page):
    def render(section=None):
        viewer=actor()
        raw=request.args.get('page','1')
        if not raw.isascii() or not raw.isdigit() or len(raw)>6:abort(400)
        from trade_shell import read_connection
        from services.trade_lifecycle_completion import ready
        with read_connection(database_path()) as db:
            if not ready(db):
                return redirect('/sammlung')
        try:
            with connection(database_path()) as db:
                model=LifecycleCenter(db).view(viewer,section,int(raw))
        except ValueError:
            abort(400)
        response=make_response(page('center',LABELS.get(section,'Deine Sammlr-Zentrale'),model=model,
            labels=LABELS,empty=EMPTY,center_navigation=True))
        response.headers['Cache-Control']='private, no-store'
        response.headers['Referrer-Policy']='no-referrer'
        return response

    @shell.get('/zentrale')
    def center():return render()

    @shell.get('/zentrale/<section>')
    def center_list(section):
        if section not in LABELS:abort(404)
        return render(section)
