# Trade UX SOLL V1

Stand: 2026-09-12. Status: dokumentierter PO-SOLL für die folgende gemeinsame Screen-für-Screen-Designphase; **keine Implementierungsfreigabe**. Alle 44 Abschnitte des Auftrags sind in §23 nachverfolgt. Arbeitsformulierungen bleiben Arbeitsformulierungen. **Night-Prep-Nachtrag:** Q1–Q8 sind durch den verbindlichen [Decision Record](TRADE_UX_PO_DECISIONS_Q1_Q8.md) geschlossen. Frühere Konflikt-/Fragentabellen in §21 dokumentieren den Ausgangsstand und sind keine weiterhin offenen Entscheidungen; maßgeblich ist die Auflösung unten.

Grundlagen: [Product Bible](SMARTDEAL_PRODUCT_BIBLE_V1.md), [Algorithm Contract](SMARTDEAL_ALGORITHM_CONTRACT_V1.md), [Roadmap](SMARTDEAL_TECHNICAL_ROADMAP_V1.md), [ursprünglicher Core-Audit](SMARTDEAL_CORE_GATE_AUDIT.md), [CG-1-Fix](SMARTDEAL_CORE_GATE_FIX_CG1.md), [CG-1-Reaudit](SMARTDEAL_CORE_GATE_REAUDIT_CG1.md) sowie [T4](SMARTDEAL_T4_SUGGESTION_REVALIDATION.md), [T5a](SMARTDEAL_T5A_ATOMIC_BINDING.md), [T5b](SMARTDEAL_T5B_RELEASE_EXPIRY.md), [T6a](SMARTDEAL_T6A_OPPORTUNITY_IDENTITY.md), [T6b](SMARTDEAL_T6B_ACCEPT_MUTUAL_GO.md). Codeabgleich insbesondere mit `App/webapp.py`, `services/smartdeal_runtime.py`, SmartDeal-Domainservices, `trade_receipt.py`, `trade_shipping.py`, `trade_problems.py`, `trade_ratings.py`, `typed_notifications.py`, `album_privacy.py`, `trade_reservations.py` und History-/Privacy-Projektionen.

Vorhandene Baseline nach CG-1: **Core Gate GREEN, Design Gate GREEN, Full Release 1251/1251 GREEN**. Diese Zahlen sind vorhandene Nachweise, kein neuer Testlauf. CG-1 sperrt nicht freigegebene V1-Lifecycle-Aktionen bis T7a. Das neue Design darf daher zukünftige Zustände beschreiben, ohne sie als bereits ausführbare Runtime auszugeben. Neue Konflikte dieses PO-SOLL werden nicht durch das frühere GREEN automatisch entschieden.

## 1. Product Intent

Sammlr ersetzt keine Sammler. Sammlr unterstützt Sammler. SmartDeal ist die intelligente Standardlösung; der Sammler darf alternativ selbst einen Tausch zusammenstellen. Der Bereich soll wenig Navigation und wenig Verwaltungsgefühl erzeugen. Zustände und notwendige Aktionen kommen zum Nutzer.

Die zukünftige UX folgt diesem PO-SOLL statt der historischen Seitenstruktur. Domain-, Privacy- und Lifecycleverträge werden nicht still überschrieben. Insbesondere bleiben SmartDeal-Paketidentität, 1:1, unveränderliche Bindungen, absolute 24h und physische Buchungswahrheit geschützt, solange ein markierter Konflikt nicht ausdrücklich neu geschlossen wurde.

## 2. Navigation Principle

Eine zentrale Seite **Tauschen**, bevorzugt Inline-Expansion, eine echte **Partnerdetailansicht** und eine sekundäre **History**. Nicht jeder Status erhält eine Seite. Zusätzliche Detailansichten nur bei tatsächlich notwendiger Informationsmenge oder Sicherheit, noch ohne Festlegung ihrer URLs.

Normale SmartDeal-Ansicht und erfolgreiche Anfrage führen nicht auf eine neue Seite. Der manuelle Composer ist ein gemeinsamer Baustein für beide Einstiege; ob er inline, als fokussierte Fläche oder in einer anderen Darstellungsform erscheint, ist Designfrage. Kein zweiter Composer und keine zusätzliche gleichwertige Request-/Versand-Hauptnavigation.

Bestehende sichere Notification-/Detail-Deep-Links und erlaubte Rückziele dürfen bei späterer Integration nicht verloren gehen. Ihre Abbildung auf einen geöffneten Inlinezustand ist T9/T10-Arbeit, keine jetzt beschlossene Routenlöschung.

## 3. Tauschen Home

Feste Grundreihenfolge:

1. **Handlungsbedarf**, nur wenn vorhanden.
2. **SmartDeals**.
3. **Alle Tauschpartner**.
4. **Vergangene Tausche** als sekundärer Zugang ganz unten.

Ohne Handlungsbedarf beginnt die Seite praktisch mit SmartDeals. Keine permanente leere Verwaltungsbox. Leere Bereiche belegen nicht unnötig Platz. Die konkrete Erklärung eines leeren SmartDeal-Plans bleibt Design-/Microcopyarbeit; sie darf kleine zulässige Partnerchancen nicht als „kein Tausch möglich“ ausgeben.

## 4. Handlungsbedarf

Vor neuen theoretischen Vorschlägen stehen eingehende Anfragen, relevante offene eigene Anfragen, angenommene Tausche, notwendige Versand-/Empfangsaktionen und relevante Probleme. Handlungsbedarf ist eine UX-Projektion über mehrere fachliche Zustände, kein neuer DB-Status.

Laufende Trades zeigen kompakt Partner, Paketumfang, relevanten Fortschritt und nächste Aktion, etwa „Fatima hat versendet · Du bist dran“. Welche gleichzeitige Aktion zuerst hervorgehoben wird, ist noch nicht endgültig festgelegt; beide physischen Richtungen bleiben sichtbar und korrekt. Nicht auf unbestimmte Weise „Du bist dran“ anzeigen, wenn die verfügbare Aktion noch ungeklärt oder fachlich gesperrt ist.

## 5. SmartDeals

Bis zu fünf aktuelle Top-SmartDeals direkt untereinander, keine künstliche Beschränkung auf drei plus „mehr“. Mindestgröße **5↔5**, keine künstliche Maximalgröße. Die Karten stammen aus einem gemeinsam ausführbaren globalen Plan; einzelne Partnermaxima dürfen diesen Plan nicht ersetzen.

Geschlossen: Partner, dominante Dealgröße, Anzahl tatsächlich beteiligter Alben und Zugang „Deal ansehen“. Beispiel: Fatima / 23↔23 / 6 Alben. Keine vollständigen Albumlisten, Stickerlisten, Scores, Prozent-Matches oder Optimierungsdetails. Porto/Briefanzahl sind keine notwendige sichtbare V1-Komponente; die interne Versand-Effizienzregel bleibt unverändert.

Geöffnet bevorzugt inline: zuerst verständlich „Du bekommst X“, nach Alben gruppierte konkrete Sticker; außerdem „Du gibst X“, ebenso vollständig gruppiert. Erst nach Sichtung dieses konkreten Pakets darf angefragt werden. Die technische Identity ist richtungsunabhängig; die Anzeige spiegelt die tatsächlichen Leistungen für den Viewer.

Primary Action als Arbeitsbegriff **„Tausch anfragen“**, sichtbares „GO“ verworfen. Finales Wording bleibt offen. Sekundär und deutlich weniger prominent **„Tausch selbst zusammenstellen“**, zum selben Composer wie auf Partnerdetail. Das bearbeitet nicht den eingefrorenen SmartDeal.

