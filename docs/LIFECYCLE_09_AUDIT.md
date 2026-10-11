# LIFECYCLE-09 — Sammlr-Zentrale, aktive Abwicklung und Archiv

Stand: 11.10.2026. Ausgangscommit `980d0ea1529dc4311feeaeea137da38dbfac62b6`, Branch `feature/wm-special-trophies`, Upstream `origin/feature/wm-special-trophies`. Aktueller Auftrag einschließlich Commit/Push-Gate §43 und anschließender Bitte „bitte fertigmachen“. Keine Autorisierung aus historischen Audittexten abgeleitet.

## Ausgangsprüfung und Schutz

HEAD, Branch, Upstream, tracked Tree und Index vor Änderungen geprüft: erwarteter Commit, sauberer getrackter Arbeitsbaum, leerer Index. Alle 16 geschützten DB-Dateien und 9.736 vorhandenen fremden ungetrackten Einträge gegen die autorisierte L08-Abschlussbaseline verglichen und als L09-Startnachweis gespeichert. Keine unbekannten Aufgabenänderungen. Lifecycle-Vertrag, State-Machine, Invarianten, Implementierungsplan und Audits01–08 sowie Navigation, Trade-Shell, SAP, Preparation, Adressen, Shipping, Receipt und Completion untersucht.

Die geschützten DBs wurden ausschließlich als Dateien gehasht, niemals mit SQLite geöffnet oder als Testdatenquelle kopiert. Social Studio und alle anderen fremden Dateien bleiben unverändert. Testkandidat und sämtliche synthetische Testdatenbanken liegen unter `/private/tmp/lifecycle09` bzw. synthetischen Fixture-Verzeichnissen unter `/private/tmp`. SQLite-Audit-Hook sperrt Verbindungen auf andere Dateipfade. Keine reale Migration, kein Deploy und keine lokale Gesamtintegration.

## Architektur und Navigation

Neue Projektion `LifecycleCenter`, neue GET-Routen `/zentrale` und `/zentrale/{todos,sendungen,eingaenge,archiv}`, eigenes Template und eng begrenztes CSS innerhalb der bestehenden Trade-Shell. Keine neue Command-Engine, POST-API, Inventory-/Claimmanipulation, Shippingfinalisierung, Receiptbuchung oder Ratingpersistenz.

Die drei bestehenden Hauptziele bleiben Sammlung, sammlr., Tauschen. Nur das mittlere Ziel ändert sich von `/` auf `/zentrale`; keine vierte Navigation. Die operative Vorbereitung/Adress-/Versand-/Empfangs-/Abschlussansicht markiert jetzt sammlr. aktiv und verlinkt zurück zur Zentrale. SAP bleibt als Tauschen markiert; Sammlung und Suche/SmartDealalgorithmen sind unverändert. Der bisherige Feed unter `/` bleibt erreichbar, wird nicht zur operativen Zentrale umgebaut.

Wichtiger Integrationsbefund: `/zentrale` war schon als Sammlung-Weiterleitung registriert. Dieser konkurrierende Decorator wurde entfernt; die neue Route besitzt den Pfad eindeutig. `/sammlr-zentrale` leitet auf `/zentrale`. Bei Schema ohne L08 bleibt der frühere Sammlung-Rückfall erhalten, ohne automatische Migration. Diese Compatibilitygrenze ist separat getestet. Mit Schema0030 ist die Zentrale vollständig aktiv.

## Drei Bereiche und Aktionsprojektion

Gelbe To-dos, rote Sendungen und grüne Eingänge zeigen je höchstens drei Vorschaukarten und „Alle anzeigen“. Jede Karte beschreibt einen Trade, nicht eine Stickerposition: Gegenpartei, Albumname(n), stabile Trade-ID, bindende gerichtete Mengen, Zustand, zulässige Aktion/Warten und relevante Frist. Keine Vollstickerliste, Adresse, Kontrollfoto oder fremder interner Inventorywert wird geladen oder ausgeliefert.

Eigene konkrete Aktionen werden aus akzeptierter Revision, aktuellen Preparation-Zyklen, Foto-Vorhandensein/Reviewstatus, Reduktionen, Missing-Holds, aktueller Adressbasis, Versand-/Receipt-/Problem-/Resolutionfakten und eigener Eligibility abgeleitet:

- Eigene Sticker prüfen/Fotos hochladen bzw. Vorbereitung abschließen; bei Fotoproblem eigene Korrektur.
- Fremdes Fotopaket nur bei beidseitig vollständig revealed und noch nicht entschiedenem Review prüfen.
- Reduktionsvorschlag nur der zustimmungsberechtigten Gegenseite als Prüfung anbieten; Vorschlagender wartet. Fehlmengen/abgelehnte Reduktion führen zur bestehenden Korrekturansicht.
- Eigene Adresse erst bei vollständiger gültiger bilateraler Vorbereitung/Fotoprüfung und ohne blockierende Reduktion/Fehlmenge auswählen. Bestehende gültige eigene Auswahl wartet auf die Gegenpartei; kein erfundener zusätzlicher Freigabeklick.
- Eigenen Versand nach Release bestätigen; Receipt erst nach aktueller bilateraler Releasebasis. Wie in L07 darf tatsächlicher Empfang auch ohne manuellen Versandklick geprüft werden.
- Senderreaktion nur bei eigener noch ungelöster Problemmeldung ohne bisherige Reaktion; freiwillige Problemakzeptanz nur für eigene verbindliche Probleminspektion.
- Nichtankunft erst nach sieben Tagen bestätigten manuellen Versands, endgültiger Problemabschluss erst nach14 Tagen Problemzeit. Keine doppelte Nichtankunftsmeldung und keine Aktionen auf supersedierten/finalen Richtungen.
- Eigene Bewertung nur innerhalb des gültigen persönlichen Fensters und ohne schon abgegebene Bewertung.

Alle Links führen zum konkreten bestehenden Tradeformular. Serviceguards bleiben verbindlich und prüfen beim tatsächlichen Command erneut; ein Zustand kann zwischen Lesen und Klick fortschreiten. Keine Fotos/Adressen durch eine Kartenprojektion freigegeben. Sendungen zeigen nur den nächsten passenden ausgehenden Schritt, Eingänge nur einen passenden eingehenden Schritt; die To-do-Karte bündelt alle eigenen zulässigen Aktionen. Warten ist kein anklickbarer ausführbarer Auftrag.

## Priorisierung und Fristen

Sortierung vollständig auf dem Server. A: eigene überfällige oder in höchstens sechs Stunden fällige Aktionen; B: andere aktuell zulässige eigene Aktionen; C: aktive Karten ohne eigene Aktion, mit Wartestatus in Sendungen/Eingängen. Innerhalb der Klasse maßgebliche Deadline, ursprünglicher Annahmezeitpunkt, stabile Trade-ID. Mehrere Aktionen einer Karte werden ebenfalls deterministisch geordnet. Es gibt kein ausschließlich clientseitiges Sortieren.

72h Vorbereitung ab authoritative accepted_at; 72h Versand ab released_at; sieben Tage Nichtankunft ab manuell bestätigtem sent_at;14 Tage Problemabschluss ab reported_at;14 Tage Rating ab eigener Eligibility. UTC-Serverzeit entscheidet, Anzeige in Europe/Berlin mit Zeitzone. Anfragefrist72h verbleibt im unveränderten SAP-/Requestprozess, nicht auf angenommenen Zentrale-Karten. Die14-Tage-Problemgrenze ist ein frühester erlaubter Zeitpunkt, keine behauptete Überfälligkeit. Exakt am Bewertungsende verschwindet die Abgabeaktion. Keine Sanktion, Bestandsänderung oder neue Frist durch Dashboardreads.

## SAP-Übergang, aktive Richtungen und Archiv

Bei vorhandenem L08-Schema führt erfolgreiche Acceptance direkt zur konkreten Vorbereitung in der Zentrale-Navigation. Angenommene V1-Anfragen werden aus `/tauschen/laufend` gefiltert; offene Anfragen und Gegenangebote bleiben erhalten. Auf älteren Schemas bleibt der bisherige Einstieg in die Abwicklung zugänglich. Legacy-Requestlisten, ihre Verträge und Notifications werden nicht pauschal gefiltert oder umgedeutet. Der SmartDeal-/Suchalgorithmus bleibt bytegleich.

