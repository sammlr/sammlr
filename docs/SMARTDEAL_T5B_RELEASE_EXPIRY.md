# SD-T5b – Fristen, Rückzug und vollständige Freigaben

Stand: 2026-09-12. Grundlage: ursprünglicher SD-T5b-Auftrag, ersetzt hinsichtlich der Frist durch die ausdrückliche PO-Klärung vom 2026-09-12. Keine neue Produktentscheidung, kein Accept oder öffentlicher SmartDeal-Cutover.

## Korrigierter Arbeitsauftrag und Frist

Verbindlich ist **`expires_at = binding_created_at + 24 Stunden` als absolute Zeitspanne**. `now < expires_at` ist zeitlich gültig; bei `now >= expires_at` ist die unbeantwortete Bindung abgelaufen. Der PO hat die Anforderung „Ende des übernächsten Kalendertags“ zurückgezogen. Kalender-Tagesgrenzen, lokale Mitternacht, Kalender-Zeitzonen und besondere Monats-/Jahreswechselregeln entfallen. Andere Anforderungen des ursprünglichen Auftrags bleiben bestehen.

Die zentrale reine Domainfunktion `services.smartdeal_expiry.expires_at` normalisiert einen gespeicherten ISO-Zeitstempel oder datetime auf UTC und addiert exakt 86400 Sekunden. Naive bestehende SQLite-Zeitstempel werden entsprechend der vorhandenen App-Konvention als UTC interpretiert. Explizite Offsets bleiben als absolute Zeit erhalten. Keine Europe/Berlin-Abhängigkeit der Runtime, keine DST-Kalenderarithmetik. Der DST-Test belegt lediglich, dass auch ein datetime mit DST-Zone dieselben 86400 Sekunden ergibt.

Bible §19 bleibt bei 24h; die historische Formulierung `created_at + 24h` in AC23 wird für diesen Auftrag durch die ausdrückliche PO-Festlegung der alleinigen Basis `binding_created_at` präzisiert. Die Produktdokumente werden nicht still umgeschrieben. T5a schreibt beide Zeiten weiterhin gemeinsam. Ein abweichendes `created_at` darf die Frist, Retry-Gültigkeit oder Quote nicht bestimmen. T2a und T5a verwenden deshalb jetzt dieselbe reine Fristfunktion.

## Domain-API und atomarer Übergang

`SmartDealReleaseService(connection, now_provider=...)` bietet interne Commands:

- `decline(request_id, actor_user_id)`: ausschließlich der Empfänger.
- `withdraw(request_id, actor_user_id)`: ausschließlich der Initiator.
- `expire(request_id)`: vertrauenswürdiger Maintenance-Aufruf ohne Nutzeraktion.
- `sweep()`: reproduzierbarer zentraler Durchlauf über alle fälligen offenen, noch nicht angenommenen V1-Requests.

Der Aufrufer liefert bei Nutzeraktionen den vertrauenswürdig serverseitig bestimmten Actor. Keine öffentliche Route oder Authentifizierung wird hier erfunden. Positive kanonische Request-IDs und Actor-Typen werden geprüft. Legacy wird mit `NOT_V1` ausgeschlossen. `accepted_at != NULL` oder Status `accepted` liefert `NOT_PENDING`, ohne Freigabe; ein inkonsistentes open+accepted_at wird auch vom Planning-Reader nicht als gewöhnliche offene Bindung ausgegeben.

Jeder öffentliche Service-Command übernimmt ausschließlich eine freie Verbindung: `BEGIN IMMEDIATE`, Uhr einmal erfassen, aktuellen Request und Zuordnungen lesen, Rolle/Vertrag/Pending/Frist prüfen, Status bedingt ändern, alle zugeordneten Reservationen freigeben, Lifecycle und Need-Projektion prüfen, gegebenenfalls vorhandene Decline-Notification erzeugen, COMMIT. Jeder Fehler rollt vollständig zurück. Eine bestehende Caller-Transaktion wird unverändert zurückgewiesen. Keine Validierung außerhalb einer später getrennten Write-Transaktion.

