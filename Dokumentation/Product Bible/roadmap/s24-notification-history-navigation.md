# S24 – Notification-Historie, Badge und sichere Navigation

Stand: 2026-08-08

## Ziel

Die globale Glocke wird zur nutzbaren Benachrichtigungszentrale. Alle
Notifications eines Nutzers bleiben gemeinsam historisch sichtbar. Ungelesene
Einträge werden global gezählt, bewusstes Öffnen setzt genau den gewählten
Eintrag auf gelesen und typisierte Notifications führen ausschließlich nach
erneuter Berechtigungsprüfung zu ihrem kanonischen S23-Ziel.

S24 verändert weder Notification-Typen noch Deduplizierung, Tradefachlogik
oder V0006.

## Verbindliche Invarianten

- Historien-GET markiert keine Notification als gelesen.
- Badge und Historie sind strikt nutzerbezogen.
- Das Badge zählt typisierte und Legacy-Notifications unabhängig von der
  aktuellen Historienseite.
- `0` erzeugt kein Badge, `1` bis `99` die exakte Zahl, ab `100` wird `99+`
  dargestellt.
- Historie enthält gelesene, ungelesene, typisierte und Legacy-Einträge in
  einer gemeinsamen, neuesten-zuerst sortierten Pagination.
- Seitengröße ist verbindlich `25`.
- Es findet keine Löschung, Retention oder Archivmigration statt.
- Nur bewusstes Öffnen eines gültigen Ziels oder eine explizite Einzelaktion
  setzt genau eine eigene Notification auf gelesen.
- Ein Ziel wird vor dem Read-State-Wechsel neu auf Existenz und Berechtigung
  geprüft.
- Unbekannte, gelöschte, inkonsistente oder unberechtigte Ziele bleiben ohne
  Zieldetails und ohne aktiven Deep Link sichtbar.
- Legacy-Notifications erhalten kein künstliches Ziel.
- Lesen bedeutet nicht, dass eine fachliche Aufgabe erledigt ist.
- S23-Deduplizierung und lazy Fristprojektion bleiben unverändert.

## Architektur

### `NotificationHistoryService`

Ein kleiner S24-Service übernimmt ausschließlich die nutzerbezogene
Historien- und Read-State-Funktion:

1. Gesamtzahl und paginierte Liste lesen,
2. ungelesene Anzahl unabhängig von Pagination zählen,
3. einen eigenen Eintrag idempotent als gelesen markieren,
4. für typisierte Einträge die bestehende S23-Zielauflösung verwenden,
5. einen Zielklick als atomaren, autorisierten Read-and-Resolve-Vorgang
   ausführen.

Der Service erzeugt keine Notification und ändert kein Fachobjekt.

### Wiederverwendung der S23-Architektur

`TypedNotificationService` und seine DTO-/Zielprüfung bleiben Eigentümer der
kanonischen Zielauflösung. S24 legt keine zweite Interpretation von
`target_type` oder `target_id` an. Die neue Historienprojektion dekoriert eine
Notification lediglich mit einem optionalen, bereits autorisierten internen
Pfad.

### Routen und Darstellung

- `GET /notifications?page=N` rendert genau eine gemeinsame Historienseite.
- Ein eigener, nutzerbezogener Open-Endpunkt prüft das Ziel, setzt genau den
  gewählten Eintrag auf gelesen und leitet intern weiter.
- Die bestehende explizite Einzelaktion zum Lesen bleibt nutzerbezogen und
  wird für nicht klickbare Einträge weiterverwendet.
- Der globale Header liest nur den ungelesenen Gesamtzähler und zeigt die
  definierte Badge-Darstellung.

Keine Route akzeptiert eine frei übergebene Ziel-URL.

## Navigation und Rückweg

S24 erweitert ausschließlich die kleine S07-Origin-Allowlist um
`notifications`.

```text
Notification-Historie
→ autorisierter Open-Endpunkt
→ kanonisches Trade-/Request-Ziel mit origin=notifications
→ fachlicher Zurückweg /notifications
```

Alle bestehenden Origin-Kontexte und Fallbacks bleiben unverändert. S24 führt
keinen allgemeinen Navigation-Stack und keine freie Return-URL ein.

## DTOs

Vorgesehen sind immutable Rückgabeobjekte:

- `NotificationHistoryItemDTO`
  - Notification-Identität und eigener Read-State,
  - Titel, Text, Zeitpunkt und S23-Typ,
  - optionaler autorisierter Zielpfad,
  - Kennzeichen `target_available`.
- `NotificationHistoryPageDTO`
  - Items,
  - aktuelle Seite,
  - Seitengröße `25`,
  - Gesamtzahl und Seitenzahl,
  - Vorher-/Nachher-Verfügbarkeit.
