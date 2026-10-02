# Trade-v2 — End-to-End-Audit

Stand: 2026-10-02 nach TRADE-10, einschließlich TRADE-08/09 und bestätigter Q2-Klärung. Lokale Preview, keine produktive Domainengine.

Preview: http://127.0.0.1:8095/trade-v2/

## Gemeinsame Grundlagen

Ein lokaler Request pro Demo-Deal, gemeinsamer eingefrorener Snapshot, zwei Rollen. Anfragezustand, operative Slots, Packen, Versandbestätigung, Empfang, Completion und Bewertung bleiben getrennt. Herkunft TOP_SUGGESTION / SMARTDEAL / MANUAL verändert den angenommenen Lifecycle nicht; manuelle Erstellung besitzt ihren separaten Vertrag und seit TRADE-09 einen Builder mit beidseitigen Albumfreigaben.

Kontingente: drei operative ausgehende Plätze des Initiators, drei operative eingehende Plätze des Empfängers. Eigene Versandbestätigung gibt ausschließlich den eigenen Platz frei. Q2-Empfang, Problemlösung, Completion und Rating verändern diese Projektion nicht. Freier Slot ist keine freie Sticker-Supply.

## Lifecycle-Matrix

| Schritt / State | Zulässige Transition | Operative Slots | Aktive Version | Schutzregel |
| --- | --- | --- | --- | --- |
| Discovery: Top-Vorschläge / Partnerpool | Konkreten Deal oder Partner öffnen; Pool sortieren/filtern | Kein neuer Slot | Ungebundene Fixture | Kanonische Stacks, keine Reservierung, kein Optimizeraufruf |
| Deal: ungebunden | Tauschanfrage senden | Frische lokale Prüfung, maximal drei ausgehend | Snapshot wird V1 | Genaue Identität, keine stillen Paketänderungen |
| Request: pending | Empfänger nimmt an/lehnt ab; absolute Expiry | Beide Verpflichtungen belegt | V1 eingefroren | 24 Stunden ab Bindung, Retry verlängert nicht |
| Declined / expired | Status ansehen | Betroffene Slots frei | Historischer Snapshot | Keine Annahme nach terminaler Entscheidung, kein Receipt/Rating |
| Accepted | Eigene Packliste öffnen | Weiter belegt | V1 oder aktive V2 | Gleicher Request, exakt gespiegelte Rollen |
| Packing | Gesamtpaket ausdrücklich bereit bestätigen; fehlende Positionen separat wählen | Weiter belegt | Aktiver Snapshot | Keine Buchung, kein Eingriff in Gegenrichtung |
| Missing review | Zurück oder genaue Fehlmenge bestätigen | Weiter belegt | Unverändert | Nur ausdrücklich ausgewählte eigene Fehlpositionen, keine automatische Reparatur |
| Missing reported / Amendment pending | Exakten Vorschlag ansehen; Gegenrolle akzeptiert oder beendet | Weiter belegt bis Beendigung | V1 bis Zustimmung | Deterministische Gegenpositionen, keine Neuberechnung |
| Amendment accepted | Mit erhaltenen Packmarkierungen fortsetzen | Weiter belegt | V2, V1-Historie bleibt | Ein bestätigter gemeinsamer Snapshot, frische Versionsfreigabe erforderlich |
| Amendment cancelled | Beendeten Vorgang ansehen | Betroffene Slots frei | Historische V1 | Kein aktiver Resttrade, keine Empfangs-/Bewertungsjourney |
| Packing complete | Bewusste eigene Packfreigabe | Weiter belegt | Aktive Version | Alle eigenen Exemplare nötig; automatisch volle V2 allein genügt nicht |
| Adresse / Ready to ship | Brief auswählen, optional Demo-Portal, eigene Sendung bestätigen | Weiter belegt | Unverändert | Eigene vollständige freigegebene Packliste plus simulierte Eigentümerfreigabe |
| Eigener SHIPPED | Versandstatus / Empfang öffnen | Nur eigener Platz frei | Unverändert | Bewusste richtungsbezogene Bestätigung, idempotent, kein zweiter Zeitstempel |
| BOTH_SHIPPED | Empfang jeder Richtung separat | Beide bereits frei | Unverändert | Unterwegs ist weder empfangen noch abgeschlossen |
| Receipt WAITING | Tatsächlich erhaltene Sendung bestätigen | Unverändert | Aktiver Snapshot | Q2: kein Partner-SHIPPED vorausgesetzt; keine erfundene Versandbestätigung |
| RECEIVED_UNCHECKED | Alles da oder Problem melden | Unverändert | Unverändert | Empfang allein schließt den Tausch nicht ab |
| RECEIVED_OK | Gegenrichtung abwarten | Unverändert | Unverändert | Nur eigene Empfangsrichtung final, kein Rückweg |
| PROBLEM_REPORTED | Gegenrolle bestätigt Klärungsvorschlag | Unverändert | Unverändert | Problemarten und betroffene erwartete Positionen; beide sehen denselben Fall |
| RESOLUTION_PENDING | Ursprünglicher Melder bestätigt Lösung | Unverändert | Unverändert | Partner kann nicht allein endgültig lösen/löschen |
| RESOLVED | Gegenrichtung abwarten oder Completion | Unverändert | Unverändert | Lösung dokumentiert, kein Ersatzpaket und kein Amendment |
| COMPLETED | Optional bewerten, Historie ansehen | Keine zweite Freigabe | Historischer aktiver Snapshot | Beide Richtungen OK/RESOLVED; irreversibel, Problemabschluss erkennbar |
| Rating NONE | 1, 2 oder 3 Sterne wählen und speichern; Später | Unverändert | Unverändert | Optional, Gegenrolle, keine automatische Wertung |
| Rating gespeichert | Ergebnis ansehen | Unverändert | Unverändert | Einmalig je Rolle; Partnerbewertung unabhängig; kein Editieren |
| Erledigt / Historie | Denselben finalen Trade wieder öffnen | Unverändert | Historisch unverändert | Kein aktives Top-Angebot für diesen abgeschlossenen Request; keine Löschung |

