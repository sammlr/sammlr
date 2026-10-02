# TRADE-00 — Sammlr Trade Product Contract V2

Status: beschlossener zukünftiger Produktvertrag; ausschließlich Dokumentation. Stand: 2026-09-30.

## 1. Zielbild und Geltungsbereich

Sammlr ist eine Sticker-Tauschbörse. Fertige Top-Tauschvorschläge erleichtern den Einstieg; der vollständige kompatible Partnerpool bleibt zugänglich. Bei einem konkreten Partner kann Sammlr einen SmartDeal bilden oder der Nutzer selbst Sticker auswählen. Alle neuen Wege führen in denselben zukünftigen Trade-Lifecycle.

Dieser Vertrag ändert weder Runtime noch Datenbank. Bestehende Legacy- und SmartDeal-V1-Vorgänge behalten ihren bisherigen Vertrag. Keine rückwirkende Migration, keine Uminterpretation bestehender Snapshots oder Zustände. Die hier beschriebenen Änderungen gelten erst für den zukünftigen, ausdrücklich abgegrenzten neuen Trade-Vertrag. Dessen technische Repräsentation ist noch offen.

## 2. Begriffe

| Begriff | Bedeutung |
| --- | --- |
| Top-Tauschvorschlag | Fertiger algorithmischer Deal aus der bestehenden globalen Planung; ungebundene Empfehlung. |
| Alle Tauschpartner | Vollständiger zugelassener kompatibler Matchpool, nicht auf die Top 5 beschränkt. |
| Partner-SmartDeal | Algorithmisch erstellter konkreter Vorschlag für genau einen gewählten Partner. |
| Selbst auswählen | Manueller Builder mit den bestehenden Regeln des neuen Manual-Offer-Vertrags. |
| Herkunft | Beispielsweise `TOP_SUGGESTION`, `SMARTDEAL`, `MANUAL`; Provenienz, kein Ersatz für Domainvertrag oder Validierung. |
| Snapshot | Exakte vereinbarte Sticker und Mengen beider Richtungen. |
| Request-State | Zustand der Anfrage, etwa offen, angenommen, abgelehnt oder abgelaufen. |
| Operativer Slot | Eigene noch abzuarbeitende Verpflichtung im eingehenden oder ausgehenden Kontingent. |
| Physische Richtung | Versand und Empfang einer konkreten Sendung, unabhängig von der Gegenrichtung. |

Herkunft, persistierter Contract-Type, Anfragezustand, physischer Zustand und Kapazität bleiben getrennte Konzepte. Die genannten Begriffe schreiben noch keine DB-Enums vor.

## 3. Deine Top-Tauschvorschläge

Standardmäßig werden fünf fertige Deals angeboten; fachlich bleibt das bestehende Maximum von fünf mit **0 bis 5 tatsächlich gültigen Vorschlägen** erhalten. Fehlende Kandidaten werden nicht künstlich aufgefüllt. Keine Pax-Verpackung, kein „Pax öffnen“, keine Booster- oder Aufreißinszenierung.

Der kanonische Stickerstapel ist die zentrale Darstellung des konkreten Deals, beispielsweise mit Partnername, `23 ↔ 23` und sechs beteiligten Alben. Noch keine endgültige Card- oder Tabellenkomposition festlegen.

Ablauf: Top-Stapel antippen → kompakte Detail-/Auffächeransicht → „Du bekommst“ als Albumstapel und „Du gibst ab“ als Packzettel/Post-its prüfen → Tausch anfragen. Der Deal ist bereits berechnet. Kein vorgeschalteter SmartDeal-versus-manuell-Schritt, kein Builder innerhalb dieses schnellen Flows. Manuelles Tauschen mit demselben Partner führt über Alle Tauschpartner → Partner → Selbst auswählen.

Discovery belegt weder Slots noch Reservierungen. Die Top 5 sperren oder verstecken keinen sonstigen Partner. Erst die tatsächliche Anfrage unterliegt aktueller atomarer Validierung und Bindung.

