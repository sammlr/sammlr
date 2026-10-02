# SmartDeal Core Gate Fix CG-1

Stand 2026-09-12. Acceptance **GREEN**. Grundlage ist der unveränderte [Core Gate Audit](SMARTDEAL_CORE_GATE_AUDIT.md). O1, O2 und Y1 geschlossen; Y2 (integrierte Gesamtlast vor Beta) bleibt. Keine Migration, keine Umsetzung T7a/T7b/T8a, keine neue öffentliche Route oder UI.

## Vorprüfung und Mutationsinventar

Product Bible, Algorithm Contract, Roadmap und T5a/T5b/T6b-Nachweise bleiben maßgeblich. Alle vier Auditfindings wurden zurückverfolgt: O1 auf die tatsächlichen Webhandler und ihre Reservations-/Lifecycle-Aufrufe, O2 auf den zuvor ausschließlich internen Sweep, Y1 auf die vorhandenen Pipelinefixtures ohne entsprechende Handlerintegration, Y2 auf reine Domainbenchmarks ohne integrierten Lastnachweis.

| Handler / Pfad | Vorher | CG-1 |
| --- | --- | --- |
| `accept_trade_request`, `/trade/<id>/accept` | Legacy-Accept, einschließlich schemaabhängigem Fallback | V1 ausschließlich `SmartDealAcceptanceService.accept`; Legacy unverändert |
| `decline_trade_request`, `/trade/<id>/decline` | Status-only-Decline konnte aktive V1-Reservationen verwaisen lassen | V1 ausschließlich T5b `decline`, vollständige atomare Freigabe |
| `cancel_trade`, `/trades/<id>/cancel` | Reiner Redirect ohne Mutation | V1-Initiator über T5b `withdraw`; Legacy-Redirect erhalten |
| `confirm_trade_shipping` | Generischer Shipping-Service ohne abgenommenen V1-Adapter | V1 fail closed vor Serviceaufruf |
| `confirm_trade_receipt` | Generischer Receipt mit Single-Album-Trophäencallback | V1 fail closed vor Reads/Callbacks/Buchung |
| `confirm_trade_done` → `complete_trade_if_ready` → `complete_trade` | Zwei Flags konnten V1 ohne Shipping als completed freigeben; leere Legacy-Codelisten statt Positionsbuchung | V1 fail closed vor Flags, Freigabe und Completion |
| `fail_trade_done` | Generische Accepted-Terminalisierung/Freigabe | V1 fail closed |
| `report_trade_problem`, `close_trade_with_problem`, `resolve_trade_problem` | Generische Problem-/Receipt-/Terminalpfade, V1-Vertrag nicht abgenommen | V1 fail closed vor Mutationen und Trophäencallbacks |
| Plurale `accept_trade`, `decline_trade`, `confirm_trade` | Nur Redirects, keine Mutation | Unverändert, kein gefährlicher zweiter Schreibpfad |
| `CommunityService.block` | Seit T5b V1-aware, vollständiger Release im bestehenden Block-TX | Unverändert, vorhandene Schutztests erneut enthalten |
| Legacy Create / SmartMatch Create | Erzeugen ausdrücklich alte Verträge mit bisheriger Semantik | Unverändert; kein öffentlicher V1-Create hinzugefügt |
| SmartMatch inspect/expire/obsolete | Alter Smart-Marker-/48h-Vertrag | Unverändert; reguläre V1-Zeilen tragen diesen Marker nicht |
| Ratings | Bestehender Erfolgs-/Teilnehmerguard, kein Request-/Inventory-Terminalisierungspfad | Unverändert, keine V1-Erfolgsvortäuschung durch gesperrten Confirm |
| Account-Lifecycle | Bestehende aktive Trade-/Reservationsguards | Unverändert, kein neuer automatischer V1-Terminalpfad |

Der neue Adapter `services.smartdeal_runtime.dispatch_request` klassifiziert über den bestehenden `request_contract_type`: fehlende Spalte bedeutet Legacy; explizit unbekannter Wert wirft einen Fehler. Keine Contract-Uminterpretation, keine Freigabelogik im Webhandler. V1-Actor stammt aus `current_user_id()`, Teilnehmerschaft und jeweilige Rolle werden geprüft. Domainservice bleibt für Transaktion, Uhr, Frist und Status verantwortlich. Erfolgreiche V1-Aktionen leiten zur bestehenden Detailadresse; nicht freigegebene Lifecycle-Aktionen liefern 409, fremde Actor 403. Fehler geben keine internen Details aus. Legacy nimmt unverändert den vorhandenen Handlerpfad.

## Operativer Expiry-Anschluss

