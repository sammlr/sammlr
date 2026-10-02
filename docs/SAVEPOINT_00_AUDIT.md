# SAVEPOINT-00 – Audit

Stand 2026-10-02. **Aktuell 2026-10-03: Whitespacebereinigung, sämtliche Nach-Smokes und beide Diffchecks grün. Savepointaufnahme freigegeben; finaler Git-Commit-Hash wird im Abschlussbericht ausgegeben.**

Die folgenden ursprünglichen Befunde sind historisch; der maßgebliche Fortsetzungsabschluss steht am Dokumentende.

## Konkreter Blocker

Der verlangte Git-Savepoint darf keine lokalen Runtime-/Privatdaten enthalten. Bereits im bestehenden Index/HEAD stehen jedoch lokale Datenbanken und historische Backups. Nicht erneut zu stagen lässt ihre bisherigen Blobs im neuen Commitbaum bestehen. `.gitignore` entfernt keine bereits getrackten Dateien. Der Auftrag verbietet zugleich eigenmächtige Bereinigung und verlangt STOP bei unklaren DB-Dateien/privaten Daten. Daher keine eigenmächtige Indexentfernung, kein Löschen und kein Commit.

Belegt durch `git ls-files` und bestehende Dokumente `docs/R5_RELEASE_CANDIDATE.md` (Abschnitt über bereits getrackte private Altdateien und explizit nötige Git-Aufnahmeentscheidung) sowie `docs/R5_RELEASE_INVENTORY.md`. Der frühere Allowlist-Export ist kein bereinigter Git-Commit und löst die Vererbung aus HEAD nicht.

Aktuell getrackte Datenbankdateien, Kategorie **G**, nicht für einen datenfreien Savepoint freigegeben:

- `App/Database/Database:Backups/collectr_backup_before_trophy_cleanup.db`
- `App/Database/Database:Backups/collectr_backup_before_users.db`
- `App/Database/Database:Backups/collectr_backup_popup_clean.db`
- `App/Database/Database:Backups/collectr_backup_trophy_tabs_visual_runs.db`
- `App/Database/Database:Backups/collectr_backup_users_trophy_clean_runs.db`
- `App/Database/collectr.db Kopie`
- `App/Database/sammlr.db`
- `App/Database/sammlr_reference_s00.db`
- `Backups/collectr_2026-06-02_22-14-58.db`

Die lokale Referenz-DB enthält drei Nutzerzeilen und Felder username/password/name; die Runtime-DB sechs Nutzerzeilen. Ausschließlich Tabellenspalten und Anzahl wurden per mode=ro&immutable=1 gelesen, keine Nutzer-/Passwortwerte ausgegeben. Die bloße Existenz dieser Spalten beweist keine echten Credentials; eine hinreichende Freigabe sämtlicher historischen Binärdaten liegt jedoch nicht vor. Synthetische SQL-Testfixtures und Scripts.prepare_release_tests existieren als sicherer Reproduktionsansatz; diese ersetzen die getrackten DB-Blobs nicht automatisch.

Erforderliche nächste Entscheidung: gezielt autorisieren, die identifizierten Runtime-/Privatdateien nur aus dem zukünftigen Gitbaum zu nehmen, lokale Dateien unverändert zu behalten und benötigte Testdaten aus geprüften synthetischen Quellen herzustellen. Das ist eine gesonderte Umfangsentscheidung, keine hier durchgeführte Bereinigung. Auch ein solcher Schritt entfernt keine Daten aus historischer Git-History; keine History-Umschreibung beauftragt oder vorgenommen.

## Bestand / Klassifikation

Branch `feature/wm-special-trophies`, HEAD unverändert. Index zu Beginn ohne staged Änderungen. 5.143 untracked Dateien zum Prüfstart; breite Asset-/Researchbestände, nicht pauschal aufnehmen. Bestehende INTEGRATION-00-Dokumente und maschinenlesbare Inventur wurden als Grundlage verwendet. Aktuelle Status-, Dependency-, Ignore- und DB-Inventur erneut gelesen.

- A: Produktiv-App, Trade-v2, Pax und ihre tatsächlich erforderlichen Rendering-/Fontassets gehören in den reproduzierbaren Sourceumfang; kein Umbau.
- B: Verträge, Dokumentation und Integrationsplanung gehören in den Umfang.
- C: Tests, Runner und Testabhängigkeiten gehören in den Umfang.
- D: Explizit synthetische SQL-Fixtures sind Kandidaten; historische Binärdatenbanken nicht ungeprüft als Fixture übernehmen.
- E: Audit-/Researchcode und nötige Nachweise gezielt auswählen; keine pauschale Aufnahme aller Ergebnisse.
- F: Generierte Screenshots, Browserberichte, temporäre Exporte, Bytecode, DS_Store nicht automatisch aufnehmen.
- G: Lokale DBs/Backups, .env, Uploads/Portraits, Runtime- und Browserdaten ausschließen. Bereits getrackte DBs sind der konkrete Stopgrund.
- H: Vollständige individuelle Aufnahmeentscheidung aller übrigen Dateien wurde wegen STOP nicht abgeschlossen. Keine Behauptung einer freigegebenen Allowlist.

## Secret-/Private-Data-Check

Vorläufiger Textscan in Source-/Textformaten fand keine typischen OpenAI-/GitHub-/AWS-Key- oder Private-Key-Muster. Das ist kein vollständiger Secret-/Privatdaten-Freigabenachweis. Binärdateien, persönliche Assets und alle Kandidaten wurden vor STOP nicht vollständig einzeln freigegeben. Keine Secrets oder privaten Werte in diesem Audit. Kein Staging erfolgte.

## Tests und Reproduzierbarkeit

Ausgeführt:

1. `.venv/bin/python -B -m unittest tests.test_trade_v2_preview tests.test_pax_preview -q` — **8 Tests OK**; Trade-v2-Factory und GET-Endpunkte werden dabei ohne DB getestet.
2. `SAMMLR_ENV=testing SAMMLR_SECRET_KEY=<bekannter synthetischer Testwert> .venv/bin/python -B -m unittest tests.test_sticker_wall_product_island tests.test_ceoklaue_sticker_list -q` — **29 Tests OK**. Wall-Testsetup kopiert Referenz-DB in temporäres Verzeichnis; keine lokale Runtime-DB beschrieben.
3. `git diff --check` — keine Ausgabe/Whitespacebefunde.

Ein anfänglich kombinierter Aufruf aller vier Module ergab 37 Tests / 1 Failure: Der Pax-Isolationstest verlangt, dass webapp nicht importiert wurde; das Wall-Testmodul importiert webapp bereits bei Testdiscovery. Dies war eine ungeeignete gemeinsame Prozessausführung durch den Prüfer, keine nachgewiesene Produktregression. Ohne Teständerung wurden die im TRADE-11-Audit getrennt dokumentierten Gruppen anschließend separat ausgeführt; beide grün. Der erste Fehlversuch wird nicht verschwiegen.

Nicht abgeschlossen: vollständige produktive Regression, TRADE-01–11-Browserregression, dynamische Stack-Parität/Wallcap5/Tradecap10, sauberer Checkout mit sämtlichen notwendigen Abhängigkeiten, Post-Commit-Smokes. Es wurde keine grüne Gesamtfreigabe behauptet. requirements.txt liegt vor; Testmodule benötigen zusätzlich z.B. fontTools und Playwright. Bestehender synthetischer Release-Bootstrap wurde nur als Quelle identifiziert, nicht auf lokale DBs angewandt.

## Ergebnis gemäß angefordertem Abschlussbericht

1. Commit-Hash: keiner neu erzeugt.
2. Commit-Message: nicht verwendet; vorgesehen war `savepoint: freeze pre-integration trade-v2 baseline`.
3. Neu versionierte Dateien: 0.
4. Aufgenommene Kategorien: keine, Index unangetastet.
5. Nicht aufgenommen: gesamter Kandidatenumfang bis zur Auflösung; insbesondere DBs/Backups, private Runtime-/Uploaddaten und generierte Artefakte.
6. Secret-/Private-Data-Check: nicht freigegeben, konkreter DB-/Gitbaumblocker.
7. Reproduzierbarkeit: noch nicht vollständig attestiert; synthetischer Export ist kein bereinigter Git-Checkout.
8. Tests: 8+29 OK in korrekter Isolation, diff-check sauber; weitere Gates nicht ausgeführt.
9. Gitstatus: bestehender Entwicklungsstand erhalten, ausschließlich dieses neue Audit hinzugefügt; kein staged Diff.
10. Keine Mutation bestehender lokaler oder produktiver DBs, kein Push, kein Deploy. Temporäre Test-DB-Kopie wurde nur im isolierten Testsetup genutzt.

## Schutzprüfung

Vor Audit-Erstellung war der Gitstatus exakt identisch zum Prüfstart. Alle 5.364 im INTEGRATION-00-Vorhermanifest geschützten Bestandsdateien haben weiterhin identische SHA256-Werte, einschließlich lokaler DBs. Indexhash unverändert. Keine Source-/Produktiv-/Testdatei angepasst; neu nur `docs/SAVEPOINT_00_AUDIT.md`.


