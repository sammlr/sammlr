# SmartDeal Technical Roadmap V1

Stand: 2026-09-10. **Planung, keine Implementierungsfreigabe.** Quellen: [Product Bible §§37–38](SMARTDEAL_PRODUCT_BIBLE_V1.md), [historischer IST-Audit](SMARTDEAL_V1_IST_AUDIT.md), [Algorithm Contract V1](SMARTDEAL_ALGORITHM_CONTRACT_V1.md). Neuere PO-Entscheidungen ersetzen die damaligen offenen Punkte des Audits, ohne dessen historische Analyse umzuschreiben.

Der Comparator ist geschlossen: E=G−2n maximieren, dann G, Größenvektor, Partner-IDs und Positionen gemäß AC12. Die finale PO-Regel schließt auch die Mehrfachunterdeckung: Versand ist vor automatischer Beendigung geschützt; accepted vor open, innerhalb derselben Stufe älterer bindender Zustand vor jüngerem, bei Zeitgleichheit kanonische Vorgangs-ID ASC. Keine offene Produktfrage; AC26 beschreibt die technische Persistenzanforderung für Bindungs-/Annahmezeit und die vollständige Freigabe ohne Paketkürzung.

## Begründung der Aufteilung

17 isolierte Blöcke: **10 P0, 6 P1, 1 P2**. P0 ist notwendige Grundlage, P1 notwendig für die SmartDeal Closed Beta, P2 optional. Risikoklassen bewerten technische Eingriffstiefe, keine Zeitdauer.

Die Ausgangshypothese wird gezielt geteilt: SD-T2a schafft die bislang fehlende bindungsbewusste Need-Projektion; SD-T2b berechnet Paare. SD-T3a entscheidet die exakte Suchmethode vor SD-T3b. Identität SD-T6a muss vor Requestpersistenz feststehen; Mutual GO SD-T6b folgt deren Transaktionen. SD-T5a und SD-T5b trennen Anlage von Freigaben, werden aber erst gemeinsam aktiviert. SD-T7a schützt Buchungen, SD-T7b behandelt Bestandsverlust. Versandkontakt SD-T8a ist Pflicht; Chat SD-T8b ist keine technische Voraussetzung und bleibt separat optional.

Codebegründung: [top_match_optimization.py](../App/services/top_match_optimization.py) ist albumgebundenes Greedy mit maximal drei Paketen und einem Gesamtplanhash. [smart_trade_requests.py](../App/services/smart_trade_requests.py) nutzt Marker −22, 48 Stunden und keine Bindung bei Anlage. [trade_reservations.py](../App/services/trade_reservations.py) erzeugt heute erst bei accept einen bereits angenommenen Lifecycle; Reservations hängen an Tradepositionen. [Basisschema](../App/Database/base_schema.sql) trägt nur ein Album pro Request; Positionen im Lifecycle können bereits mehrere Alben tragen. [Migration 0011](../App/Database/migrations/0011_http_integrity_hardening.up.sql) begrenzt Status-/Confirmationwerte. Ein neuer Marker oder strukturierte Objekte in alten Codelisten sind deshalb kein sicherer migrationsfreier Shortcut.

## SD-T1 — Domain Contract und Legacy-Separation

**Priorität / Risiko:** P0 / MEDIUM.

**Ziel:** V1 ist in allen Lese-/Schreibpfaden eindeutig von unveränderten Altverträgen unterscheidbar.

**Scope:** Technischen Daten-/Adaptervertrag und minimale dauerhafte V1-Kennzeichnung bestimmen; Zustandsmatrix request/open/accepted/terminal, Multi-Album-Positionen, Eigentümerschaft der Bindungen und Koexistenz dokumentieren. Eine spätere notwendige Schemaerweiterung als enges Foundation-Arbeitspaket konkret prüfen, ohne Altvorgänge umzustellen. Nach AC26 offene Bindungszeit und Annahmezeit unveränderlich unterscheidbar sowie eine durchgehende kanonische Vorgangs-ID vorsehen; `trades.created_at` ist im IST kein Annahmezeitpunkt. Ein garantiert einmaliger Annahmeevent kann die Zeitpersistenz tragen; keine Migration ohne Modellnachweis.

**Explicit Non-Scope:** Kein globales Umschalten von −22/48h, keine rückwirkende Datenkonvertierung, keine UI-Aktivierung.

**Reuse:** Legacy-Requests, positionsbasierter Lifecycle, vorhandene Constraints und Migrationseinspielung.

**Likely Files / Areas:** App/Database/base_schema.sql; App/Database/migrations; smart_trade_requests.py; trade_reservations.py; entsprechende zukünftige V1-Adapter.

**DB / Migration:** **Voraussichtlich erforderlich** für dauerhafte V1-Abgrenzung und den späteren Multi-Album-/Pre-accept-Vertrag. Erst prüfen, ob vorhandene Strukturen dies ohne falschen accepted-Zustand und ohne Umdeutung alter Felder tragen. Keine Migration allein zur Vereinfachung; konkretes Minimalmodell ist Ergebnis dieses Blocks.

**Required Tests:** Bestehende S22, CB011, S14 und S33; neue Koexistenz-/Roundtrip-Verträge für alte und neue Vorgänge sowie, falls Schema nötig, Upgrade auf einer isolierten Kopie mit Legacy-Fixtures.

**Acceptance Criteria:** Ein alter offener Request behält 48h und seinen bisherigen Reservierungszeitpunkt; ein neuer V1-Vertrag ist eindeutig erkennbar. Multi-Album-Inhalt bleibt vollständig erhalten. Unbekannte Vertragsarten werden nicht als Legacy oder V1 geraten; kein offener V1-Request wird als angenommener Trade projiziert.

**Risks:** Alte Callback-/Markerannahmen, Constraints, falsche History- oder Account-Schutzprojektion.

**Depends On:** Keine; AC01–AC34 sind Grundlage, die finale Priorität aus AC26 ist verbindlich.

### SD-T1 Implementierungsnotiz — 2026-09-10

Foundation implementiert; noch kein V1-User-Flow. Der konkrete SD-T1-Auftrag begrenzt die Umsetzung auf Klassifikation und Zeitpersistenz; Multi-Album-Payload, GO, Bindungserzeugung und übrige Roadmap-Blöcke sind nicht implementiert.

- **Schemaentscheidung:** Marker −22 bezeichnet den bisherigen Smart-Vertrag und verschwindet bei accept; Status, Notifications, Request-/Trade-Erzeugungszeit sind keine eindeutige V1-Klassifikation. Daher additive Migration **0021_smartdeal_contract_foundation**, keine Änderung von V0001–V0020 oder Tabellenneuanlage.
- **Persistenz:** `trade_requests.contract_type TEXT NOT NULL DEFAULT 'legacy'`, erlaubt ausschließlich `legacy` / `smartdeal_v1`. Alle Altzeilen und alle bisherigen Inserts ohne Feld bleiben Legacy, einschließlich manueller und alter Smart-Anfragen. Keine automatische Reklassifikation. Ein Trigger verbietet spätere Änderung des Vertragstyps.
- **Zeitgrundlage:** nullable `binding_created_at` und `accepted_at` ohne Uhr-Default oder Backfill. Erste künftige Bindung bzw. Annahme darf den jeweiligen Zeitfakt setzen; einmal gesetzte Werte sind unveränderlich, identische Wiederholung bleibt erlaubt. Diese Speicherfelder erzeugen keine Reservations und verändern keinen Lifecycle. Bestehende Legacy-Abläufe lassen sie NULL. Reservations entstehen heute erst bei accept; künftig bereits bei GO, weshalb deren alter Zeitstempel beide Zeitfakten nicht repräsentiert. `trades.created_at` übernimmt das Anfragedatum; der bisherige Smart-Accept-Event ist nicht für alle Einstiegspfade garantiert.
- **Kanonische API:** [trade_contracts.py](../App/services/trade_contracts.py): `request_contract_type`, `is_smartdeal_v1_request`, `LEGACY_CONTRACT`, `SMARTDEAL_V1_CONTRACT`. Alte Rows ohne Feld erhalten Legacy-Fallback; explizit unbekannte/NULL-Werte werden nicht geraten. Request-ID bleibt bestehende Vorgangsreferenz. Keine neue Opportunity-Identität.
- **Backout:** Additive Spalten werden nur entfernt, solange weder V1-Verträge noch neue Zeitfakten vorliegen; sonst atomare Verweigerung statt Datenverlust. Keine kanonische App-DB migriert.
- **Nachweis:** 18 neue Tests bestanden, darunter V20→V21 mit unveränderten Altwerten, erneutes DB-Öffnen, unbekannte Werte, unveränderliche Klassifikation/Zeitfakten, sichere Rückmigration, Fresh0→V21 sowie R5-Bootstrap0→V20→explizitV21. Legacy-Accept/Ship/Receipt auf V21 bucht weiterhin erst bei Versand/Empfang und idempotent; alte Smart-Frist bleibt48h. Integrity jeweils `ok`, FK-Verletzungen0.
- **Release-Regression:** Isolierter Allowlist-Export plus exakt die vier neuen Code-/Migration-/Testdateien, unveränderter B1.1-Cohortvertrag: **885 ausgeführt, 867 bestanden, 18 Failures, 0 Errors, 0 Skips**. Sämtliche Fehler betreffen feste höchste Version20 (16 Assertions) bzw. Migrationslisten1–20 (2 Assertions). Unveränderter V20-Kontrollexport: **867/867 bestanden**. Keine bestehenden Tests geändert oder neu ausgeschlossen. Somit kein grüner vollständiger V21-Release-Nachweis; die ausdrücklich auf V20 gebundenen Schemaerwartungen bleiben als konkrete Integrationsgrenze sichtbar. R5-Allowlist, Bootstrapziel20 und Releaseklassifikation unverändert; dies ist kein RC0.

