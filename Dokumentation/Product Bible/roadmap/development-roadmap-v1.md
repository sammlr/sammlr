sa# Sammlr Development Roadmap V1

| Metadatum | Wert |
| --- | --- |
| Status | Verbindliche Development Roadmap V1 |
| Stand | 2026-07-28 |
| Ziel | Stabiler, öffentlich testbarer Sammlr-Produktstand |
| Grundlage | Product Bible und Current-State Gap Analysis |
| Grundsatz | Sammlr ersetzt keine Sammler. Sammlr unterstützt Sammler. |

## 1. Executive Summary

Diese Roadmap ist die zentrale Antwort auf „Was bauen wir als Nächstes?“. Sie entwickelt den vorhandenen Sammlr-Kern kontrolliert weiter und ersetzt ihn nicht durch einen Greenfield-Neustart.

Die blockierende Hauptkette lautet:

`Tests → Inventory → Reservierung → Trade Lifecycle → Smart Trader → Home/Notifications → Profil/Community`

Navigation kann nach dem Referenzschutz teilweise parallel entstehen. Security läuft von Beginn an als Querschnitt und wird nicht bis zur Public-Beta-Phase aufgeschoben.

Die Roadmap besteht aus zehn Phasen und 38 bewusst kleinen Sprints. Aufwand wird relativ als klein, mittel, groß oder sehr groß angegeben. Es gibt keine Kalender- oder Stundenversprechen.

### Verbindlich zu schützen

- Stickerwall,
- Papier-Stickerliste,
- Album- und Sticker-Codeauflösung,
- direkte Mengenpflege,
- manuelle Dealzusammenstellung,
- beidseitig bestätigter Tradeabschluss,
- Trophy-Definitionen und Unlock-Historie,
- Statistik- und Profilbereiche,
- Notification-Erzeugung.

## 2. Referenzen und Geltungsrang

1. Produktentscheidungen: [Sammlr Product Bible](../README.md)
2. Technischer Ist-Zustand: [Current-State Gap Analysis](current-state-gap-analysis.md)
3. Umsetzungsreihenfolge: dieses Dokument

Die Roadmap priorisiert und zerlegt die Product Bible, ändert aber keine ihrer Kernentscheidungen. Offene Produktfragen bleiben Entscheidungs-Gates.

## 3. Roadmap-Prinzipien

1. Kein Greenfield-Neustart.
2. Erst Regression-Schutz, dann struktureller Umbau.
3. Ein Sprint verändert möglichst nur eine fachliche Achse.
4. Dateninvarianten kommen vor attraktiven neuen Screens.
5. Funktionierende Pfade werden hinter Tests gestellt und schrittweise extrahiert.
6. UX muss jederzeit verständlich sein; UI darf vor Design Patches schlicht bleiben.
7. Neue UI ist mobile-first und verwendet die Sammlr-Grundsprache.
8. UI, UX, CI und Design System werden begrifflich getrennt behandelt.
9. Security ist ein Querschnitt.
10. Future-Themen werden nicht in P0/P1 eingeschmuggelt.

## 4. Zielversion der nächsten öffentlichen Sammlr-Stufe

Die Zielversion „Sammlr Public Beta V1“ umfasst:

- geschützte und getestete Bestands- und Trade-Kernflows,
- dreiteilige Hauptnavigation,
- getrennte Home- und Sammlungsbereiche,
- konsistente verfügbare, freie, reservierte und unterwegs befindliche Mengen,
- nachvollziehbaren Trade Lifecycle mit Versand und Empfang je Seite,
- nutzbaren Smart Trader 2.0 plus erhaltenem manuellen Tausch,
- adressierbare Notifications und operative Home-Aufgaben,
- eigenes und fremdes Profil, grundlegende Privacy, Freundschaften, Blockieren und Bewertungen,
- zwei Design Patches,
- Public-Beta-taugliche Security, Migrationen, Betrieb und Recovery.

Nicht Teil dieser Zielversion sind die im Future Backlog genannten Advanced-Collector-, Commerce-, Scanner-, Offline- oder Versandplattform-Themen.

## 5. Kennzeichnungen

Prioritäten:

- **P0** – zwingend und blockierend
- **P1** – wichtig für die nächste Produktstufe
- **P2** – sinnvoll nach dem Kern
- **P3** – spätere Verbesserung
- **FUTURE** – nicht Teil der nächsten Produktversion

Arbeitsarten:

- **ARCH** Architekturarbeit
- **USER** Nutzerfunktion
- **SEC** Security
- **UX** Nutzerführung
- **UI** sichtbare Oberfläche
- **CI** Markenidentität
- **DOC** Dokumentation
- **TEST** Tests

## 6. Phasenübersicht

| Phase | Sprints | Ziel | Primär | Ergebnis |
| --- | --- | --- | --- | --- |
| 0 – Kern absichern | S00–S03 | Referenz und Regression-Schutz | P0 · TEST/ARCH | M0 |
| 1 – Navigation & Grundgerüst | S04–S07 | 3er-Navigation und globale Zugänge | P0/P1 · USER/UX/UI | M1 |
| 2 – Inventory-Fundament | S08–S12 | zentrale Bestandswahrheit | P0 · ARCH/TEST | M2 |
| 3 – Trade Lifecycle 2.0 | S13–S18 | Reservierung bis Empfang | P0/P1 · ARCH/USER | M3 |
| 4 – Smart Trader 2.0 | S19–S22 | konfliktfreie, erklärbare Matches | P1 · ARCH/USER | M4 |
| 5 – Home & Notifications | S23–S25 | operative Startseite | P1 · USER/UX | M5 |
| 6 – Profil & Community | S26–S29 | Sammlerseiten und Vertrauen | P1/P2 · USER/SEC | M6 |
| 7 – Design Patch 1 | S30–S31 | visuelle Systematisierung | P1 · UI/CI/UX | M7 |
| 8 – Betrieb, Security, Beta-Reife | S32–S35 | sicherer öffentlicher Betrieb | P0/P1 · SEC/ARCH | M8-Gate |
| 9 – Design Patch 2 & Public Beta | S36–S37 | finale Beta-Freigabe | P1 · UI/CI/SEC | M8 |

## 7. Detaillierte Sprintliste

### Phase 0 – Bestehenden Kern absichern

#### S00 – Referenzstand und Testdatenstrategie

- **Priorität/Arten:** P0 · ARCH, DOC, TEST
- **Ziel:** Reproduzierbaren, datenschutzgerechten Ausgangspunkt schaffen.
- **Fachlicher Nutzen:** Der reale Sammlr-Kern kann später beweisbar erhalten werden.
- **Umfang:** aktiven Einstieg dokumentieren; Referenz-Commit/-Tag-Konvention; anonymisierte SQLite-Fixture mit mehreren Nutzern, Alben, Mengen und einem vollständigen Trade; Datenherkunft dokumentieren.
- **Nicht enthalten:** Produktivdaten kopieren, Schema ändern, Features bauen.
- **Abhängigkeiten:** keine.
- **Risiken:** Testfixture bildet Sonderfälle unvollständig ab.
- **Zu schützen:** bestehende Datenbank und realer abgeschlossener Trade.
- **Akzeptanzkriterien:** Fixture ist ohne personenbezogene Daten reproduzierbar; Referenzstand und Startbefehl sind dokumentiert.
- **Definition of Done:** frischer Testlauf kann ausschließlich mit Fixture vorbereitet werden; keine Produktivdatei wird verändert.
- **Tests:** Fixture-Öffnung, Tabellen-/Mindestdatensätze, deterministische IDs.
- **Dokumentation:** technische Testdaten- und Referenznotiz.
- **Commit-Abschluss:** `test: establish anonymized sammlr reference fixture`
- **Größe:** klein bis mittel, 1–2 Entwicklungsabende.

#### S01 – Bestands-Regressionstests

- **Priorität/Arten:** P0 · TEST, ARCH
- **Ziel:** Mengen-, Doppelte- und Fortschrittslogik schützen.
- **Fachlicher Nutzen:** Stickerpflege bleibt bei späterer Zentralisierung stabil.
- **Umfang:** Tests für Add/Remove, Inline-`−/+`, Nullgrenze, Doppelte=`max(quantity-1,0)`, Filter, Fortschritt und Undo.
- **Nicht enthalten:** Inventory-Service oder Schemaänderung.
- **Abhängigkeiten:** S00.
- **Risiken:** aktuelle globale Flask-/DB-Zustände erschweren Isolation.
- **Zu schützen:** Stickerwall, Mengenregler, Codeauflösung.
- **Akzeptanzkriterien:** Kernfälle und Randfälle laufen deterministisch gegen Test-DB.
- **Definition of Done:** Tests schlagen bei absichtlicher Mengenabweichung fehl und im Referenzzustand grün durch.
- **Tests:** Route-, Service- und DB-Assertions für alle genannten Schreibwege.
- **Dokumentation:** Testfallmatrix Sammlung.
- **Commit-Abschluss:** `test: lock inventory quantity behavior`
- **Größe:** mittel, 2–3 Entwicklungsabende.

