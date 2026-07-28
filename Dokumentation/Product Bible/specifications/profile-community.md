# Bereich 03: Profil & Community

| Metadatum | Wert |
| --- | --- |
| Status | Working Product Specification |
| Bereich | Profil & Community |
| Stand | 2026-07-26 |
| Änderungshinweis | Änderungen nur bewusst nach neuer Produktentscheidung vornehmen. |

## Dokumentcharakter

Dieses Dokument ist ein langfristiges Produkt-/Lastenheft. Es ist ausdrücklich keine kurzfristige Codex-Todo-Liste und keine Aussage darüber, welche beschriebenen Funktionen bereits implementiert sind. Aus diesem Dokument folgt ohne gesonderte Priorisierung und Umsetzungsentscheidung kein unmittelbarer Implementierungsauftrag.

Das am Ende archivierte Produktprotokoll ist vollständig und inhaltlich übernommen. Die folgende Statusmatrix dient ausschließlich der eindeutigen Auslegung seiner Aussagen.

## BESCHLOSSEN / KERNLOGIK

Als langfristige Produktprinzipien und Kernarchitektur beschlossen sind insbesondere:

- Das Profil ist primär die persönliche Sammlerseite eines Nutzers, keine klassische Social-Media-Seite und keine reine Gamification-Seite.
- Die Sammlung steht im Mittelpunkt; Trophäen, Statistiken, Freunde und Community-Funktionen ergänzen sie, überlagern sie aber nicht.
- Die primäre öffentliche Identität ist der eindeutige Sammlr-Nutzername.
- Klarname, Profilbild und Standort können optional ergänzt werden; genaue Wohnadressen werden nicht öffentlich im Profil dargestellt.
- Bewertung und erfolgreiche Trades gehören relativ prominent in den oberen Profilbereich, damit Vertrauen vor einem Tausch schnell erfassbar ist.
- Die grobe Profilhierarchie lautet: Identität/Bewertung, kompakte Kennzahlen, aktive Alben, Vitrine abgeschlossener Alben, Trophäen, Statistiken, Freunde/Community.
- Trophäen sind wichtig, aber nicht das Hauptelement des Profils.
- Aktive Alben werden prominent dargestellt; Nutzer sollen Alben bewusst deaktivieren können, ohne sie zu löschen.
- Album-Sichtbarkeit soll kontrollierbar sein: öffentlich, nur Freunde, privat.
- Sichtbare fremde Alben dürfen je nach Privatsphäre vollständig betrachtet werden, inklusive Stickerwall und Bestandsinformationen.
- Fremde Profile müssen persönliches Tauschpotenzial sichtbar machen und direkt in sinnvolle Tauschfunktionen führen.
- Vollendete Alben wandern in eine Vitrine, bleiben aber für das Tauschsystem relevant.
- Freundschaften sind beidseitig, nicht bloße Follower-Beziehungen.
- Sammlr zeigt keine Profilbesucherlisten und keine Benachrichtigung über Profilbesuche.
- Blockieren wird benötigt und muss Interaktionen einschränken, ohne relevante Tradehistorie verschwinden zu lassen.
- Bewertungen stammen ausschließlich aus qualifizierten zustande gekommenen Trades.
- Feed und Benachrichtigungen sind unterschiedliche Produktbereiche.

Diese Festlegungen beschreiben die Zielarchitektur. Sie gelten nicht automatisch als bereits implementiert.

## NOCH ZU ENTSCHEIDEN

Bewusst offen sind insbesondere:

- die exakte visuelle Reihenfolge und Gestaltung des Profils,
- die endgültige Auswahl kompakter Profilkennzahlen,
- die technische Definition von "aktivem Album",
- ob Album-Sichtbarkeit und Teilnahme am Smart-Trade-Pool gekoppelt oder getrennte Einstellungen werden,
- die genaue Darstellung des Tauschpotenzials auf fremden Profilen,
- die genaue Datenschutz-, Sichtbarkeits- und Wording-Logik eines groben Aktivitätsstatus auf fremden Profilen,
- die konkrete Feed-Logik für Freundesaktivitäten und allgemeine Community-Meldungen,
- der Umfang eines allgemeinen Sammlr-Feeds neben Freundesaktivitäten,
- genaue Konsequenzen und technische Behandlung laufender Trades bei Blockierung,
- Detailgestaltung der in [`navigation-information-architecture.md`](navigation-information-architecture.md) festgelegten Wege zu Freunden und Community-Funktionen,
- sowie die spätere Ausarbeitung einer echten Sammlr-Startseite/Home als mögliche Community-Zentrale.

