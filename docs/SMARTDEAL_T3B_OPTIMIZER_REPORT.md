# SmartDeal SD-T3b — Runtime-Optimierer und Performance-Abnahme

**Nachtrag 3b.1: Acceptance jetzt GREEN; siehe [Performance-Untersuchung](SMARTDEAL_T3B1_PERFORMANCE_INVESTIGATION.md). Der folgende Bericht dokumentiert den Stand vor dem Fix.**

Stand: 2026-09-11. **Umgesetzt: JA. Acceptance: YELLOW — correctness-green / performance-yellow.**

Der interne read-only Domain-Service implementiert das exakte T3a-Verfahren. Die vorhandenen500 deterministischen Oracle-Fälle und alle17 Pflichtklassen sind grün. Der gemischte20-Partner-Fall bleibt jedoch mit2,15–2,16s deutlich oberhalb des500ms-Ziels. Gemäß expliziter Performance-Stop-Regel des SD-T3b-Auftrags bleibt die korrekte Implementierung erhalten; keine Heuristik, keine Produktregeländerung und keine Aktivierung. **STOP zur PO-/Architekturentscheidung. SD-T6a nicht begonnen.**

Vollständig gelesene Grundlagen: [Product Bible](SMARTDEAL_PRODUCT_BIBLE_V1.md), [Algorithm Contract](SMARTDEAL_ALGORITHM_CONTRACT_V1.md), [Roadmap](SMARTDEAL_TECHNICAL_ROADMAP_V1.md), [T3a-Nachweis](SMARTDEAL_T3A_OPTIMIZATION_PROOF.md), akzeptierte T2a/T2b-Services sowie sämtliche vier vorgegebenen Research-/Testartefakte. T1, T2a, T2b und T3a sind LOCKED und unverändert.

## 1. Architektur und Scope

Öffentliche interne Domain-API: [SmartDealOptimizer.optimize(state, opportunities)](../App/services/smartdeal_optimizer.py). Sie erhält genau einen kanonischen `PlanningState` und die **vollständigen** `PairwiseOpportunity`-Tupel desselben Snapshots. Kein Connection-Argument, keine SQL-Abfrage, keine Inventory-/Privacy-/Availability-Neuberechnung. Kein IO im Optimierungspfad.

Der private Motor [services/_smartdeal_flow.py](../App/services/_smartdeal_flow.py) verwendet ausschließlich Standardbibliothek. Weder Domain-Service noch Motor importieren Research-/Testcode. Bestehende Services, SmartMatch, Requests, Routes und Lifecycle werden nicht umgeschaltet. Keine neue Dependency, Migration, Tabelle, gespeicherte Suggestion oder Opportunity-ID.

Die kanonischen Eingaben werden auf strukturelle Konsistenz geprüft: eigene freie Supply und binäre Needs, physisches Missing vs gebundene Eingänge, eindeutige eligible Partner, Album-/Katalog-/Mitgliedschaftsbezug, einzigartige binäre Kandidaten, übereinstimmende eigene Supplymengen, Partner-Mitgliedschaft und T2b-Maximum/Albumprojektion. Widersprüche werfen `SmartDealOptimizationError`.

**Vertrauensgrenze:** Dies ist ein interner Snapshot-Consumer, kein Validator beliebiger Clientdaten. Ohne die vollständigen Partnerinventare kann er nicht erkennen, ob ein Aufrufer eine ganze gültige Opportunity oder eine konsistent gekürzte Alternative weggelassen hat. Der Aufrufer muss das ungekürzte Ergebnis des akzeptierten T2b-Service aus demselben `build_pairwise_inputs`-Snapshot übergeben. Der Optimierer erfindet keine zusätzliche DB-/Privacy-Wahrheit, keine Snapshot-ID und keine T6a-Identität. Er erkennt konkret widersprüchliche Mischstände, beansprucht aber keine spätere GO-Revalidierung.

