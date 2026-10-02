# Dokumentations-Inventur

## Umfang und Kategorien

Stand: 16. August 2026. Der aktuelle Checkout umfasst **150 projektbezogene `.md`- und `.txt`-Dateien** außerhalb von `.git/` und `.venv/`. Davon sind **141 Dokumentationsartefakte** und **9 Textdateien mit Daten-, Export-, Dependency- oder Reparaturinhalt**. Zusätzlich enthält `.venv/` fremde Markdown-/Textdateien installierter Pakete; sie gehören nicht zur Sammlr-Projektdokumentation und werden nicht einzeln klassifiziert.

Kategorien:

- **A – aktuelle Produktwahrheit**
- **B – Post-RC-Arbeitsdokumentation**
- **C – technische Dokumentation**
- **D – historische Dokumentation**
- **E – Audit/Report**
- **F – vermutlich veraltet**
- **G – Zweck unklar**

„Aktuell“ bezeichnet die vermutete heutige Pflegefunktion, nicht den Implementierungsstand. „Historisch“ bewahrt Planungs- oder Nachweisevidenz. Bei Konflikten wurde keine Datei eigenständig umgedeutet.

## Aktuelle Produktwahrheit und Markenregeln

| Pfad | Vermuteter Zweck | Kategorie | Status | Mögliche Überschneidungen |
| --- | --- | --- | --- | --- |
| `Dokumentation/Product Bible/README.md` | Einstieg und Regeln der langfristigen Product Bible | A | aktuell | Post-RC `source-of-truth.md`; alte Roadmap-Verweise |
| `Dokumentation/Product Bible/decisions/README.md` | Vorlage/Index für künftige Decision Records | A | aktuell, derzeit ohne Records | Produktentscheidungen stehen faktisch noch in Spezifikationen und Audits |
| `Dokumentation/Product Bible/specifications/README.md` | Index langfristiger Produktspezifikationen | A | aktuell | Product-Bible-README |
| `Dokumentation/Product Bible/specifications/collection.md` | Sammlung, Alben, Stickerverwaltung und Mehrfachalben | A | aktuell | Post-RC Audits Sammlung/Album; S04, S08–S12, S27 |
| `Dokumentation/Product Bible/specifications/home.md` | langfristige Regeln für Home | A | aktuell | Post-RC Audit sammlr.-Zentrale; S25 |
| `Dokumentation/Product Bible/specifications/navigation-information-architecture.md` | langfristige Navigation und Informationsarchitektur | A | aktuell | Post-RC UX Architecture; S05–S07 |
| `Dokumentation/Product Bible/specifications/profile-community.md` | Profil- und Communityregeln | A | aktuell | Home, Navigation, S26/S29 |
| `Dokumentation/Product Bible/specifications/trade-lifecycle.md` | Tradezentrale und Dealabwicklung | A | aktuell | Trading-Spezifikation; S13–S24 |
| `Dokumentation/Product Bible/specifications/trading.md` | Tauschen und Smart Trader | A | aktuell | Trade-Lifecycle; Sammlung; S19–S22 |
| `Branding/Corporate ID/Sammlr_Corporate_ID_V1.md` | vorläufige Markenidentität, Mission und visuelle Leitlinien | A | aktuell laut Product-Bible-Verweis, aber „vorläufig“ | Branding Design Bible; Product-Bible-Design; Post-RC Design System |
| `Branding/Design Bible/00 Source Assets/README.md` | Herkunft und Regeln eines Quellassets | C | aktuell | Master-Asset-README |
| `Branding/Design Bible/01 Master Assets/README.md` | Master-Asset-Regel und Assetzuordnung | A | aktuell | DB-001/DB-002; Runtime-Assetkopien |
| `Branding/Design Bible/02 Design Bible/DB-001_Master_Logo_VfL.md` | verbindlicher Master-Logo-Eintrag | A | aktuell | Master-Asset-README; App-Static-Kopie |
| `Branding/Design Bible/02 Design Bible/DB-002_Master_Album_Branding_VfL.md` | verbindlicher Album-Branding-Eintrag | A | aktuell | Master-Asset-README; App-Static-Kopie |

## Post-RC-Arbeitsdokumentation

