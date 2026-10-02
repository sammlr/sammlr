# Sammlr RC1 – Test- und Roadmap-Matrix

Stand: 9. August 2026

## Ausführungsstand

| Lauf | Befehl | Ergebnis | Dauer | Fehler | Fehlschläge | Skips |
|---|---|---:|---:|---:|---:|---:|
| S38-spezifisch | `python -m unittest tests.test_s38_release_candidate -v` | 6/6 grün | 0,431 s | 0 | 0 | 0 |
| Gesamtgate 1 | `python -m unittest discover -s tests -p "test_s*.py" -v` | 529/529 grün | 6,260 s | 0 | 0 | 0 |
| Gesamtgate 2 | derselbe Befehl | 529/529 grün | 6,237 s | 0 | 0 | 0 |

Interpreter in allen Abnahmeläufen:
`/private/tmp/sammlr-s32-py313-venv/bin/python` (CPython 3.13.15).

## Roadmap-Matrix

„Abgeschlossen“ bezeichnet den implementierten und im aktuellen Gesamtgate
regressionsgesicherten Sprintstand; es ist keine Public-Beta-Freigabe.

| Sprint | Ziel | Status | Primärer Testnachweis | Verbleibend |
|---|---|---|---|---|
| S00 | Referenzstand und Testdatenstrategie | abgeschlossen | Fixture-Hashguard und S38-Frischmigration | Fixture bewusst V0000 |
| S01 | Inventory-Regression | abgeschlossen | `test_s01_inventory_regression.py` (16) | Warnungsbereinigung später |
| S02 | Papierlisten-/Tradeflow-Regression | abgeschlossen | `test_s02_tradeflow_regression.py` (16) | Lifecycle-Erweiterungen separat umgesetzt |
| S03 | Infrastruktur-/Seiteneffekt-Gate | abgeschlossen | `test_s03_side_effect_security_gate.py` (11) | keine S38-Arbeit |
| S04 | Home-/Sammlungsgrundlage | abgeschlossen | `test_s04_home_collection_routes.py` (10) | keine S38-Arbeit |
| S05 | Dreiteilige Navigation | abgeschlossen | `test_s05_three_area_navigation.py` (11) | dauerhaft 3 Ziele |
| S06 | Globaler Header | abgeschlossen | `test_s06_global_header_shell.py` (11) | keine Notification-Fachlogik hier |
| S07 | Deep-Link-/Rückwegkontext | abgeschlossen | `test_s07_deep_link_origin_context.py` (12) | nur erlaubte Origins |
| S08 | Inventory-Vertrag | abgeschlossen | `test_s08_inventory_contract_v1.py` (15) | Zielmodell bleibt Vertrag |
| S09 | Zentraler Inventory-Lesedienst | abgeschlossen | `test_s09_inventory_read_service.py` (11) | keine S38-Arbeit |
| S10 | Zentraler Inventory-Schreibadapter | abgeschlossen | `test_s10_inventory_write_service.py` (10) | keine S38-Arbeit |
| S11 | Availability | abgeschlossen | `test_s11_availability.py` (10) | keine S38-Arbeit |
| S12 | Inventory Guard | abgeschlossen | `test_s12_inventory_guard.py` (12) | keine S38-Arbeit |
| S13 | Migrationen/Lifecycle-Grundschema | abgeschlossen | `test_s13_trade_lifecycle_schema.py` (9) | aktueller Stand V0012 |
| S14 | Reservierungen | abgeschlossen | `test_s14_trade_reservations.py` (21) | keine S38-Arbeit |
| S15 | Versand/Transit | abgeschlossen | `test_s15_trade_shipping.py` (24) | keine S38-Arbeit |
| S16 | Empfang/Bestandsbuchung | abgeschlossen | `test_s16_trade_receipt.py` (17) | keine S38-Arbeit |
| S17 | Teilmengen/Problemfälle | abgeschlossen | `test_s17_trade_problems_partial_receipt.py` (27) | keine S38-Arbeit |
| S18 | Timeline/Fälligkeiten | abgeschlossen | `test_s18_trade_lifecycle_timeline.py` (13) | keine Eskalationsautomatik |
| S18.1 | Receipt UX/Transitdarstellung | abgeschlossen | historisch `test_s19_receipt_ux_hardening.py` (13) | Dateiname historisch |
| S18.2 | Problem-/Tradeabschluss konsolidieren | abgeschlossen | `test_s18_2_problem_trade_finalization.py` (7) und historisch `test_s20_trade_completion_consistency.py` (20) | Dateiname historisch |
| S19 | Shared Availability Snapshot | abgeschlossen | `test_s19_shared_availability_snapshot.py` (18) | keine S38-Arbeit |
| S20 | Markt-/persönliche Abdeckung | abgeschlossen | `test_s20_market_coverage.py` (15) | reine Kennzahlen |
| S21 | Konfliktfreie Top Matches | abgeschlossen | `test_s21_top_match_optimization.py` (19) | keine Mutation |
| S22 | Smart Trade Requests | abgeschlossen | `test_s22_smart_trade_requests.py` (16) | kein S38-Ausbau |
| S23 | Typisierte Notifications | abgeschlossen | `test_s23_typed_notifications.py` (13) | feste Typen bleiben |
| S24 | Notificationhistorie/-navigation | abgeschlossen | `test_s24_notification_history_navigation.py` (15) | keine S38-Arbeit |
| S25 | Operatives Home | abgeschlossen | `test_s25_operational_home.py` (14) | operative Projektion bleibt |
| S26 | Sammlerprofile | abgeschlossen | `test_s26_collector_profiles.py` (11) | keine S38-Arbeit |
| S27 | Albumprivacy/Tradepool | abgeschlossen | `test_s27_album_privacy_trade_pool.py` (9) | keine S38-Arbeit |
| S28 | Tradebewertungen | abgeschlossen | `test_s28_trade_ratings.py` (9) | keine Einzelbewertungsliste |
| S29 | Freundschaften/Community | abgeschlossen | `test_s29_friendships_community.py` (10) | keine Admin-Sperre |
| S30 | Designfundament | abgeschlossen | `test_s30_design_foundation.py` (8) | keine globale Neugestaltung |
| S31 | UI-Fundament | abgeschlossen | `test_s31_ui_foundation.py` (10) | dreiteilige Navigation verbindlich |
| S32 | Auth/Session/CSRF | abgeschlossen | `test_s32_auth_session_csrf.py` (13) | Securitypflege fortlaufend |
| S33 | HTTP-/Integritätshärtung | abgeschlossen | `test_s33_http_integrity_hardening.py` (13) | freigegebene GET-Ausnahmen dokumentiert |
| S34 | Deployment/Recovery/Observability | abgeschlossen | `test_s34_deployment_recovery_observability.py` (13) | realer Betreiberdrill offen |
| S35 | Account Lifecycle/Performancebasis | fachlich abgeschlossen, Release blockiert | `test_s35_account_lifecycle_privacy_performance.py` (7) | Performance-Blocker beheben |
| S36 | Datenexport/Compliance | abgeschlossen | `test_s36_user_data_export_compliance.py` (7) | juristische Endfassung offen |
| S37 | Beta Polish | abgeschlossen | `test_s37_beta_polish.py` (6) | kein Public-Beta-Release |
| S38 | Finales RC-Gate | abgeschlossen | `test_s38_release_candidate.py` (6), Gesamtgate 529 | PO-/Engineering-Entscheidung folgt |

## RC-Kernworkflow-Matrix

| Bereich | Ausführbarer Nachweis im Gesamtgate | RC-Ergebnis |
|---|---|---|
| Account anlegen/Login/Session | S32 Registrierung, scrypt, Legacy-Migration, Rotation | grün |
| Sammlung/Inventar | S01, S08–S12, S19 | grün |
| Manuelle Anfrage | S02 | grün |
| Smart-Anfrage | S21–S22 | grün |
| Annahme/Reservierung | S14, S22 | grün |
| Versand/Transit | S15 | grün |
| Empfang/Abschluss | S16, S18.2 | grün |
| Teilmenge/Problem/Auflösung | S17, S18.1, S18.2 | grün |
| Notifications/operatives Home | S23–S25 | grün |
| Privacy/Tradepool | S27 | grün |
| Bewertung | S28 | grün |
| Freundschaft/Blockierung/Suche | S29 | grün |
| Export/Account Lifecycle | S35–S36 | grün |
| Navigation/UX/Rückwege | S05–S07, S30–S31, S37 | grün |
| Produktion/Recovery/Security | S32–S34 und S38-Produktionsprobe | grün |
