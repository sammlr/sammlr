# Sammlr RC1 – technische Abnahmecheckliste

Stand: 9. August 2026

## Definition

**Sammlr RC1** ist der intern reproduzierbare technische Kandidat auf dem
abgeschlossenen Stand S00–S38 und Schema V0012. RC1 ist weder eine öffentliche
Version 1 noch eine Freigabe für die Public Beta. Der Kandidat darf erst nach
diesem Gate als gemeinsame Grundlage für die nächste Product-Owner-/Engineering-
Besprechung verwendet werden.

## Vor Deployment

- [x] Offizielles CPython 3.13.15 verwendet; `hashlib.scrypt` verfügbar.
- [x] Abhängigkeiten der freigegebenen Runtime vorhanden, einschließlich Flask
  und Gunicorn.
- [x] Migrationsmanifest V0001–V0012 vollständig und lückenlos.
- [x] S00-Fixture und lokale Entwicklungsdatenbank durch SHA-256-Guards geschützt.
- [x] Frische S00-Kopie kontrolliert bis V0012 migriert.
- [x] Wiederholter Up-Lauf auf V0012 ist ein No-op.
- [x] Realistische V0007-Entwicklungskopie vor Migration gesichert und bis V0012
  migriert.
- [x] `PRAGMA integrity_check` ergibt `ok`.
- [x] `PRAGMA foreign_key_check` ergibt keine Zeile.
- [x] Produktionskonfiguration bleibt ohne externes Secret fail-closed.
- [x] Produktionsdatenbankpfad bleibt gemäß S34 explizit `/var/data/sammlr.db`.
- [x] Debugrouten sind in Produktion nicht registriert.
- [ ] S35-Performance-Release-Blocker behoben und Baseline erneut bestanden.
- [ ] Funktionale Datenschutztexte juristisch final geprüft und Betreiberangaben
  finalisiert.

## Deployment-Vertrag

1. Releaseartefakt und externe Konfiguration bereitstellen.
2. Vor jeder Migration `Scripts/predeploy.py` ausführen; das Skript erstellt
   zuerst ein privates, gehashtes SQLite-Backup.
3. Migration ausschließlich gegen den expliziten Produktionspfad ausführen.
4. Migrationsstand V0012 sowie Integritäts- und Fremdschlüsselprüfung bestätigen.
5. Gunicorn gemäß `Procfile` mit einem Worker starten.
6. `/healthz`, `/login` und `/static/style.css` prüfen.
7. Mit einem gültigen Konto anmelden; Home, Sammlung, Tauschbereich,
   Notifications, Profil und einen berechtigten Deal öffnen.
8. Produktions-404 für `/debug-db` und `/debug-seed-now` bestätigen.
9. Fehler- und Request-Logs auf Request-ID, Redaction und unerwartete Fehler prüfen.

## Unmittelbar nach Deployment

- [ ] Healthcheck liefert HTTP 200 und `{"status":"ok"}`.
- [ ] Login und Sessionrotation funktionieren.
- [ ] Assets liefern HTTP 200.
- [ ] Mutierende historische GET-Ziele liefern HTTP 405.
- [ ] POST-Mutationen lehnen fehlende/ungültige CSRF-Tokens ab.
- [ ] Inventar-, Trade-, Community- und Notification-Smoke ohne Datenabweichung.
- [ ] Backup-Pfad, SHA-256, Migrationsstand und Operator dokumentiert.
- [ ] Rollbackentscheidung berücksichtigt fail-closed Backouts mit Fachdaten.

## RC1-Entscheidung

- **Interner technischer RC1:** hergestellt.
- **Public Beta:** nicht freigegeben.
- **Grund:** Die vollständigen Funktions-, Migrations-, Security- und
  Produktionsvertragsgates sind grün; die aus S35 übernommenen verbindlichen
  Performance-Release-Blocker und die juristische Endprüfung bleiben offen.

## S38-Abnahme

- [x] Roadmap vollständig abgeglichen.
- [x] Migration frisch bis Zielstand ausgeführt.
- [x] Upgradepfad geprüft.
- [x] Datenbankintegrität bestätigt.
- [x] `foreign_key_check` sauber.
- [x] Securitygate grün.
- [x] Vollständige Regression zweimal grün.
- [x] End-to-End-Contract-Smoke grün.
- [x] Produktionsstartvertrag reproduziert.
- [x] Backup-/Recovery-Vertrag vorhanden und isoliert geprüft.
- [x] Bekannte Release-Blocker dokumentiert.
- [x] Lokale Entwicklungsdatenbank nicht verändert.
- [x] S00-Fixture nicht verändert.
- [x] Kein Commit erstellt.
- [x] Kein Push durchgeführt.
