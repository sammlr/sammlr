# S21 – Konfliktfreie Top-Match-Optimierung

Stand: 2026-08-06
Status: umgesetzt

## Ziel und fachliche Grenze

S21 erzeugt eine einzige gemeinsam optimierte Gesamtlösung aus höchstens drei
gleichzeitig ausführbaren Partnerpaketen. Sie maximiert den Fortschritt des
suchenden Nutzers, ohne dessen effektiv verfügbare Sticker mehrfach zu
verplanen.

Die Berechnung ist ausschließlich read-only. Sie erzeugt keine Anfrage, keinen
Trade und keine Reservierung und verändert weder Inventory noch Lifecycle.
Eine Produkt-UI ist nicht Bestandteil von S21.

## Verbindliche Product-Owner-Entscheidungen

Die Optimierung verwendet exakt diese lexikografische Zielfunktion:

1. maximale Anzahl unterschiedlicher abgedeckter fehlender Codes,
2. minimale Anzahl verwendeter Partnerpakete,
3. minimale Gesamtzahl eigener abgegebener Sticker,
4. minimale redundante Empfangspositionen,
5. höhere Summe persönlicher S20-Abdeckungen,
6. lexikografisch kleinere sortierte Partner-ID-Liste,
7. je Partner lexikografisch kleinere sortierte Empfangs- und Abgabecodelisten.

Weniger Fortschritt wird niemals zugunsten weniger Trades gewählt. „Top 3“
bedeutet höchstens drei Partnerpakete in derselben Lösung, nicht drei
alternative Lösungen.

## Datenfluss

```text
Albumkatalog + Suchender + explizite Partner-IDs
                    │
                    ▼
S19 InventoryReadService.snapshot(...)
  - effective_available und Mengenbegrenzung
  - reserved/incoming/outgoing bereits fachlich projiziert
                    │
                    ▼
S20 TradeCoverageService
  - persönliche Abdeckung Suchender ← Partner
  - reziproke Abdeckung Partner ← Suchender
  - Community-Erklärdaten / fehlende Gesamtmenge
                    │
                    ▼
S21 Partnerkandidaten und Bitmasken-Obergrenzen
                    │
                    ▼
Kombinationen mit 1, 2 oder 3 Partnern
  + deterministisches Max-Flow-Netz pro relevanter Kombination
                    │
                    ▼
lexikografischer Score → unveränderliches Ergebnis-DTO
```

Der S21-Service enthält kein SQL. Verfügbarkeit wird weder nachgerechnet noch
interpretiert: Kandidatencodes kommen aus den S20-Erklärdaten, Mengen aus dem
S19-Snapshot.

## Eingangsdaten

`TopMatchOptimizationService.optimize(...)` erhält:

- ID des suchenden Nutzers,
- genau eine Album-ID,
- den Katalog dieses Albums,
- die explizit zu betrachtenden Partner-IDs.

Katalogcodes, Partner-IDs sowie resultierende Codelisten werden dedupliziert
und lexikografisch beziehungsweise numerisch sortiert. Eingabereihenfolgen
haben dadurch keinen Einfluss auf das Ergebnis.

Ein Partner wird nur Kandidat, wenn beide Richtungen ausführbar sind:

- Er besitzt mindestens einen beim Suchenden fehlenden Code effektiv
  verfügbar.
- Der Suchende besitzt mindestens einen beim Partner fehlenden Code effektiv
  verfügbar.

## Konfliktfreie Paketbildung

Für jede Partnerkombination wird ein Flussnetz aufgebaut:

```text
Quelle
  → eigener abgebbarer Code (Kapazität = S19 effective_available)
  → Partner, der diesen Code gemäß reziproker S20-Abdeckung benötigt
  → beim Suchenden fehlender, dort effektiv angebotener Code
  → Senke (Kapazität 1 je fehlendem Code)
```

Ein Flusspfad entspricht genau einer Abgabe- und einer Empfangsposition beim
selben Partner. Damit gelten strukturell:

- keine eigene Menge wird überbucht,
- jeder fehlende Code wird höchstens einmal empfangen,
- Pakete bleiben ausgeglichen,
- Mengen größer eins können auf mehrere Partner verteilt werden,
- jedes ausgewählte Paket enthält mindestens eine ausführbare Position.

Vor einem Flusslauf berechnen Bitmasken eine sichere obere Schranke aus der
Vereinigung angebotener Codes und der verfügbaren eigenen Mengen. Eine
Kombination wird nur verworfen, wenn sie die bereits beste Lösung nach der
verbindlichen Zielfunktion sicher nicht mehr schlagen kann.

## Determinismus und Tie-Breaks

