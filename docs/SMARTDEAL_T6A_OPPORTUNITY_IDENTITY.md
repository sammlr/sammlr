# SD-T6a — Kanonische Opportunity-Identität

Stand: 2026-09-11. Reine Domainlogik gemäß Algorithm Contract AC02/07/14/24/28/29. Keine neue Produktregel. Die Wiederaufnahme startet ohne vorherige T6a-Implementierung; Dateibaseline `/private/tmp/sdt6a-before.json`. T1/T2a/T2b/T3a/T3b einschließlich Performance Fix 3b.1 bleiben LOCKED.

## Fachlicher Vertrag und API

[SmartDealIdentityService](../App/services/smartdeal_identity.py) bietet `from_view(user_id, partner_id, outgoing_pieces, incoming_pieces)` und den additiven Adapter `from_deal(user_id, SmartDealCandidate)`. Ergebnis: eingefrorene `SmartDealOpportunityIdentity`. Der Adapter liest ausschließlich das finale T3b-Paket; kein Recompute, Umordnen des Plans, Kürzen oder Rebalancing. Der Aufrufer liefert die zu diesem Plan gehörige Nutzer-ID; Identifikation authentifiziert diese Angabe nicht.

Das numerisch aufsteigend geordnete Nutzerpaar legt low/high fest. Outgoing wird dem tatsächlichen Geber zugeordnet: bei low-Viewer low→high, bei high-Viewer high→low. Incoming gehört jeweils dem anderen Teilnehmer. Es gibt keinen globalen current_user und keine Sessionabhängigkeit.

Jede Leistung enthält vollständig `(album_id, sticker_code, quantity)`. Album-/Codeidentitäten bleiben unverändert, einschließlich Groß-/Kleinschreibung und Unicode; keine Aliasauflösung, Normalisierung, natürliche Zahlensortierung, UI-Labels, Bildpfade oder physische Kopien-IDs. Sortierung lexikographisch nach Album und Code gemäß AC14. Gleicher Code in verschiedenen Alben bleibt verschieden. Nutzer-Album-Mitgliedschaft ist keine zusätzliche Stückidentität nach AC24.

Mengen werden vor Kanonisierung nach Identität summiert und als Integer explizit serialisiert. AC07 begrenzt jede gelieferte Identität je Empfänger auf **1**. Mengen >1 und doppelte positive Zeilen derselben Identität werden deshalb abgewiesen; auch Null, negative Werte, Bool, Float und Zahlentext sind ungültig. Ein fachlich zulässiger Wechsel 1→2 existiert in V1 nicht. Test J prüft daher die Ablehnung, statt vorsorglich Mehrfachbedarf einzuführen. Mehrere Geberkopien für verschiedene Partner bleiben unverändert möglich.

Diese reine Identifikation prüft keine aktuelle Availability, Eligibility, Balance oder Top-Mindestgröße. Auch ein einseitig ergänztes/gekürztes Inhaltspaket erhält eine andere Identität, ohne es still zu reparieren oder als ausführbaren SmartDeal zu bestätigen. Der spätere Validator bleibt erforderlich. Gültige T3b-Outputs erfüllen ihre gesperrten Invarianten bereits.

## Serialisierung, Version und Kollisionsschutz

Die bestehende T1-Konstante `SMARTDEAL_V1_CONTRACT = "smartdeal_v1"` bildet die Domain-/Vertragsversion. Kein neuer Produktvertrag. Festes JSON-Objekt, Schlüssel ASC, kompakte Separatoren, `ensure_ascii=False`, UTF-8 ohne BOM, keine Zahlen als Strings. Arrays halten explizit Teilnehmer und gerichtete Positionsgrenzen. Beispiel des unabhängigen Golden-Vector-Tests (klein, nur Formatnachweis):

```json
{"contract_type":"smartdeal_v1","high_to_low":[["em24","I",1]],"low_to_high":[["vfl","O",1]],"participants":[7,42]}
```

Vollständiges SHA-256 aus der Standardbibliothek über genau diese UTF-8-Bytes. `digest` enthält alle 64 Hexzeichen; `lookup_key` lautet `smartdeal_v1:sha256:<64 Hexzeichen>`. Kein Python-`hash()` als externe Identität. JSON-Escaping trennt auch Codes mit Anführungszeichen, Trennern, Zeilenumbrüchen und Backslashes eindeutig. Ungültige UTF-8-Surrogate scheitern geschlossen.

**AC24: Der Digest allein ist niemals fachliche Gleichheit.** Die eingefrorene Identity vergleicht Vertragsart, beide Nutzer und beide vollständigen kanonischen Positionsfolgen. `digest` und die abgeleitete Payload sind keine Ersatzvergleichsfelder. Selbst bei künstlich identischen SHA-256-Werten bleiben verschiedene Identity-Objekte ungleich; die Kollisionssimulation prüft auch Set-Mitgliedschaft. Eine spätere Hashsuche muss anschließend die vollständige Identity vergleichen. Der Lookup-Key ist weder Signatur noch GO-Berechtigung und darf nicht allein einen Merge auslösen. `canonical_payload` bleibt für interne Tests/Debugging verfügbar, wird nicht geloggt oder durch eine Route veröffentlicht.

