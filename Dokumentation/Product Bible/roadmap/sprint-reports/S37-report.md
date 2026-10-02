# Sprint S37 – Abschlussbericht

Stand: 2026-08-09

## Ziel und Scope

S37 vereinheitlicht ausschließlich UX, Routing und Bedienkonsistenz der bereits
vorhandenen Funktionen. Die Product-Owner-Klärung zur dauerhaft dreiteiligen
Bottom-Navigation wurde umgesetzt. S38 wurde nicht begonnen.

## Architektur und Datenfluss

Die bestehenden servergerenderten Seiten verwenden weiterhin ihre bisherigen
Read- und Fachservices. Ergänzt wurden ausschließlich gemeinsame
Darstellungsbausteine: globaler Header, bestehende Bottom-Navigation,
kontextuelle Rücklinks, Feedback-/Leerzustände sowie ein clientseitiger
Submit-Status nach dem regulären POST-Start. Es gibt keine neue Datenquelle und
keine zweite fachliche Wahrheit.

Die ausführliche Architektur ist in
[`s37-beta-polish.md`](../s37-beta-polish.md) dokumentiert.

## Geänderte und neue Dateien

Geändert:

- `App/webapp.py`
- `App/static/style.css`
- `tests/test_s31_ui_foundation.py`
- `Dokumentation/Product Bible/roadmap/README.md`

Neu:

- `tests/test_s37_beta_polish.py`
- `Dokumentation/Product Bible/roadmap/s37-beta-polish.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S37-ux-routing-smoke.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S37-report.md`

## Umgesetzte Konsistenzkorrekturen

- Exakt drei mobile Hauptziele: Sammlung, `sammlr.`, Tauschen.
- Profil und Notifications ausschließlich im Header.
- Header/Navigation auch auf Papierliste, Dealansicht, Problemweg,
  Stickerdetail, Profilformularen und Datenexport konsistent verfügbar.
- Fachlich lokale Rückwege bleiben erhalten.
- Leere Sammlung und leere Nutzersuche besitzen verständliche Zustände; der
  Sammlungs-Empty-State besitzt die bestehende Aktion `Album hinzufügen`.
- Redirect-Feedback wird auf Notifications, Freundesliste und öffentlichem
  Profil sichtbar.
- Feedbackfarben verwenden die vorhandenen S30-Statustokens.
- POST-Formulare erhalten nach regulärem Submit einen `aria-busy`-Status und
  Schutz vor Doppelklicks.

## Unveränderte Komponenten

Keine Änderungen an Inventory, Availability, Snapshot, Trades, Versand,
Empfang, Problemfällen, Coverage, TopMatch, Smart Requests, Notificationtypen,
Communityfachlogik, Privacy, Ratings, Account Lifecycle oder Exportservice.
Keine Route, Berechtigung oder Produktregel wurde ergänzt oder verändert.

## Testmatrix und Ergebnisse

| Bereich | Abdeckung | Ergebnis |
| --- | --- | --- |
| Navigation/Header | drei Ziele, keine Dopplung, Workflowseiten | bestanden |
| Routing | Album-, Trade- und Profilrückwege | bestanden |
| Empty States | Sammlung und Suche | bestanden |
| Feedback | Notifications, Freunde, Tonalität | bestanden |
| Loading | aria-busy, verzögertes Disable, Reduced Motion | bestanden |
| Read-only | Inventory vor/nach GET identisch | bestanden |
| Regression | vollständiges S01–S37-Gate zweimal | 523/523, zweimal bestanden |

Testbefehle:

```bash
PYTHONDONTWRITEBYTECODE=1 \
/private/tmp/sammlr-s32-py313-venv/bin/python \
-m unittest tests.test_s37_beta_polish -v

PYTHONDONTWRITEBYTECODE=1 \
/private/tmp/sammlr-s32-py313-venv/bin/python \
-m unittest discover -s tests -p "test_s*.py" -v
```

Ergebnisse:

- S37-spezifisch: 6 Tests, 6 bestanden.
- Erstes Gesamtgate: 523 Tests, 523 bestanden, 0 übersprungen.
- Zweites Gesamtgate: 523 Tests, 523 bestanden, 0 übersprungen.
- Syntaxprüfung: bestanden.
- `git diff --check`: bestanden.

## Datenbank und Migration

S37 benötigt und erzeugt keine Migration. Die kanonische S00-Fixture und die
lokale Entwicklungsdatenbank werden durch Hashguards geschützt und nicht
migriert. `PRAGMA integrity_check` meldet für beide Dateien `ok`;
`PRAGMA foreign_key_check` meldet keine Zeilen.

SHA-256 nach der Abnahme:

- lokale Entwicklungsdatenbank: `db29a8b84f11adeeed3a894b99df96f77ab82b26f994dc592f5f446b20490477`
- S00-Fixture: `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`

## Release Readiness und bekannte Grenzen

Die S37-UX-Härtung ist nach dem zweifachen Gesamtgate technisch abgenommen.
Die bereits in S35 dokumentierten Performance-Release-Blocker bleiben davon
unverändert bestehen; S37 enthält ausdrücklich keine Performanceoptimierung.
Der reproduzierbare Browser-Smoke steht im
[`S37-ux-routing-smoke.md`](S37-ux-routing-smoke.md).

## Offene Punkte für S38

Keine Arbeit wurde vorgezogen. Performance- und weitere Quality-Themen bleiben
dem dafür vorgesehenen späteren Scope vorbehalten.

## Scope-Bestätigung

- ausschließlich S37 bearbeitet
- keine neue Fachlogik und kein neues Feature
- keine Migration und keine Datenbankänderung
- S38 nicht begonnen
- kein Commit
- kein Push