Offene Punkte dürfen nicht beiläufig durch eine Implementierung als endgültige Produktentscheidung festgeschrieben werden.

## SPÄTER / VISION

Ausdrücklich keine aktuelle Implementierungsanforderung sind insbesondere:

- detaillierte Bewertungsansichten,
- anonymisierte oder integrierte Versandlösungen,
- Freundesaktivitäten im Feed,
- allgemeine Sammlr-News und Community-Meilensteine im Home,
- tiefgehende Statistikbereiche und "Freakstatistiken",
- weitere Community-Funktionen rund um Freunde, Suche, Home und Navigation.

Diese Punkte bleiben Teil des langfristigen Zielbilds, dürfen aber nicht als bereits priorisierte oder freigegebene Umsetzung gelesen werden.

## Abgleich mit bestehender Dokumentation

Der zentrale Product-Bible-Index trennte bisher "Community" und "Profil" als noch zu definierende Bereiche. Diese Spezifikation führt beide Produktbereiche bewusst als Bereich 03 "Profil & Community" zusammen, weil das Profil als Sammlerseite, Vertrauensfläche und Einstieg in Community- sowie Tauschfunktionen definiert wird.

Die Spezifikation [`trading.md`](trading.md) bleibt maßgeblich für Smart-Trader-Mechanik und Tauschoptimierung. [`trade-lifecycle.md`](trade-lifecycle.md) definiert, wann ein abgewickelter Deal für Bewertung und Historie qualifiziert ist. Dieses Dokument definiert die Darstellung von Bewertung und Vertrauen im Profil, dupliziert die zugrunde liegende Logik aber nicht.

Die Spezifikation [`collection.md`](collection.md) bleibt maßgeblich für Albumtypen, Albumexemplare, Aktivierung, Vitrine und Bestandslogik. Dieses Dokument definiert deren Darstellung und Sichtbarkeit im Profil, nicht die interne Sammlungsverwaltung.

Ergänzend ist als geplanter, noch offener Profilpunkt ein grober Aktivitätsstatus dokumentiert. Er soll insbesondere vor Tauschanfragen erkennen lassen, ob ein potenzieller Tauschpartner Sammlr aktuell nutzt, ohne zwingend einen exakten öffentlichen Zeitstempel offenzulegen.

Die Spezifikation [`navigation-information-architecture.md`](navigation-information-architecture.md) legt fest: Das eigene Profil wird global über Avatar beziehungsweise Profilicon im Header geöffnet; Freunde, Statistik und Einstellungen liegen unter dem Profil. Persönliche Trophäen liegen im Profil, albumbezogene Trophäen im jeweiligen Album. Ein eigener Freunde- oder Profilpunkt in der Bottom-Navigation entfällt.

---

## Archiviertes Originalprotokoll

SAMMLR PRODUCT SPECIFICATION

BEREICH 03: PROFIL & COMMUNITY

Stand: 2026-07-26

Status: Working Product Specification

### 1. Grundidee des Profils

Das Sammlr-Profil ist keine klassische Social-Media-Profilseite und auch keine reine Gamification-Seite.

Es ist in erster Linie die persönliche Sammlerseite eines Nutzers.

Die Sammlung steht im Mittelpunkt.

Trophäen, Statistiken, Freunde und soziale Funktionen ergänzen die Sammlung, dürfen sie aber nicht überlagern.

Ein fremder Nutzer soll anhand eines Profils insbesondere verstehen können:

- Wer ist dieser Sammler?
- Welche Alben sammelt er?
- Welche Alben hat er bereits vervollständigt?
- Welche meiner fehlenden Sticker besitzt er?
- Welche realistischen Tauschmöglichkeiten bestehen zwischen uns?
- Wie erfahren und zuverlässig ist dieser Sammler?
- Welche Trophäen und Sammlerstatistiken besitzt er?
- Sind wir bereits Freunde bzw. möchte ich ihn hinzufügen?

### 2. Identität

