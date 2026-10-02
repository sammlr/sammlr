# Sammlr Closed Beta Execution Roadmap

Status dieses Dokuments: verbindliche Execution-Schiene bis zur Closed Beta

Aktueller Stand: R1, R2, R3 und R4 sind `ACCEPTED / LOCKED`

**NEXT PACKAGE: R5 – REPRODUCIBLE RELEASE CANDIDATE**

Dieses Dokument ist eine ausführbare Arbeitsroadmap, keine allgemeine Product
Bible. Ein kurzer Folgeauftrag wie „Führe R3 gemäß
`CLOSED_BETA_EXECUTION_ROADMAP.md` aus“ autorisiert genau das bezeichnete Paket
und keinen späteren Roadmap-Schritt.

## 1. Verbindliches Arbeitsmodell

Sammlr wird bis zur Closed Beta paketweise abgeschlossen.

1. Pro Codex-Auftrag wird genau ein Roadmap-Paket bearbeitet.
2. Das nächste Paket wird niemals automatisch begonnen.
3. Nach Implementierung, Tests und Abschlussbericht gilt immer `STOP`.
4. Die finale manuelle Abnahme führt der Product Owner durch.
5. Ein Paket darf erst nach expliziter PO-Abnahme auf `ACCEPTED / LOCKED`
   gesetzt werden.
6. `ACCEPTED / LOCKED`-Flächen dürfen in späteren Paketen nicht beiläufig
   verändert werden.
7. Scope-fremde Auffälligkeiten werden dokumentiert und nicht spontan
   repariert.
8. Vor Closed Beta wird keine Feature-Erweiterung umgesetzt, sofern sie nicht
   Teil eines definierten Roadmap-Pakets ist.
9. Bei kleinen Implementierungsdetails ist die sicherste bestehende
   Produktinterpretation zu verwenden und innerhalb des Paket-Scope
   weiterzuarbeiten.
10. Ein vorzeitiger `STOP` ist nur bei einem echten Blocker zulässig:
    widersprüchlicher Produktvertrag, destruktive DB-Operation,
    Privacy-/Security-Risiko, irreversible Entscheidung oder Änderung zentraler
    Sammlr-Semantik.
11. Vor expliziter PO-Abnahme erfolgen weder Commit noch Push.

Statuswechsel sind PO-gesteuert. Die Implementierung eines Pakets allein ändert
seinen Status nicht. Nach einem Paketbericht wartet Codex auf die Abnahme oder
einen ausdrücklich beauftragten Korrekturpass.

## 2. Roadmap-Status und Ausführungsreihenfolge

| Reihenfolge | Paket | Status |
| --- | --- | --- |
| R1 | Stickerwall Product Island | `ACCEPTED / LOCKED` |
| R2 | Smart Trade Journey | `ACCEPTED / LOCKED` |
| R3 | Two-User Golden Path | `ACCEPTED / LOCKED` |
| R4 | V20 Performance Gate | `ACCEPTED / LOCKED` |
| R5 | Reproducible Release Candidate | `NEXT` |
| R6 | Operations + Legal | `PENDING` |
| R7 | Release Polish | `PENDING` |
| Gate | Closed Beta | gesperrt bis alle Pakete akzeptiert sind |

**R4 ist durch den Product Owner abgenommen. Autorisiert ist ausschließlich
R5 Phase A (Release Inventory + Plan). Phase B benötigt einen Folgeauftrag.**

## 3. R1 – Stickerwall Product Island

**Status: `ACCEPTED / LOCKED`**

R1 ist abgeschlossen. Die Fläche darf nur auf ausdrücklichen PO-Auftrag oder
wegen eines späteren echten Release-Blockers minimal wieder geöffnet werden.

### Abgenommener Vertrag

- Owner und Public verwenden die kanonische Stickerwall-Darstellung.
- Public ist read-only; dort existieren keine Editiercontrols.
- Kapitel-/Teamstruktur sowie Suche und Filter sind kanonisch geteilt.
- Ohne expliziten gespeicherten Collapse-State sind alle Kapitel offen.
- Ein expliziter Collapse-State bleibt erhalten.
- Sticker-Codes erscheinen als kleines Prefix plus dominanten Identifier.
- Numerische Identifier verwenden die bestehenden Retro-Digits.
- Text- und Slash-Identifier werden generisch passend skaliert.
- Die reale Duplicate-Quantity bleibt fachlich vollständig erhalten.
- Der Duplicate-Stack zeigt höchstens fünf physische Lagen, wächst kompakt nach
  oben-links und legt die neueste/frontale Lage visuell nach oben.
