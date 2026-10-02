# TRADE-10 — Laufende Tausche & Anfragen

Stand: 2026-10-02. Isolierte Trade-v2-Preview, keine produktive Integration.

## Ergebnis und Einstiege

- Preview: http://127.0.0.1:8095/trade-v2/
- Laufende Tausche: http://127.0.0.1:8095/trade-v2/active
- Mehrere Zustände: http://127.0.0.1:8095/trade-v2/active?overview=mixed
- Eingegangen: http://127.0.0.1:8095/trade-v2/active?overview=incoming
- Du bist dran: http://127.0.0.1:8095/trade-v2/active?overview=action
- Wartet: http://127.0.0.1:8095/trade-v2/active?overview=waiting
- Änderung entscheiden: http://127.0.0.1:8095/trade-v2/active?overview=amendment
- Änderung abwarten: http://127.0.0.1:8095/trade-v2/active?overview=amendment-wait
- Versand bestätigen: http://127.0.0.1:8095/trade-v2/active?overview=shipping
- Empfang bestätigen: http://127.0.0.1:8095/trade-v2/active?overview=receipt
- Partnerproblem: http://127.0.0.1:8095/trade-v2/active?overview=problem
- Eigene Problemmeldung: http://127.0.0.1:8095/trade-v2/active?overview=problem-wait
- Q2: http://127.0.0.1:8095/trade-v2/active?overview=q2
- Leer: http://127.0.0.1:8095/trade-v2/active?overview=empty

Explizite Demo-Parameter ersetzen ausschließlich den lokalen Demo-Requeststand dieses Tabs, verwenden die bestehenden Commands und verschwinden anschließend aus der URL. Normales Öffnen/Reload erzeugt keine Fixtures, führt keine Commands aus und schreibt keine Trade-Daten. Start unverändert: `.venv/bin/python -B -m App.trade_v2`.

## Projektion statt neuer Domain

`overview.js` liest vorhandenen Request, Rolle, aktiven Snapshot, richtungsbezogenen Versand/Empfang und Amendment. Die Gruppen `incoming/action/waiting` sind flüchtige UI-Ausgabe, weder persistierte Domainstates noch neue Transitionen.

| Vorhandene Situation | Gruppe / primäre Aussage | Bestehendes Ziel |
| --- | --- | --- |
| Offene Anfrage, Empfänger | Eingegangen / Tauschanfrage ansehen | Request mit `role=recipient` |
| Offene Anfrage, Initiator | Wartet / Wartet auf Antwort | Request mit `role=sender` |
| Partner hat Problem gemeldet | Du bist dran / Problem klären | Receipt |
| Eigener Lösungsvorschlag liegt zur Bestätigung vor | Du bist dran / Lösung bestätigen | Receipt |
| Eigener Empfang noch ungeprüft | Du bist dran / Sendung prüfen | Receipt |
| Amendment pending, Gegenrolle | Du bist dran / Änderung bestätigen | Amendment |
| Amendment pending, Vorschlagende Rolle | Wartet / Wartet auf Änderung | Amendment |
| Eigene gemeldete Fehlmenge ohne Pending-Amendment | Du bist dran / Fehlmenge prüfen | Eigene Packansicht |
| Eigene Packliste offen | Du bist dran / Sticker raussuchen | Eigene Packansicht |
| Komplett gepackt, Partnerfehlmenge blockiert Freigabe | Wartet / Wartet auf Fehlmengenklärung | Eigene Packansicht |
| Komplett gepackt, Freigabe offen | Du bist dran / Packfreigabe bestätigen | Eigene Packansicht |
| Freigegeben, Adresszustimmung fehlt | Wartet / Wartet auf Adressfreigabe | Versand |
| Freigegeben, Versandart noch offen | Du bist dran / Versand vorbereiten | Versand/Adresse |
| Versandart gewählt, eigener Versand offen | Du bist dran / Versand bestätigen | Versand mit `view=prepare` |
| Eigener Versand erledigt, Partner noch nicht versendet | Wartet / Wartet auf Versand | Receipt, Q2 weiterhin erreichbar |
| Eigener Versand erledigt, Partner versendet, eigener Empfang offen | Du bist dran / Empfang bestätigen | Receipt |
| Eigene Problemmeldung oder Partner muss Lösung bestätigen, eigene Versandarbeit erledigt | Wartet / Wartet auf Problemklärung | Receipt |
| Eigener Empfang final, Gegenempfang offen, eigene Versandarbeit erledigt | Wartet / Wartet auf Empfang | Receipt |
| Completed / declined / cancelled / expired oder Frist erreicht | Nicht in der Übersicht | Keine neue Historie |

