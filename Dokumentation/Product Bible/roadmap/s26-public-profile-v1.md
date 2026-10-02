# S26 – Eigenes und fremdes Profilfundament

Stand: 2026-08-08

## Ziel

Das Profil wird als mobile Sammlerseite aufgebaut. Das eigene Profil bewahrt
alle vorhandenen Bearbeitungs- und Unterseitenzugänge. Ein fremdes Profil ist
unter `/profil/<username>` als konservative, strikt read-only Projektion
erreichbar.

S26 schafft weder Community-Funktionen noch Privacy-Konfiguration. Die
Sichtgrenzen sind bis S27 bewusst eng.

## Verbindliche Invarianten

- Der Username ist die kanonische öffentliche Route und primäre Identität.
- Interne Nutzer-IDs erscheinen nicht in der öffentlichen Profilroute.
- Ein unbekannter Username liefert HTTP 404.
- Das Öffnen eines fremden Profils erzeugt keine Mutation.
- Fremde sehen keine Stickerlisten, Such- oder Doppeltlisten, Einzelmengen,
  Trophy-Details, Unlock-Zeitpunkte, Einstellungen oder Statistik-Interna.
- Es entstehen keine neue Spalte, Migration, Privacy-Stufe oder erfundene
  optionale Profildaten.
- Fehlender Klarname funktioniert; Profilbild und Standort werden mangels
  bestehender Felder nicht dargestellt.
- Albumfortschritt, Doppelte, Tradeabschluss und Trophy-Freischaltung werden
  nicht neu berechnet oder dupliziert.
- Ein fachlicher Trade zählt höchstens einmal.
- Das eigene Profil bleibt editierbar und behält Statistik, Trophäen,
  Trade-Archiv und Kontoeinstellungen.

## Architektur

### `CollectorProfileService`

Ein neuer isolierter Read-Service erhält eine bestehende SQLite-Verbindung und
erzeugt das vollständige Profil-Readmodel. Er besitzt keine Commit-, Insert-,
Update- oder Delete-Operation.

Er verwendet:

- `users` für Username und optional vorhandenen Klarnamen,
- `user_albums` und `albums` für Zuordnung und Namen,
- den bestehenden `InventoryReadService` für Fortschritt und Doppelte,
- `trade_requests` mit optionaler Lifecycle-Zuordnung für erfolgreiche Trades,
- `unlocked_trophies` als bestehende persistierte Trophy-Wahrheit.

### Immutable DTOs

`CollectorAlbumDTO`:

- Album-ID intern,
- Albumname,
- gesammelt,
- Gesamtzahl,
- Prozent,
- `completed`.

`CollectorProfileDTO`:

- interne Nutzer-ID,
- Username,
- optionaler Klarname,
- zugeordnete Alben,
- aktive Alben,
- Vitrinenalben,
- Gesamtzahl Doppelte,
- erfolgreiche Trades,
- freigeschaltete Trophäen.

Alle Listen werden als deterministisch sortierte Tupel ausgegeben. Beide DTOs
sind eingefrorene Dataclasses.

## Datenfluss

```text
GET /profil
→ Sessionnutzer intern per ID auflösen
→ CollectorProfileService lesen
→ eigene Profilansicht mit vorhandenen Bearbeitungslinks

GET /profil/<username>
→ Nutzer exakt über eindeutigen Username auflösen
→ unbekannt: HTTP 404
→ eigener Username: gemeinsames Readmodel in eigener Sicht
→ fremder Username: konservative read-only Sicht
```

Profilaufbau:

```text
Nutzer
→ zugeordnete Alben
→ zentraler Inventory-Read pro Album
→ unvollständig = aktiv / vollständig = Vitrine
→ kompakte aggregierte Kennzahlen
→ persistierte Trophy-Anzahl
→ HTML mit kontextabhängigen Sichtgrenzen
```

## Kennzahlenvertrag

Exakt vier Kennzahlen werden angezeigt:

1. Anzahl zugeordneter Alben,
2. Gesamtzahl Doppelte,
3. Anzahl erfolgreicher Trades,
4. Anzahl freigeschalteter Trophäen.

Die Doppeltenzahl summiert die `duplicates`-Projektion des zentralen
Inventory-Snapshots über die zugeordneten Albumkataloge. Reservierungen werden
nicht als Verlust physischer Doppelter umgedeutet.

Ein Trade zählt erfolgreich, wenn die Legacy-Anfrage `completed` ist und:

- keine Lifecycle-Zeile existiert (weiterhin lesbarer Legacy-Trade), oder
- die genau zugeordnete Lifecycle-Zeile ebenfalls `completed` ist.

Die Zählung erfolgt je eindeutiger Legacy-Request-ID. Dadurch wird derselbe
Lifecycle-/Legacy-Trade nie doppelt gezählt. Offene, abgelehnte, fehlgeschlagene,
abgelaufene oder obsolete Requests zählen nicht.

## Aktive Alben und Vitrine

- aktiv: zugeordnet und `collected < total`,
- Vitrine: zugeordnet und `collected >= total`.

