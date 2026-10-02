# S27 – Album-Privacy und getrennter Tradepool

Stand: 2026-08-08

## Ziel

S27 setzt die Album-Sichtbarkeit `public`, `friends` und `private`
serverseitig durch und führt eine davon fachlich unabhängige
Tradepool-Teilnahme ein. Sammler kontrollieren die Inspektion ihrer Albumdaten,
ohne private Alben automatisch aus Matching oder Smart Trades zu entfernen.

## Verbindliche Invarianten

- Privacy wird pro `user_albums`-Zuordnung gespeichert.
- Erlaubte Sichtbarkeiten sind exakt `public`, `friends`, `private`.
- Bestehende und neue Zuordnungen starten sicher als `private`.
- `trade_pool_enabled` ist ein separates boolesches Feld mit Standard `true`.
- Privacy darf nie als Tradepool-Regel verwendet werden.
- Tradepool-Eignung darf nie als Berechtigung zur allgemeinen Albuminspektion
  verwendet werden.
- Eigentümer sehen das eigene Album unabhängig von der Privacy-Stufe.
- `public` erlaubt jeden angemeldeten Nutzer.
- `friends` erlaubt neben dem Eigentümer nur einen positiv geprüften Freund.
- Mangels S29-Freundschaftssystem ist der produktive Friend-Check stets
  negativ; nur eine injizierbare Testnaht kann ihn positiv beantworten.
- `private` erlaubt ausschließlich den Eigentümer.
- Nicht vorhandene und nicht sichtbare fremde Alben sind identisch HTTP 404.
- Kein nicht autorisierter Pfad rendert Albumname, Wall, Codes, Mengen oder
  daraus abgeleitete Albumaggregate.
- Ein Fremdprofil berechnet Albumzahl und Doppelte nur aus für den Betrachter
  sichtbaren Alben.
- Erfolgreiche Trades und Trophy-Anzahl bleiben albumunabhängig sichtbar.
- Ein konkreter Match-/Trade-Kontext darf nur seine fachlich notwendigen
  Positionen und Mengen zeigen, nie eine allgemeine Bestandsinspektion.

## Migration V0007

`user_albums` erhält:

- `visibility TEXT NOT NULL DEFAULT 'private'` mit Check auf die drei Werte,
- `trade_pool_enabled INTEGER NOT NULL DEFAULT 1` mit booleschem Check.

Die Up-Migration setzt damit bestehende Zuordnungen sicher auf `private` und
lässt ihre bestehende Tradepool-Teilnahme aktiv. Die Down-Migration stellt die
V0006-Tabellenform und alle Zuordnungen ohne die beiden S27-Felder wieder her.
Es entsteht keine weitere Tabelle.

## Architektur

### `AlbumPrivacyService`

Der zentrale S27-Service kapselt:

- Laden einer Albumzuordnung als immutable DTO,
- Sichtbarkeitsentscheidung für Eigentümer, Fremde und injizierte Freunde,
- gefilterte sichtbare Zuordnungen eines Profilinhabers,
- Tradepool-Eignung eines Nutzers/Albums,
- Liste tradepool-aktivierter Nutzer je Album,
- validierte Eigentümeränderung von Privacy und Tradepool.

Der standardmäßige Friendship-Resolver liefert immer `False`. Tests können
eine reine Funktion injizieren. Es werden keine Freundschaftsdaten gespeichert
und keine S29-Logik implementiert.

### DTOs und Codes

`AlbumAccessDTO` enthält:

- Eigentümer-ID,
- Album-ID,
- Sichtbarkeit,
- Tradepool-Flag.

`AlbumPrivacyUpdateCode` unterscheidet:

- `updated`,
- `not_found`,
- `invalid_visibility`,
- `unauthorized`.

## Datenfluss

### Fremdprofil

```text
GET /profil/<username>
→ CollectorProfileService mit aktuellem Betrachter
→ AlbumPrivacyService.visible_album_ids(...)
→ InventoryReadService nur für sichtbare Alben
→ Albumzahl und Doppelte aus derselben sichtbaren Menge
→ Trades und Trophy-Anzahl unverändert albumunabhängig
```

### Fremdes Album

```text
GET /profil/<username>/album/<album_id>
→ Nutzer + Zuordnung laden
→ AlbumPrivacyService.can_view(...)
→ nein oder unbekannt: 404 vor jedem Inventory-Read/Rendern
→ ja: InventoryReadService
→ Fortschritt + vollständige read-only Wall + exakte Mengen
```

Die read-only Sticker-Detailroute unter demselben Fremdalbum-Pfad wiederholt
dieselbe Berechtigungsprüfung vor jedem Detail-Read.

### Eigentümereinstellung

```text
POST /album/<album_id>/privacy
→ Sessionnutzer muss Eigentümer der Zuordnung sein
→ visibility exakt validieren; ungültig = 400
→ trade_pool_enabled aus explizitem Formularwert
→ beide Felder atomar aktualisieren
→ zur bestehenden eigenen Albumseite zurück
```

Die kompakte Auswahl liegt direkt auf der bestehenden Albumseite. Es entsteht
keine Einstellungsseite.

### Tradepool

```text
user_albums.trade_pool_enabled
→ AlbumPrivacyService.trade_pool_user_ids(...)
→ globale/albumbezogene Tauschbörse
→ S20 Coverage
→ S21 TopMatch
→ S22 Smart-Berechnung, Erstellung und Recheck
```

