# PAX-06 — Packfreigabe, Adresse und eigener Versand

Preview: http://127.0.0.1:8094/pax/

[390-px-Galerie: elf Screenshots](../tests/research/artifacts/pax-06/index.html).

## Quellen und bestehender Versandflow

Vor Umsetzung: `SAMMLRPAX_CONTRACT_V1.md`, `PAX_05_AUDIT.md`, isolierte App-Factory/Routes/Fixtures, Pax-Templates und aktuelle Renderer/Lifecycle-/Journey-Assets gelesen. Die kanonischen Stack-/Listenquellen bleiben aus den vorausgehenden Audits maßgeblich und sind unverändert.

Produktive Referenz ausschließlich lesend: `App/services/trade_shipping.py`, insbesondere `TradeShippingService.ship` und die richtungsbezogenen Status-DTOs; `App/webapp.py` (`trade_shipping_status_label`, Trade-Status-/Aktionsdarstellung und `/trade/<id>/ship`). Eigener Versand ist dort eine bewusste, autorisierte und idempotente Aktion, getrennt vom Partner-Versand. Nur dieser produktive Service darf später die Reservierungen/Bestände atomar überführen. PAX-06 ruft ihn nicht auf und dupliziert keine Buchung.

Im aktiven Code wurde **kein belegter DHL-/Portallink, keine Carrier-API und kein Versandprodukt-/Preiskatalog gefunden**. Die Suchprüfung schließt Runtime-Python, Templates und JS ein; kodierte Backup-Blobs sind keine aktive Versandintegration. Vorhanden ist der eigene Versandbestätigungs-/Statusflow. Deshalb zeigt PAX-06 einen neutralen lokalen Portal-Demo-Schritt, keinen erfundenen DHL-Adapter. „Brief“ entspricht dem bestehenden Brief-/Sendungsmodell des Sammlr-Kontexts (u.a. SmartDeal AC11), ist hier nur eine Demo-Auswahl ohne Format-, Gewichts-, Tarif- oder Preisbehauptung. Keine weiteren Versandprodukte erfunden. Vor produktiver Anbindung muss der tatsächliche Carrier-Einstieg geklärt werden; dies ist kein Domainkonflikt im angeforderten lokalen UX-Scope.

## State und Grenzen

Der eingefrorene kanonische Demo-Deal enthält die beiden eindeutig fiktiven Adressen genau einmal unter seinen Teilnehmern. Sender liest ausschließlich das Adressobjekt des Empfängers, Empfänger das des Senders. `addressReleased: true` ist eine explizite **simulierte Eigentümerfreigabe nur für diese Demo-Adressen**. Vollständiges Packen ersetzt im produktiven Vertrag keine Eigentümerzustimmung. Das Adress-Gate prüft separat: angenommener Deal, eigene vollständige Packliste, bewusste eigene Packfreigabe und Freigabe durch den Adressinhaber.

Adresse wird erst nach „Packen abschließen“ in einen gelben Action-Zettel eingesetzt, mit maschinell lesbarer Systemschrift und deutlicher Demo-Kennzeichnung. Vorher sind die Adress-DOMs leer, auch bei 22/23 oder bei vollständig markierter, noch nicht freigegebener Liste. Zurück zur Packliste vor Versand widerruft die eigene Packfreigabe und leert die Adressanzeige; eine erneute Freigabe ist erforderlich.

Browsermodell erweitert um getrennte `ready`, `method` und `shipped` je Rolle. Ausschließlich `confirmShipment` setzt die eigene Richtung auf versendet. Vollständiges Packen, Adressanzeige, Portal und Versandauswahl senden nichts. Bestätigung ist idempotent; versendete Packlisten sind nicht mehr editierbar. Der unveränderte eigene Give-Snapshot ist damit im Demo-Lifecycle vollständig versendet; keine reale Bestandsausbuchung.

Die Anfrage bleibt angenommen. Der bestehende lokale Accepted-Zweig heißt intern weiterhin `status: packing`; daraus werden **PACKING / READY_TO_SHIP / SHIPPED_BY_ME / SHIPPED_BY_PARTNER / BOTH_SHIPPED** als richtungsbezogene Trade-Projektion abgeleitet. `Request-State: accepted` wird separat angezeigt. Beide Richtungen versendet ist weder Empfang noch Abschluss.

