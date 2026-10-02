# Product Audit – Albumabschluss / Abgeschlossene Alben

**Stand:** 16. August 2026
**Status:** Product-Owner-Entscheidungen dokumentiert; keine Implementierung, Migration, Test- oder UI-Änderung
**Abhängige Audits:** [Sammlung](03-sammlung.md), [Album](04-album.md), [Profil & Community](08-profil-community.md), [sammlr. Home / Feed](09-sammlr-home-feed.md), [Notifications](10-notifications.md), [Trophäen](11-trophaeen.md), [Statistik](12-statistik.md)

## 1. Zweck und Begriffe

Dieses Audit definiert den verbindlichen Produktvertrag für die erstmalige Vollendung eines konkreten Albums beziehungsweise späteren Albumexemplars und für dessen dauerhafte Darstellung als Teil der Sammlerhistorie.

Der bevorzugte funktionale Name des historischen Bereichs lautet **„Abgeschlossene Alben“**. Der heutige Begriff **„Vitrine“** bleibt als Legacy-Begriff dokumentiert. Er kann später ein gestalterisches Präsentationskonzept bezeichnen, ist aber nicht zwingend der funktionale Bereichsname.

## 2. Verbindlicher Albumabschluss

Ein konkretes Albumexemplar gilt automatisch als erstmals abgeschlossen, sobald jeder zu seinem verbindlichen Stickerumfang gehörende Sticker mindestens einmal vorhanden ist.

Es gilt:

- kein manueller Button „Album abschließen“,
- keine zusätzliche Bestätigung,
- der erste Übergang von unvollständig zu vollständig ist der historische Abschluss,
- der Abschlusszeitpunkt beziehungsweise das Abschlussdatum bleibt dauerhaft erhalten,
- eine spätere Bestandsreduktion ändert den historischen Abschluss nicht,
- erneutes Erreichen von 100 Prozent erzeugt keinen zweiten Abschluss desselben Exemplars.

Aktueller Bestandszustand und historischer Abschluss sind zwei verschiedene fachliche Wahrheiten:

```text
aktueller Zustand
= heute vollständig oder heute unvollständig

historischer Abschluss
= dieses konkrete Exemplar war mindestens einmal vollständig
```

## 3. Genau einmal pro Exemplar

Der erstmalige Abschluss bildet genau einen historischen Sammlermoment pro Exemplar. Wiederholte Mengenänderungen, Retries, Bulk-Aktionen, Trade-Buchungen oder ein späteres erneutes Vervollständigen dürfen nicht erzeugen:

- einen zweiten historischen Abschluss,
- eine zweite identische Abschluss-Trophäe,
- ein zweites identisches Feed-Ereignis,
- ein neues oder verschobenes Erstabschlussdatum.

Diese Einmaligkeit muss fachlich an der Identität des konkreten Albumexemplars hängen, nicht nur am Albumtyp oder an einer UI-Session.

## 4. Das Album bleibt lebendig

Ein abgeschlossenes Album bleibt regulär unter den eigenen Alben vorhanden und vollständig benutzbar. Es wird weder in ein getrenntes Archiv verschoben noch stillgelegt.

Weiterhin erreichbar bleiben insbesondere:

- normales Album,
- Stickerwand,
- Stickerliste,
- Bestandspflege,
- Album-Trophäen,
- weiterhin zulässiger Tradepool für Doppelte.

Damit wird Audit 04 bestätigt: Das vollständige Album entwickelt sich vom Sammelwerkzeug zum Erinnerungsstück, bleibt aber ein lebendiges Album.

Zusätzlich darf dasselbe Exemplar im historischen Bereich „Abgeschlossene Alben“ erscheinen. Diese zweite Darstellung ist eine historische Projektion, keine zweite Albuminstanz und kein operatives Archiv.

## 5. Inhalt von „Abgeschlossene Alben“

Der Bereich enthält ausschließlich konkrete Alben beziehungsweise Exemplare, die mindestens einmal vollständig gesammelt wurden. Nicht hinein gehören:

- fast vollständige Alben,
- Favoriten allein wegen ihres Favoritenstatus,
- beliebige Showcase-Auswahl,
- aktuell vollständige Alben ohne belastbaren historischen Abschlussnachweis,
- operative Bestandskarten.

Eine Abschlusskarte benötigt grundsätzlich:

- Albumidentität,
- Status „Vervollständigt“,
- historisches erstmaliges Abschlussdatum.

