# Product Audit – Trophäen

**Stand:** 16. August 2026
**Status:** Product-Owner-Entscheidungen dokumentiert; keine Implementierung, Migration, Test- oder UI-Änderung
**Abhängige Audits:** [Album](04-album.md), [Profil & Community](08-profil-community.md), [sammlr. Home / Feed](09-sammlr-home-feed.md), [Notifications](10-notifications.md)

## 1. Zweck und Verhältnis zum Bestand

Dieses Audit definiert das Trophy-System für die nächste Produktphase. Bestehende Definitionen, persistierte Freischaltungen, UI-Routen und ältere Spezifikationen bleiben als technischer beziehungsweise historischer Bestand erhalten. Widersprüche werden ausdrücklich dokumentiert und nicht als bereits umgesetzt ausgegeben.

Die konkreten finalen Kataloge für FIFA World Cup 2026, VfL Osnabrück und zukünftige Alben sind nicht Gegenstand dieses Audits.

## 2. Verbindliche Produktrolle

Trophäen erfüllen zwei Aufgaben:

1. **Erinnerung:** Sie markieren besondere Momente und Etappen innerhalb einer konkreten Sammlung.
2. **Motivation:** Sie dürfen zusätzlichen Sammelreiz und Entdeckungsfreude erzeugen.

Sie sollen sich wie liebevolle Geheimnisse und Kapitel eines echten Stickeralbums anfühlen. Sie sind weder bloße nachträgliche Statistik noch ein generisches Gamification-System. Das Album bleibt der Sammelgegenstand; Trophäen verstärken sein Erlebnis.

## 3. Vorerst ausschließlich Album-Trophäen

Für die nächste Produktphase besitzt jede normale Trophy genau einen Albumkontext. Globale Mengen- und Nutzungs-Achievements sind nicht Teil des kurzfristig verbindlichen Modells.

Vertagt beziehungsweise Legacy sind insbesondere:

- globale Gesamtsticker-Meilensteine,
- globale Doppelten-Meilensteine wie „Tauschmaterial 50/100“,
- globale Trade-Meilensteine wie „1 Trade“ oder „10 Trades“,
- weitere albumübergreifende Mengen-Achievements.

Diese Konzepte sind nicht für immer verworfen. Sie dürfen später neu bewertet oder neu konzipiert werden. Bestehender Code und persistierte Daten werden in diesem Audit nicht entfernt.

## 4. Ein eigener Trophy-Kosmos pro Album

Jedes Album erhält einen individuell kuratierten Trophy-Katalog aus seinem tatsächlichen Inhalt und Charakter. Eine generische Trophy-Schablone darf nicht automatisch auf jedes Album übertragen werden.

Mögliche Kategorien sind:

- besondere Kapitel,
- vollständige Gruppen,
- Wappenserien,
- Teamfotos,
- Intro- oder Sonderseiten,
- besondere Stickerreihen,
- albumtypische Sammelthemen,
- Easter Eggs,
- das vollständige Album.

WM26 kann beispielsweise Intro, Gruppen, Wappenexperte, Teamfotograf, Etikettenknibbler und besondere Serien besitzen. VfL Osnabrück benötigt eigene inhaltlich passende Ziele; WM-Regeln werden nicht kopiert.

## 5. Charakter vor Prozent-Meilensteinen

Kapitel, Serien und Easter Eggs haben Vorrang vor generischen Fortschrittsschwellen. `25 %`, `50 %` und `75 %` werden nicht zum Kern des Systems. „Erster Sticker“ kann als kleines albumbezogenes Einstiegsritual sinnvoll bleiben.

Heute vorhandene generische Ziele wie „Halbzeit“ und „Endspurt“ werden dadurch nicht in diesem Audit gelöscht, gehören aber in die spätere katalogbezogene Neubewertung. Ihre bloße technische Existenz macht sie nicht zum verbindlichen Zielmodell.

## 6. Dauerhafte, ereignisorientierte Freischaltung

Eine einmal freigeschaltete Trophy bleibt dauerhaft erreicht. Der aktuelle Bestand darf für die erstmalige Erkennung relevant sein, ein später sinkender Bestand darf die historische Freischaltung jedoch nicht rückgängig machen.

Die fachliche Wahrheit lautet damit:

```text
erstmals erfüllte Trophy-Bedingung
→ dauerhaftes Freischaltereignis
→ spätere Bestandsänderungen verändern dieses Ereignis nicht
```

Die Trophy dokumentiert einen erreichten Moment, nicht nur einen jederzeit neu berechneten Bestandszustand.

## 7. Historischer Trophy-Moment

Eine Freischaltung soll perspektivisch mindestens enthalten können:

- Album,
- Trophy-Identität,
- Freischaltdatum,
- auslösenden Sticker beziehungsweise Triggersticker, sofern genau ein letzter notwendiger Sticker bestimmbar ist.

Beispiel:

> Wappenexperte
> Abgestaubt am 12.08.2026
> Ausgelöst durch Sticker GER2

Der Triggersticker ist kein allgemeiner Pflichtwert: Bulk-Änderungen, Trade-Empfang oder mehrere gleichzeitig vervollständigte Bedingungen können mehrdeutig sein. Die genaue fachliche Regel für solche Fälle bleibt einer späteren technischen Spezifikation vorbehalten.

## 8. Entdeckung statt Checkliste

Unerreichte Trophäen bleiben grundsätzlich verborgen. Nicht vorgesehen sind:

- graue Slots für alle zukünftigen Trophäen,
- Schloss-Symbole für den vollständigen Katalog,
- „noch X Sticker bis zur Trophy“,
- eine komplette Achievement-Checkliste,
- XP, Trophy-Punkte oder Trophy-Level,
- künstliche Aufgabenformulierungen zum Grinding.

Alle erreichten Trophäen eines Albums dürfen sichtbar sein und bilden mit der Zeit dessen persönliche Geschichte. Die Sprache soll eher in Richtung „Abgestaubt“ oder „Erreicht“ gehen; finales Wording bleibt UX.

## 9. Albumvollendung

Die vollständige Sammlung eines Albums ist ein besonderer Abschluss und darf eine deutlich gewichtigere Trophy beziehungsweise Abschlussinszenierung erhalten als eine normale Kapitel-Trophäe.

Diese Vollendung kann später insbesondere für die Profil-Vitrine relevant sein. Die genaue Inszenierung und das Verhältnis zwischen Abschluss-Trophy, abgeschlossenem Album und Vitrinenkarte bleiben UX- beziehungsweise Produktausarbeitung.

## 10. Profil, Vitrine, Feed und Notifications

### Profil und Privacy

Erreichte Album-Trophäen dürfen Teil der öffentlichen Sammleridentität sein, sofern die später konsolidierte Profil-/Album-Privacy dies erlaubt. Dieses Audit erfindet keine neue Privacy-Regel. Die offene Kollision zwischen einfachem Profil-Gate und S27-Albumfreigaben bleibt bestehen.

### Vitrine

Die große Albumvollendung kann die Vitrine stärken. Der bisherige übergeordnete Album-Trophäenschrank mit Fortschrittsbalken ist nicht mehr verbindlich gesetzt und wird in einer späteren UX-Phase neu bewertet.

### sammlr.-Feed

Nicht jede Trophy-Freischaltung gehört automatisch in den Feed. Normale Kapitel-Trophäen dürfen persönliche Momente bleiben. Eine Albumvollendung kann feedwürdig sein; weitere seltene Trophy-Ereignisse werden später einzeln definiert.

### Glocke

Trophy-Freischaltungen erzeugen gemäß Audit 10 keine Notification. Die heutige lokale Freischaltinszenierung per Popup ist davon zu unterscheiden und bleibt technischer Bestand.

## 11. Aktuell definierte Trophy-Typen

### Albumbezogene Definitionen

| Katalog | Anzahl | Heutige Inhalte | Bewertung |
|---|---:|---|---|
| WM26 | 23 | Erster Sticker, Halbzeit, Endspurt, Album vollendet, Intro, Gruppen A–L, Wappenexperte, Teamfotograf, WM-Historie, Etikettenknibbler, The Last Dance, Weltmeister | Kapitel-, Serien- und Easter-Egg-Ziele passen grundsätzlich; generische Fortschrittsziele müssen katalogbezogen neu bewertet werden |
| VfL | 19 | vier generische Grundziele, 14 VfL-Kapitel, DJ Matze | eigene Kapitel und DJ Matze passen grundsätzlich; generische Grundziele sind nicht automatisch verbindlich |
| EM24 / andere Alben | 4 | Erster Sticker, Halbzeit, Endspurt, Album vollendet | generische Fallback-Schablone kollidiert mit individueller Kuration pro Album |

