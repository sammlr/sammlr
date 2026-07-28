# Bereich 01: Sammlung / Alben / Stickerverwaltung

| Metadatum | Wert |
| --- | --- |
| Status | Working Product Specification |
| Bereich | Sammlung / Alben / Stickerverwaltung |
| Stand | 2026-07-26 |
| Änderungshinweis | Änderungen nur bewusst nach neuer Produktentscheidung vornehmen. |

## Dokumentcharakter

Dieses Dokument ist ein langfristiges Produkt-/Lastenheft. Es ist ausdrücklich keine kurzfristige Codex-Todo-Liste und keine Aussage darüber, welche beschriebenen Funktionen bereits implementiert sind. Vor technischer Umsetzung müssen Datenmodell und Anwendung gesondert gegen diese Soll-Spezifikation geprüft werden.

Das am Ende archivierte Produktprotokoll ist vollständig und inhaltlich unverändert übernommen. Die folgende Statusmatrix dient ausschließlich der eindeutigen Auslegung seiner Aussagen.

## BESCHLOSSEN / KERNLOGIK

Als langfristige Produktprinzipien und Kernarchitektur beschlossen sind insbesondere:

- Die Sammlung ist das Bestandsfundament von Sammlr; häufige Vorgänge bleiben einfach, fortgeschrittene Komplexität wird nur bei Bedarf sichtbar.
- Die Sammlr-Zentrale ist der Einstieg in die eigene Sammlung und ausdrücklich nicht dasselbe wie Home / Startseite.
- Albumtyp und konkretes Albumexemplar sind getrennte Ebenen; jedes Exemplar behält Fortschritt, Stickerwall, Papierliste, Zuordnungen und Aktivitätszustand.
- Mengen beschreiben physisch vorhandene Sticker. Doppelte und freier Tauschbestand werden aus Bestand, Albumzuordnung und verbindlichen Zuständen berechnet.
- Freie Doppelte bilden je Albumtyp einen gemeinsamen Tauschpool und werden nicht künstlich einem Albumexemplar zugeordnet.
- Sammlr verwaltet keinen Klebezustand.
- Manuelle Vorgänge folgen der expliziten Nutzerentscheidung; automatische Vorgänge folgen einer definierten Prioritätslogik. Bewusste Nutzereingaben haben grundsätzlich Vorrang.
- Deaktivieren und Löschen sind unterschiedliche Vorgänge. Zugeordnete Sticker werden weder stillschweigend verschoben noch vernichtet.
- Vollständigkeit, Fortschritt, Kapitel und Vitrinenstatus werden pro Albumexemplar berechnet.
- Die Stickerwall bleibt die visuelle Hauptverwaltung; die Papier-Stickerliste bleibt eine schnelle Kernfunktion für reale Börsen- und Tauschsituationen.
- Reservierter, freier, physisch vorhandener und unterwegs befindlicher Bestand müssen logisch getrennt werden.
- Unterwegs befindliche Sticker bleiben physisch fehlend, werden aber aus neuem automatischem Smart-Trade-Bedarf herausgerechnet.
- Manuelle Bestandskorrekturen erzeugen nicht automatisch Tradehistorie oder Statistikereignisse.
- Der Smart Trader darf ausschließlich auf einem konsistenten Bestandsmodell arbeiten.

Diese Festlegungen beschreiben die Zielarchitektur. Sie gelten nicht automatisch als bereits implementiert.

## NOCH ZU ENTSCHEIDEN

Bewusst offen sind insbesondere:

- exakte Gestaltung der neuen Stickerkarten,
- exakte Größe, Form und Nullzustand des Mengenreglers,
- endgültige Filterdarstellung,
- endgültige Batch-Auswahl und genaue Code-Eingabe,
- visuelle Darstellung von „unterwegs“,
- genaue Mehrfachalbum-Stapeldarstellung,
- genaue Einstellungsoberfläche für automatische Zuordnung,
- Löschdialoge,
- Scanner-UX,
- Offline-Synchronisations-UX,
- Detailregeln einzelner Trophäen,
- exakte UI und Optionen bei Entfernung eines Albumexemplars.

Offene Punkte dürfen nicht beiläufig durch eine Implementierung als endgültige Produktentscheidung festgeschrieben werden.

## SPÄTER / VISION

Ausdrücklich keine aktuelle Implementierungsanforderung sind insbesondere:

- Mehrfachalben als Advanced-Collector-Funktion einschließlich Mehrfachbedarf und automatischer Zuordnungspräferenzen,
- komplette Albumübertragung zwischen Sammlr-Nutzern,
- kamerabasierte beziehungsweise KI-gestützte Scanner-Erfassung,
- Offline-Fähigkeit und spätere Synchronisation für börsenrelevante Funktionen.

Diese Themen müssen architektonisch berücksichtigt werden, sind aber keine unmittelbar freigegebenen MVP-Aufgaben.

## Abgleich mit bestehender Dokumentation

Die Spezifikation [`home.md`](home.md) bleibt maßgeblich für Home / Startseite. Das vorliegende Dokument konkretisiert die dort angekündigte eigene Sammlungslogik und bestätigt ausdrücklich, dass Home und Sammlr-Zentrale verschiedene Bereiche sind.

