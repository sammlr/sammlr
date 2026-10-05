# BORSE-UI-01 — Börseneingang

## Status: visuell abgenommen mit dokumentiertem kanonischem Bestandsfehler

Die Anforderungen „identische Wall-Geometrie einschließlich Mengenbubble“ (§4) und „Mengenbubble überlappt nicht die Stickernummer“ (§12) sind für vorhandene kanonische Karten nicht gleichzeitig erfüllbar. Bei375px und Sticker116 überschneidet sich die kreisförmige Bubble mit den tatsächlichen SVG-Ziffernpfaden. Diagnose:139 getroffene Abtastpunkte im0,5px-Raster, identisch auf der echten produktiven Wall und der Trade-Karte. Nicht nur deren transparente SVG-Bounding-Box überschneidet sich. Screenshots und maschinenlesbarer Nachweis liegen in bubble-conflict.json und bubble-wall-116.png / bubble-trade-116.png.

Der Nutzer hat BORSE-UI-01 ausdrücklich unter diesem bekannten Bestandsfehler visuell abgenommen. Die Bubble-Überschneidung blockiert BORSE-UI-01 nicht mehr. Keine Trade-spezifische Korrektur: Die Mengenbubble wird später separat an der kanonischen Stickerkarte korrigiert, sodass die Korrektur überall gilt. Der aktuelle Implementierungsstand bleibt zur Begehung unverändert. Kein Commit, Push oder Deploy.

Die bisherigen Prüfartefakte bleiben als Nachweis des damaligen Testzeitpunkts unverändert, einschließlich ihrer damaligen Pending-Markierungen. Die anschließende Nutzerabnahme ist in `tests/research/artifacts/borse-ui01/acceptance.json` dokumentiert; sie behauptet keine technische Behebung oder einen bestandenen Überlappungsfreiheitstest.

## Ausgangspunkt / Scope

HEAD89c957de0b3ab9f412c6d8f6648cb00f3184a051; drei vorhandene uncommittete Shell-Dateien aus01A/01A.1 als Ausgangspunkt gesichert. Frühere lokale/ungetrackte Audits, Tests, Screenshots und Designbestände unverändert belassen. Keine neue Domainphase. Vorher-Screenshot390px zeigt den tatsächlich vorhandenen72px-Stand.

Berücksichtigt: bestehende Integration-/01A-/01A.1-Audits, kanonischer Wall-Renderer und Styles sowie TRADE-11 sticker_physics.js, physics11.css und receive_motion.js. Aktuelle Datenkette bleibt SmartDealPlanningService → SmartDealPairwiseService → SmartDealOptimizer; keine Änderungen an diesen Services, Rankings, Inventardaten oder Tradeverträgen.

## Kanonische Geometrie

Quelle: App/webapp.py `sticker_wall_slot_html` / `sticker_wall_card_inner` und App/static/style.css, insbesondere `.s30-album-page .wall`, `.sticker-slot-frame`, `.sticker-wall-stack-layer`, `.slot`, Retro-Ziffern und `.sticker-qty`.

| Viewport | Kartenbreite | Kartenhöhe | Drei vollständige10-Layer-Stapel ohne Zwischenraum |
| --- | --- | --- | --- |
|375|103px|117,406px|363px|
|390|108px|123,109px|378px|
|430|118,656px|135,266px|409,968px|
|1280|96,1719px|109,625px|342,5157px|

Alle drei vollständigen Stapel passen in die verfügbare Breite. Auf375/390 ist seitliche Luft zwangsläufig knapp. Kein Skalieren, kein Croppen und keine überlappenden Stapel als Ausweg.20px Rasterabstand zwischen Kartenankern umfasst den18px Layerzuwachs plus kleinen sichtbaren Zwischenraum. Rotation−0,15° /0° /+0,15°. Geometrische Gruppenmitte geprüft, alle Faces innerhalb der Bühne und keine horizontalen Overflows.