- Das kreisförmige sanftlila Badge zeigt die reale Quantity als reine Zahl.
- Pro Kapitel existiert genau eine solide, zur Kapitelgeometrie bündige
  Fortschrittslinie. Es gibt keine dashed/dotted Lines.
- Owner-Inventarsteuerung `+`/`-` und Details bleiben erhalten.
- Auf den akzeptierten mobilen Flächen entsteht kein horizontaler Overflow.

Zusätzlich akzeptiert:

- Auf dem eigenen Profil zeigt der App-Header Glocke und Zahnrad.
- Das Zahnrad führt nach `/account`.
- Im Collector Header existiert kein zusätzliches Zahnrad.
- Fremdprofile besitzen kein Owner-Zahnrad.

Kleiner, nicht blockierender Backlog: Die Text-Identifier-/Retro-Typografie kann
bei einzelnen Buchstaben wie `S` oder `P` später harmonisiert werden. Das ist
kein R1-Blocker und darf nur in R7 erneut geprüft werden, falls es dann noch
sichtbar stört.

## 4. R2 – Smart Trade Journey

**Status: `ACCEPTED / LOCKED`**

### Ziel und primäre Journey

Der sichtbare Trade-Einstieg vom Album bis zur bestehenden Trade-Welt wird zu
einem kohärenten Sammlr-Produktfluss:

`Album → Tradehub / Tauschpartner → SmartMatch → manuelle Tauschanfrage → /trades → Trade Detail`

R2 ist primär ein UI-/Presentation-Convergence-Paket. Vor jeder Implementierung
muss Codex den realen aktuellen Zustand der vollständigen Journey im Repository
und im Browser nachvollziehen. Ziel ist die Konvergenz auf die bereits
akzeptierte Sammlr-Sprache, keine pauschale Design-Neuerfindung.

### Fachlich geschützt

- Inventory-Semantik
- Availability, Reservations und Blocks
- Privacy und Owner-/Public-/Partnerberechtigungen
- Trade Lifecycle und bestehende Trade-Services
- ungleiche Trades bleiben erlaubt
- bestehende Mengen- und Richtungslogik
- Notification-Semantik
- das akzeptierte `/trades`
- das akzeptierte Trade Detail

Stickerliste, Stickerwall und Profile dürfen ohne zwingenden, nachgewiesenen
Grund nicht verändert werden.

### Definition of Done

- Der Album-Tradehub wirkt nicht wie eine Legacy-Oberfläche.
- Die SmartMatch-Partnerliste passt visuell und semantisch zur aktuellen App.
- Die manuelle Tauschanfrage gehört erkennbar zum selben Flow.
- Der Übergang zu `/trades` und Trade Detail ist verständlich.
- Es entsteht keine fachliche Trade-Regression.
- Owner-/Public-/Partnerberechtigungen bleiben korrekt.
- Bei 390 px entsteht kein horizontaler Overflow.
- Es gibt keine dashed/dotted Lines.
- Geschützte Produktinseln bleiben unverändert.

R2 ist durch den Product Owner abgenommen und gesperrt. Änderungen daran
erfordern einen neuen ausdrücklichen Auftrag.

## 5. R3 – Two-User Golden Path

**Status: `ACCEPTED / LOCKED`**

### Ziel

Ein verbindlicher Closed-Beta-End-to-End-Golden-Path mit zwei Nutzern wird
geprüft und, soweit sinnvoll, automatisiert abgesichert:

`Registrieren → Album starten → Bestand pflegen → Missing/Duplicates → Partner finden → Tauschanfrage → Annahme → Versand/Trade-Fortschritt → Empfang/Abschluss → automatische Bestandsanpassung → Notifications → Fremdprofil → Fremd-Stickerwall`

### Verpflichtende Gegenfälle

- Privacy und Blocks
- Direkt-URLs sowie Refresh/Reload
- unerlaubte Mutationen
- Public read-only und Owner-only Controls
- Reservations/Availability während aktiver Trades

R3 implementiert kein neues Feature und erfindet das Produkt nicht neu. Wenn
Browserautomation im vorhandenen Stack sinnvoll und verhältnismäßig ist, darf
R3 ein reproduzierbares Browsergate etablieren.

## 6. R4 – V20 Performance Gate

**Status: `ACCEPTED / LOCKED`**

### Ausgangslage und Ziel

Der vorhandene Performance Runner basiert noch auf V18, während die Runtime V20
verwendet. Deshalb existiert derzeit kein gültiges V20 Performance Gate.

R4 muss:

- den Runner auf die reale V20-Struktur bringen,
- einen reproduzierbaren Testzustand verwenden,
- zentrale Closed-Beta-Routen messen,
- relevante Query-Pläne prüfen,
- ausschließlich nachgewiesene Bottlenecks optimieren und
- eine neue reproduzierbare Performance-Baseline dokumentieren.

