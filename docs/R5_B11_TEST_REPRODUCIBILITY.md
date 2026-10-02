# R5 B1.1 – Clean-Checkout Test Reproducibility

Stand: 2026-09-06. R5 bleibt NEXT. Kein Commit, Push oder Deploy.

## Release-Testvertrag

Alle Prüfungen dieses Auftrags liefen ausschließlich im aus der Allowlist erzeugten Verzeichnis `/private/tmp/sammlr-r5-b11/candidate`. Python 3.13.15 wurde mit einer neuen venv unter `/private/tmp/sammlr-r5-b11/venv` verwendet; Installation nur aus den unveränderten `requirements-test.txt` / `requirements.txt`, ohne lokale site-packages. `pip check` findet keine Konflikte.

Der Kandidat enthält 2.211 explizite Dateien. Die beabsichtigten versionierbaren Dateien sind reproduzierbar exportierbar; dies ist noch kein Nachweis eines neuen Git-Commits. Der bisherige HEAD wurde weder verändert noch bereinigt. Der spätere B2-Commit muss an genau diesen überprüften Umfang gebunden werden. Render bleibt unverändert YELLOW, da Linux-/Provider-/Deployment-Nachweis nicht Teil von B1.1 ist.

### A: Release-Gate

867 Tests sichern die aktuelle Runtime, Produktverträge, Datenmigration, Auth-/Privacy-Gegenfälle und sichere Buildinputs ab. `Scripts/release_test_gate.py --cohort release` führt sie mit normaler unittest-Fehlerbehandlung aus. Neue, nicht klassifizierte Tests gehören standardmäßig zu A; unbekannte/veraltete Ausnahme-IDs und fehlende zugeordnete Release-Gegenprüfungen führen zum Abbruch.

### B: Historische Branding-/Archivprüfungen

Neun Tests bleiben vollständig erhalten und werden ausdrücklich mit `--cohort historical` ausgeführt. Es gibt keine `skip`-/`expectedFailure`-Dekoratoren und keine Erfolgssimulation. In der sicheren Ausgabe bleiben sie wegen bewusst ausgeschlossener Originalfotos/Screenshots nicht erfolgreich. Dies wird separat ausgewiesen, nicht als bestandene Releaseprüfung gezählt.

### Separate Altfehler-Diagnostik

Drei unveränderte historische Baseline-Methoden werden zusätzlich mit `--cohort baseline` ausgeführt. Ihre aktuellen funktionalen Verträge werden in A unabhängig überprüft. Insbesondere wird kein aktueller Pagination- oder Upgradefehler als historisch verborgen.

Maschinenlesbare, methodengenaue Zuordnung mit Gründen und zugehörigen Release-Gegenprüfungen: `docs/R5_TEST_CONTRACT.json`. Alle 879 entdeckten Tests sind genau einer der drei Gruppen zugeordnet: 867 + 9 + 3.

## Analyse der acht Fotoabhängigkeiten

Ein synthetisches Ersatzfoto kann keinen erwarteten SHA-256 eines bestimmten historischen Originals erfüllen. Die Originalprüfungen bleiben daher als Provenienznachweise erhalten. Für den produktiven Build werden bereits vorhandene, verifizierte abgeleitete Glyph-/Markerquellen genutzt; keine privaten Foto- oder GPS-Dateien werden kopiert, bereinigt oder neu aufgenommen.

| Test | Tatsächlicher Vertrag | Entscheidung |
| --- | --- | --- |
| `test_seven_new_originals_are_byte_exact_archived_and_documented` | Historical provenance of seven original JPEGs: exact SHA/format/dimensions; synthetic images cannot establish identity of these GPS-tagged originals. | Historische Original-/Reimportprüfung separat; keine Runtime-Funktion wird durch Originalfoto-Identität abgesichert. |
| `test_import_is_idempotent_and_product_scope_is_locked` | Original handwritten-drop reimport idempotence; current product policy assertions remain independently executed. | Historische Original-/Reimportprüfung separat; relevante Produktprüfungen bleiben explizit in A. |
| `test_only_two_new_originals_are_byte_exact_archived_images` | Historical exact-photo archive hashes and camera image dimensions, not an application input contract. | Historische Original-/Reimportprüfung separat; keine Runtime-Funktion wird durch Originalfoto-Identität abgesichert. |
| `test_importer_is_idempotent_and_product_assets_are_out_of_scope` | Historical original-photo extraction rerun; product-scope flags remain in the release gate. | Historische Original-/Reimportprüfung separat; relevante Produktprüfungen bleiben explizit in A. |
| `test_two_new_originals_are_exact_archived_jpegs` | Original-artwork provenance check requiring the excluded GPS-bearing originals byte-for-byte. | Historische Original-/Reimportprüfung separat; keine Runtime-Funktion wird durch Originalfoto-Identität abgesichert. |
| `test_importer_is_idempotent_and_final_master_references_it_without_mutation` | Historical source reimport; runtime/harmony linkage and nonmutation policy remain separately protected. | Historische Original-/Reimportprüfung separat; relevante Produktprüfungen bleiben explizit in A. |
| `test_button_import_is_idempotent` | Original photo extraction/archive rerun; current five real pairs and runtime output hashes remain covered by existing release tests. | Historische Original-/Reimportprüfung separat; relevante Produktprüfungen bleiben explizit in A. |
| `test_runtime_builder_is_reproducible` | Full original-connected-wordmark revectorization requires its private GPS photo. Font/marker rebuilds and current wordmark artifact integrity remain release-relevant and are executed independently. | Historische Original-/Reimportprüfung separat; relevante Produktprüfungen bleiben explizit in A. |

