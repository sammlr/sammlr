# LIFECYCLE-05 — Versandadressen und gegenseitige Freigabe

Stand: 2026-10-08. Implementierung und Abnahme bis ausschließlich `ready_to_ship`.
Ausgangscommit: `a5be3f023f6c4b8ee7e31f7067af4492b604bd02`.
Branch: `feature/wm-special-trophies`; Upstream: `origin/feature/wm-special-trophies`;
Remote: `https://github.com/sammlr/sammlr.git`.
Der Abschlusscommit trägt `feat: add lifecycle v1 address release`; sein Hash wird im Abschlussbericht und Git dokumentiert (keine Selbstreferenz im Commit).

## Architektur und Vertragsbasis

Die bestehenden Lifecycle-01–04-Services, Teilnehmerprüfung, bindende Revision,
Preparation-Zyklen, gegenseitige Reviews, Command-Identitäten und `BEGIN IMMEDIATE`
werden wiederverwendet. Keine zweite Trade-Domain. Keine Pflichtadresse bei
Registrierung, Sammlung, SAP, Anfrage, Annahme oder Preparation. Keine Kopplung
an öffentliche Profile. Legacy-Verträge erhalten weder Adresspflicht noch neue
Transitions.

Audit der bestehenden Architektur: Es gibt kein geeignetes produktives privates
Adressbuch und keinen bestehenden Verschlüsselungshelfer für postalische Felder.
Die begrenzte Profil-Länderliste wird nicht zur Einschränkung von Versandadressen
verwendet. Vorhandene Authentifizierung, CSRF, signierte Formulare, SQLite-
Transaktionen und TypedNotificationService werden genutzt.

Der aktuelle Auftrag konkretisiert die Reihenfolge: abgeschlossene beidseitige
Fotoprüfung, dann explizite eigene Adressbestätigung, dann automatische gegenseitige
Freigabe beim zweiten gültigen Einreichen. Kein zusätzlicher Freigabebutton.
`released_at` stellt den eindeutigen Anker für die später vertraglich vorgesehene
72h-Versandphase bereit; hier entstehen weder Versanddeadline-Verarbeitung noch
Countdown oder Versandaktion.

## Persistenz und Migration

Neue additive Migration **0027_trade_lifecycle_addresses** (up/down).
0022–0026 unverändert. Nur synthetische Migrationstests unter `/private/tmp`;
keine reale lokale oder produktive DB migriert. Die geschützte Entwicklungs-DB
bleibt auf ihrer bisherigen Baseline (Schema 20 laut vorheriger Abnahme).

- `lifecycle_address_book`: private Einträge mit Owner, Version, optionalem Label,
  bevorzugter Adresse und Zeitstempeln. Partieller Unique-Index: maximal ein Default
  je Nutzer. Create/Edit/Delete/Default nur durch den Besitzer.
- `lifecycle_address_book_commands`: nutzerbezogene Idempotenz; Payload-Digest und
  Ergebnis-IDs statt Kopien vollständiger Anschriften.
- `lifecycle_address_snapshots`: unabhängige, bereits bei Bestätigung kopierte
  Versandfelder, Trade, Owner, Revision, Preparation-Basis, Snapshot-Version und
  Auswahlzeitpunkt. Keine Live-Referenz auf das Adressbuch.
- `lifecycle_address_choices`: aktuelle Auswahl und monotone Generation je
  Trade/Teilnehmer; ersetzt vor Freigabe nur den Zeiger, nicht einen Snapshot.
- `lifecycle_address_releases`: genau eine Freigabe mit beiden exakten Snapshot-IDs,
  Revision, Preparation-Basis und `released_at`.

Pflichtfelder: Vorname, Nachname, Straße, Hausnummer, Postleitzahl, Ort, Land.
Serverseitig werden Leerraum normalisiert, leere oder zu lange Werte und
Kontrollzeichen abgelehnt. Land ist ein normalisierter zweistelliger Großbuchstaben-
Code. Keine deutsche PLZ-/Hausnummernspezialregel, keine externe postalische
Validierung oder Porto-/Länderzulässigkeitslogik. Private Labels werden nicht
an den Partner übertragen. E-Mail, Telefon, Profilstandort usw. werden nicht kopiert.

