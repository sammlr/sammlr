# R5 Phase B1 – Release Candidate

**Fortschreibung B1.2 (2026-09-06):** R4 final GREEN im unveränderten lokalen Vertrag: drei vollständige Reihen, jeweils 15/15 GREEN; keine Runtime-Änderung. [Untersuchung und Grenzen](R5_B12_PERFORMANCE_REPRODUCIBILITY.md). [16 PO-Walkthrough-Befunde](CLOSED_BETA_PO_WALKTHROUGH.md) nur dokumentiert. R5 bleibt NEXT, PO-Abnahme ausstehend. Frühere Phasenbewertungen unten sind historische Befunde.

**Fortschreibung B1.1:** Der aktuelle Testvertrag und seine Ergebnisse stehen in [R5_B11_TEST_REPRODUCIBILITY.md](R5_B11_TEST_REPRODUCIBILITY.md). 867 Release-Gate-Tests bestanden; Portrait-Abhängigkeit behoben. Gesamtstatus B1.1 bleibt wegen zweier R4-YELLOW-Messungen YELLOW. Die folgenden B1-Befunde sind historische Ausgangswerte.

Stand: 2026-09-06T09:57:37.079834+02:00

**B1-Prüfung abgeschlossen, Gesamtfreigabe RED.** R5 bleibt NEXT. Kein Commit, Push oder Deploy.

## Reproduktion

Der Kandidat ist ein expliziter Allowlist-Export, kein Checkout eines neuen Commits. Ohne Commit ist der aktuelle HEAD kein Nachweis dieses Produktstands. `docs/R5_RELEASE_FILES.json` enthält jeden beabsichtigten Dateipfad mit Aufnahmegrund. `Scripts/assemble_release.py` exportiert ausschließlich diese Dateien in ein neues Verzeichnis unter `/private/tmp` und schreibt daneben SHA-256-Nachweise.

```sh
python3 -m Scripts.assemble_release --destination /private/tmp/sammlr-r5-clean
cd /private/tmp/sammlr-r5-clean
python3 -m venv /private/tmp/sammlr-r5-clean-env
/private/tmp/sammlr-r5-clean-env/bin/python -m pip install -r requirements-test.txt
/private/tmp/sammlr-r5-clean-env/bin/python -m Scripts.bootstrap_database --database /private/tmp/sammlr-r5-empty.db
/private/tmp/sammlr-r5-clean-env/bin/python -m Scripts.prepare_release_tests
```

Die letzten beiden Schritte erzeugen getrennte DBs: Bootstrap ohne Nutzer für den Erststart; ausdrücklich synthetische SQL-Fixtures nur für die historische Testsuite. Keine DB-Datei gehört zur Allowlist. Vorhandene Dateien werden nicht überschrieben.

## Dependency- und Startvertrag

Python 3.13.15 (`.python-version`); Runtime in `requirements.txt` vollständig versionsgepinnt, Test-/Asset-Werkzeuge separat in `requirements-test.txt`. Keine Übernahme lokaler site-packages. Die Suite benötigt zusätzlich OpenCV/numpy/brotli über bestehende CEOKlaue-Import-/Fonttests; diese bleiben Test-only. Paket-Artefakthashes sind noch nicht gelockt; Pins sichern Versionen, keine byteidentischen zukünftigen Index-Artefakte.

Development: `SAMMLR_ENV=development DATABASE_PATH=/private/tmp/sammlr-r5-empty.db python App/webapp.py` (direkter Start fest auf 8080). Production entsprechend Procfile: `cd App && gunicorn --workers 1 --bind 0.0.0.0:${PORT} --access-logfile - --error-logfile - webapp:app`.

## Render-Vertrag (nicht deployed)

Build Command: `python -m pip install -r requirements.txt` mit Python 3.13.15. Start Command: Procfile-Kommando oben ohne `web:`. Environment-Namen: `SAMMLR_ENV`, `SAMMLR_SECRET_KEY`, `DATABASE_PATH`, `PORT`, optional `PROFILE_PORTRAIT_DIR`. Secretwerte werden extern gesetzt.