Priorität: terminale Vorgänge ausblenden; Anfrage; konkret beantwortbares Problem/Lösung/Empfangsprüfung; Amendment; eigene Pack-/Versandarbeit; Empfang bzw. Warten. So versteckt eine ausstehende Partnerreaktion keine noch bestehende eigene Versandpflicht. Genau eine primäre Aussage pro Trade. Der sekundäre Zugang „Sendung bereits erhalten?“ bleibt für akzeptierte Trades mit noch offenem eigenen Empfang verfügbar, auch während Packen/Warten. Keine automatische Behauptung tatsächlichen Empfangs.

Abschluss kann gemäß Q2 bei fehlenden Versandklicks bestehen. Solche abgeschlossenen Trades verschwinden entsprechend Auftrag aus dieser Übersicht; ihre operativen Slots werden dadurch **nicht** freigegeben. Der vorhandene Abschluss-/Versandweg bleibt außerhalb der Übersicht erhalten. Keine neue History- oder Archivfunktion; der bereits in TRADE-07 vorhandene Erledigt-Bereich auf der Hauptseite bleibt unverändert.

## Rollen und Kapazität

Bestehende Preview-Datensätze besitzen den festen Initiator Valentin und die jeweilige Partnerrolle. Die gemischte QA-Demo simuliert deshalb ausdrücklich Rollen **je Vorgang**, nicht eine produktive eingeloggte Identität: Eingang und Partnerproblem aus Empfängersicht, weitere Fälle aus Initiatorsicht. Namen, Mengen und Links stammen aus derselben vorhandenen `perspective`-Funktion. Keine Umbenennung eines Empfängers zum Initiator und keine versteckte Snapshot-Umschreibung. Dies wird im DEV-Bereich erläutert.

Die Rollenmetadaten sind separat vom Domainstore gespeichert und an ID plus Bindungszeit gebunden. Ein später neu erzeugter Request mit gleicher Demo-ID erbt keinen alten Rollenwechsel. Ohne QA-Metadaten gilt die bestehende Requestrichtung. Produktiv muss die autorisierte Rolle aus der tatsächlichen Teilnehmeridentität kommen.

Keine aggregierte 3/3-Anzeige, weil diese Multirollen-Demo keine gemeinsame Nutzeridentität hat. Bestehende `slots`/`incomingSlots` und alle Commands bleiben bytegleich. Die Zielansichten zeigen weiterhin ihre bereits vorhandenen rollenbezogenen Werte. Receipt, Projektion und Completion geben keinen Slot frei; ausschließlich die bestehenden zulässigen Übergänge gelten.

## Zeit, Sortierung und UI

Gruppenreihenfolge: Eingegangen → Du bist dran → Wartet. Innerhalb einer Gruppe zuerst früheste bestehende Anfragefrist bzw. älteste Bindung, bei Gleichstand stabile Request-ID. Keine künstlichen Aktionszeitstempel oder Prioritätsengine.

Nur offene Anfragen zeigen die vorhandene absolute Frist als Datum/Uhrzeit in der lokalen Browserzeitzone. Nach Ablauf wird die Zeile auch ohne Reload ausgeblendet; hierfür ist kein persistierender Expiry-Command nötig. Andere Lifecycle-Zustände erhalten keine Frist. Der Sekundentakt ersetzt DOM nur bei veränderter Projektion und erhält damit Fokus im unveränderten Zustand.

