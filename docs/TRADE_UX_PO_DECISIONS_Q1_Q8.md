# Trade UX — PO Decisions Q1–Q8

Stand: 2026-09-12. Verbindlicher Decision Record zum Night Prep Package. Schließt die acht im [Trade UX SOLL](TRADE_UX_SOLL_V1.md) historisch ausgewiesenen Fragen. Keine Implementierung, keine rückwirkende Änderung bestehender Vorgänge. Die bestehende Core-/CG-1-Baseline 1251/1251 bleibt ein vorheriger Testnachweis.

| Entscheidung | Verbindlicher Vertrag | Wirkung auf bisherige Konflikte |
| --- | --- | --- |
| Q1 | Keine Reparatur. Vor erstem physischen Versand: unfulfillable, ganz beenden, vollständig freigeben, Gegenseite informieren, Paket unverändert erhalten, vollständig neu berechnen. Nach physischem Versand: Problem-/Action-required-Weg. Gleichwertiges Gegenstück entfernen ausdrücklich verworfen | C1 geschlossen zugunsten bestehender Bible §37.4 und AC25/26 |
| Q2 | Empfang trotz fehlendem Versandklick zulässig. Keine erfundene historische Versandzeit; Empfangszeit korrekt persistieren; notwendige physische Buchungen genau einmal; Teil-/Fehlempfang nach bestehendem Problemvertrag; Retry sicher | C2 produktseitig geschlossen; T7a-Adapter noch zu bauen, bestehender NOT_SHIPPED-Guard nicht still entfernen |
| Q3 | Globale Nutzerpräferenz OPEN / SAME_ALBUM_ONLY, Default OPEN. Gilt als Empfängerregel nur für neu erzeugte manuelle Angebote. Kein Einfluss auf SmartDeal-Algorithmus, bestehende Requests/angenommene Verträge oder Legacy; Wechsel nur für neue Angebote. Kein Ersatz für trade_pool_enabled | C4 geschlossen; eigene Präferenzpersistenz später |
| Q4 | Draft ungebunden. Submit friert Paket ein, prüft frisch und bindet beide Supplies plus zugehörige Incoming Needs atomar, ohne physische Buchung. Absolute 24h ab Bindung. Decline/Withdraw/Expiry vollständig frei; nach Accept Bindung erhalten. Kein hier erfundenes manuelles Limit | C5 geschlossen; neuer manueller Domainvertrag erforderlich |
| Q5 | Partnerdetail zeigt isoliertes 1:1-Paaroptimum aus kanonischer freier Supply, Needs, Eligibility und Reservations, kein globaler T3b-Plan. Auch kleiner als 5↔5 anzeigen; Mindestschwelle gehört zur globalen Topansicht. Präferenzen nur in ihrem jeweiligen Geltungsbereich berücksichtigen | C6 geschlossen für Berechnung/Anzeige; keine automatische Umgehung bestehender T4-Submitguards |
| Q6 | Bestehende Ratingqualifikation einschließlich berechtigtem Problemabschluss erhalten. Problemabschluss sichtbar von normalem Erfolg trennen. Rating verändert den SmartDeal-Optimizer nicht | C7 geschlossen |
| Q7 | Eigenständige relevante Nachrichten: neue Anfrage, „Tausch steht.“ für Accept/Übereinstimmung, Partner versendet, Problem erfordert Handlung. Kein eigener Notification-Zwang für Empfang, eigene unbeantwortete Expiry, Neuberechnung oder abgegebene Bewertung. Keine doppelte Mutual-Meldung | C8 produktseitig geschlossen; fehlender technischer Accept-Typ/Anbindung später, Katalog jetzt unverändert |
| Q8 | Partner nach tatsächlich möglichem 1:1-Paarvolumen DESC: Minimum beider durch freie Supply und Empfängerneed begrenzter Richtungszahlen. Albumfilter bestimmt Personen mit Chance im Album; danach weiterhin gesamtes zulässiges Paarvolumen als Sortiergröße. Beide Richtungszahlen dürfen angezeigt werden | Frühere Sortierfrage geschlossen; kein Albumfilter als stille Paketgrenze |

