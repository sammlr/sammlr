# R5 Phase A – Release Inventory + Plan

**Fortschreibung B1.2 (2026-09-06):** R4 final GREEN im unveränderten lokalen Vertrag: drei vollständige Reihen, jeweils 15/15 GREEN; keine Runtime-Änderung. [Untersuchung und Grenzen](R5_B12_PERFORMANCE_REPRODUCIBILITY.md). [16 PO-Walkthrough-Befunde](CLOSED_BETA_PO_WALKTHROUGH.md) nur dokumentiert. R5 bleibt NEXT, PO-Abnahme ausstehend. Frühere Phasenbewertungen unten sind historische Befunde.

Stand: 2026-09-06T09:32:28.503439+02:00 (Europe/Berlin). Nur Analyse, Roadmap-Status und dieses Dokument.
R4 ist PO-abgenommen / ACCEPTED / LOCKED. R5 bleibt NEXT. Phase B nicht begonnen.

## Ausgangsstand und Bewertung

- Branch: `feature/wm-special-trophies`
- HEAD: `1c0ecca4a6ec77fe3350cc47c67b97bf07bd238c`
- Dateigenauer Ausgangsstatus: **17 tracked modified, 1 tracked deleted, 2.333 untracked, 4.264 ignored**. Gezählt mit `git status --porcelain=v1 -uall --ignored`; Verzeichnisverdichtung erklärt Unterschiede zu älteren Zahlen. Kategorien unten verwenden einzelne Dateien, keine verdichteten Verzeichnisse.
- Clean Checkout: **RED**. HEAD enthält weder aktuelle Runtime-Änderungen noch zentrale neue Module, Assets und Migrationen.
- Dependencies: **RED** für exakte Reproduktion; requirements enthält lediglich unversioniertes Flask und gunicorn.
- Render-Reproduktion: **RED**; kein versionierter vollständiger Deploymentvertrag, Bootstrap und tatsächlich konfigurierte Provider-Einstellungen nicht nachgewiesen.
- Secrets / private Daten: **RED** wegen Nutzerdatenbanken, Portraits und ungeklärter Literal-Kandidaten. Keine Freigabe für pauschales Staging.

## Kategorisierte Inventur

Die Gruppen sind disjunkt: Caches haben Vorrang vor ihrem Quellverzeichnis, DBs/Uploads vor Runtime. K zählt nur separat erkennbare Testartefakte; Preview-Bilder innerhalb Branding bleiben H. Null bedeutet keine Datei nach dieser Regel, nicht pauschale Risikofreiheit.

