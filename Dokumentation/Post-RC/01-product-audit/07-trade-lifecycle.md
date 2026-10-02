# Product Audit: Trade-Lifecycle

## Auditstatus

Abgeschlossen am 15. August 2026. Dieses Dokument hält die verbindlichen Ergebnisse des Post-RC Product Audits des laufenden Trade-Lifecycles fest. Es enthält keine Implementierungs-, UX- oder Designfreigabe.

Die langfristige Dealabwicklung ist bereits in [`trade-lifecycle.md`](../../Product%20Bible/specifications/trade-lifecycle.md) beschrieben. Dieses Audit präzisiert die heute bestätigte Produktperspektive, insbesondere den Zeitpunkt der Bestandsbuchungen und die Rolle der operativen Dealansicht. Widersprüche werden sichtbar gehalten.

## Ein gemeinsamer Lifecycle

Sammlr entwickelt keinen getrennten Abwicklungsprozess für albumbezogene, albumübergreifende oder automatisch erzeugte Trades.

Das gemeinsame Grundmodell lautet:

> MATCH → ANFRAGE → ANNAHME / RESERVIERUNG → VERSAND → EMPFANG → ABSCHLUSS → BEWERTUNG

Optional kann aus der Abwicklung in „Problem melden“ verzweigt werden.

Ein SmartTrade unterscheidet sich in der automatischen Zusammenstellung des Vorschlags, nicht in seiner späteren Abwicklung.

## Warum existiert die Dealansicht?

Die Dealansicht begleitet einen bereits konkreten Tausch zuverlässig durch seine Abwicklung. Sie beantwortet:

1. Mit wem tausche ich?
2. Was bekomme ich?
3. Was gebe ich?
4. Was ist der aktuelle Status?
5. Was muss ich als Nächstes tun?

Der Tradeinhalt selbst enthält die Stickerdetails bereits. Ein persistenter unterer Aktionsbereich soll diese Informationen nicht unnötig wiederholen, sondern primär die aktuell notwendige Nutzeraktion anbieten.

## Anfrage und Erfüllbarkeitsprüfung

Eine Anfrage ist noch kein Trade und reserviert nichts.

Verändert sich vor der Annahme der reale Bestand einer beteiligten Seite, gilt:

- Die Anfrage bleibt sichtbar und nachvollziehbar.
- Sammlr prüft die Erfüllbarkeit erneut.
- Ist der vereinbarte Trade nicht mehr erfüllbar, wird die Annahme verhindert.
- Der Nutzer erhält eine klare fachliche Erklärung.
- Es entsteht keine ungültige oder teilweise falsche Reservierung.

## Annahme und Reservierung

Eine erfolgreiche Annahme erzeugt den laufenden Trade. Sämtliche vereinbarten abzugebenden Positionen werden atomar reserviert.

Reservierung bedeutet:

- Der Sticker ist physisch noch beim Nutzer.
- Er ist für diesen Trade gebunden.
- Er darf nicht parallel in einem anderen Match oder Trade angeboten werden.
- Der physische Bestand wird noch nicht endgültig reduziert.

Eine Ablehnung beendet nur die Anfrage. Sie erzeugt weder Reservierung noch Tradehistorieneintrag und benötigt in der Closed Beta keine verpflichtende Begründung.

## Versand

Für den Closed-Beta-Scope gilt zunächst:

- Jeder Nutzer bestätigt den eigenen Versand unabhängig.
- Nutzer A kann versenden, obwohl Nutzer B noch nicht versendet hat, und umgekehrt.
- Eine Trackingnummer ist nicht verpflichtend.
- Es gibt keine komplexe Versanddienstleister-Integration.

Der Lifecycle muss getrennte Versandzustände je Seite abbilden.

## Verbindlicher Vertrag der Bestandsbuchung

### Abgegebene Sticker

Sobald ein Nutzer bestätigt „Ich habe meine Sticker versendet“, werden die von ihm abgegebenen Sticker aus seinem physischen Bestand gebucht.

Dabei wird die zugehörige Reservierung korrekt aufgelöst beziehungsweise in den Versandzustand überführt. Die Buchung wartet nicht auf den Versand oder Empfang der Gegenseite und nicht auf den Gesamtabschluss des Trades.

