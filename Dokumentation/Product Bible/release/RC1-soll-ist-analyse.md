# SAMMLR SOLL-IST-ANALYSE RC1

Stand: 9. August 2026

Bewertungsgegenstand: technischer und produktseitiger Stand nach S38

Status dieses Dokuments: unabhängige Bestandsaufnahme, keine Sprintplanung

## 1. Auftrag, Maßstab und Evidenz

Diese Analyse vergleicht den nach S38 vorliegenden RC1-Stand mit der Product Bible, der Development Roadmap V1, der früheren Current-State Gap Analysis, den Sprintreports S00 bis S38, den RC1-Unterlagen sowie dem tatsächlich vorhandenen Code-, Schema-, Test- und UI-Stand.

Die Bewertung trennt bewusst vier Reifestufen:

- **RC-ready:** Ein intern reproduzierbarer, fachlich vollständiger Kandidat mit dokumentiertem Umfang.
- **Closed-Beta-ready:** Sicher und stabil genug für eine kleine, eingeladene Nutzergruppe unter enger Beobachtung.
- **Public-Beta-ready:** Für unbekannte Nutzer, höhere Last, Missbrauch und selbstständige Nutzung ausreichend robust.
- **1.0-ready:** Im realen Betrieb bewährt, rechtlich und operativ vollständig, konsistent bedienbar und dauerhaft wartbar.

Als nachgewiesen gelten insbesondere die zweimal erfolgreichen S38-Gesamtgates mit jeweils 529 Tests, der versionierte Migrationsstand V0012, die abgeschlossenen Fachsprints und die dokumentierten Release-Artefakte. Nicht als nachgewiesen gelten Dinge, die nur durch Unit-/Flask-Client-Tests oder Dokumentation belegt sind, aber noch keinen echten Browser-, Mehrnutzer- oder Produktionsbetrieb durchlaufen haben.

Diese Analyse hat keine Anwendung, Datenbank, Migration oder Tests verändert. Sie basiert auf statischer Inspektion und den vorhandenen Abnahmeprotokollen; das Gesamtgate wurde für diese reine Analyse nicht erneut ausgeführt.

## 2. Gesamturteil

Sammlr ist **fachlich RC-ready**, aber **noch nicht Closed-Beta-ready**. Die Roadmap hat aus einem funktionalen Prototyp eine ungewöhnlich breite, abgesicherte Tauschanwendung gemacht: konsistentes Inventory, Lifecycle, Reservierung, Versand, Empfang, Problemfälle, Matching, Smart Requests, Notifications, operative Home, Privacy, Community, Ratings, Security, Betrieb und Datenexport sind vorhanden und regressionstechnisch stark geschützt.

Der Engpass ist nicht mehr fehlende Kernfunktionalität. Er liegt in der Industrialisierung des vorhandenen Produkts:

- Die S35-Lastmessung weist bei Sammlung, Album, Stickerwall, Tauschbörse, Dealansicht und Notifications Antwortzeiten über fünf Sekunden beziehungsweise Timeouts aus; Suche und Profil liegen ebenfalls über einer Sekunde.
- Der Quellstand ist kein sauber eingefrorenes Release-Artefakt: unversionierte Abhängigkeiten, viele Arbeitsbaumartefakte und lokale Datenbank-/Backupkopien erschweren eine bitgenaue Reproduktion.
- Die Anwendung deklariert Foreign Keys, aktiviert deren Durchsetzung aber in normalen SQLite-Verbindungen nicht erkennbar zentral.
- Die automatisierten Tests sind breit, aber überwiegend auf Service- und Flask-Testclient-Ebene. Ein echter Browser-End-to-End-Nachweis für die wichtigsten Mehrnutzerabläufe fehlt.
- Rechtliche Texte sind ausdrücklich funktionale Entwürfe, und Betriebsüberwachung/Alarmierung ist als Schnittstelle vorbereitet, aber noch nicht als realer Dienst nachgewiesen.

Das sind lösbare Stabilisierungsaufgaben, keine notwendige Neuerfindung des Produkts. Ein kleiner geschlossener Beta-Kreis ist nach Abarbeitung der P0-Punkte realistisch; eine öffentliche Beta benötigt darüber hinaus P1-Härtung und echte Nutzungsdaten.

## 3. Perspektive A – Nutzer und Sammler

### 3.1 Onboarding und erster Erfolg

**Soll:** Ein neuer Nutzer versteht ohne Vorwissen, was Sammlr leistet, legt schnell eine Sammlung an und erlebt innerhalb weniger Minuten einen ersten sichtbaren Fortschritt.

**Ist:** Registrierung und Login sind schlank. Empty States führen grundsätzlich zu Aktionen, und die Sammlung ist der klare linke Hauptbereich. Ein geführtes Onboarding, eine kurze Erklärung des Sammlr-Modells und ein expliziter „erster Erfolg“ sind jedoch nicht vorhanden. Das aktuelle Produkt setzt voraus, dass Nutzer Album, Stickerwall, Papierliste, Tradepool und Verfügbarkeitsbegriffe selbst erschließen.

