# S34 – Deployment-Checkliste

Stand: 2026-08-18

1. `SAMMLR_ENV=production`, externes Secret, `PORT` und
   `DATABASE_PATH=/var/data/sammlr.db` prüfen.
2. Production-Datenbank erreichbar prüfen.
3. konsistentes Pre-Migration-Backup in `/var/data/backups/` erzeugen.
4. Backup-Pfad und SHA-256 im Deploymentprotokoll dokumentieren.
5. technische Öffnung und Integrität des Backups prüfen.
6. Migration Runner separat bis V0018 ausführen.
7. `PRAGMA integrity_check` muss `ok` liefern.
8. `PRAGMA foreign_key_check` darf keinen Treffer liefern.
9. Migrationsstand muss exakt V0018 sein.
10. Gunicorn mit genau einem Worker starten.
11. `/healthz` muss HTTP 200 liefern.
12. `/login` muss HTTP 200 liefern.
13. `/` muss unauthentifiziert zum Login umleiten.
14. ein statisches Asset muss erreichbar sein.
15. Logs auf unmittelbare oder wiederholte HTTP 500 prüfen.

Bei einem Fehler in Backup, Migration, Integrität, Version, Start oder Smoke
wird das Deployment abgebrochen. Es gibt keine Trotzdem-Option.
