# Trade Lifecycle V1 — Fachvertrag für neue Trade-v2-Vorgänge

Stand: 2026-10-06. Technische Ausgangsbasis: `e20a8c4e84f2adb83b2f4f3f870846267713a4c1`.
„Lifecycle V1“ bezeichnet die erste Fassung dieses neuen physischen Trade-v2-Vertrags, **nicht** `smartdeal_v1`.

**TRADE-LIFECYCLE-V1 — FACHLICH GESCHLOSSEN.** Fassung V1, Abschluss durch LIFECYCLE-00B. Alle derzeit bekannten fachlichen Entscheidungen, die LIFECYCLE-01 blockieren, sind entschieden. Option A ist verbindlich und mengenbasiert. Dies ist keine Implementierungs-, Migrations-, Produktions- oder Deployfreigabe. Spätere Detailgates und Rechts-/Datenschutz-/Launch-Blocker bleiben bestehen. LIFECYCLE-01 wurde nicht begonnen.

## 1. Geltung und Rangfolge

Dieser Auftrag setzt die nachstehenden neuen Regeln ausdrücklich für künftig neu erzeugte Vorgänge unter einem gesonderten Contract-Type durch. Bestehende Legacy-/SmartDeal-V1-Vorgänge und persistierte Snapshots bleiben auf ihrem Vertrag. Herkunft (`MANUAL`, `SMARTDEAL` usw.), Contract-Type, Verhandlungsrevision und physische Richtung sind verschiedene Merkmale. Kein Umschreiben bestehender Vorgänge, kein stiller Fallback unbekannter Vertragstypen auf Legacy.

[SAP-02](SAP_02_AUDIT.md) und [Trade-v2-Präferenzen](TRADE_V2_INTEGRATION_02A_AUDIT.md) bleiben Grundlage für Finden, Auswahl, aktuelle Zulässigkeit und Balance. Die Dokumente [Trade Product Contract V2](TRADE_PRODUCT_CONTRACT_V2.md), [Pax Contract](SAMMLRPAX_CONTRACT_V1.md), [Manual Offer Contract](MANUAL_OFFER_DOMAIN_CONTRACT_V1.md) und [Q1–Q8](TRADE_UX_PO_DECISIONS_Q1_Q8.md) werden hier präzise abgegrenzt, nicht editiert.

| Ältere Regel | Neue Regel ausschließlich für diesen neuen Lifecycle |
|---|---|
| Trade Product V2 §9 / Pax §3: drei operative Slots je Richtung bis eigenem Versand | Nur höchstens drei gleichzeitig offene selbst gesendete Anfragen; keine eingehende Quote und kein Accepted-/Versand-Slotlimit. Annahme beendet das Warten und gibt die Anfragekapazität frei. |
| Trade Product V2 §10 / AC23 / Manual §5: absolute 24 h | Genau 72 h pro abgesendeter Anfrage einschließlich eines Gegenangebots; Legacy/V1 weiter unverändert. |
| Trade Product V2 §7 / Q4 / SmartDeal-V1: beidseitige Bindung bei Submit | Nur Give-Supply des sendenden Nutzers reservieren; fremde Supply erst bei ausdrücklicher Annahme reservieren. Gleichzeitig eigene Receive-Need-Mengen claimen (Option A); keine fremden Need-Claims vor Zustimmung. |
| Frühere Mutual-GO-Mechanik | Neue Anfrage und Gegenangebot brauchen bewusste Empfängerannahme. Gleichzeitiges Absenden ist keine implizite Annahme. |
| Trade Product V2 §8 / PAX-06: eigene Packfreigabe plus gesonderte Adressfreigabe | Pflichtfotos, beidseitige Vorbereitung, gegenseitige Fotobestätigung; danach automatische gegenseitige Freigabe der konkret gewählten Adressen, mit vorheriger Information. |
| Q1/AC25–26 sowie früherer Amendment-Spielraum | Explizite beidseitig bestätigte Verkleinerung erlaubt; keine Erweiterung. Keine normale Änderung bereits versendeter Vereinbarung. Alte Version bleibt bis Zustimmung verbindlich. |
| TRADE-07-Preview: Receipt verändert weder Shipping noch Inventory/Slots | Tatsächlicher Empfang bleibt ohne Versandklick zulässig; im neuen Vertrag muss fehlende Abgangsbuchung korrekt nachgeführt werden. Keine gefälschte Absenderselbstauskunft, kein erfundener Versandzeitpunkt. D02 durch 00A entschieden: atomarer Abgang tatsächlich versendeter Mengen und Zugang akzeptierter Mengen. Operative Slots entfallen ohnehin. |
| Q6 / produktive Ratingqualifikation erst global abgeschlossen; Preview drei Sterne | Eigener Empfang plus Prüfung genügt, unabhängig von Gegenrichtung; 1–5 Sterne, optionale positive Tags, blindes Publizieren. Nichtempfang allein begründet kein Rating. |

