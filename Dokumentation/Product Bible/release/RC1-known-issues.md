# Sammlr RC1 – bekannte Befunde und technische Schuld

Stand: 9. August 2026

Diese Liste ist eine Bestandsaufnahme. S38 behebt oder optimiert keinen der
aufgeführten Punkte.

## Release-Blocker

### S35-Performance-Baseline

Die verbindliche Baseline mit Gunicorn, SQLite, 20 parallelen Requests und dem
S35-Datensatz ist weiterhin nicht bestanden:

| Ablauf | S35-Befund | Einstufung |
|---|---:|---|
| Sammlung | > 5.000 ms, 20/20 Timeouts | Release-Blocker |
| Album | > 5.000 ms, 20/20 Timeouts | Release-Blocker |
| Stickerwall | > 5.000 ms, 20/20 Timeouts | Release-Blocker |
| Suche | P95 1.472,898 ms | Release-Blocker |
| Tradebörse | > 5.000 ms, 20/20 Timeouts | Release-Blocker |
| Dealansicht | > 5.000 ms, 20/20 Timeouts | Release-Blocker |
| Notifications | > 5.000 ms, 20/20 Timeouts | Release-Blocker |
| Profil | P95 1.918,630 ms | Release-Blocker |

Login und Home lagen in S35 innerhalb der Grenze. S38 hat die Baseline bewusst
nicht erneut ausgeführt und keine Optimierung vorgenommen. Vor einer Public
Beta ist nach einer gesondert freigegebenen Performancearbeit eine vollständige
Neumessung mit 0 % Fehlerquote erforderlich.

## Freigaberelevante offene Punkte

- Die Datenschutzerklärung, das Impressum und die Exporthinweise aus S36 sind
  funktionale Entwürfe. Juristische Endprüfung und endgültige Betreiberangaben
  fehlen.
- Eine öffentliche Beta-Freigabe, Rollout-Kommunikation und Nutzer-Support sind
  nicht Bestandteil von RC1.
- Produktionsbackup und Restore sind technisch vertraglich abgesichert, müssen
  aber im realen Betreiberumfeld weiterhin operativ geprobt und dokumentiert
  werden.

## Test- und Laufzeitwarnungen

- Der finale zweite vollständige RC-Lauf enthielt 2.148 Logzeilen mit dem Marker
  `ResourceWarning`, überwiegend für nicht explizit geschlossene ältere
  SQLite-Testverbindungen. Die Tests bleiben grün; die Warnungen sind technische
  Schuld und können Dateideskriptor-/Verbindungsprobleme verdecken.
- Zwei bereits seit S34/S35 dokumentierte `SyntaxWarning`-Hinweise wurden bei
  der finalen Syntaxinventur reproduziert: ungültige Escape-Sequenzen `\d` in
  `App/webapp.py` bei Zeile 5453 und 5458. Sie verhindern Parsing und Tests
  nicht, bleiben aber unbehebene technische Schuld.
- Die nicht produktiv geladene Archivkopie
  `App/Archive/webapp_backup_before_trophy_cleanup.py` ist bei einer bewusst
  überbreiten Syntaxinventur mit einem vorbestehenden `IndentationError` in
  Zeile 941 aufgefallen. Produktive App-, Service-, Migrations-, Script- und
  Testquellen bestehen die separate Syntaxprüfung; S38 verändert das Archiv
  nicht.
- Ältere Debug-Ausgaben wie `FINAL URL` und `TRIGGER =` erzeugen unnötiges
  Testlog-Rauschen.

## Datenbank- und Artefaktbeobachtungen

- Die kanonische S00-Fixture ist weiterhin Schema V0000 und besitzt SHA-256
  `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`.
- Die lokale Entwicklungsdatenbank war beim S38-Gate weiterhin V0007 und besitzt
  SHA-256 `db29a8b84f11adeeed3a894b99df96f77ab82b26f994dc592f5f446b20490477`.
  Sie wurde nicht migriert. Für den RC wurde ausschließlich eine temporäre Kopie
  mit vorangestelltem Backup bis V0012 migriert.
- Die in älteren Reports dokumentierte historische Hashabweichung der lokalen
  Entwicklungsdatenbank ist nicht aufgeklärt. `integrity_check` und
  `foreign_key_check` sind aktuell unauffällig.
- Der Unterschied zwischen lokaler V0007-Datenbank und aktuellem V0012-Code ist
  kein Produktionsvertrag. Ein realer Start muss das S34-Predeploy-Gate nutzen.

## Architektur- und UX-Schuld

- `App/webapp.py` und `App/static/style.css` bleiben große, historisch gewachsene
  Dateien. S38 nimmt kein Refactoring vor.
- Referenzseiten und UX-Smokes sind abgesichert; eine gesonderte Quality-/UI-Woche
  wurde nicht begonnen.
- Tablet/Desktop bleiben regressionsgesichert, sind aber nicht vollständig neu
  gestaltet.

## Bewusst vertagte Product-Bible-Themen

Unter anderem bleiben Multi-Album-Komfortfunktionen, Albumtransfer, Scanner,
Offline-/QR-Funktionen, regionale Events, Marktplatz/Shop, Versandprodukte,
Premiumfunktionen, globale Suche und Mehrparteien-Tausch außerhalb RC1. Diese
Punkte sind keine impliziten S38-Zusagen.