| Pfad | Vermuteter Zweck | Kategorie | Status | Mögliche Überschneidungen |
| --- | --- | --- | --- | --- |
| `Dokumentation/Post-RC/README.md` | Wegweiser ohne eigene Produktentscheidungen | B | aktuell | keine; verweist auf zuständige Dateien |
| `Dokumentation/Post-RC/00-master-plan.md` | Prozess und Status RC1 → Closed Beta | B | aktuell | alte Development Roadmap und RC1-Releaseunterlagen |
| `Dokumentation/Post-RC/01-product-audit/01-login-registration.md` | Audit Login und Registrierung | B | aktuell | Security-/Auth-Unterlagen nur thematisch |
| `Dokumentation/Post-RC/01-product-audit/02-sammlr-zentrale.md` | Audit des bisherigen Home | B | aktuell | Product Bible `home.md`, S25; Begriffskonflikt Sammlr-Zentrale/Home |
| `Dokumentation/Post-RC/01-product-audit/03-sammlung.md` | Audit Sammlung | B | aktuell | Product Bible `collection.md`, S04 |
| `Dokumentation/Post-RC/01-product-audit/04-album.md` | Audit Album | B | aktuell | `collection.md`, S27, ältere UI-/Designunterlagen |
| `Dokumentation/Post-RC/01-product-audit/05-stickerliste.md` | Audit Stickerliste und physischer Offline-Tausch | B | aktuell | `collection.md`, S02; Abgrenzung zur Online-Fairnessregel |
| `Dokumentation/Post-RC/01-product-audit/06-tauschboerse.md` | Audit Tauschbörse, Matches und Anfragen | B | aktuell | `trading.md`, S19–S22; Smart-Trade-Priorisierung |
| `Dokumentation/Post-RC/01-product-audit/07-trade-lifecycle.md` | Audit laufender Trade und Bestandsbuchung | B | aktuell | `trade-lifecycle.md`, `collection.md`, S13–S18/S28 |
| `Dokumentation/Post-RC/01-product-audit/08-profil-community.md` | Audit Profilrollen, Sammleridentität und Community | B | aktuell | `profile-community.md`, S26–S29; Privacy- und Profilhierarchie-Konflikte |
| `Dokumentation/Post-RC/01-product-audit/09-sammlr-home-feed.md` | Audit der mittleren sammlr.-Home als chronologischer Sammler-Feed | B | aktuell | `home.md`, früheres Audit 02, S23–S25/S29; Aufgaben-/Feed-Konflikt |
| `Dokumentation/Post-RC/01-product-audit/10-notifications.md` | Audit der Glocke als kleine persönliche Inbox | B | aktuell | S23/S24, Audit 09, Trade-/Community-Events; Read-, Retention- und Typkatalog-Konflikte |
| `Dokumentation/Post-RC/01-product-audit/11-trophaeen.md` | Audit des albumbezogenen, dauerhaften und entdeckbaren Trophy-Systems | B | aktuell | Album, Profil, Feed, Notifications, globale/Legacy-Trophäen und dynamische Freischaltungsanzeige |
| `Dokumentation/Post-RC/01-product-audit/12-statistik.md` | Audit der historischen Sammlerkarriere und albumbezogenen Zustands-/Verlaufsstatistik | B | aktuell | Inventory, Trades, Albumzeitpunkte/-löschung, Profil, Privacy und gültige Album-Trophäen |
| `Dokumentation/Post-RC/01-product-audit/13-albumabschluss-vitrine.md` | Audit des erstmaligen historischen Albumabschlusses und des Bereichs „Abgeschlossene Alben“ | B | aktuell | Sammlung/Vitrine, Profil, Statistik, Trophy, Feed, Privacy, Löschung und Mehrfachexemplare |
| `Dokumentation/Post-RC/02-cross-audit/01-product-contract-konsolidierung.md` | konsolidierte Cross-Audit-Landkarte und Status aller 37 Konflikte | B | aktuell, Konflikte klassifiziert; `STILL_OPEN 0` | Audits 01–13, Freeze, Ist-Code und Datenrisiken |
| `Dokumentation/Post-RC/02-cross-audit/02-product-contract-freeze.md` | normativer Closed-Beta-Produktvertrag | B | aktuell, eingefroren | neun PO-Entscheidungen, Audits und Cross-Audit |
| `Dokumentation/Post-RC/03-closed-beta-build-plan.md` | operativer Closed-Beta-Bauplan | B | aktuell, umsetzungsbereit; noch nicht begonnen | Freeze, technische Ist-Systeme, Migrationen, Tests und Gates |
| `Dokumentation/Post-RC/02-ux-architecture.md` | künftige seitenübergreifende UX-Regeln | B | aktuell, noch nicht begonnen | Navigation-Spezifikation und S05–S07 |
| `Dokumentation/Post-RC/03-beta-scope.md` | früherer Placeholder für Closed-Beta-Scope | F | durch Freeze und `03-closed-beta-build-plan.md` als aktuelle Source of Truth ersetzt | alte Public-Beta-Roadmap; RC1-Releasebefunde |
| `Dokumentation/Post-RC/04-design-system.md` | künftige visuelle Produktregeln | B | aktuell, noch nicht begonnen | Branding und Product-Bible-Designsystem |
| `Dokumentation/Post-RC/05-ui-backlog.md` | künftige konkrete UI-Aufgaben | B | aktuell, noch nicht begonnen | alte S30/S31/S37-Unterlagen |
| `Dokumentation/Post-RC/06-engineering-hardening.md` | künftige technische Releasequalität | B | aktuell, noch nicht begonnen | Release-, Operations-, Security- und Performanceunterlagen |
| `Dokumentation/Post-RC/07-simulation.md` | künftige Mehrnutzer-/Fake-Account-Simulation | B | aktuell, noch nicht begonnen | RC1-Testmatrix und Gap Analysis |
| `Dokumentation/Post-RC/08-closed-beta-gate.md` | künftige finale Beta-Freigabe | B | aktuell, noch nicht begonnen | RC1-Checkliste und Releaseanalysen |
| `Dokumentation/Post-RC/repository-inventory.md` | Repository- und Hygiene-Inventur | B | aktuell | RC1 Soll-Ist-Analyse enthält ähnliche Befunde |
| `Dokumentation/Post-RC/documentation-index.md` | vollständige Dokumentationsklassifikation | B | aktuell | Product-Bible-Indizes |
| `Dokumentation/Post-RC/source-of-truth.md` | Pflegezuständigkeiten und Konflikte | B | aktuell | Product-Bible-Regeln |

