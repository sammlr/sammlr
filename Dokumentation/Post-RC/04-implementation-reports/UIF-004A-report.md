# UIF-004A – Tauschen / Visual Concept

**Stand:** 24. August 2026

**Status:** VISUELL FREIGEGEBEN UND IN DEN REGULÄREN PRODUKTPFAD INTEGRIERT

**Produktintegration:** JA – im nachgelagerten UI-Zwischenstands-Paket

**Migration:** NEIN

**UIF-004B:** nicht begonnen

**PO-Nacharbeit:** Grundrichtung freigegeben; kompakter Tabname und finale
typografische Konsolidierung umgesetzt, finale visuelle Abnahme ausstehend

## 1. Umsetzungsschnitt

UIF-004A ist ausschließlich ein isoliertes Visual Concept für `/trades`.
Der temporäre Renderer legt das Concept-Markup über den echten GET-Renderer,
übernimmt aber unverändert den globalen UIF-002-Header, die Bottom Navigation,
deren Links und den aktiven Hauptweltzustand „Tauschen“.

Produktive Templates, Trade-, Lifecycle-, Match-, Privacy- und Datenbanklogik
wurden nicht verändert. Stickerwall und Stickerliste wurden nicht berührt. Der
Browser-Smoke arbeitete auf einer isolierten SQLite-Kopie.

## 2. Visueller Vertrag

Die Seite trägt den Titel **„Tauschen“** und verwendet Palette A mit neutralem
Hintergrund, weißen Cards und Lila ausschließlich für Interaktion, Zahlen und
aktive Navigation. Es gibt keine großen violetten Albumheader, keine
Papiertextur und keinen Kollegblock-Stil.

Die drei Tabs beantworten jeweils eine klare Frage:

1. **Tauschpartner:** Wer passt zu mir?
2. **Trades:** Was läuft gerade?
3. **Anfragen:** Wer möchte mit mir tauschen?

Der aktive Tab verwendet Accent Soft. Inaktive Tabs bleiben neutral. Counts
sind kleine, neutrale Badges und erscheinen nur bei tatsächlich vorhandenen
beziehungsweise im Fixture ausdrücklich simulierten Zeilen.

Nach dem PO-Feedback heißt der mittlere Tab kompakt **„Trades“**. Route,
numerischer Badge und Zustand bleiben unverändert. Alle drei Tabnamen erscheinen
bei 390 px einzeilig. In der Partnercard werden beide gerichteten Aussagen mit
identischem typografischem Gewicht dargestellt; ausschließlich `2 Sticker` und
`83 Sticker` tragen den lila Zahlenakzent. Es wurden keine neuen Flächen,
Kacheln, Badges oder Komponenten ergänzt.

## 3. Visual States

### Tauschpartner

- ruhige Albumüberschrift „VfL Osnabrück“ statt Album-Farbfläche;
- `peter` mit Avatar und erkennbarem Profilzugang;
- 13 kanonisch erfolgreiche Trades als dezente Metainformation;
- gerichtete Aussagen: `peter` besitzt 2 gesuchte Sticker, der Nutzer besitzt
  83 von `peter` gesuchte Sticker;
- Primary CTA „Tausch starten“ führt auf den bestehenden Trade-Einstieg;
- zwei Alben ohne Treffer werden in einem einzigen neutralen Hinweis
  zusammengefasst.

Es wird keine mögliche Tauschmenge, kein Score und kein „Top Match“ erfunden.
Mangels vorhandener Bewertung wird keine Bewertungszahl dargestellt.

### Trades

Der State verwendet den realen Trade 36 mit `peter` im Album EURO 2024:

- kanonischer Lifecycle-State `partially_received`;
- sichtbares Wording „Teilweise erhalten“;
- gerichtete Mengen `1 erhalten · 1 gesendet`;
- Amber als Attention-Farbe, nicht Lila;
- kontextueller Einstieg „Versandstatus ansehen“ zum bestehenden Detail.

Es wurde kein neuer Lifecycle-State und keine neue Aktion eingeführt.

### Anfragen – realer Empty State

Die isolierte aktuelle DB enthält keine offenen Anfragen. Der State erscheint
direkt im Seitenlayout ohne Mini-Card, Illustration oder künstliche CTA:

> Keine offenen Anfragen
> Sobald dir jemand einen Tausch vorschlägt, erscheint er hier.

### Anfragen – Visual Fixture

Für die Beurteilung einer vorhandenen Anfrage existiert zusätzlich ein
isolierter, deutlich gekennzeichneter Fixture-State. Er zeigt `peter`, VfL
Osnabrück sowie `3 erhalten / 3 geben` und den ruhigen Einstieg „Ansehen“.

Diese Angaben sind ausschließlich Visual Fixture. Es wurde keine Anfrage
persistiert, keine Bestandszeile verändert und kein künstlicher Detaildatensatz
angelegt. Der CTA bleibt innerhalb des isolierten Fixture-State.

## 4. Datenherkunft

| Inhalt | Quelle | Bewertung |
|---|---|---|
| `peter`, VfL Osnabrück | reale isolierte Bestandskopie | echter Partner und echte Albumzuordnung |
| 2 gesuchte Sticker / 83 passende Sticker in Gegenrichtung | bestehende Inventory-/Matchprojektion von `/trades` | echte gerichtete Werte, keine Neuberechnung im Concept |
| 13 erfolgreiche Trades | kanonische Erfolgsprojektion | echter Wert; keine Legacy-Zeile als zusätzlicher Erfolg erfunden |
| keine Bewertung | kanonische Ratingprojektion | deshalb keine Bewertungszahl im Concept |
| Trade 36, `partially_received`, 1/1 | Lifecycle-, Shipping- und Receipt-Projektion | echter laufender Trade |
| 0 offene Anfragen | aktueller Read-State | echter Empty State |
| Anfrage 3/3 | isolierte Visual Fixture | keine Produkt- oder DB-Daten |

