# Bereich 04: Home / Startseite

| Metadatum | Wert |
| --- | --- |
| Status | Working Product Specification |
| Bereich | Home / Startseite |
| Stand | 2026-07-26 |
| Änderungshinweis | Änderungen nur bewusst nach neuer Produktentscheidung vornehmen. |

## Dokumentcharakter

Dieses Dokument ist ein langfristiges Produkt-/Lastenheft. Es ist ausdrücklich keine kurzfristige Codex-Todo-Liste und keine Aussage darüber, welche beschriebenen Funktionen bereits implementiert sind. Aus diesem Dokument folgt ohne gesonderte Priorisierung und Umsetzungsentscheidung kein unmittelbarer Implementierungsauftrag.

Das am Ende archivierte Produktprotokoll ist vollständig und inhaltlich übernommen. Die folgende Statusmatrix dient ausschließlich der eindeutigen Auslegung seiner Aussagen.

## BESCHLOSSEN / KERNLOGIK

Als langfristige Produktprinzipien und Kernarchitektur beschlossen sind insbesondere:

- Home / Startseite und Sammlr-Zentrale sind zwei eigenständige Bereiche mit unterschiedlichen Aufgaben.
- Die Sammlr-Zentrale zeigt den Zustand der eigenen Sammlung; Home zeigt aktuelle Ereignisse und Handlungsbedarf.
- Home ersetzt weder die Sammlr-Zentrale noch die vollständigen Fachbereiche für Sammlung und Tauschen.
- Home priorisiert notwendige Handlungen, relevante laufende Vorgänge, das persönliche Netzwerk und allgemeine Sammlr-Neuigkeiten in dieser Reihenfolge.
- Auf Home erscheinen primär aktuelle beziehungsweise offene Meldungen. Eine gesonderte Benachrichtigungszentrale kann zusätzlich ältere oder abgelaufene Meldungen enthalten.
- Benachrichtigungen, Feed-Ereignisse und Tradehistorie sind fachlich unterschiedliche Konzepte.
- Laufende Trades und Sendungen werden auf Home nur kompakt zusammengefasst; die vollständige Verwaltung bleibt unter „Tauschen → Meine Trades“.
- Smart-Match-Suche, vollständige Smart-Trade-Entdeckung und dauerhaft sichtbare Albumverwaltung gehören nicht auf Home.
- Albuminformationen erscheinen auf Home ereignisbasiert, nicht als dauerhaftes Sammlungs-Dashboard.
- Freundesaktivitäten und Sammlr News bleiben getrennte Inhaltsbereiche.
- Sammlr erhält keinen beliebigen globalen Social-Media-Feed und erzeugt keinen künstlichen Content zur Verlängerung der Nutzungszeit.
- Ein Home ohne offene Aufgaben ist ein positiver „Alles erledigt“-Zustand.
- Home informiert, ermöglicht ausgewählte direkte Aktionen und verteilt anschließend in die zuständigen Fachbereiche.
- Die Navigation wird in [`navigation-information-architecture.md`](navigation-information-architecture.md) definiert: Home ist der mittlere Startpunkt; Freunde erhalten keinen eigenen permanenten Bottom-Navigationspunkt.

Diese Festlegungen beschreiben die Zielarchitektur. Sie gelten nicht automatisch als bereits implementiert.

## NOCH ZU ENTSCHEIDEN

Bewusst offen sind:

- genaue Anzahl sichtbarer Home-Benachrichtigungen,
- exakte Sortierung bei mehreren dringenden Aufgaben,
- genaue Feed-Events für Freunde,
- genaue Kategorien von Sammlr News,
- exaktes Layout der beiden Newsbereiche,
- genaue Badge-Logik,
- Dauer der Benachrichtigungshistorie,
- welche erledigten Meldungen archiviert werden,
- genaue Leerzustände,
- exakte Wortwahl,
- Detailgestaltung und spätere Erweiterungen der Navigation,
- mögliche spätere Personalisierung von Home.

Diese Punkte gehören in spätere Detail-/UI-Spezifikationen und verhindern nicht die weitere Produktplanung. Sie dürfen nicht beiläufig durch eine Implementierung als endgültige Produktentscheidung festgeschrieben werden.

## SPÄTER / VISION

Ausdrücklich keine aktuelle Implementierungsanforderung sind insbesondere:

- die konkrete visuelle Gestaltung und Reihenfolge der Home-Bereiche,
- eine vollständige Benachrichtigungszentrale samt Historien- und Archivierungslogik,
- spätere Personalisierung von Home,
- Detailentscheidungen zu Navigation, Badges, Leerzuständen und Feed-Kategorien.

