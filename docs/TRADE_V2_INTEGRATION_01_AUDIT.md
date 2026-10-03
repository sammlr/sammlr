# INTEGRATION-01 — produktive Read-only-Tauschbörse

## Ausgangspunkt und Grenze

Rückkehrpunkt: `a997074bbaeddfd5369edf494fb0e0a9f45952a7` (`savepoint: freeze pre-integration trade-v2 baseline`). Getrackter Arbeitsbaum vor Beginn sauber. Bestehende ungetrackte/ignorierte Design-, Research-, Runtime-, Backup- und Privatdateien bleiben außerhalb dieses Commits. Keine reale App mit privater DB zu Testzwecken gestartet; keine Migration, kein Push, kein Deploy.

Grundlagen: INTEGRATION_MAP, SOURCE_OF_TRUTH_MATRIX, INTEGRATION_PLAN, INTEGRATION_00_AUDIT, SAVEPOINT_00_AUDIT, TRADE_PRODUCT_CONTRACT_V2 und TRADE_11_AUDIT sowie tatsächlicher App-/Auth-/Wall-/SmartDeal-Code. Die neue Shell verwendet keine Preview-Services oder Preview-Fixtures.

## Produktive Routes und Navigation

| Route | Daten/Verhalten |
| --- | --- |
| `/tauschen` | Bis zu drei gültige Deals des kanonischen Optimizers; 0/1/2/3 ohne Auffüllung |
| `/tauschen/sammlr` | Tatsächlich eligible Partner, Matchingmenge und gemeinsame relevante Alben |
| `/tauschen/sammlr/<id>` | Richtungsbezogene Mengen, Alben, SmartDeal-Link ab kanonischem Minimum |
| `/tauschen/vorschlag/<id>` | Genau ein aktuell vorhandener Top-3-Deal, sonst 404 |
| `/tauschen/sammlr/<id>/smartdeal` | Unveränderter Optimizer auf den gewählten eligible Partner eingeschränkt; Read-Berechnung |
| `/tauschen/laufend` | Eigene vorhandene Requests mit Status open/accepted; keine simulierte TRADE-10-Projektion |

Der bestehende gemeinsame Bottom-Nav-Eintrag „Tauschen“ führt auf `/tauschen`, mobil und Desktop. Keine zweite globale Navigation. Andere kontextuelle Home-, Album-, Notification- und Legacy-Links bleiben erhalten. Die produktive Startseite bleibt `/`. Beim bisherigen lokalen Port8080 sind die URLs `http://127.0.0.1:8080/`, `/tauschen`, `/tauschen/sammlr`, `/tauschen/laufend`. Voraussetzung: produktive App mit `SAMMLR_SECRET_KEY` gestartet und angemeldet; keine Behauptung, der bestehende Server sei automatisch neu geladen worden.

Die Links „Bestehenden Tausch öffnen“ verlassen die neue Read-only-Projektion und öffnen die unveränderten Legacy-Workflows. Deren bisherige Aktionen bleiben verfügbar; die neue Shell führt sie nicht aus.

## Auth und Datenquellen

Identität ausschließlich aus der signierten bestehenden Session `user_id`; globale Guard prüft User, auth_version und aktiven Account. Keine neue Auth-Architektur. Die vorhandene Testmodus-Kompatibilität für fehlende auth_version bleibt unverändert; produktive Semantik ebenfalls. Queryparameter user/role/demo/scenario ändern keine Identität und keinen Inhalt. Nicht angemeldete Zugriffe gehen zum Login; nicht eligible Partner/Selbst-/Fremd-IDs liefern 404.

`SmartDealPlanningService` → `SmartDealPairwiseService` → `SmartDealOptimizer`, unveränderte Fachlogik. Reale Quelle ist der bestehende konfigurierte `webapp.DB`-Pfad: Sammlungsbestand, Album-/Tradepool-Freigaben, Community-/Blockregeln, Reservierungen, gebundene Eingänge und tatsächliche Request-/Tradezustände. Keine erfundenen Entfernung-, Online- oder Profilkennzahlen. Eligibility folgt den bestehenden Pool-Regeln; allgemeine Profil-/Album-Sichtbarkeit wird nicht stillschweigend zu einer neuen Tradepool-Regel gemacht.

Der kanonische Reader erwartet V21-SELECT-Felder, die vorhandene V20-Struktur enthält diese noch nicht. Ein rein lesender Adapter projiziert ausschließlich fehlende `contract_type`, `binding_created_at`, `accepted_at` als `legacy`, NULL, NULL. Dies entspricht dem bestehenden Legacy-Default, ohne Schemaänderung/Backfill. V21 wird unverändert durchgereicht; ein partieller Feldsatz wird abgewiesen. Vergleich mit V21-Legacy-Readmodel inklusive synthetischem angenommenem Trade und beidseitigen Reservationspositionen bestanden. Kein Optimizer-/Matching-/Mengenmodul geändert.

