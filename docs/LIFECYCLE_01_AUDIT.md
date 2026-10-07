# LIFECYCLE-01 — Persistenz-/Contract-Fundament, Audit

## Ergebnis und dokumentierter zwischenzeitlicher STOP

**Abschlussfreigabe am 07.10.2026 erteilt; Integritätskonflikt durch dokumentierte User-Freigabe aufgelöst.** Der folgende Absatz beschreibt den damaligen STOP, nicht den aktuellen Freigabestand. Die Implementierung und die unten genannten Tests sind vorhanden. Der abschließende Integritätscheck meldete eine Änderung der geschützten `App/Database/sammlr.db`. Gemäß Auftrag §15 wurde vor Staging/Commit/Push gestoppt. Keine automatische Wiederherstellung, keine Neubaseline und keine weitere Implementierung nach diesem Befund. LIFECYCLE-02 wurde nicht begonnen. Kein Deploy.

Ausgangs- und weiterhin aktueller HEAD: `83437f3af9521555eb6a14b0ac11668e1bd3c233`, Branch `feature/wm-special-trophies`, Upstream `origin/feature/wm-special-trophies`. Zu Beginn getrackter Arbeitsbaum sauber, Index leer, alle 16 DB-Hashes mit vorigem Savepoint übereinstimmend. Index weiterhin leer.

## Migration und Vertragsgrenze

0022 ist Teil des bereits versionierten Trade-v2-Präferenzfeatures. Alle bisherigen Migrationen 0001–0022 bleiben bytegleich; keine Historie umgeschrieben. Neue additive Migration: `0023_trade_lifecycle_foundation`, Up/Down. Keine Anwendung durch diesen Arbeitsablauf auf eine geschützte DB; Migrationstests ausschließlich synthetisch.

Gewählter Contract-Type: `trade_lifecycle_v1`. `lifecycle_contracts` erweitert die gemeinsame `trades.id`; neue Trades besitzen keine `legacy_trade_request_id`. Damit muss der historische CHECK in 0021 nicht umgeschrieben und kein Altvertrag umklassifiziert werden. Ein neuer Contract kann nicht an einen vorhandenen Legacy-Request gehängt werden. Teilnehmer, Herkunft und Vertragsidentität bleiben unveränderlich. `trade_contract_type` und `require_trade_operation` kapseln die Zuordnung. Der neue Typ erlaubt derzeit nur interne Foundation-Primitiven, keine produktiven Lifecycle-Operationen.

## Persistenzmodell

- `lifecycle_contracts`: stabile Tradeidentität, Contract, Herkunft, minimaler globaler Zustand, je ein Zeiger auf aktuelle und angenommene Revision.
- `lifecycle_revisions` / `lifecycle_revision_positions`: monotone Revision, Urheber, Art, Zeitpunkt und ganzzahlige gerichtete Mengen. Nach vollständiger beidseitiger Erstellung versiegelt; Payload unveränderlich. Höchstens ein Original/ein Counter. Aktuelle Wirksamkeit über Zeiger, historische Zustimmung bleibt erhalten.
- `lifecycle_rule_snapshots` / `lifecycle_consents`: expliziter versionierter Regelpayload, Annahmezeit und Zustimmung beider Teilnehmer. Angenommener Zeiger benötigt versiegelte eigene Revision, Snapshot und zwei Zustimmungen; spätere Änderung nur vorwärts zu einer Reduktion.
- `lifecycle_need_targets`: autoritative Zielmenge je Nutzer/Album/Code, fehlender Eintrag entspricht dem bisherigen Einzelkopieziel. Keine Settings-UI.
- `lifecycle_need_claims`: Menge, Revisionseigentum, pending/committed/released und bereits erhaltene Menge. Keine binäre Semantik und keine Fremd-Supply-Reservierung.
- `lifecycle_directions`: zwei unabhängige physische Richtungen mit getrennten Vorbereitungs-, Versand- und Empfangsfeldern, ohne deren Workflows.
- `lifecycle_commands`: eindeutige Commandidentität, Payload-Digest und gespeichertes Ergebnis. Unterschiedlicher Payload bei gleicher Identität wird abgewiesen.
- `lifecycle_movements`: Mengen-/Ereignisidentität für spätere gemeinsame Ship-/Receipt-Buchungen. Noch kein Bestandsbuchungsservice.
- `lifecycle_supply_bindings`: Zuordnung unveränderlicher Revisionspositionen zur gemeinsamen physischen Reservation, mit genau einem aktuellen Bezug pro Reservation.

