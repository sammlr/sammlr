# Repository-Inventur

## Stand und Methode

Stand: 14. August 2026. Analysiert wurde der vollständige aktuelle Checkout einschließlich unversionierter Dateien; `.git/` wurde nur über Git-Metadaten ausgewertet, `.venv/` als generierte Abhängigkeitsumgebung inventarisiert. Es wurden keine Dateien gelöscht, verschoben oder bereinigt.

## Root-Verzeichnisse

| Pfad | Vermuteter Zweck | Befund |
| --- | --- | --- |
| `.git/` | Git-Metadaten | Technischer Repository-Bestand; nicht als Projektinhalt klassifiziert. |
| `.venv/` | Lokale Python-Umgebung und installierte Abhängigkeiten | Generiert, etwa 20 MB; enthält 26 fremde `.md`/`.txt`-Dateien aus Paketen. Die interne `.venv/.gitignore` ignoriert nur Inhalte innerhalb der Umgebung; eine Root-Ignore-Regel fehlt. |
| `App/` | Hauptanwendung mit Web-App, Services, Templates, Static Assets und Datenbankcode | Enthält zusätzlich lokale Datenbanken, Caches und mehrere Backup-/Rescue-Versionen direkt neben aktivem Code. |
| `App_backup_header_refactor/` | Vermuteter früherer Backup-Ort | Aktuell nur leerer Unterordner `Backups/`; Zweck und Weiterverwendung unklar. |
| `Archive/` | Historische Anwendungskopien | Parallel zu `Backups/` und `App/Archive/`; enthält ältere `app.py`-/`webapp`-Kopien. |
| `Backups/` | Datenbank- und Quellcode-Backups | Enthält zahlreiche historische Python-Kopien und mehrere lokale SQLite-Backups. |
| `Branding/` | Corporate Identity, Design Bible, Logos, App Icons und Social-Media-Vorlagen | Eigener verbindlich wirkender Marken-/Assetbereich; überschneidet sich thematisch mit Product-Bible- und Post-RC-Designsystemen. |
| `Dokumentation/` | Hauptdokumentation | Enthält `Product Bible/` und `Post-RC/`; zusätzlich `.DS_Store`-Artefakte. |
| `Exports/` | Exportierte Fehlenden-/Doppeltenlisten | Laufzeit-/Nutzerdaten, keine Projektdokumentation; enthält eine auffällige temporäre `.sb-*`-Datei. |
| `Scripts/` | Wartung, Backup, Restore, Predeploy, Performance und Datenreparatur | Enthält ausführbare Hilfsskripte und generierten `__pycache__`. Teilweise ähnliche Reparaturskripte auch unter `App/Database/`. |
| `docs/` | Historischer Dokumentationsort | Enthält nur den Hinweisindex `ux_audit.md`; parallel zum deutschen Hauptordner `Dokumentation/`. |
| `tests/` | Automatisierte Regression-, Contract-, Security-, Operations- und RC-Tests | Sprintorientierte Tests `S00` bis `S38` sowie generierte Caches. |

## Wichtige Root-Dateien

| Pfad | Zweck / Befund |
| --- | --- |
| `app.py` | Schlanker Runtime-Einstieg der Anwendung. |
| `Procfile` | Deployment-/Prozessdefinition; verweist auf Gunicorn und `App.performance_wsgi`. |
| `requirements.txt` | Python-Abhängigkeiten; technisch notwendig, keine Projektdokumentation. |
| `sammlr_logo_transparent.png` | Root-Kopie eines Logos; Duplikat beziehungsweise Variante zu Branding- und App-Assets. |
| `sammlr_patch_master_v1.png` | Root-Kopie eines Trophy-/Patch-Assets; ähnliche Datei unter Branding und App-Static. |
| `    vfl_official_logo.png` | Bilddatei mit führenden Leerzeichen im Dateinamen; Ablage und Benennung sind auffällig. |
| `ball vorlage sammlr.` | Datei ohne erkennbare Erweiterung und ohne eindeutigen Zweck. |
| `.DS_Store` | macOS-Metadatei; bereits von Git verfolgt und aktuell verändert. |

Eine Root-`README.md`, ein Dependency-Lockfile und eine Root-`.gitignore` wurden nicht gefunden.

## Anwendung und Datenhaltung

