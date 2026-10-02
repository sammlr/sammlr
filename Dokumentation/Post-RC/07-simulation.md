# Realistic Simulation

## Zweck

Dieses Dokument beschreibt in Phase 8 die realistische Mehrnutzer- und Fake-Account-Prüfung vor der Closed Beta.

## Abgrenzung

Die Simulation definiert weder Produktwahrheiten noch UX-/Designregeln und ersetzt nicht das technische Hardening oder das finale Closed-Beta-Gate.

## Status

**Abgeschlossen und technisch abgenommen (21. August 2026).** Die
reproduzierbare Mehrnutzer-Simulation lief ausschließlich auf V18-Wegwerfkopien
und umfasste 31 Nutzer, 56 Albumzuordnungen, mehr als 1.700 Stickerzeilen nach
den verbundenen Journeys, mehrere reguläre und problembehaftete Trades sowie
vier Integritätscheckpoints. Concurrency, Exactly-once, Dedupe, aktuelle
Privacy-Prüfung und alle neun zulässigen Notification-Typen blieben grün.

Das S35-Gate mit 100 Nutzern, 100.000 Stickerzeilen und 20 parallelen Requests
bestand 10/10 Pfade unter 500 ms. Die vollständige Regression lief zweimal mit
713/713 Tests, 0 Fehlern und 0 Skips. Die echte Bestandsdatenbank blieb auf V7
mit unverändertem SHA-256. Vollständiger Nachweis:
`04-implementation-reports/Phase-8-realistic-simulation-report.md`.

Nächster zulässiger Schritt ist **Phase 9 – finales Closed-Beta-Gate**. Externe
Nutzer sind weiterhin nicht freigegeben.
