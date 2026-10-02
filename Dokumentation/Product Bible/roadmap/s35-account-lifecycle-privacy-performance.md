# S35 – Datenschutz, Account Lifecycle und Performance-Baseline

## Ziel und verbindlicher Scope

S35 führt einen datensparsamen Account Lifecycle mit exakt `active`,
`deactivated` und `anonymized` ein. Freiwillige Deaktivierung ist reversibel,
endgültige Anonymisierung nicht. Historische Trades, ihre Positionen, Timeline,
Versand-/Empfangsdaten, Problemhistorie und Bewertungen bleiben erhalten. Eine
reproduzierbare Gunicorn-/SQLite-Baseline misst die freigegebenen Kernseiten.

Nicht Bestandteil sind Admin-Sperren, S29-Blockierung, Download-/ZIP-Export,
zusätzliche Rechtstexte, automatische Performanceoptimierung oder S36.

## Architektur und Datenfluss

```text
Login -> AuthSecurityService -> active -> Session
                             -> deactivated -> Reaktivierungsnachweis
                                -> explizites POST -> active -> Session
                             -> anonymized/ungültig -> keine Anmeldung

Profil-POST -> AccountLifecycleService
  Deaktivieren -> Passwort -> state=deactivated + auth_version++ -> Session aus
  Anonymisieren -> Passwort + Checkbox -> Trade-Gate
    -> laufend: verweigern
    -> ausschließlich terminal: abhängige persönliche Daten löschen
       + Identität intern entkoppeln + state=anonymized + auth_version++

Reads für Profil/Suche/Matching/neue Interaktionen -> ausschließlich active
Historische Trade-Reads -> Nutzerreferenz bleibt -> Anzeigename Gelöschter Nutzer
```

Der neue Service ist Eigentümer aller S35-Schreibregeln. Inventory,
Availability, Trade Lifecycle, Community, Notifications, Ratings, Security und
Deployment bleiben kanonische Quellen; S35 erzeugt keine zweite Fachlogik.

## Zustandsvertrag und Berechtigungen

| Zustand | Login | Profil/Suche | Matching/neue Interaktion | Laufender Trade | Reaktivierung |
| --- | --- | --- | --- | --- | --- |
| `active` | ja | gemäß Privacy | ja | normal | entfällt |
| `deactivated` | nein | nein | nein | bleibt unverändert gespeichert | explizit nach Passwortprüfung |
| `anonymized` | nein | dauerhaft nein | dauerhaft nein | nur terminale Historie zulässig | niemals |

Eine Deaktivierung ist auch bei laufenden Trades zulässig. Sie erhöht
`auth_version`; dadurch sind alle bestehenden Sessions sofort ungültig. Ein
korrekter Login eines deaktivierten Kontos erzeugt noch keine Session, sondern
nur einen signierten, kurzlebigen Reaktivierungsnachweis. Erst das explizite
CSRF-geschützte Reaktivierungs-POST aktiviert das Konto und erstellt eine neue
Session.

## Anonymisierung und Trade-Gate

Die Aktion verlangt aktuelles Passwort und die verpflichtende Checkbox:

> Ich verstehe, dass mein Sammlr-Konto dauerhaft anonymisiert wird und dieser
> Vorgang nicht rückgängig gemacht werden kann.

`open` und `accepted` beziehungsweise deren laufende Lifecycle-Projektionen
(`reserved`, `shipping`, `receiving`, `problem_open`) blockieren die Aktion.
Terminale Requests `completed`, `failed`, `declined`, `cancelled`, `expired`
und `obsolete` bleiben erhalten. `closed_with_problem` ist über den bereits
terminal abgeschlossenen Request ebenfalls Historie. Bei einer Blockade lautet
die Rückmeldung exakt:

> Dein Konto besitzt noch laufende Tauschaktionen. Bitte schließe diese zuerst
> vollständig ab.

