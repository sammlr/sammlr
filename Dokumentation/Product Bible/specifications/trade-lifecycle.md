# Bereich 02A: Tradezentrale / Dealabwicklung

| Metadatum | Wert |
| --- | --- |
| Status | Working Product Specification |
| Bereich | Tradezentrale / Dealabwicklung |
| Stand | 2026-07-27 |
| Änderungshinweis | Änderungen nur bewusst nach neuer Produktentscheidung vornehmen. |

## Dokumentcharakter

Dieses Dokument ist ein langfristiges Produkt-/Lastenheft. Es ist ausdrücklich keine kurzfristige Codex-Todo-Liste und keine Aussage darüber, welche beschriebenen Funktionen bereits implementiert sind. Vor technischer Umsetzung müssen Trade- und Bestandsarchitektur gesondert gegen diese Soll-Spezifikation geprüft werden.

Das am Ende archivierte Produktprotokoll ist vollständig und inhaltlich unverändert übernommen. Die folgende Statusmatrix dient ausschließlich der eindeutigen Auslegung seiner Aussagen.

## BESCHLOSSEN / KERNLOGIK

Als langfristige Produktprinzipien und Kernarchitektur beschlossen sind insbesondere:

- Albumbezogene Tauschbereiche helfen, Deals zu finden; die globale Tradezentrale wickelt entstandene Deals albumübergreifend ab.
- Eine Anfrage ist noch kein Deal und reserviert keine Sticker. Erst die Annahme erzeugt einen verbindlichen Deal und Reservierungen.
- Abgelehnte und unbeantwortet verfallene Anfragen sind keine fehlgeschlagenen oder abgeschlossenen Trades.
- Angenommene Deals werden nicht beiläufig folgenlos abgebrochen; Probleme und gescheiterte Abwicklungen bleiben nachvollziehbar.
- Dealänderungen müssen transparent erklärt werden.
- Beide Seiten besitzen getrennte Versand- und Empfangszustände.
- Eingehende Sticker werden bei Annahme oder Versand noch nicht als physisch vorhanden gebucht; der reale Zugang wird erst bei bestätigtem Empfang gebucht.
- Ein Deal ist regulär erst abgeschlossen, wenn die erfolgreiche Abwicklung auf beiden Seiten bestätigt wurde.
- Teilempfang und Problemfälle dürfen die physische Realität nicht durch einen künstlichen Gesamtstatus überschreiben.
- Jeder angenommene Deal erhält einen zweckgebundenen, dauerhaft am Deal nachvollziehbaren Chat mit Text, Bildern und Systemmeldungen.
- Die normale Tradehistorie enthält erfolgreich abgeschlossene Trades; problematische angenommene Deals bleiben gesondert nachvollziehbar.
- Bewertungen werden erst nach tatsächlicher Abwicklung beziehungsweise Empfang ermöglicht, nicht bereits nach Versand und niemals nach bloßer Anfrage oder Ablehnung.
- Home zeigt nur aktuelle Hinweise und Handlungen; die vollständige Dealverwaltung bleibt in der Tradezentrale.
- Sammlung, Smart-Trade-Engine und Tradezentrale müssen ein gemeinsames konsistentes Modell für freien, reservierten, versendeten, unterwegs befindlichen und empfangenen Bestand verwenden.

Diese Festlegungen beschreiben die Zielarchitektur. Sie gelten nicht automatisch als bereits implementiert.

## NOCH ZU ENTSCHEIDEN

Bewusst offen sind:

- exakte Anfrage-Lebensdauer innerhalb des Rahmens von ein bis zwei Tagen,
- exakte Definition der fünf Werktage und Feiertagslogik,
- genaue Überfälligkeitseskalation und operative Sortierung,
- Problemfall- und Teilempfangs-UX,
- genaue Bewertungsgründe und öffentliche Bewertungsdarstellung,
- Bildspeicherung im Dealchat,
- strukturierte Adressdaten,
- Streitfall-, Support-, Missbrauchs- und Sperrlogik,
- rechtliche Rolle, Haftung, Datenschutz und Plattformregeln.

Offene Punkte dürfen nicht beiläufig durch eine Implementierung als endgültige Produktentscheidung festgeschrieben werden.

## SPÄTER / VISION

Ausdrücklich keine aktuelle Implementierungsanforderung sind insbesondere:

- integrierte oder anonymisierte Versandlabels und Versanddaten,
- Versandtracking und Versandversicherung,
- Sammlr-Versandprodukte und integrierte Versandservices,
- regionale Tausch- und Übergabefunktionen,
- QR- beziehungsweise Börsenmodus,
- ein komplexes Streitfall- oder Schiedsgerichtssystem.

