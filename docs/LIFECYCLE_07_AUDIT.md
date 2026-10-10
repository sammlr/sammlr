# LIFECYCLE-07 — Empfang, Teilempfang und Lieferprobleme

Stand: 11.10.2026 (Integration Fix und erneute Abnahme). Ausgangscommit: `47204834e0def7ff176a981d0d04b979ce0c4146`.
Branch: `feature/wm-special-trophies`; Upstream: `origin/feature/wm-special-trophies`.
Remote: `https://github.com/sammlr/sammlr.git`.

## Ausgangskontrollen und Abgrenzung

Am 11.10.2026 wurden die bestehenden 37 Paketdateien ausdrücklich zur gezielten Fertigstellung autorisiert. Alle 37 SHA-256-Werte entsprachen vor Änderungen dem zuvor geprüften Manifest `/private/tmp/lifecycle07/formal-manifest.json`. HEAD, Branch und Upstream stimmen mit dem Ausgang überein; `git ls-remote` bestätigte unabhängig den gleichen Remote-HEAD. Index leer, 28 getrackte Änderungen und 9 neue Paketdateien vorhanden. Der vollständige Gitstatus wurde unter `/private/tmp/lifecycle07-final/git-start.txt` dokumentiert. 9.736 fremde ungetrackte Einträge wurden einschließlich Symlinkzielen erfasst und geschützt, insbesondere `sammlr-social-studio`. Alle 16 geschützten DBs wurden nur als Dateien gehasht und entsprachen der autorisierten L06-/L07-Baseline.

Die frühere pauschale Abnahmebehauptung vom 09.10.2026 war bezüglich der Gegenrichtungs-Fortsetzung nicht hinreichend belegt. Der damalige Teststand (1.625 Release-Tests, 41 L07-Tests, Browser A–G) bleibt als historischer Nachweis unter `/private/tmp/lifecycle07` erhalten. Maßgeblich sind die unten genannten neuen Prüfungen; es gab keinen Reset und keine Neuerstellung des Pakets.

Erweitert wird ausschließlich die bestehende V1-Domain mit `LifecycleReceipts(LifecycleShipping)`, deren Contract-, Teilnehmer-, Revisions-, Command- und Transaktionsprüfungen. Keine parallele Trade-Domain. Legacy-Commands, Inventory-Adapter, Reservationsadapter, ursprüngliche Migrationen und Testausschlüsse werden nicht umgeschrieben.

Kein Trade-Abschluss, Rating, Archiv, Reliability-Score, Adminentscheid, Messenger, Porto, Zentrale oder Deploy. Keine reale Migration. LIFECYCLE-08 nicht begonnen.

## Richtung, Mengen und verbindliche Prüfung

`lifecycle_directions` bleibt die kanonische Richtungsprojektion. `shipping_state` und `receipt_state` bleiben unabhängig; die jeweils andere Richtung wird durch Empfang nicht geändert.

| Empfangszustand | Bedeutung |
| --- | --- |
| `expected` | Bestehender kanonischer Wartezustand; Empfang nach vollständiger Vorbereitung/Fotoprüfung/Adressfreigabe auch ohne manuellen Versand zulässig. |
| `received_complete` | Alle erwarteten Einheiten korrekt und verbindlich akzeptiert. |
| `received_with_problem` | Fehlende, falsche oder beschädigte Einheiten dokumentiert; akzeptierte Mengen bereits gebucht. |
| `non_arrival_reported` | Nichtankunft gemeldet, ohne Zugang oder Rückbuchung. |

Erwartete Positionen und Mengen stammen ausschließlich aus `accepted_revision_id`, einschließlich gültiger L04-Reduktionen. Ein offener Reduktionsvorschlag blockiert die Empfangsbuchung. Alte Revisionen, fremde Positionen, doppelte Positionen, negative, nichtganzzahlige und überhöhte Mengen werden abgelehnt.

Jede erwartete Position wird vollständig in disjunkte Mengen zerlegt: `correct`, `missing`, `wrong`, `damaged_accepted`, `damaged_rejected`. Ihre Summe muss exakt der Erwartungsmenge entsprechen. Nur `correct + damaged_accepted` wird gutgeschrieben. Beschädigte Mengen sind ausdrücklich angenommen oder abgelehnt; auch angenommener Schaden bleibt als Lieferproblem auditierbar.

