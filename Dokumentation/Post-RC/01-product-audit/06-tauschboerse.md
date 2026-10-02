# Product Audit: Tauschbörse

## Auditstatus

Abgeschlossen am 15. August 2026. Dieses Dokument hält die verbindlichen Ergebnisse des Post-RC Product Audits der Tauschbörse fest. Es enthält keine Umsetzungsaufträge und nimmt die spätere UX Architecture, das Design System oder die UI-Überarbeitung nicht vorweg.

Die langfristige Fachlogik bleibt in den Product-Bible-Spezifikationen [`trading.md`](../../Product%20Bible/specifications/trading.md) und [`trade-lifecycle.md`](../../Product%20Bible/specifications/trade-lifecycle.md) verankert. Dieses Audit bewertet die heutige Produktrolle und Struktur der bestehenden Tauschbörse. Erkannte Spannungen werden ausdrücklich dokumentiert und nicht stillschweigend bereinigt.

## Warum existiert die Tauschbörse?

Die Tauschbörse ersetzt die mühsame manuelle Partnersuche beim Online-Stickertausch weitgehend durch automatisch erkannte Tauschmöglichkeiten.

Beim klassischen Online-Tausch muss ein Sammler fremde Suchlisten und den eigenen Stapel durchsuchen, Überschneidungen selbst vergleichen, andere Nutzer anschreiben und mit ausbleibenden Antworten oder veralteten Listen rechnen. Sammlr kennt dagegen bereits:

- den eigenen Bestand, die eigenen Fehlenden und die eigenen Doppelten,
- die Bestände, Fehlenden und Doppelten anderer Sammler,
- reservierte und anderweitig nicht frei verfügbare Mengen.

Aus diesen Daten soll Sammlr sinnvolle, tatsächlich ausführbare Tauschmöglichkeiten ableiten.

> SmartTrades und automatische Matches sind der Kernnutzen der Tauschbörse.

Die Tauschbörse ist ausdrücklich kein manueller Kleinanzeigenmarkt.

## Was ist ihre Hauptaufgabe?

Die Tauschbörse beantwortet:

1. Mit wem kann ich sinnvoll tauschen?
2. Wie viele Sticker können wir gegenseitig tatsächlich tauschen?
3. Welche fertigen SmartTrade-Vorschläge kann ich prüfen und anfragen?
4. Welche Anfragen und laufenden Trades benötigen meine Aufmerksamkeit?

Sammlr soll die eigentliche Vergleichsarbeit übernehmen. Der Nutzer prüft einen Vorschlag und entscheidet, ob er eine Anfrage senden beziehungsweise eine eingegangene Anfrage annehmen oder ablehnen möchte.

## Was ist die wichtigste Information?

Primär relevant ist die gegenseitig tatsächlich realisierbare Tauschmenge.

Eine Aussage wie „Partner besitzt 20 meiner Fehlenden“ ist irreführend, wenn der Nutzer nur genügend passende Doppelte für sechs davon anbieten kann. Für die erste Priorisierung gilt deshalb:

> Größtmögliche gegenseitig realisierbare Tauschmenge zuerst.

Weitere Sortier- und Qualitätsmerkmale, etwa Bewertung, Zuverlässigkeit, Entfernung oder regionale Nähe, bleiben spätere Produktoptionen. Sie sind keine aktuelle Implementierungsanforderung.

## Was ist die wichtigste Aktion?

Bei einem automatischen SmartTrade lautet die Kernhandlung:

1. Vorschlag prüfen.
2. Anfrage senden oder Vorschlag verwerfen.

Ein SmartTrade ist kein manueller Tradebuilder. Sammlr stellt das Paket aus den bekannten Beständen zusammen. Nach dem Absenden verwendet es denselben Trade-Lifecycle wie jede andere Tauschanfrage.

Bei einem manuellen Online-Trade bleibt die wichtigste Schutzregel erhalten:

> Der Nutzer darf großzügig tauschen, aber nicht geizig.

Der Nutzer darf mehr geben als erhalten, aber nicht mehr verlangen als anbieten. Eine regelwidrige Anfrage wird bereits beim Erstellen verhindert und gelangt im normalen Produktfluss nicht zum Empfänger.

