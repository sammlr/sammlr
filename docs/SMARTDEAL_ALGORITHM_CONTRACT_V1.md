# SmartDeal Algorithm Contract V1

Stand: 2026-09-10. **SOLL-Spezifikation, keine Implementierung.** Grundlage: [Product Bible V1 einschließlich PO-Nachtrag §37](SMARTDEAL_PRODUCT_BIBLE_V1.md), [historischer IST-Audit](SMARTDEAL_V1_IST_AUDIT.md) und PO-Auftrag vom 2026-09-10.

**Reifegrad:** Algorithm Contract V1 vollständig produktseitig geschlossen. Die finale PO-Regel zur Mehrfachunterdeckung schließt Q4; keine offenen Produktfragen. 34 Spezifikationsabschnitte, 36 zukünftige Testinvarianten und 27 entschiedene Edge Cases. Technische Persistenzanforderungen sind in AC26 ausgewiesen und bedeuten keine Implementierungs-, Schema- oder UI-Freigabe. Die [technische Roadmap](SMARTDEAL_TECHNICAL_ROADMAP_V1.md) bleibt mit 17 Blöcken bestehen.

## 1. Grundziel und Geltungsbereich

**AC01.** Für einen betrachteten Nutzer U entsteht ein globaler Plan über eligible Partner und alle relevanten tradefähigen aktiven Alben. Er beschafft fehlende Sticker, berücksichtigt zusätzliche Sendungen und enthält nur gleichzeitig erfüllbare 1:1-Deals. Ein einzelner Deal darf kleiner sein als das isolierte Paarmaximum, wenn der Gesamtplan nach dem festgelegten Vergleich besser ist.

Der Optimierungsraum umfasst alle zulässigen Gesamtallokationen, nicht nur eine vorab gierig festgelegte Paketwahl je Partner. Der Vertrag gilt für neue SmartDeal-V1-Vorgänge. Manuelle Trades, geschützte Altvorgänge und ihre Semantik werden nicht umdefiniert. Versandkontakt und optionale tradegebundene Nachrichten sind in Bible §37.3 geregelt, keine Optimierungsgewichte.

## 2. Kanonische Inputs und Identitäten

**AC02.** Ein logischer Input S besteht aus:

| Input | Bedeutung |
| --- | --- |
| current_user U | kanonische Nutzer-ID |
| kanonischer Zustandsstand und Auswertungszeitpunkt t | konsistente Grundlage; Zeit nur für zeitabhängige Gültigkeit, nie als Rang-Tie-Break |
| tradefähige aktive Alben | kanonische Album-IDs, Mitgliedschaften/Kataloge und Freigaben |
| Stickeridentität k | Tupel `(album_id, sticker_code)`; gleicher Code in verschiedenen Alben ist nicht derselbe Sticker |
| missing/need N(v,k) | pro Nutzer/Album/Sticker 0 oder 1; keine Mehrfachalbum-Vorsorge |
| available A(v,k) | nichtnegative ganze freie Stückmenge aus kanonischer Availability |
| eligible Partner und richtungsbezogene Tradefähigkeit | geltende Community-/Account-/Pool-/Privacy-Regeln |
| Reservations | gebundene Mengen und zugehörige Vorgänge, nicht nochmals frei nutzbar |
| offene Requests und aktive Trades | Vertragsart, Inhalt, Zustand und Fristen; bestehende Bindungen berücksichtigen |
| Bestands-/Eigenbedarfsprojektion | kanonischer Schutz des eigenen Albumexemplars |

`A` wird konsumiert, nicht vom Optimierer über eine konkurrierende quantity−1-Formel neu erfunden. Wiederverwendbare Quellen laut Audit: InventoryReadService/Snapshots, AlbumPrivacyService, CommunityService, ProfilePrivacyService und Account-Regeln. Aktuelle Services implementieren noch nicht alle neuen V1-Requestbindings; ihre bloße Verwendung ist daher kein Nachweis fertiger V1-Availability.

`N(v,k)=1` genau dann, wenn der tradefähige Sticker physisch fehlt und kein gültiger verbindlich zugesagter Eingang diese Lücke bereits belegt; sonst 0. Mindestens offene V1-Anfragen mit beidseitiger Reservation und angenommene/aktive Vorgänge mit weiterhin gültiger Incoming-Bindung sperren den Need. Das gilt für beide Teilnehmer. Eine beim Versand freigegebene Supply-Reservation hebt die gültige Eingangszusage nicht auf: Transit ist weiterhin geplanter Eingang, kein physischer Besitz.

Ablehnung, Rückzug, Ablauf oder Unfulfillable-Beendigung vor Versand geben den Need frei, sofern er weiterhin physisch fehlt und keine andere gültige Zusage besteht. Tatsächliche Eingangsbuchung erfüllt den physischen Bedarf. Legacy-Verträge wirken entsprechend ihrer tatsächlichen Bindungssemantik; alte unreservierte offene Anfragen erhalten dadurch keine erfundene Bindung. Inkonsistente Inputs dürfen nicht als erfüllbarer Plan ausgegeben werden.

## 3. Eligible Partner und tradefähige Positionen

**AC03.** Ein Kandidat ist nicht U, existiert, hat einen verwendbaren Account, ist nicht in einer der beiden Richtungen geblockt und erfüllt die bestehenden Trade-/Privacy-Regeln. Verwendete Alben/Positionen müssen für beide Richtungen tradefähig sein. Ohne positive verfügbare Menge entsteht keine Angebotsposition; ohne Gegenbedarf keine Lieferung.

„Privacy erlaubt“ bedeutet den kanonischen **Tradezugriff**, nicht pauschal öffentliches Profil/Album. Der geschützte IST-Vertrag erlaubt Poolteilnahme trotz privater allgemeiner Sammlerwelt. Er darf weder umgangen noch durch eine neue pauschale Öffentlichkeitspflicht ersetzt werden. Der im Audit gefundene fehlende Blockfilter der globalen alten Partnerliste ist kein zulässiger Alternativvertrag.

Top-Eligibility und Discovery sind getrennt: Ein grundsätzlich tauschbarer Partner mit kleiner bilateral möglicher Menge kann Discovery-eligible sein, ohne einen Top-Deal zu erhalten. Ein bestehender Trade wird nicht als neuer Vorschlag dargestellt; ein pauschaler Ausschluss derselben Person für jedes weitere Restpaket ist daraus nicht abgeleitet. Weitere Restpakete müssen sämtliche freien Supply-/Need- und GO-Invarianten erfüllen.

## 4. Pairwise Opportunity und Need-Cap

**AC04.** Für ein Paar A/B und tradefähige Identität k:

- `A_can_give_B(k) = min(A_available(k), N(B,k))`.
- `B_can_give_A(k) = min(B_available(k), N(A,k))`.
- Bei fehlender Richtungs-/Album-Eligibility ist der entsprechende Wert 0.
- `pair_size(A,B) = min(Σ_k A_can_give_B(k), Σ_k B_can_give_A(k))`.

