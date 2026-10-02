# TD-1 — Trade Area / Pre-Design Technical Debt Audit

Stand: 2026-09-13. **Audit abgeschlossen; keine Implementierung. Morgen kann die PO-Designphase beginnen.** 12 Findings: 0 CRITICAL, 2 HIGH, 6 MEDIUM, 4 LOW. Drei eng begrenzte SAFE-CLEANUP-Kandidaten; keine technische Schuld hebt die bestehende Designfreigabe auf.

## Grundlage, Methode und Grenzen

Berücksichtigt: [Trade UX SOLL](TRADE_UX_SOLL_V1.md), [Q1–Q8 und NP-C3-1](TRADE_UX_PO_DECISIONS_Q1_Q8.md), [Manual Offer Contract](MANUAL_OFFER_DOMAIN_CONTRACT_V1.md), [Next Blocks Tech Prep](TRADE_NEXT_BLOCKS_TECH_PREP.md), [Product Bible](SMARTDEAL_PRODUCT_BIBLE_V1.md), [Algorithm Contract](SMARTDEAL_ALGORITHM_CONTRACT_V1.md), [Roadmap](SMARTDEAL_TECHNICAL_ROADMAP_V1.md), [CG-1-Reaudit](SMARTDEAL_CORE_GATE_REAUDIT_CG1.md). Die jüngsten PO-Nachträge haben Vorrang vor historischen Beschreibungen. NP-C3-1 bleibt geschlossen; keine neue Retention- oder Produktregel.

T9 mit 46 Route-Patterns und 167 Kantenstellen wurde als Ausgangspunkt wiederverwendet. Dieser Audit zählt diese Arbeit nicht erneut als neue Routenprüfung. Geprüft wurden konkrete Definitionen, Callsites, Flask-Registrierungen, SQL-/Transaktionsgrenzen, Schema-/Releasewerkzeuge und einschlägige Tests. Referenzsuche in App, tests und Scripts; ergänzend Release-Allowlist und Dokumentation. Zeilen beziehen sich auf den aktuellen Worktree. Keine App importiert, kein HTTP-/Browserlauf, kein Test/Benchmark, keine Migration und keine DB-Abfrage. Aussagen über Abdeckung sind statische Testinhaltsbefunde, keine neue grüne Testausführung.

Die Baseline **1251/1251 GREEN** bleibt ein vorheriger Nachweis. Kein neuer erreichbarer CG-1-Web-Bypass wurde im geprüften Pfad belegt; daraus folgt keine pauschale Sicherheitsgarantie für künftige Aufrufer. HIGH bezeichnet insbesondere belegte Integrations- und Absicherungsrisiken, keinen nachgewiesenen aktuellen Exploit.

## Register

| ID | Kategorie | Risiko | Aufwand | Empfehlung | SAFE CLEANUP |
| --- | --- | --- | --- | --- | --- |
| TD-001 | A Dead Code | LOW | XS | FIX NOW | JA |
| TD-002 | H Documentation Drift | LOW | S | FIX NOW | JA |
| TD-003 | G Test Debt | HIGH | M | FIX NOW | JA |
| TD-004 | C Legacy Leakage / E Domain Boundary | HIGH | M | FIX BEFORE T7 | NEIN |
| TD-005 | D Redirect-/Origin Debt | MEDIUM | M | FIX BEFORE T10 | NEIN |
| TD-006 | D Alias-/Handler Debt | MEDIUM | S | FIX BEFORE T10 | NEIN |
| TD-007 | B/E/I Projektionen und Statusableitung | MEDIUM | L | FIX BEFORE T10 | NEIN |
| TD-008 | B/E Manueller Web-Domainpfad | MEDIUM | L | FIX BEFORE T10 | NEIN |
| TD-009 | E/I Transaktionen und Fehlerdiagnose | MEDIUM | M | FIX BEFORE T7 | NEIN |
| TD-010 | F Release-/Schemaversionierung | LOW | M | FIX BEFORE RELEASE | NEIN |
| TD-011 | G Implementierungsgebundene UI-Tests | LOW | S | LEAVE ALONE | NEIN |
| TD-012 | I/G Integrierter Lastnachweis | MEDIUM | L | FIX BEFORE RELEASE | NEIN |

