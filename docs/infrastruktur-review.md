# Infrastruktur-Review — VÖB Chatbot

**Datum:** 2026-03-16
**Version:** 1.0
**Ersteller:** COFFEESTUDIOS (Claude Infrastructure Review)
**Methodik:** Dokumentenanalyse + Live-Cluster-Verifikation + Web-Recherche

---

## 1. Executive Summary

Das VÖB-Chatbot-Projekt basiert auf einer soliden, enterprise-tauglichen Architektur mit StackIT als Cloud-Provider. Die Infrastruktur ist für 150 User ausgelegt und kostet aktuell **1.832,43 EUR/Monat** (alle 3 Umgebungen). Die Hauptkritikpunkte:

1. **CPU massiv überversorgt:** Tatsächliche Auslastung liegt bei **3-6% CPU** auf allen Clustern — die Ressourcen-Requests der Pods sind 10-16x höher als der reale Verbrauch.
2. **Storage erheblich überversorgt:** Vespa PROD nutzt 884 Mi von 50 Gi (1,7%), Prometheus PROD nutzt 1,1 Gi von 50 Gi (2,2%).
3. **DEV/TEST Node-Sizing hat Einsparpotenzial:** Mit optimierten Resource Requests könnten 2x g1a.4d statt 2x g1a.8d reichen — Einsparung **~283 EUR/Monat**.
4. **Dokumentation teilweise inkonsistent:** `prod-bereitstellung.md` dokumentiert andere Resource-Werte als tatsächlich deployed.

**Top-3 Empfehlungen:**
- **Kurzfristig:** DEV/TEST Resource Requests um 30-40% senken, PVC-Größen an realen Bedarf anpassen
- **Mittelfristig:** DEV/TEST Node-Downgrade auf 2x g1a.4d prüfen (spart 283 EUR/Mo)
- **Strategisch:** Scheduled Scaling (Nodes nachts/am Wochenende herunterfahren) — spart weitere ~200 EUR/Mo

**Gesamtbewertung:** Die Architekturentscheidungen (StackIT, K8s, 3 Umgebungen) sind für den Banking-Kontext korrekt und gut begründet. Das Einsparpotenzial liegt primär im **Sizing**, nicht in der Architektur.

---

## 2. Ressourcenbedarf Onyx

### 2.1 Upstream-Anforderungen (Onyx/Danswer)

