# Trade-v2 – Source-of-Truth-Matrix

Stand 2026-10-02. Zielzustände sind Planung, keine implementierten DB-/Runtimeänderungen. Alte Vertragsgenerationen bleiben getrennt; eine Quelle pro Regel **und Vertragsgeneration**, kein globales Überschreiben alter Vorgänge.

| Konzept | Heute produktiv | Trade-v2 Preview | Künftige verbindliche Quelle | Aktion | Risiko |
|---|---|---|---|---|---|
| User | users.id; Session + globaler Login/Auth-Version-Guard | Fixture-IDs/Valentin/role | Server actor aus Session | Fixtureidentität entfernen | IDOR |
| Album | albums + user_albums + services/albums.py | Synthetische ALBUMS | Bestehende IDs/Katalogresolver | IDs adaptieren | Falsche Albumzuordnung |
| Sticker | Kanonischer Albumcode-Resolver | Fixturecodes, z.B. BRA 1 | Kanonischer (album_id,code) | Am Rand normalisieren | Alias-Doppelposition |
| Quantity | stickers.quantity; InventoryReadService | Fixture supply/need | Inventar + Reservationsprojektion | Reader wiederverwenden | Doppelverplanung |
| Missing | Kanonischer Need unter Bindung/Transit | Fixture eligible/need | Kanonischer Need | Frisch bei Submit prüfen | Doppelte Incoming Needs |
| Duplicates | max(physical-assigned-reserved,0) | Fixture potential | Availability-Service | Keine eigene Mengenformel | Übersupply |
| Album visibility | user_albums.visibility; AlbumPrivacyService | Fixture Sichtbarkeit | Bestehende Privacy | An jeder Projektion prüfen | Datenleck |
| Favorite album | users.favorite_album_id | Fixturepriorität | Bestehender Favorit + gültiger Algorithmus | Kein neues Gewicht erfinden | Algorithmusdrift |
| Trade preferences | trade_pool_enabled; kein peralbum smart/cross Feld | manual_fixtures / manual_rules | Versionierte bilaterale Albumpräferenzen | Persistenz/Hooks ergänzen | OPEN global falsch |
| SmartDeal | Optimizer/planning/revalidation; V1-Vertrag | Fixierte Deals/Toporder | Kanonischer Optimizer + neuer Submitadapter | UI Top3 von Planung trennen | Stale Angebot |
| Manual trade | Legacy singlealbum request; neuer V1 Text noch spec | manual_rules + Sessiondraft | Servervalidator für neuen Vertrag | Beidseitige Freigaben/Receive≤Give | Client umgehbar |
| Trade request | trade_requests + trades | requests.js sessionStorage | Persistenter versionierter Request | Atomarer Submit | Keine Bindung im Browser |
| Trade version | trade_positions ohne Version | deal_versions.js v1/v2 | Immutable Paketversion + current pointer | Version/Positionsschema ergänzen | Stale Zustimmung |
| Amendment | Kein entsprechendes Modell | amendments.js | Persistenter Vorschlag + erforderliche Zustimmung | Atomarer Versionswechsel | Stille Paketmutation |
| 3/3 slots | Nur V1 offene ausgehende Requests | requests.js Slots beider Rollen | Operative richtungsbezogene Serverableitung | Status von Slot trennen | Accept schafft unbegrenzt Kapazität |
| Request expiry | V1 binding_created_at +24h; lokal Schema21 fehlt | Client Date.now | Server UTC Bindung +24h | Terminalübergang atomar | Accept vs Expiry |
| Packing state | Keine versionierte Packfreigabe | packing.js | Eigener Packstatus je Paketversion | Persistieren und invalidieren | Freigabe alten Pakets |
| Address release | Kein strukturiertes produktives Modell gefunden | shipping.js Demo-Adresse | Private Vorlage getrennt von Tradefreigabe | Zweckgebundene Autorisierung/Retention | URL-Datenleck |
| Shipping direction | trade_shipping_status + ShippingService | shipping_state / shipping.js | Eigene Versandbestätigung je Richtung | Version-/Pack-/Adressguards + exactly once | Doppelte Inventarbuchung |
| Receipt | trade_receipt_status; NOT_SHIPPED-Guard | receipts.js Q2 | Eigenständiger tatsächlicher Empfang | Neuer Q2-Adapter/Buchungsledger | Shipping/Slot unerlaubt ändern |
| Problem | trade_problem_reports/positions | receipts.js Lösungsvorschlag | Versionierter richtungsbezogener Problemflow | Bestehende Regeln scoped adaptieren | Fiktive volle Nachlieferung |
| Completion | trades.lifecycle_state/completed_at | receipt_state.js | Serveraggregation erfüllter Abschlussbedingungen | Receipt unabhängig von Versandklick | Offener eigener operativer Slot unsichtbar |
| Rating | trade_ratings 1–5 immutable | 1–3 local rating | Versionierte unveränderliche Skala je Vertrag | Keine Legacy-Konvertierung | Falsche Aggregation |
| Notifications | typed_notifications / events | Previewanzeigen | Serverevents + deduplizierte Typed-Meldungen | Q7 Accept-Typ und Deep Links | Doppelmeldung/IDOR |
| Canonical sticker card | Produktives style.css / Stickerliste | sticker_physics.js iframe-Probe | Bestehende physische Karte | Gemeinsamen Adapter scoped nutzen | Dimensionsdrift |
| Canonical stack geometry | Produktive Wall Cap5 | Pax-Receive Cap10 | Gleiche −2/−2 Faces/z-index, Tradecap10 | Nur cap kontextabhängig | Geometrie wächst über10 |
| Reservations | trade_reservations + Positionen/Availability | Session snapshot bindet nichts | Server Supply + Incoming Need Bindung | Beide Richtungen in Submittransaktion | Crossrequest Oversubscription |