Aufwand ist eine relative Schätzung für den genannten engen Lösungsschritt, keine Zusage für ganze T7/T10-Blöcke. SAFE CLEANUP bewertet einen möglichen späteren Patch: keine neue Produktsemantik, Migration, Lifecycleänderung, Routenentfernung oder Privacyänderung; ausreichender vorhandener oder klar ergänzbarer fokussierter Testschutz. Hier wurde keiner dieser Patches ausgeführt.

## Einzelbefunde

### TD-001 — Verwaister Versandstatus-Renderer

**Datei/Funktion:** `App/webapp.py:8265`, `trade_shipping_status_html` (44 Zeilen).

**Beleg:** Namenssuche in App/tests/Scripts findet ausschließlich die Definition. Keine Route dekoriert diesen Helper; kein Alias oder Callback referenziert ihn. Der aktive Detailpfad ruft `trade_product_status_html` (`webapp.py:8959`) und die Timeline auf. Dagegen haben `trade_shipping_status_label`, `trade_status_chip` und `trade_candidates` reale Runtime- beziehungsweise Testreferenzen und gehören nicht in diese Entfernung.

**Schuld/Risiko:** Ein nicht gerenderter Parallelbaustein mit eigener Versand-/Empfangsmicrocopy kann beim Umbau fälschlich als aktive Vorlage wiederverwendet werden. LOW, XS, FIX NOW, SAFE CLEANUP JA.

**Empfehlung/Schutz:** Nur diesen unregistrierten Helper entfernen; keine CSS-Regel, Route oder benachbarte Funktion mitlöschen. Bestehende Detail-/Timeline-/Receipt-Tests (`test_uif005b_trade_detail_product_integration.py`, `test_s18_trade_lifecycle_timeline.py`, `test_s19_receipt_ux_hardening.py`) plus erneute Referenzsuche. Keine neue semantiklose „Funktion existiert nicht“-Assertion nötig.

### TD-002 — Aktuelle Lesewege enthalten noch historische Offen-/Zeitangaben

**Dateien/Stellen:** `docs/TRADE_UX_SOLL_V1.md` §10 und §9; `docs/SMARTDEAL_ALGORITHM_CONTRACT_V1.md:320`, AC30 Case 15.

**Beleg:** UX §10 sagt weiterhin „Fehlende Anbindungen/Typentscheidungen C8 bleiben markiert; keine neue Notificationart wird hier beschlossen“, während Q7 im verbindlichen Decision Record bereits entscheidet, welche Nachrichten erforderlich sind. AC30 Case 15 nennt `created_at+24h`; aktueller PO-Vertrag und Runtime verwenden allein `binding_created_at+24h`. Der Kopf des UX-Dokuments erklärt zwar historische Konflikttabellen, aber der laufende §10-Text ist leicht isoliert misszuverstehen. §9 kann für den inzwischen geschlossenen Kontaktlebenszyklus unmittelbar auf NP-C3-1 verweisen.

**Schuld/Risiko:** LOW, S, FIX NOW, SAFE CLEANUP JA. Keine echte neue Produktfrage: maßgebliche Entscheidungen sind vorhanden. Case 15 ist eine veraltete Basisbezeichnung, keine Ermächtigung zur Friständerung.

**Empfehlung/Schutz:** In einem separat erlaubten Dokumentationspatch aktuelle Querverweise und Zeitbasis präzisieren; historische Entscheidungsspuren erhalten. Q7 verlangt keine eigenständige Empfangsnotification. Kein Algorithmus-/Produktvertrag neu entscheiden und keine Frist im Code ändern. Dokumentvergleich gegen Q7/NP-C3-1/AC23 und `smartdeal_expiry.py`; Links/Whitespace prüfen, keine Runtime-Tests erforderlich.

### TD-003 — V1-Handlergrenzen noch nicht als vollständige HTTP-Matrix abgesichert

**Dateien/Funktionen:** `tests/test_smartdeal_cg1.py:26` (`CoreGateTests.handler`), `:176` (`blocked_test`); Auth-/Routekontrollen in `tests/test_s32_auth_session_csrf.py`, `tests/test_s33_http_integrity_hardening.py`, `tests/test_s07_deep_link_origin_context.py`.

