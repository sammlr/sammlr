# S31 – UI Foundation und globale Workflow-Vereinheitlichung

Stand: 2026-08-09

## Ziel und Scope

S31 wendet das in S30 definierte Designsystem auf sämtliche produktiven
Hauptseiten und Workflows an. Betroffen sind insbesondere Home, Sammlung,
Album, Stickerwall, Tauschbörse, Tradeanfragen, laufende Deals, Dealansicht,
Notifications, Profil, Freundesliste und Nutzersuche. Fachlogik, Datenmodelle,
Routenbesitz und Produktzustände bleiben unverändert.

## Architektur

```text
S30 Design Tokens
  -> globale S31-Produktseitenklasse
  -> zwei Headervarianten
  -> dreiteilige mobile Hauptnavigation
  -> gemeinsame Komponentenprojektion
     -> Karten / Listen / Tabs / Filter
     -> Buttons / Formulare / Dialoge
     -> Badges / Statuschips / Leerzustände
  -> bestehende Flask-Workflows ohne Fachänderung
```

`s31-product-page` ist die einzige globale Aktivierungsgrenze. Auth-Seiten,
Debugausgaben und nicht produktive Hilfsansichten werden nicht stillschweigend
in den Patch gezogen. Die vorhandenen S30-Tokens bleiben die einzige Quelle
für Farbe, Typografie, Abstand, Radius und Schatten.

## Betroffene Komponenten

### Header

- `app-header-large`: Home, Sammlung und Profil.
- `app-header-compact`: Detailseiten, Workflows, Listen und Dealansichten.

Höhe und Innenabstände werden ausschließlich aus S30-Abstands- und
Radiustokens zusammengesetzt. Beide Varianten verwenden weiterhin Marke,
Glocke und Avatar aus dem bestehenden Header. Der Header ist mobile sticky;
es gibt keinen neuen Navigations- oder Notificationpfad.

### Hauptnavigation

Die mobile Navigation besitzt dauerhaft genau drei fachliche Hauptziele:

1. Sammlung,
2. Home als zentral hervorgehobener `sammlr.`-Spot,
3. Tauschen.

Profil und Notifications sind persönliche Aktionen und bleiben ausschließlich
oben rechts im bestehenden Header. Sie werden nicht zusätzlich in der Bottom-
Navigation angeboten. Auf Desktop wird die Bottom-Navigation ausgeblendet. Die
fokussierte Dealansicht und weitere bestehende Fokusworkflows behalten ihren
kompakten Workflowheader ohne Bottom-Navigation.

### Komponentenfamilien

- Seitenshells: gemeinsame Fläche, maximale Breite und Safe-Area-Abstände.
- Karten und Listen: S30-Flächen, Radien und Schatten; interaktive Zeilen mit
  sichtbarem Hover- und Fokuszustand.
- Buttons: einheitliche Primary-, Secondary-, Tertiary- und Danger-Hierarchie.
- Formulare: gemeinsame Controls, Fokus, Disabled- und Fehlerdarstellung.
- Dialoge: S30-Modalfläche; native Dialoge bleiben per Escape schließbar.
- Tabs und Filter: pillförmig, tastaturbedienbar und mit eindeutigem aktiven
  Zustand.
- Badges und Statuschips: ausschließlich semantische S30-Statusfarben.
- Leerzustände: bestehende Texte, bestehende Aktionen, keine neue Fachaktion.

## Statuszuordnung

| Fachzustand | S30-Statusfamilie |
|---|---|
| Reserviert | Blau / Transit |
| Versand läuft | Blau / Transit |
| Teilweise erhalten | Orange / Offen |
| Problem offen | Rot / Fehler |
| Trade mit Problem beendet | Dunkelorange |
| Problem nachträglich gelöst | Grün / Erfolg |
| Abgelaufen | Grau / Deaktiviert |
| Obsolet | Grau / Deaktiviert |

Die Zuordnung ändert weder Lifecycle-Wert noch angezeigten Fachtext.

## Stickerwall und Tradebereiche

Die Stickerwall erhält ausschließlich die globale S30-Komponentensprache.
Quantity, Filterprädikate, Batchlogik, Transitprojektion und Fortschritt werden
nicht verändert. Die endgültige Stickerwall-Version bleibt der späteren UI
Week vorbehalten.

Alle Tradeansichten teilen Karten-, Tab-, Aktions- und Statusdarstellung. Die
bestehenden Request-, Lifecycle-, Reservation-, Shipping-, Receipt-, Problem-,
Rating- und Smart-Trade-Pfade bleiben vollständig erhalten.

## Datenfluss, Read-/Write-Pfade und Seiteneffekte

S31 ergänzt keine Datenquelle und keinen Schreibpfad. Jede Seite liest und
schreibt weiterhin ausschließlich über ihre bereits getesteten Services und
Routen. Die Änderungen betreffen HTML-Klassen, wiederverwendete Icons und CSS.
Es entstehen keine Datenbankmutation, Migration, Notification, Trophy oder
Inventorybuchung.

## Accessibility und Mobile

- 390 px und 430 px sind die gestalteten Referenzbreiten.
- Touchziele besitzen mindestens 44 × 44 px.
- Fokusreihenfolge folgt weiterhin der semantischen DOM-Reihenfolge.
- Links, Buttons und Formcontrols erhalten einen sichtbaren Fokusindikator.
- Native Dialoge sind per Escape schließbar.
- Statusinformationen behalten Text beziehungsweise Symbol zusätzlich zur
  Farbe.
- S30-Kontrastpaare bleiben mindestens WCAG 2.2 AA.
- Tablet und Desktop werden regressionssicher gehalten, aber nicht neu
  gestaltet; Desktop zeigt keine Bottom-Navigation.
- Reduced Motion aus S30 bleibt wirksam; neue komplexe Animationen oder
  Gestensteuerung existieren nicht.

## Unveränderte Komponenten

Unverändert bleiben Inventory, Snapshot, Coverage, TopMatch, Smart Requests,
Trade Lifecycle, Reservierungen, Versand, Empfang, Problembehandlung,
Bewertungen, Notifications als Fachsystem, Operational Home, Profile,
Albumprivacy, Tradepool, Communityberechtigungen, Migrationen, Datenbank und
sämtliche bestehenden Icons und Masterassets.

## Referenzscreens

Die Referenzscreens wurden bei 390 px logischer Breite aus authentifizierten
HTML-Renderings gegen eine isolierte, temporär auf V0009 migrierte Kopie der
S00-Fixture erzeugt. Sie dokumentieren ausschließlich den
S31-Darstellungsstand und sind keine neue Produktfunktion.

### Home

![S31-Referenzscreen Home](screens/home-390.png)

### Sammlung

![S31-Referenzscreen Sammlung](screens/sammlung-390.png)

### Album

![S31-Referenzscreen Album](screens/album-390.png)

### Stickerwall

![S31-Referenzscreen Stickerwall](screens/stickerwall-390.png)

### Trade

![S31-Referenzscreen Trade](screens/trade-390.png)

### Notifications

![S31-Referenzscreen Notifications](screens/notifications-390.png)

### Profil

![S31-Referenzscreen Profil](screens/profil-390.png)

Die Bilddateien liegen unter
`Dokumentation/Product Bible/design-system/screens/`. Tablet und Desktop
bleiben regressionsgesichert, werden in S31 aber ausdrücklich nicht neu
gestaltet und sind deshalb nicht Teil dieses mobilen Referenzsatzes.
