# SAP-02 — Produktive Tauschbörse

Stand: 2026-10-05. Ausgangs-HEAD: `89c957de0b3ab9f412c6d8f6648cb00f3184a051`.
Umgesetzt im vorhandenen, bereits vor SAP-02 umfangreich uncommitteten Arbeitsstand. Kein Commit, Staging, Push oder Deploy.

## 1–3. Einstieg und Kompatibilität

`/tauschen` zeigt direkt SAP. `/tauschen/sammlr` verwendet denselben Controller und dasselbe Template; beide liefern dieselbe Ansicht. Keine zusätzliche Discovery-Ebene und kein sichtbarer „Alle Sammlr“-Button im Einstieg.

Die Top-3-Startseite wird nicht mehr geroutet. Ihre bisherige Berechnung, historische Template-Verzweigung und `/tauschen/vorschlag/<id>` bleiben für bestehende Deep Links erhalten. Bestehende Partner-/Auto-/laufende Routen wurden nicht destruktiv entfernt. Die alte Home-Präsentationsassertion wurde auf SAP-Ergebniszeilen umgestellt; Domain- und Deep-Link-Tests bleiben bestehen.

## 4–5. Sucharten und albumlokale Identität

Ein Suchfeld unterstützt Namen/Username, `@Username`, einzelne und mehrere Codes (Leerzeichen, Komma, Semikolon, `/`, `|`), Albumname/vorhandenen Identifier und präzise Album-plus-Code-Eingaben wie `WM26 POR15` oder `EM24 POR 15`.

`trade_search_intent.py` trennt Parser und Suchziele von Domain und Ergebnisprojektion. Suchziele sind ausschließlich `(album_id, canonical_code)` aus den aktuellen kanonischen Needs und Katalogen der ausgewählten Alben. Die Normalisierung dient nur dem Eingabeabgleich; sichtbare Originalcodes werden nicht umbenannt. Bereits besessene und durch bestehende Bindungen erfüllte Bedarfe zählen nicht.

POR15 in fünf Katalogen mit einem tatsächlichen Bedarf ergibt genau ein Ziel; bei zwei Bedarfen genau zwei Ziele und den Hinweis `POR15 · 2 Alben`. Es gibt keine Pflichtauswahl. Die präzise Albumangabe begrenzt die Suchziele, nicht die übrigen möglichen Dealbestandteile. Mehrfachsuche ist OR, kein zwingendes UND.

## 6. Ranking und Dealgröße

Ohne Suchziel: größter gültiger Gesamtdeal zuerst. Bei konkreten Stickerzielen: gleichzeitig erfüllbare Suchziele zuerst, danach Gesamtdealgröße. Damit schlägt 3/3 mit kleinem Deal 2/3 mit größerem Deal; bei gleicher Trefferzahl gewinnt der größere Deal. Diese explizite SAP-02-Entscheidung ersetzt die frühere SAP-01A-Suchsortierung „Dealgröße immer zuerst“.

Danach bleiben Favoritenalbum, relevante Überschneidung, Aktivität und stabile User-ID nachgelagerte Kriterien. Keine Aktivitätsfrist, neue Gewichtung oder Expertenfilter.

Die Suchtrefferzahl verwendet die bestehende gemeinsame `maximum_equal`-Balanceprüfung; drei einzeln relevante Ziele bei nur zwei passenden Give-Stickern werden nicht als 3/3 versprochen. Die Gesamtdealgröße stammt unverändert aus `TradeV2Domain`. Der Albumzähler verwendet weiter die vorhandene Projektion eines gültigen maximalen Pakets.

Albumsuche priorisiert Hilfe für dieses Album, ohne den möglichen Gesamtdeal auf dieses Album zu reduzieren. Nur die temporäre Tauschalben-Auswahl begrenzt beide Richtungen. Ohne konkrete Stickersuche erscheinen keine Null-Deal-Partner. Die separate Zusatzsektion trägt ausdrücklich „Aktuell kein Deal möglich“. Nulltreffer nennen den eingegebenen Code, ohne Ursachen zu erfinden.

