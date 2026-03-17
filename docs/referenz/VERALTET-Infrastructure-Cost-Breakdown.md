# VERALTET — Infrastructure Cost Breakdown.docx

**Status:** VERALTET (Stand: Pre-Upgrade, vor 2026-03-06)
**Ersetzt durch:** `technische-parameter.md` (SSOT, Sektion 7: Kosten)

## Warum veraltet?

Das Dokument `Infrastructure Cost Breakdown.docx` beschreibt eine Architektur die **nie implementiert** wurde:

| Parameter | Im .docx | Tatsaechlich deployed |
|-----------|----------|----------------------|
| PROD Nodes | 2x g1a.4d (API) + 1x g1a.8d (Search) | 2x g1a.8d (alle Pods) |
| DEV/TEST Nodes | g1a.2d | g1a.8d |
| PROD Gesamtkosten | ~950 EUR/Mo | 964 EUR/Mo |
| DEV/TEST Gesamtkosten | ~317 EUR/Mo | 868 EUR/Mo |

## Aktuelle Kostenreferenz

Die aktuelle und verbindliche Kostenaufstellung ist in `technische-parameter.md`, Sektion 7:
- DEV+TEST: **868,47 EUR/Mo**
- PROD: **963,96 EUR/Mo**
- Gesamt: **1.832,43 EUR/Mo**

Quelle: StackIT Preisliste v1.0.36 (verifiziert 2026-03-05), Live-Cluster-Verifikation 2026-03-16.

## Empfehlung

Die `.docx`-Datei sollte archiviert oder geloescht werden um Verwirrung zu vermeiden.

---

*Erstellt: 2026-03-16, Infrastruktur-Review*