Kanonische DB unverändert auf V20: `integrity_check=ok`, `foreign_key_check=0`; SHA-256 vor/nach `a183302bea3a50201d3036f5b14999da5d138a0a5156044f814c3d30880d0c56`. Ausführungslogs: `/private/tmp/sdt1-full-final.log`, `/private/tmp/sdt1-v20-control.log`; Testexport `/private/tmp/sammlr-sdt1-candidate`. Keine UI-/Routenänderung, keine Änderung bestehender Lifecycle-Services, kein Beginn SD-T2a, kein Staging/Commit/Push/Deploy.

**Acceptance Fix1.1:** Die oben dokumentierten18 V20-Erwartungsfehler sind durch gezielte Testbaseline-Anpassung geschlossen. Final **885/885 Release-Tests bestanden**, keine Failures/Errors/Skips. Runtime und Migration0021 unverändert; Produktions-/Bootstrapziel bleibt V20, verfügbare Migrationsbaseline V21. [Einzelklassifikation und Nachweis](SD_T1_ACCEPTANCE_FIX_1_1.md). SD-T2a nicht begonnen.

## SD-T2a — Kanonischer Planungszustand

**Priorität / Risiko:** P0 / HIGH.

**Ziel:** Konsistente globale Inputs aus freier Supply, freiem Need und Eligibility.

**Scope:** Batch-Projektion über aktive tradefähige Alben; gültige Incoming-Zusagen beider Teilnehmer vom Planbedarf ausschließen, Transit berücksichtigen; V1-Bindungsadapter zunächst gegen den T1-Datenvertrag und Fixtures. Read-only Inputs dürfen keine Expiry-Schreiboperation auslösen; wirksame Fristen und Freigabepfad mit T5b abstimmen.

**Explicit Non-Scope:** Keine neue Availability-Formel, keine physischen Buchungen, keine Optimierung oder alte globale Partnerlisten-Reparatur nebenbei.

**Reuse:** InventoryReadService, gemeinsame Availability, AlbumPrivacyService, CommunityService, Account-/ProfilePrivacy-Gates.

**Likely Files / Areas:** inventory.py; inventory_availability.py; trade_reservations.py; trade_shipping.py; trade_receipt.py; Community-/Privacy-Services.

**DB / Migration:** **Keine DB-Änderung erwartet** zusätzlich zum T1-Modell; Projektion vorhandener und dort geplanter Bindungen.

**Required Tests:** S08–S11, S19 Shared Availability, S27, S29, CB006, S35; neu: promised Need vor/nach Versand, nach Release und Receipt, Mischbetrieb Legacy/V1, konsistenter Snapshot bei konkurrierender Änderung.

**Acceptance Criteria:** physical5/eigen1/reserved1 ergibt freie3; fehlend plus gültige Zusage ergibt Need0; shipped ohne Receipt bleibt Need0 und physical0. Alte unreservierte offene Anfrage erzeugt keine fiktive Zusage. Blockierte Partner fehlen, privates Album mit erlaubtem Pool bleibt matchbar; keine Reservation/Buchung beim Lesen.

**Risks:** Doppelte Subtraktion, Transit irrtümlich als Besitz, inkonsistente Mehrfachreads, N+1-Lesevolumen.

**Depends On:** SD-T1; Persistenzintegration mit SD-T5a/b später verifizieren, ohne zirkuläre Implementierungsabhängigkeit.

### SD-T2a Implementierungsnotiz — 2026-09-10

[SmartDealPlanningService.build(user_id)](../App/services/smartdeal_planning.py) liefert einen eingefrorenen globalen `PlanningState`: physisch `missing`, freie `needs`, `outgoing_supply`, `incoming_committed_needs`, `eligible_partners`, `album_context` und `reservation_context`. Identität je Stück ist Album-/Sticker-Code plus persistente user_album_id; Partner numerisch ASC, Alben/Codes kanonisch ASC. Keine generierten Anzeigezeiten oder Rangfelder. Zeitabhängige Bindungsgültigkeit verwendet eine einmal pro Aufbau erfasste, injizierbare Uhr; gleicher Zustand und gleicher Friststatus ergeben dasselbe Ergebnis.

KEEP-Reuse: `LegacyAvailabilityCalculator.from_quantity` ist weiterhin die einzige Mengenformel; physische Inventoryzeilen und aktive Reservations werden gebündelt gelesen. `AlbumPrivacyService.trade_pool_user_ids_by_album` und `CommunityService.interactable_user_ids` liefern die bestehenden Account-/Pool-/Block-Gates; `all_codes` liefert den Katalog, SD-T1 `request_contract_type` die Vertragsart. Allgemeine Profil-/Albumprivacy ist gemäß AC03 kein pauschales Tradeverbot: private Sammler mit expliziter Poolfreigabe bleiben tradefähig. Ausgeschlossen sind Self, blockierte/inaktive Partner und Alben ohne Poolfreigabe; keine fremden Profil-/Inventorydaten im Ergebnis. Aktive relevante Alben entsprechen den vorhandenen Mitgliedschaften mit Katalog und Tradepool; kein neues Archiv-/Aktivitätsmodell.

Incoming wird aus den existierenden Lifecycle-Positionen, Reservations, Versand-/Empfangsflags und realen Teil-/Restmengen gelesen. Gültige Zusagen sperren den binären Need auch nach Freigabe der Geberreservation beim Versand; Receipt ist allein physischer Besitz. Legacy nutzt tatsächliche Bindungen und erhält keine neue Frist. Für künftige V1-Daten existiert ausschließlich ein Leseadapter: offene Anfrage plus offener Lifecycle, persistenter Bindungszeitpunkt und vollständige beidseitige Positionsreservations. Fehlende/inkonsistente V1-Bindungsgrundlagen scheitern geschlossen; alte JSON-Pakete erzeugen keine erfundene Reservation. Abgelaufene/terminale unversandte V1-Bindungen sind im Plan unwirksam, ohne Status oder Reservation zu schreiben. Der spätere T5b-Release bleibt notwendig. Keine V1-Anfrageerzeugung oder Reservationssemantik implementiert.

**Keine neue Persistenz/Migration.** Reader setzt V21 voraus; kanonische lokale App-DB bleibt V20. Ein eigener Read-Transaction-Snapshot verhindert Mischstände; bestehende Aufrufertransaktionen werden weder committed noch zurückgerollt. 17 SQL-/Transaktionsanweisungen bei eigenem Snapshot; Queryzahl unverändert bei bis20.000 synthetischen Katalogpositionen bzw.100 zusätzlichen Partnern. Kein per-Sticker-/Partner-N+1, kein allgemeiner R4-Performance-Nachweis behauptet.

