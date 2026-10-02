# UIF-003A – sammlr.-Home Visual Concept / Golden Screen

**Stand:** 23. August 2026

**Status:** VISUELL FREIGEGEBEN UND IN DEN REGULÄREN PRODUKTPFAD INTEGRIERT

**Produktintegration:** JA – im nachgelagerten UI-Zwischenstands-Paket

**Migration:** NEIN

**UIF-003B:** nicht begonnen

## 1. Ziel und Umsetzungsschnitt

UIF-003A ersetzt die produktive Home-Seite noch nicht. Die visuelle Richtung
wurde vollständig isoliert über dem echten `/`-Renderer aufgebaut. Dadurch
bleiben der abgenommene UIF-002-Header, die Bottom Navigation und alle realen
Routen sichtbar und anklickbar, während der bisherige Empty State nur im
lokalen Study-Renderer durch das Concept-Markup ersetzt wird.

Es wurden keine produktiven Templates, Stylesheets, Services, Feed-Reads,
Priorisierungen, Aggregatdefinitionen oder Datenbanktabellen verändert. Der
Renderer arbeitete auf einer isolierten SQLite-Kopie.

## 2. Visuelle Richtung

Der reguläre Golden Screen besitzt bewusst keine persönliche oder
tageszeitabhängige Begrüßung. Sein Einstieg lautet:

- Seitentitel: **„Für dich“**;
- Subtitle: **„Was gerade passiert und was sich für dich lohnt.“**

Die Informationshierarchie ist:

1. primäre, konkret erklärte Tauschchance;
2. kompakter Status des Favoritenalbums.

Im finalen Visual-Polish wurde die redundante violette Kennzahlenbox
`17 / erreichbar` vollständig entfernt. Die `17` bleibt ausschließlich als
Akzent innerhalb der erklärenden Headline sichtbar. Ebenso wurde der
künstliche Feed-/Sammelmomente-Platzhalter vollständig entfernt: Ohne echte
darstellbare Feed-Ereignisse zeigt das Konzept keine Ersatz- oder Empty-State-
Card.

Die Seite verwendet ausschließlich Palette A, den neutralen UIF-002-Header
und die unveränderte UIF-002-Navigation. Lila erscheint nur als Action-,
Progress- und Active-Farbe. Es gibt keine violette Headerfläche, keine
Gradient-Grundsprache und keine permanente Begrüßung.

## 3. Visual States

### A. Regulärer Home-State bei 390 px

- Action-first;
- Tauschchance als wichtigste, aber weiße Card mit schmaler Accent-Kante;
- kompakter Albumstatus statt kopierter Sammlungskarte;
- ausschließlich `sammlr.` in der Bottom Navigation aktiv;
- keine Chat-/Messages-Andeutung.

### B. Scrollzustand bei 390 px

Der Endzustand zeigt das vollständige Favoritenalbum und beweist, dass die
letzte echte Home-Card oberhalb der Bottom Navigation erreichbar bleibt.

### C. Wide-State bei 1180 px

Ab 860 px wird dieselbe mobile Informationsarchitektur zweispaltig:

- primäre Tauschchance links;
- Albumstatus rechts;
- kein separates Desktop-Dashboard.

Die globale UIF-002 Bottom Navigation bleibt im Wide-State als dieselbe
DOM-Komponente mit denselben globalen Styles sichtbar. Das isolierte
Concept-CSS überschreibt ausschließlich ein bestehendes Desktop-`display:none`;
es wurde keine Desktop-Navigation, Sidebar oder alternative Navigation
eingeführt. Auf `/` ist nur `sammlr.` aktiv, Sammlung und Tauschen bleiben
neutral.

### Responsive Ergänzungen

Zusätzlich wurden reguläre Top-States bei 336 und 430 px erzeugt.

## 4. Datenherkunft

| Inhalt | Herkunft | Behandlung |
|---|---|---|
| `17` in der Tauschchance-Headline | **Visual Fixture** | nur im isolierten Concept; sichtbar durch die globale UIF-003A-Fixture-Kennzeichnung markiert; keine Berechnung, kein Write |
| FIFA World Cup 2026 | echter Bestands-Snapshot | vorhandenes Favoritenalbum des Testnutzers |
| `647 von 992`, `65 %` | echter Bestands-Snapshot | aus dem bestehenden Collection-Zustand übernommen, im Concept nicht neu berechnet |

Die Zahl `17` ist keine fachliche Wahrheit und darf in UIF-003B nicht als
Hardcode oder neue Match-Semantik übernommen werden. Für eine produktive
Integration muss ein bereits freigegebenes Read-Modell die jeweilige Zahl
liefern; andernfalls entfällt die konkrete Zahl.

## 5. Responsive- und Overflow-Nachweis

Browser: Safari 26.6, DPR 2.

| State | CSS-Viewport | Dokumentbreite | Dokumenthöhe | Cardbreiten | Spalten | Overflow |
|---|---:|---:|---:|---:|---|---|
| Minimum | 336 × 763 | 336 px | 1045 px | 312 / 312 px | 1 | keiner |
| Golden Screen | 390 × 763 | 390 px | 983 px | 366 / 366 px | 1 | keiner |
| Mobile groß | 430 × 763 | 430 px | 983 px | 398 / 398 px | 1 | keiner |
| Wide | 1180 × 763 | 1180 px | 763 px | 627 / 435 px | 2 | keiner |

Für alle Zustände gilt `document.scrollWidth = window.innerWidth`; die
DOM-Messung fand keine überstehenden sichtbaren Elemente. Bei 336, 390 und
430 px misst die Bottom Navigation 76 px Höhe und liegt vollständig innerhalb
des Viewports. Bei 1180 px ist sie ebenfalls sichtbar, misst **620 × 76 px**
und liegt horizontal zentriert vollständig innerhalb des Viewports.

