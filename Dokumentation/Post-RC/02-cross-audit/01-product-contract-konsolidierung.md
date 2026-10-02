# Cross-Audit-Konsolidierung – Closed-Beta Product Contract

**Stand:** 16. August 2026
**Status:** Cross-Audit-Konsolidierung der Product Audits 01–13 abgeschlossen; PO-01 bis PO-09 am 16. August 2026 entschieden; keine Implementierung, Migration, Test-, Refactoring- oder UI-Änderung
**Quellenrang:** Der [Product Contract Freeze](02-product-contract-freeze.md), die finalen PO-Entscheidungen und neuere Audits haben Vorrang vor widersprechenden Legacy-Spezifikationen.

## 1. Zweck und Leseregel

Dieses Dokument ist die gemeinsame Landkarte des Post-RC-Produktmodells. Es kopiert die Audits nicht, sondern ordnet Zuständigkeiten, echte Kollisionen, Legacy-Verträge, final entschiedene Product-Owner-Fragen, Datenrisiken und grobe Closed-Beta-Relevanz. Abschnitt 14 ersetzt seit dem Freeze die frühere Offenheit der Konflikte durch einen vollständigen Status.

Kennzeichnungen:

- **BESCHLOSSEN:** durch Audit 01–13 verbindlich festgelegt.
- **OFFEN:** historischer Kennzeichner aus der Analysephase; nach Abschnitt 14 besteht kein `STILL_OPEN`-Konflikt mehr.
- **LEGACY:** technischer oder historischer Bestand, nicht mehr das aktuelle Zielbild.
- **TECHNISCHER IST-ZUSTAND:** heute implementiertes Verhalten ohne Aussage, dass es Zielvertrag ist.
- **ENTSCHEIDUNG:** finaler Product-Owner-Vertrag gemäß Freeze.

## 2. Sammlr als Gesamtsystem

| Bereich | Primärer Zweck | Gehört hierhin | Gehört ausdrücklich nicht hierhin | Berührt |
|---|---|---|---|---|
| A. Sammlung / Meine Alben | digitales Regal und operative Übersicht eigener Alben | eigene Alben, Favorit, aktueller Fortschritt, Doppelte, Tauschpotenzial, Album hinzufügen | Feed, Tradehistorie, Community-News, abgeschlossene Deals | Album, Tauschen, Profil, Abschluss |
| B. Album / Stickerwand / Stickerliste | konkretes Album erleben, prüfen und pflegen; Stickerliste als digitaler Tauschzettel | Wand, Kapitel, Suche, aktuelle Mengen, Fehlende/Doppelte, lokale physische Tauschbuchung | allgemeiner Feed, globale Statistik, Tradehistorie, Profil-/Accountverwaltung | Inventory, Trophy, Statistik, Tauschen |
| C. SmartTrades / Tauschbörse | ausführbare Tauschmöglichkeiten automatisch erkennen und priorisieren | albumbezogene Matches, SmartTrade-Pakete, Partner, gegenseitig realisierbare Menge | Kleinanzeigenmarkt, abgeschlossene Trades, separater Lifecycle je Matchtyp | Inventory, Privacy, Profil, Anfragen |
| D. Tauschanfragen | konkreten Vorschlag senden, prüfen, annehmen oder ablehnen | unverändertes Paket, Fairness, Erfüllbarkeitsprüfung, Partnerprofil, Annahme/Ablehnung | Reservierung vor Annahme, heimliche Paketänderung, verpflichtender Ablehnungsgrund | SmartTrades, Glocke, Lifecycle |
| E. Laufende Trades / Lifecycle | angenommenen Deal sicher bis zum Ende abwickeln | Reservierung, Versand, Aus-/Einbuchung, Empfang, Problem, Abschluss, Bewertung, Historie | Matchsuche, Feed-Dashboard, abgeschlossene Deals in operativer Liste | Inventory, Glocke, Profil, Statistik |
| F. sammlr. Home / Feed | chronologische Erzählung der eigenen Sammlerwelt | ausgewählte eigene Ereignisse, Freundesereignisse, Sammlr News | Aufgaben-Dashboard, laufende Trades, Versand-/Empfangsaktionen, Notification-Inbox | Profil, Privacy, Trophy, Abschluss, SmartTrades |
| G. Glocke / Notifications | kleine persönliche Inbox für direkte Aufmerksamkeit | konkrete Anfrage, Versand, Bewertung, relevantes Problem, sichere Zielnavigation, ungelesenes Badge | Sammlerchronik, Newsfeed, Tradebearbeitung auf der Karte, ewiges Archiv | Tauschzentrale, Freunde, Feed |
| H. Profil / Community / Freunde | Sammleridentität, Vertrauen, Beziehungen und Sammlerzimmer | Username, optionaler Name, Bewertung, wenige Kernzahlen, Freunde, abgeschlossene Alben, Trophäen | Bestandsbearbeitung, vollständige fremde Statistik, Accountformulare, Tradeabwicklung | Privacy, Sammlung, Trophy, Statistik, Feed |
| I. Trophäen | kuratierte albumbezogene Erinnerung und Motivation | dauerhaft erreichte, vorab verborgene individuelle Album-Trophäen | globale Mengen-Achievements im kurzfristigen Modell, XP, Level, sichtbare Checkliste | Album, Profil, Statistik, Feed, Abschluss |
| J. Statistik | persönliche Karrierehistorie plus albumbezogener Zustand/Verlauf | Lebenszeitwerte, erfolgreiche Tradehistorie, aktuelle Albumwerte, spätere Entwicklung | zweite operative Sammlung, Rankings, globale aktuelle Fehlende/Doppelte | Inventory, Trade, Trophy, Profil, Abschluss |
| K. Albumabschluss / Abgeschlossene Alben | ersten vollständigen Zustand dauerhaft als Sammlermoment bewahren | Erstabschlussdatum, Abschluss-Trophy, Feed-Ereignis, reduzierte Abschlusskarte | operative Vitrinenmetriken, zweiter Abschluss desselben Exemplars, getrenntes totes Archiv | Sammlung, Profil, Statistik, Feed, Trophy, Löschung |
| L. Account / Einstellungen / Privacy | Zugang, persönliche Daten, Sicherheit und Konfiguration | Passwort, Logout, Kontolebenszyklus, Datenschutz, Privacy-Einstellungen | Sammleridentität, Vitrine, Sammlung, Community-Präsentation | Profil, Albumprivacy, Export, Security |

## 3. Cross-Audit-Konfliktmatrix

Quellenkürzel: `Axx` = Product Audit, `PB` = Product-Bible-Spezifikation, `Sxx` = Sprintvertrag. „PO“ und „Tech“ benennen noch nötige Entscheidungen, nicht die spätere Umsetzung.