#### S02 – Papierlisten- und Tradeflow-Regressionstests

- **Priorität/Arten:** P0 · TEST, ARCH
- **Ziel:** Den real bewährten Transfer- und Tradeabschluss schützen.
- **Fachlicher Nutzen:** Kontrollierter Umbau ohne Verlust des ersten funktionierenden Kernflows.
- **Umfang:** Papierlistentransfer; Anfrage; Annahme; Ablehnung; erste und zweite Bestätigung; beidseitige Bestandsbuchung; completed/failed; Historie.
- **Nicht enthalten:** neue State Machine, Reservierung oder Versandstatus.
- **Abhängigkeiten:** S00–S01.
- **Risiken:** alte Statuswerte wie `cancelled` müssen als Fixture-Fall getrennt bleiben.
- **Zu schützen:** manuelle Dealpakete und beidseitiger Abschluss.
- **Akzeptanzkriterien:** jede Zustandsänderung und Bestandsseite ist assertiert; Doppelbuchung wird erkannt.
- **Definition of Done:** kompletter Referenztrade ist automatisiert reproduzierbar.
- **Tests:** Happy Path, Ablehnung, Fehlschlag, wiederholte Bestätigung, unberechtigter Zugriff.
- **Dokumentation:** Ist-State-Diagramm und Regression-Matrix.
- **Commit-Abschluss:** `test: protect proven trade completion flow`
- **Größe:** mittel bis groß, 3–4 Entwicklungsabende.

#### S03 – Nebenwirkungen, Security-Baseline und CI-Testgate

- **Priorität/Arten:** P0 · TEST, SEC, ARCH
- **Ziel:** Trophäen, Notifications und minimale Sicherheitsregeln in das Testgate aufnehmen.
- **Fachlicher Nutzen:** Unsichtbare Regressionen werden vor jedem Fachumbau erkannt.
- **Umfang:** Trophy-Unlocks, Popup-Queue, Notification-Erzeugung, Auth-Zugriff; automatischer Testbefehl; dokumentiertes Pflichtgate vor Merge.
- **Nicht enthalten:** Passwortmigration, Glocken-UI, vollständige CI-Plattform.
- **Abhängigkeiten:** S00–S02.
- **Risiken:** Session- und Zeitabhängigkeiten.
- **Zu schützen:** Trophy-Historie und Notification-Schreibadapter.
- **Akzeptanzkriterien:** Nebenwirkungen sind genau einmal nachweisbar; anonyme Fachrouten bleiben gesperrt.
- **Definition of Done:** ein einziger dokumentierter Befehl prüft Phase-0-Kern.
- **Tests:** Trophy/Notification-Deduplizierung, Loginpflicht, Testdatenisolation.
- **Dokumentation:** Testgate und bekannte, bewusst noch offene Security-Gaps.
- **Commit-Abschluss:** `test: add side-effect and security baseline gate`
- **Größe:** mittel, 2–3 Entwicklungsabende.

### Phase 1 – Navigation und Produktgrundgerüst

#### S04 – Home- und Sammlungsrouten trennen

- **Priorität/Arten:** P0 · ARCH, USER, UX
- **Ziel:** Stabile fachliche Besitzer für Home und Sammlung schaffen.
- **Fachlicher Nutzen:** Nutzer starten auf Home, ohne die vorhandene Sammlr-Zentrale zu verlieren.
- **Umfang:** bestehende Zentrale unter stabile Sammlungsroute verschieben; `/` als ehrlicher Home-Grundzustand; Weiterleitungen und interne Links.
- **Nicht enthalten:** vollständige Home-Aufgaben, Feed oder News.
- **Abhängigkeiten:** M0.
- **Risiken:** viele Links zeigen aktuell auf `/`.
- **Zu schützen:** Albumkarten, Favorit, Vitrine, Album hinzufügen.
- **Akzeptanzkriterien:** Sammlung vollständig erreichbar; `/` zeigt keine erfundenen Lifecycle-Daten.
- **Definition of Done:** alte Kernwege funktionieren über neue Route und Kompatibilitätsweiterleitungen.
- **Tests:** Route-, Login-, Link- und Rückwegtests.
- **Dokumentation:** Routenkarte und Begriffsklärung Home/Sammlr-Zentrale.
- **Commit-Abschluss:** `feat: separate home and collection routes`
- **Größe:** mittel, 2–3 Entwicklungsabende.

#### S05 – Dreiteilige Bottom-Navigation

- **Priorität/Arten:** P0 · USER, UX, UI
- **Ziel:** `[ Sammlung ] [ sammlr./Home ] [ Tauschen ]` aktivieren.
- **Fachlicher Nutzen:** Hauptnavigation folgt der mentalen Produktlogik.
- **Umfang:** fünf Punkte auf drei reduzieren; aktive Zustände; bestehende Zielseiten hierarchisch erhalten; mobile Grundfunktion.
- **Nicht enthalten:** finale Icons, Animationen oder Design Patch.
- **Abhängigkeiten:** S04.
- **Risiken:** CSS besitzt historische Bottom-Nav-Überschreibungen.
- **Zu schützen:** Profil-, Favorit-, Statistik- und Trophy-Routen.
- **Akzeptanzkriterien:** alle drei Punkte führen korrekt; entfernte Punkte bleiben über Fachbereiche erreichbar.
- **Definition of Done:** Navigation funktioniert auf zentralen Seiten und kleinen Viewports.
- **Tests:** aktive Zustände, Linkziele, responsive Smoke-Tests.
- **Dokumentation:** Navigationsmatrix Ist/Soll aktualisieren.
- **Commit-Abschluss:** `feat: activate three-area primary navigation`
- **Größe:** mittel, 2–3 Entwicklungsabende.

#### S06 – Globaler Header mit Avatar und Glocken-Shell

- **Priorität/Arten:** P1 · USER, UX, UI
- **Ziel:** Globale Zugänge zu Profil und Notifications bereitstellen.
- **Fachlicher Nutzen:** Untergeordnete Bereiche sind ohne zusätzliche Haupttabs erreichbar.
- **Umfang:** gemeinsame Headerstruktur; Avatar zu eigenem Profil; Glocke zu ehrlichem Notification-Leer-/Bestandszustand; kompakte Unterseitenvariante.
- **Nicht enthalten:** Badge-Logik, vollständige Notification-Historie, finales Headerdesign.
- **Abhängigkeiten:** S04–S05.
- **Risiken:** inline gerenderte Seitentemplates nutzen Header uneinheitlich.
- **Zu schützen:** bestehende Seitentitel und Zurückwege.
- **Akzeptanzkriterien:** Avatar/Glocke global auf Hauptseiten; tiefe Workflows behalten Fokus.
- **Definition of Done:** ein wiederverwendbarer Headerpfad ersetzt keine Fachseite.
- **Tests:** Zielrouten, Login, mobile Darstellung, fehlende Profilbilddaten.
- **Dokumentation:** Headerhierarchie.
- **Commit-Abschluss:** `feat: add global profile and notification access`
- **Größe:** mittel, 2–3 Entwicklungsabende.

#### S07 – Deep-Link- und Rückwegkontext

- **Priorität/Arten:** P1 · ARCH, UX, TEST
- **Ziel:** Dasselbe Objekt aus verschiedenen Ursprüngen sinnvoll öffnen und verlassen.
- **Fachlicher Nutzen:** Weniger unnötige Zwischenschritte und keine doppelten Fachansichten.
- **Umfang:** erlaubte Origin-Kontexte; konkrete Trade-/Album-Links; sicherer Fallback; Rückweg aus Deal zu Home oder Meine Deals.
- **Nicht enthalten:** neue Notification-Typen oder universelles Routingframework.
- **Abhängigkeiten:** S04–S06.
- **Risiken:** manipulierbare Return-URLs und Open Redirects.
- **Zu schützen:** direkte `/trades/<id>`-Ansicht und Berechtigungsprüfung.
- **Akzeptanzkriterien:** mindestens Home- und Tradezentrale-Ursprung liefern korrekten Rückweg; externe Ziele werden abgewiesen.
- **Definition of Done:** Kontext ist getestet, optional und sicher.
- **Tests:** gültige/ungültige Origins, Fallback, Objektberechtigung.
- **Dokumentation:** Deep-Link-Konvention.
- **Commit-Abschluss:** `feat: preserve safe navigation origin context`
- **Größe:** klein bis mittel, 1–2 Entwicklungsabende.

### Phase 2 – Inventory- und Bestandsfundament

#### S08 – Inventory-Invarianten und Zielmodell festschreiben

