# UIF-001 – UI Foundation 1.0 und Golden Screen „Sammlung“

**Stand:** 23. August 2026

**Technischer Status:** GRÜN

**Visuelle Product-Owner-Abnahme:** AUSSTEHEND

**Migration:** NEIN

## 1. Ziel

UIF-001 führt die Designsprache „Modern Collector × Digital Museum“ als
wiederverwendbare, tokenbasierte Foundation ein und migriert ausschließlich
`/sammlung` als ersten Golden Screen. Fachlogik, Datenmodelle und die übrigen
Hauptscreens bleiben unverändert.

## 2. Inventarisierte Altstruktur

Die bisherige Sammlung verwendete den gemeinsamen großen Purple-Header, eine
separate weiße Seitentitelkarte, einen dominanten Purple-CTA, stark
verschattete Albumkarten, drei verschachtelte Statistikboxen und die global
stark hervorgehobene Bottom Navigation. Header, Albumkarten und Navigation
werden auch von noch nicht migrierten Screens verwendet.

Deshalb erfolgt die Migration über die Body-Klasse `uif-collection-page`,
einen opt-in Foundation-Header und einen eigenen Collection-Card-Renderer.
Bestehende globale Renderer und Altstyles bleiben für andere Screens erhalten.

## 3. Geänderte Dateien

- `App/webapp.py`;
- `App/static/style.css`;
- `tests/test_uif001_collection_golden_screen.py` neu;
- gezielt fortgeschriebene Altverträge in
  `tests/test_s04_home_collection_routes.py`,
  `tests/test_cb013_collection_completion_projection.py`,
  `tests/test_s31_ui_foundation.py` und
  `tests/test_cb017_integrated_rc.py`;
- drei Browserartefakte unter `assets/UIF-001/`;
- dieser Report.

Keine Backendservices, Migrationen oder Datenbankdateien wurden durch
UIF-001 geändert.

## 4. Design Tokens

Die neue zentrale `--uif-*`-Schicht umfasst:

- neutrale Page-, Surface- und Secondary-Surface-Farben;
- primären, sekundären und subtilen Text;
- Border, Accent Purple, Accent Soft sowie bestehende Statusfarben;
- Card-, Control- und Compact-Radien;
- zurückhaltende Card-/Elevated-Shadows;
- Page-, Section-, Card- und Elementabstände;
- Page-, Section-, Card-, Body-, Meta-, Statistik- und Labeltypografie;
- Navigationhöhe und Safe-Area-Berechnung.

Die Tokens sind zentral definiert, ihre Anwendung ist für UIF-001 aber bewusst
auf die Sammlung begrenzt.

## 5. Header-Verhalten

Der Golden Screen verwendet einen kompakten, neutralen, sticky Header mit
dunklem `sammlr`-Schriftzug und kleinem Purple-Punkt. Rechts bleiben Glocke,
echter Unread-Badge und Avatar-/Profilzugang erhalten. Die Touch Targets sind
44 × 44 px. Der reale Safari-Header ist mobil 58 px hoch und bleibt beim
Scrollen bei `top = 0`, ohne den erreichbaren letzten Karteninhalt zu
verdecken.

Nicht migrierte Screens behalten den bisherigen Header und das bestehende
Logoasset.

## 6. Albumkarten-Verhalten

Die Albumkarte ist jetzt das zentrale ruhige Sammlerobjekt:

- Cover und Inhaltsbereich ohne unnötige Card-in-Card-Struktur;
- Titel, optionale echte Metazeile, Fortschrittsformulierung und Prozentwert;
- neutraler 7-px-Track mit Purple Fill;
- Sticker, Doppelte und verfügbare fehlende Sticker als klare Werte ohne
  Statistik-Mini-Cards;
- gesamte Inhaltskarte bleibt Albumlink;
- separater 44-px-Favoriten-Control führt zum bestehenden Auswahlpfad;
- aktiver Favorit ist zusätzlich strukturell und nicht nur farblich markiert.

Die Metazeile ist konservativ: `VfL Osnabrück` zeigt das echte zusätzliche
`2024/25`. `EURO 2024 / Germany` und `FIFA World Cup 2026 / 2026` werden nicht
redundant beziehungsweise unbegründet dargestellt. Es wurde keine neue
Album-Metadatenquelle eingeführt.

## 7. Bottom Navigation

Die drei bestehenden Ziele bleiben unverändert und gleichwertig:

1. Sammlung;
2. sammlr.;
3. Tauschen.

Auf dem Golden Screen verwendet die Navigation eine helle, neutrale Surface.
Der aktive Zustand kombiniert Purple für Icon/Text mit einer subtilen
Soft-Surface und `aria-current="page"`; der mittlere Bereich ist nicht mehr
vollflächig hervorgehoben oder angehoben. Safe Area und unterer Content-Inset
bleiben berücksichtigt. Der bestehende Desktop-Fallback blendet die mobile
Bottom Navigation ab 900 px weiterhin aus.

## 8. Responsive-Ergebnis

Echter Safari 26.6.1, DPR 2:

| Zustand | Viewport | Dokumentbreite | Kartenbreite | Ergebnis |
|---|---:|---:|---:|---|
| kleinster von Safari zugelassener Desktop-WebDriver | 336 × 792 | 336 | 312 | kein Overflow |
| Golden Screen | 390 × 792 | 390 | 366 | kein Overflow |
| großes Mobile | 430 × 792 | 430 | 406 | kein Overflow |
| Desktop-Fallback | 1024 × 848 | 1024 | 920 | kein Overflow; Bottom Nav verborgen |

