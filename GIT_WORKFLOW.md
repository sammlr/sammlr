# Sammlr Git Workflow

Ab sofort wird nicht mehr direkt auf `main` experimentiert.

## Grundregeln

- `main` bleibt stabil.
- Jede neue Aufgabe bekommt einen eigenen Branch.
- Codex arbeitet nur im aktuellen Feature- oder Fix-Branch.
- Ein Branch enthaelt genau eine Aufgabe.
- Ein Pull Request enthaelt genau eine klare Aenderung.
- Nach Fertigstellung wird ein Pull Request erstellt.
- Erst nach Sichtpruefung wird in `main` gemerged.

## Branch-Naming

Beispiele:

- `feature/wm-branding`
- `feature/trophy-doppelte`
- `feature/trophy-album-family`
- `feature/em-branding`
- `feature/vfl-trophies`
- `fix/trophy-layout`
- `fix/mobile-nav`

## Ablauf Pro Aufgabe

1. Von `main` starten.
2. Neuen Branch erstellen.
3. Aufgabe umsetzen.
4. Lokal testen.
5. Commit machen.
6. Pull Request oeffnen.
7. Aenderungen pruefen.
8. Bei Freigabe in `main` mergen.
9. `main` neu deployen.

## Codex-Regel

Codex fasst pro Aufgabe nur die Dateien an, die fuer den aktuellen Branch relevant sind.
Liegen bereits uncommitted Aenderungen aus einer anderen Aufgabe vor, werden sie nicht
in denselben Commit aufgenommen.
