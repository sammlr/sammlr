# S37 – UX- und Routing-Smokebericht

Stand: 2026-08-09

## Automatisierter Smoke

Der Test `tests.test_s37_beta_polish` öffnet auf einer temporären Kopie der
S00-Fixture unter anderem Home, Sammlung, Album, Papierliste, Albumstatistik,
Stickerdetail, Tradezentrale, Dealansicht, Notifications, Profil,
Freundesliste, Profilformulare und Datenexport.

Geprüft werden:

- HTTP 200 für die vorhandenen Produktseiten,
- globaler Header mit Glocke und Profil,
- exakt drei Bottom-Navigationsziele in der Reihenfolge Sammlung, `sammlr.`,
  Tauschen,
- kein Profil- oder Notificationziel in der Bottom-Navigation,
- fachlich lokaler Rückweg aus Album-, Trade- und Profilkontexten,
- leere Sammlung mit bestehender Aktion,
- leere Nutzersuche,
- sichtbares Feedback nach Redirects,
- POST-Ladezustand und Doppelklickschutz,
- unveränderter Stickerbestand bei den geprüften GET-Routen,
- 390-/430-Pixel-, Safe-Area-, Fokus- und Touchziel-Vertrag.

Ergebnis: 6 von 6 S37-Smoke-/Regressionstests bestanden. Dieselbe Abdeckung
war Bestandteil beider erfolgreichen Gesamtgates.

## Reproduzierbarer manueller Smoke

1. Als aktiver Nutzer auf 390 px und anschließend auf 430 px anmelden.
2. Home, Sammlung und Tauschen nacheinander über die Bottom-Navigation öffnen.
   Erwartung: exakt drei Ziele; `sammlr.` liegt mittig; Profil und Glocke sind
   ausschließlich oben rechts.
3. Aus einem Album Papierliste, Statistik und einen Sticker öffnen.
   Erwartung: Header und Navigation bleiben konsistent; `Zurück` führt zum
   aktuellen Album.
4. Aus Home und aus der Tradezentrale denselben Deal öffnen.
   Erwartung: Der bestehende kontextuelle Rückweg führt jeweils zum Ursprung.
5. Notifications, Profil, Freunde und Datenexport öffnen.
   Erwartung: persönliche Zugänge bleiben im Header; der fachliche Rückweg führt
   zum Profil bzw. zur passenden Liste.
6. In einer isolierten Testdatenbank alle eigenen Alben entfernen und nach
   einem nicht existierenden Nutzernamen suchen.
   Erwartung: verständlicher Leerzustand; die Sammlung bietet `Album hinzufügen`
   an.
7. Ein vorhandenes POST-Formular absenden.
   Erwartung: Submit wird während des Requests als beschäftigt markiert und
   kann nicht doppelt ausgelöst werden; das fachliche Ergebnis bleibt gleich.
8. Dieselben Kernseiten auf Desktop öffnen.
   Erwartung: keine Bottom-Navigation; Header und Inhalte bleiben nutzbar.

Der manuelle Browser-Smoke ist als Product-Owner-Abnahmevertrag dokumentiert;
im Sprintlauf wurde der entsprechende Flask-Route-Smoke automatisiert
ausgeführt.
