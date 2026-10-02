# SD-T4 — Suggestion-Payload und exakte Revalidierung

Stand: 2026-09-11. Reine interne Domain-Grundlage nach AC02–09, AC18–20, AC24 und AC28/29. T1/T2a/T2b/T3a/T3b einschließlich 3b.1 und T6a sind LOCKED. Keine neue Produktregel, keine Persistenz, kein GO-Command.

## Payload und Adapter

[smartdeal_suggestions.py](../App/services/smartdeal_suggestions.py) definiert die eingefrorene `SmartDealSuggestion`:

| Feld | Bedeutung |
| --- | --- |
| contract_type | ausschließlich bestehendes `smartdeal_v1` |
| opportunity_identity | vollständige kanonische T6a-Identity einschließlich Payload und Digest |
| participant_a / participant_b | kanonische Nutzer-IDs numerisch ASC |
| side_a_pieces / side_b_pieces | exakt vom jeweiligen Nutzer gelieferte `SmartDealPiece(album_id, sticker_code, quantity)`-Tupel |
| piece_count | Stückzahl je Seite, mindestens fünf, exakt 1:1 |
| involved_albums | eindeutige tatsächlich enthaltene Alben ASC |

`SmartDealSuggestion.from_deal(user_id, final_t3b_deal)` verwendet den gesperrten T6a-Adapter und überführt dessen Leistungen in die kanonischen beiden Seiten. Das finale T3b-Paket bleibt vollständig erhalten. Kein Rankingfeld, kein Berechnungszeitpunkt, keine Availability im Payload. Ein gespiegelter tatsächlicher T3b-Output des anderen Nutzers ergibt dieselbe Suggestion. Die Factory erzeugt kanonisch geordnete Positionen; die Validierung akzeptiert auch semantisch identische Positionspermutationen, ohne den Input zu verändern.

Die Factory prüft strukturell das Paket; sie bestätigt keine Aktualität. Der Validator behandelt auch manuell konstruierte Domain-DTOs als ungeprüft. Dictionaries oder fremde Typen werden nicht blind als Domainobjekt übernommen; ein Browser-/JSON-Parser und ein sichtbarer Transportpfad sind nicht Teil dieses Auftrags.

## Zentraler Validator und serverseitige Wahrheit

`SmartDealSuggestionValidator(connection, catalog_provider, now_provider).validate(suggestion, actor_user_id)`:

1. Payload strikt prüfen: Vertrag, positive unterschiedliche kanonische Teilnehmer, Tupel-/Piece-Typen, ganzzahlige Mengen, V1-Need-Cap, keine doppelten Identitäten, exakte Balance, Mindestgröße und abgeleitete Metadaten.
2. T6a-Identity aus allen konkreten Leistungen **neu rekonstruieren** und vollständigen Inhalt, kanonische Payload sowie Digest mit der getragenen Identity vergleichen. Ein Hash-Treffer allein genügt auch bei simulierter Kollision nicht.
3. Prüfen, dass die serverseitig übergebene Akteur-ID Teilnehmer ist. Diese ID muss später aus authentifiziertem Kontext stammen; der Payload authentifiziert niemanden.
4. Auf **jedem** Aufruf `SmartDealPlanningService.build_pairwise_inputs(actor_user_id)` neu laden. Keine Annahme eines alten PlanningState, kein Cache. Der serverseitige Katalogadapter ist standardmäßig das bestehende `all_codes`; injizierte Provider dienen den synthetischen Tests.
5. Zielpartner in der aktuellen kanonischen Eligibility und Partnerprojektion verlangen. T2a liefert bestehende Account-/Block-/Pool-/Trade-Privacy-Regeln; allgemeine private Profile oder Alben mit zulässiger Poolfreigabe werden nicht neu verboten.
6. Für jede exakte Leistung erlaubtes Album, freie Geber-Supply mindestens der geforderten Menge und freien Empfänger-Need exakt eins prüfen. Beide Richtungen sind gleichwertig. Keine eigene quantity−1-Formel; Reservations, Eigenexemplar und Incoming-Zusagen einschließlich Transit stammen unverändert aus T2a.

