# S26-Abschlussbericht – Eigenes und fremdes Profilfundament

Stand: 2026-08-08

## Ziel und Ergebnis

S26 ist umgesetzt. Das Profil ist nun eine mobile Sammlerseite mit Identität,
vier verbindlichen Kennzahlen, aktiven Alben, Vitrine und Trophy-Anzahl. Das
eigene Profil bewahrt seine vorhandenen Bearbeitungs- und Unterseitenzugänge.
Fremde Profile sind unter `/profil/<username>` konservativ, strikt read-only
und ohne private Bestands- oder Trophy-Details erreichbar.

S27 wurde nicht begonnen.

## Architektur

Der neue `CollectorProfileService` bildet bestehende Daten ausschließlich
read-only auf immutable DTOs ab:

- `CollectorAlbumDTO` für Albumname und zentral gelesenen Fortschritt,
- `CollectorProfileDTO` für Identität, Albumgruppen und Aggregate.

Der Service erhält eine bestehende SQLite-Verbindung und besitzt keine Commit-,
Insert-, Update- oder Delete-Operation. Er verwendet:

- `users` als bestehende Identitätsquelle,
- `user_albums` und `albums` für Albumzuordnung und Namen,
- `InventoryReadService` für Albumfortschritt und Doppelte,
- `trade_requests` mit optional zugeordnetem Lifecycle-Trade für erfolgreiche
  Tradezahlen,
- `unlocked_trophies` für die persistierte Trophy-Anzahl.

Es gibt keine zweite Inventory-, Fortschritts-, Abschluss- oder Trophy-
Freischaltungslogik.

## Datenfluss

```text
GET /profil
→ Sessionnutzer intern per ID
→ CollectorProfileService
→ gemeinsame Profilhierarchie
→ vorhandene Eigentümerlinks und Bearbeitung

GET /profil/<username>
→ exakte Auflösung über eindeutigen Username
→ unbekannt: HTTP 404
→ CollectorProfileService
→ konservative read-only Fremdsicht
```

Ein bereits sichtbarer Partnername in der berechtigten Trade-Detailansicht
verlinkt sicher auf `/profil/<username>`.

## Profilvertrag

Verbindliche mobile Reihenfolge:

1. Identität,
2. kompakte Kennzahlen,
3. aktive Alben,
4. Vitrine,
5. Trophy-Anzahl,
6. nur beim Eigentümer: bestehende Unterseiten und Kontoeinstellungen.

Exakt vier Kennzahlen:

- Anzahl zugeordneter Alben,
- Gesamtzahl Doppelte,
- Anzahl erfolgreicher Trades,
- Anzahl freigeschalteter Trophäen.

Aktiv bedeutet `collected < total`; Vitrine bedeutet `collected >= total`.
Der Fortschritt stammt aus `InventoryReadService.album(...).progress(...)`.

## Erfolgreiche Trades

Ein Trade wird genau einmal anhand seiner eindeutigen Legacy-Request-ID
gezählt:

- `trade_requests.status='completed'` ohne Lifecycle-Zeile bleibt als
  lesbarer Legacy-Abschluss enthalten,
- bei vorhandener Lifecycle-Zeile muss zusätzlich
  `lifecycle_state='completed'` gelten,
- offene, angenommene, fehlgeschlagene, abgelehnte, abgelaufene, obsolete oder
  inkonsistente Trades zählen nicht.

Lifecycle und Legacy-Repräsentation desselben fachlichen Trades können dadurch
keine Doppelzählung erzeugen.

## Sichtgrenzen

Fremd sichtbar:

- Username und optional vorhandener Klarname,
- vier aggregierte Kennzahlen,
- Namen aktiver Alben,
- Namen abgeschlossener Vitrinenalben,
- kompakte Trophy-Anzahl.

Fremd nicht sichtbar:

- Sticker-, Such- oder Doppeltlisten,
- Einzelmengen und Albumfortschrittsdetails,
- Album-Detaillinks,
- Trophy-Namen, Icons, Historie oder Freischaltzeitpunkte,
- Statistik-Interna,
- Konto-, Einstellungs- oder Bearbeitungsaktionen.

Profilbild und Standort wurden mangels bestehender Felder nicht dargestellt.
Es wurden keine Platzhalterdaten erfunden.

## Neue Dateien

- `App/services/collector_profiles.py`
- `tests/test_s26_collector_profiles.py`
- `Dokumentation/Product Bible/roadmap/s26-public-profile-v1.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S26-report.md`

## Geänderte Dateien

- `App/webapp.py`
  - gemeinsamer Profilrenderer,
  - bestehende eigene Profilroute auf das Readmodel umgestellt,
  - neue Fremdprofilroute per Username,
  - sicherer Partnerlink in der bestehenden Trade-Detailansicht.
