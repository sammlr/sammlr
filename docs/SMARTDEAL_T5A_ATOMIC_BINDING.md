# SD-T5a – Atomare SmartDeal-V1-Anlage

Stand: 2026-09-11. Interne Implementierung; keine öffentliche Aktivierung. Produktvertrag und gesperrte Vorstufen bleiben unverändert.

## Write-Vertrag

`App/services/smartdeal_requests.py`: `SmartDealRequestService.create_from_suggestion(suggestion, actor_user_id)` übernimmt eine freie SQLite-Verbindung. Eine vorhandene Caller-Transaktion wird unverändert zurückgewiesen. Der Actor muss eine vertrauenswürdig serverseitig bestimmte Teilnehmer-ID sein; der Service stellt keine HTTP-Authentifizierung bereit.

Nach rein struktureller T4-Payload-Prüfung wird `BEGIN IMMEDIATE` erworben. Erst danach wird der gemeinsame UTC-Zeitpunkt bestimmt. Für jede Neuanlage folgt frische T4-Revalidation innerhalb genau dieser Write-Transaktion. Es gibt keinen zwischenzeitlichen Commit, keine Optimierung, Ersatzstücke oder Paketkorrektur. STALE/INVALID_PAYLOAD schreiben nichts. Die Quote erlaubt höchstens drei zeitlich gültige offene ausgehende V1-Anfragen; Legacy-/manuelle offene Requests zählen nicht mit.

Persistiert werden ein offener `trade_requests`-Datensatz mit `contract_type=smartdeal_v1`, ein offener `trades`-Datensatz, das vollständige validierte Paket in `trade_positions` und aktive `trade_reservations` für beide Geber. Positions- und Reservationsanlage erfolgen jeweils als Bulk-Statement, ohne SQL pro Piece. `binding_created_at` wird einmal gesetzt. Request, Positionen und Reservationen verwenden denselben Zeitpunkt; `accepted_at` bleibt NULL, beide Bestätigungsflags bleiben 0. Physische Inventory-Mengen, Versand, Empfang, Historie und Notifications werden nicht beschrieben.

Das verpflichtende alte `album_id`-Feld enthält das erste kanonische beteiligte Album als technischen Kontext. Die vollständige Multi-Album-Wahrheit liegt ausschließlich in den Positionen. Alte `give_codes`/`get_codes` bleiben leere Arrays: Sie bilden keinen falschen Single-Album-Deal ab; der bestehende Legacy-Accept lehnt dieses leere alte Paket ab. Es wird kein alter SmartMatch-Marker gesetzt. Daraus folgt keine öffentliche V1-Tauglichkeit alter Request-Routen.

## Identität, Supply und Needs

`identity_for_request` rekonstruiert die vollständige T6a-Identity aus Teilnehmern und gerichteten Album/Code/Mengen-Positionen. Verglichen wird die vollständige kanonische Identity, kein Hash allein. Die bestehende eindeutige Request-Zuordnung im Lifecycle und die Positionen reichen dafür aus; weder zusätzliche Identity-Persistenz noch Migration sind nötig. V21 und Migration 0021 bleiben unverändert.

Beide Supplies nutzen dieselbe bestehende Reservationstabelle wie Legacy. Incoming-Needs werden durch die vorhandene T2a-Projektion dieser Positionen und Reservationen gebunden, ohne neue Need-Tabelle. Vor Commit werden das vollständig persistierte Paket, beide Reservationsseiten und die frische T2a-Need-Projektion geprüft. Nach erneutem Read erkennt die unveränderte Pipeline T2a → T2b → T3b die Bindung. Verbleibende zusätzliche physische Kopien bleiben frei, bereits zugesagte Needs jedoch nicht.

