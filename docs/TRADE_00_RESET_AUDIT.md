# TRADE-00 — Reset Audit

Stand: 2026-09-30. Dokumentationsauftrag, keine Implementierung.

Ergebnis: Das neue Zielbild ist als zukünftiger, versionierter Vertrag widerspruchsfrei dokumentierbar. Bestehende Runtime ist damit weder umgestellt noch als kompatibel zertifiziert. Die unten genannten Integrationskollisionen verbieten eine ungeprüfte Übernahme bestehender Pfade; sie erfordern keinen Abbruch der reinen Dokumentation.

Neuer Vertrag: [TRADE_PRODUCT_CONTRACT_V2.md](TRADE_PRODUCT_CONTRACT_V2.md).

## Geprüfte Quellen

| Quelle | Prüfgegenstand |
| --- | --- |
| [SmartDeal Product Bible V1](SMARTDEAL_PRODUCT_BIBLE_V1.md), insbesondere §§9–22, 25–27, 32, 37–39 | Vorschläge/Bindung, Partnerpool, manuelle Angebote, Mengen, alte Quote, Privacy und PO-Präzisierungen. |
| [SmartDeal Algorithm Contract V1](SMARTDEAL_ALGORITHM_CONTRACT_V1.md), insbesondere AC01–14, AC17–27 | Globale Planung, Paarpotential, Comparator, Minimum fünf, Freeze, Frist, Mutual-GO, Legacy-Schutz. |
| [Trade UX PO Decisions Q1–Q8](TRADE_UX_PO_DECISIONS_Q1_Q8.md) | Fehlmengen, Empfang, Albumpräferenz, Manual-Submit, Paarpotential, Bewertung, Benachrichtigungen, Ranking und Adressschutz. |
| [Trade UX Soll V1](TRADE_UX_SOLL_V1.md) | Bisherige Navigation, Einstieg und manuelle Wege. |
| [Manual Offer Domain Contract V1](MANUAL_OFFER_DOMAIN_CONTRACT_V1.md) | Manueller Mengenvertrag, Albumpräferenz, atomare Bindung und Abgrenzung zum bestehenden Legacy-Pfad. |
| [SammlrPax Contract V1](SAMMLRPAX_CONTRACT_V1.md) | Bereits entschiedene zukünftige 3/3-Regel, begrenzte Amendment-Supersession, unveränderte AC23-Frist, Legacy-Grenze. |
| [PAX-05 Audit](PAX_05_AUDIT.md), [PAX-06 Audit](PAX_06_AUDIT.md) | Anfrage/Spiegelung/Packen, Adressgate, Versandrichtungen, lokaler Demo-State und Slotprojektion. |
| `App/services/smartdeal_optimizer.py`, `smartdeal_pairwise.py`, `smartdeal_suggestions.py`, `smartdeal_requests.py` | Vorhandene Optimierung, Paarpotential, Mindestgröße/Identitätsprüfung, Fresh Validation und tatsächliche V1-Anfragequote. |
| `App/services/trade_contracts.py` | Explizite Legacy-/SmartDeal-V1-Klassifikation; unbekannte Typen werden zurückgewiesen. |
| `App/webapp.py`, insbesondere Trade-Center/-Wall, `create_trade_request`, Annahme-/Versand-/Empfangspfade | Tatsächliche produktive Routen und Grenzen der bestehenden manuellen Mechanik. |
| `App/services/trade_shipping.py` und bestehende Reservation-/Empfangsanbindung | Richtungsbezogene autorisierte physische Abwicklung, keine zweite Versandmaschine. |
| Isolierte `App/pax/`-Factory/Routes/Fixtures, Pax-Templates und `App/static/pax/`-Renderer, Lifecycle-, Journey- und Shipping-Assets | Trennung zwischen lokalen UX-Mechanismen und produktiven Services; keine Gleichsetzung des Demos mit einer Domainengine. |

