# TRADE-05 — Fehlmenge, reduzierter Tausch und Partnerzustimmung

Stand: 2026-09-30. Ausschließlich lokale Trade-v2-Preview auf Port 8095. Keine produktive Domainintegration.

## Ergebnis / Start

Die tatsächliche Bestätigung „Die Sticker fehlen wirklich“ übernimmt die konkreten offenen GIVE-Keys und erzeugt einen Amendment-Vorschlag. V1 bleibt aktiv. „Änderung ansehen“ öffnet den Wartezustand bzw. die gespiegelte Partnerentscheidung. Nur die Gegenseite kann die exakte Änderung annehmen oder den gesamten Trade beenden. Zustimmung aktiviert einen gemeinsamen V2-Snapshot mit positionsgenau erhaltenen Packmarkierungen.

Start im Projektverzeichnis:

```sh
.venv/bin/python -B -m App.trade_v2
```

- Preview: http://127.0.0.1:8095/trade-v2/
- Valentin wartet: http://127.0.0.1:8095/trade-v2/requests/fatima/amendment?amend=waiting&role=sender
- Fatima entscheidet: http://127.0.0.1:8095/trade-v2/requests/fatima/amendment?amend=proposal&role=recipient
- Valentin nach Zustimmung: http://127.0.0.1:8095/trade-v2/requests/fatima/amendment?amend=accepted&role=sender
- Fatima nach Zustimmung: http://127.0.0.1:8095/trade-v2/requests/fatima/amendment?amend=partial-after&role=recipient
- Fatima beendet: http://127.0.0.1:8095/trade-v2/requests/fatima/amendment?amend=cancelled&role=recipient
- Valentin sieht Beendigung: http://127.0.0.1:8095/trade-v2/requests/fatima/amendment?amend=cancelled&role=sender
- [Alle direkten QA-Einstiege](../tests/research/artifacts/trade-05/demos.html), einschließlich MISSING_REPORTED, 12/23 vor Änderung, Versand-Sperre, leerem Restdeal und weiterer Fehlmenge.

Explizite `amend=`-Links setzen ausschließlich den lokalen Tab-Demostand neu. Danach wird der Parameter entfernt. Reload, normaler URL-Wiedereinstieg und Rollenwechsel erhalten den Zustand. Bewusstes erneutes Öffnen eines vollständigen QA-Seed-Links ist ein expliziter Demo-Reset, keine produktive Retry-Semantik. Ohne Demo-Parameter wird kein neuer Trade erfunden.

## Ausgangszustand und Vertragsabgleich

Gelesen: `TRADE_PRODUCT_CONTRACT_V2.md`, `TRADE_00_RESET_AUDIT.md`, `TRADE_01_AUDIT.md`, `TRADE_02_AUDIT.md`, `TRADE_03_AUDIT.md`, `TRADE_04_AUDIT.md`. Zusätzlich relevante Abschnitte aus `SMARTDEAL_ALGORITHM_CONTRACT_V1.md`, `MANUAL_OFFER_DOMAIN_CONTRACT_V1.md` und `SAMMLRPAX_CONTRACT_V1.md` zu Mengen, deterministischer Reihenfolge, Amendment, Slots und Legacy.

Maßgebliche Einordnung:

- Trade-V2 §§10/12 ersetzen Q1 und AC25/26 nur hinsichtlich ausdrücklich bestätigter Änderungen vor Versand. Die alte Pflicht, jeden unvollständigen Vertrag vollständig zu beenden, wird nicht wieder eingeführt. Freeze, keine stille Reparatur und Schutz versendeter Richtungen bleiben bestehen.
- Die jetzt beauftragte Regel entspricht der bereits dokumentierten positionsgleichen deterministischen Gegenentfernung in SammlrPax Contract §8.1 ohne albumstrikte 1:1-Regel. Übernommen wird diese fachliche Regel, keine Pax-Produktmetapher. Keine DOM-Sortierung, keine neue Albumpräferenz und keine neue Matchingregel.
- AC14 definiert deterministische Stückfolgen. In dieser isolierten Preview ist die bei Anfrage eingefrorene, bereits deterministische Fixture-Reihenfolge die vereinbarte Reihenfolge. Sie wird weder neu sortiert noch als Produktions-Optimizer ausgegeben. Produktive Integration muss die kanonische vereinbarte Positionsfolge bereitstellen; die Anzeige ist nicht die Quelle.
- Trade-V2 §6 schützt **initiale** automatische 1:1-Erstellung mit Minimum fünf. TRADE-05 erstellt keinen neuen automatischen Deal und führt keinen Generator aus. Für akzeptierte Amendments ist kein zusätzliches Mindestvolumen festgelegt; verhindert wird ein leerer Richtungsteil. Eine bestätigte Verkleinerung auf 1↔1 ist daher im Modell testbar, ohne automatische Erstvorschläge unter fünf zu erlauben.
- Mengeninstanzen werden einzeln verarbeitet. Der synthetische Mehrfachexemplar-Test prüft vorhandene physische Positionen; er erlaubt dem Generator keinen neuen mehrfachen Bedarf derselben Album-/Stickeridentität. Need-Caps und manuelle Erstellungsregeln bleiben unverändert.
- Herkunft ist kein Branch im Amendment-Modell. Gleiche normalisierte akzeptierte Fixtures funktionieren für TOP_SUGGESTION, SMARTDEAL und MANUAL. Ein vorhandener ungleicher manueller Vertrag wird durch gleich viele Entfernungen nicht zwangsweise auf 1:1 umgerechnet. Fehlt ein benötigter Gegenindex, wird die Änderung kontrolliert nicht vorgeschlagen. Kein neuer manueller Builder oder Adapter für noch nicht vorhandene produktive Präferenzmetadaten.
- Gemeinsame operative Slots nach Trade-V2 §9; Request-State und physische Verpflichtung bleiben getrennt. AC23 bleibt für Pending-Anfragen gültig; kein neuer Amendment-/Packtimer.
- Legacy/V1 behalten ihre bisherigen Regeln. Dieser Auftrag definiert ausschließlich die beauftragte isolierte V1→V2-Demotransition; keine rückwirkende Migration und kein produktiver Bindungswechsel.

Keine Domainkollision im beauftragten Referenzfall. Produktive Revalidierung von Supply, Need, eingefrorenen Präferenzen und Ersatzbindung unter gemeinsamer Schreibgrenze bleibt ein späteres Integrationsgate.

## Deterministische Positionen und Vorschlag

`deal_versions.js` bildet aus dem ursprünglichen Snapshot je Richtung eine unveränderliche Positionsliste. Ein Eintrag enthält ursprünglichen 1-basierten Index, richtungsbezogene `positionId` (`request-id/sender/22`), vorhandenen Exemplar-Key, Code, Instanz und Album. `positionOrder` wird aus V1 eingefroren. Diese ursprünglichen IDs bleiben auch nach der Kürzung in der History erhalten; die Packlisten nutzen weiterhin die unveränderten Exemplar-Keys.

Ein Missing-Key wird auf seinen ursprünglichen Index abgebildet. Entfernt werden genau dieser eigene Eintrag und derselbe Index der Gegenrichtung. Beispielreferenz: Valentin fehlen WM 2006 MEX 2 und MEX 3, ursprüngliche Positionen 22 und 23; bei Fatima entfallen WM 2006 BRA 2 und BRA 3, ebenfalls 22 und 23. Beide Listen werden um genau zwei Positionen verkleinert: 23↔23 → 21↔21. Reihenfolge aller verbleibenden Einträge bleibt erhalten. Keine Zufallsauswahl, Scores, Ersatzsticker oder Neuberechnung.

Das Modell unterstützt mehrere Missing-Keys und einzelne Instanzen gleicher Codes. Der zusätzliche 37-Positionen-Test entfernt genau die Exemplare an 3 und 37 und erhält 35; nicht alle gleichen Codes. Entfernte vollständige Albumgruppen verschwinden aus V2, Counts und Albumzahl werden aus den verbleibenden Einträgen abgeleitet.

`MISSING_REPORTED` selbst ändert den aktiven Snapshot nicht. Das anschließende Erzeugen des Proposals ergänzt nur Änderungsdaten. Ein direkter Report-only-QA-Zustand zeigt noch keinen Vorschlag und bleibt auch bei Reload stabil; „Änderung ansehen“ erzeugt ihn explizit. Der normale TRADE-04-Reportbefehl erzeugt ihn unmittelbar nach der bewussten Fehlbestätigung.

