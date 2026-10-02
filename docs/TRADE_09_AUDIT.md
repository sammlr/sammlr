# TRADE-09 — Manuelle Auswahl, Abschlussaudit

Stand: 2026-10-02. Isolierte Preview; keine produktive Integration.

## Einstiege

- Preview: http://127.0.0.1:8095/trade-v2/
- Karlheinz: http://127.0.0.1:8095/trade-v2/partners/karlheinz/manual
- Albumlimit: http://127.0.0.1:8095/trade-v2/partners/karlheinz/manual?manual=same
- Beidseitig offen: http://127.0.0.1:8095/trade-v2/partners/karlheinz/manual?manual=open
- Nur einseitig offen: http://127.0.0.1:8095/trade-v2/partners/karlheinz/manual?manual=one-sided
- Album abgeschaltet: http://127.0.0.1:8095/trade-v2/partners/karlheinz/manual?manual=closed

Die Demo-Parameter setzen nur den lokalen Auswahldraft zurück und werden danach aus der URL entfernt. Für einen neuen vollständigen Durchlauf einen frischen Browserkontext verwenden oder den vorhandenen DEV-Reset nutzen. Ein bereits gebundener manueller Demo-Request wird wieder geöffnet, nicht ersetzt. Die stabile Demo-ID je Partner ist keine lebenslange produktive Angebotsbeschränkung.

## Umsetzung und begrenzte Vertragsänderung

[Vertrag](TRADE_V2_MANUAL_SELECTION_CONTRACT.md): neue Trade-v2-Angebote prüfen Albumfreigaben beider Seiten. Eingeschränkte Alben finanzieren ausschließlich sich selbst; nur beidseitig offene Alben teilen einen Pool. Receive ≤ Give, auch 2/3 erlaubt. Legacy-Vertrag und bestehende produktive Semantik bleiben unverändert.

Tauschen → Alle Sammlr → Karlheinz → Selbst auswählen nutzt die tatsächliche kanonische Stickerlisten-Quelle als Präsentationsreferenz: unveränderte produktive CSS/Fonts/Marker, gleiche Glyphen-Auswahl und Marker-DOM, isolierter Multi-Album-Controller. Produktives sticker_list.js wird wegen seiner Inventory-/Submit-Aufgaben nicht eingebunden. Spätere gemeinsame Extraktion sollte reine Präsentationsfunktionen betreffen, nicht produktive Mutationslogik.

Der gelbe Zettel zählt beide Richtungen und liegt im normalen Dokumentfluss; er verdeckt keine Controls. Auswahlgrenzen blockieren zusätzliche Auswahl, entfernen aber keine Albumsektion oder Nummer. Ohne zulässige Gegenmenge bleibt die Nummer sichtbar und erklärt die Sperre. Drafts belegen keine Slots. Review und Submit validieren erneut; veränderte/ungültige Drafts werden nicht gebunden.

Bestätigungsansicht und gesamter Lifecycle nutzen vorhandene Receive-/Give-Renderer und Requestcommands. Numerische Codes werden nur für den unveränderten kanonischen Face-Renderer als leeres Team plus Nummer adaptiert; originale Snapshotcodes bleiben identisch. Keine eigene Stackgeometrie. Reduced-motion zeigt die kanonische Kreuzmarkierung sofort vollständig.

## Nachweise

- 8 Preview-/Pax-Unit-Tests bestanden.
- 29 produktive Stickerwall-/Stickerlisten-Tests bestanden, getrennte Testprozesse.
- TRADE-01–08 Browserregressionen bestanden; historische Belege bleiben erhalten. Neue Ausgaben unter `tests/research/artifacts/trade-09/regression-01` bis `regression-08`.
- 52 neue Regelassertionen je Browserbreite (208 ausgeführte Checks): bilaterale Freigabe, eingeschränkte Pools, 2/3, Supply/Need, ungültige Identitäten, Smart-Unabhängigkeit.
- Browser 375/390/430/1280: Limit, Abwahl, Reload, einseitige Sperre, offener 5/5-Tausch, leerer/veralteter Draft, doppelte Anfrage, Drei-Slot-Sperre und vollständiger manueller 2/3-Lifecycle bis beidseitigem Abschluss.
- Touch, Tastatur und reduzierte Bewegung; keine horizontalen Überläufe, Browserfehler oder schreibenden Netzwerkanfragen.
- Kanonische Listenstile direkt mit echter produktiver Renderer-Ausgabe verglichen; synthetische read-only Dependencies, keine produktive Datenquelle.
- 28 zusätzliche numerische Face-/Stackvergleiche: vier Breiten × Mengen 1/2/5/6/10/15/37. Gleiches Face, −2/−2, z-index, Wall5/Trade10. Ab zehn Lagen konstante Geometrie. Bestehende 21 BRA-3-Vergleiche ebenfalls grün.
- Historische Modelle prüfen weiterhin Q2-Empfang ohne Partner-SHIPPED, getrennte Slots, Amendments, Problemklärung und Bewertung. Vier neue manuelle Browserjourneys ergänzen diesen gemeinsamen Lifecycle.

Reproduzierbare Tests:

```sh
.venv/bin/python -B -m unittest tests.test_trade_v2_preview tests.test_pax_preview -q
.venv/bin/python -B -m unittest tests.test_sticker_wall_product_island tests.test_ceoklaue_sticker_list -q
.venv/bin/python -B tests/research/check_trade_09_regressions.py
.venv/bin/python -B tests/research/check_trade_09.py
.venv/bin/python -B tests/research/check_trade_09_parity.py
```

Browserläufe erwarten die isolierte Preview auf Port 8095 (`.venv/bin/python -B -m App.trade_v2`).

## Artefakte, Scope und spätere Hooks

- [Screenshot-Galerie](../tests/research/artifacts/trade-09/index.html)
- [Browser-/Regelchecks](../tests/research/artifacts/trade-09/checks.json)
- [Numerische Kanonik-Parität](../tests/research/artifacts/trade-09/canonical-parity.json)
- [Vollständige Datei- und SHA-256-Liste](../tests/research/artifacts/trade-09/files.json)
- [Vorher-/Nachher-Schutznachweis](../tests/research/artifacts/trade-09/scope-checks.json)

Scope-Nachweis vergleicht die vor TRADE-09 erfassten App-/docs-/tests-Dateien: Produktiv-DBs, Stickerwall, Stickerliste, SmartDeal, Pax und Legacy unverändert. Nur acht bestehende isolierte App-/Testdateien geändert; neue Dateien ausschließlich isolierte Trade-Preview, Trade-Dokumentation und Tests/Belege. Keine Löschungen, kein git add, Commit, Push oder Deploy.

Spätere Albumsettings pro Sammler: `tradeEnabled`, `smartEnabled`, `crossAlbum`. Manual braucht beidseitiges `tradeEnabled`; Cross-Pooling zusätzlich beidseitiges `crossAlbum`; `smartEnabled` ist unabhängig. Fixtures bilden Hooks ab, keine vollständige Settings-UI. Produktive Integration benötigt autorisierte Availability-/Reservation-Reader, aktuelle beidseitige Freigaben, persistierten neuen Contract-Type und atomare Revalidierung/Bindung. Lokale Browserdaten sind keine produktive Vertrauensgrenze.
