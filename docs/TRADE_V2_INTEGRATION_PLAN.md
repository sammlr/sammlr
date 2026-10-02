# Trade-v2 – Integrationsplan

Stand 2026-10-02. Planung, keine Implementierung. Trade-v2 ist als UX-/Vertragsreferenz grundsätzlich integrationsbereit, nicht als direkt produktiv registrierbarer Blueprint. Phase01 kann nach Abgrenzung der lokalen Ausgangsbasis sicher lesend beginnen. Keine offene Produktentscheidung aus alten STOPs wird erneut aufgemacht.

Die gewünschte Reihenfolge bleibt weitgehend erhalten. Phase03 ist ausdrücklich unverbindlich; Phase04 implementiert Binding nur hinter geschlossenem Gate. Öffentliche neue Anfragen erst nach vollständiger Abwicklung bis Phase08 und kontrollierter Freigabe09. Keine Nutzer in halbfertige physische Verträge bringen.

## INTEGRATION-01 – Geschützte Shell und Read Models

- **Scope:** Bestehende App-Shell, Navigation und contract-aware Readadapter; Featureflag default off. Preview unverändert als Referenz erhalten.
- **Dateien/Module:** App/webapp.py Auth/Navigation; neue getrennte Trade-v2-Produktivadapter/Templates; bestehende Reader
- **DB-Auswirkung:** Keine Schema-/Bestandsänderung. Keine discover/cleanup-Sideeffects im Readpfad.
- **Risiken:** Sessiondefault1/IDOR, unklare lokale Baseline
- **Tests:** Login/CSRF, fremde IDs, legacy Deep Links, GET ohne DB-Schreibzugriff, responsive375/390/430
- **Rollback/Schutz:** Flag aus entfernt nur neuen Einstieg; alte Links bleiben. Baseline vorher reproduzierbar abgrenzen.
- **Abnahme:** Authentifizierte Shell zeigt ausschließlich eigene reale Readmodeldaten, keine Fixturecontrols; Legacy unverändert.

## INTEGRATION-02 – Reale Discovery und Partner

- **Scope:** Top3 aus gültiger kanonischer Planung, Nachrücken/Dismiss; Alle Sammlr und Paaransicht mit Privacy.
- **Dateien/Module:** smartdeal_planning/optimizer/revalidation, InventoryReadService, Community/AlbumPrivacy; neue DTOs
- **DB-Auswirkung:** Keine Tradebindung; Dismiss höchstens private UIpräferenz, nicht Domainstate.
- **Risiken:** Globalplan mit Paarpotential verwechseln, Need-/Privacy-Leak
- **Tests:** Katalogmapping, Block/privates Album, gebundene Supply/Need, Top3 aus max5, kleine Paarpotentiale ohne unzulässigen Submit
- **Rollback/Schutz:** Flag aus; kanonischen Optimizer und alte Discovery nicht umschreiben.
- **Abnahme:** Keine Fixtures; frische Eligibility; Discovery erzeugt weder Slot noch Reservation.

## INTEGRATION-03 – Servervalidierte unverbindliche Auswahl

- **Scope:** Manuelle bilateral freigegebene Pool-/Albumregeln und Smartpaketvalidierung; reine Draft-/Reviewphase ohne Submitbindung.
- **Dateien/Module:** Neue scoped Validatoren; manual_rules-UI als Vorprüfung; kanonische Stickerliste und SmartDeal-Revalidation
- **DB-Auswirkung:** Präferenzmodell/Defaults festlegen; Persistenzentwurf testen, produktive Einführung mit Phase04 koordinieren.
- **Risiken:** Clientregel als SoT; direkte Inventartransferroute versehentlich nutzen
- **Tests:** Receive≤Give per Album/OPEN-Pool; unilateral cross blockiert; geschlossene Alben; stale Supply; vierte Auswahl blockiert ohne Ausblenden
- **Rollback/Schutz:** Draftfeature abschaltbar, keine Inventar-/Vertragsmutation.
- **Abnahme:** Server lehnt manipulierte Auswahl ab; Originalreihenfolge/Mengen sichtbar; keine Anfrage aus GET/Review.

## INTEGRATION-04 – Versionierte Persistenz und atomarer Submit

