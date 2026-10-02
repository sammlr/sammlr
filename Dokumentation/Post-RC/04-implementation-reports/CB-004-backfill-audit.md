# CB-004 – Backfill-Audit

**Stand:** 18. August 2026
**Quelle:** read-only Dry-run auf einer mit der SQLite Backup API erzeugten und
auf V0016 migrierten Kopie von
`App/Database/sammlr.db`
**Echte lokale Datenbank:** nicht verändert; SHA-256 vor/nach Prüfung
`89254d1fe02980a0ccbf85437611273ea094568a064c75ed281f9ca6a23978a0`

## Ergebnis

| Kennzahl | Anzahl |
|---|---:|
| Legacy-Zeilen insgesamt/geprüft | 61 / 61 |
| `VALID_CANONICAL_TROPHY` | 21 |
| `VALID_COMPLETION_EVIDENCE` | 0 |
| `VALID_BOTH` | 0 |
| `LEGACY_GLOBAL` | 25 |
| `LEGACY_GENERIC` | 6 |
| `NO_CANONICAL_CATALOG` | 5 |
| `AMBIGUOUS` | 4 |
| `INVALID` | 0 |
| Zulässige Trophy-Backfills | 21 |
| Zulässige Completion-Backfills | 0 |
| Verworfen/unklar | 40 |
| Konflikte im realistischen Bestand | 0 |

## Zulässige kanonische Trophy-Backfills

Alle Zuordnungen sind exakte Namensmatches gegen den unveränderten CB-005-
Katalog. `user_id` und `user_album_id` sind nur im technisch erforderlichen
Umfang aufgeführt. Der Trigger ist für jede Zielzeile verbindlich `NULL`.

| Legacy-ID | User | Album / Nutzeralbum | Legacy-Name | Legacy-Zeit | Kanonische Definition | Erlaubt |
|---:|---:|---|---|---|---|---|
| 433 | 1 | vfl / 2 | Intro | 2026-06-27 23:55:25 | `vfl.chapter.intro.v1` | CANONICAL_TROPHY |
| 434 | 1 | vfl / 2 | Große Spieler | 2026-06-27 23:55:25 | `vfl.chapter.great_players.v1` | CANONICAL_TROPHY |
| 435 | 1 | vfl / 2 | DJ Matze | 2026-06-27 23:55:25 | `vfl.special.dj_matze.v1` | CANONICAL_TROPHY |
| 1819 | 1 | wm26 / 36 | Gruppe E | 2026-07-07 20:09:58 | `wm26.chapter.group_e.v1` | CANONICAL_TROPHY |
| 1878 | 1 | wm26 / 36 | Gruppe A | 2026-07-07 20:59:49 | `wm26.chapter.group_a.v1` | CANONICAL_TROPHY |
| 1987 | 1 | wm26 / 36 | Gruppe B | 2026-07-08 21:10:23 | `wm26.chapter.group_b.v1` | CANONICAL_TROPHY |
| 2023 | 1 | wm26 / 36 | Wappenexperte | 2026-07-12 18:02:43 | `wm26.series.crests.v1` | CANONICAL_TROPHY |
| 2071 | 1 | wm26 / 36 | WM-Historie | 2026-07-14 22:23:32 | `wm26.series.history.v1` | CANONICAL_TROPHY |
| 2100 | 1 | wm26 / 36 | Teamfotograf | 2026-07-14 22:39:04 | `wm26.series.team_photos.v1` | CANONICAL_TROPHY |
| 2141 | 1 | wm26 / 36 | Etikettenknibbler | 2026-07-14 23:28:19 | `wm26.series.coca_cola.v1` | CANONICAL_TROPHY |
| 2311 | 1 | wm26 / 36 | Weltmeister | 2026-07-19 00:55:44 | `wm26.special.argentina_champion.v1` | CANONICAL_TROPHY |
| 3487 | 2 | wm26 / 73 | Intro | 2026-07-31 22:33:16 | `wm26.chapter.intro.v1` | CANONICAL_TROPHY |
| 3488 | 2 | wm26 / 73 | Gruppe A | 2026-07-31 22:33:16 | `wm26.chapter.group_a.v1` | CANONICAL_TROPHY |
| 3489 | 2 | wm26 / 73 | Wappenexperte | 2026-07-31 22:33:16 | `wm26.series.crests.v1` | CANONICAL_TROPHY |
| 3490 | 2 | wm26 / 73 | Teamfotograf | 2026-07-31 22:33:16 | `wm26.series.team_photos.v1` | CANONICAL_TROPHY |
| 3491 | 2 | wm26 / 73 | Etikettenknibbler | 2026-07-31 22:33:16 | `wm26.series.coca_cola.v1` | CANONICAL_TROPHY |
| 3494 | 2 | vfl / 61 | Intro | 2026-08-01 21:36:22 | `vfl.chapter.intro.v1` | CANONICAL_TROPHY |
| 3893 | 2 | vfl / 61 | DJ Matze | 2026-08-03 20:57:40 | `vfl.special.dj_matze.v1` | CANONICAL_TROPHY |
| 3898 | 2 | vfl / 61 | Fanshop | 2026-08-04 18:41:57 | `vfl.chapter.fan_shop.v1` | CANONICAL_TROPHY |
| 3908 | 2 | vfl / 61 | Spiele für die Ewigkeit | 2026-08-04 18:44:25 | `vfl.chapter.eternal_matches.v1` | CANONICAL_TROPHY |
| 4086 | 1 | vfl / 2 | Legenden 11 | 2026-08-15 00:09:15 | `vfl.chapter.legends_11.v1` | CANONICAL_TROPHY |