Der geschlossene V1-Vertrag/T2a verwendet 24 Stunden; die 48h-Formulierung im Auftrag begründet keine Änderung dieses Vertrags. T5a implementiert keinen Ablauf oder Release. T2a blendet abgelaufene V1-Bindungen bereits lesend aus, während deren gespeicherte Reservationen bis T5b aktiv bleiben können. Deshalb prüft die Neuanlage zusätzlich die vorhandene `InventoryReadService.matching_states`-Availability und überzieht diese gemeinsame gespeicherte Wahrheit nicht. Das ist konservativ: Unfreigegebene alte Holds können eine neue Anlage blockieren. Zusätzliche freie Kopien bleiben nutzbar. Dasselbe abgelaufene offene Paket liefert STALE und wird nicht still ersetzt oder verlängert.

## Idempotenz und Transaktionen

Unter dem erworbenen Write-Lock wird nach derselben vollständigen Identity in offenen V1-Requests beider Richtungen gesucht. Ein intakter, zeitlich gültiger eigener Request liefert `ALREADY_CREATED` mit derselben ID, ohne Schreiben oder Zeitverlängerung. Die Gegenrichtung liefert `EXISTING_COUNTERPART_REQUEST`, ausdrücklich ohne Accept oder Mutual GO. Das meldet einen vorhandenen Bindungsfakt, keine neue Verfügbarkeitszusage; eigene bestehende Reservationen würden eine Neuanlagenprüfung erwartungsgemäß blockieren. Mehrere gleiche offene Bindungen oder inkonsistente gespeicherte Pakete werden fail-closed zurückgewiesen. Ein später terminaler und freigegebener Vorgang verhindert nicht dauerhaft eine neue Paketinstanz.

`BEGIN IMMEDIATE` serialisiert konkurrierende SQLite-Writer vor Revalidation und Quote. Auch der vorhandene Legacy-Accept verwendet diese Grenze und dieselbe Availability. Kein bloßes ungeschütztes SELECT-Dedupe. Die Garantie gilt für die geprüften Service-/Transaktionspfade, nicht beliebige direkte SQL-Manipulationen. busy_timeout und WAL werden nicht verändert. SQLITE_BUSY/SQLITE_LOCKED liefern nach Rollback `BUSY`; sonstige Fehler werden nach Rollback weitergereicht. Keine unbeschränkte Retry-Schleife. Commit-Fehlerinjektion prüft einen Fehler vor erfolgreichem Commit.

## Testnachweis

40 neue Tests in `tests/test_sd_t5a_atomic_binding.py` decken A–AA sowie Quote, Gegenrichtung, Restkopien, abgelaufene gespeicherte Holds, verschachtelte Transaktionen und Lock-Erschöpfung ab. Synthetische temporäre V21-Datenbanken; keine Nutzer-DB als Fixture.

- Rollback: 8/8. Request-Insert, nach Request-Insert, erste Reservationsseite, zweite Reservationsseite, nach Bindung bei Need-Prüfung, Binding-Timestamp, reale T2a-Postwrite-Projektion und Commit-Fehler. Nach erneutem DB-Open sind sämtliche Tabellen einschließlich Sequenzständen unverändert; Integrity/FK werden geprüft.
- Synchronisierte Rennen: 7/7. Identischer Payload, konkurrierendes outgoing Piece, konkurrierender incoming Need trotz ausreichender Geberkopien, Legacy zuerst, V1 zuerst, Gegenpartner und letzter dritter Quotenslot. Zwei echte SQLite-Verbindungen, Barrier/Events und deterministisch zuerst erworbener Write-Lock; keine Sleep-and-hope-Tests.
- Neue Tests: 40/40 GREEN (lokal 0,460 s).
- Schutzregression im isolierten Release-Export: 581/581 GREEN (10,416 s), einschließlich aller gesperrten SmartDeal-Vorstufen, Inventory/Availability/Reservations, Privacy/Blocks/Tradepool, Legacy/SmartMatch, Lifecycle, Notifications und R3 Golden Path.

