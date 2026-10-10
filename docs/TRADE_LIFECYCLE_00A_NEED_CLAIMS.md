# LIFECYCLE-00A — Need-Claims und Mischbetrieb

> Historischer Entscheidungsstand. Fortschreibung vom 11.10.2026: Für LIFECYCLE-07 ersetzt der aktuelle [Fachvertrag §11](TRADE_LIFECYCLE_V1_CONTRACT.md#11-tatsächlicher-empfang-ohne-versandklick) die frühere A/D02-Regel zu nur belegten Teilabgängen und frühem Empfang. Verbindliche Buchung erst nach beidseitiger Vorbereitung, Fotoprüfung und gegenseitiger Adressfreigabe; ohne manual_sent vollständige bindende Give-Menge abbuchen, ausschließlich akzeptierte Receive-Mengen gutschreiben. Die folgenden historischen Aussagen bleiben zur Nachvollziehbarkeit erhalten.


Stand 2026-10-06; geprüfter Source-HEAD `e20a8c4e84f2adb83b2f4f3f870846267713a4c1`. Reiner Source-/Schemaaudit, keine Abfrage privater DB-Inhalte. Tabellenbefunde stammen aus versionierten SQL-Dateien, nicht aus einer behaupteten Migration der lokalen DB. „Neuer V1“ bedeutet Lifecycle V1, ausdrücklich nicht den vorhandenen `smartdeal_v1`.

## 1. Was heute tatsächlich existiert

**Ein Need-Claim ist heute kein eigenständiger persistierter Datensatz und kein eigener Reservationstyp.** Der Begriff aus LIFECYCLE-00 beschreibt die abgeleitete Bindung eines fehlenden Albumcodes durch eine wirksame eingehende Tradeposition. Physischer Bestand, Supply-Reservierung, geplanter Eingang und freier Bedarf sind verschiedene Größen.

Der konkrete Reader ist [SmartDealPlanningService](../App/services/smartdeal_planning.py):

- `PlanningBinding.incoming_committed_quantity` ist in `_project_bindings` ein **0/1-Indikator**, nicht die erwartete physische Liefermenge.
- `_pieces` bildet eine Menge aus `(album_id, sticker_code)`. Bei physischer Menge null entsteht `missing` mit Menge 1. Ohne Zusage steht der Code auch in `needs`; mit Zusage stattdessen in `incoming_committed_needs`.
- Zwei eingehende Zusagen werden nicht zu zwei benötigten Exemplaren addiert. Es gibt hier keinen frei einstellbaren Mehrfachbedarf und keine globale Unique-Constraint für genau eine eingehende Zusage je Nutzer/Album/Code.
- Supply wird separat aus physischem Bestand minus geschütztem Eigenexemplar minus wirksamen aktiven Reservierungen gebildet. Ein Need-Claim ist keine zusätzliche Abbuchung und kein Besitz.

### Relevante Persistenz und Objekte

| Quelle | Bedeutung |
|---|---|
| `stickers.user_id, album_id, sticker_code, quantity` | Tatsächlicher gepflegter Nutzerbestand; Bedarf entsteht aus fehlendem physischen Exemplar. |
| `trade_requests.id, status, contract_type, binding_created_at, accepted_at` | Vertrag und Bindungsphase; Contract-Felder durch Migration 0021. |
| `trades.legacy_trade_request_id, requester_user_id, partner_user_id, lifecycle_state` | Zuordnung und operative Phase. |
| `trade_positions.id, trade_id, from_user_id, to_user_id, album_id, sticker_code, quantity` | Konkrete Richtung und zugesagte Menge; Grundlage der Projektion. |
| `trade_reservations.trade_position_id, trade_id, user_id, album_id, sticker_code, quantity, state` | Physischer Give-Hold, heute `active`/`released`; kein separates Need-Feld. |
| `trade_shipping_status`, `trade_receipt_status` | Richtungsflags; Zusage bleibt nach Versand trotz freigegebenem Hold bis Empfang relevant. |
| `trade_receipt_report_positions.initial_received_quantity, resolution_received_quantity` | Bereits gebuchte Teilmengen, aus denen verbleibende Positionen abgeleitet werden. |
| `PlanningState`, `PlanningBinding`, `PlanningPiece` | Flüchtige Python-Projektionen, keine zusätzlichen DB-Tabellen. |

Schemaquellen: [0001](../App/Database/migrations/0001_trade_lifecycle_foundation.up.sql), [0002](../App/Database/migrations/0002_trade_reservations.up.sql), [0021](../App/Database/migrations/0021_smartdeal_contract_foundation.up.sql). Die Detailtabellen und späteren Ledger-Lücken sind im [Gap-Audit](TRADE_LIFECYCLE_V1_GAP_ANALYSIS.md) erfasst.

## 2. Lebenslauf einer heutigen Zusage

`_project_bindings` bewertet pro Request:

1. Legacy: wirksam bei `status='accepted'` und Lifecycle `accepted`, `partially_shipped`, `shipped`, `partially_received` oder `problem_open`.
2. Expliziter `smartdeal_v1`: zusätzlich wirksam im offenen Zustand innerhalb der absoluten 24h, aber nur mit vollständig materialisierten **beidseitigen** Positionen und aktiven Holds sowie konsistenten Zeitpunkten. Unvollständige Bindung führt zum Fehler, nicht zum Legacy-Fallback.
3. Eine eingehende Position erzeugt den Indikator nur bei wirksamer Bindung, noch nicht abgeschlossenem Empfang, positiver Restmenge und aktivem Hold **oder** bestätigtem Versand des Gebers.
4. Erst `_pieces` unterscheidet physisch noch fehlend und bereits zugesagt. Ist inzwischen eine physische Kopie vorhanden, besteht kein freier Sammelbedarf, auch wenn noch eine Lieferung offen ist.

| Fachwort | Tatsächlicher heutiger Vorgang |
|---|---|
| Erzeugen/reservieren | Legacy-Accept materialisiert Positionen und beide Supply-Holds; daraus wird die Zusage lesend abgeleitet. Explizites SmartDeal-V1-Create macht dies bereits beim Absenden. Eine normale offene Legacy-Anfrage allein erzeugt diese Bindung nicht. |
| Verändern | Request-/Lifecycle-, Hold-, Versand-, Empfangs- oder Teilmengenänderung verändert die nächste Projektion. Kein `UPDATE need_claim`. |
| Konsumieren | Physischer Empfang wird über Inventory-/History-Pfade gebucht. Physischer Bedarf verschwindet; empfangene Mengen bzw. Richtungsabschluss beenden die projizierte Zusage. |
| Freigeben | Terminale/abgelaufene V1-Bindung oder beendeter Legacy-Lifecycle verliert seine eingehende Wirkung. Physische Holds werden separat freigegeben. Nach Versand darf Hold-Freigabe allein die eingehende Zusage nicht entfernen. |
| Löschen/abschließen | Kein eigenes Claim-Delete. Historische Requests/Positionen können bleiben; Projektion liefert keinen aktiven Bedarfsschutz mehr. |

Wichtiger Unterschied: Der Planner ignoriert abgelaufene explizite V1-Holds logisch; rohe Inventory-Abfragen zählen gespeicherte aktive Holds bis zum Release weiter. [SmartDealRequestService._create_locked](../App/services/smartdeal_requests.py) prüft deshalb zusätzlich die gespeicherte Inventory-Verfügbarkeit. Eine neue Implementierung darf diese zwei Sichten nicht durch ungesichertes vorzeitiges Recyceln vermischen.

## 3. Welche Pfade was berücksichtigen

| Pfad | Bedarf / Supply / Grenze |
|---|---|
| [InventoryReadService.matching_states](../App/services/inventory.py) | Bedarf ausschließlich `catalog_codes - physical_codes`; Supply berücksichtigt alle aktiven Reservierungen. Incoming-Transit beeinflusst ausdrücklich nicht `missing_codes`. |
| `InventoryReadService._transit_by_code` | Eigene Anzeigeprojektion versendeter, noch nicht empfangener Restmengen. **Nicht identisch** mit dem schon vor Versand wirkenden Planning-Claim. |
| [TradeReservationService.accept / _assert_available](../App/services/trade_reservations.py) | `BEGIN IMMEDIATE`, Prüfung der Give-Verfügbarkeit, beide Holds; keine globale Prüfung fremder Incoming-Need-Claims. |
| Legacy `/trade/<id>/accept` in [webapp.py](../App/webapp.py) | Dispatch zuerst; Legacy-Smart-Paket zusätzlich `SmartTradeRequestService.inspect(recheck=True)`, danach Reservation-Service. Dies ersetzt keinen gemeinsamen Need-Unique-Guard. |
| [SmartTradeRequestService](../App/services/smart_trade_requests.py) | Älterer S22-Smartpfad, anderer Vertrag/48h; nicht mit explizitem V1 verwechseln. |
| [SmartDealRequestService](../App/services/smartdeal_requests.py) | Explizites V1: aktuelle Planungsvalidierung, Paketidentität/Dedupe, beide Holds; `_assert_projected` prüft, dass neue eingehende Zusagen freie Needs entfernen. |
| [SmartDealAcceptanceService._currently_executable](../App/services/smartdeal_acceptance.py) | Prüft physisches Missing und fremde Incoming-Bindungen; eigene Request-Bindung wird aus der Konkurrenzmenge ausgeschlossen. |
| [SmartDealReleaseService](../App/services/smartdeal_release.py) | Release und Sweep nur für entsprechenden alten Vertrag; danach keine wirksame Bindung dieses Requests. |
| [trade_shipping](../App/services/trade_shipping.py), [trade_receipt](../App/services/trade_receipt.py), [trade_problems](../App/services/trade_problems.py) | Legacy-Abgang, Eingang, Teil-/Problemabschluss verändern die zugrunde liegenden Fakten; kein eigenständiger Claim-Service. |
| [TradeV2Domain.market / validate_deal](../App/services/trade_v2_domain.py) | SAP nutzt dieselbe SmartDealPlanning-Projektion, beide Need-/Supply-Seiten und gemeinsame Balance. Noch kein neuer Lifecycle-Writer. |
| [trade_planning_compat](../App/services/trade_planning_compat.py) | Älteres Schema ohne Contract-Felder wird lesend als Legacy adaptiert, nicht migriert. |
| SAP/Profile/manual-check | [trade_search](../App/services/trade_search.py), [trade_shell](../App/trade_shell.py), [profile_trade](../App/profile_trade.py): aktuelle Domainberechnung/Prüfung. Kein eigener Need-Persistenzpfad. |
| `App/trade_v2/` Preview | Browserzustände sind keine verbindlichen, gemeinsam transaktionalen Need-Claims. |

## 4. Was „Mischbetrieb“ konkret bedeutet

Bestehende Legacy- und explizite SmartDeal-V1-Vorgänge laufen weiter, während neue Lifecycle-V1-Vorgänge denselben realen Nutzerbestand verwenden. Nicht gemeint ist ein Trade, dessen einzelne Aktionen zwischen Verträgen wechseln.

**Heute existiert noch kein neuer Lifecycle-V1-Writer.** Die folgenden Risiken sind daher durch Source belegte Integrationsrisiken, keine Behauptung bereits aufgetretener Schäden in privaten Daten.

- **Physischer Bestand/Doppelte:** Gemeinsame `stickers`-Zeilen. Mengen verschiedener Verträge können dieselben freien Exemplare beanspruchen. Ein zentraler aktiver Hold-Summenwert kann das schützen, wenn wirklich alle Writers ihn innerhalb derselben Transaktion prüfen.
- **Reservations:** Inventory/Guards summieren `trade_reservations` vertragsübergreifend. Separate unsichtbare neue Hold-Tabellen würden alte Writers zu viel Supply sehen lassen. Neue Freigaben müssen exakt Vertrag, Trade, Richtung und Position besitzen, nicht pauschal Nutzer/Code freigeben.
- **Needs:** Keine globale exklusive DB-Ressource. SAP/SmartDeal unterdrückt zugesagte fehlende Codes, ältere Matching-/Accept-Pfade nicht überall. Serialisierung allein macht unterschiedliche fachliche Prüfungen nicht gleich.
- **Konkretes Beispiel:** Zwei unterschiedliche Geber haben je eine freie BRA-3-Kopie. Ein Legacy-Accept und ein neuer Accept können beide eine Lieferung an denselben physisch noch leeren Empfänger vereinbaren. Es wird dabei keine einzelne Give-Kopie doppelt reserviert. Trotzdem kann aus einer Sammellücke eine doppelte erwartete Lieferung werden. Das ist ein Bedarfs-/Planungskonflikt, nicht automatisch eine fehlerhafte Bestandsbuchung.
- **Supply-Race:** Beide Writers lesen dieselbe letzte freie Kopie vor der Schreibtransaktion; beide reservieren später → Überbindung. `BEGIN IMMEDIATE` mit frischer gemeinsamer Prüfung verhindert dies nur, wenn kein Writer einen alten Previewwert benutzt.
- **Selbstblockierung:** Neue Accept-Prüfung zieht den eigenen Pending-Hold/Claim wie fremde Konkurrenz ab → gültiger eigener Deal erscheint ungültig. Eigene Identität muss korrekt gutgeschrieben werden.
- **Falscher Vertrag:** Neuer einseitiger Hold unter `smartdeal_v1` verletzt dessen beidseitige Vollständigkeit. Unbekannter Typ wird heute abgewiesen. Nur Enum erweitern reicht nicht.
- **Doppelbuchung:** Legacy-Ship und neuer Receipt-Evidence-Command dürften nicht denselben Trade bearbeiten. Neuer Ship und neuer Receipt benötigen zusätzlich denselben Exactly-once-Abgangsledger.
- **Ablauf/Release:** Alter 24h-Sweep darf keine neuen 72h-Holds anfassen. Logisch abgelaufen und physisch freigegeben müssen beim neuen Writer konsistent zusammenspielen.

### Keine unerfüllbare Garantie behaupten

Unveränderte Altverträge **und** rückwirkend strikte Incoming-Need-Exklusivität sämtlicher Alt-Accepts sind nicht gleichzeitig garantiert: Der Legacy-Reservation-Service prüft diese Exklusivität heute nicht. Ein neuer Need-Guard, der ein bisher zulässiges Alt-Accept verbietet, wäre eine zusätzliche Legacy-Semantikänderung. Diese Analyse empfiehlt das nicht.

Bestandsschutz bleibt dagegen vertragsübergreifend zwingend. Eine im Altvertrag zulässige zusätzliche erwartete Lieferung muss als weiterer physischer Eingang korrekt gebucht werden können; sie darf weder eine Kopie erfinden noch einen angenommenen neuen Deal automatisch auflösen. Neue V1-Angebote werden vor Annahme gegen alle dann wirksamen bekannten Zusagen revalidiert. Spätere Alt-Accepts können unter ihren alten Regeln weiterhin eine zusätzliche Zusage erzeugen. Das ist als begrenzte Übergangseigenschaft auslaufender Altangebote zu dokumentieren, nicht als globale Need-Unique-Garantie zu verkaufen.

## 5. Contract-Type und Tragfähigkeit der Zielidee

[trade_contracts.py](../App/services/trade_contracts.py) kennt `legacy` und `smartdeal_v1`; fehlendes Feld vor Schema 21 bedeutet Legacy, unbekannter expliziter Wert wirft einen Fehler. Migration 0021 ergänzt einen CHECK und einen Unveränderlichkeitstrigger. Die Klassifikation liegt an `trade_requests`, `trades` verweist über `legacy_trade_request_id` darauf. Herkunft/Smart-Marker sind kein Ersatz.

[smartdeal_runtime.dispatch_request](../App/services/smartdeal_runtime.py) ist bereits eine produktive Grenze: `None` nur für Legacy, explizites V1 an eigene Accept/Release-Services, sonst `LIFECYCLE_UNAVAILABLE`. Diese Grenze muss später um den neuen Typ und seine eigenen Commands ergänzt werden, ebenso Reader, Jobfilter und direkte Serviceguards. Vorhandene interne Legacy-Services sind nicht allein durch ihre Namen gegen falsche Aufrufe geschützt.

**Zielmodell tragfähig, aber nicht im heutigen Code einfach einschaltbar:** ein unveränderlicher neuer Contract-Type, getrennte Lifecycle-Commands und gemeinsame physische Inventory-/Hold-Infrastruktur. Keine zweite Bestandswelt. Bestehende Legacy-Trades können so nach alten Regeln auslaufen; neue Erstellung muss nach Cutover über sämtliche alten Erstellungsrouten gesperrt/auf den neuen Pfad gelenkt werden. Vorhandene Requests behalten ihren Typ. Auslaufendes `smartdeal_v1` ist separat zu berücksichtigen: dessen physische Commands sind aktuell ausdrücklich noch nicht freigegeben; „alle Altarten schon vollständig lauffähig“ wäre eine falsche Aussage.

Späterer Migrationsbedarf: neuer zulässiger Vertrag mit unveränderlicher Zuordnung, neue Offer-/Dealrevisionen, Rule-Snapshot und Mengen-/Commandledger. Gemeinsame Hold-Anbindung mit eindeutigem Owner; keine Migration alter Vertragsinhalte. Konkrete Tabellen/Nummern erst im genehmigten technischen Entwurf. Kein Anspruch, Rollback auf alten Code könne neue Typen bereits lesen.

## 6. Historischer Optionenvergleich — durch 00B entschieden

00B hat **Option A verbindlich gewählt**, mit mengenbasierter Erweiterung. B und C sind verworfene Alternativen; die Tabelle bewahrt die technische Begründung des damaligen Vergleichs. Alle bewahren den unter §4 beschriebenen Altvertrag und gemeinsamen physischen Bestandsschutz.

| Aspekt | OPTION A — eigener Bedarf bereits bei Sendung gebunden | OPTION B — neuer Bedarf erst bei Annahme gebunden | OPTION C — neue Erstellung erst nach vollständigem Alt-Auslauf |
|---|---|---|---|
| Funktionsweise | Neue offene Anfrage bindet eigene Give-Supply und eigene Receive-Needs; niemals fremde Supply/Needs. Bei Accept beide Richtungen. | Pending bindet nur eigene Give-Supply. Mehrere eigene Angebote dürfen dieselbe eigene Lücke anfragen; erst Accept bindet Bedarf. | Keine gleichzeitigen neuen/alten operativen Vorgänge; danach neue Semantik, empfohlen wie A. |
| Spätere Änderungen | Zentraler vertragsabhängiger Binding-Reader und atomare neue Commands; eigene Claims bei Revalidierung ausschließen. | Gleiche Supply-/Contract-Arbeit; Need-Claims erst accepted, konkurrierende offene Angebote häufiger ungültig. | Globaler Cutover-/Drain-Gate zusätzlich; alte Erstellung stoppen, Alt-Abwicklung verfügbar halten. |
| Bestehende Trades | Unverändert; deren wirksame Zusagen berücksichtigt. Alt-Accept kann weiter zusätzliche Zusage erzeugen, siehe §4. | Unverändert; gleiche Grenze. | Unverändert, müssen aber erst auslaufen; Alt-Probleme können Einführung unbestimmt verzögern. |
| Reservation/Inventory | Gemeinsame Give-Holds, kein eigener physischer Need-Bestand. Projektion ergänzt um einseitige Claims. | Gleiche Give-Holds; zentrale Need-Projektion für neue Angebote bis Accept ohne Claim. | Gemeinsamer Bestand weiter nötig; kein gleichzeitiger operativer Alt-/Neu-Wettbewerb. |
| Migration | Neue Vertrags-/Offerpersistenz ohnehin nötig; Claim aus autoritativer Revision/Status ableitbar, separate Claim-Tabelle nicht zwingend. | Gleiche Grundlage; andere Gültigkeitsphase der Projektion. | Neue Persistenz bleibt erforderlich; Drain ersetzt keine Lifecycle-Migration. |
| Concurrency | Send/Accept/Counter/Release unter gleicher Schreibgrenze; klare Claim-Identität. Alt-Neu-Need-Ausnahme bleibt bewusst bestehen. | Accept-Races entscheiden über ersten neuen Claim; weitere Angebote müssen bei Prüfung nachvollziehbar scheitern. | Gate muss neue Alt-Erstellung zuverlässig verhindern; sonst kein echter Drain. |
| Rollback/Deployment | Erst Reader/Guards und neue Typunterstützung, dann Writes; bei Rollback neue Erstellung sperren, aktive neue Trades weiter bedienen. | Gleiche Grenze, zusätzlich mehr wartende Konfliktangebote. | Lange Wartungs-/Einführungsphase; darf offene physische Trades nicht zum Abbruch zwingen. |
| Vorteil | Verhindert paralleles Bewerben derselben eigenen Lücke in neuen Angeboten; nutzt existierende Incoming-Projektion, keine Parallelengine. | Größere Auswahl konkurrierender Angebote; weniger Bindung vor Annahme. | Vermeidet operative Alt-Neu-Need-Kollision ohne Legacy-Neuregelung. |
| Nachteil | 72h wartende eigene Anfrage unterdrückt diesen eigenen Bedarf in anderen neuen Deals; Release muss zuverlässig sein. | Mehr scheinbar passende Angebote, von denen später nur eines angenommen werden kann. | Für bestehende lange/problematische Trades unverhältnismäßige Blockade des gesamten Starts. |

## 7. Verbindliche Entscheidung durch LIFECYCLE-00B

**OPTION A IST FIX. TRADE-LIFECYCLE-V1 IST FACHLICH GESCHLOSSEN.** Es gibt keine offene Option-A/B-Frage und keine bekannte fachliche Startblockade von L01. Dies ist keine Runtime-/Migrations-/Produktionsfreigabe; spätere Detail- und Launch-Gates bleiben bestehen.

Eigene Give-Mengen und eigene gewünschte Receive-Need-Mengen werden bei Send gleichzeitig atomar gebunden. Fremder physischer Bestand wird nicht reserviert. Bei Withdraw, Decline, 72h-Ablauf oder endgültigem Invalidieren/Beenden werden beide Bindungen gelöst; beim Counter gemeinsam ersetzt; bei Accept nach vollständiger Revalidierung in den verbindlichen beidseitigen Deal überführt. Keine Geister-Claims oder freie Zwischenphase.

**Mengen statt Boolean:** Die §§1–3 beschreiben den heutigen binären Reader, nicht die neue Zielsemantik. Gesamtbedarf 2, vorhandener deckender Bestand 0, verbindliche Eingänge 0, eigener Pending-Claim 1 ergibt Restbedarf 1. Bestand, verbindliche Resteingänge und eigene Pending-Claims dürfen nicht doppelt gezählt werden. Autoritative Gesamtbedarfsmenge und mengenfähiger Adapter sind spätere technische Persistenzarbeit; keine neue Settings-UI wird hier gebaut. Vollständige Formel/Übergänge im Vertrag §3a.

Ein neuer unveränderlicher Contract-Type trennt jeden Trade vollständig von Legacy und `smartdeal_v1`. Die gemeinsame physische Supply und ihr Guard bleiben vertragsübergreifend. Alte Vorgänge laufen unverändert aus; keine rückwirkende globale Need-Exklusivität. Die begrenzte Legacy-Need-Abweichung aus §4 bleibt ausdrücklich dokumentiert.

Claim-Key umfasst Nutzer/Album/Code, Menge und Contract-/Offer-/Richtungsidentität. Eigene Claims bei Revalidierung als bereits diesem Angebot zugeordnet berücksichtigen. Keine implizite Mutual-GO-Annahme; Retries verwenden dieselbe Command-/Angebotsidentität. Neue Dreierquote zählt offene neue Anfragen; Altzähler behalten ihren Scope.

## 8. Drei verbindliche Entscheidungen aus 00A

- **A / D02 entschieden:** Empfang darf fehlende Versandbestätigung atomar nachführen: betroffene tatsächlich versendete Give-Mengen genau einmal abbuchen, akzeptierte Eingänge buchen, wirksame Richtung versendet/angekommen. Späterer/paralleler Versand darf nicht doppelt buchen. Quelle Empfängerbeleg statt erfundener Absenderklick; Teil-/Problemzugang nur tatsächlich akzeptierte Menge. Kein pauschaler Vollzugang. Nicht belegte Restmengen bleiben differenziert im Problem-/Mengenledger, keine erfundene physische Bewegung.
- **B / D03 entschieden:** `accepted_at + 72h` für eigene Packliste, Vorbereitung, Fotos und Abschluss. Danach eigene gegenseitige Prüfphase ohne harte automatische Abbruchfrist; Reminder-/Eskalationsereignisse erforderlich. Versand weiter `address_released_at + 72h`.
- **C / D08 Regelteil entschieden:** Vor Accept aktuelle Prüfung; bei Accept versionierter Regel-Snapshot. Globale Pool-/Cross-Präferenzänderungen sabotieren weder angenommenen Deal noch dessen Reduktion. Grundlegende Bestands-/Berechtigungs-/Datenschutzinvarianten gelten weiter. Konkrete Snapshotdaten stehen im Vertrag §6a.

## 9. Integritätsprüfung und Ende

Keine Runtime-Tests erforderlich oder ausgeführt. Source nur gelesen, kein Appstart, keine DB-Verbindung; DB-Dateien ausschließlich gehasht. Abschlussprüfung und exakte Dokumentliste im [aktualisierten Audit](TRADE_LIFECYCLE_00_AUDIT.md#15-lifecycle-00a--fortschreibung). Keine Migration erstellt/ausgeführt. 00A selbst ohne Staging/Commit/Push; 00B autorisiert ausschließlich den Dokumentationscommit und Push. Kein Deploy oder LIFECYCLE-01.