Persistentes privates Volume: `/var/data`; DB `/var/data/sammlr.db`, Portraits `/var/data/profile_portraits`, Backups `/var/data/backups`. Erstaufbau: explizit `python -m Scripts.bootstrap_database --database /var/data/sammlr.db` auf dem gemounteten Volume, nur bei noch nicht vorhandener DB. Bestandsupdate: `python -m Scripts.predeploy` mit Backup, Migration und Integrity-Gate, ebenfalls mit Zugriff auf das Volume. Appstart erst danach; Healthcheck `/healthz` erwartet V20. Kein automatisches Kopieren der lokalen DB.

Die Befehle beschreiben den beabsichtigten Vertrag. Render-Servicekonfiguration, verfügbare Python-Version, Volume-Zugriff im gewählten Deployment-Schritt und der spätere Remote-Commit sind nicht extern verifiziert. Ohne diesen Nachweis kein Render-GREEN. R6 wurde nicht begonnen.

## Schutz und ausgeschlossene Daten

Keine echte Nutzer-DB, DB-Backups, Environment-Dateien, persönlichen Portraits, Uploads, Logs, Caches oder Screenshots in der Allowlist. Kein pauschales `git add`. Bereits getrackte private Altdateien bleiben lokal und im bisherigen Git-Verlauf bestehen; sie sind kein Bestandteil des Export-Kandidaten. `.gitignore` allein entfernt sie nicht aus HEAD/Index. Eine spätere bereinigte Git-Aufnahme muss diese Differenz explizit behandeln; keine History-Bereinigung in B1.

Die CEOKlaue-Quelldateien werden nur soweit für bestehende Manifest-/Glyph-Inventar-/Importtests benötigt aufgenommen. Handgeschriebene Produktglyphen sind Test-/Buildeingaben; persönliche Portraits sind ausgeschlossen. Von Hand geschriebene HTML/CSS-Testfixtures sind Testquellen, keine generierten Screenshots. Historische Screenshot-Archive bleiben ausgeschlossen, auch wenn ein vorhandener Test ihre Existenz verlangt.

## Noch gesperrter Kandidat

`App/static/profile-sticker/valentin-portrait-source-v1.png` ist ausgeschlossen. Der bestehende 70er-Sticker referenziert diese persönliche Datei als Default. Ohne gesonderte Freigabe wurde kein visuelles Default ersetzt. Deshalb bleibt dieser konkrete Pfad ein Release-Blocker; ein bloß erfolgreicher Appstart wäre kein vollständiger Profil-Nachweis.

## Ergebnis und verbleibende Sperren

| Bereich | Bewertung | Nachweis / Grenze |
| --- | --- | --- |
| Dependency-Installation | GREEN für geprüften macOS-/Python-Stand | Frische venv, nur gepinnte Requirements, pip check ohne Konflikte; Linux/Render nicht ausgeführt |
| Bootstrap 0→V20 | GREEN | Neue DB aus sieben Basistabellen + öffentlichem Albumkatalog + unveränderten V1–V20; null Nutzer |
| HTTP-Appstart | GREEN | Neuer Gunicorn-Prozess mit explizit gefiltertem Environment; sechs Start-/Asset-Routen HTTP 200 |
| R3 / Kernregressionen | GREEN | 38 fokussierte Tests bestanden, inklusive Bootstrap, R3, R4-Regressionen, R2, Stickerwall, Profile Sticker |
| R4 Performance | GREEN | 15 Operationen, 20 parallele Requests, maximal 468,444 ms P95, null HTTP-Fehler |
| Gesamtsuite | RED | 871 Tests: 859 bestanden, 4 Failures, 8 Errors; siehe Zuordnung unten |
| Vollständiger Clean-Checkout-Nachweis | RED | Reproduzierbarer Allowlist-Export geprüft; noch kein bereinigter Git-Commit, Portrait- und historische Assettest-Sperren offen |
| Render-Reproduktion | YELLOW | Build-/Start-/Volume-Vertrag konkret; Linux-/Provider-/Remote-Commit-Nachweis fehlt |

