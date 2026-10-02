# S21 Preflight – Konfliktfreie Top-Match-Optimierung

Stand: 2026-08-06
Status: Preflight abgeschlossen; offene Entscheidungen am 2026-08-06 durch
Product Owner verbindlich geklärt

## Verbindlicher Titel

**S21 – Konfliktfreie Top-Match-Optimierung**

## Abhängigkeiten

- S19 – Shared Availability Snapshot
- S20 – Markt- und persönliche Trade-Abdeckung

S19 liefert die gemeinsame, erklärbare und read-only Verfügbarkeitsquelle.
S20 liefert getrennte Community- und persönliche Coverage-Erklärdaten. S21
darf diese Grundlagen verwenden, aber keine zweite Availability- oder
Coverage-Berechnung einführen.

## Fachliches Ziel

S21 soll bis zu drei gemeinsam optimierte, konfliktfreie Smart-Trade-Pakete
erzeugen. Begrenzte effektiv verfügbare Sticker dürfen über die gesamte
Auswahl niemals mehrfach verplant werden. Das Ergebnis soll deterministisch,
begrenzt und erklärbar auf möglichst großen Sammlungsfortschritt bei möglichst
wenigen Trades optimieren.

## Bekannte Risiken

- kombinatorisch stark wachsender Suchraum bei hoher Partner- und Codezahl
- scheinbar attraktive Einzelmatches können eine bessere Gesamtkombination
  blockieren
- doppelte Verplanung desselben verfügbaren Exemplars über mehrere Partner
- nicht reproduzierbare Ergebnisse ohne vollständig definierte Tie-Breaks
- schwer erklärbare Auswahl bei konkurrierenden Zielfunktionen
- veraltete Snapshots zwischen Berechnung und späterer Anfrage
- Vermischung von S21-Vorschlägen mit S22-Anfrage- und Reservierungsregeln

## Zwingende Invarianten

- Datengrundlage sind ausschließlich S19-Snapshots und S20-Erklärdaten.
- Derselbe effektiv verfügbare Sticker beziehungsweise dieselbe begrenzte
  Menge wird niemals mehrfach verplant.
- `reserved`, `incoming_transit` und `outgoing_transit` werden ausschließlich
  gemäß S19 berücksichtigt.
- Das Ergebnis umfasst höchstens drei Kandidaten.
- Gleiche fachliche Eingabe erzeugt dasselbe Ergebnis.
- Jedes Paket und die Gesamtauswahl besitzen nachvollziehbare Erklärdaten.
- Die vollständige manuelle Partnerliste und der manuelle Dealwizard bleiben
  unverändert nutzbar.
- S21 liest und plant nur; Anfrage, Reservierung und Lifecycle-Änderung gehören
  nicht in diesen Sprint.
- Die Optimierung bleibt innerhalb eines Albums.

## Ausdrücklich nicht enthalten

- frei wählbare Optimierungsstrategien
- Reputation-, Bewertungs-, Zuverlässigkeits- oder Nähe-Ranking
- albumübergreifende Trades
- Smart-Trade-Anfragen, Anfrage-Limits oder Ablaufzeiten
- Reservierung beim Vorschlag
- automatische Angebote oder Statusänderungen
- dynamische Paketverkleinerung und Zustimmungslogik
- neue Trade-, Versand-, Empfangs- oder Problemlogik
- UI- oder Designentscheidungen außerhalb ausdrücklich freigegebenen S21-Scopes

## Offene Product-Owner-Fragen

Die vorhandene Roadmap und Product Bible legen die folgenden Details nicht
abschließend fest. Sie dürfen nicht beiläufig durch Implementierung entschieden
werden:

1. Ist die Zielfunktion lexikografisch – zuerst maximaler Fortschritt, danach
   minimale Tradeanzahl – oder darf weniger Fortschritt für deutlich weniger
   Sendungen akzeptiert werden? Die Product Bible nennt 75 Sticker in drei
   Sendungen gegenüber 80 in acht als mögliches Beispiel, definiert aber keine
   Gewichtung.
