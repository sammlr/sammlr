# PAX-04b — Kiosktresen und Mengentiefe

Preview: http://127.0.0.1:8094/pax/

Start aus dem Repository: `.venv/bin/python -B -m App.pax`.

## Umsetzung

Alle fünf vorhandenen Kandidaten sind gleichzeitig als versetzte, leicht rotierte Packs sichtbar. Native Links öffnen direkt den jeweiligen Inhalt; Space ergänzt die native Enter-Bedienung. Fokusmarkierung, dezentes Hover-Feedback und Reduced Motion sind berücksichtigt. Register, Behälter, Auswahlzustand, Zähler und Vor-/Zurückbedienung entfallen. Die Packgrößen sind subtil abgestuft, nicht proportional zur Menge.

Receive behält das bestehende Zweispaltenlayout und die unveränderte Frontkartengeometrie. Nur dekorative Papierlagen zeigen die quantisierte Tiefe:

| Menge | Hintere Lagen | Tiefe nach oben |
| --- | ---: | ---: |
| 1 | 0 | 0 px |
| 2–4 | 2 | 3 px |
| 5–9 | 4 | 7 px |
| 10–19 | 6 | 11 px |
| 20–29 | 7 | 14 px |
| 30+ | 8 | 16 px |

Die Front liegt stets am selben Grid-Anker. Maximal acht zusätzliche Elemente, unabhängig von der tatsächlichen Menge. Dekorative Lagen enthalten keine erfundenen Stickercodes. Die separaten Mengentestfälle 3/6/15/37 werden ausschließlich im Browsertest erzeugt; die Kandidatenfixtures bleiben unverändert.

## Geänderte und neue Dateien

Bestehende Dateien:

- `App/templates/pax/base.html` — Preview-Kennung 04b.
- `App/templates/pax/discovery.html` — gemeinsame Auslage mit fünf direkten Links.
- `App/static/pax/pax.css` — isolierte Auslage und Papierlagen; bestehende Detail-/Post-it-Regeln beibehalten.
- `App/static/pax/pax.js` — Register entfernt, Space-Aktivierung, gedeckelte Mengentiefe.
- `tests/test_pax_preview.py` — Discovery-Vertrag angepasst.
- `tests/research/check_pax_04.py` — Kompatibilitätseinstieg auf aktuellen Browsercheck; alte Artefakte bleiben erhalten.
- `tests/research/check_pax_component_parity.py` — kanonische Frontkartenparität statt inzwischen bewusst abgelöster Pack-/Registergeometrie.

Neue Dateien:

- `tests/research/check_pax_04b.py`.
- `tests/research/artifacts/pax-04b/` — zehn Screenshots, `checks.json`, `index.html`, `scope-check.json`.
- `docs/PAX_04B_AUDIT.md`.

## Prüfungen

- 6 isolierte Pax-Unittests bestanden; GET-only, unbekannte Kandidaten, keine DB-Verbindung, kein Produkt-App-Import, korrekte Instanzen.
- 29 produktive Stack-/Stickerlisten-Regressionstests bestanden, separat ausgeführt.
- Der erste gemeinsame Unittest-Aufruf meldete einen Import-Isolationsfehler, weil die Produkt-Regressionstests selbst `webapp` importieren. Die isolierte Ausführung besteht; kein Produktimport im Pax-Pfad.
- Browsercheck bei 375/390/430 px: exakt fünf gleichzeitig sichtbare und nicht verdeckte Pack-Kerninformationen; jeder Kandidat direkt per Klick erreichbar; kein horizontaler Overflow.
- Touch, Tab-Reihenfolge, Enter, Space, sichtbarer Fokus und Reduced Motion für alle fünf Kandidaten geprüft.
- Fatima: sechs Alben, zwei Spalten, individuelles Auslegen/Zusammenlegen und Wiederherstellung der Positionen.
- Justus: 37er-Receive, Fortsetzung 16/20/1, keine wiederholten Albumüberschriften, keine interaktiven Give-Einträge; Papierüberlappung verdeckt keinen Text.
- Grenzen der 16/20-Aufteilung geprüft. Mehrfachexemplare bleiben einzelne Instanzen.
- Keine Kartenkollisionen, keine Codeüberläufe, CTA erreichbar; CTA bleibt lokale Demo. Keine schreibenden Browserrequests, keine JS-/Assetfehler.
- 3/6/15/37: identische Frontabmessungen und relative Positionen, gedeckelte Lagenanzahl, Front über allen Papierlagen. Screenshots visuell geprüft.
- Frontkarten-CSS/Geometrie gegen produktive CSS-Referenz bei allen drei Mobilbreiten geprüft.
- `git diff --check` und zusätzliche Whitespace-Prüfung aller neuen/geänderten Textdateien.

## Abgrenzung

SHA-256-Abgleich gegen den Zustand vor PAX-04b: Änderungen ausschließlich an den oben genannten isolierten Pax-Assets/Templates und Tests/Docs. `App/pax/`-Backend und Fixtures, produktiver Stack, produktive Stickerliste, V1/V2-Preview, DB und `SAMMLRPAX_CONTRACT_V1.md` unverändert. Bestehende fremde Arbeitskopieänderungen nicht angefasst. Keine Domainänderung, echte Anfrage, Reservation, Slotmutation, Commit, Push oder Deployment.

Screenshot-Galerie: [PAX-04b](../tests/research/artifacts/pax-04b/index.html).
