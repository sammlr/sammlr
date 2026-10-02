# CB-011 – Implementierungs- und Abnahmebericht

**Datum:** 19. August 2026
**Status:** ABGESCHLOSSEN – technisch abgenommen
**Migration:** NEIN
**Bestands-DB verändert:** NEIN

## 1. Ergebnis

CB-011 stellt für albumbezogene Tauschpartner und SmartMatch genau eine
erklärbare Priorität bereit. Angeboten werden nur bilateral ausführbare
Matches auf Basis des aktuellen S19-Availability-Snapshots. Bestehende
Reservierungen, Tradepool, Blocks und aktive Accounts wirken dadurch bereits
vor der Sortierung. Das aus einem Vorschlag bestätigte Paket wird weiterhin
unverändert als Anfrage gespeichert; spätere Bestandsabweichungen führen beim
Recheck beziehungsweise bei der Annahme fail-closed zu einer Blockierung und
nicht zu Auto-Shrink, Stickerersetzung oder Mengenänderung.

Es gab keine Änderung an zentraler Trade-, Lifecycle-, Notification-, Inbox-,
Feed- oder SuccessfulTradeProjection-Semantik.

## 2. Finaler Match-Vertrag

Für Nutzer `u`, Partner `p` und genau ein Album gelten:

- `receive_codes`: die `u` fehlenden, bei `p` aktuell effektiv verfügbaren
  unterschiedlichen Stickercodes;
- `give_codes`: die `p` fehlenden, bei `u` aktuell effektiv verfügbaren
  unterschiedlichen Stickercodes;
- `executable_quantity = min(len(receive_codes), len(give_codes))`;
- nur Matches mit `executable_quantity > 0` sind ausführbar und werden
  angeboten;
- Sortierung: `executable_quantity` absteigend, danach stabile Partner-ID
  aufsteigend; Code-Listen werden kanonisch sortiert und bestimmen die stabile
  Paketauswahl und Result-ID;
- der Score priorisiert ausschließlich. Er erzwingt weder Gleichwertigkeit
  noch Fairness und ändert keine Anfragebedingung.

Die zwei Richtungen bleiben fachlich getrennt. Insbesondere werden sie weder
addiert noch zu einem Fairnessscore umgedeutet.

## 3. Ausführbarkeit, Availability und Reservations

`ExecutableTradeMatchService` baut ausschließlich auf
`TradeCoverageService.personal_trade_coverage(...)` und damit auf
`InventoryReadService.snapshot(...)` auf. Maßgeblich ist
`effective_available`, nicht der rohe physische Bestand. Aktive Reservierungen
und bereits gebundene Mengen reduzieren die ausführbare Menge. Hypothetische,
reservierte oder nur einseitig passende Sticker erzeugen kein Match.

Der TopMatch-Optimizer verwendet dieselbe sortierte Projektion wie die
Album-Partnerliste. Bis zu drei Pakete werden in dieser Prioritätsreihenfolge
konfliktfrei gebildet. Bereits zugewiesene eigene effektive Mengen und bereits
abgedeckte Empfangscodes werden nicht nochmals verbraucht. Der frühere
parallele globale Coverage-Optimizer wurde aus dem Service entfernt; damit
existiert kein zweiter aktiver Auswahlvertrag.

## 4. Privacy, Blocks und Tradepool

- Beidseitig aktivierter Album-Tradepool bleibt Voraussetzung.
- Blocks wirken in beide Richtungen und schließen das Match aus.
- Deaktivierte Accounts werden über den bestehenden Interaction-Guard
  ausgeschlossen.
- Es wurde keine neue Friendship-Pflicht eingeführt.
- Profilprivacy bleibt gemäß bestehendem Vertrag vom Tradepool unabhängig;
  ein privates Profil allein deaktiviert kein Match.
- Albumgrenzen bleiben strikt; es gibt keine Cross-Album-Projektion.

## 5. Anfrage-Unveränderlichkeit und Race Conditions

Die bestehenden S22-Grenzen bleiben unverändert:

- vor Erstellung erfolgt der Recheck unter `BEGIN IMMEDIATE`;
- gespeichert werden exakt die bestätigten `give_codes` und `get_codes`;
- ein Retry mit identischem Vorschlag erzeugt keine fachlich abweichenden
  Inhalte;
- nach Erstellung werden Inhalte weder neu optimiert noch ersetzt;
- der Annahmepfad prüft das vollständige Paket erneut und reserviert atomar;
- bei Bestandsdrift bleibt die Originalanfrage unverändert offen/blockiert
  (`PACKAGE_CHANGED`) beziehungsweise wird nach bestehendem Vertrag obsolet;
- es gibt kein automatisches Teilpaket und keine stille Mengenreduktion.

Manuelle großzügige ungleiche Anfragen bleiben zulässig. CB-011 führt keine
mathematische Fairnessbedingung ein.

## 6. Abgrenzung

- CB-010 bleibt die read-only Erfolgswahrheit abgeschlossener Trades und ist
  keine Matchquelle.
- CB-008 Notifications und CB-009 Inbox wurden semantisch nicht verändert.
- CB-007 Feed wurde nicht verändert.
- CB-109 Cross-Album-SmartTrades und CB-203 Reputations-/Matchsignale wurden
  nicht vorgezogen.