## 4. Alle Tauschpartner

Unter den Empfehlungen ist „Alle Tauschpartner anzeigen“ erreichbar. Der Bereich umfasst alle nach den bestehenden Zugriffs-, Datenschutz- und Matchingregeln zulässigen kompatiblen Partner. „Vollständig“ erlaubt keine Umgehung dieser Regeln.

Standardranking: größtmögliches sinnvolles bilaterales Tauschpotential absteigend. Nach Q8 ist das isolierte, bedarfsbegrenzte Paarpotential maßgeblich, nicht der Anteil eines Partners am globalen Top-Plan. Fachlich gilt das Minimum der beiden richtungsbezogenen verfügbaren Matchmengen. Gleichstandsregeln dürfen später deterministisch ergänzt werden, ohne den SmartDeal-Optimizer umzuschreiben.

Vorgesehene Informationen: Nutzer, größtmöglicher Tausch, relevante Missing in seinem Bestand, von ihm benötigte eigene Doppelte, gemeinsame relevante Alben und gegebenenfalls Gesamtzahl seiner Doppelten. Sichtbarkeit bleibt berechtigungsabhängig; kein Anspruch auf Offenlegung privater Gesamtbestände.

Erweiterbar für Album, Potential, Missing, passende Doppelte, Gesamtduplikate und weitere Sammlerparameter. Entfernung nur bei später ausdrücklich datenschutzkonform verfügbarer Grundlage. „1:1 innerhalb desselben Albums“ ist eine mögliche spätere Filterfunktion, keine jetzt beschlossene neue Dealregel. Der bisherige Albumfilter findet Personen; er beschränkt nicht still den Deal auf das gewählte Album.

## 5. Partneransicht

Die Ansicht zeigt beide Matchrichtungen und gemeinsame relevante Alben. Zwei Wege stehen zur Verfügung:

- **SmartDeal:** bestehende algorithmische Regeln bilden einen konkreten Deal mit genau diesem Partner.
- **Selbst auswählen:** Nutzer wählt Receive- und Give-Sticker selbst.

Paarpotential ist noch kein fertiger Snapshot und keine Reservierung. Auch ein Paar unter fünf Stickern darf als Potential sichtbar sein; daraus folgt keine Freigabe eines automatischen SmartDeals unter dem bestehenden Minimum.

## 6. SmartDeal und Algorithmus

Der [SmartDeal Algorithm Contract V1](SMARTDEAL_ALGORITHM_CONTRACT_V1.md) bleibt die Grundlage. Keine neue Heuristik, keine neuen Gewichte, kein zufälliges Abschneiden von Stickerlisten.

Erhalten bleiben insbesondere:

- kanonische verfügbare Supply, geschütztes Eigenexemplar, Bedarf von höchstens einem Exemplar je fehlendem Sticker und Berücksichtigung verbindlich eingehender Sticker einschließlich Transit;
- bestehende Partner-/Albumzulässigkeit und Schutz bereits gültiger Bindungen;
- initial exakt 1:1, mindestens fünf Sticker pro automatischem Deal, kein neu eingeführtes Maximum;
- global zulässige Planung mit höchstens fünf Deals und einem Deal je Partner; keine doppelte Verplanung von Supply oder Need;
- bestehende Zielfunktion `E = G − 2n` und Comparator: E, G, absteigender Dealgrößenvektor, numerische Partner-IDs, kanonische Stückreihenfolge gemäß AC11–14;
- frische atomare Validierung beim Anfragen, exakte Identität, Idempotenz und unveränderlicher vereinbarter Snapshot. Ein bloßer Rangverlust aus den Top 5 macht einen weiterhin fachlich gültigen Vorschlag nicht ungültig.

