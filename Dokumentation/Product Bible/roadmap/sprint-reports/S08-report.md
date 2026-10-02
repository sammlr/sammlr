# Abschlussbericht – Sprint S08

Sprint S08 – Inventory-Invarianten und Zielmodell festschreiben ist vollständig
umgesetzt.

## Neue Dateien

- `tests/test_s08_inventory_contract_v1.py`
- `Dokumentation/Product Bible/roadmap/s08-inventory-contract-v1.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S08-report.md`

## Geänderte Dateien

- `Dokumentation/Product Bible/roadmap/README.md`

Anwendungscode, Stylesheets, Datenbankschema, Datenbankdateien und bestehende
Schreibpfade wurden für S08 nicht geändert. Die bereits vor S08 vorhandenen
Arbeitsbaumänderungen wurden nicht bearbeitet.

## Definierte Invarianten

Der Inventory Contract V1 definiert verbindlich:

1. Alle Mengen sind nichtnegative ganze Zahlen.
2. `physical = assigned + available + reserved` gilt exakt.
3. `available` ist abgeleitet, niemals negativ und niemals größer als
   `physical`.
4. `assigned`, `available` und `reserved` sind disjunkte Buckets jeder
   physischen Kopie.
5. Eine Reservierung darf die zuvor verfügbare Menge nicht überschreiten; eine
   Anfrage reserviert nichts.
6. Bestätigter Versand verschiebt eine reservierte Kopie aus `physical` nach
   `outgoing_transit`.
7. `incoming_transit` ist vor bestätigtem Empfang weder physisch, zugeordnet
   noch verfügbar.
8. Ausgehender und eingehender Transit derselben Dealposition sind zwei
   Perspektiven derselben Kopie und dürfen nicht doppelt gezählt werden.
9. Albumfortschritt entsteht ausschließlich durch die Zuordnung zur konkreten
   Albuminstanz.
10. Das heutige `quantity`-/`duplicates`-Verhalten bleibt vollständig
    kompatibel.

## Zielmodell

Die Betrachtungseinheit ist:

```text
(Nutzer, Albumtyp, Sticker-Code)
```

Definiert sind die Mengen:

- `physical`: beim Nutzer physisch vorhandene Kopien,
- `assigned`: konkreten Albuminstanzen zugeordnete physische Kopien,
- `available`: freie, nicht zugeordnete und nicht reservierte Kopien,
- `reserved`: für angenommene Deals gebundene physische Kopien,
- `outgoing_transit`: versendete, beim Empfänger noch nicht bestätigte Kopien,
- `incoming_transit`: dieselben unterwegs erwarteten Kopien aus Sicht des
  Empfängers.

Transit bleibt außerhalb der physischen Bilanz. Systemweite Summen dürfen
entweder ausgehenden oder eingehenden Transit addieren, niemals beide
Perspektiven derselben Dealposition.

## Kompatibilitätsmodell

Für das heutige Einzelalbum ohne Reservierungen und Transit gilt ausschließlich
als Projektion:

```text
physical = quantity
assigned = min(quantity, 1)
available = max(quantity - 1, 0)
reserved = outgoing_transit = incoming_transit = 0
duplicates = max(quantity - 1, 0)
```

Eine vorhandene Legacy-Zeile besitzt `quantity >= 1`; Menge null bleibt durch
eine fehlende Zeile repräsentiert. Diese Abbildung ist keine Migration und
erfindet keine heute nicht gespeicherten Zustände.

Stickerwall, Papierliste, Mengenregler, Albumfortschritt und heutiger Tradeflow
bleiben unverändert.

## Testübersicht

Nur S08:

```sh
python3 -m unittest discover -s tests -p 'test_s08_*.py' -v
```

Vollständiges Gate:

```sh
python3 -m unittest discover -s tests -p 'test_s0*.py' -v
```

Ergebnisse:

- S08: 15 von 15 Contract-Tests erfolgreich.
- Gesamtes Gate S01–S08: 102 von 102 Tests erfolgreich.
- Zwei vollständige Abschlussläufe endeten jeweils mit `OK`.
- Standard-Datenbank und kanonische S00-Fixture blieben während der
  Abschlussläufe unverändert.

Prüfsummen vor und nach den Abschlussläufen:

```text
sammlr.db:               273ae658eda0978887692ce3bdfd1e4df0f14da37bdc24a150931ccf541fd696
sammlr_reference_s00.db: 21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971
```

Die S08-Tests sind eine ausschließlich testlokale Referenzspezifikation. Sie
stellen keinen produktiven Inventory-Service und keine Lese-, Schreib-,
Reservierungs- oder Transitlogik bereit.

## Offene Punkte für S09

Nicht umgesetzt, sondern ausschließlich für S09 vorgemerkt sind:

- ein read-only Inventory-Service auf Basis des aktuellen Schemas,
- zentrale DTOs für physische, doppelte und verfügbare Mengen,
- die schrittweise Nutzung einer zentralen Leselogik,
- die bewusste Prüfung der Kompatibilitätsprojektion am Product-Owner-Gate vor
  einer produktiven Umsetzung.

Keine dieser Arbeiten wurde in S08 begonnen oder vorbereitet.

## Umfangsbestätigung

Es wurde ausschließlich Sprint S08 umgesetzt.

S09 wurde nicht begonnen. Es wurden keine Produktfunktionen, APIs,
Reservierungen, Availability-Berechnungen im Anwendungscode, Tabellen,
Migrationen, UI-, CSS-, Trade- oder Notificationänderungen und kein Refactoring
bestehender Funktionen vorgenommen.

Es wurden kein Commit und kein Push durchgeführt.