SQL-Guards sichern Owner/Trade/Revision, unveränderliche Snapshots und Releases,
verhindern Identity-Replacement und fixieren die Auswahl nach Release. Down
verweigert den Rückbau mit vorhandenen privaten Daten/Commands. Leerer Down/Up
und Upgrade einer bestehenden freigabereifen Preparation wurden getestet.

## Auswahl, Freigabe, Versandbereitschaft

Der Besitzer sieht eigene Adressen sofort. Default bewirkt keine Bestätigung oder
Freigabe. Ein verbindlicher Command enthält aktuelle Revision, beide Zyklus-IDs,
Auswahlgeneration, Adressbuch-ID und Version. Alte Tabs, fremde Adressen und
inzwischen geänderte Vertragsbasen werden abgelehnt.

Einseitige Auswahl bleibt privat und erlaubt bis zur Freigabe einen expliziten
Auswahlwechsel. Änderungen oder Löschen eines Adressbucheintrags ändern niemals
den bereits ausgewählten Trade-Snapshot. Ein Korrekturzyklus vor Freigabe macht
alte Auswahlen für die neue Basis unbrauchbar; beide Seiten müssen neu bestätigen.

Beim zweiten gültigen Command werden innerhalb derselben Schreibtransaktion
Teilnehmer, bindende Revision, Reviews, Probleme, Missing-Holds, offene Reduktion
und beide aktuellen Auswahlen geprüft. Beide Snapshot-IDs werden gemeinsam
fixiert, beide `preparation_state` werden `ready_to_ship`, History und beide
Notifications werden erzeugt. Fehler, auch bei Notification-Erzeugung, rollen
den gesamten Command zurück. `shipping_state` bleibt `not_sent`.

Nach Release werden die exakten freigegebenen Snapshots angezeigt. Normale
Adressänderung und normale Preparation-/Reduktionskorrektur nach dieser Grenze
werden sicher abgelehnt; eine eigene Post-Release-Problem-/Support-Semantik wird
hier nicht erfunden. Das bestehende Kontrollpaket verschwindet nach Release aus
der normalen Galerie gemäß Fachvertrag §8; Dateien werden dadurch nicht gelöscht.

## Privacy und Security

Serverseitige Teilnehmer-, aktiver-Account-, Vertrags- und Freigabeprüfung gelten
für HTML und direkte JSON-Snapshot-Routen. Vor Freigabe erhält der Partner keine
fremde Anschrift, auch nicht in verstecktem DOM, signierten Formulardaten oder
manipulierten IDs. Dritte erhalten keinen Zugriff. Nach Ende des aktiven Vertrags
wird Partnerzugriff verweigert (Zweckbindung aus NP-C3-1). Keine allgemeine
Support-/Admin-Adressroute. Keine neue Debug-/Preview-Route mit echten Adressen.

Private Antworten: `Cache-Control: private, no-store`, `Referrer-Policy: no-referrer`.
Bestehende Login-/CSRF-Regeln und signierte, actor-gebundene Formulare bleiben aktiv.
Fehlertexte wiederholen keine eingegebenen Anschriften. Es gibt keine neuen
Adress-Logs oder vollständigen Adressen in Audit/History/Notifications. Die
Browser-Prüfung verwendet ausschließlich synthetische Daten.

Events: `TradeAddressConfirmed`, `AddressesReleased`, `TradeReadyToShip` mit
Identitäten/Zustandsbezug, ohne vollständige Versanddaten. Neuer geschlossener
Notification-Typ `lifecycle_addresses_released`; je Empfänger genau eine Meldung
mit neutralem Text und geprüftem Trade-Ziel. Bestehende Legacy-Notification-
Produktion bleibt unverändert; Tests berücksichtigen den additiven Katalogtyp.

