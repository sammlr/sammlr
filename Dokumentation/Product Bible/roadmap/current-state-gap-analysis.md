# Sammlr Current-State Gap Analysis

| Metadatum | Wert |
| --- | --- |
| Stand | 2026-07-27 |
| Charakter | Technische und fachliche Soll-/Ist-Analyse |
| Referenz | Sammlr Product Bible |
| Implementierungsauftrag | Keiner |

> Folgeplanung: Die aus dieser Analyse abgeleitete verbindliche Umsetzungsreihenfolge steht in der [Sammlr Development Roadmap V1](development-roadmap-v1.md).

## Zweck und Abgrenzung

Dieser Bericht vergleicht die aktuelle Sammlr-Anwendung mit der langfristigen Product Bible. Er dokumentiert vorhandene Substanz, Abweichungen, fehlende Grundlagen, technische Risiken und Abhängigkeiten.

Er ist keine Sprint-Roadmap, keine Migrationsanweisung und keine Aufforderung, sämtliche langfristigen Visionen kurzfristig umzusetzen. Während der Analyse wurden weder Anwendungscode noch Datenbank, Templates, CSS, JavaScript oder Assets verändert.

Analysiert wurde der aktuelle lokale Arbeitsstand. Die bereits vor Beginn vorhandene, nicht eingecheckte Änderung an `App/webapp.py` wurde als Teil dieses Ist-Zustands gelesen, aber nicht verändert.

## Statuslegende

| Status | Bedeutung |
| --- | --- |
| ✅ PASST | Vorhanden und entspricht im Kern dem Sollzustand |
| 🔧 VORHANDEN, MUSS UMGEBAUT WERDEN | Wiederverwendbare Grundlage vorhanden, aber fachlich oder technisch noch nicht ausreichend |
| 🧱 FEHLT | Nicht vorhanden oder keine tragfähige Grundlage vorhanden |
| 🗄️ ZUKUNFT | Bewusst spätere Vision, aktuell kein Implementierungsziel |
| ⚠️ ARCHITEKTURRISIKO | Grundlage kann spätere Entwicklung oder sichere Änderungen erschweren |

Ein Eintrag kann mehrere Statussymbole tragen.

## A. Executive Summary

### Gesamteinschätzung

Der aktuelle Code ist der Product Bible näher, als seine monolithische Struktur zunächst vermuten lässt. Sammlr besitzt bereits:

- eine nutzbare Multiuser-Grundlage,
- mehrere Albumtypen pro Nutzer,
- mengenbasierte Stickerbestände,
- eine leistungsfähige Stickerwall mit Filtern, Suche, Batch-Modus und direktem Mengenregler,
- eine schnelle Papier-Stickerliste,
- albumbezogene Tauschpartnerermittlung und manuelle Dealpakete,
- Tradeanfragen mit Annahme/Ablehnung,
- einen real funktionsfähigen, beidseitig bestätigten Abschluss mit automatischer Bestandsbuchung,
- einfache Notifications,
- Tradehistorie, Statistiken und ein umfangreiches Trophäensystem.

Damit existiert eine schützenswerte vertikale Produktstrecke von der Bestandspflege über Partnerfindung bis zum abgeschlossenen Trade. Der dokumentierte erste echte Sammlr-Trade passt zum vorhandenen Datenbestand: In `trade_requests` existiert ein beidseitig bestätigter, abgeschlossener Trade.

Die Anwendung entspricht dennoch noch nicht der neuen Zielarchitektur. Die größten fachlichen Lücken sind:

1. kein getrenntes Modell für Albumtyp, Albumexemplar, Zuordnung und freien Bestand,
2. keine Reservierungen und kein belastbarer Trade-Lifecycle mit Versand/Empfang pro Seite,
3. kein optimierender, konfliktfreier Smart Trader,
4. Home ist derzeit die Sammlr-Zentrale und keine operative Startseite,
5. Profil/Community, Freunde, Bewertungen und globale Notifications sind weitgehend nicht vorhanden.

Die größten technischen Risiken sind:

1. nahezu gesamte Anwendung, SQL, HTML und JavaScript in einer 7.561-zeiligen Datei,
2. das SQLite-Schema kann zentrale Sollzustände nicht ausdrücken und besitzt praktisch keine referenzielle Absicherung,
3. Bestandsänderungen sind über viele Routen dupliziert,
4. `trade_requests` überlädt Anfrage, Deal und Abschluss in einer einzigen flachen Tabelle,
5. es existiert keine automatisierte Testsuite als Schutz für den real funktionierenden Kernflow.

### Grundsätzliche Empfehlung

Kein Greenfield-Neustart. Die vorhandenen fachlichen Kerne sollten kontrolliert extrahiert und abgesichert werden:

- Stickerauflösung und Albummetadaten,
- Mengen- und Fortschrittsberechnung,
- Stickerwall/Papierliste,
- Partnerkandidaten und manuelle Paketerstellung,
- bestätigter Tradeabschluss,
- Trophy-Definitionen und Unlock-Historie.

Neue sichtbare Features sollten nicht vor den dafür erforderlichen Zustandsmodellen gebaut werden. Insbesondere hängt ein verlässlicher Smart Trader von Bestands- und Reservierungslogik ab; Home-Tradekarten hängen wiederum vom Trade-Lifecycle und adressierbaren Notifications ab.

## B. Gap Matrix