## Technische Verträge und RC-Unterlagen

| Pfad | Vermuteter Zweck | Kategorie | Status | Mögliche Überschneidungen |
| --- | --- | --- | --- | --- |
| `Dokumentation/Product Bible/design-system/s30-design-foundation.md` | implementierter RC-Design-Foundation-Vertrag | C | historischer RC-Vertrag | Branding; Post-RC Design System; S30-Report |
| `Dokumentation/Product Bible/design-system/s31-ui-foundation.md` | implementierter UI-Foundation-/Workflow-Vertrag | C | historischer RC-Vertrag | Post-RC UX/UI; S31-Report |
| `Dokumentation/Product Bible/security/s32-auth-session-csrf.md` | Auth-, Session-, Secret- und CSRF-Vertrag | C | aktuell als technischer Vertrag | S03, S32-/S33-Reports, S35 |
| `Dokumentation/Product Bible/operations/s34-deployment-recovery.md` | kanonischer Deployment-/Recovery-/Observability-Vertrag | C | aktuell | Checklisten, S34-Report, RC1-Unterlagen |
| `Dokumentation/Product Bible/operations/s34-deployment-checklist.md` | operative Deployment-Checkliste | C | aktuell | Deployment-Vertrag, RC1-Checkliste |
| `Dokumentation/Product Bible/operations/s34-recovery-checklist.md` | operative Recovery-/Incident-Checkliste | C | aktuell | Deployment-Vertrag, S34-Report |
| `Dokumentation/Product Bible/release/RC1-checklist.md` | technische RC1-Abnahme | E | historischer Release-Nachweis mit offenen Gates | Closed-Beta-Gate; Operations |
| `Dokumentation/Product Bible/release/RC1-known-issues.md` | bekannte technische Schulden und Blocker | E | historischer RC1-Stand, fachlich relevant | Engineering Hardening; S35 |
| `Dokumentation/Product Bible/release/RC1-soll-ist-analyse.md` | umfassendes Releaseaudit | E | historischer RC1-Stand | Repository-Inventur; Hardening; Gate |
| `Dokumentation/Product Bible/release/RC1-soll-ist-executive-summary.md` | Kurzfassung des Releaseaudits | E | historischer RC1-Stand | Vollanalyse; Gate |
| `Dokumentation/Product Bible/release/RC1-test-matrix.md` | Abdeckung und offene Releaseprüfungen | E | historischer RC1-Stand | Tests; Hardening; Gate |

