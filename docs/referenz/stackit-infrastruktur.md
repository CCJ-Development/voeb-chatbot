# StackIT Infrastruktur — Technische Referenz

**Stand**: März 2026
**Region**: EU01 (Frankfurt)
**Provider**: StackIT (Schwarz Digits / Schwarz-Gruppe)

> Dieses Dokument enthält ausschließlich technische Spezifikationen.
> Preise und Kostenschätzungen liegen in separaten Dokumenten (nicht im Repository).

---

## Cluster-Architektur

### Kubernetes (SKE — STACKIT Kubernetes Engine)

| Parameter | Wert |
|-----------|------|
| Cluster | 2 (`vob-chatbot`: DEV+TEST shared, `vob-prod`: PROD eigener Cluster, ADR-004) |
| Kubernetes-Version | DEV/TEST: v1.33.8, PROD: v1.33.9 |
| Namespaces | `onyx-dev`, `onyx-test` (shared Cluster), `onyx-prod` (eigener Cluster) |
| Ingress Controller | NGINX via Essential Network Load Balancer (NLB-10) |
| TLS | Let's Encrypt via cert-manager (v1.19.4), LIVE seit 2026-03-09. ECDSA P-384, TLSv1.3, HTTP/2. DNS-01 via Cloudflare, ACME-Challenge CNAME-Delegation ueber GlobVill |
| Network Policies | IMPLEMENTIERT (SEC-03): DEV 7 Policies, PROD 7 Policies (Zero-Trust, seit 2026-03-24), Monitoring 13 Policies, cert-manager 6 Policies |

### Worker Nodes (Compute Engine g1a-Serie, AMD, kein Overprovisioning)

| Environment | Node-Typ | vCPU | RAM | Anzahl | Pool |
|-------------|----------|------|-----|--------|------|
| DEV + TEST | g1a.4d | 4 | 16 GB | 2 (1 pro Env) | `devtest` |
| PROD (dedicated) | g1a.8d | 8 | 32 GB | 2 (bei Bedarf 3) | eigener Cluster |

**DEV+TEST allokierbare Kapazitaet (2x g1a.4d):** ~7.4 CPU / ~26 Gi RAM — je ~3.7 CPU / ~13 Gi pro Env
**PROD allokierbare Kapazitaet (2x g1a.8d):** ~15.8 CPU / ~56.6 Gi RAM
**PROD geschaetzte Auslastung:** CPU ~55% Requests / ~62% mit Monitoring, RAM ~27% Requests / ~30% mit Monitoring (bei 150 Usern, basierend auf values-prod.yaml PROD-Requests)

> **Entscheidung (ADR-004):** Eigene Nodes pro Umgebung statt geteilter Node.
> Begründung: CPU-Isolation, Ausfallsicherheit, Enterprise-Standard.

