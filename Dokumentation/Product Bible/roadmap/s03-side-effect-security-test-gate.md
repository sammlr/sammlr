# S03 – Nebenwirkungen, Security-Baseline und Phase-0-Testgate

| Feld | Wert |
| --- | --- |
| Status | abgeschlossen |
| Stand | 2026-07-29 |
| Verbindliche Grundlage | [Development Roadmap V1, Sprint S03](development-roadmap-v1.md#s03--nebenwirkungen-security-baseline-und-ci-testgate) |
| Abhängigkeiten | S00–S02 |
| Anwendungscode | unverändert |
| Datenbankschema | unverändert |

Diese Notiz definiert ausschließlich das lokale Phase-0-Pflichtgate und
dokumentiert die S03-Baseline für Trophäen, Notifications, Sessions und
Loginpflicht. Sie richtet keine vollständige CI-Plattform ein.

## Verbindlicher Phase-0-Testbefehl

Vom Repository-Wurzelverzeichnis:

```sh
python3 -m unittest discover -s tests -p 'test_s0*.py' -v
```

Der Befehl führt S01, S02 und S03 gemeinsam aus. Zum S03-Abschluss umfasst das
Gate 43 Tests.

## Pflichtgate vor Merge

Vor jedem Merge mit Auswirkungen auf den Phase-0-Kern gilt:

1. Der Befehl wird ohne gesetzte S01-/S02-Mutationsvariablen ausgeführt.
2. Alle Tests müssen mit `OK` enden.
3. Kein Test darf `App/Database/sammlr.db` oder die kanonische S00-Fixture
   verändern.
4. Ein Fehlschlag blockiert den Merge, bis die Regression behoben oder die
   fachliche Änderung ausdrücklich entschieden und die Referenztests bewusst
   angepasst wurden.
5. Sachfremde Änderungen dürfen nicht zusammen mit einer Testkorrektur als
   notwendige S03-Arbeit dargestellt werden.

Das Gate ist ein lokaler Pflichtbefehl. Die Anbindung an eine bestimmte
CI-Plattform ist ausdrücklich nicht Bestandteil von S03.

## S03-Testmatrix

| Nr. | Bereich | Geschütztes Verhalten |
| ---: | --- | --- |
| 1 | Testdatenisolation | jeder Test startet aus einer eigenen unveränderten S00-Kopie |
| 2 | Album-Trophy-Historie | sichtbare und stille Unlocks werden je Nutzer/Album/Titel nur einmal gespeichert |
| 3 | Global-Trophy | der aus dem Referenztrade berechnete Unlock `Tauschgeschäfte 1` erscheint genau einmal |
| 4 | Popup-Queue | doppelte Titel werden entfernt; die Queue wird genau einmal konsumiert |
| 5 | Notification-Adapter | ungelesene Meldungen sind nutzergebunden, begrenzt und deterministisch sortiert |
| 6 | Annahme-Nebenwirkung | wiederholtes Accept erzeugt nur eine Annahme-Notification |
| 7 | Abschluss-Nebenwirkung | wiederholtes Confirm erzeugt pro beteiligter Seite nur eine Abschluss-Notification |
| 8 | Notification-Zugriff | Nutzer können nur ihre eigene Meldung als gelesen markieren |
| 9 | anonyme Lesezugriffe | Home, Album, Papierliste, Trades, Trophäen und Profil verlangen Login |
| 10 | anonyme Schreibzugriffe | Bestand, Papiertransfer, Anfrage, Confirm und Notification-Read bleiben ohne Nebenwirkung gesperrt |
| 11 | öffentliche Auth-Routen | Login und Registrierung bleiben anonym erreichbar |

## Genau-einmal-Nebenwirkungen

Folgende Invarianten sind im Gate nachweisbar:

- Die Unique-Regel der Trophy-Historie wird durch wiederholte Unlock-Aufrufe
  nicht verletzt.
- Bereits persistierte Trophy-Titel werden nicht erneut als sichtbar neu
  zurückgegeben.
- Doppelte Popup-Titel erscheinen nur einmal.
- Nach dem Konsum bleibt keine Popup-Wiederholung in derselben Queue.
- Statusgeschützte wiederholte Tradeaktionen erzeugen keine zusätzlichen
  Accept- oder Completion-Notifications.
- Die Abschlussmeldung wird genau einmal für Nutzer 1 und genau einmal für
  Nutzer 2 angelegt.

## Testdatenisolation

Die S03-Suite verwendet dieselbe Sicherheitsstrategie wie S01 und S02:

1. Noch vor dem Import von `App/webapp.py` zeigt `DATABASE_PATH` auf eine
   temporäre Bootstrap-Kopie.
2. Jeder Test erhält eine neue Kopie von
   `App/Database/sammlr_reference_s00.db`.
3. `webapp.DB` zeigt während des Falls ausschließlich auf die Testkopie.
4. Zeitabhängige Notification-Sortierungen verwenden explizite synthetische
   Zeitstempel.
5. Nach jedem Test werden die SHA-256-Prüfsummen der Standard-Datenbank und
   der kanonischen Fixture kontrolliert.
6. Temporäre Dateien werden nach dem Test verworfen.

## Bekannte, bewusst offene Security-Gaps

S03 dokumentiert diese Befunde, setzt sie aber aufgrund des Roadmap-Umfangs
nicht um:

- Passwörter werden im bestehenden Modell nicht gehasht. Eine
  Passwortmigration ist ausdrücklich aus S03 ausgeschlossen.
- Der Flask-Session-Key ist im Anwendungscode statisch.
- Es besteht noch kein CSRF-Schutz für schreibende Formulare.
- Mehrere mutierende Bestands- und Notification-Routen verwenden `GET`.
- Fehlende Berechtigungen werden häufig durch Redirect statt durch einen
  expliziten Fehlerstatus beantwortet.
- Die Debug-Routen `debug_db` und `debug_seed_now` sind in der bestehenden
  Public-Endpoint-Liste anonym erreichbar; die Seed-Route verwendet einen
  statischen Query-Key.
- Es gibt in S03 keine Rate-Limits, Login-Sperren oder vollständige
  Session-Härtung.
- Eine externe CI-Plattform erzwingt das lokale Pflichtgate noch nicht.

Diese Punkte dürfen nicht stillschweigend als erledigt gelten.

## Bewusste Nichtabdeckung

Nicht umgesetzt oder getestet wurden:

- Passwortmigration,
- Glocken- oder Notification-UI,
- vollständige CI-Plattform,
- Navigation und Home,
- neue Stickerwall-Bedienelemente,
- Profilfunktionen,
- Trade Lifecycle oder Smart Trader,
- neue Trophäen oder Trophäen-Design,
- CSS, JavaScript oder andere sichtbare Änderungen.

## Technische Änderungen

Am Anwendungscode waren keine Änderungen notwendig. Ergänzt wurden nur:

- eine S03-Testdatei in der bestehenden `tests`-Struktur,
- diese Testgate-Dokumentation,
- der S03-Sprintbericht,
- der Verweis im Roadmap-Index.

## Abschluss

S03 ist abgeschlossen, wenn zwei vollständige Ausführungen des
Phase-0-Testbefehls mit 43 von 43 Tests grün enden und der Git-Diff keine
sachfremden S03-Änderungen enthält.
