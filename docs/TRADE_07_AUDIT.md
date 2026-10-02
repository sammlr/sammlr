# TRADE-07 — Empfang, Problemklärung, Abschluss und Bewertung

Stand: 2026-10-01. Ausschließlich isolierte Trade-v2-Preview auf Port 8095; lokaler Zustand eines Browser-Tabs.

## Ergebnis und Einstieg

Die Journey von der Tauschhalle über Anfrage, Annahme, Packen und Versand bis Empfang, optionaler Problemklärung, Abschluss, optionaler Bewertung und Erledigt ist durchspielbar. Bestehende Discovery, Dealansicht, Marker, Stickerstapel, rote Packzettel, gelbe Adresse und Portal bleiben erhalten.

Start im Projektordner:

```sh
.venv/bin/python -B -m App.trade_v2
```

Preview: http://127.0.0.1:8095/trade-v2/

Receipt-Route ohne Reset: http://127.0.0.1:8095/trade-v2/requests/fatima/receipt

[Direkte Demos für beide Rollen](../tests/research/artifacts/trade-07/demos.html) · [Screenshot-Galerie](../tests/research/artifacts/trade-07/index.html) · [Prüfergebnisse](../tests/research/artifacts/trade-07/checks.json).

Die expliziten `receipt=`-Einstiege setzen ausschließlich den Demo-Zustand dieses Tabs zurück. Der Parameter wird anschließend entfernt. Normale Navigation, Rollenwechsel und Reload erhalten den Zustand. Die direkte `history`-Demo ist ein bewerteter Abschluss; „Zurück zur Tauschbörse“ zeigt ihn unter Erledigt.

## Verbindliche Q2-Klärung

Die nachgereichte Nutzerentscheidung verwirft TRADE-07 §6 und alle davon abgeleiteten Verbote. Q2 in `TRADE_PRODUCT_CONTRACT_V2.md` bleibt unverändert gültig. Empfang ist **nicht** an einen Partner-SHIPPED-Indikator gebunden. Der Nutzer bestätigt den tatsächlichen Empfang; das ist eine andere Tatsache als der Versandklick des Absenders.

Zulässig und geprüft: Fatima `READY_TO_SHIP`, Valentin `RECEIVED_OK`. Ebenso möglich: beide Empfangsrichtungen final und Trade COMPLETED, obwohl Versandbestätigungen fehlen. Empfang verändert weder Versandflags noch Versandzeitpunkte, Packlisten oder Slots. Auch nach Completion bleiben ausstehende eigene Versandbestätigungen erreichbar; ausschließlich diese geben den jeweiligen eigenen operativen Slot frei. Es wird kein historischer Versandzeitpunkt erfunden.

Direkter Referenzfall: http://127.0.0.1:8095/trade-v2/requests/fatima/receipt?receipt=q2-ready-received&role=sender

Weitere Q2-Seeds: `q2-waiting`, `q2-received`, `q2-ok`, `q2-problem`, `q2-completed`. Der früher geforderte „Empfang vor Partner-SHIPPED blockiert“-Screenshot wurde durch den erlaubten Q2-Fall ersetzt.

## Gelesene Grundlagen und Domainabgrenzung

Grundlagen: `TRADE_PRODUCT_CONTRACT_V2.md`, `TRADE_00_RESET_AUDIT.md` sowie TRADE-01–06-Audits; Q2/Q6 und Adressschutz in `TRADE_UX_PO_DECISIONS_Q1_Q8.md`. Bestehende isolierte Pack-, Amendment- und Versandmodule sowie Tests dienen als verbindliche Interaktionsreferenz.

Produktive Referenzen ausschließlich lesend: `App/services/trade_problems.py` (`problem_reported`, `problem_trade_closed`, Empfangspositionen, Idempotenz, meldende Rolle bei Resolution), `App/services/trade_ratings.py` (Teilnehmer/Gegenrolle, qualifizierte Endzustände, einmalige Bewertung), die dazugehörigen Status-/Ratingstellen in `App/webapp.py` und der dokumentierte Notification-Katalog. Keine Übernahme produktiver Buchungsbefehle in die Preview.

