# Product Audit – sammlr. Home / Feed

**Stand:** 15. August 2026
**Status:** Product-Owner-Entscheidungen dokumentiert; keine UI-, Produktlogik-, Test- oder Datenmodelländerung
**Langfristige Bestandsspezifikation:** [Home / Startseite](../../Product%20Bible/specifications/home.md)
**Früheres Seiten-Audit:** [sammlr.-Zentrale / bisheriges Home](02-sammlr-zentrale.md)

## 1. Zweck und Verhältnis zum Bestand

Dieses Audit dokumentiert die neuere Produktrichtung für die mittlere Hauptnavigation **sammlr.**. Es überschreibt die bestehende Home-Spezifikation, das frühere Seiten-Audit und S23–S25/S29 nicht stillschweigend. Abweichungen werden ausdrücklich als Kollisionen festgehalten; aus dem Dokument folgt noch keine Implementierungsfreigabe.

## 2. Verbindliche Produktregel

> sammlr. ist die chronologische Erzählung der eigenen Sammlerwelt. Die Seite zeigt interessante, feedwürdige Ereignisse; konkrete Aufmerksamkeit gehört zur Glocke und operative Trade-Arbeit in die Tauschzentrale.

Die Hauptbereiche beantworten damit unterschiedliche Fragen:

| Bereich | Produktrolle |
|---|---|
| Sammlung | mein Bestand und meine Alben |
| sammlr. | meine Sammlerwelt |
| Tauschen | Trades, SmartTrades und Tauschmarkt |
| Glocke | Dinge, die meine Aufmerksamkeit benötigen |
| Profil | meine Sammleridentität |

sammlr. ist weder klassisches Dashboard noch Aufgabenliste. Die Seite soll einen interessanten Einstieg bieten, auch wenn gerade weder Bestandspflege noch eine Trade-Aktion ansteht.

## 3. Chronologischer Feed

Der MVP folgt einer strikten Chronologie: Neueste relevante Ereignisse stehen oben. Es gibt keine algorithmische Sortierung und keine fachlichen Prioritätsnummern.

Spätere Filter oder andere Sortierungen bleiben offen. Sie dürfen nicht vorzeitig aus dem Bestandssystem oder aus bisherigen Home-Prioritäten abgeleitet werden.

## 4. Drei Ereignisquellen

### A. Eigene Sammlerreise

Grundsätzlich feedwürdig sein können:

- ein neu begonnenes Album,
- relevante Fortschrittsmeilensteine wie 50, 75 oder 90 Prozent,
- ein abgeschlossenes Album,
- eine freigeschaltete Trophäe,
- Trade- und besondere Sammlermeilensteine,
- später eventuell besondere Sticker oder vergleichbare Ereignisse.

Nicht jede normale Bestandsänderung erzeugt einen Eintrag. Der Feed erzählt eine Geschichte und ist kein Änderungslog.

### B. Aktivitäten von Freunden

Freundesaktivitäten sind grundsätzlich gewünscht. Grundlage sind ausschließlich gegenseitige Freundschaften, keine Follower-Beziehungen.

Mögliche Ereignisse sind ein neu begonnenes oder abgeschlossenes Album, eine bedeutende Trophäe, ein Trade-Meilenstein oder ein anderer relevanter Sammlermeilenstein. Nicht jede Aktivität eines Freundes ist automatisch feedwürdig.

### C. Sammlr News

Sammlr kann eigene Ereignisse veröffentlichen, etwa ein neues verfügbares Album, eine relevante neue Funktion oder eine wichtige Sammlr-Neuigkeit. Später können ausgewählte Community-Ereignisse hinzukommen.

Sammlr News dürfen nicht zur künstlichen Nachrichtenflut oder zu einer beliebigen globalen Nutzer-Timeline werden.

## 5. Feed-Würdigkeit

Das genaue Regelwerk ist noch nicht beschlossen. Verbindlich ist nur die Leitlinie:

- nicht jede Aktion,
- nicht jede Stickeränderung,
- nicht jede kleine Aktivität eines Freundes,
- stattdessen Meilensteine, interessante Entwicklungen und sammlerisch relevante Ereignisse.

Das spätere Regelwerk muss auch bei vielen aktiven Freunden einen interessanten und verständlichen Feed erhalten.

## 6. Feed, Benachrichtigung und Tauschzentrale

