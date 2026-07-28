# Bereich 05: Navigation & Information Architecture

| Metadatum | Wert |
| --- | --- |
| Status | Working Product Specification |
| Bereich | Navigation & Information Architecture |
| Stand | 2026-07-27 |
| Änderungshinweis | Änderungen nur bewusst nach neuer Produktentscheidung vornehmen. |

## Dokumentcharakter

Dieses Dokument ist ein langfristiges Produkt-/Lastenheft. Es ist ausdrücklich keine kurzfristige Codex-Todo-Liste, kein UI-Entwurf und keine Aussage darüber, welche beschriebene Navigation bereits implementiert ist.

Das am Ende archivierte Produktprotokoll ist vollständig und inhaltlich unverändert übernommen. Die folgende Statusmatrix dient ausschließlich der eindeutigen Auslegung seiner Aussagen und der transparenten Einordnung zu älteren Spezifikationen.

## BESCHLOSSEN / KERNLOGIK

Als langfristige Produktprinzipien und Informationsarchitektur beschlossen sind insbesondere:

- Die primäre Navigation besitzt genau drei Hauptbereiche: `[ Sammlung ] [ sammlr./Home ] [ Tauschen ]`.
- Home ist der mittlere, markengeprägte Startpunkt nach Login beziehungsweise regulärem Öffnen.
- Sammlung ist der fachliche Besitzer von Alben, Stickerverwaltung, Papierliste, albumbezogenen Trophäen, Lieblingsalbum und klassischem Börsenmodus.
- Tauschen ist der fachliche Besitzer von Smart Trades, Partnersuche, Tradezentrale, Dealabwicklung und Tradehistorie.
- Ein Feature besitzt genau einen fachlichen Hauptbereich, kann aber über mehrere kontextuelle Einstiege erreichbar sein.
- Mehrere Einstiege öffnen dasselbe fachliche Objekt und erzeugen keine doppelten Funktions- oder Datenmodelle.
- Home und Benachrichtigungen verwenden direkte Deep Links und bewahren nach Möglichkeit den sinnvollen Rückweg zum Ursprung.
- Die Bottom-Navigation enthält keine permanenten Punkte für Profil, Freunde, Favorit, Statistik, Trophäen, Einstellungen oder Benachrichtigungen.
- Profil und Benachrichtigungen sind global über Avatar beziehungsweise Glocke im Header erreichbar.
- Das Glocken-Badge zählt ungelesene Benachrichtigungen, nicht offene Aufgaben oder laufende Trades.
- Gelesene Benachrichtigung und erledigte Aufgabe sind getrennte Zustände.
- Freunde, Statistik und Einstellungen liegen unter dem eigenen Profil; persönliche Trophäen liegen im Profil, albumbezogene Trophäen im Album.
- Das Lieblingsalbum ist eine Eigenschaft der Sammlung und kein eigener Navigationsbereich.
- Der klassische papierbasierte Börsenmodus ist albumbezogen und fachlich nicht mit Smart Trades gleichzusetzen.
- Auf tiefen Arbeitsansichten darf die Bottom-Navigation zugunsten von Fokus und Platz ausgeblendet werden.
- Ein Hamburger-Menü ist aktuell nicht erforderlich, darf bei späteren großen Produktdomänen aber neu bewertet werden.

Diese Festlegungen beschreiben die Zielarchitektur. Sie gelten nicht automatisch als bereits implementiert.

## NOCH ZU ENTSCHEIDEN

Bewusst offen sind:

- genaue Gestaltung des mittleren `sammlr.`-Spots,
- endgültiges Album-/Buchsymbol und endgültige Tauschpfeile,
- Größe und Position von Avatar und Glocke,
- großer oder kompakter Header je Seitentyp,
- exakte Animationen beim Navigationswechsel,
- Verhalten der Bottom-Navigation beim Scrollen,
- exakte Desktop-Darstellung,
- genaue Home-Karten,
- zukünftige Navigation bei Shop, Marketplace oder Scanner,
- abschließende Bereinigung der widersprüchlichen Verwendung des Begriffs „Sammlr-Zentrale“.

