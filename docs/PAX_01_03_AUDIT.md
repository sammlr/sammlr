# PAX-01–03 — isolierter klickbarer Pfad

Stand: 2026-09-28. Kanonisch: [PAX-00](SAMMLRPAX_CONTRACT_V1.md), vollständig vor Umsetzung gelesen. Keine produktive Integration; ausschließlich Fixture-GETs und lokaler Browserzustand.

## Audit vor Implementierung

| Punkt | Lokalisierte Quelle | Verwendung / Schutz |
| --- | --- | --- |
| A Journey V2 | `App/templates/sammlrpax_journey_v2.html`, `App/static/sammlrpax_journey_v2.{css,js}` | Referenz; unverändert. Keine alte Packprüfung übernehmen |
| B Lila Pack | V1-Template `.pj-pack`, `sammlrpax_journey_v1.css` mit `.pj-pack*`, `.pj-seal*`, `pj-pack-open` | Markup als eigenes Macro, Original-CSS direkt lesen; Originalanimation |
| C Stickerface | `App/webapp.py`: `sticker_wall_card_inner`, `sammlr_retro_number_svg` | Isolierter Renderer gleicher SVG-V3-Faces/Prefix; kein Import der Produktiv-App |
| D LOCKED Stack | `App/static/style.css`: `.sticker-slot-frame`, `.sticker-wall-stack-layer`, `.s30-album-page .slot`; `sticker_wall_slot_html` | Basiskarte verankert, zusätzliche Karten 2 px nach oben/links, höchstens fünf sichtbar. Keine Änderung an Renderer/CSS; Paketmenge separat vom Inventory |
| E Post-its | `App/static/sticker_list.css`: `.trade-postit*`, `.sticker-list-review-codes`, `.pending-review-row` | Originale 224-px-Zettel und Schrift-/Zeilenregeln isoliert spiegeln |
| F Review-Renderer | `App/static/sticker_list.js`: `stickerListRenderReviewMode` | Chunks und Ein-/Zweispaltenwechsel pro Album wiederverwenden |
| G 16/20 | `STICKER_LIST_REVIEW_FIRST_NOTE_CAPACITY=16`, `CONTINUATION_NOTE_CAPACITY=20`, Spalten 8/10 | 16, 17, 36, 37, 56 als Testgrenzen; Fortsetzungen ohne Überschrift. Exemplare separat, Album/Code/Instance-Schlüssel |
| H Handschrift | `stickerListCeoklaueIndex`, `stickerListWriteCeoklaue`, CEOKlaue Final Alt 1–3, vorhandene WOFF2 | Reine Helpers spiegeln, keine andere Handschrift |
| I Durchstreichen | `App/sticker_list.py:list_item`, `.selected`, `.sticker-selection-marker`, `.marker-draw-*` | Lokalisiert, hier NICHT aktivieren: keine Buttons/Marker/Checkboxen in Give |
| J Registrierung | `App/trade_visual_preview.py:register_trade_visual_preview`, `App/sammlrpax_journey_v2_preview.py:create_app` | Neue eigene App + Blueprint; bestehende Registrierungen und `webapp.py` unangetastet |

Zusätzliche Referenzen: `tests/test_ceoklaue_sticker_list.py` (16/20-Grenzen), `tests/test_sticker_wall_product_island.py` und `tests/research/check_vertical_stacks.py` (geschützter Stack). Vorhandene Tests werden nicht geändert.

## Geplanter isolierter Scope

`App/pax` enthält nur App-Factory, Startmodul, GET-Blueprint und synthetische Fixtures. Keine Domain-/DB-Imports. Neue Templates und Assets ausschließlich unter `pax/`. Reuse des bewährten gekapselten CSS-Spiegels aus Journey V2, ergänzt um die originalen Review-Spaltenregeln. Alle Kartenregeln bleiben innerhalb des neuen Boards; kein globaler Stack-Override.

Fünf Kandidaten mit verschiedenen Größen; Fatima 23/23 über sechs Alben. Justus enthält ein Give-Album mit 37 Exemplaren für die sichtbare 16/20/1-Fortsetzung, einschließlich wiederholtem Code mit separaten Instanzen. Dies sind keine echten User, Bestände oder berechneten Domainangebote. Keine erfundenen Qualitätsscores. Kein Verwerfen implementiert (optional im Auftrag).