- **Priorität/Arten:** P0 · ARCH, DOC, TEST
- **Ziel:** Eindeutige Begriffe und mathematische Regeln vor Codeumbau.
- **Fachlicher Nutzen:** Alle Fachbereiche rechnen mit derselben Bestandswahrheit.
- **Umfang:** physisch, zugeordnet, frei, reserviert, ausgehend, unterwegs eingehend; Gleichungen und Fehlerfälle; Kompatibilitätsabbildung des heutigen Einzelexemplars.
- **Nicht enthalten:** vollständige Mehrfachalbum-UI oder Migration.
- **Abhängigkeiten:** M0; Product Bible Sammlung.
- **Risiken:** Albuminstanz und freier Pool werden zu früh übermodelliert.
- **Zu schützen:** heutiges `quantity`-Verhalten.
- **Akzeptanzkriterien:** jede Menge hat Quelle, Einheit und Invariante; keine Doppelzählung.
- **Definition of Done:** Decision Record oder technische Spezifikation ist freigegeben.
- **Tests:** tabellarische Beispieldaten und Invarianten als ausführbare Contract-Tests.
- **Dokumentation:** Inventory Contract V1.
- **Commit-Abschluss:** `docs: define inventory invariants v1`
- **Größe:** mittel, 2 Entwicklungsabende plus Product-Owner-Review.

#### S09 – Zentraler Inventory-Lesedienst

- **Priorität/Arten:** P0 · ARCH, TEST
- **Ziel:** Eine zentrale Abfrage für physisch, doppelt und verfügbar.
- **Fachlicher Nutzen:** Wall, Matching und Trades zeigen konsistente Mengen.
- **Umfang:** read-only Inventory-Service auf aktuellem Schema; zentrale DTOs; schrittweise Nutzung in Fortschritt, Liste und Matching.
- **Nicht enthalten:** Schreibpfade, Reservierungstabelle, UI-Umbau.
- **Abhängigkeiten:** S08.
- **Risiken:** Big-Bang-Ersetzung aller Queries.
- **Zu schützen:** Wall-/Listenwerte und Matchingresultate.
- **Akzeptanzkriterien:** alter und neuer Lesepfad liefern auf Fixture identische Istwerte.
- **Definition of Done:** zentrale API wird von mindestens Sammlung und Matching verwendet.
- **Tests:** Golden-Master-Vergleich, Mengenrandfälle.
- **Dokumentation:** Servicevertrag.
- **Commit-Abschluss:** `refactor: centralize inventory read model`
- **Größe:** mittel bis groß, 3–4 Entwicklungsabende.

#### S10 – Bestandsschreibpfade konsolidieren

- **Priorität/Arten:** P0 · ARCH, TEST
- **Ziel:** Alle Mengenänderungen über einen validierten Dienst führen.
- **Fachlicher Nutzen:** Manuelle Pflege, Papierliste und Tradeabschluss verhalten sich gleich.
- **Umfang:** Add/Remove, Inline, Batch, Papiertransfer und Undo schrittweise auf Inventory-Command-Service; Trophy/Notification-Hooks erhalten.
- **Nicht enthalten:** Reservierungsdurchsetzung oder neues Schema.
- **Abhängigkeiten:** S01, S09.
- **Risiken:** versteckte Seiteneffekte und Session-Undo.
- **Zu schützen:** alle Phase-0-Regressionstests.
- **Akzeptanzkriterien:** keine direkte Mengenmutation außerhalb definierter Adapter; Verhalten unverändert.
- **Definition of Done:** Suche nach alten Schreibmustern ist dokumentiert und begründet leer beziehungsweise bewusst ausgenommen.
- **Tests:** gesamte Phase-0-Suite plus parallele/ungültige Commands.
- **Dokumentation:** Schreibpfad-Inventar aktualisieren.
- **Commit-Abschluss:** `refactor: route inventory writes through one service`
- **Größe:** groß, 4–6 Entwicklungsabende, bei Bedarf in mechanische Teilcommits.

#### S11 – Verfügbare und reservierbare Menge vorbereiten

- **Priorität/Arten:** P0 · ARCH, TEST
- **Ziel:** `available = physical - assigned - reserved/bound` zentral ausdrücken.
- **Fachlicher Nutzen:** Basis gegen Doppelvergabe.
- **Umfang:** Availability-API und Erklärdaten; heutige Einzelexemplar-Zuordnung kompatibel abbilden; Matching auf verfügbare statt rohe Doppelte vorbereiten.
- **Nicht enthalten:** Reservierung bei Annahme oder Mehrfachalbum-Poolmanagement.
- **Abhängigkeiten:** S08–S10.
- **Risiken:** falsche Interpretation der impliziten ersten Albumkopie.
- **Zu schützen:** bisherige Partnerergebnisse ohne Reservierungen.
- **Akzeptanzkriterien:** Availability ist für jeden Sticker nachvollziehbar und nie negativ.
- **Definition of Done:** Collection und Matching verwenden dieselbe Berechnung.
- **Tests:** 0/1/n Mengen, gebundene erste Kopie, erklärbare Resultate.
- **Dokumentation:** Availability-Beispiele.
- **Commit-Abschluss:** `feat: define central available sticker quantity`
- **Größe:** mittel, 2–3 Entwicklungsabende.

#### S12 – Schutz manueller Mengenänderungen vorbereiten

- **Priorität/Arten:** P0 · ARCH, UX, TEST
- **Ziel:** Commands können verbindlich gebundene Mindestmengen respektieren.
- **Fachlicher Nutzen:** Menschliche Eingabe bleibt führend, zerstört aber keinen Deal unbemerkt.
- **Umfang:** Inventory-Guard-Vertrag; Warn-/Blockierfehler; UI-neutraler Fehlercode; noch ohne echte Reservierungsquelle mit Test-Doubles.
- **Nicht enthalten:** finale Warnungs-UI oder Reservierungserzeugung.
- **Abhängigkeiten:** S10–S11.
- **Risiken:** Nutzer wird unnötig blockiert.
- **Zu schützen:** schnelle Einzel- und Batchpflege.
- **Akzeptanzkriterien:** ungebundene Änderung bleibt schnell; gebundene Untergrenze wird verhindert und erklärt.
- **Definition of Done:** Guard ist servicezentriert und durch UI-Adapter darstellbar.
- **Tests:** exakt verfügbare, zu niedrige und idempotente Änderungen.
- **Dokumentation:** Fehler- und UX-Vertrag.
- **Commit-Abschluss:** `feat: guard inventory commands against bound stock`
- **Größe:** klein bis mittel, 1–2 Entwicklungsabende.

### Phase 3 – Trade Lifecycle 2.0

#### S13 – Versionierte Migrationen und Lifecycle-Grundschema

- **Priorität/Arten:** P0 · ARCH, SEC, TEST
- **Ziel:** Kontrollierte Schemaentwicklung statt Startup-ALTERs.
- **Fachlicher Nutzen:** Bestehende Trades bleiben sicher, neue Zustände werden ausdrückbar.
- **Umfang:** Migrationsmechanismus; Trade/Request-Kompatibilitätsmodell; Positionen, Ereignisse, Zeitstempel und Reservierungsgrundlage; Backout-Plan.
- **Nicht enthalten:** UI oder vollständige Migration aller Legacy-Sonderwerte.
- **Abhängigkeiten:** M0, S08–S12.
- **Risiken:** reale Tradehistorie beschädigen.
- **Zu schützen:** bestehender `completed`-Trade, JSON-Pakete und Historie.
- **Akzeptanzkriterien:** Migration vorwärts/rückwärts auf Kopie; Altbestand lesbar; keine Produktivmutation im Test.
- **Definition of Done:** versionierte Migration und Kompatibilitätstests grün.
- **Tests:** leere DB, Fixture, wiederholter Lauf, Rollback.
- **Dokumentation:** Schema- und Migrationsentscheidung.
- **Commit-Abschluss:** `feat: introduce versioned trade lifecycle schema`
- **Größe:** groß, 4–6 Entwicklungsabende.

#### S14 – Annahme erzeugt verbindliche Reservierungen

- **Priorität/Arten:** P0 · ARCH, USER, TEST
- **Ziel:** Dealannahme reserviert alle ausgehenden Positionen atomar.
- **Fachlicher Nutzen:** Kein Sticker wird mehrfach verbindlich vergeben.
- **Umfang:** Reservierungsservice; Availability-Recheck in Transaktion; Erfolg/konflikthafte Annahme; Freigabe bei zulässigem Ende.
- **Nicht enthalten:** Versand oder dynamische Paketanpassung.
- **Abhängigkeiten:** S11–S13.
- **Risiken:** Race Conditions und Legacy-Anfragen.
- **Zu schützen:** bestehende Annahme-Notification und manuelle Pakete.
- **Akzeptanzkriterien:** Annahme ist vollständig oder ohne Teilreservierung abgelehnt; Matching sieht reduzierte Menge.
- **Definition of Done:** paralleler Annahmetest verhindert Doppelreservierung.
- **Tests:** Happy Path, Konkurrenz, nicht mehr verfügbar, idempotente Wiederholung.
- **Dokumentation:** Reservierungs-Lifecycle.
- **Commit-Abschluss:** `feat: reserve stickers atomically on trade acceptance`
- **Größe:** groß, 3–5 Entwicklungsabende.