`services.smartdeal_runtime.cleanup` ruft den bestehenden atomaren T5b-Sweep auf; Pre-V21 ist ein expliziter No-op. Aufruf ausschließlich an relevanten Punkten:

- Neuer **interner** kanonischer Runtimeeinstieg `discover`: Cleanup → frischer T2a-Batch → T2b → T3b. Keine neue öffentliche Discoveryroute.
- Bestehendes `webapp.smart_trade_calculation`: Cleanup vor Eligibility-/Inventory-/Matchingprojektion. Beide bestehenden Aufrufer verwenden diesen Punkt.
- Bestehende `trades_overview` und `trade_detail`: Cleanup vor Inbox-/Detailprojektion, damit tote aktive Reservationen auch bei diesem Nutzerweg nicht unbegrenzt verbleiben.

Die reinen T2a/T2b/T3b-Services bleiben unverändert read-only. Direkte fachliche Projektionen, etwa T4 innerhalb einer bestehenden Write-TX, führen keinen versteckten Sweep aus. Accept braucht keinen globalen Vorsweep: T6b prüft unabhängig exakt `binding_created_at + 24h` und gibt den fälligen eigenen Pending-Request innerhalb seiner TX frei.

Lazy bedeutet: Persistente Freigabe beim nächsten relevanten Zugriff, kein zeitgesteuerter Commit exakt zum Fristzeitpunkt ohne Traffic. Fachliche Nichtannahmbarkeit gilt trotzdem exakt ab 24h. Der Sweep bearbeitet nur offene nicht akzeptierte V1-Zeilen, keine History/Legacy/accepted; ein vollständiger atomarer Durchlauf, keine neue Cron-/Worker-Infrastruktur und keine willkürliche Produktquote. Arbeitsumfang wächst mit der Zahl offener V1-Zeilen; keine pauschale konstante Latenzgarantie. Die vorhandene 30er-Stressklasse wird gemessen.

Fehler rollen den gesamten Sweep zurück und verhindern nachfolgende Discovery/Anzeige; sie werden nicht als erfolgreicher Cleanup verschluckt. Die Domainservices behalten BEGIN IMMEDIATE, gemeinsame Uhr, Idempotenz, Quota, aktuelle Need-/Supply-Prüfung und vollständigen Rollback. Ein anderer Writer zwischen Cleanup-Commit und Read/GO ist zulässig: Planning liest frisch, GO revalidiert wiederum unter eigenem Schreiblock. Keine alte VALID-Antwort wird Schreibberechtigung.

## Composite Golden Paths und Grenzen

Neue Datei `tests/test_smartdeal_cg1.py`, ausschließlich synthetische V21-Fixtures. Vorhandene Helper werden ohne erneutes Entdecken alter Tests verwendet.

- Accepted **1/1**: echter 17↔17-Zweialbum-Planning-/Pairwise-/Optimizer-/Suggestion-/Identity-Pfad, GO, gebundene Planung, realer Accept-Handler, erneutes DB-Open, gleiche Instanz/Positionen/Zeiten, Acceptance-Event einmal, Inventory unverändert, Bindung auch nach 24h.
- Expiry **1/1**: derselbe reale Mehralbumumfang, frei → geplant → gebunden → operativer Discovery-Cleanup nach 24h → vollständig expired → ursprünglicher Plan wieder verfügbar, physische Mengen unverändert.
- Handlerpfade **4/4**: V1-Decline, V1-Withdraw, Legacy-Decline-Kontrolle und bestehender `smart_trade_calculation`-Cleanup-Einstieg. Tests rufen die realen Flask-Handler in Request-Kontexten mit synthetischer DB und kontrolliertem authentifiziertem Actor auf; Auth/CSRF bleibt in der bestehenden Schutzregression.
- Lifecycle-Sperren **7/7**: Confirm, Ship, Receive, Fail, Problem, Problem-Close und Problem-Resolve; vollständige Tabellen-/DB-Reopen-Vergleiche bestätigen keinerlei Mutation.
- Weitere Grenzen: fälliges Accept ohne Sweep, accepted/Legacy-Schutz, unbekannter Contract, fremder Actor, Cleanup-Idempotenz und fremde noch gültige Reservation.

**29/29 neue Tests GREEN.** Gruppen sind separat ausgewiesen; der Accepted-Golden-Path enthält zusätzlich einen Handleraufruf und wird nicht nochmals als eigener neuer Test gezählt.

## Races und Rollback

**8/8 synchronisierte Race-Tests**, ohne Sleeps: Cleanup/Accept, Cleanup/Withdraw, tatsächlicher Decline-Handler/Mutual GO und Cleanup/neuer GO, jeweils beide Lock-Reihenfolgen. Der vorhandene Barrier/Event-Harness wartet auf erworbenen ersten Schreiblock und den Schreibversuch des zweiten Writers. Nach terminalem Decline darf ein späterer Gegen-GO eine neue Pending-Instanz erzeugen, aber niemals den alten Request wieder annehmen.