## Fortsetzung nach ausdrücklicher Privatdaten-Freigabe

Vor jeder Indexänderung erfasste Liste. Alle Dateien derzeit getrackt; Inhalte werden nicht verändert. Die S00-Binärfixture stimmt mit dem im S00-Vertrag dokumentierten Hash überein und bleibt entgegen der vorherigen pauschalen DB-Sperre ausdrücklich erhalten.

| Datei | Klassifikation | Geplante Aktion | SHA256 vorher |
|---|---|---|---|
| `.DS_Store` | Finder-Runtimemetadaten | Nur Git-Tracking entfernen | `23e5f150c1ff101835fed7d763e511bd9360192d7c9bd13272c1810925be3e42` |
| `App/.DS_Store` | Finder-Runtimemetadaten | Nur Git-Tracking entfernen | `c42474c79a09ce6b6a3a1871de0c397dec340efa73cb5b398946642f2d02cec4` |
| `App/Database/.DS_Store` | Finder-Runtimemetadaten | Nur Git-Tracking entfernen | `0bc41c416a8286a45becd4a597f83877d45906cf38686e55c0c091d8ff25ade2` |
| `App/Database/Database:Backups/collectr_backup_before_trophy_cleanup.db` | historisches DB-Backup | Nur Git-Tracking entfernen | `447a9164ba7772b04ee12ccfc5c65a39720cf1f1776c86002ffe3161fded287e` |
| `App/Database/Database:Backups/collectr_backup_before_users.db` | historisches DB-Backup | Nur Git-Tracking entfernen | `f4796d18d36a6a0f1625bfc7eb2fb926006ef50d534472ca32a3cfbe0a4e8039` |
| `App/Database/Database:Backups/collectr_backup_popup_clean.db` | historisches DB-Backup | Nur Git-Tracking entfernen | `6bcb037730123b78fe756856bc8735a7358f185872040d179fc34a5ebb1d51e3` |
| `App/Database/Database:Backups/collectr_backup_trophy_tabs_visual_runs.db` | historisches DB-Backup | Nur Git-Tracking entfernen | `6bcb037730123b78fe756856bc8735a7358f185872040d179fc34a5ebb1d51e3` |
| `App/Database/Database:Backups/collectr_backup_users_trophy_clean_runs.db` | historisches DB-Backup | Nur Git-Tracking entfernen | `602883a8538f9377847542c1c7c969d326adc7d071c6cca2ff5822eca1b96f8f` |
| `App/Database/collectr.db Kopie` | historisches DB-Backup | Nur Git-Tracking entfernen | `f25e1b02975da4cda2dfc0e217fe30ae294030dbb9fc0b7a5b6d4b93318f5e4a` |
| `App/Database/em24_fehlende.txt` | lokaler Sammlungsexport | Nur Git-Tracking entfernen | `ecea639f00b92aea8b1beb31e1abd6017718b0882e2ab08100be844b5ea6ca04` |
| `App/Database/fehlende.txt` | lokaler Sammlungsexport | Nur Git-Tracking entfernen | `2d821f3a14930f07eb261999d3f506deb485aa473e647d803cf7bc54ab788a3e` |
| `App/Database/sammlr.db` | aktive lokale DB | Nur Git-Tracking entfernen | `164917d8fd97e517cbb4323326f5f2aff85db9ed0e42c54d6f4849b28ad0c602` |
| `App/Database/sammlr_reference_s00.db` | legitime synthetische S00-Testfixture — BEHALTEN | Versioniert behalten | `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971` |
| `App/services/.DS_Store` | Finder-Runtimemetadaten | Nur Git-Tracking entfernen | `d93309d94b32ba6fedff8aeee437df419d9e6de612e5e45983fbfdb0348ca23b` |
| `App/static/.DS_Store` | Finder-Runtimemetadaten | Nur Git-Tracking entfernen | `beab13b832f59cb83d6ce073c3b77f62b806ac492a88573db1d9c8d2e3dcb79e` |
| `Backups/collectr_2026-06-02_22-14-58.db` | historisches DB-Backup | Nur Git-Tracking entfernen | `474f1bf0573717c1594a5cb6311d1f8ea99c461357715e1e43315f6c3285654c` |
| `Backups/em24_doppelte.txt` | lokaler Sammlungsexport | Nur Git-Tracking entfernen | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |
| `Branding/.DS_Store` | Finder-Runtimemetadaten | Nur Git-Tracking entfernen | `ab0b7e8b22dd10c744a13265b6097285aca2f011dfd8e7958c5c8b40521f46af` |
| `Branding/App Icons/.DS_Store` | Finder-Runtimemetadaten | Nur Git-Tracking entfernen | `0ef849a695da0588276fc0988d17f9184485e342a81ca6c12b24efba58408ff5` |
| `Branding/Design Bible/.DS_Store` | Finder-Runtimemetadaten | Nur Git-Tracking entfernen | `185a5e23235938f353ece56ec2227adec12a75c9da7d25c58384cd9f86655b1b` |
| `Branding/Design Bible/00 Source Assets/.DS_Store` | Finder-Runtimemetadaten | Nur Git-Tracking entfernen | `5abcedd472973e7476c329a2ad74a2586d4163c21eed957c0b585542be6bb56c` |
| `Branding/Design Bible/01 Master Assets/.DS_Store` | Finder-Runtimemetadaten | Nur Git-Tracking entfernen | `56377ce4c4fd7434605dd22a99e368d2d9d509d6a2dca18e94ac960a9acfc43f` |
| `Branding/Logos/.DS_Store` | Finder-Runtimemetadaten | Nur Git-Tracking entfernen | `72a83a45f0c2e6d7fd4942add1fa198c0497ab689a796517d3d921c23acd3371` |
| `Dokumentation/.DS_Store` | Finder-Runtimemetadaten | Nur Git-Tracking entfernen | `cc7e8f35f08e6e3d0406aef6826d141d9c207dc718b41c3ddfa51e950032a320` |
| `Dokumentation/Product Bible/.DS_Store` | Finder-Runtimemetadaten | Nur Git-Tracking entfernen | `5a5ce8d70b4f789525da88c300014f71bddd0f078d52ef18bd4cbae8373448d2` |
| `Exports/doppelte.txt` | lokaler Sammlungsexport | Nur Git-Tracking entfernen | `e7adab9e311d07fd26fc50a452ccdf68c821aef0a2c2cab74b005ff7135e8f16` |
| `Exports/em24_doppelte.txt` | lokaler Sammlungsexport | Nur Git-Tracking entfernen | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |
| `Exports/em24_doppelte.txt.sb-dbb357db-Ma1uD4` | lokaler Sammlungsexport | Nur Git-Tracking entfernen | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |
| `Exports/em24_fehlende.txt` | lokaler Sammlungsexport | Nur Git-Tracking entfernen | `ecea639f00b92aea8b1beb31e1abd6017718b0882e2ab08100be844b5ea6ca04` |
| `Exports/fehlende.txt` | lokaler Sammlungsexport | Nur Git-Tracking entfernen | `2d821f3a14930f07eb261999d3f506deb485aa473e647d803cf7bc54ab788a3e` |


## Fortsetzungsabschluss – Trackingbereinigung ausgeführt, neuer STOP

Die Freigabe wurde für exakt 29 eindeutig lokale Dateien umgesetzt: eine aktive DB, sieben historische DB-Backups, acht Sammlungsexporte und 13 Finder-Metadatendateien. Ausschließlich `git rm --cached -- <exakter Pfad>`; nach jeder einzelnen Entfernung Existenz und unveränderten SHA256 geprüft. Kein lokales Löschen, keine DB-Migration, kein Leeren und keine neue DB erzeugt. Die vom Werkzeug ausgegebenen `rm`-Zeilen beziehen sich ausschließlich auf den Index.

### Vollständiger Vorher-/Nachhernachweis