| Problem | Schweregrad | Nutzerwirkung | Konkretes Beispiel | Empfehlung | Beta-Blocker |
|---|---|---|---|---|---|
| Kein geführter Ersteinstieg | Hoch | Abbruch vor dem ersten Sammlungswert | Nach Registrierung landet der Nutzer in einer operativen Home ohne erklärten nächsten Gesamtweg | Einen kurzen, überspringbaren Erstlauf von Albumwahl bis erstem Mengen-Eintrag konzipieren; keine Fachlogik duplizieren | Vor Public Beta, nicht zwingend vor eng begleiteter Closed Beta |
| Fachbegriffe werden früh vorausgesetzt | Mittel | Unsicherheit über Bestand, Doppelte, „unterwegs“ und Tradepool | Privacy/Tradepool und Bestandskonzepte erscheinen, bevor ihr Nutzen erlebt wurde | Kontextuelle Kurztexte und progressive Offenlegung in Nutzertests validieren | Nein |
| Passwortanforderungen sind nicht als klarer Produktvertrag sichtbar | Mittel | Schwache Passwörter oder Frust durch unklare Erwartungen | Registrierung prüft im sichtbaren Stand im Wesentlichen auf vorhandene Eingabe | Verbindliche Mindestregeln und verständliche Rückmeldung vor Public Beta festlegen | Vor Public Beta |

### 3.2 Navigation und Orientierung

**Soll:** Sammlung, sammlr. und Tauschen bilden dauerhaft die drei Hauptbereiche; Profil und Notifications bleiben persönliche Headeraktionen. Rückwege erhalten den fachlichen Kontext.

**Ist:** Dieses Modell ist nach der S31-Korrektur und S37 konsistent definiert. Headervarianten, Safe Area, aktive Zustände und Deal-Deep-Links sind automatisiert abgesichert. Das ist eine klare Stärke. Die verbleibende Unsicherheit liegt weniger in der Informationsarchitektur als im fehlenden echten Browsernachweis über alle Viewports und in der hohen Dichte einzelner Zielseiten.

| Problem | Schweregrad | Nutzerwirkung | Konkretes Beispiel | Empfehlung | Beta-Blocker |
|---|---|---|---|---|---|
| Browserrealität nicht vollständig automatisiert geprüft | Hoch | Fehler bei Fokus, Modal, Sticky Header oder mobiler Navigation können trotz grünem Flask-Test unentdeckt bleiben | S37 prüft HTML-Verträge und dokumentierte Smokes, aber keine Playwright-/Selenium-End-to-End-Strecke | Die drei Hauptwege auf 390/430 px und Desktop in echten Browsern automatisieren | Vor Closed Beta |
| Detailseiten sind informationsdicht | Mittel | Nutzer verlieren die primäre nächste Aktion aus dem Blick | Dealansicht kombiniert Timeline, Status, Versand, Empfang, Probleme, Bewertung und Historie | Mit Nutzern die Aktionshierarchie prüfen; nur Darstellung vereinfachen, Lifecycle unverändert lassen | Vor Public Beta |

### 3.3 Sammlung und Stickerverwaltung

**Soll:** Mengen, Doppelte, Fortschritt, Transit und Filter sind schnell verständlich und konsistent. Die Stickerwall bleibt die verlässliche visuelle Wahrheit.

**Ist:** Der fachliche Vertrag ist stark: zentraler Read-/Write-Service, Availability Snapshot, Guards, Transitkennzeichnung, Golden-Master- und Regressionstests. Fehlende Sticker bleiben trotz Transit korrekt fehlend; physischer Bestand und „unterwegs“ werden getrennt dargestellt. Mengen, Undo, Batch und Papierlisten sind geschützt.

| Problem | Schweregrad | Nutzerwirkung | Konkretes Beispiel | Empfehlung | Beta-Blocker |
|---|---|---|---|---|---|
| Sammlung und Stickerwall brechen unter dem verbindlichen S35-Datensatz ein | Kritisch | Kernfunktion ist langsam oder nicht nutzbar | Sammlung, Album und Stickerwall überschreiten bei 20 parallelen Requests fünf Sekunden beziehungsweise laufen in Timeouts | N+1-Abfragen, wiederholte Snapshots und Renderingmenge messen und gezielt reduzieren; Baseline unverändert wiederholen | Ja, vor jeder Beta |
| Albumseite überlädt den Einstieg | Mittel | Bestandsarbeit beginnt erst nach Privacy-, Tradepool- und Metainformationen | Im Referenzscreen nimmt die Verwaltungsbox viel Raum vor der Stickerwall ein | Reihenfolge und progressive Offenlegung in realen Tests prüfen | Nein |
| Mehrere eigene Instanzen desselben Albums und ein albumunabhängiger Freipool fehlen | Niedrig für RC1, strategisch relevant | Power-Collector können reale physische Sammlungen nur näherungsweise abbilden | Bestand bleibt an die aktuelle Nutzer-Album-Struktur gekoppelt | Als zukünftige Modellentscheidung behandeln, nicht vor Beta in den stabilen Inventory-Vertrag eingreifen | Nein |

### 3.4 Tauschen und Deal-Lifecycle

**Soll:** Nutzer verstehen jederzeit, was vereinbart, reserviert, versendet, empfangen, problematisch oder abgeschlossen ist. Keine Doppelbuchung und keine unberechtigte Aktion ist möglich.

**Ist:** Der Trade-Kern ist die größte Produktstärke. Von Papierliste und manueller Anfrage über konfliktfreie Smart-Pakete bis zu Reservierung, Versand je Seite, Teil-/Problemempfang, Auflösung, Abschluss und Bewertung ist der Lifecycle detailliert modelliert. Idempotenz, Berechtigungen und Inventory-Invarianten sind umfangreich getestet. Erwartete Lieferung und tatsächlicher Bestand wurden in S18.1 klar getrennt.

