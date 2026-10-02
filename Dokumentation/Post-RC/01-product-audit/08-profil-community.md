# Product Audit – Profil & Community

**Stand:** 15. August 2026
**Status:** Produktentscheidungen dokumentiert; keine UI-, Produktlogik- oder Datenmodelländerung
**Langfristige Produktspezifikation:** [Profil & Community](../../Product%20Bible/specifications/profile-community.md)

## 1. Zweck dieses Audits

Dieses Audit präzisiert die Produktrolle von Profil und Community nach dem Release Candidate. Es ersetzt weder die langfristige Product Bible noch die bereits umgesetzten Sprint-Spezifikationen S26–S29. Wo die neue Produktausrichtung mit diesen Ständen kollidiert, wird die Kollision ausdrücklich festgehalten und nicht stillschweigend aufgelöst.

Das Profil soll sich wie ein **digitales Sammlerzimmer** anfühlen: Es erzählt Identität, Vertrauen und Sammlerleben. Es ist kein zweites Statistik-Dashboard und keine zweite operative Sammlungsverwaltung.

## 2. Verbindliche Produktregel

> Das Profil ist der Ort für Sammleridentität, Vertrauen, Community-Beziehungen und die persönliche Sammlergeschichte. Operative Album- und Bestandsarbeit bleibt in der Sammlung; operative Trade-Abwicklung bleibt im Deal; Konto- und Sicherheitsfunktionen bleiben im Account beziehungsweise in den Einstellungen.

Diese Trennung gilt für alle weiteren Profilentscheidungen.

## 3. Zwei Rollen, ein gemeinsamer Profilkern

Es gibt kein separates Produkt für das eigene und ein fremdes Profil. Beide Ansichten beruhen auf demselben Kern und unterscheiden sich nur durch Berechtigungen, persönliche Daten und mögliche Aktionen.

### Eigenes Profil

Das eigene Profil dient der eigenen Sammleridentität, den Community-Beziehungen, der eigenen Sammlergeschichte, der Präsentation von Vitrine, abgeschlossenen Alben und Trophäen sowie dem Zugriff auf die vollständige persönliche Trade-Historie.

Bearbeitungs-, private und persönliche Verlaufsfunktionen sind nur hier verfügbar. Eine große operative Albumübersicht oder Bestandsbearbeitung gehört dagegen in die Sammlung.

### Fremdes Profil

Ein fremdes Profil dient der Identifikation einer anderen sammelnden Person, der Einschätzung von Vertrauen, dem sichtbaren Sammlerleben, der Einordnung der Freundschafts- und Trade-Beziehung sowie der Präsentation freigegebener Alben und Trophäen.

Das fremde Profil darf den Einstieg in Freundschaft oder einen möglichen Tausch unterstützen. Der Deal selbst und seine Details bleiben jedoch im Trade-Kontext.

## 4. Emotionale Hierarchie

Die künftige Profilhierarchie folgt dieser Reihenfolge:

1. Identität
2. Vertrauen
3. Sammlerleben
4. Vitrine und abgeschlossene Alben
5. Trophäen

Die genaue visuelle Ausgestaltung ist nicht Teil dieses Audits. Die Hierarchie ist dennoch verbindlich: Kennzahlen und operative Albumdaten dürfen das Profil nicht wieder zu einem Verwaltungsdashboard machen.

## 5. Sammlr-Ausweis und Identität

Der **Sammlr-Ausweis** ist eine positive Produktrichtung für den kompakten Identitäts- und Vertrauensbereich. Er kann Avatar, stabilen `@username`, optionalen Anzeigenamen, öffentliche Bewertung, Anzahl erfolgreicher Trades und optional „Sammler seit“ enthalten.

Der `@username` bleibt die stabile, primäre und öffentlich sichtbare Identität. Ein Anzeigename ist optional. Das Produkt darf keinen Klarnamen voraussetzen.

Design, Wortlaut, Upload-Verhalten und genaue Feldanordnung des Sammlr-Ausweises bleiben einer späteren UX-Ausarbeitung vorbehalten.

## 6. Vertrauen, Bewertung und Kennzahlen

Öffentlich sichtbar sind grundsätzlich Sterne beziehungsweise Bewertungsdurchschnitt und die Anzahl der eingegangenen Bewertungen. Die Anzahl erfolgreicher Trades kann zusätzlich öffentlich erscheinen. Detaillierte Einzelbewertungen sind eine spätere Ausbaustufe. Die bestehende Entscheidung aus S28, zunächst nur Durchschnitt und Anzahl zu zeigen, bleibt damit gültig.