| Lokale Datei | Lokal vorhanden | SHA256 vorher | SHA256 nachher |
|---|---|---|---|
| `.DS_Store` | ja | `23e5f150c1ff101835fed7d763e511bd9360192d7c9bd13272c1810925be3e42` | `23e5f150c1ff101835fed7d763e511bd9360192d7c9bd13272c1810925be3e42` |
| `App/.DS_Store` | ja | `c42474c79a09ce6b6a3a1871de0c397dec340efa73cb5b398946642f2d02cec4` | `c42474c79a09ce6b6a3a1871de0c397dec340efa73cb5b398946642f2d02cec4` |
| `App/Database/.DS_Store` | ja | `0bc41c416a8286a45becd4a597f83877d45906cf38686e55c0c091d8ff25ade2` | `0bc41c416a8286a45becd4a597f83877d45906cf38686e55c0c091d8ff25ade2` |
| `App/Database/Database:Backups/collectr_backup_before_trophy_cleanup.db` | ja | `447a9164ba7772b04ee12ccfc5c65a39720cf1f1776c86002ffe3161fded287e` | `447a9164ba7772b04ee12ccfc5c65a39720cf1f1776c86002ffe3161fded287e` |
| `App/Database/Database:Backups/collectr_backup_before_users.db` | ja | `f4796d18d36a6a0f1625bfc7eb2fb926006ef50d534472ca32a3cfbe0a4e8039` | `f4796d18d36a6a0f1625bfc7eb2fb926006ef50d534472ca32a3cfbe0a4e8039` |
| `App/Database/Database:Backups/collectr_backup_popup_clean.db` | ja | `6bcb037730123b78fe756856bc8735a7358f185872040d179fc34a5ebb1d51e3` | `6bcb037730123b78fe756856bc8735a7358f185872040d179fc34a5ebb1d51e3` |
| `App/Database/Database:Backups/collectr_backup_trophy_tabs_visual_runs.db` | ja | `6bcb037730123b78fe756856bc8735a7358f185872040d179fc34a5ebb1d51e3` | `6bcb037730123b78fe756856bc8735a7358f185872040d179fc34a5ebb1d51e3` |
| `App/Database/Database:Backups/collectr_backup_users_trophy_clean_runs.db` | ja | `602883a8538f9377847542c1c7c969d326adc7d071c6cca2ff5822eca1b96f8f` | `602883a8538f9377847542c1c7c969d326adc7d071c6cca2ff5822eca1b96f8f` |
| `App/Database/collectr.db Kopie` | ja | `f25e1b02975da4cda2dfc0e217fe30ae294030dbb9fc0b7a5b6d4b93318f5e4a` | `f25e1b02975da4cda2dfc0e217fe30ae294030dbb9fc0b7a5b6d4b93318f5e4a` |
| `App/Database/em24_fehlende.txt` | ja | `ecea639f00b92aea8b1beb31e1abd6017718b0882e2ab08100be844b5ea6ca04` | `ecea639f00b92aea8b1beb31e1abd6017718b0882e2ab08100be844b5ea6ca04` |
| `App/Database/fehlende.txt` | ja | `2d821f3a14930f07eb261999d3f506deb485aa473e647d803cf7bc54ab788a3e` | `2d821f3a14930f07eb261999d3f506deb485aa473e647d803cf7bc54ab788a3e` |
| `App/Database/sammlr.db` | ja | `164917d8fd97e517cbb4323326f5f2aff85db9ed0e42c54d6f4849b28ad0c602` | `164917d8fd97e517cbb4323326f5f2aff85db9ed0e42c54d6f4849b28ad0c602` |
| `App/services/.DS_Store` | ja | `d93309d94b32ba6fedff8aeee437df419d9e6de612e5e45983fbfdb0348ca23b` | `d93309d94b32ba6fedff8aeee437df419d9e6de612e5e45983fbfdb0348ca23b` |
| `App/static/.DS_Store` | ja | `beab13b832f59cb83d6ce073c3b77f62b806ac492a88573db1d9c8d2e3dcb79e` | `beab13b832f59cb83d6ce073c3b77f62b806ac492a88573db1d9c8d2e3dcb79e` |
| `Backups/collectr_2026-06-02_22-14-58.db` | ja | `474f1bf0573717c1594a5cb6311d1f8ea99c461357715e1e43315f6c3285654c` | `474f1bf0573717c1594a5cb6311d1f8ea99c461357715e1e43315f6c3285654c` |
| `Backups/em24_doppelte.txt` | ja | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |
| `Branding/.DS_Store` | ja | `ab0b7e8b22dd10c744a13265b6097285aca2f011dfd8e7958c5c8b40521f46af` | `ab0b7e8b22dd10c744a13265b6097285aca2f011dfd8e7958c5c8b40521f46af` |
| `Branding/App Icons/.DS_Store` | ja | `0ef849a695da0588276fc0988d17f9184485e342a81ca6c12b24efba58408ff5` | `0ef849a695da0588276fc0988d17f9184485e342a81ca6c12b24efba58408ff5` |
| `Branding/Design Bible/.DS_Store` | ja | `185a5e23235938f353ece56ec2227adec12a75c9da7d25c58384cd9f86655b1b` | `185a5e23235938f353ece56ec2227adec12a75c9da7d25c58384cd9f86655b1b` |
| `Branding/Design Bible/00 Source Assets/.DS_Store` | ja | `5abcedd472973e7476c329a2ad74a2586d4163c21eed957c0b585542be6bb56c` | `5abcedd472973e7476c329a2ad74a2586d4163c21eed957c0b585542be6bb56c` |
| `Branding/Design Bible/01 Master Assets/.DS_Store` | ja | `56377ce4c4fd7434605dd22a99e368d2d9d509d6a2dca18e94ac960a9acfc43f` | `56377ce4c4fd7434605dd22a99e368d2d9d509d6a2dca18e94ac960a9acfc43f` |
| `Branding/Logos/.DS_Store` | ja | `72a83a45f0c2e6d7fd4942add1fa198c0497ab689a796517d3d921c23acd3371` | `72a83a45f0c2e6d7fd4942add1fa198c0497ab689a796517d3d921c23acd3371` |
| `Dokumentation/.DS_Store` | ja | `cc7e8f35f08e6e3d0406aef6826d141d9c207dc718b41c3ddfa51e950032a320` | `cc7e8f35f08e6e3d0406aef6826d141d9c207dc718b41c3ddfa51e950032a320` |
| `Dokumentation/Product Bible/.DS_Store` | ja | `5a5ce8d70b4f789525da88c300014f71bddd0f078d52ef18bd4cbae8373448d2` | `5a5ce8d70b4f789525da88c300014f71bddd0f078d52ef18bd4cbae8373448d2` |
| `Exports/doppelte.txt` | ja | `e7adab9e311d07fd26fc50a452ccdf68c821aef0a2c2cab74b005ff7135e8f16` | `e7adab9e311d07fd26fc50a452ccdf68c821aef0a2c2cab74b005ff7135e8f16` |
| `Exports/em24_doppelte.txt` | ja | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |
| `Exports/em24_doppelte.txt.sb-dbb357db-Ma1uD4` | ja | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |
| `Exports/em24_fehlende.txt` | ja | `ecea639f00b92aea8b1beb31e1abd6017718b0882e2ab08100be844b5ea6ca04` | `ecea639f00b92aea8b1beb31e1abd6017718b0882e2ab08100be844b5ea6ca04` |
| `Exports/fehlende.txt` | ja | `2d821f3a14930f07eb261999d3f506deb485aa473e647d803cf7bc54ab788a3e` | `2d821f3a14930f07eb261999d3f506deb485aa473e647d803cf7bc54ab788a3e` |

### .gitignore

Die zuvor bereits vorhandenen pauschalen Regeln `*.db`, `*.db-*`, `*.sqlite`, `*.sqlite3`, `/App/Database/*.db Kopie` und `/Backups/` wurden durch konservative pfadbezogene Regeln ersetzt. Keine Sourcebackups werden allein wegen ihres Ordners ignoriert. Die bestehende `.DS_Store`-Regel bleibt erhalten. Ergänzte/konkretisierte Regeln:

```gitignore
/App/Database/sammlr.db
/App/Database/sammlr.db-*
/App/Database/s20_coverage_debug.db
/App/Database/s20_coverage_debug.db-*
/App/Database/collectr.db Kopie
/App/Database/Database:Backups/*.db
/Backups/*.db
/Backups/*.db-*
/App/Database/em24_fehlende.txt
/App/Database/fehlende.txt
/Backups/em24_doppelte.txt
/Exports/doppelte.txt
/Exports/em24_doppelte.txt
/Exports/em24_doppelte.txt.sb-*
/Exports/em24_fehlende.txt
/Exports/fehlende.txt
```

Alle 29 entfernten Pfade sind durch `git check-ignore` geschützt. Die S00-Binärfixture ist ausdrücklich nicht ignoriert. `.gitignore` liegt weiterhin unstaged/untracked vor; kein Source-Staging und kein Commit.

### Absichtlich weiter versionierte Fixtures

`App/Database/sammlr_reference_s00.db` und `App/Database/sammlr_reference_s00.sql` bleiben im Index. Der maßgebliche S00-Vertrag dokumentiert vollständig erfundene Nutzer/Zugangsdaten/Sammlungszustände, keinen Auszug aus einer Nutzer-DB. Die Binärdatei stimmt bytegenau mit dem dort dokumentierten SHA256 `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971` überein. Die ursprüngliche pauschale Einordnung als ungeklärte DB wurde damit durch konkreten Provenienznachweis aufgelöst, nicht durch Ausnahme vom Datenschutz. Keine legitime Source-/Fixture-/Testdatei aufgrund einer Endung entfernt.

### Neuer Privatdatenbefund – H / STOP

Folgende weiterhin getrackte historische Source-Dateien enthalten literal gesetzte Benutzername-/Passwort-Seeds. Anders als bei S00 liegt kein nachgewiesener synthetischer Fixturevertrag für diese Werte vor. Es wird weder behauptet, dass die Zugangsdaten heute gültig seien, noch werden Werte ausgegeben. Diese Dateien würden aus dem bisherigen HEAD in den neuen Commitbaum vererbt.

