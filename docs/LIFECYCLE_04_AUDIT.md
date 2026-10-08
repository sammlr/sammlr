# LIFECYCLE-04 — Vorbereitung, Kontrollfotos und Deal-Reduktion

Stand: 2026-10-08. Ausgangscommit `590aa2c7ed6d440c7693cef7993f054d245ae422`. Branch `feature/wm-special-trophies`, Upstream `origin/feature/wm-special-trophies`, Remote `https://github.com/sammlr/sammlr.git`.

## Ausgang und DB-Schutz

Vor Implementierung: HEAD/Branch/Upstream geprüft; Index leer und getrackter Arbeitsbaum sauber. Die bestehende ungetrackte Audit-Datei dieses Auftrags wird fortgeführt; andere vorhandene ungetrackte/ignorierte Dateien bleiben unberührt. Alle 16 geschützten DBs entsprechen vor und nach den Prüfungen der autorisierten L03-Baseline. Keine davon wurde geöffnet, kopiert, migriert, repariert oder als Testdatenquelle verwendet. Dateihashes wurden ausschließlich gelesen.

## Foundation-Audit und Architektur

L01 stellt versiegelte immutable Revisionen, eingefrorene `RuleSnapshot`s, Consents, Richtungen, mengenbasierte Need-Claims, gemeinsame Supply-Bindings und die `BEGIN IMMEDIATE`-Schreibgrenze bereit. L03 speichert Acceptance und deren Zeitpunkt unveränderlich. `LifecyclePreparation` erweitert den vorhandenen Service und verwendet dessen Auth-/Contract-Guards, Commandidentitäten und Foundation-Transaktionen; keine zweite Lifecycle- oder Matchingengine.

Geprüft wurden außerdem `trade_events`, produktive Anfrage-/Acceptance-UI, gemeinsame InventoryRead-/Write-/Reservation-Adapter, SmartDealPlanning, TradeV2Domain, globale CSRF-/Session-Guards und der vorhandene Profile-Sticker-Upload. JPEG-/PNG-Sanitizer werden wiederverwendet, aber Fotos werden in einem getrennten privaten Storage und über eine eigene autorisierte Resource ausgeliefert. Keine alte Preview-Zustandsmaschine wird zur Produktivdomain gemacht.

## D06 — ausdrücklich entschieden und implementiert

Der ursprüngliche STOP betraf den im Fachvertrag ausdrücklich vor L04 offenen Phantom-Supply-Fall. Der Nutzer hat anschließend separate mengenbasierte `physical_missing_hold`-Semantik freigegeben. Diese Entscheidung ersetzt den D06-STOP dieses Audits:

- Verbindliche Besitzermeldung einer konkreten aktuellen reservierten Give-Menge erzeugt einen Hold mit User/Album/Code, ursprünglicher Revisionsposition, Reservation, Menge und Zeitpunkt.
- Ein Hold ist keine codeweite Sperre. Die Declaration benennt die gesamte bekannte Fehlmenge dieser Revisionsposition; wiederholte gleiche Meldung erzeugt keine zweite Menge. Eine höhere Gesamterklärung ergänzt nur das Delta. Kleinerwerden erfordert die explizite Auflösung.
- Die bestehende Trade-Reservation bleibt bestehen. Die Überschneidung wird explizit als `overlap_quantity` geführt. Verfügbarkeit: `max(stored - assigned - active reservations - SUM(missing quantity - still active overlap), 0)`. Dadurch wird dieselbe physische Menge nicht doppelt gesperrt; ein fremder Hold erhält keine ungerechtfertigte Gutschrift.
- SAP-/Inventory-Snapshots, Matching-/Markt-Batchleser, Collection-Summaries, SmartDeal-/manuelle Dealbildung und InventoryGuard berücksichtigen die Quarantäne. Zusätzliche SQL-Guards verhindern neue Reservationen/Reaktivierung aus gesperrter Supply. Credits für die eigene Revision ziehen deren fehlende Teilmenge ab.
- Bei bestätigter Reduktion entfällt der entfernte Trade-Hold, die Fehlmengen-Sperre bleibt. Eine reduzierte bindende Give-Menge darf keine weiterhin als fehlend deklarierte reservierte Menge enthalten. Beispiel 23→22: Missing 1 bleibt gesperrt, Gegenmenge wird regulär frei.
- Ablehnung verändert weder den alten Vertrag noch den Missing-Hold. Weder Zeit noch Trade-Ende noch Reduktion lösen ihn automatisch auf.
- `resolve_missing(..., resolution='found')`: expliziter Besitzerbefehl, Hold auflösen, gespeicherte Quantity unverändert.
- `resolution='corrected'`: Quantity über den bestehenden InventoryWrite-/Guard-Pfad reduzieren und Hold in derselben Transaktion auflösen. Verbleibende bindende Reservations dürfen nicht unterlaufen werden; nötigenfalls zuerst die bilaterale Reduktion. Fehler rollt beides zurück.
- Domain-Auflösung funktioniert auch nach Ende des ursprünglichen Trades. Es gibt keine neue große Bestandskorrektur-UI; eine explizite UI-Anbindung bleibt Folgepunkt. Normale Bestandsbearbeitung hebt Holds nicht still auf.

