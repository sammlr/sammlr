# PROFILE-TRADE-01 – Fremdprofil als Tausch-Einstieg

## Umsetzung und Begehung

Lokale synthetische Begehung: `http://127.0.0.1:18081/sap-fixture-login`.
Danach:

- Mit Tausch: `/profil/Demo%20Jens` (8 Sticker, 2 tatsächlich beteiligte Alben).
- Ohne Tausch: `/profil/Demo%20ohne%20Gegentausch`.
- SAP-Kontext: `/tauschen/sammlr?filtered=1&album=wm26&q=Demo+Jens` → Fremdprofil
  (3 Sticker, 1 Album); weiterhin alle drei normalen sichtbaren Sammlungsalben.
- Automatisch: SAP → Profil → „Besten Tausch zusammenstellen“ → bestehende
  `/tauschen/sammlr/2/smartdeal`-Dealansicht.
- Manuell: SAP → Profil → „Selbst zusammenstellen“ →
  `/tauschen/sammlr/2/manual` mit bestehender Stickerliste und gelbem Auswahlzettel.

Die produktive SAP-Liste verlinkt direkt die vorhandene `/profil/<username>`-Route,
korrekt URL-escaped. Keine neue Profil-Zwischenroute. Bestehende alte Partnerlinks
bleiben kompatibel; keine Umgestaltung dieser Altansicht.
Profilidentität, Sammlrsticker, Bewertungen und „Sammelt gerade“ bleiben erhalten.
Albumcover führen unverändert in normale privacygeschützte Sammlungsansichten.
Der neue kompakte Handelsbereich steht direkt unter diesen Covern. Eigene Profile
zeigen ihn nicht. Bei null Kapazität bleibt ein ruhiger Status ohne Fake-Deals.

## Fachliche Quelle und temporärer Kontext

`TradeV2Domain.market`, `receivable_candidates`, `validate_deal` und der bestehende
`SmartDealOptimizer.optimize` bleiben die fachliche Basis. Keine Mutation oder
Änderung der Domainregeln, Cross-/Balance-/Reservation-/Slot-/Lifecycle-Semantik.

Die neue gemeinsame Projektion `services.partner_trade` nutzt den bisherigen
Single-Partner-SmartDeal-Aufruf für Auto-Route, Profil und SAP-Albumzählung. Die
maximale Stickerzahl kommt unverändert aus `pair.max_equal_piece_count`.
Die Albumzahl zählt jetzt die Alben des konkreten maximalen Dealpakets des
bestehenden Optimizers, nicht mehr alle theoretischen Kandidatenalben. SAP und
Profil benutzen exakt dieselbe Projektion; der Auto-Deal entspricht dem bisherigen
Single-Partner-SmartDeal unter gleichen Bedingungen. Keine neue Rankingengine.

Die bestehende SmartDeal-Mindestgröße von fünf bleibt bestehen. Für gültige kleinere
manuelle Tausche wird ein deterministisches maximales, bereichsweise ausgeglichenes
Kandidatenpaket zur exakten Albumzählung projiziert; es wird kein SmartDeal unter
fünf erfunden. Der manuelle Weg bleibt möglich, der automatische Weg nennt bei
1–4 die vorhandene Mindestgröße statt einen toten Link anzubieten.

SAP übergibt nur den temporären Tauschraum als `trade_context=1` und wiederholte
`trade_album`-Parameter. Fehlender Kontext bedeutet alle zulässigen Alben;
explizit leere Auswahl bedeutet keinen Tauschraum. Vor Berechnung werden
unberechtigte Alben durch die zentrale Domain entfernt. Keine dauerhaften Settings,
keine neue State-Persistenz. Auf dem Profil kann ein natives Details-/GET-Formular
die Auswahl ändern oder auf alle Tauschalben zurücksetzen. Profil-/Albumprojektion
liest diese Parameter nicht und bleibt unverändert.

## Wiederverwendete manuelle Auswahl

Das bestehende `trade_v2/templates/manual.html`, `manual_view.js`, `manual_ink.js`,
`manual_rules.js` und `manual.css` werden wiederverwendet. Keine neue Auswahloberfläche.
Der produktive Adapter liefert aktuelle kanonische Kandidaten und bereits berechnete
Balance-Gruppen; die existierende JS-Auswahllogik ist nur unmittelbares UI-Feedback.

Die bestehende Preview bleibt im bisherigen Modus erhalten. Im Live-Modus werden
Preview-Requests und Demo-Lifecycle-Module nicht geladen oder gelesen. Vier
explizit erlaubte manuelle Assets sind unter einer authentifizierten Assetroute
verfügbar; keine pauschale Freigabe aller Preview-Module.

