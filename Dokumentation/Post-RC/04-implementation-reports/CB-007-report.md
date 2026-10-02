# CB-007 – Implementierungsreport

**Stand:** 2026-08-18

**Branch:** `feature/wm-special-trophies`

**Status:** ABGESCHLOSSEN – technisch abgenommen

## 1. Implementierter Datenvertrag

Der bereits mit V0013 eingeführte Eventstore `feed_events` ist die einzige
kanonische Feed-Datengrundlage. CB-007 erzeugt ausschließlich reale neue
Ereignisse ab V0018; vorhandene Bestände, Albumzuordnungen, Trophäen,
Notifications und `user_activity` werden weder rekonstruiert noch migriert.

Zulässige CB-007-Typen sind:

- `album_started`
- `album_completed`
- `trophy_unlocked`
- `sammlr_news`

V0018-Trigger verweigern neue beziehungsweise umtypisierte
`album_progress`-/`trade_milestone`-Zeilen. Der Read-Service filtert zusätzlich
auf den freigegebenen Katalog. SmartMatches, normale Bestandsänderungen,
Tradeereignisse, Notifications und grobe Aktivitätszeitpunkte sind keine
Feedquelle.

## 2. Migration

Migration **JA**, V0018
`feed_eventstore_operationalization`, ausschließlich additiv:

- neue Tabelle `sammlr_news` für stabile Newsidentität, Titel, Inhalt,
  optionalen internen Zielpfad und Veröffentlichungszeitpunkt,
- kanonischer Sortierindex auf
  `feed_events(occurred_at DESC, event_key DESC)`,
- News-Zeitindex,
- Insert-/Update-Trigger für den eingefrorenen Eventtypkatalog.

Die bestehende Tabelle `feed_events` wurde nicht ersetzt und keine Zeile wurde
eingefügt, gelöscht oder umgedeutet. Das Down-Skript entfernt nur V0018-Struktur
und verweigert den Verlust bereits veröffentlichter News fail-closed.

## 3. Eventidentität und Deduplizierung

Die stabilen Fachschlüssel lauten:

- `feed:album-start:<user_album_id>`
- `feed:album-completion:<user_album_id>`
- `feed:trophy-unlock:<user_album_id>:<trophy_definition_id>`
- `feed:sammlr-news:<news_key>`

`feed_events.event_key UNIQUE` erzwingt Deduplizierung. Identischer Retry liest
den vorhandenen Fakt und meldet `created=False`; derselbe Key mit abweichendem
Typ, Ziel oder Zeitpunkt erzeugt einen Konflikt und überschreibt nichts.

## 4. Sortierstrategie

Der Read-Vertrag ist strikt und deterministisch:

```text
occurred_at DESC, event_key DESC
```

Neue Producer akzeptieren ausschließlich kanonische UTC-Zeitpunkte im Format
`YYYY-MM-DDTHH:MM:SS.ffffffZ`. Der fachliche Event-Key ist auch bei identischen
Zeitpunkten über Datenbankkopien hinweg ein stabiler Tie-Breaker; eine
algorithmische Sortierung oder Prioritätszahl existiert nicht.

## 5. Albumstart-Producer

`AlbumHistoryCutoverService.add(...)` schreibt das Event nur, wenn dieselbe
Operation tatsächlich erstmals eine `user_albums`-Zuordnung und den
CB-002-Startfakt `album-start:<user_album_id>` erzeugt. Membership, Historie und
Feed liegen im selben Savepoint. Retry erzeugt weder neuen Start noch zweiten
Feed-Eintrag; ein Feedfehler rollt auch Membership und Startfakt zurück.

## 6. Completion-Producer

`HistoricalInventoryWriteService` konsumiert ausschließlich einen im selben
Mutationsmoment neu erzeugten CB-003-Fakt. `completed_at` wird unverändert als
`occurred_at` übernommen. Das Event entsteht nur bei `completion_result.created`
und kann daher weder alte Completionfakten nachtragen noch bei Wiedererreichen
von 100 Prozent duplizieren. Inventory, History, Completion, Trophy und Feed
liegen in derselben Savepoint-/Rollbackgrenze.