Diese Punkte bleiben Teil des langfristigen Zielbilds, dürfen aber nicht als bereits priorisierte oder freigegebene Umsetzung gelesen werden.

## Abgleich mit bestehender Dokumentation

Die Spezifikation [`profile-community.md`](profile-community.md) beschreibt Home in ihrem archivierten Originalprotokoll noch als mögliche Community-Zentrale und lässt die Feed- und Benachrichtigungsarchitektur ausdrücklich für eine spätere Home-Spezifikation offen. Das vorliegende, gleich datierte Dokument ist diese angekündigte Folgespezifikation und konkretisiert beziehungsweise ersetzt für den Bereich Home den dort dokumentierten vorläufigen Planungsstand.

Dabei werden die dort bereits angelegten Grundideen bestätigt: Freundesaktivitäten können auf Home erscheinen, Feed und Benachrichtigungen sind zu trennen und ein eigener permanenter Freunde-Navigationspunkt ist nicht zwingend. Präzisiert wird insbesondere, dass Home keine allgemeine Community-Zentrale, keine zweite Sammlungsverwaltung und kein zweiter vollständiger Tradebereich ist.

Die Spezifikation [`trading.md`](trading.md) bleibt maßgeblich für Smart-Trader-Mechanik und Dealfindung; [`trade-lifecycle.md`](trade-lifecycle.md) definiert Dealabwicklung, Versandzustände und Tradehistorie. Home zeigt davon nur offene Handlungen und kompakte Zusammenfassungen. Eine Benachrichtigungshistorie ist ausdrücklich keine Tradehistorie.

Die genaue Logik der Sammlr-Zentrale wird in der Spezifikation [`collection.md`](collection.md) definiert. Home und Sammlr-Zentrale sind verbindlich als unterschiedliche Bereiche dokumentiert.

Die Spezifikation [`navigation-information-architecture.md`](navigation-information-architecture.md) definiert Home als mittleren Startpunkt der dreiteiligen Hauptnavigation. Ihre einzelne Gleichsetzung von „Home / Sammlr-Zentrale / zentrale Startseite“ steht terminologisch im Konflikt mit diesem Dokument; bis zu einer bewussten Umbenennung bleibt „Sammlr-Zentrale“ der von Home getrennte Sammlungseinstieg.

---

## Archiviertes Originalprotokoll – vollständig und inhaltlich übernommen

SAMMLR PRODUCT SPECIFICATION

BEREICH: HOME / STARTSEITE

Stand: 2026-07-26

Status: Working Product Specification

### 1. Grundsätzliche Trennung: Home vs. Sammlr-Zentrale

Sammlr besitzt langfristig zwei unterschiedliche Bereiche, die nicht miteinander vermischt werden sollen:

A) SAMMLR-ZENTRALE  
= Ort der eigenen Sammlung

B) HOME / STARTSEITE  
= Ort für aktuelle Ereignisse, Handlungsbedarf, laufende Vorgänge, Freundesaktivitäten und Sammlr-Neuigkeiten.

Die bestehende Sammlr-Zentrale mit Lieblingsalbum, aktiven Alben und Vitrine bleibt vom Grundprinzip erhalten.

Home ersetzt diese Zentrale NICHT.

### 2. Sammlr-Zentrale

Die Sammlr-Zentrale beantwortet primär:

„Wie sieht meine Sammlung aus?“

Dort befinden sich insbesondere:

- Lieblingsalbum
- aktive Alben
- Albumfortschritt
- Doppelte
- fehlende Sticker
- Album hinzufügen
- Vitrine abgeschlossener Alben
- Einstieg in die jeweilige Stickerverwaltung

Die genaue Sammlungslogik wird in einer eigenen Product Specification „Sammlung“ definiert.

Home soll diese Informationen nicht unnötig duplizieren.

### 3. Home

Home beantwortet primär zwei Fragen:

A) Was ist seit meinem letzten Besuch passiert?  
B) Was benötigt jetzt meine Aufmerksamkeit?

Home ist damit die operative Eingangshalle von Sammlr.

Home ist KEIN klassisches Dashboard voller dauerhafter Kennzahlen.

Home ist KEINE zweite Sammlungsverwaltung.

Home ist KEIN zweiter vollständiger Tradebereich.

### 4. Grundstruktur von Home

Der aktuelle konzeptionelle Aufbau besteht aus vier Ebenen:

1. aktueller Handlungsbedarf / offene Benachrichtigungen
2. kompakte Zusammenfassung laufender Trades / Sendungen
3. Freundesaktivitäten
4. Sammlr News

Die genaue visuelle Gestaltung und Reihenfolge wird später im UI-Design festgelegt.

Die funktionale Trennung dieser Bereiche soll jedoch erhalten bleiben.

### 5. Handlungsbedarf

Ganz oben auf Home stehen Dinge, bei denen der Nutzer aktiv werden muss.

Beispiele:

„Rolf möchte 17 Sticker mit dir tauschen.“

„Versende Amelies Sticker innerhalb der nächsten 4 Tage.“

„Neue Freundesanfrage von Peter.“

„Bestätige den Erhalt deiner Sticker.“

„Deine Tauschanfrage wurde angepasst. Bitte erneut bestätigen.“

Diese Meldungen besitzen höhere Priorität als allgemeine Feed-Ereignisse.

### 6. Home zeigt primär offene Meldungen

Auf Home sollen primär aktuelle bzw. noch offene Meldungen erscheinen.

Sobald eine notwendige Handlung erledigt wurde, muss die Meldung nicht dauerhaft auf Home verbleiben.

Grundprinzip:

Home soll übersichtlich bleiben und den aktuellen Zustand zeigen.

Eine vollständige bzw. historische Benachrichtigungsansicht existiert separat über die Benachrichtigungszentrale.

### 7. Benachrichtigungszentrale / Glocke

Home erhält langfristig einen gut sichtbaren Zugang zu einer Benachrichtigungszentrale, beispielsweise über eine Glocke mit rotem Badge.

Die Benachrichtigungszentrale enthält mehr als nur die aktuell auf Home sichtbaren Aufgaben.

Dort können beispielsweise auch ältere oder bereits abgelaufene Meldungen eingesehen werden.

Beispiel:

„Ralfs Tauschanfrage über 17 Sticker ist abgelaufen.“

WICHTIG:

Benachrichtigungshistorie ist NICHT dasselbe wie Tradehistorie.

Eine abgelaufene Tauschanfrage kann in der Benachrichtigungshistorie sichtbar bleiben, obwohl sie gemäß Trade-Spezifikation nicht als abgeschlossener Trade in Statistiken oder Tradehistorie eingeht.

### 8. Benachrichtigungen vs. Feed

Diese beiden Konzepte sind strikt zu unterscheiden.

BENACHRICHTIGUNG:  
verlangt Aufmerksamkeit oder informiert über einen direkt relevanten Vorgang.

Beispiele:

- Tradeanfrage
- Versandfrist
- Freundesanfrage
- Bestätigung erforderlich
- Paket / Sticker angekommen
- relevante Änderung eines laufenden Vorgangs

FEED:  
passive Information, die interessant sein kann, aber keine unmittelbare Handlung verlangt.

Beispiele:

- Freund hat Album vervollständigt
- Freund hat neue Sticker eingetragen
- neues Album bei Sammlr verfügbar
- ausgewählte Sammlr-Neuigkeit

Feed darf niemals wichtige Handlungsaufforderungen ersetzen.

### 9. Laufende Trades auf Home

Home soll NICHT den vollständigen Bereich „Meine Trades“ duplizieren.

Stattdessen wird eine kompakte Zusammenfassung laufender Vorgänge angezeigt.

Beispiel:

„51 Sticker sind auf dem Weg zu dir.“

„26 Sticker musst du noch versenden.“

„3 laufende Trades.“

Die exakten Zahlen und die Darstellung werden später gestaltet.

Durch Antippen gelangt der Nutzer in den vollständigen Tradebereich.

### 10. Vollständige Tradeverwaltung

Die vollständige Verwaltung laufender Trades befindet sich weiterhin unter:

Tauschen  
→ Meine Trades

Dort können unter anderem sichtbar sein:

- offene Trades
- zu versendende Sticker
- versendete Sticker
- unterwegs befindliche Sticker
- empfangene Sticker
- Fristen
- Chat
- weitere Dealinformationen

Home zeigt davon nur eine relevante Zusammenfassung und dringende Handlungen.

### 11. Keine Smart-Match-Duplikation auf Home

Neue Smart Matches und die vollständige Smart-Trade-Entdeckung gehören grundsätzlich in den Bereich „Tauschen“.

Home soll nicht zu einer zweiten Smart-Trade-Seite werden.

Falls ein Smart-Trade-Ereignis später als besonders relevant eingestuft wird, kann Home darauf hinweisen.

