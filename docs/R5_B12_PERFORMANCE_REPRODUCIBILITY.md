# R5 B1.2 – R4 Performance Reproducibility Investigation

Stand: 2026-09-06. **R4 final GREEN unter dem unveränderten lokalen R4-Vertrag. R5 bleibt NEXT; PO-Abnahme ausstehend.**

Drei vorab festgelegte vollständige Wiederholungen bestehen jeweils alle 15 Operationen, ohne HTTP-Fehler. Keine Candidate-Regression nachgewiesen: Runner und relevante Laufzeitpfade weisen keine erklärende Regression auf; derselbe Candidate erfüllt das Gate mehrfach. Die früheren YELLOW-Werte bleiben gültige historische Messungen. Parallelitäts-/Schedulingvarianz ist eine plausible Einordnung, keine rückwirkend bewiesene Einzelursache. Keine Runtime-Optimierung, keine Gate-Lockerung.

## Vergleich und Messvertrag

| Aspekt | Original R4 / B1.1 / B1.2 |
| --- | --- |
| Python / Plattform | Lokal Python 3.13.15, gleicher Build, macOS 26.6.2 arm64; SQLite 3.50.4 |
| Runtime-Pakete | Original-venv und frische B1.1-venv versionsgleich: Flask 3.1.3, gunicorn 26.0.0, Werkzeug 3.1.8, Jinja2 3.1.6, MarkupSafe 3.0.3, click 8.4.2, blinker 1.9.0, itsdangerous 2.2.0, packaging 26.3 |
| Runner | Unveränderter `Scripts/r4_v20_performance_gate.py`; SHA-Vergleich mit frühestem Post-R4-Snapshot und B1/B1.1. Original-JSON enthält selbst keinen Source-Hash; historische Versionsprovenienz daher begrenzt |
| Server | Gunicorn, 1 Worker, 20 Threads, `performance_wsgi:app`, eigener neuer Prozess pro Route |
| Auth | Vorher separater Auth-Prozess, 20 individuelle signierte Sessions; Login besucht Home. Auth-Prozess danach beendet |
| Warm-up | Healthcheck, ein ausgeschlossener erster Routenrequest, fünf serielle Requests; anschließend 20 parallele Requests, Nutzer 1–20 |
| Messgrenzen | HTTP inklusive vollständigem Response-Body; Start/Login/Healthcheck ausgeschlossen; ThreadPoolExecutor(20), keine Startbarriere |
| Statistik | Typical = Median der 5 seriellen Requests; P95 = nearest rank, 19. von 20. GREEN <500 ms und null Fehler; Schwellen unverändert |
| Daten | Synthetisch: 100 Nutzer, 10 Alben, 100 Slots/Album/Nutzer, 100.000 Stickerzeilen, 2.000 Requests, 5.000 Notifications, 1.000 Freundschaften |
| Nutzerzustand | Nutzer 1–20 aktiv, je 10 öffentliche Mitgliedschaften. perf01: 100 belegte Slots, physische Menge 120, 20 Duplikate; keine fehlenden Slots |
| SQLite | V20, DELETE-Journal, Runtime busy_timeout 5000 ms. Der unveränderte isolierte Lockprobe benutzt eigene Verbindungen mit 250 ms |
| Physische Daten | Synthetische Basisfixtures logisch identisch (iterdump). Vorbereitete DBs wegen Zeitstempeln/Passworthashes nicht byteidentisch; original 1859 vs B1.1 1853 Seiten à 4096 Byte; freelist 0, kein sqlite_stat1 |
| Pläne | Archivierte R4-Gate-Query-Pläne und B1.1 identisch; kein belegter Planwechsel |

B1 entfernte lediglich persönlichen Legacy-Seed aus der unbenutzten Initialisierung; B1.1 änderte den persönlichen Profilbild-Fallback. Relevante Album-/Inventory-/Statistikpfade und Performance-WSGI sind unverändert. Ein ungefilterter Cold Request erklärt B1.1 nicht: Der ursprüngliche Vertrag hatte bereits denselben Warm-up.

## Vollständige unveränderte Gate-Reihen

Alle Werte ms, pro Zelle **Typical / P95 bei 20 parallelen Requests**. Alle drei Reihen vollständig, ohne Auswahl einzelner guter Läufe.

