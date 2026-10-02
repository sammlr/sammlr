# Sprint-Report S21 – Konfliktfreie Top-Match-Optimierung

Stand: 2026-08-06

## Ziel und Ergebnis

S21 ist umgesetzt. Der neue read-only `TopMatchOptimizationService` erzeugt
eine gemeinsam optimierte Gesamtlösung aus höchstens drei konfliktfreien
Partnerpaketen. Bestehende Trade-, Inventory-, Snapshot- und Coverage-Logik
wurde nicht verändert.

Es wurden keine UI, keine Anfrage, keine Reservierung, kein Trade und keine
Migration ergänzt.

## Product-Owner-Entscheidungen und Zielfunktion

Der Product Owner hat die zuvor offenen Punkte verbindlich entschieden. Der
Service minimiert beziehungsweise maximiert lexikografisch exakt:

1. maximale unterschiedliche fehlende Abdeckung,
2. minimale Zahl Partnerpakete,
3. minimale eigene Abgabemenge,
4. minimale redundante Empfangspositionen,
5. maximale Summe persönlicher S20-Abdeckungen,
6. kleinere sortierte Partner-ID-Liste,
7. je Partner kleinere sortierte Empfangs- und Abgabecodelisten.

Weniger Fortschritt verliert immer. Top 3 bezeichnet bis zu drei gleichzeitig
ausführbare Pakete derselben Lösung.

## Neue und geänderte Dateien

Neu:

- `App/services/top_match_optimization.py`
- `tests/test_s21_top_match_optimization.py`
- `Dokumentation/Product Bible/roadmap/s21-conflict-free-top-match-optimization.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S21-report.md`

Geändert:

- `Dokumentation/Product Bible/roadmap/s21-preflight.md`
  - Product-Owner-Entscheidungen als verbindlich geklärt dokumentiert.

Keine bestehende Python-Datei wurde geändert.

## Architektur und Datenfluss

Der neue Service besitzt einen eigenen unveränderlichen DTO-Vertrag und wird
mit `InventoryReadService` sowie optional dem bestehenden
`TradeCoverageService` konstruiert.

```text
explizite Nutzer-/Album-/Partnerdaten
  → S19 Snapshot
  → beidseitige persönliche S20-Coverage-Erklärdaten
  → Partnerkandidaten
  → Kombinationen der Größe 1–3
  → Bitmasken-Obergrenze
  → deterministisches Max-Flow-Netz
  → vollständiger lexikografischer Score
  → unveränderliches S21-Ergebnis
```

Ein Flusspfad koppelt eine abzugebende und eine zu empfangende Position beim
selben Partner. Eigene Codeknoten tragen exakt die S19-Menge
`effective_available`; Empfangscodeknoten besitzen Kapazität eins. Damit sind
Mengen- und Konfliktinvarianten Bestandteil des Algorithmus, nicht nur eine
nachträgliche Prüfung.

Der Service enthält kein SQL, keine Mutation und keine Availability-
Neuberechnung.

## Ergebnis-DTO

`TopMatchOptimizationResultDTO` enthält:

- höchstens drei `TopMatchPackageDTO`,
- Partner-ID sowie Empfangs-/Abgabepositionen und Mengen je Paket,
- Abdeckungsbeitrag und persönliche S20-Abdeckung je Paket,
- Auswahlgründe,
- kompakte nicht ausgewählte eigene Mengenkonflikte,
- Gesamtabdeckung, Partnerzahl, Abgabemenge und redundanten Empfang,
- Summe persönlicher S20-Abdeckungen,
- Erklärung und deterministische SHA-256-Ergebniskennung.

Alle öffentlichen DTOs sind eingefrorene Dataclasses; Listen werden als
sortierte Tupel ausgegeben.

## Algorithmus und Komplexität

Der Service prüft ausschließlich Partnerteilmengen der Größen 1, 2 und 3.
Sichere Bitmasken-Obergrenzen verwerfen Kombinationen, die das aktuelle
Optimum nicht mehr schlagen können. Für verbleibende Kombinationen bestimmt
ein deterministischer maximaler Fluss die größte konfliktfreie, ausgeglichene
Codezuordnung. Danach wird der vollständige PO-Score verglichen.

