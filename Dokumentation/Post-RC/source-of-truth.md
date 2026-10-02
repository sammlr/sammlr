# Source-of-Truth-Matrix

## Zweck

Diese Matrix ordnet Informationsarten den bereits beschlossenen Dokumentationsebenen zu. Sie erzeugt keine neuen Produktentscheidungen. Eine Information kann zu Nachweis- oder Historienzwecken auch in anderen Dateien erwähnt werden; verbindlich gepflegt werden soll sie jedoch nur an der zuständigen Stelle.

| Informationsart | Zuständige Source of Truth | Abgrenzung |
| --- | --- | --- |
| Langfristige Produktphilosophie und Fachwahrheit | [`../Product Bible/`](../Product%20Bible/) | Dauerhafte Produktprinzipien, Fachlogik und bewusst offene langfristige Fragen. |
| Bewertung bestehender Seiten | [`01-product-audit/`](01-product-audit/) | Beobachtungen und bewusst getroffene Entscheidungen zu bestehenden Seiten nach RC1. |
| Konsolidierter Post-RC-Produktvertrag | [`02-cross-audit/01-product-contract-konsolidierung.md`](02-cross-audit/01-product-contract-konsolidierung.md) | Bereichslandkarte, 37 Konflikte mit finalem Status, Legacy, Abhängigkeiten und Datenrisiken aus Audit 01–13. |
| Normativer Closed-Beta-Freeze | [`02-cross-audit/02-product-contract-freeze.md`](02-cross-audit/02-product-contract-freeze.md) | Verbindliche neun PO-Entscheidungen, Kernrollen, Freeze-Ausnahmen und Scope-Creep-Grenze. |
| Operativer Closed-Beta-Bauplan | [`03-closed-beta-build-plan.md`](03-closed-beta-build-plan.md) | Arbeitspakete, Reihenfolge, Daten-/Migrationsstrategie, Legacy-Cutover, Tests und Release-Gates. |
| Seitenübergreifende Bedienregeln | [`02-ux-architecture.md`](02-ux-architecture.md) | Navigation, Rückwege, Zustände, Informationsarchitektur und Bedienmuster. |
| Closed-Beta-Funktionsumfang | [`02-cross-audit/02-product-contract-freeze.md`](02-cross-audit/02-product-contract-freeze.md) und [`03-closed-beta-build-plan.md`](03-closed-beta-build-plan.md) | Freeze besitzt den normativen Kern; Bauplan besitzt P0–P3-Scope und Reihenfolge. `03-beta-scope.md` bleibt ein noch nicht ausgearbeitetes Alt-Placeholder und darf beide nicht überschreiben. |
| Visuelle Regeln | [`04-design-system.md`](04-design-system.md) | Farbe, Typografie, Spacing, Komponenten und Motion. |
| Konkrete spätere UI-Arbeit | [`05-ui-backlog.md`](05-ui-backlog.md) | Umsetzungsaufgaben erst nach abgeschlossenem Product Audit. |
| Technische Releasequalität | [`06-engineering-hardening.md`](06-engineering-hardening.md) | Performance, Runtime, Datenbank, Browser-E2E und technische RC-Blocker. |
| Mehrnutzer- und Realitätssimulation | [`07-simulation.md`](07-simulation.md) | Realistische Prüfung mit mehreren Nutzern und Fake-Accounts. |
| Freigabe der Closed Beta | [`08-closed-beta-gate.md`](08-closed-beta-gate.md) | Finale Kriterien und Go/No-Go vor externen Testern. |
| Historische Roadmaps und Audits | Historische Dokumentation | Nachweis früherer Planung und Entscheidungen; keine aktuelle Produktwahrheit. |

Der Gesamtprozess und sein Status werden in [`00-master-plan.md`](00-master-plan.md) gepflegt.

Für den aktuell auditierten Tradebereich gilt die folgende Abgrenzung:

- [`../Product Bible/specifications/trading.md`](../Product%20Bible/specifications/trading.md) bleibt die langfristige fachliche Source of Truth für Match- und Smart-Trade-Logik.
- [`../Product Bible/specifications/trade-lifecycle.md`](../Product%20Bible/specifications/trade-lifecycle.md) bleibt die langfristige fachliche Source of Truth für die Dealabwicklung.
- [`01-product-audit/06-tauschboerse.md`](01-product-audit/06-tauschboerse.md) und [`01-product-audit/07-trade-lifecycle.md`](01-product-audit/07-trade-lifecycle.md) halten die aktuelle Bewertung der bestehenden Seiten und die am 15. August 2026 bestätigten Product-Owner-Entscheidungen fest. Sie erzeugen keine UI- oder Implementierungsfreigabe.

Für Profil und Community gilt entsprechend:

- [`../Product Bible/specifications/profile-community.md`](../Product%20Bible/specifications/profile-community.md) bleibt die langfristige fachliche Source of Truth.
- [`01-product-audit/08-profil-community.md`](01-product-audit/08-profil-community.md) dokumentiert die aktuelle Seitenbewertung und die am 15. August 2026 bestätigten Produktgrenzen. Der Audit erzeugt keine UI- oder Implementierungsfreigabe.
- Wo der Audit von S26–S29 oder der langfristigen Profilspezifikation abweicht, bleibt der ältere Stand als Implementierungsnachweis erhalten; die Kollision wird nicht als bereits umgesetzte Änderung ausgegeben.

Für die mittlere sammlr.-Home gilt:

- [`../Product Bible/specifications/home.md`](../Product%20Bible/specifications/home.md) bleibt die langfristige Bestandsspezifikation und dokumentiert den vor dem neuen Audit geltenden Aufgaben-/Home-Vertrag.
- [`01-product-audit/09-sammlr-home-feed.md`](01-product-audit/09-sammlr-home-feed.md) dokumentiert die neuere Product-Owner-Entscheidung für einen chronologischen Sammler-Feed. Der Audit erzeugt keine UI- oder Implementierungsfreigabe.
- Das frühere [`01-product-audit/02-sammlr-zentrale.md`](01-product-audit/02-sammlr-zentrale.md), S25 und die aktuelle Oberfläche bleiben Nachweise des bestehenden operativen Home-Modells; ihre Abweichungen werden nicht als bereits behoben ausgegeben.

Für Benachrichtigungen und Glocke gilt:

- [`../Product Bible/roadmap/s23-typed-notifications.md`](../Product%20Bible/roadmap/s23-typed-notifications.md) und [`../Product Bible/roadmap/s24-notification-history-navigation.md`](../Product%20Bible/roadmap/s24-notification-history-navigation.md) bleiben technische Bestands- und Implementierungsverträge.
- [`01-product-audit/10-notifications.md`](01-product-audit/10-notifications.md) dokumentiert die neuere Produktentscheidung für eine kleine persönliche Inbox einschließlich Typkatalog, Read-Semantik, Badge und Retention. Der Audit erzeugt keine Implementierungs-, UI-, Test- oder Migrationsfreigabe.
- Audit 09 bleibt für die Abgrenzung zum sammlr.-Feed verbindlich; die Tauschzentrale bleibt Eigentümerin operativer Trade-Aktionen.

Für Trophäen gilt:

- Die bestehenden Definitionen in `App/trophy_definitions.py`, die Tabelle `unlocked_trophies`, Trophy-Routen und ältere Profil-/Albumverträge bleiben technische Bestandswahrheit.
- [`01-product-audit/11-trophaeen.md`](01-product-audit/11-trophaeen.md) dokumentiert die neuere Produktentscheidung für ausschließlich albumbezogene, individuell kuratierte, dauerhaft erreichte und vor Freischaltung verborgene Trophäen. Der Audit erzeugt keine Implementierungs-, Migrations-, Test- oder UI-Freigabe.
- Finale Trophy-Kataloge je Album werden ausdrücklich nicht durch das System-Audit festgelegt.

Für Statistik gilt:

- Die bestehende Route `/statistik`, die Albumstatistik, `CollectorProfileService`, Inventory-, Trade- und Trophy-Tabellen bleiben technische Bestandswahrheit.
- [`01-product-audit/12-statistik.md`](01-product-audit/12-statistik.md) dokumentiert die neuere Produktentscheidung, die historische Sammlerkarriere von aktuellen Album-/Bestandswerten zu trennen. Der Audit erzeugt keine Implementierungs-, Migrations-, Test- oder UI-Freigabe.
- Historische Tradewerte werden nur aus regulär erfolgreichen Deals abgeleitet. Albumstart, erster Abschluss, Lebenszeitsumme gesammelter Sticker und Fortschrittskurven dürfen ohne belastbare Historie nicht rückwirkend erfunden werden.
- Finale UI, Historisierungstechnik, Cutover/Backfill und Albumlöscharchitektur bleiben gesonderten Entscheidungen vorbehalten.

Für Albumabschluss und abgeschlossene Alben gilt:

- Aktuelle Vitrinenprojektionen in Sammlung und `CollectorProfileService`, dynamische Completion-Berechnung sowie `unlocked_trophies` bleiben technische Bestandswahrheit.
- [`01-product-audit/13-albumabschluss-vitrine.md`](01-product-audit/13-albumabschluss-vitrine.md) dokumentiert die neuere Produktentscheidung: Der erste vollständige Zustand eines konkreten Albumexemplars ist ein dauerhafter, genau einmaliger historischer Abschluss. Der Audit erzeugt keine Implementierungs-, Migrations-, Test- oder UI-Freigabe.
- „Abgeschlossene Alben“ ist die bevorzugte funktionale Bezeichnung; „Vitrine“ bleibt Legacy beziehungsweise mögliche spätere Gestaltungsmetapher.
- Abschlussdatum, Abschluss-Trophy und Feed-Ereignis müssen später aus demselben exemplarbezogenen Moment konsistent und idempotent hervorgehen. Die konkrete Speicher- und Orchestrierungsarchitektur bleibt offen.
- Die Audits 01–13 sind vollständig konsolidiert; Freeze und Closed-Beta-Bauplan sind erstellt. Noch nicht begonnen ist ausschließlich die Umsetzung ab CB-001.

Für Cross-Audit-Konsolidierung, Freeze und Bauplan gilt:

- [`02-cross-audit/01-product-contract-konsolidierung.md`](02-cross-audit/01-product-contract-konsolidierung.md) betrachtet die verbindlichen Entscheidungen aus Audit 01–13 erstmals als gemeinsames Produktmodell.
- Das Dokument ist Source of Truth für die **Existenz, Einordnung und finale Statusklassifikation** der 37 Kollisionen. Die fachlichen Einzelentscheidungen bleiben in Audits und Freeze beheimatet.
- [`02-cross-audit/02-product-contract-freeze.md`](02-cross-audit/02-product-contract-freeze.md) ist die normative Source of Truth für PO-01 bis PO-09. Empfehlungen aus früheren Analysephasen sind dadurch ersetzt.
- [`03-closed-beta-build-plan.md`](03-closed-beta-build-plan.md) ist die Source of Truth für P0–P3-Arbeitspakete, Implementierungsreihenfolge, Historisierungsbeginn, Bestandsdatenstrategie, Legacy-Abbau, Teststrategie und Closed-Beta-Gates.
- Product Audit 01–13, Cross-Audit-Konsolidierung, PO-Entscheidungen, Product Contract Freeze und Bauplan sind abgeschlossen. Implementierung, Migrationen und Teständerungen sind noch nicht begonnen.

## Bereits bestehende Regeln

Die Product Bible erklärt sich in [`../Product Bible/README.md`](../Product%20Bible/README.md) selbst zum zentralen langfristigen Einstiegspunkt für Produktentscheidungen und Produktspezifikationen. Ihre Spezifikationen sollen nur nach bewusster Produktentscheidung geändert werden; Widersprüche sollen transparent und nicht stillschweigend überschrieben werden. Das stimmt mit der obigen Zuständigkeit für langfristige Produktwahrheit überein.

