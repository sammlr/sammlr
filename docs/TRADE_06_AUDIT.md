# TRADE-06 — Packfreigabe, Adresse und eigener Versand

Stand: 2026-09-30. Isolierte Trade-v2-Preview, ausschließlich lokaler Demo-State. Keine produktive Versand- oder Datenbankintegration.

## Ergebnis und Start

Eigene Packprüfung abschließen → Partneradresse auf gelbem Action-Post-it → Versand vorbereiten → optionales lokales Portal → ausdrückliche eigene Versandbestätigung. Nur dadurch wird der eigene operative Slot frei. Die andere Richtung bleibt unabhängig. Beide versendet ergibt BOTH_SHIPPED, niemals COMPLETED.

Start im Projektverzeichnis:

```sh
.venv/bin/python -B -m App.trade_v2
```

Preview: http://127.0.0.1:8095/trade-v2/

| Direkter QA-Einstieg | URL |
| --- | --- |
| A · Valentin Packfreigabe / Adresse | http://127.0.0.1:8095/trade-v2/requests/fatima/shipping?ship=address&role=sender |
| B · Valentin READY_TO_SHIP | http://127.0.0.1:8095/trade-v2/requests/fatima/shipping?ship=ready&role=sender |
| C · Valentin SHIPPED / Fatima PACKING | http://127.0.0.1:8095/trade-v2/requests/fatima/shipping?ship=me-packing&role=sender |
| D · Valentin SHIPPED / Fatima PACKING_COMPLETE | http://127.0.0.1:8095/trade-v2/requests/fatima/shipping?ship=me-complete&role=recipient |
| E · Valentin SHIPPED / Fatima READY_TO_SHIP | http://127.0.0.1:8095/trade-v2/requests/fatima/shipping?ship=me-ready&role=recipient |
| F · BOTH_SHIPPED | http://127.0.0.1:8095/trade-v2/requests/fatima/shipping?ship=both&role=sender |
| G · Fatima SHIPPED / Valentin PACKING | http://127.0.0.1:8095/trade-v2/requests/fatima/shipping?ship=partner-first&role=sender |
| H · V2 21↔21 Adresse | http://127.0.0.1:8095/trade-v2/requests/fatima/shipping?ship=v2-address&role=sender |
| I · V2 READY_TO_SHIP | http://127.0.0.1:8095/trade-v2/requests/fatima/shipping?ship=v2-ready&role=sender |
| J · V2 SHIPPED | http://127.0.0.1:8095/trade-v2/requests/fatima/shipping?ship=v2-shipped&role=sender |
| K · Adresse vor Packfreigabe gesperrt | http://127.0.0.1:8095/trade-v2/requests/fatima/shipping?ship=locked&role=sender |
| L · Amendment nach SHIPPED gesperrt | http://127.0.0.1:8095/trade-v2/requests/fatima/shipping?ship=amendment-blocked&role=recipient |

Zusätzliche Seeds: `long` (lange Demoadresse), `consent-blocked` (fehlende Eigentümerfreigabe), `full-unreleased` (alle 23 markiert, noch keine Packfreigabe). [Alle Links für beide Rollen](../tests/research/artifacts/trade-06/demos.html).

Ein expliziter `ship=`-QA-Link setzt nur den lokalen Tab-Demostand neu und entfernt seinen Seed-Parameter. Danach verändern Reload, normale URL und Rollenwechsel weder Packfreigabe noch Versand. Der Seed `amendment-blocked` führt direkt zur bestehenden gesperrten Änderungsansicht. Keine zweite Trade-Instanz.

## Grundlagen / Referenzprüfung

Maßgebliche gelesene Grundlagen: `TRADE_PRODUCT_CONTRACT_V2.md` sowie `TRADE_00_RESET_AUDIT.md` bis `TRADE_05_AUDIT.md`. Insbesondere Trade-V2 §§8–10: eigene bewusste Packfreigabe, zusätzliche Freigabe durch den Adressinhaber, unabhängige physische Richtungen, gemeinsames operatives 3/3, Versand ist nicht Empfang und nicht Abschluss. Alle bisherigen Legacy-/SmartDeal-V1-Grenzen bleiben erhalten.

Gezielte Referenzprüfung:

- `docs/PAX_06_AUDIT.md`
- `App/static/pax/shipping.js`, `shipping.css`, `journey.js`, `lifecycle.js`
- `App/templates/pax/detail.html`
- `App/services/trade_shipping.py`: `TradeShippingService.ship`, getrennte Richtungsflags/-zeiten, Autorisierung, idempotenter Versand und echte Reservations-/Bestandsbuchung.
- `App/webapp.py`: Versandstatus und `/trade/<id>/ship` ausschließlich lesend.