2. Welche vollständige Tie-Break-Reihenfolge gilt nach Fortschritt und
   Tradeanzahl, damit Partner- oder Datenbankreihenfolge kein Produktverhalten
   bestimmt?
3. Was ist das verbindliche Performancebudget und welche Nutzer-/Stickerzahl
   bildet die „realistische Fixture“ der Definition of Done?
4. Welche konkrete Fixture und welches vollständige erwartete Ergebnis bilden
   das Roadmap-Regressionsbeispiel `GER17`?
5. Bedeutet „Top-3-Kandidaten“ drei einzelne Partnerpakete in einer gemeinsam
   optimierten Auswahl oder bis zu drei alternative Gesamtlösungen? Die
   Beispiele sprechen für drei Partnerpakete, die Formulierung ist jedoch
   nicht formalisiert.

## Verbindliche Auflösung

Der Product Owner hat am 2026-08-06 entschieden:

- lexikografische Zielfunktion in der Reihenfolge Fortschritt, Partnerzahl,
  Abgabemenge, redundanter Empfang, persönliche S20-Abdeckung, Partner-IDs,
  Codelisten,
- weniger Fortschritt darf nie zugunsten weniger Trades gewählt werden,
- Top 3 sind höchstens drei gleichzeitig ausführbare Partnerpakete einer
  gemeinsam optimierten Gesamtlösung,
- GER17 darf höchstens einmal verplant werden; danach gelten Beitrag,
  Abgabemenge und Partner-ID,
- Referenzlast 1.000 Codes, 100 Partner, 100 relevante Codes je Partner;
  Kernbudget 500 ms, vollständiger Performancetest 2 Sekunden,
- kein Caching.

Diese Auflösung ist in
[`s21-conflict-free-top-match-optimization.md`](s21-conflict-free-top-match-optimization.md)
vollständig in den ausführbaren Vertrag überführt.

## Vorgeschlagene Testmatrix

| Bereich | Prüffall | Erwartete Invariante |
|---|---|---|
| leer | keine Partner beziehungsweise keine gegenseitige Deckung | leeres, erklärtes Ergebnis |
| Basis | genau ein konfliktfreier Partner | korrektes bilaterales Paket |
| Top-3 | mehr als drei geeignete Partner | höchstens drei gemäß freigegebener Zielfunktion |
| Codekonflikt | zwei Partner benötigen dasselbe einmal verfügbare Exemplar | Exemplar höchstens einmal verplant |
| Menge | mehrere verfügbare Exemplare desselben Codes | Summe aller Pakete höchstens effective_available |
| Gesamtoptimum | größtes Einzelmatch blockiert bessere Kombination | freigegebene Gesamtzielfunktion gewinnt |
| GER17 | Peter/Jens-Konflikt aus Product Bible | GER17 nicht doppelt, erwartete Pakete reproduzierbar |
| Tie-Break | fachlich gleichwertige Lösungen | identisches Ergebnis bei jeder Wiederholung |
| Reihenfolge | Nutzer/Codes anders eingereiht | identisches fachliches Ergebnis |
| Snapshot | active reservation und Transit | keine Nutzung nicht effektiv verfügbarer Mengen |
| Problem | offener Problemrest und spätere Auflösung | jeweiliger S19-Zustand korrekt übernommen |
| Albumgrenze | gleiche Codes in mehreren Alben | keine albumübergreifende Planung |
| Schutz | bestehende manuelle Partnerliste | Golden Master unverändert |
| Read-only | Berechnung wiederholt | keine Datenbank-, Inventory- oder Trade-Mutation |
| Last | leere und hohe Partnerzahl | definiertes Performancebudget eingehalten |

## Scope-Bestätigung

Dieses Dokument bleibt der historische Preflight. Die nachträglich
freigegebene S21-Umsetzung ist separat spezifiziert und verändert keine UI,
Migration oder bestehende Produktlogik.
