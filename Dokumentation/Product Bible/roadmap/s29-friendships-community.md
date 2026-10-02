# S29 – Freunde, Blockieren, Aktivitätsstatus und Tauschpotenzial

## Verbindlicher Scope

S29 ergänzt die Community-Grundlage. Die bestehende Inventory-, Snapshot-,
Coverage-, TopMatch-, Smart-Request-, Trade-Lifecycle-, Notification-, Privacy-
und Rating-Fachlogik bleibt unverändert. Neue Interaktionen verwenden diese
Projektionen ausschließlich lesend.

## Architektur und Datenmodell

Migration V0009 ergänzt vier getrennte persistente Bereiche:

- `friendship_requests`: gerichtete Anfragen mit `pending`, `accepted`,
  `declined` oder `cancelled`;
- `friendships`: genau eine kanonische, beidseitige Verbindung je Nutzerpaar,
  ausschließlich im Zustand `accepted`;
- `user_blocks`: gerichtete Blockierung;
- `user_activity`: letzter Zeitpunkt einer erfolgreich persistierten
  fachlichen Mutation.

Eine entfernte Freundschaft wird physisch gelöscht. V0009-Backout ist
fail-closed und verweigert den Rückbau, solange einer dieser Bereiche Daten
enthält. Die lokale Entwicklungsdatenbank wird in S29 nicht migriert.

## Friendship-State-Machine

```text
pending --Empfänger--> accepted
pending --Empfänger--> declined
pending --Absender----> cancelled
accepted --Teilnehmer-> physisch gelöscht
```

Eine Gegenanfrage führt atomar zur Freundschaft, schließt beide offenen
Anfragen als `accepted` und erzeugt für beide Nutzer je eine deduplizierte
`friend_accepted`-Notification. Im normalen Annahmepfad erhält der ursprüngliche
Absender die Annahmebestätigung. Es gibt keine Notification für Ablehnung,
Abbruch oder Entfernen.

## Berechtigungen und zentrale Interaktionsmatrix

| Aktion | Voraussetzung | Wirkung |
|---|---|---|
| Anfrage senden | fremder, existierender, nicht blockierter Nutzer | `pending` oder Kreuzannahme |
| annehmen/ablehnen | Empfänger einer offenen Anfrage | Zustandswechsel |
| zurückziehen | Absender einer offenen Anfrage | `cancelled` |
| Freundschaft entfernen | Teilnehmer | Freundschaft löschen |
| blockieren | fremder Nutzer | Freundschaft löschen, offene Freundschafts- und nicht angenommene Tradeanfragen `cancelled` |
| Block aufheben | Blockierender | Block löschen; keine Wiederherstellung |

Eine Blockierung in einer Richtung verhindert neue Freundschafts-, manuelle
Trade- und Smart-Trade-Interaktionen in beiden Richtungen. Blockierte Nutzer
werden aus Suche, Partnerlisten, Coverage und TopMatch ausgeschlossen. Bereits
angenommene beziehungsweise laufende Trades, deren Versand, Empfang,
Problembehandlung, Abschluss, Bewertung, Historie und Notifications bleiben
vollständig erreichbar. Profile bleiben erreichbar und zeigen den Hinweis
„Du kannst mit diesem Nutzer derzeit nicht interagieren.“; die vorhandene
S27-Albumsichtbarkeit gilt unverändert.

## Datenfluss

```text
POST Community-Aktion
  -> FriendshipService / BlockService
  -> BEGIN IMMEDIATE + Berechtigungsprüfung
  -> persistierte Zustandsänderung
  -> TypedNotificationService (nur request/accepted)
  -> UserActivityService.touch(actor)
  -> Commit

GET Profil/Freunde/Suche
  -> CommunityReadService
  -> Friendship-/Block-/Activity-Projektion
  -> bestehende S20-Coverage und S21-TopMatch-Projektion
  -> HTML ohne Mutation
```

## Activity-Vertrag

Aktivität wird ausschließlich nach einer tatsächlich persistierten fachlichen
Mutation aktualisiert, nicht bei Login, GET, bloßem Redirect oder abgewiesener
Aktion. Die Anzeige ist nur für Freunde sichtbar:

- unter 24 Stunden: `Heute aktiv`
- 1 bis 7 Tage: `Diese Woche aktiv`
- 8 bis 30 Tage: `Kürzlich aktiv`
- älter als 30 Tage: `Länger nicht aktiv`

## Notification-Vertrag

- `friend_request`: Ziel `friendship`, `target_id` und `source_event_id` sind
  die Friendship-Request-ID.
- `friend_accepted`: Ziel `friendship`, `target_id` und `source_event_id` sind
  die Friendship-ID.
- Deduplizierung bleibt
  `recipient_id + notification_type + source_event_id`.

## Profil- und Album-Tauschpotenzial

Das fremde Profil zeigt ausschließlich:

- „Wie gut kann dieser Nutzer mir helfen?“ aus der bestehenden persönlichen
  S20-Coverage (Profilinhaber deckt Fehlbestand des Besuchers),
- den besten vorhandenen S21-TopMatch und die Anzahl ausführbarer Pakete dieses
  Matches.

Es entsteht keine neue Kennzahl und kein neues Ranking. Nur beidseitig für den
Tradepool aktivierte Alben nehmen teil; Privacy steuert allein die Darstellung.
Der Albumeinstieg verweist auf den bestehenden TopMatch-/Tradepfad.

## Read-/Write-Pfade und Seiteneffekte

Schreibend sind ausschließlich Friendship-Requests, Friendships, Blocks,
Activity-Zeitpunkte sowie die zwei neuen Notification-Typen. Das Beenden noch
nicht angenommener Tradeanfragen beim Blockieren verwendet den bestehenden
Status `cancelled`. Alle Coverage-/TopMatch-/Profilprojektionen sind read-only.

Unverändert bleiben insbesondere Inventory und Bestandsbuchung, Lifecycle,
Reservierung, Versand, Empfang, Probleme, S18.2-Abschluss, Ratings,
Albumprivacy, S19-Snapshot, S20-Formeln und S21-Optimierungsalgorithmus.

## Risiken und Absicherung

- Race Conditions bei Kreuzanfragen werden durch `BEGIN IMMEDIATE`, kanonische
  Nutzerpaare und Unique Constraints abgefangen.
- Blockierung darf laufende Trades nicht beschädigen; ausschließlich offene
  `trade_requests` werden abgebrochen.
- Activity darf abgewiesene Aktionen nicht als Aktivität vortäuschen.
- Friend-Privacy wird über den bereits in S27 vorgesehenen Checker angebunden.
- Migration, Backout, Notification-Deduplizierung und sämtliche
  Berechtigungsmatrizen werden auf temporären Datenbanken getestet.