Zu untersuchende SIA-Hinweise sind relevante User-/Time-Zugriffe auf
`trade_requests` und `notifications`, mögliche Scan-/Sort-Pläne sowie – nur bei
einem realistischen Parallelitäts-Smoke – SQLite `busy_timeout`/WAL-Verhalten.
Indizes oder andere DB-Änderungen werden nicht auf Verdacht angelegt. Eine
Migration ist nur nach Messung, mit separater Begründung und innerhalb des
autorisierten Pakets zulässig. Performance-Voodoo ist ausgeschlossen.

## 7. R5 – Reproducible Release Candidate

**Status: `NEXT`**

### Ausgangslage

Der derzeitige Worktree ist ein Release-Blocker: Der Audit fand ungefähr 252
Worktree-Einträge, davon ungefähr 234 untracked. Relevante Runtime-, Service-,
Template- und Migrationsdateien sind nicht vollständig im aktuellen Commit;
`HEAD` repräsentiert den laufenden Produktstand nicht zuverlässig und
`requirements.txt` ist nicht ausreichend reproduzierbar gepinnt.

### Ziel und Scope

Ein neuer Rechner muss aus Repository und dokumentierter Konfiguration denselben
Sammlr-Stand reproduzieren können. Dazu gehören:

- den Worktree vollständig klassifizieren,
- Produktdateien korrekt versionieren,
- temporäre und irrelevante Artefakte ausschließen,
- Dependencies reproduzierbar pinnen,
- einen Clean Checkout testen,
- DB/Migration vom leeren Zustand bis V20 testen,
- Appstart und vollständige Testsuite prüfen,
- Golden-Path-Smoke ausführen,
- den Release Candidate eindeutig markieren und dokumentieren sowie
- Restore-/Rollback-Fähigkeit mit R6 abstimmen.

Eine blinde Massenaufnahme aller untracked Dateien ist verboten. Jede relevante
Dateikategorie muss zuerst verstanden werden.

## 8. R6 – Operations + Legal

**Status: `PENDING`**

### Ziel

Sammlr wird Closed-Beta-betriebsfähig, nicht nur lokal korrekt.

Technischer Scope:

- Backup-Vertrag und getesteter Restore
- Runbook auf aktuellem Schema
- dokumentierter Produktionsstart
- Healthcheck
- grundlegender Fehler-/Alert-Weg
- dokumentierte relevante Betriebsparameter

Legal-/Operator-Scope:

- Impressum, Datenschutztext und Betreiberangaben finalisieren
- Platzhalter entfernen

Codex darf technische Vollständigkeit und offensichtliche Platzhalter prüfen,
aber keine juristische Rechtsberatung oder rechtliche Freigabe simulieren. Die
finale rechtliche Verantwortung und Freigabe liegen außerhalb des Codes.

## 9. R7 – Release Polish

**Status: `PENDING`**

R7 schließt ausschließlich kleine, klar begrenzte SIA-Restpunkte vor Closed
Beta. Zulässige Kandidaten sind:

- gemeinsamer Sammlr Error Shell für 400/404/405/409,
- Production-Gating für `/dev/retro-ziffern`,
- enger begrenzte/sicherere Master-Asset-Route,
- verbleibende sichtbare dashed/dotted Lines auf solid umstellen,
- wenige wirklich störende Empty States und
- der kleine R1-Backlog zur typografischen Harmonisierung von
  Text-Identifier-/Retro-Buchstaben, falls weiterhin sichtbar störend,
- SmartMatch-Text „Dieses optimierte Paket ist nicht editierbar.“ später auf
  natürlichere Sammlr-Sprache prüfen; jetzt keine Runtime-Änderung und
- „0 von 3 Smart-Anfragen global offen“ später auf verständlichere
  Formulierung prüfen; jetzt keine Runtime-Änderung.

R7 ist kein allgemeiner Design-Sprint. Verboten sind globale CSS-Bereinigung,
ein Großrefactor von `webapp.py`, ein neues Designsystem, Feature-Erweiterung,
Trophy-, Profil- oder Stickerlisten-Rework sowie ein Trade-Rework nach
akzeptiertem R2. Es werden nur Release-Krümel bearbeitet.

## 10. Global locked / protected

Folgende akzeptierte Produktinseln sind grundsätzlich geschützt:

- Stickerliste
- CEOKlaue
- Glassboard Review
- Profile V1
- 70er Profile Sticker Front
- Sammlung
- `/trades`
- Trade Detail
- Stickerwall nach R1

