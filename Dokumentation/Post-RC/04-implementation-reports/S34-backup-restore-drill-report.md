# S34 – realer Betreiber-Backup-/Restore-Drill

**Datum:** 21. August 2026

**Operatorfenster:** 19:09:26–19:14:10 UTC (4 Minuten 44 Sekunden)

**Ergebnis:** GRÜN

**S34 erfüllt:** JA

**Migration der echten Bestands-DB:** NEIN

## 1. Umfang und Betreiberumgebung

Der verpflichtende S34-Drill wurde lokal im tatsächlichen Betreiber-Working-
Tree auf macOS mit dem Projektinterpreter `.venv/bin/python`, den vorhandenen
Operator-Skripten und der aktuellen Bestands-DB ausgeführt. Es wurden keine
Produkt-, Schema- oder Konfigurationsänderungen implementiert.

Die aktive Bestands-DB war ausschließlich read-only Quelle. Backup, beide
Restores und das V7→V18-Upgrade lagen getrennt unter:

`/private/tmp/sammlr-s34-operator-drill-20260821T190800Z`

S34 definiert für den späteren Linux-PaaS-Betrieb `/var/data/sammlr.db` und
`/var/data/backups/`. Der vorliegende Drill musste gemäß Aufgabenfreigabe die
tatsächliche lokale Bestands-DB unter `App/Database/sammlr.db` prüfen und
verwendete deshalb ein privates, repositoryfernes macOS-Isolationsverzeichnis
als Betreiberpfad. Methode, Namensschema und Rechte entsprechen dem S34-
Vertrag; weder der Produktionspfad noch ein produktiver Restore wurden
simuliert oder überschrieben.

Der Drill verwendete keine Passwörter oder realen Anmeldedaten. Es wurden
keine Secrets protokolliert und keine Datenbankdateien in Git aufgenommen.

## 2. Ausgangsnachweis der Bestands-DB

Quelle:
`/Users/valy/Desktop/sammlr./App/Database/sammlr.db`

- Schema: V7;
- SHA-256 vor dem Drill:
  `3eb9da3b6d4898533030221bc80e8ed6406a25458eb8e1bca1f0e473a515b056`;
- `integrity_check = ok`;
- `foreign_key_check`: 0 Befunde;
- zentrale Counts: 4 Nutzer, 8 Nutzeralben, 1.971 Stickerzeilen,
  18 Trade-Requests, 89 Notifications und 61 Legacy-Trophy-Unlocks;
- Inventarmengen: 12.372 Exemplare, davon 10.401 Duplikate.

## 3. Backup

Das Backup wurde entsprechend S34 mit `Scripts/backup_sqlite.py` und damit
über die SQLite Backup API erzeugt. Es war kein Dateisystem-Copy der laufenden
DB. Der S34-Online-Backup-Vertrag verlangt dafür weder einen naiven Offline-
Copy noch einen manuellen Dateilock. Verwendeter Pfad:

`/private/tmp/sammlr-s34-operator-drill-20260821T190800Z/backups/sammlr-20260821-191030-v0007.db`

- Größe: 249.856 Bytes;
- SHA-256:
  `ac58159ce9b90cbd384430d3e6771954531562f383e12b213c10b18609ea34d5`;
- Schemaerkennung: V7;
- `integrity_check = ok`;
- `foreign_key_check`: 0 Befunde;
- Backupverzeichnis: Modus `0700`;
- Backupdatei: Modus `0600`;
- Retentionlauf: 0 abgelaufene Backups entfernt.

Der Backup-Hash ist nicht der Hash der aktiven SQLite-Datei. Das ist im
S34-Vertrag zulässig und bei der SQLite Backup API erwartbar: Sie erzeugt eine
neue, transaktionskonsistente SQLite-Datei. Schema, Integrity/FK, zentrale
Counts und Inventarsummen stimmen vollständig mit der Quelle überein.

## 4. Erster isolierter Restore auf V7

Restore über `Scripts/restore_sqlite.py`, intern ebenfalls mit der SQLite
Backup API, in die vorher nicht vorhandene Zieldatei:

`/private/tmp/sammlr-s34-operator-drill-20260821T190800Z/restore-v7/restore-v7.db`

- Restore-Dauer: 0,03 Sekunden;
- Dateimodus: `0600`, Elternverzeichnis `0700`;
- SHA-256 vor dem Upgrade:
  `ac58159ce9b90cbd384430d3e6771954531562f383e12b213c10b18609ea34d5`;
- damit bytegleich zum erzeugten Backup;
- Schema: V7;
- `integrity_check = ok`;
- `foreign_key_check`: 0 Befunde;
- zentrale Counts und Inventarsummen unverändert.

Ein echter Gunicorn-Prozess startete gegen genau diese Restore-Datei.
Ergebnisse:

| Pfad | HTTP | Bewertung |
|---|---:|---|
| `/healthz` | 503 | erwartetes Fail-closed, da aktuelle Runtime V18 verlangt |
| `/login` | 200 | grün |
| `/static/style.css` | 200 | grün |
| `/`, `/sammlung`, `/trades`, `/notifications`, `/profil` | 302 | erwarteter Redirect zu `/login` |

Der V7-Prozess ist damit start- und restorefähig. Der 503-Healthstatus ist kein
Startfehler, sondern verhindert vertragsgemäß, dass eine noch nicht auf V18
aktualisierte Restore-Datei als produktionsbereit markiert wird.

## 5. Upgrade-Drill V7→V18

Ausschließlich die erste Restore-Datei wurde mit dem kanonischen
Migration-Runner auf V18 aktualisiert.

