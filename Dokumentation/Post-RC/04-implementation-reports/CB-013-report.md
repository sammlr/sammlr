# CB-013 – Sammlung und historische Abschlussprojektion

**Stand:** 20. August 2026
**Status:** ABGESCHLOSSEN – technisch abgenommen
**Migration:** NEIN
**Echte Bestands-DB verändert:** NEIN

## 1. Ergebnis

CB-013 trennt die normale Sammlung als Current-State-Projektion von der
historischen Abschlussprojektion. Jedes aktive Nutzeralbum bleibt unabhängig
von seinem heutigen Fortschritt als normale, vollständig bedienbare Albumkarte
in der Sammlung. Besitzt dasselbe Nutzeralbum einen kanonischen historischen
Erstabschluss, erscheint es zusätzlich unter „Abgeschlossene Alben“.

Die historische Karte enthält ausschließlich Albumidentität, Status
„Vervollständigt“ und das historische Erstabschlussdatum. Aktueller Fortschritt,
Doppelte, Missing-/Marktwerte und andere operative Kennzahlen werden dort nicht
gerendert.

## 2. Finaler Sammlungs-/Historienvertrag

### Current State

Current State sind die gegenwärtigen `user_albums`-Zuordnungen und deren über
die vorhandenen Inventory-/Availability-Services berechnete heutige Werte.
Alle aktiven Nutzeralben bleiben in der normalen Sammlung, einschließlich
heute vollständiger und historisch abgeschlossener Alben. Favoritenreihenfolge,
Albumziel, Bestandspflege und Tradepotenzial bleiben unverändert.

### Historischer Abschluss

Historische Abschlusskarten entstehen ausschließlich aus
`historical_album_records` mit vorhandenem `completed_at`. Kanonische Quellen
sind damit:

- CB-003 `inventory_transition`, also ein realer erster
  `unvollständig → vollständig`-Übergang;
- CB-004 `validated_trophy`, ausschließlich nach dessen validiertem
  Backfillvertrag.

Der aktuelle Bestand wird für diese Auswahl nicht gelesen. Eine spätere
Bestandsreduktion entfernt oder verändert die Karte nicht. Ein heutiger
100-Prozent-Zustand ohne kanonischen Completion-Fakt erzeugt keine Karte.

## 3. Projektion und Sortierung

`CollectionProjectionService` liefert zwei unveränderliche Projektionen:

- `current_albums` in bestehender Sammlungsreihenfolge
  `season DESC, name, album_id, user_album_id`;
- `historical_completions` deterministisch nach
  `completed_at DESC, user_album_id DESC`.

Der stabile `user_album_id` bleibt Identität des konkreten heutigen
Nutzeralbums. Das rohe kanonische UTC-`completed_at` bleibt im `<time>`-Element
erhalten; das sichtbare Datum wird nach der bestehenden Europe/Berlin-Regel
formatiert. Die Karte führt zum unverändert aktiven normalen Album.

## 4. Privacy und Ownership

Eigene Collection-Reads sehen sämtliche eigenen aktiven Nutzeralben. Für
fremde Projektionen verwendet derselbe Service die bestehende zentrale
Privacy-Kaskade:

1. aktiver Account,
2. `ProfilePrivacyService` als äußeres Gate,
3. Blocks mit Vorrang,
4. Albumprivacy als innere Sichtbarkeit,
5. bestehende Friendship-Regel für `friends` beziehungsweise private Profile.

Die Projektion gibt weder eine aktuelle noch eine historische Karte zurück,
wenn das Nutzeralbum für den Viewer nicht sichtbar ist. Der Tradepool wird
nicht gelesen und nicht an Profil- oder Albumdarstellung gekoppelt.

## 5. Legacy-Behandlung

Folgende Daten sind ausdrücklich keine Completion-Evidenz:

- aktuelle 100 Prozent oder heutige Stickermengen,
- `unlocked_trophies`, auch bei Name `Album vollendet`,
- dynamische Legacy-„Vitrine“ aus dem aktuellen Fortschritt,
- Notifications, Feedzeilen, Statistiken oder Profilzustände,
- geschätzte oder rekonstruierte Zeitpunkte.

Legacydaten werden weder gelöscht noch umgedeutet. Ein durch CB-004 bereits
validierter Trophy-Fakt ist nur deshalb sichtbar, weil er als kanonischer
`validated_trophy`-Completion-Fakt in `historical_album_records` vorliegt.

## 6. Migration und Bestandsdaten

Keine Migration erforderlich. V0013 enthält den vollständigen Completion-
Readvertrag, CB-003 und CB-004 liefern die zulässigen Fakten. CB-013 fügt weder
Schema noch Backfill oder Schreibpfad hinzu.

Die echte Bestands-DB blieb auf Schema V7. SHA-256 vor und nach sämtlichen
Arbeiten:

`3eb9da3b6d4898533030221bc80e8ed6406a25458eb8e1bca1f0e473a515b056`

## 7. Abgrenzung

- CB-014 Profil-/Account-Trennung und öffentliche Profilprojektion wurde nicht
  vorgezogen; `CollectorProfileService` bleibt im bisherigen Zustand.
- CB-015 Statistikprojektion wurde nicht verändert. Historische Aggregate und
  Karrierebegriffe bleiben dessen Verantwortung.