Bei falschen Stickern wird weder der erwartete noch der gemeldete falsche Code automatisch gutgeschrieben. Optionaler tatsächlicher Code wird ausschließlich gegen den öffentlichen Katalog des erwarteten Albums geprüft; fremde Inventardaten werden nicht übernommen. Ein Code anderer Alben wird in diesem optionalen Feld nicht akzeptiert.

## Atomare Bestandsbuchung und Receipt ohne Sent

Verbindliche Empfangskontrolle läuft vollständig unter der vorhandenen `BEGIN IMMEDIATE`-Schreibgrenze:

1. Aktiven Teilnehmer, Empfänger der konkreten Richtung und aktuelle bindende Revision prüfen. Aktuelle beidseitige Vorbereitung, Fotoprüfung und gegenseitige Adressfreigabe unter derselben Schreibsperre prüfen, danach Commandidentität.
2. Erwartete Positionen rekonstruieren und die Mengenpartition validieren.
3. Bestehenden identischen Empfang erkennen; abweichende erneute Inspektion ablehnen.
4. Zentrale L06-Finalisierung `finalize_direction_sent(..., source='RECEIPT_EVIDENCE')` aufrufen. Bereits vorhandener Versand wird unverändert zurückgegeben.
5. Fehlenden Senderabgang und exakten Give-Hold-Verbrauch durch diese bestehende Finalisierung sicherstellen.
6. Akzeptierte Zugänge über `HistoricalInventoryWriteService.set_quantity` buchen; vorherigen physischen Bestand unter derselben Schreibsperre lesen und exakt um die akzeptierte Menge erhöhen.
7. Genau zugehörige Need-Claims erfüllen, immutable Inspektion, Richtungsstatus, Events, Notifications und Commandresult speichern; gemeinsam committen.

Der aktuelle L07-Auftrag §§6/18 verlangt auch beim Teilempfang den exakten bindenden Give-Abgang. Damit konkretisiert er die älteren Planungsnotizen zu noch unbelegten Restabgängen. Die vorhandene L06-Abbuchungsimplementierung bleibt dabei unverändert; keine zweite Versandlogik und kein Legacy-`ship()` im Namen des Senders. Beispiel Erwartung 3, akzeptiert 2: Sender −3, Empfänger +2, Problemrest 1.

Der vorhandene Delta-Adapter verwendet beim erstmaligen Anlegen einer Bestandszeile `duplicates=0` und verletzt damit bei Zugang >1 den bestehenden SQL-Integritätsguard. L07 verwendet deshalb den bereits vorhandenen kanonischen Set-Adapter unter der Schreibsperre. Kein Fix oder Verhaltenswechsel des Legacy-Delta-Adapters. Historisches Event hält bisherigen/neuen Bestand sowie Quelle `trade_receipt` fest; die Mengenbewegung selbst enthält das akzeptierte Delta.

Versandherkunft bleibt in den kanonischen L06-Werten auditierbar:

| Fachlicher Begriff im Auftrag | Persistierter L06-Wert |
| --- | --- |
| `manual_sent` | `SENDER_CONFIRMATION`, `sender_confirmed_at = sent_at` |
| `systemic_sent_from_receipt` | `RECEIPT_EVIDENCE`, `sender_confirmed_at IS NULL` |

Bei systemischem Versand bezeichnet `sent_at` den Beobachtungs-/Finalisierungszeitpunkt, keinen erfundenen früheren Versandtermin. Die Versandoberfläche weist auf den unbekannten tatsächlichen Versandzeitpunkt hin. Ein späterer manueller Versand erzeugt weder weiteren Abgang noch zweiten Holdverbrauch, Timestamp oder Shipping-Event.

Bei unzureichendem oder durch Missing-Hold blockiertem Senderbestand, inkonsistentem Empfängerbestand oder fehlendem eindeutigen Claim wird sicher abgelehnt und vollständig zurückgerollt. Keine negative Menge, Nullkappung, Teilbuchung oder vorgetäuschte erfolgreiche Prüfung. Ein eigenständiger Reconciliation-/Korrekturworkflow ist nicht Teil dieses Pakets.

## Need-Bindings

Bestehende Semantik aus Vertrag §3a und Foundation wird unverändert verwendet: `received_quantity` steigt exakt um die akzeptierte Menge. Bei Vollannahme beträgt `quantity - received_quantity` null; der Claim bindet keinen weiteren Eingang. Bei Teilempfang bleibt ausschließlich die ungeklärte Differenz als verbindlicher Resteingang bestehen. Physischer Bestand und geplanter Eingang werden nicht doppelt gezählt.

