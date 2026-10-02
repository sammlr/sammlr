# R4 – V20 Performance Baseline

Stand: 2026-09-06

## Ergebnis

**Closed-Beta-Bewertung: GREEN.** Alle 15 gemessenen Kernoperationen blieben
bei 20 parallelen Requests unter 500 ms P95 und lieferten keine HTTP-Fehler.
R4 setzt seinen Roadmap-Status nicht selbst auf `ACCEPTED / LOCKED`.

## Reproduzierbarer Messvertrag

- Runtime: CPython 3.13.15, Gunicorn 26.0.0, SQLite 3.50.4
- Host: macOS 26.6.2 (25G83)
- Server: ein Gunicorn-Worker, 20 Threads
- Pro Route: ein Warm-up, fünf serielle typische Requests und 20 zeitgleiche
  Requests mit getrennten angemeldeten Nutzersessions
- Bewertung: `GREEN` bei P95 unter 500 ms und null Fehlern; `YELLOW` bei
  500–1.000 ms; `RED` über 1.000 ms oder bei einem Fehler
- Isolation: Datenbank und JSON-Ergebnis ausschließlich unter `/private/tmp`;
  der Runner lehnt andere Zielpfade ab

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  Scripts/r4_v20_performance_gate.py \
  --database /private/tmp/sammlr-r4-v20-performance-final.db \
  --output /private/tmp/sammlr-r4-v20-performance-final.json \
  --python .venv/bin/python \
  --port 18400
