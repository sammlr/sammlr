# SmartDeal Core Gate Reaudit CG-1

Stand 2026-09-12. **Core Gate GREEN. Design Gate GREEN. CG-1 Acceptance GREEN.** Diese Neubewertung ergänzt den unveränderten [ursprünglichen Audit](SMARTDEAL_CORE_GATE_AUDIT.md); Implementierung und konkrete Tests stehen im [CG-1-Nachweis](SMARTDEAL_CORE_GATE_FIX_CG1.md).

## Findings und Gate

O1 geschlossen: Alle belegten gefährlichen Web-Mutationspfade klassifizieren vor Legacy-Mutation. V1-Accept/Decline/Withdraw gehen ausschließlich an T6b/T5b. Nicht freigegebene Versand-/Empfangs-/Abschluss-/Problempfade sind gesperrt. Unknown Contract fail closed. Die bestehende Block-Integration bleibt erhalten.

O2 geschlossen: Ein expliziter Runtime-Cleanup läuft vor kanonischer interner V1-Discovery, bestehender SmartTrade-Berechnung und Trade-Inbox/Detail. Die unabhängige Fristprüfung verbleibt im Domainservice. Lazy-Freigabe erfolgt beim nächsten relevanten Zugriff; ohne Traffic gibt es keinen neuen Scheduler. Reine Planning-Reads schreiben weiterhin nichts.

Y1 geschlossen: Zusammengesetzte reale Mehralbum-Pfade über Runtime-Discovery, GO, Handler-Accept/Decline/Withdraw, persistierte Bindung und Cleanup bestehen. Beide Konkurrenzreihenfolgen sind synchronisiert getestet. Keine Behauptung, dass T7a-Versand oder eine neue öffentliche V1-Erzeugungsroute bereits existieren.

Y2 offen: Integrierte Gesamtlast/HTTP-Performance des später sichtbaren Nutzerwegs bleibt T11. Die neue Cleanup-Arbeit ist separat gemessen. **Verbleibend 0 RED / 0 ORANGE / 1 YELLOW.**

## 26 Invarianten erneut geprüft

Die Code-/Testbelege der unveränderten Domainblöcke in §4 des ursprünglichen Audits gelten weiter und wurden mit der Schutz-/Full-Regression erneut geprüft. Nachstehend jeweils die jetzt maßgebliche Grenze; CG-1-Tests liegen in `tests/test_smartdeal_cg1.py`.

| # | Invariante | Reaudit / konkreter Nachweis |
| --- | --- | --- |
| 1 | 1:1 | GREEN: T3b `_validated_plan`, T4 `_payload_identity`; unveränderte Balance-/Oracle-Tests plus 17↔17 Composite |
| 2 | Max. fünf TopDeals | GREEN: vollständige T3b-Teilmenge bis fünf; unveränderte globale Auswahltests |
| 3 | Min. fünf je Richtung | GREEN: Optimizer und Payloadguard; bestehende Vierer-/Fünfer-Grenztests |
| 4 | Partner einmal | GREEN: Optimizer-Teilmenge/Outputprüfung; vollständige Oracle-Planvergleiche |
| 5 | Outgoing nicht doppelt | GREEN: Supply-Counter + frischer Writeguard; T5a Copy-Races, CG-1 Cleanup/neue Bindung |
| 6 | Incoming nicht doppelt | GREEN im V1-Vertrag: Need-Counter und aktuelle fremde Zusagen; T5a Need-Race, T6b Foreign-Need-Test |
| 7 | Protected copy | GREEN: kanonische Availability; T2a/T4 Last-Copy-Nachweise unverändert |
| 8 | Reservierte Supply nicht frei angeboten | GREEN am Runtimeeinstieg: Cleanup vor Projektion, gültige Bindungen bleiben; `test_cleanup_preserves_foreign_valid_binding` |
| 9 | Gebundener Need nicht erneut angeboten | GREEN: T2a-Projektion; `test_composite_accepted` prüft frische leere Planung auch nach 24h |
| 10 | Suggestion reserviert nichts | GREEN: reine T4-Erzeugung/Validation unverändert; Cleanup ist gesonderte Runtimeoperation, keine Vorschlagsreservation |
| 11 | GO frisch | GREEN: T5a/T6b Schreiblock und aktuelle Prüfung unverändert; Cleanup/neue Bindung beide Reihenfolgen |
| 12 | Requestanlage atomar | GREEN: bestehende T5a/T6b-TX/Fehlerinjektionen; kein Zwischencommit im Domainwriter |
| 13 | Beide Seiten gebunden | GREEN: 34 Positionen/Reservationen im 17er Composite und T6b-Reopen-Assertions |
| 14 | Need und Supply gemeinsam | GREEN: `_assert_projected` im Write; Composite frei/gebunden/frei |
| 15 | Pending max. 24h | GREEN: unabhängige absolute Domainfrist; `test_expired_accept_without_sweep`, Runtime-Expiry-Composite. Persistenter Cleanup lazy, keine Behauptung eines zeitgesteuerten Hintergrundwrites |
| 16 | Vollständige Freigabe | GREEN: reale Decline-/Cancel-Handler delegieren an T5b; Handler- und Expiry-Golden-Paths, Rollback nach Release |
| 17 | Accepted bleibt gebunden | GREEN bis T7a: Sweep schützt accepted, alte Lifecycle-Handler liefern 409 ohne jede Tabellenänderung |
| 18 | Mutual GO keine zweite Instanz | GREEN: unveränderte vollständige T6b-Identitysuche und Vier-GO-Race; CG-1 Handler/Mutual-Races |
| 19 | A/A pending | GREEN: unveränderte T6b-Idempotenz-/Paralleltests; Runtimeadapter fügt keine Annahme hinzu |
| 20 | A/B accepted | GREEN: T6b-Mirror-/Race-Nachweise, Composite über expliziten Handler und Mutual-Races |
| 21 | accepted_at stabil | GREEN: T6b und Migration 0021 unverändert; Composite `assert_accepted`, keine Legacy-Annahme mehr |
| 22 | binding_created_at stabil | GREEN: gleiche persistierte Zeit im Composite; Cleanup/Handler setzen keine neue Bindungszeit |
| 23 | Inventory bis Lifecycle unverändert | GREEN: Composite-Vergleiche und sieben fail-closed Handler mit vollständigem Reopen-Snapshot |
| 24 | Legacy bleibt Legacy | GREEN für geprüfte Runtimegrenzen: zentraler Contract-Dispatch, unbekannt wirft, V20-No-op; Legacy-Decline und vollständige bestehende Schutzsuite |
| 25 | Privacy/Blocks | GREEN: Actor aus Runtime-Kontext, Rollen im Domainservice; fremder Actor ohne Mutation, bestehende T2a/T4/T5b/T6b-Block-/Pooltests |
| 26 | Keine Clientdaten als Wahrheit | GREEN: vorhandene Payload-/Identity-/DB-Revalidation unverändert; Webadapter verwendet aktuellen serverseitigen Actor, keine Client-Bestandsannahme |