Diese Regel gilt nicht für die Stickerliste als Offline-Tauschwerkzeug. Dort dokumentiert Sammlr auch bewusst ungleiche physische Trades; dieser getrennte Vertrag steht in [`05-stickerliste.md`](05-stickerliste.md).

## Fachlich notwendige Bereiche

Die heutige Dreiteilung ist funktional grundsätzlich brauchbar. Ob der bestehende 3er-Switcher bleibt und wie die endgültige Hierarchie aussieht, wird erst in der UX Architecture entschieden.

Fachlich müssen mindestens unterscheidbar bleiben:

### Albumbezogene Matches

- mögliche Tauschpartner innerhalb eines Albums
- besonders relevant für klassische Ein-Album-Sammler
- in der Übersicht nur Alben, für die tatsächlich Tauschmöglichkeiten bestehen

### Albumübergreifende SmartMatches

- Sammlr kombiniert mögliche Trades über mehrere freigegebene Alben
- langfristig wahrscheinlich der attraktivste Bereich
- zunächst nicht automatisch über albumbezogene Matches stellen
- Hierarchie später anhand realer Nutzung bewerten

### Eingehende Tauschanfragen

Eine neue Anfrage kann über Home beziehungsweise sammlr.-Zentrale, eine Notification oder die Tauschbörse sichtbar werden. Es wird kein zusätzlicher separater Posteingang eingeführt. Die Tauschbörse bleibt das fachliche Zuhause des Vorgangs.

Eine kompakte Anfrageansicht zeigt mindestens:

- Partner
- optional beziehungsweise später zu prüfende kompakte Bewertung
- „Du bekommst“
- „Du gibst“
- Annehmen
- Ablehnen
- Zugang zu weiteren Informationen

Der Partnername soll zum Profil führen können. Vollständige Einzelheiten müssen nicht bereits die erste Karte überladen.

### Laufende Trades

Angenommene Anfragen wechseln in die laufenden Trades. Das heutige Wording „Absprachen“ ist nicht überzeugend; die endgültige Benennung wird in der UX Architecture entschieden.

Abgeschlossene Trades gehören nicht in die operative Tauschbörsenansicht. Sie gehören in die Tradehistorie.

## Annehmen und Ablehnen

### Annahme

- Vor der Annahme wird die aktuelle Erfüllbarkeit erneut geprüft.
- Ist der Trade nicht mehr erfüllbar, bleibt die Anfrage nachvollziehbar, aber die Annahme wird mit fachlicher Erklärung verhindert.
- Es entsteht keine ungültige Reservierung.
- Eine erfolgreiche Annahme erzeugt einen laufenden Trade und reserviert die vereinbarten Sticker.
- Reservierung ist keine endgültige Bestandsbuchung.
- Die Anfrage verschwindet aus „Anfragen“ und erscheint bei den laufenden Trades.

### Ablehnung

- beendet die Anfrage,
- erzeugt keine Reservierung,
- verlangt in der Closed Beta keine verpflichtende Begründung.

Es wird kein unnötiges Ablehnungsformular vorweggenommen.

## Was gehört ausdrücklich nicht in die operative Tauschbörse?

- manuelle Kleinanzeigenlogik
- abgeschlossene Trades zwischen offenen Matches und laufenden Vorgängen
- ein zusätzlicher separater Trade-Posteingang
- komplexe Ablehnungsformulare
- Trackingnummern- oder Versanddienstleisterlogik
- genaue regionale Matchdarstellung
- ein eigener Lifecycle je Trade-Typ oder Album

## Was funktioniert heute bereits gut?

- Albumbezogene Partner und Smart-Trade-Vorschläge sind als getrennte Einstiege vorhanden.
- Anfragen und angenommene Trades bleiben unterscheidbar.
- Fairness wird beim Erstellen manueller und automatischer Anfragen geprüft.
- Annahme, Reservierung und Bestandsverfügbarkeit sind technisch voneinander getrennt.
- Home und Notifications können auf Trade-Handlungsbedarf verweisen, ohne einen eigenen zweiten Tradebereich zu erzeugen.
- Abgeschlossene Trades werden aus der operativen `/trades`-Übersicht herausgehalten.

