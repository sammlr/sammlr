# CB-008 – Closed-Beta Notification-Katalog

**Stand:** 19. August 2026
**Implementierung:** vollständig
**Technische Tests:** bestanden
**Formale Abnahme:** abgeschlossen; technisch abgenommen
**Nächster zulässiger Schritt:** CB-009

## 1. Ziel und eingefrorener Vertrag

CB-008 beschränkt neue Notification-Writes auf exakt diese neun Typen:

1. `trade_request_created`
2. `smart_trade_request_created`
3. `trade_request_declined`
4. `trade_shipped`
5. `trade_rating_available`
6. `friend_request`
7. `trade_request_unfulfillable`
8. `trade_problem_action_required`
9. `trade_problem_terminal`

Es entstehen keine neuen Notifications für Accepted, Received, regulären
Tradeabschluss, Friend-accepted, Reminder, Trophy-/Album-/Feed-Ereignisse,
eigene Aktionen oder interne Problem-Zwischenzustände. Bestehende Altzeilen
bleiben unverändert lesbar.

## 2. Eventmatrix

| Fachvorgang | Empfänger | stabiler Dedupe-Beleg | Ergebnis |
| --- | --- | --- | --- |
| manuelle Anfrage erstellt | Gegenseite | Trade-Request-ID | genau ein `trade_request_created` |
| Smart-Anfrage erstellt | Gegenseite | Trade-Request-ID | genau ein `smart_trade_request_created` |
| Anfrage abgelehnt | ursprünglicher Absender | Trade-Request-ID | genau ein `trade_request_declined` |
| Smart-Request `open -> obsolete` | ursprünglicher Absender | Trade-Request-ID | genau ein `trade_request_unfulfillable` |
| Versand bestätigt | Gegenseite | kanonische Shipment-Event-ID | genau ein `trade_shipped` je Seite |
| eigene Aktion macht Trade erstmals bewertbar | ausschließlich Gegenseite | Lifecycle-Trade-ID | genau ein `trade_rating_available` |
| Freundschaftsanfrage | Empfänger | Friendship-Request-ID | genau ein `friend_request` |
| Problembericht persistent angelegt | Gegenseite des Melders | Problembericht-ID | genau ein `trade_problem_action_required` |
| Problem schließt Trade terminal | Gegenseite des Melders | Problembericht-ID | genau ein `trade_problem_terminal` |

Die Notification-Projektionen laufen in derselben Transaktion wie der
kanonische Fachvorgang. Ein erzwungener Fehler im Problem-Producer rollt
Problembericht, Domain-Event und Notification gemeinsam zurück.

## 3. Product-Owner-Entscheidungen

- `trade_rating_available`: Die eigene Empfangs-/Problemaktion benachrichtigt
  nur die Gegenseite; keine Self-Notification; maximal einmal pro
  Lifecycle-Trade.
- `trade_request_unfulfillable`: ausschließlich ursprünglicher Absender und
  ausschließlich der vorhandene Smart-Übergang `open -> obsolete`; keine
  Erweiterung manueller Requests.
- Problemvertrag: neuer persistierter Bericht erzeugt Action-required;
  terminales Schließen erzeugt Terminal; reguläre Lösung und
  `problem_resolved_after_close` erzeugen keinen eigenen Typ.

## 4. Implementierung

- `TypedNotificationService` besitzt den exakten Katalog, verlangt für jeden
  neuen Write eine positive stabile Source-ID und lehnt nicht zugelassene
  Typen fail-closed ab.
- Request-, Shipping-, Receipt-/Rating-, Problem-, Smart-Request- und
  Friendship-Producer wurden an den jeweiligen kanonischen Erfolgsübergang
  gebunden.
- Aktive Legacy-Fallback-Writes sowie Accepted-, Received-, Completion-,
  Friend-accepted- und Overdue-Producer wurden entfernt.
- Read-Routen erzeugen keine Reminder mehr.
- Zielauflösung bleibt nutzergebunden. Friendship-Ziele sind nur für den
  tatsächlichen Empfänger, bei noch offener Anfrage und ohne Block erreichbar.
- Notification-Writes verwenden weder `feed_events` noch `user_activity` als
  fachliche Datenquelle.

## 5. Schema und Migration

**Neue Migration: NEIN.** Es wurde keine V0019 angelegt und die vorhandene
`notifications`-Tabelle samt partiellem Unique-Index auf `dedupe_key`
weiterverwendet. Es gibt keinen Backfill und keine Umdeutung historischer
Zeilen.

Beim V18-Test wurde eine bereits vorhandene technische Inkonsistenz entdeckt:
V0011 verbot `from_confirmed=-22`, obwohl S22 genau diesen Wert als kanonischen
Smart-Request-Marker definiert. Damit wäre der bestätigte Übergang
`open -> obsolete` im Gesamtschema unerreichbar gewesen. Die noch nicht auf
der echten V7-DB angewandte V0011-Regel wurde minimal auf `-22, 0, 1`
korrigiert. Das ändert weder Schema noch Produktsemantik und fügt keine
Migration hinzu.

## 6. Bereits vor dem Verbindungsabbruch vorhanden

Beim Wiederaufnehmen waren folgende CB-008-Arbeiten bereits im Working Tree:

- exakter Katalog und neue Producer-Methoden in
  `App/services/typed_notifications.py`;
- transaktionale Shipping-, Rating- und Problem-Producer;
- Smart-Obsolete-Producer;
- Entfernung von `friend_accepted`;
- Entfernung aktiver Legacy-, Accepted-, Received-, Completion- und
  Overdue-Writes aus `App/webapp.py`;
- präziser Friendship-Deep-Link-Anker.

Ein zuvor gestarteter kombinierter Testlauf war durch den Verbindungsabbruch
nicht belastbar abgeschlossen. Ein dedizierter CB-008-Test und dieser Report
existierten noch nicht.

## 7. Nach dem Verbindungsabbruch abgeschlossen

- vorhandene Implementierung gegen alle drei PO-Entscheidungen geprüft;
- V0011-/Smart-Marker-Inkonsistenz behoben;
- dedizierte CB-008-Eventmatrix mit Rollback-, Dedupe-, Ownership- und
  Negativtests ergänzt;
- ältere S02/S03/S14/S16/S17/S18.2/S20/S23/S24/S29/S38-Erwartungen auf den
  eingefrorenen Katalog umgestellt;
- kombinierte Suite und zwei vollständige Regressionen ausgeführt;
- isolierte Migration und Datenprüfung auf einer Kopie der aktuellen echten
  DB ausgeführt;
- `py_compile` und `git diff --check` ausgeführt.

## 8. Testergebnisse

- Gezielte CB-008-Tests: **11/11**, `OK`, 0 Fehler, 0 Skips.
- Kombinierte Notification-/Trade-/Privacy-/Friendship-Suite:
  **199/199**, `OK`, 0 Fehler, 0 Skips.
- Ergänzender S03-Side-Effect-Gate: **11/11**, `OK`, 0 Fehler, 0 Skips.
- Regression Lauf 1: **650/650** in **7,689 s**, `OK`, 0 Fehler, 0 Skips.
- Regression Lauf 2: **650/650** in **7,681 s**, `OK`, 0 Fehler, 0 Skips.
- `py_compile`: erfolgreich; nur zwei bereits vorhandene `SyntaxWarning`s in
  `App/webapp.py` wegen `\d` in Stringliteralen.
- `git diff --check`: ohne Befund.

Ein früher Diagnose-Discovery ohne das vorgeschriebene explizite
Testing-Environment zählt nicht als Regression. Die beiden finalen Läufe
verwendeten jeweils eine frische Wegwerf-DB sowie
`SAMMLR_ENV=testing` und den repositoryweit erwarteten Test-Secret-Vertrag.

## 9. Integrity, FK und realistischer Daten-Audit

Eine Kopie der beim Wiederaufnehmen vorhandenen echten V7-DB wurde isoliert
über `(8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18)` migriert.

- Schema der Kopie: V18
- `PRAGMA integrity_check`: `ok`
- `PRAGMA foreign_key_check`: 0 Treffer
- typed Notifications ohne Dedupe-Key: 0
- doppelte nicht-null Dedupe-Keys: 0
- Self-Trade-Requests: 0
- historische Typen wie `trade_accepted` und `trade_received` blieben
  unverändert erhalten; es erfolgte kein Backfill.

## 10. SHA-256 und geklärte Baseline-Abweichung

Die beim Start von CB-008 zunächst herangezogene CB-007-Baseline war:

`082188aba03ce712ad2df58a05f807ba5544cb5c301e5d4f4c725ad618523641`

Bereits beim ersten Read-only-Prüfpunkt dieser Fortsetzung vor neuen Tests:

`3eb9da3b6d4898533030221bc80e8ed6406a25458eb8e1bca1f0e473a515b056`

Der Product Owner hat bestätigt, dass die Domainaktionen am 19. August 2026 um
15:03:34/15:04:06 UTC (`problem_reported`, `problem_trade_closed`) und die
daraus entstandenen Problem-Notifications aus einer bewusst durchgeführten
manuellen Browser-/Nutzerprüfung von Sammlr stammen. Sie sind legitime reale
Nutzeraktivität, wurden nicht durch CB-008 verursacht und bleiben vollständig
erhalten.

Der Hash blieb über sämtliche CB-008-Abnahmearbeiten unverändert. Die echte DB
blieb V7 und wurde weder migriert, gelöscht noch restauriert. Der ehemalige
formale Hash-Blocker ist damit fachlich geklärt.

Neue bestätigte Bestands-DB-Baseline:

`3eb9da3b6d4898533030221bc80e8ed6406a25458eb8e1bca1f0e473a515b056`

## 11. Abschlussstatus

- Implementierung vollständig: **JA**
- Neue Migration: **NEIN**
- Gezielte und kombinierte Tests grün: **JA**
- Regression zweimal grün: **JA**
- Integrity/FK grün: **JA**
- Echte DB durch die Fortsetzung verändert: **NEIN**
- Baseline-Abweichung fachlich geklärt: **JA**
- Neue bestätigte Baseline: **`3eb9da3b6d4898533030221bc80e8ed6406a25458eb8e1bca1f0e473a515b056`**
- Product-Contract-Verletzung im implementierten Katalog: **NEIN**
- CB-008 formal technisch abgenommen: **JA**
- CB-009 bereit: **JA**
