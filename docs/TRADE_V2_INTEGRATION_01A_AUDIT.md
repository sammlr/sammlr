# INTEGRATION-01A — Startscreen Tauschbörse

Ausgangspunkt: 89c957de0b3ab9f412c6d8f6648cb00f3184a051. Ausschließlich Präsentation von /tauschen geändert. Kein Commit, Push oder Deploy.

## Ergebnis

0/1/2/3 vorhandene Vorschläge, korrekte Zahl und Singular/Plural, sachlicher Leerzustand. Ranking, Auswahl und Read-Daten unverändert. Gemeinsame Milchglasfläche statt weißem Dashboard-Container; keine einzelnen Sammler-Cards. Sichtbare physische Gruppe einschließlich kanonischer Layer-Versätze geometrisch zentriert, auch bei einem oder zwei Vorschlägen. Rotation deterministisch −0,35° / +0,05° / +0,35°. Nur Name, X ↔ X und Albumanzahl unter jedem Stapel. Stapel und Name führen unverändert zum vollständigen Deal.

Milchglas-Rezept aus der bestehenden `.sticker-filter-row` in App/static/style.css: rgba(255,255,255,.70), weiße transparente Border, vorhandener Außen-/Innenschatten, blur(18px) saturate(1.25). Im Shell-CSS lokal wiederverwendet; Originalstyle unverändert. Flächenbreite/Abstände dienen der Aufnahme der unverkleinerten Karten. Keine Skalierung und keine Änderungen an Face, Layer-Versatz, Richtung, z-index oder Cap.

Kartenmaß wird weiterhin aus einem echten kanonischen Wall-Raster gemessen. Auf dem Startscreen dient ein unsichtbarer, nicht interaktiver und aria-hidden Wall-Messbereich dazu, die Messung von der Anzahl der Vorschläge zu entkoppeln. Flex-Gruppe enthält ausschließlich die tatsächlich vorhandenen Vorschläge. Die geometrische Zentrierung misst die realen Face-/Layer-Außenkanten; sie verändert nur die Position der gesamten Gruppe.

## Navigation und offene Zielroute

Unter der Fläche ausschließlich „Alle Sammlr“ und „Meine Anfragen“. Alle Sammlr bleibt /tauschen/sammlr. Meine Anfragen ist ein deaktivierter Button: Noch keine semantisch passende, eigenständig produktiv integrierte Trade-v2-Anfragenroute vorhanden. /tauschen/laufend enthält offene und angenommene Vorgänge und wird nicht umbenannt. Der Legacy-Anfragenbereich wird ebenfalls nicht stillschweigend als neue Trade-v2-Route eingesetzt. Keine Fake-Daten oder neue Persistenz.

/tauschen/laufend bleibt unverändert erreichbar; lediglich sein Startscreen-Link entfällt. Partnerpool, Dealansicht, Auffächerlogik und sämtliche Lifecycle-Routen bleiben unverändert.

## Spätere Sammlr-Zentrale — nur dokumentiert

Die Zentrale soll nach Annahme der operative Bereich werden: grüner Post-it = Eingang / was der Nutzer bekommt; gelber Post-it = To-do / aktiv zu erledigen; roter Post-it = Ausgang / was der Nutzer versendet. Laufende Tausche, Packaufgaben, eingehende/ausgehende Sendungen und abgeschlossene Vorgänge sollen dort später organisiert werden. Hier nicht implementiert.

## Abnahme

16 Browserfälle: 0/1/2/3 Vorschläge × 375/390/430/1280px. Alle bestanden, auch mit zehn sichtbaren Layern bei jedem Vorschlag. Geprüft: korrekter Text, Kartenanzahl, tatsächliche Gruppenmitte (Abweichung <0,1px), vollständige physische Containment mit mindestens8px Randabstand, kein horizontaler Overflow, korrekte Dealnavigation per Touch, Partnerlink, deaktivierter Anfragenbutton, kein Laufende-Tausche-Einstieg, keine Albumlisten. Keine Browserfehler oder mutierenden Requests. Screenshots mit ausschließlich synthetischen Nutzern.

Kartenmaße Wall = Startscreen (CSS-Pixel, unabhängig von Vorschlagsanzahl):

| Viewport | Breite | Höhe |
| --- | --- | --- |
| 375 | 103px | 117.406px |
| 390 | 108px | 123.109px |
| 430 | 118.656px | 135.266px |
| 1280 | 96.1719px | 109.625px |

1.303 produktive Release-/Integrationstests bestanden, keine Fehler oder Skips. Zwölf bereits zuvor klassifizierte historische/Baseline-Tests gemäß unverändertem R5_TEST_CONTRACT nicht im Release-Gate; keine neuen Ausschlüsse. Bestehende Wall-Cap5/Trade-Cap10-Tests enthalten. Preview/Domain-Code unverändert; keine neue Preview-Regression behauptet.

Testumgebung ausschließlich isolierter Sourcebestand /private/tmp/integration01-tests; neue SQL-generierte synthetische DBs unter /private/tmp. Testserver prüft nach jeder Response Bytegleichheit aller vier Fixtures. Alle15 geschützten lokalen DBs per SHA256 gegenüber vorher bytegleich. Keine echte DB für Tests geöffnet, kopiert oder verändert. App/trade_shell.py, App/webapp.py, App/static/style.css, Domainservices, Preview und Legacy-Code unverändert. git diff --check sauber.

Reproduktion: im isolierten Sourcebestand `python -B tests/research/check_integration01a.py --serve` auf127.0.0.1:18081 starten, dann in zweitem Terminal `python -B tests/research/check_integration01a.py`. Der synthetische Fixture-Cookie existiert ausschließlich im Testserver, niemals in produktivem Code. Release-Gate wie INTEGRATION-01 mit SQL-generierter S00-Fixture und SQLite-Pfadguard ausgeführt.

## Exakte Dateien

- `App/templates/trade_shell.html`
- `App/static/trade_shell.css`
- `App/static/trade_shell.js`
- `tests/research/check_integration01a.py`
- `docs/TRADE_V2_INTEGRATION_01A_AUDIT.md`
- `tests/research/artifacts/integration-01a/checks.json`
- `tests/research/artifacts/integration-01a/home-1280-3.png`
- `tests/research/artifacts/integration-01a/home-390-0.png`
- `tests/research/artifacts/integration-01a/home-390-1.png`
- `tests/research/artifacts/integration-01a/home-390-2.png`
- `tests/research/artifacts/integration-01a/home-390-3.png`
- `tests/research/artifacts/integration-01a/protection.json`
- `tests/research/artifacts/integration-01a/release-tests.json`