Dies ist das isolierte maximal erfüllbare 1:1-Paarvolumen vor Konkurrenz mit anderen Partnern. Die Mengen werden **vor** dem Summieren durch den Bedarf des konkreten Empfängers begrenzt. Supply quantity=3 kann drei Stück im Gesamtplan beitragen, beispielsweise je eines an drei Partner; derselbe V1-Empfänger benötigt dieselbe Album-/Stickeridentität höchstens einmal. Drei Supply-Kopien dürfen deshalb das Paarmaximum bei nur einer solchen Lücke nicht um drei erhöhen.

Das verbindet die PO-Aussage „Stückmengen zählen einzeln“ mit A1. Eine unbeschränkte Summe aller Geberkopien, deren Code irgendwo fehlt, wäre nur eine Supply-Obergrenze, kein realisierbares Paarmaximum. quantity meint hier bereits freie Supply; physical quantity kann durch Eigenexemplar/Reservations weniger freie Kopien ergeben.

## 5. 1:1-Invariante und zulässige Allokation

**AC05.** Für U, Partner p und Identität k bezeichnet:

- `x(p,k)` die Menge U → p.
- `y(p,k)` die Menge p → U.
- `z(p)` ist 1 genau dann, wenn p im Plan einen Deal erhält.

Alle Mengen sind ganze Zahlen ≥0. Für jeden ausgewählten Partner:

`d(p) = Σ_k x(p,k) = Σ_k y(p,k)`.

Kein automatischer SmartDeal darf davon abweichen. Keine Seitenauffüllung mit nicht benötigten Stickern, um rechnerisch Balance zu erzeugen. Für nicht ausgewählte Partner sind alle x/y null. Manuelle Ungleichheiten sind nicht Gegenstand dieser Invariante.

## 6. Partner-Zusammenführung

**AC06.** Pro Partner-ID höchstens ein Deal im Plan. Alle dessen verwendeten Alben werden in demselben Deal vereint. Eine Albumfilter-Herkunft ist keine Allokationsgrenze und kein Gewicht. Der Plan darf beispielsweise WM26 abgeben und Bundesliga/EM24 empfangen.

## 7. Globale Ressourcen- und Bedarfsconstraints

**AC07.** Harte Nebenbedingungen für alle k und p:

1. `Σ_p x(p,k) ≤ A(U,k)` — eigene freie Kopien werden partnerübergreifend nicht doppelt verwendet.
2. `y(p,k) ≤ A(p,k)` — die Supply des jeweiligen Partners wird nicht überzeichnet.
3. `x(p,k) ≤ N(p,k)` — der Partner erhält höchstens seine eine Lücke dieser Identität.
4. `Σ_p y(p,k) ≤ N(U,k)` — dieselbe eigene Lücke darf im Gesamtplan nur einmal geschlossen werden.
5. x/y dürfen nur auf den nach AC03 zulässigen Richtungen positiv sein.

Folglich sind einzelne Line-Item-Mengen für denselben Empfänger/k in V1 höchstens 1; die Geber-Supply und deren Gesamtnutzung über verschiedene Partner bleiben echte Mehrfachmengen. Austauschbare physische Kopien benötigen für diese Semantik keine neu erfundenen Stück-IDs: Mengenkapazität genügt. Es wird keine Supply aus erst zukünftig empfangenen Stickern zur Finanzierung anderer Deals verwendet.

## 8. Maximale Planlänge

**AC08.** `trade_count(P) = Σ_p z(p) ≤ 5`. Ein Partner ist ein Deal. Der leere Plan mit 0 Deals ist zulässig, wenn keine Top-Opportunity besteht.

Die Bible behält die Produktformulierung „maximal ungefähr fünf“. Der vorliegende technische Auftrag spezifiziert ausdrücklich höchstens fünf für diesen Algorithm Contract. Es gibt keine Top-3-Änderung. Die Zahl gleichzeitig offener Anfragen ist eine separate Lifecyclegrenze, keine Planlänge.

## 9. Mindestgröße und fehlende Maximalgröße

**AC09.** Für jeden ausgewählten Top-Deal gilt `d(p) ≥ 5`. Ein nach globaler Allokation auf 4 reduziertes Paket darf nicht als Top-Deal verbleiben; ein anderer gültiger Gesamtplan muss betrachtet werden. Kleinere Opportunities bleiben außerhalb des Top-Plans für manuelle Discovery relevant.

Diese technische Grenze ist im aktuellen Auftrag ausdrücklich festgelegt; sie ist keine eigenmächtige Verschärfung des vorher ungefähren Bible-Richtwerts. Es gibt **keine künstliche Obergrenze für d(p)**. 150↔150 ist gültig, wenn Bedarf, Supply und Eligibility es ermöglichen.

## 10. Hauptnutzen

**AC10.** `G(P) = total_gain(P) = Σ_p Σ_k y(p,k) = Σ_p d(p)`.

Dank der globalen Need-Constraint ist jedes gezählte eingehende Stück eine zusätzliche eigene Lücke. Dieselbe Lücke von zwei Partnern darf nicht doppelt als Gain erscheinen. Die Zahl unterschiedlicher Alben, Stückwert, Albumfortschritt und angebotener Geberüberschuss sind keine zusätzlichen Nutzenpunkte.

Die Auswahl erfolgt global unter AC05–AC09 und dem Comparator; nicht zuerst für jeden Partner dessen größtes Paket unveränderlich festlegen.

## 11. Versand-Effizienzregel und exakte Grenze

**AC11.** Für gültige Pläne L/H mit `n_H > n_L` gilt `Δn=n_H−n_L`, `ΔG=G_H−G_L`:

- `ΔG < 2Δn`: L gewinnt.
- `ΔG ≥ 2Δn`: H gewinnt, ausdrücklich auch bei exakt erreichter Schwelle.

Ein zusätzlicher Trade muss **mindestens** zwei zusätzliche Lücken schließen. `E(P)=G(P)−2n(P)` bildet diese Regel algebraisch ab, ohne einen neuen Produkt-Score einzuführen. Bei gleichem E entscheidet höherer G zugunsten des Mehrgewinns. Deshalb gewinnt 26/4 gegen 20/1 (beide E18) und 41/5 gegen 35/2 (beide E31). Bei gleichem G gewinnt durch E der Plan mit weniger Trades. „Weniger Trades“ ist keine vorgelagerte Gleichstandsregel, die die entschiedene exakte Mindestschwelle wieder aufheben dürfte.

## 12. Deterministischer Planvergleich

**AC12.** Ungültige Pläne werden ausgeschlossen. Der Gewinner ist das lexikographische Optimum über **alle** gültigen Allokationen desselben kanonischen Inputs:

| Priorität | Vergleich |
| --- | --- |
| 1 | `E=G−2n` maximieren |
| 2 | `G` maximieren |
| 3 | `D`, absteigend sortierter Dealgrößenvektor, lexikographisch maximieren |
| 4 | `J`, numerische Partner-IDs in Ausgabeordnung AC29, lexikographisch minimieren |
| 5 | `C`, vollständige kanonische Positionsfolge AC14, lexikographisch minimieren |