Die Spezifikation [`trading.md`](trading.md) bleibt maßgeblich für Smart-Trade-Mechanik und Dealfindung. Die Spezifikation [`trade-lifecycle.md`](trade-lifecycle.md) bleibt maßgeblich für Tradezustände und Dealabwicklung. Dieses Dokument liefert dafür das Bestandsfundament und präzisiert die Trennung von physischem, zugeordnetem, freiem, reserviertem und unterwegs befindlichem Bestand.

Die Spezifikation [`profile-community.md`](profile-community.md) bleibt maßgeblich für öffentliche Sichtbarkeit und Darstellung fremder Alben. Dieses Dokument definiert dagegen die interne fachliche Struktur eigener Albumexemplare und Bestände.

Die Spezifikation [`navigation-information-architecture.md`](navigation-information-architecture.md) ordnet die Sammlr-Zentrale dem linken Hauptbereich „Sammlung“ zu. Ihr mittlerer `sammlr.`-Punkt führt zu Home. Die dort einmal verwendete Gleichsetzung von Home und Sammlr-Zentrale ist als offener Begriffskonflikt dokumentiert und ändert die fachliche Trennung nicht stillschweigend.

Vorhandene Verweise auf Stickerwall, Vitrine, aktive Alben und Tauschbestand wurden berücksichtigt. Eine eigenständige ältere Sammlungsspezifikation wurde nicht gefunden.

---

## Archiviertes Originalprotokoll – vollständig und unverändert

SAMMLR PRODUCT SPECIFICATION
BEREICH: SAMMLUNG / ALBEN / STICKERVERWALTUNG
Stand: 2026-07-26
Status: Working Product Specification
============================================================


1. ZWECK DES BEREICHS

Die Sammlung ist das Bestandsfundament von Sammlr.

Sie muss sowohl für einfache Nutzer mit einem einzigen aktuellen Album als auch perspektivisch für intensive Sammler mit mehreren Exemplaren desselben Albums funktionieren.

Grundprinzip:

Komplexität darf im System vorhanden sein, soll aber nur dann sichtbar werden, wenn der Nutzer sie benötigt.

Ein Nutzer mit einem Album soll nicht mit Mehrfachalbum-, Pool- oder Prioritätslogik konfrontiert werden.


2. PRODUKTREGEL: HÄUFIGE VORGÄNGE OPTIMIEREN

Sammlr optimiert häufige reale Vorgänge.

Seltene Sonderfälle dürfen mehr manuelle Schritte benötigen.

Es sollen nicht für jeden theoretisch denkbaren Spezialfall eigene Buttons, Modi oder Workflows entstehen.

Grundsatz:

„Komplexität im Motorraum, Einfachheit am Lenkrad.“


3. SAMMLR-ZENTRALE

Die Sammlr-Zentrale bleibt der zentrale Einstieg in die eigene Sammlung.

Grundstruktur:

- Lieblingsalbum
- aktive Alben
- Album hinzufügen
- Vitrine abgeschlossener Alben

Von dort gelangt der Nutzer in einzelne Alben und deren Stickerverwaltung.

Die Sammlr-Zentrale ist ausdrücklich NICHT dasselbe wie die separate Home-/Startseite.


4. ALBUM HINZUFÜGEN

Über „Album hinzufügen“ wählt der Nutzer ein von Sammlr unterstütztes Album aus.

Besitzt der Nutzer diesen Albumtyp noch nicht, wird ein neues Albumexemplar angelegt.

Besitzt der Nutzer bereits ein Exemplar dieses Albumtyps, soll Sammlr erkennen, dass es sich um ein weiteres Exemplar handelt und entsprechend „Weiteres Exemplar hinzufügen“ anbieten.

Die Mehrfachalbumlogik wird erst sichtbar, wenn sie tatsächlich benötigt wird.


5. ALBUMTYP VS. ALBUMEXEMPLAR

Langfristig muss zwischen zwei Ebenen unterschieden werden:

ALBUMTYP
Beispiel:
FIFA World Cup 2026

ALBUMEXEMPLAR
Beispiel:
das konkrete erste, zweite oder dritte physische WM26-Album des Nutzers

Ein Nutzer kann mehrere Exemplare desselben Albumtyps besitzen.


6. MEHRFACHALBEN SIND EIN ADVANCED-COLLECTOR-FEATURE

Für normale Nutzer mit einem einzigen Album bleibt die Oberfläche so einfach wie heute.

Kein:

- „Exemplar #1“
- Pool-Management
- Prioritätenverwaltung
- Mehrfachbedarfsanzeige
- zusätzliche technische Begriffe

Erst wenn ein weiteres Exemplar hinzugefügt wird, erscheint die zusätzliche Ebene.

Ziel:

Schulhoftauscher bekommt eine einfache App.

Intensiver Sammler bekommt bei Bedarf ein leistungsfähiges System.


7. EIGENE NAMEN FÜR ALBUMEXEMPLARE

