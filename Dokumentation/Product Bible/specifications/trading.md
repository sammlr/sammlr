# Bereich 02: Tauschen / Smart Trader

| Metadatum | Wert |
| --- | --- |
| Status | Product Specification / Working Specification |
| Bereich | Tauschen / Smart Trader |
| Stand | 2026-07-25 |
| Langfristiger Zielhorizont | EM 2028 |
| Änderungshinweis | Änderungen nur bewusst nach neuer Produktentscheidung vornehmen. |

## Dokumentcharakter

Dieses Dokument ist ein langfristiges Produkt-/Lastenheft. Es ist ausdrücklich keine kurzfristige Codex-Todo-Liste und keine Aussage darüber, welche beschriebenen Funktionen bereits implementiert sind. Aus diesem Dokument folgt ohne gesonderte Priorisierung und Umsetzungsentscheidung kein unmittelbarer Implementierungsauftrag.

Das am Ende archivierte Produktprotokoll ist vollständig und inhaltlich unverändert übernommen. Die folgende Statusmatrix dient ausschließlich der eindeutigen Auslegung seiner Aussagen.

## BESCHLOSSEN / KERNLOGIK

Als langfristige Produktprinzipien und Kernarchitektur beschlossen sind insbesondere:

- Sammlr optimiert auf möglichst großen Sammlungsfortschritt mit möglichst wenigen Tauschvorgängen.
- Gepflegte Bestände bilden die Datengrundlage; der Smart Trader erzeugt daraus den eigentlichen Netzwerknutzen.
- Marktabdeckung und persönliche Tauschabdeckung sind unterschiedliche Kennzahlen.
- Top Smart Trades werden gemeinsam und konfliktfrei optimiert. Derselbe verfügbare Sticker darf nicht mehrfach verplant werden.
- Automatisch zusammengestellte Smart-Trade-Pakete sind nicht verhandelbar. Individuelle Pakete gehören in den manuellen Tauschbereich.
- Profile von Tauschpartnern müssen vor einer Anfrage erreichbar sein.
- Abgelehnte oder ausgeschlossene Top Matches führen zu einer Neuberechnung, ohne den Partner aus der manuellen Partnerliste zu entfernen.
- Im manuellen Tausch darf ein Nutzer freiwillig mehr geben, aber niemals mehr verlangen als anbieten.
- Sticker werden systemweit mindestens durch Album-ID plus Sticker-ID eindeutig identifiziert.
- Eine Anfrage ist noch kein Trade und reserviert keine Sticker.
- Erst die Annahme erzeugt einen dokumentierten Deal und reserviert die enthaltenen Sticker.
- Nicht mehr verfügbare Sticker können aus offenen Dealpaketen entfernt werden; neue Sticker werden nicht ungefragt ergänzt.
- Angenommene Deals erhalten einen Deal-Chat, getrennte Versandzustände und eine Versandfrist von fünf Werktagen.
- Physischer Bestand, reservierter Bestand und der temporäre Zustand „unterwegs“ müssen getrennt modelliert werden.
- Erst bestätigter Empfang führt zur finalen Bestandsänderung und zum vollständigen Abschluss.
- Bewertung ist erst nach einem tatsächlichen Deal möglich, niemals nach einer bloßen Anfrage oder Ablehnung.
- Sammlr dokumentiert die Abwicklung, entscheidet zunächst aber nicht über Schuldfragen bei Versandproblemen.
- Die reale Sammelkultur und reale Stickerbörsen werden unterstützt, nicht ersetzt.

Diese Festlegungen beschreiben die Zielarchitektur. Sie gelten nicht automatisch als bereits implementiert.

## NOCH ZU ENTSCHEIDEN

Bewusst offen sind insbesondere:

- genaue Gestaltung und Wording des Tausch-Dashboards,
- Prozent- oder Bruchdarstellung für Markt- und Tauschabdeckung,
- exakte Gewichtung von Fortschritt, Bewertung, Zuverlässigkeit und Versandaufwand,
- endgültige Lebensdauer unbeantworteter Anfragen; 48 Stunden sind im Protokoll als voraussichtlicher Wert festgehalten,
- endgültiges Limit paralleler ausgehender Anfragen; maximal drei sind als V1-Schutzmechanismus diskutiert,
- Standardverhalten und genaue Zustimmungsschritte bei dynamisch verkleinerten Dealpaketen,
- genaue Konsequenzen bei Fristüberschreitungen,
- rechtliche Rolle von Sammlr, Haftung, Plattformpflichten, Datenschutz und Adressweitergabe,
- sowie sämtliche in Abschnitt 27 des Originalprotokolls aufgeführten Punkte.