## Migration 0026

Neue additive `0026_trade_lifecycle_preparation` für Preparation-Zyklen, private Foto-Metadaten, strukturierte Fotoprobleme, Reduktionsvorschläge und Missing-Holds. Ownership-/Mengenconstraints, eindeutige aktuelle Zyklen, eindeutiges offenes Amendment sowie Missing-Hold-/Reservation-Guards sichern die neue Persistenz. Bestehende Foundation-Tabellen werden nicht neu gebaut; 0022/0023/0024/0025 bleiben unverändert.

Die 0026-Migration wurde ausschließlich synthetisch getestet: Upgrade mit vorhandener Acceptance, leeres Down/Up, verweigerter Downgrade bei operativen Daten, FK-/Integritätscheck. Produktive neue Pfade sind auf Vorhandensein des Schemas gegated. Die reale Migrationsfreigabe steht weiterhin aus.

## Preparation, Fristen und Packlisten

Jede Richtung erhält einen eigenen aktuellen Zyklus zur bindenden Revision. Die Packliste stammt ausschließlich aus dieser Revision, mit Albumname, Code und Menge; keine SAP-Neuberechnung. Cycles werden beim ersten autorisierten Zugriff angelegt, die Frist wird dennoch immer aus der ursprünglichen persistierten Acceptance abgeleitet: **accepted_at + exakt 72 Stunden**. Die Anzeige verwendet Berliner Zeit samt Zeitzone. Öffnen, Upload, Retry, Korrektur oder Reduktion starten keine neue Frist.

Abschluss erfordert mindestens ein aktuelles eigenes Foto, keine offene Reduktion und keine ungeklärte fehlende Give-Menge. Completion fixiert Paket und Zeitpunkt. Danach sind stille Uploads/Entfernungen verboten. Mengen werden beim Packen nicht aus dem Inventar gebucht.

Die Deadlinefrage war bereits durch State-Machine T21 entschieden: OVERDUE + dedupliziertes `PackingOverdue`-Audit pro Zyklus; keine automatische Cancellation, Sanktion, Bewertung oder Mengenfreigabe. Verspätete Vorbereitung bleibt kontrolliert abschließbar. Rechtzeitig abgeschlossene Vorbereitung wird nicht wegen langsamer Gegenprüfung überfällig. Keine harte Reviewfrist, kein Reminder-/Push-System.

## Fotos, Reveal, Review und Korrektur

Mehrere sequenzielle Uploads aus Kamera bzw. Galerie/Dateiauswahl sind möglich, ohne Ein-Foto-Limit. JPEG/PNG, maximal 12 MB je Datei und begrenzte Bildabmessungen; Metadaten werden über vorhandene Sanitizer entfernt. Die bestehende globale 1-MB-Requestgrenze bleibt für alle anderen Endpoints unverändert; nur der dedizierte Upload bekommt eine lokale Requestgrenze von 12 MB plus Multipart-Overhead vor dem CSRF-Parsing.