Unverändert bleiben kanonische mengenbasierte Supply, geschütztes Eigenexemplar, tatsächlicher Need, Album-/Pool-/bilaterale Cross-Freigaben, Privacy, aktuelle Erstellungsvoraussetzungen, atomare Validierung und Idempotenz. Kein neues starres 1:1 für manuelle Trades: aus der fixierten Angebotserstellerperspektive gilt weiterhin `Receive <= Give` in den zulässigen Balancegruppen. Automatische Erstellung bleibt initial 1:1 und mindestens fünf; keine automatische Umklassifizierung kleiner Gegenangebote zu manuellen Angeboten. 00B verlangt mengenbasierte Needs einschließlich Mehrfachbedarf; der bisherige binäre Reader ist dafür keine Zielbegrenzung. Keine neue Rankingregel oder Settings-UI wird hier festgelegt.

## 2. Produktgrenze

SAP organisiert Finden und Vereinbaren: Partner → konkreter Deal → Anfrage/Gegenangebot → Entscheidung. Nach Annahme erfolgt die operative Abwicklung primär in der späteren Sammlr-Zentrale. Die Zentrale projiziert kanonische Zustände; sie besitzt keine zweite Tradeengine.

Gelb „MEINE TO-DOS“, Rot „MEINE SENDUNGEN“, Grün „MEINE EINGÄNGE“ sind Eingänge in skalierbare Listen, nicht ein Post-it pro Trade. Ein Nutzer darf 30 angenommene Trades haben, sofern Supply/Need und sonstige Regeln ihre Annahme zuließen. To-dos, Sendungen und Eingänge dürfen dieselbe Trade-ID aus verschiedenen Handlungsperspektiven zeigen, ohne einen Trade mehrfach anzulegen. Noch keine UI spezifiziert oder gebaut.

## 3. Anfrage, Kapazität und Reservierung

Eine Preview ist ungebunden. „Anfrage senden“ legt einen exakten unveränderlichen Angebotssnapshot mit Teilnehmern, Richtung, Album, Code, positiven ganzzahligen Mengen, Herkunft, Erstellerperspektive und gültigem Regelkontext fest. Serverseitige aktuelle Prüfung ist in derselben atomaren Grenze wie die Anfrage und ihre Reservierungen erforderlich.

`open_outgoing(u,t) = Anzahl aktiver wartender Angebote mit aktuellem Angebotssender u und t < expires_at`.
Vor einer neuen Anfrage muss der Wert kleiner als drei sein. Gegenangebote sind ebenfalls selbst gesendete Anfragen und zählen beim neuen Sender. Akzeptierte, abgelehnte, zurückgezogene, ersetzte oder abgelaufene Angebote zählen nicht. Eingehende Anfragen sind unbegrenzt; keine separate operative Slotprojektion im neuen Vertrag. Legacy-Zähler behalten ihren Scope; Bestandsbindungen aller Verträge müssen gemeinsam berücksichtigt werden.

Nur eigene angebotene Give-Mengen werden bei Sendung reserviert. `3` handelbare Überschusskopien minus eine reservierte Kopie ergeben zwei weitere handelbare Kopien. „Dreimal insgesamt im Bestand“ ist etwas anderes: das kanonisch geschützte Eigenexemplar bleibt geschützt. Es werden weder der ganze Code noch der Bestand eines nicht zustimmenden Empfängers gesperrt.

Eine fremde Anfrage garantiert ihre Receive-Seite nicht. Reservierte Mengen verschwinden aus freier Supply für SAP, Auto-/manuelle Deals, weitere Anfragen und Annahmen. Kein neuer Lifecycle-eigener Verfügbarkeitsrechner. Option A ist verbindlich: Gleichzeitig mit den eigenen Give-Holds werden die eigenen gewünschten Receive-Mengen für dieses Angebot geclaimt. Keine fremde Supply und kein fremder Need wird dadurch reserviert. Der Empfänger kann seine angebotene Ware weiterhin anderweitig verwenden; vollständige Revalidierung bei Accept bleibt zwingend.

### 3a. Mengenbasierte Receive-Need-Claims — Option A

Für Nutzer/Album/Code seien `T` die autoritative benötigte Gesamtmenge, `P` der bereits vorhandene deckende Bestand, `I` noch ausstehende verbindliche Eingänge und `C` aktive eigene Pending-Claims neuer V1-Angebote. Für neue Angebote gilt `free_need = max(T - P - I - C, 0)`. Eine neue Claim-Menge darf `free_need` nicht überschreiten. Alle Mengen sind nichtnegative ganze Zahlen; kein Boolean-Cap auf eins. Der technische Ursprung/Persistenzadapter von T ist in L01 zu entwerfen; eine neue Bedarfseinstellungs-UI ist nicht Teil dieses Vertrags. Bestehender Einzelexemplarbedarf bleibt der entsprechende Spezialfall, keine Migration alter Verträge.

POR15 fehlt einmal: eigener Claim 1 lässt keinen weiteren freien Bedarf. POR15 wird insgesamt zweimal benötigt, Bestand und verbindliche Eingänge null: Claim 1 lässt Bedarf 1. Erst vollständige Deckung unterdrückt den Code. Ein Need-Claim verändert keinen physischen Bestand des Partners und garantiert keine Lieferung.

Give-Hold und eigener Receive-Claim werden innerhalb derselben Transaktion angelegt. Withdraw, Decline, 72h-Expiry und endgültiges Invalidieren/Beenden lösen beide exakt zugehörigen Bindungen atomar; keine Geister-Claims. Beim Counter werden alte Holds/Claims durch die eigenen des neuen Senders atomar ersetzt. Ein fehlgeschlagener Wechsel lässt den alten Zustand unverändert.

