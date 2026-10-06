# TRADE-LIFECYCLE-00 — Spezifikationsaudit

Datum: 2026-10-06. Ausgangs-HEAD verifiziert: `e20a8c4e84f2adb83b2f4f3f870846267713a4c1` (`feat: integrate sticker exchange program`). Ausschließlich Analyse und sechs neue Markdown-Dokumente. Kein Codeimport/Appstart, kein Lifecycle-Testlauf, kein DB-SQL oder Schemaeingriff.

> Historischer Auditstand, durch §16 / LIFECYCLE-00B fortgeschrieben: D02, D03 und der Regelteil D08 sind inzwischen entschieden. Die folgende ursprüngliche Konfliktübersicht dokumentiert den 00-Befund; aktueller Entscheidungsstand und Integritätsnachweis stehen in §15 und im aktualisierten Vertrag. Frühere offene Fragen sind keine erneuten Freigabeanforderungen.

## 1. Ist der Vertrag intern widerspruchsfrei?

**Aktueller Status nach 00B: TRADE-LIFECYCLE-V1 ist fachlich geschlossen.** Die folgenden ursprünglichen Befunde dokumentieren die Herleitung; alle Startblocker von L01 sind durch 00A/00B entschieden, spätere Detail-/Launch-Gates bleiben bestehen. Explizite neue Produktentscheidungen superseden die älteren Zielregeln nur für einen neuen zukünftigen Contract-Type. Nicht entschiedene Details sind D01–D09 mit Phase/Gate; kein frei erfundener Default kaschiert sie. Deshalb keine Freigabe von LIFECYCLE-01 durch dieses Audit.

Die komplette Analyse-/Spezifikationsaufgabe ist bearbeitet, einschließlich der verlangten offenen Fragen. „Offen“ bedeutet nicht, dass 3/72h/Fotos oder der akzeptierte SAP erneut zur Diskussion stehen. Die neue Fachentscheidung ist dokumentiert; eine sichere produktive Umsetzung benötigt die benannten Ergänzungen.

## 2. Echte Konflikte und Lücken

| Konflikt | Einordnung |
|---|---|
| Alte 3/3-operative Slots versus nur offene eigene Anfragen | Durch neuesten Auftrag entschieden: outgoing pending maximal 3, incoming/accepted nicht künstlich begrenzt. Kein Rest-Slot bis Versand. |
| Alter expliziter V1-24h-Vertrag, Legacy-S22 tatsächlich 48h, Preview 24h versus neue 72h | Neuer Vertrag 72h; alte Persistenz und Requests unverändert. Keine pauschale Änderung einer gemeinsamen Konstante. |
| Alte beidseitige Pending-Bindung versus fremden Bestand nicht ohne Zustimmung blockieren | Neuer Sender hält nur seine Give-Supply. Zentrale Incoming-Need- und Mischbetriebssemantik durch 00B/D01 entschieden. |
| Preview/alter eigener Pack- und Adress-Release versus neue gegenseitige Fotobarriere | Neuer Pflichtfoto-/Partnerprüfungsprozess und gemeinsame automatische Adressfreigabe; kein alter eigener Releasebutton genügt. |
| Receipt ohne Klick versus notwendiger physischer Abgang | Ankunft erlaubt; keine gefälschte Selbstauskunft. Vollerhalt kann fehlenden Abgang genau einmal nachholen. Teil-/Fehlmengen und widersprüchlicher gepflegter Bestand benötigen D02. |
| 72h „Vorbereitung“ versus 72h „Packen/Kontrolle“ | Nicht eindeutig, ob rechtzeitiger eigener Upload genügt oder Gegenprüfung innerhalb derselben Frist erforderlich ist: D03. |
| Änderung nach Annahme versus Fristen, Kontrolle und bekannt fehlender Ware | Versionierte Zustimmung ist klar; Fristneustart/Abbruchrechte und Phantom-Supply nach Freigabe fehlen: D04/D06. |
| Frühe individuelle Bewertung versus Blindheit bis fremder Frist | Kein fremder Empfang → noch keine laufende fremde 14-Tage-Frist; automatische Veröffentlichung wäre erfunden: D07. |
| Endliche Problemabwicklung versus später tatsächlicher Empfang | Adminautorität, Frist und Mengen-/Ratingwirkung späterer Ankunft fehlen: D09. |

