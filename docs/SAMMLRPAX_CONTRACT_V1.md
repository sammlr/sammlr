# PAX-00 — SammlrPax Product/UX Contract V1

Stand: 2026-09-28. Grundlage: PAX-00-Auftrag und ausdrückliche PO-Auflösung der Domainkonflikte vom 2026-09-28. **Verbindlicher Produkt-/UX-Zielvertrag für den zukünftigen separaten Pax-/Trade-Zweig; ausschließlich Dokumentation, keine Implementierungs- oder Aktivierungsfreigabe.** Ausdrücklich offene Punkte bleiben offen.

## 1. Geltungsbereich und Legacy-Grenze

SammlrPax bezeichnet ausschließlich automatisch von Sammlr erzeugte SmartDeals. Manuelle/freie Tauschangebote sind niemals SammlrPax. Pax-Packaging, lila Pack und Öffnungsmetapher bleiben algorithmisch erzeugten SmartDeals vorbehalten. Nach Annahme dürfen beide Einstiege denselben technischen Unterbau für Packen, Adresse, Versand, Empfang, Probleme und Bewertung verwenden.

Die hier ausdrücklich geänderten Domainregeln gelten nur für den **zukünftigen separaten Zweig beziehungsweise dessen neuen Contract-Type/Lifecycle**. Dessen technische Kennung und Repräsentation sind noch nicht festgelegt. Bestehende Legacy- und SmartDeal-V1-Vorgänge behalten vollständig ihren bisherigen Vertrag. Keine rückwirkende Migration, Umklassifikation oder Änderung bestehender Vorgänge. Ihre tatsächlichen Reservations-, Supply- und Incoming-Bindungen bleiben bei neuer Planung wirksam.

PAX-00 allein verändert keinerlei Runtime- oder DB-Verhalten. Bestehende Dokumente und Implementierungen werden nicht überschrieben. Nicht ausdrücklich ersetzte Sicherheits-, Privacy-, Mengen-, Buchungs- und Identitätsprinzipien bleiben maßgeblich. Die Supersession-Matrix in §14 begrenzt die Änderungen; sie ist kein pauschales Außerkraftsetzen des Algorithm Contract.

## 2. Discovery und Kandidaten

Ungefähr fünf gleichzeitig auswählbare Pax-Kandidaten bilden das Schaufenster verfügbarer SmartDeals. Fünf sichtbare Pax sind keine fünf laufenden Anfragen und belegen keine operativen Slots. Vorschläge sind von verbindlichen Anfragen und deren Ressourcenbindung zu unterscheiden.

Ein Kandidat darf verworfen werden; danach darf ein weiterer nachrücken. Niemand muss einen uninteressanten Kandidaten anfragen, um weitere zu sehen. Verwerfen eines Vorschlags ist keine Ablehnung einer bereits bindenden Anfrage. Dauer und technische Speicherung des Verwerfens werden hier nicht erfunden.

Matching/Sichtbarkeit und tatsächliche Anfragbarkeit sind getrennte Konzepte. Ein Nutzer mit voller eingehender Kapazität erhält vorübergehend keine weitere Anfrage, muss deshalb aber nicht dauerhaft aus dem Matching verschwinden. Eine sichtbare Chance ist keine Zusage, dass sie unverändert anfragbar bleibt; bestehende frische Supply-/Need-/Eligibility-Prüfungen bleiben erforderlich.

## 3. Operative Kapazität: gemeinsam 3 ausgehend / 3 eingehend

Pax und spätere manuelle Trades des neuen Zweigs teilen dieselbe Kapazitätssteuerung: maximal drei operative ausgehende und maximal drei operative eingehende Slots pro Nutzer. Beispiel: zwei operative ausgehende Pax plus ein operativer ausgehender manueller Trade ergeben 3/3 ausgehend.

**Request-State und operativer Slot-State sind ausdrücklich verschieden.** Diese Regel ist keine neue Bedeutung von `open request count`. Eine angenommene Anfrage ist nicht mehr pending, kann aber weiterhin eigene physische Arbeit und damit einen belegten Slot bedeuten. Die spätere technische Repräsentation ist offen; PAX-00 legt weder Tabellen noch Statusfelder fest.

