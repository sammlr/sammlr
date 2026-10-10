"""Authenticated, signed two-step receipt inspection without client expectations."""
import uuid
from flask import abort, request, redirect, make_response
from lifecycle_request_routes import connection, serializer, read_draft
from services.trade_lifecycle_receipts import LifecycleReceipts, COUNTS, ready


def register_receipts(shell, database_path, actor, page, csrf_token):
    def service(db):
        if not ready(db):
            abort(503)
        return LifecycleReceipts(db)

    def private(content):
        response = make_response(content)
        response.headers['Cache-Control'] = 'private, no-store'
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response

    def token(viewer, model, operation, **data):
        return serializer().dumps(dict(actor=viewer, trade=model['trade'], revision=model['revision'],
            operation=operation, key=uuid.uuid4().hex, **data))

    def signed(trade, viewer, operation):
        data = read_draft(request.form.get('token', ''), viewer)
        if data.get('trade') != trade or data.get('operation') != operation:
            abort(400)
        return data

    @shell.get('/tauschen/empfang/<int:trade>')
    def receipts(trade):
        viewer = actor()
        try:
            with connection(database_path()) as db:
                model = service(db).receipt_view(trade, viewer)
        except ValueError:
            abort(404)
        for d in model['directions']:
            d['token'] = token(viewer, model, 'receipt_review', sender=d['from_user_id'])
            d['non_arrival_token'] = token(viewer, model, 'non_arrival', sender=d['from_user_id'])
            for p in d['problems']:
                p['token'] = token(viewer, model, 'receipt_response', sender=d['from_user_id'], problem=p['id'])
        return private(page('receipts', 'Empfang prüfen', model=model, csrf=csrf_token(), step='view'))

    @shell.post('/tauschen/empfang/<int:trade>/review')
    def receipt_review(trade):
        viewer = actor(); data = signed(trade, viewer, 'receipt_review')
        try:
            with connection(database_path()) as db:
                s = service(db)
                model = s.receipt_view(trade, viewer)
                positions, _ = s.review_receipt(trade, viewer, data['sender'], data['revision'])
                mode = request.form.get('mode')
                if mode == 'problem':
                    return private(page('receipts', 'Problem mit Lieferung', model=model, positions=positions,
                        token=request.form['token'], csrf=csrf_token(), step='inspect'))
                if mode == 'structured':
                    expected = {'token', '_csrf_token', 'mode'} | {f"{k}_{p['id']}" for p in positions for k in (*COUNTS, 'wrong_code')}
                    # Global HTML middleware also injects a CSRF field. Domain
                    # fields must be unique; CSRF is checked by that middleware.
                    # The shared browser history helper adds its own transport
                    # identity; receipt identity comes from our signed command.
                    if set(request.form) - {'_history_mutation_id'} != expected or any(len(request.form.getlist(k)) != 1 for k in request.form if k != '_csrf_token'):
                        raise ValueError('Unexpected inspection fields')
                    inspection = []
                    for p in positions:
                        counts = {}
                        for k in COUNTS:
                            value = request.form[f"{k}_{p['id']}"]
                            if not value.isascii() or not value.isdigit() or len(value) > 9:
                                raise ValueError('Integer required')
                            counts[k] = int(value)
                        inspection.append(dict(position=p['id'], wrong_code=request.form[f"wrong_code_{p['id']}"], **counts))
                elif mode == 'complete':
                    inspection = None
                else:
                    raise ValueError('Invalid review')
                positions, inspection = s.review_receipt(trade, viewer, data['sender'], data['revision'], inspection)
            data.update(operation='receipt_confirm', inspection=inspection)
            return private(page('receipts', 'Empfang verbindlich bestätigen', model=model, positions=positions,
                inspection=inspection, token=serializer().dumps(data), csrf=csrf_token(), step='confirm'))
        except (ValueError, KeyError):
            return private((page('changed', 'Empfang noch nicht bestätigt', notice='Bitte prüfe die aktuelle Liste und ordne jede erwartete Einheit genau einmal zu.'), 409))

    @shell.post('/tauschen/empfang/<int:trade>/confirm')
    def receipt_confirm(trade):
        viewer = actor(); data = signed(trade, viewer, 'receipt_confirm')
        try:
            with connection(database_path()) as db:
                service(db).confirm_receipt(trade, viewer, data['sender'], data['revision'], data['key'], data['inspection'])
        except (ValueError, KeyError):
            return private((page('changed', 'Empfang nicht gebucht', notice='Die Buchungsgrundlage ist nicht mehr aktuell oder benötigt einen Mengenabgleich. Es wurde nichts zusätzlich gebucht.'), 409))
        return redirect(f'/tauschen/empfang/{trade}', 303)

    @shell.post('/tauschen/empfang/<int:trade>/non-arrival')
    def receipt_non_arrival(trade):
        viewer = actor(); data = signed(trade, viewer, 'non_arrival')
        try:
            with connection(database_path()) as db:
                service(db).report_non_arrival(trade, viewer, data['sender'], data['revision'], data['key'])
        except (ValueError, KeyError):
            abort(409)
        return redirect(f'/tauschen/empfang/{trade}', 303)

    @shell.post('/tauschen/empfang/<int:trade>/response')
    def receipt_response(trade):
        viewer = actor(); data = signed(trade, viewer, 'receipt_response')
        try:
            with connection(database_path()) as db:
                service(db).respond(trade, viewer, data['sender'], data['revision'], data['problem'], request.form.get('response'), data['key'])
        except (ValueError, KeyError):
            abort(409)
        return redirect(f'/tauschen/empfang/{trade}', 303)