- CB-012 Home-/Feed-Cutover wurde nicht verändert.
- CB-016 Legacy-Cutover wurde nicht vorgezogen.
- Trophy-, Feed- und Notification-Producer beziehungsweise Readverträge wurden
  nicht verändert.
- SmartMatch, Tradepool und Trade-Lifecycle wurden nicht verändert.
- Keine historische Statistik-UI, keine Read-only-Ansicht gelöschter Alben und
  keine Mehrfachexemplare.

## 8. Geänderte Dateien

- `App/services/collection_projection.py`: neue kanonische read-only
  Collection-/Completion-Projektion inklusive Privacy.
- `App/webapp.py`: normale Sammlung zeigt alle aktiven Alben; zusätzlicher
  reduzierter Bereich „Abgeschlossene Alben“.
- `App/static/style.css`: minimale Darstellung der neuen reduzierten Karte.
- `tests/test_cb013_collection_completion_projection.py`: gezielter Vertrag.
- `tests/test_s04_home_collection_routes.py`: Legacy-Vitrinentest auf den
  eingefrorenen No-Reconstruction-Vertrag umgestellt.
- `Dokumentation/Post-RC/03-closed-beta-build-plan.md`: Statusfortschreibung.
- dieser Report.

## 9. Gezielte Tests

`tests.test_cb013_collection_completion_projection`: **10/10** in **0,129 s**,
`OK`, 0 Fehler, 0 Skips.

Abgedeckt sind normales aktives Album, zusätzliche historische Karte,
Bestandsrückgang, keine Rekonstruktion aus heutigen 100 Prozent, reduzierte
Karteninhalte, deterministische Mehrfachsortierung, Albumprivacy,
ProfilePrivacy, Friendship, Blocks, Legacy-Trophy-Ausschluss, CB-003-/CB-004-
Quellen, Side-Effect-Freiheit, DTO-Unveränderlichkeit, kein Migrationszuwachs
und die bewusste Nichtvorziehung der Profil-/Statistikprojektion.

## 10. Kombinierte Suiten

- Collection/Album/Completion/Privacy: **195/195** in **1,446 s**, `OK`,
  0 Fehler, 0 Skips.
- Trophy/Feed/Notification: **70/70** in **0,716 s**, `OK`, 0 Fehler,
  0 Skips.
- SmartMatch/Trade-/Erfolgsprojektion: **91/91** in **1,582 s**, `OK`,
  0 Fehler, 0 Skips.

## 11. Vollständige Regressionen

- Lauf 1: **676/676** in **8,197 s**, `OK`, 0 Fehler, 0 Skips.
- Lauf 2: **676/676** in **8,116 s**, `OK`, 0 Fehler, 0 Skips.

Beide offiziellen Läufe verwendeten das explizite S32/S35-Test-Environment
und die Paket-Discovery.

## 12. Integrity, FK und Startup

- Echte V7-Bestands-DB: `PRAGMA integrity_check = ok`,
  `PRAGMA foreign_key_check` ohne Treffer.
- Isolierte, ausschließlich temporär V7→V18 migrierte Kopie:
  `integrity_check = ok`, FK-Check ohne Treffer.
- Offizieller Startup-Smoke auf dieser V18-Kopie: `/healthz` HTTP 200 mit
  `{"status":"ok"}` und authentifiziertes `/sammlung` HTTP 200.
- Die Migration der Kopie erzeugte erwartungsgemäß keine historischen Karten
  und keinen Backfill.
- Zusätzlicher Kompatibilitäts-Smoke auf unveränderter V7-Kopie:
  `/sammlung` HTTP 200 ohne erfundene Abschlussprojektion. `/healthz` meldet
  dort erwartungsgemäß 503, weil die produktive Runtime Schema V18 verlangt;
  dieser Diagnoseaufruf ist nicht der offizielle Startup-Gate-Lauf.
- `py_compile`: erfolgreich; nur die zwei bereits vorhandenen
  `SyntaxWarning`s zu `\d`-Stringliteralen in `App/webapp.py`.
- `git diff --check`: ohne Befund.

## 13. Product-Contract-Bewertung und Restrisiken

Product-Contract-Verletzung: **NEIN**.

Das aktuelle Schema bindet historische Fakten per `ON DELETE RESTRICT` an die
aktive `user_albums`-Identität. Deshalb kann CB-013 nur die heute mögliche
aktive und anklickbare Karte projizieren. Der von PO-05/PO-06 vorgesehene
spätere Zustand „aktives Album gelöscht, Abschluss bewusst bewahrt und Karte
nicht anklickbar“ benötigt zuerst den ausdrücklich vertagten Löschvertrag und
wurde nicht simuliert oder vorweggenommen. Mehrfachexemplare bleiben ebenfalls
Future-Scope.

Alben ohne validierten historischen Completion-Fakt bleiben bewusst ohne
Abschlusskarte, selbst wenn Legacydaten oder Current State einen Abschluss
vermuten lassen. Das ist gewollte Datenvorsicht, keine Projektionslücke.

## 14. Abschluss und nächster Block

CB-013 ist formal abgeschlossen und technisch abgenommen. Gemäß der
eingefrorenen Reihenfolge ist **CB-014 – Profil-/Account-Trennung und öffentliche
Projektion** der nächste zulässige Closed-Beta-Block.