Nach Gleichheit von E und G ist n bereits gleich; eine zusätzliche n-Stufe wäre redundant. Der Comparator ist vollständig, antisymmetrisch auf logischen Plänen und transitiv. Identische C bei gleichen vorherigen Kriterien bedeutet denselben logischen Plan. Keine Zufallsentscheidung, keine alternative K-Lesart. Der leere Plan hat G=n=E=0; jeder zulässige nichtleere Plan mit mindestens fünf Stickern je Deal hat positives E.

## 13. Deterministische Partner-Tie-Breaks

**AC13.** Kanonische Nutzer-/Partner-IDs werden numerisch **ASC** verglichen, nicht als Username, Anzeigename, zufälliger Timestamp oder String einer Zahl. Bei gleichen vorhergehenden Plankriterien wird J(P) lexikographisch ASC bevorzugt. J entsteht aus der nach Größe DESC, dann Partner-ID ASC geordneten Ausgabe; damit ist auch die Zuordnung gleicher Größenvektoren zu Personen deterministisch.

Keine Nutzung von last_active, Request-Erzeugungsreihenfolge, DB-Zeilenreihenfolge oder Zufall. Für das Ranking neuer Vorschläge beeinflussen Zeiten allein tatsächliche Frist-/Eligibility-Zustände im Input. Davon getrennt verwendet die Bestandsverlust-Auflösung bestehender Bindungen ausdrücklich Vertragsstufe und Bindungsalter nach AC26; dies ist kein SmartDeal-Ranggewicht.

## 14. Kanonische Stickerauswahl

**AC14.** Erst nach Gleichheit aller vorrangigen globalen Plankriterien werden Positionen gewählt nach:

1. kanonische Album-ID ASC;
2. kanonischer Sticker-Code ASC.

Für textuelle kanonische Album-IDs/Codes bedeutet ASC lexikographisch nach Unicode-Codepunkten, unabhängig von Locale, Groß-/Kleinschreibungs-Faltung und natürlicher Zahlensortierung. Kürzere Präfixfolge zuerst. Beispiel: Code `10` vor `2`, sofern dies die kanonischen Codes sind. Keine Identitäten normalisieren oder umbenennen; Aliasauflösung ist Aufgabe der kanonischen Quelle, nicht des Comparators.

C(P) wird folgendermaßen verglichen: Deals in Ausgabeordnung; pro Deal zuerst Incoming-Identitäten in obiger Reihenfolge, danach Outgoing-Identitäten in derselben Reihenfolge, jeweils als Stückfolge. Das logische Line-Item enthält `(album_id, sticker_code, quantity)`; äquivalente gesplittete Zeilen werden zum Vergleich aggregiert. Mengen werden bei der Vergleichssemantik als wiederholte Stückeinheiten berücksichtigt, ohne eine konkrete Speicher-/Transportkodierung festzulegen. Need-Cap begrenzt dieselbe Identität je Empfänger in V1 auf 1.

Diese Reihenfolge entscheidet gleichwertige Incoming-Auswahl, aber darf nicht die globale Ressourcenzuteilung vorwegnehmen. Keine eigenständige Produktgewichtung nach Album-ID: ASC ist ausschließlich letzter Tie-Break.

## 15. Outgoing-Zuteilung im Gesamtplan

**AC15.** Ein knapper eigener Sticker, den mehrere Partner benötigen, wird im gemeinsamen Allokationsraum verteilt. Lokales lexikographisches Abschneiden darf kein global besseres Ergebnis ausschließen. Hat Fatima Alternativen und Johann nur den knappen Sticker, muss die global bessere Verteilung überhaupt berücksichtigt werden.

Auch Incoming-Auswahl muss die eigene globale Need-Cap wahren. Erst wenn Nutzen, Versandvergleich, Größenverteilung und Partnerfolge gleichwertig sind, greifen AC14-Tie-Breaks. Der Algorithm Contract legt Ergebnisverhalten fest, keine konkrete Suchreihenfolge.

## 16. Keine Albumgewichtung

**AC16.** Kein Bonus/Malus für Favoritenalbum, fast abgeschlossenes Album, Alter, WM/Bundesliga, Trophy-Relevanz, Seltenheit oder Marktwert. Missing Piece = Missing Piece. Relevante Freigabe/Eligibility kann eine Position ausschließen; sie ist kein numerischer Albumscore.

## 17. Keine Partnerqualitätsgewichtung

**AC17.** Ratings, Entfernung oder sonstige Partnerqualität verändern die mathematische Top-Auswahl nicht, solange die kanonische Eligibility erfüllt ist. Sie sind keine Tie-Breaks. Spätere Filter/Sortierungen manueller Discovery ändern diesen V1-Planvertrag nicht automatisch.

## 18. Live-State und Reservations

**AC18.** Berechnung und GO verwenden den aktuellen kanonischen Zustand. Aktive gebundene Mengen dürfen nicht als Supply erneut erscheinen. Neue SmartDeal-V1-Anfragen reservieren **ab GO beide Seiten mengenbasiert**. Accepted-Bindungen werden nicht doppelt abgezogen oder bei Annahme nochmals angelegt. Bei eigenem Versand bleiben die physische Ausbuchung und Überführung der eigenen Bindung maßgeblich; erwarteter Eingang wird erst beim eigenen bestätigten Empfang physisch gebucht.

IST laut Audit: Reservation erst bei accept, Smart-Frist 48h und Inventory-Guard blockiert Unterdeckung. Das bleibt für Altvorgänge geschützt und ist **nicht** der neue SOLL-Vertrag. Keine Implementation dieser Unterschiede hier.

Alle Inputs einer Berechnung müssen einen zusammengehörigen kanonischen Zustand beschreiben. Eine alte Vorschlagsanzeige ist keine Zusicherung, dass andere Nutzer seitdem nichts reserviert haben. Unveränderter Input umfasst auch unveränderte zeitabhängige Gültigkeit.

Ein später neu berechneter, besserer SmartDeal darf niemals eine bestehende gültige Reservation verdrängen. Bestehende Zusagen sind harte Constraints; Optimierung nutzt ausschließlich aktuell freie Mengen. AC26 wird durch reale Unterdeckung ausgelöst, nicht durch höheren Gain eines neuen Vorschlags.

## 19. Vorschläge reservieren nichts

**AC19.** Ein Top-Plan ist read-only und erzeugt weder Request noch Bindung oder Inventorybuchung. Die gemeinsame Ausführbarkeit gilt für seinen zugrunde liegenden Zustand, nicht als Reservation aller dargestellten Deals. Unabhängige Pläne anderer Nutzer können dieselben Ressourcen zunächst ebenfalls erwägen. Verbindliche Konkurrenz wird erst bei atomarem GO entschieden.

„Neu berechnen“ ist kein Zufallsgenerator. Das Verwerfen eines Vorschlags ist kein Cancel eines existierenden Requests.

## 20. GO Validation

