# Sprint-Report S24 – Glocke, Badge und Notification-Historie

Stand: 2026-08-08

## Ergebnis

S24 ist vollständig umgesetzt und release-ready. Die globale Glocke zeigt die
Anzahl aller ungelesenen eigenen Notifications. Die Notificationseite ist eine
gemeinsame, neueste-zuerst sortierte Historie für gelesene, ungelesene,
typisierte und Legacy-Einträge. Ein bewusster Klick prüft das S23-Ziel erneut,
setzt genau diesen Eintrag auf gelesen und öffnet das kanonische Fachobjekt mit
dem sicheren Rückwegkontext `notifications`.

Es gibt keine Retention, Löschung, Massenmarkierung oder Migration. Lesen und
fachliches Erledigen bleiben getrennte Zustände.

## Ziel und verbindliche Semantik

- Historien-GET verändert keinen Read-State.
- Seitengröße: exakt 25 Einträge.
- Sortierung: `created_at DESC`, bei gleichem Zeitpunkt `id DESC`.
- Eine gemeinsame Pagination für alle Notification-Kategorien.
- Badge zählt alle eigenen ungelesenen Legacy- und Typed-Einträge.
- Badge `0`: unsichtbar; `1–99`: exakt; ab `100`: `99+`.
- Nur Zielklick oder explizite Einzelaktion setzt gelesen.
- Ein Zielklick prüft Existenz und Berechtigung vor dem Read-State-Wechsel.
- Nicht verfügbare Ziele bleiben sichtbar, sind nicht klickbar und können über
  die Einzelaktion gelesen werden.
- Legacy-Einträge werden nicht semantisch rekonstruiert.
- Alle Notifications bleiben unbegrenzt erhalten.

## Architektur

### NotificationHistoryService

Der neue isolierte Service besitzt ausschließlich S24-Verantwortung:

- nutzerbezogener ungelesener Gesamtzähler,
- gemeinsame paginierte Historie,
- immutable History-, Page- und Open-DTOs,
- idempotente Einzelmarkierung als gelesen,
- atomarer Read-and-Resolve-Vorgang für einen Zielklick.

Für typisierte Ziele ruft der Service ausschließlich
`TypedNotificationService.target_path_for(...)` auf. Es existiert keine zweite
Interpretation von `target_type` oder `target_id`.

### Neue DTOs und Ergebniscode

- `NotificationHistoryItemDTO`
- `NotificationHistoryPageDTO`
- `NotificationOpenResultDTO`
- `NotificationOpenCode`
  - `opened`
  - `target_unavailable`
  - `not_found`

Alle DTOs sind immutable.

## Datenfluss

### Historie und Badge

```text
Sessionnutzer
→ S23-lazy Fristprojektion am bestehenden Notification-Einstieg
→ COUNT aller eigenen Notifications
→ ORDER BY created_at DESC, id DESC
→ LIMIT 25 / OFFSET
→ S23-Zielauflösung je typisiertem Eintrag
→ Historienansicht ohne Read-State-Mutation
```

Der globale Header führt unabhängig von der aktuellen Seite ein
nutzerspezifisches `COUNT ... WHERE is_read=0` aus. Die Pagination beeinflusst
den Badgewert nicht.

### Zielklick

```text
eigene Notification-ID
→ Zeile unter kurzer Transaktion laden
→ kanonisches S23-Ziel samt Beteiligung prüfen
→ genau diese Notification is_read=1
→ Commit
→ interner Zielpfad mit origin=notifications
```

Wiederholtes Öffnen ist idempotent und verändert kein Fachobjekt.

### Nicht verfügbares Ziel

Ein unbekanntes, gelöschtes, inkonsistentes oder nicht mehr berechtigtes Ziel
erzeugt keinen Link und keine Zielauskunft. Titel und Text der Notification
bleiben sichtbar. Die vorhandene nutzerbezogene Einzelaktion kann nur den
Read-State dieser Notification ändern.

## Navigation

Die kleine S07-Allowlist wurde additiv um `notifications` erweitert:

```text
/notifications
→ /notifications/<id>/open
→ /trades/<request-id>?origin=notifications
→ zurück zu /notifications
```

Die bestehenden Kontexte `home`, `trades` und `album_trades`, unbekannte
Origins und der fachliche Standardfallback bleiben unverändert. Es wurde kein
allgemeiner Navigation-Stack und keine frei übergebene Return-URL eingeführt.

## Neue Dateien

- `App/services/notification_history.py`
- `tests/test_s24_notification_history_navigation.py`
- `Dokumentation/Product Bible/roadmap/s24-notification-history-navigation.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S24-report.md`

## Geänderte Dateien

- `App/webapp.py`
  - globales Badge eingebunden,
  - bestehende Notification-Shell zur gemeinsamen Historie erweitert,
  - sichere Open-Route und nutzerbezogene Read-State-Route angebunden,
  - Origin-Allowlist ausschließlich um `notifications` ergänzt.
- `App/static/style.css`
  - minimale mobile-taugliche Badge-, History- und Paginationdarstellung.
- `tests/test_s06_global_header_shell.py`
  - ausschließlich die durch S24 ersetzte Erwartung angepasst: Die
    Notificationseite enthält nun auch gelesene eigene Einträge und den neuen
    ehrlichen Leerzustand.
- `tests/test_s07_deep_link_origin_context.py`
  - explizite Allowlist-Erwartung additiv um `notifications` ergänzt.
- `Dokumentation/Product Bible/roadmap/README.md`
  - S24-Spezifikation und Bericht verlinkt; S25 nur als offen bezeichnet.

