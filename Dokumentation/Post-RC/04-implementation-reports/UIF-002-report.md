# UIF-002 – Global App Shell / Sammlr Design Foundation

**Stand:** 23. August 2026

**Status:** TECHNISCH UMGESETZT – VISUELLE PO-ABNAHME AUSSTEHEND

**Migration:** NEIN

**Nächster Block:** UIF-003 bleibt bis zur visuellen PO-Abnahme gesperrt

## 1. Ergebnis und Scope

UIF-002 konsolidiert die globale App-Shell auf Basis der in UIF-002A
freigegebenen Palette A „Current Sammlr Refined“. Die Änderung umfasst den
neutralen Header, eine gemeinsame Seiten- und Typografiebasis, die neutrale
Bottom Navigation sowie tokenisierte gemeinsame Komponenten. Routen,
Produktlogik und Datenverträge blieben unverändert.

Nicht vorgezogen wurden Feed-, Tauschen-, Tradeflow-, Stickerwall-, Trophy-,
Profil- oder Freunde-Redesigns. Es wurden weder Chat/Messaging noch neue
Community-Funktionen, Icons, Cover oder Produktzustände implementiert.

## 2. Verbindlicher visueller Vertrag

Die Produkt-CSS enthält Palette A als einzige kanonische Farbquelle:

| Rolle | Wert |
|---|---|
| App-Hintergrund | `#F6F3EF` |
| Surface / Subtle | `#FFFFFF` / `#EEEAE5` |
| Text primär / sekundär / muted | `#211D24` / `#625B66` / `#766E79` |
| Border / stark | `#DDD7DF` / `#C8C0CB` |
| Accent / Hover / Soft | `#6B32C9` / `#5825AD` / `#F0E9FA` |
| Success / Soft | `#2E7150` / `#E9F4ED` |
| Warning / Soft | `#9A5B18` / `#FFF2DC` |
| Danger / Soft | `#B23A32` / `#FCECEA` |

Bestehende `--sammlr-*`- und UIF-001-Tokens verweisen auf diese kanonischen
Rollen. Farben aus den Studien B und C wurden nicht produktiv übernommen.
Fachlich getrennte Bestands-/Trade-Statusfarben blieben erhalten, damit UIF-002
keine Produktsemantik verändert.

## 3. Globaler Header

Der gemeinsame Header rendert auf den geprüften Produktseiten:

- links die textbasierte `sammlr.`-Wortmarke mit Accent-Punkt;
- rechts die bestehende Notification-Aktion samt unverändertem Unread-Badge;
- den bestehenden Profilzugang mit Avatarinitiale;
- eine flexible Aktionsfläche, aber keinen Chat- oder Messaging-Zugang.

Die vormals große violette Headerwirkung ist durch eine kompakte, ruhige
Surface mit dezentem Border und Shadow ersetzt. Im Safari-Smoke wurde eine
CSS-Spezifitätskollision gefunden und behoben: Der allgemeine Primary-Button-
Selektor erfasste zunächst den submit-basierten Glocken-Button. Die Auswahl
schließt nun `.app-header-action` explizit aus; die Glocke bleibt neutral.

## 4. Page Layout und Komponentenbasis

Die globale Foundation vereinheitlicht ohne Seitenredesign:

- Page Title und Subtitle mit klarer Hierarchie und umbrechbaren Texten;
- Surface/Card, Primary und Secondary Button sowie Icon-Button;
- Notification-Badge, Inputs/Search-Surfaces und Progress Bars;
- Active/Inactive Navigation;
- Success, Attention/Warning und Problem/Error;
- ruhige Shadows, Borders, Radien und mobile Abstände.

Der Favoritenstern wurde ausschließlich auf die neue Palette normalisiert.
Seine endgültige Form und das globale Iconsystem bleiben UIF-011 vorbehalten.

## 5. Bottom Navigation

Die drei bestehenden Ziele und Routen bleiben unverändert:

1. Sammlung → `/sammlung`;
2. sammlr. → `/`;
3. Tauschen → `/trades`.

Die Navigation nutzt eine ruhige Surface. Der aktive Zustand verwendet
Accent auf Accent Soft, inaktive Zustände sekundären Text auf transparenter
Fläche. Das mittlere `sammlr.`-Ziel besitzt inaktiv keinen weißen/negativen
Sonderzustand. Die Icons wurden funktional und formal nicht neu gestaltet.

## 6. Responsive Safari-Nachweis

Browser: Safari 26.6, DPR 2. Gemessen wurde im normalen Safari-Fenster auf
einer isolierten SQLite-Kopie. Die verfügbare Bildschirmhöhe ergab jeweils
einen CSS-Viewport von 768 px Höhe; die geforderten Breiten wurden exakt
gesetzt.

