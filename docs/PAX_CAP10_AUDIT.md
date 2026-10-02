# Pax Receive: kanonischer Stack, Cap 10

Nur `maxVisibleLayers = 10` im Pax-Receive-Renderer; kein abweichender Perspektiv-, Drift- oder Extrusionsparameter. Auch der frühere Vergleich kann den Cap nicht mehr überschreiben. Front und Back verwenden unveränderte kanonische CSS-Regeln: Index i, Translation −2i/−2i, z-index i+1. Frontdimensionen und Face bleiben unverändert. Produktive Wall unverändert mit Cap 5.

Der Browsertest ruft den tatsächlichen produktiven `sticker_wall_slot_html`-Renderer für BRA 3 mit synthetischen Mengen auf. Import erfolgt über das bestehende Testmodul mit temporärer Testdatenbank; keine produktive DB-Verbindung. Rendering ist read-only. Vergleich der Front-/Back-Eigenschaften mit originaler produktiver CSS, nicht bloß mit kopiertem Pax-Markup. Wall-Bestandsbadge gehört nicht zum unveränderten Pax-Frontinhalt.

Prüfungen:

- `check_pax_cap10.py`: Mengen 1/2/5/6/10/15/37 bei 375/390/430; 21 Fälle. Layerzahl, −2/−2-Versatz, z-index, Face-/Kartendimensionen; Geometrie von 10/15/37 identisch.
- `check_pax_04c.py`: mobile Discovery, Touch/Keyboard, einzelne Album-Toggles, Kollisionen/Overflow, Post-it-16/20, CTA, deterministische Posen und aktualisierte Vergleichsansicht.
- `python -B -m unittest tests.test_pax_preview`: 6 bestanden.
- `python -B -m unittest tests.test_sticker_wall_product_island tests.test_ceoklaue_sticker_list`: 29 bestanden.
- SHA-256-Abgleich: produktive Wall/JS/CSS, kanonische Pax-CSS-Kopie, DB und Domainvertrag unverändert.
- `git diff --check`, zusätzliche Whitespace-Prüfung neuer/geänderter Textdateien.

Preview: http://127.0.0.1:8094/pax/layer-comparison

[Direkter BRA-3-Bildvergleich](../tests/research/artifacts/pax-cap10/index.html).

Geänderte bestehende Dateien (inklusive aktualisierter Testartefakte):

- `App/pax/layer_comparison.html`
- `App/static/pax/pax.js`
- `tests/research/check_pax_04c.py`
- `tests/research/artifacts/pax-04c/layer-comparison-375.png`
- `tests/research/artifacts/pax-04c/layer-comparison-390.png`
- `tests/research/artifacts/pax-04c/04-fatima-receive-390.png`
- `tests/research/artifacts/pax-04c/layer-comparison-430.png`
- `tests/research/artifacts/pax-04c/03-large-receive-390.png`

Neu: `tests/research/check_pax_cap10.py`, dieser Bericht und `tests/research/artifacts/pax-cap10/` (acht PNGs, Galerie, Checks und Scope-Abgleich).
