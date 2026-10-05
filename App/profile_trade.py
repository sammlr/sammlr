"""Profile trade presentation and live manual adapter; no persistence or lifecycle writes."""
from pathlib import Path
import hashlib
import json
from flask import abort, render_template, render_template_string, request, session, jsonify, send_from_directory
from services.partner_trade import (selected_albums,context_query,profile_url,manual_context,
                                    participating_album_count,change_notice)
from services.trade_v2_domain import TradeV2Domain
from services.smartdeal_optimizer import SmartDealPiece

ASSETS=Path(__file__).resolve().parent/'trade_v2'/'assets'


def profile_trade_html(database, viewer, profile):
    if viewer is None or viewer==profile.user_id:
        return ''
    from trade_shell import read_connection
    selected=selected_albums(request.args)
    with read_connection(database) as db:
        # Preserve historical profile-only fixtures; productive Trade shell is V20+.
        if db.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0] < 20:
            return ''
        available=tuple((r['album_id'],r['name']) for r in db.execute('''SELECT ua.album_id,a.name
            FROM user_albums ua JOIN albums a ON a.id=ua.album_id
            WHERE ua.user_id=? AND ua.trade_pool_enabled=1 ORDER BY a.name''',(viewer,)))
        if selected is not None:
            selected &= {a for a,_ in available}
        market=TradeV2Domain(db).market(viewer,selected)
        pair=next((p for p in market.pairs if p.partner_id==profile.user_id),None)
        count=pair.max_equal_piece_count if pair else 0
        album_count=participating_album_count(market,pair) if pair else 0
    query=context_query(selected)
    query+=('&' if query else '')+'trade_seen='+str(count)
    suffix='?'+query
    return render_template('profile_trade.html',notice=change_notice(request.args,count),
        collection_hidden=not profile.current_albums,username=profile.username,count=count,album_count=album_count,
        restricted=selected is not None,selected=selected if selected is not None else {a for a,_ in available},
        available=available,profile_path=profile_url(profile.username),
        auto_url=f'/tauschen/sammlr/{profile.user_id}/smartdeal'+suffix,
        manual_url=f'/tauschen/sammlr/{profile.user_id}/manual'+suffix)


def register_manual(blueprint,database_path,actor,csrf_token):
    @blueprint.get('/tauschen/manual-assets/<name>')
    def manual_asset(name):
        actor()
        if name not in {'manual.css','manual_ink.js','manual_rules.js','manual_view.js'}:
            abort(404)
        return send_from_directory(ASSETS,name)

    def context(db,partner_id):
        viewer=actor()
        market=TradeV2Domain(db).market(viewer,selected_albums(request.args))
        pair=next((p for p in market.pairs if p.partner_id==partner_id and p.max_equal_piece_count>0),None)
        if pair is None:return None
        username=db.execute('SELECT username FROM users WHERE id=?',(partner_id,)).fetchone()[0]
        names={r['id']:r['name'] for r in db.execute('SELECT id,name FROM albums')}
        return viewer,market,pair,username,manual_context(market,pair,names,username)

    @blueprint.get('/tauschen/sammlr/<int:partner_id>/manual')
    def manual(partner_id):
        from trade_shell import read_connection
        with read_connection(database_path()) as db:
            result=context(db,partner_id)
            if result is None:
                if request.method=='POST':
                    return jsonify(ok=False,message='Die Tauschmöglichkeit hat sich geändert. Aktuell ist kein Deal möglich.'),409
                notice=change_notice(request.args,0)
                if notice:
                    return render_template_string('<p>{{ notice }}</p><a href="/tauschen">Zur Tauschbörse</a>',notice=notice)
                abort(404)
            viewer,market,pair,username,current=result
        signature=hashlib.sha256(json.dumps(current,sort_keys=True).encode()).hexdigest()[:20]
        suffix=context_query(selected_albums(request.args))
        data=dict(live=True,partner=dict(slug=f'live-{viewer}-{partner_id}-{signature}',display_name=username),
                  contexts={'same':current},notice=change_notice(request.args,pair.max_equal_piece_count),profile_url=profile_url(username,selected_albums(request.args)),
                  validation_url=f'/tauschen/sammlr/{partner_id}/manual/check'+('?' + suffix if suffix else ''),
                  csrf=csrf_token(),fingerprint=signature)
        template=(ASSETS.parent/'templates'/'manual.html').read_text()
        return render_template_string(template,data=data)

    @blueprint.post('/tauschen/sammlr/<int:partner_id>/manual/check')
    def manual_check(partner_id):
        from trade_shell import read_connection
        payload=request.get_json(silent=True)
        if not isinstance(payload,dict):abort(400)
        with read_connection(database_path()) as db:
            result=context(db,partner_id)
            if result is None:
                if request.method=='POST':
                    return jsonify(ok=False,message='Die Tauschmöglichkeit hat sich geändert. Aktuell ist kein Deal möglich.'),409
                notice=change_notice(request.args,0)
                if notice:
                    return render_template_string('<p>{{ notice }}</p><a href="/tauschen">Zur Tauschbörse</a>',notice=notice)
                abort(404)
            viewer,market,pair,username,current=result
            signature=hashlib.sha256(json.dumps(current,sort_keys=True).encode()).hexdigest()[:20]
            if payload.get('fingerprint') != signature:
                return jsonify(ok=False,message='Die Tauschalben oder verfügbaren Sticker haben sich geändert. Bitte lade die Auswahl neu.'),409
            try:
                def pieces(side):
                    values=payload[side]
                    if not isinstance(values,list) or len(values)>2000:raise ValueError()
                    result=[]
                    for value in values:
                        if not isinstance(value,str) or '::' not in value:raise ValueError()
                        album,code=value.split('::',1)
                        result.append(SmartDealPiece(album,code,1))
                    return tuple(result)
                TradeV2Domain.validate_deal(market,partner_id,pieces('give'),pieces('receive'))
            except (KeyError,ValueError,TypeError):
                return jsonify(ok=False,message='Diese Auswahl ist nicht zulässig. Bitte prüfe die Sticker und Mengen.'),400
        return jsonify(ok=True,message='Auswahl gültig. Es wurde noch keine Tauschanfrage erstellt.')
