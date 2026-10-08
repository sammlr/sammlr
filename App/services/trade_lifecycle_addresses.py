"""Private address book and atomic bilateral logistics boundary; no shipping."""
import hashlib
import json
import re
from services.trade_lifecycle_preparation import LifecyclePreparation
from services.trade_lifecycle_foundation import _json
from services.trade_lifecycle_requests import instant

FIELDS=('first_name','last_name','street','house_number','postal_code','city','country')


def ready(db):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE name='lifecycle_address_releases'").fetchone())


def normalized(data):
    result={}
    for field in FIELDS:
        value=data.get(field)
        if not isinstance(value,str):raise ValueError('Required address field missing')
        value=' '.join(value.split())
        if not value or len(value)>160 or any(ord(c)<32 for c in value):raise ValueError('Invalid address field')
        result[field]=value
    country=result['country'].upper()
    if not re.fullmatch('[A-Z]{2}',country):raise ValueError('Two-letter country code required')
    result['country']=country
    label=data.get('label','')
    if not isinstance(label,str) or len(label)>80:raise ValueError('Invalid private label')
    result['label']=' '.join(label.split())
    return result


class LifecycleAddresses(LifecyclePreparation):
    def _schema(self,actor):
        self._actor(actor)
        if not ready(self.db):raise ValueError('Address schema unavailable')

    def book(self,actor):
        self._schema(actor)
        return [dict(r) for r in self.db.execute('SELECT * FROM lifecycle_address_book WHERE owner_id=? ORDER BY is_default DESC,id',(actor,))]

    def book_command(self,actor,key,operation,address=None,version=None,data=None):
        self._schema(actor)
        if not isinstance(key,str) or not 1<=len(key)<=200:raise ValueError('Command identity required')
        clean=normalized(data or {}) if operation in ('create','edit') else {}
        payload=dict(address=address,version=version,data=clean)
        digest=hashlib.sha256(_json(payload).encode()).hexdigest()
        with self.store.transaction():
            self._schema(actor)
            old=self.db.execute('SELECT * FROM lifecycle_address_book_commands WHERE owner_id=? AND command_key=?',(actor,key)).fetchone()
            if old:
                if old['operation']!=operation or old['payload_digest']!=digest:raise ValueError('Conflicting command')
                return json.loads(old['result_json'])
            now=instant(self.clock()).isoformat()
            if operation=='create':
                address=self.db.execute('''INSERT INTO lifecycle_address_book(owner_id,label,first_name,last_name,street,house_number,postal_code,city,country,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)''',(actor,clean['label'],*(clean[f] for f in FIELDS),now,now)).lastrowid
            else:
                row=self.db.execute('SELECT * FROM lifecycle_address_book WHERE id=? AND owner_id=?',(address,actor)).fetchone()
                if row is None or type(version) is not int or row['version']!=version:raise ValueError('Own current address required')
                if operation=='edit':
                    self.db.execute('''UPDATE lifecycle_address_book SET label=?,first_name=?,last_name=?,street=?,house_number=?,postal_code=?,city=?,country=?,version=version+1,updated_at=? WHERE id=?''',(clean['label'],*(clean[f] for f in FIELDS),now,address))
                elif operation=='delete':self.db.execute('DELETE FROM lifecycle_address_book WHERE id=?',(address,))
                elif operation=='default':
                    self.db.execute('UPDATE lifecycle_address_book SET is_default=0,version=version+1,updated_at=? WHERE owner_id=? AND is_default=1 AND id<>?',(now,actor,address))
                    self.db.execute('UPDATE lifecycle_address_book SET is_default=1,version=version+1,updated_at=? WHERE id=?',(now,address))
                else:raise ValueError('Unknown address operation')
            result=dict(address=address,status='ok')
            self.db.execute('INSERT INTO lifecycle_address_book_commands VALUES (?,?,?,?,?,?)',(actor,key,operation,digest,_json(result),now))
            return result

    def _released(self,trade):
        return self.db.execute('SELECT * FROM lifecycle_address_releases WHERE trade_id=?',(trade,)).fetchone()

    def _choice(self,trade,actor):
        return self.db.execute('''SELECT c.generation,s.* FROM lifecycle_address_choices c
            JOIN lifecycle_address_snapshots s ON s.id=c.snapshot_id WHERE c.trade_id=? AND c.owner_id=?''',(trade,actor)).fetchone()

    @staticmethod
    def _safe(snapshot):
        return {f:snapshot[f] for f in ('id','owner_id','revision_id','selected_at',*FIELDS)}

    def view_address(self,trade,actor):
        self._schema(actor)
        with self.store.transaction():
            row=self._binding(trade,actor);now=instant(self.clock());cycles=self._cycles(row,now)
            basis=[c['id'] for c in cycles];released=self._released(trade)
            choice=self._choice(trade,actor)
            if not released and self._state(row,cycles)!='ready_for_address_release':raise ValueError('Current preparation approval required')
            partner=row['partner_user_id'] if row['requester_user_id']==actor else row['requester_user_id']
            current=choice and choice['revision_id']==row['accepted_revision_id'] and choice['basis_json']==_json(basis)
            result=dict(trade=trade,revision=row['accepted_revision_id'],basis=basis,generation=choice['generation'] if choice else 0,
                own=self._safe(choice) if current else None,other=None,
                state='ready_to_ship' if released else 'address_waiting' if current else 'address_selection',
                shipping_enabled=bool(self.db.execute("SELECT 1 FROM sqlite_master WHERE name='lifecycle_shipping'").fetchone()),
                addresses=self.book(actor),released_at=released['released_at'] if released else None)
            if released:
                ids=(released['requester_snapshot_id'],released['partner_snapshot_id'])
                snapshots=[self.db.execute('SELECT * FROM lifecycle_address_snapshots WHERE id=?',(i,)).fetchone() for i in ids]
                result['own']=self._safe(next(s for s in snapshots if s['owner_id']==actor))
                result['other']=self._safe(next(s for s in snapshots if s['owner_id']==partner))
            return result

    def confirm(self,trade,actor,revision,basis,generation,address,version,key):
        self._schema(actor)
        payload=dict(revision=revision,basis=basis,generation=generation,address=address,version=version)
        with self.store.transaction():
            old=self._command(trade,actor,key,'address_confirm',payload)
            if old is not None:return old
            row,now,cycles,own,other=self._context(trade,actor,revision,basis)
            if self._released(trade):raise ValueError('Released trade address cannot change')
            if self._state(row,cycles)!='ready_for_address_release':raise ValueError('Current bilateral approval required')
            previous=self._choice(trade,actor)
            if type(generation) is not int or generation!=(previous['generation'] if previous else 0):raise ValueError('Stale address choice')
            entry=self.db.execute('SELECT * FROM lifecycle_address_book WHERE id=? AND owner_id=?',(address,actor)).fetchone()
            if entry is None or type(version) is not int or entry['version']!=version:raise ValueError('Own unchanged address required')
            normalized(dict(entry))
            snapshot=self.db.execute('''INSERT INTO lifecycle_address_snapshots(trade_id,owner_id,revision_id,basis_json,first_name,last_name,street,house_number,postal_code,city,country,selected_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',(trade,actor,revision,_json(basis),*(entry[f] for f in FIELDS),now.isoformat())).lastrowid
            if previous:self.db.execute('UPDATE lifecycle_address_choices SET generation=generation+1,snapshot_id=? WHERE trade_id=? AND owner_id=?',(snapshot,trade,actor))
            else:self.db.execute('INSERT INTO lifecycle_address_choices VALUES (?,?,1,?)',(trade,actor,snapshot))
            self._event_data(row,'TradeAddressConfirmed',actor,now,snapshot_id=snapshot)
            opposite=self._choice(trade,other['owner_id'])
            released=False
            if opposite and opposite['revision_id']==revision and opposite['basis_json']==_json(basis):
                selected={actor:snapshot,other['owner_id']:opposite['id']}
                self.db.execute('INSERT INTO lifecycle_address_releases VALUES (?,?,?,?,?,?)',
                    (trade,revision,_json(basis),selected[row['requester_user_id']],selected[row['partner_user_id']],now.isoformat()))
                self.db.execute("UPDATE lifecycle_directions SET preparation_state='ready_to_ship' WHERE trade_id=?",(trade,))
                self._event_data(row,'AddressesReleased',actor,now)
                event=self.db.execute('SELECT last_insert_rowid()').fetchone()[0]
                self._event_data(row,'TradeReadyToShip',actor,now)
                from services.typed_notifications import TypedNotificationService
                for user in selected:
                    TypedNotificationService(self.db).create(user,'lifecycle_addresses_released','Versandadressen verfügbar',
                        'Die Versandadressen sind jetzt für diesen Tausch verfügbar.','trade',trade,event)
                released=True
            return self.store.record_command(trade,actor,key,'address_confirm',payload,dict(snapshot=snapshot,released=released))

    def snapshot(self,trade,actor,snapshot):
        self._schema(actor);self._binding(trade,actor)
        row=self.db.execute('SELECT * FROM lifecycle_address_snapshots WHERE id=? AND trade_id=?',(snapshot,trade)).fetchone()
        if row is None:raise ValueError('Address unavailable')
        if row['owner_id']!=actor:
            release=self._released(trade)
            if not release or snapshot not in (release['requester_snapshot_id'],release['partner_snapshot_id']):raise ValueError('Address private before bilateral release')
        return self._safe(row)