**Beleg:** CG-1 erstellt `test_request_context('/trade/action')`, patcht `current_user_id` und ruft `getattr(webapp,name)(request_id)` direkt auf. Das schützt reale Handler, Domainwirkung, Rollback und Tabellen-Reopen, durchläuft aber nicht Flask-URLdispatch samt Before-Request/Auth/CSRF für jede konkrete V1-URL. Die sieben generierten Sperrentests sind echte verschiedene Handlerfälle, keine redundanten Kopien. Bestehende HTTP-Schutztests decken Auth/CSRF grundsätzlich ab, ersetzen jedoch diese zusammengesetzte synthetische V21-Matrix nicht.

**Schuld/Risiko:** HIGH als Regressionserkennungsrisiko beim Umverdrahten, M, FIX NOW, SAFE CLEANUP JA. Kein Beleg für derzeit fehlendes Auth/CSRF in der Runtime; der CG-1-Bericht beschreibt seine Testgrenze korrekt.

**Empfehlung/Schutz:** Additive Testdatei `tests/test_trade_http_contract_boundaries.py` vorgeschlagen: synthetische V21-DB, realer Testclient und echte Registrierungen, Authsession/CSRF; V1-Accept/Decline/Withdraw, alle sieben gesperrten physischen POSTs, beide Rollen/Fremder/anonym, fehlendes CSRF, plurale Hinweiswege und Legacy-Kontrolle. Nach Ablehnung persistierten Gesamtzustand unverändert prüfen, nach Erfolg exakten Domainzustand; Alias nicht als Command voraussetzen. Keine öffentliche V1-Create-Route erfinden, keine CHECKs für einen Unknown-String umgehen. Bestehender Unknown-Classifier-Test bleibt zuständig. Neue Datei bei späterem Auftrag in `docs/R5_RELEASE_FILES.json` aufnehmen, damit der isolierte Releaseexport sie tatsächlich ausführt. Bestehende CG-1-, S32/S33- und Journeytests ergänzen, nicht ersetzen.

### TD-004 — Legacy-Mutatoren verlassen sich auf äußere Contract-Gates

**Dateien/Funktionen:** `App/services/trade_shipping.py:175` (`ship`), `trade_receipt.py:311` (`receive`), `trade_reservations.py:382` (`release`), `App/webapp.py:8065/8098` (`complete_trade`, `complete_trade_if_ready`). Gegenbeleg: `App/services/smartdeal_runtime.py:11` und `App/webapp.py:149`.

**Beleg:** Ship/Receive laden Request plus Lifecycle und prüfen Rolle/Status, aber keinen eigenen `contract_type`. `release` lädt den Lifecycle per Request-ID und setzt aktive Reservationen/Status ohne Contractklassifikation; es ist ein caller-owned Low-Level-Writer. Alte Completion verarbeitet `album_id` plus JSON-Listen und bucht beide Richtungen. Die aktuellen gefährlichen HTTP-Handler passieren vorher den CG-1-Dispatcher; nicht freigegebene V1-Aktionen enden dort. `contract_type` ist durch 0021 unveränderlich. Somit kein belegter TOCTOU-Contractwechsel oder aktueller HTTP-Bypass.

**Schuld/Risiko:** HIGH für zukünftige direkte Wiederverwendung bei T7/UI-Integration; M, FIX BEFORE T7, SAFE CLEANUP NEIN. Ein neuer Aufrufer könnte die geschützte Webgrenze umgehen oder die alte Single-Album-Completion verwenden.

**Empfehlung/Schutz:** Vor T7 die zulässigen Service-Entry-Points und internen Writeprimitiven explizit abgrenzen und die neue Contractdispatch-/Adaptergrenze festlegen. Nicht einfach einen Guard in jeden generischen Low-Level-Writer setzen: bestehende Kompositionen und Transaktionen benötigen gezielte Prüfung. Direkte Legacy/V1-Grenztests, Mehralbum-Exactly-once, Legacy-S14/S15/S16/S17, CB002 und CG-1. Die neue physische Funktion ist T7-Arbeit, kein heutiger Cleanup.

### TD-005 — Rücknavigation verteilt, Kontextverlust und ungeprüfter Referrer

