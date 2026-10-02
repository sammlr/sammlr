# CB-009 – Kleine Inbox: Read-State und Retention

**Stand:** 19. August 2026
**Implementierung:** vollständig
**Technische Tests:** bestanden
**Formale Abnahme:** abgeschlossen; technisch abgenommen
**Nächster zulässiger Schritt:** CB-011

## 1. Finaler Inbox-Vertrag

Die Glocke und die Pagination öffnen die Inbox über einen nutzerbezogenen,
CSRF-geschützten `POST /notifications`. Ein direkter `GET /notifications`
verändert keine Daten und liefert nur ein CSRF-geschütztes Öffnungs-Gate, das
im Browser den kontrollierten POST auslöst.

Der POST führt in einer SQLite-Transaktion aus:

1. bereits gelesene eigene Notifications außerhalb der Retention löschen;
2. die konkrete angeforderte Seite mit maximal 25 Einträgen bestimmen;
3. ausschließlich die tatsächlich selektierten IDs des angemeldeten Nutzers
   idempotent auf `is_read=1` setzen;
4. den globalen eigenen Unread-Zähler aus dem danach persistierten Zustand neu
   berechnen;
5. die markierte Seite rendern.

Einträge anderer Seiten und anderer Nutzer bleiben unverändert. Neue
Notifications, die erst nach der abgeschlossenen Öffnung entstehen, bleiben
ungelesen. Einzelne „Als gelesen“-Buttons wurden aus dem Renderer entfernt.
Die bestehende eigentümergebundene Einzelroute bleibt als abgesicherter
Kompatibilitätspfad erhalten und wird von der Inbox nicht mehr angeboten.

## 2. Read-State, Pagination und Badge

- Sichtbar bedeutet serverseitig in genau dieser POST-Response selektiert.
- Seite 1 liest niemals Seite 2 mit; ungültige Seitennummern werden sicher auf
  den vorhandenen Bereich begrenzt.
- Wiederholung desselben POST ist idempotent.
- Das Öffnen eines erreichbaren Notification-Ziels bleibt ebenfalls eine
  eigentümergebundene Read-Aktion.
- Das Badge zeigt nach dem Seitenread die Zahl aller weiterhin ungelesenen
  eigenen Notifications, einschließlich anderer Seiten.
- Bei global null ungelesenen Einträgen wird kein Badge gerendert.

## 3. Retention-Vertrag

- Maßgeblicher Timestamp: `created_at` in UTC.
- Frist: 30 Tage.
- Exakt am Grenzwert bleibt eine gelesene Notification erhalten.
- Erst `created_at < now - 30 Tage` wird physisch gelöscht.
- Ausschließlich gelesene Notifications laufen ab; ungelesene laufen nicht ab.
- Legacy- und typisierte Notifications werden gleich behandelt.
- Cleanup erfolgt ausschließlich im kontrollierten Inbox-POST, nie in einem
  GET und nie über Feed-, Domainhistorien- oder Producerpfade.
- Ein alter ungelesener Eintrag wird beim ersten sichtbaren Abruf gelesen und
  erst bei einem späteren Cleanup entfernt. Dadurch wird keine ungelesene
  Information ungesehen gelöscht.

## 4. Ownership und Security

Alle Select-, Update-, Delete- und Count-Abfragen sind mit `user_id` des
angemeldeten Nutzers eingeschränkt. Die gelesenen IDs stammen aus der
serverseitigen Seitenselektion und nicht aus Clientdaten. Fremde oder
manipulierte Notification-IDs verändern keinen Zustand. Target-Auflösung
bleibt an Empfänger und Zielobjekt gebunden. Ein POST ohne gültigen CSRF-Token
endet mit HTTP 403 und ohne Mutation.

## 5. Schema und Migration

**Neue Migration: NEIN.** `notifications.is_read` und
`notifications.created_at` genügen. Es wurde keine V0019 angelegt, kein
Backfill ausgeführt und keine Bestandszeile umgedeutet. Die echte Bestands-DB
blieb auf V7.