**AC20.** Ein neuer GO erfordert serverseitig im verbindlichen Zustandsübergang mindestens:

- authentifizierter berechtigter Akteur und weiter eligible Partner;
- alle betroffenen Alben/Positionen weiter tradefähig;
- sämtliche exakten Outgoing- und Incoming-Mengen verfügbar;
- gültiger Need-Cap und weiterhin 1:1;
- keine Kollision mit inzwischen entstandenen Bindungen;
- Opportunity-Inhalt vollständig gültig;
- bei Erzeugung einer neuen eigenen Anfrage offener Count <3;
- keine Annahme eines bereits abgelaufenen/beendeten Vertrags.

Die Anzeige und ein vom Client gesendeter Hash reichen nicht. Geprüft wird der genaue angezeigte Vertragsinhalt; ungültige Positionen dürfen nicht heimlich ersetzt oder gekürzt werden. Eine reine Rangänderung invalidiert das Paket nicht: Auch Platz 4 → Platz 6 darf GO erfolgreich durchlaufen, wenn alle harten Invarianten atomar erfüllt sind. Erneute Zugehörigkeit zur aktuellen Top 5 ist nicht erforderlich; Top 5 ist Discovery-/Darstellungslogik.

Mutual GO ist ein anderer Zweig: Bei identischem offenem Gegenrequest wird dessen Vertrag geprüft und atomar angenommen. Seine eigenen, bereits bestehenden Reservations werden als **zu diesem Vertrag gehörige Bindung** geprüft und nicht als fremder Supply-Konflikt behandelt. Ebenso wird die zu genau diesem Vertrag gehörige Incoming-Zusage nicht gegen dessen eigene Annahme verwendet; fremde Supply-/Need-Bindungen bleiben ausgeschlossen. Kein doppeltes Reservieren. Ein bereits eingegangener Vertrag benötigt zur Annahme keinen neuen ausgehenden Requestplatz.

## 21. Atomare Request-Erzeugung

**AC21.** Gültigkeitsprüfung, neue Requestanlage und vollständige beidseitige mengenbasierte Bindung bilden einen atomaren Übergang. Es gibt keinen von außen gültigen Zustand „Request ohne vollständige Bindung“ oder „Bindung ohne Vorgang“. Bei Konflikt scheitert der Übergang vollständig; keine halbe Seite bleibt gespeichert oder gebunden.

Auch Mutual-GO-Annahme und konkurrierende GO-Entscheidungen müssen einen eindeutigen konsistenten Zustand ergeben. Atomizität/Isolation sind Anforderungen; SQLite-Transaktionsdesign, Tabellen, Locks und Hashspeicherung werden hier nicht entschieden. Notification-Infrastruktur muss aus dem verbindlichen Fakt eine deduplizierbare Benachrichtigung ermöglichen; kein Transport-/Queue-Design festgelegt.

## 22. Drei offene eigene ausgehende Anfragen

**AC22.** Vor neuer Requesterzeugung gilt `count(open outgoing SmartDeal-V1 requests) < 3`; nach Erfolg höchstens 3. Kein Tageslimit und kein per-Album-Limit. Accepted, declined, expired und beendet zählen nicht. Ein freier Platz ist sofort wieder nutzbar.

Die Annahme eines identischen eingehenden Requests durch Mutual GO erzeugt keinen vierten ausgehenden Vorgang. Retry desselben GO erzeugt ebenfalls keinen neuen Count-Eintrag. Ausschließlich offene ausgehende SmartDeal-V1-Anfragen zählen zur V1-Quote. Legacy-Requests, Altvorgänge und manuelle Trades zählen nicht mit und behalten ihre bisherigen Regeln. Ihre tatsächlichen Supply-/Reservation-/Incoming-Bindungen bleiben für V1 dennoch wirksam.

## 23. 24h Expiry

**AC23.** Für neu erzeugte V1-Anfragen: `expires_at = created_at + 24 Stunden`, als absolute Zeitspanne und unabhängig von lokaler Sommerzeit. `t < expires_at` ist fristgültig; `t ≥ expires_at` nicht mehr annehmbar.

Nach Ablauf müssen Status/offene Quote und vollständige Reservationsfreigabe konsistent wirksam sein; künftige Availability darf die Mengen wieder nutzen. Eine bloß zeitlich abgelaufene offene Zeile darf nicht unbegrenzt den Platz blockieren. Kein Scheduler-/Lazy-/DB-Design vorgeschrieben. Bei gleichzeitigem accept/expiry muss genau ein zulässiger geordneter Übergang gelten: rechtzeitige erfolgreiche Annahme oder Ablauf; keine Freigabe eines bereits angenommenen Vorgangs durch nachlaufende Request-Expiry. Wiederholung darf weder doppelt freigeben noch neu erzeugen.

## 24. Mutual GO und semantische Deal-Identität

**AC24.** Die richtungsunabhängige Identität enthält mindestens Vertragsart SmartDeal V1, das numerisch ASC kanonisierte Nutzerpaar `(low_user_id, high_user_id)` und zwei vollständige Positions-Multimengen:

- low → high: `(album_id, sticker_code, quantity)`;
- high → low: `(album_id, sticker_code, quantity)`.

Reihenfolge der ursprünglichen Anzeige, Senderrolle, Username, Gesamtplan-ID und Clientzeit sind nicht Teil der semantischen Paketidentität. Positionen werden aggregiert und kanonisch geordnet. Spiegelung A.outgoing=B.incoming und A.incoming=B.outgoing ergibt genau denselben Vertrag, einschließlich Mengen/Albumidentitäten. Verschiedene Teilnehmer oder veränderte Position/Menge/Albumidentität ergeben nicht denselben Vertrag.

Die Identitätsprüfung muss auf Anwendungsebene collision-safe sein: Ein technischer Hash-Treffer allein darf nie verschiedene vollständige Verträge zusammenfallen lassen. Kein Hashformat implementiert. Semantische Paketidentität ist von Vorgangsidentität zu unterscheiden: Ein beendeter früherer Vertrag darf eine spätere neu berechnete identische Opportunity nicht für immer blockieren.

A GO erzeugt einen offenen eingefrorenen Request mit beiden Bindungen. B GO auf genau diesen gültigen Vertrag akzeptiert ihn atomar, statt eine Kreuzanfrage anzulegen. Bei nahezu gleichzeitigem GO müssen die Handlungen als ein konsistenter Verlauf wirken: eine Anlage, eine Annahme, eine Bindung pro Position; unter erfüllten Voraussetzungen genau ein accepted Vorgang. Derselbe Akteur zweimal GO ist Retry, keine Zustimmung der anderen Person. Zeitgleiche andere Ereignisse dürfen zur Ablehnung wegen Invalidität führen, niemals zur doppelten Bindung.

Ein global für A optimaler Plan und ein global für B optimaler Plan müssen nicht dieselben Partner/Pakete auswählen. Mutual GO wird deshalb über gleichen konkreten Vertragsinhalt erkannt, nicht durch die Behauptung automatisch identischer Gesamtpläne.

