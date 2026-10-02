# S06 – Globaler Header mit Avatar- und Glocken-Shell

Stand: 2026-07-31

Dieses Dokument ergänzt die S05-Navigationsmatrix um die in S06 aktivierte
Headerhierarchie. Die Development Roadmap V1 und die Product Bible bleiben die
fachlich verbindlichen Quellen.

## Headerhierarchie

Der wiederverwendbare `app_header` bildet auf eingeloggten Seiten genau diese
globalen Zugänge ab:

| Element | Ziel | Funktion in S06 |
| --- | --- | --- |
| Sammlr-Marke | `/` | bestehender Rückweg zu Home |
| Glocke | `/notifications` | Shell für vorhandene ungelesene Hinweise oder ehrlichen Leerzustand |
| Initialen-Avatar | `/profil` | Einstieg zum bestehenden eigenen Profil |

Home (`/`), Sammlung (`/sammlung`) und Tauschen (`/trades`) verwenden denselben
Headerpfad. Bestehende Unterseiten, die bereits `app_header` einsetzen, erhalten
dieselben globalen Zugänge, ohne dass Seitentitel, Fachinhalte oder bestehende
Zurückwege ersetzt werden.

Login und Registrierung zeigen weiterhin nur die Marke. Private Profil- und
Notificationzugänge werden dort nicht gerendert.

## Avatar-Shell

Es gibt unverändert kein Profilbildfeld und kein neues Datenmodell. Der Avatar
zeigt deshalb den ersten Buchstaben des vorhandenen Namens beziehungsweise
Benutzernamens. Fehlen beide Werte, wird neutral `S` dargestellt. Der Avatar
verlinkt ausschließlich auf das bestehende eigene Profil unter `/profil`.

## Glocken-Shell

Die Glocke besitzt kein Badge und berechnet keine Anzahl. `/notifications`
verwendet ausschließlich den bestehenden Adapter `unread_notifications()`:

- Sind ungelesene Einträge vorhanden, werden höchstens die fünf aktuellen
  Einträge des eingeloggten Nutzers angezeigt.
- Sind keine ungelesenen Einträge vorhanden, wird der ehrliche Leerzustand
  „Keine neuen Benachrichtigungen.“ angezeigt.
- Der reine Seitenaufruf ändert keinen Read-State und erzeugt keine Einträge.

Die Seite ist ausdrücklich keine Notification-Historie. Sie ergänzt weder Typen
noch Zielobjekte, Deep Links, Aufbewahrungsregeln, Pagination oder Badge-Logik.

## Mobile Grundfunktion

Die vorhandene Headerfläche bleibt ein gemeinsamer flexibler Container. Bis
520 Pixel werden Innenabstand, Logo-Breite und Zwischenraum reduziert; Glocke
und Avatar behalten jeweils eine 44 × 44 Pixel große Bedienfläche.

## Tests

Nur S06:

```sh
python3 -m unittest discover -s tests -p 'test_s06_*.py' -v
```

Vollständiges Gate:

```sh
python3 -m unittest discover -s tests -p 'test_s0*.py' -v
```

Geprüft werden Headerzugänge auf allen drei Hauptbereichen, Zielrouten,
Login-Schutz, Initialen-Fallback ohne Profilbilddaten, mobiler CSS-Smoke,
Notification-Leer-/Bestandszustand, Nutzerscoping und nebenwirkungsfreies Lesen.

## Bewusst nicht enthalten

- Notification-Badge oder Zähler,
- vollständige Notification-Historie oder neue Read-Funktionen,
- Notification-Typen, Deep Links, neue APIs oder Datenbanktabellen,
- Home-Aufgaben, Friend Feed oder Sammlr News,
- neue Tradefunktionen,
- finales Headerdesign oder Design Patch.