| Operation | Lauf 1 | Lauf 2 | Lauf 3 |
| --- | ---: | ---: | ---: |
| login | 0.774 / 10.203 | 0.744 / 10.657 | 0.756 / 11.431 |
| home | 1.608 / 69.341 | 1.643 / 66.834 | 1.714 / 70.834 |
| collection | 3.058 / 66.530 | 3.049 / 67.779 | 3.083 / 67.364 |
| album | 5.894 / 457.928 | 5.910 / 480.934 | 5.836 / 470.084 |
| stickerwall_missing | 6.169 / 456.669 | 5.716 / 477.727 | 6.058 / 489.014 |
| partner_search | 2.043 / 98.959 | 2.078 / 108.483 | 2.047 / 116.090 |
| trade_market | 3.717 / 79.226 | 3.796 / 78.131 | 3.855 / 77.121 |
| trade_requests | 3.811 / 76.084 | 3.925 / 79.292 | 3.945 / 80.439 |
| album_trade_hub | 3.255 / 347.009 | 3.107 / 291.319 | 3.154 / 299.424 |
| deal | 5.375 / 142.695 | 5.322 / 138.107 | 5.287 / 138.105 |
| notifications_gate | 1.363 / 33.497 | 1.331 / 33.114 | 1.238 / 32.658 |
| notifications_inbox | 3.905 / 152.689 | 3.704 / 129.208 | 3.723 / 183.761 |
| profile | 3.551 / 71.497 | 3.491 / 72.725 | 3.385 / 73.544 |
| public_profile | 3.666 / 74.130 | 3.477 / 72.739 | 3.513 / 71.072 |
| public_stickerwall | 3.839 / 203.392 | 3.507 / 203.769 | 3.780 / 175.584 |

Historie: Original R4 Album 442.550 / Missing 265.752 ms P95, alle 15 GREEN. B1.1 Album 631.496 / Missing 635.734, Wiederholung 996.007 / 809.641 ms, jeweils beide YELLOW und übrige 13 GREEN. Diese Werte werden nicht ersetzt oder verworfen.

## Unabhängige Cold-/Warm-Diagnostik

Drei weitere frische Datensätze; pro Route frischer Prozess. Cold bezeichnet nur den ersten Prozessrequest, nicht geleerte OS-Dateicaches. Je Welle fünf serielle und 20 parallele Requests. Diese Zusatzwellen ersetzen keine Gatewerte. Zellen: Typical / P95 in ms.

| Reihe | Route | Cold ms | Welle 1 | Welle 2 | Welle 3 |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | album | 8.879 | 6.080 / 463.751 | 5.539 / 458.506 | 5.485 / 252.782 |
| 1 | stickerwall_missing | 8.867 | 5.969 / 464.030 | 5.619 / 397.535 | 5.639 / 252.504 |
| 1 | home | 2.200 | 1.803 / 90.305 | 1.512 / 83.092 | 1.484 / 75.847 |
| 1 | collection | 5.388 | 3.071 / 67.263 | 2.590 / 64.497 | 2.600 / 64.811 |
| 1 | album_trade_hub | 4.000 | 3.165 / 301.045 | 2.919 / 344.226 | 2.861 / 334.487 |
| 1 | profile | 5.736 | 3.566 / 72.536 | 3.025 / 71.442 | 2.970 / 72.303 |
| 2 | album | 8.301 | 5.836 / 237.756 | 5.501 / 238.343 | 5.522 / 322.452 |
| 2 | stickerwall_missing | 8.905 | 5.934 / 462.377 | 5.599 / 450.367 | 5.593 / 437.549 |
| 2 | home | 2.308 | 1.772 / 77.587 | 1.467 / 62.415 | 1.520 / 67.259 |
| 2 | collection | 5.303 | 3.211 / 66.904 | 2.587 / 63.737 | 2.596 / 64.491 |
| 2 | album_trade_hub | 3.858 | 3.099 / 314.228 | 2.873 / 306.004 | 2.908 / 322.754 |
| 2 | profile | 5.666 | 3.463 / 71.584 | 2.981 / 71.890 | 3.005 / 72.117 |
| 3 | album | 8.700 | 6.026 / 339.300 | 5.683 / 480.704 | 5.692 / 311.482 |
| 3 | stickerwall_missing | 9.223 | 6.222 / 453.681 | 5.608 / 470.285 | 5.611 / 435.316 |
| 3 | home | 2.238 | 1.756 / 76.710 | 1.517 / 75.558 | 1.478 / 66.849 |
| 3 | collection | 5.398 | 3.046 / 65.060 | 2.692 / 65.771 | 2.681 / 66.324 |
| 3 | album_trade_hub | 3.993 | 3.121 / 359.873 | 2.895 / 350.826 | 2.936 / 316.693 |
| 3 | profile | 5.750 | 3.396 / 72.015 | 3.015 / 72.985 | 3.014 / 71.596 |

