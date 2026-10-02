# TRADE-11 — Kanonische Stickerphysik und gezielter UI-Feinschliff

Stand: 2026-10-02. Funktionaler Stand TRADE-10 bleibt erhalten. Ausschließlich isolierte Präsentation und Tests; keine produktive Integration.

## Ergebnis

**Die kanonische Stickerkarte besitzt in Wall und Trade dieselben physischen Dimensionen.**

Die Aussage gilt bei gleicher Viewportbreite. Die produktive Wall ist selbst responsiv; sie hat keine universelle 100-px-Karte. Die früheren 100-px-Komponentenprüfungen bleiben als Layer-/Face-Gates erhalten, werden aber durch einen Vergleich des tatsächlichen produktiven Rasters ergänzt.

| Viewport | Wall = Top 3 = Albumfront = ausgelegte Karte |
| --- | --- |
| 375 px | 103 × 117,406 px |
| 390 px | 108 × 123,109 px |
| 430 px | 118,656 × 135,266 px |
| 1280 px | 96,1719 × 109,625 px |

Werte sind die vom Browser serialisierten CSS-Pixelmaße; Rendering rundet intern auf Subpixel. Aspect-Ratio 1 / 1,14, Radius 14 px, Border 1 px solid und Padding 11 px 7 px sind aus der vorhandenen Wall übernommen. Bestehende Unterschiede zwischen owned/duplicate (etwa Statusfarbe und produktiver Mengenbadge) werden nicht umgedeutet. Rotation verändert die umschließende achsenparallele Boundingbox, nicht die physische Kartengröße. Die Tests prüfen zusätzlich Skalierungsfreiheit der vollständigen Vorfahrenkette.

## Unveränderte Quelle und Schutz gegen zweite Größenwahrheit

Quellen:

- `App/webapp.py`: `canonical_sticker_wall_html`, `sticker_wall_slot_html`, `sticker_wall_card_inner`; tatsächlicher Owner-Wall-Kontext `body.s31-product-page.s30-reference-page.s30-album-page > .container > .card.sticker-wall-card > .canonical-sticker-wall > .wall`.
- `App/static/style.css`: `.s30-album-page .wall`, mobile Rasterregeln bis 430 px, `.sticker-slot-frame`, `.sticker-wall-stack-layer`, `.s30-album-page .sticker-slot-frame .slot`, kanonische Nummern-/Glyphenregeln und bestehende Container-/Padding-Regeln.
- `App/static/pax/components.css`: bereits vorhandene, unveränderte gescopte Präsentationskopie der Wall-Regeln.
- `App/static/pax/pax.js`: unveränderter `card`-/`renderReceive`-Renderer und deterministische Posen, maximal zehn Receive-Lagen.

`sticker_physics.js` misst die Breite in einem unsichtbaren, inerten, read-only iframe mit genau dem Owner-Wall-Ancestor-Kontext und der **originalen** `/static/style.css`. Das iframe lädt keine Produktivroute, kein Inventar und keinen Produktions-JS-Controller. Der Browser löst die vorhandenen Container-/Raster-/Breakpointregeln selbst auf. Der Messwert wird als `--trade-card-width` verwendet und über ResizeObserver aktualisiert. Keine kopierte Berechnungsformel, keine festgelegte 100-px-Ersatzkarte, kein Scale-Faktor. Das ist ein eng begrenzter Preview-Adapter, keine produktive Architekturrefaktorierung.

Faces, Höhe/Ratio, innere Positionierung, SVG-Ziffern und Layer bleiben aus der vorhandenen Komponente. Der neue Test rendert **zusätzlich die vollständige tatsächliche Produktions-Wall** mit synthetischem Read-only-Bestand und vergleicht deren BRA1-Karte mit allen Trade-Kontexten. Damit wird auch eine künftige Abweichung zwischen Original-CSS, bestehender Komponentenkopie oder Messkontext sichtbar. Vor Integration bleibt eine gemeinsame kanonische Quelle kontrolliert zu extrahieren; das bestehende Pax-/Wall-System wird jetzt nicht refaktoriert. Der Paritätsgate ist dafür die überprüfbare Grenze.

## Präsentationsänderungen

- Sämtliche Trade-72-%-Transforms entfernt. Top- und Albumstapel sowie alle ausgelegten Karten erhalten dieselbe gemessene Breite. Der frühere feste Top-100-px-Wert ist entfernt.
- Top 3 behalten Auswahl, Dismiss, Nachrücken und Linkverhalten. Der Wortlaut lautet jetzt „3 vielversprechende Tauschvorschläge für dich.“ Auch die zugängliche Sektionsbezeichnung enthält keine Algorithmuserklärung.
- Top-Stapel maximal ±0,3° und ±1 px, Albumstapel entsprechend zurückhaltend und deterministisch. Offene Sticker verwenden die unveränderten vorhandenen Pax-Posen. Keine Mengen-Skalierung und keine neue Layergeometrie.
- Raster verteilen die unverkleinerten Karten nach verfügbarem Platz. Die Top-3-Auslage nutzt mobil mehr horizontale Fläche innerhalb des Viewports; alle drei Stapel passen ohne Kollision. Ausgelegte Alben dürfen entsprechend weniger Spalten haben, statt ihre Karten zu verkleinern.
- „Alle anzeigen“ und „Zusammenlegen ↑“ sind kompakte sekundäre Textaktionen mit mindestens 44 px Höhe. Primäre Request-/Lifecycle-Aktionen bleiben unverändert.
- Manuelle Auswahl bleibt die kanonische handschriftliche Zahlenliste, ohne neue Karten oder Änderungen an Eligibility. Ihre bestehende Dealprüfung und sämtliche anderen Receive-Ansichten verwenden denselben verbesserten Trade-Wrapper.

