# Trade Lifecycle V1 — Invarianten, Buchungen und Nebenläufigkeit

Verbindlicher Kontext: [Fachvertrag](TRADE_LIFECYCLE_V1_CONTRACT.md), [Transitions-IDs](TRADE_LIFECYCLE_V1_STATE_MACHINE.md). Ausschließlich Spezifikation, keine ausführbaren DB-Commands.

## 1. Mengenbegriffe

Schlüssel `k = (album_id, canonical_sticker_code)`, immer im Kontext eines Nutzers. Sichtbarer Code allein identifiziert keinen Sticker global. Mengen sind nichtnegative ganze Zahlen, Positionsmengen strikt positiv; Boolean-Werte sind keine Mengen.

- `P(u,k)`: physischer gepflegter Bestand.
- `A(u,k)`: kanonisch geschützte Albumzuordnung/Eigenexemplar.
- `R(u,k)`: Summe wirksamer Supply-Holds aller relevanten Verträge/Vorgänge.
- `F(u,k)=P−A−R`: tatsächlich freie Menge, nicht auf null gekappte Fehlerverdeckerformel.
- `E(d,k)`: erwartete vereinbarte Menge einer physischen Richtung d.
- `D(d,k)`: kumulativ genau einmal gebuchter realer Abgang zu dieser Position.
- `C(d,k)`: kumulativ gebuchter akzeptierter physischer Zugang beim Empfänger.
- `M(d,k)`: belegte tatsächlich physisch bewegte Menge, einschließlich nicht akzeptierter Ware; bei fehlender Evidenz unbekannt statt erfundener Vollmenge.

Bei normalem bestätigtem Versand gilt `D=E`; bei geprüftem korrektem Vollerhalt `C=E`. Bei 30 gesendet/29 akzeptiert gilt `D=30`, `C=29`, nicht D=29. Bei Empfang ohne Versandklick gilt der durch 00A entschiedene D02-Pfad: tatsächliche Abgangsmengen und akzeptierte Zugangsmengen atomar, offene Restdifferenz separat. Zugang und Abgang sind verschiedene Fakten; Warenverlust/Schaden darf `D>C` hinterlassen. Weltweite Bestandskonstanz durch automatische Ersatzgutschriften wäre falsch.

Der aktuelle Reader projiziert binären Bedarf; das ist ein Ist-Befund, keine V1-Zielgrenze. 00B setzt mengenbasierte Claims: freier Bedarf = max(Gesamtbedarf − deckender Bestand − verbindliche Resteingänge − eigene aktive Pending-Claims, 0). Bedarf 2 minus Claim 1 lässt Bedarf 1.

## 2. Formale Kerninvarianten A–N