| Route/Zustand | Viewport | Dokumentbreite | Header | Bottom Nav | Body-Padding unten | Overflow |
|---|---:|---:|---:|---:|---:|---|
| Sammlung, Minimum | 336 × 768 | 336 px | 312 × 58 px | 320 × 76 px | 104 px | keiner |
| Sammlung | 390 × 768 | 390 px | 366 × 58 px | 370 × 76 px | 104 px | keiner |
| Sammlung | 430 × 768 | 430 px | 406 × 58 px | 410 × 76 px | 104 px | keiner |
| Feed/Home | 390 × 768 | 390 px | 366 × 58 px | 370 × 76 px | 112 px | keiner |
| Tauschen | 390 × 768 | 390 px | 366 × 58 px | 370 × 76 px | 112 px | keiner |
| Profil | 390 × 768 | 390 px | 366 × 58 px | 370 × 76 px | 112 px | keiner |

Für alle Messungen gilt `document.scrollWidth <= window.innerWidth`. Der
Bottom-Abstand ist größer als die 76 px hohe Navigation einschließlich ihres
8-px-Inset; Inhalte bleiben am Scrollende erreichbar. Die DOM-Prüfung meldete
keine über den Viewport hinausragenden sichtbaren Elemente. Wortmarke, Glocke
und Profilzugang waren vorhanden; ein Chat-Zugang war nicht vorhanden.

## 7. Screenshot-Artefakte

- [Sammlung bei 336 px](assets/UIF-002/sammlung-shell-336.png)
- [Sammlung bei 390 px](assets/UIF-002/sammlung-shell-390.png)
- [Sammlung bei 430 px](assets/UIF-002/sammlung-shell-430.png)
- [Feed/Home bei 390 px](assets/UIF-002/feed-shell-390.png)
- [Tauschen bei 390 px](assets/UIF-002/trades-shell-390.png)
- [Profil bei 390 px](assets/UIF-002/profile-shell-390.png)

Die PNGs zeigen das vollständige normale Safari-Fenster inklusive Browser-
Chrome; das Layout selbst wurde im angegebenen CSS-Viewport vermessen.

## 8. Tests

### Gezielte UIF-002-Suite

Die gezielte Shell-/Navigation-/Foundation-/Collection-/Feed-Suite umfasste
nach der Implementierung **86 Tests** und nach der Safari-Korrektur nochmals
die unmittelbar betroffenen **66 Tests**. Beide Läufe endeten mit 0 Fehlern
und 0 Skips.

Neu ist `tests/test_uif002_global_app_shell.py`. Der Test schützt:

- die exakten Palette-A-Rollen und den Ausschluss der B/C-Farben;
- den gemeinsamen Header auf Feed, Sammlung, Tauschen und Profil;
- Routen und aktive Zustände der Bottom Navigation;
- die tokenisierte Komponentenbasis und responsive Breakpoints;
- read-only GETs auf einer temporären DB;
- die vollständige UIF-Roadmap und die Abgrenzung von Chat/Messaging.

Bestehende Header-, UIF-001- und S30-Assertions wurden an den neuen globalen
Vertrag angepasst, ohne ihre Funktions- oder Kontrastprüfung zu entfernen.

### Vollregression

Erster technischer Abnahmelauf vor der visuellen PO-Nacharbeit:

- **728 Tests**;
- **0 Fehler**;
- **0 Skips**;
- Laufzeit **7,957 s**.

Der nach den beiden PO-Restpunkten erneut ausgeführte finale Lauf ist in
Abschnitt 12 dokumentiert.

## 9. Datenbank- und Qualitätsnachweis

| Prüfung | Ergebnis |
|---|---|
| Migration | keine |
| Schema | V7 |
| SHA-256 vorher | `3ccaff9ca4b4140ab9338c23f486f57e0ae253605f79c47f03a79f46dafa9df4` |
| SHA-256 nachher | `3ccaff9ca4b4140ab9338c23f486f57e0ae253605f79c47f03a79f46dafa9df4` |
| `PRAGMA integrity_check` | `ok` |
| `PRAGMA foreign_key_check` | leer |
| `git diff --check` | ohne Befund |

Die Browser-Smokes verwendeten eine isolierte SQLite-Backupkopie. Die echte
Bestands-DB wurde nicht migriert und durch UIF-002 nicht verändert.

## 10. Geänderte UIF-002-Dateien

- `App/webapp.py`;
- `App/static/style.css`;
- `tests/test_uif002_global_app_shell.py`;
- `tests/test_uif001_collection_golden_screen.py`;
- `tests/test_s06_global_header_shell.py`;
- `tests/test_s30_design_foundation.py`;
- `Dokumentation/Post-RC/04-design-system.md`;
- `Dokumentation/Post-RC/05-ui-backlog.md`;
- dieser Report und die sechs Screenshot-Artefakte.

Die vorausgehende PO-Freigabe von Palette A wurde außerdem im bestehenden
`UIF-002A-color-study.md` als abgenommen dokumentiert.

## 11. Product-Contract-Bewertung und Restrisiko

**Product-Contract-Verletzung: NEIN.** Es wurden keine Routen, Datenzugriffe,
Writes, Domainzustände, Notifications, Feedregeln oder Privacy-Regeln
verändert. Eine Migration war weder erforderlich noch zulässig.

