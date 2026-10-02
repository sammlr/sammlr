# TRADE-02 — Direkt zum Deal, Anfrage und Wartezustand

## Ergebnis und Preview

Die Sender-Journey funktioniert ohne Zwischenzustand: Tauschen → Top-Stapel → vollständiger Deal → **Tauschanfrage senden** → **Wartet auf Fatima**. Kein zusätzlicher Dialog, kein Mini-Fächer oder „Tausch ansehen“-Zwischenbutton. Partnerpool und beide Partnerprofil-Aktionen bleiben erhalten.

Server unverändert isoliert auf Port 8095. Start im Projektordner:

```sh
.venv/bin/python -B -m App.trade_v2
```

- Start: http://127.0.0.1:8095/trade-v2/
- Fatima-Deal: http://127.0.0.1:8095/trade-v2/deals/fatima
- Wartezustand nach Senden: http://127.0.0.1:8095/trade-v2/requests/fatima
- Direkte gesendete **Demo**: http://127.0.0.1:8095/trade-v2/requests/fatima?demo=sent
- 0/3: http://127.0.0.1:8095/trade-v2/deals/fatima?demo=0
- 2/3: http://127.0.0.1:8095/trade-v2/deals/fatima?demo=2
- 3/3: http://127.0.0.1:8095/trade-v2/deals/fatima?demo=3
- Partnerpool: http://127.0.0.1:8095/trade-v2/partners
- Karlheinz: http://127.0.0.1:8095/trade-v2/partners/karlheinz

Die ausdrücklich benannten Demo-Query-Einstiege setzen die lokale Sitzung bewusst zurück. Der Parameter wird sofort aus der URL entfernt; Reload erzeugt keine neue Anfrage und erneuert keine Frist. Ohne vorhandene Anfrage zeigt die normale Status-URL „Noch keine Anfrage gesendet“, keine erfundene Sendebestätigung.

[Galerie](../tests/research/artifacts/trade-02/index.html) · [kanonischer Stackvergleich](../tests/research/artifacts/trade-02/stack-comparison.html) · [bestehende mobile Regression](../tests/research/artifacts/trade-02/regression/index.html).

## Grundlage und Ausgangszustand

Gelesen/berücksichtigt: `TRADE_PRODUCT_CONTRACT_V2.md`, `TRADE_00_RESET_AUDIT.md`, `TRADE_01_AUDIT.md`, relevante Algorithmus-/Mengen-/Manual-Offer-Regeln, operative 3/3-Regel und AC23 sowie `PAX_CAP10_AUDIT.md`. Bestehende isolierte Darstellungsrenderer und Tests bleiben Referenz; kein Pax-Produktmodell.

TRADE-01 besaß einen Mini-Fächer mit zusätzlichem Detail-Link und einen reinen Anfrage-Platzhalter. Der aktuelle Auftrag ersetzt ausdrücklich diesen UX-Zwischenschritt aus §3 des V2-Contracts. Dies ist eine autorisierte gezielte UX-Weiterentwicklung, keine ungelöste Domainkollision; bestehende Contract-Dateien wurden nicht geändert.

Die Formulierung „3 gleichzeitig offene Anfragen“ wird im hier implementierten Pending-Sender-Scope umgesetzt, **nicht** als Abschaffung der getrennten drei eingehenden/drei ausgehenden operativen Slots oder als Freigabe durch bloße Annahme. Diese bereits entschiedenen Sicherheitsgrenzen gelten weiter.

## Direktklick und Darstellung

Alle fünf Top-Vorschläge sind native Links auf ihren vollständigen Deal. Enter ist nativ, Space aktiviert den Link einmal; keine div-onclick-Lösung. Der vorherige Mini-Fächer samt Zwischenbutton wurde entfernt. Keine zusätzlichen SmartDeal-/Manual-Optionen innerhalb des Top-Pfads.

Die geschlossene Startseite bleibt bei 375/390/430 px **pixelgleich** mit den TRADE-01-Screenshots. Keine neue Auslage oder kosmetische Überarbeitung. Receive-Alben bleiben innerhalb der vollständigen Detailansicht einzeln auffächerbar. Post-its, 16/20-Kapazität und bestehende Darstellung bleiben unverändert. Fatimas Fixture bleibt unverändert 23 Receive- und 23 Give-Positionen in sechs Alben.