Die Klassifikation bezieht sich auf die relevanten Vertragsabschnitte und Implementierungspfade. Historische Testresultate in PAX-Audits sind Quellenbefunde, keine in TRADE-00 erneut ausgeführten Tests.

## A — Weiterhin gültig

| Entscheidung | Begründung / Grenze |
| --- | --- |
| Bestehender SmartDeal-Algorithmus | Globale zulässige Planung, AC11–14-Optimierung/Comparator, deterministische Auswahl, höchstens fünf Deals, ein Partner pro Dealplan. Keine neue Heuristik. |
| Supply und Need | Kanonische freie Supply, Eigenexemplarschutz, Need 0/1, verbindliche Incoming einschließlich Transit und Schutz gültiger Bindungen. Slotfreiheit ersetzt keine Verfügbarkeit. |
| Automatische Erstvorschläge | Exakt 1:1, mindestens fünf Stück, kein neues Maximum. Top-Plan und isoliertes Paarpotential sind unterschiedliche Größen. |
| Vollständiger zugelassener Pool | Top-Vorschläge sind Convenience, keine Reservierung oder Ausschluss anderer Partner. Albumfilter findet Personen und beschränkt nicht still den Deal. |
| Manueller Erstellungsvertrag | Positive Stückmengen, Give >= Receive, beide >= 1; kein SmartDeal-Minimum fünf. `SAME_ALBUM_ONLY` bedeutet pro Album Receive <= Give und gilt nicht pauschal für SmartDeals. |
| Freeze und Zustimmung | Exakter Snapshot, keine stille Änderung/Reparatur, keine rückwirkende Änderung versendeter Richtungen. Neue Amendments nur im bereits autorisierten künftigen Scope. |
| Frist | AC23: absolute 24 Stunden ab Bindung; unverändert, mit PO-Review vor produktiver Integration. |
| Bestehende V1-Identität/Mutual-GO | Exakte gespiegelte Identität, keine Zustimmung durch eigenen Retry; keine automatische Übertragung auf manuelle Angebote. |
| Physische Abwicklung | Packen ist keine Buchung; eigener Versand bewusst, richtungsbezogen und idempotent. Beide versendet ist weder Empfang noch Abschluss. |
| Datenschutz / Adressen | Konkreter Trade, berechtigter Teilnehmer und Eigentümerfreigabe erforderlich; Packfreigabe allein genügt nicht. |
| Q2/Q6/Q7 | Tatsächlicher Empfang ohne erfundene Versandzeit, bestehende Bewertungsberechtigung und relevante Ereignisbenachrichtigungen bleiben. Fehlende Adapter/Ereignistypen sind nicht durch UX-Texte implementiert. |
| Legacy-Grenze | Bestehende Vorgänge behalten Contract-Type, Regeln und Historie. Keine Migration durch Dokumentation. |
| Kanonischer Stack | Wall5, Trade/Receive10; identische −2/−2-Geometrie, Faces, Dimensionen, Front und z-index. Extraktion erst nach vollständigem Lifecycle. |

## B — Zukünftig ersetzt

| Alte Annahme / Fundstelle | Beschlossene Ersetzung |
| --- | --- |
| SammlrPax Contract §4 und Pax-Discovery: Pack als Produktobjekt, öffnen/aufreißen | Top-Tauschvorschläge als Stickerstapel. Pax ist nicht das primäre Produktmodell. |
| Pax-spezifische Rahmung der PAX-05/06-Abwicklung | Gemeinsamer Lifecycle aller neuen Herkunftswege. Die Interaktionen bleiben wertvoll. |
| Ältere verpflichtende Einstiegskomposition aus Trade UX Soll V1 | Zwei Discovery-Ebenen: Top-Vorschläge und Alle Tauschpartner. Operative Anfragen/Trades bleiben notwendig, ohne jetzt eine endgültige Navigation zu bauen. |
| Manueller Umweg im schnellen Vorschlagsflow | Top ansehen → anfragen; manuell über Partneransicht. |
| Product Bible §32, offene gesonderte SmartDeal-Inszenierung | Kanonischer Stapel, keine Pax-/Booster-Verpackung. |
| Product Bible §18/§38, AC22, Manual Contract §5 und Q4: V1-Pending-Ausgangsquote/manuelle Ausnahme | Gemeinsame operative 3/3-Regel, bereits durch PAX-00 für den zukünftigen Zweig autorisiert und jetzt auf das gemeinsame Zielmodell bezogen. Annahme gibt keinen Slot frei; eigener Versand schon. |
| Q1, Bible §37.4/§39 und AC25/26: strikter Ausschluss reduzierter Fortsetzung | Begrenzte, bereits autorisierte zukünftige Pre-Shipment-Amendments. Nicht ersetzt werden Freeze, explizite Zustimmung und Schutz physisch versendeter Richtungen. |

