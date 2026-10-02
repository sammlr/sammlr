# PAX-04c Audit

Preview: http://127.0.0.1:8094/pax/

Layer-Vergleich: http://127.0.0.1:8094/pax/layer-comparison

Galerie: [Screenshots](../tests/research/artifacts/pax-04c/index.html).

## Umsetzung

Kanonische Stack-Indizes, 2-px-Versatz links/oben, unverändertes Face-Markup, CSS und z-index werden wiederverwendet. Sichtbare Layer zählen die Frontkarte mit. Vergleich: 7/10/12/15/18/20/22/27/35. Kein finaler Pax-Cap gewählt. Normale Details verwenden vorläufig das bestehende Wall-Limit 5. Die PAX-04b-Sondergeometrie wurde im isolierten Pax-Renderer entfernt. Die produktiven Wall-Dateien und die scoped kanonische CSS-Kopie bleiben bytegleich.

Nur aufgefächerte Karten und Give-Post-its erhalten deterministische, schlüsselbasierte Abweichungen: ±0,35 bis ±0,95 Grad; Fan-Karten zusätzlich höchstens ±1 px je Achse. Fortsetzungsabstand und Albumabstand bleiben unverändert. Kein Zufall, keine Änderung an Inhalt, Reihenfolge oder 16/20-Chunking.

## Ausgeführte Tests

- `.venv/bin/python -B -m unittest tests.test_pax_preview`: 6 bestanden.
- `.venv/bin/python -B -m unittest tests.test_sticker_wall_product_island tests.test_ceoklaue_sticker_list`: 29 bestanden.
- `.venv/bin/python -B tests/research/check_pax_04c.py`: bestanden bei 375/390/430; Klick/Touch/Tab/Enter/Space/Reduced Motion, fünf Packs, sechs Fatima-Alben, individuelles Öffnen/Schließen, keine Kartenkollisionen/Überläufe, CTA erreichbar, Fortsetzungen 16/20/1 und Chunk-Grenzen, keine schreibenden Browserrequests oder JS-/Assetfehler. Neuladen erhält identische Posen. Alle neun Vergleichsmengen auf allen drei Breiten geprüft.
- `.venv/bin/python -B tests/research/check_pax_component_parity.py`: Front- und Back-Layer-Geometrie/CSS gegen produktive CSS-Referenz bei 375/390/430.
- Discovery-Screenshots pixelgleich zu PAX-04b bei allen drei Breiten.
- SHA-256-Abgleich aller vorab erfassten App-/Docs-/Test-Dateien: Änderungen nur in der folgenden Liste. Produktive Webapp, DB, Domainvertrag, Fixtures, kanonische Komponenten und V1/V2 unverändert.
- `git diff --check` sowie `git diff --no-index --check /dev/null DATEI` für alle neuen/geänderten Textdateien.
- Screenshots visuell geprüft: Layer-Vergleich, Fan und Post-it-Fortsetzung.

Kein Commit, Push oder Deploy. Keine echten Requests, Reservationen, Slots oder DB-Mutationen.

## Exakte Dateiliste

Geändert:

- `App/pax/routes.py`
- `App/static/pax/pax.js`
- `App/static/pax/pax.css`
- `tests/test_pax_preview.py`
- `tests/research/check_pax_04b.py`
- `tests/research/check_pax_component_parity.py`

Neu:

- `App/pax/layer_comparison.html`
- `docs/PAX_04C_AUDIT.md`
- `tests/research/artifacts/pax-04c/01-discovery-375.png`
- `tests/research/artifacts/pax-04c/01-discovery-390.png`
- `tests/research/artifacts/pax-04c/01-discovery-430.png`
- `tests/research/artifacts/pax-04c/03-large-receive-390.png`
- `tests/research/artifacts/pax-04c/04-fatima-receive-390.png`
- `tests/research/artifacts/pax-04c/05-album-fan-390.png`
- `tests/research/artifacts/pax-04c/06-give-albums-390.png`
- `tests/research/artifacts/pax-04c/07-continuation-16-20-rest-390.png`
- `tests/research/artifacts/pax-04c/08-cta-390.png`
- `tests/research/artifacts/pax-04c/checks.json`
- `tests/research/artifacts/pax-04c/index.html`
- `tests/research/artifacts/pax-04c/layer-comparison-375.png`
- `tests/research/artifacts/pax-04c/layer-comparison-390.png`
- `tests/research/artifacts/pax-04c/layer-comparison-430.png`
- `tests/research/artifacts/pax-04c/scope-check.json`
- `tests/research/check_pax_04c.py`