Private Dateien liegen standardmäßig unter `App/uploads/lifecycle_control` (bereits ignorierter Runtime-Bereich); Konfiguration `LIFECYCLE_PHOTO_DIR`. Zufällige Storage-Namen, SHA256-Digest und Metadaten referenzieren Trade über Zyklus, Revision, Besitzer und Zeit. Dateischreiben und Metadatenfinalisierung werden innerhalb des serialisierten Commands durchgeführt; bei DB-Fehler wird nur die gerade neu erzeugte Datei entfernt, Retry erzeugt keine neue Datei. Ein Prozessabbruch zwischen Dateiablage und Commit kann eine unreferenzierte private Datei hinterlassen; es entsteht dadurch keine lesbare öffentliche Ressource.

Fotozugriff prüft serverseitig aktiven Teilnehmer, konkreten Trade, aktuelle bindende Revision, aktuellen Zyklus und Reveal. Eigene Drafts sind sichtbar, fremde Fotos vor beidseitiger Completion nicht. Zweite Completion setzt den Reveal für beide Pakete atomar. Ressourcen werden mit `private, no-store`, `nosniff`, ohne ETag/Conditional-Reuse und mit restriktiver CSP ausgeliefert. Es existiert kein öffentlicher Storage-Handler.

Nach Reveal prüft jeder ausschließlich das Gegenpaket: „Alles passt“ oder `MISSING_STICKER`, `WRONG_STICKER`, `CONDITION_PROBLEM`, `NOT_RECOGNIZABLE`. Domainseitig sind betroffene Position/Menge optional präzise validierbar. Kein Chat/Rating und keine automatische Bildanalyse.

Eine explizite Fotokorrektur ersetzt nur den eigenen aktuellen Zyklus. Das Review genau dieses Pakets wird neu erforderlich; das unveränderte andere Paket kann seine gültige Freigabe behalten. Neue Fotos bleiben bis erneuter eigener Completion verborgen. Bereits gesehene fremde Information wird nicht als ungesehen behandelt. Alte Paket-URLs sind nach Ablösung nicht mehr abrufbar. Eine verbindliche Fehlmengenmeldung nach Completion entwertet ebenfalls den eigenen abgeschlossenen Zyklus, statt einen Ready-Zustand weiterzutragen.

## Reduktion und eingefrorener Regelrahmen

Der Vorschlag enthält ausdrücklich ausgewählte Restmengen beider Richtungen. Kein Optimizer, kein zufälliges Gegenstück, keine neuen Codes/Alben oder größere Mengen. Beide Richtungen bleiben nichtleer. Validierung erfolgt mit dem bei Acceptance eingefrorenen `RuleSnapshot` einschließlich ursprünglicher Erstellerperspektive, SAME-/Cross-Gruppen und Equal-/Receive≤Give-Modus; spätere globale Pool-/Cross-Einstellungen ändern ihn nicht.

Vorschlag erzeugt eine neue versiegelte Reduction-Revision samt Zustimmung des Vorschlagenden; alte Vertragsbasis und Bindungen bleiben maßgeblich. Nur die Gegenseite darf den konkreten aktuellen Vorschlag annehmen oder ablehnen. Bei Annahme unter derselben Schreibsperre: aktuelle Basis, physische Sicherheit, exakte aktive Holds/Claims und Fehlmengen prüfen; unveränderten Regelrahmen an die neue Revision binden, zweite Zustimmung speichern und Root atomar weiterschalten.