Der vorhandene `TradeReservationService.release` bleibt die gemeinsame Reservations-Schreiboperation. Ein optionaler `released_at`-Parameter ermöglicht den injizierten gemeinsamen Freigabezeitpunkt; bei Legacy-Aufrufen ohne diesen Parameter bleiben CURRENT_TIMESTAMP und bisheriges Verhalten erhalten. Es gibt keine parallele Reservations- oder Need-Tabelle und keine physische Mengenbuchung.

## Persistenz, vollständige Freigabe und Nachvollziehbarkeit

| Ursache | Requeststatus / Lifecycle | Persistierte release_reason |
| --- | --- | --- |
| Decline vor Frist | declined / declined | declined |
| Withdraw vor Frist | cancelled / cancelled | withdrawn |
| Frist erreicht | expired / expired | expired |
| bestehender Block-Cancel vor Frist | cancelled / cancelled | blocked |

Diese Statuswerte sind bereits durch Schema 0011 erlaubt. Der technische Status `cancelled` repräsentiert Rückzug; die vorhandene freie `release_reason`-Spalte erhält die Ursache verlustfrei. **Keine Migration erforderlich**, V21 und sämtliche UP/DOWN-Dateien unverändert.

Nur aktive Reservationen genau des zugeordneten Lifecycle-Trades werden auf `released` gesetzt, mit gemeinsamem `released_at` und Ursache. Request, Trade, sämtliche eingefrorenen Positionen sowie `binding_created_at` bleiben historisch erhalten; `accepted_at` bleibt NULL. Keine Deletes und keine quantity-Änderung. Die bestehende T2a-Projektion erkennt den terminalen Request und die freigegebenen Reservationen, sodass beide Incoming-Zusagen entfallen. Was danach tatsächlich frei ist, entscheiden unveränderte Mengen-/Need-Regeln: fremde Bindungen bleiben wirksam, inzwischen physisch erfüllte Needs bleiben erfüllt.

Vor Freigabe werden Request-/Trade-Teilnehmer, vollständige kanonische Paketidentität, alle Positions-/Reservationszuordnungen und deren Mengen/Geber/Album/Code sowie fehlender Versand/Empfang geprüft. Die Prüfung erfasst auch fehlerhaft kreuzverknüpfte Reservationen über beide Zuordnungsrichtungen. Fehlende, fremde oder teilweise freigegebene Bindungen führen zum Rollback. Die Zuordnung nutzt vorhandene Trade-/Positionsindizes; keine Tabelle aller Reservationen wird pro Request gescannt. Nach Freigabe wird die requestlokale T2a-Projektion für beide Beteiligten geprüft, ohne aktuelle Eligibility oder freie Ressourcen anderer Requests als Voraussetzung für einen Release zu verlangen.

## Idempotenz, Fristablauf und Konkurrenz

Ein sauber beendeter Request liefert bei Wiederholung `ALREADY_RELEASED` samt bestehendem Status. Kein neuer Timestamp, keine weitere Notification, kein Wechsel eines bereits gewonnenen Terminalgrunds. Ein teilweise terminaler inkonsistenter Datensatz wird nicht als erfolgreicher No-op verdeckt. Eine berechtigte Nutzeraktion nach der Frist beendet noch offene Daten als `expired`; eine unberechtigte Aktion verändert auch nach Fristablauf nichts.

SQLite `BEGIN IMMEDIATE` serialisiert konkurrierende Releases und T5a-Neuanlagen. Vor dem Release-COMMIT kann keine konkurrierende Anlage die Ressourcen übernehmen; danach kann ein neuer Request mit derselben Paketidentität entstehen. Accepted wird unter demselben Lock ausgeschlossen; der bedingte Statuswechsel verlangt weiterhin `status='open' AND accepted_at IS NULL`. Zwei Tests simulieren nur die zukünftige bedingte Accept-Schreibgrenze: committed accepted schützt vor Release; committed terminal lässt das spätere bedingte Accept-UPDATE null Zeilen treffen. Das ist kein implementierter Accept und kein vollständiger T6b-Nachweis. T6b muss zusätzlich dieselbe Frist und sämtliche eigenen Annahmebedingungen prüfen.