Die Product Bible verweist für Markenidentität und Corporate Design auf `Branding/Corporate ID/` und die dortige Design Bible. Damit besteht neben dem künftigen Post-RC Design System ein bereits festgelegter Marken- und Assetbereich. Die Trennlinie sollte später ausdrücklich lauten: Branding besitzt Markenidentität und Master Assets; `04-design-system.md` besitzt die produktweiten visuellen UI-Regeln. Diese Klarstellung ist noch keine Änderung der bestehenden Dokumente.

## Dokumentierte Konflikte

### Aktuelle Umsetzungsreihenfolge

- [`../Product Bible/roadmap/README.md`](../Product%20Bible/roadmap/README.md) bezeichnet `development-roadmap-v1.md` als „aktuelle zentrale Umsetzungsreihenfolge“ und meldet am Dokumentende noch „S38 wurde nicht begonnen“.
- [`00-master-plan.md`](00-master-plan.md) dokumentiert dagegen: RC1, Product Audit 01–13, Cross-Audit, PO-Entscheidungen, Freeze und Closed-Beta-Bauplan sind abgeschlossen; die Umsetzung beginnt erst mit CB-001. Die alte Roadmap ist keine aktuelle Umsetzungsreihenfolge.
- [`../Product Bible/release/RC1-checklist.md`](../Product%20Bible/release/RC1-checklist.md) bezeichnet S00–S38 und RC1 als abgeschlossen beziehungsweise hergestellt.

Damit besteht ein echter Status- und Source-of-Truth-Konflikt zwischen alter Roadmap, RC1-Releaseunterlagen und neuem Post-RC-Prozess. Er wird hier nur dokumentiert und nicht aufgelöst.

### Navigation und Informationsarchitektur

- [`../Product Bible/specifications/navigation-information-architecture.md`](../Product%20Bible/specifications/navigation-information-architecture.md) ist als langfristige Produkt-/Lastenheft-Spezifikation gekennzeichnet und enthält verbindliche Regeln zu Hauptbereichen, Bottom-Navigation, Header und Rückwegen.
- [`02-ux-architecture.md`](02-ux-architecture.md) ist gemäß neuem Post-RC-Prozess für spätere seitenübergreifende Regeln zu denselben Themen vorgesehen.

Es besteht eine Zuständigkeitsüberschneidung, aber noch kein inhaltlicher Widerspruch, weil die Post-RC UX Architecture noch nicht ausgearbeitet ist. Spätere Arbeit muss die Product Bible als langfristige fachliche Wahrheit behandeln und darf ihre Regeln nicht stillschweigend ersetzen.

### Visuelle Regeln

- [`../Product Bible/design-system/s30-design-foundation.md`](../Product%20Bible/design-system/s30-design-foundation.md), [`../Product Bible/design-system/s31-ui-foundation.md`](../Product%20Bible/design-system/s31-ui-foundation.md), `Branding/Corporate ID/` und `Branding/Design Bible/` enthalten bereits Design-, Marken- und UI-Regeln.
- [`04-design-system.md`](04-design-system.md) ist für die spätere Post-RC-Designphase vorgesehen.

Es besteht eine Zuständigkeitsüberschneidung. Vor einer späteren Designphase muss festgelegt werden, welche Bestandsdokumente verbindliche Eingaben, historische RC-Implementierungsverträge oder Marken-Source-of-Truth sind. Hier wird nichts umklassifiziert oder überschrieben.

### Technische Releasequalität

- Technische Releasequalität ist derzeit auf `Product Bible/release/`, `operations/`, `security/`, technische Roadmap-Dateien und Sprintberichte verteilt.
- [`06-engineering-hardening.md`](06-engineering-hardening.md) soll sie für den Post-RC-Prozess bündeln.

Es besteht eine strukturelle Überschneidung, aber kein festgestellter fachlicher Widerspruch. Alte Unterlagen bleiben Nachweis und technischer Vertrag; die künftige Pflegezuständigkeit muss bei Beginn von Phase 6 präzisiert werden.

### Trade- und Smart-Trade-Priorisierung

