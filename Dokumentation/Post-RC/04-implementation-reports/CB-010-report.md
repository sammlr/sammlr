# CB-010 – Implementierungsreport

**Stand:** 2026-08-18
**Empfehlung:** CB-010 ABGENOMMEN

## 1. Ziel

Eine einzige read-only Fachgrenze für erfolgreiche Trades, ihre gerichteten
Positionen und sämtliche daraus abgeleiteten Aggregate herstellen. Es wurden
keine Lifecycle-, Buchungs-, Rating-, Notification-, Feed- oder
Bestandsregeln verändert.

## 2. Ausgangszustand

Erfolg wurde mehrfach und widersprüchlich gelesen. Profil und Statistik
vertrauten zu stark auf `trade_requests.status='completed'`; das Archiv hatte
einen stärkeren, aber in Flask duplizierten Lifecycle-Check und erfand für
Legacy den Request-Erstellungszeitpunkt als Abschlussdatum. Statistik summierte
beide JSON-Richtungen ohne Nutzerperspektive. Eine gemeinsame Album-, Partner-
oder Largest-Trade-Projektion existierte nicht.

## 3. Geänderte Dateien

- Fachgrenze: `App/services/successful_trade_projection.py`
- minimale Verbraucher: `App/services/collector_profiles.py`, `App/webapp.py`
- neue Tests: `tests/test_cb010_successful_trade_projection.py`
- angepasste Vertragsfixtures/Regressionen:
  `tests/test_s02_tradeflow_regression.py`,
  `tests/test_s26_collector_profiles.py`,
  `tests/test_s28_trade_ratings.py`
- Dokumentation: Closed-Beta-Bauplan und dieser Report

## 4. Migration JA/NEIN

**NEIN.** V0016 enthält alle benötigten Fakten. Es gibt keine neue Tabelle,
Materialisierung, Datenänderung oder historische Rekonstruktion.

## 5. Bestandsaufnahme bisheriger Trade-Zählungen

| Stelle | Tabellen/Status vorher | Perspektive/Dedupe | Mengen/Album/Partner/Zeit | Abweichung |
|---|---|---|---|---|
| Profil | `trade_requests completed`, optional `trades completed` | Teilnehmerfilter, Request `DISTINCT` | nur Count | Receipts und Problemreste fehlten |
| Statistik | nur `trade_requests completed` | Teilnehmerfilter, einmal je Request | `len(give)+len(get)`, keine Richtung; kein Album/Partner/Zeit | Lifecycle-/Problemzustand ignoriert |
| Tradearchiv | Request + Lifecycle + Receipt + Problems | Nutzerperspektive, einmal je Request | JSON-Längen, Requestalbum, Gegenpart; Lifecyclezeit oder `created_at` | Logik in Flask; Legacyzeit erfunden; keine Cross-Album-Positionen |
| Ratings | `trades` + `trade_ratings`; `completed`, `closed_with_problem`, `problem_resolved_after_close` | je Bewertungsrichtung, nicht Tradecount | keine Trademengen | abhängiges Feature, darf keine Erfolgsquelle sein |
| Home | aktive Lifecyclezustände | Nutzerperspektive | operative Aufgaben | keine Erfolgskennzahl, nicht betroffen |
| Trophy-Legacyfallback | Request `completed` | Teilnehmerfilter | nur Count | ab V0015/V0016 im kanonischen Pfad nicht aktiv; nicht geändert |
| Datenexport | rohe Request-/Lifecycle-/Positionsdaten | Ownershipfilter | Faktenexport | keine Erfolgskennzahl, nicht betroffen |

Profil, Statistik und Archiv lesen nun minimal dieselbe CB-010-Grenze. Die
sichtbare Statistik bleibt gestalterisch unverändert; CB-014/CB-015 wurden
nicht vorgezogen.

## 6. Kanonische Erfolgsdefinition

- Legacy: Requeststatus exakt `completed` und keine Lifecycle-Repräsentation.
- Lifecycle: Requeststatus `completed`, Lifecyclezustand `completed`, beide
  Receipt-Flags wahr und weder offener Problemreport noch offene Restmenge.
- Aktive, nur versendete, teilweise empfangene sowie problemterminal beendete
  Trades zählen nicht.
- Rating, Notification und heutiger Bestand sind keine Evidence.

## 7. Lifecycle-Erfolg

