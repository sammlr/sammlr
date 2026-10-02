# Manual Offer Domain Contract V1

Stand 2026-09-12. Phase B des Night Prep Package, **Spezifikation ohne Implementierung**. Grundlage: [PO Decisions Q1–Q8](TRADE_UX_PO_DECISIONS_Q1_Q8.md), [Trade UX SOLL](TRADE_UX_SOLL_V1.md), bestehende Availability-/Privacy-/Lifecycleverträge. Kein UI-, Schema- oder Runtimeauftrag.

## 1. Abgrenzung und Inputs

Ein neues manuelles Angebot ist ein eigener Vertrag, weder SmartDeal V1 noch automatisch Legacy noch ein editierter SmartDeal. Historische und laufende alte Requests behalten Klassifikation, Fristen, Reservierungszeitpunkt und Abschlusssemantik. Keine Umklassifikation bestehender Zeilen.

Inputs: authentifizierter Initiator U, anderer Empfänger V, vollständige gerichtete Leistungen U→V und V→U mit kanonischem `(album_id, sticker_code, quantity)`, aktuelle kanonische Supply/Needs beider Nutzer, aktuelle Eligibility/Albumfreigaben/Blocks/Accountzustände, globale aktuelle Empfängerpräferenz sowie vertrauenswürdiger Auswertungszeitpunkt. Clientmengen sind beantragte Leistungen, keine Availability-Wahrheit. Aliasauflösung an der kanonischen Quelle, kein UI-eigener Bestandsrechner.

Mengen sind positive ganze Zahlen, keine Bool/Float/Negativwerte; äquivalente doppelte Zeilen vor Prüfung kanonisch aggregieren. Supply und tatsächlicher Empfängerbedarf begrenzen jede Leistung. Keine neue Mehrfachbedarfsfunktion wird eingeführt; das vorhandene Needmodell ist maßgeblich. Mehrere freie Geberkopien dürfen nicht als mehrere erfüllbare identische Empfängerlücken ausgegeben werden.

## 2. Draft

Frei editierbar innerhalb des jeweils angezeigten Availability-/Preference-Rahmens. Keine Reservation, keine Requestanlage erforderlich, keine 24h-Frist. Ein alter Draft ist keine Zusicherung aktueller Ausführbarkeit. Bei neuem Read und spätestens Submit aktuelle Empfängerpräferenz prüfen. Kein verpflichtendes Speichern von Entwürfen durch diese Spezifikation.

Ein gemeinsamer Composer liefert denselben Domaininput, unabhängig davon, ob der Nutzer über SmartDeal oder Partnerdetail kam. Herkunft ist Navigationskontext, keine abweichende Vertragsregel.

## 3. Mengen und Präferenzen

Sei `g_a` die Gesamtmenge U→V im Album a, `r_a` die Gesamtmenge V→U. `G=Σg_a`, `R=Σr_a`. Immer `G>=R`, `G>=1`, `R>=1`. Keine künstliche Mindestgröße fünf und keine künstliche Deal-Maximalgröße aus SmartDeal ableiten.

OPEN: nur globale Mengenbedingung, beliebige zulässige Albumkombination. SAME_ALBUM_ONLY: zusätzlich **für jedes Album a: `r_a<=g_a`**. Dies ist die im Auftrag vorgegebene Semantik, keine alternative Pairingregel. Sie impliziert globale Großzügigkeit, die trotzdem als allgemeine Invariante bestehen bleibt. Es ist keine Eins-zu-eins-Zuordnung physischer Einzelstücke erforderlich.

| Beispiel | OPEN | SAME_ALBUM_ONLY |
| --- | --- | --- |
| Gleiches Album 10 geben /10 erhalten | erlaubt | erlaubt |
| Gleiches Album 10/8 | erlaubt | erlaubt |
| Gleiches Album 8/10 | verboten | verboten |
| WM26 5/4 und EM04 0/3 | verboten, auch global 5<7 | verboten, EM04 verletzt |
| WM26 10/0 und EM04 0/8 | erlaubt | verboten |
| WM26 5/4 und EM04 4/3 | erlaubt | erlaubt |
| Nur geben, kein Eingang | verboten | verboten |

