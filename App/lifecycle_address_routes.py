"""Private address responses. No address payload in redirects, events or logs."""
import uuid
from flask import abort,request,redirect,jsonify,make_response
from lifecycle_request_routes import connection,serializer,read_draft
from services.trade_lifecycle_addresses import LifecycleAddresses,ready,FIELDS


def register_addresses(shell,database_path,actor,page,csrf_token):
    def private(response):
        result=make_response(response);result.headers['Cache-Control']='private, no-store'
        result.headers['Referrer-Policy']='no-referrer'
        return result

    def service(db):
        if not ready(db):abort(503)
        return LifecycleAddresses(db)

    def token(viewer,operation,**data):
        return serializer().dumps(dict(actor=viewer,operation=operation,key=uuid.uuid4().hex,**data))

    @shell.get('/tauschen/adressbuch')
    def address_book():
        viewer=actor()
        try:back=int(request.args['trade']) if request.args.get('trade') else None
        except ValueError:abort(400)
        with connection(database_path()) as db:
            domain=service(db);entries=domain.book(viewer)
            if back:
                try:domain.view_address(back,viewer)
                except ValueError:abort(404)
        def command(operation,entry=None):
            return token(viewer,operation,address=entry['id'] if entry else None,version=entry['version'] if entry else None,back=back)
        return private(page('address_book','Meine Versandadressen',entries=entries,command=command,fields=FIELDS,csrf=csrf_token(),back=back))

    @shell.post('/tauschen/adressbuch/<operation>')
    def address_book_command(operation):
        viewer=actor();signed=read_draft(request.form.get('token',''),viewer)
        if signed.get('operation')!=operation or operation not in ('create','edit','delete','default'):abort(400)
        try:
            with connection(database_path()) as db:
                service(db).book_command(viewer,signed['key'],operation,signed.get('address'),signed.get('version'),dict(request.form))
        except ValueError:
            return private((page('changed','Adresse nicht geändert',notice='Bitte prüfe alle Pflichtfelder, den zweistelligen Ländercode und ob die Adresse noch aktuell ist.'),409))
        return redirect(f"/tauschen/adressen/{signed['back']}" if signed.get('back') else '/tauschen/adressbuch',code=303)

    @shell.get('/tauschen/adressen/<int:trade>')
    def trade_addresses(trade):
        viewer=actor()
        try:
            with connection(database_path()) as db:model=service(db).view_address(trade,viewer)
        except ValueError:abort(404)
        def confirm(entry):
            return token(viewer,'confirm',trade=trade,revision=model['revision'],basis=model['basis'],generation=model['generation'],address=entry['id'],version=entry['version'])
        return private(page('addresses','Versandadresse',model=model,confirm=confirm,csrf=csrf_token()))

    @shell.post('/tauschen/adressen/<int:trade>/confirm')
    def confirm_address(trade):
        viewer=actor();signed=read_draft(request.form.get('token',''),viewer)
        if signed.get('operation')!='confirm' or signed.get('trade')!=trade:abort(400)
        try:
            with connection(database_path()) as db:
                service(db).confirm(trade,viewer,signed['revision'],signed['basis'],signed['generation'],signed['address'],signed['version'],signed['key'])
        except (ValueError,KeyError):
            return private((page('changed','Adresse nicht bestätigt',notice='Die Auswahl oder Vertragsbasis ist nicht mehr aktuell. Bitte prüfe den Tausch und deine Adresse erneut.'),409))
        return redirect(f'/tauschen/adressen/{trade}',code=303)

    @shell.get('/tauschen/adressen/<int:trade>/snapshots/<int:snapshot>')
    def address_snapshot(trade,snapshot):
        viewer=actor()
        try:
            with connection(database_path()) as db:data=service(db).snapshot(trade,viewer,snapshot)
        except ValueError:abort(404)
        return private(jsonify(data))