| Konzept | Bedeutung |
|---|---|
| Benachrichtigung | Etwas verlangt Aufmerksamkeit oder informiert über einen konkreten Vorgang. |
| Feed | Etwas Interessantes ist in meiner Sammlerwelt passiert. |
| Tauschzentrale | Dort werden Trades operativ bearbeitet. |

Primär zur Glocke beziehungsweise Tauschzentrale gehören:

- neue Tauschanfragen,
- notwendige Versandaktionen,
- Empfangsbestätigungen,
- sonstige konkrete Trade-Aktionen,
- Bewertungsaufforderungen,
- laufende Trades und Sendungen.

Das Glocken-Badge bedeutet: **Hier benötigt etwas deine Aufmerksamkeit.** Dieselbe Information soll nicht gleichzeitig groß auf sammlr., in der Glocke und in der Tauschzentrale geführt werden.

S23 und S24 bleiben technische Besitzer typisierter Notifications, Historie, Read-State, Badge und sicherer Zielnavigation. Das Audit erweitert ihren Eventkatalog nicht. Insbesondere muss für eine spätere Bewertungsaufforderung separat geprüft werden, ob ein geeigneter Notification-Typ bereits existiert oder bewusst ergänzt werden soll.

## 7. Interaktion

Feed-Einträge dürfen auf ihr natürliches Ziel führen:

- Albumereignis → Album,
- Trophäe → Trophäe oder Profil,
- Freundesereignis → entsprechendes Profil oder Ereignis,
- Sammlr News → passende Detailseite,
- ein später freigegebener SmartMatch → Match oder Tauschzentrale.

Likes, Kommentare und Reaktionen sind nicht vorgesehen. Sammlr besitzt Community, wird aber kein allgemeines soziales Netzwerk.

## 8. SmartTrades als offene Ausnahme

Ein SmartMatch kann langfristig als echte Entdeckung feedwürdig sein, etwa wenn eine andere Person viele fehlende Sticker anbieten könnte. Das ist konzeptionell etwas anderes als eine Versand- oder Bestätigungsaufgabe.

Ob, wann und in welcher Form SmartMatches in den Feed gelangen, ist nicht final entschieden. Daraus folgt keine aktuelle Implementierung.

## 9. Privacy-Abhängigkeit

Freundesereignisse dürfen keine privaten Profile, Alben, Bestände oder Aktivitäten indirekt offenlegen. Der Feed muss deshalb das noch nicht konsolidierte Profil-/Album-Privacy-Modell beachten.

Offen sind insbesondere:

- welche Freigabe ein Ereignis zum Erzeugungs- und zum Anzeigezeitpunkt benötigt,
- ob ein später privatisiertes Album einen vorhandenen Feed-Eintrag ausblendet,
- wie das einfache Profilmodell öffentlich/privat mit S27 `public` / `friends` / `private` je Album zusammenwirkt,
- welche Detailtiefe ein Ereignis ohne Offenlegung konkreter Bestände besitzen darf.

Bis zur gesonderten Entscheidung wird keine Privacy-Vererbung erfunden.

## 10. Abgleich mit bestehender Home

| Bestehendes Element oder Vertrag | Bewertung im neuen Modell | Spätere Auswirkung |
|---|---|---|
| „Das braucht dich“ | kollidiert direkt | kann als großer Home-Bereich entfallen; Aufmerksamkeit gehört zur Glocke |
| S25-Prioritätskarten und Prioritätsnummern | kollidieren direkt mit Chronologie | müssen auf Home später abgelöst werden; eine Wiederverwendung außerhalb des Feeds ist nicht Gegenstand dieses Audits |
| laufende Trades und Sendungen auf Home | kollidieren als dauerhafter Bereich | gehören primär zur Glocke beziehungsweise Tauschzentrale |
| Freunde-Kachel „Freunde kommen später.“ | Quelle passt, heutiger Platzhalter erfüllt den Feed nicht | wird später durch privacy-geprüfte, feedwürdige Freundesereignisse ersetzt |
| Sammlr-News-Kachel | Quelle passt, heutiger Platzhalter erfüllt den Feed nicht | wird später Teil der Chronologie; kein künstlicher Inhalt |
| dauerhafte Links zu Sammlung und Tauschzentrale | natürliche Ziele passen grundsätzlich | kontextbezogene Eventlinks bleiben sinnvoll; Bedarf an zusätzlichen dauerhaften Abkürzungen bleibt UX-offen |
| S23 typisierte Notifications | grundsätzlich passend | konkrete Vorgänge bleiben Notification-Scope; Eventkatalog wird hier nicht verändert |
| S24 Historie, Glocken-Badge und sichere Ziele | deckungsgleich mit der neuen Aufmerksamkeitstrennung | bleibt zuständiger Einstieg für Aufmerksamkeit und konkrete Vorgänge |
| S29 gegenseitige Freundschaften | deckungsgleich | bildet die Beziehungsgrundlage, enthält aber noch keinen Freundesfeed |