| ID | Thema | Audits / Legacy | Technischer Ist-Zustand | Neuer Vertrag und genaue Kollision | PO | Tech | Beta | Risiko ohne Klärung |
|---|---|---|---|---|---|---|---|---|
| CA-001 | Grundrolle Home | A02, A09; PB Home, S25 | priorisierte Aufgaben und laufende Trades | A09 verlangt strikt chronologischen Sammlerfeed statt Aufgaben-Dashboard | NEIN | JA | P1 | mittlere Hauptwelt erzählt falsche Produktrolle |
| CA-002 | Neue Tauschanfrage | A06, A09, A10; S23–S25 | Tauschzentrale, Home-Aufgabe und Notification zeigen denselben Vorgang | operatives Zuhause ist Tauschen, Aufmerksamkeit Glocke; Home darf ihn nicht als Aufgabe duplizieren | NEIN | JA | P1 | dreifache Zuständigkeit und widersprüchlicher Erledigtzustand |
| CA-003 | Versand/Empfang | A07, A09, A10; S15–S25 | Deal, Glocke und Home-Aufgaben/-Tradecards überlappen | Aktion bleibt im Deal/Tauschen, Glocke weist gezielt hin, Home erzählt sie nicht operativ | NEIN | JA | P1 | Nutzer sieht denselben Handlungsbedarf mehrfach |
| CA-004 | Tradeproblem | A07, A09, A10; S17/S18/S25 | Problem wird im Deal und Home projiziert; typisierter Notification-Vertrag fehlt | Problem bleibt im Deal, relevante Aufmerksamkeit gehört in die Glocke | JA | JA | P1 | kritischer Problemzustand wird übersehen oder doppelt angezeigt |
| CA-005 | Laufende Trades auf Home | A06, A09; PB Home, S25 | bis zu drei laufende Trades dauerhaft auf Home | laufende Deals gehören in Tauschzentrale, nur konkrete Aufmerksamkeit in Glocke | NEIN | JA | P1 | Home bleibt zweites Trade-Dashboard |
| CA-006 | Bewertungsmöglichkeit | A07, A10; S28 | Bewertung erscheint am abgeschlossenen Deal/Archiv, keine Notification | genau eine Bewertungsmöglichkeit soll eine Glockenmeldung erzeugen | NEIN | JA | P1 | gewünschte Bewertung wird schwer auffindbar |
| CA-007 | SmartMatch im Feed | A06, A09; S20–S22 | nicht ausführbare Smartpakete können Home-Aufgabe sein; kein Feed | SmartMatch kann Entdeckung sein, genaue Feed-Aufnahme ist offen; nie operative Home-Aufgabe | JA | JA | P2 | Feed und Tauschen konkurrieren um Discovery |
| CA-008 | Profil und Account | A08; S26, aktuelle Profilroute | Konto-, Passwort-, Logout- und Löschfunktionen liegen im Profilpanel | Profil ist Sammleridentität; Account/Einstellungen sind getrennte Welt | NEIN | JA | P1 | Identitätsseite bleibt technische Kontoverwaltung |
| CA-009 | Profil und operative Sammlung | A03, A08, A12; S26 | aktive Alben und Doppelte sind prominent; vier feste Kennzahlen | Sammlung besitzt operative Alben; Profil zeigt wenige repräsentative Kernwerte | JA | JA | P1 | Profil wird zweites Bestandsdashboard |
| CA-010 | Profil- vs Albumprivacy | A08, A09, A11–A13; S27 | nur `public/friends/private` je Album plus Tradepool-Schalter; kein globales Profil-Gate | neues Modell verlangt verständliches öffentlich/privat für Profil; Zusammenspiel ungeklärt | JA | JA | P1 | indirekte Datenlecks oder unerwartet unsichtbare Inhalte |
| CA-011 | Fremde Abschlussgeschichte | A08, A13; S26/S27 | fremde Vitrine folgt sichtbaren, aktuell vollständigen Alben | historische Abschlüsse dürfen nur bei öffentlichem Profil privacy-sicher erscheinen | JA | JA | P1 | privater Abschluss wird offengelegt oder öffentlicher verschwindet |
| CA-012 | Globale Trophäen | A11, A12; aktuelle Definitionen | globale Sticker-, Doppelten- und Trade-Schwellen unter `__global__` | kurzfristiger Vertrag kennt nur individuelle Album-Trophäen | NEIN | JA | P1 | falsche Trophy-Zahlen und widersprüchliche Motivation |
| CA-013 | Generischer Trophy-Katalog | A11; aktuelle Fallback-Definitionen | jedes nicht kuratierte Album erhält generische Prozent-/Mengen-Ziele | jedes Album benötigt eigenen kuratierten Kosmos | NEIN | JA | P2 | neue Alben erben ungewollte Standardziele |
| CA-014 | Trophy-Wahrheit | A11–A13 | Unlock wird gespeichert, Ansichten berechnen Erreichen teilweise neu aus aktuellem Bestand | persistierte Freischaltung ist dauerhafte Wahrheit | NEIN | JA | P1 | erreichte Trophy verschwindet bei Bestandsrückgang |
| CA-015 | Verborgene Ziele | A11; Album, Statistik, Trophy-Schrank | „nächstes Ziel“, Fortschritt, Locked-/Secret-Elemente sichtbar | unerreichte Trophäen bleiben verborgen | NEIN | JA | P1 | Entdeckungsprinzip wird aufgehoben |
| CA-016 | Trophy-Zählung | A08, A11, A12; S26 | Profil zählt alle persistierten Zeilen, Statistik dynamisch inklusive global | nur gültige albumbezogene Trophäen zählen | NEIN | JA | P1 | Profil und Statistik nennen verschiedene/falsche Zahlen |
| CA-017 | „Sticker gesammelt“ | A12; aktuelle Statistik | Summe des momentanen `quantity` heißt „gesammelt“ und kann sinken | nicht sinkender Lebenszeitwert ist historische Karrierekennzahl | NEIN | JA | P2 | scheinbare Karriere schrumpft durch normale Abgabe |
| CA-018 | Globale Fehlende/Doppelte | A08, A12; aktuelle Statistik/S26 | globale Missing-/Doppeltenwerte in Statistik und Profil | operative Werte gehören zum Album/Bestand, nicht zur Karriere/Identität | NEIN | JA | P1 | neue Alben verschlechtern scheinbar die Karriere |
| CA-019 | Trade-Statistik | A07, A12; aktuelle Statistik/Profil | beide Pakete werden addiert; Erfolg wird je Route unterschiedlich geprüft | erhalten/abgegeben trennen und exakt regulär erfolgreiche Deals zählen | NEIN | JA | P1 | falsche Lebenszeitwerte und inkonsistente Erfolgszahlen |
| CA-020 | Albumabschluss/Vitrine | A04, A08, A12, A13; S26 | Abschluss ist überall aktuelles `collected >= total` | Erstabschluss ist dauerhaftes historisches Ereignis | JA für Backfill | JA | P1 | frühere Vollendung verschwindet; Datum fehlt |
| CA-021 | Löschung und Abschlusszählung | A12, A13 | kein Einzelalbum-Löschpfad | A12: gelöscht zählt nicht; A13: historischer Abschluss kann erhalten bleiben; Aggregat offen | JA | JA | P2 | Karte und Statistik widersprechen einander |
| CA-022 | Klickziel bewahrter Abschluss | A13 | kein Zustand „Album gelöscht, Geschichte erhalten“ | Abschlusskarte ist klickbar, besitzt nach Löschung aber kein normales Albumziel | JA | JA | P2 | toter Link oder unbeabsichtigte Bestandswiederherstellung |
| CA-023 | Albumtyp vs Exemplar | A04, A13; PB Collection | `user_id + album_id` prägt Zuordnung, Inventory, Trophy, Privacy, Profil und URLs | künftiger Abschluss gehört zu konkretem Exemplar | NEIN | JA | P3 | Mehrfachexemplare werden strukturell verbaut |
| CA-024 | Albumübergreifende SmartTrades | A06, A07; PB Trading, S20–S22 | positionsfähiges Lifecycle-Schema, aber Request/UI an eine `album_id` gebunden | notwendiger fachlicher Bereich, Beta-Priorität und End-to-End-Scope offen | JA | JA | P2/P3 | Teilfunktion wird als fertiger Kernnutzen missverstanden |
| CA-025 | Match-Priorisierung | A06; S20/S21 | globale Partnerübersicht priorisiert eigene Fehlende beim Partner | größtmögliche gegenseitig realisierbare Menge zuerst | NEIN | JA | P1 | vermeintlich beste Matches sind nicht ausführbar optimal |
| CA-026 | Paketverkleinerung | A06/A07; PB Trading/Lifecycle, S22 | S22 schützt unveränderte Pakete; ältere Spezifikation erlaubt Verkleinerung | ursprüngliche nicht erfüllbare Anfrage bleibt sichtbar und blockiert; keine heimliche Änderung | NEIN | JA | P1 | Zustimmung gilt plötzlich für anderes Paket |
| CA-027 | Bestandsbuchungszeitpunkt | A07; verkürzte PB-Trading-Matrix | Lifecycle bucht ausgehend beim Versand, eingehend beim eigenen Empfang | detaillierter neue Vertrag bestätigt diese Trennung | NEIN | NEIN | P1 Dokumentation | spätere Arbeit könnte wieder beim Gesamtabschluss doppelt buchen |
| CA-028 | Bewertungszeitpunkt | A07; älteres Trading-Protokoll, S28 | S28 erlaubt Bewertung nach qualifiziertem Abschluss | Legacy erlaubt bereits nach beidseitigem Versand | NEIN | NEIN | P1 Dokumentation | Bewertung vor tatsächlicher Abwicklung |
| CA-029 | Nicht gewünschte Notifications | A10; S23/S29/Legacy | `trade_accepted`, `trade_received`, `friend_accepted` und Abschluss-Hinweise werden erzeugt | Annahme, Empfang, regulärer Abschluss, eigene Aktionen und Freundesannahme erzeugen keine Glockenmeldung | NEIN | JA | P1 | Inbox wird laut und dupliziert Dealstatus |
| CA-030 | Routine-Reminder | A10; S23/S24 | Versand-/Empfangsreminder werden lazy erzeugt | Closed Beta startet ohne Routine-Erinnerungsserien | NEIN | JA | P1 | ruhige Inbox wird wieder Aufgabenmotor |
| CA-031 | Notification Read-State | A10; S24 | Öffnen der Liste liest nichts; einzelne POST-Buttons lesen genau eine Karte | sichtbare Einträge gelten beim Öffnen als gelesen; manuelle Read-Buttons entfallen | NEIN | JA | P1 | Badge bleibt trotz gelesener Inbox stehen |
| CA-032 | Notification-Retention | A10; S24 | unbegrenzte, paginierte Historie | gelesene Meldungen höchstens 30 Tage sichtbar | NEIN | JA | P2 | Glocke wird ewiges fachfremdes Archiv |
| CA-033 | Home-/Sammlr-Zentrale-Begriff | A02, A05, A09; PB Home/Collection | aktuelle Navigation nutzt `sammlr.` für Home und Sammlung separat; ältere Texte anders | Zielwelt ist Sammlung / sammlr. / Tauschen | NEIN | JA | P1 | Navigation und Dokumentation sprechen von verschiedenen Orten |
| CA-034 | Feed-Historie | A09, A13; S25/S29 | kein Feed-Eventstore; `user_activity` ist nur letzter Aktivitätszeitpunkt | chronologischer Feed benötigt reale, privacy-geprüfte Ereignisse | JA für MVP-Scope | JA | P1 | Feed müsste Ereignisse aus aktuellem Zustand erfinden |
| CA-035 | Completion-Orchestrierung | A11–A13 | Trophy-Erkennung verteilt über Routen/Trade-Callbacks; kein Abschluss-/Feedobjekt | Abschluss, Trophy und Feed müssen genau einmal aus demselben Moment entstehen | NEIN | JA | P1 | Doppelereignisse, fehlende Events oder abweichende Zeiten |
| CA-036 | Vollständige Alben in „Meine Alben“ | A04, A13; aktuelle Sammlung | vollständige Alben verlassen „Aktive Alben“ und stehen nur in Vitrine | sie bleiben regulär in der Sammlung und erscheinen zusätzlich historisch | NEIN | JA | P1 | vollständiges Album wirkt archiviert statt benutzbar |
| CA-037 | Abschlusskarte | A13; aktuelle `album_card` | Vitrine zeigt Fortschritt, Doppelte, Missing/Marktwerte | historische Karte zeigt Identität, Status und Erstabschlussdatum | NEIN | JA | P1 | Sammlergeschichte bleibt operatives Dashboard |

