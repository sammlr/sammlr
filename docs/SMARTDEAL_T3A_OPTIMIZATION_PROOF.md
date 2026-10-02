# SmartDeal SD-T3a — Exakte Optimierungsmethode und Referenznachweis

Stand: 2026-09-11. **Research abgeschlossen; keine produktive Verdrahtung und kein Beginn von SD-T3b.** Grundlage vollständig gelesen: [Product Bible](SMARTDEAL_PRODUCT_BIBLE_V1.md), [historischer IST-Audit](SMARTDEAL_V1_IST_AUDIT.md), [geschlossener Algorithm Contract](SMARTDEAL_ALGORITHM_CONTRACT_V1.md), [Roadmap](SMARTDEAL_TECHNICAL_ROADMAP_V1.md), akzeptierte T2a-/T2b-Services und deren Tests. T1/T2a/T2b bleiben unverändert. Keine neue Produktentscheidung.

## 1. Extrahierter Vertrag

AC01–AC10: ein globaler Plan für einen Nutzer U, alle aktiven tradefähigen Alben gleichwertig, höchstens ein Deal je eligible Partner-ID, höchstens fünf Partner, jeder ausgewählte Deal mindestens 5↔5 und exakt 1:1. Keine künstliche obere Dealgröße. Partnerauswahl und sämtliche Positionsalternativen gehören zum Optimierungsraum. Kein Fokusalbum, Albumfortschrittsbonus, Rating, Entfernung oder künstlicher Wert für eine Lücke (AC16/17).

**Exakte Prioritäten aus AC12, unverändert:**

| Priorität | Ziel |
| --- | --- |
| 1 | `E = G − 2n` maximieren |
| 2 | `G` maximieren |
| 3 | `D`, absteigend sortierter Dealgrößenvektor, lexikographisch maximieren |
| 4 | `J`, numerische Partner-IDs in Ausgabeordnung AC29, lexikographisch minimieren |
| 5 | `C`, vollständige kanonische Positionsfolge AC14, lexikographisch minimieren |

AC29-Ausgabeordnung: Größe DESC, numerische Partner-ID ASC. C durchläuft die Deals in dieser Reihenfolge, innerhalb jedes Deals zuerst Incoming, dann Outgoing, jeweils Album-ID/Sticker-Code ASC. Textvergleich nach Unicode-Codepunkten; `10` vor `2`, keine Locale-/Natural-Sort-/Normalisierungsregel. Mengen werden als Stückfolge verglichen; V1-Line-Item je Empfänger/Identität maximal eins. Nach gleichem E/G ist n bereits gleich. Kein zusätzliches vorgelagertes „weniger Briefe“-Ziel.

AC02/18/19/27: freie Supply und freier Need werden aus demselben T2a-Snapshot konsumiert. Eigenexemplar, Reservations und gültig zugesagte Eingänge einschließlich Transit sind bereits berücksichtigt. Optimierung berechnet diese Werte nicht erneut und verdrängt keine Bindung. Vorschläge schreiben nichts. AC20–AC27-Lifecycle, GO, Quote drei und Fristen sind keine weiteren Optimierungsgewichte; ihre wirksamen Bindungen sind harte Eingabegrenzen. Insbesondere ist die Requestquote drei kein Top-Plan-Limit.

## 2. Formales Modell

Identität `k=(album_id, sticker_code)`; verschiedene Alben trennen gleiche Codes. Sei P die vollständige eligible Partnerliste des Snapshots. `A_U(k)` ist freie eigene ganzzahlige Supply; `A_p(k)` freie Supply des Partners; `N_U(k), N_p(k) ∈ {0,1}` sind freie Needs. Alle Größen sind endlich. Austauschbare eigene Kopien benötigen keine Stück-IDs.

`O_p` und `I_p` sind die **vollständigen**, ungekappten T2b-Kandidatenmengen für U→p bzw. p→U. Jede Kandidatenkante ist nur bei kanonischer Richtungs-/Album-Eligibility und positiver Geberkapazität/Empfängerneed vorhanden. Ihr Binärcap ist `min(A_giver(k), N_receiver(k))=1`. `available_quantity` ist Geberkapazität, nicht mehrfacher Empfängerbedarf. Insbesondere werden wiederholte eigene Supplyangaben über verschiedene Opportunities **nicht summiert**.

Variablen: `x_pk,y_pk ∈ {0,1}`, `z_p ∈ {0,1}`, ganzzahlige Dealgröße `d_p`. Außerhalb O_p/I_p sind x/y fest null.