Operative Kapazität ist nur eine DEV-Projektion, keine Slotengine: je Richtung zwei andere fiktive Verpflichtungen als Testbasis plus der eigene noch abzuarbeitende Teil dieses Deals. Sender belegt den ausgehenden, Empfänger den eingehenden Slot. Annahme/Packfreigabe behalten ihn. Eigener Versand ändert nur den entsprechenden eigenen Wert von 3/3 auf 2/3; Partner bleibt unabhängig belegt. Die Werte werden abgeleitet, nicht mehrfach heruntergezählt.

Nach Versand steht eine kompakte Statusansicht im Vordergrund, ohne aktive Packliste oder Adresse. Partner noch offen ist ein neutraler Normalzustand. Bei beidseitigem Versand sind beide Pakete unterwegs; der Trade bleibt aktiv. Keine Empfangs-/Bewertungsaktion.

Demo-State ausschließlich in `sessionStorage` unter `sammlr-pax-06:<candidate>` pro Tab. PAX-05-Demoeinträge werden nicht migriert oder geändert; eine frische PAX-06-Demo beginnt unter eigenem Schlüssel. Reload erhält PAX-06-State; unterschiedliche Tabs sind kein synchronisierter echter Mehrbenutzerbetrieb.

## Direkte Demo-URLs

- Vollständige, noch nicht freigegebene Packliste: http://127.0.0.1:8094/pax/fatima?demo=complete
- Adressmoment: http://127.0.0.1:8094/pax/fatima?demo=address
- Versand vorbereiten: http://127.0.0.1:8094/pax/fatima?demo=shipping
- Eigener Versand, Partner offen: http://127.0.0.1:8094/pax/fatima?demo=shipped-me
- Partner versendet, eigene Packaufgabe offen: http://127.0.0.1:8094/pax/fatima?demo=shipped-partner
- Beide versendet: http://127.0.0.1:8094/pax/fatima?demo=both-shipped

Bestehende PAX-05-Szenarien bleiben verfügbar. Rollenwechsel unter PREVIEW / DEV zeigt denselben Deal. Query-/Szenarioeinstiege setzen nur die lokale Demo bewusst neu auf. Portal führt ausschließlich zu einer lokalen Ansicht, ohne externes Fenster, Bestellung oder Datenübertragung.

## Tests und Responsive-Ergebnis

- `.venv/bin/python -B tests/research/check_pax_06.py`: **PASS bei 375/390/430 px**. Alle fünf kanonischen Deals zusätzlich im Modell geprüft. Keine Adresse vor eigener vollständiger Freigabe, 22/23 gesperrt, Zustimmungsgate, verschiedene gespiegelte Adressen, separate Richtungen, keine automatische Versandmarkierung, idempotente Bestätigung, unveränderter Partner, eigener Slot frei ohne Partner-Versand, Partner-Slot bleibt, beide versendet ohne Abschluss/Empfang/Bewertung. Keine fremden Versandprodukte. Nach Versand keine Pack-Editierung. Persistenz nach Reload.
- UI: Touch, Enter, Space, Reduced Motion, lesbare Adressen, Post-its innerhalb der Breite, kein horizontaler Overflow, erreichbarer CTA, kompakter Status, Rollenwechsel. Portal und Auswahl lösen keinen Versand aus. **Null externe Requests, null schreibende Requests, keine JS-Fehler.**
- `.venv/bin/python -B tests/research/check_pax_05.py`: **PASS**. Nur erwarteten PAX-05-Endpunkt auf den jetzt beauftragten Adressübergang und den neuen Demo-Speicherschlüssel angepasst. Fehlmengenweg/Packinteraktion/Spiegelung/24h bleiben geprüft.
- `.venv/bin/python -B tests/research/check_pax_04c.py`: **PASS**. Discovery, Fans, Post-it-16/20, Fortsetzungen, Touch/Keyboard und Mobilgeometrie.
- `.venv/bin/python -B tests/research/check_pax_cap10.py`: **21 Fälle PASS**. Mengen 1/2/5/6/10/15/37 bei drei Breiten, tatsächlicher produktiver BRA-3-Renderer, Wall5/Pax10, −2/−2, Faces/Dimensionen/z-index, identische Geometrie ab 10.
- `.venv/bin/python -B tests/research/check_pax_component_parity.py`: **PASS**, Front-/Back-Layer gegen produktive CSS.
- `.venv/bin/python -B -m unittest tests.test_pax_preview`: **6 PASS**; GET-only, keine produktive App-/DB-Anbindung.
- `.venv/bin/python -B -m unittest tests.test_sticker_wall_product_island tests.test_ceoklaue_sticker_list`: **29 PASS**; isolierte temporäre Test-DB im bestehenden Testharness.
- Discovery-Screenshots pixelgleich mit PAX-04b bei 375/390/430.
- SHA-256-Abgleich aller vorbestehenden App-/Test-/Doc-Dateien. Produktive Dateien und alle erfassten Datenbanken unverändert. `pax.js`, `pax.css`, `components.css`, PAX-05-`journey.css`, kanonische Stickerliste, Fixtures und Contract bytegleich.
- `git diff --check` sowie Whitespace-Prüfung neuer/geänderter Textdateien mit `git diff --no-index --check /dev/null DATEI`.