## Idempotenz, Konkurrenz und Inventar

Buchoperationen verwenden nutzerbezogene Command-Keys und Payload-Digests;
Trade-Bestätigungen den vorhandenen Lifecycle-Command-Store. Retry erzeugt keine
zusätzlichen Snapshots, Releases, Events oder Notifications. Versions-/Generations-
prüfung und Transaktionsserialisierung verhindern gemischte Auswahlen.

Explizit getestet: gleichzeitige Bestätigung beider Seiten, doppelte Bestätigung,
Auswahlwechsel gegen Partnerbestätigung, Buch-Edit/Delete gegen Bestätigung,
Freigabe gegen Review-Korrektur und Reduktion. Ergebnis ist ein konsistenter
Gewinnerzustand oder sichere Ablehnung.

Quantities, Give-Reservations, Need-Bindings und Physical-Missing-Holds bleiben
bei Auswahl und Release exakt unverändert (Vorher-/Nachher-Assertion).
Keine Versandbestätigung, Bestandsabbuchung, Slotfreigabe, Tracking-, Porto-,
Empfangs- oder Bewertungsfunktion.

## UI und Begehung

- `/tauschen/vorbereitung/<trade>`: Einstieg nach abgeschlossener Prüfung;
  nach Release nur Versandbereitschaft/Adresslink statt normaler Preparation-Aktionen.
- `/tauschen/adressen/<trade>`: eigene Auswahl, expliziter Datenschutzhinweis vor
  Bestätigung, einseitiger Wartezustand oder beide fixierten Versandadressen.
- `/tauschen/adressbuch`: mehrere eigene Adressen, Edit/Delete/Default.
- `/tauschen/adressbuch?trade=<trade>`: eigener validierter Rückweg zur Auswahl.
- `/tauschen/adressen/<trade>/snapshots/<snapshot>`: identisch geschützte JSON-Ansicht.

Auf unmigrierter geschützter DB bleibt die Adressfunktion schema-gated (503),
ohne automatische Migration. Vollständige lokale Begehung mit realer DB folgt
wie beauftragt erst im separaten Integrationspaket. Hier wurde die produktive
Flask-UI mit ausschließlich synthetischen Daten im isolierten Checkout geprüft.

## Tests und Nachweise

- Vollständige Release-Suite: **1.542 Tests bestanden**, 0 Fehler, 0 Failures,
  0 Skips; 1.554 entdeckt, dieselben **12** vertraglichen Ausschlüsse unverändert.
- Darin **30 neue L05-Tests**: 24 Domain-/Persistenz-/Konkurrenztests und
  6 HTTP-/Security-/UI-Tests.
- Zusätzlich **8 separate Pax-/Trade-v2-Preview-Tests bestanden**.
- Enthalten: Lifecycle 01–04, TradeV2, Inventory, Reservations, SAP, SmartDeal,
  Legacy, Registrierung/Profile und bestehende Solver-Vergleiche.
- Browser A–D bestanden: bestehende/neue Adresse und verdecktes Warten;
  Auswahlwechsel; Buch-Edit nach Freigabe; Dritter/manipulierte direkte URLs.
- Viewports **375 / 390 / 430 / 1280 px** ohne horizontalen Overflow;
  keine JavaScript-Fehler; **9 Screenshots**.
- Migration: synthetisches Upgrade, leerer Down/Up, befüllter Rückbau abgelehnt,
  Foreign-Key- und SQLite-Integritätsprüfungen bestanden.
- Release-/Browser-Harness verweigert SQLite-Dateizugriffe außerhalb
  `/private/tmp`; keine bestehende DB als Ausgangsdatenquelle kopiert.
- Finaler Source-Abgleich: alle 34 Source-/Testdateien bytegleich mit dem
  vollständig release-getesteten isolierten Kandidaten; Audit zusätzlich.
- `git diff --check` und finaler Index-Diff-Check sind Abschlussgates.