- **Scope:** Schema-/Contractgeneration, immutable Paket, beidseitige Bindung, 3/3 operative Slots und Idempotenz; vorerst nur isolierte Test-/interne Umgebung.
- **Dateien/Module:** Neue scoped Request/Reservation/Capacity-Services; shared Availability-Coverage; Migration/runtime_operations geplant angepasst
- **DB-Auswirkung:** Schema20/21-Ausgangslage verifizieren; versionierte additive Migration nach Backup/restore rehearsal; neue Contracttypen, Positionen, Bindungen, Events. Keine Legacysemantik migrieren.
- **Risiken:** Write-write races, unbekannte Contracttype CHECKs, Legacy und V2 konkurrieren um Supply
- **Tests:** Zwei Connections letztes Duplicate; 2/3+zweiSubmits; Incomingneed; retry; rollback bei Injected Failure; bestehende V1/Legacy-Gates
- **Rollback/Schutz:** Neuerstellung aus; additive Schemaelemente nicht blind droppen. Neue Vorgänge nie als Legacy öffnen.
- **Abnahme:** Genau ein atomarer Commit pro Bindung; beide Slotachsen max3; shared Inventar zählt alle Vertragsgenerationen.

## INTEGRATION-05 – Accept/Decline/Expiry und laufende Trades

- **Scope:** Servercommands, immutable Annahme, Withdraw/Decline/24h, eigener/Partner-Aktionsbedarf, Typed Notifications und Deep Links.
- **Dateien/Module:** Neue Lifecycle-/Readmodelservices, typed_notifications/events, Übersichtadapter
- **DB-Auswirkung:** Requestrevision/Zeiten/Events/Outbox; keine zweite Reservation bei Accept.
- **Risiken:** Accept-expiry race, Uhrzeitclient, angenommene Slots fälschlich frei
- **Tests:** Deadline exakte Grenze UTC; Race mit Withdraw/Expiry; doppelte Notifications; incoming/outgoing Sicht und Autorisierung
- **Rollback/Schutz:** Flag verhindert neue Bindung; bereits bestehende neue Requests weiter bearbeiten, Cleanup kontrolliert.
- **Abnahme:** Annahme hält Slots und Paket; Terminal vor Versand gibt Bindung frei; keine GET-Mutation durch Übersichtsrender.

## INTEGRATION-06 – Packen und explizite Amendments

- **Scope:** Packprüfung pro Version, Fehlmengenmeldung, genaue reduzierte Pakete und notwendige Zustimmung; kein stilles Recalculate.
- **Dateien/Module:** Neue Packing/Amendment-Services; UI aus packing/amendment adaptieren
- **DB-Auswirkung:** Versionierte Pack-/Vorschlags-/Consentdaten; atomarer Reservationswechsel.
- **Risiken:** Indexpaarung der Preview für asymmetrische manuelle Trades ungeeignet; Versand vs Amendment
- **Tests:** G>R, crossalbum/SAME-Regeln nach Reduktion, stale Zustimmung, Amendment-Pack/Ship-Race, versendete Richtung immutable
- **Rollback/Schutz:** Amendmentfeature stoppen, gebundene Originalversion bleibt gültig; keine automatische Reparatur.
- **Abnahme:** Exaktes Paket vor Zustimmung; alte Version auditierbar; neue Version verlangt passende Packfreigabe.

## INTEGRATION-07 – Private Adresse und eigener Versand

- **Scope:** Konkrete Adressfreigabe getrennt von Vorlage, Zugriff/Revocation/Retention; Versand je Richtung und eigener Slotrelease.
- **Dateien/Module:** Neue Adresspolicy/-service, Shippingadapter und Inventory-History
- **DB-Auswirkung:** Private Release/Snapshotdaten, Packversion, genau einmal Buchungsledger, shipping state/slot transaction.
- **Risiken:** IDOR/Cache/Logs, Widerruf bei laufendem physischem Trade, doppelte Buchung
- **Tests:** Fremde IDs/role query, Abschlusszugriff endet, notwendiger Problemfall, Shipretry, Partner-unshipped, eigener Slot frei
- **Rollback/Schutz:** Keine neue Bindung bei Ausfall; physische Trades und notwendiger Adresszugriff bleiben bedienbar, keine destruktive Downmigration.
- **Abnahme:** Nur Partner mit gültiger Freigabe sieht Adresse; eigener Versand gibt nur eigenen Slot frei; Reservierungen/Inventar konsistent.

