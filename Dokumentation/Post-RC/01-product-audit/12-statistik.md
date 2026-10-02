# Product Audit – Statistik

**Stand:** 16. August 2026
**Status:** Product-Owner-Entscheidungen dokumentiert; keine Implementierung, Migration, Test- oder UI-Änderung
**Abhängige Audits:** [Sammlung](03-sammlung.md), [Album](04-album.md), [Trade-Lifecycle](07-trade-lifecycle.md), [Profil & Community](08-profil-community.md), [sammlr. Home / Feed](09-sammlr-home-feed.md), [Trophäen](11-trophaeen.md)

## 1. Zweck und Produktrolle

Statistik beschreibt die persönliche Sammlerkarriere in Zahlen. Sie soll über Monate und Jahre interessanter werden und die tatsächliche Sammlerreise dokumentieren. Sie ist keine zweite operative Bestandsübersicht und ersetzt weder Sammlung, Stickerwand, SmartTrades, Tauschzentrale, Profil, Home-Feed noch Trophy-System.

Verbindlich sind zwei getrennte Ebenen:

1. **Gesamtstatistik:** historische Sammlr-Karriere.
2. **Albumstatistik:** aktueller Zustand und historische Entwicklung eines konkreten Albums.

Aktuelle Bestandswerte und historische Karrierewerte dürfen dabei nicht unter derselben Bedeutung vermischt werden.

## 2. Verbindliche Gesamtstatistik

Die persönliche Gesamtstatistik darf langfristig folgende Kernwelt enthalten:

- historisch insgesamt gesammelte beziehungsweise erhaltene Sticker,
- über erfolgreiche Trades historisch erhaltene Sticker,
- über erfolgreiche Trades historisch abgegebene Sticker,
- Anzahl erfolgreicher abgeschlossener Trades,
- Anzahl unterschiedlicher erfolgreicher Tauschpartner,
- größter erfolgreicher Trade mit getrennten Richtungen, zum Beispiel `18 erhalten · 21 abgegeben`,
- Alben begonnen,
- Alben abgeschlossen,
- Anzahl gültiger albumbezogener Trophäen nach Audit 11.

`Sticker gesammelt` ist ein nicht sinkender Lebenszeitwert. Er ist ausdrücklich **nicht** die Summe des aktuell vorhandenen Bestands. Eine Herkunftszerlegung nach Pack, manueller Eingabe, Trade, Kauf oder sonstiger Quelle gehört nicht zum Vertrag.

Erhaltene und abgegebene Trade-Sticker bleiben getrennte Werte. Ungleiche Trades sind zulässig. Daraus werden weder Durchschnittstauschgröße noch Großzügigkeitsquote, Trade-Effizienz, Tauschwert oder Verhältnis-Score gebildet.

Als erfolgreicher Trade gilt entsprechend dem konsolidierten Lifecycle-Vertrag:

- Legacy-Anfrage `completed` ohne Lifecycle-Zeile oder
- Anfrage `completed` mit Lifecycle `completed`, beidseitigem vollständigem Empfang und ohne offenen Problemrest.

Anfragen, Annahmen, Reservierungen, Abbrüche und terminale Problemzustände `closed_with_problem` beziehungsweise `problem_resolved_after_close` zählen nicht. Eine vor dem regulären Abschluss vollständig gelöste Beanstandung verhindert den Erfolg nicht: Der Deal endet danach regulär als `completed`, die Problemhistorie bleibt lediglich nachvollziehbar.

## 3. Bewusste Ausschlüsse der Gesamtstatistik

Nicht Teil der Karriere-Gesamtstatistik sind:

- globale aktuell fehlende Sticker,
- globale aktuelle Doppelte,
- Herkunftsanteile gesammelter Sticker,
- durchschnittliche Tauschgröße,
- künstliche Verhältnis- oder Bewertungsscores,
- schnellstes Album,
- aktivster Monat, beste Woche, Serien oder weitere persönliche Rekorde,
- `Sammlr seit` als Profil-/Identitätsinformation,
- Rankings, Leaderboards und Vergleiche mit anderen Nutzern.

