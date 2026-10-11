"""Signed V1 resolution and final blind ratings; no client-controlled deadlines."""
import uuid
from flask import abort, request, redirect, make_response
from lifecycle_request_routes import connection, serializer, read_draft
from services.trade_lifecycle_completion import LifecycleCompletion, ready


def register_completion(shell, database_path, actor, page, csrf_token):
    def private(content):
        response = make_response(content)
        response.headers['Cache-Control'] = 'private, no-store'
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response

    def service(db):
        if not ready(db):
            abort(503)
        return LifecycleCompletion(db)

    def token(viewer, model, operation, **data):
        return serializer().dumps(dict(actor=viewer, trade=model['trade'], revision=model['revision'],
            operation=operation, key=uuid.uuid4().hex, **data))

    def signed(trade, viewer, operation):
        data = read_draft(request.form.get('token', ''), viewer)
        if data.get('trade') != trade or data.get('operation') != operation:
            abort(400)
        return data

    @shell.get('/tauschen/abschluss/<int:trade>')
    def completion(trade):
        viewer = actor()
        try:
            with connection(database_path()) as db:
                model = service(db).completion_view(trade, viewer)
        except ValueError:
            abort(404)
        for d in model['directions']:
            for p in d['problems']:
                p['token'] = token(viewer, model, 'resolve_review', sender=d['from_user_id'], problem=p['id'])
        return private(page('completion', 'Abschluss und Bewertung', model=model,
            rating_token=token(viewer, model, 'rating'), csrf=csrf_token(), step='view'))

    @shell.post('/tauschen/abschluss/<int:trade>/review')
    def resolution_review(trade):
        viewer = actor(); data = signed(trade, viewer, 'resolve_review')
        try:
            with connection(database_path()) as db:
                model = service(db).completion_view(trade, viewer)
            mode = request.form.get('mode')
            direction = next(d for d in model['directions'] if d['from_user_id']==data['sender'])
            problem = next(p for p in direction['problems'] if p['id']==data['problem'])
            if data['revision'] != model['revision'] or mode not in ('problem_accepted','after_wait') or not problem['can_accept' if mode=='problem_accepted' else 'can_close']:
                raise ValueError('Resolution not allowed')
            data.update(operation='resolve_confirm', mode=mode)
            return private(page('completion', 'Empfang endgültig abschließen', model=model, direction=direction,
                problem=problem, token=serializer().dumps(data), csrf=csrf_token(), step='confirm'))
        except (ValueError, KeyError, StopIteration):
            abort(409)

    @shell.post('/tauschen/abschluss/<int:trade>/confirm')
    def resolution_confirm(trade):
        viewer = actor(); data = signed(trade, viewer, 'resolve_confirm')
        try:
            with connection(database_path()) as db:
                service(db).resolve_problem(trade, viewer, data['sender'], data['revision'], data['problem'], data['mode'], data['key'])
        except (ValueError, KeyError):
            abort(409)
        return redirect(f'/tauschen/abschluss/{trade}', 303)

    @shell.post('/tauschen/abschluss/<int:trade>/rating')
    def rating(trade):
        viewer = actor(); data = signed(trade, viewer, 'rating')
        try:
            permitted = {'token','_csrf_token','_history_mutation_id','stars','tags'}
            if set(request.form)-permitted or any(len(request.form.getlist(k))!=1 for k in request.form if k not in ('tags','_csrf_token')):
                raise ValueError('Unexpected rating fields')
            stars = request.form.get('stars','')
            if stars not in ('1','2','3','4','5'):
                raise ValueError('Whole stars required')
            with connection(database_path()) as db:
                service(db).submit_rating(trade, viewer, data['revision'], int(stars), request.form.getlist('tags'), data['key'])
        except (ValueError, KeyError):
            abort(409)
        return redirect(f'/tauschen/abschluss/{trade}', 303)