Bei Accept: aktuellen Bestand, alle wirksamen Reservations und Need-Mengen prüfen; eigene Claims/Holds als diesem Angebot zugehörig berücksichtigen, nicht gegen sich selbst zählen. Beide Give-Richtungen verbindlich halten und eingehende Claims in den angenommenen Deal überführen, einschließlich der anderen Seite. Dieselbe Menge darf nicht zugleich in C und I oder wieder als frei zählen. Prüfung, Versionierung und Speicherung bilden eine atomare Grenze gegen konkurrierendes Send/Accept.

Bei physischem Eingang erhöht sich P nur um akzeptierte Mengen; I wird entsprechend reduziert, ohne Doppelzählung. Nach Send bleibt I bis zur Empfangs-/Problemklärung bestehen, obwohl der Give-Hold verbraucht ist. Reduktionen geben nur entfallene Mengenclaims frei. Terminale Problemfälle behalten eine explizite Restmengenbehandlung; keine fingierte Bestandskorrektur. Spätere globale Einstellungen ändern nicht den angenommenen Regel-Snapshot.

Legacy bleibt unverändert und nutzt denselben realen Supply-Schutz. Keine rückwirkende globale Need-Exklusivität für alte Accepts. Bekannte verbindliche alte Eingänge werden von neuen V1-Prüfungen berücksichtigt; die in 00A dokumentierte Alt-Need-Abweichung darf nicht als Garantie globaler Exklusivität ausgegeben werden.

## 4. Anfragefrist und Ausgänge

`expires_at = offer_sent_at + 72 Stunden` als absolute UTC-Dauer; lokale Anzeige mit Zeitzone. Bei `now >= expires_at` keine Annahme oder Gegenangebot auf diesem Angebot. Sonntag/Montag und Sommerzeit verändern die Dauer nicht. Retry, Refresh, erneute Ansicht und Reminder verlängern sie nicht.

Sender darf bis zur Annahme zurückziehen; aktueller Empfänger darf ablehnen. Beide Vorgänge beenden das jeweilige offene Angebot und geben dessen Give-Reservations und Receive-Need-Claims atomar frei. Ablauf bewirkt dasselbe. Kein physischer Bestandszugang/-abgang, keine automatische schlechte Bewertung, keine Sanktion. Kurze Ablaufnachricht möglich; Systemaudit und dauerhafte Nutzerhistorie sind getrennt. Ein laufender angenommener Trade wird nicht durch einen verspäteten Pending-Expiry-Job beendet.

Reminder-Ereignisse bei `expires_at − 24h` und `expires_at − 6h`; serverseitiger Zeit-/Statuscheck, dedupliziert je Phase/Revision/Adressat/Schwelle. Kein Versand nach Phasenende und kein Anspruch auf Push-Infrastruktur in diesem Paket. Verzögerte Jobs dürfen weder Fristen verlängern noch dieselbe Warnung mehrfach erzeugen; Bündelung verpasster Schwellen ist spätere Zustellpolitik.

## 5. Revalidierung und höchstens ein Gegenangebot

Annahme validiert **die konkreten Positionen und Mengen**, nicht den alten Matchrang, einen pauschalen Inventar-Fingerprint oder die Identität aller übrigen Bestände. Unbeteiligte Inventaränderungen lassen ein noch gültiges Paket gültig. Bereits für diesen Vorgang gehaltene eigene Mengen werden innerhalb derselben Transaktion korrekt zugeordnet, nicht nochmals als fremde Konkurrenz abgezogen.

Ist das Originalangebot nicht mehr gültig, keine Teilannahme oder stille Neuberechnung. Der Empfänger kann einen aktuell berechneten konkreten Deal prüfen und als Gegenangebot absenden. Eine Neuberechnung allein sendet nichts. Das Original bleibt bis zur erfolgreichen atomaren Ersetzung offen oder wird regulär abgelehnt/zurückgezogen/abgelaufen; ein gescheiterter Gegenangebotsversuch hinterlässt keinen halben Wechsel.

Beim erfolgreichen Gegenangebot: Originalangebot `SUPERSEDED`, dessen Holds und Claims freigeben, neuen Sender und Snapshot setzen, dessen Give reservieren und eigene Receive-Mengen claimen, neuen 72-h-Zeitpunkt speichern, Gegenangebotszähler von 0 auf 1. Alles atomar. Der bisherige Sender muss nun selbst zustimmen; beim neuen Sender gilt dessen aktuelle Dreiergrenze. Ein Retry desselben Commands erzeugt keine zweite Revision oder neue Frist.

Wird das eine Gegenangebot bei späterer Annahme ungültig, endet die Verhandlung (`INVALIDATED`), Holds und Claims frei. Kein zweites Gegenangebot. Ein ausdrücklich neu gestarteter Tausch hat neue Verhandlungsidentität und aktuelle Validierung. Vorannahme-Gegenangebot und nachträgliches Amendment sind getrennte Konzepte; das Ein-Gegenangebot-Limit ist keine erfundene Obergrenze für Packkorrekturen. Retries nutzen dieselbe Command-/Angebotsidentität; parallele neue Verhandlungen dürfen keine bereits geclaimten Need-Mengen nochmals beanspruchen. Keine implizite gegenseitige Annahme.