## 7. Reservierungen und frische Prüfung

Kein neuer Reservationspfad: SAP nutzt weiterhin `TradeV2Domain.market` → kanonische Planung mit bestehendem `LegacyPlanningReadAdapter`. Relevante bestehende Bindungen/Positionen/Reservations werden in Give-Supply und offenen Receive-Needs berücksichtigt. Kein fehlender zusätzlicher produktiver Reservationsadapter wurde festgestellt.

Profile, Auto-Deal und manuelle Auswahl lesen beim Öffnen erneut serverseitig. `trade_seen` ist lediglich der zuvor angezeigte Vergleichswert, niemals eine Autorisierung oder Paketquelle. Änderungen erzeugen einen verständlichen Hinweis, auch wenn inzwischen gar kein Tausch mehr möglich ist. Der manuelle Prüfendpunkt validiert weiterhin Fingerprint und Auswahl gegen einen frischen Domain-Snapshot; bei vollständig weggefallener Gelegenheit antwortet er mit 409 statt einer veralteten Freigabe. Es wird keine Anfrage erstellt.

## 8. Album-/Sticker-Konsistenz und Privacy

Sammlungssichtbarkeit und explizite Trade-Pool-Freigabe sind bestehende, getrennte Verträge. `profile.current_albums` enthält nur sichtbare Sammlungsalben; eine private Sammlung darf unabhängig davon ausdrücklich zum Tauschen freigegeben sein. Die aktuelle lokale DB wurde hierfür ausschließlich über `mode=ro`/`query_only` aggregiert gelesen: Schema 20, neun private Album-Mitgliedschaften mit aktivem Trade-Pool. Keine Namen oder privaten Inventare wurden exportiert.

Synthetisch bestätigt: private Albumansicht bleibt unsichtbar, freigegebener Trade bleibt möglich. Der Profilhinweis erklärt diese Trennung. Tauschalben-Auswahl und Albumüberschriften der manuellen Liste machen den erlaubten Kontext nachvollziehbar. Deaktivierte/ausgewählte-fremde Alben werden nicht in die manuelle Auswahl eingeschleust. Kein Domainkonflikt, keine Privacy-Aufweichung und keine Migration erforderlich.

## 9. Gelber Übersichts-Post-it

Die bestehende manuelle Liste und ihr gelber Post-it werden weiterverwendet. Nur der produktive Live-Kontext erhält eine fixierte Position im Viewport samt zusätzlichem Scrollraum. Receive/Give-Zähler und „Auswahl prüfen“ bleiben sichtbar. Die isolierte Trade-v2-Preview und kanonische Stickerlisten-/Wall-Komponenten behalten ihre bestehenden Styles und Geometrien.

Die Tauschalben stehen auch bei 17 Alben einzeln untereinander. Lokale Checkbox-Regeln begrenzen Breite, Padding und Min-Breite; das gesamte Label bleibt mindestens 44 px hoch. Die globale Input-Regel wird nicht verändert.

## 10. Exakter Änderungsumfang

Die folgende Liste vergleicht mit dem SHA256-Snapshot **zu Beginn von SAP-02**, nicht mit HEAD. Mehrere dieser zuvor bereits vorhandenen Dateien sind weiterhin untracked aus früheren Aufträgen.

| Datei | SAP-02-Status |
|---|---|
| `App/profile_trade.py` | Geändert |
| `App/services/partner_trade.py` | Geändert |
| `App/services/trade_search.py` | Geändert |
| `App/services/trade_search_intent.py` | Neu |
| `App/static/profile_trade.css` | Geändert |
| `App/static/trade_manual_live.css` | Neu |
| `App/static/trade_search.css` | Geändert |
| `App/templates/profile_trade.html` | Geändert |
| `App/templates/trade_search.html` | Geändert |
| `App/templates/trade_search_additional.html` | Geändert |
| `App/templates/trade_shell.html` | Geändert |
| `App/trade_search_routes.py` | Geändert |
| `App/trade_shell.py` | Geändert |
| `App/trade_v2/templates/manual.html` | Geändert |
| `tests/research/check_sap01.py` | Geändert |
| `tests/research/check_sap02.py` | Neu |
| `tests/test_integration01_trade_shell.py` | Geändert |
| `tests/test_sap01_search.py` | Geändert |
| `tests/test_sap02_search.py` | Neu |

