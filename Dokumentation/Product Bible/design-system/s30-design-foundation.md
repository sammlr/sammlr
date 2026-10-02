# S30 – Design Foundation

Stand: 2026-08-09

## Ziel und Scope

S30 schafft ein verbindliches, tokenbasiertes Designfundament und wendet es
ausschließlich auf die sieben freigegebenen Referenzseiten Home, Sammlung,
Album, Tauschbörse, Dealansicht, Notifications und Profil an. Das bestehende
Layout und sämtliche Fachfunktionen bleiben unverändert. Header, dreiteilige
Navigation und bestehende Icons sind ausdrücklich nicht Teil der Migration;
ihre globale Vereinheitlichung gehört zu S31.

## Architektur und Datenfluss

Die Designschicht ist vollständig statisch und read-only:

```text
Product-Owner-Tokenvertrag
  -> CSS Custom Properties in :root
  -> semantische S30-Komponenten
  -> .s30-reference-page als enger Seiten-Scope
  -> bestehendes HTML der sieben Referenzseiten
```

Es entstehen keine DTOs, Services, Datenbankzugriffe, APIs oder fachlichen
Read-/Write-Pfade. Die einzige Markierung im HTML ist eine Seitenklasse. Die
späten, eng begrenzten CSS-Regeln übersetzen bestehende Referenzkomponenten in
Tokens, ohne DOM-Reihenfolge, Navigation oder Interaktion umzubauen.

## Verbindlicher Tokenvertrag

### Typografie

| Token | Größe | Gewicht | Zeilenhöhe |
|---|---:|---:|---:|
| Display | 40 px | 700 | 1,1 |
| H1 | 32 px | 700 | 1,2 |
| H2 | 24 px | 700 | 1,25 |
| H3 | 20 px | 600 | 1,3 |
| Body | 16 px | 400 | 1,5 |
| Small | 14 px | 400 | 1,45 |
| Caption | 12 px | 500 | 1,4 |

Die Referenzseiten verwenden die bestehende Sammlr-Schriftfamilie mit
systemischem Fallback. Header und Navigation bleiben unberührt.

### Abstände, Radien und Schatten

- Abstände: 4, 8, 12, 16, 24, 32, 48 und 64 px.
- Radien: Small 8 px, Medium 12 px, Large 16 px, XL 24 px, Pill 999 px.
- Schatten Small: Karten.
- Schatten Medium: interaktive Elemente.
- Schatten Large: Modal und Bottom Sheet.

Alle drei Schatten sind einmal zentral definiert. Komponenten erzeugen keine
individuellen Schatten.

### Farben

Primärfarbe ist ausschließlich `#7C3AED`. Das frühere Corporate-Lila
`#5D2F86` ist kein gültiges Token mehr. Die Corporate-Basis bleibt Weiß,
hellgraue Oberfläche und dunkler Text. Die Statusfamilien sind semantisch:

| Status | Farbe | Verwendung |
|---|---|---|
| Fehlend / Fehler | Rot | fehlender Bestand, Fehlerfeedback |
| Vorhanden / Erfolgreich | Grün | Bestand, Erfolg |
| Doppelt | Violett | doppelte Sticker |
| Unterwegs | Blau | Transit |
| Offen | Orange | offene Handlung oder Zustand |
| Warnung | Gelb | nicht blockierender Warnhinweis |
| Deaktiviert | Grau | nicht verfügbare Aktion |

Für jeden Status gibt es getrennte Vordergrund-, Hintergrund- und Randtokens.
Damit wird Bedeutung nicht allein durch Farbe vermittelt und AA-Kontrast kann
zentral geprüft werden.

## Komponentenvertrag

### Buttons

- Primary: wichtigste positive Aktion.
- Secondary: gleichwertige Alternative mit Outline.
- Tertiary: zurückhaltender Link-/Textbutton.
- Danger: destruktive, ausdrücklich benannte Aktion.

Buttons teilen Mindesthöhe, Typografie, Fokusindikator, Radien und Disabled-
Verhalten. Bestehende Zielpfade und Submit-Verhalten ändern sich nicht.

### Karten

- Standard: ruhige Inhaltsfläche.
- Interactive: klickbare Karte mit Medium-Schatten und Fokuszustand.
- Status: semantischer Zustand mit Statusrand.
- Empty: leerer Zustand mit erklärendem Text und fachlich vorhandenem
  Einstieg beziehungsweise Aktion.

### Formulare und Feedback

Input, Select und Textarea teilen Fläche, Rand, Fokusindikator und Disabled-
Zustand. Checkbox und Radio behalten ihre native Semantik und verwenden
`accent-color`. Feedback verwendet Success, Warning, Error oder Info mit
Text-/Flächenpaaren aus den Statusfarben. Leere Zustände werden nur als
Komponente eingesetzt, wenn eine passende Aktion vorhanden ist.

## Referenzseiten

Die Klasse `.s30-reference-page` aktiviert das Fundament ausschließlich auf:

1. Home (`/`),
2. Sammlung (`/sammlung`),
3. Album (`/album/<id>`),
4. Tauschbörse (`/trades`),
5. Dealansicht (`/trades/<id>`),
6. Notifications (`/notifications`),
7. eigenes und fremdes Profil (`/profil`, `/profil/<username>`).

Die Regeln schließen `.app-header`, `.bottom-nav` sowie deren Inhalte aus.
Andere Seiten behalten ihre bisherige Darstellung bis S31.

## Barrierefreiheit und Mobile-Vorprüfung

- Text- und Statusfarbpaare werden rechnerisch gegen WCAG 2.2 AA geprüft.
- Interaktive Elemente erhalten einen deutlich sichtbaren Fokusindikator.
- Native Controls und semantische Links/Buttons bleiben erhalten.
- `prefers-reduced-motion` deaktiviert die verbliebenen dekorativen
  Übergänge innerhalb der Referenzseiten.
- Die gezielte mobile Referenzprüfung erfolgt bei 390 px und 430 px.
- Es wird keine Tabletoptimierung eingeführt.

## Unveränderte Komponenten und Seiteneffekte

Unverändert bleiben Header, Navigation, Icons, Layoutreihenfolge, Inventory,
Trade Lifecycle, Shared Snapshot, Coverage, TopMatch, Smart Requests,
Notifications als Fachsystem, Operational Home als Projektion, Profile,
Privacy, Bewertungen und Communitylogik. Es gibt keine Mutation, Migration,
neue Tabelle, neue Route, neue Aktion oder neue Produktentscheidung.

## Abgrenzung zu S31

S30 ist keine globale CSS-Migration. Historische Selektoren außerhalb der
Referenzseiten, globale Header-/Navigationsregeln, Icons, restliche Produktseiten
und eine weitergehende Bereinigung der Alt-CSS-Schichten bleiben ausdrücklich
offen für S31.