Fortschritt wird ausschließlich mit `InventoryReadService.album(...).progress`
und dem bestehenden Albumkatalog bestimmt. Es entsteht keine Aktiv-
Einstellung. Fremde sehen ausschließlich die Albumnamen; das eigene Profil
darf zu den bereits bestehenden eigenen Albumseiten verlinken.

## Sichtgrenzen

### Eigenes Profil

- Identität mit optional vorhandenem Klarnamen,
- vier Kennzahlen,
- aktive Alben,
- Vitrine,
- Trophy-Anzahl,
- bestehende Links zu Sammlung, Statistik, Trophäen, Trade-Archiv und Konto,
- bestehende Bearbeitungs- und Löschdialoge unverändert verfügbar.

### Fremdes Profil

- Username und optional bereits vorhandener Klarname,
- vier aggregierte Kennzahlen,
- Namen aktiver Alben,
- Namen der Vitrinenalben,
- Trophy-Anzahl.

Nicht gerendert werden fremde Albumlinks, Fortschrittsdetails,
Bestandsinformationen, Trophy-Details, Statistik-, Konto- oder
Bearbeitungszugänge.

## Trade-Integration

Ein bereits sichtbarer konkreter Partnername in der Trade-Detailansicht wird
auf `/profil/<escaped-username>` verlinkt. Die Tradeberechtigung bleibt
unverändert Voraussetzung für die Detailseite. Es entstehen keine Nutzersuche,
Discovery, Vorschlagsliste, Freundschaft oder Community-Navigation.

## Read-/Write-Pfade und Seiteneffekte

Read-only:

- Identität,
- Albumzuordnung und Album-Metadaten,
- Inventory-/Fortschrittsprojektion,
- erfolgreiche Tradeprojektion,
- persistierte Trophy-Anzahl.

Nicht vorhanden:

- Profilmutation im neuen Service,
- Fremdprofil-POST,
- Inventory- oder Tradewrite,
- Trophy-Berechnung oder -Freischaltung,
- Notification,
- Migration.

Das eigene Profil verwendet seine bereits vorhandenen separaten
Bearbeitungsrouten unverändert weiter.

## Mobile Hierarchie

1. Identität,
2. kompakte Kennzahlen,
3. aktive Alben,
4. Vitrine,
5. Trophy-Anzahl,
6. nur beim Eigentümer: vorhandene Unterseiten und Kontoeinstellungen.

Es wird lediglich die für diese Hierarchie notwendige responsive Darstellung
ergänzt; kein allgemeiner Design-Patch.

## Betroffene Komponenten

- neuer Profil-Read-Service,
- eigene Profilroute `/profil`,
- neue Fremdprofilroute `/profil/<username>`,
- bestehende Trade-Detaildarstellung für den Partnerlink,
- minimale profilbezogene CSS-Regeln,
- S26-Tests und Dokumentation.

## Unveränderte Komponenten

- Inventory- und Availability-Services,
- Trade Lifecycle und alle Trade-Schreibpfade,
- Snapshot, Coverage und TopMatch,
- Smart Requests,
- Notifications und Operational Home,
- Statistik-, Trophy-, Profilbearbeitungs- und Account-Routen,
- Datenbankschema und Migration V0006,
- S27-Privacy, Freunde, Bewertungen und Blockieren.

## Testvertrag

Getestet werden:

- eigenes Profil erreichbar und bestehende Bearbeitung weiterhin vorhanden,
- fremdes Profil per Username und strikt read-only,
- unbekannter Username mit HTTP 404,
- optional fehlender Klarname,
- aktive Alben und Vitrine aus zentralem Fortschritt,
- keine fremden Sticker-, Trophy- oder Einstellungsdetails,
- exakt vier Kennzahlen,
- Lifecycle- und Legacy-completed einschließlich Deduplizierung,
- Ausschluss aller nicht erfolgreichen Status,
- persistierte Trophy-Anzahl,
- sicher escaped Identität,
- korrekter Trade-Partnerlink,
- Fremdprofil-GET ohne Datenbankmutation,
- unveränderter Migrationsumfang und vollständige Regression.

## Risiken und Begrenzungen

- S27 führt erst die technische Album-Sichtbarkeit ein; S26 zeigt fremd daher
  nur Namen und Aggregate.
- Der vorhandene Klarname besitzt noch keine eigene Sichtbarkeitseinstellung;
  S26 behandelt ihn entsprechend Product Bible und Roadmap als optionale
  bestehende Identität, erfindet aber kein neues Feld.
- Persistierte Trophy-Historie kann von rein dynamisch erreichbaren, noch nie
  gespeicherten Schwellen abweichen. S26 zeigt absichtlich nur die bestehende
  Freischaltungswahrheit.
- Mehrfachalbum und manuelle Aktivierung existieren nicht und werden nicht
  vorgezogen.
- Profilbild, Standort, Bewertungen, Tauschpotenzial, Freunde, Blockieren und
  Aktivststatus sind nicht Teil von S26.
