# Sprintbericht S38 – Finales Release-Candidate-Gate

Stand: 9. August 2026

## Ergebnis

Der interne technische Stand **Sammlr RC1** ist reproduzierbar hergestellt.
Die Public Beta ist **nicht freigegeben**. S38 hat keine neue Produktfunktion,
keine Fachlogik, keine Migration, kein Refactoring und keine
Performanceoptimierung eingeführt. Die aus S35 übernommenen Performance-
Release-Blocker und die juristische Endprüfung aus S36 bleiben offen.

## Ziel und Scope

S38 schließt den bisherigen Roadmap-Stand durch einen letzten Abgleich, isolierte
Migrations- und Upgradeprüfungen, den Produktions-/Security-Vertrag, einen
ausführbaren Kernworkflow-Nachweis und die RC-Dokumentation ab. Grundlage waren
Product Bible, Development Roadmap V1, Current-State Gap Analysis sowie die
Spezifikationen und Reports S00–S37 einschließlich S18.2 und S32–S37.

Der ältere Gap-Analysis-Stand wurde nicht als neue Produktanforderung behandelt.
Die späteren verbindlichen Sprintentscheidungen und Reports haben Vorrang, wo
sie frühere Lücken nachweislich geschlossen haben.

## RC1-Vertrag

RC1 bezeichnet den internen Kandidaten auf:

- CPython 3.13.15 mit `hashlib.scrypt`,
- Anwendungscode nach S37,
- lückenlosem Migrationsmanifest V0001–V0012,
- expliziter Produktionskonfiguration nach S34,
- vollständigem S01–S38-Testgate,
- dokumentierten statt verdeckten Release-Blockern.

RC1 ist kein öffentlicher Release, keine Public Beta und keine Zusage für
vertagte Product-Bible-Funktionen.

## Neue Dateien

- `tests/test_s38_release_candidate.py`
- `Dokumentation/Product Bible/release/RC1-checklist.md`
- `Dokumentation/Product Bible/release/RC1-known-issues.md`
- `Dokumentation/Product Bible/release/RC1-test-matrix.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S38-report.md`

Bestehende Anwendungscode-, CSS-, JavaScript-, Datenbank- und Migrationsdateien
wurden durch S38 nicht geändert.

## Isolierte Datenbankprüfungen

### Frischer Stand

Eine temporäre Kopie von `sammlr_reference_s00.db` wurde von V0000 in exakt
dieser Reihenfolge migriert:

`V0001, V0002, V0003, V0004, V0005, V0006, V0007, V0008, V0009, V0010, V0011, V0012`

Der zweite Up-Lauf lieferte keine Änderung. Der Ledger enthält alle zwölf
Versionen mit den kanonischen Checksums. `integrity_check` ergab `ok`,
`foreign_key_check` keine Zeile.

### Realistischer Upgradepfad

Die lokale Entwicklungsdatenbank wurde nur als Quelle gelesen und in ein
temporäres RC-Verzeichnis kopiert. Ausgangsstand der Kopie war V0007. Das
S34-Predeploy-Gate erstellte zuerst ein privates, gehashtes Backup und führte
danach ausschließlich V0008–V0012 aus. Backup V0007 und Ziel V0012 bestanden
die Artefakt-, Integritäts- und Fremdschlüsselvalidierung. Ein separater
Anwendungsimport gegen genau diese migrierte Kopie lieferte anschließend für
`/healthz` HTTP 200. Die temporären
Artefakte wurden mit dem Testverzeichnis entfernt.

Nicht verändert wurden:

- S00-Fixture, SHA-256
  `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`,
- lokale Entwicklungsdatenbank, SHA-256
  `db29a8b84f11adeeed3a894b99df96f77ab82b26f994dc592f5f446b20490477`,
- Backups und sonstige Datenbankkopien im Projekt.

Eine neue Migration war nicht erforderlich und wurde nicht erzeugt.

## Produktionsvertrag

Der Produktionsmodus wurde in einem separaten Prozess gegen eine isolierte
V0012-RC-Datenbank reproduziert:

- externe Produktionskonfiguration gesetzt,
- Gunicorn-WSGI-Import `webapp:app` erfolgreich,
- produktiver `ProxyFix` aktiv,
- `/healthz` HTTP 200,
- `/login` HTTP 200 und gültiger Login HTTP 302,
- Home, Sammlung, Tauschen, Notifications und Profil HTTP 200,
- `/static/style.css` HTTP 200,
- `/debug-db` und `/debug-seed-now` HTTP 404,
- historische mutierende GET-Ziele HTTP 405.

Der reale Pfad `/var/data/sammlr.db` wurde nicht beschrieben. Für die isolierte
Probe wurde ausschließlich im Subprozess die S34-Pfadkonstante auf die
temporäre RC-Datenbank gebunden. Es wurde kein öffentlich erreichbarer Server
gestartet und keine echte Produktionsdatenbank verwendet.

## Security- und Integritätsgate

Das Gesamtgate bestätigt weiterhin:

- kanonisches scrypt und erfolgreiche Legacy-Hash-Migration nach gültigem Login,
- Fail-closed-Start in Produktion ohne `SAMMLR_SECRET_KEY`,
- getrenntes temporäres Development-Secret und explizites Test-Secret,
- Sessionrotation und `auth_version`-Invalidierung,
- Login-Throttling,
- CSRF vor mutierenden POST-Aktionen,
- HTTP 405 und Persistenzfreiheit historischer mutierender GETs,
- produktive GETs ohne persistente Fachmutation mit den in S33 ausdrücklich
  dokumentierten Ausnahmen,
- Produktions-404 für Debugrouten,
- erneute Passwortprüfung bei sensiblen aktuellen Kontofunktionen.

## Kernworkflow und Testbestand

Die S38-Prüfung erzeugt bewusst keine große zweite Quality-Fixture. Sie nutzt
temporäre S00-/Entwicklungskopien und erzwingt per ausführbarer Contract-Matrix,
dass die bestehenden isolierten Workflowtests im vollständigen Gate vorhanden
sind und laufen. Abgedeckt sind mehrere Nutzer, mehrere Alben und differenzierte
Inventarstände sowie:

- Registrierung, Login und Session,
- Sammlung und Inventar,
- manuelle und Smart-Anfragen,
- Annahme und Reservierung,
- Versand und Transit,
- Empfang und Abschluss,
- Teilmengen, Problembericht, Retry und Auflösung,
- Notifications und operatives Home,
- Privacy und Tradepool,
- Bewertungen,
- Freundschaften, Blockierung und Suche,
- Datenexport und Account Lifecycle.

Die detaillierte Zuordnung steht in `release/RC1-test-matrix.md`.

## Testresultate

Verwendeter Interpreter:
`/private/tmp/sammlr-s32-py313-venv/bin/python` – CPython 3.13.15.

1. S38-spezifisch: **6 Tests**, 6 bestanden, 0 Fehler, 0 Fehlschläge,
   0 Skips, 0,431 s.
2. Gesamtgate Lauf 1: **529 Tests**, 529 bestanden, 0 Fehler, 0 Fehlschläge,
   0 Skips, 6,260 s.
3. Gesamtgate Lauf 2: **529 Tests**, 529 bestanden, 0 Fehler, 0 Fehlschläge,
   0 Skips, 6,237 s.

Testbefehl:

```bash
PYTHONDONTWRITEBYTECODE=1 \
/private/tmp/sammlr-s32-py313-venv/bin/python \
-m unittest discover -s tests -p "test_s*.py" -v
```

Der erste Lauf selbst war vollständig grün; nur der nachgelagerte Shell-
Zeitmesser verwendete anschließend versehentlich den in zsh reservierten Namen
`status`. Der zweite Lauf und seine Exitcode-Erfassung waren sauber. Es wurden
keine übersprungenen Tests als grün deklariert.

## Warnungen und offene Risiken

- S35-Performanceblocker bleiben unverändert und verhindern die Public Beta.
- Im finalen zweiten Gate wurden 2.148 `ResourceWarning`-Logzeilen aus älteren
  SQLite-Testpfaden ausgegeben.
- Zwei historisch dokumentierte `SyntaxWarning`-Hinweise wurden bei der finalen
  Syntaxinventur als ungültige `\d`-Escape-Sequenzen in `App/webapp.py` bei
  Zeile 5453 und 5458 reproduziert und bleiben offen.
- Eine nicht geladene historische Datei unter `App/Archive` besitzt einen
  vorbestehenden `IndentationError` in Zeile 941. Alle produktiven Pythonquellen
  bestehen die Syntaxprüfung; das Archiv wurde scopegemäß nicht bereinigt.
- Funktionale Compliance-Texte benötigen eine juristische Endfassung.
- Die historische Hashabweichung der lokalen Datenbank bleibt ungeklärt; die
  aktuelle Datei ist integral und wurde durch S38 nicht geändert.
- Architektur-/UI-Schuld und vertagte Product-Bible-Funktionen sind vollständig
  in `release/RC1-known-issues.md` erfasst.

## Release Readiness

| Entscheidung | Status |
|---|---|
| Migrations- und Upgradevertrag | bereit |
| Security-/HTTP-/Integritätsvertrag | bereit |
| Produktionsimport, Health, Login und Assets | bereit |
| Kernfunktionen/Regression | bereit |
| Interner technischer RC1 | **hergestellt** |
| Public Beta | **nicht freigegeben** |

Die nächste zulässige Aktivität ist die Product-Owner-/Engineering-Besprechung
über die dokumentierten Blocker und offenen Punkte. S38 startet weder S39 noch
eine Quality-, UI- oder Performance-Woche.

## Scope-Bestätigung

- Ausschließlich S38 wurde bearbeitet.
- Keine Anwendungscode- oder Fachlogikänderung.
- Keine Datenbank- oder Migrationsänderung.
- Keine echte Entwicklungs-, Fixture-, Backup- oder Produktionsdatenbank wurde
  migriert oder verändert.
- Keine Performanceoptimierung und kein Refactoring.
- Kein Commit und kein Push.
