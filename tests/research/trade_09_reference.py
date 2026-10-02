"""Render the actual frozen production list with synthetic read-only dependencies."""
from pathlib import Path
from types import SimpleNamespace
from flask import Flask
from tests.test_sticker_wall_product_island import webapp
from sticker_list import register_sticker_list_routes, StickerListDependencies
ROOT=Path(__file__).resolve().parents[2]


def reference_html():
    def forbidden(*args,**kwargs):raise AssertionError('Reference must not mutate/read product DB')
    deps={field:forbidden for field in StickerListDependencies.__dataclass_fields__}
    codes=[f'BRA {n}' for n in range(1,9)]+[f'MEX {n}' for n in range(1,4)]
    rows={c:SimpleNamespace(availability=SimpleNamespace(physical=2,available=1,is_available=True)) for c in codes if c.startswith('MEX')}
    deps.update(load_album=lambda _:({'name':'WM 2026'},rows,3,3,0,11),all_codes=lambda _:codes,display_code=lambda c:c,
        ceoklaue_run=webapp.ceoklaue_runtime_run,ceoklaue_mix_index=webapp.ceoklaue_runtime_mix_index,
        ceoklaue_marker_asset=webapp.ceoklaue_marker_asset,bracket_button_content=webapp.ceoklaue_bracket_button_content,
        feedback_html=lambda *a:'',consume_trophy_popup_html=lambda *a:'',app_header_brand_wordmark=webapp.app_header_brand_wordmark,
        global_head=webapp.style,bottom_nav=lambda *a:'',ceoklaue_mixing_seed=webapp.CEOKLAUE_RUNTIME_MIXING_SEED)
    app=Flask('trade09_reference',template_folder=str(ROOT/'App/templates'))
    app.secret_key='isolated-synthetic-reference-only'
    register_sticker_list_routes(app,deps)
    with app.test_client() as client:
        response=client.get('/album/wm26/liste');assert response.status_code==200
        return response.get_data(as_text=True)
