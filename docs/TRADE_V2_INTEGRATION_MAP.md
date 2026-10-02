# Trade-v2 – Productive Integration Map

Stand 2026-10-02. Ausschließlich statische Analyse; keine Integration oder Freigabe eines Deployments. Belegpfade sind repository-relativ. Maschinenlesbare Bestandsaufnahme: `tests/research/artifacts/integration-00/`.

## Repository und belastbare Ausgangsbasis

Branch `feature/wm-special-trophies`, HEAD `1c0ecca` (`feat: separate home and collection routes`). HEAD ist Vergleichsbasis, kein nachgewiesener produktiver Deploymentstand. Weitere relevante Commits: `3ccf77d` Tradeflow-Regression, `4521151` S00-Referenz, `d75186c` Papier/Wall/Liste, `9e6887f` und `c6d6d24` Trade-Papier-/Listen-UX. Vollständige 20-Commit-Liste, Indexdateien, lokale Dateien, Status und Änderungsumfang stehen in repository-state.json.

227 Dateien sind im Index; 5.138 weitere erfasste Dateien sind nicht im Index (Union aus Git-untracked und zusätzlich erfassten App-Dateien, daher nicht gleichbedeutend mit 5.138 Git-status-Zeilen). Alle 51 Trade-v2-Dateien und die TRADE-00–11-Vertrags-/Auditdokumente sind lokal/untracked. Auch große Teile der Service-/Migrationsschicht sind nicht versioniert. Der bisherige Commit allein reproduziert diesen geprüften Stand nicht.

Bereits vorher verändert: unter anderem App/webapp.py (+10013/−4396), App/static/style.css (+6049/−778), lokale DB, trophy_definitions.py, requirements.txt, drei Regressionstests, Roadmap-/Entscheidungsdokumente und DS_Store-Dateien. App/services/notifications.py ist bereits lokal geleert (−20); die aktuelle App verwendet separate Typed-Notifications. Nicht reparieren. Die exakte vollständige Dateiliste und diff-numstat sind maßgeblich, nicht diese Auswahl. Vor Integrationsänderungen muss ein ausdrücklich abgegrenzter, reproduzierbarer Ausgangsstand samt bestehender Änderungen festgehalten werden; INTEGRATION-00 stagt oder committet ihn nicht.

## Produktive Architektur

`Procfile`: `cd App && gunicorn --workers 1 --bind 0.0.0.0:${PORT} --access-logfile - --error-logfile - webapp:app`. `App/webapp.py` erzeugt global Flask (keine App-Factory), enthält Routes, Inline-Templates und Serviceadapter. `App/sticker_list.py` registriert vier zusätzliche Routen per add_url_rule. route-map.json enthält die expliziten Registrierungen einschließlich isolierter Trade-v2-Routes; automatisch erzeugte static/HEAD/OPTIONS sind keine zusätzlichen fachlichen Endpunkte.

`services/runtime_operations.py` verlangt in Produktion `/var/data/sammlr.db`, SAMMLR_ENV/Secret/Port und Schema-Version20 über schema_migrations. Lokal verwendet webapp standardmäßig `App/Database/sammlr.db`. Das produktive Ziel ist aus Code bestimmt; Remote-Volume/Deployment wurden nicht angefasst und dessen tatsächlicher Stand ist hier nicht attestiert. Die lokale DB wurde ausschließlich mit SQLite mode=ro&immutable=1 auf Schema und Migrationsledger untersucht. Ledger1–20, PRAGMA user_version0 (nicht die fachliche Versionsnummer), 76 Schemaobjekte; keine WAL-Sidecars vorgefunden. Quelle0021 existiert, ist lokal nicht angewendet. App-Import/Serverstart könnte Initialisierung auslösen und wurde bewusst nicht ausgeführt.

### Identität und Schutz

Kanonisch ist `users.id`. `current_user_id()` hat einen Default1, ist allein deshalb kein Sicherheitsguard. Der globale before_request-Guard verlangt für nicht öffentliche Endpunkte Session-Login, aktive Identität/Auth-Version und bei POST CSRF. Produktionscookies sind Secure/HttpOnly/SameSite Lax. Neue Tradeadapter müssen darunter laufen und zusätzlich jede Ressource serverseitig auf Teilnehmer und Aktionsrolle prüfen. Kein `role`, Slug, Actorfeld oder Session-fixture aus dem Browser darf Autorisierung liefern.

### Inventar, Sammlung und Einstellungen