- angewandte Changesets: V8 bis V18, exakt einmal;
- Upgrade-Dauer: 0,04 Sekunden;
- Zielschema: V18;
- `integrity_check = ok`;
- `foreign_key_check`: 0 Befunde;
- SHA-256 der aktualisierten Kopie:
  `1e85afcfcbeb2487b10ac38e39147d1438f0bf153d2df133a0c1373c9697b8f6`;
- Dateimodus blieb `0600`.

Die geschützten Bestandszählungen blieben exakt erhalten. Zusätzlich wurden
alle vorhandenen Lifecycle-Daten vor/nach dem Upgrade abgeglichen: 3 Alben,
10 Trades, 62 Trade-Positionen, 49 Trade-Events, 62 Reservierungen, je 10
Shipping- und Receipt-Statuszeilen, 5 Problemberichte und 17
Problemberichtpositionen.

Es gab keinen unzulässigen Backfill:

- `historical_album_records`: 0;
- `historical_sticker_acquisitions`: 0;
- `historical_album_progress_points`: 0;
- `historical_inventory_mutations`: 0;
- `canonical_trophy_unlocks`: 0;
- `feed_events`: 0;
- `sammlr_news`: 0.

Dedupe-Prüfungen ergaben jeweils 0 doppelte Completion-Keys, kanonische
Trophy-Kombinationen, Feed-Event-Keys und Notification-Dedupe-Keys. Die 89
Notifications und ihr vorhandener Typmix waren vor und nach dem Upgrade exakt
gleich; die Migration erzeugte keine Notification- oder Feed-Writes.

## 6. Startup- und Read-Smoke auf V18

Der echte isolierte Gunicorn-Prozess lieferte:

- `/healthz`: 200;
- `/login`: 200;
- `/static/style.css`: 200;
- unauthentifizierte Kernrouten: kontrolliert 302 zu `/login`.

Ein zusätzlicher authentifizierter, read-only Anwendungssmoke ohne reale
Anmeldedaten bestätigte jeweils HTTP 200 für:

- Feed/Home;
- Sammlung;
- Trades;
- Inbox-GET;
- Profil;
- albumbezogenes SmartMatch.

## 7. Zweiter Restore / Rollbacknachweis

Das unveränderte Originalbackup wurde erneut in eine neue Datei restauriert:

`/private/tmp/sammlr-s34-operator-drill-20260821T190800Z/rollback-v7/rollback-v7.db`

- Restore-Dauer: 0,05 Sekunden;
- Schema: V7;
- SHA-256:
  `ac58159ce9b90cbd384430d3e6771954531562f383e12b213c10b18609ea34d5`;
- bytegleich zum Originalbackup;
- `integrity_check = ok`;
- `foreign_key_check`: 0 Befunde;
- zentrale Counts und Inventarsummen unverändert;
- Dateimodus `0600`, Elternverzeichnis `0700`.

Der erneute echte Gunicorn-Start war erfolgreich. `/login` und das zentrale
Asset lieferten 200, geschützte Kernrouten die erwarteten 302-Redirects und
`/healthz` im bewusst nicht aktualisierten V7-Zustand korrekt 503.

Damit ist die vollständige Kette praktisch nachgewiesen:

`Backup → Restore V7 → Upgrade V18 → erneuter Restore V7`.

## 8. Zeit- und Recovery-Gates

- gesamtes Operatorfenster einschließlich Vor-/Nachprüfung und HTTP-Smokes:
  4 Minuten 44 Sekunden;
- erster Restore: 0,03 Sekunden;
- Upgrade V7→V18: 0,04 Sekunden;
- zweiter Restore: 0,05 Sekunden;
- S34-RTO von 60 Minuten: eingehalten;
- das Backup bildet den aktuellen Betreiberstand ab; S34-RPO von 24 Stunden:
  eingehalten.

## 9. Bestands-DB-Schutz und Abschlussprüfung

Nach dem Drill wurde die echte Bestands-DB erneut ausschließlich read-only
geprüft:

- Schema: weiterhin V7;
- SHA-256:
  `3eb9da3b6d4898533030221bc80e8ed6406a25458eb8e1bca1f0e473a515b056`;
- `integrity_check = ok`;
- `foreign_key_check`: 0 Befunde;
- zentrale Counts unverändert.

Die echte DB wurde weder migriert noch restauriert oder als Testziel
verwendet. Backup- und Restore-Dateien liegen außerhalb des Repositories und
werden weder committed noch gepusht. `git diff --check` ist ohne Befund.

## 10. Aufgetretene Probleme und Restrisiken

Der erste Backup-CLI-Aufruf brach vor jeder DB-Aktion ab, weil der
Repository-Modulpfad nicht gesetzt war. Der erfolgreiche Wiederholungsaufruf
verwendete explizit `PYTHONPATH=.`. Der erste lokale Gunicorn-Bindversuch wurde
von der Ausführungssandbox abgewiesen; der identische, freigegebene
localhost-only Start war erfolgreich. Beide Vorfälle hatten keine Wirkung auf
eine Datenbank.

Der technische Recoveryvertrag ist praktisch erfüllt. Als externer
Closed-Beta-Blocker verbleibt ausschließlich die juristische Endprüfung der
Datenschutztexte und finalen Betreiberangaben. Diese Freigabe wird durch den
S34-Drill nicht ersetzt.

## 11. Bewertung

**S34 erfüllt: JA.**

**Technischer Betreiber-Recoveryblocker geschlossen: JA.**

**Closed Beta freigegeben: NEIN.**

**Externe Nutzer eingeladen: NEIN.**

**Nächster Schritt:** juristische Endprüfung und finale Betreiberangaben.

Kein Commit und kein Push wurden ausgeführt.
