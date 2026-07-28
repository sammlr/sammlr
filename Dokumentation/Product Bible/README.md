# Sammlr Product Bible

Die Sammlr Product Bible ist der zentrale, langfristige Einstiegspunkt für Produktentscheidungen und Produktspezifikationen im Repository.

Sie dokumentiert:

- welches Produkt Sammlr langfristig sein soll,
- welche Produktprinzipien und Kernlogiken beschlossen sind,
- welche Fragen bewusst noch offen sind,
- welche Ideen ausdrücklich Zukunftsmusik sind,
- und warum wesentliche Produkt- und Architekturentscheidungen getroffen wurden.

Die Product Bible ist ein Produkt-/Lastenheft. Sie ist keine kurzfristige Codex-Todo-Liste und kein Nachweis darüber, welche Funktionen bereits implementiert sind.

## Dokumentationsbereiche

- [`specifications/`](specifications/) enthält dauerhafte Spezifikationen einzelner Produktbereiche.
- [`decisions/`](decisions/) enthält künftig bewusst getroffene, datierte Produktentscheidungen.
- [`roadmap/`](roadmap/) trennt zeitliche Planung und Umsetzungshorizonte von der langfristigen Produktspezifikation.

Aktuelle Umsetzungsplanung:

- [Sammlr Development Roadmap V1](roadmap/development-roadmap-v1.md)
- [Current-State Gap Analysis](roadmap/current-state-gap-analysis.md)

Markenidentität und Corporate Design bleiben in [`Branding/Corporate ID/`](../../Branding/Corporate%20ID/) beziehungsweise in der Design Bible dokumentiert. Diese Dokumente werden nicht durch die Product Bible dupliziert.

## Index der Produktspezifikationen

| Nr. | Produktbereich | Status | Dokument |
| --- | --- | --- | --- |
| 01 | Sammlung / Alben / Stickerverwaltung | Working Product Specification | [collection.md](specifications/collection.md) |
| 02 | Tauschen / Smart Trader | Product Specification / Working Specification | [trading.md](specifications/trading.md) |
| 02A | Tradezentrale / Dealabwicklung | Working Product Specification | [trade-lifecycle.md](specifications/trade-lifecycle.md) |
| 03 | Profil & Community | Working Product Specification | [profile-community.md](specifications/profile-community.md) |
| 04 | Home / Startseite | Working Product Specification | [home.md](specifications/home.md) |
| 05 | Navigation & Information Architecture | Working Product Specification | [navigation-information-architecture.md](specifications/navigation-information-architecture.md) |

## Statusmodell

Jede Produktspezifikation unterscheidet mindestens:

### BESCHLOSSEN / KERNLOGIK

Verbindliche Produktprinzipien und grundlegende Zielarchitektur. Auch beschlossene langfristige Kernlogik ist nicht automatisch bereits implementiert.

### NOCH ZU ENTSCHEIDEN

Bewusst offene Fragen. Diese Punkte dürfen nicht durch beiläufige Implementierungsentscheidungen vorweggenommen werden.

### SPÄTER / VISION

Langfristige Optionen und Zielbilder ohne aktuelle Implementierungsanforderung.

## Änderungsregeln

1. Produktspezifikationen werden nur nach einer bewussten neuen Produktentscheidung geändert.
2. Eine Implementierung allein ändert keine Produktspezifikation.
3. Widersprüche zu älteren Dokumenten werden transparent festgehalten und nicht stillschweigend überschrieben.
4. Zeitplanung gehört in die Roadmap, Entscheidungsbegründungen gehören in `decisions/`.
5. Wesentliche Änderungen erhalten einen neuen Stand und bei Bedarf ein eigenes Decision Record.