| Parameter | Upstream-Empfehlung | Quelle |
|-----------|---------------------|--------|
| Minimum RAM (Single Instance) | 10 GB min, 16 GB empfohlen | [docs.onyx.app/resourcing](https://docs.onyx.app/deployment/getting_started/resourcing) |
| Minimum CPU (Single Instance) | 4 vCPU min, 8 vCPU empfohlen | docs.onyx.app |
| Helm Chart Defaults (Requests) | ~14,65 CPU, ~24,8 Gi RAM | Upstream `values.yaml` |
| Helm Chart Defaults (Limits) | ~30 CPU, ~94 Gi RAM | Upstream `values.yaml` |
| Vespa RAM (Basis) | 8 Gi Request, 32 Gi Limit | Upstream `values.yaml` |
| Vespa Skalierung | +3 GB RAM pro 1 GB indexierter Daten | docs.onyx.app |
| Vespa Disk-Schwelle | Blockiert Writes bei 75% Disk-Nutzung | [GitHub Issue #839](https://github.com/danswer-ai/danswer/issues/839) |
| Model Server (Indexing) | 4 CPU Req, 3 Gi RAM Req | Upstream `values.yaml` |
| Model Server (Inference) | 2 CPU Req, 3 Gi RAM Req | Upstream `values.yaml` |
| Getestet bis | "Tens of thousands" User | onyx.app |
| Pflichtkomponenten | API, Web, Vespa, PG, Redis, 2x Model Server, 8 Celery Worker | Helm Chart |

**Kritische Erkenntnis:** Die VÖB-Konfiguration setzt die Resource Requests deutlich NIEDRIGER an als Upstream-Defaults:

| Komponente | Upstream Request | VÖB DEV Request | VÖB PROD Request | Reduktion vs Upstream |
|------------|-----------------|-----------------|-------------------|----------------------|
| Vespa CPU | 4000m | 500m | 2000m | -88% / -50% |
| Vespa RAM | 8 Gi | 2 Gi | 4 Gi | -75% / -50% |
| Indexing Model CPU | 4000m | 250m | 500m | -94% / -88% |
| Inference Model CPU | 2000m | 250m | 500m | -88% / -75% |
| Celery DocFetching RAM | 2 Gi | 512 Mi | 1 Gi | -75% / -50% |
| Celery DocProcessing RAM | 2 Gi | 512 Mi | 1 Gi | -75% / -50% |

Dies ist bei minimalem Datenvolumen (< 1 GB indexiert) vertretbar, wird aber bei wachsender Datenmenge kritisch.

### 2.2 Tatsächlicher Verbrauch (Live-Cluster, 2026-03-16)

#### Node-Auslastung

| Cluster | Node | CPU Actual | CPU % | RAM Actual | RAM % |
|---------|------|-----------|-------|-----------|-------|
| **DEV+TEST** | Node 1 | 473m | **5%** | 8.669 Mi | **30%** |
| **DEV+TEST** | Node 2 | 457m | **5%** | 9.730 Mi | **34%** |
| **DEV+TEST Total** | 2 Nodes | **930m** | **5,8%** | **18.399 Mi** | **31,7%** |
| **PROD** | Node 1 | 304m | **3%** | 7.806 Mi | **27%** |
| **PROD** | Node 2 | 277m | **3%** | 4.854 Mi | **17%** |
| **PROD Total** | 2 Nodes | **581m** | **3,7%** | **12.660 Mi** | **21,8%** |

> **Bewertung:** CPU-Auslastung ist extrem niedrig (3-6%). RAM-Auslastung mit 22-32% ist moderat. Dies ist allerdings der Idle-Zustand ohne reale Nutzer — bei 150 aktiven Usern wird die CPU-Auslastung steigen, aber nicht auf über 30-40%.

#### Top-Verbraucher nach tatsächlicher RAM-Nutzung (PROD)

| Pod | CPU Actual | RAM Actual | CPU Request | RAM Request | CPU-Nutzung der Requests |
|-----|-----------|-----------|-------------|-------------|-------------------------|
| Vespa | 189m | 3.143 Mi | 2000m | 4 Gi | 9,5% |
| API Server (je) | 2m | 504 Mi | 500m | 512 Mi | 0,4% |
| Celery Primary (je) | 12m | 269 Mi | 500m | 1 Gi | 2,4% |
| Model Servers (je) | 1-2m | 279 Mi | 500m | 1 Gi | 0,4% |
| Celery Light | 10m | 249 Mi | 500m | 1 Gi | 2,0% |
| Celery Heavy | 10m | 220 Mi | 500m | 1 Gi | 2,0% |
| Celery DocFetching | 10m | 192 Mi | 500m | 1 Gi | 2,0% |
| Prometheus | 42m | 415 Mi | 500m | 1 Gi | 8,4% |
| Grafana | 6m | 299 Mi | 100m | 256 Mi | 6,0% |
| Redis Operator | 5m | 33 Mi | 500m | 500 Mi | 1,0% |

> **Erkenntnis:** Die CPU Requests sind im Durchschnitt **20x höher** als die tatsächliche Nutzung. RAM Requests sind realistischer (Faktor 1,5-4x). Dies ist typisch für Low-Load-Szenarien, aber die Requests könnten signifikant gesenkt werden.

### 2.3 Datenbank-Sizing & Wachstumsprognose

| Umgebung | PG Flavor | vCPU | RAM | Storage | Aktuelle DB-Größe | Quelle |
|----------|-----------|------|-----|---------|-------------------|--------|
| DEV | Flex 2.4 Single | 2 | 4 GB | 20 GB | ~17 MB | Backup-Recovery-Konzept |
| TEST | Flex 2.4 Single | 2 | 4 GB | 20 GB | ~17 MB (geschätzt) | Analog DEV |
| PROD | Flex 4.8 HA 3-Node | 4 | 8 GB | 50 GB | < 1 GB | Backup-Recovery-Konzept |

#### Vespa Storage (Vektor-Datenbank)

| Umgebung | PVC Provisioned | PVC Used | Auslastung |
|----------|----------------|----------|-----------|
| DEV | 20 Gi | 927 Mi | **4,5%** |
| TEST | 20 Gi | 911 Mi | **4,4%** |
| PROD | 50 Gi | 884 Mi | **1,7%** |

#### Wachstumsprognose (bei 150 Usern, 10 Queries/Tag)

| Zeitraum | Geschätzte DB-Größe | Geschätzte Vespa-Größe | Basis |
|----------|---------------------|----------------------|-------|
| Heute (März 2026) | < 1 GB | < 1 GB | Live-Messung |
| 6 Monate (Sep 2026) | 1-2 GB | 2-3 GB | ~10 MB/User/Monat, moderate Connector-Nutzung |
| 12 Monate (März 2027) | 3-5 GB | 5-8 GB | Steigendes Datenvolumen durch RAG |
| 24 Monate (März 2028) | 6-10 GB | 10-15 GB | Mit Chat-Retention 6 Monate gedämpft |

> **Bewertung:** Bei < 5 GB indexierten Daten benötigt Vespa ~19 CPU und ~19 Gi RAM (Onyx-Formel). Das passt auf 2x g1a.8d. Erst bei > 10 GB wird es eng (RAM ~34 Gi, CPU ~9 zusätzlich). **PROD Vespa PVC von 50 Gi ist für die nächsten 2 Jahre ausreichend, könnte aber initial auf 20 Gi reduziert werden.**

---

## 3. Kostenanalyse

### 3.1 Aktuelle monatliche Kosten (verifiziert)

**Quelle:** `docs/referenz/technische-parameter.md` (SSOT), verifiziert gegen StackIT Preisliste v1.0.36

#### DEV+TEST (Cluster `vob-chatbot`, shared)

| Posten | Anz. | EUR/Mo je | EUR/Mo gesamt | Verifiziert |
|--------|------|-----------|---------------|-------------|
| SKE Cluster Management Fee | 1 | 71,71 | 71,71 | ✅ StackIT Preisliste |
| Worker Node g1a.8d | 2 | 283,18 | 566,36 | ✅ 0,39331 EUR/h × 720h |
| PostgreSQL Flex 2.4 Single | 2 | 105,54 | 211,08 | ✅ inkl. Disk Perf. |
| Object Storage Bucket | 2 | 0,27 | 0,54 | ✅ |
| Load Balancer Essential-10 | 2 | 9,39 | 18,78 | ✅ |
| **Gesamt DEV+TEST** | | | **868,47** | |

#### PROD (Cluster `vob-prod`, dedicated)

| Posten | Anz. | EUR/Mo je | EUR/Mo gesamt | Verifiziert |
|--------|------|-----------|---------------|-------------|
| SKE Cluster Management Fee | 1 | 71,71 | 71,71 | ✅ |
| Worker Node g1a.8d | 2 | 283,18 | 566,36 | ✅ |
| PostgreSQL Flex 4.8 HA 3-Node | 1 | 316,23 | 316,23 | ✅ inkl. Disk Perf. |
| Object Storage Bucket | 1 | 0,27 | 0,27 | ✅ |
| Load Balancer Essential-10 | 1 | 9,39 | 9,39 | ✅ |
| **Gesamt PROD** | | | **963,96** | |

#### Gesamtkosten

| Scope | EUR/Monat | EUR/Jahr |
|-------|-----------|----------|
| DEV+TEST | 868,47 | 10.421,64 |
| PROD | 963,96 | 11.567,52 |
| **Gesamt** | **1.832,43** | **21.989,16** |

#### Nicht enthaltene Kosten

| Posten | Geschätzter Betrag | Status |
|--------|-------------------|--------|
| Block Storage (Vespa PVCs) | ~5-10 EUR/Mo | Preis nicht verifizierbar (StackIT Block Storage Preis nicht öffentlich) |
| Container Registry | 0 EUR (Beta) | Wird bei GA kostenpflichtig |
| LLM Token-Kosten (StackIT AI) | ~40-96 EUR/Mo (bei 80-150 Usern) | Usage-basiert, variabel |
| DNS Zone | ~1,92 EUR/Mo | Falls genutzt |
| Monitoring-Stack | 0 EUR (self-hosted) | Statt StackIT LogMe (~274 EUR/Mo) |

### 3.2 Kostenverteilung

```
Kostenverteilung GESAMT (1.832,43 EUR/Mo):

Compute (Worker Nodes):     1.132,72 EUR  ████████████████████  61,8%
Datenbank (PostgreSQL):       527,31 EUR  ██████████            28,8%
K8s Management (2 Cluster):   143,42 EUR  ███                    7,8%
Load Balancer (3x):            28,17 EUR  █                      1,5%
Object Storage:                 0,81 EUR  ▏                      0,0%
```

> **Compute und Datenbank machen zusammen 90,6% der Kosten aus.** Jede Optimierung muss hier ansetzen.

### 3.3 Vergleich mit Alternativen

#### Äquivalentes PROD-Setup (2x 8vCPU/32GB Nodes, HA PostgreSQL, S3, LB)

| Provider | Compute | K8s Fee | Datenbank (HA) | Storage | LB | **Gesamt/Mo** | BSI C5 |
|----------|---------|---------|----------------|---------|-----|--------------|--------|
| **StackIT** | 566 | 72 | 316 | 0,27 | 9 | **~964** | ✅ Type 2 |
| **IONOS** (Pay-as-you-go) | ~622 | 0 | ~183 | ~7 | 14 | **~826** | ✅ |
| **IONOS** (3yr Savings) | ~400 | 0 | ~122 | ~7 | 14 | **~543** | ✅ |
| **Open Telekom Cloud** | ~290 | 0 | ~180 | ~5 | ~10 | **~485** | ✅ Type 2 |
| **Hetzner** (DIY K8s) | 97 | 0 | ~50 (self-hosted) | 6 | 5 | **~158** | ✅ (seit 2024) |

#### Bewertung des Vergleichs

| Kriterium | StackIT | Hetzner | IONOS | OTC |
|-----------|---------|---------|-------|-----|
| BSI C5 Type 2 | ✅ | ✅ (seit 2024) | ✅ | ✅ |
| Managed Kubernetes | ✅ (SKE) | ❌ (DIY) | ✅ (free CP) | ✅ (CCE) |
| Managed PostgreSQL | ✅ (Flex) | ❌ (Self-Host) | ✅ (DBaaS) | ✅ (RDS) |
| AI Model Serving | ✅ (vLLM) | ❌ | ❌ | ❌ |
| Egress-Kosten | **FREI** | 1,20 EUR/TB (>1TB) | N/A | Kostenpflichtig |
| Rechenzentrum DE | ✅ Frankfurt | ✅ Falkenstein/Nürnberg | ✅ Frankfurt | ✅ Magdeburg/Biere |
| Support Deutsch | ✅ | ✅ | ✅ | ✅ |
| Banking-Referenzen | ✅ (Schwarz Gruppe) | ❌ | Einige | ✅ (T-Systems) |

> **Fazit:** StackIT ist ~2x teurer als IONOS/OTC für vergleichbare Managed Services. Der Aufpreis von ~400-500 EUR/Mo (PROD) ist durch den integrierten AI Model Serving Service, kostenfreien Egress und die bestehende Vertragsbeziehung teilweise gerechtfertigt. Ein Provider-Wechsel würde signifikanten Migrationsaufwand bedeuten (5-10 PT) und den AI-Model-Serving-Vorteil verlieren. **Kein Wechsel empfohlen, aber im Hinterkopf behalten.**

---

## 4. Architektur-Bewertung

### 4.1 StackIT als Provider

**ADR-003 Validierung:**

| Entscheidungsgrund im ADR | Noch aktuell? | Bewertung |
|---------------------------|---------------|-----------|
| 100% deutsche Datensouveränität (CLOUD Act) | ✅ Ja | Kernargument für Banking, weiterhin valide |
| BSI C5 Type 2 zertifiziert | ✅ Ja | Aber: Hetzner hat seit 2024 auch BSI C5 |
| Managed K8s + PG + S3 | ✅ Ja | Full-Managed reduziert Betriebsaufwand erheblich |
| AI Model Serving (vLLM) | ✅ Ja | Einzigartiger Vorteil — GPT-OSS 120B, Qwen3 VL 235B on-premise |
| Transparente Preise | ✅ Ja, mit Einschränkung | Block Storage Preise nicht öffentlich dokumentiert |
| Banking-Erfahrung | ✅ Ja | Schwarz Gruppe / Lidl Bank als Referenz |

**Neues Argument seit ADR-003:** Hetzner hat BSI C5 erhalten (2024). Damit fällt das Compliance-Argument als Alleinstellungsmerkmal weg. Hetzner bietet allerdings weder Managed K8s noch Managed PostgreSQL — der Self-Hosting-Aufwand wäre erheblich (~3-5 PT Setup + laufende Wartung).

**Bewertung: 7/10** — StackIT ist die richtige Wahl für den Banking-Kontext, aber nicht die günstigste. Der AI Model Serving Service ist ein echter Differentiator.

### 4.2 Kubernetes-Entscheidung

**Ist K8s für 150 User nötig?**

| Argument Pro K8s | Bewertung |
|-----------------|-----------|
| Onyx hat 14-19 Pods mit komplexer Orchestrierung | ✅ Zwingend — 8 Celery Worker + Vespa + Redis + 2 Model Server |
| HA für PROD (multi-Pod) | ✅ Sinnvoll für Banking |
| NetworkPolicies (Namespace-Isolation) | ✅ Security-Anforderung |
| Health Probes + Auto-Restart | ✅ Betriebsstabilität |
| Helm-basiertes Deployment | ✅ Reproduzierbar, versioniert |

| Argument Contra K8s | Bewertung |
|--------------------|-----------|
| Docker Compose wäre einfacher | ❌ Nicht für 19 Pods mit HA, Probes, NetworkPolicies |
| Wartungsaufwand (Upgrades, kubeconfig) | ⚠️ Real, aber durch StackIT SKE reduziert |
| Overhead (kube-system ~1 CPU, ~1 Gi) | ⚠️ Akzeptabel bei 16 CPU/64 GB Nodes |

**Alternative geprüft:** Docker Compose auf VM (Hetzner CX42, ~30 EUR/Mo). Theoretisch möglich, aber:
- Kein HA (Single Point of Failure)
- Keine NetworkPolicies
- Keine Health Probes / Auto-Restart
- Kein Monitoring-Stack out-of-the-box
- Nicht banking-konform (BSI SYS.1.6 fordert Container-Orchestrierung für produktive Systeme)

**Bewertung: 9/10** — Kubernetes ist für diesen Use-Case korrekt. Onyx IST eine K8s-Anwendung mit 14-19 Pods. Docker Compose wäre nur für eine reine Evaluierung vertretbar.

### 4.3 3-Umgebungen-Strategie

**ADR-004 Validierung:**

| Umgebung | Monatliche Kosten | Notwendigkeit |
|----------|-------------------|---------------|
| DEV | ~434 EUR (Anteil) | ✅ Zwingend für Entwicklung |
| TEST | ~434 EUR (Anteil) | ⚠️ Aktuell ohne User, Kosten fragwürdig |
| PROD | ~964 EUR | ✅ Zwingend für Live-Betrieb |

**Frage: Braucht man TEST 24/7?**

Die TEST-Umgebung läuft rund um die Uhr, hat aber aktuell keine regelmäßigen Nutzer. Optionen:

| Option | Einsparung/Mo | Aufwand | Risiko |
|--------|--------------|---------|--------|
| TEST on-demand (Scale-to-Zero) | ~200 EUR | Skript schreiben (1h) | Startup-Zeit ~15 Min |
| TEST entfernen, DEV = TEST | ~434 EUR | Workflow ändern | Keine getrennten Test-Daten |
| DEV lokal (Docker Compose) | ~434 EUR | Setup (2h) | Abweichung vom Cloud-Setup |
| Status quo (24/7) | 0 | 0 | 0 |

> **Empfehlung:** TEST on-demand ist der beste Kompromiss — Skript existiert bereits konzeptionell in `docs/referenz/kostenoptimierung-dev-test.md`. Einsparung: ~200 EUR/Mo bei minimalem Risiko.

**Bewertung: 7/10** — 3 Umgebungen sind enterprise-konform, aber TEST 24/7 ist für die aktuelle Phase (kein Live-Betrieb) Overprovisioning.

### 4.4 Node-Sizing

**ADR-005 Validierung:**

| Behauptung im ADR | Verifiziert | Status |
|--------------------|-----------|--------|
| g1a.4d reicht nicht für 8 Celery Worker | ⚠️ Teilweise | Resource REQUESTS passen nicht, aber ACTUAL Usage ist 5% CPU |
| 2x g1a.8d: ~5% CPU, ~28% RAM (ADR-005) | ✅ Live bestätigt | DEV+TEST: 5,8% CPU, 31,7% RAM |
| 2x g1a.8d Kosten: 566,36 EUR/Mo | ✅ Bestätigt | StackIT Preisliste verifiziert |
| PROD: 2x g1a.8d reicht für 150 User | ⚠️ Wahrscheinlich | Actual PROD 3,7% CPU — aber ohne reale Last |

**Kritische Analyse: Passen 2x g1a.4d für DEV+TEST?**

```
DEV+TEST Cluster Resource Requests (live, 2026-03-16):

DEV (16 Pods):       CPU  2.850m  |  RAM  6,33 Gi
TEST (15 Pods):      CPU ~2.750m  |  RAM ~6,10 Gi
Monitoring (11 Pods): CPU ~1.100m |  RAM ~1,90 Gi
kube-system:          CPU ~1.060m |  RAM ~1,00 Gi
──────────────────────────────────────────────────
TOTAL Requests:       CPU ~7.760m |  RAM ~15,33 Gi

2x g1a.4d allocatable: CPU ~7.400m |  RAM ~28 Gi
→ CPU: 105% ← PASST NICHT (360m über Limit)

2x g1a.8d allocatable: CPU ~15.820m | RAM ~55 Gi
→ CPU: 49%  | RAM: 28% ← Reichlich Headroom
```

Die 360m Überschreitung bei g1a.4d ist marginal. Mit einer **10-15% Reduktion der Resource Requests** (die bei 5% tatsächlicher Auslastung absolut vertretbar ist) würde es passen. Konkret:

| Komponente | Aktueller Request | Vorschlag | Reduktion |
|------------|-------------------|-----------|-----------|
| Celery Worker (je, CPU) | 250m | 150m | -40% |
| Redis Operator (CPU) | 500m | 200m | -60% |
| Model Server (CPU, je) | 250m | 150m | -40% |
| Vespa DEV (CPU) | 500m | 400m | -20% |

Damit: DEV+TEST Requests ~6.200m → passt auf 2x g1a.4d (84%).

**Einsparung: 2x (283,18 - 141,59) = 283,18 EUR/Monat.**

> **Empfehlung:** Zuerst Resource Requests für DEV/TEST optimieren. Wenn stabil bei 80% Requests-Auslastung → Node-Downgrade auf g1a.4d evaluieren. Für PROD bleiben g1a.8d korrekt.

### 4.5 PostgreSQL-Sizing

| Instanz | Flavor | Kosten/Mo | DB-Größe | Auslastung | Bewertung |
|---------|--------|-----------|----------|-----------|-----------|
| DEV | Flex 2.4 Single | 105,54 | ~17 MB | < 0,1% | ⚠️ Oversized |
| TEST | Flex 2.4 Single | 105,54 | ~17 MB | < 0,1% | ⚠️ Oversized |
| PROD | Flex 4.8 HA 3-Node | 316,23 | < 1 GB | < 5% | ⚠️ Oversized, aber HA ist korrekt |

**Analyse:** Die kleinste verfügbare Instanz (Flex 2.4 Single) kostet 105,54 EUR/Mo. Ein Downgrade ist nicht möglich — es gibt keine kleinere Option.

Für PROD: Flex 4.8 HA (3-Node) ist für Banking-PROD korrekt. Ein Downgrade auf Flex 2.4 HA wäre möglich:
- Flex 2.4 Replica HA: ~141,90 EUR/Mo (aus Excel)
- Einsparung: ~174 EUR/Mo
- Risiko: 2 CPU / 4 GB RAM könnte bei 150 gleichzeitigen DB-Connections eng werden
- **Empfehlung: Aktuell beibehalten, nach 6 Monaten PROD-Betrieb reevaluieren**

### 4.6 Monitoring-Overhead

| Metrik | App-Pods (PROD) | Monitoring-Pods (PROD) | Verhältnis |
|--------|----------------|----------------------|------------|
| CPU Actual | 307m | 60m | 5:1 |
| RAM Actual | 5.572 Mi | 912 Mi | 6:1 |
| CPU Requests | 8.450m | 1.175m | 7:1 |
| Pod Count | 19 | 9 | 2:1 |

**Bewertung:** Das Monitoring verbraucht ~14% der CPU-Requests und ~16% der RAM-Nutzung. Das Verhältnis (Monitoring ~1/6 der App) ist für einen Stack dieser Größe **akzeptabel**. Der kube-prometheus-stack ist Standard für K8s-Deployments und die Kosten (0 EUR, self-hosted) sind niedriger als StackIT LogMe (~274 EUR/Mo).

#### Prometheus Storage

| Cluster | PVC | Genutzt | Retention | Bewertung |
|---------|-----|---------|-----------|-----------|
| DEV+TEST | 20 Gi | 2,3 Gi (11,8%) | 30 Tage | ✅ Angemessen |
| PROD | 50 Gi | 1,1 Gi (2,2%) | 90 Tage | ⚠️ Oversized |

> PROD Prometheus läuft erst seit ~4 Tagen. Bei linearer Hochrechnung: 90 Tage × (1,1 Gi / 4 Tage) = ~25 Gi. Die 50 Gi PVC hat also ausreichend Headroom und ist für 90-Tage-Retention **vertretbar**, könnte aber auf 30 Gi reduziert werden.

---

## 5. Komponentenanalyse Onyx

### 5.1 Laufende Komponenten (PROD)

| Komponente | Pods | Nötig? | CPU Actual | RAM Actual | Bewertung |
|------------|------|--------|-----------|-----------|-----------|
| API Server | 2 (HA) | ✅ Ja | 2m × 2 | 504 Mi × 2 | Core-App |
| Web Server | 2 (HA) | ✅ Ja | 1m × 2 | 64 Mi × 2 | Frontend |
| Vespa | 1 | ✅ Ja | 189m | 3.143 Mi | Vektor-DB, Haupt-RAM-Verbraucher |
| Redis | 1 | ✅ Ja | 6m | 12 Mi | Cache/Queues |
| Inference Model | 1 | ✅ Ja | 1m | 278 Mi | Embedding-Inference |
| Indexing Model | 1 | ✅ Ja | 2m | 279 Mi | Embedding-Indexing |
| Celery Primary | 2 (HA) | ✅ Ja | 12m × 2 | 269 Mi × 2 | Kern-Tasks |
| Celery Light | 1 | ✅ Ja | 10m | 249 Mi | Vespa Ops |
| Celery Heavy | 1 | ✅ Ja | 10m | 220 Mi | Pruning |
| Celery DocFetching | 1 | ✅ Ja | 10m | 192 Mi | Connector-Daten |
| Celery DocProcessing | 1 | ✅ Ja | 10m | 192 Mi | Indexing-Pipeline |
| Celery Monitoring | 1 | ⚠️ Optional | 11m | 170 Mi | System-Monitoring (redundant mit kube-prometheus?) |
| Celery UserFile | 1 | ✅ Ja | 9m | 203 Mi | User-Uploads |
| Celery Beat | 1 | ✅ Ja | 13m | 160 Mi | Scheduler |
| NGINX Ingress | 1 | ✅ Ja | 2m | 112 Mi | Traffic-Routing |
| Redis Operator | 1 | ✅ Ja | 5m | 33 Mi | Redis-Management |

**Keine unnötigen Komponenten gefunden.** Alle Pods haben eine Funktion. Der Celery Monitoring Worker ist der einzige potenziell redundante Pod (da kube-prometheus-stack bereits System-Monitoring macht), aber er überwacht Onyx-interne Metriken (Queue-Längen etc.).

### 5.2 Deaktivierte Komponenten (korrekt)

| Komponente | Status | Begründung |
|------------|--------|-----------|
| PostgreSQL (Helm) | ❌ Deaktiviert | Extern (StackIT PG Flex) |
| MinIO | ❌ Deaktiviert | Extern (StackIT Object Storage) |
| OpenSearch | ❌ Deaktiviert | Vespa wird stattdessen genutzt |
| Slackbot | ❌ Deaktiviert | Nicht benötigt |
| Discordbot | ❌ Deaktiviert | Nicht benötigt |
| Code Interpreter | ❌ Deaktiviert | Nicht benötigt |
| MCP Server | ❌ Deaktiviert | Nicht benötigt |
| Let's Encrypt (Chart) | ❌ Deaktiviert | Eigener cert-manager ClusterIssuer |

---

## 6. Optimierungsempfehlungen

### Quick Wins (0-2 Wochen)

| # | Maßnahme | Einsparung/Mo | Risiko | Aufwand |
|---|----------|--------------|--------|---------|
| Q1 | ~~DEV/TEST Resource Requests um 30% senken~~ | ✅ **ERLEDIGT (2026-03-16)** — 40-80% Reduktion, inkl. redis-operator + Monitoring | — | — |
| Q2 | ~~Vespa PROD PVC von 50 Gi auf 20 Gi reduzieren~~ | **UEBERSPRUNGEN** — ~2 EUR/Mo Einsparung, Aufwand >> Nutzen | — | — |
| Q3 | `prod-bereitstellung.md` Section 11 korrigieren | 0 EUR | Keine | 1h |
| Q4 | Excel + Word Kostenaufstellung archivieren oder als "veraltet" markieren | 0 EUR | Keine | 30 Min |

### Mittelfristig (1-3 Monate)

| # | Maßnahme | Einsparung/Mo | Risiko | Aufwand |
|---|----------|--------------|--------|---------|
| M1 | ~~DEV/TEST Nodes: g1a.8d → g1a.4d~~ | ✅ **ERLEDIGT (2026-03-16)** — Terraform apply, 2x g1a.4d, **-283 EUR/Mo** | — | — |
| M2 | ~~TEST Scale-to-Zero~~ | ✅ **ERLEDIGT (2026-03-16)** — CronJobs Mo-Fr 08-18 UTC, **~130-200 EUR/Mo** | — | — |
| M3 | PROD PG: Flex 4.8 → Flex 2.4 HA nach 6 Mo Betriebserfahrung | **~174 EUR** | Mittel (weniger CPU/RAM) | 2h (Terraform, Downtime 30 Min) |

### Strategisch (3-6 Monate)

| # | Maßnahme | Einsparung/Mo | Risiko | Aufwand |
|---|----------|--------------|--------|---------|
| S1 | PROD Resource Requests right-sizen (nach 3 Mo Live-Daten) | Prerequisite für weitere Optimierung | Niedrig | 4h |
| S2 | StackIT Reserved Instances (falls angeboten) | ~10-20% | Niedrig | 2h (Vertrag) |
| S3 | Provider-Vergleich reevaluieren (IONOS, OTC) bei Vertragsverlängerung | ~200-400 EUR | Hoch (Migration) | 20-40h |

### Maximales Einsparpotenzial

| Szenario | Monatliche Kosten | Einsparung vs. Heute |
|----------|-------------------|---------------------|
| Status quo | 1.832 EUR | - |
| Q1-Q4 umgesetzt | 1.830 EUR | ~2 EUR |
| + M1 (g1a.4d DEV/TEST) | 1.547 EUR | **285 EUR (15,5%)** |
| + M2 (TEST Scale-to-Zero) | 1.347 EUR | **485 EUR (26,5%)** |
| + M3 (PG Downgrade PROD) | 1.173 EUR | **659 EUR (36,0%)** |

---

## 7. Gesamtbewertung

| Dimension | Score (1-10) | Kommentar |
|-----------|-------------|-----------|
| **Kosten-Effizienz** | **5/10** | 1.832 EUR/Mo für 150 User ist hoch. 36% Einsparpotenzial identifiziert. Haupttreiber: g1a.8d für DEV+TEST und PG HA PROD. |
| **Sizing-Angemessenheit** | **4/10** | CPU 10-16x überversorgt, Vespa PVC 20-50x überversorgt. RAM ist der einzige korrekt dimensionierte Parameter. |
| **Architektur-Fit** | **9/10** | StackIT + K8s + 3 Umgebungen ist enterprise-korrekt für Banking. Keine fundamentalen Architekturprobleme. |
| **Zukunftssicherheit** | **8/10** | Skalierungspfad klar (3. Node, PG HA, Vespa Scale-Up). Upstream-Sync funktioniert. |
| **Betriebskomplexität** | **6/10** | kube-prometheus-stack + 3 Umgebungen + 2 Cluster + cert-manager + NetworkPolicies. Für Solo-Dev erheblich, aber durch Managed Services reduziert. |

---

## 8. Dokumenten-Validierung

### 8.1 StackIT Kostenaufstellung VOEB Chatbot v1.xlsx

| Behauptung | Dokumentiert | Verifiziert | Status |
|------------|-------------|-------------|--------|
| g1a.8d Preis | 283,18 EUR/Mo | 283,18 EUR/Mo | ✅ BESTÄTIGT |
| g1a.4d Preis | 141,59 EUR/Mo | 141,59 EUR/Mo | ✅ BESTÄTIGT |
| PG Flex 2.4 Single | 90,71 EUR/Mo | 90,71 EUR (ohne Disk Perf) | ⚠️ TEILWEISE — SSOT zeigt 105,54 inkl. Disk Performance (14,50 EUR) |
| PG Flex 4.8 HA 3-Node | 271,75 EUR/Mo | 271,75 EUR (ohne Disk Perf) | ⚠️ TEILWEISE — SSOT zeigt 316,23 inkl. Disk Performance |
| "Expected" Gesamtkosten | 1.091,03 EUR/Mo | N/A | ❌ VERALTET — basiert auf g1a.4d Nodes und anderer Architektur |
| LLM Tokenkosten "Expected" | 40,26 EUR/Mo | Plausibel bei 80 Usern | ✅ Rechnung nachvollziehbar |

> **Bewertung:** Das Excel enthält valide Stückpreise, aber die Kostenszenarien sind **veraltet** (pre-Upgrade-Architektur). Die Preisliste-Sheet bleibt als Referenz nutzbar. Die PG-Preise unterscheiden sich von der SSOT weil das Excel den Disk-Performance-Aufschlag separat ausweist. **Empfehlung: Als "historisch" markieren, Preisliste-Sheet ggf. aktualisieren.**

### 8.2 Infrastructure Cost Breakdown.docx

| Behauptung | Dokumentiert | Verifiziert | Status |
|------------|-------------|-------------|--------|
| PROD Architektur | 2x g1a.4d (API) + 1x g1a.8d (Search) | Aktuell: 2x g1a.8d (alle Pods) | ❌ VERALTET |
| PROD Gesamtkosten | ~950,82 EUR/Mo | Aktuell: 963,96 EUR/Mo | ❌ VERALTET (andere Architektur) |
| DEV/TEST Node-Flavor | g1a.2d | Aktuell: g1a.8d | ❌ VERALTET |
| DEV/TEST Kosten | ~316,66 EUR/Mo | Aktuell: 868,47 EUR/Mo | ❌ VERALTET |

> **Bewertung: KOMPLETT VERALTET.** Beschreibt eine Architektur die nie implementiert wurde (g1a.4d + g1a.8d gemischt, DEV/TEST auf g1a.2d). **Empfehlung: Archivieren oder löschen. Verwirrungsgefahr hoch.**

### 8.3 technische-parameter.md (SSOT)

| Behauptung | Dokumentiert | Verifiziert | Status |
|------------|-------------|-------------|--------|
| Node Flavor g1a.8d | 8 vCPU, 32 GB | ✅ Live bestätigt | ✅ BESTÄTIGT |
| Allocatable CPU pro Node | ~7.910m | ✅ Live: 7.910m | ✅ BESTÄTIGT |
| Allocatable RAM pro Node | ~28.332 Mi (~27,7 Gi) | ✅ Live: 28.333 Mi | ✅ BESTÄTIGT |
| DEV+TEST Total Allocatable RAM | ~56,6 Gi | Live: ~55,3 Gi | ⚠️ MINOR — Rundungsfehler (~56.666 Mi ≠ 56,6 Gi sondern 55,3 Gi) |
| DEV Pods: 16 | ✅ Live: 16 (inkl. redis-operator) | ✅ BESTÄTIGT |
| TEST Pods: 15 | ✅ Live: 15 | ✅ BESTÄTIGT |
| PROD Pods: 19 | ✅ Live: 19 (inkl. redis-operator) | ✅ BESTÄTIGT |
| DEV+TEST Kosten | 868,47 EUR/Mo | ✅ StackIT Preisliste | ✅ BESTÄTIGT |
| PROD Kosten | 963,96 EUR/Mo | ✅ StackIT Preisliste | ✅ BESTÄTIGT |
| CPU Auslastung DEV+TEST | ~5% (813m/15.820m, 2026-03-06) | Live 2026-03-16: 5,8% (930m) | ✅ BESTÄTIGT (konsistent) |
| RAM Auslastung DEV+TEST | ~28% (2026-03-06) | Live 2026-03-16: 31,7% | ✅ BESTÄTIGT (leicht gestiegen) |
| PG DEV Flex 2.4 Single | 2 CPU, 4 GB, 20 GB | ✅ Terraform bestätigt | ✅ BESTÄTIGT |
| PG PROD Flex 4.8 HA 3-Node | 4 CPU, 8 GB, 50 GB | ✅ Terraform bestätigt | ✅ BESTÄTIGT |

> **Bewertung: Überwiegend korrekt.** Einzige Abweichung: Die Angabe "~56,6 Gi" für Total Allocatable RAM ist vermutlich in Mi gemeint (56.666 Mi = 55,3 Gi). **Empfehlung: Einheit korrigieren oder auf "~55 Gi" ändern.**

### 8.4 ADR-003 (StackIT-Entscheidung)

| Behauptung | Dokumentiert | Verifiziert | Status |
|------------|-------------|-------------|--------|
| StackIT hat BSI C5 Type 2 | ✅ | ✅ Web-Recherche bestätigt | ✅ BESTÄTIGT |
| Hetzner hat kein Managed K8s | ✅ (Stand Feb 2026) | ✅ Weiterhin kein Managed K8s | ✅ BESTÄTIGT |
| AWS/Azure unterliegen CLOUD Act | ✅ | ✅ Juristisch korrekt | ✅ BESTÄTIGT |
| DEV+TEST ~868 EUR/Mo | ✅ | ✅ Verifiziert | ✅ BESTÄTIGT |
| Hetzner hat kein BSI C5 | ❌ | Hetzner hat BSI C5 seit 2024 | ❌ VERALTET |

> **Bewertung:** ADR-003 ist fundiert und die Kernargumente bleiben valide. Die Aussage zu Hetzner und BSI C5 ist **veraltet** — Hetzner hat seit 2024 BSI C5 Zertifizierung. Dies ändert nichts an der Gesamtentscheidung (Hetzner hat weiterhin kein Managed K8s/PG), sollte aber aktualisiert werden.

### 8.5 ADR-005 (Node-Upgrade)

| Behauptung | Dokumentiert | Verifiziert | Status |
|------------|-------------|-------------|--------|
| g1a.4d reicht nicht für 8 Celery Worker | ⚠️ | ⚠️ Stimmt für aktuelle Requests, nicht für tatsächliche Nutzung | ⚠️ NUANCIERT |
| 2x g1a.8d: 5% CPU, 28% RAM | ✅ | Live 2026-03-16: 5,8% CPU, 31,7% RAM | ✅ BESTÄTIGT |
| 2x g1a.8d: 566,36 EUR/Mo | ✅ | ✅ Verifiziert | ✅ BESTÄTIGT |
| 2x g1a.8d reicht für 150 User | ✅ (geschätzt) | NICHT VERIFIZIERT (keine reale Last) | ⚠️ NICHT LIVE VERIFIZIERT |

> **Bewertung:** ADR-005 war zum Zeitpunkt der Entscheidung korrekt. Die Erkenntnis, dass Resource Requests 10-16x über der tatsächlichen Nutzung liegen, war damals noch nicht bekannt. **Mit optimierten Requests wäre ein Rück-Downgrade auf g1a.4d für DEV/TEST möglich.**

### 8.6 prod-bereitstellung.md (Section 11: Resource-Tabelle)

| Behauptung | Dokumentiert | Live-Deployed | Status |
|------------|-------------|---------------|--------|
| API Server CPU Request | 1000m | 500m | ❌ FALSCH — deployed ist 50% des dokumentierten Werts |
| API Server CPU Limit | 2000m | 1000m | ❌ FALSCH |
| API Server RAM Request | 1024 Mi | 512 Mi | ❌ FALSCH |
| Web Server CPU Request | 500m | 250m | ❌ FALSCH |
| Web Server RAM Request | 512 Mi | 256 Mi | ❌ FALSCH |
| Celery Primary CPU Request | 1000m | 500m | ❌ FALSCH |
| Celery Primary RAM Request | 2048 Mi | 1 Gi (1024 Mi) | ❌ FALSCH |
| Vespa CPU Request | 2000m | 2000m | ✅ BESTÄTIGT |
| Vespa RAM Request | 4096 Mi | 4 Gi | ✅ BESTÄTIGT |
| Total CPU Requests | 8750m | ~8.450m (ohne NGINX/Redis-Op) | ⚠️ LEICHT ABWEICHEND |
| Total RAM Requests | ~15,25 Gi | ~14,75 Gi | ⚠️ LEICHT ABWEICHEND |

> **Bewertung: ERHEBLICHE DISKREPANZ.** Die dokumentierten Resource-Werte in Section 11 sind systematisch ~2x höher als die tatsächlich deployed Werte (values-prod.yaml). Die Dokumentation zeigt geplante, nie implementierte Werte. **Empfehlung: Section 11 an die tatsächlichen `values-prod.yaml`-Werte anpassen.**

### 8.7 kostenoptimierung-dev-test.md

| Behauptung | Dokumentiert | Verifiziert | Status |
|------------|-------------|-------------|--------|
| Parking-Option A spart ~302 EUR/Mo | ✅ (basierend auf g1a.4d) | Preise korrekt, aber Baseline veraltet | ⚠️ BASELINE VERALTET — basiert auf g1a.4d (585 EUR), aktuell g1a.8d (868 EUR). Einsparung wäre HÖHER. |
| Restore-Zeit ~15 Min | ✅ | Plausibel für Node-Scale-Up | ✅ PLAUSIBEL |

> **Bewertung:** Konzeptionell valide, aber alle Kostenberechnungen basieren auf dem alten g1a.4d-Pricing. Mit g1a.8d wäre die Einsparung durch Parking deutlich höher (~450 EUR/Mo statt ~302 EUR/Mo). **Empfehlung: Zahlen auf g1a.8d-Basis aktualisieren.**

### 8.8 kostenvergleich-node-upgrade.md / .pdf

| Behauptung | Dokumentiert | Verifiziert | Status |
|------------|-------------|-------------|--------|
| IST DEV+TEST (g1a.4d) | 585,29 EUR/Mo | ✅ Historisch korrekt | ✅ BESTÄTIGT (historisch) |
| SOLL DEV+TEST (g1a.8d) | 868,47 EUR/Mo | ✅ Live bestätigt | ✅ BESTÄTIGT |
| PROD (geplant) | 963,96 EUR/Mo | ✅ Live bestätigt | ✅ BESTÄTIGT |
| Alle StackIT Preise | Verifiziert-Label im Dokument | ✅ Gegen aktuelle Preisliste geprüft | ✅ BESTÄTIGT |

> **Bewertung: Korrekt und gut dokumentiert.** Einziger Kritikpunkt: "Offene Posten" (Block Storage, Container Registry) wurden nie nachträglich ergänzt.

---

## 9. Offene Fragen

| # | Frage | Kontext | Wer klärt |
|---|-------|---------|-----------|
| 1 | Was kostet StackIT Block Storage pro GB/Mo? | Nicht öffentlich dokumentiert, relevant für PVC-Kosten (5x 20-50 Gi) | StackIT Support / Preisrechner |
| 2 | Wann wird Container Registry kostenpflichtig (Beta → GA)? | Aktuell 0 EUR, wird sich ändern | StackIT Roadmap |
| 3 | Bietet StackIT Reserved Instances / Savings Plans? | Könnte 10-20% Rabatt auf Compute bringen | StackIT Sales |
| 4 | Wie hoch ist die PROD-Last bei 150 aktiven Usern? | Aktuelle 3,7% CPU sind Idle-Werte ohne reale Last | 3 Monate PROD-Betrieb abwarten |
| 5 | Kann Celery Monitoring Worker deaktiviert werden? | Potenziell redundant mit kube-prometheus-stack | Onyx Upstream-Doku prüfen |
| 6 | VÖB: Ist TEST 24/7 erforderlich oder reicht on-demand? | Einsparung ~200 EUR/Mo | Abstimmung mit VÖB |
| 7 | Stimmt die SSOT-Angabe "~56,6 Gi" als RAM-Gesamtwert? | Berechnung ergibt ~55,3 Gi oder ~56.666 Mi — Einheitenfehler | Niko (Korrektur in SSOT) |

---

## Anhang A: Vollständige Live-Daten (2026-03-16)

### A.1 DEV+TEST Cluster — Node-Auslastung
```
NAME                                                    CPU(cores)   CPU(%)   MEMORY(bytes)   MEMORY(%)
shoot--vob-chatbot-devtest-z1-6f8c4-g25tg               473m         5%       8669Mi          30%
shoot--vob-chatbot-devtest-z1-6f8c4-tddnn               457m         5%       9730Mi          34%
```

### A.2 PROD Cluster — Node-Auslastung
```
NAME                                              CPU(cores)   CPU(%)   MEMORY(bytes)   MEMORY(%)
shoot--vob-prod-prod-z1-6c786-cz9jh               304m         3%       7806Mi          27%
shoot--vob-prod-prod-z1-6c786-ntd4p               277m         3%       4854Mi          17%
```

### A.3 PVC-Auslastung
```
Vespa DEV:    20 Gi provisioned,  927 Mi used (4,5%)
Vespa TEST:   20 Gi provisioned,  911 Mi used (4,4%)
Vespa PROD:   50 Gi provisioned,  884 Mi used (1,7%)
Prometheus:   20 Gi provisioned, 2,3 Gi used (11,8%) [DEV+TEST]
Prometheus:   50 Gi provisioned, 1,1 Gi used (2,2%)  [PROD]
```

### A.4 PROD Pod-Level Ressourcen
```
Pod                         CPU Actual  RAM Actual  CPU Req    RAM Req
da-vespa-0                  189m        3143Mi      2000m      4Gi
api-server (×2)             2m          504Mi       500m       512Mi
celery-primary (×2)         12m         269Mi       500m       1Gi
inference-model             1m          278Mi       500m       1Gi
indexing-model              2m          279Mi       500m       1Gi
celery-light                10m         249Mi       500m       1Gi
celery-heavy                10m         220Mi       500m       1Gi
celery-user-file            9m          203Mi       500m       512Mi
celery-docfetching          10m         192Mi       500m       1Gi
celery-docprocessing        10m         192Mi       500m       1Gi
celery-monitoring           11m         170Mi       250m       256Mi
celery-beat                 13m         160Mi       250m       512Mi
nginx-controller            2m          112Mi       100m       90Mi
web-server (×2)             1m          64Mi        250m       256Mi
redis-operator              5m          33Mi        500m       500Mi
redis (onyx-prod-0)         6m          12Mi        250m       512Mi
```