- Kandidatenprojektion ungefähr `O(P · C)` auf DTO-Ebene.
- Hart begrenzter Kombinationsraum `O(P³)` für maximal drei Partner.
- Bitmasken-Pruning vor dem Flusslauf.
- Max-Flow nur für noch konkurrenzfähige Kombinationen.
- Kein Caching und keine unbegrenzte kombinatorische Suche.

## GER17-Beispiel

Die synthetische Regression enthält genau eine effektiv verfügbare
Überschusskopie `GER17`. Zwei Partnerpakete benötigen sie. Das Paket mit dem
größeren Beitrag gewinnt und `GER17` wird genau einmal abgegeben. Bei gleicher
Abdeckung greifen minimale Abgabemenge und anschließend kleinere Partner-ID.

Ein weiterer Mengentest setzt `effective_available=2`; dann darf GER17 an zwei
Partner je einmal, aber niemals dreimal verplant werden.

## Testmatrix und Ergebnisse

S21-spezifisch:

```bash
python3 -m unittest tests.test_s21_top_match_optimization -v
```

Ergebnis: **19 Tests, OK**.

Abgedeckt:

- keine Partner, ein Partner und mehr als drei Partner,
- maximal drei ausgewählte Pakete,
- gemeinsame Optimierung statt isolierter Top-3-Sortierung,
- keine Mehrfachverplanung und Mengen größer eins,
- GER17,
- sämtliche sieben Score-/Tie-Break-Stufen,
- Wiederholung und geänderte Eingabereihenfolge,
- Reservierung, outgoing_transit und incoming_transit,
- strikte Albumtrennung,
- hohe Partnerzahl und Performance,
- unveränderte Snapshots, Inventory- und Datenbankzustände.

Vollständiges Gate, zweimal:

```bash
python3 -m unittest discover -s tests -p 'test_s*.py' -v
```

- Lauf 1: **341 Tests, OK**
- Lauf 2: **341 Tests, OK**

## Performancefixture und Messwerte

Verbindliche Fixture:

- ein Album,
- 1.000 Katalogcodes,
- ein suchender Nutzer,
- 100 mögliche Partner,
- je Partner 100 relevante Codes,
- höchstens drei ausgewählte Pakete.

Gemessen in der lokalen Testumgebung:

- reine Kernoptimierung: **ca. 276 ms**; Budget kleiner 500 ms,
- vollständiger einzelner Performancetest einschließlich Fixture-Aufbau und
  S19/S20-Projektion: **ca. 1,5 s**; Budget kleiner 2 s.

## Bekannte Grenzen

- Vorschläge werden nicht gespeichert und erzeugen keine Anfrage.
- Recheck, Anfrage-Limit, Ablauf und Reservierung gehören zu S22.
- Bedarf ist innerhalb des bestehenden Einzelalbum-Modells ein Exemplar je
  fehlendem Code.
- Partnerauswahl und Berechtigung erfolgen außerhalb des Services.
- kein Reputation-, Zuverlässigkeits- oder Nähe-Ranking,
- keine albumübergreifenden Trades,
- kein Caching,
- maximal drei Pakete.

## Release Readiness

- S21-spezifische Tests vollständig grün
- beide Vollgates vollständig grün
- Syntaxprüfung erfolgreich
- `PRAGMA integrity_check`: `ok`
- `PRAGMA foreign_key_check`: keine Befunde
- lokaler Migrationsstand read-only geprüft: V0005
- Migration erforderlich beziehungsweise ausgeführt: nein
- kanonische S00-Fixture unverändert
- lokale Entwicklungsdatenbank innerhalb der S21-Testläufe unverändert
- `git diff --check`: ohne Befund

## Offene Punkte für S22

- erneuter Availability-Recheck vor der Anfrage
- eindeutige Smart-Paketkennzeichnung
- Anfrage-Limit und Ablaufzeit nach separater Produktfreigabe
- transparente Paketverkleinerung und erneute Zustimmung
- Ausschließen eines Vorschlags und anschließende Neuberechnung

Keiner dieser Punkte wurde begonnen.

## Scope-Bestätigung

- ausschließlich S21 umgesetzt
- S22 nicht begonnen
- keine UI
- keine Migration oder Schemaänderung
- keine Änderung an Trade-, Inventory-, S19-, S20-, Versand-, Empfangs- oder
  Problemlogik
- ausschließlich read-only
- kein Commit
- kein Push