Die sieben PNG-Dateien unter `Dokumentation/Product Bible/design-system/screens/` sind visuelle RC-Nachweise, keine `.md`/`.txt`-Dokumente: `album-390.png`, `home-390.png`, `notifications-390.png`, `profil-390.png`, `sammlung-390.png`, `stickerwall-390.png`, `trade-390.png`. Status: historischer Referenzstand; Überschneidung mit der späteren Post-RC-Designphase.

## Roadmap und Sprintverträge

| Pfad | Vermuteter Zweck | Kategorie | Status | Mögliche Überschneidungen |
| --- | --- | --- | --- | --- |
| `Dokumentation/Product Bible/roadmap/README.md` | Index und frühere „verbindliche Roadmap“ | F | vermutlich veraltet als aktueller Einstieg | Post-RC Master Plan; RC1-Checkliste |
| `Dokumentation/Product Bible/roadmap/development-roadmap-v1.md` | frühere Umsetzungsreihenfolge S00–S38 | D | historisch; als „verbindlich“ bezeichnet | Post-RC Master Plan und Beta-Prozess |
| `Dokumentation/Product Bible/roadmap/current-state-gap-analysis.md` | Vor-Roadmap Soll-/Ist-Analyse | D | historisch | RC1 Soll-Ist-Analyse |
| `Dokumentation/Product Bible/roadmap/s00-reference-and-test-data.md` | Referenzstand/Testdatenstrategie | C | historischer Sprintvertrag | S00-/S01-Tests, Reports |
| `Dokumentation/Product Bible/roadmap/s01-inventory-regression-tests.md` | Bestands-Regressionstestvertrag | C | historischer Sprintvertrag | Tests, S01-Report |
| `Dokumentation/Product Bible/roadmap/s02-paper-list-tradeflow-regression-tests.md` | Papierlisten-/Tradeflow-Testvertrag | C | historischer Sprintvertrag | Tests, S02-Report |
| `Dokumentation/Product Bible/roadmap/s03-side-effect-security-test-gate.md` | frühes Security-Testgate | C | historischer Sprintvertrag | S32/S33-Security |
| `Dokumentation/Product Bible/roadmap/s04-home-collection-routes.md` | Trennung von Home-/Sammlungsrouten | C | historischer Sprintvertrag | Product Bible Home/Sammlung; Post-RC Audits |
| `Dokumentation/Product Bible/roadmap/s05-three-area-navigation.md` | dreiteilige Bottom-Navigation | C | historischer Sprintvertrag | Navigation-Spezifikation; Post-RC UX Architecture |
| `Dokumentation/Product Bible/roadmap/s06-global-header-shell.md` | globaler Header | C | historischer Sprintvertrag | Navigation-Spezifikation; S31 |
| `Dokumentation/Product Bible/roadmap/s07-deep-link-origin-context.md` | Deep-Link- und Rückwegvertrag | C | historischer Sprintvertrag | Navigation-Spezifikation; Post-RC UX Architecture |
| `Dokumentation/Product Bible/roadmap/s08-inventory-contract-v1.md` | Inventory-Fachvertrag | C | historischer Sprintvertrag | Collection-Spezifikation; S09–S12 |
| `Dokumentation/Product Bible/roadmap/s09-inventory-read-service.md` | Inventory-Lesedienst | C | historischer Sprintvertrag | S08/S10/S11 |
| `Dokumentation/Product Bible/roadmap/s10-inventory-write-service.md` | Inventory-Schreibpfade | C | historischer Sprintvertrag | S08/S12 |
| `Dokumentation/Product Bible/roadmap/s11-availability.md` | Availability-Projektion | C | historischer Sprintvertrag | Trading/Collection; S19/S20 |
| `Dokumentation/Product Bible/roadmap/s12-inventory-guard.md` | Bestands-Guard und Fehlervertrag | C | historischer Sprintvertrag | S08/S10 |
| `Dokumentation/Product Bible/roadmap/s13-trade-lifecycle-schema.md` | Trade-Lifecycle-Schema | C | historischer Sprintvertrag | Trade-Lifecycle-Spezifikation; S14–S18 |
| `Dokumentation/Product Bible/roadmap/s14-trade-reservations.md` | Trade-Reservierungen | C | historischer Sprintvertrag | Trade-Lifecycle; S15–S18 |
| `Dokumentation/Product Bible/roadmap/s15-trade-shipping-transit.md` | Versand-/Transitvertrag | C | historischer Sprintvertrag | Trade-Lifecycle; S16–S19 |
| `Dokumentation/Product Bible/roadmap/s16-trade-receipt.md` | Empfang und Bestandsbuchung | C | historischer Sprintvertrag | Trade-Lifecycle; S17/S18 |
| `Dokumentation/Product Bible/roadmap/s17-trade-problems-partial-receipt.md` | Problemfälle und Teilempfang | C | historischer Sprintvertrag | Trade-Lifecycle; S18.2 |
| `Dokumentation/Product Bible/roadmap/s18-trade-lifecycle-timeline.md` | Timeline und Fälligkeiten | C | historischer Sprintvertrag | Trade-Lifecycle; S18.2 |
| `Dokumentation/Product Bible/roadmap/s18-2-problem-trade-finalization.md` | endgültiger Problemtrade-Abschluss | C | historischer Sprintvertrag | gleich nummerierter Konsolidierungsvertrag; Reports |
| `Dokumentation/Product Bible/roadmap/s18-2-trade-completion-consistency.md` | Konsolidierung des Tradeabschlusses | C | historischer Sprintvertrag | anderer S18.2-Vertrag; Nummerierungsbericht |
| `Dokumentation/Product Bible/roadmap/s19-shared-availability-snapshot.md` | gemeinsamer Availability Snapshot | C | historischer Sprintvertrag | S11/S20/S21 |
| `Dokumentation/Product Bible/roadmap/s20-market-coverage.md` | Markt-/Trade-Abdeckung | C | historischer Sprintvertrag | Trading; S19/S21 |
| `Dokumentation/Product Bible/roadmap/s21-conflict-free-top-match-optimization.md` | Top-Match-Optimierung | C | historischer Sprintvertrag | Trading; S20/S22 |
| `Dokumentation/Product Bible/roadmap/s21-preflight.md` | Vorprüfung desselben S21-Themas | D | historisch | S21-Hauptvertrag und Report |
| `Dokumentation/Product Bible/roadmap/s22-smart-trade-requests.md` | Smart-Trade-Anfragen | C | historischer Sprintvertrag | Trading; S21/S27 |
| `Dokumentation/Product Bible/roadmap/s23-typed-notifications.md` | typisierte Notifications | C | historischer Sprintvertrag | Home/Navigation; S24 |
| `Dokumentation/Product Bible/roadmap/s24-notification-history-navigation.md` | Notification-Historie und Navigation | C | historischer Sprintvertrag | Home/Navigation; S23 |
| `Dokumentation/Product Bible/roadmap/s25-operational-home-v1.md` | operatives Home | C | historischer Sprintvertrag | Product Bible Home; Post-RC Home-Audit |
| `Dokumentation/Product Bible/roadmap/s26-public-profile-v1.md` | Profilfundament | C | historischer Sprintvertrag | Profile/Community |
| `Dokumentation/Product Bible/roadmap/s27-album-privacy-trade-pool.md` | Album-Privacy und Tradepool | C | historischer Sprintvertrag | Collection-Spezifikation; Post-RC Album-Audit |
| `Dokumentation/Product Bible/roadmap/s28-trade-ratings.md` | Tradebewertungen | C | historischer Sprintvertrag | Profile/Trading |
| `Dokumentation/Product Bible/roadmap/s29-friendships-community.md` | Freundschaften und Community | C | historischer Sprintvertrag | Profile/Home |
| `Dokumentation/Product Bible/roadmap/s35-account-lifecycle-privacy-performance.md` | Account, Privacy und Performance | C | historischer Sprintvertrag | Security; S35-Baseline; Releasebefunde |
| `Dokumentation/Product Bible/roadmap/s35-performance-baseline.md` | Performance-Messvertrag | C | aktuell als reproduzierbarer technischer Vertrag | S35-Report; Release Known Issues; Hardening |
| `Dokumentation/Product Bible/roadmap/s36-data-export-compliance.md` | Datenexport und Compliance | C | historischer Sprintvertrag | Login-Footer; Closed-Beta-Gate |
| `Dokumentation/Product Bible/roadmap/s37-beta-polish.md` | Beta-Polish-Vertrag | C | historischer Sprintvertrag | Post-RC UX/UI-Prozess |