Legacy-Mengenverträge werden weiterhin nicht durch eine erfundene globale binäre Need-Unique-Regel verändert. Physische Buchung bleibt außerhalb dieses Core-Standes. Pure Domain-Reads können abgelaufene gespeicherte Fakten logisch projizieren; der freigegebene frische Runtime-Discoveryweg bereinigt diese vorher.

## Anschlussvertrag für PO-SOLL

Der sichtbare fachliche Verlauf kann jetzt ohne neue Core-Semantik entworfen werden: Suggestion → Pending/Bound → Accepted; Pending alternativ Declined/Withdrawn/Expired. Accepted ist ein bindender, noch unversandter Vertrag. Bis T7a sind Ship/Receive/Complete/Problem-Mutationen für V1 ausdrücklich nicht verfügbar. Das ist eine überprüfte technische Grenze, keine improvisierte Legacy-Weiterverwendung und keine fertig implementierte Versandfunktion.

T7a muss vorhandene positionsbasierte Buchung genau einmal anbinden, alte Confirm-Bypässe gesperrt halten und Retry-/Eventprojektionen nach Versand übernehmen. T7b muss die bereits entschiedene AC26-Priorität und Vor-/Nachversand-Problemgrenze umsetzen. T8a muss konkrete Kontaktfreigabe ausschließlich an bestätigte berechtigte Partner einschließlich Änderungen/Widerruf/Problemzugriff konkretisieren; gespeicherte Adresse allein gibt nichts frei. Diese Aufgaben können im PO-SOLL als explizite spätere Übergänge berücksichtigt werden. Ihre vollständige Implementierung ist keine Voraussetzung für Design-GREEN, aber Pflicht vor öffentlicher UI-/Beta-Aktivierung. Kein Chat erforderlich.

## Nachweis und Freigabegrenze

Neue Tests **29/29**, davon Composite Accepted **1/1**, Composite Expiry **1/1**, Handlergruppe **4/4**, Race-/Rollback **10/10**, Lifecycle-Sperren **7/7**. Kanonische Full Release **1251/1251**, 0 Failures/Errors/Skips, bestehende Kohorten unverändert. Cleanup-Mittelwerte 0/3/30 fällige Requests: **0,033 / 0,921 / 5,801 ms**, keine neue SLA.

GREEN erlaubt den nächsten gesonderten PO-/IA-/Designauftrag. Keine automatische Freigabe für T7a/T7b/T8a, keine öffentliche V1-Erzeugung, keine UI-/Beta-/Deployfreigabe. Ursprünglicher Audit, Product Bible, Algorithm Contract, Roadmap und Migrationen unverändert. Kein git add, Commit, Push oder Deploy. STOP nach CG-1.
