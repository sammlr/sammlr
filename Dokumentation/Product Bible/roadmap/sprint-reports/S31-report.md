# Sprintbericht S31 – UI Foundation und globale Workflow-Vereinheitlichung

Stand: 2026-08-09

## Ziel und Ergebnis

S31 migriert die produktiven Hauptseiten und Workflows auf das in S30
festgeschriebene Designsystem. Home, Sammlung, Album, Stickerwall,
Tauschbörse, Tradeanfragen, laufende Deals, Dealansicht, Notifications,
Profil, Freundesliste und Suche verwenden nun dieselbe visuelle Sprache für
Seitenshells, Karten, Buttons, Formulare, Dialoge, Tabs, Listen, Filter,
Badges, Statuschips, Leerzustände und Aktionshierarchien.

Es wurden keine neue Produktfunktion, kein neuer Fachzustand, kein neuer
Schreibpfad und keine Migration eingeführt. S32 wurde nicht begonnen.

## Architektur und Datenfluss

```text
S30 Design Tokens
  -> s31-product-page als begrenzte Produktshell
  -> globaler Header
     -> large: Home / Sammlung / Profil
     -> compact: Details / Listen / Workflows / Deals
  -> mobile Dreier-Navigation
     -> Sammlung / Home / Tauschen
  -> gemeinsame CSS-Komponentenfamilien
  -> unveränderte Flask-Routen und bestehende Fachservices
```

Die serverseitigen Routen erzeugen weiterhin dieselben fachlichen Inhalte und
rufen dieselben Read-/Write-Services auf. S31 ergänzt ausschließlich
Darstellungsvarianten, semantische Klassen und CSS. Der mittlere `sammlr.`-Spot
bleibt auf Mobilgeräten zentral hervorgehoben; ab Desktopbreite wird die
Bottom-Navigation ausgeblendet. Profil und Notifications bleiben ausschließlich
als persönliche Aktionen oben rechts im Header. Die fokussierte Dealansicht und
die bestehende Papierlistenansicht behalten ihren kompakten Workflowheader ohne
Bottom-Navigation.

## Neue Komponenten und Dateien