Withdraw und produktive Benachrichtigungen werden hier nicht neu implementiert. Bestehende Vertragsregeln bleiben erhalten; dieser Audit beansprucht ausschließlich den aktuellen Preview-Umfang.

## Q2 ist kein Versand-Shortcut

Beispiel: Fatima ist im System READY_TO_SHIP, Valentin hat die Sendung tatsächlich erhalten und meldet RECEIVED_OK. Fatimas Versandflag bleibt false, `shippedAt` bleibt null, ihr eingehender operativer Platz bleibt belegt. Valentin kann alternativ ein Problem melden und gemeinsam lösen. Keine Versand- oder Slotmutation durch diese Schritte.

Sind beide Empfangsrichtungen final, kann der Trade COMPLETED sein, auch wenn Versandklicks fehlen. Die finale Ansicht benennt die noch ausstehende eigene Versandbestätigung und hält deren bestehenden Weg erreichbar. Erst der eigene spätere Versandklick gibt den jeweiligen Slot frei. Completion und Rating bleiben dabei bestehen.

Sobald eine tatsächliche physische Abwicklung durch Versandbestätigung **oder tatsächlichen Empfang** dokumentiert ist, darf ein Amendment das vereinbarte Paket nicht mehr umschreiben. Ein bereits offener Amendmentkonflikt wird nicht heimlich repariert oder gelöscht. Q2 ersetzt keinen Supply-/Reservation-Adapter und erzeugt keine produktive Buchung.

## End-to-End-Nachweise

1. Vier vollständige frische UI-Journeys bei 375/390/430/1280: Discovery → Deal → Send → Accept → beide Packprüfungen → beide Versandbestätigungen → beide Empfänge OK → COMPLETED → drei Sterne → Erledigt → Historie öffnen. Keine State-Injektion innerhalb des vollständigen Browserpfads.
2. Vier Problem-Journeys ab explizitem BOTH_SHIPPED-Demostand: Empfang → zwei konkrete fehlende Positionen → Partner sieht identischen Fall → Lösung vorschlagen → Melder bestätigt → Gegenempfang OK → Completion, Bewertung verfügbar. Physische Daten unverändert.
3. Q2-Journeys auf allen vier Breiten: fehlender Partner-Versandklick, trotzdem Empfang/Problem/Resolution; READY_TO_SHIP + RECEIVED_OK; Completion bei fehlenden Versandklicks, spätere eigene Bestätigung gibt ausschließlich eigenen Slot frei.
4. TRADE-01–06-Regressionen inklusive 21 produktiver Stack-Paritätsfälle, Slot-/Frist-/Snapshot-/Marker-/Adress-/Versandprüfungen bestanden. 37 Unittests und 1.511 explizit gezählte Modellassertionen einschließlich TRADE-05/06 bestanden.

