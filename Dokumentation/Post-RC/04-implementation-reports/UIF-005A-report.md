# UIF-005A – Laufender Trade / Visual Concept

**Stand:** 25. August 2026

**Status:** VISUAL CONCEPT BEREIT ZUR PO-ABNAHME

**Produktintegration:** NEIN

**Migration:** NEIN

**UIF-005B:** nicht begonnen

## 1. Umsetzungsschnitt

UIF-005A ist ausschließlich ein isolierter Visual Concept für die
Trade-Detailansicht. Der temporäre WSGI-Renderer legt das Concept-Markup über
den echten GET-Renderer von Trade 36. Dadurch verwendet die Studie unverändert
den produktiven neutralen UIF-002-Header, dessen reale Notification-Anzeige,
die globale Bottom Navigation und deren Links.

Der Renderer läuft auf Port 18191 mit einer byte-identischen SQLite-Kopie unter
`/private/tmp`. Produktive Templates, das produktive Stylesheet, Trade-
State-Machine, Shipping, Receipt, Probleme, Reservierungen, Ratings,
Notifications und die Bestands-DB wurden nicht verändert.

## 2. Visueller Vertrag

Die Seite beantwortet in dieser Reihenfolge:

1. Partner und Album;
2. verständlicher aktueller Zustand;
3. gerichteter Tauschinhalt;
4. genau eine dominante nächste Aktion;
5. kompakter Versandstatus und optionaler vollständiger Verlauf.

Der Seitentitel lautet **„Trade mit peter“**, EURO 2024 steht direkt darüber.
Die Rücknavigation lautet **„‹ Zurück zu Trades“**. Partneridentität wird
kompakt durch Avatar und – im Wide-State – 13 kanonisch erfolgreiche Trades
gestützt; es gibt keinen separaten großen Infoblock.

Der laufende State verwendet Attention/Warm für den ausstehenden Empfang. Grün
markiert ausschließlich erledigte Schritte. Rot bleibt der sekundären
Problemhandlung vorbehalten. Lila wird nur für Interaktion und den globalen
Active State verwendet. Ein blauer Status oder Papier-/Kollegblock-Stil kommt
nicht vor.

## 3. Visual States

### Laufender Trade

- Status: „Warte auf deine Empfangsbestätigung“;
- Sekundärtext: „peter hat seinen Versand bestätigt.“;
- `Du bekommst`: `UEFA 1`;
- `Du gibst`: `LEG 2`;
- einzige dominante Primäraktion: „Alles vollständig erhalten“;
- erledigte Eigenaktion nur als ruhiger Text: „✓ Dein Versand wurde
  bestätigt“;
- „Problem mit Lieferung melden“ bleibt sichtbar, aber klar sekundär.

Auf 390 px ist die Primäraktion vollständig im ersten Viewport sichtbar. Der
kompakte Versandstatus folgt beim Scrollen.

### Verlauf

Nach der letzten PO-Nacharbeit ist der Versandstatus genau **eine Komponente
mit zwei Darstellungszuständen**:

- geschlossen beantwortet sie nur „Wo stehen wir gerade?“;
- geöffnet beantwortet sie nur „Wie sind wir hierher gekommen?“.

Im geschlossenen laufenden State erscheint ausschließlich „peter hat den
Versand bestätigt“ mit „Sticker sind unterwegs“. Im geschlossenen
abgeschlossenen State erscheint ausschließlich „Trade abgeschlossen“ mit dem
letzten belastbaren Zeitpunkt `25.08.2026 · 21:28`.

Beim Öffnen verschwindet diese Kurzprojektion vollständig und dieselbe Card
zeigt stattdessen den chronologischen Verlauf mit dezenten Zeitstempeln. Es
gibt keine zusätzliche Kurz-Timeline, keine parallele zweite Verlaufskomponente
und kein Ereignis erscheint innerhalb der geöffneten Liste doppelt. Der
UI-seitige Klappzustand verwendet ein natives semantisches `details`-Element
und persistiert nichts.

Ein echter Safari-Runtime-Zyklus bei 390 px bestätigte nacheinander:

1. geschlossen: Latest-State sichtbar, 0 Verlaufsevents sichtbar;
2. geöffnet: Latest-State ausgeblendet, 3 eindeutige Events sichtbar;
3. wieder geschlossen: Latest-State sichtbar, 0 Events sichtbar;
4. erneut geöffnet: Latest-State ausgeblendet, wieder exakt 3 Events sichtbar.

In allen vier Zuständen blieb `scrollWidth = innerWidth = 390`; der Klappzyklus
erzeugte weder Overflow noch ein Doppelrendering.