Der globale Top-Plan ist nicht identisch mit der isolierten Paaroptimierung. Für den Partner-SmartDeal ist später der bestehende Algorithmus gezielt auf das konkrete Paar zu adaptieren. Das Beispiel 84 relevante Sticker gegen 37 beschreibt Inputpotential, keine neue Auswahlregel. `smartdeal_pairwise.py` liefert heute Paarpotential; es ersetzt keinen fertigen Proposal-Generator. Das Minimum von fünf gilt weiter. Eine Absenkung erfordert einen gesonderten PO-Entscheid.

## 7. Manueller Trade

[Manual Offer Domain Contract V1](MANUAL_OFFER_DOMAIN_CONTRACT_V1.md) bleibt für die Erstellung maßgeblich: freie konkrete Auswahl über zulässige Alben, positive ganzzahlige Stückmengen, verfügbare Supply und tatsächlicher Bedarf. Aus Initiatorsicht gilt `Give >= Receive`, beide mindestens eins. Das SmartDeal-Minimum fünf wird nicht auf manuelle Angebote übertragen.

Entwürfe sind ungebunden; Submit friert das Angebot ein und bindet beide Richtungen atomar. Die Empfängerpräferenz `OPEN` beziehungsweise `SAME_ALBUM_ONLY` gilt im dort festgelegten Scope. Letztere bedeutet pro Album `Receive <= Give`, nicht automatisch striktes 1:1. Sie wird nicht zum globalen SmartDeal-Filter. Die beim Submit gültige Präferenz wird eingefroren.

Manuelle Angebote brauchen ausdrückliche Annahme. SmartDeal-Mutual-GO wird nicht pauschal auf manuelle Angebote übertragen. Nach Bindung/Annahme nutzen alle neuen Herkunftswege dieselben Pack-, Versand-, Empfangs- und Problemmechanismen. Die frühere Ausnahme manueller Angebote von der Kapazität entfällt ausschließlich im zukünftigen neuen Zweig.

## 8. Gemeinsamer Lifecycle

Fachliche Stationen: Draft/Proposal → Requested → Accepted → Packing → Ready to ship → richtungsbezogener Versand → beide versendet → Empfang → Abschluss. Problem/Resolution ist ein bei Bedarf erreichbarer Zweig, keine verpflichtende Station nach Empfang. Ablehnung, Rückruf und Ablauf sind zusätzliche zulässige Anfrageausgänge. Die exakten Zustandsnamen und Übergangsbedingungen sind vor Integration mit bestehender Domainlogik abzugleichen.

Annahme ist keine Versandbestätigung. Beide versendet bedeutet unterwegs, nicht empfangen oder abgeschlossen. Packfortschritt ist keine Inventarbuchung. Portalöffnung, Versandartauswahl oder Adressanzeige lösen keinen Versand aus. Eigener Versand ist bewusst, autorisiert, atomar und idempotent; die Gegenrichtung bleibt unabhängig.

PAX-05/06 liefern die Interaktionsreferenz für Anfrage, Warten, gespiegelten Snapshot, Annahme/Ablehnung, Packliste, Fortschritt, Fehlmengenweg, bewusste Packfreigabe und getrennte Versandrichtungen. Die Referenz ist kein produktiver Mehrbenutzer-State und keine zweite Versandmaschine.

Adressanzeige erfordert zusätzlich zum angenommenen Trade die eigene vollständige Packliste, bewusste Packfreigabe und Freigabe durch den Adressinhaber. Packen ersetzt keine Eigentümerzustimmung. Zugriff bleibt auf autorisierte Teilnehmer des konkreten Trades begrenzt; Datenschutz- und Aufbewahrungsregeln werden nicht durch Demo-Adressen definiert.

Q2 bleibt erhalten: Tatsächlicher Empfang kann trotz fehlendem Versandklick der Gegenseite relevant sein. Keine erfundene historische Versandzeit, keine Doppelbuchung. Die dafür vorgesehene Domainanbindung muss vor produktiver Freigabe gelöst sein; vorhandene Schutzprüfungen werden nicht einfach entfernt. Bewertungsberechtigung gemäß Q6 bleibt einschließlich qualifizierter Problemlösungen erhalten.