| Fachliches Ereignis | Operative Kapazität im neuen Zweig |
| --- | --- |
| Kandidat ansehen, öffnen oder verwerfen | Kein Slot entsteht |
| Tatsächliche Anfrage A → B | Ausgehender Slot bei A und eingehender Slot bei B; beide Kapazitätsgrenzen müssen eingehalten werden |
| Anfrage wird angenommen | Bestehende entsprechende Slots bleiben belegt; kein Freischalten unbegrenzter neuer Anfragen allein durch Annahme |
| A bestätigt eigenen Versand | Nur As entsprechender Slot wird frei, unabhängig von Bs Versandstand |
| B hat selbst noch nicht versendet | Bs entsprechender Slot bleibt belegt, auch wenn As Sendung bereits unterwegs ist |
| Ablehnung, Withdraw, Expiry oder vollständiges Beenden vor Versand | Betroffene Slots werden frei; Ressourcenfreigaben nach geltendem Lifecyclevertrag |
| Eigene Sendung bereits versendet/unterwegs | Kein operativer Slot für diesen eigenen abgearbeiteten Teil mehr |

Annahme eines eingehenden Vorgangs erzeugt nicht allein dadurch eine neue ausgehende Anfrage. Fachliche Richtung folgt dem tatsächlichen Anfrageverhältnis; technische Sonderfälle wie konkurrierende Gegenanfragen müssen im späteren Lifecycle-/Kapazitätsvertrag konsistent abgebildet werden, ohne Doppelbelegung.

Kein künstliches Tages- oder Gesamtlimit: Wer abarbeitet und selbst versendet, erhält wieder Kapazität. Slotfreigabe ist **keine** allgemeine Freigabe des Partnerbestands. Supply-/Reservation-/Incoming-Regeln gelten unabhängig weiter; dasselbe physisch verfügbare Exemplar darf niemals parallel mehrfach verplant werden. Freie operative Kapazität allein macht ein Paket nicht ausführbar.

## 4. Anfragephase: öffnen, ansehen, anfragen

Das geschlossene Pax übernimmt die bestehende lila SammlrPax-Metapher der Preview. Öffnen ist ein visueller Übergang. Danach erscheinen zwei klar getrennte Informationswelten: **Du bekommst** und **Du gibst ab**. Finale visuelle Politur bleibt offen.

### 4.1 Du bekommst: Albumstapel

Receive wird nach Album gruppiert, nicht als globaler Monsterstapel: sechs beteiligte Receive-Alben ergeben sechs Albumstapel. Jeder Stapel verwendet die abgenommene echte Stickerwall-Sprache einschließlich Faces, Prefix/Nummer, Fonts, Kartengeometrie, Konturen, Radien, Schatten und Stack-Wirkung.

Jeder Albumstapel kann einzeln geöffnet/aufgefächert und wieder zusammengelegt werden. Die Aktion betrifft nur den gewählten Stapel, nicht pauschal alle Alben. Die produktive LOCKED Stickerstack-Mechanik und ihre Geometrie bleiben unverändert. Album-Paketdarstellung darf nicht als neuer physischer Inventorybestand oder als Mehrfachmenge eines einzelnen Sticker-Codes ausgegeben werden.

### 4.2 Du gibst ab: informative Post-its

Give verwendet die rote/rosa handschriftliche Sammlr-Post-it-/Listenwelt mit vorhandener Typografie und Mengenlogik. **In der Anfragephase keine Checkboxen, kein Durchstreichen und keine Packkontrolle.** Die Liste informiert ausschließlich. CTA: **„Pax anfragen“**; keine Pflichtprüfung jedes Give-Stickers vor einer Anfrage. Fachliche Kapazitäts-/Ausführbarkeitsprüfungen bleiben davon unabhängig.

Jedes Album beginnt mit einem eigenen roten Zettel und Albumüberschrift. Reicht dessen kanonische Kapazität nicht, folgen unmittelbar zugehörige Fortsetzungszettel ohne wiederholte Albumüberschrift. Fortsetzungen stehen eng/direkt anschließend oder leicht überlappend. Ein neues Album erhält eine neue Überschrift und sichtbar mehr Abstand zur vorherigen Albumgruppe. Kein einzelner unübersichtlicher Gesamtzettel und keine erfundene neue Zettelkapazität.

## 5. Kanonische Komponenten- und Mengenreferenzen

### 5.1 Post-it-Kapazität und Fortsetzung

Kanonisch ist [App/static/sticker_list.js](../App/static/sticker_list.js), insbesondere die vier `STICKER_LIST_REVIEW_*_CAPACITY`-Konstanten und `stickerListRenderReviewMode`:

| Eigenschaft | Bestehende Regel |
| --- | --- |
| Erster Zettel | Bis 16 Einträge, bis 8 pro Spalte |
| Fortsetzungszettel | Jeweils bis 20 Einträge, bis 10 pro Spalte |
| Spaltenwechsel | `is-two-column`, sobald der Chunk die jeweilige Einspaltenkapazität überschreitet |
| Anzahl Fortsetzungen | `ceil(max(0, n - 16) / 20)` |
| Fortsetzungsinhalt | `cloneNode(false)`, eigener Codes-Container, `is-continuation`, keine kopierte Überschrift |
| Vollständigkeit | Alle Chunks in bestehender Reihenfolge; kein Abschneiden oder „weitere …“ als Ersatz |

Grenzfälle aus [tests/test_ceoklaue_sticker_list.py](../tests/test_ceoklaue_sticker_list.py), `test_review_capacity_boundaries_and_distribution_are_fixed`: 16 → [16]; 17 → [16, 1]; 36 → [16, 20]; 37 → [16, 20, 1]; 56 → [16, 20, 20]. Die Zahlen bezeichnen **einzelne Einträge/Exemplare**, nicht die Anzahl unterschiedlicher Codes.

[App/sticker_list.py](../App/sticker_list.py) expandiert Mengen zu `(code, instance)`; `list_item` kennzeichnet Give-Exemplare mit `data-instance`. `stickerListItemKey` in der JS-Datei verwendet `code::instance`. Mehrfachexemplare dürfen deshalb weder dedupliziert noch als ein einziger abhakbarer Code behandelt werden. Bei späterer Multi-Album-Anbindung muss zusätzlich der Albumkontext eindeutig bleiben; die bestehende Single-Album-Keybildung ist keine fertige globale Pax-Identität.

PAX-00 übernimmt die bestehende Kapazitäts-/Chunkinglogik **pro Albumgruppe**. Die aktuelle Review-Funktion ist keine bereits fertige Multi-Album-Pax-Implementierung. Albumüberschrift, Gruppenabstand und Fortsetzungsnähe sind der neue dokumentierte Gruppierungsauftrag, kein Auftrag zur Änderung der echten Stickerliste.

Kanonische Optik: [App/static/sticker_list.css](../App/static/sticker_list.css), `.trade-postit`, `.trade-postit-give`, `.trade-postit-content`, `.is-continuation`, `.sticker-list-review-codes`; bestehende 224×224-Zettel, 20-px-Codezeilen, erster Codes-Bereich 160 px, Fortsetzung 200 px. Handschrift: bestehende CEOKlaue-Final-Alternativen und `stickerListWriteCeoklaue`, keine neue Handschrift.

Kanonischer Durchstreichmodus: `list_item`/Give-Marker in `sticker_list.py`, `.sticker-list-item.selected`, `.sticker-selection-marker` und `.marker-draw-*` in der CSS sowie bestehende Give-Cross-Assets. Diesen Auswahlmechanismus erst in der Packphase verwenden. Die heutige Listen-/Transfer-Domainwirkung wird dadurch nicht als Pax-Packcommand übernommen.

### 5.2 Stickerwall und LOCKED Stack

Kanonische Darstellung: `sticker_wall_slot_html`, `sticker_wall_card_inner` und `sammlr_retro_number_svg` in [App/webapp.py](../App/webapp.py); Retro-Ziffern V3. CSS in [App/static/style.css](../App/static/style.css): `.sticker-slot-frame`, `.sticker-wall-stack-layer`, `.slot` und `.sammlr-retro-number`.

Das bestehende physische Stack-Prinzip bleibt geschützt: Basiskarte verankert, zusätzliche Kopien nach oben/links, `--stack-step:2px`, maximal fünf sichtbare Karten; echte Menge nicht auf fünf kürzen. Referenzen: [tests/test_sticker_wall_product_island.py](../tests/test_sticker_wall_product_island.py), insbesondere `test_stack_caps_at_five_layers_without_changing_real_badge_quantity`, und [tests/research/check_vertical_stacks.py](../tests/research/check_vertical_stacks.py). Hier nur Quellprüfung, keine Testausführung.

### 5.3 Preview-Einordnung