| ID | Invariante | Abnahmeszenario |
|---|---|---|
| A | `P>=0`, `A>=0`, `R>=0`, `R<=P−A`, `F>=0` nach jedem erfolgreichen Commit. Ungültige Ausgangslage nicht still kappen. | Zwei Reservierungen konkurrieren um letzte freie Kopie: nur eine erfolgreich. |
| B | Summe fremder Holds plus zu reservierendes Delta überschreitet keine freie physische Menge; keine Doppelverplanung einer konkreten Menge. | Gleicher Code mit drei freien Kopien: 1+2 erlaubt, zusätzliche 1 abgelehnt. |
| C | Unilateral offene Anfrage S→R erzeugt Supply-Holds ausschließlich für S, niemals R. | Zehn fremde Anfragen reduzieren R-Supply nicht. |
| D | Accept setzt erfolgreiche frische Prüfung exakt derselben Revision in derselben atomaren Schreibgrenze voraus. | Zwischen Preview und Accept belegter Sticker verhindert Annahme ohne Teilreparatur. |
| E | Bei Accept entsprechen beide wirksamen Richtungs-Holds exakt der noch unversendeten vereinbarten Menge; vorhandene eigene Holds nicht doppelt zählen. | Accept-Retry liefert vorhandenen Erfolg, keine zweiten Holds. |
| F | Eigene physische Versandbestätigung überführt Hold und senkt P genau einmal um tatsächliche vereinbarte Give-Menge. | Zweimal „Versendet“: nur ein Abgang. |
| G | `C` entsteht ausschließlich aus tatsächlich erhaltenen und akzeptierten Mengen; `0<=C<=E`. | Falsch oder beschädigt/nicht akzeptiert erzeugt keine erwartete Gutschrift. |
| H | Verlust/fehlende Empfangsmenge erzeugt keinen automatischen Zugang beim Absender und kein erneutes Supply-Angebot. | D=30, C=29 bleibt so bis echter weiterer Eingang. |
| I | Partneradresszugriff nur nach zwei aktuellen Vorbereitungen, beidseitiger Sichtbarkeit, zwei gültigen Gegenpaketbestätigungen und zwei gewählten Adressen. | Einseitige Fotos/Review oder stale Revision: keine Adresse. |
| J | Jede tatsächliche physische Bewegung (auch Receipt-Evidence) sperrt normalen Cancel und normales Amendment. | Receipt ohne Versandklick darf kein anschließendes Cancel mit Hold-Recycling erlauben. |
| K | Vor Accept gelten aktuelle Pool-/Cross-/Same-/Need-/Mengenregeln; angenommene Reduktionen halten den eingefrorenen Zulässigkeitsrahmen und aktuelle physische Sicherheitsinvarianten ein; keine zufällige Ersatzwahl. | Reduktion quer durch gesperrte Alben wird abgelehnt. |
| L | Effektive angenommene Version wechselt nur nach zwei identifizierbaren Zustimmungen zum gleichen genauen Proposal und frischer Prüfung. | Gleichzeitige unterschiedliche Amendment-Revisionen können nicht beide wirksam werden. |
| M | Je Verhandlung `counter_count` monoton in `{0,1}`; höchstens ein aktives Angebot. | Ungültiges Gegenangebot beendet Vorgang; kein drittes Angebot in derselben Verhandlung. |
| N | Rating nur nach eigenem tatsächlichem Empfang und Prüfung, nicht allein aufgrund eigener Versand-/Partner- oder globaler Abschlussaktion. | Eigene Sendung noch unterwegs, Gegenpaket geprüft: Rating erlaubt. Ohne Erhalt keine Berechtigung. |

## 3. Zusätzliche Sicherheitsinvarianten

- S01: `open_outgoing_new <=3` im entschiedenen Scope; keine incoming-/accepted-Quota. D01 ist durch 00B entschieden: Option A mit mengenbasierten eigenen Pending-Claims und unveränderten Altverträgen. Keine Begrenzung über 3/3-Preview-Slots übernehmen.
- S02: Bestehende Snapshots unveränderlich; Angebot, Gegenangebot und Amendment erhalten eigene Versionen. Herkunft wechselt nicht still von automatisch zu manuell.
- S03: Bei Annahme gilt exakt gespeicherte Erstellerperspektive, nicht unbemerkt die aktuelle Request-/Sessionperspektive. Ein zulässiges manuelles 3-Give/2-Receive-Angebot bleibt bei Gegenparteiannahme dasselbe Angebot.
- S04: Idempotenz enthält Teilnehmer, Aktion, Vorgang, Revision und Payloadidentität; gleicher Schlüssel mit verändertem Payload ist Konflikt, kein neuer Erfolg.
- S05: Zeitpunkte serverseitig, absolute Zeit; unveränderlicher Offer-Sendezeitpunkt je Revision. Keine Fristverlängerung durch Retry/Clockwechsel. `now==deadline` ist bereits abgelaufen.
- S06: Foto-/Review-/Adressfreigaben referenzieren konkrete Versionen. Sichtbarkeitsprüfung auch für Direkt-URLs/Downloads und nach Rollenwechsel/Block; keine allgemein zugängliche Galerie.
- S07: Versand nach Receipt-Evidence und Receipt nach Versand teilen genau eine fachliche Abgangsidentität. Beide Wege dürfen denselben Abgang nicht zweimal auslösen.
- S08: Empfang darf nicht als fremde Selbstauskunft protokolliert werden. `sender_confirmed_at` bleibt ohne dessen Erklärung leer; `arrival_recorded_at` ist keine erfundene Versandzeit.
- S09: Je Positionsbuchung `ΔC = bestätigte neue akzeptierte Zielmenge − bereits gebuchte C`; nur positive echte Deltas, keine pauschale Neuaddition der Erwartung.
- S10: Terminaler Verlust/Problemabschluss ist kein erfolgreicher Vollerhalt. Rating, Erfolgstrophäen und Historie dürfen diese Qualität nicht vermischen.
- S11: Geplante Incoming-Menge ist niemals physischer Bestand und keine handelbare Supply. Nach endgültig verlorener Restmenge darf ein neuer tatsächlicher Need wieder sichtbar werden, ohne Senderbestand zu restaurieren; qualifizierter Abschluss D09.
- S12: Neue Fachversionen ändern keine Legacy-/SmartDeal-V1-Fristen, Holds, Zustände oder Bewertungsrechte rückwirkend.

