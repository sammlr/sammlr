# SAP-01 – Alle Sammlr

## Ergebnis

`/tauschen/sammlr` ist als serverseitige, authentifizierte und rein lesende
Tauschsuche umgesetzt. Keine Neugestaltung von `/tauschen`, der Partnerseite,
der Stickerwall, Karten, Mengenbubble oder der Trade-Lifecycle-Flows.
Keine Migration 0022 auf geschützten lokalen oder produktiven DBs ausgeführt.
Kein Commit, Push oder Deploy.

## Datenquelle und sichere Ausführung auf Schema 20

Reale Source of Truth bleibt die konfigurierte App-Datenbank. `read_connection`
öffnet sie mit SQLite `mode=ro`, `query_only=ON`, zusätzlichem Authorizer und
konsistentem Read-Snapshot. Keine Datenduplikation, Preview-Fixture oder neue DB
als produktive Datenquelle. Albumtitel aus `albums`, Freigaben aus `user_albums`,
Usernames/Favorit aus `users`, vorhandene Aktivität aus `user_activity`.

`TradeV2Domain.market(actor, selected_albums)` liefert die kanonischen Partner,
relevanten Sticker, verfügbaren Mengen nach Reservierungen, beidseitigen Freigaben,
Balance-Gruppen und maximalen gültigen Dealgrößen. Kein SAP-Nachbau der Matching-
oder Reservationslogik. Ein kleiner zentraler Domain-Helper
`receivable_candidates(pair)` projiziert diejenigen Receive-Kandidaten, die in
mindestens einem zulässigen Deal teilnehmen können. Der gemeinsame Balance-Helper
begrenzt auch den tatsächlich möglichen Favoritenalbum-Anteil.

Auf der vorhandenen lokalen Schema-20-DB wurde genau die schreibgeschützte
SAP-Abfrage erfolgreich ausgeführt; Hash vorher/nachher identisch. Die fehlende
`cross_album_mode`-Spalte wird durch INTEGRATION-02A konservativ als SAME_ALBUM_ONLY
behandelt. Kein Schema-Write, keine automatische Migration, kein STOP erforderlich.
Cross-Album-Freigaben können auf dieser DB bis zum separaten kontrollierten Rollout
von Migration 0022 nicht gespeichert werden. Synthetische V22-Tests prüfen auch
beidseitige Freigaben; keine geschützte DB dient als Ausgangsquelle für Testdaten.

## Funktionen und präzise Zählsemantik

- Default: alle eigenen für den Tauschpool freigegebenen Alben. „Alle“/„Keine“,
  beliebige Kombinationen, unbekannte Albumparameter werden verworfen. Abgewählte
  Alben fehlen in beiden Richtungen, Dealgröße, Albumanzahl, Doppeltensumme und Suche.
  GET-Parameter sind Ansichtszustand, keine dauerhaften Einstellungen.
- Ein Suchfeld: case-insensitive Username oder einzelne/mehrere konkrete Codes.
  Komma, Semikolon, Whitespace, `/` und `|` werden unterstützt; Codes werden mit
  kanonischen Katalogen verglichen. „POR 17“ und „POR17“ sind gleichwertig.
  Doppelte Suchbegriffe zählen einmal. Keine neue Spieler-Metadatensuche.
- Genau zwei Sortierungen: maximaler regelkonformer Tausch (Default) und
  handelbare Doppelte. Letztere zählt verfügbare physische Extraexemplare ausschließlich
  in der aktuell gewählten, beidseitig freigegebenen Albumschnittmenge; keine
  accountweite Summe. „Für dich relevant“ zählt unterschiedliche aktuell empfangbare
  Codes, nicht dieselben Mehrfachexemplare mehrfach.
- Bei konkreter Mehrfachsuche zuerst Zahl unterschiedlicher passender Suchcodes,
  danach gewählte fachliche Sortierung. Ohne konkrete Suche ist die gewählte
  mathematische Kennzahl uneingeschränkt primär. Bei Gleichstand: erreichbarer
  Favoritenalbum-Anteil, relevante Überschneidung, vorhandene gültige Aktivitätszeit,
  User-ID. Aktivität überholt niemals eine größere Dealgröße. Kein Ranking-Score.
