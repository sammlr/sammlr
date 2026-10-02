# SD-T3b Acceptance Fix 3b.1

Stand 2026-09-11. **T3b GREEN** für das vorgegebene synthetische Acceptance-Gate. Keine allgemeine HTTP-/Produktionslatenzgarantie oder Aktivierung. SD-T6a nicht begonnen.

## Nachgewiesene Ursache

**JA.** E erzeugt viele fast gleich gute, ressourcenüberlappende Gruppen, bevor die aufsteigende Teilmengensuche den ersten G=40-Plan erreicht. Von 367 Netzwerken liegen allein 267 bei fünf Partnern und Upper Bound 38 oder 39. Das optimale G=40 wird erst spät gefunden. Vorher werden 25.089 Größenreihenfolgen exakt nachoptimiert. Das ist keine mangelnde Flow-Korrektheit und keine teure C-Auswahl.

Die Research-Instrumentierung misst für E **98.220 D/J-Feasibility-Anfragen**, davon 86.655 Memo-Hits und **11.565 echte Flows**. D/J-Feasibility beansprucht ca. **1,916 s**; E/G benötigt 1.082 Flows und ca. 0,144 s; C benötigt keine Flows. D/J ist damit allein bereits die dominante Komponente. D und J werden im Algorithmus gemeinsam über die Größenpermutationen optimiert; E/G teilen die Gain-Suche. Die Diagnose trennt diese operativen Phasen, ohne künstlich exklusive Zeiten für gekoppelte Kriterien zu behaupten. Die erste Diagnose hatte exakte Total-Bounds pauschal D/J zugeordnet; die archivierten finalen Daten verwenden den tatsächlichen Aufrufer (Gain- vs Größen-Lambda).

| Struktur | C | D | E | F |
| --- | ---: | ---: | ---: | ---: |
| Partner | 20 | 10 | 20 | 25 |
| Overlap-Kanten (gleiche Richtung/Identität) | 0 | 44 | 101 | 299 |
| Zusammenhangskomponenten | 20 einzelne | 1 mit 10 | 1 mit 20 | 1 mit 25 |
| Identische O/I-Kandidatensignaturen | 0 | 0 | 0 | 0 |
| Vorher erzeugte Netzwerke | 5 | 26 | 367 | 87 |
| Vorher wegen Mindestkapazität verworfen | 0 | 309 | 0 | 52.356 |
| Vorher wegen E-Schranke verworfen | 0 | 293 | 21.092 | 15.938 |
| Vorher wegen J-Schranke verworfen | 21.694 | 9 | 240 | 24 |
| Nach Gain-Suche wegen E/G ausgeschieden | 0 | 0 | 85 | 0 |

C hat unabhängige Ressourcen und erreicht sofort pro Gruppengröße die Schranke. D/F teilen kleinere Ressourcenpools; insbesondere F verwirft 52.356 Gruppen bereits wegen unzureichender Mindestkapazität. E hat durch private plus gemeinsame Ressourcen genügend Kapazität für viele fast gleichwertige Gruppen. Mehr Dichte allein erklärt den Aufwand nicht: F ist dichter, aber wesentlich günstiger. Alle tatsächlich erzeugten Netzwerke waren zunächst feasible.

Memoization funktioniert: 86.655 identische Anfragen werden in E bereits wiederverwendet. Die 12.647 übrigen Zustände sind unterschiedliche exakte Schlüssel einschließlich Partner-Identität/Bounds und gegebenenfalls C-Präfix. Das beweist keine semantische Nichtäquivalenz beliebiger verschiedener Netzwerke. Es gibt keine gemessene Grundlage für eine weitergehende Zustandszusammenlegung oder Partnerdominanz. Diese wurde deshalb nicht eingeführt. Eine reine Komponentenzerlegung würde E nicht aufteilen.

## Genau eine produktive Optimierung: vollständige Branch-Reihenfolge

