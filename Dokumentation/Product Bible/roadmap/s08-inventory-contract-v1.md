# S08 – Inventory Contract V1

Stand: 2026-07-31
Status: verbindliche fachliche Grundlage für die nachfolgenden Inventory-Sprints
Laufzeitimplementierung: nicht Bestandteil von S08

Dieser Contract definiert Begriffe, Einheiten, Gleichungen und Invarianten für
das Sammlr-Inventar. Er verändert weder Anwendungscode noch Datenbankschema oder
das heutige `quantity`-Verhalten.

## 1. Betrachtungseinheit

Alle Mengen sind nichtnegative ganze Anzahlen physischer Stickerkopien für
genau diese fachliche Identität:

```text
(Nutzer, Albumtyp, Sticker-Code)
```

Eine Albuminstanz ist eine konkrete Ausgabe eines Albumtyps. `assigned` wird
über die Zuordnungen aller Albuminstanzen derselben Betrachtungseinheit
aggregiert. Ein Klebe-, Hüllen- oder Lagerzustand wird nicht modelliert.

## 2. Verbindliche Begriffe

| Begriff | Symbol | Quelle | Bedeutung und Einheit |
| --- | --- | --- | --- |
| `physical` | `P` | bestätigte manuelle Bestände und bestätigte Eingänge abzüglich bestätigter Ausgänge | Anzahl der Kopien, die beim Nutzer physisch vorhanden sind |
| `assigned` | `A` | explizite oder regelgebundene Zuordnung zu konkreten Albuminstanzen | physisch vorhandene Kopien, die genau einer Albuminstanz zugeordnet sind |
| `available` | `V` | aus `physical`, `assigned` und `reserved` abgeleitet | physisch vorhandene, nicht zugeordnete und nicht reservierte Kopien im freien Tauschpool |
| `reserved` | `R` | verbindliche Positionen angenommener Deals | physisch vorhandene freie Kopien, die für genau einen Deal gebunden sind |
| `outgoing_transit` | `O` | bestätigter Versand einer zuvor reservierten Dealposition | versendete Kopien, die den physischen Bestand des Senders verlassen haben, deren Empfang aber noch nicht bestätigt ist |
| `incoming_transit` | `I` | Spiegel derselben bestätigten Versandposition beim Empfänger | erwartete Kopien unterwegs; noch kein physischer Bestand des Empfängers |

`available` ist der fachliche freie Bestand. Er ist nicht gleichbedeutend mit
allen physischen Überschusskopien, sobald Reservierungen existieren.

## 3. Mengengleichungen

Für jede Betrachtungseinheit gilt:

```text
P = A + V + R
V = P - A - R
0 <= A <= P
0 <= R <= P - A
0 <= V <= P
```

`A`, `V` und `R` sind disjunkte Teilmengen des physischen Bestands. Jede
physisch vorhandene Kopie liegt zu einem Zeitpunkt in genau einem dieser drei
Buckets.

Transit ist bewusst außerhalb dieser Gleichung:

```text
O ∉ P des Senders
I ∉ P des Empfängers
```

Für jede versendete Dealposition gilt paarweise:

```text
O(Sender, Dealposition) = I(Empfänger, Dealposition)
```

`O` und `I` beschreiben damit dieselben unterwegs befindlichen Kopien aus zwei
Perspektiven. Bei systemweiten Summen darf nur eine Transitperspektive gezählt
werden:

```text
eindeutig gezählte Kopien = Summe(P aller Nutzer) + Summe(O)
                         = Summe(P aller Nutzer) + Summe(I)
```

`Summe(P) + Summe(O) + Summe(I)` wäre eine Doppelzählung.

## 4. Abgeleitete Zustände

Der physische Überschuss oberhalb der Albumzuordnungen lautet:

```text
surplus_physical = max(P - A, 0) = V + R
```

Damit gilt:

- `surplus_physical` kann reservierte Kopien enthalten.
- Nur `available` darf für einen neuen Deal oder Smart-Trade-Vorschlag genutzt
  werden.
- `incoming_transit` erhöht weder Albumfortschritt noch `physical` oder
  `available`.
- Ein unterwegs eingehender Sticker bleibt physisch fehlend, kann aber in einer
  späteren Bedarfslogik separat berücksichtigt werden. Diese Berechnung ist
  nicht Bestandteil von S08.

## 5. Verbindliche Invarianten

### I-01 – Ganzzahligkeit und Nullgrenze

Alle sechs Mengen sind ganze Zahlen und niemals negativ.

### I-02 – Physische Bilanz

`physical` entspricht exakt `assigned + available + reserved`.

### I-03 – Verfügbarkeit

`available` ist abgeleitet, niemals größer als `physical` und niemals negativ.

### I-04 – Eindeutige Bucket-Zuordnung

Eine physische Kopie darf nicht zugleich `assigned`, `available` oder
`reserved` sein. Die Summe dieser Buckets darf `physical` weder über- noch
unterschreiten.

### I-05 – Reservierungsgrenze

Eine neue Reservierung darf höchstens die vor der Reservierung verfügbare Menge
binden. Eine bloße Anfrage reserviert weiterhin nichts.

### I-06 – Ausgehender Transit

Beim bestätigten Versand wechselt die betroffene Menge von `reserved` zu
`outgoing_transit` und verlässt gleichzeitig `physical`. Sie bleibt nicht
zusätzlich reserviert oder verfügbar.

### I-07 – Eingehender Transit

`incoming_transit` ist beim Empfänger weder `physical`, `assigned` noch
`available`. Erst bestätigter Empfang darf `incoming_transit` vermindern und
`physical` erhöhen.