Die primäre öffentliche Identität eines Nutzers ist sein eindeutiger Sammlr-Nutzername.

Beispiel:

`@atzenklaus`

Der Nutzername steht visuell stärker im Mittelpunkt als der Klarname.

Ein echter Name kann zusätzlich hinterlegt bzw. angezeigt werden.

Der Klarname ist nicht die primäre öffentliche Identität.

Beim späteren Versand kann ein Klarname ohnehin erforderlich werden. Langfristig sind integrierte bzw. anonymisierte Versandlösungen denkbar, gehören aber nicht zu dieser Spezifikation.

Ein Profilbild ist optional.

Nutzer sollen nicht gezwungen werden, ein echtes Foto von sich zu verwenden.

Ein frei wählbares Profilbild oder kein Profilbild sind zulässig.

Ein Standort, beispielsweise Osnabrück, kann freiwillig angegeben und öffentlich angezeigt werden.

Keine genaue Wohnadresse wird öffentlich im Profil dargestellt.

### 3. Bewertung und Vertrauen

Die Bewertung eines Sammlers gehört relativ prominent in den oberen Profilbereich.

Beispiel:

```text
@atzenklaus
Valentin
★ 4,9
36 erfolgreiche Trades
Osnabrück
```

Die genaue UI wird später definiert.

Wichtig ist:

Bewertung und Trade-Erfahrung sollen bereits vor einem möglichen Tausch schnell erfassbar sein.

Die Bewertungslogik selbst wird in der Spezifikation "Tauschen / Smart Trader" definiert.

Beim Antippen der Bewertung soll langfristig eine detailliertere Ansicht möglich sein.

Blockieren, Zuverlässigkeit und weitere Sicherheitsfunktionen werden ebenfalls berücksichtigt.

### 4. Profilhierarchie

Die grobe inhaltliche Hierarchie des Profils lautet:

1. Identität / Nutzername / Bewertung
2. wichtige kompakte Kennzahlen
3. aktive Alben
4. Vitrine abgeschlossener Alben
5. Trophäen
6. Statistiken
7. Freunde / weitere Community-Funktionen

Die exakte visuelle Reihenfolge kann im späteren UI-Design noch angepasst werden.

Entscheidend ist:

Trophäen sind nicht das Hauptelement des Profils.

Die Alben des Sammlers stehen im Mittelpunkt.

### 5. Kompakte Profilkennzahlen

Im oberen Bereich sollen einige wenige aussagekräftige Kennzahlen erscheinen.

Als aktuelle Kandidaten gelten insbesondere:

- Anzahl Alben
- Anzahl Doppelte
- erfolgreiche Trades

Die endgültige Auswahl und Darstellung wird im späteren Profildesign festgelegt.

Die obere Profilansicht darf nicht mit Statistiken überladen werden.

Für Statistik-Freaks existiert ein eigener detaillierter Statistikbereich.

### 6. Aktive Alben

Aktive Alben werden prominent im Profil dargestellt.

Grundsätzlich gilt ein Album zunächst als aktiv, wenn der Nutzer darin noch sammelt bzw. sowohl fehlende Sticker als auch relevantes Tauschmaterial besitzt.

Der Nutzer soll ein Album bewusst deaktivieren können.

Damit können beispielsweise alte, derzeit nicht aktiv bearbeitete Alben aus dem prominenten Bereich entfernt werden, ohne sie löschen zu müssen.

Die genaue Definition von "aktiv" wird bei der Umsetzung noch technisch präzisiert.

### 7. Album-Sichtbarkeit

Nutzer sollen die Sichtbarkeit eines Albums kontrollieren können.

Vorgesehene Sichtbarkeitsstufen:

- öffentlich
- nur Freunde
- privat

Diese Einstellung beeinflusst, ob andere Nutzer das Album auf dem Profil sehen und öffnen können.

Ein sichtbares Album darf auf Wunsch vollständig betrachtet werden.

Dazu können gehören:

- Fortschritt
- Stickerwall
- vorhandene Sticker
- fehlende Sticker
- Doppelte
- genaue Bestandsmengen
- albumbezogene Trophäen

Es besteht grundsätzlich kein Problem damit, dass ein anderer Sammler beispielsweise sehen kann, dass ein Sticker viermal vorhanden ist.

