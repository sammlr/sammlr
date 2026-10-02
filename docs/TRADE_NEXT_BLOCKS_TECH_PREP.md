# Trade Next Blocks — Technical Prep

Stand 2026-09-13. Phase C nach verbindlichem PO-Entscheid NP-C3-1 abgeschlossen. T7a/T8a technische Vorbereitung und T9 statischer Route-/IA-Audit abgeschlossen; keine Implementierung oder Laufzeitabnahme. Der frühere C3-STOP ist aufgehoben.

Grundlagen: Q1–Q8 Decision Record, Trade UX SOLL, Product Bible einschließlich gezielter Night-Prep-Präzisierung, unveränderter Algorithm Contract AC25/26/27, Roadmap T7a/b/T8a/T9, T5a/T5b/T6b-Berichte und CG-1-Reaudit. Bestehende Core-/Design-/CG-1-Baseline GREEN, Full Release 1251/1251 als vorhandener Nachweis. Keine Tests in diesem Dokumentationsauftrag.

## C1. T7a Shipping / Receipt / Completion

### Reale Anschlussstellen

`TradeShippingService.ship` erwirbt BEGIN IMMEDIATE, prüft Teilnehmer/Lifecycle und vollständige aktive eigene Reservationen, gibt deren Supply mit Grund shipped frei und bucht je Position aus. Bei installiertem Cutover verwendet es `HistoricalInventoryWriteService.remove` mit Eventkey `trade-shipping:{trade}:{side}:{position}`; danach Versandflag und aktueller Timestamp. Diesen Command nicht stellvertretend beim Empfang aufrufen: Er würde einen Versandklick/Versandzeitpunkt behaupten und besitzt eigene TX-/Actorsemantik.

`TradeReceiptService.receive` joint Request/Trade/Shippingstatus, prüft Empfänger und dessen bereits bestätigten Empfang, verlangt derzeit einen passenden Lifecycle und Partner-Shippedflag. Ohne Flag NOT_SHIPPED. Bei normalem Vollreceipt bucht es Positionen genau einmal über `HistoricalInventoryWriteService.add` mit Eventkey `trade-receipt:{trade}:{side}:{position}` und ruft `finalize_received_side`. Partielle/problematische Meldungen laufen über `TradeProblemService`, keine pauschale Vollmengenbuchung.

`finalize_received_side`/bestehende Completion-Projektionen, History-Cutover, SuccessfulTradeProjection und Ratings sind wiederverwendbare Grundlagen, müssen aber auf die neue physische Evidenz abgebildet werden. Rating erlaubt qualifizierte Problemabschlüsse; diese bleiben von normalem Erfolg getrennt. Typed-Katalog enthält Versand und Problemhandlung, aber keine fertige gemeinsame Accept-/Mutual-Notification; Q7 verlangt deren spätere deduplizierte Ergänzung. Empfang selbst bleibt sichtbarer Status ohne eigenen Notification-Zwang.

CG-1 `smartdeal_runtime.dispatch_request` blockiert Ship/Receive/Complete/Fail/Problem für V1, und Webhandler delegieren Accept/Decline/Withdraw. Diese Sperren bleiben bis einer gezielten T7a-Abnahme bestehen. Alte Confirm-/Single-Album-Callbacks nicht wieder öffnen, bevor Multi-Album-/Exactly-once-Nachweise vorliegen. Neue manuelle Vertragsart ebenfalls explizit behandeln; kein Unknown-Contract-Fallback.

### Konkreter technischer Vorschlag zu Q2, keine Implementierungsentscheidung

1. Unter einer gemeinsamen atomaren Schreibgrenze den berechtigten Empfänger, Vertrag, konkrete Positionen und bereits vorhandene physische Buchungsfakten prüfen. Vollständigen Inhalt und Mengen aus Persistenz rekonstruieren, nicht aus Clientdaten vertrauen.
2. Zwischen **expliziter Versandbestätigung**, **durch Empfang belegtem Verlassen des Geberbestands** und **Empfangsbestätigung** unterscheiden. Der zweite Fakt benötigt keine erfundene historische Versandzeit. Ein neu persistierter Evidenz-/Buchungszeitpunkt bedeutet Zeitpunkt der Erfassung, nicht Datum des damaligen Versands.
3. Pro gerichteter Position dauerhafte einmalige Ausbuchungs-/Eingangsfakten verwenden. Normales Ship und spätere Receipt-Ableitung müssen denselben Ausbuchungsnachweis konsumieren, damit ein später nachgeholter Shipklick nicht nochmals entfernt. Vorhandene Eventkeys/History-Mechanik prüfen und für neue Vertragsarten gezielt erweitern; bestehende Legacy-Keys nicht rückwirkend ersetzen.
4. Bei bestätigtem Vollreceipt ohne früheren Shipfakt: noch ausstehende notwendige Geberausbuchung und Empfängereinbuchung gemeinsam atomar herstellen. Geber-Reservation entsprechend überführen, zugehörigen Need physisch erfüllen, keine zwischenzeitlich wieder frei verplanbare Kopie. Existiert die Geberausbuchung bereits, nur den fehlenden Eingang buchen. Kein verschachtelter Aufruf zweier jeweils selbst commitender Services.
5. Tatsächliche Empfangsinformation beziehungsweise deren Bestätigung korrekt persistieren. Erfassungszeit nicht als unbekannten historischen Versandzeitpunkt ausgeben; `shipped_at` bei unbekanntem Versanddatum nicht künstlich aus receipt_at ableiten. Darstellung kann „Empfang bestätigt, Versandzeit nicht erfasst“ transportieren, endgültige Microcopy offen.
6. Teil-/Fehlempfang: nur tatsächlich bestätigte Eingänge buchen, Mengen-/Problembericht erhalten. Nachweis einer Teilankunft beweist nicht automatisch den Versand aller übrigen Positionen; Restbindung/-problem nicht durch Vollreceipt überschreiben. Bestehenden Partial-/Problemvertrag nutzen, tatsächliche zusätzliche physische Fakten explizit erfassen.
7. Bei widersprüchlichem Bestand keine negative Buchung oder stilles Überspringen. Bestehende Integritäts-/Fehlergrenze erhalten und Problem sichtbar machen; ein fehlgeschlagener physischer Übergang darf nicht als abgeschlossener Empfang erscheinen. Dedupe prüft tatsächliche Buchungsfakten statt nur UI-Flags.
8. Erfolgreicher Normalabschluss erst wenn beide Empfänge vollständig und konsistent sind; nicht nur beide Shippedflags. Problemabschluss bleibt separat. History/Erfolg/Rating-Eligibility aus denselben Fakten, Notification nicht doppelt.

Schemaeinschätzung: Neue Evidenz ohne erfundenes `shipped_at` passt möglicherweise nicht in alle bestehenden Flag-/Timestamp-CHECKs. Erst vorhandene Tabellen/Constraints und Eventmodell vollständig gegen diesen Vorschlag prüfen; Erweiterung möglich, keine Migration festgelegt oder erstellt. Die konkrete Darstellung eines unbekannten Versandzeitpunkts ist Technik-/Datenmodellarbeit innerhalb Q2, keine neue Pflicht zu einem erfundenen Datum.

Spätere T7a-Gates: normales Ship→Receipt, Receipt ohne Ship, späterer Ship nach Receipt, Retry beider Commands, zwei parallele Commands in beiden Reihenfolgen, Voll-/Teil-/Fehlempfang, Mehralbum, Unterdeckung, Rollback zwischen Geberabgang und Eingang, beide Empfänge→Completion, Rating nach qualifiziertem Problemabschluss, Legacy-Kontrolle. Keine Tests implementiert.

## C2. T7b Unfulfillable / Problems

Q1 bestätigt Bible §37.4 und AC25/26 vollständig: Vor jeglichem physischem Versand betroffenen Vertrag ganz beenden/freigeben/informieren, eingefrorenes Paket erhalten, vollständig neu berechnen. Keine Gegenstückauswahl, kein Rebalancing und keine alte Instanz bevorzugt reparieren. Nach erstem physischen Versand Problem-/Action-required-Weg, keine gewöhnliche automatische Vollfreigabe oder fiktive Rückbuchung.