Der Aufruf von `build_pairwise_inputs` ist ein Batch-Leseweg von **T2a**, kein T2b-Paarmatching. T2b und T3b werden während Revalidation nicht aufgerufen. T2a lädt derzeit die vollständigen eligible Partnerinventare; die Queryzahl bleibt gebündelt, Datenvolumen kann mit dem übrigen Pool wachsen. Eine separate zielpartnerspezifische zweite Availability-Wahrheit wurde nicht eingeführt.

## Ergebnisvertrag

Eingefrorene `SuggestionValidation(status, reason)`; Reasons sind technische Codes, keine UI-Texte:

| Status | Bedingungen / Reasons |
| --- | --- |
| VALID | `exact_package_available`: strukturell gültiges Paket, Identität konsistent, beide Seiten im aktuellen Snapshot vollständig verfügbar und benötigt |
| STALE | `canonical_state_unavailable`, `partner_unavailable`, `album_unavailable`, `supply_unavailable`, `need_unavailable` |
| INVALID_PAYLOAD | `payload_contract` für manipulierte/ungültige Struktur oder Identity; `actor_not_participant` für unzulässigen Akteurparameter |

Fehlender/inaktiver Akteur oder inkonsistente kanonische Bindungsprojektion kann keine aktuelle Ausführbarkeit beweisen und ergibt STALE. Infrastruktur-/unerwartete interne Fehler propagieren; kein Fehler wird als VALID oder Ersatzpaket ausgegeben.

Andere Positionen, zusätzliche/entfernte Pieces, andere Teilnehmer, Vertragsart, Mengen, Duplikate oder falsche Metadaten werden abgewiesen. Auch mit neu berechneter Identity bleibt ein unbalanciertes oder kleineres als 5↔5-Paket INVALID. T6a-Mengenmodell unverändert: jedes positive Line-Item je Empfänger/Identität ist eins.

Ein Digest ist weder Signatur noch Nachweis einer früheren Anzeige. T4 prüft konsistenten exakten Inhalt und aktuelle serverseitige Ausführbarkeit, nicht die Provenienz einer Browseranzeige. Eine selbst konsistent veränderte, aktuell ausführbare neue Paketbeschreibung ist fachlich eine andere Opportunity; sie wird niemals unter der alten Identity akzeptiert. Der spätere Transport-/Auth-Pfad darf eine übermittelte Akteur-ID oder Client-Availability nicht zur Autorität machen.

## Exaktheit, Rang und Atomaritätsgrenze

Rank, Gesamtplanhash und aktuelle Top-5-Mitgliedschaft sind keine Validitätsbedingungen. Ein besserer neu berechenbarer Deal oder irrelevante Bestandsänderungen entwerten ein weiterhin vollständig mögliches Paket nicht. Die Tests prüfen sowohl tatsächlichen Rangwechsel als auch ein altes Paket, das gar nicht mehr im aktuellen Top-Plan liegt. Zusätzliche gebundene Kopie bei weiterhin ausreichender freier Supply bleibt zulässig; „irgendetwas reserviert“ ist kein pauschales Verbot.

Verliert dagegen nur ein benötigtes Piece freie Supply oder freien Need, ist das gesamte unveränderte Paket STALE. Keine Kürzung, Ersatzwahl, Neuoptimierung oder heimliche neue Suggestion. Ein Test weist ausdrücklich eine weiterhin mögliche andere 5↔5-Allokation nach und lehnt trotzdem das alte Paket ab.

