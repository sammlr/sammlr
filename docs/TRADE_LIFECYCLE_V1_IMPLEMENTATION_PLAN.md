# Trade Lifecycle V1 — Kleine sichere Folgepakete

Ausschließlich Planung. Kein Paket ist durch dieses Dokument zur Runtime-Ausführung freigegeben. Ausgangsstand `e20a8c4e84f2adb83b2f4f3f870846267713a4c1`; [Vertrag](TRADE_LIFECYCLE_V1_CONTRACT.md), [Auditlücken](TRADE_LIFECYCLE_V1_GAP_ANALYSIS.md).

## 1. Gate vor LIFECYCLE-01

**TRADE-LIFECYCLE-V1 — FACHLICH GESCHLOSSEN.** Keine bekannte fachliche Entscheidung blockiert L01. Die Implementierung erfordert weiterhin einen gesonderten Auftrag. Verbindliche Grundlage:

- **D01 entschieden (00B):** Option A. Eigene Give-Mengen und eigene Receive-Need-Mengen gleichzeitig bei Send binden; beide bei terminalem Pending-Ausgang lösen und bei Accept atomar überführen. Kein fremder Hold, keine binäre Need-Begrenzung.
- **D02, D03, D08-Regelteil sind entschieden:** atomarer Receipt-Evidence-Abgang/Zugang; 72h nur eigene Vorbereitung, separate Fotoprüfung ohne automatische Abbruchfrist; eingefrorener Regel-Snapshot bei Accept auch für Reduktionen.
- Technische Ausarbeitung des neuen unveränderlichen Contract-Types, gemeinsamer Supply-/Need-Projektion, Exactly-once-Mengenledger und Snapshotfelder gemäß Vertrag §6a. Keine erneute Produktfreigabe für die drei entschiedenen Regeln erforderlich.

D04-Abbruchautorität vor Annahme-/Cancel-Integration; übrige Detailgates je Paket unten. Datenschutzentscheidungen sind Launch-Blocker, nicht durch einen SQL-Entwurf erledigt. Bei noch offenen Details kann ausschließlich nach separatem Auftrag weitere Spezifikation erfolgen; dieses Paket beginnt keine Skeleton-Implementierung.

## 2. Reihenfolge und vertikale Schnitte