**Validierung:**29 neue Tests bestanden; fokussierte Regression **303/303**, kanonische Release-Suite **914/914**,0 Failures/Errors/Skips. Legacy-/SD-T1-Tests unverändert. Testexport `/private/tmp/sammlr-sdt2a-candidate`, Logs `/private/tmp/sdt2a-focused-final.log`, `/private/tmp/sdt2a-regression-final.log`, `/private/tmp/sdt2a-full-final.log`. Release-Allowlist lediglich um neuen Service und Tests ergänzt. App-DB SHA-256 vor/nach `265de4e7cd438a8c9f2bb6673c7a020570605eed8c326e98ab4c378d2fa6d522`; Integrity `ok`, FK0. Keine UI/Route, kein Pairwise/Ranking/Optimierer/GO, keine neue Reservation, kein T2b, kein git add/Commit/Push/Deploy.

## SD-T2b — Globale Pairwise Opportunities

**Priorität / Risiko:** P0 / MEDIUM.

**Ziel:** Für A/B vollständige gerichtete Mengen und maximales 1:1-Paarvolumen über Alben bestimmen.

**Scope:** AC03/04; pro Identität min(freie Gebermenge, Empfängerneed), anschließend Summenminimum beider Richtungen. Kandidatenpositionen und Alternativen behalten, nicht nur ein abgeschnittenes Maximalpaket.

**Explicit Non-Scope:** Keine globale Auswahl, keine Reservierung, keine Ranggewichtung durch Coverage/Rating/Album.

**Reuse:** ExecutableTradeMatchService und TradeCoverageService als Eligibility-/Projektionsbausteine; deren albumbezogene Code-Sets nicht unverändert als Mengenmodell übernehmen.

**Likely Files / Areas:** executable_trade_matches.py; trade_coverage.py; T2a-Projektionsadapter.

**DB / Migration:** **Keine DB-Änderung erwartet**; reine Berechnung.

**Required Tests:** S20 Market Coverage, CB011, S27/S29; neue Gegenrichtungs-, Mengen-, Albumidentitäts- und Need-Cap-Fälle.

**Acceptance Criteria:** Derselbe Code in zwei Alben bleibt verschieden; Geberkopien3 liefern einem konkreten Empfänger maximal1 derselben Identität. Ungleiche gerichtete Kapazitäten20/12 ergeben Paarmaximum12. Fehlende Gegenrichtung erzeugt kein ausführbares Paar; Albumherkunft begrenzt das Paar nicht.

**Risks:** Code-Sets verlieren Mengen/Albumidentität; frühe Positionswahl verhindert später das globale Optimum.

**Depends On:** SD-T2a.

### SD-T2b Implementierungsnotiz — 2026-09-11

[SmartDealPairwiseService](../App/services/smartdeal_pairwise.py) liefert immutable `PairwiseOpportunity`-Tupel in Partner-ID-ASC-Reihenfolge. Vollständige Incoming-/Outgoing-Kandidaten tragen Album-ID, kanonischen Sticker-Code, Geber-/Empfänger-user_album_id, freie Gebermenge (`available_quantity`) und durch den Empfängerneed begrenzte Kandidatenmenge (`quantity`). Bei Supply3 und Need1 gilt quantity1; keine Mehrfachalbum-Semantik. Maximum je Paar ist exakt `min(sum(outgoing.quantity), sum(incoming.quantity))`. Beide Richtungen müssen positiv sein; 1↔1 bleibt erlaubt. Kandidaten werden nicht auf das Minimum gekürzt. `involved_albums` vereint die tatsächlich beteiligten Alben, ohne Partneraufspaltung.

**Minimal additive T2a-Erweiterung:** `SmartDealPlanningService.build_pairwise_inputs()` liefert `PairwisePlanningInputs(subject, partners)` mit `PartnerPlanningInventory` für bereits eligible Partner und deren freigegebene gemeinsame Alben. T2a lieferte zuvor nur eigene Supply/Needs. Mengen- und Bindungsprojektion werden jetzt als gemeinsame reine Hilfsfunktionen von Einzel- und Batch-Leseweg verwendet; bestehendes `build()` und sämtliche T2a-/Legacy-Regeln bleiben erhalten. Ein gemeinsamer Snapshot und eine Uhr gelten für alle Teilnehmer. Vier zusätzliche Batch-Reads laden Mitgliedschaften, Inventory, Reservations und Bindungspositionen; keine Einzelabfragen je Partner. Keine zweite Eligibility-/Availability-Logik.

Repräsentative Nachweise: 23 outgoing /28 incoming über fünf beteiligte Alben ergeben **eine** Opportunity mit Maximum23 und allen28 Incoming-Kandidaten. Zwei Partner dürfen denselben knappen Candidate unabhängig enthalten; im Skalierungsfixture entstehen101 Opportunities ohne Top-Limit. Höchstens21 SQL-/Transaktionsanweisungen beim Laden, auch mit100 zusätzlichen Partnern; `from_planning_inputs()` selbst benötigt **0 SQL**. Keine globale Allokation, kein Ranking, keine Versandregel, keine Requests/Reservations, keine neue Persistenz/Migration.

**Validierung:**22 neue T2b-Tests und29 unveränderte T2a-Tests bestanden; fokussierte Schutzregression **325/325**, vollständige kanonische Release-Suite **936/936**,0 Failures/Errors/Skips. Isolierter Allowlist-Export mit2219 Dateien unter `/private/tmp/sammlr-sdt2b-candidate`; Logs `/private/tmp/sdt2b-focused.log`, `/private/tmp/sdt2b-regression.log`, `/private/tmp/sdt2b-full.log`. App-DB SHA-256 vor/nach `265de4e7cd438a8c9f2bb6673c7a020570605eed8c326e98ab4c378d2fa6d522`, Integrity `ok`, FK0. Release-Allowlist um neuen Pairwise-Service und Tests ergänzt; keine vorhandenen Tests oder Migrationen geändert. Kein T3a, GO, UI-/Routenumbau, Staging/Commit/Push/Deploy.

## SD-T3a — Exakte Optimierungsmethode und Referenznachweis

**Priorität / Risiko:** P0 / HIGH.

**Ziel:** Eine nachweisbar vertragskonforme Methode mit begründetem Aufwand auswählen.

**Scope:** Auf den realen Kandidatenstrukturen einen kleinen erschöpfenden Referenzraum und reproduzierbare Konfliktfixtures planen/erstellen; Methoden gegen AC05–AC15 vergleichen. Empfehlung nach IST-Analyse: exakte Suche mit sicheren Schranken als erste zu prüfende Methode, nicht heutiges Greedy erweitern und Optimalität behaupten.

**Explicit Non-Scope:** Kein produktiver Solver, kein stilles Kandidatenlimit, kein Timeout-Ergebnis als angeblich optimales Top-Ergebnis.

**Reuse:** T2b-Inputs und AC30-Cases, bestehende S21-Konfliktfixtures.

**Likely Files / Areas:** top_match_optimization.py als Vergleichsbasis; zukünftige isolierte Solver-/Referenztests.

**DB / Migration:** **Keine DB-Änderung erwartet**.

**Required Tests:** S21/CB011 unverändert; neue vollständige kleine Allokationsräume, Comparator-Transitivität, Permutationsstabilität, beide exakten +2-Fälle.

**Acceptance Criteria:** Jede vorgeschlagene Methode bildet max5/min5, gemeinsame Need-/Supply-Kapazität, Partnerbalance und alle Tie-Breaks ab; keine gültige bessere Allokation wird durch Vorabschneiden entfernt. Auswahlentscheidung dokumentiert Laufzeit-/Optimalitätsnachweis und Abbruchverhalten; Heuristik ohne Optimalitätsnachweis scheidet als alleinige Lösung aus.

**Risks:** Kombinatorischer Aufwand; numerische Gewichtung kann lexikographische Prioritäten verfälschen.

**Depends On:** SD-T2b.

Methodenvergleich: Vollständige Enumeration ist eine verlässliche kleine Referenz, skaliert aber nicht automatisch. Branch-and-Bound kann denselben exakten Raum mit beweisbar sicheren Schranken kürzen; Wirksamkeit ist zu messen. Integer-Optimierung kann Aktivierungsvariablen, Kapazitäten und lexikographische Ziele ausdrücken, fügt aber Solver-/Betriebsabhängigkeiten hinzu. Einfaches Matching/Flow darf erst nach einem Nachweis verwendet werden, dass insbesondere Partneraktivierung, Mindestgröße und Sendungsziel exakt erhalten bleiben. Deterministische Heuristik ist höchstens Suchhilfe; Determinismus ersetzt Optimalität nicht. Keine Bibliothek oder neue Abhängigkeit hier festgelegt.