`Doppelte` ist **keine zentrale, dauerhafte Profilkennzahl**. Sinnvolle Kandidaten für wenige profilrelevante Kennzahlen sind erfolgreiche Trades, abgeschlossene Alben und Trophäen. Die endgültige Auswahl und Gewichtung erfolgt erst in einer Statistik- beziehungsweise UX-Ausarbeitung; dieses Audit erfindet keine neue vollständige Kennzahlenliste.

## 7. Alben, Vitrine und Trophäen

### Aktive Alben

Auf dem eigenen Profil müssen aktive Alben nicht als große operative Übersicht erscheinen. Die Sammlung bleibt der Arbeitsort für Albumverwaltung, Fortschritt und Bestände.

Auf einem fremden Profil sind freigegebene aktive Alben dagegen relevant, weil sie Interessen und mögliche Trade-Bezüge verständlich machen. Wenn die geltende Privatsphäre es erlaubt, kann eine fremde Albumansicht auch Bestände zeigen. Der genaue Detaillierungsgrad wird später geklärt.

### Vitrine und abgeschlossene Alben

Die Vitrine ist ein zentraler Teil des Profils. Abgeschlossene Alben sollen sichtbar und ausstellungsartig präsentiert werden. Auf fremden Profilen gilt dies nur, wenn Profil- und Albumfreigabe die Darstellung erlauben.

### Trophäen

Alle freigeschalteten Trophäen dürfen sichtbar sein; es gibt keine künstliche fachliche Begrenzung auf wenige angeheftete Trophäen. Ob das UI zunächst eine Vorschau, „Alle anzeigen“, eine Unterseite oder Gruppen verwendet, bleibt offen.

## 8. Profil-Privatsphäre und bestehendes S27-Modell

Die neue Produktausrichtung fordert eine leicht verständliche Profil-Privatsphäre mit zwei Zuständen: Profil öffentlich oder Profil privat. Viele zusätzliche Einzel-Schalter auf Profil-, Trophäen-, Statistik- oder Abschnittsebene sollen vermieden werden.

Gleichzeitig ist seit S27 ein detaillierteres, bereits technisch umgesetztes Album-Modell dokumentiert:

- `public`, `friends` oder `private` pro Album,
- ein davon unabhängiger Schalter für den Trade-Pool,
- Sichtbarkeitsprüfung bis in die fremde Albumwand.

Diese Modelle sind derzeit **nicht konsolidiert**. Dieses Audit löscht oder interpretiert die S27-Regeln nicht um. Offen bleibt insbesondere, ob die Profil-Privatsphäre künftig als äußeres Gate vor dem Album-Modell liegt oder ob Produkt und Datenmodell anders zusammengeführt werden. Bis zu einer gesonderten Entscheidung bleibt S27 die technische Wahrheit für Album-Sichtbarkeit und Trade-Pool.

## 9. Freundschaften und Community

Community-Beziehungen sind gegenseitige Freundschaften. Ein Follower-Modell ist nicht vorgesehen.

Freundschaften dürfen echte Produktvorteile haben. Bereits vorhandene Beispiele sind Sichtbarkeit für Freunde, grober Aktivitätsstatus und Trade-Bezug. Weitere Vorteile werden erst separat entschieden und hier nicht erfunden.

Persönliche Community-Aktivitäten in der Sammlr-Zentrale stammen ausschließlich von Freunden. Globale **Sammlr News** sind davon getrennt. Es entsteht kein öffentlicher Follower- oder allgemeiner Social Feed.

## 10. Trade-Historie und Deal-Bezug

Das eigene Profil darf die vollständige persönliche Trade-Historie zeigen. Auf einem fremden Profil sind nur die öffentliche Bewertung und die Anzahl erfolgreicher Trades sichtbar. Gegenpartei, Datum, Sticker und andere Deal-Details anderer Personen gehören nicht dorthin.

Ein Trade oder Deal darf auf das fremde Profil verlinken. Das Profil wird dadurch nicht zu einem zweiten Trade-Archiv; alle fachlichen Deal-Details verbleiben im Deal.

## 11. Profil und Konto bleiben getrennte Welten

| Profil | Account / Einstellungen |
|---|---|
| Sammleridentität | E-Mail und Passwort |
| Community und Freundschaften | Privatsphäre konfigurieren |
| Vitrine und Trophäen | Logout und Kontolebenszyklus |
| Vertrauen und öffentliche Bewertung | Sicherheits- und Systemeinstellungen |
| persönliche Sammlergeschichte | technische Kontoverwaltung |

Die derzeitige Karte „Profil & Konto“ sowie Account-/Einstellungslinks im eigenen Profil sind als Übergang zu bewerten, nicht als langfristige Produktarchitektur.

## 12. Bewusste Abgrenzung