- `App/static/style.css`
  - ausschließlich notwendige responsive S26-Profilhierarchie und dezenter
    Partnerlink.
- `Dokumentation/Product Bible/roadmap/README.md`
  - S26-Spezifikation und -Report verlinkt; S27 als nächster offener Sprint.

## Unveränderte Komponenten

- Inventory, Availability und Shared Snapshot,
- Trade Lifecycle sowie alle Trade-Schreibpfade,
- Coverage, TopMatch und Smart Requests,
- Notification-System und Operational Home,
- Statistik-, Trophy-, Profilbearbeitungs- und Account-Routen,
- Datenbankschema und Migration V0006,
- Freunde, Bewertungen, Blockieren und S27-Privacy.

## Testmatrix

Die 11 neuen S26-Tests prüfen:

- eigenes Profil weiterhin erreichbar und editierbar,
- fremdes Profil per Username strikt read-only,
- HTTP 404 für unbekannten Username,
- fehlenden optionalen Klarnamen,
- XSS-Escaping bestehender Identitätsdaten,
- aktive Alben und Vitrine aus zentralem Inventory-Fortschritt,
- exakt vier Kennzahlen und korrekte Doppelte,
- Trophy-Anzahl ohne fremde Trophy-Details,
- Lifecycle-completed und Legacy-completed ohne Doppelzählung,
- Ausschluss offener, angenommener, failed, declined/rejected, expired,
  obsolete und inkonsistenter Trades,
- verbindliche mobile Inhaltsreihenfolge,
- Trade-Partnerlink auf die Username-Route,
- immutable DTOs,
- Fremdprofil-GET ohne DB-Mutation,
- unveränderten Migrationsumfang bis V0006.

## Testbefehle und Ergebnisse

Der wörtlich vorgegebene Befehl

```bash
python3 -m unittest tests.test_s26_* -v
```

ist unter der verwendeten zsh kein ausführbarer Modulaufruf; die Shell beendet
ihn vor Python mit `no matches found: tests.test_s26_*`.

Der konkrete ausführbare Modulbefehl lautet:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_s26_collector_profiles -v
```

Ergebnis: **11 Tests, alle erfolgreich**.

Vollständiges Gate:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p "test_s*.py" -v
```

- finaler Lauf 1: **410 Tests, alle erfolgreich**,
- finaler Lauf 2: **410 Tests, alle erfolgreich**.

## Bekannte Grenzen

- S26 besitzt noch keine Album-Privacy; fremde Albumdarstellung bleibt deshalb
  auf Namen und Aggregate beschränkt.
- Es gibt keine manuelle Aktiv-/Inaktiv-Einstellung; diese wurde nicht
  vorgezogen.
- Profilbild und Standort besitzen weiterhin kein persistentes Feld.
- Trophy-Details, Bewertungen, Tauschpotenzial, Freunde, Blockieren,
  Aktivstatus, Suche und People Discovery sind nicht Teil von S26.
- Der optionale bestehende Klarname hat noch keine eigene S27-
  Sichtbarkeitseinstellung.

## Release Readiness

- S26-spezifisch: 11/11 grün,
- beide finalen Vollgates: jeweils 410/410 grün,
- lokale Entwicklungsdatenbank: V0006,
- neue Migration erforderlich oder erzeugt: nein,
- `PRAGMA integrity_check`: `ok`,
- `PRAGMA foreign_key_check`: keine Befunde,
- kanonische S00-Fixture SHA-256:
  `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`,
- lokale Entwicklungsdatenbank SHA-256 nach den finalen Tests:
  `c4f8d4b154c1d8f88575e1405aa52fadf4cb11d394d1ac612cf2d6407a94a08f`,
- alle S26-Tests ausschließlich auf temporären V0006-Kopien,
- lokale Datenbank und Fixture durch Test-Hashguards geschützt,
- lokaler Debug-Server vor Python-Änderungen gestoppt, damit kein Auto-Reload-
  Startup-Schreibpfad ausgelöst wird,
- `git diff --check`: ohne Befund vor dem finalen Gate.

## Offene Punkte für S27

- technische Album-Sichtbarkeit `public`, `friends`, `private`,
- Objektberechtigung für sichtbare fremde Albumdetails,
- künftige Sichtbarkeit des optionalen Klarnamens,
- Verhältnis von Profilsichtbarkeit und Smart-Trade-Pool.

Keiner dieser Punkte wurde begonnen.

## Scope-Bestätigung

- Ausschließlich S26 umgesetzt.
- S27 nicht begonnen.
- Keine Migration oder Datenbankschemaänderung.
- Keine Änderung an Inventory, Trade Lifecycle, Snapshot, Coverage, TopMatch,
  Smart Requests, Notification-System oder Operational Home.
- Keine Freunde, Bewertungen, Privacy, Suche oder Community-Funktionen.
- Kein Commit erstellt.
- Kein Push durchgeführt.