## Unveränderte Komponenten

- Migration V0006 Up und Down,
- S23-Notification-Typen, Eventprojektion und Deduplizierung,
- Inventory, Availability und Shared Snapshot,
- Coverage, TopMatch und Smart Requests,
- Reservation, Shipping, Receipt und Problems,
- Trade- und Lifecycle-Zustände,
- Home-Inhalte,
- alle bestehenden Origin-Regeln außer der ausdrücklich freigegebenen
  additiven Allowlist-Erweiterung.

## Testmatrix

| Bereich | Abdeckung |
| --- | --- |
| Leerzustand | keine Notifications, weiterhin HTTP 200 |
| Pagination | weniger als 25, genau 25, mehr als 25, zwei Seiten |
| Sortierung | neueste zuerst mit stabiler ID-Reihenfolge |
| Kategorien | Legacy, Typed, gelesen und ungelesen gemeinsam |
| Read-State | History-GET unverändert; Einzelaktion nutzerbezogen |
| Badge | 0, 1, 99, 100 → 99+; Legacy und Typed gemeinsam |
| Request-Ziel | gelesen und Redirect auf kanonische Request-ID |
| Lifecycle-Ziel | gelesen und Redirect über Lifecycle-Trade-Ziel |
| Rückweg | `origin=notifications` führt zur Historie |
| Regression Origins | Home, Trades und Album-Trades unverändert |
| Fehlendes Ziel | sichtbar, nicht klickbar, einzeln lesbar |
| Fremdes Ziel | keine Zieldetails, kein Read-State durch Open-Endpunkt |
| Retry | identischer Redirect, genau ein Read-State, kein Fachwrite |
| S23 | Dedupe-Key und idempotente Erzeugung unverändert |
| Persistenz | keine neue Migration; lokale DB und Fixture unverändert |

## Tests und Ergebnisse

Gezielter ausführbarer S24-Befehl:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_s24_notification_history_navigation -v
```

Ergebnis: **15 Tests, 15 erfolgreich**.

Der vorgegebene Ausdruck `python3 -m unittest tests.test_s24_* -v` ist kein
gültiger `unittest`-Modulname. Deshalb wurde der konkrete Modulname verwendet.

Gezieltes Kompatibilitätsgate über S03, S06, S07, S23 und S24:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_s03_side_effect_security_gate \
  tests.test_s06_global_header_shell \
  tests.test_s07_deep_link_origin_context \
  tests.test_s23_typed_notifications \
  tests.test_s24_notification_history_navigation -v
```

Ergebnis: **62 Tests, 62 erfolgreich**.

Vollständiges Gate:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p "test_s*.py" -v
```

- finaler Lauf 1: **385 Tests, 385 erfolgreich**,
- finaler Lauf 2: **385 Tests, 385 erfolgreich**.

Ein erster nicht-finaler Gate-Lauf fand einen historischen Importvertrag des
S03-Tests für `webapp.unread_notifications`. Der Re-Export wurde ohne Nutzung
im neuen S24-Historienpfad bewahrt. Das anschließende Kompatibilitätsgate und
beide finalen Vollgates waren vollständig grün.

## Release Readiness

- neue Migration für S24 erforderlich: **nein**,
- V0006 verändert: **nein**,
- lokale Datenbank migriert: **nein**,
- lokaler Migrationsstand read-only: **V0005**,
- `PRAGMA integrity_check`: **ok**,
- `PRAGMA foreign_key_check`: **keine Befunde**,
- Tests ausschließlich auf temporären Fixture-Kopien bis V0006,
- lokale Datenbank und kanonische S00-Fixture durch Hash-Guards unverändert,
- History-GET verändert keinen Read-State,
- Klick-Retry verändert keinen Tradezustand,
- fremde Ziele und Notification-IDs sind nutzerbezogen geschützt,
- Syntaxprüfung von Service, Webapp und S24-Test erfolgreich,
- `git diff --check`: **ohne Befund**,
- kein Commit,
- kein Push.

## Bekannte Grenzen

- Es gibt absichtlich keine Retention; die Historie wächst unbegrenzt, bis
  eine spätere Product-Owner-Policy freigegeben wird.
- Legacy-Einträge ohne echtes gespeichertes Ziel bleiben nicht klickbar.
- S24 besitzt nur Vorher-/Nachher-Pagination und keine Suche, Tabs oder Filter.
- Das Badge zählt Notifications und ausdrücklich keine offenen Fachaufgaben.
- Die Darstellung ist funktional und mobil bedienbar, aber kein finales
  Notification-Design.

## Offene Punkte für S25

- Operative Home-Aufgaben müssen Read-State und fachliches Erledigt weiterhin
  strikt unterscheiden.
- Home darf die Notification-Historie nicht duplizieren und muss über
  kanonische Fachziele verteilen.
- S24 hat keine Home-Inhalte, Aufgabenpriorisierung oder Feedlogik vorgezogen.

## Scope-Bestätigung

- ausschließlich S24 umgesetzt,
- S25 nicht begonnen,
- keine neue Migration und keine Änderung an V0006,
- keine neuen Notification-Typen,
- keine Änderung an S23-Deduplizierung,
- keine Änderung an Inventory, Snapshot, Coverage, TopMatch oder Smart
  Requests,
- keine Änderung an Reservierungs-, Versand-, Empfangs-, Problem- oder
  Tradefachlogik,
- keine Retention, Push-, E-Mail-, Einstellungs- oder Mute-Funktion,
- kein allgemeiner Design-Patch,
- kein Commit,
- kein Push.