Die Servicegrenze liest Request, `trades`, `trade_receipt_status`,
`trade_positions` sowie Problemreports/-positionen. Request- und Lifecycle-
Parteien müssen identisch sein. Fremde oder mehrdeutige Positionen lassen den
Trade fail-closed aus der Projektion fallen.

## 8. Legacy-Erfolg

Ein eindeutig `completed` markierter Legacy-Request zählt. Seine persistierten
`give_codes`/`get_codes` werden strikt als Listen gelesen und aus Sicht des
Nutzers gerichtet. Ungültiges JSON wird nicht interpretiert. Ein
Abschlusszeitpunkt bleibt `NULL`.

## 9. Deduplizierung Legacy/Lifecycle

Die eindeutige Beziehung `trades.legacy_trade_request_id` entscheidet die
Repräsentation: Existiert sie, wird ausschließlich Lifecycle ausgewertet. Der
zugrunde liegende Request wird nie zusätzlich als Legacy-Erfolg ausgegeben.

## 10. Stabile Trade-Identität

Kanonische IDs sind `lifecycle:<20-stellige-id>` beziehungsweise
`legacy:<20-stellige-request-id>`. Zusätzlich bleiben `source_type`,
`source_id` und `trade_request_id` explizit verfügbar.

## 11. Nutzerperspektive

Jedes DTO enthält `user_id`, `partner_user_id`, gerichtete Given-/Received-
Positionen und beide getrennten Summen. A und B erhalten dieselbe kanonische
Trade-ID, aber spiegelverkehrte Richtungswerte. Unbeteiligte Nutzer erhalten
keinen Datensatz.

## 12. Positions-/Mengenvertrag

Lifecyclewerte stammen ausschließlich aus `trade_positions.quantity`.
Legacywerte stammen ausschließlich aus den gespeicherten JSON-Codes; gleiche
Codes werden verlustfrei zu Mengen gruppiert. Current-State-Inventar wird nie
als historische Trademenge gelesen.

## 13. Albumfilter

Ein Trade erscheint in jedem Album mit mindestens einer belegten Position,
dort aber nur einmal. Albumaggregate filtern beide Positionsrichtungen auf das
Album; global bleibt ein Cross-Album-Trade genau ein Erfolg.

## 14. Distinct Partner

`distinct_partner_count` ist die Menge der `partner_user_id` ausschließlich
aus der kanonischen Erfolgsliste. Freundschafts- oder Blockzustände werden
nicht nachträglich auf historische Erfolge angewendet.

## 15. Größter Trade

PO-Entscheidung umgesetzt: Score ist
`max(given_quantity_total, received_quantity_total)`. Beide Richtungswerte
bleiben separat. Nicht verwendet werden Summe oder Minimum. Bei gleichem Score
gewinnt ein belastbarer Timestamp vor einem fehlenden oder nicht parsebaren
Timestamp, danach der spätere `completed_at` und schließlich die aufsteigend
stabile kanonische Trade-ID. Das ist nur deterministische Auswahl, keine
Nutzerwertung.

Die Auswahl liegt explizit in `_largest_trade(...)`; `_completion_rank(...)`
normalisiert ISO-/SQLite-Zeitwerte nach UTC und stuft `NULL`, leer oder nicht
parsebar als nicht belastbar ein. Die im Fortsetzungsauftrag beschriebene
Änderung wurde geprüft und **angepasst**: Im tatsächlich vorgefundenen Working
Tree war der Score bereits korrekt, die Auswahl erfolgte aber noch indirekt
über die vorherige Listensortierung plus `max(...)`; eine explizite
`_largest_trade(...)`-Methode war dort noch nicht vorhanden.

| Sonderfall | Nachweis |
|---|---|
| A: 18 erhalten / 21 abgegeben | Score 21 |
| B: 20 erhalten / 5 abgegeben | Score 20 |
| C: 7 erhalten / 7 abgegeben | Score 7 |
| D: Score 20 gegen 18 | Score 20 gewinnt |
| E: Scoregleichstand | späteres `completed_at` gewinnt |
| F: Timestamp gegen `NULL` | belastbarer Timestamp gewinnt |
| G: Score und Timestamp gleich | kleinere stabile kanonische ID gewinnt |
| H | `given + received` ist nachweislich nicht der Score |
| I | `min(given, received)` ist nachweislich nicht der Score |
| Zusatz | nicht parsebarer Timestamp wird wie fehlend behandelt |

## 16. Abschlusszeitpunkt