Alle Ergebnisse sind eingefrorene Dataclasses mit Tupeln:

| Domainobjekt | Inhalt |
| --- | --- |
| SmartDealPiece | album_id, sticker_code, quantity=1 nach V1-Need-Cap |
| SmartDealCandidate | partner_id, outgoing_pieces, incoming_pieces, piece_count, involved_albums |
| SmartDealObjective | efficiency E, total_gain G, trade_count n, deal_sizes D, partner_ids J, positions C |
| SmartDealDiagnostics | untersuchte Teilmengen, sichere Ausschlüsse, Flow-Prüfungen, Cachetreffer, Größenpermutationen |
| SmartDealPlan | deals, objective, diagnostics |

Ein Deal entspricht einer Sendung nach dem bestehenden AC11-Modell; Briefmetrik n und E liegen in `objective`, keine neue Kosten-/Adress-/Versandart. Diagnostics enthalten nur deterministische Zähler, keine Uhrzeiten, Laufzeiten oder prozessabhängigen Werte. Sie sind keine Rankinggewichte.

## 2. Exakte Zielhierarchie und Allokationsvertrag

Unverändert AC12:

1. `E=G−2n` maximieren.
2. `G=Σ d_p` maximieren.
3. `D`, absteigend sortierte Größen, lexikographisch maximieren.
4. `J`, numerische Partner-IDs **in Ausgabeordnung**, lexikographisch minimieren.
5. `C`, vollständige Positionsfolge, lexikographisch minimieren.

Ausgabe: Größe DESC, dann Partner-ID ASC. C: pro Deal Incoming vor Outgoing, Album-ID/Code nach Unicode-Codepunkten ASC. Mengen zählen als Stücke; V1 erlaubt je Empfänger/Identität maximal ein Stück. Supply-Kopien können verschiedene Partner versorgen. Keine natürlichen Codezahlen, Locale-Sortierung, Albumgewichtung, Partnerqualität oder Floating-Point-Ersatzgewichte.

Harte Constraints: höchstens fünf ausgewählte Partner aus **allen** T2b-Opportunities, jeder Deal mindestens5 und exakt dieselbe Incoming-/Outgoing-Stückzahl. Eigene Supply wird global mengenbasiert begrenzt, eigene Needs global höchstens einmal erfüllt. Partnerkanten sind bereits durch deren freie Supply bzw. binären Need begrenzt. Keine Doppelverplanung. Kein künstliches Dealmaximum. Der leere Plan ist nur bei tatsächlich fehlender zulässiger Top-Allokation ein korrektes Ergebnis.

Nach abgeschlossener Suche prüft ein eigener Postcondition-Schritt nochmals alle ausgewählten Kanten, Partner, Größen, globalen Supplymengen und Incoming-Need-Caps. Ungültiges Resultat wird nicht ausgegeben. Dieser Validator ergänzt den Suchbeweis; er ersetzt keine Optimalitätsprüfung.

## 3. Übernahme der T3a-Methode

Für jede mögliche aktive Teilmenge S mit1…5 Partnern entsteht das T3a-Netz:

```text
source → eigene Outgoing-Identität k       [0, A_U(k)]
Outgoing k → p_in                         [0, 1], nur T2b-Kandidaten
p_in → p_out                              [5, M_p]
p_out → Incoming k                        [0, 1], nur T2b-Kandidaten
Incoming k → sink                         [0, 1]
sink → source                             [Gain-Untergrenze, Gain-Obergrenze]
```

`M_p=min(|O_p|,|I_p|)` ist die natürliche Inputgrenze, kein neues Produktlimit. Flusserhaltung an der Partnerkante erzwingt1:1. Gemeinsame Identitätsknoten erzwingen globale Ressourcenknappheit. Knotenidentität umfasst das Album. Untergrenzen werden durch Knotensalden und Superquelle/-senke reduziert; vollständige ganzzahlige Max-Flow-Prüfung entscheidet Feasibility.