Journey V1 und V2 bleiben unveränderte historische Design-/Interaktionsreferenzen, keine produktiven Domainverträge. Quellen: [V1-Template](../App/templates/sammlrpax_journey_v1.html), [V2-Template](../App/templates/sammlrpax_journey_v2.html), [V2-State](../App/static/sammlrpax_journey_v2.js), [Preview-Registrierung](../App/trade_visual_preview.py), [isolierter V2-Einstieg](../App/sammlrpax_journey_v2_preview.py).

**superseded by PAX-00:** globaler Receive-Stapel in V2; Durchstreichen und vollständige Give-Prüfung als Voraussetzung für Anfrage beziehungsweise Annahme in V2. Ziel sind Albumstapel und informative Give-Listen bis Annahme. Keine Preview wird in PAX-00 angepasst.

## 6. Gespiegelte Partneransicht

Dieselbe Oberfläche zeigt dasselbe konkrete Paket mit gespiegelten Leistungen: A RECEIVE = B GIVE und A GIVE = B RECEIVE, einschließlich Alben, Codes und Mengen. Keine zweite Partner-UX.

Der Empfänger kann Receive-Albumstapel ansehen/auffächern, Give-Listen lesen, **Pax annehmen** oder **Pax ablehnen**. Er kann das algorithmisch erzeugte Paket vor Annahme nicht frei editieren. Abweichende Wunschpakete gehören später in manuelle Trades, nicht in einen verdeckten Pax-Editor. Auch die Annahme verlangt keine vorgelagerte Packkontrolle.

## 7. Packphase erst nach Annahme

Erst nach Annahme werden dieselben roten Give-Post-its zur echten Packcheckliste. Tap bedeutet physisch gefunden/eingepackt; erneuter Tap macht die Markierung rückgängig. Bestehender Durchstreichmodus, keine Checkbox-UI.

Durchstreichen bucht keinen physischen Bestand aus. Sekundärer Fortschritt: **„x / y eingepackt“**, bei Vollständigkeit **„y / y eingepackt“**. Kein dominantes Dashboard. Nach vollständiger Prüfung folgt der Versandübergang.

Wer mit offenen Einträgen weitergehen möchte, darf nicht unmittelbar Versand bestätigen. Die konkreten noch offenen Sticker werden sichtbar gezeigt. Zwei fachliche Fälle sind zu unterscheiden:

- Noch nicht in der Checkliste bestätigt: zurück zur Packliste.
- Tatsächlich nicht mehr verfügbar: Abweichung melden, Partner informieren, expliziten Änderungs-/Beendigungsweg verwenden.

Finales Wording ist offen. Insbesondere „Sticker fehlen wirklich“ ist **nicht abgenommen**.

## 8. Explizites Pre-Shipment Amendment

Q1/AC25/26 werden für den neuen Pax-Zweig nur im ausdrücklich beschriebenen Umfang weiterentwickelt. **Niemals stille Paketänderung, niemals automatische heimliche Reparatur. Der vereinbarte Snapshot bleibt verbindlich, bis eine explizite Änderung von den erforderlichen Parteien bestätigt ist.**

Meldet ein Nutzer vor Versand tatsächlich nicht verfügbare vereinbarte Give-Sticker, sieht der Partner exakt die betroffenen Alben, Codes und Exemplare/Mengen. Fachlich stehen drei Optionen zur Verfügung:

1. Mit reduzierter Gegenleistung weiter tauschen.
2. Paxgröße symmetrisch anpassen.
3. Trade beenden.

Das exakte neue Paket und alle entfernten Positionen müssen vor neuer Bindung sichtbar sein. Erforderliche Zustimmung(en), Versions-/Bindungsübergang, Revalidierung, konkurrierende Änderungen und Abbruch werden im späteren Lifecycle-Contract exakt festgelegt. Hier kein erfundener Zustimmungsautomat oder Persistenzentwurf. Eine bloße Fehlmeldung ändert den gebundenen Snapshot nicht und erlaubt keinen ungeklärten Versand.

### 8.1 Deterministische Größenanpassung

Bei geltender albumstrikter 1:1-Regel wird die entsprechende Gegenleistung aus demselben Album reduziert. Ohne albumstrikte 1:1-Regel werden die entsprechenden gleichen Positionen aus der kanonischen/deterministischen Dealreihenfolge der Gegenseite entfernt. Beispiel: nicht lieferbare Give-Positionen 3 und 37 führen bei symmetrischer Anpassung zur Entfernung der deterministischen Gegenpositionen 3 und 37.