## 25. Request Freeze

**AC25.** Nach erfolgreichem GO ist der Inhalt unveränderlich. Neuberechnung verändert weder Positionen noch Mengen des Requests. Zustand darf nach Lifecyclevertrag wechseln; eingefrorener Inhalt bleibt erhalten. Keine clientseitige Bearbeitung als derselbe SmartDeal und keine verdeckte Ersatzwahl.

## 26. Unfulfillable: beenden statt reparieren

**AC26.** Reale Bestandskorrekturen bleiben erlaubt. Der Versandstand bestimmt die Behandlung eines dadurch unerfüllbaren V1-Vertrags:

**Vor irgendeinem Versand:** Hat noch keine Seite versendet, endet der gesamte betroffene Deal sichtbar unfulfillable / nicht mehr möglich. Sämtliche zugehörigen Reservations werden freigegeben, die Gegenseite informiert, der eingefrorene Vertrag erhalten. Kein Teilvertrag bleibt bestehen, keine Paketmutation, kein Rebalancing oder Reparatureditor. Anschließend vollständige Neuberechnung aus dem aktuellen Zustand ohne Priorität für den früheren Partner.

**Ab Versand mindestens einer Seite:** Keine automatische Beendigung wie bei einer gewöhnlichen unfulfillable Anfrage. Sichtbarer Problem-/Action-required-Zustand und menschliche Klärung über den bestehenden Problemflow beziehungsweise dessen spätere V1-Anbindung. Keine automatische Inventory-Rückabwicklung, keine Paketmutation und kein Reservations-/Lifecycle-Reset, der tatsächlichen Versand ungeschehen behauptet. Reale Ein-/Ausbuchungen, Transit und Verlauf bleiben erhalten; kein neuer komplexer Reparatureditor.

### AC26: Deterministische Priorität bei Mehrfachunterdeckung

Finale PO-Entscheidung: **stärkerer Vertrag vor schwächerem; innerhalb derselben Stufe ältere gültige Bindung vor jüngerer**.

| Schutzpriorität | Vertragszustand | Behandlung bei Unterdeckung |
| --- | --- | --- |
| 1 (höchste) | Mindestens eine Seite hat physisch versendet | Aus automatischer Verliererauswahl ausgeschlossen; bei Problem bestehender Problem-/Action-required-Flow |
| 2 | Angenommener/aktiver Trade, noch keine Seite versendet | Vor offenen Anfragen schützen; innerhalb dieser Stufe früherer Eintritt in den angenommenen bindenden Zustand zuerst |
| 3 | Offene reservierende SmartDeal-V1-Anfrage | Frühere gültige beidseitige Bindung zuerst schützen |

Für automatisch auflösbare Vorgänge ist die Schutzordnung lexikographisch `(Stufe ASC, bindender_Zustandszeitpunkt ASC, kanonische_Vorgangs-ID numerisch ASC)`. Der Zeitvergleich erfolgt als kanonischer absoluter Zeitpunkt, nicht nach lokaler Anzeige. Bei Zeitgleichheit bleibt die kleinere ID geschützt; beim Beenden gilt die umgekehrte Reihenfolge. Die kanonische V1-Request-ID bleibt auch nach Annahme die Referenz desselben Vorgangs; nicht je nach Ansicht zwischen Request-ID, Trade-ID und Reservation-Zeilen-ID wechseln. Eine spätere alternative Persistenz muss eine entsprechend stabile eindeutige Vorgangsidentität tragen.

Bei einer realen Unterdeckung werden nur die noch unversandten, von aktuell unterdeckten Ressourcen betroffenen automatisch beendbaren V1-Verträge in dieser umgekehrten Schutzordnung vollständig beendet: schwächere Stufe zuerst, darin jüngste Bindung, bei Zeitgleichheit höchste ID. Nach jeder vollständigen beidseitigen Freigabe wird die Deckung sämtlicher betroffener Ressourcen erneut geprüft; keine weiteren Verträge beenden, wenn deren Unterdeckung bereits entfällt. Dadurch entscheidet weder die Reihenfolge der Stickerqueries noch ein Albumrang. Ein Vertrag wird nie teilweise geschrumpft. Maßstab ist die reale tauschbare Kapazität nach Eigenbedarf vor Abzug der zu prüfenden Bindungen, nicht die bereits reservationsbereinigte freie Availability ein zweites Mal.

Ein höher priorisierter Vorgang wird nicht geopfert, um einen niedrigeren zu erhalten. Bereits versandte Vorgänge bleiben auch dann aus der automatischen Auswahl ausgeschlossen, wenn nach Freigabe niedrigerer Bindungen weiterhin Unterdeckung besteht: Problemflow, keine fiktive Deckung oder automatische Rückbuchung. Geschützte Legacy-Verträge behalten AC27 und ihre tatsächlichen Bindungswirkungen; diese Regel autorisiert keine rückwirkende Legacy-Autobeendigung. Nach jeder V1-Beendigung gelten vollständiger Release, sichtbares Unfulfillable, Information der Gegenseite, Payload-Erhalt und unabhängige Neuberechnung. Rating, Partnername, SmartDeal-Rang und Albumpriorität sind irrelevant.

### AC26: Kanonischer Bindungszeitpunkt — Schemaabgleich

| Vorhandenes Feld / Quelle | Semantische Eignung |
| --- | --- |
| `trade_requests.created_at` | Anfrageerzeugung; kein allgemeiner Annahmezeitpunkt. Bei künftig garantiert atomarer V1-Anlage plus Bindung nur dann als Open-Bindungszeit geeignet, wenn genau diese Zeit gemeinsam persistiert wird. |
| `trades.created_at` | Im aktuellen `_lifecycle_trade` ausdrücklich aus `trade_requests.created_at` übernommen; deshalb **nicht** als Annahme-/Bindungsalter verwenden. |
| `trades.updated_at` | Veränderlicher Lifecyclezeitpunkt; **nicht** als unveränderliches Bindungsalter verwenden. |
| `trade_reservations.created_at` | Tatsächliche Erzeugung einer Reservation. Im heutigen `TradeReservationService.accept` entstehen die Reservations erstmals in der Annahmetransaktion; `MIN(created_at)` pro Trade ist bereits die bestehende `accepted_at`-Projektion im Timeline-Kontext. Für nach diesem Pfad konsistent erzeugte Legacy-Bindungen semantisch geeignete Quelle; keine erfundene Annahmezeit für Datensätze ohne diese Evidenz. |
| `trade_events.occurred_at` beim `SMART_ACCEPTED_EVENT` | Tatsächlicher Annahmeevent im heutigen Smart-HTTP-Callback; geeignet, wenn dieser konkrete Event nachweislich vorhanden und eindeutig ist. Der generische accept-Service garantiert ihn nicht für alle Vertragsarten/Einstiege. Beliebige Events sind kein Ersatz. |

