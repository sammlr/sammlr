# TRADE-08 — Tauschbörse UX konsolidieren

Stand: 2026-10-01. Ausschließlich isolierte Trade-v2-Preview, Trade-spezifische Tests und neue Audit-/Research-Artefakte. Keine produktive Integration.

## Ergebnis und Preview

Start im Projektverzeichnis:

```sh
.venv/bin/python -B -m App.trade_v2
```

- Tauschbörse: http://127.0.0.1:8095/trade-v2/
- Alle Sammlr: http://127.0.0.1:8095/trade-v2/partners
- Anfragen und laufende Tausche: http://127.0.0.1:8095/trade-v2/active
- Vollständiger Vorschlag: http://127.0.0.1:8095/trade-v2/deals/fatima
- Direkte Packdemo: http://127.0.0.1:8095/trade-v2/requests/fatima/next?pack=zero&role=sender

Die Preview ist weiterhin eine lokale Ein-Tab-Simulation mit DEV-Rollenwechsel. Explizite ältere Demo-URLs setzen wie bisher den Request-Demostand zurück. Dismiss bleibt separat pro Browser-Tab erhalten; ein neuer Browser-Tab mit frischer Sitzung ermöglicht einen frischen Discovery-Durchlauf. Kein neuer produktiver Persistenzvertrag.

## Top 3 und Navigation

Die Hauptseite zeigt „Tauschen“ und den beauftragten Satz: „3 automatische Tauschvorschläge, die sammlr. für dich gefunden hat.“ Die alte Partnervorschau und die Preview-Erklärung auf der Hauptseite sind entfernt. Drei kompakte Vorschläge stehen bei 375/390/430 px in einer horizontalen Reihe. Jeder zeigt den kanonischen Stapel, Name, Menge und Albumzahl.

Darunter: „Alle Sammlr“ sowie „Anfragen & laufende Tausche“. Der separate Partnerpool heißt jetzt „Alle Sammlr“; bestehende Sortierung, Albumfilter, Partnerdaten und manueller Platzhalter bleiben erhalten. Keine neue Filter- oder Eligibility-Architektur.

Die neue laufende Übersicht liest ausschließlich vorhandene Demo-Requests, aktualisiert über die bestehende Expiry-Funktion abgelaufene Pending-Anfragen und verlinkt denselben Request. Angenommene Trades bleiben sichtbar; Completed bleibt im vorhandenen Erledigt-Bereich historisch erreichbar. Keine neue Request-, Slot- oder Trade-Domain.

## Nachrücken und Dismiss

Die fünf vorhandenen, vorqualifizierten und geordneten Top-Fixtures bleiben unverändert. Sichtbar sind die ersten maximal drei ohne bereits vorhandenen Request und ohne lokalen Dismiss. Initial Fatima/Justus/Marek; Fatima ablehnen ergibt Justus/Marek/Luca. Eine tatsächlich angefragte Chance rückt ebenfalls aus der Vorschlagsfläche in den bestehenden Request-/Tradebereich. Sind weniger als drei geeignete Demo-Chancen übrig, werden keine erfundenen Kandidaten aufgefüllt.

`sessionStorage['sammlr-trade-08-dismissed']` enthält ausschließlich konkrete Fixture-Vorschlags-IDs. Reload erhält die Ablehnung. Dismiss erzeugt oder verändert keinen Request, Snapshot, Slot oder Timer. Ein bereits angefragter Vorschlag kann nicht durch diesen Befehl zum bloßen Discovery-Dismiss umgedeutet werden. Die neue Oberfläche führt keine endgültige produktive Dismiss-, Neubewertungs- oder Lebenszeitregel ein.

„Tausch anfragen“ nutzt unverändert den vorhandenen Sendercommand mit frischer Kapazitätsprüfung und absoluter 24h-Frist. Nachrücken erlaubt keine vierte operative Anfrage. Auf der Dealansicht ist der bestehende Request-CTA weiterhin „Tauschanfrage senden“; daneben als sekundäre Aktion „Vorschlag ablehnen“.

## Kanonische Receive-Darstellung

`assets/receive.js` ist der einzige Trade-Wrapper für die vorhandene reine `renderReceive`-Funktion aus `/static/pax/pax.js`. Deal, gespiegelte Requestansicht und sekundäres Receive in der Packphase verwenden denselben Wrapper. Er baut keine Stickerfaces oder Back-Layer selbst.