Physische Give-Holds liegen weiterhin in `trade_reservations`, Materialisierung in `trade_positions`. Alte Inventory-/Reservation-Leser sehen sie ohne zweiten Bestandstopf. Diese gemeinsamen Zeilen sind die aktuelle physische Projektion; die genaue Historie liegt in den unveränderlichen neuen Revisionen. Nach expliziter Freigabe kann eine neue Revision dieselbe physische Projektion erneut binden; der alte Revisionsbezug bleibt erhalten und ein verspäteter alter Release greift nicht auf den neuen Bezug zu. Aktive Mengen werden nicht still umgeschrieben.

## Rule-Snapshot und Verfügbarkeit

`RuleSnapshot` enthält Schema-/Regelversion, Angebotserstellerperspektive, Partner, Herkunft, Gleichheits-/Ungleichheitsmodus und explizite bilaterale Pool-/Cross-Regeln je beteiligtem Album. Keine kompletten Nutzerobjekte, Kontakte oder Inventarsnapshots. Balancegruppen werden mit dem vorhandenen `trade_v2_rules` berechnet. Gegenangebote behalten ihre eigene Angebotserstellerperspektive; Reduktionen müssen den angenommenen Regelrahmen erhalten. Spätere globale Präferenzänderungen verändern gespeicherte Snapshots nicht.

`TradeV2Domain.lifecycle_availability` ist ein expliziter neuer Foundation-Lesezugang. Supply stammt aus `InventoryReadService`; Need aus Zielmenge minus physischem Bestand minus alten/neuen verbindlichen Resteingängen minus eigenen offenen Mengenclaims. Bedarf 2 / Claim 1 lässt Bedarf 1. Alte Incoming-Bindungen werden über den bestehenden Planning-Adapter gelesen, ohne rückwirkende neue Claim-Zeilen.

Interne `bind_pending_quantities`-/`release_pending_quantities`-Primitiven komponieren Give und Need in derselben Transaktion. Sie sind **keine** freigegebenen Send-/Accept-Services und werden von keiner produktiven Route aufgerufen. Bestehende `market`-/SAP-/Legacy-Flows werden nicht auf die neue Need-Politik umgestellt. Vor produktiver Erstellung muss L02 die aktuelle Domainvalidierung, Quoten, Fristen, Authentisierung und vollständige neue Readerintegration ergänzen.

## Atomicity, Constraints und Legacy

Schreibende Primitiven benötigen eine explizite `BEGIN IMMEDIATE`-Unit-of-work mit aktivierten Foreign Keys; verschachtelte fremde Transaktionen werden abgewiesen. Fehler rollen die gesamte Unit zurück. Positive ganzzahlige Positions-/Claim-/Bewegungsmengen, Ownership-FKs/-Trigger, eindeutige Revisionen/Counter/Heads und Command-/Movementidentitäten schützen das Fundament. `INSERT OR REPLACE` darf unveränderliche Historien nicht über SQLite-Nebeneffekte ersetzen. Zwei-Verbindungs-Tests decken Konkurrenz um letzte physische Kopie und letzte Need-Menge ab.

Rollback 0023 ist nur bei leeren neuen Strukturen erlaubt; mit Daten wird er atomar abgewiesen, statt neue Verträge oder Zielmengen zu löschen. Migrationsfehler rollen DDL und Ledger zurück. Altverträge werden weder umgetypt noch mit neuen Claims/Fristen versehen. Ein bestehender Legacy-Accept respektiert neue gemeinsame Give-Holds; alte eingehende Zusagen reduzieren den neuen Bedarf, ohne globale Legacy-Need-Exklusivität einzuführen.

## Tests

- **31 fokussierte Foundation-Tests bestanden.** Frische Basisschema-DB bis 23, Upgrade 22→23, wiederholter Check, leerer Rollback/Reapply, verweigerter destruktiver Rollback und injizierter Migrationsfehler; Vertrags-/Ownershipschutz; Revisionen/Replace-Schutz; Snapshot-Roundtrip/Gegenangebotsperspektive; mengenbasierte Claims/Freigabe; keine Partnersupply-Bindung; Legacy-Interop; Rebinding-Historie; Idempotenz; parallele Need-/Supply-Konkurrenz.
- **1.384 Release-Tests bestanden**, 0 Fehler, 0 Failures, 0 Skips. 1.396 entdeckt, dieselben **12 bestehenden** historischen/Baseline-Ausschlüsse. Neue Foundation-Tests darin enthalten, nicht zusätzlich zur Gesamtzahl addieren.
- **8 separate Pax-/Trade-v2-Preview-Tests bestanden.** Keine Browser- oder visuelle Regression als neu ausgeführt behauptet; UI/Preview-Assets unverändert.
- Bestehende relevante Domain-, Inventory-, Reservation-, SmartDeal-, SAP- und Trade-Tests sind in der Release-Suite enthalten.
- 17 bestehende Testdateien wurden ausschließlich an den neuen neuesten Schema-Stand 23 angepasst (bei S38 zusätzlich passender Kommentar). Assertions für ausdrücklich ältere Zielversionen und Bootstrap V20 unverändert. Keine Tests entfernt oder neu ausgeschlossen.
- Entwicklungszwischenläufe korrigierten synthetische Fixture-Initialisierung (Inventory-Constraints/FK-Pragma/Code-Strings) sowie fest codierte Latest-Version-Erwartungen. Die obigen Zahlen stammen aus grünen Läufen nach den Korrekturen.