AC26-Priorität bleibt unverändert: accepted vor open, innerhalb Stufe maßgebliches Bindungsalter, stabiler numerischer ID-Tie-Break. Für accepted maßgeblich accepted_at, nicht einfach GO-Zeit. Nach jeder vollständigen Freigabe Deckung erneut prüfen, keine zusätzlichen Verträge unnötig beenden. Versandte Vorgänge nicht automatisch auswählen; tatsächliche Legacy-Bindungen respektieren.

Reuse: InventoryGuard/InventoryWrite/History-Cutover für kanonische physische Änderung; T5b-Release-Prinzip für Pending; Reservationsmaterialisierung und Projektionsprüfung; `TradeProblemService` für reale Partial-/Rest-/Problemfakten, vorhandene Typed-Problem-/Unfulfillable-Nachrichten. T5b schützt Accepted ausdrücklich vor Pending-Release und ist deshalb kein ungeprüfter allgemeiner Accepted-Unfulfillable-Command. T7b braucht hierfür einen gesondert freigegebenen Übergang.

Receipt-Evidenz aus C1 muss als physischer Versandnachweis gelten, auch wenn der alte Versandklick fehlt. Sonst könnte T7b nach tatsächlicher Ankunft fälschlich „vor Versand“ annehmen. Keine erfundene Vollreceipt-Meldung verwenden, um fehlende Restlieferbarkeit sichtbar zu machen. Keine Runtimeänderung.

## C3. T8a Shipping Contact — GREEN (Tech Prep)

