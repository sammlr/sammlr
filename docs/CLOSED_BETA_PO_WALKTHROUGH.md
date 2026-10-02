# Closed-Beta PO-Walkthrough

Stand: 2026-09-06. Laufendes PO-Protokoll; Quelle: manueller Walkthrough des Product Owners. Keine unabhängige technische Reproduktion der visuellen Befunde in diesem Auftrag.

16 Befundgruppen. Alle Punkte sind dokumentiert, **keiner ist als erledigt markiert**. Statuslabels dienen der Einordnung; offene Optionen bleiben PO-Entscheidungen. Keine Umsetzung innerhalb R5 B1.2. R5 bleibt NEXT und wartet auf PO-Abnahme.

Stickerwall, Stickerliste/CEOKlaue/Glassboard und Profile V1 bleiben geschützt. Keine allgemeine Wiederöffnung dieser Flächen.

## B1. LOGIN / REGISTRIERUNG / ONBOARDING

**Einordnung: BEFORE BETA / PRODUCT DECISION; Passwort-Reset und Verifizierung: später, Termin offen.**

PO-Befund:

- Login und Registrierung funktionieren grundsätzlich, sollen aber noch
  in das aktuelle Sammlr-Design überführt werden.

- Passwort vergessen ist später erforderlich.

- E-Mail-Verifizierung ist später erforderlich.

- Kritischer Zero-Album-Zustand:
  Ein neuer Nutzer ohne Album landet aktuell in der Sammlr-Zentrale und
  bekommt bereits sinngemäß "Finde Tauschpartner" angeboten.

  Das ist semantisch falsch, weil ohne eigenes Album / Bestand noch keine
  sinnvolle Tauschpartnersuche existiert.

- Gewünschte Richtung:
  Die Sammlr-Zentrale soll gleichzeitig als leichtes kontextabhängiges
  Onboarding dienen.

  Beispielidee:
  "Schön, dass du da bist."
  "Leg jetzt dein erstes Album an."

- Kein langer bürokratischer Onboarding-Wizard gewünscht.

- Die Zentrale soll später abhängig vom Nutzerzustand den nächsten
  sinnvollen Schritt zeigen.

## B2. ALBUM HINZUFÜGEN

**Einordnung: BEFORE BETA / PRODUCT DECISION.**

PO-Befund:

- Seite ist funktional auffindbar, aber visuell noch nicht auf dem
  Niveau der aktuellen Sammlr-Kernflächen.

- Albumdarstellung soll stärker über echte Cover / Albumidentität
  funktionieren.

- Aktuelle große lila "Hinzufügen"-Pillen wirken zu grob.

- "Hinzufügen" erscheint teilweise redundant / doppelt.

- Beim Start eines Albums soll später geprüft werden, ob ein sinnvoller
  Einstieg angeboten wird, beispielsweise:

  - leer starten
  - aktuellen eigenen Sammelstand eintragen
  - Album bereits vollständig

Dies ist noch eine Produktentscheidung und NICHT jetzt zu implementieren.

## B3. FAVORITENALBUM

**Einordnung: BEFORE BETA – visueller Beta-Befund, laut PO nicht releasefähig.**

PO-Befund:

Die aktuelle Favoritenauswahl ist sichtbar nicht releasefähig.

Im manuellen Smoke zerbricht die Albumkarte / Darstellung deutlich.

Das ist ein klarer visueller Beta-Befund.

Zusätzlich:

- Wording eher "Auswählen" statt "Als Favorit setzen".
- Favoritenauswahl soll sich an der aktuellen Albumkarten-Sprache
  orientieren.

NICHT jetzt reparieren.

## B4. SAMMLUNG / ALBUM / STICKERWALL

**Einordnung: ACCEPTED / PROTECTED; Menge 2: R7 POLISH.**

PO-Befund:

- Sammlung ist logisch und verständlich.
- Albumübersicht ist grundsätzlich stark.
- Stickerwall ist aktuell die visuelle Referenz für den Rest der App.