Alle 18 parallelen Problemroutenwellen erreichten Client-Overlap 20. Cold dort 8–9 ms; warme Wellen werden nicht monoton schneller. Das widerspricht einer einfachen Cold-Start-Erklärung. Host-Load-Kontext liegt für die neuen Reihen vor; zeitgleiche historische Systemlast-/CPU-Daten fehlen. Ein quantitativer historischer Lastvergleich ist deshalb nicht möglich.

## SQL, Query-Pläne, CPU und I/O

Exakte Routen: `GET /album/perf01` und `GET /album/perf01?filter=missing`, beide `albumseite` in `App/webapp.py`. Gemeinsame Arbeit: Inventory, Markt-Vorschau, offene Eingänge, Trophäen und Privacy vor HTML-Filterung. Missing spart diese Arbeit nicht ein. Beide Albumrouten laufen ohne den gemeinsamen `serialized_sqlite_projection`-RLock, der Sammlung und Profil schützt; dies ist bereits der ursprüngliche Aufbau.

Je Route **54 SQL-Ausführungen einschließlich PRAGMAs und Schema-Probes**, sowohl erster als auch warmer Request und alle 20 instrumentierten parallelen Requests. Historische vollständige Request-SQL-Zählungen fehlen; 54 ist der aktuelle Messwert, kein erfundener Originalmesswert.

- Auth: Nutzer-PK SEARCH mit korreliertem `SCAN notifications` (5.000 Zeilen).
- 18 `sqlite_master`-Schema-Probes und fünf `PRAGMA table_info(users)`; acht FK-PRAGMAs.
- Reservation-Lesen nutzt `idx_trade_reservations_active_inventory`.
- Wiederholte Transit-Abfragen: `SCAN trade_positions` über Unique-Index, PK-Lookups für Trade/Versand/Receipt, Index für Problempositionen, temporärer B-Tree für GROUP BY (je Richtung zweimal).
- Offene eingehende Album-Requests: `SCAN trade_requests` (2.000 Zeilen).
- Keine isolierte serielle Query erklärt eine Sekunde Laufzeit; relevante Pläne zeigen bestehende Arbeit, keinen neuen Candidate-Planfehler.

Separate Flask-Testclient-/SQLite-/cProfile-Instrumentierung, **keine R4-Gatezeiten**: erster Albumrequest 8.452 ms, davon SQL 3.250; warm 5.240 / SQL 2.666. Missing 7.486 / SQL 2.788; warm 5.193 / SQL 2.603. Antwortumfang 282.401 / 283.803 Byte. 20 instrumentierte Requests: Album Wall 498.154 ms, User-CPU 0.338 s, System-CPU 2.295 s; Missing Wall 496.742 ms, User-CPU 0.336 s, System-CPU 2.281 s. CPU summiert über Threads darf Walltime übersteigen. OS gemeldete involuntary context switches 195.577 / 196.617; Block-I/O-Zähler jeweils 0. macOS-Zähler beweisen keine vollständige I/O-Abwesenheit.

Hohe System-CPU und Schedulingaktivität zusammen mit starkem Abstand seriell/parallel und nichtmonotonen Warm-Wellen stützen die Empfindlichkeit paralleler SQLite-Lese-/Schemaarbeit gegenüber Ausführungsinterleaving. Ob historische Hostlast, Scheduling oder physischer Cachezustand welchen Anteil an 996/810 ms hatte, lässt sich nachträglich nicht trennen. Kein methodischer Wechsel und keine echte Candidate-Regression belegt. GREEN gilt für den bestehenden gemessenen Vertrag, nicht als Garantie bei beliebiger Hostlast; der Abstand zum Grenzwert ist gering (höchster kanonischer P95 489.014 ms).