### Erhaltene Sticker

Sobald ein Nutzer bestätigt „Ich habe die Sticker erhalten“, werden die tatsächlich erhaltenen Sticker seinem physischen Bestand hinzugefügt.

Auch diese Buchung wartet nicht auf die Empfangsbestätigung der Gegenseite. Der Gesamttrade kann nach einer einseitigen Empfangsbestätigung weiterhin offen sein.

### Zusammenfassung

> Eigener bestätigter Versand → eigene abgegebene Sticker werden ausgebucht.
>
> Eigener bestätigter Empfang → eigene erhaltene Sticker werden eingebucht.
>
> Der Gesamtabschluss ist kein Sammel-Buchungszeitpunkt.

Dieser Vertrag entspricht der physischen Realität und muss Engineering-seitig besonders abgesichert bleiben.

## Status und nächste Aktion

Die heutige große Timeline enthält fachlich sinnvolle Zustände, ist aber visuell und hierarchisch zu dominant. Für die spätere UX Architecture ist ein kompakterer Status nach Art einer Paket- oder Versandstatusanzeige zu prüfen.

Relevante Zustände sind beispielsweise:

- Anfrage gesendet
- Anfrage angenommen
- Sticker reserviert
- eigener Versand bestätigt
- Gegenseite versendet
- eigener Empfang bestätigt
- Gegenseite bestätigt
- Trade abgeschlossen

Details können später gegebenenfalls aufklappbar sein. Dieses Audit entscheidet keine Darstellung.

Der persistente Aktionsbereich soll primär die nächste notwendige Aktion zeigen, beispielsweise:

- Anfrage annehmen
- Versand bestätigen
- Empfang bestätigen
- Status prüfen beziehungsweise Trade abschließen

Die exakte Sticky-/Dock-Darstellung bleibt offen.

## Problem melden

Für die Closed Beta ist ein einfacher Problemzustand notwendig, etwa für:

- Sendung nicht angekommen
- falscher Sticker
- beschädigte Sendung
- sonstiges relevantes Problem

Ein offener Problemzustand stoppt den normalen automatischen Abschluss beziehungsweise versetzt den Trade in einen klärungsbedürftigen Zustand. Der Nutzer darf nicht gezwungen werden, einen problematischen Trade als erfolgreich abzuschließen.

Es wird kein komplexes Dispute-, Mediations- oder Schiedsgerichtssystem vorweggenommen.

## Abschluss und Tradehistorie

Wenn die notwendigen Empfangsbestätigungen vorliegen und kein offener Problemzustand besteht, wird der Trade abgeschlossen.

Danach:

- verschwindet er aus den laufenden Trades,
- erscheint er in der Tradehistorie,
- wird eine Bewertung möglich.

Abgelehnte oder lediglich verfallene Anfragen sind keine abgeschlossenen Trades und gehören nicht in die normale Tradehistorie.

## Bewertung

Gewünscht ist eine Sternebewertung nach abgeschlossenem beziehungsweise entsprechend qualifiziertem Trade.

Noch nicht festgelegt sind:

- genaue Darstellung,
- Textbewertung,
- strukturierte Bewertungsgründe,
- Aggregations- und Vertrauenslogik.

Die Bewertung soll perspektivisch Vertrauen bei zukünftigen Tauschpartnern schaffen. Die konkrete Komponente wird nicht in diesem Audit entworfen.

## Mehrere Alben, ein Trade

Ein Trade darf Positionen aus mehreren Alben enthalten. Konzeptionell gilt:

> Trade → Positionen → jede Position kennt mindestens Album, Sticker, Menge und Richtung beziehungsweise Seite.

Der Lifecycle bleibt dabei ein gemeinsamer Vorgang. Es gibt keine separate Lifecycle-Implementierung je Album.

## Was funktioniert heute bereits gut?

