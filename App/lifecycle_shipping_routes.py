"""Two-step manual confirmation. No client quantities, clock or evidence source."""
import uuid
from flask import abort,request,redirect,make_response
from lifecycle_request_routes import connection,serializer,read_draft
from services.trade_lifecycle_shipping import LifecycleShipping,ready


def register_shipping(shell,database_path,actor,page,csrf_token):
    def service(db):
        if not ready(db):abort(503)
        return LifecycleShipping(db)
    def private(content):
        response=make_response(content);response.headers['Cache-Control']='private, no-store';response.headers['Referrer-Policy']='no-referrer';return response
    @shell.get('/tauschen/versand/<int:trade>')
    def shipping(trade):
        viewer=actor()
        try:
            with connection(database_path()) as db:model=service(db).shipping_view(trade,viewer)
        except ValueError:abort(404)
        signed=serializer().dumps(dict(actor=viewer,trade=trade,revision=model['revision'],operation='shipping_review',key=uuid.uuid4().hex))
        return private(page('shipping','Versand',model=model,token=signed,csrf=csrf_token(),confirm=False))
    @shell.post('/tauschen/versand/<int:trade>/review')
    def shipping_review(trade):
        viewer=actor();signed=read_draft(request.form.get('token',''),viewer)
        if signed.get('trade')!=trade or signed.get('operation')!='shipping_review':abort(400)
        try:
            with connection(database_path()) as db:model=service(db).shipping_view(trade,viewer)
            if model['revision']!=signed['revision']:raise ValueError('Stale revision')
        except ValueError:abort(409)
        if next(d for d in model['directions'] if d['sender']==viewer)['state']=='sent':return redirect(f'/tauschen/versand/{trade}',303)
        signed['operation']='shipping_confirm'
        return private(page('shipping','Versand bestätigen',model=model,token=serializer().dumps(signed),csrf=csrf_token(),confirm=True))
    @shell.post('/tauschen/versand/<int:trade>/confirm')
    def shipping_confirm(trade):
        viewer=actor();signed=read_draft(request.form.get('token',''),viewer)
        if signed.get('trade')!=trade or signed.get('operation')!='shipping_confirm':abort(400)
        try:
            with connection(database_path()) as db:service(db).send_direction(trade,viewer,signed['revision'],signed['key'])
        except (ValueError,KeyError):
            return private((page('changed','Versand nicht bestätigt',notice='Die Vertragsbasis oder der gebundene Bestand ist nicht mehr aktuell. Bitte prüfe den Tausch erneut.'),409))
        return redirect(f'/tauschen/versand/{trade}',303)