**Ergebnis:** 37 eigenständige Cross-Audit-Konflikte beziehungsweise konkrete Ist-/Zielkollisionen. Die noch offenen Produktanteile bündeln sich in neun echte Product-Owner-Entscheidungen; die übrigen Kollisionen sind fachlich entschieden oder rein technisch/dokumentarisch zu konsolidieren.

## 4. Vertiefung zentraler Bereichsgrenzen

### 4.1 Home, Glocke und Tauschzentrale

| Information/Aktion | Heute | Beschlossener Eigentümer |
|---|---|---|
| neue Tauschanfrage | Home-Aufgabe, Glocke, Tauschen | Glocke weist hin; Tauschen bearbeitet |
| Anfrage annehmen/ablehnen | Tauschen/Deal, teils Home-Link | Tauschen/konkrete Anfrage |
| laufender Trade | Home-Karte und Tauschen | Tauschen |
| eigener Versand | Deal, Home-Aufgabe, Glocke/Reminder | Glocke weist bei relevantem Ereignis hin; Deal führt Aktion aus |
| eigener Empfang | Deal, Home-Aufgabe, Glocke/Reminder | Glocke weist bei relevantem Ereignis hin; Deal führt Aktion aus |
| Problemzustand | Deal und Home; Notification unvollständig | Deal bearbeitet; Glocke informiert bei direkter Relevanz |
| Bewertungsmöglichkeit | Deal/Archiv, keine Glocke | einmalige Glockenmeldung → abgeschlossener Deal |
| SmartMatch | Tauschen; nicht ausführbarer Zustand als Home-Aufgabe möglich | Tauschen; mögliche Feed-Entdeckung ist PO-offen |
| Albumabschluss/Trophy | Popup; kein Feed | unmittelbarer Moment plus Feed; keine Glocke |

