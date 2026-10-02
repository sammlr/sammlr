# Sprint-Report S29

## Ziel und Scope

S29 ergänzt die verbindliche Community-Grundlage: beidseitige Freundschaften,
Freundschaftsanfragen, Blockierung neuer Interaktionen, grobe Aktivitätsklassen
sowie profil- und albumbezogenes Tauschpotenzial aus den bestehenden S20-/S21-
Projektionen. Die Product-Owner-Klärungen und der Nachtrag sind vollständig
umgesetzt. S30 wurde nicht begonnen.

## Architektur und Datenfluss

Die neue zentrale Service-Schicht `CommunityService` kapselt die gesamte
Friendship-State-Machine und Block-Matrix. `UserActivityService` stellt den
separaten Activity-Vertrag bereit. Beide Dienste sind über unveränderliche DTOs
beziehungsweise stabile Ergebnis-Codes angebunden.

```text
Community POST
  -> CommunityService
  -> BEGIN IMMEDIATE
  -> Berechtigungs-/Blockprüfung
  -> Request/Friendship/Block persistieren
  -> optional typisierte Notification
  -> Activity des handelnden Nutzers
  -> Commit

Profil / Album / Partnerliste
  -> Community-Read-Projektion
  -> bestehende S27-Privacy
  -> bestehende S20-Coverage
  -> bestehende S21-TopMatch-Optimierung
  -> read-only Darstellung / bestehender Tradeeinstieg
```

Die ausführliche Architektur, Datenflüsse, Berechtigungsmatrix, Read-/Write-
Pfade und Risiken stehen in
[`s29-friendships-community.md`](../s29-friendships-community.md).

## Zustandsmodell und Berechtigungen

`friendship_requests` erlaubt ausschließlich `pending`, `accepted`, `declined`
und `cancelled`. `friendships` enthält ausschließlich kanonische beidseitige
Verbindungen im Zustand `accepted`. Entfernen löscht die Freundschaft physisch.

- Nur der Empfänger kann annehmen oder ablehnen.
- Nur der Absender kann eine offene Anfrage zurückziehen.
- Beide Teilnehmer können eine Freundschaft entfernen.
- Kreuzanfragen werden atomar angenommen; beide offenen Requests wechseln auf
  `accepted`, genau eine Freundschaft entsteht und beide Nutzer erhalten
  `friend_accepted`.
- Eine gerichtete Blockierung verhindert neue Interaktionen in beiden
  Richtungen.
- Blockieren löscht die Freundschaft, setzt offene Friend-/manuelle-/Smart-
  Anfragen auf den bestehenden Status `cancelled` und lässt angenommene sowie
  laufende Trades vollständig bestehen.
- Entblocken stellt weder Freundschaft noch Anfragen wieder her.

## Datenmodell und Migration V0009

Neue Tabellen:

- `friendship_requests`,
- `friendships`,
- `blocks`,
- `user_activity`.

Kanonische Paar- und gerichtete Pending-Unique-Constraints schützen vor
Duplikaten. V0009 ist wiederholt ausführbar. Der Backout ist fail-closed, sobald
Community-/Activity-Daten oder S29-Notifications vorhanden sind; er löscht
keine fachlichen Daten automatisch.

Die Migration wurde ausschließlich auf temporären Kopien der kanonischen
S00-Fixture geprüft. Die lokale Entwicklungsdatenbank und die kanonische
Fixture wurden nicht migriert oder verändert.

## Notifications

S29 ergänzt exakt:

- `friend_request`: Ziel und `source_event_id` = Friendship-Request-ID,
- `friend_accepted`: Ziel und `source_event_id` = Friendship-ID.

Die bestehende transaktionale Deduplizierung bleibt unverändert. Eine
Kreuzannahme ersetzt die kurz zuvor erzeugte Request-Notification und erzeugt
stattdessen genau eine Annahme-Notification je Nutzer.

## Activity

Activity wird nur bei einer tatsächlich persistierten Fachmutation geschrieben.
Login, GET, fehlgeschlagene Aktion und Redirect ohne Mutation schreiben nichts.
Abgedeckt sind die zentralen Collection-, Trade-, Shipping-/Receipt-, Problem-,
Rating-, Privacy- und Community-Mutationspfade. Sichtbar ist der Status nur für
Freunde und ausschließlich als eine der vier freigegebenen Klassen.

## Tauschpotenzial

Das Profil zeigt nur die freigegebene Richtung „Wie gut kann dieser Nutzer mir
helfen?“ aus der persönlichen S20-Coverage. Der beste vorhandene S21-TopMatch
und seine ausführbaren Pakete werden ohne neue Kennzahl dargestellt. Album und
Profil verlinken in den bereits vorhandenen Smart-/TopMatch-Pfad. Blockierte
Paare werden zentral aus Coverage, TopMatch, Smart Trades, Partnerlisten und
direkter neuer Tradezusammenstellung ausgeschlossen.

## Neue Dateien

- `App/Database/migrations/0009_friendships_community.up.sql`
- `App/Database/migrations/0009_friendships_community.down.sql`
- `App/services/community.py`
- `tests/test_s29_friendships_community.py`
- `Dokumentation/Product Bible/roadmap/s29-friendships-community.md`
- `Dokumentation/Product Bible/roadmap/sprint-reports/S29-report.md`

