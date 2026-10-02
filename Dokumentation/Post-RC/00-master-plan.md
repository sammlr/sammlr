# Post-RC Master Plan: RC1 → Closed Beta

## Zweck

Dieser Master Plan ordnet die Produktarbeit nach RC1 bis zur Closed Beta. Die Phasen bauen aufeinander auf; Erkenntnisse und Entscheidungen werden ausschließlich in der jeweils zuständigen Dokumentationsebene gepflegt.

## Geltungsregeln

### Product Bible

Die **Product Bible** enthält die langfristige fachliche Produktwahrheit.

### Post-RC Product Audit

Das **Post-RC Product Audit** dokumentiert Beobachtungen und bewusst getroffene Produktentscheidungen für bestehende Seiten nach RC1.

Für jede Seite beantwortet es ausschließlich:

- Warum existiert die Seite?
- Was ist ihre Hauptaufgabe?
- Was ist die wichtigste Information?
- Was ist die wichtigste Aktion?
- Was gehört ausdrücklich nicht auf diese Seite?
- Was funktioniert heute bereits gut?
- Was verursacht fachliche oder UX-seitige Reibung?
- Welche Produktentscheidungen wurden getroffen?
- Welche Ideen werden bewusst für UX/UI oder später zurückgestellt?

Das Product Audit entscheidet nicht über exakte Farben, Pixelwerte, Radien, Schatten, konkrete Animationen, die finale Komponentenoptik oder die genaue Positionierung einzelner UI-Elemente. Solche Punkte werden höchstens als spätere Design- oder UX-Frage notiert.

### UX Architecture

Die **UX Architecture** definiert später seitenübergreifende Regeln zu Navigation, Rückwegen, Zuständen, Informationsarchitektur und Bedienmustern.

### Design System

Das **Design System** definiert später visuelle Regeln wie Farbe, Typografie, Spacing, Komponenten und Motion.

### UI Backlog

Das **UI Backlog** enthält erst nach abgeschlossenem Product Audit konkrete Umsetzungsaufgaben.

### Engineering Hardening

Das **Engineering Hardening** umfasst Performance, Runtime, Datenbank, Browser-E2E und andere technische RC-Blocker.

### Simulation

Die **Simulation** ist die spätere realistische Mehrnutzer- und Fake-Account-Prüfung.

### Closed Beta Gate

Das **Closed-Beta-Gate** enthält die finalen Freigabekriterien vor externen Testern.

Diese Ebenen werden nicht vermischt.

## Prozess

1. **Phase 1 – Product Audit:** Bestehende Seiten fachlich und aus Produktsicht prüfen; Entscheidungen und bewusst vertagte Fragen dokumentieren. **Abgeschlossen.**
2. **Phase 2 – Cross-Audit und Product Contract Freeze:** Konflikte konsolidieren, PO-Fragen entscheiden und Closed-Beta-Kern einfrieren. **Abgeschlossen.**
3. **Phase 3 – Closed-Beta-Bauplan:** technische Arbeitspakete, Datenverträge, Reihenfolge, Tests und Gates ableiten. **Abgeschlossen.**
4. **Phase 4 – notwendige UX Architecture:** nur die für P1 erforderlichen seitenübergreifenden Bedienregeln konkretisieren, ohne den Freeze zu öffnen.
5. **Phase 5 – notwendiges Design System:** nur die für konsistente P1-Umsetzung erforderlichen visuellen Regeln festlegen.
6. **Phase 6 – Closed-Beta-Implementation:** CB-001 ff. in Abhängigkeitsreihenfolge umsetzen.
7. **Phase 7 – Engineering Hardening:** technische Blocker und Stabilitätsrisiken bearbeiten.
8. **Phase 8 – Realistic Simulation:** Produkt realistisch mit mehreren Nutzern und Fake-Accounts prüfen.
9. **Phase 9 – Closed Beta Gate:** sechs Bauplan-Gates prüfen und über externe Tester entscheiden.

Nach Abschluss von Phase 1 wurde die **Cross-Audit-Konsolidierung** durchgeführt. Die neun daraus hervorgegangenen Product-Owner-Fragen sind entschieden, der Closed-Beta-Produktvertrag ist eingefroren und der technische Bauplan ist erstellt. Umsetzung beginnt nicht automatisch; der erste zulässige Umsetzungsschritt ist `CB-001`.

## Aktueller Status