Fehlende und Doppelte bleiben operative album- beziehungsweise bestandsbezogene Werte. Ein neues Album darf eine Karrierekennzahl nicht künstlich verschlechtern.

## 4. Verbindliche Albumstatistik

Die Statistik eines konkreten, weiterhin zur eigenen Sammlung gehörenden Albums darf enthalten:

- aktuellen Fortschritt `x / gesamt`,
- aktuellen Prozentwert,
- aktuell fehlende Sticker,
- aktuell vorhandene Doppelte,
- historisch über dieses Album ertauschte Sticker,
- historisch über dieses Album abgegebene Sticker,
- erfolgreiche Trades dieses Albums,
- gültige abgestaubte Trophäen dieses Albums,
- Sammelbeginn,
- bei erstmals vollständig gewordenem Album die Sammeldauer.

Start ist das Hinzufügen des Albums zur eigenen Sammlung. Ende ist die erstmalige vollständige Fertigstellung. Eine spätere Bestandsreduktion darf diesen historischen ersten Abschlusszeitpunkt nicht verschieben oder löschen.

Ein gelöschtes Album zählt anschließend weder bei `Alben begonnen` noch bei `Alben abgeschlossen`. „Gelöscht“ bedeutet für diese Kennzahlen bewusst „raus“. Dass Tradehistorie aus Nachweisgründen erhalten bleibt, macht das gelöschte Album nicht wieder zu einem Statistik-Album.

Es werden keine künstlichen Statistikereignisse für `25 %`, `50 %`, `75 %` oder `90 %` eingeführt. Langfristig genügt als visuelle Zielrichtung eine verständliche Fortschrittskurve pro Album; weitere Chart- oder Dashboardwelten sind nicht beschlossen.

## 5. Heutige Seite `/statistik`

Die globale Route zeigt aktuell:

| Bereich | Angezeigter Wert | Tatsächliche Berechnung | Einordnung |
|---|---|---|---|
| Alben | begonnen | Anzahl aktueller `user_albums`-Zuordnungen | aktueller Mitgliedschaftsstand |
| Alben | beendet | aktuelle unterschiedliche Stickerzahl `>=` aktueller Albumumfang | aktueller Bestand, kein historischer Abschluss |
| Sticker | gesammelt | Summe `stickers.quantity` über alle Stickerzeilen des Nutzers | aktueller Bestand, sinkt bei Abgabe/Entfernung |
| Sticker | fehlen | Summe der aktuellen Albumlücken | aktueller operativer Zustand; künftig nicht global gewünscht |
| Sticker | doppelt | Summe `stickers.duplicates` | aktueller operativer Zustand; künftig nicht global gewünscht |
| Tauschbörse | abgeschlossen | `trade_requests.status='completed'` | historische Zeilen, aber ohne Lifecycle-/Problem-Konsistenzprüfung |
| Tauschbörse | Sticker getauscht | Länge von `give_codes` plus Länge von `get_codes` für jeden `completed`-Request | zählt beide Seiten zusammen statt erhalten/abgegeben zu trennen |
| Trophäen | abgestaubt | dynamisch aktuell erfüllte Albumziele plus globale aktuelle Schwellen | kein Lesen der dauerhaften, gültigen Albumfreischaltungen |

Zusätzlich zeigt die Seite einen Trophäenschrank mit „zuletzt“, „nächstes Ziel“ und Fortschritt. Auch diese Werte werden dynamisch aus dem aktuellen Bestand und den globalen Definitionen erzeugt. Das kollidiert sowohl mit der historischen Statistikrolle als auch mit dem in Audit 11 verborgenen Trophy-Katalog.

`Sticker gesammelt` erfüllt den neuen Vertrag nicht: Die heutige Summe ist lediglich die aktuelle physische Menge. Manuelle Reduktion, Trade-Abgabe oder andere Bestandskorrektur können sie senken; frühere Zugänge sind danach nicht mehr enthalten.

## 6. Heutige Albumstatistik

`/album/<album_id>/statistik` zeigt ausschließlich den aktuellen Zustand:

- Fortschritt in Prozent,
- Anzahl aktuell gesammelter unterschiedlicher Sticker,
- aktuell fehlende Sticker,
- aktuelle Doppelte,
- Albumgesamtzahl.