### 4.2 Profil, Account und Sammlung

- **Profil:** Identität, Vertrauen, Freunde, abgeschlossene Alben, Trophäen und wenige repräsentative Zahlen.
- **Account:** Zugang, Passwort, Logout, Datenschutz, Kontolebenszyklus und Privacy-Konfiguration.
- **Sammlung:** eigene Alben, aktueller Bestand, Fortschritt, Doppelte und Albumverwaltung.

Die aktuelle Profilseite vermischt alle drei Ebenen. Die spätere Trennung darf bestehende sichere Accountfunktionen nicht entfernen, aber ihr fachliches Zuhause ändern.

### 4.3 Trophäen, Statistik und Feed

- **Trophy:** kuratierter, dauerhaft erreichter Album-Moment.
- **Statistik:** aggregierte historische Karriere oder aktueller Zustand eines konkreten Albums.
- **Feed:** ausgewählte erzählenswerte Ereignisse, nicht jede Trophy und nicht jeder Statistikwert.

Albumabschluss ist der klare Schnittpunkt: genau ein historischer Abschluss, genau eine Abschluss-Trophy, genau ein Feed-Ereignis, keine Notification. Andere Trophy-Feedregeln sind noch nicht vollständig beschlossen.

## 5. Current State gegenüber historischer Sammlergeschichte

| Fachwert | CURRENT STATE | HISTORICAL EVENT / LIFETIME VALUE | Heutige Verwechslung |
|---|---|---|---|
| Stickerbestand | momentane `quantity` je Code | alle jemals erhaltenen/gesammelten Einheiten | Statistik nennt Current State „gesammelt“ |
| Fehlende | aktueller Albumumfang minus aktuelle Sammlung | keine Karrierekennzahl | global in Statistik dargestellt |
| Doppelte | aktuelle überschüssige Einheiten | keine Karriere-/Profilkernzahl | global in Statistik/Profil dargestellt |
| Album vollständig | heute jeder Sticker vorhanden | Exemplar war erstmals vollständig, mit Zeitpunkt | Sammlung, Profil und Statistik verwenden nur Current State |
| Vitrine | heute aktuell 100 Prozent | historische „Abgeschlossene Alben“ | dynamische Vitrine verliert frühere Abschlüsse |
| Trophy | Bedingung heute erfüllt | einmal dauerhaft freigeschaltet | viele Reads rechnen dynamisch neu |
| Trades | offener/aktueller Lifecycle | regulär erfolgreicher abgeschlossener Deal mit Positionen | Statistik prüft Erfolg zu schwach und mischt Richtungen |
| Albumfortschritt | heutiges `x / total` | Verlaufspunkte über Zeit | keine persistierten Snapshots/Ereignisse |
| Albumstart | aktuelle Zuordnung vorhanden | Zeitpunkt des Beginns | `user_albums` besitzt keinen Zeitstempel |

## 6. Albumtyp gegenüber Albumexemplar

| Bereich | Heute typbezogen | Auswirkung des späteren Exemplarvertrags |
|---|---|---|
| `user_albums` | eindeutig je `user_id + album_id` | mehrere Zuordnungen desselben Typs derzeit blockiert |
| Inventory | `user_id + album_id + sticker_code` | Bestand kann keinem einzelnen Exemplar zugeordnet werden |
| Trophy | `user_id + album_id + trophy_name` | zwei Exemplare können keine zwei Abschluss-Trophäen besitzen |
| Statistik | Aggregation nach Nutzer/Albumtyp | Start, Dauer, Verlauf und Abschluss je Exemplar fehlen |
| Trades | Legacy-Request besitzt eine `album_id`; Positionen ebenfalls Albumtyp | gemeinsamer Pool denkbar, Herkunft aus Exemplar ungeklärt |
| Profil | DTO und URLs verwenden Albumtyp | zwei identische Typen nicht getrennt darstellbar |
| Albumabschluss | kein Abschlussobjekt | Erstabschluss kann nur typbezogen angedeutet werden |
| URLs | `/album/<album_id>` | kein stabiler Deep Link zu einem konkreten Exemplar |
| Privacy | Einstellung pro Nutzer/Albumtyp | unterschiedliche Exemplare können nicht verschieden sichtbar sein |

Dies ist P3 und kein Closed-Beta-Umbau. Gegenwärtige historische Entscheidungen dürfen jedoch nicht behaupten, die heutige `album_id` sei bereits eine Exemplaridentität.

## 7. Trade-Lifecycle End-to-End

| Schritt | Beschlossener Vertrag | Ist-/Legacy-Befund |
|---|---|---|
| SmartMatch | konfliktfrei, tatsächlich ausführbar, größtmögliche gegenseitige Menge priorisieren | Kernservices vorhanden; globale Sortierung und Cross-Album-End-to-End lückenhaft |
| Anfrage | unverändertes Paket; manuell darf Nutzer mehr geben, nie mehr verlangen | Fairness und Smart-Paketprüfung vorhanden |
| Annahme | Erfüllbarkeit erneut prüfen; nicht erfüllbare Anfrage sichtbar blockieren | atomare Prüfung/Reservierung vorhanden; Legacy-Spezifikation zur Verkleinerung kollidiert |
| Reservierung | erst bei Annahme, noch keine physische Buchung | vorhanden |
| Versand | jede Seite bestätigt selbst | vorhanden |
| Ausbuchung | eigener Versand bucht eigene Abgabe genau einmal aus | neuer Lifecycle entspricht Vertrag; verkürzte Legacy-Aussage missverständlich |
| Empfang | eigene tatsächliche erhaltene Menge bestätigen | vorhanden einschließlich Teilempfang/Problem |
| Einbuchung | eigener Empfang bucht erhaltene Positionen genau einmal ein | vorhanden |
| Abschluss | beide Empfangsseiten vollständig, kein offener Problemrest | Lifecycle vorhanden; Legacy-Completed bleibt kompatibel, besitzt aber weniger Historie |
| Bewertung | erst nach qualifiziertem Abschluss | S28 entspricht; älteres Protokoll „nach Versand“ ist Legacy |
| Historie | regulär erfolgreiche Deals getrennt von operativen Vorgängen | Archiv vorhanden; Statistikprojektionen sind noch inkonsistent |
| Notifications/Feed | nur direkte Aufmerksamkeit in Glocke; Tradearbeit im Deal; keine operative Home-Dopplung | heutige Typen/Home widersprechen teilweise; Tradefeed ist nicht beschlossen |

