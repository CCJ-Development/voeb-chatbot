# Technische Parameter — Single Source of Truth

> Alle technischen Spezifikationen an EINER Stelle. Andere Dokumente verweisen hierher.
> Letzte Aktualisierung: 2026-03-25

---

## 1. Umgebungen

| Parameter | DEV | PROD |
|-----------|-----|------|
| Cluster | vob-chatbot | vob-prod (eigener, ADR-004) |
| Namespace | onyx-dev | onyx-prod |
| K8s Version | v1.33.9 | v1.33.9 |
| Flatcar | 4459.2.3 | 4459.2.3 |
| Node Pool | devtest (2x g1a.4d) | prod (2x g1a.8d) |
| Node Specs | 4 vCPU, 16 GB RAM, 100 GB Disk | 8 vCPU, 32 GB RAM, 100 GB Disk |
| Allocatable (gesamt) | ~7.400m CPU, ~28 Gi RAM | 15.820m CPU, ~55 Gi RAM (56.666 Mi) |
| Pods | 17 | 20 (inkl. OpenSearch, seit 2026-03-22) |
| API Replicas | 1 | 2 (HA) |
| Web Replicas | 1 | 2 (HA) |
| Celery Worker | 8 (Standard Mode, 7 Worker + 1 Beat) | 8 |
| IngressClass | nginx | nginx |
| URL | https://dev.chatbot.voeb-service.de | https://chatbot.voeb-service.de |
| HTTPS | **LIVE** (seit 2026-03-22, DNS A-Record 188.34.118.222) | **LIVE** (2026-03-17) — Let's Encrypt ECDSA P-384, TLSv1.3, HTTP/2 |
| Auth | oidc (Entra ID, seit 2026-03-23) | oidc (Entra ID, seit 2026-03-24) |
| Deploy-Trigger | Push auf main (auto) | workflow_dispatch (manuell, Required Reviewer) |
| Status | LIVE seit 2026-02-27 | **HTTPS LIVE** seit 2026-03-17 (deployed 2026-03-11) |
| Deployment-Strategie | Recreate | Recreate |

**TEST-Umgebung:** Seit 2026-04-21 **vollstaendig abgebaut** (Helm Release, Namespace, PostgreSQL Flex `vob-test`, Object Storage Bucket `vob-test` via StackIT CLI + kubectl + Terraform state rm geloescht). Die Konfigurations-Artefakte (`deployment/terraform/environments/test/`, `deployment/helm/values/values-test.yaml`, `deploy-test`-Workflow-Job) bleiben als Template-Blueprint im Repo fuer Kunden-Klon-Projekte und eventuelle Reaktivierung. Reaktivierungs-Anleitung im Header von `environments/test/main.tf`.

Historisch: TEST war LIVE von 2026-03-03 bis 2026-03-19 (15 Pods), dann Compute-seitig auf 0 Replicas (Managed Services liefen weiter bis 2026-04-21).

---

## 2. Netzwerk & DNS