`_search_subsets` stellt höchstens eine algebraisch besonders vielversprechende Gruppe voran. Anschließend werden **alle bisherigen Teilmengen in unveränderter kanonischer Reihenfolge** untersucht. Der vorangestellte Zweig kann dabei nochmals erscheinen; auch diese Wiederholung wird gezählt. Es gibt keine Kandidatenabschneidung, keinen ungeprüften Ergebnis-Shortcut und keine veränderte Pruning-Regel.

Für n aktive Partner sei M(p)=min(|O(p)|,|I(p)|) und U die globale Supply-/Incoming-Union-Schranke. Dann gilt für jede zulässige Gruppe:

`G <= U_n = min(U, Summe der n größten M)` und `E <= U_n - 2n`.

Der Vorlauf nimmt die Gruppengröße mit maximalem lexikographischem `(U_n-2n, U_n)`. Er sucht in ID-Reihenfolge die erste Gruppe mit `Summe M = U_n` und ausreichenden beiden Union-Kapazitäten. Das sind nur notwendige Kriterien; tatsächliche Feasibility, E/G/D/J und C werden unverändert durch den exakten Motor bewiesen. Scheitert der Vorlauf oder die Gruppe, läuft die vollständige Suche trotzdem. Das Beenden des Vorlaufs schneidet **keinen** Zweig der Hauptsuche ab.

**Optimalitätserhaltung:** Die neue Besuchsfolge enthält die gesamte alte Besuchsfolge. Ein Incumbent entsteht nur aus einem tatsächlich feasible, exakt optimierten Plan. Die bisherigen zulässigen lexikographischen Schranken dürfen deshalb früher greifen. Jeder Zweig, der das Ergebnis verbessern könnte, bleibt erhalten. Die bestehenden Regeln für D/J und die abschließende C-Minimierung bleiben identisch; weder Ergebnis noch Tie-Break darf von der Besuchsfolge abhängen. Die globale Schranke steuert ausschließlich die Besuchsfolge, niemals eine ungeprüfte Rückgabe. Der Speicher bleibt linear in der Partnerzahl plus Ressourcen von höchstens fünf Partnern; keine materialisierte Kombinationenliste.

Für E findet der Vorlauf nach 15.172 leichten Gruppenprüfungen die G=40-Gruppe. Die anschließende vollständige Suche verwirft 21.698 Gruppen über E und die wiederholte Gewinnergruppe über Gleichheit E/G/D/J. D/F finden im Vorlauf keine passende Gruppe und behalten exakt ihre bisherigen Flows/Ergebnisse.

## Messzahlen vor / nach

`subsets` zählt die Hauptsuche inklusive vorangestelltem Zweig. Der Research-Vorlauf wird separat ausgewiesen; die Gesamtarbeit wird nicht als 21.700 Prüfungen verschleiert.

| Fall | Hauptsuche vorher → nach | Vorlauf nach | Pruned vorher → nach | Flows = Misses vorher → nach | Memo-Hits vorher → nach | verschiedene Zustände vorher → nach | D/J-Reihenfolgen vorher → nach |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| C | 21.699 → 21.700 | 1 | 21.694 → 21.699 | 10 → 2 | 0 → 0 | 10 → 2 | 153 → 120 |
| D | 637 → 637 | 210 | 611 → 611 | 410 → 410 | 540 → 540 | 410 → 410 | 465 → 465 |
| E | 21.699 → 21.700 | 15.172 | 21.332 → 21.699 | 12.647 → 2 | 86.655 → 0 | 12.647 → 2 | 25.089 → 120 |
| F | 68.405 → 68.405 | 12.650 | 68.318 → 68.318 | 2.100 → 2.100 | 2.883 → 2.883 | 2.100 → 2.100 | 1.661 → 1.661 |

