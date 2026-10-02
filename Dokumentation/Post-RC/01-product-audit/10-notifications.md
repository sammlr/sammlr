# Product Audit – Benachrichtigungen / Glocke

**Stand:** 16. August 2026
**Status:** Product-Owner-Entscheidungen dokumentiert; keine Implementierung, UI-, Test- oder Datenmodelländerung
**Technische Bestandsverträge:** [S23 – Typisierte Notifications](../../Product%20Bible/roadmap/s23-typed-notifications.md), [S24 – Historie, Badge und Navigation](../../Product%20Bible/roadmap/s24-notification-history-navigation.md)
**Verbindliche Home-Abgrenzung:** [Audit 09 – sammlr. Home / Feed](09-sammlr-home-feed.md)

## 1. Zweck und Verhältnis zum Bestand

Dieses Audit definiert die Produktrolle der Glocke nach dem Release Candidate. S23, S24, bestehende Product-Bible-Aussagen und die aktuelle Oberfläche bleiben als technische beziehungsweise historische Verträge erhalten. Abweichungen werden ausdrücklich dokumentiert und nicht als bereits umgesetzt ausgegeben.

## 2. Verbindliche Produktrolle

> Die Glocke ist die persönliche Inbox des Nutzers. Sie sagt „Schau hier hin“, bleibt klein, ruhig und abarbeitbar und führt zu genau dem fachlichen Vorgang, der Aufmerksamkeit verdient.

Die Glocke ist keine Sammlerchronik, Newsseite, Tradeverwaltung oder dauerhafte Ereignishistorie.

| Bereich | Produktfrage |
|---|---|
| Glocke | Was verdient meine direkte Aufmerksamkeit? |
| sammlr.-Feed | Was ist in meiner Sammlerwelt passiert? |
| Tauschzentrale | Wo bearbeite ich meine Trades? |

Eine Notification informiert und navigiert. Komplexe Aktionen wie Annehmen, Ablehnen, Versand, Empfang oder Problembearbeitung finden im konkreten Anfrage- beziehungsweise Trade-Kontext statt.

## 3. Verbindlicher Notification-Katalog

### Ereignisse, die grundsätzlich eine Notification erzeugen

| Ereignis | Ziel | Technischer Ist-Stand |
|---|---|---|
| neue manuelle Tauschanfrage | konkrete Anfrage | typisiert als `trade_request_created` vorhanden |
| neue Smart-Tauschanfrage | konkrete Anfrage | typisiert als `smart_trade_request_created` vorhanden; dies ist eine direkte Anfrage, nicht bloß ein neuer SmartMatch |
| eigene Tauschanfrage wurde abgelehnt | Anfrage-/Trade-Kontext, sofern noch sinnvoll | wird heute nur als ungezielter Legacy-Hinweis erzeugt; kein typisierter Vertrag |
| Tauschpartner hat Sticker versendet | konkreter laufender Trade | typisiert als `trade_shipped` vorhanden |
| Bewertung eines abgeschlossenen Trades ist möglich | abgeschlossener Trade beziehungsweise Bewertung | technisch nicht als Notification vorhanden |
| neue Freundschaftsanfrage | Freundschaftsanfrage beziehungsweise Profilkontext | typisiert als `friend_request` vorhanden; Ziel ist derzeit die allgemeine Freundeseite |
| relevanter Problemzustand eines Trades | betroffener Trade | kein vollständiger typisierter Notification-Vertrag; „Tausch geplatzt“ existiert nur als Legacy-Hinweis für einen Teilfall |
| bestehende Tauschanfrage ist nicht mehr erfüllbar | betroffene Anfrage | fachlicher Smart-Status existiert, aber keine entsprechende Notification |
| vergleichbares direktes Ereignis mit tatsächlicher Relevanz | genau ein fachlich sinnvolles Ziel | nur nach gesonderter Produktentscheidung; keine offene Generalkategorie für beliebige Meldungen |

### Ereignisse ohne Notification