Sondergröße72×82,08px und28px-Sonderziffern entfernt. Ein unsichtbarer aria-hidden Messbereich verwendet die echten produktiven `.card.sticker-wall-card > .wall`-Styles. Seine tatsächliche Rasterbreite steuert alle Shell-Karten, unabhängig von Vorschlagsanzahl und geöffnetem Zustand. Höhe, Seitenverhältnis, Innenabstände, Ziffern, Mengenbubble und Layer-Geometrie kommen wieder aus den kanonischen Styles. Kein fixer Trade-Größenersatz.

Reine Darstellungsanpassung in App/trade_shell.py: Bei Menge>1 erhält der wiederverwendete Renderer wie auf der Wall den Zustand `duplicate`, sonst `owned`. Dadurch gilt auch die kanonische24px-Mengenbubble statt der vorher abweichenden Owned-Pill. Mengen, Auswahl und Daten bleiben identisch. Genau dadurch wird der bestehende kanonische Bubble-Konflikt sichtbar; er wird nicht durch eine neue Sondergeometrie versteckt.

## Information und Interaktion

0/1/2/3 echte Vorschläge mit korrektem Singular/Plural; keine Auffüllung. Unter dem Stapel nur Name und „X Sticker · Y Alben“. Name verlinkt auf vorhandenes /tauschen/sammlr/<id>. Keine Albumlisten, Bewertungen oder sonstigen Metadaten im geschlossenen Eingang.

Normales Aktivieren des Stapels lädt ausschließlich die vorhandene authentifizierte GET-Dealroute. Aus ihrem serverseitig kanonisch gerenderten HTML werden die tatsächlichen Receive-/Give-Albumgruppen übernommen. Kein neuer Endpunkt, kein zweiter Matching-/Gruppierungsalgorithmus, keine Previewdaten. Kontrollierter Fehlerzustand bei404 oder Loginredirect; keine Fake-Erfolgsansicht. Ohne JavaScript sowie bei modifiziertem Linkklick bleibt die bestehende direkte Dealnavigation erhalten.

Gesamtstapel → tatsächliche Albumstapel → einzelne Sticker. Die gewählte Erkundung ersetzt vorübergehend die Vorschlagsreihe. „Zurück zu Vorschlägen“ stellt Reihe und Fokus wieder her. Kleine Aktion „Tausch ansehen“ erscheint erst in der geöffneten Erkundung und führt in die vorhandene Dealansicht. Albumgruppen bleiben einzeln bedienbar; bestehende Dealaktionen Alle anzeigen/Zusammenlegen funktionieren.

Produktionsadapter des TRADE-11-FLIP-Prinzips:440ms, cubic-bezier(.22,.7,.25,1), vorhandene Faces als nichtinteraktive/aria-hidden Flugkopien, ausschließlich Translation, kein Scale. Beim Öffnen beider Stufen geprüft. Reduced Motion überspringt Animationen; laufende Kopien werden bei Resize/Scroll/Medienwechsel aufgeräumt. Kein Import der Preview-Runtime.

Ruhige transparente Shell-Fläche, keine neue Tisch-/Papier-/Post-it-Metapher und keine einzelnen Vorschlags-Cards. Alle Sammlr bleibt /tauschen/sammlr. Meine Anfragen bleibt deaktiviert, weil keine semantisch passende integrierte Trade-v2-Zielroute vorhanden ist. /tauschen/laufend unverändert, ohne Einstieg auf dem Hauptscreen.

## Tests und Schutz