Die semantische Identität ist daher vollständig und verlustfrei; der Digest hat die üblichen kryptographischen Eigenschaften, keine behauptete mathematische Kollisionsfreiheit. Künftige inkompatible Vertragssemantik darf nicht unter unverändertem V1-Domainformat ausgegeben werden.

## Invarianten und spätere Verwendung

- Spiegelung der Teilnehmer und ihrer Leistungen ergibt bytegleiche Payload und gleichen Lookup-Key.
- Eingabepermutation ergibt dieselben sortierten Leistungen.
- Anderer Teilnehmer, anderes Piece, anderes Album, hinzugefügtes oder entferntes Piece verändert den kanonischen Inhalt und in den Negativtests auch den Digest.
- Vertauschte Leistungen bei unverändertem Nutzerpaar sind ein anderes Paket.
- Rank, Score, Plan-ID, Berechnungszeit, Requestzeit, Session, Aufruf-ID und Anzeigenamen fehlen vollständig.
- Tatsächliche T3b-Neuberechnung mit zusätzlicher Konkurrenz verschiebt ein unverändertes Paket von Platz 1 auf 3: Identity bleibt gleich.
- Unverändertes Paket nach erneuter Berechnung bleibt identisch; geändertes Paket wird neu identifiziert. Staleness/Eligibility werden hier nicht gelöst.
- Keine Registry oder Vorgangs-ID: Ein beendeter früherer Vorgang kann eine identische neue Opportunity nicht durch diese Domainfunktion sperren.

Für späteres Mutual GO können A und B ihre exakten Inhalte gleich vergleichen. Der Test führt ausschließlich diesen Vergleich aus; keine Zustimmung, Requestanlage oder Annahme. Globale Pläne beider Nutzer müssen nicht allgemein dieselben Pakete enthalten. Im echten isolierten Zwei-Nutzer-Fixture werden beide T3b-Pläne separat berechnet und ihre Spiegelpakete gleich identifiziert.

Durable aktive Deduplizierung und Transaktionssicherung aus der umfassenderen Roadmap sind nach dem konkreten T6a-Auftrag **nicht** implementiert. Reine Paketidentität benötigt keine Persistenz. Das verschiebt keine Produktentscheidung und ist kein behaupteter Race-/Mutual-GO-Nachweis.

## Tests und Performance

25 neue Tests decken alle Pflichtfälle A–R ab; Q/R sind ein gemeinsamer Integrationstest. Zusätzlich simulierte Hashkollision, vertauschte Geberleistungen, unzulässige Mengen/Duplikate, Unicode-/Trennerfälle, unabhängiger Golden Vector, tiefe Unveränderlichkeit und drei separate Prozesse mit PYTHONHASHSEED 0/1/731. Spiegelmatrix: ein Album, mehrere Alben, 5/28/150 Stück, verschiedene Reihenfolgen und numerisch unterschiedlich geordnete Nutzer-IDs.

Der echte V21-Integrationstest erstellt T2a→T2b→T3b ausschließlich auf einer synthetischen temporären DB. Während Identity-Erzeugung: SQL-Trace leer, neue Verbindungen sowie Planning/Optimizer-Aufrufe explizit untersagt, DB-Hash und total_changes unverändert einschließlich Fehlerpfad. Ein frischer Prozess importiert Identity ohne sqlite3, Flask, Planning oder Optimizer. Runtime importiert nur Standardbibliothek und die reine T1-Vertragskonstante; die T3b-Typreferenz ist ausschließlich TYPE_CHECKING.

[Reproduzierbarer Benchmark](../tests/research/benchmark_smartdeal_identity.py): Python 3.13.15, macOS 26.6.2 ARM64. Je drei Serien mit 1.000 Identifikationen eines echten synthetischen T3b-Outputs. Kompletter `from_deal` inklusive Transformation, Sortierung, JSON und SHA-256 gemessen; Fixture-/Optimiereraufbau vorher, kein SQL, keine parallel laufenden Tests. Mittelzeit pro Aufruf innerhalb jeder Serie, keine P95-Aussage:

| Größe je Seite | Serie 1 ms | Serie 2 ms | Serie 3 ms |
| --- | ---: | ---: | ---: |
| 5 | 0,005934 | 0,006163 | 0,005776 |
| 28 | 0,020812 | 0,020998 | 0,020691 |
| 150 | 0,094829 | 0,094559 | 0,095690 |
| 1.500 | 1,121510 | 1,166367 | 1,155059 |