Offene Designfragen blockieren die Informationsarchitektur nicht und dürfen nicht beiläufig durch Implementierung als endgültige Produktentscheidung festgeschrieben werden.

## SPÄTER / VISION

Ausdrücklich keine aktuelle Implementierungsanforderung sind insbesondere:

- eine globale objektübergreifende Suche,
- QR-basierter Börsenmodus,
- regionale Suche und weitere Community-Einstiege,
- mögliche neue Navigation für Shop, Marketplace, Scanner oder Events,
- eine spätere erneute Bewertung eines Hamburger-Menüs.

Diese Themen bleiben Teil des langfristigen Zielbilds, sind aber keine unmittelbar freigegebenen V1-Aufgaben.

## Abgleich mit bestehender Dokumentation

Die Spezifikation [`home.md`](home.md) bleibt für Inhalt und Funktionslogik von Home maßgeblich. Dieses Dokument entscheidet ergänzend, dass Home der mittlere Startpunkt und Aufmerksamkeitsverteiler ist.

Die Spezifikation [`collection.md`](collection.md) bleibt für Sammlr-Zentrale, Alben, Stickerverwaltung, Papierliste, Lieblingsalbum und klassischen Börsenmodus maßgeblich. Die Navigation ordnet diese Funktionen dem linken Hauptbereich „Sammlung“ zu.

Die Spezifikation [`trading.md`](trading.md) bleibt für Smart-Trade-Mechanik und Dealfindung maßgeblich; [`trade-lifecycle.md`](trade-lifecycle.md) für Tradezentrale und Dealabwicklung. Die Navigation ordnet beide unter dem rechten Hauptbereich „Tauschen“ ein.

Die Spezifikation [`profile-community.md`](profile-community.md) bleibt für Profil, Freunde, Trophäen, Statistiken und Privatsphäre maßgeblich. Dieses Dokument entscheidet die globalen beziehungsweise hierarchischen Zugänge über Avatar, Profil und Album.

Die älteren Home- und Profilprotokolle ließen die endgültige Navigation und einen möglichen Freunde-Hauptpunkt ausdrücklich offen. Diese Fragen werden durch das vorliegende Dokument fortgeschrieben: Freunde erhalten keinen permanenten Bottom-Navigationspunkt. Eine ältere Product-Bible-Spezifikation mit einer verbindlichen fünfteiligen Bottom-Navigation, einem permanenten Favoriten-, Profil- oder Statistikpunkt wurde nicht gefunden.

Die Corporate-ID nennt „Sticker | Tauschen | Trophäen“ als Beispiel für ein Switch-System, nicht ausdrücklich als globale Hauptnavigation. Dieser historische Designhinweis wird daher nicht überschrieben und steht nicht im direkten Widerspruch zur neuen Informationsarchitektur.

### Offener Begriffskonflikt: Home vs. Sammlr-Zentrale

Abschnitt 3 des archivierten Originalprotokolls setzt in einer Formulierung „Home / Sammlr-Zentrale / zentrale Startseite“ gleich. Das widerspricht den Spezifikationen `home.md` und `collection.md`, die Home und Sammlr-Zentrale ausdrücklich als unterschiedliche Bereiche definieren. Auch die übrige Navigationsspezifikation ordnet die Inhalte der Sammlr-Zentrale dem linken Hauptbereich „Sammlung“ zu.

Eindeutig beschlossen und für die Navigation maßgeblich ist: Der mittlere `sammlr.`-Punkt führt zu Home; der linke Hauptbereich führt zur Sammlung. Ob der Name „Sammlr-Zentrale“ künftig aufgegeben oder neu verwendet werden soll, bleibt bis zu einer bewussten Produktentscheidung offen. Das Originalprotokoll wird nicht stillschweigend umformuliert.

---

## Archiviertes Originalprotokoll – vollständig und unverändert

SAMMLR PRODUCT SPECIFICATION
BEREICH: NAVIGATION & INFORMATION ARCHITECTURE
Stand: 2026-07-27
Status: Working Product Specification
============================================================


1. ZIEL DER NAVIGATIONSARCHITEKTUR

Sammlr soll trotz wachsendem Funktionsumfang eine sehr einfache Hauptnavigation besitzen.