| Produktbereich | Funktion / Thema | Ist-Zustand | Soll-Zustand | Status | Fundstellen | Abhängigkeiten / Risiko |
| --- | --- | --- | --- | --- | --- | --- |
| Sammlung | Album hinzufügen | Unterstützte, noch nicht zugeordnete Albumtypen können hinzugefügt werden | Albumtyp auswählen; erstes oder weiteres Albumexemplar anlegen | ✅ für erstes Exemplar; 🔧 für Zielmodell | `alben_hinzufuegen()` und `album_hinzufuegen()`, `App/webapp.py:2605-2679`; `user_albums` | Albuminstanzmodell |
| Sammlung | Mehrere verschiedene Alben | Nutzer kann mehrere Albumtypen besitzen | Mehrere Typen und später mehrere Exemplare desselben Typs | ✅ / 🗄️ | `user_albums`, `App/webapp.py:400-407` | `UNIQUE(user_id, album_id)` blockiert Mehrfachexemplare |
| Sammlung | Albumtyp / Albumexemplar | Nur globale `albums.id` plus Nutzerzuordnung | Eigene Albuminstanz mit Name, Aktivität, Fortschritt und Priorität | 🧱 ⚠️ | Tabellen `albums`, `user_albums`; `App/webapp.py:369-407` | Fundament für Mehrfachalbum, Zuordnung, Vitrine |
| Sammlung | Favorit | `users.favorite_album_id`, Auswahl und eigene Route vorhanden | Favorit bezieht sich auf konkretes Albumexemplar innerhalb Sammlung | ✅ heute; 🔧 später | `current_favorite_album_id()`, `favorit()`, `App/webapp.py:2222-2584` | Navigation und später Albuminstanz-ID |
| Sammlung | Aktive Alben | Startseite zeigt unvollständige Nutzeralben als aktiv | explizit aktiv/deaktivierbar; Deaktivierung beeinflusst Bedarf, nicht freien Pool | 🔧 | `startseite()`, `App/webapp.py:2162-2220`; `user_albums` ohne Status | Albuminstanz und Tradebedarf |
| Sammlung | Vitrine | Vollständige Alben werden dynamisch getrennt angezeigt | vollständige Albumexemplare automatisch in Vitrine; bei Verlust zurück | ✅ im Einzelexemplar-Kern | `startseite()`, `App/webapp.py:2202-2214`; `album_portal_cards()` | Albuminstanz für mehrere volle Exemplare |
| Sammlung | Stickerwall | Kapitel, Karten, Fortschritt, Filter, Suche, Batch und Detailmodal vorhanden | visuelle Hauptverwaltung eines konkreten Exemplars | ✅, schützenswert | `albumseite()`, `App/webapp.py:2836-4164` | Funktion ist mit 1.330 Zeilen stark gekoppelt |
| Sammlung | Filter und Suche | Alle/Fehlende/Vorhandene/Doppelte und Code-/Textsuche vorhanden | dieselben Kernfilter; Code zuerst | ✅ | `filter_ok()`, `App/webapp.py:723-732`; Wall-UI ab `3015` | Für „unterwegs“ erweiterbar |
| Sammlung | Direkter Mengenregler | Modal mit `− Anzahl +`, sofortige JSON-Aktualisierung | kompakte direkte Mengenpflege | ✅ im Kern | `update_sticker_quantity_inline()`, `App/webapp.py:4786-4835`; JS `3269-3450` | Reservierungen müssen Minus künftig schützen |
| Sammlung | Papier-Stickerliste | Eigene schnelle Liste; Doppelte erscheinen mehrfach; manueller Transfer möglich | konkrete, schnelle Papierliste pro Albumexemplar | ✅, schützenswert | `stickerliste()`, `App/webapp.py:4165-4490` | Später Instanzbezug nötig |
| Sammlung | Batch-/Code-Eingabe | Batch-Auswahl und Codeauflösung vorhanden | mehrere Eingabemethoden | ✅ Basis | `bulk_add()`, `bulk_remove()`, `resolve_code()`, `App/services/albums.py` | Mutation ist mehrfach implementiert |
| Sammlung | Physischer Bestand | `quantity` speichert Gesamtmenge; `duplicates` wird zusätzlich gespeichert | physischer Bestand als Wahrheit; Doppelte berechnet | 🔧 ⚠️ | Tabelle `stickers`, `App/webapp.py:358-367`; `change_sticker_quantity()` | Redundantes `duplicates` kann auseinanderlaufen |
| Sammlung | Albumzuordnung / freier Pool | Ein Stickerbestand ist direkt an `album_id` gebunden; erste Kopie gilt Album, Rest doppelt | explizite Zuordnung zu Albumexemplaren plus freier albumtypbezogener Pool | 🧱 ⚠️ | `lade_album_for_user()`, `App/webapp.py:523-552` | Kernabhängigkeit für Mehrfachalbum und Trades |
| Sammlung | Reserviert / unterwegs | Keine entsprechenden Bestands- oder Zuordnungstabellen | getrennte verbindliche Zustände | 🧱 ⚠️ | Schema `App/webapp.py:344-448` | Voraussetzung für sicheren Lifecycle und Home |
| Sammlung | Manuell vs. automatisch | Manuelle Änderungen und automatische Abschlussbuchung existieren | explizite Nutzereingabe vs. Prioritätsautomatik | 🔧 | Mutationen `App/webapp.py:2836-5097`; `complete_trade()` | Keine Priorität/Zuordnung, viele Schreibpfade |
| Smart Trades | Basismatching | Gegenseitige Fehlende/Doppelte pro Album und Nutzer werden berechnet | Datengrundlage für Smart Trader | ✅ als Basis | `trade_candidates()`, `App/webapp.py:5868-5885` | Reservierungen und Zustände fehlen |
| Smart Trades | Partnerranking | Sortierung primär nach Anzahl der erhältlichen Sticker | Fortschritt, wenige Deals, Zuverlässigkeit, Konfliktfreiheit | 🔧 | `trades_overview()`, `App/webapp.py:6642-6927` | Optimierungsengine fehlt |
| Smart Trades | Manuelle Dealpakete | Nutzer wählt konkrete Mengen; Server prüft Verfügbarkeit und `geben >= bekommen` | manueller Trade darf freiwillig mehr geben | ✅, schützenswert | `trade_center()`, `create_trade_request()`, `App/webapp.py:5887-6588` | Validation erhalten, um Reservierung ergänzen |
| Smart Trades | 1:1-Smart-Pakete | Kein automatisch zusammengestelltes nicht verhandelbares Paket | optimierte Smart-Trade-Pakete | 🧱 | Keine eigene Engine/Entität | Bestandsmodell, Reservierungen, Optimierer |
| Smart Trades | Konfliktfreie Top Matches | Partner werden unabhängig bewertet; Bestände werden nicht partnerübergreifend verplant | gemeinsame konfliktfreie Top-3-Optimierung | 🧱 ⚠️ | `album_trade_preview_counts()`, `trades_overview()` | Erfordert zentralen Verfügbarkeits-Snapshot |
| Smart Trades | Markt-/Tauschabdeckung | Marktfehlende und direkte Partner werden grob gezählt | getrennte Markt- und simulierte persönliche Tauschabdeckung | 🔧 | `album_trade_preview_counts()`, `App/webapp.py:2309-2352` | Kein konfliktfreier Gesamtplan |
| Smart Trades | Parallele Anfragen / Ablauf | Beliebig viele offene Anfragen; kein Ablaufjob | kurzes Ablaufdatum, V1-Limit, keine Reservierung vor Annahme | 🔧 ⚠️ | `trade_requests.created_at`; `create_trade_request()` | Statuszeit, Expiry und Policy fehlen |
| Smart Trades | Dynamische Paketanpassung | Bei Erstellung erneut validiert, danach nicht angepasst | transparente Verkleinerung/erneute Zustimmung | 🧱 | `create_trade_request()`, `App/webapp.py:6514-6588` | Reservierung und Paketversionen |
| Smart Trades | Albumübergreifende Trades | `trade_requests.album_id` erzwingt genau ein Album | später freigegebene Alben gemeinsam optimieren | 🗄️; Schema ⚠️ | `trade_requests`, `App/webapp.py:409-421` | Tradepositionen benötigen Albumidentität |
| Trade Lifecycle | Anfrage / Annahme / Ablehnung | `open`, `accepted`, `declined`; Benachrichtigungen vorhanden | kurzlebige Anfrage, verbindliche Annahme | ✅ Kern; 🔧 Details | Routen `App/webapp.py:6514-6639` | Ablauf und Gründe fehlen |
| Trade Lifecycle | Reservierung bei Annahme | Status wechselt nur auf `accepted`; Bestand bleibt frei sichtbar | enthaltene Sticker verbindlich reservieren | 🧱 ⚠️ | `accept_trade_request()`, `App/webapp.py:6590-6614` | Doppelvergabe möglich |
| Trade Lifecycle | Dealzustände | Eine Tabelle mit `status`, `from_confirmed`, `to_confirmed` | klare State-Machine mit Versand, unterwegs, Empfang, Problem | 🔧 ⚠️ | `trade_requests`, `trade_status_label()`, `App/webapp.py:409-432, 5198-5220` | Flaches Modell nicht ausreichend |
| Trade Lifecycle | Beidseitiger Abschluss | Beide markieren „durchgeführt“; dann Status `completed` und atomare Buchung | Versand/Empfang getrennt; Abschluss nach beidseitigem Empfang | ✅ Kernidee; 🔧 Semantik | `confirm_trade_done()`, `complete_trade_if_ready()`, `App/webapp.py:5097-5137, 6933-6984` | Erfolgreichen Kernflow schützen |
| Trade Lifecycle | Bestandsbuchung | Sämtliche Bestände erst nach beiden generischen Bestätigungen gebucht | Ausgang bei Versand/Zustandswechsel; Eingang pro Seite bei Empfang | 🔧 ⚠️ | `complete_trade()`, `App/webapp.py:5097-5112` | Keine physische Zwischenrealität |
| Trade Lifecycle | Deal geplatzt / Problem | Jede Seite kann angenommenen Deal direkt auf `failed` setzen | nachvollziehbarer Problem-/Abbruchprozess ohne beiläufige Auflösung | 🔧 ⚠️ | `fail_trade_done()`, `App/webapp.py:6986-7021` | Einseitige endgültige Zustandsänderung |
| Trade Lifecycle | Versand / Empfang / Teilempfang | Nicht separat modelliert | je Seite getrennt, Teilempfang und verloren/falsch | 🧱 | Keine Felder/Tabellen | State-Machine und Positionsebene |
| Trade Lifecycle | Fristen | `created_at`, aber keine Versandfrist oder Überfälligkeit | fünf Werktage, vorher kommuniziert, überfällig statt blind gelöscht | 🧱 | `trade_requests.created_at` | Zeitstempel pro Übergang nötig |
| Trade Lifecycle | Dealchat / Bilder | Nicht vorhanden | dealgebundener Text-/Bildchat und Systemchronologie | 🧱 | Keine Tabelle/Route | Deal-ID, Speicherung, Datenschutz |
| Trade Lifecycle | Historie | Abgeschlossene Trades nach Album, Partner, Datum und Mengen | vollständige erfolgreiche Historie; Probleme separat nachvollziehbar | 🔧 | `profile_trade_archive_html()`, `App/webapp.py:574-676` | Nutzt Anfragezeit statt Abschlusszeit; keine Details/Chat |
| Trade Lifecycle | Bewertung | Nicht vorhanden | erst nach tatsächlicher Abwicklung, 1–5 Sterne | 🧱 | Keine Tabelle/Route | Lifecycle-Abschluss und Profil |
| Profil | Eigenes Profil | Name, Username, Initialavatar und Links vorhanden | Sammlerseite mit Vertrauen, Alben, Vitrine, Trophäen, Statistik, Freunde | 🔧 | `profil()`, `App/webapp.py:7288-7399` | Gute Hülle, Inhalte verteilt |
| Profil | Nutzername / Klarname | Beide vorhanden und editierbar | Username primär, Klarname optional | ✅ Kern | `users`; Profilrouten `App/webapp.py:7417-7490` | Escaping/Validierung vereinheitlichen |
| Profil | Profilbild / Standort | Initialenavatar; keine Bild- oder Standortfelder | optionales Bild und Standort | 🧱 | `users`-Schema | Upload/Datenschutz |
| Profil | Fremde Profile / Sichtbarkeit | Keine fremde Profilroute und keine Albumprivacy | öffentliche/freundes/private Sammlerseite | 🧱 | Keine Modelle/Routen | Identität, Privacy, Freunde |
| Profil | Trophäen / Statistik | Umfangreiche eigene Bereiche vorhanden | kompakte Vorschau plus tiefe Bereiche | ✅ Basis, schützenswert | `/trophaeen`, `/statistik`, `App/webapp.py:7053-7287` | Navigation umordnen, nicht neu schreiben |
| Profil | Erfolgreiche Trades / Bewertung | Tradearchiv und Count vorhanden; keine Bewertung | prominent Vertrauen und erfolgreiche Trades | 🔧 | `profile_trade_archive_html()`, Statistik | Bewertungsmodell |
| Community | Freunde / Anfragen / Blockieren | Nicht vorhanden | beidseitige Freundschaften, Anfragen, Blockieren | 🧱 | Keine Tabellen/Routen | Profil, Notifications, Interaktionsregeln |
| Community | Aktivitätsstatus | Nicht vorhanden | grober datenschutzgerechter Status | 🧱 | `users` ohne Zeitfelder | Login-/Aktivitätsereignisse, Privacy |
| Profil | Tauschpotenzial / Direkteinstieg | Partnerkarten zeigen Mengen und starten Trade; kein fremdes Profil | profilweiter Nutzen und direkter Einstieg | 🔧 | `/album/<album_id>/trade/<user>` | Fremdprofil plus gemeinsame Matchingbasis |
| Home | Startseite | `/` ist Sammlr-Zentrale mit aktiven Alben und Vitrine | operative Home-Seite, getrennt von Sammlung | 🔧, klarer Sollkonflikt | `startseite()`, `App/webapp.py:2162-2220` | Sammlung braucht eigene Route; Navigation |
| Notifications | Datenmodell | Tabelle mit Titel, Body, `is_read`, Zeit; Tradeevents schreiben Einträge | adressierbare Notification-Historie mit Badge und Deep Links | 🔧 | `notifications`, Service `App/services/notifications.py` | Zielobjekt, Typ, Event, Archivierung fehlen |
| Notifications | Anzeige / Glocke | Kein sichtbarer globaler Zugang; `unread_notifications()` wird nicht genutzt | Glocke, Ungelesen-Badge und Zentrale | 🧱 trotz Datenbasis | `app_header()`, `App/webapp.py:503-515`; Mark-read `7042-7051` | Header und Notification-Routen |
| Home | Handlungsbedarf / Tradezusammenfassung | Trade-Popup-Helfer existiert, wird aber nicht aufgerufen; keine Homeaufgaben | priorisierte offene Aufgaben und kompakte Deals | 🧱 / 🔧 | `trade_request_popup_html()`, `App/webapp.py:5402-5420` | Lifecycle, Deep Links |
| Home | Feed / Freundesnews / Sammlr News | Nicht vorhanden | getrennte passive Bereiche | 🧱 | Keine Modelle | Freunde/Events; bewusst nach Kern |
| Navigation | Bottom-Navigation | Fünf Punkte: Profil, Favorit, sammlr, Tauschen, Statistik | Sammlung, sammlr./Home, Tauschen | 🔧 | `bottom_nav()`, `App/webapp.py:2427-2478` | Routen weitgehend wiederverwendbar |
| Navigation | Header | Nur Markenlink auf `/` | globale Marke, Glocke und Avatar | 🔧 | `app_header()`, `App/webapp.py:503-515` | Home-/Sammlungsroute und Notifications |
| Navigation | Fachliche Besitzer | Sammlung liegt auf `/`; Profil/Favorit/Statistik permanent; Tradefunktionen albumlokal und global | klare Besitzer mit mehreren Einstiegen | 🔧 | Routen ab `2162`; Album- und globale Trades | Primär UI/Routeordnung, aber nicht nur CSS |
| Navigation | Deep Links / Rückwege | Konkrete Trade-URLs vorhanden; Rückwege meist fest codiert | Zielobjekt direkt, Rückweg nach Ursprung | 🔧 | `trade_detail()`, `App/webapp.py:5307-5400` | Notification-Ziel und Navigationkontext |
| Navigation | Doppelte Fachansichten | Album- und globale Tradeübersicht führen ähnliche Queries/Renderlogik aus | ein Fachmodell, kontextuelle Ansichten | 🔧 ⚠️ | `album_trades()` und `trades_overview()` | Gemeinsamen Application-Service extrahieren |
| Zukunft | Scanner, Offline, QR, regional, Marketplace, Shop, Versandprodukte | nicht oder nur konzeptionell vorhanden | bewusst spätere Visionen | 🗄️ | Product Bible | Nicht in kurzfristige Gap-Arbeit ziehen |

