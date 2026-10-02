# Product Audit: Stickerliste

## Auditstatus

Abgeschlossen am 14. August 2026. Dieses Dokument hält die verbindlichen Ergebnisse des Post-RC Product Audits der Stickerliste fest. Es enthält keine Umsetzungsaufträge und nimmt keine konkrete UX-, Design- oder Engineering-Lösung vorweg.

## Warum existiert die Seite?

Die Stickerliste ist der digitale Tauschzettel des Sammlers. Sie ist bewusst wesentlich fokussierter als Sammlung und Album.

Die Produktlandkarte lautet:

- **sammlr.-Zentrale:** Was passiert gerade für mich und in meiner Sammlr-Welt?
- **Sammlung:** Was besitze ich? Digitales Regal.
- **Album:** Was steckt in diesem Album? Digitales Sammelalbum.
- **Stickerliste:** Was fehlt mir und was kann ich abgeben? Digitaler Tauschzettel.

Die Seitenidentitäten von Sammlung und Album werden verbindlich in [`03-sammlung.md`](03-sammlung.md) und [`04-album.md`](04-album.md) gepflegt. Die obige Landkarte dient hier nur der Einordnung der Stickerliste und ersetzt diese Audits nicht.

**Transparenter Begriffskonflikt:** Die heute bestätigte Produktlandkarte und das bestehende Post-RC-Audit verwenden „sammlr.-Zentrale“ für den persönlichen Home-Einstieg. Die älteren Product-Bible-Spezifikationen [`../../Product Bible/specifications/collection.md`](../../Product%20Bible/specifications/collection.md) und [`../../Product Bible/specifications/home.md`](../../Product%20Bible/specifications/home.md) reservieren „Sammlr-Zentrale“ dagegen für den von Home getrennten Sammlungseinstieg. Beide Aussagen bleiben dokumentiert; dieses Audit löst den Namenskonflikt nicht eigenständig und überschreibt die Product Bible nicht.

Die Stickerliste verbindet die digitale Bestandsverwaltung von Sammlr unmittelbar mit dem realen Sammeln und Tauschen außerhalb der App.

## Was ist ihre Hauptaufgabe?

Die Stickerliste existiert primär für die schnelle Nutzung im realen Sammelalltag. Besonders wichtig sind:

- Stickerbörsen
- persönliche Tauschtreffen
- Schulhof, Verein und Freundeskreis
- andere Offline-Tauschsituationen
- schnelles Nachschlagen fehlender Sticker
- schnelles Nachschlagen doppelter Sticker
- direktes Dokumentieren eines physischen Tauschs

Sie ist Werkzeug und Arbeitsgrundlage des Sammlers. Sie versucht nicht, eine physische Stickerbörse zu ersetzen; Sammlr unterstützt den realen Tauschprozess.

## Was ist die wichtigste Information?

Die Stickerliste besitzt bewusst nur zwei fachliche Hauptbereiche:

1. Fehlende Sticker
2. Doppelte Sticker

Beide Bereiche befinden sich untereinander auf derselben Seite. Es gibt keinen erzwungenen Wechsel zwischen zwei separaten Seiten.

Auf einer realen Stickerbörse kann der Nutzer dadurch zunächst markieren, welche fehlenden Sticker er erhält, und anschließend direkt darunter markieren, welche Doppelten er abgibt. Diese einfache lineare Arbeitsweise ist ausdrücklich gewünscht.

Die Sticker werden in der Reihenfolge des physischen Albums dargestellt, zum Beispiel `FWC → MEX → RSA → BRA → …`. Digitaler Tauschzettel und physisches Album verwenden damit dieselbe mentale Reihenfolge.

Es gibt keine automatische alphabetische Sortierung, keine Sortierung nach Seltenheit und keine algorithmische „Smart Sortierung“, welche die Albumreihenfolge zerstört.

## Was ist die wichtigste Aktion?

Die wichtigste Aktion ist das schnelle Markieren erhaltener und abgegebener Sticker während eines physischen Tauschs.

Der gewünschte Ablauf:

1. Der Nutzer markiert unter „Fehlende Sticker“ die Sticker, die er erhält.
2. Der Nutzer markiert unter „Doppelte Sticker“ die Sticker, die er abgibt.
3. Beide Seiten landen in der temporären Zusammenstellung „Aktueller Tausch“.
4. Der Nutzer prüft die Auswahl.
5. Nach der Bestätigung wird der Bestand entsprechend aktualisiert.

„Aktueller Tausch“ bezeichnet hier die lokale Zusammenstellung und Prüfung des physischen Tauschs. Der bestehende fachliche Vertrag bleibt unberührt: Der Papierlistentransfer bucht die Zu- und Abgänge für den aktuellen Nutzer und erzeugt keinen digitalen Trade-Lifecycle beziehungsweise keine `trade_requests`-Zeile.

Die genaue spätere UI-Ausgestaltung wird erst in den zuständigen UX- und Designphasen entschieden.

## Was gehört ausdrücklich nicht auf diese Seite?

- Trophäen
- Communityfeed
- Freunde
- News
- allgemeine Statistiken
- Privacy-Einstellungen
- Empfehlungen
- vollständige Tradehistorie
- allgemeine Notifications
- Communityaktivitäten
- sonstige Dashboard-Inhalte

Die Produktregel für die Abgrenzung lautet:

> Fehlende. Doppelte. Fertig.

Die Einfachheit der Stickerliste ist ausdrücklich eine Stärke.

## Was funktioniert heute bereits gut?

- extrem klarer Anwendungsfall
- sehr geringe fachliche Komplexität für den Nutzer
- starke Verbindung zwischen digitalem und physischem Sammeln
- schnelle Nutzung auf Stickerbörsen
- Fehlende und Doppelte direkt verfügbar
- physische Trades können unmittelbar dokumentiert werden
- Albumreihenfolge entspricht dem realen Arbeitsablauf
- Grundlage für zukünftige Share- und Exportfunktionen
- bereits vorhandene eigenständige Produktidentität

### Bewertung

- **Produktkonzept:** sehr stark und weitgehend abgeschlossen.
- **Grundlegender Funktionsumbau:** aktuell nicht erforderlich.
- **Wesentliche spätere Arbeit:** UX-Verfeinerung, visuelle Rückkehr zu einer konsequenteren Tauschzettel-Identität, Share-/Exportkonzept und technische Bewertung der Offline-Fähigkeit.

## Was verursacht fachliche oder UX-seitige Reibung?

- Die neuere Darstellung mit stärkerer Standard- beziehungsweise Display-Typografie bei den Stickercodes schwächt gegenüber der älteren, konsequenter handschriftlichen Darstellung die Identität als digitaler Tauschzettel.
- Der zentrale Einsatz auf realen Stickerbörsen kann durch schlechte oder überlastete Mobilfunkabdeckung erschwert werden.
- Auswahl, Prüfung und Bestätigung eines physischen Tauschs benötigen später eine klare UX, ohne die fokussierte lineare Arbeitsweise zu überladen.

Die konkrete Schrift, Typografie, Lesbarkeit, Größen und visuelle Gestaltung werden erst in der Designphase entschieden. Es werden jetzt keine Fonts oder Styles festgelegt oder verändert.

## Welche Produktentscheidungen wurden getroffen?

### Zwei Hauptbereiche auf einer Seite

Fehlende und Doppelte stehen untereinander auf derselben Seite. Die lineare Arbeitsweise wird nicht durch zwei getrennte Seiten unterbrochen.

### Reihenfolge des physischen Albums

Sticker werden verbindlich in der Reihenfolge des physischen Albums dargestellt. Alphabetische, seltenheitsbasierte oder algorithmische Sortierungen dürfen diese mentale Reihenfolge nicht ersetzen.

### Dokumentation physischer Trades

Erhaltene und abgegebene Sticker können für einen physischen Tausch markiert, gemeinsam geprüft und nach Bestätigung in den Bestand gebucht werden.

### Beliebig ungleiche physische Trades

Physische Trades dürfen beliebig ungleich sein, zum Beispiel:

- 3 erhalten / 3 abgegeben
- 3 erhalten / 8 abgegeben
- 15 erhalten / 2 abgegeben
- nur erhalten
- nur abgegeben