Alle Werte stammen aus dem zentralen Inventory-Readmodel und dem aktuellen Albumkatalog. Nicht angezeigt und nicht durch diese Route berechnet werden historische Trade-Richtungen, erfolgreiche Albumtrades, Trophy-Historie, Sammelbeginn, erster Abschluss, Sammeldauer oder Verlaufspunkte.

Die aktuellen Albumwerte sind fachlich brauchbar, bleiben aber Bestandswerte und dürfen nicht zu Lebenszeitwerten umgedeutet werden.

## 7. Kennzahlen im heutigen Profil

S26 beziehungsweise `CollectorProfileService` zeigt heute vier aggregierte Werte:

1. Anzahl sichtbarer/zugeordneter Alben,
2. aktuelle Doppelte dieser sichtbaren Alben,
3. erfolgreiche Trades,
4. alle persistierten Trophy-Zeilen.

Die Tradezahl prüft bereits besser als `/statistik`, dass ein zugeordneter Lifecycle ebenfalls `completed` ist, validiert dort aber nicht zusätzlich Empfangs- und Problemrest. Die Trophyzahl zählt auch globale `__global__`- und historische Legacy-Namen. `Doppelte` ist nach Audit 08 keine dauerhafte zentrale Profilkennzahl.

Die vollständige persönliche Statistik bleibt dem Nutzer selbst vorbehalten. Fremde Profile dürfen später nur eine privacy-geprüfte, repräsentative Auswahl zeigen; Kandidaten sind abgeschlossene Alben, erfolgreiche Trades, unterschiedliche Tauschpartner und gültige Album-Trophäen. Endgültige Auswahl und Darstellung bleiben UX-offen. Eine vollständige fremde Statistikseite ist nicht vorgesehen.

## 8. Persistierte Datenbasis

### Aktueller Bestand

`stickers` speichert pro Nutzer, Album und Stickercode nur den aktuellen Zustand mit `quantity`, redundanter `duplicates`-Projektion und Status. Die Zeile besitzt keinen Erfassungs-, Änderungs- oder Löschzeitpunkt. Add-, Remove-, Set- und Bulk-Pfade überschreiben den Bestand ohne allgemeine Bestandsereignisse oder Snapshots.

Der `InventoryReadService` erzeugt zwar einen `captured_at`-Zeitpunkt für den jeweiligen Read-Snapshot, persistiert diesen Snapshot jedoch nicht. Er bildet daher keine Verlaufshistorie.

### Albumzuordnung und Vollendung

`user_albums` speichert Nutzer, Album, Sichtbarkeit und Trade-Pool-Schalter, aber keinen `created_at`- beziehungsweise Sammelbeginn. Die Hinzufügen-Route schreibt nur die Zuordnung. Die numerische ID ist kein belastbarer Zeitstempel.

Es gibt kein eigenes persistiertes Albumabschlussereignis und keinen `first_completed_at`-Wert. `Album vollendet` in `unlocked_trophies` kann bei einer konkreten vorhandenen, fachlich gültigen Freischaltung ein Indiz mit Zeitpunkt sein. Wegen historisch verteilter Trigger, Legacy-Namen und nicht garantierter vollständiger Freischaltung ist es kein allgemeiner Ersatz für einen verlässlichen ersten Albumabschluss.

### Tradehistorie

`trade_requests` bewahrt Album, beide Beteiligten, gerichtete `give_codes`-/`get_codes`-Pakete, Status und Erstellzeit. Wiederholte Codes bilden mehrere Einheiten ab. Für angenommene neuere Trades verdichtet `trade_positions` diese Pakete zusätzlich zu gerichteten Positionen mit positiver `quantity`.

`trades` bewahrt Lifecycle-Zustand und bei regulärem Abschluss `completed_at`; Empfangs- und Problemtabellen sowie `trade_events` erlauben die konsistente Erfolgsprüfung. Legacy-Completed-Trades ohne Lifecycle bleiben mit ihren gerichteten JSON-Paketen lesbar, besitzen aber keinen verlässlichen Abschlusszeitpunkt.