Die bestehende produktive Rating-Skala 1–5 bleibt unangetastet. Die ausdrücklich beauftragte neue lokale Oberfläche akzeptiert ausschließlich ganzzahlige Werte 1–3. Gelöste Problemfälle sind bewertbar; deren Abschluss wird textlich von einem normalen erfolgreichen Empfang unterschieden. Kein automatisches Rating und keine neue Bewertung unaufgelöster Problemfälle. Es werden keine produktiven `closed_with_problem`-Vorgänge importiert, migriert oder umgedeutet.

Trade-v2 besitzt keine lokale Notification-Infrastruktur. Deshalb keine neue gebaut und keine Zustellung behauptet: Die UI erklärt, dass die Gegenseite den Problemfall im Tausch sehen kann. Legacy, Product Contract und Q2 bleiben bytegleich.

## State-Modell und Schutzregeln

Der bestehende Request bleibt `status: accepted`. Der gemeinsame Tradezustand wird separat als ACTIVE, COMPLETED oder CANCELLED projiziert. Dadurch kann Completion keine bestehende operative Slotprojektion versehentlich freigeben.

`receipts.sender` bedeutet Valentins Empfang **von der Gegenseite**, `receipts.recipient` den Empfang der Gegenseite **von Valentin**. Je Rolle: `state`, tatsächlicher lokaler `receivedAt`, aktive `version`, optionaler `problem`. Kein globales Received-Boolean.

| Ausgang | Autorisierte Aktion | Ergebnis |
| --- | --- | --- |
| Akzeptierter Trade, eigene WAITING-Richtung | Sendung erhalten | RECEIVED_UNCHECKED, unabhängig vom Partner-Versandklick |
| RECEIVED_UNCHECKED | Ja, alles da | Nur eigene Richtung RECEIVED_OK |
| RECEIVED_UNCHECKED | Problem melden | PROBLEM_REPORTED mit konkreten Angaben |
| PROBLEM_REPORTED | Gegenseite markiert Klärung | RESOLUTION_PENDING |
| RESOLUTION_PENDING | Meldende Seite bestätigt | RESOLVED |
| Beide Richtungen RECEIVED_OK oder RESOLVED | Abgeleiteter Abschluss | COMPLETED mit einmaligem `completedAt` |
| COMPLETED, eigene Bewertung fehlt | 1, 2 oder 3 speichern | Eigene einmalige Partnerbewertung |

WAITING, UNCHECKED, offenes Problem und ausstehende Bestätigung sind nicht final. Eine finale Richtung genügt nicht. Nicht angenommene, abgelehnte, abgelaufene und beendete Requests bieten keinen Empfangs-/Bewertungsflow. Unbekannte Rollen werden im Modell abgewiesen.

Die Commands lesen den aktuellen gemeinsamen Sessionstand vor jeder UI-Aktion; danach erfolgt ein synchroner gesamter Schreibvorgang. Erste zulässige Transition gewinnt. Doppelklicks, konkurrierendes Alles-da/Problem, Wiederholung von Resolution oder Rating können keine terminalen Zustände zurückdrehen. Speicherung validiert Empfangszustände, aktive Version, erwartete Problempositionen, Rollen und Ratingwerte. Bestehende Datensätze ohne Receipt bleiben lesbar, ohne Migration.

Der lokale Speicher ist weiterhin `sessionStorage['sammlr-trade-02']`. Diese Ein-Tab-Simulation ist keine produktive Authentifizierung, Mehrbenutzersynchronisierung oder DB-Transaktion. Rollenwechsel ist ausschließlich ein DEV-Werkzeug.

## Problem und unveränderliches Paket

Vier auswählbare Problemarten: fehlend, falsch, beschädigt, sonst unvollständig. Mehrfachauswahl möglich. Bei stickerbezogenen Arten mindestens eine konkrete erwartete Position; mehrere Exemplare auswählbar. Jede Position enthält Album, Code und Instanz aus dem aktiven Empfangssnapshot. Gespeichert werden richtungsbezogene Positions-IDs zusammen mit der aktiven Version. V1 umfasst im Referenzdeal 23, V2 21 Positionen. Kein freies Erfinden von Stickern.

