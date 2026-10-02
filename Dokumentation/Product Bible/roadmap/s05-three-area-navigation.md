# S05 – Dreiteilige Bottom-Navigation

Stand: 2026-07-31

Dieses Dokument hält die in Sprint S05 aktivierte Primärnavigation fest. Die
Development Roadmap V1 und die Product Bible bleiben die fachlich verbindlichen
Quellen.

## Zielzustand

Die globale Bottom-Navigation besitzt genau drei primäre Einstiegspunkte:

| Position | Bereich | Linkziel | Aktiver Zustand |
| --- | --- | --- | --- |
| links | Sammlung | `/sammlung` | Sammlung und sammlungseigene Unterseiten |
| Mitte | sammlr. / Home | `/` | ausschließlich Home |
| rechts | Tauschen | `/trades` | Tradezentrale und bestehende Trade-Unterseiten |

## Navigationsmatrix Ist/Soll

| Navigationseintrag vor S05 | Zustand nach S05 | Fachliche Einordnung |
| --- | --- | --- |
| Profil | kein primärer Tab | bestehender persönlicher Bereich unter `/profil`; seit S06 global über den Header-Avatar erreichbar |
| Favorit | kein primärer Tab | bestehende Sammlungsseite unter `/favorit`; markiert Sammlung aktiv |
| sammlr. | primärer Tab in der Mitte | Home unter `/` |
| Tauschen | primärer Tab rechts | Tradezentrale unter `/trades` |
| Statistik | kein primärer Tab | bestehender persönlicher Bereich unter `/statistik`, weiterhin aus `/profil` verlinkt |
| Sammlung | neuer primärer Tab links | bestehende Sammlr-Zentrale unter `/sammlung` |

Die ebenfalls geschützten Trophy-Routen `/trophaeen` und
`/album/<album_id>/trophaeen` bleiben bestehen. Globale Trophäen sind weiterhin
aus dem Profil erreichbar; Albumauszeichnungen gehören zum Bereich Sammlung.

## Ergänzung durch S06: globale Headerzugänge

Seit S06 ergänzt der gemeinsame Header die dreiteilige Primärnavigation:

- Die Sammlr-Marke führt zu Home.
- Der Initialen-Avatar führt zum bestehenden eigenen Profil.
- Die Glocke führt zur Notification-Shell ohne Badge oder Historie.

Die vollständige Headerhierarchie ist in
[S06 – Globaler Header mit Avatar- und Glocken-Shell](s06-global-header-shell.md)
dokumentiert.

## Aktive Zustände

- Home aktiviert nur `sammlr.`.
- `/sammlung`, `/favorit`, `/alben/hinzufuegen`, Albumübersichten,
  Albumstatistiken und Albumauszeichnungen aktivieren `Sammlung`.
- `/trades` und die bestehende albumbezogene Tauschpartnersuche aktivieren
  `Tauschen`.
- Persönliche Seiten wie Profil, globale Statistik und globale Trophäen bleiben
  erhalten, werden aber keinem der drei Primärbereiche künstlich zugeordnet.

## Mobile Grundfunktion

Die bestehende Floating-Bottom-Navigation wird weiterverwendet. Alle drei
historischen Spaltenregeln verwenden nun drei gleich breite Spalten. Die bereits
vorhandene Regel bis 420 Pixel hält die Navigation innerhalb des Viewports und
berücksichtigt den unteren Safe Area Inset.

## Tests

Nur S05:

```sh
python3 -m unittest discover -s tests -p 'test_s05_*.py' -v
```

Vollständiges Gate:

```sh
python3 -m unittest discover -s tests -p 'test_s0*.py' -v
```

Geprüft werden Linkziele und Reihenfolge, aktive Zustände auf Haupt- und
Unterseiten, der Erhalt der bisherigen Fachrouten, die Wiederverwendung des
vorhandenen Stickeralbum-Assets, die responsive CSS-Grundregel und der Schutz
von Produktivdatenbank und S00-Fixture.

## Bewusst nicht enthalten

- neuer Header, Avatar oder Glocke,
- Home-Inhalte oder Notificationlogik,
- neue oder finale Icons,
- Animationen oder ein Design Patch,
- CSS-Politur außerhalb der notwendigen Drei-Spalten-Anpassung,
- Änderungen an Trade-, Album- oder Inventorylogik.