### SD-T3a Researchnotiz — 2026-09-11

Exakte Methode nachgewiesen: vollständige globale Partnerteilmengensuche bis fünf mit sicheren Schranken, ganzzahlige Zirkulation für Ressourcen/1:1/Mindestgröße sowie vollständige lexikographische Nachoptimierung E/G/D/J/C. Greedy durch konkreten Fall6/1 gegen10/2 widerlegt. Standardbibliothek genügt; keine neue Dependency empfohlen. Unabhängiges erschöpfendes Oracle und separater Flow-Prototyp ausschließlich unter `tests/research`, keine produktive Verdrahtung. [Formales Modell, Optimalitätsargument und Machbarkeitsgrenzen](SMARTDEAL_T3A_OPTIMIZATION_PROOF.md).

27 neue Tests: alle17 Pflichtklassen, sechs Versandschwellen,240 feste Differential-Seeds und Determinismus bestanden. T1/T2a/T2b unverändert69/69; zusammen96/96, relevante Regression371/371, Full Release963/963 ohne Failures/Errors/Skips. Drei synthetische Messreihen:150↔150 etwa18ms,20 disjunkte Partner etwa56ms, zehn überlappende Partner jedoch2,33–2,39s. Keine allgemeine Beta-/R4-Latenzfreigabe; T3b muss sichere Such-/Flow-Optimierungen und deklarierte größere Konfliktlasten prüfen. Keine Kandidatenabschneidung oder approximativen Timeout-Ergebnisse erlaubt. Runtime, Migrationen, App-DB und Produktverträge unverändert; Integrity ok, FK0, DB-Hash vor/nach identisch. Kein T3b, UI/Route/GO/Request/Reservation, Staging/Commit/Push/Deploy.

## SD-T3b — Globaler deterministischer Optimierer

**Priorität / Risiko:** P0 / HIGH.

**Ziel:** Gemeinsamen optimalen Top-Plan als reine Domainfunktion berechnen.

**Scope:** T3a-Methode, globale Allokation, max5/min5, ein Deal pro Partner, E/G/D/J/C und kanonische Ausgabe. Leeres Ergebnis und große gültige Pakete unterstützen.

**Explicit Non-Scope:** Keine Requests, UI, Albumgewichte, künstliche Maximalgröße oder globale Vorreservierung.

**Reuse:** T2a/b und T3a-Referenz; keine Änderung des alten S21-/CB011-Vertrags.

**Likely Files / Areas:** Neuer V1-Optimierungsservice neben top_match_optimization.py; isolierte Contracttests.

**DB / Migration:** **Keine DB-Änderung erwartet**.

**Required Tests:** AC30 Cases1–20 soweit reine Planung, AC33 I01–I17/I27–I29; kleiner Oracle-Abgleich und Eingabereihenfolge-Permutationen; S21/CB011 bleiben grün.

**Acceptance Criteria:** 26/4 schlägt20/1, 41/5 schlägt35/2; 20/1 schlägt23/4. Case2 ergibt unter seinen Annahmen A20+B5, nicht A19+B6. Kein Need oder Supply wird doppelt verplant; 4↔4 nicht im Top-Plan, 150↔150 möglich. Wiederholter identischer Input liefert denselben kanonischen Plan.

**Risks:** Suchzeit, falsche Pruning-Regeln, lexikographischer Tie-Break vor Ressourcenoptimierung.

**Depends On:** SD-T3a.

### SD-T3b Implementierungsnotiz — 2026-09-11

**Umgesetzt; Acceptance YELLOW: correctness-green / performance-yellow.** Interner read-only `SmartDealOptimizer.optimize(PlanningState, PairwiseOpportunities)` mit eingefrorenem Plan/Objective/Diagnostics. Exakte T3a-Teilmengensuche, ganzzahliger Flow und vollständiges E/G/D/J/C; sichere Schranken, Memoization identischer Feasibility-Zustände und wiederverwendete Topologie. Kein produktiver Route-Cutover, keine neue Dependency/Persistenz. [Architektur, Pruning-Beweise und Abschlussbericht](SMARTDEAL_T3B_OPTIMIZER_REPORT.md).

28 neue Tests grün;500/500 feste Oracle-Seeds einschließlich unveränderter T3a-Seeds0–239,17/17 Pflichtklassen, sechs Versandgrenzen und zusätzliche echte globale Schwellenfälle. Vorstufen unverändert96/96; Schutzregression473/473; Full Release991/991 ohne Failures/Errors/Skips. Drei Messreihen: dichter T3a-Zehnpartnerfall48–50ms,20 disjunkte Partner86ms,150↔150 etwa1ms,25er-Stress453–456ms; gemischter20-Partner-Fall jedoch2,15–2,16s. Daher Performance-Gate nicht ausreichend: korrekten Zustand erhalten, **STOP zur PO-/Architekturentscheidung**, keine Heuristik oder Gate-Lockerung. SD-T6a nicht begonnen. Bestehende Runtime/Vorstufen/Legacy, Migrationen und App-DB unverändert; Integrity ok, FK0, SHA-256 vor/nach identisch. Kein Identity/GO/Request/Reservation/Mutual GO/UI/Route, git add/Commit/Push/Deploy.

### SD-T3b Acceptance Fix 3b.1 — 2026-09-11

**Acceptance jetzt GREEN.** Sichere vollständige Branch-Reihenfolge beseitigt die verspätete Schrankenwirkung in Fall E: 85,8–87,3 ms statt 2.152–2.159 ms, 13 Wiederholungen insgesamt. Oracle 500/500, A–Q 17/17, Runtime 29/29, Schutzregression 474/474, Full Release 992/992. Keine Produktregel-/Migrations-/DB-Änderung; kein SD-T6a. [Messdaten, Beweis und Abschlussbericht](SMARTDEAL_T3B1_PERFORMANCE_INVESTIGATION.md). Die vorstehende YELLOW-Notiz dokumentiert den historischen Stand vor diesem Fix.

## SD-T6a — Kanonische Opportunity-Identität

**Priorität / Risiko:** P0 / HIGH.

**Ziel:** Spiegelgleiche Pakete unabhängig von Ansicht und Gesamtplan sicher erkennen.

**Scope:** V1-Version, numerisch geordnetes Nutzerpaar und vollständige gerichtete Multi-Album-Positionen kanonisieren; Opportunity-Identität von Vorgangs-ID trennen; durable Konkurrenzsicherung für aktive identische Vorgänge entwerfen.

**Explicit Non-Scope:** Kein Mutual-Accept vor T6b; kein Ersatz der Altrequest-Retry-Semantik.

**Reuse:** Kanonische Nutzer-/Album-/Codeidentitäten, vorhandene Positionsaggregation; heutiger Gesamtplanhash nur als IST-Gegenbeispiel.

**Likely Files / Areas:** top_match_optimization.py _result_id; smart_trade_requests.py; V1-Domain-/Persistenzadapter aus T1.

**DB / Migration:** **Möglicherweise erforderlich** für durable aktive Identität/Unique-Schutz; mit T1 bündeln, wenn dessen Modell dies bereits sicher trägt. Prozesslokale Dedupe genügt nicht.

**Required Tests:** CB011 Legacy-Retry bleibt erhalten; neu Spiegelung, Reihenfolge, gleiche Codes in anderen Alben, simulierte Hashkollision, terminaler früherer identischer Vertrag.

**Acceptance Criteria:** A→B und gespiegeltes B→A vergleichen gleich; geänderte Position/Menge/Teilnehmer nicht. Hashgleichheit allein führt nie zum Merge. Beendeter Altvertrag sperrt spätere neue identische Opportunity nicht dauerhaft.

**Risks:** Falsches Zusammenführen, überbreite Unique-Regel, Richtungstausch.

**Depends On:** SD-T1, SD-T2b; vor SD-T4/SD-T5a abschließen.

### SD-T6a Implementierungsnotiz — 2026-09-11

**ACCEPTANCE GREEN.** Reine `SmartDealIdentityService`-Domainfunktion mit additivem T3b-Adapter: numerisches Nutzerpaar, vollständige zugeordnete Multi-Album-Positionen, V1-Vertragsart, kanonisches UTF-8-JSON und voller SHA-256. Fachliche Gleichheit vergleicht vollständigen Inhalt auch bei Hashkollision. 25/25 neue Tests, Schutzregression 499/499, Full Release 1.017/1.017; gesperrte Vorstufen unverändert. 150↔150-Identity etwa 0,095 ms. Keine DB/Persistenz/Migration, keine dauerhafte Deduplizierung oder GO-Logik im ausdrücklich begrenzten Auftrag; T4/T5a/T6b nicht begonnen. [Technischer Bericht und Acceptance](SMARTDEAL_T6A_OPPORTUNITY_IDENTITY.md).