| Kategorie | Untracked | Ignored | Beispiele (untracked, sonst ignored) | Release-Relevanz / Phase B |
| --- | ---: | ---: | --- | --- |
| A. Runtime / Betriebscode | 9 | 0 | `App/Database/migration_runner.py`; `App/Database/sqlite_recovery.py`; `App/performance_wsgi.py` | Ja: gezielt versionieren; Performance-Harness als Testwerkzeug kennzeichnen. |
| B. Templates | 4 | 0 | `App/templates/components/profile_sticker.html`; `App/templates/components/profile_sticker_70.html`; `App/templates/profile_sticker_edit.html` | Ja: alle vier Template-Dateien versionieren. |
| C. Static Assets | 43 | 0 | `App/static/ceoklaue-markers/give_cross/give_cross_01.svg`; `App/static/ceoklaue-markers/give_cross/give_cross_02.svg`; `App/static/ceoklaue-markers/give_cross/give_cross_03.svg` | Ja, nach Asset-/Portrait-Prüfung; persönliche Portraits separat freigeben. |
| D. Services / Module | 33 | 0 | `App/services/account_lifecycle.py`; `App/services/album_completion.py`; `App/services/album_privacy.py` | Ja: kanonische Services gezielt versionieren. |
| E. Migrationen | 40 | 0 | `App/Database/migrations/0001_trade_lifecycle_foundation.down.sql`; `App/Database/migrations/0001_trade_lifecycle_foundation.up.sql`; `App/Database/migrations/0002_trade_reservations.down.sql` | Ja: alle 20 Up-/Down-Paare und Runner versionieren. |
| F. Tests | 78 | 0 | `tests/__init__.py`; `tests/test_cb001_historical_collection_contract.py`; `tests/test_cb002_history_cutover.py` | Für RC-Nachweis ja; Fixtures auf private Daten prüfen. |
| G. Dokumentation | 209 | 0 | `Dokumentation/Post-RC/00-master-plan.md`; `Dokumentation/Post-RC/01-product-audit/01-login-registration.md`; `Dokumentation/Post-RC/01-product-audit/02-sammlr-zentrale.md` | Release-/Testverträge versionieren; historische Dokumente separat zuordnen. |
| H. Branding / Source Assets | 1743 | 0 | `Branding/CEOKlaue/00_raw/ceoklaue_alphabet_lower_symbols_01.jpg`; `Branding/CEOKlaue/00_raw/ceoklaue_alphabet_upper_01.jpg`; `Branding/CEOKlaue/00_raw/ceoklaue_analog_ui_final_01.jpg` | Teilweise: referenzierte Laufzeitassets zwingend; Entwürfe/Quellen nicht pauschal aufnehmen. |
| I. Lokale Daten / DB / Uploads | 8 | 1 | `App/Database/s20_coverage_debug.db`; `App/uploads/.gitignore`; `App/uploads/profile_portraits/.gitkeep` | Keine echten Nutzerdaten aufnehmen; bestehende tracked DBs separat entscheiden; synthetische Fixtures auditieren. |
| J. Caches / Logs / temporär | 163 | 1581 | `App/Database/__pycache__/database.cpython-313.pyc`; `App/Database/__pycache__/em24_data.cpython-313.pyc`; `App/Database/__pycache__/em24_structure.cpython-313.pyc` | Nein: künftig ignorieren; bereits tracked Artefakte nur explizit aus Index nehmen. |
| K. Screenshots / Testartefakte | 0 | 0 |  | Nur bewusst ausgewählte Abnahmenachweise, sonst ignorieren. |
| L. Lokale Entwicklungswerkzeuge | 3 | 2682 | `Scripts/cb004_validated_trophy_backfill.py`; `Scripts/r4_v20_performance_gate.py`; `Scripts/s35_performance_baseline.py` | Reproduktionsskripte ja; lokale venv nein, neu erzeugen. |
| M. Environment / Credentials-Dateien | 0 | 0 |  | Nein: ausschließen, Werte niemals dokumentieren. |
| N. Sonstige | 0 | 0 |  | Einzelfallprüfung vor Staging. |

Die 1.749 untracked Dateien unter `Branding/CEOKlaue` enthalten viele Arbeitsstände; ihre Anzahl ist kein Beleg für 1.749 notwendige Runtime-Assets. `Branding` darf dennoch nicht pauschal ausgeschlossen werden. Es fehlt eine Root-`.gitignore`; die venv schützt sich selbst über `.venv/.gitignore`.

### Tracked Änderungen gegenüber HEAD

- ` M .DS_Store`
- ` M App/.DS_Store`
- ` M App/Database/.DS_Store`
- ` M App/Database/sammlr.db`
- ` D App/services/notifications.py`
- ` M App/static/style.css`
- ` M App/trophy_definitions.py`
- ` M App/webapp.py`
- ` M Branding/.DS_Store`
- ` M "Branding/Design Bible/.DS_Store"`
- ` M Dokumentation/.DS_Store`
- ` M "Dokumentation/Product Bible/.DS_Store"`
- ` M "Dokumentation/Product Bible/decisions/README.md"`
- ` M "Dokumentation/Product Bible/roadmap/README.md"`
- ` M "Dokumentation/Product Bible/roadmap/development-roadmap-v1.md"`
- ` M tests/test_s01_inventory_regression.py`
- ` M tests/test_s02_tradeflow_regression.py`
- ` M tests/test_s04_home_collection_routes.py`