Die bestehende aktive Portalreferenz ist die **lokale PAX-06-Vorschau** mit Option „Brief“, neutralem Portalschritt und eigener ausdrücklicher Bestätigung. Keine belegte aktive DHL-API, kein Produkt-/Tarifkatalog oder Labelkauf in diesen Quellen. Kodierte Backup-Blobs sind keine aktive Integration. TRADE-06 übernimmt diese Mechanik; kein erfundener Carrier-Adapter, Preis, Paketprodukt oder Trackingcode.

## Wiederverwendung / Darstellung

Der gelbe Zettel verwendet unverändert das vorhandene `/static/pax/shipping.css`: `#f5dd62`, identische Papier-/Schattenbehandlung und deterministische Rotation −0,7°. Adresse in maschineller Schrift, normale Systemtexte; keine komplett handschriftliche Adresse. Der reine Stylesheet wird lesend eingebunden, ohne Pax-Journey oder produktive Mutation auszulösen. Lokales `shipping.css` ergänzt nur die Einbettung und Controls.

Bestehender Portalablauf: Adresse → Versand vorbereiten → Versandart Brief wählen → optional „Versandportal ansehen“ → lokale Erläuterung → zurück → „Versand bestätigen“. Die Portalansicht zeigt das Versandziel, öffnet keinen Anbieter und sendet keine Adresse. Eigene Briefmarke, Filiale oder bereits frankierte Sendung sind ausdrücklich möglich. Besuch des Portals ist keine Modellvoraussetzung; nur die vorhandene Versandartwahl und ausdrückliche Bestätigung werden übernommen.

Keine neue Animation; auch die gelbe Referenz hat keine Einfluganimation. Reduced Motion wird vom bestehenden Trade-Stylesheet respektiert. Blutroter Marker und Pack-CSS unverändert. Rote Post-its bleiben 16/20, unveränderte kanonische Renderer und Stickerfaces.

## Adressgate und Datensparsamkeit

Eine Adresse wird ausschließlich aus der **Gegenrolle** abgeleitet. Fiktive Beispiele: „Valentin Beispiel (Demo)“, „Fatima Beispiel (Demo)“, erfundene Straßen und fünfstellige `00000` mit ausdrücklich fiktiven Orten. Lange Variante mit Doppelname und langer Straße. Keine echte Privatadresse aus Projekt, DB oder Nutzerprofil.

Gate:

1. akzeptierter aktiver Trade;
2. eigene vollständige Packliste aus der aktiven Version;
3. eigene abgeschlossene Packprüfung und bewusste Freigabe genau dieser Version;
4. kein ungeklärtes Pending-Amendment bzw. bestätigter offener Fehlbericht;
5. separate simulierte Eigentümerfreigabe der fiktiven Zieladresse.

Die Zustimmung des Adressinhabers wird **nicht** aus dem Packzustand abgeleitet. Wie in PAX-06 besitzen die eindeutig fiktiven Adressfixtures explizites `addressReleased: true`; ein negativer QA-Fall blockiert diese Freigabe zusätzlich. Kein produktiver Consent-Workflow wird durch die Demo ersetzt oder superseded.

Vor dem Gate entstehen keine Adressknoten, versteckten Adressfragmente, Attribute, serialisierten Demoadressen im Seiten-HTML oder Adresswerte im DEV-Text. Die Daten leben nur im internen Demo-Modul. `targetAddress` gibt bei gesperrtem Gate null zurück; die Oberfläche erstellt `<address>` erst im autorisierten Renderzweig. Getestet durch Prüfung des gesamten HTML, nicht nur der sichtbaren Textansicht.

23 markierte Positionen ohne eigenen Abschluss reichen nicht. Ebenso reicht die durch TRADE-05 automatisch vollständige V2-Packintersektion allein nicht: bewusste Freigabe für V2 erforderlich. Die eigene Freigabe hängt nicht von der Packvollständigkeit des Partners ab.

„Packliste nochmals prüfen“ ist vor Versand möglich: Freigabe/Versandart dieser Richtung werden gelöscht, Markierungen bleiben erhalten. Adresse verschwindet aus dem DOM, erneute Freigabe erforderlich. Nach eigenem Versand ist dieser Weg gesperrt.

Nach Versand zeigt die Hauptansicht keine Adresse. Erst Öffnen des sekundären Versanddetails erzeugt die zulässige fiktive Zieladresse erneut; Schließen entfernt sie wieder. Keine neue Aufbewahrungs-/Löschpolicy für produktive Daten.

## Richtungsbezogenes Modell und Versionen

Ein Request bleibt `status: accepted`, derselbe aktive `snapshot`, dieselbe Dealversion. `shipping.sender` und `shipping.recipient` speichern unabhängig:

- `releasedVersion`: bewusst freigegebene aktive Version oder null;
- `method`: null / bestehende Demo-Option `brief`;
- `shippedAt`: einmaliger eigener Demo-Zeitpunkt oder null.

Die bereits vorhandenen richtungsbezogenen Flags `ownShipped` und `recipientShipped` werden ausschließlich durch `confirmShipment` für die eigene Rolle gesetzt. Kein globales `trade.shipped` als Wahrheit. `shippingState` projiziert je Rolle PACKING / PACKING_COMPLETE / READY_TO_SHIP / SHIPPED. BOTH_SHIPPED ist ausschließlich die Konjunktion beider Flags, keine weitere Mutation.

`releasePacking`, `chooseMethod`, `confirmShipment` und `reopenPacking` prüfen eigenen Zustand, Rolle, vollständige aktuelle Positionen, Versions-/Pack-/Versandvalidität sowie das Adressgate. Request-Persistenz validiert Versandzustände und aktive Release-Version. Die älteren expliziten TRADE-05-QA-Versandindikatoren bleiben lesbar; sie erzeugen weder neue Versandevents noch Adressfreigaben.

V1 funktioniert mit 23 Positionen. V2 arbeitet nur mit den verbleibenden 21; weder UI noch Commands verlangen wieder 23. Bei angenommenem Amendment werden eventuell bestehende Freigaben und Methodenauswahl beider Richtungen zurückgesetzt; die neue Version braucht bewusste Freigabe. Eine gespeicherte V1-Freigabe auf aktivem V2 wird abgewiesen. Snapshot und Versionshistorie werden durch Versand nicht verändert.

Vor jeder UI-Mutation wird der gemeinsame Sessionstand neu gelesen; anschließend erfolgt ein synchroner gesamter SessionStorage-Schreibvorgang. Idempotenz bewahrt beim erneuten Bestätigen Zustand und ursprünglichen Versandzeitpunkt. Keine produktive Mehrbenutzer-/DB-Atomarität beansprucht, keine SessionStorage-Übernahme als Produktionsdomain.

## Operative Slots / BOTH_SHIPPED

Es werden keine Zähler heruntergezählt. Die bestehenden Slotprojektionen lesen den jeweiligen Versandindikator und Request-State:

- Annahme, Packen, Packabschluss, Freigabe, Adresse, Versandart und Portal: Slot bleibt belegt.
- Valentin bestätigt eigenen Versand: ausgehend 3/3→2/3; Fatimas eingehender Slot bleibt 1/3.
- Fatima bestätigt eigenen Versand: eingehend 1/3→0/3; Valentins noch offene Verpflichtung wäre unabhängig weiterhin belegt.
- Beide versendet: beide individuellen Freigaben sind bereits erfolgt. Keine zweite Freigabe und keine negative Slotzahl.

Die Kontingentrichtung folgt weiterhin der ursprünglichen Request-Rolle: Initiator ausgehend, Empfänger eingehend. Die Formulierung „eigener ausgehender Slot“ aus dem Versandablauf wird nicht zur Umdeutung der globalen 3/3-Semantik benutzt.

Sichtbare Zustände: eigene Sticker unterwegs / Partner packt noch; Partner zuerst unterwegs / eigene Packaufgabe offen; beide Sendungen unterwegs. Der Trade bleibt accepted/aktiv, nicht COMPLETED. Keine Empfangs-, Problem-, Bewertungs- oder Abschlussaktion.

## Freeze und Amendment-Sperre

Nach eigenem Versand sind sämtliche eigenen Packaktionen einschließlich Toggle, Abschluss, Fehlmengenreview/-meldung und Wiederöffnen gesperrt, auch bei synthetischem Event auf alten Controls. Der unversandte Partner bleibt normal bedienbar.

Die TRADE-05-Schutzregel prüft dieselben beiden Versandflags. Sobald eine Richtung versendet ist, gibt es kein normales Amendment mehr. Der noch packende Partner kann eine tatsächlich festgestellte Fehlmenge dokumentieren, erhält anschließend aber nur den bereits vorgesehenen Hinweis auf spätere Klärung; keine Dealverkleinerung. Keine neue Problem-nach-Versand-Logik.

## Tests / Browser / Sichtprüfung

Ausgeführt:

```sh
.venv/bin/python -B -m unittest tests.test_trade_v2_preview tests.test_pax_preview -q
.venv/bin/python -B -m unittest tests.test_sticker_wall_product_island tests.test_ceoklaue_sticker_list -q
.venv/bin/python -B tests/research/check_trade_06_regressions.py
.venv/bin/python -B tests/research/check_trade_06.py
git diff --check
```

