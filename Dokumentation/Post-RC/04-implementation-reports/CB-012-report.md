# CB-012 – sammlr.-Feed und Ablösung des operativen Home

**Stand:** 21. August 2026
**Status:** ABGESCHLOSSEN – technisch abgenommen
**Migration:** NEIN
**Echte Bestands-DB verändert:** NEIN

## 1. Ergebnis und finaler Home-Vertrag

Die Route `/` ist auf genau eine Produktprojektion umgestellt: den strikt
chronologischen Feed aus `FeedEventService`. Aufgaben, Prioritäten, laufende
Trades, SmartMatches und die alten Home-Platzhalter werden dort nicht mehr
gerendert. Aufmerksamkeit bleibt Aufgabe der Glocke; Tradeoperationen bleiben
unter `/trades` erreichbar.

`OperationalHomeService` wird von der Home-Route nicht mehr importiert oder
aufgerufen. Der Service selbst bleibt bis zum kontrollierten Legacy-Cutover in
CB-016 im Working Tree, damit dessen Entfernung nicht vorgezogen und seine
bestehende fachliche Regression weiterhin separat abgesichert wird.

## 2. Feed-Vertrag und Datenquellen

Einzige Feed-Datenquelle ist das in CB-007 eingeführte `feed_events` mit den
kanonischen Typen:

- `album_started`;
- `album_completed`;
- `trophy_unlocked`;
- `sammlr_news`.

Notifications, `user_activity`, SmartMatches, Trades und Tradepool werden
weder direkt noch indirekt als Feedquelle verwendet. Die produktive
Trophy-Allowlist bleibt leer. Die Completion-Trophy erzeugt weiterhin kein
zweites Ereignis neben `album_completed`; eine kontrollierte feedwürdige
Testdefinition belegt ausschließlich die technische Darstellbarkeit.

Die Sortierung bleibt `occurred_at DESC, event_key DESC`. Home fordert maximal
20 Einträge an. Persönliche Einträge füllen das Limit zuerst; höchstens ein
geeignetes `sammlr_news` wird danach aufgenommen. CB-012 führt keine
algorithmische Gewichtung und keine Pagination ein.

## 3. Karten, Identität und natürliche Ziele

Die Feedkarte zeigt Quelle beziehungsweise sichtbare Identität, einen zum
Eventtyp passenden Titel, Albumname und Ereigniszeit. Personen- und
Albumnamen werden beim Read gebündelt aus den kanonischen aktuellen Quellen
aufgelöst; gespeicherte interne Detailwerte werden nicht ungeprüft in die UI
projiziert.

Natürliche Ziele sind:

- eigene Albumereignisse: `/album/<album_id>`;
- eigene Trophäe: `/album/<album_id>/trophaeen`;
- fremdes Albumereignis: `/profil/<username>/album/<album_id>`;
- fremde Trophäe: `/profil/<username>`;
- News: nur ein gültiger interner, mit `/` beginnender Pfad; externe oder mit
  `//` beginnende Ziele werden beim Read verworfen.

Die Zielrouten behalten ihre eigenen Ownership- und Privacy-Gates. Ein Link
ist damit keine Autorisierung.

## 4. Privacy, Friendship und Blocks

Eigene kanonische Ereignisse sind sichtbar. Fremde Ereignisse benötigen eine
bestätigte gegenseitige Freundschaft und bestehen zusätzlich alle aktuellen
Read-Gates:

- Blocks haben Vorrang;
- `ProfilePrivacyService` wird respektiert;
- Albumprivacy wird respektiert;
- Accountzustand und sichtbare öffentliche Identität werden aktuell geprüft.

Eine spätere Sperre oder Privatisierung blendet ein bereits gespeichertes
Ereignis aus. Gefilterte Karten, Texte, Counts, Links und Empty States geben
keine private Identität oder Albuminformation preis. Die notwendigen
Identitäts- und Albumreads erfolgen gebündelt und nicht als Privacy-N+1 pro
Karte.

## 5. Empty State und mobile Projektion

Ein Nutzer ohne sichtbare Ereignisse erhält keine Fake-Events und keine
irreführenden Social-Platzhalter. Der Empty State erklärt, dass die
Sammlerreise hier beginnt, und verlinkt auf Sammlung und Tauschen.

Feedkarten und Empty State besitzen eigene, flache Layoutklassen ohne
Card-in-Card-Struktur. Lange Inhalte dürfen umbrechen; bei maximal 390 px
bleiben Container und Karten auf 100 Prozent Breite. Bottom Navigation und
Glocke bleiben Bestandteil des bestehenden Shell-Vertrags.

Der automatisierte Mobile-Vertragstest ist grün. Der reale Browsernachweis
wurde nach manueller Aktivierung von Safari Remote Automation mit Safari 26.6
auf macOS und einem WebDriver-Fenster von exakt `390 × 844 px` ausgeführt. Die
tatsächliche Layout-Viewportgröße betrug `390 × 792 px` bei DPR 2.

