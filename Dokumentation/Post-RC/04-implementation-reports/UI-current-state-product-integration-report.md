# UI-Zwischenstand – Integration in die reguläre lokale App

**Stand:** 24. August 2026

**Status:** ABGESCHLOSSEN UND TECHNISCH ABGENOMMEN

**Reguläre lokale App entspricht dem aktuell freigegebenen UI-Zwischenstand:** JA

**Migration:** NEIN

**Nächster UIF-Block:** nicht begonnen

## 1. Integrationsumfang

UIF-001, UIF-002, Palette A aus UIF-002A und die freigegebene
UIF-002-Nacharbeit waren bereits im regulären Produktpfad vorhanden. Noch nicht
produktiv integriert waren die freigegebenen Visual-Concept-Richtungen für:

- UIF-003A: `sammlr.`-Home;
- UIF-004A: Tauschen einschließlich der letzten PO-Nacharbeit.

Diese beiden Richtungen wurden in die regulären Renderer und das reguläre
Stylesheet übernommen. Die normale Entwicklungsinstanz auf
`http://127.0.0.1:8080` ist die Abnahmeoberfläche; es wird kein Concept-Server
und keine Fixture-App als Produktansicht verwendet.

Nicht Teil der Integration waren Stickerwall, Sticker-`+/-`, Trophäen, Chat,
Community-Erweiterungen, Albumcover-Neugestaltung oder ein neuer UIF-Block.

## 2. Finaler Produktstand

### Sammlung

Die bereits produktive UIF-001/002-Sammlung bleibt unverändert Grundlage:
neutraler Header, Palette A, neue Albumcards, kompakter Favoritenstern und die
globale Bottom Navigation. Nur das tatsächlich gespeicherte Favoritenalbum ist
aktiv. Albumöffnung und Favoritenaktion verwenden weiterhin die bestehenden
Routen, CSRF-Prüfungen und Produktregeln.

### Home / `sammlr.`

Der reguläre `/`-Renderer verwendet jetzt die freigegebene UIF-003A-Hierarchie:

- neutraler Seiteneinstieg „Für dich“;
- ruhige Tauschchance ohne dekorative Statistikbox;
- reales Favoritenalbum mit bestehender Bestandsprojektion;
- reale Feed-Events ausschließlich aus dem bestehenden `FeedEventService`;
- kein künstlicher Feed-Platzhalter, wenn keine darstellbaren Events existieren.

Die Visual-Fixture `17` wurde nicht übernommen. Ohne freigegebene kanonische
Mengenprojektion bleibt die Aussage bewusst generisch. Es wurden keine
Feedlogik, Priorisierung oder Produktsemantik geändert.

### Tauschen

Der reguläre `/trades`-Renderer verwendet jetzt die freigegebene
UIF-004A-Richtung:

- Tabs `Tauschpartner | Trades | Anfragen`;
- partnerzentrierte Cards mit realen, gerichteten Bestandsmengen;
- kanonische Erfolgsprojektion für die Anzahl erfolgreicher Trades, soweit die
  aktuelle Profilprivacy diese Information zulässt;
- reale laufende Trades mit bestehendem Lifecycle-State und Detailroute;
- reale Anfragen und ein ruhiger Empty State ohne Visual Fixtures;
- kein Papier-/Kollegblock-Stil.

Matching, Tradepool, Lifecycle, Requests, Ratings, Privacy und alle Schreibwege
bleiben unverändert. Die zwischenzeitlich im Visual Concept gezeigte
`3 erhalten / 3 geben`-Anfrage wurde nicht in das Produkt übernommen.

### Globaler App-Shell

Header und Bottom Navigation stammen weiterhin aus dem freigegebenen
UIF-002-App-Shell. Auf `/` ist ausschließlich `sammlr.` aktiv, auf `/sammlung`
ausschließlich Sammlung und auf `/trades` ausschließlich Tauschen. Nebenrouten
erhalten keinen erfundenen Active State. Im Wide-State bleibt dieselbe Bottom
Navigation sichtbar; es wurde keine alternative Desktopnavigation eingeführt.

## 3. Geänderte Dateien

- `App/webapp.py` – produktive Home- und Tauschen-Projektion;
- `App/static/style.css` – freigegebene UIF-003A/UIF-004A-Strukturen und
  responsive Darstellung;
- `tests/test_s04_home_collection_routes.py`;
- `tests/test_cb012_feed_home_cutover.py`;
- `tests/test_s30_design_foundation.py`;
- `tests/test_s31_ui_foundation.py`;
- `tests/test_uif_current_state_product_integration.py` – neuer gezielter
  Integrationsvertrag;
- `Dokumentation/Post-RC/04-implementation-reports/UIF-003A-report.md`;
- `Dokumentation/Post-RC/04-implementation-reports/UIF-004A-report.md`;
- dieser Report.

Andere bereits vorhandene Working-Tree-Änderungen wurden nicht zurückgesetzt
oder fachlich verändert.

## 4. Tests

### Gezielte kombinierte Suite