`albums`, `user_albums`, `stickers.quantity`, `services/albums.py`, InventoryReadService und Availability sind die vorhandenen Wahrheiten. Album-/Code-Resolver statt synthetischer Previewcodes verwenden. Zugeordnetes Exemplar, freie Doppelte, Reservierungen und Incoming Need/Transit bleiben getrennt. Physischer Bestand ist nicht gleich available. Schreiben läuft über Inventory-/History-Services und deren Event-Idempotenz, nicht direkte JS-Zahlen.

AlbumPrivacyService/CommunityService prüfen Sichtbarkeit, Account, Freundschaft/Blocks. `user_albums.visibility` (public/friends/private) und `trade_pool_enabled` sind verschiedene Freigaben. `users.favorite_album_id` ist vorhanden. Per-Album smartEnabled/crossAlbum gibt es im untersuchten Schema nicht; Manual Offer V1s globale OPEN-Präferenz ist ein Vertrag, keine vorgefundene Persistenz.

### Bestehende Trade-Domain

Legacy manuelles create_trade_request speichert singlealbum give/get JSON und reserviert erst bei Accept durch TradeReservationService. SmartDeal-V1 besitzt eigene atomare Submitbindung, Snapshotidentität, beide Supplyreservierungen, Incoming-Coverage und binding+24h. Sein Quota zählt nur offene ausgehende V1-Anfragen, nicht eingehende/angenommene/manuelle Vorgänge. trade_contracts kennt legacy/smartdeal_v1, unbekannte Typen werden abgewiesen; fehlende Spalte bedeutet Legacy. Neuer Tradevertrag darf nicht durch Herkunft MANUAL/SMART oder URL erraten werden.

SmartDealRuntime verweigert nicht implementierten physischen V1-Lifecycle ausdrücklich statt Legacy-Fallthrough. discover kann cleanup/Expiry auslösen: für neue Read-Models reine Reader/Planungsfunktionen verwenden. Der ältere smart_trade_requests-Service ist nicht der neue smartdeal_requests-Service. Bestehenden Optimizer und Revalidation erhalten; globale Topplanung (max5) und isoliertes Paarpotential sind nicht austauschbar.

Stickerliste POST `/album/<album_id>/liste/trade` ist ein direkter eigener Inventartransfer mit Mengenbuchung, kein Netzwerkangebot. Niemals als Submitroute des manuellen Composers verwenden.

### Versand, Empfang, Problem und Bewertung

TradeShippingService verbucht eigenen physischen Versand atomar, löst Reservierungen und setzt eigene Versandrichtung. Kein produktives strukturiertes Adress-/Tradefreigabemodell und keine versionierte Packprüfung gefunden. Profilprivacy ersetzt keinen adressbezogenen Teilnehmerzugriff.

TradeReceiptService und TradeProblemService verlangen heute Partner-SHIPPED. Das kollidiert für den neuen Zweig mit Q2, nicht mit einem Auftrag zur Legacyänderung. Q2 verlangt tatsächlichen Empfang auch ohne Versandklick, genau einmal physische Buchungen, niemals erfundene Versandbestätigung oder Slotfreigabe. Das braucht einen ausdrücklich versionierten Buchungsadapter.

Produktive Problempositionen erfassen expected/initial/resolution quantities und begrenzen deren Summe. Die Preview-Lösungsvorschläge sind nicht ohne weiteres derselbe Vertrag. Ratings sind heute immutable 1–5, Preview 1–3. Neue Skala getrennt versionieren. Typed Notifications/Tradeevents existieren; Q7s fachlicher Accept-Typ ist nicht durch eine bloße Previewmeldung produktiv implementiert.

## Frontend, kanonische Komponenten und Navigation

Produktiv: webapp-Inline-HTML, Profiltemplates, static/style.css, Stickerliste/Marker-/Glyphenassets. Die gemeinsame app_header/bottom_nav-Shell enthält Sammlung `/sammlung`, sammlr `/`, Tauschen `/trades`; Profil `/profil`, Account `/account`, Notifications. Mobile und Desktop sollen dieselbe autorisierte Navigation verwenden; es wird keine neue separate Desktop-Domain abgeleitet. Responsive Kartengeometrie bleibt kanonisch.