```text
Σ_p x_pk ≤ A_U(k)                        eigene globale Supply
x_pk ≤ N_p(k)                            Bedarf des konkreten Partners
y_pk ≤ A_p(k)                            freie Gebermenge des Partners
Σ_p y_pk ≤ N_U(k)                        eigene Lücke global höchstens einmal
Σ_k x_pk = d_p = Σ_k y_pk                 1:1 für jeden einzelnen Partner
5 z_p ≤ d_p ≤ M_p z_p                    Partneraktivierung / Mindestgröße
Σ_p z_p ≤ 5                              globale Auswahl aus ALLEN Partnern
M_p = min(|O_p|, |I_p|)                  natürliche Input-Obergrenze, kein Produktlimit
G = Σ_p d_p; n = Σ_p z_p; E = G − 2n
```

Diese Constraints sind zusammen mit dem Comparator vollständig. Der leere Plan ist zulässig und hat E=G=n=0. Jeder nichtleere gültige Plan hat E≥3n>0. Supply aus künftigem Empfang finanziert keine anderen Deals. Andere Nutzer optimieren nicht gleichzeitig in diesem einen Nutzerplan; spätere atomare GO-Konkurrenz bleibt eigener Block.

## 3. Warum isoliertes Greedy nicht reicht

Konkretes synthetisches Gegenbeispiel, alle genannten Identitäten jeweils einmal frei:

- B (ID3) braucht O_B1…O_B5 und liefert I_B1…I_B5.
- C (ID4) braucht O_C1…O_C5 und liefert I_C1…I_C5.
- A (ID2) braucht alle fünf O_B plus O_C1; A liefert alle fünf I_C plus I_B1.

A hat isoliert 6↔6, B/C jeweils 5↔5. Größter zuerst nimmt A6. Danach ist B outgoing-seitig und C incoming-seitig unter der Mindestgröße. Greedy: G6/n1/E4. B5+C5 sind gemeinsam ausführbar: G10/n2/E6. A5 kann ebenfalls keinen weiteren Mindestdeal ermöglichen: entweder B verliert mindestens vier seiner fünf Outgoing-Ressourcen oder C mindestens vier seiner Incoming-Needs. Vollständiges Oracle bestätigt B+C als Optimum.

T2b darf alle drei Opportunities ausgeben; erst T3 verteilt Ressourcen. Weder fünf größte Pairwise-Pakete vorwählen noch lokale Listen vor globaler Suche abschneiden ist zulässig. Ein weiterer Test ergänzt drei disjunkte Fünferpartner: Das Optimum umfasst B,C und diese drei; die fünf isoliert besten Partner schließen dagegen einen notwendigen Partner aus.

## 4. Methodenvergleich

Determinismus in der Tabelle meint **vollständigen AC12-Comparator**, nicht nur einen festen Seed. Beta-Eignung bezieht sich auf die Messgrenzen in §10.

| Methode | Alle Constraints / global optimal? | Determinismus | Dependency / Infrastruktur | Testbarkeit / Beta / Worst Case |
| --- | --- | --- | --- | --- |
| größter Pairwise-Deal zuerst | Nein, Gegenbeispiel §3 | reproduzierbar möglich, falsches Optimum bleibt falsch | Standardbibliothek, lokal | einfach testbar; schnell, semantisch verworfen |
| vollständige Paket-/Allokationsenumeration | Ja | vollständiger Comparator | Standardbibliothek, lokal | unabhängiges kleines Oracle; kombinatorische Explosion bei großen Alternativmengen |
| Branch-and-Bound auf Aktivierung und/oder Kanten | Ja, nur mit bewiesenen Bounds und vollständigem Abschluss | Ja | Standardbibliothek möglich | oracle-testbar; Konflikte und schwache Schranken können vollständige Suche erzwingen |
| DP über Rest-Supply, belegte Needs, Partnerzahl | Ja, wenn der volle Ressourcen-/Tie-Break-Zustand erhalten bleibt | Ja | Standardbibliothek möglich | viele Zustände: mindestens Need-Teilmenge und Supply-Vektor; DP nur über G/n verliert Konfliktidentität; keine bessere allgemeine Beta-Garantie |
| MILP / ILP | Ja: obige Binärvariablen, danach exakte lexikographische Stufen | nicht allein durch Solver-Seed; alle Stufen müssen abgeschlossen und kanonisiert sein | zusätzlicher Solver oder enorme Eigenimplementierung | differential-testbar; numerische Toleranzen, Timeout/Status, native Distribution und kombinatorische Suche bleiben Risiken |
| einfacher Max-Flow / Min-Cost-Flow auf allen Partnern | Nein als alleinige Lösung: Aktivierung mit 0 oder ≥5 und fixe Briefkosten fehlen | beliebiger optimaler Flow garantiert C nicht | Standardbibliothek möglich | falsche Relaxation darf nur eine Schranke liefern |
| Matching / b-Matching | einfache unabhängige Matches bilden gekoppelte Richtungen/0-oder-5-Aktivierung nicht vollständig ab | kanonische Nachoptimierung nötig | Standardbibliothek oder zusätzliche Library | für Richtungszuweisung nützlich; allein keine vollständige Lösung |
| **vollständige Teilmengensuche mit sicheren Schranken + ganzzahlige Zirkulation + lexikographische Nachoptimierung** | **Ja**, §5–7 | **Ja**, keine Zufalls-/Floatentscheidung | **Standardbibliothek, rein im Speicher** | unabhängiger Oracle-Abgleich; gemessene einfache Beta-Fälle günstig, dichte Konkurrenz weiterhin teuer |