| Problem | Schweregrad | Nutzerwirkung | Konkretes Beispiel | Empfehlung | Beta-Blocker |
|---|---|---|---|---|---|
| Zentrale Tradeansichten überschreiten die Lastziele deutlich | Kritisch | Anfrage- und Dealbearbeitung wirkt defekt; Doppelaktionen werden wahrscheinlicher | Tauschbörse und Dealansicht timeouten im S35-Profil | Read-Pfade bulkfähig machen, Query-Indizes ergänzen, danach 20er-Parallelität erneut messen | Ja, vor jeder Beta |
| Hohe Zustands- und Begriffsdichte | Hoch | Seltene Nutzer wissen nicht, welche Aktion jetzt zulässig oder notwendig ist | „reserviert“, „Versand läuft“, „teilweise erhalten“, „Problem offen“, „closed_with_problem“ und Auflösung erscheinen in einem langen Workflow | Eine dominante nächste Aktion und kurze Zustandserklärung pro Phase im Browser-/Nutzertest validieren | Vor Public Beta; für Closed Beta eng begleiten |
| Legacy-Anfrage und Lifecycle-Trade sind technisch parallel vorhanden | Für Nutzer mittelbar hoch | Randfälle können unterschiedliche Ziel-IDs, Status oder Historien erzeugen | Vor Annahme ist das Ziel `trade_request`, danach `trade`; Kompatibilität bleibt absichtlich bestehen | Keine spontane Migration; Übergangsvertrag vollständig beobachten und langfristig kontrolliert abbauen | Nein, solange Regression grün und Monitoring vorhanden |

### 3.5 Community, Profil und Vertrauen

**Soll:** Nutzer finden andere Sammler, verstehen Privatsphäre, tauschen nur mit zulässigen Kontakten und können Vertrauen durch Profil, Aktivitäten und Bewertungen einschätzen.

**Ist:** Profile, Privacy, Tradepool, Freunde, Blocks, Suche, Aktivität und aggregierte Ratings sind vorhanden. Blockierungen greifen auf Freundschaft und offene Anfragen durch. Ratings sind an vollständig abgeschlossene Lifecycle-Trades gebunden. Das ist für einen RC überraschend vollständig.

| Problem | Schweregrad | Nutzerwirkung | Konkretes Beispiel | Empfehlung | Beta-Blocker |
|---|---|---|---|---|---|
| Community-Erlebnis ist funktional, aber wenig selbsterklärend | Mittel | Nutzer finden den Wert von Freunden, Coverage und Top Match nicht unmittelbar | Suche ist zielgerichtet, Profilkennzahlen und Aktionen sind dichter als eine klassische soziale Oberfläche | Begriffe und Primäraktionen mit einer kleinen Beta-Kohorte testen | Nein |
| Vertrauen beruht auf wenigen Signalen | Mittel | Neue Nutzer können Gegenüber schwer einschätzen | Es gibt aggregierte Bewertung, erfolgreiche Trades und Aktivität, aber keine Einzelhistorie oder Moderationssignale | Zunächst reale Missbrauchs- und Supportfälle beobachten; keine vorschnellen neuen Social Features | Nein |
| Kein administratives Moderations-/Support-Backoffice | Hoch für öffentliche Reichweite | Konflikte oder Missbrauch lassen sich nur operativ/manuell behandeln | S35 definiert nur freiwillige Deaktivierung und Anonymisierung, ausdrücklich keine Admin-Sperre | Vor Public Beta einen minimalen Support- und Incidentprozess festlegen; UI erst bei belegtem Bedarf | Vor Public Beta |

### 3.6 Home und Notifications

**Soll:** Home projiziert maximal fünf reale Aufgaben, ohne zweite Tradezentrale zu werden. Notifications sind typisiert, dedupliziert, zielgerichtet und als Historie verständlich.

**Ist:** Die operative Projektion, Prioritäten, stabile Sortierung, Typed Notifications, Badge, Historie und sichere Ziele sind sauber getrennt. Das ist konzeptionell stark. Gleichzeitig zeigen die Referenzscreens sichtbare Platzhalter und die Notifications-Seite ist unter Last ein Blocker.

| Problem | Schweregrad | Nutzerwirkung | Konkretes Beispiel | Empfehlung | Beta-Blocker |
|---|---|---|---|---|---|
| Sichtbare Platzhalter wirken unfertig | Mittel | RC wirkt wie eine Demo statt ein bewusst fokussiertes Produkt | „Freunde kommen später.“ und „Noch keine Sammlr News.“ belegen prominente Home-Flächen | Für Beta entweder bewusst als kleine Empty States gestalten oder aus der operativen Home entfernen; keine Fake-Inhalte | Vor Public Beta |
| Notification-Historie ist bei Last nicht zuverlässig erreichbar | Kritisch | Nutzer übersehen Aufgaben oder hält Badge/History für defekt | S35: Notifications über fünf Sekunden/Timeout | Lazy-Projektion, Zählung und History-Query messen; passende zusammengesetzte Indizes und Bulkpfade prüfen | Ja, vor jeder Beta |
| Read und operative Aufgabe können mental vermischt werden | Mittel | „gelesen“ wird als „erledigt“ interpretiert | Badge/History und Home-Aufgabe besitzen bewusst verschiedene Semantik | Mikrotexte und Zustandswechsel in Nutzertests prüfen | Nein |

### 3.7 Account, Datenschutz und Sicherheitserleben

**Soll:** Deaktivierung, Reaktivierung, Anonymisierung und Export sind sicher, verständlich und ohne Datenleck. Nutzer erkennen irreversible Schritte.

**Ist:** Re-Authentifizierung, doppelte Anonymisierungsbestätigung, Trade-Guards, Sessioninvalidierung, Accountzustände und JSON-Export sind umgesetzt. Produktionssecret, scrypt, CSRF, POST-only-Mutationen, Throttling und Sanitized Logging sind gute Grundlagen.