Während Pending werden die Packaktionen für beide Richtungen gesperrt; die bestehende Packliste bleibt unverändert im Snapshot. Die Gegenseite wird zur Änderungsansicht geführt. Kein ungeklärtes Weiterpacken gegen eine still aktualisierte Liste.

## Versions- und Zustandsmodell

Ein Request, eine aktive `snapshot`-Referenz. Neue Requests führen `deal_version: 1`. Vorbestehende lokale Preview-Requests ohne Versionsfeld werden als unveränderte V1 gelesen; dabei kein Rewrite, keine Migration produktiver/Legacy-Verträge.

Beim Vorschlag zusätzlich:

- `dealVersions`: V1-Snapshot als unveränderliche Historie.
- `positionOrder`: beide ursprünglichen Stückfolgen.
- `amendment`: stabile ID, `baseVersion: 1`, meldende Rolle, Demo-Zeitpunkt, konkrete Missing-Keys, entfernte Positionen beider Richtungen, vorgeschlagener Snapshot und `pending`.

Annahme durch die andere Rolle setzt in **einer synchronen logischen Transition** `deal_version: 2`, den gemeinsamen aktiven Snapshot, die V2-Historie, Zustimmung/Zeitpunkt, `amendment.status: accepted` und beide abgeleiteten Packstände. Der Controller liest vor jedem Command den neuesten Sessionstand und schreibt anschließend genau einmal den gesamten Zustand. Es gibt keinen gespeicherten Zwischenzustand 21 gegen 23 und keinen zweiten Trade.

`readState` prüft Versionsstruktur, ursprüngliche Positionsfolge, deterministische Gegenentfernung, Proposal-Inhalt und aktive V2 gegen die Historie. Manipulierte Gegenpositionen werden zurückgewiesen. Snapshots, Versionshistorie, Positionsfolge und Proposal werden beim Erstellen/Lesen rekursiv eingefroren. Unzulässige/überholte Aktionen werden abgewiesen.

Diese Atomarität gilt für den bestehenden isolierten **einen SessionStorage-Tab**. Kein Anspruch auf produktive Mehrbenutzer-/DB-Transaktionen oder tabsübergreifende Synchronisierung.

## Packfortschritt und Spiegelung

Nach Zustimmung kommen beide Listen ausschließlich aus dem neuen aktiven Snapshot. Eigene Packkeys werden mit den verbleibenden Positionen geschnitten. Keine Zählerkorrektur ohne Identitäten und keine manuell gepflegte Ersatzpackliste.

- Valentin 21/23, die beiden offenen entfallen → 21/21, `packing_complete`.
- Fatima vorher 12/23; null/eine/zwei bereits gepackte Gegenpositionen entfallen → 12/21, 11/21 bzw. 10/21.
- Unvollständig bleibt `packing`; vollständig wird je Rolle unabhängig `packing_complete`.
- Nach V2 gilt weiterhin Referenzgleichheit A GIVE = B RECEIVE und A RECEIVE = B GIVE.

Für vollständig gepackte V2 ist eine lesbare Packlistenansicht erreichbar; Markierungen bleiben sichtbar, abgeschlossene Controls sind dort deaktiviert. Unvollständige V2 bleibt normal bedienbar. Request-Detail und ursprüngliche Deal-URL lesen ebenfalls V2; kein Rückfall auf die 23er-Fixture. Der blutrote Marker, Pack-CSS und kanonische Renderer bleiben bytegleich.

## Entscheidung, Slots und Schutzregeln

Nur die Rolle gegenüber `amendment.proposer` kann Pending annehmen/beenden. Same-actor, fremde Rolle, falsche Amendment-ID und illegale Transition verändern den Deal nicht. Erste gültige Entscheidung gewinnt. Accept→Cancel, Cancel→Accept, Doppelklick und wiederholte Events erhöhen die Version nicht erneut.

Nach dem ersten Accept erhält der neu eingeblendete Packlisten-Link einen kurzen 350-ms-Klickschutz, damit der zweite physische Doppelklick nicht versehentlich auf diesen Link fällt. Das ist ausschließlich ein Navigationsschutz; weder Domainzeit noch Markeranimation wird geändert. `aria-disabled` kommuniziert den kurzen Schutz auch semantisch.