Beispiel Ziel 3, vorher Bestand 0, Claim 3; nach Annahme 2: Bestand 2, verbleibender Claim 1, freier Bedarf 0. Die fehlende Einheit gilt ausdrücklich nicht als erfüllt. Weder Senderreaktion noch Non-Arrival löst den Restclaim. Der Trade wird hier nicht terminal beendet; eine spätere tatsächliche Nachmenge oder qualifizierte Problemklärung benötigt ihren eigenen nachvollziehbaren Folgeprozess. Es wird keine neue automatische Restfreigabe oder dauerhaft als erfüllt markierte Fehlmenge erfunden. Verbindliche LIFECYCLE-08-Aufgabe: Bei endgültiger Problemauflösung unerfüllte Restclaims korrekt freigeben oder fachlich abschließen. Bis dahin bleiben sie auditierbar gebunden. Diese Anschlussvereinbarung beginnt keine L08-Implementierung.

## Non-Arrival, Late Arrival und Absenderreaktion

Nichtankunft ist nur für den tatsächlichen Empfänger, vor bestätigtem Empfang und ab exakt `sent_at + 7×24h` einer manuellen Versandbestätigung zulässig. Eine Mikrosekunde früher wird serverseitig abgelehnt. Ohne manuellen Versand existiert kein erfundener Fristanker. Kein Inventory-Zugang, Sender-Restore, Cancel oder Tradeabschluss.

„Doch angekommen“ öffnet die normale vollständige oder strukturierte Kontrolle. Erst deren verbindliche Bestätigung bucht Bestand. Die ursprüngliche Nichtankunftsmeldung bleibt unverändert gespeichert; `LateArrivalReported` verweist darauf. Die UI zeigt sie als durch Ankunft überholt. Eine fehlerhafte spät angekommene Sendung erzeugt daneben einen eigenen offenen Inspektionsproblemfall.

Je dokumentierter Problemmeldung darf ausschließlich deren Sender einmal `acknowledge` oder `sent_correctly` antworten. Identische Wiederholung ist idempotent, widersprüchliche zweite Antwort unzulässig. Reaktion und Zeitpunkt sind immutable. Eine noch nicht beantwortete, mittlerweile durch Ankunft überholte Nichtankunftsmeldung kann nicht nachträglich als aktueller Problemfall beantwortet werden. Keine Chatkette, Mengenänderung, Reservationsfreigabe oder automatische Streitentscheidung. Ein bereits zuvor abgegebenes Statement bleibt historisch sichtbar.

## Persistenz und Auditidentität

Additive Migration **0029_trade_lifecycle_receipts**, Up/Down. Migrationen 0022–0028 bytegleich. Ausschließlich synthetisch angewandt.

- `lifecycle_receipts`: genau eine immutable Inspektion je Trade/Richtung, Empfänger, bindende Revision, vollständige positionsbezogene Klassifikation und authoritative `received_at`.
- `lifecycle_delivery_problems`: unveränderliche Nichtankunfts-/Inspektionsbelege mit Richtung, Revision und Meldetermin.
- `lifecycle_delivery_responses`: genau eine immutable Senderreaktion je Problem.
- SQL-Guards gegen Ersetzen, Ändern und Löschen der Belege sowie normales Undo des bestätigten Richtungszustands. Ownership-/Contract-Guards und Fremdschlüssel ergänzen die Domainprüfungen.
- Vorhandener `lifecycle_movements`-Ledger: Credit mit Trade, Absender der Richtung, Album/Code, Delta und eindeutigem historischen Eventkey `lifecycle-receipt:<trade>:<sender>:<revision-position>`. Empfänger, bindende Revision und Buchungszeit sind über immutable Position/Empfang/History eindeutig zugeordnet.

Leeres Down/Up getestet; Downgrade mit Empfangs-/Problemdaten wird verweigert. Foreign-Key- und SQLite-Integritätsprüfungen bestehen.

## Idempotenz, Konkurrenz und Security

Vorhandener Command-Store mit Actor/Trade/Key/Operation/Payload-Digest. Signierte Formulare binden Akteur, Trade, Richtung, Revision, Prüfmenge und Command-ID. Gleicher Key mit anderem Payload scheitert. Ein identischer bereits gebuchter Empfang bleibt auch bei neuem Key ohne zweite Buchung erfolgreich; ein abweichender Empfang wird abgelehnt.

