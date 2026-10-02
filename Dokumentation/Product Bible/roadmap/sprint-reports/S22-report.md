# Sprint-Report S22 – Smart-Trade-Anfragen und transparente Paketänderungen

Stand: 2026-08-07

## Ergebnis

S22 ist umgesetzt und release-ready. Konfliktfreie S21-Pakete werden in einer
eigenen read-only Ansicht eindeutig als Smart-Paket gezeigt, sind nicht
editierbar und können über die bestehende TradeRequest-Architektur angefragt
werden. Limit, Ablauf und Availability-Recheck gelten ausschließlich für
Smart-Anfragen. Der manuelle Dealwizard und seine Fairnessregel bleiben
unverändert.

## Ziel und umgesetzte Product-Owner-Regeln

- global höchstens drei gleichzeitig offene Smart-Anfragen je Absender,
- manuelle Anfragen werden nicht mitgezählt,
- exakter Ablauf nach 48 Stunden in den Status `expired`,
- Ablaufprüfung ausschließlich beim Öffnen, Annehmen und Ablehnen,
- Availability-Recheck beim Absenden, Öffnen und Annehmen,
- keinerlei automatische Paketverkleinerung oder Stickerentfernung,
- teilweise noch ausführbares, aber verändertes Paket bleibt unverändert
  `open`; die Annahme ist gesperrt,
- nicht mehr bilateral ausführbares Paket wird `obsolete`,
- Partnerausschluss gilt nur für den aktuellen Rechenrequest und wird nicht
  gespeichert,
- keine Migration und keine neue Datenbankstruktur.

## Architektur

Der neue `SmartTradeRequestService` kapselt die komplette neue S22-Fachlogik.
Er verwendet für jeden Recheck ausschließlich
`InventoryReadService.snapshot(...)`. Die S21-Optimierung wird unverändert
über `TopMatchOptimizationService` aufgerufen.

Die migrationsfreie Kennzeichnung nutzt für eine noch nicht angenommene
Smart-Anfrage den exakt reservierten Legacy-Wert `from_confirmed = -22`.
Manuelle Werte `0` und `1` bleiben unberührt. Nach Annahme setzt der bestehende
Reservierungsservice die Legacy-Bestätigungsfelder wie bisher zurück; ein rein
informatives Lifecycle-Event `smart_request_accepted` erhält dann die
Smart-Herkunft für Darstellung und Historie.

### Neue DTOs und Codes

- `SmartPackageRecheckDTO`
- `SmartTradeRequestStateDTO`
- `SmartTradeRequestCode`
  - `ready`
  - `created`
  - `limit_reached`
  - `package_changed`
  - `obsolete`
  - `expired`
  - `invalid_request`
  - `unauthorized`
  - `not_smart`

Alle neuen DTOs sind immutable. Die Routen enthalten keine zweite
Availability-Berechnung.

## Datenfluss

### Berechnen und Absenden

1. Albumkatalog und aktuelle, albumgebundene Partner werden gelesen.
2. Ein optionaler Partnerausschluss wird nur auf diese Berechnung angewendet.
3. Der unveränderte S21-Service erzeugt höchstens drei konfliktfreie Pakete.
4. Die UI zeigt Codes und Mengen read-only; es existieren keine editierbaren
   `give_codes`-/`get_codes`-Felder.
5. Beim POST werden S21-`result_id` und ausgewähltes Partnerpaket neu berechnet
   und verglichen.
6. Der S22-Service prüft unter `BEGIN IMMEDIATE` das globale Limit und die
   exakte Availability beider Richtungen.
7. Nur ein vollständig unverändertes Paket wird als `trade_requests`-Zeile
   gespeichert; Anfrage und bestehender Notification-Hook committen atomar.

### Öffnen, Annehmen und Ablehnen

- Öffnen prüft Teilnehmerberechtigung, Ablauf und Availability.
- Ein verändertes Paket zeigt die konkret nicht mehr freien Codes und Mengen;
  die gespeicherten JSON-Codepakete bleiben unverändert.
- Annehmen wiederholt Ablauf und Recheck. Nur `ready` delegiert an den
  unveränderten `TradeReservationService.accept(...)`.
- Ablehnen prüft vor dem vorhandenen Ablehnungspfad ausschließlich den Ablauf.
- Nach erfolgreicher Annahme erzeugt der vorhandene Service Lifecycle,
  Positionen und Reservierungen wie bisher; S22 ergänzt nur das informative
  Herkunftsevent.

## Neue Dateien

- `App/services/smart_trade_requests.py`
- `tests/test_s22_smart_trade_requests.py`
- `Dokumentation/Product Bible/roadmap/s22-smart-trade-requests.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S22-report.md`

## Geänderte Dateien

- `App/webapp.py`
  - S22-Service eingebunden,
  - albumbezogener Smart-Trade-Einstieg und read-only Paketansicht,
  - Smart-Request-POST,
  - Ablauf-/Recheck-Integration beim Detailaufruf, Annehmen und Ablehnen,
  - eindeutige Smart-Kennzeichnung und transparente Konflikthinweise,
  - bestehender Annahmepfad ausschließlich um den vorgeschalteten S22-Check
    und das Herkunftsevent ergänzt.