## Technische Read-only-Grenze

Neue Blueprint-Routen sind ausschließlich GET (plus implizites HEAD/OPTIONS). Keine Mutation-Endpunkte, kein Aufruf von Cleanup oder Request-/Lifecycle-Commands. SQLite-Verbindung: URI `mode=ro`, `PRAGMA query_only=ON`, SELECT-Snapshot und Authorizer-Allowlist; Schreib-/DDL-Statements werden abgewiesen. Bestehende globale Auth-Lesezugriffe bleiben erhalten. Route-Tests überprüfen POST-Ablehnung, verbotenen Cleanup-Aufruf und vollständige DB-Bytegleichheit. Frontend-JS enthält nur Auf-/Zuklappen und Kartenbreitenmessung, keine Netzwerk-/Storage-/Domainbefehle.

„Tausch anfragen“ und „Selbst auswählen“ sind disabled. Keine Fake-Erfolgsmeldung, Reservation, Slotbelegung, Annahme/Ablehnung, Pack-, Amendment-, Adress-, Versand-, Empfangs- oder Bewertungsaktion. Manuelle Trade-v2-Auswahl bleibt gesperrt, bis beidseitige albumbezogene Einstellungen real persistiert und vollständig lesbar sind.

## Rendering und geschützte Referenzen

Neue Template-/CSS-/JS-Dateien integrieren bestehenden Head, Header und globale Navigation. Explizite Überschrift, weil die produktive Headerdarstellung den internen Workflowtitel unterdrückt. Scoped Layoutregeln vermeiden den für Wall-Editcontrols reservierten Leerraum und responsive Kollisionen.

`sticker_wall_slot_html` erhält ausschließlich einen optionalen Cap (Default5, Trade10). Vorhandene Face-Funktion, Markup, Layer-Richtung, Versatz und z-index bleiben dieselben. Keine zweite Kartenphysik. Die Shell misst die erste echte Wall-Rasterzelle; so entstehen auch bei gerundeten Teilpixel-Spalten keine abweichenden Kartengrößen. Keine Skalierung. Leichte deterministische äußere Rotation nur bei Topvorschlägen. Native details/summary für unabhängig bedienbare Albumgruppen; darin nichtinteraktive Karten vermeiden verschachtelte Links.

App/static/style.css, Stickerlisten-Code, Domainservices, App/pax und App/trade_v2 bytegleich zum Savepoint. Die Preview auf8095 bleibt unverändert; Regression nur auf eigenem Testport18095. Die produktive Shell ist bewusst noch grob: native Buttons/Albumgruppen statt finaler Papierinszenierung, echte Legacy-Statuslabels statt simulierter Preview-Lifecyclezustände. Keine finalen Filter oder manuelle Auswahl.

## Verifikation

- 1.303 produktive Release-/Integrationstests grün, keine Fehler/Skips; davon sieben neue Shell-Tests. 1.315 entdeckt, die zwölf bestehenden historischen/Baseline-Klassifizierungen aus R5_TEST_CONTRACT unverändert. Keine neuen Ausschlüsse.
- Acht Preview-Isolationstests separat grün. Zusammen1.311 Tests. Ein zunächst gemeinsamer Aufruf verletzte die beabsichtigte Import-Isolation von Pax (webapp bereits importiert); anschließend korrekt separater Prozess, keine Teständerung.
- Bestehende Navigationsassertions gezielt auf `/tauschen` aktualisiert. S37 benutzte einen ungültigen `origin=trade_center` und fand bisher versehentlich den Bottom-Nav-Link: jetzt Prüfung des bereits bestehenden `origin=trades` mit `/trades?tab=requests`. Legacy-Origin-Vertrag und S07 bleiben unverändert.
- Browser Shell:375/390/430/1280px; exakt gleiche berechnete Kartenmaße und Face-Typografie wie echte `/album/vfl`-Wall; Touch/Maus/Enter, einzelne/alle Gruppen, Zusammenlegen, Reduced Motion, keine JS-Fehler, keine Schreibrequests, kein horizontaler Overflow einschließlich offenem Deal. Gesamte synthetische Browser-DB vor/nach Bytegleich.
- Layerzahlen1/2/5/6/10/15/37: Wall min(q,5), Trade min(q,10), ab10 keine weitere Layerzunahme. Unveränderte kanonische Preview-Paritätsgates ergänzen die Geometrieprüfung.
- TRADE-01–11-Regression und numerische Stack-Parität: alle grün, einschließlich28 numerischer Stackvergleiche; Nachweise in `preview-regression.json` und `preview-regression.txt`.
- Ein erster Preview-Lauf traf bei TRADE-06 auf einen Load-Timeout. Eigenen Testserver mit Request-Dateilog neu gestartet und gesamten Lauf wiederholt; keine Preview-/Testassertion geändert.
- Beide Git-Diffchecks sowie vollständiger Scope-/Secretcheck vor Commit durchgeführt; Ergebnis in `final-checks.json`.