#### S15 – Versandstatus je Seite und Unterwegs-Zustand

- **Priorität/Arten:** P0 · ARCH, USER, UX, TEST
- **Ziel:** Jede Seite bestätigt eigenen Versand; eingehende Positionen werden „unterwegs“.
- **Fachlicher Nutzen:** Sammlr bildet die physische Zwischenrealität ab.
- **Umfang:** Versandübergang und Zeitstempel pro Seite; ausgehende Bestandsbindung; eingehendes Transit-Readmodel; einfache Status-UI.
- **Nicht enthalten:** Tracking, Labels oder Versicherung.
- **Abhängigkeiten:** S14.
- **Risiken:** physisch/versendet/reserviert doppelt zählen.
- **Zu schützen:** konkrete Stickerlisten und Dealansicht.
- **Akzeptanzkriterien:** A und B können unabhängig versenden; Transit erhöht keinen physischen Eingang.
- **Definition of Done:** Inventory-Invarianten bleiben in allen Versandkombinationen erfüllt.
- **Tests:** A-only, B-only, beide, Wiederholung, unberechtigter Übergang.
- **Dokumentation:** State-Diagramm aktualisieren.
- **Commit-Abschluss:** `feat: track per-side shipment and transit state`
- **Größe:** groß, 3–5 Entwicklungsabende.

#### S16 – Empfang je Seite und sichere Bestandsbuchung

- **Priorität/Arten:** P0 · ARCH, USER, TEST
- **Ziel:** Eingang erst bei realem Empfang pro Seite buchen.
- **Fachlicher Nutzen:** Bestand entspricht der physischen Realität.
- **Umfang:** Empfangsübergang; per-side Buchung; Abschluss nach beiden erfolgreichen Abwicklungen; kontrollierte Wiederverwendung des alten `complete_trade`-Verhaltens.
- **Nicht enthalten:** Teilempfang oder Bewertung.
- **Abhängigkeiten:** S15.
- **Risiken:** Doppelbuchung bei Retry; Trophy-Nebenwirkungen.
- **Zu schützen:** atomarer Altabschluss und Trophy-/Notification-Verhalten.
- **Akzeptanzkriterien:** erster Empfang bucht nur diese Seite; zweiter schließt Deal; Retry ist idempotent.
- **Definition of Done:** neue und Legacy-Kompatibilitätstests grün.
- **Tests:** Reihenfolgen, Retry, Abbruch vor Empfang, Trophy/Notification genau einmal.
- **Dokumentation:** Buchungsregeln und Legacy-Mapping.
- **Commit-Abschluss:** `feat: book incoming stock on per-side receipt`
- **Größe:** groß, 4–6 Entwicklungsabende.

#### S17 – Problemfälle und Teilempfang

- **Priorität/Arten:** P1 · ARCH, USER, UX, TEST
- **Ziel:** Unvollständige, falsche, verlorene oder beschädigte Sendungen nachvollziehbar behandeln.
- **Fachlicher Nutzen:** Physische Realität gewinnt vor künstlichem Gesamtstatus.
- **Umfang:** einfacher Problemworkflow; betroffene Positionen; Teilempfang; Transitauflösung; keine automatische Schuldentscheidung.
- **Nicht enthalten:** Schiedsgericht, Supportautomation oder Versicherung.
- **Abhängigkeiten:** S15–S16; Product-Owner-Gate Problem-UX.
- **Risiken:** zu komplexe Zustandskombinationen.
- **Zu schützen:** normale schnelle Empfangsbestätigung.
- **Akzeptanzkriterien:** erhaltene Positionen buchbar, fehlende nicht; Problem bleibt historisch sichtbar.
- **Definition of Done:** Zustandsinvarianten und klare Nutzertexte für V1.
- **Tests:** 29/30, falscher Sticker, verloren, spätere Auflösung.
- **Dokumentation:** Problemfallmatrix und offene Supportgrenzen.
- **Commit-Abschluss:** `feat: support partial receipt and trade problems`
- **Größe:** groß, 4–6 Entwicklungsabende.

#### S18 – Fristen, Ereignisprotokoll und Lifecycle-Historie

- **Priorität/Arten:** P1 · ARCH, USER, UX, TEST
- **Ziel:** Jede relevante Zustandsänderung zeitlich nachvollziehbar machen.
- **Fachlicher Nutzen:** Überfälligkeit, History und spätere Notifications erhalten belastbare Daten.
- **Umfang:** Eventlog; Anfrageablauf; fünf-Werktage-Frist; überfällig statt automatisches Scheitern; Abschlusszeit; Legacy-Statusdarstellung; minimale textbasierte Systemchronologie.
- **Nicht enthalten:** vollständiger Dealchat mit Bildern oder Bewertung.
- **Abhängigkeiten:** S13–S17; Product-Owner-Gates Ablauf/Feiertage.
- **Risiken:** Zeitzonen und alte `created_at`-Semantik.
- **Zu schützen:** bestehendes Tradearchiv.
- **Akzeptanzkriterien:** Anfrage, Annahme, Versand, Empfang, Problem und Abschluss haben Ereignisse/Zeitpunkte.
- **Definition of Done:** Historie nutzt Abschluss- statt Anfragezeit, Legacy bleibt lesbar.
- **Tests:** Zeitgrenzen, Ablauf, Überfällig, Sortierung, Zeitzone.
- **Dokumentation:** Eventkatalog und Fristentscheidung.
- **Commit-Abschluss:** `feat: add trade event log deadlines and lifecycle history`
- **Größe:** groß, 4–6 Entwicklungsabende.

### Phase 4 – Smart Trader 2.0

#### S19 – Gemeinsamer Verfügbarkeits-Snapshot

- **Priorität/Arten:** P1 · ARCH, TEST
- **Ziel:** Reproduzierbare Matching-Eingabe aus Beständen, Reservierungen und Transit.
- **Fachlicher Nutzen:** Vorschläge zeigen nur wirklich nutzbare Sticker.
- **Umfang:** Snapshot pro Nutzer/Album; Version/Zeitpunkt; reservierte und unterwegs eingehende Positionen; bestehendes bilaterales Matching als Vergleich.
- **Nicht enthalten:** Ranking oder Top Matches.
- **Abhängigkeiten:** M2, S14–S18.
- **Risiken:** veraltete Snapshots und teure Abfragen.
- **Zu schützen:** `trade_candidates()`-Resultate ohne Bindungen.
- **Akzeptanzkriterien:** Snapshot erklärt jede verfügbare/fehlende Menge; gleiche Eingabe ergibt gleiches Resultat.
- **Definition of Done:** manueller Trade und neuer Matcher nutzen dieselbe Verfügbarkeitsquelle.
- **Tests:** Reservierung, Transit, Abschluss und manuelle Korrektur.
- **Dokumentation:** Snapshot-Vertrag.
- **Commit-Abschluss:** `feat: create shared trade availability snapshot`
- **Größe:** mittel bis groß, 3–4 Entwicklungsabende.

#### S20 – Marktdeckung und persönliche Tauschabdeckung

- **Priorität/Arten:** P1 · ARCH, USER, TEST
- **Ziel:** Zwei fachlich getrennte Kennzahlen korrekt berechnen.
- **Fachlicher Nutzen:** Nutzer versteht Marktpotenzial und eigenes realistisches Potenzial.
- **Umfang:** Marktabdeckung; bilaterale konfliktbereinigte persönliche Abdeckung V1; erklärbare Resultate; API ohne finale UI.
- **Nicht enthalten:** globale optimale Top-3-Kombination.
- **Abhängigkeiten:** S19.
- **Risiken:** Kennzahl verspricht mehr als Algorithmus garantiert.
- **Zu schützen:** heutige grobe Marktanzahl als Vergleich.
- **Akzeptanzkriterien:** Beispiele der Product Bible sind als Tests darstellbar; Begriffe werden nicht vermischt.
- **Definition of Done:** Kennzahlen enthalten Definition und Confidence/Scope.
- **Tests:** keine Partner, ein Partner, konkurrierende Sticker, Mengen.
- **Dokumentation:** Berechnungsdefinition.
- **Commit-Abschluss:** `feat: calculate market and personal trade coverage`
- **Größe:** mittel, 2–3 Entwicklungsabende.

#### S21 – Konfliktfreie Top-Match-Optimierung