**Dateien/Funktionen:** `App/webapp.py:8706` `trade_detail_back_context`; `:161` V1-Erfolgsredirect; `:10719/10734/10756/10826/11165` Legacy-Aktionsredirects; `:11587–11656` alte Confirm/Fail-Rückwege. T9-Register enthält die einzelnen Kanten.

**Beleg:** Detail hat vier erlaubte origin-Werte. Mehrere Aktionshandler verwenden direkt `request.referrer or fallback`; dies ist nicht derselbe Allowlistmechanismus. V1-Erfolg geht ohne origin zum Detail. Archiv verlinkt Detail ohne Archivorigin; Rating/Problem verlieren den Kontext ebenfalls. Ein externer Referrer kann hier als Location übernommen werden, wenn ein berechtigter Request bis zu diesem Branch gelangt; keine behauptete CSRF-Umgehung.

**Schuld/Risiko:** MEDIUM, M, FIX BEFORE T10, SAFE CLEANUP NEIN, weil Rücksprungverhalten geändert würde.

**Empfehlung/Schutz:** Ein explizites erlaubtes Back-/Kontextmodell für SOLL, kanonische lokale Fallbacks und validierte Referrerbehandlung. Bestehende URLs nicht entfernen. S07/R2/UIF005b/S24/CB009 plus externe/protokollrelative/malformed Referrer, fehlender origin, Archiv/Inbox und Mehralbumkontext; Domainwirkung unverändert. Kein vorschnelles globales Redirect-Rewrite vor PO-IA-Integration.

### TD-006 — Gleich aussehende Pluralpfade haben unterschiedliche Commandwirkung

**Dateien/Routen:** `App/webapp.py:11567` plural accept, `:11679` plural decline, `:11686` plural confirm, `:11691` plural cancel; echte singuläre Handler ab `:10652`; Detail-/Composer-Aliase im T9-Inventar.

**Beleg:** Plural accept/decline/confirm liefern Hinweisredirects nach Trades. Plural cancel delegiert V1-Withdraw und liefert für Legacy einen Hinweisfallback. Dagegen sind singular/plural Detail und Composer echte Registrierungsaliase derselben Funktion.

**Schuld/Risiko:** MEDIUM, S, FIX BEFORE T10, SAFE CLEANUP NEIN. Ein mechanischer URL-Namensabgleich würde wirkungslose Forms oder unbeabsichtigte Aktionen erzeugen; die Handler sind erreichbar und nicht Dead Code.

**Empfehlung/Schutz:** Beim Wiring eine explizite Command-/Kompatibilitätsmatrix verwenden und jede tatsächlich gerenderte Form gegen registrierten Handler und Resultat prüfen. Keine Routenlöschung, keine automatische Aliasangleichung. Additive HTTP-Matrix TD-003 schützt den IST; spätere SOLL-Tests dokumentieren bewusst geänderte Ziele.

### TD-007 — Mehrfache Status-/Cardprojektion in großen Viewfunktionen

**Dateien/Funktionen:** `App/webapp.py:8174` `trade_status_label`, `:8247` Shippinglabel, `:8442` Productstatus, `:8555` Primaryaction, `:9095` Albumtrades, `:11170` Overview; `:3140` Statuschip.

**Beleg:** Albumtrades umfasst 334, Overview 394, Trade Detail 290 und Composer 642 Zeilen laut AST. Mehrere Pfade kombinieren Requeststatus, Shipping/Receipt/Problem und eigene Darstellung. Konkreter Drift: `trade_status_label` gibt für obsolete „Nicht mehr verfügbar“ zurück; Chip-Mapping kennt „Obsolet“ als obsolete-Variante, daher fällt das erste Label auf muted zurück. Die Canonical-Success-Projektion wird dagegen bereits von `trade_is_successfully_completed` wiederverwendet; nicht alles ist doppelte Domainwahrheit.

**Schuld/Risiko:** MEDIUM, L, FIX BEFORE T10, SAFE CLEANUP NEIN. Neues „Handlungsbedarf“-Rendering könnte von tatsächlichen Commandgrenzen abweichen. Funktionsgröße allein wäre kein Finding; die mehrfachen Ableitungen und konkrete Labelkopplung sind der Nutzenbeleg.