Belege: [Reservationsschema](../App/Database/migrations/0002_trade_reservations.up.sql), [Lifecycle-Schema](../App/Database/migrations/0001_trade_lifecycle_foundation.up.sql), [accept und Lifecycleanlage](../App/services/trade_reservations.py), [Timeline-Projektion und Smart-Accept-Callback](../App/webapp.py).

**Technische Persistenzanforderung für V1:** Den Zeitpunkt der vollständigen offenen Bindung sowie den Eintritt in den angenommenen bindenden Zustand jeweils dauerhaft, eindeutig und unveränderlich festhalten. In Stufe 2 gilt der Annahmezeitpunkt, nicht der frühere GO-Zeitpunkt; in Stufe 3 der Reservationszeitpunkt. GO-/Accept-Retry darf diese Zeiten nicht verjüngen. Da V1 Reservations bereits bei GO anlegt und bei accept übernimmt, ist deren `created_at` allein künftig **kein** Annahmezeitpunkt. Das aktuelle Schema garantiert keinen universellen V1-Accept-Zeitfakt; SD-T1/SD-T6b müssen dessen Speicherung bzw. einen garantiert einmaligen Annahmeevent sicherstellen. Fehlende/uneindeutige Zeitdaten nicht mit `updated_at`, aktuellem Zeitpunkt oder willkürlicher ID-only-Sortierung ersetzen. Keine Datenmigration, kein Backfill und keine neue Produktfrage in diesem Auftrag.

## 27. Altvorgänge und Vertragsgrenze

**AC27.** Nur neue ausdrücklich als SmartDeal V1 erzeugte Vorgänge folgen diesem Vertrag. Bestehende historische/laufende Requests/Trades behalten ihre ursprüngliche Reservations-, Frist-, Buchungs- und Abschlusssemantik. Keine rückwirkende Migration oder Umdeutung des alten Smart-Markers. Ein späterer technischer Umbau muss Vertragsarten sicher unterscheiden und Altvorgänge weiterhin abschließbar halten; keine Schemaentscheidung getroffen.

Legacy-Bindungen, die kanonisch weiterhin aktiv sind, stehen auch einem neuen V1-Plan nicht frei zur Verfügung. Legacy-Request darf nicht nur zum Zweck einer neuen V1-Berechnung verändert werden.

## 28. Logisches Ausgabeformat

**AC28.** Technologieunabhängiger Inhalt:

| Ebene | Feld | Semantik |
| --- | --- | --- |
| Deal | partner_id | kanonische Nutzer-ID |
| Deal | deal_size | Summe Incoming = Summe Outgoing |
| Deal | outgoing_line_items | geordnete `(album_id, sticker_code, quantity)`-Positionen U → Partner |
| Deal | incoming_line_items | geordnete Positionen Partner → U |
| Deal | affected_album_ids | eindeutige verwendete Album-IDs ASC, keine eigene Handelsgrenze |
| Plan | ordered_deals | Reihenfolge nach AC29 |
| Plan | total_gain | G(P) |
| Plan | trade_count | n(P) |

Keine UI-Felder, Ratinggewichte, Adressdaten, Zufalls-IDs oder künstlichen Dealobergrenzen. Identität/Validierungsgrundlage sind Vertragsanforderungen, kein hier implementierter Token. Keine Null-/Negativpositionen, keine doppelten unaggregierten Identitäten innerhalb derselben Richtung. Ein leerer Plan hat leere ordered_deals, Gain 0 und Count 0.

## 29. Stabile Ausgabeordnung

**AC29.** Finale Deals nach deal_size **DESC**, dann numerischer partner_id **ASC**. Line-Items und affected_album_ids nach AC14 ASC. Gleicher vollständiger kanonischer Input und dieselbe endgültig freigegebene Comparator-Regel ergeben denselben logischen Plan, unabhängig von Input-Reihenfolge oder Ausführungsinterleaving innerhalb einer Berechnung.

Bei festgelegter identischer Serialisierung muss derselbe Inhalt bytegleich reproduzierbar sein; ein konkretes Format wird hier nicht vorgegeben. Flüchtige Generierungszeitpunkte/Anzeigeattribute dürfen nicht als Bestandteil des algorithmischen Plans Byte-/Semantikgleichheit verhindern.

## 30. Edge-Case-Matrix

**AC30.** Konzeptionelle Vertragsprüfung, keine ausgeführten Runtime-/Produkttests. Zahlenpaare G/n sind jeweils Gain/Tradeanzahl; alle angegebenen Alternativen müssen die Supply-/Need-/Eligibility-Constraints erfüllen. Wo nötig sind vereinfachende Datenannahmen explizit genannt. Der eindeutige Comparator AC12 gilt für sämtliche Fälle.