### Finale Full Suite

Ausgeführt im sicheren Prüfverzeichnis `/private/tmp/sammlr-r5-b1/final`, mit der frisch installierten venv unter `/private/tmp/sammlr-r5-b1/venv`. Kommando: `PYTHONDONTWRITEBYTECODE=1 SAMMLR_ENV=testing` und explizites synthetisches Testsecret gemäß bestehendem Testing-Vertrag, dann `python -m unittest discover -s tests`. Keine Produktionssecrets verwendet; keine Werte im Bericht.

Vier Failures:

1. Bekannter CEOKlaue-DB-Masterhash: verlangt weiterhin eine historische lokale DB. Eine neu erzeugte synthetische DB kann diesen Binärhash absichtlich nicht erfüllen. Das ist jetzt zusätzlich ein expliziter Konflikt mit dem datenfreien Release-Nachweis.
2. Bekannte Notification-Pagination-/Retention-Assertion.
3. Bekannte S38-V0007-Annahme gegenüber der aktuellen V20-DB; keine rückwirkende Fixture-/Migrationänderung.
4. `test_reference_screen_manifest_is_complete`: verlangt sieben historische PNG-Screenshots. Diese bleiben gemäß B1 ausgeschlossen.

Acht Errors betreffen CEOKlaue-Originalarchiv-/Import-/Runtime-Builder-Tests, die die ausgeschlossenen GPS-haltigen Originalfotos bytegenau benötigen. Die endgültigen Produktfonts, SVGs, Marker und Templates sind vorhanden; die laufende App benötigt diese Raw-Fotos im geprüften Journey-/Performancepfad nicht. Ein vollständiger Source-Rebuild ist ohne Lösung dieses Konflikts nicht bewiesen. Keine Tests wurden übersprungen oder auf Erfolg umgeschrieben.

Die drei alten Baseline-Fehler wurden nicht repariert. Für Screenshot-/Raw-Archivprüfungen ist vor B2 eine explizite Entscheidung erforderlich: sicher veröffentlichbare, separat abgenommene Quellen und angepasster Provenienzvertrag oder klar getrennte Archivprüfungen außerhalb des Releasegates. Das ist kein Auftrag, GPS-Daten aufzunehmen oder Schutzverträge still zu lockern.

### Datenschutzprüfung der Quellassets

**14 Raw-Fotos mit EXIF-GPS-Tag sind für diesen Kandidaten gesperrt.** Die Prüfung hat nur das Vorhandensein des Tags erfasst; keine Koordinaten wurden ausgegeben. Keine Originaldatei wurde verändert oder gelöscht. Die endgültige Allowlist enthält keine dieser Dateien. Die verbleibenden aufgenommenen Rasterdateien wurden ebenfalls auf den GPS-Tag geprüft, ohne weiteren Treffer.


- `Branding/CEOKlaue/00_raw/ceoklaue_analog_ui_final_01.jpg`
- `Branding/CEOKlaue/00_raw/ceoklaue_analog_ui_final_02.jpg`
- `Branding/CEOKlaue/00_raw/ceoklaue_analog_ui_final_03.jpg`
- `Branding/CEOKlaue/00_raw/ceoklaue_analog_ui_final_04.jpg`
- `Branding/CEOKlaue/00_raw/ceoklaue_analog_ui_final_05.jpg`
- `Branding/CEOKlaue/00_raw/ceoklaue_analog_ui_final_06.jpg`
- `Branding/CEOKlaue/00_raw/ceoklaue_analog_ui_final_07.jpg`
- `Branding/CEOKlaue/00_raw/ceoklaue_button_brackets_01.jpg`
- `Branding/CEOKlaue/00_raw/ceoklaue_final_fh_repair_01.jpg`
- `Branding/CEOKlaue/00_raw/ceoklaue_final_mini_reselection_glyphs_01.jpg`
- `Branding/CEOKlaue/00_raw/ceoklaue_final_mini_reselection_marks_01.jpg`
- `Branding/CEOKlaue/00_raw/ceoklaue_final_reselection_01.jpg`
- `Branding/CEOKlaue/00_raw/ceoklaue_final_reselection_02.jpg`
- `Branding/CEOKlaue/00_raw/ceoklaue_product_wordmark_final_01.jpg`