## Was verursacht fachliche oder UX-seitige Reibung?

- Die aktuelle globale Partnerübersicht sortiert primär nach der Zahl der eigenen Fehlenden beim Partner, nicht nach der beiderseitig tatsächlich realisierbaren Menge.
- Alben ohne konkrete Tauschmöglichkeit werden derzeit trotzdem als leere Bereiche gerendert.
- Albumübergreifende SmartMatches sind noch kein vollständiger End-to-End-Produktpfad.
- Der Partnername einer kompakten Anfragekarte führt heute nicht durchgängig zum Profil; eine kompakte Bewertung ist dort nicht vorhanden.
- Die aktuelle Bezeichnung „Absprachen“ beschreibt laufende Trades nicht überzeugend.
- Die genaue Hierarchie von albumbezogenen Matches, SmartMatches, Anfragen und laufenden Trades ist noch offen.

Diese Befunde werden nicht in UI-Aufgaben umgewandelt, solange UX Architecture und Beta Scope nicht abgeschlossen sind.

## Dokumentierte Spannungen zur bestehenden Product Bible

### Albumübergreifende SmartTrades

[`trading.md`](../../Product%20Bible/specifications/trading.md) führt albumübergreifende SmartTrades in seiner Statusmatrix unter „Später / Vision“. Die aktuelle Product-Owner-Entscheidung bestätigt sie dagegen als notwendigen fachlichen Bereich und wahrscheinlich langfristig attraktivsten Teil der Tauschbörse. Daraus folgt noch kein automatischer Closed-Beta-Implementierungsauftrag; die abweichende Prioritätseinstufung muss aber bei einer späteren bewussten Aktualisierung der Product Bible konsolidiert werden.

### Paketänderung vor Annahme

Das archivierte ältere Trading-Protokoll erlaubt, offene Dealpakete bei Bestandsänderungen automatisch zu verkleinern und abhängig von einer Zustimmungseinstellung weiterzuführen. Die aktuelle Entscheidung legt für eine nicht mehr erfüllbare Anfrage fest: sichtbar und nachvollziehbar lassen, Annahme verhindern, fachlich erklären und keine ungültige Reservierung erzeugen. Ob eine explizit neu berechnete Folgeanfrage zulässig ist, bleibt davon unberührt; die ursprüngliche Anfrage wird nicht stillschweigend verändert.

### Kein weiterer Widerspruch

Fairness, Reservierung erst bei Annahme, getrennte operative Hinweise auf Home/Notifications und die Trennung von offenen Vorgängen und Tradehistorie stimmen grundsätzlich mit der bestehenden Product Bible überein.

## Bewusst vertagte UX-, Design- und Produktfragen

- Fortbestand des 3er-Switchers
- endgültiges Wording für „Absprachen“
- genaue Kartenoptik
- SmartTrade-Priorisierung innerhalb der Tauschbörse
- genaue regionale Matchdarstellung
- Darstellung kompakter Bewertungen
- genaue Sortierauswahl nach der initialen Mengenpriorität
- Farben, Typografie, Animationen und Abstände

Diese Punkte sind Eingaben für [`../02-ux-architecture.md`](../02-ux-architecture.md), [`../04-design-system.md`](../04-design-system.md) und – erst nach den vorgesehenen Entscheidungen – [`../05-ui-backlog.md`](../05-ui-backlog.md).

## Verbindliche Produktregel

> Die Tauschbörse nimmt dem Sammler die mühsame manuelle Partnersuche und Listenabgleichsarbeit ab.
>
> SmartTrades und automatisch erkannte, tatsächlich ausführbare Matches sind ihr Kernnutzen.
>
> Entscheidend ist die gegenseitig realisierbare Tauschmenge, nicht die einseitige Zahl theoretisch verfügbarer Fehlender.
>
> Anfragen und laufende Trades bleiben operativ sichtbar; abgeschlossene Trades wechseln in die Tradehistorie.
>
> Alle Trade-Typen münden nach der Anfrage in denselben Lifecycle.