## SD-T4 — Suggestion-Payload und GO-Revalidierung

**Priorität / Risiko:** P0 / HIGH.

**Ziel:** Konkretes angezeigtes Paket unabhängig von seinem späteren Rang prüfen.

**Scope:** Unveränderliche serverseitig prüfbare Suggestion-Repräsentation und transaktionsfähige Validierungsfunktion; Auth, Eligibility, vollständige Positionen, freie Supply/Need, 1:1, Mindestgröße und Quote. Rang und Gesamtplanhash sind keine harte GO-Bedingung.

**Explicit Non-Scope:** Noch keine öffentlich aktivierte GO-Route; keine Reservation durch Anzeige, kein Paket-Recompute als Ersatz.

**Reuse:** SmartTradeRequestService.recheck_codes als Prüflandkarte, kanonische T2a-Inputs und T6a-Identität; alte Prüfung nicht ungeändert übernehmen.

**Likely Files / Areas:** smart_trade_requests.py; webapp.py bestehender Smart-Request-Handler als späterer Adapter; neuer V1-Validator.

**DB / Migration:** **Keine DB-Änderung erwartet** zusätzlich zu T1/T6a; eine persistierte Suggestion ist nicht automatisch nötig.

**Required Tests:** S22/CB011; neu Rang4→6, manipulierte Payload, fehlender Need, neue Fremdbindung, Block/Pooländerung; Validator später innerhalb T5a-Transaktion prüfen.

**Acceptance Criteria:** Rang4→6 mit exaktem gültigem Paket erlaubt GO; eine verlorene notwendige Kopie oder gesperrter Partner lehnt vollständig ab. Kein heimliches Kürzen/Ersetzen und keine Bindung beim Vorschlaglesen. Eigene Vertragsbindungen werden im Mutual-Zweig korrekt zugeordnet.

**Risks:** Clientvertrauen, Time-of-check/time-of-use, Ablehnung eigener gültiger Incoming-Zusage.

**Depends On:** SD-T3b, SD-T6a.

### SD-T4 Implementierungsnotiz — 2026-09-11

**ACCEPTANCE GREEN.** Immutable `SmartDealSuggestion` aus finalem T3b/T6a-Paket; `SmartDealSuggestionValidator` prüft exakten Inhalt und vollständige Identity gegen auf jedem Aufruf frisch geladene T2a-Inputs. VALID/STALE/INVALID_PAYLOAD, kein Re-Ranking oder Ersatzpaket. 42/42 neue Tests, Schutzregression 541/541, Full Release 1.059/1.059; gesperrte Vorstufen unverändert. 5/25/150 je Seite etwa 0,11/0,23/0,98 ms, konstant 21 SQL-/Transaktionsanweisungen. VALID bindet nichts und sichert keinen Anfrageplatz; atomare Anlage/Quote und eigene Mutual-Bindungen bleiben T5/T6b. Keine Persistenz/Migration oder sichtbare Route. [Vertrag, Race-Grenze und Nachweise](SMARTDEAL_T4_SUGGESTION_REVALIDATION.md). T5a/T5b/T6b nicht begonnen.

## SD-T5a — Atomare V1-Anlage und beidseitige Reservation

**Priorität / Risiko:** P0 / HIGH.

**Ziel:** Intern einen V1-Request samt beiden Mengenbindungen atomar erzeugen.

**Scope:** Prüfung und Schreiben in derselben Transaktion; max3 offene ausgehende V1, Freeze, positionsbasierte beidseitige Bindung, atomare Domain-/Notification-Fakten. Lifecycle offen halten; Annahme nicht vortäuschen. Nur interner Einstieg bis T5b/T6b und Lifecycle-Anbindung geprüft sind.

**Explicit Non-Scope:** Keine physischen Mengenänderungen, keine globale Änderung des alten accept, keine neue öffentliche Route.

**Reuse:** BEGIN IMMEDIATE-/Rollback-Muster, Positions-/Reservationsschema nach T1, TypedNotificationService mit stabiler Quelle.

**Likely Files / Areas:** smart_trade_requests.py; trade_reservations.py; typed_notifications.py; T1-/T6a-Persistenz.

**DB / Migration:** **Möglicherweise erforderlich**; ausschließlich die in T1/T6a belegte Lücke schließen. Bestehende Reservation-FKs und accepted-Fabrik verhindern blindes Vorziehen des alten accept.

**Required Tests:** S14, S22, CB008, CB011; neu Bilateralität, dritte/vierte Anfrage, Mischquote, injizierter Fehler zwischen Positionen, parallele GO mit letzter Kopie, parallele GO am dritten Slot.

**Acceptance Criteria:** Beide Gebermengen reserviert, physische quantity unverändert; dritte erlaubt, vierte abgewiesen; beliebige Legacy-/manuelle offene Requests verbrauchen keinen V1-Slot, reale Bindungen aber Supply. Fehler hinterlässt weder Request noch Teilbindung/Notification. Neue Anfrage erscheint nicht als accepted oder erfolgreich abgeschlossen.

**Risks:** Writer-Contention, Callback-Commits außerhalb Transaktion, doppelte Bindung, orphan positions.

**Depends On:** SD-T1, SD-T6a, SD-T4.

**Implementierungsnachweis SD-T5a (2026-09-11):** Interner atomarer V1-Writer einschließlich beidseitiger Supply-/Need-Bindung; keine Migration oder öffentliche Aktivierung. Neue Tests 40/40, Schutzregression 581/581, Full Release 1099/1099 GREEN. Details: [SD-T5a-Bericht](SMARTDEAL_T5A_ATOMIC_BINDING.md). SD-T5b/SD-T6b/SD-T7a nicht begonnen.

## SD-T5b — Fristen, Rückzug und vollständige Freigaben

**Priorität / Risiko:** P0 / HIGH.

**Ziel:** Offene V1-Requests ohne Leaks beenden; Mengen, Need und Quote zuverlässig wieder nutzbar machen.

**Scope:** Decline/withdraw/24h expiry und gemeinsamer Release-Baustein für T7b; Eligibility-Ereignisse einschließlich bestehender Block-Cancel-Pfade anbinden. Ablaufmechanismus explizit bestimmen; wirksame Reads/GO dürfen nicht auf unbegrenzt liegengebliebene Zeilen vertrauen.

**Explicit Non-Scope:** Keine Änderung von Legacy48h, accepted-Trades bei Block nicht pauschal canceln; keine reale Inventorybuchung oder Nachversand-Autobeendigung.

**Reuse:** TradeReservationService.release, bestehende Status-/Notification- und Community-Transaktionen.

**Likely Files / Areas:** smart_trade_requests.py; trade_reservations.py; CommunityService; typed_notifications.py; später zuständige Command-Adapter.

**DB / Migration:** **Keine DB-Änderung erwartet** über T1-Modell hinaus; 24h allein benötigt keine Migration. Falls ein benötigter Zustand nicht abbildbar ist, gezielte T1-Nachprüfung statt globalem Statusumbau.

**Required Tests:** S22, S29, S14, CB008/009; neu t=24h, wiederholter Release, accept/expiry-Race, Block mit offenen V1-Bindungen, unberechtigter Rückzug.

**Acceptance Criteria:** Bei exakt24h kein accept; beide Reservations frei, weiter fehlender Need frei und Slot wieder verfügbar. Decline/withdraw idempotent; fremder Akteur kann nicht withdrawen. Nach rechtzeitigem accept darf nachlaufende Expiry nichts freigeben; alte Requests bleiben unverändert.

**Risks:** Halbfreigabe, veraltete Counts, ungewollte GET-Mutationen, Notification-Duplikate.

**Depends On:** SD-T5a.

**Implementierungsnachweis SD-T5b (2026-09-12):** Interne atomare Decline-/Withdraw-/Expiry-Freigabe und zentraler expliziter Sweep; PO-Präzisierung: absolute 24h ausschließlich ab `binding_created_at`. Beidseitige Supply-/Need-Freigabe, vorhandene Decline-Notification und Block-Transaktion integriert. Neue Tests 60/60, Schutzregression 641/641, Full Release 1159/1159 GREEN; keine Migration oder öffentliche Aktivierung. [Bericht und korrigierter Arbeitsauftrag](SMARTDEAL_T5B_RELEASE_EXPIRY.md). SD-T6b/SD-T7a/SD-T7b nicht begonnen.