| Problem | Schweregrad | Nutzerwirkung | Konkretes Beispiel | Empfehlung | Beta-Blocker |
|---|---|---|---|---|---|
| Datenschutz und Impressum sind keine juristische Endfassung | Kritisch für externe Freigabe | Rechtliche Unsicherheit für Betreiber und Nutzer | S36 kennzeichnet die Texte ausdrücklich als technisch/funktional | Vor Einladung externer Tester Rechtsgrundlagen, Verantwortliche, Zwecke, Empfänger, Löschung und Betroffenenrechte final prüfen lassen | Ja, vor jeder externen Beta |
| Fehlerpfade sind teilweise technisch statt produktnah | Mittel | Nutzer erlebt bei irreversiblen Aktionen rohe Fehlerseiten | Kontooperationen können 403/409 als schlichte Antwort liefern | Bestehende Fehlercodes in konsistente Formfeedbacks überführen, ohne Fachlogik zu ändern | Vor Public Beta |
| Export ist synchron | Niedrig im aktuellen Umfang | Sehr große Konten könnten warten oder abbrechen | Ein JSON-Dokument wird im Request erzeugt | In Beta messen; erst bei realem Problem asynchronisieren | Nein |

## 4. Perspektive B – Entwickler und Architektur

### 4.1 Architekturstatus

Die Architektur ist nicht mehr der ungetestete Monolith der alten Gap Analysis. Es existieren heute kanonische Services für Inventory Read/Write, Availability, Guard, Lifecycle, Reservations, Shipping, Receipt, Problems, Snapshot, Coverage, Top Match, Smart Requests, Notifications, Home, Privacy, Profiles, Community, Ratings, Auth, Account und Export. DTOs und Contracts verhindern an vielen Stellen zweite Wahrheiten.

Gleichzeitig ist die Flask-Einstiegsdatei auf rund 10.848 Zeilen und 249 Top-Level-Funktionen gewachsen. Die größte Route umfasst etwa 1.330 Zeilen, weitere zentrale Routen 270 bis 635 Zeilen. Services reduzieren Fachduplikation, aber Routing, Query-Orchestrierung, HTML und JavaScript bleiben stark gekoppelt. Die Architektur hat ihre Fachkerne stabilisiert, nicht jedoch ihre Präsentations- und Read-Pfade industrialisiert.

### 4.2 Technische Befunde