Während der Prüfung behoben: ungültiges Option-Markup; Testauswertung eines geschlossenen DEV-Panels auf dessen Textinhalt korrigiert. Finale Gates bestanden. Keine Full Release Suite erforderlich oder ausgeführt.

## TODO — ausdrücklich nicht umgesetzt

- Pax-Post-its später gegebenenfalls 1–2 Einträge luftiger als die Stickerliste.
- Später roter Textmarker-Haken statt der bestehenden Markierung.

Keine Änderung an 16/20, roten Post-its, Markern oder deren aktueller PAX-05-Geometrie. Kein 14/18-Polish.

## Bestätigung

**Keine Produktiv-DB verändert. Keine produktiven Dateien verändert. Keine produktiven Trade-Routen verändert. Keine externe Versandmutation, kein Kauf und keine Adressübertragung. Kein git add, kein Commit, kein Push, kein Deploy.** Keine Bestandsausbuchung, produktive Slotengine, Empfang, Bewertung, Amendment oder endgültige Problembehandlung.

## Exakte Dateiliste

Geändert:

- `App/templates/pax/detail.html`
- `App/static/pax/journey.js`
- `App/static/pax/lifecycle.js`
- `tests/research/check_pax_05.py`
- `tests/research/artifacts/pax-04c/08-cta-390.png`
- `tests/research/artifacts/pax-05/07-missing.png`
- `tests/research/artifacts/pax-05/05-packing-zero.png`
- `tests/research/artifacts/pax-05/02-opened.png`
- `tests/research/artifacts/pax-05/04-recipient.png`
- `tests/research/artifacts/pax-05/08-packing-complete.png`
- `tests/research/artifacts/pax-05/09-pack-endpoint.png`
- `tests/research/artifacts/pax-05/03-waiting.png`
- `tests/research/artifacts/pax-05/06-packing-partial.png`

Neu:

- `App/static/pax/shipping.css`
- `App/static/pax/shipping.js`
- `docs/PAX_06_AUDIT.md`
- `tests/research/artifacts/pax-06/01-packed-23.png`
- `tests/research/artifacts/pax-06/02-finish-packing.png`
- `tests/research/artifacts/pax-06/03-address.png`
- `tests/research/artifacts/pax-06/04-shipping.png`
- `tests/research/artifacts/pax-06/05-portal-demo.png`
- `tests/research/artifacts/pax-06/06-before-confirmation.png`
- `tests/research/artifacts/pax-06/07-own-shipped.png`
- `tests/research/artifacts/pax-06/08-both-shipped.png`
- `tests/research/artifacts/pax-06/09-dev-before.png`
- `tests/research/artifacts/pax-06/10-dev-after.png`
- `tests/research/artifacts/pax-06/11-recipient-address.png`
- `tests/research/artifacts/pax-06/checks.json`
- `tests/research/artifacts/pax-06/index.html`
- `tests/research/artifacts/pax-06/scope-check.json`
- `tests/research/check_pax_06.py`