Nach erfolgreicher Anfrage bleibt der Nutzer im Kontext: sinngemäß „Tausch angefragt ✓ / Fatima hat 24 Stunden Zeit zu antworten / Deine betroffenen Sticker sind reserviert“. Fachlich sind **beide Seiten** und deren Incoming Needs gebunden; das verkürzte Beispiel darf keine einseitige Bindung behaupten. Bei später erneut geöffneter Anfrage beginnt kein neuer 24h-Zeitraum. Anschließend aktuelle Neuberechnung, wodurch andere Vorschläge wechseln können.

Exakt gleicher Gegenwunsch führt nach T6b zur Annahme derselben Instanz: sinngemäß „Tausch steht! Du und Fatima wolltet denselben Tausch. 23↔23“. Kein technisches „Mutual GO“ in der UX, keine zusätzliche Kreuzanfrage/Bestätigung. Positive Hervorhebung erwünscht, konkrete Animation nicht entschieden. Ein eigener Retry bleibt pending. Ein anderes konkretes Paket ist keine gegenseitige Übereinstimmung.

Stale/ungültig, Quote erreicht, Busy oder verlorene Berechtigung dürfen nicht als erfolgreiche Anfrage erscheinen. Keine heimliche Paketkorrektur. Das konkrete Fehlerwording folgt später; erneute Berechnung ist keine Veränderung eines bestehenden Vertrags.

## 6. Requests

Ein gemeinsamer Bereich für offene eingehende und ausgehende Anfragen, Richtung eindeutig. Beispiel: „Fatima · 23↔23 · erhalten“ beziehungsweise „Peter · 12↔12 · von dir angefragt“.

Eingehend aufklappen → exaktes Paket ansehen → Annehmen/Ablehnen. Ausgehend aufklappen → exaktes Paket ansehen → gegebenenfalls Zurückziehen. Keine eigene Requests-Hauptnavigation. T6b erlaubt explizites Accept nur dem Empfänger; T5b erlaubt Decline dem Empfänger und Withdraw dem Initiator. Abgelaufene oder terminale Anfragen bieten keine ungültige Annahme.

V1-Frist ist allein `binding_created_at + 24 Stunden`, absolute Dauer. CG-1 räumt fällige Pending-Anfragen beim nächsten relevanten Runtimezugriff auf; die Annahmegrenze gilt auch ohne vorherigen Cleanup. Maximal drei gleichzeitig offene eigene **SmartDeal-V1**-Anfragen ist unabhängig von fünf Vorschlägen. Diese Regeln nicht ohne Entscheidung auf neue manuelle Angebote übertragen. Altanfragen behalten ihren Vertrag.

## 7. Laufende Tausche

Angenommene Trades liegen in Handlungsbedarf/laufende Tausche. Kompakte geschlossene Karte, inline geöffnet soweit die Informationsmenge sinnvoll beherrschbar bleibt. Keine separate Versand-Hauptnavigation.

Fortschritt zeigt zwei getrennte Bewegungen:

- **Meine Sendung:** Tausch steht → Versendet → Angekommen.
- **Fatimas Sendung:** Tausch steht → Versendet → Angekommen.

Trackinggefühl darf DHL-inspiriert sein, keine DHL-Kopie. Kein eigener Zustand „Verpackt“ und kein entsprechender Pflichtklick. „Angekommen“ meiner Sendung beruht auf Bestätigung des Partners, „Angekommen“ seiner Sendung auf meiner Bestätigung. Zwei Versandbestätigungen sind kein abgeschlossener Trade.

Zusätzlich können Kontakt-/Freigabebedarf, Wartezustand oder Problem den jeweils nächsten Schritt bestimmen. Aktuell ist accepted V1 bindend, aber Shipping/Receipt/Completion sind durch CG-1 bis T7a gesperrt. Diese technische Sperre wird nicht als zukünftiger Produkt-Endzustand entworfen.

## 8. Versand / Empfang

Nächste Aktion beispielsweise **„23 Sticker versenden“**, keine Verpackungsanweisung. „Als versendet markieren“ erhält vor endgültiger Buchung eine kurze Bestätigung, etwa „23 Sticker wirklich versendet?“. Erst tatsächlicher eigener Versand bucht die eigenen gelieferten Positionen physisch aus. Accept und Reservation buchen nichts aus; fremder Versand erzeugt noch keinen eigenen Besitz.

„Sticker erhalten“ macht vor Bestätigung klar, welche Menge als physisch eingegangen gebucht wird. Erst der bestätigte reale Eingang erhöht den eigenen Bestand. Teil-/Fehlempfang darf nicht pauschal die gesamte erwartete Menge buchen; vorhandene Problem-/Partial-Receipt-Verträge schützen.

**Verbindliche PO-Entscheidung Q2:** Empfang soll auch ohne vorherigen Versandklick des Partners möglich sein, da physische Realität stärker ist als ein vergessener Statusklick. **Aufgelöster Konflikt C2; technischer Gap bleibt:** `TradeReceiptService.receive` fordert eine Shipping-Statuszeile und den Versandflag der Gegenseite, sonst INVALID_TRADE_STATE/NOT_SHIPPED. Weder bloßes Entfernen dieses Guards noch automatisches Nachbuchen/Datieren fremden Versands ist hier beschlossen. T7a muss den expliziten neuen Ableitungs-, Autorisierungs-, Buchungs- und Retryvertrag schließen.

**„Sticker nicht auffindbar?“** vor Versand sekundär, sichtbar und nicht im allgemeinen Problemmenü versteckt. **Q1 verbindlich:** Keine Reparatur oder Entfernung eines gleichwertigen Gegenstickers. Vor erstem physischen Versand vollständig unfulfillable/beenden/freigeben/informieren, unverändertes Paket erhalten und neu berechnen; nach Versand Problem-/Action-required-Flow. Die frühere Ausbalancierungs-Idee ist ausdrücklich verworfen. AC25/26 bleiben maßgeblich.

Allgemeine Konflikte sekundär, etwa „••• → Problem mit diesem Tausch“. Nach erstem tatsächlichen Versand schützt der bestehende Vertrag physische Fakten und verlangt einen Problem-/Action-required-Weg statt gewöhnlicher automatischer Freigabe. Vor Versand verlangt der gesperrte Vertrag derzeit vollständiges Beenden/Freigeben/Informieren und unabhängige Neuberechnung. Q1 bestätigt diese bestehende Regel ausdrücklich.

## 9. Adresse

Versandadresse erst nach angenommenem Deal und kontrollierter Freigabe relevant. Keine vollständige Anschrift dauerhaft offen auf der Übersicht. Beispiel „Versand an / Fatima M. · Berlin / Adresse anzeigen“; vollständige Anschrift erst nach bewusster Anzeigeaktion.

**Freigeben und Anzeigen sind zwei unterschiedliche Handlungen:** Der Eigentümer gibt für den konkreten bestätigten Partner frei; der bereits berechtigte Empfänger öffnet anschließend die geschützte Anzeige. Ein „Adresse anzeigen“-Klick ersetzt weder Eigentümerzustimmung noch serverseitige Berechtigung. Auch Stadt/Kurzname aus Versanddaten dürfen nicht vor der entsprechenden Berechtigung in öffentlichen Projektionen erscheinen.