- **Priorität/Arten:** P1 · ARCH, USER, TEST
- **Ziel:** Gemeinsam optimierte, konfliktfreie Smart-Trade-Pakete erzeugen.
- **Fachlicher Nutzen:** Maximaler Fortschritt mit wenigen Trades ohne Mehrfachverplanung.
- **Umfang:** Top-3-Kandidaten; gemeinsamer Ressourcenverbrauch; Zielfunktion Fortschritt/Tradeanzahl; deterministische Tie-Breaks; Erklärdaten.
- **Nicht enthalten:** frei wählbare Strategien, Reputation-Ranking oder albumübergreifende Trades.
- **Abhängigkeiten:** S19–S20.
- **Risiken:** kombinatorische Laufzeit und schwer erklärbare Auswahl.
- **Zu schützen:** vollständige manuelle Partnerliste.
- **Akzeptanzkriterien:** derselbe Sticker wird nie mehrfach verplant; Regression-Beispiel GER17 besteht.
- **Definition of Done:** deterministisch, begrenzt und gemessen auf realistischer Fixture.
- **Tests:** Konflikte, Mengen, Tie-Break, leere/hohe Partnerzahl, Performancebudget.
- **Dokumentation:** Optimierungsregel und Grenzen.
- **Commit-Abschluss:** `feat: generate conflict-free top smart matches`
- **Größe:** groß bis sehr groß, 5–8 Entwicklungsabende in Algorithmus-Teilcommits.

#### S22 – Smart-Trade-Anfragen und transparente Paketänderungen

- **Priorität/Arten:** P1 · USER, UX, ARCH, TEST
- **Ziel:** Smart-Pakete klar von manuellen Paketen trennen und sicher anfragen.
- **Fachlicher Nutzen:** Nutzer erhält verlässliche, nicht verhandelbare Smart-Vorschläge; manuelle Großzügigkeit bleibt möglich.
- **Umfang:** Smart-Paketkennzeichnung; Anfrage-Limit; Ablauf; Recheck; transparente Verkleinerung/erneute Zustimmung; Ausschließen und Neuberechnen.
- **Nicht enthalten:** Bewertungssortierung, Strategiewahl oder Cross-Album.
- **Abhängigkeiten:** S18–S21; Product-Owner-Gates Limit/Ablauf/Anpassungszustimmung.
- **Risiken:** Smart- und manuelle Regeln werden versehentlich gekoppelt.
- **Zu schützen:** manueller Dealwizard und Regel `geben >= bekommen`.
- **Akzeptanzkriterien:** Smart-Paket nicht editierbar; manuelles Paket weiterhin editierbar; Änderungen werden nie heimlich.
- **Definition of Done:** vollständiger Smart-Request-Happy-Path bis Reservierung getestet.
- **Tests:** Ablauf, Limit, Bestandskonflikt, Anpassung, Ablehnung/Neuberechnung.
- **Dokumentation:** Smart-vs.-manuell-Regelmatrix.
- **Commit-Abschluss:** `feat: integrate transparent smart trade requests`
- **Größe:** groß, 4–6 Entwicklungsabende.

### Phase 5 – Home und Notifications

#### S23 – Typisierte Notifications mit Zielobjekt

- **Priorität/Arten:** P1 · ARCH, TEST
- **Ziel:** Notifications aus echten Ereignissen adressierbar machen.
- **Fachlicher Nutzen:** Jede Meldung kann direkt zur relevanten Aufgabe führen.
- **Umfang:** Typ, Zieltyp/-ID, Deep Link, gelesen/ungelesen; Adapter aus Tradeevents; Legacy-Notifications lesbar.
- **Nicht enthalten:** Feed, Freundesnews oder finale Notification-UI.
- **Abhängigkeiten:** S07, S18.
- **Risiken:** doppelte Notifications bei Retry.
- **Zu schützen:** bestehende Notification-Erzeugung.
- **Akzeptanzkriterien:** Tradeanfrage, Annahme, Frist, Versand und Empfang besitzen stabile Ziele.
- **Definition of Done:** Ereignis erzeugt idempotent höchstens eine fachliche Notification.
- **Tests:** Typen, Deep-Link-Berechtigung, Deduplizierung, Legacy.
- **Dokumentation:** Notification-Eventkatalog.
- **Commit-Abschluss:** `feat: type notifications and attach target objects`
- **Größe:** mittel, 2–3 Entwicklungsabende.

#### S24 – Glocke, Badge und Notification-Historie

- **Priorität/Arten:** P1 · USER, UX, UI, TEST
- **Ziel:** Globale Benachrichtigungszentrale nutzbar machen.
- **Fachlicher Nutzen:** Ungelesene Ereignisse sind überall erreichbar und historisch nachvollziehbar.
- **Umfang:** Glocken-Badge zählt ungelesen; Liste; lesen; Deep Link; leere Zustände; einfache Pagination/Aufbewahrungsgrenze.
- **Nicht enthalten:** offene Aufgaben als Badgezahl oder finale visuelle Politur.
- **Abhängigkeiten:** S06, S23; Product-Owner-Gate Aufbewahrung.
- **Risiken:** gelesen wird mit erledigt verwechselt.
- **Zu schützen:** globale Headerstruktur.
- **Akzeptanzkriterien:** Lesen senkt Badge; Aufgabe bleibt offen; Zielobjekt öffnet korrekt.
- **Definition of Done:** mobile Bedienung und Berechtigungen getestet.
- **Tests:** Badge, Read-State, History, fremdes Ziel, Deep Link.
- **Dokumentation:** Glocken- und Badge-Semantik.
- **Commit-Abschluss:** `feat: add notification bell badge and history`
- **Größe:** mittel, 2–3 Entwicklungsabende.

#### S25 – Operatives Home V1

- **Priorität/Arten:** P1 · USER, UX, UI, TEST
- **Ziel:** Home beantwortet „Was braucht mich?“ und „Was ist passiert?“.
- **Fachlicher Nutzen:** Nutzer sieht dringende Tradehandlungen und laufende Vorgänge sofort.
- **Umfang:** priorisierte offene Aufgaben; Alles-erledigt-Zustand; kompakte Trades/Sendungen; Deep Links; getrennte ehrliche Platzhalter/Leerzustände für Freunde und Sammlr News.
- **Nicht enthalten:** künstlicher Feed, vollständige Tradeverwaltung oder permanente Albumfortschritte.
- **Abhängigkeiten:** S18, S23–S24; Product-Owner-Gates Anzahl/Sortierung/Wording.
- **Risiken:** doppelte Fachlogik auf Home.
- **Zu schützen:** Sammlung bleibt eigener Bereich; Tradezentrale bleibt Besitzer.
- **Akzeptanzkriterien:** Home leitet immer zum Fachobjekt; erledigte Aufgaben verschwinden; gelesene offene Aufgaben bleiben.
- **Definition of Done:** definierte Prioritätsfälle und Leerzustand sind getestet.
- **Tests:** Aufgabe vs. Notification, Reihenfolge, Deep Link, keine offenen Vorgänge.
- **Dokumentation:** Home-Eventmatrix V1.
- **Commit-Abschluss:** `feat: launch operational home v1`
- **Größe:** groß, 4–6 Entwicklungsabende.

### Phase 6 – Profil und Community

#### S26 – Eigenes und fremdes Profilfundament

- **Priorität/Arten:** P1 · USER, UX, ARCH, TEST
- **Ziel:** Profil als Sammlerseite statt bloßer Linkliste.
- **Fachlicher Nutzen:** Identität, Vertrauen, Alben, Vitrine, Trophäen und Statistik werden zusammen sichtbar.
- **Umfang:** eigenes/fremdes Profil; Username primär; optionaler Klarname, Bild und Standort; aktive Alben/Vitrine; kompakte Kennzahlen; bestehende Unterseiten verlinken.
- **Nicht enthalten:** Freunde, Bewertungen oder tiefes Privacy-Regelwerk.
- **Abhängigkeiten:** M1, M2.
- **Risiken:** private Bestandsdaten werden versehentlich sichtbar.
- **Zu schützen:** bestehende Statistik-, Trophy- und Profilbearbeitung.
- **Akzeptanzkriterien:** eigene und fremde Sicht sind getrennt; fehlende optionale Daten funktionieren.
- **Definition of Done:** Objektberechtigung und mobile Profilhierarchie getestet.
- **Tests:** own/foreign, unbekannter Nutzer, optionale Felder, XSS-Escaping.
- **Dokumentation:** Profil-Readmodel und Sichtgrenzen.
- **Commit-Abschluss:** `feat: establish collector profile pages`
- **Größe:** groß, 4–6 Entwicklungsabende.

#### S27 – Album-Sichtbarkeit und Profil-Privacy