Besonders der vorher gemischte `test_runtime_builder_is_reproducible` wird nicht ersatzlos aus dem Produktnachweis entfernt: Der neue Release-Test prüft exakt gebundene Harmony-Selektionen, Version und Markerrotation, baut alle drei WOFF2-Fonts und alle zehn Runtime-Marker aus den sicheren abgeleiteten Inputs neu und vergleicht deren Bytes mit den produktiven Manifest-Hashes. Die produktive Wordmark-SVG wird ebenfalls gegen ihren gebundenen Hash geprüft. Nur die erneute Vektorisierung aus dem persönlichen Originalfoto bleibt historische Branding-Arbeit. Die produktive App konsumiert die enthaltene SVG; sie vektorisiert beim Appstart kein Foto.

Auch Produkt-Policy-Flags und die Runtime-/Harmony-Verknüpfung aus gemischten Importtests bleiben in A. Die hinter dem veralteten DB-Hash bislang unerreichbaren Prüfungen der 82×3-Masterstruktur und der exakten Markerhashes wurden zusätzlich als eigenständige Release-Methode übernommen. Alle ursprünglichen Testmethoden bleiben unverändert erhalten.

## Screenshot-Prüfung

`test_reference_screen_manifest_is_complete` prüft ausschließlich Existenz, Namen und Mindestdateigröße von sieben historischen lokalen PNGs. Der Test rendert keine Seite und prüft weder Layout noch Verhalten. Er wird deshalb als Archivnachweis B ausgeführt. Ein synthetisches PNG, das nur groß genug ist, wäre eine inhaltslose Grünfärbung; solche Ersatzbilder wurden bewusst nicht erzeugt. Alle vorhandenen aktuellen UI-/Routing-/Owner-/Public-Tests bleiben in A.

## Portrait ohne persönliche Datei

Der alte Fallback referenzierte die ausgeschlossene Portraitdatei und war tatsächlich keine funktionierende Lösung. `App/profile_sticker.py` verwendet für genau den Fall ohne eigenes Portrait jetzt ein transparentes, selbst enthaltenes 1×1-SVG als Data-URL. Es enthält keine Personen, Metadaten oder externen Links.

Das bestehende `<img>` bleibt erhalten, damit Name-/Upload-/Crop-JavaScript weiterhin denselben DOM findet. Template, CSS, Editor-JavaScript, Layout und Farben sind gegenüber B1 byteidentisch; es wurde kein neues Ersatzmotiv gestaltet. Existierende private Portrait-URLs und ihre Berechtigungen werden unverändert verwendet.

Der neue HTTP-/DOM-Test erstellt einen synthetischen Sticker ohne Foto und prüft Ownerprofil, Editor und Fremdprofil: HTTP 200, vorhandener Rahmen und Bild-DOM, gültiges leeres Inline-SVG, keine persönliche Referenz, keine leeren sichtbaren Bildquellen und HTTP 200 für sämtliche lokalen Bild-URLs. Das noch ungefüllte Bild im ausdrücklich versteckten Crop-Dialog wird als solches erkannt. Die bestehenden Upload-/Owner-/Public-/Privacy-Tests laufen ebenfalls im Release-Gate. Es wurden keine neuen Screenshots oder privaten Testfotos benötigt.

## Die drei Baseline-Probleme

