# TRADE-01 — Isolierte Tauschhalle

## Start und Preview

Aus dem Repository `/Users/valy/Desktop/sammlr.`:

```sh
.venv/bin/python -B -m App.trade_v2
```

Eigener Server: **http://127.0.0.1:8095/trade-v2/**. Bindung nur an Loopback, kein Debug-/Reload-Modus. 8080 und 8094 werden weder eingebunden noch neu gestartet.

Direkte Einstiege:

- [Tauschen](http://127.0.0.1:8095/trade-v2/)
- [Top-Deal Fatima](http://127.0.0.1:8095/trade-v2/deals/fatima)
- [Justus mit 16/20/1-Fortsetzung](http://127.0.0.1:8095/trade-v2/deals/justus)
- [Alle Tauschpartner](http://127.0.0.1:8095/trade-v2/partners)
- [Karlheinz](http://127.0.0.1:8095/trade-v2/partners/karlheinz)
- [Karlheinz SmartDeal](http://127.0.0.1:8095/trade-v2/partners/karlheinz/smartdeal)
- [Manueller Preview-Endzustand](http://127.0.0.1:8095/trade-v2/partners/karlheinz/manual)

[Lokale Screenshot-Galerie](../tests/research/artifacts/trade-01/index.html): zwölf Ansichten bei 390 px plus Hauptseite bei 375 und 430 px.

## Quellen und Scope

Vor Änderungen gelesen: `TRADE_PRODUCT_CONTRACT_V2.md`, `TRADE_00_RESET_AUDIT.md`, historischer `SAMMLRPAX_CONTRACT_V1.md`, `PAX_05_AUDIT.md`, `PAX_06_AUDIT.md`, `PAX_CAP10_AUDIT.md`. Zusätzlich isolierte Pax-Factory/Routes/Fixtures, Shell und reine Darstellungsrenderer/CSS; produktive `sticker_wall_slot_html`, `sticker_wall_card_inner`, kanonische Stack-CSS, bestehende Trade-Wall/-Center-Ansichten und vorhandene Paritäts-/Isolationsprüfungen.

Keine Kollision mit dem neuen Produktvertrag. TRADE-01 bildet ausschließlich Discovery, Partnerpool und ungebundene Detailvorschläge ab. Offene Lifecycle-, Amendment-, Slot- und Contract-Type-Fragen aus TRADE-00 werden nicht implementiert oder neu entschieden.

## Umsetzung

Eigene Flask-Factory unter `App/trade_v2/`, ausschließlich GET-Routen, eigene Templates und Assets. Kein Import von `webapp`, produktiven Domainservices oder DB durch diese App. Der normale statische Assetpfad dient nur zur unveränderten lokalen Wiederverwendung vorhandener Darstellungsressourcen.

Startseite mit genau fünf einzeln bedienbaren, gleich dimensionierten Stickerstapeln in einer gemeinsamen kompakten 2+2+1-Auslage. Kleine Rotationen betreffen die äußere Auslage, niemals die interne Layer-Geometrie. Tap, Enter oder Space öffnet den gewählten Vorschlag im Kontext; ein deterministischer kleiner Receive-Ausschnitt erscheint zusammen mit „Tausch ansehen“. Erneute Aktivierung legt ihn zusammen. Keine Produktkarten, Verpackung, Öffnungsanimation oder entsprechende sichtbare Sprache.

Darunter drei nach Paarpotential ausgewählte Sammler und der Zugang zum vollständigen Pool. Zwölf strukturierte synthetische Partner, datengetriebene Sortierung nach maximalem bilateralen Potential absteigend; alternativ Doppelte oder relevante Sticker für mich. Funktionierender Albumfilter findet Partner, ohne deren Gesamtpotential oder fertigen Demo-Deal auf ein Album zu beschneiden. Gleichstände nach numerischer User-ID. Keine Bewertungsscores oder Sterne.

Karlheinz zeigt 84 für mich, 37 von mir, sechs Alben und 4.603 Doppelte. Seine beiden Aktionen führen zu einem konkreten 37↔37-SmartDeal beziehungsweise ausschließlich zum Endzustand „Manuelle Auswahl folgt in TRADE-02.“ Kein Builder.

Top-Vorschläge und Partner-SmartDeals nutzen dieselbe normalisierte Dealstruktur und dieselbe Detailvorlage. `TOP_SUGGESTION` und `SMARTDEAL` sind Herkunftsmetadaten; `MANUAL` kennzeichnet den ungebundenen Endzustand und erzeugt keinen fertigen Deal. Keines dieser Labels wird als persistierter Contract-Type ausgegeben.

Die Fixtures enthalten vorab festgelegte, deterministische Demonstrationspakete. Sie sind **keine neu implementierte Optimierung**, kein aktuelles Live-Ranking und kein ausführbarer Domainpayload. Counts stimmen mit den Einzelpositionen überein; Give und Receive sind gleich groß und liegen innerhalb des angegebenen Paarpotentials. Die fünf Top-Fixtures überlappen weder bei Receive-Needs noch bei Give-Positionen. Der Top-Plan wird nicht mit der Sortierung nach isoliertem Paarpotential gleichgesetzt.

Detail: einzeln auf-/zuklappbare Receive-Albumstapel, informative rote Give-Post-its, keine Packcheckliste. „Tausch anfragen“ zeigt lediglich „Anfrage folgt im gemeinsamen Trade-Lifecycle.“ Keine Anfrage-, Reservation-, Slot-, Bestands- oder Browser-Storage-Mutation.

## Komponenten und Stack-Parität

Direkte, unveränderte Wiederverwendung der reinen Exporte `card`, `renderReceive`, `renderGive` aus `App/static/pax/pax.js` und der vorhandenen `components.css`/`pax.css`. Keine neue Stack-CSS-Kopie, keine neue Layerlogik. Technische CSS-Klassen/Assetpfade behalten ihre bestehenden Namen; im sichtbaren Trade-V2-UI gibt es kein Pax-Wording. Es existiert kein `#pax-data`, daher startet der importierte Renderer keinen Pax-Lifecycle.

Produktive Stickerwall unverändert: Cap fünf. Trade/Receive: vorhandener Cap zehn, identische Faces, Front, Dimensionen, −2/−2-Versatz, Layer-Richtung und z-index `i+1`. Ab zehn sichtbaren Lagen wächst der Stack nicht weiter. Der umgebende Album-Schriftkontext ist wie in der Referenz 16 px; die Komponenten selbst bleiben unverändert.

Browser-Parität gegen den **tatsächlichen produktiven BRA-3-Renderer**, nicht bloß gegen kopiertes Markup: Mengen 1/2/5/6/10/15/37 bei 375/390/430 px. Verglichen werden berechnete Front-/Back-/Zifferneigenschaften einschließlich Maße, Padding, Radius, Farbe, Schatten, Transformation und z-index. Die Referenz wird ausschließlich im vorhandenen Testharness mit temporärer Test-DB importiert; die laufende Preview verwendet keine DB.

Post-its unverändert mit 16 Einträgen auf dem ersten und 20 pro Fortsetzungszettel; Grenzfall Justus 37 → 16/20/1 geprüft. Bestehende deterministische Rotationen, enge Fortsetzungen und größere Albumabstände wiederverwendet. Kein Kapazitätspolish oder neuer Textmarker.

## Tests und Responsive

Ausgeführt:

```sh
.venv/bin/python -B -m unittest tests.test_trade_v2_preview tests.test_pax_preview
.venv/bin/python -B -m unittest tests.test_sticker_wall_product_island tests.test_ceoklaue_sticker_list
.venv/bin/python -B tests/research/check_trade_01.py
git diff --check
```

- **8 Preview-Tests bestanden:** GET-only/POST 405, unbekannte IDs, fünf Top-Deals, zwölf Partner, konsistente Mengen/Alben/Identitäten, Herkunftstrennung und keine DB-Verbindung/Produktiv-App-Imports durch die isolierten Factorys.
- **29 bestehende Wall-/Listen-Tests bestanden**, bestehender Cap fünf und kanonische Listenregeln erhalten.
- **Browsergate bestanden bei 375/390/430 px:** alle fünf Top-Deals erreichbar, nicht überlappende Hitflächen, kompakte Auslage unter 660 px Höhe, kein horizontaler Seitenoverflow. Top öffnen/schließen, deterministischer Fächer, Top→Detail, mehrere Receive-Alben unabhängig öffnen/schließen, CTA-Endzustand, Pool-Sortierungen, Albumfilter, korrekte Partnerdaten, alle zwölf Partner-SmartDeals und Manual-Endzustand.
- Touch, Maus, Space und Enter geprüft; native Links/Buttons/Selects, Fokusmarkierung und Reduced Motion. Keine JS-/Assetfehler, keine externen Requests und keine schreibenden Browserrequests; kein Local-/Session-Storage.
- **21 Stack-Paritätsfälle bestanden**, einschließlich identischer Geometrie bei 10/15/37.
- 14 Screenshots erzeugt; Hauptseite, geöffneter Vorschlag, Partneransicht, Detail und Give-Fortsetzung visuell geprüft. Die Hauptseite verwendet eine gemeinsame Sticker-Auslage und darunter den größeren Pool, keine umetikettierten Verpackungskarten.
- `git diff --check` sowie zusätzliche Whitespace-Prüfung aller neuen Textdateien bestanden.

Während der Prüfung korrigiert: geerbte Schriftgröße des Albumcontainers, damit auch die Back-Layer-Eigenschaften exakt der Referenz entsprechen; nativen Touch-Tap-Highlight für saubere Darstellung deaktiviert. Der erste gemeinsame Unittest-Aufruf aller vier Module kollidierte mit dem bestehenden Pax-Test, der ein noch nicht importiertes `webapp` voraussetzt, während der Wall-Test dieses im Setup importiert. Die korrekte getrennte Ausführung beider Testgruppen besteht; keine alten Tests dafür verändert. Chromium und der lokale Server benötigten die Sandbox-Freigabe zum Start.

## Unverändert / Abschluss

SHA-256-Abgleich sämtlicher vorbestehender Dateien unter `App/`, `docs/`, `tests/` ohne Cache-Dateien: **keine geändert, keine gelöscht**. Einschließlich `App/pax/`, zugehöriger Assets/Templates/Tests, produktiver Kernquellen und aller dort erfassten Datenbanken. Die bei Beginn bereits vorhandenen Git-Änderungen bleiben unangetastet. Der neue Server ist nicht in der produktiven App registriert.

**Keine bestehende Datei geändert. Keine produktive DB oder produktiven Userdaten verändert. Keine Requests, Reservations-, Slot- oder Bestandsmutationen. Kein git add, Commit, Push oder Deploy.**

## Exakte neue Dateiliste

Anwendung:

- `App/trade_v2/__init__.py`
- `App/trade_v2/__main__.py`
- `App/trade_v2/fixtures.py`
- `App/trade_v2/routes.py`
- `App/trade_v2/templates/preview.html`
- `App/trade_v2/assets/preview.css`
- `App/trade_v2/assets/preview.js`

Tests und Dokumentation:

- `tests/test_trade_v2_preview.py`
- `tests/research/check_trade_01.py`
- `docs/TRADE_01_AUDIT.md`

Artefakte unter `tests/research/artifacts/trade-01/`:

- `01-home-375.png`
- `01-home-390.png`
- `01-home-430.png`
- `02-top-five-390.png`
- `03-top-open-390.png`
- `04-top-detail-390.png`
- `05-partner-preview-390.png`
- `06-partners-390.png`
- `07-filter-390.png`
- `08-karlheinz-390.png`
- `09-karlheinz-smartdeal-390.png`
- `10-manual-end-390.png`
- `11-receive-open-390.png`
- `12-give-continuation-390.png`
- `checks.json`
- `index.html`
- `scope-check.json`