Safari akzeptierte den angeforderten 320-px-Fensterwert nicht und klemmte ihn
auf sein reales Minimum von 336 px. Dieser nächstmögliche echte Zustand nutzt
bereits den `max-width:350px`-Vertrag. Lange Titel brechen kontrolliert um; die
reale fünfstellige Doppeltenzahl `10182` bleibt vollständig lesbar.

Im unteren Scrollzustand lagen bei 336, 390 und 430 px jeweils rund 200 px
zwischen der Unterkante der letzten Albumkarte und der Oberkante der Bottom
Navigation. Damit wird der letzte Inhalt nicht verdeckt.

## 9. Accessibility-Prüfung

- semantische Links für Album, CTA, Favorit, Profil und Navigation;
- Notification-Öffnung bleibt ein CSRF-geschütztes POST-Formular;
- 44-px-Touch-Targets für Headeraktionen, Favorit und CTA;
- `role="progressbar"` mit Min/Max/Aktuellwert;
- Unread-Badge mit tatsächlichem zugänglichem Zähler;
- `aria-current="page"` für den aktiven Navigationsbereich;
- bestehender `focus-visible`- und Reduced-Motion-Vertrag bleibt aktiv;
- aktive Zustände besitzen neben Farbe auch Markup-/Shape-/Current-State-
  Hinweise.

## 10. Fachliche Funktionen vor/nach

Unverändert erhalten und geprüft sind:

- alle aktiven Alben und Albumöffnung;
- Album hinzufügen;
- Favoritenauswahl;
- Fortschritt, Sticker, Doppelte und Verfügbarkeit aus denselben Services;
- historische Abschlüsse aus der bestehenden kanonischen Projektion;
- Notification-Badge und Glocke;
- Profilzugang;
- alle drei Bottom-Nav-Ziele;
- Privacy-/Completion- und read-only GET-Verträge.

Reale Safari-Klicks erreichten `/album/wm26`, `/alben/hinzufuegen`,
`/favorit?auswahl=1`, `/profil`, `/`, `/trades` und `/notifications`.

## 11. Gezielte Tests

Die gezielte UIF-/Collection-/Navigation-/Header-/Projection-Suite bestand
**68/68 Tests**, 0 Fehler, 0 Skips. Sie umfasst den neuen UIF-001-Vertrag sowie
S04, S05, S06, S30, S31 und CB-013.

Ein erster Plain-Discovery-Diagnoselauf war kein gültiger Regressionlauf,
weil er das bekannte `tests/__init__.py`-Environment-Bootstrap umging. Dabei
wurde außerdem ein historischer CSS-Stringtest auf seinen eigenen S31-Block
begrenzt. Es entstand keine Produkt- oder Datenänderung.

## 12. Regression

Die kanonische Paket-Discovery bestand anschließend **721/721 Tests** in
8,513 Sekunden, 0 Fehler, 0 Skips.

Zusätzlich:

- `py_compile` für alle geänderten Pythondateien: grün;
- `git diff --check`: ohne Befund;
- echte Safari-Smokes und Klickpfade: grün.

## 13. Datenbank verändert

**Durch UIF-001: NEIN.**

Der Browser verwendete ausschließlich einen per SQLite Backup API erzeugten
isolierten V7-Snapshot. Der Notification-Klick wirkte nur auf diese Kopie.
Die echte Bestands-DB blieb bei Schema V7, `integrity_check = ok` und leerem
`foreign_key_check`.

Ihr aktueller SHA-256 ist
`5158960cb54da0914395a03568ea24aefb8b632ddbf9aae47f0db5e8b77bcd7e`.
Dieser Stand datiert laut Dateisystem vom 21. August 2026, 21:28:30 CEST und
liegt damit vor UIF-001. Der zu Beginn erzeugte Browser-Snapshot und die
Bestands-DB nach UIF-001 besitzen denselben vollständigen logischen
SQLite-Dump-Hash
`6db7fcfa42b1136d1da702a3d7cca1ab77e5838e75eeddae64f402560a3daa39`.

## 14. Bekannte visuelle Restpunkte

- Die Product-Owner-Sichtprüfung ist ausdrücklich noch offen.
- Safari konnte nicht unter sein echtes WebDriver-Minimum von 336 px
  verkleinert werden; der 320-nahe CSS-Vertrag wurde deshalb bei 336 px real
  und zusätzlich automatisiert geprüft.
- Die bestehenden Cover-/Album-Art-Platzhalter wurden vertragsgemäß nicht
  ersetzt.
- Andere Hauptscreens behalten bewusst die bisherige Designsprache, bis ein
  späterer freigegebener Migrationsblock folgt.

## 15. Product-Contract-Verletzungen

**NEIN.** Keine Backend-, Inventory-, Trade-, Trophy-, Feed-, Privacy-,
Notification-, Auth- oder Datenbanksemantik wurde geändert. Es gibt keine neue
Migration und keine neue Frontend-Abhängigkeit.

## 16. Empfehlung zur visuellen Abnahme

Der Product Owner sollte primär den 390-px-Topzustand und den unteren
Scrollzustand prüfen, ergänzend den 336-px-Zustand für lange Titel und große
Zahlen. Technisch ist der Golden Screen abnahmebereit.

![Sammlung bei 390 px](assets/UIF-001/sammlung-390-top.png)

![Sammlung bei 390 px im unteren Scrollzustand](assets/UIF-001/sammlung-390-scroll.png)

![Sammlung beim kleinsten Safari-Fenster mit 336 px](assets/UIF-001/sammlung-336-top.png)

## 17. Kann UIF-002 begonnen werden?

**NEIN.** Zuerst ist die ausdrücklich verlangte visuelle Product-Owner-
Freigabe für UIF-001 erforderlich.

Kein Commit und kein Push wurden ausgeführt.