- Accept: Request bleibt `accepted`; eigener ausgehender Slot 3/3 und Fatimas eingehender Slot 1/3 bleiben belegt.
- Cancel: gesamter Request `cancelled`, Änderungsentscheidung und Zeitpunkt gespeichert. Kein aktiver Resttrade, keine Reaktivierung von V1; V1 bleibt nur Historie. Ausgehend 3/3→2/3, eingehend 1/3→0/3. Beide Rollen sehen „Der Tausch wurde beendet.“ Alte Pack- und Deal-URLs führen ebenfalls zum Endzustand.
- `ownShipped` **oder** `recipientShipped`: Vorschlagserzeugung, Annahme und Beendigung über diesen Amendment-Mechanismus gesperrt, auch wenn der Indikator erst nach Pending gesetzt wurde. Snapshot unverändert, späterer Problemflow erforderlich. DEV simuliert nur einen bestehenden Versandindikator; kein Versandcommand.
- Leerer Restdeal: kein aktivierbarer 0↔0-Snapshot, kein Accept-CTA; Partner kann den gesamten Trade beenden. Bis zur Entscheidung bleibt V1 gespeichert und der Slot belegt.
- Zweite Fehlmenge nach V2: „Weitere Änderung erforderlich“, V2 bleibt aktiv und unverändert. Keine automatische V3-/Verhandlungskaskade.
- Gleichzeitige unabhängige Fehlberichte oder nicht vorhandener Gegenindex: kontrollierte Klärung statt stiller Auswahl. Kein erfundener Fallback.

## UI / Accessibility / Responsive

Kompakte textliche Änderungsliste in der bestehenden Shell. Bisher/Vorgeschlagen, konkrete nicht mehr erhaltene und nicht mehr abzugebende Exemplare, Zustimmung oder Beendigung. Technische Versions-/Positionsdetails nur im DEV-Bereich. Kein Pax-Wording.

Native Buttons/Links, sichtbarer Fokus, Tab/Shift+Tab/Enter/Space, Touch und Maus. Nach Entscheidung Fokus auf Ergebnisüberschrift. Statusänderungen über Live-Regionen; Bedeutung unabhängig von Farbe. Reduced Motion unverändert wirksam. 375/390/430/1280 px: kein horizontaler Overflow; beide CTAs, Fehlpositionen, Wartestatus, V2-Packlisten und Beendigung geprüft. Sichtprüfung der 390-px-Partneransicht und vollständigen 21/21-Liste bestanden.

## Tests und Artefakte

Ausgeführt:

```sh
.venv/bin/python -B -m unittest tests.test_trade_v2_preview tests.test_pax_preview -q
.venv/bin/python -B -m unittest tests.test_sticker_wall_product_island tests.test_ceoklaue_sticker_list -q
.venv/bin/python -B tests/research/check_trade_05_regressions.py
.venv/bin/python -B tests/research/check_trade_05.py
git diff --check
```

- 8 Preview-/Isolations-Unittests bestanden, neue GET-Route eingeschlossen, POST 405, kein DB-/Produktivservice-Import durch Preview.
- 29 bestehende Stickerwall-/Listen-Unittests bestanden; deren Referenzharness verwendet temporäre Test-DBs.
- TRADE-01–04-Browsergates werden **unverändert** importiert und in neue Artefaktordner ausgeführt. Discovery, Anfrage, Spiegelung, Slots, Fristen, Packen, Marker, Touch/Keyboard/Reduced Motion und alte direkte Demos bleiben abgedeckt. Keine alte Assertion für TRADE-05 entfernt.
- Stack-Parität: tatsächlicher produktiver BRA-3-Renderer gegen unveränderten Trade-Renderer, 21 Fälle (Mengen 1/2/5/6/10/15/37 bei 375/390/430). Wall-Cap 5, Trade-Cap 10, −2/−2, Faces/Maße/z-index identisch; ab 10 kein weiteres Wachstum.
- Neuer Browsergate bei allen vier Breiten: tatsächlicher Report→Pending→Partnerzustimmung, beide Rollen, konkrete Keys und Vorher/Nachher, kein Self-Accept, aktive V2 auf allen Detailpfaden, 21/21 und 11/21-Packlisten, Doppelklick/mehrfache Gegenaktionen, Cancel und Slotfreigabe, Endzustände über alte URLs, Versand-Sperre, leerer Restdeal, zweite Fehlmenge, direkte Demo-Einstiege und Reload. Keine JS-/HTTP-Fehler, externen oder schreibenden Requests.
- 205 reine Modellassertionen: beide meldenden Rollen × drei Herkünfte, genaue Gegenpositionen, Originalindizes 3/37, separate Exemplare, V1-Historie/Freeze, atomare V2, 12→12/11/10, spiegelgleiche Referenzen, Auth-/Stale-/Terminalguards, Slots, Versand vor/nach Pending beider Richtungen, leerer Restdeal, positive kleine Restgröße, zweite Meldung, manipulierte Persistenz und gleichzeitige Fehlberichte.