## C. Analyse nach Produktbereichen

### A. Sammlung / Alben / Stickerverwaltung

#### Stärken

Die Sammlung ist der reifste Produktbereich. `lade_album_for_user()` berechnet Fortschritt und Doppelte konsistent aus `quantity`; Stickerwall, Kapitelstruktur, Filter und Suche sind funktional miteinander verbunden. Der direkte Mengenregler aktualisiert Karten, Fortschritt und Trophy-Popups ohne Vollreload. Die Papierliste bildet Doppelte mehrfach ab und erlaubt schnelle reale Bestandskorrekturen.

Besonders schützenswert:

- `resolve_code()` und `all_codes()` für die unterstützten Albumtypen,
- Kapitel-/Teamstruktur der Wall,
- `change_sticker_quantity()` als Keim eines zentralen Mengenservices,
- Papierlisten-Workflow,
- Trophy-Auslösung nach Bestandsänderungen.

#### Fachliche Abweichungen

`albums` beschreibt ausschließlich globale Albumtypen. `user_albums` ist nur eine Join-Tabelle und erzwingt `UNIQUE(user_id, album_id)`. Ein Nutzer kann daher drei verschiedene Albumtypen, aber nicht zwei konkrete WM26-Exemplare besitzen.

`stickers` verbindet den gesamten physischen Bestand direkt mit `user_id + album_id + sticker_code`. Die erste Kopie erfüllt implizit das eine Album; jede weitere Kopie ist automatisch doppelt. Für das heutige Einzelexemplar-Modell ist dies einfach und funktional. Es kann aber weder konkrete Albumzuordnungen noch freien Pool, Mehrfachbedarf oder Priorität ausdrücken.