## 9. Gemeinsame operative Kapazität 3/3

Alle neuen Herkunftswege teilen maximal **drei ausgehende und drei eingehende operative Slots** pro Nutzer. Keine separaten Pax-, SmartDeal- oder Manual-Kontingente. Ausgehend/eingehend richtet sich nach der Rolle in der Anfrage, nicht nach der Tatsache, dass bei jedem Tausch beide Personen etwas versenden.

| Ereignis | Operative Wirkung |
| --- | --- |
| Discovery oder Entwurf | Kein Slot. |
| Tatsächliche zulässige Anfrage | Ausgehender Slot beim Initiator, eingehender beim Empfänger; gemeinsame Kapazitätsprüfung. |
| Annahme, Packen, Packfreigabe | Eigener Slot bleibt belegt. Annahme ermöglicht keine unbegrenzten Folgeanfragen. |
| Eigene bestätigte Sendung | Nur der eigene entsprechende Slot wird frei, unabhängig vom Partner-Versand. |
| Partner versendet, eigener Teil offen | Eigener Slot bleibt belegt. |
| Ablehnung, Withdraw, Expiry oder vollständiges Beenden vor Versand | Betroffene Verpflichtungen/Slots werden frei. |
| Beide versendet | Keine operativen Slots mehr für diesen Trade; Empfang/Problem/Abschluss können noch offen sein. |

Dies ist **keine neue Bedeutung von „open request count“**. Ein angenommener Request kann noch Kapazität belegen, ein weiterhin aktiver unterwegs befindlicher Trade dagegen nicht. Technische Speicherung/Ableitung ist offen. Supply-, Reservation- und Incoming-Regeln bleiben unabhängig wirksam; Slotfreigabe erlaubt keine Mehrfachverplanung und macht Transit nicht zu physischem Bestand.

## 10. Snapshot, Fehlmengen und Fristen

Die durch PAX-00 autorisierte Weiterentwicklung von Q1/AC25/26 bleibt für den zukünftigen neuen Trade-Zweig erhalten: expliziter Pre-Shipment-Amendment-Flow statt stiller Reparatur. Nutzer meldet tatsächlich nicht verfügbare vereinbarte Give-Sticker; der Partner sieht exakt, was fehlt, und kann mit reduzierter Gegenleistung fortsetzen, die Tauschgröße symmetrisch anpassen oder den Trade beenden.

Bei Größenanpassung wird das exakte neue Paket vor Bindung sichtbar. Kein Zufall, keine stille SmartDeal-Neuberechnung. Der alte Snapshot bleibt verbindlich, bis die erforderlichen Parteien die konkrete Änderung bestätigt haben. Bereits physisch versendete Richtungen dürfen nicht rückwirkend verändert werden. Zustimmungen, atomarer Austausch von Bindungen und Regeln bei teilweise versendeten Trades bleiben vor Implementierung exakt zu definieren. Der initiale automatische 1:1-Vertrag ist keine Erlaubnis zur stillen späteren Anpassung.

**AC23 wird nicht superseded:** `binding_created_at + 24 Stunden` als absolute Frist gilt vorläufig weiter; Retry verlängert sie nicht. Angenommene Vorgänge verfallen nicht einfach als offene Anfrage. **PO review before productive Pax integration** bleibt der ursprüngliche Review-Marker; er gilt nun entsprechend vor produktiver Integration des neuen gemeinsamen Trade-Zweigs. Verfall, Withdraw/Rückruf, Reminder und Timeout-Verhalten werden gemeinsam geprüft. Bis zu einer ausdrücklichen Änderung bleibt die Frist gültig.

## 11. Kanonische Sticker und Pax-Beziehung