Wer dies nicht möchte, kann das Album auf "nur Freunde" oder "privat" stellen.

### 8. Offene Frage: Sichtbarkeit vs. Tauschpool

Noch nicht endgültig entschieden ist, ob Album-Sichtbarkeit und Teilnahme am Smart-Trade-Pool zwingend gekoppelt sein sollen.

Beispiel:

Ein Nutzer könnte sein WM06 möglicherweise nicht öffentlich auf seinem Profil zeigen wollen, seine WM06-Doppelten aber trotzdem für Smart Trades bereitstellen wollen.

Deshalb ist später zu prüfen, ob zwei getrennte Einstellungen sinnvoller sind:

A) Wer darf dieses Album sehen?

B) Darf Tauschmaterial dieses Albums vom Smart Trader verwendet werden?

Diese Frage bewusst offen lassen und nicht voreilig technisch koppeln.

### 9. Fremde Alben ansehen

Öffentliche bzw. entsprechend freigegebene Alben anderer Nutzer können geöffnet werden.

Dabei soll nicht nur der allgemeine Albumfortschritt sichtbar sein.

Ein fremder Nutzer darf, entsprechend der Privatsphäre-Einstellung, auch die Stickerwall und exakte Bestandsinformationen ansehen.

Dadurch wird das Profil zu einer echten Sammlerseite und nicht lediglich zu einer Liste von Albumnamen.

### 10. Tauschpotenzial auf fremden Profilen

Ein zentraler Bestandteil fremder Profile ist die direkte Verbindung zum Smart Trader.

Wenn Nutzer A das Profil von Nutzer B besucht, soll Sammlr berechnen können, welchen Nutzen die Sammlung von B für A besitzt.

Ganz oben kann beispielsweise sinngemäß stehen:

"Peter besitzt 888 Sticker, die dir in deinen Sammlungen fehlen."

Zusätzlich:

"Mit euren aktuellen Beständen könnt ihr 234 Sticker direkt miteinander tauschen."

Diese beiden Werte sind bewusst unterschiedlich.

Wert 1:
Wie viele meiner fehlenden Sticker besitzt dieser Nutzer grundsätzlich?

Wert 2:
Wie viele davon können aufgrund des gegenseitigen Bedarfs aktuell tatsächlich in einem Trade ausgetauscht werden?

### 11. Tauschpotenzial pro Album

Auch innerhalb der Albumübersicht eines fremden Profils soll der persönliche Nutzen sichtbar werden.

Beispiel:

```text
WM 2026
Peter besitzt 69 deiner fehlenden WM26-Sticker.
Davon könnt ihr aktuell 41 miteinander tauschen.

WM 2006
Peter besitzt 17 deiner fehlenden WM06-Sticker.
Davon könnt ihr aktuell 12 miteinander tauschen.
```

Die genaue Darstellung wird später gestaltet.

Die Information selbst ist ein Kernbestandteil des Profils.

### 12. Direkter Einstieg in einen Trade

Von einem fremden Profil aus muss ein direkter Einstieg in die Tauschfunktionen möglich sein.

Der Nutzer soll nicht erst das Profil verlassen, in "Tauschen" wechseln und denselben Nutzer erneut suchen müssen.

Profil und Smart Trader sind miteinander verbunden.

Ein Profilbesuch kann unmittelbar zu einem sinnvollen Trade führen.

### 13. Vitrine für vollendete Alben

Vollständig abgeschlossene Alben werden in einer eigenen Vitrine dargestellt.

Die Vitrine ist ein sichtbarer Bestandteil des Profils, aber kein separater Ersatz für die Sammlung.

Ein abgeschlossenes Album kann automatisch aus dem Bereich "aktive Alben" in die Vitrine wechseln.

Die Sichtbarkeit richtet sich weiterhin nach der jeweiligen Privatsphäre-Einstellung des Albums.

WICHTIG:

Ein abgeschlossenes Album bleibt weiterhin für das Tauschsystem relevant.

Doppelte aus einem vollständigen Album dürfen weiterhin im Tauschpool verwendet werden.

Beispiel:

Ein abgeschlossenes WM06-Album kann weiterhin Doppelte liefern, mit denen ein aktuelles Bundesliga-Album oder ein anderes historisches Album vervollständigt wird.