Diese Themen bleiben Teil des langfristigen Zielbilds, sind aber keine unmittelbar freigegebenen MVP-Aufgaben.

## Abgleich mit bestehender Dokumentation

Die Spezifikation [`trading.md`](trading.md) bleibt maßgeblich für die Frage, wie Smart Matches berechnet, ausgewählt und zu Anfragen werden. Das vorliegende Dokument ist für die globale Abwicklung ab Anfrage beziehungsweise verbindlicher Annahme maßgeblich.

Beide Dokumente stimmen bei Anfrage, Reservierung, Versandfrist, getrennten Versandzuständen, Empfang, Bestandstrennung, Historie und Problemfällen grundsätzlich überein. Ein ausdrücklicher Widerspruch besteht beim Bewertungszeitpunkt: Abschnitt 20 des älteren Originalprotokolls in `trading.md` ermöglicht Bewertungen bereits nach beidseitiger Versandbestätigung. Diese speziellere Folgespezifikation vom 2026-07-27 ermöglicht sie erst nach tatsächlicher Abwicklung beziehungsweise Empfang. Für den Trade Lifecycle gilt die neue Regel; das ältere Original bleibt als historischer Stand sichtbar.

Die Spezifikation [`collection.md`](collection.md) bleibt maßgeblich für das Bestandsmodell und die Darstellung von „unterwegs“ in der Stickerverwaltung. Dieses Dokument definiert, durch welche Dealereignisse Reservierung, Versand, Unterwegs- und Empfangszustände ausgelöst werden.

Beim Begriff „fehlend“ besteht eine ältere terminologische Spannung: Das Originalprotokoll in `trading.md` bezeichnet einen unterwegs befindlichen Sticker als weder fehlend noch vorhanden. Die neuere Sammlungsspezifikation präzisiert: Er ist physisch noch fehlend und darf im Filter „Fehlende“ markiert sichtbar sein, wird aber aus neuem Smart-Trade-Bedarf herausgerechnet. Für Bestandsmodell und Stickerwall gilt die Sammlungsspezifikation; die grundlegende Aussage beider Dokumente bleibt gleich: „unterwegs“ ist ein eigener Zustand und noch kein physischer Bestand.

Die Spezifikation [`home.md`](home.md) bleibt maßgeblich für Benachrichtigungen und operative Hinweise auf Home. Dieses Dokument definiert die zugrunde liegenden Tradeereignisse und die vollständige Detailverwaltung.

Die Spezifikation [`profile-community.md`](profile-community.md) bleibt maßgeblich für die öffentliche Darstellung von Bewertung und Zuverlässigkeit. Dieses Dokument definiert, wann ein Deal für Bewertung und Historie qualifiziert ist.

Die Spezifikation [`navigation-information-architecture.md`](navigation-information-architecture.md) ordnet die globale Tradezentrale dem rechten Hauptbereich „Tauschen“ zu. Home- und Benachrichtigungseinstiege führen per Deep Link in denselben konkreten Deal und erzeugen keine getrennte Dealverwaltung.

---

## Archiviertes Originalprotokoll – vollständig und unverändert

SAMMLR PRODUCT SPECIFICATION
BEREICH: TRADEZENTRALE / DEALABWICKLUNG
Stand: 2026-07-27
Status: Working Product Specification
============================================================


1. ZWECK DER TRADEZENTRALE

Die Tradezentrale ist der zentrale operative Bereich für bereits entstandene und globale Trades.

Sie ist NICHT identisch mit:

- der albumbezogenen Tauschbörse
- Smart-Match-Suche innerhalb eines Albums
- der Home-/Startseite
- der Sammlr-Zentrale

Grundprinzip:

Albumbezogene Bereiche helfen dabei, einen Deal zu FINDEN.

Die Tradezentrale hilft dabei, einen entstandenen Deal ABZUWICKELN.


2. TRENNUNG ALBUMTAUSCH UND TRADEZENTRALE

Innerhalb eines konkreten Albums darf weiterhin lokal nach Tauschmöglichkeiten gesucht werden.

Beispiel:

WM26
→ Tauschbörse
→ passende Sammler
→ einzelne Sticker suchen
→ albumbezogene Smart Matches
→ Deal starten

Sobald daraus ein konkreter Deal entstanden ist, gehört dieser Deal jedoch in die globale Tradezentrale.

Der Nutzer soll seine laufenden Deals nicht über verschiedene Albumseiten zusammensuchen müssen.