## 6. Annahme und Packen

Erfolgreiche Annahme benötigt Authentisierung des aktuellen Empfängers, nicht abgelaufene aktuelle Revision, aktuelle Supply-/Need-/Regelprüfung und atomare beidseitige Reservierung. Bestehende Sender-Holds bleiben zugeordnet; nicht doppelt reservieren. Pending-Need-Claims werden ohne Lücke oder Doppelzählung in verbindliche Eingänge überführt. Der unveränderte genaue Snapshot wird verbindlich; Annahmezeit und initiale Packfrist `accepted_at + 72h` werden festgehalten. Kein Inventarabbuchen und keine Adressanzeige bei Annahme.

Jede Person erhält ihre eigene mengenrichtige Give-Packliste aus der angenommenen Version. Große Deals nutzen dieselbe Regel, keine künstliche Fotozahlgrenze. Packhäkchen und Fotos verändern keinen Bestand. Fehlende reale Sticker werden ausdrücklich gemeldet, nicht durch automatische Auswahl ersetzt; Behandlung des inkorrekten Bestands/Holds siehe D06.

Vorbereitung besteht aus bereitgelegten Mengen, mindestens einem Kontrollfoto und ausdrücklicher Vollständigkeitsbestätigung für diese Version. Mehrere Fotos, Kamera oder Galerie sind zulässig; sämtliche zu sendenden Sticker müssen grundsätzlich erkennbar sein. Ohne automatische Erkennung bleibt das eine Nutzererklärung plus Partnerprüfung, keine maschinelle Echtheitsgarantie.

Eigene Fotodrafts sind nicht für den Partner sichtbar. Erst beidseitig abgeschlossene Vorbereitung öffnet beide Kontrollpakete gegenseitig. Diese Barriere muss auf dem Server gelten, nicht nur als CSS/URL-Versteck. „Wartet auf Gegenseite“ ist eine rollenbezogene Projektion, keine zusätzliche globale Sperre.

### 6a. Verbindliche Präzisierungen aus LIFECYCLE-00A

**Pack-/Kontrollfrist (D03 entschieden):** Innerhalb von 72 Stunden ab erfolgreicher Annahme muss jede Seite ihre eigene Packliste abarbeiten, Sticker vorbereiten, notwendige Fotos hochladen und die eigene Vorbereitung abschließen. Die anschließende gegenseitige Fotoprüfung ist eine getrennte Phase und nicht Teil dieser Frist. Für sie gilt in V1 keine harte automatische 72h-Abbruchfrist; Reminder-/Eskalationsereignisse werden unterstützt, ohne daraus einen automatischen Abbruch abzuleiten. Muster: 72h Anfrage → 72h eigene Vorbereitung → gegenseitige Fotoprüfung → 72h Versand. Fristen bei späteren Änderungen bleiben D04.

**Regel-Snapshot (D08 Regelteil entschieden):** Bis einschließlich Annahme gelten aktuelle Bestände, Reservierungen, Trade-v2-Regeln und beide Album-/Cross-Einstellungen. Bei Annahme werden konkrete Vereinbarung und relevante Zulässigkeit gemeinsam eingefroren. Nachträgliche globale Änderungen wirken nur auf neue Deals und noch offene Angebote. Auch Reduktionen verwenden den eingefrorenen Rahmen, ohne fundamentale Mengen-, Consent- oder Sicherheitsinvarianten auszuschalten.

Später zu persistierende Contract-Daten, noch kein Schemaentwurf:

- unveränderlicher Lifecycle-Contract-Type und Rule-Version mit definiertem Validator; Annahmezeit, Teilnehmer-IDs und feste Angebotserstellerperspektive;
- exakte Dealrevision mit beiden Richtungen, Album-/Code-/Mengenpositionen und beidseitiger Zustimmung;
- für jeden beteiligten Nutzer und jedes betroffene Album damalige Pool-Freigabe (`trade_pool_enabled`) und normalisierter `cross_album_mode`, einschließlich explizitem SAME-Default bei fehlender Präferenz;
- daraus verbindlich abgeleitete Balancegruppen sowie Prüfmodus `Receive<=Give` versus initial automatisch gleich, Herkunft und anwendbare Erstellungsvoraussetzungen; keine Neuinterpretation über spätere globale Defaults;
- zulässiger Album-/Positionsumfang, Referenz auf die angenommene Basisrevision und Policy-Version für reine Verkleinerung. Keine neuen Alben/Sticker durch Amendment;
- Referenz auf den gemeinsamen Hold-/Mengenledger. Aktuelle physische Mengen und fremde Reservations werden **nicht** als dauerhaft gültige Verfügbarkeitsgarantie eingefroren.

Ein globaler Einstellungsschalter ändert diesen Snapshot niemals nachträglich. Accountende/Blockierung hebt Datenschutz und Authentisierung nicht auf; konkrete Zugriffspolitik bleibt separates Folge-/Launch-Gate, keine erneute offene Cross-Regel.

## 7. Fotokontrolle und Änderungen