**VALID ist nur eine Aussage über den Lese-Snapshot, keine Reservation oder vollständige GO-/Annahmeberechtigung.** Ohne bestehende Aufrufertransaktion öffnet/beendet T2a einen eigenen Read-Snapshot. Eine parallele Änderung nach dessen Beginn wird innerhalb desselben Aufrufs nicht teilweise eingemischt; der nächste Aufruf sieht sie und kann STALE liefern. Vorhandene Aufrufertransaktionen bleiben offen und werden weder committed noch zurückgerollt. Deren Snapshot-Frische verantwortet der Aufrufer.

T5a muss später die relevante Schreibtransaktion **vor** der Revalidierung beginnen und Prüfung, Requestanlage und beide Bindungen ohne dazwischenliegende Freigabe atomar ausführen. Quote, Request-/Retry-/Fristentscheidung und der eigene Bindungskontext einer späteren Mutual-Annahme sind keine durch dieses T4-VALID erteilten Rechte. Insbesondere sichert T4 keinen der drei Anfrageplätze. Keine dieser T5/T6b-Operationen wurde vorgezogen.

## Tests und Performance

42 neue Tests in [test_sd_t4_suggestions.py](../tests/test_sd_t4_suggestions.py), alle Pflichtfälle A–Z sowie zusätzliche Kollisions-, Mengen-/Metadaten-/Mindestgrößen-, Read-Snapshot-, Fehler-/Rollback-, Nullmutations- und Queryzahlprüfungen. Gültige vollständige Pakete werden aus echten T2a→T2b→T3b-Outputs auf synthetischen V21-Fixtures abgeleitet. A/B-Bindungsfälle werden getrennt geprüft; testseitige Bindungsfixtures nutzen bestehende Legacy-Positions-/Reservationsfakten und implementieren keinen V1-Writer.

[Benchmark](../tests/research/benchmark_smartdeal_revalidation.py): Python 3.13.15, macOS 26.6.2 ARM64; drei Serien mit je 100 Aufrufen. Gemessen wird der vollständige Validator einschließlich frischem T2a-Snapshot/SQLite-Reads und Identity-Kontrolle. Fixture-/T3b-Aufbau außerhalb des Timers, keine parallel laufenden Tests. Mittelwert pro Aufruf innerhalb einer Serie; keine P95-/Produktions-SLA.

| Paket | Alben | SQL-/Transaktionsanweisungen je Aufruf | Serie 1 / 2 / 3 in ms |
| --- | ---: | ---: | --- |
| 5↔5 | 1 | 21 | 0,1110 / 0,1073 / 0,1102 |
| 25↔25 | 2 | 21 | 0,2321 / 0,2303 / 0,2294 |
| 150↔150 | 2 | 21 | 0,9848 / 0,9696 / 0,9675 |

Die 21 Anweisungen beinhalten BEGIN/ROLLBACK des eigenen Snapshots. Keine per-Piece-SQL-Schleife; ungültige Payloads benötigen null SQL. Konstantheit über alle drei Paketgrößen ist zusätzlich getestet. Fixture umfasst zwei Teilnehmer und kleine synthetische Kataloge; daraus folgt keine allgemeine Latenzgarantie für beliebige Partnerpools. Keine harte neue SLA.

## Acceptance, Regression und Dateischutz

**SD-T4 umgesetzt: JA. Acceptance GREEN.**

| Prüfung | Ergebnis |
| --- | --- |
| Neue T4-Tests | **42/42**, alle A–Z und Zusatzverträge |
| T1 / T2a / T2b | **18/18 / 29/29 / 22/22**, unverändert |
| T3a / T3b inklusive 3b.1 / T6a | **27/27 / 29/29 / 25/25**, unverändert |
| T3b Oracle / Pflichtklassen | **500/500 / 17/17**, in den gesperrten Tests erneut ausgeführt |
| Schutzregression einschließlich T4 | **541/541**, 10,126 s |
| Vollständige kanonische V21 Release-Suite | **1.059/1.059**, 20,387 s |
| Full-Suite Failures / Errors / Skips | **0 / 0 / 0** |

