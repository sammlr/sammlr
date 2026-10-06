# Trade Lifecycle V1 — Read-only Code- und Persistenzaudit

Geprüfter Source-Stand: `e20a8c4e84f2adb83b2f4f3f870846267713a4c1`, 2026-10-06. Keine App gestartet, keine DB geöffnet/migriert, keine Runtime geändert. „Produktiv vorhanden“ bedeutet im produktiven Source-/Routenpfad vorhanden, **nicht** Behauptung über den Deploy- oder Migrationsstand einer entfernten Installation.

## 1. Drei getrennte technische Welten

1. Produktive Legacy-Trades mit Requests, Annahme/Reservations, Versand, Empfang, Problemen, Ratings.
2. Expliziter `smartdeal_v1`-Contract mit verbindlichen beidseitigen Pending-Holds, 24h, eigenen Accept-/Release-Grenzen. Physischer V1-Lifecycle wird an der Runtime-Grenze bewusst noch nicht in Legacy durchgereicht.
3. Neuer SAP-/Trade-v2-Read-Pfad mit zentraler Domain und produktivem Profil-/Manual-Adapter; der umfangreiche physische Trade-v2-Lifecycle daneben ist derzeit weitgehend **isolierte sessionStorage-Preview**.

Keine dieser Welten ist bereits der vollständige neue 72h-/Foto-/Adress-/Receipt-Vertrag. Keine automatische Übernahme alter Tabellenbedeutungen oder lokaler JS-Szenarien.

## 2. Bestehender Code: Beleg, Nutzen und Lücke