## Reproduktion und Evidence

Bestehende Werkzeuge weiterverwendet: `Scripts/r5_b12_performance_investigation.py` (`--mode canonical` exakt drei unveränderte R4-CLI-Aufrufe; `--mode warm` drei Zusatzreihen) und `Scripts/r5_b12_sql_probe.py` (separate Instrumentierung). Nur temporäre Kandidaten/DBs; keine Runtime-Datei instrumentiert oder geändert.

Evidence: `/private/tmp/sammlr-r5-b12/measurements/canonical-{1,2,3}.json`, jeweilige `-context.json`, `warm-{1,2,3}.json`; SQL-Templates ohne Bindwerte, EXPLAIN und Profile in `/private/tmp/sammlr-r5-b12/sql-probe.json`. Ursprüngliche Evidence `/private/tmp/sammlr-r4-v20-performance-final.json`; B1.1 `/private/tmp/sammlr-r5-b11/performance.json` und `performance-repeat.json`. Temporäre Evidence ist lokal und nicht dauerhaft versioniert.

Geprüfter Candidate `/private/tmp/sammlr-r5-b12/candidate`, unveränderter B1.1-Allowlist-Export; Python `/private/tmp/sammlr-r5-b11/venv/bin/python`. Investigation-Tools und neue Berichte bleiben außerhalb der unveränderten Release-Allowlist (2.211 Dateien); keine erneute Assembly oder Release-Freigabe behauptet.

## Validierung und Scope

12 fokussierte Tests bestanden: `tests.test_r4_v20_performance_gate` und `tests.test_r5_release_bootstrap`, ausschließlich im temporären Candidate. Log: `/private/tmp/sammlr-r5-b12/focused.log` (ResourceWarning zu ungeschlossener SQLite-Verbindung; kein Testfehler). B1.1-Nachweis 867/867 bleibt unberührt; keine erneute Full Suite.

Abschließender Hash-/Integritätsnachweis siehe unten. Keine Migration, neuen Indizes, WAL-/busy_timeout-Änderungen oder sonstige Runtime-Änderung. PO-Walkthrough in `CLOSED_BETA_PO_WALKTHROUGH.md`: 16 Gruppen ausschließlich dokumentiert. Kein Navigationsaudit begonnen, kein R6/R7, kein Staging/Commit/Push/Deploy. STOP; R5 bleibt NEXT.

### Abschließender Workspace-Nachweis

Runtime-Quellen und Assets unter `App/` gegenüber B1.2-Beginn unverändert; R4-Runner unverändert. Gewollte Änderungen: zwei Investigation-Skripte, zwei neue Berichte und Fortschreibungen der Release-Inventur/des Candidate-Berichts. Zusätzlich hat sich während des unterbrochenen Auftrags die lokale App-DB sowie `App/__pycache__/profile_sticker.cpython-313.pyc` verändert. Diese beiden Änderungen werden nicht zurückgesetzt.

Kanonische DB SHA-256 vorher:
`c02354fa094071802c73e2f8080e1c5fac920c838adeb326732e92539fadb37a`

Kanonische DB SHA-256 beim Abschluss:
`da5771c463e2967f6a96b729a490db1fce1c76ba8bc533f2724a51fdc43fd157`

**DB-Hash nicht identisch.** Parallel findet laut PO ein manueller Walkthrough der realen App statt; damit ist eine unabhängige Datenänderung plausibel, aber ihre konkrete Herkunft hier nicht bewiesen. Keine behauptete DB-Unverändertheit und keine Zuordnung dieser Änderung zur Performance-Untersuchung. Die gemessenen Candidate-Datenbanken sind getrennte synthetische DBs unter `/private/tmp`; die kanonische DB wurde für diesen Abschluss nur read-only geprüft.

`integrity_check=ok`, `foreign_key_check=0` für die kanonische DB und alle sieben B1.2-Mess-/Probe-DBs. `git diff --check` bestanden; Index leer. Kein Commit, Push oder Deploy. Die Hashabweichung begrenzt den Workspace-Unverändertheitsnachweis, nicht die separat aufgezeichneten R4-Messwerte. R5 bleibt NEXT zur PO-Abnahme.