Evidenz ausschließlich unter `/private/tmp/lifecycle01/`: `release.log`, `release-results.json`, `preview.log`, `current-candidate`, `tracked.json`, `db.json`, `db-deviation.json`. Tatsächliche Release-Läufe verwenden frische SQL-generierte synthetische DBs in den dortigen Kandidaten. Ein Python-Auditguard verhindert SQLite-Verbindungen außerhalb `/private/tmp` (außer reinem In-Memory). Ein erster Vorbereitungslauf brach vor Tests ab, weil der kopierte Gitbestand bereits das versionierte synthetische S00-DB-Fixture enthielt; die folgenden Kandidaten wurden ohne DB-Dateien kopiert und aus SQL aufgebaut. Keine reale Entwicklungsdatenbank wurde als Testquelle verwendet.

## Geschützte DB-Abweichung / Ursachenanalyse

**15 von 16 DBs bytegleich; die aktive lokale DB weicht ab.**

- Datei: `App/Database/sammlr.db`
- SHA256 vorher: `4b706e02c57d01b64bf311f6bdef25800fe27c38848f939c4176dbde45a54d24`
- SHA256 nachher: `c317d3ee7418f9caeaf655e9ed13c04ccdd88f1b8599652b42d56b1163905771`
- Dateigröße nachher: 905216 Bytes
- Dateisystem-mtime: `2026-10-06T18:25:06.522344` (lokale Systemzeit)

Die Baseline wurde vor Implementierung erfasst. Beim Befund gab es keine `sammlr.db-wal`-/`-shm`-Dateien und `lsof` zeigte keinen gerade offenen Zugriff auf diese Datei. Das beweist nicht, welcher Prozess früher geschrieben hat.

Die neuen fokussierten Tests verbinden sich ausschließlich mit ihrer expliziten temporären DB unter `/private/tmp`; die Release-Suite lief zusätzlich unter dem SQLite-Auditguard. Neue Foundation-Services erhalten eine Connection injiziert und öffnen keine DB selbst. Es wurde nach dem Befund kein privater DB-Inhalt abgefragt und keine Rücksetzung vorgenommen. **Die verursachende Aktion ist mit der verfügbaren Hash-/Dateimetadaten-Evidenz nicht eindeutig nachweisbar.** Eine externe Änderung wird nicht als bewiesen behauptet; ein grüner Testlauf ersetzt den fehlgeschlagenen Integritätsnachweis nicht. Daher STOP, keine Commit-/Pushfreigabe aus diesem Audit.

## Exakter Dateiumfang

Geänderte bisher versionierte Dateien:

- `App/services/trade_contracts.py`
- `App/services/trade_v2_domain.py`
- `tests/test_cb008_notification_catalog.py`
- `tests/test_cb009_inbox_read_retention.py`
- `tests/test_cb011_executable_match_contract.py`
- `tests/test_cb012_feed_home_cutover.py`
- `tests/test_cb013_collection_completion_projection.py`
- `tests/test_cb014_profile_account_projection.py`
- `tests/test_cb015_statistics_projection.py`
- `tests/test_cb016_legacy_cutover.py`
- `tests/test_s26_collector_profiles.py`
- `tests/test_s27_album_privacy_trade_pool.py`
- `tests/test_s28_trade_ratings.py`
- `tests/test_s29_friendships_community.py`
- `tests/test_s31_ui_foundation.py`
- `tests/test_s32_auth_session_csrf.py`
- `tests/test_s33_http_integrity_hardening.py`
- `tests/test_s35_account_lifecycle_privacy_performance.py`
- `tests/test_s38_release_candidate.py`

Neue Dateien:

- `App/Database/migrations/0023_trade_lifecycle_foundation.up.sql`
- `App/Database/migrations/0023_trade_lifecycle_foundation.down.sql`
- `App/services/trade_lifecycle_foundation.py`
- `tests/test_lifecycle01_foundation.py`
- `docs/LIFECYCLE_01_AUDIT.md`

Die sieben geschlossenen Fachvertragsdokumente wurden nicht verändert. Alle bisherigen SQL-Migrationen unverändert. Keine produktive Route, UI, Domainregel des Altvertrags oder automatische Migration angepasst. Zusätzlich zu diesem Code-/Dokumentumfang liegt die oben ausgewiesene unerwartete, ungetrackte DB-Inhaltsabweichung vor; sie wird ausdrücklich nicht als beauftragte Änderung legitimiert.

## Verbleibende Grenzen / Git

Der damalige DB-Integritätsblocker ist durch die unten dokumentierte explizite Freigabe aufgelöst. Die technischen Abnahmekriterien sind geprüft. Persistenzprimitiven sind noch kein ausführbarer Lifecycle: keine produktive Send-/Accept-/Counter-/Pack-/Foto-/Adress-/Versand-/Empfangs-/Rating-Journey, keine reale V1-Erstellung. Bewegungsledger und Commandidentitäten ermöglichen spätere exactly-once-Transaktionen, führen jetzt selbst keine Bestandsbuchung aus. Spätere fachliche/Datenschutz-/Launch-Gates gelten weiterhin.

Historischer Stand beim STOP: kein L01-Commit oder Push, HEAD auf dem Dokumentationssavepoint, Index leer, Source-/Teständerungen unstaged und fünf neue Dateien ungetrackt. Beide Git-Diffchecks ohne Befund. Bestehende sonstige ungetrackte Dateien nicht aufgenommen. Kein Deploy. LIFECYCLE-02 nicht begonnen.

## Autorisierte Baseline und finaler Abschluss — 07.10.2026

Der Nutzer hat die manuelle Profil-/Browseränderung ausdrücklich als eigene Änderung akzeptiert und nach lesender Ursachenprüfung die neue Baseline freigegeben. Betroffen war `user_profile_stickers` für User-ID 1: neues Portrait mit 640×480 statt 788×1400, Zuschnitt X/Y −1/13 statt 35/11, Zoom 1,0 statt 1,93. Datenbankzeitpunkt und Bilddatei-Anlage stimmen am 06.10.2026 um 18:25:06 Berliner Zeit überein; vorhandener Profilsticker-Uploadpfad. Die Vergleichssicherung liegt vor dem früher autorisierten Passwortreset; diese Nachweisgrenze wurde ausdrücklich akzeptiert. Schema/Migrationshistorie der realen DB weiterhin Version 20, keine neuen Lifecycle-Strukturen oder Testdaten.

Neue autorisierte SHA256-Baseline für `App/Database/sammlr.db`:
`c317d3ee7418f9caeaf655e9ed13c04ccdd88f1b8599652b42d56b1163905771`.

Die anderen 15 Baselines bleiben unverändert. Finaler Baselinesatz außerhalb des Repositories: `/private/tmp/lifecycle01/db-authorized-final.json`. Alle 16 Dateien gegen diese Baselines geprüft. Die aktive DB ist nicht getrackt; weder sie noch Portraitdateien oder andere private Runtime-Dateien gehören zum Commit.

Finaler Scope: die oben einzeln aufgeführten **24 Dateien**. Alle 23 Source-/Test-/Migrationsdateien sind bytegleich mit dem isolierten Kandidaten des grünen 1.384-Test-Laufs. Seitdem nur dieses Audit fortgeschrieben. Die 31 fokussierten Tests werden im Abschluss nochmals bestätigt; 8 getrennte Preview-Tests grün. Keine vollständige Regression ohne Codeänderung wiederholt. 12 bisherige Ausschlüsse unverändert. Bestehende Migrationen und die sieben Fachvertragsdokumente unverändert. Beide Diffchecks sauber; Index vor gezieltem Staging leer. Keine weitere unerklärte geschützte DB-Abweichung erlaubt.

Freigegebener Commit: `feat: add trade lifecycle v1 foundation`, nur die 24 L01-Dateien. Normaler Push auf `origin/feature/wm-special-trophies`; keine DB-/Profiländerung aufgenommen, kein Force-Push/Branchwechsel/Rebase/Merge. Commitumfang, DB-Hashes und lokaler/Remote-HEAD werden abschließend verifiziert; der konkrete Commit-Hash steht im Abschlussbericht, damit kein selbstreferenzieller zweiter Auditcommit erforderlich ist. Kein Deploy, LIFECYCLE-02 nicht begonnen.