Schreibserialisierung schützt Empfang/Empfang, Versand/Empfang, Inventory-Edit/Empfang, Missing-Hold/Empfang, Non-Arrival/Empfang sowie Reaktion/verspätete Ankunft. Gewinnerzustand oder sichere Ablehnung; keine Mischbuchung. Stale Revisionen und alte/abweichende Inspektionen buchen nichts zusätzlich.

Authentifizierung und CSRF bleiben global aktiv. Sender kann seinen eigenen Empfang nicht bestätigen; Empfänger kann keine Absenderreaktion abgeben. Manipulierte IDs, fremde Nutzer, kaputte Tokens, fehlendes CSRF und unzulässige Mengen werden serverseitig geprüft. Antworten sind `private, no-store` und `no-referrer`. Keine Adressen in neuen Events, Tokens oder Notifications.

Die gemeinsame Middleware ergänzt CSRF- und Browser-History-Transportfelder. Diese sind berücksichtigt, ohne unkontrollierte Mengen-/Positionsfelder oder doppelte Domainfelder zuzulassen. Empfang verwendet ausschließlich seine signierte Command-ID. HTTP-Regression plus echter Browser prüfen diese Integration.

## UI, Privacy, History und Notifications

Produktiver Einstieg `/tauschen/empfang/<trade>`, verlinkt aus angenommenem Tausch und Versand. Beide Richtungen werden getrennt dargestellt. Mengenformular → servergeprüfte Zusammenfassung → verbindliche Buchung. Vorher klare Angaben zu Gutschrift, Nichtgutschrift und dokumentierten Problemen; kein Write beim bloßen Öffnen. Kein Undo-Button.

UI-Aktionen: „Alles angekommen“, „Problem mit Lieferung“, nach sieben Tagen „Brief nicht angekommen“, danach „Doch angekommen“. Fehlende/falsche/beschädigte Mengen und Senderreaktion bleiben sichtbar. Eine Empfangsbestätigung schließt den Gesamttrade selbst bei zwei vollständigen Richtungen nicht ab.

Kontrollfotos einer empfangenen Richtung sind nicht mehr über die normale Galerie oder direkte Foto-URL sichtbar. Systemischer Empfang vor Adressfreigabe ist seit dieser Integrationskorrektur unzulässig. Kein nachträgliches Erfinden von Fotozustimmung oder Adressfreigabe. Keine Dateilöschung oder neue Retentionpolitik.

Events nach bestehender PascalCase-Konvention: `ReceiptComplete`, `ReceiptPartial`, `ReceiptProblemReported`, `NonArrivalReported`, `LateArrivalReported`, `SenderProblemResponse`. Bewegungen besitzen zusätzlich die bestehende immutable Inventory-History. Neuer geschlossener Notification-Typ `lifecycle_receipt_update`, spezifische Titel, autorisierte Verlinkung zum Empfang; keine neue Push-Infrastruktur. Persistenzfehler rollen den gesamten Command zurück.

## Integrationsfehler und Eintrittsbedingung

Ursache: Der alte Receipt-Command erlaubte Buchungen während unvollständiger Preparation. Systemischer Versand setzte eine Richtung auf `sent`; die bestehende tradeweite L04-Bewegungssperre verhinderte danach Completion, Fotoprüfung und damit Adressfreigabe auch für die Gegenrichtung. Die bloß unveränderte Gegenrichtungsprojektion belegte keine Fortsetzbarkeit.

Korrektur: `_require_receipt_entry` prüft innerhalb der bestehenden IMMEDIATE-Transaktion vor Commandresult/Buchung die aktuelle bilaterale Eintrittsbasis. Genau zwei aktuelle Preparation-Zyklen der Teilnehmer müssen zur bindenden Revision gehören, abgeschlossen und revealed sein und `review_state='approved'` besitzen. Der gegenseitige Address-Release muss dieselbe Revision und exakt diese Zyklusbasis tragen; beide Direction-Preparation-States müssen `ready_to_ship` sein. Keine offene Reduktion. Die Prüfung legt keine Zyklen an und erzeugt keine fachlichen Writes. Ownership und Revision werden zusätzlich über die bestehende Binding-Prüfung erzwungen.