Reproduzierbare Release-Prüfung: `python3 -B -m Scripts.assemble_release --destination /private/tmp/sammlr-sdt5a-final`, anschließend im Export mit der Repo-Testvenv und `PYTHONDONTWRITEBYTECODE=1` zuerst `python -m Scripts.prepare_release_tests`, dann `python -m Scripts.release_test_gate --cohort release`. Export: 2238 allowlist-definierte Dateien. Vollständiges Gate-Ergebnis siehe Abschlussnachweis unten.

## Performance

`tests/research/benchmark_smartdeal_binding.py`; Python 3.13.15, SQLite 3.50.4, macOS 26.6.2 ARM64. Je Größe drei Serien mit zehn unabhängigen Anlagen auf frischen synthetischen V21-Fixtures. Aufbau außerhalb, vollständige Anlage einschließlich BEGIN, Revalidation, Postwrite-Prüfung und COMMIT innerhalb der Messung. Keine parallel laufende Testsuite.

| Paket je Seite | Alben | Serienmittel in ms | Einzelwerte min–max in ms | SQLite-Trace-Statements |
| --- | --- | --- | --- | --- |
| 5 | 1 | 0,892 / 0,849 / 0,883 | 0,820–1,028 | 59 |
| 25 | 2 | 1,588 / 1,583 / 1,611 | 1,535–1,738 | 62 |
| 150 | 2 | 6,156 / 6,349 / 6,797 | 6,013–12,754 | 62 |

Trace-Zahlen enthalten von SQLite wegen Triggern wiederholte Statements. Keine N+1-pro-Piece-Reads/Writes; Availability liest pro Album. Der Lookup bereits vorhandener offener Requests rekonstruiert deren Pakete je Request und ist von deren Anzahl abhängig. Gemessen ist die erste Anlage, kein Produktions-SLA und keine Aussage über unbegrenzt angesammelte abgelaufene Requests oder hohe Writer-Contention.

## Umfang und Abschlussnachweis

Exakt diese sechs Dateien gehören zu SD-T5a:

1. `App/services/smartdeal_requests.py` – neu.
2. `tests/test_sd_t5a_atomic_binding.py` – neu.
3. `tests/research/benchmark_smartdeal_binding.py` – neu.
4. `docs/SMARTDEAL_T5A_ATOMIC_BINDING.md` – neu.
5. `docs/SMARTDEAL_TECHNICAL_ROADMAP_V1.md` – minimale Implementierungsnotiz.
6. `docs/R5_RELEASE_FILES.json` – drei additive Runtime-/Test-/Benchmark-Einträge.

Keine bestehende Runtime, Migration, Product Bible oder Algorithm-Contract-Datei wurde für T5a geändert. Der schon vorher stark veränderte Worktree wird über den vor Taskbeginn erstellten Datei-Hash-Snapshot abgegrenzt, nicht als T5a-Gesamtdiff ausgegeben.

Kanonische lokale `App/Database/sammlr.db` bleibt unmigriert auf ihrer bestehenden Baseline. SHA-256 vor und nach der Arbeit identisch:

`265de4e7cd438a8c9f2bb6673c7a020570605eed8c326e98ab4c378d2fa6d522`

Read-only `integrity_check`: `ok`; `foreign_key_check`: keine Zeilen.

SD-T5b, SD-T6b und SD-T7a nicht begonnen. Kein Accept, Mutual GO, Expiry-/48h-Release, Withdraw-/Decline-Release, Versand, Empfang, Kontakt, Chat, Notification, UI oder sichtbare Route. Keine öffentliche Aktivierung. Kein git add, Commit, Push oder Deploy. Nach Abschluss STOP.

Finales Release-Gate: **1099/1099 GREEN**, 20,591 s, 0 Failures, 0 Errors, 0 Skips. Discovery 1111; unverändert 9 historische und 3 Baseline-Fälle außerhalb der kanonischen Release-Kohorte. Die Baseline steigt ausschließlich um die 40 neuen T5a-Tests von 1059 auf 1099. **SD-T5a umgesetzt: JA; Acceptance: GREEN.** `git diff --check` ohne Befund; zusätzliche Whitespace-Prüfung der neuen Dateien ohne Befund.