- Partner werden nach ID sortiert.
- Codes werden als Strings lexikografisch sortiert.
- Kombinationen werden in Größenfolge 1, 2, 3 geprüft.
- Knoten und Kanten des Flussnetzes werden deterministisch angelegt.
- Der vollständige Score wird als vergleichbares Tupel abgebildet.
- Empfangs- und Abgabepositionen werden sortiert ausgegeben.
- Die Ergebniskennung ist SHA-256 über eine kanonische JSON-Darstellung der
  Version, Nutzer-/Albumidentität und sortierten Pakete.

Da das Flussnetz nur unterschiedliche fehlende Empfangscodes zur Senke
durchlässt, beträgt die redundante Empfangsmenge in S21 V1 immer null. Der
vierte Scorebestandteil bleibt im Vertrag sichtbar und abgesichert.

## Ergebnis-DTO

`TopMatchOptimizationResultDTO` ist unveränderlich und enthält:

- Version `S21-v1`, Nutzer und Album,
- höchstens drei `TopMatchPackageDTO`,
- kompakte `TopMatchConflictDTO` für nicht ausgewählte Partner mit bereits
  ausgeschöpften eigenen Codes,
- fehlende und insgesamt abgedeckte Codemenge,
- Anzahl Partnerpakete,
- gesamte Abgabemenge,
- redundante Empfangspositionen,
- Summe persönlicher S20-Abdeckungen,
- deterministische SHA-256-Ergebniskennung,
- kurze Gesamterklärung.

Jedes Paket enthält Partner-ID, sortierte Empfangs- und Abgabepositionen mit
Mengen, eigenen Abdeckungsbeitrag, persönliche S20-Abdeckung und kompakte
Auswahlgründe.

## GER17-Regression

Die isolierte Regression gibt dem Suchenden genau eine effektiv verfügbare
Überschusskopie `GER17`. Zwei Partner benötigen sie. Das größere ausführbare
Paket gewinnt; `GER17` erscheint genau einmal. Bei gleicher Abdeckung greift
zuerst die minimale Abgabemenge und danach die kleinere Partner-ID.

Die allgemeine Mengenprüfung zeigt ergänzend: Bei zwei effektiv verfügbaren
Überschusskopien darf derselbe Code an zwei Partner je einmal vergeben werden,
niemals häufiger als `effective_available`.

## Komplexität und Begrenzung

Für `P ≤ 100` Kandidaten und `C ≤ 1.000` Katalogcodes gilt:

- S19/S20-Projektion: abhängig von den bestehenden Snapshotabfragen,
  näherungsweise `O(P · C)` auf DTO-Ebene,
- Kombinationsraum: `O(P³)`, hart begrenzt auf Teilmengen der Größen 1–3,
- Obergrenze pro Kombination: konstante Anzahl von Bitoperationen über
  Python-Integer-Bitmasken,
- Max-Flow nur für Kombinationen, die das aktuelle Optimum noch erreichen
  oder übertreffen können,
- kein Caching und keine unbegrenzte Suche.

Die getestete Referenzfixture mit 1.000 Codes, 100 Partnern und je 100
relevanten Codes benötigte rund **276 ms für die Kernoptimierung** und rund
**1,5 s für den vollständigen Performancetest einschließlich Fixture-Aufbau
und S19/S20-Projektion**.

## Testmatrix

Abgedeckt sind:

- keine Partner und ein Partner,
- mehr als drei Partner und Top-3-Grenze,
- gemeinsame Optimierung statt isolierter Partnersortierung,
- eigener Codekonflikt und GER17,
- Mengen größer eins,
- vollständige Score- und Tie-Break-Reihenfolge,
- gleiche und umsortierte Eingaben,
- aktive Reservierung, outgoing_transit und incoming_transit,
- strikte Albumgrenze,
- unveränderte Snapshots, Inventory- und Datenbankzustände,
- 1.000 Codes, 100 Partner und Performancebudgets.

## Bekannte Grenzen

- S21 erzeugt ausschließlich Vorschläge; Recheck, Anfrage und Reservierung
  gehören zu S22.
- Ein fehlender Albumcode wird in V1 als Bedarf einer Kopie behandelt.
- Partnerauswahl und Zugriffsberechtigung bleiben Aufgabe des Aufrufers.
- Es gibt kein Ranking nach Reputation, Zuverlässigkeit oder Nähe.
- Es gibt keine albumübergreifende Optimierung.
- Es gibt kein Caching.
- Der kombinatorische Raum ist bewusst auf höchstens drei Pakete begrenzt.

## Nicht enthalten

Keine UI, Migration, Datenbankschemaänderung, Tradeerzeugung, Reservierung,
Versand-/Empfangsänderung, Problemlogik, frei wählbare Strategie oder
Änderung bestehender S19-/S20-Komponenten.