**Empfehlung/Schutz:** Bei der geplanten Integration eine kleine read-only Zustands-/Next-Action-Projektion mit maschinenlesbarem Zustand, Rollen und Contractgrenze verwenden; Darstellung darauf aufbauen. Keine komplette webapp-Aufteilung auf Vorrat. Statusmatrix einschließlich terminalem Problem, Retry und gesperrtem V1; S18/UIF005b/CB010, nicht nur CSS-Substringchecks. Die kleine Chipabweichung allein rechtfertigt keinen heutigen Layoutpatch vor neuem Design.

### TD-008 — Manueller Alt-Submit enthält Domainorchestrierung im Webhandler

**Dateien/Funktionen:** `App/webapp.py:9663` Composer, `:9644` Availabilitykandidaten, `:10556` Create, `App/services/trade_reservations.py` accept; `App/services/album_privacy.py` und `community.py`.

**Beleg:** Create prüft Community/Pool, resolve_code, nichtleere Listen, G>=R, beide Mengen und führt direkt INSERT/Notification/Commit aus. Composer wiederholt die Interaktions-/Pool-/Availabilityvorbereitung. Es entstehen Legacy-Anfragen; Bindung erst beim Accept. Das ist der geschützte IST, kein fehlerhafter neuer Manual-Offer-Submit. Neue globale Empfängerpräferenz und atomare beidseitige Submitbindung fehlen bewusst.

**Schuld/Risiko:** MEDIUM, L, FIX BEFORE T10, SAFE CLEANUP NEIN. Copy/Paste dieses Webpfads als neuen Composer würde den geschlossenen Manual Contract verfehlen.

**Empfehlung/Schutz:** Den neuen Vertrag unabhängig von der UI implementieren, vorhandene kanonische Reader wiederverwenden, alte Submitsemantik erhalten. Kein generischer Merge mit SmartDeal-1:1/min5/Quota. Neue Domain-/Race-/Rollback-/Preferencefälle nach Manual Contract, plus CB011, S14/S22 und Legacy-Journeys. Fehlende neue Produktfunktionen werden nicht nochmals als zusätzliche Debt-Findings gezählt.

### TD-009 — Uneinheitliche Ownership von Transaktionen und Fehlerursachen

**Dateien/Funktionen:** `App/services/smart_trade_requests.py:162` inspect und `:200/261/273` Mutationen/Commits; `trade_shipping.py:429`, `trade_receipt.py:488`, `trade_problems.py:571/871/1097`; `smartdeal_release.py:39`, `smartdeal_acceptance.py:52` als Gegenbeispiele.

**Beleg:** Das scheinbar prüfende Legacy-inspect kann expired/obsolete schreiben und committen. Ship/Receipt fangen breit Exception, rollen zurück und geben generischen TRANSACTION_ERROR zurück; dort bleibt die konkrete unerwartete Ursache ohne eigene Weitergabe/Diagnose. V1-Transaktionswrapper prüfen dagegen idle connection, unterscheiden BUSY und werfen unerwartete Fehler nach Rollback weiter. `release` in TD-004 committet bewusst nicht selbst.

**Schuld/Risiko:** MEDIUM, M, FIX BEFORE T7, SAFE CLEANUP NEIN. Zusammensetzen selbst commitender Commands kann Atomizität zerstören; pauschale Fehlercodes erschweren Diagnose. Rollback selbst ist korrekt und darf nicht entfernt werden.

**Empfehlung/Schutz:** Vor T7 pro Entry-Point Ownership, erlaubte Caller-TX und Fehlerabbildung festhalten; bei notwendigen neuen Kompositionen einen einzigen Writeowner und interne nichtcommitende Primitive verwenden. Legacy-inspect nicht ohne Vertragsnachweis read-only machen. Unerwartete Ursachen später datensparsam diagnostizieren, ohne Payload-/Adresslogs; gesonderter Privacy-/Observabilityreview. Fehlerinjektion zwischen Writes, Busy, Caller-TX-Erhalt, Retry, Legacy-Codes prüfen. Kein bloßes Entfernen aller breiten except-Blöcke.