Keine feste Laufzeit-Assertion; Aufwand O(m log m) für die Sortierung plus lineare Serialisierung/Hashbildung, linearer Speicher in Payloadgröße. Identity-Aufwand bleibt klein; keine erneute globale Suche. T3b und dessen akzeptierter Performancefix bleiben bytegleich.

## Acceptance und Schutzprüfung

**SD-T6a umgesetzt: JA. Acceptance: GREEN.**

| Prüfung | Ergebnis |
| --- | --- |
| Neue T6a-Tests | **25/25** |
| T1 / T2a / T2b | **18/18 / 29/29 / 22/22**, unverändert |
| T3a / T3b einschließlich 3b.1 | **27/27 / 29/29**, unverändert |
| T3b Oracle / Pflichtklassen | **500/500 / 17/17**, Bestandteil der unveränderten Tests |
| Schutzregression einschließlich T6a | **499/499** in 9,636 s |
| Kanonische vollständige V21 Release-Suite | **1.017/1.017** in 19,977 s |
| Full-Suite Failures / Errors / Skips | **0 / 0 / 0** |

1.029 Tests entdeckt; unverändert neun historische und drei Baseline-Klassifizierungen. Keine neue Ausnahme, keine Erwartungsänderung. Die gesperrte 992er-Baseline bleibt vollständig enthalten. Schutzregression umfasst Inventory, Availability, Reservations, Privacy, Blocks, Tradepool, altes SmartMatch, Requests, Shipping/Receipt/Problems/Completion, History/Notifications, Account-Lifecycle und R3 Golden Path.

Isolierter Allowlist-Export `/private/tmp/sammlr-sdt6a-final` mit 2.232 Dateien, ausschließlich synthetische Testfixtures über `Scripts.prepare_release_tests`. Interpreter: unveränderte Repository-`.venv/bin/python`, keine Dependency-Installation. Reproduktion:

```text
python3 -B -m Scripts.assemble_release --destination /private/tmp/sammlr-sdt6a-final
# Im isolierten Export, mit dem Repository-Interpreter und PYTHONDONTWRITEBYTECODE=1:
python -m Scripts.prepare_release_tests
python -m unittest tests.test_sd_t6a_identity -v
python -m Scripts.release_test_gate --cohort release
# Benchmark, PYTHONPATH=App:
python -m tests.research.benchmark_smartdeal_identity
```

Logs: `/private/tmp/sdt6a-focused-final.log`, `/private/tmp/sdt6a-regression.log`, `/private/tmp/sdt6a-full.log`, `/private/tmp/sdt6a-benchmark.jsonl`. Neue Runtime-/Test-/Benchmark-Dateien und Release-Allowlist sind bytegleich mit dem getesteten Export. Kein nachträglicher Runtime-/Testpatch.

Kanonische App-DB ausschließlich read-only geprüft, unverändert auf V20; alle V21-Fixtures temporär. Keine Migration:

```text
DB-SHA-256 vorher:
265de4e7cd438a8c9f2bb6673c7a020570605eed8c326e98ab4c378d2fa6d522
DB-SHA-256 nachher:
265de4e7cd438a8c9f2bb6673c7a020570605eed8c326e98ab4c378d2fa6d522
integrity_check: ok
foreign_key_check: 0 Befunde
```

`git diff --check` bestanden; zusätzliche Whitespace-Prüfung einschließlich neuer untracked Dateien bestanden. Vollständiger Dateihashvergleich gegen den Auftragsbeginn bestätigt: T1/T2a/T2b/T3a/T3b und Performancefix, ihre Tests/Research-Artefakte, sämtliche Migrationen, Product Bible, Algorithm Contract, bestehende Runtime und DB unverändert. Der bereits vorhandene dirty Worktree bleibt erhalten.

Exakt sechs Auftragsdateien:

1. **Neu** `App/services/smartdeal_identity.py` — einzige neue Runtime-Datei; keine bestehende Runtime-Datei geändert.
2. **Neu** `tests/test_sd_t6a_identity.py` — 25 Tests.
3. **Neu** `tests/research/benchmark_smartdeal_identity.py` — synthetische Messung.
4. **Neu** `docs/SMARTDEAL_T6A_OPPORTUNITY_IDENTITY.md` — dieser Bericht.
5. **Additiv geändert** `docs/R5_RELEASE_FILES.json` — genau die drei neuen Runtime-/Test-/Benchmark-Dateien aufgenommen.
6. **Minimal geändert** `docs/SMARTDEAL_TECHNICAL_ROADMAP_V1.md` — Acceptance-Notiz und Nachweislink.

**SD-T4, SD-T5a, SD-T6b NICHT begonnen.** Kein GO, Request, Reservation oder Mutual GO, keine UI oder sichtbare Route. Keine Persistenz, keine Schemaänderung. Kein git add, Commit, Push oder Deploy. **STOP nach SD-T6a.**