Mobile Zeilen enthalten Partner, gespiegelte Mengen, Albumzahl und eine primäre Aussage. Keine Stickerlisten, Post-it-Flut, technischen Zustandsnamen oder Adressen. Native Links mit Focus States; keine Swipe-Aktionen oder Animation. Hauptseite weiterhin drei Top-Vorschläge und Navigation, jetzt „Laufende Tausche“, ohne Tabellenpreview.

## Prüfung und Evidenz

Vor der Umsetzung: Verträge und TRADE-08/09/End-to-End-Audit, Request-/Pack-/Amendment-/Shipping-/Receipt-/Problemquellen gelesen; aktuelle Hauptseite und vorhandene Lifecycle-Browseransichten dokumentiert unter `before/`.

Ausgeführt:

```sh
.venv/bin/python -B -m unittest tests.test_trade_v2_preview tests.test_pax_preview -q
.venv/bin/python -B -m unittest tests.test_sticker_wall_product_island tests.test_ceoklaue_sticker_list -q
.venv/bin/python -B tests/research/check_trade_10.py
.venv/bin/python -B tests/research/check_trade_10_regressions.py
git diff --check
```

- 37 Unittests bestanden, getrennte Prozesse für die produktiven Referenztests.
- Neue Projektion: 172 Modellassertionen je Breite, 688 ausgeführt. Alle drei Herkünfte, beide Rollen, Gruppen/Links, Pending-Frist, Problem/Resolution, Amendments, Adressfreigabe, abgeschlossene/abgelehnte/beendete Vorgänge, Q2 und unveränderte Shipping-/Slotdaten.
- Vier Browserbreiten 375/390/430/1280: gemischte sechs Vorgänge, alle Gruppen, alle primären Direktlinks, Annahme → eigene Aktion, Ablehnung/Expiry/Completion → ausgeblendet, Q2-Empfang und Q2-Problem trotz fehlendem Partner-Versandklick.
- Touch/Maus/Keyboard, sichtbarer Fokus, Reduced Motion, keine horizontalen Überläufe, keine Browser-/HTTP-Fehler oder schreibenden Netzwerkanfragen. Normaler Overview-Reload verändert den Requeststore nicht.
- TRADE-01–09-Regressionsausgaben ausschließlich im neuen TRADE-10-Artefaktordner; alte Belege unverändert. Ausschließlich der neue Navigationstext und der explizite Rollenparameter im Overview-Direktlink ersetzen die entsprechenden TRADE-08-Test-Erwartungen.
- Kanonische Stack-Parität: bestehende 21 BRA-3-Fälle und 28 numerische Face-/Stackfälle, Wall5/Trade10 unverändert.

[Galerie](../tests/research/artifacts/trade-10/index.html) · [Neue Checks](../tests/research/artifacts/trade-10/checks.json) · [Vollständige Dateiliste](../tests/research/artifacts/trade-10/files.json) · [Hashes/Schutznachweis](../tests/research/artifacts/trade-10/scope-checks.json).

## Endaudit und Integration

Der [aktualisierte End-to-End-Audit](TRADE_V2_END_TO_END_AUDIT.md) dokumentiert vorhandene Preview-Funktionen, spätere Gestaltung, zu ersetzende Fixtures und kanonische Integrationspunkte. Zentrale offene Punkte: autorisierte reale Teilnehmer-/Rollenprojektion; versionierter Contract mit Legacy-Grenze; atomare Availability/Reservation/Slot- und Submit-Adapter; echte Snapshot-/Lifecyclepersistenz mit Nebenläufigkeit; Q2-Buchungen/Problemabschluss; Datenschutz und Adressfreigaben; Review von 24h/Withdraw/Reminder; gemeinsame kanonische Darstellung nach Regression.

Keine produktive DB-Mutation, kein git add, Commit, Push oder Deploy.