- `Dokumentation/Product Bible/design-system/s31-ui-foundation.md`
- `Dokumentation/Product Bible/design-system/screens/home-390.png`
- `Dokumentation/Product Bible/design-system/screens/sammlung-390.png`
- `Dokumentation/Product Bible/design-system/screens/album-390.png`
- `Dokumentation/Product Bible/design-system/screens/stickerwall-390.png`
- `Dokumentation/Product Bible/design-system/screens/trade-390.png`
- `Dokumentation/Product Bible/design-system/screens/notifications-390.png`
- `Dokumentation/Product Bible/design-system/screens/profil-390.png`
- `tests/test_s31_ui_foundation.py`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S31-report.md`

Die neue technische Aktivierungsgrenze ist `s31-product-page`. Der vorhandene
Header unterstützt die Varianten `large` und `compact`; es wurde keine zweite
Headerimplementierung geschaffen. Die bestehenden Icons und Masterassets
werden wiederverwendet.

## Geänderte Dateien

- `App/webapp.py`: Header-Varianten, dreiteilige mobile Hauptnavigation,
  Produktshell-Klassen, Workflowheader und rein visuelle Statusvarianten.
- `App/static/style.css`: tokenbasierte S31-Shells und Komponentenfamilien,
  mobile Safe Area, Sticky Header/Navigation, Desktop-Fallback, Fokus- und
  Reduced-Motion-Regeln.
- `tests/test_s05_three_area_navigation.py`: verbindlicher Vertrag für genau
  drei fachliche Hauptziele und ausschließlich persönliche Headeraktionen.
- `tests/test_s30_design_foundation.py`: die historische S30-Hardcodeprüfung
  bleibt auf den S30-Block begrenzt und zählt den nachgelagerten S31-Block
  nicht als S30-Implementierung.
- `Dokumentation/Product Bible/roadmap/README.md`: Verweise und Sprintstand.

## Statusdarstellung

| Status | Darstellung |
|---|---|
| Reserviert | Blau |
| Versand läuft | Blau |
| Teilweise erhalten | Orange |
| Problem offen | Rot |
| Trade mit Problem beendet | Dunkelorange |
| Problem nachträglich gelöst | Grün |
| Abgelaufen | Grau |
| Obsolet | Grau |

Die Zuordnung ändert ausschließlich CSS-Varianten. Lifecyclewerte, Texte und
Übergänge bleiben unverändert.

## Unveränderte Komponenten

Unverändert bleiben Inventory und dessen Read-/Write-Pfade, Shared
Availability Snapshot, Coverage, TopMatch, Smart Requests, Trade Lifecycle,
Reservations, Shipping, Receipt, Problems, Ratings, Notification-Fachsystem,
Operational Home, Albumprivacy, Tradepool, Communityberechtigungen,
Datenbankschema und Migrationen. Die Stickerwall behält insbesondere Mengen-,
Batch-, Filter-, Transit- und Fortschrittslogik.

## Accessibility und Viewports

- 390 px und 430 px werden als mobile Zielbreiten behandelt.
- Touchziele sind mindestens 44 × 44 px groß.
- Tastaturfokus bleibt in semantischer DOM-Reihenfolge sichtbar.
- Native Dialoge bleiben per Escape schließbar.
- Statusinformationen werden nicht ausschließlich über Farbe vermittelt.
- Die S30-Kontrastpaare bleiben WCAG-2.2-AA-konform.
- `prefers-reduced-motion` wird berücksichtigt.
- Tablet und Desktop bleiben regressionssicher, werden in S31 nicht neu
  gestaltet; Desktop erhält keine Bottom-Navigation.

## Testmatrix

| Bereich | Prüfung | Ergebnis |
|---|---|---|
| Produktshell | produktive Hauptseiten verwenden S31, Auth-Seiten nicht | grün |
| Header | large/compact je verbindlichem Seitenkontext | grün |
| Navigation | drei Ziele, zentraler Home-Spot, aktive Zustände | grün |
| Deal/Papierliste | kompakter Fokusworkflow ohne Bottom-Navigation | grün |
| Komponenten | Tokens, Karten, Aktionen, Dialoge, Tabs, Statusfarben | grün |
| Accessibility | Fokus, Touchziele, Escape, Reduced Motion | grün |
| Nebenwirkungsfreiheit | UI-GETs verändern keine Fachdaten | grün |
| Migrationen | keine neue Migration, Repository bleibt maximal V0009 | grün |
| Referenzscreens | sieben erwartete PNG-Dateien vorhanden | grün |
| Regression | vollständige Tests S01–S31 | grün |

S31-spezifischer Lauf:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_s31_ui_foundation -v
Ran 10 tests – OK
```

Vollständiges Gate, Lauf 1:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p "test_s*.py" -q
Ran 463 tests in 4.928s – OK
```

Vollständiges Gate, Lauf 2:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p "test_s*.py" -q
Ran 463 tests in 4.993s – OK
```

## Referenzscreens

Die sieben 390-px-Referenzen wurden aus authentifizierten Renderings gegen
eine isolierte, temporär bis V0009 migrierte Kopie der S00-Fixture erzeugt.
Weder die lokale Entwicklungsdatenbank noch die kanonische Fixture waren Ziel
dieser Screen-Erzeugung. Die Screens sind im S31-Designsystemdokument direkt
eingebettet.

## UX-Review: verbindliche Navigationskorrektur

Die ursprünglich eingeführte fünfteilige Navigation wurde nach UX-Review
verworfen.

Verbindlich gilt dauerhaft die dreiteilige Bottom-Navigation mit Sammlung,
`sammlr.` und Tauschen.

Profil und Notifications bleiben ausschließlich im Header. Dadurch existiert
kein doppelter Einstieg in persönliche Bereiche. Header, Routen,
Berechtigungen und Fachlogik wurden für diese Korrektur nicht verändert.