Die Anwendung besitzt langfristig zahlreiche Funktionen:

- Home
- Benachrichtigungen
- Alben
- Stickerverwaltung
- Stickerlisten
- Börsenmodus
- Smart Trades
- Tradezentrale
- Freunde
- fremde Profile
- eigenes Profil
- Trophäen
- Statistiken
- Einstellungen
- später weitere Bereiche

Diese Funktionen sollen NICHT alle gleichberechtigt in einer großen Navigation nebeneinanderstehen.

Stattdessen werden sie logisch hierarchisiert.

Grundsatz:

Komplexität darf innerhalb der Produktarchitektur wachsen.

Die Hauptnavigation soll einfach bleiben.


2. DREI HAUPTBEREICHE

Die primäre Navigation besteht aus genau drei Bereichen:

SAMMLUNG | HOME | TAUSCHEN

Home sitzt in der Mitte.

Die bevorzugte visuelle Grundstruktur lautet:

[ Album/Sammlung ]   [ sammlr. ]   [ Tauschen ]

Der mittlere Home-Punkt repräsentiert gleichzeitig die Marke sammlr.


3. HOME ALS MITTELPUNKT

Der mittlere Navigationspunkt ist die Startseite der Anwendung.

Er soll visuell mit der Marke „sammlr.“ verbunden sein.

Damit bedeutet „sammlr.“ in der Hauptnavigation zukünftig:

Home / Sammlr-Zentrale / zentrale Startseite

und NICHT mehr ausschließlich:

meine Sammlung.


4. SAMMLUNG ALS LINKER HAUPTBEREICH

Links befindet sich die Sammlung.

Bevorzugte Symbolsprache:

Album / Buch.

Dieser Bereich enthält insbesondere:

- aktive Alben
- Lieblingsalbum
- Albumfortschritt
- Vitrine abgeschlossener Alben
- Album hinzufügen
- Zugriff auf einzelne Alben
- Stickerverwaltung
- Stickerwall
- Stickerliste
- albumbezogene Trophäen
- klassischer Börsenmodus


5. TAUSCHEN ALS RECHTER HAUPTBEREICH

Rechts befindet sich Tauschen.

Bevorzugte Symbolsprache:

gegenläufige Tauschpfeile.

Dieser Bereich enthält insbesondere:

- globale Tradezentrale
- Smart Trades
- albumübergreifende Trades
- Tauschpartnersuche
- einzelne Stickersuche im Tradingkontext
- Tradeanfragen
- offene Trades
- Meine Deals
- Versand-/Empfangsabwicklung
- Tradehistorie


6. SYMMETRIE

Die drei Hauptbereiche sollen visuell eine klare, ruhige Struktur bilden.

Links:
Sammlung

Mitte:
sammlr. / Home

Rechts:
Tauschen

Die mittlere Position darf visuell leicht hervorgehoben werden.

Das genaue Design wird später festgelegt.


7. STARTSEITE

Nach Login bzw. regulärem Öffnen der Anwendung landet der Nutzer auf:

HOME.

Nicht automatisch auf:

- Lieblingsalbum
- Sammlung
- Tradezentrale
- zuletzt geöffnetem Album

Home ist der definierte Ausgangspunkt.


8. ROLLE VON HOME

Home beantwortet primär:

„Was passiert gerade und was braucht meine Aufmerksamkeit?“

Home ist:

- Startseite
- Aufmerksamkeitszentrale
- Informationsverteiler
- Einstieg in aktuelle Vorgänge

Home ist NICHT der fachliche Besitzer aller dort dargestellten Funktionen.


9. HOME ALS VERTEILER

Home darf Informationen und Handlungsaufforderungen aus anderen Bereichen anzeigen.

Beispiele:

„Rolf möchte 17 Sticker tauschen.“

„Noch 2 Tage zum Versenden.“

„17 Sticker sind unterwegs.“

„Empfang bestätigen.“

„Peter möchte dein Freund sein.“

Bei Interaktion wird der Nutzer zum fachlich zuständigen Bereich weitergeleitet.


10. EIN FEATURE HAT EINEN FACHLICHEN BESITZER

Zentrale Architekturregel:

Ein Feature besitzt genau einen fachlichen Hauptbereich.

Es darf jedoch von mehreren Stellen aus erreichbar sein.

Beispiele:

Home zeigt:
„Versand bestätigen“

Die eigentliche Funktion gehört:
Tauschen → Meine Deals → konkreter Deal.

Home zeigt:
„Freundschaftsanfrage“

Die eigentliche Funktion gehört:
Profil/Freunde → konkrete Anfrage.

Profil zeigt:
„WM26 – 86 %“

Das Album gehört:
Sammlung → WM26.

Feed zeigt:
„Peter hat Trophy X erhalten“

Die Trophy gehört:
Peters Profil / Trophybereich.


11. KEINE DOPPELTE FUNKTIONSIMPLEMENTIERUNG

Mehrere Einstiege dürfen nicht zu mehreren fachlich getrennten Versionen derselben Funktion führen.

Beispiel:

Ein Trade kann über Home geöffnet werden.

Derselbe Trade kann über Tauschen → Meine Deals geöffnet werden.

Beide Wege öffnen denselben Deal.

Es werden nicht zwei unterschiedliche Dealansichten oder Dealmodelle gebaut.


12. DEEP-LINK-PRINZIP

Benachrichtigungen und Home-Elemente sollen möglichst direkt zum konkreten Objekt führen.

Nicht nur:

„Sticker unterwegs“
→ Tauschen

sondern:

„Sticker unterwegs“
→ Tauschen
→ Meine Deals
→ konkreter Deal

Nicht nur:

„Freundschaftsanfrage“
→ Profil

sondern:

→ Freunde
→ konkrete Freundschaftsanfrage

Grundsatz:

So wenig unnötige Zwischenschritte wie möglich.


13. NAVIGATIONSKONTEXT BEIBEHALTEN

Die Anwendung soll nach Möglichkeit wissen, von wo ein Nutzer eine Unterseite geöffnet hat.

Beispiel A:

Home
→ Notification
→ Deal mit Ralli

Zurück:
→ Home

Beispiel B:

Tauschen
→ Meine Deals
→ Deal mit Ralli

Zurück:
→ Meine Deals

Dieselbe Zielseite kann damit unterschiedliche sinnvolle Rückwege besitzen.


14. BOTTOM-NAVIGATION

Die Bottom-Navigation enthält ausschließlich die drei Hauptbereiche.

Keine zusätzlichen permanenten Punkte für:

- Profil
- Freunde
- Favorit
- Statistik
- Trophäen
- Einstellungen
- Benachrichtigungen


15. BOTTOM-NAVIGATION UND UNTERSEITEN

Auf den drei Hauptbereichen ist die Bottom-Navigation grundsätzlich sichtbar.

Auf tieferen Arbeitsansichten darf sie ausgeblendet werden, wenn dies Fokus oder verfügbaren Platz verbessert.

Beispiele:

- Dealchat
- später Scanner
- spezielle Vollbild-Workflows

Die Bottom-Navigation muss nicht dogmatisch auf jeder einzelnen Seite sichtbar bleiben.


16. KEINE BOTTOM-NAV-BADGES

Die Bottom-Navigation soll zunächst bewusst ruhig bleiben.

Keine mehrfachen roten Benachrichtigungspunkte auf:

- Home
- Sammlung
- Tauschen

Benachrichtigungen werden zentral über die Glocke kommuniziert.

Home kann zusätzlich relevante Aufgaben darstellen.


17. GLOBALER HEADER

Die drei Hauptbereiche sollen grundsätzlich einen gemeinsamen Sammlr-Header besitzen.

Bevorzugte Grundstruktur:

sammlr. / Markenbereich

plus:

Benachrichtigungsglocke

plus:

Profilbild / Profilicon

Die genaue visuelle Gestaltung wird später separat definiert.


18. HEADER AUF UNTERSEITEN

Auf tieferen Unterseiten darf der große Hauptheader in eine kompaktere Variante wechseln.

Dabei sollen Navigation, Zurück-Funktion und Kontext wichtiger sein als die dauerhafte Darstellung eines sehr großen Markenheaders.