## 4. Buchungsmatrix

| Übergang | Supply-Holds | Senderbestand | Empfängerbestand |
|---|---|---|---|
| Preview / Entwurf | keine neuen | unverändert | unverändert |
| Original/Gegenangebot senden | nur aktuelle Sender-Give; beim Gegenangebot alte Holds atomar ersetzen | unverändert | unverändert |
| Offene Anfrage ablehnen/zurückziehen/ablaufen | eigene Vorgangsholds frei | unverändert | unverändert |
| Annahme | beide Seiten vollständig, eigene vorhandene Holds übernehmen | unverändert | unverändert |
| Packen/Fotos/Review/Adresse | halten | unverändert | unverändert |
| Reduktion wirksam | beide Richtungen exakt auf neue Version reduzieren; D06 bei fehlendem Realbestand | kein stiller Phantomzugang | unverändert |
| Pre-shipment Cancel | erlaubte Holds frei; Fehlbestand nicht unbehandelt anbieten | keine vermeintliche Rückbuchung, weil noch nicht abgebucht | unverändert |
| Eigener Versand | eigene Holds in Abgang überführen | −Deltamenge | unverändert |
| Tatsächlicher Eingang, Abgang schon gebucht | bereits verbrauchte Holds nicht wiederverwenden | unverändert | nur +akzeptiertes Delta |
| Vollerhalt ohne vorherigen Abgang | gleiche Abgangsidentität genau einmal nutzen | −fehlender voller Abgang | +fehlender akzeptierter Zugang |
| Teil-/Falsch-/Schadenseingang ohne Versandklick | D02 entschieden / Reconciliation; unbelegte Restmengen nicht freigeben | nur fachlich belegter und autorisierter Abgang, keine erfundene Vollmenge | nur tatsächlich akzeptierte Menge; bei fehlender sicherer atomarer Bilanz explizit ausstehend statt falscher Erfolg |
| Nichtankunft / Überziehung | keine stillen Releases | kein Restore | kein Zugang |
| Tatsächliche spätere Restlieferung | gemäß bestehender Richtung/Problemauflösung | kein zweiter Abgang derselben bereits versendeten Ware | nur noch fehlendes echtes Delta |
| Administrativer Abschluss | Restmengendisposition nach D09 | kein automatischer Restore | kein automatischer Vollzugang |

Packfehlmenge ist nicht mit einer gewöhnlichen Rücknahme eines Drafts gleichzusetzen: das System kennt jetzt eine Abweichung zwischen gepflegtem und tatsächlichem P. Eine einfach freigegebene falsche Menge könnte erneut angeboten werden. D06 muss diese Lücke vor Produktivbetrieb schließen.

## 5. Atomare Grenzen und Rennen