## Sprintberichte und Audits

Alle folgenden Dateien sind Kategorie **E – Audit/Report**, Status **historisch**. Sie dokumentieren ausgeführte Sprints, Checks oder Untersuchungen und überschneiden sich jeweils mit dem gleich nummerierten Sprintvertrag, Tests und teilweise den kanonischen technischen Unterlagen:

- `Dokumentation/Product Bible/roadmap/sprint-reports/S02-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S03-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S04-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S05-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S06-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S07-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S08-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S09-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S10-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S11-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S12-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S13-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S14-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S15-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S16-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S17-inventory-bug-investigation.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S17-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S18-numbering-cleanup-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S18-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S18.1-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S18.2-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S19-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S20-closeout-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S20-debug-smoke-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S20-debug-start-smoke-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S20-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S21-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S22-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S23-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S24-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S25-local-migration-check.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S25-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S26-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S27-local-migration-check.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S27-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S28-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S29-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S30-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S31-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S32-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S33-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S34-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S35-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S36-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S37-report.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S37-ux-routing-smoke.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S38-report.md`

Besonders auffällige Überschneidungen: S20 besitzt Hauptreport, Closeout und zwei Debug-Smokes; S25/S27 besitzen zusätzliche lokale Migrationschecks; S18 besitzt mehrere Nummern-/Abschlussartefakte; S34/S35/S38 wiederholen Release- und Gatebefunde aus `operations/` beziehungsweise `release/`.