### Abgeschlossener Trade / Bewertung

Der reale abgeschlossene Lifecycle-State wird als grüner Erfolg dargestellt:

- „Trade abgeschlossen“;
- „Du und peter habt den Tausch erfolgreich abgeschlossen.“;
- derselbe gerichtete Tauschinhalt ohne Wiederholung an anderer Stelle;
- Bewertung als nächste sinnvolle Aktion, nicht als permanenter Block im
  laufenden State.

Die Bewertungsaktion ist im isolierten Visual State vollständig sichtbar und
führt keinen Request aus.

## 4. Verwendete reale Daten

| Inhalt | reale Quelle der isolierten DB-Kopie |
|---|---|
| Trade Request | `trade_requests.id = 36` |
| kanonischer Lifecycle-Trade | `trades.id = 10` |
| Partner | `peter` |
| Album | EURO 2024 |
| gerichteter Inhalt aus Sicht Nutzer 1 | `UEFA 1` bekommen, `LEG 2` geben |
| angenommen | 15.08.2026, 00:15:20 UTC |
| Versand peter | 15.08.2026, 00:15:22 UTC |
| eigener Versand | 16.08.2026, 17:41:13 UTC |
| real abgeschlossen | 25.08.2026, 19:28:15 UTC |
| Vertrauensinformation | 13 kanonisch erfolgreiche Trades für Nutzer 1 |

Die lokal dargestellten Uhrzeiten sind um zwei Stunden in Europe/Berlin
formatiert.

## 5. Sämtliche Visual Fixtures

### Laufender Empfangsstatus

Trade 36 war beim ersten UIF-005A-Datencheck bereits real abgeschlossen. Für
den verpflichtenden laufenden State wird deshalb ausschließlich im Concept ein
früherer Snapshot simuliert: beide Sendungen bestätigt, eigener Empfang noch
offen. Der State ist im UI ausdrücklich als **Visual Fixture** markiert. Die
späteren realen Receipt-/Completion-Ereignisse werden in diesem einen
laufenden Snapshot nicht angezeigt; sie werden weder gelöscht noch verändert.

### Bewertung

Die Bestands-DB steht auf Schema V7 und enthält keine produktive
`trade_ratings`-Tabelle. Die Schaltfläche „peter bewerten“ ist daher nur der
geforderte visuelle Bewertungszustand. Sie ist ein `type="button"` ohne Form,
Action oder Write. Es wurde keine Bewertung angelegt.

Alle übrigen angezeigten Partner-, Album-, Code- und Ereignisdaten sind reale
Read-Daten der isolierten Kopie.

## 6. Responsive-, Overflow- und Bottomnav-Nachweis

Browser: Safari 26.6, DPR 2. Messung über ein isoliertes, read-only
Browser-Instrument im Concept-Renderer.

| Breite | CSS-Viewport | Dokumentbreite | Dokumenthöhe | Primäraktion bis Nav | Endcontent bis Nav | Overflow |
|---:|---:|---:|---:|---:|---:|---|
| 336 px | 336 × 751 | 336 px | 1160 px | 15 px | 136 px | keiner |
| 390 px | 390 × 751 | 390 px | 1136 px | 39 px | 136 px | keiner |
| 430 px | 430 × 751 | 430 px | 1112 px | 63 px | 136 px | keiner |
| 1180 px | 1180 × 751 | 1180 px | 1003 px | 42 px | 88 px | keiner |

Für alle Pflichtbreiten gilt
`document.documentElement.scrollWidth === window.innerWidth`. Die Suche über
alle sichtbaren nicht-fixierten DOM-Elemente fand keine Overflow-Offender.
Header und Bottom Navigation liegen vollständig innerhalb des Viewports.

Die Navigation misst mobil 76 px Höhe und bei 1180 px **620 × 76 px**. In
allen Zuständen ist ausschließlich `/trades` aktiv; Sammlung und `sammlr.` sind
neutral. Alle drei Links besitzen `pointer-events:auto`. Beim Endscroll bleibt
der letzte Inhalt mit mindestens 88 px Abstand oberhalb der Navigation
erreichbar.

Zusätzliche 390-px-Nachweise nach der Verlaufsklappen-Nacharbeit:

- laufender Verlauf geschlossen: nur Latest-State sichtbar;
- laufender Verlauf geöffnet: Latest-State ausgeblendet, exakt drei
  chronologische Ereignisse;