Lifecycle verwendet ausschließlich `trades.completed_at`. Legacy bleibt
`NULL`; `trade_requests.created_at` wird nicht mehr als Abschlusszeitpunkt
ausgegeben. Listen sortieren bekannte Zeitpunkte absteigend, dann kanonische
ID; unbekannte Legacyzeitpunkte stehen deterministisch am Ende.

## 17. Service/API

`SuccessfulTradeProjectionService` bietet:

- `trades_for_user(user_id, album_id=None)`
- `count_for_user(user_id, album_id=None)`
- `aggregates_for_user(user_id, album_id=None)`
- DTOs für Position, Trade und Aggregate
- zentrale Legacy-/Lifecycle-Erfolgspredikate

Alle Aggregate werden aus derselben projizierten Trade-Liste gebildet; es gibt
keine parallele Aggregat-SQL-Wahrheit. Die Grenze hat keine Flask-Abhängigkeit
und mutiert nicht.

## 18. Profil-/Statistik-Integrationsstatus

Profilcount, `/statistik` und Tradearchiv verwenden die Servicegrenze. Das
Archiv nutzt gerichtete Positionsmengen und zeigt bei Legacy bewusst
`Zeitpunkt nicht verfügbar`. Keine neue Statistiksektion, kein Cross-Album-UI
und kein Profil-/Designumbau wurden umgesetzt.

## 19. Ratings-Abgrenzung

Die Ratinglogik blieb unverändert. Ratings werden von CB-010 weder gelesen noch
geschrieben. Ein Rating erzeugt keinen Erfolg; ein fehlendes Rating verhindert
keinen Erfolg; mehrere Ratings vervielfachen keinen Trade. Dass Rating-
Eligibility eigene problemterminale Zustände kennt, bleibt ein separater
bestehender Produktvertrag und keine Erfolgsdefinition.

## 20. Security/Ownership

Die erste Query ist auf echte Requestteilnahme begrenzt. Partner wird nur aus
den zwei Requestparteien ermittelt. Lifecycle-Parteien und sämtliche
Positionsparteien werden dagegen validiert. Albumfilter kann keine fremden
Trades oder Positionen einblenden. Es gibt keinen neuen Endpoint.

## 21. Performance

Eine typische vollständige Nutzerprojektion benötigt konstant acht SELECTs:
fünf kleine Schema-Capability-Checks sowie je eine Bulkquery für Requests,
Positionen und Problemreste. Anzahl der Trades/Positionen erzeugt kein N+1.
Aggregate und Albumfilter arbeiten danach im Speicher aus derselben Liste. Ein
neuer Index oder eine Migration ist für den realistischen Bestand nicht nötig.

## 22. Realistischer Daten-Audit

Auditbasis war eine per SQLite Backup API erzeugte Kopie der lokalen V7-DB,
isoliert nach V0016 migriert. Ergebnis:

| Nutzer | Erfolge | abgegeben | erhalten | Partner | größter kanonischer Trade / Score |
|---:|---:|---:|---:|---:|---|
| 1 | 12 | 40 | 35 | 1 | Lifecycle 4 / 6 |
| 2 | 13 | 36 | 41 | 2 | Lifecycle 4 / 6 |
| 3 | 1 | 1 | 1 | 1 | Legacy Request 2 / 1 |
| 7 | 0 | 0 | 0 | 0 | – |

Global liegen 13 fachliche Trades vor: 8 erfolgreiche Lifecycle- und 5
erfolgreiche Legacy-Trades. Albumbeispiele:

| Nutzer/Album | Trades | abgegeben | erhalten |
|---|---:|---:|---:|
| 1 / VfL | 6 | 19 | 18 |
| 1 / WM26 | 6 | 21 | 17 |
| 2 / VfL | 6 | 18 | 19 |
| 2 / WM26 | 7 | 18 | 22 |

## 23. Ausgeschlossene/unklare Trades

Zwei vorhandene Lifecycle-Trades sind `partially_received` und werden
ausgeschlossen. Cancelled/failed Requests zählen ebenfalls nicht. Unter den
fünf abgeschlossenen Legacy-Requests existiert kein ungültiges JSON und damit
kein unklarer abgeschlossener Legacyfall. Fehlende Legacy-Completionzeiten
bleiben als bekannte Datenlücke `NULL` statt Ausschluss oder Erfindung.

## 24. Gezielte Tests