## Historischer Index

| Pfad | Vermuteter Zweck | Kategorie | Status | Mögliche Überschneidungen |
| --- | --- | --- | --- | --- |
| `docs/ux_audit.md` | historischer Hinweis auf die überführten Product Audits | D | historisch | Post-RC Product Audit; enthält bewusst keine duplizierten Inhalte |

## `.txt`-Dateien, die keine Projektdokumentation sind

| Pfad | Inhalt / Zweck | Kategorie | Status | Überschneidung |
| --- | --- | --- | --- | --- |
| `requirements.txt` | Python-Abhängigkeiten | C | aktuell, technische Konfiguration | Deployment/Reproduzierbarkeit |
| `App/Database/em24_fehlende.txt` | Bestands-/Seedwert | G | Daten, nicht Dokumentation | `Exports/em24_fehlende.txt` |
| `App/Database/fehlende.txt` | JSON-Bestandsliste | G | Daten, nicht Dokumentation | `Exports/fehlende.txt` |
| `App/Database/repair_vfl_database.py.txt` | leere Datei | G | Zweck unklar | gleichnamiges Python-Skript |
| `Backups/em24_doppelte.txt` | historische JSON-Bestandsliste | D | historisches Datum/Backup | `Exports/em24_doppelte.txt` |
| `Exports/doppelte.txt` | exportierte JSON-Liste | G | Laufzeit-/Nutzerdaten | weitere Exportlisten |
| `Exports/em24_doppelte.txt` | exportierte JSON-Liste | G | Laufzeit-/Nutzerdaten | Backupkopie |
| `Exports/em24_fehlende.txt` | exportierte Bestandsliste | G | Laufzeit-/Nutzerdaten | App/Database-Kopie |
| `Exports/fehlende.txt` | exportierte JSON-Liste | G | Laufzeit-/Nutzerdaten | App/Database-Kopie |