Diese Ersetzungen sind keine offenen PO-Fragen und kein Auftrag, ältere Dateien umzuschreiben. Unentschieden sind die ausdrücklich genannten technischen Repräsentationen und noch fehlenden Übergangsdetails. AC23 wird ausdrücklich nicht ersetzt.

## C — Nur Pax-Prototyp

- Verpackung, Pax-Wording, Öffnungsinszenierung und Kiosk-Produktobjekt werden konserviert, nicht in den primären Trade-Einstieg übernommen.
- Feste Kandidaten und Rollenwechsel simulieren Partner. Lokaler Browser-/Session-State ist keine synchronisierte Mehrbenutzer-Domain und keine produktive Anfrage.
- PAX-05 demonstriert eingefrorene gespiegelte Pakete, Warten, Annahme und Packfortschritt. Fehlmengen-UX implementiert keine atomare Amendment-Bindung.
- PAX-06-Fakeadressen besitzen simulierte Eigentümerfreigabe. Sie belegen keinen produktiven Consent-/Adressspeicher.
- Lokaler Portal-Demoschritt ist keine belegte DHL-/Carrier-Integration und kein Versandkauf. Eigene Versandmarkierung im Demo bucht keine realen Bestände.
- Die Slotanzeige mit zwei weiteren fiktiven Verpflichtungen ist eine Projektion, keine gemeinsame Slotengine.
- `status: packing` im angenommenen Demo-Zweig ist kein finaler Domainstatus. Request-State und getrennte Versandzustände bleiben fachlich verschieden.
- Bestehende Stack-/Post-it-/Fan-Interaktionen sind visuelle Referenzen. Keine neue CSS-Kopie und kein vorgezogener Komponentenumbau in TRADE-00.

Alle Pax-Dateien, Assets, Tests und Dokumente bleiben erhalten. „Archiviert“ bezeichnet ihre Rolle; es findet keine physische Archivierung, Löschung oder Abschaltung statt.

## D — Domainkollisionen und Gates vor Implementierung