| Bereich | Konkreter Sourcebeleg | Vorhanden / Wiederverwendung | Neue Lücke oder Konflikt |
|---|---|---|---|
| SAP / Partner / Auto | [trade_search_routes.py](../App/trade_search_routes.py), [trade_shell.py](../App/trade_shell.py), [trade_search.py](../App/services/trade_search.py) | `/tauschen`, kompatibles `/tauschen/sammlr`, frische Domainberechnung, existierende Deal-GETs | Kein neuer Lifecycle-Send-Command im SAP. `/tauschen/laufend` liest bestehende Requests; keine neue Zentrale. |
| Manuelle produktive Auswahl | [profile_trade.py](../App/profile_trade.py): `register_manual`, `/manual/check`; [manual_view.js](../App/trade_v2/assets/manual_view.js) | Read-only POST-Prüfung mit CSRF, Fingerprint und konkreter Domainvalidierung; vorhandene UI | Erfolgsantwort sagt ausdrücklich „noch keine Tauschanfrage erstellt“. Keine produktive Lebenszykluspersistenz. |
| Zentrale Trade-v2-Domain | [trade_v2_domain.py](../App/services/trade_v2_domain.py): `market`, `validate_deal`; [trade_v2_rules.py](../App/services/trade_v2_rules.py) | Bilaterale Albumfreigabe, Same-/Cross-Gruppen, konkrete Mengen-/Need-Prüfung, manuelles Receive≤Give | Heutiger frischer Read-Markt ist kein Accept-Writer. Eigene bestehende Holds/Incoming-Claims müssen beim späteren Recheck korrekt zum selben Vorgang zugeordnet werden; sonst Selbstblockierung. |
| Präferenzen | [trade_v2_preferences.py](../App/services/trade_v2_preferences.py), Migration 0022 | `trade_pool_enabled` bleibt Source of Truth; Cross-Mode additiv, Default SAME, kein Auto-Migrate | Kein Lifecycle-Schema; angenommener Regelkontext und Versionsbezug noch nicht gespeichert. |
| Freie Supply / Needs | [inventory_availability.py](../App/services/inventory_availability.py), [smartdeal_planning.py](../App/services/smartdeal_planning.py): `_pieces`, `_project_bindings` | Mengenbasierte aktive Holds und verbindliche eingehende Needs/Transit, geschütztes Eigenexemplar | Planung versteht heute nur Legacy/V1 und verlangt für offenes V1 vollständige beidseitige Materialisierung. Einseitige neue Pending-Holds benötigen expliziten zentralen Vertragsadapter; keine zweite Supplyengine. |
| Vertragsdispatch | [trade_contracts.py](../App/services/trade_contracts.py); [smartdeal_runtime.py](../App/services/smartdeal_runtime.py): `dispatch_request` | Explizite Trennung Legacy / smartdeal_v1, unbekannte Typen fail closed | Neuer Typ noch nicht erlaubt. V1 ship/receive/problem liefert `LIFECYCLE_UNAVAILABLE`, nicht Legacy-Fallback. |
| Ältere Smart-Anfragen | [smart_trade_requests.py](../App/services/smart_trade_requests.py) | Legacy-S22, `SMART_REQUEST_MARKER=-22`, Limit 3, **48h** `SMART_REQUEST_LIFETIME`, aktuelle Paketprüfung | Weder neuer 72h-Vertrag noch expliziter SmartDeal-V1. Nicht pauschal als 24h bezeichnen/ändern. |
| Explizite V1-Anfragen | [smartdeal_requests.py](../App/services/smartdeal_requests.py): `_create_locked`; [smartdeal_expiry.py](../App/services/smartdeal_expiry.py) | Atomare Create-Identität, genaues Paket, 3 offene V1-Senderanfragen, **24h**, Materialisierung von Positionen | Reserviert bei Create **beide** Supplies. Keine direkte Wiederverwendung für die neue einseitige Reservierung. |
| V1-Accept / Release | [smartdeal_acceptance.py](../App/services/smartdeal_acceptance.py), [smartdeal_release.py](../App/services/smartdeal_release.py) | Transaktionshülle, Idempotenz, Explicit-Accept-/GO, Decline/Withdraw/Sweep | Frühere GO-/Mutual- und Fristsemantik nicht auf neue explizite Gegenangebote übertragen. Keine 1-Counter-Verhandlungspersistenz. |
| Legacy-Accept / Holds | [trade_reservations.py](../App/services/trade_reservations.py): `accept`, `_assert_available`, `release` | `BEGIN IMMEDIATE`, autorisierte Annahme, Positionen, mengenbasierte beidseitige Holds; Bestandsuntergrenze über `ActiveReservationBindings` | Reservierung bisher erst bei Legacy-Accept; neue Sender-Pending-Holds und Versionierung fehlen. Release kann nicht ungeprüft nach physischer Bewegung aufgerufen werden. |
| Physischer Versand | [trade_shipping.py](../App/services/trade_shipping.py): `ship`; [webapp.py](../App/webapp.py): `/trade/<id>/ship` | Eigene Seite, aktive Reservierungen, genaues Remove, History-Eventkey, Commit/Rollback, Gegenrichtung unabhängig | Keine Pflichtfotos-/Review-/Adressbarriere, keine neue 72h-Versandphase. Boolean+Zeit erwartet Absenderselbstauskunft; Q2-Evidenzherkunft/Teilabgang fehlt. |
| Voller Empfang | [trade_receipt.py](../App/services/trade_receipt.py): `receive`, `finalize_received_side`; `/trade/<id>/receive` in webapp | Eigene empfangende Seite, atomare Inventory-Adds, Retry, Abschluss erst beide received ohne offenes Problem | **NOT_SHIPPED-Guard** gegen fehlenden Partnerklick; neuer Q2-Pfad nicht implementiert. Pauschale Vollpositionen bei normalem Receive; kein neuer Prüfungs-/Fotoprozess. |
| Teil-/Problemempfang | [trade_problems.py](../App/services/trade_problems.py): `report`, `_book`, `resolve`, `close_with_problem` | Expected/initial/resolution-Mengen; missing/wrong/damaged/shipment_lost; idempotente Buchung korrekter Teilmenge; problematischer Abschluss | Ebenfalls NOT_SHIPPED. `resolve` arbeitet die verbleibende erwartete Menge ab; kein beliebiger neuer Schadensakzeptanz-/Teilprüfungsworkflow. 7-Tage-Guard nicht als neue Vertragssicherheit vorhanden. Globales close_with_problem kann nicht ungeprüft beide neuen Richtungen schließen. |
| Inventory-/Historienwrites | [inventory_write.py](../App/services/inventory_write.py), [inventory_guard.py](../App/services/inventory_guard.py), [history_cutover.py](../App/services/history_cutover.py) | Guard, atomare Writes, `HistoricalInventoryWriteService` mit event_key-Dedupe/Savepoints | Neue gemeinsame Abgangsidentität für Shipment-/Receipt-Evidence, Positionsdelta-Ledger und Reconciliation fehlen. Keine pauschale Verwendung alter whole-position-Keys bei mehreren Teilbuchungen. |
| Ratings | [trade_ratings.py](../App/services/trade_ratings.py): `state_for_request`, `create`, `summary_for_user` | Bereits 1–5 Sterne, Teilnehmerprüfung, unique Rating, Transaktion, Profilaggregat | Qualifikation erst `completed`/`closed_with_problem`/`problem_resolved_after_close`; Aggregate ohne Blind-Publikationsfilter. Keine positive Tags oder individuelle 14-Tage-Fenster. |
| Notifications | [typed_notifications.py](../App/services/typed_notifications.py), [notification_history.py](../App/services/notification_history.py) | Typisierter Katalog, target/source_event/dedupe, Sichtbarkeit/Retentionmechanik | Keine vollständigen neuen Counter-/Foto-/Review-/Reminder-/Adress-/Richtungsereignisse. `smart_request_accepted` Domain-Event ist nicht bereits ein vollständiger neuer Notificationtyp. Kein Push-System behaupten. |
| Erfolgsprojektion | [successful_trade_projection.py](../App/services/successful_trade_projection.py) | Bestehende Trennung von Erfolg und qualifizierten Legacy-Abschlüssen | Neue Richtungs-/Adminqualität, Rating vor Gesamtabschluss und Zentrale benötigen passende Projektionen; kein falscher Erfolgszähler. |
| Adressen / Kontrollfotos | Source-Suche in `App/services` und SQL-Migrationen; [shipping.js](../App/trade_v2/assets/shipping.js) | Profile-Portrait-Upload ist ein anderer Zweck; Demo-Adressen existieren im isolierten Prototyp | Keine produktive Trade-Adressvorlage/-Snapshot/-Freigabepersistenz und keine Pflicht-Kontrollpaket-/Reviewpersistenz gefunden. Profilbildsystem nicht als bereits fertiges Tradefoto-System deklarieren. |