- Annahme und Reservierung sind atomar gekoppelt.
- Nicht verfügbare Positionen verhindern eine ungültige Annahme.
- Beide Seiten besitzen getrennte Versand- und Empfangszustände.
- Eigener Versand reduziert die eigenen ausgehenden physischen Bestände und löst Reservierungen aus dem aktiven Zustand.
- Eigener Empfang bucht die eingehenden Positionen unmittelbar ein.
- Der Gesamtabschluss wartet auf beide Empfangsseiten und einen problemfreien Zustand.
- Problemberichte, Teilempfangslogik, Timeline, Notifications und Sternebewertungen sind technisch angelegt.
- Abgeschlossene Trades werden nicht in der operativen `/trades`-Übersicht geführt.
- Das versionierte `trade_positions`-Modell kennt Album, Sticker, Menge, Absender und Empfänger je Position.

## Was verursacht fachliche oder UX-seitige Reibung?

- Der aktuelle persistente Bereich „Aktueller Tausch“ wiederholt Stickerdetails, die bereits im Dealinhalt stehen.
- Die Timeline ist gegenüber der nächsten Nutzeraktion zu dominant.
- Der bestehende Globalpfad und die Legacy-`trade_requests`-Darstellung bleiben im sichtbaren Produkt stark an eine einzelne `album_id` und zwei Code-Listen gebunden; ein albumübergreifender SmartTrade ist trotz positionsfähigem Lifecycle-Schema noch kein vollständiger End-to-End-Pfad.
- Die endgültige Bezeichnung und Hierarchie laufender Trades ist noch offen.

## Dokumentierte Spannungen zur bestehenden Product Bible

### Bestandsbuchung

Die Statusmatrix von [`trading.md`](../../Product%20Bible/specifications/trading.md) formuliert verkürzt, erst bestätigter Empfang führe zur „finalen Bestandsänderung“. Isoliert gelesen könnte dies wie eine gesamte Buchung erst beim Empfang oder Gesamtabschluss wirken. Die detaillierteren Abschnitte in [`collection.md`](../../Product%20Bible/specifications/collection.md) und [`trade-lifecycle.md`](../../Product%20Bible/specifications/trade-lifecycle.md) trennen die Vorgänge bereits: ausgehender physischer Bestand beim Versand, eingehender Bestand beim eigenen Empfang. Die heutige Entscheidung bestätigt diese detaillierte Auslegung ausdrücklich.

### Paketänderung vor Annahme

Die ältere Möglichkeit einer automatischen Verkleinerung offener Pakete steht in Spannung zum heutigen Vertrag, eine nicht mehr erfüllbare ursprüngliche Anfrage sichtbar zu lassen und ihre Annahme zu blockieren. Eine Neuberechnung kann einen neuen Vorschlag erzeugen; die ursprüngliche Anfrage wird nicht heimlich verändert.

### Bewertung

Der bereits dokumentierte alte Widerspruch bleibt bestehen: Das archivierte Original in `trading.md` öffnet Bewertungen nach beidseitigem Versand, die neuere Lifecycle-Spezifikation und dieses Audit erst nach tatsächlicher Abwicklung beziehungsweise Empfang. Die neuere Lifecycle-Regel bleibt maßgeblich.

## Bewusst vertagte UX-, Design- und Produktfragen

- genaue Timeline-Darstellung
- exakte Sticky-/Dock-Darstellung
- endgültiges Wording für laufende Trades
- genaue Bewertungskomponente
- Kartenoptik und Informationsdichte
- Animationen, Farben und Typografie
- genaue UX eines einfachen Problemzustands

Diese Punkte sind Eingaben für [`../02-ux-architecture.md`](../02-ux-architecture.md), [`../04-design-system.md`](../04-design-system.md) und – erst nach den vorgesehenen Entscheidungen – [`../05-ui-backlog.md`](../05-ui-backlog.md).

## Verbindliche Produktregel

> Alle Online-Trade-Typen verwenden denselben Lifecycle.
>
> Annahme erzeugt Reservierungen, aber noch keine endgültige Bestandsbuchung.
>
> Eigener Versand bucht die eigenen abgegebenen Sticker aus; eigener Empfang bucht die eigenen erhaltenen Sticker ein.
>
> Ein offener Problemzustand verhindert den normalen Abschluss.
>
> Nach Abschluss verlässt der Trade die operative Ansicht, wechselt in die Historie und kann bewertet werden.