## INTEGRATION-08 – Q2 Empfang, Problem, Abschluss, 3-Sterne

- **Scope:** Unabhängiger tatsächlicher Empfang, Alles da/Problem, Lösung und Abschluss; optionale immutable V2-Bewertung.
- **Dateien/Module:** Neue Receipt/Problem/Completion/Ratingadapter; vorhandene Inventory-/Historyprimitive scoped nutzen
- **DB-Auswirkung:** Empfang/Problemversionen, Ledger, Abschluss, Skalenkennung; Legacy1–5 bleibt.
- **Risiken:** Receipt ohne SHIPPED doppelt buchen; Receipt darf eigenen Sender-Slot nicht heimlich lösen
- **Tests:** Partner PACKING/READY + RECEIVED_OK und Problem; späterer Shipretry; Teilmengen; Problemlösung; rating1..3 einmal; berechtigter Problemabschluss; Legacy-Gates
- **Rollback/Schutz:** Neue Anfragen abschalten; vorhandenen V2-Abwicklungsweg behalten. Keine Rückdeutung zu Legacy.
- **Abnahme:** Q2 ohne Shipping-/Slotmutation; Buchungen genau einmal; unerledigter eigener Versand bleibt erreichbar, auch wenn Empfänger bereits abgeschlossen hat.

## INTEGRATION-09 – Kontrollierte Umschaltung und Cleanupvorbereitung

- **Scope:** Erst jetzt öffentliche neue Bindungen per Kohorte; Tauschen-Einstieg produktiv. Altlinks weiterhin contract-aware; Depecationinventur ohne automatische Löschung.
- **Dateien/Module:** App-Navigation, Deep-link dispatcher, Betriebsmetriken/Runbook; UIadapter
- **DB-Auswirkung:** Keine rückwirkende Trade-/Preference-/Ratingmigration; nur freigegebene neue Contracts.
- **Risiken:** Rollback kappt laufende physische Vorgänge, Notificationlinks falsch
- **Tests:** End-to-End zwei echte Sessions, Auth/Privacy, Parallelrequests, 375/390/430, Cardparität und Stack1/2/5/6/10/15/37; no overflow; Restore rehearsal
- **Rollback/Schutz:** Kill switch nur Neuerstellung; Lifecycle für gebundene V2 bleibt online, Legacy bleibt online.
- **Abnahme:** Alle Phasen/Gates bestanden, keine Previewcontrols, vollständige Abwicklung, dokumentierter Restore-/Rollbackpfad.

## Entscheidungskategorien

### BLOCKER

Vor dem ersten Integrationspatch muss der geprüfte lokale Stand reproduzierbar abgegrenzt werden: gesamter Trade-v2-Zweig und wesentliche Services/Migrationen sind untracked, produktive Dateien bereits stark geändert. Ein Checkout von HEAD reproduziert diese Grundlage nicht. Versionierungs-/Baselineumfang bestimmen und bewahren; dieser Auftrag autorisiert dafür keinen Commit. Die Analyse selbst ist belastbar und vollständig möglich. Keine zusätzliche Domainentscheidung blockiert die **lesende** Phase01; Authschutz und wirklich readonly Reader sind deren harte Abnahmebedingungen.

### LATER

Vor dem jeweiligen schreibenden Schritt: reale Deployment-/Schema20/21-Baseline verifizieren, neue Contract-/Reservierungs-/Slotpersistenz und atomare Commands, bilaterale Präferenzdefaults, explizite Amendmentpakete, Adressretention, Q2-Ledger und Rating-Skalendarstellung spezifizieren und testen. Diese Arbeiten sind Phasen03–08 zugeordnet, kein Grund die lesende Shell aufzuhalten. Keine stillschweigende Änderung von Legacy, keine Neuberechnung gebundener Deals.

### VISUAL POLISH

Großer visueller Überarbeitungspass erst nach technischer Integration. Bereits verbindliche kanonische Kartenmaße, Stackcap5/10, Layergeometrie, Bedienbarkeit und mobile Overflowfreiheit sind dagegen Regression-Gates jeder betroffenen Phase und kein später optionaler Polish.