"Album vollendet" bedeutet niemals automatisch "Album aus dem Tauschnetzwerk entfernen".

### 14. Trophäen

Trophäen sind ein wichtiger emotionaler Bestandteil von Sammlr, aber nicht das primäre Element des Profils.

Es existiert ein eigener Trophäenbereich.

Andere Nutzer dürfen den Trophäenschrank sehen, sofern die entsprechenden Inhalte freigegeben sind.

Es soll zunächst keine manuelle Auswahl einzelner "Lieblingstrophäen" für das Profil geben.

Stattdessen werden die relevantesten bzw. hochwertigsten Trophäen durch Sammlr sinnvoll sortiert.

Grundidee:

alle Trophäen anzeigen oder Trophäenbereich entsprechend der Privatsphäre nicht anzeigen.

Kein manuelles Kuratieren einzelner Trophy-Slots erforderlich.

### 15. Statistiken

Das Profil zeigt zunächst nur wenige wichtige Statistikwerte.

Beim Öffnen des Statistikbereichs gelangt der Nutzer in eine deutlich ausführlichere Statistikansicht.

Dort dürfen langfristig auch sehr detaillierte Sammlerstatistiken angeboten werden.

Die genaue Auswahl dieser "Freakstatistiken" wird in einer späteren eigenen Planung definiert.

Grundprinzip:

Profil = kompakt und verständlich.

Statistikbereich = tief, detailliert und explorativ.

### 16. Freunde

Sammlr verwendet ein klassisches beidseitiges Freundschaftssystem.

Kein reines Follower-Modell.

Ablauf:

Nutzer A sendet Freundesanfrage.

Nutzer B bestätigt.

Danach besteht eine Freundschaft.

Eine Freundschaft soll funktionalen Nutzen besitzen und nicht lediglich eine Zahl im Profil sein.

### 17. Funktionen von Freundschaften

Langfristig können Freunde insbesondere folgende Vorteile erhalten:

- leichter gegenseitig auffindbar
- schneller Zugriff auf mögliche Trades
- Sichtbarkeit von Alben mit Einstellung "nur Freunde"
- Freundesaktivitäten im Feed
- mögliche Filterung oder Priorisierung bei Tauschmöglichkeiten
- schneller Zugriff auf das Profil
- weitere Community-Funktionen

Die genaue Ausgestaltung wird zusammen mit Home/Feed und Navigation weiter definiert.

### 18. Freundesaktivitäten

Freundesaktivitäten sollen langfristig in einem persönlichen Feed bzw. auf einer möglichen Sammlr-Startseite erscheinen können.

Beispiele:

"Knom84 hat 16 neue Sticker hinzugefügt."

"Ralli hat WM26 vervollständigt."

"Ali hat 8 Sticker getauscht."

Wenn der betrachtende Nutzer mit beiden beteiligten Personen befreundet ist, kann eine Meldung gegebenenfalls konkreter sein:

"Justin und Samira haben miteinander getauscht."

Detaillierte Tradeinformationen zwischen völlig fremden Personen sollen nicht öffentlich verbreitet werden.

Die genaue Feed-Logik wird ausdrücklich NICHT in dieser Spezifikation abgeschlossen.

Sie wird bei der Planung der Sammlr-Startseite / Home separat definiert.

### 19. Community-Feed vs. Freundesfeed

Noch offen ist, in welchem Umfang Home später neben Freundesaktivitäten auch einen allgemeinen Sammlr-Feed enthält.

Denkbare allgemeine Meldungen:

- neues Album bei Sammlr verfügbar
- neues historisches Album eingepflegt
- Community-Meilensteine
- relevante Sammlr-Neuigkeiten

Denkbare persönliche Meldungen:

- Freund hat neue Sticker eingetragen
- Freund hat Album vervollständigt
- neue Tauschmöglichkeiten mit einem Freund

Diese Frage wird im Bereich HOME / STARTSEITE weiter ausgearbeitet.

### 20. Profilbesuche

Sammlr zeigt NICHT an, wer ein Profil besucht hat.

Keine Profilbesucherlisten.

Keine Benachrichtigung:

"Peter hat dein Profil angesehen."

Sammlr soll daraus keine LinkedIn-artige Beobachtungsmechanik machen.

### 21. Blockieren