Die bereits entschiedene neue manuelle Mengenregel bleibt `give_count >= receive_count`, mindestens ein Piece in beiden Richtungen. Sie präzisiert den breiten älteren manuellen Bibletext nur für neue manuelle Angebote; C3 wird durch den eigenen [Manual Offer Contract](MANUAL_OFFER_DOMAIN_CONTRACT_V1.md) abgegrenzt.

Q5 autorisiert Anzeige kleiner Chancen, nicht ungefragt eine neue SmartDeal-Requestart unterhalb des aktuellen T4-Minimums. Ein kleines Paket kann als Grundlage des gesonderten manuellen Composers dienen; keine automatische Umklassifikation oder abgesendete Anfrage durch bloßes Anzeigen. Q3 betrifft ausdrücklich manuelle Angebote; sie schränkt den automatischen globalen SmartDeal nicht ein.

Aktueller Typed-Katalog: `trade_request_created`, `smart_trade_request_created`, `trade_request_declined`, `trade_shipped`, `trade_rating_available`, `friend_request`, `trade_request_unfulfillable`, `trade_problem_action_required`, `trade_problem_terminal`. Ein deduplizierter fachlicher Accept-/Übereinstimmungstyp fehlt; `smart_request_accepted` ist bereits ein Domain-Event, keine fertige Typed-Notification. Die Entscheidung entfernt keine bestehenden geschützten Notificationtypen.

Status: **Q1–Q8 geschlossen; 0 verbleibende Fragen aus diesem ursprünglichen Achterblock.** Spätere neue Fragen etwa zu Kontaktretention sind davon getrennt. Kein Algorithmus-, Runtime-, Schema-, Test- oder Katalogpatch.


## NP-C3-1 — Versandkontakt, PO-Entscheidung 2026-09-13

**CLOSED.** Hebt den bisherigen Phase-C-STOP bei T8a auf. Ergänzt Q1–Q8, ohne deren Verträge oder die gesperrte Core-Baseline zu verändern.

1. Vollständige freigegebene Versandadresse nur für den berechtigten Partner des konkreten Versandtrades. Nach normalem Abschluss endet notwendiger Partnerzugriff; vergangene Trades begründen keine dauerhafte Sichtbarkeit.
2. Widerruf beendet zukünftige Anzeige/Freigabe unmittelbar, soweit dadurch kein bereits notwendiger physischer Abwicklungsweg unmöglich wird. Bereits gesehene oder außerhalb Sammlr gespeicherte Informationen lassen sich technisch nicht zurückrufen; keinen solchen Löschungseffekt behaupten.
3. Bei offenem Tradeproblem dürfen nur die für diesen Trade zur Klärung oder physischen Abwicklung notwendigen Versanddaten intern zweckgebunden erhalten bleiben. Kein neues oder erweitertes Zugriffsrecht des Partners.
4. Kein allgemeiner Supportzugriff. Nur bei konkretem berechtigtem Problem-/Supportfall, soweit erforderlich, serverseitig autorisiert und nachvollziehbar/protokolliert. Keine öffentliche oder allgemeine interne Adressprojektion.
5. Accountende darf laufenden physischen Versandtrade/offenen Problemfall nicht inkonsistent machen. Notwendige Daten zweckgebunden bis zur beendeten Abwicklung/Problembehandlung erhalten; danach löschen oder anonymisieren, soweit keine zwingende anderweitige Aufbewahrungspflicht besteht. Keine gesetzliche Frist erfunden.
6. Optionale gespeicherte Adresse und konkrete Tradefreigabe sind getrennt. Löschen/Widerrufen der Vorlage entfernt sie aus dem Wiederverwendungsspeicher, zerstört aber keine notwendigen Daten eines laufenden physischen Trades. Gespeicherte Adresse erlaubt niemals automatisch neuen Partnerzugriff; jeder neue Trade benötigt eigene konkrete Freigabe.
7. Keine willkürliche feste Retentiondauer. Daten nur so lange erhalten, wie konkreter Versandzweck, notwendige Problembehandlung oder zwingende Pflichten es erfordern. Konkrete technische/rechtliche Retention Policy separat festlegen.

[T8a-Tech-Prep und vollständiger T9-Audit](TRADE_NEXT_BLOCKS_TECH_PREP.md) führen diese Grenzen weiter. Verbleibende echte Produktfragen nach Fortsetzung: **0**. Keine Runtime- oder Designimplementierung.