Für festes S ist höherer G zugleich höheres E. Monotone Suche über „mindestens g“ bestimmt den maximalen G; danach wird G exakt fixiert. Alle höchstens120 Partnerpermutationen werden zur lexikographischen Größenmaximierung geprüft. Die aus ihnen resultierenden D/J werden global verglichen. Erst nach eindeutigem E/G/D/J wird C über kanonische Kantenpräfixe minimiert: früheste Kante genau dann auswählen, wenn eine optimale Vervollständigung weiterhin möglich ist.

**Optimalität:** Jede gültige Allokation gehört zu einer untersuchten oder beweisbar unterlegenen Teilmenge. Allokation und ganzzahlige Zirkulation entsprechen einander. Die Maximierung je Teilmenge und alle Größenpermutationen finden E/G/D/J gemäß T3a-Beweis §§5–7. Präfix-Feasibility liefert danach die exakte C-Minimierung. Alle zusätzlichen Einsparungen unten erhalten diesen Lösungsraum. Jeder zurückgegebene Plan ist damit für den vollständigen kanonischen Input global optimal; kein vorläufiger Suchgewinner wird veröffentlicht.

## 4. Sichere Optimierungen und Pruning-Beweise

| Regel | Warum kein besserer Plan verloren geht |
| --- | --- |
| M_p<5 ausschließen | Partner kann die harte Mindestgröße unter keiner Allokation erreichen. |
| Partnerzahl ≤ floor(globales Gain-Upper/5) | Jeder aktivierte Partner benötigt mindestens fünf freie Incoming-/Outgoing-Einheiten. |
| `U_S=min(Σ M_p, freie Supply der Outgoing-Union, Größe der Incoming-Union)` | Alle drei Terme sind notwendige Gain-Obergrenzen, keine erreichbaren Gewinne vorgaukelnden Untergrenzen. U_S<5|S| beweist Unmöglichkeit. |
| Optimistische E/G/D/J-Schranke | E/G aus U_S sind obere Grenzen; sortierte M_p begrenzen die sortierten tatsächlichen Größen komponentenweise. Numerisch sortierte IDs sind eine untere lexikographische Grenze jeder möglichen J-Ausgabe. Nur nachweisbar nicht bessere Zweige werden verworfen. |
| Gleiches E/G/D/J nicht erneut suchen | Diese Werte bestimmen bereits Partner und beschriftete Größen eindeutig. Die vollständige C-Suche für genau diesen Gewinner erfolgt anschließend. |
| Fester Gain + noch aktive Partner | Bei Restgain R und r späteren Partnern ist d_p≤R−5r; außerdem d_p≥R−Σ M_später. Diese algebraischen Grenzen gelten für jede Vervollständigung. |
| Maximalschranke einmal testen | Falls die höchste Schranke erreichbar ist, ist kein Binärsuchschritt nötig. Falls nicht, wird die bereits widerlegte Schranke nicht erneut getestet. |
| Memoization vollständiger Feasibility-Zustände | Cache je festem Teilmengennetz, Key aus **allen** Partner-Unter-/Obergrenzen und Gain-Grenzen. Exakt dasselbe Problem hat dieselbe Feasibility. Keine übergreifende Restzustands-/Partnerannahme. Bei C mit fixierten Kanten wird dieser Cache ausdrücklich nicht benutzt. |
| Kanonische Integer-Topologie wiederverwenden | Nur unveränderte Knoten-/Kantenstruktur wird je Teilmenge vorgebaut. Jede tatsächliche Prüfung erhält frische Residualkapazitäten und Knotensalden. Keine unzulässige Übernahme eines vorherigen Flusses. |
| Ganzzahliger Dinic-Flow | BFS-Level und vollständige blockierende Augmentierungen ersetzen einzelne BFS-Pfade. Integrale Kapazitäten, Residualrückkanten und vollständiger Suchabschluss erhalten dieselbe Feasibility. Keine Näherung. |
| Erzwungene C-Kanten | Ist Richtungsgröße erreicht, müssen verbleibende Kanten null sein. Werden alle verbleibenden Kandidaten benötigt, müssen alle eins sein. Zuvor bewiesene Feasibility des Präfixes bleibt erhalten. |