Die Stickerliste ist insbesondere als modulare Protected Surface zu behandeln:

- `App/sticker_list.py`
- `App/templates/sticker_list.html`
- `App/static/sticker_list.css`
- `App/static/sticker_list.js`

Diese Dateien und Flächen dürfen nicht beiläufig verändert werden.

Globale Designregel: Alle intentionalen UI-Linien und Borders sind
solid/continuous. `dashed` und `dotted` sind unzulässig.

## 11. Explizit bis nach Closed Beta zurückgestellt

Vor Closed Beta werden nicht implementiert:

- 90er Profile Sticker
- Modern Profile Sticker
- Sticker-Rückseiten
- Portrait-Segmentation
- eigene Albumcover-Uploads
- Trophy-Rework
- Friends-Ausbau
- Share Cards / QR-Marketing
- Scanner
- Premium
- Store
- Sammlr Insights
- neue Stats-Dashboards
- Mehrfachkopien eines Albums
- sonstige neue Feature-Breite

Diese Punkte bleiben Backlog und sind keine verlorenen Ideen.

## 12. Bekannte Test-Baseline

Stand nach R1: **850 Tests, 847 bestanden.**

Die drei bekannten scope-fremden Bestandsfehler sind:

1. Die DB-Masterhash-Erwartung ist gegenüber dem bewusst veränderten lokalen
   DB-Zustand stale.
2. Der Notification-Pagination-Test besitzt eine bekannte Bestandsursache durch
   30-Tage-Retention und Testtimestamps.
3. Das v0007-/S38-Migrationsfixture beziehungsweise dessen
   Schema-Version-Annahme ist veraltet; die Runtime befindet sich auf V20.

Diese Fehler werden innerhalb eines fremden Roadmap-Pakets nicht beiläufig
repariert. Betrifft ein Paket einen dieser Bereiche ausdrücklich, ist zuerst zu
klären, ob der Baseline-Vertrag selbst aktualisiert werden soll.

## 13. Standard-Acceptance-Vertrag für jedes Paket

Soweit für den jeweiligen Scope relevant, sind auszuführen und zu berichten:

- fokussierte Tests,
- betroffene Regressionstests,
- vollständige Testsuite,
- Safari-Smoke bei 390 px für sichtbare Produktflächen,
- Desktop-Smoke,
- Prüfung auf horizontalen Overflow,
- Privacy-/Block-/Owner-/Public-Prüfungen bei betroffenen Flächen,
- `integrity_check`,
- `foreign_key_check`,
- DB-SHA-256 unmittelbar vor und nach dem Paket sowie
- `git diff --check`.

DB-Hash-Abweichungen werden logisch untersucht. Eine binäre DB-Rekonstruktion
nur zur künstlichen Wiederherstellung eines Hashes ist verboten. Ohne
ausdrückliche Paketnotwendigkeit gibt es keine Migration. Vor einer destruktiven
DB-Änderung gilt `STOP` zur PO-Entscheidung.

## 14. Verbindlicher Abschlussbericht

Jedes Paket endet mit einem kompakten Bericht über:

- implementierten Scope,
- geänderte Runtime-Dateien,
- fokussierte Tests,
- vollständige Testsuite,
- Safari-/Desktop-Smoke,
- DB-Hash vorher/nachher,
- `integrity_check`,
- `foreign_key_check`,
- `git diff --check`,
- Migration ja/nein,
- Commit nein,
- Push nein und
- bekannte verbleibende scope-fremde Fehler.

Danach: **STOP – wartet auf Product-Owner-Abnahme.**

## 15. Closed-Beta-Gate

Closed Beta darf erst als erreicht markiert werden, wenn R1, R2, R3, R4, R5,
R6 und R7 jeweils explizit `ACCEPTED / LOCKED` sind und kein neu entdeckter
`RED` Release-Blocker offen ist.

Nach Erreichen dieses Gates beginnt vor dem ersten echten Beta-Einsatz keine
weitere Feature-Runde.

## 16. Aktuelle Ausführungsanweisung

1. R1, R2, R3 und R4 bleiben `ACCEPTED / LOCKED`.
2. **Das nächste Paket ist R5 – Reproducible Release Candidate.**
3. Autorisiert ist ausschließlich Phase A: Read-only-Inventur und Phase-B-Plan.
4. Änderungen sind auf dieses Statusupdate und `docs/R5_RELEASE_INVENTORY.md` begrenzt.
5. Nach Phase A gilt STOP. R5 bleibt `NEXT`; Phase B benötigt einen ausdrücklichen Folgeauftrag.
6. Kein Staging, Commit, Push oder Deploy. R6 und R7 bleiben `PENDING`.