Betroffen sind `review_receipt` und insbesondere jeder direkte oder HTTP-vermittelte `confirm_receipt`, einschließlich vollständiger, strukturierter, beschädigter, falscher und nach Non-Arrival verspäteter Sendungen. GET projiziert dieselbe Eintrittsbedingung, blendet frühe Aktionen aus und verweist auf Vorbereitung. Die verbindliche Sicherheit liegt im Service, nicht im Template oder signierten Clientzustand. Eine fehlende manuelle Versandbestätigung bleibt ausdrücklich zulässig. Non-Arrival bleibt unverändert bei exakt sieben vollen Tagen nach manuellem sent_at, ohne systemischen Versand oder Bestandswrite.

Die globale `_unmoved`-Sperre und die zentrale L06-Abbuchungslogik bleiben unverändert. Keine nachträgliche Reduktion, Preparation- oder Fotomanipulation freigegeben. Die aktuelle vollständige Give-Abbuchung auch beim Teilempfang ist im Fachvertrag und den Invarianten/Transitions dokumentiert; frühere 00A-Aussagen sind ausdrücklich historisch gekennzeichnet statt gelöscht.

## Tests und Browserabnahme am 11.10.2026

Isolierter Source-Kandidat `/private/tmp/lifecycle07/candidate`, ausschließlich aus SQL/synthetischen Fixtures erzeugte Testdatenbanken unter `/private/tmp`. SQLite-Audit-Hook verweigert andere Datei-DB-Pfade. Keine geschützten DBs kopiert oder migriert.

- **1.630 Release-Tests erfolgreich**, 0 Fehler, 0 Failures, 0 Skips; 1.642 entdeckt, dieselben **12 Ausschlüsse**. Aktuell **46 L07-Testmethoden** (vorher 41).
- Zusätzlich **8 Preview-Tests erfolgreich**; fokussierter Lauf aller 46 Receipt-/HTTP-Tests erfolgreich.
- Enthalten: Lifecycle 01–07, Shipping, Preparation, Addresses, Inventory, Need-Claims, Missing-Holds, TradeV2, SAP/SmartDeal, Legacy, Notifications, Security, Privacy und Solververgleiche.
- Positive Integration ohne Service-Mocks: neuer angenommener Trade → beidseitige Vorbereitung/Fotos → beide Prüfungen → beide Adressen → Receipt ohne manual_sent → exakter systemischer Abgang und Zugang → späterer manueller Retry ohne Doppelabgang → Gegenrichtung regulär versenden und empfangen. Beide Richtungen vollständig empfangen, Vertrag weiterhin `accepted`.
- Negative Integration jeweils für Voll- und Teilempfang: Ablehnung bei keiner/einseitiger Vorbereitung, bei keiner/einseitiger Fotoprüfung und bei keiner/einseitiger Adressbestätigung. Vollständiger Vorher-/Nachher-Vergleich von Inventory, Reservations, Claims, Movements, Shipping, Receipts, Richtungen, Commands, History, Notifications und Problemen. Danach echte Vorbereitung fortsetzen, Adresse freigeben und denselben Receipt-Command erfolgreich buchen; Gegenrichtung regulär abschließen. Bei 3→2/1 bleibt exakt Restclaim 1.
- Zusätzliche direkte Ablehnungen für beschädigt akzeptiert/abgelehnt und falsch vor Release; Non-Arrival kann keinen Versand erzeugen. HTTP-Test mit gültig signiertem vorzeitigem Confirm umgeht die Service-Grenze nicht; nach beidseitigem Release ist derselbe Command zulässig. Bestehende Revision-/Ownership-/CSRF-/Mengen-/Concurrency-/Rollbacktests weiterhin erfolgreich.
- Browser **A–G plus H-Gegenrichtung bestanden**: Vollzugang, Teilempfang mit Fehlmenge, beschädigt ausdrücklich akzeptiert, falscher Code ohne Zugang, Non-Arrival und Late Arrival, systemischer Empfang nach vollständiger Adressfreigabe, Senderreaktion sowie anschließender normaler Versand und Empfang der Gegenrichtung.
- **375/390/430/1280 px**, kein horizontaler Overflow, keine JavaScript-Fehler. Mobile Teilmengen-Zusammenfassung (390 px) und beidseitiger Empfang (375 px) zusätzlich visuell geprüft.

