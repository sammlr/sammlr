# sammlr. SmartDeal Product Bible V1

Status: Produktvertrag V1
Zweck: Definiert, was SmartDeal sein soll, bevor bestehende Trade-Routen, UI oder Backend darauf umgebaut werden.
Noch kein Implementierungsauftrag.

**PO-Nachtrag vom 2026-09-10:** Die Entscheidungen in [§37](#37-po-entscheidungen-vom-2026-09-10) präzisieren ausschließlich Mehrfachbedarf, Altvorgänge, Versandkontakt/Chatoption, Unfulfillable und Top-N. Bei Widersprüchen zu älteren Beispielen/Ausschlüssen gelten diese ausdrücklich neu entschiedenen Punkte. Der [Algorithm Contract V1](SMARTDEAL_ALGORITHM_CONTRACT_V1.md) dokumentiert die algorithmische Spezifikation samt noch offenen semantischen Fragen.

---

## 1. Die Idee

SmartDeal ist nicht einfach eine bessere Tauschpartnersuche.

SmartDeal soll dem Sammler die eigentliche Denkarbeit beim Tauschen abnehmen.

Der Nutzer soll nicht fragen müssen:

Wer hat Sticker für mein WM-Album?

Sammlr soll beantworten:

Welche Tausche bringen meine gesamte Sammlung jetzt am schnellsten voran?

Dabei denkt Sammlr sammlerzentriert und albumübergreifend.

Ein Nutzer kann einem anderen 17 WM-Sticker geben und dafür Sticker aus drei völlig anderen Alben erhalten.

Das ist kein Sonderfall.

Das ist genau der Sinn von SmartDeal.

---

## 2. Oberstes Produktziel

SmartDeal soll:

möglichst viele fehlende Sticker durch möglichst sinnvolle, große 1:1-Tausche beschaffen und unnötige Sendungen vermeiden.

Dabei gelten zunächst alle fehlenden Sticker gleich.

Ein fehlender WM26-Sticker ist algorithmisch nicht wertvoller als ein fehlender Sticker aus einem alten Bundesligaalbum.

Fehlend ist fehlend.

Keine versteckten Seltenheits-, Fortschritts- oder Album-Scores in V1.

---

## 3. Albumübergreifend by default

Der globale SmartDeal betrachtet alle aktiven, für Trades freigegebenen Alben eines Sammlers gleichzeitig.

Beispiel:

Valentin gibt Abderahim:

* 17 × WM26
* 4 × EM24
* 2 × Bundesliga

Abderahim gibt Valentin:

* 8 × WM26
* 7 × Bundesliga 2007
* 5 × EM04
* 3 × anderes Album

Ergebnis:

23 ↔ 23

Völlig legitimer SmartDeal.

Albumgrenzen sind Informationen über Sticker, keine Grenzen eines Tausches.

Grundregel

Albumkontext darf einen Tausch finden, aber niemals einen Tausch künstlich begrenzen.

---

## 4. SmartDeals sind grundsätzlich 1:1

Automatisch erzeugte SmartDeals sind immer mengenmäßig ausgeglichen.

5 ↔ 5

17 ↔ 17

83 ↔ 83

Keine automatische Empfehlung:

30 ↔ 12

Ungleiche Trades bleiben im manuellen Tauschmodus erlaubt.

Damit ist die Trennung klar:

SmartDeal: Sammlr baut einen fairen, optimierten 1:1-Vorschlag.

Manueller Deal: Sammler dürfen jede gewünschte Vereinbarung treffen.

---

## 5. Keine künstliche Maximalgröße

SmartDeal besitzt keine künstliche Obergrenze.

Wenn zwei Sammler sinnvoll:

147 ↔ 147

tauschen können, darf Sammlr genau das vorschlagen.

Große Deals sind ausdrücklich erwünscht.

Sammlr soll nicht aus technischen oder gestalterischen Gründen einen guten großen Deal künstlich zerstückeln.

---

## 6. SmartDeal optimiert global, nicht Partner für Partner

Das ist eine der wichtigsten Regeln.

Sammlr darf nicht einfach für jeden Partner isoliert dessen maximal möglichen Deal berechnen.

Beispiel:

Fatima könnte isoliert:

20 ↔ 20

Mit einer anderen Verteilung könnten aber entstehen:

Fatima 14 ↔ 14
Johann 10 ↔ 10

→ insgesamt 24 neue Sticker

Dann ist die zweite Variante besser.

Sammlr darf einen einzelnen Deal bewusst verkleinern, wenn dadurch der globale Tauschplan besser wird.

---

## 7. Ein SmartDeal-Plan muss gleichzeitig ausführbar sein

Die fünf angezeigten SmartDeals sind keine fünf unabhängigen Fantasien.

Sie bilden gemeinsam einen konsistenten Plan.

Wenn derselbe verfügbare Sticker sowohl von Fatima als auch Johann benötigt wird, darf Sammlr dieses konkrete Exemplar innerhalb des Plans nur einmal vergeben.

Damit gilt:

Alle gleichzeitig dargestellten Top-SmartDeals müssen nebeneinander ausführbar sein.

Das ist ein wesentlicher Unterschied zu einer gewöhnlichen Partner-Rangliste.

---

## 8. Optimierungsreihenfolge

Grundsätzlich will Sammlr möglichst viele echte Lücken schließen.

Gleichzeitig sollen nicht für marginalen Zusatznutzen unnötig viele Briefe entstehen.

Dafür gilt in V1 folgende Produktregel:

Ein zusätzlicher Trade muss mindestens zwei zusätzliche fehlende Sticker bringen.

Beispiel:

20 Sticker / 1 Trade

Gegenüber:

26 Sticker / 4 Trades

Drei zusätzliche Sendungen erzeugen sechs zusätzliche Sticker.

→ ausreichend Mehrwert.

Dagegen:

20 / 1

gegen:

23 / 4

Drei zusätzliche Briefe für nur drei weitere Sticker.

→ der kompaktere Plan wird bevorzugt.

Damit soll SmartDeal weder stumpf maximale Stickerzahl noch stumpf minimale Versandzahl optimieren.

Bei ansonsten gleichwertigen Lösungen

1. weniger Trades bevorzugen
2. größere Einzeldeals bevorzugen
3. deterministischer Tie-Break

Die genaue mathematische Umsetzung wird später separat spezifiziert und getestet.

---

## 9. Top-SmartDeals

Die Hauptansicht zeigt ungefähr:

Deine SmartDeals

maximal 5 Deals.

Ein Deal soll dort grundsätzlich erst ab ungefähr:

5 ↔ 5

erscheinen.

Kleinere Matches sind nicht wertlos.

Sie gehören aber eher in die vollständige Partnersuche und sollen die zentrale SmartDeal-Fläche nicht mit 1 ↔ 1-Kleinkram zuschütten.

---

## 10. Ein Partner, ein SmartDeal

Ein Partner erscheint innerhalb des aktuellen SmartDeal-Plans maximal einmal.

Wenn mit Fatima über fünf Alben getauscht werden kann, baut Sammlr daraus einen gemeinsamen Deal.

Nicht:

Fatima WM26
Fatima EM24
Fatima Bundesliga

sondern:

Fatima

31 ↔ 31

5 Alben

Ein Brief. Ein Partner. Ein Deal.

---

## 11. Vorschlag und Anfrage sind fundamental verschieden

SmartDeal-Vorschlag

Ist nur eine aktuelle Berechnung.

Er:

* reserviert nichts
* verändert keinen Bestand
* erzeugt keinen Trade
* kann nach Bestandsänderungen verschwinden
* wird aus dem aktuellen Zustand berechnet

SmartDeal-Anfrage

Entsteht erst durch:

GO / SmartDeal anfragen

Dann wird aus Mathematik ein echter Vorgang.

Die konkreten Sticker und Mengen werden eingefroren.

---

## 12. SmartDeals sind uneditierbar

Ein SmartDeal ist Sammlrs fertiger Vorschlag.

Der Nutzer kann:

GO

oder nicht.

Er kann nicht einzelne Sticker herauspulen und anschließend weiterhin behaupten, dies sei derselbe optimierte SmartDeal.

Wer selbst zusammenstellen möchte, benutzt den manuellen Deal.

Damit bleiben SmartDeals:

* reproduzierbar
* verständlich
* reservierbar
* testbar
* fair 1:1

---

## 13. Determinismus

Identischer Datenzustand soll denselben optimalen SmartDeal-Plan erzeugen.

Neu berechnen ist kein Spielautomatenknopf.

Wenn sich nichts geändert hat, soll nicht aus Langeweile eine andere Partnerkombination erscheinen.

Bei gleichwertigen Stickeroptionen verwendet V1 eine stabile, deterministische Auswahlregel, beispielsweise kanonische Album-/Stickerreihenfolge.

Die exakte technische Tie-Break-Regel wird später spezifiziert.

---

## 14. Live-Berechnung

SmartDeals sollen auf dem aktuellen kanonischen Zustand basieren.

Relevant sind insbesondere:

* Bestand
* fehlende Sticker
* Doppelte
* Tradepool
* Reservations
* offene Anfragen
* aktive Trades
* Blocks
* Privacy
* Account-/Availability-Regeln

Nach relevanten Änderungen muss der nächste SmartDeal-Plan den neuen Zustand berücksichtigen.

Keine veralteten Matchkarten dürfen weiter ausführbar erscheinen.

---

## 15. Mengen sind echte Mengen

**V1-Präzisierung vom 2026-09-10 (A1):** Das ältere Beispiel „Fatima benötigt ARG17 ×2“ unten gilt nicht für SmartDeal V1. Pro Album/Sticker beträgt Bedarf maximal 1; mehrere verfügbare Geberkopien können verschiedene Partner versorgen. Kein vorsorgliches Mehrfachalbum-Modell. Siehe §37.1.

SmartDeal arbeitet nicht nur mit unterschiedlichen Stickercodes.

Beispiel:

Valentin besitzt ARG17 ×5.

Davon:

* 1 Albumexemplar geschützt
* 4 tauschbar

Benötigt Fatima ARG17 ×2, darf SmartDeal:

ARG17 ×2

verwenden.

Diese beiden Exemplare zählen für einen 1:1-Deal als zwei Sticker.

---

## 16. Das letzte Exemplar bleibt geschützt

Grundsätzlich:

tauschbar = Bestand - geschützter Eigenbedarf - Reservations

Ein Sticker mit Menge 1 ist nicht als Doppelter verfügbar.

Beispiel:

quantity 5

kann bedeuten:

* 1 geschützt
* 2 reserviert
* 2 aktuell verfügbar

Reservations sind deshalb mengenbasiert, nicht bloß ein Boolean reserved=yes.

---

## 17. Anfrage reserviert beide Seiten

Sobald Valentin Fatima einen SmartDeal anfragt, werden die enthaltenen Mengen auf beiden Seiten reserviert.

Das verhindert:

Valentin fragt BRA22 von Fatima an, während Peter denselben konkreten verfügbaren BRA22 gleichzeitig ebenfalls zugesagt bekommt.

Eine offene Anfrage besitzt daher für ihre kurze Lebensdauer echte Availability-Wirkung.

---

## 18. Maximal drei offene eigene SmartDeal-Anfragen

Ein Nutzer darf zunächst maximal:

3 gleichzeitig offene ausgehende SmartDeal-Anfragen

haben.

Nicht drei pro Tag.

Sondern drei gleichzeitig offene.

Sobald eine:

* angenommen
* abgelehnt
* zurückgezogen
* abgelaufen

ist, wird der entsprechende Anfrageplatz wieder frei.

Aktive, bereits angenommene Trades zählen nicht mehr zu diesem Anfrage-Limit.

---

## 19. Anfragefrist

SmartDeal-Anfragen sollen kurzlebig sein.

V1:

24 Stunden

Keine Antwort → Anfrage läuft ab → Reservations werden freigegeben → zukünftige SmartDeals berücksichtigen die Mengen wieder.

Produktgedanke:

Wer einen digitalen Tausch angeboten bekommt, kann innerhalb eines Tages reagieren. Gleichzeitig werden Bestände anderer Nutzer nicht tagelang blockiert.

---

## 20. Gegenseitiges GO

Ein besonders wichtiger Komfortfall:

Sammlr berechnet zwischen Valentin und Fatima denselben gemeinsamen SmartDeal.

Beide können ihn sehen.

Valentin drückt GO.

Normal:

→ Fatima erhält Anfrage
→ Fatima nimmt an
→ Deal geschlossen.

Wenn Fatima denselben SmartDeal ebenfalls bereits aktiv mit GO bestätigt:

Beidseitiges GO = Deal geschlossen.

Keine künstliche Kreuzanfrage und keine zusätzliche Bestätigungsschleife.

---

## 21. Bestandsänderungen bleiben immer erlaubt

Sammlr darf niemals die reale Sammlung als Geisel eines digitalen Trades nehmen.

Valentin kann einen reservierten Sticker trotzdem auf einer realen Börse weggeben und anschließend seinen echten Bestand korrigieren.

Wenn dadurch ein offener Deal nicht mehr erfüllbar ist:

→ Deal/Anfrage wird sichtbar nicht mehr erfüllbar.

Nicht:

→ Bestandsänderung verbieten.

Die reale Sammlung bleibt Wahrheit.

---

## 22. SmartDeals mutieren niemals heimlich

**V1-Präzisierung vom 2026-09-10 (A4):** Die unten beschriebene mögliche spätere Reparatur ist kein V1-Umfang. In V1 wird ein unfulfillable Vorgang beendet, werden Reservations freigegeben und wird die Gegenseite informiert. Der unveränderte alte Vertrag wird nicht repariert; danach vollständige Neuberechnung ohne Wiederherstellungspriorität. Siehe §37.4.

Ein angefragter:

17 ↔ 17

SmartDeal bleibt exakt dieser Vertrag.

Wenn später zwei Sticker fehlen, darf Sammlr daraus nicht still:

15 ↔ 15

machen.

Mögliche spätere Reparatur:

Dieser Tausch ist nicht mehr vollständig erfüllbar.

Tausch anpassen

Sammlr kann daraus einen neuen ausgeglichenen Vorschlag erzeugen, beispielsweise den nicht verfügbaren Sticker entfernen und auf der Gegenseite deterministisch einen entsprechenden Sticker herausnehmen.

Aber:

Das ist ein neuer/angepasster Vertragsstand, den die Gegenseite erneut bestätigen muss.

Keine heimliche Mutation nach GO.

---

## 23. Physische Bestandsbuchung

Sammlr soll möglichst die physische Realität abbilden.

Reservation

Sticker liegt noch bei mir.

→ Bestand physisch vorhanden
→ aber für andere Trades nicht verfügbar.

„Ich habe versendet“

Meine versendeten Sticker verlassen meinen Bestand.

→ aus meinem Bestand ausbuchen.

Partner meldet Versand

Bei meinem Bestand passiert noch nichts.

Der Brief ist unterwegs.

„Erhalten“

Ich bestätige den Eingang.

→ erhaltene Sticker meinem Bestand hinzufügen.

Damit gilt:

Sammlr bucht Papier dann, wenn es meine Sammlung tatsächlich verlässt oder erreicht.

---

## 24. SmartDeals sind Zukunft, laufende Trades sind Realität

Ein angenommener SmartDeal verschwindet aus der SmartDeal-Fläche.

Er ist jetzt ein laufender Trade.

Keine Vermischung von:

* möglichen Deals
* offenen Vorgängen
* bereits laufenden Trades

SmartDeal zeigt, was als Nächstes möglich ist.

Laufende Trades zeigen, was bereits passiert.

---

## 25. Alle Tauschpartner

SmartDeal ersetzt nicht die freie Partnersuche.

Unterhalb bzw. sekundär zur SmartDeal-Fläche gibt es:

Alle Tauschpartner

Dort darf der Nutzer selbst stöbern.

V1 zunächst primär nach möglicher Tauschmenge.

Später sortier-/filterbar nach beispielsweise:

* Menge
* Bewertung
* Entfernung
* Album

---

## 26. Albumfilter findet Menschen, keine isolierten Albumdeals

Wenn Valentin unter WM26 Justus entdeckt:

Justus

12 mögliche Sticker in WM26

Sammlr soll sofort zusätzlich sichtbar machen:

Außerdem Matches in 4 weiteren Alben

beziehungsweise:

31 mögliche Sticker insgesamt · 5 Alben

Beim Öffnen von Justus sieht Valentin die gesamte gemeinsame Tauschlandschaft.

Beispiel:

WM26 · 12
EM24 · 7
Buli19 · 6
VfL · 4
MLB89 · 2

Der Einstieg über WM26 beschränkt den anschließenden Tausch nicht auf WM26.

---

## 27. Manueller Deal

Aus der Partneransicht kann der Nutzer bewusst:

Eigenen Tausch zusammenstellen

Der manuelle Composer darf:

* albumübergreifend arbeiten
* ungleiche Trades erlauben
* vom Nutzer frei zusammengestellt werden

Visuell soll er später die digitale Stickerwall-Grammatik verwenden.

Explizit:

keine CEOKlaue.

CEOKlaue gehört zur physischen Stickerliste.

---

## 28. Die normale SmartDeal-Reise

Der Idealweg soll extrem kurz sein:

1. Deal gefunden

Sammlr zeigt einen SmartDeal.

2. GO

Nutzer prüft bei Bedarf das Paket und fragt an.

3. Gegenseite GO

Deal steht.

4. Brief packen

Sammlr sagt konkret:

Pack diese Sticker in einen Umschlag:

Sticker X
Sticker Y
Sticker Z

5. Versand

Freigegebene Versanddaten des konkreten Partners.

6. Versendet

Eigene Sticker aus Bestand.

7. Erhalten

Neue Sticker in Bestand.

8. Fertig

Trade in Verlauf.

Produktmantra:

Deal gefunden → Go → Brief packen.

Wenn der normale Tausch wieder fünf Unterseiten und drei Zwischenbestätigungen braucht, ist die Informationsarchitektur falsch.

---

## 29. Versand & Kontakt

**V1-Präzisierung vom 2026-09-10 (A3):** Konkrete Trade-Freigabe und optionales Speichern der Adresse sind entschieden. Ein minimaler Nachrichtenbereich ausschließlich an bestätigten Trades ist als V1-Option zulässig, aber nicht verpflichtend und hier nicht zur Implementierung freigegeben. Siehe §37.3.

Ein Sammlr-Chat ist für Closed Beta nicht notwendig.

Der Trade muss trotzdem vollständig durchführbar sein.

V1-Richtung:

Versandadresse freigeben

Nicht beim Signup erzwingen.

Nicht öffentlich im Profil.

Nicht öffentlich über APIs/Views projizieren.

Nur für den notwendigen Versandkontext und den konkreten bestätigten Tradepartner.

Optional später beziehungsweise ergänzend:

* Telegram
* weitere Kontaktmöglichkeiten

Telegram darf niemals Voraussetzung für einen Sammlr-Trade sein.

---

## 30. Laufende Trades

Laufende Trades sollen einfach einsehbar sein.

Der Nutzer interessiert sich primär für:

Was muss ich jetzt tun?

Beispiele:

Fatima · 17 ↔ 17
📦 Du musst versenden

Johann · 12 ↔ 12
🚚 Unterwegs zu dir

Justus · 31 ↔ 31
✓ Warte auf Empfangsbestätigung

Die normale Aktion soll möglichst direkt erreichbar sein.

Trade Detail bleibt sinnvoll für:

* vollständige Inhalte
* Timeline
* Probleme
* Historie
* Sonderfälle

Aber nicht als Zwangsstation für jeden normalen Klick.

---

## 31. Verlauf

Abgeschlossene Trades sind wichtig, aber nicht die Hauptattraktion.

Ein einfacher:

Verlauf

reicht zunächst.

Dort können abgeschlossene Tausche nachvollzogen werden.

Der aktive Produktfokus liegt auf:

neuen SmartDeals und laufenden Trades.

---

## 32. SmartDeal braucht eine eigene visuelle Identität

SmartDeal soll nicht einfach eine weitere lila Dashboardkarte werden.

Sammlr besitzt inzwischen unterschiedliche physische/digitale Produktobjekte:

* Stickerwall
* CEOKlaue-Stickerliste
* 70er-Profilsticker
* künftig SmartDeal

SmartDeal braucht ebenfalls einen wiedererkennbaren Banger.

Noch keine Gestaltung festlegen.

Denkbare Richtung:

Ein visuelles Tauschobjekt, bei dem zwei Sammler und der Deal unmittelbar als zusammengehörig verstanden werden.

Ziel:

Nutzer sieht die Karte und denkt sofort:
„Sammlr hat mir einen Deal gebaut.“

Nicht:

„Hier ist noch ein Dashboard-Widget.“

---

## 33. Was V1 ausdrücklich NICHT braucht

**V1-Präzisierung vom 2026-09-10 (A3):** „Kein eigener Chat“ unten ist kein Ausschluss der jetzt zulässigen minimalen tradegebundenen Nachrichtenoption. Allgemeiner Messenger/DM/Social-Chat ist damit nicht autorisiert. Siehe §37.3.

Keine künstliche Albumpriorisierung.

Kein komplizierter SmartScore für Nutzer.

Keine Seltenheitsgewichtung.

Keine KI-Erklärung.

Keine editierbaren SmartDeals.

Kein verpflichtendes Telegram.

Kein eigener Chat.

Keine riesige Trade-Historienwelt.

Keine getrennten parallelen Tradeuniversen pro Album.

Keine fünf Haupttabs für verschiedene Lifecycle-Zustände.

Keine künstliche maximale Dealgröße.

---

## 34. Noch offene technische Spezifikation

**V1-Präzisierung vom 2026-09-10 (A1/A2/A4):** Mehrfachbedarf pro Album gehört nicht zu V1; Altvorgänge behalten ihren Vertrag; „Unfulfillable-Reparatur“ unten entfällt aus dem V1-Umfang. Zu spezifizieren ist stattdessen Beenden/Freigeben/Informieren und unabhängige Neuberechnung. Siehe §37.

Die Product Bible legt die Semantik fest, aber noch nicht den Algorithmuscode.

Vor Implementierung müssen wir insbesondere technisch beweisen/definieren:

* globale Optimierung über mehrere Partner
* Mengenmodell
* deterministische Paketbildung
* Versandkostenregel +1 Trade benötigt ≥ +2 Sticker
* Top-5-Auswahl
* Mindestgröße 5 ↔ 5
* simultan ausführbare Pläne
* identische gegenseitige SmartDeals
* atomare beidseitige Reservation
* Race Conditions bei gleichzeitigem GO
* 24h Expiry
* Drei-Anfragen-Limit
* bestehende Availability-/Reservation-Verträge
* bestehende Trade-Lifecycle-Kompatibilität
* Unfulfillable-Reparatur
* Performance bei realistischen Nutzer-/Albumzahlen

Diese Punkte dürfen nicht durch improvisierte UI-Logik gelöst werden.

---

## 35. Was wir ausdrücklich noch NICHT tun

Noch keine bestehenden Trade-Routen löschen.

Noch keine Tabs entfernen.

Noch keine DB-Migration.

Noch keine SmartMatch-Implementierung ersetzen.

Noch keine Navigation umbauen.

Noch keine bestehende Trade-Logik „vereinfachen“.

Erst vergleichen wir diesen Produktvertrag mit dem tatsächlichen System.

---

## 36. Nächster Schritt

Jetzt würde ich keinen weiteren Fragenhagel machen.

Der nächste Schritt sollte ein technischer IST-Audit gegen diese Bible sein:

Was von SmartDeal V1 kann unser bestehendes Sammlr heute bereits?

Dann entsteht eine Matrix:

V1-Anforderung | heute vorhanden | teilweise | fehlt | bestehender Code/Route | wiederverwendbar | Konflikt

Insbesondere dürften wir feststellen, dass wir schon sehr viel besitzen:

Reservations, Availability, Requests, Notifications, Trade Lifecycle, Unfulfillable, Bestandsanpassung, Partnerermittlung, SmartMatch-Grundlagen.

---

## Dokumenteinordnung und geschützte bestehende Verträge

Diese Product Bible ist das kanonische SOLL-Produktdokument und ein eigener Produktvertrag. Sie beschreibt nicht automatisch den aktuellen IST-Zustand des Codes. Bestehende Implementierung ist bei Widersprüchen nicht stillschweigend maßgeblich; die bestehende Trade-Infrastruktur ist zugleich nicht pauschal veraltet oder zu verwerfen.

Bestehende Verträge für Inventory, Availability, Reservations, Trade Requests, Trade Lifecycle, Notifications, Privacy, Blocks, Unfulfillable States, Bestandsanpassungen und Trade History bleiben zunächst geschützt und werden später gegen diese Bible geprüft.

Die ungefähren Richtwerte der Top-Ansicht und Mindestgröße, die V1-Richtung sowie ausdrücklich offene Entscheidungen behalten ihren jeweiligen Status. Dieser Dokumentationsauftrag legt keine technischen Lösungen, kein Design und keinen freigegebenen SOLL-Routenbaum fest.

## Separater Folgeauftrag: SMARTDEAL V1 IST-AUDIT

Der nächste technische Schritt ist **nicht die Implementierung**, sondern ein separater **SMARTDEAL V1 IST-AUDIT**. Dieser Audit wurde mit dem Ablegen des Dokuments nicht begonnen.

Der bestehende Sammlr-Code soll systematisch gegen die Product Bible verglichen werden. Erwartete Matrix:

| V1-Anforderung | IST vorhanden | Status | bestehender Code/Service/Route | wiederverwendbar | Konflikt/Lücke |
| --- | --- | --- | --- | --- | --- |

Dabei insbesondere untersuchen:

- bestehende SmartMatch-Logik
- Partnerermittlung
- Availability
- mengenbasierte Availability
- Reservations
- Reservation-Zeitpunkte
- Request Lifecycle
- Drei-Anfragen-Limit, falls vorhanden
- Expiry
- gegenseitige Requests
- Race Conditions
- Inventory-Buchung
- shipped/received-Semantik
- Unfulfillable
- Privacy
- Blocks
- Tradepool
- Notifications
- manueller Composer
- globale vs albumbezogene Trade-Routen
- Trade Detail
- laufende Trades
- Historie

Zusätzlich wird später ein separater Route-/Information-Architecture-Audit benötigt.

Erst danach:

IST → Gap-Analyse → technischer Algorithmusvertrag → SOLL-Navigation → Implementierungspakete

## R5 / Release-Scope und Umsetzungsgrenze

Diese Bible ist Produktdokumentation und verändert den aktuellen R5-Releaseprozess nicht. R5 B1/B1.1/B1.2 wurden separat behandelt. Keine Vermischung des zukünftigen SmartDeal-Umbaus mit dem bestehenden Release-Candidate-Prozess ohne ausdrückliche PO-Anweisung.

Das Ablegen autorisiert keine Featureimplementierung und keine Änderungen an Runtime, UI/CSS/JS, Datenbank, Schema, Indizes, Performance, Routen, Navigation oder bestehender Trade-Semantik. Kein bestehendes Trade-Feature entfernen; keine vorhandene Route aufgrund dieser Bible als obsolet markieren oder löschen. Noch existiert kein freigegebener SOLL-Routenbaum.


## 37. PO-Entscheidungen vom 2026-09-10

Diese fünf Entscheidungen ergänzen den Produktvertrag. Sie ändern weder den aktuellen Code noch rückwirkend alte Requests/Trades. Das [IST-Audit vom 2026-09-09](SMARTDEAL_V1_IST_AUDIT.md) bleibt als historische Codeanalyse unverändert; seine damaligen offenen Fragen sind anhand dieses Nachtrags neu einzuordnen.

### 37.1 A1 – Mehrfachbedarf

Ein einzelnes Album benötigt einen konkreten Sticker maximal einmal. Für SmartDeal V1 ist der Bedarf pro Album/Sticker deshalb 0 oder 1, niemals größer als 1. Mehrfachmengen betreffen die Bestands-/Geberseite: Bei ARG17 quantity=5 können nach Eigenbedarf und Reservations mehrere Exemplare tauschbar sein. Diese können jeweils den Bedarf verschiedener Sammler erfüllen.

Ein zukünftiges Feature mit mehreren Exemplaren desselben Albums könnte Mehrfachbedarf schaffen. Dieses Mehrfachalbum-Modell gehört ausdrücklich nicht zu V1; SmartDeal V1 wird dafür nicht vorsorglich erweitert. Das ältere Bedarf-×2-Beispiel in §15 ist für V1 überholt.

### 37.2 A2 – Altvorgänge

Bestehende Requests und Trades behalten ihren bisherigen Vertrag. SmartDeal V1 gilt nur für neu erzeugte SmartDeal-V1-Vorgänge. Historische oder laufende Verträge werden weder rückwirkend geändert noch auf neue Semantik migriert. Sie müssen nach ihrer bisherigen Semantik abschließbar bleiben. Eine spätere technische Unterscheidung darf keine automatische Altvertragsumstellung bedeuten; keine Schemaentscheidung in diesem Nachtrag.

### 37.3 A3 – Versandkontakt, Adresse und optionale Nachrichten

Nach beidseitiger Annahme wird ein geschützter Kontakt-/Versandweg benötigt. Eine Versandadresse kann für den konkreten bestätigten Trade eingegeben beziehungsweise freigegeben werden. Bei der Eingabe soll optional gefragt werden, ob Sammlr sie für zukünftige bestätigte Trades speichern darf.

Speichern ist keine Veröffentlichung und keine automatische Partnerfreigabe. Eine gespeicherte Adresse darf nur für Versandzwecke im Zusammenhang mit bestätigten Trades und nach kontrollierter Freigabe gegenüber dem konkreten Tradepartner sichtbar werden. Bei späteren Trades kann sie erneut verwendet werden; die Freigabe für diesen Partner muss erneut kontrolliert erfolgen. Privacy-Texte erklären ausdrücklich: **nicht öffentlich; ausschließlich für Versandzwecke; nur für bestätigte Tradepartner nach Freigabe**. Keine Pflicht zur Adressangabe beim Signup; keine öffentliche Profil-/API-/View-Projektion.

Ein minimaler tradegebundener Nachrichtenbereich ist als V1-Produktoption zulässig und ausdrücklich nicht mehr ausgeschlossen. Er wäre erst nach Annahme an genau einem bestätigten Trade verfügbar, für kurze Versandhinweise, Adresse, Rückfragen oder „geht morgen raus“. Er ist kein öffentlicher Messenger, keine allgemeine DM-Funktion und keine Social-Chat-Plattform. Die Zulässigkeit ist kein Pflichtfeature und kein Chat-Implementierungsauftrag. Telegram bleibt optional, niemals Voraussetzung.

### 37.4 A4 – Unfulfillable beendet den Vorgang

Für V1 wird kein Reparatureditor gebaut. Wird ein bereits angefragter oder gebundener SmartDeal durch reale Bestandsänderung unerfüllbar und hat **noch keine Seite versendet**, gilt:

1. Vorgang sichtbar als unfulfillable / nicht mehr möglich kennzeichnen.
2. Deal beenden.
3. Reservations freigeben.
4. Gegenseite informieren.
5. Alten Vertrag unverändert erhalten.

Keine Sticker automatisch entfernen, kein Neu-Ausbalancieren im alten Vertrag und keine erneute Annahme einer reparierten Version. SmartDeals werden aus dem aktuellen Zustand vollständig neu berechnet. Der frühere Partner kann wieder zu den besten Möglichkeiten gehören oder vollständig verschwinden; der alte Deal besitzt keinen Anspruch auf bevorzugte Wiederherstellung. Reale Bestandskorrekturen bleiben erlaubt. Die physische Buchungssemantik aus §23 bleibt maßgeblich.

### 37.5 A5 – Top-N

Die Produktformulierung bleibt **maximal ungefähr fünf Top-SmartDeals**. „Top 3“ in einer späteren Diskussion war lediglich umgangssprachlich „unter den besten Deals“, kein neuer Produktvertrag. Keine Änderung auf Top 3. Die technischen Top-Plan-Grenzen werden im gesondert beauftragten Algorithm Contract festgehalten; das Drei-Limit offener eigener ausgehender Anfragen ist davon unabhängig.

## 38. PO-Präzisierungen zum Algorithm Contract vom 2026-09-10

Diese nachgereichten Entscheidungen präzisieren die zuvor nicht eindeutigen Grenzen; sie gelten nur für SmartDeal V1.

1. **Exakte Versandschwelle (§8):** Mindestens zwei zusätzliche fehlende Sticker je zusätzlichem Trade genügen. Bei exakt erreichter Schwelle gewinnt der höhere Gesamtgewinn: 26/4 vor 20/1 und 41/5 vor 35/2. Der verbindliche Comparator steht in Algorithm Contract AC11/12.
2. **Zugesagter Eingang (§14):** Physisch fehlender, aber durch gültige Bindung bereits zugesagter Eingang ist kein freier Need für neue SmartDeals. Das umfasst offene beidseitig reservierte V1-Anfragen und gültige angenommene/aktive Zusagen einschließlich Transit. Ablehnung, Rückzug, Ablauf oder Vorversand-Unfulfillable geben weiterhin physisch fehlenden Bedarf frei; Receipt erfüllt ihn physisch. Tatsächliche Legacy-Bindungswirkungen bleiben maßgeblich.
3. **Rangänderung:** Ein zuvor angezeigtes exaktes Paket darf trotz Platz 4 → 6 per GO angefragt werden, wenn alle harten Vertragsinvarianten atomar gültig sind. Aktuelle Top-5-Zugehörigkeit ist keine GO-Voraussetzung.
4. **Teilversand (§37.4):** Sobald mindestens eine Seite versendet hat, ist die gewöhnliche automatische Unfulfillable-Beendigung ausgeschlossen. Sichtbarer Problem-/Action-required-Flow mit menschlicher Klärung; kein fiktiver Inventory-, Reservations- oder Lifecycle-Reset, keine Paketmutation und kein Reparatureditor. Tatsächlicher Versand und History bleiben erhalten.
5. **Quote (§18):** Maximal drei offene ausgehende Anfragen zählt ausschließlich SmartDeal V1. Legacy-/Altvorgänge und manuelle Trades zählen nicht; ihre tatsächlichen Availability-/Reservationseffekte werden dennoch berücksichtigt.

## 39. Night-Prep: gezielte Vertragspräzisierungen

Verbindliche PO-Entscheidungen: [Q1–Q8 Decision Record](TRADE_UX_PO_DECISIONS_Q1_Q8.md).

- **Manuell (§4/27):** Für neu erzeugte manuelle V1-Angebote gilt Initiator gibt mindestens so viel wie er erhält, mit mindestens einem Piece je Richtung. Die ältere Formulierung „jede gewünschte Vereinbarung“ bleibt keine Ausnahme für neue manuelle V1-Angebote; geschützte Legacy-Verträge bleiben unverändert. Eigener Manual Offer Contract, nicht SmartDeal V1.
- **Physischer Empfang (§23):** Empfang darf trotz fehlendem vorherigem Versandklick bestätigt werden. Kein historischer Versandzeitpunkt wird erfunden; Empfangszeit und notwendige physische Buchungen genau einmal. Teil-/Fehlempfang und Retry bleiben geschützt; technische Umsetzung T7a.

Keine Änderung an AC25/26: nachträgliches Ausbalancieren ist durch Q1 ausdrücklich verworfen. Globale SmartDeal-Optimierung unverändert. Keine Runtime-/Schema-/Teständerung.
