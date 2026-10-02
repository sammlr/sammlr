"""Explicit synthetic two-party inputs; no inventory, eligibility or optimizer service."""
from copy import deepcopy


def manual_contexts(partner):
    albums=[]
    for aid,title,prefix,receive_count,give_count in (
        ('wm06','WM 2006','',8,3),
        ('em04','EM 2004','',2,0),
        ('buli07','Bundesliga 07/08','',2,5),
        ('wm26','WM 2026','BRA ',3,2),
    ):
        def items(count,offset):
            return [dict(key=f'{aid}::{prefix}{offset+n}::1',code=f'{prefix}{offset+n}',instance=1,supply=1,need=1) for n in range(1,count+1)]
        albums.append(dict(id=aid,title=title,receive=items(receive_count,0),give=items(give_count,100),
                           me=dict(tradeEnabled=True,smartEnabled=True,crossAlbum=False),
                           partner=dict(tradeEnabled=True,smartEnabled=True,crossAlbum=False)))
    contexts={}
    for name in ('same','open','one-sided','closed'):
        groups=deepcopy(albums)
        for album in groups:
            if name in ('open','one-sided'):album['me']['crossAlbum']=True
            if name=='open':album['partner']['crossAlbum']=True
        if name=='closed':groups[-1]['partner']['tradeEnabled']=False
        contexts[name]=dict(scenario=name,partner_id=partner['id'],partner=partner['display_name'],profile_slug=partner['slug'],albums=groups)
    return contexts


def manual_lifecycle_stub(partner):
    slug='manual-'+partner['slug']
    return dict(id=slug,partner_id=partner['id'],partner=partner['display_name'],partner_slug=slug,
                profile_slug=partner['slug'],origin='MANUAL',receive=[],give=[],receive_count=0,give_count=0,album_count=0)