Keine Dominanzregel nach isolierter Dealgröße, keine Top-5-Vorauswahl, kein Album- oder Partnerfilter außerhalb des kanonischen Inputs, kein Timeout-Greedy. Die Teilmengensuche ist weiterhin vollständig mit bewiesenen Schranken. Die durch Zahlenbegrenzung ausgeschlossenen Werte können in keiner gültigen Lösung vorkommen.

## 5. Oracle- und Contract-Gate

Das akzeptierte [T3a-Oracle](../tests/research/smartdeal_oracle.py) sowie Prototyp, Benchmarks und T3a-Tests bleiben bytegleich. Runtime verwendet weder deren Comparator noch deren Validator oder Dataclasses. Der neue Testadapter übersetzt synthetische Oracle-Graphen verlustfrei in kanonische T2a-Daten und ruft den **echten T2b-Service** zur Kandidatenerzeugung auf. Danach Runtime ausführen und vollständige logische Allokation sowie E/G/D/J/C vergleichen.

**500/500 feste Differential-Seeds bestanden.** Seeds0–239 reproduzieren exakt die Generatoren aus T3a; Seeds240–499 ergänzen drei konkurrierende Partner mit privaten Viererblöcken, geteilten Ergänzungen, freien Kopien1–2 und IDs2/10/17. Kein veränderter Oracle-Expected-Wert, kein Score-only-Vergleich. Für alle500 zusätzlich umgekehrte Inputreihenfolgen; vollständiger Plan einschließlich Diagnostics identisch. Getrennte Prozesse mit PYTHONHASHSEED0/1/731 erzeugen identische serialisierte Ergebnisse.

**Pflichtklassen A–Q:17/17 bestanden**, erneut gegen Runtime. Die16 reinen T3a-Klassen verwenden ihre unveränderten Fixtures und Assertions über den Runtime-/Oracle-Adapter. Klasse O verwendet eine echte temporäre V21-Datenbank mit akzeptiertem T2a/T2b-Reader. Eigene gebundene Supply und zugesagter Incoming-Need sind nicht nutzbar; widersprüchliche alte Opportunities scheitern geschlossen.

Greedy-Gegenbeispiel: greedy G6/n1/E4, erwartetes Optimum G10/n2/E6, **Runtime tatsächlich G10 mit Partnern3 und4, jeweils5↔5**. Außerdem geprüft: konkurrierende Outgoing-/Incoming-Identitäten, mehrere freie Kopien für verschiedene Partner, verkettete Konflikte, globale Auswahl jenseits isolierter Top5,4er-Ausschluss/5er-Zulassung, Größen7+5 statt6+6 und numerische/Unicode-Tie-Breaks.

**Versandregel vollständig:** Die sechs akzeptierten T3a-Boundaries werden mit vom produktiven Optimierer erzeugten Plan-Objectives erneut verglichen:

| Basis | unter Schwelle | exakt | über Schwelle |
| --- | --- | --- | --- |
| 20/1 | 25/4 verliert | **26/4 gewinnt, Case4** | 27/4 gewinnt |
| 35/2 | 40/5 verliert | **41/5 gewinnt, Case6** | 42/5 gewinnt |

Wie im gesperrten T3a-Nachweis sind diese sechs Zahlenfälle Vergleiche gültiger Alternativen; daraus wird kein erfundener vollständiger Konfliktgraph mit ausschließlich diesen Alternativen behauptet. Zusätzlich laufen drei echte konkurrierende globale Inputs gegen Oracle und Runtime: A9 gegen A5+B5 (Zusatzgain1, Einzeldeal gewinnt), A8 gegen A5+B5 (exakt+2, zwei Deals gewinnen), A7 gegen A5+B5 (+3, zwei Deals gewinnen). Somit sind Comparator und tatsächliche Suchentscheidung geprüft.

