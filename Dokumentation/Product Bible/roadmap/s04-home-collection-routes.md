# S04 – Home- und Sammlungsrouten trennen

| Feld | Wert |
| --- | --- |
| Status | abgeschlossen |
| Stand | 2026-07-29 |
| Verbindliche Grundlage | [Development Roadmap V1, Sprint S04](development-roadmap-v1.md#s04--home--und-sammlungsrouten-trennen) |
| Product Bible | [Home](../specifications/home.md), [Sammlung](../specifications/collection.md), [Navigation & IA](../specifications/navigation-information-architecture.md) |
| Datenbankschema | unverändert |
| Sichtbare spätere Features | keine |

## Begriffsklärung

**Home** und **Sammlr-Zentrale** sind zwei unterschiedliche fachliche
Bereiche:

- Home ist der reguläre Startpunkt und spätere Ort für aktuelle Ereignisse
  und Handlungsbedarf.
- Die Sammlr-Zentrale ist der Einstieg in die eigene Sammlung und besitzt
  Albumkarten, Lieblingsalbum, aktive Alben, Album hinzufügen und Vitrine.

Der bestehende Begriff **Sammlr-Zentrale** bleibt erhalten. Eine spätere
Umbenennung wurde in S04 nicht eigenständig entschieden.

## Routenkarte

| Route | Rolle | Verhalten |
| --- | --- | --- |
| `/` | kanonisches Home | ehrlicher Grundzustand ohne erfundene Aufgaben, Trades, Feed- oder Newsdaten |
| `/home` | Home-Kompatibilität | Redirect auf `/` |
| `/sammlung` | kanonische Sammlung | bestehende Sammlr-Zentrale vollständig |
| `/zentrale` | Sammlungs-Kompatibilität | Redirect auf `/sammlung` |
| `/sammlr-zentrale` | Sammlungs-Kompatibilität | Redirect auf `/sammlung` |

Alle Routen unterliegen weiterhin der bestehenden Loginpflicht.

## Home-Grundzustand

Home enthält in S04 ausschließlich:

- eine eindeutige Home-Überschrift,
- einen neutralen Willkommenszustand,
- einen direkten Link zur Sammlr-Zentrale,
- die unveränderte bestehende Navigation.

Home behauptet keine offenen oder abgeschlossenen Lifecycle-Zustände. Es
zeigt keine Albumkarten, keine Vitrine, keine Tradezusammenfassung und keinen
künstlichen Feed.

## Geschützte Sammlung

Die bisherige Zentrale wurde ohne Änderung ihrer Bestandsberechnungen unter
`/sammlung` verschoben. Geschützt und per Regressionstest nachgewiesen sind:

- aktive Albumkarten,
- Favoritenkennzeichnung und Favoritenreihenfolge,
- Fortschritt, Doppelte und verfügbare Lücken,
- Vitrine auf Basis real berechneter Vollständigkeit,
- Einstieg „Album hinzufügen“,
- Einstieg in einzelne Alben.

## Interne Links und Rückwege

Collection-spezifische Rückwege zeigen nun auf `/sammlung`:

- Home → Sammlr-Zentrale,
- Profil → „Meine Alben“,
- Album → „Zur Sammlung“,
- Album-hinzufügen → zurück zur Sammlung,
- erfolgreicher Albumzugang → Sammlung,
- leerer Undo-Fallback → Sammlung,
- Favoriten-Leerzustand → Sammlung.

Markenlogos, erfolgreicher Login, `/home` und Notification-Rückkehr führen
weiterhin zum kanonischen Home `/`.

## Akzeptanzkriterien

| Kriterium | Nachweis |
| --- | --- |
| Sammlung vollständig erreichbar | `/sammlung` liefert Albumkarten, Favorit, Album hinzufügen und Vitrinenlogik |
| `/` ist Home | eigene Home-Überschrift und direkter Sammlungseinstieg |
| keine erfundenen Lifecycle-Daten | Home enthält keine Anfrage-, Versand-, Feed-, News- oder Albumzustände |
| alte Kernwege funktionieren | Collection-Rückwege und drei Kompatibilitätsredirects sind getestet |
| Login bleibt stabil | erfolgreicher Login landet auf `/`; anonyme Home-/Sammlungsrouten landen auf `/login` |
| bestehende Kernlogik bleibt stabil | vollständiges Testgate S01–S04 ist grün |

## S04-Testbefehl

Nur S04:

```sh
python3 -m unittest discover -s tests -p 'test_s04_*.py' -v
```

Vollständiges Gate:

```sh
python3 -m unittest discover -s tests -p 'test_s0*.py' -v
```

S04 ergänzt 10 Routentests. Das vollständige Gate umfasst nach S04 insgesamt
53 Tests.

## Bewusst nicht umgesetzt

- echte Home-Aufgaben oder Notification-Karten,
- Feed, Freundesaktivitäten oder Sammlr News,
- laufende Trade- oder Versandzusammenfassungen auf Home,
- Glocken-UI,
- dreiteilige Bottom-Navigation aus S05,
- Änderungen an Favoriten-, Profil- oder Statistiknavigation,
- Navigation-, Design-, CSS- oder JavaScript-Umbauten,
- Datenbankschema oder Migrationen.

## Offene Punkte für spätere Sprints

- Die bestehende Bottom-Navigation bildet noch nicht die in der Product Bible
  beschlossene Dreiteilung ab. Das ist explizit S05.
- Home besitzt absichtlich noch keine operativen Aufgaben- oder
  Ereigniskarten.
- Notification-Rückkehr führt bereits zu Home; eine Notification-Historie
  oder Glocke ist nicht Teil von S04.
- Die langfristige Umbenennung oder Aufgabe des Begriffs
  „Sammlr-Zentrale“ bleibt eine bewusste Produktentscheidung.

## Abschluss

S04 trennt die fachlichen Besitzer stabil, ohne spätere Home- oder
Navigationsfunktionen vorzuziehen. Datenbankschema, Bestandslogik, Tradeflow,
Templates, CSS und JavaScript bleiben unverändert.