| Source-Datei | Zeile | Befund |
|---|---|---|
| `App/Archive/webapp_backup_before_trophy_cleanup.py` | 35 | `INSERT … INTO users … VALUES` mit literalem Benutzername/Passwort; Herkunft ungeklärt |
| `App/Archive/webapp_backup_multiuser_albums.py` | 60 | `INSERT … INTO users … VALUES` mit literalem Benutzername/Passwort; Herkunft ungeklärt |
| `App/Archive/webapp_backup_popup_clean.py` | 46 | `INSERT … INTO users … VALUES` mit literalem Benutzername/Passwort; Herkunft ungeklärt |
| `App/Archive/webapp_backup_session_ready.py` | 49 | `INSERT … INTO users … VALUES` mit literalem Benutzername/Passwort; Herkunft ungeklärt |
| `App/Archive/webapp_backup_trophy_tabs_visual_runs.py` | 46 | `INSERT … INTO users … VALUES` mit literalem Benutzername/Passwort; Herkunft ungeklärt |
| `App/Archive/webapp_backup_users_trophy_clean_runs.py` | 35 | `INSERT … INTO users … VALUES` mit literalem Benutzername/Passwort; Herkunft ungeklärt |
| `App/webapp_backup.py` | 91 | `INSERT … INTO users … VALUES` mit literalem Benutzername/Passwort; Herkunft ungeklärt |
| `App/webapp_broken_now.py` | 91 | `INSERT … INTO users … VALUES` mit literalem Benutzername/Passwort; Herkunft ungeklärt |
| `App/webapp_rescue_candidate.py` | 91 | `INSERT … INTO users … VALUES` mit literalem Benutzername/Passwort; Herkunft ungeklärt |
| `Backups/webapp_2026-06-02_22-14-50.py` | 98 | `INSERT … INTO users … VALUES` mit literalem Benutzername/Passwort; Herkunft ungeklärt |
| `Backups/webapp_2026-06-02_22-14-58.py` | 98 | `INSERT … INTO users … VALUES` mit literalem Benutzername/Passwort; Herkunft ungeklärt |

Gemäß STOP-Regel keine weitere Aufnahmeentscheidung, kein Sourcepatch, keine eigenmächtige Entfernung dieser elf Source-Dateien. Zur Auflösung erforderlich: entweder belastbarer Nachweis synthetischer Werte oder ausdrückliche Freigabe, genau diese historischen Sourcekopien ebenfalls ausschließlich aus dem zukünftigen Gitbaum herauszunehmen. Keine Historybereinigung vorgenommen. Der vollständige Privatdatencheck bleibt bis zur Klärung offen; weitere Kandidaten sind noch nicht freigegeben.

### Reproduzierbarkeit und Teststand

Legitime S00-DB/SQL und bestehende temporäre Testfixture-Mechanik gefunden. Vollständiger Clean-Checkout-/Gate-Nachweis noch nicht durchgeführt. Die Anweisung „keine neue DB erzeugen“ wurde eingehalten. Die separat gestellte Rückfrage betrifft ausschließlich automatisch erzeugte synthetische temporäre Testdatenbanken, die die produktiven Tests benötigen; ohne diese Freigabe keine entsprechenden Tests gestartet.

In dieser Fortsetzung bestanden: 29 Einzelprüfungen lokale Existenz/SHA256/Indexentfernung, Ignoreprüfung aller 29 Pfade, S00-Tracking/Provenienz/Ignore-Ausnahme, `git diff --check`, `git diff --cached --check`. Keine neuen Runtime-/Browser-/Produktivtests vor dem Privatdaten-STOP. Die früheren getrennten 8+29 erfolgreichen Tests stehen oben und sind ausdrücklich keine vollständige aktuelle Savepoint-Gate-Freigabe.

Commit-Hash: **keiner**. Gitstatus: **29 staged deletions ausschließlich der freigegebenen Pfade**, bestehende lokale Entwicklungsänderungen/untracked Dateien bleiben, `.gitignore` und dieses Audit aktualisiert, aber nicht gestagt. Keine weitere Datei in diesem Schritt geändert. Insbesondere war die Löschung von `App/services/notifications.py` bereits im Startstatus dieser Fortsetzung vorhanden; sie wurde weder ausgeführt noch gestagt. Kein Push, kein Deploy.


## Fortsetzung: Freigabe der exakt elf historischen Sourcekopien

Die elf Pfade wurden gegen den vorherigen Audit und tatsächliches Git-Tracking geprüft. Vorher jeweils lokal vorhanden/getrackt, Größe und SHA256 erfasst. Der produktive Einstieg bleibt `Procfile` → `App/webapp.py`; die isolierte Trade-v2-Factory verwendet keine dieser Kopien. Suche nach exakten Dateinamen und Importmodulnamen in App/Scripts/Tests ergab ausschließlich historische Research-Inventar-/Hashnachweise, keine Runtime-/Test-/Importabhängigkeit. Keine kanonische ausgeführte Source entfernt.

Jede Entfernung ausschließlich `git rm --cached -- <exakter Pfad>`. Anschließend lokale Existenz, unveränderte Größe und Hash einzeln geprüft.

| Historische Sourcekopie | Vorher getrackt | Bytes vorher/nachher | Lokal weiterhin vorhanden | SHA256 vorher | SHA256 nachher |
|---|---|---|---|---|---|
| `App/Archive/webapp_backup_before_trophy_cleanup.py` | ja | 33165 / 33165 | ja | `a2aa44e81f3f994f77504e90c530b27137303525a492ec380245a4b9b33526d6` | `a2aa44e81f3f994f77504e90c530b27137303525a492ec380245a4b9b33526d6` |
| `App/Archive/webapp_backup_multiuser_albums.py` | ja | 40660 / 40660 | ja | `bc3a3fe43d3693b0d4b74031274be8d1c5d7cb1f941343ef16e95b33cab5b57c` | `bc3a3fe43d3693b0d4b74031274be8d1c5d7cb1f941343ef16e95b33cab5b57c` |
| `App/Archive/webapp_backup_popup_clean.py` | ja | 34191 / 34191 | ja | `adb74a3418752e59f5047f96651e8fa9ac0f6e2f4cde118a40d673b470233bc5` | `adb74a3418752e59f5047f96651e8fa9ac0f6e2f4cde118a40d673b470233bc5` |
| `App/Archive/webapp_backup_session_ready.py` | ja | 35552 / 35552 | ja | `4959b9c58edd66908d3f7906bd28f2a5d55f92650b7c87b86e3aaefbf53b7cae` | `4959b9c58edd66908d3f7906bd28f2a5d55f92650b7c87b86e3aaefbf53b7cae` |
| `App/Archive/webapp_backup_trophy_tabs_visual_runs.py` | ja | 33638 / 33638 | ja | `1994e83e8bb9d0f1a2db8df48882f01a07b3cc5182de8b21e76976dc550aa47b` | `1994e83e8bb9d0f1a2db8df48882f01a07b3cc5182de8b21e76976dc550aa47b` |
| `App/Archive/webapp_backup_users_trophy_clean_runs.py` | ja | 33131 / 33131 | ja | `8fcb5f1c96bea4bce080079a1e93d90def7233c00304d85ff40f43bd301fabad` | `8fcb5f1c96bea4bce080079a1e93d90def7233c00304d85ff40f43bd301fabad` |
| `App/webapp_backup.py` | ja | 91928 / 91928 | ja | `6c5c8cb71b2963e88e00b9037a98fc7a52e2d1329ba3561b1eadfb53508b703e` | `6c5c8cb71b2963e88e00b9037a98fc7a52e2d1329ba3561b1eadfb53508b703e` |
| `App/webapp_broken_now.py` | ja | 75259 / 75259 | ja | `f593a1265005ffcc919f8031b3145ecc401dd652daa2880ee97f6a18dccfabba` | `f593a1265005ffcc919f8031b3145ecc401dd652daa2880ee97f6a18dccfabba` |
| `App/webapp_rescue_candidate.py` | ja | 91928 / 91928 | ja | `6c5c8cb71b2963e88e00b9037a98fc7a52e2d1329ba3561b1eadfb53508b703e` | `6c5c8cb71b2963e88e00b9037a98fc7a52e2d1329ba3561b1eadfb53508b703e` |
| `Backups/webapp_2026-06-02_22-14-50.py` | ja | 91888 / 91888 | ja | `dd08ff5def62a4131eada143a7220d34184dc7d138e54bc3397f6559e55d22cf` | `dd08ff5def62a4131eada143a7220d34184dc7d138e54bc3397f6559e55d22cf` |
| `Backups/webapp_2026-06-02_22-14-58.py` | ja | 91888 / 91888 | ja | `dd08ff5def62a4131eada143a7220d34184dc7d138e54bc3397f6559e55d22cf` | `dd08ff5def62a4131eada143a7220d34184dc7d138e54bc3397f6559e55d22cf` |