**2/2 neue Rollbacktests**: Fehler nach Release-Mutationen verhindert Discovery; derselbe Fehler über realen Decline-Handler liefert 409 und lässt alle Tabellen unverändert. Zusammen neue Race-/Rollbackgruppe **10/10**. Die bestehenden T5a/T5b/T6b-Fehlerinjektionen und Races bleiben unverändert Teil der Schutzregression.

## Performance

`tests/research/benchmark_smartdeal_cleanup.py`: zehn unabhängige synthetische Fixtures pro Klasse, Setup nicht gemessen, vollständiger neuer Cleanup-Wrapper einschließlich Schemaprüfung und T5b-TX gemessen. Keine parallel laufende Testsuite während der Messung.

| Fällige Requests | Mittel ms | Minimum ms | Maximum ms |
| --- | --- | --- | --- |
| 0 | 0,033 | 0,030 | 0,040 |
| 3 | 0,921 | 0,867 | 0,975 |
| 30 | 5,801 | 5,645 | 6,222 |

Kein offensichtlicher zusätzlicher Hotpath in diesen Klassen. Keine neue SLA, kein Nachweis beliebig großer Pools. Audit-Y2 bleibt T11-Aufgabe. Rohlog `/private/tmp/cg1-benchmark.jsonl`.

## Release und Dateischutz

Kanonische Full Release **1251/1251**, 22,480 s; 0 Failures/Errors/Skips. 1263 entdeckt, unveränderte neun historische und drei Baseline-Klassifizierungen. Vorher 1222 plus 29 neue Tests. Kein Test geändert, abgeschwächt oder neu ausgeschlossen. Export `/private/tmp/sammlr-cg1`, ausschließlich Allowlist und synthetische SQL-Fixtures; finale Auftragsdateien werden bytegleich gegen diesen getesteten Export verglichen.

Ein vorläufiger breit ausgewählter Schutzlauf enthielt den bereits historisch klassifizierten S24-Test `test_more_than_twenty_five_paginates_newest_first` (feste August-Daten/Retention) und meldete dessen bekannten Fehler. Der kanonische Schutzlauf verwendet die **unveränderte** vorhandene `R5_TEST_CONTRACT.json`-Kohortentrennung. Die aktuellen Ersatztests sind im grünen Full Release enthalten. Dies ist keine neue Ausnahme für CG-1.

Exakte Auftragsdateien:

1. `App/webapp.py` — begrenzte Contract-Adapter und Cleanup-Aufrufe.
2. `App/services/smartdeal_runtime.py` — neuer Runtime-Adapter/Discovery-Cleanup.
3. `tests/test_smartdeal_cg1.py` — 29 neue Integrationstests.
4. `tests/research/benchmark_smartdeal_cleanup.py` — Messharness.
5. `docs/R5_RELEASE_FILES.json` — drei additive Release-Einträge.
6. `docs/SMARTDEAL_CORE_GATE_FIX_CG1.md` — dieser Nachweis.
7. `docs/SMARTDEAL_CORE_GATE_REAUDIT_CG1.md` — separate Neubewertung, ursprünglicher Audit unverändert.

DB SHA-256 vorher/nachher: `265de4e7cd438a8c9f2bb6673c7a020570605eed8c326e98ab4c378d2fa6d522`. Kanonische DB nur read-only auf Integrity/FK geprüft, nicht migriert. Keine Runtimeänderung der gesperrten Domainservices, keine Migration, keine Produkt-/Roadmapänderung. Kein neuer Versand/Empfang/Kontakt/Chat, keine Trade-UI/Navigation. T7a/T7b/T8a nicht begonnen. Kein git add, Commit, Push oder Deploy.

Finale kanonische Schutzregression: **944/944 GREEN**, 13,596 s, 0 Failures/Errors/Skips. Enthält alle zehn SmartDeal-Blöcke, Inventory/Availability/Reservations, Privacy/Blocks/Tradepool, Legacy Requests/Lifecycle, Notifications/Problems/History und R3. Logs `/private/tmp/cg1-new.log`, `/private/tmp/cg1-protection-final.log`, `/private/tmp/cg1-full-final.log`. `git diff --check` und zusätzlicher Whitespacecheck der neuen Dateien sauber; Integrity **ok**, FK **0 Befunde**. Dateihashvergleich gegen `/private/tmp/cg1-before.json` bestätigt ausschließlich die sieben genannten Auftragsdateien.