Keine zufällige Auswahl, keine Wertigkeitsheuristik, keine stille SmartDeal-Neuberechnung. Beide Seiten sehen exakt, was entfernt wird. Die technische Abbildung von Mengen auf eindeutige Positionen/Exemplare und die verbindliche Ordnung gehören in den späteren Lifecycle-Contract; die visuelle Zettelreihenfolge darf nicht versehentlich eine neue fachliche Ordnung erzeugen.

Diese Fallunterscheidung erweitert nicht eigenmächtig Q3: Die bestehende Empfängerpräferenz OPEN/SAME_ALBUM_ONLY gilt bisher nur für neue manuelle Angebote. PAX-00 führt dadurch keinen neuen SmartDeal-Filter und keine neue globale albumstrikte Optimierung ein.

### 8.2 Unveränderte Sicherheitsgrenzen

Initial algorithmisch erzeugte SmartDeals bleiben grundsätzlich 1:1. Explizit akzeptierte reduzierte Gegenleistung ist eine neue Amendment-Ausnahme im künftigen Lifecycle, keine Lockerung des SmartDeal-Generators oder Legacy-Validators. Der ursprüngliche Snapshot darf nicht rückwirkend umgeschrieben werden.

Bereits physisch versendete Richtungen dürfen niemals rückwirkend verkleinert oder verändert werden. **Gegenseite schon versendet + nachträgliche Abweichung** bleibt gesondert im späteren Lifecycle-Contract zu behandeln; die normale Pre-Shipment-Anpassung autorisiert keine solche Rückwirkung. Nach Versand entdeckte Abweichungen sind Problemfälle. Kein fiktiver Inventory-, Reservations- oder History-Reset.

Die AC26-Mehrfachunterdeckungspriorität wird nicht durch ein frei erfundenes neues Auswahlverfahren ersetzt. Ihre technische Zusammensetzung mit dem neuen Amendment-Verfahren muss später ausdrücklich geschlossen werden; PAX-00 erlaubt weder automatische Teilkürzung noch Verdrängung gültiger Bindungen durch attraktivere neue Vorschläge.

## 9. Adresse und Versandübergang

Keine Adresse beim bloßen Pax-Ansehen oder in der Anfragephase. Nach vollständiger Packprüfung beziehungsweise akzeptierter Dealänderung folgt der Versandübergang. Vorgesehen: „x/x eingepackt“ → weiter → gelber Action-Post-it und/oder Briefumschlag mit Versandadresse. Nach einer Änderung bezieht sich die Packprüfung auf die tatsächlich vereinbarte zu versendende Leistung; keine Versandbestätigung mit ungeklärten offenen Positionen.

Beispielinhalt, keine echten Kontaktdaten:

> Versenden an
> Fatima Beispiel
> Musterstraße 89
> 29693 Hodenhagen

Exakte Optik und Wording werden separat abgenommen. Danach Versand bestätigen über den später gezielt angebundenen vorhandenen Mechanismus.

Adresse anzeigen setzt weiterhin die berechtigte konkrete Tradefreigabe voraus. Eigentümerfreigabe, optionale gespeicherte Vorlage und autorisierter Read bleiben getrennt; ein Umschlag oder erfolgreicher Packcheck ersetzt keine Zustimmung. NP-C3-1 und T8a-Kontaktgrenzen gelten fort, einschließlich fehlender öffentlicher Adressprojektion und fehlender automatischer Freigabe an neue Partner.

Eigene Versandbestätigung bucht die tatsächlich vereinbarten eigenen Positionen nach bestehendem physischen Buchungsvertrag genau einmal aus und gibt den eigenen entsprechenden operativen Slot frei. Die Gegenseite darf noch offen sein. Packmarkierungen, Anfrage und Annahme sind keine physische Buchung. Transit ist kein Besitz.

## 10. Nach Versand, Empfang, Probleme und Abschluss

Nach eigener Versandbestätigung verlässt der Trade die primäre Pack-/Arbeitsansicht und wechselt in einen ruhigeren Versand-/Statusbereich. Das vorhandene Versandportal soll später grundsätzlich wiederverwendet, optisch angepasst und vereinfacht werden. Nächsten Schritt hervorheben; lange technische Ereignislisten zurücknehmen, vollständigen Verlauf gegebenenfalls sekundär öffnen.

Beispiel einer Anzeige: „Gepackt ✓ / Versendet ✓ / Angekommen ○“. Dies definiert keinen neuen DB-Status und keinen zusätzlichen Pflichtklick „Verpackt“. Beide physischen Richtungen bleiben korrekt unterscheidbar.