Die SQLite-Form `YYYY-MM-DD HH:MM:SS` stammt aus dem fachlichen
`unlocked_at`-Feld mit `CURRENT_TIMESTAMP`-UTC-Semantik und wird beim Apply in
`YYYY-MM-DDTHH:MM:SS.000000Z` normalisiert.

## Completion-Kandidaten

Keine Zeile erfüllt den vollständigen Vertrag. Insbesondere wird weder aus
heutigem Bestand noch aus einer nicht katalogvalidierbaren Trophy ein Abschluss
abgeleitet.

## Verworfen und Gründe

| Kategorie | Legacy-IDs | Grund / Status | Erlaubt |
|---|---|---|---|
| `AMBIGUOUS` | 2, 3, 4, 6 | Namen `Anfänger`, `Schulhof-Tauscher`, `Stickerjäger`, `Experte` besitzen kein exaktes CB-005-Mapping | NONE |
| `LEGACY_GENERIC` | 5, 347, 431, 1877, 3486, 3493 | `Erster Sticker`/`Halbzeit` sind generische Legacy-Meilensteine | NONE |
| `LEGACY_GLOBAL` | 424–430, 1171–1179, 3492, 3500–3504, 3894, 3987, 3998 | globale Sticker-/Doppelten-/Trade-Trophäen liegen außerhalb des kanonischen Albumkatalogs | NONE |
| `NO_CANONICAL_CATALOG` | 597–600, 3696 | EM24 besitzt keinen freigegebenen kanonischen Trophy-Katalog | NONE |

Es gab auf dieser Kopie keine bestehende kanonische Trophy oder Completion und
daher keinen realen `CONFLICT`. Der Service klassifiziert abweichende bestehende
kanonische Zeitpunkte sowie widersprüchliche Legacy-Zeitpunkte fail-closed als
`CONFLICT`; identische Mehrfachevidenz erhält nur für die kleinste Legacy-ID
einen Kandidaten.

## EM24-Sonderfall

| Legacy-ID | User / Nutzeralbum | Name | Legacy-Zeit | Kategorie | Ergebnis |
|---:|---|---|---|---|---|
| 597 | 1 / 1 | Album vollendet | 2026-07-01 15:57:30 | `NO_CANONICAL_CATALOG` | weder Trophy noch Completion |
| 598 | 1 / 1 | Erster Sticker | 2026-07-01 15:57:30 | `NO_CANONICAL_CATALOG` | NONE |
| 599 | 1 / 1 | Halbzeit | 2026-07-01 15:57:30 | `NO_CANONICAL_CATALOG` | NONE |
| 600 | 1 / 1 | Endspurt | 2026-07-01 15:57:30 | `NO_CANONICAL_CATALOG` | NONE |
| 3696 | 2 / 7 | Erster Sticker | 2026-08-01 23:33:53 | `NO_CANONICAL_CATALOG` | NONE |

Row 597 ist zwar namentlich Abschluss-Evidenz, kann ohne freigegebenen EM24-
Katalog aber nicht eindeutig als gültige kanonische Abschluss-Trophäe validiert
werden. PO-07 erlaubt kein Raten; der bekannte heutige Bestand 709/728 ist kein
historischer Beleg.

## Apply-Nachweis auf zweiter isolierter Kopie

| Tabelle | Vorher | Nach Apply | Nach Repeat |
|---|---:|---:|---:|
| `canonical_trophy_unlocks` | 0 | 21 | 21 |
| `historical_album_records` | 0 | 0 | 0 |
| `unlocked_trophies` | 61 | 61 | 61 |
| `notifications` | 87 | 87 | 87 |
| `feed_events` | 0 | 0 | 0 |

Users (4), Nutzeralben (8), Inventory (1968), Trade Requests (18), Trades (10)
und Tradepositionen (62) blieben nach Count und Inhalts-SHA-256 unverändert.
Alle 21 Backfill-Trophäen besitzen `source_type=legacy_trophy_backfill`, eine
Legacy-Row-basierte `source_key` und `trigger_sticker_code=NULL`. Repeat-Apply
meldete 0 Trophy- und 0 Completion-Writes. `integrity_check=ok` und
`foreign_key_check` ohne Treffer.
