# S28 – Qualifizierte Tradebewertungen und Vertrauen

Stand: 2026-08-08

## Ziel

S28 macht ausschließlich vollständig abgeschlossene Lifecycle-Trades mit
1–5 Sternen bewertbar. Jeder Beteiligte darf die jeweilige Gegenseite genau
einmal und unabhängig bewerten. Profile zeigen nur den sofort aktualisierten
Durchschnitt mit einer Nachkommastelle und die Anzahl empfangener Bewertungen.

## Verbindliche Invarianten

- Bewertbar sind ausschließlich die terminalen Lifecycle-Zustände
  `completed`, `closed_with_problem` und `problem_resolved_after_close`.
- Eine reine Legacy-Request-Zeile ohne Lifecycle-Trade ist nie bewertbar.
- Vor V0008 abgeschlossene Lifecycle-Trades bleiben dauerhaft bewertbar.
- Eine vollständig gelöste Problemhistorie ändert die Qualifikation nicht.
- Eine Bewertung auf `closed_with_problem` bleibt bei einer späteren echten
  Problemlösung unverändert und wird nicht erneut angeboten.
- Rater und bewerteter Nutzer müssen die beiden Teilnehmer desselben Trades
  sein und dürfen nicht identisch sein.
- Je Trade und Rater existiert exakt eine endgültige Bewertung.
- Eine gespeicherte Bewertung kann weder geändert noch gelöscht werden.
- Beide Seiten bewerten unabhängig; keine Seite wartet auf die andere.
- Sterne sind ausschließlich ganze Werte von 1 bis 5.
- Bewertungsaggregation und erfolgreiche Tradezahl sind getrennte Kennzahlen.
- S28 erzeugt keine Notification und verändert keinen Tradezustand.
- Einzelbewertungen werden weder auf eigenen noch auf fremden Profilen
  veröffentlicht.

## Architektur

### Migration V0008

Eine normalisierte Tabelle `trade_ratings` speichert:

- stabile Rating-ID,
- kanonische Lifecycle-Trade-ID,
- Rater-Nutzer-ID,
- bewertete Nutzer-ID,
- Sternezahl,
- Erstellungszeitpunkt.

Ein Unique Constraint auf `trade_id + rater_user_id` erzwingt die einmalige
Bewertung je Richtung auch bei Retry oder konkurrierenden Requests. Checks
sichern 1–5 Sterne und verhindern Selbstbewertungen auf Datenbankebene. Der
Lifecycle-Trade ist das einzige fachliche Ziel; Legacy-Request-IDs werden nicht
als Ratingziel gespeichert.

Zusätzliche Datenbank-Trigger weisen `UPDATE` und `DELETE` auf Bewertungen ab.
Die fachliche Endgültigkeit hängt damit nicht allein von fehlenden UI- oder
Servicepfaden ab.

Die Down-Migration ist fail-closed: Sobald mindestens eine Bewertung existiert,
wird V0008 nicht automatisch zurückgebaut. Ohne Bewertungsdaten kann die neue
Tabelle kontrolliert entfernt werden.

### `TradeRatingService`

Ein eigener Service kapselt ausschließlich:

- Qualifikation und Beteiligungsprüfung,
- Auflösung der bestehenden Deal-URL von Legacy-Request auf Lifecycle-Trade,
- transaktional einmaliges Speichern,
- Ratingstatus eines Nutzers für eine Dealansicht,
- read-only Durchschnitt und Anzahl für ein Profil.

Ergebnisobjekte und Aggregationen sind immutable. Stabile Ergebnis-Codes
unterscheiden gespeichert, bereits bewertet, nicht qualifiziert,
unberechtigt und ungültige Sterne.

### Vorbereitung strukturierter Gründe

S28 führt keine Gründe, Kategorien, Spalten, UI oder Bewertungslogik ein. Die
stabile normalisierte Rating-ID ist ausschließlich die technische
Erweiterungsnaht, an die ein später bewusst spezifiziertes Reason-Modell
referenziell angebunden werden kann. Dadurch muss die finale Sternebewertung
später nicht umgedeutet oder dupliziert werden.

## Datenfluss

### Bewertungsanzeige im abgeschlossenen Deal