## Request-State und Persistenz

Neue reine Demo-Logik in `requests.js`, eigener Controller in `sender.js`. Zustand ausschließlich unter `sessionStorage['sammlr-trade-02']` in diesem Tab, gemeinsam für alle Demo-Partner und Herkunftswege. Keine echte Anfrage, keine Notification, keine Reservierung, keine Inventar-/DB-Buchung oder Server-Session.

Datensatz: stabile Fixture-Command-ID, Herkunft, Anfragerichtung, Request-State, eigener Versandindikator, `bindingCreatedAt`, `expiresAt` und kopierter Snapshot. Die Sender-Journey erzeugt `pending`; Fristablauf setzt `expired`. Das Modell berücksichtigt vorbereitend `accepted` getrennt vom operativen Slot, bietet aber **keine Annahme-/Versandaktion** an.

Wiederholter Submit derselben Fixture-Chance liefert innerhalb dieser Demo-Sitzung denselben Request mit unveränderten Zeiten und unverändertem Snapshot. Eine Navigationssperre verhindert konkurrierende Redirects. Der Statuslink im bereits angefragten Deal führt wieder zur bestehenden Anfrage. Ein abgelaufener Datensatz wird durch Retry nicht neu gebunden. Ein expliziter DEV-Reset beginnt eine frische Demo.

Diese lokale Fixture-Identität ist keine neue produktive Regel für herkunftsübergreifende Gegenanfragen, Mutual-GO oder lebenslange Paket-Einmaligkeit. Die dazu offenen Domainentscheidungen werden nicht vorweggenommen. Geteilte Tabs, Mehrbenutzer-Synchronisierung und produktive Concurrency sind nicht implementiert.

SessionStorage wird vor jedem Sendebefehl erneut gelesen. Bei ungültigem/nicht verfügbarem Speicher wird nicht fälschlich ein erfolgreicher Request bestätigt; UI meldet den lokalen Fehler und sperrt das Senden. Gespeicherte Demo-Version, Zustandsfelder und Frist werden beim Laden geprüft. Keine stille Migration fremder Preview-Speicherstände.

## Kapazität und 24 Stunden

Gemeinsame ausgehende Kapazitätsprojektion unabhängig von `TOP_SUGGESTION`, `SMARTDEAL`, `MANUAL`. Demo-Belegung kann 0/3, 2/3 oder 3/3 vorgeben. Die zwei vorbereiteten Verpflichtungen haben verschiedene Herkünfte; eine weitere Top-Anfrage erreicht gemeinsam 3/3. Karlheinz-SmartDeal und Top-Anfrage belegen denselben lokalen Pool.

Bei 3/3 ist der CTA gesperrt; der Sendebefehl selbst prüft ebenfalls die Kapazität, auch bei künstlichem Event hinter einem disabled Button. Hinweis erläutert Freigabe etwa durch Ablehnung, Ablauf oder eigenen bestätigten Versand nach Annahme. Keine separaten Herkunftskontingente.

Request-State ist nicht Slot-State: `accepted` bleibt im reinen Modell operativ belegt, bis `ownShipped` wahr ist; eingehende und ausgehende Richtung sind getrennt testbar. Dies bereitet den vorhandenen Zielvertrag vor, implementiert aber weder Empfänger- noch Versandflow. Supply-/Need-Bindungen bleiben außerhalb dieser Demo; freie Kapazität ersetzt später keine Availabilityprüfung.

`expiresAt = bindingCreatedAt + 86.400.000 ms` als absolute Zeitspanne. Kein Reset bei Retry/Reload, keine lokale Tagesgrenze, keine Verlängerung durch Navigation. Pending wird bei `now >= expiresAt` abgelaufen und belegt keinen operativen Platz mehr. Die offene Statusseite aktualisiert Frist und Ablauf regelmäßig; angenommene Modellzustände werden nicht als Pending abgelaufen. Countdown plus lokales Fristende sichtbar; kein Adress-/Versandschritt und keine Checkliste im Wartezustand. AC23 bleibt unverändert.

