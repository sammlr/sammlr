# Abschlussbericht – Sprint S04

Sprint S04 – Home- und Sammlungsrouten trennen ist vollständig abgeschlossen.

## Neue Dateien

- `tests/test_s04_home_collection_routes.py`
- `Dokumentation/Product Bible/roadmap/s04-home-collection-routes.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S04-report.md`

## Geänderte Dateien

- `App/webapp.py`
- `Dokumentation/Product Bible/roadmap/README.md`

Die vor S04 vorhandenen S03- und `.DS_Store`-Änderungen wurden nicht
bearbeitet.

## Testbefehl

Vollständiges Gate:

```sh
python3 -m unittest discover -s tests -p 'test_s0*.py' -v
```

Nur S04:

```sh
python3 -m unittest discover -s tests -p 'test_s04_*.py' -v
```

## Testergebnisse

- S04: 10 von 10 Tests erfolgreich.
- Gesamtes Gate S01–S04: 53 von 53 Tests erfolgreich.
- Zwei vollständige Abschlussläufe endeten jeweils mit `OK`.
- Standard-Datenbank und kanonische S00-Fixture blieben unverändert.

## Umgesetzte Akzeptanzkriterien

- `/` ist der eigenständige Home-Grundzustand.
- Home zeigt keine erfundenen Lifecycle-, Feed-, News-, Trade- oder
  Albumdaten.
- Die vollständige bestehende Sammlr-Zentrale ist unter `/sammlung`
  erreichbar.
- Albumkarten, Favorit, Vitrine und „Album hinzufügen“ bleiben funktionsfähig.
- `/home`, `/zentrale` und `/sammlr-zentrale` besitzen eindeutige
  Kompatibilitätsredirects.
- Login startet auf Home.
- Anonyme Home- und Sammlungsrouten bleiben gesperrt.
- Collection-spezifische Links und Rückwege führen stabil nach `/sammlung`.
- Bestehende Regressionstests bleiben grün.

## Codeänderungen und Begründung

`App/webapp.py` wurde ausschließlich für S04 geändert:

1. Die bisherige Zentrale wurde von `/` nach `/sammlung` verschoben, damit
   Sammlung einen stabilen fachlichen Besitzer besitzt.
2. `/` erhielt den minimalen, datenfreien Home-Grundzustand.
3. Drei schmale Kompatibilitätsredirects wurden ergänzt.
4. Collection-spezifische Rücklinks und Redirects wurden auf `/sammlung`
   umgestellt.
5. Ein direkter Rückweg vom Album zur Sammlung wurde ergänzt.

Es wurden keine fachlichen Bestands-, Trade-, Trophy- oder
Notification-Berechnungen geändert.

## Offene Punkte

Nicht umgesetzt wurden:

- Home-Aufgaben, Feed, News oder Tradezusammenfassungen,
- Glocken- oder Notification-UI,
- die dreiteilige Bottom-Navigation aus S05,
- eine Umbenennung der Sammlr-Zentrale,
- CSS, JavaScript oder Designänderungen.

## Umfangsbestätigung

Es wurde ausschließlich Sprint S04 umgesetzt.

S05 und spätere Sprints wurden nicht begonnen oder vorbereitet.
Datenbankschema und bestehende fachliche Kernlogik blieben unverändert.

Es wurden kein Commit und kein Push durchgeführt.