Weitere Nachweise:28↔28 über vier Alben,150↔150 ohne künstliches Maximum, leerer Input, unilateraler Partner, ausschließlich kleine Opportunities, tiefe Unveränderlichkeit des Ergebnisses, unveränderte Eingaben, verworfene inkonsistente Mengen/IDs/Alben/Kandidaten, injizierter interner Fehler ohne Fallback, null SQL und null DB-Mutationen einschließlich Fehlerpfad. Keine Runtime-Imports aus `tests`.

## 6. Performance-Gate A–F

Reproduzierbarer Einstieg: [tests/research/benchmark_smartdeal_runtime.py](../tests/research/benchmark_smartdeal_runtime.py). Neue Datei, bestehender T3a-Benchmark unverändert. Seeds31001 (T3a-dicht),32001 (gemischt),33001 (Stress). Python3.13.15, macOS26.6.2 arm64. Drei vollständige Wiederholungen pro Fall, gleiche Ergebnisinhalte und Suchzähler. Messung umfasst Eingabevalidierung, Optimierung und Output-Aufbau; synthetische Fixture-/T2a-/T2b-Erzeugung vorher, keine DB-/HTTP-Zeit enthalten. Keine Parallelitäts- oder P95-Aussage.

| Fall | Partner; eigene Outgoing-Identitäten / Incoming-Needs | Ergebnis G/n | Lauf1 / Lauf2 / Lauf3, ms |
| --- | --- | --- | --- |
| A kleiner Normalfall, disjunkt8+6 | 2;14/14 | 14/2 | **0,284 /0,211 /0,264** |
| B mittlerer Normalfall, disjunkt10…14 | 5;60/60 | 60/5 | **6,021 /5,536 /5,305** |
| C viele disjunkte Zehnerpartner | 20;200/200 | 50/5 | **85,798 /85,781 /85,644** |
| D exakt der dichte T3a-Zehnpartnerfall | 10;27/29 | 26/5 | **48,291 /50,188 /48,370** |
| E gemischte Überlappungen: je vier private und vier geteilte Kandidaten pro Richtung, vier Alben | 20;118/116 | 40/5 | **2.152,326 /2.157,471 /2.159,049** |
| F größerer dichter Stressfall, je acht Kandidaten pro Richtung | 25;30/30 | 28/5 | **454,399 /455,901 /453,379** |
| Zusatz G großer Einzeldeal | 1;150/150 | 150/1 | **1,054 /0,998 /1,006** |

Alle Fälle sind synthetisch; „Normalfall“ und „gemischt“ beschreiben deklarierte Lastklassen, keine erhobene Verteilung realer Nutzerinventare. Das Gemisch aus privaten und gemeinsamen Ressourcen ist ein plausibles Beta-Szenario, keine Aussage über tatsächliche Häufigkeit. D übernimmt dieselbe Eingabe wie T3a und verbessert deren2,33–2,39s deutlich. G nutzt denselben150er-Umfang. C nutzt hier20×10, T3a20×5; die C-Zeiten dürfen nicht als identischer Vorher-/Nachher-Vergleich ausgegeben werden.

Langsamster realistischer Testfall: **E, maximal2.159,049ms**. Langsamster ausdrücklich deklarierter Stressfall: **F, maximal455,901ms**. Mehr Partner bedeuten nicht zwingend mehr Suchzeit: starke globale Knappheit kann sehr viele Teilmengen früh ausschließen, während größere gemischte Ressourcenunionen lange konkurrenzfähig bleiben.