### TD-010 — Zweigleisiger V20-Releasebetrieb und V21-Core erfordern expliziten Cutover

**Dateien/Stellen:** `App/services/runtime_operations.py:12` EXPECTED_SCHEMA_VERSION=20, `App/webapp.py:333` Produktionsvalidierung; `Scripts/bootstrap_database.py:28`, `Scripts/prepare_release_tests.py:24`; `docs/R5_RELEASE_FILES.json`; `tests/test_sd_t1_contract_foundation.py:141`.

**Beleg:** Produktionsprüfung erwartet exakt V20, Bootstrap/Testvorbereitung migrieren gezielt bis20. Release-Allowlist enthält bereits Migration0021 und SmartDeal-Module. Foundationtest prüft ausdrücklich V20-Bootstrap plus nachfolgenden V21-Upgrade. V20-Tests wie `test_empty_database_reaches_v20_without_users_and_rejects_reuse` sind daher derzeit kein pauschaler Fehler. Ein V21-DB-Start unter unverändertem Produktionsvalidator würde abgewiesen.

**Schuld/Risiko:** LOW im noch nicht aktivierten Stand, M, FIX BEFORE RELEASE, SAFE CLEANUP NEIN. Es fehlt keine spontan nachzuholende Migration; der spätere aktivierende Release muss Runtime-, Bootstrap-, Manifest- und Teststand gemeinsam entscheiden und nachweisen.

**Empfehlung/Schutz:** Vor öffentlicher V1-Aktivierung ein ausdrücklich versioniertes Cutoverpaket planen, Fresh/Upgrade/Backout und Produktionsstart isoliert nachweisen. Nicht alle 20-Literale ersetzen. Aktuelle Migrationschecks/Trigger bleiben unverändert. Kein Index/Spaltenabbau aus Namens- oder Altersvermutung.

### TD-011 — Historische UI-Assertions sind teilweise Implementierungssnapshots

**Dateien/Funktionen:** `tests/test_uif005b_trade_detail_product_integration.py:139/149`, `tests/test_s31_ui_foundation.py:197/251`.

**Beleg:** `test_existing_trade_mutation_endpoints_remain_wired` sucht Pfadstrings im gesamten webapp-Quelltext. Ein solcher String beweist keinen erreichbaren Form-Handler-Fluss. Andere Tests binden CSS-Selektoren, Texte und konkrete Iconaufrufe. Daneben existieren echte gerenderte HTTP-/Lifecycletests; diese sind keine bloße Duplikation.

**Schuld/Risiko:** LOW, S, LEAVE ALONE, SAFE CLEANUP NEIN. Heute schützen die Assertions freigegebene Altgestaltung. Ihr Entfernen ohne beschlossenen Nachfolger würde Testschutz schwächen.

**Empfehlung/Schutz:** Bei jeweils freigegebenem T10-Screen historische Visualassertions bewusst auf den neuen Vertrag abbilden; Command-/Privacy-/Bestandsassertions erhalten und durch TD-003 ergänzen. Keine breite Testbereinigung vor Design. Keine belegte unnötige doppelte Domain-Testkohorte gefunden.

### TD-012 — Gesamtlast des künftigen Nutzerwegs noch nicht nachgewiesen

**Dateien/Funktionen:** `App/services/smartdeal_runtime.py` cleanup/discover, `smartdeal_release.py:74` sweep; `tests/research/benchmark_smartdeal_cleanup.py`, `benchmark_smartdeal_runtime.py`; `docs/SMARTDEAL_CORE_GATE_REAUDIT_CG1.md` Y2.

**Beleg:** Sweep selektiert offene V1-Requests innerhalb einer Schreibtransaktion; Aufwand wächst mit deren Anzahl. CG-1 misst 0/3/30 fällige Requests (Mittel 0,033/0,921/5,801ms), nennt ausdrücklich keinen Gesamtlastnachweis. Y2 bleibt T11. Der T3b-Performancefix ist ACCEPTED/LOCKED und kein Beleg für die vollständige spätere HTTP-/Kontakt-/Lifecyclekette.

**Schuld/Risiko:** MEDIUM, L, FIX BEFORE RELEASE, SAFE CLEANUP NEIN. Bekannte Messschuld, keine neu nachgewiesene schlechte Performance und kein Designblocker.