- [`../Product Bible/specifications/trading.md`](../Product%20Bible/specifications/trading.md) ordnet albumübergreifende SmartTrades in seiner Statusmatrix „Später / Vision“ zu.
- [`01-product-audit/06-tauschboerse.md`](01-product-audit/06-tauschboerse.md) dokumentiert die neuere Product-Owner-Entscheidung, albumübergreifende SmartMatches als notwendigen fachlichen Bereich und SmartTrades insgesamt als Kernnutzen der Tauschbörse zu behandeln.

Dies ist ein Priorisierungs- und Pflegekonflikt, aber noch keine Closed-Beta-Implementierungsfreigabe. Eine spätere bewusste Product-Bible-Aktualisierung muss ihn konsolidieren.

### Offene Anfrage bei Bestandsänderung

- Das archivierte Originalprotokoll in [`../Product Bible/specifications/trading.md`](../Product%20Bible/specifications/trading.md) erlaubt eine automatische Verkleinerung offener Dealpakete abhängig von später zu definierenden Zustimmungsschritten.
- Die neuere Entscheidung in den Trade-Audits lässt eine nicht mehr erfüllbare ursprüngliche Anfrage nachvollziehbar sichtbar, verhindert ihre Annahme und verbietet eine ungültige Reservierung. Eine Neuberechnung kann einen neuen Vorschlag erzeugen; die ursprüngliche Anfrage wird nicht stillschweigend verändert.

Diese Spannung wird nicht durch ein heimliches Überschreiben der älteren Spezifikation aufgelöst.

### Zeitpunkt der Bestandsbuchung im Trade

Die Kurzformulierung in der Statusmatrix von `trading.md`, erst bestätigter Empfang führe zur „finalen Bestandsänderung“, ist gegenüber den detaillierten Verträgen missverständlich. [`../Product Bible/specifications/collection.md`](../Product%20Bible/specifications/collection.md), `trade-lifecycle.md` und das aktuelle Lifecycle-Audit stimmen in der detaillierten Auslegung überein: eigene Abgänge werden beim eigenen bestätigten Versand ausgebucht, eigene Zugänge beim eigenen bestätigten Empfang eingebucht. Der Gesamtabschluss ist kein gemeinsamer Sammel-Buchungszeitpunkt.

### Profilhierarchie und Kennzahlen

- Die Product Bible und S26 gewichten aktive Alben auf dem Profil prominent; S26 führt außerdem `Doppelte` als feste Profilkennzahl.
- Das neue Profil-Audit legt fest, dass das eigene Profil kein zweites Sammlungsdashboard ist und `Doppelte` keine zentrale dauerhafte Profilkennzahl bleibt.

Die heutige UI bleibt ein belegter Umsetzungsstand, ist aber nicht die langfristige Zielhierarchie. Eine spätere UX- und Umsetzungsentscheidung muss die Abweichung bewusst bearbeiten.

### Profil-Privatsphäre und S27

- S27 definiert `public` / `friends` / `private` je Album sowie einen unabhängigen Trade-Pool-Schalter.
- Das neue Profil-Audit fordert zusätzlich ein einfaches Profilmodell öffentlich/privat.

Ob das Profil-Gate künftig vor dem S27-Modell liegt oder beide Modelle anders konsolidiert werden, ist ausdrücklich offen. S27 wird nicht gelöscht oder umgedeutet.

### Profil, Konto und Community-Aktivitäten

- Account- und Einstellungszugänge im eigenen S26-Profil sowie die Karte „Profil & Konto“ sind gemäß neuem Audit Übergangszustände. Langfristig sind Profilidentität und Community von Account, Sicherheit und Kontolebenszyklus getrennt.
- Persönliche Community-Aktivitäten werden im neuen Audit auf Freunde begrenzt und von globalen Sammlr News getrennt. S29 enthält diese Freundesaktivitäten noch nicht; daraus wird kein bereits implementierter Feed abgeleitet.

### Operatives Home gegenüber chronologischem Feed

- Die Home-Spezifikation, das frühere Audit 02 und S25 priorisieren Handlungsbedarf. S25 rendert bis zu fünf Prioritätsaufgaben und drei laufende Trades auf Home.
- Das neue Audit 09 definiert sammlr. als strikt chronologischen Feed und verschiebt konkrete Aufmerksamkeit primär zur Glocke sowie operative Trade-Arbeit in die Tauschzentrale.