`pruned` ist der bestehende Runtime-Zähler vor Netzwerkaufbau. Die 85 späteren E/G-Ausscheidungen von E stehen separat im Diagnoseprotokoll. Nachher benötigt E zwei E/G-Flows; D/J arbeitet die 120 Permutationen rein algebraisch ohne zusätzliche Feasibility-Anfrage ab. C bleibt flowfrei. Hauptaufwand ist jetzt die vollständige Enumeration mit Union-/Schrankenberechnung und Vorlauf.

## Benchmarks

Identische synthetische A–F plus 150↔150, Python 3.13.15, macOS ARM64. Je drei Läufe, keine gleichzeitig laufenden Regressionen. Timer umfasst den gesamten Optimierer einschließlich Vorlauf, Validierung und Planaufbau. Fixture-/T2a-/T2b-Aufbau, Diagnoseinstrumentierung und externe Validierung liegen außerhalb. Keine privaten Daten, DB oder HTTP. Rohdaten unter [SD_T3B1_EVIDENCE](SD_T3B1_EVIDENCE/).

| Fall | Vorher ms (3 Läufe) | Nachher ms (3 Läufe) |
| --- | --- | --- |
| A-small-normal | 0.284, 0.211, 0.264 | 0.238, 0.162, 0.153 |
| B-medium-normal | 6.021, 5.536, 5.305 | 1.428, 1.447, 2.063 |
| C-20-disjoint | 85.798, 85.781, 85.644 | 86.044, 87.482, 86.228 |
| D-10-overlapping-T3a | 48.291, 50.188, 48.370 | 47.902, 50.148, 47.994 |
| E-20-mixed | 2152.326, 2157.471, 2159.049 | 85.997, 85.836, 86.339 |
| F-25-dense-stress | 454.399, 455.901, 453.379 | 452.464, 454.732, 452.136 |
| G-single-150 | 1.054, 0.998, 1.006 | 1.040, 1.028, 1.016 |

E separat, zehn weitere Läufe in ms: 85.904, 85.893, 85.859, 86.209, 85.776, 86.272, 85.984, 86.916, 86.917, 87.296.

E liegt damit in allen 13 Läufen bei 85,776–87,296 ms statt 2.152,326–2.159,049 ms. Langsamster realistischer Fall A–E ist in der Dreiermessung C mit maximal 87,482 ms (E einschließlich Zusatzläufen maximal 87,296 ms). Einschließlich deklariertem dichtem Stressfall ist F mit maximal 454,732 ms am langsamsten. **Performance-Gate GREEN**, Correctness weiterhin GREEN. Diese Messung ist keine universelle Laufzeitgrenze für beliebig große Eingaben.

## Correctness und Regression

Nach der einzigen produktiven Optimierung lief das vollständige bestehende Runtime-Gate sofort erneut: 28/28, einschließlich unveränderter **500/500 Oracle-Seeds**, **A–Q 17/17**, Versandgrenzen und deterministischer Tie-Breaks. Keine abweichende kanonische Lösung.

Danach ein zusätzlicher gezielter Test: ursprüngliche und umgekehrte vollständige Teilmengenfolge gegen die neue Folge, jeweils vollständige Deals und Objective einschließlich C verglichen; 30 feste kleine Inputs und der pathologische E-Fall. Diagnostics dürfen wegen anderer Sucharbeit abweichen. Kein Zeit-Assertion-Test und keine abgeschwächte bestehende Assertion.

- T3b Runtime: **29/29**.
- T3a Oracle: **27/27**, T1/T2a/T2b: **69/69**, unverändert; enthalten in der Schutzregression.
- Relevante Inventory-/Availability-/Trade-/Legacy-/Privacy-/Receipt-/History-/Golden-Path-Regression einschließlich der Vorstufen: **474/474**, 9,626 s.
- Kanonische isolierte V21 Full Release: **992/992**, 19,770 s; 0 Failures, 0 Errors, 0 Skips. 1.004 entdeckt, unverändert 9 historische und 3 Baseline-Klassifizierungen. Zuwachs von 991 auf 992 ausschließlich durch den neuen Branch-Reihenfolge-Test.