Die absichtlich noch nicht neu gestalteten Seiten können bis zu ihren eigenen
UIF-Paketen unterschiedliche interne Dichte oder ältere Iconformen behalten.
Das ist die vereinbarte Paketgrenze, kein unvollständiger UIF-002-Teil.

UIF-002 ist technisch vollständig und als visueller PO-Abnahmestand
bereitgestellt. **UIF-003 darf erst nach der ausdrücklichen visuellen Abnahme
von UIF-002 beginnen.**

## 12. Visuelle PO-Nacharbeit – Favorit und Bottom Navigation

Am 23. August 2026 gab der Product Owner die Sammlung grundsätzlich frei und
benannte exakt zwei verbleibende UIF-002-Punkte. Es wurden ausschließlich
diese beiden Punkte bearbeitet.

### 12.1 Favoriten-State

Die gespeicherte Favoritenlogik war korrekt: Der Renderer verglich jedes Album
mit genau dem einen `users.favorite_album_id`. Die visuelle Abweichung entstand
durch einen späten UIF-002-Selektor, der aktive und inaktive Favoriten-Controls
gemeinsam lila einfärbte.

Die Korrektur trennt die Zustände wieder eindeutig:

- inaktiv: 18-px-Stern in Muted-Grau, ohne sichtbare Fläche oder Border;
- aktiv: derselbe 18-px-Stern in Sammlr-Lila auf einer lediglich 28 × 28 px
  großen Accent-Soft-Fläche;
- der unsichtbare interaktive Bereich bleibt für Accessibility **44 × 44 px**;
- kein Glow und keine zusätzliche Hervorhebung der gesamten Albumkarte.

Echter Safari-Nachweis auf der isolierten DB-Kopie:

- vor der Aktion war `em24` der einzige Favorit;
- der echte CSRF-geschützte Browserrequest schaltete auf `wm26` um;
- nach anschließendem Browser-Reload blieb `wm26` der einzige Favorit;
- Ergebnis: `ok=true`, `count=1`, `reloaded=true`.

Die echte Bestands-DB wurde dabei nicht verwendet und nicht verändert.

### 12.2 Bottom-Nav-Zuordnung

Die drei Hauptwelten projizieren exklusiv:

| Route | Sammlung | sammlr. | Tauschen |
|---|---|---|---|
| `/sammlung` | aktiv | neutral | neutral |
| `/` | neutral | aktiv | neutral |
| `/trades` | neutral | neutral | aktiv |
| `/profil` | neutral | neutral | neutral |
| `/notifications` | neutral | neutral | neutral |

Albumdetail, Albumstatistik und Albumtrophäen bleiben der Sammlungswelt
zugeordnet; Trade-Unterseiten bleiben der Tauschen-Welt zugeordnet. Profil,
Account, Freunde, globale Trophäen/Statistik und Notifications erzeugen keinen
willkürlichen Hauptwelt-State. Zwei öffentliche Profil-Albumrouten wurden von
der fälschlichen Sammlung-Aktivierung auf den neutralen Profilkontext
korrigiert.

Im echten Safari wurden alle drei sichtbaren Hauptlinks tatsächlich
nacheinander angeklickt. Der Klickpfad erreichte erfolgreich
`/sammlung → / → /trades`; alle drei Links hatten `pointer-events:auto` und
jeweils rund 117 px Breite.

### 12.3 Finaler 390-px-Smoke

- Safari 26.6, CSS-Viewport **390 × 763 px**, DPR 2;
- `document.scrollWidth = 390 px` auf allen geprüften Zuständen;
- keine Overflow-Offender;
- Bottom Navigation **370 × 76 px**, vollständig im Viewport;
- Sammlung-Endcontent endet bei 479 px gegenüber Nav-Oberkante 679 px;
- Albumdetail-Endcontent endet bei 447,36 px gegenüber Nav-Oberkante 679 px;
- Albumdetail-Navigation und alle drei Hauptziele erreichbar;
- Profil und Notifications ohne Active State.

### 12.4 Finale Tests und Datenbankprüfung

Gezielte UIF-/Collection-/Navigation-/Header-/Projection-Suite nach der
Nacharbeit: **89/89 Tests**, 0 Fehler, 0 Skips.

Finale Vollregression nach der Nacharbeit:

- **731 Tests**;
- **0 Fehler**;
- **0 Skips**;
- Laufzeit **8,171 s**.

| Prüfung | Finales Ergebnis |
|---|---|
| Schema | V7 |
| SHA-256 | `3ccaff9ca4b4140ab9338c23f486f57e0ae253605f79c47f03a79f46dafa9df4` |
| `PRAGMA integrity_check` | `ok` |
| `PRAGMA foreign_key_check` | leer |
| `git diff --check` | ohne Befund |

Die vier 390-px-Screenshots für Sammlung, sammlr.-Home, Tauschen und Profil
wurden nach der Nacharbeit vom normalen Produktserver ohne Messinjektion
aktualisiert. UIF-002 bleibt bis zur visuellen PO-Entscheidung offen; UIF-003
wurde nicht begonnen.