Beim ersten relevanten Deal Adresse eingeben; optional „Für zukünftige Tausche speichern“. Keine Pflicht, keine Signup-Pflicht, keine automatische Freigabe an neue Partner. T8a muss Speicherung, Retention, Änderungen, Widerruf, Accountende und Problemzugriff technisch konkretisieren. Nicht entschieden sind konkrete Fristen oder ein neues Datenmodell. Diese UX-Richtung stimmt mit Bible §37.3 überein, ist aber noch nicht implementiert.

## 10. Abschluss / Bewertung

Erfolgreicher Versandtrade erst nach beiden physischen Empfangsbestätigungen entsprechend finalem Lifecycle. Nicht bei beidseitigem Versand. Kurz positiver Zustand „Tausch abgeschlossen / +X Sticker für deine Sammlung“, anschließend vergangene Tausche. X darf nur tatsächlich eingegangene Mengen ausdrücken, keine nochmalige Buchung beim Abschluss. Problemabschluss ist kein erfundener erfolgreicher Volltausch.

Optional „Wie lief der Tausch mit Fatima? / 1–5 Sterne / Später“. Keine Pflicht, keine notwendige Textrezension. Vorhandener `TradeRatingService` unterstützt 1–5, Beteiligte und einmalige Bewertung je Seite; erlaubt derzeit auch `closed_with_problem` und `problem_resolved_after_close`, nicht nur `completed`. Die neue Darstellung nach Abschluss darf diesen geschützten Umfang nicht still entfernen: C7/Q6.

Bewertung soll perspektivisch Vertrauen und Sortierung unterstützen. **AC17 schützt den SmartDeal-Optimierer:** Rating ist kein Gewicht/Tie-Break des globalen V1-Plans. Spätere Discovery-Sortierung ist davon getrennt. Dies ist keine Ermächtigung, den Core-Comparator zu ändern.

**Verbindlicher Notification-Vertrag Q7:** Eigenständig relevant sind neue Tauschanfrage, „Tausch steht.“ bei Annahme/gegenseitiger Übereinstimmung, Partner hat versendet und Problem erfordert Handlung. Kein eigener Notification-Zwang für Empfangsbestätigung, Ablauf einer eigenen unbeantworteten Anfrage, SmartDeal-Neuberechnung oder abgegebene Bewertung. Empfang bleibt sichtbarer Trade-Status; Mutual Match erzeugt keine doppelte Annahmemeldung. Aktueller Typed-Katalog enthält Anfrage, Decline, Versand, Rating verfügbar, Unfulfillable, Problem-Aktion und Problem-Terminal; T6b besitzt ein Acceptance-Event, aber noch keine Typed-Accept-Notification, und T5a erzeugt noch keine neue Anfrage-Notification. C8 ist produktseitig geschlossen; diese technischen Anbindungen bleiben spätere Implementierungsarbeit gemäß [Q7 Decision Record](TRADE_UX_PO_DECISIONS_Q1_Q8.md). Bestehende geschützte Notificationtypen werden dadurch nicht entfernt.

## 11. Alle Tauschpartner

Menschen statt mehrfacher isolierter Albumbeziehungen. V1 zunächst größere Tauschmöglichkeit zuerst; Rangmetrik gemäß Q8 ist das gesamte tatsächlich mögliche 1:1-Paarvolumen, absteigend. Spätere Sortierung nach Menge, Bewertung, Entfernung oder Aktivität optional, keine Filter-/Sortierorgie und keine Standortpflicht.

Albumfilter etwa „Alle | WM26 | EM04 | Bundesliga 07/08 | …“. WM26 findet Menschen mit einer dortigen Tauschmöglichkeit; die Karte darf zusätzliche relevante Alben zeigen, und der Einstieg beschränkt nicht automatisch das gesamte Folgepaket.

Partnerkarte: Profilbild, Name, Bewertung, Anzahl seiner Sticker, die mir fehlen, Anzahl meiner Sticker, die er braucht, Anzahl gemeinsamer relevanter Alben. Beispiel „Justus ★4,9 / Hat 37 Sticker, die dir fehlen / Du hast 24 für ihn / 5 gemeinsame Alben“. „24↔24 möglich“ ist ausdrücklich nicht finalisiert; PO bevorzugt die verständlichen Need-/Supply-Aussagen. Zahlen müssen ihren Bezug auf freie kanonische Mengen/Needs klar definieren und dürfen keine gebundenen Stücke als frei ausführbar verkaufen.

Trade-Privacy ist nicht allgemeine Profilöffentlichkeit: ein privat geführtes Album mit erlaubter Poolteilnahme kann tradefähig bleiben. Zusätzliche Profil-/Historydaten nur entsprechend eigener Sichtbarkeitsregeln. Entfernung ist spätere Erweiterung, besonders für persönlichen Tausch, keine V1-Standortpflicht.

## 12. Partnerdetail

Eigenständige Detailansicht, da die Beziehung zwischen zwei Sammlern und größere Informationsmenge im Mittelpunkt stehen. Mögliche Inhalte bleiben als solche gekennzeichnet: Profilbild/Name, Bewertung/Tradehistorie soweit sichtbar, gemeinsame Chancen nach Alben, beide Richtungslisten, bester Smart-Vorschlag und manueller Composer.

Arbeitsaktion „Besten Tausch mit Justus anzeigen“. **Q5:** Gemeint ist das isolierte 1:1-Paaroptimum mit genau diesem Partner aus kanonischen freien Mengen, Needs, Eligibility und Reservations, ausdrücklich nicht dessen Paket im globalen T3b-Plan. Chancen unter 5↔5 dürfen angezeigt werden. Der vorhandene T4-Requestguard wird dadurch nicht implementierungsseitig geändert; Anzeige ist keine automatische Anfrage. Relevante Präferenzen gelten nur im entschiedenen Geltungsbereich (Q3: neu erzeugte manuelle Angebote).

## 13. Manueller Composer

Ein gemeinsamer Composer aus Partnerdetail und sekundär aus SmartDeal. Der Nutzer wählt konkrete Sticker bewusst, gegebenenfalls albumübergreifend gemäß Empfängerpräferenz. Kein editierter SmartDeal unter derselben Identity. Ein manueller Draft reserviert noch nichts; verbindlicher Schutz beginnt nach PO beim tatsächlichen Anfragen.

**Neue explizite Mengenregel:** Initiator darf gleich viel oder mehr geben als verlangen. 10 geben/10 bekommen und 10 geben/8 bekommen erlaubt; 8 geben/10 bekommen verboten. SmartDeal bleibt strikt 1:1. Die manuelle Regel muss später serverseitige Domainregel sein, keine reine UI-Sperre.

IST ist differenziert: `webapp.create_trade_request` enthält bereits `len(give_codes) < len(get_codes)` als Ablehnung und prüft beide Seiten auf nichtleere Listen sowie aktuelle erlaubte Mengen. Es ist aber ein Single-Album-Webpfad; `TradeReservationService.accept` ist kein vollständiger neuer großzügiger Multi-Album-Composer-Vertrag. Bible §4/27 beschreibt manuell bislang freie/ungleiche Vereinbarungen ohne diese Einschränkung. PO-Neuregel erhalten, geschützte alte Verträge nicht rückwirkend ändern (C3).