## 11. Dokumentierte Vertragskollisionen

### Bestehende Home-Spezifikation

Die langfristige Home-Spezifikation priorisiert notwendige Handlungen, laufende Vorgänge, Freunde und Sammlr News in dieser Reihenfolge. Sie erlaubt kompakte laufende Trades auf Home und sieht direkte operative Aktionen vor. Das neue Audit verschiebt Handlungsbedarf und laufende Vorgänge primär zur Glocke beziehungsweise Tauschzentrale und macht Chronologie statt Priorität zum Home-Prinzip.

Die Bestandsspezifikation trennt Freundesaktivitäten und Sammlr News bevorzugt in separate Bereiche. Das neue Audit definiert einen chronologischen Feed mit drei Quellen. Die fachliche Herkunft bleibt unterscheidbar; genaue Karten, Gruppierung und optische Trennung bleiben jedoch UX-offen.

### Früheres Post-RC-Audit 02

Das frühere Audit erklärt Handlungsbedarf zum obersten Home-Bereich und lässt laufende Trades bei konkreter Aktion auf Home erscheinen. Diese Aussagen werden durch die neuere Feed-Entscheidung fachlich überholt, bleiben aber als früherer Auditstand erhalten.

### S25 – Operatives Home V1

S25 implementiert maximal fünf deterministisch priorisierte Aufgaben, maximal drei laufende Trades, „Das braucht dich“, „Alles erledigt.“ sowie getrennte Freunde-/News-Platzhalter. Diese Umsetzung ist der aktuelle technische Stand, kollidiert aber in ihrer Informationsarchitektur direkt mit dem neuen Zielbild.

### Begriffe Home und Sammlr-Zentrale

Die ältere Product Bible unterscheidet Home von einer Sammlung-orientierten „Sammlr-Zentrale“. Die aktuelle Navigation verwendet „sammlr.“ für den mittleren Home-Einstieg und „Sammlung“ für Bestand und Alben. Das Audit folgt der aktuellen Hauptbereichslogik `Sammlung / sammlr. / Tauschen`; die historische Benennung bleibt als dokumentierter Terminologiekonflikt bestehen.

## 12. Bewusst vertagte UX- und Produktfragen

Noch nicht festgelegt werden:

- Feedkarten, Kartenhöhe und Bilder beziehungsweise Stickerabbildungen,
- Gruppierung mehrerer Ereignisse,
- Zeitdarstellung und Tages-/Wochenüberschriften,
- Animationen und Empty State,
- Pagination oder Infinite Scroll,
- genaue SmartMatch-Integration,
- abschließendes Regelwerk feedwürdiger Freundes- und Eigenevents,
- Feed-Filter und spätere alternative Sortierungen,
- Typografie, Farben und endgültige Informationsdichte,
- die technische Erzeugung, Speicherung und Retention von Feed-Ereignissen,
- Redaktion und Veröffentlichungsweg für Sammlr News.

## 13. Aktueller technischer Stand und spätere Betroffenheit

Heute vorhanden sind die Home-Route `/`, das read-only `OperationalHomeService`-Modell, priorisierte Aufgaben, kompakte laufende Trades, sichere Deep Links, die Glocke mit Badge und Notification-Historie sowie statische Freunde-/News-Platzhalter.

Bei einer später gesondert freigegebenen Umsetzung wären insbesondere betroffen:

- Home-Route und Home-Rendering,
- `OperationalHomeService` und seine heutige Aufgaben-/Trade-Projektion,
- Home-spezifische Styles und S25-Vertragstests,
- Ereignisquellen aus Sammlung, Trophäen, Trades und Community,
- Privacy-Prüfung für Freundesereignisse,
- S23-/S24-Abgrenzung und gegebenenfalls ein bewusst erweiterter Notification-Vertrag,
- natürliche Deep Links zu Album, Profil, Trophäe, News und eventuell SmartMatch.

Dieses Audit verändert keine dieser Komponenten.