## Verträge gegen Code

Belegkatalog mit Hashes und Kapitelüberschriften: relevant-files.json. Er umfasst TRADE-00 Reset, TRADE-01–11 Audits, End-to-End-Audit, Q1–Q8, NP-C3-1, Manual Offer V1, Trade-v2 Manual Selection, SmartDeal Algorithmus/Bible/T4/T5/T6 und Pax-Audits. Audits beschreiben lokale Previewtests, nicht produktive Persistenz oder aktuelle Deploymentverifikation. Die konkrete Kollision wird jeweils durch Code und ausdrücklich scoped Entscheidung aufgelöst, nicht das Datum allein.

| ID | Konflikt / Quellen | Auflösung | Phase |
|---|---|---|---|
| C01 | Q1 / AC25–26 vs Trade-v2 Amendment: `docs/TRADE_UX_PO_DECISIONS_Q1_Q8.md; docs/SMARTDEAL_ALGORITHM_CONTRACT_V1.md` ↔ `docs/TRADE_PRODUCT_CONTRACT_V2.md; App/trade_v2/assets/amendments.js` | Nur neuer Contract: explizite Zustimmung zu exaktem Pre-Shipment-Paket; kein stiller Repair, keine Änderung versendeter Richtung. Legacy bleibt unverändert. | 06 |
| C02 | Empfängerpräferenz vs beidseitige Albumfreigabe: `docs/MANUAL_OFFER_DOMAIN_CONTRACT_V1.md; Q3` ↔ `docs/TRADE_V2_MANUAL_SELECTION_CONTRACT.md; manual_rules.js` | Neue Trade-v2-Angebote: Schnittmenge beider Freigaben; SAME_ALBUM_ONLY Receive≤Give pro Album, OPEN nur bilateral zulässiger Pool. Nicht global umdeuten. | 03 |
| C03 | Open-request-Quota vs operative 3/3-Slots: `App/services/smartdeal_requests.py; SMARTDEAL_PRODUCT_BIBLE_V1.md` ↔ `TRADE_PRODUCT_CONTRACT_V2.md; requests.js` | Neue manuelle und Smart-Angebote teilen 3 ausgehende/3 eingehende operative Slots; Accept hält, nur eigener Versand oder zulässiger Abbruch löst. Receipt löst nie. | 04 |
| C04 | Q2 erlaubt Empfang, produktiver Service verlangt Partner-SHIPPED: `App/services/trade_receipt.py; App/services/trade_problems.py` ↔ `TRADE_UX_PO_DECISIONS_Q1_Q8.md Q2; TRADE_PRODUCT_CONTRACT_V2.md; receipts.js` | Neue versionierte Receipt-/Buchungslogik; keine fingierte Shippingmutation oder Slotfreigabe, genau einmal physisch buchen. Legacyguard unangetastet lassen. | 08 |
| C05 | Rating 1–5 vs 1–3: `App/services/trade_ratings.py; DB trade_ratings CHECK und immutable triggers` ↔ `TRADE_PRODUCT_CONTRACT_V2.md; receipts.js` | Neue Skala versionieren; Legacy nicht umrechnen; Aggregationsdarstellung vor Phase08 spezifizieren. | 08 |
| C06 | Schema21-Quellcode vs tatsächlich lokaler Schema20: `App/services/runtime_operations.py; schema_migrations; App/migrations/0021*` ↔ `App/services/trade_contracts.py; smartdeal_requests.py` | Schema21 existiert nur als Migration; Produktionsvolume nicht geprüft. Migrationsfolge/runtime expected version koordinieren; keine blinde Anwendung oder V2-Enum-Erweiterung. | 04 |
| C07 | Legacy manuelle Submitbindung vs neuer Vertrag: `App/webapp.py create_trade_request; TradeReservationService.accept` ↔ `MANUAL_OFFER_DOMAIN_CONTRACT_V1.md Q4; TRADE_PRODUCT_CONTRACT_V2.md` | Neuer Submit reserviert beide Richtungen und Incoming Needs atomar; Legacy reserviert erst bei Accept. Stickerlisten-Transfer ist kein Requestendpoint. | 04 |
| C08 | Indexreduktion und zwei Previewversionen vs belastbare Amendments: `App/trade_v2/assets/deal_versions.js` ↔ `TRADE_PRODUCT_CONTRACT_V2.md; TRADE_V2_MANUAL_SELECTION_CONTRACT.md` | Previewindexpaarung ist keine allgemeine Domainregel. Exakte explizite Positionen, Versionen und beidseitige Mengenregeln validieren; asymmetrische manuelle Pakete abdecken. | 06 |
| C09 | 24h: kein Superseding: `SMARTDEAL_ALGORITHM_CONTRACT_V1.md AC23; smartdeal_expiry.py` ↔ `TRADE_PRODUCT_CONTRACT_V2.md; requests.js` | Bindungszeit + absolute24h bleibt; server UTC und atomarer Accept/Expiry-Wettlauf. PO review before productive Pax integration bleibt historischer Reviewmarker, keine neue Frist. | 05 |
| C10 | Top3 vs global maximal5 / Paarpotential: `SMARTDEAL_ALGORITHM_CONTRACT_V1.md; smartdeal_planning.py` ↔ `TRADE_08_AUDIT.md; discovery.js; Q5/Q8` | Drei sichtbare Vorschläge mit Nachrücken, kein neuer Optimizer. Paaroptimum nicht globaler Plan; Unter5-Paaranzeige keine automatische Smart-Submit-Freigabe. | 02 |
| C11 | Discovery kann schreiben: `App/services/smartdeal_runtime.py discover/cleanup` ↔ `INTEGRATION-01 Read Models` | Readonly-Shell verwendet reine Reader/Planung, nicht Wrapper mit Expiry-Cleanup; GET-Sideeffects explizit trennen. | 01 |
| C12 | Pax-Komponenten vs Pax-Produktsemantik: `App/trade_v2/assets/preview.js; receive.js; App/static/pax/` ↔ `TRADE_00_RESET_AUDIT.md; TRADE_11_AUDIT.md` | Nur geprüfte Renderingbausteine adaptieren; keine Paxgröße/Lifecycle-Fixture als neue Trade-SoT. Wall5/Trade10, −2/−2, Face und z-index kanonisch. | 01–09 |