| Altprüfung | Nachgewiesene Ursache | Aktueller Release-Vertrag in A |
| --- | --- | --- |
| Historischer DB-Masterhash | Ein fester Hash eines alten lokalen DB-Zustands ist für neue synthetische DBs ungeeignet; die ursprüngliche Methode bleibt erhalten. | Nutzerfreier Bootstrap, V20/Integrity/FK, gebundene Produktasset-Hashes und unveränderte 82×3-/Marker-Prüfungen. |
| Notification-Pagination | Die festen August-2026-Zeitstempel liegen inzwischen außerhalb der 30-Tage-Retention. Der erste POST markiert 25 alte Einträge als gelesen; der zweite POST entfernt diese und begrenzt die Seite auf 1. | 30 frische synthetische Einträge: korrekte Reihenfolge, 25/5 Aufteilung und beide Navigationslinks. Separater Test mit injizierter Uhr beweist exakt die Retention von 25 alten gelesenen Einträgen. Keine Produktänderung. |
| V0007/V20-Annahme | Der Test kopiert eine V20-Anwendungs-DB und erwartet, dass sie V7 ist. | Explizit aus sicherem SQL aufgebautes V7-Fixture: Backup bleibt V7, alle Migrationen 8–20 angewendet, Ergebnis V20, Integrity OK und FK 0. |

Die drei historischen Methoden wurden nicht repariert oder still umgeschrieben. Ihre Fehler sind mit den bekannten Baseline-Problemen identisch; die aktuellen Verträge bestehen in unabhängigen ausführbaren Gegenprüfungen. Sie sind damit für diesen Release-Testvertrag keine unbehobenen Produktfehler.

## Reproduzierbare Befehle

```sh
python3 -B -m Scripts.assemble_release --destination /private/tmp/sammlr-b11-clean
cd /private/tmp/sammlr-b11-clean
python3 -m venv /private/tmp/sammlr-b11-env
/private/tmp/sammlr-b11-env/bin/python -m pip install -r requirements-test.txt
PYTHONDONTWRITEBYTECODE=1 /private/tmp/sammlr-b11-env/bin/python -m Scripts.prepare_release_tests
PYTHONDONTWRITEBYTECODE=1 /private/tmp/sammlr-b11-env/bin/python -m Scripts.release_test_gate --cohort release
PYTHONDONTWRITEBYTECODE=1 /private/tmp/sammlr-b11-env/bin/python -m Scripts.release_test_gate --cohort baseline
PYTHONDONTWRITEBYTECODE=1 /private/tmp/sammlr-b11-env/bin/python -m Scripts.release_test_gate --cohort historical
PYTHONDONTWRITEBYTECODE=1 /private/tmp/sammlr-b11-env/bin/python -m Scripts.release_smoke --database /private/tmp/sammlr-b11-start.db --port 18461
PYTHONDONTWRITEBYTECODE=1 /private/tmp/sammlr-b11-env/bin/python -m unittest tests.test_r3_two_user_golden_path
PYTHONDONTWRITEBYTECODE=1 /private/tmp/sammlr-b11-env/bin/python Scripts/r4_v20_performance_gate.py --database /private/tmp/sammlr-b11-perf.db --output /private/tmp/sammlr-b11-perf.json --python /private/tmp/sammlr-b11-env/bin/python --port 18462
```

Die diagnostischen Baseline-/Historienbefehle liefern bewusst Exit 1 bei ihren weiter vorhandenen Fehlern. Nur `--cohort release` ist das Release-Gate. Ein ungefiltertes `unittest discover` bleibt eine Ausführung einschließlich aller historischen Verträge und wird nicht als vollständig grün bezeichnet. Der Runner verweigert Testausführung außerhalb eines isolierten `/private/tmp`-Kandidaten.

## Ergebnisse

**Test-Reproduzierbarkeit GREEN; B1.1-Gesamtkriterium YELLOW wegen R4.** Die GREEN-Anforderung des Auftrags ist damit noch nicht vollständig erfüllt. Es erfolgt keine Performanceoptimierung innerhalb dieses Testvertrags-Auftrags.