- Keine ML-/Engagement-/Regionssignale, keine Autoannahme und kein Marktmodell.

## 7. Migration und Daten

CB-011 benötigt weder Schema noch Backfill. Es wurde keine Migration ergänzt
oder ausgeführt. Die echte Bestands-DB blieb auf Schema V7.

Bestätigte SHA-256-Baseline vor und nach der Abnahme:

`3eb9da3b6d4898533030221bc80e8ed6406a25458eb8e1bca1f0e473a515b056`

## 8. Geänderte Dateien

- `App/services/executable_trade_matches.py`: neue kanonische bilaterale
  Matchprojektion und deterministische Priorität.
- `App/services/top_match_optimization.py`: Nutzung derselben Priorität,
  konfliktfreie Pakete und Entfernung des parallelen alten Optimierers.
- `App/webapp.py`: Partnerliste nutzt die kanonische ausführbare Reihenfolge.
- `tests/test_cb011_executable_match_contract.py`: gezielter CB-011-Vertrag.
- `tests/test_s21_top_match_optimization.py`: S21-Erwartungen und
  Performanceprüfung auf den freigegebenen CB-011-Vertrag umgestellt.
- `Dokumentation/Post-RC/03-closed-beta-build-plan.md`: Abschlussstatus und
  nächster zulässiger Block.
- dieser Report.

`smart_trade_requests.py`, CB-008/009/010-Services und Migrationen mussten
nicht geändert werden.

## 9. Gezielte Tests

`tests.test_cb011_executable_match_contract`: **10/10**, `OK`, 0 Fehler,
0 Skips. Abgedeckt sind ausführbar/nicht ausführbar, beide Bestandsrichtungen,
effektive Mengen, Reservationskonflikte, bessere und gleiche Scores,
Partner-ID-Tie-Breaker, deterministische Result-ID, UI-Reihenfolge, Blocks,
private Profile, Tradepool-Opt-out, ungleiche manuelle Anfrage, exakte
Smart-Anfrage, Retry-Inhalte, Bestandsrace, kein Auto-Shrink und keine neue
Migration.

## 10. Kombinierte Suiten

- SmartMatch/Availability/Reservation/Trade einschließlich CB-010:
  **315/315** in **2,899 s**, `OK`, 0 Fehler, 0 Skips.
- Privacy/Block: **36/36** in **0,825 s**, `OK`, 0 Fehler, 0 Skips.
- Notification/Inbox: **45/45** in **0,472 s**, `OK`, 0 Fehler, 0 Skips.
- S19/S20/S21/S22 plus gezielter CB-011-Vertrag während der Integration:
  **77/77** in **1,471 s**, `OK`, 0 Fehler, 0 Skips.

Die aktive 100-Partner-Performanceprüfung ist Bestandteil der grünen
S21-Suite und misst jetzt den vollständigen produktiven Optimierungspfad.

## 11. Vollständige Regressionen

- Lauf 1: **666/666** in **7,937 s**, `OK`, 0 Fehler, 0 Skips.
- Lauf 2: **666/666** in **7,734 s**, `OK`, 0 Fehler, 0 Skips.

Beide offiziellen Läufe verwendeten das explizite S32/S35-Test-Environment und
die Paket-Discovery. Ein vorangegangener Diagnoseaufruf mit `discover -s tests`
umging das bekannte `tests/__init__.py`-Bootstrap und erzeugte deshalb
erwartungsgemäße Test-Secret-/Importfehler; er ist kein Abnahmelauf und führte
zu keiner Code- oder Datenänderung.

## 12. Technische Checks

- `PRAGMA integrity_check`: `ok`.
- `PRAGMA foreign_key_check`: 0 Treffer.
- Bestands-DB-Schema: V7.
- SHA-256 nach allen Tests: exakt bestätigte Baseline.
- Startup-Smoke auf isolierter Kopie der V7-Bestands-DB: `/login` HTTP 200.
- `py_compile`: erfolgreich; lediglich zwei bereits vorhandene
  `SyntaxWarning`s zu `\d`-Stringliteralen in `App/webapp.py`.
- `git diff --check`: ohne Befund.
- Commit: NEIN. Push: NEIN.

## 13. Product-Contract-Bewertung und Restrisiken

Keine Product-Contract-Verletzung festgestellt. Der Score ist bewusst klein,
deterministisch und rein priorisierend. Er bewertet keine Qualität und
garantiert nicht, dass ein Nutzer einen Vorschlag später annimmt. Zwischen
Anzeige und Aktion mögliche reale Bestandsänderungen bleiben unvermeidlich;
der bestehende transaktionale Recheck behandelt sie fail-closed. Transport-
Retries bleiben innerhalb des bestehenden S22-Anfragelimits; CB-011 verändert
diese Lifecycle-/Idempotenzsemantik nicht, garantiert aber identische
fachliche Inhalte statt stiller Neuoptimierung.

## 14. Abschluss und nächster Block

CB-011 ist formal abgeschlossen und technisch abgenommen. Gemäß der
eingefrorenen Implementierungsreihenfolge ist **CB-013 – Sammlung und
historische Abschlussprojektion** der nächste zulässige Closed-Beta-Block.