- **Priorität/Arten:** P1 · SEC, USER, ARCH, TEST
- **Ziel:** öffentlich, Freunde und privat technisch durchsetzen.
- **Fachlicher Nutzen:** Sammler kontrollieren ihre Albumdaten.
- **Umfang:** Privacy-Einstellung; serverseitige Zugriffskontrolle für Album, Wall und Mengen; sichere Defaults; getrennte Vorbereitung von Sichtbarkeit und Tradepool.
- **Nicht enthalten:** endgültige Kopplungsentscheidung Tradepool oder komplexe Rollen.
- **Abhängigkeiten:** S26; Product-Owner-Gate Sichtbarkeit-vs.-Pool.
- **Risiken:** Datenleck über Nebenrouten oder Matching.
- **Zu schützen:** eigener Albumzugriff und Smart-Trade-Datengrundlage.
- **Akzeptanzkriterien:** jede relevante Route respektiert Sichtbarkeit; private Daten fehlen auch in abgeleiteten Views.
- **Definition of Done:** Zugriffsmatrix vollständig automatisiert getestet.
- **Tests:** Eigentümer, Fremder, künftiger Freund-Testdouble, direkte URL.
- **Dokumentation:** Privacy-Matrix und offene Poolentscheidung.
- **Commit-Abschluss:** `feat: enforce album profile visibility`
- **Größe:** groß, 3–5 Entwicklungsabende.

#### S28 – Bewertungen und Vertrauen

- **Priorität/Arten:** P1 · USER, SEC, TEST
- **Ziel:** Qualifizierte abgeschlossene Deals bewertbar machen.
- **Fachlicher Nutzen:** Nutzer erkennen Zuverlässigkeit vor einer Anfrage.
- **Umfang:** 1–5 Sterne; genau eine Bewertung je Richtung/Deal; erst nach Lifecycle-Abschluss; Durchschnitt und erfolgreiche Trades im Profil; strukturierte Gründe vorbereiten.
- **Nicht enthalten:** Freitext, komplexes Reputationsranking oder Streitentscheidung.
- **Abhängigkeiten:** M3, S26; Product-Owner-Gate Bewertungsgründe/Darstellung.
- **Risiken:** Missbrauch und rückwirkende Legacy-Bewertung.
- **Zu schützen:** Tradehistorie und abgeschlossene-Trade-Zählung.
- **Akzeptanzkriterien:** Anfrage/Versand allein reicht nicht; Selbst-/Doppelbewertung unmöglich.
- **Definition of Done:** Profilwert ist nachvollziehbar und nur aus qualifizierten Deals berechnet.
- **Tests:** Berechtigung, Zeitpunkt, Deduplizierung, Durchschnitt.
- **Dokumentation:** Bewertungsqualifikation V1.
- **Commit-Abschluss:** `feat: add qualified post-trade ratings`
- **Größe:** mittel bis groß, 3–4 Entwicklungsabende.

#### S29 – Freunde, Blockieren, Aktivitätsstatus und Tauschpotenzial

- **Priorität/Arten:** P2 · USER, SEC, UX, TEST
- **Ziel:** Grundlegende Community mit funktionalem Sammlernutzen.
- **Fachlicher Nutzen:** Sammler finden, verbinden, schützen und direkt tauschen.
- **Umfang:** beidseitige Freundschaftsanfrage; Liste/Suche; Blockieren neuer Interaktionen; grober Aktivitätsstatus; profil-/albumbezogenes Tauschpotenzial; direkter Einstieg in vorhandene Matching-/Tradefunktion.
- **Nicht enthalten:** globaler Social Feed, Besucherlisten, regionale Suche oder Events.
- **Abhängigkeiten:** S23–S28; Product-Owner-Gates Aktivitätsprivacy/Blockierung laufender Deals.
- **Risiken:** Blockierung beschädigt Tradehistorie oder laufende Deals.
- **Zu schützen:** historische Trades und Profilprivacy.
- **Akzeptanzkriterien:** Freundschaft ist beidseitig; Block verhindert neue Interaktion, löscht aber keinen Nachweis.
- **Definition of Done:** zentrale Interaktionsmatrix und Notifications funktionieren.
- **Tests:** Anfragezustände, Blockrichtungen, Aktivitätsklassen, Trade-Deep-Link.
- **Dokumentation:** Community- und Blockiermatrix.
- **Commit-Abschluss:** `feat: add collector relationships and profile trade potential`
- **Größe:** sehr groß, 6–9 Entwicklungsabende; in Daten-, Policy- und UI-Teilcommits.

### Phase 7 – Design Patch 1

#### S30 – Design Tokens und Kernkomponenten

- **Priorität/Arten:** P1 · UI, CI, UX, ARCH
- **Ziel:** Wiederverwendbares, ruhiges Sammlr Design System schaffen.
- **Fachlicher Nutzen:** Alle Kernbereiche wirken zusammengehörig und verständlich.
- **Umfang:** Tokens für Farbe, Typografie, Abstand, Radius, Status; Buttons, Karten, Formulare, Fehler, Leerzustände; CSS-Überschreibungen inventarisieren.
- **Nicht enthalten:** neue Fachfeatures, Pixelperfektion oder große Animationen.
- **Abhängigkeiten:** M6.
- **Risiken:** funktionale Selektoren brechen.
- **Zu schützen:** Statusfarben und Masterasset-Regeln.
- **Akzeptanzkriterien:** Kernkomponenten dokumentiert und auf Referenzseiten eingesetzt.
- **Definition of Done:** keine neue Wegwerf-Komponente; visuelle Regression-Smokes grün.
- **Tests:** mobile Screens, Status-/Fehlerzustände, Kontrast-Vorprüfung.
- **Dokumentation:** Tokens und Komponenten-Katalog.
- **Commit-Abschluss:** `design: establish sammlr design system foundations`
- **Größe:** groß, 4–6 Entwicklungsabende.

#### S31 – Navigation, Workflows und Mobile vereinheitlichen

- **Priorität/Arten:** P1 · UI, CI, UX, TEST
- **Ziel:** Navigation, Header und Fachworkflows konsistent gestalten.
- **Fachlicher Nutzen:** Nutzer erkennt Zustände und nächste Aktionen ohne Systemwissen.
- **Umfang:** Navigation, Header, Karten, Formulare, Status, Leerzustände, Wall, Trades, Home, Profil; mobile-first; ruhige iOS-nahe Bedienlogik.
- **Nicht enthalten:** neue Produktlogik, finale Accessibility oder Mikroanimationen.
- **Abhängigkeiten:** S30.
- **Risiken:** großer visueller Patch erzeugt Regressionen.
- **Zu schützen:** Wall-Geschwindigkeit, Papierliste und Dealaktionen.
- **Akzeptanzkriterien:** definierte Referenzscreens sind konsistent und mobil nutzbar.
- **Definition of Done:** Design-Review, visuelle Smoke-Matrix und keine offenen P0-UI-Regressionen.
- **Tests:** Viewport-Matrix, Tastatur-Smoke, zentrale Happy Paths.
- **Dokumentation:** Design Patch 1 Changelog und bekannte Restinkonsistenzen.
- **Commit-Abschluss:** `design: unify core sammlr product workflows`
- **Größe:** sehr groß, 6–9 Entwicklungsabende in seitenweisen Teilcommits.

### Phase 8 – Betrieb, Security und Public-Beta-Reife

#### S32 – Authentifizierung, Secrets und CSRF

- **Priorität/Arten:** P0 · SEC, ARCH, TEST
- **Ziel:** Kritische Auth- und Request-Sicherheit beta-tauglich machen.
- **Fachlicher Nutzen:** Nutzerkonten und schreibende Aktionen sind grundlegend geschützt.
- **Umfang:** Passwort-Hashing mit kontrollierter Altpasswortmigration; Secret-Management; CSRF; Session-Cookies; Login-Throttling-Grundlage.
- **Nicht enthalten:** SSO oder komplexes Identity-System.
- **Abhängigkeiten:** S03; kann vorbereitend früher laufen, Abschluss vor M8.
- **Risiken:** Nutzer werden ausgesperrt.
- **Zu schützen:** Login/Registrierung und bestehende Konten.
- **Akzeptanzkriterien:** kein Klartextpasswort neu gespeichert; Secrets nicht im Code; CSRF blockiert Fremdrequest.
- **Definition of Done:** Securitytests und Migrations-/Rollbackpfad dokumentiert.
- **Tests:** Legacy-Login, Rehash, Session, CSRF, Rate-Limit-Smoke.
- **Dokumentation:** Auth- und Secret-Betriebsanleitung.
- **Commit-Abschluss:** `security: harden authentication sessions and csrf`
- **Größe:** groß, 4–6 Entwicklungsabende.

#### S33 – HTTP-Methoden, Debugrouten und Datenbank-Constraints

