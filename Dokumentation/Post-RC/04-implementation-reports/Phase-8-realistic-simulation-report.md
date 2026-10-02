# Phase 8 – Realistic-Simulation-Nachweis

**Stand:** 21. August 2026
**Status:** ABGESCHLOSSEN – technisch abgenommen
**Migration:** NEIN
**Product-Contract-Verletzung:** NEIN
**Externe Closed Beta freigegeben:** NEIN

## 1. Ergebnis und Grundlage

Phase 8 prüfte erstmals längere, verbundene Closed-Beta-Journeys in einer
gemeinsamen Mehrnutzerdatenbank. Grundlage waren der aktuelle Bauplan, die
Source-of-Truth-Matrix, der Product Contract Freeze, CB-017 und der
Phase-7-Hardening-Nachweis. Es wurde keine Produktfunktion, Produktsemantik,
Migration oder Designänderung ergänzt.

Der neue reproduzierbare Nachweis liegt in
`tests/test_phase8_realistic_simulation.py`. Alle schreibenden Vorgänge liefen
auf temporären V18-Kopien der kanonischen Referenzfixture. Die echte V7-
Bestandsdatenbank wurde ausschließlich für read-only Hash-, Schema-, Integrity-
und FK-Prüfungen geöffnet, nie als Simulationsziel verwendet, migriert oder
beschrieben.

## 2. Simulationspopulation und Datenvolumen

- 31 Nutzer einschließlich einer Registrierung über den echten HTTP-,
  Session- und CSRF-Pfad;
- 56 Zuordnungen über `vfl`, `wm26` und `em24`;
- 1.305 initiale Stickerzeilen, nach den Abschluss- und Tradejourneys mehr als
  1.700 Zeilen;
- Nutzer mit einem und mehreren Alben, wenig und vielen Doppelten, niedrigen
  und hohen Fortschritten sowie zwei historisch abgeschlossenen Alben;
- öffentliche und private Profile sowie `public`-, `friends`- und
  `private`-Alben mit unabhängigem Tradepool;
- gegenseitige Freundschaften, offene Anfragen und geblockte Paare;
- mehrseitige Inbox mit alten gelesenen und alten ungelesenen Einträgen;
- offene, obsolet gewordene, regulär abgeschlossene und mit Problem beendete
  Trades.

Der ergänzende verbindliche S35-Lastdatensatz umfasste 100 Nutzer, 10 Alben,
100.000 Stickerzeilen, 2.000 Trades, 5.000 Notifications und 1.000
Freundschaften.

## 3. Verbundene User Journeys

### Account und Sammlung

Registrierung, Login, Account, Profilprivacy, Albumstart, Inline-Mengenänderung,
Missing-/Duplicate-Ansicht und Logout liefen als zusammenhängender HTTP-Pfad.
Zwei VFL-Alben wurden über den letzten Sticker historisch abgeschlossen. Ein
paralleler Abschlussversuch erzeugte genau einen Completion-Fakt, eine
Completion-Trophy und ein Feed-Event. Eine anschließende Bestandsreduktion
änderte den historischen Abschluss nicht.

### Social und Privacy

Freundschaftsanfrage und Annahme, eine offen bleibende Anfrage sowie Block und
Interaktionssperre wurden im selben Bestand ausgeführt. Bereits gespeicherte
Feed-Events wurden nach späterer Albumprivatisierung und nach einem Block beim
Read verborgen. Owner-, Freundes- und Fremdperspektiven blieben durch
ProfilePrivacy und Albumprivacy getrennt; der Tradepool blieb unabhängig.

### SmartMatch und Trade-Lifecycle

- Zwei reguläre SmartTrades wurden angefragt, atomar reserviert, von beiden
  Seiten versendet und empfangen sowie abgeschlossen.
- Ein ungleicher Trade `2 abgegeben / 1 erhalten` blieb gerichtet erhalten;
  Statistik und Profil verwendeten denselben erfolgreichen Trade.
- Acceptance-, Shipping-, Receipt- und Rating-Retries erzeugten keine
  Doppelbuchung oder zweite Bewertung.
- Eine Bestandsänderung zwischen Anfrage und Annahme machte das unveränderte
  Smart-Paket `obsolete`; es entstand keine Reservierung und kein Auto-Shrink.
- Eine manuelle Anfrage wurde abgelehnt und blieb von der Smart-Obsolete-
  Semantik getrennt.

### Problem und konkurrierende Nachfrage

Ein weiterer Trade wurde beidseitig versendet, mit fehlender Position
gemeldet, identisch erneut gemeldet und terminal mit Problem beendet. Der
offene Rest wurde nicht eingebucht; Problem- und Terminal-Notification blieben
jeweils dedupliziert.

Zwei Nutzer fragten zeitlich überlappend dasselbe letzte verfügbare Duplikat
eines dritten Nutzers an. Parallele Acceptance auf getrennten SQLite-
Verbindungen ergab genau eine erfolgreiche atomare Reservierung; der zweite
Pfad scheiterte geschlossen. Es gab keine negative Menge und keine
Überreservierung.

### Inbox, Feed und Karriere

Alle neun produktiven CB-008-Typen entstanden aus den verbundenen Domainflows.
Kein neuer `legacy`-Write und kein nicht zugelassener Typ wurde gefunden.
Pagination markierte nur die 25 ausgelieferten Einträge; ein alter gelesener
Eintrag wurde entfernt, ein älterer ungelesener blieb bestehen und der globale
Unread-Zähler wurde neu berechnet.

Zwei News-Ereignisse belegten erneut das Response-Limit von höchstens einer
News. Notifications und `user_activity` wurden nicht als Feedquelle benutzt.
Current State, Completion-Karriere, erfolgreiche Trades, gerichtete Mengen,
Partner, Bewertungen und Trophäen lasen weiterhin ihre kanonischen Quellen.