| Rennen | Gemeinsame Prüf-/Schreibgrenze | Erwartetes Ergebnis |
|---|---|---|
| Zwei eingehende Anfragen beanspruchen dieselbe freie Kopie | Beide Accepts serialisieren Inventory-/Hold-Prüfung und Speicherung | Erste gültige Annahme hält Menge, zweite wird ohne Teilannahme ungültig. Mehrfachkopien bleiben mengenbasiert. |
| Ausgehendes Senden versus eingehende Annahme | Gemeinsame zentrale Supply-/Need-Sicht, nicht zwei eigene Cacheprüfungen | Kein negativer Rest und keine Überschneidung durch getrennte Services. |
| Vierte ausgehende Anfrage / zwei parallele Sends bei Count=2 | Nutzerbezogene Count-Prüfung und Hold-/Requestcommit in derselben Grenze | Nur ein neuer dritter Request; incoming bleibt unbegrenzt. |
| Accept versus Withdraw/Expiry | Erwarteter offener Status/Revision und autoritative Zeit unter derselben Grenze | Genau ein Gewinner. Wenn zuerst accepted, kein späteres Pending-Release. |
| Original-Accept versus Gegenangebot | Vergleich auf aktuelle Originalrevision; alte/new Holds und Counterzählung gemeinsam | Entweder ursprünglicher Vertrag angenommen oder einziges Gegenangebot aktiv, nie beide. |
| Bestand/Präferenz/Need ändert sich nach Preview | Snapshotkonkrete Validierung innerhalb Commitgrenze | Preview gilt nicht als Freibrief; unbeteiligte Änderungen kein pauschaler Reject. |
| Zwei verschiedene Amendment- oder Foto-Revisionsaktionen | Expected-version auf Proposal, Deal und Kontrollpaket | Keine gemischte Zustimmung aus alten und neuen Paketen. |
| Letzte Fotobestätigung versus Foto-/Adressänderung | Reviews, Adresssnapshots und Freigabeversion gemeinsam serialisieren | Nur die tatsächlich bestätigte Kombination wird sichtbar; D05 für spätere Änderung. |
| Versand versus Cancel/Amendment | Richtungsnachweis, wirksame Version und Mengenholds gemeinsam prüfen | Erste physische Bewegung sperrt normalen Cancel/Änderung; keine Lagerfreigabe nach Abgang. |
| Receipt-Evidence versus Versandklick | Beide verwenden denselben eindeutigen Abgangsdatensatz plus Mengenledger | Ein Abgang, korrekte separate Akteurs-/Evidenzzeiten, höchstens ein Zugang. |
| Doppeltes/teilweise überlappendes Receipt | Bisher gebuchte Positionssummen und Command-ID in derselben Grenze | Nur neue akzeptierte Deltas; Refresh oder zweiter Tab addiert nichts doppelt. |
| Verlustmeldung versus verspätete Ankunft | Richtungsrevision und aktuelle tatsächliche Ankunft | Reale Ankunft gewinnt fachlich gegenüber weiterem „nicht angekommen“; Historie bleibt. |
| Bewertung/Publikationsjob parallel | Individuelle Berechtigung, Fristen, unique Rating und blindes Sichtbarkeitskriterium gemeinsam | Keine zweite Bewertung, keine vorzeitige Offenlegung durch Aggregate. |

Unter SQLite zeigen vorhandene Services `BEGIN IMMEDIATE` als brauchbares Transaktionsmuster. Spätere Backendwahl darf anders sperren, muss aber dieselben Grenzen gewährleisten. Ein `SELECT`, danach unabhängiger Commit in anderem Service genügt nicht. Keine verschachtelten Services mit eigenem Commit in einer größeren Domaintransaktion; existierende interne Hooks/Savepoints müssen bewusst komponiert werden.

## 6. Idempotenz, Ausfälle, Events

Ein Command hat einen dauerhaften fachlichen Idempotenzschlüssel; Browserbutton-Deaktivierung oder sessionStorage allein reicht nicht. Identischer Retry erhält das gespeicherte Ergebnis und dieselben IDs/Zeiten. Geänderter Payload bei gleichem Schlüssel wird zurückgewiesen. Nach Timeout/Refresh muss der Client den bestehenden Vorgang abfragen können.

Requeststatus, Reservierung, Inventardelta und deren idempotenter Nachweis gehören in dieselbe Transaktion. Inventory-History muss denselben Ledgerbezug verwenden. Ein späterer Ausfall der Notificationzustellung rollt keinen bereits erfolgten physischen Zustand scheinbar zurück; deduplizierte Zustellung aus persistiertem Ereignis/Outbox-Hook. Hier keine Queue implementieren.

Fotos benötigen zusätzlich robuste Objekt-/Metadatenkoordination: Upload allein ist keine Vorbereitung; erst referenziertes vollständiges Paket wird bestätigt. Verwaiste Uploads sind nicht sichtbar und brauchen spätere Retentionbehandlung. Keine Transaktion behaupten, die Cloudobjekte automatisch zusammen mit SQL rollbackt.

Ein Absturz darf keine Zwischenlage mit freigegebenem Hold, unverändertem P und anschließend erneut angebotener Ware hinterlassen. Wird Reconciliation benötigt, bleibt sie explizit und sperrt die strittige Verplanung; sie darf nicht als stiller erfolgreicher Vollabschluss erscheinen.

## 7. Spätere Pflicht-Tests

