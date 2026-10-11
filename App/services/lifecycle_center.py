"""Bounded public cards from batched V1 metadata; no lifecycle commands or inventory writes."""
from datetime import timedelta
from zoneinfo import ZoneInfo
from services.trade_lifecycle_completion import LifecycleCompletion, ready
from services.trade_lifecycle_requests import instant

PAGE_SIZE = 12
PREVIEW_SIZE = 3
LABELS = {'todos':'Meine To-dos','sendungen':'Meine Sendungen','eingaenge':'Meine Eingänge','archiv':'Abgeschlossene Tausche'}
EMPTY = {'todos':'Alles erledigt.','sendungen':'Du hast aktuell keine offenen Sendungen.',
         'eingaenge':'Du erwartest gerade keine Sticker.','archiv':'Du hast noch keine abgeschlossenen Tausche.'}


def date_label(value):
    return instant(value).astimezone(ZoneInfo('Europe/Berlin')).strftime('%d.%m.%Y, %H:%M %Z') if value else None


class LifecycleCenter:
    def __init__(self, db, clock=None):
        self.db = db
        self.lifecycle = LifecycleCompletion(db, clock)

    def _load(self, actor, now, archive=False, page=1):
        # Aggregate only binding quantities. Neither sticker lists nor photo/address
        # content nor rating values are selected into overview projections.
        condition = "x.trade_id IS NOT NULL" if archive else "(c.state='accepted' OR (e.eligible_at>=? AND own_rating.id IS NULL))"
        params = [actor,actor,actor,actor]
        if not archive:params.append((now-timedelta(days=15)).isoformat())
        base = '''SELECT c.trade_id,c.accepted_revision_id,c.state,t.requester_user_id,t.partner_user_id,
          u.username,a.accepted_at,x.outcome,x.completed_at,e.eligible_at,own_rating.id AS own_rating
          FROM lifecycle_contracts c JOIN trades t ON t.id=c.trade_id
          JOIN lifecycle_acceptances a ON a.trade_id=c.trade_id
          JOIN users u ON u.id=CASE WHEN t.requester_user_id=? THEN t.partner_user_id ELSE t.requester_user_id END
          LEFT JOIN lifecycle_completions x ON x.trade_id=c.trade_id
          LEFT JOIN lifecycle_rating_eligibility e ON e.trade_id=c.trade_id AND e.user_id=?
          LEFT JOIN trade_ratings own_rating ON own_rating.trade_id=c.trade_id AND own_rating.rater_user_id=?
          WHERE ? IN(t.requester_user_id,t.partner_user_id) AND '''+condition
        total = None
        if archive:
            total=self.db.execute('SELECT COUNT(*) FROM ('+base+')',params).fetchone()[0]
            base+=' ORDER BY x.completed_at DESC,c.trade_id DESC LIMIT ? OFFSET ?';params += [PAGE_SIZE,(page-1)*PAGE_SIZE]
        rows=[dict(r) for r in self.db.execute(base,params)]
        if not rows:return [],total
        # A CTE of authorized selected trade IDs scopes every batch. A bounded
        # number of SELECTs regardless of the number of trades; chunked IDs avoid
        # SQLite parameter limits for large active portfolios.
        by_id={r['trade_id']:r for r in rows}
        for row in rows:
            row.update(cycles={},shipping={},receipts={},resolutions={},problems=[],quantities={},albums=set(),release=None,
                       reduction=None,missing=set(),rejected=False,choices={},credited={})
        ids=list(by_id)
        for offset in range(0,len(ids),400):
            batch=ids[offset:offset+400];marks=','.join('?' for _ in batch)
            def query(sql):return self.db.execute(sql.replace('{ids}',marks),batch).fetchall()
            for r in query('''SELECT c.trade_id,p.from_user_id,SUM(p.quantity) AS quantity,a.name AS album,
                SUM(COALESCE(n.received_quantity,0)) AS credited
                FROM lifecycle_contracts c JOIN lifecycle_revision_positions p ON p.revision_id=c.accepted_revision_id
                JOIN albums a ON a.id=p.album_id LEFT JOIN lifecycle_need_claims n ON n.revision_position_id=p.id
                WHERE c.trade_id IN ({ids}) GROUP BY c.trade_id,p.from_user_id,p.album_id'''):
                item=by_id[r['trade_id']];item['quantities'][r['from_user_id']]=item['quantities'].get(r['from_user_id'],0)+r['quantity'];item['albums'].add(r['album'])
                item['credited'][r['from_user_id']]=item['credited'].get(r['from_user_id'],0)+r['credited']
            for r in query('''SELECT c.trade_id,c.owner_id,c.id,c.revision_id,c.completed_at,c.revealed_at,c.review_state,
                EXISTS(SELECT 1 FROM lifecycle_control_photos p WHERE p.cycle_id=c.id AND p.removed_at IS NULL) AS has_photo
                FROM lifecycle_preparation_cycles c WHERE c.is_current=1 AND c.trade_id IN ({ids})'''):
                by_id[r['trade_id']]['cycles'][r['owner_id']]=dict(r)
            for table,key,columns in (
                ('lifecycle_shipping','shipping','from_user_id,sent_at,source'),
                ('lifecycle_receipts','receipts','from_user_id,received_at,has_problem'),
                ('lifecycle_direction_resolutions','resolutions','from_user_id,kind,resolved_at')):
                for r in query('SELECT trade_id,'+columns+' FROM '+table+' WHERE trade_id IN ({ids})'):
                    by_id[r['trade_id']][key][r['from_user_id']]=dict(r)
            for r in query('SELECT trade_id,revision_id,basis_json,released_at FROM lifecycle_address_releases WHERE trade_id IN ({ids})'):
                by_id[r['trade_id']]['release']=dict(r)
            for r in query('''SELECT p.trade_id,p.id,p.from_user_id,p.kind,p.reported_at,r.response
                FROM lifecycle_delivery_problems p LEFT JOIN lifecycle_delivery_responses r ON r.problem_id=p.id
                WHERE p.trade_id IN ({ids})'''):by_id[r['trade_id']]['problems'].append(dict(r))
            for r in query("SELECT trade_id,base_revision_id,proposer_id,state FROM lifecycle_reductions WHERE trade_id IN ({ids}) AND state IN ('proposed','rejected')"):
                if r['base_revision_id']==by_id[r['trade_id']]['accepted_revision_id']:
                    if r['state']=='proposed':by_id[r['trade_id']]['reduction']=dict(r)
                    else:by_id[r['trade_id']]['rejected']=True
            for r in query('''SELECT DISTINCT h.trade_id,m.user_id FROM physical_missing_holds m JOIN trade_reservations h ON h.id=m.reservation_id
                WHERE h.trade_id IN ({ids}) AND m.resolved_at IS NULL AND m.overlap_quantity>0'''):
                by_id[r['trade_id']]['missing'].add(r['user_id'])
            for r in query('''SELECT c.trade_id,c.owner_id,s.revision_id,s.basis_json FROM lifecycle_address_choices c
                JOIN lifecycle_address_snapshots s ON s.id=c.snapshot_id WHERE c.trade_id IN ({ids})'''):
                by_id[r['trade_id']]['choices'][r['owner_id']]=dict(r)
        return rows,total

    def _card(self, row, actor, now):
        import json
        trade=row['trade_id'];partner=row['partner_user_id'] if actor==row['requester_user_id'] else row['requester_user_id']
        card=dict(trade=trade,partner=row['username'],albums=sorted(row['albums']),give=row['quantities'].get(actor,0),
                  receive=row['quantities'].get(partner,0),completed_at=row['completed_at'],completion_label=date_label(row['completed_at']),
                  archived=bool(row['outcome']),status='Mit Lieferproblem abgeschlossen' if row['outcome']=='closed_with_problem' else 'Erfolgreich abgeschlossen' if row['outcome'] else 'Tausch angenommen',
                  href=f'/tauschen/abschluss/{trade}',actions=[],waiting=None)
        card.update(received=row['credited'].get(partner,0),partner_received=row['credited'].get(actor,0),problem_count=len(row['problems']))
        def action(code,label,area,deadline=None):
            due=instant(deadline) if deadline else None
            card['actions'].append(dict(code=code,label=label,href=f'/tauschen/{area}/{trade}',deadline=deadline,
                deadline_label=date_label(deadline),priority=0 if due and due<=now+timedelta(hours=6) else 1,
                overdue=bool(due and now>=due)))
        eligible=row['eligible_at']
        if eligible and not row['own_rating'] and instant(eligible)<=now<instant(eligible)+timedelta(days=14):
            action('rate','Bewertung abgeben','abschluss',(instant(eligible)+timedelta(days=14)).isoformat())
        if not card['archived']:
            cycles=row['cycles'];own=cycles.get(actor,{});other=cycles.get(partner,{})
            basis=[c['id'] for _,c in sorted(cycles.items())]
            valid_cycles=len(cycles)==2 and all(c['revision_id']==row['accepted_revision_id'] for c in cycles.values())
            approved=valid_cycles and all(c['completed_at'] and c['revealed_at'] and c['review_state']=='approved' for c in cycles.values())
            release=row['release'];pending=row['reduction'];unmoved=not release and not row['shipping'] and not row['receipts']
            prep_due=(instant(row['accepted_at'])+timedelta(hours=72)).isoformat()
            address_ready=approved and not pending and not row['missing'] and not row['rejected']
            receipt_ready=bool(approved and release and release['revision_id']==row['accepted_revision_id'] and json.loads(release['basis_json'])==basis and not pending)
            if unmoved:
                if pending:
                    if pending['proposer_id']!=actor:action('reduction','Reduktion prüfen','vorbereitung')
                    else:card['waiting']='Wartet auf Zustimmung zur Reduktion'
                else:
                    if actor in row['missing']:action('missing','Fehlmenge und Reduktion prüfen','vorbereitung')
                    elif not own.get('completed_at'):
                        action('prepare','Vorbereitung abschließen' if own.get('has_photo') else 'Sticker kontrollieren und Fotos hochladen','vorbereitung',prep_due)
                    elif own.get('review_state')=='problem':action('correct','Kontrollfotos korrigieren','vorbereitung')
                    if valid_cycles and all(c['completed_at'] and c['revealed_at'] for c in cycles.values()) and other['review_state']=='pending':
                        action('review','Fotos prüfen','vorbereitung')
                    if row['rejected']:action('reduction_retry','Neue Reduktion prüfen','vorbereitung')
                    if address_ready:
                        choice=row['choices'].get(actor)
                        if not choice or choice['revision_id']!=row['accepted_revision_id'] or json.loads(choice['basis_json'])!=basis:
                            action('address','Adresse auswählen und bestätigen','adressen')
                        else:card['waiting']='Wartet auf Adresse der Gegenpartei'
            if release and actor not in row['shipping'] and not pending:
                action('ship','Versand bestätigen','versand',(instant(release['released_at'])+timedelta(hours=72)).isoformat())
            incoming=row['receipts'].get(partner);resolved=row['resolutions'].get(partner)
            if receipt_ready and not incoming and not resolved:action('receive','Empfang prüfen','empfang')
            for problem in row['problems']:
                sender=problem['from_user_id']
                if sender in row['resolutions'] or (problem['kind']=='non_arrival' and sender in row['receipts']):continue
                if sender==actor:
                    if not problem['response']:action('respond','Auf Lieferproblem reagieren','empfang')
                else:
                    if problem['kind']=='inspection':action('accept_problem','Problem akzeptieren','abschluss')
                    due=instant(problem['reported_at'])+timedelta(days=14)
                    if now>=due:action('close_problem','Problem endgültig abschließen','abschluss')
                    else:card['problem_wait_until']=date_label(due.isoformat())
            sent=row['shipping'].get(partner)
            if sent and sent['source']=='SENDER_CONFIRMATION' and not incoming and not resolved and not any(p['from_user_id']==partner and p['kind']=='non_arrival' for p in row['problems']):
                due=instant(sent['sent_at'])+timedelta(days=7)
                if now>=due:action('nonarrival','Nichtankunft melden','empfang')
            def status(sender,outgoing):
                receipt=row['receipts'].get(sender);resolution=row['resolutions'].get(sender)
                if resolution:return 'Empfang bestätigt' if resolution['kind']=='complete' else 'Problem abgeschlossen'
                if receipt:return 'Teilempfang / Lieferproblem dokumentiert'
                if any(p['from_user_id']==sender for p in row['problems']):return 'Nichtankunft gemeldet'
                if sender in row['shipping']:return 'Versendet' if outgoing else 'Sendung unterwegs'
                if release:
                    if now>=instant(release['released_at'])+timedelta(hours=72):return 'Versand überfällig' if outgoing else 'Gegenpartei ist mit dem Versand überfällig'
                    return 'Versand bereit' if outgoing else 'Gegenpartei muss versenden'
                return 'Vorbereitung läuft' if outgoing else 'Gegenpartei bereitet vor'
            card['outgoing_status']=status(actor,True);card['incoming_status']=status(partner,False)
            card['waiting']=card['waiting'] or ('Wartet auf Gegenpartei' if not card['actions'] else None)
            card['status']=card['outgoing_status']+' · '+card['incoming_status']
        card['actions'].sort(key=lambda a:(a['priority'],a['deadline'] or '9999',a['code']))
        primary=card['actions'][0] if card['actions'] else None
        card['sort']=(primary['priority'] if primary else 2,primary['deadline'] or '9999' if primary else '9999',row['accepted_at'],trade)
        return card

    def view(self, actor, section=None, page=1):
        if section is not None and section not in LABELS:raise ValueError('Unknown center list')
        if type(page) is not int or page<1 or page>100000:raise ValueError('Invalid page')
        self.lifecycle._actor(actor)
        if not ready(self.db):return dict(enabled=False,sections=[],section=section,items=[],total=0,page=page,pages=0)
        self.lifecycle.refresh_for_actor(actor)
        now=instant(self.lifecycle.clock())
        with self.lifecycle.store.transaction():
            rows,total=self._load(actor,now,section=='archiv',page)
            cards=[self._card(row,actor,now) for row in rows]
        if section=='archiv':return dict(enabled=True,section=section,items=cards,total=total,page=page,pages=(total+PAGE_SIZE-1)//PAGE_SIZE)
        cards.sort(key=lambda c:c['sort'])
        lists=dict(todos=[c for c in cards if c['actions']],sendungen=[c for c in cards if not c['archived']],eingaenge=[c for c in cards if not c['archived']])
        if section:
            items=lists[section];return dict(enabled=True,section=section,items=items[(page-1)*PAGE_SIZE:page*PAGE_SIZE],total=len(items),page=page,pages=(len(items)+PAGE_SIZE-1)//PAGE_SIZE)
        return dict(enabled=True,section=None,sections=[dict(key=k,title=LABELS[k],empty=EMPTY[k],total=len(v),items=v[:PREVIEW_SIZE]) for k,v in lists.items()])
