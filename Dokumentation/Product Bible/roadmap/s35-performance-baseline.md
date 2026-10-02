# S35 – Performance-Baseline

Stand: 2026-08-09

## Messvertrag

Gemessen wurde mit CPython 3.13.15, Gunicorn 26.0.0, einem Worker, 20 Threads,
SQLite V0012 und 20 gleichzeitigen Requests. Die Datenbank lag ausschließlich
temporär unter `/private/tmp` und enthielt exakt 100 Nutzer, 10 Alben, 100.000
Stickerpositionen, 2.000 Trades, 5.000 Notifications und 1.000 Freundschaften.
`integrity_check` lieferte `ok`; `foreign_key_check` war leer.

Der reproduzierbare Befehl lautet:

```sh
PYTHONDONTWRITEBYTECODE=1 \
/private/tmp/sammlr-s32-py313-venv/bin/python \
Scripts/s35_performance_baseline.py \
  --database /private/tmp/sammlr-s35-performance.db \
  --output /private/tmp/sammlr-s35-performance-result.json \
  --python /private/tmp/sammlr-s32-py313-venv/bin/python
```

Die Messung bricht einen Einzelrequest nach fünf Sekunden ab. Ein solcher
Timeout liegt bereits eindeutig über der verbindlichen Release-Blocker-Grenze
von 1.000 ms und wird als Fehler gezählt. Nach einem Timeout wird Gunicorn für
die nächste Seitengruppe auf einem neuen lokalen Port neu gestartet; dadurch
verfälscht kein hängender Request die Folgemessung.

## Ergebnis

| Ablauf | P95 | Fehler | Bewertung |
| --- | ---: | ---: | --- |
| Login | 8,278 ms | 0/20 | bestanden |
| Home | 115,485 ms | 0/20 | bestanden |
| Sammlung | > 5.000 ms | 20/20 Timeouts | Release-Blocker |
| Album | > 5.000 ms | 20/20 Timeouts | Release-Blocker |
| Stickerwall | > 5.000 ms | 20/20 Timeouts | Release-Blocker |
| Suche | 1.472,898 ms | 0/20 | Release-Blocker |
| Tradebörse | > 5.000 ms | 20/20 Timeouts | Release-Blocker |
| Dealansicht | > 5.000 ms | 20/20 Timeouts | Release-Blocker |
| Notifications | > 5.000 ms | 20/20 Timeouts | Release-Blocker |
| Profil | 1.918,630 ms | 0/20 | Release-Blocker |

## Release Readiness

Die Fehlerquote von null Prozent und die P95-Grenze unter 500 ms werden nur
von Login und Home erfüllt. Alle übrigen gemessenen Kernseiten sind nach dem
verbindlichen Vertrag Release-Blocker. S35 nimmt keine automatische oder
opportunistische Optimierung vor. Eine Public Beta darf erst nach separater,
priorisierter Behebung und erneuter identischer Baseline freigegeben werden.
