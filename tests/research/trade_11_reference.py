"""Actual production wall renderer; synthetic inventory, temporary reference DB only."""
from tests.test_sticker_wall_product_island import webapp,ReadOnlyInventory

def wall_html():
    wall=webapp.canonical_sticker_wall_html('wm26',{'BRA1':{'quantity':6}},ReadOnlyInventory(),'all',can_edit_inventory=False)
    return '<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/static/style.css"></head><body class="s31-product-page s30-reference-page s30-album-page"><div class="container"><div class="card sticker-wall-card">'+wall+'</div></div></body></html>'