## Doppelte Wahrheiten und thematische Überschneidungen

Die folgenden Aussagen beziehungsweise Entscheidungsbereiche erscheinen derzeit mehrfach. Das ist keine Neubewertung ihrer Gültigkeit.

- Entscheidung „drei Hauptbereiche / Bottom-Navigation“ erscheint in `Product Bible/specifications/navigation-information-architecture.md`, `roadmap/s05-three-area-navigation.md`, `roadmap/s06-global-header-shell.md` und den zugehörigen Reports.
- Entscheidung zu Deep Links und sinnvollen Rückwegen erscheint in `Product Bible/specifications/navigation-information-architecture.md`, `roadmap/s07-deep-link-origin-context.md` und S07-Report.
- Entscheidung zur Trennung Home und Sammlung erscheint in `Product Bible/specifications/home.md`, `specifications/collection.md`, `roadmap/s04-home-collection-routes.md` und den Post-RC-Audits `02-sammlr-zentrale.md`/`03-sammlung.md`.
- Entscheidung „Home zeigt Handlungsbedarf; vollständige Tradeverwaltung bleibt in Tauschen“ erscheint in `Product Bible/specifications/home.md`, `roadmap/s25-operational-home-v1.md` und `Post-RC/01-product-audit/02-sammlr-zentrale.md`.
- Entscheidungen zu eigenständigen Albumexemplaren und gemeinsamem Tauschbestand erscheinen in `Product Bible/specifications/collection.md` und `Post-RC/01-product-audit/04-album.md`.
- Entscheidungen zu Album-Privacy und Tradepool erscheinen in `Product Bible/specifications/collection.md`, `roadmap/s27-album-privacy-trade-pool.md`, S27-Report und `Post-RC/01-product-audit/04-album.md`; das Audit bewertet zusätzlich die Prominenz auf der Seite.
- Trophäenregeln erscheinen in `Product Bible/specifications/collection.md`, `specifications/navigation-information-architecture.md`, Branding `Design Bible/` und im Album-Audit. Dabei behandeln die Dateien Fachlogik, Navigation, Assets und Seitenbewertung teilweise unterschiedlich, aber die Zuständigkeiten sind noch nicht durchgängig explizit.
- Statistikregeln erscheinen in der aktuellen `/statistik`- und Albumstatistik-Implementierung, `Product Bible/specifications/profile-community.md`, S26 sowie den Audits zu Profil und Trophäen. Audit 12 trennt erstmals verbindlich historische Karrierewerte von aktuellen Bestandswerten und dokumentiert die fehlende Album-/Bestandschronik.
- Albumabschluss und Vitrine erscheinen in Sammlung, Profil-Spezifikation, S26 sowie den Audits 04, 08, 09, 11 und 12. Audit 13 konsolidiert den genau einmaligen Erstabschluss; PO-05/06 entscheiden Zählung und Closed-Beta-Klickziel nach einer Löschung verbindlich.
- Die Cross-Audit-Konsolidierung in `02-cross-audit/01-product-contract-konsolidierung.md` verknüpft alle Audits 01–13 und klassifiziert alle 37 Konflikte. Der Freeze entscheidet PO-01 bis PO-09; der Bauplan übersetzt sie in technische Pakete, Migrationen, Tests und Gates.
- Tradeentscheidungen erscheinen parallel in `specifications/trading.md`, `specifications/trade-lifecycle.md`, den Post-RC-Audits `06-tauschboerse.md`/`07-trade-lifecycle.md`, den Sprintverträgen S13–S22 und den jeweiligen Reports. Die Product Bible bleibt langfristige Fachwahrheit; die Audits dokumentieren die aktuelle Seitenbewertung und neue, noch zu konsolidierende PO-Entscheidungen.
- Security-Verträge erscheinen in S03, `security/s32-auth-session-csrf.md`, S32-/S33-Reports, S35 und RC1-Releaseunterlagen.
- Deployment-/Recoveryregeln erscheinen in `operations/s34-*`, S34-Report, RC1-Checkliste, Testmatrix und Soll-Ist-Analyse.
- Performanceblocker erscheinen in `roadmap/s35-performance-baseline.md`, S35-Report, `release/RC1-known-issues.md`, beiden Soll-Ist-Dokumenten, RC1-Checkliste und Testmatrix.
- Closed-/Public-Beta-Gates erscheinen in der alten Development Roadmap, RC1-Releaseunterlagen und den neuen Post-RC-Dateien `03-beta-scope.md`, `06-engineering-hardening.md` und `08-closed-beta-gate.md`.
- Die Rolle der Product Bible als Produktwahrheit erscheint in ihrem `README.md`, den Spezifikationspräambeln und dem Post-RC Master Plan beziehungsweise `source-of-truth.md`.