Die `visibility`-Spalte wird auf diesem Pfad nicht gelesen. Ein privates Album
mit aktivem Pool bleibt matchbar; ein öffentliches Album mit deaktiviertem Pool
bleibt sichtbar, aber ist kein Matchkandidat.

## Sichtbarkeitsmatrix

| Betrachter | public | friends | private |
| --- | --- | --- | --- |
| Eigentümer | sichtbar | sichtbar | sichtbar |
| positiv injizierter Friend-Testdouble | sichtbar | sichtbar | nicht sichtbar |
| normaler angemeldeter Fremder | sichtbar | nicht sichtbar | nicht sichtbar |

Nicht sichtbar bedeutet auf Profilen: Albumname und albumbezogene Aggregate
fehlen. Bei direkter Fremdalbum- oder Detail-URL bedeutet es HTTP 404.

## Sichtbare Fremdalbumdaten

Nach erfolgreicher Berechtigung dürfen erscheinen:

- Albumname,
- Fortschritt,
- vollständige Stickerwall,
- fehlende, vorhandene und doppelte Sticker,
- exakte Mengen.

Die Ansicht ist read-only. Sie enthält keine Mengenbuttons, Formulare,
Bestandswrites, Tradepool-Einstellung oder Eigentümer-Navigation.

## Abgeleitete Ansichten

- Eigenes Profil und eigene Albumseite bleiben vollständig verfügbar.
- Fremdprofil filtert Albumzahl, Doppelte, aktive Alben und Vitrine nach
  `can_view`.
- Fremde Wall und Mengen-/Detailansicht prüfen `can_view` direkt.
- Globale und albumbezogene Tauschbörse verwenden ausschließlich
  `trade_pool_enabled`; ihre Anzeige bleibt auf konkrete Matchpositionen und
  notwendige Mengen begrenzt.
- S20 Coverage filtert Subjekt und Gegenüber nach Tradepool-Teilnahme.
- S21 TopMatch verwendet die gefilterte S20-Coverage und poolberechtigte
  Partnerkandidaten.
- S22 Smart Requests prüfen Tradepool-Eignung bei Berechnung, Erzeugung und
  Recheck. Gespeicherte Pakete werden nicht automatisch angepasst.
- Bestehende angenommene oder laufende Trades bleiben unabhängig von einer
  späteren Pooländerung lesbar und abwickelbar.

## Seiteneffekte

Neu schreibend sind ausschließlich:

- Migration V0007,
- expliziter Eigentümer-POST für die zwei S27-Einstellungen.

Alle Profil-, Fremdalbum-, Wall-, Detail-, Matching- und Coverage-GETs bleiben
read-only. S27 erzeugt keine Notification und keinen Trade.

## Betroffene Komponenten

- V0007 Up-/Down-Migration,
- neuer Album-Privacy-/Tradepool-Service,
- S26-Profilprojektion,
- eigene Albumseite und kompakter Einstellungs-POST,
- neue Fremdalbum- und Fremdsticker-Detailroute,
- zentrale Coverage-/TopMatch-/Smart-Trade-Kandidatenzuführung,
- globale und albumbezogene Tauschbörse,
- S27-Tests und Dokumentation.

## Unveränderte Komponenten

- Inventory Read/Write, Availability, Guard und Snapshot,
- Trade Lifecycle, Reservierungen, Shipping, Receipt und Problems,
- bestehende Tradepakete und laufende Trades,
- S20-Berechnungsformeln, S21-Score und S22-Paketregeln,
- Notifications und Operational Home,
- Freunde, Bewertungen, Blockieren und Aktivstatus,
- S28 und S29.

## Testvertrag

Getestet werden:

- V0007 Up, Default/Backfill, Wiederholung und Down,
- exakt drei Sichtbarkeitswerte und boolescher Tradepool,
- Eigentümer, Fremder und Friend-Testdouble je relevante Stufe,
- HTTP 404 ohne Existenzoffenlegung,
- Eigentümer-Update, 400 bei Manipulation und Fremdschutz,
- vollständige public Fremdwall und read-only Mengendetail,
- kein privater Code-, Mengen- oder Albumname-Leak,
- gefilterte S26-Albumzahl und Doppelte bei unveränderten Trade-/Trophy-
  Aggregaten,
- privates Pool-Album matchbar,
- öffentliches Nicht-Pool-Album sichtbar, aber nicht matchbar,
- S20 Coverage, S21 TopMatch und S22 Smart Requests,
- globale und albumbezogene Tauschbörse,
- keine Mutation durch fremde GETs,
- vollständige S01–S27-Regression.

## Risiken und Gegenmaßnahmen

- **Privacy/Pool vermischt:** getrennte Spalten und getrennte Servicemethoden;
  Tests für beide Gegenbeispiele.
- **Nebenroute leakt:** dieselbe Access-Prüfung vor Wall und Detail; 404 vor
  Inventory-Aufruf.
- **Fremdprofil-Aggregat leakt:** Inventory wird nur für sichtbare Zuordnungen
  gelesen.
- **Friends vorgezogen:** produktiver Resolver bleibt immer negativ.
- **Direkt-POST manipuliert:** Eigentümerbindung plus exakte Enum-Validierung.
- **Legacy-Tests ohne V0007:** Schemaerkennung bewahrt auf nicht migrierten
  isolierten Alt-Fixtures das bisherige Verhalten; V0007 selbst setzt sichere
  Defaults.
- **laufender Trade blockiert:** Poolfilter gilt nur Kandidatenbildung und neue
  Smart-Ausführbarkeit, nicht Lifecycle-/Historienzugriff.
