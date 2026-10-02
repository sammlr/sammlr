# Abschlussbericht – Sprint S11

Sprint S11 – Verfügbare und reservierbare Menge vorbereiten ist vollständig
umgesetzt.

## Neue Dateien

- `App/services/inventory_availability.py`
- `tests/test_s11_availability.py`
- `Dokumentation/Product Bible/roadmap/s11-availability.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S11-report.md`

## Geänderte Dateien

- `App/services/inventory.py`
- `App/webapp.py`
- `Dokumentation/Product Bible/roadmap/README.md`

`App/webapp.py` wurde ausschließlich in verhaltensgleichen Inventory- und
Matching-Lesepfaden angepasst. Schreibpfade, Transaktionsgrenzen, Tradezustände,
Notifications, Trophy-Hooks und sichtbare Antworten blieben unverändert.
Bereits vor S11 vorhandene Änderungen im Arbeitsbaum wurden weder bearbeitet
noch zurückgesetzt.

## Availability-Modell

Die neue read-only Komponente `LegacyAvailabilityCalculator` projiziert die
heutige `quantity` gemäß S08:

```text
physical         = max(quantity, 0)
assigned         = min(physical, 1)
reserved         = 0
available        = max(physical - assigned - reserved, 0)
incoming_transit = 0
reservable       = available
```

Für gültige heutige Daten ist damit:

```text
physical = quantity
assigned = min(quantity, 1)
available = max(quantity - 1, 0)
```

`reserved` und `incoming_transit` sind ausschließlich erklärende Bestandteile
des DTO und in S11 immer null. `reservable` benennt die heute freie Menge,
erzeugt oder bindet aber keine Reservierung.

Die defensive Begrenzung eines vertragswidrigen negativen Eingangswerts auf
eine nichtnegative Leseprojektion schreibt nichts zurück und ist kein Guard.

## Verwendete DTOs

`AvailabilityDTO` ist eine unveränderliche Dataclass mit:

- `physical`,
- `assigned`,
- `reserved`,
- `available`,
- `incoming_transit`,
- `reservable`,
- `is_available`,
- `balance_is_valid`,
- `reason_code`,
- `explanation`.

Die stabilen Begründungscodes lauten:

- `not_physical`: keine physische Kopie,
- `assigned_only`: nur die implizit zugeordnete Albumkopie,
- `legacy_surplus_available`: mindestens eine freie Überschusskopie.

`StickerInventoryDTO.availability` und
`AlbumInventoryDTO.availability(code)` stellen dieses DTO zentral bereit. Für
einen fehlenden Code liefert der Albumzugriff nachvollziehbar den Nullzustand.
`AlbumInventoryDTO.availabilities` ist schreibgeschützt.

## Kompatibilität und umgestellte Lesepfade

Verhaltensgleich auf Availability umgestellt wurden:

- Albumfortschritt und angezeigte Anzahl Doppelter,
- Papierliste mit fehlenden und mehrfach vorhandenen Exemplaren,
- Mengenprüfung beim Papierlisten-Transfer,
- erhältliche Lücken in der Sammlung,
- Matching-Vorschau,
- Partner und Codes der Album-Tauschbörse,
- Dealzusammenstellung,
- Mengenprüfung beim Erstellen einer Tradeanfrage,
- Partnerzählung der globalen Tradezentrale.

Die neue Funktion `availability_trade_candidates` verwendet:

```text
fehlend: physical == 0
anbietbar: available > 0
maximale Anzahl: available
```

Im heutigen Modell sind diese Regeln exakt gleichbedeutend mit den bisherigen
Prüfungen `quantity == 0`, `quantity >= 2` und `quantity - 1`.

Die bisherige `trade_candidates`-Funktion und `quantities`-Projektion bleiben
als Kompatibilitäts- und Golden-Master-Weg erhalten. Es wurde keine
Tradefachlogik und kein sichtbares Ergebnis verändert.

Globale Statistik- und Trophy-Pfade, die direkt das redundant gespeicherte
Legacy-Feld `duplicates` auswerten, wurden bewusst nicht umgestellt. Wegen der
in S10 dokumentierten Legacy-Mehrfachanlage wäre dort nicht für alle Altwerte
eine identische Ausgabe garantiert.

## Tests

Nur S11:

```sh
python3 -m unittest discover -s tests -p 'test_s11_*.py' -v
```

Ergebnis: 10 von 10 S11-Tests erfolgreich.

Geprüft wurden insbesondere:

- Mengen `0`, `1`, `2` und `5`,
- defensive Projektion weiterer negativer und positiver Eingangswerte,
- `available >= 0`,
- `available <= physical`,
- exakte Bilanz `physical = assigned + reserved + available`,
- konstantes `reserved = incoming_transit = 0`,
- Begründungscodes und verständliche Erklärtexte,
- vollständige Fixture-Kompatibilität,
- vorhandene und fehlende Codes im S09 Read Service,
- identische Sammlung-, Fortschritts- und Papierlistenwerte,
- identische Get-/Give-Matchingresultate von altem Mengenpfad und neuer
  Availability-Projektion,
- read-only Komponente und unverändertes Schema,
- Schutz der Produktivdatenbank und kanonischen S00-Fixture.

Vollständiges Gate S01–S11:

```sh
python3 -m unittest discover -s tests -p 'test_s*.py' -v
```

Ergebnisse der beiden abschließenden vollständigen Läufe:

- Lauf 1: 133 von 133 Tests erfolgreich, `OK`.
- Lauf 2: 133 von 133 Tests erfolgreich, `OK`.

Prüfsummen unmittelbar vor und nach beiden Abschlussläufen:

```text
sammlr.db:               81233bc3fd85e2500d809c8c87e782b5b670ea1daee2012ddc53ca477f948fc9
sammlr_reference_s00.db: 21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971
```

Beide Prüfsummen blieben über die Abschlussläufe identisch. Sämtliche S11-Tests
arbeiteten auf temporären Fixture-Kopien. Die bereits vorhandene,
nutzerverwaltete Arbeitsbaumänderung an `sammlr.db` wurde nicht als Testziel
verwendet und nicht zurückgesetzt.

`git diff --check` meldete keine Fehler. Die Scope-Suche fand in der neuen
Availability-Komponente weder DML, Transaktionsbefehle noch Schemaanweisungen.

## Offene Punkte für S12

Nur dokumentiert und nicht umgesetzt wurden:

- ein zentraler Guard-Vertrag für Bestandscommands,
- erklärbare Warn-/Blockierfehler und UI-neutrale Fehlercodes,
- die Prüfung einer gebundenen Mindestmenge vor einer Mutation,
- Test-Doubles für eine spätere Bindungs- oder Reservierungsquelle,
- atomare Behandlung einer Availability-Prüfung gemeinsam mit dem
  nachfolgenden Schreibcommand,
- die Entscheidung, wie vertragswidrige Legacy-Daten einem Guard gemeldet
  werden.

S11 stellt dafür ausschließlich erklärbare Lesedaten bereit. Kein Guard und
keine Reservierungsdurchsetzung wurden begonnen.

## Umfangsbestätigung

Es wurde ausschließlich Sprint S11 umgesetzt.

S12 wurde nicht begonnen. Es wurden keine Reservierungen, Inventory Guards,
Tabellen, Spalten, Migrationen, UI-, CSS-, Notification-, Tradezustands- oder
Produktänderungen umgesetzt. Das sichtbare Verhalten blieb unverändert.

Es wurden kein Commit und kein Push durchgeführt.