Start: `cd '/Users/valy/Desktop/sammlr.' && .venv/bin/python -B -m App.pax`
URL: `http://127.0.0.1:8094/pax/`

## Abnahme

Abnahme bestanden; Nachweise unten. Keine POST-Route, Anfrage, Reservation, Slot- oder Bestandsmutation. Kein git add/Commit/Push/Deploy.

### Ausgeführte Prüfungen

- `.venv/bin/python -B -m unittest tests.test_pax_preview`: 5/5 erfolgreich; nur isolierte GET-Routen, POST 405, unbekannte Kandidaten 404, Fixture-Zahlen/Instanzen, DB-Zugriff blockiert und kein produktiver App-Import.
- `.venv/bin/python -B tests/research/check_pax_01_03.py`: alle fünf Kandidaten bei 375/390/430 px geprüft. Keine horizontalen Überläufe, Textabschneidungen oder Karten-/Albumkollisionen; individuelle Fans und Zusammenlegen, unveränderte andere Album-DOMs, lesbare Fortsetzungen, erreichbarer CTA, Rückkehr/Reload geprüft. Keine Browserfehler oder schreibenden Requests, kein Local-/Session-Storage.
- Neun Chunking-Grenzfälle: 0, 8, 9, 16, 17, 36, 37, 56, 57; Reihenfolge und alle Exemplare erhalten. 37 → 16/20/1 sichtbar, ein Albumtitel, 10 Zeilen je Fortsetzungsspalte; größere Abstände zwischen neuen Albumgruppen.
- `tests/research/check_pax_component_parity.py`: Original-Pack und produktive Karten-/Stack-CSS mit berechneten Browserstilen und Geometrie bei 375/390/430 verglichen; identisch. Testinitiallauf aus inhaltsgleicher temporärer Datei. Kein Produktiv-App-Import.
- SHA-256-Vorher/Nachher-Abgleich aller vorbestehenden Dateien unter App/docs/tests erfolgreich: keine bestehende Datei geändert, einschließlich DB, Domain, produktiver Stack/Stickerliste sowie V1/V2.
- `git diff --check` und zusätzliche `git diff --no-index --check /dev/null <Datei>`-Prüfung neuer Textdateien erfolgreich. Keine Full Suite notwendig oder ausgeführt.

Screenshots: [Galerie bei 390 px](../tests/research/artifacts/pax-01-03/index.html). Browserprotokoll: [checks.json](../tests/research/artifacts/pax-01-03/checks.json).

### Vollständiges Manifest neuer Dateien

- `App/pax/__init__.py`
- `App/pax/__main__.py`
- `App/pax/fixtures.py`
- `App/pax/routes.py`
- `App/static/pax/components.css`
- `App/static/pax/pax.css`
- `App/static/pax/pax.js`
- `App/templates/pax/_pack.html`
- `App/templates/pax/base.html`
- `App/templates/pax/detail.html`
- `App/templates/pax/discovery.html`
- `docs/PAX_01_03_AUDIT.md`
- `tests/research/artifacts/pax-01-03/01-discovery-390.png`
- `tests/research/artifacts/pax-01-03/02-closed-390.png`
- `tests/research/artifacts/pax-01-03/03-album-stacks-390.png`
- `tests/research/artifacts/pax-01-03/04-single-album-fan-390.png`
- `tests/research/artifacts/pax-01-03/05-give-postits-390.png`
- `tests/research/artifacts/pax-01-03/06-continuation-16-20-1-390.png`
- `tests/research/artifacts/pax-01-03/07-demo-end-390.png`
- `tests/research/artifacts/pax-01-03/checks.json`
- `tests/research/artifacts/pax-01-03/index.html`
- `tests/research/check_pax_01_03.py`
- `tests/research/check_pax_component_parity.py`
- `tests/test_pax_preview.py`

Geänderte vorbestehende Dateien: **KEINE**. Keine POST-Route; keine Anfrage, DB-Mutation, Reservation, Slotmutation oder Inventorybuchung. Kein git add, Commit, Push oder Deploy. STOP nach Abnahme.