Jeder prüft die **Gegenseite**: bestätigen oder `MISSING_STICKER`, `WRONG_STICKER`, `CONDITION_PROBLEM`, `NOT_RECOGNIZABLE` melden. Ein Kontrollproblem beendet den Trade nicht automatisch. Gegenseite kann Packung korrigieren und neue/zusätzliche Fotos hochladen oder eine regelkonforme Verkleinerung vorschlagen. Fotos und Bestätigungen tragen Dealversion und Kontrollpaketversion. Eine Fotokorrektur invalidiert die Bestätigung genau dieses geänderten Pakets; kein unbemerktes Austauschen nach Bestätigung. Bereits gesehene Information kann nicht „ungesehen“ gemacht werden.

Eine Verkleinerung wird innerhalb des bei Annahme eingefrorenen Regelrahmens geprüft, nicht gegen nachträglich geänderte globale Pool-/Cross-Einstellungen. Physische Mengen, Holds, aktuelle Revision und Sicherheitsinvarianten werden weiterhin frisch geprüft. Eine Verkleinerung benennt alle entfernten Positionen/Mengen beider Seiten vor Zustimmung. Im 23↔23-Beispiel entfernt der meldende Nutzer den nicht vorhandenen Give-Sticker und verzichtet auf ein regelkonformes Receive-Gegenstück: 22↔22. Keine zufällige Auswahl. Ein anderes Album darf nur dann als Gegenstück dienen, wenn die bestehenden Balancegruppen das erlauben. Die manuelle Ungleichheitsregel wird dadurch nicht global zu 1:1 umdefiniert.

Ein Amendment darf nur Teilmengen der bisherigen Positionen enthalten, keine hinzugefügten Sticker oder Mengenerhöhung. Beide Richtungen bleiben nichtleer und regelkonform. Die ursprüngliche Erstellerperspektive bleibt bei der Validierung des angenommenen Vertrags gespeichert; eine Prüfung aus der versehentlich umgedrehten Empfängerperspektive darf einen gültigen asymmetrischen Deal nicht verbieten.

Vorschlag ist explizite Zustimmung des Vorschlagenden zur exakten Version; Wirksamkeit erst mit Zustimmung der anderen Seite und atomarer frischer Prüfung. Alter Snapshot und Holds bleiben bis dahin verbindlich. Bei Erfolg neue unveränderliche Version, frei werdende Mengen atomar freigeben, betroffene Pack-/Foto-/Review-Schritte entwerten. Keine automatische Wiederherstellung des physisch fehlenden Stickers; D06. Bei Ablehnung kein stiller Wechsel: das Original bleibt oder der Trade wird vor Versand ausdrücklich beendet. Frist-/Abbruchdetails bei späteren Korrekturen D04; initiale eigene Packfrist durch D03 entschieden.

Bereits bestätigter oder durch tatsächlichen Empfang belegter physischer Versand sperrt normale Amendments und normalen Abbruch. Die Reduktion einer zweiten Richtung darf nicht rückwirkend eine bereits versendete Gegenleistung ändern; Teilversand führt ausschließlich zum Problemweg.

## 8. Fotozugriff und Retention

Kontrollfotos sind operative Daten. Nach erfolgreicher beidseitiger Kontrolle plus Adressfreigabe keine dauerhafte normale Galerie; spätestens bei bestätigtem Empfang verschwindet das betreffende Kontrollpaket aus normaler Nutzeransicht. Zugriffssperre/Entfernung aus UI ist **nicht** gleich physische Löschung aus Storage, Caches oder Backups.

Keine gesetzliche oder technische Tagesfrist erfunden. Versionierte Korrektur nach bereits erfolgter Adressfreigabe darf alte gelöschte Fotos nicht voraussetzen: neue gültige Kontrollpakete nötig, soweit die Grundlage geändert wurde. Beweissicherung bei Problemen, Löschjob, Dateigrößen/Uploadschutz und berechtigter Supportzugriff vor Launch separat festlegen. Keine offene Foto-URL oder öffentliche Sammlung aus Kontrollfotos.

## 9. Adresse und automatische Freigabe

Adresse ist keine Registrierungsvoraussetzung. Vor Eintritt in die Adressfreigabe benötigt jeder eine konkret gewählte, vollständige Versandadresse: Vorname, Nachname, Straße, Hausnummer, PLZ, Ort, Land. Bestehende Adresse wählen/ändern oder neue hinzufügen; mehrere Vorlagen/Standardadresse perspektivisch möglich. Vorlagen und konkreter Trade-Adresssnapshot sind getrennt. Keine zusätzlichen Pflichtdaten wie Messenger oder Telefonnummer.

Beidseitig vorbereitete Pakete, erfolgte gegenseitige Sichtbarkeit, beide gültigen Partnerbestätigungen **und** zwei feststehende vollständige Adressen bilden die Freigabebarriere. Vor finaler Fotobestätigung ist klar zu informieren: Wenn beide bestätigen, werden die gewählten Versandadressen gegenseitig sichtbar. Keine gesonderte „Adresse freigeben“-Aktion. Fehlende eigene Adresse muss vor dieser finalen Zustimmung vervollständigt werden; kein heimliches späteres Austauschen einer bestätigten Adresse.