Albumexemplare erhalten zunächst den offiziellen Albumtitel bzw. eine neutrale Standardbezeichnung.

Nutzer dürfen ihre konkreten Albumexemplare jedoch frei umbenennen.

Beispiele:

„Hauptalbum“
„Weglegealbum“
„Album für Luca“

Die genaue UI dafür wird später definiert.


8. MEHRERE EXEMPLARE IN DER SAMMLR-ZENTRALE

Mehrere Exemplare desselben Albumtyps sollen nicht unnötig als fünf identische große Karten untereinander erscheinen.

Bevorzugte Designrichtung:

gestapelte Darstellung ähnlich einem Karten-/Wallet-Stapel.

Beispiel:

FIFA World Cup 2026
3 Exemplare

Beim Öffnen kann der Nutzer die einzelnen Exemplare auswählen.

Die genaue visuelle Umsetzung wird später definiert.


9. JEDES ALBUMEXEMPLAR BLEIBT EIGENSTÄNDIG

Jedes konkrete Albumexemplar besitzt:

- eigenen Fortschritt
- eigene Stickerwall
- eigene Papier-Stickerliste
- eigenen fehlenden Bestand
- eigene Zuordnung vorhandener Sticker
- eigenen Aktivitätszustand

Damit bleibt ein konkretes physisches Album auch digital als eigenes Album verwaltbar.


10. STICKERBESTAND

Die zentrale Mengenangabe eines Stickers beschreibt grundsätzlich die Anzahl physisch vorhandener Exemplare.

Beispiel:

GER20 = 1
→ Nutzer besitzt GER20 einmal.

GER20 = 2
→ Nutzer besitzt GER20 zweimal.

GER20 = 5
→ Nutzer besitzt GER20 fünfmal.

Die angezeigte Menge beschreibt NICHT die Anzahl der Doppelten.


11. DOPPELTE SIND EIN BERECHNETER ZUSTAND

Bei einem einzelnen aktiven Album gilt beispielsweise:

Bestand GER20 = 1
→ Album erfüllt
→ 0 frei verfügbare Doppelte

Bestand GER20 = 2
→ Album erfüllt
→ 1 frei verfügbarer Doppelter

Bestand GER20 = 5
→ Album erfüllt
→ 4 frei verfügbare Doppelte

Der Nutzer soll nicht separat pflegen müssen:

„vorhanden“
vs.
„doppelt“

Doppelte ergeben sich aus Bestand, Albumzuordnung und weiteren relevanten Zuständen.


12. MEHRFACHALBUM UND STICKERZUORDNUNG

Bei mehreren Exemplaren desselben Albumtyps können physische Sticker konkreten Albumexemplaren zugeordnet sein.

Beispiel:

Gesamtbestand GER20 = 3

WM26 Hauptalbum:
GER20 erfüllt

WM26 Weglegealbum:
GER20 erfüllt

Freier Bestand:
GER20 = 1

Der freie Sticker gehört keinem Albumexemplar und ist Teil des freien Bestands bzw. Tauschpools dieses Albumtyps.


13. ALBUMTYPBEZOGENER TAUSCHPOOL

Freie Doppelte desselben Albumtyps bilden einen gemeinsamen Tauschpool.

Doppelte gehören nicht künstlich einem bestimmten Albumexemplar.

Beispiel:

WM26 #1 besitzt GER20.
WM26 #2 besitzt GER20.
Ein weiterer GER20 ist frei.

Dieser dritte GER20 ist Teil des freien WM26-Tauschbestands.

Smart Trades können damit arbeiten.


14. KEIN KLEBEZUSTAND

Sammlr verwaltet nicht, ob ein Sticker:

- eingeklebt
- lose
- in einer Hülle
- in einer Box
- anderweitig physisch gelagert

ist.

Für Sammlr ist entscheidend:

- physischer Bestand
- Zuordnung zu einem Albumexemplar
- freier Bestand
- fehlender Bedarf
- Reservierung
- unterwegs befindlicher Bestand

Ob ein Nutzer klebt oder nicht, ist seine Sache.


15. MANUELLE EINGABEN HABEN EXPLIZITE ZUORDNUNG

Wichtige Systemregel:

Manuelle Eingaben folgen dem ausdrücklichen Nutzerbefehl.

Beispiel:

Nutzer öffnet bewusst WM26 #2.

Er trägt GER20 dort als vorhanden ein.

Dann wird GER20 WM26 #2 zugeordnet, auch wenn GER20 in WM26 #1 ebenfalls fehlt.

Sammlr darf eine explizite manuelle Eingabe nicht heimlich in ein anderes Albumexemplar umleiten.


16. PAPIERLISTE UND MANUELLE ZUORDNUNG

Dasselbe gilt für die Papier-Stickerliste.

Öffnet der Nutzer:

WM26 #3
→ Stickerliste

und streicht GER20 als erhalten ab, dann wird GER20 diesem konkreten Albumexemplar zugeordnet.

Dadurch bleibt die Papierliste ein reales Werkzeug für ein konkretes physisches Album.


17. AUTOMATISCHE VORGÄNGE VERWENDEN PRIORITÄTEN