## Geänderte Dateien

- `App/webapp.py`
- `App/services/album_privacy.py`
- `App/services/inventory_write.py`
- `App/services/smart_trade_requests.py`
- `App/services/trade_coverage.py`
- `App/services/trade_ratings.py`
- `App/services/trade_reservations.py`
- `App/services/typed_notifications.py`
- `tests/test_s18_2_problem_trade_finalization.py`
- `tests/test_s23_typed_notifications.py`
- `tests/test_s26_collector_profiles.py`
- `tests/test_s27_album_privacy_trade_pool.py`
- `tests/test_s28_trade_ratings.py`
- `Dokumentation/Product Bible/roadmap/README.md`

Die älteren Tests wurden ausschließlich von historisch absoluten
„neueste Migration“- beziehungsweise „global exakt sieben Typen“-Annahmen auf
ihren eigentlichen Sprintvertrag präzisiert. Ihre Fachlogik wurde nicht
gelockert.

## Testmatrix

| Bereich | Abdeckung |
|---|---|
| V0009 | Forward, Repeat, Constraints, leerer Backout, fail-closed Backout |
| Requests | senden, annehmen, ablehnen, zurückziehen, unberechtigter Zugriff |
| Kreuzanfrage | atomare Annahme, eine Freundschaft, zwei Notifications |
| Freundschaft | bilateral, entfernen, S27-Friends-Privacy sofort aktiv/inaktiv |
| Block | beide Richtungen, offene manuelle/Smart-Anfragen, laufender Trade bleibt |
| Suche | case-insensitive Prefix, alphabetisch, max. 20, Blockfilter, Freundmarker |
| Activity | vier Klassen, nur Freunde, GET/Login/Fehler ohne Write |
| Matching | S20-Coverage, S21-TopMatch, Smart-/manueller Pfad blockgefiltert |
| UI | Freundesbereich, Profilaktionen, Blockhinweis, Profil-/Album-Deep-Link |
| Regression | vollständige S01–S29-Suite zweimal |

## Testergebnisse

S29-spezifischer, tatsächlich ausführbarer Modulbefehl:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_s29_friendships_community -v
```

Ergebnis: **10 Tests, alle erfolgreich**.

Der in der Übergabe angegebene unquotierte Platzhalter
`python3 -m unittest tests.test_s29_* -v` wird von zsh bereits vor Python als
nicht vorhandener Dateiglob abgewiesen; `unittest` selbst expandiert auch die
quotierte Modul-Wildcard nicht. Deshalb wurde das konkrete Modul ausgeführt.

Vollständiges Gate, zweimal:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p "test_s*.py" -v
```

- Lauf 1: **445 Tests, alle erfolgreich**, 4,778 s.
- Lauf 2: **445 Tests, alle erfolgreich**, 4,900 s.

`git diff --check`: erfolgreich, keine Whitespace-Fehler.

## Release Readiness

- Temporäre S00-Kopie kontrolliert auf V0009 migriert: Versionen 1–9
  erfolgreich.
- `PRAGMA integrity_check`: `ok`.
- `PRAGMA foreign_key_check`: keine Befunde.
- SHA-256 lokale Entwicklungsdatenbank nach den Prüfungen:
  `4227cffc2047ccc95b3949cd31b3116a40ef1a384bc7e2b9889aeab6fc0bb4ab`.
- SHA-256 kanonische S00-Fixture:
  `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971`.
- Sämtliche S29-Tests sichern beide kanonischen Dateien während jedes
  isolierten Testfalls gegen Veränderung. Die lokale Datenbank blieb auf V0007
  und war zu keinem Zeitpunkt Ziel des V0009-Migrationsrunners.
- Temporäre Release-Datenbank wurde nach erfolgreicher Prüfung entfernt.

## Bekannte Grenzen und offene Punkte für S30

- Eine Migration der normalen lokalen Entwicklungsdatenbank auf V0009 ist ein
  gesonderter, kontrollierter Betriebs-/Abnahmeschritt und wurde nicht
  vorgezogen.
- Feed, Chat, Freundesaktivitätsfeed, Besucherlisten, regionale Suche,
  dauerhaftes Block-/Friendship-Audit und weitere Community-Features gehören
  nicht zu S29.
- Der vorhandene Gesamtkontext des Worktrees enthält weiterhin frühere,
  uncommittete Sprintstände; sie wurden nicht bereinigt oder umgeschrieben.

## Scope-Bestätigung

- Ausschließlich S29 wurde umgesetzt.
- S30 wurde nicht begonnen oder vorbereitet.
- Inventory-, Lifecycle-, Snapshot-, Coverage-, TopMatch-, Smart-Request-,
  Shipping-, Receipt-, Problem-, Rating- und Privacy-Fachregeln wurden nicht
  verändert; S29 ergänzt nur Community-Policy, erlaubte Integrationsguards und
  Activity-Hooks.
- Keine lokale oder produktive Datenbank wurde migriert.
- Kein Commit wurde erstellt.
- Kein Push wurde durchgeführt.
