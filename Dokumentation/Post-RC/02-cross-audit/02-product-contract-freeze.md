# Sammlr Closed-Beta Product Contract Freeze

**Freeze-Datum:** 16. August 2026
**Status:** verbindlich
**Geltungsbereich:** Closed-Beta-Kernvertrag

## 1. Normative Quellen

Der Closed-Beta-Produktvertrag besteht, in dieser Rangfolge, aus:

1. diesem Freeze und den neun unten festgehaltenen Product-Owner-Entscheidungen,
2. der aufgelösten [Cross-Audit-Konsolidierung](01-product-contract-konsolidierung.md),
3. den Product Audits 01–13,
4. älteren Product-Bible- und Sxx-Verträgen nur dort, wo sie den neueren Entscheidungen nicht widersprechen.

Der operative Umsetzungsumfang und seine Reihenfolge stehen im [Closed-Beta-Bauplan](../03-closed-beta-build-plan.md). Technischer Ist-Code beweist Implementierung, überschreibt aber keinen neueren Produktvertrag.

## 2. Verbindliche PO-Entscheidungen

### PO-01 – Profil- und Albumprivacy: A

Profilprivacy ist das äußere Gate mit `öffentlich` und `privat`. Ein privates Profil verbirgt Sammlung, Trophäen, abgeschlossene Alben und vergleichbare Sammlerinformationen nach außen. Bei öffentlichem Profil wirken darunter die bestehenden beziehungsweise konsolidierten Albumfreigaben weiter. Der Tradepool bleibt von der Profildarstellung fachlich getrennt.

### PO-02 – Feedumfang: C

Der strikt chronologische `sammlr.`-Feed enthält die eigene Sammlerreise, privacy-geprüfte Aktivitäten gegenseitiger Freunde und zurückhaltende Sammlr News. Es gibt keine algorithmische Sortierung und keine Prioritätslogik.

### PO-03 – SmartMatches im Feed: A

SmartMatches erscheinen nicht im Feed. Sie gehören ausschließlich in die operative Welt Tauschen / SmartTrades / Tauschzentrale.

### PO-04 – Cross-Album-SmartTrades: B

Die Closed Beta benötigt einen vollständigen und zuverlässigen albumbezogenen SmartTrade-Pfad. Cross-Album-SmartTrades bleiben beschlossenes Post-Beta-Ziel. Der Closed-Beta-Umbau darf dieses Ziel nicht unnötig verbauen, muss es aber nicht implementieren.

### PO-05 – Bewahrter Abschluss nach Albumlöschung: A

Beim Löschen eines abgeschlossenen Albums entscheidet der Nutzer ausdrücklich, ob die historische Abschlussgeschichte bewahrt oder mitgelöscht wird. Bewahrte Geschichte bleibt Teil der Karriere und zählt weiter als abgeschlossenes Album. Mitgelöschte Geschichte verschwindet und zählt nicht mehr. Sammlr entscheidet dies nie automatisch.

### PO-06 – Klickziel ohne aktives Album: B

Eine bewahrte Abschlusskarte ohne aktives Album ist in der Closed Beta nicht anklickbar. Eine historische Read-only-Ansicht gehört nicht zum Closed-Beta-Scope.

### PO-07 – Backfill bestehender Abschlüsse: A

Ein Abschluss darf nur aus einer eindeutig validierten Abschluss-Trophy mit belastbarem historischem Datum übernommen werden. Heutige 100 Prozent, aktuelle Mengen, Notifications, Schätzungen oder andere Current-State-Signale sind keine Evidenz. Vor einer Migration ist der relevante Trophy-Katalog zu validieren.

### PO-08 – Öffentliche Profilzahlen: B

Ein zugängliches öffentliches Profil darf Bewertung, erfolgreiche Trades, abgeschlossene Alben und gültige albumbezogene Trophäen zeigen. Unterschiedliche Tauschpartner sind keine notwendige öffentliche Kennzahl. Die vollständige Statistik bleibt privat.

### PO-09 – Problem-Notifications: A, präzisiert

Eine Problem-Notification entsteht nur bei einem neuen, für den Empfänger tatsächlich handlungsrelevanten Zustand. Zusätzlich ist genau ein terminaler Hinweis erlaubt, wenn die Auflösung die eigene nächste Aktion, die endgültige Durchführbarkeit oder die Möglichkeit von Abschluss beziehungsweise Bewertung relevant verändert. Interne Statusänderungen erzeugen kein Notification-Pingpong.

## 3. Eingefrorener Closed-Beta-Kern

- **Sammlung:** digitales Regal und Current-State-Übersicht der eigenen Alben.
- **Album:** lebendiges digitales Sammelalbum; auch nach Vollendung weiter benutzbar.
- **Stickerliste:** fokussierter digitaler Tauschzettel für Fehlende, Doppelte und physische Trades.
- **sammlr.:** strikt chronologischer Feed, kein Arbeitskorb.
- **Tauschen:** einzige operative Welt für Matches, Anfragen und laufende Deals.
- **Glocke:** kleine persönliche Inbox für direkte Aufmerksamkeit, keine Fachaktion und keine Dauerhistorie.
- **Profil:** Sammleridentität und Community; Account- und Sicherheitsverwaltung bleiben getrennt.
- **Statistik:** klare Trennung zwischen Current State und historischer Karriere.
- **Trophäen:** dauerhaft erreichte, verborgene, individuell kuratierte Album-Erinnerungen.
- **Albumabschluss:** genau ein historischer Erstabschluss pro konkretem Exemplar; Abschluss, Trophy und Feed entstehen konsistent aus demselben Moment.
- **Trade-Lifecycle:** Anfrage reserviert nichts; Annahme reserviert atomar; eigener Versand bucht eigene Abgaben aus; eigener Empfang bucht tatsächliche Zugänge ein; Abschluss erst nach vollständigem, problemfreiem Empfang; Bewertung danach.

## 4. Freeze-Regel

Während der Umsetzung werden keine spontanen Produktänderungen in den Kernvertrag aufgenommen. Neue Ideen werden als `Backlog`, `UX Backlog`, `Post-Beta` oder `Future` klassifiziert.

Der Freeze darf nur geöffnet werden bei:

- einem echten logischen Widerspruch,
- einem Datenintegritätsproblem,
- einem Securityproblem,
- einem technisch unmöglichen Vertrag,
- einer Erkenntnis aus realer Beta-Nutzung, die einen Kernworkflow nachweislich beeinträchtigt.

Geschmacksänderungen, zusätzliche Varianten, visuelle Perfektion, neue Kennzahlen oder eine breitere langfristige Vision öffnen den Freeze nicht. Jede Ausnahme benötigt einen benannten Konflikt, Beleg, betroffene Vertragsstellen, Auswirkung auf Scope/Daten und eine ausdrückliche Product-Owner-Entscheidung.

## 5. Ausdrücklich außerhalb der Closed Beta

- Cross-Album-SmartTrades,
- Mehrfachexemplare desselben Albumtyps,
- Push-Zustellung,
- historische Read-only-Ansicht gelöschter Alben,
- vollständige langfristige Statistik- und Feedvision,
- Rankings, Leaderboards, XP und Level,
- komplexe Reminder-, Dispute-, Versanddienstleister- oder Reputationssysteme,
- perfekte finale UI, jede Animation und jeder langfristige Trophy-Katalog.

Diese Abgrenzung schützt die Closed Beta vor Scope Creep; sie verwirft die Themen nicht dauerhaft.
