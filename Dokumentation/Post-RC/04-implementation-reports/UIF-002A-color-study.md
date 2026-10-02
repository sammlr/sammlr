# UIF-002A – Color System / Visual Palette Study

**Stand:** 23. August 2026

**Status:** ABGENOMMEN

**Visuelle Product-Owner-Abnahme:** Variante A „Current Sammlr Refined“ am
23. August 2026 verbindlich freigegeben

**UIF-002:** Noch nicht begonnen und nicht abgeschlossen

**Migration:** NEIN

## 1. Ziel

UIF-002A stellt drei professionelle Farbvarianten im echten UIF-001-
Sammlungsscreen gegenüber. Es handelt sich ausschließlich um eine visuelle
Entscheidungsstudie vor UIF-002. Der Product Owner hat Variante A „Current
Sammlr Refined“ als verbindliche Grundlage des neuen Sammlr Color Systems
ausgewählt.

Die Freigabe gilt für die Farbrollen und semantischen Farben der Variante A.
Sie ist keine automatische Freigabe aller in der Studie gezeigten
Komponenten, Icons oder Detailzustände. Varianten B und C bleiben reine
Entscheidungsdokumentation und dürfen nicht produktiv mit A vermischt werden.

Der bestehende Sammlungsscreen, seine Inhalte und alle fachlichen Funktionen
blieben unverändert. Die Paletten wurden nur in einem isolierten lokalen
Renderer auf einer temporären SQLite-Kopie zur Laufzeit auf den aktuellen
UIF-001-Screen gelegt. Die App enthält daher keine drei parallelen Theme-
Systeme.

## 2. Geänderte Dateien

Neu erzeugt wurden ausschließlich:

- `assets/UIF-002A/palette-a-390.png`;
- `assets/UIF-002A/palette-b-390.png`;
- `assets/UIF-002A/palette-c-390.png`;
- `assets/UIF-002A/semantic-colors-a.png`;
- `assets/UIF-002A/semantic-colors-b.png`;
- `assets/UIF-002A/semantic-colors-c.png`;
- `assets/UIF-002A/palette-comparison.svg`;
- dieser Report.

Es wurden keine Produktdateien, Templates, Stylesheets, Services, Tests oder
Datenbankdateien für UIF-002A geändert. Der temporäre Study-Renderer wurde
nach der Artefakterzeugung entfernt.

## 3. Variante A – Current Sammlr Refined

| Token | Wert |
|---|---|
| `--color-background` | `#F6F3EF` |
| `--color-surface` | `#FFFFFF` |
| `--color-surface-subtle` | `#EEEAE5` |
| `--color-text-primary` | `#211D24` |
| `--color-text-secondary` | `#625B66` |
| `--color-text-muted` | `#766E79` |
| `--color-border` | `#DDD7DF` |
| `--color-border-strong` | `#C8C0CB` |
| `--color-accent` | `#6B32C9` |
| `--color-accent-hover` | `#5825AD` |
| `--color-accent-subtle` | `#F0E9FA` |
| `--color-accent-foreground` | `#FFFFFF` |
| `--color-success` | `#2E7150` |
| `--color-success-subtle` | `#E9F4ED` |
| `--color-warning` | `#9A5B18` |
| `--color-warning-subtle` | `#FFF2DC` |
| `--color-danger` | `#B23A32` |
| `--color-danger-subtle` | `#FCECEA` |

Charakter: die direkteste Evolution des heutigen Sammlr-Lilas. Der Accent ist
weiter klar und lebendig, aber weniger elektrisch; die warmen Neutralflächen
und ruhigen Statusfarben nehmen ihm visuelle Lautstärke.

## 4. Variante B – Deep Purple / Premium

