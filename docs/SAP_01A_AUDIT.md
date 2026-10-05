# SAP-01A – Vereinfachung und leichter UI-Polish

## Ergebnis

Die bestehende produktive Route `/tauschen/sammlr` ist vereinfacht. Kein Redesign
von Börsen-Startseite, Partnerseite oder anderen Trade-Bereichen.

- Sortierumschalter und „Meiste Doppelte“ aus dem Workflow entfernt. Alte
  `sort=duplicates`-URLs werden als normale Deal-Suche behandelt; Nachlade-Links
  enthalten keinen Sortierparameter mehr. Der vorhandene interne DTO-Default
  `sort='deal'` bleibt kompatibel, beeinflusst aber keine Auswahl zwischen Rankings.
- Größte aktuell gültige Dealgröße ist immer primär, auch bei Mehrfachsuche.
  Suchabdeckung ordnet nur noch gleich große Deals; bestehender Favoriten-,
  Überschneidungs-, Aktivitäts- und stabiler ID-Tie-Break bleiben nachgelagert.
  Suche, Tokenisierung und fachliche Gültigkeit bleiben erhalten. Keine Änderung
  der Trade-Domain oder der SmartDeal-Zielfunktion.
- Native auf-/zuklappbare Albumwahl: „Tauschalben“, „Alle N ausgewählt“ bzw.
  „N von M ausgewählt“/„Keine ausgewählt“. Kein Modal und kein Overlay.
  Checkboxen, Alle/Keine und GET-Ansichtszustand bleiben funktional erhalten.
- Ein sichtbares primäres Suchfeld über die mobile Breite, Placeholder exakt
  „Sticker oder Sammlr suchen …“. Zugängliches Label bleibt vorhanden.
- Ruhige vollständig anklickbare Ergebniszeilen: Name, hervorgehobene maximal
  gültige Stickerzahl, sekundäre Albumzahl, dezentes Chevron und Trennlinie.
  Keine Avatare, Doppeltenzahlen, ausgeschriebenen Albumlisten, Extra-Buttons oder
  zusätzliche Suchtreffer-Erklärzeile. Native App-Typografie und bestehende
  Farbvariablen werden wiederverwendet.
- Separate Zusatzsektion bleibt unverändert funktional, wird sekundär dargestellt.
  Pagination bleibt 50 + „Mehr anzeigen“, ohne Infinite Scroll.

## Unverändert und geschützt

`TradeV2Domain`, Cross-Album-/Balance-Regeln, SmartDeal, Favoritenberechnung,
Stickerwall/-geometrie, Migration 0022, DB, Börsen-Startseite, Partnerseite,
manuelle Deals, Requests und Zentrale sind unverändert. Die Domain- und anderen
geschützten Source-Dateien wurden gegen ihre SHA256-Werte vor Auftrag verglichen.
Doppeltenstatistiken bleiben in Datenbank und Query-Projektion erhalten; ihre
Bestands-/Filterprüfungen wurden nicht entfernt.

Keine Migration oder Mutation einer geschützten lokalen/produktiven DB. Alle
Tests ausschließlich mit synthetischen Daten unter `/private/tmp`. 15 geschützte
lokale DBs weiterhin vorhanden und SHA256-identisch. Hashpaare in den Artefakten.

## Testnachweise

- **1.331 Release-Tests bestanden**, keine Fehler/Skips. 12 vorher bestehende
  R5-Vertragsausschlüsse unverändert, keine neu ausgeschlossenen Tests.
- Darin **16 SAP-Funktionstests**. Bestehende Prüfungen bleiben erhalten;
  Doppeltensummen werden weiterhin geprüft, Sortier-/Nachladeerwartungen wurden
  auf die einzige Deal-Reihenfolge angepasst. Zusätzlicher Test beweist, dass
  alte Doppelte-URLs und höhere Suchtrefferzahlen größere gültige Deals nicht
  überholen. Doppeltendaten bleiben vorhanden.
- **8 separate Pax-/Trade-v2-Preview-Tests bestanden**.
- SAP-Browserabnahme bei **375/390/430/1280 px**: kein Sortierumschalter oder
  Doppeltenzahlen, kompakter geschlossener Albumfilter, Alle/Keine, Albumwechsel,
  Einzel-/Mehrfach-/Namensuche, Nachladen mit Parametererhalt, Zusatzsektion,
  Partnernavigation, keine horizontalen Overflows, „Mehr anzeigen“ nicht von
  Bottom-Navigation verdeckt. Keine JS-Fehler oder Nicht-GET-Requests;
  synthetische DB bytegleich vor/nach Browserlauf.
- Screenshots 390 und 1280 visuell geprüft. Bilder aller vier Breiten gespeichert.
- Begehungs-Einstieg geprüft: HTTP 200 und aktualisierte SAP-01A-Ansicht.

## Exakt geänderte Dateien

- `App/services/trade_search.py`
- `App/templates/trade_search.html`
- `App/static/trade_search.css`
- `App/static/trade_search.js`
- `tests/test_sap01_search.py`
- `tests/research/check_sap01.py`

Neu: dieses Audit `docs/SAP_01A_AUDIT.md` sowie die unten aufgeführten Prüfartefakte.
Bestehende SAP-01-Screenshots und Audits bleiben als historischer Stand erhalten.
Dieses Audit superseded ausschließlich die SAP-Oberfläche und Sortierauswahl.

## Begehung

`http://127.0.0.1:18081/sap-fixture-login`

Die laufende Begehung zeigt den produktiven Code mit rein synthetischen Daten.
Der Test-Login existiert ausschließlich im isolierten Research-Harness.
Die produktive Route bleibt `/tauschen/sammlr`; kein echter App-Server wurde neu
gestartet und keine reale Sitzung verändert. Kein Commit, Push oder Deploy.

## Abschließende Regression und Gitstatus

TRADE-01 bis TRADE-11 bei allen vier Breiten bestanden. Zusätzlich 28 kanonische
Listen-/Stack-Paritätsvergleiche bestanden, Wall-Cap 5 und Trade-Cap 10 erhalten.
Alle sechs bearbeiteten Source-/Testdateien sind bytegleich zum getesteten
isolierten Checkout. Keine weitere vorhandene Datei wurde in diesem Auftrag
verändert. Kein neues DB-File im Repository. Beide Diff-Checks ohne Befund.
Index leer; HEAD weiterhin `89c957de0b3ab9f412c6d8f6648cb00f3184a051`.
27 vorbestehende tracked Modifikationen insgesamt bleiben erhalten; die sechs
SAP-01A-Dateien waren bereits als neue SAP-01-Dateien ungetrackt vorhanden.
Keine Staging-Aktion, kein Commit, Push oder Deploy.

Neu erstellte Prüfartefakte/Screenshots:

- `tests/research/artifacts/sap-01a/browser-results.json`
- `tests/research/artifacts/sap-01a/db-hashes.json`
- `tests/research/artifacts/sap-01a/default-1280.png`
- `tests/research/artifacts/sap-01a/default-375.png`
- `tests/research/artifacts/sap-01a/default-390.png`
- `tests/research/artifacts/sap-01a/default-430.png`
- `tests/research/artifacts/sap-01a/final-checks.json`
- `tests/research/artifacts/sap-01a/regression-gates.json`
- `tests/research/artifacts/sap-01a/release-tests.json`
- `tests/research/artifacts/sap-01a/search-1280.png`
- `tests/research/artifacts/sap-01a/search-375.png`
- `tests/research/artifacts/sap-01a/search-390.png`
- `tests/research/artifacts/sap-01a/search-430.png`