Lokale, nicht zu committende Nachweise:
`/private/tmp/lifecycle05/release-results.json`, `release.log`, `preview.log`,
`browser/results.json`, `browser/*.png`, `db-start.json`, `final-files.json`.
Reproduzierbar: `Scripts.prepare_release_tests`, bestehender Release-Testvertrag,
neue Unit-Tests und `tests/research/check_lifecycle05.py`. Browser-Skript verweigert
Ausführung außerhalb eines isolierten Source-Kandidaten unter `/private/tmp`.

## DB-Schutz

Alle **16** geschützten Dateien vor/nach Tests per SHA256 identisch. Keine neue
Test-DB im Repository, keine DB/Runtime-Datei im Commitumfang. Ungetrackte und
ignorierte lokale Dateien bleiben unangetastet. Kein Hash als neue Baseline
übernommen, keine Reparatur oder Migration realer Daten.

Die folgende Tabelle nennt jeweils den identischen Vorher-/Nachher-Hash:

| Datei | SHA256 vorher = nachher |
| --- | --- |
| `App/Database/sammlr_reference_s00.db` | `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971` |
| `App/Database/s20_coverage_debug.db` | `dadac1c379a45ec0245208293aef3eccd732cc41b3c07e4b8c523cace1444d9e` |
| `App/Database/sammlr.db` | `c317d3ee7418f9caeaf655e9ed13c04ccdd88f1b8599652b42d56b1163905771` |
| `App/Database/Database:Backups/collectr_backup_before_trophy_cleanup.db` | `447a9164ba7772b04ee12ccfc5c65a39720cf1f1776c86002ffe3161fded287e` |
| `App/Database/Database:Backups/collectr_backup_popup_clean.db` | `6bcb037730123b78fe756856bc8735a7358f185872040d179fc34a5ebb1d51e3` |
| `App/Database/Database:Backups/collectr_backup_before_users.db` | `f4796d18d36a6a0f1625bfc7eb2fb926006ef50d534472ca32a3cfbe0a4e8039` |
| `App/Database/Database:Backups/collectr_backup_trophy_tabs_visual_runs.db` | `6bcb037730123b78fe756856bc8735a7358f185872040d179fc34a5ebb1d51e3` |
| `App/Database/Database:Backups/collectr_backup_users_trophy_clean_runs.db` | `602883a8538f9377847542c1c7c969d326adc7d071c6cca2ff5822eca1b96f8f` |
| `Backups/sammlr_local_pre_v0005_20260803_211622.db` | `cb69ff4407f6c9c166e84d472f8a89b32e33692cde109b437b1d60ebb0aa0a01` |
| `Backups/sammlr_local_pre_v0003_20260802_091642.db` | `ff96c936c3a4fe86433f3cd42dfbc51e24a034a02c147ccc5e40aefdb436c5d8` |
| `Backups/sammlr_before_valy_password_reset_20261004T084422847704Z.db` | `0748a936250c2771173a5bfb3853b7718c79e376fed25409438d0927062c5eb1` |
| `Backups/collectr_2026-06-02_22-14-58.db` | `474f1bf0573717c1594a5cb6311d1f8ea99c461357715e1e43315f6c3285654c` |
| `Backups/sammlr_local_pre_v0006_20260808_010509.db` | `159cc562b648ebf567878622b4db815cc2acf86601b9d2bc2a586793b8cd5912` |
| `Backups/sammlr_local_pre_v0004_20260802_232331.db` | `2063fddc7991cd699dc5321f8210b1278ee8180a96dbaf0ab0a89a87aafcd466` |
| `Backups/sammlr_local_pre_v0007_20260808_023853.db` | `752292434f44c637f7518c71494d5b7f787d786d881bca06024b8547c732eac8` |
| `App/Database/collectr.db Kopie` | `f25e1b02975da4cda2dfc0e217fe30ae294030dbb9fc0b7a5b6d4b93318f5e4a` |

## Retention / Launch / bekannte Grenzen

