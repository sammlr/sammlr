# CB-006 – Implementierungsreport

**Stand:** 2026-08-18

**Branch:** `feature/wm-special-trophies`

**Empfehlung:** CB-006 ABGENOMMEN

1. **Ziel:** Die globale Profilprivacy ist als äußeres, serverseitiges Gate vor
   jede fremde Sammlerwelt geschaltet. Darunter bleibt S27-Albumprivacy die
   innere Sichtbarkeitsstufe; Tradepool und operative Tradefreigabe bleiben ein
   unabhängiger Vertrag.

2. **Ausgangszustand:** Fremde Profile wurden über
   `CollectorProfileService` einschließlich Album-, Bestands-, Rating-, Trade-
   und Trophywerten projiziert. Einzelne Alben waren bereits durch
   `AlbumPrivacyService` geschützt, es gab jedoch kein globales
   `public/private`-Profilgate. Ein privater Gesamtzustand konnte deshalb weder
   zentral entschieden noch vor den sensiblen Reads durchgesetzt werden.

3. **Geänderte Dateien:** Neu sind
   `App/services/profile_privacy.py`, die V0017-Up-/Down-Migration und
   `tests/test_cb006_profile_privacy_gate.py`. Angepasst wurden
   `App/services/album_privacy.py`, `collector_profiles.py`,
   `user_data_export.py`, `runtime_operations.py`, `App/webapp.py`, die
   Latest-Schema-Fixtures der betroffenen S26–S38-/Post-RC-Tests, die
   Performance-Baseline und S34-Deployment-/Recovery-Dokumente. Zusätzlich
   wurden dieser Report und der Closed-Beta-Bauplan fortgeschrieben. Feed,
   Notifications, Statistikprojektion und Trade-Lifecycle wurden nicht
   umgebaut.

4. **Migration:** JA. V0017 erweitert ausschließlich `users`; keine bestehende
   Albumprivacy-, Tradepool-, Bestands- oder Historienzeile wird umgeschrieben.
   Die Runtime-Zielversion ist 17. Das Down-Skript verweigert den Rückbau
   fail-closed, sobald ein Nutzer bereits einen von `public` abweichenden Wert
   besitzt.

5. **Finales Profilprivacy-Schema:** `users.profile_privacy TEXT NOT NULL
   DEFAULT 'public' CHECK (profile_privacy IN ('public', 'private'))`. Andere
   Werte sind weder im Schema noch im Update-Service zulässig.

6. **Default bestehende Nutzer:** `public`. SQLite befüllt beim additiven
   `ALTER TABLE` alle vorhandenen Zeilen mit dem festgelegten Default. Der
   realistische Migrations-Smoke bestätigte vier von vier vorhandene Nutzer als
   `public`.

7. **Default neue Nutzer:** `public`. Inserts ohne explizite
   `profile_privacy` übernehmen den Datenbankdefault; dies ist in der gezielten
   Suite ausdrücklich geprüft.

8. **Zentrale Privacy-Grenze:** `ProfilePrivacyService.decision(...)` liefert
   eine unveränderliche Entscheidung mit Owner-, Mutual-Friend-, Block-,
   Privacy- und Freigabestatus. `CollectorProfileService` prüft diese Grenze vor
   jedem sensiblen Projektionsread. `AlbumPrivacyService` wendet sie für
   Einzel- und Listenentscheidungen vor der Albumstufe an. Die Routen
   duplizieren die Fachregel nicht.

9. **Owner-Verhalten:** Ein aktiver Owner darf das eigene Profil sowohl bei
   `public` als auch bei `private` vollständig sehen. Das äußere Gate blockiert
   die Eigenansicht nie; die bestehende Eigenalbumlogik bleibt erhalten.

10. **Nicht-Freund-Verhalten:** Bei `public` ist die Sammlerwelt grundsätzlich
    offen und wird anschließend nach Albumprivacy gefiltert. Bei `private`
    entsteht nur eine minimale Identitäts-/Communityansicht mit Username,
    notwendigem Beziehungsstatus und zulässiger Aktion; Name, Kennzahlen,
    Alben, Bestand, Trophäen, Abschlüsse, Ratings, Tradeaggregate und
    Tradepotential werden nicht projiziert.