## 3. Preview-/Research-only

[App/trade_v2/routes.py](../App/trade_v2/routes.py) bietet isolierte GET-Fixtures. [requests.js](../App/trade_v2/assets/requests.js) verwendet sessionStorage, 24h und operative eingehende/ausgehende Slots bis eigenem Versand. [packing.js](../App/trade_v2/assets/packing.js), [amendments.js](../App/trade_v2/assets/amendments.js), [deal_versions.js](../App/trade_v2/assets/deal_versions.js) zeigen Pack-/Versions-/Reduktionsinteraktion, ohne produktive Mehrbenutzertransaktionen.

[shipping.js](../App/trade_v2/assets/shipping.js) enthält ausdrücklich erfundene Demo-Adressen und lokale Versandfreigaben. Keine echte Speicherung/Weitergabe. [receipts.js](../App/trade_v2/assets/receipts.js) erlaubt tatsächlichen Empfang ohne SHIPPED, verändert bewusst weder Shipping noch Inventory; Rating dort 1–3 und erst nach Gesamtabschluss. [receipt_state.js](../App/trade_v2/assets/receipt_state.js) validiert denselben alten Demo-Vertrag.

Diese Interaktionen sind Referenzen, kein Schema-/Servicevertrag für diesen Auftrag. Die neue Pflichtfotobarriere, neue Anfragekapazität, 72h, Bestandsnachholung und blinde 1–5-Ratings erfordern spätere gezielte neue Integration. `App/pax/` bleibt historischer Prototyp. Die produktive manuelle Auswahl nutzt nur gezielt Teile der vorhandenen Preview-Präsentation; daraus folgt kein produktiver JS-Lifecycle.

## 4. Bereits vorhandene Persistenz