Nach Empfang: Empfang bestätigen oder Problem melden. Nur tatsächlich bestätigter physischer Eingang wird eingebucht; Teil-/Fehlempfang nicht als Vollmenge verbuchen. Zwei Versandbestätigungen allein schließen den Trade nicht erfolgreich ab. Q2 (physischer Empfang trotz fehlendem Partner-Versandklick) wird durch PAX-00 nicht aufgehoben; dessen bestehende Buchungs-/Evidenzschutzregeln bleiben erhalten. Die Abbildung dieses Sonderfalls auf neue operative Slots ist später ausdrücklich zu spezifizieren, ohne einen fremden Versandklick oder historischen Zeitpunkt zu erfinden.

Bewertung nach Abschluss ist einfach mit 1–5 Sternen geplant; genaue Darstellung offen. Kein automatischer Strafscore wegen eines Problems. Bestehende zulässige Bewertungen qualifizierter Problemabschlüsse bleiben erhalten und von normalem Erfolg unterscheidbar; keine Änderung des SmartDeal-Optimierers durch Ratings.

Abgeschlossene Trades verlassen die aktive Hauptansicht und liegen sekundär, etwa unter „Erledigt“ oder „Vergangene Tausche“. Finales Wording offen.

## 11. Manuelle Trades und Navigation

Manuelle Trades werden später separat gebaut: kein Pax-Packaging, kein Aufreißen, keine Pax-Bezeichnung. Nach Annahme können sie Packcheckliste, Adresse, Versand, Empfang, Probleme und Bewertung mit Pax teilen. Im neuen Zweig gilt die gemeinsame operative Kapazität aus §3; geschützte alte manuelle Vorgänge werden nicht migriert. Sonstige manuelle Mengen-/Präferenzregeln werden nicht beiläufig ersetzt.

Der bestehende Dreierswitch „Tauschpartner / Trades / Anfragen“ ist keine finale UX. Später zu prüfen ist eine handlungsorientierte Trade-Home/InBox mit neuen Pax, zu erledigen, wartet auf andere, unterwegs, Tauschpartner/manuellen Einstieg und sekundär erledigten Trades. Keine finale Navigationshierarchie oder neuen URLs durch PAX-00. Bestehende sichere Deep Links, Auth-/Beteiligten- und Rückzielprüfungen bleiben bei späterer Anbindung zu schützen.

## 12. Zeitvertrag und offene PO-Reviews

**AC23 wird nicht superseded.** Bis zu einer ausdrücklichen späteren Entscheidung gilt `expires_at = binding_created_at + 24 Stunden` als absolute Zeitspanne. Retry setzt den Bindungszeitpunkt nicht zurück. Ab Erreichen der Frist ist eine pending Anfrage nicht mehr annehmbar; konsistente Freigabe bleibt erforderlich. Pending-Expiry darf keinen bereits angenommenen Trade nachträglich freigeben.

**PO review before productive Pax integration** — Verfall, Withdraw/Rückruf, Reminder und Timeout-Verhalten verschiedener Lifecycle-Zustände werden vor produktiver Integration erneut gemeinsam geprüft. „Review offen“ bedeutet weder abgeschaffte 24 Stunden noch jetzt eingeführte neue Fristen. Bestehende Withdraw-/Release-Autorisierung gilt bis zu einer ausdrücklichen späteren Entscheidung weiter; keine automatische Verlängerung oder Reminder-Regel erfunden.

Bewusst offen bleiben außerdem:

- Finales Wording im Packfehler-/Abweichungsflow.
- Finale Pax-Optik/Politur und genaue UX „Anfrage gesendet / wartet“.
- Exakte erforderliche Zustimmung(en) und Lifecycle-/Bindungstechnik für Amendments.
- Sonderfall einseitig bereits versendet und nachträgliche Abweichung.
- Technische Slot-Repräsentation und deren Sonderfall-/Concurrency-Abbildung.
- Zusammenspiel des Amendment-Flows mit AC26-Mehrfachunterdeckung und kanonischer Positionsordnung.
- Finale Trade-Home/Navigation und optische Anpassung des Versandportals.
- Finale Optik/Wording des Adress-/Versandübergangs und genaue Bewertungsdarstellung.