Entwürfe bleiben tablokal in der schon vorhandenen SessionStorage-Mechanik, getrennt
nach eingeloggtem Nutzer, Partner und Fingerprint des aktuellen Kandidatenraums.
Kein Teilen mit Demo-Drafts. Änderungen am Kandidatenraum machen alte Entwürfe
unverwendbar. Keine Trade-Bindung, DB-Schreiboperation oder Reservierung.

„Auswahl prüfen“ ruft eine CSRF-geschützte reine Validierungsroute auf. Diese liest
den aktuellen Markt neu, kontrolliert Fingerprint und konkrete Give-/Receive-Codes
über `TradeV2Domain.validate_deal`. Manipulierte, veraltete, doppelte oder unbalancierte
Auswahlen werden serverseitig abgelehnt. Erfolgreiche Prüfung sagt ausdrücklich,
dass noch keine Anfrage erstellt wurde. Das spätere produktive Absenden ist nicht
Bestandteil dieses Auftrags.

## Privacy und Kompatibilität

Die vorhandene Profil-/Albumprivacy bleibt erhalten. Private Sammlungen werden
nicht als Folge des Trade-Einstiegs sichtbar. Die schon bestehende unabhängige
Trade-Pool-Freigabe kann dagegen einen Tausch mit einem privaten Sammler erlauben
(AC03; keine neue Ausnahme). Block-/Account-/Pool-Gates bleiben zentral wirksam.

Ein alter CB-006-HTML-Test wertete auch die Namen der eigenen Alben des Besuchers
im neuen Filterformular als fremde Sammlungsoffenlegung. Die Assertion blendet
jetzt ausschließlich dieses eigene GET-Filterformular aus; alle übrigen Profil-
und Trade-Inhalte bleiben geprüft. Keine Privacy-Assertion oder Testausnahme
entfernt. Zusätzliche Integrationstests prüfen explizit private Sammlung ohne
Albumlinks bei unabhängig erlaubtem Trade-Pool.
Historische Profil-Fixtures vor Schema 20 behalten ihre Profil-only-Darstellung.
Produktive Schema-20/21/22-Pfade werden nicht migriert.

## Tests

- Vollständiges Releasegate: **1.340 Tests bestanden**, keine Fehler/Skips.
  12 unveränderte historische R5-Vertragsausschlüsse, keine neuen Ausschlüsse.
- Darin **9 neue Profil-Trade-Integrationstests**: SAP-Kontext, direkte Profile,
  eigene Profile, identische SAP-/Profilzahlen, unveränderte Sammlung, leerer
  Kontext, bestehender Auto-Pfad, reale manuelle Kandidaten, serverseitige
  Prüfung, veraltete Auswahl, Pool-off, beidseitiges Cross, private Sammlung,
  Asset-Allowlist und unzulässige Partner.
- **8 separate Pax-/Trade-v2-Preview-Tests bestanden**.
- Profilbrowser bei **375/390/430/1280**: SAP → Profil → Auto, Profil → manuelle
  Auswahl → serverseitig gültige Auswahl, Null-Deal-Profil, eigenes Profil,
  unveränderte Albumcover trotz Filter, keine Overflows und erreichbare Aktion
  trotz Bottom-Navigation. Genau vier read-only Validierungs-POSTs, keine Requests
  oder sonstigen Mutationen. Synthetische DB vorher/nachher bytegleich.
- SAP-01A-Browserregression mit neuem Fremdprofilziel ebenfalls bei allen vier
  Breiten bestanden. Filter, Suche, Pagination und Zusatzsektion bleiben erhalten.
- 390- und 1280-Profil sowie 390-manuelle Auswahl visuell geprüft.

Anfangs korrigierte Testfälle: öffentliche Album-Fixture explizit auf `public`
gesetzt (kanonischer Default ist private); CB-006-Prüfung auf eigene Filterdaten
präzisiert; historische Profil-Fixtures ohne Trade-Schema bleiben unangetastet.
Alle betroffenen Tests wurden im vollständigen Releasegate erneut ausgeführt.

## Spätere albuminterne Trades – nur Entscheidung

Ein späterer Trade-Einstieg aus einem fremden Album verwendet ausschließlich dieses
eine Album als Tauschraum, sowohl automatisch als auch manuell. Das ist ein separater
Schritt. Albumseiten wurden hier nicht verändert; keine halbfertigen Buttons ergänzt.

## DB-Schutz