Zusätzlich neu: `docs/SAP_02_AUDIT.md` und die Prüfarbeitsprodukte unter `tests/research/artifacts/sap-02/`. Die vollständige Einzeldateiliste samt SHA256 steht in `artifact-manifest.json` (440 PNGs plus Ergebnis-/Log-/Manifestdateien). Keine alten Screenshotordner im Projekt überschrieben.

## 11. Ausgeführte Tests und Assertions

Alle App-/DB-Tests wurden in `/private/tmp/integration01-tests` mit ausschließlich SQL-generierten synthetischen Datenbanken ausgeführt. Keine echte Sammlr-DB wurde als Fixture kopiert. Der Release-Harness sperrt SQLite-Zugriffe außerhalb `/private/tmp` per Audit-Hook; `:memory:` bleibt erlaubt.

- Release-Gate: **1.353 bestanden**, 0 Fehler, 0 Failures, 0 Skips. 1.365 entdeckt; die zwölf bestehenden Ausschlüsse aus `docs/R5_TEST_CONTRACT.json` unverändert. Vorhandene SmartDeal-/Solver-/Privacy-/Stickerwall-Tests eingeschlossen.
- Getrennter Preview-Prozess: **8 bestanden** (`test_pax_preview`, `test_trade_v2_preview`).
- **13 neue SAP-02-Tests**: fünf gleiche Codes/nur ein oder zwei echte Needs, 17 Albumkontexte, präziser Albumcode, robuste OR-Suche, Username, Suchtreffer-vor-Deal-Ranking, Trefferlimit nach Give-Kapazität, Albumfrage versus Filter, reale EM24/WM26-Codeformate, besessene Needs, Give-/Receive-Reservations, 1/5/17 tatsächlich angelegte Memberships, identische Einstiegsrouten, Stale-Deal von 7 auf 6 und anschließend 0, unabhängige Privacy/Trade-Freigabe.
- Bestehende SAP-Suchtests und PROFILE-TRADE-01 im Release-Gate. Nur die ausdrücklich ersetzte SAP-01A-Rankingassertion wurde angepasst.
- Browser SAP-01A-Interaktionen: Pagination 50/Mehr anzeigen, Auswahl Alle/Keine, Code-/Namenssuche, separate Null-Deal-Sektion, Kontextübergabe ans Profil, keine DB-Schreibrequests.
- Browser PROFILE-TRADE-01: SAP → Profil → Auto/Manuell, Sammlung unabhängig vom Tradefilter, eigener Account ohne Fremdprofil-Tradeblock, Serverprüfung der Auswahl; nur vier erwartete read-only `/manual/check`-POSTs, keine Anfragen.
- Browser SAP-02: **375/390/430/1280 px**, 1/5/17 ausgewählte Alben, 17 geöffnete Albumzeilen, je 44–80 px Höhe, Checkbox ≤24 px, genau ein Suchfeld, keine Top-3-Fläche, verschiedene Sucharten, geöffnete Profil-Albumauswahl, Post-it bei Scrollpositionen 0/400/Seitenende, Prüfen-Button nicht verdeckt, kein horizontaler Overflow.
- **TRADE-01–11 komplett bestanden**, inklusive Lifecycle, Q2, Slot-/Amendment-Regeln, manuelle Auswahl, Eingabemethoden und responsive UI. Logs enthalten die einzelnen Modellassertionszahlen.
- **28 kanonische Stack-Paritätsfälle bestanden** (7 Mengen × 4 Breiten). Produktiver Wall-Cap 5 und Trade-Cap 10 weiterhin geprüft. Keine kanonische Wall-/Listen-/Stackdatei in SAP-02 verändert.
- `git diff --check` und `git diff --cached --check`: sauber. Index leer.