| Priorität | Befund | Technisches Risiko | Empfehlung | Vor Beta beheben? |
|---|---|---|---|---|
| P0 | S35-Performanceziel bei sechs Kernpfaden verfehlt, Suche/Profile ebenfalls >1 s | Timeouts, Lock-Contention und nicht nutzbare Kernwege unter nur 20 parallelen Requests | Queryprofile je Route erstellen; N+1-Aufrufe, wiederholte Snapshots, große Renderpfade und fehlende Indizes gezielt beheben; identischen Baseline-Datensatz wiederverwenden | Ja |
| P0 | Normale SQLite-Verbindungen aktivieren `PRAGMA foreign_keys=ON` nicht zentral | Deklarierte Foreign Keys werden im laufenden Produkt nicht zuverlässig erzwungen; schleichende Inkonsistenz möglich | Eine kanonische Connection-Factory mit Foreign Keys, Timeout und dokumentierten Transaktionsregeln etablieren; Regression und Integrity Check ergänzen | Ja |
| P0 | Releasequellstand ist nicht sauber eingefroren | 176 Arbeitsbaumartefakte, lokale DBs, Backups, Cachedateien und historische Kopien erschweren Audit, Rollback und Reproduktion | Einen sauberen, unveränderlichen RC-Artefaktstand mit klarer Ignore-/Packaging-Regel erzeugen; Nutzeränderungen nicht blind löschen | Ja |
| P0 | Python-Abhängigkeiten sind unversioniert (`Flask`, `gunicorn`) | Neuinstallation kann andere Versionen und anderes Verhalten liefern; Supply-Chain- und Rollbackrisiko | Verifizierten Dependency-Lock beziehungsweise vollständig gepinnte Runtime-Abhängigkeiten erzeugen und clean-install testen | Ja |
| P0 | Kein echter Browser-E2E-Nachweis für Kernworkflow | Templates, JS, Modals, Sticky Navigation, CSRF und Multiuser-Wechsel können trotz Flask-Tests regressieren | Kleines, stabiles Browsergate: Registrierung/Login, Sammlung, Anfrage, Annahme, Versand, Empfang, Problem, Notifications, Account | Ja |
| P0 | Rechtliche und operative Endabnahme nicht vollständig real belegt | Externe Tester ohne finale Datenschutzhinweise; Restore/Alarmierung möglicherweise nur dokumentiert | Juristische Freigabe plus echter Deploy-, Alert- und Restore-Drill in Zielumgebung | Ja |
| P1 | `webapp.py` bündelt Routing, Query-Orchestrierung, Rendering und Inline-JS | Hohe Änderungskopplung, schwere Reviews, langsame Fehlerlokalisierung | Nach Beta-Gate schrittweise nach Feature-Slices extrahieren; keine Big-Bang-Neuschreibung | Vor Public Beta teilweise |
| P1 | Lesepfade erzeugen wiederholt identische Snapshots/Coverage/Top-Match-Projektionen | CPU-/DB-Explosion mit Nutzer- und Albumzahl | Request-lokale Wiederverwendung und bulkfähige Service-APIs konzipieren, ohne dauerhaften Cache oder zweite Wahrheit | Ja, soweit für P0-Performance nötig |
| P1 | `trade_requests` besitzt keine erkennbaren Query-Indizes; Notifications keinen offensichtlichen Empfänger/Ungelesen/Zeit-Index | Full scans in zentralen Listen und Lazy-Projektionen | Reale Querypläne prüfen und ausschließlich belegte zusammengesetzte/partielle Indizes ergänzen | Ja, soweit Baseline betroffen |
| P1 | SQLite-Konfiguration hat keinen zentral sichtbaren `busy_timeout`-/WAL-Vertrag | Threaded Gunicorn und lazy GET-Projektionen können `database is locked` erzeugen | Zielbetrieb messen; Busy Timeout und Journalstrategie explizit festlegen, Transaktionen kurz halten | Vor Public Beta; vor Closed Beta Lasttest |
| P1 | Dualität aus Legacy-`trade_requests`/JSON und Lifecycle-Modell bleibt | Zwei Identitäten und Kompatibilitätszweige erhöhen Randfallrisiko | Übergangsvertrag dokumentiert lassen, Telemetrie auf Kompatibilitätspfade; später kontrollierter Abbau | Nein, nicht vor Beta erzwingen |
| P1 | Rund 178 Schema-/Kompatibilitätsprüfungen verteilen sich über Codepfade | Laufzeitkosten, schwer verständliche Versionslogik, tote Zweige | Nach sauberer Mindestversion auf Migrationsversion statt Ad-hoc-Introspektion konsolidieren | Vor 1.0 |
| P1 | Security-Härtung ist stark, aber Response-Header/CSP und Passwortpolicy sind nicht als vollständiger Vertrag nachweisbar | Clickjacking/XSS-Schadensradius und schwache Zugangsdaten | Header in Zieldeployment prüfen und minimalen Policy-Vertrag definieren; CSP schrittweise wegen Inline-Code | Vor Public Beta |
| P1 | `current_user_id()` besitzt einen Fallback auf Nutzer 1 | Künftige falsch geschützte Route könnte fail-open lesen oder schreiben | Explizit fail-closed machen, nachdem alle öffentlichen Aufrufer geprüft sind | Vor Public Beta |
| P1 | Development-Server bindet bei direktem Start mit Debug auf `0.0.0.0`; Debug-Seeds sind authfrei im Development-Modus | Lokales LAN kann Entwicklungsaktionen erreichen | Dev-Defaults auf Loopback, deutliche Warnung und dokumentierte Opt-in-Freigabe begrenzen | Vor Public Beta, lokal früher sinnvoll |
| P2 | CSS umfasst rund 10.426 Zeilen, 1.805 `!important`, viele Rohwerte und wiederholte Selektoren | Override-Kaskaden, visuelle Regression und langsame Weiterentwicklung | Nach visueller Baseline in Seitengruppen konsolidieren; Tokenvertrag messen, nicht global neu schreiben | Quality-/UI-Phase |
| P2 | Erfolgs-/Fehlertyp wird teilweise aus deutschen Textschlüsselwörtern abgeleitet | Textänderung kann Semantik/Farbe unbeabsichtigt ändern | Strukturierte Feedback-DTOs mit explizitem Typ verwenden | Quality-/UI-Phase |
| P2 | Tests sind breit, aber stark implementierungsnah | Quelltext-Assertions können Refactoring blockieren, während echte Browserfehler fehlen | Contract-, Integration- und Browserpyramide ergänzen; Source-Assertions nur für harte Securityverträge behalten | Quality-/UI-Phase |
| P2 | Tausende ResourceWarnings und zwei SyntaxWarnings sind dokumentiert | Offene SQLite-Ressourcen verbergen Leaks; Warnrauschen normalisiert echte Fehler | Connection-Lifecycle in Tests und App schließen, ungültige Escape-Sequenzen korrigieren, Warnbudget null anstreben | Vor Public Beta |
| P2 | Historische Pythonkopien und tote Startup-/Schemahelfer liegen nahe am Produktcode | Falsche Importe, Securityscanner-Rauschen, Entwicklerverwechslung | Nach sauberem Archivnachweis aus dem Laufzeitpfad entfernen oder extern archivieren | Quality-/Maintenance-Phase |
| P2 | Externe Observability ist nur providerneutral vorbereitet | Fehler werden geloggt, aber nicht zwingend bemerkt | Error Collector, Uptimecheck, Alertkanal und Verantwortlichkeit real verbinden | Vor Public Beta |
| P3 | Stored `duplicates` bleibt neben `quantity` eine redundante Darstellung | Invarianten müssen dauerhaft synchron gehalten werden | Solange zentrale Services/Trigger greifen nicht migrieren; langfristig abgeleiteten Wert prüfen | Später |
| P3 | Keine albumunabhängige physische Besitzschicht | Künftige Multi-Album-/Transferfälle bleiben teuer | Erst mit validierter Product-Bible-Erweiterung modellieren | Phase 2 |

### 4.3 Datenbank und Migrationen

**Stärken:** V0001 bis V0012 sind versioniert; Up/Down-Verträge, Fail-closed-Backouts, additive S33-Constraints und Fixture-/Produktionsschutz sind umfassend getestet. Inventory- und Lifecycle-Invarianten besitzen Service- und Contracttests. Backups und Integritätsprüfungen sind dokumentiert.

**Risiken:** Der produktive Connection-Vertrag ist der wesentliche Restpunkt. Foreign-Key-Deklarationen helfen nur, wenn jede Verbindung ihre Durchsetzung aktiviert. Zudem passen Query-Indizes noch nicht sichtbar zum inzwischen großen Read-Modell. Die lokale Entwicklungsdatenbank lag in mehreren Reports hinter dem jeweils aktuellen Schema; für RC1 wurde das durch temporäre Testkopien abgesichert, nicht durch einen einheitlichen lokalen Stand.

**Soll:** Eine einzige Connection-Factory, eine explizite Mindestmigration, belegte Query-Indizes, kurze Transaktionen und reproduzierbare Integrity-/FK-Checks. Keine neue Fachmigration ohne einen konkreten Befund.

### 4.4 Tests und Qualitätsnachweis