Freigabe ist ein atomarer richtungsübergreifender Zugriffsschritt für die zwei Teilnehmer dieses Trades, niemals allgemeiner Profilzugriff. Keine Anzeige bei Anfrage, Annahme, Packen oder einseitigem Foto. Kontakte/WhatsApp/Telegram bleiben optionales späteres Thema. Der bestehende NP-C3-1-Schutz für zweckgebundenen Zugriff, Ende normaler Partneransicht, Widerruf und Support bleibt; Wechsel/Widerruf nach Freigabe D05. Keine Annahme, dass bereits kopierte Adressen zurückgerufen werden könnten.

## 10. Versand und physischer Abgang

Ab gemeinsamer Adressfreigabe: `ship_due_at = address_released_at + 72h`, pro Person eigener Erfüllungsstatus; Reminder bei 24h/6h Restzeit. Adressansicht, Versandoption oder Packbestätigung sind kein Versand. V1 Selbstauskunft mit Confirm-Schritt „Bitte bestätige erst, wenn du den Brief tatsächlich versendet hast.“ / „Ja, versendet“ / „Abbrechen“.

„Ja, versendet“ bewirkt atomar genau einmal: eigene reservierte Give-Mengen aus physischem Bestand abbuchen, entsprechenden Hold in verbrauchten/abgewickelten Abgang überführen, Versandbestätigung mit Akteur und Beobachtungszeit festhalten, Gegenrichtung unverändert lassen. Ein späterer Verlust erzeugt weder Bestandsrückgabe noch freie Doppelte. Nach endgültiger Bestätigung kein normaler Rückzieher; nur autorisierter Problem-/Supportpfad.

Nach einseitigem Versand bleibt die Gegenseite verpflichtet, ihre Give-Mengen bleiben gehalten. Bei Fristüberschreitung `OVERDUE`/Problem-/Action-required, keine normale Auflösung und keine Freigabe ihrer Mengen allein wegen Timeout. Keine automatische Sanktion oder Bewertung. Auch bei noch keinem Versand erlaubt Fristablauf ohne gesonderte Entscheidung keine erfundene Bestandsbuchung oder automatische erfolgreiche Beendigung.

## 11. Tatsächlicher Empfang ohne Versandklick

Empfang ist unabhängig von einer Absenderselbstauskunft zulässig, auch aus `PACKING` oder `READY_TO_SHIP`. Bei bestätigter physischer Ankunft darf der weitere Prüf-/Problemweg nicht vom fehlenden Klick abhängen. Keine rückwirkende Fotobestätigung oder Adressfreigabe fingieren.

Unterschiedliche Fakten speichern: `sender_confirmed_at` (Absender hat erklärt), `arrival_recorded_at` (Empfänger hat Ankunft erklärt), Abgangsnachweisquelle (`SENDER_CONFIRMATION` oder `RECEIPT_EVIDENCE`) und tatsächlich gebuchte Mengen. Empfang belegt physische Bewegung, aber weder einen früheren exakten Versandzeitpunkt noch einen fremden Klick. Ein effektiver physischer Richtungsstatus darf deshalb „angekommen“ sein, während `sender_confirmed_at` weiterhin leer ist.

Bei vollständig korrekt bestätigtem Paket ist die fehlende Abgangsbuchung derselben Positionen zusammen mit dem Eingang genau einmal nachzuholen. Nachträglicher Versandklick erkennt den bereits gebuchten Abgang und bucht nichts erneut. Ist Bestand/Reservierung unerwartet unzureichend, darf keine negative Buchung oder Nullkappung erfolgen: Ankunftsfakt bleibt dokumentierbar, Mengenabgleich in explizitem Problem-/Reconciliation-Zustand, keine zweite Verplanung der strittigen Menge.

Durch 00A ist D02 entschieden: Auch Teil-/Problemempfang führt in derselben atomaren Verarbeitung die tatsächlich festgestellten versendeten Give-Mengen aus dem Absenderbestand ab und ausschließlich tatsächlich akzeptierte Mengen in den Empfängerbestand zu. Abgang und Zugang können verschieden groß sein (etwa bei identifizierter, aber abgelehnter beschädigter Ware). Die Versandrichtung gilt systemisch als versendet und angekommen; offene Mengendifferenzen bleiben sichtbar. Ein fehlendes Stück wird nicht allein durch seine Erwartung zu einem bewiesenen Empfang oder zur automatischen Rückgutschrift. Unbelegte Restmengen und inkonsistenter Ausgangsbestand benötigen den expliziten Problem-/Reconciliation-Zustand, keine negative oder erfundene Buchung. Dies ist kein erneutes Freigabegate für den bereits entschiedenen Empfangspfad. Alle Fälle müssen durch denselben Ledger-/Reservationsadapter laufen; kein Aufruf des alten `ship()` im Namen der Gegenseite.

## 12. Empfang, Probleme und verspätete Ankunft

Erwartete Liste je Position und Menge prüfen: korrekt erhalten, fehlt, falsch, beschädigt. Beschädigt kann der Empfänger ausdrücklich akzeptieren oder nicht akzeptieren; falsch wird nicht als erwarteter richtiger Sticker eingebucht. Ein fremder falscher Code wird nicht automatisch der Sammlung hinzugefügt. Nur tatsächlich erhaltene, akzeptierte Mengen erzeugen Zugang.

