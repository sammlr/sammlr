"""Acceptance and explicitly confirmed counteroffers in the existing request UI."""
import uuid
from flask import abort,request,redirect
from services.trade_lifecycle_requests import LifecycleRequests
from services.trade_lifecycle_acceptance import LifecycleAcceptance,ready
from lifecycle_request_routes import connection,serializer,read_draft


def decorate(db,rows,actor):
    enabled=ready(db)
    for q in rows:
        q['acceptance_enabled']=enabled
        from services.trade_lifecycle_preparation import ready as preparation_ready
        q['preparation_enabled']=preparation_ready(db)
        if enabled and q['status']=='open' and actor==q['partner_user_id']:
            q['accept_token']=serializer().dumps(dict(actor=actor,trade=q['trade_id'],revision=q['revision_id'],
                key=uuid.uuid4().hex,operation='accept'))
    return rows


def register_acceptance(shell,database_path,actor,page,csrf_token):
    def current(db,viewer,trade,notice=''):
        rows=decorate(db,LifecycleRequests(db).view(viewer,trade),viewer)
        return page('request','Tauschanfrage',lifecycle=rows,viewer=viewer,csrf=csrf_token(),notice=notice)

    @shell.post('/tauschen/anfragen/<int:trade>/accept')
    def accept(trade):
        viewer=actor();data=read_draft(request.form.get('token',''),viewer)
        if data.get('trade')!=trade or data.get('operation')!='accept':abort(400)
        with connection(database_path()) as db:
            if not ready(db):abort(503)
            try:result=LifecycleAcceptance(db).accept(trade,viewer,data['revision'],data['key'])
            except ValueError:abort(403)
            if result['status']=='not_possible':
                return current(db,viewer,trade,'Dieser Tausch ist so nicht mehr vollständig möglich. Das ursprüngliche Angebot bleibt unverändert.'),409
        return redirect(f'/tauschen/anfragen/{trade}',code=303)

    @shell.post('/tauschen/anfragen/<int:trade>/counter-preview')
    def counter_preview(trade):
        viewer=actor()
        try:revision=int(request.form['revision'])
        except (KeyError,ValueError):abort(400)
        with connection(database_path()) as db:
            if not ready(db):abort(503)
            service=LifecycleAcceptance(db)
            try:result=service.preview_counter(trade,viewer,revision)
            except ValueError:
                try:return current(db,viewer,trade,'Aktuell ist kein neues zulässiges Gegenangebot möglich.'),409
                except ValueError:abort(403)
            if result['status']=='expired':return redirect(f'/tauschen/anfragen/{trade}',code=303)
            rows=service.view(viewer,trade)
        proposal={k:result[k] for k in ('give','receive')}
        token=serializer().dumps(dict(actor=viewer,trade=trade,revision=revision,key=uuid.uuid4().hex,
            operation='counter',proposal=proposal))
        return page('counter_review','Gegenangebot prüfen',proposal=proposal,token=token,trade=trade,
            username=rows[0]['sender'],csrf=csrf_token())

    @shell.post('/tauschen/anfragen/<int:trade>/counter')
    def counter(trade):
        viewer=actor();data=read_draft(request.form.get('token',''),viewer)
        if data.get('trade')!=trade or data.get('operation')!='counter':abort(400)
        with connection(database_path()) as db:
            if not ready(db):abort(503)
            try:LifecycleAcceptance(db).counter(trade,viewer,data['revision'],data['key'],data['proposal'])
            except ValueError:
                try:return current(db,viewer,trade,'Das Gegenangebot ist nicht mehr unverändert verfügbar oder dein Anfragelimit ist erreicht. Bitte prüfe die Anfrage erneut.'),409
                except ValueError:abort(403)
        return redirect(f'/tauschen/anfragen/{trade}',code=303)