> **Upgrade (ADR-005):** g1a.4d → g1a.8d seit 2026-03-06 (8 separate Celery-Worker nach Upstream PR #9014).
> **Downgrade DEV+TEST (2026-03-16):** g1a.8d → g1a.4d (Kostenoptimierung). PROD bleibt g1a.8d.

---

## PostgreSQL (Flex — Managed Database)

| Environment | Konfiguration | vCPU | RAM | HA |
|-------------|---------------|------|-----|-----|
| DEV | Flex 2.4 Single | 2 | 4 GB | Nein |
| TEST | Flex 2.4 Single | 2 | 4 GB | Nein |
| PROD | Flex 4.8 Replica | 4 | 8 GB | Ja (3-Node Set) |

**Disk Performance:** Premium Performance Tier 2 (`premium-perf2-stackit`, SSD-level IOPS), 1 Disk pro Node
**Backup:** PostgreSQL PITR (automatisch), Object Storage für Backup-Daten
**PROD-Besonderheit:** 3-Node Replica Set (Primary + 2 Standby) als ein verwaltetes Set

**Managed PG Einschränkungen:**
- Kein `CREATEROLE` / `SUPERUSER` für App-User
- User-Verwaltung ausschließlich über StackIT API (Terraform)
- Datenbank muss manuell angelegt werden (Terraform erstellt nur Instanz + User)
- Details: [PostgreSQL Runbook](../runbooks/stackit-postgresql.md)

---

## Storage

| Typ | Zweck | Technologie |
|-----|-------|-------------|
| Object Storage | Dokumente, Uploads, Connector-Daten, Backups | S3-kompatibel |
| Block Storage SSD | K8s PersistentVolumeClaims, OpenSearch-Indizes + Vespa (Zombie-Mode) | Premium Performance Tier 2 (`premium-perf2-stackit`) |

**Buckets (Object Storage):** `vob-dev`, `vob-test`, `vob-prod`
**PROD Backups:** PG PITR + Object Store Versioning

---

## Netzwerk

| Komponente | Spezifikation |
|------------|---------------|
| Load Balancer | Essential Network Load Balancer (NLB-10) |
| Public IP | 1× IPv4 (Floating IP für Ingress) |
| Egress/Traffic | Derzeit nicht separat bepreist bei StackIT |
| DNS | Nicht enthalten — über bestehende Client-Infrastruktur |

---

## LLM / AI Model Serving (StackIT-hosted)

| Modell | StackIT Model ID | Verwendung | Status |
|--------|------------------|------------|--------|
| GPT-OSS 120B | `openai/gpt-oss-120b` | Chat (primaer), 131K Kontext | ✅ Verifiziert (DEV + TEST) |
| Qwen3-VL 235B | `Qwen/Qwen3-VL-235B-A22B-Instruct-FP8` | Chat + Vision/OCR, 218K Kontext | ✅ Verifiziert (DEV + TEST) |
| Llama 3.3 70B | `cortecs/Llama-3.3-70B-Instruct-FP8-Dynamic` | Chat, 128K Kontext | ✅ Verifiziert (TEST, 2026-03-08) |
| Llama 3.1 8B | `neuralmagic/Meta-Llama-3.1-8B-Instruct-FP8` | Chat (leichtgewichtig), 128K Kontext | ✅ Verifiziert (TEST, 2026-03-08) |
| Qwen3-VL-Embedding 8B | `Qwen/Qwen3-VL-Embedding-8B` | Embedding (multilingual, 32k Context, 4096 Dim) | ✅ Aktiv (DEV seit 2026-03-12, TEST seit 2026-03-08) |

**Nicht kompatibel mit Onyx** (kein Tool Calling auf StackIT vLLM): `google/gemma-3-27b-it` (Gemma 3 27B), `neuralmagic/Mistral-Nemo-Instruct-2407-FP8` (Mistral-Nemo 12B). Details: [LLM-Runbook](../runbooks/llm-konfiguration.md#chat-modelle--nicht-kompatibel-mit-onyx).

**Wichtig:** LLM laeuft auf StackIT AI Model Serving (OpenAI-kompatible API, vLLM-Backend) — kein OpenAI, keine Daten verlassen Deutschland.

---

## PROD Sizing Detail (80–100 gleichzeitige Nutzer)

### Onyx-Komponenten Resource Requests

| Komponente | CPU Request | RAM Request | Replicas |
|------------|------------|-------------|----------|
| Backend API (FastAPI) | 500m | 512 Mi | 2–3 |
| Frontend (Next.js) | 250m | 256 Mi | 2 |
| Background Worker (Celery Beat) | 250m | 512 Mi | 1 |
| Background Worker (Primary) | 500m | 1 Gi | 2 |
| Background Worker (Light) | 500m | 1 Gi | 1 |
| Background Worker (Heavy) | 500m | 1 Gi | 1 |
| Background Worker (DocFetching) | 500m | 1 Gi | 1 |
| Background Worker (DocProcessing) | 500m | 1 Gi | 1 |
| Background Worker (Monitoring) | 250m | 256 Mi | 1 |
| Background Worker (User File) | 500m | 512 Mi | 1 |
| Redis | 250m | 512 Mi | 1 |
| OpenSearch (primaerer Document Index) | 1000m | 2 Gi | 1 |
| Vespa (Zombie-Mode, kein aktiver Betrieb) | 100m | 512 Mi | 1 |
| System-Overhead (kube-system) | ~1.4 CPU | ~2 Gi | — |
| **TOTAL PROD** | **~8.6-9.1 CPU** | **~16-17 Gi** | — |

### Skalierung

- 2× g1a.8d Worker Nodes decken den erwarteten Bedarf
- Bei Lastspitzen: 3. Node hinzufügen (HPA-ready)
- OpenSearch als primaeres Document Index Backend (DEV + PROD aktiv)
- Vespa im Zombie-Mode (minimale Ressourcen, kein aktiver Betrieb mehr)
- Redis als In-Cluster Pod (kein Managed Redis notwendig)

---

## Environments-Übersicht

| Aspekt | DEV | TEST | PROD |
|--------|-----|------|------|
| Namespace | `onyx-dev` | `onyx-test` | `onyx-prod` (eigener Cluster `vob-prod`, deployed 2026-03-11) |
| Cluster | shared (`vob-chatbot`) | shared (`vob-chatbot`) | **eigener Cluster** (ADR-004) |
| Worker Nodes | eigener Node (g1a.4d) | eigener Node (g1a.4d) | 2× g1a.8d dedicated |
| PostgreSQL | Flex 2.4 Single (`vob-dev`) | Flex 2.4 Single (`vob-test`) | Flex 4.8 Replica (3 Nodes HA) |
| Object Storage | `vob-dev` | `vob-test` | `vob-prod` |
| OpenSearch | In-Cluster (1 Replica) | In-Cluster (1 Replica) | In-Cluster (1 Replica) |
| Vespa | In-Cluster (Zombie-Mode) | In-Cluster (Zombie-Mode) | In-Cluster (Zombie-Mode) |
| Redis | In-Cluster Pod | In-Cluster Pod | In-Cluster Pod |
| LLM | StackIT AI Serving | gleich | gleich + Monitoring |
| Backups | PG PITR (auto) | PG PITR (auto) | PG PITR + ObjStore Versioning |
| Resource Quotas | Entfernt (DEV) | Entfernt (TEST) | CPU: 12, RAM: 20 Gi (berechnet: 8.75 CPU Requests + 37% Buffer, 15.25 Gi RAM Requests + 31% Buffer) |
| Network Policy | Implementiert (SEC-03, 7 Policies) | Implementiert (SEC-03) | monitoring-NS: 13 Policies (2026-03-24). onyx-prod: 7 Policies (Zero-Trust, seit 2026-03-24) |

### DNS

| Environment | Domain | IP | Status |
|-------------|--------|-----|--------|
| DEV | `dev.chatbot.voeb-service.de` | `188.34.118.222` | A-Record aktualisiert (2026-03-22, LB-IP nach Helm-Neuinstallation 2026-03-18) |
| TEST | `test.chatbot.voeb-service.de` | `188.34.118.201` | A-Record gesetzt (2026-03-05) |
| PROD | `chatbot.voeb-service.de` | `188.34.92.162` | **HTTPS LIVE** (2026-03-17), Let's Encrypt ECDSA P-384, TLSv1.3, HTTP/2, HSTS 1 Jahr |

Cloudflare: DNS-only (kein Proxy). TLS DEV/TEST: LIVE seit 2026-03-09. TLS PROD: LIVE seit 2026-03-17. cert-manager (v1.19.4), DNS-01 via Cloudflare API, ACME-Challenge CNAME-Delegation ueber GlobVill. ECDSA P-384, TLSv1.3, HTTP/2. Auto-Renewal aktiv.

---

## Token-Kalkulation (Sizing-Annahmen)

| Parameter | DEV | Erwartet (80 User) | Peak (100 User) |
|-----------|-----|---------------------|------------------|
| Aktive Nutzer/Tag | 5 | 80 | 100 |
| Queries/Nutzer/Tag | 5 | 10 | 15 |
| Arbeitstage/Monat | 22 | 22 | 22 |
| Ø Input-Tokens/Query | 3.000 | 4.000 | 5.000 |
| Ø Output-Tokens/Query | 500 | 750 | 1.000 |
| **Queries/Monat** | 550 | 17.600 | 33.000 |
| **Input-Tokens/Monat** | 1,65 Mio | 70,4 Mio | 165 Mio |
| **Output-Tokens/Monat** | 0,28 Mio | 13,2 Mio | 33 Mio |

---

## Nicht enthalten (optional hinzubuchbar)

- **Observability/Logging:** Self-hosted kube-prometheus-stack (deployed 2026-03-10 DEV/TEST, 2026-03-12 PROD). StackIT LogMe nicht genutzt
- **DNS-Zone:** 1,92 EUR/Monat — ggf. über bestehende VÖB-Infrastruktur
- **WAF/DDoS:** Abhängig von StackIT-Angebot

---

## Quellen

- StackIT Pricing API (`pim.api.stackit.cloud`), Stand Februar 2026
- Kostenaufstellung und Architecture Sizing: Coffee Studios (intern, nicht im Repository)