Die finalen Kataloge werden separat ausgearbeitet. Dieses Audit bestätigt keine der genannten Listen vollständig.

### Globale Definitionen

Aktuell existieren 24 globale Definitionen:

- neun Gesamtsticker-Schwellen von 50 bis 25.000,
- neun Doppelten-Schwellen von 50 bis 25.000,
- sechs Trade-Schwellen von 1 bis 250.

Sie verwenden den künstlichen Albumkontext `__global__` und sind für die nächste Produktphase vollständig Legacy beziehungsweise vertagt.

### Technische Triggerarten

Der heutige Definitionskatalog kennt:

- `album_count`,
- `album_complete`,
- `codes`,
- `global_stickers`,
- `global_duplicates`,
- `global_trades`.

Für das neue aktive Modell sind nur albumbezogene Bedingungen relevant. Die konkrete künftige Trigger-Taxonomie wird nicht in diesem Audit erweitert.

## 12. Aktueller Freischalt- und Persistenzvertrag

### Erkennung

Album-Trophäen werden dynamisch aus dem aktuellen Inventory berechnet:

- `album_count` und `album_complete` aus der Anzahl vorhandener unterschiedlicher Sticker,
- `codes` aus der vollständigen Abdeckung definierter Sticker-Codes.

Routen für Einzeländerung, Mengenänderung, Bulk-Änderung, lokalen Transfer sowie Trade-/Problem-Empfang vergleichen vor und nach einer Mutation die dynamisch erreichten Trophy-Namen. Neu erreichte Namen werden anschließend gespeichert und gegebenenfalls für ein Session-Popup vorgemerkt.

Die Trophy-Orchestrierung liegt nicht zentral im `InventoryWriteService`, sondern verteilt in Route- und Lifecycle-Callbacks. Dadurch ist die Freischaltung vorhanden, aber nicht als einheitlicher fachlicher Eventservice modelliert.

### Persistenz

`unlocked_trophies` speichert:

- `user_id`,
- `album_id`,
- `trophy_name`,
- `unlocked_at` mit `CURRENT_TIMESTAMP`.

`UNIQUE(user_id, album_id, trophy_name)` verhindert dieselbe Freischaltung mehrfach. Es gibt keinen regulären Löschpfad bei sinkendem Bestand; Kontolöschung beziehungsweise Anonymisierung ist davon getrennt. Die persistierte Zeile erfüllt damit bereits den Kern einer dauerhaften Freischaltung.

Es werden jedoch weder eine stabile Trophy-ID noch Triggersticker, Source-Mutation oder ein Snapshot der Definition gespeichert. Namen fungieren faktisch als Identität. Katalogumbenennungen können deshalb bestehende Historie von heutigen Definitionen entkoppeln; die lokale Datenbank enthält bereits ältere Trophy-Namen, die nicht mehr im aktiven Katalog stehen.

## 13. Persistiert dauerhaft, angezeigt teilweise dynamisch

Die heutige Anwendung besitzt zwei konkurrierende Wahrheiten:

1. `unlocked_trophies` bewahrt historische Freischaltungen dauerhaft.
2. Album-, Statistik- und globale Ansichten bestimmen den sichtbaren Status teilweise erneut aus dem aktuellen Bestand.

Konkrete Folgen:

- Die Album-Trophy-Seite lädt zwar `unlocked_at`, rendert aber nur Definitionen, die nach aktuellem Bestand erneut `unlocked` sind.
- Der globale Sammlr-Schrank berechnet globale Schwellen vollständig aus aktuellen Stickern, Doppelten und Trades statt aus gespeicherten Freischaltungen.
- Statistik, „zuletzt“ und „nächstes Ziel“ werden dynamisch berechnet.
- Das Profil zählt dagegen alle persistierten Zeilen, einschließlich `__global__` und historischer Namen.