## 8. Legacy-Verträge und voraussichtlich entfallende Produktlogik

| Legacy-/Bestandslogik | Heutiger Zustand | Neuer Status |
|---|---|---|
| „Das braucht dich“ und Prioritätsnummern auf Home | S25 aktiv | **ERSETZT** durch chronologischen Feed |
| dauerhafte laufende Trades auf Home | S25 aktiv | **ENTFÄLLT** auf Home; bleibt in Tauschen |
| operative Versand-/Empfangs-/Problemkarten auf Home | aktiv | **ENTFÄLLT** auf Home; Glocke/Deal übernehmen |
| globale Sticker-Trophäen | definiert und teilweise persistiert | **VERTAGT** |
| globale Doppelten-Trophäen | definiert und teilweise persistiert | **VERTAGT** |
| globale Trade-Trophäen | definiert und teilweise persistiert | **VERTAGT** |
| generischer Trophy-Fallback je Album | aktiv | **ERSETZT** durch individuelle Kataloge |
| dynamische Trophy-Anzeige | aktive Reads | **ERSETZT** durch persistierte Freischaltungswahrheit |
| nächste/Locked-/Secret-Trophy-Ziele | mehrere Renderer | **ENTFÄLLT** im aktuellen Trophy-Vertrag |
| Doppelte als zentrale Profilkennzahl | S26 aktiv | **ENTFÄLLT** als zentrale dauerhafte Profilzahl |
| aktuelle Menge als Karriere-„gesammelt“ | Statistik aktiv | **ERSETZT** durch historischen Lebenszeitwert; Current State bleibt albumbezogen |
| globale Missing-/Doppelten-Statistik | aktiv | **ENTFÄLLT** aus Gesamtstatistik |
| dynamische „Vitrine“ aus aktuellem 100 Prozent | Sammlung/Profil aktiv | **ERSETZT** durch historische „Abgeschlossene Alben“; Designmetapher vertagt |
| operative Vitrinenmetriken | normale Albumkarte aktiv | **ENTFÄLLT** auf Abschlusskarte |
| automatische Paketverkleinerung | ältere Spezifikation, nicht S22-Ziel | **ENTFÄLLT** für ursprüngliche Anfrage |
| Bewertung nach beidseitigem Versand | älteres Protokoll | **ERSETZT** durch qualifizierten Abschluss |
| `trade_accepted`, `trade_received`, `friend_accepted` in Glocke | aktiv | **ENTFÄLLT** nach neuem Katalog |
| reguläre Tradeabschluss-Notification | Legacy aktiv | **ENTFÄLLT** |
| Routine-Versand-/Empfangsreminder | aktiv | **VERTAGT** nach Closed-Beta-Erfahrung |
| unbegrenzte Notification-History | aktiv | **ERSETZT** durch höchstens 30 Tage für gelesene Meldungen |
| einzelne „Als gelesen markieren“-Buttons | aktiv | **ENTFÄLLT** nach neuem Read-Vertrag |
| „Vitrine“ als zwingender funktionaler Name | aktiv | **ERSETZT** durch „Abgeschlossene Alben“; als Gestaltungsidee vertagt |

## 9. Final entschiedene Product-Owner-Fragen

Die Optionen bleiben als Entscheidungsnachweis erhalten. Verbindlich sind die jeweils als **ENTSCHEIDUNG** markierten Ergebnisse und das normative Freeze-Dokument.

### PO-01 – Verhältnis Profilprivacy zu Albumprivacy

**Frage:** Wie wirken `Profil öffentlich/privat` und S27 `public/friends/private` je Album zusammen?

- **Option A:** Profilprivacy ist äußeres Gate; bei öffentlichem Profil begrenzt zusätzlich jede Albumfreigabe. Präzise, aber zwei Ebenen bleiben.
- **Option B:** Einfaches Profil-Gate ersetzt die Sichtbarkeitsstufen für Profildarstellung; S27 bleibt nur für Tradepool/interne Freigaben. Einfacher, aber bestehende differenzierte Freigaben verlieren Bedeutung.
- **Option C:** Kein globales Gate; S27 bleibt alleinige Sichtbarkeitsquelle. Technisch nah am Ist, widerspricht aber der gewünschten einfachen privaten Profilwelt.

**Warum jetzt:** Feed, fremde Profile, Trophäen und abgeschlossene Alben benötigen dieselbe Leak-sichere Regel.
**ENTSCHEIDUNG:** Option A.

### PO-02 – Minimaler Feedumfang der Closed Beta

**Frage:** Welche der drei beschlossenen Feedquellen müssen bereits in der Closed Beta tatsächlich enthalten sein?

- **Option A:** zunächst nur eigene Sammlerreise.
- **Option B:** eigene Reise plus privacy-geprüfte Freundesereignisse.
- **Option C:** eigene Reise, Freundesereignisse und redaktionelle Sammlr News.

**Warum jetzt:** Ereignisspeicherung, Privacy und Home-Ablösung hängen vom Mindestumfang ab.
**ENTSCHEIDUNG:** Option C; Sammlr News bleiben zurückhaltend und dürfen den Feed nicht dominieren.

### PO-03 – SmartMatches im Feed

**Frage:** Sind neue ausführbare SmartMatches bereits Closed-Beta-Feedereignisse?

- **Option A:** nein, ausschließlich Entdeckung in Tauschen.
- **Option B:** ja, aber nur seltene/qualifizierte TopMatches nach später klarer Schwelle.
- **Option C:** ja, jedes neu berechnete Match.

**Warum jetzt:** Sonst drohen doppelte Discovery, Ereignisflut und unklare Deduplizierung.
**ENTSCHEIDUNG:** Option A.

### PO-04 – Albumübergreifende SmartTrades in der Closed Beta

**Frage:** Muss der albumübergreifende Pfad bereits End-to-End Teil der Closed Beta sein?

- **Option A:** ja, gleichrangiger Kernpfad neben albumbezogenen SmartTrades.
- **Option B:** Closed Beta startet mit vollständigem albumbezogenem SmartTrade; Cross-Album bleibt sichtbar als späterer Ausbau.
- **Option C:** beide SmartTrade-Arten werden bis nach der Beta zurückgestellt; nur manuelle/albumbezogene Partner bleiben.

**Warum jetzt:** Requestmodell, UI, Positionsbezug und Testscope unterscheiden sich erheblich.
**ENTSCHEIDUNG:** Option B.

### PO-05 – Statistikzählung eines bewahrten Abschlusses

**Frage:** Zählt ein historischer Abschluss weiter bei `Alben abgeschlossen`, wenn das aktive Album gelöscht, die Abschlussgeschichte aber bewusst bewahrt wurde?

- **Option A:** ja; die Zahl beschreibt historische Karriere.
- **Option B:** nein; Audit-12-Regel „gelöscht bedeutet raus“ gilt auch für das Aggregat.
- **Option C:** zwei getrennte Zahlen für aktive abgeschlossene und historisch bewahrte Alben.

