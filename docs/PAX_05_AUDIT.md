# PAX-05 — Anfrage, Annahme und Packphase

Preview: http://127.0.0.1:8094/pax/

Frische Journey: http://127.0.0.1:8094/pax/fatima?demo=opened

[Screenshot-Galerie, neun Ansichten bei 390 px](../tests/research/artifacts/pax-05/index.html).

## Grundlagen und Abgleich

Vor Umsetzung gelesen: `SAMMLRPAX_CONTRACT_V1.md`, `PAX_01_03_AUDIT.md`, `PAX_04_AUDIT.md`, `PAX_04B_AUDIT.md`, `PAX_04C_AUDIT.md`, `PAX_CAP10_AUDIT.md`. Ältere Register-/Stack-Experimente sind durch PAX-04b/04c und den finalen Cap10-Auftrag überholt. Finale Discovery, Face-/Stack-Geometrie und Post-it-Chunking bleiben verbindlich.

Produktive Quellen ausschließlich gelesen:

- `App/services/smartdeal_acceptance.py`: Empfängerautorisierung, absolute Frist, idempotente Annahme, Snapshot-/Ausführbarkeitsprüfungen und Transaktionsgrenze. Keine produktiven Services aus der Demo aufgerufen.
- `App/services/smartdeal_expiry.py`: absolute 24 Stunden ab `binding_created_at`; keine Verlängerung bei Retry.
- `App/services/smartdeal_release.py`: getrennte Withdraw-/Decline-Autorisierung, Pending-Expiry und idempotente Freigabe.
- `App/services/trade_shipping.py`: physische Richtungen, eigener Versand genau einmal, Reservierungen und atomare Bestandsbuchung. Packmarkierung ersetzt keine dieser Aktionen.
- `App/webapp.py`: bestehende Accept-/Ship-HTTP-Flows und Serviceanschlüsse. Unverändert; keinerlei Registrierung des Pax-Pfads in der produktiven App.
- `App/sticker_list.py` und `App/static/sticker_list.css`: vorhandene Give-Cross-Assets und Post-it-Mengenlogik. Nur vorhandene Cross-Assets zur lokalen Packmarkierung verwendet, ohne produktive Listen-/Transferwirkung.

Kein Domainkonflikt. AC23 bleibt gültig. **PO review before productive Pax integration** bleibt offen; kein Amendment-, Kapazitäts-, Adress- oder Versandvertrag vorweggenommen.

## Lokaler Demo-Vertrag

Ein eingefrorener Fixture-Snapshot pro Kandidat ist die einzige Dealquelle. Sender RECEIVE ist Empfänger GIVE und umgekehrt. Es gibt keine separat gepflegten Partnerlisten. Alben, Reihenfolge, Codes und einzelne Exemplarschlüssel bleiben erhalten.

Reines Browsermodell in `lifecycle.js`: discovery → pending → packing beziehungsweise withdrawn/declined/expired. Nur Sender darf anfragen/zurückziehen, nur Empfänger darf annehmen/ablehnen. Pending läuft exakt nach 24 absoluten Stunden ab; Retry verjüngt die Frist nicht. Bereits angenommene Deals verfallen nicht durch Pending-Expiry. Der UI-Status ACTIVE / PACKING ist nur Preview-State, kein neuer DB-Lifecycle.

`sessionStorage` speichert Zustand, Rollenansicht und simulierten Zeitoffset pro Kandidat und Tab. Reload erhält Bindungszeit und Packmarkierungen; unterschiedliche Tabs sind ausdrücklich keine synchronisierte Mehrbenutzeranwendung. Die kanonischen Listen werden nicht aus dem gespeicherten Zustand rekonstruiert. Fixture-Signatur und validierte Zustandsschlüssel verhindern Übernahme unpassender/veralteter Demo-Daten. Bei gesperrtem Storage bleibt der In-Memory-Pfad nutzbar und weist auf die fehlende Reload-Persistenz hin.

Anfrage/Annahme benötigen keine Packprüfung. Nach Annahme wird die eigene Give-Liste interaktiv; Receive ist sekundär einklappbar und bleibt rein informativ. Jeder Eintrag ist ein nativer Button mit `aria-pressed`, Keyboard-/Touch-Bedienung und Fokusmarkierung. Vorhandene Give-Cross-Grafiken markieren einzelne physische Exemplare ohne Layoutsprung. Die beiden Rollen speichern unabhängige Packmarkierungen. 16/20-Fortsetzung, Rotationen und Albumabstände unverändert.

Fortschritt aktualisiert sich live. Der Versand-CTA wird erst bei vollständiger eigener Packliste aktiv. Ein separater Weg für offene Einträge zeigt genaue Alben/Codes/Exemplare. Zurückgehen erhält die Markierungen. „Sticker fehlen wirklich“ endet ohne Paketänderung am späteren Amendment-Schritt. Vollständig endet bei „Packprüfung abgeschlossen. Versand folgt in PAX-06.“ Beide Wege buchen nichts, ändern nicht den Snapshot und zeigen keine Adresse.

## Demo-Navigation

Auf jeder Detailseite unten: **PREVIEW / DEV · PAX-05**. Rollenwechsel zeigt denselben Deal. Szenarioauswahl erzeugt bewusst eine neue lokale Demo, unabhängig von Produktaktionen.

Query-Einstiege `/pax/fatima?demo=…`:

| Wert | Ansicht |
| --- | --- |
| opened | B · Pax geöffnet |
| waiting | C · Sender wartet |
| received | D · Empfänger erhält Anfrage |
| packing-sender | E · Sender packt |
| packing-recipient | F · Empfänger packt |
| partial | G · 21/23 eingepackt |
| complete | H · 23/23 eingepackt |

A: `/pax/`. Der Query-Szenarioparameter wird nach einmaliger Initialisierung entfernt, damit Reload keine Frist/Markierungen zurücksetzt. „Zeit +24 Stunden“ prüft den Ablauf sichtbar; zusätzlich aktualisiert ein Timer offene Anfragen ohne weiteren Klick.

## Tests und Ergebnisse

- `.venv/bin/python -B -m unittest tests.test_pax_preview`: **6 bestanden**. GET-only, POST abgewiesen, alle Fixtures, unbekannte IDs, keine DB-Verbindung und kein produktiver App-Import.
- `.venv/bin/python -B -m unittest tests.test_sticker_wall_product_island tests.test_ceoklaue_sticker_list`: **29 bestanden**. Produktiver Wall-Cap5 und kanonische Listenregeln geschützt.
- `.venv/bin/python -B tests/research/check_pax_05.py`: Journey bei **375/390/430 px bestanden**. Anfrage ohne Checkliste; Reload-Persistenz; exakte Spiegelung; Annahme; separate Packlisten; Touch/Space/Enter/Fokus; Undo; gleichbleibende Post-it-Rechtecke; 21/23 mit zwei exakten offenen Instanzen; kontrollierte Endpunkte; Decline/Withdraw/Expiry; Accepted bleibt aktiv; Justus-Duplikate und 16/20/1; kein Overflow/Abschneiden; keine JS-/Assetfehler; keine schreibenden Browserrequests.
- Im selben Browsergate: reine Modellprüfungen für alle fünf Kandidaten, eingefrorene Snapshots, eindeutige Instanzen, Rollen- und Zustandsgrenzen, Bindungszeit unverändert bei Retry, Annahme bei 24h−1ms erlaubt und ab 24h ausgeschlossen, keine fremden Packkeys, getrennte Seiten, vollständige eigene Packliste als Voraussetzung. Live-Ablauf einer offen gelassenen Warteansicht zusätzlich mit simulierter Browserzeit geprüft.
- `.venv/bin/python -B tests/research/check_pax_04c.py`: bestehende Discovery-/Detail-/Fan-/Post-it-Regression bestanden; erwarteter früherer Demo-Endpunkt auf die jetzt angeforderte Warteansicht angepasst.
- `.venv/bin/python -B tests/research/check_pax_cap10.py`: **21 Fälle bestanden**; Mengen 1/2/5/6/10/15/37 bei drei Breiten gegen tatsächlichen produktiven BRA-3-Renderer. Wall5/Pax10, −2/−2, z-index, Faces/Dimensionen; 10/15/37 geometrisch identisch.
- Pixelvergleich aktueller Discovery-Screenshots mit PAX-04b: **375/390/430 identisch**.
- Visuelle Prüfung der Journey-Screenshots, insbesondere Empfänger, Packmarkierungen, fehlende Sticker, Vollständigkeit und Warteansicht.
- SHA-256-Abgleich aller vor Umsetzung erfassten App-/Docs-/Testdateien: nur unten aufgeführte Änderungen. Produktive DB inklusive Trades, Produktivdateien, kanonische Komponenten-CSS, Fixtures, Domainvertrag und V1/V2 unverändert.
- `git diff --check` und zusätzliche `git diff --no-index --check /dev/null DATEI` für alle neuen/geänderten Textdateien bestanden.

## Explizite Abgrenzung

**Keine Produktiv-DB verändert. Keine produktiven Dateien außerhalb des vereinbarten Pax-/Test-/Doc-Bereichs verändert. Keine produktiven POST-Requests, Reservations-, Slot- oder Bestandsmutationen. Keine Migration bestehender Trades. Kein git add, kein Commit, kein Push, kein Deploy.**

Kein Versand, keine Adresse/DHL-Anbindung, kein Amendment, kein Empfang, keine Bewertung oder Historie implementiert. Bestehende produktive Mechaniken sind als spätere Integrationsanschlüsse dokumentiert; die Demo ersetzt sie nicht.

## Exakte Dateiliste

Geändert:

- `App/templates/pax/detail.html`
- `App/static/pax/pax.js`
- `tests/research/check_pax_04c.py`
- `tests/research/artifacts/pax-04c/layer-comparison-375.png`
- `tests/research/artifacts/pax-04c/08-cta-390.png`

Neu:

- `App/static/pax/journey.css`
- `App/static/pax/journey.js`
- `App/static/pax/lifecycle.js`
- `docs/PAX_05_AUDIT.md`
- `tests/research/artifacts/pax-05/01-discovery.png`
- `tests/research/artifacts/pax-05/02-opened.png`
- `tests/research/artifacts/pax-05/03-waiting.png`
- `tests/research/artifacts/pax-05/04-recipient.png`
- `tests/research/artifacts/pax-05/05-packing-zero.png`
- `tests/research/artifacts/pax-05/06-packing-partial.png`
- `tests/research/artifacts/pax-05/07-missing.png`
- `tests/research/artifacts/pax-05/08-packing-complete.png`
- `tests/research/artifacts/pax-05/09-pack-endpoint.png`
- `tests/research/artifacts/pax-05/checks.json`
- `tests/research/artifacts/pax-05/index.html`
- `tests/research/artifacts/pax-05/scope-check.json`
- `tests/research/check_pax_05.py`