## Tests

Ausgeführt:

```sh
.venv/bin/python -B -m unittest tests.test_trade_v2_preview tests.test_pax_preview
.venv/bin/python -B -m unittest tests.test_sticker_wall_product_island tests.test_ceoklaue_sticker_list
.venv/bin/python -B tests/research/check_trade_01.py
.venv/bin/python -B tests/research/check_trade_02.py
git diff --check
```

- **8 Preview-Tests bestanden:** bestehende Fixture-/GET-only-/No-DB-Isolation, neue Wartezustandsroute eingeschlossen; POST weiterhin 405.
- **29 bestehende Wall-/Listen-Tests bestanden.** Referenzharness verwendet ausschließlich temporäre Test-DB, keine produktive DB.
- **TRADE-01-Browsergate bestanden:** fünf direkte Einstiege, Partnerpool-Sortierung/Albumfilter, zwölf normalisierte Partner-SmartDeals, Karlheinz-Daten, Manual-Endzustand, unabhängige Receive-Fächer und Post-it-16/20/1. Nur ausdrücklich ersetzte Mini-Fächer-/CTA-Erwartungen angepasst. Historische TRADE-01-Artefakte bleiben erhalten; neue Regressionsergebnisse liegen unter `trade-02/regression/`.
- **21 Stack-Paritätsfälle:** Mengen 1/2/5/6/10/15/37 bei 375/390/430, tatsächlicher produktiver BRA-3-Renderer versus unveränderter wiederverwendeter Trade-Renderer. Front-/Back-Maße, Faces, Ziffern, Padding, Radien, Schatten, Farben, −2/−2 und z-index geprüft. Wall5, Trade10; Geometrie 10/15/37 identisch. Sechs direkte Vergleichsscreenshots für Mengen 6/10/37.
- **TRADE-02-Browsergate bei 375/390/430/1280 bestanden:** Direktklick, vollständige 23↔23, Anfrage/Warten, 0/3→1/3, 2/3→3/3, 3/3 blockiert, echter Doppelklick, acht synchrone Mehrfachaktivierungen, wiederholtes Enter/Touch, Reload, unveränderliche Zeiten, gemeinsame Top-/Partner-Kapazität, direkte Demo-URL ohne Reload-Neubindung, Live-Ablauf und Reload nach Ablauf.
- **Reine Modellprüfungen im Browser bestanden:** zwanzig Retries, unveränderter Input/kopierter Snapshot, absolute Frist, exakt 1 ms vor und auf der Deadline, Freigabe bei Ablauf, Accepted bleibt belegt, eigener Versandindikator gibt eigenen Platz frei, getrennte Richtungen, Wiederherstellung und Ablehnung defekter Speicherdaten. Kein zusätzlicher Lifecycle umgesetzt.
- Touch, Maus, Enter/Space; Reduced Motion. Kein horizontaler Overflow auf mobilen Ansichten oder Desktop, kein sichtbares verbotenes Produktwording, keine JS-/Assetfehler, keine externen/schreibenden Browserrequests.
- 16 Journey-Screenshots, 13 mobile Regression-Screenshots und sechs Stack-Vergleichsscreenshots. Wartezustand und blockierter weiterer Deal visuell geprüft; Startseite per Pixelvergleich unverändert.
- `git diff --check` und zusätzliche Whitespace-Prüfung aller neuen/geänderten Textdateien bestanden.

Während der Tests behoben: Mehrfachaktivierungen erzeugten zwar nur einen gespeicherten Request, aber mehrere konkurrierende Navigationen; zusätzliche Sendesperre verhindert dies. Die simulierte Testuhr musste vor der Registrierung des Seitentimers installiert werden; Fristregel selbst blieb unverändert.

## Geschützte Grenzen