| Case | vereinfachter Input | erwartetes Verhalten | entscheidende Regel |
| --- | --- | --- | --- |
| 1 | ein eligible Partner; 20 unterschiedliche freie benötigte Positionen je Richtung | ein Deal 20↔20, G=20, n=1 | AC04/05/09/10 |
| 2 | Paarmaxima A20, B6; eigene Kopie k nur einmal, beide benötigen k; sonst unabhängige Bedarf-/Supplymengen, A kann ohne k noch 19↔19, B mit k 6↔6 | A20+B6 ist ungültig. A19+B6 und A20+B5 sind beide gültig mit G25/n2 und schlagen A20/n1 (ΔG5>2). Unter diesen Annahmen gewinnt A20+B5 im Größen-Tie-Break gegen A19+B6; k geht an A. Andere Alternativen benötigen konkrete Inputmengen | AC07/11/15; ohne Restmengenannahmen sind die zwei Paarmaxima allein nicht entscheidend |
| 3 | gültige Alternativen 20/1 und 23/4, etwa 8+5+5+5 | 20/1 gewinnt: 3 zusätzliche Sticker <6 erforderlich | AC11; E18 gegenüber E15 |
| 4 | gültige Alternativen 20/1 und 26/4, etwa 11+5+5+5 | Entschieden: 26/4 gewinnt; Mindestschwelle exakt erfüllt, höherer G | AC11/12; beide E18 |
| 5 | 35/2 gegen 36/5 | 35/2 gewinnt: +1<6; E31>E26 | AC11 |
| 6 | 35/2 gegen 41/5 | Entschieden: 41/5 gewinnt; exakt +6 für drei weitere Trades, höherer G | AC11/12; beide E31 |
| 7 | sechs Partner mit je 10↔10; disjunkte eigene Lücken und genug Supply; IDs1–6 | fünf Deals, IDs1–5; Gain50; keine sechste Sendung | AC08/13; Annahme echter Gleichwertigkeit notwendig |
| 8 | einziges Paar 4↔4, sonst eligible | leerer Top-Plan; Partner bleibt in kleiner Discovery-Opportunity auffindbar | AC03/09 |
| 9 | ein eligible Paar mit 150 verschiedenen Lücken je Richtung und genügend Supply | 150↔150 zulässig; keine künstliche Zerstückelung | AC05/09 |
| 10 | ARG17 physical5, Eigenexemplar1, reserved1 → kanonisch available3; drei Partner benötigen je einmal ARG17, zusätzlich je vier passende eigene Give-Positionen und fünf disjunkte Receives | drei Kopien desselben Gebercodes können in drei je 5↔5-Deals verwendet werden; niemand erhält ARG17 zweimal, protected/reserved Kopie bleibt ungenutzt | AC04/07; Gebermehrmenge ≠ Empfängermehrbedarf |
| 11 | A und B sehen exakt gespiegelte Positionen/Mengen desselben Vertrags | semantische Identität gleich; Vorschläge selbst reservieren nichts | AC19/24 |
| 12 | A GO erfolgreich; danach B GO auf identischen offenen, gültigen Request | bestehenden Vorgang atomar accepted; keine zweite Anfrage/Reservation; eigene Bindung zählt nicht als fremde Kollision | AC20/21/24 |
| 13 | A/B GO nahezu gleichzeitig; keine sonstige Invalidierung, Erzeugerquote frei | genau ein Request/angenommener Vorgang; geordnete atomare Anlage+Annahme; keine Kreuzanfrage | AC21/24 |
| 14 | nach Berechnung bindet anderer Vorgang die einzige für dieses Paket benötigte freie Kopie | GO dieses Pakets scheitert atomar; keine Teilreservation/heimliche Ersatzwahl | AC18/20/21; bleibt genug freie Menge, ist erneute Mengenprüfung maßgeblich |
| 15 | offene neue Anfrage, t exakt binding_created_at + 24 Stunden absolut | nicht mehr annehmbar, vollständig freigeben, offener Platz frei, Supply wieder nutzbar | AC22/23 |
| 16 | drei offene eigene V1-Requests; GO für eine zusätzliche neue Opportunity | keine vierte Anfrage/Bindung. Annahme eines identischen eingehenden Requests ist keine vierte ausgehende Anfrage | AC20/22/24 |
| 17 | neuer offener, noch unversandter V1-Deal; reale Korrektur entzieht eine zugesagte Kopie, nur dieser Vertrag betroffen | Korrektur erlaubt; sichtbar unfulfillable/beendet; alle seine aktiven Bindungen frei; Partner informiert; Payload unverändert; neuer Plan ohne Partnerbonus | AC26; vollständige Beendigung vor Versand |
| 18 | gleiche G30/n2 und sonst gleiche Voraussetzungen: Größen18+12 gegen15+15 | 18+12 gewinnt lexikographisch: erste Größe18>15 | AC12; keine ID-Auswahl vor Größenvergleich |
| 19 | gleiche G/n/D; geordnete Partnerfolgen [2,7] bzw. [3,4] | [2,7] gewinnt lexikographisch numerisch ASC; bei gleichen Partnerfolgen entscheidet C | AC13/14 |
| 20 | Partner über WM26 entdeckt; gemeinsamer maximaler Deal umfasst WM26, EM24, Bundesliga | ein gemeinsamer Partnerdeal über alle zulässigen Alben; global kann dessen endgültige Größe kleiner als das Paarmaximum sein | AC01/06/15 |
| 21 | ARG17 tauschbar2→1; Fatima älter offen reserviert1, Johann jünger offen reserviert1; sonst alle Positionen gedeckt | Fatima bleibt; Johann endet vollständig, beide Seiten frei, Gegenseite informiert; keine Kürzung | AC26 ältere offene Bindung zuerst |
| 22 | Ein neuerer accepted/unversandter V1-Trade und eine ältere offene V1-Anfrage binden je1; nur1 verbleibt | Accepted bleibt, offene Anfrage endet trotz älterem GO | AC26 Stufe vor Zeit |
| 23 | Zwei accepted/unversandte V1-Trades: A zuerst angefragt, später angenommen; B später angefragt, früher angenommen; Ressource reicht nur für einen | B bleibt wegen früherem Annahmezeitpunkt; A endet vollständig | AC26 Alter des bindenden Zustands |
| 24 | Gleiche Stufe und gleicher Bindungszeitpunkt; V1-Request-IDs12 und19; nur eine Kopie reicht | ID12 bleibt; ID19 endet, unabhängig von Eingabe-/Queryreihenfolge | AC26 ID numerisch ASC |
| 25 | Bei einem Trade hat eine Seite versendet; notwendige Restmenge ist nun unterdeckt | Dieser Trade wird nie automatischer Verlierer; sichtbarer Problemflow, keine Rückbuchung/Paketmutation | AC26 Versand geschützt |
| 26 | Gültige ältere Reservation bindet die letzte benötigte Kopie; neuer Vorschlag hätte höheren G/E | Neuer Plan darf die Kopie nicht nutzen; GO ohne freie Menge scheitert, bestehender Vertrag bleibt unverändert | AC18/20; kein Verdrängen durch Optimierung |
| 27 | Mehrere offene Verträge betreffen zwei unterdeckte Identitäten; Beenden des jüngsten betroffenen Gesamtvertrags deckt bereits beide Engpässe | Nur diesen gesamten Vertrag beenden; alle seine Positionen beidseitig freigeben, nach Deckungsprüfung stoppen; keine weiteren Kürzungen/Beendigungen | AC26 vollständige Freigabe und erneute Deckungsprüfung |

**Ergebnis:** Alle 27 Fälle besitzen unter ihren expliziten Inputannahmen ein eindeutiges erwartetes Verhalten. Die ursprünglichen Cases1–20 bleiben erhalten; Cases21–27 prüfen die abschließende PO-Priorität. Konzeptionelle Vertragsprüfung, keine ausgeführten Produkttests.

## 31. Komplexität und Technikfreiheit

**AC31.** Globale Ressourcenverteilung kann kombinatorisch werden. Exakte Optimierung, Integer Programming, Min-Cost Flow, Matching, Branch and Bound oder deterministische Heuristik werden hier nicht ausgewählt. Der Produktvertrag definiert zulässigen Plan und Gewinnerverhalten, nicht eine bestimmte Technik.

Eine deterministische Heuristik ist nicht allein wegen ihrer Deterministik vertragskonform: Sie muss das vereinbarte Ergebnisverhalten liefern oder Abweichungen vorab zur PO-Entscheidung bringen. Keine stillschweigende Reduktion auf heutiges Greedy, keine vorab begrenzte Kandidatenliste, die einen besseren zulässigen Plan unbemerkt ausschließt.

## 32. Performance-Anforderung

**AC32.** Öffnen und Neuberechnung sollen praktisch nutzbar sein. Keine neue harte Millisekundengrenze in diesem Dokument. Bestehenden [R4-Vertrag](R4_V20_PERFORMANCE_BASELINE.md) und [B1.2-Nachweis mit Grenzen](R5_B12_PERFORMANCE_REPRODUCIBILITY.md) nicht leichtfertig zerstören oder als Nachweis für einen neuen globalen Solver ausgeben.

Reale Beta-Daten und konkurrierende GO-/Expiry-Vorgänge benötigen später einen geeigneten Nachweis. Falls exakte Vertragserfüllung zu teuer wäre, ist **vor semantischer Vereinfachung eine erneute PO-Entscheidung** nötig. Kein Performanceargument ändert automatisch Bedarf, Top-Auswahl, Vergleich, Privacy oder Atomizität.