**Warum jetzt:** Audit 12 und 13 lassen hier zwei gültige, aber widersprüchliche Lesarten.
**ENTSCHEIDUNG:** Option A mit expliziter Löschwahl: Bewahren zählt weiter, Mitlöschen entfernt Geschichte und Zählung.

### PO-06 – Klickziel nach Albumlöschung

**Frage:** Was öffnet eine bewusst bewahrte Abschlusskarte ohne aktives Album?

- **Option A:** eine historische read-only Abschlussansicht.
- **Option B:** die Karte ist nicht anklickbar und zeigt nur Identität/Datum.
- **Option C:** bewahrte Geschichte ist nicht zulässig, wenn das aktive Album vollständig gelöscht wird.

**Warum jetzt:** Audit 13 verlangt grundsätzlich anklickbare Karten, erlaubt aber bewahrte Geschichte nach Löschung.
**ENTSCHEIDUNG:** Option B für die Closed Beta.

### PO-07 – Anerkennung bestehender Albumabschlüsse

**Frage:** Welche vorhandenen Daten dürfen bei Einführung des historischen Abschlusses als Altabschluss anerkannt werden?

- **Option A:** nur eindeutig passende persistierte Abschluss-Trophy mit ihrem vorhandenen Zeitpunkt.
- **Option B:** zusätzlich aktuell vollständige Alben mit Cutover-Zeitpunkt, klar als technisch übernommener Zeitpunkt.
- **Option C:** kein automatischer Backfill; Historie beginnt ab Einführung.

**Warum jetzt:** Ohne Datenregel würden bestehende Nutzer Geschichte verlieren oder scheinpräzise falsche Daten erhalten.
**ENTSCHEIDUNG:** Option A; Katalogvalidierung ist vor jedem Backfill Pflicht.

### PO-08 – Öffentliche Profil-Kernzahlen

**Frage:** Welche reduzierte Kennzahlenmenge zeigt ein fremdes öffentliches Profil in der Closed Beta?

- **Option A:** Bewertung und erfolgreiche Trades.
- **Option B:** zusätzlich abgeschlossene Alben und gültige Album-Trophäen.
- **Option C:** zusätzlich unterschiedliche Tauschpartner.

**Warum jetzt:** S26 zeigt vier andere feste Werte; Privacy, Profilhierarchie und Statistikprojektion benötigen eine verbindliche Auswahl.
**ENTSCHEIDUNG:** Option B.

### PO-09 – Welche Tradeprobleme erzeugen Glockenaufmerksamkeit?

**Frage:** Welche Problemänderungen sind „relevant“ im Sinne von Audit 10?

- **Option A:** nur neu entstandene Zustände, die eine konkrete Aktion des Empfängers verlangen.
- **Option B:** jede Problemöffnung, Auflösung und terminale Änderung für beide Seiten.
- **Option C:** nur Problemöffnung und terminaler Ausgang, keine Zwischenschritte.

**Warum jetzt:** Ein fehlender Hinweis kann den Kernworkflow blockieren; zu viele Hinweise widersprechen der kleinen Inbox.
**ENTSCHEIDUNG:** Option A, ergänzt um genau einen terminalen Hinweis, wenn sich die eigene nächste Aktion, Durchführbarkeit, Bewertung oder Abschlussmöglichkeit relevant verändert.

## 10. Closed-Beta-Relevanz

Die Einordnung beschreibt die groben Themenpakete der Analysephase, keine fertigen Sprints. Seit dem Freeze wird sie durch die technisch geschnittenen `P0 0 / P1 17 / P2 9 / P3 3`-Arbeitspakete im [Closed-Beta-Bauplan](../03-closed-beta-build-plan.md) operationalisiert; unterschiedliche Zahlen bedeuten daher keine Scope-Erweiterung.

### P0 – vor Closed Beta zwingend: 0 Themen

Die Audits belegen keinen neuen ungeklärten Security-, Datenintegritäts- oder Bestandsbuchungsfehler, der den vorhandenen Kernworkflow aktuell unbenutzbar macht. Bestehende technische Release-Gates bleiben davon unberührt.

### P1 – Closed Beta sollte es haben: 12 Themen

1. eindeutige Zuständigkeit Home/Glocke/Tauschzentrale,
2. minimaler chronologischer Feed nach PO-02,
3. bereinigter Notification-Typkatalog einschließlich Bewertung/Problem,
4. Read-State und kleine Inbox-Semantik,
5. Profil-/Account-/Sammlungsgrenze,
6. konsolidierte Privacy-Regel nach PO-01,
7. persistente Trophy-Reads und gültige albumbezogene Zählung,
8. minimaler historischer Albumabschluss mit genau-einmal-Konsistenz,
9. historische Projektion „Abgeschlossene Alben“ ohne operative Metriken,
10. korrekte Statistikbegriffe und gerichtete erfolgreiche Tradewerte,
11. gegenseitig realisierbare Match-Priorisierung,
12. einheitliche Erfolgsprojektion für Tradehistorie, Profil und Statistik.

### P2 – nach beziehungsweise kontrolliert um die Closed Beta: 11 Themen

1. vollständiger Feed-Ausbau um Freunde/News über den gewählten MVP hinaus,
2. erweiterter Feed-Ereigniskatalog, Retention und Gruppierung,
3. Lebenszeit-Historisierung `Sticker gesammelt`,
4. Albumstart, Sammeldauer und Fortschrittsverlauf,
5. Einzelalbum-Löschworkflow mit Historienwahl,
6. kontrollierter Abschluss-Backfill nach PO-07,
7. endgültige öffentliche Profil-Kernzahlen nach PO-08,
8. vollständig kuratierte Trophy-Kataloge für alle unterstützten Alben,
9. albumübergreifender SmartTrade-End-to-End-Pfad, falls PO-04 ihn vertagt,
10. Offline-Fähigkeit der Stickerliste,
11. Share-/Exportdarstellungen der Stickerliste.

### P3 – Zukunft: 3 Themen

1. echte Mehrfachexemplare mit exemplarbezogenem Inventory und Abschluss,
2. Push-Zustellung auf Basis des konsolidierten Notification-Vertrags,
3. weitergehende SmartTrade-Strategien, regionale Signale und vertiefte Reputationsmodelle.

## 11. Abhängigkeitsmatrix