- `NotificationOpenResultDTO`
  - stabiler Ergebniscode,
  - optionaler interner Zielpfad,
  - Kennzeichen, ob der Read-State geändert wurde.

## Datenfluss

### Historie

```text
authentifizierter Nutzer
→ bestehende S23-lazy Fristprojektion am Notification-Einstieg
→ COUNT aller eigenen Notifications
→ eigene Notifications ORDER BY created_at DESC, id DESC
→ LIMIT 25 / OFFSET
→ S23-Zielprüfung je typisiertem Eintrag
→ read-only HTML
```

Das Anzeigen selbst verändert keinen Read-State.

### Badge

```text
globaler Header
→ COUNT eigene notifications WHERE is_read=0
→ 0: unsichtbar | 1–99: exakt | >=100: 99+
```

Die Pagination beeinflusst diese Abfrage nicht.

### Gültiger Klick

```text
Notification-ID + Sessionnutzer
→ eigene Zeile laden
→ S23-Ziel neu autorisieren
→ nur bei gültigem Ziel is_read=1
→ Commit
→ kanonischer interner Zielpfad + origin=notifications
```

Ein Retry ist idempotent. Er verändert weder Zielobjekt noch fachliche
Aufgabe.

### Nicht verfügbares Ziel

```text
Zielprüfung fehlgeschlagen
→ kein Deep Link und keine Zieldetails
→ Eintrag bleibt sichtbar
→ optionale explizite Einzelaktion setzt nur is_read
```

## Read-/Write-Pfade und Seiteneffekte

Read-only:

- History-Abfrage und Pagination,
- Badge-Zähler,
- Zielverfügbarkeit und Berechtigungsprüfung.

Erlaubter S24-Write:

- ausschließlich `notifications.is_read` für genau eine Notification des
  aktuellen Nutzers.

Bereits vorhandener S23-Seiteneffekt am Notification-Einstieg:

- idempotente lazy Erzeugung freigegebener Fristnotifications.

Nicht erlaubt:

- Änderung an Trade, Request, Inventory oder Lifecycle,
- neue Notification-Typen oder Änderungen an Deduplizierung,
- Löschung, Retention, Massenmarkierung oder neue Persistenzfelder.

## Betroffene Komponenten

- neuer, isolierter Notification-History-Service,
- bestehende Notificationseite,
- globaler Header/Glocke,
- bestehende einzelne Read-State-Route,
- kleine S07-Origin-Allowlist und fachlicher Deal-Rückweg,
- S24-spezifische Tests und Dokumentation.

## Unveränderte Komponenten

- V0006 Up-/Down-Migration,
- S23-Notification-Typen, Erzeugung und Deduplizierung,
- Inventory, Availability und Shared Snapshot,
- Coverage, TopMatch und Smart Requests,
- Reservation, Shipping, Receipt und Problems,
- Tradezustände und Lifecycle-Regeln,
- Home-Inhalte,
- bestehende Origin-Kontexte außer der additiven Allowlist-Erweiterung,
- CSS außerhalb minimal notwendiger Badge-/Historien-Darstellung.

## Fehler- und Sicherheitsregeln

- fremde Notification-ID: keine Offenlegung und kein Read-State-Wechsel,
- fremdes oder nicht mehr berechtigtes Ziel: keine Zieldetails, keine
  Weiterleitung,
- Legacy-/zielloser Eintrag: sichtbar, nicht klickbar, einzeln lesbar,
- unbekannte Seite: deterministischer, sicherer Seitenzustand ohne Zugriff auf
  fremde Daten,
- Zielpfad stammt ausschließlich aus der S23-Allowlist, niemals aus Request-
  Parametern,
- wiederholter Klick ist idempotent.

## Testvertrag

Abgedeckt werden leere, kleine, exakt 25 und mehrseitige Historien; gemeinsame
Legacy-/Typed-Sortierung; unveränderter History-GET; gültige Request- und
Lifecycle-Ziele; `origin=notifications`; Rückweg; unveränderte andere Origins;
Badge `0`, `1`, `99`, `99+`; Legacy im Badge; unbekannte und fremde Ziele;
explizites Lesen zielloser Einträge; Klick-Retry; unveränderte S23-
Deduplizierung und vollständige S01–S24-Regression.

## Nicht enthalten

- S25 oder operative Home-Aufgaben,
- neue Notification-Typen und Problemnotifications,
- Retention oder Löschung,
- Push, E-Mail, Einstellungen, Mute oder Gruppennotifications,
- allgemeiner Navigation-Stack,
- finales Design oder allgemeiner Design-Patch.