| Quelle | Tabellen/Constraints | Verwendbarkeit / Grenze |
|---|---|---|
| `base_schema.sql` | `users`, `albums`, `user_albums`, `stickers`, `trade_requests`, `notifications` | Bestehende Identitäten/Inventare/Legacy-Requests; neue Verhandlungsversion nicht in legacy give/get JSON hineininterpretieren. |
| Migration 0001 | `trades`, `trade_positions`, `trade_events`; unique gerichteter Albumcode je Tradeposition | IDs, mengenbasierte Positionen, Audit als Anknüpfung; explizite Versionsidentität und Eventdedupe fehlen. |
| 0002 | `trade_reservations`: Positionsbezug unique, aktive/freigegebene Menge | Gemeinsame Holdquelle erhalten. Contract-/Offer-/Amendment-Version und gegebenenfalls stückweiser Verbrauch benötigen Adapter/Erweiterung. |
| 0003 | `trade_shipping_status`: je Seite Boolean plus timestamp, CHECK koppelt beide | Reicht nicht für „physisch angekommen ohne Absenderklick“ samt Herkunft/mehreren Buchungsmengen. Nicht einfach Boolean als Selbstauskunft fälschen. |
| 0004 | `trade_receipt_status`: je Seite Boolean plus timestamp | Keine separate arrival/inspection/settlement- oder differenzierte Mengenprüfung. |
| 0005 | `trade_receipt_reports`, `trade_receipt_report_positions` | Erwartung, initialer und Resolution-Eingang, Problemtypen vorhanden. Resolved-Constraint verlangt vollständige Restfüllung; neue qualifizierte Teil-/Adminausgänge gesondert gestalten. |
| 0006 | Notificationtyp, Target, Source-Event, Dedupe | Neue fachliche Ereignisse anschließbar; vertrauliche Inhalte nicht in generische Payloads kopieren. |
| 0008 | `trade_ratings`: Sterne 1–5, unique pro Trade/Rater/Partner; No-Update/No-Delete-Trigger | Kein Blindstatus, Releasezeit, Tag-Relation oder individuelle Eligibility/Deadline. Alte immutable Ratings nicht umschreiben. |
| 0013/0014 | Collection-/Feed-/History-Events, `historical_inventory_mutations` mit unique event_key | Genau-einmal-Buchungsbeleg und Historie wiederverwenden; neuen fachlichen Schlüssel und Deltaidentität definieren. |
| 0021 | `trade_requests.contract_type`, `binding_created_at`, `accepted_at`; erlaubte Typen nur legacy/smartdeal_v1, Zeit-/Type-Immutable-Trigger | Explizite Grenze bereits vorhanden, neuer Contract-Type ohne spätere Schemaerweiterung nicht speicherbar. Kein Update alter immutable Vertragswerte. |
| 0022 | `user_albums.cross_album_mode` | Fachliche Präferenzgrundlage, kein Lifecycle. Source vorhanden; in diesem Auftrag nicht ausgeführt und realer DB-Migrationsstand nicht neu abgefragt. |

## 5. Später erforderliche Erweiterungen — keine Migration jetzt

Keine verbindlichen Migrationsnummern oder SQL-DDL in diesem Auftrag. Folgende Datenfähigkeiten sind erforderlich; additive Tabellen oder Erweiterungen vorhandener Tabellen erst nach D01–D09 und technischer Entwurfsprüfung wählen:

1. Neuer unverwechselbarer Contract-Type/Version, stabile Teilnehmer und Erstellerperspektive; Legacy/V1-Routing unverändert, unbekannt weiterhin fail closed.
2. Verhandlung/Angebotsrevisionen mit höchstens einem Counter, exakten Snapshots, Rollenwechsel, 72h-Zeiten, Zustand und dauerhaften Commandresultaten.
3. Verknüpfte einseitige Pending-Holds, nach Accept beidseitige Holds, akzeptierte Incoming-Claims; versionierter atomarer Austausch bei Reduktion und zentrale Planungserweiterung.
4. Angenommene Dealrevisionen, beidseitige Amendmentzustimmungen und wirksame Regelgrundlage; kein Überschreiben alter Positionen/Historien.
5. Eigene Vorbereitung, Fotoobjektmetadaten, versionierte Kontrollpakete, Sichtbarkeitsbarriere, Reviews/Problemgründe und Retention-/Zugriffshooks.
6. Optionale Adressvorlagen, unverwechselbare konkrete Trade-Adresssnapshots, versionierte Freigabe-/Widerrufsnachweise und autorisierte Zugriffsdauer.
7. Richtungsbezogene Versand-/Ankunfts-/Prüf-/Klärungsfakten mit Evidenzquelle; exakte idempotente Abgangs-/Zugangsdeltas und Reconciliation.
8. Granulare Empfangsprobleme/Teilmengen/akzeptierter Schaden, Nichtankunft nach 7 Tagen, spätere Ankunft und qualifizierte Adminabschlüsse.
9. Individuelle Ratingberechtigung/-frist, blinde Publikation, positive Tags und angepasste Aggregation; bestehende Ratings/Qualifikation nicht rückwirkend ändern.
10. Deduplizierte Deadline-/Reminder-/To-do-Ereignisse und zustellsichere Notification-Anbindung. Kein öffentlicher Zuverlässigkeitsscore.