Unveränderte Give-Reservationen behalten ID und aktive Menge, erhalten nur die neue Revisionszuordnung. Verringerte Projektionen werden innerhalb derselben Transaktion freigegeben und mit der kleineren Menge an dieselbe Hold-ID gebunden; außen ist keine Freigabelücke sichtbar. Alte Need-Claims bleiben als released Audit erhalten, neue Claims entsprechen exakt der neuen Revision. Entfernte Need-/Give-Mengen sind nach Commit unmittelbar frei, Missing-Holds ausgenommen. Die gemeinsame Inventoryquelle bleibt erhalten.

Nach Aktivierung werden konservativ beide Preparation-/Foto-/Reviewbasen für die neue Revision neu erforderlich. Die alte Revision, Snapshot und Historie bleiben unverändert. Ablehnung schaltet keine Revision um, storniert nichts und bleibt als offener Problemzustand für diese Vertragsbasis sichtbar; sie führt nicht still zurück zur Adressbereitschaft. Eine neue zulässige Reduktion ist möglich. Keine Cancellation-Semantik erfunden.

## Ready-Grenze, UI und Events

`ready_for_address_release` ist eine eindeutig abgeleitete Domainprojektion: aktuelle Bindung, zwei vollständige aktuelle Pakete, Reveal, beide gültigen Reviews und keine offene/rejektierte ungeklärte Reduktion, kein Fotoproblem oder aktiver überlappender Missing-Hold. Keine Adresse wird ausgewählt, gespeichert, geladen, angezeigt oder API-seitig ausgeliefert. Shipping-/Receipt-Zustände bleiben unverändert.

Produktiver Einstieg: `/tauschen/vorbereitung/<trade_id>`, verlinkt aus Anfrage und laufenden Tauschen nach Acceptance. Eigene Packliste, Deadline/Überfälligkeit, Foto-Drafts, wartender/revealed Zustand, strukturierte Probleme, Correction, verbindliche Missing-Meldung und konkrete Mengenreduktionsansicht. Nach einer Reduktion zeigt auch die bisherige Anfrageübersicht die aktuell bindenden Mengen und bleibt erreichbar.

Vorhandene `trade_events` speichert u.a. PreparationConfirmed, BothPackagesVisible, PhotoConfirmed, PhotoProblemReported, ControlPackageRevised, AmendmentProposed/Accepted/Rejected, PhysicalMissingDeclared/Resolved und PackingOverdue mit Revision und relevanter Basis. Kein Foto-/Adressinhalt in Events; keine neue Push-Infrastruktur.

## Idempotenz, Konkurrenz und Legacy

Commands verwenden bestehende Actor/Trade/Key/Operation/Payload-Digests. Upload, Complete, Approve, Problem, Correction, Reduction und Missing-Auflösung sind retry-sicher; eine wiederverwendete Identität mit anderem Payload wird abgewiesen. Aktuelle Vertragsrevision und beide Cycle-IDs schützen gegen alte Browserseiten. Alle schreibenden Übergänge nutzen `BEGIN IMMEDIATE` und rollbacken atomar.

Geprüfte Rennen: beide Complete, Complete/Upload, Complete/Reduction-Proposal, Approve/Problem, beide Reviews, Reduction-Approve/Reject, Reduction-Approve/InventoryWrite, Correction-Upload/altes Review. Ungültige alte Basis gewinnt nie durch spätere Ausführung. Physische Bewegung sperrt normale Änderungen.

Legacy-Verträge werden nicht migriert und bekommen keine Preparation-/Foto-/Reduktionszustände. D06 wirkt bewusst auf die gemeinsame verfügbare physische Supply, einschließlich alter Availability-Konsumenten; Legacy-Transitions, Fristen und bestehende Bindungen werden nicht umgedeutet. Ohne 0026 beziehungsweise ohne Missing-Holds bleiben bisherige Ergebnisse erhalten.

## Tests und Nachweise

Source-only Kandidaten unter `/private/tmp/lifecycle04/`; synthetische DBs aus SQL/Fixtures, nie Kopien privater DBs. Release- und Browserharness verweigern SQLite-Pfade außerhalb `/private/tmp` per Audit-Hook.

