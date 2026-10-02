# S34 – Recovery- und Incident-Checkliste

Stand: 2026-08-18

## Recovery

1. gewünschtes Backup nach Zeitpunkt auswählen und kontrolliert bis V0018 migrieren.
2. SHA-256 des unveränderten Backups berechnen und dokumentieren.
3. neue isolierte Recovery-Zieldatei festlegen; Production nie überschreiben.
4. Restore über die SQLite Backup API erzeugen.
5. SQLite-Öffnung prüfen.
6. `PRAGMA integrity_check = ok` prüfen.
7. leeren `PRAGMA foreign_key_check` prüfen.
8. Migrationsstand V0018 prüfen.
9. Test-App ausschließlich gegen die Recovery-Datei starten.
10. `/healthz` und `/login` prüfen.
11. Home, Sammlung, Tradeübersicht, Profil und Notifications read-only prüfen.
12. Ergebnis, Dauer und SHA-256 dokumentieren.
13. einen echten Restore erst nach vollständig grüner manueller Freigabe
    durchführen.

## Incident-Miniplan

1. betroffenen Deploymentstand und Request-IDs sichern.
2. weitere Deployments stoppen; keine Produktdaten manuell verändern.
3. strukturierte Request- und Error-Events anhand der Request-ID korrelieren.
4. bei möglichem Datenbankschaden Schreibzugriffe stoppen und ein konsistentes
   Backup erstellen.
5. Recovery-Drill nach obiger Liste durchführen.
6. Restore nur bei vollständiger technischer Freigabe planen.
7. Zeitpunkt, Auswirkung, Entscheidung, Backup-Hash und Abschlussprüfung
   dokumentieren.

Beta-Ziele: RPO höchstens 24 Stunden, RTO höchstens 60 Minuten.