| Paket | Umfang / Persistenzfähigkeit | Vorbedingungen | Abnahme / sichere Grenze |
|---|---|---|---|
| **LIFECYCLE-01** | Neuer Contract-Type, stabile Richtungen, Offer-/Dealversion, Command-/Eventidentität, gemeinsamer Mengenledger-/Hold-Bezug und Zeitmodell; additive Migrationen erst entwerfen/testen | entschiedene D01/D02/D03/D08 umsetzen | Frischer synthetischer Schemaaufbau, alte Typen/Instanzen unverändert, unbekannte Typen abgewiesen, Rollback/FK/unique-Tests. Noch kein neuer produktiver Send-Button. |
| **LIFECYCLE-02** | Anfrage senden, eigene Give-Mengen reservieren und Receive-Need-Mengen claimen, outgoing-open 3, incoming unbegrenzt, absolute 72h, Withdraw/Decline/Expiry, Reminder-Hooks; zentralen SAP-/Need-Readadapter in demselben Schnitt erweitern | L01, D01 | Parallel-Send/Accept-Supply-Simulation, Mengen- und Quote-Races, Fristgrenzen/Retry. Neue Holds müssen sofort in SAP sichtbar sein; keine temporäre Doppelengine. |
| **LIFECYCLE-03** | Exakte aktuelle Annahme mit eigenen Hold-Credits, beidseitige Bindung, genau ein Counter mit atomarem Rollen-/Holdwechsel, keine stille Paketänderung; Vertrag/Annahmezeit | L02, D04-Abbruchrechte; eingefrorener D08-Snapshot | Unbeteiligte Bestandsänderung erlaubt; konkurrierende Requests, Gegenangebot-versus-Accept, asymmetrische manuelle Perspektive, ungültiger Counter endet. Kein normaler physischer Lifecycle freigeschaltet. |
| **LIFECYCLE-04** | Eigene mengenrichtige Packliste, Pflichtfotos/Uploadschutz, gegenseitige Sichtbarkeit, versionierte Reviews, Problem-/Korrekturweg und beidseitig bestätigte Reduktion | L03, D04/D06; entschiedene separate D03-Prüfphase; Upload-/Retentionzugriff konzeptionell geklärt | Große Deals/viele Fotos, Direkt-URL-Auth, keine einseitige Sichtbarkeit, 23→22-Regelprüfung, alte Fotos/Review entwertet, Phantom-Supply ausgeschlossen. Noch keine automatische Adressanzeige. |
| **LIFECYCLE-05** | Optionale Adresse wählen/ändern/neue Vorlage, konkreter Trade-Snapshot, Information vor Reviewbestätigung, beidseitige automatische Freigabe und 72h-Versandanker | L04, D05, Adress-/Datenschutzfreigabe | Kein Zugriff bei Anfrage/Accept/einseitiger Vorbereitung; parallele Foto-/Adressänderung, Block/Accountende, Widerrufsgrenze; keinerlei öffentlicher Adresspayload. |
| **LIFECYCLE-06** | Bewusstes „Versendet“, eigener exactly-once Abgang und Holdverbrauch, Überfälligkeit, Teilversandschutz; gemeinsamer Abgangsadapter bereits für Receipt-Evidence vorbereitet | L05, entschiedener D02-Receipt-Evidence-Pfad | Send/Cancel-/Amendment-Races, Doppelklick/Timeout, keine automatische Rücknahme, kein Bestand bei Verlust zurück. Noch keine Benutzerfreigabe ohne sicheren anschließenden Empfangspfad. |
| **LIFECYCLE-07** | Ankunft auch ohne Versandklick, genaue Prüfung und akzeptierte Deltas, Wrong/Damaged/Partial, 7-Tage-Nichtankunft, „doch angekommen“, Reconciliation; beide Richtungen getrennt | L06, D02 umgesetzt; D09 soweit für Problemsicherheit erforderlich | Ship/Receipt beide Reihenfolgen/parallel; 30/29/später1; nicht akzeptierter Schaden kein Zugang; kein erfundener Abgang/Restore, Nachweisakteur korrekt. |
| **LIFECYCLE-08** | Richtungs-/Gesamtabschluss und qualifizierte Problembeendigung, unabhängige eigene Ratingberechtigung, 1–5/positive Tags, individuelle 14 Tage, blinde Veröffentlichung/Aggregate | L07, D07/D09, Bewertungs-/Support-Launchprüfung | Nie Gesamtabschluss nach nur einer geklärten Richtung; keine erfolgreiche Kennzeichnung administrativer Probleme; keine Rating-Leaks, keine Automatiksanktion. |
| **LIFECYCLE-09** | Zentrale-Readprojektionen: To-dos, Sendungen, Eingänge, Historie, Mengen-/Deadline-/Problemhinweise und deduplizierte Notification-Hooks | L02–08 | 1 und 30 Trades, rollenrichtige nächste Aktion, kein eigener Zustand neben Domain, Privacy und vollständige Legacy-/SAP-Regression. Kein verpflichtendes Redesign. |

Die Zentrale-Projektionsschnittstelle und Events sollten bereits bei L01–03 fachlich festliegen, damit spätere Screens keine neuen Status erfinden. Die endgültige UI bleibt ein gesonderter Auftrag. Die operative Freigabe von L06 und L07 muss zusammenhängend erfolgen: keine realen Sendungen in einen noch nicht sicher empfangbaren Prozess schicken.

## 3. Technische Integrationsleitplanken