Die exakte Header-Hierarchie wird beim Designsystem festgelegt.


19. BENACHRICHTIGUNGSGLOCKE

Die Glocke ist global erreichbar.

Der Nutzer soll Benachrichtigungen nicht nur von Home aus öffnen können.

Sie kann insbesondere im globalen Sammlr-Header liegen.


20. BADGE DER GLOCKE

Das Badge an der Glocke repräsentiert:

UNGelesene Benachrichtigungen.

Es repräsentiert NICHT direkt:

- Anzahl offener Trades
- Anzahl laufender Versandvorgänge
- Anzahl unerledigter Aufgaben

Beispiel:

„3“ bedeutet drei ungelesene Benachrichtigungen.


21. BENACHRICHTIGUNGEN VS. AUFGABEN

Benachrichtigungen und operative Aufgaben sind fachlich zu unterscheiden.

Eine Benachrichtigung kann gelesen sein.

Die zugrunde liegende Aufgabe kann trotzdem weiterhin offen sein.

Beispiel:

Nutzer liest:

„Noch 2 Tage zum Versenden.“

Damit verschwindet die Benachrichtigung gegebenenfalls aus „ungelesen“.

Der Deal bleibt selbstverständlich weiterhin offen, bis versendet wurde.


22. BENACHRICHTIGUNGSHISTORIE

Über die Glocke kann eine vollständige bzw. weiter zurückreichende Benachrichtigungsansicht geöffnet werden.

Dort können gegebenenfalls auch ältere oder abgelaufene Meldungen nachvollzogen werden.

Die genaue Aufbewahrungslogik wird in der Home-/Notification-Spezifikation gepflegt.


23. HOME MUSS NICHT AUS BENACHRICHTIGUNGEN BESTEHEN

Da die Glocke die vollständige Benachrichtigungsfunktion übernimmt, muss Home nicht jede Meldung als große Karte darstellen.

Home soll nur relevante aktuelle Informationen und Handlungsbedarf sinnvoll hervorheben.

Die genaue Home-Gestaltung wird separat behandelt.


24. PROFIL NICHT IN DER BOTTOM-NAVIGATION

Das eigene Profil erhält keinen permanenten Bottom-Navigation-Punkt mehr.

Stattdessen ist es über Profilbild bzw. Profilicon im globalen Header erreichbar.


25. PROFILAUFRUF

Klick auf Profilbild / Profilicon öffnet direkt das eigene Profil.

Kein zusätzliches Zwischenmenü ist zunächst notwendig.


26. PROFIL ALS PERSÖNLICHER HUB

Im eigenen Profil liegen unter anderem:

- öffentliche Profilansicht
- Klarname entsprechend den definierten Regeln
- Bewertung
- aktive Alben
- Vitrine
- Freunde
- Trophäen
- Statistik
- Einstellungen
- Sichtbarkeits-/Privatsphäreoptionen

Die genaue Profilarchitektur ist in der Profil-/Community-Spezifikation definiert.


27. FREUNDE NICHT IN DER BOTTOM-NAVIGATION

Freunde erhalten zunächst keinen eigenen permanenten Hauptnavigationspunkt.

Grund:

Freunde sind wichtig für Community und Vertrauen, aber voraussichtlich kein so häufiger Kernworkflow wie:

- Sammlung
- Home
- Tauschen


28. FREUNDE-BEREICH

Der Freunde-Bereich ist über das eigene Profil erreichbar.

Er enthält insbesondere:

- Freundesliste
- Freundschaftsanfragen
- Sammlr suchen

Später können weitere Community-Funktionen ergänzt werden.


29. FREUNDSCHAFTSANFRAGEN

Neue Freundschaftsanfragen erzeugen eine Benachrichtigung.

Diese kann über Home bzw. Glocke geöffnet werden.

Die Anfrage selbst bleibt im Freunde-Bereich bestehen, bis sie angenommen, abgelehnt oder anderweitig beendet wurde.

Das Lesen der Notification beantwortet die Anfrage nicht.


30. FREMDES PROFIL

Fremde Profile sind kein eigener Hauptnavigationsbereich.

Sie werden kontextuell geöffnet.

Mögliche Einstiege:

- Freunde
- Sammlr-Suche
- Smart Match
- Deal
- Feed
- später regionale Suche

Zurück führt sinnvoll zum jeweiligen Ursprung.


31. SAMMLR-SUCHE

Die öffentliche Suche nach anderen Sammlr-Nutzern liegt zunächst primär unter:

Profil
→ Freunde
→ Sammlr finden

Eine spätere globale Suche kann diesen Einstieg ergänzen.


32. GLOBALE SUCHE – ZUKUNFT

Langfristig denkbar:

eine globale Sammlr-Suche, die unterschiedliche Objekttypen versteht.

Beispiele:

ARG17
→ Sticker

knom84
→ Nutzer

WM 2006
→ Album

Diese Funktion ist kein unmittelbarer V1-Zwang und wird später separat spezifiziert.


33. STATISTIK NICHT IN DER BOTTOM-NAVIGATION

Der bisherige Statistik-Punkt wird aus der Hauptnavigation entfernt.

Statistiken gehören zum Profil.

Bevorzugter Weg:

Profil
→ Statistik-Vorschau
→ detaillierter Statistikbereich

Der detaillierte Statistikbereich darf bewusst umfangreich sein.


34. FREMDE STATISTIKEN

Auf fremden Profilen werden Statistiken nur entsprechend der definierten Privatsphäre-/Sichtbarkeitsregeln angezeigt.


35. TROPHÄEN NICHT IN DER HAUPTNAVIGATION

Trophäen erhalten keinen eigenen Hauptnavigationspunkt.

Globale/persönliche Trophäen:

Profil
→ Trophäenschrank

Albumbezogene Trophäen:

Sammlung
→ Album
→ Album-Trophäen


36. FAVORIT AUS DER BOTTOM-NAVIGATION ENTFERNEN

Der bisherige Favorit-Navigationspunkt entfällt.

Das Lieblingsalbum bleibt weiterhin ein wichtiges Konzept.

Es wird prominent innerhalb der Sammlung dargestellt.

Favorit ist damit eine Eigenschaft der Sammlung, kein eigener Produktbereich.


37. EINSTELLUNGEN

Einstellungen werden über das eigene Profil erreicht.

Kein eigener Hauptnavigationspunkt.


38. ALBUM HINZUFÜGEN

„Album hinzufügen“ gehört primär in den Bereich Sammlung.

Home benötigt im normalen Zustand keinen permanenten Album-hinzufügen-Button.

Bei komplett neuen Nutzern darf später ein sinnvoller Onboarding-Einstieg existieren.


39. SAMMLUNG – GRUNDHIERARCHIE

Bevorzugte fachliche Struktur:

Sammlung
→ Lieblingsalbum / aktive Alben / Vitrine
→ konkretes Album
→ Stickerwall
→ Stickerliste
→ Album-Trophäen
→ albumbezogene Tauschfunktionen
→ klassischer Börsenmodus

Die genaue Albumstruktur wird in der Sammlungsspezifikation gepflegt.


40. KLASSISCHER BÖRSENMODUS

Der bestehende papierbasierte Börsenmodus bleibt bewusst albumbezogen.

Beispiel:

Sammlung
→ WM26
→ Stickerliste / Börsenmodus

Dieser Modus basiert auf der schnellen papierähnlichen Stickerliste.

Auf einer realen Börse kann der Nutzer fehlende bzw. doppelte Sticker unmittelbar von der Liste streichen.

Dieser Workflow ist bewusst nicht identisch mit Smart Trades.


41. PAPIERBÖRSE VS. SMART TRADE

Klassischer Börsenmodus:

Mensch entscheidet den Deal.
Sammlr stellt schnelle Liste und Bestandsverwaltung bereit.

Smart Trade:

Sammlr berechnet sinnvolle Tauschmöglichkeiten anhand gepflegter Bestände.

Beide Systeme sollen nebeneinander existieren.


42. QR-BÖRSENMODUS – ZUKUNFT

Später kann ein QR-basierter Börsenmodus hinzukommen.

Dabei können zwei Sammlr-Nutzer ihre mitgebrachten Alben auswählen.

Sammlr berechnet anschließend direkt mögliche Tausche.