Optional können später Albumcover oder kuratierte visuelle Albumidentität hinzukommen. Nicht Teil der Abschlusskarte sind:

- aktuelle Doppelte,
- aktuell verfügbare fehlende Sticker,
- aktuelle Missing-Zahlen,
- ein 100-Prozent-Fortschrittsbalken,
- andere operative Bestandskennzahlen.

Die Karte bleibt anklickbar und führt zum normalen Album. Sortiert wird nach dem historischen Erstabschlusszeitpunkt, neuester Abschluss zuerst.

## 6. Abschlussmoment, Trophy, Feed und Glocke

### Unmittelbarer Moment

Der erstmalige Abschluss ist ein besonderer, liebevoll inszenierter Sammlr-Moment. Er bleibt frei von XP, Leveln und überladener Gamification. Animation, Grafik und Microcopy gehören in die spätere UX-/Designarbeit.

### Abschluss-Trophäe

Beim selben erstmaligen Abschluss wird die dafür vorgesehene individuelle Album-Trophäe genau einmal freigeschaltet. Historischer Albumabschluss und Abschluss-Trophäe dürfen weder unterschiedliche Exemplare noch widersprüchliche Zeitpunkte oder Wiederholungszähler abbilden.

### Feed

Der erstmalige Abschluss ist ein starkes Feed-Ereignis, sinngemäß beispielsweise: „Valy hat FIFA World Cup 2026 vervollständigt.“ Es entsteht genau einmal aus demselben fachlichen Abschlussmoment. Finale Karte und Microcopy bleiben offen.

### Glocke

Der eigene Albumabschluss erzeugt keine zusätzliche Notification. Die handelnde Person erhält die unmittelbare Abschlussinszenierung; die Sammlerchronik gehört in den Feed. Das entspricht dem Notification-Vertrag aus Audit 10.

## 7. Eigene und fremde Profile

Abgeschlossene Alben gehören zur Sammleridentität und dürfen auf einem fremden **öffentlichen** Profil sichtbar sein. Bei einem **privaten** Profil ist der gesamte Bereich verborgen.

Die Darstellung darf keine privaten Bestände, Mengen, fehlenden Sticker, Doppelte oder andere Sammlungsdetails indirekt offenlegen. Die Abschlusskarte benötigt diese Daten ohnehin nicht.

Die Privacy-Grundrichtung ist verbindlich, ihre technische Vererbung noch nicht: Audit 08 fordert ein einfaches öffentliches/privates Profil-Gate, während S27 derzeit `public`, `friends` oder `private` pro Album plus separaten Tradepool speichert. Bis zur Cross-Audit-Konsolidierung wird nicht entschieden, ob und wie ein global öffentliches Profil und eine einzelne Albumfreigabe gemeinsam gelten.

## 8. Löschen eines abgeschlossenen Albums

Beim späteren Löschen eines bereits abgeschlossenen Albums soll der Nutzer entscheiden können, ob der historische Abschluss ebenfalls aus „Abgeschlossene Alben“ entfernt wird.

Zwei fachliche Ergebnisse müssen damit grundsätzlich möglich bleiben:

1. aktives Album entfernen, historischen Abschluss bewahren,
2. aktives Album und historischen Abschluss entfernen.

Die konkrete Lösch-UX, Datenhaltung und Wiederherstellbarkeit werden nicht festgelegt.

Ein offener Folgevertrag entsteht, wenn der historische Eintrag erhalten, das reguläre Album aber gelöscht wurde: Die allgemeine Regel „Abschlusskarte öffnet das normale Album“ besitzt dann kein aktives Ziel mehr. Ob eine historische read-only Ansicht, ein entfernter Link oder ein anderer Zielvertrag gilt, bleibt ausdrücklich offen.

Audit 12 legt für die Statistik fest, dass ein gelöschtes Album aus `Alben begonnen` und `Alben abgeschlossen` herausfällt. Audit 13 erlaubt dagegen optional den Erhalt seines historischen Abschlusses im Bereich „Abgeschlossene Alben“. Ob ein bewahrter historischer Eintrag trotz gelöschtem aktivem Album in die aggregierte Statistikzahl `Alben abgeschlossen` einfließt, ist nicht entschieden und muss in der Cross-Audit-Konsolidierung ausdrücklich aufgelöst werden.

## 9. Heutige Completion- und Vitrinenlogik

### Sammlung