Die sichtbaren Hauptdifferenzen liegen in `App/webapp.py`, `App/static/style.css`, `App/trophy_definitions.py` und drei Regressionstests. `App/services/notifications.py` ist gelöscht; die aktuelle Runtime importiert die neuen typed-notification/history Services. Diese Ablösung muss als zusammenhängender Diff geprüft werden. HEAD enthält außerdem bereits DBs, Backups und Finder-Metadaten: eine neue ignore-Regel entfernt tracked Dateien nicht aus Git oder dessen Historie.

## Runtime Dependency Map

Statische Analyse vom Einstieg `SAMMLR_ENV=development PORT=8080 python3 App/webapp.py`; App wurde nicht gestartet oder importiert, weil DB- und Startseiteneffekte ausgeschlossen bleiben sollen.

| Einstieg / Oberfläche | Lokale Abhängigkeiten | Clean-Checkout-Lücke |
| --- | --- | --- |
| Appstart | `App/webapp.py`, `em24_data.py`, `wm26_data.py`, `trophy_definitions.py`, Flask/Werkzeug | HEAD-webapp ist älter; aktuelle Änderungen fehlen |
| Globale Fachlogik | `App/services/*.py`, darunter Inventory, Availability, Reservations, Lifecycle, Privacy, Auth, Notifications, Feed, Statistics | Neue Services untracked |
| Datenbankvertrag | `App/Database/migration_runner.py`, `sqlite_recovery.py`, `migrations/*.sql`, `services/runtime_operations.py` | Runner und V1–V20 untracked |
| Stickerliste | `App/sticker_list.py`, `templates/sticker_list.html`, `static/sticker_list.css`, `static/sticker_list.js` | Untracked, geschützte Fläche |
| Stickerwall | Darstellung in webapp, `static/sticker_wall_read_only.js`, gemeinsame Sticker-/CEOKlaue-Assets | JS und Assetfamilien fehlen HEAD |
| Profil / Profile Sticker | `profile_sticker.py`, vier Templates inkl. Komponenten, `profile_sticker.css/js`, `profile_v1.css`, `static/profile-sticker/` | Module und Assets untracked; Portrait-Daten gesondert prüfen |
| Tradehub / SmartMatch / Trades / Detail | webapp, globale CSS, Matching-/Coverage-/Trade-Services | Current Worktree nötig; kein separater Frontend-Build nachgewiesen |
| Branding | `Branding/Design Bible/01 Master Assets/`, `Branding/CEOKlaue/05_runtime/manifest.json`, weitere Source-Manifeste, Glyphen-/Harmony-/Repair-Pfade | Branding enthält Laufzeitabhängigkeiten außerhalb App/static |
| Static | Fonts, CEOKlaue-Marker/UI/Wordmark, Retro-Digits, Profile-Sticker-Assets | Referenzierte Dateien mit aufnehmen und URLs im isolierten Smoke prüfen |
| Produktion | `Procfile`, `Scripts/predeploy.py`, Backup-/Restore-Skripte | Betriebsdateien untracked |

`webapp.py` nutzt auch dynamisch zusammengesetzte Assetpfade und überwiegend inline erzeugtes HTML. Die statische Map beweist daher keinen vollständigen URL-/Asset-Smoke; Phase B benötigt einen Request-basierten Assetcheck. Direkter Development-Start verwendet fest Port 8080; die PORT-Variable steuert diesen Codepfad derzeit nicht. Produktion nutzt PORT im Gunicorn-Kommando.

## Secrets und private Daten

Es wurden Dateinamen sowie Textdateien außerhalb `.git` und `.venv` auf typische Key-Muster, Private-Key-Marker und Passwort-/Secret-Zuweisungen geprüft. Keine Werte wurden ausgegeben. Das ist ein heuristischer Scan, kein Beweis der Secret-Freiheit und kein Git-History-Audit.