Dieser spätere Workflow kann technisch stärker auf Smart-Trade-Logik zurückgreifen.

Er ist nicht mit der heutigen papierbasierten Stickerliste gleichzusetzen.


43. TAUSCHEN – GRUNDHIERARCHIE

Die globale Tradezentrale soll fachlich insbesondere Zugriff bieten auf:

- dringende / offene Trades
- Meine Deals
- Smart Trades
- albumbezogene Trading-Einstiege
- albumübergreifende Smart Trades
- Tauschpartnersuche
- Stickersuche im Tradingkontext
- Tradehistorie

Die genaue UI-Reihenfolge wird beim konkreten Design festgelegt.


44. DRINGENDE DEALS

Laufende Deals mit Handlungsbedarf dürfen in der Tradezentrale besonders sichtbar sein.

Beispiele:

- Versand vorbereiten
- Versandfrist läuft ab
- Empfang bestätigen
- Problem mit Sendung

Home darf auf diese Vorgänge hinweisen.

Die eigentliche Verwaltung bleibt in Tauschen.


45. ALBUMBEZOGENE DEALS

Albumbezogene Deals können weiterhin aus einem konkreten Album heraus entstehen.

Beispiel:

Sammlung
→ WM26
→ albumbezogene Tauschfunktion
→ Deal entsteht

Nach Entstehung wird der Deal zentral in:

Tauschen
→ Meine Deals

verwaltet.


46. MEHRERE EINSTIEGE IN ALBUMBEZOGENES TRADING

Albumbezogenes Trading kann grundsätzlich sowohl aus dem Albumkontext als auch aus der globalen Tradezentrale erreichbar sein.

Diese Einstiege müssen nicht zwingend dieselbe Oberfläche besitzen, wenn der Nutzungskontext unterschiedlich ist.

Sie müssen jedoch dieselben fachlichen Daten und dieselbe Tradinglogik verwenden.


47. BÖRSENMODUS IST EINE AUSNAHME

Der klassische papierbasierte Börsenmodus ist bewusst ein eigener Workflow.

Er darf sich von Smart-Trade- und Deal-Workflows unterscheiden.

Grund:

Er soll auf einer realen Stickerbörse möglichst schnell und papierähnlich funktionieren.


48. HOME-PROTOKOLL BLEIBT MASSGEBLICH

Diese Navigationsspezifikation definiert nicht erneut das vollständige Home-Layout.

Sie ergänzt die bestehende Home-Spezifikation um die Rolle von Home innerhalb der Gesamtarchitektur.

Home ist:

- Startpunkt
- Aufmerksamkeitszentrale
- Verteiler
- Feed-/Informationsfläche

Die konkrete Gestaltung wird anhand der bestehenden Home-Spezifikation weiterentwickelt.


49. KEIN HAMBURGER-MENÜ ZUM START

Sammlr benötigt aktuell kein zusätzliches Hamburger-Menü.

Die Kombination aus:

- drei Hauptbereichen
- Profilzugang
- Glocke
- hierarchischen Unterbereichen

reicht für die derzeit geplante Produktstruktur aus.


50. HAMBURGER-MENÜ NICHT FÜR IMMER VERBOTEN

Diese Entscheidung ist nicht dogmatisch dauerhaft.

Wenn Sammlr später weitere große Produktbereiche erhält, kann die Navigationsarchitektur erneut bewertet werden.

Mögliche spätere Bereiche:

- Shop
- Marketplace
- Scanner
- Events
- weitere große Community-Funktionen

Neue Funktionen rechtfertigen jedoch nicht automatisch einen neuen Hauptnavigationspunkt.


51. NAVIGATION SOLL MITWACHSEN

Neue Funktionen werden zunächst dort eingeordnet, wo sie fachlich hingehören.

Erst wenn ein neuer Bereich eine eigene große Produktdomäne bildet, wird geprüft, ob die Hauptnavigation erweitert werden muss.


52. ICON-SPRACHE

Aktuelle bevorzugte semantische Richtung:

Sammlung:
Album / Buch

Home:
sammlr.-Markensymbol bzw. bestehendes zentrales Sammlr-Symbol