- RC1 ist abgeschlossen.
- Phase 1 – Product Audit deckt mit den Audits 01–13 die wesentlichen Produktbereiche des aktuellen Post-RC-Stands ausreichend ab.
- Bereits geprüft:
  - Login
  - Registrierung
  - sammlr.-Zentrale / bisheriges Home
  - Sammlung
  - Album
  - Stickerliste
  - Tauschbörse
  - Trade-Lifecycle
  - Profil & Community
  - sammlr. Home / Feed
  - Notifications / Glocke
  - Trophäen
  - Statistik
  - Albumabschluss / Abgeschlossene Alben
- Es wird kein weiterer Product Audit automatisch gestartet.
- Die Cross-Audit-Konsolidierung ist in [`02-cross-audit/01-product-contract-konsolidierung.md`](02-cross-audit/01-product-contract-konsolidierung.md) abgeschlossen.
- Die neun Product-Owner-Fragen PO-01 bis PO-09 sind final entschieden und im [`02-cross-audit/02-product-contract-freeze.md`](02-cross-audit/02-product-contract-freeze.md) normativ eingefroren.
- Alle 37 Cross-Audit-Konflikte besitzen einen finalen Status: `RESOLVED_BY_PO 9`, `RESOLVED_BY_EXISTING_CONTRACT 4`, `TECHNICAL_IMPLEMENTATION_GAP 22`, `UX_DEFERRED 0`, `POST_BETA 2`, `STILL_OPEN 0`.
- Der operative [`03-closed-beta-build-plan.md`](03-closed-beta-build-plan.md) umfasst `P0 0 / P1 17 / P2 9 / P3 3` Arbeitspakete, historische Datenerfassung, Bestandsdatenstrategie, Legacy-Cutover, Teststrategie und sechs Release-Gates.
- Der Product Contract Freeze ist aktiv. Neue Ideen werden Backlog, UX Backlog, Post-Beta oder Future zugeordnet; Ausnahmen gelten nur für belegte logische, Security-, Datenintegritäts-, technische oder reale Beta-Kernworkflowprobleme.
- CB-001 bis CB-017 sind vollständig abgeschlossen und technisch abgenommen
  (`17/17`).
- **Phase 7 – Engineering Hardening** ist abgeschlossen und technisch
  abgenommen. Der S35-Performancevertrag, Security-/Privacy-, Transaction-,
  Runtime-, Migration-/Restore- und Vollregressionsgates sind grün.
- **Phase 8 – Realistic Simulation** ist abgeschlossen und technisch
  abgenommen. Die verbundene 31-Nutzer-Simulation, Concurrency-/Chaosfälle,
  vier Integritätscheckpoints, das S35-Performancegate und zwei vollständige
  Regressionen sind grün.
- **Phase 9 – Closed Beta Gate** wurde am 21. August 2026 ausgeführt. Alle
  lokalen technischen Gates sind grün; die Entscheidung lautet dennoch
  `CLOSED BETA: NICHT FREIGEGEBEN`, weil die juristische Endprüfung der
  Datenschutz-/Betreibertexte und ein realer Betreiber-Backup-/Restore-Drill
  noch nicht belegt sind.
- Nächster notwendiger Schritt ist der belegte Abschluss dieser beiden
  Operations-/Compliancepunkte und danach die erneute Bewertung ausschließlich
  des finalen Operations-Gates. Externe Nutzer bleiben gesperrt.

Die abgeschlossenen Trade-Audits werden in [`01-product-audit/06-tauschboerse.md`](01-product-audit/06-tauschboerse.md) und [`01-product-audit/07-trade-lifecycle.md`](01-product-audit/07-trade-lifecycle.md) gepflegt. Die abgeschlossenen Audit-Stände zu Profil und Community, sammlr. Home / Feed, Notifications / Glocke, Trophäen, Statistik sowie Albumabschluss / Abgeschlossene Alben werden in [`01-product-audit/08-profil-community.md`](01-product-audit/08-profil-community.md), [`01-product-audit/09-sammlr-home-feed.md`](01-product-audit/09-sammlr-home-feed.md), [`01-product-audit/10-notifications.md`](01-product-audit/10-notifications.md), [`01-product-audit/11-trophaeen.md`](01-product-audit/11-trophaeen.md), [`01-product-audit/12-statistik.md`](01-product-audit/12-statistik.md) und [`01-product-audit/13-albumabschluss-vitrine.md`](01-product-audit/13-albumabschluss-vitrine.md) gepflegt. Ein nächster Audit wird nicht ohne gesonderte Product-Owner-Entscheidung als beauftragt behandelt.