## Vorhandenes Schema und Wiederverwendung

persistence-map.json enthält das tatsächlich gelesene lokale CREATE-Schema (Tabellen, Indizes, Trigger), Migrationen und Ledger. Remote produktiv ist nicht aus diesem lokalen Snapshot abzuleiten.

- `trade_requests`: Legacy JSON-Paket/status/from/to; lokal fehlen contract_type/binding_created_at/accepted_at. Migration0021 sieht legacy/smartdeal_v1 mit CHECK und unveränderlichen Vertrags-/Zeitfeldern vor; V2 passt nicht ohne geplante separate Erweiterung hinein.
- `trades`: eindeutige legacy_trade_request_id, verschiedene Teilnehmer, lifecycle/timestamps. Als Legacy-Verknüpfung wiederverwendbar, neue Root-/ID-Namensräume ausdrücklich definieren.
- `trade_positions`: positive Mengen, FKtrade, UNIQUE(trade,from,to,album,code), keine Paketversion. Immutable Versionierung fehlt.
- `trade_reservations`: UNIQUE(position), positive Menge, active/released und Freigabezeit/-grund, Supply-/Trade-Indizes. Kein summenübergreifendes DB-Constraint gegen Überreservierung. Versionswechsel darf eine freigegebene Position nicht einfach als neue Bindung überschreiben.
- Shipping-/Receipt-Status: eine Zeile je Trade, richtungsbezogene Flags/Zeitstempel mit Konsistenzchecks. Kein vollständiger Pack-/Adress-/Empfangsprüfungszustand.
- Problemberichte: UNIQUE(trade,receiver), Positionen mit expected/initial/resolution und Mengenchecks; bestehende resolved-Bedingung darf nicht unbemerkt zur neuen Lösungsvorschlagssemantik werden.
- Ratings: 1–5 CHECK, UNIQUE(trade,rater) sowie (trade,rated), Update-/Delete-Schutztrigger. Events besitzen keine allgemein ausreichende Command-Idempotenzgarantie.

