"""Authenticated preparation commands and private, noncacheable photo delivery."""
from pathlib import Path
import uuid
from flask import abort,current_app,redirect,request,send_from_directory
from lifecycle_request_routes import connection,serializer,read_draft
from services.trade_lifecycle_preparation import LifecyclePreparation,ready,REASONS
from services.lifecycle_photos import MAX_BYTES


def register_preparation(shell,database_path,actor,page,csrf_token):
    def storage():
        return Path(current_app.config.get('LIFECYCLE_PHOTO_DIR',Path(__file__).parent/'uploads'/'lifecycle_control'))

    @shell.get('/tauschen/vorbereitung/<int:trade>')
    def preparation(trade):
        viewer=actor()
        with connection(database_path()) as db:
            if not ready(db):abort(503)
            try:model=LifecyclePreparation(db).view(trade,viewer)
            except ValueError:abort(404)
        def token(action):
            return serializer().dumps(dict(actor=viewer,trade=trade,revision=model['revision'],basis=model['basis'],key=uuid.uuid4().hex,action=action))
        return page('preparation','Tausch vorbereiten',model=model,token=token,csrf=csrf_token(),reasons=REASONS)

    @shell.post('/tauschen/vorbereitung/<int:trade>/<action>')
    def preparation_command(trade,action):
        viewer=actor();signed=read_draft(request.form.get('token',''),viewer)
        if signed.get('trade')!=trade or signed.get('action')!=action:abort(400)
        # No actor/owner field from the form can select another participant.
        data={}
        try:
            if action=='problem':
                data={'reason':request.form.get('reason')}
            elif action in ('remove_photo','reduction_approve','reduction_reject'):
                field='photo' if action=='remove_photo' else 'proposal';data[field]=int(request.form[field])
            elif action=='missing':
                data={k:int(request.form[k]) for k in ('position','quantity')}
            with connection(database_path()) as db:
                if not ready(db):abort(503)
                service=LifecyclePreparation(db)
                if action=='upload':
                    upload=request.files.get('photo')
                    if upload is None:abort(400)
                    service.upload(trade,viewer,signed['revision'],signed['basis'],signed['key'],upload.stream.read(MAX_BYTES+1),storage())
                else:
                    if action=='reduction_propose':
                        model=service.view(trade,viewer);positions=[]
                        for p in model['positions']:
                            n=int(request.form.get('quantity_'+str(p['id']),p['quantity']))
                            if n<0 or n>p['quantity']:raise ValueError('Nur kleinere Mengen zulässig')
                            if n:positions.append([p[k] for k in ('from_user_id','to_user_id','album_id','sticker_code')]+[n])
                        data={'positions':positions}
                    service.command(trade,viewer,signed['revision'],signed['basis'],signed['key'],action,data)
        except (ValueError,KeyError):
            return page('changed','Vorbereitung nicht geändert',notice='Diese Aktion passt nicht mehr zur aktuellen Vertrags- oder Fotobasis. Bitte öffne die Vorbereitung erneut und prüfe Mengen, Fotos und offene Änderungen.'),409
        return redirect(f'/tauschen/vorbereitung/{trade}',code=303)

    @shell.get('/tauschen/vorbereitung/<int:trade>/fotos/<int:photo>')
    def preparation_photo(trade,photo):
        viewer=actor()
        with connection(database_path()) as db:
            if not ready(db):abort(503)
            try:p=LifecyclePreparation(db).photo(trade,viewer,photo)
            except ValueError:abort(404)
        response=send_from_directory(storage(),p['storage_name'],mimetype=p['mime'],conditional=False,etag=False,max_age=0)
        response.headers['Cache-Control']='private, no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Content-Security-Policy']="default-src 'none'; sandbox"
        return response