Dies ist eine direkte Produkt- und Informationsarchitektur-Kollision. Der S25-Service, seine Tests und die heutige Oberfläche bleiben technischer Bestand; das Audit entfernt oder verändert sie nicht.

### Freundesaktivitäten und Sammlr News auf Home

- Die ältere Home-Spezifikation bevorzugt getrennte Bereiche für Freundesaktivitäten und Sammlr News; S25 enthält dafür nur statische Platzhalter.
- Audit 09 führt eigene Sammlerreise, Freundesaktivitäten und Sammlr News als Quellen einer gemeinsamen chronologischen Home ein. Die fachliche Herkunft bleibt erkennbar, während Karten, Gruppierung und visuelle Trennung bewusst offen sind.
- S29 stellt gegenseitige Freundschaften und groben Aktivitätsstatus bereit, aber keinen Freundesaktivitätsfeed. Das Privacy-Verhältnis zwischen Profil-Gate, S27-Albumfreigabe und sichtbarem Feed-Ereignis ist weiterhin nicht konsolidiert.

### Home, Glocke und Notification-Verträge

S23/S24 bleiben technische Besitzer von Notification-Typen, Deduplizierung, Historie, Badge und sicherer Zielnavigation. Audit 09 ändert diesen Katalog nicht. Ob noch nicht typisierte Aufmerksamkeitssignale wie eine Bewertungsaufforderung später einen eigenen Notification-Vertrag benötigen, bleibt eine gesonderte Produkt- und Technikentscheidung.

Audit 10 trifft diese Produktentscheidung nun für die Inbox: Eine einmalige Bewertungsmöglichkeit soll eine Notification erzeugen. Ein technischer Typ, Erzeugungszeitpunkt und Zielvertrag existieren dafür noch nicht und werden durch das Audit nicht implementiert.

### Notification-Typkatalog

- S23/S29 erzeugen heute `trade_accepted`, `trade_received`, `trade_shipping_overdue`, `trade_receipt_overdue` und `friend_accepted`.
- Audit 10 schließt Annahmebestätigung, Empfangsbestätigung, Routine-Reminder und angenommene Freundschaft aus der Closed-Beta-Inbox aus.
- Gewünschte typisierte Ereignisse für abgelehnte beziehungsweise nicht mehr erfüllbare Anfragen, Bewertungsmöglichkeit und relevante Tradeprobleme fehlen heute ganz oder existieren nur als ungezielte Legacy-Meldung.

Der bestehende Katalog bleibt technischer Ist-Stand. Seine Änderung benötigt einen späteren kontrollierten Umsetzungs- und Migration-/Kompatibilitätsentscheid.

### Notification-Read-State und Retention

- S24 lässt `GET /notifications` unverändert, markiert nur den konkret geöffneten oder manuell bestätigten Eintrag und bewahrt alle Meldungen ohne Retention auf.
- Audit 10 definiert das Öffnen der Inbox als Read-Aktion für die sichtbaren Einträge, sieht keinen manuellen Kartenbutton vor und begrenzt die Sichtbarkeit gelesener Meldungen auf höchstens 30 Tage.

Dies ist eine direkte Kollision. Wie Read-Synchronisation und Retention technisch sicher umgesetzt werden, bleibt einem späteren Arbeitspaket vorbehalten.

### Notification-Badge

S24 und Audit 10 stimmen semantisch überein: Das Badge zählt ausschließlich eigene ungelesene Notification-Zeilen und verschwindet bei null. Die bestehende visuelle Darstellung `99+` ab 100 ist eine noch nicht neu entschiedene Darstellungsregel, keine kombinierte Aufgabenkennzahl.

### Legacy und „Historischer Hinweis“

V0006 kennzeichnete Bestandszeilen ohne semantischen Backfill als `legacy`; S24 zeigt sie ziellos als „Historischer Hinweis“. Aktive Altpfade erzeugen weiterhin Legacy-Meldungen für Ablehnung, Abschluss und geplatzte Trades. Das ist Übergangs-/Kompatibilitätslogik und keine dauerhafte Produkt-Historie. Audit 10 löscht keine Daten, beendet keine Schreibpfade und führt noch keine 30-Tage-Retention aus.