Im 390-px-Endscrollzustand endet die letzte Card bei 453 px, während die
Navigation bei 679 px beginnt. Der Abstand beträgt damit **226 px**; der letzte
Inhalt wird nicht verdeckt. Header und Navigation bleiben funktional, alle
drei Hauptlinks besitzen `pointer-events:auto`.

Im 1180-px-Zustand endet der letzte Inhalt bei 500 px, während die Navigation
bei 679 px beginnt. Damit bleiben **179 px** Abstand zwischen
Endcontent und Navigation. Die Active-State-Messung weist in allen vier
Breiten ausschließlich `/` als aktiv aus.

Auf `/sammlung` weist die Browsermessung ausschließlich Sammlung als aktiv
aus. Der aktive Favorit ist ein gefülltes lila `★`, inaktive Favoriten sind
graue Outline-`☆`. Alle Controls messen weiterhin **44 × 44 px**, während das
sichtbare Glyph 16 px misst; Background und Border sind in beiden Zuständen
transparent. Im Endscrollzustand bleiben 200 px Abstand zur Bottom Navigation.

## 6. Screenshotpfade

- [Regulärer Golden Screen, 390 px](assets/UIF-003A/home-regular-390.png)
- [Scrollzustand, 390 px](assets/UIF-003A/home-scroll-390.png)
- [Minimum-State, 336 px](assets/UIF-003A/home-regular-336.png)
- [Mobile-State, 430 px](assets/UIF-003A/home-regular-430.png)
- [Wide-State, 1180 px](assets/UIF-003A/home-wide-1180.png)
- [Sammlung, aktiver Favorit bei 390 px](assets/UIF-003A/collection-favorite-active-390.png)
- [Sammlung, inaktive Favoriten bei 390 px](assets/UIF-003A/collection-favorite-inactive-390.png)

Reproduzierbare Study-Quellen:

- [Concept-Markup](assets/UIF-003A/home-concept.html)
- [Concept-CSS](assets/UIF-003A/home-concept.css)

## 7. Tests und Safety

Ausgeführte UIF-/Shell-/Navigation-/Collection-/Feed-Suite:

- `tests.test_uif002_global_app_shell`;
- `tests.test_uif001_collection_golden_screen`;
- `tests.test_s04_home_collection_routes`;
- `tests.test_s05_three_area_navigation`;
- `tests.test_s06_global_header_shell`;
- `tests.test_s30_design_foundation`;
- `tests.test_s31_ui_foundation`;
- `tests.test_cb012_feed_home_cutover`;
- `tests.test_cb013_collection_completion_projection`.

Ergebnis: **89/89 Tests**, 0 Fehler, 0 Skips.

| Prüfung | Vorher | Nachher |
|---|---|---|
| Schema | V7 | V7 |
| SHA-256 Bestands-DB | `3ccaff9ca4b4140ab9338c23f486f57e0ae253605f79c47f03a79f46dafa9df4` | `3ccaff9ca4b4140ab9338c23f486f57e0ae253605f79c47f03a79f46dafa9df4` |
| `PRAGMA integrity_check` | `ok` | `ok` |
| `PRAGMA foreign_key_check` | leer | leer |
| `git diff --check` | ohne Befund | ohne Befund |

## 8. Geänderte Dateien

Dauerhaft geändert beziehungsweise neu sind:

- `assets/UIF-003A/home-concept.html`;
- `assets/UIF-003A/home-concept.css`;
- sieben PNG-Screenshots;
- `App/webapp.py` ausschließlich für die zustandsabhängigen Stern-Glyphen;
- `App/static/style.css` ausschließlich für den transparenten, kompakten
  Favoriten-Visual-State bei unverändertem Touch Target;
- `tests/test_uif002_global_app_shell.py` für den aktiven/inaktiven
  Glyph-Nachweis;
- dieser Report.

Der temporäre WSGI-Renderer liegt außerhalb des Repositories. Produktdateien
der Fachlogik und die Bestands-DB wurden durch UIF-003A nicht verändert.

## 9. Offene visuelle Fragen für den Product Owner

1. Ist „Für dich“ die passende dauerhafte Überschrift ohne persönliche
   Begrüßung?
2. Hat die primäre Tauschchance die richtige visuelle Priorität, oder soll sie
   kompakter werden?
3. Ist die zweispaltige Wide-Komposition mit dominanter linker Action-Card die
   gewünschte Desktop-Richtung?
4. Passt „Tauschpartner ansehen“ als primärer CTA?

## 10. Empfehlung für UIF-003B

Nach visueller Freigabe sollte UIF-003B dieselbe Struktur produktiv
integrieren, jedoch ausschließlich mit bestehenden, fachlich freigegebenen
Read-Modellen:

- echte Feed-Ereignisse – falls vorhanden – oberhalb der Action-Ebene;
- ansonsten Action-first wie im Golden Screen;
- Tauschchance nur mit belastbarer vorhandener Kennzahl, niemals mit der
  Fixture `17`;
- Favoritenalbum aus der bestehenden Collection-Projektion;
- keine künstliche Feed- oder Empty-State-Card ohne echte Ereignisse;
- keine permanente Begrüßung und keine neue First-Open-Persistenz ohne
  gesonderten Vertrag;
- keine Änderung an Feed-, Trade-, Privacy-, Notification- oder
  Collection-Semantik.

Die freigegebene Richtung ist inzwischen ohne Visual Fixtures in den regulären
`/`-Renderer übernommen. Details und Abnahme stehen im
`UI-current-state-product-integration-report.md`. **UIF-003B wurde nicht
begonnen.**