3. GLOBALE FUNKTIONEN DER TRADEZENTRALE

Die Tradezentrale beherbergt insbesondere:

- globale / albumübergreifende Smart Trades
- allgemeine Partnersuche
- Tradeanfragen
- laufende Deals
- Dealabwicklung
- Dealchat
- Versandstatus
- Empfangsstatus
- Problemfälle
- abgeschlossene Trades
- Tradehistorie
- Bewertungen

Damit ist die Tradezentrale das operative Hauptquartier des Tauschsystems.


4. „MEINE DEALS“ IST ALBUMÜBERGREIFEND

Alle entstandenen Deals werden zentral verwaltet.

Dabei ist unerheblich, ob ein Deal ursprünglich entstanden ist über:

- WM26
- VfL
- ein anderes Album
- einen manuellen Stickerdeal
- Smart Match
- einen albumübergreifenden Smart Trade
- später eine Börsenfunktion

Ein entstandener Deal gehört anschließend in „Meine Deals“.


5. GRUNDLEBENSZYKLUS EINES DEALS

Der grundsätzliche Deal-Lebenszyklus lautet:

Anfrage
→ angenommen
→ Sticker reserviert
→ gegebenenfalls automatisch angepasst
→ Versandvorbereitung / Dealchat
→ versendet
→ unterwegs
→ Empfang pro Seite
→ gegebenenfalls Teilempfang / Problem
→ abgeschlossen
→ Bewertung
→ Historie

Die technische State-Machine wird vor Implementierung separat aus diesem Produktmodell abgeleitet.


6. TRADEANFRAGE

Eine Tradeanfrage ist noch kein verbindlich abgeschlossener Deal.

Der Empfänger kann sie:

- annehmen
- ablehnen
- auslaufen lassen

Solange sie nicht angenommen wurde, gelten die Regeln für offene Anfragen.


7. LEBENSDAUER EINER ANFRAGE

Tradeanfragen sollen bewusst kurzlebig sein.

Aktuelle Produktrichtung:

ca. 1–2 Tage maximale Lebensdauer.

Danach verfällt eine unbeantwortete Anfrage automatisch.

Grund:

Tauschbestände verändern sich schnell.

Wochenlang offene Anfragen würden Bestände, Smart Matches und Nutzererwartungen unnötig blockieren.


8. VERFALLENE ANFRAGEN

Eine lediglich verfallene Anfrage gilt nicht als fehlgeschlagener Trade.

Sie soll:

- nicht als negativer Deal gewertet werden
- nicht in normale Tradehistorie eingehen
- keine negative Statistik erzeugen

Sie darf gegebenenfalls technisch bzw. in einer erweiterten Benachrichtigungsansicht noch nachvollziehbar sein.


9. ABGELEHNTE ANFRAGEN

Auch eine abgelehnte Anfrage ist kein fehlgeschlagener Deal.

Beim Ablehnen darf Sammlr nach einem Grund fragen, um Produktlogik und Matching langfristig zu verbessern.

Beispielhafte Gründe können später definiert werden.

Ablehnung allein führt nicht zu einer negativen Nutzerbewertung.


10. ANNAHME MACHT DEN DEAL VERBINDLICH

Mit Annahme der Anfrage entsteht ein verbindlicher Deal zwischen den beteiligten Nutzern.

Ab diesem Moment:

- enthaltene Sticker werden reserviert
- der Deal erscheint unter offenen Trades
- die Versand-/Abwicklungsfrist beginnt
- andere Smart Trades müssen die Reservierungen berücksichtigen
- die beteiligten Nutzer erhalten Zugriff auf die Dealabwicklung


11. RESERVIERUNG

Sticker eines angenommenen Deals dürfen nicht gleichzeitig für weitere Deals als frei verfügbar behandelt werden.

Beispiel:

Nutzer besitzt GER20 dreimal.

1 Exemplar ist einem Album zugeordnet.
1 Exemplar ist für einen angenommenen Deal reserviert.
1 Exemplar ist frei.

Smart Trades dürfen nur mit dem tatsächlich freien Exemplar rechnen.


12. AUTOMATISCHE DEALANPASSUNG

Smart-Trade-Pakete können sich vor endgültiger Annahme bzw. entsprechend der bereits definierten Smart-Trade-Regeln verkleinern, wenn einzelne Sticker zwischenzeitlich anderweitig gebunden wurden.

Beispiel:

ursprünglicher Smart Match:
45 ↔ 45

später noch möglich:
39 ↔ 39

Die Tradezentrale muss solche Anpassungen transparent darstellen.

