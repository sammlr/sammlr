# S07 – Deep-Link- und Rückwegkontext

Stand: 2026-07-31

Dieses Dokument beschreibt ausschließlich die in Sprint S07 eingeführte kleine
Deep-Link-Konvention für die bestehende Dealansicht. Die Development Roadmap V1
und die Product Bible bleiben die fachlich verbindlichen Quellen.

## URL-Konvention

Die bestehenden direkten Dealrouten bleiben erhalten:

```text
/trades/<id>
/trade/<id>
```

Optional darf ein fester Origin-Wert ergänzt werden:

```text
/trades/<id>?origin=<erlaubter-origin>
```

Es wird keine frei übergebene Return-URL unterstützt.

## Erlaubte Origin-Kontexte

| Origin | Belegter Ursprung | Sicher erzeugter Rückweg |
| --- | --- | --- |
| `home` | Home | `/` |
| `trades` | globale Tradezentrale / Meine Deals | `/trades?tab=<deal-tab>` |
| `album_trades` | bestehende albumbezogene Tauschansicht | `/album/<trade-album>/trades?tab=<deal-tab>` |

`album_trades` ist notwendig, weil bereits vor S07 konkrete Deal-Links in der
albumbezogenen Tauschansicht existierten. Es wurden keine zukünftigen oder
erfundenen Kontexte ergänzt.

Der Deal-Tab wird nicht aus der Anfrage gelesen. Er wird aus dem bestehenden
Tradezustand abgeleitet:

- `accepted` führt zu `agreements`.
- Alle anderen bereits darstellbaren Zustände führen zu `requests`.

Auch die Album-ID stammt ausschließlich aus dem berechtigt geladenen Trade.

## Sicherer Fallback

Fehlt `origin` oder entspricht der Wert nicht exakt der Allowlist, verwendet die
Dealansicht den fachlichen Standardrückweg zur globalen Tradezentrale:

```text
/trades?tab=<deal-tab>
```

Damit bleiben direkte bestehende URLs ohne Origin unverändert funktionsfähig.
Ungültige Werte erzeugen weder Fehler noch tote Seiten oder externe
Weiterleitungen.

## Sicherheitsregeln

1. Die Dealroute lädt das Objekt weiterhin mit der bestehenden Prüfung auf
   `from_user_id` beziehungsweise `to_user_id`.
2. Erst nach erfolgreicher Objektberechtigung wird der optionale Origin
   ausgewertet.
3. Nur exakte Werte aus `TRADE_DETAIL_ORIGINS` werden akzeptiert.
4. Absolute URLs, fremde Domains, protokoll-relative URLs,
   `javascript:`-Ziele und beliebige interne Pfade sind keine erlaubten Werte
   und fallen auf die Tradezentrale zurück.
5. Es wird kein Requestwert als `href` oder Redirectziel ausgegeben.
6. Eine unbekannte Trade-ID und ein fremder Trade verwenden weiterhin die
   bestehende sichere Nicht-gefunden-Behandlung.

## Bestehende kontextuelle Links

- Deal-Links aus der globalen Tradezentrale setzen `origin=trades`.
- Deal-Links aus der albumbezogenen Tauschansicht setzen
  `origin=album_trades`.
- Home besitzt in S07 weiterhin keine erfundenen Dealkarten. Ein bereits
  bekannter Deal kann sicher mit `origin=home` geöffnet werden.

Es wurden keine neuen Fachansichten oder Album-Deep-Links ergänzt, weil sie für
den nachweisbaren S07-Kontext nicht erforderlich sind.

## Tests

Nur S07:

```sh
python3 -m unittest discover -s tests -p 'test_s07_*.py' -v
```

Vollständiges Gate:

```sh
python3 -m unittest discover -s tests -p 'test_s0*.py' -v
```

Geprüft werden alle erlaubten Kontexte, direkte URLs ohne Origin, beide
bestehenden Dealrouten, sicherer Fallback, externe und manipulierte Werte,
vorhandene Linkquellen, Objektberechtigungen, unbekannte IDs,
Nebenwirkungsfreiheit sowie der Schutz von Produktivdatenbank und S00-Fixture.

## Bewusst nicht enthalten

- neue Notification-Typen oder Zielobjekte,
- Notification-Badge oder Historie,
- neue Home-Aufgaben,
- neue Dealzustände oder Fachlogik,
- neue Datenbankfelder,
- universelle Return-URL- oder Redirect-Engine,
- Routingframework oder Design Patch.