Geschlossen: drei kompakte Albumstapel je Reihe mit Albumname und Menge. Die unveränderten 100-px-Komponenten werden ausschließlich über äußere Darstellungscontainer mit Faktor .72 verkleinert; innere Face-/Layermaße, −2/−2-Versatz, Richtung und z-index bleiben kanonisch. Offene Albumsektoren zeigen die unveränderten einzelnen kanonischen Faces. Einzeln öffnen/schließen betrifft ausschließlich das jeweilige Album. „Alle anzeigen“ öffnet alle über dieselben vorhandenen Controls; keine zweite Logik für die einzelnen Sticker.

Albumsektoren sind mit mehr Abstand getrennt als Sticker innerhalb eines Sektors. Öffnen blendet den jeweiligen Fächer für 240 ms dezent ein. Auch die Vorschlagsauslage verwendet eine kurze 240-ms-Einblendung. Bei Reduced Motion findet keine Animation statt; die Funktion hängt nie von deren Abschluss ab. Native Controls und sichtbarer Fokus bleiben erhalten.

## Packphase ohne Einzelabhaken

Die roten Post-its sind reine Listen. Keine Einzelbuttons, Checkboxen, Kreuze oder Textmarker in den Packzetteln. Die bisherige Packmarker-CSS wurde ausschließlich im Trade-v2-Pfad entfernt; das historische SVG bleibt ungenutzt erhalten. Pax und produktive Post-it-/Listenkomponenten sind unverändert.

Der Fortschritt lautet nun beispielsweise „23 Sticker auf deiner Packliste“. „Alle Sticker sind bereit – Packfreigabe bestätigen“ ist die bewusste Gesamtbestätigung. Der neue UI-Adapter bestätigt das vollständige aktuelle Paket und ruft die bestehenden Packabschluss-/Versandfreigabe-Funktionen auf. Intern bleibt das bisherige validierte positionsbezogene Modell erhalten; die Benutzerinteraktion hängt nicht mehr von 23 Einzelklicks ab. Keine neue Scanner-/Fotoprüfung und keine erfundene Versandbestätigung.

„Ich kann nicht alles einpacken“ öffnet eine separate Fehlmengenauswahl aus den tatsächlich vereinbarten eigenen GIVE-Positionen. Ausschließlich hier werden semantische Auswahlfelder für die fehlenden Exemplare verwendet; sie sind keine Pack-Checkboxen. Keine Vorauswahl bei normalem Einstieg. Eine leere oder unbekannte Auswahl darf nicht gemeldet werden. Zurück verwirft den ungesendeten Auswahldraft ohne Änderung am gespeicherten Paket.

Die ausdrückliche Fehlbestätigung übernimmt exakt diese fehlenden Keys, stellt die übrigen als bereit erklärt dar und verwendet die bestehenden Review-/Report-/Amendment-Übergänge. Der aktive Snapshot bleibt V1 bis zur Partnerzustimmung. Kein automatisches Ändern, kein neuer Algorithmus und kein eigener paralleler Amendment-Lifecycle. V2, bewusste Versionsfreigabe, Eigentümerfreigabe der Adresse und eigener Versand bleiben erhalten. Nach Versand sind Gesamtbestätigung und Fehlmengenadapter gesperrt.

## Erhaltene Domain und Grenzen

Unverändert: `requests.js`, `packing.js`, `deal_versions.js`, `amendments.js`, Versandmodell/-Commands, Receipt-/Problem-/Completion-/Ratingmodell sowie sämtliche produktiven Domainquellen. Der UX-Adapter verwendet die vorhandenen Validators und Transitions.

Q2 bleibt gültig: Empfang darf ohne Partner-Versandklick erfolgen. Kein Shipping- oder Slotwechsel durch Empfang/Problem/Completion. Die ganze TRADE-07-Journey bleibt einschließlich optionaler gemeinsamer Problemlösung, 1–3-Sterne-Bewertung und Historie erreichbar.

Keine manuellen Builder, neuen Eligibility-/Onboarding-/Album-Publicity-Regeln, Favoritenprioritäten, Entfernungssuche, Scan-/Fotobelege oder Pax-Produktmechanik implementiert.

## Regressionen und Abnahme

Ausgeführt:

```sh
.venv/bin/python -B -m unittest tests.test_trade_v2_preview tests.test_pax_preview -q
.venv/bin/python -B -m unittest tests.test_sticker_wall_product_island tests.test_ceoklaue_sticker_list -q
.venv/bin/python -B tests/research/check_trade_08_regressions.py
.venv/bin/python -B tests/research/check_trade_08.py
git diff --check
```