| Voraussetzung | Nachgelagerte Bereiche | Warum zuerst |
|---|---|---|
| PO-01 Privacyvertrag | fremde Profile, Freundesfeed, Trophäen, abgeschlossene Alben | verhindert indirekte Leaks und doppelte Sichtbarkeitslogik |
| Feed-MVP PO-02/PO-03 | Home, Eventpersistenz, Privacy, Retention | bestimmt, welche Ereignisse überhaupt historisiert werden müssen |
| Notification-Katalog PO-09 | Glocke, Home-Ablösung, Trade-Lifecycle | Eigentümer und Empfänger müssen vor UI-/Read-Umbau feststehen |
| historische Abschlusswahrheit | Abschluss-Trophy, Feed, Statistik, Profilbereich | alle benötigen dieselbe Exemplar-/Zeitwahrheit und Deduplizierung |
| Trophy-Identität/Kataloggültigkeit | Trophy-Read, Profilzahl, Statistik, Abschluss-Backfill | verhindert globale/Legacy-Verzerrung |
| einheitliche Trade-Erfolgsprojektion | Profil, Statistik, Partnerzahl, größter Trade | dieselben Deals dürfen nicht je Oberfläche anders zählen |
| aktuelle vs historische Statistiksemantik | Statistikseite, Profilkernzahlen, Feed-Rückblicke | verhindert Backfill aus momentanen Beständen |
| PO-04 Cross-Album-Scope | SmartTrade-UI, Requestmodell, Tradepositionen | bestimmt, ob ein oder mehrere Alben End-to-End transportiert werden |
| Löschvertrag PO-05/PO-06 | Album, Abschlussgeschichte, Statistik, Trophy, Feed | aktive Daten und Historie dürfen nicht unbeabsichtigt gemeinsam verschwinden |
| spätere Exemplaridentität | Inventory, URLs, Privacy, Trophy, Abschluss | muss vor echten Mehrfachexemplaren bereichsübergreifend gelten |

## 12. Datenrisiken

### A – sicher weiterverwendbar

- aktuelle Inventory-Mengen als **aktueller Zustand**, nicht als Historie,
- gerichtete Legacy-Tradepakete für Mengen und Partner,
- Lifecycle-Trades, Positionen, Versand, Empfang, Probleme und Abschlusszeitpunkte,
- Freundschaften und Blocks als gegenseitige Communitybeziehungen,
- Albumkataloge und aktuelle Albumzuordnungen als gegenwärtige Mitgliedschaft,
- gültige typisierte Notification-Ziele und Read-States als technische Bestandsdaten.

### B – transformierbar

- Trophy-Zeilen, wenn Scope, Album und Name einem gültigen Katalog eindeutig zugeordnet werden,
- typisierte Notifications in einen bereinigten Katalog/Retention-Vertrag,
- aktuelle `user_albums`-Zuordnungen als Ausgangspunkt einer späteren Exemplarstrategie, nicht als vergangene Instanzen,
- aktuell vollständige Alben als Current-State-Ausgangslage, sofern der Cutover ausdrücklich gekennzeichnet wird,
- Legacy-Completed-Trades für Anzahl/Richtungsmengen trotz fehlendem Abschlusszeitpunkt.

### C – historisch unvollständig

- Lebenszeitwert aller gesammelten Sticker,
- Album-Startzeiten,
- Erstabschlusszeiten ohne belastbare Abschluss-Trophy,
- vergangene Fortschrittskurven und nicht tradebezogene Bestandsbewegungen,
- historische Feed-Ereignisse,
- Abschlusszeitpunkte reiner Legacy-Trades.

### D – potenziell inkonsistent

- dynamischer Vitrinenstatus gegenüber persistierter Abschluss-Trophy,
- Trophy-Zahl in Profil gegenüber dynamischer Statistik/Schrank,
- `trade_requests.status='completed'` gegenüber Lifecycle-Problemendzuständen,
- Legacy- und typisierte Notifications nebeneinander,
- globale/Legacy-Trophy-Namen gegenüber aktuellem Katalog,
- Albumzuordnung/Inventory bei einer hypothetischen Teil-Löschung.

Der lokale `em24`-Fall ist der konkrete Nachweis: Abschluss-Trophy vom `2026-07-01 15:57:30`, aktueller Bestand nur `709 / 728`. Weder darf die Trophy gelöscht noch darf der heutige Bestand als Beweis gegen den historischen Moment verwendet werden; zugleich ist der Trophy-Zeitpunkt erst nach Validierung als kanonischer Erstabschluss nutzbar.

### E – niemals automatisch interpretieren oder backfillen

- aktuellen Inventory-Bestand als Lebenszeitsumme,
- aktuelle 100 Prozent als unbekanntes historisches Abschlussdatum,
- `user_albums.id` als Startzeit oder bereits stabile Exemplarhistorie,
- Trophy-`unlocked_at` pauschal als garantiert ersten Albumabschluss ohne Katalog-/Pfadprüfung,
- Notification-Zeitpunkte als Feed-Historie,
- `trade_requests.created_at` als Abschlusszeit eines Legacy-Trades,
- fehlende vergangene Zwischenstände als künstliche Fortschrittskurve,
- gelöschte oder nicht vorhandene Albumzuordnungen als Beleg, dass nie ein Album existierte.

## 13. Definition des Closed-Beta-Produkts

**Sammlr Closed Beta ist eine mobile Anwendung, mit der Sammler ihre Stickeralben als aktuellen Bestand pflegen, fehlende und doppelte Sticker erkennen, reale Tauschsituationen dokumentieren und über vorhandene Communitybestände sinnvolle Online-Tauschmöglichkeiten finden können.**

Die Navigation bildet drei Hauptwelten ab:

1. **Sammlung** ist das digitale Regal. Dort liegen die eigenen Alben, ihr aktueller Fortschritt und der Einstieg in das konkrete Album. Das Album bleibt der Ort zum Anschauen, Blättern und Pflegen; die Stickerliste ist der fokussierte digitale Tauschzettel.
2. **sammlr.** ist die strikt chronologische Erzählung ausgewählter eigener Ereignisse, privacy-geprüfter Aktivitäten gegenseitiger Freunde und zurückhaltender Sammlr News. Die Seite ist kein Aufgaben- oder Trade-Dashboard; SmartMatches gehören ausschließlich zu Tauschen.
3. **Tauschen** ist der operative Bereich für SmartMatches, Partner, Anfragen und laufende Deals. Eine Anfrage reserviert nichts. Erst Annahme nach erneuter Erfüllbarkeitsprüfung erzeugt Reservierungen. Eigener Versand bucht eigene Abgaben aus, eigener Empfang bucht tatsächliche Zugänge ein. Ein Trade endet erst nach vollständigem Empfang ohne offenen Problemrest und kann danach bewertet werden.

Die **Glocke** ist eine kleine Inbox für direkte Aufmerksamkeit und führt zum fachlichen Vorgang; sie führt die Aktion nicht selbst aus. Das **Profil** ist Sammleridentität, Vertrauen und Community: Username, Bewertung, Freunde, wenige Kernzahlen, gültige Album-Trophäen und abgeschlossene Alben. Account- und Sicherheitsverwaltung sind davon getrennt.

**Trophäen** sind dauerhaft erreichte, zunächst verborgene und individuell kuratierte Album-Erinnerungen. **Statistik** trennt historische Karrierewerte von aktuellen Albumzuständen. Der erste Albumabschluss ist ein genau einmaliger historischer Moment mit Abschlussdatum, Abschluss-Trophy und Feed-Ereignis; das Album bleibt trotzdem normal benutzbar.

