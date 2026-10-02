# S25 – Lokaler Migrations- und Smoke-Check

Stand: 2026-08-08

## Ergebnis

Die normale lokale Sammlr-Entwicklungsdatenbank wurde nach einer verifizierten
Sicherung mit dem bestehenden Migration Runner kontrolliert von V0005 auf
V0006 migriert. Der lokale Server läuft anschließend wieder gegen genau diese
Datenbank. Alle geforderten read-only Smoke- und Integritätsprüfungen waren
erfolgreich.

Es wurde kein neuer Sprint begonnen.

## Datenbank und Backup

- Verwendete lokale Entwicklungsdatenbank:
  `/Users/valy/Desktop/sammlr./App/Database/sammlr.db`
- Datierte Sicherung vor jeder Änderung:
  `/Users/valy/Desktop/sammlr./Backups/sammlr_local_pre_v0006_20260808_010509.db`
- Verifizierter Migrationsstand der Sicherung: V0005
- Integrität der Sicherung: `ok`
- SHA-256 der Sicherung:
  `159cc562b648ebf567878622b4db815cc2acf86601b9d2bc2a586793b8cd5912`

## Migration

- Alter Stand: V0005
- Neuer Stand: V0006
- Ausgeführter Befehl:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 App/Database/migration_runner.py up \
  --database /Users/valy/Desktop/sammlr./App/Database/sammlr.db \
  --target 6
```

- Runner-Ergebnis:
  `Applied change set: (6,); current version: 6`
- Es wurde ausschließlich die lokale Entwicklungsdatenbank migriert.
- Es wurde keine neue Migration erzeugt.
- Fixture-, Test- und Backup-Datenbanken wurden nicht migriert.

## Prüfsummen

- SHA-256 vor Migration:
  `f2ece9fd5b10cb2d1d52834325aeb2d781eaf1615396361a9bf01035ea17e0b3`
- SHA-256 unmittelbar nach Migration:
  `1cff8ca22afa84e808a294dd2f006a21bf2c80a14dd650ff8dbd2154885075f7`
- SHA-256 nach vollständigem Serverneustart und Smoke-Test:
  `61a5d43ea5ab6b8858f9dfa7e8fdc59b67336df2dcd73aac47934995efb9ecaf`

Die zusätzliche physische Prüfsummenänderung beim Neustart stammt aus dem
bereits vorhandenen idempotenten `init_db()`-Startup-Pfad. Der nachfolgende
Smoke-Test selbst veränderte die finale Prüfsumme nicht.

## Server

Der zuvor laufende lokale Server wurde vollständig beendet und anschließend
ohne `DATABASE_PATH`-Override aus dem Projektverzeichnis neu gestartet:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 App/webapp.py
```

Damit verwendet die App wieder den normalen lokalen Standardpfad
`/Users/valy/Desktop/sammlr./App/Database/sammlr.db`. Der Server ist unter
`http://127.0.0.1:8080` erreichbar.

## Read-only Smoke-Test

| Prüfung | Ergebnis |
| --- | --- |
| Login | HTTP 302 auf Home, erfolgreich |
| Home | HTTP 200; „Das braucht dich“ und „Alles erledigt.“ sichtbar |
| Sammlung | HTTP 200; Sammlr-Zentrale und aktive Alben sichtbar |
| Tradebörse | HTTP 200; Tauschbörse sichtbar |
| Notification-Historie | HTTP 200; leerer Zustand für den passiven Prüfnutzer sichtbar |
| Glocken-Badge | HTTP 200; vorhandener Wert `18` für einen Nutzer mit ungelesenen Notifications sichtbar |
| Trade öffnen | HTTP 200; bestehender abgeschlossener Trade mit Partner und Timeline lesbar |

Für Home, Tradebörse, Notification-Historie und Tradeansicht wurde ein
vorhandener Nutzer ohne laufenden Lifecycle-Trade verwendet. Dadurch konnte
keine lazy Fristnotification entstehen. Für den Badge wurde ausschließlich
eine read-only Sammlungsseite eines Nutzers mit bereits vorhandenen ungelesenen
Notifications geladen.

Vor und nach dem Smoke-Test waren identisch:

- Datenbank-SHA-256:
  `61a5d43ea5ab6b8858f9dfa7e8fdc59b67336df2dcd73aac47934995efb9ecaf`
- Notifications: `58`
- Trade Events: `23`
- Inventory-Summen `quantity|duplicates`: `12308|10381`

Der Smoke-Test hat keine Produktdaten verändert und keine Notification als
gelesen markiert.

## Integritätsprüfungen

- `PRAGMA integrity_check`: `ok`
- `PRAGMA foreign_key_check`: keine Befunde
- finaler Migrationsstand: V0006

## Scope-Bestätigung

- Keine fachlichen Änderungen vorgenommen.
- Keine neuen Features implementiert.
- Keine Anwendungscode- oder Teständerungen vorgenommen.
- S26 wurde nicht begonnen.
- Kein Commit erstellt.
- Kein Push durchgeführt.