Automatische Vorgänge funktionieren anders als manuelle Eingaben.

Beispiele:

- abgeschlossener Smart Trade
- automatisch eingehende Sticker
- automatische Befüllung eines neu hinzugefügten Albumexemplars

Hier verteilt Sammlr nach einer definierten Prioritätsreihenfolge.

Standard:

Albumexemplar 1
→ Albumexemplar 2
→ Albumexemplar 3
→ usw.

Deaktivierte Albumexemplare werden übersprungen.

Beispiel:

#1 aktiv
#2 aktiv
#3 deaktiviert
#4 aktiv

Automatische Priorität:

#1 → #2 → #4


18. ZENTRALE SYSTEMREGEL

Diese Regel soll langfristig als fundamentale Sammlungsregel behandelt werden:

MANUELLE VORGÄNGE:
folgen der expliziten Nutzerentscheidung.

AUTOMATISCHE VORGÄNGE:
folgen der systemischen Prioritätslogik.


19. MENSCH VOR AUTOMATIK

Wenn eine Automatik und eine bewusste Nutzereingabe miteinander kollidieren, gewinnt grundsätzlich die bewusste Nutzereingabe.

Sammlr darf warnen oder in zwingenden Fällen blockieren.

Sammlr soll jedoch nicht heimlich Bestände anders verteilen als vom Nutzer angegeben.

Ausnahme:

Bereits verbindliche Zustände wie reservierte Sticker dürfen nicht durch eine Bestandsänderung unbemerkt mathematisch unmöglich gemacht werden.


20. NEUES ALBUMEXEMPLAR AUS DOPPELTEN BEFÜLLEN

Beim Hinzufügen eines weiteren Exemplars desselben Albumtyps soll Sammlr anbieten, bereits vorhandene freie Doppelte automatisch zur Befüllung zu verwenden.

Beispiel:

Nutzer besitzt WM26 einmal und hat sehr viele Doppelte.

Er fügt WM26 ein zweites Mal hinzu.

Sammlr kann anbieten:

„Vorhandene Doppelte für das neue Album verwenden.“

Dadurch werden geeignete freie Sticker dem neuen Albumexemplar zugeordnet und stehen anschließend nicht mehr als freie Doppelte im Tauschpool zur Verfügung.


21. MEHRFACHBEDARF

Mehrere aktive Albumexemplare können dazu führen, dass derselbe Sticker mehrfach benötigt wird.

Beispiel:

3 aktive WM26-Alben.

GER20 ist nur einmal zugeordnet.

Dann kann GER20 zweimal fehlen.

Smart Trades müssen langfristig Mengenbedarfe größer als 1 unterstützen.

Damit können Deals legitimerweise auch mehrere Exemplare desselben Stickers enthalten.


22. ALBEN DEAKTIVIEREN

Ein Album kann deaktiviert werden, wenn der Nutzer es momentan nicht aktiv vervollständigen möchte.

Beispiele:

- keine Zeit
- aktuell kein Interesse
- keine Tradeanfragen für dieses Album gewünscht
- Projekt vorübergehend pausiert

Deaktivieren ist ausdrücklich NICHT Löschen.


23. AUSWIRKUNG DER DEAKTIVIERUNG

Bereits zugeordnete Sticker bleiben beim deaktivierten Album.

Sie werden nicht freigegeben oder verschoben.

Fehlende Sticker dieses Albumexemplars werden jedoch bei automatischer Smart-Trade-Bedarfsberechnung ignoriert.

Andere aktive Exemplare desselben Albumtyps bleiben davon unberührt.


24. SAMMELAKTIVITÄT UND TAUSCHBEREITSCHAFT TRENNEN

Langfristig muss unterschieden werden können zwischen:

- Album aktiv vervollständigen
- freie Doppelte dieses Albumtyps zum Tauschen anbieten

Ein deaktiviertes Albumexemplar bedeutet nicht automatisch, dass freie Doppelte dieses Albumtyps nicht mehr getauscht werden dürfen.

Der Tauschpool ist albumtypbezogen.


25. ALBUM LÖSCHEN

Löschen bedeutet:

Dieses physische Album gehört nicht mehr zur Sammlung.

Mögliche reale Gründe:

- verkauft
- verschenkt
- verloren
- zerstört
- anderweitig dauerhaft abgegeben

Nur „gerade keine Lust“ ist kein Löschgrund, sondern ein Fall für Deaktivieren.


26. LÖSCHEN DARF KEINE BESTÄNDE STILLSCHWEIGEND VERNICHTEN

Wenn ein Albumexemplar entfernt wird, muss Sammlr explizit klären, was mit den diesem Album zugeordneten physischen Stickern geschieht.

Mögliche spätere Optionen können beispielsweise sein:

- Sticker vollständig aus der eigenen Sammlung entfernen
- Sticker in freien Bestand / Doppelte überführen
- Sticker einem anderen Exemplar zuordnen

Die exakte UI und die exakten Optionen werden später definiert.

Fundamentale Regel:

Keine stillschweigende Bestandsvernichtung oder Bestandsverschiebung.


