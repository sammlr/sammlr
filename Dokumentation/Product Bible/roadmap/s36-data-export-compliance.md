# S36 – Datenexport und Compliance-Grundlagen

Stand: 2026-08-09

## Geltungsrang und Scope

Die verbindliche Product-Owner-Klärung vom 2026-08-09 definiert S36 für die
aktuelle Umsetzung ausschließlich als Datenexport, Datenschutz-/Compliance-
Grundlagen und Exportarchitektur. Sie ersetzt damit für diesen Sprint die
ältere S36-Kurzbeschreibung „Accessibility, responsive Sonderfälle und finale
CI-Politur“ in der Development Roadmap V1. Der ältere Roadmaptext wird nicht
stillschweigend fachlich verändert; die Abweichung bleibt hier nachvollziehbar.

Nicht enthalten sind Accessibility-/UI-Politur, Performanceoptimierung,
Communityfunktionen, Backup, Retentionänderungen, automatische Löschung,
Änderungen der S35-Anonymisierung sowie S37 oder S38.

## Ziel

Ein angemeldeter aktiver Nutzer kann nach erneuter Passwortprüfung ein
einzelnes, menschenlesbar formatiertes UTF-8-JSON-Dokument mit seinen bei
Sammlr gespeicherten personenbezogenen und fachlichen Daten herunterladen.
Der Export ist synchron, read-only und erzeugt weder persistente Exportdatei
noch Hintergrundauftrag.

## Architektur

```text
angemeldeter Nutzer
  -> GET /profil/datenexport
     -> Passwortformular und Exporthinweise
  -> POST /profil/datenexport (CSRF + aktuelles Passwort)
     -> AuthSecurityService.password_matches
     -> UserDataExportService.export_for_user
        -> ausschließlich kanonische Tabellen lesen
        -> objektbezogene Nutzergrenze erzwingen
        -> deterministisch sortiertes DTO
     -> UTF-8 JSON als direkter Attachment-Response
```

`UserDataExportService` besitzt allein den Exportvertrag. Die Route trifft
keine fachlichen Entscheidungen und berechnet keine neue Inventory-, Trade-,
Privacy-, Community-, Notification- oder Ratingwahrheit. Es gibt keine
Datenbankmutation und keine Migration.

## Exportvertrag

Das Wurzeldokument enthält:

- `format_version`
- `subject_user_id`
- `profile`
- `account`
- `favorites`
- `albums`
- `inventory`
- `trades`
- `ratings`
- `notifications`
- `trophies`
- `community`
- `login_security`

### Eigene Daten und Referenzgrenze

Es werden ausschließlich Datensätze exportiert, die über eine dokumentierte
Eigentümer- oder Beteiligtenbeziehung zum angemeldeten Nutzer gehören:

- direkte Eigentümerschaft über `user_id`,
- eigene Album-, Sticker-, Trophy-, Notification- oder Aktivitätsdaten,
- Tradeanfragen und Lifecycle-Trades, an denen der Nutzer beteiligt ist,
- zu diesen Trades gehörende Positionen, Events, Reservierungen, Versand,
  Empfang, Problemhistorie und Bewertungen,
- Freundschafts-, Anfrage- und Blockbeziehungen mit eigener Beteiligung.

Andere Nutzer werden ausschließlich durch die bereits legitime numerische
Referenz innerhalb solcher Trade-/Communitybeziehungen abgebildet. Profile,
Klarname, Username, Sammlung oder andere unabhängige Daten der Gegenseite
werden nicht in den Export hineingezogen.

### Sicherheitsgrenze

Nicht exportiert werden:

- Passwort oder Passwort-Hash,
- Sessiondaten und CSRF-Token,
- Secret Keys,
- interne Observability-Daten,
- Daten fremder Nutzer außerhalb legitimer eigener Beziehungen.

`password_scheme` und `auth_version` bleiben ebenfalls interne
Authentifizierungssteuerung. Exportiert werden nur Accountzustand und
fachliche Accountidentität.

## Determinismus und Kodierung

- JSON wird mit `ensure_ascii=False`, Einrückung und UTF-8 erzeugt.
- Das Dokument enthält keinen flüchtigen Erstellungszeitpunkt.
- Objektfelder besitzen eine stabile Reihenfolge.
- Listen sind durch stabile fachliche Schlüssel und anschließend IDs
  sortiert.
- Leere Kategorien werden als leere Listen beziehungsweise klar strukturierte
  Leerobjekte ausgegeben, nicht weggelassen.

## Compliance-Seiten

S36 ergänzt funktionale, ausdrücklich noch nicht juristisch finalisierte
Seiten für:

- Datenschutzerklärung,
- Impressum,
- Exporthinweise.

Die öffentlichen Informationsseiten enthalten keinen ausführbaren
Exportlink. Der Exportzugang erscheint ausschließlich im authentifizierten
eigenen Profil. Die Texte ersetzen keine juristische Endprüfung.

## Unveränderte Komponenten

- S35 Accountzustände, Deaktivierung und Anonymisierung
- Retention und Löschregeln
- Inventory- und Availability-Logik
- Trade Lifecycle und Tradehistorie
- Ratings, Privacy, Community und Notifications
- S34 Backup-/Recoveryvertrag
- Datenbankschema V0012
- lokale Entwicklungsdatenbank und S00-Fixture