**Neue Bindungsrichtung:** Tatsächlich angefragte manuelle Ressourcen dürfen nicht parallel in SmartDeal, anderem manuellen Versanddeal oder künftigem QR-Tausch frei erscheinen. Beispiel ARG17 für Justus blockiert dasselbe verfügbare Exemplar für andere Zusagen. Der aktuelle manuelle Create bindet erst bei späterem Legacy-Accept. **Q4:** Beide Supply-Seiten und zugehörige Incoming Needs werden bei Submit atomar nach frischer Prüfung gebunden. Frist absolute 24h ab Bindung; Decline/Withdraw/Expiry vollständig frei, nach Accept weiter gebunden. Kein manuelles Limit wird eingeführt. Eigenständiger Vertrag gemäß Manual Offer Domain Contract, keine SmartDeal-Identity-Übernahme.

## 14. Trade Preferences

Zwei konzeptionelle Empfängermodi:

- **Offener Tausch:** albumübergreifende Angebote, beispielsweise WM26 geben und mehrere ältere Bundesliga-Alben erhalten.
- **Nur albumgleich:** Sticker eines Albums dürfen nur gegen Sticker desselben Albums angeboten werden.

Der Composer darf Empfängereinstellungen nicht verletzen. IST `AlbumPrivacyService` kennt `visibility` und `trade_pool_enabled` pro Nutzeralbum; das sind Sichtbarkeit und Teilnahme, keine Austauschpräferenz zwischen Alben. Im untersuchten kanonischen Schema/Tradepfad ist kein entsprechender Zwei-Modi-Vertrag vorhanden.

**Q3 verbindlich:** Global pro Nutzer, OPEN als Default, nur Empfängerregel für neu erzeugte manuelle Angebote. Wechsel wirkt nicht auf bestehende verbindliche Angebote, angenommene Verträge, Legacy oder den SmartDeal-Algorithmus. Neue Drafts/Submits verwenden die aktuelle Einstellung. SAME_ALBUM_ONLY wird im Manual Offer Contract je Album als `receive_a <= give_a` präzisiert. Kein Umdeuten des Poolflags, keine neue Persistenz in diesem Auftrag.

## 15. Vergangene Tausche

Sekundärer Zugang ganz unten „Vergangene Tausche →“. Bestehende History, unveränderliche Fakten und sichere Detail-/Notification-Zuordnung soweit sinnvoll wiederverwenden. Keine dominante Hauptfläche, kein History-Rewrite.

Erfolg, terminale Anfrage und Problemabschluss bleiben fachlich verschieden. Ob und wie diese Untergruppen im Verlauf sichtbar gegliedert werden, ist spätere Ausgestaltung innerhalb geschützter History-/Privacyverträge; ein Problemabschluss darf keine erfolgreiche Tauschzahl fälschen.

## 16. Future QR Personal Trade

**Future Contract, kein V1-Build:** QR scannen → Partner identifizieren → aktuelle Bestände, Needs und Reservationen live prüfen → vor Ort mögliche physische Tausche anzeigen → gemeinsam bestätigen → Bestände ohne Versand-Lifecycle entsprechend buchen.

Bereits für Fatima reserviertes ARG17 erscheint beim QR-Tausch mit Justus nicht als frei. Gemeinsame kanonische Availability und atomare Reservierungs-/Buchungsgrenzen sollen diesen späteren Weg ermöglichen. Das beschreibt keine jetzt fertige Authentifizierung, Bestätigungsfolge, Buchungs-API oder Frist. Kein Standortzwang, keine QR-Route, kein vorweggenommener persönlicher Tauschstatus.

## 17. Canonical Screen Tree

**Zählung: 3 Screen-/Navigationskontexte und 16 benannte Hauptzustände.** Composer, Adressansicht, Bestätigungen und Expansionen sind hier Komponenten/Zustände, keine zusätzlich beschlossenen Seiten. Technische Fehler-/Leerezustände bleiben ergänzende Varianten. Der Baum definiert keine URLs.

```text
S1 TAUSCHEN
├── Handlungsbedarf (nur falls vorhanden)
│   ├── gemeinsamer Anfragebereich
│   │   ├── eingehend: U03 geschlossen → U04 Paket offen → Annehmen/Ablehnen
│   │   └── ausgehend: U05 geschlossen → U06 Paket offen → Zurückziehen
│   └── laufender Tausch, kompakt / inline geöffnet
│       ├── U07 accepted, Kontakt/Freigabe relevant
│       ├── U08 eigene Versandaktion bereit
│       ├── U09 eine Sendung versendet
│       ├── U10 beide Sendungen versendet, Empfang noch offen
│       ├── U11 ein Empfang bestätigt
│       ├── U12 beide Empfänge / erfolgreicher Abschluss → Bewertung optional
│       ├── U13 Problem / Handlung erforderlich
│       └── U14 terminal beendet (Decline/Withdraw/Expiry/Unfulfillable getrennt)
├── SmartDeals (0 bis 5)
│   ├── U01 geschlossen
│   └── U02 geöffnet: konkrete Leistungen beider Richtungen
│       ├── Tausch anfragen → U05 oder bei exaktem Gegenwunsch U07
│       ├── nicht mehr ausführbar → U15 stale / keine stille Paketänderung
│       └── selbst zusammenstellen → gemeinsamer Composer U16
├── Alle Tauschpartner, menschenbezogen / Albumfilter
│   └── S2 PARTNERDETAIL
│       ├── Sichtbares Profil / Bewertung / gemeinsame Chancen
│       ├── Smart-Vorschlag (Vertrag C6 offen)
│       └── gemeinsamer Composer U16 → manuelle Anfrage (Vertrag C3–C5 offen)
└── Vergangene Tausche → S3 HISTORY
    └── geschützte Fakten / Details, optional berechtigte Bewertung
```

U07/U08 sind UI-Handlungsvarianten desselben angenommenen Vertrags, keine erfundenen DB-Statuswerte. U09–U11 sind Zusammenfassungen zweier unabhängiger Richtungen, keine zwingende lineare Kette: Ein Empfang kann erfolgen, bevor meine Gegensendung versendet wurde. U10 ist nicht Voraussetzung von U11. Der ungeklärte Empfang-ohne-Versandstatus aus C2 wird im Baum nicht durch eine heimliche Kante entschieden.

Pro Richtung gilt als bisheriger Vertrag: angenommen/unversandt → tatsächlich versendet → durch Empfänger bestätigt angekommen. Der normale Gesamterfolg verlangt beide Empfänge; Problemzustände können daneben bestehen. U14 fasst nur die Navigation zusammen und muss seinen konkreten terminalen Grund behalten. Die Korrekturidee „Sticker nicht auffindbar“ erhält bis C1-Klärung bewusst keinen erfundenen gültigen Zielzustand.

## 18. State / Action Matrix

**20 sichtbare Hauptaktionen.** „Implementiert“ bewertet den vollständigen angefragten SOLL-Pfad, nicht nur eine ähnliche Legacy-Funktion. Bei NEIN wird vorhandene Domainbasis ausdrücklich genannt. S = Supply-Reservation, N = Incoming-Need-Bindung. Kein neuer Notificationtyp wird durch diese Matrix freigegeben.

