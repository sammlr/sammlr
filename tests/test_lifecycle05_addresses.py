"""Synthetic address selection, bilateral disclosure and immutable logistics."""
import json,sqlite3,unittest
from unittest.mock import patch
from tests import test_lifecycle04_preparation as fixtures
from services.trade_lifecycle_addresses import LifecycleAddresses,FIELDS,normalized
from services.trade_lifecycle_preparation import LifecyclePreparation
from App.Database.migration_runner import migrate,rollback


def address(tag='A',**changes):
    return dict(first_name='Synthetic',last_name='Person '+tag,street='Fixture Road '+tag,house_number='7 B',postal_code='SW1A 1AA',city='Fixture City',country='GB',label='Private '+tag)|changes


class AddressTests(unittest.TestCase):
    connect=fixtures.PreparationTests.connect
    send=fixtures.PreparationTests.send
    stock=fixtures.PreparationTests.stock
    target=fixtures.PreparationTests.target
    race=fixtures.PreparationTests.race
    view=fixtures.PreparationTests.view
    call=fixtures.PreparationTests.call
    photo=fixtures.PreparationTests.photo
    both=fixtures.PreparationTests.both
    ready=fixtures.PreparationTests.ready
    larger=fixtures.PreparationTests.larger
    reduction=fixtures.PreparationTests.reduction
    def setUp(self):
        fixtures.PreparationTests.setUp(self);migrate(self.db,27)
        self.a=LifecycleAddresses(self.db,lambda:self.now);self.ready();self.counter=0
    def book(self,owner=1,tag='A',**changes):
        self.counter+=1
        result=self.a.book_command(owner,'create-'+str(self.counter),'create',data=address(tag,**changes))
        return next(e for e in self.a.book(owner) if e['id']==result['address'])
    def confirm(self,owner=1,entry=None,key=None,model=None):
        entry=entry or self.book(owner,str(owner));v=model or self.a.view_address(self.t,owner);self.counter+=1
        return self.a.confirm(self.t,owner,v['revision'],v['basis'],v['generation'],entry['id'],entry['version'],key or 'confirm-'+str(self.counter))
    def released(self):
        self.confirm();self.confirm(2);return self.a.view_address(self.t,1)
    def inventory(self):
        return {t:[tuple(r) for r in self.db.execute('SELECT * FROM '+t)] for t in ('stickers','trade_reservations','lifecycle_need_claims','physical_missing_holds')}

    def test_normalization_required_fields_and_international_format(self):
        self.assertEqual('GB',normalized(address(country=' gb '))['country'])
        self.assertEqual('Fixture City',normalized(address(city=' Fixture  \nCity '))['city'])
        for field in FIELDS:
            with self.assertRaises(ValueError):normalized(address(**{field:' \t '}))
        with self.assertRaises(ValueError):normalized(address(country='Deutschland'))
        self.assertEqual('7 B',normalized(address())['house_number'])

    def test_multiple_addresses_default_and_owner_only_edit_delete(self):
        one=self.book();two=self.book(tag='B')
        self.a.book_command(1,'default','default',two['id'],two['version'])
        self.assertEqual(two['id'],self.a.book(1)[0]['id'])
        for op in ('edit','delete','default'):
            with self.assertRaises(ValueError):self.a.book_command(2,'foreign-'+op,op,one['id'],one['version'],address())
        self.a.book_command(1,'edit','edit',one['id'],one['version'],address(city='Other synthetic city'))
        updated=next(e for e in self.a.book(1) if e['id']==one['id'])
        self.assertEqual(2,updated['version']);self.a.book_command(1,'delete','delete',one['id'],2)
        self.assertEqual(1,len(self.a.book(1)))

    def test_address_book_commands_idempotent(self):
        data=address();r=self.a.book_command(1,'create','create',data=data)
        self.assertEqual(r,self.a.book_command(1,'create','create',data=data))
        with self.assertRaises(ValueError):self.a.book_command(1,'create','create',data=address(city='Other'))
        for op in ('default','edit','delete'):
            e=self.a.book(1)[0];key=op
            result=self.a.book_command(1,key,op,e['id'],e['version'],data)
            self.assertEqual(result,self.a.book_command(1,key,op,e['id'],e['version'],data))

    def test_one_selection_is_blind_but_owner_can_read(self):
        r=self.confirm();v=self.a.view_address(self.t,1)
        self.assertEqual('address_waiting',v['state']);self.assertIsNotNone(v['own']);self.assertIsNone(v['other'])
        self.assertEqual(r['snapshot'],self.a.snapshot(self.t,1,r['snapshot'])['id'])
        self.assertIsNone(self.a.view_address(self.t,2)['other'])
        with self.assertRaises(ValueError):self.a.snapshot(self.t,2,r['snapshot'])
        self.assertEqual(0,self.db.execute('SELECT COUNT(*) FROM lifecycle_address_releases').fetchone()[0])

    def test_bilateral_release_readiness_and_no_shipping(self):
        before=self.inventory();first=self.confirm();second=self.confirm(2)
        self.assertTrue(second['released'])
        for owner,other in ((1,2),(2,1)):
            v=self.a.view_address(self.t,owner);self.assertEqual('ready_to_ship',v['state']);self.assertEqual(other,v['other']['owner_id'])
        self.assertEqual(before,self.inventory())
        self.assertEqual({'not_sent'},set(r[0] for r in self.db.execute('SELECT shipping_state FROM lifecycle_directions')))
        self.assertEqual({'ready_to_ship'},set(r[0] for r in self.db.execute('SELECT preparation_state FROM lifecycle_directions')))
        self.assertEqual(self.now.isoformat(),self.a.view_address(self.t,1)['released_at'])

    def test_change_selection_before_release_only_latest_disclosed(self):
        old=self.confirm(entry=self.book(tag='old'));new=self.confirm(entry=self.book(tag='new'));self.confirm(2)
        self.assertEqual('Fixture Road new',self.a.view_address(self.t,2)['other']['street'])
        with self.assertRaises(ValueError):self.a.snapshot(self.t,2,old['snapshot'])
        self.assertEqual(new['snapshot'],self.a.view_address(self.t,2)['other']['id'])

    def test_book_edit_delete_default_never_mutate_selected_snapshot(self):
        e=self.book();self.confirm(entry=e)
        self.a.book_command(1,'edit','edit',e['id'],1,address(street='Different synthetic street'))
        self.confirm(2);before=self.a.view_address(self.t,2)['other']
        self.assertEqual('Fixture Road A',before['street'])
        self.a.book_command(1,'default','default',e['id'],2)
        self.a.book_command(1,'delete','delete',e['id'],3)
        self.assertEqual(before,self.a.view_address(self.t,2)['other'])

    def test_snapshots_immutable_and_no_normal_selection_after_release(self):
        self.released()
        for sql in ("UPDATE lifecycle_address_snapshots SET city='changed'","UPDATE lifecycle_address_releases SET released_at='changed'"):
            with self.assertRaises(sqlite3.IntegrityError):self.db.execute(sql)
            self.db.rollback()
        with self.assertRaises(ValueError):self.confirm()

    def test_foreign_participant_ids_and_foreign_book_entry_rejected(self):
        e=self.book(2)
        with self.assertRaises(ValueError):self.confirm(entry=e)
        with self.assertRaises(ValueError):self.a.view_address(self.t,3)
        r=self.confirm();self.confirm(2)
        for trade,user,snapshot in ((self.t,3,r['snapshot']),(999,1,r['snapshot']),(self.t,1,999)):
            with self.assertRaises(ValueError):self.a.snapshot(trade,user,snapshot)

    def test_stale_tab_and_changed_book_version_rejected(self):
        e=self.book();v=self.a.view_address(self.t,1);self.confirm(entry=e,model=v)
        with self.assertRaises(ValueError):self.confirm(entry=e,model=v)
        self.a.book_command(1,'edit','edit',e['id'],1,address())
        with self.assertRaises(ValueError):self.confirm(entry=e)

    def test_duplicate_confirmation_no_extra_snapshot_events_or_notifications(self):
        e=self.book();v=self.a.view_address(self.t,1);r=self.confirm(entry=e,key='once',model=v)
        self.assertEqual(r,self.confirm(entry=e,key='once',model=v))
        b=self.book(2);vb=self.a.view_address(self.t,2);r=self.confirm(2,b,'second',vb)
        self.assertEqual(r,self.confirm(2,b,'second',vb))
        self.assertEqual(2,self.db.execute('SELECT COUNT(*) FROM lifecycle_address_snapshots').fetchone()[0])
        self.assertEqual(1,self.db.execute('SELECT COUNT(*) FROM lifecycle_address_releases').fetchone()[0])
        self.assertEqual(2,self.db.execute("SELECT COUNT(*) FROM notifications WHERE notification_type='lifecycle_addresses_released'").fetchone()[0])

    def test_history_notifications_and_commands_have_no_addresses_or_labels(self):
        self.released()
        for table in ('trade_events','notifications','lifecycle_commands','lifecycle_address_book_commands'):
            encoded=json.dumps([tuple(r) for r in self.db.execute('SELECT * FROM '+table)])
            for secret in ('Fixture Road','Fixture City','Private 1','Private 2','SW1A 1AA'):
                self.assertNotIn(secret,encoded)
        from services.typed_notifications import TypedNotificationService
        service=TypedNotificationService(self.db)
        for row in self.db.execute("SELECT * FROM notifications WHERE notification_type='lifecycle_addresses_released'"):
            n=service.from_row(row);self.assertEqual(f'/tauschen/adressen/{self.t}',service.target_path_for(n,row['user_id']))
            self.assertIsNone(service.target_path_for(n,3))
        for s in (self.a.view_address(self.t,1)['own'],self.a.view_address(self.t,1)['other']):
            self.assertNotIn('label',s);self.assertNotIn('email',s);self.assertNotIn('phone',s)

    def test_not_ready_correction_invalidates_previous_choices(self):
        self.confirm();old=self.a.view_address(self.t,2);entry=self.book(2)
        self.call('correct')
        with self.assertRaises(ValueError):self.a.view_address(self.t,1)
        with self.assertRaises(ValueError):self.confirm(2,entry,model=old)
        self.photo();self.call('complete');self.call('approve',2)
        self.confirm(2,entry)
        self.assertEqual('address_waiting',self.a.view_address(self.t,2)['state'])
        self.assertIsNone(self.a.view_address(self.t,1)['own'])
        self.confirm();self.assertEqual('ready_to_ship',self.a.view_address(self.t,1)['state'])

    def test_release_blocks_normal_preparation_changes_and_old_photo_gallery(self):
        photo=self.view()['cycles'][0]['photos'][0]['id'];self.released()
        for action in ('correct','reduction_propose','missing'):
            with self.assertRaises(ValueError):self.call(action)
        with self.assertRaises(ValueError):self.s.photo(self.t,1,photo)

    def test_default_does_not_select_or_disclose(self):
        e=self.book();self.a.book_command(1,'default','default',e['id'],1)
        self.assertIsNone(self.a.view_address(self.t,1)['own']);self.assertIsNone(self.a.view_address(self.t,2)['other'])

    def test_release_rollback_on_notification_error(self):
        self.confirm();e=self.book(2);before=self.inventory()
        with patch('services.typed_notifications.TypedNotificationService.create',side_effect=ValueError('injected')):
            with self.assertRaises(ValueError):self.confirm(2,e)
        self.assertEqual(0,self.db.execute('SELECT COUNT(*) FROM lifecycle_address_releases').fetchone()[0])
        self.assertEqual(1,self.db.execute('SELECT COUNT(*) FROM lifecycle_address_snapshots').fetchone()[0])
        self.assertEqual(before,self.inventory())

    def race_confirm(self,owner,entry,model,key):
        return lambda q:LifecycleAddresses(q.db,lambda:self.now).confirm(self.t,owner,model['revision'],model['basis'],model['generation'],entry['id'],entry['version'],key)

    def test_simultaneous_both_confirm(self):
        ea,eb=self.book(),self.book(2);a,b=self.a.view_address(self.t,1),self.a.view_address(self.t,2)
        r=self.race([self.race_confirm(1,ea,a,'a'),self.race_confirm(2,eb,b,'b')])
        self.assertEqual(['ok','ok'],sorted(x[0] for x in r));self.assertEqual('ready_to_ship',self.a.view_address(self.t,1)['state'])

    def test_parallel_duplicate_same_side(self):
        e=self.book();v=self.a.view_address(self.t,1);fn=self.race_confirm(1,e,v,'same')
        self.assertEqual(['ok','ok'],sorted(x[0] for x in self.race([fn,fn])))
        self.assertEqual(1,self.db.execute('SELECT COUNT(*) FROM lifecycle_address_snapshots').fetchone()[0])

    def test_selection_change_races_partner_confirmation(self):
        self.confirm();e,b=self.book(tag='new'),self.book(2);v,w=self.a.view_address(self.t,1),self.a.view_address(self.t,2)
        self.race([self.race_confirm(1,e,v,'replace'),self.race_confirm(2,b,w,'release')])
        final=self.a.view_address(self.t,2);self.assertEqual('ready_to_ship',final['state'])
        self.assertIn(final['other']['street'],('Fixture Road 1','Fixture Road new'))

    def test_book_edit_and_delete_race_confirmation(self):
        for op in ('edit','delete'):
            e=self.book(tag=op);v=self.a.view_address(self.t,1)
            fn=lambda q:LifecycleAddresses(q.db,lambda:self.now).book_command(1,op,op,e['id'],e['version'],address('changed'))
            r=self.race([self.race_confirm(1,e,v,op+'confirm'),fn]);self.assertIn('ok',[x[0] for x in r])
            choice=self.a.view_address(self.t,1)['own']
            if choice:self.assertNotEqual('Fixture Road changed',choice['street'])

    def test_release_race_review_correction(self):
        self.confirm();e=self.book(2);v=self.a.view_address(self.t,2)
        correction=lambda q:LifecyclePreparation(q.db,lambda:self.now).command(self.t,1,self.rev,v['basis'],'correction','correct')
        results=self.race([self.race_confirm(2,e,v,'release'),correction]);self.assertEqual(['conflict','ok'],sorted(x[0] for x in results))

    def test_release_race_reduction(self):
        self.larger()
        for owner in (1,3):self.photo(owner);self.call('complete',owner)
        self.call('approve');self.call('approve',3)
        self.confirm();e=self.book(3);v=self.a.view_address(self.t,3)
        positions=[[p[k] for k in ('from_user_id','to_user_id','album_id','sticker_code')]+[22] for p in self.view()['positions']]
        proposal=lambda q:LifecyclePreparation(q.db,lambda:self.now).command(self.t,1,self.rev,v['basis'],'reduce','reduction_propose',{'positions':positions})
        results=self.race([self.race_confirm(3,e,v,'release'),proposal]);self.assertEqual(['conflict','ok'],sorted(x[0] for x in results))

    def test_end_state_removes_partner_access(self):
        r=self.confirm();self.confirm(2);self.db.execute("UPDATE lifecycle_contracts SET state='ended' WHERE trade_id=?",(self.t,));self.db.commit()
        with self.assertRaises(ValueError):self.a.snapshot(self.t,2,r['snapshot'])

    def test_upgrade_existing_preparation_empty_down_and_populated_guard(self):
        self.assertEqual((27,),rollback(self.db,26));self.assertEqual((27,),migrate(self.db,27))
        self.assertEqual('address_selection',self.a.view_address(self.t,1)['state'])
        self.book()
        with self.assertRaises(sqlite3.IntegrityError):rollback(self.db,26)
        self.assertEqual([],self.db.execute('PRAGMA foreign_key_check').fetchall())
        self.assertEqual('ok',self.db.execute('PRAGMA integrity_check').fetchone()[0])

if __name__=='__main__':unittest.main()