Während der Prüfung behoben: Nach physischem Doppelklick konnte der zweite Klick auf den neu eingeblendeten Packlisten-Link fallen. Der lokale Navigationsschutz verhindert das; Versionsmodell blieb auch vorher bei V2. Der neue Modelltest benötigte absolute Modul-URLs beim Laden aus einem Blob; Testharness korrigiert, keine App-Änderung dafür. Report-only-Demo behält ihren Zustand auch bei Reload.

Evidenz:

- [Screenshot-Galerie](../tests/research/artifacts/trade-05/index.html)
- [Direkte Demo-URLs](../tests/research/artifacts/trade-05/demos.html)
- [Browser-/Modellergebnis](../tests/research/artifacts/trade-05/checks.json)
- [TRADE-01](../tests/research/artifacts/trade-05/regression-01/checks.json), [TRADE-02](../tests/research/artifacts/trade-05/regression-02/checks.json), [TRADE-03](../tests/research/artifacts/trade-05/regression-03/checks.json), [TRADE-04](../tests/research/artifacts/trade-05/regression-04/checks.json)
- [Dateimanifest](../tests/research/artifacts/trade-05/files.json)
- [Geschützte Hashes und Whitespace-Prüfung](../tests/research/artifacts/trade-05/scope-checks.json)

## Geänderte / neue Quelldateien

Geändert:

- `App/trade_v2/routes.py` — isolierter GET-Amendment-Endpunkt.
- `App/trade_v2/templates/preview.html` — Änderungsansicht, DEV und Packlistenlinks.
- `App/trade_v2/assets/requests.js` — explizite Version, Validierung/Freeze, lokaler Cancel-Zustand.
- `App/trade_v2/assets/packing.js` — Pending-Guard und lesbarer historischer Cancel-Packstand.
- `App/trade_v2/assets/packing_view.js` — Report-Anschluss, Pending-/Cancel-Navigation, vollständige V2-Liste.
- `App/trade_v2/assets/request_view.js` — aktive V2, Pending-Link und gemeinsamer Cancel-Endzustand.
- `App/trade_v2/assets/sender.js` — beendeten Trade nicht als aktiven Deal anzeigen.
- `App/trade_v2/assets/preview.js` — Amendment-Controller und korrekte V2-Zusammenfassung.
- `tests/test_trade_v2_preview.py` — zusätzliche isolierte Route in No-DB-/GET-only-Test.

Neu:

- `App/trade_v2/assets/deal_versions.js` — ursprüngliche Positionen, Reduktion, Versionsprüfung/Freeze.
- `App/trade_v2/assets/amendments.js` — Vorschlag und atomare lokale Accept-/Cancel-Transition.
- `App/trade_v2/assets/amendment_demo.js` — ausschließlich explizite QA-Seeds.
- `App/trade_v2/assets/amendment_view.js` — Rollenansicht, Controls, Endzustände und DEV.
- `App/trade_v2/assets/amendment.css` — lokale Änderungsansicht.
- `tests/research/check_trade_05.py` — Browsergate und Galerie.
- `tests/research/trade_05_model.js` — reine Modellassertionen gegen tatsächliche App-Module.
- `tests/research/check_trade_05_regressions.py` — unveränderte alte Browsergates, neuer Ausgabeort.
- `docs/TRADE_05_AUDIT.md` — dieser Audit.
- Neue Research-Artefakte ausschließlich unter `tests/research/artifacts/trade-05/`; jede Datei einzeln im Manifest und nachfolgend aufgeführt. Alte Galerien/Audits/Tests bleiben erhalten.

## Schutzgrenzen / negative Assertions

SHA-256-Baseline vor Änderungen: `/tmp/trade05-before.json`. Der dauerhafte Scope-Bericht enthält Vorher-/Nachher-Hashes und die vollständige Änderungsliste. Vorbestehende lokale Änderungen werden als Ausgangszustand geschützt, nicht gegen Git zurückgesetzt.