Sinngemäß:

„Deal angepasst“
„Ursprünglich 45 · aktuell 39“

Die exakte Formulierung wird später im UX-Wording festgelegt.


13. KEINE HEIMLICHEN DEALÄNDERUNGEN

Der Nutzer muss nachvollziehen können, warum ein vorgeschlagener oder laufender Deal eine andere Größe besitzt als ursprünglich.

Sammlr darf Dealpakete gemäß den definierten Regeln automatisch optimieren.

Sammlr darf dabei jedoch nicht den Eindruck erzeugen, Sticker seien ohne Erklärung verschwunden.


14. VERSANDFRIST

Nach Annahme eines Versanddeals erhalten beide Nutzer eine klar definierte Versandfrist.

Aktuelle Produktrichtung:

5 Werktage.

Die Frist beginnt mit dem verbindlichen Dealabschluss / der Annahme.


15. FRIST MUSS VORHER KOMMUNIZIERT WERDEN

Vor Abschluss eines Deals muss klar sein, dass der Deal innerhalb der vorgesehenen Frist durchgeführt werden soll.

Ziel:

Niemand soll einen Deal annehmen und erst danach erfahren, dass zeitnah versendet werden muss.


16. HOME-ERINNERUNGEN ZUM VERSAND

Die Home-/Startseite darf wichtige operative Erinnerungen aus laufenden Trades hervorheben.

Beispiele:

„Noch 4 Tage zum Versenden.“

„Noch 2 Tage: Deal mit Ralli versenden.“

„Versand heute fällig.“

Home dient dabei als Aufmerksamkeitsfläche.

Die eigentliche Detailverwaltung bleibt in der Tradezentrale.


17. FRISTÜBERSCHREITUNG

Nach Ablauf der Versandfrist soll ein Deal nicht automatisch blind gelöscht oder als gescheitert verbucht werden.

Grund:

Ein Nutzer könnte bereits versendet haben und lediglich vergessen haben, dies in Sammlr zu markieren.

Stattdessen soll der Deal zunächst als:

„überfällig“

bzw. entsprechend gekennzeichnet werden.

Weitere Eskalationslogik wird später definiert.


18. KEIN EINFACHES ABBRECHEN NACH ANNAHME

Eine unverbindliche Anfrage kann abgelehnt werden.

Ein angenommener Deal soll dagegen nicht über einen beiläufigen „Abbrechen“-Button folgenlos aufgelöst werden können.

Nach Annahme ist der Deal verbindlich.

Wenn er anschließend nicht durchgeführt werden kann, handelt es sich um einen Problem-/Abbruchfall.


19. PROBLEMFALL NACH ANNAHME

Für angenommene Deals muss langfristig eine Möglichkeit existieren, Probleme zu melden.

Beispiele:

- Tauschpartner versendet nicht
- Sticker fehlen
- falsche Sticker
- Sendung beschädigt
- Sendung verloren
- Deal konnte aus anderem Grund nicht durchgeführt werden

Dies ist etwas anderes als eine abgelehnte Anfrage.


20. SAMMLR ORGANISIERT DEN DEAL

Grundsätzliche Produktposition für die frühe Phase:

Sammlr organisiert und dokumentiert den Tausch.

Der physische Versand bzw. die persönliche Übergabe findet zwischen den Nutzern statt.

Sammlr ist zunächst nicht selbst Versanddienstleister, Versicherer oder Garant des physischen Tauschs.

Rechtliche Texte und Haftungsfragen müssen vor öffentlicher Skalierung gesondert professionell geprüft werden.


21. ZUKÜNFTIGE VERSANDSERVICES

Langfristig denkbar:

- Sammlr-Versandlabels
- anonymisierte Versandlabels
- versicherter Versand
- integrierte Versandservices
- Versandtracking
- Sammlr-Versandverpackungen

Diese Punkte sind Zukunftsthemen und kein Bestandteil der aktuellen Dealabwicklung.


22. DEALCHAT

Jeder angenommene Deal erhält einen eigenen, an diesen Deal gebundenen Chat.

Der Chat dient der konkreten Abwicklung.

Beispiele:

- Adresse austauschen
- Versandart klären
- persönliche Übergabe vereinbaren
- Rückfragen zu Stickern
- Versand bestätigen / besprechen
- Problem dokumentieren


23. CHAT BLEIBT AM DEAL

Der Dealchat ist kein allgemeiner Messenger.

Er gehört zum jeweiligen Deal.

Nach Abschluss soll der Chat weiterhin mit diesem Deal einsehbar bleiben, damit Absprachen später nachvollzogen werden können.