```text
GET /trades/<legacy-request-id>
→ bestehende Beteiligungsprüfung
→ TradeRatingService löst genau den Lifecycle-Trade auf
→ kein terminaler Lifecycle-Zustand: keine Bewertungsaktion
→ terminal + noch nicht bewertet: 1–5-Sterne-Formular
→ terminal + bereits bewertet: finaler Hinweis und eigener Timeline-Eintrag
```

### Bewertung speichern

```text
POST /trades/<legacy-request-id>/rating
→ Sterne strikt validieren
→ BEGIN IMMEDIATE
→ Lifecycle-Trade completed und Beteiligung erneut prüfen
→ bewertete Gegenseite aus Tradeparticipants ableiten
→ INSERT unter Unique Constraint
→ Commit
→ zurück zur bestehenden abgeschlossenen Dealansicht
```

Es gibt keinen Update- und keinen Delete-Pfad.

### Profilaggregation

```text
GET /profil oder /profil/<username>
→ bestehender CollectorProfileService
→ TradeRatingService.summary_for_user(profile_user_id)
→ COUNT + Durchschnitt ausschließlich empfangener Bewertungen
→ 0: „Noch keine Bewertungen“
→ sonst: ★ Durchschnitt mit einer Nachkommastelle + Bewertungsanzahl
```

Das Profil rendert keine Rating-Zeile, Rater-ID, Trade-ID, Zeit oder Gründe.

## Betroffene Komponenten

- V0008 Up-/Down-Migration,
- neuer TradeRatingService und DTOs,
- abgeschlossene Dealansicht plus genau eine POST-Route,
- S26 CollectorProfileDTO und gemeinsame eigene/fremde Profilansicht,
- minimale S28-Darstellung,
- S28-Tests und Roadmap-Dokumentation.

## Unveränderte Komponenten

- Inventory Read/Write, Availability, Guard und Snapshot,
- Coverage, TopMatch und Smart Requests,
- Trade Lifecycle, Reservierung, Versand, Empfang und Problembehandlung,
- bestehende Abschluss- und erfolgreiche-Trade-Zählung,
- Tradearchiv,
- Notification-Typen, Deduplizierung, Historie und Badge,
- Operational Home,
- Albumprivacy und Tradepool,
- Freunde, Blockierung, Aktivitätsstatus und S29.

## Read-/Write-Pfade und Seiteneffekte

Read-only:

- Qualifikationsstatus der Dealansicht,
- Profilaggregation,
- erneutes Anzeigen einer bereits gespeicherten Bewertung.

Schreibend:

- V0008-Migration,
- genau ein `INSERT` je Rater und Lifecycle-Trade über den Bewertungs-POST.

Bewusst ausgeschlossen:

- Rating-Update oder -Delete,
- Notification,
- Trade-/Lifecycle-Event,
- Inventory- oder Reservation-Mutation,
- Gründe oder Freitext,
- Ranking und Smart-Match-Gewichtung.

## Risiken und Gegenmaßnahmen

- **Doppelbewertung/Retry:** Unique Constraint plus unmittelbare Transaktion.
- **Fremd- oder Selbstbewertung:** Teilnehmer werden serverseitig aus dem
  Lifecycle-Trade abgeleitet; der Client übergibt keinen Zielnutzer.
- **Zu frühe Bewertung:** ausschließlich Lifecycle-Zustand `completed`.
- **Legacy-Verwechslung:** Legacy-ID dient nur der bestehenden Route; gespeichert
  wird allein die Lifecycle-Trade-ID.
- **Öffentliche Detaillecks:** Profile erhalten nur Count und Durchschnitt.
- **Datenverlust beim Backout:** Down-Migration schlägt bei vorhandenen Ratings
  geschlossen fehl.

## Testvertrag

Getestet werden V0008 Up/No-op/Down/fail-closed, abgeschlossene und offene
Lifecycle-Trades, reine Legacy-Abschlüsse, abgeschlossene Problemfälle,
Beteiligung, Selbst-/Fremdschutz, 1–5-Grenzen, Retry, Parallelität,
Unveränderlichkeit, unabhängige Richtungen, sofortige Aggregation, Rundung,
eigene und fremde Profile, fehlende Bewertungen, fehlende Einzelrating-Leaks,
Notificationfreiheit sowie die vollständige S01–S28-Regression.