11. **Gegenseitige Freunde:** Nur eine bestehende bestätigte Friendship öffnet
    ein privates Profil. Offene Requests und einseitige beziehungsweise
    inkonsistente Zustände reichen nicht. Nach erfolgreichem Profilgate bleiben
    `public`- und `friends`-Alben sichtbar, `private`-Alben verborgen.

12. **Blockierungsverhalten:** Ein Block in beliebiger Richtung hat Vorrang vor
    `public`, `private` und Freundschaft. Er kann weder über Profil- noch über
    Album-Deep-Links umgangen werden. Die minimal notwendige Blockstatus-/
    Unblockdarstellung bleibt erhalten, ohne Sammlerdaten zu laden.

13. **Zusammenspiel Profilprivacy/Albumprivacy:** Die ausgewertete Reihenfolge
    ist verbindlich `Profilgate → Albumprivacy`. Ein offenes Profil macht ein
    `friends`- oder `private`-Album nicht öffentlich. Ein geschlossenes Profil
    sperrt für Nicht-Freunde auch ein an sich öffentliches Album. Die Werte
    `public/friends/private` in `user_albums.visibility` wurden nicht geändert.

14. **Tradepool-Unabhängigkeit:** Profilprivacy-Updates verändern
    `trade_pool_enabled` nicht. `is_trade_pool_enabled`,
    `trade_pool_user_ids`, Matchbarkeit, Reservierungen, Requests und laufende
    Trades konsultieren das Profilgate nicht. Lediglich die Profilseite selbst
    zeigt einem nicht berechtigten Betrachter kein Tradepotential, weil dieses
    Sammlerbestände offenlegen würde.

15. **Deep-Link-Schutz:** Direkte fremde Albumrouten, Stickerlisten und
    Preview-/Albumreads verwenden `AlbumPrivacyService.can_view(...)` und damit
    zuerst die zentrale Profilentscheidung. Ein bekannter Username, eine
    Album-ID oder ein direkter URL-Aufruf liefert keine Umgehung; verborgene
    Alben antworten weiter mit 404 statt Daten.

16. **Fail-closed-Fälle:** Unbekannter oder korrupter Privacywert, nicht
    vorhandener/deaktivierter Owner, nicht konvertierbare Nutzer-ID, ungültige
    Albumzuordnung, fehlende bestätigte Beziehung und Blockierung führen für
    fremde Zugriffe zu keiner Sammlerprojektion. Ungültige Updates werden mit
    400 abgelehnt; fremde Updates sind service-seitig unautorisiert.

17. **Gezielte Tests:** `tests.test_cb006_profile_privacy_gate` ist mit 10/10
    Tests grün. Die Tests bilden A–Z ab: V0017/Defaults/Constraints/Repeat-up/
    Safe-down, Owner, public/private, Mutual Friend, Pending/inkonsistent,
    Blocks, vollständige Profil-/Albummatrix J–R, Deep Links, Leaks,
    Settings-Isolation, Tradepool und fail-closed. Ein SQL-Trace beweist
    zusätzlich, dass ein abgelehntes Profil vor Reads aus `user_albums`,
    Beständen, Trades, Ratings, Trophäen und Historie stoppt und keine Writes
    ausführt.

18. **Relevante Privacy-/Securitytests:** Die kombinierte Verbraucher-Suite aus
    CB-006, S26, S27, S29, S35, S32, S33, S34, S36, S21 und S22 lief mit
    129/129 Tests in 3,489 s, `OK`, 0 Fehler und 0 Skips. Damit sind Profil,
    Albumprivacy, Friendship/Block, Account, Auth/CSRF, HTTP-Integrität,
    Deployment, Export und Tradepool/Matching gemeinsam geprüft.

19. **Regression Lauf 1:** Korrekt konfigurierte vollständige Discovery mit
    explizitem Testing-Environment: 628 Tests in 7,954 s, `OK`, 0 Fehler,
    0 Skips. Ein vorheriger Diagnoseaufruf mit einem aus der Shell geerbten
    falschen Secret scheiterte erwartungsgemäß am S32/S35-Environment-Gate und
    zählt nicht als Regression.

20. **Regression Lauf 2:** Identische frische Discovery: 628 Tests in 7,560 s,
    `OK`, 0 Fehler, 0 Skips.

21. **Integrity/FK:** Die realistische isolierte Kopie wurde von V7 über
    `(8, 9, 10, 11, 12, 13, 14, 15, 16, 17)` migriert; Repeat-up ergab `()`.
    `PRAGMA integrity_check` lieferte `ok`, `PRAGMA foreign_key_check` null
    Treffer. Dieselben Checks waren auch nach den ausschließlich auf der Kopie
    ausgeführten Privacy-/Friendship-Smokes sauber.