## 6. Abgrenzung

- **CB-008:** Katalog mit exakt neun Typen, Dedupe und sämtliche Producer
  unverändert.
- **CB-007:** keine Kopplung an `feed_events`.
- **CB-012:** kein Vorziehen des Feed-Home-Cutovers.
- **CB-104:** keine Bündelung, Gruppierung oder algorithmische Priorisierung.
- **CB-202:** keine Push-Zustellung oder Delivery-Präferenzen.
- `user_activity`, Trade-/Problemhistorien und sonstige Fachhistorien werden
  weder als Inboxquelle genutzt noch durch Cleanup verändert.

## 7. Geänderte Dateien

- `App/services/notification_history.py`
- `App/webapp.py`
- `App/static/style.css`
- `tests/test_cb009_inbox_read_retention.py`
- angepasste Inbox-/Header-/Read-only-Vertragstests in S06, S23–S27,
  S31, S33 und S37
- `Dokumentation/Post-RC/03-closed-beta-build-plan.md`
- dieser Report

## 8. Testergebnisse

- Gezielte CB-009-Tests: **6/6**, `OK`, 0 Fehler, 0 Skips.
- Kombinierte Inbox-/UI-/Security-Suite: **101/101**, `OK`, 0 Fehler,
  0 Skips.
- Kombinierte Notification-/Trade-/Privacy-/Friendship-Suite:
  **222/222**, `OK`, 0 Fehler, 0 Skips.
- Relevante CB-008-Regression separat: **11/11**, `OK`, 0 Fehler, 0 Skips.
- Vollständige Regression Lauf 1: **656/656** in **7,840 s**, `OK`,
  0 Fehler, 0 Skips.
- Vollständige Regression Lauf 2: **656/656** in **7,757 s**, `OK`,
  0 Fehler, 0 Skips.
- `py_compile`: erfolgreich; nur zwei bereits vorhandene `SyntaxWarning`s in
  `App/webapp.py` wegen `\d` in Stringliteralen.
- `git diff --check`: ohne Befund.

Vor den beiden offiziellen Läufen deckte ein Discovery-Diagnoselauf drei
ältere Assertions auf, die im gesamten Seiten-HTML keinerlei POST-Form
zuließen. Sie wurden auf ihren eigentlichen Read-only-Bereich begrenzt, da der
neue CSRF-geschützte Glockenzugang bewusst eine POST-Form im globalen Header
ist. Der fehlgeschlagene Diagnoselauf zählt nicht als Abnahme.

## 9. Integrity, Foreign Keys und Bestands-DB

- `PRAGMA integrity_check`: `ok`
- `PRAGMA foreign_key_check`: 0 Treffer
- Schema der echten DB vor/nach der Abnahme: V7
- SHA-256 vorher:
  `3eb9da3b6d4898533030221bc80e8ed6406a25458eb8e1bca1f0e473a515b056`
- SHA-256 nachher:
  `3eb9da3b6d4898533030221bc80e8ed6406a25458eb8e1bca1f0e473a515b056`
- Echte DB durch CB-009 verändert oder migriert: **NEIN**

## 10. Product-Contract-Bewertung und Restrisiken

Der freigegebene CB-009-Vertrag ist vollständig umgesetzt. Es gibt keine neue
Notification-Semantik, keinen neuen Producer und keine Kopplung an Feed oder
Fachhistorien. Die physische Retention ist bewusst opportunistisch an das
kontrollierte Öffnen der Inbox gebunden; ohne Inbox-Aufruf findet kein
Hintergrund-Cleanup statt. Das entspricht der freigegebenen kleinen
Closed-Beta-Variante und vermeidet einen neuen Job oder eine Migration.

- Product-Contract-Verletzung: **NEIN**
- Migration: **NEIN**
- CB-009 formal abgeschlossen und technisch abgenommen: **JA**
- CB-011 bereit: **JA**