Bewusst nicht Teil dieses Closed-Beta-Kernvertrags sind Rankings, Leaderboards, XP/Level, Käufe/Verkäufe, Trackingdienstleister, ein sozialer Reaktionsfeed, vollständige fremde Statistiken, komplexe Reminder-Serien, Herkunftssplitting gesammelter Sticker, mehrere physische Exemplare desselben Albumtyps, Push-Zustellung, regionale/komplexe SmartTrade-Strategien und eine erfundene rückwirkende Sammlerhistorie.

Die neun PO-Fragen sind final beantwortet. Der eingefrorene Vertrag und die technische Reihenfolge werden im [Closed-Beta-Bauplan](../03-closed-beta-build-plan.md) operationalisiert.

## 14. Finaler Status der 37 Cross-Audit-Konflikte

Die Statuswerte bezeichnen die fachliche Auflösung beziehungsweise den nächsten zulässigen Umgang. `TECHNICAL_IMPLEMENTATION_GAP` ist keine offene Produktfrage: Der Vertrag steht, der Ist-Code weicht jedoch ab. Es verbleibt kein `STILL_OPEN`.

| ID | Status | Auflösungsgrund / nächster Vertrag |
|---|---|---|
| CA-001 | TECHNICAL_IMPLEMENTATION_GAP | Home durch strikt chronologischen Feed ersetzen |
| CA-002 | TECHNICAL_IMPLEMENTATION_GAP | Anfrage operativ in Tauschen, Aufmerksamkeit in Glocke; Home-Duplikat entfernen |
| CA-003 | TECHNICAL_IMPLEMENTATION_GAP | Versand/Empfang im Deal, relevante Aufmerksamkeit in Glocke |
| CA-004 | RESOLVED_BY_PO | PO-09 definiert handlungsrelevante und genau eine zulässige terminale Problemmeldung |
| CA-005 | TECHNICAL_IMPLEMENTATION_GAP | laufende Trades aus Home entfernen |
| CA-006 | TECHNICAL_IMPLEMENTATION_GAP | genau eine Bewertungsmöglichkeits-Notification ergänzen |
| CA-007 | RESOLVED_BY_PO | PO-03 schließt SmartMatches aus dem Feed aus |
| CA-008 | TECHNICAL_IMPLEMENTATION_GAP | Profil und Accountoberfläche trennen |
| CA-009 | TECHNICAL_IMPLEMENTATION_GAP | Profil auf repräsentative Sammleridentität reduzieren |
| CA-010 | RESOLVED_BY_PO | PO-01 setzt Profilprivacy als äußeres Gate vor Albumprivacy |
| CA-011 | RESOLVED_BY_PO | PO-01 gilt auch für fremde Abschlussgeschichte |
| CA-012 | TECHNICAL_IMPLEMENTATION_GAP | globale Trophäen aus Closed-Beta-Projektionen ausblenden |
| CA-013 | TECHNICAL_IMPLEMENTATION_GAP | generischen Fallback entfernen; nur gültige kuratierte Kataloge lesen |
| CA-014 | TECHNICAL_IMPLEMENTATION_GAP | persistierter Unlock wird alleinige dauerhafte Read-Wahrheit |
| CA-015 | TECHNICAL_IMPLEMENTATION_GAP | unerreichte/Locked-/Next-Ziele ausblenden |
| CA-016 | TECHNICAL_IMPLEMENTATION_GAP | nur gültige albumbezogene Unlocks zählen |
| CA-017 | POST_BETA | sichtbare vollständige Lifetime-Statistik später; Erfassung ab Cutover ist P1 |
| CA-018 | TECHNICAL_IMPLEMENTATION_GAP | globale Missing/Doppelte aus Karriere und Profil entfernen |
| CA-019 | TECHNICAL_IMPLEMENTATION_GAP | gemeinsame gerichtete Trade-Erfolgsprojektion herstellen |
| CA-020 | RESOLVED_BY_PO | PO-07 erlaubt Backfill nur aus validierter Abschluss-Trophy; neuer Abschluss bleibt historisch |
| CA-021 | RESOLVED_BY_PO | PO-05: bewahrte Geschichte zählt, mitgelöschte nicht |
| CA-022 | RESOLVED_BY_PO | PO-06: bewahrte Karte ohne aktives Album ist in der Closed Beta nicht anklickbar |
| CA-023 | POST_BETA | Mehrfachexemplare sind Future; Closed-Beta-Vertrag darf sie nicht verbauen |
| CA-024 | RESOLVED_BY_PO | PO-04 verschiebt Cross-Album-SmartTrades nach Post-Beta |
| CA-025 | TECHNICAL_IMPLEMENTATION_GAP | nach größter gegenseitig realisierbarer Menge priorisieren |
| CA-026 | RESOLVED_BY_EXISTING_CONTRACT | Audits 06/07 verbieten heimliche Paketverkleinerung |
| CA-027 | RESOLVED_BY_EXISTING_CONTRACT | eigener Versand bucht Abgabe aus, eigener Empfang Zugang ein |
| CA-028 | RESOLVED_BY_EXISTING_CONTRACT | Bewertung erst nach qualifiziertem Abschluss |
| CA-029 | TECHNICAL_IMPLEMENTATION_GAP | unerwünschte Notification-Writer entfernen |
| CA-030 | TECHNICAL_IMPLEMENTATION_GAP | Routine-Reminder für Closed Beta stoppen |
| CA-031 | TECHNICAL_IMPLEMENTATION_GAP | sichtbare Inbox beim Öffnen lesen, Einzelbuttons entfernen |
| CA-032 | TECHNICAL_IMPLEMENTATION_GAP | gelesene Einträge höchstens 30 Tage sichtbar halten |
| CA-033 | RESOLVED_BY_EXISTING_CONTRACT | Hauptwelten heißen Sammlung / sammlr. / Tauschen; Altbegriffe bleiben historische Evidenz |
| CA-034 | RESOLVED_BY_PO | PO-02 verlangt alle drei Feedquellen und strikte Chronologie |
| CA-035 | TECHNICAL_IMPLEMENTATION_GAP | Abschluss, Trophy und Feed exactly once orchestrieren |
| CA-036 | TECHNICAL_IMPLEMENTATION_GAP | vollständiges Album in der Sammlung belassen und zusätzlich historisch projizieren |
| CA-037 | TECHNICAL_IMPLEMENTATION_GAP | Abschlusskarte auf Identität, Status und Erstabschlussdatum reduzieren |

**Verteilung:** `RESOLVED_BY_PO 9`, `RESOLVED_BY_EXISTING_CONTRACT 4`, `TECHNICAL_IMPLEMENTATION_GAP 22`, `UX_DEFERRED 0`, `POST_BETA 2`, `STILL_OPEN 0`.