Die Spalte `duplicates` ist vollständig aus `quantity` ableitbar und wird parallel gespeichert. Im aktuellen Datenbestand ist sie zwar konsistent, aber jeder neue Schreibpfad muss beide Werte korrekt aktualisieren.

#### Reale Datenhinweise

Der aktuelle Datenbestand enthält keine doppelten Zeilen für denselben Schlüssel `user_id + album_id + sticker_code` und keine Abweichung zwischen `duplicates` und `quantity - 1`. Es gibt jedoch einen Mengenwert von `10.000` für einen einzelnen Sticker. Das kann absichtlicher Testbestand sein, verzerrt aber globale Statistiken und Trophy-Schwellen. Vor späteren Analysen sollte Test-/Produktionsdatenstatus geklärt werden; in dieser Aufgabe wurde nichts bereinigt.

### B. Smart Trades / Tauschpartnerfindung

#### Wiederverwendbare Basis

`trade_candidates()` berechnet korrekt die unmittelbare bilaterale Schnittmenge:

- Nutzer fehlt Sticker und Partner besitzt mindestens zwei,
- Nutzer besitzt mindestens zwei und Partner fehlt Sticker.

Die manuelle Paketerstellung unterstützt Mengen auf der Empfangsseite und prüft serverseitig die tatsächliche Verfügbarkeit. Die Regel, nicht mehr zu verlangen als anzubieten, wird sowohl im Browser als auch serverseitig geprüft.

