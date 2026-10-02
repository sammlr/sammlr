# TRADE-04 — Packphase und Fehlmengen-Ausgang

Stand: 2026-09-30. Ausschließlich isolierte Trade-v2-Preview. Keine produktive Integration.

## Ergebnis und Start

Die angenommene Anfrage führt über „Zum Packen →“ zur eigenen Packliste. Valentin und Fatima arbeiten am selben eingefrorenen Deal, mit getrennten Packständen. GIVE ist primär; RECEIVE bleibt sekundär, geschlossen und pro Album auffächerbar.

Start im Projektverzeichnis:

```sh
.venv/bin/python -B -m App.trade_v2
```

Preview: http://127.0.0.1:8095/trade-v2/

Accepted-Einstieg: http://127.0.0.1:8095/trade-v2/requests/fatima?scenario=accepted&role=sender

| Demo | Valentin | Fatima |
| --- | --- | --- |
| 0/23 | [Öffnen](http://127.0.0.1:8095/trade-v2/requests/fatima/next?pack=zero&role=sender) | [Öffnen](http://127.0.0.1:8095/trade-v2/requests/fatima/next?pack=zero&role=recipient) |
| 21/23 | [Öffnen](http://127.0.0.1:8095/trade-v2/requests/fatima/next?pack=partial&role=sender) | [Öffnen](http://127.0.0.1:8095/trade-v2/requests/fatima/next?pack=partial&role=recipient) |
| 22/23 | [Öffnen](http://127.0.0.1:8095/trade-v2/requests/fatima/next?pack=22&role=sender) | [Öffnen](http://127.0.0.1:8095/trade-v2/requests/fatima/next?pack=22&role=recipient) |
| 23/23 | [Öffnen](http://127.0.0.1:8095/trade-v2/requests/fatima/next?pack=23&role=sender) | [Öffnen](http://127.0.0.1:8095/trade-v2/requests/fatima/next?pack=23&role=recipient) |
| Packprüfung abgeschlossen | [Öffnen](http://127.0.0.1:8095/trade-v2/requests/fatima/next?pack=complete&role=sender) | [Öffnen](http://127.0.0.1:8095/trade-v2/requests/fatima/next?pack=complete&role=recipient) |
| Fehlmengenreview | [Öffnen](http://127.0.0.1:8095/trade-v2/requests/fatima/next?pack=review&role=sender) | [Öffnen](http://127.0.0.1:8095/trade-v2/requests/fatima/next?pack=review&role=recipient) |
| Fehlmenge gemeldet | [Öffnen](http://127.0.0.1:8095/trade-v2/requests/fatima/next?pack=reported&role=sender) | [Öffnen](http://127.0.0.1:8095/trade-v2/requests/fatima/next?pack=reported&role=recipient) |

Die direkten Demo-Links initialisieren ausschließlich den lokalen Session-Demostand neu. Der normale Rollenwechsel erhält den gemeinsamen gespeicherten Request und beide Packstände.

## Gelesene Grundlagen / übernommene Mechanik

Grundlagen: `TRADE_PRODUCT_CONTRACT_V2.md`, `TRADE_00_RESET_AUDIT.md`, `TRADE_01_AUDIT.md`, `TRADE_02_AUDIT.md`, `TRADE_03_AUDIT.md`; Pax-05-Journey, Lifecycle, zugehörige CSS/JS und Packlisten-Research; produktive Stickerlisten-/Post-it-Referenz nur lesend.

`App/static/pax/pax.js` rendert unverändert GIVE und RECEIVE. Keine neue Post-it-Paginierung: 16 Positionen, danach 20 pro Fortsetzung. Bestehende Überlappung, Rotation und Albumabstände bleiben erhalten. Die Receive-Stacks bleiben kanonisch −2/−2, identische Faces/Maße/z-index, Trade-Cap 10, Wall-Cap 5.

Die Packbuttons übernehmen die Struktur aus `App/static/pax/journey.js`: bestehendes Label im nativen Button, dekoratives Markerbild, `aria-pressed`, derselbe einzelne Exemplar-Key. Fünf CSS-Regeln aus `App/static/pax/journey.css` sind deklarationsgleich übernommen, nur auf `.trade-packing` begrenzt. Automatischer Quellvergleich belegt die Parität. Höhe 20 px; Bild 64 × 30 px, links 0, top 50 %, translate 0 −50 %; Opacity 0 / .72; identische Focus-Regeln. Kein Layoutsprung beim Toggle.

**Animationsbefund:** Die tatsächliche Pax-Packmarkierung hat keine Ziehanimation und keine CSS-Transition. Sie wechselt die Opacity direkt. Auch das bisherige statische SVG implementiert keine Animation. Trade-v2 übernimmt exakt dieses Verhalten: berechnet `transition-duration: 0s`, `animation-name: none`. Es wurde keine neue Bewegung oder Dauer erfunden. Die anderweitige produktive Stickerlistenanimation ist nicht die Pax-Packanimation und wurde nicht übernommen. Reduced Motion funktioniert mit demselben direkten Zustandswechsel.

Nur das isolierte Marker-SVG ist neu: dunkles Blutrot `#820c1d`, transparente Füllung, schmale organische Kante. Text und Papier bleiben sichtbar. Kein Kuli-Kreuz, Haken, Kreis oder Checkbox als Packmarkierung. Der ausdrücklich gewünschte Vollständigkeitsstatus darf ein ✓ im Fortschrittstext anzeigen.

## Modell und Lifecycle

`request.status` bleibt `accepted`. Request-State und richtungsbezogener Pack-State sind getrennt. Es entsteht kein zweiter Trade. `packing.sender` und `packing.recipient` führen jeweils `phase`, `packed` (Exemplar-Keys), `missingReported`.

Phasen: `accepted` → `packing` → `packing_complete`; alternativ `packing` → `missing_review` → `packing` oder `missing_reported`. Terminale Ergebnisse können nicht durch weitere Klicks wieder geöffnet werden. Unbekannte Keys, falsche Rollen und unvollständiger Abschluss werden abgewiesen; gespeicherte Packdaten werden vor Verwendung validiert.

Alle Positionen werden aus `perspective(request, role).give` abgeleitet. Keine separat gepflegten Listen. Eigene GIVE- und Partner-GIVE-Seite sind exakt gespiegelt; Mehrfachexemplare sind getrennte Keys. Herkunft TOP_SUGGESTION / SMARTDEAL / MANUAL verändert diese Mechanik nicht. MANUAL bleibt im UI ansonsten der vorhandene Preview-Endpunkt; der Modelltest verwendet normalisierte Accepted-Fixtures aller drei Herkünfte.

Abschluss erfordert jede Position: 22/23 genügt nicht; 23/23 aktiviert den CTA. Das Ergebnis lautet „Packprüfung abgeschlossen.“ / „Adresse und Versand folgen im nächsten Schritt.“

Fehlmengenreview zeigt ausschließlich die nicht markierten Keys und sagt noch nicht, dass sie tatsächlich fehlen. Zurück erhält Marks, Deal und Partnerzustand exakt. Erst die ausdrückliche Bestätigung speichert die offenen Keys als `missingReported`, ohne sie aus dem Snapshot zu entfernen. Ergebnis: „Fehlende Sticker gemeldet.“ / „Wie der Tausch angepasst wird, folgt im nächsten Schritt.“ Keine Partnerzustimmung, Neuberechnung, Benachrichtigung oder Amendment.

Alle Packphasen behalten den operativen Slot. `ownShipped` bleibt false. Der Accepted-Request läuft nicht durch die ursprüngliche 24h-Anfragefrist ab. Kein Countdown und keine neue Packfrist.

## Ausgeführte Tests

- `.venv/bin/python -B -m unittest tests.test_trade_v2_preview tests.test_pax_preview -q`: **8 Tests, OK**. DB-Zugriff bei Preview-Routen verboten, keine Produktiv-App-/Service-Imports; Schreibmethoden 405.
- `.venv/bin/python -B tests/research/check_trade_01.py`: **PASS**. Discovery/Partner/Deal-Journeys, 16/20-Fortsetzung; 21 Stack-Paritätsfälle (Mengen 1, 2, 5, 6, 10, 15, 37 bei 375/390/430 px), vollständiger CSS-Geometrievergleich zur produktiven Referenz, Wall 5 / Trade 10, kein Wachstum oberhalb des Caps. Produktiver Renderer dabei nur gegen temporäre Test-DB.
- `.venv/bin/python -B tests/research/check_trade_02.py`: **PASS**. Anfrage, Slots, Idempotenz, absolute 24h-Frist, defekter lokaler Speicher, vier Breiten.
- `.venv/bin/python -B tests/research/check_trade_03.py`: **PASS**. Spiegelung, Accept/Decline/Expiry, Rollen, Slots, wiederholte Aktionen, alle acht Demo-Einstiege, vier Breiten. Ausschließlich der überholte „Packphase folgt“-Test wurde auf den tatsächlichen 0/23-Einstieg und erhaltenen Request angepasst.
- `.venv/bin/python -B tests/research/check_trade_04.py`: **PASS**. 375/390/430/1280 px; 14 direkte Packdemos je Breite; realer Klickpfad von 0 bis 23 und Abschluss; 22 verhindert Abschluss auch bei synthetischem Klick; exakte Give-Keys beider Rollen, 23/23 vs. 4/23, Reload-Erhalt, Review/Zurück/Report, Snapshot unverändert, belegte Slots, kein Countdown. Modelltest: drei Herkünfte, getrennte Mehrfachexemplare, ungültige Keys/Zustände, terminale Guards, keine Accepted-Expiry.
- Touch, Maus, Enter und Space toggeln denselben State; Focus sichtbar; `aria-pressed` und zugängliche Labels; Fortschritt als Live-Status; Reduced Motion; Marker berechnet 64 × 30 / .72 / 0s / none; absolute Dokumentgeometrie vor/nach Toggle identisch. Kein horizontaler Seitenoverflow. Receive weiterhin unabhängig auf-/zuklappbar.
- Browserprüfungen: keine JS-Fehler, HTTP-Fehler, externen Requests oder Schreibrequests.
- `git diff --check` und ergänzende Whitespace-Prüfung aller neuen/geänderten Textdateien: siehe `scope-checks.json`.

Anfangs war `pytest` in der vorhandenen venv nicht installiert. Die vorhandenen unittest-Tests wurden deshalb direkt mit unittest ausgeführt; keine Dependency installiert. Ein Browserprüflauf verwendete zunächst fälschlich den nach Auffächern versteckten Öffnungsbutton zum Schließen. Test auf den vorhandenen „Zusammenlegen ↑“-Button korrigiert, gesamter Trade-04-Lauf anschließend bestanden; keine Änderung am kanonischen Verhalten.

## Sichtprüfung und Artefakte

- [Screenshot-Galerie](../tests/research/artifacts/trade-04/index.html)
- [Marker A/B/C](../tests/research/artifacts/trade-04/marker.html)
- [Direkte QA-Einstiege](../tests/research/artifacts/trade-04/demos.html)
- [Packflow-Prüfergebnis](../tests/research/artifacts/trade-04/checks.json)
- [Scope-/Hashnachweis](../tests/research/artifacts/trade-04/scope-checks.json)
- [Vollständiges Dateimanifest](../tests/research/artifacts/trade-04/files.json)

17 neue Packflow-Screenshots einschließlich 390-px-Pflichtzustände, gespiegelter Fatima-Liste, getrenntem DEV-Stand, Receive und zentraler Ansicht in allen vier Breiten. Zusätzlich neu erzeugte Regressionsevidenz von Trade-01/02/03. Ältere Galerien wurden nicht überschrieben. Marker A ungepackt / B erster Paint bei 0 ms / C gepackt: B und C entsprechen wegen der unverändert sofortigen Mechanik demselben sichtbaren Zustand. Sichtprüfung von mobilem Packzettel, Marker-Nahaufnahme und Fehlmengenreview: lesbar, nicht abgeschnitten, Marker auf korrekter Zeile, klare Review-Aktionen.

## Exakte Quelländerungen

Bestehende Dateien geändert:

- `App/trade_v2/templates/preview.html` — Packansicht und Endpunkte, DEV-Daten, bedingtes Pack-CSS.
- `App/trade_v2/assets/preview.js` — Next-Einstieg an Packcontroller delegiert.
- `tests/research/check_trade_01.py` — neuer Artefakt-Ausgabeordner.
- `tests/research/check_trade_02.py` — neuer Artefakt-Ausgabeordner.
- `tests/research/check_trade_03.py` — tatsächlicher Packeinstieg statt altem Platzhalter; neuer Ausgabeordner und Galerielinks.

Neu:

- `App/trade_v2/assets/packing.js` — isoliertes richtungsbezogenes Packmodell.
- `App/trade_v2/assets/packing_view.js` — Controller, lokale Demos, Buttons, Ergebnisse, DEV.
- `App/trade_v2/assets/packing.css` — scoped kanonische Packbutton-Regeln und Packansicht.
- `App/trade_v2/assets/marker.svg` — alleiniger neuer Packmarker.
- `tests/research/check_trade_04.py` — Browser-/Modell-/Paritätsprüfungen und Galerien.
- `docs/TRADE_04_AUDIT.md` — dieser Audit.
- Neue Research-Artefakte ausschließlich in `tests/research/artifacts/trade-04/`; jede einzelne Datei steht im vollständigen Manifest und in der nachfolgenden Liste.

## Geschützte Grenzen / negative Assertions

Vergleich gegen den vor Änderungen gesicherten SHA-256-Bestand `/tmp/trade04-before.json`. Der dauerhafte Scope-Bericht enthält Vorher-/Nachher-Hashes aller geschützten Dateien sowie die genaue Änderungsliste. Vorbestehende lokale Änderungen werden dabei als Ausgangszustand behandelt, nicht gegen Git zurückgesetzt.

- Keine Produktiv-DB verändert; kein produktiver DB-Zugriff im Preview-Prozess.
- Keine produktiven Trade-Routen verändert.
- `App/pax/` und `App/static/pax/` unverändert.
- Produktive Stickerwall, Stickerliste und Post-it-Logik unverändert.
- SmartDeal-Algorithmus unverändert; Dealinhalt nicht neu berechnet.
- Kein Amendment, kein Entfernen von Dealpositionen, keine automatische Zustimmung und kein Abbruch.
- Keine Adresse angezeigt, kein Versand implementiert, kein Slot freigegeben.
- Keine neue Post-it-Paginierung; keine Checkbox, kein Kreis oder Haken als Packmarkierung.
- Keine produktive Mutation, kein git add, kein Commit, kein Push, kein Deploy.

## Vollständige Liste neuer Research-Artefakte

- `tests/research/artifacts/trade-04/01-packing-zero-1280.png`
- `tests/research/artifacts/trade-04/01-packing-zero-375.png`
- `tests/research/artifacts/trade-04/01-packing-zero-390.png`
- `tests/research/artifacts/trade-04/01-packing-zero-430.png`
- `tests/research/artifacts/trade-04/02-first-mark-390.png`
- `tests/research/artifacts/trade-04/03-packing-partial-390.png`
- `tests/research/artifacts/trade-04/04-packing-22-390.png`
- `tests/research/artifacts/trade-04/05-packing-23-390.png`
- `tests/research/artifacts/trade-04/06-packing-complete-390.png`
- `tests/research/artifacts/trade-04/07-missing-review-390.png`
- `tests/research/artifacts/trade-04/08-missing-reported-390.png`
- `tests/research/artifacts/trade-04/09-secondary-receive-390.png`
- `tests/research/artifacts/trade-04/10-fatima-packing-390.png`
- `tests/research/artifacts/trade-04/12-dev-independent-390.png`
- `tests/research/artifacts/trade-04/checks.json`
- `tests/research/artifacts/trade-04/demos.html`
- `tests/research/artifacts/trade-04/files.json`
- `tests/research/artifacts/trade-04/index.html`
- `tests/research/artifacts/trade-04/marker-A-unpacked-390.png`
- `tests/research/artifacts/trade-04/marker-B-first-paint-0ms-390.png`
- `tests/research/artifacts/trade-04/marker-C-packed-390.png`
- `tests/research/artifacts/trade-04/marker.html`
- `tests/research/artifacts/trade-04/regression-01/01-home-375.png`
- `tests/research/artifacts/trade-04/regression-01/01-home-390.png`
- `tests/research/artifacts/trade-04/regression-01/01-home-430.png`
- `tests/research/artifacts/trade-04/regression-01/02-top-five-390.png`
- `tests/research/artifacts/trade-04/regression-01/04-top-detail-390.png`
- `tests/research/artifacts/trade-04/regression-01/05-partner-preview-390.png`
- `tests/research/artifacts/trade-04/regression-01/06-partners-390.png`
- `tests/research/artifacts/trade-04/regression-01/07-filter-390.png`
- `tests/research/artifacts/trade-04/regression-01/08-karlheinz-390.png`
- `tests/research/artifacts/trade-04/regression-01/09-karlheinz-smartdeal-390.png`
- `tests/research/artifacts/trade-04/regression-01/10-manual-end-390.png`
- `tests/research/artifacts/trade-04/regression-01/11-receive-open-390.png`
- `tests/research/artifacts/trade-04/regression-01/12-give-continuation-390.png`
- `tests/research/artifacts/trade-04/regression-01/checks.json`
- `tests/research/artifacts/trade-04/regression-01/index.html`
- `tests/research/artifacts/trade-04/regression-02/01-home-1280.png`
- `tests/research/artifacts/trade-04/regression-02/01-home-390.png`
- `tests/research/artifacts/trade-04/regression-02/02-fatima-deal-1280.png`
- `tests/research/artifacts/trade-04/regression-02/02-fatima-deal-390.png`
- `tests/research/artifacts/trade-04/regression-02/03-sent-1280.png`
- `tests/research/artifacts/trade-04/regression-02/03-sent-390.png`
- `tests/research/artifacts/trade-04/regression-02/04-two-before-1280.png`
- `tests/research/artifacts/trade-04/regression-02/04-two-before-390.png`
- `tests/research/artifacts/trade-04/regression-02/05-three-after-1280.png`
- `tests/research/artifacts/trade-04/regression-02/05-three-after-390.png`
- `tests/research/artifacts/trade-04/regression-02/06-fourth-blocked-1280.png`
- `tests/research/artifacts/trade-04/regression-02/06-fourth-blocked-390.png`
- `tests/research/artifacts/trade-04/regression-02/07-pool-1280.png`
- `tests/research/artifacts/trade-04/regression-02/07-pool-390.png`
- `tests/research/artifacts/trade-04/regression-02/08-karlheinz-1280.png`
- `tests/research/artifacts/trade-04/regression-02/08-karlheinz-390.png`
- `tests/research/artifacts/trade-04/regression-02/checks.json`
- `tests/research/artifacts/trade-04/regression-02/index.html`
- `tests/research/artifacts/trade-04/regression-03/01-valentin-waiting-1280.png`
- `tests/research/artifacts/trade-04/regression-03/01-valentin-waiting-375.png`
- `tests/research/artifacts/trade-04/regression-03/01-valentin-waiting-390.png`
- `tests/research/artifacts/trade-04/regression-03/01-valentin-waiting-430.png`
- `tests/research/artifacts/trade-04/regression-03/02-fatima-incoming-1280.png`
- `tests/research/artifacts/trade-04/regression-03/02-fatima-incoming-375.png`
- `tests/research/artifacts/trade-04/regression-03/02-fatima-incoming-390.png`
- `tests/research/artifacts/trade-04/regression-03/02-fatima-incoming-430.png`
- `tests/research/artifacts/trade-04/regression-03/03-fatima-mirrored-1280.png`
- `tests/research/artifacts/trade-04/regression-03/03-fatima-mirrored-375.png`
- `tests/research/artifacts/trade-04/regression-03/03-fatima-mirrored-390.png`
- `tests/research/artifacts/trade-04/regression-03/03-fatima-mirrored-430.png`
- `tests/research/artifacts/trade-04/regression-03/04-fatima-before-accept-390.png`
- `tests/research/artifacts/trade-04/regression-03/05-fatima-accepted-1280.png`
- `tests/research/artifacts/trade-04/regression-03/05-fatima-accepted-375.png`
- `tests/research/artifacts/trade-04/regression-03/05-fatima-accepted-390.png`
- `tests/research/artifacts/trade-04/regression-03/05-fatima-accepted-430.png`
- `tests/research/artifacts/trade-04/regression-03/06-valentin-accepted-1280.png`
- `tests/research/artifacts/trade-04/regression-03/06-valentin-accepted-375.png`
- `tests/research/artifacts/trade-04/regression-03/06-valentin-accepted-390.png`
- `tests/research/artifacts/trade-04/regression-03/06-valentin-accepted-430.png`
- `tests/research/artifacts/trade-04/regression-03/07-fatima-declined-1280.png`
- `tests/research/artifacts/trade-04/regression-03/07-fatima-declined-375.png`
- `tests/research/artifacts/trade-04/regression-03/07-fatima-declined-390.png`
- `tests/research/artifacts/trade-04/regression-03/07-fatima-declined-430.png`
- `tests/research/artifacts/trade-04/regression-03/08-valentin-declined-1280.png`
- `tests/research/artifacts/trade-04/regression-03/08-valentin-declined-375.png`
- `tests/research/artifacts/trade-04/regression-03/08-valentin-declined-390.png`
- `tests/research/artifacts/trade-04/regression-03/08-valentin-declined-430.png`
- `tests/research/artifacts/trade-04/regression-03/09-fatima-expired-1280.png`
- `tests/research/artifacts/trade-04/regression-03/09-fatima-expired-375.png`
- `tests/research/artifacts/trade-04/regression-03/09-fatima-expired-390.png`
- `tests/research/artifacts/trade-04/regression-03/09-fatima-expired-430.png`
- `tests/research/artifacts/trade-04/regression-03/10-dev-roles-390.png`
- `tests/research/artifacts/trade-04/regression-03/11-slot-before-decline-390.png`
- `tests/research/artifacts/trade-04/regression-03/12-slot-after-decline-390.png`
- `tests/research/artifacts/trade-04/regression-03/checks.json`
- `tests/research/artifacts/trade-04/regression-03/index.html`
- `tests/research/artifacts/trade-04/scope-checks.json`
- `tests/research/artifacts/trade-04/trade-stack-10.png`
- `tests/research/artifacts/trade-04/trade-stack-37.png`
- `tests/research/artifacts/trade-04/trade-stack-6.png`
- `tests/research/artifacts/trade-04/wall-stack-10.png`
- `tests/research/artifacts/trade-04/wall-stack-37.png`
- `tests/research/artifacts/trade-04/wall-stack-6.png`