Offene Punkte dürfen nicht beiläufig durch eine Implementierung als endgültige Produktentscheidung festgeschrieben werden.

## SPÄTER / VISION

Ausdrücklich keine aktuelle Implementierungsanforderung sind insbesondere:

- frei wählbare Smart-Trade-Strategien,
- stärkere Einbeziehung von Bewertung, Zuverlässigkeit und räumlicher Nähe,
- Lernen aus Ablehnungsgründen,
- erweiterte öffentliche Profile und Community-Funktionen,
- globale Einzelstickersuche über mehrere Alben,
- Textbewertungen und differenziertere Reputationsmodelle,
- Tauschpause-Modus,
- eigene Versandprodukte und Versicherungsangebote,
- albumübergreifende Smart Trades,
- Börsenmodus mit QR-Code,
- Wert- und Raritätsmodelle,
- Kaufen und Verkaufen,
- Spieler-/Sticker-Gesuche ohne klassischen gegenseitigen Bedarf,
- komplexe Mehrparteien-Trades,
- Monetarisierung und Premiumgrenzen,
- sowie der volle Nordstern EM 2028.

Diese Punkte bleiben Teil des langfristigen Zielbilds, dürfen aber nicht als bereits priorisierte oder freigegebene Umsetzung gelesen werden.

## Abgleich mit bestehender Dokumentation

Die Datei [`Branding/Corporate ID/Sammlr_Corporate_ID_V1.md`](../../../Branding/Corporate%20ID/Sammlr_Corporate_ID_V1.md) bleibt unverändert.

Die Folgespezifikation [`trade-lifecycle.md`](trade-lifecycle.md) ist für die globale Dealabwicklung maßgeblich, während dieses Dokument die Entstehung sinnvoller Deals und die Smart-Trade-Mechanik definiert. Beide stimmen in der grundlegenden Anfrage-, Reservierungs-, Versand- und Empfangslogik überein.

Die Spezifikation [`navigation-information-architecture.md`](navigation-information-architecture.md) ordnet Smart Trades, Partnersuche und Tradezentrale dem rechten Hauptbereich „Tauschen“ zu. Albumbezogene Einstiege bleiben zusätzlich möglich und verwenden dieselbe fachliche Tradinglogik.

Folgende Abweichungen müssen bei einer späteren bewussten Produktentscheidung bereinigt werden:

- Die Corporate-ID nennt im Zukunfts-Backlog „Reservierte Sticker bei offenen Anfragen“. Das vorliegende Protokoll legt dagegen ausdrücklich fest: Eine Anfrage reserviert nichts; erst die Annahme erzeugt einen Deal und reserviert Sticker.
- Top-Matches und Bewertungssystem sind in der Corporate-ID pauschal als offene beziehungsweise spätere Ideen eingeordnet. Das neue Protokoll konkretisiert Teile davon als langfristige Kernlogik, lässt Detailausgestaltung und erweiterte Reputation aber weiterhin offen.
- Abschnitt 20 des hier archivierten Originalprotokolls ermöglicht Bewertungen bereits nach beidseitiger Versandbestätigung. Die speziellere Folgespezifikation `trade-lifecycle.md` vom 2026-07-27 legt dagegen fest, dass Bewertungen erst nach tatsächlicher Abwicklung beziehungsweise Empfang möglich werden. Für den Trade Lifecycle gilt diese neuere Regel; das Originalprotokoll bleibt unverändert archiviert.
- Abschnitt 18 bezeichnet „unterwegs“ als weder fehlend noch vorhanden. Die neuere Sammlungsspezifikation präzisiert diesen Begriff für Bestandsmodell und Stickerwall: physisch noch fehlend, als „unterwegs“ markiert und aus neuem Smart-Trade-Bedarf herausgerechnet.

Empfehlung: Die Corporate-ID später nicht mit Detailregeln zu überladen, sondern ihre Produktpassagen auf diese Product Bible verweisen lassen. Bis zu einer bewussten Bereinigung bleibt die Abweichung sichtbar dokumentiert.

---

## Archiviertes Originalprotokoll – vollständig und unverändert

SAMMLR PRODUKT-PROTOKOLL