## Auffächern und Zusammenlegen

`receive_motion.js` adaptiert ausschließlich die Präsentationsinteraktion. Die kanonische Receive-DOM-Struktur und die kanonischen Faces werden weiterverwendet. Native Albumbuttons behalten aria-expanded/aria-controls und fokussieren nach Öffnen/Schließen die passende Kontrolle.

Vor Layoutwechsel werden reale Karten-/Stack-Layer-Mittelpunkte gemessen. Danach bewegen sich nicht interaktive, aria-hidden Präsentationskopien der vorhandenen kanonischen Karten über **440 ms** zu den neuen Positionen oder zurück. Nur Translation und kleine Rotation; keine Width-/Height-/Scale-Keyframes. Die Zielkarten werden nach Abschluss sichtbar und die temporäre Ebene entfernt. Die Animation übernimmt gemessene Layerpositionen; sie implementiert keinen eigenen −2/−2-Algorithmus und keinen zweiten Cap. Andere betroffene Albumkarten bewegen sich bei der Umordnung ebenfalls per Translation.

„Alle anzeigen“ öffnet alle noch geschlossenen Alben in einem gemeinsamen Layoutschritt. Einzelne Alben bleiben unabhängig schließbar. Weitere Eingaben beenden eine noch laufende Präsentationsbewegung sauber, bevor die nächste beginnt; keine übrig gebliebenen Ebenen oder verborgenen Karten. Reduced Motion überspringt die Bewegungen und behält Interaktion/Fokus bei; auch ein Präferenzwechsel beendet die laufende Bewegung.

Die Animationsebene enthält denselben getrennten `.pax-board > .s30-album-page`-Kontext wie die echte Receive-Ansicht. Das ist für die gescopten kanonischen Regeln notwendig und wird in Zwischenständen geprüft. Top-Vorschlag → Deal bleibt die bestehende Seitennavigation, kein neuer Router oder Lifecycle.

## Prüfungen

Ausgeführt:

```sh
.venv/bin/python -B -m unittest tests.test_trade_v2_preview tests.test_pax_preview -q
.venv/bin/python -B -m unittest tests.test_sticker_wall_product_island tests.test_ceoklaue_sticker_list -q
.venv/bin/python -B tests/research/check_trade_11_regressions.py
.venv/bin/python -B tests/research/check_trade_11.py
git diff --check
```

- 37 Unit-Tests bestanden; produktive Referenzen verwenden ausschließlich temporäre Testdatenbanken.
- TRADE-01–10-Browserregressionen bestanden. Geänderte Erwartungen ausschließlich für freigegebenes Wording, responsive statt fest 100 px breite Karten, 440 statt 240 ms und numerische Referenzkarten auf derselben gemessenen Breite. Domainassertionen unverändert.
- Neue direkte Produktions-Wall-Parität bei 375/390/430/1280: gleiche Breite, Höhe, Ratio, Radius, Borderbreite/-stil, Padding, Flex-/Typografiegrundwerte und identische innere Team-/Nummern-/SVG-Maße. Keine Skalierung in der Vorfahrenkette.
- Alle ausgelegten Karten und temporären Bewegungskarten geprüft; Animation vorwärts/rückwärts in angehaltenen Zwischenständen. Kanonische Maße bleiben erhalten.
- Top-3-Stapel und alle ausgelegten Karten kollisionsfrei, keine horizontalen Überläufe. Einzelnes Album, alle sechs Alben, Zusammenlegen, Reload-Determinismus, Touch/Tastatur und Reduced Motion bestanden.
- Kein Requeststore-Wechsel durch Öffnen/Schließen; keine schreibenden Browserrequests oder Browser-/HTTP-Fehler.
- Bestehende 21 BRA-3-Layerprüfungen sowie 28 numerische Face-/Stackprüfungen bestanden. Wall5/Trade10, −2/−2, z-index und konstante Geometrie ab zehn Lagen unverändert.
- Neue Screenshots bei vier Breiten: Top 3, geschlossene Albumstapel, ein offenes Album, alle Alben, beide Bewegungsrichtungen und direkter Größenvergleich. Visuell geprüft. Die Vergleichsbilder enthalten unskalierte Originalausschnitte; die Galerie verlinkt volle Auflösung.

## Links und vollständiger Scope

- Preview: http://127.0.0.1:8095/trade-v2/
- Fatima-SmartDeal: http://127.0.0.1:8095/trade-v2/partners/fatima/smartdeal
- [Galerie](../tests/research/artifacts/trade-11/index.html)
- [Direkter Größenvergleich, 390 px](../tests/research/artifacts/trade-11/comparison-390.html)
- [Prüfergebnis](../tests/research/artifacts/trade-11/checks.json)
- [Vollständige geänderte/neue Dateiliste mit SHA-256](../tests/research/artifacts/trade-11/files.json)
- [Vorher-/Nachher-Schutznachweis](../tests/research/artifacts/trade-11/scope-checks.json)

Der Schutznachweis vergleicht gegen den tatsächlichen Bestand vor TRADE-11, einschließlich bereits vorhandener fremder Arbeitsänderungen. Produktiv-DB/Webapp, Stickerwall/-liste, Pax, SmartDeal, Legacy und sämtliche Trade-Domain-/Lifecyclemodule bleiben bytegleich. Keine Löschungen. Keine Änderung an Auswahl, Mengen, manuellen Regeln, Slots, Request-/Frist-/Amendment-/Pack-/Adress-/Versand-/Empfang-/Problem-/Bewertungslogik oder TRADE-10-Projektion.

Keine produktive DB-Mutation. Kein git add, Commit, Push oder Deploy.