22. **Startup-Smoke:** Frischer Appstart gegen die isolierte V17-Kopie war
    erfolgreich. `/healthz` antwortete 200 mit `{"status":"ok"}`, `/login`
    mit 200. Authentifizierte Profil- und Albumrequests verwendeten den neuen
    Vertrag.

23. **Realistischer Daten-Smoke:** S34-Backup-API erzeugte die isolierte Datei
    `/private/tmp/sammlr-cb006-audit.DZ1gyR/sammlr-20260818-201552-v0007.db`.
    Vor/nach Migration blieben 4 Nutzer und alle 8 `user_albums` samt
    Visibility-/Tradepoolwerten gleich. Owner 1 war zunächst public: Nichtfreund
    2 sah das Profil und das öffentliche VfL-Album, nicht das private EM24-Album.
    Nach Umschalten nur der Kopie auf private sah er die minimale Profilansicht,
    keine Kennzahlen/Trophäen und kein VfL-Album. Nach bestätigter Friendship
    waren Profil und VfL sichtbar, EM24 blieb 404. Tradepoolwerte blieben in
    allen Phasen identisch.

24. **Echte lokale DB verändert:** NEIN durch CB-006. Sie wurde weder migriert
    noch für Tests oder Smoke beschrieben. Ihr vor und nach CB-006 gemessener
    SHA-256 ist
    `89254d1fe02980a0ccbf85437611273ea094568a064c75ed281f9ca6a23978a0`.
    Die bereits vor diesem Paket im Working Tree vorhandene Git-Abweichung der
    Datei wurde nicht angefasst.

25. **Bekannte Grenzen:** Die freigegebene Ansicht konsumiert weiterhin die
    bestehenden S26-/Legacy-Profilzahlen. Deren fachliche Umstellung auf
    kanonische Abschluss-, Trophy- und Tradeprojektionen gehört zu CB-014.
    Historische Schematests vor V0017 behalten bewusst ihr damaliges
    S27-Verhalten; der produktive Runtime-Start verlangt V17.

26. **Technische Restpunkte:** Profil und Account bleiben visuell teilweise in
    der bestehenden Architektur verbunden; CB-006 ergänzt dort nur die kleine
    Sichtbarkeitseinstellung. Neue API-/Feed-Verbraucher müssen die zentrale
    Policy verwenden. Feedstore, Notification-Umbau, Inbox, Home, Statistik und
    neue Profilprojektion bleiben in ihren vorgesehenen Paketen.

27. **Abweichungen vom Bauplan:** Keine fachliche Abweichung. Die additive
    eigene V0017-Spalte und der sichere Rückbauguard konkretisieren lediglich
    den geforderten Cutover. Keine zusätzliche Section-Privacy, Followerlogik,
    Social-Funktion oder Tradekopplung wurde eingeführt.

28. **Product-Contract-Verletzungen:** NEIN. PO-01 Variante A, public-Default,
    gegenseitige Freundschaft, Blockvorrang, innere Albumprivacy und unabhängiger
    Tradepool sind unverändert umgesetzt.

29. **Empfehlung:** **CB-006 ABGENOMMEN.** Die Privacygrenze ist zentral,
    serverseitig, fail-closed, Deep-Link-sicher und auf realistischer Kopie
    sowie in zwei vollständigen Regressionen nachgewiesen.

30. **Kann CB-007 begonnen werden?** **JA.** CB-007 kann die zentrale
    Profilentscheidung als äußere Lesebedingung verwenden. Es wurde nicht
    begonnen.

## Recovery und Datenbestand

Der Backup-Artefakt-Hash vor Migration war
`f59349c6846fe8d5db4b103c2500ce5f0142cbac74e234eb3d4a204ee7f550a4`.
Nach den ausdrücklich nur auf der Kopie ausgeführten V17-/Privacy-/Friendship-
Smokes lautete deren Hash
`af75ce8680c0b3b0ebcaa078a7974128aea8caddbae4d5b1c0dac827469349c1`;
diese veränderte Auditkopie ist kein Produktions- oder lokaler
Arbeitsdatenbestand. `git diff --check` und Python-Kompilation sind sauber. Es
wurde kein Commit erstellt und nichts gepusht.