Sammlr bewertet die Fairness eines physischen Trades nicht. Die Stickerliste dokumentiert, was tatsächlich passiert ist. Dies entspricht der bestehenden Produktphilosophie für Offline-Trades.

### Unterstützung statt Ersatz

Die Stickerliste unterstützt reale Stickerbörsen und andere physische Tauschsituationen. Sie soll diese nicht ersetzen.

### Eine Datenbasis, verschiedene Darstellungen

Die Stickerliste ist die natürliche Datenbasis für die bereits vorgemerkte zukünftige Funktion „Share Trade List“. Eine gemeinsame fachliche Datenquelle kann später unterschiedliche Darstellungen erzeugen:

- interaktive Stickerliste innerhalb von Sammlr
- Share-Bild
- Download- oder Exportdarstellung
- Tauschzettel für soziale Netzwerke, Messenger oder Marktplätze
- QR-basierte öffentliche Tauschliste

Für diese Anwendungsfälle werden keine separaten fachlichen Listen erzeugt. Es gilt: eine Datenbasis, verschiedene Darstellungen.

## Welche Ideen werden bewusst für UX/UI oder später zurückgestellt?

### Offline-Nutzung

Die Stickerliste soll perspektivisch auch bei schlechtem oder fehlendem Mobilfunk sinnvoll nutzbar sein. Ihr zentraler Anwendungsfall sind reale Stickerbörsen und andere Offline-Tauschsituationen, in denen die Netzabdeckung schlecht oder überlastet sein kann.

Dies ist eine wichtige Produktanforderung, wird aber jetzt ausdrücklich nicht automatisch als Closed-Beta-P0 eingestuft. Technischer Aufwand und Beta-Priorität werden später in den dafür vorgesehenen Engineering- und Beta-Scope-Phasen bewertet. Es wird keine Offline-Implementierung vorgezogen.

### Visuelle Identität einer Share-Liste

Eine geteilte Stickerliste soll später eher wie ein hochwertiger digitaler beziehungsweise handgeschriebener Tauschzettel wirken als wie eine generische Social-Media-Werbegrafik.

Mögliche Bestandteile:

- Papier- oder Notizbuchcharakter
- Handschrift
- Fehlende Sticker
- Doppelte Sticker
- dezentes „Erstellt mit sammlr.“
- Sammlr-Branding
- optionaler QR-Code

Langfristig kann eine Sammlr-Tauschliste bereits anhand ihrer Gestaltung wiedererkennbar sein. Es wird jetzt keine Gestaltung festgelegt oder umgesetzt.

### Design-Beobachtung

Der Nutzer bevorzugt bei der Stickerliste aktuell die ältere, konsequenter handschriftliche Darstellung gegenüber der neueren Version mit stärkerer Standard- beziehungsweise Display-Typografie bei den Stickercodes.

Der handgeschriebene Charakter ist auf dieser Seite nicht ausschließlich Dekoration. Er unterstützt die Produktidentität als digitaler Tauschzettel. Die konkrete Schrift, Typografie, Lesbarkeit, Größen und visuelle Gestaltung bleiben der späteren Designphase vorbehalten.

### Offene UX-, Design- und Engineering-Fragen

Noch nicht entschieden werden:

- genaue Auswahlmechanik
- genaue Darstellung des aktuellen Tauschs
- Sticky-Verhalten
- Typografie
- Handschrift-Auswahl
- visuelle Kennzeichnung ausgewählter Sticker
- Share-Card-Layout
- QR-Platzierung
- Offline-Technik
- Exportformat
- Downloadformat

Diese Punkte gehören in spätere UX-, Design- oder Engineering-Phasen und sind keine aktuellen Umsetzungsaufträge.

## Verbindliche Produktregel

> Die Stickerliste ist der digitale Tauschzettel des Sammlers.
>
> Sie zeigt fehlende und doppelte Sticker in der Reihenfolge des physischen Albums und dient insbesondere der schnellen Nutzung in realen Tauschsituationen.
>
> Der Nutzer kann erhaltene und abgegebene Sticker unmittelbar für einen physischen Tausch markieren.
>
> Die Stickerliste bleibt bewusst fokussiert: Fehlende. Doppelte. Fertig.
>
> Sie unterstützt die reale Sammelkultur, statt sie zu ersetzen.
