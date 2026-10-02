# S37 – Beta-Polish: UX, Routing und Konsistenz

Stand: 2026-08-09

## Ziel und Scope

S37 härtet ausschließlich die Bedienung der vorhandenen Funktionen. Fachlogik,
Datenmodell, Services, Berechtigungen und bestehende Zustände bleiben
unverändert. Der Sprint vereinheitlicht Rückwege, Produktshells, Leer- und
Feedbackzustände sowie den Schutz vor versehentlichen Mehrfach-POSTs.

Die verbindliche Product-Owner-Klärung ersetzt die missverständliche
Navigationsformulierung des ursprünglichen Auftrags: Die mobile
Bottom-Navigation besteht ausschließlich aus `Sammlung`, `sammlr.` und
`Tauschen`. Profil und Notifications bleiben ausschließlich im globalen Header.
Es gibt keine fünfteilige Bottom-Navigation.

## Architektur und Datenfluss

```text
bestehende Flask-Route
  -> bestehende Fach-/Read-Services (unverändert)
  -> app_header(...) + kontextueller Rückweg
  -> bestehende Seiteninhalte
  -> bottom_nav(Sammlung | sammlr. | Tauschen)
  -> gemeinsame S30/S31/S37-Darstellungsregeln
```

POST-Datenfluss:

```text
vorhandenes POST-Formular
  -> Browser startet regulären Submit
  -> nächster Event-Loop: Formular aria-busy, Submit deaktiviert
  -> vorhandene Route, CSRF-Prüfung und Fachmutation unverändert
```

Das verzögerte Deaktivieren erhält Name und Wert des auslösenden Submit-Buttons
für die reguläre Formularauswertung. Es entsteht kein neuer Request, kein
Hintergrundjob und kein fachlicher Zustand.

## Routing-Vertrag

| Kontext | Rückweg |
| --- | --- |
| Album hinzufügen | Sammlung |
| Papierliste, Albumstatistik, Stickerdetail | aktuelles Album |
| Deal aus Home | Home |
| Deal aus Tradezentrale | Tradezentrale |
| Profilformulare und Datenexport | eigenes Profil |
| Problemweg | aktuelle Dealansicht |

Der sichere S07-Origin-Vertrag der Dealansicht bleibt unverändert. S37 fügt
keine allgemeine Return-URL-Mechanik hinzu.

## Produktshell und Navigation

- Haupt- und Workflowseiten verwenden den vorhandenen globalen Header.
- Glocke und Profil sind ausschließlich Headeraktionen.
- Alle authentifizierten Produktseiten behalten die dreiteilige mobile
  Bottom-Navigation.
- Der mittlere `sammlr.`-Spot bleibt visuell hervorgehoben und führt immer zu
  Home.
- Bestehende Kontextheader der Papierliste und Dealansicht bleiben erhalten,
  konkurrieren aber nicht mehr als zweiter Sticky Header.
- Desktop blendet die Bottom-Navigation weiterhin aus; 390 px, 430 px und Safe
  Area folgen den vorhandenen S31-Regeln.

## UX-Zustände

- Eine leere Sammlung erklärt den Zustand und bietet die bestehende Aktion
  `Album hinzufügen` an.
- Eine erfolglose Nutzersuche zeigt `Keine Suchergebnisse.`.
- Bereits vorhandene Empty States für Trades, Notifications, Freunde,
  Bewertungen und Stickerlisten bleiben erhalten.
- Redirect-Meldungen werden auch in Notification-Historie, Freundesliste und
  öffentlichem Profil sichtbar ausgegeben.
- Feedback verwendet die bestehenden Success-, Warning- und Error-Tokens.
- Vorhandene POST-Formulare erhalten nach dem Submit einen sichtbaren
  Ladezustand und Doppelklickschutz.

## Unveränderte Komponenten

- Inventory-, Availability- und Snapshot-Services
- Trade Lifecycle, Reservierung, Versand, Empfang und Probleme
- Coverage, TopMatch und Smart Requests
- Notification-Typen und Notification-Service
- Community-, Privacy-, Rating- und Account-Lifecycle-Logik
- Datenbankschema und Migrationen
- Desktopnavigation, Routen und Berechtigungen

## Accessibility und Responsive Contract

Die bestehenden S30/S31-Verträge bleiben maßgeblich: Fokusdarstellung,
44x44-Pixel-Touchziele, ESC-schließbare Dialoge, reduzierte Bewegung,
WCAG-AA-Farbtokens sowie die Referenzbreiten 390 px und 430 px. Der neue
Submit-Status nutzt `aria-busy`; bei reduzierter Bewegung rotiert der Indikator
nicht.

## Nicht enthalten

Keine neue Fachfunktion, keine Migration, keine Performanceoptimierung, keine
API-Erweiterung, keine neue Navigation, keine neue Produktentscheidung und
keine Arbeiten an S38.