Diese Punkte sind keine verdeckten Implementierungsentscheidungen. Sie müssen in den entsprechenden späteren Blöcken geschlossen werden.

## 13. Architekturziel für spätere Blöcke

Der neue Pax-Zweig entsteht zunächst separat/modular. Kein weiterer großer Lifecycleblock direkt in `App/webapp.py`. Unverbindliche Modulaufteilung als Zielrichtung:

```text
App/pax/
  __init__.py
  routes.py
  service.py
  matching.py
  lifecycle.py
  capacity.py
  shipping.py
  problems.py
```

Dazu eigene Pax-Templates/Assets. **Keine dieser Dateien wird durch PAX-00 angelegt.** Bestehende Trade-/SmartDeal-Domainlogik später gezielt anbinden und wiederverwenden, nicht duplizieren oder leichtfertig ersetzen. Neue Contract-Grenze und erforderliche Adapter müssen ausdrücklich nachgewiesen werden. Erst nach vollständiger Abnahme kontrolliert an die bestehende App anbinden. Historische Roadmap-Verweise auf `webapp.py` sind keine Erlaubnis, dieses Architekturziel zu umgehen.

## 14. Audit und ausdrückliche Supersession

Geprüfte Vertragsquellen und auftragsrelevante Ergebnisse:

| Quelle | Abgleich und Geltung |
| --- | --- |
| [TRADE_UX_SOLL_V1](TRADE_UX_SOLL_V1.md), insbesondere §§2–10, 13–14 | Discovery getrennt von Requests, physische Buchung und Adressschutz bleiben. Navigation nicht final; Anfrage-/Packphasen richten sich im neuen Zweig nach PAX-00. Q1-/Quotenabweichungen siehe unten |
| [TRADE_UX_PO_DECISIONS_Q1_Q8](TRADE_UX_PO_DECISIONS_Q1_Q8.md), Q1–Q8 und NP-C3-1 | Q1 teilweise ersetzt; Q2 physische Realität, Q3 Präferenzgrenze, Q6 Rating und Kontaktfreigabe bleiben. Keine pauschale Aufhebung des Decision Records |
| [MANUAL_OFFER_DOMAIN_CONTRACT_V1](MANUAL_OFFER_DOMAIN_CONTRACT_V1.md), §§1–9 | Eigenständige manuelle Vertragsart und geschützte bisherige Vorgänge bleiben. Für zukünftige neue manuelle Trades gilt gemeinsame operative 3/3-Kapazität statt Übernahme einer ausgeschlossenen manuellen Quote. 24h nicht aufgehoben |
| [TRADE_NEXT_BLOCKS_TECH_PREP](TRADE_NEXT_BLOCKS_TECH_PREP.md), C1–C4 | Wiederverwendbare Ship-/Receipt-/Problem-/Kontaktanschlüsse und Privacygrenzen; technische Vorschläge nicht mit Implementierung gleichsetzen. Alte Unfulfillable-Vorgaben nur im ausdrücklich ersetzten Umfang anders |
| [SMARTDEAL_PRODUCT_BIBLE_V1](SMARTDEAL_PRODUCT_BIBLE_V1.md), §§9–23, 37–39 | Ungefähr fünf Kandidaten, Mengen, Reservierungen, physische Wahrheit bleiben. Quote und Reparaturverbot für neuen Zweig teilweise ersetzt |
| [SMARTDEAL_ALGORITHM_CONTRACT_V1](SMARTDEAL_ALGORITHM_CONTRACT_V1.md), AC20–29 | AC22 für neuen Zweig ersetzt; AC25/26 begrenzte Amendment-Ausnahme; AC23 bleibt gültig. Algorithmus nicht heimlich neu definiert, Legacygrenze bleibt |
| [SMARTDEAL_TECHNICAL_ROADMAP_V1](SMARTDEAL_TECHNICAL_ROADMAP_V1.md), T1, T5a/b, T6b, T7a/b, T8a, T9–T11 | Wiederverwendung und Schutzgates bleiben Referenz. Alte Quoten-/No-Repair-Annahmen dürfen nicht ungeprüft in den neuen Zweig übernommen werden; modularer Aufbau gemäß §13 |

### 14.1 Domainentscheidungen — durch PO ausdrücklich aufgelöst

