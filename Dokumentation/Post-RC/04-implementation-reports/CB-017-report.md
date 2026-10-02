# CB-017 – Integrierter Closed-Beta-RC-Nachweis

**Stand:** 21. August 2026
**Status:** ABGESCHLOSSEN – technisch abgenommen
**P1-Gesamtstatus:** 17/17 Kernblöcke abgeschlossen
**Migration:** NEIN in der echten Bestands-DB; Upgradeprobe ausschließlich auf Kopien
**Echte Bestands-DB verändert:** NEIN

## 1. Ergebnis

CB-017 bestätigt, dass die in CB-001 bis CB-016 einzeln abgenommenen
Produktverträge auch integriert funktionieren. Alle sechs Closed-Beta-Gates
sind grün. Es gibt keinen offenen P0 und keine ungeklärte P1-Abweichung.

Der reale 390-px-Safari-Smoke fand drei sichtbare Overflow-Ausprägungen mit
zwei eng begrenzten CSS-Ursachen. Diese wurden ohne Produkt-, Feed-,
Navigations- oder Datenlogikänderung minimal korrigiert und anschließend im
echten Browser sowie in beiden vollständigen Regressionen erneut geprüft.

CB-017 schließt den P1-Produktvertrag ab. Es ist ausdrücklich **keine**
Freigabe für externe Closed-Beta-Nutzer: Laut Post-RC-Masterplan folgen noch
Engineering Hardening, realistische Mehrnutzer-Simulation und das finale
Closed-Beta-Gate.

## 2. Vollständige Gate-Matrix

| Gate | Nachweis | Ergebnis |
|---|---|---|
| 1 – Data Contract | CB-001–005, Migration/Idempotenz, Completion/Trophy/Feed, `em24` | GRÜN; 60 Tests |
| 2 – Trade Core | CB-008/010/011, Inventory, Reservation, Shipping, Receipt, Problem, Rating | GRÜN; 329 Tests |
| 3 – Product Projections | CB-007/009/012–016, Feed, Inbox, Collection, Profile, Statistics | GRÜN; 109 Tests |
| 4 – Privacy/Auth | CB-006, S03/S07/S27/S29/S32/S33/S35/S36, direkte und manipulierte Ziele | GRÜN; 92 Tests |
| 5 – Mobile E2E | echter Safari 26.6, 390 × 792 CSS-Pixel, DPR 2; Kernmatrix und Zwei-Nutzer-Trade | GRÜN nach minimalem CSS-Fix |
| 6 – Release Candidate | Regression ×2, Recovery, Migration, Startup/HTTP, Integrity/FK, DB-Schutz | GRÜN |

Zusätzlich liefen 203 Mehrnutzer-/Race-Tests und 19 kombinierte
Release-/Recovery-Tests grün. Die Suites überlappen fachlich bewusst mit den
Gate-Suites; ihre Zahlen werden nicht zu einer künstlichen Gesamtsumme addiert.

## 3. Integrierte Produktbereiche

- **Sammlung:** Current State bleibt Inventory-Wahrheit; Completion-Historie
  stammt nur aus kanonischen Fakten. Bestandsänderungen erzeugen keine
  rückwirkende Rekonstruktion. Albumprivacy bleibt wirksam.
- **Trophäen:** kanonische persistente Unlocks und kuratierter Katalog;
  Completion-, Trophy- und Feed-Dedupe bleiben exactly once. Dynamische
  Legacy-Wahrheiten bleiben abgeschaltet.
- **Trades:** manuelle und Smart-Anfragen, Availability, Reservation,
  Versand, Empfang, Probleme, Abschluss, Bewertung und gerichtete
  `SuccessfulTradeProjection` sind gemeinsam grün. Ungleiche Pakete bleiben
  zulässig; bestätigte Anfragen werden nicht verkleinert.
- **SmartMatch:** nur ausführbare Pakete, stabile Priorisierung,
  deterministische Sortierung, Block- und Tradepool-Gates. Verbrauchte
  Verfügbarkeit beendet konkurrierende Requests fail-closed.