- Keine Produktiv-DB verändert; keine produktive DB-Mutation.
- Keine produktiven Trade-Routen oder produktive Webapp verändert.
- `App/pax/`, sämtliche Pax-Assets/Templates und historische Previews unverändert.
- Produktive Stickerwall, Stickerliste und Post-it-Logik unverändert.
- SmartDeal-Algorithmus unverändert; kein Algorithmus-Neulauf beim Amendment.
- Keine Ersatzsticker, kein Gegenangebot, keine neue Partnerwahl.
- Keine Adresse, kein DHL, kein Versand, kein Empfang und keine Bewertung implementiert.
- Kein Slot bei angenommenem Amendment freigegeben. Freigabe ausschließlich bei expliziter vollständiger Beendigung in diesem Scope.
- Blutroter Marker, bestehendes Pack-CSS, kanonische Stacklogik und 16/20-Paginierung unverändert.
- Keine produktiven Bindungen, Reservations- oder Inventarbuchungen; keine Legacy-Migration.
- Kein git add, kein Commit, kein Push, kein Deploy. Nur eigener Previewserver 8095 neu gestartet; 8080/8094 unberührt.

## Vollständige Liste neuer Research-Artefakte

- `tests/research/artifacts/trade-05/01-packing-21-390.png`
- `tests/research/artifacts/trade-05/01b-missing-reported-390.png`
- `tests/research/artifacts/trade-05/02-valentin-waiting-1280.png`
- `tests/research/artifacts/trade-05/02-valentin-waiting-375.png`
- `tests/research/artifacts/trade-05/02-valentin-waiting-390.png`
- `tests/research/artifacts/trade-05/02-valentin-waiting-430.png`
- `tests/research/artifacts/trade-05/03-fatima-proposal-1280.png`
- `tests/research/artifacts/trade-05/03-fatima-proposal-375.png`
- `tests/research/artifacts/trade-05/03-fatima-proposal-390.png`
- `tests/research/artifacts/trade-05/03-fatima-proposal-430.png`
- `tests/research/artifacts/trade-05/04-missing-positions-390.png`
- `tests/research/artifacts/trade-05/05-counter-positions-390.png`
- `tests/research/artifacts/trade-05/06-before-after-390.png`
- `tests/research/artifacts/trade-05/07-fatima-accepted-1280.png`
- `tests/research/artifacts/trade-05/07-fatima-accepted-375.png`
- `tests/research/artifacts/trade-05/07-fatima-accepted-390.png`
- `tests/research/artifacts/trade-05/07-fatima-accepted-430.png`
- `tests/research/artifacts/trade-05/08-valentin-v2-packed-1280.png`
- `tests/research/artifacts/trade-05/08-valentin-v2-packed-375.png`
- `tests/research/artifacts/trade-05/08-valentin-v2-packed-390.png`
- `tests/research/artifacts/trade-05/08-valentin-v2-packed-430.png`
- `tests/research/artifacts/trade-05/09-fatima-progress-retained-1280.png`
- `tests/research/artifacts/trade-05/09-fatima-progress-retained-375.png`
- `tests/research/artifacts/trade-05/09-fatima-progress-retained-390.png`
- `tests/research/artifacts/trade-05/09-fatima-progress-retained-430.png`
- `tests/research/artifacts/trade-05/10-fatima-cancelled-1280.png`
- `tests/research/artifacts/trade-05/10-fatima-cancelled-375.png`
- `tests/research/artifacts/trade-05/10-fatima-cancelled-390.png`
- `tests/research/artifacts/trade-05/10-fatima-cancelled-430.png`
- `tests/research/artifacts/trade-05/11-valentin-cancelled-1280.png`
- `tests/research/artifacts/trade-05/11-valentin-cancelled-375.png`
- `tests/research/artifacts/trade-05/11-valentin-cancelled-390.png`
- `tests/research/artifacts/trade-05/11-valentin-cancelled-430.png`
- `tests/research/artifacts/trade-05/12-shipped-blocked-390.png`
- `tests/research/artifacts/trade-05/13-dev-v1-390.png`
- `tests/research/artifacts/trade-05/14-dev-v2-390.png`
- `tests/research/artifacts/trade-05/15-empty-proposal-390.png`
- `tests/research/artifacts/trade-05/checks.json`
- `tests/research/artifacts/trade-05/demos.html`
- `tests/research/artifacts/trade-05/files.json`
- `tests/research/artifacts/trade-05/index.html`
- `tests/research/artifacts/trade-05/regression-01/01-home-375.png`
- `tests/research/artifacts/trade-05/regression-01/01-home-390.png`
- `tests/research/artifacts/trade-05/regression-01/01-home-430.png`
- `tests/research/artifacts/trade-05/regression-01/02-top-five-390.png`
- `tests/research/artifacts/trade-05/regression-01/04-top-detail-390.png`
- `tests/research/artifacts/trade-05/regression-01/05-partner-preview-390.png`
- `tests/research/artifacts/trade-05/regression-01/06-partners-390.png`
- `tests/research/artifacts/trade-05/regression-01/07-filter-390.png`
- `tests/research/artifacts/trade-05/regression-01/08-karlheinz-390.png`
- `tests/research/artifacts/trade-05/regression-01/09-karlheinz-smartdeal-390.png`
- `tests/research/artifacts/trade-05/regression-01/10-manual-end-390.png`
- `tests/research/artifacts/trade-05/regression-01/11-receive-open-390.png`
- `tests/research/artifacts/trade-05/regression-01/12-give-continuation-390.png`
- `tests/research/artifacts/trade-05/regression-01/checks.json`
- `tests/research/artifacts/trade-05/regression-01/index.html`
- `tests/research/artifacts/trade-05/regression-02/01-home-1280.png`
- `tests/research/artifacts/trade-05/regression-02/01-home-390.png`
- `tests/research/artifacts/trade-05/regression-02/02-fatima-deal-1280.png`
- `tests/research/artifacts/trade-05/regression-02/02-fatima-deal-390.png`
- `tests/research/artifacts/trade-05/regression-02/03-sent-1280.png`
- `tests/research/artifacts/trade-05/regression-02/03-sent-390.png`
- `tests/research/artifacts/trade-05/regression-02/04-two-before-1280.png`
- `tests/research/artifacts/trade-05/regression-02/04-two-before-390.png`
- `tests/research/artifacts/trade-05/regression-02/05-three-after-1280.png`
- `tests/research/artifacts/trade-05/regression-02/05-three-after-390.png`
- `tests/research/artifacts/trade-05/regression-02/06-fourth-blocked-1280.png`
- `tests/research/artifacts/trade-05/regression-02/06-fourth-blocked-390.png`
- `tests/research/artifacts/trade-05/regression-02/07-pool-1280.png`
- `tests/research/artifacts/trade-05/regression-02/07-pool-390.png`
- `tests/research/artifacts/trade-05/regression-02/08-karlheinz-1280.png`
- `tests/research/artifacts/trade-05/regression-02/08-karlheinz-390.png`
- `tests/research/artifacts/trade-05/regression-02/checks.json`
- `tests/research/artifacts/trade-05/regression-02/index.html`
- `tests/research/artifacts/trade-05/regression-03/01-valentin-waiting-1280.png`
- `tests/research/artifacts/trade-05/regression-03/01-valentin-waiting-375.png`
- `tests/research/artifacts/trade-05/regression-03/01-valentin-waiting-390.png`
- `tests/research/artifacts/trade-05/regression-03/01-valentin-waiting-430.png`
- `tests/research/artifacts/trade-05/regression-03/02-fatima-incoming-1280.png`
- `tests/research/artifacts/trade-05/regression-03/02-fatima-incoming-375.png`
- `tests/research/artifacts/trade-05/regression-03/02-fatima-incoming-390.png`
- `tests/research/artifacts/trade-05/regression-03/02-fatima-incoming-430.png`
- `tests/research/artifacts/trade-05/regression-03/03-fatima-mirrored-1280.png`
- `tests/research/artifacts/trade-05/regression-03/03-fatima-mirrored-375.png`
- `tests/research/artifacts/trade-05/regression-03/03-fatima-mirrored-390.png`
- `tests/research/artifacts/trade-05/regression-03/03-fatima-mirrored-430.png`
- `tests/research/artifacts/trade-05/regression-03/04-fatima-before-accept-390.png`
- `tests/research/artifacts/trade-05/regression-03/05-fatima-accepted-1280.png`
- `tests/research/artifacts/trade-05/regression-03/05-fatima-accepted-375.png`
- `tests/research/artifacts/trade-05/regression-03/05-fatima-accepted-390.png`
- `tests/research/artifacts/trade-05/regression-03/05-fatima-accepted-430.png`
- `tests/research/artifacts/trade-05/regression-03/06-valentin-accepted-1280.png`
- `tests/research/artifacts/trade-05/regression-03/06-valentin-accepted-375.png`
- `tests/research/artifacts/trade-05/regression-03/06-valentin-accepted-390.png`
- `tests/research/artifacts/trade-05/regression-03/06-valentin-accepted-430.png`
- `tests/research/artifacts/trade-05/regression-03/07-fatima-declined-1280.png`
- `tests/research/artifacts/trade-05/regression-03/07-fatima-declined-375.png`
- `tests/research/artifacts/trade-05/regression-03/07-fatima-declined-390.png`
- `tests/research/artifacts/trade-05/regression-03/07-fatima-declined-430.png`
- `tests/research/artifacts/trade-05/regression-03/08-valentin-declined-1280.png`
- `tests/research/artifacts/trade-05/regression-03/08-valentin-declined-375.png`
- `tests/research/artifacts/trade-05/regression-03/08-valentin-declined-390.png`
- `tests/research/artifacts/trade-05/regression-03/08-valentin-declined-430.png`
- `tests/research/artifacts/trade-05/regression-03/09-fatima-expired-1280.png`
- `tests/research/artifacts/trade-05/regression-03/09-fatima-expired-375.png`
- `tests/research/artifacts/trade-05/regression-03/09-fatima-expired-390.png`
- `tests/research/artifacts/trade-05/regression-03/09-fatima-expired-430.png`
- `tests/research/artifacts/trade-05/regression-03/10-dev-roles-390.png`
- `tests/research/artifacts/trade-05/regression-03/11-slot-before-decline-390.png`
- `tests/research/artifacts/trade-05/regression-03/12-slot-after-decline-390.png`
- `tests/research/artifacts/trade-05/regression-03/checks.json`
- `tests/research/artifacts/trade-05/regression-03/index.html`
- `tests/research/artifacts/trade-05/regression-04/01-packing-zero-1280.png`
- `tests/research/artifacts/trade-05/regression-04/01-packing-zero-375.png`
- `tests/research/artifacts/trade-05/regression-04/01-packing-zero-390.png`
- `tests/research/artifacts/trade-05/regression-04/01-packing-zero-430.png`
- `tests/research/artifacts/trade-05/regression-04/02-first-mark-390.png`
- `tests/research/artifacts/trade-05/regression-04/03-packing-partial-390.png`
- `tests/research/artifacts/trade-05/regression-04/04-packing-22-390.png`
- `tests/research/artifacts/trade-05/regression-04/05-packing-23-390.png`
- `tests/research/artifacts/trade-05/regression-04/06-packing-complete-390.png`
- `tests/research/artifacts/trade-05/regression-04/07-missing-review-390.png`
- `tests/research/artifacts/trade-05/regression-04/08-missing-reported-390.png`
- `tests/research/artifacts/trade-05/regression-04/09-secondary-receive-390.png`
- `tests/research/artifacts/trade-05/regression-04/10-fatima-packing-390.png`
- `tests/research/artifacts/trade-05/regression-04/12-dev-independent-390.png`
- `tests/research/artifacts/trade-05/regression-04/checks.json`
- `tests/research/artifacts/trade-05/regression-04/demos.html`
- `tests/research/artifacts/trade-05/regression-04/index.html`
- `tests/research/artifacts/trade-05/regression-04/marker-A-unpacked-390.png`
- `tests/research/artifacts/trade-05/regression-04/marker-B-first-paint-0ms-390.png`
- `tests/research/artifacts/trade-05/regression-04/marker-C-packed-390.png`
- `tests/research/artifacts/trade-05/regression-04/marker.html`
- `tests/research/artifacts/trade-05/scope-checks.json`
- `tests/research/artifacts/trade-05/trade-stack-10.png`
- `tests/research/artifacts/trade-05/trade-stack-37.png`
- `tests/research/artifacts/trade-05/trade-stack-6.png`
- `tests/research/artifacts/trade-05/wall-stack-10.png`
- `tests/research/artifacts/trade-05/wall-stack-37.png`
- `tests/research/artifacts/trade-05/wall-stack-6.png`
