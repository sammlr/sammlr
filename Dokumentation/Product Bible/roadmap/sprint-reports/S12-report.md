# Sprintbericht S12 – Schutz manueller Mengenänderungen vorbereiten

Stand: 2026-08-01

## Ergebnis

Sprint S12 wurde ausschließlich als Service- und Architekturvorbereitung umgesetzt. Ein zentraler, UI-neutraler Inventory Guard prüft Mengenänderungen vor dem bestehenden `InventoryWriteService`. Ohne simulierte Bindungsquelle verwendet der Guard einen Mindestbestand von `0`; dadurch bleibt das bisherige Produktverhalten unverändert.

Es wurden keine echten Reservierungen, keine neue Produktlogik, keine UI-Änderungen und keine Datenbankänderungen umgesetzt.

## Neue Dateien

- `App/services/inventory_guard.py`
  - Inventory Guard, Entscheidungs-DTO, Fehlercodes und bindungsfreie Standardquelle
- `tests/test_s12_inventory_guard.py`
  - isolierte S12-Contract- und Integrationstests mit ausschließlich testseitig simulierten Bindungen
- `Dokumentation/Product Bible/roadmap/s12-inventory-guard.md`
  - verbindlicher S12-Guard-Vertrag und Integrationsbeschreibung
- `Dokumentation/Product Bible/roadmap/sprint-reports/S12-report.md`
  - dieser Sprintbericht

## Geänderte Dateien

- `App/services/inventory_write.py`
  - optionale Guard-Abhängigkeit ergänzt
  - Guard-Prüfung unmittelbar vor dem bestehenden Schreibadapter eingebunden
  - Mutationsergebnis um die UI-neutrale Guard-Entscheidung ergänzt
  - bei abgelehnter Änderung erfolgt keine Datenbankmutation
- `Dokumentation/Product Bible/roadmap/README.md`
  - Verweise auf S12-Spezifikation und S12-Sprintbericht ergänzt

Weitere bereits vorhandene Änderungen im Arbeitsverzeichnis wurden nicht S12 zugerechnet und nicht zurückgesetzt.

## Guard-Konzept

Der `InventoryGuard` erhält:

- die Inventory-Identität,
- die aktuelle Menge,
- die angeforderte Zielmenge,
- und optional eine Quelle für einen simulierten gebundenen Mindestbestand.

Die Standardquelle `NoInventoryBindings` liefert immer den Mindestbestand `0`. Damit sind alle heute gültigen Änderungen weiterhin zulässig. Simulierte Bindungen existieren ausschließlich als Test-Doubles in der S12-Testsuite; es gibt weder eine produktive Bindungsquelle noch Reservierungs- oder Persistenzlogik.

Die Entscheidung wird als unveränderliches `InventoryGuardDecisionDTO` zurückgegeben. Es enthält Code, aktuelle Menge, Zielmenge, Mindestbestand und eine erklärende, UI-neutrale Beschreibung.

Prüfreihenfolge:

1. Eingabewerte validieren.
2. Simulierten Mindestbestand lesen und validieren.
3. Idempotente Änderungen und Erhöhungen erlauben.
4. Verringerungen unter den simulierten Mindestbestand ablehnen.
5. Alle übrigen Verringerungen erlauben.

## Fehlercodes

| Code | Bedeutung |
| --- | --- |
| `OK` | Die Änderung ist nach dem Guard-Vertrag zulässig. |
| `BELOW_BOUND_STOCK` | Die Zielmenge würde einen simulierten gebundenen Mindestbestand unterschreiten. |
| `INVALID_OPERATION` | Mengenwert oder simulierte Bindungsantwort ist für den Vertrag ungültig. |

Die Codes sind stabile String-Enum-Werte und können später ohne UI-Abhängigkeit ausgewertet werden.

## Einbindung in den InventoryWriteService

Der `InventoryWriteService` akzeptiert optional einen Guard. Ohne Übergabe wird der kompatible Standardguard ohne Bindungen verwendet. Vor dem vorhandenen SQL-Adapter wird die Zielmenge geprüft:

- `OK`: Der bestehende S10-Schreibpfad wird unverändert ausgeführt.
- anderer Code: Es erfolgt kein `INSERT`, `UPDATE` oder `DELETE`; das Ergebnis enthält die unveränderte Bestandsinformation und die Guard-Entscheidung.

Die vorhandenen Schreiboperationen, DTO-Eingaben, Trophy-/Notification-Hooks und Transaktionsgrenzen wurden nicht fachlich verändert.

## Testübersicht

S12-spezifischer Testbefehl:

```text
python3 -m unittest tests.test_s12_inventory_guard -v
```

Ergebnis: 12 von 12 Tests erfolgreich.

Geprüft wurden insbesondere:

- Änderung ohne Bindung bleibt erlaubt und liefert das bisherige Ergebnis.
- Simulierte Bindung verhindert eine Unterschreitung ohne Datenbankmutation.
- Änderung exakt bis zum simulierten Mindestbestand bleibt erlaubt.
- Idempotente Änderungen bleiben erlaubt.
- Erhöhungen bleiben erlaubt.
- Alle drei definierten Fehlercodes sind stabile UI-neutrale Werte.
- Ungültige Mengen und ungültige Antworten eines Test-Doubles liefern `INVALID_OPERATION`.
- Das Entscheidungs-DTO ist unveränderlich und erklärbar.
- Die Standardanwendung besitzt keine simulierte oder echte Bindungsquelle.
- Der Guard enthält keine Persistenz- oder UI-Abhängigkeit.

Vollständiges Testgate, zweimal ausgeführt:

```text
python3 -m unittest discover -s tests -p 'test_s*.py' -v
```

- Lauf 1: 145 von 145 Tests erfolgreich (`OK`).
- Lauf 2: 145 von 145 Tests erfolgreich (`OK`).

Der zweite Lauf bestätigt die Reproduzierbarkeit. Sämtliche vorhandenen Regressionstests bis einschließlich S12 blieben grün.

## Datenbank- und Fixture-Schutz

Die vollständigen Testläufe verwendeten die isolierte Testinfrastruktur. Vor und nach den beiden Abschlussläufen waren die Prüfsummen identisch:

- `App/Database/sammlr.db`: `4ea4a9a097fa5061c4d8b5675db82fdca4e23c6b3994b457e5efb3161320e306`
- `App/Database/sammlr_reference_s00.db`: `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`

Das Datenbankschema wurde nicht geändert. Die bereits im Arbeitsverzeichnis vorhandene, benutzerverwaltete Änderung an `sammlr.db` wurde weder als S12-Änderung behandelt noch zurückgesetzt.

## Offene Punkte für S13

Diese Beobachtungen wurden nicht umgesetzt:

- Eine spätere versionierte Schema-/Lifecycle-Grundlage muss festlegen, wie reale Bindungen fachlich repräsentiert und migriert werden.
- Eine spätere reale Bindungsquelle benötigt eine konsistente Transaktionsgrenze zwischen Mindestbestandsabfrage und Bestandsmutation.
- Identität, Lebenszyklus und Auflösung zukünftiger Reservierungen müssen vor einer produktiven Anbindung verbindlich definiert werden.
- Die spätere Abbildung der UI-neutralen Fehlercodes auf sichtbare Meldungen bleibt außerhalb von S12.

S13 wurde nicht begonnen; es wurden dafür weder Schema-, Reservierungs- noch UI-Arbeiten vorgezogen.

## Scope-Bestätigung

- Ausschließlich Sprint S12 wurde umgesetzt.
- Sprint S13 wurde nicht begonnen.
- Es wurden keine echten Reservierungen implementiert.
- Es wurden keine Availability-Regeln verändert.
- Es wurden keine UI-, CSS-, Trade- oder Notification-Änderungen vorgenommen.
- Es wurden keine Produktfunktionen und kein sichtbares Verhalten verändert.
- Es wurden keine Datenbankmigrationen und keine Datenbankschemaänderungen vorgenommen.
- Es wurde kein Commit erstellt und kein Push durchgeführt.