| Ereignis | Richtiger Produktort | Heutiger Ist-Stand |
|---|---|---|
| eigene Tauschanfrage wurde angenommen | laufender Trade | `trade_accepted` wird heute typisiert erzeugt und kollidiert |
| Tauschpartner hat Empfang bestätigt | Status im Trade | `trade_received` wird heute typisiert erzeugt und kollidiert |
| Trade regulär abgeschlossen | Trade-Lifecycle und Historie | „Tausch abgeschlossen“ wird heute für beide Seiten als Legacy-Hinweis erzeugt und kollidiert |
| eigene Aktionen | aktueller Fachkontext | kein allgemeiner Self-Event-Guard; Abschlussmeldungen können auch die handelnde Seite erreichen |
| Freundschaftsanfrage wurde angenommen | Freundesstatus | `friend_accepted` wird heute typisiert erzeugt und kollidiert |
| Trophäe freigeschaltet | sammlr.-Feed und Profil | keine Notification vorgesehen |
| Album-Meilenstein | sammlr.-Feed | keine Notification vorgesehen |
| neuer SmartMatch ohne Anfrage | sammlr.-Feed beziehungsweise Tauschzentrale | keine Notification vorgesehen |
| normale Freundesaktivität | sammlr.-Feed | keine Notification vorgesehen |

## 4. Keine Routine-Erinnerungsserien zum Start

Für die Closed Beta gibt es zunächst keine automatische Erinnerungsserie für offenen Versand, offenen Empfang, tägliche Trade-Aufgaben oder wiederholte Bewertungsaufforderungen. Eine Bewertungsmöglichkeit erzeugt höchstens eine Notification.

Die bestehenden Typen `trade_shipping_overdue` und `trade_receipt_overdue` sowie ihre lazy Erzeugung nach fünf Werktagen beziehungsweise 14 Kalendertagen kollidieren damit. Sie gehören nicht zum neuen Closed-Beta-Katalog. Eine spätere Reminderlogik wird erst anhand realer Nutzung entschieden.

## 5. Gelesen-Vertrag

Beim Öffnen der Glocke gelten die aktuell sichtbaren Notifications als gelesen. Das Lesen der Inbox ist selbst die Read-Aktion.

Nicht erforderlich sind:

- ein Button „Als gelesen markieren“ pro Karte,
- ein zusätzlicher Button „Alle als gelesen“.

Wird der zugrunde liegende Vorgang außerhalb der Glocke erledigt, darf seine Notification ebenfalls als erledigt beziehungsweise gelesen behandelt werden. Eine bereits direkt in der Tauschbörse bearbeitete Anfrage soll nicht weiter ungelesene Aufmerksamkeit verlangen.

Die technische Umsetzung dieser Zustandskopplung ist nicht Teil des Audits. Insbesondere wird hier kein GET-Schreibpfad oder neuer Endpoint festgelegt.

## 6. Badge

Das rote Glocken-Badge bedeutet ausschließlich die Anzahl ungelesener Notifications. Es enthält keine offenen Trades, Aufgaben, historischen Meldungen, Freunde oder kombinierten Kennzahlen. Bei null ungelesenen Notifications verschwindet es.

Der heutige technische Badge-Vertrag entspricht dieser Semantik:

```sql
SELECT COUNT(*)
FROM notifications
WHERE user_id = ? AND is_read = 0
```

Gezählt werden derzeit typisierte und Legacy-Einträge gemeinsam. Die Darstellung zeigt `1` bis `99` exakt und ab `100` den Text `99+`; der zugängliche Beschriftungstext enthält weiterhin den tatsächlichen Wert. Ob die visuelle Kappung langfristig bleibt, ist eine spätere Darstellungsfrage, kein semantischer Widerspruch.

## 7. Retention statt ewiger Historie

Gelesene Notifications bleiben höchstens 30 Tage in der Inbox sichtbar. Danach können sie entfernt werden. Dauerhafte Fachhistorien verbleiben in Trade, Profil, Sammlung oder Sammlerchronik.

S24 enthält heute ausdrücklich keine Löschung, Retention oder Archivmigration. Die History-Abfrage zählt und paginiert alle eigenen Einträge ohne Altersgrenze. Das kollidiert direkt mit dem neuen Inbox-Vertrag.

## 8. Bündelung

Zusammengehörige Ereignisse dürfen gebündelt werden, damit kein Kartenhagel entsteht. Die genaue Logik bleibt offen. Bündelung darf keine relevante Handlung oder eindeutige Zielinformation verstecken.

S23 dedupliziert identische typisierte Events bereits über einen eindeutigen semantischen Schlüssel. Das verhindert Dubletten, ist aber noch keine fachliche Bündelung mehrerer verschiedener Ereignisse.