## 7. Trophy-Producer

Der Producer liest ausschließlich eine persistierte
`canonical_trophy_unlocks`-Zeile und kann keine DTO- oder URL-Behauptung als
Unlock akzeptieren. Seine Feedwürdigkeits-Policy ist eine explizite Menge
stabiler Definition-IDs.

Die produktive Allowlist ist vertragsgemäß leer:

```python
FEED_WORTHY_TROPHY_DEFINITION_IDS = frozenset()
```

Keine bestehende Trophy wurde durch CB-007 freigegeben. Die Completion-Trophy
ist unabhängig von einer Allowlist immer ausgeschlossen, weil derselbe Erfolg
bereits genau ein `album_completed`-Event besitzt. Ein injizierter, ausdrücklich
feedwürdiger Test-Unlock belegt den vollständigen technischen Producer,
Deduplizierung und Rollback.

## 8. Privacy, Friendship und Blocks

Eigene albumbezogene Ereignisse sind auch bei privatem Profil beziehungsweise
privatem Album sichtbar. Fremde Ereignisse benötigen gleichzeitig:

1. eine bestätigte kanonische Friendship,
2. keinen Block in irgendeiner Richtung,
3. ein aktuelles positives CB-006-Profilgate,
4. ein aktuell sichtbares Album (`public` oder für Freunde `friends`).

Offene, nur als akzeptiert markierte Requests ohne Friendship und inkonsistente
Beziehungszustände reichen nicht. Private Alben bleiben auch für Freunde
verborgen. Spätere Privatisierung oder Blockierung blendet ein persistiertes
Event beim nächsten Read aus; es wird nicht als Sichtbarkeitssnapshot
weitergegeben.

`ProfilePrivacyService.visible_collector_world_owner_ids(...)` und
`AlbumPrivacyService.visible_user_album_ids(...)` bilden gebündelte zentrale
Policy-Grenzen. Die Feedprojektion führt keine Privacy-Abfrage je Event aus.

## 9. News-Regel

`FeedEventService.publish_news(...)` ist der einzige Schreibweg. Er besitzt
stabile News-/Eventkeys, exakte Retryprüfung, kanonische UTC-Zeit und erlaubt
nur interne Zielpfade. Es gibt keine öffentliche Route, kein CMS, keine
Entwurfszustände und keine algorithmische Gewichtung.

Eine Response enthält maximal ein `sammlr_news`-Event. Eigene und sichtbare
Freundesereignisse füllen das angeforderte Limit zuerst; nur ein verbleibender
Platz kann von der neuesten geeigneten News belegt werden. Innerhalb der
Response bleibt die bestätigte kanonische Zeitordnung erhalten.

## 10. Bewusst ausgeschlossene Features

Nicht umgesetzt wurden Likes, Kommentare, Reaktionen, SmartMatches,
Progress-Feed, Tradefeed, Engagement-Scores, algorithmische Sortierung,
News-CMS, Feed-UI, Pagination-/Infinite-Scroll-UX, Notification-Katalog und
weitere Social-Funktionen. Home bleibt bis CB-012 unverändert.

Tradepool, Matchbarkeit, Reservierungen, Trade Requests und laufende Trades
werden weder gelesen noch durch Feed-/Privacyänderungen beeinflusst.

## 11. Export und bestehende Verbraucher

Der bestehende S36-Vollständigkeitsvertrag erfordert eigene Aktivitätsdaten.
`UserDataExportService` exportiert deshalb deterministisch ausschließlich
Feed-Ereignisse mit `actor_user_id` des Subjekts. Globale News und Ereignisse
anderer Nutzer werden nicht in den persönlichen Export hineingezogen. Die
Exportformatversion und alle bestehenden Bereiche bleiben unverändert.

## 12. Geänderte Dateien

Fachcode:

- `App/services/feed_events.py`
- `App/services/history_cutover.py`
- `App/services/historical_collection.py`
- `App/services/profile_privacy.py`
- `App/services/album_privacy.py`
- `App/services/user_data_export.py`

Schema und Runtime:

- V0018 Up/Down unter `App/Database/migrations/`
- `App/services/runtime_operations.py`
- `Scripts/s35_performance_baseline.py`
- Latest-Schema-Erwartungen der betroffenen S26–S38-/Post-RC-Tests
- S34 Deployment-/Recovery-Dokumente

Tests und Dokumentation:

- `tests/test_cb007_feed_eventstore.py`
- S36-Exporttests
- Closed-Beta-Bauplan und dieser Report

Keine sichtbare UI-, Notification-, Home-, Trade- oder SmartMatch-Produktlogik
wurde geändert.

## 13. Gezielte Tests

`tests.test_cb007_feed_eventstore`: **11/11** in **0,103 s**, `OK`, 0 Fehler,
0 Skips.

Abgedeckt sind Migration/Repeat-up/Safe-down, Eventpersistenz, Konflikt-
Deduplizierung, strikte Zeitordnung und Tie-Breaker, Owner, bestätigte Freunde,
Pending/inkonsistent, Blockvorrang, public/private Profil, alle relevanten
Albumstufen, Albumstart, Completion, Rollback, leere Trophy-Allowlist,
kontrollierter Test-Unlock, Completion-Trophy-Unterdrückung, kontrollierte News,
Newsdominanz, SmartMatch-Ausschluss, Tradepool-Unabhängigkeit, keine
Notification-/`user_activity`-Reads sowie Feedexport-Ownership.

## 14. Kombinierte Suite

CB-001/002/003/005/006/007 zusammen mit S26, S27, S29, S32, S33, S34, S35,
S36 und S38: **156/156** in **3,451 s**, `OK`, 0 Fehler, 0 Skips.

## 15. Vollständige Regressionen

- Lauf 1: **639/639** in **7,626 s**, `OK`, 0 Fehler, 0 Skips.
- Lauf 2: **639/639** in **7,629 s**, `OK`, 0 Fehler, 0 Skips.

Beide finalen Läufe verwendeten einen expliziten Wegwerf-`DATABASE_PATH`, damit
kein Testimport die echte lokale DB als Ziel auswählen konnte.

## 16. Isolierter realistischer Daten-Smoke

Die S34-Backup-API erstellte aus der aktuellen lokalen V7-Datei:

`/private/tmp/sammlr-cb007-audit.nBmOS2/sammlr-20260818-204808-v0007.db`

Backup-Hash:
`c42a0970c0aef4db1c89e4b3077d6770c1f52d3b70830518649b89a1bf27f764`.

Auf der Kopie wurden V8–V18 angewendet; Repeat-up war leer. Migration allein
ließ die Kerncounts unverändert: 4 Nutzer, 3 Alben, 8 Zuordnungen, 1969
Stickerpositionen, 18 Requests, 10 Lifecycle-Trades, 87 Notifications und 61
Legacy-Trophäen. `feed_events` blieb nach Migration bei 0: kein Backfill.

Danach erzeugte ein realer isolierter Albumstart genau ein Event und sein Retry
kein zweites. Ein realer letzter VfL-Sticker erzeugte genau eine Completion,
eine Completion-Trophy und genau ein `album_completed`-Event, aber 0
`trophy_unlocked`-Events. Privates Freundesprofil plus bestätigte Friendship war
sichtbar; Block und anschließend private Albumstufe blendeten es aus. Zwei News
ergaben genau eine News in der Response.

Nach diesen absichtlichen Kopie-Mutationen:

- `integrity_check=ok`
- `foreign_key_check=0`
- Kopie-SHA-256:
  `13f849ef69f7ba492d83cbd17168904a881f281fa87e834941073deb88a46da6`

## 17. Startup-Smoke

Frischer Testing-Appimport gegen die isolierte V18-Kopie war erfolgreich.
`GET /healthz` lieferte HTTP 200 und `{"status":"ok"}`, `GET /login` HTTP 200.

## 18. Bestands-DB-Baseline und geklärte Abweichung

Der dokumentierte unveränderte CB-006-Endhash lautete:

`89254d1fe02980a0ccbf85437611273ea094568a064c75ed281f9ca6a23978a0`.