## SD-T6b — Accept, Mutual GO und konkurrierende Requests

**Priorität / Risiko:** P0 / HIGH.

**Ziel:** Annahme und spiegelgleiches GO führen zu genau einem angenommenen Vertrag.

**Scope:** Unter derselben Schreibisolation Identität, Frist, Beteiligtenrecht, Eligibility und eigene Bindungen prüfen; offenes Gegenpaket annehmen statt neu anlegen. Wiederholung derselben Person bleibt Retry. Annahme übernimmt vorhandene Bindungen und persistiert den Eintritt in die accepted-Stufe eindeutig und unveränderlich nach AC26; Retry setzt diesen Zeitpunkt nicht neu.

**Explicit Non-Scope:** Keine automatische Zustimmung durch denselben Akteur; keine neue Reservation bei accept; kein allgemeines Request-Merging.

**Reuse:** T6a-Identität, T4-Validator, T5-Transaktionen; bestehende akzeptierte Lifecycle-Positionsverträge.

**Likely Files / Areas:** V1-Requestservice; trade_reservations.py accept-Adapter; Account-/Community-Gates.

**DB / Migration:** **Keine DB-Änderung erwartet** nach T1/T6a; Konkurrenzsicherung muss dort dauerhaft gewährleistet sein.

**Required Tests:** S14/S22 und CB011 Legacy-Retry; neue barrier-synchronisierte A/B-GO, Same-actor-Retry, accept/expiry, Block/accept und Quote voll bei eingehender Annahme.

**Acceptance Criteria:** Gültiges nahezu gleichzeitiges A/B-GO ergibt genau einen accepted Vorgang mit einer Bindung je Position. Gleicher Akteur zweimal GO bleibt ein offener Request; kein Selbst-Accept. Volle eigene outgoing Quote verhindert gültige eingehende Annahme nicht. Eigene gebundene Need/Supply löst keine falsche Kollision aus; abgelaufener Vertrag wird nicht angenommen.

**Risks:** Cross Requests, doppelte Reservierung, fehlende Eligibility-Prüfung innerhalb der alten accept-Transaktion.

**Depends On:** SD-T5b, SD-T6a; akzeptierter Zustand gegen SD-T7a-Buchungsvertrag abgleichen.

**Implementierungsnachweis SD-T6b (2026-09-12):** Interner Accept-/GO-Service mit exaktem T6a-Batch-Lookup, atomarer T5a-Komposition, Mutual GO, stabilem accepted_at und T5b-Expiry ab binding_created_at+24h. A/A bleibt pending; A/B übernimmt dieselbe Instanz und beide Bindungen. Neue Tests 63/63, Schutzregression 704/704, Full Release 1222/1222 GREEN. Keine Migration oder öffentliche Aktivierung. [Technischer Bericht](SMARTDEAL_T6B_ACCEPT_MUTUAL_GO.md). SD-T7a/SD-T7b/SD-T8a nicht begonnen.

## SD-T7a — Physischer Lifecycle, History und Notifications

**Priorität / Risiko:** P1 / HIGH.

**Ziel:** Angenommene Multi-Album-V1-Verträge über vorhandene Versand-/Empfangsmaschine abschließen.

**Scope:** Request-/Positionsadapter, shipped/received/partial-receipt, vorhandene Problemzustände, Erfolgsprojektion und sichere Detail-/Notification-Zuordnung. Alle verbleibenden Single-album-Callbacks überprüfen.

**Explicit Non-Scope:** Keine zweite Buchungsmaschine, kein History-Rewrite, kein Kontakt-UI oder Bestandsverlust-Auswahlentscheid.

**Reuse:** TradeShippingService, TradeReceiptService, TradeProblemService, HistoricalInventoryWriteService, SuccessfulTradeProjection, TypedNotificationService, Ratings.

**Likely Files / Areas:** trade_shipping.py; trade_receipt.py; trade_problems.py; history_cutover.py; successful_trade_projection.py; typed_notifications.py; webapp.py Legacy-Completion-Adapter.

**DB / Migration:** **Keine DB-Änderung erwartet** zusätzlich zu T1; trade_positions trägt bereits Album und Menge. Echte neue Lifecycle-Fakten nur nach belegter Modelllücke ergänzen.

**Required Tests:** S15/S16/S17/S18_2/S19 Receipt UX/S20 Completion, CB002/CB010, S28, CB008/009, R3; neu Multi-Album-End-to-end und Callback-Rollback.

**Acceptance Criteria:** Ship bucht nur eigene ausgehende Positionen genau einmal aus; Receipt nur tatsächlich bestätigten Eingang einmal ein. Zweimaliger Request bucht nicht doppelt; Transit kein Besitz. Erfolgreicher Vertrag zählt global einmal, Problemabschluss nicht fälschlich als Erfolg. Notificationziele sind nur für Berechtigte zugänglich, keine doppelten Events.

**Risks:** Legacy-Confirm als zweiter Buchungspfad, Single-album-Verlust, History-/Rating-/Account-Regression.

**Depends On:** SD-T6b; seine Abschluss-/Adapterverträge bereits vor Core-Gate prüfen.

## SD-T7b — Bestandskorrektur und Unfulfillable nach Versandphase

**Priorität / Risiko:** P1 / HIGH.

**Ziel:** Reale Bestandskorrekturen ermöglichen und betroffene V1-Verträge phasengerecht behandeln.

**Scope:** V1-spezifische Guard-/Mutationseinbindung mit T5b-Release; vor jedem Versand ganz beenden, ab erstem Versand sichtbarer Problem-/Action-required-Pfad. Mehrfachunterdeckung nach AC26 auflösen: accepted vor open, ältere Bindung innerhalb derselben Stufe zuerst schützen, stabile ID ASC bei Zeitgleichheit. Jüngere/schwächere betroffene Gesamtverträge vollständig freigeben und Deckung nach jedem Release erneut prüfen; versandte Trades nie automatisch auswählen.

**Explicit Non-Scope:** Kein pauschales Entfernen des Legacy-Guards, kein Reparatureditor, keine Payload- oder fiktive Inventory-Rückabwicklung.

**Reuse:** InventoryWriteService/InventoryGuard, HistoricalInventoryWriteService, bestehender Problemflow und Typed Notifications. Aktueller Receipt-Problemreport darf nicht durch eine erfundene Receipt-Buchung für einen unversendbaren Rest missbraucht werden.

**Likely Files / Areas:** inventory_write.py; inventory_guard.py; history_cutover.py; trade_problems.py; trade_reservations.py; typed_notifications.py.

**DB / Migration:** **Möglicherweise erforderlich**, falls ein Action-required-Fakt ohne bisherigen Receipt-Report nicht darstellbar ist; zunächst vorhandenes Event-/Problemmodell prüfen. Kein neues Reparaturmodell.

**Required Tests:** S12/S14 Legacy-Guard, S17/S18_2, CB002/CB008; neue Bestandsverlustfälle vor Versand, nach einseitigem Versand, gleichzeitigem ship/Korrektur und Mehrfachunterdeckung nach AC26: accepted > open, older binding > newer binding, stable ID tie-break, no partial shrinking, shipped => problem flow und keine Verdrängung bestehender gültiger Reservations durch neue SmartDeals; zusätzlich Annahmezeit versus GO-Zeit, Retry-Zeitstabilität und mehrere Ressourcen nach vollständigem Release (Cases21–27, I31–I36).

**Acceptance Criteria:** Ein einziger betroffener unversandter V1-Deal endet vollständig, alle Bindungen frei, Partner informiert, Payload erhalten. Nach einseitigem Versand bleibt physische Wahrheit erhalten und Problem sichtbar; keine gewöhnliche automatische Cancel-Freigabe. Legacy bleibt nach altem Vertrag geschützt. Fatimas ältere offene Bindung bleibt bei ARG17 2→1 bestehen, Johanns jüngere endet ganz; ein neuerer accepted-Vertrag schlägt eine ältere offene Anfrage. Zeitgleichstand schützt kleinere kanonische ID. Kein besserer neuer Plan verdrängt gültige Bindungen; nach erreichter Deckung keine weiteren Verträge beenden.