Produktive Stickerwall: bestehende Dimensionen, Frontkarte, Faces, Layer-Richtung, −2/−2 px und z-index-Regeln; Cap fünf. Trade/Receive: exakt dieselbe Geometrie, ausschließlich Kontext-Cap zehn. Oberhalb zehn sichtbarer Lagen kein weiteres geometrisches Wachstum. Keine Mengen-Skalierung, dritte Stackvariante, seitliche Extrusion, alternative Perspektive oder zusätzliche Stack-CSS-Kopie.

Langfristig wird eine kanonische Quelle wiederverwendet. Die tatsächliche Auslagerung und Absicherung erfolgt erst nach Fertigstellung des Trade-Lifecycles; TRADE-00 verändert keine Komponenten.

> SammlrPax ist kein Bestandteil des aktuellen primären Trade-Modells.
> Der bestehende isolierte Prototyp bleibt archiviert und kann zukünftig für
> andere Produktmechaniken wiederverwendet werden.

„Archiviert“ ist hier die dokumentierte Produktrolle, kein Auftrag zum Verschieben, Löschen oder Abschalten. `App/pax/`, zugehörige Assets, Templates, Tests, Docs und andere bestehende Prototypen bleiben vollständig erhalten. Die Aussage bezeichnet das jetzt beschlossene Zielmodell, keinen bereits erfolgten Runtime-Umbau.

## 12. Ausdrückliche Supersessions

Alle folgenden Ersetzungen gelten **nur für den zukünftigen neuen Vertrag**, niemals rückwirkend:

| Quelle / ältere Annahme | Zukünftige Einordnung |
| --- | --- |
| SammlrPax Contract V1 §4, Pax-Verpackung/Öffnen als primärer Einstieg | Top-Tauschvorschläge als konkrete Stickerstapel; keine Pax-Produktmetapher. |
| Pax-spezifischer Produkt-/Lifecycle-Rahmen in Contract und PAX-05/06 | Gemeinsamer Trade-Lifecycle für alle Herkünfte; Interaktionen bleiben Referenz. |
| Trade UX Soll V1: vorgeschriebene ältere Einstiegskomposition und manueller Nebenweg direkt im schnellen Vorschlagsflow | Zwei Discovery-Ebenen; Top direkt ansehen/anfragen, manueller Weg über Partneransicht. Operative Anfragen/Trades brauchen weiterhin Zugang, ihre genaue Navigation ist offen. |
| Product Bible §32: noch offene eigenständige SmartDeal-Inszenierung | Kanonischer Stapel als Deal-Repräsentation; keine Pack-Inszenierung. Keine Änderung der Algorithmik. |
| Product Bible §18 und entsprechende Regeln in §38; Algorithm AC22; Manual Contract §5 / Q4: nur offene ausgehende V1-Anfragen zählen, manuell ausgenommen | Bereits durch PAX-00 autorisierte gemeinsame operative 3/3-Regel, jetzt ausdrücklich für sämtliche neuen Trade-Herkünfte. |
| Q1, Product Bible §37.4/entsprechende Q1-Konkretisierung in §39, AC25/26: keine Fortsetzung mit reduziertem Paket | Bereits durch PAX-00 begrenzt ersetzt durch explizite, bestätigte Pre-Shipment-Amendments. Snapshot-Freeze, keine stille Reparatur, Schutz versendeter Richtungen bleiben. |

Nicht ersetzt: Algorithmus, Mengen-/Need-Regeln, Legacy-Schutz, AC23, Datenschutz, idempotente physische Buchungen und manuelle Erstellungsregeln. Ein gemeinsamer Lifecycle vereinheitlicht die Abwicklung, nicht sämtliche Erstellungsbedingungen. Alte Dokumente bleiben unverändert als Vertrags- und Historienquellen bestehen.

## 13. Offene Fragen und Integrationsgates

