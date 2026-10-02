# S20 – Debug-Start-Smoke

Stand: 06.08.2026

> Historischer Prüfbericht: Die Debug-Integration und ihre temporäre Datenbank
> wurden nach erfolgreichem S20-Closeout am 06.08.2026 vollständig entfernt.
> Die folgenden Pfade und Befehle dokumentieren nur den ausgeführten Smoke-Test
> und sind nicht mehr als aktuelle Startanleitung gedacht.

## Ergebnis

Der isolierte Debug-Start und die Route `/debug/trade-coverage` funktionieren.
Ein echter lokaler Flask-Prozess wurde gegen die temporäre Debug-Datenbank
gestartet und per HTTP GET geprüft. Ergebnis: **HTTP 200**.

Die Debug-Accounts sind ausschließlich auf der technischen Debug-Route
sichtbar. Sie werden nicht in die normale Tauschbörse oder eine normale
Produktdatenbank übernommen.

## Datenbank und Start

Exakter absoluter Datenbankpfad:

`/private/tmp/sammlr-s20-debug-coverage-20260806.db`

Exakter Startbefehl aus dem Projektstamm:

```bash
DATABASE_PATH=/private/tmp/sammlr-s20-debug-coverage-20260806.db \
SAMMLR_DEBUG_COVERAGE=1 \
python3 App/webapp.py
```

Danach ist die Prüfung erreichbar unter:

`http://127.0.0.1:8080/debug/trade-coverage`

Für den automatisierten HTTP-Smoke wurde derselbe Startvertrag auf dem freien
Prüfport 8092 verwendet.

## Sichtbare Prüfdaten

Die HTTP-Antwort enthält:

- Valentin Debug
- Anna Debug
- Mehmet Debug
- Sofia Debug
- Community: 10 fehlend, 6 verfügbar, 4 nicht verfügbar, 60 %
- Valentin → Anna: 5 physisch vorhanden, 4 effektiv verfügbar, 40 %
- Valentin → Mehmet: 3 physisch vorhanden, 3 effektiv verfügbar, 30 %
- Valentin → Sofia: 1 physisch vorhanden, 0 effektiv verfügbar, 0 %

## Korrektur der Debug-Integration

Die Route verlangte zuvor zusätzlich die nicht zum gewünschten Startvertrag
gehörende Variable `SAMMLR_DEBUG_COVERAGE_DB`. Diese überzählige Debug-Sperre
wurde entfernt.

Die Isolation bleibt gewährleistet:

- `SAMMLR_DEBUG_COVERAGE` muss exakt `1` sein.
- Die normale lokale Datenbank und die S00-Fixture sind als Ziele ausdrücklich
  gesperrt.
- Die aktive Datenbank muss den internen Marker
  `s20-trade-coverage-v1` enthalten.
- Die vier erwarteten Debug-Nutzer müssen vollständig vorhanden sein.
- Ohne diese Bedingungen liefert die Route HTTP 404.

## Tests und Schutz

```bash
python3 -m unittest tests.test_s20_debug_coverage -v
```

Ergebnis: 13 Tests erfolgreich.

Zusätzlich geprüft:

- realer HTTP GET: Status 200
- alle vier Debug-Nutzer in der Antwort
- alle Community- und persönlichen Coverage-Zahlen in der Antwort
- Debug-Route mit normaler Produktdatenbank: HTTP 404
- Debug-Route ohne Aktivierungsvariable: HTTP 404
- Debug-Route ohne Fixture-Marker: HTTP 404

Es wurden keine Produktdaten, keine normale Produktfunktion und keine normale
Tauschbörsenansicht geändert. Kein Commit und kein Push.