#### Grenzen

Das System ist eine gute manuelle Tauschbörse, aber noch kein Smart Trader im Sinne der Product Bible:

- Partner werden isoliert nach `du_suchst` sortiert.
- Es gibt keine gemeinsame Optimierung über mehrere Partner.
- Derselbe freie Sticker kann in mehreren offenen Anfragen vorkommen.
- Aktive Partner werden pauschal aus neuen Vorschlägen ausgeschlossen.
- Anfragepakete verfallen nicht und werden nach Bestandsänderungen nicht neu berechnet.
- Marktabdeckung wird als Vereinigungsmenge vorhandener Doppelter gezählt; persönliche Tauschabdeckung wird nicht simuliert.

Die Matchingfunktionen sollten als fachliche Primitive erhalten bleiben, aber auf eine zentrale Verfügbarkeitsabfrage umgestellt werden. Ein Optimierer darf nicht direkt aus den heutigen `quantity >= 2`-Abfragen gebaut werden, solange Reservierungen und Zustände fehlen.

### C. Tradezentrale / Dealabwicklung

#### Funktionierende Substanz

Der aktuelle Kernflow ist klar nachvollziehbar:

1. `create_trade_request()` validiert und speichert ein JSON-Paket.
2. `accept_trade_request()` setzt `accepted`.
3. Beide Seiten setzen über `confirm_trade_done()` ihr Bestätigungsflag.
4. `complete_trade_if_ready()` ruft bei zwei Bestätigungen `complete_trade()` auf.
5. Bestände beider Nutzer werden in einer Transaktion angepasst.
6. Status wird `completed`; Notifications und Trophäen folgen.

Dieser Kern hat einen real abgeschlossenen Datensatz und sollte nicht unnötig neu geschrieben werden.

#### State-Machine-Eignung

Die aktuelle Tabelle ist für die vollständige Ziel-State-Machine nicht ausreichend:

- `status` mischt Anfrage- und Dealstatus.
- `from_confirmed` und `to_confirmed` bedeuten generisch „durchgeführt“, nicht Versand oder Empfang.
- Es fehlen Zeitpunkte für Annahme, Frist, Versand, Empfang, Problem und Abschluss.
- Paketpositionen liegen als JSON-Arrays in zwei Spalten.
- Es gibt keine Reservierungsentität, Sendung, Empfangsposition, Chatnachricht, Bewertung oder Ereignisfolge.
- Ein Altstatus `cancelled` existiert im Datenbestand, wird vom aktuellen Statusrenderer nicht speziell behandelt; aktueller Code verwendet `failed`.

Eine erweiterte State-Machine nur durch immer weitere Spalten in `trade_requests` würde schnell unübersichtlich. Trotzdem sollte der bestehende Abschlussalgorithmus als verifiziertes Verhalten in Tests konserviert und anschließend kontrolliert hinter einem neuen Lifecycle-Service verwendet werden.