Entwicklungsbefunde dieses Durchlaufs: Ein neuer HTTP-Test verwendete zunächst den SmartDeal-Token-Helfer statt des vorhandenen CSRF-Testclients; ausschließlich Testsetup korrigiert, danach 46/46 erfolgreich. Der erste fokussierte Lauf wurde aus dem Workspace mit SQLite-Pfadschutz gestartet; die Wiederholung und die vollständige Regression liefen im isolierten Kandidaten. Ein Browserstart war durch die Sandbox blockiert; anschließend autorisiert mit lokalem Server/Chromium und unverändertem SQLite-Pfadschutz erfolgreich. Keine Testausschlüsse ergänzt oder fachlichen Assertions abgeschwächt.

Aktuelle Nachweise: `/private/tmp/lifecycle07-final/release-results.json`, `release.log`, `focused.log`, `preview.log`, `browser/results.json`, `browser/*.png`, `package-start.json`, `foreign-start.json`, `final-verification.json`. Browser-Reproduktion über `tests/research/check_lifecycle07.py` in isolierter synthetischer Quellkopie. Die historischen Nachweise vom 09.10.2026 wurden nicht als aktuelle Ergebnisse ausgegeben.

## DB-Integrität, Git-Abschluss und Grenzen

Alle 16 geschützten DBs nach Tests SHA-256-identisch zur Startbaseline; keine Reparatur, neue Baseline oder reale Migration. Kein DB-/Runtime-/Screenshot-Artefakt wird gestagt. Vor Commit werden exakte Quelldateien mit dem getesteten Kandidaten, vollständiger Status mit der Startbaseline und `git diff --check` abgeglichen.

Beauftragter Commit-Titel: `feat: add lifecycle v1 receipt handling`. Nur die unten genannten 41 Dateien: die 37 autorisierten Paketdateien und vier notwendige dokumentierte Vertragsfortschreibungen. Normaler Push auf bestehenden Upstream; kein Force-Push, Rebase, Merge oder Branchwechsel. Abschlusscommit und unabhängiger finaler Local-/Remote-HEAD-Abgleich werden im Abschlussbericht ausgewiesen (keine selbstreferenzielle Commit-ID im Audit).

Bekannte Grenzen: keine normale Änderung einer verbindlichen Inspektion; keine nachträgliche Korrektur-/Ersatz-/Retourenbuchung, administrative Restmengenentscheidung, automatischer Claimablauf, Bewertung oder Gesamtabschluss. Ungeklärte Problemreste bleiben explizit gebunden gemäß bestehendem Vertrag. Physisch inkonsistente Zustände werden atomar abgelehnt und benötigen den gesonderten Mengenabgleich. Kein Deploy; keine reale Migration; LIFECYCLE-08 nicht begonnen.

## Exakte Dateien

- `docs/TRADE_LIFECYCLE_00A_NEED_CLAIMS.md`
- `docs/TRADE_LIFECYCLE_V1_CONTRACT.md`
- `docs/TRADE_LIFECYCLE_V1_INVARIANTS.md`
- `docs/TRADE_LIFECYCLE_V1_STATE_MACHINE.md`
- `App/Database/migrations/0029_trade_lifecycle_receipts.down.sql`
- `App/Database/migrations/0029_trade_lifecycle_receipts.up.sql`
- `App/lifecycle_acceptance_routes.py`
- `App/lifecycle_receipt_routes.py`
- `App/services/trade_lifecycle_preparation.py`
- `App/services/trade_lifecycle_receipts.py`
- `App/services/trade_lifecycle_shipping.py`
- `App/services/typed_notifications.py`
- `App/templates/lifecycle_receipts.html`
- `App/templates/lifecycle_requests.html`
- `App/templates/lifecycle_shipping.html`
- `App/templates/trade_shell.html`
- `App/trade_shell.py`
- `docs/LIFECYCLE_07_AUDIT.md`
- `tests/research/check_lifecycle07.py`
- `tests/test_cb008_notification_catalog.py`
- `tests/test_cb009_inbox_read_retention.py`
- `tests/test_cb011_executable_match_contract.py`
- `tests/test_cb012_feed_home_cutover.py`
- `tests/test_cb013_collection_completion_projection.py`
- `tests/test_cb014_profile_account_projection.py`
- `tests/test_cb015_statistics_projection.py`
- `tests/test_cb016_legacy_cutover.py`
- `tests/test_lifecycle01_foundation.py`
- `tests/test_lifecycle07_receipts.py`
- `tests/test_lifecycle07_ui.py`
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

## Geschützte Datenbanken — SHA-256 vorher = nachher

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