- **1.512 Release-Tests**, davon **45 neue L04-Tests** (38 Domain/Migration/Concurrency, sieben HTTP/UI). Null Fehler/Failures/Skips; **12 bestehende Ausschlüsse unverändert**.
- **Acht separate Preview-Tests** grün.
- Bestehende **900 binäre und 40 mengenbasierte Solververgleiche** Teil der unveränderten grünen Regression.
- Browser A: Packlisten → private Completion → Mutual Reveal → beidseitige Freigabe → ready, ohne Adresse.
- Browser B: nicht erkennbar → expliziter Correction-Zyklus → neue Fotos → notwendige neue Freigaben → ready.
- Browser C: 23↔23 → eigene Missing-Meldung → sichtbare 22↔22-Revision → bilaterale Aktivierung → 44 aktive Give-Mengen, Missing 1 bleibt gesperrt → neue Vorbereitung/Reviews → ready.
- Browser D: Reduktion abgelehnt → Original 46 Give-Mengen weiter gebunden, kein Cancel/Ready/Adresszugriff.
- Keine JS-Fehler; kein horizontaler Overflow bei 375/390/430/1280 px. Zwölf Screenshots und `browser/results.json` unter `/private/tmp/lifecycle04/`.

Entwicklungsfunde wurden behoben: ungültige synthetische PNG-CRC ersetzt; präziser Browser-Submit-Selektor; Latest-Migration-Assertions auf 26 aktualisiert; zusätzliche Schema-Queries in vorhandene SmartDeal-Ownerprüfung integriert (bestehender Query-Grenzwert nicht erhöht); private Uploadgrenze vor globalem CSRF-Parsing gezielt gesetzt und >1-MB-/Überlimit-Test ergänzt. Bestehende fachliche Assertions wurden nicht abgeschwächt.

Finale Nachweise: `release-results.json`, `release.log`, `preview.log`, `browser.log`, `browser/results.json`, `db-start.json`, `db-final.json`, `final-files.json` unter `/private/tmp/lifecycle04/`.

## Grenzen und Abschluss

Keine reale Migration; produktive lokale DB bleibt unverändert. Keine Bestandskorrektur-UI, keine nachträgliche Cancellation, keine Adresse, Versand, Receipt, Bewertung, Zentrale oder Push. Foto-Retention/physische Löschung und Behandlung verwaister Uploads sind Launch-/Privacy-Restpunkte; es wird keine neue automatische Löschfrist eingeführt. Foto-Metadaten besitzen eine explizite Entfernungsmarkierung, private Storage-Dateien sind gezielt löschbar. Kein öffentlicher Galeriezweck.

Commit nach finalen Gates: `feat: add lifecycle v1 trade preparation`. Nur unten genannte Dateien; keine Runtime-/DB-/Bilddateien im Commit. Der End-Commit ist der Commit, der dieses Audit hinzufügt; sein Hash und der unabhängige Remotevergleich stehen im Abschlussbericht. Kein Deploy. LIFECYCLE-05 nicht begonnen.