**Empfehlung/Schutz:** In T11 isolierten integrierten Mehrnutzerlauf mit deklarierten Pool-/Requestgrößen, SQL-/Lock-/CPU-Anteilen und konkretem öffentlichen Flow messen. Keine vorgezogenen Indizes, Caches, Scheduler oder Optimizervereinfachung ohne Messung; bestehende R4-/T3b-Verträge schützen.

## Abdeckung aller Auditbereiche und bewusste Nicht-Findings

| Bereich | Ergebnis |
| --- | --- |
| A Dead Code | Ein belegter unreferenzierter Renderer TD-001. Dekorierte Handler mit nur einer Namensfundstelle bleiben registriert erreichbar. `trade_candidates` wird in S09/S11/S19 als Vergleich genutzt; `complete_trade_if_ready` im alten Confirmhandler. Nicht löschen |
| B Duplication | TD-007/008. Mehrfache frische Prüfung in Read und atomarem Submit ist notwendig gegen Races; nicht als unnötige Duplizierung entfernen. Legacy48h und V1-24h sind verschiedene Verträge |
| C Legacy Leakage | TD-004. CG-1 prüft vor den relevanten Webmutationen, Unknown fail closed. Community.block unterscheidet V1-Pending-Release und Legacy-Update ausdrücklich (`community.py:416–435`), kein neuer Block-Bypass belegt |
| D Routes | TD-005/006, T9 wiederverwendet. Keine Route wegen unähnlicher Schreibweise oder Hinweiswirkung als tot klassifiziert |
| E State/Domain | TD-004/007/008/009. Canonical-Success-Projektion bereits wiederverwendet; qualifizierter Problemabschluss bei Rating ist gewollt, kein Drift |
| F DB/Migration | TD-010. 0021 schützt Contract-Type und gesetzte Bindungs-/Annahmezeit durch Trigger; Downmigration verweigert unbeabsichtigtes V1-Backout. JSON-Kompatibilitätsfelder/alte Confirmmarker werden tatsächlich gelesen; nicht ungenutzt. Keine belegte überflüssige Indexstruktur oder fehlende neue Pflichtconstraint im gesperrten Core; ohne Queryplan/Last kein Indexpatch. Kein DBinhalt benötigt |
| G Tests | TD-003/011/012. Vorhandene V1-Foundation-, Mirror-, Oracle-, Release-, Rollback- und Racefälle erhalten. V20-Kontroll-/Bootstrapannahmen sind von aktuellen V21-Fixtures zu unterscheiden; keine neue Testausnahme |
| H Dokumentation | TD-002. Roadmap und alte Abschlussberichte sind zeitgebundene Spezifikationen/Nachweise; nicht jeden historischen Zukunftssatz als Fehler zählen. Aktuelle Prep schließt NP-C3-1 korrekt |
| I Hygiene | TD-007/009/012. Suche TODO/FIXME/HACK/XXX im aktiven webapp- und relevanten Trade/SmartDeal/Inventory/Notification/History-Servicebereich ergab keinen eigenständigen konkreten Blocker. Breite Exceptionhandler mit Rollback/erneutem raise sind nicht per se falsch |
| Availability/Discovery | Kanonische Inventory-/Availabilityreader vorhanden; T2a berücksichtigt reale Bindungen und zugesagte Needs. Profilöffentlichkeit und Tradepool bleiben getrennt. Unterschiede zwischen Coverage, isoliertem Paaroptimum und globalem Plan nicht vorschnell vereinheitlichen |
| History/Privacy/Notifications | History-Eventkeys/Exactly-once und SuccessfulTradeProjection sind Reuse-Basis. Typed-Ziele prüfen Beteiligung, Inbox prüft Eigentümer. Kein belegter neuer Adressleak: T8a noch nicht implementiert. Fehlender Q7-Accept-Typ ist geplanter Adapterbedarf, keine Ermächtigung zu neuer Notificationsemantik |
| Historische Appkopien | webapp_backup/broken_now/rescue_candidate sind im Release-Inventar als Altmaterial ausgewiesen. Nicht als aktive Handler gezählt und nicht zum Anlass einer Repo-Aufräumaktion genommen |