Keine erfundene Aufbewahrungsfrist und kein automatisches Löschen. Langfristige
Retention, rechtliche Grundlage, explizite Löschung/Anonymisierung und Backup-
Löschung bleiben Launch-/Privacy-Arbeit. Ownership und getrennte Tabellen erlauben
eine spätere autorisierte Erasure: Referenzen lösen, danach Snapshots löschen.
Ein Update-Guard ist keine unbegrenzte gesetzliche Aufbewahrungspflicht. Es gibt
hier keinen solchen öffentlichen Löschworkflow.

Postalische Felder werden in SQLite nicht anwendungsseitig verschlüsselt. Es
existiert kein passender projektweiter Encryption-Helfer; der Flask-Session-Key
wird nicht für eine improvisierte Verschlüsselung verwendet. Storage-/Backup-
Verschlüsselung und Schlüsselverwaltung sind vor produktiver Adressnutzung als
Launch-Sicherheitsaufgabe zu entscheiden. Bereits vom Partner kopierte Adressen
können technisch nicht zurückgerufen werden.

Keine externe postalische Zustellbarkeitsprüfung, kein Länder-/Porto-Regelwerk,
kein optionaler Copy-Button. Adresskorrektur nach Freigabe braucht einen separaten
Problem-/Support-Contract. Keine neuen Cancellation-/Shipping-Regeln.

## Exakter Commitumfang

Nur diese **35 Dateien**, einschließlich dieses Audits. Bestehende Teständerungen
beschränken sich auf die neue maximale Migrationsnummer und den additiven
Notification-Katalog; die historische Legacy-Eventproduktion bleibt geprüft.

- `App/Database/migrations/0027_trade_lifecycle_addresses.down.sql`
- `App/Database/migrations/0027_trade_lifecycle_addresses.up.sql`
- `App/lifecycle_address_routes.py`
- `App/services/trade_lifecycle_addresses.py`
- `App/services/trade_lifecycle_preparation.py`
- `App/services/typed_notifications.py`
- `App/templates/lifecycle_address_book.html`
- `App/templates/lifecycle_addresses.html`
- `App/templates/lifecycle_preparation.html`
- `App/templates/trade_shell.html`
- `App/trade_shell.py`
- `docs/LIFECYCLE_05_AUDIT.md`
- `tests/research/check_lifecycle05.py`
- `tests/test_cb008_notification_catalog.py`
- `tests/test_cb009_inbox_read_retention.py`
- `tests/test_cb011_executable_match_contract.py`
- `tests/test_cb012_feed_home_cutover.py`
- `tests/test_cb013_collection_completion_projection.py`
- `tests/test_cb014_profile_account_projection.py`
- `tests/test_cb015_statistics_projection.py`
- `tests/test_cb016_legacy_cutover.py`
- `tests/test_lifecycle01_foundation.py`
- `tests/test_lifecycle05_addresses.py`
- `tests/test_lifecycle05_ui.py`
- `tests/test_phase8_realistic_simulation.py`
- `tests/test_s23_typed_notifications.py`
- `tests/test_s26_collector_profiles.py`
- `tests/test_s27_album_privacy_trade_pool.py`
- `tests/test_s28_trade_ratings.py`
- `tests/test_s29_friendships_community.py`
- `tests/test_s31_ui_foundation.py`
- `tests/test_s32_auth_session_csrf.py`
- `tests/test_s33_http_integrity_hardening.py`
- `tests/test_s35_account_lifecycle_privacy_performance.py`
- `tests/test_s38_release_candidate.py`

## Abschlussgrenze

Nach sauberem Index-/Secret-/DB-Check erfolgt ausschließlich der autorisierte
Commit und normale Push auf den bestehenden Upstream. Keine Tags, kein Rebase,
kein Branchwechsel, kein Deploy. Local/Remote-HEAD werden unabhängig verifiziert
und im Abschlussbericht genannt. **LIFECYCLE-06 nicht begonnen.**