Die eigentliche Suche, Sortierung und Auswahl von Smart Matches findet jedoch im Tauschbereich statt.

### 12. Keine dauerhafte Albumverwaltung auf Home

Albumfortschritt, Lieblingsalbum und aktive Alben werden nicht dauerhaft auf Home dupliziert.

Diese Inhalte gehören in die Sammlr-Zentrale.

Ein Album darf auf Home nur ereignisbasiert auftauchen.

Beispiel:

„Ralli hat WM26 vervollständigt.“

Nicht als permanentes Dashboardelement:

„Dein WM26 steht bei 86 %.“

Die Sammlr-Zentrale bleibt der Ort für diesen Zustand.

### 13. Sticker unterwegs

Sticker, die sich aktuell auf dem Versandweg befinden, sind eine besonders relevante Information.

Home darf deshalb eine kompakte Information zeigen wie:

„51 Sticker unterwegs“

bzw.

„51 Sticker kommen zu dir.“

Diese Information führt bei Interaktion in den entsprechenden Bereich unter „Meine Trades“.

Die vollständige Sendungsverwaltung bleibt dort.

### 14. Freundesbereich

Home soll einen eigenen Bereich für Aktivitäten von Freunden besitzen.

Dieser Bereich ist inhaltlich vom allgemeinen Sammlr-News-Bereich getrennt.

Beispiele:

„Knom84 hat 16 neue Sticker hinzugefügt.“

„Ralli hat WM26 vervollständigt.“

„Ali hat 8 Sticker getauscht.“

Wenn der betrachtende Nutzer mit beiden an einem Ereignis beteiligten Personen befreundet ist, kann eine Meldung konkreter sein.

Beispiel:

„Justin und Samira haben miteinander getauscht.“

Detaillierte Tradeinformationen zwischen völlig fremden Nutzern sollen nicht veröffentlicht werden.

### 15. Leerzustand des Freundesbereichs

Ein Nutzer ohne Freunde soll nicht mit einem leeren oder traurig wirkenden Feed konfrontiert werden.

Stattdessen verwandelt sich der Bereich in ein sinnvolles Onboarding-Element.

Beispiel sinngemäß:

„Dein Sammlr-Kreis“

„Füge Sammler hinzu und sieh, was sich in ihren Alben tut.“

Aktion:

„Sammler finden“

Sobald Freundschaften bestehen und Aktivitäten vorhanden sind, kann derselbe Bereich zum Freundesfeed werden.

Die genaue Formulierung wird später gestaltet.

### 16. Sammlr News

Neben Freundesaktivitäten besitzt Home einen separaten Bereich für Sammlr-Neuigkeiten.

Beispiele:

- neues Album verfügbar
- historisches Album neu hinzugefügt
- relevante neue Sammlr-Funktion
- ausgewählter Community-Meilenstein
- wichtige Produktneuigkeit

Sammlr News sind keine beliebige globale Nutzer-Timeline.

### 17. Kein globaler Social-Media-Feed

Sammlr soll nicht jeden beliebigen Vorgang fremder Nutzer veröffentlichen.

Nicht sinnvoll:

„RandomKevin97 aus Wuppertal hat 14 Sticker getauscht.“

Globale Meldungen sollen einen echten Informations- oder Communitywert besitzen.

Sammlr soll kein klassisches Engagement-getriebenes Social Network werden.

### 18. Freundesnews und Sammlr News getrennt

Aktueller Produktentscheid:

Freundesaktivitäten und Sammlr News sollen eher in zwei getrennten Bereichen/Fenstern dargestellt werden als in einem einzigen vermischten Feed.

Dadurch bleibt klar:

Was passiert in meinem persönlichen Sammler-Netzwerk?

vs.

Was gibt es Neues bei Sammlr insgesamt?

Die genaue visuelle Umsetzung bleibt offen.

### 19. Kein künstlicher Content

Wenn es keine relevanten Sammlr News gibt, muss Sammlr nicht künstlich Meldungen erzeugen.

Wenn es bei Freunden keine neuen Aktivitäten gibt, muss ebenfalls kein belangloser Inhalt produziert werden.

Die App soll nicht versuchen, künstlich Nutzungszeit zu erzeugen.

Sammlr unterstützt reale Sammelaktivität.

Die App ist Werkzeug, Netzwerk und Infrastruktur, kein Selbstzweck.

### 20. „Alles erledigt“-Zustand

Wenn keine offenen Aufgaben oder dringenden Benachrichtigungen bestehen, darf Home dies klar und ruhig kommunizieren.