Der erste Smoke ist **fehlgeschlagen**:

- `document.documentElement.scrollWidth = 412 px`;
- `document.body.scrollWidth = 412 px`;
- horizontaler Overflow: **JA**, exakt 22 px;
- der leere Zustand lag bei `left = 12 px`, `right = 412 px`,
  `width = 400 px`;
- eine echte Feedkarte lag ebenfalls bei `left = 12 px`, `right = 412 px`,
  `width = 400 px`;
- die Bottom Navigation lag bei `left = -1 px`, `right = 391 px`,
  `width = 392 px`.

Die technische Ursache ist das reale Safari-Boxmodell: Im
`@media (max-width:390px)` setzt CB-012 `.feed-card, .feed-empty` auf
`width:100%` und `padding:16px`, ohne `box-sizing:border-box`. Der berechnete
Wert bleibt `box-sizing:content-box`; zur 366-px-Contentbreite kommen 32 px
Padding und 2 px Border hinzu, also 400 px. Die Karte vergrößert dadurch den
366-px-Container auf `scrollWidth = 400 px` und das Dokument auf 412 px. Die
Bottom Navigation besitzt denselben grundsätzlichen Content-box-Effekt mit
Breite, Padding und Border und ragt je 1 px über beide Viewportseiten.

Der Funktionsanteil des ersten Smokes war grün: `/` lieferte HTTP 200, Header und
Glocke waren vorhanden, Sammlung/Tauschen blieben erreichbar, alte operative
Home-Inhalte fehlten, ein isoliertes kanonisches `album_started` wurde als
Feedkarte dargestellt und der Klick führte ohne HTTP-Fehler nach
`/album/em24`.

Der kleinste sichere Fix setzt für `.feed-card`, `.feed-empty` und die
bestehende `.bottom-nav` ausschließlich `box-sizing:border-box`. Breiten,
Padding, Farben, Navigation und Produktlogik bleiben unverändert. Der erneute
Smoke mit Safari 26.6 bei demselben 390-px-Fenster war vollständig grün:

- `window.innerWidth = 390 px`;
- `document.documentElement.scrollWidth = 390 px`;
- `document.body.scrollWidth = 390 px`;
- `document.scrollWidth <= window.innerWidth`: **JA**;
- Feedkarte: `left = 12 px`, `right = 378 px`, `width = 366 px`, vollständig
  innerhalb des Viewports;
- Empty State: `left = 12 px`, `right = 378 px`, `width = 366 px`, vollständig
  innerhalb des Viewports;
- Bottom Navigation: `left = 8 px`, `right = 382 px`, `width = 374 px`,
  vollständig innerhalb des Viewports;
- keine weiteren DOM-Elemente mit einem Rand außerhalb des Viewports;
- Glocke, Sammlung und Tauschen erreichbar;
- Feed-Deep-Link weiterhin erfolgreich nach `/album/em24`.

## 6. Home-Cutover und Abgrenzung

Abgelöst wurden auf `/`:

- „Das braucht dich“ und dessen Priorisierung;
- „Alles erledigt“ als Arbeitskorbzustand;
- laufende Trade-/Versandkarten;
- SmartMatch-Aufgaben;
- Freunde-/News-Platzhalter des alten operativen Home.

Bewusst bis CB-016 erhalten bleiben der nicht mehr konsumierte
`OperationalHomeService`, seine fachlichen Service-Tests und weitere in der
Legacy-Matrix klassifizierte Implementierung. Nicht vorgezogen wurden
Legacy-Datenlöschung, Feed-/Notification-Bündelung, neue Social-Funktionen,
Trophy-Freigaben oder Änderungen an Collection-, Profil-, Statistik-, Trade-,
Notification- und Inbox-Semantik.

## 7. Migration und Datenwirkung

Keine Migration und kein Backfill sind erforderlich. CB-012 liest das bereits
mit V0013 bereitgestellte `feed_events`-Schema. Auf einem alten Schema ohne
Feedtabelle liefert Home fail-safe den ehrlichen leeren Zustand; es fällt
nicht auf die alte operative Parallelwahrheit zurück.

Die echte Bestands-DB blieb auf Schema V7. SHA-256 vorher und nachher:

`3eb9da3b6d4898533030221bc80e8ed6406a25458eb8e1bca1f0e473a515b056`

## 8. Geänderte Dateien

- `App/services/feed_events.py`: sichtbare öffentliche Identität und
  Albumname in die kanonische Feedprojektion aufgenommen; Newsziele
  serverseitig auf interne Pfade begrenzt.
- `App/services/collector_profiles.py`: gebündelte, privacy-geprüfte minimale
  öffentliche Identitätsprojektion ergänzt.