Neue Tabellen dürfen die alte zentrale Reservationquelle nicht durch eine unabhängige, von SAP ignorierte Supplywelt ersetzen. Bestehende Services mit eigenem Commit sind keine beliebig verschachtelbaren Bausteine. Technische Migrationen müssen spätere frische synthetische Testdaten, Backout-Grenzen und Dual-Contract-Regressionen nachweisen; keine Produktivaktivierung allein durch vorhandene Tabellen.

## 6. Konkrete Konflikte und Handlungsgrenzen

**Ausdrücklich durch den neuen Auftrag entschieden:** 3/3→offene outgoing 3; 24h-V1 bzw. bestehender Legacy-48h-Pfad→neuer 72h-Typ; beidseitige Pending-Bindung→einseitig; Pack-/Adress-Preview→gegenseitige Pflichtfotobarriere; 3-Sterne-Preview/globales Ratinggate→1–5 nach eigenem Empfang und blind. Diese Konflikte werden durch neuen Vertragsscope gelöst, nicht durch Änderungen an alten Vorgängen.

**Noch nicht vollständig entschieden:** D04 Abbruch-/Revisionsfristen, D05 Adresswechsel, D06 falscher gepflegter Bestand, D07 Rating-Uhr/Nichterhalt, D08 nur verbleibende Zugriffs-/Privacydetails, D09 administrative Restklärung/später Eingang. Vollständige Entscheidungsmatrix im Vertrag.

**Nicht als ungeprüfte Reparatur erlaubt:** NOT_SHIPPED einfach löschen; Receipt durch fremdes `ship()` simulieren; Legacy-Releases nach Versand aufrufen; neue Offer-Holds als V1 kennzeichnen; alter Preview-Slotzähler für offene Anfragen; alte Rating-Aggregate ungefiltert bei blinden Bewertungen; Gegenangebote durch Mutation desselben frozen Pakets; Datenbankversion beim Appstart automatisch hochziehen.

## 7. Fortschreibung LIFECYCLE-00A

D02 Empfang ohne Versandbestätigung ist entschieden: atomarer tatsächlicher Give-Abgang/akzeptierter Zugang mit gemeinsamem Exactly-once-Ledger und wirksamer Richtung versendet/angekommen. D03: 72h eigene Vorbereitung, separate Fotoprüfung ohne harte automatische Abbruchfrist. D08: aktuelle Prüfung vor Accept, danach eingefrorene relevante Zulässigkeit, auch für Reduktionen; Snapshotfelder im Vertrag §6a. Diese Regeln sind spezifiziert, weiterhin nicht implementiert.

Der konkrete [Need-Claims-/Mischbetriebsaudit](TRADE_LIFECYCLE_00A_NEED_CLAIMS.md) präzisiert: keine eigene Claim-Tabelle, sondern binäre Incoming-Projektion aus Requests/Positionen/Holds/Status. Legacy-`matching_states` und `TradeReservationService.accept` haben keine gleichwertige Incoming-Exklusivität. Ein gemeinsamer Hold-Reader allein beseitigt diese semantische Grenze nicht. D01 ist durch 00B entschieden: mengenbasierte Option A, keine Parallelengine. Der binäre Ist-Reader muss später mengenfähig erweitert werden; keine Runtimeänderung in diesem Paket.

## 8. Abschluss 00B / neue technische Lücke

TRADE-LIFECYCLE-V1 ist fachlich geschlossen; keine bekannte Fachentscheidung blockiert den Start von L01. Option A ist verbindlich. Neben der einseitigen Pending-Bindung fehlt heute die neue **mengenbasierte Bedarfsprojektion**: `_pieces` liefert im Ist eine fehlende Kopie, `incoming_committed_quantity` einen Indikator. Das erfüllt den neuen Fall Bedarf 2 / Claim 1 / Rest 1 noch nicht. Autoritative Gesamtbedarfsdaten, Claim-Mengen und versionsbezogene Überführung sind später zu modellieren; keine zusätzliche Domainentscheidung über Option A erforderlich.

Neue Vertragsidentität, Claim-/Hold-Transaktionen und gemeinsamer Ledger bleiben technische Implementierungslücken. Geschlossener Fachvertrag bedeutet weder implementiert noch Migration/Launch genehmigt. Rechts-/Datenschutzprüfung und die paketbezogenen späteren Detailgates bleiben ausdrücklich erhalten.