Bereich 02: Tauschen / Smart Trader

Stand: 25.07.2026

1. Grundidee

Sammlr soll langfristig nicht nur Stickerbestände verwalten oder einzelne Tauschpartner finden.

Das Ziel des Tauschsystems lautet:

Mit möglichst wenigen Tauschvorgängen möglichst viele fehlende Sticker für möglichst viele Sammler beschaffen.

Sammlr nutzt die gepflegten Bestände seiner Community, um sinnvolle, konfliktfreie und möglichst große Tauschmöglichkeiten zu berechnen.

Der langfristige Anspruch ist nicht „digitale Stickerliste“, sondern ein intelligentes Tauschnetzwerk für Sammler.

Je mehr Sammler ihre Bestände pflegen, desto größer wird der Pool verfügbarer Doppelter und desto besser werden die Smart Trades für alle.

Nordstern EM 2028: Sammlr soll so leistungsfähig sein, dass Nutzer bewusst alte, unfertige Alben wieder hervorholen, weil realistisch die Aussicht besteht, sie über das Sammlr-Netzwerk zu vervollständigen.

⸻

2. Grundstruktur des Bereichs „Tauschen“

Der globale Bereich Tauschen zeigt zunächst die vorhandenen Alben des Nutzers.

Beispiel:TAUSCHEN

WM 2026
Bundesliga 26/27
WM 2006
...

Albumübergreifend tauschen
Damit existieren langfristig zwei grundlegende Tauscharten:

Albumbezogen: Nutzer möchte gezielt ein bestimmtes Album vervollständigen.

Albumübergreifend: Mehrere ausdrücklich freigegebene Alben werden gemeinsam vom Smart Trader berücksichtigt.

Ein Album soll weiterhin auch direkt aus seinem eigenen Bereich heraus in seinen Tauschbereich führen können.

⸻

3. Tausch-Dashboard eines Albums

Beispiel WM26.

Ganz oben erhält der Nutzer eine kompakte Einschätzung seiner aktuellen Möglichkeiten.

Inhaltlich etwa:

Dir fehlen 167 Sticker.
150 davon sind aktuell bei Sammlr verfügbar.
Mit deinem aktuellen Tauschmaterial kannst du dein Album derzeit voraussichtlich auf 96 % vervollständigen.

Die genaue visuelle Darstellung, Wording sowie Prozent-/Bruchdarstellung werden später im UI-Design festgelegt.

Entscheidend ist die zugrunde liegende Information.

Dabei sind mindestens zwei Kennzahlen zu unterscheiden:

Marktabdeckung: Wie viele meiner fehlenden Sticker befinden sich als verfügbare Doppelte im Sammlr-Netzwerk?

Persönliche Tauschabdeckung: Wie weit kann ich mein Album mit meinem tatsächlich vorhandenen Tauschmaterial und den derzeit verfügbaren Tauschpartnern bringen?

Die persönliche Tauschabdeckung soll langfristig nicht lediglich verfügbare Sticker zählen, sondern tatsächlich mögliche, konfliktfreie Kombinationen von Trades simulieren.

⸻

4. Top Smart Trades

Das Herzstück des albumbezogenen Tauschsystems.

Sammlr zeigt zunächst die drei aktuell attraktivsten Smart Trades.

Beispiel: DEINE SMART TRADES

Peter     45 ↔ 45
Jens      29 ↔ 29
Dana       7 ↔ 7

69 Sticker erreichbar Diese drei Deals werden **gemeinsam optimiert**.

Hat der Nutzer einen bestimmten abzugebenden Sticker nur einmal verfügbar, darf dieser nicht gleichzeitig Bestandteil mehrerer vorgeschlagener Top-Deals sein.

Beispiel:

Peter benötigt GER17 und ermöglicht 45 Sticker.

Jens benötigt GER17 ebenfalls, kann aber ohne GER17 weiterhin 29 Sticker tauschen.

Dann darf Sammlr beispielsweise berechnen: Peter 45 ↔ 45
Jens  29 ↔ 29

Gesamt: 74
statt GER17 zweimal zu verplanen.

Optimierungsprinzip

Nicht zwangsläufig der größte einzelne Trade gewinnt.

Sammlr optimiert auf:

maximalen Sammlungsfortschritt bei möglichst wenigen einzelnen Tauschvorgängen.