### Neue konkrete Ignore-Regeln

```gitignore
/App/Archive/webapp_backup_before_trophy_cleanup.py
/App/Archive/webapp_backup_multiuser_albums.py
/App/Archive/webapp_backup_popup_clean.py
/App/Archive/webapp_backup_session_ready.py
/App/Archive/webapp_backup_trophy_tabs_visual_runs.py
/App/Archive/webapp_backup_users_trophy_clean_runs.py
/App/webapp_backup.py
/App/webapp_broken_now.py
/App/webapp_rescue_candidate.py
/Backups/webapp_2026-06-02_22-14-50.py
/Backups/webapp_2026-06-02_22-14-58.py
```

Keine pauschale Python-Ignore-Regel; keine produktive Source oder legitime Fixture ignoriert.

### Erneuter Privatdatencheck – zusätzlicher STOP

`App/Database/database.py:6` enthält eine direkte Zuweisung eines nichtleeren Stringliterals an `app.secret_key`. Damit liegt ein im Sourcecode fest eingebauter Flask-Session-Signaturschlüssel vor. Ob er nur ein historischer Entwicklungswert oder jemals real verwendet war, ist nicht durch einen synthetischen Fixturevertrag belegt. Keine Behauptung einer aktuellen Kompromittierung; kein Schlüsselwert wird hier ausgegeben. Die Datei ist weiterhin getrackt und würde in einem neuen Commit enthalten bleiben.

Dieser Pfad ist **nicht** Teil der elf ausdrücklich freigegebenen Kopien. Gemäß aktueller STOP-Regel keine eigenmächtige Änderung, Ignorierung oder Trackingentfernung. Erforderliche Auflösung: Herkunft/Verwendung des Literals klären oder eine gesonderte konkrete Behandlung dieser Datei autorisieren; bei eventueller Trackingentfernung vorher deren Runtime-/Testabhängigkeiten gesondert prüfen.

Der Scan ist ausdrücklich **nicht als final sauber freigegeben**. Nach diesem neuen Befund angehalten, keine Aussage, dass alle weiteren Kandidaten unbedenklich seien. Reproduzierbarkeit und vollständige produktive/Trade-01–11-/SmartDeal-/Stack-Browsergates weiterhin ausstehend, nicht als bestanden ausgegeben. In dieser Fortsetzung bestanden ausschließlich statische Referenzprüfung, Hash-/Größen-/Existenz-/Tracking-/Ignoreprüfungen sowie beide Diff-Whitespacechecks. Frühere Teiltestresultate bleiben historische Teilnachweise. Keine Tests repariert.

### Abschlussstatus dieser Fortsetzung

- Exakt elf weitere Sourcekopien entfernt; zusammen mit den zuvor freigegebenen 29 Dateien **40 staged Tracking-Entfernungen**. Alle 40 lokal unverändert vorhanden.
- Keine neue Source-/Privatdatei gestagt. Anzahl neu versionierter Savepoint-Dateien: 0; Aufnahmeumfang nicht final freigegeben.
- `.gitignore` und dieses Audit aktualisiert, weiterhin nicht gestagt; übriger vorbestehender Entwicklungsstand erhalten.
- Commit-Hash: keiner; vorgesehener Savepoint-Commit noch nicht erstellt.
- Bewusst lokal bleiben alle 40 freigegebenen Dateien, private Runtime-DB/Backups/Exporte, historische Kopien sowie bisherige unversionierte/ignorierte Entwicklungs-/Researchartefakte. Exakte 40 Pfade und Hashes stehen in den Tabellen dieses Audits.
- Lokale DB und sämtliche historischen Kopien unverändert; keine neue DB erzeugt, keine Nutzerdaten geändert, keine Privatdaten neu versioniert. Kein Push, kein Deploy.


## Gezielte Bereinigung des Flask-Session-Schlüssels

Nur `App/Database/database.py` geändert: vorher hardcoded session signing secret; nachher `os.environ.get("SAMMLR_SECRET_KEY")` → Flask `SECRET_KEY`. Fehlender/leerer Wert führt zu `RuntimeError`, ohne bekannten Fallback. Dieselbe Environmentvariable wird bereits in `App/webapp.py` und `services/runtime_operations.py` verwendet; kein Import der produktiven App, kein zweites Configsystem, kein DB-Aufruf durch den Adapter. `init_db()` wurde weder geändert noch ausgeführt. Die Datei bleibt kanonische Source und getrackt/nicht ignoriert.

Verwendungsanalyse: eigener Flask-App-Gegenstand, keine registrierten Routes/Blueprints in dieser Datei; keine externen Import-/Runtime-/Testreferenzen auf das Modul gefunden. Das ist keine Entfernungserlaubnis; die Nutzerfestlegung als kanonische Source bleibt maßgeblich. Suche nach dem konkreten alten Wert im getrackten/untracked nicht ignorierten Textbestand fand nur die betreffende Zuweisung. Keine Tests setzen diesen konkreten Wert voraus. Kein alter/neuer Schlüsselwert wurde in Terminal, Audit oder Researchdateien ausgegeben.

**lokaler Session-Key vorhanden / nicht versioniert**. Neue `.env`, Dateirechte0600, durch bestehende `.env`-Regel ignoriert; keine zusätzliche Ignore-Regel erforderlich. Kein automatischer dotenv-Loader eingeführt. Lokaler Start mit explizitem Environmentladen:

```sh
set -a
. ./.env
set +a
.venv/bin/python -B App/webapp.py
```

Dieser Startbefehl ist dokumentiert, nicht auf der privaten DB ausgeführt. Das bereinigte Modul selbst wurde mit der lokalen Konfiguration erfolgreich importiert und dessen Sessionserializer roundtrip-geprüft, während sqlite3.connect technisch blockiert war. Produktiver vollständiger App-/HTTP-Smoke bleibt vor dem Savepoint erforderlich.

Sessionfolge: Der neue lokale Schlüssel ersetzt den alten; bisher mit dem alten Schlüssel signierte Flask-Cookies werden ungültig. Erneute Anmeldung kann erforderlich werden. Kein Cookiezugriff, keine Sessionmigration oder -manipulation; keine produktive Rotation/deploymentseitige Änderung durchgeführt.

### Aktuelle Checks

- Produktion ohne SAMMLR_SECRET_KEY: erwarteter sauberer Startabbruch bestanden, DB-Zugriff blockiert.
- Explizit synthetischer Testschlüssel: Import und Session-Signierung bestanden, DB-Zugriff blockiert.
- Ignorierte lokale Konfiguration: Import und Session-Signierung bestanden, DB-Zugriff blockiert; kein Schlüssel ausgegeben.
- Trade-v2/Pax-Unitgruppe: 8 Tests, 0 Failures/Errors.
- Python-AST der betroffenen Source und kanonischen App/Tradefactory geprüft.
- 40 Tracking-Entfernungen, sämtliche lokalen Dateien/Hashes und S00-Fixture weiterhin korrekt; beide Diffchecks bestanden.

### Weiterer Scan und noch ausstehende Freigabe

Kandidateninventur umfasst 2.709 Pfade (bisheriger Gitbaum, bestehende geprüfte Release-Allowlist und neue Source-/Test-/Dokumentationspfade). Heuristische Textscans auf bekannte Token-/Private-Key-Formate und persönliche Mailanbieter ohne weitere Treffer; AST-Suche nach weiteren literalem SECRET_KEY bzw. nicht als Tests eingeordneten User-Insert-Seeds ohne Treffer. Kandidaten-Rasterassets auf EXIF-GPS geprüft, keine Treffer. Bereits ausgeschlossene persönliche Raw-Fotos/Runtime-Daten werden nicht automatisch aufgenommen. Diese Teilprüfungen sind kein abgeschlossener Freigabenachweis sämtlicher Kandidateninhalte oder finaler Staging-Diffs.

Vollständige Reproduzierbarkeit und Produktiv-/SmartDeal-/TRADE-01–11-/Stack-Browsergates stehen aus. Die bestehenden Testmechanismen erzeugen synthetische temporäre Datenbanken. Die frühere ausdrückliche Anweisung „keine neue DB erzeugen“ wurde nicht still übergangen; eine auf /private/tmp begrenzte Ausnahme wurde erfragt. Bis zur Antwort keine DB-Erzeugung und keine davon abhängigen Tests. In dieser Fortsetzung keine bestehende DB geändert und keine neue DB erzeugt.

Kein Savepoint-Commit erstellt, Hash ausstehend. Sourcebereinigung und Audit nicht gestagt; nur die 40 freigegebenen Trackingentfernungen bleiben im Index. Kein Push, kein Deploy.


## Finalisierung nach Freigabe ausschließlich synthetischer temporärer Testdatenbanken