- **8 Preview-/Isolations-Unittests bestanden**, neuer GET-Versandendpunkt eingeschlossen, POST 405, kein Import produktiver Services und kein DB-Zugriff der Preview.
- **29 bestehende Wall-/Listen-Unittests bestanden**; kanonischer Referenzharness ausschließlich mit temporären Test-DBs.
- **TRADE-01–05-Browsergates bestanden**, darunter Discovery, Anfragen/Fristen/Slots, genaue Spiegelung, Packen und 205 Amendment-Modellassertionen. Nur die obsolete pauschale TRADE-04-Assertion „nirgendwo ein address-Knoten“ wurde für die jetzt ausdrücklich freigegebene abgeschlossene eigene Packprüfung angepasst: Adresse verlangt passende `packing_complete`-Phase und freigegebene aktive Version. Keine andere bisherige Prüfung entfernt. Historische Artefakte bleiben unverändert.
- **259 neue Modellassertionen bestanden**: beide Richtungen × drei Herkünfte, 22/23 und 23 ohne Abschluss gesperrt, bewusste Versionsfreigabe, separate Eigentümerfreigabe, genaue Gegenadresse, keine Partner-Abhängigkeit, Slots über alle Vorstufen, erlaubte Briefwahl, keine fremden Produkte, Idempotenz/Zeitstabilität, eigene eingefrorene Packliste, unabhängiger Partner, BOTH_SHIPPED ohne Abschluss, kein zweiter Trade, V1/V2-Historie unverändert, erneute Versionsfreigabe nach Amendment, ungültige Persistenz, Amendment nach echtem Versand beider Richtungen blockiert.
- **Browser bei 375/390/430/1280 px bestanden**: echter Packabschluss bis Versand beider Rollen, Slotwerte, keine Adressen im unfreigegebenen DOM, keine eigene Adresse als Versandziel, optionales Portal, lange Adresszeilen, mehrfaches Event und physischer Doppelklick, Reload, Rollenwechsel ohne Versandmutation, sekundäre Details, V2, echte Amendment-Sperre nach Versand und alle 15 QA-Seeds einschließlich bewusstem fehlendem Consent.
- Touch, Maus, Tab-/Enter-/Space-Verhalten und sichtbarer Fokus; Ergebnisüberschrift erhält Fokus nach Versand. Adresse semantisch `<address>`, Status textlich eindeutig. Reduced Motion, keine funktionale Animationsabhängigkeit.
- **Stack-Parität:** 21 Fälle mit Mengen 1/2/5/6/10/15/37 bei 375/390/430 gegen den tatsächlichen produktiven BRA-3-Renderer. Wall5 / Trade10, identische −2/−2, Faces, Maße und z-index; kein Wachstum über 10.
- Keine horizontalen Seitenüberläufe, JS-/HTTP-Fehler, externen Requests, Schreibrequests, neue Fenster, Carrier-, Zahlungs- oder Labelaktionen im Browsergate.
- **38 neue TRADE-06-Screenshots** einschließlich aller geforderten 390-px-Zustände sowie zentraler Ansichten bei 375/430/1280. Lange Demoadresse, Versandvorbereitung und BOTH_SHIPPED bei 390 px visuell geprüft: lesbare Systemschrift, korrekter gelber Zettel, erreichbare native Controls und ruhiger Endzustand.

[Galerie](../tests/research/artifacts/trade-06/index.html) · [Demo-Einstiege](../tests/research/artifacts/trade-06/demos.html) · [Prüfergebnis](../tests/research/artifacts/trade-06/checks.json)

Regressionsnachweise: [TRADE-01](../tests/research/artifacts/trade-06/regression-01/checks.json), [TRADE-02](../tests/research/artifacts/trade-06/regression-02/checks.json), [TRADE-03](../tests/research/artifacts/trade-06/regression-03/checks.json), [TRADE-04](../tests/research/artifacts/trade-06/regression-04/checks.json), [TRADE-05](../tests/research/artifacts/trade-06/regression-05/checks.json).

[Scope-/Hashnachweis](../tests/research/artifacts/trade-06/scope-checks.json) · [Vollständiges Dateimanifest](../tests/research/artifacts/trade-06/files.json)

## Exakte Quelländerungen

Geändert:

- `App/trade_v2/routes.py` — isolierte GET-Versandroute.
- `App/trade_v2/templates/preview.html` — Versandhost, lesende gelbe Referenz-CSS, lokales CSS und DEV.
- `App/trade_v2/assets/preview.js` — Versandcontroller starten.
- `App/trade_v2/assets/requests.js` — lokale Versandpersistenz validieren.
- `App/trade_v2/assets/packing.js` — Guards gegen eigene Packaktionen nach Versand.
- `App/trade_v2/assets/packing_view.js` — bewusste Freigabe, integrierter gelber Zettel/Versandflow, Partnerstatus, DEV.
- `App/trade_v2/assets/request_view.js` — unabhängige Versandstatus und Links, BOTH_SHIPPED bleibt aktiv.
- `App/trade_v2/assets/amendments.js` — Versionswechsel setzt vorherige Packfreigabe/Versandauswahl zurück.
- `tests/test_trade_v2_preview.py` — neue Route in GET-only-/No-DB-Prüfung.
- `tests/research/check_trade_04.py` — autorisierte Adressausgabe am ersetzten Shipping-Endpunkt prüfen.