**RED:** Kanonische DB, historische Backups und Upload-/Portrait-Dateien können echte private Daten bzw. Zugangsdaten enthalten. Die kanonische DB enthält vier Nutzerzeilen; fünf neue lokale Backups ebenfalls je vier. Auch bereits getrackte Altbackups enthalten Nutzerzeilen. Das S00-Referenzfixture enthält drei Nutzerzeilen und benötigt einen dokumentierten Nachweis synthetischer Daten. `App/Database/s20_coverage_debug.db` enthält eine Nutzerzeile. Keine Nutzerwerte wurden gelesen oder dokumentiert.

**RED:** `App/static/profile-sticker/valentin-portrait-source-v1.png` ist ein von der Runtime verwendetes persönliches Portrait-Fallback. `App/uploads/profile_portraits/` enthält weitere private Bilder, teils untracked/ignored. Veröffentlichung nur nach ausdrücklicher Entscheidung; keine Löschung oder Ersetzung in Phase A.

**RED zur Sichtung:** Folgende Dateien trafen auf Literal-Heuristiken. Treffer können Testwerte oder harmlose Ausdrücke sein; sie sind keine Behauptung kompromittierter Produktionscredentials:

- `App/webapp_rescue_candidate.py`
- `App/webapp_backup.py`
- `App/webapp_broken_now.py`
- `tests/test_cb014_profile_account_projection.py`
- `Scripts/r4_v20_performance_gate.py`
- `Backups/webapp_2026-06-02_22-14-50.py`
- `Backups/webapp_2026-06-02_22-14-58.py`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S34-report.md`
- `App/Database/database.py`
- `App/Archive/webapp_backup_session_ready.py`
- `App/Archive/webapp_backup_multiuser_albums.py`
- `App/services/account_lifecycle.py`

Phase B: Kandidaten lokal sichten und als synthetisch/harmlos oder echt klassifizieren, ohne Werte in Berichte zu übernehmen. Bei echten Credentials: ausschließen; Rotation und mögliche History-Bereinigung als separate PO-Entscheidung behandeln. Keine Environment-Werte, Git-Remote-Credentials oder private Git-Konfiguration wurden ausgegeben.

## Datenbank und Migrationen

**V1–V20 vollständig auf Dateiebene: ja**, 20 Up- und 20 Down-Dateien, alle untracked. Der Runner ist ebenfalls untracked. Kanonische DB read-only geprüft: Schema V20, `integrity_check=ok`, `foreign_key_check=0`.

**Leere DB → V20 allein mit dem Runner: nein.** Isolierter Versuch mit SQLite `:memory:` und explizitem `migrate(..., target_version=20)` scheitert mit `OperationalError: no such table: notifications`. Keine Dateidatenbank wurde hierfür erzeugt oder kopiert. Die Migrationen setzen ein Legacy-Basisschema voraus. `init_db()` in webapp enthält Basistabellen, ist aber kein nachgewiesener vollständiger, eigenständiger Bootstrap bis V20. R4 verwendet das getrackte `sammlr_reference_s00.db` als Ausgangsfixture; das erfüllt keinen nachgewiesenen Nullstart ohne Fixture.

Runtime-Standardpfad: `App/Database/sammlr.db`; `DATABASE_PATH` kann ihn überschreiben. Production fordert bereits beim Import `/var/data/sammlr.db` mit V20. `SEED_DB` zeigt auf die kanonische Arbeitsdatenbank; Seed-/Debug-Hilfsfunktionen können Dateien kopieren. Ihre bloße Existenz ist kein sicherer automatischer Erststartvertrag. Predeploy erstellt zunächst ein Backup einer vorhandenen DB und migriert diese; es löst den Erstaufbau einer fehlenden DB nicht.

### Alle lokalen DB-Dateien und Git-Status

- `App/Database/Database:Backups/collectr_backup_before_trophy_cleanup.db` — tracked.
- `App/Database/Database:Backups/collectr_backup_before_users.db` — tracked.
- `App/Database/Database:Backups/collectr_backup_popup_clean.db` — tracked.
- `App/Database/Database:Backups/collectr_backup_trophy_tabs_visual_runs.db` — tracked.
- `App/Database/Database:Backups/collectr_backup_users_trophy_clean_runs.db` — tracked.
- `App/Database/s20_coverage_debug.db` — untracked.
- `App/Database/sammlr.db` — tracked modified.
- `App/Database/sammlr_reference_s00.db` — tracked.
- `Backups/collectr_2026-06-02_22-14-58.db` — tracked.
- `Backups/sammlr_local_pre_v0003_20260802_091642.db` — untracked.
- `Backups/sammlr_local_pre_v0004_20260802_232331.db` — untracked.
- `Backups/sammlr_local_pre_v0005_20260803_211622.db` — untracked.
- `Backups/sammlr_local_pre_v0006_20260808_010509.db` — untracked.
- `Backups/sammlr_local_pre_v0007_20260808_023853.db` — untracked.

## Python / Dependency-Befund

Lokal beobachtet: Python 3.13.15. `.venv` enthält Flask 3.1.3, gunicorn 26.0.0, Werkzeug 3.1.8, Jinja2 3.1.6, MarkupSafe 3.0.3, itsdangerous 2.2.0, click 8.4.2, blinker 1.9.0 und packaging 26.3. `requirements.txt` enthält nur `Flask` und `gunicorn` ohne Pins. Keine Python-Versionsdatei oder Lockdatei gefunden.

AST-Analyse der Python-Dateien in App/Scripts/tests: aktuelle App benötigt Flask/Werkzeug neben Standardbibliothek und lokalen Modulen. PIL und fontTools werden in sechs CEOKlaue-Tests importiert, nicht im geprüften aktuellen Appcode. Installiert: Pillow 12.3.0, fonttools 4.63.0. Weitere venv-Pakete: brotli 1.2.0, numpy 2.5.2, opencv-python-headless 5.0.0.93, playwright 1.62.0, greenlet 3.5.5, pyee 13.0.1, typing_extensions 4.16.0; deren bloße Installation begründet keine Runtime-Abhängigkeit.

Phase-B-Empfehlung: Python 3.13.15 als geprüften Ausgangspunkt festlegen, direkte und transitive Runtime-Abhängigkeiten exakt in einer reproduzierbaren Lockdatei mit Hashes festlegen, Linux-Kompatibilität separat installieren/prüfen. Test-/Asset-Werkzeuge in separater Dependency-Datei; nur tatsächlich benötigte Pakete aufnehmen. Playwright samt Browser-Version nur bei Nutzung des entsprechenden Smokes festlegen. Kein blindes vollständiges pip freeze der lokalen venv. Hier wurden keine Dependencies verändert, installiert oder extern recherchiert; lokale Versionen sind Messbefunde, keine aktuelle Anbieter-Kompatibilitätszusage.

## Render / Deployment Inventory

Kein `render.yaml` oder vergleichbarer Blueprint gefunden. `Procfile` ist untracked und enthält:

```sh
web: cd App && gunicorn --workers 1 --bind 0.0.0.0:${PORT} --access-logfile - --error-logfile - webapp:app
```

Ein tatsächlicher Render-Build-Command ist im geprüften Projekt nicht verbindlich konfiguriert; `pip install -r requirements.txt` wäre erst ein festzulegender Phase-B-Buildschritt. Render-Dashboard, Remote-Branch, Auto-Deploy und tatsächlich laufender Commit wurden nicht abgefragt und sind unbekannt.

Runtime fordert `SAMMLR_ENV=production`, externes `SAMMLR_SECRET_KEY`, `DATABASE_PATH=/var/data/sammlr.db`, `PORT`; Portraits standardmäßig `/var/data/profile_portraits`, Backups `/var/data/backups`. Ein persistentes privates Volume für diese Pfade ist Voraussetzung. `/healthz` validiert den aktuellen Schema-Vertrag. Der lokale Predeploy-Einstieg ist `python -m Scripts.predeploy`; seine Ausführung mit Zugriff auf das persistente Volume muss vor Deployment konkret geklärt werden. Ein Procfile beweist nicht, dass Render diesen Ablauf tatsächlich ausführt.

Das Betriebsdokument `Dokumentation/Product Bible/operations/s34-deployment-recovery.md` nennt noch V18; Runtime erwartet V20. Nach später freigegebenem Git-Push müssen Build/Start/Python/Branch/Commit, externe Env-Werte, Volume, kontrollierter DB-Bootstrap bzw. Backup+Migration und Healthcheck zusammenpassen. Diese Schritte wurden nur inventarisiert; keine Render-Änderung und kein Beginn von R6.

## Clean-Checkout-Gap

**RED, direkt aus Git-Objekten und Dateistatus nachgewiesen.** HEAD-webapp hat 277.559 Bytes und repräsentiert den älteren Produktstand; eine funktionierende alte App wäre kein Beleg für den aktuellen RC. Aktuelle Module und Migrationen fehlen in HEAD, requirements ist unfixiert, Bootstrap ist unvollständig und persönliche DB-/Backup-Dateien sind bereits versioniert.

Ein kompletter Checkout wurde bewusst nicht exportiert: HEAD enthält private Datenbankartefakte. Die Lücken lassen sich ohne Kopie dieser Daten anhand `git ls-files`, `git show HEAD:App/webapp.py` und Worktree-Diff feststellen. Kein Appstart oder HTTP-Test; Assetvollständigkeit und Linux-Start sind noch zu erbringen.

## Konkreter Phase-B-Plan (noch nicht autorisiert)

1. **PO-Folgeauftrag Phase B einholen.** Scope auf R5 begrenzen; R1–R4-Flächen bleiben geschützt.
2. Explizite Dateiliste vorbereiten: neue Runtime-Module/Services, alle vier Templates, referenzierte Static-/Branding-Assets, alle 40 SQL-Dateien, Migration-/Recovery-Runner und Betriebs-/Testskripte. Dynamische Manifeste auflösen; Source-Entwürfe einzeln von Laufzeitassets unterscheiden. Noch keine pauschale Aufnahme.
3. Secret-Kandidaten und Fixture-/Portrait-Herkunft klären. Echte Nutzerdaten/Backups/Uploads nicht aufnehmen. **PO-Entscheidung** für öffentliches Portrait, Umgang mit bereits getrackten privaten Daten und eventuelle Credential-Rotation/History-Bereinigung; keine destruktive Aktion aus dieser Analyse ableiten.
4. Root-ignore-Regeln für venv, Bytecode, Finder-Dateien, lokale DBs/Backups/Uploads und Testartefakte erstellen; synthetische notwendige Fixtures explizit behandeln. Getrackte Artefakte benötigen eine separat geprüfte Index-Änderung; lokale Daten nicht löschen.
5. Python-Version und Runtime-Lock einschließlich Transitives festlegen; Test-/Asset-Abhängigkeiten getrennt pinnen. Frische isolierte Umgebung aufsetzen, Linux-Ziel prüfen.
6. Eigenständigen, deterministischen Basisschema-/Katalog-Bootstrap planen und implementieren; keine echten Nutzerbestände seeden. **PO-Scope-Freigabe** für hierfür nötige Runtime-/Bootstrap-Anpassungen im Phase-B-Auftrag. Vorhandene V1–V20 nicht still umschreiben; keine kanonische DB migrieren.
7. Allowlist-basierten Kandidaten unter `/private/tmp` erzeugen, ohne Secrets/kanonische DB. Vor Commit als Kandidatenexport korrekt bezeichnen; nach späterem freigegebenem Commit echten Clean Checkout dieses SHA prüfen.
8. In ausschließlich temporärer leerer DB Basisschema + Kataloge + V1–V20 ausführen; Versions-/Checksum-/FK-/Integrity-Prüfung und Wiederholbarkeit nachweisen. Fixture-Lösung allein nicht als Nullstart ausgeben.
9. Appstart mit expliziter temporärer DB und neuem synthetischem Testsecret, danach HTTP-/Asset-Smoke sowie fokussierte Regressionen und Full Suite. Die drei bekannten Baseline-Fehler getrennt berichten und nur im ausdrücklich passenden Scope bearbeiten.
10. R3 Two-User Golden Path und Gegenfälle mit synthetischen Nutzern ausführen; R4-Performancegate reproduzieren. Keine Produktions- oder lokale Nutzerdaten verwenden.
11. Release-Candidate-Diff, enthaltene Dateien, Secretprüfung, Dependency-Lock, Bootstrap-Anleitung und konkrete Deployment-Kommandos reviewen. R6-Betriebs-/Legal-Arbeit nicht vorziehen; offene Provider-Annahmen benennen.
12. **PO STOP vor Commit/Push.** Staging nur gemäß ausdrücklichem Phase-B-Auftrag und geprüfter Allowlist. Commit, Push, RC-Markierung und Render-Deploy bedürfen jeweils passender Autorisierung; nach einem späteren Commit echten Checkout-Nachweis an dessen SHA binden.

## Phase-A-Abschluss / Grenzen

Keine Runtime-Änderung, keine Datenmigration, kein Staging, Commit, Push oder Deploy. Full Suite gemäß Auftrag nicht erforderlich. Die einzigen beabsichtigten Workspace-Änderungen sind `docs/CLOSED_BETA_EXECUTION_ROADMAP.md` und dieses neue Dokument. Temporäre Analysemetadaten liegen unter `/private/tmp/sammlr-r5-audit`, ohne Secret-Werte oder DB-Kopien.

R4-Referenzhash laut Auftrag: `ce5f985b8fbfa10d6864acf8bc320a486c726a254c7b70fba2668161b84ecc95`.

Tatsächlicher DB-SHA-256 **vor Phase A**: `c02354fa094071802c73e2f8080e1c5fac920c838adeb326732e92539fadb37a`. Die Abweichung bestand bereits beim ersten Hash der Phase A; ihre Ursache wurde nicht rückwirkend nachgewiesen. Keine Rekonstruktion oder Änderung vorgenommen.

DB-SHA-256 **nach Phase A**: `c02354fa094071802c73e2f8080e1c5fac920c838adeb326732e92539fadb37a` — identisch zum tatsächlichen Ausgangshash. Dateihash-Abgleich aller Workspace-Dateien außerhalb `.git`/`.venv`: ausschließlich Roadmap geändert und R5-Inventur neu; keine anderen Änderungen gegenüber dem Analysebeginn.

`git diff --check`: bestanden (Exit 0). R5 bleibt NEXT. **STOP nach Phase A; wartet auf Phase-B-Auftrag.**


## Fortschreibung: R5 Phase B1

B1 wurde auf ausdrücklichen PO-Auftrag ausgeführt. Die Phase-A-Zahlen oben bleiben historische Ausgangszahlen, keine Behauptung über den inzwischen durch Ignore-Regeln geänderten Status.

Behoben: versionierbare Dateiauswahl über eine konkrete Allowlist; neun Runtime-Dependencies gepinnt und in frischer venv installiert, Test-Dependencies getrennt; nutzerfreier Bootstrap vom Legacy-Basisschema bis V20 ohne neue Migration; synthetische Fixtures aus SQL; reproduzierbarer isolierter Export und Start-/Testwerkzeuge. Keine pauschale Aufnahme, keine persönlichen Datenbanken als Releasequelle.

Zusätzlicher RED-Befund: 14 CEOKlaue-Raw-Fotos enthalten EXIF-GPS-Tags und sind ausgeschlossen. Dadurch bleiben acht historische Quellarchiv-/Rebuildtests blockiert. Persönlicher Portrait-Default ebenfalls gesperrt; keine Änderung der geschützten Darstellung. Der Screenshot-Archivtest ist durch den verlangten Screenshot-Ausschluss blockiert. Drei bekannte Altfehler unverändert.

Finale Prüfungen: 871 Tests, 859 bestanden, 4 Failures und 8 Errors; 38 fokussierte Tests inklusive R3 bestanden. R4 alle 15 Operationen GREEN, maximal 468,444 ms P95, null HTTP-Fehler. Nutzerfreier Bootstrap und HTTP-Start bestanden. Dependencies GREEN für die tatsächlich geprüfte Umgebung; Bootstrap GREEN; vollständiger Clean-Checkout-/Gesamt-RC-Nachweis RED; Render YELLOW (nicht remote/Linux verifiziert).

Finaler beabsichtigter Releaseumfang: 2.207 explizit ausgewählte Dateien in `docs/R5_RELEASE_FILES.json`. Kein Staging; bereits tracked private Altdateien bleiben in altem HEAD, sind jedoch vom Export ausgeschlossen. `.gitignore` ersetzt keine spätere geprüfte Indexbereinigung.

Kanonischer DB-SHA vorher/nachher identisch: `c02354fa094071802c73e2f8080e1c5fac920c838adeb326732e92539fadb37a`; V20, Integrity OK, FK 0. Keine Original-DB oder private Originaldatei verändert/gelöscht. Der versehentlich im Workspace gestartete erste Testlauf sowie die vor dem GPS-Befund erzeugten, nicht freigabefähigen Zwischenexporte sind im B1-Bericht offen dokumentiert.

Vollständiger Umfang, reproduzierbare Befehle, Ausschlüsse, Einzelbefunde und STOP-Entscheidungen: [R5_RELEASE_CANDIDATE.md](R5_RELEASE_CANDIDATE.md). R5 bleibt NEXT; B2 und R6 nicht begonnen.


## Fortschreibung: R5 B1.1

Der reproduzierbare Release-Testvertrag ist umgesetzt: 867 Release-Gate-Tests bestehen ohne Fehler oder Skips. Neun historische Foto-/Screenshot-Archivprüfungen und drei unveränderte Baseline-Methoden werden methodengenau separat ausgeführt, nicht gelöscht oder übersprungen. Alle relevanten Produktteile aus gemischten Prüfungen bleiben in neuen Release-Gegenprüfungen abgedeckt. Die aktuelle Pagination, Retention und ein explizites V7→V20-Upgrade sind unabhängig nachgewiesen.

Der portraitfreie Fallback verwendet nun ein transparentes selbst enthaltenes SVG; vorhandener DOM, Template, CSS, Upload- und Privacy-Verträge bleiben erhalten. Owner-, Editor- und Public-Profil benötigen keine persönliche Bilddatei.

Umfang: 2.211 explizite Dateien. Frische Umgebung, Bootstrap und HTTP-Appstart GREEN; R3 GREEN; Clean-Candidate-Reproduzierbarkeit GREEN für den vorgesehenen Inhalt. **B1.1 insgesamt noch YELLOW:** R4 blieb in zwei unveränderten Messläufen auf zwei Albumrouten über 500 ms P95 (maximal 635,734 bzw. 996,007 ms), jeweils ohne HTTP-Fehler. Keine Ursache behauptet und keine Performanceoptimierung vorgenommen.

DB-Hash vor/nach B1.1 unverändert: `c02354fa094071802c73e2f8080e1c5fac920c838adeb326732e92539fadb37a`. V20, Integrity OK, FK 0. Keine Tests im Original-Workspace. Keine GPS-Fotos, persönlichen Portraits, echten DBs oder Screenshots aufgenommen. Nichts staged, kein Commit/Push/Deploy. R5 bleibt NEXT.

Details, Einzelklassifikation und alle Messwerte: [R5_B11_TEST_REPRODUCIBILITY.md](R5_B11_TEST_REPRODUCIBILITY.md).