- Ein zentraler Reservation-/Incoming-Adapter für SAP, manuelle Auswahl, Send und Accept. Kein extra Cache, der andere Holds nicht sieht.
- Neue Writers akzeptieren ausschließlich neuen Contract-Type; alte Routes dispatchen eindeutig. Kein alter Versand-/Empfangsservice wird ungeprüft für alle Typen freigeschaltet.
- Bestehende `HistoricalInventoryWriteService`-/Guard-/Eventfähigkeiten bewusst komponieren. Nicht zwei interne Top-Level-Commits für ein fachlich atomares Ereignis verwenden.
- Neue SQL-Migrationen müssen synthetisch, vorwärts/rückwärts soweit verlustfrei und mit bestehenden Datenzuständen getestet werden. Schemakompatibilität, Operational-Rollout, Backup und Datenschutzfreigaben getrennte Schritte; keine lokale/produktive Migration durch LIFECYCLE-00.
- Rücknahme einer Aktivierung darf abgeschickte reale Trades nicht funktionslos zurücklassen. Keine Migration bestehender Legacy/V1-Verträge; im Rollback neue Writes stoppen, bestehende neue physische Verpflichtungen weiter geordnet abwickeln.
- Neue Event-/Ratingprojekte dürfen keinen unbestätigten Versandzeitpunkt, keine falsche Schuldzuordnung oder stillen Erfolg erzeugen.
- Private Medien/Adressen nur zweckgebunden und autorisiert; synthetische Tests ohne reale Nutzerdaten. Keine Fotos/Adressen im allgemeinen Eventlog/Monitoring.

## 4. Gemeinsame Release-Gates je späterem Paket

Neue Invarianten-/Commandtests und echte Mehrverbindungs-Concurrency-Tests; vorhandene Legacy/V1-, SmartDeal-, SAP-01A/02-, PROFILE-TRADE- und Privacy-Gates. Browser erst bei tatsächlich geändertem UI-Paket, dann 375/390/430/1280 px und zugängliche Confirm-/Fehlerpfade. Kanonische Stickerwall/Stack-Caps weiterhin geschützt.

Geschützte DBs vorher/nachher hashgleich; synthetische Test-DBs ausschließlich in autorisierter Testumgebung. Kein verdeckter Schema-Fallback auf reale Entwicklungsdaten. Keine neuen Testausschlüsse, Secrets oder privaten Fixtures. Produktive Aktivierung erst nach geklärten paketbezogenen Domainentscheidungen und vollständigen Datenschutz-/Launch-Gates.

## 5. Nicht in diesen Paketen verstecken

Kein Messenger, Porto-/Post-API-Verkauf, Tracking, Versicherung, Support-Dashboard, öffentlicher Score, Sanktionen, neue SAP-Suchfilter, geändertes Auto-Minimum oder ungefragtes Zentrale-/Trade-Redesign. Dafür höchstens spätere Events/Integrationspunkte vorsehen. LIFECYCLE-00B endet mit versionierter Dokumentation; LIFECYCLE-01 wird nicht begonnen.

## 6. Technische Vertragsidentität und mengenbasierte Grundlage

Für den neuen Typ wird der eindeutige Name `trade_lifecycle_v1` vorgesehen, unveränderlich je Trade; kein Alias für `smartdeal_v1`. Nur Dokumentationsfestlegung, keine Enum-/Schemaänderung. L01 entwirft die autoritative Gesamtbedarfsmenge pro Nutzer/Album/Code und den Adapter zu Bestand, verbindlichen Resteingängen und eigenen Pending-Claims. Die heutige binäre `_pieces`-Projektion reicht nicht aus. Kein neuer zweiter Inventory-Topf; Claim-Ownership und Mengen werden versions-/richtungsgebunden, historische Altverträge nicht migriert.

Vor jeder späteren Aktivierung müssen alle alten und neuen physischen Writers dieselben aktiven Give-Reservations sehen. Legacy-Release darf keine neue fremde Bindung freigeben. Technischer Entwurf, synthetische Migrationsprüfung und gesonderte Aktivierungsfreigabe folgen erst in beauftragten Paketen; keine Datenbankfreigabe durch den geschlossenen Fachvertrag.