Stand: 2026-10-03. Alle nachfolgenden Tests verwenden ausschließlich `/private/tmp/savepoint00-tests-current` sowie synthetische temporäre Unterverzeichnisse unter `/private/tmp`. Keine bestehende Sammlr-DB wurde kopiert oder als Ausgangsdatenquelle verwendet. Der isolierte Sourceexport enthielt **null Datenbankdateien**. `Scripts.prepare_release_tests` erzeugte die Testdateien ausschließlich aus der dokumentierten synthetischen SQL-Fixture; weitere Testkopien stammen ausschließlich aus diesen neu erzeugten synthetischen Dateien. TMPDIR=/private/tmp, expliziter DATABASE_PATH im isolierten Export, ein SQLite-Audithook blockiert im Gateprozess jeden Dateizugriff außerhalb /private/tmp. In-Memory-Testdaten sind ebenfalls synthetisch.

Die 15 geschützten bestehenden lokalen DB-/Backupdateien wurden vor Beginn gehasht und nach den Tests unverändert vorgefunden. Keine neue DB im Repository. Die beibehaltene S00-Binärfixture wurde nicht als Testquelle kopiert; ihre SQL-Quelle genügt. Keine privaten Nutzer/Adressen/Credentials/Sammlungen/Sessions/Trades in das Testverzeichnis übertragen.

### Vollständige Gates

| Gate | Ergebnis |
|---|---|
| Produktiver Releaseumfang einschließlich Inventory, Privacy, Auth, Legacy, SmartDeal, Wall/Liste | **1296 bestanden**, 0 Fehler, 0 Skips |
| Preview-Isolation Trade-v2/Pax, eigener Prozess | **8 bestanden**, 0 Fehler |
| TRADE-01 | Drei mobile Breiten; Journeys, **21 kanonische Stackfälle**, keine Schreib-/externen Requests/Browserfehler |
| TRADE-02 | Vier Breiten, Sender/Kapazität/Idempotenz/absolute Expiry und beschädigter lokaler Speicher bestanden |
| TRADE-03 | Vier Breiten, Spiegelung, Accept/Decline/Expiry, Rollen/Slots/Doppelaktionen und acht Direktszenarien bestanden |
| TRADE-04 | Vier Breiten, 14 Demos, Packmodell/Interaktionen bestanden |
| TRADE-05 | Vier Breiten, Fehlmengen-/Zustimmungs-/Abbruchjourneys, **205 Modellassertionen** bestanden |
| TRADE-06 | Vier Breiten, **259 Modellassertionen**, Adressprivacy/Richtungen/Slots/Versionen/Races bestanden |
| TRADE-07 | **1047 Modellassertionen**, vollständige E2E-, Problem- und Q2-Journeys bestanden |
| TRADE-08 | **90 Adapterassertionen**, vier Breiten bestanden |
| TRADE-09 | Vier Breiten, je **52 Modellassertionen**, bilaterale Regeln, Mengenlimits, manuelle E2E, kein Overflow bestanden |
| TRADE-10 | Übersicht/Handlungsprojektion und zugehöriges Modell bestanden |
| TRADE-11 | Echte Produktions-Wall-Parität bei 375/390/430/1280, vorwärts/rückwärts Motion, keine Skalierung/Überläufe bestanden |
| Numerische kanonische Liste/Stack-Parität | **28 Vergleiche** bestanden; Mengen1/2/5/6/10/15/37, Cap10 wächst nicht weiter |
| Wallcap5 / Tradecap10 | Direkte Renderer-/Layer- und Face-/z-index-Paritätsprüfungen bestanden |
| Kanonischer App-Smoke auf synthetischer DB | /healthz, /login, /static/style.css jeweils200 |
| Secretadapter | Produktion ohne Key verweigert Start; synthetischer und lokaler Environmentkey signieren Sessions ohne DB-Zugriff |
| Whitespace | git diff --check und git diff --cached --check bestanden |

1308 Tests im produktiven Prozess entdeckt, davon zwölf **bereits im bestehenden R5_TEST_CONTRACT.json** ausgegliederte historische/Baselineprüfungen unverändert behandelt; keine neuen Ausschlüsse, kein Test repariert, keine erwarteten Fehler hinzugefügt. Die acht Preview-Isolationstests müssen gemäß bestehendem TRADE-11-Aufruf in eigenem Prozess laufen, damit vorheriger produktiver Appimport ihre Isolationsaussage nicht verfälscht. Alle vorgesehenen aktuellen Release-/Tradegates grün; keine Behauptung, die historischen Originalfoto-/alte DB-Hashprüfungen seien ausgeführt worden.

Browserrunner importiert die vorhandenen Testmodule unverändert und setzt ausschließlich BASE auf den eigenen Loopback-Port18095 und OUT auf /private/tmp. Für das unmittelbar ausführende Paritätsskript wurde ausschließlich dieselbe BASE-Konstante im Speicher angepasst. Kein Assert, Domainmodell oder Repositorytest verändert. Bestehende Nutzerpreview auf8095 nicht angefasst. Generierte Screenshots und Browserprofile verbleiben außerhalb des Repositorys und werden nicht aufgenommen.

### Reproduzierbarkeit / Privatdatenprüfung

2727 Source-/Vertrags-/Test-/Assetdateien in isoliertem Export geprüft. Die getesteten Originalquellen stimmen weiterhin bytegleich mit dem aufzunehmenden Arbeitsbaum überein (Auditfortschreibung und generierte Researchresultate getrennt). Kanonische App, Trade-v2, Pax-Komponenten, Stickerwall/-liste, Migrationen, synthetische SQL-Fixture, Fonts/Glyphen und Tests sind enthalten. Keine Abhängigkeit auf die 40 lokal zurückbehaltenen Dateien gefunden.

Runtime-Abhängigkeiten: requirements.txt; Test-/Assetabhängigkeiten: requirements-test.txt. Browsergates benötigen zusätzlich **playwright==1.62.0** und dessen Chromium; diese zusätzliche bestehende Testabhängigkeit wird hier ausdrücklich dokumentiert, nicht als in requirements-test.txt enthalten behauptet. Für frische Testumgebung: `python -m pip install -r requirements-test.txt playwright==1.62.0`, danach `python -m playwright install chromium`. Keine Installation/Versionsänderung in dieser Prüfung. Reproduktion in einem /private/tmp-Sourceexport mit TMPDIR=/private/tmp, synthetischem Testing-Key und Scripts.prepare_release_tests; nie eine lokale Entwicklungs-DB kopieren.

Finale Kandidatenprüfung umfasst bekannte Schlüssel-/Token-/Private-Key-Muster, fest kodierte Flask-Konfiguration, User-/Passwort-Seeds und deren Testherkunft, persönliche Mailanbieter, EXIF-GPS in aufzunehmenden Rasterassets sowie explizite DB-/Backup-/Runtime-/Export-Ausschlüsse. Keine weitere ungeklärte Fundstelle im ausgewählten zukünftigen Baum. Die .env und echte lokale Schlüssel sind ausgeschlossen; Beispiele/Testschlüssel ausschließlich synthetisch. Alte entfernte Sourcekopien bleiben lokal; bestehende Git-History wird nicht umgeschrieben und kann frühere Secrets enthalten. Kein Push.

Die vollständige dateibezogene Klassifikation, Aufnahmeliste, 40 Vorher-/Nachher-Hashes und DB-Schutzmanifest stehen in **docs/SAVEPOINT_00_FILES.json**. Kategorien A/B/C/D und für Nachweis notwendige E aufgenommen; generierte Screenshot-/Temporärbestände und nicht benötigte Research-/Designexperimente verbleiben lokal. Keine pauschale Aufnahme aller Dateien.

Zusätzlich wird die **bereits vor dieser Fortsetzung vorhandene Löschung von App/services/notifications.py** als Entwicklungszustand festgehalten. Sie ist keine weitere von SAVEPOINT vorgenommene lokale Löschung oder Privatdatenbereinigung. Die aktive Typed-Notification-Implementierung und ihre Regressionen sind vorhanden und grün. Die 40 freigegebenen `--cached`-Entfernungen bleiben davon getrennt.

### Aufnahme und Commit

Explizite Pfadliste, kein git add .; vollständiger staged Diff wird vor Commit kontrolliert, ohne darin enthaltene alte entfernte Schlüsselwerte zu loggen. Der Commit ist ausschließlich Vorintegrations-Savepoint, keine produktive Trade-v2-Freigabe. Commitmessage: `savepoint: freeze pre-integration trade-v2 baseline`. Der tatsächliche Commit-Hash und abschließende Gitstatus werden nach erfolgreichem Commit im Abschlussbericht genannt; kein selbstreferenzieller Hash in diesem Commitdokument.


## Abschließender Staging-Gate: STOP wegen bestehender Whitespacebefunde

Nach gezieltem Staging des gesamten Kandidaten wurde der vollständige Gitbaum blobweise gelesen, mit den geprüften lokalen Dateien verglichen und nochmals auf den alten/hiesigen lokalen Schlüssel, Credentialmuster und SQLite-Dateien geprüft. **Keine neuen ungeklärten Privatdaten-/Secretfunde**; einzige DB im Index ist die dokumentierte synthetische S00-Fixture. Alle 40 freigegebenen lokalen Dateien und 15 DB-Hashes weiterhin unverändert.