Die Nutzerpräferenz ist global pro Empfänger, OPEN Default. Sie betrifft nur neu erzeugte manuelle Angebote. `trade_pool_enabled` und allgemeine Privacy behalten ihre unabhängige Bedeutung. Keine neue Beschränkung des SmartDeal-Algorithmus. Bei Submit geltende Präferenz ist Bestandteil des geprüften Vertragsstands; Wechsel nach verbindlichem Submit entwertet den bestehenden Vertrag nicht. Keine nachträgliche Präferenz-Revalidation beim Accept, die eingefrorene Angebote allein deswegen ungültig macht; aktuelle tatsächliche Eligibility/Deckung weiterhin prüfen.

## 4. Submit und Frozen Package

Server muss vor Bindung einen aktuellen konsistenten Zustand unter einer atomaren Schreibgrenze prüfen: Teilnehmer/Autorisierung, Katalogidentitäten, beide Supply-/Need-Seiten, aktuelle Empfängerpräferenz, G>=R und beidseitig positive Menge. Eine reine frühere Read-Validation erteilt keine Schreibberechtigung.

Bei Erfolg gemeinsam persistieren: eigene Vertragsart, Teilnehmer und Initiatorrolle, vollständige unveränderliche Multi-Album-Positionen, geprüfter Präferenzstand, Pending-Status, eindeutige Instanz-/Retry-Zuordnung, einmaliger Bindungszeitpunkt und alle beidseitigen Reservationen. Zugehörige Incoming Needs werden aus denselben bindenden Fakten wirksam. Kein äußerlich gültiger Request ohne vollständige Bindung, keine Teilseite, keine Inventorybuchung. Scheitern irgendeiner Seite oder des Commits: gesamter Übergang zurückrollen.

Keine automatische Paketersetzung oder -kürzung bei stale. Ein neuer manueller Draft kann separat entstehen; bestehende Verträge werden dadurch nicht bearbeitet. Der permanente Vertrag benötigt vollständige Positionswahrheit, keinen verlustbehafteten Single-Album-JSON-Fallback.

## 5. Zeit und Zustandsautomat

Draft → Submit → Pending/Bound → Accept → Accepted/Bound → später T7a-Lifecycle.

Pending alternativ → Declined / Withdrawn / Expired, jeweils vollständige beidseitige Freigabe. Keine Kette dieser terminalen Zustände. Rollen: Empfänger nimmt an/lehnt ab; Initiator zieht zurück; fällige Expiry durch vertrauenswürdigen Runtime-/Maintenancepfad. Dritte dürfen keine dieser Mutationen auslösen.

Frist `binding_created_at + 24h`, absolute Dauer. Vor Frist gültig, exakt ab Frist nicht mehr annehmbar. Kein Kalender-/DST-/Mitternachtsmodell. Bindungszeit einmalig; Retry setzt sie nicht zurück. Accepted hat eigene stabile Annahmezeit; Pending-Expiry gibt Accepted nicht frei. Physisches Inventory bleibt in allen diesen Übergängen unverändert.

Kein manuelles Anfrage-Limit wird spezifiziert. Die SmartDeal-Quote drei gilt nicht automatisch. Technischer Missbrauchsschutz darf später nicht still als neue fachliche manuelle Quote implementiert werden.

## 6. Accept, Release und physischer Anschluss

Accept übernimmt die vollständigen bestehenden eigenen Bindungen, reserviert nicht noch einmal und behandelt sie nicht als fremden Konflikt. Fremde Zusagen und aktuelle reale Deckung/Needs bleiben geschützt. Kein Akzeptieren einer abgelaufenen oder bereits terminalen Instanz; eingefrorene Leistungen und Bindungszeit bleiben erhalten. Status, Annahmezeit und erforderliche deduplizierbare Fakten bilden eine atomare Einheit.