## Priorisierung

**A. QUICK WINS — heute sinnvoll:** TD-001, TD-002, TD-003. Drei FIX NOW und drei SAFE CLEANUP; auch diese benötigen einen gesonderten Implementierungs-/Dokumentationsauftrag. Kein Patch ist Voraussetzung für den Beginn der Designgespräche.

**B. PRE-T7/T10 — sechs Findings:** TD-004 und TD-009 vor T7; TD-005/006/007/008 vor T10. Den passenden Integrationsblock nutzen, nicht einen zweiten parallelen Refactoringstrang eröffnen.

**C. LATER — drei Findings:** TD-010 und TD-012 vor Release; TD-011 jetzt LEAVE ALONE, später nur mit freigegebenem UI-Nachfolger anfassen.

### Die höchstens drei heutigen Kandidaten konkret

| Kandidat | Warum jetzt / erwartete Änderung | Exakte Patchdateien | Notwendiger Schutz | Risiko |
| --- | --- | --- | --- | --- |
| TD-001 | Ungenutzte alternative Darstellung aus dem künftigen Arbeitsbereich entfernen; ausschließlich 44-Zeilen-Helper löschen | `App/webapp.py` | Referenzsuche; UIF005b, S18 Timeline, S19 Receipt UX | LOW |
| TD-002 | Morgen keine bereits geschlossenen Fragen oder falsche Fristbasis übernehmen; gezielte Text-/Linkkorrektur | `docs/TRADE_UX_SOLL_V1.md`, `docs/SMARTDEAL_ALGORITHM_CONTRACT_V1.md` | Abgleich Decision Record/AC23/Expiry; Dokumentdiff und Whitespace | LOW |
| TD-003 | Vor Umverdrahtung reale HTTP-Schutzmatrix etablieren; ausschließlich additive Tests | Neue `tests/test_trade_http_contract_boundaries.py`, `docs/R5_RELEASE_FILES.json` | Neue V21-Matrix plus CG-1/S32/S33; keine bestehende Assertion löschen, isolierte synthetische DB | LOW für den test-only Patch; HIGH bleibt das ungesicherte Integrationsrisiko |

TD-003 hat M-Aufwand und kann mehr Zeit beanspruchen als die beiden ersten Kandidaten. Kein Grund, zur Einhaltung eines Tagesplans die bestehende Runtime oder Testverträge zu verändern. Bei seiner späteren Umsetzung neue Testdatei ausdrücklich in den Releaseexport aufnehmen und Testgesamtzahl frisch berichten.

## Abschluss und Dateischutz

- **12 Findings: 0 CRITICAL / 2 HIGH / 6 MEDIUM / 4 LOW.** SAFE CLEANUP 3; FIX NOW 3; PRE-T7/T10 6; LATER 3.
- Größte Legacy-Gefahr: direkte Wiederverwendung nicht selbst contractbewusster alter Buchungs-/Release-/Completionpfade unter Umgehung des heutigen äußeren CG-1-Gates (TD-004).
- Größte Testschuld: kombinierte echte V21-URL/Auth/CSRF/Command-Matrix fehlt trotz guter direkter Handler-/Domainnachweise (TD-003).
- Größte Route-/Handlerschuld: verstreute Rücknavigation und nicht gleichwirkende singular/plural Aktionswege (TD-005/006).
- **Grund, morgen NICHT mit Design zu beginnen: NEIN.** Alle sechs Designbereiche bleiben GREEN, 0 neue RED/ORANGE-Produktblocker. Technische Umsetzung bleibt separat freizugeben.
- Genau eine neue Auftragsdatei: `docs/TRADE_TECH_DEBT_AUDIT_TD1.md`. Keine bestehenden Dokumente korrigiert und keine Quick Wins implementiert.
- Runtime/UI/Routes/DB/Migrationen/Tests unverändert gegenüber dem Auftragsbeginn. Keine Tests ausgeführt. Validierung: `git status --short`, `git diff --stat`, `git diff --check` sowie Dateihashvergleich und eigene Whitespaceprüfung für die ungetrackte Auditdatei.
- Kein git add, kein Commit, kein Push, kein Deploy. STOP nach Audit.