Ausführung:

```text
.venv/bin/python -B /private/tmp/integration01-run-gate.py
.venv/bin/python -B -m unittest tests.test_pax_preview tests.test_trade_v2_preview
.venv/bin/python -B /private/tmp/sap02-preview-gates.py
.venv/bin/python -B tests/research/check_sap02.py check /private/tmp/sap02-browser.db
```

Die letzten drei Befehle verwendeten den isolierten Checkout als Arbeitsverzeichnis und den absoluten Pfad zur Projekt-venv. Browser gegen synthetische Server 18081/18095. Server 18095 nach erfolgreichem Gate beendet.

Während der Entwicklung korrigiert und danach erfolgreich erneut geprüft: veraltete Home-/Rankingassertionen gemäß neuem Vertrag; fehlendes `total` der neu angelegten synthetischen Albumfixture; globale Input-Breite/Min-Breite/Padding im lokal begrenzten Albumwähler. Kein offener Testfehler.

Evidenz: `release-results.json`, `release.log`, `preview-unit.log`, `trade-regressions.json`, `trade-regressions.log`, `canonical-parity.json`, `results.json`, `sap-regression/browser-results.json`, `profile-regression/results.json` im Artifact-Ordner.

## 12. Screenshots

Unter `tests/research/artifacts/sap-02/`:

- `sap-390.png`, `sap-1280.png`: produktiver SAP-Einstieg mit synthetischen Daten.
- `albums-open-390.png`, `albums-open-1280.png`: geöffnete Tauschalben-Auswahl.
- `albums17-390.png`, `albums17-1280.png`: vollständige Seite mit 17 Alben.
- `manual-sticky-390.png`, `manual-sticky-1280.png`: bestehender Post-it am Listenende.
- Entsprechende Dateien für 375 und 430 px sowie Profil-/Auto-/manuelle Screenshots und TRADE-01–11-Evidenz in Unterordnern.

390/1280-Einstieg, geöffnete Albumauswahl und mobilen Sticky-Post-it zusätzlich visuell geprüft.

## 13. Geschützte Datenbanken

**Alle 16 geschützten lokalen DB-/Backup-Dateien bytegleich zum Beginn dieses Auftrags.** Keine neue DB im Repository. Migration 0022 weder lokal noch produktiv ausgeführt. Die echte DB bleibt auf Schema 20; SAME_ALBUM_ONLY-Fallback der bestehenden Präferenzdomain bleibt unverändert. Vollständige Vorher-/Nachher-SHA256: `protected-db-hashes.json`.

Die 16 umfassen die zuvor 15 geschützten DBs plus das bereits vor SAP-02 vom Nutzer freigegebene Backup vor dem eigenen Passwortreset. Der Reset gehört nicht zu SAP-02; dieser Auftrag verändert kein Passwort und keine Daten.