Zusätzlich ausgeschlossen: persönlicher Portrait-Default und Uploads, alle DB-/Backupdateien (auch die synthetische Binärfixture wird neu aus SQL erzeugt), .env-Dateien, lokale Altcode-Backups, Logs, Bytecode, Finder-Metadaten, Screenshots und nicht benötigte Branding-Entwürfe. Dateiname-/Textscan des endgültigen Umfangs fand keine typischen Token-/Private-Key-Muster. Literal-Treffer in den aufgenommenen Tests/Performancewerkzeugen sind ausdrücklich synthetische Testcredentials; das SQL-Fixture kennzeichnet sämtliche Personen/Passwörter als synthetisch. Die persönliche Legacy-Nutzeranlage in der unbenutzten `init_db()`-Hilfsfunktion wurde entfernt, einschließlich ihrer festen Nutzerzuordnung. Die aktuelle HTTP-/Produktlogik bleibt unverändert.

### Releaseumfang

Die explizite Allowlist enthält **2.207 Dateien**:

| Kategorie | Dateien |
| --- | ---: |
| Runtime Python | 7 |
| Services | 35 |
| Templates | 4 |
| Static/Product Assets und notwendige Glyph-/Font-Testquellen | 1.843 |
| Migration / Bootstrap / synthetisches Fixture-SQL | 45 |
| Tests | 82 |
| Docs und handgeschriebene HTML/CSS-Regressionsfixtures | 176 |
| Deployment / Testwerkzeuge / Dependency-Konfiguration | 14 |
| Ignore-Regeln | 1 |

Die große Assetzahl entsteht durch die von geschützten Tests vollständig gehashten Glyphinventare, nicht durch pauschale Aufnahme aller untracked Dateien. Jede Datei besitzt einen Aufnahmegrund in `R5_RELEASE_FILES.json`. Keine unnötigen Branding-Originale, Portraits oder Test-Screenshots wurden zur Behebung von Testfehlern aufgenommen.

### Änderungen gegenüber B1-Beginn

- Neu: `.gitignore`, `.python-version`, `requirements-test.txt`.
- Geändert: `requirements.txt` mit neun exakten Runtime-Pins.
- Neu: `App/Database/base_schema.sql`, `catalog_seed.sql`, `Scripts/bootstrap_database.py`.
- Neu: `Scripts/assemble_release.py`, `prepare_release_tests.py`, `release_smoke.py`, `tests/test_r5_release_bootstrap.py` (vier Schutz-/Schemafälle).
- `App/webapp.py`: ausschließlich persönliche Default-Nutzeranlage und feste Nutzer-Album-Zuordnung aus der nicht aufgerufenen Legacy-Initialisierung entfernt; kein Umbau einer Produktoberfläche.
- `tests/test_r4_v20_performance_gate.py`: Negativziel ist jetzt unabhängig vom Checkout-Ordner sicher außerhalb `/private/tmp`; R4-Implementierung/Schwellen unverändert.
- `Branding/CEOKlaue/import_analog_ui_final_sources.py`: private absolute Desktop-Inbox durch projektlokalen optionalen Quellordner ersetzt; Produktassets und Extraktionslogik unverändert.
- Aktualisiert: `docs/R5_RELEASE_INVENTORY.md`.
- Neu: dieses Dokument und `docs/R5_RELEASE_FILES.json`.
- Alle 40 V1–V20-SQL-Dateien sind gegenüber B1-Beginn SHA-identisch. Keine neue Migration, keine Schema-Semantikänderung, keine UI-/CSS-/Templateänderung.