#### Kritische Semantik

Annahme reserviert heute nichts. Dadurch kann ein Sticker nach Annahme weiterhin manuell entfernt oder in einem weiteren Deal angeboten werden. Beim Abschluss reduziert `change_sticker_quantity()` Mengen bis mindestens null; eine inzwischen fehlende Ausgangsmenge führt nicht zu einem harten Abschlussfehler. Das ist das größte unmittelbare fachliche Integritätsrisiko des Tradebereichs.

`fail_trade_done()` erlaubt jeder beteiligten Seite, einen angenommenen Deal einseitig endgültig auf `failed` zu setzen. Das ist funktional, entspricht aber nicht dem geplanten differenzierten Problemprozess.

### D. Profil & Community

Das eigene Profil bietet eine brauchbare Hülle mit Nutzername, Klarname, Initialavatar, Statistik, Trophäen und Tradearchiv. Die Product-Bible-Hierarchie ist jedoch nur in getrennten Zielseiten vorhanden, nicht als echte Sammlerseite.

Vollständig fehlen:

- fremde Profile,
- Profilbilder und Standort,
- öffentliche/freundes/private Sichtbarkeit,
- Freunde und Freundschaftsanfragen,
- Blockieren,
- Aktivitätsstatus,
- Bewertungen,
- profilweites Tauschpotenzial.

Der direkte Tradeeinstieg zu einem bekannten Partner existiert bereits im Albumkontext. Er kann später vom fremden Profil wiederverwendet werden.

Beim Löschen eines Kontos werden Tradezeilen vollständig gelöscht. Das widerspricht langfristig der Anforderung, relevante Tradehistorie und Nachweise trotz Blockierung oder Kontoproblemen zu erhalten. Eine spätere Account-Lifecycle-Entscheidung ist erforderlich; hier wurde nichts verändert.

### E. Home / Startseite / Notifications

Die Route `/` ist heute exakt die Sammlr-Zentrale: aktive Alben, Albumfortschritt, Favorit, Album hinzufügen und Vitrine. Sie ist keine Home-Seite der neuen Product Bible.

Die Notification-Grundlage ist klein, aber brauchbar:

- `notifications` speichert Empfänger, Text, Lesestatus und Zeit.
- Tradeanfrage, Annahme, Fehlschlag und Abschluss erzeugen Einträge.
- `mark_notification_read()` kann den Lesestatus setzen.

Die Notifications sind in der aktuellen UI jedoch faktisch nicht erreichbar:

- `unread_notifications()` wird importiert, aber nicht verwendet.
- Der Header besitzt weder Glocke noch Badge.
- Es gibt keine Benachrichtigungsliste.
- Notifications besitzen kein `type`, `target_type`, `target_id` oder Deep-Link-Ziel.
- Der Helfer `trade_request_popup_html()` wird definiert, aber nicht in eine Seite eingebaut.

Home sollte daher nicht zuerst als statische neue Oberfläche gebaut werden. Zuerst müssen adressierbare offene Aufgaben aus Trade- und Freundschaftszuständen ableitbar sein.

### F. Navigation & Information Architecture

Die aktuelle Bottom-Navigation besteht aus fünf Punkten:

`Profil | Favorit | sammlr | Tauschen | Statistik`

Die Umstellung auf:

`Sammlung | sammlr./Home | Tauschen`

ist teilweise ein UI-/Routing-Umbau, aber nicht ausschließlich:

- `/` muss von Sammlung zu Home wechseln.
- Die bestehende Sammlung braucht eine stabile eigene Route.
- Profil und Notifications benötigen globale Headerzugänge.
- Favorit und Statistik bleiben als bestehende Seiten erhalten, werden aber hierarchisch umgeordnet.
- Album- und globale Tradeansichten sollten dieselben Fachservices verwenden.

Viele Zielseiten existieren bereits, sodass kein Neuschreiben der Seiten erforderlich ist. Deep Links zu konkreten Trades funktionieren über `/trades/<id>`. Der Rückweg ist heute jedoch fest auf die Tauschbörse codiert und kennt den Ursprung Home/Notification nicht.

## D. Architektur- und Legacy-Risiken

### 1. Monolithische Hauptdatei — hoch

`App/webapp.py` umfasst 7.561 Zeilen und enthält:

- Datenbankschema und Ad-hoc-ALTERs,
- SQL-Zugriff,
- Geschäftslogik,
- HTML-Templates als Strings,
- große JavaScript-Blöcke,
- SVG-Erzeugung,
- Navigation und Seitenrouting.

`albumseite()` allein umfasst ungefähr 1.330 Zeilen, `trade_center()` rund 627. Eine Änderung an Bestandslogik kann dadurch Wall, Trophy, Suche, Tradeauswahl und UI gleichzeitig berühren.

Empfehlung für spätere Arbeitspakete: kontrollierte Extraktion entlang fachlicher Grenzen, kein Big-Bang-Rewrite.

### 2. Unzureichendes relationales Modell — hoch

Es existieren keine Foreign Keys für Nutzer-, Album-, Sticker- oder Tradebeziehungen. `stickers` besitzt keinen Unique-Constraint auf `user_id + album_id + sticker_code`; die aktuelle Eindeutigkeit wird nur durch Codekonvention gehalten. Mengen besitzen keine Datenbank-Checks.

Das Schema kann Albumexemplare, Reservierungen, Sendungen, Empfang, Chat, Bewertungen, Freundschaften oder Privacy nicht ausdrücken.

### 3. Tradeintegrität ohne Reservierung — sehr hoch

Angenommene Deals blockieren Bestand nicht. Mehrere offene oder angenommene Pakete können dieselben physischen Sticker verwenden. Manuelle Mengenänderungen beachten Trades ebenfalls nicht.