| Token | Wert |
|---|---|
| `--color-background` | `#F5F2EE` |
| `--color-surface` | `#FFFFFF` |
| `--color-surface-subtle` | `#EEEAE6` |
| `--color-text-primary` | `#1F1B22` |
| `--color-text-secondary` | `#5D5761` |
| `--color-text-muted` | `#7C7480` |
| `--color-border` | `#DCD5DE` |
| `--color-border-strong` | `#C4BAC8` |
| `--color-accent` | `#54239A` |
| `--color-accent-hover` | `#421873` |
| `--color-accent-subtle` | `#EEE6F6` |
| `--color-accent-foreground` | `#FFFFFF` |
| `--color-success` | `#276A4A` |
| `--color-success-subtle` | `#E7F2EB` |
| `--color-warning` | `#8A5617` |
| `--color-warning-subtle` | `#FBF0DC` |
| `--color-danger` | `#A93632` |
| `--color-danger-subtle` | `#F8E9E8` |

Charakter: tieferes, satteres und stärker editorial wirkendes Lila. Der
Kontrast ist am höchsten, während Hintergrund und Cards bewusst freundlich
und hell bleiben. Die Variante bleibt produktnah und vermeidet Luxus-/Fashion-
Anmutung.

## 5. Variante C – Soft Modern

| Token | Wert |
|---|---|
| `--color-background` | `#F7F4F0` |
| `--color-surface` | `#FFFFFF` |
| `--color-surface-subtle` | `#F0ECE7` |
| `--color-text-primary` | `#242126` |
| `--color-text-secondary` | `#625D64` |
| `--color-text-muted` | `#777078` |
| `--color-border` | `#DED9DF` |
| `--color-border-strong` | `#C9C1CB` |
| `--color-accent` | `#73569B` |
| `--color-accent-hover` | `#624685` |
| `--color-accent-subtle` | `#F1EDF5` |
| `--color-accent-foreground` | `#FFFFFF` |
| `--color-success` | `#3B7258` |
| `--color-success-subtle` | `#EAF2ED` |
| `--color-warning` | `#93662B` |
| `--color-warning-subtle` | `#F8F0E3` |
| `--color-danger` | `#A84D49` |
| `--color-danger-subtle` | `#F7EBEA` |

Charakter: am stärksten entsättigte und harmonischste Variante. Sie setzt den
Accent kontrollierter ein, bleibt aber in Progress, Action und Active State
eindeutig und kontrastreich genug.

## 6. UIF-001-Polish in der Studie

Alle Varianten demonstrieren dieselben rein visuellen Feinjustierungen:

- Header-Brand mit 26 px und stärkerem Gewicht, weiterhin unterhalb der
  Seitentitel-Hierarchie;
- aktiver Favoritenstern als klarer Accent auf neutraler Fläche, ohne große
  violette Füllung oder Glow;
- aktiver Sammlungstab mit Accent und subtiler Accentfläche;
- mittlerer `sammlr.`-Tab im Sammlungsscreen vollständig neutral;
- aktiver und inaktiver `sammlr.`-Zustand zusätzlich nebeneinander in der
  isolierten Komponentendemo.

Die Komponentendemo zeigt außerdem Success, Warning und Danger, ohne diese als
Fake-Zustände in die reale Sammlung einzubauen.

## 7. Screenshotpfade

### Variante A

![Palette A bei 390 px](assets/UIF-002A/palette-a-390.png)

![Semantische Farben A](assets/UIF-002A/semantic-colors-a.png)

### Variante B

![Palette B bei 390 px](assets/UIF-002A/palette-b-390.png)

![Semantische Farben B](assets/UIF-002A/semantic-colors-b.png)

### Variante C

![Palette C bei 390 px](assets/UIF-002A/palette-c-390.png)

![Semantische Farben C](assets/UIF-002A/semantic-colors-c.png)

## 8. Viewport und Layoutmessung

Browser: Safari 26.6, DPR 2.

Alle sechs Artefakte wurden mit demselben echten CSS-Viewport von
**390 × 792 px** aufgenommen und besitzen deshalb **780 × 1584 Pixel**.