**Risks:** Reale Korrektur wird weiterhin blockiert, falscher Vertrag endet, Ware im Transit verschwindet aus Projektionen.

**Depends On:** SD-T7a, SD-T5b; technische Zeit-/Identitätspersistenz aus SD-T1/SD-T6b gemäß AC26.

## SD-T8a — Geschützter Versandkontakt

**Priorität / Risiko:** P1 / HIGH.

**Ziel:** Zwei bestätigte Partner können tatsächlich versenden, ohne öffentliche Adressfreigabe.

**Scope:** Tradebezogene Eingabe/Freigabe, optional ausdrücklich gewünschte Speicherung für spätere bestätigte Trades, kontrollierte erneute Partnerfreigabe, berechtigte Leseprojektion. Technischen Datenlebenszyklus einschließlich Änderungen, Widerruf und Problemzugriff konkret zur Prüfung dokumentieren; keine darüber hinausgehende Produktpolitik still festlegen.

**Explicit Non-Scope:** Kein Signup-Pflichtfeld, öffentliches Profilfeld, allgemeine Kontaktliste, Telegram-Zwang oder Chat.

**Reuse:** Beteiligten-/Account-/Privacy-Gates, bestätigter Lifecycle, Auth/CSRF. Bestehende Shippingflags sind keine Adressspeicherung.

**Likely Files / Areas:** Neue eng begrenzte Kontaktpersistenz/-service; Trade-Detail-Adapter; Privacy-/Account-Lifecycle; Datenbankschema.

**DB / Migration:** **Voraussichtlich erforderlich**, weil kein Adress-/Freigabemodell vorhanden ist; getrennt von Algorithmus und minimal auf Versandzweck begrenzen.

**Required Tests:** CB006, S32/S33/S35, R3; neu Drittzugriff, offener/abgelehnter Request, fehlende Freigabe, gespeicherte Adresse bei neuem Partner, Daten in öffentlichen APIs/Logs/Notifications.

**Acceptance Criteria:** Nach beidseitiger Annahme und konkreter Freigabe sieht ausschließlich der berechtigte Partner Versanddaten. Gespeicherte Adresse allein gibt nichts frei. Nichtbeteiligter und noch unbestätigter Partner erhalten keine Daten; Signup ohne Adresse funktioniert. Kontaktweg funktioniert ohne Chat oder Telegram.

**Risks:** Adressleaks, automatische Wiederfreigabe, unklarer Zugriff bei Problemen oder Accountende.

**Depends On:** SD-T1, SD-T7a; konkreter UI-Einbau nach SD-T9.

## SD-T8b — Optionaler minimaler Tradechat

**Priorität / Risiko:** P2 / MEDIUM.

**Ziel:** Optional kurze Nachrichten zwischen genau zwei bestätigten Tradepartnern ermöglichen.

**Scope:** Nur bei separater Auswahl dieses Optionsblocks: tradegebundene Nachrichten und Beteiligtenprüfung, einfacher Verlauf; Datenlebenszyklus passend zum Trade konkretisieren.

**Explicit Non-Scope:** Kein allgemeiner Messenger, keine öffentliche DM-Suche, keine Social-Plattform; kein Ersatz für sichere Adressfreigabe.

**Reuse:** T8a-Berechtigungen, bestätigter Trade, bestehende sichere Benachrichtigungsinfrastruktur nur bei separat benötigtem Trigger.

**Likely Files / Areas:** Enger neuer Nachrichtenservice/-speicher und späterer Trade-Detail-Adapter.

**DB / Migration:** **Voraussichtlich erforderlich, nur wenn Option gewählt**; kein vorhandener Nachrichtenspeicher im untersuchten Tradepfad.

**Required Tests:** S32/S33/CB006; neue Nichtbeteiligten-, Unbestätigten-, HTML-Escaping- und tradeübergreifende Zugriffsfälle.

**Acceptance Criteria:** Bestätigte Beteiligte können Nachricht ausschließlich ihrem Trade zuordnen; Fremde und offene Anfragen können weder lesen noch schreiben. Ohne implementierten Chat bleibt T8a vollständig nutzbar; Chat ist kein Beta-Gate.

**Risks:** Nachrichten-/Adressleaks, ungewollte allgemeine DM-Funktion.

**Depends On:** SD-T8a, SD-T9 und gesonderte Wahl der Produktoption.

## SD-T9 — Vollständiger Route-/IA-Audit und PO-SOLL

**Priorität / Risiko:** P1 / MEDIUM.

**Ziel:** Einen nachgewiesenen IST-Fluss und einen separat prüfbaren SOLL-Fluss besitzen.

**Scope:** Sämtliche betroffenen Routes → Links → Forms → Redirects → Back targets → origin params einschließlich Aliases, Fehler-/Terminalzuständen und Einstieg über Profil/Album/Inbox erfassen. Danach SOLL anhand der bestätigten Domain-/Lifecyclezustände ausarbeiten und PO vorlegen.

**Explicit Non-Scope:** Noch keine Route ändern/umbenennen, keine kosmetische Übernahme historischer Struktur, kein visuelles Design festlegen.

**Reuse:** S07-Origin-Allowlist, canonical Detail und sichere Notificationzielauflösung; Audit-Landkarte als Ausgangspunkt, nicht als fertige SOLL-Architektur.

**Likely Files / Areas:** webapp.py inklusive Inline-HTML/JS; sticker_list.py; notification_history.py; templates; static/style.css.

**DB / Migration:** **Keine DB-Änderung erwartet**; Navigationsvertrag.

**Required Tests:** S07, R2 Journey, UIF005b, S24, CB009; vollständige statische Kantenprüfung und später ausführbare SOLL-Navigationsassertions planen. Dieser Auditblock ändert noch keine Produkttests.

**Acceptance Criteria:** Jede relevante Form hat realen Handler, Redirect und erlaubtes Rückziel; singular/plural Accept-/Cancel-Aliases sind nach tatsächlicher Wirkung klassifiziert. Profil-/Albumeinstiege und Notifications verlieren ihren zulässigen Kontext nicht im SOLL. Kein Sollziel wird ohne PO-Freigabe produktiv; Mobile-Bottom-Overlay-Befund bleibt bis Viewportnachweis offen.

**Risks:** Alias als funktionierendes Command missverstanden, origin-Verlust, offene Redirects, überdeckte Aktionen.

**Depends On:** Core-Gate und klare SD-T7a/b-/SD-T8a-Verträge; Die entschiedene Prioritäts-/Phasenregel AC26 gehört zum SOLL des Bestandsverlustflows.

## SD-T10 — Technische UI-/Design-Integration

**Priorität / Risiko:** P1 / MEDIUM.

**Ziel:** Freigegebene SOLL-UX auf geprüfte Domaincommands und Zustände abbilden.

**Scope:** Top-SmartDeals, Preview/Detail, GO, Pending, Mutual Accept, Active/Next action, Versandkontakt/Versand, Discovery und manueller Composer; Empty/Error/Expired/Unfulfillable-/Problemzustände. Ausführung in getrennten kleinen PRs je freigegebenem Zustandsfluss, mit eigenem Scope und Regressionen; kein einmaliger Tradebereich-Neubau.

**Explicit Non-Scope:** Hier keine Farben, Layouts oder neue Routen vorwegnehmen; kein UI-eigener Algorithmus oder Lifecycle. Ungleiche manuelle Trades bleiben erlaubt; CEOKlaue/Papierliste nicht zum digitalen Composer umdeuten.

**Reuse:** Freigegebene Adapter, Auth/CSRF, Next-action-Projektion und bestehende funktionierende Infrastruktur.

**Likely Files / Areas:** webapp.py Inline-Views/Forms; Templates/JS/CSS nur entsprechend PO-SOLL; manual Composer und Trade-Detail-Adapter.

**DB / Migration:** **Keine DB-Änderung erwartet** durch Gestaltung. Multi-Album-Payloads nutzen Domainmodell; eine neue manuelle Vertragsart nicht versteckt im UI-Block einführen.

**Required Tests:** S07/R2/UIF005b/R3, CB011 manual unequal, Auth/Privacy; neue SOLL-Flow-, Form-Doppelklick-, Fehler- und reale Mobile-Viewport-Prüfungen.