Neue Vorher-Basis ist ausdrücklich der Stand nach dem autorisierten Passwortwechsel
für User-ID 1. Lokale aktive DB: SHA256
`4b706e02c57d01b64bf311f6bdef25800fe27c38848f939c4176dbde45a54d24`.
16 geschützte DB-Dateien einschließlich des dabei angelegten Backups wurden vor/nach
gehasht und sind bytegleich. Tests nur mit synthetischen SQL-Daten unter `/private/tmp`;
keine geschützte DB kopiert oder migriert. Migration 0022 nicht ausgeführt.
Hashpaare in `tests/research/artifacts/profile-trade-01/db-hashes.json`.

## Exakt geänderte bestehende Dateien

- `App/services/trade_search.py`
- `App/templates/trade_search.html`
- `App/trade_shell.py`
- `App/trade_v2/assets/manual_view.js`
- `App/trade_v2/templates/manual.html`
- `App/webapp.py`
- `tests/research/check_sap01.py`
- `tests/test_cb006_profile_privacy_gate.py`

## Neue Dateien

- `App/profile_trade.py`
- `App/services/partner_trade.py`
- `App/static/profile_trade.css`
- `App/templates/profile_trade.html`
- `tests/research/check_profile_trade01.py`
- `tests/test_profile_trade01.py`
- `docs/PROFILE_TRADE_01_AUDIT.md`

Neue Prüfartefakte/Screenshots:

- `tests/research/artifacts/profile-trade-01/auto-1280.png`
- `tests/research/artifacts/profile-trade-01/auto-375.png`
- `tests/research/artifacts/profile-trade-01/auto-390.png`
- `tests/research/artifacts/profile-trade-01/auto-430.png`
- `tests/research/artifacts/profile-trade-01/browser-results.json`
- `tests/research/artifacts/profile-trade-01/db-hashes.json`
- `tests/research/artifacts/profile-trade-01/filtered-profile-1280.png`
- `tests/research/artifacts/profile-trade-01/filtered-profile-375.png`
- `tests/research/artifacts/profile-trade-01/filtered-profile-390.png`
- `tests/research/artifacts/profile-trade-01/filtered-profile-430.png`
- `tests/research/artifacts/profile-trade-01/final-checks.json`
- `tests/research/artifacts/profile-trade-01/manual-1280.png`
- `tests/research/artifacts/profile-trade-01/manual-375.png`
- `tests/research/artifacts/profile-trade-01/manual-390.png`
- `tests/research/artifacts/profile-trade-01/manual-430.png`
- `tests/research/artifacts/profile-trade-01/no-trade-1280.png`
- `tests/research/artifacts/profile-trade-01/no-trade-375.png`
- `tests/research/artifacts/profile-trade-01/no-trade-390.png`
- `tests/research/artifacts/profile-trade-01/no-trade-430.png`
- `tests/research/artifacts/profile-trade-01/profile-1280.png`
- `tests/research/artifacts/profile-trade-01/profile-375.png`
- `tests/research/artifacts/profile-trade-01/profile-390.png`
- `tests/research/artifacts/profile-trade-01/profile-430.png`
- `tests/research/artifacts/profile-trade-01/regression-gates.json`
- `tests/research/artifacts/profile-trade-01/release-tests.json`
- `tests/research/artifacts/profile-trade-01/sap-regression.json`
- `tests/research/artifacts/profile-trade-01/scope.json`

## Abschließende Regression und Gitstatus

TRADE-01–11 bei vier Breiten vollständig bestanden; 28 kanonische Listen-/Stack-
Vergleiche bestanden. Wall-Cap 5 und Trade-Cap 10 unverändert. Begehungslinks für
Profil mit/ohne Trade und manuelle Auswahl abschließend mit HTTP 200 geprüft.

Alle bearbeiteten Implementierungs-/Testdateien sind bytegleich zum erfolgreich
getesteten isolierten Checkout. Beide Diff-Checks sauber. Git-Index leer,
HEAD unverändert `89c957de0b3ab9f412c6d8f6648cb00f3184a051`. Vorbestehende
Änderungen erhalten, keine Staging-Aktion, kein Commit, Push oder Deploy.
Keine neue DB im Repository; die 16 geschützten Dateien bleiben bytegleich.

## Bekannte Grenzen

Auto-SmartDeal weiterhin erst ab fünf Stickern; 1–4 können manuell ausgewählt
und validiert werden. Kein produktives Absenden/Reservieren/Lifecycle in diesem
Schritt. Manuelle Oberfläche entspricht bewusst der bestehenden Trade-v2-Auswahl.
Albuminterne Einstiegsschaltflächen wurden nur als spätere Produktentscheidung
dokumentiert. Die Begehung enthält synthetische Identitäten; für reale Profile
muss die lokale App den aktuellen Source-Stand laden. Der reale App-Prozess auf
Port 8080 wurde nicht neu gestartet oder für Tests benutzt.