| Parameter | Wert |
|-----------|------|
| Domain | voeb-service.de |
| Subdomain | chatbot (festgelegt durch VoeB, Mail Leif Rasch, 2026-03-04) |
| Authoritative NS | GlobVill (dns.voerde.globvill.de, dns.globvill.de, dns.globvill.ruhr) |
| DNS Provider | Cloudflare (DNS-only, kein Proxy, Pro-Plan) |
| DNS-Aufloesungskette | GlobVill CNAME -> *.voeb-service.de.cdn.cloudflare.net -> Cloudflare A-Record -> StackIT LB IP |
| LB DEV | **188.34.118.222** (DNS aktualisiert 2026-03-22 durch Leif/GlobVill) |
| LB TEST | (abgebaut 2026-04-21; ehemals 188.34.118.201) |
| LB PROD | 188.34.92.162 |
| Egress DEV | 188.34.93.194 (NAT Gateway, fest fuer Cluster-Lifecycle) |
| Egress PROD | 188.34.73.72 |
| TLS Algorithmus | ECDSA P-384 (secp384r1), BSI TR-02102-2 konform |
| TLS Version | TLSv1.3 |
| TLS Cipher | AEAD-AES256-GCM-SHA384 / TLS_AES_256_GCM_SHA384 |
| TLS Issuer | Let's Encrypt E8 (ECDSA Intermediate) |
| TLS Chain | Leaf (P-384) -> E8 (P-384) -> ISRG Root X1 (RSA 4096) |
| TLS Laufzeit | 90 Tage (cert-manager Renewal nach 2/3 = ~Tag 60) |
| HTTP-Version | HTTP/2 |
| cert-manager | v1.19.4, DNS-01 via Cloudflare API |
| ClusterIssuers | onyx-dev-letsencrypt, onyx-prod-letsencrypt (beide READY); onyx-test-letsencrypt obsolet seit TEST-Abbau 2026-04-21 |
| ACME Server | https://acme-v02.api.letsencrypt.org/directory (Production) |
| ACME Email | nikolaj.ivanov@coffee-studios.de |
| HSTS DEV | max-age=3600; includeSubDomains (reaktiviert mit HTTPS, 2026-03-22) |
| HSTS TEST | (abgebaut 2026-04-21) |
| HSTS PROD | max-age=31536000; includeSubDomains |
| HTTP-zu-HTTPS Redirect | 308 Permanent Redirect |
| NetworkPolicies DEV | 7 Policies in onyx-dev (SEC-03 + Monitoring-Scrape + Redis-Exporter, seit 2026-03-10) |
| NetworkPolicies PROD | **7 Policies** (Zero-Trust: Default-Deny, DNS, Intra-NS, NGINX Ingress, External Egress, Monitoring Scrape, Redis Exporter. Seit 2026-03-24) |
| NetworkPolicies Monitoring | 13 Policies (Zero-Trust, alle applied. Seit 2026-03-24 vollstaendig) |
| SKE Cluster API ACL | 0.0.0.0/0 (Kubeconfig mit Client-Zertifikat als Schutz) |
| PG ACL DEV | 188.34.93.194/32 + Admin (SEC-01) |
| PG ACL PROD | 188.34.73.72/32 + Admin (SEC-01) |

---

## 3. Datenbank (PostgreSQL Flex)

| Parameter | DEV | PROD |
|-----------|-----|------|
| Instanz-Name | vob-dev | vob-prod |
| Konfiguration | Flex 2.4 Single | Flex 4.8 HA (3-Node Cluster) |
| Specs | 2 CPU, 4 GB RAM, 20 GB SSD | 4 CPU, 8 GB RAM (HA 3 Nodes) |
| PostgreSQL Version | 16 | 16 |
| Datenbank | onyx | onyx |
| User (RW) | onyx_app | onyx_app |
| User (RO) | db_readonly_user | db_readonly_user |
| Port | 5432 | 5432 |
| Verbindung | SSL/TLS (sslmode=require) | SSL/TLS |
| Backup | Taeglich 02:00 UTC, 30 Tage | Taeglich 01:00 UTC, 30 Tage, PITR sekundengenau (Flex 4.8 HA) |
| Encryption at Rest | AES-256 (StackIT Default) | AES-256 |
| Lifecycle Protection | prevent_destroy = true (Terraform) | prevent_destroy = true |
| User-Rollen | login, createdb | login, createdb |
| max_connections | 100 (StackIT Default) | 100 |

> PG Flex `vob-test` wurde am 2026-04-21 geloescht (zusammen mit Backups). Template fuer Neuanlage: `deployment/terraform/environments/test/main.tf`.