22 neue CB-010-Testmethoden decken die geforderten Kern- und Aggregatfälle ab:
beide Perspektiven, Mehrpositionen, Richtungen, Partnerdedupe, aktive/
versendete/partielle/problemterminale Zustände, Receipts, Problemreste,
Legacy/unklares JSON, Dedupe, Cross-Album-Filter, alle Largest-Sonderfälle A–I,
nicht belastbare Timestamps, Ratings, Ownership, Determinismus,
Side-Effect-Freiheit, Querygrenze und Profilintegration. Zusammen mit den
gezielt betroffenen Integrationssuiten: **70/70** in 0,759 s, `OK`.

## 25. Kombinierte Trade-/Historytests

CB-001 bis CB-005, CB-010 sowie relevante Problem-, Completion- und
Ratingtests: **118/118** in 1,364 s, `OK`.

## 26. Regression Lauf 1

**618/618** in 7,315 s, `OK`, 0 Fehler, 0 Skips.

## 27. Regression Lauf 2

**618/618** in 7,506 s, `OK`, 0 Fehler, 0 Skips.

## 28. Integrity/FK

Auf der isolierten V16-Auditkopie: `PRAGMA integrity_check = ok` und
`PRAGMA foreign_key_check` ohne Treffer. Die Kopie meldet Schema V16.

## 29. Startup-Smoke

App-Import gegen die isolierte V16-Kopie erfolgreich. `/healthz` 200 mit
`{"status":"ok"}`, `/login` 200, authentifiziert `/statistik` 200 und
`/profil/trade-archiv` 200.

## 30. Echte DB verändert JA/NEIN

**NEIN.** Vor und nach CB-010 lautet SHA-256 der lokalen DB
`89254d1fe02980a0ccbf85437611273ea094568a064c75ed281f9ca6a23978a0`.
Migration und Audit liefen ausschließlich auf der Backupkopie.

## 31. Bekannte Grenzen

Legacy besitzt keinen beweisbaren Abschlusszeitpunkt. Ungültige Legacy-
Positions-JSONs würden fail-closed ausgeschlossen. Ein erfolgreicher
Lifecycle ohne persistierte Positionen kann als Erfolg zählen, liefert aber
keine erfundenen Mengen oder Albumzuordnung. Die sichtbare tiefere Statistik
und Profilprojektion bleiben Aufgabe von CB-014/CB-015.

## 32. Technische Restpunkte

Innerhalb CB-010 keiner. Spätere Verbraucher müssen die vorhandene
Servicegrenze nutzen. Legacy-Trophyfallbacks und der Rohdatenexport sind keine
kanonischen Erfolgsverbraucher und bleiben in ihren Paketen.

## 33. Abweichungen vom Bauplan

Keine fachliche Abweichung. Die im Bauplan genannten drei bestehenden
Verbraucher wurden minimal technisch vereinheitlicht, ohne ihre UI neu zu
gestalten. Keine Migration war erforderlich. Die PO-Entscheidung zur
Largest-Trade-Definition wurde nach dem vorgeschriebenen Stop explizit
eingearbeitet.

## 34. Product-Contract-Verletzungen JA/NEIN

**NEIN.** Keine historische Zeit oder Menge wurde erfunden; Lifecycle,
Bestand, Ratings, Notifications, Feed und Privacyarchitektur blieben
unverändert.

## 35. Empfehlung

**CB-010 ABGENOMMEN.** Die einheitliche Erfolgsprojektion ist deterministisch,
gerichtet, dedupliziert, albumfilterbar, ownership-sicher und durch den realen
V16-Datenstand bestätigt.

## 36. Kann CB-006 begonnen werden?

**JA.** CB-010 ist ohne Migration abgeschlossen und erzeugt keinen offenen
Blocker für das äußere Privacy-Gate. CB-006 wurde nicht vorgezogen.

## Recovery- und Nachweisdetails

Backup-Artefakt vor Migration:
`sammlr-20260818-200203-v0007.db`, SHA-256
`f59349c6846fe8d5db4b103c2500ce5f0142cbac74e234eb3d4a204ee7f550a4`.
Nach V8–V16 lautete der isolierte Hash
`ef190dde764ae09fee49773bc0eb1725a31dcd4ae6b1a996410a18b0cbf9bc36`.
Die acht vorhandenen Lifecyclezeilen mit Erfolg sind zugleich acht
Request/Lifecycle-Doppelrepräsentationen und werden jeweils genau einmal
projiziert.