- abgeschlossener Verlauf geschlossen: nur Abschluss und Abschlusszeitpunkt;
- abgeschlossener Verlauf geöffnet: Latest-State ausgeblendet, exakt sechs
  chronologische Ereignisse ohne Duplikat;
- beide geöffneten States: 390 px Dokumentbreite, kein Offender, 136 px
  Endcontent-Abstand;
- abgeschlossener State: 390 px Dokumentbreite, kein Offender;
- Bewertungsaktion endet 18 px oberhalb der Navigation und ist vollständig
  sichtbar;
- produktive Papier-/Tradebar-Elemente sind im Concept-DOM nicht vorhanden.

## 7. Abnahmeartefakte

- [Laufender Trade, 390 px](assets/UIF-005A/trade-running-390.png)
- [Laufender Trade, Verlauf geschlossen bei 390 px](assets/UIF-005A/trade-running-status-closed-390.png)
- [Laufender Trade, Verlauf geöffnet bei 390 px](assets/UIF-005A/trade-running-status-open-390.png)
- [Abgeschlossener Trade / Bewertung, 390 px](assets/UIF-005A/trade-completed-390.png)
- [Abgeschlossener Trade, Verlauf geschlossen bei 390 px](assets/UIF-005A/trade-completed-status-closed-390.png)
- [Abgeschlossener Trade, Verlauf geöffnet bei 390 px](assets/UIF-005A/trade-completed-status-open-390.png)
- [Laufender Trade, 336 px](assets/UIF-005A/trade-running-336.png)
- [Laufender Trade, 430 px](assets/UIF-005A/trade-running-430.png)
- [Laufender Trade, Wide-State bei 1180 px](assets/UIF-005A/trade-status-wide-1180.png)

Reproduzierbare Concept-Quellen:

- `assets/UIF-005A/trade-running.html`;
- `assets/UIF-005A/trade-running-timeline.html`;
- `assets/UIF-005A/trade-completed.html`;
- `assets/UIF-005A/trade-completed-timeline.html`;
- `assets/UIF-005A/trade-detail-concept.css`.

Der WSGI-Renderer selbst liegt ausschließlich unter
`/private/tmp/uif005a_visual_server.py` und ist kein Produktartefakt.

## 8. Tests

Gezielt ausgeführt wurden:

- `tests.test_uif005a_trade_detail_visual_concept`;
- `tests.test_uif002_global_app_shell`;
- `tests.test_s15_trade_shipping`;
- `tests.test_s16_trade_receipt`;
- `tests.test_s17_trade_problems_partial_receipt`;
- `tests.test_s18_trade_lifecycle_timeline`;
- `tests.test_s28_trade_ratings`.

**Ergebnis nach der letzten Nacharbeit:** 109/109 Tests, 0 Fehler, 0 Skips.

Die Tests belegen unter anderem die einzelne Primäraktion, die explizite
Fixture-Kennzeichnung, die write-freien Visual Controls, die eine native
Collapsed/Open-Komponente, eindeutige Timeline-Ereignisse,
Success-/Attention-Semantik, den Verzicht auf Papierstil sowie den mobilen
Box-Model-Vertrag.

## 9. DB- und Safety-Nachweis

| Prüfung | Vorher | Nachher |
|---|---|---|
| Schema Bestands-DB | V7 | V7 |
| SHA-256 Bestands-DB | `2485300440f4176a31acae8fb9bea047007efec8ad72dd86ccedfbbd9895ff55` | `2485300440f4176a31acae8fb9bea047007efec8ad72dd86ccedfbbd9895ff55` |
| SHA-256 isolierte DB-Kopie | identisch | identisch |
| `PRAGMA integrity_check` Bestands-DB | `ok` | `ok` |
| `PRAGMA foreign_key_check` Bestands-DB | leer | leer |
| Integrity/FK isolierte Kopie | `ok` / leer | `ok` / leer |
| `git diff --check` | – | ohne Befund |

Keine Migration und keine Bestands-DB-Änderung wurden ausgeführt.

## 10. Geänderte Dateien

Dauerhaft neu sind ausschließlich:

- die fünf Concept-Quellen unter `assets/UIF-005A/`;
- die Safari-Abnahmescreenshots unter `assets/UIF-005A/`;
- `tests/test_uif005a_trade_detail_visual_concept.py`;
- dieser Report.

Keine produktive Python-, Template- oder CSS-Datei wurde durch UIF-005A
geändert.

## 11. Abschluss

UIF-005A ist als isolierter Visual Concept vollständig vorbereitet und wartet
auf die visuelle PO-Entscheidung. **Es gab keine Produktintegration. UIF-005B
wurde nicht begonnen.**