Der geprüfte lokale Datenstand bestätigt den Mischbetrieb: 13 Requests tragen `completed`; davon besitzen acht eine ebenfalls abgeschlossene Lifecycle-Zeile und fünf sind reine Legacy-Abschlüsse. Zwei weitere Requests sind angenommen und im Lifecycle erst `partially_shipped`; sie dürfen nicht zählen. Die gespeicherten Positionen erhalten Richtung und Menge, und gelöste Problemereignisse bleiben auch bei anschließend regulär abgeschlossenen Deals sichtbar.

Damit sind aus der erhaltenen Tradehistorie grundsätzlich bestimmbar:

- erfolgreiche Tradeanzahl,
- erhaltene und abgegebene Einheiten aus Nutzerperspektive,
- dieselben Richtungswerte pro Album,
- unterschiedliche Gegenparteien,
- größter erfolgreicher Trade.

Die robuste Projektion muss jeden fachlichen Deal genau einmal zählen, Lifecycle-Positionen beziehungsweise Legacy-Pakete korrekt perspektivieren und den erfolgreichen Endzustand prüfen. Die heutige Statistikroute tut dies nicht.

### Trophy-Historie

`unlocked_trophies` bewahrt Nutzer, Album, Trophy-Namen und `unlocked_at`. Für die Statistik dürfen nur fachlich gültige albumbezogene Freischaltungen des Vertrags aus Audit 11 zählen. Globale `__global__`-Zeilen und nicht mehr gültige Legacy-Namen müssen abgegrenzt werden; eine stabile Trophy-ID und ein Definitionssnapshot fehlen weiterhin.

## 9. Zuverlässigkeit der gewünschten Werte

| Zielwert | Heute zuverlässig bestimmbar? | Begründung |
|---|---|---|
| erfolgreiche abgeschlossene Trades | ja | persistierte Requests plus Lifecycle-/Empfangs-/Problemzustand; Legacy-Completed bleibt kompatibel |
| historisch ertauschte Sticker | ja | gerichtete Pakete/Positionen und Mengen bleiben erhalten |
| historisch abgegebene Sticker | ja | gleicher gerichteter Vertrag aus Gegenperspektive |
| unterschiedliche erfolgreiche Partner | ja | beide Nutzer-IDs sind pro erfolgreichem Deal erhalten |
| größter erfolgreicher Trade | ja | Richtungs- und Mengenwerte pro Deal sind erhalten; Gleichstands-UX ist offen |
| Album-Tradezahlen und -mengen | ja | `album_id` ist in Request und Position gespeichert |
| aktueller Albumfortschritt/Fehlende/Doppelte | ja | aktuelles Inventory und Katalog sind vorhanden |
| historisch insgesamt gesammelte Sticker | nein | frühere Zugänge und spätere Reduktionen außerhalb der Tradehistorie fehlen |
| verlässlicher Sammelbeginn | nein | `user_albums` besitzt keinen Zeitstempel |
| erstmaliger Albumabschluss | nicht allgemein | einzelne passende Trophy-Zeilen können Indiz sein, aber kein vollständiger Vertrag |
| korrekte Sammeldauer | nein | verlässlicher Start und allgemein verlässliches erstes Ende fehlen |
| historische Fortschrittskurve | nein | es gibt weder persistierte Bestandsänderungsereignisse noch Snapshots |
| gültige Album-Trophyzahl | teilweise | Freischaltungen sind persistiert; gültige Katalogidentität und Legacy-Abgrenzung sind noch nicht stabil |

## 10. Albumlöschung und Datenverlust

Im aktuellen Produktcode existiert kein regulärer Pfad, mit dem ein Nutzer ein einzelnes Album aus seiner Sammlung löscht. Deshalb ist das geforderte Verhalten heute weder als kompletter Workflow implementiert noch real beobachtbar.

Die Kontenanonymisierung ist kein Album-Löschmodell: Sie löscht alle `stickers`, `user_albums` und `unlocked_trophies` des Kontos, lässt die für Nachweis und Gegenparteien relevante Tradehistorie jedoch bestehen und anonymisiert das Konto.