## 33. Validierbare Invarianten

**AC33.** Zukünftige automatisierte Prüfverträge; keine Testdatei wird in diesem Auftrag erstellt oder verändert:

| ID | Invariante |
| --- | --- |
| I01 | Jeder automatische Deal ist exakt 1:1 in Stückmengen. |
| I02 | Top-Plan enthält 0 bis höchstens 5 Deals. |
| I03 | Jeder enthaltene Deal hat Größe mindestens 5. |
| I04 | Jede Partner-ID kommt im Plan höchstens einmal vor. |
| I05 | Eigene Outgoing-Gesamtmenge je Identität überschreitet freie Supply nicht. |
| I06 | Partner-Supply wird innerhalb des Plans nicht überzeichnet. |
| I07 | Eine eigene Album-/Stickerlücke wird höchstens einmal verplant; gültig zugesagte Eingänge sperren neuen Need auch im Transit. |
| I08 | Jeder Partner erhält je Album-/Stickeridentität höchstens Need1; Mehrfachalbum-Modell fehlt bewusst. |
| I09 | Fremd gebundene Reservations werden nie als freie Supply benutzt. |
| I10 | Geschütztes eigenes Albumexemplar wird nie abgegeben. |
| I11 | Gleicher kanonischer Input ergibt nach finalem Comparator denselben Plan; Input-Reihenfolge ist irrelevant. |
| I12 | Mindestens +2 je zusätzlichem Trade; exakt erreicht gewinnt höherer G (26/4 und 41/5). |
| I13 | Comparator E DESC, G DESC, D DESC, J ASC, C ASC ist vollständig, antisymmetrisch und transitiv; semantisch gleicher Plan vergleicht gleich. |
| I14 | Bei gleicher G/n gewinnt Größenvektor18+12 gegen15+15. |
| I15 | Partner-ID numerisch ASC und Album-/Codefolge ASC brechen verbleibende Gleichstände. |
| I16 | Lokales Outgoing-Greedy darf keinen global besseren Plan ausschließen. |
| I17 | Berechnung erzeugt keine Requests, Reservations oder Inventorybuchungen. |
| I18 | GO revalidiert Eligibility, exakte Mengen, Need, Balance, Opportunity und Erzeugerquote atomar serverseitig; Rangverlust allein ist kein Ablehnungsgrund. |
| I19 | Requestanlage und beidseitige Reservation sind atomar; Fehler hinterlassen keinen Teilzustand. |
| I20 | Erfolgreicher GO friert alle Vertragspositionen/Mengen ein; Recompute verändert sie nicht. |
| I21 | Maximal 3 offene eigene V1-Anfragen; keine Tages-/Albumquote, kein Limitverbrauch durch reine Annahme oder Legacy-/manuelle Vorgänge. |
| I22 | Exakt ab 24h nicht mehr annehmbar; Freigabe/Quote wirksam, keine nachlaufende Freigabe accepted. |
| I23 | Gespiegelte vollständige Pakete besitzen dieselbe semantische Identität; Mengen/Album/Teilnehmeränderung unterscheidet sie. |
| I24 | Mutual GO führt zu einem Vorgang; Same-actor-Retry ist keine Gegenzustimmung; keine doppelte Reservation. |
| I25 | Vor jedem Versand: ganz beenden/freigeben/informieren; ab erstem Versand: Problemflow ohne fiktiven Reset. Reale Korrektur bleibt erlaubt. |
| I26 | Recompute nach Unfulfillable bevorzugt den alten Partner nicht. |
| I27 | Multi-Album-Deal möglich; Albumfilter begrenzt den Deal nicht. |
| I28 | Kein Rankinggewicht für Album, Trophy, Seltenheit, Marktwert, Rating oder Entfernung. |
| I29 | Kein künstliches Dealmaximum; 150↔150 bleibt bei gültigen Inputs zulässig. |
| I30 | Legacy-Verträge und physische Buchung bleiben erhalten; keine doppelte Ein-/Ausbuchung durch neuen Lifecycle. |
| I31 | Bereits physisch versandte Trades sind von automatischer Verliererauswahl ausgeschlossen; Unterdeckung führt zum Problemflow. |
| I32 | Angenommener unversandter Vertrag bleibt vor offener reservierender V1-Anfrage geschützt, unabhängig vom Alter der Anfrage. |
| I33 | Innerhalb einer Stufe schützt der frühere unveränderliche bindende Zustandszeitpunkt; accepted nutzt Annahmezeit, open nutzt Reservationszeit. |
| I34 | Vollständiger Zeitgleichstand wird durch stabile kanonische Vorgangs-ID numerisch ASC entschieden; Queryreihenfolge ist irrelevant. |
| I35 | Verlierer werden vollständig beidseitig freigegeben, niemals teilweise geschrumpft; erneute Deckungsprüfung beendet weitere Auflösung, sobald alle relevanten Mengen gedeckt sind. |
| I36 | Neuer optimierter Plan und GO verdrängen niemals bestehende gültige Reservations; Retry verändert deren Bindungsalter nicht. |

## 34. Spezifikationsvalidierung und Scope

**AC34.** Die fünf nachgereichten PO-Entscheidungen schließen: exakte +2-Schwelle (AC11/12, Cases 4/6), zugesagte Eingänge (AC02), Rangänderung (AC20), Vor-/Nachversand-Unfulfillable (AC26) und ausschließliche V1-Quote (AC22). Die früheren Fragen Q1/Q2/Q3/Q5 sind damit nicht mehr offen. Ein Partner darf für ein anderes Restpaket erneut eligible sein, sofern sämtliche Invarianten gelten; kein zusätzliches Partnerverbot wird eingeführt.

Die finale PO-Entscheidung schließt zusätzlich Q4 durch AC26: Vertragsstufe, Bindungsalter und stabile ID bestimmen Schutz und Beendigung. 34 Spezifikationsabschnitte, 36 Invarianten und 27 Cases sind enthalten. Product Bible und IST-Audit bleiben in diesem Auftrag unverändert; ältere Statushinweise auf offene Fragen dokumentieren den früheren Stand, keine verbleibende Produktentscheidung. Die technische Umsetzung wird separat in der [Roadmap V1](SMARTDEAL_TECHNICAL_ROADMAP_V1.md) geplant. Keine Runtime-/UI-/Routen-/DB-/Schema-/Teständerung, keine Implementierung oder Testausführung und keine R5-Statusänderung durch diesen Dokumentationsauftrag.

## Open Product Questions

**Keine. Algorithm Contract V1 ist produktseitig vollständig geschlossen.** Q4 ist durch die finale PO-Regel in AC26 entschieden. Die dort ausgewiesene dauerhafte Zeit-/Identitätspersistenz ist eine technische Umsetzungsanforderung, keine offene Produktfrage. Keine Implementierung und insbesondere kein Beginn von SD-T1 durch diesen Abschluss.