27. ZUKUNFT: KOMPLETTE ALBUMÜBERTRAGUNG

Als spätere Funktion soll konzeptionell berücksichtigt werden, dass ein komplettes Album möglicherweise direkt von einem Sammlr-Nutzer auf einen anderen übertragen werden kann.

Beispiel:

Nutzer verkauft oder verschenkt ein vollständiges Album an einen anderen Sammlr-Nutzer.

Dies ist ausdrücklich KEIN aktuelles Implementierungsziel.

Die zukünftige Möglichkeit soll lediglich architektonisch nicht unnötig verbaut werden.


28. VITRINE

Ein vollständig abgeschlossenes Albumexemplar wandert automatisch aus „Aktive Alben“ in die Vitrine.

Beispiel:

992/992
→ Vitrine

Die Vitrine repräsentiert tatsächlich vollständige Albumexemplare.


29. VITRINE BEI MEHREREN VOLLEN EXEMPLAREN

Wird später ein zweites Exemplar desselben Albumtyps vollständig, entsteht in der Vitrine eine entsprechende Mehrfach-/Stapeldarstellung.

Mehrere abgeschlossene Exemplare desselben Albumtyps sollen nicht unnötig als identische große Karten nebeneinander erscheinen.


30. ALBUM VERLIERT VOLLSTÄNDIGKEIT

Entfernt der Nutzer aus einem vollständigen Album manuell einen zugeordneten Sticker:

992/992
→ 991/992

ist das Album nicht mehr vollständig.

Es verlässt automatisch die Vitrine und erscheint wieder unter den aktiven Alben, sofern es nicht anderweitig deaktiviert ist.

Die Vitrine bildet den realen Sammlungszustand ab.


31. STICKER IN DER VITRINE

Sticker eines vollständigen Albumexemplars bleiben diesem Album zugeordnet.

Sie sind nicht automatisch Tauschmaterial.

Nur tatsächlich freier Bestand oberhalb der Albumzuordnungen darf in den Tauschpool gelangen.


32. FAVORIT / LIEBLINGSALBUM

Der Favorit bezieht sich auf ein konkretes Albumexemplar.

Besitzt der Nutzer mehrere WM26-Alben, kann beispielsweise sein Hauptalbum Favorit sein.

Die Sammlr-Zentrale kann dieses konkrete Exemplar entsprechend priorisiert darstellen.


33. FORTSCHRITT

Albumfortschritt wird immer pro Albumexemplar berechnet.

Grundprinzip:

Anzahl erfüllter unterschiedlicher Sticker
/
Anzahl benötigter Sticker

Doppelte erhöhen den Albumfortschritt nicht.

Beispiel:

859 von 992 benötigten Stickern vorhanden
→ Fortschritt basiert auf 859/992.

Keine Vermischung mehrerer Albumexemplare zu einem künstlichen Durchschnitt.


34. KAPITELFORTSCHRITT

Kapitel innerhalb eines Albums werden ebenfalls pro Albumexemplar berechnet.

Beispiele:

Intro 1/2
Kader 82/82
Rückblick 11/11

Die bestehende Grundidee der Kapitelbalken bleibt erhalten.


35. TROPHÄEN

Trophäen werden automatisch aus Sammlungsereignissen ausgelöst.

Der Nutzer muss keinen Trophy-Modus aktivieren.

Trophäen sind eine Folge des Sammelns, nicht Teil der eigentlichen Bestandsverwaltung.


36. TROPHÄEN BEI MEHREREN EXEMPLAREN

Albumbezogene Trophäen werden grundsätzlich nicht beliebig mehrfach erzeugt, nur weil derselbe Albumtyp mehrfach vervollständigt wurde.

Beispiel:

WM26 dreimal vollständig.

Die entsprechende zentrale Album-Trophy wird grundsätzlich einmal freigeschaltet.

Statistiken dürfen dagegen erfassen:

„WM26 3× vervollständigt.“

Details einzelner Trophy-Regeln werden in der Trophy-Spezifikation gepflegt.


37. STICKERWALL ALS HAUPTVERWALTUNG

Die Stickerwall bleibt die visuelle Hauptverwaltung eines konkreten Albumexemplars.

Die bestehende Grundstruktur mit:

- Kapiteln
- Stickerkarten
- Suche
- Filtern
- Fortschrittsanzeigen

bleibt grundsätzlich erhalten.

Optik und Interaktionsdetails werden später überarbeitet.


38. DIREKTER MENGENZÄHLER

Die normale Bestandsverwaltung soll langfristig direkt an den Stickerkarten möglich sein.

Bevorzugtes Prinzip:

−  Anzahl  +

Die Anzahl beschreibt den physischen Bestand im jeweiligen Eingabekontext bzw. die dafür relevante Bestandsmenge.

Beispiel:

0 → 1 → 2 → 3

Änderungen sollen im normalen Fall unmittelbar erfolgen, ohne unnötige Bestätigungsdialoge.


39. DESIGNRICHTUNG DES MENGENZÄHLERS

Aktuelle bevorzugte Designrichtung:

Der Mengenregler sitzt UNTER der Stickerkarte und nicht innerhalb der eigentlichen Karte.

Grund:

Die Stickerkarte soll visuell nicht überladen werden.

Die Karte selbst soll künftig stärker für Albumidentität und Stickeridentität genutzt werden.

Der Regler soll kompakt und zurückhaltend gestaltet werden.

Er darf nicht dazu führen, dass eine Stickerwall mit vielen Karten wie eine Wand aus großen Buttons wirkt.

Exaktes UI später festlegen.


40. ZUKÜNFTIGE STICKERKARTEN-DESIGNSPRACHE

Für Sportalben ist aktuell folgende Richtung vorgesehen:

- albumbezogene CI
- beispielsweise Trikot-/Teamoptik
- große, schnell erkennbare Stickernummer bzw. Code
- beispielsweise „80“ oder „GER 23“
- kleines albumbezogenes Wasserzeichen / Branding
- Mengensteuerung separat unter der Karte

Die genaue Designsprache kann je nach Sammelkategorie variieren.

Beispiel:

Pokémon muss nicht zwangsläufig dieselbe visuelle Logik wie Fußballalben verwenden.


41. GROSSE STICKERNUMMERN / CODES

Bei Sportstickern soll die Stickernummer bzw. der Sticker-Code visuell stark priorisiert werden.

Ziel:

Beim Öffnen eines Packs muss der Nutzer einen Sticker sehr schnell identifizieren und seinen Bestand aktualisieren können.

Beispiele:

ARG17
GER23
VfL 80

Die genaue typografische Umsetzung wird später gestaltet.


42. DIREKTE PLUS-LOGIK

Normalfall:

0 → + → 1
Sticker wird dem geöffneten Albumexemplar zugeordnet.

1 → + → 2
weiteres physisches Exemplar vorhanden.

Weitere Plus-Eingaben erhöhen entsprechend den Bestand.

Keine unnötigen Dialoge im normalen Ein-Album-Fall.


43. MEHRFACHALBUM BEI ZUSÄTZLICHEM EXEMPLAR EINES STICKERS

Bei mehreren Albumexemplaren kann eine zusätzliche physische Kopie entweder:

- als freier Doppelter behandelt werden
oder
- einem weiteren fehlenden Albumexemplar zugeordnet werden.

Sammlr soll dafür eine Nutzerpräferenz unterstützen.

Sinngemäße Möglichkeiten:

- jedes Mal fragen
- automatisch an nächstes fehlendes Albumexemplar weitergeben
- automatisch als freien Doppelten behandeln

Beim ersten relevanten Fall kann Sammlr nachfragen und anbieten, die Entscheidung für zukünftige Eingaben zu speichern.

Die Präferenz soll später änderbar sein.


44. MINUS-LOGIK

Minus reduziert den entsprechenden Bestand.

Normalfall:

3 → 2 → 1 → 0

Keine unnötige Nachfrage.

Wenn eine Reduktion jedoch einen verbindlich reservierten oder anderweitig zwingend gebundenen Sticker mathematisch unmöglich machen würde, muss Sammlr warnen oder die Aktion blockieren.


45. RESERVIERTE STICKER

Ein physisch noch vorhandener Sticker kann bereits für einen verbindlichen Trade reserviert sein.

Beispiel:

Gesamt physisch vorhanden: 3
davon Album zugeordnet: 1
davon Trade reserviert: 1
frei tauschbar: 1

Der Smart Trader darf nur mit tatsächlich frei verfügbarem Bestand rechnen.

Reservierter Bestand darf nicht parallel erneut angeboten werden.


46. VERSAND UND BESTANDSÄNDERUNG

Solange ein reservierter Sticker noch nicht versendet wurde, kann er physisch noch beim Nutzer liegen.

Beim Versand wird der ausgehende physische Bestand entsprechend reduziert und der Tradezustand aktualisiert.

Die genaue Trade-State-Logik wird in der Trading-Spezifikation gepflegt.


47. EINGEHENDE STICKER / UNTERWEGS

Ein Sticker, der aus einem bestätigten Trade unterwegs ist, ist noch nicht physisch vorhanden.

Er besitzt einen separaten Zustand:

„unterwegs“

Dieser Sticker darf nicht gleichzeitig weiterhin als normaler offener Bedarf für neue Smart Trades behandelt werden.

Dadurch sollen unnötige Mehrfachbeschaffungen vermieden werden.


48. VERLORENE / GESCHEITERTE SENDUNG

Kommt ein erwarteter Sticker nicht an bzw. scheitert der entsprechende Vorgang, wird der Unterwegs-Zustand entfernt.

Falls der Sticker weiterhin benötigt wird, wird er anschließend wieder als fehlender und Smart-Trade-fähiger Bedarf behandelt.


49. UNTERWEGS IN DER STICKERWALL

Ein unterwegs befindlicher Sticker ist physisch noch fehlend.

Aktuelle Produktentscheidung:

Er kann deshalb weiterhin im Bereich „Fehlende“ sichtbar sein, muss dort jedoch eindeutig als „unterwegs“ bzw. entsprechend visuell markiert werden.