- Kompakte Zeilen ohne Avatare oder ausgeschriebene Albumlisten. Albumzahl bezeichnet
  Alben mit möglichen Beiträgen zum gültigen Tauschraum, nicht ignorierte Nullbereiche.
  Reguläre Zeilen führen auf die bereits vorhandene Partnerroute.
- Ohne gültigen Deal kein normales Ergebnis. Nur konkrete Stickersuche kann
  zusätzliche Sammlr zeigen. Das separate Template zeigt verfügbare gesuchte
  Sticker ohne derzeit möglichen Gegentausch. Auch wenn mit demselben Partner
  ein anderer Deal möglich wäre, wird ein gesuchter Sticker aus einem gesperrten
  Balance-Bereich nicht als handelbarer Suchtreffer ausgegeben. Die Zusatzsektion
  formuliert ausdrücklich „kein möglicher Tausch mit diesem Sticker“.
- Initial höchstens 50 Partner insgesamt, reguläre vor zusätzlichen. „Mehr anzeigen“
  erweitert serverseitig um 50; Auswahl, Suche und Sortierung bleiben in der URL.
  Kein Infinite Scroll. Ergebnisse werden bei jedem GET frisch berechnet.
- Ohne JavaScript bleiben Formular, Checkboxen, Suche, Sortierung und Pagination
  bedienbar; JS ergänzt sofortiges Absenden bei Album-/Sortierwechsel und Alle/Keine.

## Tests und visuelle Prüfung

- Vollständiges bestehendes Releasegate: **1.330 Tests bestanden**, keine Fehler
  oder Skips; 12 unveränderte historische R5-Ausschlüsse, keine neuen Ausschlüsse.
- **15 SAP-Tests** darin: Default/Keine, beidseitige Filterschnittmenge, ausgeschlossene
  Alben in beiden Richtungen und Suche, Maximalgröße, Doppeltensumme, Einzel-/Mehrfach-
  und Namenssuche, Trennzeichen, kombinierte Sortierung, Favorit, Überschneidung,
  Aktivität/ID, isolierte Null-Deal-Treffer, einseitige/beidseitige Cross-Freigabe,
  Reservierungen, 50er-Grenze, Parametererhalt, Read-only-Hash und ungültige Parameter.
- **8 separate Pax-/Trade-Preview-Tests bestanden**.
- SAP-Browserabnahme auf **375/390/430/1280 px** bestanden: echte Filterinteraktion,
  Suche, beide Sortierungen, Nachladen, zusätzliche Suchsektion, Partnernavigation,
  kein horizontaler Overflow, Nachladeaktion nicht von Bottom-Navigation verdeckt.
  Keine Browserfehler oder Nicht-GET-Requests; synthetische DB vor/nachher bytegleich.
- Screenshots für alle vier Breiten; 390 und 1280 visuell geprüft. Der erste mobile
  Screenshot bei 375 wurde ebenfalls visuell geprüft. Bestehende Header-/Form-
  Typografie wiederverwendet. Kein Eingriff in kanonische Checkbox-/Kartenkomponenten.
- Zwei Fehler im ersten Browser-Testskript (mehrdeutiger Submit-Selektor und fehlendes
  Warten auf Navigation) wurden im Test korrigiert; der komplette SAP-Browserlauf
  wurde danach erfolgreich wiederholt.

## Begehung und Einschränkungen

Produktive Route: `http://127.0.0.1:8080/tauschen/sammlr` nach Laden des aktuellen
Source-Stands durch die normale lokale App. Kein produktiver Server wurde dafür
neu gestartet und keine echte Sitzung oder Nutzerdaten verändert.