Eine Blockierfunktion wird benötigt.

Ein blockierter Nutzer soll insbesondere:

- keine neue Freundesanfrage senden können
- keine neuen Tradeanfragen senden können
- keinen neuen Chat starten können
- nicht normal mit dem blockierenden Nutzer interagieren können

Bereits existierende problematische oder laufende Trades dürfen jedoch nicht einfach aus der Dokumentation verschwinden.

Tradehistorie, Status und relevante Nachweise müssen erhalten bleiben.

Die exakte technische und rechtliche Behandlung laufender Trades bei einer Blockierung wird später präzisiert.

### 22. Bewertungen

Bewertungen werden öffentlich im Profil dargestellt.

Beispiel:

```text
★ 4,9
36 erfolgreiche Trades
```

Eine detaillierte Bewertungsansicht kann später über Antippen geöffnet werden.

Bewertungen stammen ausschließlich aus tatsächlich zustande gekommenen bzw. entsprechend qualifizierten Trades gemäß Trade-Spezifikation.

Keine Bewertung aufgrund einer bloßen abgelehnten oder ausgelaufenen Anfrage.

### 23. Startseite / Home als mögliche Community-Zentrale

Während der Profilplanung entstand die wichtige Produktidee, eine echte Sammlr-Startseite zu entwickeln.

Diese Startseite könnte langfristig mehrere Funktionen bündeln:

- persönliche relevante Informationen
- Freundesaktivitäten
- allgemeine Sammlr-Neuigkeiten
- neue Alben
- neue Smart-Trade-Möglichkeiten
- Benachrichtigungen
- offene Handlungsaufforderungen
- Community-/Sportticker-artiger Feed

Dadurch könnten Freunde und Community-Funktionen zentral erreichbar sein, ohne einen eigenen Hauptnavigationspunkt zu benötigen.

Diese Idee wird in der nächsten Product-Specification-Session separat ausgearbeitet.

NICHT jetzt implementieren.

### 24. Benachrichtigungen vs. Feed

Bereits jetzt als Grundidee festhalten:

Feed und Benachrichtigungen sind nicht dasselbe.

Feed:
passive, interessante Informationen.

Beispiele:

"Knom84 hat sein WM06 auf 91 % gebracht."

"Neues DEL2-Album verfügbar."

Benachrichtigungen:
Informationen, die konkrete Aufmerksamkeit bzw. Handlung des Nutzers erfordern.

Beispiele:

"Peter hat deinen Trade angenommen."

"Versandfrist endet morgen."

"Neue Freundesanfrage."

Die genaue Architektur wird bei HOME / NAVIGATION definiert.

### 25. Freunde und Navigation

Aktueller Arbeitsstand:

Ein eigener dauerhafter Bottom-Navigation-Punkt "Freunde" erscheint derzeit nicht zwingend notwendig.

Wahrscheinlicher:

Profil -> Freunde

sowie Zugriff über Home, Suche und relevante Community-Elemente.

Dies ist noch KEINE endgültige Navigationsentscheidung.

Die gesamte Navigation wird erst festgelegt, nachdem die Hauptbereiche von Sammlr vollständig definiert wurden.

### 26. Produktphilosophie

Das Profil soll keine Selbstdarstellungsplattform werden.

Sein Hauptzweck ist:

- Sammlung zeigen
- andere Sammler kennenlernen
- Vertrauen schaffen
- gemeinsame Interessen entdecken
- Tauschpotenzial erkennen
- reale Sammelaktivität unterstützen

### Ergänzung vom 2026-07-26: Aktivitätsstatus / zuletzt online

Auf fremden Profilen soll langfristig ein grober Aktivitätsstatus sichtbar sein können.

Beispielhafte Darstellung:

- heute aktiv
- diese Woche aktiv
- kürzlich aktiv
- länger nicht aktiv

Zweck:

Vor allem bei Tauschanfragen soll ein Nutzer erkennen können, ob ein potenzieller Tauschpartner Sammlr aktuell überhaupt noch aktiv nutzt.

Es soll nicht zwingend ein exakter Zeitstempel wie „zuletzt online um 14:37 Uhr“ öffentlich angezeigt werden.

Die genaue Datenschutz-, Sichtbarkeits- und Wording-Logik wird später definiert.