Das bedroht genau den bereits funktionierenden Abschlussflow und sollte vor Smart-Trader-Ausbau fachlich abgesichert werden.

### 4. Duplizierte Bestandsmutationen — hoch

Bestand wird unter anderem verändert in:

- Album-POST-Transfer,
- Batch Add/Remove,
- Stickerdetail,
- Inline-Mengenroute,
- Add/Remove-Routen,
- Undo,
- Papierlistentransfer,
- Tradeabschluss.

Fast jeder Pfad berechnet `quantity` und `duplicates` erneut. `change_sticker_quantity()` ist ein guter Konsolidierungskern, wird aber noch nicht überall verwendet.

### 5. Flacher Tradezustand und JSON-Pakete — hoch

JSON-Arrays erlauben Mengen, aber keine stabile Positions-ID, keinen Einzelstatus, kein Teilempfang und keine albumübergreifende Position. Statusübergänge sind über Routen verteilt und nicht zentral validiert.

### 6. Fehlende Regressionstests — sehr hoch

Im Repository wurde keine Testsuite gefunden. Gerade weil ein realer Trade erfolgreich war, muss dessen Verhalten vor strukturellen Änderungen reproduzierbar abgesichert werden.

### 7. Startup-Migrationen und Debugrouten — mittel bis hoch

`init_db()` führt bei jedem Import Tabellenanlage und `ALTER TABLE` mit verschluckten `OperationalError`s aus. Zusätzlich existieren öffentlich zugelassene Debugrouten; `/debug-seed-now` kann mit einem hart codierten Query-Key eine Datenbankkopie auslösen.

Das ist für frühe Entwicklung verständlich, aber für kontrollierte Evolution und öffentliche Skalierung riskant.

### 8. Authentifizierung und schreibende GET-Routen — hoch vor öffentlichem Betrieb

Passwörter werden im Klartext gespeichert und verglichen; der Flask-Secret-Key ist fest im Code. Mehrere Zustandsänderungen sind per GET erreichbar, unter anderem Add/Remove, Favorit und Notification-Read. CSRF-Schutz ist nicht erkennbar.

Dies ist nicht der Kern der Product-Bible-Gap-Analyse, aber eine zwingende technische Voraussetzung vor öffentlicher Skalierung.

### 9. CSS- und UI-Layer mit historischen Überschreibungen — mittel

`App/static/style.css` umfasst 8.946 Zeilen und definiert zentrale Selektoren wie `.bottom-nav`, `.profile-*` und `.trade-*` in mehreren späteren Blöcken erneut. Das erschwert sichere Navigationseingriffe und kann responsive Regressionen verursachen.

### 10. Mehrere historische Appkopien und unklarer Einstieg — mittel

Neben `App/webapp.py` liegen mehrere Backup-, Rescue- und Broken-Dateien; die Root-`app.py` ist leer. Eine explizite Deployment-Konfiguration wurde nicht gefunden. Diese Dateien wurden nicht gelöscht, können aber Analyse und Betrieb verwirren.

## E. Bestehende Teile, die geschützt und wiederverwendet werden sollten

1. **Stickerwall und Albumstruktur**  
   Kapitel, Teams, Filter, Suche, direkte Mengenpflege und Fortschrittsupdate funktionieren als zusammenhängender Nutzerworkflow.

2. **Papier-Stickerliste**  
   Der schnelle Börsenworkflow bildet reale Sammelpraxis und Mehrfachdoppelte bereits gut ab.

3. **Codeauflösung und Albumdaten**  
   `resolve_code()`, `all_codes()` sowie EM24-/WM26-/VfL-Strukturen sind wertvolle Domänenbasis.

4. **Manuelle Dealzusammenstellung**  
   UI und serverseitige Regeln für konkrete Sticker und Mengen sind eine belastbare Grundlage des manuellen Tauschbereichs.

5. **Beidseitig bestätigter Tradeabschluss**  
   Die atomare Buchung beider Seiten ist real erprobt. Semantik und Zustandsmodell müssen erweitert, das nachgewiesene Verhalten aber konserviert werden.

6. **Trophy-Definitionen und Unlock-Historie**  
   Album- und globale Trophäen sind datengetrieben definiert; `unlocked_trophies` bewahrt Zeitpunkte.

7. **Statistik- und Profil-Unterseiten**  
   Sie müssen navigativ und fachlich erweitert, nicht vollständig neu gebaut werden.

8. **Notification-Erzeugung**  
   Der kleine Service ist als Schreibadapter wiederverwendbar, benötigt aber typisierte Ereignisse und Zielobjekte.

## F. Technische Abhängigkeiten / Dependency Map

```text
Albuminstanz- und Bestandsmodell
├── explizite Albumzuordnung / freier Pool
├── aktive und deaktivierte Alben
├── Mehrfachbedarf (später)
└── zentrale verfügbare Menge
    ├── Reservierungen
    │   ├── sichere Annahme
    │   ├── konfliktfreie Smart Matches
    │   └── geschützte manuelle Mengenänderung
    └── Trade-State-Machine
        ├── Versand pro Seite
        ├── unterwegs
        ├── Empfang pro Seite / Teilempfang
        ├── Bestandsbuchung
        ├── Historie / Bewertung
        └── adressierbare Trade-Events
            ├── Notifications / Glocke
            └── Home-Handlungsbedarf
```

```text
Profilbasis und Privacy
├── fremde Profile
├── Album-Sichtbarkeit
├── Bewertungen / Zuverlässigkeit
└── Freunde / Blockieren
    ├── Freundschaftsanfragen
    ├── Freundesaktivitäten
    └── Home-Freundesbereich
```