**Hinweise:**
- StackIT PG Flex erlaubt kein CREATEROLE -- spezielle User per Terraform
- StackIT PG Flex erlaubt kein Patching von User-Rollen (Destroy + Recreate)
- pg_monitor Rolle nicht verfuegbar (nur login + createdb)
- Backups sind instanzgebunden -- nach Loeschung nicht mehr verfuegbar

---

## 4. Object Storage

| Parameter | DEV | PROD |
|-----------|-----|------|
| Bucket | vob-dev | vob-prod |
| Endpoint | object.storage.eu01.onstackit.cloud | (identisch) |
| Encryption | AES-256 (at rest) | AES-256 |
| Versionierung | Unterstuetzt, **nicht aktiviert** | Unterstuetzt, **nicht aktiviert** |
| Versionierung Hinweis | Nicht via Terraform konfigurierbar (StackIT API-Limitation, GH Issue #1048). Aktivierung per `aws s3api put-bucket-versioning` (einmalig pro Bucket). Audit H3. | |

> Bucket `vob-test` wurde am 2026-04-21 geleert und geloescht.

---

## 5. LLM-Konfiguration

| Parameter | DEV | PROD |
|-----------|-----|------|
| Provider | openai-compat (StackIT AI Model Serving) | openai-compat (StackIT AI Model Serving, seit 2026-03-24) |
| API Base | https://api.openai-compat.model-serving.eu01.onstackit.cloud/v1 | (identisch) |
| Chat-Modelle | 4 Modelle (seit 2026-03-08) | 3 Modelle (GPT-OSS 120B, Qwen3-VL 235B, Llama 3.3 70B, seit 2026-03-24) |
| Embedding | Qwen3-VL-Embedding 8B (4096 Dim) | Qwen3-VL-Embedding 8B (4096 Dim, seit 2026-03-24) |

### Chat-Modelle (DEV)

| Modell | Modell-ID |
|--------|-----------|
| GPT-OSS 120B | openai/gpt-oss-120b |
| Qwen3-VL 235B | Qwen/Qwen3-VL-235B-A22B-Instruct-FP8 |
| Llama 3.3 70B | cortecs/Llama-3.3-70B-Instruct-FP8-Dynamic |
| Llama 3.1 8B | neuralmagic/Meta-Llama-3.1-8B-Instruct-FP8 (bei StackIT inzwischen deprecated) |

### Nicht kompatible Modelle (kein Tool Calling auf StackIT vLLM)

| Modell | Grund |
|--------|-------|
| google/gemma-3-27b-it | tool_choice: "auto" wird abgelehnt |
| neuralmagic/Mistral-Nemo-Instruct-2407-FP8 | tool_choice: "auto" wird abgelehnt |

---

## 5b. Document Index

> **Hintergrund:** Onyx migriert von Vespa zu OpenSearch (seit v3.0.0). Vollstaendige Analyse: `docs/analyse-opensearch-vs-vespa.md`.

### Architektur (Stand v3.x)

| Komponente | Rolle | Version | Status |
|------------|-------|---------|--------|
| **OpenSearch** | Primaeres Document Index Backend (Indexing + Retrieval) | 3.4.0 | Aktiv (Upstream-Default seit v3.0.0) |
| **Vespa** | Zombie-Mode (nur fuer Readiness Check, kein aktiver Index-Traffic) | 8.609.39 | Aktiv (MUSS bis v4.0.0 laufen) |

### OpenSearch

| Parameter | DEV | PROD |
|-----------|-----|------|
| Cluster-Name | onyx-opensearch | onyx-opensearch |
| Modus | Single-Node (discovery.type: single-node) | Single-Node |
| CPU Request / Limit | 300m / 1000m | 1000m / 2000m |
| RAM Request / Limit | 1.5Gi / 4Gi | 2Gi / 4Gi |
| JVM Heap | 512m (Docker Compose) | [Helm Default] |
| PVC | 30Gi | 30Gi |
| Port (REST API) | 9200 | 9200 |
| Auth | admin / [Secret] | admin / [Secret] |

### Vespa (Zombie-Mode)

| Parameter | DEV | PROD |
|-----------|-----|------|
| CPU Request / Limit | 50m / 200m | 100m / 500m |
| RAM Request / Limit | 512Mi / 4Gi | 512Mi / 4Gi |
| PVC | 20Gi | 50Gi |
| Port (Application) | 8081 | 8081 |
| Port (Config) | 19071 | 19071 |
| privileged | false (Override, Upstream Default true) | false |
| runAsUser | 0 (Upstream-Limitation: benoetigt Root fuer vm.max_map_count) | 0 |

**Vespa Einschraenkungen (KRITISCH):**
- **Memory LIMIT >= 4 Gi Pflicht:** Vespa-Container prueft beim Start ob memory LIMIT >= 4 Gi (Hard-Check). Pod startet nicht bei niedrigerem Limit. `requests` koennen niedriger sein.
- **StatefulSet PVC immutable:** `volumeClaimTemplates` koennen in Kubernetes NICHT per Helm geaendert werden. Bei PVC-Groessenaenderung: StatefulSet + PVC manuell loeschen, neu erstellen. Daten gehen verloren.
- **`vespa.enabled: true` Pflicht (bis v4.0.0):** v3.x Code prueft Vespa-Erreichbarkeit (`wait_for_vespa_or_shutdown` in `app_base.py:517`). Ohne Vespa-Pod crashen alle Celery-Worker.

---

## 6. Monitoring

### 6.1 Stack

| Parameter | Wert |
|-----------|------|
| Stack | Self-Hosted kube-prometheus-stack (Entscheidung Niko, 2026-03-10) |
| Chart | prometheus-community/kube-prometheus-stack |
| Helm Release | monitoring (separater Release, nicht im Onyx Chart) |
| Namespace | monitoring |
| Cross-Cluster | Nein -- jeder Cluster hat eigenen Stack |
| Zugang Grafana | kubectl port-forward (kein Ingress, Enterprise Best Practice) |
| Maintenance-Aufwand | ~2h/Quartal (incl. Helm Upgrade ~30 Min) |

### 6.2 Pods

| Umgebung | Pods im monitoring NS |
|----------|-----------------------|
| DEV (Cluster vob-chatbot) | 9 (7 Basis + 2 Exporter) |
| PROD (Cluster vob-prod) | 9 (7 Basis + 2 Exporter) |

**Basis-Pods (7):** Prometheus, Grafana, AlertManager, kube-state-metrics, 2x node-exporter (DaemonSet), prometheus-operator

**Exporter DEV:** pg-exporter-dev, redis-exporter-dev

**Exporter PROD:** pg-exporter-prod, redis-exporter-prod

> Bis 2026-04-21 lief zusaetzlich pg-exporter-test + redis-exporter-test im monitoring NS. Diese wurden mit dem TEST-Abbau entfernt.

### 6.3 Scrape & Retention

| Parameter | DEV | PROD |
|-----------|-----|------|
| Scrape-Intervall | 30s | 30s |
| Scrape-Targets | 6 | 3 (onyx-api-prod, postgres-prod, redis-prod) |
| Retention | 30d | 90d |
| Retention Size | 15 GB | 40 GB |
| PVC | 20 Gi (ReadWriteOnce) | 50 Gi |

### 6.4 Alerting

| Parameter | DEV | PROD |
|-----------|-----|------|
| Kanal | Microsoft Teams Webhook | Microsoft Teams (separater PROD-Kanal) |
| Receiver | teams-niko | teams-prod |
| Alert-Prefix | -- | [PROD] |
| Alert-Rules | 20 | 22 (20 Basis + 2 Backup-Check, mit Mindest-Traffic Guards) |
| send_resolved | true | true |
| group_wait | 30s | 30s |
| group_interval | 5m | 5m |
| repeat_interval | 4h (Critical: 1h) | 4h (Critical: 1h) |

### 6.5 Monitoring-Ressourcen (Requests/Limits)

| Komponente | CPU Req/Lim | RAM Req/Lim | Hinweis |
|------------|-------------|-------------|---------|
| Prometheus | 500m / 1000m | 1 Gi / 2 Gi | |
| Grafana | 100m / 250m | 256 Mi / 512 Mi | |
| AlertManager | 100m / 200m | 128 Mi / 256 Mi | |
| kube-state-metrics | 100m / 200m | 128 Mi / 256 Mi | |
| node-exporter (x2) | 100m / 200m | 128 Mi / 256 Mi | PROD: 150m / 500m |
| prometheus-operator | 100m / 200m | 128 Mi / 256 Mi | |
| postgres_exporter | 50m / 100m | 64 Mi / 128 Mi | PROD: 100m / 250m |
| redis_exporter | 25m / 50m | 32 Mi / 64 Mi | PROD: 50m / 150m |
| **Summe (DEV)** | **1.100m** | **~1,9 Gi** | |

### 6.6 Exporter-Ports

| Exporter | Port | Image |
|----------|------|-------|
| postgres_exporter | 9187 | quay.io/prometheuscommunity/postgres-exporter:v0.19.1 |
| redis_exporter | 9121 | oliver006/redis_exporter:v1.82.0 |

### 6.7 Health Probes (Onyx)

| Komponente | Typ | Endpoint | Readiness | Liveness |
|------------|-----|----------|-----------|----------|
| API Server | httpGet | /health:8080 | 30s + 6x10s = 90s | 60s + 8x15s = 180s |
| Webserver | tcpSocket | :3000 | 20s + 6x10s = 80s | 30s + 5x15s = 105s |

**Hinweis:** Next.js Webserver hat keinen HTTP Health-Endpoint -- daher tcpSocket.

### 6.8 Dashboards

| Dashboard | Grafana ID | Persistenz |
|-----------|------------|------------|
| PostgreSQL | 14114 (Fallback: 9628) | DEV: manuell (nicht persistent). PROD: Sidecar |
| Redis | 763 | DEV: manuell (nicht persistent). PROD: Sidecar |
| Kubernetes Cluster | 6417 | -- |
| Kubernetes Pods | 15760 | -- |
| NGINX Ingress | 9614 | -- |
| Onyx API (Custom) | -- | 6 Panels: Request Rate, Latency, Error Rate, Slow Requests, DB Pool, DB Hold Time |

---

## 7. Kosten (netto, zzgl. MwSt.)

### 7.1 DEV (Cluster vob-chatbot)

| Posten | Anzahl | EUR/Mo (je) | EUR/Mo (gesamt) |
|--------|--------|-------------|-----------------|
| SKE Cluster Management Fee | 1 | 71,71 | 71,71 |
| Worker Node g1a.4d | 2 | 141,59 | 283,18 |
| PostgreSQL Flex 2.4 Single | 1 | 105,54 | 105,54 |
| Object Storage Bucket | 1 | 0,27 | 0,27 |
| Load Balancer Essential-10 | 1 | 9,39 | 9,39 |
| **Gesamt DEV** | | | **470,09** |

### 7.2 PROD (Cluster vob-prod, eigener)

| Posten | Anzahl | EUR/Mo (je) | EUR/Mo (gesamt) |
|--------|--------|-------------|-----------------|
| SKE Cluster Management Fee | 1 | 71,71 | 71,71 |
| Worker Node g1a.8d | 2 | 283,18 | 566,36 |
| PostgreSQL Flex 4.8 Replica (HA 3-Node) | 1 | 316,23 | 316,23 |
| Object Storage Bucket | 1 | 0,27 | 0,27 |
| Load Balancer Essential-10 | 1 | 9,39 | 9,39 |
| **Gesamt PROD** | | | **963,96** |

### 7.3 Gesamtkosten

| Posten | EUR/Mo |
|--------|--------|
| DEV | 470,09 |
| PROD | 963,96 |
| **Gesamt alle aktiven Environments** | **1.434,05** |

**Historie der Kosten-Aenderungen:**
- **2026-03-16:** DEV+TEST Node-Downgrade g1a.8d → g1a.4d (von 868,47 auf 585,29 EUR/Mo). Details: `audit-output/kostenoptimierung-ergebnis.md`.
- **2026-03-19:** TEST auf 0 Pods skaliert (Compute-Kosten entfallen, Managed-Services liefen noch ~115 EUR/Mo).
- **2026-04-21:** **TEST-Live-Infrastruktur vollstaendig abgebaut** — PostgreSQL Flex `vob-test`, Object Storage Bucket `vob-test` und Load Balancer geloescht via StackIT CLI. Einsparung: ~115 EUR/Mo. Template-Code bleibt im Repo fuer Reaktivierung / Klon-Projekte.

**Geplanter PROD-Node-Downgrade** (g1a.8d → g1a.4d): reduziert PROD um ca. 283 EUR auf ~681 EUR/Mo. Gesamt danach: ~1.151 EUR/Mo.

**Nicht enthalten:** Block Storage (Vespa + OpenSearch PVCs pro Environment), StackIT Container Registry, StackIT AI Model Serving (nutzungsabhaengig). PG-Backups sind im PG-Flex-Preis enthalten.

**Preisquelle:** StackIT Preisliste v1.0.36 (03.03.2026). Alle Preise netto.

---

## 8. Versionen

| Komponente | Version | Hinweis |
|------------|---------|---------|
| Kubernetes DEV | v1.33.9 | Flatcar 4459.2.3 |
| Kubernetes PROD | v1.33.9 | Flatcar 4459.2.3 |
| PostgreSQL | 16 | StackIT Managed Flex |
| Redis | 7.0.15 | In-Cluster, OT Operator |
| OpenSearch | 3.4.0 | In-Cluster, primaeres Document Index Backend |
| Vespa | 8.609.39 | In-Cluster, Zombie-Mode (nur Readiness Check, wird in v4.0.0 entfernt) |
| Python | 3.11 | Backend |
| FastAPI | 0.133.1 | |
| SQLAlchemy | 2.0.15 | |
| Alembic | 1.10.4 | |
| Pydantic | 2.11 | |
| Celery | 5.5.1 | |
| LiteLLM | 1.81.6 | |
| Next.js | 16.1.6 | Frontend |
| React | 19.2.4 | |
| TypeScript | 5.9 | |
| Tailwind CSS | 3.4 | |
| Helm | v3.16.0 | |
| Terraform Provider | stackitcloud/stackit ~> 0.80 | |
| cert-manager | v1.19.4 | Behebt CVE-2026-24051, CVE-2025-68121 |
| postgres_exporter | v0.19.1 | quay.io/prometheuscommunity/postgres-exporter |
| redis_exporter | v1.82.0 | oliver006/redis_exporter |
| Onyx Model Server | v2.9.8 | Docker Hub Upstream (onyxdotapp/onyx-model-server) |
| Onyx Chart | READ-ONLY | Nicht veraendern |
| kube-prometheus-stack | [Zu verifizieren] | prometheus-community Helm Chart |

---

## 9. Maintenance Windows

| Cluster | Fenster (UTC) | Typ |
|---------|---------------|-----|
| vob-chatbot (DEV) | 02:00-04:00 | K8s Managed (StackIT, Terraform-konfiguriert) |
| vob-prod (PROD) | 03:00-05:00 | K8s Managed (StackIT, Terraform-konfiguriert) |

**PG Backups:**
- DEV: taeglich 02:00 UTC (`pg_backup_schedule = "0 2 * * *"`)
- PROD: taeglich 01:00 UTC (`pg_backup_schedule = "0 1 * * *"`) — Flex 4.8 HA, WAL-basiert + PITR sekundengenau

**StackIT Service Certificate V1.1 (gueltig ab 12.09.2025):**
- RPO vertraglich: 4 Stunden | RTO vertraglich: 4 Stunden (DB < 500 GB)
- Retention: 30 Tage (Default) | Restore: Self-Service per Clone (kein In-Place)
- Backup-Monitoring: Kundenverantwortung | Kosten: separat (pro GB/h)
- Backups instanzgebunden — bei Instanz-Loeschung unwiederbringlich verloren
- Konzept: `docs/backup-recovery-konzept.md`

---

## 10. Kubeconfig-Ablauf

| Cluster | Gueltig bis | Hinweis |
|---------|-------------|---------|
| vob-chatbot (DEV) | 2026-06-14 | 90-Tage-Rotation |
| vob-prod (PROD) | **2026-06-22** | Erneuert 2026-03-24 (vorherige expired) |

---

## 11. Container Registry

| Parameter | Wert |
|-----------|------|
| Provider | StackIT Container Registry |
| Registry URL | registry.onstackit.cloud |
| Projekt | voeb-chatbot |
| Images | onyx-backend, onyx-web-server |
| Image-Format | registry.onstackit.cloud/voeb-chatbot/onyx-backend:\<sha\> |
| Model Server | onyxdotapp/onyx-model-server:v2.9.8 (Docker Hub, nicht selbst gebaut) |

---

## 12. CI/CD

| Parameter | Wert |
|-----------|------|
| Workflow | .github/workflows/stackit-deploy.yml |
| Build | Parallel (Backend + Frontend), ~8 Min |
| Actions | SHA-gepinnt (Supply-Chain-Sicherheit) |
| Permissions | contents: read |
| Concurrency | 1 Deploy pro Environment gleichzeitig |
| DEV Deploy | Automatisch bei Push auf main |
| TEST Deploy | Manuell (workflow_dispatch); Template-Job inaktiv seit 2026-04-21 |
| PROD Deploy | Manuell (workflow_dispatch, Required Reviewer) |
| Smoke Test DEV | 12 Versuche a 10s (~2 Min) |
| Smoke Test PROD | 18 Versuche a 10s (~3 Min) |
| Helm Flags | --wait --timeout 15m --history-max 5 |
| paths-ignore | docs/**, *.md (Root), .claude/** |
| Branch Protection | PR required, 3 Status Checks (helm-validate, build-backend, build-frontend) |
| PROD Secrets | 7 Environment Secrets + Required Reviewer (inkl. OPENSEARCH_PASSWORD seit 2026-03-22) |

---

## 13. Security-Status

| ID | Massnahme | Status |
|----|-----------|--------|
| SEC-01 | PG ACL (IP-Allowlisting) | Umgesetzt (DEV+TEST+PROD) |
| SEC-02 | Dedicated Node Affinity | Zurueckgestellt (P3, ADR-004: nicht noetig) |
| SEC-03 | NetworkPolicies | Umgesetzt (alle Environments). DEV: 7, PROD: 7, Monitoring: 13, cert-manager: 6. |
| SEC-04 | Sealed Secrets | Zurueckgestellt (P3, Solo-Dev, chmod 600) |
| SEC-05 | Kubeconfig-Trennung | Zurueckgestellt (P3, PROD = eigener Cluster) |
| SEC-06 | runAsNonRoot | Phase 2 ERLEDIGT (PROD, Vespa = Ausnahme — braucht Root fuer vm.max_map_count) |
| SEC-07 | Encryption at Rest | Verifiziert (StackIT Default, AES-256) |

---

## 14. Extensions

| Modul | Feature Flag | Status | Admin UI |
|-------|-------------|--------|----------|
| ext-framework | EXT_ENABLED | Deployed | /ext/health |
| ext-branding | EXT_BRANDING_ENABLED | Deployed (DEV+TEST, 2026-03-08) | /admin/ext/branding |
| ext-token | EXT_TOKEN_LIMITS_ENABLED | Deployed (DEV+TEST, 2026-03-09) | /admin/ext/token-usage |
| ext-prompts | EXT_CUSTOM_PROMPTS_ENABLED | Deployed (DEV+TEST, 2026-03-09) | /admin/ext/system-prompts |
| ext-i18n | EXT_I18N_ENABLED + NEXT_PUBLIC_EXT_I18N_ENABLED | Deployed (DEV, 2026-03-22) | -- (Frontend-only) |
| ext-analytics | EXT_ANALYTICS_ENABLED | UEBERSPRUNGEN (in ext-token enthalten) | -- |
| ext-rbac | EXT_RBAC_ENABLED | Implementiert (2026-03-23) | /admin/ext-groups |
| ext-access | EXT_DOC_ACCESS_ENABLED | Implementiert (2026-03-25) | /admin/ext/access (resync, status) |
| ext-audit | EXT_AUDIT_ENABLED | Implementiert (2026-03-25) | /admin/ext/audit (events, CSV-export) |

**Alembic-Chain:** a3b8d9e2f1c4 -> ff7273065d0d (branding) -> b3e4a7d91f08 (token) -> c7f2e8a3d105 (prompts) -> d8a1b2c3e4f5 (audit)

**DB-Tabellen:** ext_branding_config, ext_token_usage, ext_prompt_templates, ext_audit_log (alle mit ext_-Prefix)

---

## 15. Kapazitaet & Skalierung

| Parameter | Wert |
|-----------|------|
| PROD-Sizing | 2x g1a.8d reicht fuer ~150 gleichzeitige User |
| CPU bei Vollauslastung (150 User) | ~40% |
| RAM bei Vollauslastung (150 User) | ~25% |
| Aktuelle CPU-Auslastung (DEV) | 2x g1a.4d, ~7.400m gesamt allocatable |
| Aktuelle RAM-Auslastung (DEV) | 2x g1a.4d, ~28 Gi gesamt allocatable |
| HPA | Nicht aktiv, nachruestbar |
| Upload-Limit (Ingress Controller) | **20 MB** (`proxy-body-size: "20m"` in values-common.yaml, XREF-007, 2026-03-15) |
| Upload-Limit (interner NGINX, Chart) | 5 GB (Upstream Helm Chart, READ-ONLY — Port 1024 nicht exponiert) |
| Upload-Limit (Docker Compose) | 20 MB (`client_max_body_size 20m` in app.conf, XREF-007) |
| Upload-Limit (Backend App) | **20 MB** (`MAX_FILE_SIZE_BYTES: "20971520"` in values-common.yaml, Defense-in-Depth XREF-007, 2026-03-16) |
| Request-Rate-Limiting (SEC-09) | **10 r/s per IP**, burst 50, nodelay. NGINX `limit_req_zone` + `limit_req` in values-common.yaml + values-prod.yaml. HTTP 429 bei Ueberschreitung. `externalTrafficPolicy: Local` fuer Client-IP Erhaltung. (2026-03-16) |
| Chat-Retention (vereinbart, Kickoff) | 6 Monate [Noch nicht implementiert] |
| Vespa PVC | 20 GB DEV, 50 GB PROD (kein separates Backup, Zombie-Mode — kein aktiver Index-Traffic) |
| OpenSearch PVC | 30 GB pro Umgebung (primaerer Document Index) |
| Gemessene RTO (DEV, 17 MB DB) | Technisch: 3:16 Min, Operativ: 7:15 Min (Test 2026-03-15) |
| Letzter Restore-Test | 2026-03-15 (DEV, ✅ 100% Integritaet) |
| Naechster Restore-Test | 2026-06-15 (quartalsmaessig) |