Neu:

- `App/trade_v2/assets/shipping_state.js` — gemeinsame richtungsbezogene Projektion und Persistenzvalidierung.
- `App/trade_v2/assets/shipping.js` — lokale Packfreigabe-/Adress-/Versandcommands, eindeutig fiktive Adressfixtures.
- `App/trade_v2/assets/shipping_panel.js` — wiederverwendete Versandmechanik in isoliertem UI.
- `App/trade_v2/assets/shipping_view.js` — isolierter Route-/Sessioncontroller.
- `App/trade_v2/assets/shipping_demo.js` — explizite QA-Seeds.
- `App/trade_v2/assets/shipping.css` — lokale Einbettung ohne Änderung gelber kanonischer Geometrie.
- `tests/research/check_trade_06.py` — Browsergate/Galerie.
- `tests/research/trade_06_model.js` — Modellassertionen gegen tatsächliche App-Module.
- `tests/research/check_trade_06_regressions.py` — bestehende Browsergates in neue Artefaktordner ausführen.
- `docs/TRADE_06_AUDIT.md` — dieser Audit.
- Neue Research-Artefakte ausschließlich unter `tests/research/artifacts/trade-06/`, jede Datei im Manifest und nachfolgend aufgeführt.

## Geschützte Grenzen / negative Assertions

SHA-256-Abgleich gegen `/tmp/trade06-before.json`, vor der ersten Änderung aufgenommen. Vorbestehende lokale Änderungen bleiben Ausgangszustand. Dauerhafter Scope-Bericht mit Vorher-/Nachher-Hashes der geschützten Dateien, unverändertem Marker/Pack-CSS/Fixtures und kompletter erlaubter Änderungsliste. `git diff --check` plus gesonderte Whitespace-Prüfung neuer/ungetrackter Textdateien.

- Keine Produktiv-DB verändert; keine produktive DB-Mutation.
- Keine produktiven Trade- oder Versandrouten verändert.
- `App/pax/`, Pax-JS/CSS/Templates und produktive Webapp unverändert.
- Stickerwall, Stickerliste, Post-it-Logik und SmartDeal-Algorithmus unverändert.
- Kein echter DHL-/Carrier-Auftrag, keine echte Zahlung, keine Versandmarke gekauft.
- Keine echten Privatadressen verwendet und keine Adresse extern übertragen.
- Kein Empfang implementiert.
- Kein Problem-nach-Versand-Flow implementiert.
- Keine Bewertung oder Abschlussbewertung implementiert.
- Kein Trade bei BOTH_SHIPPED als abgeschlossen markiert.
- Keine neue globale Carrier-/Versandmaschine, keine produktiven Reservations-/Inventarbuchungen.
- Keine Legacy-Migration, kein Algorithmus-Neulauf, keine Marker-/Stack-Politur.
- Kein git add, kein Commit, kein Push, kein Deploy. Nur isolierter Server 8095 neu gestartet; 8080/8094 unberührt.

## Vollständige Liste neuer Research-Artefakte