Die Korrektur wurde mit den bestehenden S05-, S06- und S31-Tests sowie zwei
vollständigen, isolierten Regressionsläufen geprüft:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_s05_three_area_navigation \
  tests.test_s06_global_header_shell \
  tests.test_s31_ui_foundation -v
Ran 32 tests – OK

DATABASE_PATH=<isolierte-temporäre-db> PYTHONDONTWRITEBYTECODE=1 \
  python3 -m unittest discover -s tests -p "test_s*.py" -q
Lauf 1: Ran 463 tests in 4.907s – OK
Lauf 2: Ran 463 tests in 4.977s – OK
```

Die kanonische Fixture blieb bei
`21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`.
Der Rohdatei-Hash der lokalen V0007-Datenbank änderte sich während des
Zeitfensters dieser Gesamtgates erneut, obwohl beide Prozesse ausdrücklich mit
`DATABASE_PATH=/private/tmp/.../gate.db` gestartet wurden. Dies entspricht dem
bereits unter Release Readiness dokumentierten Isolations- beziehungsweise
externen Zugriffsbefund. Die UX-Korrektur enthält weder Datenbankzugriff noch
Migration; die lokale Datei wurde nicht zurückgesetzt oder anderweitig
bearbeitet.

## Release Readiness

- S31 benötigt und erzeugt keine Migration.
- Höchste im Repository vorhandene Migration: V0009.
- Lokale Entwicklungsdatenbank: V0007.
- `PRAGMA integrity_check`: `ok`.
- `PRAGMA foreign_key_check`: keine Befunde.
- SHA-256 lokale Entwicklungsdatenbank beim Abschluss:
  `667f5df8ad48c6f784a2f7364a83506f27f19977c31c8548eeac276aca256abb`.
- SHA-256 kanonische S00-Fixture:
  `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`.
- Sämtliche S31-Tests und Screen-Daten verwendeten isolierte temporäre
  Datenbanken.
- `git diff --check` wird im finalen Abschlussgate geprüft.

Der aktuelle lokale Datenbankhash unterscheidet sich vom im S30-Bericht
festgehaltenen Abschlusswert und änderte sich außerdem während des Zeitfensters
der vollständigen Regression. Die S31-spezifischen Tests und die
Screen-Erzeugung verwendeten nachweislich temporäre Datenbanken und schützen
lokale Datenbank sowie Fixture jeweils durch Hash-Guards; S31 führte keinen
Migrationsbefehl gegen die lokale Datei aus. Eine statische Prüfung der
S01–S31-Tests zeigt deren temporäre `DATABASE_PATH`-Bootstraps, grenzt aber die
Ursache der externen beziehungsweise historischen Gesamtgate-Berührung nicht
eindeutig ein. Da kein gesicherter S31-Eingangshash vorliegt, wird dieser
Befund transparent dokumentiert und die lokale Datenbank nicht spekulativ
zurückgesetzt. Schema V0007, `integrity_check` und `foreign_key_check` sind
unauffällig.

## Bekannte Grenzen und offene Punkte für S32

- Die Referenzscreens bilden die verbindlichen mobilen 390-px-Zustände ab;
  430 px wird über denselben Tokenvertrag getestet.
- Tablet und Desktop sind Regressionziele, aber bewusst kein S31-Redesign.
- Die endgültige Stickerwall-Ausarbeitung bleibt der späteren UI Week
  vorbehalten.
- Komplexe Animationen, Gestensteuerung und ein Icon-Redesign wurden nicht
  umgesetzt.
- S32 wurde nicht begonnen; dessen fachlicher Inhalt bleibt vollständig offen.

## Scope-Bestätigung

Es wurde ausschließlich S31 umgesetzt. Es gab keine neue Produktfunktion,
keine Fachlogikänderung, keine neue Migration und keine Arbeit an S32. Es
wurde kein Commit erstellt und kein Push durchgeführt.