Trade-v2 importiert Pax-Rendering für Receive/Give sowie CSS und misst produktive Stickermaße über einen versteckten iframe. Das ist ein Previewadapter, kein Grund eine zweite Kartenphysik zu pflegen. Produktionsintegration muss dieselbe Karte und Layerfaces verwenden: Wallcap5, Tradecap10, −2/−2, gleiche z-index-Regeln. Post-it-Mengen16/20 und kanonische Stickerlisteninteraktion bleiben geschützt. Ab Menge10 wächst der sichtbare Stack nicht weiter. Keine CSS-Neugestaltung in dieser Phase.

Ziel `/trades`: drei Vorschläge, Alle Sammlr, Laufende Tausche. Preview-Navigation/Demobuttons entfernen, Templates an vorhandene Shell anschließen. Bestehende `/trade/<id>` und `/trades/<id>` nutzen Request-IDs bzw. legacy_trade_request_id: nicht still mit neuer Trade-PK verwechseln. Vertragsspezifischer Dispatcher und autorisierte Notification-Links müssen Legacy weiterhin korrekt öffnen. Backnavigation führt zum realen Ursprung (Partner/Übersicht), keine Query darf den Vertrag wählen. Neue Navigation erst cohort-/featureflag-gesteuert; ein Rollback versteckt neue Erstellung, lässt bereits gebundene neue Trades erreichbar.

## Gesamter isolierter Trade-v2-Zweig

Alle Dateien unten sind derzeit Previewcode, keine unmittelbar freigegebene Produktivimplementierung. Flags D/S/L/UI/Q = Demo-Daten / simulierter State / Domainlogik / Projektion oder UI / Preview-URL-Kopplung. Mischmodule bleiben ausdrücklich gemischt. JSON enthält zusätzlich Imports, Funktionen, Queryparameter, Zeilenevidenz und Hashes. CSS als UI ist keine Erlaubnis globale Styles blind zu kopieren.