| ID / Aktion | Actor; Ausgang → Ziel | Erwarteter Domainservice | Persistenz / S+N / Inventory | Notification | SOLL implementiert? / Block |
| --- | --- | --- | --- | --- | --- |
| A01 SmartDeal ansehen | Viewer; U01 → U02 | T4 Suggestion + T6a Identity als unverändertes Paket lesen | Keine Vertragsmutation; keine Bindung/Buchung | Keine | NEIN inline; Payload JA / T9,T10 |
| A02 Tausch anfragen | Berechtigter Teilnehmer; U02 → U05 oder U07 bei exaktem Gegenrequest | T6b `go`, T5a atomarer Create, frische T4-Prüfung | Request/Positionen/beidseitig S+N oder Annahme derselben Instanz; physisch unverändert | Anfrage-Anbindung fehlt; Annahmeevent vorhanden, Typed-Accept fehlt | NEIN sichtbarer Inlinepfad; Core JA / T10,T7a |
| A03 Selbst zusammenstellen | Initiator; U02/S2 → U16 | Gemeinsamer künftiger manueller Composer | Draft; keine verbindliche S/N, kein Inventory | Keine | NEIN / vorgeschlagener Domainblock,T10 |
| A04 Anfrage annehmen | Empfänger; U04 → U07 | CG-1 Adapter → T6b `accept` | Status+accepted_at+Event; vorhandene S/N bleiben; keine Buchung | Acceptance-Event einmal, kein Typed-Accept | NEIN neue Inline-UX; Handler/Domain JA / T9,T10,T7a |
| A05 Anfrage ablehnen | Empfänger; U04 → U14 declined/ggf. expired | CG-1 → T5b `decline` | Vollständige atomare S/N-Freigabe; keine physische Buchung | Bestehende Decline-Notification, nicht bei spät erkannter Expiry | NEIN neue UX; Handler/Domain JA / T10 |
| A06 Anfrage zurückziehen | Initiator; U06 → U14 cancelled/ggf. expired | CG-1 Cancel → T5b `withdraw` | Vollständige S/N-Freigabe; keine Buchung | Kein neuer Typ | NEIN neue UX; Handler/Domain JA / T10 |
| A07 Adresse eingeben | Eigentümer; accepted ohne Versanddaten → Eingabe zur Freigabe | Künftiger T8a-Kontaktservice | Dealbezogene Daten nach noch zu schließendem Speichervertrag; S/N/Inventory unverändert | Nicht entschieden/kein neuer Typ | NEIN / T8a,T10 |
| A08 Adresse freigeben | Eigentümer; accepted → konkreter Partner berechtigt | Künftiger T8a-Freigabecommand | Kontrollierte tradebezogene Berechtigung; keine S/N-/Inventoryänderung | Keine Katalogerweiterung beschlossen | NEIN / T8a |
| A09 Adresse anzeigen | Bestätigter bereits berechtigter Partner; verborgen → bewusst geöffnet | Künftige T8a-Leseprojektion | Kein Freigabeersatz; keine Bindung/Buchung | Keine | NEIN / T8a,T10 |
| A10 Adresse für später speichern | Eigentümer; optionale Eingabe → gespeicherte Wiederverwendung | Künftiger T8a-Service | Optional speichern, keine automatische spätere Partnerfreigabe; S/N/Inventory gleich | Keine | NEIN / T8a |
| A11 Als versendet markieren | Geber; accepted/unversandt → eigene Richtung versendet | Künftiger T7a-Adapter zu `TradeShippingService.ship` | Nach Bestätigung genau einmal ausbuchen; eigene Supplybindung überführen, Incoming-Zusage bleibt | `trade_shipped` vorhanden, V1-Anbindung später | NEIN V1, CG-1 sperrt / T7a,T10 |
| A12 Sticker erhalten | Empfänger; reale Ankunft → eigene Empfangsrichtung bestätigt | Künftiger T7a-Adapter zu `TradeReceiptService.receive` | Tatsächlich bestätigte Menge einmal einbuchen; Need erfüllt; Gesamterfolg nur bei beiden Empfängen | Eigenständiger Empfangstyp fehlt | NEIN V1; ohne Versandflag C2 offen / T7a |
| A13 Sticker nicht auffindbar | Geber vor Versand; Bindung → Ziel ungeklärt C1 | T7b/Inventorykorrektur nach PO-Vertragsklärung | PO will Gegenstückkorrektur; bestehender Vertrag verlangt vollständiges Ende. Keine Mutation spezifiziert | Bestehender Unfulfillable-Typ nur gemäß geschlossenem Vertrag | NEIN / T7b, vorher Q1 |
| A14 Problem melden | Berechtigter Beteiligter; laufend → dokumentiertes Problem | Künftiger T7a/b-Adapter zu `TradeProblemService` | Reale Teil-/Restfakten, kein fiktiver Gesamtreset; exakte Wirkung abhängig von Fall | `trade_problem_action_required` / terminal vorhanden | NEIN V1, CG-1 sperrt / T7a,T7b |
| A15 Bewertung abgeben | Beteiligter; qualifizierter terminaler Trade → bewertet | `TradeRatingService.create` | 1–5, einmal pro Seite; keine S/N-/Inventoryänderung | Verfügbarkeitstyp vorhanden; kein neuer Bewertungseingangstyp verlangt | NEIN neuer V1-Abschlussfluss; Basis JA, C7 / T7a,T10 |
| A16 Partner öffnen | Berechtigter Viewer; Partnerliste → S2 | Trade-Eligibility + getrennte Profil-/History-/Ratingreads | Read-only; keine Bindung/Buchung | Keine | NEIN globales SOLL-Detail / T9,T10 |
| A17 Manuellen Deal anfragen | Initiator; U16 → neue manuelle Pending-Bindung | Neuer manueller Domainvertrag, bestehende Availability wiederverwenden | G≥E, Präferenzen, atomarer Ressourcenschutz; Zeit/Umfang offen; Inventory gleich | Bestehender manueller Anfragetyp als Wiederverwendung prüfen | NEIN; alter Create unreserviert / Domainblock,T10 |
| A18 Besten Partnertausch anzeigen | Viewer; S2 → konkreter Smart-Vorschlag | Noch festzulegender Partnerkontextadapter zu T2a/T2b/T3b/T4 | Vorschlag ohne Bindung/Buchung; keine Änderung globaler Planregeln | Keine | NEIN, C6 / Domainklärung,T9,T10 |
| A19 Vergangene Tausche öffnen | Berechtigter Viewer; S1 → S3 | History/SuccessfulTradeProjection mit Privacy | Read-only, keine Umbuchung beim Öffnen | Keine | NEIN neue IA; Historybasis JA / T9,T10 |
| A20 Albumfilter wählen | Viewer; Partnerliste → gefilterte Menschenliste | Eligibility/Pairwise-Leseprojektion | Keine Bindung/Buchung; Filter findet Personen, beschränkt nicht still Folgepaket | Keine | NEIN globaler SOLL-Ast / T9,T10 |

Systemübergänge sind keine zusätzlichen sichtbaren Aktionen: CG-1-Expiry, Block-Freigabe, frische Neuberechnung und idempotente Retries folgen bestehenden Domainverträgen. Lade-/Busy-/Stale-/Berechtigungsfehler benötigen spätere Darstellung, dürfen aber keine erfolgreiche Mutation vortäuschen. Adresse und Draft sind keine neuen Requeststatus.

## 19. IST → SOLL Gap Matrix

**20 Einordnungen: 4 KEEP / 7 ADAPT / 6 BUILD / 3 REMOVE FROM PRIMARY FLOW.** Zählung je Zeile, keine Mehrfachkategorie. REMOVE bedeutet zukünftige Priorisierung, keine aktuelle Löschfreigabe.