529 erfolgreiche Tests zweimal sind ein starkes Signal. Die Suite deckt Migration, Idempotenz, Berechtigung, Inventory, Lifecycle, Problems, Notifications, Privacy, Security, Export und UI-Verträge ungewöhnlich breit ab. Produktivdatenbank und kanonische Fixture werden durch Hashguards geschützt.

Die Suite enthält jedoch überwiegend `unittest`, Service- und Flask-Testclient-Prüfungen. Es gibt keinen erkennbaren echten Browserrunner und keine formale Accessibility-Engine. Manuelle Smokeverträge sind dokumentiert, aber nicht dasselbe wie ein reproduzierbarer externer Abnahmelauf. Außerdem schwächen ResourceWarnings den Aussagewert „vollständig sauber“.

### 4.5 Security und Betrieb

**Bereits stark:** Production-Secret fail-closed, temporäres Development-Secret, scrypt mit Legacy-Upgrade, Auth-Versionierung, Login-Throttle, CSRF, POST-only-Mutationen, Debug-Gates, sichere Cookies, Request-ID, Logsanitizing, Healthcheck, Gunicornvertrag, Backup/Restore-Dokumentation und Datenexport mit Re-Authentifizierung.

**Vor externer Freigabe offen:** finaler Legal Review, echte Zielumgebungs-Alarme, Restore-Drill, Response-Headerprüfung, Passwortpolicy, Fail-closed User-ID-Helfer, sauberer Dependency-/Build-Stand und nachgewiesene SQLite-Integrität unter Last.

## 5. Perspektive C – Produkt und Release

### 5.1 Reifegrade

| Reifegrad | Urteil heute | Begründung | Erforderlicher nächster Nachweis |
|---|---|---|---|
| RC-ready | **Ja, fachlich und testseitig** | Vollständiger definierter Scope, V0012, 529 Tests zweimal, S38-Artefakte, keine bekannten funktionalen Kernregressionen | Sauberen, gepinnten und unveränderlichen RC-Artefaktstand herstellen |
| Closed-Beta-ready | **Nein** | Kritische Performancepfade, fehlender Browser-E2E-Nachweis, FK-Laufzeitvertrag, Legal-/Ops-Abnahme offen | Sämtliche P0-Punkte schließen und kleine reale Kohorte unter Monitoring abnehmen |
| Public-Beta-ready | **Nein** | Zusätzlich Onboarding, Missbrauch/Support, Securityheader/Policy, Warnungsfreiheit, Monitoring und UX-Verständlichkeit offen | P1 schließen, Closed-Beta-Daten auswerten, Lastziel mit Reserve bestehen |
| 1.0-ready | **Nein** | Noch keine reale Betriebsbewährung, Support-/Incidentdaten oder validierte Nutzungsqualität | Stabilitätszeitraum, Supportprozess, Analytics/Feedback, P2-Schuldenplan und bewusste Scopeentscheidung |

### 5.2 Geschlossene Beta oder weitere interne Qualität?

Heute sollte **noch keine externe Closed Beta** gestartet werden. Sammlr braucht aber auch keinen weiteren breiten Feature-Sprint. Der sinnvolle nächste Schritt ist ein eng begrenztes Release-Hardening mit messbaren Gates:

1. Kernpfade unter dem S35-Datensatz zuverlässig unter das vereinbarte Ziel bringen.
2. Runtime-Integrität und SQLite-Verbindungsvertrag schließen.
3. Einen sauberen, gepinnten RC-Build erzeugen.
4. Browser-E2E, Zieldeployment, Alert und Restore real ausführen.
5. Rechtliche Texte freigeben und anschließend fünf bis zwanzig eingeladene Nutzer auf reale Kernreisen setzen.

Danach ist eine geschlossene Beta sinnvoller als weitere interne Funktionsarbeit. Mehr Features würden die wichtigste offene Evidenz nicht liefern: Verstehen echte Sammler den Workflow, und hält das System deren parallele Nutzung aus?

## 6. Vergleich mit der alten Current-State Gap Analysis