`/sammlung` berechnet für jede aktuelle `user_albums`-Zuordnung die Zahl momentan vorhandener unterschiedlicher Sticker. Unvollständige Alben erscheinen unter „Aktive Alben“, momentan vollständige Alben ausschließlich unter „Vitrine“.

Die dort verwendete `album_card` zeigt auch in der Vitrine:

- aktuellen Fortschrittsbalken,
- `gesammelt / gesamt`,
- aktuelle Doppelte,
- aktuell verfügbare fehlende Sticker beziehungsweise fehlende Anzahl.

Der heutige Vitrinenbereich ist damit eine operative 100-Prozent-Bestandsprojektion, kein historischer Abschlussbereich. Er verschiebt vollständige Alben außerdem aus der Liste „Aktive Alben“ in einen eigenen Abschnitt, während der neue Vertrag sie regulär in der eigenen Sammlung belässt und zusätzlich historisch darstellt.

### Profil

`CollectorProfileService` setzt `completed=True`, wenn der aktuelle Inventory-Fortschritt `collected >= total` ist. `showcase_albums` beziehungsweise die gerenderte „Vitrine“ bestehen ausschließlich aus diesen momentan vollständigen Alben. Bei Bestandsreduktion wandert ein früher vollständiges Album zurück zu `active_albums`.

Die Profil-Vitrine zeigt nur den Albumtitel und ist anklickbar, besitzt aber weder historischen Abschlussstatus noch Abschlussdatum. Die Sortierung folgt Albumname/ID statt dem Erstabschlusszeitpunkt.

### Statistik

Auch `/statistik` zählt `Alben beendet` ausschließlich anhand des aktuellen Bestands. Audit 12 hat diese Kollision bereits als fehlende historische Abschlusswahrheit dokumentiert.

## 10. Heutige Trophy-Persistenz

Die aktuellen Trophy-Definitionen enthalten pro Albumtyp eine Bedingung `album_complete`, die dynamisch erfüllt ist, wenn der aktuelle Bestand den Albumumfang erreicht. Zahlreiche Sticker-, Bulk-, Listen- und Tradepfade vergleichen die dynamisch erfüllten Trophäen vor und nach einer Mutation und schreiben neue Namen in `unlocked_trophies`.

`unlocked_trophies` speichert:

- Nutzer,
- Albumtyp über `album_id`,
- Trophy-Namen,
- `unlocked_at`.

`UNIQUE(user_id, album_id, trophy_name)` und `INSERT OR IGNORE` verhindern heute eine zweite gleichnamige Abschluss-Trophy für denselben Nutzer und Albumtyp. Fällt der Bestand später und erreicht erneut 100 Prozent, bleibt die gespeicherte Zeile bestehen und wird nicht erneut als sichtbare neue Trophy zurückgegeben. Diese Einmaligkeit passt für das heutige Einzelexemplar-Modell grundsätzlich zum neuen Vertrag.

Die Trophy-Zeile ist dennoch kein verlässlicher allgemeiner Albumabschlussvertrag:

- sie identifiziert nur Albumtyp, nicht ein konkretes Exemplar,
- der Trophy-Name fungiert als technische Identität,
- die Erkennung ist über viele Route- und Trade-Callbacks verteilt,
- ein bereits erfülltes, aber noch nicht persistiertes Ziel kann bei einer späteren Mutation mit dem dann aktuellen Zeitstempel still nachgetragen werden,
- nicht jeder denkbare Bestandsimport oder zukünftige Schreibpfad ist zwangsläufig an dieselbe Erkennung gekoppelt,
- Abschluss, Trophy und Feed werden nicht atomar als ein gemeinsamer fachlicher Moment festgehalten.

Die heutige Trophy-Persistenz ist daher eine wertvolle historische Spur, aber nicht die kanonische Wahrheit des erstmaligen Albumabschlusses.

## 11. Evidenz aus dem lokalen Datenstand

Der geprüfte Datenstand enthält für Nutzer 1 und `em24` eine persistierte Trophy `Album vollendet` mit `unlocked_at = 2026-07-01 15:57:30`. Der aktuelle Bestand umfasst dagegen nur 709 von 728 unterschiedlichen Stickern.

Damit ist real belegt:

- eine Freischaltzeile kann die spätere Bestandsreduktion überleben,
- Sammlung, Profil und Statistik zeigen dasselbe Album heute nicht mehr als abgeschlossen,
- aktueller Fortschritt und historische Vollendung sind bereits praktisch auseinandergefallen,
- das vorhandene Trophy-Datum ist ein historisches Indiz, aber mangels eigenständigem Abschlussobjekt nicht automatisch ein vollständig belastbarer Erstabschlussvertrag.