WAL und busy_timeout unverändert. Einzelcommands melden nach Lock-Erschöpfung `BUSY`; beim Sweep propagiert der SQLite-Fehler nach Rollback an den Maintenance-Aufrufer. Keine unbeschränkte Retry-Schleife. Der interne `_release_locked`-Adapter wird ausschließlich unter bereits erworbenem BEGIN IMMEDIATE verwendet und übernimmt keinen Caller-Commit.

## Sweep, Read-Vertrag und Block-Integration

`sweep()` ist der zentrale explizite interne Maintenance-Einstieg; keine Cron-/Deployment-Infrastruktur und keine versteckten GET-/Planning-Schreiboperationen. Der gesamte Pass verwendet eine Uhr und eine Transaktion. Er betrachtet ausschließlich offene V1-Zeilen mit `accepted_at IS NULL`; erst fällige Zeilen werden beendet. Wiederholung findet keine bereits beendeten Requests. Ein Fehler in einem fälligen Request rollt den gesamten Pass zurück und wird gemeldet, statt eine teilweise erfolgreiche Liste vorzutäuschen.

T2a projiziert zeitlich abgelaufene V1-Bindungen bereits read-only als unwirksam. Der Sweep entfernt zusätzlich deren gespeicherte aktive Reservationswirkung und beendet den offenen Request. Bis zum expliziten Sweep schützt T5a weiterhin die tatsächliche gemeinsame Inventory-/Reservationswahrheit konservativ. Interne Aufrufer können vor einer neuen Anlage den Sweep ausführen und anschließend T5a seine eigene atomare Revalidation durchführen lassen. Keine garantierte Hintergrund-Ausführung wird behauptet; der spätere öffentliche Command-/Maintenance-Adapter muss diesen zentralen Einstieg aufrufen. Eine öffentliche Aktivierung erfolgt in T5b nicht.

Der bestehende `CommunityService.block` ist bereits ein atomarer Write-Pfad. Für V21 werden betroffene offene, nicht angenommene V1-Requests nun innerhalb dieser selben Transaktion vollständig freigegeben, bevor der unveränderte Legacy-Cancel ausgeführt wird. Bei fehlendem V21-Vertragsfeld bleibt der alte Pfad erhalten. Angenommene V1-Requests werden nicht pauschal gecancelt. Ein Fehler der Freigabe rollt auch den neuen Block zurück. Keine neue Block-Route, keine Bestandsverlust-/Unfulfillable-Auswahl aus T7b.

## Notifications

Decline verwendet die vorhandene `TypedNotificationService.notify_request_declined`-Semantik innerhalb der Release-Transaktion: genau eine deduplizierte `trade_request_declined`-Notification an den Initiator mit Requestreferenz. Fehler dieser Erzeugung rollt Status und beide Bindungsseiten zurück. Withdraw, Expiry und Block erfinden keine neue Notification-Art. Kein Notificationversand über externe Tools; keine Erweiterung des Katalogs.

## Tests und Integration

60 neue Tests, ausschließlich synthetische temporäre V21-Datenbanken. Die bestehenden Tests wurden nicht geändert oder abgeschwächt.

| Nachweis | Ergebnis / Umfang |
| --- | --- |
| Dedizierte Fristtests | 11/11: sieben reine Domain-Tests plus unmittelbar vor/exakt/nach Ablauf und persistierter Reload mit absichtlich abweichendem created_at |
| Rollbacktests | 9/9: vor Status, nach Status/vor Supply, zweite Supply-Seite, Lifecycle, Need-Projektion, Notification, Commit-Fehler, zweiter Sweep-Request, Block-Transaktion |
| Synchronisierte Race-Tests | 7/7: Decline/Withdraw, Expiry/Withdraw, zwei Expiries, Release vor Neuanlage, Neuanlage vor Release, accepted-Fakt vor Release, terminal-Fakt vor bedingtem Accept-Probe |
| Neue T5b-Tests | 60/60 GREEN, final 0,646 s |

Race-Harness aus T5a: zwei echte SQLite-Verbindungen, Barrier/Events und deterministisch zuerst erworbener Write-Lock; keine sleep-and-hope-Tests. Nach Rollbacks werden alle Tabellen einschließlich Sequenzen über eine neue DB-Verbindung exakt verglichen; Integrity/FK werden geprüft. Die Fehler beim ersten Fixture-Aufbau wurden in neuen Tests korrigiert, ohne bestehende Expectations anzupassen.

