# INTEGRATION-00 – Audit

Stand 2026-10-02. Analyse/Inventur/Planung abgeschlossen. Keine Implementierung, kein Produktivpatch, keine Migration, kein Appstart. Kein git add, Commit, Push oder Deploy.

## Ergebnis und Reichweite

Trade-v2 ist als UX- und Domainreferenz integrationsfähig. Es ist weiterhin eine isolierte GET-/Fixture-/Session-Preview und keine persistente, autorisierte Tradeengine. Vor Phase01 ist der lokal geprüfte, weitgehend unversionierte Stand reproduzierbar abzugrenzen. Kein weiterer Domain-STOP erforderlich. Später betroffen sind geschützte Shell/Navigation, reale Discovery-/Inventarprojektionen, serverseitige Validatoren, neue versionierte Tradecommands, gemeinsame Availability, private Adresse, gerichteter Versand/Empfang, Probleme, Rating und Notifications.

DB-Arbeit: neue Vertrags-/Paketversion, beidseitige Reservierungen/Incoming Needs, operative 3/3-Kapazität getrennt von Requeststate, Pack-/Amendmentzustimmung, Adressfreigabe, Q2-kompatible Exactly-once-Buchung, versionierte Bewertung, Idempotenz/Events. Lokales Schema20 und vorhandene noch nicht angewendete Migration21 sind vor produktiven Writes mit tatsächlichem Deployment abzugleichen. Konfiguriertes produktives Ziel `/var/data/sammlr.db`; kein Remotezugriff und keine Behauptung über dort angewendete Migrationen.

## Ausgeführte Prüfungen

- Git branch/HEAD/log/status/Indexinventur/diff-numstat lesend erfasst; Vorherstatus vor Erzeugung der Artefakte gesichert.
- Quellcode statisch gelesen, Python-AST für Funktionen/Routes/Registrierungen ausgewertet, Imports/Queryparameter und tatsächliche Serviceguards untersucht. Alle 51 Trade-v2-Dateien einzeln klassifiziert.
- Produktive Konfiguration und lokale SQLite-Schemametadaten per `mode=ro&immutable=1` gelesen; keine Nutzerdatenzeilen gelesen, keine SQL-Mutation. schema_migrations ist ausschließlich technisches Ledger.
- Vertrags-/Auditquellen mit Hashes und Kapiteln erfasst, zwölf scoped Konflikte/Integrationsgrenzen dokumentiert, 27 Konzepte in Source-of-Truth-Matrix abgebildet.
- Neue JSONs syntaktisch validiert; Trade-v2-Pythonquellen per AST ohne Import geprüft. Bestehende Dateien per SHA256 gegen Vorhermanifest geprüft, Gitstatus und Indexhash verglichen.
- Keine Runtime-, Browser- oder Regressionstests ausgeführt: sie wären in diesem Auftrag kein Nachweis neuer Funktionalität und könnten bestehende DB-/Artefaktdateien schreiben. Historische TRADE-Audits werden ausdrücklich nicht als hier erneut bestandene Tests ausgegeben. Die erforderlichen zukünftigen Tests stehen je Integrationsphase.

## Neue Dateien

1. `docs/TRADE_V2_INTEGRATION_MAP.md`
2. `docs/TRADE_V2_SOURCE_OF_TRUTH_MATRIX.md`
3. `docs/TRADE_V2_INTEGRATION_PLAN.md`
4. `docs/TRADE_V2_INTEGRATION_00_AUDIT.md`
5. `tests/research/artifacts/integration-00/repository-state.json`
6. `tests/research/artifacts/integration-00/relevant-files.json`
7. `tests/research/artifacts/integration-00/route-map.json`
8. `tests/research/artifacts/integration-00/persistence-map.json`
9. `tests/research/artifacts/integration-00/conflict-map.json`
10. `tests/research/artifacts/integration-00/protected-hashes.json`

## Schutzprüfung

Der abschließende maschinenlesbare Vorher-/Nachhernachweis steht in protected-hashes.json und repository-state.json: vollständiges Vorhermanifest, eventuelle Abweichungen, Indexvergleich und ausschließlich erlaubte neue Statuszeilen. Bestehender schmutziger Arbeitsbaum bleibt erhalten; kein Restore oder Reparaturversuch. Keine bestehende Datei wurde durch INTEGRATION-00 verändert.