Beispiel sinngemäß:

„Alles erledigt.“

„Keine offenen Benachrichtigungen.“

Darunter können Freundesaktivitäten und Sammlr News weiterhin verfügbar sein.

Ein leerer Aufgabenbereich ist ein positiver Zustand und muss nicht künstlich gefüllt werden.

### 21. Direkte Aktionen auf Home

Bestimmte dringende Aktionen dürfen direkt von Home bzw. aus einer Home-Benachrichtigung erreichbar sein.

Dazu können gehören:

- Tradeanfrage öffnen / beantworten
- Trade bestätigen
- Versand markieren
- Freundesanfrage beantworten
- Empfang bestätigen
- notwendige Anpassung eines Deals bestätigen

Andere Funktionen gehören bewusst in ihre Fachbereiche.

### 22. Funktionen, die nicht primär auf Home gehören

Insbesondere folgende Dinge sollen nicht unnötig auf Home dupliziert werden:

- vollständige Stickerwall
- Bestandspflege
- Album hinzufügen
- vollständige Albumübersicht
- vollständige Smart-Match-Liste
- Smart-Trade-Suche
- vollständige Tradeverwaltung
- detaillierte Statistiken
- Trophäenschrank

Diese Bereiche besitzen eigene Orte innerhalb der App.

### 23. Home als Verteiler

Home darf den Nutzer gezielt in die zuständigen Bereiche führen.

Beispiele:

„51 Sticker unterwegs“  
→ Tauschen / Meine Trades

„Neue Freundesanfrage“  
→ Freundesanfrage

„Versandfrist endet“  
→ konkreter Trade

„Neues DEL2-Album verfügbar“  
→ Albuminformation / Album hinzufügen

Home informiert und verteilt.

Die Fachbereiche verwalten.

### 24. Priorität

Die grundsätzliche Priorität von Home lautet:

1. notwendige Handlung
2. relevante laufende Vorgänge
3. persönliches Netzwerk
4. allgemeine Sammlr-Neuigkeiten

Damit beantwortet Home sowohl:

„Was muss ich tun?“

als auch:

„Was ist passiert?“

### 25. Verhältnis zu Freunden

Freunde benötigen nach aktuellem Stand nicht zwingend einen eigenen permanenten Bottom-Navigation-Punkt.

Home kann einen wichtigen Zugang zum Freundesnetzwerk darstellen.

Weitere Zugänge können beispielsweise über Profil und Suche erfolgen.

Die endgültige Navigationsentscheidung wird ausdrücklich erst in der separaten Navigationsplanung getroffen.

### 26. Verhältnis zur Sammlr-Zentrale

Die bestehende Sammlr-Zentrale bleibt ein zentraler Hauptbereich.

Ihre aktuelle Grundidee:

- Lieblingsalbum
- aktive Alben
- Vitrine

wird ausdrücklich nicht durch Home ersetzt.

Home und Sammlr-Zentrale besitzen unterschiedliche Aufgaben und dürfen langfristig nebeneinander bestehen.

### 27. Produktphilosophie

Home soll keine Aufmerksamkeit um ihrer selbst willen erzeugen.

Home soll dem Nutzer schnell zeigen:

- Was braucht mich?
- Was ist mit meinen Trades?
- Was passiert bei meinen Sammlerfreunden?
- Was gibt es Relevantes bei Sammlr?

Danach soll der Nutzer problemlos wieder seine Sammlung pflegen, tauschen oder die App verlassen können.

Sammlr ersetzt nicht das Sammeln.

Sammlr unterstützt das Sammeln.

### 28. Offene Punkte

Bewusst noch nicht final entschieden:

- genaue Anzahl sichtbarer Home-Benachrichtigungen
- exakte Sortierung bei mehreren dringenden Aufgaben
- genaue Feed-Events für Freunde
- genaue Kategorien von Sammlr News
- exaktes Layout der beiden Newsbereiche
- genaue Badge-Logik
- Dauer der Benachrichtigungshistorie
- welche erledigten Meldungen archiviert werden
- genaue Leerzustände
- exakte Wortwahl
- endgültige Navigation
- mögliche spätere Personalisierung von Home

Diese Punkte gehören in spätere Detail-/UI-Spezifikationen und verhindern nicht die weitere Produktplanung.

### 29. Status

Der Bereich HOME / STARTSEITE gilt damit konzeptionell auf Produktebene als weitgehend definiert.

Detaildesign und technische Umsetzung erfolgen später in kontrollierten Arbeitspaketen.
