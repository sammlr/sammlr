"""Productive V1 request entry points; the global auth/CSRF guards still apply."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import uuid
from flask import abort, current_app, redirect, request
from itsdangerous import URLSafeTimedSerializer, BadSignature
from services.smartdeal_optimizer import SmartDealPiece
from services.trade_lifecycle_requests import LifecycleRequests, ready


@contextmanager
def connection(path):
    # mode=rw fails closed when the configured database does not already exist.
    db = sqlite3.connect(Path(path).resolve().as_uri()+'?mode=rw',uri=True,timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        if not ready(db):
            abort(503,description='Tauschanfragen sind auf diesem Datenbankstand noch nicht freigeschaltet.')
        yield db
    finally:
        db.close()


def serializer():
    return URLSafeTimedSerializer(current_app.secret_key,salt='lifecycle-v1-request-review')


def draft_token(actor, partner, give, receive, origin):
    return serializer().dumps(dict(actor=actor,partner=partner,origin=origin,key=uuid.uuid4().hex,
        give=[(p.album_id,p.sticker_code,p.quantity) for p in give],
        receive=[(p.album_id,p.sticker_code,p.quantity) for p in receive]))


def read_draft(token, actor):
    try:
        data = serializer().loads(token,max_age=3600)
        if data['actor'] != actor:
            abort(403)
        return data
    except (BadSignature,KeyError,TypeError):
        abort(400,description='Die Vorschau ist abgelaufen. Bitte prüfe den Deal erneut.')


def register_requests(shell,database_path,actor,page,csrf_token):
    @shell.get('/tauschen/anfragen/entwurf')
    def review():
        viewer = actor()
        token = request.args.get('token','')
        data = read_draft(token,viewer)
        with connection(database_path()) as db:
            LifecycleRequests(db).expire()
            from services.trade_v2_domain import TradeV2Domain
            try:
                TradeV2Domain.validate_deal(TradeV2Domain(db).market(viewer),data['partner'],
                    tuple(SmartDealPiece(*p) for p in data['give']),tuple(SmartDealPiece(*p) for p in data['receive']),
                    balanced=data['origin']=='SMARTDEAL')
            except ValueError:
                abort(409,description='Dieser Deal ist nicht mehr verfügbar. Bitte wähle erneut.')
            username = db.execute('SELECT username FROM users WHERE id=?',(data['partner'],)).fetchone()[0]
        return page('request_review','Tauschanfrage prüfen',draft=data,token=token,username=username,csrf=csrf_token())

    @shell.post('/tauschen/anfragen')
    def send():
        viewer = actor()
        data = read_draft(request.form.get('token',''),viewer)
        with connection(database_path()) as db:
            try:
                trade = LifecycleRequests(db).create(viewer,data['partner'],
                    tuple(SmartDealPiece(*p) for p in data['give']),tuple(SmartDealPiece(*p) for p in data['receive']),
                    data['key'],origin=data['origin'])
            except ValueError:
                return page('changed','Anfrage nicht gesendet',notice='Der Deal ist nicht mehr verfügbar oder das Anfragelimit ist erreicht. Bitte prüfe deine offenen Anfragen und Auswahl.'),409
        return redirect(f'/tauschen/anfragen/{trade}',code=303)

    @shell.get('/tauschen/anfragen/<int:trade_id>')
    def detail(trade_id):
        viewer = actor()
        with connection(database_path()) as db:
            try:
                rows = LifecycleRequests(db).view(viewer,trade_id)
            except ValueError:
                abort(404)
        return page('request','Tauschanfrage',lifecycle=rows,viewer=viewer,csrf=csrf_token())

    @shell.post('/tauschen/anfragen/<int:trade_id>/<action>')
    def transition(trade_id,action):
        viewer = actor()
        if action not in ('withdrawn','rejected'):
            abort(404)
        with connection(database_path()) as db:
            try:
                LifecycleRequests(db).transition(trade_id,viewer,action)
            except ValueError:
                abort(403)
        return redirect(f'/tauschen/anfragen/{trade_id}',code=303)