[TRADE-07-Prüfergebnis](../tests/research/artifacts/trade-07/checks.json) · [Galerie](../tests/research/artifacts/trade-07/index.html) · [Scope/Hashes](../tests/research/artifacts/trade-07/scope-checks.json) · [TRADE-07-Audit](TRADE_07_AUDIT.md).

## Grenzen der Aussage

Der gemeinsame Lifecycle ist in einem lokalen Demo-Tab durchspielbar. Rollenwechsel simuliert zwei Teilnehmer. Keine produktive DB, Mehrbenutzer-Concurrency, Bestands-/Reservationsbuchung, echte Privatadresse, Carrier-, Zahlungs-, Moderations- oder Notification-Anbindung. Keine Migration von Legacy-Vorgängen. Der implementierte Manual-Builder verwendet synthetische Eligibility-/Supply-/Need-Fixtures, keine autorisierten produktiven Daten. Die anschließende manuelle Produkt-/UX-Begehung bleibt ausdrücklich offen.


## Vollständiger funktionaler Preview-Stand nach TRADE-10

- TRADE-01/08: drei sichtbare Top-Vorschläge aus dem vorhandenen geordneten Fünferpool, Dismiss/Nachrücken, vollständiger Partnerpool, Paaransicht und Partner-SmartDeal.
- TRADE-09: kanonisch adaptierte Multi-Album-Stickerliste, Receive/Give-Auswahl, gelber Mengenzettel, bilaterale Freigaben, eingeschränkte Album-Pools, offener Ausgleich, Receive ≤ Give, explizite Überprüfung und normaler Request-Submit.
- TRADE-02/03: eingefrorene Anfrage, absolute 24h, gespiegelte Empfängeransicht, Annehmen/Ablehnen und operativer Kapazitätsvertrag.
- TRADE-04/05/08: Packliste, ausdrückliche Gesamtfreigabe, exakte Fehlpositionen, explizites Pre-Shipment-Amendment, Partnerzustimmung/Beenden, Snapshotversionen.
- TRADE-06/07: richtungsbezogene Pack-/Adress-/Versandfreigabe, eigene Slotfreigabe, Q2-Empfang ohne Partnerklick, Problem/Resolution, Abschluss und optionale 1–3-Sterne-Bewertung.
- TRADE-10: reine Übersicht laufender Vorgänge in Eingegangen / Du bist dran / Wartet, direkte rollenrichtige Lifecycle-Links, Fristprojektion, ausgeblendete terminale Vorgänge und weiterhin erreichbarer Q2-Weg. Keine eigene State Machine oder neue Historie.

Diese Vollständigkeit bezeichnet bedienbare lokale Preview-Funktionen. Sie ist keine Aussage über produktive Persistenz, Privacy, Concurrency oder Buchungsreife.

## Nachweise nach TRADE-10

[TRADE-10-Audit](TRADE_10_AUDIT.md), [neue Browser-/Projektionsprüfungen](../tests/research/artifacts/trade-10/checks.json), [Regressionsgalerie TRADE-01–09](../tests/research/artifacts/trade-10/index.html) und [Datei-/Schutznachweis](../tests/research/artifacts/trade-10/scope-checks.json).

Die alten E2E-Gates bleiben erhalten. Hinzu kommen die vollständigen manuellen 2/3-Journeys von TRADE-09 bei vier Breiten sowie die rein lesende Projektion, alle Lifecycle-Direktlinks, Gruppen und Q2-Zugänge von TRADE-10. Die obsolete Pack-Einzelabhakung wurde in TRADE-08 ausschließlich als UI-Interaktion durch bewusste Gesamtfreigabe ersetzt; das bestehende validierte Positionsmodell bleibt erhalten.

