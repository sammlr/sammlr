# S12 – Inventory Guard und Fehlervertrag

Stand: 2026-08-01
Status: servicezentrierte Architekturvorbereitung ohne echte Bindungsquelle
Grundlagen: S10 InventoryWriteService und S11 Availability-Projektion

## 1. Zweck und Grenze

Der `InventoryGuard` entscheidet, ob eine normalisierte Mengenänderung eine
zukünftig gebundene Mindestmenge unterschreiten würde. In S12 existiert keine
echte Bindung und keine Reservierung. Die Anwendung verwendet standardmäßig
`NoInventoryBindings`, sodass alle heutigen Commands exakt wie bisher
ausgeführt werden.

S12 ergänzt ausschließlich:

- einen Guard-Vertrag,
- einen injizierbaren Vertrag für eine spätere Bindungsquelle,
- UI-neutrale Fehlercodes,
- unveränderliche, erklärbare Entscheidungsobjekte,
- die servicezentrierte Auswertung vor Sticker-DML.

Nicht ergänzt werden Persistenz, Reservierungen, Tradebindung, UI-Auswertung,
Migrationen oder neue Produktregeln.

## 2. Komponenten

Die Guard-Architektur liegt in:

```text
App/services/inventory_guard.py
```

### `InventoryGuard`

Der Guard erhält eine optionale Bindungsquelle und bewertet:

```text
(user_id, album_id, sticker_code,
 current_quantity, requested_quantity)
```

Er gibt immer ein `InventoryGuardDecisionDTO` zurück. Er liest und schreibt
selbst keine Datenbank.

### Bindungsquellen-Vertrag

Eine Quelle stellt ausschließlich diese Methode bereit:

```python
minimum_quantity(user_id, album_id, sticker_code) -> int
```

Die zurückgegebene Menge muss eine nichtnegative ganze Zahl sein. Sie ist die
Mindestmenge, die nach einer Verringerung erhalten bleiben müsste.

In der Anwendung ist ausschließlich `NoInventoryBindings` aktiv:

```text
minimum_quantity(...) = 0
```

Simulierte Quellen befinden sich nur in `tests/test_s12_inventory_guard.py`.
Es gibt keine produktive In-Memory-Bindung und keine echte Reservierungsquelle.

## 3. Fehlercodes

`InventoryGuardCode` ist ein String-Enum mit genau diesen stabilen Werten:

| Code | `allowed` | Bedeutung |
| --- | --- | --- |
| `OK` | ja | Command darf mit der angeforderten Menge fortfahren |
| `BELOW_BOUND_STOCK` | nein | Verringerung würde die simuliert gebundene Mindestmenge unterschreiten |
| `INVALID_OPERATION` | nein | Mengen oder Wert der Bindungsquelle sind keine nichtnegativen ganzen Zahlen |

Die Codes enthalten keine UI-Formulierung, HTTP-Semantik oder
Flask-Abhängigkeit. Eine spätere UI kann ausschließlich den Code auswerten und
einen eigenen Text wählen.

## 4. Entscheidungs-DTO

`InventoryGuardDecisionDTO` ist unveränderlich und enthält:

- `code`,
- `current_quantity`,
- `requested_quantity`,
- `bound_quantity`,
- `explanation`,
- die abgeleitete Eigenschaft `allowed`.

`explanation` macht die technische Entscheidung nachvollziehbar, wird in S12
aber nirgendwo sichtbar ausgegeben.

## 5. Entscheidungsregeln

Die Regeln werden in dieser Reihenfolge ausgewertet:

1. Aktuelle, angeforderte und gebundene Menge müssen nichtnegative ganze
   Zahlen sein; boolesche Werte gelten nicht als Menge.
2. Idempotente Änderungen und Erhöhungen sind `OK`. Sie unterschreiten keinen
   vorhandenen Bestand und werden auch bei einem inkonsistent höheren
   Test-Double-Bound nicht blockiert.
3. Eine Verringerung mit `requested_quantity < bound_quantity` liefert
   `BELOW_BOUND_STOCK`.
4. Eine Verringerung auf oder oberhalb der Mindestmenge ist `OK`.

Damit gilt beispielsweise bei aktuellem Bestand drei und simuliert gebundener
Mindestmenge zwei:

| Angefordert | Ergebnis | Erklärung |
| ---: | --- | --- |
| 4 | `OK` | Erhöhung |
| 3 | `OK` | idempotent |
| 2 | `OK` | exakte Mindestmenge bleibt erhalten |
| 1 | `BELOW_BOUND_STOCK` | Mindestmenge würde unterschritten |

## 6. Anbindung an `InventoryWriteService`

Der Konstruktor akzeptiert optional einen Guard:

```python
service = InventoryWriteService(connection, guard=guard)
```

Ohne Argument wird intern `InventoryGuard(NoInventoryBindings())` verwendet.
Das ist die einzige Verdrahtung der aktiven Anwendung.

Vor `INSERT`, `UPDATE` oder `DELETE` ruft der Service den Guard mit alter und
bereits nach den Legacy-Regeln normalisierter Zielmenge auf.

Bei `OK` läuft die S10-Mechanik unverändert weiter. Bei einer blockierten
Entscheidung:

- wird keine Sticker-DML ausgeführt,
- bleiben `quantity` und das gespeicherte `duplicates` unverändert,
- sind `created`, `deleted` und `changed` falsch,
- enthält das bestehende `InventoryMutationDTO` die `guard_decision`,
- liefern `allowed` und `error_code` eine einfache Adapteroberfläche.

Aktive Webrouten werten diese Felder noch nicht aus, weil die Standardquelle
niemals blockiert. Eine UI-Anbindung wäre eine spätere Produktarbeit und ist
nicht Bestandteil von S12.

## 7. Kompatibilität

Ohne simulierte Bindung ist `bound_quantity = 0`. Jede durch die bestehenden
Routen erzeugte Zielmenge ist bereits nichtnegativ. Der Guard liefert deshalb
`OK`, und der S10-Schreibpfad führt dieselbe DML mit denselben
Transaktionsgrenzen aus.

Unverändert bleiben insbesondere:

- Add, Remove, Inline und Mengenfeld,
- Batch und Session-Undo,
- Papierlisten-Transfer,
- manueller Tausch und bestätigter Tradeabschluss,
- Trophy- und Notification-Hooks,
- Legacy-Normalisierung von `quantity` und `duplicates`.

Der Guard verwendet die Availability-Projektion aus S11 nicht als echte
Bindungsquelle. `available` beschreibt weiterhin nur den heutigen freien
Überschuss; `reserved` bleibt null.

## 8. Transaktions- und Sicherheitsgrenze

Der Guard läuft innerhalb desselben `InventoryWriteService`-Aufrufs zwischen
Lesen der aktuellen Zeile und möglicher DML. `commit`, `rollback` und `close`
bleiben beim aufrufenden Workflow.

Eine zukünftige echte Bindungsquelle müsste konsistent mit derselben
Transaktion gelesen werden. S12 definiert dafür weder Schema noch Locking,
Lifecycle oder Retry-Verhalten.

## 9. Tests

Nur S12:

```sh
python3 -m unittest discover -s tests -p 'test_s12_*.py' -v
```

Vollständiges Gate S01–S12:

```sh
python3 -m unittest discover -s tests -p 'test_s*.py' -v
```

Die S12-Tests prüfen:

- unveränderte Änderung ohne Bindung,
- Blockierung unter einer simulierten Mindestmenge ohne DML,
- Zulässigkeit exakt auf der Mindestmenge,
- idempotente Änderungen und Erhöhungen,
- alle drei Fehlercodes,
- ungültige Operationen und ungültige Test-Double-Werte,
- unveränderliche und erklärbare DTOs,
- ausschließlich standardmäßige Nullbindung in aktiven Routen,
- servicezentrierte, persistenz- und UI-freie Guard-Logik,
- unverändertes Schema und geschützte kanonische Datenbanken.

## 10. Ausdrücklich nicht enthalten

- echte Reservierungen oder Bindungen,
- Bindung bei Tradeanfrage, Annahme oder Bestätigung,
- Tabellen, Spalten, Migrationen oder Unique Constraints,
- Guard-Fehlermeldungen in Webrouten,
- UI, CSS, HTTP-Fehlervertrag oder neue APIs,
- Änderungen an Availability, Trade, Notification oder Produktverhalten.