### Globale und generische Trophäen

- Der aktuelle Katalog enthält globale Sticker-, Doppelten- und Trade-Schwellen unter `__global__` sowie einen generischen Vierer-Fallback für nicht eigens definierte Alben.
- Audit 11 vertagt globale Trophäen vollständig und verlangt einen individuell kuratierten Trophy-Kosmos je Album.

Globale Definitionen, persistierte globale Zeilen und generische Kataloge bleiben technischer beziehungsweise historischer Bestand. Sie werden nicht gelöscht; ihre heutige Präsenz in Sammlr-Schrank, Statistik und Profilzahl ist als Kollision dokumentiert.

### Dauerhafte Trophy gegenüber dynamischem Bestand

`unlocked_trophies` speichert Album, Trophy-Name und Freischaltdatum dauerhaft. Albumseite, globaler Schrank und Statistik berechnen sichtbare Freischaltungen jedoch teilweise erneut aus dem aktuellen Bestand. Dadurch kann eine persistierte Trophy bei sinkendem Bestand aus der Darstellung verschwinden.

Audit 11 legt die persistierte Freischaltung als dauerhafte historische Wahrheit fest. Eine spätere Umsetzung muss die konkurrierenden Readmodelle bewusst konsolidieren; das Audit ändert heute weder Daten noch Code.

### Verborgene Trophy-Ziele

Audit 11 verbirgt unerreichte Trophäen. Die aktuelle Album-Quick-Card, Statistik und der übergeordnete Trophäenschrank zeigen dagegen nächste Ziele, Fortschritt oder Trophy-Schrank-Fortschrittsbalken. Ältere Renderer enthalten zusätzlich Locked-/Secret-Zustände. Diese UI-Verträge sind nicht mehr verbindliches Zielbild und müssen später in UX Architecture und UI Backlog neu bewertet werden.

### Trophy-Historie und Triggersticker

Das Freischaltdatum ist vorhanden und wird exportiert. Ein Triggersticker, eine stabile Trophy-ID und ein historischer Definitionssnapshot fehlen. Der bestehende URL-Parameter `trigger` markiert nur vorübergehend einen Sticker in der Albumwand und ist keine persistierte Trophy-Historie. Wie ein eindeutiger oder mehrdeutiger Trigger fachlich gespeichert wird, bleibt einer späteren technischen Spezifikation vorbehalten.

### Trophäen in Profil, Feed und Notifications

- Audit 08 erlaubt erreichte Trophäen als Teil der Sammleridentität, abhängig von der offenen Privacy-Konsolidierung. Die heutige Profilzahl zählt auch globale und historische Trophy-Zeilen; fremde Trophy-Details fehlen.
- Audit 09 erlaubt Trophy-Ereignisse grundsätzlich als Sammlerreise. Audit 11 präzisiert: Nicht jede Freischaltung ist feedwürdig; Albumvollendung kann es sein.
- Audit 10 schließt Trophy-Notifications aus. Das bestehende lokale Freischalt-Popup ist keine Glocken-Notification und bleibt technischer Bestand.

### Statistik: aktueller Bestand gegenüber Karrierehistorie

- `/statistik` bezeichnet heute die aktuelle Summe `stickers.quantity` als „gesammelt“, zeigt globale Fehlende und Doppelte und summiert bei abgeschlossenen Requests beide Tradepakete zu „Sticker getauscht“.
- Audit 12 definiert `Sticker gesammelt` dagegen als nicht sinkenden Lebenszeitwert, entfernt Fehlende und Doppelte aus der Gesamtstatistik und trennt historisch erhaltene von abgegebenen Tradeeinheiten.
- Erfolgreiche Tradeanzahl, gerichtete Tradeeinheiten, unterschiedliche Partner und größter Trade sind aus der erhaltenen Request-/Lifecycle-Historie rekonstruierbar. Die heutige Statistikroute verwendet die dafür notwendige konsistente Erfolgs- und Perspektivprüfung noch nicht.