| Konkrete Kollision bei direkter Übernahme | Status / erforderliche Auflösung |
| --- | --- |
| `smartdeal_requests.py` zählt gültige offene ausgehende V1-Anfragen; Ziel zählt gemeinsame operative Verpflichtungen auch nach Annahme und außerdem eingehend. | Ziel entschieden. Separates versioniertes Kapazitätsmodell und atomare Prüfung erforderlich; bestehenden V1-Count nicht semantisch umwidmen. |
| `create_trade_request` ist ein Legacy-Pfad mit Single-Album-JSON und ohne die neue beidseitige atomare Submit-Bindung; Manual Contract fordert diese für neue Angebote. | Ziel entschieden, Adapter fehlt. Keine neue manuelle Abwicklung ungeprüft auf diesen Pfad setzen, keine Legacy-Migration. |
| `trade_contracts.py` kennt Legacy und SmartDeal V1; die neuen Herkunftslabels liefern keinen vollständigen neuen Domainvertrag. | Neue Versionierung und Dispatch vor Integration definieren. Unbekannte Typen weiter fail-closed; nicht aus UI-Herkunft ableiten. |
| Paarpotential ist auch unter fünf sichtbar, aber `SmartDealSuggestionValidator._payload_identity` lehnt automatische Vorschläge unter fünf ab. | Kein aktueller Widerspruch: Anzeige ist keine Anfragefreigabe. Automatische Unter-fünf-Erstellung braucht gesonderten PO-Entscheid; bis dahin bestehendes Minimum. |
| Globaler Optimizer plant über mehrere Partner; Paarpotential allein enthält noch keinen nach denselben Regeln erzeugten konkreten Partner-Snapshot. | Technischer Adaptionsauftrag für später, keine Erlaubnis für neue Greedy-/Zufallsauswahl oder stilles Trimmen. |
| Legacy/V1-Unfulfillable-Regeln versus neue bestätigte Amendments. | Begrenzte Supersession entschieden. Exakte Zustimmungen, Bindungswechsel, Konfliktprioritäten und Teilversand-Fälle noch offen; keine stille Reparatur und keine Änderung versendeter Richtungen. |
| Gemeinsamer Lifecycle versus unterschiedliche Erstellungs-/Zustimmungsregeln, insbesondere V1-Mutual-GO und explizite Manual-Annahme. | Validatoren und Versionen erhalten. Herkunftsübergreifende Duplikat-/Gegenanfrage-Identität muss vor Implementierung entschieden werden; kein pauschales Auto-Accept. |
| Q2 erlaubt tatsächlichen Empfang trotz fehlendem Partner-Versandklick; der hierfür vorgesehene produktive Adapter ist nicht durch PAX-06 ersetzt. | Bestehende Schutzguards nicht entfernen. Genau-einmal-Buchung ohne erfundene Versandhistorie im gemeinsamen Lifecycle absichern. |
| Gewünschter möglicher „1:1 im selben Album“-Filter versus bestehende Manual-Präferenz mit Receive <= Give und reinem Discovery-Albumfilter. | Filtersemantik ist offen, keine bereits beschlossene Verschärfung oder neue SmartDeal-Regel. |

Zusätzliche offene Integrationsfragen sind Adresszugriff/Retention, konkrete Carrier-Anbindung sowie vollständige Problem-/Empfangs-/Abschlussübergänge. Die gültige 24-Stunden-Regel ist dagegen **keine ungelöste Kollision**; der Review-Marker erlaubt noch keine Änderung.

Keine dieser Kollisionen zwingt zu einer heutigen produktiven Änderung. Der neue Vertrag grenzt sie aus und enthält keine widersprüchliche Verpflichtung zur sofortigen Übernahme. Daher kein Domain-STOP für TRADE-00.

## Umfang und Prüfung

Neu erstellt, ausschließlich:

- `docs/TRADE_PRODUCT_CONTRACT_V2.md`
- `docs/TRADE_00_RESET_AUDIT.md`

Prüfung: Quellenabgleich, explizite Supersessions, Erhalt der Legacy-Grenze, Trennung von Herkunft/Contract-Type/Request/Slot/physischer Richtung und Abdeckung der geforderten Vertragsthemen. SHA-256-Abgleich mit dem vor dem Auftrag aufgenommenen Bestand unter `App/`, `docs/` und `tests/` (ohne Cache-Dateien): keine vorbestehende Datei verändert oder gelöscht, nur die zwei beauftragten Dokumente hinzugefügt.

`git diff --check` und gesonderte Whitespace-Prüfung beider neuen, ungetrackten Dokumente: bestanden. Keine Runtime-, Browser- oder DB-Tests ausgeführt, da ausschließlich Dokumentation geändert wurde. Historische PAX-Testergebnisse nicht neu beansprucht.

Keine Produktivdateien, DB, Routen, UI, CSS, JS oder Python verändert. Keine bestehenden Contracts überschrieben. Kein git add, Commit, Push oder Deploy. TRADE-00 endet mit Contract und Audit.