| Ältere Entscheidung | Status ausschließlich für zukünftigen neuen Zweig | Was bleibt geschützt? |
| --- | --- | --- |
| Q1; UX SOLL §8; Bible §22/§37.4/§39; AC26: vor Versand zwingend gesamter Deal unfulfillable, kein reduzierter Teilvertrag, kein Gegenstück entfernen; Roadmap T7b: kein Reparaturpfad | **superseded by PAX-00, teilweise:** expliziter Pre-Shipment-Amendment-Flow gemäß §8 erlaubt reduzierte Gegenleistung, symmetrische Anpassung oder Beenden | Keine automatische heimliche Reparatur; keine Paketmutation ohne notwendige Zustimmung; tatsächliche physische Fakten und alte Snapshots erhalten; kein rückwirkender Eingriff in versendete Richtungen |
| AC25: nach GO ausnahmslos unveränderlicher Inhalt | **superseded by PAX-00, teilweise:** explizit bestätigter neuer Vereinbarungsstand darf im neuen Lifecycle gebunden werden | Bisheriger Snapshot gilt bis zur nötigen Bestätigung. Keine stille Überschreibung, UI-Editierung desselben Frozen-Pakets oder heimliche Neuberechnung |
| Bible §18/§38 Nr. 5; AC22; UX SOLL §6: nur pending ausgehende SmartDeal-V1-Anfragen zählen, accepted zählt nicht; manuelle Angebote ausgenommen; Manual Contract §5 ohne manuelle Quote | **superseded by PAX-00:** gemeinsame operative 3/3-Slots für neue Pax/manuelle Trades; Annahme hält Slot, eigener Versand gibt eigenen Slot frei | Keine Umdeutung bestehender `open request count`-Semantik, keine Legacy-Migration, Supply-/Need-Bindungen unabhängig wirksam |
| AC23, Manual Contract §5: absolute 24h-Frist | **Nicht superseded.** Vorläufig weiterhin gültig; „PO review before productive Pax integration“ | Absolute Frist ab Bindung, keine Retry-Verjüngung, keine pending Expiry eines accepted Trades |

Initiale 1:1-Erzeugung bleibt geschützt; die ausdrücklich erlaubte reduzierte Fortsetzung ist auf das spätere bestätigte Amendment begrenzt. Die konkrete AC26-Konfliktpriorität wird nicht eigenmächtig neu entschieden. Der Sonderfall bereits versendeter Richtungen bleibt offen, nicht still unter den normalen Amendment-Weg subsumiert.

### 14.2 Ersetzte ältere UX-Entscheidungen

**superseded by PAX-00** für das neue Zielsystem sind: ein globaler Receive-Stapel statt Albumstapeln; Packprüfung/Durchstreichen vor Anfrage oder Annahme; V2-CTA-Freigabe erst nach vollständiger Give-Prüfung; ein bloßes Durchreichen des V2-Ablaufs direkt zum Versand ohne eigene Packphase nach Annahme. Auch der historische Dreierswitch und eine bereits abschließend verstandene ältere Home-Anordnung gelten nicht als finale Navigation. Die konkrete neue Trade-Home bleibt offen.

Die alte Aussage „kein eigener Zustand Verpackt/kein Pflichtklick“ wird nicht in einen neuen DB-Status umgedeutet: Neu verbindlich ist die Packcheckliste nach Annahme mit Prüfung offener Einträge vor Versand. Die genauen technischen Zustände sind später zu definieren.

### 14.3 Konfliktstatus

Die im Erstabgleich gefundenen echten Domainkonflikte (No-Repair/Freeze und Quotenbedeutung) sind durch ausdrückliche PO-Entscheidung für den zukünftigen separaten Zweig **begrenzt aufgelöst**, nicht als bloße UX-Altlasten wegdefiniert. AC23 bleibt unverändert; sein Review ist kein weiterer Override. Kein zusätzlicher ungelöster direkter Widerspruch im geprüften Scope; die genannten Lifecycle-Ausgestaltungen bleiben offen und sind keine Implementierungsfreigabe.

## 15. Dokumentationsabschluss

Einziger neuer Output dieses Auftrags: `docs/SAMMLRPAX_CONTRACT_V1.md`. Keine Änderung bestehender Contracts, Produktiv-/Previewdateien, Tests, Routes, Runtime oder Datenbank; keine Migration. Keine Tests/Benchmarks für diesen reinen Dokumentationsschritt ausgeführt. Abschlusskontrolle: `git diff --check` plus Whitespace-Prüfung der neuen, noch ungetrackten Datei. Kein git add, Commit, Push oder Deploy. Danach STOP.
