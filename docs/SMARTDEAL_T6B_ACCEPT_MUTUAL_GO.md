# SD-T6b – Accept, Mutual GO und konkurrierende Requests

Stand: 2026-09-12. Interner Domain-/Persistence-Core auf V21. Basis: geschlossene Product Bible, Algorithm Contract AC18–25/27 und PO-Präzisierung der Frist auf ausschließlich `binding_created_at + 24h`. Keine öffentliche Aktivierung oder physische Lifecycle-Implementierung.

## Einstieg und Transaktionsgrenze

`SmartDealAcceptanceService(connection, catalog_provider, now_provider)` in `App/services/smartdeal_acceptance.py` stellt `accept(request_id, actor_user_id)` und `go(suggestion, actor_user_id)` bereit. Actor-IDs müssen aus einem vertrauenswürdigen serverseitigen Kontext stammen; der interne Service implementiert keine HTTP-Authentifizierung.

Ein gültiger Command übernimmt eine freie SQLite-Verbindung, erwirbt `BEGIN IMMEDIATE` und erfasst danach einmal die injizierbare UTC-Uhr. Dieser unter dem Write-Lock erfasste Zeitpunkt ist der fachliche Prüf-/Annahmezeitpunkt. Lookup, aktuelle Validierung, Status-/Timestamp-/Lifecycle-Übergang und Annahmeevent liegen bis COMMIT in derselben Transaktion. Fehler führen zu vollständigem Rollback. Caller-Transaktionen werden unverändert zurückgewiesen. busy_timeout und WAL bleiben unverändert; SQLITE_BUSY/SQLITE_LOCKED liefern nach Rollback BUSY, andere Fehler propagieren. Keine Retry-Schleife und keine Teil-Commits.

Der bisherige T5a-Service behält seine öffentliche Semantik. Sein unveränderter Anlageablauf wurde als interner `_create_locked`-Kern extrahiert; der öffentliche `create_from_suggestion` besitzt weiterhin seine eigene Transaktion. T6b kann denselben Kern unter seinem bereits erworbenen Lock aufrufen. Es gibt keine zweite Anlageimplementierung und keine Lücke zwischen Opportunity-Lookup und Anlage. Alle bestehenden T5a-Tests bleiben unverändert enthalten.

## Explizites Accept

Nur der gespeicherte Gegenpartner darf explizit annehmen. Initiator, Dritte und nichtkanonische Actor-Werte erhalten UNAUTHORIZED; Legacy erhält NOT_V1, fehlende Requests NOT_FOUND. Declined/cancelled/expired und sonstige terminale Zustände werden nicht angenommen. Ein offener Request mit schon gesetztem accepted_at ist inkonsistent und wird fail-closed abgewiesen.

Vor dem Übergang werden aus der Datenbank rekonstruiert bzw. geprüft:

- vollständige T6a-Identity, eindeutige aktive Opportunity-Instanz, V1/Pending und alleinige Binding-Frist;
- richtige Request-/Trade-Teilnehmer und unveränderliches, ausgeglichenes Paket ab 5↔5;
- vollständige aktive Reservationen beider Seiten, passende Positionsmengen, Geber, Album/Code, Bindungszeit und keine fremden Crosslinks;
- kein vorgetäuschter Versand/Empfang oder bereits abgeschlossener Lifecycle;
- aktuelle Account-/Block-/Tradepool-/Album-/Katalog-Eligibility;
- reale Deckung aller bestehenden Reservations einschließlich eigener zugesagter Stücke und weiterhin physisch fehlender Empfangsbedarf;
- keine fremde gültige Eingangszusage, die denselben Need beansprucht.

Hierzu werden bestehende T5a-Integritätsprüfung, T5b-Materialisierung, T2a-Inputs/-Bindungsprojektion und kanonische Inventory-Snapshots wiederverwendet. Eine verlorene notwendige Kopie, erfüllter Need, Block oder aufgehobene Poolfreigabe liefert STALE ohne Mutation. Fremde gültige Bindungen werden niemals übergangen. Bestandsverlust löst hier keinen T7b-Unfulfillable-Workflow aus.