Für jeden T01–T32: erlaubte Rolle, falsche Rolle, falscher Contract-Type, stale Revision, Doppelaufruf, veränderter Payload bei gleichem Schlüssel, Clockgrenze und rollback nach jeder Schreibstufe. Zusätzlich Paralleltests mit zwei Verbindungen für die Rennen oben.

Pflichtfälle: 3→4 offene Requests; beliebig viele eingehende/angenommene bei verfügbarer Supply; drei Überschusskopien mit Teilreservierung; Revalidierung ohne Selbstblockierung eigener Holds; unbeteiligte Inventaränderung; genau ein Gegenangebot; asymmetrische manuelle Perspektive; 23→22 Same-/Cross-Reduktion; spätere Fotoänderung nach Review; keine Adresse vor beidseitiger Barriere; beide Versand-/Receipt-Reihenfolgen; 30→29→30 ohne Doppelbuchung; falsche/beschädigte Ware; Nichtankunft am Tag 6/7 und „doch angekommen“; vollständiger/qualifizierter Abschluss; Rating einer Seite vor Gesamtabschluss und Blindheit in Detail/Notification/Aggregat.

Bestehende Legacy-/V1-, SAP-, PROFILE-TRADE-, SmartDeal- und Stackgates bleiben separat erhalten. Preview-Tests beweisen kein produktives Mehrbenutzer-/Transaktionsverhalten. In LIFECYCLE-00 wurden diese neuen Lifecycle-Tests nicht implementiert oder ausgeführt.

## 8. Zusätzliche Prüffälle aus 00A (spezifiziert, nicht ausgeführt)

- Ship versus Receipt-Evidence in beiden Reihenfolgen und parallel: ein Abgang pro tatsächlich versendeter Menge, nur akzeptierte Zugänge, atomare Richtungs-/Holdänderung; kein erfundener Absenderzeitpunkt.
- Eigene Vorbereitung bei accepted_at +71h59m fertig, Gegenprüfung später: keine Verletzung der eigenen 72h-Packfrist allein wegen der fremden Prüfung, kein automatischer Review-Abbruch.
- Beidseitiges CROSS bei Accept, danach globale SAME-/Pool-Änderung: angenommener Snapshot und darin gültige Reduktion bleiben zulässig. Neue/offene Angebote prüfen dagegen die aktuellen Einstellungen.
- Legacy und neuer V1 reservieren dieselbe letzte freie Kopie: höchstens ein Gewinner; gesondert prüfen, dass eine zulässige Alt-Mehrfachzusage nicht fälschlich als doppelte physische Reservierung derselben Kopie behandelt wird. Grenzen der Need-Exklusivität und verbindliche Option A siehe [00A](TRADE_LIFECYCLE_00A_NEED_CLAIMS.md).

## 9. Verbindliche Claim-Invarianten (00B)

TRADE-LIFECYCLE-V1 ist fachlich geschlossen; keine Startblockade von L01. Spätere Gates bleiben bestehen.

- NQ1: Send erzeugt eigenen Give-Hold und eigenen Receive-Mengenclaim gemeinsam. Kein fremder Hold/Claim ohne Zustimmung.
- NQ2: Summe neuer konkurrierender Claims überschreitet unter atomarer aktueller Prüfung keinen freien Bedarf. Eigene Claim-Credits beim Accept verhindern Selbstblockierung.
- NQ3: Withdraw/Decline/Expiry/terminales Invalidieren lösen exakt beide Bindungen; Retry erzeugt weder Geister-Claim noch zweite Freigabe.
- NQ4: Accept überführt Pending nach verbindlich ohne freie Zwischenphase und ohne doppelte Subtraktion; Gegenangebot ersetzt Claims atomar.
- NQ5: Bedarf 2, Claim 1 → Rest 1; weiterer Claim 1 → Rest 0; zusätzlicher Claim 1 abgelehnt. Bestand/verbindlicher Eingang reduzieren vorher dieselbe Bedarfsbasis. Kein globaler Unique-Key darf einen legitimen zweiten Mengenclaim verhindern.
- NQ6: Legacy und neuer Vertrag respektieren dieselbe physische Supply. Alte Need-Regeln werden nicht rückwirkend verschärft; keine neue Parallelbuchung oder negativer Bestand.

Diese Fälle sind spätere Testanforderungen, keine in 00B ausgeführten Runtime-Tests.