NP-C3-1 ist durch PO geschlossen; verbindlicher Wortlaut und Grenzen im [Decision Record](TRADE_UX_PO_DECISIONS_Q1_Q8.md#np-c3-1--versandkontakt-po-entscheidung-2026-09-13). Keine weitere echte RED-Produktfrage entstanden.

### Anschlussstellen und vorgeschlagener technischer Vertrag

Die vorhandenen Teilnehmer-/Lifecycle-Prüfungen, AccountLifecycleService und UserDataExportService sind Anschlussstellen, kein bereits implementierter Versandkontaktservice. Die vorhandenen Trade-, Profil-, History- und Notificationprojektionen dürfen nicht durch eine allgemeine Adressprojektion erweitert werden. Neue manuelle angenommene Verträge brauchen später dieselbe autorisierte Kontaktgrenze wie bestätigte SmartDeals; offene Anfragen und Drafts begründen keine Partnerfreigabe.

| Vorgang | Technische Vorbereitung innerhalb des PO-Vertrags |
| --- | --- |
| Eingabe | Eigentümer erfasst/validiert Adresse. Kontaktinhalt, optionale Wiederverwendungsvorlage und konkrete Tradefreigabe getrennt modellieren; Schema noch nicht festgelegt |
| Freigabe | Expliziter Command für bestätigten konkreten Trade und berechtigten Partner. Server prüft Actor, Teilnehmer, Lifecycle und konkrete Inhaltsversion; keine aus Profil oder früherem Trade geerbte Freigabe |
| Bewusstes Anzeigen | Autorisierter Read nach konkreter Freigabe; aktuelle Berechtigung bei jedem Read prüfen. Anzeigen erzeugt keine Zustimmung und kein weiteres Zugriffsrecht |
| Optional speichern | Gesonderte Eigentümerentscheidung. Neue Trades benötigen auch mit Vorlage jeweils eine neue Freigabe. Vorlage nicht automatisch in Partnerdaten projizieren |
| Änderung | Vorschlag: Inhaltsversionen getrennt halten; Vorlagenänderung nicht still als Änderung einer bereits freigegebenen Tradeadresse behandeln. Konkrete geänderte Tradeadresse ausdrücklich bestätigen/freigeben; laufenden physischen Weg konsistent erhalten |
| Widerruf | Zukünftige Partneranzeige/Freigabe unmittelbar beenden, soweit kein bereits notwendiger physischer Abwicklungsweg unmöglich wird. Eine notwendige Ausnahme nur konkret zweckbezogen und nachvollziehbar prüfen; kein pauschales Fortbestehen der Freigabe bei accepted/problem |
| Normalabschluss | Partnerzugriff endet. Vergangener Trade und Historyeintrag erlauben keine dauerhafte Adressanzeige |
| Offenes Problem | Nur für diesen Fall notwendige Daten intern zweckgebunden erhalten. Daraus folgt keinerlei neues oder erweitertes Partnerrecht |
| Support | Konkreter berechtigter Fall, Erforderlichkeit und serverseitige Autorisierung bei jedem Zugriff; Zugriff mit Actor, Fall, Zweck und Zeitpunkt nachvollziehbar protokollieren. Keine allgemeine Support-Adresssuche/-projektion |
| Accountende | Aktive physische Abwicklung/offenen Problemfall konsistent erhalten; notwendige Daten zweckgebunden bis zur Erledigung sichern. Danach löschen/anonymisieren, soweit keine zwingende andere Aufbewahrungspflicht besteht |
| Vorlage löschen | Aus Wiederverwendungsspeicher entfernen; notwendige Daten eines laufenden physischen Trades nicht rückwirkend zerstören. Dies ist fachlich verschieden vom Widerruf der konkreten Tradefreigabe |
| Retention | Zweck-/Fallende und zwingende Pflichten entscheiden, keine willkürliche Dauer. Detaillierte technische/rechtliche Policy separat; keine gesetzliche Frist erfunden |

Autorisierter Kontaktservice als einzige Inhaltslesegrenze empfohlen. Allgemeine Logs, History, Notifications und öffentliche Profile enthalten keine Volladresse; auch Kurzprojektionen benötigen Berechtigung. Zugriffsprotokolle enthalten Referenzen und Zugriffsgrund, nicht nochmals den Adressinhalt. Kein Adressinhalt in URL, Formularfehlermeldung, öffentlichem Templatecache oder gewöhnlichem Requestlog. Cache-/Export-/Backupbehandlung muss die getrennten Zwecke und spätere Retention Policy übernehmen; Eigentümerexport ist keine Partnerfreigabe.

Widerruf kann tatsächlich bereits gesehene oder außerhalb Sammlr gespeicherte Daten nicht zurückrufen. Darstellung darf keinen solchen Löschungseffekt behaupten. Interne Aufbewahrung, Anzeigeermächtigung und physischer Abwicklungsbedarf werden getrennt geprüft. Ein offenes Problem allein erlaubt weder Supportzugriff ohne konkreten Bedarf noch erneuten Partnerzugriff.

Spätere technische Ausgestaltung der erforderlichen physischen Ausnahme, Speicherung, Löschjobs und Auditablage ist innerhalb dieser geschlossenen Grenzen zu konkretisieren. Sie begründet keine neue Produktregel und keinen jetzigen Implementierungsauftrag. Erst vor produktiver Aktivierung sind die autorisierten Reads, Widerrufsrennen und zweckgebundene Löschung nachzuweisen.

### Spätere T8a-Abnahmefälle (nur dokumentiert)

Eigentümer/Partner/Fremder/Support ohne Fall; Draft/pending/accepted/completed/problem; eigene Freigabe pro Trade einschließlich erneuter Partnerkombination; Anzeigen vor/nach Freigabe; Änderung einer Vorlage gegenüber Änderung einer Tradeversion; Widerruf vor Read und konkurrierend zu Read; konkreter erforderlicher physischer Ausnahmefall ohne pauschale Zugriffserweiterung; Normalabschluss trotz intern erhaltener Daten; Vorlage löschen bei laufendem Versand; Accountende mit/ohne offenen Vorgang; berechtigter minimaler Supportread mit Audit und abgewiesener unberechtigter Zugriff; keine Adresse in öffentlichen Projektionen/Logs/Notifications; Zweckende führt zur Löschung/Anonymisierung nach separat festgelegter Policy. Keine Tests ausgeführt oder verändert.

## C4. T9 Route-/IA-Audit — abgeschlossen, statisch

### Umfang und Zählweise

**46 registrierte Route-Patterns / 167 Navigations-Kantenstellen.** Alias-Patterns zählen einzeln, GET/POST desselben Patterns einmal; implizite HEAD/OPTIONS nicht zusätzlich. Kantenstellen sind konkrete Link-/Form-/Redirect-/Back-/Target-Quellstellen, keine Anzahl sämtlicher dynamischer Browserpfade: 158 in App/webapp.py, sechs im Papiertransfer (drei Templateziele, drei Redirects), drei autorisierte Notification-Target-Returns. Gemeinsame Helper zählen einmal; mehrere dynamische Ziele derselben Quellstelle werden unten aufgelöst. Eine HTML-Zeile mit mehreren Aktionen bleibt eine Kantenstelle. Zähler ist damit prüfbar und kein künstlicher Unique-Graph-Zähler.

Scope: Trade/SmartTrade/Requests, Profile als Partnereinstieg, Archiv, Notificationziele, Home-/Sammlungs-/Albumeinstiege sowie vorhandener Papiertransfer. Account, Freunde, Statistik und Trophäen sind dokumentierte Ausgänge; deren eigenständige Unterflows gehören nicht zum Trade-Audit. Statischer Quellabgleich, kein Browser-/HTTP-Test und keine Sicherheitsabnahme. Quellzeilen beziehen sich auf den geprüften Worktree.

### Routeninventar und SOLL-Klassifikation

Alle Pfade sind IST, keine vorgeschlagenen neuen Routen. Ein Deep Link benötigt weiterhin die bestehenden Actor-/Teilnehmer-/Privacyprüfungen; ein Alias erteilt keine zusätzliche Berechtigung. Eingänge/Ausgänge sind in den anschließenden Flow-Gruppen und im vollständigen Kantenregister aufgeschlüsselt.

| ID | Route | Methode | Handler / Quelle | SOLL |
| --- | --- | --- | --- | --- |
| R01 | `/` | GET | `startseite` (App/webapp.py:5338) | KEEP |
| R02 | `/home` | GET | `home_compatibility_redirect` (App/webapp.py:5486) | LEGACY SAFE FALLBACK |
| R03 | `/zentrale` | GET | `collection_compatibility_redirect` (App/webapp.py:5492) | LEGACY SAFE FALLBACK |
| R04 | `/sammlr-zentrale` | GET | `collection_compatibility_redirect` (App/webapp.py:5492) | LEGACY SAFE FALLBACK |
| R05 | `/sammlung` | GET | `sammlung` (App/webapp.py:5498) | KEEP |
| R06 | `/album/<album_id>` | GET,POST | `albumseite` (App/webapp.py:6392) | KEEP |
| R07 | `/trade/<int:trade_id>` | GET | `trade_detail` (App/webapp.py:8755) | ADAPT |
| R08 | `/trades/<int:trade_id>` | GET | `trade_detail` (App/webapp.py:8755) | ADAPT |
| R09 | `/trades/<int:trade_id>/rating` | POST | `create_trade_rating` (App/webapp.py:9048) | ADAPT |
| R10 | `/album/<album_id>/trades` | GET | `album_trades` (App/webapp.py:9095) | REMOVE FROM PRIMARY FLOW |
| R11 | `/album/<album_id>/trade/<int:other_user_id>` | GET | `trade_center` (App/webapp.py:9663) | ADAPT |
| R12 | `/album/<album_id>/trades/<int:other_user_id>` | GET | `trade_center` (App/webapp.py:9663) | ADAPT |
| R13 | `/album/<album_id>/smart-trades` | GET | `album_smart_trades` (App/webapp.py:10340) | REMOVE FROM PRIMARY FLOW |
| R14 | `/album/<album_id>/smart-trades/<int:partner_user_id>/request` | POST | `create_smart_trade_request` (App/webapp.py:10476) | ADAPT |
| R15 | `/album/<album_id>/trade/<int:other_user_id>/request` | POST | `create_trade_request` (App/webapp.py:10556) | ADAPT |
| R16 | `/album/<album_id>/trades/<int:other_user_id>/request` | POST | `create_trade_request` (App/webapp.py:10556) | ADAPT |
| R17 | `/trade/<int:trade_id>/accept` | POST | `accept_trade_request` (App/webapp.py:10652) | ADAPT |
| R18 | `/trade/<int:trade_id>/ship` | POST | `confirm_trade_shipping` (App/webapp.py:10738) | ADAPT |
| R19 | `/trade/<int:trade_id>/receive` | POST | `confirm_trade_receipt` (App/webapp.py:10760) | ADAPT |
| R20 | `/trades/<int:trade_id>/problem` | GET | `trade_problem_form` (App/webapp.py:10830) | ADAPT |
| R21 | `/trade/<int:trade_id>/problem` | POST | `report_trade_problem` (App/webapp.py:10977) | ADAPT |
| R22 | `/trade/<int:trade_id>/problem/close` | POST | `close_trade_with_problem` (App/webapp.py:11053) | ADAPT |
| R23 | `/trade/<int:trade_id>/problem/resolve` | POST | `resolve_trade_problem` (App/webapp.py:11079) | ADAPT |
| R24 | `/trade/<int:trade_id>/decline` | POST | `decline_trade_request` (App/webapp.py:11130) | ADAPT |
| R25 | `/trades` | GET | `trades_overview` (App/webapp.py:11170) | ADAPT |
| R26 | `/trades/<int:trade_id>/accept` | POST | `accept_trade` (App/webapp.py:11567) | LEGACY SAFE FALLBACK |
| R27 | `/trade/<int:trade_id>/confirm` | POST | `confirm_trade_done` (App/webapp.py:11572) | LEGACY SAFE FALLBACK |
| R28 | `/trade/<int:trade_id>/fail` | POST | `fail_trade_done` (App/webapp.py:11635) | LEGACY SAFE FALLBACK |
| R29 | `/trades/<int:trade_id>/decline` | POST | `decline_trade` (App/webapp.py:11679) | LEGACY SAFE FALLBACK |
| R30 | `/trades/<int:trade_id>/confirm` | POST | `confirm_trade` (App/webapp.py:11686) | LEGACY SAFE FALLBACK |
| R31 | `/trades/<int:trade_id>/cancel` | POST | `cancel_trade` (App/webapp.py:11691) | ADAPT |
| R32 | `/notifications` | GET,POST | `notifications_page` (App/webapp.py:11703) | ADAPT |
| R33 | `/notifications/<int:notification_id>/open` | POST | `open_notification` (App/webapp.py:11820) | KEEP |
| R34 | `/notifications/<int:notification_id>/read` | POST | `mark_notification_read` (App/webapp.py:11835) | KEEP |
| R35 | `/statistik` | GET | `statistik` (App/webapp.py:11912) | ADAPT |
| R36 | `/profil` | GET | `profil` (App/webapp.py:12470) | KEEP |
| R37 | `/profil/<username>` | GET | `public_profile` (App/webapp.py:12629) | KEEP |
| R38 | `/profil/<username>/block` | POST | `mutate_user_block` (App/webapp.py:12744) | KEEP |
| R39 | `/profil/<username>/unblock` | POST | `mutate_user_block` (App/webapp.py:12744) | KEEP |
| R40 | `/profil/<username>/album/<album_id>` | GET | `public_profile_album` (App/webapp.py:12788) | ADAPT |
| R41 | `/profil/<username>/album/<album_id>/sticker/<path:code>` | GET | `public_profile_sticker` (App/webapp.py:12876) | KEEP |
| R42 | `/profil/trade-archiv` | GET | `profil_trade_archiv` (App/webapp.py:12903) | ADAPT |
| R43 | `/album/<album_id>/liste` | GET | `stickerliste` (App/sticker_list.py:381) | KEEP |
| R44 | `/album/<album_id>/stickerliste` | GET | `stickerliste` (App/sticker_list.py:386) | KEEP |
| R45 | `/album/<album_id>/liste/trade` | POST | `stickerliste_trade` (App/sticker_list.py:391) | KEEP |
| R46 | `/album/<album_id>/stickerliste/trade` | POST | `stickerliste_trade` (App/sticker_list.py:397) | KEEP |

KEEP schützt bestehende Funktion und Privacy, bedeutet keine neue V1-Fähigkeit. REMOVE FROM PRIMARY FLOW verschiebt albumzentrierte Entdeckung zugunsten des zentralen Tauschen-Kontexts; vorhandene Deep Links benötigen weiterhin sicheren Übergang. LEGACY SAFE FALLBACK bedeutet erhaltene Kompatibilität beziehungsweise geschützte alte Lifecyclefunktion, keine Wiederöffnung für V1.

### Eingänge, Zielauflösung, Forms, Redirects und Kontext

| Flow-Gruppe | Vollständiger fachlicher Navigationsabgleich |
| --- | --- |
| Home / Sammlung / Album | `/home` → `/`; beide Zentrale-Aliase → `/sammlung`. Globale Bottomnav: Sammlung, Home, Trades. Album-Bottomnav: Album, Albumtrades, Trophäen, Statistik. Header: eigenes Profil, Account, POST Notifications, Home. Sammlungskarten → konkretes Album. Homefeed löst Newsziele, eigenes Album/eigene Albumtrophäen oder fremdes Profil/Profilalbum auf. `origin=home` ist im Detail unterstützt, kein Beleg für aktuell ausgesendeten Trade-Homefeedlink |
| Album / Papiertransfer | Album-GET/POST enthält lokalen Bestands-/Transferweg mit Rückkehr zum Album samt filter/focus. Listenaliase rendern denselben Screen; Logo → Home, Back → Album, POST liste/trade. Leere Auswahl, unzureichende freie Menge und Erfolg führen jeweils zur kanonischen Liste mit message. Keine Partneranfrage, kein Versandvertrag, keine neue QR-Transaktion; diese physische Buchung geschützt erhalten |
| Globales Tradesboard | Eingang Bottomnav und bestehende Submit-/Kompatibilitätsredirects. Tabs partners (Default), agreements, requests; unbekannter Tab → partners. Partner-/Albumkarten → Profil, albumbezogener Composer oder Albumtrades. Requests/Agreements → kanonisches Detail mit origin=trades. Mehr-Links → Albumtrades mit passendem Tab. Für zentralen SOLL-Screen ADAPT |
| Albumtrades | Eingang Albumnav, Popup und Mehr-Links. incoming/outgoing werden requests; Default bei eingehender Anfrage requests, sonst partners. Self-Links für drei Tabs, Back → Album, globaler Tradeslink, SmartMatch-Link, Partnerprofil, Composer; Detail mit origin=album_trades. Popup-Altlink tab=incoming bleibt normalisiert. Kein zusätzlicher zukünftiger Hauptscreen |
| Composer / manueller Submit | Zwei GET-Aliase für identisches Paar im Album, zwei POST-Aliase. Back/Cancel → Albumtrades. Form give_codes/get_codes → singulärer Requestpfad, clientseitige Mengen-/Dialogdarstellung ohne weitere Route. Fehler → Composer oder Albumtrades mit message, Erfolg → globale Trades. Heute Single-Album/Legacy; neuer Manual Contract, freie Mehralbum-Mengen und Präferenzprüfung benötigen Adapter |
| Alter SmartMatch | Eingang Albumtrades oder Profilalbum. Schema-/Poolgrenze → Albumtrades mit message. Alternativvorschlag self mit exclude_partner_id; result_id und exclude_partner_id im Submit. Profil-Link pro Partner. Stale Result → recalculation_url mit erhaltenem exclude und message; Erfolg → kanonisches Detail mit origin=album_trades. Diese UI verwendet alten SmartMatch, nicht globalen T3b-V1-Plan; alte 48h-/Limitdarstellung nicht als neuen Vertrag übernehmen |
| Detail und Back | Beide Detailaliase → gleiche Teilnehmerprojektion. partner → öffentliches Profil; Ratingform, rollenabhängige Aktionen und Problemweg. Backhelper: home → `/`; notifications → `/notifications`; album_trades → Requestalbum mit tab; sonst `/trades?tab=…`. tab ist agreements bei accepted, sonst requests. Nur vier origin-Werte anerkannt; kein Archiv-/Profilorigin. Ungültiger/nicht sichtbarer Trade → Trades mit message |
| Open / Accept / Decline / Withdraw | Empfänger-Forms verwenden singuläres accept/decline. Eigene offene Detailansicht ist Warten; vorhandener cancel-POST ist noch keine neue Withdraw-UI. V1 wird zuerst CG-1-dispatcht (Accept T6b, Decline/Withdraw T5b), Erfolg → kanonisches Detail ohne origin. Legacy nutzt teilweise request.referrer oder Trades mit message; alter SmartMatch-Fehler → Detail. Plurale accept/decline/confirm sind Hinweisredirects, keine gleichwertigen Commandaliase; plural cancel delegiert V1 und ist Legacy-Hinweisfallback |
| Shipping / Receipt / alte Completion | Detail/helper erzeugen Ship/Receive/Problem nach Status; bei altem Fall ohne Shippingstatus Confirm/Fail. Singuläre ship/receive → Referrer oder Detail mit message. confirm/fail → Referrer/Trades beziehungsweise Trades nach Abschluss. Für V1 blockiert CG-1 physische Commands weiterhin mit 409 bis T7a; kein Route-Audit hebt diese Sperre auf |
| Problem | GET plural problem prüft Teilnehmer und Lifecycle/Versand, Fehler → Detail. Form → singulärer Problem-POST mit Positionsmengen/Problem und Verlustangabe. Close-/Resolve-POST und Problembericht → Detail mit message; Resolve verlangt confirm_physical_arrival. Back → Detail ohne origin. V1-Commands bleiben CG-1-gesperrt; alte Teil-/Problemsemantik schützen |
| Rating / Archiv | Rating POST plural mit 1–5 Sternen → kanonisches Detail ggf. message, ohne origin. Qualifizierte Problemabschlüsse weiterhin vom normalen Erfolg unterscheiden. Eigenes Profil → Archiv, Archivback → Profil. Archiv gruppiert erfolgreiche Positionen nach Album, Detail-Link ohne Archivorigin. Derselbe Mehralbumtrade kann unter mehreren Alben erscheinen; keine neue globale Erfolgszählung ableiten |
| Profile / Partnerkontext | Öffentliche Profile und Profilalben prüfen CollectorProfile-Privacy vor Projektion; eigene Navigation führt auch zu Sammlung/Statistik/Trophäen/Freunden/Account/Archiv. Community-Forms verlassen Trade-Scope zu Freundschaft; block/unblock → Profil mit message und bestehender Pending-Freigabe. Profilalbum filtert Anzeige und verlinkt fremdes Stickerdetail; dessen Back → Profilalbum. Tradepotentiallink → albumbezogener SmartMatch ohne ausgewählten Partner: für isoliertes Paaroptimum ADAPT, Profil allein ist noch kein neuer Partnerdetailscreen |
| Inbox / Deep Links | GET/POST Notifications, POST-Pagination; jede Karte POST notification/open, separater read-POST → Inbox?page, leer → Home. open_target prüft Eigentümer und typisiertes Ziel in Transaktion, markiert gelesen; fehlendes/ungültiges Ziel → Inbox mit message. Trade-Requesttarget → dessen kanonisches Detail; Trade-Lifecycletarget → legacy_trade_request_id → Detail; Web ergänzt origin=notifications. Freundschaftstarget → Freundeanker nur berechtigter pending Empfänger, unblocked. Untyped Alttext liefert keinen freien URL-Deep-Link. Fehlender Accept-/Mutual-Typ bleibt Q7-Adapteraufgabe |

Dynamische Linkhelper für Profilalbum/Stickertile und Sammlung nutzen den jeweiligen geprüften Owner, album_id und code. Navigation darf diesen Kontext später nicht als Paketbeschränkung auslegen. T9 muss bei der Umsetzung Eingabeparameter und sichere Zielauflösung erhalten; externe/referrerbasierte Rücksprünge sind im geprüften Handler nicht durch den Detail-origin-Allowlistmechanismus abgesichert und müssen vor Vereinheitlichung separat gehärtet werden. Hier keine neue Route oder Authregel implementiert.

### Technische Abweichungen und spätere Abnahme

1. Albumzentrierte Altboards/Composer/SmartMatch sind kein fertiger zentraler V1-Flow; neue manuelle Vertragsart und T3b/T4-Anbindung fehlen in diesen UIwegen.
2. Plurale accept/decline/confirm sind Hinweiswege. Nicht mechanisch auf sie umverdrahten; echte Commanddelegation und Legacyabgrenzung ausdrücklich testen.
3. Archiv → Detail verliert Archivback; Profilalbum → SmartMatch verliert konkrete Partnerauswahl. Zukünftiger Kontext muss beide Wege korrekt tragen.
4. CG-1-Commandredirects, Rating und Problem-Rückwege erhalten origin nicht durchgängig. Spätere einheitliche, serverseitig erlaubte Backziele vorsehen; request.referrer nicht ungeprüft zum neuen Vertrag machen.
5. T7a-Physical-Gates bleiben gesperrt; Empfang ohne Versandklick, Kontaktservice T8a und deduplizierte Accept-Notification sind noch zu implementieren. Fehlende Runtimefähigkeit ist kein offener Produktentscheid.
6. Spätere T9-Verifikation: direkte Links/Refresh, beide Aliase, alle Rollen/Tabs/origins, abgefangene veraltete Formulare, ungültige IDs, Rechteverlust, Notificationziel nach Statuswechsel, Archivback, ausgewählter Partner, Mehralbumkontext, kleiner Paarvorschlag sowie Legacy-Papiertransfer. Mutationen nur durch autorisierte Commands; GET-Navigation nicht zu neuen Submit-/Freigabebefehlen machen.

Keine RED-/ORANGE-Produktblocker. Die genannten technischen Aufgaben verhindern eine Behauptung produktiver Fertigstellung, aber keine Gestaltung nach geschlossenem SOLL.

### Kantenregister (167 geprüfte Quellstellen)

W = App/webapp.py, P = App/sticker_list.py, H = App/templates/sticker_list.html, N = App/services/typed_notifications.py. Dynamische Variablen sind in der Flow-Tabelle aufgelöst; Attribute im Register sind bestehender Quellcode, keine neu gebauten URLs.

| ID | Quelle | Kontext | Art / Zielausdruck |
| --- | --- | --- | --- |
| E001 | W:161 | `smartdeal_request_boundary` | Redirect: `redirect(f'/trades/{trade_id}')` |
| E002 | W:2896 | `app_header` | Form/Link: `<a class="app-header-action app-header-profile" href="/profil" aria-label="Eigenes Profil öffnen">` |
| E003 | W:2902 | `app_header` | Form/Link: `<a class="app-header-action app-header-settings" href="/account" aria-label="Account und Einstellungen öffnen">` |
| E004 | W:2913 | `app_header` | Form/Link: `<form class="app-header-notification-form" method="POST" action="/notifications">` |
| E005 | W:2925 | `app_header` | Form/Link: `<a class="app-header-brand" href="/">` |
| E006 | W:3530 | `profile_trade_archive_html` | Form/Link: `<a class="trade-detail-link" href="/trades/{trade_item['id']}">Ansehen</a>` |
| E007 | W:5423 | `startseite` | Form/Link: `f'href="{escape(target)}">{body}</a>'` |
| E008 | W:5454 | `startseite` | Form/Link: `<a href="/album/{quote(favorite_status['id'], safe='')}">Album öffnen</a>` |
| E009 | W:5473 | `startseite` | Form/Link: `<a class="home-concept-primary-action" href="/trades">Tauschpartner ansehen</a>` |
| E010 | W:5487 | `home_compatibility_redirect` | Redirect: `redirect("/")` |
| E011 | W:5493 | `collection_compatibility_redirect` | Redirect: `redirect("/sammlung")` |
| E012 | W:5554 | `sammlung` | Form/Link: `<a class="add-album-button" href="/alben/hinzufuegen"><span aria-hidden="true">+</span>Album hinzufügen</a>` |
| E013 | W:5564 | `sammlung` | Form/Link: `<a class="btn" href="/alben/hinzufuegen">Album hinzufügen</a>` |
| E014 | W:5936 | `bottom_nav` | Form/Link: `links += f'<a class="bottom-nav-link{active_class}" href="{href}"{current_attribute}>{icons[key]}{label_html}</a>'` |
| E015 | W:6079 | `album_bottom_nav` | Form/Link: `links += f'<a class="bottom-nav-link{active_class}" href="{href}">{label}</a>'` |
| E016 | W:6430 | `albumseite` | Redirect: `redirect(f"/album/{album_id}?filter={current_filter}&message=Tausch-Sticker%20nicht%20vorhanden.&focus=trade")` |
| E017 | W:6442 | `albumseite` | Redirect: `redirect(f"/album/{album_id}?filter={current_filter}&message=Du%20kannst%20nur%20Sticker%20abgeben,%20die%20du%20besitzt.&focus=trade")` |
| E018 | W:6467 | `albumseite` | Redirect: `redirect(f"/album/{album_id}?filter={current_filter}&message={quote(msg)}&focus=trade")` |
| E019 | W:6475 | `albumseite` | Redirect: `redirect(f"/album/{album_id}?filter={current_filter}&message=Sticker%20nicht%20vorhanden.&focus={aktion}")` |
| E020 | W:6509 | `albumseite` | Form/Link: `<a class="sammlr-back-link" href="/sammlung">← Zur Sammlung</a>` |
| E021 | W:6558 | `albumseite` | Form/Link: `<a class="album-quick-card" href="/album/{album_id}/liste">` |
| E022 | W:6572 | `albumseite` | Form/Link: `<a class="album-quick-card {'has-badge' if incoming_trade_request_count > 0 else ''}" href="/album/{album_id}/trades?tab={'incoming' if incoming_trade_request_count > 0 else 'partners'}">` |
| E023 | W:6581 | `albumseite` | Form/Link: `<a class="album-quick-card" href="/album/{album_id}/trophaeen">` |
| E024 | W:6604 | `albumseite` | Form/Link: `<a class="sticker-filter-pill {'active' if filter_name == 'all' else ''}" href="/album/{album_id}" data-filter="all">Alle</a>` |
| E025 | W:6605 | `albumseite` | Form/Link: `<a class="sticker-filter-pill missing {'active' if filter_name == 'missing' else ''}" href="/album/{album_id}?filter=missing" data-filter="missing">Fehlende</a>` |
| E026 | W:6606 | `albumseite` | Form/Link: `<a class="sticker-filter-pill duplicate {'active' if filter_name == 'duplicate' else ''}" href="/album/{album_id}?filter=duplicate" data-filter="duplicate">Doppelte</a>` |
| E027 | W:8237 | `trade_open_actions` | Form/Link: `<form method="POST" action="/trade/{trade['id']}/accept">` |
| E028 | W:8240 | `trade_open_actions` | Form/Link: `<form method="POST" action="/trade/{trade['id']}/decline">` |
| E029 | W:8395 | `trade_completion_actions` | Form/Link: `<a class="trade-detail-link" href="/trades/{trade['id']}?origin=trades">Versandstatus öffnen</a>` |
| E030 | W:8417 | `trade_completion_actions` | Form/Link: `<form method="POST" action="/trade/{trade['id']}/confirm">` |
| E031 | W:8420 | `trade_completion_actions` | Form/Link: `<form method="POST" action="/trade/{trade['id']}/fail">` |
| E032 | W:8575 | `trade_detail_primary_action` | Form/Link: `<form method="POST" action="/trade/{trade['id']}/problem/resolve"` |
| E033 | W:8606 | `trade_detail_primary_action` | Form/Link: `<form method="POST" action="/trade/{trade['id']}/accept">` |
| E034 | W:8609 | `trade_detail_primary_action` | Form/Link: `<form method="POST" action="/trade/{trade['id']}/decline">` |
| E035 | W:8634 | `trade_detail_primary_action` | Form/Link: `<form method="POST" action="/trade/{trade['id']}/ship">` |
| E036 | W:8652 | `trade_detail_primary_action` | Form/Link: `<form method="POST" action="/trade/{trade['id']}/problem/resolve"` |
| E037 | W:8672 | `trade_detail_primary_action` | Form/Link: `<form method="POST" action="/trade/{trade['id']}/problem/close">` |
| E038 | W:8680 | `trade_detail_primary_action` | Form/Link: `<form method="POST" action="/trade/{trade['id']}/receive">` |
| E039 | W:8687 | `trade_detail_primary_action` | Form/Link: `f'<a class="trade-detail-link" href="/trades/{trade["id"]}/problem">'` |
| E040 | W:8692 | `trade_detail_primary_action` | Form/Link: `<form method="POST" action="/trade/{trade['id']}/confirm">` |
| E041 | W:8708 | `trade_detail_back_context` | Back: `return "/", "Home"` |
| E042 | W:8710 | `trade_detail_back_context` | Back: `return "/notifications", "Benachrichtigungen"` |
| E043 | W:8712 | `trade_detail_back_context` | Back: `return f"/album/{album_id}/trades?tab={back_tab}", "Album-Tauschbörse"` |
| E044 | W:8713 | `trade_detail_back_context` | Back: `return f"/trades?tab={back_tab}", "Tauschbörse"` |
| E045 | W:8745 | `trade_rating_html` | Form/Link: `<form method="POST" action="/trades/{rating_state.legacy_trade_request_id}/rating">` |
| E046 | W:8830 | `trade_detail` | Redirect: `redirect("/trades?message=Tauschangebot%20nicht%20gefunden")` |
| E047 | W:8932 | `trade_detail` | Form/Link: `<a class="btn green" href="/album/{album_id}/smart-trades">Neu berechnen</a>` |
| E048 | W:8933 | `trade_detail` | Form/Link: `<a class="btn gray" href="{back_href}">Abbrechen</a>` |
| E049 | W:8937 | `trade_detail` | Form/Link: `<form method="POST" action="/trade/{trade_id}/decline">` |
| E050 | W:8943 | `trade_detail` | Form/Link: `smart_options_html = f'<a class="btn gray" href="{back_href}">Abbrechen</a>'` |
| E051 | W:8990 | `trade_detail` | Form/Link: `<a class="sticker-list-back" href="{back_href}">← zurück zu {escape(back_label)}</a>` |
| E052 | W:8998 | `trade_detail` | Form/Link: `<a class="trade-partner-profile-link" href="/profil/{quote(partner_name, safe='')}">{escape(partner_name)}</a>` |
| E053 | W:9001 | `trade_detail` | Form/Link: `href="/profil/{quote(partner_name, safe='')}"` |
| E054 | W:9067 | `create_trade_rating` | Redirect: `redirect( f"/trades/{trade_id}?message=" f"{quote('Dieser Trade kann noch nicht bewertet werden.')}" )` |
| E055 | W:9071 | `create_trade_rating` | Redirect: `redirect(f"/trades/{trade_id}")` |
| E056 | W:9087 | `trade_request_popup_html` | Form/Link: `<a href="/album/{album_id}/trades?tab=incoming">Ansehen</a>` |
| E057 | W:9193 | `album_trades` | Form/Link: `<a class="r2-trade-back" aria-label="Zurück zu {escape(album['name'])}" href="/album/{album_id}">← Zurück</a>` |
| E058 | W:9200 | `album_trades` | Form/Link: `<a class="trade-concept-primary-action" href="/album/{album_id}/smart-trades">SmartMatch öffnen</a>` |
| E059 | W:9201 | `album_trades` | Form/Link: `<a class="trade-concept-secondary-action" href="/trades">Alle Trades</a>` |
| E060 | W:9206 | `album_trades` | Form/Link: `<a class="{'is-active' if tab == 'partners' else ''}" href="/album/{album_id}/trades?tab=partners" {'aria-current="page"' if tab == 'partners' else ''}>` |
| E061 | W:9209 | `album_trades` | Form/Link: `<a class="{'is-active' if tab == 'agreements' else ''}" href="/album/{album_id}/trades?tab=agreements" {'aria-current="page"' if tab == 'agreements' else ''}>` |
| E062 | W:9212 | `album_trades` | Form/Link: `<a class="{'is-active' if tab == 'requests' else ''}" href="/album/{album_id}/trades?tab=requests" {'aria-current="page"' if tab == 'requests' else ''}>` |
| E063 | W:9277 | `album_trades` | Form/Link: `<a class="trade-detail-link" href="/trades/{trade['id']}?origin=album_trades">Ansehen</a>` |
| E064 | W:9325 | `album_trades` | Form/Link: `<a class="trade-detail-link" href="/trades/{trade['id']}?origin=album_trades">Ansehen</a>` |
| E065 | W:9364 | `album_trades` | Form/Link: `<a class="trade-detail-link" href="/trades/{trade['id']}?origin=album_trades">Ansehen</a>` |
| E066 | W:9400 | `album_trades` | Form/Link: `<a class="trade-person-identity" href="/profil/{username_path}"` |
| E067 | W:9412 | `album_trades` | Form/Link: `<a class="trade-concept-primary-action" href="/album/{album_id}/trade/{user['id']}">Tausch starten</a>` |
| E068 | W:9685 | `trade_center` | Redirect: `redirect(f"/album/{album_id}/trades")` |
| E069 | W:9709 | `trade_center` | Form/Link: `<a class="r2-trade-back" href="/album/{album_id}/trades">← zurück zu Tauschpartner</a>` |
| E070 | W:9765 | `trade_center` | Form/Link: `<form method="POST" action="/album/{album_id}/trade/{other_user_id}/request" id="tradeRequestForm">` |
| E071 | W:9791 | `trade_center` | Form/Link: `<a class="smart-add-secondary trade-cancel-link" href="/album/{album_id}/trades">Abbrechen</a>` |
| E072 | W:10349 | `album_smart_trades` | Redirect: `redirect( f"/album/{album_id}/trades?message=" f"{quote('Smart Trades sind für dieses Album nicht verfügbar.')}" )` |
| E073 | W:10396 | `album_smart_trades` | Form/Link: `<a class="trade-person-identity" href="/profil/{quote(partner_name, safe='')}"` |
| E074 | W:10413 | `album_smart_trades` | Form/Link: `<form method="POST" action="/album/{album_id}/smart-trades/{package.partner_user_id}/request">` |
| E075 | W:10418 | `album_smart_trades` | Form/Link: `<a class="trade-concept-secondary-action" href="/album/{album_id}/smart-trades?exclude_partner_id={package.partner_user_id}">` |
| E076 | W:10448 | `album_smart_trades` | Form/Link: `<a class="r2-trade-back" href="/album/{album_id}/trades">← zurück zu Tauschpartner</a>` |
| E077 | W:10480 | `create_smart_trade_request` | Redirect: `redirect( f"/album/{album_id}/trades?message=" f"{quote('Smart Trades benötigen die bestehende Reservierungsbasis.')}" )` |
| E078 | W:10505 | `create_smart_trade_request` | Redirect: `redirect( f"{recalculate_url}{separator}message=" f"{quote('Der Vorschlag hat sich geändert. Bitte neu berechnen.')}" )` |
| E079 | W:10532 | `create_smart_trade_request` | Redirect: `redirect(f"/trades/{trade_id}?origin=album_trades")` |
| E080 | W:10549 | `create_smart_trade_request` | Redirect: `redirect(f"{recalculate_url}{separator}message={quote(message)}")` |
| E081 | W:10572 | `create_trade_request` | Redirect: `redirect( f"/album/{album_id}/trades?message=" f"{quote('Mit diesem Nutzer ist derzeit keine Interaktion möglich.')}" )` |
| E082 | W:10586 | `create_trade_request` | Redirect: `redirect(f"{trade_url}?message={quote('Bitte wähle auf beiden Seiten mindestens einen Sticker aus.')}")` |
| E083 | W:10590 | `create_trade_request` | Redirect: `redirect(f"{trade_url}?message={quote('Du musst mindestens so viele Sticker anbieten, wie du suchst.')}")` |
| E084 | W:10595 | `create_trade_request` | Redirect: `redirect(f"/album/{album_id}/trades")` |
| E085 | W:10615 | `create_trade_request` | Redirect: `redirect(f"{trade_url}?message={quote('Ein ausgewählter Sticker ist nicht mehr verfügbar.')}")` |
| E086 | W:10620 | `create_trade_request` | Redirect: `redirect(f"{trade_url}?message={quote('Ein ausgewählter Sticker ist nicht mehr verfügbar.')}")` |
| E087 | W:10648 | `create_trade_request` | Redirect: `redirect(f"/trades?message=Tauschanfrage%20gesendet")` |
| E088 | W:10681 | `accept_trade_request` | Redirect: `redirect(f"/trades/{trade_id}?message={quote(message)}")` |
| E089 | W:10719 | `accept_trade_request` | Redirect: `redirect(request.referrer or fallback)` |
| E090 | W:10734 | `accept_trade_request` | Redirect: `redirect(request.referrer or "/trades?message=Tauschanfrage%20angenommen")` |
| E091 | W:10756 | `confirm_trade_shipping` | Redirect: `redirect(request.referrer or fallback)` |
| E092 | W:10826 | `confirm_trade_receipt` | Redirect: `redirect(request.referrer or fallback)` |
| E093 | W:10846 | `trade_problem_form` | Redirect: `redirect(f"/trades/{trade_id}?message=Problemweg%20nicht%20verfügbar")` |
| E094 | W:10885 | `trade_problem_form` | Redirect: `redirect(f"/trades/{trade_id}?message=Problemweg%20nicht%20verfügbar")` |
| E095 | W:10916 | `trade_problem_form` | Form/Link: `<form method="POST" action="/trade/{trade_id}/problem">` |
| E096 | W:10924 | `trade_problem_form` | Form/Link: `<a class="trade-detail-link" href="/trades/{trade_id}">Abbrechen und zurück zum Deal</a>` |
| E097 | W:11047 | `report_trade_problem` | Redirect: `redirect( f"/trades/{trade_id}?message={quote(messages[result.code])}" )` |
| E098 | W:11072 | `close_trade_with_problem` | Redirect: `redirect( f"/trades/{trade_id}?message=" f"{quote(messages.get(result.code, 'Problemtrade nicht beendbar'))}" )` |
| E099 | W:11081 | `resolve_trade_problem` | Redirect: `redirect( f"/trades/{trade_id}?message=" f"{quote('Bitte die physische Nachlieferung ausdrücklich bestätigen')}" )` |
| E100 | W:11124 | `resolve_trade_problem` | Redirect: `redirect( f"/trades/{trade_id}?message={quote(messages[result.code])}" )` |
| E101 | W:11148 | `decline_trade_request` | Redirect: `redirect( f"/trades/{trade_id}?message={quote('Smart-Anfrage abgelaufen')}" )` |
| E102 | W:11165 | `decline_trade_request` | Redirect: `redirect(request.referrer or "/trades?message=Tauschanfrage%20abgelehnt")` |
| E103 | W:11331 | `trades_overview` | Form/Link: `<a class="{'is-active' if tab == 'partners' else ''}" href="/trades?tab=partners"` |
| E104 | W:11333 | `trades_overview` | Form/Link: `<a class="{'is-active' if tab == 'agreements' else ''}" href="/trades?tab=agreements"` |
| E105 | W:11337 | `trades_overview` | Form/Link: `<a class="{'is-active' if tab == 'requests' else ''}" href="/trades?tab=requests"` |
| E106 | W:11378 | `trades_overview` | Form/Link: `<a class="trade-person-identity" href="/profil/{username_path}"` |
| E107 | W:11388 | `trades_overview` | Form/Link: `href="/album/{quote(album['id'], safe='')}/trade/{sammler_item['id']}">Tausch starten</a>` |
| E108 | W:11395 | `trades_overview` | Form/Link: `<a class="trade-current-more" href="/album/{quote(album['id'], safe='')}/trades">Mehr anzeigen</a>` |
| E109 | W:11499 | `trades_overview` | Form/Link: `<a class="trade-person-identity" href="/profil/{partner_path}"` |
| E110 | W:11511 | `trades_overview` | Form/Link: `<a class="trade-concept-secondary-action" href="/trades/{trade['id']}?origin=trades">Versandstatus ansehen</a>` |
| E111 | W:11538 | `trades_overview` | Form/Link: `<a class="trade-concept-primary-action" href="/trades/{trade['id']}?origin=trades">Ansehen</a>` |
| E112 | W:11547 | `trades_overview` | Form/Link: `<a class="trade-current-more" href="/album/{quote(album['id'], safe='')}/trades?tab={detail_tab}">Mehr anzeigen</a>` |
| E113 | W:11568 | `accept_trade` | Redirect: `redirect("/trades?message=Bitte%20die%20Tauschanfrage%20%C3%BCber%20den%20Button%20annehmen.")` |
| E114 | W:11587 | `confirm_trade_done` | Redirect: `redirect(request.referrer or "/trades?message=Tauschanfrage%20nicht%20gefunden")` |
| E115 | W:11591 | `confirm_trade_done` | Redirect: `redirect( request.referrer or "/trades?message=Der%20neue%20Versandflow%20wartet%20auf%20Empfang" )` |
| E116 | W:11627 | `confirm_trade_done` | Redirect: `redirect("/trades?message=Tausch%20abgeschlossen")` |
| E117 | W:11631 | `confirm_trade_done` | Redirect: `redirect(request.referrer or "/trades?message=Tausch%20vormarkiert")` |
| E118 | W:11650 | `fail_trade_done` | Redirect: `redirect(request.referrer or "/trades?message=Tauschanfrage%20nicht%20gefunden")` |
| E119 | W:11655 | `fail_trade_done` | Redirect: `redirect( request.referrer or "/trades?message=Versendeter%20Trade%20kann%20nicht%20pauschal%20beendet%20werden" )` |
| E120 | W:11674 | `fail_trade_done` | Redirect: `redirect("/trades?message=Tausch%20geplatzt")` |
| E121 | W:11680 | `decline_trade` | Redirect: `redirect("/trades?message=Bitte%20die%20Tauschanfrage%20%C3%BCber%20den%20Button%20ablehnen.")` |
| E122 | W:11687 | `confirm_trade` | Redirect: `redirect("/trades?message=Bitte%20den%20Tausch%20%C3%BCber%20den%20Button%20best%C3%A4tigen.")` |
| E123 | W:11697 | `cancel_trade` | Redirect: `redirect("/trades?message=Bitte%20den%20Tausch%20%C3%BCber%20den%20Button%20als%20geplatzt%20markieren.")` |
| E124 | W:11724 | `notifications_page` | Form/Link: `<form id="notification-inbox-open" method="POST" action="/notifications?{open_query}">` |
| E125 | W:11749 | `notifications_page` | Form/Link: `f'<form method="POST" action="/notifications/{notification.id}/open">'` |
| E126 | W:11784 | `notifications_page` | Form/Link: `<a class="notification-open" href="/">Zur Startseite</a>` |
| E127 | W:11791 | `notifications_page` | Form/Link: `f'<form method="POST" action="/notifications?page={history.page - 1}">'` |
| E128 | W:11799 | `notifications_page` | Form/Link: `f'<form method="POST" action="/notifications?page={history.page + 1}">'` |
| E129 | W:11828 | `open_notification` | Redirect: `redirect(f"{result.target_path}{separator}origin=notifications")` |
| E130 | W:11829 | `open_notification` | Redirect: `redirect( "/notifications?message=" + quote("Ziel nicht mehr verfügbar") )` |
| E131 | W:11845 | `mark_notification_read` | Redirect: `redirect(f"/notifications?page={page}")` |
| E132 | W:12002 | `collector_profile_album_section` | Form/Link: `f'<a class="collector-profile-album" href="{target}">'` |
| E133 | W:12020 | `collector_profile_owner_navigation` | Form/Link: `<a class="profile-link-card" href="/sammlung">` |
| E134 | W:12024 | `collector_profile_owner_navigation` | Form/Link: `<a class="profile-link-card" href="/statistik">` |
| E135 | W:12028 | `collector_profile_owner_navigation` | Form/Link: `<a class="profile-link-card" href="/trophaeen">` |
| E136 | W:12032 | `collector_profile_owner_navigation` | Form/Link: `<a class="profile-link-card" href="/profil/trade-archiv">` |
| E137 | W:12036 | `collector_profile_owner_navigation` | Form/Link: `<a class="profile-link-card" href="/profil/freunde">` |
| E138 | W:12040 | `collector_profile_owner_navigation` | Form/Link: `<a class="profile-link-card" href="/account">` |
| E139 | W:12166 | `collector_profile_community_html` | Form/Link: `f'<form method="POST" action="/profil/{username}/unblock">'` |
| E140 | W:12178 | `collector_profile_community_html` | Form/Link: `f'<form method="POST" action="/profil/freunde/{profile.user_id}/remove">'` |
| E141 | W:12185 | `collector_profile_community_html` | Form/Link: `f'<form method="POST" action="/profil/freunde/anfragen/{request_id}/accept">'` |
| E142 | W:12187 | `collector_profile_community_html` | Form/Link: `f'<form method="POST" action="/profil/freunde/anfragen/{request_id}/decline">'` |
| E143 | W:12194 | `collector_profile_community_html` | Form/Link: `f'<form method="POST" action="/profil/freunde/anfragen/{profile.user_id}">'` |
| E144 | W:12203 | `collector_profile_community_html` | Form/Link: `<form method="POST" action="/profil/{username}/block">` |
| E145 | W:12226 | `collector_profile_completion_section` | Form/Link: `f'<a class="collector-profile-album" href="{target}">'` |
| E146 | W:12307 | `render_collector_profile` | Form/Link: `'href="/profil/sticker/bearbeiten">Sticker bearbeiten</a>'` |
| E147 | W:12318 | `render_collector_profile` | Form/Link: `'href="/profil/sticker/bearbeiten" aria-label="Sticker erstellen">'` |
| E148 | W:12323 | `render_collector_profile` | Form/Link: `'href="/profil/sticker/bearbeiten">Sticker erstellen</a>'` |
| E149 | W:12374 | `render_collector_profile` | Form/Link: `<a class="collector-showcase-album" href="{target}"` |
| E150 | W:12406 | `render_collector_profile` | Form/Link: `<a class="collector-showcase-album is-complete" href="{target}">` |
| E151 | W:12757 | `mutate_user_block` | Redirect: `redirect(f"/profil/{quote(username, safe='')}?message={quote(_community_redirect_message(result))}")` |
| E152 | W:12805 | `public_profile_album` | Form/Link: `f'<a class="trade-partner-button" href="/album/{quote(album_id, safe="")}/smart-trades">'` |
| E153 | W:12836 | `public_profile_album` | Form/Link: `<a class="sammlr-back-link" href="/profil/{quote(owner['username'], safe='')}">← Zum Profil</a>` |
| E154 | W:12852 | `public_profile_album` | Form/Link: `<a class="sticker-filter-pill{' active' if filter_name == 'all' else ''}" href="{base_path}" data-filter="all">Alle</a>` |
| E155 | W:12853 | `public_profile_album` | Form/Link: `<a class="sticker-filter-pill missing{' active' if filter_name == 'missing' else ''}" href="{base_path}?filter=missing" data-filter="missing">Fehlende</a>` |
| E156 | W:12854 | `public_profile_album` | Form/Link: `<a class="sticker-filter-pill duplicate{' active' if filter_name == 'duplicate' else ''}" href="{base_path}?filter=duplicate" data-filter="duplicate">Doppelte</a>` |
| E157 | W:12889 | `public_profile_sticker` | Form/Link: `<a class="sammlr-back-link" href="/profil/{quote(owner['username'], safe='')}/album/{quote(album_id, safe='')}">← Zur Stickerwand</a>` |
| E158 | W:12908 | `profil_trade_archiv` | Form/Link: `<a class="sammlr-back-link trade-back-link" href="/profil">← Zurück</a>` |
| E159 | P:310 | `stickerliste_trade` | Redirect: `list_url + message → /album/{album_id}/liste` |
| E160 | P:331 | `stickerliste_trade` | Redirect: `list_url + message → /album/{album_id}/liste` |
| E161 | P:379 | `stickerliste_trade` | Redirect: `list_url + message → /album/{album_id}/liste` |
| E162 | H:6 | `stickerliste` | Link/Form: `/` |
| E163 | H:7 | `stickerliste` | Link/Form: `/album/{{ album_id }}` |
| E164 | H:31 | `stickerliste` | Link/Form: `POST /album/{{ album_id }}/liste/trade` |
| E165 | N:191 | `target_path_for` | Target: `trade_request → /trades/{id}` |
| E166 | N:203 | `target_path_for` | Target: `trade → /trades/{legacy_trade_request_id}` |
| E167 | N:221 | `target_path_for` | Target: `friendship → /profil/freunde#friend-request-{id}` |

## C5. Design-Bereitschaft nach abgeschlossenem Phase-C-Audit

GREEN bezeichnet Gestaltung ohne weitere fundamentale Domainentscheidung, nicht implementierte oder getestete UI.

| Bereich | Status | Begründung |
| --- | --- | --- |
| Tauschen Home | GREEN | Reihenfolge und Zustandsbereiche entschieden; T9 benennt die notwendigen Übergänge vom Album-IST zum zentralen SOLL |
| SmartDeal collapsed/expanded | GREEN | Exaktes Paket, Anfrage, Bindung und gegenseitige Annahme geschlossen. Alte SmartMatch-Seiten sind keine V1-Implementierungsfreigabe |
| Gemeinsamer Anfragebereich | GREEN | Rollen, Richtungen, 24h und Freigaben geschlossen; neuer manueller Vertrag getrennt spezifiziert |
| Laufender Trade | GREEN | Q2 und NP-C3-1 schließen physische Evidenz sowie Kontaktzugriff/Widerruf/Problem/Accountende. Technische Umsetzung und separate konkrete Retention Policy bleiben erforderlich |
| Partnerliste | GREEN | Q8 entscheidet Sortierung und Albumfilter; bestehende Privacygrenzen bleiben erhalten |
| Partnerdetail | GREEN | Isoliertes Paaroptimum und manueller Composer sind definiert. T9 dokumentiert den heute verlorenen Partnerkontext und die nötige Anpassung |

## Abschlussstatus

Phase A/B aus dem vorherigen Lauf abgeschlossen; Phase C jetzt vollständig dokumentiert. Q1–Q8 und NP-C3-1 geschlossen. **0 echte offene Produktfragen, 0 RED / 0 ORANGE Produktblocker.** T7a-Tech-Prep GREEN als konkreter Vorschlag, T8a-Tech-Prep GREEN, T9 46 Routen / 167 Kantenstellen statisch auditiert. Alle sechs Designbereiche GREEN.

Manual Offer Contract vorhanden: eigener neuer Contract-Type empfohlen, Persistenz voraussichtlich erforderlich, Migration MÖGLICH; kein Schema beschlossen. Gesperrte Baseline 1251/1251 ist historischer Nachweis, kein neu ausgeführter Testlauf.

Fortsetzung ändert ausschließlich diesen Prep-Bericht und den PO-Decision-Record. Runtime/UI/Routes/DB/Migrationen/Tests unverändert; keine Implementierung T7a/T7b/T8a/T9. Kein git add, Commit, Push oder Deploy. Nach Dokumentationsvalidierung STOP.