## 4. Concurrency, Exactly-once und Integritätscheckpoints

Vier Checkpoints liefen nach Onboarding, parallelem Albumabschluss,
regulären/obsoleten Tradejourneys und abschließend nach Problem-/Race-/Feed-
und Inboxfluss. Jeder Checkpoint bestätigte:

- `integrity_check = ok`, `foreign_key_check` leer;
- keine negativen oder formal inkonsistenten Bestandszeilen;
- keine Self-Trades und keine unzulässige aktive Überreservierung;
- keine doppelten Completion-Fakten oder Trophy-Unlocks;
- keine doppelten Notification-Dedupe-Keys;
- keine unerlaubten neuen Notification-Typen und keine neuen Legacy-Writer;
- ausschließlich die vier zugelassenen CB-007-Feedtypen;
- stabile historische Abschlüsse trotz später verändertem Current State.

## 5. Privacy und Security

Die Simulation bewies aktuelle Privacy-Auswertung für bereits gespeicherte
Events, Blocks vor sozialer Sichtbarkeit, gegenseitige Freundschaft,
Profilprivacy, Albumprivacy, nutzerbezogene Inboxwrites, CSRF und Sessionwechsel.
Die zusätzliche kombinierte Suite umfasste diese Bereiche zusammen mit Trade,
Completion, Feed und Notifications: **359/359**, 0 Fehler, 0 Skips. Es wurde
kein Privacy- oder Security-Leak gefunden.

## 6. Performance

Gunicorn lief mit einem Worker, 20 Threads und 20 parallelen Requests auf der
isolierten Datei
`/private/tmp/sammlr-phase8-performance-20260821-run2.db`. Artefakt:
`/private/tmp/sammlr-phase8-performance-20260821-run2.json`.

| Pfad | P95 | Fehler | Ergebnis |
|---|---:|---:|---|
| Login | 8,073 ms | 0 | PASS |
| Home | 64,048 ms | 0 | PASS |
| Sammlung | 67,188 ms | 0 | PASS |
| Album | 469,071 ms | 0 | PASS |
| Stickerwall | 429,284 ms | 0 | PASS |
| Suche | 82,475 ms | 0 | PASS |
| Tauschbörse | 76,630 ms | 0 | PASS |
| Deal | 139,961 ms | 0 | PASS |
| Notifications | 34,118 ms | 0 | PASS |
| Profil | 196,976 ms | 0 | PASS |

Ergebnis: **10/10 unter 500 ms**, Fehlerquote 0 %. Die besonders beobachtete
Stickerwall blieb unter ihrem Phase-7-Wert von 439,025 ms. Die Albumseite war
diesmal der langsamste Pfad, blieb aber reproduzierbar innerhalb des Gates. Es
gab keinen klaren Skalierungsfehler und deshalb keine opportunistische
Optimierung.

## 7. Gefundene Bugs und Änderungen

Es wurde **kein Produktbug** gefunden. Entsprechend waren kein Produktfix und
keine Migration nötig. Während des Aufbaus wurde lediglich die Testpopulation
so korrigiert, dass die für Problemtrades vorgesehenen Nutzer gemäß ihrem
Szenario im Tradepool aktiv sind; das war kein Befund im Anwendungscode.

Neu ist ausschließlich der reproduzierbare Phase-8-Regressionstest
`tests/test_phase8_realistic_simulation.py` sowie die Abschlussdokumentation.

## 8. Tests und Abschlussgates

- gezielte realistische Simulation: **1/1**, grün;
- kombinierte Privacy-/Trade-/Lifecycle-/Feed-/Inbox-Suite: **359/359**,
  0 Fehler, 0 Skips;
- vollständige Regression Lauf 1: **713/713**, 0 Fehler, 0 Skips, 8,213 s;
- vollständige Regression Lauf 2: **713/713**, 0 Fehler, 0 Skips, 8,094 s;
- aktive Pythonquellen, Tests und Skripte: `py_compile -Werror` grün;
- `pip check`: `No broken requirements found`;
- `git diff --check`: ohne Befund;
- Gunicorn-Startup und `/healthz`: im S35-Lauf grün;
- finale echte DB: Schema V7, `integrity_check = ok`, FK leer.

## 9. Bestands-DB-Schutz

SHA-256 vor und nach Phase 8:
`3eb9da3b6d4898533030221bc80e8ed6406a25458eb8e1bca1f0e473a515b056`.

Die echte DB wurde nicht migriert oder verändert. Sämtliche Populationen,
Journeys, Concurrencyfälle und Lastmessungen verwendeten Wegwerfdateien unter
dem Test-Tempbereich beziehungsweise `/private/tmp`.

## 10. Restrisiken und Abschlussbewertung

Die Simulation bleibt lokal und zeitlich komprimiert; echte Netzlatenz,
mehrtägige menschliche Bedienmuster, Betreiber-Backupdrill und reale externe
Nutzerrückmeldungen können sie nicht vollständig ersetzen. Die bestehende
Testschuld zu einzelnen älteren `ResourceWarning`-Hinweisen bleibt unverändert
und verursachte keine Fehler oder Skips.

Phase 8 ist vollständig grün, formal abgeschlossen und technisch abgenommen.
Es besteht keine Product-Contract-Verletzung. Externe Nutzer sind weiterhin
nicht freigegeben. Nächster zulässiger Schritt ist **Phase 9 – finales
Closed-Beta-Gate**; die dort noch erforderlichen Nachweise sind in
`08-closed-beta-gate.md` festgehalten.