Bereitgestellte isolierte Begehung mit synthetischen Daten:
`http://127.0.0.1:18081/sap-fixture-login` → `/tauschen/sammlr`.
Der Test-Login existiert ausschließlich im unter `/private/tmp` gestarteten
Research-Harness, niemals in der produktiven App. Die Preview nutzt die echten
produktiven Templates/Services mit einer synthetischen Schema-20-DB.

Screenshots: `tests/research/artifacts/sap-01/default-390.png`, `default-1280.png`
sowie Suchansichten und weitere Breiten im selben Ordner.

Keine Spielernamensuche ohne verlässliche bestehende Metadaten. Bei identischen
Codes in mehreren ausgewählten Alben zählt die Suchabdeckung den Suchbegriff einmal;
Albumzugehörigkeit und Mengen bleiben in der Domain getrennt. Der bestehende
Partnerbereich wird unverändert geöffnet und besitzt noch keine neue Profil×Trade-
Zwischenwelt oder produktiven manuellen Write-Flow. Pagination begrenzt das Rendern,
nicht die vollständige fachliche Marktberechnung für globale Sortierung.

## Exakter Dateiumfang dieses Auftrags

Bestehende Dateien geändert (INTEGRATION-02A-Vorarbeit bleibt erhalten):

- `App/trade_shell.py`
- `App/services/trade_v2_domain.py`

Neu erstellt:

- `App/services/trade_search.py`
- `App/trade_search_routes.py`
- `App/templates/trade_search.html`
- `App/templates/trade_search_additional.html`
- `App/static/trade_search.css`
- `App/static/trade_search.js`
- `tests/test_sap01_search.py`
- `tests/research/check_sap01.py`
- `docs/SAP_01_AUDIT.md`

Neue Prüfartefakte/Screenshots:

- `tests/research/artifacts/sap-01/browser-results.json`
- `tests/research/artifacts/sap-01/db-hashes.json`
- `tests/research/artifacts/sap-01/default-1280.png`
- `tests/research/artifacts/sap-01/default-375.png`
- `tests/research/artifacts/sap-01/default-390.png`
- `tests/research/artifacts/sap-01/default-430.png`
- `tests/research/artifacts/sap-01/final-checks.json`
- `tests/research/artifacts/sap-01/regression-gates.json`
- `tests/research/artifacts/sap-01/release-tests.json`
- `tests/research/artifacts/sap-01/scope.json`
- `tests/research/artifacts/sap-01/search-1280.png`
- `tests/research/artifacts/sap-01/search-375.png`
- `tests/research/artifacts/sap-01/search-390.png`
- `tests/research/artifacts/sap-01/search-430.png`

## Abschlussprüfung

TRADE-01–11 erneut vollständig bei 375/390/430/1280 px bestanden. Kanonische
Listen-/Stack-Parität: 28 Mengen-/Viewportkombinationen bestanden, Wall-Cap 5
und Trade-Cap 10 unverändert. Keine Geometrie-, Bubble- oder Lifecycleänderung.

Alle 15 geschützten lokalen DBs existieren weiterhin und sind SHA256-bytegleich
zum Beginn dieses Auftrags. Keine neue DB im Repository; Tests ausschließlich
synthetisch unter `/private/tmp`, keine Kopien realer Nutzerdaten. Schema 20 der
lokalen DB unverändert. Hashpaare in `db-hashes.json`.

Beide Diff-Checks ohne Befund. Index leer. HEAD unverändert
`89c957de0b3ab9f412c6d8f6648cb00f3184a051`. 27 bereits bekannte tracked Änderungen
insgesamt; davon wurde in diesem Auftrag nur `App/trade_shell.py` weiterbearbeitet.
`trade_v2_domain.py` war als neue INTEGRATION-02A-Datei bereits ungetrackt vorhanden.
Die übrigen vorbestehenden Source-/Designänderungen sind erhalten. Vollständiger
SAP-Dateiumfang oben, zusammengefasster Gitstatus in `final-checks.json`.
Keine Staging-Aktion, kein Commit, Push oder Deploy.