## 9. Ziel und Navigation

Jede Notification besitzt genau ein fachlich sinnvolles Ziel. Wenn ein konkreter Vorgang existiert, ist eine beliebige generische Seite nicht ausreichend.

Die S23-/S24-Grundarchitektur passt dazu: typisierte Einträge besitzen `target_type`, `target_id`, `source_event_id` und einen deduplizierten Schlüssel; das Ziel wird beim Öffnen erneut auf Existenz und Berechtigung geprüft. Trade- und Anfrageziele führen bereits zum konkreten Objekt. `friend_request` führt derzeit nur zur allgemeinen Freundeseite und muss bei einer späteren Umsetzung gegen den präziseren Zielvertrag geprüft werden.

Legacy-Einträge besitzen kein Ziel. Abgelehnte Anfragen, reguläre Abschlüsse und geplatzte Trades werden heute über solche ungezielten Altpfade erzeugt.

## 10. Push-Fähigkeit

Die fachliche Notification-Erzeugung soll später auch Push Notifications speisen können, ohne eine zweite parallele Ereignislogik zu benötigen. Push wird jetzt nicht gebaut.

Die typisierte S23-Struktur ist grundsätzlich eine geeignete Basis: Eventtyp, Empfänger, fachliches Ziel, Source-Event und Deduplizierung sind von der HTML-Karte getrennt. Noch nicht vollständig push-reif sind die gemischten Legacy-Schreibpfade, der unvollständige Eventkatalog und das Fehlen eines eigenen Zustellungs-/Kanalvertrags. Diese Lücken sind keine Freigabe für einen Push-Umbau im Product Audit.

## 11. Keine Notification-Einstellungen für die Closed Beta

Es werden zunächst keine Kategorien oder Einzelschalter für Trades, Freunde, SmartMatches, Trophäen oder Untertypen vorgesehen. Sammlr startet mit einem zurückhaltenden einheitlichen Regelwerk. Spätere Einstellungen werden erst aus realer Nutzung abgeleitet.

## 12. Beziehung zu Home und Tauschzentrale

Audit 09 ist verbindlich: Operative Notifications werden nicht zusätzlich als große Aufgabenblöcke auf Home dupliziert. Die Glocke besitzt die Aufmerksamkeitsebene; sammlr. erhält Raum für Sammlerreise, Freundesaktivitäten, Sammlr News und ausgewählte Entdeckungen.

Die heutige S25-Home dupliziert weiterhin:

- bis zu fünf Fachaufgaben unter „Das braucht dich“,
- eingehende manuelle und Smart-Tauschanfragen,
- offenen beziehungsweise überfälligen Versand und Empfang,
- Problemfälle und nicht mehr ausführbare Smart-Pakete,
- bis zu drei laufende Trades und Sendungen.

Diese Home-Projektion ist technischer Bestand, aber mit Audit 09 und diesem Inbox-Vertrag nicht mehr das langfristige Zielbild.

## 13. Technischer Ist-Stand

### Typen und Erzeugung

Der aktuelle typisierte Katalog umfasst neun Typen:

- `trade_request_created`,
- `smart_trade_request_created`,
- `trade_accepted`,
- `trade_shipped`,
- `trade_received`,
- `trade_shipping_overdue`,
- `trade_receipt_overdue`,
- `friend_request`,
- `friend_accepted`.

Zusätzlich erzeugen aktive Legacy-Pfade weiterhin untypisierte Meldungen, unter anderem für abgelehnte Anfragen, reguläre Tradeabschlüsse und „Tausch geplatzt“. Legacy-Einträge besitzen weder fachliches Ziel noch `source_event_id` oder Deduplizierung.

Der lokale Datenbank-Snapshot vom 16. August 2026 enthält 64 Legacy-Einträge und 19 typisierte Einträge. Er belegt, dass „legacy“ nicht nur ein theoretischer Migrationsfall ist; die Zahlen sind Audit-Evidenz und kein Produktvertrag.

### Aktuelle Read- und History-Logik