Die Nutzerzeile bleibt als interne referenzielle Hülle bestehen. Ihr früherer
Username wird durch einen nicht öffentlich dargestellten, eindeutigen
Tombstone-Wert ersetzt, damit der Username wieder vergeben werden kann. Name,
Passwortbezug und Favorit werden entfernt beziehungsweise unbrauchbar gemacht.
Jede Produktoberfläche zeigt für diese Identität ausschließlich „Gelöschter
Nutzer“; der interne Schlüssel ist nie öffentliches Pseudonym.

## Datenschutz- und Retention-Matrix

| Datenkategorie | active/deactivated | anonymized | Begründung |
| --- | --- | --- | --- |
| Nutzerzeile | vollständig | referenzielle Hülle, State und interner Schlüssel | historische Referenzen schützen |
| Username/Klarname/Profil | erhalten | sofort entfernt; Username freigegeben | Datensparsamkeit |
| Passwort/Sessions | erhalten | Passwort unbrauchbar; Sessions invalidiert | kein erneuter Zugriff |
| Sammlung, Albumzuordnung, Sticker | erhalten | sofort gelöscht | kein historischer Nachweiszweck |
| Trophäen | erhalten | sofort gelöscht | profilbezogen |
| Freundschaften/-anfragen/Blocks | erhalten | sofort beidseitig gelöscht | Communitybezug entfernen |
| Aktivitätsstatus | erhalten | sofort gelöscht | Profilbezug entfernen |
| empfangene Notifications | erhalten | sofort gelöscht | keine Archivierung |
| Login-Throttle | erhalten | alle Schlüssel des früheren Usernames gelöscht | Authdaten minimieren |
| Trade Requests/Lifecycle/Positionen/Events | erhalten | vollständig erhalten | technische und fachliche Historie |
| Versand, Empfang, Probleme | erhalten | vollständig erhalten | Tradehistorie/Nachweis |
| abgegebene Ratings | endgültig erhalten | erhalten; Aggregat des bewerteten Partners bleibt korrekt | S28-Finalität |
| empfangene Ratings | erhalten | historisch erhalten, aber kein gelöschtes Profil/Aggregat sichtbar | Tradehistorie |
| S34-Backups | S34-Vertrag | unverändert nach S34-Retention | kein S35-Backupeingriff |

## Export-Grundlage und Dateninventar

`AccountDataInventoryService` stellt ausschließlich immutable Metadaten und
Zählwerte der vom Account betroffenen Datenkategorien bereit. Der Service ist
read-only und erzeugt weder Datei, Download, ZIP noch UI. Er ist die technische
Grundlage für einen später separat freizugebenden Export.

## Migration V0012

V0012 ergänzt ausschließlich
`users.account_state TEXT NOT NULL DEFAULT 'active'` mit den drei erlaubten
Werten und einen Index für aktive Projektionen. Bestehende Nutzer werden
`active`. Der Backout ist fail-closed, sobald ein nicht aktiver Account
existiert; er löscht oder transformiert keine Accountdaten.

## Performance-Baseline

Die reproduzierbare Baseline verwendet ausschließlich temporäre Daten:

- 100 Nutzer,
- 10 Alben,
- ungefähr 100.000 Stickerpositionen,
- 2.000 Trades,
- 5.000 Notifications,
- 1.000 Freundschaften,
- Gunicorn und SQLite in der S34-Produktionskonfiguration,
- 20 gleichzeitige Requests,
- Login, Home, Sammlung, Album, Stickerwall, Suche, Tradebörse, Dealansicht,
  Notifications und Profil.

Bewertet wird die P95-Antwortzeit: unter 500 ms bestanden, 500–1000 ms
dokumentationspflichtig, über 1000 ms Release-Blocker. Die Fehlerquote muss
null Prozent betragen. Die Baseline misst und berichtet; sie löst keine
automatische Optimierung aus.

## Bewusst unverändert

- Inventory- und Availability-Verträge,
- Trade Lifecycle, Reservation, Shipping, Receipt und Problems,
- Ratingfinalität und Tradehistorie,
- Notificationtypen und Retention aktiver/deaktivierter Konten,
- S29-Nutzerblockierung,
- S34-Deployment, Backups, Logs und Recovery,
- lokale Entwicklungsdatenbank und S00-Fixture.