Tauschen:
gegenläufige Pfeile

Profil:
einzelne Person / Avatar

Freunde:
mehrere Personen

Benachrichtigungen:
Glocke

Die endgültigen Icons werden im Designsystem festgelegt.


53. HOME-ICON IST BEWUSST KEIN KLASSISCHES HAUS

Obwohl Home funktional die Startseite ist, soll der mittlere Navigationspunkt bevorzugt die Marke sammlr. repräsentieren.

Dadurch entsteht:

Album | sammlr. | Tauschen

statt:

Home | sammlr. | Tauschen

Dies stärkt Symmetrie und Markenidentität.


54. SAMMLR.-MITTELSPOT

Der Mittelspot darf gegenüber den beiden äußeren Punkten visuell hervorgehoben werden.

Er repräsentiert:

- Home
- zentrale Sammlr-Erfahrung
- Marke

Die genaue Größe, Form, Farbe und Animation werden später gestaltet.


55. NAVIGATION UND DESIGN SIND GETRENNT

Diese Spezifikation definiert:

- Informationsarchitektur
- fachliche Besitzer
- Navigationswege
- Hauptbereiche
- Deep-Link-Verhalten

Sie definiert NICHT final:

- Pixelmaße
- Icongrößen
- Headerhöhe
- Schatten
- Animationen
- konkrete Kartendarstellung
- exakte Farben
- endgültiges Mobile-Verhalten

Diese Punkte werden in späteren Design-/Implementierungssessions entschieden.


56. ZIELBILD

Der Nutzer öffnet Sammlr.

Er landet auf Home.

Dort sieht er, was aktuell wichtig ist.

Benötigt ein Vorgang Aufmerksamkeit, führt Sammlr ihn direkt zum konkreten Objekt.

Will er seine Sammlung verwalten:

linker Hauptbereich → Sammlung.

Will er tauschen:

rechter Hauptbereich → Tauschen.

Will er persönliche Informationen, Freunde, Trophäen, Statistiken oder Einstellungen:

Profilicon im Header.

Will er Benachrichtigungen sehen:

Glocke im Header.

Damit bleiben selbst umfangreiche Funktionen in einer sehr einfachen Grundarchitektur organisiert.


57. MENTALE PRODUKTLOGIK

Die drei Hauptbereiche lassen sich gedanklich reduzieren auf:

SAMMLUNG:
„Was habe ich?“

HOME / SAMMLR.:
„Was passiert gerade?“

TAUSCHEN:
„Was kann ich tauschen / was muss ich bei meinen Deals tun?“

Diese drei Fragen bilden den Kern der Hauptnavigation.


58. PRODUKTPHILOSOPHIE

Navigation soll nicht zeigen, wie viele Features Sammlr besitzt.

Navigation soll dem Nutzer helfen, ohne Nachdenken an sein Ziel zu kommen.

Sammlr darf im Hintergrund komplex werden.

Die Oberfläche soll ruhig, klar und sammlerorientiert bleiben.


59. BEWUSST OFFENE DESIGNFRAGEN

Noch nicht final entschieden:

- genaue Gestaltung des mittleren sammlr.-Spots
- endgültiges Album-/Buchsymbol
- endgültige Tauschpfeile
- Größe und Position von Avatar und Glocke
- großer vs. kompakter Header je Seitentyp
- exakte Animationen beim Navigationswechsel
- Verhalten der Bottom-Navi bei Scroll
- exakte Darstellung auf Desktop
- genaue Home-Karten
- zukünftige Navigation bei Shop/Marketplace/Scanner

Diese Punkte sind keine Blocker für die Informationsarchitektur.


60. PRODUKTSTATUS

Der Bereich:

NAVIGATION & INFORMATION ARCHITECTURE

gilt auf fachlicher Produktebene als spezifiziert.

Die drei Hauptbereiche sind:

SAMMLUNG | SAMMLR./HOME | TAUSCHEN

Profil und Benachrichtigungen liegen global im Header.

Freunde, Statistik, Trophäen und Einstellungen sind logisch untergeordnet.

Vor Implementierung muss die aktuelle Navigation gegen diese Sollstruktur geprüft werden.