Sendungen und Eingänge verwenden ausschließlich die aktuelle bindende accepted_revision. Erfolgreiche Mengenreduktion wird sofort richtig angezeigt; alte Angebotsmengen werden nicht verwendet. Die Richtungen bleiben unabhängig: vorbereitet, versandbereit, überfällig, versendet/unterwegs, Empfang bestätigt, Teil-/Problemempfang, Nichtankunft, endgültiger Problemabschluss. Late Arrival verdrängt nur den aktiven Nichtankunftsstatus, nicht die unveränderliche Problemhistorie.

Nach L08-Completion verschwinden beide aktiven Richtungskarten. Das Archiv zeigt Gegenpartei, Alben, Abschlussdatum, Erfolg/Problem, bindende Give-/Receive-Mengen, tatsächlich bestätigte Empfangsmengen beider Richtungen und Anzahl dokumentierter Lieferprobleme. Die konkrete Abschlussansicht enthält unveränderte Inspektions-/Problemhistorie und zulässige Ratingdetails. Kein Löschen oder neue Archivpersistenz.

Ein archivierter Trade mit offenem eigenen Bewertungsfenster erzeugt ausschließlich die Bewertungskarte unter To-dos, keine neue aktive Sendungs-/Eingangskarte. Nach Bewertung oder Fristablauf verschwindet auch dieses To-do; das Archiv bleibt zugänglich. Empty States lauten „Alles erledigt.“, „Du hast aktuell keine offenen Sendungen.“ und „Du erwartest gerade keine Sticker.“

## Zeitabhängige L08-Nachführung und Blindheit

`LifecycleCompletion.refresh_for_actor` bündelt die Suche nach wirklich ausstehenden L08-Fakten: historische Receipts ohne Eligibility/saubere Resolution sowie fällige noch nicht materialisierte Ratingpublikationen. Nur eigene Trades sind Kandidaten. Die existierenden `settle_receipts`-/`_publish_ratings`-Primitiven laufen in ihrer IMMEDIATE-Transaktion; kein Aufruf eines Receipt-/Claim-/Inventorycommands. Reguläre Projektionen laden nicht je Trade das gesamte Completiondetailmodell.

Damit werden schon beidseitig empfangene L07-Altstände beim Zentralelesen korrekt abgeschlossen/archiviert und fällige Reveal-Ereignisse genau einmal nachgezogen. Neue Fristen werden auch ohne Materialisierung direkt aus der aktuellen Serverzeit berechnet. Die L08-Revealbedingung selbst ist unverändert: beide Ratings oder tatsächlich abgelaufene Gegenfrist; nie gestartete Gegenfrist bleibt offen. Keine Bewertungswerte in Karten, Badges, HTML/JSON-Modellen oder Archivlisten, auch nicht nach Reveal. Sichtbare Einzelwerte liegen ausschließlich in der autorisierten bestehenden L08-Detailansicht. Eigene Eligibility benötigt keine Kenntnis des fremden Ratingwerts.

## Privacy, Ownership und Sicherheit

Actor kommt ausschließlich aus der geprüften Session; aktiver Account erneut im Service geprüft. Rootquery beschränkt die Auswahl auf requester/partner. Alle Batchleser sind auf genau diese ausgewählten Trade-IDs beschränkt. URL-Parameter können keinen anderen Owner bestimmen. Ungültige Listen/Paginierung werden abgewiesen; keine Dashboard-POST-Commands. Fremde Detail-ID bleibt durch bestehende Services404/403-geschützt.

Listenselektion enthält keine Adressfelder, Fotopfade, Inspektionspayloads oder Sterne/Tags. Adressmetadaten umfassen nur Revisions-/Basisidentität zur Aktionsberechtigung; Fotometadaten nur aktuelle Cyclefakten und EXISTS eines eigenen gültigen Fotos. Kein fremder Inventoryquery. Jinja escaped Benutzer-/Albumnamen; XSS-Sentinel geprüft. Listenantworten `private, no-store` und `no-referrer`. Bestehende CSRF-, Signatur-, Snapshot-, Retention- und Endzustandsregeln für Detailaktionen bleiben unverändert.

## Skalierung und Performance