| ID | Bereich / IST-Beleg | Einordnung | SOLL / Gap |
| --- | --- | --- | --- |
| G01 | SmartDeal-Domain T2a–T6b, CG-1 | KEEP | Globaler Plan, exakte Identity, atomare Bindung/Annahme/Freigabe unverändert |
| G02 | Inventory/Availability, Reservations, Ship/Receipt-Grundlage | KEEP | Physische Wahrheit, Eigenexemplar, Mengen, Idempotenz erhalten; neue Ableitung C2 separat |
| G03 | Account/Block/Album-/Profilprivacy | KEEP | Keine Gleichsetzung privates Album = kein Tradezugriff; Kontakt extra geschützt |
| G04 | History/Erfolgsprojektion, unveränderliche Events | KEEP | Tatsächliche Geschichte erhalten, kein Rewrite |
| G05 | `trades_overview`, bisherige Boardsegmente | ADAPT | Zentrale Reihenfolge und bedingter Handlungsbedarf |
| G06 | `trade_open_actions`, vorhandene Requesthandler | ADAPT | Gemeinsamer Richtungsbereich, inline Paket/Aktionen, bestehende Domainadapter |
| G07 | `trade_detail`, Primary Action/Timeline-Helfer | ADAPT | Laufende Karte mit zwei Richtungen und Next Action; Sonderfälle erreichbar |
| G08 | `create_trade_request`, `trade_center`, `render_trade_wall` | ADAPT | Gemeinsamer Multi-Album-Composer; heutiger Single-Album-Webcheck reicht nicht |
| G09 | `album_trades`, albumbezogene Partner-/Coverageanzeigen | ADAPT | Personen einmal, globale Zahlen, Albumfilter als Discoverykontext |
| G10 | TypedNotificationService und sichere Zielauflösung | ADAPT | V1-Anbindung vorhandener Typen, fehlende Ereignisse explizit entscheiden |
| G11 | TradeRatingService/Ratinganzeige | ADAPT | Optionaler Abschlussmoment und spätere Discoverysortierung, C7 schützen |
| G12 | Neue SmartDeal collapsed/expanded + Inline-Erfolg | BUILD | Eigene sichtbare UX auf vorhandenem Core, keine Scoreanzeige |
| G13 | Globales Partnerdetail | BUILD | Beziehung/mehrere Alben/Smart-Vorschlag/Composer an einem Ort |
| G14 | Versandkontakt/Freigabe/optionales Speichern | BUILD | T8a-Privacy-/Speichervertrag; kein vorhandenes Adressmodell behaupten |
| G15 | Empfänger-Tauschpräferenzen | BUILD | Neue fachliche Regel, Poolflag ist kein Ersatz |
| G16 | Atomare neue manuelle Pending-Bindung | BUILD | Cross-Flow-Ressourcenschutz ab Anfrage, Legacy bleibt Legacy |
| G17 | Neue Receipt-ohne-Shipping-Ableitung und Verlustkonflikt | BUILD | Erst C1/C2 klären, keine Reparaturlogik vorwegnehmen |
| G18 | Zwangsdetailseite für normalen SmartDeal/Anfrageerfolg | REMOVE FROM PRIMARY FLOW | Inline; bestehende sichere Deep-Links später abbilden |
| G19 | Gleichwertige Request-/Versand-/Album-Unterseiten als Hauptnavigation | REMOVE FROM PRIMARY FLOW | Zustände in zentralen Einstieg integrieren |
| G20 | Prominente History-/Verwaltungsflächen | REMOVE FROM PRIMARY FLOW | History sekundär ganz unten |

Der reale Tradebereich liegt überwiegend als Python-erzeugtes HTML mit Forms/Redirects in `App/webapp.py`; es gibt keinen hier bereits fertigen neuen SmartDeal-Templatebaum. Bestehende Routen `/trades`, `/trade/<id>`, `/trades/<id>`, Album-Trade-/SmartTrade-Einstiege und Profilarchiv sind IST-Belege, keine automatisch beschlossenen SOLL-URLs. Singular/plural Handleralias kann nur Redirect sein; die CG-1-Cancelroute ist dagegen V1-Withdraw. T9 muss die vollständigen Kanten vor späterem Umbau prüfen.

## 20. Roadmap Mapping

| Block | Zuordnung dieses SOLL | Grenze / Voraussetzung |
| --- | --- | --- |
| SD-T7a | Zwei Versandrichtungen, Ship/Receipt, Abschluss/History/Rating-/Notificationadapter | C2 vor Implementierung schließen; CG-1-Sperren bis Nachweis erhalten |
| SD-T7b | Sichtbar „Sticker nicht auffindbar“, reale Korrekturen und Problemweg | C1/Q1 vor fachlich endgültigem Screenflow; AC26 nicht still überschreiben |
| SD-T8a | Eingabe, konkrete Freigabe, bewusstes Anzeigen, optionales Speichern | Kontrollierter Datenlebenszyklus; kein öffentliches Adressfeld |
| SD-T8b | Chat optional/später | Kein Golden-Path-Pflichtfeature, kein aktueller Auftrag |
| SD-T9 | Zentrale IA, Screens/States, Inline-/Deep-Link-/Rückzielvertrag, vollständiger Routeaudit | Dieses Dokument ist PO-SOLL-Grundlage, keine vollständige T9-Kantenabnahme |
| SD-T10 | Karten, gemeinsame Composeroberfläche, Next Action, Bestätigungen, Microcopy | Erst jeweiliger geschlossener Domain-/Privacyvertrag und gemeinsame Designfreigabe |
| SD-T11 | Reale neue Nutzerwege, manuell/SmartDeal-Konkurrenz, Frist, Rollen, Ship/Receipt, Kontakt, mobile Nutzung und Last | CG-1-1251-Baseline nicht als Beweis dieser neuen Fälle ausgeben |

**Zusätzlichen begrenzten Domainblock empfehlen: JA.** Arbeitsbezeichnung „Manueller Angebotsvertrag V1“, ohne neue Roadmap-ID oder Roadmapänderung. Bündelt gemeinsamen kanonischen Multi-Album-Payload, Empfängerpräferenzen, großzügige Mengenregel, frische atomare Validierung und Binding/Release/Expiry/Retry für neue manuelle Angebote. Wiederverwendung derselben Availability/Reservations, aber keine Umklassifikation in `smartdeal_v1` und keine Änderung alter Legacy-Verträge. Datenmodell erst nach den offenen Verträgen prüfen; keine Migration beschlossen.

Warum separat: Der bestehende Webcheck implementiert einen Teil der Mengenregel, aber nicht den neuen bindenden Lifecycle. Dies in T10 zu verstecken würde Domainentscheidungen in UI-Code verlagern. Ob der empfohlene Block intern in kleine Teilaufträge zerlegt wird, bleibt spätere Planung; kein zweiter Composer. Partnerkontext-Vorschlag C6 als begrenzte fachliche Adapterklärung separat zuordnen, keinen neuen Algorithmus erfinden.

## 21. Contract Conflicts

**Historischer Ausgangsstand: 8 Konflikt-/Vertragslücken C1–C8, produktseitig durch den Night-Prep-Nachtrag aufgelöst.** Nicht jeder Eintrag ist ein Widerspruch: Typ und bestehender Schutz sind jeweils ausgewiesen. Die folgenden Zeilen bleiben als Herkunftsnachweis; ihre frühere Offen-Markierung wird durch den verbindlichen Decision Record ersetzt. Technische Umsetzungslücken bleiben bestehen.

