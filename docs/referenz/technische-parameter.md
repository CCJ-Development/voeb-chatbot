# Technische Parameter — Single Source of Truth

> Alle technischen Spezifikationen an EINER Stelle. Andere Dokumente verweisen hierher.
> Letzte Aktualisierung: 2026-03-17

---

## 1. Umgebungen

| Parameter | DEV | TEST | PROD |
|-----------|-----|------|------|
| Cluster | vob-chatbot (shared) | vob-chatbot (shared) | vob-prod (eigener, ADR-004) |
| Namespace | onyx-dev | onyx-test | onyx-prod |
| K8s Version | v1.33.8 | v1.33.8 | v1.33.9 |
| Flatcar | 4459.2.1 | 4459.2.1 | 4459.2.3 |
| Node Pool | devtest (2x g1a.4d) | devtest (2x g1a.4d) | prod (2x g1a.8d) |
| Node Specs | 4 vCPU, 16 GB RAM, 100 GB Disk | 4 vCPU, 16 GB RAM, 100 GB Disk | 8 vCPU, 32 GB RAM, 100 GB Disk |
| Allocatable (gesamt) | ~7.400m CPU, ~28 Gi RAM | ~7.400m CPU, ~28 Gi RAM | 15.820m CPU, ~55 Gi RAM (56.666 Mi) |
| Pods | 16 | 15 | 19 |
| API Replicas | 1 | 1 | 2 (HA) |
| Web Replicas | 1 | 1 | 2 (HA) |
| Celery Worker | 8 (Standard Mode, 7 Worker + 1 Beat) | 8 | 8 |
| IngressClass | nginx | nginx-test | nginx |
| URL | https://dev.chatbot.voeb-service.de | https://test.chatbot.voeb-service.de | https://chatbot.voeb-service.de |
| HTTPS | LIVE (2026-03-09) | LIVE (2026-03-09) | **LIVE** (2026-03-17) — Let's Encrypt ECDSA P-384, TLSv1.3, HTTP/2 |
| Auth | basic | basic | basic (Entra ID geplant, Phase 3) |
| Deploy-Trigger | Push auf main (auto) | workflow_dispatch (manuell) | workflow_dispatch (manuell, Required Reviewer) |
| Status | LIVE seit 2026-02-27 | LIVE seit 2026-03-03 | **HTTPS LIVE** seit 2026-03-17 (deployed 2026-03-11) |
| Deployment-Strategie | Recreate | Recreate | Recreate |

---

## 2. Netzwerk & DNS

| Parameter | Wert |
|-----------|------|
| Domain | voeb-service.de |
| Subdomain | chatbot (festgelegt durch VoeB, Mail Leif Rasch, 2026-03-04) |
| Authoritative NS | GlobVill (dns.voerde.globvill.de, dns.globvill.de, dns.globvill.ruhr) |
| DNS Provider | Cloudflare (DNS-only, kein Proxy, Pro-Plan) |
| DNS-Aufloesungskette | GlobVill CNAME -> *.voeb-service.de.cdn.cloudflare.net -> Cloudflare A-Record -> StackIT LB IP |
| LB DEV | 188.34.74.187 |
| LB TEST | 188.34.118.201 |
| LB PROD | 188.34.92.162 |
| Egress DEV+TEST | 188.34.93.194 (NAT Gateway, fest fuer Cluster-Lifecycle) |
| Egress PROD | 188.34.73.72 |
| TLS Algorithmus | ECDSA P-384 (secp384r1), BSI TR-02102-2 konform |
| TLS Version | TLSv1.3 |
| TLS Cipher | AEAD-AES256-GCM-SHA384 / TLS_AES_256_GCM_SHA384 |
| TLS Issuer | Let's Encrypt E8 (ECDSA Intermediate) |
| TLS Chain | Leaf (P-384) -> E8 (P-384) -> ISRG Root X1 (RSA 4096) |
| TLS Laufzeit | 90 Tage (cert-manager Renewal nach 2/3 = ~Tag 60) |
| HTTP-Version | HTTP/2 |
| cert-manager | v1.19.4, DNS-01 via Cloudflare API |
| ClusterIssuers | onyx-dev-letsencrypt, onyx-test-letsencrypt, onyx-prod-letsencrypt (alle READY) |
| ACME Server | https://acme-v02.api.letsencrypt.org/directory (Production) |
| ACME Email | nikolaj.ivanov@coffee-studios.de |
| HSTS DEV/TEST | max-age=3600; includeSubDomains |
| HSTS PROD | max-age=31536000; includeSubDomains |
| HTTP-zu-HTTPS Redirect | 308 Permanent Redirect |
| NetworkPolicies DEV/TEST | 5 Policies in onyx-dev/onyx-test (SEC-03, seit 2026-03-05) |
| NetworkPolicies PROD | Offen (vollstaendiges Set kommt mit DNS/TLS-Hardening) |
| NetworkPolicies Monitoring | 7 Policies pro Cluster (Zero-Trust) |
| SKE Cluster API ACL | 0.0.0.0/0 (Kubeconfig mit Client-Zertifikat als Schutz) |
| PG ACL DEV+TEST | 188.34.93.194/32 + Admin (SEC-01) |
| PG ACL PROD | 188.34.73.72/32 + Admin (SEC-01) |