### I-08 – Transitspiegel statt Doppelzählung

Ausgehender und eingehender Transit derselben Dealposition müssen mengenmäßig
übereinstimmen und dürfen bei systemweiten Summen nicht als zwei verschiedene
Kopien gezählt werden.

### I-09 – Albumfortschritt

Albumfortschritt entsteht ausschließlich durch `assigned` der konkreten
Albuminstanz. Freie, reservierte oder unterwegs befindliche Kopien erhöhen ihn
nicht.

### I-10 – Heutige `quantity`-Kompatibilität

Für das heutige Einzelalbum ohne Reservierungs- und Transitmodell bleibt die
sichtbare und gespeicherte Mengenlogik unverändert:

```text
P = quantity
A = min(quantity, 1)
V = max(quantity - 1, 0)
R = O = I = 0
duplicates = max(quantity - 1, 0) = V
```

Menge null bleibt im Ist-Modell durch das Fehlen einer `stickers`-Zeile
repräsentiert. Eine vorhandene Zeile muss `quantity >= 1` besitzen.

## 6. Zustandsbeispiele

| Fall | `P` | `A` | `V` | `R` | `O` | `I` | Erklärung |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| fehlt | 0 | 0 | 0 | 0 | 0 | 0 | keine physische Kopie |
| Einzelalbum erfüllt | 1 | 1 | 0 | 0 | 0 | 0 | eine Kopie ist zugeordnet |
| eine freie Doppelte | 2 | 1 | 1 | 0 | 0 | 0 | zweite Kopie ist tauschbar |
| drei Kopien, eine reserviert | 3 | 1 | 1 | 1 | 0 | 0 | nur eine Kopie bleibt frei |
| reservierte Kopie versendet | 2 | 1 | 1 | 0 | 1 | 0 | Versandkopie ist nicht mehr physisch beim Sender |
| dieselbe Kopie beim Empfänger unterwegs | 0 | 0 | 0 | 0 | 0 | 1 | noch kein physischer Eingang |
| Empfang bestätigt und zugeordnet | 1 | 1 | 0 | 0 | 0 | 0 | Transit ist in physischen Bestand überführt |
| zwei Albuminstanzen erfüllt, eine frei | 3 | 2 | 1 | 0 | 0 | 0 | freie Kopie gehört keiner Albuminstanz |

## 7. Fehlerfälle

Ein Zustand ist vertragswidrig, wenn mindestens eines gilt:

- eine Menge ist negativ, nicht ganzzahlig oder boolesch,
- `A + V + R != P`,
- `V > P`,
- eine Reservierung übersteigt die zuvor verfügbare Menge,
- eine versendete Kopie bleibt zugleich in `P`, `R` oder `V`,
- `I` wird vor Empfang als physisch, zugeordnet oder verfügbar gezählt,
- `O` und `I` derselben Dealposition unterscheiden sich,
- eine Transitkopie wird durch Addition beider Perspektiven doppelt gezählt,
- heutige `quantity`-Daten werden anders als in I-10 interpretiert.

## 8. Kompatibilität mit dem aktuellen Sammlr-Modell

### Ist-Modell

Die Tabelle `stickers` speichert derzeit pro Nutzer, `album_id` und
`sticker_code` eine aggregierte `quantity`. Das Feld `duplicates` ist redundant
und entspricht nach den geschützten Schreibwegen `max(quantity - 1, 0)`.

Das Ist-Modell kennt nicht getrennt:

- mehrere Albuminstanzen desselben Albumtyps,
- einen albumtypbezogenen freien Pool,
- Reservierungen,
- ausgehenden oder eingehenden Transit.

### Reine Kompatibilitätsprojektion

Bis zu einer späteren bewusst freigegebenen Migration wird jede heutige Zeile
nur gedanklich gemäß I-10 projiziert. Es werden keine Spalten, Tabellen oder
Schreibpfade ergänzt. Fehlende Zielinformationen werden nicht erfunden, sondern
mit `R = O = I = 0` und genau einer möglichen Zuordnung behandelt.

Diese Projektion ist verlustfrei für das heutige sichtbare Verhalten:

- Stickerwall-Menge bleibt `quantity`.
- „Doppelt“ bleibt ab `quantity >= 2`.
- `duplicates` bleibt `max(quantity - 1, 0)`.
- Albumfortschritt zählt weiterhin einen vorhandenen Code höchstens einmal.
- Papierliste, Mengenregler und heutiger Tradeabschluss bleiben unverändert.

Sie ist ausdrücklich keine Datenmigration und noch kein Inventory-Service.

## 9. Ausführbarer Contract

`tests/test_s08_inventory_contract_v1.py` ist eine testlokale, reine
Referenzspezifikation. Sie prüft:

- die tabellarischen Zielzustände,
- alle mathematischen Invarianten und Fehlerfälle,
- Reservierungs-, Versand- und Empfangsübergänge ausschließlich als
  Vertragsbeispiele,
- Transitspiegel und Schutz vor Doppelzählung,
- die `quantity`-Kompatibilitätsprojektion,
- die ausschließlich lesende Vereinbarkeit der S00-Fixture,
- das unveränderte Legacy-Schema.

Die Tests stellen keine produktive Berechnungs-, Lese- oder Schreiblogik bereit.

## 10. Nicht Bestandteil von S08

- Inventory-Service oder zentrale Lese-/Schreiblogik,
- Availability-Berechnung im Anwendungscode,
- Reservierungen oder Transitimplementierung,
- neue APIs, Tabellen, Spalten oder Migrationen,
- UI, CSS, Trade- oder Notificationänderungen,
- Refactoring bestehender Funktionen.
