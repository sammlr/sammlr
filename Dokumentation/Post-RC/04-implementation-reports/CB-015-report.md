# CB-015 – Statistikprojektion Current State versus Karriere

**Stand:** 20. August 2026
**Status:** ABGESCHLOSSEN – technisch abgenommen
**Migration:** NEIN
**Echte Bestands-DB verändert:** NEIN

## 1. Ergebnis und finaler Statistikvertrag

CB-015 führt eine read-only `StatisticsProjectionService` als kanonische
Grenze für Statistikreads ein. Jede Kennzahl gehört genau einer Welt an:

- **Current State** beschreibt ausschließlich den heutigen, albumbezogenen
  Bestand.
- **Karriere/Historie** beschreibt ausschließlich persistierte historische
  Fakten und kanonisch erfolgreiche Trades.

Die globale Statistik nennt keine momentane Stickermenge mehr
„lebenslang gesammelt“. Globale Missing- und Doppeltenaggregate sowie die
dynamisch aus heutigem Bestand berechnete Trophy-/Nächstes-Ziel-Projektion
sind entfernt. Albumstatistiken zeigen Current State und den kleinen
zugelassenen historischen Albumkontext getrennt.

## 2. Current-State-Kennzahlen und Datenquellen

Für jede heutige `user_albums`-Zuordnung werden aus
`InventoryReadService` und dem aktuellen Albumkatalog projiziert:

- aktuell vorhandene unterschiedliche Sticker;
- aktuelle physische Stickeranzahl;
- aktuell fehlende Sticker;
- aktuell verfügbare Doppelte gemäß zentralem Availability-Vertrag;
- Gesamtumfang und aktueller Fortschritt in Prozent.

Die Albumreihenfolge ist deterministisch:
`season DESC, name COLLATE NOCASE, album_id, user_album_id`.
Historische Completion-Fakten verändern diese Werte nicht. Eine heutige
Bestandsänderung verändert sie sofort, ohne Karrierefakten umzuschreiben.

## 3. Karrierekennzahlen und Datenquellen

- **Erfasste Stickerzugänge seit Historienstart:** Summe der positiven,
  idempotenten `historical_sticker_acquisitions` aus CB-002. Eine spätere
  Bestandsreduktion senkt diesen Wert nicht.
- **Seit Historienstart begonnene Alben:** ausschließlich persistierte
  `historical_album_records.started_at`.
- **Historisch abgeschlossene Alben:** ausschließlich persistierte
  `historical_album_records.completed_at` aus CB-003 beziehungsweise dem
  validierten CB-004-Pfad.
- **Erfolgreiche Trades, unterschiedliche Partner, erhaltene und abgegebene
  Mengen sowie größter Trade:** ausschließlich
  `SuccessfulTradeProjectionService` aus CB-010.
- **Gültige Trophäen:** ausschließlich persistierte CB-005-Unlocks, erneut
  gegen den expliziten kanonischen Trophy-Katalog validiert.

Erhaltene und abgegebene Trade-Mengen bleiben gerichtet und werden nicht zu
einer künstlichen Menge „getauschte Sticker“ addiert. Der größte Trade zeigt
beide Richtungen separat und übernimmt unverändert den CB-010-Vertrag
`max(given_quantity_total, received_quantity_total)` samt deterministischem
Tie-Break.

Albumbezogen werden zusätzlich der persistierte Start, der erste persistierte
Abschluss und – nur bei zwei belastbaren Zeitpunkten – die nichtnegative Dauer
bis zum ersten Abschluss ausgegeben. Albumbezogene Tradewerte benutzen den
CB-010-Albumfilter.

## 4. Trennung und Legacy-Behandlung

Current State wird nie aus Completion-, Acquisition- oder Trophy-Historie
abgeleitet. Karrierewerte werden nie aus dem heutigen Stickerbestand
rekonstruiert. Insbesondere erzeugt ein heutiger 100-Prozent-Bestand keinen
Karriereabschluss, und ein später reduzierter Bestand zerstört keinen
persistierten Karriereabschluss.

Die Vor-Cutover-Sammlungshistorie bleibt unbekannt. Die UI kennzeichnet Werte
als „seit Historienstart erfasst“ und weist ausdrücklich auf unbekannte
Vorwerte hin. Auf alten Schemas ohne Historienfundament werden historische
Werte als nicht verfügbar ausgegeben, statt Nullen oder heutige Bestände als
Historie zu erfinden. `unlocked_trophies`, dynamische Trophy-Schwellen und
aktuelle Vollständigkeit sind keine Karrierebelege. Belastbare Legacy-Trades
bleiben ausschließlich über die bereits kanonische CB-010-Abgrenzung lesbar.

## 5. Privacy und Ownership

Die persönliche Vollstatistik ist owner-only. Der Service liefert für einen
abweichenden Viewer keine Projektion. Eine Albumstatistik setzt eine heutige
Albumzuordnung des authentifizierten Eigentümers voraus und liefert andernfalls
HTTP 404. Es existiert kein öffentlicher Vollstatistikpfad, über den fremde oder
private Alben sichtbar würden.

Die öffentliche CB-014-Profilprojektion bleibt durch `ProfilePrivacyService`,
Blocks und Albumprivacy begrenzt. Soweit Profil und Statistik dieselbe
Kennzahl zeigen, bezieht das Profil die Anzahl erfolgreicher Trades nun über
den gemeinsamen Statistikservice und damit unverändert aus CB-010. Weitere
Karrierekennzahlen wurden nicht ins öffentliche Profil aufgenommen.

## 6. Migration und Performance