---

## 3. Datenbank (PostgreSQL Flex)

| Parameter | DEV | TEST | PROD |
|-----------|-----|------|------|
| Instanz-Name | vob-dev | vob-test | vob-prod |
| Konfiguration | Flex 2.4 Single | Flex 2.4 Single | Flex 4.8 HA (3-Node Cluster) |
| Specs | 2 CPU, 4 GB RAM, 20 GB SSD | 2 CPU, 4 GB RAM, 20 GB SSD | 4 CPU, 8 GB RAM (HA 3 Nodes) |
| PostgreSQL Version | 16 | 16 | 16 |
| Datenbank | onyx | onyx | onyx |
| User (RW) | onyx_app | onyx_app | onyx_app |
| User (RO) | db_readonly_user | db_readonly_user | db_readonly_user |
| Port | 5432 | 5432 | 5432 |
| Verbindung | SSL/TLS (sslmode=require) | SSL/TLS | SSL/TLS |
| Backup | Taeglich 02:00 UTC, 30 Tage | Taeglich 03:00 UTC, 30 Tage | Taeglich 01:00 UTC, 30 Tage, PITR sekundengenau (Flex 4.8 HA) |
| Encryption at Rest | AES-256 (StackIT Default) | AES-256 | AES-256 |
| Lifecycle Protection | prevent_destroy = true (Terraform) | prevent_destroy = true | prevent_destroy = true |
| User-Rollen | login, createdb | login, createdb | login, createdb |
| max_connections | 100 (StackIT Default) | 100 | 100 |

**Hinweise:**
- StackIT PG Flex erlaubt kein CREATEROLE -- spezielle User per Terraform
- StackIT PG Flex erlaubt kein Patching von User-Rollen (Destroy + Recreate)
- pg_monitor Rolle nicht verfuegbar (nur login + createdb)
- Backups sind instanzgebunden -- nach Loeschung nicht mehr verfuegbar

---

## 4. Object Storage