Eigene vollständige Bindungen sind bei Annahme keine fremde Belegung. Normales freies T4-VALID ist deshalb nicht die Annahmeprüfung: Das schon reservierte Paket wäre dort erwartungsgemäß STALE. Stattdessen wird seine aktuelle Deckung geprüft. Inventory-Snapshots verwenden die vorhandene Availability-Bilanz, keine alternative Mengenformel. Die Prüfung fremder Incoming-Zusagen schließt ausschließlich die konkrete eigene Request-ID aus. Annahme benötigt keinen neuen ausgehenden Quotenslot; ein Gegenpartner mit drei eigenen ausgehenden Anfragen kann weiterhin annehmen.

## Opportunity Lookup, Mutual GO und Dedupe

GO prüft zuerst die vollständige Payload-/Identity-Konsistenz über T4. Innerhalb der Write-Transaktion lädt `_lookup` anschließend alle offenen/angenommenen V1-Requests des Nutzerpaars und deren Positionen in **zwei Batch-Abfragen**. Nutzerpaar grenzt nur den Suchraum ein. Aus sämtlichen gerichteten Album/Code/Mengen-Positionen wird die vollständige kanonische T6a-Identity rekonstruiert und verglichen; weder Dealgröße, Albumliste, Rank noch Digest allein entscheiden.

| Gespeicherter Zustand für exakt dieses Paket | Wirkung von GO |
| --- | --- |
| Kein aktiver Treffer | Normaler T5a-Anlagekern mit frischer T4-Revalidation und Quote |
| Eigener intakter offener Treffer | ALREADY_CREATED; bleibt pending, keine Zustimmung durch eigenen Retry |
| Offener Treffer des Gegenpartners | Atomarer Accept desselben Requests |
| Bereits angenommener konsistenter Treffer | ALREADY_ACCEPTED, bestehende Request-ID, keine weitere Mutation |
| Fälliger offener Treffer | T5b-Expiry, EXPIRED; keine Wiederbelebung oder zweite Anlage in diesem Aufruf |
| Mehrere aktive Treffer derselben vollständigen Identity | Fail-closed; keine willkürliche Zusammenführung |

T6a ordnet die Geberrichtungen unabhängig vom Viewer zu. Deshalb treffen A-GO/B-GO und B-GO/A-GO dieselbe Opportunity. Gleiches Paar/gleiche Größe/gleiche Alben mit einem anderen Piece trifft nicht; der normale T5a-Pfad verweigert bereits gebundene Ressourcen. Ein tatsächlich disjunktes Restpaket kann nach normaler Revalidation einen separaten Request bilden. Rangwechsel verändern keinen Vertragsinhalt; ein Test verschiebt das unveränderte Paket im echten T3b-Plan von Rang 1 auf Rang 2.

Request-ID ist die persistierte Instanz, Opportunity-Identity die vollständige Paketsemantik. Ein terminaler früherer Request verhindert keine spätere neue Instanz. Ein Digest-Kollisionstest bestätigt den vollständigen Inhaltsvergleich. SQLite serialisiert die Instanzsuche und Anlage/Annahme; prozesslokale Locks oder In-Memory-Dedupe sind keine Grundlage. Keine Migration oder neue Hashspalte erforderlich: V21-Positionen, eindeutige Request-/Trade-Zuordnung und BEGIN IMMEDIATE tragen die Invariante für die internen Servicepfade. Beliebige direkte SQL-Manipulationen werden dadurch nicht zu autorisierten Commands.

## Persistenz, Zeit und Bindungen

Erfolgreiches Accept setzt `trade_requests.status='accepted'` und `accepted_at` gemeinsam in einem bedingten UPDATE mit weiterhin `status='open' AND accepted_at IS NULL`. Der bestehende Trade wechselt auf Lifecycle `accepted`, updated_at erhält denselben Annahmezeitpunkt. Keine neue Request-, Positions- oder Reservationszeile. Kein Update der Reservationsmengen/-zeiten, keine Freigabe, keine Inventory-Mutation.