Der anschließend auf dem vollständigen Index ausgeführte `git diff --cached --check` liefert jedoch **Exitcode2**. Frühere grüne Checks betrafen den vorherigen Index mit lediglich den Trackingentfernungen; bislang unversionierte Dateien waren darin nicht enthalten. Die nachstehende Prüfung ersetzt deshalb jede frühere pauschale Aussage „beide Diffchecks bestanden“ für den finalen Umfang.

**123 Befunde in 55 Dateien:** 31 × new blank line at EOF., 92 × trailing whitespace.. Einige Markdown-Zeilen verwenden zwei Leerzeichen als expliziten Zeilenumbruch; deshalb wäre pauschales Entfernen nicht nur eine mechanisch folgenlose Entscheidung. Keine Source-/Test-/Dokumentationsbereinigung und keine Git-Whitespace-Ausnahme eigenmächtig vorgenommen.

| Datei | Zeile | Exakter Checkbefund |
|---|---|---|
| `App/Database/base_schema.sql` | 66 | new blank line at EOF. |
| `App/Database/catalog_seed.sql` | 6 | new blank line at EOF. |
| `App/Database/migrations/0009_friendships_community.up.sql` | 54 | new blank line at EOF. |
| `App/Database/migrations/0014_collection_history_cutover.down.sql` | 3 | new blank line at EOF. |
| `App/Database/migrations/0014_collection_history_cutover.up.sql` | 34 | new blank line at EOF. |
| `App/services/observability.py` | 99 | new blank line at EOF. |
| `App/static/sticker_list.css` | 1697 | new blank line at EOF. |
| `Branding/CEOKlaue/03_font/build_ceoklaue.py` | 242 | trailing whitespace. |
| `Dokumentation/Post-RC/01-product-audit/08-profil-community.md` | 3 | trailing whitespace. |
| `Dokumentation/Post-RC/01-product-audit/08-profil-community.md` | 4 | trailing whitespace. |
| `Dokumentation/Post-RC/01-product-audit/09-sammlr-home-feed.md` | 3 | trailing whitespace. |
| `Dokumentation/Post-RC/01-product-audit/09-sammlr-home-feed.md` | 4 | trailing whitespace. |
| `Dokumentation/Post-RC/01-product-audit/09-sammlr-home-feed.md` | 5 | trailing whitespace. |
| `Dokumentation/Post-RC/01-product-audit/10-notifications.md` | 3 | trailing whitespace. |
| `Dokumentation/Post-RC/01-product-audit/10-notifications.md` | 4 | trailing whitespace. |
| `Dokumentation/Post-RC/01-product-audit/10-notifications.md` | 5 | trailing whitespace. |
| `Dokumentation/Post-RC/01-product-audit/11-trophaeen.md` | 3 | trailing whitespace. |
| `Dokumentation/Post-RC/01-product-audit/11-trophaeen.md` | 4 | trailing whitespace. |
| `Dokumentation/Post-RC/01-product-audit/11-trophaeen.md` | 84 | trailing whitespace. |
| `Dokumentation/Post-RC/01-product-audit/11-trophaeen.md` | 85 | trailing whitespace. |
| `Dokumentation/Post-RC/01-product-audit/12-statistik.md` | 3 | trailing whitespace. |
| `Dokumentation/Post-RC/01-product-audit/12-statistik.md` | 4 | trailing whitespace. |
| `Dokumentation/Post-RC/01-product-audit/13-albumabschluss-vitrine.md` | 3 | trailing whitespace. |
| `Dokumentation/Post-RC/01-product-audit/13-albumabschluss-vitrine.md` | 4 | trailing whitespace. |
| `Dokumentation/Post-RC/02-cross-audit/01-product-contract-konsolidierung.md` | 3 | trailing whitespace. |
| `Dokumentation/Post-RC/02-cross-audit/01-product-contract-konsolidierung.md` | 4 | trailing whitespace. |
| `Dokumentation/Post-RC/02-cross-audit/01-product-contract-konsolidierung.md` | 200 | trailing whitespace. |
| `Dokumentation/Post-RC/02-cross-audit/01-product-contract-konsolidierung.md` | 211 | trailing whitespace. |
| `Dokumentation/Post-RC/02-cross-audit/01-product-contract-konsolidierung.md` | 222 | trailing whitespace. |
| `Dokumentation/Post-RC/02-cross-audit/01-product-contract-konsolidierung.md` | 233 | trailing whitespace. |
| `Dokumentation/Post-RC/02-cross-audit/01-product-contract-konsolidierung.md` | 244 | trailing whitespace. |
| `Dokumentation/Post-RC/02-cross-audit/01-product-contract-konsolidierung.md` | 255 | trailing whitespace. |
| `Dokumentation/Post-RC/02-cross-audit/01-product-contract-konsolidierung.md` | 266 | trailing whitespace. |
| `Dokumentation/Post-RC/02-cross-audit/01-product-contract-konsolidierung.md` | 277 | trailing whitespace. |
| `Dokumentation/Post-RC/02-cross-audit/01-product-contract-konsolidierung.md` | 288 | trailing whitespace. |
| `Dokumentation/Post-RC/02-cross-audit/02-product-contract-freeze.md` | 3 | trailing whitespace. |
| `Dokumentation/Post-RC/02-cross-audit/02-product-contract-freeze.md` | 4 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-004-backfill-audit.md` | 3 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-004-backfill-audit.md` | 6 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-004-report.md` | 3 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-005-report.md` | 3 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-005-report.md` | 4 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-008-report.md` | 3 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-008-report.md` | 4 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-008-report.md` | 5 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-008-report.md` | 6 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-009-report.md` | 3 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-009-report.md` | 4 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-009-report.md` | 5 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-009-report.md` | 6 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-010-report.md` | 3 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-011-report.md` | 3 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-011-report.md` | 4 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-011-report.md` | 5 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-011-report.md` | 183 | new blank line at EOF. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-012-report.md` | 3 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-012-report.md` | 4 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-012-report.md` | 5 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-013-report.md` | 3 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-013-report.md` | 4 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-013-report.md` | 5 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-013-report.md` | 196 | new blank line at EOF. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-014-report.md` | 3 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-014-report.md` | 4 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-014-report.md` | 5 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-015-report.md` | 3 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-015-report.md` | 4 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-015-report.md` | 5 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-016-report.md` | 3 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-016-report.md` | 4 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-016-report.md` | 5 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-017-report.md` | 3 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-017-report.md` | 4 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-017-report.md` | 5 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-017-report.md` | 6 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-017-report.md` | 246 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/CB-017-report.md` | 247 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/Phase-7-engineering-hardening-report.md` | 3 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/Phase-7-engineering-hardening-report.md` | 4 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/Phase-7-engineering-hardening-report.md` | 5 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/Phase-7-engineering-hardening-report.md` | 6 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/Phase-8-realistic-simulation-report.md` | 3 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/Phase-8-realistic-simulation-report.md` | 4 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/Phase-8-realistic-simulation-report.md` | 5 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/Phase-8-realistic-simulation-report.md` | 6 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/Phase-9-closed-beta-gate-report.md` | 3 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/Phase-9-closed-beta-gate-report.md` | 4 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/Phase-9-closed-beta-gate-report.md` | 5 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/Phase-9-closed-beta-gate-report.md` | 6 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/Phase-9-closed-beta-gate-report.md` | 7 | trailing whitespace. |
| `Dokumentation/Post-RC/04-implementation-reports/UI-current-state-product-integration-report.md` | 191 | new blank line at EOF. |
| `Dokumentation/Post-RC/04-implementation-reports/UIF-004A-report.md` | 84 | trailing whitespace. |
| `Dokumentation/Product Bible/roadmap/s03-side-effect-security-test-gate.md` | 139 | new blank line at EOF. |
| `Dokumentation/Product Bible/roadmap/s06-global-header-shell.md` | 81 | new blank line at EOF. |
| `Dokumentation/Product Bible/roadmap/s07-deep-link-origin-context.md` | 112 | new blank line at EOF. |
| `Dokumentation/Product Bible/roadmap/s08-inventory-contract-v1.md` | 3 | trailing whitespace. |
| `Dokumentation/Product Bible/roadmap/s08-inventory-contract-v1.md` | 4 | trailing whitespace. |
| `Dokumentation/Product Bible/roadmap/s08-inventory-contract-v1.md` | 245 | new blank line at EOF. |
| `Dokumentation/Product Bible/roadmap/s09-inventory-read-service.md` | 3 | trailing whitespace. |
| `Dokumentation/Product Bible/roadmap/s09-inventory-read-service.md` | 4 | trailing whitespace. |
| `Dokumentation/Product Bible/roadmap/s09-inventory-read-service.md` | 154 | new blank line at EOF. |
| `Dokumentation/Product Bible/roadmap/s10-inventory-write-service.md` | 3 | trailing whitespace. |
| `Dokumentation/Product Bible/roadmap/s10-inventory-write-service.md` | 4 | trailing whitespace. |
| `Dokumentation/Product Bible/roadmap/s10-inventory-write-service.md` | 172 | new blank line at EOF. |
| `Dokumentation/Product Bible/roadmap/s11-availability.md` | 3 | trailing whitespace. |
| `Dokumentation/Product Bible/roadmap/s11-availability.md` | 4 | trailing whitespace. |
| `Dokumentation/Product Bible/roadmap/s11-availability.md` | 182 | new blank line at EOF. |
| `Dokumentation/Product Bible/roadmap/s12-inventory-guard.md` | 3 | trailing whitespace. |
| `Dokumentation/Product Bible/roadmap/s12-inventory-guard.md` | 4 | trailing whitespace. |
| `Dokumentation/Product Bible/roadmap/s12-inventory-guard.md` | 209 | new blank line at EOF. |
| `Dokumentation/Product Bible/roadmap/s13-trade-lifecycle-schema.md` | 199 | new blank line at EOF. |
| `Dokumentation/Product Bible/roadmap/s14-trade-reservations.md` | 253 | new blank line at EOF. |
| `Dokumentation/Product Bible/roadmap/s15-trade-shipping-transit.md` | 269 | new blank line at EOF. |
| `Dokumentation/Product Bible/roadmap/s18-trade-lifecycle-timeline.md` | 182 | new blank line at EOF. |
| `Dokumentation/Product Bible/roadmap/s37-beta-polish.md` | 105 | new blank line at EOF. |
| `Dokumentation/Product Bible/roadmap/sprint-reports/S03-report.md` | 86 | new blank line at EOF. |
| `Dokumentation/Product Bible/roadmap/sprint-reports/S07-report.md` | 133 | new blank line at EOF. |
| `Dokumentation/Product Bible/roadmap/sprint-reports/S08-report.md` | 140 | new blank line at EOF. |
| `Dokumentation/Product Bible/roadmap/sprint-reports/S13-report.md` | 198 | new blank line at EOF. |
| `Dokumentation/Product Bible/roadmap/sprint-reports/S14-report.md` | 272 | new blank line at EOF. |
| `Dokumentation/Product Bible/roadmap/sprint-reports/S15-report.md` | 294 | new blank line at EOF. |
| `Scripts/backup_sqlite.py` | 46 | new blank line at EOF. |
| `Scripts/predeploy.py` | 63 | new blank line at EOF. |

### Verbindlicher Abschlussstatus

- 1296 produktive Release-/Regressionstests +8 separate Previewtests bestanden; TRADE-01–11 und21/28 Stackvergleiche bestanden. Bestehender R5-Testvertrag unverändert.
- Reproduktion aus isoliertem Sourcebestand mit ausschließlich neu erzeugtem synthetischem SQL-Testbestand bestanden; keine bestehende Sammlr-DB kopiert.
- Privater Schlüssel nur ignorierte .env; aktive Sourcebereinigung geprüft; kein neuer ungeklärter Secretfund im staged Baum.
- git diff --check vor Staging grün; **finaler git diff --cached --check rot**. Kein Test/Gate repariert, abgeschwächt oder durch Konfigurationsänderung umgangen.
- **Commit-Hash: keiner.** Kein Savepoint-Commit erstellt, keine neuen Dateien durch Commit versioniert.
- Der explizit aufgenommene Kandidat bleibt im Index erhalten. Keine Rücksetzung; die lokalen Dateien werden dadurch nicht gelöscht.
- Staged Statusklassen bei STOP: `{'D': 41, 'A': 2543, 'M': 11}`. D enthält40 autorisierte reine Trackingentfernungen plus die schon vorher vorhandene Source-Löschung von App/services/notifications.py.
- Dieses Audit und SAVEPOINT_00_FILES.json wurden nach dem STOP im Arbeitsbaum aktualisiert; diese letzten Reportkorrekturen sind noch nicht erneut gestagt. Der vorbereitete Index ist nicht als finale Freigabe anzusehen.
- Screenshots/Browserartefakte und synthetische Test-DBs verbleiben zur Diagnose nur unter /private/tmp; keine neue DB im Repository, keine Test-DB im Index. Keine privaten DB-/Nutzerinhalte in die Testumgebung übertragen.
- Keine bestehende lokale DB oder historische Kopie verändert; kein Push, kein Deploy.

Nötige nächste Entscheidung: die konkret dokumentierten Whitespacebefunde gezielt behandeln oder ausdrücklich eine fachlich passende Whitespacebewertung festlegen; der aktuelle Auftrag erlaubt keine eigenmächtige Reparatur. Bis dahin kein Commit.


## Autorisierte mechanische Whitespacebereinigung

Die aktuellen 123 staged Befunde wurden vor jeder Änderung erneut mit der vorherigen Liste verglichen: identische55 Dateien und123 Stellen. Vorherbytes der55 Dateien stimmten mit dem Index überein und wurden außerhalb des Repositorys gesichert. Ausschließlich92 gemeldete nachgestellte Whitespacevorkommen und31 gemeldete Leerzeilenbereiche am Dateiende entfernt. Jede nicht gemeldete Zeile unverändert; vorhandene LF-/CRLF-Zeilenenden erhalten. Kein Formatter, keine Import-/Kommentar-/Logikänderung.

Für alle55 Dateien sind die Nicht-Whitespace-Bytes identisch; für betroffene Pythondateien zusätzlich vollständige AST-Gleichheit (einschließlich Stringwerte) nachgewiesen. Die explizit freigegebene Entfernung von Markdown-Zeilenend-Leerzeichen ist Teil dieser mechanischen Liste, keine weitergehende Umformatierung. Die beiden Auditdateien werden gesondert wie beauftragt fortgeschrieben; keine weitere Source-/Testdatei geändert.

Genau55 korrigierte Pfade erneut gestagt, kein git add .; die40 autorisierten Trackingentfernungen unverändert. Die vollständigen123 Befunde sowie Vorher-/Nachherhashes der55 Dateien stehen in SAVEPOINT_00_FILES.json.

### Erneute Smoke-Gates

- Trade-v2/Pax Preview:8 Tests bestanden.
- Kanonische Stickerwall:11 Tests bestanden.
- App-/Secretadapter-Import und /healthz, /login, /static/style.css: bestanden/HTTP200 mit synthetischer Test-DB.
- Beide Diffchecks nach mechanischer Bereinigung: Exit0, keine Befunde.
- Der vorherige vollständige Umfang von1296+8=1304 bestandenen Tests und TRADE-01–11 bleibt gültig; kein erneuter vollständiger Durchlauf, wie ausdrücklich autorisiert.

Alle Smokes ausschließlich im bisherigen isolierten synthetischen Source-/Testbestand unter /private/tmp; kopiert wurden nur die55 bereinigten Source-/Dokumentationsdateien, keine bestehende Sammlr-DB.15 lokale geschützte DBs weiterhin bytegleich.


### Finaler Nachweis nach Whitespacebereinigung

Direkte Produktions-Wall-/Trade-Parität bei375/390/430/1280 sowie28 numerische Stackvergleiche erneut bestanden. Wallcap5/Tradecap10 und konstante Geometrie ab10 weiterhin korrekt. Damit alle geforderten Nach-Smokes grün. Keine über die exakt freigegebene Whitespacebereinigung hinausgehende Sourceänderung; die bereits freigegebene SAMMLR_SECRET_KEY-Bereinigung bleibt erhalten.

Finaler Scope:40 freigegebene reine Trackingentfernungen (alle lokal vorhanden/Hash identisch), vorbestehender aktueller Entwicklungsstand einschließlich bereits vorher gelöschter alter notifications.py, geprüfte Source-/Vertrags-/Testdateien, zwei Savepoint-Auditdateien. Geheimwerte, lokale Runtime-/Backup-/Exportdateien und neu generierte Screenshots bleiben ausgeschlossen. Legitime synthetische S00-Fixture bleibt absichtlich versioniert. Der abschließende Gitbaumscan prüft erneut alle Indexblobs und den vollständigen staged Diff; alte entfernte Schlüsselwerte werden dabei nicht ausgegeben oder als Diffartefakt gespeichert.

Reproduzierbarkeit bereits erfolgreich mit ausschließlich synthetischem SQL-Testbestand.1304 vorherige Tests plus TRADE-01–11 grün;19 nachgelagerte Unit-Smokes, HTTP-/Import-Smoke und Browser-Stack-Smokes grün.15 geschützte lokale DBs bytegleich, keine neue DB im Repository, keine Test-DB im Index. Beide Diffchecks Exit0.

Commitmessage: `savepoint: freeze pre-integration trade-v2 baseline`. Kein Push, kein Deploy, kein INTEGRATION-01. Nach Commit nur Abschlussverifikation und Bericht; keine weitere Bereinigung. Bewusst verbleiben .env, die40 geschützten historischen/privaten Dateien, weitere bereits lokale DB-/Uploaddaten, .venv/Caches, nicht aufgenommene Forschungs-/Designexporte und Screenshots lokal. Die ursprüngliche History wird nicht umgeschrieben.