Beispielsweise können 75 fehlende Sticker durch drei Sendungen sinnvoller sein als 80 Sticker durch acht Sendungen.

Versandaufwand bzw. Anzahl der notwendigen Tauschvorgänge ist damit langfristig Bestandteil der Optimierung.

⸻

5. Smart-Trade-Pakete sind nicht verhandelbar

Ein Top Smart Match wird von Sammlr vollständig zusammengestellt.

Der Nutzer darf vor der Anfrage sehen, welche Sticker enthalten sind.

Er kann das Paket jedoch nicht verändern.

Beispiel:

Peter · 45 ↔ 45

Entscheidung:

Deal anfragen oder nicht anfragen.

Keine einzelnen Sticker hinzufügen oder entfernen.

Der Grund: Veränderungen eines automatisch optimierten Pakets könnten andere Smart Matches zerstören.

Für individuelle Zusammenstellungen existiert der manuelle Tauschbereich.

⸻

6. Sortierung der Smart Matches

Bewertung und Zuverlässigkeit anderer Sammler sollen berücksichtigt werden.

Langfristig soll der Nutzer seine bevorzugte Strategie auswählen können, beispielsweise:

Maximaler Fortschritt: größtmöglicher Fortschritt mit möglichst wenigen Trades.

Hohe Zuverlässigkeit: Bewertung und bisherige Zuverlässigkeit werden stärker gewichtet.

Später kann beispielsweise auch räumliche Nähe relevant werden.

Sammlr optimiert dennoch immer sinnvoll. Eine Sortierung nach Bewertung bedeutet nicht stumpf „fünf Sterne zuerst“, wenn dadurch schlechte Mini-Deals entstehen.

⸻

7. Profile vor einer Anfrage

Ein Tauschpartner muss vor der Anfrage anklickbar sein.

Der Nutzer kann dessen öffentliches Profil ansehen und beispielsweise später Informationen wie folgende erhalten:

- Bewertungen
- abgeschlossene Trades
- öffentliche Alben
- Statistiken
- Trophäenschrank
- weitere für Vertrauen relevante Informationen

Anschließend kann zum Smart Trade zurückgekehrt werden.

Damit sind Tauschsystem und zukünftige Community-/Profilfunktionen direkt miteinander verbunden.

⸻

8. Smart Match ablehnen

Wird ein vorgeschlagenes Smart Match nicht gewünscht, soll Sammlr nach Möglichkeit nach dem Grund fragen.

Dies kann zukünftig helfen, Vorschläge zu verbessern.

Nach Ablehnung beziehungsweise Ausschluss eines Top Matches wird die Liste neu berechnet.

Beispiel: 1 Peter
2 Jens
3 Dana
4 Yusuf Peter fällt heraus.

Danach: 1 Jens
2 Dana
3 Yusuf
Der ehemalige Smart-Match-Partner darf weiterhin in der vollständigen manuellen Tauschpartnerliste erscheinen.

⸻

9. Alle Tauschpartner / manueller Tausch

Neben den drei fertigen Smart Trades existiert:

Alle Tauschpartner

Hier sieht der Nutzer sämtliche Personen, mit denen grundsätzlich ein Deal möglich ist, bis hin zu 1 ↔ 1.

Mögliche Sortierungen:

- größte Tauschmöglichkeit
- beste Bewertung
- später Entfernung

Hier darf der Nutzer das Paket selbst zusammenstellen.

Fairnessregel

Ein Nutzer darf freiwillig mehr geben als erhalten, aber niemals mehr verlangen als anbieten.

Beispiele: 17 geben ↔ 17 nehmen  ✓
23 geben ↔ 17 nehmen  ✓
56 geben ↔ 17 nehmen  ✓

14 geben ↔ 17 nehmen  ✗
Wer nur 14 Sticker geben möchte, darf maximal 14 auswählen.

Wenn ein anderer Nutzer keinen passenden Bedarf an den eigenen Doppelten besitzt, ist über das normale Tauschsystem kein Deal möglich.

Spätere Spieler-/Sticker-Gesuche können hierfür andere Regeln erhalten.

⸻

10. Einzelstickersuche

Nutzer können gezielt nach einem fehlenden Sticker suchen.

Beispiel:

ARG17

Innerhalb eines Albums ist die Suche eindeutig diesem Album zugeordnet.

Langfristig soll zusätzlich eine globale Suche existieren.

Da Stickerbezeichnungen albumübergreifend mehrfach vorkommen können, muss intern immer eine eindeutige Identität aus mindestens:

Album-ID + Sticker-ID

existieren.

Die globale Suche gruppiert entsprechend nach Album.

Suchergebnisse

Nicht lediglich:

38 Nutzer besitzen ARG17.

Sondern beispielsweise: ARG17 wird von 38 Sammlern angeboten.

Peter
ARG17 + 17 weitere mögliche Sticker

Yusuf
ARG17 + 8 weitere

Ralf
ARG17 + 3 weitere
Die Einzelstickersuche dient damit als Einstieg in einen möglichst sinnvollen Gesamtdeal.

⸻

11. Anfragephase

Für Top Smart Trades gilt zunächst:

Anfrage ≠ Reservierung.

Beim Absenden wird klar kommuniziert, dass bei Annahme ein verbindlicher Deal entsteht und anschließend eine Versandfrist gilt.

Eine unbeantwortete Anfrage lebt voraussichtlich 48 Stunden.

Danach verfällt sie vollständig.

Sie erscheint:

- nicht als Trade
- nicht in der Tradehistorie
- nicht in Statistiken
- nicht als „geplatzter Deal“

Eine ignorierte Anfrage ist noch kein Trade.

⸻

12. Reservierung

Erst wenn der Empfänger einen Deal annimmt, werden die enthaltenen abzugebenden Sticker reserviert.

Grundlogik: ANFRAGE
keine Reservierung

↓ Annahme

DEAL
Sticker reserviert
Nach einer Annahme werden sämtliche betroffenen offenen Anfragen und Smart Matches erneut geprüft.

⸻

13. Dynamische Dealpakete

Sticker können während einer offenen Anfrage anderweitig nicht mehr verfügbar werden, beispielsweise durch:

- einen anderen angenommenen Trade
- einen physischen Tausch auf einer Börse
- manuelle Bestandskorrektur

Deshalb können offene Dealpakete automatisch verkleinert werden.

Beispiel: ursprünglich 17 ↔ 17

Messi nicht mehr verfügbar

neu 16 ↔ 16
Der Nutzer soll vorher entscheiden können, ob er:

automatische Anpassungen akzeptiert

oder

bei Änderungen erneut zustimmen möchte.

Neue Sticker werden nicht ohne Zustimmung automatisch in bestehende Pakete eingesetzt. Zunächst werden lediglich nicht mehr verfügbare Positionen entfernt und der Deal entsprechend angepasst.

⸻

14. Begrenzung paralleler Anfragen

Als V1-Schutzmechanismus wurde diskutiert:

maximal 3 selbst versendete offene Anfragen gleichzeitig.

Eingehende Anfragen werden nicht entsprechend hart begrenzt.

Die genaue Grenze kann anhand echter Nutzung später angepasst werden.

⸻

15. Angenommener Deal

Mit der Annahme beginnt die eigentliche Abwicklung.

Ab diesem Zeitpunkt:

- Sticker sind reserviert
- ein Deal-Chat wird geöffnet
- der Deal ist dokumentiert
- beide Seiten erhalten eine Versandfrist
- der Deal kann später Bestandteil von History/Bewertung werden

Vor Annahme muss klar kommuniziert werden:

Angenommene Deals müssen innerhalb von 5 Werktagen versendet werden.

Wer aktuell nicht versenden kann, soll keinen Deal annehmen.

Langfristig ist ein Tauschpause-Modus sinnvoll, durch den ein Nutzer vorübergehend aus Smart Matches herausgenommen wird.

⸻

16. Deal-Chat

Sammlr benötigt zunächst keinen allgemeinen Messenger.

Stattdessen erhält jeder angenommene Deal einen eigenen Chat.

Dort können Nutzer beispielsweise:

- Versand abstimmen
- Adresse mitteilen
- persönliche Übergabe vereinbaren
- Fragen zum Deal klären
- bei Bedarf externe Kontaktdaten austauschen

Der Chat bleibt später zusammen mit dem Trade einsehbar.

Sammlr stellt damit die notwendige Kommunikation für den konkreten Deal bereit, ohne zunächst ein vollständiges soziales Nachrichtensystem bauen zu müssen.

⸻

17. Versand

Persönliche Übergabe oder Versand können die Nutzer zunächst selbst im Deal-Chat vereinbaren.

Der Standard-Use-Case des Online-Trades wird zunächst als Postversand gedacht.