| Variante | Viewport | `scrollWidth` | Bottom Nav | Nav-Oberkante | letzter Albuminhalt unten im Bottom-State | Ergebnis |
|---|---:|---:|---:|---:|---:|---|
| A | 390 × 792 | 390 | 76 px | 708 px | 174 px | kein Overflow, keine Verdeckung |
| B | 390 × 792 | 390 | 76 px | 708 px | 174 px | kein Overflow, keine Verdeckung |
| C | 390 × 792 | 390 | 76 px | 708 px | 174 px | kein Overflow, keine Verdeckung |

Damit gilt für jede Variante `document.scrollWidth <= window.innerWidth`.
Header, Cards, Favoritensteuerung, CTA sowie aktive und inaktive Bottom-
Navigation liegen vollständig innerhalb des Viewports.

## 9. Tests

Gezielte bestehende UIF-/Collection-/Navigation-/Header-/Projection-Suite:

- `tests.test_uif001_collection_golden_screen`;
- `tests.test_s04_home_collection_routes`;
- `tests.test_s05_three_area_navigation`;
- `tests.test_s06_global_header_shell`;
- `tests.test_s30_design_foundation`;
- `tests.test_s31_ui_foundation`;
- `tests.test_cb013_collection_completion_projection`.

Ergebnis: **68/68 Tests**, 0 Fehler, 0 Skips.

Die Sammlung-Route blieb erfolgreich, read-only und funktional unverändert.
Die Testausgabe enthielt bereits bekannte `ResourceWarning`-Hinweise zu nicht
geschlossenen SQLite-Testverbindungen; sie verursachten keinen Fehler oder
Skip und stehen nicht mit der Palette Study in Zusammenhang.

## 10. Datenbanknachweis

| Prüfung | Vorher | Nachher |
|---|---|---|
| Schema | V7 (`schema_migrations`) | V7 (`schema_migrations`) |
| SHA-256 | `3ccaff9ca4b4140ab9338c23f486f57e0ae253605f79c47f03a79f46dafa9df4` | `3ccaff9ca4b4140ab9338c23f486f57e0ae253605f79c47f03a79f46dafa9df4` |
| `integrity_check` | `ok` | `ok` |
| `foreign_key_check` | leer | leer |

Der Browser-Renderer verwendete ausschließlich eine mit der SQLite Backup API
erzeugte temporäre Kopie. Die echte Bestands-DB wurde weder migriert noch
verändert.

## 11. Product-Owner-Entscheidung

**Freigegeben: Variante A – Current Sammlr Refined.**

Damit sind für das neue Sammlr Color System verbindlich:

- die neutralen Rollen und HEX-Werte aus Abschnitt 3;
- Sammlr Accent `#6B32C9`, Hover `#5825AD` und Accent Soft `#F0E9FA`;
- Success `#2E7150` mit Soft `#E9F4ED`;
- Warning `#9A5B18` mit Soft `#FFF2DC`;
- Danger `#B23A32` mit Soft `#FCECEA`.

Varianten B und C sind nicht freigegeben und bleiben ausschließlich
dokumentierte Studien. Aus ihnen dürfen keine Farben in die produktive
Palette übernommen werden.

Die Freigabe betrifft ausschließlich das Farbsystem. Die in der Study
verwendeten Komponentenproben, Icons und Detailzustände begründen keinen
eigenständigen Implementierungsauftrag.

## 12. Abschlussbewertungen

- Product-Contract-Verletzung: **NEIN**.
- Migration: **NEIN**.
- Produktlogik geändert: **NEIN**.
- Weitere Seiten redesigned: **NEIN**.
- Commit: **NEIN**.
- Push: **NEIN**.
- UIF-002 begonnen oder abgeschlossen: **NEIN**.
- Gewinnerpalette ausgewählt: **JA – Variante A**.
- Varianten B/C produktiv freigegeben: **NEIN**.
- UIF-002A visuell abgenommen: **JA**.

UIF-002A ist abgeschlossen und abgenommen. Für die Umsetzung des nächsten
UIF-Blocks ist dessen verbindlicher Scope aus der UI/UX-Roadmap maßgeblich.