## DB-Schutz und Testreproduktion

Alle15 geschützten lokalen DBs vor Beginn gegen vorhandenen Savepoint-Nachweis geprüft; SHA256 vor/nach identisch. Keine neue DB im Repository. Temporäre Test-DBs ausschließlich SQL-generiert unter `/private/tmp`, keine bestehende DB kopiert und keine privaten Nutzerdaten übernommen. Hashvergleich liest Dateien direkt, öffnet keine private SQLite-Verbindung. Private Pfade/Inhalte werden nicht in Browserartefakte übernommen.

Reproduktion in einem isolierten Sourceexport unter `/private/tmp`, ohne DB-/Backup-/Runtime-Dateien: `TMPDIR=/private/tmp`, Testabhängigkeiten aus requirements-test.txt sowie bestehendes Playwright/Chromium; `python -B -m Scripts.prepare_release_tests` erzeugt synthetische S00-/V20-Bestände ausschließlich dort. `python -B tests/research/artifacts/integration-01/run-release.py` führt den dokumentierten Release-Gate mit SQLite-Pfadguard aus. Danach `python -B -m unittest tests.test_pax_preview tests.test_trade_v2_preview` in separatem Prozess.

Für die unveränderten Browsergates isolierte App.trade_v2 auf127.0.0.1:18095 starten, dann `python -B tests/research/artifacts/integration-01/run-preview.py`. Für Shell: `python -B tests/research/check_integration01.py --serve --database /private/tmp/NEUER-EINDEUTIGER-NAME.db` (verweigert vorhandene DB); danach ohne `--serve` denselben Pfad prüfen. Serverport18081. Nur eigene Testserver;8095 bleibt unberührt. Alle hier dokumentierten Source-/Testläufe erfolgten in `/private/tmp/integration01-tests`.

## INTEGRATION-02

Separater Auftrag erforderlich für produktive Trade-v2-Persistenz/Contract-Type, beidseitige Settings-Eligibility, Request-/Reservations-/operative Slot-Commands, Lifecycle und Migration-/Rolloutkonzept. Die Shell liefert noch keine vollständige TRADE-10-Lifecycleprojektion. Layoutpolitur/Filter bleiben nachgelagert. Kein Start von INTEGRATION-02 mit diesem Commit.

## Vollständiger Änderungsscope

- `App/static/trade_shell.css`
- `App/static/trade_shell.js`
- `App/templates/trade_shell.html`
- `App/trade_shell.py`
- `App/webapp.py`
- `docs/TRADE_V2_INTEGRATION_01_AUDIT.md`
- `tests/research/artifacts/integration-01/active-1280.png`
- `tests/research/artifacts/integration-01/active-375.png`
- `tests/research/artifacts/integration-01/active-390.png`
- `tests/research/artifacts/integration-01/active-430.png`
- `tests/research/artifacts/integration-01/browser-checks.json`
- `tests/research/artifacts/integration-01/db-protection.json`
- `tests/research/artifacts/integration-01/deal-open-1280.png`
- `tests/research/artifacts/integration-01/deal-open-375.png`
- `tests/research/artifacts/integration-01/deal-open-390.png`
- `tests/research/artifacts/integration-01/deal-open-430.png`
- `tests/research/artifacts/integration-01/home-1280.png`
- `tests/research/artifacts/integration-01/home-375.png`
- `tests/research/artifacts/integration-01/home-390.png`
- `tests/research/artifacts/integration-01/home-430.png`
- `tests/research/artifacts/integration-01/preview-unit-tests.txt`
- `tests/research/artifacts/integration-01/release-tests.json`
- `tests/research/artifacts/integration-01/run-preview.py`
- `tests/research/artifacts/integration-01/run-release.py`
- `tests/research/check_integration01.py`
- `tests/test_integration01_trade_shell.py`
- `tests/test_s05_three_area_navigation.py`
- `tests/test_s31_ui_foundation.py`
- `tests/test_s37_beta_polish.py`
- `tests/test_uif001_collection_golden_screen.py`
- `tests/test_uif002_global_app_shell.py`
- `tests/test_uif005b_trade_detail_product_integration.py`
- `tests/test_uif_current_state_product_integration.py`
- `tests/research/artifacts/integration-01/preview-regression.json`
- `tests/research/artifacts/integration-01/preview-regression.txt`
- `tests/research/artifacts/integration-01/final-checks.json`