24. TEXT UND BILDER

Der Dealchat soll mindestens unterstützen:

- Text
- Bilder

Bilder sind ausdrücklich sinnvoll.

Beispiele:

- Sticker vor Versand zeigen
- Zustand dokumentieren
- gepackten Umschlag zeigen
- Verpackung dokumentieren
- bei Problemen beschädigte Sendung zeigen

Nicht notwendig für die erste Version:

- Sprachnachrichten
- GIF-System
- Social-Media-Messenger-Funktionen
- unnötige Chat-Spielereien

Der Chat bleibt zweckgebunden.


25. ADRESSAUSTAUSCH

Für die erste Produktstufe ist keine komplexe zentrale Adressdatenbank zwingend erforderlich.

Die Nutzer können Versanddaten zunächst im Dealchat austauschen.

Später können strukturierte Versanddaten bzw. Versandlabels ergänzt werden.

Datenschutz und Speicherung personenbezogener Versanddaten müssen vor einer solchen Erweiterung gesondert betrachtet werden.


26. SYSTEMMELDUNGEN IM DEALCHAT

Der Dealchat soll wichtige Zustandsänderungen automatisch dokumentieren können.

Beispiele:

„Deal angenommen.“

„Deal wurde von 45 auf 39 Sticker angepasst.“

„Valentin hat Versand bestätigt.“

„Ralli hat Versand bestätigt.“

„Valentin hat Empfang bestätigt.“

Dadurch entsteht eine nachvollziehbare Chronologie des Deals.


27. KONKRETE STICKERLISTEN

Ein laufender Deal muss jederzeit vollständig geöffnet werden können.

Der Nutzer muss sehen können:

- welche konkreten Sticker er erhält
- welche konkreten Sticker er abgibt
- jeweilige Mengen
- gegebenenfalls beteiligte Alben
- aktuellen Status

Eine reine Anzeige wie:

„17 erhalten / 17 abgegeben“

reicht nicht.


28. VERSAND BESTÄTIGEN

Jeder Nutzer bestätigt seinen eigenen Versand separat.

Dadurch kann ein Deal beispielsweise folgenden Zustand besitzen:

A hat versendet.
B hat noch nicht versendet.

Diese Information muss im Dealstatus sichtbar sein.


29. BEIDE HABEN VERSENDET

Wenn beide Seiten Versand bestätigt haben, befinden sich die jeweiligen Sendungen im Zustand „unterwegs“.

Die zugehörigen eingehenden Sticker können in der Sammlung entsprechend als unterwegs berücksichtigt werden.


30. BESTAND NICHT BEI DEALANNAHME ENDGÜLTIG BUCHEN

Bei Annahme eines Deals dürfen eingehende Sticker nicht bereits als physisch vorhanden verbucht werden.

Sie sind zu diesem Zeitpunkt lediglich vereinbart.

Auch beim Versand sind eingehende Sticker noch nicht physisch beim Empfänger.

Dafür existiert der Zustand „unterwegs“.


31. EMPFANG BESTÄTIGEN

Zusätzlich zu „Versendet“ muss es einen separaten Empfangsstatus geben.

Jede Seite bestätigt unabhängig:

„Sticker erhalten.“

Erst dadurch weiß Sammlr, dass ein eingehender Sticker tatsächlich beim Nutzer angekommen ist.


32. EMPFANG PRO SEITE

Empfang wird nicht nur für den Gesamtdeal, sondern pro beteiligter Seite betrachtet.

Beispiel:

Valentin erhält seine Sendung.
Ralli erhält seine Sendung noch nicht.

Dann kann Valentins Empfang bereits bestätigt sein, während der Deal insgesamt noch offen bleibt.


33. BESTANDSBUCHUNG BEI EMPFANG

Sobald ein Nutzer den tatsächlichen Empfang seiner Sticker bestätigt, dürfen diese eingehenden Sticker in seinen realen Bestand überführt werden.

Damit bildet Sammlr die physische Realität ab.

Der Gesamtdeal kann trotzdem weiterhin offen sein, solange die Gegenseite ihren Empfang noch nicht bestätigt hat.


34. AUSGEHENDE BESTÄNDE

Ausgehende Sticker müssen entsprechend ihrem tatsächlichen Versand-/Abwicklungszustand aus dem frei verfügbaren physischen Bestand entfernt bzw. in den korrekten Zustand überführt werden.

Die genaue technische Buchungslogik wird vor Implementierung anhand der zentralen Bestandsarchitektur definiert.

Wichtig:

Keine Doppelzählung zwischen:

- frei
- reserviert
- versendet
- unterwegs
- angekommen


35. TEILEMPFANG

Sammlr muss konzeptionell verstehen können, dass eine Sendung nur teilweise angekommen ist.

Beispiel:

30 Sticker erwartet.
29 Sticker tatsächlich erhalten.

Der eine fehlende Sticker darf nicht automatisch als vorhanden gelten.


36. TEILEMPFANG UND BESTAND

Bei Teilempfang dürfen tatsächlich erhaltene Sticker bereits in den Bestand übernommen werden.

Fehlende Sticker bleiben offen bzw. wechseln in einen Problemzustand.

Damit gilt:

physische Realität vor künstlichem Gesamtdealstatus.


37. UX FÜR TEILEMPFANG

Langfristig kann Sammlr eine genaue Auswahl ermöglichen:

„29 von 30 erhalten“

→ fehlenden Sticker auswählen.

Für eine frühe Version kann zunächst ein einfacherer:

„Problem mit Sendung“

Workflow ausreichend sein.

Das Datenmodell sollte Teilempfang jedoch nicht unnötig ausschließen.


38. VERLORENE SENDUNGEN

Wird eine Sendung als verloren betrachtet, dürfen die erwarteten Sticker nicht als physisch vorhanden gelten.

Der entsprechende „unterwegs“-Zustand muss aufgelöst werden.

Weiterhin benötigte Sticker können anschließend wieder für neue Smart Trades freigegeben werden.


39. BESCHÄDIGTE / FALSCHE SENDUNGEN

Beschädigte, falsche oder unvollständige Sendungen sind Problemfälle.

Die genaue Streitfall-/Supportlogik wird später definiert.

Sammlr soll in der frühen Phase nicht versuchen, ein vollständiges Schiedsgerichtssystem zu bauen.


40. PERSÖNLICHE ÜBERGABE

Trades dürfen auch persönlich durchgeführt werden.

Für die erste Version ist keine komplexe Regional- oder Börsenlogik notwendig.

Nutzer können beispielsweise im Dealchat vereinbaren:

„Morgen 18 Uhr an der Bremer Brücke.“

Danach wird die erfolgreiche Übergabe entsprechend bestätigt.


41. PERSÖNLICHE ÜBERGABE NICHT ALS VERSAND SIMULIEREN

Langfristig soll ein Deal eine Abwicklungsart kennen können:

- Versand
- persönliche Übergabe

Bei persönlicher Übergabe muss nicht künstlich ein Versandstatus erzeugt werden.

Nach erfolgter Übergabe können beide Seiten den Empfang / die Durchführung bestätigen.


42. ZUKUNFT: REGIONALE ÜBERGABEN

Später denkbar:

- Sammlr in deiner Region
- persönliche Tauschpartner
- Börsenmodus
- QR-basierter Direktvergleich
- Treffpunkte
- lokale Events

Dies ist nicht Bestandteil der aktuellen Tradezentrale.


43. QR-/BÖRSENDEALS

Langfristiges Ziel:

Zwei Sammlr-Nutzer treffen sich physisch.

Sie wählen die mitgebrachten Alben aus.

Über QR bzw. direkte Partnersuche kann Sammlr sofort berechnen:

„Was könnt ihr jetzt miteinander tauschen?“

Nach Bestätigung werden beide Bestände automatisch angepasst.

Dies ist ein Zukunftsthema des Börsenmodus.


44. ABSCHLUSS EINES DEALS

Ein Deal gilt regulär als vollständig abgeschlossen, wenn die vereinbarte Abwicklung auf beiden Seiten erfolgreich bestätigt wurde.

Bei Versand bedeutet dies grundsätzlich:

beide Seiten haben den relevanten Empfang bestätigt.

Bei persönlicher Übergabe:

beide Seiten bestätigen die erfolgreiche Durchführung.


45. BEWERTUNG ERST NACH ABWICKLUNG

Bewertungen sollen nicht bereits unmittelbar nach Versand freigeschaltet werden.

Grund:

Zu diesem Zeitpunkt ist noch unbekannt, ob die Sendung korrekt ankommt.

Bewertung wird nach tatsächlicher Abwicklung / Empfang ermöglicht.


46. BEWERTUNGSSYSTEM

Erste Produktrichtung:

1–5 Sterne.

Kein öffentliches Freitext-Bewertungssystem zum Start.

Bei schlechter Bewertung können später strukturierte Gründe angeboten werden.

Beispiele:

- nicht versendet
- sehr spät versendet
- unvollständig
- falsche Sticker
- schlechte Verpackung
- Kommunikation problematisch

Exakte Kategorien später definieren.


47. ZUVERLÄSSIGKEIT

Bewertungen sollen langfristig in einen sichtbaren Zuverlässigkeitseindruck eines Nutzers einfließen.

Smart Matches dürfen perspektivisch neben der reinen Tauschmenge auch Zuverlässigkeit berücksichtigen.

Beispiel:

Nutzer kann Smart Matches später gegebenenfalls sortieren nach:

- größter Tauschmenge
- bester Bewertung

Die genaue Rankinglogik wird in der Smart-Trade-Spezifikation gepflegt.


48. VERSANDQUALITÄT

Sammlr soll langfristig eine kurze Anleitung für fachgerechten Stickerversand bereitstellen.

Ziel:

- Sticker schützen
- Verlust vermeiden
- Beschädigung vermeiden
- einheitliche Grundempfehlungen geben

Später können Sammlr-Versandprodukte diese Empfehlungen unterstützen.


49. TRADEHISTORIE

Die normale Tradehistorie enthält erfolgreich abgeschlossene Trades.

Sie soll später nachvollziehbar machen:

- Tauschpartner
- Datum
- beteiligte Sticker
- Mengen
- gegebenenfalls beteiligte Alben
- Dealchat
- Bewertung
- Abwicklungsart


50. WAS NICHT ALS NORMALER TRADE IN DIE HISTORIE GEHÖRT

Nicht als regulärer abgeschlossener Trade behandeln:

- abgelehnte Anfrage
- unbeantwortet verfallene Anfrage

Diese Vorgänge sind keine abgeschlossenen Tauschgeschäfte.


51. PROBLEMATISCHE ANGENOMMENE DEALS

Ein bereits angenommener Deal, der anschließend scheitert, darf nicht einfach vollständig aus dem System verschwinden.

Grund:

Er kann für:

- Zuverlässigkeit
- Bewertungen
- Support
- Missbrauchserkennung
- spätere Konfliktklärung

relevant sein.

Die genaue Darstellung solcher Fälle wird später definiert.


52. TRADEZENTRALE: GRUNDSTRUKTUR

Bevorzugte einfache Informationsarchitektur:

A) ANFRAGEN

Noch nicht angenommene Deals.

B) OFFENE TRADES

Alle angenommenen, aber noch nicht vollständig abgeschlossenen Deals.

Dazu gehören beispielsweise:

- Versand vorbereiten
- Versand überfällig
- teilweise versendet
- unterwegs
- Empfang bestätigen
- Problemfall

C) HISTORIE

Abgeschlossene Trades.

Die exakte UI und Tabstruktur werden später gestaltet.


53. KEINE 17 HAUPTTABS

Unterschiedliche Dealzustände sollen nicht automatisch jeweils einen eigenen Haupttab erhalten.

Beispiel:

„Versand vorbereiten“
„Unterwegs“
„Empfang bestätigen“

sind Zustände innerhalb offener Trades.

Ziel:

übersichtliche Tradezentrale statt Status-Labyrinth.


54. HOME IST NICHT DIE TRADEZENTRALE

Home zeigt nur relevante aktuelle Aufgaben und Hinweise.

Beispiele:

„Rolf möchte 17 Sticker tauschen.“

„Noch 2 Tage zum Versenden.“

„17 Sticker sind unterwegs.“

„Empfang bestätigen.“

Die vollständige Dealverwaltung erfolgt weiterhin in der Tradezentrale.


55. BENACHRICHTIGUNGEN

Tradeereignisse erzeugen entsprechende Benachrichtigungen.

Beispiele:

- neue Tradeanfrage
- Deal angepasst
- Deal angenommen
- Versandfrist nähert sich
- Tauschpartner hat versendet
- Empfang bestätigen
- Problemstatus geändert

Die allgemeine Benachrichtigungsarchitektur wird in der Home-/Notification-Spezifikation gepflegt.


56. STICKERWALL UND UNTERWEGS-STATUS

Eingehende Sticker aus einem laufenden Deal können in der Stickerwall bereits als:

„unterwegs“

sichtbar werden.

Sie sind jedoch noch nicht physisch vorhanden.

Sie werden gleichzeitig aus dem normalen offenen Smart-Trade-Bedarf herausgerechnet.

Die genaue visuelle Darstellung wird in der Sammlungsspezifikation gepflegt.


57. SMART-TRADE-ENGINE UND OFFENE DEALS

Die Smart-Trade-Engine muss jederzeit berücksichtigen:

- offene Anfragen gemäß definierter Reservierungslogik
- angenommene Deals
- reservierte Sticker
- bereits versendete Sticker
- unterwegs befindliche eingehende Sticker
- abgeschlossene Empfangsbuchungen

Ziel:

Kein Sticker soll versehentlich mehrfach verbindlich vergeben oder mehrfach beschafft werden.


58. ABHÄNGIGKEIT VON KORREKTEN BESTÄNDEN

Die Tradezentrale ist auf das Bestandsmodell der Sammlung angewiesen.

Die technische Implementierung darf deshalb nicht isoliert erfolgen.

Vor größeren Änderungen müssen insbesondere geprüft werden:

- physischer Bestand
- Albumzuordnung
- freie Doppelte
- Reservierungen
- Versandzustände
- Unterwegs-Zustände
- Empfang
- Teilempfang


59. HAFTUNG UND RECHT

Vor öffentlicher Skalierung muss professionell geklärt werden:

- Rolle von Sammlr als Vermittlungsplattform
- Haftung bei Verlust
- Haftung bei Beschädigung
- Haftung bei Betrug
- Datenschutz bei Adressen und Bildern
- Plattformregeln
- Bewertungsregeln
- Melde-/Sperrprozesse

Bis dahin darf die Product Bible keine ungeprüften rechtlichen Garantien versprechen.


60. DESIGNPRINZIP

Die Tradezentrale soll trotz komplexer Zustände einfach wirken.

Der Nutzer soll primär wissen:

„Was muss ich jetzt tun?“

Nicht:

„In welchem von 14 technischen Zuständen befindet sich mein Trade?“

Komplexität gehört in die Logik, nicht auf die Oberfläche.


61. OPERATIVE PRIORITÄT

Bei offenen Deals sollen Aufgaben mit Handlungsbedarf priorisiert werden.

Beispiele:

1. Versand überfällig
2. heute versenden
3. Empfang bestätigen
4. neue Anfrage
5. normale laufende Sendung

Die exakte Sortierung wird später definiert.


62. ZIELBILD

Ein Nutzer findet einen geeigneten Tauschpartner.

Sammlr organisiert den Deal.

Nach Annahme reserviert Sammlr die relevanten Sticker.

Die Nutzer klären bei Bedarf Details im Dealchat.

Sie versenden bzw. übergeben die Sticker.

Sammlr begleitet den Vorgang mit Fristen und Zuständen.

Empfang wird pro Seite bestätigt.

Bestände werden entsprechend der physischen Realität aktualisiert.

Der Deal wird abgeschlossen.

Beide Nutzer können sich bewerten.

Der Deal wandert in die Historie.

Danach kann die Smart-Trade-Engine mit den aktualisierten Beständen unmittelbar weiterarbeiten.


63. PRODUKTPHILOSOPHIE

Sammlr soll den realen Tausch nicht ersetzen.

Sammlr soll:

- passende Menschen finden
- sinnvolle Deals berechnen
- Doppelvergaben verhindern
- Abwicklung strukturieren
- Bestände automatisch aktuell halten
- Vertrauen unterstützen
- reale Sammlerkultur einfacher machen

Grundsatz:

„Sammlr ersetzt keine Sammler. Sammlr unterstützt Sammler.“


64. BEWUSST OFFENE FRAGEN

Noch nicht final entschieden:

- exakte Anfrage-Lebensdauer innerhalb des 1–2-Tage-Rahmens
- exakte Definition von 5 Werktagen
- Feiertagslogik
- exakte Überfälligkeitseskalation
- Problemfall-UX
- genaue Teilempfangs-UX
- genaue Bewertungsgründe
- öffentliche Darstellung von Bewertungen
- Bildspeicherung im Dealchat
- strukturierte Adressdaten
- Versandtracking
- Versandlabels
- Versicherungsmodelle
- Streitfall-/Supportprozess
- Missbrauchs-/Sperrlogik

Diese Punkte werden vor der jeweils relevanten Implementierung gesondert spezifiziert.


65. PRODUKTSTATUS

Der Bereich:

TRADEZENTRALE / DEALABWICKLUNG

gilt damit auf fachlicher Produktebene als weitgehend spezifiziert.

Vor technischer Implementierung muss die bestehende Trade- und Bestandsarchitektur gegen diese Soll-Spezifikation geprüft werden.

Insbesondere Reservierungen, Versand, Unterwegs-Zustände, Empfang und Teilempfang dürfen nicht ohne vorherige Architekturprüfung in die bestehende Datenbanklogik eingebaut werden.
