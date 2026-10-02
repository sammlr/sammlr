# S27 – Lokaler Migrations- und Smoke-Check

Stand: 2026-08-08

## Ergebnis

Die normale lokale Sammlr-Entwicklungsdatenbank wurde nach verifiziertem
Backup kontrolliert von V0006 auf V0007 migriert. Der Entwicklungsserver wurde
vollständig beendet und ohne `DATABASE_PATH`-Override neu gestartet. Der
anschließende S27-Smoke-Test mit Eigentümer- und Fremdkonto war erfolgreich.

Dies war ausschließlich die lokale Abnahmevorbereitung für S27. Es wurden
keine Features, Refactorings oder Arbeiten an S28 durchgeführt.

## Datenbank und Backup

Verwendete lokale Entwicklungsdatenbank:

```text
/Users/valy/Desktop/sammlr./App/Database/sammlr.db
```

Datierte Sicherung vor der Migration:

```text
/Users/valy/Desktop/sammlr./Backups/sammlr_local_pre_v0007_20260808_023853.db
```

Die Sicherung wurde vor der Migration mit `cp -p` erstellt. Original und
Backup hatten zu diesem Zeitpunkt denselben SHA-256. Zusätzlich ergab
`PRAGMA integrity_check` auf dem Backup `ok`; sein Migrationsstand ist V0006.

## Migration V0006 → V0007

Ausgeführter Befehl:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m App.Database.migration_runner up --database /Users/valy/Desktop/sammlr./App/Database/sammlr.db --target 7
```

Ergebnis:

```text
Applied change set: (7,); current version: 7
```

Es wurde ausschließlich die normale lokale Entwicklungsdatenbank migriert.
Die S00-Fixture, das Backup und andere Datenbankkopien wurden nicht migriert.
Es wurde keine neue Migration erzeugt.

## SHA-256

Vor der Migration, gleichzeitig SHA-256 des Backups:

```text
752292434f44c637f7518c71494d5b7f787d786d881bca06024b8547c732eac8
```

Nach Migration und erfolgreichem Smoke-Test:

```text
6a8b416806824ce1078379f7e2658d7939e040722c8b96a77c23e32cc67b0e6c
```

Unveränderte kanonische S00-Fixture:

```text
21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971
```

## Server-Neustart

Die beiden zuvor auf Port 8080 laufenden Flask-ReLoader-Prozesse wurden
vollständig beendet. Anschließend wurde aus dem Projektverzeichnis ohne
`DATABASE_PATH`-Override neu gestartet:

```text
env -u DATABASE_PATH PYTHONDONTWRITEBYTECODE=1 python3 App/webapp.py
```

Damit verwendet der Server den Standardpfad
`/Users/valy/Desktop/sammlr./App/Database/sammlr.db`. Der neue Server lauscht
auf Port 8080; `GET http://127.0.0.1:8080/login` lieferte HTTP 200.

## S27-Smoke-Test

Der Test verwendete zwei vorhandene lokale Accounts. Es wurden ausschließlich
die S27-Felder der Eigentümerzuordnung für das Album `vfl` geändert. Nach dem
Test wurde der sichere Ausgangszustand `private` und `trade_pool_enabled=1`
wiederhergestellt und durch erneuten Read bestätigt.

### Eigentümer

- Albumseite: HTTP 200.
- `Privat` gespeichert und nach Reload erhalten.
- `Freunde` gespeichert und nach Reload erhalten.
- `Öffentlich` gespeichert und nach Reload erhalten.
- Tradepool eingeschaltet, gespeichert und nach Reload erhalten.
- Tradepool ausgeschaltet, gespeichert und nach Reload erhalten.
- Abschließend `Privat + Tradepool ein` wiederhergestellt.

### Fremdkonto und Privacy

| Sichtbarkeit | Fremdalbum |
| --- | --- |
| private | HTTP 404 |
| friends | HTTP 404 |
| public | HTTP 200 |

In der öffentlichen Ansicht wurden geprüft:

- Albumname und Fortschrittsdarstellung,
- vollständige Stickerwall,
- konkrete Stickermenge aus der lokalen Datenbank,
- konkrete Zahl der Doppelten,
- read-only Stickerdetail.

### Fremdprofil

Die albumbezogenen Kennzahlen reagierten auf die Sichtbarkeit:

- sichtbare Alben: `0 → 1`,
- sichtbare Doppelte: `0 → 10172` entsprechend dem vorhandenen lokalen
  Albumdatenbestand.

Die albumunabhängigen Kennzahlen blieben identisch:

- erfolgreiche Trades: `10`,
- Trophy-Anzahl: `41`.

Der auffällig hohe vorhandene lokale Duplikatwert wurde ausschließlich gelesen
und weder korrigiert noch fachlich neu bewertet.

### Tradepool

Mit `Privacy=private` und `Tradepool=ein` blieb das Album trotz verborgener
Wall fachlich verwendbar:

- persönliche Coverage: 6 effektiv verfügbare Codes,
- TopMatch: 1 Partnerpaket,
- Smart-Request-Recheck: Paket vollständig verfügbar.

Mit `Tradepool=aus` galt für neue Matches:

- persönliche Coverage: 0 effektiv verfügbare Codes,
- TopMatch: 0 Partnerpakete,
- Smart-Request-Recheck: nicht ausführbar.

Die vor dem Smoke-Test gespeicherte Projektion aller bestehenden
`trade_requests` einschließlich Status und Bestätigungen war nach dem Test
unverändert.

## Integrität

Nach Migration, Smoke-Test und Wiederherstellung der S27-Ausgangseinstellung:

```text
PRAGMA integrity_check;
ok
```

```text
PRAGMA foreign_key_check;
keine Befunde
```

Der abschließend gelesene Migrationsstand ist V0007. Die abschließend gelesene
Eigentümereinstellung für `vfl` ist `private|1`.

## Bestätigung

- Backup vor jeder Änderung erstellt und geprüft.
- Lokale Entwicklungsdatenbank ausschließlich V0006 → V0007 migriert.
- Server vollständig neu gestartet und normale lokale Datenbank verwendet.
- S27-Privacy, Tradepool, Fremdprofil und bestehende Trades geprüft.
- Keine neue Migration, keine neue Produktfunktion und kein Refactoring.
- S28 wurde nicht begonnen.
- Kein Commit erstellt.
- Kein Push durchgeführt.