- **37 Unittests bestanden**: 8 Preview-/Isolationstests einschließlich GET-only `/active`, 29 bestehende produktive Wall-/Listenreferenztests mit temporären Test-DBs.
- **TRADE-01–07-Browsergates bestanden.** Nur die ausdrücklich ersetzten UI-Erwartungen wurden angepasst: drei statt fünf sichtbare Vorschläge, keine Partnervorschau, Gesamtbestätigung statt Marker-/Einzelklicks, explizite Fehlmengenauswahl und geänderte Fortschrittstexte. Historische Artefakte wurden nicht überschrieben.
- Die bestehenden reinen Pack-, Amendment-, Versand- und Empfangsmodellprüfungen bleiben erhalten. Enthalten sind **205 Amendment-, 259 Versand- und 1.047 Receipt-Modellassertionen**. Zusätzlich **90 neue Adapterassertionen** für beide Rollen × drei Herkünfte, Pending-/Stale-/Invalid-Guards, exakte Fehlpositionen, unabhängige Gegenrolle, Snapshot-Erhalt, bewusste Freigabe und Wiederholungen. Insgesamt **1.601 explizit gezählte Modellassertionen**, zusätzlich zu weiteren bestehenden Browser-/Modellprüfungen. Kein Vermischen dieser Zahl mit der unittest-Testzahl.
- Neuer Browsergate bei **375/390/430/1280**: drei mobile Top-Angebote in einer Reihe, direkter Deal, unabhängige Alben und Alle anzeigen, 240-ms-Animation/Reduced Motion, Dismiss→Nachrücker→Reload, keine Requestmutation durch Dismiss, Anfrage→Nachrücker, laufende Übersicht, Alle Sammlr, 3/3-Sperre, Packliste ohne Tick-Controls, exakte Fehlmenge→V2, Gesamtfreigabe→Adresse. Keine horizontalen Überläufe, JS-/HTTP-Fehler, externen oder schreibenden Browserrequests.
- TRADE-07 führt erneut bei allen vier Breiten die vollständige frische Journey bis Bewertung/Erledigt und den gemeinsamen Problem-E2E aus. Q2 ohne Partner-SHIPPED, unabhängige Slots und spätere Versandbestätigung bestehen weiterhin. TRADE-06 prüft Adresse, Eigentümerfreigabe, Portal und Versand; TRADE-05 prüft Amendment/Cancel/Versionen.
- **21 Stack-Paritätsfälle** gegen den tatsächlichen produktiven BRA-3-Renderer: Mengen 1/2/5/6/10/15/37 bei 375/390/430, Wall5/Trade10, gleiche Faces, Dimensionen, −2/−2 und z-index, kein geometrisches Wachstum über zehn. Keine Änderung kanonischer Quellen.
- **44 neue TRADE-08-Screenshots** plus neue Regressionsevidenz. Hauptseite, kompakte Albumdarstellung und reine Packzettel visuell geprüft. Galeriebilder werden nach Abschluss der kurzen Einblendung aufgenommen, damit kein transparenter Animationszwischenstand als Endzustand erscheint.
- `git diff --check` und zusätzliche Whitespace-Prüfung neuer/geänderter Textdateien bestanden; siehe Scope-Nachweis.

## Dateien und Evidenz

- [Neue Screenshot-Galerie](../tests/research/artifacts/trade-08/index.html)
- [TRADE-08-Prüfergebnis](../tests/research/artifacts/trade-08/checks.json)
- [Vollständige Liste aller geänderten/neuen Dateien](../tests/research/artifacts/trade-08/files.json)
- [Geschützte Dateien / SHA-256-Nachweis](../tests/research/artifacts/trade-08/scope-checks.json)

Neue App-Dateien ausschließlich unter `App/trade_v2/assets/`: `discovery.js`, `proposal_dismiss.js`, `receive.js`, `packing_confirmation.js`, `ux08.css`. Bestehende lokale Änderungen betreffen Template, Routes, Preview-/Request-/Packing-Ansicht, Packing-CSS und die Request-/History-Navigation. Neue Trade-08-Tests und dieser Audit ergänzen die überprüfbare Umsetzung. Jede einzelne Artefaktdatei steht im Manifest.

Hashvergleich gegen den tatsächlichen Bestand unmittelbar vor TRADE-08: keine Änderungen außerhalb der erlaubten Trade-v2-/Trade-Testdateien, keine Löschungen. Insbesondere produktive Webapp/DB/Routen, Stickerwall, Stickerliste, SmartDeal-Algorithmus, Pax samt Assets/Templates, Legacy-Pfade, bestehende Vertragsdokumente und historische Research-Ausgaben unverändert. Bestehende fremde Git-Änderungen wurden nicht zurückgesetzt.

**Keine produktive DB-Mutation. Kein git add, Commit, Push oder Deploy.**
