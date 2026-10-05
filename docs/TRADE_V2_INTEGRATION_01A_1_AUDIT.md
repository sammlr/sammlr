# INTEGRATION-01A.1 — feste kompakte Trade-Karte

Die ausdrückliche Nutzerkorrektur ersetzt die Wall-Größenparität für die produktive Trade-Shell. Produktive Stickerwall, Domain-/Read-Services, Matching und Legacy bleiben unverändert. Kein Commit, Push oder Deploy.

## Größenvertrag und Darstellung

Feste CSS-Kartenmaße 72×82,08px, unabhängig von Viewport oder Vorschlagsanzahl. Derselbe Token gilt für Topvorschläge, geschlossene Albumstapel, aufgefächerte Sticker und beide Give-/Receive-Richtungen im produktiven Deal. Keine scale-Transformation; Wall-Messprobe und dynamische Übernahme der Wall-Breite entfernt. Layer-Richtung, −2/−2-Versatz, Face-Struktur und z-index bleiben unverändert, Wall-Cap5/Trade-Cap10 ebenfalls. Zifferngröße lokal auf28px für die kompakte Trade-Karte; keine globalen Fontänderungen.

Die tatsächlich vorhandene TRADE-11-Preview misst weiterhin die responsive Wall; sie enthält keinen festen kompakten Referenzwert.72×82,08px ist daher der hier bewusst neu definierte Trade-Präsentationswert gemäß Nutzerfreigabe, keine angeblich aus TRADE-11 extrahierte Konstante. Die historische Preview bleibt unverändert. Frühere Wall-Paritätsnachweise in INTEGRATION-01/01A dokumentieren frühere Zustände und gelten für die Shell nicht mehr.

Milchglas-Tisch bleibt bestehen, 30px Abstand zwischen den festen Kartenplätzen,54px oberer/40px unterer Innenabstand. Die ganze tatsächliche physische Gruppe wird mittig ausgerichtet; keine unsichtbaren freien Vorschlagsplätze. Subtile deterministische Rotation. Unter den Stapeln nur Sammlername und X ↔ X. Albumanzahl und Albumliste dort entfernt, Dealinhalt unverändert. Dynamisches Wording für0/1/2/3 bleibt. Meine Anfragen weiterhin deaktiviert, da keine neue passende produktive Route integriert ist.

## Prüfung

- 16 Browserfälle:0/1/2/3 Vorschläge ×375/390/430/1280px mit maximal10 sichtbaren Lagen.
- Alle Top-/Album-/Fan-/Receive-/Give-Karten auf72×82,08px geprüft (Browser-Subpixelrundung unter0,02px toleriert).
- Physische Gruppenmitte unter0,1px Abweichung; alle sichtbaren Kartenflächen vollständig innerhalb des Tisches, mindestens8px Randabstand; kein horizontaler Overflow.
- Produktive Wall vor/nach Navigation unverändert gemessen.
- Dealnavigation per Touch, unabhängiges Öffnen per Enter, alle öffnen, alle schließen, Reduced Motion, keine JS-Fehler oder mutierenden Requests.
- 1.303 produktive Regressionstests plus8 separat ausgeführte Preview-Isolationstests grün. Die zwölf vorbestehenden R5-Testklassifizierungen bleiben unverändert; keine neuen Ausschlüsse.
- Alle15 geschützten lokalen DBs SHA256-identisch gegenüber vorher; keine private DB für Tests geöffnet/kopiert. Fixtures ausschließlich neu aus SQL unter /private/tmp. Testserver prüft nach jeder Response Bytegleichheit aller synthetischen Fixtures.
- App/webapp.py, App/trade_shell.py und App/static/style.css bytegleich zum Commit89c957d. Git-Diffcheck sauber.

Testscript: tests/research/check_integration01a1.py. Ausführung wie01A im isolierten Sourcebestand /private/tmp/integration01-tests: mit --serve synthetischen Server auf18081 starten, ohne --serve Browsermatrix ausführen. Keine Fixture-Steuerung in produktiven Routen.

## Dateien dieses Schritts

Geändert (auf dem noch uncommitteten01A-Stand):

- App/templates/trade_shell.html
- App/static/trade_shell.css
- App/static/trade_shell.js

Neu:

- tests/research/check_integration01a1.py
- docs/TRADE_V2_INTEGRATION_01A_1_AUDIT.md
- tests/research/artifacts/integration-01a1/checks.json
- tests/research/artifacts/integration-01a1/deal-open-390.png
- tests/research/artifacts/integration-01a1/home-1280-1.png
- tests/research/artifacts/integration-01a1/home-1280-2.png
- tests/research/artifacts/integration-01a1/home-1280-3.png
- tests/research/artifacts/integration-01a1/home-375-1.png
- tests/research/artifacts/integration-01a1/home-375-2.png
- tests/research/artifacts/integration-01a1/home-375-3.png
- tests/research/artifacts/integration-01a1/home-390-1.png
- tests/research/artifacts/integration-01a1/home-390-2.png
- tests/research/artifacts/integration-01a1/home-390-3.png
- tests/research/artifacts/integration-01a1/home-430-1.png
- tests/research/artifacts/integration-01a1/home-430-2.png
- tests/research/artifacts/integration-01a1/home-430-3.png
- tests/research/artifacts/integration-01a1/preview-unit-tests.txt
- tests/research/artifacts/integration-01a1/protection.json
- tests/research/artifacts/integration-01a1/release-tests.json