A–M: vollständiger Zyklus für Decline, Withdraw, Expiry und Multi-Album: frei → T5a-gebunden → T5b-frei; beide Supplies, beide Needs, unverändertes physisches Inventory, erhaltene Paketidentität/Timestamps, frischer T2a-State und erneut ausführbarer T2b/T3b-Plan. Erneute Anlage derselben Opportunity erhält eine neue Request-ID. Weitere Tests: 150↔150, Quote nach Release, beide unerlaubten Rollen, Legacy, accepted/open+accepted_at, terminaler Retry, fremde Bindung, erfüllter Need, manipulierte Owner-/Crosslinks, fehlende Reservation, vorgetäuschter Versand, partielle Terminaldaten, Uhr vor Bindung, Busy und Caller-Transaktion. Die durch PO ersetzten Kalenderfälle N–U werden durch die oben genannten absoluten Fristtests abgedeckt. V–AJ werden durch Rollen-/Negativ-, Rollback- und Race-Tests abgedeckt.

## Performance des finalen Codes

Python 3.13.15, SQLite 3.50.4, macOS 26.6.2 ARM64. Drei Serien; je zehn frische einzelne Freigaben oder fünf frische Sweeps über je 30 tatsächlich via T5a angelegte fällige 5↔5-Requests. Fixture-/T5a-Aufbau außerhalb der Messung; kompletter Release von BEGIN bis COMMIT einschließlich Zuordnungs- und Projektionsprüfung innerhalb. Kein parallel laufender Testprozess.

| Freigabe | Serienmittel ms | Einzelwerte min–max ms | SQLite-Trace-Statements |
| --- | --- | --- | --- |
| 5↔5 | 0,555 / 0,537 / 0,532 | 0,499–0,625 | 24 |
| 25↔25, zwei Alben | 1,067 / 1,093 / 1,022 | 0,973–1,410 | 24 |
| 150↔150, zwei Alben | 4,068 / 3,850 / 3,836 | 3,663–4,752 | 24 |
| Sweep: 30 × 5↔5 | 5,792 / 5,780 / 5,819 | 5,533–6,147 | 663 |

Trace enthält SQLite-Triggerwiederholungen. Einzelmessung verwendet Withdraw; Decline enthält zusätzlich die vorhandene Notification-Erzeugung. Keine N+1-pro-Piece-Reads/Writes, eine Bulk-Freigabe je Request. Der Sweep verarbeitet Requests einzeln innerhalb einer gemeinsamen Transaktion; Anzahl der Statements wächst linear mit fälligen Requests, nicht mit Pieces. Requestlokale Materialisierung und Projektion verwenden bestehende Indizes; keine erneute globale Optimierung. Große Sweeps können entsprechend länger einen Write-Lock halten; kein Produktions-SLA oder unbegrenzter Lastnachweis.