Nicht Bestandteil des Profils sind operative Sammlungs- und Bestandsverwaltung, Mengenänderungen, vollständige Trade-Verwaltung, Benachrichtigungsverwaltung, ein globaler News-Feed, die vollständige Trade-Historie fremder Personen sowie Account-, Sicherheits- und Passwortformulare.

## 13. Heutiger technischer Stand

Bereits vorhanden und in S26–S29 dokumentiert sind:

- ein gemeinsames Leseprofil für eigenes und fremdes Profil,
- die kanonische Profilroute über den Username,
- öffentlicher Bewertungsdurchschnitt und Bewertungsanzahl,
- die Anzahl erfolgreicher Trades,
- aktive und abgeschlossene Albumprojektionen,
- durch S27 gefilterte fremde Albumansichten bis zur read-only Albumwand,
- die Trennung von Album-Sichtbarkeit und Trade-Pool,
- die vollständige eigene Trade-Historie sowie Profilverlinkungen aus Deals,
- gegenseitige Freundschaftsanfragen mit Annahme, Ablehnung, Rücknahme und Entfernung,
- Blockieren, Personensuche, Freundschaftsstatus und grober Freundes-Aktivitätsstatus,
- Trade-Potenzial auf Profil- und Albumebene,
- Benachrichtigungen für Freundschaftsanfrage und -annahme.

Noch nicht oder nicht vollständig vorhanden sind:

- ein globales Profil-Gate `öffentlich` / `privat`,
- eine vollständige Darstellung aller freigeschalteten Trophäen im Profil,
- Freundesaktivitäten als Bereich der Sammlr-Zentrale,
- der Sammlr-Ausweis einschließlich Avatar- und Upload-Verhalten,
- die langfristig klare Trennung der Profil- von der Account-Oberfläche,
- die in diesem Audit festgelegte reduzierte Gewichtung aktiver Alben und der Kennzahl `Doppelte`,
- die ausstellungsartige finale UX für Vitrine und abgeschlossene Alben.

Detaillierte Bewertungen, tiefere Statistiken und weitere Freundschaftsvorteile sind bewusst spätere Produktfragen und daher keine aktuellen technischen Defekte.

## 14. Abgleich mit S26–S29

| Bestand | Verhältnis zum neuen Audit | Konsequenz für die Dokumentation |
|---|---|---|
| S26 setzt aktive Alben prominent und führt `Doppelte` als eine von vier festen Kennzahlen | direkte Hierarchie- und Kennzahlenkollision | S26 bleibt Umsetzungsnachweis; die neue langfristige Richtung benötigt später eine eigene UX-/Umsetzungsentscheidung |
| S26 führt vom eigenen Profil zu Account und Einstellungen | Spannung zur langfristigen Trennung von Profil und Konto | heutiger Zustand gilt als Übergang, nicht als neue Produktregel |
| S27 nutzt Album-Sichtbarkeit `public` / `friends` / `private` plus separaten Trade-Pool | direkte Spannung zum einfachen Profilmodell öffentlich/privat | keine stille Überschreibung; Verhältnis beider Ebenen bleibt offen |
| S28 zeigt Bewertungsdurchschnitt und Anzahl, aber keine Einzelbewertungen | deckungsgleich | keine Korrektur erforderlich |
| S29 setzt gegenseitige Freundschaften, Blockierung und Freundesstatus um | deckungsgleich | kein Follower-Modell ergänzen |
| S29 enthält ausdrücklich noch keinen Freundes-Aktivitätsfeed | funktionale Lücke gegenüber der neuen Community-Regel | späterer eigener Scope für die Sammlr-Zentrale; keine Erweiterung in diesem Audit |

## 15. Bewusst vertagte UX-Fragen

Später zu klären sind:

- visuelle Profilhierarchie und genaue Gestaltung des Sammlr-Ausweises,
- Avatar-Upload und Fallback,
- Eingabe und Darstellung des optionalen Anzeigenamens,
- endgültige Auswahl und Gewichtung der obersten Kennzahlen,
- detaillierte Statistikdarstellung,
- Inszenierung von Vitrine und abgeschlossenen Alben,
- Vorschau, Gruppierung und vollständige Ansicht der Trophäen,
- genaue Bewertungsdarstellung und eine mögliche spätere Detailansicht,
- konkrete Produktvorteile von Freundschaften,
- UX der Profil-Privatsphäre und ihre Beziehung zum S27-Album-Modell,
- genauer Einstieg vom Profil in einen Trade,
- Farben, Typografie, Bewegung und Kartenlayout.

Diese Fragen gehören in die nachfolgenden UX-, Statistik- oder technischen Audit-Schritte. Sie ändern die in diesem Dokument gesetzten Produktgrenzen nicht.