`binding_created_at` bleibt unverändert. `accepted_at` wird genau einmal gesetzt und durch den vorhandenen V21-Trigger geschützt. Retry bestätigt die vorhandene Instanz, ohne Status, Annahmezeit oder Event erneut zu schreiben. Accepted-Integrität umfasst auch den einmaligen Annahmeevent mit passendem Gegenpartner und Zeitpunkt. Die offene Bindungszeit ist niemals der spätere Annahmezeitpunkt.

Die Frist ist absolut: unmittelbar vor `binding_created_at + 24h` zulässig, exakt ab diesem Zeitpunkt nicht mehr zulässig. Ein fälliges noch offenes Accept verwendet T5b `_release_locked` innerhalb derselben Write-Transaktion, beendet als expired und gibt vollständig frei. Es wird nicht allein ein Fehler zurückgegeben, während Reservationen unbegrenzt liegenbleiben. Thread-/Scheduler-Reihenfolge ersetzt diese Prüfung nicht. Nach rechtzeitiger Annahme bleibt der Vertrag auch nach 24h gebunden; T5b-Pending-Expiry/Decline/Withdraw geben ihn nicht frei.

Frische T2a-Reads erkennen beide Supplies und beide Incoming-Needs als gebunden. T2b/T3b verplanen sie nicht erneut. Keine Sonderbehandlung im Optimierer. Accepted-Retry ist ein vorhandener Zustandsfakt und kein neuer Bestands-/Eligibility-Command.

## Lifecycle und Notifications

Der bestehende Smart-Accept-Eventtyp `smart_request_accepted` wird als einmaliger Lifecycle-Fakt wiederverwendet, mit Gegenpartner, Annahmezeit und Quelle `smartdeal_v1`. Der geschlossene Typed-Notification-Katalog enthält keine Accept-Notification; eine solche wird nicht erfunden. Keine neue Notification-Art oder doppelte Notification bei Mutual GO. Fehler beim Event-/Lifecycle-Schreiben rollt den gesamten Übergang zurück.

Shipping-/Receipt-Status, Inventory, Versandkontakt und Chat werden nicht angelegt oder gebucht. Die bisherigen Legacy-Accept-/Notification-/HTTP-Callbacks bleiben unverändert. Das ist kein vollständiger T7a-Lifecycle-Adapter: Die aktuelle Accepted-Integritätsprüfung gilt für angenommene, noch unversandte V1-Verträge dieses internen Core-Standes. Spätere physische Zustände/Retry-Projektionen sind im separat freizugebenden T7a-Vertrag anzubinden. Keine öffentliche Route aktiviert.

## Tests

63 neue Tests ausschließlich auf synthetischen temporären V21-Datenbanken. Keine Nutzer-DB als Fixture; keine vorhandenen Tests verändert oder abgeschwächt.

| Gruppe | Ergebnis / Nachweis |
| --- | --- |
| Idempotenz | 4/4: zweimal Accept, Gegenpartner-GO nach Accept, eigener GO vor Zustimmung, paralleler gleicher Actor |
| Rollback | 7/7: vor Status, während accepted_at-Statement, Lifecycle, Annahmeevent, Mutual-Mitte, Postwrite-Projektion, Commit-Fehler vor erfolgreicher Persistenz |
| Synchronisierte Races | 14/14: 13 benannte Race-Tests plus paralleler Same-Actor-Idempotenztest |
| Neue Tests gesamt | 63/63, 0,829 s |

Race-Nachweise: A/B und B/A GO, Accept/GO in beiden Reihenfolgen, Accept/Decline und Accept/Withdraw in beiden Reihenfolgen, rechtzeitiges Accept vor nachlaufender fälliger Expiry, fälliges Accept vor Expiry, Expiry vor Accept, andere Opportunity sowie vier gleichzeitige GO-Intentionen beider Nutzer. Zwei-Writer-Harness übernimmt T5a Barrier/Events und deterministisch erworbenen ersten Lock; Vier-Writer-Test verwendet eine gemeinsame Barrier und prüft das von jeder zulässigen Lock-Reihenfolge unabhängige Ergebnis: genau ein CREATED, genau ein ACCEPTED und eine Request-ID. Keine sleep-and-hope-Tests.