```

## V20-Datenbasis

Der Runner kopiert das kontrollierte S00-Referenzfixture, migriert die Kopie auf
Schema V20, leert ausschließlich deren Anwendungsdaten und erzeugt anschließend:

| Entität | Umfang |
| --- | ---: |
| Nutzer | 100 |
| Alben | 10 |
| Katalogplätze je Album | 100 |
| Sticker-Bestandszeilen | 100.000 |
| Trade Requests | 2.000 |
| Notifications | 5.000 |
| Freundschaften | 1.000 |

SHA-256 der vorbereiteten Messdatenbank:
`2dccf24fc4b5a0987eca8c28da327444faa33df42bfc6b3c4bf2c324da197bd2`.
Nach der Messung, einschließlich der fachlich erwarteten Notification-Read-
Mutationen: `d3e04f9ffb07d0e1d252b524506661365086e2d2f5777b86ce536cec328dffce`.
Die Zeilenzahlen blieben vollständig erhalten; `integrity_check=ok` und
`foreign_key_check=0` galten vor und nach der Messung.

## Finale Messwerte

Zeiten in Millisekunden. „Typisch“ ist der Median der fünf seriellen Samples;
P95 und Maximum stammen aus dem parallelen 20-Request-Smoke.

| Operation | Typisch | Parallel P95 | Parallel Max | Fehler | Status |
| --- | ---: | ---: | ---: | ---: | --- |
| Login | 1,058 | 14,137 | 14,490 | 0 | GREEN |
| Home | 2,228 | 74,906 | 75,154 | 0 | GREEN |
| Sammlung | 3,871 | 69,830 | 71,200 | 0 | GREEN |
| Album | 6,820 | 442,550 | 444,082 | 0 | GREEN |
| Stickerwall Missing | 6,704 | 265,752 | 266,195 | 0 | GREEN |
| Partnersuche | 2,935 | 109,637 | 110,252 | 0 | GREEN |
| Trade-Markt | 4,820 | 82,822 | 84,600 | 0 | GREEN |
| Trade Requests | 4,846 | 81,055 | 84,395 | 0 | GREEN |
| Album-Trade-Hub | 3,826 | 306,029 | 306,767 | 0 | GREEN |
| Trade Detail | 6,181 | 140,992 | 144,247 | 0 | GREEN |
| Notification GET-Gate | 1,778 | 39,631 | 39,752 | 0 | GREEN |
| Notification Inbox POST | 4,619 | 190,713 | 246,063 | 0 | GREEN |
| Eigenes Profil | 4,457 | 76,580 | 78,399 | 0 | GREEN |
| Fremdprofil | 4,522 | 75,716 | 77,752 | 0 | GREEN |
| Fremd-Stickerwall | 4,231 | 221,529 | 221,617 | 0 | GREEN |

## Befunde und begrenzte Optimierungen

Der veraltete Runner migrierte explizit nur auf V18, maß ausschließlich P95,
prüfte keinen Query-Plan und keinen Lock-Fall und bildete beim Notification-Pfad
nicht die reale POST-Operation ab. Der neue Runner verwendet V20, getrennte
Server-Lebenszyklen je Route, Median/P95/Maximum/Fehler, kontrollierte Sessions,
Query-Pläne, einen Lock-Smoke sowie Vor-/Nachprüfung der Messdatenbank.

Zwei reproduzierbare Runtime-Engpässe wurden vor Änderungen nachgewiesen:

- Der Album-Trade-Hub führte für 198 Partner wiederholt vollständige
  Einzel-Snapshots aus: serieller Median 142,157 ms; bei 20 parallelen Requests
  20/20 Timeouts über zehn Sekunden. Die Projektion nutzt jetzt die bereits
  vorhandenen kanonischen Batch-Reads für Interaktionsmenge, Matching-State und
  Album-Markt. Finale Werte: 3,826 ms typisch, 306,029 ms P95.
- Die Profilstatistik las zehn Alben einzeln; danach verblieb unter paralleler
  Last SQLite-Read-Thrashing. Die Statistik nutzt nun die bestehende
  `collection_summaries`-Batchprojektion, und eigenes/öffentliches Profil nutzen
  denselben bestehenden Read-Serialisierungsvertrag wie Sammlung und
  Tradeübersicht. Ausgangswerte: 1.494,873/1.538,715 ms P95; final
  76,580/75,716 ms P95.

Vergleichstests sichern für Matching-Rangfolge/-Mengen sowie Profilfortschritt
und physische Menge die exakte Gleichheit zum kanonischen Einzelpfad. Es wurden
keine Business-, Lifecycle-, Reservierungs-, Privacy- oder UI-Verträge geändert.

## Query-Pläne und SQLite

Bei 2.000 `trade_requests` und 5.000 `notifications` zeigen die untersuchten
User-/Status-/Zeit-Abfragen weiterhin Table Scans; die zeitlich sortierten
Abfragen verwenden zusätzlich einen temporären B-Tree. Trotz dieser Pläne
bleiben die realen Trade-Request-Routen bei 81,055 ms P95 und Notification POST
bei 190,713 ms P95. Damit ist für das Closed-Beta-Volumen kein gemessener
Index-Engpass vorhanden. Es wird keine Indexmigration vorgeschlagen.

Die V20-Datenbank blieb bei `journal_mode=delete`; der Runtime-Verbindungswert
für `busy_timeout` beträgt 5.000 ms. Im kontrollierten Probe-Fall mit absichtlich
auf 250 ms reduziertem Timeout blieb ein paralleler Read mit 0,253 ms möglich;
der konkurrierende Write wartete 289,786 ms und endete erwartungsgemäß mit
`database is locked`. Die Daten blieben erhalten. Im realen 20-fachen
Notification-POST-Smoke traten keine Lock- oder HTTP-Fehler auf. Messbar besteht
daher kein Anlass, WAL oder einen anderen `busy_timeout` einzuführen.

## Änderungen

- `Scripts/r4_v20_performance_gate.py`: aktueller isolierter V20-Runner
- `Scripts/s35_performance_baseline.py`: kompatibler Einstieg in den V20-Runner
- `App/performance_wsgi.py`: V20-Harness und korrekte synthetische Kataloge
- `App/services/executable_trade_matches.py`: kanonische Batchprojektion
- `App/services/inventory.py`: physische Menge in der Batch-Zusammenfassung
- `App/services/statistics_projection.py`: Batch-Profilstatistik
- `App/webapp.py`: bestehende SQLite-Read-Serialisierung für Profilprojektionen
- `tests/test_r4_v20_performance_gate.py`: Reproduzierbarkeit, Isolation,
  Gleichheit, Query-/Lock- und Harness-Regressionsschutz
- `docs/CLOSED_BETA_EXECUTION_ROADMAP.md`: R3 `ACCEPTED / LOCKED`, R4 `NEXT`

Keine Migration, keine Schema-/Indexänderung, kein WAL- oder Timeout-Umbau.

## Abschlussprüfungen

- Fokussierte R4-/Inventory-/Matching-/Profil-/R2-/R3-Regressionen:
  130 Tests, `OK`
- Full Suite mit der kanonischen Testing-Konfiguration: 867 Tests; exakt drei
  bekannte scope-fremde Baseline-Fehler (veralteter CEOKlaue-DB-Hash,
  Notification-Pagination-Form-Assertion und V0007-Fixture mit realem V20-
  Stand). Keine neue R4-Regression; diese drei Fehler wurden nicht verändert.
- Safari 26.6.2 Desktop (1.200 px): eigenes Profil, Fremdprofil, `/trades` und
  Album-Trade-Hub geladen; erwartete DOM-Flächen vorhanden, kein horizontaler
  Overflow.
- Safari 26.6.2 bei exakt 390 px: eigenes Profil, Fremdprofil,
  Album-Trade-Hub und Missing-Stickerwall geladen; erwartete DOM-Flächen
  vorhanden, kein horizontaler Overflow.
- `git diff --check`: bestanden.

Die kanonische lokale App-DB hatte unmittelbar vor R4 SHA-256
`cfa951d2cf366aec5fd824c44bd57d8c1d7fb22fab36f86e171fe2fddea923f1`.
Der Abschlusswert ist
`ce5f985b8fbfa10d6864acf8bc320a486c726a254c7b70fba2668161b84ecc95`.
Die Abweichung wurde untersucht: Sämtliche R4-Datensatzerzeugung und Lasttests
waren fail-closed auf `/private/tmp` begrenzt, und der R4-Test bestätigt den
unveränderten kanonischen Hash innerhalb seines Testlaufs. Während der Prüfung
lief parallel der bestehende Development-Server auf Port 8080. Die physische
Neuschreibung der DB-Datei (mtime 01:39:31) fällt zeitlich mit dessen Reload
zusammen; das ist die belastbare Zuordnung, nicht der Nachweis einer einzelnen
SQL-Anweisung. Der logische Abschlusszustand bleibt Schema V20 mit 4 Nutzern,
3 Alben, 2.046
Sticker-Bestandszeilen, 21 Trade Requests und 56 Notifications;
`integrity_check=ok`, `foreign_key_check=0`. Es wurde keine binäre
Rekonstruktion zur künstlichen Hash-Wiederherstellung vorgenommen.