- 16 Browserfälle:0/1/2/3 Vorschläge ×375/390/430/1280.
- Kanonische Kartenmaße, Padding, Radius, Border, Proportionen und Bubblemaße mit der echten Wall verglichen. Geometrie bleibt während Animation und in Album-/Einzel-/Dealzuständen konstant.
- Keine horizontalen Overflows, keine Überschneidung der geschlossenen Stapel, geometrische Mitte, Wording und tatsächliche Albumgruppen geprüft.
- Touch/Maus/Enter, beide Auffächerstufen, Dealnavigation, Rückkehr, Reduced Motion und fehlender Deal geprüft. Keine JS-Fehler oder Schreibrequests.
- Bubble-Überlappungsfreiheit **nicht bestanden**, da kanonischer Bestandsfehler; ausdrücklich separat erfasst, nicht als grünes Gate ausgegeben.
- 1.303 produktive Regressionstests und8 separate Preview-Isolationstests bestanden. Zwölf vorbestehende R5-Klassifizierungen unverändert; keine neuen Ausschlüsse.
- Alle15 geschützten lokalen DBs per Vorher-/Nachher-SHA256 bytegleich. Neue synthetische SQL-Fixtures ausschließlich unter/private/tmp. Testserver prüft nach jeder Response Bytegleichheit der vier synthetischen Fixture-DBs. Keine privaten Daten verwendet.
- App/webapp.py, App/static/style.css, Domainservices, Verträge, Legacy-Routen und App/trade_v2 bytegleich zum Arbeitsstand vor diesem Auftrag. Getrackte Änderungen ausschließlich Shell-Präsentation. Beide Diffchecks sauber; nichts gestagt.

## Reproduktion / BORSE-UI-02

Im isolierten Sourcebestand unter/private/tmp: `python -B tests/research/check_borse_ui01.py --serve` startet synthetischen Testserver18081. Ohne --serve läuft die UI-Matrix; `check_borse_ui01_bubble.py` dokumentiert den kanonischen Bestandskonflikt. Kein Fixture-Cookie oder Teststeuerung in produktiven Dateien. Vorhandene produktive App8080 und Preview8095 nicht gestartet/geändert.

Offen für spätere separate Aufträge: kanonische Bubble-Korrektur, sichere produktive Anfragenroute, Zentrale/Partnerpool-Weiterentwicklung. Die Übernahme des bestehenden Bubble-Fehlers für BORSE-UI-01 ist entschieden und freigegeben. Keine Umsetzung weiterer Domain-/Lifecycle-/Settings-Schritte. Der Bubble-Fix ist nicht stillschweigend Teil von BORSE-UI-02; dafür ist eine explizite Freigabe nötig.

## Exakte Dateien dieses Schritts

- `App/trade_shell.py`
- `App/templates/trade_shell.html`
- `App/static/trade_shell.css`
- `App/static/trade_shell.js`
- `App/static/trade_shell_motion.js`
- `tests/research/check_borse_ui01.py`
- `tests/research/check_borse_ui01_bubble.py`
- `docs/BORSE_UI_01_AUDIT.md`
- `tests/research/artifacts/borse-ui01/album-open-390.png`
- `tests/research/artifacts/borse-ui01/bubble-conflict.json`
- `tests/research/artifacts/borse-ui01/bubble-trade-116.png`
- `tests/research/artifacts/borse-ui01/bubble-wall-116.png`
- `tests/research/artifacts/borse-ui01/checks.json`
- `tests/research/artifacts/borse-ui01/home-1280-1.png`
- `tests/research/artifacts/borse-ui01/home-1280-2.png`
- `tests/research/artifacts/borse-ui01/home-1280-3.png`
- `tests/research/artifacts/borse-ui01/home-375-1.png`
- `tests/research/artifacts/borse-ui01/home-375-2.png`
- `tests/research/artifacts/borse-ui01/home-375-3.png`
- `tests/research/artifacts/borse-ui01/home-390-1.png`
- `tests/research/artifacts/borse-ui01/home-390-2.png`
- `tests/research/artifacts/borse-ui01/home-390-3.png`
- `tests/research/artifacts/borse-ui01/home-390-before.png`
- `tests/research/artifacts/borse-ui01/home-430-1.png`
- `tests/research/artifacts/borse-ui01/home-430-2.png`
- `tests/research/artifacts/borse-ui01/home-430-3.png`
- `tests/research/artifacts/borse-ui01/preview-unit-tests.txt`
- `tests/research/artifacts/borse-ui01/protection.json`
- `tests/research/artifacts/borse-ui01/release-tests.json`
- `tests/research/artifacts/borse-ui01/total-open-390.png`
- `tests/research/artifacts/borse-ui01/wall-geometry.json`
- `tests/research/artifacts/borse-ui01/acceptance.json`