Abgedeckt wurden insbesondere Home, Sammlung, Feed-Cutover, globaler App-Shell,
Navigation, Trade-Matching, Trade-Lifecycle, Requests, Privacy, Ratings,
Design Foundation und die neue Produktintegration.

**Ergebnis:** 246/246 Tests, 0 Fehler, 0 Skips.

### Vollregression

Aufruf mit expliziter Testing-Konfiguration und Package-Discovery:

```text
SAMMLR_ENV=testing \
SAMMLR_SECRET_KEY=sammlr-explicit-testing-secret \
PYTHONWARNINGS='ignore::ResourceWarning' \
.venv/bin/python -m unittest discover
```

**Ergebnis:** 736/736 Tests, 0 Fehler, 0 Skips.

## 5. Responsive- und Browser-Smoke

Geprüft wurde die reguläre Produktinstanz auf Port 8080 im normalen Safari,
nicht ein WebDriver-/Concept-Fenster. Die Fenster-/Viewportbreiten wurden über
die Safari-Accessibility-Geometrie kontrolliert.

| Breite | geprüfte Produktansicht | Ergebnis |
|---:|---|---|
| 336 px | Tauschen / Tauschpartner | Tabs, Header und Navigation vollständig sichtbar; keine sichtbare horizontale Überbreite |
| 390 px | Home, Sammlung und Tauschen | Cards und Navigation innerhalb des Fensters; korrekter Active State |
| 430 px | Home | mobile Hierarchie vollständig innerhalb des Fensters |
| 1180 px | Home | freigegebene Zweispaltenkomposition und dieselbe Bottom Navigation vollständig sichtbar |

Die vorhandenen UIF-002-Endcontent-Inset-Regeln blieben unverändert und werden
durch die UIF-/Shell-Regressionen abgesichert. Bei den visuellen Smokes wurde
kein abgeschnittener Endcontent und kein unsichtbares Overlay gefunden. Die
Bottom Navigation blieb anklickbar. Die produktive Sammlung ist für die
PO-Prüfung bei 390 px geöffnet und wurde mit einem Hard Reload aktualisiert.

Safari Remote Automation blieb deaktiviert. Deshalb wurde in diesem Lauf kein
neuer JavaScript-DOM-Messwert für `document.scrollWidth` erhoben; die Prüfung
erfolgte über die exakten Fensterbreiten, vollständige Browseransichten und die
gezielten CSS-/Routing-Regressionen. Es wurde kein gegenteiliger Overflow-
Befund beobachtet.

## 6. Datenbank und Safety

Bestätigte Ausgangsbaseline aus den vorausgehenden UIF-Abnahmen:

`3ccaff9ca4b4140ab9338c23f486f57e0ae253605f79c47f03a79f46dafa9df4`

Während der Arbeit änderte sich die laufende Bestands-DB durch eine zeitgleiche
reale Domainaktion am 24. August 2026 um 18:41:38 UTC. Read-only geprüft wurden:

- `trade_requests.id = 37`, Smart-Tauschanfrage von Nutzer 1 an Nutzer 2;
- `notifications.id = 116`, `smart_trade_request_created` für Nutzer 2;
- identischer Erstellungszeitpunkt beider fachlich zusammengehöriger Zeilen.

Diese Zeilen wurden weder von der UI-Integration noch von deren Tests erzeugt.
Es wurde nichts gelöscht oder restauriert. Die Abweichung wird deshalb nicht
als unveränderte neue Produktbaseline behauptet, sondern als transparente
parallele Bestandsaktivität dokumentiert.

| Prüfung | Ergebnis |
|---|---|
| Schema Bestands-DB | V7, unverändert; keine Migration |
| SHA-256 nach paralleler Domainaktion | `e74a8f5bd495959f1ff91142294f8f401286066b5efab1f0e72d372277f5c265` |
| beabsichtigte DB-Änderung durch Integration | NEIN |
| `PRAGMA integrity_check` | `ok` |
| `PRAGMA foreign_key_check` | leer |
| `git diff --check` | ohne Befund |

## 7. Laufende reguläre Instanz

Der zuvor auf Port 8080 laufende, vor dem aktuellen Working-Tree-Stand
gestartete Flask-Prozess wurde kontrolliert beendet. Port 8080 wird nun durch
den regulären virtuellen Python-Interpreter aus diesem Working Tree mit
`App/webapp.py` bedient. Der normale Safari zeigt
`http://127.0.0.1:8080/sammlung` bei 390 px nach Hard Reload und bleibt dort für
die freie PO-Navigation geöffnet.

## 8. Abschluss

- Reguläre lokale App entspricht dem aktuell freigegebenen UI-Zwischenstand:
  **JA**.
- Produktlogik geändert: **NEIN**.
- Migration ausgeführt: **NEIN**.
- Bestands-DB durch diese Integration verändert: **NEIN**.
- Visual Fixtures produktiv übernommen: **NEIN**.
- Neuer UIF-Block begonnen: **NEIN**.
- Commit/Push: **NEIN/NEIN**.