Reproduktion: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m tests.research.benchmark_smartdeal_release`. Messlog: `/private/tmp/sdt5b-benchmark-final.jsonl`.

## Änderungen und Schutzumfang

Exakt elf Auftragsdateien:

1. Neu: `App/services/smartdeal_expiry.py` – reine Fristfunktion.
2. Neu: `App/services/smartdeal_release.py` – atomare Commands und Sweep.
3. Geändert: `App/services/smartdeal_planning.py` – gemeinsame Binding-Frist, open+accepted_at fail-closed, optional requestlokaler Readfilter für Release-Prüfung.
4. Geändert: `App/services/smartdeal_requests.py` – alleinige Binding-Frist für Gültigkeit und Quote; gleiche atomare Anlage und alle bisherigen T5a-Tests erhalten.
5. Geändert: `App/services/trade_reservations.py` – optional injizierter Freigabezeitpunkt, Legacy-Default unverändert.
6. Geändert: `App/services/community.py` – V1-Release im bestehenden Block-Write, Legacy-/Pre-V21-Pfad erhalten.
7. Neu: `tests/test_sd_t5b_release_expiry.py` – 60 Tests.
8. Neu: `tests/research/benchmark_smartdeal_release.py` – synthetische Messungen.
9. Neu: `docs/SMARTDEAL_T5B_RELEASE_EXPIRY.md` – dieser Bericht inklusive korrigiertem Auftrag.
10. Geändert: `docs/SMARTDEAL_TECHNICAL_ROADMAP_V1.md` – minimale Implementierungsnotiz.
11. Geändert: `docs/R5_RELEASE_FILES.json` – vier additive Runtime-/Test-/Benchmark-Einträge.

T1/T2b/T3a/T3b inklusive 3b.1/T6a/T4, sämtliche bestehenden Tests, alle Migrationen, Product Bible, Algorithm Contract, UI und Routes bleiben bytegleich zur Auftragsbaseline. Die oben offen ausgewiesenen T2a/T5a-Anpassungen sind notwendige Integration der präzisierten Frist und Freigabe; keine Optimierungs- oder Legacy-Produktregel geändert.

SD-T6b, SD-T7a und SD-T7b nicht begonnen. Kein Accept, Mutual GO, Versand, Empfang, Versandkontakt, Chat, UI oder sichtbare Route. Kein git add, Commit, Push oder Deploy. Nach Abschluss STOP.


## Abschließender Acceptance- und Release-Nachweis

**SD-T5b umgesetzt: JA. Acceptance: GREEN.** Decline, Withdraw und Expiry implementiert; beide Supplies und beide Needs vollständig freigegeben, jeweils unter Berücksichtigung weiterhin gültiger fremder Bindungen. Historische binding_created_at-Werte erhalten; accepted_at bleibt NULL; physisches Inventory unverändert. T2a und T2b/T3b weisen frei → gebunden → frei nach.

- Neue Tests **60/60**, darin dedizierte Fristtests **11/11**, Rollbacktests **9/9**, synchronisierte Race-Tests **7/7**.
- Finale Schutzregression **641/641**, 11,155 s. Enthalten: alle gesperrten SmartDeal-Vorstufen inklusive T5a, Inventory, Availability, Reservations, Privacy/Blocks/Tradepool, bestehendes SmartMatch, Legacy Requests, Lifecycle, Notifications/History und R3 Golden Path.
- Finale kanonische V21 Full Release Suite **1159/1159**, 21,148 s; **0 Failures, 0 Errors, 0 Skips**. 1171 entdeckt; unverändert neun historische und drei Baseline-Klassifizierungen außerhalb der Release-Kohorte. Baseline 1099 plus ausschließlich 60 neue Tests.

Finaler isolierter Allowlist-Export: `/private/tmp/sammlr-sdt5b-verified`, 2242 Dateien. Synthetische Fixtures über `Scripts.prepare_release_tests`; keine Nutzer-DB als Fixture. Unveränderte Repo-`.venv/bin/python`; `PYTHONDONTWRITEBYTECODE=1`. Full-Gate: `python -m Scripts.release_test_gate --cohort release`. Logs: `/private/tmp/sdt5b-new.log`, `/private/tmp/sdt5b-regression-final.log`, `/private/tmp/sdt5b-full-final.log`. Runtime, Tests, Benchmark und Allowlist werden bytegleich zum final getesteten Export geprüft. Keine weiteren Codeänderungen nach diesem Gate.

Kanonische lokale App-DB bleibt auf ihrer bisherigen V20-Baseline, nicht migriert. SHA-256 vor und nach der Arbeit identisch:

`265de4e7cd438a8c9f2bb6673c7a020570605eed8c326e98ab4c378d2fa6d522`

Read-only `integrity_check`: **ok**. `foreign_key_check`: **0 Befunde**. `git diff --check`: **bestanden**, zusätzlich Whitespace-Prüfung der neuen Auftragsdateien. Auftragsbezogener Dateihashvergleich gegen `/private/tmp/sdt5b-before.json` grenzt die elf oben aufgeführten Dateien vom unverändert erhaltenen vorbestehenden dirty Worktree ab. Keine Schema-/DB-/Dependency-/UI-/Routenänderung; kein git add, Commit, Push oder Deploy. **STOP.**