Nach erneutem DB-Open werden Paketidentität, beide aktiven Bindungsseiten, Status/Annahmezeit, genau ein Event, Integrity und FK geprüft. Rollbacks vergleichen alle Tabellen einschließlich Sequenzen mit der vorherigen vollständigen Snapshot-Wahrheit. Status und accepted_at werden in einem SQL-Statement gesetzt: eine AFTER-Trigger-Fehlerinjektion beweist deren gemeinsamen Rollback.

Pflichtfälle A–AJ sind durch explizites Accept, Spiegel-/Rang-/Multi-Album-/150-Piece-Mutual-GO, unveränderte Inventory-/Positions-/Reservationsdaten, frische Planung nach Ablauf der Pending-Frist, Rollen/Legacy/Terminalgrenzen, manipulierte Mengen/Teilnehmer/Reservationen/Lifecycle, exaktes anderes Piece und Digest-Kollision, fremden Need, aktuellen Bestandsverlust, Block/Pool/Account, volle Quote, Retry/Races und Fehlerinjektionen abgedeckt. Der reine Opportunity-Lookup über mehrere aktive Requests benötigt exakt zwei SQL-Reads. Ein anfänglich importierter TestCase wurde aus dem neuen Modulnamespace entfernt, damit bestehende Tests nicht als neue Tests doppelt gezählt werden.

## Performance

Python 3.13.15, SQLite 3.50.4, macOS 26.6.2 ARM64. Je drei Serien mit zehn unabhängigen Fällen. Fixture, T3b-Payload und T5a-Bindung außerhalb der Messung; kompletter Command von BEGIN bis COMMIT einschließlich Revalidation, Integritätsprüfung und Event innerhalb. Keine parallel laufende Testsuite.

| Fall | Serienmittel ms | Einzelwerte min–max ms | Trace-Statements |
| --- | --- | --- | --- |
| Explizites Accept 5↔5 | 1,287 / 1,264 / 1,267 | 1,180–1,521 | 95 |
| Mutual GO 5↔5 | 1,244 / 1,249 / 1,242 | 1,166–1,351 | 97 |
| Mutual GO 25↔25, zwei Alben | 2,954 / 3,055 / 3,508 | 2,870–4,629 | 121 |
| Mutual GO 150↔150, zwei Alben | 14,441 / 13,811 / 13,893 | 13,300–19,441 | 121 |
| Lookup bei sechs aktiven Requests | 0,131 / 0,111 / 0,113 | 0,107–0,259 | 4 einschließlich BEGIN/COMMIT |

Trace zählt auch SQLite-Triggerwiederholungen. Kein SQL pro Piece; die vollständigen bestehenden Inventory-Snapshots verursachen zusätzliche feste Reads pro beteiligtem Album. Lookup lädt Paketzeilen gebündelt; CPU und Materialisierung wachsen mit gespeicherten Positionen/Kandidaten, nicht mit einer globalen T3b-Suche. Die sechs Lookup-Fixtures sind drei ausgehende Requests pro Seite, keine Quotenaufweichung. Kein Produktions-SLA und kein Nachweis beliebig großer aktiver Requesthistorien.