- **Profil/Account:** öffentliche Projektion und private Accountdaten bleiben
  getrennt. ProfilePrivacy, Friendship, Blocks und Albumprivacy greifen.
- **Feed/Home:** ausschließlich kanonische CB-007-Ereignisse, aktuelle
  Privacy beim Read, chronologische Sortierung und höchstens eine News.
  Notifications, `user_activity` und SmartMatches sind keine Feedquelle.
- **Notifications/Inbox:** exakt neun produktive CB-008-Typen, keine neuen
  Legacy-Writer, nutzerbezogener CSRF-Read, Pagination, globaler Badge und
  30-Tage-Retention ab `created_at` für gelesene Zeilen.
- **Statistik:** Current State und Karriere sind getrennt; Trade-Erfolge,
  Completion und Trophäen lesen die kanonischen Projektionen ohne
  Legacy-Rekonstruktion.
- **Legacy-Cutover:** nur klassifizierte Read-/Redirect-Kompatibilität bleibt;
  keine operative Parallelwahrheit und kein Privacy-Bypass wurden gefunden.

## 4. Privacy-/Security-Nachweis

Die kombinierte Matrix deckt Owner, gegenseitige Freunde, Fremde, private
Profile, private Alben, Blocks und einseitige/offene Freundschaften ab.
Manipulierte IDs, fremde Notifications, fremde Trade-/Request-Ziele, direkte
Routen, Sessiongrenzen, CSRF und sichere Deep Links werden fail-closed
behandelt. Bereits gespeicherte Feed- oder Historienzeilen umgehen aktuelle
Privacy nicht. Öffentliche Profile enthalten keine Passwörter, Accountfelder
oder andere interne Identitätsdaten.

Ergebnis: **92/92**, 0 Fehler, 0 Skips; kein Privacy- oder Security-Verstoß.

## 5. Mehrnutzer-, Race- und Exactly-once-Nachweis

Die Race-Suite umfasst parallele Bestandsänderungen, konkurrierende
Reservierungen/Anfragen, SmartMatch-Rechecks, Versand/Empfang, Problemzustände,
Completion, Trophy-Unlock sowie Notification-/Feed-Dedupe.

- Ergebnis kombinierte Race-Suite: **203/203**, 0 Fehler, 0 Skips.
- Completion, Trophy, Feed und Notifications bleiben unter Retry dedupliziert.
- Inventar wird nur beim eigenen Versand aus- und beim eigenen Empfang
  eingebucht.
- Nicht mehr ausführbare Anfragen erzeugen keine zweite Reservierung und werden
  nicht automatisch verkleinert.

Der echte Safari-Smoke ergänzte dies mit zwei bewusst nacheinander erzeugten,
identischen Smart-Anfragen. Request 38 wurde reserviert und vollständig
abgeschlossen; Request 37 wechselte beim Recheck nach Verbrauch der
Verfügbarkeit auf `obsolete` und blieb ohne Reservierung.

## 6. Realistischer Migrations- und Recoverynachweis

Die echte Bestands-DB wurde nicht geöffnet, migriert oder beschrieben. Eine
Kopie wurde unter `/private/tmp/sammlr-cb017.LRAlyp/` geprüft.

Ausgang V7:

- 4 Nutzer, 8 Nutzeralben, 1.971 Stickerzeilen;
- 18 Trade-Requests, 10 Lifecycle-Trades, 89 Notifications;
- 61 Legacy-Trophyzeilen;
- Schema-Version 7, `integrity_check = ok`, 0 FK-Treffer.

Upgrade:

- Predeploy-Backup erfolgreich;
- Migrationen V8 bis V18 vollständig angewendet;
- zentrale Ausgangszahlen blieben unverändert;
- 0 historische Albumrecords, 0 kanonische Trophy-Unlocks und 0 Feed-Events
  unmittelbar nach Upgrade: kein impliziter Backfill;
- 0 doppelte Completion-, Trophy-, Feed- oder Notification-Dedupe-Schlüssel;
- `integrity_check = ok`, 0 FK-Treffer.

Recovery:

- Backup wurde in eine getrennte Datei restauriert;
- restaurierte Version 7 und alle Ausgangszahlen identisch;
- Backup- und Restore-SHA-256 identisch;
- frische Referenzfixture migrierte V0→V18; Repeat-up war leer;
- Release-/Recovery-Suite: **19/19**, 0 Fehler, 0 Skips.

## 7. Echter Safari-Nachweis bei 390 px

Umgebung: Safari 26.6, echtes Fenster 390 × 844 px, gemessener Viewport
390 × 792 px, DPR 2. Server und Browser verwendeten ausschließlich die
isolierte V18-Kopie. Es erfolgten harte Reloads und reale HTTP-/Form-/Fetch-
Requests.

### Gefundener Fehler vor Fix

- `/album/wm26`: `document.scrollWidth = 404`; mobile
  `.album-quick-card` mit Elternbreite 366 px lag durch `width:100%`, 24 px
  Padding und 2 px Border bei 392 px und reichte bis x=404.
- `/statistik`: derselbe Fehler auf
  `.statistics-trophy-card.album-quick-card`; Dokumentbreite 404 px.
- `/album/wm26/statistik`: vier intrinsisch breite `.stat`-Spalten ergaben
  `document.scrollWidth = 516` bei einem 366-px-Container.

Technische Ursache war ausschließlich das mobile Box Model beziehungsweise ein
nicht schrumpfendes Vier-Spalten-Grid. Der kleinste sichere Fix:

- S31-Kartenfamilie einschließlich `.album-quick-card`:
  `box-sizing:border-box; min-width:0`;
- `.stats` unter 430 px: `repeat(2, minmax(0,1fr))`;
- `.stat`: `box-sizing:border-box; min-width:0`.

Es wurden keine Pixelkompensation, kein Markup-Umbau und keine Design- oder
Produktlogikänderung vorgenommen.

### Wiederholung nach Fix

Für `/`, `/sammlung`, `/album/wm26`, `/album/wm26/liste`, `/trades`,
`/album/wm26/smart-trades`, `/profil`, `/statistik` und
`/album/wm26/statistik` gilt jeweils:

- `window.innerWidth = document.scrollWidth = body.scrollWidth = 390`;
- 0 überstehende DOM-Elemente;
- Bottom Navigation vollständig bei x=8 bis x=382, Höhe 83 px;
- Glocke und Tauschen erreichbar.

Zusätzliche reale Browserbelege:

- Empty State vollständig innerhalb x=12 bis x=378;
- echte Feedkarte vollständig innerhalb x=12 bis x=378;
- Feed-Deep-Link per Tastatur aktiviert und `/album/wm26` erreicht;
- Glockenformular real per POST geöffnet: `/notifications`, HTTP-Erfolg,
  Dokumentbreite 390 px;
- FWC4 per Inline-Fetch `1→2→1`, DOM und isolierte DB jeweils synchron,
  keine Meldung „Die Änderung konnte nicht gespeichert werden“;
- SmartMatch-Paket `101, 103 ↔ 242, 245` real angefragt, angenommen,
  reserviert, von beiden Nutzern versendet und empfangen;
- Trade 38 endete mit genau einem `completed`-Event, korrekter Aus-/Einbuchung,
  freigegebenen Reservierungen und einer persistenten 5-Sterne-Bewertung;
- Statistik und öffentliches Profil zeigten den neuen erfolgreichen Trade und
  die Bewertung, ohne Accountdaten zu leaken.

## 8. Tests und technische Gates

Gezielte Fix-/Projection-Suite:

- `test_cb017_integrated_rc`, `test_cb012_feed_home_cutover`,
  `test_cb015_statistics_projection`: **25/25**, 0 Fehler, 0 Skips.

Integrierte Suites:

- Gate 1 Data Contract: **60/60**;
- Gate 2 Trade Core: **329/329**;
- Gate 3 Product Projections: **109/109**;
- Gate 4 Privacy/Auth: **92/92**;
- Mehrnutzer/Races: **203/203**;
- Release/Recovery: **19/19**.