Beim ersten expliziten CB-007-Bestandscheck – nach den ersten Testläufen, da
leider kein separater Hash unmittelbar vor der Implementierung genommen wurde –
lautete der Hash:

`082188aba03ce712ad2df58a05f807ba5544cb5c301e5d4f4c725ad618523641`.

Die V7-Datei enthielt dabei eine zusätzliche aktuelle Stickerposition
`id=2477, user_id=1, album_id=wm26, sticker_code=FWC4, quantity=1`. Der
Dateizeitpunkt war `2026-08-18T22:26:00+0200`. Der Product Owner hat am
2026-08-18 bestätigt, dass diese Position durch eine von ihm bewusst
durchgeführte reale Browser-/Nutzeränderung entstand. Sie ist legitimer
Nutzerbestand, wurde nicht durch CB-007 verursacht und darf weder gelöscht
noch durch eine Datenbankrestaurierung zurückgesetzt werden.

Die echte DB wurde nicht migriert und blieb ab diesem ersten CB-007-Prüfpunkt
durch den isolierten Audit, beide finalen Regressionen und alle Abschlusschecks
bytegleich bei
`082188aba03ce712ad2df58a05f807ba5544cb5c301e5d4f4c725ad618523641`.
Sie steht weiterhin auf V7, `integrity_check=ok`, `foreign_key_check=0`. Es
wurde bewusst weder gelöscht noch aus einem Backup restauriert.

Mit der belastbaren Attribution durch den Product Owner ist die Abweichung zum
CB-006-Endhash fachlich geklärt. Der ab dem ersten CB-007-Prüfpunkt
unveränderte Hash `082188...` ist die neue legitime Bestands-DB-Baseline. Der
operative Daten-Sicherheitsnachweis für CB-007 ist damit geschlossen; es
besteht kein Hash- oder Abnahmeblocker mehr.

## 19. Product-Contract-Bewertung

Die implementierte Fachlogik verletzt den eingefrorenen Product Contract nicht:

- genau ein Completion-Feedereignis,
- leere produktive Trophy-Allowlist,
- höchstens eine News,
- keine algorithmische Sortierung,
- bestätigte gegenseitige Freundschaft,
- Blockvorrang,
- CB-006-Profilgate plus innere Albumprivacy,
- Tradepool unabhängig,
- SmartMatches ausgeschlossen,
- keine Ableitung aus Notifications oder `user_activity`.

**Product-Contract-Verletzung: NEIN.**

## 20. Bekannte Restrisiken

Der technische Unterbau besitzt noch keine sichtbare Feed-UI; diese gehört zu
CB-012. Der Read-Service filtert die persistierten persönlichen Kandidaten in
einer konstanten Zahl gebündelter Queries und vermeidet N+1, lädt für den
Closed-Beta-Unterbau aber noch alle Kandidaten vor der Limitierung. Eine spätere
Pagination muss Privacy korrekt vor Seitenbildung behandeln und darf die
kanonische Reihenfolge nicht verändern.

Neue feedwürdige Trophäen benötigen immer eine ausdrückliche Product-Owner-
Freigabe ihrer stabilen Definition-ID. Eine bloße neue Katalogdefinition reicht
nicht.

## 21. Empfehlung und CB-008-Bereitschaft

Code, Migration, Producer, Privacy, Tests, Startup und isolierter Daten-Smoke
sind technisch grün. Die zuvor offene Bestandszeile ist durch die
Product-Owner-Bestätigung als beabsichtigte reale Browser-/Nutzeränderung
belastbar attribuiert. Damit lautet die formale Entscheidung:

**CB-007 ABGESCHLOSSEN – technisch abgenommen.**

`FWC4` bleibt unverändert legitimer Nutzerbestand. Der Hash
`082188aba03ce712ad2df58a05f807ba5544cb5c301e5d4f4c725ad618523641`
ist die neue bestätigte Baseline. CB-007 hat die echte Bestands-DB weder
migriert noch verändert.

**CB-008 bereit: JA.** CB-008 wurde im Rahmen dieses Abschlusses nicht begonnen.

Kein Commit und kein Push wurden ausgeführt.