Vorschau drei Karten je Bereich; vollständige Listen zwölf Trades pro Seite. Serverseitige Auswahl, Sortierung und Pagination, keine hunderte Karten im DOM. Archive: SQL COUNT sowie LIMIT/OFFSET vor Laden der Batchmetadaten. Aktive Portfolio-/To-do-Sortierung liest kompakte aggregierte Metadaten, sortiert global und schneidet die zwölf sichtbaren Karten serverseitig aus. Alte archivierte Trades ohne offenes eigenes Ratingfenster werden dafür bereits im SQL ausgeschlossen (grober15-Tage-Vorfilter, exakte14-Tage-Prüfung im Projektor).

Mengen werden im SQL je Trade/Richtung/Album aggregiert, keine Code-/Stickerlisten. Metadatentabellen werden gebündelt gelesen, höchstens400 Trade-IDs pro Chunk zur Einhaltung der SQLite-Parametergrenze. Für30 aktive Trades weniger als25 SELECTs statt einer Detailansicht pro Trade. Queryzahl wächst mit Chunks, nicht je Trade. Der seltene L08-Nachholpfad materialisiert erforderliche bestehende Domainereignisse pro betroffenem Trade; das ist bewusst getrennt vom regulären Batchread. Keine zusätzliche Persistenz/Cache und kein Hintergrundjob.

Bewusste Skalierungsgrenze: exakte globale To-do-Priorisierung benötigt derzeit Metadaten aller aktiven Trades des Nutzers; Speicher-/Sortierkosten wachsen mit diesem aktiven Portfolio. Die ausgelieferte Ansicht ist immer begrenzt, Archive werden schon im SQL paginiert.30 aktive und26 abgeschlossene Trades sowie mehrere Aufgaben pro Trade sind synthetisch geprüft; kein Lasttest mit Millionen aktiver Trades behauptet.

## UI und Browser

Bestehende globale Typografie, Flächen-/Text-/Statusfarb-, Abstand- und Radiustokens; keine Fonts oder Libraries ergänzt. Ruhige gelb/rot/grüne Flächen ohne Rotation/3D, desktop drei Spalten und mobil untereinander. Richtungsbezogene nächste Aktionen verhindern dreifache volle To-do-Listen. Links mindestens44px hoch, Umbruch langer Inhalte, Bottom-Navigation-Sicherheitsabstand. Angezeigte Mengen bleiben kompakt.

Echter Chromium-/Flask-Browserlauf deckt A–J ab: mittlere Navigation, aktive Aufgaben, Sendungen/Eingänge, Vorbereitung-Deep-Link, offene SAP-Anfrage annehmen und aus aktiver SAP-Liste entfernen, beidseitigen Receipt abschließen und archivieren, Bewertung trotz Archivierung, Blindheit vor zweiter Bewertung und Reveal danach,30 Trades/Vorschau/Pagination mit disjunkten Seiten. Fremde Abschluss-ID404. Zehn Flussstationen jeweils bei **375/390/430/1280px**, keine JS-Fehler, kein horizontaler Overflow. Touchgrößen und unterste Aktionen oberhalb der Bottom-Navigation automatisiert geprüft. Mobile Übersicht und Desktopansicht mit30 Trades zusätzlich visuell geprüft.

## Tests, Migration und Entwicklungsbefunde

**Keine neue Migration0031. Alle bestehenden Migrationen0022–0030 unverändert.** Keine reale lokale Migration, kein Deploy. Neue Speicherung nicht erforderlich.

Abnahme: **1.690 Release-Tests erfolgreich**,1.702 entdeckt, **12 bestehende Ausschlüsse unverändert**,0 Failures/Errors/Skips. Zusätzlich **8 Preview-Tests erfolgreich**. **22 neue L09-Tests** (16 Projektion/Domain,6 HTTP) plus gezielter Compatibility-Schemagatetest im bestehenden CB016-Modul. Die L09-Tests sind im Release-Ergebnis enthalten, nicht zusätzlich zu addieren.

Abgedeckt: Empty/Einzel-/Viele-Trades, eigene/fremde Rollen, gesperrte Preparation und wartende Gegenpartei, gegenseitiges Fotoreview/Korrektur, Adressauswahl, exakte72h-/7d-/14d-Grenzen, keine frühe Nichtankunft/Schließung, Ratingexpiry/Blindheit/Reveal, alte L07-Abschlüsse ohne Bestandswrite, Problemarchiv, bindende Reduktionsmengen, SQL-Payloadausschluss,30 aktive/26 archivierte Trades, stabile Sortierung und disjunkte Pagination, XSS, POST-Abweisung, parametermanipulierter Owner, SAP-Offen/Counter/Accepted-Übergang, Archivrating und Detailownership. Vollregression Lifecycle01–09, TradeV2/Inventory/Reservations/Claims/Missing-Holds, SAP/SmartDeal, Shipping/Receipt/Completion, Ratings/Profiles/Notifications, Legacy/Privacy/Security und Preview.