```text
Route für Sammlung + Route für Home
├── 3er-Bottom-Navigation
├── globaler Header mit Avatar/Glocke
├── kontextbewusste Deep Links
└── hierarchische Einordnung bestehender Statistik-/Trophy-/Favorit-Seiten
```

Wichtigste Reihenfolgenabhängigkeit: Ein neuer Smart-Trade-Screen sollte nicht verbindliche Pakete erzeugen, bevor verfügbare Mengen und Reservierungen zentral konsistent sind.

## G. Kandidaten für spätere Arbeitspakete

Die folgenden Gruppen sind keine priorisierte Sprint-Roadmap.

### Kandidat 1: Regression-Schutz für den Ist-Kern

- Datenbankfixture ohne personenbezogene Produktivdaten,
- Tests für Mengenänderung, Doppelte, Papierlistentransfer,
- Tests für Anfrage, Annahme, beide Bestätigungen und Bestandsbuchung,
- Tests für Trophy- und Notification-Nebenwirkungen.

### Kandidat 2: Fachliche Servicegrenzen

- zentraler Inventory-Service,
- zentraler Trade-Application-Service,
- read-only Matching-Service,
- HTML/JS schrittweise aus dem Monolithen lösen.

### Kandidat 3: Bestands- und Reservierungsentwurf

- Sollbegriffe und Invarianten formalisieren,
- bestehende Einzelexemplar-Daten abbilden,
- reserviert/frei/unterwegs ohne sofortige Mehrfachalbum-UI ermöglichen,
- erst danach Migrationsentwurf.

### Kandidat 4: Trade Lifecycle

- explizite Übergänge und Zeitstempel,
- Versand und Empfang pro Seite,
- Problemzustände,
- Ereignisprotokoll,
- bestehende Abschlussbuchung kontrolliert integrieren.

### Kandidat 5: Smart Trader 2.0 – fachliche Engine

- zentraler Verfügbarkeits-Snapshot,
- Markt- und persönliche Tauschabdeckung,
- konfliktfreie Paketoptimierung,
- Anfrageablauf und parallele Limits,
- transparente Paketänderungen.

### Kandidat 6: Home und Notifications

- typisierte Notifications mit Zielobjekt,
- Glocke und Historie,
- offene Aufgaben getrennt von gelesen/ungelesen,
- kompakte Tradezusammenfassung,
- danach Freundes- und Sammlr-News.

### Kandidat 7: Profil und Community

- fremdes Profil und Privacy,
- Bewertung nach qualifiziertem Lifecycle,
- Freundschaften und Blockieren,
- Aktivitätsstatus,
- Tauschpotenzial als Wiederverwendung des Matching-Service.

### Kandidat 8: Navigation

- stabile getrennte Routen für Sammlung und Home,
- bestehende Seiten hierarchisch umordnen,
- 3er-Bottom-Navigation,
- Avatar/Glocke im Header,
- Navigationkontext für Deep Links.

### Kandidat 9: Betriebs- und Sicherheitsgrundlagen

- Passwort-Hashing und Secrets,
- CSRF und HTTP-Methoden,
- Debugrouten absichern/entfernen,
- versionierte Migrationen,
- klarer Deployment-Einstieg.

## H. Bewusst nicht kurzfristig relevante Zukunftsthemen

Folgende Product-Bible-Themen sind in dieser Analyse nicht als kurzfristige Gaps priorisiert:

- Mehrfachalbum-UI und Advanced-Collector-Poolmanagement,
- komplette Albumübertragung,
- KI-/Foto-Scanner,
- Offline-Synchronisation,
- QR-Börsenmodus,
- regionale Suche und lokale Events,
- Marketplace und Shop,
- Versandversicherung und Versandlabels,
- anonymisierter Versand,
- Premium,
- globale objektübergreifende Suche,
- komplexe Mehrparteien-Trades.

Architektonisch sollten Albuminstanzen, Tradepositionen und Ereignisse diese Optionen nicht unnötig verhindern. Ihre vollständige Implementierung ist aber keine Voraussetzung für die nächste kontrollierte Verbesserung des heutigen Kernflows.

## I. Gelesene Dokumente und untersuchte Komponenten

### Product Bible

- `Dokumentation/Product Bible/README.md`
- `specifications/collection.md`
- `specifications/trading.md`
- `specifications/trade-lifecycle.md`
- `specifications/profile-community.md`
- `specifications/home.md`
- `specifications/navigation-information-architecture.md`
- `roadmap/README.md`
- `decisions/README.md`

### Ergänzende Produkt-/Designunterlagen

- `Branding/Corporate ID/Sammlr_Corporate_ID_V1.md`
- relevante README- und Design-Bible-Dokumente zu Masterassets und Trophäen

### Anwendung

- `App/webapp.py`
- `App/services/albums.py`
- `App/services/notifications.py`
- `App/services/trophy_service.py`
- `App/trophy_definitions.py`
- `App/em24_data.py`
- `App/wm26_data.py`
- `App/Database/database.py`
- SQLite-Schema und anonymisierte Struktur-/Statusabfragen in `App/Database/sammlr.db`
- `App/static/style.css` hinsichtlich Navigation und Seitenstruktur
- vorhandene aktive und historische Python-Einstiegspunkte

## J. Schlussfolgerung

Sammlr sollte kontrolliert weiterentwickelt werden. Der funktionierende Kern rechtfertigt keinen kompletten Neustart. Die wichtigste Aufgabe vor größeren sichtbaren Erweiterungen ist, die bereits funktionierenden Abläufe durch Tests zu schützen und die fachlichen Zustände für Bestand, Reservierung und Dealabwicklung explizit zu machen.

Danach können Smart Trader, Home, Notifications und Community auf einer gemeinsamen verlässlichen Grundlage wachsen, ohne den ersten real bewährten Sammlr-Tradeflow zu verlieren.