| ID / Typ | Neuer PO-SOLL bleibt | Bestehender Vertrag / Code | Konsequenz |
| --- | --- | --- | --- |
| C1 — direkter Widerspruch | Fehlenden Sticker durch gleichwertiges Entfernen auf Gegenseite ausgleichen | Bible §37.4, §38.4; AC25/26: unveränderliches Paket, vor Versand ganz beenden, keine Reparatur; nach Versand Problemflow | Expliziter PO-Vertragsentscheid nötig, bevor Korrekturflow festgelegt wird; T7b |
| C2 — neuer Lifecycle-Vertrag gegen IST-Guard | Realer Empfang auch ohne Versandklick | Bible §23 physische Wahrheit; `trade_receipt.receive` verlangt Shippingrow/Partnerflag und passende Lifecyclezustände | T7a Ableitung/Autorisierung/ausstehende Ausbuchung/Teilfälle/Retry festlegen; nicht nur Guard entfernen |
| C3 — Präzisierung gegen breiten Altvertrag | Manuell nur G≥E aus Initiatorsicht | Bible §4/27 freie ungleiche Vereinbarung; aktueller `create_trade_request` prüft G≥E bereits im Web, generischer Legacy-Service nicht neuer globaler Vertrag | Neue Domainregel versioniert/abgegrenzt sichern, bestehende Vorgänge nicht rückwirkend ungültig machen |
| C4 — neue Präferenz, kein vorhandener Vertrag | Offen vs nur albumgleich auf Empfängerseite | `AlbumPrivacyService` hat visibility/trade_pool_enabled; AC01/06 globaler SmartDeal über Alben | Reichweite/Wechsel/Default/Abgrenzung klären; keine Umdeutung des Poolflags |
| C5 — anderer Bindungszeitpunkt | Manuelle Angebote ab Anfrage verbindlich geschützt | Manuelles Create speichert ungebundenen Legacy-Request; Reservations erst bei `TradeReservationService.accept`; AC27 schützt Altverträge | Neuer manueller Bindungs-/Releasevertrag, keine pauschale Übernahme von T5a/24h/Quote |
| C6 — Kontext-/Optimierungsvertrag fehlt | Besten Tausch mit genau diesem Partner anzeigen | AC01/12 globales Optimum; T2b isolierte Chancen, T3b validiert vollständigen globalen Input; T4 min5 | Begriff und Größen-/Kontextgrenze klären; lokales Maximum nicht als globales Planpaket ausgeben |
| C7 — möglicherweise engerer UX-Umfang | Optional bewerten nach abgeschlossenem Tausch, später Vertrauen/Sortierung | Ratingservice erlaubt auch Problemabschlüsse; AC17 verbietet Ratinggewicht im SmartDeal-Plan | Problemabschluss-Zugang explizit erhalten/entscheiden; Sortierung nicht still auf Optimierer ausweiten |
| C8 — Ereignis-/Kataloglücke | Anfrage, angenommen/Übereinstimmung, Versand, Empfang, Handlung sichtbar relevant | Typed-Katalog ohne Accept-/Empfangstyp; T6b nur Acceptance-Event, T5a ohne Requestnotification | Sichtbarer In-App-Zustand von neuer Benachrichtigung unterscheiden; Katalogentscheidung und Dedupe-Anbindung später |

**Geprüft und kompatibel, keine künstlichen Zusatzkonflikte:** Striktes SmartDeal-1:1 und getrennte großzügige manuelle Angebote können nebeneinander bestehen. Bewusstes Adressanzeigen plus vorherige konkrete Freigabe passt zu Bible §37.3; Persistenz/Retention fehlt technisch. Versand-Ausbuchung und Empfang-Einbuchung stimmen mit Bible §23 überein, außer der offenen Statusableitung C2. Sekundäre History verlangt keinen History-Rewrite. Optionaler Chat und fehlende Standortpflicht widersprechen keinem gesperrten Pflichtvertrag. Sekundärer Problemzugang erlaubt nicht, notwendige Action-required-Zustände zu verstecken. Kein „verpackt“-Status ist erforderlich.

**Historische 8 PO-Fragen — jetzt Q1–Q8 GESCHLOSSEN gemäß Decision Record:**

| ID | Noch zu schließende Frage | Zuständiger Abschnitt |
| --- | --- | --- |
| Q1 | Soll die neue Korrekturidee den gesperrten V1-Vertrag tatsächlich ersetzen, und welcher neue Zustimmungs-/Vertragsstand wäre dann gewollt? | C1/T7b |
| Q2 | Welche für beide Seiten sichtbare Bedeutung hat Empfang ohne Versandklick, insbesondere bei Teilankunft oder Widerspruch? Die technische einmalige Buchungsableitung folgt in T7a | C2/T7a |
| Q3 | Gilt Empfängerpräferenz global/pro Album, nur manuell oder auch automatisch, welcher Default und welche Wirkung eines Wechsels auf bestehende Angebote? | C4/manueller Domainblock |
| Q4 | Welche Seiten/Needs bindet das neue manuelle Angebot wie lange; welche Rückzugs-, Frist- und Limitregeln gelten? Keine ungefragte SmartDeal-Übernahme | C5/manueller Domainblock |
| Q5 | Bedeutet „bester Tausch mit Partner“ sein Paket im globalen Plan oder ein isoliertes Paaroptimum; was geschieht unter 5↔5? | C6/Partnerdetail |
| Q6 | Soll die optionale Bewertung nach Problemabschluss weiter im neuen Flow erreichbar sein, entsprechend dem bestehenden Ratingvertrag? | C7/T7a,T10 |
| Q7 | Welche genannten Ereignisse brauchen eigenständige Benachrichtigung, welche nur sichtbare Zustandsänderung; wie wird doppelte Meldung bei Übereinstimmung vermieden? | C8/T7a,T10 |
| Q8 | Welche fachliche Menge sortiert Partner bei ungleichen Richtungen und Albumfilter: Paarvolumen, möglicher eigener Eingang oder andere klar benannte Größe? | Partnerliste/T9 |

Nicht als zusätzliche offene Produktentscheidung gezählt: konkrete technische Speicherform, Indizes, Retry-Implementierung und API-Formate; diese sind spätere Technikarbeit innerhalb geschlossener Regeln. Bereits entschiedene optionale Adressspeicherung, kein Chat-Zwang, max5/min5 und absolute V1-Frist werden nicht erneut zur Abstimmung gestellt.

## 22. Open Design Questions

Noch nicht festgelegt: Farben, Radien, exakte Typografie, Icons, Animationen, Abstände, genaue Card-Komposition und endgültiges Button-Wording. Ebenfalls gemeinsam ausarbeiten: Expansion/Collapse-Verhalten, Zugänglichkeit und Fokus, große Stickerpakete ohne fachliche Kürzung, sichtbare Richtungskennzeichnung, kompakte zwei Sendungsbahnen, sichere Adressanzeige, Bestätigungen sowie Empty/Loading/Busy/Stale/Terminaldarstellung.

Arbeitswörter sind keine finalen Texte. „GO“/„Mutual GO“ bleiben technische Begriffe außerhalb der Nutzeroberfläche. „Tausch selbst zusammenstellen“ ist sekundär, Dealgröße dominant. Diese festgehaltenen Prioritäten werden durch spätere Gestaltung nicht umgekehrt. Kein Designpreset aus historischen Templates übernommen.

## 23. PO Decisions Captured

**44/44 Auftragsabschnitte erfasst.** Referenznummern entsprechen exakt der nummerierten PO-Vorlage; sie sind keine neue Produktpriorisierung.