Zwischenbefunde wurden korrigiert: bestehender `/zentrale`-Redirect konkurrierte mit neuer Route; Jinja-Dictschlüssel `items` benötigte explizite Indexnotation; neue synthetische Fixture benötigte ihren Adresscommand-Zähler; der Reduktionstest musste den betroffenen Trade statt anderer paralleler Aufgaben prüfen. Historische Navigationstests erwarten jetzt den beauftragten mittleren Link. Ein direkter Zwischenlauf eines alten ganzen UI-Moduls enthielt auch dessen bereits im12-Ausschlussvertrag dokumentierten fehlenden Screenshotmanifest-Test; er ist kein neuer Ausschluss und die abschließende Release-Abnahme nutzt exakt den unveränderten Vertrag. Keine fachlichen Legacy-Assertions abgeschwächt.

Nachweise: `/private/tmp/lifecycle09/{git-start.txt,db-start.json,foreign-start.json,focused.log,release.log,release-results.json,preview.log,browser.log,browser/results.json,final-verification.json}` und Browser-PNGs. Reproduktion des Browsers über `tests/research/check_lifecycle09.py` ausschließlich in isolierter synthetischer Quellkopie.

## Integrität, Git und Grenzen

Alle16 geschützten DB-Hashes nach den Prüfungen identisch zur autorisierten Startbaseline. Alle9.736 fremden ungetrackten Dateien/Symlinkziele unverändert; keine unbekannten neuen Aufgabenartefakte. Keine DB-, Foto-, Runtime-, Screenshot- oder Social-Studio-Datei im Commit. Getesteter Kandidat und exaktes Quellenmanifest werden vor Staging bytegleich geprüft; `git diff --check` erfolgreich.

Commit nur nach grüner Abnahme: `feat: add sammlr lifecycle command center`, ausschließlich die unten aufgeführten25 Dateien. Normaler Push auf bestehenden Upstream, unabhängiger Remote-HEAD-Abgleich, danach tracked Tree sauber und Index leer. Abschlusscommit/Remote-Nachweis stehen im Abschlussbericht, ohne selbstreferenzielle Commit-ID im Audit.

Keine festgestellten Abnahmeblocker. Bekannte Grenzen sind die beschriebene aktive Metadatensortierung und synchrone L08-Nachführung bei ausstehenden Fakten. Bestehende Schema-/Launch-/Foto-/Adressretentiongrenzen werden nicht erweitert. Schema ohne L08 erhält den bisherigen Sammlung-Rückfall. Kein Scheduler, Messenger, Suchumbau oder weiteres Trade-System. **Kein Deploy, keine reale Migration; lokale Gesamtintegration nicht begonnen.**

## Exakte Dateiliste
- `App/lifecycle_acceptance_routes.py`
- `App/lifecycle_center_routes.py`
- `App/services/lifecycle_center.py`
- `App/services/trade_lifecycle_completion.py`
- `App/static/lifecycle_center.css`
- `App/templates/lifecycle_addresses.html`
- `App/templates/lifecycle_center.html`
- `App/templates/lifecycle_completion.html`
- `App/templates/lifecycle_preparation.html`
- `App/templates/lifecycle_receipts.html`
- `App/templates/lifecycle_shipping.html`
- `App/templates/trade_shell.html`
- `App/trade_shell.py`
- `App/webapp.py`
- `docs/LIFECYCLE_09_AUDIT.md`
- `tests/research/check_lifecycle09.py`
- `tests/test_cb016_legacy_cutover.py`
- `tests/test_lifecycle09_center.py`
- `tests/test_lifecycle09_ui.py`
- `tests/test_s04_home_collection_routes.py`
- `tests/test_s05_three_area_navigation.py`
- `tests/test_s31_ui_foundation.py`
- `tests/test_s37_beta_polish.py`
- `tests/test_uif002_global_app_shell.py`
- `tests/test_uif_current_state_product_integration.py`

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