## Exakte Dateien
- `App/Database/migrations/0026_trade_lifecycle_preparation.down.sql`
- `App/Database/migrations/0026_trade_lifecycle_preparation.up.sql`
- `App/lifecycle_acceptance_routes.py`
- `App/lifecycle_preparation_routes.py`
- `App/services/inventory.py`
- `App/services/inventory_availability.py`
- `App/services/lifecycle_photos.py`
- `App/services/lifecycle_planning.py`
- `App/services/physical_missing.py`
- `App/services/smartdeal_planning.py`
- `App/services/trade_lifecycle_preparation.py`
- `App/services/trade_lifecycle_requests.py`
- `App/services/trade_reservations.py`
- `App/templates/lifecycle_preparation.html`
- `App/templates/lifecycle_requests.html`
- `App/templates/trade_shell.html`
- `App/trade_shell.py`
- `App/webapp.py`
- `docs/LIFECYCLE_04_AUDIT.md`
- `tests/research/check_lifecycle04.py`
- `tests/test_cb008_notification_catalog.py`
- `tests/test_cb009_inbox_read_retention.py`
- `tests/test_cb011_executable_match_contract.py`
- `tests/test_cb012_feed_home_cutover.py`
- `tests/test_cb013_collection_completion_projection.py`
- `tests/test_cb014_profile_account_projection.py`
- `tests/test_cb015_statistics_projection.py`
- `tests/test_cb016_legacy_cutover.py`
- `tests/test_lifecycle01_foundation.py`
- `tests/test_lifecycle04_preparation.py`
- `tests/test_lifecycle04_ui.py`
- `tests/test_s26_collector_profiles.py`
- `tests/test_s27_album_privacy_trade_pool.py`
- `tests/test_s28_trade_ratings.py`
- `tests/test_s29_friendships_community.py`
- `tests/test_s31_ui_foundation.py`
- `tests/test_s32_auth_session_csrf.py`
- `tests/test_s33_http_integrity_hardening.py`
- `tests/test_s35_account_lifecycle_privacy_performance.py`
- `tests/test_s38_release_candidate.py`

## DB-SHA256 vor/nach (identisch)

- `App/Database/sammlr_reference_s00.db`: `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`
- `App/Database/s20_coverage_debug.db`: `dadac1c379a45ec0245208293aef3eccd732cc41b3c07e4b8c523cace1444d9e`
- `App/Database/sammlr.db`: `c317d3ee7418f9caeaf655e9ed13c04ccdd88f1b8599652b42d56b1163905771`
- `App/Database/Database:Backups/collectr_backup_before_trophy_cleanup.db`: `447a9164ba7772b04ee12ccfc5c65a39720cf1f1776c86002ffe3161fded287e`
- `App/Database/Database:Backups/collectr_backup_popup_clean.db`: `6bcb037730123b78fe756856bc8735a7358f185872040d179fc34a5ebb1d51e3`
- `App/Database/Database:Backups/collectr_backup_before_users.db`: `f4796d18d36a6a0f1625bfc7eb2fb926006ef50d534472ca32a3cfbe0a4e8039`
- `App/Database/Database:Backups/collectr_backup_trophy_tabs_visual_runs.db`: `6bcb037730123b78fe756856bc8735a7358f185872040d179fc34a5ebb1d51e3`
- `App/Database/Database:Backups/collectr_backup_users_trophy_clean_runs.db`: `602883a8538f9377847542c1c7c969d326adc7d071c6cca2ff5822eca1b96f8f`
- `Backups/sammlr_local_pre_v0005_20260803_211622.db`: `cb69ff4407f6c9c166e84d472f8a89b32e33692cde109b437b1d60ebb0aa0a01`
- `Backups/sammlr_local_pre_v0003_20260802_091642.db`: `ff96c936c3a4fe86433f3cd42dfbc51e24a034a02c147ccc5e40aefdb436c5d8`
- `Backups/sammlr_before_valy_password_reset_20261004T084422847704Z.db`: `0748a936250c2771173a5bfb3853b7718c79e376fed25409438d0927062c5eb1`
- `Backups/collectr_2026-06-02_22-14-58.db`: `474f1bf0573717c1594a5cb6311d1f8ea99c461357715e1e43315f6c3285654c`
- `Backups/sammlr_local_pre_v0006_20260808_010509.db`: `159cc562b648ebf567878622b4db815cc2acf86601b9d2bc2a586793b8cd5912`
- `Backups/sammlr_local_pre_v0004_20260802_232331.db`: `2063fddc7991cd699dc5321f8210b1278ee8180a96dbaf0ab0a89a87aafcd466`
- `Backups/sammlr_local_pre_v0007_20260808_023853.db`: `752292434f44c637f7518c71494d5b7f787d786d881bca06024b8547c732eac8`
- `App/Database/collectr.db Kopie`: `f25e1b02975da4cda2dfc0e217fe30ae294030dbb9fc0b7a5b6d4b93318f5e4a`