Decline/Withdraw/Expiry geben beide Supplies und zugehörige Incoming-Zusagen vollständig frei, ohne fremde gültige Bindungen zu lösen. Physisch inzwischen erfüllter Need wird dadurch nicht wieder künstlich fehlend. Wiederholung bestätigt nur einen tatsächlich vollständig terminalen Zustand, keine halbe Freigabe als erfolgreichen NOOP ausgeben.

Nach Accept soll derselbe später durch T7a vereinheitlichte physische Versand-/Empfangslifecycle gelten: einmalige Ausbuchung bei Versand beziehungsweise korrekter nachgewiesener physischen Ableitung, einmaliger echter Eingang, Transit kein Besitz, kein Abschluss allein durch Versandflags. Kein neuer Reparaturpfad, kein vorgezogener T7a/T7b-Adapter.

## 7. Cross-Flow und Privacy

Eine gemeinsame kanonische Availability für SmartDeal, neue manuelle Angebote, Legacy mit tatsächlichen Bindungen und künftigen QR-Personaltausch. Dieselbe gebundene Kopie darf nicht nochmals frei erscheinen, derselbe gebundene Need nicht nochmals zugesagt werden. Neue manuelle Vertragsart muss ausdrücklich in den Bindungsreader integriert werden; ein unbekannter Typ darf nicht durch Legacy-Fallback geraten werden.

Aktuelle Trade-Eligibility ist nicht gleich öffentliche Profil-/Albumansicht. Blocks/Account-/Poolregeln beider Seiten prüfen, keine Standortpflicht. Adressen erst über den separat bestätigten T8a-Kontaktvertrag, nicht im Draft oder offenen Angebot. Der künftige QR-Weg nutzt dieselben freien Mengen und atomare Konkurrenzprüfung, erhält hier aber keine neue Buchungs-/Scan-API.

## 8. Idempotenz und Races

Technische Empfehlung: langlebiger Command-/Retry-Schlüssel gebunden an Actor, Vertragsart und vollständigen Payload. Gleiches Command plus gleicher Inhalt liefert dieselbe Instanz und stabile Zeiten; gleicher Schlüssel mit anderem Inhalt scheitert. Paketgleichheit allein ist keine dauerhafte globale Einmaligkeitsregel; nach beendetem Vorgang darf ein neues Command denselben Inhalt erneut anfragen, wenn er verfügbar ist.

Diese technische Retry-Empfehlung beschließt kein automatisches Mutual Accept für manuelle Angebote. Die vorhandene T6b-Regel ist SmartDeal-spezifisch; in diesem Vertrag bleibt explizites Empfänger-Accept maßgeblich. Ein unabhängiges neues Gegenangebot muss normale freie Supply/Need-Prüfung bestehen und kann nicht die Bindung des ersten umgehen.

Spätere Nachweise: identischer Doppelsubmit, konkurrierende Kopie, konkurrierender Need bei zusätzlicher Geberkopie, SmartDeal vs manuell in beiden Lock-Reihenfolgen, später QR vs gebundenes Angebot, Submit vs Preferencewechsel, Accept vs Expiry/Decline/Withdraw, Release vs Neubindung, Commit-/zweite-Seite-/Notificationfehler. Deterministische Barrier/Lock-Synchronisierung, vollständige DB-Reopen-Vergleiche, keine Sleeps als Sicherheitsbeweis.

Preferencewechsel und Submit serialisieren: Wer vor verbindlichem Submit wirksam wird, bestimmt dessen geprüften Stand; danach bleibt der Stand eingefroren. Kein globaler Optimierer unter dem Submit-Schreiblock nötig.

## 9. Notifications

Neue Anfrage und erfolgreiche Annahme benötigen die nach Q7 entschiedenen deduplizierbaren Benachrichtigungen. Existierende Anfrage-/Decline-/Shipping-/Problemtypen wiederverwenden soweit passend; neuer fachlicher „Tausch steht“-Typ später katalogkonform anbinden. Kein eigener Notification-Zwang für Expiry, Receipt, Neuberechnung oder abgegebene Bewertung. Dieses Dokument ändert keinen Katalog und legt keinen neuen Transport oder Queue fest.