Eine gespeicherte Trophy wird daher nicht aus der Datenbank verloren, kann aber bei sinkendem Bestand aus Trophy-Ansichten verschwinden. Das verletzt den neuen dauerhaften Darstellungsvertrag und kann außerdem unterschiedliche Trophy-Zahlen zwischen Profil, Statistik und Trophy-Seite erzeugen.

## 14. Freischaltdatum und Triggersticker

Das Freischaltdatum ist bereits persistiert, wird exportiert und kann in der Album-Trophy-Detailansicht dargestellt werden, solange die Trophy dort aufgrund des aktuellen Bestands sichtbar bleibt.

Ein Triggersticker wird nicht in `unlocked_trophies` gespeichert. Der bestehende URL-Parameter `trigger` hebt nach einer einzelnen Mengenänderung kurzfristig einen Sticker in der Albumwand hervor, besitzt aber keine feste Beziehung zu einer Trophy und ist keine Trophy-Historie. Bei Bulk- oder Trade-Ereignissen existiert keine persistierte Triggerinformation.

Für eine historische Detailansicht sind heute bereits Nutzer, Album, Trophy-Name, Freischaltdatum sowie die aktuelle Definition mit Beschreibung und Icon verfügbar. Es fehlen stabile Trophy-ID, Triggersticker und ein historischer Definitionssnapshot.

## 15. Sichtbarkeit unerreichter Ziele im heutigen UI

Die eigentliche Album-Trophy-Liste rendert nur aktuell erreichte Trophäen und entspricht damit grundsätzlich dem Entdeckungsprinzip. Andere Einbindungen kollidieren jedoch:

- Die Album-Hauptseite nennt „Nächstes Ziel“ mit dem Namen einer unerreichten Trophy.
- Die Statistik nennt nächste Trophy und exakten Fortschritt.
- Der globale Sammlr-Schrank zeigt Album-Trophäenschränke mit Fortschrittsbalken.
- vorhandene ältere Renderer enthalten gesperrte, nächste und teilweise verschwommene Trophy-Ziele, auch wenn sie aktuell nicht der Hauptpfad sind.

Diese Funktionen werden nicht jetzt entfernt. Bei einer späteren Umsetzung müssen sie ausgeblendet, entfernt oder auf das neue Entdeckungsmodell umgebaut werden.

## 16. Technische und UX-seitige Einbindungen

| Bereich | Heutige Einbindung | Abhängigkeit zum neuen Modell |
|---|---|---|
| Album | Quick Card mit nächstem/letztem Ziel; eigene Trophy-Route; Album-Bottom-Navigation | unerreichte Vorschau entfernen oder neu bewerten; erreichte Historie albumbezogen lesen |
| Sammlr-Schrank `/trophaeen` | Albumportal plus globale Sticker-/Doppelte-/Trade-Trophäen | globale Bereiche vertagen; übergeordneter Schrank und Fortschrittsbalken neu bewerten |
| Statistik | dynamische Gesamtzahl, letzte und nächste Trophy samt Fortschritt | globale Zahlen und nächste Ziele kollidieren; Statistik-/Trophy-Grenze später klären |
| Profil | persistierte Gesamtzahl und Eigentümerlink; fremd keine Details | Zählung enthält heute globale/Legacy-Zeilen; spätere öffentliche Album-Trophäen hängen von Privacy ab |
| Vitrine | abgeschlossene Alben werden aus aktuellem Albumfortschritt abgeleitet | Albumvollendung kann später stärker inszeniert werden; kein neuer Vertrag in diesem Audit |
| Home | keine Trophy-Feedquelle implementiert | nur Albumvollendung ist bereits grundsätzlich feedwürdig; weitere Auswahl offen |
| Notifications | keine reguläre Trophy-Notification | entspricht Audit 10 |
| Sticker-Mutationen | Vorher-/Nachher-Erkennung in mehreren Routen | historische Eventerfassung und Triggerzuordnung sind nicht zentralisiert |
| Trades/Probleme | Empfangs- und Abschlusscallbacks können Album-Trophäen persistieren | Tradeeingang kann Freischaltmoment auslösen; Triggerdetails fehlen |
| Privacy | fremde Profile zeigen nur aggregierte Trophy-Anzahl | konkrete öffentliche Trophäen benötigen die offene Profil-/Album-Privacy-Konsolidierung |
| Datenexport/Kontolebenszyklus | Freischaltungen mit Datum werden exportiert und bei Kontolöschung behandelt | bestehende Compliance-Pfade müssen bei späteren Feldern mitgeführt werden |

