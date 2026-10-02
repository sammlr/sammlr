# CB-014 – Profil-/Account-Trennung und öffentliche Projektion

**Stand:** 20. August 2026
**Status:** ABGESCHLOSSEN – technisch abgenommen
**Migration:** NEIN
**Echte Bestands-DB verändert:** NEIN

## 1. Ergebnis

CB-014 trennt die öffentliche Sammlerprojektion vom internen Account- und
Einstellungsmodell. Eigenes und fremdes Profil verwenden denselben fachlichen
Profilkern. Nur der Eigentümer erhält zusätzlich eine schmale Navigation zu
Sammlung, Statistik, Trophäenschrank, Trade-Archiv, Freunden und dem getrennten
Accountbereich `/account`.

Der öffentliche Profilkern zeigt ausschließlich erlaubte Identitätsdaten,
Freundschaftsaktionen, sichtbare Albumidentitäten, kanonische Abschlüsse,
gültige kanonische Trophäen und die vier PO-08-Kennzahlen. Accountaktionen,
Passwort-/Securitydaten und Lifecycle-Metadaten werden nie Bestandteil dieser
Projektion.

## 2. Öffentlicher Profilvertrag

Die read-only `CollectorProfileDTO` enthält:

- öffentliche Identität: Benutzername und optionaler Anzeigename;
- `current_albums`: nur für den Viewer sichtbare heutige Albumidentitäten;
- `historical_completions`: nur kanonische CB-013-Abschlussfakten;
- `valid_trophies`: nur gültige CB-005-Unlocks;
- Rating-Aggregat aus Anzahl und Durchschnitt;
- kanonische Anzahl erfolgreicher Trades aus CB-010;
- das Ergebnis des äußeren CB-006-Privacy-Gates.

Die vier sichtbaren PO-08-Kennzahlen sind exakt:

1. Bewertung mit Bewertungsanzahl,
2. erfolgreiche Trades,
3. abgeschlossene Alben,
4. gültige Trophäen.

Nicht projiziert werden Doppelte, globale Missing-Werte, Stickeranzahl,
Fortschrittswerte, Partnerzahl, Ratingdetails oder einzelne Rater, interne
IDs, Passwort-/Session-/Securitydaten, Accountstatus, Adminflags oder andere
nicht freigegebene Statistikwerte. Die vier Kennzahlen werden je Profil genau
einmal gerendert.

## 3. Kanonische Datenquellen

- **Rating:** `TradeRatingService.summary_for_user`.
- **Erfolgreiche Trades:**
  `SuccessfulTradeProjectionService.count_for_user`; damit bleiben Lifecycle-
  und belastbare Legacy-Erfolge gemäß CB-010 dedupliziert.
- **Abgeschlossene Alben:** `CollectionProjectionService` und ausschließlich
  `historical_album_records` aus CB-003 beziehungsweise validiertem CB-004.
- **Trophäen:** `canonical_trophy_unlocks`, validiert gegen den expliziten
  CB-005-Katalog. `unlocked_trophies` wird nicht als öffentliche Wahrheit
  gelesen.
- **Aktuelle Alben:** heutige `user_albums`-Identitäten ohne Bestands- oder
  Fortschrittskennzahlen.

Ein heutiger vollständiger Bestand erzeugt keinen historischen Abschluss.
Legacy-Trophäen erzeugen weder Completion- noch Trophy-Zahlen. Es gibt keinen
Backfill und keine Rekonstruktion unbekannter Historie.

## 4. Sortierung und Darstellung

- aktuelle Alben: bestehende CB-013-Reihenfolge
  `season DESC, name, album_id, user_album_id`;
- Abschlüsse: `completed_at DESC, user_album_id DESC`;
- gültige Trophäen: `unlocked_at DESC, event_key DESC`.

Abschlüsse zeigen Albumidentität und Abschlussdatum. Trophäen zeigen den
kanonischen Namen und die sichtbare Albumidentität. Fremde Detailstatistiken
werden nicht gerendert.

## 5. Privacy, Ownership und Deep Links

Die Reihenfolge ist unverändert fail-closed:

1. nur aktive Accounts sind adressierbar;
2. `ProfilePrivacyService` ist das äußere Gate;
3. Blocks gewinnen vor öffentlichem Profil und bestätigter Freundschaft;
4. bei privatem Profil ist gegenseitige bestätigte Freundschaft erforderlich;
5. Albumprivacy filtert als inneres Gate Alben, zugehörige Abschlüsse und
   Trophäen gemeinsam.

Pending Requests und bloße historische Accepted-Zeilen öffnen kein privates
Profil. Derselbe Gate-Vertrag gilt für Profil-Album- und Sticker-Deep-Links.
Ein verweigertes Profil beendet die Projektion vor Album-, Trophy-, Trade- und
Ratingreads. Der Anzeigename wird im privaten Shell-Zustand nicht ausgegeben.

## 6. Account-Trennung

`AccountSettingsService` liefert ein separates, ausschließlich im
authentifizierten Owner-Pfad verwendetes DTO. `/account` bündelt die bereits
vorhandenen Aktionen für Name, Benutzername, Passwort, Profilprivacy,
Datenexport, Abmeldung, Deaktivierung und Anonymisierung. Die bestehenden
Mutationrouten und ihre Security-/CSRF-Semantik wurden nicht verändert.

Das Profil enthält nur einen Link in diesen Bereich. Fremde Profile besitzen
weder den Link noch Accountaktionen. Passwort-Hash, Accountstate, interne
Nutzer-ID und andere interne Felder werden auch auf `/account` nicht gerendert.

## 7. Tradepool und Abgrenzung