**Gewählt für T3b:** die letzte hybride exakte Methode. Sie trennt die kleine maximale Aktivierungszahl fünf von der Kanten-/Stückallokation; große Pakete erfordern keine Enumeration sämtlicher Stickerteilmengen. Das ist ein Modellnachweis, keine Behauptung allgemeiner niedriger Latenz.

## 5. Netzwerk für eine feste Partnerteilmenge S

Für jede Teilmenge `S⊆P`, `1≤|S|≤5`, nur deren Partner aktivieren. Dies ist ein Zweig innerhalb der globalen Suche, keine Vorauswahl der besten fünf.

Gerichtete Kanten mit ganzzahligen unteren/oberen Grenzen:

| Kante | Untergrenze | Obergrenze |
| --- | --- | --- |
| source → eigene Outgoing-Identität k | 0 | A_U(k) |
| Outgoing k → p_in, falls k∈O_p | 0 | 1 |
| p_in → p_out | 5 | M_p |
| p_out → Incoming k, falls k∈I_p | 0 | 1 |
| Incoming k → sink | 0 | 1 |
| sink → source | gewünschte Gain-Untergrenze | natürliche Gain-Obergrenze |

Flusserhaltung an p_in/p_out erzwingt exakt dieselbe Stückzahl beider Richtungen. Gemeinsame Outgoing-Knoten verteilen mehrere eigene Kopien korrekt, gemeinsame Incoming-Knoten verhindern doppelte Lückenerfüllung. Albumidentitäten bleiben Knotenlabels, ohne Gewicht. Partner-Supply≥1 ist an jeder T2b-Incoming-Kante bereits geprüft; wegen N_U≤1 genügt dort Cap1.