## 10. IST-Audit

| Bereich / konkrete Quelle | Kategorie | Befund |
| --- | --- | --- |
| InventoryRead/Availability/Reservations | KEEP | Eine gemeinsame Mengenwahrheit, Eigenexemplar und atomare Reservationsbausteine |
| Privacy-/Community-/Accountgates | KEEP | Unabhängige Pool-/Sichtbarkeits- und Rollenregeln |
| `webapp.create_trade_request` | LEGACY ONLY | Prüft G>=R, nichtleere Seiten und aktuelle erlaubte Mengen, schreibt aber Single-Album-Codelisten und ungebundenen offenen Legacy-Request |
| `trade_center`, `render_trade_wall` | ADAPT | Auswahl-/Darstellungsbausteine, noch kein neuer gemeinsamer globaler Composer-Domainvertrag |
| `TradeReservationService.accept` | LEGACY ONLY | Reservation erst bei alter Annahme; nicht für neue bereits gebundene manuelle Requests blind wiederverwenden |
| `trade_positions` und Mengenreservationen | ADAPT | Multi-Album-Speichergrundlage brauchbar; neue Contract-Klassifikation/Need-Projektion prüfen |
| Shipping/Receipt/History/Rating | ADAPT | Gemeinsame positionsbasierte Basis, T7a muss beide neuen Vertragsarten explizit anbinden |
| TypedNotificationService | ADAPT | Anfrage/Decline vorhanden; neue Vertragsart und gemeinsame Annahmebotschaft dedupliziert anbinden |
| Globales Empfängerpräferenzmodell | BUILD | OPEN/SAME_ALBUM_ONLY plus geprüfter Stand je verbindlichem Angebot fehlen |
| Neuer atomarer Submit/Accept/Release-/Expiryadapter | BUILD | Eigenständige Semantik statt Copy/Paste oder SmartDeal-Umetikettierung |

## 11. Technische Empfehlung

**Neuer Contract-Type: JA**, beispielsweise `manual_offer_v1` als technischer Namensvorschlag, noch keine implementierte Konstante. Die aktuelle V21-Klassifikation akzeptiert nur legacy/smartdeal_v1; Migration 0021 sowie Validatoren/Reader dürfen nicht durch einen ungeprüften dritten String umgangen werden.

**Neue Persistenz voraussichtlich erforderlich: JA; Migration MÖGLICH beziehungsweise zu erwarten**, genauer Umfang erst nach Schemaentwurf. Mindestens Nutzerpräferenz, eindeutige neue Vertragsklassifikation und nachvollziehbarer eingefrorener Prüf-/Retryzustand müssen dauerhaft darstellbar sein. Vorhandene Request-/Positions-/Reservations-/Zeitspalten können teilweise wiederverwendet werden; eine komplett zweite Trade-/Inventorydatenbank ist nicht erforderlich. CHECKs/Trigger/Downmigration und Legacybackout gesondert prüfen; keine Migration in diesem Auftrag.

Reuse: kanonische Inventory-/Eligibilityreader, Positions-/Reservationsprinzip, zentrale absolute Zeitberechnung, atomare Transaktions-/Freigabeinvarianten, vorhandene spätere T7a-Buchung und Typed-Notification-Infrastruktur. T5a/T6b sind nicht automatisch generische manuelle APIs; deren 1:1/min5/Quote/Identity dürfen nicht für diesen Vertrag abgeschwächt werden.

## 12. Phase-B-Abschluss

B1–B12 abgedeckt. **Verbleibende echte Open Product Questions in diesem Manual Contract: 0.** Die empfohlene SAME_ALBUM_ONLY-Semantik ist im Auftrag ausreichend vorgegeben. Konkrete Tabellen, technische Namenswahl und Dedupe-Implementierung sind spätere technische Entscheidungen, kein Anlass für eine zusätzliche Produktfrage.

Keine Implementierung, keine Tests oder Migrationen. Geschützte Legacy-/SmartDeal-Verträge bleiben erhalten. Phase C kann mit den nun geschlossenen Grundlagen beginnen.