Er wird gleichzeitig aus neuem automatischem Smart-Trade-Bedarf herausgerechnet.


50. FILTER

Die bestehende Filterlogik:

- Alle
- Fehlende
- Vorhandene
- Doppelte

ist grundsätzlich sinnvoll.

Die genaue UI muss jedoch nicht zwingend bei vier großen Switchern bleiben.

Eine kompaktere Filtersteuerung darf später geprüft werden.

Wichtig ist die Funktion, nicht die heutige konkrete Buttonform.


51. FILTER BEI MEHRFACHALBEN

Bei einem konkreten Albumexemplar beziehen sich albumbezogene Zustände auf dieses Exemplar.

Beispiel:

„Fehlende“
→ fehlt in diesem Albumexemplar

„Vorhandene“
→ diesem Albumexemplar zugeordnet / dort erfüllt

Freie Doppelte bzw. Tauschbestand sind dagegen albumtypbezogen.

Diese Unterscheidung muss bei späterem UI-Design verständlich kommuniziert werden.


52. PAPIER-STICKERLISTE

Die bestehende Papierlisten-Ansicht ist eine Kernfunktion von Sammlr.

Sie ist kein dekoratives Nebenfeature.

Sie dient insbesondere:

- Stickerbörsen
- persönlichem Tauschen
- schneller Bestandsarbeit
- Arbeiten mit einem konkreten physischen Album

Die aktuelle Grundidee und auch die grundsätzliche Papier-/Handschrift-Optik sollen erhalten bleiben.


53. PAPIERLISTE: GESCHWINDIGKEIT VOR SCHNICKSCHNACK

Die Papierliste soll mindestens so schnell bedienbar sein wie eine klassische physische Stickerliste.

Grundsatz:

Ein Tap soll für die normale Änderung reichen.

Keine unnötigen:

- Popups
- Animationen
- Bestätigungsdialoge
- verschachtelten Menüs

Die Börsensituation verlangt Geschwindigkeit.


54. PAPIERLISTE PRO ALBUMEXEMPLAR

Bei mehreren Exemplaren besitzt jedes Album seine eigene Papierliste.

Beispiel:

WM26 Hauptalbum
→ eigene Fehlendenliste

WM26 Weglegealbum
→ eigene Fehlendenliste

Dadurch muss die Papierliste keinen künstlichen aggregierten Mehrfachbedarf wie „GER20 ×3“ darstellen.

Der Smart Trader kann Mengen intern aggregieren.

Die physische Börsenliste bleibt einfach und konkret.


55. DOPPELTE IN DER PAPIERLISTE

Mehrere frei verfügbare Exemplare desselben Stickers dürfen weiterhin mehrfach in der Doppeltenliste erscheinen.

Beispiel:

20, 20, 20, 20

statt zwingend:

20 ×4

Das bestehende Papierlisten-Feeling soll erhalten bleiben.


56. MANUELLE BESTANDSKORREKTUR ÜBER PAPIERLISTE

Sticker können direkt über die Papierliste hinzugefügt bzw. entfernt werden.

Beispiele:

- auf Börse erhalten
- verkauft
- verschenkt
- verloren
- anderweitig erworben

Nicht jede Bestandsänderung ist ein Sammlr-Trade.

Deshalb muss manuelle Bestandskorrektur jederzeit möglich bleiben.


57. KEINE ERZWUNGENE TRADEHISTORIE

Wenn der Nutzer einen Sticker beispielsweise:

- auf eBay kauft
- verschenkt
- verliert
- auf einer nicht über Sammlr dokumentierten Börse tauscht

kann er seinen Bestand einfach manuell korrigieren.

Dadurch entsteht nicht automatisch ein Sammlr-Trade oder Statistikereignis.


58. AUSWAHLMODUS / BATCH-MODUS

Der bestehende Auswahlmodus wird nicht vorschnell entfernt.

Für tägliche Einzeländerungen ist der direkte Mengenregler voraussichtlich schneller.

Für initiale Bestandserfassung kann ein Batch-Modus jedoch weiterhin sinnvoll sein.

Beispiel:

Nutzer installiert Sammlr, besitzt aber bereits sehr viele Sticker.

Er kann viele Sticker markieren und gesammelt als vorhanden erfassen.

Die genaue Zukunft des Auswahlmodus wird beim UI-/Workflow-Design entschieden.


59. CODE-EINGABEMODUS

Ein schneller Code-Eingabemodus aus frühen Sammlr-Versionen soll als sinnvolle Eingabeform berücksichtigt werden.

Beispiele:

GER20
ARG17
FWC4

Dies kann insbesondere beim schnellen Erfassen vieler Sticker hilfreich sein.

Der Modus darf bei einer späteren Überarbeitung neu bewertet und verbessert werden.


60. MEHRERE EINGABEMETHODEN

Langfristig kann Sammlr unterschiedliche Eingabemethoden anbieten:

A) Direkte Stickerwall
− Anzahl +

B) Batch-Auswahl
viele Sticker gleichzeitig markieren