## Benötigte Persistenz – präziser Entwurf, keine Migration

Tabellennamen unten sind Vorschläge, keine bereits getroffene technische Architekturentscheidung. Getrennte V2-Tabellen sind angesichts Legacychecks der sichere Ausgangsentwurf; gemeinsame Adapter erst nach Kompatibilitätsbeweis.

| Bereich | Benötigte Felder/Relationen und Constraints |
|---|---|
| Contract/Request root | contract_type/version, request_id, zwei kanonische user FKs (verschieden), origin, state, immutable binding_created_at, expires_at, accepted/terminal times, current_package_version, revision; Origin ist nicht Contracttyp. Unique(actor,command_key), payload hash gegen Key-Wiederverwendung |
| Paketversion/-position | UNIQUE(trade,version); immutable exakte gerichtete Positionen mit canonical album/code/quantity>0; UNIQUE(version,from,to,album,code); proposer, created_at, package_hash; initialer Snapshot bleibt lesbar |
| Bindung | Aktive Supply- und Incoming-Need-Bindung je Version/Position; eindeutige aktive Bindungsidentität, quantity>0, released_at/reason konsistent; gemeinsame Availability muss neue und Legacybindungen zählen |
| Kapazität | Operative Slotprojektion je participant und Anfrageorientierung, getrennt von Requeststate; maximal3 incoming/3 outgoing. Entweder atomar serverseitig ableiten oder explizite belegte Slotzeilen1..3 UNIQUE(user,direction,slot); nicht gleichzeitig zwei Wahrheiten. Discovery belegt0 |
| Präferenzen | UNIQUE(user,album), trade_enabled/smart_enabled/cross_album_enabled plus Revision; bestehendes trade_pool_enabled nicht parallel widersprüchlich führen; Defaults vor Einführung festlegen |
| Amendment | proposal_id, trade, base_version, proposed_version, genaue fehlende/neue Positionen, proposer, status, erforderliche Zustimmungen mit actor/time/hash; höchstens ein aktiver Vorschlag pro Basispaket; compare-and-swap current version |
| Packprüfung | UNIQUE(trade,version,actor), state, exact checked quantities/position IDs, confirmed_at/revision; alte Freigabe kann neues Paket nicht freigeben |
| Adresse | Private optionale Vorlage getrennt von konkretem versioniertem Tradeadress-Snapshot/release; owner/authorized_partner, purpose, released/revoked/access-end times; minimierte Zugriffsprotokolle, keine Klaradresse im allgemeinen Eventpayload |
| Versand | UNIQUE(trade,actor), gebundene Versandversion, Versandbestätigung/timestamp, stabiler physischer Buchungsschlüssel; kein rückwirkendes Amendment dieser Richtung |
| Empfang/Problem | UNIQUE(trade,receiver), tatsächlicher Empfang/Prüfstatus/times unabhängig vom Partnerklick; gerichtete Mengen pro Position, Problemstatus, Lösungsvorschlag und Zustimmungen, keine erfundene volle Lieferung |
| Abschluss/Rating | Abschlusszustand/-grund/time aus Domain ableiten; UNIQUE(trade,rater), scale_version und 1..3 für V2, immutable; eigene unerledigte Versandbestätigung/Slot bleibt auch nach tatsächlichem Empfang sichtbar |
| Events/Outbox | Command-Idempotenz und UNIQUE(event identity,recipient,type); Event plus Notification-outbox im selben Commit, Zustellung retrybar. Keine doppelte Acceptmeldung |