## 5. Responsive- und Shell-Nachweis

Browser: Safari 26.6, DPR 2.

| Breite | CSS-Viewport | Dokumentbreite | Dokumenthöhe Tauschpartner | Endcontent-Abstand zur Bottomnav | Overflow |
|---:|---:|---:|---:|---:|---|
| 336 px | 336 × 801 | 336 px | 989 px | 208 px | keiner |
| 390 px | 390 × 801 | 390 px | 997 px | 208 px | keiner |
| 430 px | 430 × 801 | 430 px | 997 px | 208 px | keiner |
| 1180 px | 1180 × 801 | 1180 px | 801 px | 192 px | keiner |

Für jede Breite gilt `document.scrollWidth = window.innerWidth`. Die
DOM-Messung fand keine überstehenden sichtbaren Elemente. Header und Bottom
Navigation liegen vollständig innerhalb des Viewports; die Navigation misst
mobil 76 px Höhe und im Wide-State **620 × 76 px**.

In sämtlichen States ist global ausschließlich `/trades` aktiv. Sammlung und
`sammlr.` bleiben neutral. Innerhalb der Seite ist exakt der ausgewählte Tab
aktiv. Alle Haupt- und Tablinks besitzen `pointer-events:auto`. Der Wide-State
verwendet dieselbe Bottom Navigation; es wurde keine Sidebar oder alternative
Desktopnavigation eingeführt.

Zusätzliche 390-px-Messungen:

- Trades: 390 px Dokumentbreite, kein Overflow;
- Anfragen Empty: 390 px Dokumentbreite, kein Overflow;
- Anfrage-Fixture: 390 px Dokumentbreite, kein Overflow und Fixture-Label im
  DOM vorhanden;
- kein Papier-/Kollegblock-Element in einem State.

## 6. Screenshots

- [Tauschpartner, 390 px](assets/UIF-004A/trades-partners-390.png)
- [Trades, 390 px](assets/UIF-004A/trades-running-390.png)
- [Anfragen Empty State, 390 px](assets/UIF-004A/trades-requests-empty-390.png)
- [Anfrage vorhanden – isolierte Fixture, 390 px](assets/UIF-004A/trades-request-fixture-390.png)
- [Tauschpartner Wide-State, 1180 px](assets/UIF-004A/trades-wide-1180.png)

Reproduzierbare Study-Quellen:

- `assets/UIF-004A/trades-partners.html`;
- `assets/UIF-004A/trades-running.html`;
- `assets/UIF-004A/trades-requests-empty.html`;
- `assets/UIF-004A/trades-request-fixture.html`;
- `assets/UIF-004A/trades-concept.css`.

## 7. Tests und Safety

Ausgeführte UIF-/Shell-/Match-/Trade-/Privacy-Suite:

- `tests.test_uif002_global_app_shell`;
- `tests.test_s05_three_area_navigation`;
- `tests.test_s06_global_header_shell`;
- `tests.test_s30_design_foundation`;
- `tests.test_s31_ui_foundation`;
- `tests.test_cb011_executable_match_contract`;
- `tests.test_s15_trade_shipping`;
- `tests.test_s16_trade_receipt`;
- `tests.test_s17_trade_problems_partial_receipt`;
- `tests.test_s18_trade_lifecycle_timeline`;
- `tests.test_s22_smart_trade_requests`;
- `tests.test_s27_album_privacy_trade_pool`;
- `tests.test_s28_trade_ratings`.

Ergebnis: **175/175 Tests**, 0 Fehler, 0 Skips.

| Prüfung | Vorher | Nachher |
|---|---|---|
| Schema Bestands-DB | V7 | V7 |
| SHA-256 Bestands-DB | `3ccaff9ca4b4140ab9338c23f486f57e0ae253605f79c47f03a79f46dafa9df4` | `3ccaff9ca4b4140ab9338c23f486f57e0ae253605f79c47f03a79f46dafa9df4` |
| `PRAGMA integrity_check` | `ok` | `ok` |
| `PRAGMA foreign_key_check` | leer | leer |
| `git diff --check` | ohne Befund | ohne Befund |

## 8. Geänderte Dateien

Dauerhaft neu sind ausschließlich Dokumentations-/Study-Artefakte:

- vier HTML-Visual-States unter `assets/UIF-004A/`;
- `assets/UIF-004A/trades-concept.css`;
- fünf PNG-Screenshots;
- dieser Report.

Der WSGI-Visual-Renderer und die Session-Brücke liegen außerhalb des
Repositories unter `/private/tmp`. Es gab keine Produktübernahme und keine
Bestands-DB-Änderung.

## 9. Offene visuelle PO-Fragen

1. Ist die partnerzentrierte Card-Hierarchie mit den zwei gerichteten Aussagen
   die gewünschte Richtung?
2. Ist „Trades“ als kompakter Ersatz für „Absprachen“ visuell und sprachlich
   final freigegeben?
3. Ist Amber für `Teilweise erhalten` angemessen zurückhaltend?
4. Soll der kompakte Sammelhinweis für Alben ohne Treffer in dieser Form
   bestehen bleiben?
5. Ist der Anfragen-Entry-Point „Ansehen“ ausreichend ruhig?

Die freigegebene Richtung ist inzwischen ohne Visual Fixtures in den regulären
`/trades`-Renderer übernommen. Details und Abnahme stehen im
`UI-current-state-product-integration-report.md`. **UIF-004B wurde nicht
begonnen.**