| Prüfung | Ergebnis |
| --- | --- |
| Neue Umgebung / gepinnte Dependencies | GREEN; Python 3.13.15, frische venv, pip check ohne Konflikte |
| Release-Gate Full Suite | **867/867 bestanden**, 0 Failures, 0 Errors, 0 Skips; finaler Lauf 19,540 s |
| Historische Gruppe | 9 ausgeführt: 1 Failure (Screenshotarchiv), 8 Errors (private Originalfotos/Rebuild); keine Skips |
| Baseline-Diagnostik | 3 ausgeführt: exakt die bekannten 3 Failures; keine Errors oder Skips |
| R3 Golden Path | GREEN; vollständiger vorhandener Two-User-Journey-Test separat bestanden |
| Bootstrap 0→V20 | GREEN; neue DB ohne Nutzer, keine Kopie der kanonischen DB |
| HTTP-Appstart | GREEN; `/healthz`, `/login`, `/register` und drei Static-Routen HTTP 200 |
| Profile ohne persönliches Portrait | GREEN für Owner/Editor/Public, alle lokalen Bildquellen erreichbar; Privacy-/Upload-Gegenfälle im Release-Gate |
| Clean Candidate aus vorgesehenem Releaseinhalt | GREEN; expliziter Allowlist-Export, noch kein neuer Git-Commit |
| R4 Performance | **YELLOW in beiden B1.1-Läufen**, jeweils 13/15 Operationen GREEN und null HTTP-Fehler |
| Render | unverändert YELLOW; kein Deploy / kein Linux- oder Provider-Nachweis |

### R4: beide Messläufe, ohne Auswahl nur günstiger Ergebnisse

Die erste Messung lag für Album bei 631,496 ms P95 und für Missing-Stickerwall bei 635,734 ms P95. Die Wiederholung wurde nach Ende sämtlicher übrigen Testläufe ausgeführt, ohne Code-, Datenmengen-, Grenzwert- oder Serverkonfigurationsänderung. Sie lag bei 996,007 bzw. 809,641 ms P95. Beide Male: ein Gunicorn-Worker, 20 Threads, 20 parallele Requests, null HTTP-Fehler, 13 weitere Operationen GREEN.

Die Ursache dieser Abweichung zur früheren R4-/B1-Baseline ist nicht nachgewiesen. Die betroffenen Album-Routen und R4-Implementierung wurden in B1.1 nicht geändert. Die Nachmessung wird nicht als Beweis von Hostlast oder einer Produktregression ausgegeben. Die R4-Grenzwerte bleiben unverändert. Es wurde nicht weiter gemessen, bis zufällig GREEN entsteht.

| Operation | Erster P95 (ms) | Zweiter P95 (ms) | Zweiter Status |
| --- | ---: | ---: | --- |

| login | 14.517 | 11.624 | GREEN |
| home | 114.543 | 106.182 | GREEN |
| collection | 124.537 | 106.693 | GREEN |
| album | 631.496 | 996.007 | YELLOW |
| stickerwall_missing | 635.734 | 809.641 | YELLOW |
| partner_search | 158.932 | 149.801 | GREEN |
| trade_market | 103.327 | 104.624 | GREEN |
| trade_requests | 97.247 | 97.798 | GREEN |
| album_trade_hub | 379.954 | 261.710 | GREEN |
| deal | 213.054 | 198.932 | GREEN |
| notifications_gate | 42.670 | 41.917 | GREEN |
| notifications_inbox | 180.077 | 159.445 | GREEN |
| profile | 93.267 | 95.594 | GREEN |
| public_profile | 90.688 | 95.156 | GREEN |
| public_stickerwall | 264.542 | 309.904 | GREEN |

Die R4-Messdatenbanken blieben V20, `integrity_check=ok`, FK-Verletzungen 0. Datensatzumfang blieb bei 100 synthetischen Nutzern, 10 Alben, 100.000 Bestandszeilen, 2.000 Trades, 5.000 Notifications und 1.000 Freundschaften. Kein Eingriff in WAL, Timeout, Indizes oder Produktlogik.

## Sicherheit, Änderungen und Abschluss

Alle B1.1-Testaufrufe liefen im neuen temporären Kandidaten. Keine Tests im ursprünglichen Workspace, keine kanonische DB-Kopie, keine privaten Quelldateien für den Testlauf. Die Test-DBs wurden ausschließlich aus dem explizit synthetischen SQL-Fixture neu erzeugt. Es gab in B1.1 keinen Zwischenexport mit den ausgeschlossenen GPS-Fotos.

Erneute Prüfung sämtlicher aufgenommenen Rasterdateien: kein EXIF-GPS-Tag. Im vorgesehenen Umfang keine DB-/Backup-/Upload-/Portrait-/Screenshot-/Log-/Cache-Dateien, keine .env-Dateien und keine erkannten Credential-/Private-Key-Signaturen. Die aufgenommenen Python-Dateien enthalten keinen absoluten `/Users/`-Pfad. Synthetische Testcredentials bleiben ausdrücklich Testdaten und wurden nicht als Produktionssecrets ausgegeben. Keine Secretwerte oder Koordinaten im Bericht.

