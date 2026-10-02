# TRADE-03 — Ein Request, zwei Perspektiven

## Ergebnis und Start

Valentin sendet den unveränderten Fatima-Deal. Fatima öffnet **denselben** Request mit exakt gespiegelten Receive-/Give-Seiten und kann annehmen oder ablehnen. Beide Rollen sehen anschließend den gemeinsamen Zustand. Annahme führt ausschließlich zum kontrollierten nächsten Preview-Endpunkt, nicht in eine implementierte Packphase.

Start im Repository `/Users/valy/Desktop/sammlr.`:

```sh
.venv/bin/python -B -m App.trade_v2
```

Preview: http://127.0.0.1:8095/trade-v2/

Bestehender Deal: http://127.0.0.1:8095/trade-v2/deals/fatima

Bestehende Anfrage, ohne Reset:

- Valentin: http://127.0.0.1:8095/trade-v2/requests/fatima?role=sender
- Fatima: http://127.0.0.1:8095/trade-v2/requests/fatima?role=recipient

Direkte QA-Zustände — setzen ausdrücklich **nur die lokale Demo** zurück:

| Zustand | Valentin | Fatima |
| --- | --- | --- |
| OPEN | [Sender wartet](http://127.0.0.1:8095/trade-v2/requests/fatima?scenario=open&role=sender) | [Empfänger entscheidet](http://127.0.0.1:8095/trade-v2/requests/fatima?scenario=open&role=recipient) |
| ACCEPTED | [Sender aktiv](http://127.0.0.1:8095/trade-v2/requests/fatima?scenario=accepted&role=sender) | [Empfänger aktiv](http://127.0.0.1:8095/trade-v2/requests/fatima?scenario=accepted&role=recipient) |
| DECLINED | [Sender abgelehnt](http://127.0.0.1:8095/trade-v2/requests/fatima?scenario=declined&role=sender) | [Empfänger abgelehnt](http://127.0.0.1:8095/trade-v2/requests/fatima?scenario=declined&role=recipient) |
| EXPIRED | [Sender abgelaufen](http://127.0.0.1:8095/trade-v2/requests/fatima?scenario=expired&role=sender) | [Empfänger abgelaufen](http://127.0.0.1:8095/trade-v2/requests/fatima?scenario=expired&role=recipient) |

Der `scenario`-Parameter wird nach einmaliger Initialisierung entfernt. `role` bleibt als reine Perspektive bestehen. Reload oder Rollenwechsel setzen keine Zeiten zurück. Die direkten QA-Szenarien nutzen zwei weitere fiktive ausgehende Verpflichtungen, damit Slotübergänge sichtbar sind. Der Fatima-Snapshot stammt dabei aus `TOP_SUGGESTION`.

[Galerie](../tests/research/artifacts/trade-03/index.html) · [Stackvergleich](../tests/research/artifacts/trade-03/stack-comparison.html) · [TRADE-01-Regression](../tests/research/artifacts/trade-03/regression-01/index.html) · [TRADE-02-Regression](../tests/research/artifacts/trade-03/regression-02/index.html).

## Grundlage und Ausgangszustand

Vor Umsetzung gelesen: `TRADE_PRODUCT_CONTRACT_V2.md`, `TRADE_00_RESET_AUDIT.md`, `TRADE_01_AUDIT.md`, `TRADE_02_AUDIT.md` und die vollständige aktuelle Trade-v2-Implementierung. Maßgeblich bleiben insbesondere die gemeinsame operative Kapazität in §9, der unveränderte absolute Zeitvertrag in §10 und die geschützten Komponenten in §11 des Produktvertrags.

TRADE-02 hatte Sender, Pending/Expired, Snapshot, SessionStorage und ausgehende Kapazität vorbereitet. Neu hinzugekommen sind die reine Empfängerentscheidung, abgeleiteter Rollenblick und die gemeinsame Statusansicht. Keine Domainkollision: Annahme hält den operativen Slot; Ablehnung und Ablauf geben ihn frei. Es wurden keine produktiven Lifecycle-Grenzen vorweggenommen.

## Ein Request und eine Snapshotquelle

Der vorhandene Speicher bleibt `sessionStorage['sammlr-trade-02']`; kein zweiter Empfänger-Store und keine zweite Fatima-Fixture. `state.requests[id]` enthält weiterhin genau einen Request mit Herkunft, absoluter Frist und einmal beim Senden erzeugtem Snapshot. Die vorhandenen TRADE-02-Datensätze können unverändert gelesen werden; keine stille Neuanlage bei Empfängeröffnung.

`perspective(request, role)` leitet beide Ansichten ausschließlich aus diesem gespeicherten Snapshot ab:

- Side A ist der bestehende Demo-Sender Valentin, Side B der Partner aus dem Snapshot.
- A Receive ist dieselbe Arrayreferenz wie B Give.
- A Give ist dieselbe Arrayreferenz wie B Receive.
- Request-ID, Albumkontext, Codes, Instanzen, Reihenfolge und Mengen bleiben erhalten.

Die Perspektive enthält keine separat gepflegte Stickerliste. Auch die nachträgliche vollständige Sender-Dealansicht verwendet den gesendeten Snapshot. Keine Matching-/Optimizer-Anbindung, keine Bestandsabfrage oder Neuberechnung beim Öffnen einer Anfrage. Fatimas unveränderte Fixture hat 23 Positionen je Richtung und sechs Alben; ihre Quelldatei blieb bytegleich.

`freezeSnapshot` friert den gespeicherten Inhalt beim Erstellen und Einlesen rekursiv ein. Annahme ändert weder den Snapshot noch dessen Identität, Bindungszeit oder Ablaufzeit. Der Inhalt ist bereits seit dem Senden verbindlich und bleibt nach Annahme unverändert.

## Zustände und Transitionen

Die technische bestehende Kennung `pending` entspricht hier dem fachlichen OPEN. `decide(state, id, role, action, now)` arbeitet auf demselben Requestobjekt:

| Ausgang | Aktion | Ergebnis |
| --- | --- | --- |
| Pending vor Frist, Empfänger | Accept | `accepted`, einmaliges `decidedAt` |
| Pending vor Frist, Empfänger | Decline | `declined`, einmaliges `decidedAt` |
| Pending ab Frist | Accept oder Decline | `expired`, keine Entscheidung mehr |
| Accepted / Declined / Expired | erneute oder entgegengesetzte Entscheidung | Bestehender terminaler Anfragezustand bleibt |
| Sender oder unzulässige Aktion | Accept/Decline | Verboten, keine Empfängerentscheidung |

Accepted ist die Projektion **eines** gemeinsamen aktiven Tauschs; keine zweite Trade-Sammlung und kein neu erzeugter Request. `decidedAt` ist nur die lokale Demo-Entscheidungszeit, keine produktive History- oder Versandbuchung. Die Transition prüft keine Herkunftsart: identisches Verhalten für TOP_SUGGESTION, SMARTDEAL und MANUAL im Modelltest. Ein manueller Builder wird dadurch nicht implementiert.

Vor jedem Klick wird der aktuelle gemeinsame Zustand erneut gelesen. Die Modelltransition erlaubt nur den ersten Ausgang aus Pending. Ein UI-Busy-Guard ergänzt dies; die Domänenprüfung bleibt auch bei programmgesteuerten Events auf ausgeblendeten Controls wirksam. Synchronous SessionStorage serialisiert diesen **einen Tab**. Dies ist weder produktive Nebenläufigkeitskontrolle noch eine zwischen Tabs synchronisierte Mehrbenutzeranwendung.

## Empfänger- und Senderansicht

Pending-Empfänger: „Valentin möchte mit dir tauschen“, 23↔23/sechs Alben, vollständiger gespiegelter Receive-Bereich und unveränderte informative Give-Post-its. Genau zwei Hauptentscheidungen: **Tausch annehmen** und **Ablehnen**. Keine Auswahl-, Gegenangebots- oder Änderungsfunktion; keine Checkliste vor Annahme.

Accepted-Empfänger: „Tausch steht ✓“. Accepted-Sender: „Fatima hat angenommen ✓“, kein veraltetes „Wartet auf Fatima“. Beide erhalten **Zum Packen →**; der vorhandene Request muss dafür Accepted sein. Der Endpunkt zeigt ausschließlich **„Packphase folgt im nächsten Trade-Schritt.“** und verändert keinen State. Bei einem direkten Einstieg ohne Annahme bleibt er gesperrt.

Declined und Expired werden ruhig und explizit für beide Rollen angezeigt. Kein aktiver Trade-CTA bei Ablehnung oder Ablauf. Die vollständige vereinbarte Dealansicht bleibt sekundär erreichbar.

**PREVIEW / DEV** enthält native Rollenlinks Valentin/Partner. Nur URL/Perspektive wechseln, nie Snapshot oder Zeit. Die bekannte Demo-Kapazitätsauswahl bleibt als ausdrücklich lokaler Reset erhalten. Ungültiger/nicht zugänglicher SessionStorage wird als Fehler angezeigt, nicht als erfolgreiche Entscheidung behandelt.

## Slots und Zeit

Senderprojektion unverändert: Pending und Accepted belegen den ausgehenden operativen Slot. Accepted bleibt auch nach der ursprünglichen Anfragefrist belegt; keine Pending-Expiry eines aktiven Tauschs. Erst ein späterer eigener bestätigter Versand würde freigeben — eine Versandaktion ist in TRADE-03 nicht vorhanden.

Empfängersicht projiziert eingehende Verpflichtungen desselben Partners aus denselben Requestobjekten. Es entsteht kein zweiter Datensatz oder separates Herkunftskontingent. Declined und Expired belegen auf keiner Seite mehr einen operativen Slot. In der Referenz mit zwei anderen Verpflichtungen gilt: 3/3 vor Entscheidung → 3/3 bei Annahme beziehungsweise 2/3 bei Ablehnung. Bei Live-Ablauf aller gleichzeitig begonnenen Seed-Anfragen werden selbstverständlich auch deren Slots frei.

Die Frist bleibt `bindingCreatedAt + 86.400.000 ms`. Akzeptieren/ablehnen ist nur bei `now < expiresAt` erlaubt. Exakt am Grenzzeitpunkt setzt die gemeinsame Prüfung Expired; beide Rollen lesen diesen Zustand. Rollenwechsel, Lesen des Deals und Reload verändern die absoluten Zeiten nicht. Keine Reminder-, Withdraw-, Verlängerungs- oder neue Fristregel implementiert.

## Komponenten und Bedienbarkeit

Kanonische Darstellungsrenderer unverändert direkt eingebunden: Wall5, Trade10, identische −2/−2-Geometrie, Faces, Maße, Front und z-index. Keine neue Stack-CSS, kein anderer Renderer für die gespiegelte Seite. Mengen über zehn wachsen geometrisch nicht weiter.

Unveränderte rote Post-its und 16/20-Fortsetzung. Keine Haken/Marker oder Packinteraktion. Bestehende Typografie und Shell fortgeführt; Rollensteuerung und Status-CTA verwenden vorhandene Controls.

Native Buttons/Links, sichtbarer Fokus, Tab/Shift+Tab/Enter/Space, Touch und Maus. Status besitzt `role=status`/`aria-live=polite`; nach Entscheidung wandert der Fokus zur Überschrift. Unveränderte Texte werden beim Timerupdate nicht erneut in die Live-Region geschrieben. Reduced Motion bleibt wirksam; keine Animation für das Verständnis erforderlich.

## Ausgeführte Prüfungen

```sh
.venv/bin/python -B -m unittest tests.test_trade_v2_preview tests.test_pax_preview
.venv/bin/python -B -m unittest tests.test_sticker_wall_product_island tests.test_ceoklaue_sticker_list
.venv/bin/python -B tests/research/check_trade_01.py
.venv/bin/python -B tests/research/check_trade_02.py
.venv/bin/python -B tests/research/check_trade_03.py
git diff --check
```

- **8 Preview-Tests bestanden:** GET-only inklusive Status-/Next-Endpunkt, POST abgewiesen, keine DB-/Produktiv-App-Anbindung, unveränderte Fixture-Konsistenz.
- **29 bestehende Wall-/Listen-Tests bestanden.** Deren vorhandener Testharness verwendet temporäre Test-DBs, keine produktive Datenbank.
- **TRADE-01-Browsergate bestanden:** fünf direkte Top-Einstiege, Partnerpool, datengetriebene Sortierung/Filter, Karlheinz-Daten, alle zwölf Partner-SmartDeals, Manual-Endzustand, unabhängige Receive-Fächer und 16/20/1.
- **21 kanonische Stackfälle bestanden:** 1/2/5/6/10/15/37 bei 375/390/430, tatsächlicher produktiver BRA-3-Renderer und vorhandene Trade-Darstellung. Identische Geometrie ab zehn; sechs direkte Vergleichsscreenshots.
- **TRADE-02-Browsergate bestanden:** Direktnavigation, Senden/Warten, gemeinsame Kapazität, vierte Anfrage blockiert, Doppelklick/Mehrfachaktivierung/Enter, Reload, absolute Frist und Live-Ablauf, 375/390/430/1280. Nur die Status-URL-Erwartung wurde um den neuen Perspektivparameter ergänzt.
- **TRADE-03-Browsergate bestanden bei 375/390/430/1280:** derselbe echte Sender-Request in beiden Rollen; exakter Vergleich sämtlicher Album-/Code-/Instanzschlüssel und Reihenfolge; 23↔23/sechs Alben; Empfänger- und Senderansichten nach Annahme/Ablehnung; kein zweiter Trade; unveränderte Snapshots und Zeiten; Slots gehalten/freigegeben; vollständiger Snapshot auch nach Annahme; gesperrte Gegenaktionen; Doppelklick, acht wiederholte Aktivierungen, Enter, Tab/Shift+Tab/Space und Touch-Rollenwechsel; Reload, Live-Expiry, Aktionen nach Ablauf und alle acht direkten QA-Zustände.
- **Reine Modellprüfungen im Browser:** alle drei Herkünfte, Referenzgleichheit beider gespiegelter Listen, tiefer Freeze, Sender darf nicht entscheiden, zwanzig wechselnde Gegenaktionen, gleiche Objektidentität, einmalige Entscheidungszeit, unveränderte Bindungszeit, Accepted/Declined werden nicht nachträglich expired, Deadline genau und 1 ms davor.
- Kein horizontaler Overflow auf allen vier Breiten. Keine JS-/Assetfehler, keine externen oder schreibenden Browserrequests. Kein sichtbares Pax-Wording, keine Adresse, Checkbox oder Packmarkierung.
- **36 neue TRADE-03-Screenshots** einschließlich aller geforderten 390-px-Szenen und zentraler Ansichten bei 375/430/1280; zusätzlich 13 TRADE-01- und 16 TRADE-02-Regressionsbilder sowie sechs Stackbilder. Historische Artefakte bleiben unverändert.
- Screenshots von eingehender Anfrage sowie beiden Accepted-Ansichten visuell geprüft. Geschlossene mobile Startseite zusätzlich pixelgleich mit TRADE-01.
- `git diff --check` und zusätzliche Whitespace-Prüfung der neuen/geänderten Textdateien bestanden.

## Negative Nachweise und Schutzgrenzen

SHA-256 vor/nach Umsetzung über den vorhandenen Bestand unter App/docs/tests ohne Cache-Dateien. Ausschließlich die nachfolgend aufgeführten erlaubten Trade-v2- und Testdateien geändert. Insbesondere unverändert: alle erfassten Datenbanken, `App/webapp.py`, produktive Trade-Routen, `App/static/style.css`, produktive Stickerwall und Stickerliste, Algorithmusquellen, vollständiger Pax-Pfad samt Assets/Templates/Tests, bestehende Contracts/Audits, historische Screenshots und `App/trade_v2/fixtures.py`.

Das neue Browsermodul projiziert ausschließlich den gespeicherten Snapshot; es ruft weder Optimizer noch Produktionsservices auf. Negative UI-/Modellprüfungen zeigen: kein zweiter Trade bei Annahme, kein neuer Deal bei Empfängeröffnung, keine Adresse/Checkliste und keine aktive Folgeaktion vor Accepted. Der Next-Endpunkt zeigt nur Text und verändert den Request nicht.

**Keine Produktiv-DB-Mutation. Keine produktiven Routenänderungen. App/pax unverändert. Keine Packphase, kein Versand, kein Amendment, kein Empfang und keine Bewertung implementiert. Kein git add, kein Commit, kein Push, kein Deploy.** Nur der isolierte Port 8095 wurde neu gestartet; 8080/8094 bleiben unberührt.

## Vollständige Dateiliste

Geändert:

- `App/trade_v2/assets/preview.css`
- `App/trade_v2/assets/preview.js`
- `App/trade_v2/assets/requests.js`
- `App/trade_v2/assets/sender.js`
- `App/trade_v2/routes.py`
- `App/trade_v2/templates/preview.html`
- `tests/research/check_trade_01.py`
- `tests/research/check_trade_02.py`
- `tests/test_trade_v2_preview.py`

Neu:

- `App/trade_v2/assets/request_view.js`
- `App/trade_v2/assets/session.js`
- `docs/TRADE_03_AUDIT.md`
- `tests/research/artifacts/trade-03/01-valentin-waiting-1280.png`
- `tests/research/artifacts/trade-03/01-valentin-waiting-375.png`
- `tests/research/artifacts/trade-03/01-valentin-waiting-390.png`
- `tests/research/artifacts/trade-03/01-valentin-waiting-430.png`
- `tests/research/artifacts/trade-03/02-fatima-incoming-1280.png`
- `tests/research/artifacts/trade-03/02-fatima-incoming-375.png`
- `tests/research/artifacts/trade-03/02-fatima-incoming-390.png`
- `tests/research/artifacts/trade-03/02-fatima-incoming-430.png`
- `tests/research/artifacts/trade-03/03-fatima-mirrored-1280.png`
- `tests/research/artifacts/trade-03/03-fatima-mirrored-375.png`
- `tests/research/artifacts/trade-03/03-fatima-mirrored-390.png`
- `tests/research/artifacts/trade-03/03-fatima-mirrored-430.png`
- `tests/research/artifacts/trade-03/04-fatima-before-accept-390.png`
- `tests/research/artifacts/trade-03/05-fatima-accepted-1280.png`
- `tests/research/artifacts/trade-03/05-fatima-accepted-375.png`
- `tests/research/artifacts/trade-03/05-fatima-accepted-390.png`
- `tests/research/artifacts/trade-03/05-fatima-accepted-430.png`
- `tests/research/artifacts/trade-03/06-valentin-accepted-1280.png`
- `tests/research/artifacts/trade-03/06-valentin-accepted-375.png`
- `tests/research/artifacts/trade-03/06-valentin-accepted-390.png`
- `tests/research/artifacts/trade-03/06-valentin-accepted-430.png`
- `tests/research/artifacts/trade-03/07-fatima-declined-1280.png`
- `tests/research/artifacts/trade-03/07-fatima-declined-375.png`
- `tests/research/artifacts/trade-03/07-fatima-declined-390.png`
- `tests/research/artifacts/trade-03/07-fatima-declined-430.png`
- `tests/research/artifacts/trade-03/08-valentin-declined-1280.png`
- `tests/research/artifacts/trade-03/08-valentin-declined-375.png`
- `tests/research/artifacts/trade-03/08-valentin-declined-390.png`
- `tests/research/artifacts/trade-03/08-valentin-declined-430.png`
- `tests/research/artifacts/trade-03/09-fatima-expired-1280.png`
- `tests/research/artifacts/trade-03/09-fatima-expired-375.png`
- `tests/research/artifacts/trade-03/09-fatima-expired-390.png`
- `tests/research/artifacts/trade-03/09-fatima-expired-430.png`
- `tests/research/artifacts/trade-03/10-dev-roles-390.png`
- `tests/research/artifacts/trade-03/11-slot-before-decline-390.png`
- `tests/research/artifacts/trade-03/12-slot-after-decline-390.png`
- `tests/research/artifacts/trade-03/checks.json`
- `tests/research/artifacts/trade-03/index.html`
- `tests/research/artifacts/trade-03/regression-01/01-home-375.png`
- `tests/research/artifacts/trade-03/regression-01/01-home-390.png`
- `tests/research/artifacts/trade-03/regression-01/01-home-430.png`
- `tests/research/artifacts/trade-03/regression-01/02-top-five-390.png`
- `tests/research/artifacts/trade-03/regression-01/04-top-detail-390.png`
- `tests/research/artifacts/trade-03/regression-01/05-partner-preview-390.png`
- `tests/research/artifacts/trade-03/regression-01/06-partners-390.png`
- `tests/research/artifacts/trade-03/regression-01/07-filter-390.png`
- `tests/research/artifacts/trade-03/regression-01/08-karlheinz-390.png`
- `tests/research/artifacts/trade-03/regression-01/09-karlheinz-smartdeal-390.png`
- `tests/research/artifacts/trade-03/regression-01/10-manual-end-390.png`
- `tests/research/artifacts/trade-03/regression-01/11-receive-open-390.png`
- `tests/research/artifacts/trade-03/regression-01/12-give-continuation-390.png`
- `tests/research/artifacts/trade-03/regression-01/checks.json`
- `tests/research/artifacts/trade-03/regression-01/index.html`
- `tests/research/artifacts/trade-03/regression-02/01-home-1280.png`
- `tests/research/artifacts/trade-03/regression-02/01-home-390.png`
- `tests/research/artifacts/trade-03/regression-02/02-fatima-deal-1280.png`
- `tests/research/artifacts/trade-03/regression-02/02-fatima-deal-390.png`
- `tests/research/artifacts/trade-03/regression-02/03-sent-1280.png`
- `tests/research/artifacts/trade-03/regression-02/03-sent-390.png`
- `tests/research/artifacts/trade-03/regression-02/04-two-before-1280.png`
- `tests/research/artifacts/trade-03/regression-02/04-two-before-390.png`
- `tests/research/artifacts/trade-03/regression-02/05-three-after-1280.png`
- `tests/research/artifacts/trade-03/regression-02/05-three-after-390.png`
- `tests/research/artifacts/trade-03/regression-02/06-fourth-blocked-1280.png`
- `tests/research/artifacts/trade-03/regression-02/06-fourth-blocked-390.png`
- `tests/research/artifacts/trade-03/regression-02/07-pool-1280.png`
- `tests/research/artifacts/trade-03/regression-02/07-pool-390.png`
- `tests/research/artifacts/trade-03/regression-02/08-karlheinz-1280.png`
- `tests/research/artifacts/trade-03/regression-02/08-karlheinz-390.png`
- `tests/research/artifacts/trade-03/regression-02/checks.json`
- `tests/research/artifacts/trade-03/regression-02/index.html`
- `tests/research/artifacts/trade-03/scope-check.json`
- `tests/research/artifacts/trade-03/stack-comparison.html`
- `tests/research/artifacts/trade-03/trade-stack-10.png`
- `tests/research/artifacts/trade-03/trade-stack-37.png`
- `tests/research/artifacts/trade-03/trade-stack-6.png`
- `tests/research/artifacts/trade-03/wall-stack-10.png`
- `tests/research/artifacts/trade-03/wall-stack-37.png`
- `tests/research/artifacts/trade-03/wall-stack-6.png`
- `tests/research/check_trade_03.py`