| Datei | SHA256 vorher = nachher |
|---|---|
| `App/Database/sammlr_reference_s00.db` | `21774db638fa8f700b4e831d56e14739acb1b74e4d307852e8a7b2c474811971` |
| `App/Database/s20_coverage_debug.db` | `dadac1c379a45ec0245208293aef3eccd732cc41b3c07e4b8c523cace1444d9e` |
| `App/Database/sammlr.db` | `4b706e02c57d01b64bf311f6bdef25800fe27c38848f939c4176dbde45a54d24` |
| `App/Database/Database:Backups/collectr_backup_before_trophy_cleanup.db` | `447a9164ba7772b04ee12ccfc5c65a39720cf1f1776c86002ffe3161fded287e` |
| `App/Database/Database:Backups/collectr_backup_popup_clean.db` | `6bcb037730123b78fe756856bc8735a7358f185872040d179fc34a5ebb1d51e3` |
| `App/Database/Database:Backups/collectr_backup_before_users.db` | `f4796d18d36a6a0f1625bfc7eb2fb926006ef50d534472ca32a3cfbe0a4e8039` |
| `App/Database/Database:Backups/collectr_backup_trophy_tabs_visual_runs.db` | `6bcb037730123b78fe756856bc8735a7358f185872040d179fc34a5ebb1d51e3` |
| `App/Database/Database:Backups/collectr_backup_users_trophy_clean_runs.db` | `602883a8538f9377847542c1c7c969d326adc7d071c6cca2ff5822eca1b96f8f` |
| `Backups/sammlr_local_pre_v0005_20260803_211622.db` | `cb69ff4407f6c9c166e84d472f8a89b32e33692cde109b437b1d60ebb0aa0a01` |
| `Backups/sammlr_local_pre_v0003_20260802_091642.db` | `ff96c936c3a4fe86433f3cd42dfbc51e24a034a02c147ccc5e40aefdb436c5d8` |
| `Backups/sammlr_before_valy_password_reset_20261004T084422847704Z.db` | `0748a936250c2771173a5bfb3853b7718c79e376fed25409438d0927062c5eb1` |
| `Backups/collectr_2026-06-02_22-14-58.db` | `474f1bf0573717c1594a5cb6311d1f8ea99c461357715e1e43315f6c3285654c` |
| `Backups/sammlr_local_pre_v0006_20260808_010509.db` | `159cc562b648ebf567878622b4db815cc2acf86601b9d2bc2a586793b8cd5912` |
| `Backups/sammlr_local_pre_v0004_20260802_232331.db` | `2063fddc7991cd699dc5321f8210b1278ee8180a96dbaf0ab0a89a87aafcd466` |
| `Backups/sammlr_local_pre_v0007_20260808_023853.db` | `752292434f44c637f7518c71494d5b7f787d786d881bca06024b8547c732eac8` |
| `App/Database/collectr.db Kopie` | `f25e1b02975da4cda2dfc0e217fe30ae294030dbb9fc0b7a5b6d4b93318f5e4a` |

## 14. Gitstatus

HEAD unverändert `89c957de0b3ab9f412c6d8f6648cb00f3184a051`. Index leer. Der bereits vorher stark veränderte Arbeitsbaum bleibt erhalten; diese Arbeit wurde nicht gestaged. Vollständiger aktueller Status unter `tests/research/artifacts/sap-02/git-status.txt`. Kein Commit, Push oder Deploy.

## 15. Bewusste Grenzen

- Noch kein abschließendes visuelles Trade-Redesign und keine neue Metadaten-/Spielernamensuche.
- Der vorhandene automatische SmartDeal-Mindestumfang 5 bleibt; kleinere gültige Möglichkeiten bleiben manuell erreichbar.
- Manuelle Auswahl prüft serverseitig, erstellt weiterhin keine produktive Anfrage; keine neue Lifecycle-/Slot-/DB-Mutation.
- Die aktuelle zentrale Domain bildet kanonische offene Sammelbedarfe ab; SAP erfindet keine neue Mehrfachbedarfsregel.
- Der vom Nutzer bereits akzeptierte kanonische Mengenbubble-Bestandsfehler bleibt unverändert.
- Die 14 zusätzlichen Alben der 17-Alben-Begehung sind ausdrücklich synthetische Layout-/Membership-Fixtures, keine neu eingeführten produktiven Kataloge.
- Der vorhandene reale Server auf Port 8080 wurde nicht neu gestartet. Die Begehung verwendet denselben aktuellen Produktcode mit synthetischen Daten auf 18081.

## 16. Begehung

**http://127.0.0.1:18081/sap-fixture-login**

Einmaliger Einstieg in den ausschließlich synthetischen Testaccount, danach direkt `/tauschen`. Testlogin existiert nur im Research-Harness, nicht in der produktiven App. Der Server bleibt zur Begehung erreichbar.

SAP-02 ist zur gemeinsamen funktionalen Begehung bereit. Danach keine weiterführende Integration begonnen.