## 17. Abgleich mit bestehenden Verträgen

| Bestandsvertrag | Kollision oder Übereinstimmung |
|---|---|
| Product Bible Profil: Trophäen als sichtbarer Teil der Sammleridentität | grundsätzlich passend, abhängig von Privacy |
| Audit 08: alle erreichten Trophäen dürfen sichtbar sein | passend; aktuelle Profile zeigen nur Anzahl, keine vollständige Liste |
| Audit 09: Trophy-Freischaltung als mögliche eigene Sammlerreise | präzisiert: nicht jede Trophy, Albumvollendung kann feedwürdig sein |
| Audit 10: keine Trophy-Notification | deckungsgleich |
| Audit 04: Trophäen auf Album sekundär; möglicher „Stats & Trophäen“-Bereich offen | weiterhin gültig; konkrete Struktur bleibt UX-offen |
| S26: persistierte Trophy-Anzahl inklusive aller Scopes | technisch korrekt für S26, kollidiert aber mit dem kurzfristig albumbezogenen Modell und zählt Legacy/global mit |
| heutige globale Sticker-/Doppelte-/Trade-Schwellen | direkte Kollision; Legacy/vertagt |
| generischer Fallbackkatalog für jedes Album | direkte Kollision mit individueller Kuration |
| dynamische Neuberechnung sichtbarer Freischaltungen | direkte Kollision mit dauerhafter historischer Trophy |
| nächstes Ziel, Fortschrittsbalken und Locked-/Secret-Renderer | direkte Spannung zum verborgenen Katalog |
| übergeordneter Sammlr-/Album-Trophäenschrank | nicht mehr verbindlich gesetzt; spätere UX-Neubewertung |

## 18. Bereits vollständig oder grundsätzlich vorhanden

- albumbezogene Definitionen für WM26 und VfL,
- charaktervolle Kapitel-, Serien- und Easter-Egg-Beispiele,
- Bedingungen über Albumanzahl, Vollendung oder definierte Codes,
- persistente einmalige Zeile pro Nutzer, Album und Trophy-Name,
- Freischaltdatum,
- Freischaltprüfung nach mehreren Sticker- und Trade-Mutationen,
- lokale Freischaltinszenierung per Popup,
- Anzeige erreichter Album-Trophäen mit Datum und Beschreibung,
- Datenexport und Kontolebenszyklus für Trophy-Zeilen,
- Profilaggregation aus persistierter Trophy-Wahrheit.

## 19. Technisch fehlend oder später umzubauen

- aktive Beschränkung auf albumbezogene Trophäen,
- Entfernung beziehungsweise Ausblendung globaler Trophy-Flächen und Kennzahlen,
- individuell kuratierter Katalog für jedes unterstützte Album ohne generischen Fallback,
- dauerhafte Anzeige ausschließlich aus persistierter Freischaltungswahrheit,
- stabile Trophy-ID unabhängig vom Anzeigenamen,
- persistierbarer Triggersticker beziehungsweise definierter mehrdeutiger Triggerzustand,
- zentrale ereignisorientierte Freischaltarchitektur über alle relevanten Mutationen,
- Entfernung unerreichter Ziele und Fortschritthinweise aus Album, Statistik und Schrank,
- konsistente albumbezogene Profilzählung ohne globale/Legacy-Verzerrung,
- privacy-geprüfte Darstellung erreichter Trophäen auf fremden Profilen,
- Feed-Ereignis für Albumvollendung,
- besondere Abschlussinszenierung für ein vollständiges Album.

## 20. Bewusst vertagte UX- und Produktfragen

Nicht festgelegt werden finale Trophy-Grafik, Kartenlayout, Freischaltanimation, Detailansicht, Typografie, Farben, Sortierung, Microcopy, Vitrineninszenierung, endgültiger Album-Trophäenschrank oder zusätzliche seltene feedwürdige Trophäen.

Ebenfalls separat auszuarbeiten sind die vollständigen Kataloge je Album, der Umgang mit mehrdeutigen Triggern, die technische Identität versionierter Definitionen und eine mögliche spätere Neubewertung globaler Trophäen.