| Alter Befund | Alte Schwere | Status heute | Geschlossen durch | Restrisiko |
|---|---:|---|---|---|
| Keine automatisierte Testbasis | Kritisch | Geschlossen | S01–S03, danach fortlaufende Regression bis S38 | Browser-E2E und Warnungsfreiheit fehlen |
| Bestandslogik verteilt und uneinheitlich | Kritisch | Fachlich geschlossen | S08–S12, S19 | Read-Performance und redundantes `duplicates` bleiben |
| Keine Reservierungen | Kritisch | Geschlossen | S14 | Last- und Parallelitätsverhalten weiter beobachten |
| Trade nur als flache Anfrage/JSON, kein echter Lifecycle | Kritisch | Weitgehend geschlossen | S13–S18.2 | Legacy-/Lifecycle-Dualität bleibt als Kompatibilitätsschicht |
| Keine Versand-/Empfangs-/Problemzustände | Hoch | Geschlossen | S15–S18.2 | UX-Komplexität und reale Nutzerverständlichkeit offen |
| Kein Smart Matching/keine Konfliktoptimierung | Hoch | Geschlossen | S19–S22 | Algorithmusqualität erst mit Echtdaten validiert |
| Home nur Sammelfläche statt operativer Projektion | Hoch | Geschlossen | S25 | Platzhalterflächen wirken unfertig |
| Notifications untypisiert und ohne sichere Ziele | Hoch | Geschlossen | S23–S24 | History-Performance und reale Alerting-Grenze offen |
| Profile, Privacy, Freunde, Blocks und Ratings fehlen | Hoch | Geschlossen | S26–S29 | Moderation/Support für öffentliche Reichweite fehlt |
| Navigation/Design inkonsistent | Hoch | Weitgehend geschlossen | S05–S07, S30–S31, S37 | CSS-Override-Schuld und echter Browsernachweis bleiben |
| Passwörter/Sessions/CSRF/GET-Mutationen unsicher | Kritisch | Weitgehend geschlossen | S32–S33 | Header/CSP, Passwortpolicy und User-ID-Fallback offen |
| Startup-Schemaänderungen statt Migrationen | Kritisch | Geschlossen | S13, V0001–V0012 | Verteilte Schema-Introspektion und tote Helfer bleiben |
| Keine Deployment-/Backup-/Restore-Grundlage | Hoch | Geschlossen als Architektur | S34, S38 | Reale Zielumgebungs- und Restoreübung nachweisen |
| Konto-Lifecycle und Datenexport fehlen | Hoch | Geschlossen | S35–S36 | Legal-Endfassung und Export unter Extremgröße messen |
| Monolithische `webapp.py` | Hoch | **Nicht geschlossen; größer geworden** | Services reduzieren Fachkopplung, aber keine Routenschichtung | 10.848 Zeilen, sehr große Routen, hohe Reviewkosten |
| CSS historisch gewachsen | Hoch | **Nur teilweise geschlossen** | S30–S31, S37 | 10.426 Zeilen und 1.805 `!important` zeigen weiter hohe Kaskadenschuld |
| Keine explizite physische/albumspezifische Besitztrennung | Hoch strategisch | Vertrag dokumentiert, Modell nicht ersetzt | S08–S12 | Multi-Album-/Freipool-Szenarien bleiben später |
| Fehlende Constraints/FKs | Kritisch | Schema deutlich gehärtet, Laufzeit teilweise offen | S13, S27–S35 | Foreign-Key-Durchsetzung pro Verbindung ist nicht zentral belegt |
| Historische Appkopien im Repository | Mittel | Nicht geschlossen | — | Verwechslung, Scannerrauschen, tote Syntaxfehler |

### 6.1 Neue RC1-Befunde, die vor der Roadmap nicht sichtbar waren

1. **Skalierungsgrenze ist jetzt gemessen statt vermutet.** Die reicheren Services haben korrekte Ergebnisse, aber zentrale Read-Pfade skalieren im verbindlichen S35-Datensatz nicht.
2. **Fachliche Services sind sauberer als die Webschicht.** Die eigentliche Restmonolithik liegt in Route, Query-Orchestrierung, HTML und JavaScript.
3. **Release-Reproduzierbarkeit hinkt der Testreife hinterher.** Ein grünes Gate ersetzt keinen gepinnten, sauberen Build.
4. **SQLite-Integrität ist im Schema stärker als im Connection-Vertrag.** Deklarierte FKs ohne verbindliches Laufzeit-PRAGMA sind eine Scheinsicherheit.
5. **Qualität wird durch Warnrauschen relativiert.** Mehr als zweitausend ResourceWarning-Ausgaben im Gate deuten auf offene Connection-Lebenszyklen.
6. **UI-Foundation und CSS-Bestand divergieren.** Das Tokensystem existiert, aber historische Override-Schichten dominieren weiterhin die Wartbarkeit.
7. **Das Produkt braucht jetzt Nutzerevidenz statt zusätzliche Fachbreite.** Die offene Frage ist Verständnis und Zuverlässigkeit, nicht Featureanzahl.

## 7. Priorisierter Maßnahmenkatalog

Maximal 20 Maßnahmen, bewusst ohne neue Sprintnummern:

### P0 – vor jeder externen Beta

1. **Performanceblocker schließen:** Sammlung, Album, Stickerwall, Tauschbörse, Dealansicht und Notifications unter identischem S35-Datensatz und 20 parallelen Requests ohne Fehler/Timeout; P95 unter 500 ms anstreben, Abweichungen explizit freigeben.
2. **SQLite-Laufzeitvertrag härten:** Foreign Keys auf jeder Verbindung aktivieren, Lock-/Timeoutstrategie festlegen, Integrity- und FK-Checks als Gate ausführen.
3. **Sauberes RC-Artefakt erzeugen:** Produktquellen von lokalen DBs, Backups, Cache und historischen Arbeitskopien trennen; exakt nachvollziehbaren Buildstand herstellen.
4. **Abhängigkeiten pinnen:** Python- und Runtime-Abhängigkeiten vollständig festschreiben, Clean-Install und Start mit Python 3.13 nachweisen.
5. **Echten Browser-Kernflow automatisieren:** Zwei Nutzer, Sammlung, Anfrage, Annahme, Versand, Empfang, Problem, Notifications und Accountaktionen auf Mobile/Desktop.
6. **Releasebetrieb real proben:** Zieldeployment, Healthcheck, externer Fehleralarm, Backup und isolierter Restore mit Verantwortlichkeit und Zeitmessung.
7. **Rechtliche Freigabe abschließen:** Datenschutzerklärung, Impressum und Exporthinweise für den tatsächlichen Betreiber und Betaumfang prüfen lassen.

### P1 – vor Public Beta

