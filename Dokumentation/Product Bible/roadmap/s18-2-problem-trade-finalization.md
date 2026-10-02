# S18.2 – Problemtrade endgültig beenden und später optional lösen

Stand: 2026-08-08

## Ziel

Ein Empfänger darf einen Trade mit seinem dokumentierten offenen
Lieferproblem operativ beenden, ohne die offene Restmenge einzubuchen. Trifft
die Restlieferung später physisch ein, darf exakt derselbe Empfänger sie genau
einmal nachträglich auflösen. Sammlr dokumentiert nur den Verlauf und trifft
keine Schuldentscheidung.

## Zustandsmodell

```text
problem_open
├─ bestehender Pfad: Rest erhalten → resolved → completed
└─ neuer Pfad: Trade mit Problem beenden
   → closed_with_problem
   └─ optional: Rest später physisch erhalten
      → problem_resolved_after_close (endgültig)
```

Die Zustände liegen kanonisch in `trades.lifecycle_state`. Zeitpunkte und
Akteur werden append-only in `trade_events` gespeichert:

- `problem_trade_closed`
- `problem_resolved_after_close`

Das bestehende Lifecycle- und Eventgrundschema kann beide Werte ohne
Schemaänderung speichern. Eine neue Migration wäre daher reine Scheinarbeit
und wird nicht eingeführt. V0008 bleibt die aktuelle Schema-Version.

## Invarianten

- Nur der Empfänger, dem der offene Bericht gehört, darf schließen.
- Nur der Nutzer des zugehörigen `problem_trade_closed`-Events darf später
  nachträglich lösen.
- Schließen bucht keinen Sticker.
- Bereits initial korrekt erhaltene Mengen bleiben unverändert.
- Die offene Restmenge bleibt im Bericht dokumentiert, wird aber nicht länger
  als `incoming_transit` projiziert.
- Nachträgliches Lösen bucht ausschließlich
  `expected - initial_received - resolution_received`.
- Retry von Schließen oder Lösen ist idempotent.
- Nach `problem_resolved_after_close` sind Problemöffnung, Schließen und
  erneutes Lösen ausgeschlossen.
- Geschlossene Problemtrades sind bis auf die explizite nachträgliche
  Problemlösung read-only.
- `completed`, `closed_with_problem` und `problem_resolved_after_close` sind
  bewertbar; eine vorhandene Bewertung bleibt unverändert.
- Beide neuen Zustände zählen nicht als „Erfolgreiche Trades“.
- Keine Trophy und keine Notification wird durch Schließen oder nachträgliches
  Lösen erzeugt.

## Datenfluss

### Trade mit Problem beenden

```text
POST /trade/<request-id>/problem/close
→ BEGIN IMMEDIATE
→ Lifecycle, Teilnehmer und eigener offener Bericht prüfen
→ aktive Restreservierungen kontrolliert freigeben
→ Legacy-Request operativ auf completed setzen
→ lifecycle_state = closed_with_problem
→ completed_at setzen
→ problem_trade_closed Event anhängen
→ Commit
```

Inventory-Zeilen und Problempositionen werden dabei nicht verändert.

### Spätere echte Problemlösung

```text
POST /trade/<request-id>/problem/resolve
→ ausdrückliche physische Ankunft bestätigen
→ BEGIN IMMEDIATE
→ closed_with_problem + ursprünglichen Schließer prüfen
→ ausschließlich offene Restmenge via InventoryWriteService einbuchen
→ Positionen/Bericht resolved markieren
→ problem_resolved_after_close Event anhängen
→ lifecycle_state = problem_resolved_after_close
→ Commit
```

Der bestehende S17-Pfad `problem_open → resolve → completed` bleibt separat
und unverändert erhalten.

## Read-/Write-Pfade und Seiteneffekte

Schreibend sind ausschließlich die beiden expliziten POST-Aktionen. Alle
Deal-, Timeline-, Problemhistorien-, Profil- und Bewertungsansichten bleiben
read-only. Die zentrale Inventory-Leseprojektion beendet Transit anhand des
kanonischen Lifecycle-Zustands; es gibt keine zweite Transitberechnung in UI
oder JavaScript.

Nicht verändert werden Notificationtypen, Trophyregeln, Successful-Trade-
Definition, Ratingfinalität, Versand- und normaler Empfangspfad.

## UI-Vertrag

Bei einem eigenen offenen Problem erscheint „Trade mit Problem beenden“ mit
dem verbindlichen Sicherheitsdialog und einer Abbruchmöglichkeit. Danach zeigt
die Dealansicht „Trade mit Problem beendet“ und den dokumentierten offenen
Problemverlauf. Nur der ursprüngliche Empfänger sieht „Problem nachträglich
gelöst“. Nach erfolgreicher Auflösung bleibt der Deal endgültig read-only.

## Testvertrag

Geprüft werden alle vier Problemarten, Teilmengen, Inventory- und
Transitwerte, append-only Historie, Read-only-Verhalten, Berechtigungen,
Idempotenz, exakt einmalige Nachbuchung, endgültiger Zustand, Bewertbarkeit,
unveränderte Bewertung, keine Notifications/Trophies, unveränderte
Successful-Trade-Zahl und die vollständige S01–S28-Regression.
