# LIFECYCLE-06 — Versand

Abschluss der Implementierung am 08.10.2026. Keine produktive Aktivierung oder Migration. Die operative Freigabe bleibt gemäß Implementierungsplan an den sicheren Empfangspfad aus LIFECYCLE-07 gebunden.

## Verhalten

- Bewusste zweistufige Versandbestätigung nach beidseitiger Adressfreigabe; signierte, nutzer- und revisionsgebundene Formulare mit CSRF-Schutz.
- Eigener physischer Abgang und Verbrauch der genauen Reservierung in einer atomaren Transaktion. Wiederholungen und parallele Bestätigungen buchen nicht doppelt.
- Beide Versandrichtungen unabhängig; Empfangsbedarf bleibt gebunden, kein Zugang oder automatischer Gesamtabschluss.
- Versandfrist 72 Stunden ab gemeinsamer Adressfreigabe, deduplizierte Überfälligkeitsereignisse ohne automatische Rücknahme.
- Unveränderliche Versandbeobachtung, Sperre normaler Stornierung/Vertragsänderung nach Versand. Rückmigration bei vorhandenen Versanddaten wird verweigert.
- Interner Abgangspfad für künftigen vollständigen Empfangsnachweis vorbereitet; Teil-Empfang und Reconciliation bleiben Aufgabe von LIFECYCLE-07.

## Fertiggestellte Restarbeiten

Falschen Zugriff auf `StickerAvailabilitySnapshotDTO.quantity` durch das tatsächliche physische Bestandsfeld `physical` ersetzt. Den Reduktions-Test auf den bestehenden Command `reduction_approve` samt Proposal-ID korrigiert. HTTP-Tests für die beiden Bestätigungsschritte, Wiederholung, Fremdzugriff, manipulierte Tokens und CSRF ergänzt; Browserablauf für Versand ergänzt.

## Prüfung

Isolierte Quellkopie mit synthetischen Daten unter `/private/tmp/lifecycle06/candidate-f0avtm8i`. SQLite-Zugriffe des Release-Laufs außerhalb `/private/tmp` durch Audit-Hook gesperrt.

- Release-Gate: **1.584 Tests erfolgreich**, keine Fehler, keine Skips. 12 bereits bestehende Ausschlüsse gemäß `docs/R5_TEST_CONTRACT.json`, keine neuen Ausschlüsse.
- Versandtests umfassen exakte Mengen, Doppelklick/Retry, mehrere Verbindungen, konkurrierende Bestandsänderung, stale Adresse/Reduktion, Transaktionsrollback bei Bestands-/Notificationfehlern und Migration vorwärts/rückwärts.
- Browser: gemeinsame Adressfreigabe, beide Versandbestätigungen, Fremdzugriff abgewiesen; Ansichten und Bestätigung bei 375/390/430/1280 px ohne horizontalen Overflow oder JavaScript-Fehler. Mobile Bestätigungsansicht zusätzlich visuell geprüft.
- Alle 16 geschützten Datenbanken gegenüber vorhandener Startbaseline SHA-256-identisch.
- `git diff --check` erfolgreich.

Nachweise: `/private/tmp/lifecycle06/release-results.json`, `release.log`, `browser.log`, `browser/results.json`, `browser/*.png`, `db-start.json`. Browser-Reproduktion: `tests/research/check_lifecycle06.py` in einer isolierten synthetischen Kopie ausführen.

## Formaler Git-Abschluss

Beauftragter Abschluss am 08.10.2026 auf `feature/wm-special-trophies`, Upstream `origin/feature/wm-special-trophies`, Remote `https://github.com/sammlr/sammlr.git`.

- Lokaler HEAD und unabhängig per `git ls-remote` geprüfter Remote-HEAD vor dem Commit: LIFECYCLE-05-Savepoint `2ea8b3ce183e403567197083f5e6c4eb4dc447b7`.
- Alle getrackten Implementierungs-/Testquellen und acht neuen Implementierungs-/Testdateien stimmen bytegenau mit dem erfolgreichen isolierten Testkandidaten überein. Die dort synthetisch erzeugte Referenz-DB ist erwartungsgemäß verschieden und gehört nicht zum Commit. Der Audit ist die einzige nachträgliche Dokumentationsergänzung.
- 25 geänderte getrackte Dateien gehören ausschließlich zur Versandintegration sowie den Erwartungen für Migration 28 und den neuen Notification-Typ. Neun neue LIFECYCLE-06-Dateien einschließlich dieses Audits; insgesamt 34 Dateien im vorgesehenen Commit.
- Die 3.194 bereits in der L06-Startbaseline vorhandenen ungetrackten lokalen Dateien bleiben vollständig außerhalb des Index. Keine unerklärten neuen oder entfernten Dateien gegenüber dieser Baseline.
- Alle 16 geschützten DBs erneut SHA-256-identisch zur autorisierten Baseline. Index vor dem Staging leer.
- Keine relevante Änderung seit dem erfolgreichen Release-Gate; daher keine Wiederholung erforderlich. Teststand weiterhin 1.584 erfolgreiche Tests und bestandene Browserprüfungen.

Commit-Titel: `feat: add lifecycle v1 shipping`. Commit-ID, Push-Ergebnis, unabhängiger finaler Remotevergleich und Abschlusskontrollen werden nach der Ausführung im Abschlussbericht ausgewiesen. Prüfmanifest unter `/private/tmp/lifecycle06/formal-manifest.json`.

Kein Deploy und keine reale Migration. LIFECYCLE-07 wurde nicht begonnen.