Würde heute nur eine `user_albums`-Zuordnung entfernt, verschwänden `begonnen` und die aktuelle Abschlussprojektion aus den zuordnungsbasierten Albumzahlen. Die globale Stickerabfrage von `/statistik` ist dagegen nicht an `user_albums` gekoppelt; verbliebene Stickerzeilen könnten weiter in `gesammelt` und `doppelt` eingehen. Dieser hypothetische Teildelete wäre inkonsistent und ist kein bestehender Produktworkflow.

Eine spätere Albumlöschung muss deshalb fachlich festlegen, welche zugehörigen aktuellen Daten entfernt werden und welche Nachweishistorie erhalten bleibt. Verbindlich ist bereits nur das Ergebnis: Das gelöschte Album ist aus begonnenen/abgeschlossenen Albumkennzahlen und eigener Albumstatistik herauszufiltern. Dieses Audit beschließt keine Löscharchitektur.

## 11. Fehlende Historie nach A/B/C

Die Kategorien bewerten Informationen, nicht pauschal ganze Features:

### A – später aus vorhandener Historie rekonstruierbar

- Anzahl regulär erfolgreich abgeschlossener Trades,
- historisch erhaltene und abgegebene Tradeeinheiten insgesamt und pro Album,
- unterschiedliche erfolgreiche Tauschpartner,
- größter erfolgreicher Trade,
- Abschlusszeit neuerer Lifecycle-Trades,
- vorhandene Trophy-Freischaltzeitpunkte, soweit die Zeile einer gültigen Album-Trophy sicher zugeordnet werden kann.

### B – ab einem definierten zukünftigen Erfassungsbeginn historisierbar, Vergangenheit aber unvollständig

- nicht sinkender Lebenszeitwert `Sticker gesammelt`,
- Sammelbeginn neu hinzugefügter Alben,
- erster Abschluss neu vollständig werdender Alben,
- Sammeldauer daraus,
- zukünftige Fortschrittskurven,
- künftige Lösch-/Austrittsinformation eines Albums, falls sie für Filterung oder Nachweis benötigt wird.

Ein heutiger Bestandsstand kann später höchstens als ausdrücklich datierter Ausgangssnapshot dienen. Er beweist nicht, wie viele Sticker zuvor bereits gesammelt und wieder abgegeben wurden.

### C – ohne rechtzeitige Änderung dauerhaft verloren oder später nicht zuverlässig bestimmbar

- alle vergangenen manuellen beziehungsweise nicht als Trade erfassten Stickerzugänge und -abgänge,
- daraus die exakte bisherige Lebenszeitsumme `Sticker gesammelt`,
- ursprüngliche Startzeit bestehender Albumzuordnungen,
- erster historischer Vollendungszeitpunkt eines bestehenden Albums ohne belastbaren passenden Freischaltnachweis,
- sämtliche früheren Zwischenstände für eine rückwirkende Fortschrittskurve,
- Zeitpunkt und frühere Zugehörigkeit bereits entfernter Albumzuordnungen, sofern solche Löschungen außerhalb des heutigen regulären Codes stattgefunden haben.

Die B-Einordnung bedeutet, dass künftige Ereignisse ab einem Cutover zuverlässig erfasst werden können. Die bereits fehlenden Vor-Cutover-Einzelereignisse bleiben C und dürfen nicht aus dem aktuellen Bestand erraten werden.

## 12. Prinzip: Historie vor späterer Auswertung erfassen

Für bereits beschlossene zukünftige Statistikfunktionen gilt:

> Ein fachlich wichtiger Sammlermoment wird bei seinem Eintritt verlässlich festgehalten, bevor eine spätere Statistik oder Visualisierung ihn benötigt.

Heute fehlen dafür insbesondere verlässliche Informationen zu Albumhinzufügen, erstmaliger Vollendung und Bestandsentwicklung beziehungsweise Zugängen. Der Audit legt weder konkrete Eventtabellen noch Snapshotfrequenz, Backfill, Migration oder technische Architektur fest. Er verbietet jedoch, Jahre später scheinpräzise Historie aus dem dann aktuellen Bestand zu erfinden.

## 13. Abhängigkeiten und Grenzen