Beide Rollen lesen dasselbe Problemobjekt. Die Gegenseite schlägt die Klärung vor; ausschließlich der ursprüngliche Melder bestätigt den Abschluss. Keine einseitige Löschung, keine Rücknahmefunktion erfunden. Problemverlauf bleibt auch nach Resolution und Completion sichtbar.

Empfang, Problemmeldung, Resolution, Completion und Rating verändern weder Snapshot, Dealversion, Versionshistorie, Packlisten, Versandfelder noch Slots. Keine Mengenreduktion oder erneute Optimierung. Ein dokumentierter tatsächlicher Empfang ist auch ohne Versandklick ein Nachweis physischer Abwicklung: neue Amendments sowie Entscheidungen über ein noch offenes Amendment werden gegen Snapshot-Umschreibung gesperrt. Die Änderungsansicht erklärt diese Sperre und verlinkt den Empfang. Ein offener alter Fehlmengen-/Amendmentkonflikt wird dadurch nicht still repariert oder gelöscht.

## Rating und Historie

Native Radio-Gruppe mit genau drei Auswahlwerten, zugänglichen Labels und sichtbarem Fokus. Keine halben Sterne, 0, 4, 5, Freitexte oder Unterkategorien. Speichern erst nach Completion und Auswahl. Gespeichert je bewertender Rolle: Sterne, explizite Gegenrolle und Zeitpunkt. Kein Self-Rating, kein Editieren, keine Abhängigkeit von der Partnerbewertung. „Später“ lässt den bereits abgeschlossenen Trade unverändert.

Die Startseite zeigt abgeschlossene Vorgänge in einem kleinen Bereich „Erledigt“. Der konkrete abgeschlossene Deal verschwindet aus den Top-Handlungsangeboten, bleibt historisch über denselben Request erreichbar. Bestehende Status- und Versandwege verlinken den Abschluss; keine neue globale Navigation. Bei Q2 bleiben dort separat noch ausstehende eigene Versandbestätigungen erreichbar, ohne Completion zurückzusetzen.

## Prüfungen und Evidenz

Ausgeführt:

```sh
.venv/bin/python -B -m unittest tests.test_trade_v2_preview tests.test_pax_preview -q
.venv/bin/python -B -m unittest tests.test_sticker_wall_product_island tests.test_ceoklaue_sticker_list -q
.venv/bin/python -B tests/research/check_trade_07_regressions.py
.venv/bin/python -B tests/research/check_trade_07.py
git diff --check
```

- **37 Unittests bestanden:** 8 Preview-/Isolationstests und 29 bestehende Wall-/Listentests; die neue GET-Route ist eingeschlossen, POST bleibt 405. Preview ohne DB-Verbindung oder Import produktiver Services. Referenztests verwenden ausschließlich temporäre Test-DBs.
- **1.047 neue Modellassertionen bestanden:** beide Rollen × drei Herkünfte × V1/V2, richtige Empfangsrichtung und Positionen, mehrere Problemarten/-positionen, Rollenrechte, erster gültiger Übergang gewinnt, Problem/Alles-da-Rennen, Completion, 1–3-Rating, ungültige Werte, korrupte Persistenz, Reload, Q2 bei PACKING/READY_TO_SHIP, unveränderte physische Daten und Slots, spätere eigene Versandklicks sowie Amendment-Sperre nach tatsächlichem Empfang.
- **TRADE-01–06-Browsergates bestanden**, ohne Änderungen an deren Assertions. Enthalten weiterhin 205 Amendment- und 259 Versand-Modellassertionen; insgesamt damit **1.511 explizit gezählte Modellassertionen** plus weitere bestehende Browser-/Modellprüfungen aus TRADE-01–04. Assertions sind nicht als zusätzliche unittest-Testfälle gezählt.
- **Vollständiger E2E bei 375/390/430/1280 bestanden:** jeweils frischer Browserkontext, Tauschhalle → Fatima → Senden → Rollenwechsel/Annahme → beide Packlisten und bewusste Versandbestätigungen → beide Empfänge vollständig → Completion → Valentin vergibt drei Sterne → Erledigt → finalen Trade wieder öffnen. Keine Seed-URL oder manuelle State-Manipulation innerhalb dieses E2E.
- **Problem-E2E bei allen vier Breiten bestanden:** zulässiger BOTH_SHIPPED-Demoeinstieg, danach ausschließlich Controls; Empfang → zwei fehlende erwartete Sticker → andere Rolle sieht identische Meldung → Klärung vorschlagen → Melder bestätigt → andere Empfangsrichtung vollständig → Completion und Rating verfügbar. Snapshot/Version/Packen/Versand unverändert.
- **Q2-Browserflow bei allen vier Breiten bestanden:** Empfang und Problem ohne Partner-SHIPPED, unveränderte Slots, gemeinsame Resolution, zusätzlicher READY_TO_SHIP/RECEIVED_OK-Demofall, Completion ohne Versandklicks und spätere eigene Versandbestätigung mit alleiniger Slotfreigabe.
- Native Touch-/Maus-/Keyboard-Aktionen, Enter und Space, sichtbarer Fokus, semantische Checkboxen und Stern-Radios, Reduced Motion. Kein horizontaler Overflow. Keine JS-/HTTP-Fehler, keine externen oder schreibenden Browserrequests.
- **21 kanonische Stack-Paritätsfälle** gegen den tatsächlichen produktiven BRA-3-Renderer: Mengen 1/2/5/6/10/15/37 bei 375/390/430; Wall5/Trade10, −2/−2, Faces, Maße und z-index unverändert. Kein Wachstum über zehn.
- **81 neue TRADE-07-Screenshots** plus separate Regressionsevidenz. Sichtprüfung von Rating, Partnerproblem und Q2-Empfang: vollständige lesbare Controls, klare getrennte Rollen, kein Abschneiden. Keine anschließende Polishrunde.