- **Priorität/Arten:** P0 · SEC, ARCH, TEST
- **Ziel:** Gefährliche Entwicklungsaltlasten und ungesicherte Datenbeziehungen beseitigen.
- **Fachlicher Nutzen:** Keine versehentlichen Schreibaktionen oder Datenbankresets im öffentlichen Betrieb.
- **Umfang:** mutierende GETs auf POST; Debugrouten entfernen/absichern; Foreign Keys, Unique-/Check-Constraints über versionierte Migrationen; Fehlerbehandlung.
- **Nicht enthalten:** neues Produktfeature.
- **Abhängigkeiten:** S13, S32.
- **Risiken:** vorhandene inkonsistente Daten blockieren Constraints.
- **Zu schützen:** alle Fachrouten und Datenbestände.
- **Akzeptanzkriterien:** GET ist idempotent; Debugzugriff in Produktion unmöglich; Constraints bestehen auf Fixture und geprüfter Kopie.
- **Definition of Done:** Migration, Integrity-Check und Regression-Suite grün.
- **Tests:** Methoden, CSRF, FK/Unique/Check, Legacy-Datenprüfung.
- **Dokumentation:** Constraint- und Debug-Entscheidung.
- **Commit-Abschluss:** `security: enforce safe http and database integrity`
- **Größe:** groß, 4–6 Entwicklungsabende.

#### S34 – Deployment, Backup, Recovery, Logging und Fehlertracking

- **Priorität/Arten:** P1 · ARCH, SEC, DOC, TEST
- **Ziel:** Reproduzierbaren und beobachtbaren Betrieb herstellen.
- **Fachlicher Nutzen:** Beta kann sicher ausgerollt und bei Problemen wiederhergestellt werden.
- **Umfang:** eindeutiger App-Einstieg; Umgebungen; Backup/Restore-Probe; strukturierte Logs ohne sensible Daten; Fehlertracking; Healthcheck; Migrationsablauf.
- **Nicht enthalten:** Hochverfügbarkeitsplattform oder große Lastarchitektur.
- **Abhängigkeiten:** S32–S33.
- **Risiken:** Backup existiert, Restore wurde aber nie getestet.
- **Zu schützen:** Seed/Test/Produktivdaten klar trennen.
- **Akzeptanzkriterien:** frisches Deployment und Restore sind dokumentiert reproduzierbar; Fehler korrelierbar.
- **Definition of Done:** Recovery-Drill und Deployment-Checkliste erfolgreich.
- **Tests:** Start, Health, Migration, Backup/Restore, Log-Redaction.
- **Dokumentation:** Runbook und Incident-Miniplan.
- **Commit-Abschluss:** `ops: establish deploy backup recovery and observability`
- **Größe:** groß, 4–6 Entwicklungsabende.

#### S35 – Datenschutz, Account Lifecycle und Performance-Baseline

- **Priorität/Arten:** P1 · SEC, ARCH, UX, TEST
- **Ziel:** Öffentliche Nutzung rechtlich/technisch vorbereiten und Kernperformance messen.
- **Fachlicher Nutzen:** Nutzerkonten können verantwortungsvoll betrieben werden; Kernseiten bleiben schnell.
- **Umfang:** Dateninventar; Lösch-/Sperr-/Anonymisierungsregeln; historische Trades schützen; Export/Retention-Grundlage; Query-/Page-Baselines; einfache Lasttests.
- **Nicht enthalten:** Rechtsberatung ersetzen, regionale/Versanddaten oder Premium.
- **Abhängigkeiten:** S18, S23–S29, S34; Product-Owner/Legal-Gates.
- **Risiken:** Kontolöschung widerspricht Nachweispflichten.
- **Zu schützen:** Tradehistorie bei gleichzeitiger Datensparsamkeit.
- **Akzeptanzkriterien:** Accountzustände und Datenfolgen dokumentiert; P0-Performanceprobleme behoben oder blockierend markiert.
- **Definition of Done:** Privacy-Review, Retention-Matrix und reproduzierbare Baseline.
- **Tests:** Delete/Block/Anonymize, Berechtigungen, Kernlastfälle.
- **Dokumentation:** Datenschutz-/Retention-Matrix und Performancebericht.
- **Commit-Abschluss:** `security: define account lifecycle privacy and beta performance`
- **Größe:** groß bis sehr groß, 5–8 Entwicklungsabende plus fachliche Prüfung.

### Phase 9 – Design Patch 2 und Public Beta

#### S36 – Accessibility, responsive Sonderfälle und finale CI-Politur

- **Priorität/Arten:** P1 · UI, CI, UX, TEST
- **Ziel:** Letzte visuelle und interaktive Inkonsistenzen vor Beta schließen.
- **Fachlicher Nutzen:** Sammlr ist robust, zugänglich und markenkonsistent.
- **Umfang:** Tastatur/Fokus; Screenreader-Semantik; Kontrast; Fehlerzustände; Mikrointeraktionen; responsive Sonderfälle; Oberflächenperformance; finale CI-Prüfung.
- **Nicht enthalten:** neue Fachfeatures oder aufwendige Showanimationen.
- **Abhängigkeiten:** M7, S32–S35.
- **Risiken:** späte UI-Änderung beeinflusst kritische Workflows.
- **Zu schützen:** Geschwindigkeit der Bestands- und Tauschbedienung.
- **Akzeptanzkriterien:** Accessibility-Checkliste erfüllt; keine P0/P1-responsive Regression.
- **Definition of Done:** Design Patch 2 Review und automatisierte/manuel­le UI-Matrix abgeschlossen.
- **Tests:** Tastatur, Fokus, Kontrast, Zoom, Viewports, reduzierte Bewegung, Performance.
- **Dokumentation:** Accessibility- und Design-Patch-2-Bericht.
- **Commit-Abschluss:** `design: complete accessibility and public beta polish`
- **Größe:** groß, 4–6 Entwicklungsabende.

#### S37 – Public-Beta-Freigabe

- **Priorität/Arten:** P1 · DOC, TEST, SEC, UX
- **Ziel:** Kontrollierte öffentliche Teststufe freigeben.
- **Fachlicher Nutzen:** Reales Feedback unter beherrschbaren Risiken.
- **Umfang:** Beta-Testplan; definierte Testgruppe; Feedbackkanal; Supportweg; Releasecheckliste; Daten-/Migrationsprobe; Monitoring; Rollback; Go/No-Go.
- **Nicht enthalten:** neue Features, Future Backlog oder ungeprüfte Skalierung.
- **Abhängigkeiten:** alle M0–M7 und S32–S36; Product-Owner-Gate Testgruppe/Go.
- **Risiken:** letzte Featurewünsche verwässern Releasekriterien.
- **Zu schützen:** stabiler Kern und Recovery-Fähigkeit.
- **Akzeptanzkriterien:** alle M8-Kriterien erfüllt; keine offenen P0-Bugs; Rollback getestet; Verantwortlichkeiten benannt.
- **Definition of Done:** dokumentiertes Go, versionierter Release und aktiver Feedback-/Incident-Kanal.
- **Tests:** vollständige End-to-End-Matrix, Smoke nach Deployment, Rollback-Drill.
- **Dokumentation:** Release Notes, Beta Guide, bekannte Einschränkungen.
- **Commit-Abschluss:** `release: prepare sammlr public beta v1`
- **Größe:** mittel bis groß, mehrere fokussierte Entwicklungsabende und Product-Owner-Abnahme.

## 8. Dependency Map

```text
S00 Referenz/Testdaten
└── S01 Bestandstests
    ├── S02 Tradeflowtests
    │   └── S03 Testgate
    └── S08 Inventory Contract
        └── S09 Lesen
            └── S10 Schreiben
                └── S11 Availability
                    └── S12 Guards
                        └── S13 Lifecycle-Schema
                            └── S14 Reservierung
                                └── S15 Versand
                                    └── S16 Empfang
                                        ├── S17 Probleme
                                        └── S18 Events/Fristen
                                            └── S19 Snapshot
                                                └── S20 Abdeckung
                                                    └── S21 Top Matches
                                                        └── S22 Smart Requests
```

```text
S04 Home/Sammlung trennen
└── S05 3er-Navigation
    └── S06 Header
        └── S07 Deep Links
            └── S23 typisierte Notifications
                └── S24 Glocke/History
                    └── S25 Home V1
```

```text
S26 Profil
├── S27 Privacy
├── S28 Bewertungen ← M3
└── S29 Freunde/Block/Activity/Tauschpotenzial ← S23, S27, S28
```

```text
Security-Querschnitt:
S03 Baseline
├── S13 versionierte Migrationen
├── S27 Privacy
├── S32 Auth/Secrets/CSRF
├── S33 HTTP/Constraints
├── S34 Betrieb/Recovery
└── S35 Datenschutz/Account/Performance
```

Navigation S04–S07 darf nach M0 teilweise parallel zu S08–S12 laufen. S23–S25 wartet auf echte Lifecycle-Events; S26 kann als Read-only-Profilbasis früher vorbereitet werden, Community-Schreibfunktionen nicht.

## 9. Meilensteine