Vollständige Regressionen im expliziten S32/S35-Testenvironment:

- Lauf 1: **706/706**, `OK`, 0 Fehler, 0 Skips;
- Lauf 2: **706/706**, `OK`, 0 Fehler, 0 Skips.

Weitere Gates:

- aktive Python-Quellen per `py_compile`: erfolgreich; zwei bereits bestehende
  `invalid escape sequence`-Warnings in `webapp.py`, kein Compilefehler;
- ein bewusst zu breit gestarteter Diagnose-Compile über nichtproduktive
  Archivkopien fand deren bekannten Syntaxdefekt; Archive sind weder Runtime-
  noch Releasequelle und der aktive Scope wurde danach vollständig grün
  kompiliert;
- `git diff --check`: ohne Befund;
- echte V7-DB: `integrity_check = ok`, 0 FK-Treffer;
- isolierte V18-Kopie: `integrity_check = ok`, 0 FK-Treffer;
- Startup-Smoke auf `127.0.0.1:8091`: erfolgreich;
- `/healthz`: HTTP 200;
- authentifizierte echte Browser-HTTP-Smokes für `/`, `/sammlung`, Album,
  Stickerliste, SmartMatch, `/trades`, `/profil`, `/account`, `/statistik` und
  `/trophaeen`: jeweils HTTP 200.

## 9. Bestands-DB-Schutz

| Zeitpunkt | Schema | SHA-256 |
|---|---:|---|
| vor CB-017 | V7 | `3eb9da3b6d4898533030221bc80e8ed6406a25458eb8e1bca1f0e473a515b056` |
| nach CB-017 | V7 | `3eb9da3b6d4898533030221bc80e8ed6406a25458eb8e1bca1f0e473a515b056` |

Die echte Bestands-DB ist byte-identisch und wurde nicht migriert. Sämtliche
Browser-, Trade-, Feed-, Login- und Migrationsmutationen fanden nur auf
Wegwerfkopien statt.

## 10. Geänderte Dateien

- `App/static/style.css`: minimaler responsiver Box-Model-/Grid-Fix;
- `tests/test_cb017_integrated_rc.py`: gezielter statischer Vertrag für beide
  im echten Browser bewiesenen Ursachen;
- `Dokumentation/Post-RC/03-closed-beta-build-plan.md`: CB-017 und P1 auf
  abgeschlossen gesetzt;
- dieser Report.

Keine Migration, kein neuer Featurecode und keine Produktsemantik.

## 11. Product Contract, Known Issues und Restrisiken

**Product-Contract-Verletzung: NEIN.**
**Offener P0: NEIN.**
**Ungeklärte P1-Abweichung: NEIN.**

Die ausgegebenen `ResourceWarning`-Hinweise zu nicht geschlossenen
Testverbindungen sowie zwei bestehende Escape-Sequence-Warnings sind bekannte
Engineering-Hardening-Punkte; sie verursachen keine Testfehler, Datenmutation
oder Vertragsabweichung. Nichtproduktive Archivkopien enthalten weiterhin
historische, nicht importierte Syntaxartefakte. Diese Punkte gehören in die
nachgelagerte Hardening-/Repository-Hygienephase und blockieren den
abgenommenen P1-Vertrag nicht.

Post-Beta-Pakete CB-101 ff. und Future-Pakete bleiben ausdrücklich außerhalb
dieses Nachweises.

## 12. Abschluss und nächster zulässiger Schritt

CB-017 ist formal abgeschlossen und technisch abgenommen. Damit ist der
Closed-Beta-P1-Produktvertrag mit **17 von 17 Kernblöcken** abgeschlossen.

Der nächste tatsächlich zulässige Schritt ist **Phase 7 – Engineering
Hardening** gemäß `06-engineering-hardening.md`. Danach folgen **Phase 8 –
realistische Simulation** und **Phase 9 – finales Closed-Beta-Gate**. Erst ein
grünes finales Gate autorisiert die Einladung externer Closed-Beta-Nutzer.

Kein Commit und kein Push wurden ausgeführt.