- `App/webapp.py` ist der große Anwendungseinstieg; `App/services/` enthält fachlich getrennte Services.
- `App/templates/` und `App/static/` enthalten UI-Templates und ausgelieferte Assets.
- `App/Database/` enthält Datenbankzugriff, Referenzdaten, Migrationen, Reparatur- und Recovery-Werkzeuge sowie mehrere SQLite-Dateien.
- `App/Archive/`, `App/webapp_backup.py`, `App/webapp_blob_backup.py`, `App/webapp_broken_now.py` und `App/webapp_rescue_candidate.py` mischen historische beziehungsweise diagnostische Kopien in den aktiven Anwendungsbaum.
- `App/Backups/` existiert zusätzlich, war zum Inventurzeitpunkt jedoch leer.

## Dokumentationsorte

- `Dokumentation/Product Bible/`: langfristige Produktspezifikationen sowie aktuell auch Roadmaps, Design-, Security-, Operations-, Release- und Sprintunterlagen.
- `Dokumentation/Post-RC/`: aktueller Prozess von RC1 zur Closed Beta.
- `Branding/Corporate ID/` und `Branding/Design Bible/`: Marken-, Design- und Assetdokumentation.
- `docs/ux_audit.md`: historischer Verweis auf die neue Post-RC-Struktur.
- Vereinzelte `README.md`-Dateien unter Branding dokumentieren Assetquellen und Master Assets.

Die vollständige Einordnung steht in [`documentation-index.md`](documentation-index.md).

## Teststruktur

- 39 `test_*.py`-Dateien decken die Sprintfolge S00 bis S38 ab; S18, S19 und S20 besitzen jeweils zusätzliche beziehungsweise geteilte Testdateien.
- `tests/__init__.py` macht den Testordner zum Python-Paket.
- `tests/__pycache__/` enthält generierte Bytecode-Dateien.
- Testnamen spiegeln die historische Sprint-/Roadmap-Struktur wider und koppeln die Tests organisatorisch an diese Historie.

## Scripts und Tools

- `Scripts/backup_sqlite.py`, `restore_sqlite.py` und `predeploy.py`: Betriebs-, Backup- und Deployment-Werkzeuge.
- `Scripts/s35_performance_baseline.py`: historisches Performance-Messwerkzeug.
- `Scripts/repair_database.py`, `repair_quantity.py`, `repair_vfl_database.py`: Reparaturwerkzeuge.
- `Scripts/em24_structure.py` und `sticker.py`: Daten-/Stickerhilfen; genauer langfristiger Status unklar.
- Ähnliche Reparaturdateien liegen zusätzlich unter `App/Database/`; dies ist eine auffällige Doppelstruktur.

## Backups und Archive

Es bestehen mindestens vier parallele Ablageformen:

1. `Archive/` mit historischen Anwendungskopien.
2. `Backups/` mit Quellcode- und Datenbankkopien.
3. `App/Archive/` sowie Backup-/Rescue-Dateien direkt unter `App/`.
4. `App/Database/Database:Backups/` mit fünf SQLite-Backups.

Zusätzlich existieren lokale Pre-Migration-Backups in `Backups/` und einzelne Datenbankkopien direkt in `App/Database/`. Diese Struktur ist weder einheitlich benannt noch klar nach versionierter Historie, lokaler Recovery und produktivem Laufzeitbestand getrennt.

## Assets und Branding

- `Branding/` ist mit Corporate ID, Design Bible, Source Assets, Master Assets, Trophy Families, Logos und App Icons grundsätzlich nachvollziehbar gegliedert.
- `App/static/` enthält für die Runtime benötigte Kopien.
- Weitere Logo- und Patchkopien liegen im Repository-Root.
- `Dokumentation/Product Bible/design-system/screens/` enthält sieben RC-UI-Screenshots. Sie sind als visuelle Evidenz plausibel, benötigen aber eine klare Kennzeichnung als historischer Referenzstand, sobald das neue Design System beginnt.

## Runtime und Deployment

- `Procfile`, `app.py` und `App/performance_wsgi.py` bilden den Runtime-/Deployment-Einstieg.
- `requirements.txt` definiert Dependencies, pinnt Versionen aber nicht durchgehend reproduzierbar fest.
- Datenbankmigrationen liegen unter `App/Database/migrations/`; Backup/Restore/Predeploy unter `Scripts/`.
- Betriebsdokumentation liegt unter `Dokumentation/Product Bible/operations/`, Releasebefunde unter `release/` und technische Sprintdetails zusätzlich unter `roadmap/` und `sprint-reports/`.