| Datei | Tatsächlicher Zweck | D/S/L/UI/Q | Integrationsaktion |
|---|---|---|---|
| `App/trade_v2/__init__.py` | Isolierte Flask-Factory ohne produktiven Auth-/DB-Kontext | nein/nein/nein/nein/nein | Research behalten; nicht produktiv übernehmen |
| `App/trade_v2/__main__.py` | Lokaler Preview-Start auf Port 8095 | nein/nein/nein/nein/nein | Research behalten; nicht produktiv übernehmen |
| `App/trade_v2/assets/amendment.css` | Screen-/Responsive-CSS; Geometrie und Zustandsdarstellung, keine persistente Domain | nein/nein/nein/ja/nein | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/amendment_demo.js` | Synthetische Änderungszustände | ja/ja/nein/nein/nein | Research behalten; nicht produktiv übernehmen |
| `App/trade_v2/assets/amendment_view.js` | Amendment-Projektion mit lokalen Commands und Rollenwechsel | nein/ja/nein/ja/ja | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/amendments.js` | Lokale Vorschlags-/Zustimmungs- und Abbruchguards | nein/ja/ja/nein/nein | Serververtrag neu implementieren; JS höchstens Vorprüfung/Projektion |
| `App/trade_v2/assets/deal_versions.js` | Eingefrorene Paketversionen; indexbasierte symmetrische Reduktion | nein/nein/ja/nein/nein | Serververtrag neu implementieren; JS höchstens Vorprüfung/Projektion |
| `App/trade_v2/assets/discovery.js` | Lokale Dismiss-Auswahl und Nachrücken auf drei sichtbare Vorschläge | nein/nein/nein/nein/nein | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/manual.css` | Screen-/Responsive-CSS; Geometrie und Zustandsdarstellung, keine persistente Domain | nein/nein/nein/ja/nein | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/manual_ink.js` | DOM-/Glyphenadapter der kanonischen Handschrift | nein/nein/nein/ja/nein | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/manual_review.js` | Review und lokales Absenden des manuellen Drafts | nein/ja/nein/nein/ja | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/manual_rules.js` | Bilaterale Album-/Mengenvalidierung und gespeicherter Draft | nein/nein/ja/nein/nein | Serververtrag neu implementieren; JS höchstens Vorprüfung/Projektion |
| `App/trade_v2/assets/manual_view.js` | Stickerlisten-Auswahl, Limits und lokale Draft-Interaktion | nein/ja/nein/ja/ja | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/marker.svg` | Altes isoliertes Markerasset; keine neue kanonische Ressource | nein/nein/nein/ja/nein | Research behalten; nicht produktiv übernehmen |
| `App/trade_v2/assets/overview.css` | Screen-/Responsive-CSS; Geometrie und Zustandsdarstellung, keine persistente Domain | nein/nein/nein/ja/nein | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/overview.js` | Rollenbezogene Gruppen-/Handlungsprojektion | nein/nein/ja/nein/ja | Serververtrag neu implementieren; JS höchstens Vorprüfung/Projektion |
| `App/trade_v2/assets/overview_demo.js` | Synthetische Übersichts-Szenarien | ja/ja/nein/nein/nein | Research behalten; nicht produktiv übernehmen |
| `App/trade_v2/assets/overview_view.js` | Übersicht mit Sessiondaten, Demo-Seeding und lokalen Zeitgebern | nein/ja/nein/ja/ja | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/packing.css` | Screen-/Responsive-CSS; Geometrie und Zustandsdarstellung, keine persistente Domain | nein/nein/nein/ja/nein | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/packing.js` | Lokaler Packzustand und Fehlmengencommands | nein/nein/ja/nein/nein | Serververtrag neu implementieren; JS höchstens Vorprüfung/Projektion |
| `App/trade_v2/assets/packing_confirmation.js` | Packprüfungsdialog und lokale Freigabe | nein/nein/nein/nein/nein | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/packing_view.js` | Packliste, Query-Demos und Rollenprojektion | nein/ja/nein/ja/ja | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/physics11.css` | Screen-/Responsive-CSS; Geometrie und Zustandsdarstellung, keine persistente Domain | nein/nein/nein/ja/nein | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/preview.css` | Screen-/Responsive-CSS; Geometrie und Zustandsdarstellung, keine persistente Domain | nein/nein/nein/ja/nein | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/preview.js` | Screen-Dispatcher; Fixture-Sortierung und Pax-Komponentenadapter | nein/ja/nein/ja/ja | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/proposal_dismiss.js` | Dismiss-UI auf lokalem Discovery-Speicher | nein/ja/nein/ja/ja | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/receipt.css` | Screen-/Responsive-CSS; Geometrie und Zustandsdarstellung, keine persistente Domain | nein/nein/nein/ja/nein | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/receipt_demo.js` | Synthetische Empfangs-/Problem-/Ratingzustände | ja/nein/nein/nein/nein | Research behalten; nicht produktiv übernehmen |
| `App/trade_v2/assets/receipt_history.js` | History-Projektion; enthält älteren renderActive-Pfad | nein/ja/nein/ja/ja | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/receipt_state.js` | Empfangs-, Problem- und Abschlussprojektion/Guards | nein/nein/ja/nein/nein | Serververtrag neu implementieren; JS höchstens Vorprüfung/Projektion |
| `App/trade_v2/assets/receipt_view.js` | Empfangs-/Problem-/Bewertungsansicht mit lokalen Commands | nein/ja/nein/ja/ja | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/receipts.js` | Lokale Empfangs-, Problemlösungs-, Abschluss- und Ratingmutation | nein/nein/ja/nein/nein | Serververtrag neu implementieren; JS höchstens Vorprüfung/Projektion |
| `App/trade_v2/assets/receive.js` | Pax-Receive-Adapter mit kanonischer Stackdarstellung | nein/nein/nein/ja/nein | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/receive_motion.js` | FLIP-Auffächerung, 440 ms, keine Kartenskalierung | nein/nein/nein/ja/nein | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/request_view.js` | Anfrageprojektion mit lokaler Entscheidung und Rollen-/View-Query | nein/ja/nein/ja/ja | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/requests.js` | Session-State, Snapshot, Versand-unabhängige Slots, Send/Decide/Expiry | nein/ja/ja/nein/nein | Serververtrag neu implementieren; JS höchstens Vorprüfung/Projektion |
| `App/trade_v2/assets/sender.js` | Lokales Absenden, Reset und Zeitgeber | nein/ja/nein/nein/ja | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/session.js` | Session-Laden und querygesteuerte Demo-Resets | nein/ja/nein/nein/ja | Research behalten; nicht produktiv übernehmen |
| `App/trade_v2/assets/shipping.css` | Screen-/Responsive-CSS; Geometrie und Zustandsdarstellung, keine persistente Domain | nein/nein/nein/ja/nein | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/shipping.js` | Lokale Adress-/Freigabe-/Versandcommands einschließlich Demo-Adresse | ja/nein/ja/nein/nein | Serververtrag neu implementieren; JS höchstens Vorprüfung/Projektion |
| `App/trade_v2/assets/shipping_demo.js` | Synthetische Versandzustände | ja/ja/nein/nein/nein | Research behalten; nicht produktiv übernehmen |
| `App/trade_v2/assets/shipping_panel.js` | Versand-/Adress-UI mit lokalen Aktionen und Demo-Einstiegen | nein/nein/nein/nein/nein | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/shipping_state.js` | Richtungsbezogene Versand-/Freigabeprojektion | nein/nein/ja/nein/nein | Serververtrag neu implementieren; JS höchstens Vorprüfung/Projektion |
| `App/trade_v2/assets/shipping_view.js` | Versandansicht mit Query-Rolle und Demos | nein/ja/nein/ja/ja | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/sticker_physics.js` | Versteckter iframe misst echte kanonische Sticker-CSS | nein/nein/nein/ja/nein | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/assets/ux08.css` | Screen-/Responsive-CSS; Geometrie und Zustandsdarstellung, keine persistente Domain | nein/nein/nein/ja/nein | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/fixtures.py` | Synthetische Partner, Alben, Angebote und Top-Reihenfolge | ja/nein/nein/nein/nein | Research behalten; nicht produktiv übernehmen |
| `App/trade_v2/manual_fixtures.py` | Vier manuelle Präferenz-/Supply-Szenarien und Lifecycle-Stubs | ja/nein/nein/nein/nein | Research behalten; nicht produktiv übernehmen |
| `App/trade_v2/routes.py` | GET-Fixture-Router; Slugs ersetzen keine persistenten Trade-IDs | nein/nein/nein/nein/ja | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/templates/manual.html` | Preview-Template für manuelle kanonische Stickerliste | nein/nein/nein/ja/ja | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |
| `App/trade_v2/templates/preview.html` | Gemeinsames Screen-Template mit Preview-/Entwicklersteuerung | nein/nein/nein/ja/ja | Adaptieren; kanonische UI bewahren, Fixture-/Session-/Query-Kopplung entfernen |

## Authorization pro Preview-Route

Heute alle GET-Fixtures ohne produktiven Session-/DB-Vertrag; keine echte Command-API. Folgende Rechte beschreiben den notwendigen Zieladapter, nicht existierende Sicherheit. Alle Mutationen brauchen CSRF, Serveridentität, Teilnehmerprüfung, erwartete Version, Idempotenz und serverseitige Guards.

| Route | Lesen künftig | Verändern künftig |
|---|---|---|
| `/trade-v2/` | Authentifiziert; Privacy, Account/Block, Album-Eligibility prüfen | Keine Mutation durch GET; eigener autorisierter Submit separat |
| `/trade-v2/partners` | Authentifiziert; Privacy, Account/Block, Album-Eligibility prüfen | Keine Mutation durch GET; eigener autorisierter Submit separat |
| `/trade-v2/partners/<slug>` | Authentifiziert; Privacy, Account/Block, Album-Eligibility prüfen | Keine Mutation durch GET; eigener autorisierter Submit separat |
| `/trade-v2/deals/<slug>` | Authentifiziert; Privacy, Account/Block, Album-Eligibility prüfen | Keine Mutation durch GET; eigener autorisierter Submit separat |
| `/trade-v2/partners/<slug>/smartdeal` | Authentifiziert; Privacy, Account/Block, Album-Eligibility prüfen | Keine Mutation durch GET; eigener autorisierter Submit separat |
| `/trade-v2/partners/<slug>/manual` | Authentifiziert; Privacy, Account/Block, Album-Eligibility prüfen | Nur eigener unverbindlicher Draft |
| `/trade-v2/requests/<slug>` | Nur authentifizierte Teilnehmer des konkreten Trades | Absender Withdraw, Empfänger Accept/Decline; Serverzeit |
| `/trade-v2/requests/<slug>/next` | Nur authentifizierte Teilnehmer des konkreten Trades | Nur eigene Packrichtung, aktuelle Paketversion |
| `/trade-v2/requests/<slug>/amendment` | Nur authentifizierte Teilnehmer des konkreten Trades | Berechtigter Melder schlägt vor, erforderliche Gegenseite stimmt exakt dieser Version zu |
| `/trade-v2/requests/<slug>/shipping` | Nur authentifizierte Teilnehmer des konkreten Trades | Nur eigene Adresse freigeben und eigenen Versand bestätigen; Partner liest freigegebene notwendige Adresse |
| `/trade-v2/requests/<slug>/receipt` | Nur authentifizierte Teilnehmer des konkreten Trades | Nur eigene Empfangsrichtung/Problemmeldung/Bewertung; Lösung gemäß bestätigter Rollenfreigabe |
| `/trade-v2/active` | Nur eigene laufende Vorgänge | Keine Mutation durch GET; eigener autorisierter Submit separat |
| `/trade-v2/partners/<slug>/manual/review` | Authentifiziert; Privacy, Account/Block, Album-Eligibility prüfen | Nur eigener Draft; Submit atomar neu validieren |

Private Adresse nur notwendiger autorisierter Partner im konkreten freigegebenen Versandtrade; kein Zugriff durch Rollenwechsel/erratene ID, keine Rohadresse in Discovery, Notifications, HTML-Fixtures oder Logs. Eigene gespeicherte Vorlage separat von konkreter Tradefreigabe. NP-C3-1 in TRADE_UX_PO_DECISIONS_Q1_Q8.md gilt: nach normalem Abschluss kein fortdauernder Partnerzugriff, Widerruf begrenzt zukünftige Anzeige, notwendige Problemfallaufbewahrung ohne pauschalen Supportzugriff, keine erfundene feste Retentionfrist. Technische Retentionpolicy vor Phase07 festlegen.

`role`, `scenario`, `demo`, `pack`, `amend`, `ship`, `receipt`, `manual`, `overview` als Fixture-/Stateumschalter vollständig entfernen. `view` höchstens validierter Darstellungszustand; nie Identität/Einwilligung. Browserzeit und sessionStorage sind niemals Vertrags-, Versand-, Zustimmungs- oder Slotnachweise.

## Alte Welt: explizite Klassifikation

| Klasse | Bestand | Behandlung |
|---|---|---|
| A bleibt | Bestehende Legacy-/SmartDeal-V1-Verträge, Vorgänge und ihre Services/Deep Links | Keine Migration der Semantik; alte Endpunkte weiter bedienen |
| B wiederverwenden | Auth, Privacy, Katalog/Resolver, Inventory/History, Optimizer, kanonische Karte/Stack/Liste, Typed-Grundmechanik | Über geprüfte Adapter; keine konkurrierende Wahrheit |
| C später ersetzen | Einstieg/Discovery/Composer und neue Tradeerstellung im bisherigen UI | Kohortenweise neuer Frontendpfad; nur neue Verträge |
| D später deprecaten | Alte Einstiegspresentation und überholte doppelte UI-Adapter | Erst nach Link-/Nutzungsinventur und vollständigem Rollbacknachweis; keine laufenden Vorgänge abschneiden |
| E Research | App/pax, Pax-/Journey-Previews, Trade-Fixtures/Demos/Sessionruntime, Audits/Screenshots | Jetzt vollständig behalten; keine Pax-Domain übernehmen |
| F Entscheidung nötig | Gemeinsame technische Renderingextraktion, Rating-Aggregation, konkrete Adressretention, reproduzierbarer Integrationsbaseline | Vor jeweiliger Phase festlegen; keine stillen Defaults |

## Settings-Hooks: entschieden / vorbereitet / offen

| Thema | Entschieden | Technisch vorhanden | Noch offen / Arbeit |
|---|---|---|---|
| Tauschen pro Album | Teilnahmefreigabe nötig | trade_pool_enabled produktiv | Abbildung in neue UI/Readmodels |
| Smart pro Album | Eigener Hook, unabhängig von manueller Freigabe | Previewpräferenz | Persistenz/Default und Einführung vor realem Filter festlegen |
| Crossalbum | Trade-v2 bilateral, sonst peralbum Receive≤Give | manual_rules-Fixtures | Persistenz/Defaults; keine ungefragte Migration alter Vorgänge |
| OPEN / SAME_ALBUM_ONLY | Neue manuelle V2-Semantik scopebegrenzt | Clientvalidator | Serverseitige Poolbildung, Revalidation bei Submit/Amendment |
| Favorit | Favorit existiert; Algorithmusvertrag bleibt | users.favorite_album_id | Keine neue Gewichtungsentscheidung aus UI ableiten |
| Öffentlich | Unabhängig von Trade-/Smart-Freigabe | visibility + PrivacyService | Konsistente DTO-Filter, keine Gleichsetzung |

Vollständige Konflikte und Persistenzarbeit stehen in den beiden Begleitdokumenten; frühere Audit-Testzahlen sind historische Nachweise, keine in INTEGRATION-00 wiederholten Tests.