| Parameter | DEV | TEST | PROD |
|-----------|-----|------|------|
| Bucket | vob-dev | vob-test | vob-prod |
| Endpoint | object.storage.eu01.onstackit.cloud | (identisch) | (identisch) |
| Encryption | AES-256 (at rest) | AES-256 | AES-256 |
| Versionierung | Unterstuetzt, **nicht aktiviert** | Unterstuetzt, **nicht aktiviert** | Unterstuetzt, **nicht aktiviert** |
| Versionierung Hinweis | Nicht via Terraform konfigurierbar (StackIT API-Limitation, GH Issue #1048). Aktivierung per `aws s3api put-bucket-versioning` (einmalig pro Bucket). Audit H3. | | |

---

## 5. LLM-Konfiguration

| Parameter | DEV | TEST | PROD |
|-----------|-----|------|------|
| Provider | openai-compat (StackIT AI Model Serving) | (identisch) | [Noch nicht konfiguriert] |
| API Base | https://api.openai-compat.model-serving.eu01.onstackit.cloud/v1 | (identisch) | (identisch) |
| Chat-Modelle | 4 Modelle (seit 2026-03-08) | 4 Modelle (identisch) | [Ausstehend] |
| Embedding | Qwen3-VL-Embedding 8B (4096 Dim) | Qwen3-VL-Embedding 8B | [Ausstehend] |

### Chat-Modelle (DEV + TEST)

| Modell | Modell-ID |
|--------|-----------|
| GPT-OSS 120B | openai/gpt-oss-120b |
| Qwen3-VL 235B | Qwen/Qwen3-VL-235B-A22B-Instruct-FP8 |
| Llama 3.3 70B | cortecs/Llama-3.3-70B-Instruct-FP8-Dynamic |
| Llama 3.1 8B | neuralmagic/Meta-Llama-3.1-8B-Instruct-FP8 |

### Nicht kompatible Modelle (kein Tool Calling auf StackIT vLLM)

| Modell | Grund |
|--------|-------|
| google/gemma-3-27b-it | tool_choice: "auto" wird abgelehnt |
| neuralmagic/Mistral-Nemo-Instruct-2407-FP8 | tool_choice: "auto" wird abgelehnt |

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
| DEV+TEST (shared Cluster) | 11 (7 Basis + 4 Exporter) |
| PROD (eigener Cluster) | 9 (7 Basis + 2 Exporter) |

**Basis-Pods (7):** Prometheus, Grafana, AlertManager, kube-state-metrics, 2x node-exporter (DaemonSet), prometheus-operator

**Exporter DEV+TEST:** pg-exporter-dev, pg-exporter-test, redis-exporter-dev, redis-exporter-test

**Exporter PROD:** pg-exporter-prod, redis-exporter-prod

### 6.3 Scrape & Retention

| Parameter | DEV+TEST | PROD |
|-----------|----------|------|
| Scrape-Intervall | 30s | 30s |
| Scrape-Targets | 6 | 3 (onyx-api-prod, postgres-prod, redis-prod) |
| Retention | 30d | 90d |
| Retention Size | 15 GB | 40 GB |
| PVC | 20 Gi (ReadWriteOnce) | 50 Gi |

### 6.4 Alerting

| Parameter | DEV+TEST | PROD |
|-----------|----------|------|
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
| **Summe (DEV/TEST)** | **1.100m** | **~1,9 Gi** | |

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
| PostgreSQL | 14114 (Fallback: 9628) | DEV/TEST: manuell (nicht persistent). PROD: Sidecar |
| Redis | 763 | DEV/TEST: manuell (nicht persistent). PROD: Sidecar |
| Kubernetes Cluster | 6417 | -- |
| Kubernetes Pods | 15760 | -- |
| NGINX Ingress | 9614 | -- |
| Onyx API (Custom) | -- | 6 Panels: Request Rate, Latency, Error Rate, Slow Requests, DB Pool, DB Hold Time |

---

## 7. Kosten (netto, zzgl. MwSt.)

### 7.1 DEV+TEST (Cluster vob-chatbot, shared)

| Posten | Anzahl | EUR/Mo (je) | EUR/Mo (gesamt) |
|--------|--------|-------------|-----------------|
| SKE Cluster Management Fee | 1 | 71,71 | 71,71 |
| Worker Node g1a.4d | 2 | 141,59 | 283,18 |
| PostgreSQL Flex 2.4 Single | 2 | 105,54 | 211,08 |
| Object Storage Bucket | 2 | 0,27 | 0,54 |
| Load Balancer Essential-10 | 2 | 9,39 | 18,78 |
| **Gesamt DEV+TEST** | | | **585,29** |

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
| DEV+TEST | 585,29 |
| PROD | 963,96 |
| **Gesamt alle 3 Environments** | **1.549,25** |

**Kostenoptimierung (2026-03-16):** DEV+TEST von 868,47 auf 585,29 EUR/Mo gesenkt durch Node-Downgrade g1a.8d → g1a.4d nach Resource-Requests-Optimierung. Details: `audit-output/kostenoptimierung-ergebnis.md`.

**Nicht enthalten:** Block Storage (Vespa PVCs, 20 GB/Env), StackIT Container Registry, StackIT AI Model Serving (nutzungsabhaengig). PG-Backups sind im PG Flex Preis enthalten.

**Preisquelle:** StackIT Preisliste v1.0.36 (03.03.2026), verifiziert gegen StackIT Calculator (2026-03-05). Alle Preise netto.

---

## 8. Versionen

| Komponente | Version | Hinweis |
|------------|---------|---------|
| Kubernetes DEV+TEST | v1.33.8 | Flatcar 4459.2.1 |
| Kubernetes PROD | v1.33.9 | Flatcar 4459.2.3 |
| PostgreSQL | 16 | StackIT Managed Flex |
| Redis | 7.0.15 | In-Cluster, OT Operator |
| Vespa | 8.609.39 | In-Cluster |
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
| vob-chatbot (DEV+TEST) | 02:00-04:00 | K8s Managed (StackIT, Terraform-konfiguriert) |
| vob-prod (PROD) | 03:00-05:00 | K8s Managed (StackIT, Terraform-konfiguriert) |

**PG Backups:**
- DEV: taeglich 02:00 UTC (`pg_backup_schedule = "0 2 * * *"`)
- TEST: taeglich 03:00 UTC (`pg_backup_schedule = "0 3 * * *"`)
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
| vob-chatbot (DEV+TEST) | 2026-05-28 | 90-Tage-Rotation |
| vob-prod (PROD) | 2026-06-09 | 90-Tage-Rotation |

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
| TEST Deploy | Manuell (workflow_dispatch) |
| PROD Deploy | Manuell (workflow_dispatch, Required Reviewer) |
| Smoke Test DEV/TEST | 12 Versuche a 10s (~2 Min) |
| Smoke Test PROD | 18 Versuche a 10s (~3 Min) |
| Helm Flags | --wait --timeout 15m --history-max 5 |
| paths-ignore | docs/**, *.md (Root), .claude/** |
| Branch Protection | PR required, 3 Status Checks (helm-validate, build-backend, build-frontend) |
| PROD Secrets | 6 Environment Secrets + Required Reviewer |

---

## 13. Security-Status

| ID | Massnahme | Status |
|----|-----------|--------|
| SEC-01 | PG ACL (IP-Allowlisting) | Umgesetzt (DEV+TEST+PROD) |
| SEC-02 | Dedicated Node Affinity | Zurueckgestellt (P3, ADR-004: nicht noetig) |
| SEC-03 | NetworkPolicies | Umgesetzt (DEV+TEST, 5 Policies). PROD offen. |
| SEC-04 | Sealed Secrets | Zurueckgestellt (P3, Solo-Dev, chmod 600) |
| SEC-05 | Kubeconfig-Trennung | Zurueckgestellt (P3, PROD = eigener Cluster) |
| SEC-06 | runAsNonRoot | Phase 2 ERLEDIGT (PROD, Vespa = Ausnahme) |
| SEC-07 | Encryption at Rest | Verifiziert (StackIT Default, AES-256) |

---

## 14. Extensions

| Modul | Feature Flag | Status | Admin UI |
|-------|-------------|--------|----------|
| ext-framework | EXT_ENABLED | Deployed | /ext/health |
| ext-branding | EXT_BRANDING_ENABLED | Deployed (DEV+TEST, 2026-03-08) | /admin/ext/branding |
| ext-token | EXT_TOKEN_LIMITS_ENABLED | Deployed (DEV+TEST, 2026-03-09) | /admin/ext/token-usage |
| ext-prompts | EXT_CUSTOM_PROMPTS_ENABLED | Deployed (DEV+TEST, 2026-03-09) | /admin/ext/system-prompts |
| ext-analytics | EXT_ANALYTICS_ENABLED | UEBERSPRUNGEN (in ext-token enthalten) | -- |
| ext-rbac | EXT_RBAC_ENABLED | BLOCKIERT (Entra ID) | -- |
| ext-access | EXT_DOC_ACCESS_ENABLED | BLOCKIERT (braucht RBAC) | -- |

**Alembic-Chain:** a3b8d9e2f1c4 -> ff7273065d0d (branding) -> b3e4a7d91f08 (token) -> c7f2e8a3d105 (prompts)

**DB-Tabellen:** ext_branding_config, ext_token_usage, ext_prompt_templates (alle mit ext_-Prefix)

---

## 15. Kapazitaet & Skalierung

| Parameter | Wert |
|-----------|------|
| PROD-Sizing | 2x g1a.8d reicht fuer ~150 gleichzeitige User |
| CPU bei Vollauslastung (150 User) | ~40% |
| RAM bei Vollauslastung (150 User) | ~25% |
| Aktuelle CPU-Auslastung (DEV+TEST, 2026-03-16) | ~5,8% (930m). Nach Downgrade auf g1a.4d: ~13% von ~7.400m |
| Aktuelle RAM-Auslastung (DEV+TEST, 2026-03-16) | ~32% (18.399 Mi). Nach Downgrade auf g1a.4d: ~66% von ~28 Gi |
| HPA | Nicht aktiv, nachruestbar |
| Upload-Limit (Ingress Controller) | **20 MB** (`proxy-body-size: "20m"` in values-common.yaml, XREF-007, 2026-03-15) |
| Upload-Limit (interner NGINX, Chart) | 5 GB (Upstream Helm Chart, READ-ONLY — Port 1024 nicht exponiert) |
| Upload-Limit (Docker Compose) | 20 MB (`client_max_body_size 20m` in app.conf, XREF-007) |
| Upload-Limit (Backend App) | **20 MB** (`MAX_FILE_SIZE_BYTES: "20971520"` in values-common.yaml, Defense-in-Depth XREF-007, 2026-03-16) |
| Request-Rate-Limiting (SEC-09) | **10 r/s per IP**, burst 50, nodelay. NGINX `limit_req_zone` + `limit_req` in values-common.yaml + values-prod.yaml. HTTP 429 bei Ueberschreitung. `externalTrafficPolicy: Local` fuer Client-IP Erhaltung. (2026-03-16) |
| Chat-Retention (vereinbart, Kickoff) | 6 Monate [Noch nicht implementiert] |
| Vespa PVC | 20 GB pro Umgebung (kein separates Backup) |
| Gemessene RTO (DEV, 17 MB DB) | Technisch: 3:16 Min, Operativ: 7:15 Min (Test 2026-03-15) |
| Letzter Restore-Test | 2026-03-15 (DEV, ✅ 100% Integritaet) |
| Naechster Restore-Test | 2026-06-15 (quartalsmaessig) |