- Versionierung und technische Repräsentation des neuen Vertrags, Adapter für Legacy/V1 sowie gemeinsame, atomar geprüfte Slotprojektion; Herkunft allein genügt nicht.
- Exakter Partner-SmartDeal-Adapter auf bestehendem Algorithmus. Automatische Deals unter fünf sind derzeit nicht erlaubt; eine gewünschte Ausnahme braucht PO-Entscheid.
- Amendment-Zustimmungen, konkurrierende Änderungen, neue Supply-/Need-Prüfung, Ersatzbindung und Teilversand-Fälle. Kein Implementierungsfreibrief aus dem UX-Fehlmengenweg.
- Herkunftsübergreifende Identität, doppelte Anfragen und gegenseitige Anfragen. Bestehendes V1-Mutual-GO bleibt geschützt; keine stillschweigende Ausdehnung auf manuelle Angebote.
- Review von Verfall, Withdraw, Reminder und Timeout; AC23 gilt bis dahin.
- Empfang ohne vorherigen Partner-Versandklick, Problem-/Resolution- und Abschlussübergänge samt Buchungs-/Bewertungsrechten abschließend anbinden.
- Zulässige Sichtbarkeit zusätzlicher Partnerdaten und Filtersemantik, insbesondere Entfernung und striktes albuminternes 1:1. Kein Aufweichen bestehender Privacy-/Albumregeln.
- Konkreter Carrier-/Portal-Einstieg und Versandprodukte sind durch die lokale PAX-06-Demo nicht belegt; keine erfundene produktive Anbindung.

Diese Grenzen verhindern keine widerspruchsfreie Dokumentation. Sie verhindern eine ungeprüfte direkte Übernahme der Prototypen oder bestehender inkompatibler Pfade in den neuen produktiven Vertrag.

## 14. Nicht-Ziele

Kein UI-/Routenumbau, keine neuen Cards/Tabellen, keine CSS-/JS-/Python-Änderungen, keine Algorithmusänderung, DB-Migration, Bestandsmutation oder Veränderung bestehender Trades. Keine Löschung oder Refaktorierung der Pax-/Wall-Komponenten. Keine neuen Versandmaschinen oder jetzt festgeschriebenen finalen DB-Zustandsnamen. Keine Umsetzung der Filter oder offenen Lifecycle-Gates in TRADE-00.

## 15. Integrationsstrategie

Zuerst die offenen Domainübergänge und versionierten Grenzen festlegen. Danach den gemeinsamen Lifecycle über die vorhandenen autorisierten Request-, Reservation-, Versand-, Empfangs- und Problemservices anbinden, mit getrennten Erstellungsvalidatoren für automatische und manuelle Angebote. Bestehende Vorgänge bleiben auf ihrem Vertrag; unbekannte Vertragstypen dürfen nicht als Legacy interpretiert werden.

Discovery und Partner-SmartDeal nutzen kanonische Supply-/Need-Daten und bestehenden Optimizer; manuelle Angebote erhalten den vorgesehenen atomaren Submit-Pfad. Keine Übernahme der lokalen JS-Demozustände als Produktionsdomain. Slot- und Supplyprüfungen müssen gemeinsam nebenläufigkeitssicher sein.

Vor produktiver Freigabe: Regression für Legacy/V1, alle neuen Herkünfte, 3/3 über Annahme und eigenen Versand, Fristen, exakte Snapshots, Datenschutz, Idempotenz und getrennte physische Richtungen. Erst nach vollständigem Lifecycle die kanonische Stackquelle auslagern und Wall5/Receive10 absichern. Diese Reihenfolge ist eine Integrationsleitlinie, kein Implementierungsauftrag.

## 16. Quellen und Audit

Die geprüften Quellen, erhaltenen Regeln, zukünftigen Ersetzungen und Domaingrenzen stehen im [TRADE-00 Reset Audit](TRADE_00_RESET_AUDIT.md). PAX-05/06-Erkenntnisse sind in §§8–11 übernommen; ältere Verträge bleiben unverändert.
