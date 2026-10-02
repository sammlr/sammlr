# SAMMLR RC1 – Executive Summary

Stand: 9. August 2026

## Position heute

Sammlr ist nach S38 **fachlich RC-ready**, aber **noch nicht Closed-Beta-ready**.

Die ursprünglichen Kernlücken der alten Gap Analysis sind weitgehend geschlossen. Sammlr besitzt heute eine durchgängige Sammler- und Tauschplattform: zentrale Bestandsdienste, Availability Snapshot, Reservierungen, Versand und Empfang je Seite, Teilmengen und Problemfälle, deterministische Smart Matches, typisierte Notifications, operative Home, Profile, Privacy, Freunde, Blocks, Ratings, Account-Lifecycle, Datenexport sowie eine belastbare Security- und Deployment-Grundlage.

Der zweimal erfolgreiche S38-Gesamtlauf mit jeweils 529 Tests ist ein starkes Qualitätssignal. Die nächste Hürde ist nicht weitere Featurebreite, sondern die zuverlässige Auslieferung und reale Nutzung des bereits vorhandenen Produkts.

## Größte Stärken

- Der Trade-Lifecycle ist fachlich tief, idempotent und berechtigungsgeprüft.
- Inventory Read/Write, Availability und Snapshot bilden eine gemeinsame Wahrheit.
- Smart Matching und Trade Coverage sind read-only und deterministisch aufgebaut.
- Home und Notifications trennen operative Aufgaben sauber von Historie.
- Privacy, Community, Ratings und Accountzustände sind miteinander integriert.
- Security-Härtung, versionierte Migrationen und Regressionstests sind für einen RC weit entwickelt.
- Die dreiteilige Navigation aus Sammlung, sammlr. und Tauschen ist klar; Profil und Glocke bleiben persönliche Headeraktionen.

Diese Bereiche sollten vor Beta nicht neu erfunden oder großflächig refaktoriert werden.

## Beta-Blocker

1. **Performance:** Im verbindlichen S35-Lastprofil überschreiten Sammlung, Album, Stickerwall, Tauschbörse, Dealansicht und Notifications fünf Sekunden beziehungsweise timeouten. Suche und Profil liegen ebenfalls über einer Sekunde. Das betrifft Kernreisen und blockiert jede externe Beta.
2. **Laufzeitintegrität:** SQLite-Foreign-Keys sind im Schema vorhanden, ihre Aktivierung ist in normalen Anwendungsverbindungen aber nicht zentral erzwungen. Connection-, Lock- und Timeoutregeln müssen verbindlich werden.
3. **Release-Reproduzierbarkeit:** Abhängigkeiten sind nicht vollständig gepinnt; der Arbeitsstand enthält zahlreiche lokale Datenbanken, Backups, Cache- und historische Arbeitsdateien. Ein sauberer, unveränderlicher RC-Build aus leerer Umgebung fehlt.
4. **Browsernachweis:** 529 Tests sichern Services und Flask-Verträge breit ab, aber ein echter End-to-End-Browserflow über zwei Nutzer, Mobile/Desktop, JavaScript, Modals und CSRF fehlt.
5. **Betrieb und Recht:** Zieldeployment, externe Alarmierung und Restore müssen real geprobt werden. Datenschutzerklärung und Impressum sind noch funktionale Entwürfe und brauchen vor externen Testern eine rechtliche Freigabe.

## Die nächsten fünf Prioritäten

1. Die sechs blockierten Kernpfade mit identischem S35-Datensatz profilieren, gezielt korrigieren und unter 20 parallelen Requests erneut messen.
2. Eine kanonische SQLite-Connection-Konfiguration mit Foreign Keys sowie klaren Lock-/Timeout- und Transaktionsregeln etablieren.
3. Einen sauberen, gepinnten und reproduzierbaren RC-Build erstellen, getrennt von lokalen Datenbanken, Backups und historischen Kopien.
4. Den vollständigen Zwei-Nutzer-Kernflow in einem echten Browser automatisieren und auf 390/430 px sowie Desktop prüfen.
5. Zieldeployment, Monitoring, Backup/Restore und Legaltexte abnehmen; danach eine kleine, begleitete Nutzerkohorte starten.

## Releaseurteil

| Stufe | Urteil |
|---|---|
| RC-ready | **Ja**, als fachlich vollständiger und stark regressionstesteter Kandidat |
| Closed-Beta-ready | **Nein**, bis Performance, Integrität, Build, Browsergate, Betrieb und Legal geschlossen sind |
| Public-Beta-ready | **Nein**, zusätzlich fehlen reale Closed-Beta-Evidenz, Onboardingvalidierung, Monitoring/Support und weitere Security-/UX-Härtung |
| 1.0-ready | **Nein**, reale Betriebsbewährung und ein bewusster Abbau der wichtigsten Wartungsschulden fehlen |

## Realistische Distanz zur Closed Beta

Sammlr braucht keinen weiteren breiten Featuresprint. Es braucht einen fokussierten Stabilisierungsschritt. Unter der Annahme eines erfahrenen Engineers und schneller rechtlicher/operativer Zuarbeit sind ungefähr **drei bis sechs Wochen** bis zu einer belastbaren Closed-Beta-Entscheidung plausibel; der Performancebefund ist dabei der größte Unsicherheitsfaktor.

Die Freigabe sollte evidenzbasiert erfolgen: P0-Punkte geschlossen, Lastprofil bestanden, Build sauber reproduziert, Browserflow grün, Restore und Alarm erprobt, Legaltexte freigegeben. Danach ist eine kleine Closed Beta sinnvoller als weitere interne Funktionsarbeit. Die wichtigste offene Produktfrage lautet jetzt nicht „Was fehlt noch?“, sondern „Verstehen echte Sammler den vorhandenen Workflow, und bleibt er unter realer Nutzung zuverlässig?“