Ein erster Testharness-Aufruf musste seinen Playwright-Eventhandler korrigieren; der erste E2E-Versuch musste vor dem Rollenwechsel den eingeklappten DEV-Bereich öffnen. Beide waren Testharnessfehler, keine umgangenen Produktguards. Finale vollständige Läufe sind maßgeblich.

## Dateien und geschützte Bereiche

[Vollständige maschinenlesbare Dateiliste](../tests/research/artifacts/trade-07/files.json) mit allen geänderten/neuen Dateien, geprüften geschützten Dateien und SHA-256-Status. [Scope-Nachweis](../tests/research/artifacts/trade-07/scope-checks.json) enthält Vorher-/Nachher-Hashes. Referenz ist der tatsächliche lokale Bestand unmittelbar vor TRADE-07, einschließlich bereits vorhandener Git-Änderungen; kein Zurücksetzen fremder Arbeit.

Neue Anwendungsmodule: `receipt_state.js`, `receipts.js`, `receipt_view.js`, `receipt_demo.js`, `receipt_history.js`, `receipt.css` unter `App/trade_v2/assets/`. Bestehende Integrationspunkte: Routes, Template, Preview, Requests/Validierung, Request-Ansicht, Amendment-Modell/-Ansicht und Versandpanel. Keine kanonische Darstellungsdatei geändert.

Neue Tests: `tests/research/check_trade_07.py`, `trade_07_model.js`, `check_trade_07_regressions.py`; bestehender Preview-Unittest um die neue GET-Route ergänzt. Neue Dokumente: dieser Audit, End-to-End-Audit und manuelle Walkthrough-Checkliste. Research-Ausgaben ausschließlich unter `tests/research/artifacts/trade-07/`.

Bestätigt: keine Produktiv-DB verändert; keine produktiven Trade-/Versandrouten geändert; `App/pax/` samt Assets/Templates unverändert; Stickerwall, Stickerliste, Post-it-Logik, SmartDeal-Algorithmus unverändert. Keine Deal-Neuberechnung beim Empfang, keine Dealänderung oder Amendments nach Versand beziehungsweise dokumentiertem tatsächlichem Empfang. Keine automatische Schuldzuweisung/Bewertung, keine Geld-/Refundlogik, echte Versandmutation, echten Privatadressen oder Moderationsengine. Kein git add, Commit, Push oder Deploy.

Die produktive Anbindung samt atomaren Bestandsbuchungen, Authentifizierung, Retention und Mehrbenutzersynchronisierung bleibt außerhalb dieser Preview. Der bestehende manuelle Builder-Platzhalter wurde nicht erweitert; der gemeinsame Lifecycle normalisierter MANUAL-Deals ist im Modell geprüft.