## Erkannte echte Konflikte

- `Product Bible/roadmap/README.md` nennt die Development Roadmap weiterhin die aktuelle zentrale Umsetzungsreihenfolge und sagt „S38 wurde nicht begonnen“; `release/RC1-checklist.md` dokumentiert S00–S38 und RC1 als abgeschlossen, während der Post-RC Master Plan bereits den Folgeprozess startet.
- `Product Bible/specifications/collection.md` und `home.md` dokumentieren selbst einen älteren terminologischen Konflikt um „Sammlr-Zentrale“ versus Home. Das neue Audit trägt im Dateinamen „sammlr.-Zentrale / bisheriges Home“, wodurch die Begriffsgrenze weiterhin klärungsbedürftig ist.
- Die künftigen Zuständigkeiten von `Post-RC/02-ux-architecture.md` und `Post-RC/04-design-system.md` überschneiden sich mit bestehenden, als verbindlich gekennzeichneten Product-Bible-/Branding-Unterlagen. Noch besteht kein neuer Sachwiderspruch, aber ein Source-of-Truth-Konflikt bei der Pflegezuständigkeit.
- `Product Bible/specifications/trading.md` klassifiziert albumübergreifende SmartTrades als „Später / Vision“; das Post-RC-Audit `06-tauschboerse.md` dokumentiert sie als notwendigen fachlichen Bereich und SmartTrades insgesamt als Kernnutzen. Dies ist noch keine Beta-Scope-Freigabe, aber eine zu konsolidierende Prioritätsspannung.
- Das archivierte Trading-Protokoll erlaubt die automatische Verkleinerung offener Dealpakete; die neuere PO-Entscheidung lässt eine nicht mehr erfüllbare ursprüngliche Anfrage sichtbar, blockiert ihre Annahme und verhindert eine ungültige Reservierung. Eine Neuberechnung ist als neuer Vorschlag denkbar, nicht als heimliche Änderung der ursprünglichen Anfrage.
- Die aktuelle Statistik nennt die Summe des momentanen Bestands „gesammelt“, führt globale Fehlende/Doppelte und zählt Tradepakete beider Seiten zusammen. Audit 12 verlangt stattdessen eine nicht sinkende Lebenszeitsumme, albumbezogene operative Bestandswerte sowie getrennte historische erhaltene/abgegebene Tradeeinheiten.
- S26 setzt `Doppelte` als feste Profilkennzahl und zählt alle Trophy-Zeilen. Audit 08/12 stuft Doppelte als operativ ein; Audit 11/12 begrenzt die Statistikzahl auf gültige albumbezogene Trophäen.
- Sammlung, Profil/S26 und Statistik behandeln ein Album nur bei aktuellem `100 %` als abgeschlossen. Audit 13 verlangt dagegen einen dauerhaften historischen Erstabschluss mit Datum; die aktuelle „Vitrine“ ist daher eine dynamische Bestandsprojektion und kein Abschlussarchiv.
- Die frühere Kollision zwischen gelöschtem Album und bewahrter Abschlussgeschichte ist durch PO-05/06 aufgelöst: Bewahren zählt weiter; Mitlöschen nicht; ohne aktives Album ist die Karte in der Closed Beta nicht anklickbar.
- Das heutige typbezogene Modell `user_id + album_id` kollidiert mit dem in Audit 04/13 langfristig erforderlichen exemplarbezogenen Abschluss mehrerer physischer Alben desselben Typs.