SHA-256-Abgleich gegen den vor TRADE-02 aufgenommenen Bestand: ausschließlich die unten aufgeführten erlaubten Trade-v2-/Testdateien geändert. Produktive `App/webapp.py`, `App/static/style.css`, Stickerwall, Stickerliste, sämtliche Pax-Quellen/Assets/Templates/Tests, Fixtures, alte Contracts und erfasste Datenbanken unverändert. Kein Eingriff auf Port 8080 oder 8094; ausschließlich der eigene Previewserver auf 8095 neu gestartet.

**Kein Commit. Kein Push. Kein Deploy. Kein git add. Keine produktive DB-Mutation.** Keine Migration, keine echten Requests, keine Änderung bestehender Userdaten oder produktiver Algorithmen/Mengenregeln.

## Vollständige Dateiliste

Geändert:

- `App/trade_v2/assets/preview.css`
- `App/trade_v2/assets/preview.js`
- `App/trade_v2/routes.py`
- `App/trade_v2/templates/preview.html`
- `tests/research/check_trade_01.py`
- `tests/test_trade_v2_preview.py`

Neu:

- `App/trade_v2/assets/requests.js`
- `App/trade_v2/assets/sender.js`
- `docs/TRADE_02_AUDIT.md`
- `tests/research/artifacts/trade-02/01-home-1280.png`
- `tests/research/artifacts/trade-02/01-home-390.png`
- `tests/research/artifacts/trade-02/02-fatima-deal-1280.png`
- `tests/research/artifacts/trade-02/02-fatima-deal-390.png`
- `tests/research/artifacts/trade-02/03-sent-1280.png`
- `tests/research/artifacts/trade-02/03-sent-390.png`
- `tests/research/artifacts/trade-02/04-two-before-1280.png`
- `tests/research/artifacts/trade-02/04-two-before-390.png`
- `tests/research/artifacts/trade-02/05-three-after-1280.png`
- `tests/research/artifacts/trade-02/05-three-after-390.png`
- `tests/research/artifacts/trade-02/06-fourth-blocked-1280.png`
- `tests/research/artifacts/trade-02/06-fourth-blocked-390.png`
- `tests/research/artifacts/trade-02/07-pool-1280.png`
- `tests/research/artifacts/trade-02/07-pool-390.png`
- `tests/research/artifacts/trade-02/08-karlheinz-1280.png`
- `tests/research/artifacts/trade-02/08-karlheinz-390.png`
- `tests/research/artifacts/trade-02/checks.json`
- `tests/research/artifacts/trade-02/index.html`
- `tests/research/artifacts/trade-02/regression/01-home-375.png`
- `tests/research/artifacts/trade-02/regression/01-home-390.png`
- `tests/research/artifacts/trade-02/regression/01-home-430.png`
- `tests/research/artifacts/trade-02/regression/02-top-five-390.png`
- `tests/research/artifacts/trade-02/regression/04-top-detail-390.png`
- `tests/research/artifacts/trade-02/regression/05-partner-preview-390.png`
- `tests/research/artifacts/trade-02/regression/06-partners-390.png`
- `tests/research/artifacts/trade-02/regression/07-filter-390.png`
- `tests/research/artifacts/trade-02/regression/08-karlheinz-390.png`
- `tests/research/artifacts/trade-02/regression/09-karlheinz-smartdeal-390.png`
- `tests/research/artifacts/trade-02/regression/10-manual-end-390.png`
- `tests/research/artifacts/trade-02/regression/11-receive-open-390.png`
- `tests/research/artifacts/trade-02/regression/12-give-continuation-390.png`
- `tests/research/artifacts/trade-02/regression/checks.json`
- `tests/research/artifacts/trade-02/regression/index.html`
- `tests/research/artifacts/trade-02/scope-check.json`
- `tests/research/artifacts/trade-02/stack-comparison.html`
- `tests/research/artifacts/trade-02/trade-stack-10.png`
- `tests/research/artifacts/trade-02/trade-stack-37.png`
- `tests/research/artifacts/trade-02/trade-stack-6.png`
- `tests/research/artifacts/trade-02/wall-stack-10.png`
- `tests/research/artifacts/trade-02/wall-stack-37.png`
- `tests/research/artifacts/trade-02/wall-stack-6.png`
- `tests/research/check_trade_02.py`