| Meilenstein | Messbare Kriterien |
| --- | --- |
| **M0 – Ist-Kern geschützt** | anonymisierte Fixture; Bestands-, Papierlisten-, Trade-, Trophy- und Notificationtests; ein Pflicht-Testbefehl |
| **M1 – Neue Navigation aktiv** | getrennte Home/Sammlung; 3er-Bottom-Navigation; Avatar/Glocke; sichere kontextuelle Rückwege |
| **M2 – Inventory Engine verlässlich** | zentrale Lese-/Schreibwege; dokumentierte Invarianten; Availability nie negativ; manuelle Guards testbar |
| **M3 – Trade Lifecycle vollständig** | Annahme reserviert; Versand/Empfang je Seite; idempotente Buchung; Probleme/Teilempfang; Fristen/Eventlog/History |
| **M4 – Smart Trader 2.0 nutzbar** | Snapshot; beide Abdeckungen; konfliktfreie Top Matches; Smart Requests; manueller Trade unverändert nutzbar |
| **M5 – Home/Notifications operativ** | typisierte Ziele; Glocke/Badge/History; Aufgaben getrennt von gelesen; kompakte Tradeübersicht |
| **M6 – Profile/Community nutzbar** | eigenes/fremdes Profil; Privacy; Bewertungen; Freunde; Blockieren; Aktivitätsstatus; direkter Tradeeinstieg |
| **M7 – Visuell vereinheitlicht** | Tokens/Komponenten; Kernseiten mobile-first konsistent; Design Patch 1 ohne P0-Regression |
| **M8 – Public-Beta-ready** | Security-/Privacy-Gates; Migration/Backup/Restore; Observability; Accessibility; E2E; Rollback; Go/No-Go |

## 10. Definition of Done

### Produktebene

Eine Funktion ist produktseitig fertig, wenn sie:

- einer Product-Bible-Entscheidung entspricht,
- einen eindeutigen fachlichen Besitzer besitzt,
- mit realistischen Zuständen statt Demoannahmen arbeitet,
- verständliche UX inklusive Fehler- und Leerzustand besitzt,
- bestehende Kernflows nicht regressiert,
- dokumentiert und beobachtbar ist.

### Phasenebene

Eine Phase ist fertig, wenn:

- ihr Meilenstein messbar erreicht ist,
- alle P0-Sprints abgeschlossen sind,
- keine offene Abhängigkeit als erledigt dargestellt wird,
- Regression-, Security- und Migrationsprüfungen für ihren Umfang grün sind,
- relevante Product-Bible-, Decision- und Roadmap-Dokumente aktualisiert sind.

### Sprintebene

Ein Sprint ist fertig, wenn:

- Umfang und expliziter Nichtumfang eingehalten wurden,
- Akzeptanzkriterien nachweisbar erfüllt sind,
- notwendige automatisierte Tests grün sind,
- manuelle mobile/UX-Smokes erfolgt sind, sofern UI betroffen ist,
- Datenmigrationen vorwärts, wiederholt und bei Bedarf rückwärts geprüft sind,
- Dokumentation und bekannte Restpunkte aktualisiert sind,
- ein fokussierter Commit-Abschluss ohne sachfremde Änderungen vorliegt.

## 11. Design-Patch-Strategie

### Laufende Fachsprints

- **UX:** immer verständlicher Ablauf und sinnvolle Fehlermeldungen.
- **UI:** sauber, schlicht, mobile-first; keine Wegwerfoberfläche.
- **CI:** vorhandene Wortmarke, Lila, Typografie und Masterassets respektieren.
- **Design System:** neue wiederkehrende Muster als Kandidaten markieren, aber nicht in jedem Fachsprint global perfektionieren.

### Design Patch 1

Nach M6: Tokens, Komponenten, Navigation, Header, Karten, Buttons, Formulare, Abstände, Typografie, Icons, Status, Fehler, Leerzustände und mobile Ansichten vereinheitlichen.

### Design Patch 2

Vor Public Beta: Accessibility, Fokus, Fehlertoleranz, Mikrointeraktionen, responsive Sonderfälle, Oberflächenperformance und finale CI-Politur.

## 12. Security-Querschnitt

Security beginnt mit S03 und wird in jedem betroffenen Sprint akzeptanzrelevant:

- Objektberechtigung bei Deep Links,
- Transaktions- und Konkurrenztests bei Reservierungen,
- Privacy bei Profil und Freunden,
- idempotente Events und Notifications,
- keine sensiblen Daten in Logs/Testfixtures,
- versionierte Migrationen,
- sichere HTTP-Methoden und CSRF,
- Passwort- und Secret-Schutz,
- Tradehistorie trotz Account-/Blockierprozessen,
- Recovery vor Beta.

S32–S35 sind das Abschlussgate, nicht der Beginn der Security-Arbeit.

## 13. Future Backlog

| Thema | Einordnung |
| --- | --- |
| vollständige Mehrfachalbum-UI und komplexes Poolmanagement | FUTURE – Architektur vorbereiten, nicht in M0–M8 ausbauen |
| komplette Albumübertragung | FUTURE |
| KI-/Foto-Scanner | FUTURE |
| Offline-Synchronisation | FUTURE |
| QR-Börsenmodus | FUTURE |
| regionale Suche und lokale Events | FUTURE |
| Marketplace und Shop | FUTURE |
| Versandlabels, Versicherung, anonymisierter Versand | FUTURE |
| Premium | FUTURE |
| globale objektübergreifende Suche | FUTURE |
| komplexe Mehrparteien-Trades | FUTURE |

## 14. Offene Entscheidungen / Product-Owner-Gates

| Gate | Spätestens vor | Entscheidung |
| --- | --- | --- |
| Begriff „Sammlr-Zentrale“ | S04 | Name bleibt Sammlungseinstieg oder wird bewusst ersetzt |
| Inventory Contract | S09 | genaue Kompatibilitätsabbildung Albumzuordnung/freier Pool V1 |
| Anfrageablauf | S18/S22 | exakte Dauer innerhalb 1–2 Tagen |
| Versandfrist | S18 | Definition fünf Werktage und Feiertage |
| Problemfall V1 | S17 | minimale UX, zulässige Auflösungen und Supportgrenze |
| Smart-Request-Limit | S22 | endgültige Zahl paralleler ausgehender Anfragen |
| Paketanpassung | S22 | automatische Verkleinerung oder erneute Zustimmung |
| Notification-Aufbewahrung | S24 | Dauer und Archivierungsumfang |
| Home V1 | S25 | Anzahl, Sortierung und Wording dringender Aufgaben |
| Albumprivacy vs. Tradepool | S27 | gekoppelte oder getrennte Einstellungen |
| Bewertungen | S28 | öffentliche Darstellung und strukturierte Gründe |
| Aktivitätsstatus | S29 | Sichtbarkeit, Klassen und Datenschutz |
| Blockierung laufender Deals | S29 | zulässige Interaktionen und Eskalation |
| Account Lifecycle | S35 | Löschen, Sperren, Anonymisieren, Tradehistorie |
| Public-Beta-Testgruppe | S37 | Größe, Zugang, Feedback- und Supportverantwortung |

Keine dieser Fragen darf stillschweigend durch einen Implementierungsdetailentscheid beantwortet werden.

## 15. Empfohlener erster Sprint

**S00 – Referenzstand und Testdatenstrategie**

Begründung: Ohne anonymisierte, reproduzierbare Ausgangsdaten und klaren Referenzstand können Tests den real funktionierenden Kern nicht zuverlässig schützen. S00 ist klein, blockiert keine Produktentscheidung und reduziert das Risiko aller folgenden Sprints.

## 16. Empfohlene nächsten fünf Sprints

1. **S00** – Referenzstand und Testdatenstrategie
2. **S01** – Bestands-Regressionstests
3. **S02** – Papierlisten- und Tradeflow-Regressionstests
4. **S03** – Nebenwirkungen, Security-Baseline und CI-Testgate
5. **S04** – Home- und Sammlungsrouten trennen

Danach folgt **S05 – Dreiteilige Bottom-Navigation**. Parallel darf erst nach M0 die fachliche Vorbereitung von S08 beginnen.

## 17. Roadmap-Index für tägliches Arbeiten

| Jetzt/Reihenfolge | Sprint | Blockiert/Freigabe |
| --- | --- | --- |
| 1 | [S00 – Referenzstand](#s00--referenzstand-und-testdatenstrategie) | sofort |
| 2 | [S01 – Bestandstests](#s01--bestands-regressionstests) | S00 |
| 3 | [S02 – Tradeflowtests](#s02--papierlisten--und-tradeflow-regressionstests) | S00–S01 |
| 4 | [S03 – Testgate](#s03--nebenwirkungen-security-baseline-und-ci-testgate) | S00–S02 |
| 5 | [S04 – Home/Sammlung trennen](#s04--home--und-sammlungsrouten-trennen) | M0 + Begriffs-Gate |
| 6 | [S05 – 3er-Navigation](#s05--dreiteilige-bottom-navigation) | S04 |
| parallel danach | [S08 – Inventory Contract](#s08--inventory-invarianten-und-zielmodell-festschreiben) | M0 |

Tägliche Regel: Nur den ersten nicht blockierten Sprint beginnen. Ein späterer attraktiver Sprint wird nicht vorgezogen, wenn seine Daten- oder Zustandsabhängigkeit fehlt.