8. **Onboarding/First Value validieren:** Neunutzer ohne Anleitung beobachten und den kürzesten Weg zum ersten Album und ersten Mengenstand verständlich machen.
9. **Trade-UX verständlich machen:** Pro Lifecyclephase eine dominante nächste Aktion und klare Erklärung; keine Fachzustände entfernen.
10. **Query- und Servicezugriffe bulkfähig machen:** belegte Indizes, Request-lokale Wiederverwendung, keine zweite Availability-Wahrheit.
11. **Security-Restpunkte schließen:** Passwortpolicy, Response-Header/CSP-Plan, fail-closed User-ID und sichere Development-Bindung.
12. **Monitoring und Support operationalisieren:** Error Collector, Uptime, Alarmkanal, Incident-Owner und minimaler Moderationsprozess.
13. **Warnungsbudget auf null senken:** SQLite-Verbindungen sauber schließen und SyntaxWarnings beseitigen.
14. **Unfertige Home-Signale bereinigen:** Platzhalter entweder bewusst reduzieren oder als klare, hilfreiche Empty States positionieren.
15. **Closed-Beta-Evidenz auswerten:** Task Completion, Abbruchstellen, Supportfälle, Missbrauch und subjektives Vertrauen dokumentieren, bevor Reichweite erhöht wird.

### P2 – Quality-/UI-Phase

16. **CSS schrittweise konsolidieren:** Tokenverstöße, redundante Selektoren und `!important` pro Seitengruppe abbauen, visuelle Baseline behalten.
17. **Webschicht in Feature-Slices zerlegen:** große Routen, Inline-HTML und JS schrittweise trennen; keine Big-Bang-Neuschreibung.
18. **Feedback und Formfehler strukturieren:** explizite Success/Warning/Error/Info-Typen statt Textheuristik.
19. **Testpyramide neu balancieren:** weniger fragile Source-Assertions, mehr Contract-, Browser- und Accessibility-Prüfung.

### P3 – später / Phase 2

20. **Sammlungsmodell nur bei validiertem Bedarf erweitern:** mehrere Albuminstanzen, albumunabhängiger Freipool, Transfers sowie reichere Community-/Media-Funktionen nicht in die Beta-Härtung mischen.

## 8. Top 10 der nächsten Arbeiten

1. Performance der sechs blockierten Kernpfade messbar stabilisieren.
2. SQLite-Foreign-Keys und Connection-/Lock-Vertrag produktiv erzwingen.
3. Gepinnten, sauberen und unveränderlichen RC-Build herstellen.
4. Browser-E2E für den vollständigen Zwei-Nutzer-Tradeflow etablieren.
5. Zieldeployment, Monitoring, Backup und Restore real abnehmen.
6. Datenschutz-/Impressumsinhalte juristisch finalisieren.
7. Ersten Nutzerweg bis zum ersten Sammlungswert testen und vereinfachen.
8. Trade-Lifecycle mit echten Sammlern auf Verständnis und Aktionssicherheit testen.
9. Resource-/SyntaxWarnings beseitigen und Gate wirklich warnungsfrei machen.
10. Nach P0 mit einer kleinen, begleiteten Closed-Beta-Kohorte echte Evidenz sammeln.

## 9. Stärken und Nicht-anfassen-Bereiche

### Stärken

- **Inventory-Vertrag:** zentrale Read-/Write-/Availability-/Guard-Schicht, Transit und Invarianten.
- **Trade-Lifecycle:** Reservierung, Versand, Empfang, Teilmengen, Probleme, Idempotenz und Historie.
- **Smart-Trade-Fundament:** Snapshot, Coverage, deterministische konfliktfreie Optimierung und Recheck.
- **Operative Projektionen:** Home-Aufgaben und Notifications sind von Historie und Fachmutation sauber getrennt.
- **Privacy und Community:** Sichtbarkeit, Tradepool, Freunde, Blocks und Ratings greifen fachlich ineinander.
- **Security-Fundament:** scrypt, CSRF, POST-only, Secret-Gate, Throttle, Sessions und Logsanitizing.
- **Regressionstiefe:** 529 Tests, Hashguards, Migrationstests und doppelte Gates.
- **Klare Hauptnavigation:** Sammlung, sammlr. und Tauschen; persönliche Aktionen ausschließlich im Header.

### Nicht anfassen, solange kein belegter Fehler vorliegt

- Keine neue Inventory-Wahrheit neben Snapshot und kanonischen Services.
- Keine Neuschreibung der Trade-State-Machine oder des Legacy-Adapters vor Beta.
- Keine automatische Anpassung veränderter Smart-Pakete.
- Keine Vermischung von Notification-Historie und operativer Home.
- Keine neue Bottom Navigation oder zweite Position für Profil/Notifications.
- Keine Big-Bang-CSS- oder `webapp.py`-Neuschreibung.
- Keine Schemaerweiterung für hypothetische Phase-2-Funktionen.
- Keine Performanceoptimierung ohne Profil, Queryplan und identischen Vorher-/Nachher-Test.
- Keine neuen Social-, Chat-, Scanner- oder Marketplace-Features vor Stabilisierung.

## 10. Realistische Distanz zur Closed Beta

Die Distanz ist **überschaubar, aber nicht nur kosmetisch**. Unter der Annahme eines erfahrenen Engineers und schneller rechtlicher/operativer Zuarbeit erscheint ein fokussierter Zeitraum von ungefähr **drei bis sechs Wochen** für die P0-Härtung realistisch. Diese Schätzung ist keine Zusage: Der Performancebefund kann je nach Queryprofil kleiner oder größer ausfallen.

Das Freigabekriterium sollte nicht ein Datum sein, sondern folgende Evidenz:

- alle P0-Punkte geschlossen,
- Kernpfade unter dem verbindlichen Lastprofil stabil,
- sauberer Build aus leerer Umgebung reproduziert,
- echter Browserflow mit zwei Nutzern grün,
- Zieldeployment, Alert und Restore erprobt,
- Legaltexte freigegeben,
- anschließend ein kleiner interner Pilot ohne Datenintegritäts- oder Workflowfehler.

Erst dann sollte Sammlr als Closed Beta bezeichnet werden. Public Beta und 1.0 brauchen danach reale Nutzungszeit; sie benötigen nicht automatisch mehr Features.