- `tests/research/artifacts/trade-06/01-all-marked-before-release-390.png`
- `tests/research/artifacts/trade-06/02-yellow-address-1280.png`
- `tests/research/artifacts/trade-06/02-yellow-address-375.png`
- `tests/research/artifacts/trade-06/02-yellow-address-390.png`
- `tests/research/artifacts/trade-06/02-yellow-address-430.png`
- `tests/research/artifacts/trade-06/02b-address-note-390.png`
- `tests/research/artifacts/trade-06/03-long-demo-address-1280.png`
- `tests/research/artifacts/trade-06/03-long-demo-address-375.png`
- `tests/research/artifacts/trade-06/03-long-demo-address-390.png`
- `tests/research/artifacts/trade-06/03-long-demo-address-430.png`
- `tests/research/artifacts/trade-06/04-prepare-shipping-390.png`
- `tests/research/artifacts/trade-06/05-local-portal-1280.png`
- `tests/research/artifacts/trade-06/05-local-portal-375.png`
- `tests/research/artifacts/trade-06/05-local-portal-390.png`
- `tests/research/artifacts/trade-06/05-local-portal-430.png`
- `tests/research/artifacts/trade-06/06-ready-to-ship-390.png`
- `tests/research/artifacts/trade-06/07-before-confirmation-390.png`
- `tests/research/artifacts/trade-06/08-valentin-shipped-fatima-packing-1280.png`
- `tests/research/artifacts/trade-06/08-valentin-shipped-fatima-packing-375.png`
- `tests/research/artifacts/trade-06/08-valentin-shipped-fatima-packing-390.png`
- `tests/research/artifacts/trade-06/08-valentin-shipped-fatima-packing-430.png`
- `tests/research/artifacts/trade-06/09-fatima-sees-valentin-shipped-390.png`
- `tests/research/artifacts/trade-06/10-fatima-shipped-valentin-packing-390.png`
- `tests/research/artifacts/trade-06/11-both-shipped-1280.png`
- `tests/research/artifacts/trade-06/11-both-shipped-375.png`
- `tests/research/artifacts/trade-06/11-both-shipped-390.png`
- `tests/research/artifacts/trade-06/11-both-shipped-430.png`
- `tests/research/artifacts/trade-06/12-v2-address-1280.png`
- `tests/research/artifacts/trade-06/12-v2-address-375.png`
- `tests/research/artifacts/trade-06/12-v2-address-390.png`
- `tests/research/artifacts/trade-06/12-v2-address-430.png`
- `tests/research/artifacts/trade-06/13-v2-shipped-1280.png`
- `tests/research/artifacts/trade-06/13-v2-shipped-375.png`
- `tests/research/artifacts/trade-06/13-v2-shipped-390.png`
- `tests/research/artifacts/trade-06/13-v2-shipped-430.png`
- `tests/research/artifacts/trade-06/14-address-blocked-390.png`
- `tests/research/artifacts/trade-06/15-amendment-blocked-after-shipment-390.png`
- `tests/research/artifacts/trade-06/16-dev-independent-shipping-390.png`
- `tests/research/artifacts/trade-06/checks.json`
- `tests/research/artifacts/trade-06/demos.html`
- `tests/research/artifacts/trade-06/files.json`
- `tests/research/artifacts/trade-06/index.html`
- `tests/research/artifacts/trade-06/regression-01/01-home-375.png`
- `tests/research/artifacts/trade-06/regression-01/01-home-390.png`
- `tests/research/artifacts/trade-06/regression-01/01-home-430.png`
- `tests/research/artifacts/trade-06/regression-01/02-top-five-390.png`
- `tests/research/artifacts/trade-06/regression-01/04-top-detail-390.png`
- `tests/research/artifacts/trade-06/regression-01/05-partner-preview-390.png`
- `tests/research/artifacts/trade-06/regression-01/06-partners-390.png`
- `tests/research/artifacts/trade-06/regression-01/07-filter-390.png`
- `tests/research/artifacts/trade-06/regression-01/08-karlheinz-390.png`
- `tests/research/artifacts/trade-06/regression-01/09-karlheinz-smartdeal-390.png`
- `tests/research/artifacts/trade-06/regression-01/10-manual-end-390.png`
- `tests/research/artifacts/trade-06/regression-01/11-receive-open-390.png`
- `tests/research/artifacts/trade-06/regression-01/12-give-continuation-390.png`
- `tests/research/artifacts/trade-06/regression-01/checks.json`
- `tests/research/artifacts/trade-06/regression-01/index.html`
- `tests/research/artifacts/trade-06/regression-02/01-home-1280.png`
- `tests/research/artifacts/trade-06/regression-02/01-home-390.png`
- `tests/research/artifacts/trade-06/regression-02/02-fatima-deal-1280.png`
- `tests/research/artifacts/trade-06/regression-02/02-fatima-deal-390.png`
- `tests/research/artifacts/trade-06/regression-02/03-sent-1280.png`
- `tests/research/artifacts/trade-06/regression-02/03-sent-390.png`
- `tests/research/artifacts/trade-06/regression-02/04-two-before-1280.png`
- `tests/research/artifacts/trade-06/regression-02/04-two-before-390.png`
- `tests/research/artifacts/trade-06/regression-02/05-three-after-1280.png`
- `tests/research/artifacts/trade-06/regression-02/05-three-after-390.png`
- `tests/research/artifacts/trade-06/regression-02/06-fourth-blocked-1280.png`
- `tests/research/artifacts/trade-06/regression-02/06-fourth-blocked-390.png`
- `tests/research/artifacts/trade-06/regression-02/07-pool-1280.png`
- `tests/research/artifacts/trade-06/regression-02/07-pool-390.png`
- `tests/research/artifacts/trade-06/regression-02/08-karlheinz-1280.png`
- `tests/research/artifacts/trade-06/regression-02/08-karlheinz-390.png`
- `tests/research/artifacts/trade-06/regression-02/checks.json`
- `tests/research/artifacts/trade-06/regression-02/index.html`
- `tests/research/artifacts/trade-06/regression-03/01-valentin-waiting-1280.png`
- `tests/research/artifacts/trade-06/regression-03/01-valentin-waiting-375.png`
- `tests/research/artifacts/trade-06/regression-03/01-valentin-waiting-390.png`
- `tests/research/artifacts/trade-06/regression-03/01-valentin-waiting-430.png`
- `tests/research/artifacts/trade-06/regression-03/02-fatima-incoming-1280.png`
- `tests/research/artifacts/trade-06/regression-03/02-fatima-incoming-375.png`
- `tests/research/artifacts/trade-06/regression-03/02-fatima-incoming-390.png`
- `tests/research/artifacts/trade-06/regression-03/02-fatima-incoming-430.png`
- `tests/research/artifacts/trade-06/regression-03/03-fatima-mirrored-1280.png`
- `tests/research/artifacts/trade-06/regression-03/03-fatima-mirrored-375.png`
- `tests/research/artifacts/trade-06/regression-03/03-fatima-mirrored-390.png`
- `tests/research/artifacts/trade-06/regression-03/03-fatima-mirrored-430.png`
- `tests/research/artifacts/trade-06/regression-03/04-fatima-before-accept-390.png`
- `tests/research/artifacts/trade-06/regression-03/05-fatima-accepted-1280.png`
- `tests/research/artifacts/trade-06/regression-03/05-fatima-accepted-375.png`
- `tests/research/artifacts/trade-06/regression-03/05-fatima-accepted-390.png`
- `tests/research/artifacts/trade-06/regression-03/05-fatima-accepted-430.png`
- `tests/research/artifacts/trade-06/regression-03/06-valentin-accepted-1280.png`
- `tests/research/artifacts/trade-06/regression-03/06-valentin-accepted-375.png`
- `tests/research/artifacts/trade-06/regression-03/06-valentin-accepted-390.png`
- `tests/research/artifacts/trade-06/regression-03/06-valentin-accepted-430.png`
- `tests/research/artifacts/trade-06/regression-03/07-fatima-declined-1280.png`
- `tests/research/artifacts/trade-06/regression-03/07-fatima-declined-375.png`
- `tests/research/artifacts/trade-06/regression-03/07-fatima-declined-390.png`
- `tests/research/artifacts/trade-06/regression-03/07-fatima-declined-430.png`
- `tests/research/artifacts/trade-06/regression-03/08-valentin-declined-1280.png`
- `tests/research/artifacts/trade-06/regression-03/08-valentin-declined-375.png`
- `tests/research/artifacts/trade-06/regression-03/08-valentin-declined-390.png`
- `tests/research/artifacts/trade-06/regression-03/08-valentin-declined-430.png`
- `tests/research/artifacts/trade-06/regression-03/09-fatima-expired-1280.png`
- `tests/research/artifacts/trade-06/regression-03/09-fatima-expired-375.png`
- `tests/research/artifacts/trade-06/regression-03/09-fatima-expired-390.png`
- `tests/research/artifacts/trade-06/regression-03/09-fatima-expired-430.png`
- `tests/research/artifacts/trade-06/regression-03/10-dev-roles-390.png`
- `tests/research/artifacts/trade-06/regression-03/11-slot-before-decline-390.png`
- `tests/research/artifacts/trade-06/regression-03/12-slot-after-decline-390.png`
- `tests/research/artifacts/trade-06/regression-03/checks.json`
- `tests/research/artifacts/trade-06/regression-03/index.html`
- `tests/research/artifacts/trade-06/regression-04/01-packing-zero-1280.png`
- `tests/research/artifacts/trade-06/regression-04/01-packing-zero-375.png`
- `tests/research/artifacts/trade-06/regression-04/01-packing-zero-390.png`
- `tests/research/artifacts/trade-06/regression-04/01-packing-zero-430.png`
- `tests/research/artifacts/trade-06/regression-04/02-first-mark-390.png`
- `tests/research/artifacts/trade-06/regression-04/03-packing-partial-390.png`
- `tests/research/artifacts/trade-06/regression-04/04-packing-22-390.png`
- `tests/research/artifacts/trade-06/regression-04/05-packing-23-390.png`
- `tests/research/artifacts/trade-06/regression-04/06-packing-complete-390.png`
- `tests/research/artifacts/trade-06/regression-04/07-missing-review-390.png`
- `tests/research/artifacts/trade-06/regression-04/08-missing-reported-390.png`
- `tests/research/artifacts/trade-06/regression-04/09-secondary-receive-390.png`
- `tests/research/artifacts/trade-06/regression-04/10-fatima-packing-390.png`
- `tests/research/artifacts/trade-06/regression-04/12-dev-independent-390.png`
- `tests/research/artifacts/trade-06/regression-04/checks.json`
- `tests/research/artifacts/trade-06/regression-04/demos.html`
- `tests/research/artifacts/trade-06/regression-04/index.html`
- `tests/research/artifacts/trade-06/regression-04/marker-A-unpacked-390.png`
- `tests/research/artifacts/trade-06/regression-04/marker-B-first-paint-0ms-390.png`
- `tests/research/artifacts/trade-06/regression-04/marker-C-packed-390.png`
- `tests/research/artifacts/trade-06/regression-04/marker.html`
- `tests/research/artifacts/trade-06/regression-05/01-packing-21-390.png`
- `tests/research/artifacts/trade-06/regression-05/01b-missing-reported-390.png`
- `tests/research/artifacts/trade-06/regression-05/02-valentin-waiting-1280.png`
- `tests/research/artifacts/trade-06/regression-05/02-valentin-waiting-375.png`
- `tests/research/artifacts/trade-06/regression-05/02-valentin-waiting-390.png`
- `tests/research/artifacts/trade-06/regression-05/02-valentin-waiting-430.png`
- `tests/research/artifacts/trade-06/regression-05/03-fatima-proposal-1280.png`
- `tests/research/artifacts/trade-06/regression-05/03-fatima-proposal-375.png`
- `tests/research/artifacts/trade-06/regression-05/03-fatima-proposal-390.png`
- `tests/research/artifacts/trade-06/regression-05/03-fatima-proposal-430.png`
- `tests/research/artifacts/trade-06/regression-05/04-missing-positions-390.png`
- `tests/research/artifacts/trade-06/regression-05/05-counter-positions-390.png`
- `tests/research/artifacts/trade-06/regression-05/06-before-after-390.png`
- `tests/research/artifacts/trade-06/regression-05/07-fatima-accepted-1280.png`
- `tests/research/artifacts/trade-06/regression-05/07-fatima-accepted-375.png`
- `tests/research/artifacts/trade-06/regression-05/07-fatima-accepted-390.png`
- `tests/research/artifacts/trade-06/regression-05/07-fatima-accepted-430.png`
- `tests/research/artifacts/trade-06/regression-05/08-valentin-v2-packed-1280.png`
- `tests/research/artifacts/trade-06/regression-05/08-valentin-v2-packed-375.png`
- `tests/research/artifacts/trade-06/regression-05/08-valentin-v2-packed-390.png`
- `tests/research/artifacts/trade-06/regression-05/08-valentin-v2-packed-430.png`
- `tests/research/artifacts/trade-06/regression-05/09-fatima-progress-retained-1280.png`
- `tests/research/artifacts/trade-06/regression-05/09-fatima-progress-retained-375.png`
- `tests/research/artifacts/trade-06/regression-05/09-fatima-progress-retained-390.png`
- `tests/research/artifacts/trade-06/regression-05/09-fatima-progress-retained-430.png`
- `tests/research/artifacts/trade-06/regression-05/10-fatima-cancelled-1280.png`
- `tests/research/artifacts/trade-06/regression-05/10-fatima-cancelled-375.png`
- `tests/research/artifacts/trade-06/regression-05/10-fatima-cancelled-390.png`
- `tests/research/artifacts/trade-06/regression-05/10-fatima-cancelled-430.png`
- `tests/research/artifacts/trade-06/regression-05/11-valentin-cancelled-1280.png`
- `tests/research/artifacts/trade-06/regression-05/11-valentin-cancelled-375.png`
- `tests/research/artifacts/trade-06/regression-05/11-valentin-cancelled-390.png`
- `tests/research/artifacts/trade-06/regression-05/11-valentin-cancelled-430.png`
- `tests/research/artifacts/trade-06/regression-05/12-shipped-blocked-390.png`
- `tests/research/artifacts/trade-06/regression-05/13-dev-v1-390.png`
- `tests/research/artifacts/trade-06/regression-05/14-dev-v2-390.png`
- `tests/research/artifacts/trade-06/regression-05/15-empty-proposal-390.png`
- `tests/research/artifacts/trade-06/regression-05/checks.json`
- `tests/research/artifacts/trade-06/regression-05/demos.html`
- `tests/research/artifacts/trade-06/regression-05/index.html`
- `tests/research/artifacts/trade-06/scope-checks.json`
- `tests/research/artifacts/trade-06/trade-stack-10.png`
- `tests/research/artifacts/trade-06/trade-stack-37.png`
- `tests/research/artifacts/trade-06/trade-stack-6.png`
- `tests/research/artifacts/trade-06/wall-stack-10.png`
- `tests/research/artifacts/trade-06/wall-stack-37.png`
- `tests/research/artifacts/trade-06/wall-stack-6.png`