| Fall | Teilmengen | sicher ausgeschlossene | Flow-Prüfungen | identische Prüfungen aus Cache | Größenpermutationen |
| --- | --- | --- | --- | --- | --- |
| A | 3 | 1 | 4 | 0 | 3 |
| B | 31 | 6 | 50 | 0 | 301 |
| C | 21.699 | 21.694 | 10 | 0 | 153 |
| D | 637 | 611 | 410 | 540 | 465 |
| E | 21.699 | 21.332 | 12.647 | 86.655 | 25.089 |
| F | 68.405 | 68.318 | 2.100 | 2.883 | 1.661 |
| G | 1 | 0 | 2 | 0 | 1 |

Rohlog: `/private/tmp/sdt3b-benchmark-final.jsonl`. Gemäß Performance-Stop-Regel bleibt **Acceptance YELLOW**. Keine weitere Umstellung auf Heuristik, kein verborgenes Kandidatenlimit und keine stillschweigende Lockerung von E/G/D/J/C. Der Domain-Service ist noch an keine Nutzerroute angeschlossen. Ein allgemeiner Closed-Beta-/R4-Performance-Gate ist nicht erfüllt.

## 7. Worst Case und bekannte Grenzen

`Σ_{j=1..5} binom(p,j)` mögliche aktive Teilmengen; bei p=20 sind es21.699, bei p=50 bereits2.369.935, bei p=99 insgesamt75.449.319. Bei festem Limit fünf O(p⁵), praktisch dennoch groß. Die sicheren Schranken müssen nicht scharf sein. Pro konkurrenzfähiger Teilmenge fallen ganzzahlige Gain-Suche und bis120 Größenpermutationen an. Der Feasibility-Cache beseitigt nur identische Zustände; für unterschiedliche Grenzen bleibt vollständiger Flow nötig. C wird nur für die global gewinnende Partner-/Größenzuordnung nachoptimiert.

Der Motor speichert keine vollständige Teilmengenliste. Topologie und Cache gehören je zu einem Teilmengennetz; höchstens aktuelles Netz und bisheriges Gewinnernetz werden gehalten. Cachegröße hängt von den tatsächlich geprüften Kombinationen der höchstens fünf Größenintervalle ab. Kein persistenter oder prozessglobaler Cache, keine Cross-Snapshot-Wiederverwendung. Sehr große ungleiche Kandidatenlisten erhöhen auch C-Prüfungen. Kein allgemeiner50-/99-Partner-Latenznachweis aus den leichteren Fällen abgeleitet.

Die Flussprüfung beendet sich erst bei vollständiger Feasibility-Entscheidung. Kein konfiguriertes Zeit-/Arbeitslimit und keine partielle Rückgabe. Ein interner Fehler propagiert als Exception; Validierungsfehler sind Domain-Exceptions. Da weder DB noch Schreibdienste erreichbar sind, kann auch ein Abbruch keine Teilreservation oder Bestandsänderung verursachen. Das ersetzt keine spätere Betriebsentscheidung zum CPU-/Request-Zeitbudget.

Erforderlicher nächster **Entscheidungspunkt**, hier nicht umgesetzt: Umgang mit dem nachgewiesenen realistischen2,16s-Fall und Architektur/Performance der exakten Suche. Mathematisch sichere weitere Bounds oder Flow-Wiederverwendung wären gesondert zu beweisen. T3a-Contract, Oracle und Produktregeln bleiben maßgeblich. Neue Dependency ist derzeit weder hinzugefügt noch vorgeschlagen. SD-T6a bleibt gesperrt.

## 8. Tests, Release und Dateischutz

Neue Runtime-Testdatei: **28/28 bestanden**, darin500 feste Differentialfälle,17 Pflichtklassen, sechs T3a-Comparator-Boundaries und drei echte globale Versandkonkurrenzen. Unveränderte Vorstufen: T1 18, T2a29, T2b22, T3a27, insgesamt96 Tests. Alle in der fokussierten Schutzregression enthalten.