Insbesondere als Referenz betrachten:

- Farben
- Zurückhaltung
- Buttons / Controls
- Radien
- Abstände
- Slot-Grammatik
- Filter
- Suche
- Kapitelstruktur
- Retro-Ziffern

Die Stickerwall selbst ist weitgehend abnahmebereit und bleibt geschützt.

Stickerstapel:

- ab Menge 3 wirkt der physische Stapel gut.
- Menge 2 wirkt noch nicht überzeugend.
- Bei 2 ist hauptsächlich Schatten sichtbar; die zweite physische
  Kanten-/Layerstruktur ist zu schwach.
- später kleiner gezielter visueller Fix.

Keine generelle Stickerwall-Neugestaltung.

## B5. ALBUMEINSTELLUNGEN

**Einordnung: BEFORE BETA / PRODUCT DECISION.**

PO-Befund:

Aktuelles Popup für:

- Album-Sichtbarkeit
- Tradepool

ist funktional, aber langfristig zu eng gedacht.

Gewünschte Richtung:

Eine gebündelte Album-Bearbeiten-/Einstellungszentrale, in der
albumbezogene Optionen zusammengeführt werden.

Privacy nicht als isoliertes Sonderkonstrukt betrachten.

Keine Umsetzung jetzt.

## B6. TROPHÄEN-EINGANG IM ALBUM

**Einordnung: BEFORE BETA / PRODUCT DECISION – offen.**

PO-Befund:

Die aktuell sehr prominente Trophäen-Kachel muss nicht zwingend einer
der drei zentralen Album-Eingänge bleiben.

Denkbare spätere Nutzung dieser Fläche:

- Einstellungen
- Statistik

Noch KEINE Produktentscheidung.

Trophäensystem selbst nicht im Rahmen dieses Auftrags verändern.

## B7. PROFIL

**Einordnung: ACCEPTED / PROTECTED; Erweiterungen: POST BETA.**

PO-Befund:

Profil V1 ist grundsätzlich gut und funktioniert.

Der 70er-Profilsticker ist ein starker Identitätsanker.

Aktuell aber noch kein endgültiger "Überbrecher".

Spätere Entwicklung:

- weitere Stickeroptionen
- ausgereifterer Fotomodus
- weitere Individualisierungsmöglichkeiten

Der untere Profilbereich hat zusätzliches Potential.

PO betrachtet das eigene Profil perspektivisch als eine Art persönliche
zweite Sammlr-Zentrale.

Für Closed Beta NICHT aufblasen.

Profile V1 bleibt geschützt.

## B8. TAUSCHEN – GRUNDSTRUKTUR

**Einordnung: BEFORE BETA / PRODUCT DECISION.**

PO-Befund:

Die Trade-Funktionen sind grundsätzlich vorhanden und funktionieren.

Die Informationsarchitektur ist jedoch im Laufe der Entwicklung
unübersichtlich geworden.

Es existieren:

- mehrere Einstiege
- teilweise fehlende Rückwege
- teilweise semantisch falsche Rückwege
- albumbezogene Trade-Wege
- globale Trade-Wege
- SmartMatch
- Partnerliste
- Requests
- Trade Detail
- origin-abhängige Navigation

PO beschreibt dies als "Kabelsalat", der vor Closed Beta einmal
systematisch sortiert werden soll.

Keine weiteren punktuellen Navigationspatches ohne vorherigen
Soll-Navigationsvertrag.

## B9. SMARTMATCH – PRODUKTVISION

**Einordnung: BEFORE BETA / PRODUCT DECISION; albumübergreifende Vision: langfristig.**

Dies ist ein zentraler PO-Befund.

SmartMatch soll das eigentliche besondere Sammlr-Erlebnis sein.

Gewünschte Produktlogik:

Der Nutzer soll möglichst wenig Tauschbürokratie haben.

Nicht primär:

"Suche selbst einen Partner und baue selbst einen Trade."

Sondern:

Sammlr soll direkt sagen:

"Das könnt ihr füreinander tun."

Die Tauschen-Hauptansicht soll perspektivisch zuerst konkrete,
ausführbare SmartMatches zeigen.

Beispiel:

Partner
Du bekommst X Sticker
Du gibst Y Sticker
Paket ansehen / anfragen

PO-Idee:

SmartMatch wird möglicherweise der Default-Einstieg von "Tauschen".

Klassische Partnersuche bleibt sinnvoll, aber sekundär.

Wichtig:

Bereits reservierte / in angenommenen Deals gebundene Sticker dürfen
nicht weiterhin so behandelt werden, als wären sie für andere Matches
frei verfügbar.

Bestehende Reservation-/Availability-Verträge prüfen, nicht neu erfinden.

Langfristige SmartMatch-Vision:

albumübergreifende Deals zwischen zwei Sammlern.

Ein Sammler ist nicht "WM-Peter" und separat "EM-Peter".

Sammlr soll perspektivisch über mehrere gemeinsame Alben hinweg ein
sinnvolles Gesamtpaket erkennen können.

Für Closed Beta ist zu entscheiden, welcher Teil davon zwingend vor
Release nötig ist.

NICHT innerhalb R5 implementieren.

## B10. TRADE COMPOSER

**Einordnung: R7 POLISH – Designrichtung festgehalten.**

PO-Befund:

Die Sticker-Auswahl beim manuellen Trade verwendet noch eine ältere
visuelle Slot-Sprache.

Gewünschte Richtung:

Trade Composer soll die aktuelle Stickerwall-Grammatik übernehmen.

Explizite Designentscheidung:

NICHT CEOKlaue.

CEOKlaue gehört zur physischen Stickerliste / Börsenlisten-Metapher.

Der digitale Trade Composer soll sich wie die digitale Sammlung /
Stickerwall anfühlen.

## B11. TRADE REQUEST / TRADE DETAIL

**Einordnung: BETA BLOCKER – mobile Erreichbarkeit; übrige Hierarchie: R7 POLISH.**

PO-Befund:

Funktional grundsätzlich brauchbar.

Visuell / strukturell wirkt die Seite aber wieder unruhiger und älter
als aktuelle Kernflächen.

Insbesondere:

- Status
- Smart-Paket-Kennzeichnung
- Antwortfrist
- Tauschinhalte
- Aktionen
- Versandstatus

konkurrieren teilweise zu stark miteinander.

Kritischer Mobile-Befund:

Der Versandstatus / untere Inhalt ist teilweise nicht vollständig
erreichbar bzw. verschwindet hinter der Bottom Navigation.

Das ist ein Beta-Blocker.

Bottom Navigation darf niemals den letzten relevanten Inhalt oder eine
Aktion unerreichbar machen.

## B12. "ANSEHEN" / ZWISCHENANSICHTEN

**Einordnung: BEFORE BETA / PRODUCT DECISION – erst Flow-Analyse.**

PO-Frage:

Ist der separate "Ansehen"-Modus bei Trade Requests überhaupt notwendig?

Aktuell existieren mehrere Ebenen zwischen:

- Anfrage
- Anfrage ansehen
- Trade Detail
- Versandstatus

Prüfen, ob diese Struktur vereinfacht werden kann.

Nicht vorschnell entfernen.

Erst Route-/Flow-Analyse.

## B13. VERSANDSTATUS

**Einordnung: BEFORE BETA / PRODUCT DECISION – offen.**

PO-Idee:

Der zentrale Versand-/Trade-Status könnte stärker direkt in der
Trade-Übersicht sichtbar sein.

Beispiel:

Partner
2 ↔ 2
Anfrage angenommen
"Jetzt versenden"

oder:

"Partner hat versendet"
"Erhalt bestätigen"

Trade Detail kann für:

- Details
- vollständige Historie
- Problemfälle
- Timeline

bestehen bleiben.

Aber der normale Trade-Lifecycle soll möglicherweise ohne unnötiges
Eintauchen in Detailseiten bedienbar sein.

Noch keine endgültige Entscheidung.

## B14. KONTAKT / VERSANDADRESSE

**Einordnung: BETA BLOCKER – praktikabler Versand-/Kontaktweg offen.**

Kritische offene Produktfrage:

Ohne eigenen Chat muss geklärt sein, wie zwei Nutzer nach einem
zustande gekommenen Trade den Versand organisieren.

Diskutierte Optionen:

A. Versandadresse hinterlegen
B. Telegram-Kontakt
C. WhatsApp-Kontakt
D. Kombination / freiwillige Kontaktoptionen

PO-Präferenz noch nicht final.

Wichtig:

Eine Adresse im initialen Onboarding könnte unnötig invasiv sein.

Zu prüfen ist eher ein eigener Bereich:

"Versand & Kontakt"

Datenschutzvertrag:

- niemals öffentlich auf Profil / Stickerwall
- nur für den konkreten Versandzweck
- falls Adresse verwendet wird, vorzugsweise erst nach zustande
  gekommenem Trade für den jeweiligen Partner sichtbar

Kein eigener Sammlr-Chat für Closed Beta.

Das Fehlen eines praktikablen Versand-/Kontaktwegs ist vor Closed Beta
zu lösen.

## B15. NAVIGATION / RÜCKWEGE

**Einordnung: BEFORE BETA / PRODUCT DECISION – Navigationsvertrag erforderlich.**

Mehrfach im manuellen Walkthrough beobachtet:

- fehlende Rückwege
- falsche Rückwege
- Rückwege abhängig vom Einstieg
- besonders problematisch bei:
  Fremdprofil → fremdes Album → SmartTrade / Trade

Beispiel:
Ein Trade kann anschließend semantisch falsch zurück zur
Album-Tauschbörse führen.

Vor weiteren Einzelkorrekturen soll die gesamte Trade-Navigation
kartiert werden.

## B16. RED BADGE / VISUELLE RESTE

**Einordnung: R7 POLISH.**

Auf der Album-Tauschbörse erscheint ein großer roter Badge/Fleck, der
sichtbar nicht zur aktuellen Sammlr-Designsprache passt.

Als visuellen R7-/Beta-Polish-Befund dokumentieren.

Nicht jetzt reparieren.

## Vorgemerkter Folgeauftrag – nicht begonnen

Noch NICHT durchführen, falls dies den R5-B1.2-Scope wesentlich
erweitern würde.

Im Dokument aber als nächsten Produkt-/Architekturauftrag vormerken:

"SAMMLR CLOSED-BETA INFORMATION ARCHITECTURE AUDIT"

Dieser spätere Audit soll automatisiert/statisch soweit möglich
kartieren:

- Flask Routes
- interne Links
- Forms / POST Targets
- Redirects
- Back Targets
- `origin`-Parameter
- Owner vs foreign paths
- Album Tradehub paths
- global `/trades`
- SmartMatch paths
- Request paths
- Trade Detail paths
- Profile → Album → Trade paths

Gesucht werden:

- Sackgassen
- falsche Rückwege
- doppelte Zwischenansichten
- zyklische Navigation
- historische Routen
- kontextabhängig widersprüchliche Navigation
- mehrere URLs für semantisch denselben Nutzerjob

Ziel danach:

IST-ROUTE-GRAPH
→ menschliche PO-Entscheidung
→ SOLL-NAVIGATION
→ erst dann Implementierung.

Der Audit wurde in B1.2 nicht durchgeführt. Reihenfolge bleibt: IST-ROUTE-GRAPH → menschliche PO-Entscheidung → SOLL-NAVIGATION → Implementierung. Keine UI-, Trade-, SmartMatch- oder Navigationsänderung aus diesen Notes.