Beide Nutzer haben nach Annahme 5 Werktage, ihre Sticker zu versenden.

Jede Seite bestätigt separat:

Ich habe versendet.

Damit entstehen getrennte Versandzustände.

Beispiel: Valentin   ✓ versendet
Peter      Versand ausstehend
Erst wenn beide bestätigt haben:

Beidseitig versendet

Ein bereits einseitig versendeter Deal darf nach Ablauf einer Frist niemals einfach verschwinden.

Status, Zeitstempel und Chat bleiben erhalten.

⸻

18. Unterwegs-Status für Sticker

Versendete, aber noch nicht erhaltene Sticker sind weder „fehlend“ noch „vorhanden“.

Dafür benötigt Sammlr einen temporären Zustand:

unterwegs

Beispiel Stickerwall: ARG17

0 vorhanden
📮 +1 unterwegs Stickerliste entsprechend beispielsweise: ARG17   📮 unterwegs
Ein unterwegs befindlicher Sticker:

- erhöht den physischen Bestand noch nicht
- darf nicht erneut als fehlender Bedarf für Smart Trades behandelt werden

Auf der Abgabeseite dürfen versendete Exemplare ebenfalls nicht mehr für weitere Deals verfügbar sein.

Grundsätzlich müssen deshalb physischer Bestand und Trade-Status getrennt modelliert werden.

⸻

19. Empfang und Bestandsänderung

Erst der tatsächliche Empfang führt zur finalen Bestandsänderung.

Beide Seiten bestätigen unabhängig:

Sticker erhalten

Erst wenn die entsprechenden Bestätigungen erfolgt sind, wird der Trade vollständig abgeschlossen.

Dann folgen:

- finale Bestandsänderungen
- Fortschrittsberechnung
- Trophy-Prüfung
- Tradehistorie
- Statistik
- Auflösung der temporären Status

Der bereits im ersten realen Sammlr-Trade erfolgreich getestete Grundsatz der beidseitigen Bestätigung vor finalem Abschluss bleibt erhalten.

⸻

20. Bewertung und Zuverlässigkeit

Sobald beide Nutzer den Versand bestätigt haben, wird eine gegenseitige Bewertung möglich.

V1:

★★★★★

Später können Textbewertungen oder differenziertere Kriterien ergänzt werden.

Keine Bewertung ist nach einer bloßen Anfrage oder Ablehnung möglich.

Langfristig soll zusätzlich eine Zuverlässigkeitskomponente entstehen, beispielsweise aus:

- fristgerechtem Versand
- abgeschlossenen Trades
- geplatzten angenommenen Deals
- Nutzerbewertungen

Bewertungen können wiederum in die Smart-Match-Optimierung einfließen.

⸻

21. Versandprobleme

Sammlr dokumentiert:

- Deal
- Chat
- Versandbestätigungen
- Status
- Zeitpunkte
- Bewertungen

Sammlr entscheidet zunächst nicht, wer bei einem verlorenen Brief oder widersprüchlichen Aussagen Recht hat.

Vor öffentlichem Betrieb muss die konkrete rechtliche Rolle von Sammlr professionell geprüft werden.

Insbesondere Haftung, Plattformpflichten, Datenschutz, Adressweitergabe und spätere Zahlungs-/Versicherungsangebote dürfen nicht durch selbst formulierte Haftungsausschlüsse ersetzt werden.

⸻

22. Versandanleitung

Sammlr soll eine kostenlose Anleitung bereitstellen, wie Sticker möglichst sicher versendet werden.

Ziel:

- Schutz vor Knicken
- Schutz vor Feuchtigkeit
- Vermeidung loser Sticker im Umschlag
- möglichst geringe Verlustgefahr

Langfristig kann diese Funktion mit eigenen Sammlr-Versandlösungen aus dem Store verbunden werden.

Die kostenlose sichere Versandmethode bleibt dennoch erhalten.

⸻

23. Albumübergreifende Trades

Nutzer können einzelne Alben ausdrücklich für albumübergreifendes Tauschen freigeben.

Es werden ausschließlich abgebbare Doppelte verwendet. Einzelne Sammlungsexemplare bleiben unangetastet.

Beispiel: CROSS-ALBUM-POOL

☑ WM26
☑ Bundesliga 26/27
☑ WM06
☐ VfL Albumübergreifende Trades sollen langfristig primär beziehungsweise ausschließlich durch den **Smart Trader** zusammengestellt werden.