„Alles angekommen“ bedeutet geprüfte vollständige Annahme des vereinbarten Pakets. Reine Ankunft ist noch keine Vollbuchung. Bei 30 erwartet/29 akzeptiert: 29 Zugänge, 1 offene Differenz. Bereits gebuchte 29 werden bei weiterer Bestätigung niemals erneut gebucht. Kein Restore beim Sender für fehlende Stücke. Später wirklich akzeptierte Nachmengen nur als zusätzliche noch ungebuchte Deltas, nie über der vereinbarten Erwartungsmenge. Ersatz-/Retourenprozesse sind nicht still Bestandteil dieses Vertrags.

„Noch nicht angekommen“ frühestens 7×24h nach der tatsächlichen Versandbestätigung; maßgeblich ist diese konkrete Richtung. Kein Timer ab Annahme oder fremder Gegenrichtung. Ohne Versandbestätigung gibt es keinen erfundenen Fristanker; dafür Versand-überfällig/Problemhilfe. Nichtankunftsmeldung bucht nichts. „Doch angekommen“ bleibt möglich und führt zur tatsächlichen Prüfung/Teilbuchung, auch ohne Absenderversandklick. Nach administrativem Abschluss siehe D09.

Ein Teil-/Fehlempfang ist ein offener Problemfall, bis die offene Restmenge durch tatsächlichen weiteren Eingang oder ausdrücklich qualifizierte Problementscheidung geklärt wird. „Problem gelöst“ darf keine fehlenden Mengen ohne physischen Beleg einbuchen. Der andere Tradezweig läuft unabhängig weiter.

## 13. Abschluss, Bewertung und Zuverlässigkeit

Ein Trade ist vollständig geklärt, wenn **beide Richtungen** `SETTLED_OK` oder qualifiziert `SETTLED_WITH_PROBLEM` sind und keine offene Mengen-/Problemabstimmung bleibt. Beide versendet reicht nicht. Ein geklärter eigener Empfang mit wartender Gegenrichtung ist `PARTIALLY_SETTLED`; Abschluss und Archiv sind getrennte Projektionen. Problematischer/administrativer Abschluss bleibt vom normalen Erfolg unterscheidbar. Nicht erfolgreich gelöste Probleme dürfen nicht automatisch als Erfolg zählen; spätere administrative Frist/Autorität D09.

Bewerten darf jeder nach eigenem tatsächlichem Empfang und Prüfung der Gegensendung, ohne auf Ankunft des eigenen Briefs zu warten. 1–5 Sterne, optionale positive Tags: Schneller Versand, Gut verpackt, Sticker wie beschrieben, Freundlicher Tausch. Keine Pflichtfreitexte, öffentlichen negativen Tags, automatische 1-Stern-Wertung oder Ratingpflicht zum Tradeabschluss.

Bewertungen bleiben gegenüber der Gegenseite blind bis beide bewertet haben oder die Frist der noch nicht bewertenden Gegenseite endet. Je Person 14 Tage nach relevantem Empfang; Fristanker, lange Nichtprüfung und nie eintretender Empfang siehe D07. Auch Aggregate/Notifications dürfen eine noch blinde Einzelwertung nicht verraten. Keine Veröffentlichung nur weil die eigene Abgabefrist vorbei ist, solange die fremde Frist noch läuft oder gar nicht begonnen hat.

Zuverlässigkeit ist ein getrenntes, nicht öffentlich berechnetes Ereignisprotokoll: erfolgreicher Abschluss, Abbruch nach Annahme, Pack-/Versandüberziehung, Nichtankunft und andere belegte Lifecycle-Fakten. Nichtankunft ist eine Meldung, keine automatisch bewiesene Schuld des Partners. Keine Rankingstrafe oder öffentliche Scoreformel.

## 14. Entscheidungsstatus und spätere Detailgates