### Fehlende Album- und Bestandschronik

`user_albums` besitzt keinen Startzeitpunkt, ein allgemein verlässlicher erster Albumabschluss wird nicht gespeichert und `stickers` bewahrt nur den aktuellen Zustand ohne Mutationshistorie. Deshalb sind bestehende Albumstarts, vergangene nicht tradebezogene Stickerbewegungen und frühere Fortschrittspunkte nicht zuverlässig rückwirkend bestimmbar. Einzelne Vollendungs-Trophy-Zeilen können Indizien sein, ersetzen aber keinen vollständigen Abschlussvertrag. Audit 12 verlangt keine konkrete Eventarchitektur, verbietet jedoch scheinpräzise Rekonstruktion aus dem aktuellen Bestand.

### Albumlöschung und Statistik

Der aktuelle Produktcode besitzt keinen regulären Einzelalbum-Löschpfad. Audit 12 legt nur die Produktfolge fest: Ein gelöschtes Album zählt danach weder als begonnen noch als abgeschlossen und besitzt keine eigene aktive Albumstatistik. Wie aktuelle Bestände gelöscht und Trade-/Trophy-/Verlaufsnachweise erhalten oder gefiltert werden, ist noch nicht spezifiziert; die Kontenanonymisierung ist dafür kein Ersatzmodell.

### Historischer Albumabschluss gegenüber dynamischer Vitrine

Sammlung, Profil und Statistik leiten „abgeschlossen“ heute jeweils aus dem aktuellen Fortschritt ab. `unlocked_trophies` kann eine einmal erreichte Abschluss-Trophy mit Datum dagegen über eine spätere Bestandsreduktion hinweg bewahren. Der lokale Datenstand enthält genau diesen Fall für `em24`: Trophy-Zeitpunkt vorhanden, aktueller Bestand wieder unter dem Albumumfang. Audit 13 setzt deshalb den exemplarbezogenen Erstabschluss als eigene historische Wahrheit; die Trophy-Zeile bleibt ein nützliches Indiz, ist aber wegen typbezogener Identität und verteilter Erkennung kein vollständiger Abschlussvertrag.

### Abgeschlossene Alben, Löschung und Statistikzählung

Audit 13 erlaubt bei späterer Albumlöschung die Wahl, den historischen Abschluss zu bewahren oder zu entfernen. PO-05 löst die frühere Zählkollision: Bewahrte Geschichte zählt weiter, mitgelöschte nicht. PO-06 legt für die Closed Beta fest, dass eine bewahrte Abschlusskarte ohne aktives Album nicht anklickbar ist.

### Albumtyp gegenüber Albumexemplar

Audit 04 und Audit 13 verlangen langfristig eigenständige Exemplare desselben Albumtyps. Das heutige Modell adressiert Inventory, Privacy, Profil, Trophy und Routen dagegen im Wesentlichen über `user_id + album_id` und erlaubt nur eine `user_albums`-Zuordnung pro Typ. Eine spätere Architektur muss Exemplar- und Typidentität trennen, ohne jetzt Keys, Relationen, URLs oder Migration festzulegen.

### Benennung Home und Sammlr-Zentrale

Die ältere Product Bible trennt Home von einer sammlungsorientierten „Sammlr-Zentrale“. Die aktuelle Hauptnavigation und Audit 09 verwenden dagegen `Sammlung` für Bestand und Alben sowie `sammlr.` für die mittlere Home. Dieser Terminologiekonflikt wird dokumentiert, aber nicht durch eine beiläufige Umbenennung der Bestandsunterlagen aufgelöst.

## Regel für historische Unterlagen

Roadmaps, Sprintpläne, Sprintberichte, RC1-Analysen und das frühere UX-Sammeldokument bleiben als historische Evidenz erhalten. Sie werden nicht als aktuelle Produktwahrheit interpretiert, sofern eine neuere zuständige Source of Truth ausdrücklich einen anderen Prozessstand festhält. Inhaltliche Konflikte werden weiterhin sichtbar dokumentiert und nicht stillschweigend bereinigt.