Manuelle Zusammenstellung über mehrere große Alben wäre unnötig komplex.

Beispiel: Du bekommst:

17 × WM06
12 × WM26

Peter bekommt:

21 × Bundesliga
8 × Basketball

29 ↔ 29
Für Cross-Album-Smart-Trades gelten grundsätzlich dieselben Regeln wie für normale Smart Trades.

Der Algorithmus behandelt normale Sticker zunächst 1:1 nach Stückzahl, unabhängig von Album, Alter oder Spieler.

Wert-/Raritätsmodelle gehören in eine spätere Produktphase.

⸻

24. Börsenmodus

Sammlr soll reale Stickerbörsen unterstützen und nicht ersetzen.

Ziel:

Zwei Sammlr stehen physisch voreinander und erfahren innerhalb weniger Sekunden, was sie sinnvoll miteinander tauschen können.

Langfristiger Wunschflow: BÖRSENMODUS

Welche Alben hast du dabei?

☑ WM26
☑ EM24
☐ WM06
☐ Bundesliga

QR-CODE ERSTELLEN
Der andere Sammler scannt den QR-Code und gibt ebenfalls die tatsächlich mitgebrachten Alben frei.

Sammlr vergleicht nur diese Bestände.

Beispiel:

Ihr könnt 47 Sticker tauschen.

Anschließend kann ein sinnvoller Deal berechnet werden.

Da beide Personen physisch anwesend sind, entfällt der Online-Abwicklungsprozess:

QR → Match → Deal → beide bestätigen → Bestände aktualisieren.

Kein Versandstatus und keine 5-Werktage-Frist.

⸻

25. Strategische Rolle des Smart Traders

Die langfristig wichtigste technische Komponente von Sammlr ist nicht die Stickerwall.

Die Stickerwall erzeugt Daten.

Der Smart Trader erzeugt daraus Nutzen.

Langfristig soll Sammlr nicht nur sagen:

Peter besitzt Sticker, die dir fehlen.

Sondern:

Mit deinen aktuellen Beständen und den verfügbaren Sammlern existiert eine Kombination aus vier Trades, mit der du dein Album voraussichtlich auf 96 % vervollständigen kannst.

Später soll diese Optimierung über mehrere Alben und mehrere Sammler funktionieren.

Das System soll Nutzer dabei unterstützen, auch lange nicht vervollständigte historische Alben wieder aktiv zu sammeln.

⸻

26. Netzwerkeffekt

Der Wert des Smart Traders steigt mit jedem aktiven Sammler. mehr Sammler
      ↓
mehr gepflegte Alben
      ↓
mehr Doppelte im Netzwerk
      ↓
höhere Marktabdeckung
      ↓
größere/bessere Smart Trades
      ↓
weniger Versandvorgänge pro Album
      ↓
mehr vervollständigte Alben
      ↓
höherer Nutzen von Sammlr
      ↓
mehr Sammler
Dieser Netzwerkeffekt ist zentral für die langfristige Produktstrategie.

⸻

27. Nicht für die unmittelbare Umsetzung festgelegt

Bewusst noch nicht abschließend entschieden:

- genaue UI des Tausch-Dashboards
- Prozent vs. Bruch bei Markt-/Tauschabdeckung
- exakte Gewichtung von Menge, Bewertung und Versandaufwand
- endgültiges Limit paralleler Anfragen
- genaue Konsequenzen bei Fristüberschreitungen
- Textbewertungen
- regionale Sammlersuche
- Spieler-/Sticker-Gesuche ohne klassischen gegenseitigen Bedarf
- Wert/Rarität einzelner Sticker
- Versicherung
- Kaufen/Verkaufen
- Sammlr-Versandprodukte
- komplexe Mehrparteien-Trades
- Monetarisierung/Premiumgrenzen

Diese Punkte dürfen später entwickelt werden, ohne die hier definierte Kernarchitektur zu verändern.

⸻

28. Produktprinzip

Und den würde ich tatsächlich wortwörtlich prominent archivieren:

Sammlr ersetzt keine Sammler. Sammlr unterstützt Sammler.

Ziel des Smart Traders ist es, mit möglichst wenigen Tauschvorgängen möglichst viele Lücken in den Sammlungen aller Beteiligten zu schließen.

Die App soll reale Sammelkultur, Tauschen und Stickerbörsen stärken, nicht ersetzen.

⸻