## Bewusst spätere Gestaltung und Funktionen

Nach produktiver Integration gesondert zu gestalten/entscheiden: endgültige Tauschhauptseite, Alle-Sammlr-Filter, zentrale Tauscheinstellungen, Album-Kippschalter, Favoritenalbum-Gewichtung, Notification-/Post-it-System, Foto-/Scan-Versandnachweis, produktive Historie, weitere Reputation und Pax-Zukunftskonzept. Vorhandene Preview-Filter und der minimale TRADE-07-Erledigt-Zugang sind keine fertige produktive Informationsarchitektur. TRADE-10 erweitert diesen historischen Zugang nicht.

## Vor Integration zu ersetzende Demo-Daten

1. Synthetische Partner, Matchpotentiale, Top-Reihenfolge, Stickerkatalog-/Need-/Supply-Daten und manuelle Albumfreigaben durch autorisierte kanonische Daten und bestehende Algorithmusadapter ersetzen.
2. SessionStorage, feste Demo-IDs, simulierte Rollenwechsel und explizite Szenario-Resets durch echte angemeldete Teilnehmer, stabile Angebotsidentität und persistierte versionierte Trades ersetzen. Die gemischte Overview-Demo besitzt Rollen je Vorgang, keinen gemeinsamen eingeloggten Nutzer.
3. Lokale Uhr/Requestfristen durch autoritative Zeit und bestehende absolute Fristregeln; Fristen-/Withdraw-/Reminder-Review bleibt offen, bis dahin 24h unverändert.
4. Fiktive Adressen, angenommene Eigentümerfreigaben und Demo-Versandportal durch datenschutzkonforme Freigaben und ausdrücklich entschiedene Carrier-Anbindung ersetzen.
5. Lokale Pack-/Shipping-/Receipt-/Problem-/Ratingmodelle über reale autorisierte Services anbinden, keine Übernahme als vertrauenswürdige clientseitige Produktionsdomain.

## Kanonisierung und technische Integrationsgates

- Separater neuer Contract-Type/Lifecycle, Legacy-Adapter und keine rückwirkende Migration. Herkunft ist kein Contract-Type.
- Vorhandene Availability-/Reservation-/Transit-/Eigenexemplarregeln und SmartDeal-Optimizer wiederverwenden; atomare frische Bindung, Need-/Supply- und 3/3-Slotprüfung, Idempotenz und konkurrierende Gegenangebote absichern.
- Manual-Settings pro Album/Teilnehmer: tradeEnabled, smartEnabled, crossAlbum. Bilaterale Schnittmenge ausdrücklich nur für neue Trade-v2-Angebote. Aktuelle Einstellungen und Eligibility vor Submit serverseitig validieren.
- Exakte Amendment-Zustimmungen und Versionen, Teilversand-/Receipt-Schutz, Snapshotfreeze sowie autorisierte physische Buchungen einschließlich Q2 mit vorhandenen Services verbinden.
- Receipt darf keinen Versandklick ersetzen und keinen Slot freigeben. Completion kann trotz fehlender Versandklicks bestehen. Ein solcher abgeschlossener Vorgang verschwindet aus der primären Übersicht; die verbleibende eigene Versandbestätigung bleibt im bestehenden Abschlussweg zugänglich.
- Reine gemeinsame Stickerfaces/Stackquelle und Stickerlisten-Präsentation später kontrolliert kanonisieren; Wall5/Trade10, −2/−2, z-index und 16/20-Post-it-Mengen beibehalten. Keine produktive Refaktorierung in TRADE-10.
- Overview wird als read model an autorisierten Nutzer und bestehende Lifecycle-/Slotservices angeschlossen. Keine parallelen INBOX-/NEEDS_ACTION-Domainzustände; kein Rückschluss von einer ausgeblendeten Zeile auf freie Kapazität.
- Finale Legacy-/Privacy-/Concurrency-/Buchungs-/Idempotenz-Tests und manuelle Produktabnahme vor Freigabe. Keine produktive Integration ist durch diesen Audit bereits autorisiert oder erfolgt.