C) Code-Eingabe
Sticker-Codes schnell hintereinander erfassen

D) perspektivisch Scanner
automatische visuelle Erkennung

Nicht alle Methoden müssen gleich prominent sein.


61. SUCHE

Die erste Priorität der Stickerwall-Suche liegt auf Sticker-Codes bzw. Stickernummern.

Beispiele:

ARG17
GER23
80

Suche nach Spielernamen, Teams oder weiteren Metadaten kann später erweitert werden.

Die erste Version muss nicht unnötig komplex werden.


62. ZUKUNFT: SCANNER

Langfristiges Ziel ist eine kamerabasierte bzw. KI-gestützte Bestandserfassung.

Vision:

Nutzer fotografiert Albumseiten.

Sammlr erkennt vorhandene bzw. fehlende Sticker und kann daraus den Bestand ableiten.

Bei mehreren Albumexemplaren soll die Erfassung entsprechend einem konkreten Albumexemplar zugeordnet werden können.

Dies ist ausdrücklich kein aktuelles Implementierungsziel.


63. OFFLINE-FÄHIGKEIT

Stickerbörsen können schlechten oder fehlenden Mobilfunkempfang haben.

Langfristige Produktanforderung:

Mindestens die für Börsen besonders wichtigen Funktionen sollen perspektivisch offline bzw. bei instabiler Verbindung nutzbar sein.

Insbesondere relevant:

- Papier-Stickerliste
- lokale Bestandsänderungen

Änderungen sollen später synchronisiert werden können.

Dies ist kein unmittelbares Implementierungsziel, soll aber architektonisch berücksichtigt werden.


64. BÖRSENMODUS UND REALWELT-PHILOSOPHIE

Sammlr soll reale Stickerbörsen nicht ersetzen.

Sammlr unterstützt den Nutzer dort.

Die Papierliste und schnelle Bestandsänderungen sind deshalb zentrale Bestandteile der Produktphilosophie:

„Sammlr ersetzt keine Sammler. Sammlr unterstützt Sammler.“


65. SMART-TRADE-ABHÄNGIGKEIT

Der Smart Trader ist vollständig von korrekten Sammlungsdaten abhängig.

Deshalb muss der Sammlungsbereich eine verlässliche Wahrheit über folgende Dinge liefern können:

- vorhandener Bestand
- Albumzuordnungen
- freie Doppelte
- fehlender Bedarf
- Mehrfachbedarf
- reservierte Sticker
- unterwegs befindliche Sticker
- aktive/deaktivierte Alben

Der Smart Trader darf nicht mit bloßen UI-Zuständen arbeiten, sondern benötigt ein logisch konsistentes Bestandsmodell.


66. DATENPFLEGE UND VERTRAUEN

Sammlr kann nur so gut rechnen wie die gepflegten Bestände seiner Nutzer.

Das Produkt soll deshalb Bestandsänderungen möglichst schnell und angenehm machen.

Langfristiges Ziel:

Nach der initialen Erfassung sollen möglichst viele Bestandsänderungen automatisch aus über Sammlr abgewickelten Trades entstehen.

Dadurch sinkt der manuelle Pflegeaufwand und die Datenqualität steigt.


67. ZIELBILD

Ein Nutzer soll langfristig:

1. Album hinzufügen
2. Bestand schnell erfassen
3. Sticker über Wall, Papierliste, Batch, Code oder später Scanner pflegen
4. automatisch fehlende und freie Sticker berechnen lassen
5. Smart Trades nutzen
6. abgeschlossene Trades automatisch in seinen Bestand übernehmen lassen
7. möglichst wenig manuelle Nacharbeit benötigen

Für normale Nutzer bleibt dies einfach.

Für intensive Sammler unterstützt dasselbe Fundament mehrere Exemplare, Mehrfachbedarf und große albumübergreifende Smart Trades.


68. BEWUSST OFFENE UI-FRAGEN

Noch nicht final entschieden:

- exakte Gestaltung der neuen Stickerkarten
- exakte Größe und Form des − Anzahl +-Reglers
- Verhalten des Reglers bei 0
- endgültige Filterdarstellung
- endgültige Batch-Auswahl
- genaue Code-Eingabe
- visuelle Darstellung „unterwegs“
- genaue Mehrfachalbum-Stapeldarstellung
- genaue Einstellungsoberfläche für automatische Zuordnung
- Löschdialoge
- Scanner-UX
- Offline-Synchronisations-UX

Diese Fragen gehören in spätere Design-/Implementierungssprints.


69. PRODUKTSTATUS

Der Bereich:

SAMMLUNG / ALBEN / STICKERVERWALTUNG

gilt damit auf fachlicher Produktebene als weitgehend spezifiziert.

Vor technischer Implementierung müssen bestehendes Datenmodell und bestehende Anwendung gegen diese Soll-Spezifikation geprüft werden.

Insbesondere Mehrfachalbum, physischer Bestand, Albumzuordnung, freie Doppelte, Reservierungen und Unterwegs-Zustände dürfen nicht ohne vorherige Architekturprüfung in den bestehenden Code eingebaut werden.