- `App/webapp.py`: `/` vollständig auf `FeedEventService` umgestellt und
  natürliche Feedkarten/Empty State integriert.
- `App/static/style.css`: mobile Feedkarten- und Empty-State-Regeln.
- `tests/test_cb012_feed_home_cutover.py`: gezielter CB-012-Vertrag.
- `tests/test_s04_home_collection_routes.py`,
  `tests/test_s25_operational_home.py`, `tests/test_s30_design_foundation.py`:
  historische Route-Erwartungen auf den bestätigten Home-Cutover aktualisiert;
  Legacy-Serviceverhalten bleibt separat getestet.
- dieser Report.

## 9. Tests

Gezielte CB-012-Suite:

- **11/11**, `OK`, 0 Fehler, 0 Skips.

Abgedeckt sind eigene Starts/Abschlüsse, Completion-Dedupe, kontrollierte
Trophäendarstellung bei unverändert leerer Produktiv-Allowlist, gegenseitige
Friendship, Blocks, Profil- und Albumprivacy, nachträgliche Privatisierung,
Chronologie und stabiler Tie-Break, Newslimit und persönlicher Vorrang, Empty
State, natürliche Ziele, ausgeschlossene Quellen, unveränderter Tradepool,
Home-Cutover, Navigation und Mobile-CSS-Vertrag.

Nach der ausschließlich auf `box-sizing` begrenzten CSS-Korrektur liefen der
CB-012-Test und die relevanten S30-/S31-CSS-/UI-Tests erneut gemeinsam:

- **29/29**, `OK`, 0 Fehler, 0 Skips.

Kombinierte Feed/Home/Privacy/Profile-, Collection/History/Stats-,
Notification/Inbox- und Trade/SmartMatch-Suite:

- **326/326**, `OK`, 0 Fehler, 0 Skips.

Vollständige Regressionen im expliziten S32/S35-Testenvironment:

- Lauf 1: **711/711**, `OK`, 0 Fehler, 0 Skips;
- Lauf 2: **711/711**, `OK`, 0 Fehler, 0 Skips.

Ein vorheriger Discover-Diagnoselauf ohne das vorgeschriebene explizite
S32-Test-Secret scheiterte erwartungsgemäß bereits an den Environment-Gates
und ist kein Produkt- oder Regressionsergebnis.

`py_compile` ist erfolgreich; sichtbar bleiben ausschließlich die zwei bereits
bekannten `SyntaxWarning`s zu `\d`-Stringliteralen in `App/webapp.py`.

## 10. Integrity, FK, Startup, HTTP und Diff

- echte V7-Bestands-DB: `PRAGMA integrity_check = ok`;
- echte V7-Bestands-DB: `PRAGMA foreign_key_check` ohne Treffer;
- isolierte temporäre V7→V18-Kopie: `MAX(schema_migrations.version) = 18`,
  `integrity_check = ok`, FK-Check ohne Treffer;
- Startup-Smoke im expliziten Testenvironment auf der isolierten V18-Kopie:
  `/healthz` HTTP 200 mit `{"status":"ok"}`;
- authentifizierte Routen `/`, `/sammlung`, `/notifications`, `/profil`,
  `/statistik` und `/trades`: jeweils HTTP 200;
- ein Production-Diagnoseimport mit einer temporären DB außerhalb `/var/data`
  wurde vom bestehenden Production-Volume-Gate erwartungsgemäß abgewiesen und
  ist nicht der offizielle isolierte Startup-Smoke;
- `git diff --check`: ohne Befund.

Die beiden vollständigen Regressionen mussten nach der reinen CSS-
Box-Model-Korrektur nicht erneut ausgeführt werden: Es wurde keine Python-,
Service-, Feed-, Navigations- oder Produktlogik geändert. Die gezielten
CB-012-/S30-/S31-Tests und der echte Safari-Retest decken den geänderten Scope
direkt ab.

## 11. Product-Contract-Bewertung und Restrisiken

In der implementierten Produktlogik wurde keine Contract-Verletzung
festgestellt. Migration, echte DB-Mutation, Commit und Push fanden nicht statt.

Der echte 390-px-Safari-Smoke hat die Layoutregression zunächst nachgewiesen
und nach der eng begrenzten Box-Model-Korrektur widerlegt. Es bestehen keine
gleichartigen überstehenden mobilen Vollbreiten-Elemente auf dem geprüften
Home-DOM. Product-Contract-Verletzung: **NEIN**.

## 12. Abschlussstatus und nächster Block

CB-012 ist formal abgeschlossen und technisch abgenommen. Alle automatisierten
Fach-, Integrations-, Regression-, Datenbank-, Startup- und HTTP-Gates sowie
der verpflichtende echte 390-px-Safari-Smoke sind grün.

**CB-016 – Kontrollierter Legacy-Cutover** ist der nächste zulässige und nun
freigegebene Closed-Beta-Block.