Eine Zirkulation mit unteren Grenzen lässt sich auf Max-Flow reduzieren: Untergrenzen abziehen, je Knoten `b(v)=eingehende Untergrenzen−ausgehende Untergrenzen`. Bei b>0 Kante Superquelle→v mit Cap b; bei b<0 Kante v→Supersenke mit Cap −b. Genau wenn alle Superquellenkanten gesättigt werden, existiert eine zulässige Zirkulation. Ganzzahlige Augmentierungen erhalten ganzzahlige Kantenwerte. Diese allgemeine Reduktion und das Integrality-Prinzip sind in den [Princeton-Lehrunterlagen zu Flow-Anwendungen](https://www.cs.princeton.edu/~wayne/kleinberg-tardos/pearson/07MaximumFlowApplications.pdf) beschrieben; die hier verwendete SmartDeal-Modellierung und der Gesamtbeweis sind eigene Ableitungen aus AC05–AC15.

Der Prototyp verwendet BFS-Augmentierung (Edmonds–Karp), ganzzahlige Residualkapazitäten und deterministische Kantenanlage. Der klassische Worst-Case-Aufwand einer Max-Flow-Prüfung ist O(V·L²) bei V Knoten und L Kanten; siehe [Princeton Algorithms: Maximum Flow](https://algs4.cs.princeton.edu/64maxflow/). Keine Gleitkommakosten oder numerisch übergroßen Ersatzgewichte.

## 6. Exakte Such- und Tie-Break-Schritte

1. Verwerfe ausschließlich Partner mit M_p<5: Sie können keinen Top-Deal erhalten. Initialer Gewinner ist leer. Durchsuche alle übrigen Teilmengen bis fünf; globales Supply-/Need-Volumen kann komplette unmögliche Partnerzahlstufen ausschließen.
2. Für S obere Gain-Schranke `U_S=min(Σ M_p, Σ_{k∈∪O_p} A_U(k), |∪I_p|)`. Wenn U_S<5|S|, ist S unmöglich. Die Schranke darf ungenau nach oben sein, niemals nach unten.
3. Weitere sichere lexikographische Schranke: `E≤U_S−2|S|`, `G≤U_S`, sortierter tatsächlicher D komponentenweise ≤ sortierten M_p; aufsteigend sortierte IDs bilden eine lexikographische Untergrenze für jedes mögliche J dieser Teilmenge. Nur wenn selbst dieses optimistische E/G/D/J nicht besser als der vollständig bekannte Gewinner sein kann, überspringen. Gleichheit von E/G/D/J fixiert bereits Partner und deren Größen; C kann anschließend gemeinsam für genau diese Zuordnung optimiert werden.
4. Prüfe grundsätzliche Zirkulationsfeasibility. Für festes S maximiert größter G zugleich E. Bestimme den maximal möglichen Gain durch monotone ganzzahlige Suche mit `sink→source`-Untergrenze g und Obergrenze U_S. **Feasible mit mindestens g** ist monoton; nicht irrtümlich eine Binärsuche über beliebige exakte Dealgrößen verschiedener Aktivierungen verwenden. Ein abschließender exakter Gesamtgain wird als untere=obere Grenze fixiert.
5. Prüfe für S sämtliche höchstens 5!=120 Partnerpermutationen. In jeder Reihenfolge maximiere nacheinander d_p durch monotone Untergrenzenprüfung bei festem G und allen zuvor exakt fixierten d. Danach d_p exakt fixieren. Bewerte den erhaltenen Größenvektor und die tatsächliche Ausgabeordnung mit D/J. Behalte global die beste E/G/D/J-Kombination.
6. Erst jetzt C minimieren: Die endgültigen Größen und Partner stehen fest. In AC29-Dealreihenfolge, jeweils Incoming vor Outgoing, Kandidaten ASC prüfen. Erzwinge die früheste Kante=1 genau dann, wenn eine zulässige Vervollständigung mit sämtlichen fixierten Größen, G und früheren Entscheidungen existiert; sonst Kante=0. Bei bereits erfüllter Richtungsgröße sind alle restlichen Kanten null. Wenn alle verbleibenden Kandidaten gebraucht werden, sind sie durch die bereits bewiesene Feasibility zwingend eins. Diese beiden Fälle sparen Prüfungen ohne alternative Lösungen zu verlieren.
7. Ausgabe kanonisieren und gegen sämtliche Ressourcen-/Need-/Balance-/Min-/Max-Partnerconstraints validieren. Kein Request, Hash-Token, Zeitstempel oder persistenter Plan wird erzeugt.

## 7. Optimalitätsargument und Determinismus

**Allokation ↔ Zirkulation:** Jede zulässige Allokation mit aktivem S erzeugt den beschriebenen ganzzahligen Flow, wobei Partnerkante=d_p und Rückkante=G. Umgekehrt liefern ganzzahlige Kandidatenkanten eines zulässigen Flows x/y∈{0,1}; gemeinsame Knoten und Partneruntergrenzen erzwingen alle AC05–AC09-Constraints. Die Zuordnung einzelner outgoing zu einzelnen incoming Stücken innerhalb eines Briefes ist nicht Bestandteil des Vertrags. Daher fügt das Netzwerk keine künstliche Paarungsregel hinzu.

**Vollständige globale Auswahl:** Jeder gültige nichtleere Plan hat eine Teilmenge S mit höchstens fünf Partnern. Sie wird untersucht oder nur mit einer bewiesenen Obergrenze ausgeschlossen, die keinen besseren Plan enthalten kann. Keine Top-5-Vorauswahl, kein Kandidatenlimit. Für festes S ist kleinerer G immer schlechteres E; die Max-G-Prüfung verliert dort keinen Gewinner.

**D/J durch Permutationen:** Betrachte einen global bestmöglichen Größenvektor und seine sortierte Ausgabeordnung π. Diese Permutation wird untersucht. Eine lexikographisch größere beschriftete Größenfolge in π würde nach absteigendem Sortieren ebenfalls einen besseren D erzeugen: am ersten erhöhten Eintrag sind alle früheren Werte unverändert und die ursprüngliche Folge war bereits absteigend. Das widerspräche der D-Optimalität. Somit wird auch die optimale Größenbelegung erreicht. Dasselbe Argument gilt für jede D-optimale Zuordnung zu Partner-IDs, einschließlich der J-minimalen. Die globale Auswertung der Permutationen findet deshalb exakt D und J, ohne sie durch numerische Gewichte zu approximieren.

**C:** Nach E/G/D/J sind Dealgrößen und Partnerzuordnung eindeutig. Jede Richtungsfolge hat feste Länge. Die früheste noch verfügbare Identität zu wählen, wenn eine optimale Vervollständigung existiert, ist genau lexikographische Minimierung; ist sie unmöglich, muss sie in jeder Vervollständigung fehlen. Induktion über alle Kanten liefert die kanonische Positionsfolge. Eine beliebige erste Max-Flow-Lösung allein genügt hierfür ausdrücklich nicht.

**Determinismus:** Vollständiger Comparator über ganze Zahlen, numerische IDs und unveränderte Unicode-Strings; keine Floating-Point-Toleranzen, Zeilenreihenfolge, Hashiteration, Uhr oder Randomness im Solver. Auch eine andere korrekte interne Flow-Suchreihenfolge ergibt nach den vollständigen lexikographischen Schritten denselben logischen Plan. Forschungs-DTOs sind eingefroren und bestehen aus Tupeln. C ist in `plan_key` eine flache Stückfolge; E/G/D/J fixieren alle Abschnittslängen, daher geht durch diese Kodierung keine Richtungs-/Dealgrenze verloren.

## 8. Unabhängiges Referenz-Oracle

[tests/research/smartdeal_oracle.py](../tests/research/smartdeal_oracle.py): vollständige rekursive Enumeration. Für jeden Partner wird Nichtauswahl sowie **jede** gleiche Incoming-/Outgoing-Teilmenge jeder Größe von fünf bis zum noch möglichen Maximum besucht. Eigene verbleibende Mengen und bereits erfüllte Needs werden branchweise geführt; alle Blätter vergleichen den vollständigen AC12-Key. Bei fünf Deals sind verbleibende Partner zwangsläufig nicht ausgewählt. Dies enumeriert jede gültige logische Allokation; ungültige Ressourcennutzung wird nicht als Kandidat erzeugt.

Das Oracle teilt Comparator/DTOs und abschließenden Planvalidator mit dem Prototyp, aber **keine Allokations-, Flow- oder Pruning-Logik**. Explizite handgeprüfte Comparator-Tests sichern die gemeinsame Zieldefinition zusätzlich. `differential(problem, candidate)` ist der wiederverwendbare Harness für eine spätere T3b-Funktion: logischen kanonischen Plan exakt vergleichen, nicht bloß G/E.

Standardlimit zwei Millionen besuchte Zustände schützt Testläufe; Überschreitung wirft `OracleLimit`, ohne einen Teilgewinner als Ergebnis zurückzugeben. `max_states=None` ermöglicht unbegrenzte Enumeration. Das Limit ist kein Produktlimit und keine probabilistische Acceptance. Große Tests wie 150↔150 laufen gegen den Prototyp mit analytisch eindeutigem Optimum, nicht mit vorgetäuschtem erschöpfendem 150-Sticker-Oracle.

[tests/research/smartdeal_flow_prototype.py](../tests/research/smartdeal_flow_prototype.py) ist der ausführbare zweite mathematische Nachweis. Kein Import durch App-Runtime, keine produktive Optimizer-Serviceklasse, keine Route. `from_snapshot` validiert vollständige T2b-Opportunities gegen denselben eingefrorenen T2a-Input und konsumiert dessen eigene globale Supply einmal. Er sammelt weder Nutzerprofile noch DB-Zugangsdaten.

## 9. Adversariale Klassen und Versandgrenzen

[tests/test_sd_t3a_optimization.py](../tests/test_sd_t3a_optimization.py) deckt alle **17 Pflichtklassen A–Q** ab:

| Klasse | Nachweis |
| --- | --- |
| A | ein Partner, exakte Fünferallokation |
| B | zwei disjunkte Partner, G10/n2 |
| C | gemeinsame outgoing Kopie nur einmal; zwei freie Kopien erlauben zwei Empfänger |
| D | derselbe Incoming-Need nur einmal, auch bei überschüssiger Supply |
| E | größter isolierter Deal zuerst ist strikt schlechter (§3) |
| F | zwei Fünferdeals schlagen isolierten Sechserdeal |
| G | A–B outgoing und B–C incoming verkettet; A+C gewinnt |
| H | sieben gleichwertige Partner → fünf kleinste IDs; zusätzlicher Fall widerlegt isolierte Top-5-Vorauswahl |
| I | 4↔4 ergibt leeren Top-Plan |
| J | 5↔5 ist zulässig |
| K | zwei Alben mit je drei Positionen ergeben einen Sechserdeal; albumweise Top-Pläne wären leer |
| L | ID2 gewinnt vor ID10, numerisch |
| M | A9 allein: E7; A5+B5: G10, aber E6. Beide Pläne sind auf demselben Input ausführbar; Versand verändert den Gewinner |
| N | mehrdeutige Positionen, Unicode-/Zahlentext-Reihenfolge, Inputpermutationen |
| O | synthetische V21-DB: T2a-Reservation entzieht Supply und Incoming-Need; keine Verwendung, veraltete T2b-Projektion abgewiesen |
| P | zehn Incoming-Kandidaten, fünf Outgoing → fünf gewählte Incoming |
| Q | zehn Outgoing-Kandidaten, fünf Incoming → fünf gewählte Outgoing |

Zusätzlich: globale Größenallokation 7+5 statt6+6 und kanonische Zuordnung an IDs2/10; drei freie Kopien desselben Outgoing-Codes an drei verschiedene Partner, jeweils Need1; Comparator-Größenfall18+12/15+15, Ausgabeordnung, Transitivität/Gleichheit; ungültige Pläne; Oracle-Limit; großer 150↔150-Deal.

**Wortlaut AC11:** „Ein zusätzlicher Trade muss mindestens zwei zusätzliche Lücken schließen.“ Für n_H>n_L gilt algebraisch `E_H−E_L=ΔG−2Δn`. Unter Schwelle gewinnt niedrigeres n, auf Schwelle gewinnt durch Stufe2 höherer G, darüber höheres E. Die sechs gezielten Grenzen prüfen zulässige Alternativen und den vollständigen Comparator:

| niedrigeres n | knapp unter Schwelle | exakt auf Schwelle | knapp darüber |
| --- | --- | --- | --- |
| 20/1, E18 | 25/4, E17: verliert | **26/4, E18: gewinnt (AC30 Case4)** | 27/4, E19: gewinnt |
| 35/2, E31 | 40/5, E30: verliert | **41/5, E31: gewinnt (AC30 Case6)** | 42/5, E32: gewinnt |

Diese großen Zahlenfälle sind explizite Comparator-Boundaries zwischen gültigen Alternativen; sie behaupten nicht, dass eine Fixture mit deren vereinigten Ressourcen keine weitere bessere Kombination zulässt. Die tatsächliche konkurrierende Gesamtoptimierung der Versandregel ist separat durch Klasse M oracle-differentiell geprüft.

**240 reproduzierbare Differentialfälle:** Seeds0–199 erzeugen ein bis drei grundsätzlich mögliche Partner, ein oder zwei Alben, freie Kopien1–3 und geteilte Needs; für alle zusätzlich umgekehrte Inputreihenfolgen in beiden Solvern. Seeds200–239 ergänzen drei Partner mit privaten Viererblöcken plus verketteten gemeinsamen Ergänzungen, sodass auch mehrere Mindestdeals gleichzeitig machbar sind. In jedem Fall vollständige Plangleichheit zum unabhängigen Oracle, nicht nur Constraints oder erwarteter Score. Seeds sind reine Testdatenerzeugung; kein Zufall im Algorithmus. Keine probabilistische Freigabe.

## 10. Komplexität und synthetische Größen

Sei p die Zahl der Top-fähigen Partner, o die Zahl relevanter eigener Outgoing-Identitäten, i die Zahl freier Incoming-Needs und m die Summe gerichteter Kandidatenkanten. Mengen>1 erhöhen Kapazität, nicht zwingend Knotenzahl; die Zahl der Needs begrenzt den Gesamtgain. Überschneidungen treiben konkurrierende Zuordnungen und die Wirksamkeit der Schranken. Große ungleiche Richtungslisten treiben insbesondere Positionsprüfungen.

Die vollständige Auswahl hat `B(p)=Σ_{j=1..min(5,p)} binom(p,j)` Zweige:

| p | nichtleere Kombinationen bis fünf |
| --- | --- |
| 10 | 637 |
| 20 | 21.699 |
| 50 | 2.369.935 |
| 99 | 75.449.319 |
| 100 | 79.375.495 |

Bei **festem** Limit fünf ist diese Anzahl polynomial O(p⁵), nicht pauschal exponentiell in p. Sie ist praktisch dennoch groß. Pro Teilmenge: O(log M) Gain-Prüfungen und im ungünstigen Fall 5!·5·O(log M) Größenprüfungen, jeweils ganzzahliger Flow. C braucht höchstens m weitere Feasibility-Prüfungen **nur für den endgültigen Gewinner**. Grobe sichere Schranke: `O((B(p)·(1+5!·5)·log(M+1)+m)·V·L²)` mit V=O(o+i+5), L=O(m+o+i+5). Der Prototyp hält keinen kompletten Potenzraum im Speicher, sondern jeweils ein Netzwerk und den Gewinner; Speicher O(o+i+m+p). Das Oracle hat dagegen Paketkombinationen `Σ_{d≥5} binom(|O_p|,d)·binom(|I_p|,d)` je Partner, über Partner multiplikativ, und ist bewusst nur für kleine Fälle gedacht.

**Messung:** ausschließlich synthetisch, Seed31001, Python3.13.15, macOS26.6.2 arm64. Drei Wiederholungen desselben Forschungsprototyps. Rohlog `/private/tmp/sdt3a-benchmark-repeated.jsonl`; reproduzierbarer Einstieg [benchmark_smartdeal.py](../tests/research/benchmark_smartdeal.py). Zeitintervalle sind Min–Max dieser drei Läufe, keine P95- oder Parallelitätsmessung.

| synthetischer Input | o / i | Ergebnis G/n | Teilmengen / Flow-Prüfungen | Sekunden |
| --- | --- | --- | --- | --- |
| Greedy-Gegenbeispiel, 3 Partner | 10 /10 | 10/2 | 6 /5 | 0,000333–0,000617 |
| ein Partner 150↔150 | 150 /150 | 150/1 | 1 /3 | 0,018327–0,018554 |
| 20 disjunkte Fünferpartner | 100 /100 | 25/5 | 21.699 /10 | 0,055899–0,057002 |
| 10 überlappende Achterpartner, zwei Alben | 27 /29 | 26/5 | 637 /5.635 | **2,332918–2,386524** |
| 100 Partner mit identischen fünf Ressourcen | 5 /5 | 5/1 | 100 /2 | 0,000596–0,000607 |

Der letzte Fall ist leicht, weil global nur ein Mindestdeal möglich ist; er beweist ausdrücklich keine allgemeine 100-Partner-Skalierung. Gleiche logische Ergebnisse und Suchzähler in allen drei Wiederholungen. Das kleine Oracle löst den Greedy-Fall in0,000235–0,000247s; kein relevanter Vergleich zu großen Flussproblemen.

Die bestehende Beta-Referenz umfasst100 Nutzer/10 Alben; höchstens99 andere Nutzer wären in diesem hypothetischen vollständigen Kandidatenpool relevant. Weder die tatsächliche Verteilung der freien Ressourcen noch der eligible Partner ist dadurch vorgegeben. Schon der dichte Zehnpartnerfall überschreitet zwei Sekunden. **Keine pauschale Closed-Beta-Latenzfreigabe, kein R4-/500ms-Nachweis.** Die Methode ist mathematisch exakt und ohne Infrastruktur betreibbar, der illustrative BFS-Prototyp ist nicht als fertiger synchroner Requestpfad empfohlen. T3b benötigt stärkere sichere Teilbaumgrenzen, Wiederverwendung von Residualnetzen und/oder effizientere ganzzahlige Flow-Implementierung sowie deklarierte dichte 20-/50-/99-Partner-Lastmessungen. Das mathematische Ergebnis darf dafür nicht vereinfacht werden.

## 11. Dependency-Entscheidung

**Keine neue Dependency für T3b empfohlen oder produktiv hinzugefügt.** Die exakte Methode ist in der Standardbibliothek konstruktiv nachgewiesen; vorhandene Requirements bleiben bytegleich. Der zusätzliche Betriebs-/Distributionsaufwand einer externen Solver-Library ist damit derzeit nicht als notwendig belegt. Render benötigt durch die Empfehlung weder neuen Solver-Binary noch separaten Dienst oder persistente Jobspeicherung.

MILP bleibt eine spätere technische Alternative, wenn Messungen den Eigenbau unvernünftig machen. Als recherchiertes Beispiel ist SCIP ein MIP/CIP-Solver mit Apache2.0 seit8.0.3; Drittkomponenten können weitere Lizenzbedingungen haben ([offizielle SCIP-Projektseite](https://www.scipopt.org/)). Das ist **keine konkrete Library-Empfehlung oder Installationsfreigabe**. Vor einer solchen Empfehlung müssen genaue Python-/Solver-Version, transitive Lizenzen, Render-Linux-/Wheel-/Build-Auswirkung, reproduzierbarer Betrieb, exakter Optimalitätsstatus und kanonische Nachoptimierung belegt werden. Ein Solver-Timeout oder „feasible“ allein ist kein AC12-Optimalitätsnachweis.

## 12. Failure Modes und konkrete Empfehlung für T3b

- Unvollständiger/veralteter T2b-Snapshot, doppelte Kandidaten oder inkonsistente Supply: geschlossen ablehnen; keine konkurrierende Availability-/Eligibility-Berechnung im Optimierer. Laufende Bindungen werden nie zur Verbesserung eines Vorschlags aufgelöst.
- Schlechte Schranke kann einen optimalen Zweig verlieren. Jede spätere Schranke separat beweisen und gegen das vollständige Oracle prüfen. Große Paketlisten dürfen nicht vorab gekürzt werden.
- Sortierte Partner-IDs sind lediglich eine optimistische J-Untergrenze, nicht die finale Ausgabeordnung. Final bleibt Größe DESC/ID ASC; C beginnt mit Incoming.
- Rechenzeit/Abbruch: kein Teilplan als „optimal“, kein stilles Greedy-Fallback, kein leerer Plan als Fehlerersatz. Das Oracle wirft bei Arbeitslimit explizit; der Forschungsprototyp hat keinen versteckten Timeout und liefert erst nach Suchabschluss. Eine spätere Betriebsschnittstelle muss unvollständigen Nachweis unterscheidbar behandeln; hier keine neue UI-/Produktentscheidung.
- Eine bewiesene Zirkulationsfeasibility setzt vollständiges Max-Flow voraus. Integerarithmetik, korrekte Residualrückkanten und Untergrenzenreduktion schützen die harten Constraints; nachträgliche Planvalidierung allein beweist keine Optimalität.
- Konkurrierende DB-Änderungen nach dem Snapshot bleiben Aufgabe späterer GO-Revalidierung. Der Plan ist keine Reservation.

T3b soll die bewiesene hybride Methode als reine Domainfunktion auf akzeptierten Snapshot-/Pairwise-Daten umsetzen, alle Zwischenstufen testbar halten und das vorhandene Oracle als unabhängige Acceptance verwenden. Forschungs-DTOs sind kein vorgezogener produktiver Payloadvertrag. Neue Allokations-DTOs können später die AC28-Felder ohne Persistenz repräsentieren. Für C und Primärziele getrennte Nachweise behalten; Ressourcenlimits müssen explizit Fehler statt approximativer Ergebnisse liefern. Vor Nutzung im Requestpfad die genannten Performance-Risiken messen und lösen. Kein T3b-Code in diesem Auftrag.

## 13. Regression und Schutz

27 neue T3a-Tests bestanden. Alle17 Pflichtklassen, sechs Versandgrenzen,240 feste Differential-Seeds, Permutationen und Oracle-Invarianten grün. Unveränderte Foundationtests: T1 **18/18**, T2a **29/29**, T2b **22/22**; zusammen mit T3a **96/96**. Relevante Inventory-/Availability-/Reservations-/Privacy-/Block-/Pool-/Trade-/Legacy-/History-/Notification-/R3-/S21-Regression **371/371**.

**Kanonische Full Release: 963/963 bestanden**,0 Failures/Errors/Skips,975 entdeckt. Bestehende neun historische und drei Baseline-Klassifikationen unverändert. Testausführung in `/private/tmp/sammlr-sdt3a-candidate`, Allowlist-Export2224 Dateien; ausschließlich synthetische DBs. Produktions-/Bootstrapziel V20 bleibt unverändert; V21-Migrationstests verwenden temporäre Datenbanken. Finaler Interpreter: vorhandenes Repository-venv, Python3.13.15, alle14 exakten Requirements-Pins geprüft; keine Installation oder Requirementsänderung.

Logs: `/private/tmp/sdt3a-foundations-final.log`, `/private/tmp/sdt3a-regression.log`, `/private/tmp/sdt3a-full.log`. Bytevergleich der getesteten Research-/Testdateien mit dem Worktree bestanden. Vorbestehende Tests, gesamte App-Runtime, T1/T2a/T2b, Migration0021 UP/DOWN, Product Bible, Algorithm Contract, IST-Audit und Requirements unverändert. Nur fünf neue Research-/Testdateien, dieses Nachweisdokument, additive Release-Allowlist-Einträge und die minimale Roadmap-Notiz gehören zu diesem Auftrag. Vorbestehender dirty Worktree bleibt erhalten.

Kanonische App-DB SHA-256 **vorher = nachher**:

```text
265de4e7cd438a8c9f2bb6673c7a020570605eed8c326e98ab4c378d2fa6d522
```

`integrity_check=ok`, `foreign_key_check=[]`, `git diff --check` bestanden; zusätzliche Whitespace-Prüfung aller neuen Dateien bestanden. DB nur read-only geprüft, nicht migriert. Vollständiger auftragsbezogener Dateihashvergleich basiert auf `/private/tmp/sdt3a-before.json`.

**SD-T3a abgeschlossen.** Algorithm Contract vollständig modellierbar; exakte Methode, Optimalitäts-/Determinismusargument, unabhängiges Oracle, adversariale Tests und Machbarkeitsgrenzen nachgewiesen. Kein allgemeiner Beta-Performance-Gate behauptet. SD-T3b nicht begonnen; kein produktiver Optimierer, kein Request/GO/Reservation, keine UI/Route, keine Migration, kein git add, Commit, Push oder Deploy. **STOP.**