1.071 entdeckt; unverändert neun historische und drei Baseline-Klassifizierungen. Kein bestehender Test verändert, abgeschwächt oder ausgeschlossen. Die 1.017er-Baseline bleibt vollständig enthalten. Schutzregression umfasst zusätzlich Inventory, Availability, Reservations, Privacy, Blocks, Tradepool, altes SmartMatch, Requests, Shipping/Receipt/Problems/Completion, History/Notifications, Account-Lifecycle und R3 Golden Path.

Isolierter Allowlist-Export `/private/tmp/sammlr-sdt4-final`, 2.235 Dateien; synthetische Fixtures mit `Scripts.prepare_release_tests`. Unveränderter Repository-Interpreter `.venv/bin/python`, Python 3.13.15, keine Dependency-Installation. Ausführung mit `PYTHONDONTWRITEBYTECODE=1`. Release-Gate im Export: `python -m Scripts.release_test_gate --cohort release`; neue Tests: `python -m unittest tests.test_sd_t4_suggestions`; Benchmark mit `PYTHONPATH=App python -m tests.research.benchmark_smartdeal_revalidation`.

Logs: `/private/tmp/sdt4-focused.log`, `/private/tmp/sdt4-regression.log`, `/private/tmp/sdt4-full.log`, `/private/tmp/sdt4-benchmark.jsonl`. Neue Runtime-/Test-/Benchmark-Dateien und Allowlist sind bytegleich mit dem getesteten Export. Keine Runtime-/Teständerung nach dem Full-Gate.

Kanonische lokale App-DB ausschließlich read-only geprüft, bleibt V20; alle V21-Testdatenbanken temporär. **Keine Migration, keine DB-Mutation.**

```text
DB-SHA-256 vorher:
265de4e7cd438a8c9f2bb6673c7a020570605eed8c326e98ab4c378d2fa6d522
DB-SHA-256 nachher:
265de4e7cd438a8c9f2bb6673c7a020570605eed8c326e98ab4c378d2fa6d522
integrity_check: ok
foreign_key_check: 0 Befunde
```

`git diff --check`: bestanden. Zusätzlich alle neuen/auftragsbezogenen Dateien auf Whitespace geprüft. Vollständiger Dateihashvergleich gegen `/private/tmp/sdt4-before.json`: alle gesperrten Vorstufen einschließlich Tests/Research/Nachweisen, Migrationen, bestehende Runtime, Product Bible, Algorithm Contract und App-DB unverändert. Vorbestehender dirty Worktree bleibt erhalten.

Exakt sechs Auftragsdateien:

1. **Neu:** `App/services/smartdeal_suggestions.py` — einzige neue Runtime-Datei; keine bestehende Runtime-Datei geändert.
2. **Neu:** `tests/test_sd_t4_suggestions.py` — 42 Tests.
3. **Neu:** `tests/research/benchmark_smartdeal_revalidation.py` — 5/25/150-Benchmark inklusive frischer Reads.
4. **Neu:** `docs/SMARTDEAL_T4_SUGGESTION_REVALIDATION.md` — dieser Bericht.
5. **Additiv geändert:** `docs/R5_RELEASE_FILES.json` — ausschließlich drei neue Runtime-/Test-/Benchmark-Einträge.
6. **Minimal geändert:** `docs/SMARTDEAL_TECHNICAL_ROADMAP_V1.md` — Acceptance-Notiz und Link.

**SD-T5a, SD-T5b und SD-T6b NICHT begonnen.** Keine Requestanlage, Reservation, Notification, Bindungs-/Annahmezeitänderung, Inventory- oder Lifecycle-Mutation. Kein Mutual GO, keine UI, kein GO-Button und keine sichtbare Route. Keine Suggestion-Persistenz. Kein git add, Commit, Push oder Deploy. **STOP nach SD-T4.**
