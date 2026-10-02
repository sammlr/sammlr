# Stickerliste: geschützte Produktoberfläche

Die abgenommene Stickerliste ist eine eingefrorene Produktoberfläche. Ihre
feature-spezifischen Runtime-Dateien dürfen nur in einem ausdrücklich
beauftragten Stickerlisten-Paket geändert werden:

- `App/sticker_list.py`
- `App/templates/sticker_list.html`
- `App/static/sticker_list.css`
- `App/static/sticker_list.js`
- die von der Stickerliste referenzierten CEOKlaue-, Marker- und UI-Assets

Allgemeine SAMMLR-Arbeiten dürfen diese Dateien weder als Ablage für geteilte
Styles noch für fachfremde Helper verwenden. Gemeinsame Infrastruktur bleibt
in den globalen Modulen; neue Stickerlisten-spezifische Regeln müssen innerhalb
der Feature-Dateien und der Body-Klasse `.sticker-list-glassboard-page`
gekapselt bleiben.