- `Dokumentation/Product Bible/roadmap/README.md`
  - Verweise auf S21 und S22 ergänzt,
  - S22 als abgeschlossen dokumentiert.

## Unveränderte Komponenten

- Shared Availability Snapshot und `InventoryReadService`,
- `TradeCoverageService`,
- `TopMatchOptimizationService`,
- `TradeReservationService`,
- Inventory Read/Write/Availability/Guard,
- Shipping-, Receipt- und Problem-Services,
- Datenbankschema und Migrationen,
- manueller Dealwizard und Regel `geben >= bekommen`,
- bestehende Versand-, Empfangs-, Problem- und Abschlusslogik,
- CSS und Designsystem.

## Testmatrix

| Bereich | Abdeckung |
| --- | --- |
| Erzeugung | Marker, Status, keine Reservierung, keine Inventory-Mutation |
| Limit | drei offene Smart-Anfragen global; manuelle Anfragen ausgeschlossen |
| Ablauf | exakte 48-h-Grenze; Öffnen, Annehmen und Ablehnen als Trigger |
| Recheck | vollständig verfügbar, teilweise verändert, bilateral unmöglich |
| Transparenz | konkrete nicht mehr freie Codes/Mengen, keine JSON-Anpassung |
| Happy Path | UI → Anfrage → vorhandene Annahme → zwei Reservierungen |
| Herkunft | `smart_request_accepted` genau einmal beim Happy Path |
| Sicherheit | fremder Nutzer kann weder öffnen noch annehmen |
| Vorschlagskonsistenz | veraltete S21-`result_id` wird ohne Anfrage abgewiesen |
| Ausschluss | request-lokal, keine Spalte und keine Speicherung |
| Manuell | Wizard bleibt editierbar; manueller Request bleibt normal markiert |
| Regression | vollständige S01–S22-Suite |

## Testbefehle und Ergebnisse

Gezielter ausführbarer Modulbefehl:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_s22_smart_trade_requests -v
```

Ergebnis: **16 Tests, 16 erfolgreich**.

Der vorgegebene Ausdruck
`python3 -m unittest tests.test_s22_* -v` ist kein gültiger
`unittest`-Modulname; `unittest` versucht dabei wörtlich das Modul
`tests.test_s22_*` zu importieren. Deshalb wurde der konkrete Modulname oben
verwendet.

Vollständiges Gate, finaler Stand:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p "test_s*.py" -v
```

- finaler Lauf 1: **357 Tests, 357 erfolgreich**
- finaler Lauf 2: **357 Tests, 357 erfolgreich**

Zusätzlich war die Syntaxprüfung von Service, Webapp und S22-Test erfolgreich.

## Release Readiness

- lokaler Migrationsstand read-only geprüft: **V0005**,
- für S22 erforderliche Migration: **nein**,
- Migration ausgeführt: **nein**,
- `PRAGMA integrity_check`: **ok**,
- `PRAGMA foreign_key_check`: **keine Befunde**,
- lokale Datenbank und kanonische S00-Fixture durch Hash-Prüfungen der
  isolierten Tests unverändert,
- ausschließlich temporäre, auf V0005 migrierte Testkopien verwendet,
- `git diff --check`: **ohne Befund**,
- kein Commit,
- kein Push.

## Bekannte Grenzen

- Der Ablauf ist gemäß Product-Owner-Entscheidung absichtlich lazy und wird
  nicht durch Hintergrundarbeit ermittelt.
- Ein teilweise verändertes Paket bleibt bis Ablehnung, neuer Entscheidung
  oder Ablauf offen und belegt weiterhin einen der drei Plätze; es wird nie
  automatisch angepasst.
- Eine Neuberechnung kann nur der ursprüngliche Absender als eigenes
  S21-Paket auslösen. Der Empfänger kann die nicht mehr ausführbare Anfrage
  abbrechen beziehungsweise ablehnen.
- Ein öffentliches Fremdprofil wurde nicht erfunden. Das Projekt besitzt noch
  keine freigegebene fremde Profilroute oder Privacy-Regeln; S22 zeigt daher
  den vorhandenen Partnernamen, ohne spätere Profil-/Community-Arbeit
  vorzuziehen.
- Es gibt weder Cross-Album-Pakete noch Ranking nach Bewertung oder Strategie.

## Offene Punkte für S23

- Das neue Smart-Anfrage-Ereignis und die bestehende Smart-Notification können
  in S23 typisierte Zielobjekte und sichere Deep Links erhalten.
- S22 hat keine Notification-Typisierung, Deduplizierungsarchitektur oder
  Notification-Migration vorgezogen.

## Scope-Bestätigung

- ausschließlich S22 umgesetzt,
- S23 nicht begonnen,
- keine Migration und keine neue Datenbankstruktur,
- keine Änderung an S17–S21-Fachlogik,
- keine Änderung an Inventory-, Reservierungs-, Versand-, Empfangs- oder
  Problemlogik,
- keine automatische Paketänderung,
- keine UI-Politur oder CSS-Änderung,
- kein Commit,
- kein Push.