### Abweichungen und Nachweise

Ein erster Full-Suite-Aufruf lief versehentlich im ursprünglichen Workspace. Er lief durch (869 Tests, ausschließlich drei bekannte Fehler), zählt aber ausdrücklich nicht als Clean-Environment-Nachweis. Ein versuchter Prozessabbruch traf keinen noch laufenden Prozess mehr. Unmittelbarer DB-Hash- und anschließender vollständiger Dateihash-Abgleich zeigen keine zusätzlichen Workspace-Mutationen; nur die oben genannten beabsichtigten Änderungen. Der bestehende S38-Test kopierte dabei die lokale DB kurzzeitig in sein `TemporaryDirectory`, scheiterte an seiner bekannten Versionsannahme und bereinigte die temporäre Kopie beim Verlassen des Kontextes. Damit war auch die Vorgabe ausschließlich synthetischer Testdaten in diesem irrtümlichen Lauf verletzt. Die kanonische Quelldatei blieb hashidentisch; diese Abweichung wurde nicht als isolierter Nachweis gewertet. Alle danach berichteten finalen Kandidatentests verwendeten ausschließlich aus SQL erzeugte synthetische DBs.

Die erste Allowlist-Prüfung hatte GPS-Metadaten noch nicht erkannt. Frühere lokale Exportverzeichnisse `candidate` und `clean` unter `/private/tmp/sammlr-r5-b1` sind deshalb **nicht freigabefähige Zwischenstände** und enthalten Kopien dieser Quellbilder. Es fand keine Git-Aufnahme oder externe Veröffentlichung statt. Die Originale blieben unangetastet. Erst der Export `final` wurde ohne diese 14 Dateien erneut vollständig geprüft.

Sandboxbedingte Netzwerk-/Prozessbeschränkungen wurden für die ausdrücklich autorisierte PyPI-Installation und lokalen HTTP-/Performance-Prozesse gezielt eskaliert. Keine automatische Approval-Ablehnung blieb offen. Keine Anwendung oder DB auf Render wurde angesprochen.

Kanonische App-DB vor und nach B1:
`c02354fa094071802c73e2f8080e1c5fac920c838adeb326732e92539fadb37a`.
Schema V20, `integrity_check=ok`, `foreign_key_check=0`. Auch die Bootstrap-/HTTP-Smoke-DB und R4-Messdatenbank haben V20, Integrity OK und keine FK-Verletzung. Die Bootstrap-/HTTP-Smoke-DB besitzt null Nutzer. In den finalen isolierten Prüfungen keine kanonische DB-Kopie als Seed oder Testfixture.

Die getesteten Allowlist-Dateien im Verzeichnis `final` blieben während der finalen Prüfungen SHA-identisch. Das Verzeichnis enthält nach der Prüfung zusätzlich ausschließlich erzeugte Testdaten; deshalb ist es nicht der auszuliefernde Ordner. Der saubere Export `/private/tmp/sammlr-r5-b1/release-verified` wird anschließend erneut ausschließlich aus der Allowlist erstellt; SHA-Evidence daneben. Beim abschließenden Pfadvergleich wurde ein nur auf dem case-insensitiven Mac auflösbarer, doppelt gelisteter Fontpfad entfernt; der echte `CEOKlaue-v0.1.woff2` bleibt unverändert enthalten. Der Exporter prüft jetzt jede Pfadkomponente auf exakte Schreibweise. Gegenüber den Suite-/Performanceprüfungen unterscheiden sich ausschließlich diese Assembly-Prüfung, die bereinigte Manifestliste und Abschlussdokumentation; Runtime, Assets und Tests sind SHA-identisch.

`git diff --check`: bestanden. Nichts staged; kein Commit, Push oder Deploy. R5 bleibt NEXT. **STOP nach B1; keine B2- oder R6-Arbeit ohne PO-Folgeauftrag.**