## Auffällige Doppelstrukturen und unklare Ablageorte

- `Dokumentation/` und `docs/` sind zwei Dokumentationswurzeln.
- Product Bible, Branding Design Bible und Post-RC Design System überschneiden sich bei visuellen Regeln.
- `Archive/`, `Backups/`, `App/Archive/`, `App/Backups/`, `App/Database/Database:Backups/` und Backupdateien direkt unter `App/` bilden mehrere historische Ablagen.
- Reparaturskripte liegen sowohl in `Scripts/` als auch in `App/Database/`.
- Produkt-Roadmap, Sprintverträge und Sprintberichte liegen gemeinsam unter `Product Bible/roadmap/`, obwohl sie unterschiedliche Aktualität und Beweiskraft besitzen.
- Logos und Patch-Assets existieren in Root, Branding und `App/static/`.
- `App_backup_header_refactor/` ist leer und sein Zweck unklar.
- `ball vorlage sammlr.` und `App/Database/repair_vfl_database.py.txt` haben unklaren beziehungsweise keinen Inhalt.

## Hygiene-Check

### `.gitignore`

Im Repository-Root existiert keine `.gitignore`. Dadurch gibt es keine projektweite Regel für virtuelle Umgebungen, Bytecode, macOS-Metadaten, lokale Datenbanken, temporäre Dateien oder lokale Backups. Die Datei `.venv/.gitignore` schützt nur den Inhalt der lokalen virtuellen Umgebung und ersetzt keine Root-Regel.

### Generierte und lokale Dateien

- Mehrere `__pycache__/`-Ordner und mindestens 41 unversionierte `.pyc`-/Cachepfade sind im Arbeitsbaum sichtbar.
- 13 `.DS_Store`-Dateien werden bereits von Git verfolgt; weitere existieren im Checkout.
- `.venv/` liegt im Repository-Arbeitsbaum und ist nur durch ihre eigene interne Ignore-Datei lokal abgeschirmt.
- `Exports/em24_doppelte.txt.sb-dbb357db-Ma1uD4` wirkt wie eine temporäre Editor-/Sandboxdatei.

### Datenbanken und Backups

- Neun Datenbankdateien beziehungsweise Datenbankbackups werden von Git verfolgt, darunter die aktive `App/Database/sammlr.db`, eine Referenzdatenbank und historische Backups.
- Weitere lokale Pre-Migration- und Debugdatenbanken sind unversioniert vorhanden.
- Die Mischung aus Fixture, aktiver lokaler Runtime-DB, Debug-DB und Backups erschwert die Erkennung, welche Datenbank reproduzierbarer Projektbestand sein soll.

### Historische Dateien und Reports

- `Product Bible/roadmap/sprint-reports/` enthält 47 historische Berichte einschließlich Debug-Smokes, lokaler Migrationschecks und Nummerierungsbereinigung.
- Die historischen Dateien sind wertvolle Evidenz, liegen aber neben als aktuell bezeichneten Roadmap-Dokumenten und sind nicht als abgeschlossenes Archiv abgegrenzt.
- Mehrere Quellcodekopien tragen Namen wie `backup`, `broken`, `rescue` oder `Kopie` und liegen außerhalb eines einheitlichen Archivs.

## Empfehlungen – nicht ausgeführt

1. Eine bewusste Root-`.gitignore`-Policy für `.venv`, `__pycache__`, `*.pyc`, `.DS_Store`, temporäre Editor-Dateien und klar definierte lokale Runtime-Artefakte beschließen; bereits verfolgte Dateien separat prüfen.
2. Backup-/Archivorte inventarbasiert konsolidieren und zwischen versionierter historischer Evidenz, lokalen Recovery-Backups, Fixtures und aktiver Runtime-Datenbank unterscheiden.
3. Roadmap- und Sprintunterlagen nach Abschlussstatus klar als historisch kennzeichnen und den Widerspruch zwischen alter „aktueller“ Roadmap und Post-RC Master Plan auflösen.
4. Branding-, Runtime- und Root-Assetkopien anhand einer kanonischen Assetquelle prüfen; Rootdateien mit unklaren Namen oder ohne Erweiterung zuordnen.
5. Technische Dokumentation aus Roadmap, Sprintreports, Operations, Security und Release durch Verweise auf eindeutige kanonische Verträge entflechten, ohne Evidenz zu verlieren.
