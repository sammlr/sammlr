# S01 – Bestands-Regressionstests

| Feld | Wert |
| --- | --- |
| Status | abgeschlossen |
| Stand | 2026-07-28 |
| Verbindliche Grundlage | [Development Roadmap V1, Sprint S01](development-roadmap-v1.md#s01--bestands-regressionstests) |
| Abhängigkeit | [S00-Referenzfixture](s00-reference-and-test-data.md) |
| Anwendungscode | unverändert |
| Datenbankschema | unverändert |

Diese Notiz dokumentiert ausschließlich die Testfallmatrix für Sprint S01.
Inventory-Service, Schemaarbeiten, Papierlisten-/Tradeflowtests und spätere
Produktarbeit sind nicht enthalten.

## Testbefehl

Vom Repository-Wurzelverzeichnis:

```sh
python3 -m unittest discover -s tests -p 'test_s01_*.py' -v
```

Der Befehl verwendet ausschließlich die Python-Standardbibliothek. Es wurden
keine Testabhängigkeiten ergänzt.

## Testdatenbank und Isolation

Kanonische Ausgangsbasis ist
`App/Database/sammlr_reference_s00.db`.

1. Noch vor dem Import von `App/webapp.py` legt die Testsuite eine temporäre
   Kopie der S00-Fixture an und setzt `DATABASE_PATH` auf diese Kopie.
2. Jeder einzelne Test erhält anschließend eine neue, unabhängige Kopie in
   einem eigenen temporären Verzeichnis.
3. `webapp.DB` zeigt während des Testfalls ausschließlich auf diese Kopie.
4. Nach dem Test wird die Kopie verworfen.
5. Nach jedem Test wird die SHA-256-Prüfsumme von
   `App/Database/sammlr.db` gegen den Wert vor dem Testlauf geprüft.

Damit teilen Tests keine Schreibzustände und öffnen die Standard-Datenbank
nicht als Testziel.

## Testfallmatrix

| Nr. | Bereich | Normalfall oder Randfall | Route/Einheit | Geschütztes Verhalten |
| ---: | --- | --- | --- | --- |
| 1 | Hinzufügen | normal | `GET /add/vfl/1` | vorhandene Menge `3 → 4`, Doppelte `2 → 3` |
| 2 | Hinzufügen | Randfall | `GET /add/vfl/3` | fehlender Sticker wird mit Menge `1`, Doppelte `0` angelegt |
| 3 | Entfernen | normal | `GET /remove/vfl/1` | Menge `3 → 2`, Doppelte `2 → 1` |
| 4 | Entfernen | Randfall | `GET /remove/vfl/2` | letzte Kopie erreicht Null und die Zeile entfällt |
| 5 | Entfernen | Randfall | `GET /remove/vfl/3` | fehlender Sticker erzeugt keinen negativen Bestand |
| 6 | Inline-`+` | normal | `POST /album/vfl/sticker/1/quantity` | DB und JSON melden Menge `4`, Doppelte `3` |
| 7 | Inline-`+` | Randfall | gleiche Route für Code `3` | fehlender Sticker wird mit Menge `1` angelegt |
| 8 | Inline-`−` | normal | gleiche Route für Code `1` | DB und JSON melden Menge `2`, Doppelte `1` |
| 9 | Nullgrenze | Randfall | Inline-`−` mit `-1`, danach `-99` | Menge bleibt bei Null; keine negative Zeile entsteht |
| 10 | Delta-Eingabe | Randfall | Inline-Route mit `0` und Text | HTTP 400; Bestand bleibt unverändert |
| 11 | Filterlogik | normal/Randfall | `filter_ok()` | fehlend, vorhanden, doppelt und alle für Mengen `0`, `1`, `3` |
| 12 | Stickerwall-Filter | normal | drei `GET /album/vfl?filter=…` | nicht passende Karten erhalten `filter-hidden`, passende nicht |
| 13 | Albumfortschritt | normal | `lade_album_for_user()` und Inline-Route | eindeutige Codes statt Gesamtmenge; `3/4 = 75 %`, danach `4/4 = 100 %` |
| 14 | Undo Add | normal | Add, danach `GET /undo` | Menge und Doppelte werden exakt auf `3/2` zurückgesetzt |
| 15 | Undo Remove | Randfall | letzte Kopie entfernen, danach Undo | gelöschte Zeile wird mit Menge `1`, Doppelte `0` wiederhergestellt |
| 16 | Codeauflösung | normal/Randfall | `resolve_code()` | VFL-Grenzen `1` und `250` gültig; `0`, `251` und Text ungültig |

Alle schreibenden Fälle prüfen sowohl die Route als auch den resultierenden
SQLite-Zustand. Die Inline-Fälle prüfen zusätzlich den JSON-Vertrag.

## Geschützte Invarianten

- `quantity` sinkt nicht unter `0`.
- `duplicates` entspricht nach jedem getesteten Schreibweg
  `max(quantity - 1, 0)`.
- Menge `0` wird im bestehenden Modell durch das Fehlen der Stickerzeile
  repräsentiert.
- Albumfortschritt zählt unterschiedliche vorhandene Codes, nicht physische
  Gesamtmenge.
- Stickerwall-Filter unterscheiden Menge `0`, mindestens `1` und mindestens
  `2`.
- Undo stellt reale Add-/Remove-Bestandsänderungen einschließlich einer zuvor
  gelöschten letzten Kopie wieder her.
- Die bestehende VFL-Codeauflösung akzeptiert nur den Katalogbereich
  `1` bis `250`.

## Reproduzierbarkeit

Der vollständige normale Testlauf wurde zweimal in getrennten Prozessen
ausgeführt. Beide Läufe:

- führten 16 Tests aus,
- endeten mit `OK`,
- benötigten jeweils rund 0,04 Sekunden,
- hinterließen die Standard-Datenbank mit unveränderter Prüfsumme.

## Nachweis durch absichtliche Mengenabweichung

Die Testsuite unterstützt ausschließlich für diesen Nachweis eine
prozesslokale Mutation:

```sh
SAMMLR_S01_MUTATE_QUANTITY=1 \
python3 -m unittest discover -s tests -p 'test_s01_*.py' -v
```

Dabei wird `change_sticker_quantity()` nur im Speicher des Testprozesses so
ersetzt, dass ein Element zu viel angewendet wird. Es wird keine
Anwendungsdatei editiert. Erwartetes und bestätigtes Ergebnis:

- Exit-Code `1`,
- 16 ausgeführte Tests,
- 4 fehlgeschlagene Inline-Mengentests,
- klare Abweichungen wie erwartet `4`, tatsächlich `5`.

Damit ist nachgewiesen, dass eine absichtliche Abweichung der Mengenlogik
erkannt wird.

## Bewusste Nichtabdeckung

Nicht getestet und nicht verändert wurden:

- Papierlisten- und papierlistenbasierte Tradeflows aus S02,
- Trophy-, Notification- und Nebenwirkungsregressionen aus S03,
- Navigation und Seitenstruktur,
- Inventory-Service oder zentrale Inventory-Architektur,
- Reservierungen und Trade Lifecycle,
- Datenmigrationen, Security-Verbesserungen, UI, CSS und JavaScript.

## Minimale technische Anpassungen

Am Anwendungscode waren keine Anpassungen erforderlich.

Neu eingerichtet wurde nur der Ordner `tests` mit einer
S01-Testdatei. Die Datei konfiguriert den vorhandenen Flask-Einstieg vor dem
Import auf eine temporäre Fixture-Kopie. Dies ist die minimale notwendige
Teststruktur, weil zuvor keine Teststruktur existierte.

## Offene Beobachtungen für spätere Sprints

Diese Beobachtungen wurden nicht umgesetzt:

- `App/webapp.py` initialisiert die konfigurierte Datenbank bereits beim
  Modulimport. Die S01-Suite isoliert diesen Effekt durch eine
  Bootstrap-Kopie; eine Architekturänderung gehört nicht in S01.
- Die mutierenden Add-/Remove-Endpunkte verwenden aktuell `GET`. Eine
  Security- oder API-Änderung gehört nicht in S01.
- Ein Remove-Aufruf für einen bereits fehlenden Sticker hinterlegt trotzdem
  eine Undo-Aktion; ein anschließendes Undo würde eine Kopie anlegen. S01
  verändert dieses bestehende Randverhalten nicht.
- Die Inline-Route nimmt technisch auch Deltas außerhalb `−1/+1` entgegen,
  obwohl die sichtbaren Regler nur einzelne Schritte senden. S01 ändert die
  Eingabevalidierung nicht.
- Bestehende Debug-Ausgaben erscheinen während Route-Tests auf der Konsole.
  Sie wurden nicht entfernt.

## Abschluss

S01 ist abgeschlossen: Alle verbindlichen Bestandsfälle und relevanten
Randfälle laufen deterministisch gegen unabhängige Testdatenbanken, der
Mutationsnachweis ist rot und der unveränderte Referenzzustand ist grün.
Weder sichtbares Verhalten noch fachliche Bestandslogik oder Datenbankschema
wurden geändert.