| Bereich | Statistikabhängigkeit |
|---|---|
| Albumverwaltung | besitzt Mitgliedschaft und spätere Löschgrenze; Startzeit fehlt |
| Inventory | besitzt aktuellen Zustand; allgemeine Mutationshistorie fehlt |
| Trades | besitzt gerichtete Mengen und die belastbarste vorhandene Karrierehistorie |
| Trophäen | liefert dauerhafte Unlock-Zeilen, benötigt aber gültigen albumbezogenen Katalog |
| Profil | zeigt nur repräsentative Kernzahlen; vollständige Statistik bleibt privat |
| Privacy | fremde Kernzahlen und Albumbezug müssen dem konsolidierten Profil-/Album-Gate folgen |
| Home-Feed | darf ausgewählte Ereignisse erzählen, ist aber keine Statistikdatenbank |
| Albumlöschung | muss gelöschte Alben aus Albumkennzahlen entfernen, ohne Trade-Nachweis beliebig zu vernichten |

## 14. Konflikte mit älteren Verträgen und Ist-Code

| Bestand | Konflikt mit dem neuen Vertrag |
|---|---|
| `/statistik`: aktuelle Menge heißt `gesammelt` | verwechselt aktuellen Bestand mit nicht sinkender Lebenszeitkennzahl |
| `/statistik`: globale Fehlende und Doppelte | operative Werte gehören nicht in die Karriere-Gesamtstatistik |
| `/statistik`: beide Tradepakete zusammen | trennt erhalten und abgegeben nicht und zählt nicht aus Nutzerperspektive |
| `/statistik`: nur Legacy-Statusprüfung | kann inkonsistente Lifecycle-/Problemzustände als erfolgreich zählen |
| `/statistik`: dynamische globale und Album-Trophäen | kollidiert mit gültigen, dauerhaft persistierten Album-Trophäen aus Audit 11 |
| `/statistik`: nächstes Trophy-Ziel | kollidiert mit dem verborgenen Trophy-Katalog |
| Profil/S26: feste Kennzahl `Doppelte` | Audit 08 und dieses Audit stufen sie als operativ statt repräsentativ ein |
| Profil/S26: alle Trophy-Zeilen | zählt globale und Legacy-Freischaltungen mit |
| Profil/S26: aktueller Fortschritt entscheidet Vitrine/Abschluss | ist kein historischer erster Abschluss |
| ältere Profilspezifikation: spätere „Freakstatistiken“ | bleibt nur allgemeine Vision; die hier ausdrücklich ausgeschlossenen Werte werden nicht dadurch freigegeben |

Die älteren Dokumente und der aktuelle Code bleiben Nachweis des Bestands. Neue Product-Owner-Entscheidungen dieses Audits haben für die nächste Produktausrichtung Vorrang, sind aber noch nicht umgesetzt.

## 15. Bewusst vertagte Fragen

Offen bleiben:

- Gleichstandsregel und Detaildarstellung beim größten Trade,
- finale Auswahl, Reihenfolge, Wording und Visualisierung der eigenen Statistikwerte,
- endgültige Auswahl der wenigen fremd sichtbaren Kernzahlen,
- Privacy-Konsolidierung zwischen Profil-Gate und Album-Sichtbarkeit,
- konkrete Darstellung der einen Album-Fortschrittskurve,
- technische Form von Events, Snapshots, Zählern, Cutover und möglichem Backfill,
- stabile Trophy-Identität und Umgang mit Legacy-Namen,
- genauer technischer Vertrag einer späteren Albumlöschung.

Nicht vertagt, sondern ausdrücklich ausgeschlossen sind Durchschnittswerte, künstliche Verhältnis-Scores, weitere persönliche Rekorde, Rankings und Nutzervergleiche.

## 16. Empfohlener nächster Product-Audit-Bereich

Als nächster Bereich empfiehlt sich **Albumlöschung und Kontinuität der Sammlerhistorie**. Die Statistikentscheidungen hängen unmittelbar davon ab, wann ein Album fachlich als entfernt gilt, welche aktuellen Bestände verschwinden und welche Trade-, Trophy- und Verlaufsnachweise erhalten bleiben. Das ist eine Produktgrenze; konkrete Datenhaltung oder Migration gehört erst in eine spätere technische Spezifikation.
