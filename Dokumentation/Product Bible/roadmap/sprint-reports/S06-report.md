# Abschlussbericht – Sprint S06

Sprint S06 – Globaler Header mit Avatar- und Glocken-Shell ist vollständig
umgesetzt.

## Neue Dateien

- `tests/test_s06_global_header_shell.py`
- `Dokumentation/Product Bible/roadmap/s06-global-header-shell.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S06-report.md`

## Geänderte Dateien

- `App/webapp.py`
- `App/static/style.css`
- `Dokumentation/Product Bible/roadmap/s05-three-area-navigation.md`
- `Dokumentation/Product Bible/roadmap/README.md`

Die bereits vor S06 vorhandenen Änderungen an `.DS_Store`, `sammlr.db` sowie
die unversionierten Artefakte früherer Sprints wurden nicht bearbeitet.

## Testbefehl

Vollständiges Gate:

```sh
python3 -m unittest discover -s tests -p 'test_s0*.py' -v
```

Nur S06:

```sh
python3 -m unittest discover -s tests -p 'test_s06_*.py' -v
```

## Testergebnisse

- S06: 11 von 11 Tests erfolgreich.
- Gesamtes Gate S01–S06: 75 von 75 Tests erfolgreich.
- Zwei vollständige Abschlussläufe endeten jeweils mit `OK`.
- Standard-Datenbank und kanonische S00-Fixture blieben während der
  Abschlussläufe unverändert.

Prüfsummen vor und nach den Abschlussläufen:

```text
sammlr.db:               c493b5666e7239a25bf0c416bcf82eae10aa30e646ed4d2f3ac893f9ecf8cae7
sammlr_reference_s00.db: 21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971
```

## Umgesetzte Akzeptanzkriterien

- Home, Sammlung und Tauschen verwenden denselben wiederverwendbaren
  `app_header`.
- Die Sammlr-Marke bleibt der bestehende Home-Link.
- Der Initialen-Avatar führt zum bestehenden eigenen Profil unter `/profil`.
- Die Glocke führt zur neuen schmalen Shell unter `/notifications`.
- Die Notification-Shell zeigt entweder vorhandene ungelesene Einträge des
  eingeloggten Nutzers oder einen ehrlichen Leerzustand.
- Login und Registrierung zeigen keine privaten Headeraktionen.
- Fehlen Profilbilddaten oder verwertbare Namenswerte, bleibt der Avatar durch
  den neutralen Initialen-Fallback funktionsfähig.
- Bestehende Seitentitel, Fachseiten, Bottom-Navigation und Zurückwege bleiben
  erhalten.
- Eine mobile Headerregel hält Marke, Glocke und Avatar in derselben
  Headerfläche; beide Aktionen behalten 44 × 44 Pixel große Bedienflächen.

## Codeänderungen und Begründung

`App/webapp.py` wurde ausschließlich für die S06-Header-Shell geändert:

1. `app_header` rendert für eingeloggte Nutzer zwei globale Zielverknüpfungen.
2. Ein kleiner Initialen-Fallback liest nur vorhandene Nutzerfelder und legt
   weder Profilbilddaten noch neue Produktlogik an.
3. `/notifications` rendert mit dem bereits vorhandenen
   `unread_notifications()`-Adapter maximal fünf ungelesene Einträge oder den
   Leerzustand. Der Seitenaufruf verändert keinerlei Daten.

`App/static/style.css` erhielt nur die für Headeraktionen und kleine Viewports
notwendigen Layoutregeln. Es wurde kein finales Headerdesign umgesetzt.

Notification-Erzeugung, Read-State-Route, Trade-, Album- und Inventorylogik
sowie das Datenbankschema blieben unverändert.

## Dokumentation

- `s06-global-header-shell.md` dokumentiert Headerhierarchie, Avatar-Fallback,
  Glocken-Shell, mobile Grundfunktion und Abgrenzung.
- Die S05-Navigationsmatrix verweist nun auf die ergänzende S06-Headerhierarchie.
- Der Roadmap-Index verweist auf das S06-Artefakt und diesen Abschlussbericht.

## Offene Punkte für spätere Sprints

Nicht umgesetzt wurden:

- kontextabhängige Deep Links und Rückwege aus S07,
- typisierte Notification-Zielobjekte aus S23,
- Badge, Zähler, vollständige Historie, Pagination und Notificationzentrale aus
  S24,
- Home-Aufgaben, Friend Feed oder Sammlr News,
- finales Headerdesign oder Design Patch.

## Umfangsbestätigung

Es wurde ausschließlich Sprint S06 umgesetzt.

S07 und spätere Sprints wurden nicht begonnen oder vorbereitet. Es wurden
keine zusätzlichen Produktentscheidungen getroffen, keine neuen Tabellen oder
APIs ergänzt und weder Datenbankschema noch Trade-, Album- oder Inventorylogik
verändert.

Es wurden kein Commit und kein Push durchgeführt.