Release-Export: `/private/tmp/sammlr-sdt3b1-final`, 2.229 allowlisted Dateien; Testfixtures mit `Scripts.prepare_release_tests` ausschließlich dort erzeugt. Ausführung mit Repository-`.venv/bin/python`, unveränderten Abhängigkeiten und `PYTHONDONTWRITEBYTECODE=1`:

```text
python3 -B -m Scripts.assemble_release --destination /private/tmp/sammlr-sdt3b1-final
python -m Scripts.prepare_release_tests
python -m Scripts.release_test_gate --cohort release
python -m unittest tests.test_sd_t3b_optimizer -q
PYTHONPATH=App python -m tests.research.benchmark_smartdeal_runtime --repeats 3
PYTHONPATH=App python -m tests.research.investigate_smartdeal_performance
```

Die ersten beiden Testbefehle laufen im isolierten Export. Vollständige temporäre Logs: `/private/tmp/sdt3b1-focused.log`, `/private/tmp/sdt3b1-regression.log`, `/private/tmp/sdt3b1-full.log`. Vorherige Runtime für Differentialdiagnose unverändert unter `/private/tmp/sdt3b1-flow-before.py`; Dateihashes im abschließenden Prüfprotokoll. Die Diagnose kompiliert instrumentierte Kopien ausschließlich im Research-Prozess und vergleicht deren Allocation mit der unveränderten jeweiligen Engine. Keine Instrumentierung im produktiven Flow-Pfad.

## Dateiumfang und Schutz

Einzige geänderte Runtime-Datei: `App/services/_smartdeal_flow.py`. Darin ausschließlich Traversal-Helfer und Einbindung der Besuchsfolge; öffentlicher Optimizer-Service, Flow-Algorithmus, Memoization, Feasibility, Bounds, D/J/C, Produktregeln und Vorgängerphasen unverändert.

Weitere Änderungen: `tests/test_sd_t3b_optimizer.py`, neue `tests/research/investigate_smartdeal_performance.py`, additive Allowlist-Zeile in `docs/R5_RELEASE_FILES.json`, dieser Bericht mit synthetischen JSONL-Messdaten, kleiner Acceptance-Nachtrag in Roadmap und historischem T3b-Bericht.

**Migration: NEIN. DB-Änderung: NEIN.** Kanonische DB bleibt V20. Read-only geprüft:

```text
SHA-256 vorher:
265de4e7cd438a8c9f2bb6673c7a020570605eed8c326e98ab4c378d2fa6d522
SHA-256 nachher:
265de4e7cd438a8c9f2bb6673c7a020570605eed8c326e98ab4c378d2fa6d522
integrity_check: ok
foreign_key_check: 0 Zeilen
```

`git diff --check`: bestanden; zusätzlich Whitespace-Prüfung aller auftragsbezogenen Dateien einschließlich untracked. Bytevergleich der geänderten Runtime und Tests mit dem isoliert getesteten Export bestanden. Die Research-Diagnose wurde nach dem Full-Gate präziser in E/G vs D/J aufgeteilt und nochmals separat ausgeführt; diese reine Messdatei ist im Export aktualisiert. Keine nachträgliche Runtime-/Teständerung.

**SD-T6a NICHT begonnen.** Keine Identity, GO, Requests, Reservation, Mutual GO, UI, Routes oder Lifecycle-Integration. Kein git add, kein Commit, kein Push, kein Deploy. STOP nach diesem Acceptance-Fix.

Prüfprotokoll der einzigen Runtime-Datei (SHA-256):

```text
vorher: fa60eac25539c2e6f821cb433d44cf3a18be99c1ea25aaa94c74d2532258baf1
nachher: 69ec13507929519bf2f7a749854becf17b94f3d5fe708014df31caef55b41dec
```

Der vollständige Dateivergleich gegen den Auftragsbeginn meldet ausschließlich die oben aufgeführten fünf geänderten und sieben neuen Dateien; keine weiteren bestehenden Dateien verändert.