- `GET /notifications` markiert nichts als gelesen.
- Alle gelesenen und ungelesenen Einträge werden gemeinsam, neueste zuerst und ohne Retention paginiert.
- Seitengröße ist 25.
- „Öffnen“ ist ein POST: Nur bei weiterhin gültigem, autorisiertem Ziel wird genau dieser Eintrag gelesen und anschließend geöffnet.
- Ziellose oder nicht mehr verfügbare Einträge besitzen einen separaten POST „Als gelesen markieren“.
- Es gibt kein automatisches Markieren der sichtbaren Seite und keine allgemeine fachliche Erledigungssynchronisation.
- Eine Kreuz-Freundschaftsanfrage löscht ausnahmsweise die dazugehörige offene `friend_request`-Notification, bevor Annahmehinweise erzeugt werden; das ist kein allgemeiner Erledigt-Vertrag.

### Auth und CSRF

Notificationseite und Read-Endpunkte liegen hinter dem globalen Session-/Account-Guard. Beide Read-Mutationen sind POST-Routen und werden durch die globale CSRF-Prüfung geschützt; die gerenderten Formulare erhalten automatisch das Sessiontoken. Zusätzlich begrenzen die SQL-Updates auf `notification_id` und aktuellen `user_id`. Fremde Notifications können weder gelesen noch geöffnet werden.

Im heutigen Open-Handler wird die Datenbankverbindung zweimal angefordert, aber nur die zweite Referenz geschlossen. Das ist ein technischer Ist-Befund außerhalb der Produktentscheidung und wurde nicht verändert.

## 14. „Historischer Hinweis“ klassifiziert

V0006 gab allen bereits bestehenden Notification-Zeilen den Typ `legacy`, ohne Titel, Bedeutung oder Ziel rückwirkend zu rekonstruieren. S24 zeigt solche ziellosen Legacy-Zeilen deshalb als **„Historischer Hinweis“** und hält sie gemeinsam mit typisierten Notifications sichtbar.

Die Kennzeichnung ist eine technische Übergangs- und Kompatibilitätslogik, keine eigenständige Produktfunktion und keine fachliche Dauerhistorie. Weil heutige Altpfade weiterhin neue Legacy-Einträge erzeugen, betrifft sie jedoch nicht ausschließlich vor V0006 vorhandene Daten. Nach dem neuen Vertrag darf daraus kein ewiges Inbox-Archiv abgeleitet werden. Dieses Audit löscht keine bestehenden Einträge.

## 15. Expliziter Abgleich mit S23 und S24

| Bestandsregel | Verhältnis zum neuen Vertrag |
|---|---|
| typisierte Ziele, Empfängerprüfung und Deduplizierung aus S23 | grundsätzlich passend |
| `trade_accepted` | soll künftig keine Notification erzeugen |
| `trade_received` | soll künftig keine Notification erzeugen |
| `trade_shipping_overdue` und `trade_receipt_overdue` | kollidieren mit dem Closed-Beta-Verzicht auf Routine-Reminder |
| `friend_accepted` aus S29 | soll künftig keine Notification erzeugen |
| History-GET verändert keinen Read-State | direkte Kollision: Öffnen der Inbox soll sichtbare Einträge lesen |
| einzelne Open-/Read-Aktion markiert genau einen Eintrag | wird für Karten-Read nicht mehr benötigt; Zielöffnung bleibt fachlich sinnvoll |
| keine Retention oder Löschung | direkte Kollision mit maximal 30 Tagen für gelesene Einträge |
| Badge zählt alle eigenen ungelesenen Einträge | semantisch deckungsgleich |
| gemeinsame Legacy-/Typed-Historie | Übergang technisch nachvollziehbar, aber kein langfristiger Archivvertrag |
| S25-Aufgaben unabhängig vom Notification-Read-State | technischer Bestand, kollidiert mit der neuen Home-/Glocken-Abgrenzung |

## 16. Bewusst vertagte UX-Fragen

Nicht festgelegt werden Kartenoptik, Farben, Icons, Typografie, Animationen, Swipe-Aktionen, Gruppierungsdarstellung, Empty State, genaue Zeitdarstellung, Darstellung gelesen/ungelesen, Push-UI sowie Desktop-/Mobile-Detaildesign.

Ebenfalls später zu präzisieren sind die genaue Bündelungslogik, technische Read-Synchronisation bei extern erledigten Vorgängen, Retention-Ausführung und der konkrete Problem-Eventkatalog. Diese Fragen ändern den verbindlichen Produktumfang nicht.