**Acceptance Criteria:** Jede Aktion ruft genau den berechtigten Domainübergang auf; GO zeigt unverändertes Paket, Pending ist nicht Active. Abgelaufene/unerfüllbare Vorgänge bieten keine ungültige Annahme; Problem nach Versand bleibt erreichbar. Mobile-Endaktionen sind bei geprüften Viewports vollständig erreichbar. Freie Discovery, manuell ungleiche Mengen und geschützte Papierfunktion bleiben nutzbar.

**Risks:** Viewlogik umgeht harte Invarianten; Mobile-Overlay; Scope wächst zum Redesign aller Trades.

**Depends On:** SD-T7a/b, SD-T8a, SD-T9 mit PO-SOLL und separater visueller Designentscheidung. SD-T8b optional.

## SD-T11 — Golden Path, Regression und Performance-Gate

**Priorität / Risiko:** P1 / HIGH.

**Ziel:** SmartDeal V1 über echte HTTP-/Nutzerflüsse und konkurrierende Vorgänge nachweisen.

**Scope:** Mindestens zwei tatsächlich registrierte Testaccounts in isoliertem Testsystem mit synthetischen Inventaren: Suggestion → GO → beide Reservations → Gegenpartei → Accept bzw. Mutual GO → Kontakt → sent → received → Inventory → completed/history. Separate Läufe für normale Annahme und Mutual GO. Mehrparteienfixtures für Konflikte/Quote ergänzen.

**Explicit Non-Scope:** Keine persönlichen Produktionsaccounts/-daten, kein automatisches Deploy/RC0, kein Ersatz von Messung durch historischen R4-Nachweis.

**Reuse:** R3 Golden Path, bestehende Contracttests und R4-/B1.2-Testumgebung.

**Likely Files / Areas:** tests/test_r3_two_user_golden_path.py; tests/test_r4_v20_performance_gate.py; neue isolierte V1-Integrations-/Race-/Performancefixtures; spätere Browserprüfung.

**DB / Migration:** **Keine neue DB-Änderung erwartet**; isolierte Testdatenbanken mit zuvor geprüften Migrationen und Legacy-Fixtures.

**Required Tests:** Alle KEEP-Bereiche aus Audit §18 sowie neue V1-Verträge; expiry, decline, withdraw, Quota3, stale rank/payload, concurrent GO/expiry, Pre-shipping-Unfulfillable, Problem nach Versand, Block/Privacy, Mengen-/Need-Kollisionen, CSRF und Wiederholung.

**Acceptance Criteria:** Beide Golden Paths vollständig erfolgreich ohne doppelte Buchung/Bindung/History. Jeder Negativfall hinterlässt den vertraglich erwarteten atomaren Zustand. Bestehender R4-Gate (20 parallele Nutzer, P95 unter500ms gemäß Baseline) bleibt grün; Globalberechnung und GO zusätzlich mit deklarierten Datenumfängen, Wiederholungen, SQL-/Lock-/CPU-Anteilen messen. Kein unbelegtes „performance ready“ bei ungemessenem Solver oder fehlendem Nachweis der AC26-Prioritätsregel.

**Risks:** Nur kleine Fixtures verdecken globale Suchkosten; parallele Writes serialisieren; historische grüne Werte werden auf neue Pfade übertragen.

**Depends On:** Alle P0/P1-Blöcke; SD-T8b nur testen, falls gewählt.

## Reihenfolge und Gates

Implementierungsfolge: T1 → T2a → T2b → T3a → T3b; T6a nach T1/T2b und vor T4; T4 → T5a → T5b → T6b. Die zukünftigen Buchungsadapter von T7a werden bei T1 und vor Core-Abnahme auf Anschlussfähigkeit geprüft. T7a → T7b; T8a nach T7a; T9 nach klaren Lifecycle-/Kontaktverträgen; T10 erst nach deren Implementierungsnachweisen und PO-SOLL; T11 als Endabnahme. Blocktests laufen jeweils beim späteren Implementieren, nicht erst am Schluss. T8b ist ein unabhängiger optionaler Ausbau nach seinen Voraussetzungen.

**Design-Gate:** Alle zehn P0-Blöcke sind isoliert verifiziert. Berechnen → exaktes GO → beidseitig reservieren → offener Request → Accept/Mutual GO funktioniert einschließlich Identität, Retry/Races, Quota, 24h/Release, Eligibility, versprochenem Need und Legacy-Koexistenz. Accepted-Positionen passen nach geprüftem Adaptervertrag zum bestehenden physischen Lifecycle. Dann kann der PO visuelle SmartDeal-Sprache und SOLL-UX konkret entwickeln; vollständige Versand-/Kontaktimplementierung muss dafür noch nicht fertig sein. Die entschiedene Konfliktpriorität aus AC26 ist feste Designgrundlage.

Dieses Gate ist **keine Beta- oder UI-Aktivierungsfreigabe**. Öffentliches Aktivieren erfordert zusätzlich T7a/b einschließlich AC26-Prioritätsnachweis, sicheren Kontakt T8a, PO-geprüfte IA T9, UI-Nachweise T10 und Abschluss T11. Interne Foundation-Schritte dürfen keine öffentlich erzeugbaren, nicht vollständig freigebbaren oder nicht abschließbaren Vorgänge hinterlassen. Bis zur Aktivierung sind neue Einstiegspunkte intern bzw. im isolierten Testsystem.

## Migrationen und ausdrücklich geschützte KEEP-Verträge

Keine Migration wird in diesem Auftrag erstellt. Wahrscheinlich ist eine minimale dauerhafte V1-/Multi-Album-/Pre-accept-Erweiterung nötig; T1 muss dies gegen vorhandene positionsbasierte Speicherung belegen. Identität/Unique-Schutz möglichst darin bündeln. Sichere Kontaktpersistenz ist ein separater wahrscheinlicher Bedarf; Chatpersistenz nur bei Wahl von P2. Problemstatus benötigt lediglich bei nachgewiesener Lücke eine Erweiterung. Read-only Projektion/Optimizer/Navigation/Design rechtfertigen für sich keine Migration. Keine Anzahl oder konkrete Tabellen ohne Foundation-Nachweis festlegen.

KEEP: kanonische physische quantity und Eigenexemplar, Availability ohne Doppelabzug; atomare Mengenbindungen/Rollback; positionsbasierte Ausbuchung bei eigenem Versand und Einbuchung bei tatsächlichem Empfang; Transit kein Besitz; idempotente Events und append-only History; reale Teil-/Restlieferung, Problemabschluss, Erfolgsprojektion und Ratings; Auth/CSRF/Beteiligtenprüfung, Account-/Block-/Pool-/Privacy-Gates; Typed Notifications mit Source-Dedupe und sicherem Ziel, Inbox Read/Retention; freie Discovery, unveränderliches Smart-Paket, manuelle Ungleichheit und Papier-/CEOKlaue-Vertrag. Alte Requests behalten Frist, Reservierungszeitpunkt, Retry und Abschlusssemantik; ihre echten Bindungen wirken weiter auf neue V1-Verfügbarkeit. ADAPT ist ausdrücklich auf neue V1-Semantik und notwendige Adapter begrenzt.

## R5-Abgrenzung und Dokumentationsprüfung

Diese Roadmap läuft separat vom R5-Releaseprozess. Kein R5-Statuswechsel, kein RC0, kein Commit/Push/Deploy. Falls eine spätere Implementierung denselben Releasezweig betrifft, muss ihr Scope samt Regressionen und Migrationen ausdrücklich in den Releaseprozess eingeordnet werden; dieses Dokument trifft keine Releaseentscheidung. Der [R4-Vertrag](R4_V20_PERFORMANCE_BASELINE.md) und die [B1.2-Reproduzierbarkeit](R5_B12_PERFORMANCE_REPRODUCIBILITY.md) bleiben Referenzen mit ihren dokumentierten Grenzen, kein Nachweis für neue globale Last.

Für den finalen Dokumentations-/Review-Auftrag werden ausschließlich Algorithm Contract und notwendige Präzisierungen dieser bestehenden Roadmap geändert. Product Bible bleibt unverändert. IST-Audit und vorhandener Worktree bleiben erhalten. Keine Runtime/UI/Routes/DB/Tests verändert, keine Tests oder Benchmarks ausgeführt, kein git add/Commit/Push/Deploy. Abschlusskontrolle erfolgt mit auftragsbezogenem Dateihashvergleich und Whitespace-Prüfung zusätzlich zu git status --short, git diff --check und git diff --stat. **STOP nach Dokumentation.**