Keine Migration ist erforderlich. CB-015 ergänzt weder Tabellen noch Spalten,
führt keinen Backfill aus und besitzt keinen Schreibpfad. Die Fundamente aus
CB-002–005 und CB-010 sind vollständig ausreichend.

Die Projektion bündelt Historienaggregate und Trophy-Reads. Für den
Closed-Beta-Testbestand mit zwei Alben wurden 35 SELECTs gemessen; der gezielte
Test setzt eine feste Obergrenze von 40. Die Zahl der Acquisition- oder
Completion-Zeilen erzeugt keine N+1-Reads. Inventory-Reads bleiben bewusst
albumbezogen, weil Current State ebenfalls albumbezogen definiert ist.

## 7. Abgrenzung

Nicht vorgezogen wurden:

- CB-012 Feed-/Home-Cutover;
- CB-016 Legacy-Cutover;
- CB-103 historische Statistikvertiefung und Fortschrittskurven;
- CB-108 Profilvertiefung;
- CB-203 Reputationssignale;
- Rankings, Forecasting, Gamification oder neue Trophy-Arten;
- Änderungen an Feed-, Notification-, Trade-, Trophy- oder Completionsemantik.

## 8. Geänderte Dateien

- `App/services/statistics_projection.py`: immutable DTOs und kanonische
  Current-State-/Karriereprojektion.
- `App/services/collector_profiles.py`: gemeinsame erfolgreiche-Trade-
  Definition für die CB-014-Profilkennzahl.
- `App/webapp.py`: `/statistik` und `/album/<album_id>/statistik` auf die neue
  Projektion umgestellt.
- `tests/test_cb015_statistics_projection.py`: gezielter CB-015-Vertrag.
- `Dokumentation/Post-RC/03-closed-beta-build-plan.md`: Statusfortschreibung.
- dieser Report.

## 9. Tests und kombinierte Suiten

Gezielte CB-015-Suite:

- **12/12**, `OK`, 0 Fehler, 0 Skips.

Abgedeckt sind aktive Alben, physische und unterschiedliche aktuelle Sticker,
Missing, Doppelte, echte Bestandsänderungen, stabile Historienzugänge,
Completion-Persistenz, fehlende 100-Prozent-Rekonstruktion, gerichtete
CB-010-Mengen, unterschiedliche Partner, größter Trade, gültige Trophäen,
Legacy-Abgrenzung, Owner-Gate, deterministische immutable Reads, gemeinsamer
CB-014-Wert, Query-Baseline und unveränderter Migrationsstand.

Kombinierte Suiten:

- Statistik/Profile/Collection/Completion: **51/51**, `OK`, 0 Fehler,
  0 Skips.
- Trade/Trophy/Privacy: **46/46**, `OK`, 0 Fehler, 0 Skips.
- Notification/Feed/Inbox: **28/28**, `OK`, 0 Fehler, 0 Skips.

Vollständige Regressionen im expliziten S32/S35-Testenvironment:

- Lauf 1: **700/700** in **8,464 s**, `OK`, 0 Fehler, 0 Skips.
- Lauf 2: **700/700** in **8,545 s**, `OK`, 0 Fehler, 0 Skips.

Ein vorheriger Diagnoseaufruf mit dem verkürzten Test-Secret `test` wurde von
den bestehenden S32/S35-Environment-Gates erwartungsgemäß abgewiesen. Er ist
kein Produkt- oder Regressionsergebnis; beide formalen Vollregressionen liefen
danach mit dem vorgeschriebenen expliziten Testing-Secret vollständig grün.

## 10. Integrity, FK, Startup, Hash und Diff

- echte V7-Bestands-DB: `PRAGMA integrity_check = ok`;
- echte V7-Bestands-DB: `PRAGMA foreign_key_check` ohne Treffer;
- isolierte temporäre V7→V18-Kopie: `integrity_check = ok`, FK-Check ohne
  Treffer, `MAX(schema_migrations.version) = 18`;
- Startup-Smoke auf der isolierten V18-Kopie: `/healthz`, `/statistik`,
  `/album/vfl/statistik` und `/profil` jeweils HTTP 200;
- `git diff --check`: ohne Befund.

SHA-256 der echten Bestands-DB vor und nach allen Arbeiten:

`3eb9da3b6d4898533030221bc80e8ed6406a25458eb8e1bca1f0e473a515b056`

Die echte DB blieb auf Schema V7 und wurde weder migriert noch durch CB-015
verändert.

## 11. Product-Contract-Bewertung und Restrisiken

Product-Contract-Verletzung: **NEIN**.

Historische Zugänge sind absichtlich nur ab dem CB-002-Cutover vollständig.
Sie sind deshalb als aufgezeichneter Zeitraum und nicht als garantierte
gesamte Lebenszeit bezeichnet. Der kleine Album-Historienblock ist keine
Vorwegnahme von CB-103; vollständige Kurven und vertiefte historische Analyse
bleiben dort.

Die Projektion verwendet weiterhin die von CB-010 klassifizierten belastbaren
Legacy-Erfolge. Deren kontrollierte Entfernung oder UI-Ausblendung gehört zu
CB-016. Bestehende ResourceWarnings aus älteren Tests sind nicht neu durch
CB-015 entstanden und beeinflussen die mit `OK` abgeschlossenen Gates nicht.

## 12. Abschluss und nächster Block

CB-015 ist formal abgeschlossen und technisch abgenommen. Gemäß der
eingefrorenen Implementierungsreihenfolge ist **CB-012 – sammlr.-Feed und
Ablösung des operativen Home** der nächste zulässige Closed-Beta-Block.