| PO # | Festgehaltener Inhalt | Zielabschnitt |
| --- | --- | --- |
| 1 | Zentraler Einstieg in vierteiliger Reihenfolge | §3 |
| 2 | Handlungsbedarf zuerst, keine leere Box | §4 |
| 3 | Anfragen gemeinsam, Richtung, Aufklappen/Aktionen | §6 |
| 4 | Bis fünf SmartDeals, min5, kein 3+mehr | §5 |
| 5 | Geschlossene Karte Partner/Größe/Alben, technische Details ausblenden | §5 |
| 6 | Inline volle konkrete Leistungen beider Seiten vor Anfrage | §5 |
| 7 | „Tausch anfragen“ Arbeitsbegriff, kein sichtbares GO | §5,22 |
| 8 | Sekundärer manueller Einstieg, gemeinsamer Composer | §5,13 |
| 9 | Inline-Erfolg, 24h/Reservation, Neuberechnung | §5,6 |
| 10 | Gegenseitige Übereinstimmung, positive Darstellung, gleicher Vertrag | §5 |
| 11 | Laufende Trades kompakt/inline im Handlungsbedarf | §7 |
| 12 | Zwei physische Bewegungen, Trackinggefühl, kein Verpackt | §7 |
| 13 | Konkrete Versandaktion statt Verpackungsanweisung | §8 |
| 14 | Adresse erst nach Annahme/Freigabe, bewusst anzeigen | §9 |
| 15 | Adresse optional speichern, dealbezogene Partnerfreigabe | §9 |
| 16 | Kein notwendiger Chat, T8b später optional | §10,20 |
| 17 | Porto/Briefanzahl nicht notwendige sichtbare V1-Komponente | §5 |
| 18 | Versand bestätigt vor tatsächlicher Ausbuchung | §8 |
| 19 | Empfang mit klarer Menge vor Einbuchung | §8 |
| 20 | Empfang ohne Versandklick als PO-Richtung, Ableitung offen | §8,C2 |
| 21 | Nicht auffindbar sichtbar; Korrekturidee erhalten, Konflikt markiert | §8,C1 |
| 22 | Allgemeine Probleme sekundär, notwendige Handlung sichtbar | §4,8 |
| 23 | Abschluss nach beiden Empfängen, positiver Moment/History | §10 |
| 24 | Optionale Sterne/Später, keine Pflichtrezension, Vertrauen | §10,C7 |
| 25 | Relevante Ereignisse, keine Flut/neue Typen ohne Entscheid | §10,C8 |
| 26 | Vergangene Tausche unten sekundär | §15 |
| 27 | Menschenbezogene Partnerliste, Albumfilter findet Personen | §11 |
| 28 | Partnerdaten/Need-Supply-Zahlen, kein finales ↔-Wording | §11 |
| 29 | Eigene Partnerdetailansicht, Inhalte soweit sichtbar | §12 |
| 30 | Partnerbezogener Smart-Vorschlag unter Domainvorbehalt | §12,C6 |
| 31 | Derselbe manuelle Composer im Partnerdetail | §13 |
| 32 | Empfängerpräferenzen offen/albumgleich, bestehendes Poolmodell prüfen | §14,C4 |
| 33 | Manuell nur großzügig G≥E, spätere Domainregel | §13,C3 |
| 34 | Manuelle Anfrage bindet gegen alle parallelen Wege | §13,C5 |
| 35 | Größere Chance zuerst, spätere Sortierungen optional | §11,Q8 |
| 36 | Keine Standortpflicht, Entfernung später | §11 |
| 37 | QR vor Ort als Future Contract, gebundene Mengen ausschließen | §16 |
| 38 | Zentrale Seite/inline/Partnerdetail/sekundäre History | §2,17 |
| 39 | Screenbaum und laufende Zustände | §17 |
| 40 | Action-/State-Matrix mit Actor/Service/Effekten/Status | §18 |
| 41 | KEEP/ADAPT/BUILD/REMOVE-Einordnung | §19 |
| 42 | Roadmap und empfohlener manueller Domainblock | §20 |
| 43 | Konflikte und echte offene Fragen explizit | §21 |
| 44 | Visuelle/Microcopyentscheidungen offen lassen | §22 |

## Night-Prep: verbindlicher Closure-Status

Alle Q1–Q8 und die zugehörigen fachlichen C1–C8 sind gemäß [Decision Record](TRADE_UX_PO_DECISIONS_Q1_Q8.md) geschlossen. Die frühere Matrix und der Screenbaum sind mit folgenden gezielten Auflösungen zu lesen:

- A13/U14: Vorversand-Unfulfillable vollständig beenden statt reparieren; nach Versand Problemweg.
- A12: Empfang ohne vorigen Versandklick muss T7a zulassen, ohne erfundene Versandzeit und mit genau einmaliger Buchung.
- A17/U16: Neuer manueller Vertrag bindet beide Seiten ab Submit für absolute 24h; keine manuelle Quote erfunden.
- A18/S2: Isoliertes Paaroptimum, auch unter 5↔5 anzeigen; globaler Topplan unverändert.
- A15: Bewertung auch nach qualifiziertem Problemabschluss nach bestehendem Service.
- Benachrichtigungen: Anfrage, Tausch steht, Versand, Problemhandlung eigenständig; Empfang nur Status ohne neuen Notification-Zwang.
- Partnerliste: gesamtes zulässiges Paarvolumen DESC, auch nach Albumfilter; Filter bestimmt nur Personen mit Chance im Album.

Die Zählung 3 Screen-Kontexte / 16 Hauptzustände / 20 Aktionen und die ursprüngliche 44-Punkte-Abdeckung bleibt bestehen. Frühere Formulierungen „offen“, „noch zu schließen“ oder „vor Q-Klärung“ beziehen sich auf den damaligen Stand; keine erneute PO-Abstimmung über bereits entschiedene Q1–Q8. Der technische Manual-/T7-/T8-/T9-Nachweis folgt gesondert und ist nicht durch diesen Dokumentnachtrag implementiert.

## 24. Recommendation for Design Phase

Mit S1 Tauschen und der SmartDeal-Karte beginnen: Hier sind Reihenfolge, Paketinhalt, Anfrage-/Bindungs- und gegenseitige Annahmesemantik entschieden. Danach gemeinsamer Anfragebereich und kompakter laufender Trade mit zwei physischen Richtungen. Keine historische Zwangsdetailnavigation als unveränderliche Vorgabe behandeln.

Q1–Q8 sind nun geschlossen; die betroffenen Screens auf deren verbindlicher Grundlage ausarbeiten. Noch fehlende technische Adapter und eigenständige neue Kontaktfragen getrennt behandeln. Unstrittige Screens können parallel fachlich konkretisiert werden, ohne diese Konflikte durch Design zu entscheiden. Adressansicht gemeinsam mit T8a-Berechtigungs-/Datenlebenszyklus ausarbeiten.

Dieses Dokument bestätigt keine neue Implementierung und bewertet die gesperrten Coreblöcke nicht rückwirkend um. Es macht neue PO-Richtungen und ihre Vertragsfolgen reviewbar. Ausschließlich `docs/TRADE_UX_SOLL_V1.md` neu; Runtime, Templates, CSS/JS, Routes, DB, Migrationen, Tests, bestehende Bible/Algorithm Contract/Roadmap und Auditberichte bleiben unverändert. Keine Tests nötig oder ausgeführt. Abschlussprüfung: auftragsbezogener Dateihashvergleich gegen `/private/tmp/trade-ux-before.json`, `git status --short`, `git diff --stat`, `git diff --check` plus Whitespacecheck der neuen untracked Datei. Kein git add, Commit, Push oder Deploy. Danach STOP.
