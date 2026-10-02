# Trade-v2 — Manuelle Auswahl / TRADE-09

Entscheidung des Nutzers vom 2026-10-01; ausschließlich neue, isolierte Trade-v2-Angebote. Keine rückwirkende Migration und keine produktive Integration.

## Explizite begrenzte Supersession

Für diesen neuen Trade-v2-Vertrag ersetzt die **beidseitige Albumfreigabe** die reine globale Empfängerpräferenz aus Manual Offer Domain Contract V1 §3 und der bisherigen Referenz in Trade Product Contract V2 §7. Die älteren Dokumente werden nicht global umgedeutet oder überschrieben. Legacy, vorhandene Angebote, SmartDeal und produktive Pfade bleiben unverändert.

Unverändert: positive ganzzahlige Mengen, tatsächliche freie Supply und Need, keine Mehrfacherfüllung desselben fehlenden Stickers, Give ≥ Receive, beide Seiten mindestens eins, kein künstliches Minimum fünf, keine künstliche Maximalgröße. Empfänger nimmt ausdrücklich an. Ein verbindlicher Snapshot wird niemals nachträglich durch Settings-Wechsel umgeschrieben.

## Albumregeln

Für jedes Album liefern beide Teilnehmer drei getrennte Hooks: `tradeEnabled`, `smartEnabled`, `crossAlbum`. Für eine manuelle Auswahl muss `tradeEnabled` beidseitig wahr sein. `smartEnabled` beeinflusst diesen manuellen Weg nicht.

Ein Album gehört nur dann zum gemeinsamen offenen Ausgleichspool, wenn `crossAlbum` für **beide** Nutzer wahr ist. Alle anderen zugelassenen Alben bilden jeweils ihren eigenen Ausgleichsbereich.

- Je einzelnem eingeschränkten Album: Receive ≤ Give.
- Im offenen Pool: Summe Receive ≤ Summe Give ausschließlich über die beidseitig offenen beteiligten Alben.
- Ein Überschuss aus einem eingeschränkten Album darf kein anderes Album finanzieren.
- Kein striktes 1:1: 2 erhalten / 3 abgeben bleibt erlaubt.
- Ohne zulässige Gegensticker im gleichen Ausgleichsbereich ist Receive nicht auswählbar.

## Draft und Überprüfung

Receive-Auswahl kann bis zum **verfügbaren** Gegenpotential des passenden Ausgleichsbereichs vorgenommen werden, auch bevor die konkreten Give-Sticker gewählt sind. Das ermöglicht die bestehende Listenreihenfolge. Der Nutzer muss vor Review/Submit tatsächlich genügend konkrete Give-Positionen auswählen. Drafts können vorübergehend unausgeglichen sein; sendbar sind sie niemals.

Ein Limit entfernt keine Albumsektion oder Sticker. Zusätzliche unzulässige Auswahl wird mit kurzem Hinweis blockiert; Abwahl bleibt immer möglich. Keine automatische Kürzung anderer gewählter Positionen. Abwahl von Give darf einen ungebundenen Draft ungültig machen; Review und Submit werden dann gesperrt.

Auswahlprüfung und Submit validieren erneut beide Richtungen, Albumfreigaben, Identitäten, freie Supply, Need und Bereichsmengen gegen die explizite Preview-Kontextquelle. Draft belegt keine Slots und besitzt keine 24h-Frist. Erst der vorhandene Requestcommand verwendet gemeinsame Kapazität, Frist, Annahme, Packen, Versand, Q2-Empfang, Problemklärung, Abschluss und Bewertung.

## Spätere Integration

Preview-Fixtures sind ausdrücklich synthetische, bereits kanonisch aufgelöste Supply-/Need-/Eligibility-Eingaben. Kein neuer Inventarrechner oder Optimizer. Später benötigt: autorisierte gemeinsame Availability-Reader einschließlich Reservations/Transit/Eigenexemplar, beide aktuellen Albumfreigaben, globaler Settings-Editor für dieselben Albumwerte, geprüfter Versions-/Freigabestand im Snapshot sowie atomare Revalidierung und Bindung beim Submit. Herkunft allein ersetzt keinen persistierten Contract-Type. Keine Settings-UI, DB-Migration oder produktive Reservation in TRADE-09.