Die einzige Runtime-Änderung betrifft den portraitfreien Fallback in `App/profile_sticker.py`. Template, CSS, Editor-JavaScript, `App/webapp.py`, R4-Runner, Inventory-/Trade-/Privacy-Services und alle V1–V20-Migrationen sind gegenüber B1.1-Beginn byteidentisch. Keine neue Migration, keine Schemaänderung, kein neues Produktfeature.

Geänderte bestehende Dateien:

- `App/profile_sticker.py`: persönliches Fallback durch selbst enthaltenes transparentes SVG ersetzt; vorhandener DOM und Upload-/Privacy-Pfade erhalten.
- `tests/test_ceoklaue_analog_ui_final_import.py`: zusätzliche eigenständige Release-Methode mit den exakten Master-/Marker-Prüfungen; sämtliche ursprünglichen Methoden unverändert.
- `docs/R5_RELEASE_FILES.json`: vier neue Testvertrags-/Dokumentationsdateien explizit aufgenommen.
- `docs/R5_RELEASE_INVENTORY.md`, `docs/R5_RELEASE_CANDIDATE.md`: B1.1-Fortschreibung; historische B1-Ergebnisse bleiben erkennbar.

Neue Dateien:

- `Scripts/release_test_gate.py`
- `tests/test_r5_release_contracts.py`
- `docs/R5_TEST_CONTRACT.json`
- `docs/R5_B11_TEST_REPRODUCIBILITY.md`

Kanonischer DB-SHA-256 vor und nach B1.1:
`c02354fa094071802c73e2f8080e1c5fac920c838adeb326732e92539fadb37a`.
Schema V20, `integrity_check=ok`, `foreign_key_check=0`. Auch die nutzerfreie HTTP-/Bootstrap-DB besitzt V20, Integrity OK, FK 0 und null Nutzer.

Der saubere abschließende Export liegt unter `/private/tmp/sammlr-r5-b11/release`; Dateihashes liegen daneben. Nur Abschlussdokumentation unterscheidet sich vom tatsächlich getesteten Dateibestand. Erzeugte Test-DBs und Logs bleiben außerhalb dieses Exportumfangs. Die Gesamtsuite einschließlich historischer Tests wird ausdrücklich nicht als grün bezeichnet.

`git diff --check`: bestanden. Nichts staged; kein Branchwechsel, Commit, Push, Deploy oder Eingriff in Git-Historie. R5 bleibt NEXT. **STOP nach B1.1. Der offene R4-YELLOW-Befund ist vor einer vollständigen GREEN-Abnahme zu klären; B2, R6 und R7 wurden nicht begonnen.**


## Abgenommener Stickerstack und lokale Runtime

Der PO-abgenommene Stack verwendet maximal fünf vollständige Exemplare desselben
Stickers. Bestehende DOM-Karten behalten ihre Position; eine neue oberste Karte
wird mit konstant 2 px nach links/oben ergänzt. Nur oben steht die reale Menge.

Nach Änderungen an Python-Renderingcode (`App/webapp.py`) muss die laufende lokale
App neu gestartet werden. Der normale Start mit `debug=False` lädt Python-Code
nicht automatisch nach. Vor visueller Bewertung Prozessstart, Working Directory
und ausgelieferten Code prüfen: Alter Python-Prozess plus aktuelles CSS/JS ist
kein gültiger visueller Abnahmestand. Keine synthetische Testinstanz mit der
angemeldeten Benutzerinstanz auf Port 8080 verwechseln.

Regression: `tests/test_sticker_wall_product_island.py` schützt serverseitige
Faces, Bubble und Limit. `tests/research/check_vertical_stacks.py` prüft feste
Offset-Folgen bei 375/390/430 px und zusätzlich die echte Albumseite bei 390 px
über die vorhandenen Plus-/Minus-Controls mit synthetischer temporärer DB.
Dabei werden DOM-Identität und Bounding-Boxes bestehender Karten, vollständige
Faces, Z-Reihenfolge, Bubble, Kollisionen und Overflow geprüft.

Im isolierten Release-Kandidaten mit vorbereiteten synthetischen Fixtures:

```sh
SAMMLR_ENV=testing SAMMLR_SECRET_KEY=sammlr-explicit-testing-secret python tests/research/check_vertical_stacks.py
```

Die App-DB des Workspace darf dafür nicht verwendet werden.