Das zuvor in der Profilseite berechnete inventarbezogene Tradepotenzial wurde
aus der öffentlichen Profilprojektion entfernt. Dadurch können private Alben
nicht indirekt über Coverage oder TopMatch-Namen sichtbar werden. Die
Tradepool-Flags, Matchingservices, Tauschen-Routen und fachliche
Tradepool-Unabhängigkeit bleiben vollständig unverändert.

Nicht vorgezogen wurden:

- CB-015 Current-State-/Karriere-Statistik;
- CB-012 Home-/Feed-Cutover;
- CB-016 vollständiger Legacy-Cutover;
- CB-108 Profil-/Bewertungsvertiefung;
- Avatar-/Ausweis-Perfektion;
- Ratingdetails oder Partnerzahl;
- neue Profil-, Trophy-, Feed-, Notification- oder Trade-Semantik.

## 8. Performance

Trophäen für alle sichtbaren Albumzuordnungen werden gebündelt in zwei Queries
geladen und anschließend gegen den kanonischen Katalog validiert. Die gezielte
Query-Baseline bleibt mit maximal 30 SELECTs begrenzt, unabhängig davon, wie
viele Trophy-Unlocks zu den sichtbaren Alben gehören. Der V18-Profilread liest
weder `stickers` noch `unlocked_trophies`; dadurch entstehen keine
inventarbezogenen N+1-Reads oder Legacy-Detailreads.

## 9. Migration und Bestandsdaten

Keine Migration erforderlich. Alle benötigten Quellen existieren durch
CB-005/006/010/013. CB-014 fügt kein Schema, keinen Backfill und keinen
Schreibpfad hinzu.

Die echte Bestands-DB blieb auf Schema V7. SHA-256 vor und nach sämtlichen
Arbeiten:

`3eb9da3b6d4898533030221bc80e8ed6406a25458eb8e1bca1f0e473a515b056`

## 10. Geänderte Dateien

- `App/services/collector_profiles.py`: öffentliche Profilprojektion und
  getrenntes Account-Settings-DTO.
- `App/services/trophy_unlocks.py`: gebündelter, katalogvalidierter Read für
  privacy-gefilterte Nutzeralben.
- `App/webapp.py`: Profilrenderer, Accountseite/-navigation und Entfernung des
  inventarbezogenen Profil-Tradepotenzials.
- `tests/test_cb014_profile_account_projection.py`: gezielter CB-014-Vertrag.
- bestehende Profil-, Privacy-, Rating-, Community-, Navigation-, HTTP- und
  Compliance-Tests: auf die neue vertragliche Trennung aktualisiert.
- `Dokumentation/Post-RC/03-closed-beta-build-plan.md`: Statusfortschreibung.
- dieser Report.

## 11. Tests

Gezielte CB-014-Suite:

- **12/12**, `OK`, 0 Fehler, 0 Skips.

Abgedeckt sind eigenes und fremdes Profil, exakt vier Kernzahlen, gültige
Trophäen, kanonische Historie, fehlende Rekonstruktion, Albumprivacy,
ProfilePrivacy, bestätigte Freunde, Pending Requests, Block-Priorität,
Accountleak-Verbot, Deep-Link-Gates, unveränderter Tradepool, Side-Effect-
Freiheit, Unveränderlichkeit, Query-Baseline und kein Migrationszuwachs.

Kombinierte Suiten:

- Profile/Collection/Privacy/Community: **63/63**, `OK`, 0 Fehler, 0 Skips.
- Trade/Rating/History/Trophy: **55/55**, `OK`, 0 Fehler, 0 Skips.
- Feed/Notification/Inbox: **56/56**, `OK`, 0 Fehler, 0 Skips.

Vollständige Regressionen im expliziten S32/S35-Testenvironment:

- Lauf 1: **688/688** in **8,220 s**, `OK`, 0 Fehler, 0 Skips.
- Lauf 2: **688/688** in **8,209 s**, `OK`, 0 Fehler, 0 Skips.

## 12. Integrity, FK, Startup und Diff

- echte V7-Bestands-DB: `PRAGMA integrity_check = ok`;
- echte V7-Bestands-DB: `PRAGMA foreign_key_check` ohne Treffer;
- isolierte temporäre V7→V18-Kopie: `integrity_check = ok`, FK-Check ohne
  Treffer;
- Startup-Smoke auf der isolierten V18-Kopie: `/healthz`, `/sammlung`,
  `/profil` und `/account` jeweils HTTP 200;
- `git diff --check`: ohne Befund.

Der bewusst nicht als Gate verwendete Produktionsimport aus `/private/tmp`
wurde erwartungsgemäß von der bestehenden S34-Volume-Prüfung abgewiesen;
der offizielle isolierte Startup-Smoke lief deshalb im expliziten
Testenvironment, wie die vorigen CB-Abnahmen.

## 13. Product-Contract-Bewertung und Restrisiken

Product-Contract-Verletzung: **NEIN**.

Die öffentliche Profilzahl für Abschlüsse und Trophäen kann bei fremden
Viewern kleiner sein als die ownerinterne Gesamtzahl, weil Albumprivacy die
zugehörigen Fakten gemeinsam filtert. Das ist der beabsichtigte Privacyvertrag
und kein inkonsistentes Aggregat.

Alte V6-Testfixtures besitzen noch einen rein technischen Compatibility-Pfad
für aktuelle Albumidentitäten. Der produktive V18-Pfad verwendet ausschließlich
die kanonischen Projektionen. Der vollständige Removal dieses Altpfads bleibt
CB-016 vorbehalten.

## 14. Abschluss und nächster Block

CB-014 ist formal abgeschlossen und technisch abgenommen. Gemäß dem
eingefrorenen Bauplan ist **CB-015 – Statistikprojektion Current State versus
Karriere** der nächste zulässige Closed-Beta-Block.