**Fokussierte Regression:473/473 bestanden.** Umfasst zusätzlich Inventory/Availability/Guard/Reservations, Privacy/Blocks/Tradepool, bestehendes SmartMatch/Market Coverage, Requests, Shipping/Receipt/Problems/Completion, History/Notifications, Account-Schutz und R3 Golden Path. Keine Tests abgeschwächt oder zusätzlich ausgeschlossen.

Isolierter vollständiger Allowlist-Export: `/private/tmp/sammlr-sdt3b-final`,2228 Dateien. Synthetische Testdaten mit unverändertem `Scripts.prepare_release_tests` vorbereitet. Interpreter: vorhandenes Repository-venv, keine neue Installation. Kanonische App-DB bleibt V20; Migrationstests ausschließlich gegen temporäre V21-Datenbanken. Logs `/private/tmp/sdt3b-focused.log`, `/private/tmp/sdt3b-regression.log`, `/private/tmp/sdt3b-full.log`.

**Full Release Suite:991/991 bestanden**,0 Failures/Errors/Skips,1.003 entdeckt. Unveränderte Kohortentrennung: neun historische und drei Baseline-Tests separat klassifiziert. Kein neuer Ausschluss. Runtime-/Test-/Benchmark-Dateien und Release-Allowlist sind bytegleich mit dem final getesteten Export.

Kanonische lokale App-DB SHA-256 **vorher = nachher**:

```text
265de4e7cd438a8c9f2bb6673c7a020570605eed8c326e98ab4c378d2fa6d522
```

`PRAGMA integrity_check`: **ok**. `PRAGMA foreign_key_check`: **0 Zeilen**. DB nur read-only geprüft, nicht migriert. `git diff --check` sauber; zusätzliche Whitespace-Prüfung der neuen untracked Dateien bestanden. Auftragsbezogenes SHA-Manifest `/private/tmp/sdt3b-before.json` schützt den vorbestehenden dirty Worktree; sämtliche Bestandsdateien außer Release-Allowlist und minimaler Roadmap-Notiz sind unverändert.

Exakte Auftragsdateien:

- Neu: `App/services/smartdeal_optimizer.py` — Domain-API, immutable Output, Konsistenz-/Postcondition-Prüfung.
- Neu: `App/services/_smartdeal_flow.py` — privater exakter Allokationsmotor.
- Neu: `tests/test_sd_t3b_optimizer.py` —28 Runtime-/Oracle-/Snapshot-/Failure-Safety-Tests.
- Neu: `tests/research/benchmark_smartdeal_runtime.py` — A–F plus150er-Zusatzmessung.
- Neu: `docs/SMARTDEAL_T3B_OPTIMIZER_REPORT.md` — dieser Bericht.
- Additiv geändert: `docs/R5_RELEASE_FILES.json` — vier neue Runtime-/Test-/Benchmark-Dateien.
- Minimal geändert: `docs/SMARTDEAL_TECHNICAL_ROADMAP_V1.md` — T3b-Status und Nachweislink.

**Bestehende Runtime-Dateien unverändert; nur zwei neue Domainmodule.** Keine Änderung von T1/T2a/T2b/T3a, deren Tests/Oracle/Nachweisen, Product Bible, Algorithm Contract, Migrationen, Requirements oder bestehenden Legacy-Verträgen.

**SD-T3b umgesetzt; Acceptance YELLOW.** Globales Optimum, globale Max5-Auswahl,1:1, Ressourcen-/Need-Konsistenz, Versandregel und Determinismus sind nachgewiesen. Performance im plausiblen gemischten Fall noch nicht ausreichend. Kein weiterer Block: **SD-T6a nicht begonnen**, keine Opportunity Identity, kein Request, GO, Reservation oder Mutual GO, keine UI oder sichtbare Route. Kein git add, Commit, Push oder Deploy. **STOP gemäß Performance-Stop-Regel zur PO-/Architekturentscheidung.**