Zusätzlich: D05 Adressänderung/Widerruf nach Freigabe und D08 geänderte Account-/Pool-/Cross-/Blockregeln im bereits angenommenen Vertrag. Die aktuelle manuelle `Receive<=Give`-Regel bleibt erhalten; die „1:1“-Beispiele sind keine globale neue Restriktion.

## 3. Entscheidungen vor LIFECYCLE-01

Aktueller Stand nach 00B: Keine bekannte fachliche Entscheidung blockiert LIFECYCLE-01. D01 ist verbindliche mengenbasierte Option A; D02, D03 und der Regel-Snapshot D08 wurden in 00A entschieden. Ein gesonderter Implementierungsauftrag fehlt weiterhin; 00B beginnt L01 nicht.

Weitere Entscheidungen vor ihren Folgepaketen: D04 spätestens Annahme-/Abbruch- bzw. Pack-/Amendmentintegration; D05 vor Adresse; D06 vor Packfehlmengen; D07 vor Bewertung; D09 vor produktiver Problembeendigung und Abschluss. Vollständige Frage-/Empfehlungs-/Gate-Matrix im [Vertrag §14](TRADE_LIFECYCLE_V1_CONTRACT.md#14-entscheidungsstatus-und-spätere-detailgates).

## 4. Bereits produktive Bausteine

Produktive Source enthält Legacy-Anfrage-/Accept-Routen, mengenbasierte Reservations, eigene Versandbuchung, Empfangs-/Teilbuchung, Problembehandlung, Historien-/Inventory-Guards, 1–5-Ratings und typisierte Notifications. Expliziter SmartDeal-V1-Request/Accept/Release besitzt eine getrennte Contract-Grenze. Der SAP-/Profil-/manuelle Prüfpfad verwendet aktuelle zentrale TradeV2Domain.

Das ist keine Behauptung, der neue Lifecycle sei bereits produktiv: SAP sendet noch keine neue 72h-Lifecycle-Anfrage; manuelles `/check` validiert nur. Alte Receipt-/Problemservices verlangen Partner-SHIPPED; neue Pflichtfoto-/Adressbarrieren fehlen. Der V1-Dispatch gibt physische Befehle nicht ungeprüft an Legacy weiter. Details mit konkreten Quellen/Funktionen im [Gap-Audit](TRADE_LIFECYCLE_V1_GAP_ANALYSIS.md).

## 5. Nur Preview/Research

`App/trade_v2/` hat GET-Fixtures und lokale JS-Zustände für Requests, operative Slots, Packing, Amendments, Demo-Adressen, Versand, Empfang, Probleme und 3-Sterne-Ratings. Keine produktive DB-/Mehrbenutzertransaktion. Q2 ist dort vorgeführt, aber ohne reale Inventarbuchung. `App/pax/` bleibt historischer Prototyp. Wiederverwendbare manuelle Präsentation ist keine automatische Übernahme dieses Zustandsmodells.

## 6–7. Fehlende Persistenz und spätere Migrationen

Fehlend: neuer Contract-Type, Offer-/Counter-/Dealrevisionen, einseitige Pending-Bindung und passende zentrale Need-Projektion, eigene Fristen/Remindernachweise, Fotos/Reviews, konkrete Adresssnapshots/Freigaben, evidenzbasierte Richtungs-/Mengenledger, differenzierte Problemabschlüsse, individuelle blinde Ratingfenster/Tags und Zentrale-Projektionen.

Vorhanden sind `trades`, `trade_positions`, `trade_events`, `trade_reservations`, Shipping-/Receipt-Status, Receipt-Reports/-Positions, `trade_ratings`, Notifications und Inventory-History. Ihre Constraints/Semantik begrenzen direkte Wiederverwendung. Später additive, versionierte Schemafähigkeit erforderlich; 0021 lässt aktuell nur legacy/smartdeal_v1 zu, 0022 ist ausschließlich Cross-Präferenz. Keine neue Migrationsnummer/DDL geschrieben und keine bestehende Migration ausgeführt.

## 8. Concurrency / Atomicity

Fachliche Grenzen dokumentiert für parallele Accepts auf dieselbe Kopie, Send versus Accept, Dreierlimit, Accept versus Expiry/Withdraw/Counter, Preview-Änderungen, Foto-/Adress-/Amendmentversionen, Shipment versus Cancel/Receipt, überlappende Teilmengen und blinde Veröffentlichung. Read-check und Schreiben müssen dieselbe Transaktionsgrenze haben.

32 explizite Transitionen T01–T32, Kerninvarianten A–N und weitere S01–S12; Positionen immer Album+Code+Richtung+Version. Exactly-once-Abgang muss Shipment- und Receipt-Evidence gemeinsam abdecken, Zugang nur neue akzeptierte Deltas. Keine verschachtelte Selbst-Commit-Kette, kein idempotenzloser Refresh, keine pauschale Mengenkappung.

## 9. Datenschutz-/Launch-Blocker

Separate Prüfung für Speicherung/Freigabe/Retention von Versandadressen, Kontrollfoto-Retention und personenbezogene Foto-Inhalte, freiwillige externe Kontakte, Rating/Reputation, Moderation/Support, Minderjährige, Haftung bei Verlust, etwaigen späteren Porto-/Frankierverkauf sowie Datenschutzinformation/Einwilligungs-/Vertragslogik. Keine rechtliche Bewertung oder erfundene gesetzliche Frist. Partnerzugriff, Supportzugriff, normale UI-Sichtbarkeit und physische Löschung ausdrücklich getrennt.

## 10. Folgepakete

L01 Vertrags-/Persistenzgrundlage → L02 einseitige Anfrage/72h/Reservations → L03 Accept/Counter/Recheck → L04 Packen/Fotos/Reduktion → L05 Adresse → L06 Versand/Abgang → L07 Empfang/Teilprobleme/Zugang → L08 Abschluss/blinde Bewertung → L09 Zentrale-Projektionen.

Verbesserte Sicherheitsgrenze: zentralen Supply-/Need-Reader gleichzeitig mit neuen Holds anschließen; keine reale Versandfreigabe ohne funktionsfähigen anschließenden Empfangspfad. L06/L07 dürfen nicht als unvollständige physische Journey für reale Nutzer aktiviert werden. [Detaillierter Plan](TRADE_LIFECYCLE_V1_IMPLEMENTATION_PLAN.md).

## 11. Exakte neue Dateien

1. `docs/TRADE_LIFECYCLE_V1_CONTRACT.md`
2. `docs/TRADE_LIFECYCLE_V1_STATE_MACHINE.md`
3. `docs/TRADE_LIFECYCLE_V1_INVARIANTS.md`
4. `docs/TRADE_LIFECYCLE_V1_GAP_ANALYSIS.md`
5. `docs/TRADE_LIFECYCLE_V1_IMPLEMENTATION_PLAN.md`
6. `docs/TRADE_LIFECYCLE_00_AUDIT.md`

Keine optionalen JSON-/Schema-/Runtime-Artefakte angelegt. Prüfhashes liegen außerhalb des Repositorys unter `/private/tmp/trade-lifecycle00/`.

## 12. Prüfungen und Schutzgrenzen

- Ausgangs-HEAD und leerer getrackter Arbeitsbaum/Index vor Analyse geprüft.
- Bestehende Verträge, produktive Routes/Services, SQL-Migrationen und Preview-JS ausschließlich gelesen.
- Fachliche Walkthroughs: normale beidseitige Abwicklung; ungültiges Original mit einmaligem Counter; zwei parallele Annahmen; Same-/Cross-Reduktion; Receipt vor Versandklick; Teil-/Falsch-/Schadensempfang; einseitiger Abschluss; Nichtankunft und späterer Eingang; individuelle blinde Bewertung.
- Dokumentprüfung: alle sechs Dateien, interne/referenzierte Dateilinks, T01–T32 und A–N/S01–S12 vollständig; keine zusätzliche Runtimefreigabe aus offenen Gates.
- Keine Unit-/Browser-/Release-Tests ausgeführt, weil keine Runtimeänderung und ausschließlich lesender Codeaudit beauftragt. Frühere Savepoint-Tests nicht als neu ausgeführte Lifecycle-Tests ausgegeben.
- Alle **2.799 versionierten Dateien** nach Abschluss gegen SHA256-Baseline geprüft und unverändert; alle **16 geschützten DBs** vorher/nachher bytegleich. Nur Dateibytes gelesen, keine DB-Verbindung/Migration/Bestandsbuchung.
- Alle sechs neuen Markdown-Dateien separat mit `git diff --no-index --check` geprüft: ohne Befund. `git diff --check` und `git diff --cached --check` ebenfalls ohne Befund; sämtliche referenzierten Dateien vorhanden.

## 13. Gitstatus und Ende

HEAD bleibt `e20a8c4e84f2adb83b2f4f3f870846267713a4c1`. Getrackter Arbeitsbaum unverändert, Index leer. Genau die sechs genannten Dokumente als neue ungetrackte Auftragsdateien; bereits vorhandene andere ungetrackte/ignorierte Dateien unberührt. **Kein Commit, kein Push, kein Deploy, keine Runtime-/DB-/Schemaänderung. Kein LIFECYCLE-01 begonnen.**

## 14. Abdeckung des Auftrags

| Auftragsabschnitt | Dokumentation |
|---|---|
| 1 Grundprinzip | Vertrag §2; Plan L09 |
| 2 Anfragequote | Vertrag §3; Invarianten S01; D01 Mischbetrieb |
| 3 einseitige Mengenreservierung | Vertrag §3; A–C; T01/T04 |
| 4 SAP-Auswirkung | Vertrag §3; Gap zentrale Projektion; Plan L02 |
| 5 72h/Withdraw/Decline/Expiry | Vertrag §4; T07–T09 |
| 6 Reminder | Vertrag §4; T32; Eventmodell |
| 7 frische Annahme | Vertrag §5–6; T02/T03/T05/T06 |
| 8 einmaliges Gegenangebot | Vertrag §5; Invariante M |
| 9 unbeteiligte Änderungen | Vertrag §5; Concurrency-Matrix |
| 10 Annahme | Vertrag §6; Invarianten D/E |
| 11 Packfrist | Vertrag §6; D03 explizite Unklarheit |
| 12 Packliste | Vertrag §6; T10 |
| 13 Pflichtfotos | Vertrag §6; Plan L04 |
| 14 gegenseitige Sichtbarkeit | Vertrag §6; T11 |
| 15 Fotoprobleme | Vertrag §7; T12–T14 |
| 16 fehlender Sticker / Gegenstück | Vertrag §7; Invariante K; D06 |
| 17 Änderung nach Annahme | Vertrag §7; T15–T19; D04 |
| 18 Fotos löschen | Vertrag §8/15; Launch-Gates |
| 19 Adresse | Vertrag §9 |
| 20 Adressvorlagen/Auswahl | Vertrag §9; D05 |
| 21 automatische Freigabe | Vertrag §9; Invariante I; T18 |
| 22 externe Kontakte | Vertrag §9/15, kein Pflichtbestandteil |
| 23 Versandfrist | Vertrag §10; T21/T32 |
| 24 Confirm Versand | Vertrag §10; T20 |
| 25 Bestandsabgang | Vertrag §10; Invariante F; Buchungsmatrix |
| 26 einseitig versendet | Vertrag §10; Invariante J |
| 27 Eingang ohne Klick | Vertrag §11; T22–T24; D02 |
| 28 Empfang | Vertrag §12; Invariante G |
| 29 Lieferproblem | Vertrag §12; T24/T27 |
| 30 Teilempfang | Vertrag §12; Buchungsmatrix; S09 |
| 31 Nichtankunft / spätere Ankunft | Vertrag §12; T25/T26 |
| 32 beidseitiger Abschluss | Vertrag §13; T28/T29; D09 |
| 33 individuelle Bewertung | Vertrag §13; T30; Invariante N |
| 34 blinde Bewertung / 14 Tage | Vertrag §13; T31; D07 |
| 35 Zuverlässigkeit separat | Vertrag §13; Ereignismodell |
| 36 Zentrale / Listen statt Einzelpostits | Vertrag §2; Plan L09 |
| 37 Zustandsmaschine | Zustandsdokument §§1–5 |
| 38 Invarianten A–N | Invarianten §2 |
| 39 Idempotenz | Invarianten §§3/6 |
| 40 Concurrency | Invarianten §5 |
| 41 Recht/Datenschutz offen | Vertrag §15; Audit §9 |
| 42 Nicht-Ziele | Vertrag §15; Plan §5 |
| 43 Codeaudit | Gap-Analyse §§1–6 |
| 44 Ergebnisdateien | Audit §11 |
| 45 Implementierungsplan | Plan L01–09 und Freigabegates |
| 46 Abschluss/STOP | Audit §§1–13; Abschlussbericht |

## 15. LIFECYCLE-00A — Fortschreibung

Reiner Sourceaudit und Dokumentation auf unverändertem HEAD `e20a8c4e84f2adb83b2f4f3f870846267713a4c1`. Die [Need-Claims-Analyse](TRADE_LIFECYCLE_00A_NEED_CLAIMS.md) beantwortet alle zehn Ist-Fragen, bewertet die Zielarchitektur und vergleicht drei Optionen.

**Ergebnis:** Need-Claim ist eine abgeleitete binäre Incoming-Bindung, kein eigenes DB-Objekt. SAP/SmartDeal berücksichtigt sie, ältere Matching-/Accept-Pfade nicht gleichwertig. Gemeinsame physische Inventory-/Reservation-Infrastruktur ist nötig; ein unveränderlicher neuer Contract-Type und getrennte Commands verhindern Vertragsvermischung. Legacy kann unter diesen späteren Integrationsvoraussetzungen nach alten Regeln auslaufen. Keine heute schon vorhandene vollständige neue Lifecycle-Fähigkeit behauptet.

**Historische Empfehlung aus 00A, durch 00B verbindlich gewählt:** Neue offene Anfrage bindet eigene Receive-Needs zusätzlich zur eigenen Give-Supply; keine fremde Bindung. Alternative B bindet neue Needs erst bei Accept; C wartet den Alt-Auslauf vollständig ab. Die damalige Pending-Need-Frage ist durch 00B entschieden; Option B/C sind keine offenen Alternativen mehr. Keine globale rückwirkende Need-Unique-Regel für alte Accepts erfinden; deren mögliche zusätzliche Zusagen sind von physischer Doppelreservierung zu unterscheiden.

**Verbindlich übernommen:** D02 Empfang führt tatsächlichen Abgang und akzeptierten Zugang atomar/idempotent nach, Richtung systemisch versendet/angekommen; D03 eigene Vorbereitung 72h ab Annahme, gegenseitige Prüfung getrennt ohne automatische harte Abbruchfrist; D08 aktuelle Prüfung vor Accept, eingefrorener Regel-Snapshot danach einschließlich Reduktionen. Konkrete Snapshotdaten im Vertrag §6a. Spätere Detail-/Datenschutzgates bleiben ohne vorgezogene Runtimefreigabe.

### Exakter Dokumentumfang

Geändert, bereits vor diesem Auftrag ungetrackt:

- `docs/TRADE_LIFECYCLE_V1_CONTRACT.md`
- `docs/TRADE_LIFECYCLE_V1_STATE_MACHINE.md`
- `docs/TRADE_LIFECYCLE_V1_INVARIANTS.md`
- `docs/TRADE_LIFECYCLE_V1_GAP_ANALYSIS.md`
- `docs/TRADE_LIFECYCLE_V1_IMPLEMENTATION_PLAN.md`
- `docs/TRADE_LIFECYCLE_00_AUDIT.md`

Neu: `docs/TRADE_LIFECYCLE_00A_NEED_CLAIMS.md`.

### Abschlussprüfungen 00A

Prüfbaselines außerhalb des Repositorys: `/private/tmp/trade-lifecycle00a/`. Alle 2.799 versionierten Dateien unverändert, alle 16 geschützten DBs gegenüber dem unmittelbar vor 00A erfassten SHA256 unverändert. Keine DB geöffnet, keine Migration angelegt/ausgeführt. Nur die sechs erlaubten Dokumente geändert und das siebte neu erstellt; keine zusätzliche ungetrackte Auftragsdatei. Alle lokalen Dateiverweise geprüft; Whitespaceprüfung aller sieben Dokumente sowie beide Git-Diffchecks ohne Befund. Keine Runtime-Tests erforderlich oder ausgeführt.

HEAD unverändert; Index unverändert und leer, getrackter Arbeitsbaum sauber. Zum Abschluss von 00A waren die sieben Dokumente ungetrackt; vorherige übrige ungetrackte Dateien bleiben bestehen. Kein Staging, Commit, Push oder Deploy. LIFECYCLE-01 nicht begonnen.

## 16. LIFECYCLE-00B — Fachlicher Abschluss und Dokumentationssicherung

**TRADE-LIFECYCLE-V1 — FACHLICH GESCHLOSSEN.** Option A ist verbindlich, einschließlich mengenbasierter Receive-Need-Claims. Keine bekannte fachliche Entscheidung blockiert aktuell LIFECYCLE-01. Dies bedeutet weder Implementierung noch Produktions-, Migrations- oder Deployfreigabe. D04–D07/D09 und verbleibende Zugriffs-/Rechts-/Datenschutzfragen bleiben Gates für die jeweiligen späteren Funktionen und den Launch.

Alle sieben Dokumente wurden konsistent aktualisiert: eigenes Give plus eigener Receive-Claim bei Send; keine Partnersupply-Bindung; Claim-/Hold-Freigabe bei terminalem Pending-Ausgang; atomare Überführung bei Accept; Need 2 minus Claim 1 lässt Rest 1; unveränderlicher neuer Contract-Type; gemeinsame reale Supply mit Legacy ohne Migration alter Need-Semantik. Der heutige binäre Reader bleibt ausdrücklich Ist-Befund und technische Lücke, kein V1-Ziel.

Drei eigene offene Anfragen, eingehend unbegrenzt, ein Gegenangebot, 72h Anfrage, 72h eigene Vorbereitung, getrennte Fotoprüfung ohne automatischen Fristabbruch, 72h Versand ab gemeinsamer Freigabe, eingefrorener Regel-Snapshot und atomarer Receipt-Evidence-Pfad bleiben verbindlich.

### Prüf- und Commitumfang

Ausschließlich diese sieben Dateien dürfen im Dokumentationscommit liegen:

1. `docs/TRADE_LIFECYCLE_V1_CONTRACT.md`
2. `docs/TRADE_LIFECYCLE_V1_STATE_MACHINE.md`
3. `docs/TRADE_LIFECYCLE_V1_INVARIANTS.md`
4. `docs/TRADE_LIFECYCLE_V1_GAP_ANALYSIS.md`
5. `docs/TRADE_LIFECYCLE_V1_IMPLEMENTATION_PLAN.md`
6. `docs/TRADE_LIFECYCLE_00_AUDIT.md`
7. `docs/TRADE_LIFECYCLE_00A_NEED_CLAIMS.md`

Vor Staging: HEAD `e20a8c4e84f2adb83b2f4f3f870846267713a4c1`, Index leer. Prüfbasis außerhalb des Repositories `/private/tmp/trade-lifecycle00b/`: 2.799 bereits versionierte Dateien und 16 geschützte DBs per SHA256; keine Runtime-, DB- oder Migrationsänderung. Dokumentlinks, Whitespace und neuer Dokumentinhalt auf Secrets/Privatdaten geprüft. Nur synthetische Produktbeispiele, Source-/Schemanamen und technische Git-/Prüfpfade; keine DB-Inhalte, Adressen, Credentials oder Nutzerexporte übernommen. Keine Runtime-Test-Suite erforderlich/ausgeführt.

Autorisierte Sicherung: genau ein Commit `docs: define trade lifecycle v1 contract`, danach normaler Push auf `origin/feature/wm-special-trophies` ohne Branchwechsel, Rebase, Merge oder Force. Commit-Dateiliste und Remote-HEAD werden nach Ausführung überprüft; der finale Hash und die tatsächlichen Ergebnisse stehen im Abschlussbericht, um keinen zweiten selbstreferenziellen Auditcommit zu erzeugen. Kein Deploy, kein LIFECYCLE-01.