| ID | Entscheidungsstand / spätere Ausarbeitung | Grenze | Spätester Gate |
|---|---|---|---|
| D01 | **Entschieden durch 00B: OPTION A, mengenbasiert.** Eigene Give-Holds und eigene Receive-Claims bei Send, gemeinsame Freigabe/Überführung bei Ausgang/Accept. | Neuer unveränderlicher Contract-Type, gemeinsame physische Supply, Altverträge unverändert; §3a. | Fachlich geschlossen; technische Ausarbeitung L01 |
| D02 | **Entschieden durch 00A A:** Empfang ohne Versandklick führt betroffene tatsächliche Abgänge und akzeptierte Zugänge atomar nach; Richtung systemisch versendet/angekommen. | Gemeinsamer Exactly-once-Ledger für Ship und Receipt; Teil-/Problemzugang nur akzeptierte Menge, keine erfundenen Restbuchungen. | Fachlich geschlossen; technische Ausarbeitung in L01/L06/L07 |
| D03 | **Entschieden durch 00A B:** eigene Vorbereitung bis accepted_at +72h; gegenseitige Fotoprüfung separat. | Keine harte automatische Abbruchfrist der Prüfung; Reminder/Eskalation möglich. | Fachlich geschlossen; Zeitmodell in L01/L04 |
| D04 | Fristen nach Foto-Korrektur/Amendment, Frist für Amendmentzustimmung, Wiederholungen; wer darf nach Annahme vor Versand allein beenden? | Kein stiller Neustart/TTL aus Pending übernehmen. Sicherheitsgrenze „nach physischer Bewegung kein normaler Abbruch“ gilt bereits. | Vor LIFECYCLE-04, Abbruchberechtigung vor LIFECYCLE-03 |
| D05 | Änderung/Widerruf gewählter Adresse nach finaler Fotobestätigung/Freigabe; Re-Freigabe bei neuer Version | Bereits offengelegte Daten nicht zurückrufbar; Vorlage darf nicht heimlich den Trade ändern. Bestehenden NP-C3-1-Vertrag beachten. | Vor LIFECYCLE-05 |
| D06 | Tatsächlich fehlender Give-Sticker trotz gepflegtem Bestand: Korrekturzeitpunkt, aktiver Hold, Verfügbarkeit nach Freigabe | Keine Phantom-Doppele nach Amendment/Cancel wieder anbieten; keine unspezifizierte automatische Bestandskorrektur. Umgang mit physisch unsicheren Mengen explizit autorisieren. | Vor LIFECYCLE-04; Persistenzbedarf in LIFECYCLE-01 vorbereiten |
| D07 | 14-Tage-Anker (Ankunft oder abgeschlossene Prüfung), Teilprüfung, verpasste Prüfung; blindes Rating wenn Gegenseite nie empfängt | Individuelle Zeitpunkte; kein stilles Freigeben am eigenen Deadline-Ende. Unbegonnene fremde Frist ist nicht abgelaufen. Regeln für Nichtempfang/administrativen Abschluss separat entscheiden. | Vor LIFECYCLE-08 |
| D08 | **Regel-Snapshot entschieden durch 00A C:** aktuelle Prüfung vor Accept, danach eingefrorene Zulässigkeit auch bei Reduktion. | Konkrete Snapshotdaten §6a. Accountende/Block-/Zugriffsfolgen bleiben Sicherheits-/Datenschutzgate; kein Widerruf des Deals durch globale Cross-/Pool-Änderung. | Snapshot fachlich geschlossen; Zugriffsdetails vor produktiver Integration/Launch |
| D09 | Administrative Problembeendigung, Autorität/Frist, Restholds, danach verspäteter Eingang, Nachbewertung | Kein unendlicher operativer Schwebezustand; keine erfundene automatische Frist, kein Mengenrestore. Terminalen Auditstand nicht überschreiben, spätere Fakten separat. | Vor LIFECYCLE-07/08 und Launch |

Die neuen ausdrücklichen 3-/72h-/einseitigen Reservierungsregeln sind **keine** offenen Fragen mehr. Widersprüche mit alten Zielverträgen sind durch die abgegrenzte Supersession aufgelöst. D02/D03 und der Regelteil D08 sind durch 00A entschieden. D01 ist in der [Need-Claims-Analyse](TRADE_LIFECYCLE_00A_NEED_CLAIMS.md) konkretisiert; Option A ist durch 00B verbindlich beschlossen, einschließlich mengenbasierter Semantik. D04–D07/D09 und separate Zugriffs-/Launchfragen bleiben spätere Gates; keine davon blockiert aktuell die Persistenz-/State-Grundlage LIFECYCLE-01. Ihre betroffenen späteren Funktionen bleiben bis zur Klärung gesperrt.

## 15. Separate Datenschutz-/Launch-Gates

Vor öffentlichem Produktivbetrieb fachlich/rechtlich klären, hier **keine Rechtsberatung oder Fristenfestlegung**:

1. Speicherung von Versandadressen und Rechtsgrundlage/Zeitpunkt konkreter Partnerweitergabe.
2. Retention von Trade-Adressen, Widerruf/Accountende, technische Löschung einschließlich Backups.
3. Kontrollfoto-Retention, personenbezogene Bildinhalte, Zugriffs- und Löschkonzept bei Problemen.
4. Freiwillige externe Kontaktweitergabe, ohne Messengerpflicht.
5. Bewertungs-/Reputationssystem einschließlich Blindheit, Moderation und Auskunft/Löschung.
6. Zweckgebundene Supportrechte, Nachvollziehbarkeit und kein pauschaler interner Adresszugriff.
7. Minderjährige Nutzer.
8. Haftung bei Briefverlust.
9. Künftiger Porto-/Frankierverkauf (außerhalb V1), falls später geplant.
10. Datenschutzinformation sowie Einwilligungs-/Vertragslogik für den Gesamtprozess.

Nicht enthalten: Messenger, Post-API, Porto-Verkauf, Tracking, Versicherung, Support-Dashboard, öffentlicher Zuverlässigkeitsscore, automatische Sanktionen, finale Zentrale-UI, Push-Infrastruktur oder Trade-Redesign.

Weitere Vertragsbestandteile: [Zustandsmaschine](TRADE_LIFECYCLE_V1_STATE_MACHINE.md), [Invarianten/Atomarität](TRADE_LIFECYCLE_V1_INVARIANTS.md), [Code-/Persistenzlücken](TRADE_LIFECYCLE_V1_GAP_ANALYSIS.md), [Folgepakete](TRADE_LIFECYCLE_V1_IMPLEMENTATION_PLAN.md), [Audit](TRADE_LIFECYCLE_00_AUDIT.md).