## Atomarität und konkrete Wettläufe

SQLite benötigt für read→validate→write `BEGIN IMMEDIATE` auf **derselben** Verbindung; WAL oder ein Gunicornworker ersetzen dies nicht. Andere Datenbanken benötigen entsprechende Rowlocks/Serializable-Strategie. Constraints ergänzen, ersetzen aber keine aggregierten Supply-/Need-/Slotprüfungen. Keine langen Benutzerinteraktionen unter Lock.

| Kommando / Race | Atomarer Bereich / erneute Serverprüfung | Erwarteter Ausgang |
|---|---|---|
| B und C konkurrieren um As letzte Dublette | Beide Richtungen Supply+Need, Eligibility/Blocks/Prefs, identisches Paket, beide Slots, Snapshot+Reservations+Event zusammen | Genau ein Bindungscommit, zweiter stale/insufficient; keine Negativsupply |
| Zwei Submits bei 2/3 Slots | Slotprüfung und beide Bindungen im selben Schreiblock | Maximal3, kein check-then-write außerhalb Transaktion |
| Submitretry / Doppelklick | actor+idempotency key+payload hash, Snapshotidentity | Gleiche Antwort, kein zweites Paket/Reservierung/Notification |
| Accept gleichzeitig Expiry/Withdraw/Decline | State+Revision+Serverzeit unter Lock; expiry binding+24h absolut | Ein Terminal-/Acceptgewinner; Bindungen genau einmal freigeben oder halten |
| Accept | Empfänger/aktueller Vertrag/Snapshot/Zustand/Deadline, bestehende Bindung prüfen, state+event | Keine Neuberechnung, keine zweite Reservierung, Slots bleiben belegt |
| Amendment gegen Pack/Versand | base/current revision, Richtung noch nicht versendet; neue Regeln/Supply/Need; Zustimmung exakt zum Paket | Veraltete Aktion verworfen, alter Snapshot erhalten; atomarer Bindungswechsel und neue Packprüfung |
| Addressrelease gegen Widerruf/Abschluss | Autorisierung und aktuelle Purpose-Laufzeit bei jedem Read, Freigaberevision bei Commands | Kein stale URLcache/Partnerzugriff nach Ende; Vorlage getrennt |
| Shipretry / Ship gegen Amendment | Aktuelle Paket-/Pack-/Adressfreigabe, eigene Richtung; Inventarledger, Reservationsrelease, eigener Slot, Status+Event zusammen | Genau eine Buchung, nur eigener Slot frei |
| Q2 Receipt vor Ship, später Shipretry | Physische Buchungsidentität getrennt von Versandattestation; gerichtete Menge und Empfangsstatus atomar | Keine doppelte Buchung; Receipt ändert weder Shippingflag noch Slot |
| Problem / Lösungszustimmung / Abschluss | Teilnehmer, Empfangstatsache auch ohne Partner-SHIPPED, aktuelle Problemrevision/Quantitäten/Zustimmungen | Keine Überbuchung oder fingierter Erfolg; Abschluss nur gültig aggregiert |
| Ratingretry / zwei Tabs | Teilnahme+Qualifikation, Scale, UNIQUE, immutable | Eine optionale Bewertung, keine nachträgliche Änderung |

Preview-Object.freeze, Date.now, sessionStorage, versteckte Buttons und Clientlimits liefern für keinen dieser Fälle Sicherheit. Die konkrete Ledger-Abbildung von Q2 auf vorhandene Inventory-History muss vor Phase08 anhand Receipt→Ship, Teilreceipt und Retry nachgewiesen werden, nicht nur NOT_SHIPPED entfernen.
