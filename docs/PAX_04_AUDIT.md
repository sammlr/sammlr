# PAX-04 — Kioskbox / Register-Browsing

Abschluss: 2026-09-29. Grundlage: SAMMLRPAX_CONTRACT_V1 und PAX-01–03-Audit; bestehende App/pax-Module, Templates, Interaktionscode und kanonische Stack-/Review-Regeln vor Änderung geprüft.

## Umsetzung

Feste neutrale Kioskbox mit fünf persistenten Pack-DOM-Elementen. Down-Drag bewegt das vordere Element ans Ende, Up-Drag das letzte nach vorne. Kurzer Registerwechsel, keine ersetzten Partnertexte auf einer einzigen Karte. Reihenfolge und Fixtures unverändert. Nur die aktuelle Vorderseite ist fokussierbar; dezente Zurück/Weiter-Controls, Pfeiltasten, Enter/Space sowie sinnvolle ARIA-Texte. Keine Wheel-Übernahme; Seitenscroll außerhalb der Packs bleibt normal.

Drag-Schwelle 55 px, Tap-Toleranz maximal 6 px; kleine/horizontale Drags öffnen kein Pax. Pointer-Capture und Cancel-Behandlung. Reduzierte Bewegung wird berücksichtigt. Zurückkehrende Discovery startet sauber mit Fatima, auch im Back-forward-Cache. Tap/Klick reißt das konkrete Front-Pack auf und öffnet dessen Inhalt ohne zweiten Öffnen-CTA. Anfrage bleibt eine bewusste separate lokale Demo-Aktion.

Receive kompakt zweispaltig; ein aufgefächertes Album nutzt die volle Zeile, beim Schließen kehrt es in das Grid zurück. Stickerfaces und interne Stack-Geometrie unverändert. Handschrift nur in Post-its. Give-Fortsetzungen überlappen um 8 px Layoutabstand; sichtbare Textbereiche bleiben frei. 16/20/Rest sowie Mehrfachexemplare unverändert. Keine Packprüfung in dieser Phase.

## Prüfungen

- 6/6 fokussierte Tests: `.venv/bin/python -B -m unittest tests.test_pax_preview`.
- Browser: `.venv/bin/python -B tests/research/check_pax_04.py` — 375/390/430 px erfolgreich: vollständiger Vorwärts-/Rückwärtszyklus, DOM-Identität, feste Box, sichtbare hintere Ränder, Tap/Drag getrennt, richtige Justus-Daten, alle fünf Kandidaten, direkte Öffnung, Rückkehr, zweispaltige Receive-Anordnung, Fans ohne Kollisionen, erreichbarer CTA, keine horizontalen Überläufe. Neun kanonische Chunking-Grenzen erhalten.
- Touch über echte Chromium-Touch-Events, Enter/Space/Pfeiltasten und Reduced Motion bei 390 px erfolgreich.
- `.venv/bin/python -B tests/research/check_pax_component_parity.py` — Pack-Innenlayout sowie Karten-/Stack-Stile und -Geometrie bei 375/390/430 px mit Originalquellen identisch. Die äußere Pack-Positionierung ist absichtlich die neue Registeranordnung.
- Historischer Browser-Einstieg `check_pax_01_03.py` delegiert nun an den aktuellen Gate, weil dessen Listen-/Zwischenklick-UX ausdrücklich ersetzt wurde. Historische Screenshots und Audit bleiben unverändert.
- Keine JS-Fehler oder schreibenden Browserrequests. GET-only-App und abgewiesene POSTs durch fokussierte Tests bestätigt. Keine neue Route, DB-Mutation, Reservation, Inventory- oder Slotmutation.
- SHA-256-Abgleich aller vorbestehenden App/docs/tests-Dateien: nur die unten genannten acht erlaubten Dateien verändert. Produktive Stack-/Listen-/Trade-/Domain-Dateien, DB, Fixtures, Komponenten-CSS, PAX-00 und V1/V2 bytegleich.
- `git diff --check` sowie Whitespace-Prüfung aller geänderten/neuen Textdateien bestanden. Keine Full Suite erforderlich.

## Geänderte bestehende Dateien

- `App/static/pax/pax.css`
- `App/static/pax/pax.js`
- `App/templates/pax/base.html`
- `App/templates/pax/detail.html`
- `App/templates/pax/discovery.html`
- `tests/research/check_pax_01_03.py`
- `tests/research/check_pax_component_parity.py`
- `tests/test_pax_preview.py`

## Neue Dateien

- `docs/PAX_04_AUDIT.md`
- `tests/research/check_pax_04.py`
- `tests/research/artifacts/pax-04/index.html`
- `tests/research/artifacts/pax-04/checks.json`
- `tests/research/artifacts/pax-04/01-fatima-front-390.png`
- `tests/research/artifacts/pax-04/02-justus-front-390.png`
- `tests/research/artifacts/pax-04/03-luca-front-390.png`
- `tests/research/artifacts/pax-04/04-fatima-receive-390.png`
- `tests/research/artifacts/pax-04/05-album-fan-390.png`
- `tests/research/artifacts/pax-04/06-give-albums-390.png`
- `tests/research/artifacts/pax-04/07-continuation-16-20-rest-390.png`
- `tests/research/artifacts/pax-04/08-cta-390.png`

Außerhalb des isolierten Pax-Pfads und zugehöriger Tests/Docs: **keine Änderung**.

## Öffnen

```sh
cd '/Users/valy/Desktop/sammlr.' && .venv/bin/python -B -m App.pax
```

URL: http://127.0.0.1:8094/pax/

[Galerie: acht Screenshots bei 390 px](../tests/research/artifacts/pax-04/index.html) · [Browserprotokoll](../tests/research/artifacts/pax-04/checks.json).

Kein git add, Commit, Push oder Deploy. STOP nach Abschluss.