Reproduktion: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m tests.research.benchmark_smartdeal_acceptance`. Messlog `/private/tmp/sdt6b-benchmark.jsonl`.

## Geänderte Dateien und Grenzen

Exakt sieben Auftragsdateien:

1. Neu: `App/services/smartdeal_acceptance.py`.
2. Geändert: `App/services/smartdeal_requests.py` – Extraktion des transaktionslosen internen Anlagekerns zur Komposition, bestehendes T5a-Verhalten erhalten.
3. Neu: `tests/test_sd_t6b_accept_mutual_go.py`.
4. Neu: `tests/research/benchmark_smartdeal_acceptance.py`.
5. Neu: `docs/SMARTDEAL_T6B_ACCEPT_MUTUAL_GO.md`.
6. Geändert: `docs/SMARTDEAL_TECHNICAL_ROADMAP_V1.md` – minimale Implementierungsnotiz.
7. Geändert: `docs/R5_RELEASE_FILES.json` – drei additive Service-/Test-/Benchmark-Einträge.

Alle bestehenden Tests, Legacy-Services/Accept, T1/T2a/T2b/T3a/T3b einschließlich Performancefix, T6a/T4/T5b, Migrationen, Product Bible, Algorithm Contract, App-DB, UI und Routes bleiben bytegleich zur Auftragsbaseline. Keine Migration notwendig, kein Legacy-Backfill. Keine Dependency-Änderung.

SD-T7a, SD-T7b und SD-T8a nicht begonnen. Kein Versand, Empfang, Versandkontakt, Chat, UI oder sichtbare Route. Kein git add, Commit, Push oder Deploy. Nach Abschluss STOP.


## Abschließender Acceptance- und Release-Nachweis

**SD-T6b umgesetzt: JA. Acceptance: GREEN.** Explizites Accept und Mutual GO implementiert. Vollständige spiegelgleiche Opportunity ist das Matchkriterium; A/A-Doppel-GO bleibt pending, A/B-GO übernimmt denselben Request als accepted. accepted_at einmalig/stabil; binding_created_at und alle bestehenden Positions-/Reservationsfakten erhalten. Beide Supplies und beide Needs bleiben gebunden, physisches Inventory unverändert. Fristprüfung exakt ab binding_created_at+24h mit atomarer T5b-Freigabe. Ein bestehender Smart-Accept-Event, keine neue Notification-Art.

| Prüfung | Finales Ergebnis |
| --- | --- |
| Neue Tests | **63/63** |
| Idempotenz / Rollback / synchronisierte Races | **4/4 / 7/7 / 14/14**; Gruppen überlappen beim parallelen Same-Actor-Test |
| Schutzregression | **704/704**, 11,999 s |
| Vollständige kanonische V21 Release-Suite | **1222/1222**, 22,282 s |
| Failures / Errors / Skips | **0 / 0 / 0** |

1234 Tests entdeckt; unverändert neun historische und drei Baseline-Klassifizierungen außerhalb der kanonischen Release-Kohorte. Baseline 1159 plus ausschließlich 63 neue Tests. Schutzregression enthält alle gesperrten SmartDeal-Vorstufen einschließlich T5a/T5b, Inventory/Availability/Reservations, Privacy/Blocks/Tradepool, SmartMatch, Legacy Requests/Accept, Lifecycle, Notifications/History und R3 Golden Path.

Finaler isolierter Allowlist-Export `/private/tmp/sammlr-sdt6b-final`: 2245 Dateien. Synthetische Fixtures über `Scripts.prepare_release_tests`, unveränderte Repo-`.venv/bin/python`, `PYTHONDONTWRITEBYTECODE=1`. Full-Gate: `python -m Scripts.release_test_gate --cohort release`. Logs: `/private/tmp/sdt6b-new.log`, `/private/tmp/sdt6b-regression.log`, `/private/tmp/sdt6b-full.log`. Runtime, Tests, Benchmark und Allowlist bytegleich mit dem getesteten Export; keine Codeänderungen nach diesem Gate.

Kanonische lokale App-DB nicht migriert oder mutiert. SHA-256 vor und nach der Arbeit identisch:

`265de4e7cd438a8c9f2bb6673c7a020570605eed8c326e98ab4c378d2fa6d522`

Read-only `integrity_check`: **ok**. `foreign_key_check`: **0 Befunde**. `git diff --check`: **bestanden**, zusätzliche Whitespace-Prüfung der neuen Dateien. Auftragsbezogener Hashvergleich gegen `/private/tmp/sdt6b-before.json`: ausschließlich die sieben aufgeführten Dateien neu/geändert; vorbestehender dirty Worktree erhalten. Keine Migration, keine Dependency-/UI-/Routenänderung. Kein git add, Commit, Push oder Deploy. **STOP.**