## 12. Feed- und Notification-Ist-Stand

Der aktuelle Home-Pfad ist weiterhin das operative S25-Home mit Aufgaben, laufenden Trades sowie Freunde-/News-Platzhaltern. Es gibt keine persistierte Feed-Entität und keinen Schreibpfad für Albumabschlussereignisse. `user_activity` aus S29 speichert, sofern das Schema verfügbar ist, nur einen groben letzten Aktivitätszeitpunkt und keine Sammlerereignisse.

Die aktuelle Trophy-Freischaltung kann ein lokales Session-Popup erzeugen. Sie erzeugt weder einen Albumabschluss-Feed-Eintrag noch eine Albumabschluss-Notification. Das Fehlen der Notification entspricht dem neuen Vertrag; Feed-Ereignis und besondere Abschlussinszenierung fehlen.

## 13. Albumlöschung im Ist-Code

Es gibt weiterhin keinen regulären Pfad zum Löschen eines einzelnen Albums. Die einzige produktive Löschung aller `user_albums`- und `unlocked_trophies`-Zeilen erfolgt im Rahmen der vollständigen Kontenanonymisierung und ist kein Album-Löschvertrag.

Darum existieren heute weder:

- die Wahl, einen historischen Abschluss zu bewahren oder zu entfernen,
- ein Zustand „aktives Album gelöscht, Abschlussgeschichte erhalten“,
- ein Zielvertrag für die bewahrte historische Karte,
- eine Löschkonsistenz zwischen Album, Inventory, Trophy, Statistik, Feed und Profil.

## 14. Was bereits zum neuen Vertrag passt

- Vollständigkeit wird automatisch aus mindestens einem Exemplar jedes Stickers erkannt; es gibt keinen manuellen Abschlussbutton.
- Audit 04 hält vollständige Alben benutzbar und den Tradepool für Doppelte offen.
- `unlocked_trophies` bewahrt eine Abschluss-Trophy trotz später sinkendem Bestand.
- der heutige Unique-Vertrag verhindert im Einzelexemplar-Modell die identische Trophy-Dopplung.
- Audit 08 versteht abgeschlossene Alben als Teil der Sammleridentität.
- Audit 09 klassifiziert Albumabschluss als feedwürdig.
- Audit 10 schließt eigene Albummeilensteine und Trophy-Unlocks aus der Glocke aus.
- Audit 11 verlangt eine dauerhafte individuelle Albumabschluss-Trophy.
- Audit 12 trennt aktuellen Bestand vom historischen ersten Abschluss und benötigt diesen Zeitpunkt für die Sammeldauer.

## 15. Konflikte und Legacy-Verträge

| Bestand | Konflikt oder Legacy-Einordnung |
|---|---|
| Sammlung: „Vitrine“ aus aktuellem `100 %` | keine historische Wahrheit; frühere Abschlüsse verschwinden bei Bestandsrückgang |
| Sammlung: vollständige Alben nicht mehr unter „Aktive Alben“ | Spannung zum regulären Verbleib aller eigenen Alben; genaue neue Sammlungshierarchie bleibt UX-offen |
| Vitrinenkarte verwendet normale operative Albumkarte | Fortschritt, Doppelte und Missing/Marktwerte widersprechen der reduzierten Abschlusskarte |
| Profil/S26: `showcase_albums` aus aktuellem Fortschritt | historischer Abschlussstatus und Datum fehlen |
| Profilbegriff „Vitrine“ | funktionaler Legacy-Begriff; „Abgeschlossene Alben“ ist bevorzugt |
| Statistik: `Alben beendet` aus aktuellem Fortschritt | kann nach Bestandsreduktion sinken und kennt keinen ersten Abschluss |
| Trophy als einzige Abschlussindikation | Name statt stabiler Abschluss-/Trophy-Identität; verteilte Erkennung; keine Exemplarzuordnung |
| Home S25 | besitzt keinen Sammlerfeed und kein Abschlussereignis |
| S27-Albumprivacy | kollidiert noch mit dem einfachen öffentlichen/privaten Profil-Gate |
| Audit 12: gelöschtes Album zählt nicht mehr | Verhältnis zu einem in Audit 13 optional bewahrten historischen Abschluss ist offen |

## 16. Minimal benötigte historische Fachinformation

Damit Abschlussdatum, Trophy und Feed dauerhaft konsistent aus demselben Moment hervorgehen können, muss später mindestens zuverlässig feststehen:

- welches konkrete Albumexemplar abgeschlossen wurde,
- welchem Nutzer und Albumtyp dieses Exemplar gehört,
- wann es erstmals vollständig wurde,
- dass dieser Erstabschluss bereits verarbeitet wurde,
- welche genau eine Abschluss-Trophäe und welches genau eine Feed-Ereignis zu diesem Abschluss gehören beziehungsweise daraus dedupliziert werden,
- ob der historische Abschluss nach Löschung des aktiv verwalteten Exemplars bewahrt oder entfernt wurde.

Ob diese Fakten als Felder, eigenes Abschlussobjekt, Domain-Event oder Kombination gespeichert werden, ist nicht entschieden. Ebenso offen bleiben Transaktionsgrenze, Backfill, Migration, Retention und Verhalten bei bereits vorhandenen Trophy-Indizien.

## 17. Konsequenzen für zukünftige Mehrfachexemplare

Das aktuelle Datenmodell bildet faktisch höchstens ein Exemplar je Nutzer und Albumtyp ab:

- `UNIQUE(user_id, album_id)` in `user_albums`,
- Inventory-Zeilen adressieren `user_id + album_id + sticker_code`,
- Routen adressieren `/album/<album_id>`,
- Trophäen adressieren `user_id + album_id + trophy_name`,
- Privacy und Profilprojektionen hängen an derselben typbezogenen Zuordnung.

Die vorhandene numerische `user_albums.id` wird im Produktcode nicht als durchgängige Exemplaridentität verwendet und ist allein noch kein Mehrfachexemplar-Vertrag.

Spätere Mehrfachexemplare benötigen fachlich eine stabile Identität je konkretem Exemplar. Abschluss, Erstabschlusszeitpunkt, Inventory, Trophy, Profilkarte, Löschentscheidung und Albumziel müssen sich auf diese Identität beziehen können. Der Albumtyp bleibt separat für Katalog, Name, Cover und gemeinsame Definitionen relevant.

Der gemeinsame Tradepool aus Audit 04 darf Bestände mehrerer Exemplare aggregieren, ohne deren historische Abschlüsse zusammenzulegen. Zwei vollständig gesammelte Exemplare desselben Albumtyps dürfen zwei Abschlussgeschichten erzeugen; erneutes Vervollständigen desselben Exemplars weiterhin nur eine.

Dieses Audit legt weder konkrete Keys, Tabellen, Foreign Keys, URL-Struktur, Aggregationslogik noch Migration fest. Es dokumentiert nur, dass eine rein typbezogene Abschlussidentität das beschlossene Mehrfachexemplar-Modell verbauen würde.

## 18. Bewusst vertagte UX- und Architekturfragen

Offen bleiben:

- konkrete Abschlussanimation, Grafik, Sound und Microcopy,
- endgültige Gestaltung und Platzierung von „Abgeschlossene Alben“,
- Vitrine als mögliches rein gestalterisches Konzept,
- Cover beziehungsweise kuratierte visuelle Albumidentität,
- Privacy-Vererbung zwischen Profil-Gate und Albumfreigabe,
- Löschdialog und genaue Bedeutung der beiden Löschoptionen,
- Ziel einer bewahrten Abschlusskarte ohne aktives Album,
- Statistikzählung eines bewahrten Abschlusses nach Albumlöschung,
- technische Speicherungform und atomare Orchestrierung des Abschlussmoments,
- Umgang mit bestehenden Trophy-Zeilen und möglichem Backfill,
- Katalogversion beziehungsweise Umfang, gegen den ein historischer Abschluss nach späteren Katalogänderungen gilt,
- konkrete Exemplar-Keys, Relationen, URLs und gemeinsamer Tradepool.

## 19. Abschluss des Product Audits 01–13

Mit Audit 13 sind die wesentlichen Produktbereiche des aktuellen Post-RC-Stands ausreichend beschrieben, um keinen weiteren Product Audit automatisch zu starten.

Der empfohlene nächste Schritt ist eine **Cross-Audit-Konsolidierung / Closed-Beta-Bauplan**. Sie soll Audits 01–13 gegeneinander prüfen, Konflikte und Legacy-Verträge bündeln, offene Product-Owner-Entscheidungen sichtbar machen, technische Abhängigkeiten erkennen und Closed-Beta-Muss / Danach / Später trennen. Diese Konsolidierung ist ausdrücklich noch nicht Bestandteil dieses Audits.
