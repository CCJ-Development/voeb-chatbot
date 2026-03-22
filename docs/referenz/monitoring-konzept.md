# Monitoring-Konzept — VÖB Service Chatbot

> **Status:** ✅ Deployed (2026-03-10) — Phase 1-4 live (Exporters + Dashboards deployed), Alerting via Teams aktiv. PROD deployed (2026-03-12, Helm Rev 4). OpenSearch-Monitoring hinzugefuegt (2026-03-19), Vespa auf Alive-Check reduziert (Zombie-Mode).
> **Entscheidung:** Self-Hosted kube-prometheus-stack (Niko, 2026-03-10)
> **Scope:** DEV + TEST (Shared Cluster) deployed, PROD (eigener Cluster) deployed (2026-03-12, Helm Rev 4)
> **Compliance:** BSI DER.1 (Detektion), BSI OPS.1.1.5 (Protokollierung), orientiert an BAIT Kap. 5 (freiwillig)
> **Helm Release:** `monitoring` in Namespace `monitoring` (separater Release, nicht im Onyx Chart)
> **Chart:** `prometheus-community/kube-prometheus-stack`

---

## 1. IST-Zustand

### Was bereits existiert (Onyx FOSS built-in)

Onyx hat ein produktives Prometheus-Monitoring. Der API-Server exponiert `/metrics` im Prometheus Text Format.

**Vorhandene Metriken (~20 Stück):**

| Kategorie | Metriken | Quelle |
|-----------|----------|--------|
| HTTP Requests | `http_requests_total`, `http_request_duration_seconds` (Histogram, 10 Buckets), `http_requests_inprogress` | `prometheus-fastapi-instrumentator` |
| Slow Requests | `onyx_api_slow_requests_total` (>1s, konfigurierbar via `SLOW_REQUEST_THRESHOLD_SECONDS`) | `server/metrics/slow_requests.py` |
| Per-Tenant | `onyx_api_requests_by_tenant_total` | `server/metrics/per_tenant.py` |
| DB Pool State (4) | `onyx_db_pool_checked_out`, `_checked_in`, `_overflow`, `_size` (je Engine: sync, async, readonly) | `server/metrics/postgres_connection_pool.py` |
| DB Pool Lifecycle (4) | `onyx_db_pool_checkout_total`, `_checkin_total`, `_connections_created_total`, `_invalidations_total` | `server/metrics/postgres_connection_pool.py` |
| DB per Endpoint | `onyx_db_connections_held_by_endpoint` (Gauge), `onyx_db_connection_hold_seconds` (Histogram) | `server/metrics/postgres_connection_pool.py` |
| DB Timeout | `onyx_db_pool_checkout_timeout_total` + HTTP 503 Response | Exception Handler in `prometheus_setup.py` |
| Celery Queues | Queue Lengths (PRIMARY, DOCPROCESSING, DOCFETCHING, etc.) alle 5 Min | `background/celery/tasks/monitoring/tasks.py` |
| Connector Lifecycle | Start Latency, Index Attempt Duration, Success/Failure | `monitoring/tasks.py` |
| Process Memory | RSS, VMS, CPU% pro Worker-Prozess | `memory_monitoring.py` → `/var/log/onyx/memory/memory_usage.log` |

**Vorhandene Health-Endpoints:**

| Endpoint | Auth | Response |
|----------|------|----------|
| `GET /health` | Nein (PUBLIC_ENDPOINT_SPECS) | `{"success": true, "message": "ok"}` |
| `GET /ext/health` | Nein (PUBLIC_ENDPOINT_SPECS) | Extension-Status + Feature Flags |
| `GET /metrics` | Nein (excluded von Instrumentierung) | Prometheus Text Format (0.0.4) |

**Prometheus-Setup im Code:**
- `backend/onyx/main.py:667` — `setup_prometheus_metrics(application)`
- `backend/onyx/main.py:329-331` — `setup_postgres_connection_pool_metrics(engines={...})`
- Excluded Handlers: `/health`, `/metrics`, `/openapi.json`

**Health Probes im Helm Chart:**
- Templates vorbereitet: `{{- with .Values.api.readinessProbe }}` (api-deployment.yaml), analog webserver
- Chart-Defaults definieren korrekte Probes (httpGet /health port http)
- ✅ **Konfiguriert in `values-common.yaml`** (2026-03-10, siehe Deployment-Protokoll Abschnitt 9)

### Was fehlt (Stand vor Deployment)

| Feature | Status | Impact |
|---------|--------|--------|
| Prometheus-Server (Scraping) | ✅ Deployed (2026-03-10) | 20 Targets, 30s Intervall |
| Grafana (Dashboards) | ✅ Deployed (2026-03-10) | Zugang via port-forward |
| AlertManager (Alerting) | ✅ Deployed (2026-03-10), Teams Webhook (2026-03-11) | 20 Alert-Rules, Microsoft Teams Webhook aktiv |
| Log-Aggregation | Nicht vorhanden | Pod-Logs gehen bei Restart verloren (Loki evaluieren) |
| Health Probes in Helm Values | ✅ Konfiguriert (2026-03-10) | API: httpGet /health, Webserver: tcpSocket 3000 |
| kube-state-metrics | ✅ Deployed (2026-03-10) | Pod/Node/Deployment-Level-Metriken |
| node-exporter | ✅ Deployed (2026-03-10) | 2× DaemonSet (je Node) |

---

## 2. Entscheidung: Self-Hosted kube-prometheus-stack

### Begründung

| Kriterium | StackIT Managed (70 EUR/Mo) | Self-Hosted (0 EUR/Mo) | Gewinner |
|-----------|----------------------------|------------------------|----------|
| Setup-Aufwand | 1-1,5 PT | 1,5 PT | Managed (leicht) |
| Monatliche Kosten | 70 EUR (840 EUR/Jahr) | 0 EUR | **Self-Hosted** |
| Metriken-Abdeckung | Nur API (externer Scrape) | Alles (API, Redis, OpenSearch (Primary), Vespa (Zombie, Alive-Check), Celery, Nodes) | **Self-Hosted** |
| Maintenance | Null | ~30 Min/Quartal (Helm Upgrade) | Managed |
| Cluster-Ressourcen | 0 | ~1,1 vCPU, ~1,9 Gi RAM | Managed |
| K8s-native (ServiceMonitor) | Nein (externer Scrape) | Ja (CRDs) | **Self-Hosted** |

**Entscheidende Faktoren:**
1. **Kosten:** 840 EUR/Jahr gespart bei einem Projekt das auf Kosten achtet
2. **Abdeckung:** Managed sieht nur den API-Server. Self-Hosted sieht alles.
3. **Für vollständige Abdeckung mit Managed** bräuchte man trotzdem einen In-Cluster-Agent (Grafana Alloy) → dann hat man einen Pod im Cluster UND zahlt 70 EUR/Mo

### Verworfene Alternative: StackIT Managed Observability

StackIT bietet `Observability-Starter-EU01` (70 EUR/Mo) mit Prometheus + Grafana + Alerting. Terraform-native (6 Resources: `stackit_observability_instance`, `_credential`, `_scrapeconfig`, `_alertgroup`, `_logalertgroup`, `_loadbalancer_observability_credential`). Für Projekte ohne K8s-Expertise oder mit kleinem Cluster wäre das die bessere Wahl. Hier nicht gewählt wegen Kosten und eingeschränkter Abdeckung.

> **Hinweis:** Im Kickoff-Meeting wurde StackIT Managed Observability als erste Option besprochen (KICKOFF-022). Diese wurde zugunsten von kube-prometheus-stack verworfen (Gründe: eingeschränkte Abdeckung, 70 EUR/Mo Zusatzkosten, fehlende Custom-Alert-Rules).

---

## 3. Ressourcen-Validierung

### Cluster-Budget: Passt es?

**Aktuell belegt (DEV + TEST + System):**

| | CPU Requests | RAM Requests | CPU Limits | RAM Limits |
|---|---|---|---|---|
| DEV (17 Pods) | 2.950m | 7,5 Gi | 8.750m | 24 Gi |
| TEST (0 Pods, heruntergefahren seit 2026-03-19) | 0 | 0 | 0 | 0 |
| System (kube-system, cert-manager, redis-op) | ~500m | ~1 Gi | ~800m | ~2 Gi |
| **Summe aktuell** | **6.400m** | **16 Gi** | **18.300m** | **50 Gi** |

**kube-prometheus-stack (Bedarf):**

| Komponente | CPU Request | RAM Request | CPU Limit | RAM Limit |
|------------|-------------|-------------|-----------|-----------|
| Prometheus | 500m | 1 Gi | 1.000m | 2 Gi |
| Grafana | 100m | 256 Mi | 250m | 512 Mi |
| AlertManager | 100m | 128 Mi | 200m | 256 Mi |
| kube-state-metrics | 100m | 128 Mi | 200m | 256 Mi |
| node-exporter (×2 DaemonSet) | 200m | 256 Mi | 400m | 512 Mi |
| prometheus-operator | 100m | 128 Mi | 200m | 256 Mi |
| **Summe Monitoring** | **1.100m** | **~1,9 Gi** | **2.250m** | **~3,8 Gi** |

**Nach Monitoring-Deployment:**

| | CPU Requests | RAM Requests | CPU Limits | RAM Limits |
|---|---|---|---|---|
| **Gesamt** | **7.500m** | **17,9 Gi** | **20.550m** | **53,8 Gi** |
| **Allocatable (2× g1a.8d)** | 15.820m | 56,6 Gi | 15.820m | 56,6 Gi |
| **Auslastung** | **47%** | **32%** | **130%** | **95%** |

**Bewertung:**
- **Requests: Kein Problem** (47% CPU, 32% RAM)
- **CPU Limits 130%:** OK — Burstable, wird nur throttled
- **RAM Limits 95%:** Theoretisch eng, praktisch OK — die meisten Pods nutzen 30-50% ihres Limits. Reale RAM-Nutzung liegt bei ~28% (gemessen 2026-03-06)
- **Risiko:** Bei gleichzeitiger Indexierung vieler Dokumente (Docfetching + Docprocessing nahe Limit) könnte es eng werden. Monitoring zeigt das dann selbst an.

### PROD-Cluster (eigener, 2× g1a.8d, ADR-004)

| | CPU Requests | RAM Requests | CPU Limits | RAM Limits |
|---|---|---|---|---|
| PROD (20 Pods) | ~7.850m | ~15.25 Gi | ~19.500m | ~42.5 Gi |
| System | ~500m | ~1 Gi | ~800m | ~2 Gi |
| Monitoring | 1.100m | 1,9 Gi | 2.250m | 3,8 Gi |
| **Gesamt PROD** | **~9.450m** | **~18.15 Gi** | **~22.550m** | **~48.3 Gi** |
| **Auslastung** | **~60%** | **~32%** | **~143%** | **~85%** |

**PROD: Komfortabel.** CPU Requests ~65%, RAM Requests ~32%. CPU Limits uebercommitted (normal bei Burstable QoS). Detailberechnung in `docs/referenz/prod-bereitstellung.md`, Sektion 11.

---

## 4. Implementierungsplan

### Phase 1: Health Probes aktivieren (0,25 PT) — ✅ DEPLOYED

**Status:** ✅ Deployed auf DEV (2026-03-10). TEST-Deploy: Probe-Timeouts korrigiert (Liveness 105s → 180s), Re-Deploy läuft.

**values-common.yaml — finale Konfiguration:**

```yaml
api:
  # /health ist PUBLIC_ENDPOINT (keine Auth), existiert in Onyx FOSS
  readinessProbe:
    httpGet:
      path: /health
      port: 8080
    initialDelaySeconds: 30
    periodSeconds: 10
    failureThreshold: 6
    timeoutSeconds: 5
  livenessProbe:
    httpGet:
      path: /health
      port: 8080
    initialDelaySeconds: 60      # API braucht >30s bei Alembic Migrations
    periodSeconds: 15
    failureThreshold: 8           # 60s + 8×15s = 180s Gnadenfrist
    timeoutSeconds: 5

webserver:
  # TCP Socket statt HTTP — siehe "Lesson Learned" unten
  readinessProbe:
    tcpSocket:
      port: 3000
    initialDelaySeconds: 20
    periodSeconds: 10
    failureThreshold: 6
    timeoutSeconds: 5
  livenessProbe:
    tcpSocket:
      port: 3000
    initialDelaySeconds: 30
    periodSeconds: 15
    failureThreshold: 5
    timeoutSeconds: 5
```

**Lesson Learned — Webserver HTTP Probes funktionieren NICHT:**

Der erste Deploy-Versuch nutzte `httpGet /api/health:3000` (Readiness) und `httpGet /:3000` (Liveness). Beides schlug fehl:

| Probe | Geplant | Ergebnis | Ursache |
|-------|---------|----------|---------|
| Readiness | `GET /api/health:3000` | **404** | `/api/*`-Proxy läuft über NGINX Ingress Controller, NICHT über Next.js intern. Next.js hat keine `/api/health`-Route. |
| Liveness | `GET /:3000` | **Timeout** | `/` triggert Redirect-Chain (`/` → 307 `/app` → 307 `/auth/login` → 200). Bei Kaltstart (SSR-Kompilierung) dauert der erste Request >5s → Timeout → Pod wird neugestartet. |

**Fix:** TCP Socket Probe auf Port 3000. Prüft ob der Next.js-Prozess lebt und Connections annimmt — das ist für den Webserver ausreichend. Die eigentliche Health-Prüfung (Backend erreichbar?) erfolgt über die API-Probe.

**Verifizierung:**
```bash
# API Server — HTTP Probe verifizieren
kubectl port-forward -n onyx-dev svc/onyx-dev-api-service 8080:8080
curl http://localhost:8080/health    # → {"success": true, "message": "ok"}
curl http://localhost:8080/metrics   # → Prometheus Text Format

# Webserver — Pod-Status prüfen (tcpSocket hat keinen curl-Test)
kubectl get pods -n onyx-dev -l app.kubernetes.io/name=web-server
# READY 1/1 = Probe erfolgreich
```

### Phase 2: kube-prometheus-stack deployen (0,75 PT) — ✅ DEPLOYED

**Status:** ✅ Deployed (2026-03-10), 7 Pods Running, 20 Targets aktiv

**2.1 Namespace + Helm Install**

```bash
# Helm Repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install in eigenen Namespace
helm install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace \
  -f deployment/helm/values/values-monitoring.yaml \
  --set grafana.adminPassword=<PASSWORD>
```

**2.2 Custom Values (`deployment/helm/values/values-monitoring.yaml`)**

```yaml
# ===========================================================
# VÖB Service Chatbot — Monitoring Stack Values
# ===========================================================
# kube-prometheus-stack auf shared DEV+TEST Cluster
# Ressourcen-Budget: 1,1 vCPU Requests, 1,9 Gi RAM Requests
# ===========================================================

# --- Prometheus ---
prometheus:
  prometheusSpec:
    retention: 30d                    # 30 Tage Metriken behalten
    retentionSize: "15GB"             # Max Storage
    scrapeInterval: "30s"             # Scrape alle 30 Sekunden
    resources:
      requests:
        cpu: 500m
        memory: 1Gi
      limits:
        cpu: 1000m
        memory: 2Gi
    storageSpec:
      volumeClaimTemplate:
        spec:
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 20Gi
    # Scrape Onyx API in beiden Namespaces
    additionalScrapeConfigs:
      - job_name: "onyx-api-dev"
        metrics_path: "/metrics"
        scrape_interval: "30s"
        static_configs:
          - targets: ["onyx-dev-api-service.onyx-dev.svc.cluster.local:8080"]
            labels:
              environment: "dev"
              service: "api"
      - job_name: "onyx-api-test"
        metrics_path: "/metrics"
        scrape_interval: "30s"
        static_configs:
          - targets: ["onyx-test-api-service.onyx-test.svc.cluster.local:8080"]
            labels:
              environment: "test"
              service: "api"
    # ServiceMonitor Namespace Selector (alle Namespaces)
    serviceMonitorSelectorNilUsesHelmValues: false
    podMonitorSelectorNilUsesHelmValues: false

# --- Grafana ---
grafana:
  enabled: true
  adminPassword: ""  # → Wird per --set oder Secret gesetzt
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: 250m
      memory: 512Mi
  # Kein eigener Ingress — Zugriff per kubectl port-forward
  # Für PROD: Ingress mit Auth evaluieren
  ingress:
    enabled: false
  # Persistence deaktiviert — Dashboards kommen per ConfigMap
  persistence:
    enabled: false

# --- AlertManager ---
alertmanager:
  alertmanagerSpec:
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 200m
        memory: 256Mi
  config:
    global:
      resolve_timeout: 5m
    route:
      group_by: ["alertname", "namespace"]
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h
      receiver: "teams-niko"
      routes:
        - match:
            severity: critical
          repeat_interval: 1h
          receiver: "teams-niko"
    receivers:
      - name: "teams-niko"
        msteams_configs:
          - webhook_url: "<REDACTED>"  # Teams Incoming Webhook (Scale42 AI)
            title: '{{ .GroupLabels.alertname }}'
            text: '{{ range .Alerts }}{{ .Annotations.summary }} — {{ .Annotations.description }}{{ end }}'
            send_resolved: true

# --- kube-state-metrics ---
kube-state-metrics:
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 200m
      memory: 256Mi

# --- node-exporter ---
prometheus-node-exporter:
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 200m
      memory: 256Mi

# --- prometheus-operator ---
prometheusOperator:
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 200m
      memory: 256Mi

# --- Unnötige Komponenten deaktivieren ---
# Etcd, Scheduler, Controller-Manager Monitoring = StackIT-managed, kein Zugriff
kubeEtcd:
  enabled: false
kubeScheduler:
  enabled: false
kubeControllerManager:
  enabled: false
kubeProxy:
  enabled: false
```

**2.3 NetworkPolicy für Monitoring-Namespace** — ✅ Applied (2026-03-10), PROD-ready (2026-03-12)

**Status:** 9 Policies in `monitoring` + 2 Policies in `onyx-dev` + `onyx-test` applied (5 Basis + 2 Exporter-Egress seit Phase 4 + `08-allow-alertmanager-webhook-egress.yaml` seit Alerting-Konfiguration + `09-allow-backup-check-egress.yaml` seit 2026-03-15). `03-allow-scrape-egress.yaml` um `onyx-prod` erweitert (2026-03-12).

Der Monitoring-Namespace braucht:
- Egress zu `onyx-dev`, `onyx-test` und `onyx-prod` (Scraping auf Port 8080)
- Egress DNS (Port 53 + 8053 für StackIT/Gardener)
- Egress K8s API (Port 443 für prometheus-operator, kube-state-metrics, Service Discovery)
- Ingress von Admin (kubectl port-forward)

**Zusätzlich gegenüber dem Entwurf:** Policy `05-allow-k8s-api-egress.yaml` war im Entwurf nicht vorgesehen, ist aber nötig für prometheus-operator (CRD-Watches), kube-state-metrics (Cluster-State) und Prometheus Service Discovery.

```yaml
# deployment/k8s/network-policies/monitoring/01-default-deny.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: monitoring
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]

---
# deployment/k8s/network-policies/monitoring/02-allow-dns.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns-egress
  namespace: monitoring
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
    - ports:
        - port: 53
          protocol: UDP
        - port: 53
          protocol: TCP

---
# deployment/k8s/network-policies/monitoring/03-allow-scrape-egress.yaml
# (vollstaendige aktuelle Version — inkl. onyx-prod, ergaenzt 2026-03-12)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-prometheus-scrape
  namespace: monitoring
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: prometheus
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: onyx-dev
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: onyx-test
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: onyx-prod
      ports:
        - port: 8080
          protocol: TCP
    # kube-state-metrics, node-exporter (im eigenen Namespace)
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: monitoring
    # Kubelet Metrics (node-exporter, cAdvisor)
    - ports:
        - port: 10250
          protocol: TCP
        - port: 9100
          protocol: TCP

---
# deployment/k8s/network-policies/monitoring/04-allow-intra-namespace.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-intra-namespace
  namespace: monitoring
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress:
    - from:
        - podSelector: {}
  egress:
    - to:
        - podSelector: {}

# Weitere Policies (vollstaendige Dateien im Repo):
# 05-allow-k8s-api-egress.yaml    — K8s API (443) fuer prometheus-operator, kube-state-metrics
# 06-allow-pg-exporter-egress.yaml — PG Exporter → StackIT PG:5432
# 07-allow-redis-exporter-egress.yaml — Redis Exporter → onyx-dev/test/prod:6379
# 08-allow-alertmanager-webhook-egress.yaml — AlertManager → Teams Webhook (HTTPS:443)
# 09-allow-backup-check-egress.yaml — pg-backup-check CronJob → StackIT API (HTTPS:443)
```

**Zusätzlich:** Die bestehenden NetworkPolicies in `onyx-dev` und `onyx-test` müssen Ingress von `monitoring` Namespace auf Port 8080 erlauben. Neue Policy hinzufügen:

```yaml
# deployment/k8s/network-policies/onyx-dev/06-allow-monitoring-scrape.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-monitoring-scrape
  namespace: onyx-dev  # Analog für onyx-test
spec:
  podSelector: {}
  policyTypes: [Ingress]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: monitoring
      ports:
        - port: 8080
          protocol: TCP
```

### Phase 3: Alert-Rules (0,25 PT) — ✅ DEPLOYED

**Status:** 20 Custom-Regeln aktiv in `values-monitoring.yaml` (DEV/TEST) + 22 in `values-monitoring-prod.yaml` (PROD, inkl. 2 Backup-Check-Alerts). AlertManager konfiguriert mit Microsoft Teams Webhook (Kanal: Scale42 AI). OpenSearch PVC Storage Alert (#8b `OpenSearchStorageFull`) hinzugefuegt (2026-03-19).

**Alert-Rules (aktiv in YAML-Dateien):**

| # | Alert | Severity | DEV/TEST | PROD | Beschreibung |
|---|-------|----------|----------|------|-------------|
| 1 | `APIDown` | critical | ✅ | ✅ | API nicht erreichbar |
| 2 | `PodCrashLooping` | critical | ✅ | ✅ | Pod restartet wiederholt (>3/h) |
| 3 | `HighErrorRate` | warning | ✅ | ✅ | >5% HTTP 5xx Server Errors |
| 4 | `DBPoolExhausted` | warning | ✅ | ✅ | DB Connection Pool Overflow |
| 5 | `HighSlowRequests` | warning | ✅ | ✅ | >1 Slow Request/Sek seit 10min |
| 6 | `NodeMemoryPressure` | critical | ✅ | ✅ | <10% freier RAM auf Node |
| 7 | `NodeDiskPressure` | warning | ✅ | ✅ | <15% freier Disk auf Node |
| 8 | `VespaStorageFull` | warning | ✅ | ✅ | Vespa PVC <20% frei (Zombie-Mode) |
| 8b | `OpenSearchStorageFull` | warning/critical | ✅ | ✅ | OpenSearch PVC <20% frei |
| 9 | `CertExpiringSoon` | warning | ✅ | ✅ | TLS-Zertifikat laeuft in <14 Tagen ab |
| 10 | `PGExporterDown` | critical | ✅ | ✅ | PostgreSQL Exporter nicht erreichbar |
| 11 | `RedisExporterDown` | critical | ✅ | ✅ | Redis Exporter nicht erreichbar |
| 12 | `PGConnectionsHigh` | warning | ✅ | ✅ | PG Connections >80% von max_connections |
| 13 | `PGDeadlocks` | warning | ✅ | ✅ | >5 Deadlocks in 5min |
| 14 | `PGHighRollbackRate` | warning | ✅ | ✅ (tuned) | Rollback-Rate >5% (PROD: nur bei >10 tx/sec) |
| 15 | `PGDatabaseGrowing` | warning | ✅ | ✅ | PostgreSQL DB >10 GB |
| 16 | `RedisMemoryHigh` | warning | ✅ | ✅ | Redis Memory >80% von maxmemory |
| 17 | `RedisHighEvictions` | warning | ✅ | ✅ | >100 Keys evicted in 5min |
| 18 | `RedisCacheHitRateLow` | warning | ✅ | ✅ (tuned) | Cache Hit Rate <80% (PROD: nur bei >50 ops/sec) |
| 19 | `RedisRejectedConnections` | critical | ✅ | ✅ | Redis lehnt Connections ab |
| 20 | `PGCacheHitRateLow` | warning | ✅ | ✅ | PG Cache Hit Ratio <90% |
| 21 | `PGBackupCheckFailed` | critical | — | ✅ | Backup-Check CronJob fehlgeschlagen (PROD-only) |
| 22 | `PGBackupCheckNotScheduled` | warning | — | ✅ | Backup-Check CronJob nicht gelaufen (PROD-only) |

> **Hinweis OpenSearch Cluster-Health:** Ein `OpenSearchClusterRed`-Alert (basierend auf `opensearch_cluster_status` Metriken) ist konzeptionell geplant, aber **NOCH NICHT IMPLEMENTIERT**. Es existiert kein OpenSearch Prometheus Exporter im Cluster — daher stehen die dafuer noetigen Metriken (`opensearch_cluster_status`, `up{job=~"opensearch.*"}`) nicht zur Verfuegung. Der PVC-Alert (`OpenSearchStorageFull`) funktioniert dagegen ueber `kubelet_volume_stats_*` (kube-state-metrics) und ist aktiv. Naechster Schritt: OpenSearch Exporter evaluieren und deployen, dann Cluster-Health-Alert aktivieren.

**Alerting-Kanal:** Microsoft Teams Webhook (konfiguriert 2026-03-11).

### Phase 4: Grafana Dashboards (0,25 PT) — ⏳ OFFEN

**Standard-Dashboards (Import via ID):**

| Dashboard | Grafana ID | Zeigt |
|-----------|-----------|-------|
| Kubernetes Cluster Overview | 6417 | Node CPU/RAM/Disk, Pod Count |
| Kubernetes Pods | 15760 | Per-Pod Ressourcen |
| NGINX Ingress | 9614 | Request Rate, Latency, Errors |

**Custom Dashboard: Onyx API (manuell erstellen)**

Panels:
1. Request Rate (HTTP requests/sec) — `rate(http_requests_total[5m])` by status
2. Latency p50/p95/p99 — `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
3. Error Rate — `rate(http_requests_total{status=~"5.."}[5m])`
4. Slow Requests — `rate(onyx_api_slow_requests_total[5m])`
5. DB Pool — `onyx_db_pool_checked_out` / `_overflow`
6. DB Connection Hold Time — `histogram_quantile(0.95, rate(onyx_db_connection_hold_seconds_bucket[5m]))`

**Grafana-Zugriff:**
- DEV/TEST: `kubectl port-forward -n monitoring svc/monitoring-grafana 3001:80`
- PROD: Evaluieren ob Ingress mit Auth sinnvoll ist

---

## 5. PROD-Strategie

PROD = eigener Cluster (ADR-004). Monitoring wird als eigenstaendiger Stack deployed.

### 5.1 Architektur-Entscheidung

Kein Cross-Cluster-Monitoring. Jeder Cluster hat seinen eigenen Stack (Prometheus + Grafana + AlertManager + Exporter). Begruendung: ADR-004 (Blast Radius, eigenes Maintenance-Window). PROD-Monitoring darf nicht von DEV/TEST-Cluster abhaengen.

### 5.2 PROD-spezifische Konfiguration (Abweichungen von DEV/TEST)

| Parameter | DEV/TEST | PROD | Begruendung |
|-----------|----------|------|-------------|
| Scrape-Targets | `onyx-dev-api-service`, `onyx-test-api-service` | `onyx-prod-api-service.onyx-prod.svc.cluster.local:8080` | Eigener Cluster, nur 1 Namespace |
| Prometheus Retention | 30d | **90d** | PROD-Metriken muessen laenger aufbewahrt werden (Capacity Planning, Incident Review) |
| Prometheus Storage | 20 Gi | **50 Gi** | Laengere Retention = mehr Speicher |
| AlertManager Receiver | `teams-niko` (DEV/TEST-Kanal) | **Eigener PROD-Kanal** | ITIL: PROD-Alerts duerfen nicht in DEV-Rauschen untergehen |
| Grafana Dashboards | Manuell importiert | **Sidecar-Provisioning (gnetId)** | BSI OPS.1.1.2: Wiederherstellbarkeit. Kein manueller Zustand auf PROD |
| Grafana Ingress | `kubectl port-forward` | `kubectl port-forward` | Entscheidung Niko (2026-03-12): kein externer Zugang, nur Kubeconfig |
| `send_resolved` | `true` | `true` | Entwarnung bei Alert-Resolution |
| Alert-Rules | Original (20 Regeln) | **Tuned** (20 Regeln, PGHighRollbackRate + RedisCacheHitRateLow mit Mindest-Traffic Guard) | False Positives bei Idle-System vermeiden (2026-03-12) |
| coreDns ServiceMonitor | Aktiv (implizit) | **Deaktiviert** (`coreDns.enabled: false`) | StackIT-managed kube-system, kein Scrape-Zugriff |
| node-exporter CPU | 100m / 200m | **150m / 500m** | CPUThrottlingHigh behoben (27% Throttling) |
| PG Exporter CPU | 50m / 100m | **100m / 250m** | CPUThrottlingHigh behoben (49% Throttling) |
| Redis Exporter CPU | 25m / 50m | **50m / 150m** | CPUThrottlingHigh behoben (54% Throttling) |
| Prometheus retentionSize | 15 GB | **40 GB** | Mehr Headroom fuer 90d Retention |

### 5.3 Deployment-Anleitung

```bash
# 1. Kubeconfig auf PROD-Cluster wechseln
export KUBECONFIG=~/.kube/config-prod

# 2. Helm Repo (falls nicht vorhanden)
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# 3. Monitoring-Stack deployen (eigene PROD Values-Datei)
helm install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace \
  -f deployment/helm/values/values-monitoring-prod.yaml \
  --set grafana.adminPassword=<PASSWORD>

# 4. Exporter-Secrets erstellen (Daten aus terraform output + onyx-prod Secrets)
PG_PROD_PW=$(kubectl get secret onyx-dbreadonly -n onyx-prod -o jsonpath='{.data.db_readonly_password}' | base64 -d)
echo -n "postgresql://db_readonly_user:${PG_PROD_PW}@fdc7610c-91dc-4d0a-9652-adafe1a509cd.postgresql.eu01.onstackit.cloud:5432/onyx?sslmode=require" > /tmp/pg-dsn.txt
kubectl create secret generic pg-exporter-prod -n monitoring --from-file=DATA_SOURCE_NAME=/tmp/pg-dsn.txt
rm /tmp/pg-dsn.txt

REDIS_PROD_PW=$(kubectl get secret onyx-redis -n onyx-prod -o jsonpath='{.data.redis_password}' | base64 -d)
kubectl create secret generic redis-exporter-prod -n monitoring \
  --from-file=REDIS_ADDR=<(echo -n "onyx-prod.onyx-prod.svc.cluster.local:6379") \
  --from-file=REDIS_PASSWORD=<(echo -n "${REDIS_PROD_PW}")

# 5. Exporter deployen
bash deployment/k8s/monitoring-exporters/apply.sh

# 6. NetworkPolicies anwenden
bash deployment/k8s/network-policies/monitoring/apply.sh

# 7. Verifizierung
kubectl get pods -n monitoring
kubectl port-forward -n monitoring svc/monitoring-grafana 3001:80
# → http://localhost:3001 → Targets pruefen (3 Targets: onyx-api-prod, postgres-prod, redis-prod)
```

### 5.4 Vorbereitete Dateien

| Datei | Status | Beschreibung |
|-------|--------|-------------|
| `values-monitoring-prod.yaml` | ✅ Erstellt (2026-03-12) | Eigene PROD Values: 90d Retention, 50Gi Storage, PROD-only Targets, Teams-Receiver `teams-prod`, Sidecar-Dashboard-Provisioning |
| `pg-exporter-prod.yaml` | ✅ Erstellt (2026-03-11) | postgres_exporter PROD (Secret manuell erstellen) |
| `redis-exporter-prod.yaml` | ✅ Erstellt (2026-03-11) | redis_exporter PROD (Secret manuell erstellen) |
| `03-allow-scrape-egress.yaml` | ✅ Aktualisiert (2026-03-12) | `onyx-prod` Namespace hinzugefuegt |
| `apply.sh` (Exporters) | ✅ Aktualisiert (2026-03-12) | Auto-Detection DEV/TEST/PROD, PROD-Secrets Anleitung |
| `07-allow-redis-exporter-egress.yaml` | ✅ Aktualisiert (2026-03-12) | `onyx-prod` Namespace hinzugefuegt |
| `09-allow-backup-check-egress.yaml` | ✅ Erstellt (2026-03-15) | pg-backup-check CronJob → StackIT API (HTTPS:443) |
| NetworkPolicies (monitoring/) | ✅ Wiederverwendbar | `apply.sh` erkennt `onyx-prod` automatisch |

### 5.5 Offene Punkte

- [x] ~~Teams-Webhook-URL fuer PROD-Kanal~~ ✅ Separater Webhook erstellt, in `values-monitoring-prod.yaml` eingetragen (2026-03-12)
- [x] ~~NetworkPolicy `03-allow-scrape-egress.yaml` fuer PROD anpassen~~ ✅ `onyx-prod` hinzugefuegt (2026-03-12)
- [x] ~~Dashboard-Provisioning~~ ✅ Grafana Sidecar mit gnetId (PG: 14114, Redis: 763) in PROD Values (2026-03-12)
- [x] ~~Grafana Zugang PROD~~ ✅ Nur `kubectl port-forward`, kein Ingress (Entscheidung Niko, 2026-03-12)
- [x] ~~Helm install + Secrets + Exporter~~ ✅ Deployed auf PROD-Cluster (2026-03-12, Revision 3 → aktuell Rev 4). 9 Pods, 3/3 Targets UP. Alert-Tuning applied (Revision 3)
- [ ] NetworkPolicies `onyx-prod`: Kommt als vollstaendiges Set zusammen mit DNS/TLS-Hardening

---

## 6. Maintenance

| Aufgabe | Frequenz | Aufwand |
|---------|----------|---------|
| Helm Upgrade (kube-prometheus-stack) | Alle 2-3 Monate | ~30 Min |
| Prometheus Storage prüfen | Monatlich (via Grafana) | 5 Min |
| Alert-Rules anpassen | Bei Bedarf | 15 Min |
| Grafana Dashboards updaten | Bei Bedarf | 15 Min |

**Geschätzter laufender Aufwand:** ~2h/Quartal

---

## 7. Offene Fragen

| # | Frage | Wer | Status |
|---|-------|-----|--------|
| 1 | ~~Alerting-Kanal: Email, Slack, oder Webhook?~~ | Niko | ✅ Microsoft Teams Webhook konfiguriert (2026-03-11). Alerts werden an Teams-Kanal zugestellt. |
| 2 | ~~Grafana-Zugang für VÖB? (port-forward reicht oder Ingress?)~~ | Niko | ✅ Entscheidung (2026-03-12): Nur `kubectl port-forward` fuer alle Environments (DEV/TEST/PROD). Kein Ingress, kein externer Zugang. Zugriff nur mit Kubeconfig. |
| 3 | ~~Grafana Admin-Passwort: Wie verwalten?~~ | Niko | ✅ Per `--set grafana.adminPassword=<SECRET>` beim Install. Passwort liegt in K8s Secret `monitoring-grafana`. |
| 4 | Log-Aggregation (Loki) in Phase 2 oder später? | Niko | Offen |
| 5 | ~~SMTP-Server für AlertManager (Email-Versand)?~~ | Niko | ✅ Entfällt — Teams Webhook statt Email gewählt (2026-03-10). Kein SMTP nötig. |

---

## 8. Zeitleiste

| Phase | Was | Aufwand | Status |
|-------|-----|---------|--------|
| 1 | Health Probes aktivieren + `/metrics` verifizieren | 0,25 PT | ✅ Deployed (2026-03-10) |
| 2 | kube-prometheus-stack deployen + NetworkPolicies | 0,75 PT | ✅ Deployed (2026-03-10) |
| 3 | Alert-Rules konfigurieren | 0,25 PT | ✅ Deployed (2026-03-10), Teams Webhook konfiguriert (2026-03-11) |
| 4 | Grafana Dashboards (Standard + Onyx Custom) | 0,25 PT | ✅ PROD: Sidecar-Provisioning (gnetId). DEV/TEST: manuell importiert |
| 5 | PROD Monitoring Config + Deploy | 0,25 PT | ✅ Deployed (2026-03-12, Helm Rev 3 → Rev 4). Alert-Tuning applied |
| **Gesamt** | | **1,75 PT** | **1,75 PT erledigt, alle Phasen deployed** |

---

## 9. Deployment-Protokoll (2026-03-10)

### Ablauf

| Schritt | Aktion | Ergebnis |
|---------|--------|----------|
| 1 | Feature-Branch `feature/monitoring-stack` erstellt | OK |
| 2 | Health Probes in `values-common.yaml` (API httpGet + Webserver httpGet) | ⚠️ Webserver-Probes fehlgeschlagen (siehe Lessons Learned) |
| 3 | `values-monitoring.yaml` erstellt | OK |
| 4 | 5 NetworkPolicies für `monitoring` NS + 1 für App-NS erstellt | OK |
| 5 | 9 Alert-Rules in `values-monitoring.yaml` konfiguriert | OK |
| 6 | Merge auf `main` + Push | OK (Fast-forward) |
| 7 | DEV Deploy getriggert (`gh workflow run stackit-deploy.yml`) | ❌ Fehlgeschlagen — Webserver Readiness Probe 404 |
| 8 | `helm install monitoring prometheus-community/kube-prometheus-stack` | ✅ 7/7 Pods Running (70s) |
| 9 | Prometheus Targets geprüft — `onyx-api-dev` + `onyx-api-test` **down** | ❌ DNS-Fehler: `no such host` |
| 10 | Service-Name-Fix: `onyx-dev-api` → `onyx-dev-api-service` | ✅ nach `helm upgrade` |
| 11 | NetworkPolicies applied via `apply.sh` | ✅ 7 Policies erstellt (8. Policy `08-allow-alertmanager-webhook-egress.yaml` mit Alerting hinzugefügt) |
| 12 | Prometheus Targets erneut geprüft | ✅ **onyx-api-dev: UP, onyx-api-test: UP** |
| 13 | Webserver Probe Fix: httpGet → tcpSocket auf Port 3000 | ✅ Commit + Push + Redeploy |
| 14 | TEST Deploy (Nachmittag) — `--atomic --timeout 10m` | ❌ Timeout nach 10m, automatischer Rollback |
| 15 | CI/CD Fix: `--atomic` → `--wait`, Timeout 10m → 15m (alle Environments) | ✅ Commit `9cc09e2` |
| 16 | DEV + TEST Re-Deploy | ❌ StackIT Container Registry 503 (Outage ~15:15-16:50 UTC) |
| 17 | DEV + TEST Re-Deploy (nach Registry-Recovery) | ✅ DEV grün, ❌ TEST: API Server CrashLoop (7 Restarts) |
| 18 | Root Cause TEST: Liveness Probe killt Pod vor Startup (30s + 5×15s = 105s zu kurz) | Analyse via `kubectl describe pod` + `kubectl logs` |
| 19 | Probe-Fix: Liveness initialDelay 30→60s, failureThreshold 5→8 (180s Gnadenfrist) | ✅ Commit `8d4b9a6` |
| 20 | DEV Re-Deploy mit neuen Probe-Timeouts | ✅ DEV grün |
| 21 | TEST Re-Deploy mit neuen Probe-Timeouts | ❌ API CrashLoop: `TooManyConnectionsError` (RollingUpdate hält alte Pods mit DB-Connections) |
| 22 | Root Cause: RollingUpdate → alte + neue Pods gleichzeitig → PG Connection Pool erschöpft | Analyse via `kubectl logs` + `kubectl describe pod` |
| 23 | Fix: Recreate-Strategie via `kubectl patch deployment` auf alle 10 Deployments | ✅ Alle Pods terminiert + neu gestartet |
| 24 | CI/CD Fix: Recreate-Patch-Step in TEST Deploy-Job (analog DEV) | ✅ Commit `784577f` |
| 25 | TEST Re-Deploy mit Recreate-Strategie | ✅ **Alle 15 Pods Running, Smoke Test grün** |
| 26 | **Phase 4: Exporter-Deploy** — Secrets erstellt (4x im monitoring-NS) | ✅ pg-exporter-dev/test, redis-exporter-dev/test |
| 27 | NetworkPolicies: 2 neue Egress (PG:5432, Redis:6379) + 2 App-NS Ingress | ✅ 8 Policies in monitoring (inkl. AlertManager-Webhook-Egress), +2 in App-NS |
| 28 | K8s Manifeste applied: 4 Deployments + 4 Services im monitoring-NS | ✅ Alle 4 Exporter 1/1 Running |
| 29 | PG Exporter Health Probe Fix: `/healthz` → `/` (kein /healthz Endpoint) | ✅ Re-apply, Pods 1/1 |
| 30 | PG Exporter WAL Collector: `permission denied for pg_ls_waldir` → `--no-collector.wal` | ✅ Keine Fehler mehr |
| 31 | Helm Upgrade: 4 Scrape-Configs + 11 Alert-Rules in values-monitoring.yaml | ✅ Revision 3, 6 Targets UP, 20 Rules OK |
| 32 | Grafana Dashboards importiert: PostgreSQL (ID 14114) + Redis (ID 763) | ✅ Beide sichtbar in Grafana |

### Lessons Learned

**1. Webserver HTTP Probes funktionieren nicht (kritisch)**

Next.js Webserver hat KEINEN eigenen Health-Endpoint. `/api/*`-Proxy läuft über NGINX Ingress Controller, nicht über Next.js intern. Daher:
- `GET /api/health:3000` → 404 (Route existiert nicht in Next.js)
- `GET /:3000` → Timeout bei Kaltstart (SSR-Kompilierung, Redirect-Chain `/ → /app → /auth/login`)
- **Fix:** TCP Socket Probe auf Port 3000 (prüft ob Prozess Connections annimmt)

**2. Onyx Service-Namen haben Suffix `-service` (mittel)**

Helm Chart erstellt Services mit Pattern `<release>-<component>-service` (z.B. `onyx-dev-api-service`), nicht `<release>-<component>` (z.B. `onyx-dev-api`). Scrape-Targets mussten korrigiert werden.
- **Prüfung:** `kubectl get svc -n <namespace>` vor Konfiguration

**3. NetworkPolicy für K8s API fehlte im Entwurf (mittel)**

prometheus-operator, kube-state-metrics und Prometheus Service Discovery brauchen Zugriff auf den K8s API Server (Port 443). Ohne `05-allow-k8s-api-egress.yaml` funktioniert kein CRD-Watch, kein Cluster-State-Scraping und keine automatische Target-Erkennung.

**4. StackIT/Gardener DNS-Port 8053 (niedrig)**

CoreDNS auf StackIT mappt Port 53 → 8053 (DNAT). NetworkPolicy für DNS muss beide Ports erlauben. War bereits aus SEC-03 bekannt und korrekt implementiert.

**5. `--atomic` ist kontraproduktiv bei langsamem Startup (kritisch)**

`helm upgrade --atomic --timeout 10m` rollt automatisch zurück wenn der Timeout erreicht wird. Bei 15 Pods mit Cold Start (Alembic Migrations, Model Server Download) ist das kontraproduktiv — der Rollback verursacht einen weiteren Neustart-Zyklus. Fix: `--wait --timeout 15m` — wartet auf Readiness, rollt aber bei Timeout nicht zurück. Der Release bleibt stehen und kann debuggt werden.

**6. Liveness Probe darf Pod nicht vor Startup killen (kritisch)**

Ursprüngliche API Liveness Probe: `initialDelaySeconds: 30`, `failureThreshold: 5`, `periodSeconds: 15`. Das bedeutet: nach 30s + 5×15s = **105s** wird der Pod gekillt. Auf TEST braucht der API Server aber länger (Alembic Migrations + FastAPI Startup + Extension-Hooks). Resultat: CrashLoop mit 7 Restarts, `connection refused` in Probe-Logs.

Fix: `initialDelaySeconds: 60`, `failureThreshold: 8` → **180s Gnadenfrist**. Faustregel: Liveness Timeout sollte mindestens 2× die beobachtete Startup-Zeit sein.

| Probe | Vorher | Nachher | Max Startup-Zeit |
|-------|--------|---------|-----------------|
| Readiness | 15s + 3×10s = 45s | 30s + 6×10s = 90s | 90s bis ready |
| Liveness | 30s + 5×15s = 105s | 60s + 8×15s = 180s | 180s bis Kill |

**7. StackIT Container Registry Outage (informativ)**

Am 2026-03-10 ~15:15-16:50 UTC war `registry.onstackit.cloud` nicht erreichbar (HTTP 503). Docker Login schlug fehl, Build-Jobs scheiterten. Kein Einfluss auf laufende Pods (Images bereits gepullt). Recovery ohne eigenes Zutun. Empfehlung: `imagePullPolicy: IfNotPresent` (bereits gesetzt) schützt laufende Deployments vor Registry-Ausfällen.

**8. RollingUpdate erschöpft DB Connection Pool (kritisch)**

Bei RollingUpdate laufen alte und neue Pods gleichzeitig. Jeder API-Server-Pod hält ~20 DB-Connections (SQLAlchemy Pool). Bei 2 gleichzeitigen Pods → 40 Connections auf StackIT Managed PG Flex (Default `max_connections = 100`, abzüglich Reserved + System). Resultat: `TooManyConnectionsError` / `pg_use_reserved_connections` → neuer Pod startet nicht → CrashLoop.

Fix: **Recreate-Strategie** für alle Onyx-Deployments. Alle alten Pods werden zuerst terminiert, dann starten neue Pods. Kurze Downtime (~30-60s), dafür keine Connection-Konflikte. Wird im CI/CD via `kubectl patch` nach `helm upgrade` angewendet (Helm setzt Strategy auf RollingUpdate, Patch überschreibt).

| Strategie | Vorteil | Nachteil | Onyx-Eignung |
|-----------|---------|----------|-------------|
| RollingUpdate | Zero-Downtime | Connection-Pool-Exhaustion bei DB-intensiven Apps | ❌ Nicht geeignet |
| Recreate | Sauberer Neustart, kein Connection-Konflikt | Kurze Downtime | ✅ **Gewählt** |

**9. postgres_exporter Health Probe `/healthz` existiert nicht (niedrig)**

postgres_exporter (prometheuscommunity) hat keinen `/healthz` Endpoint. `/` liefert eine Landing-Page (HTTP 200). Readiness/Liveness Probes muessen auf `/` zeigen, nicht `/healthz`. redis_exporter hat dagegen `/healthz` (funktioniert).

**10. postgres_exporter WAL Collector braucht pg_monitor (mittel)**

Der WAL Collector ruft `pg_ls_waldir()` auf — braucht `pg_monitor` Rolle. StackIT Managed PG Flex unterstuetzt nur `login` + `createdb` via Terraform. Fix: `--no-collector.wal` als Container-Argument. Alle anderen Collectors (stat_database, stat_user_tables, locks, database_size) funktionieren ohne pg_monitor. `pg_stat_activity` zeigt nur eigene Sessions — daher `pg_stat_database_numbackends` fuer Connection-Monitoring.

### Deployed Pods

```
$ kubectl get pods -n monitoring  (nach Phase 4 Exporter-Deploy, DEV/TEST Shared Cluster)
NAME                                                     READY   STATUS    AGE
alertmanager-monitoring-kube-prometheus-alertmanager-0   2/2     Running   ~5h
monitoring-grafana-5548f645df-cclq8                      3/3     Running   ~5h
monitoring-kube-prometheus-operator-78fbcc9cdb-pxp82     1/1     Running   ~5h
monitoring-kube-state-metrics-6b4845b878-5lznr           1/1     Running   ~5h
monitoring-prometheus-node-exporter-x2gzh                1/1     Running   ~5h (Node 1)
monitoring-prometheus-node-exporter-x2xn9                1/1     Running   ~5h (Node 2)
postgres-exporter-dev-748c958db6-wt7hw                   1/1     Running   ~10m
postgres-exporter-test-9ff8dd4fd-xflqk                   1/1     Running   ~10m   # HINWEIS: TEST heruntergefahren seit 2026-03-19 (Exporter laeuft noch, Target onyx-test hat 0 Pods)
prometheus-monitoring-kube-prometheus-prometheus-0       2/2     Running   ~5h
redis-exporter-dev-74c6f94956-ndd7j                      1/1     Running   ~10m
redis-exporter-test-7648fc9f-cvzdb                       1/1     Running   ~10m   # HINWEIS: TEST heruntergefahren seit 2026-03-19 (Exporter laeuft noch, Target onyx-test hat 0 Pods)

# Zustand DEV (onyx-dev Namespace): 17 Pods Running
# Zustand TEST (onyx-test Namespace): 0 Pods — dauerhaft heruntergefahren seit 2026-03-19
```

### NetworkPolicies

```
$ kubectl get networkpolicies -n monitoring
NAME                                POD-SELECTOR                        AGE
allow-alertmanager-webhook-egress   app.kubernetes.io/name=alertmanager  ~5h  (Phase 3)
allow-backup-check-egress           app=pg-backup-check                 ~7d  (2026-03-15)
allow-dns-egress                    <none>                              ~5h
allow-intra-namespace               <none>                              ~5h
allow-k8s-api-egress                <none>                              ~5h
allow-pg-exporter-egress            app=postgres-exporter               ~10m  (Phase 4)
allow-prometheus-scrape             app.kubernetes.io/name=prometheus    ~5h
allow-redis-exporter-egress         app=redis-exporter                  ~10m  (Phase 4)
default-deny-all                    <none>                              ~5h

$ kubectl get networkpolicies -n onyx-dev | grep -E "monitoring|redis-exporter"
allow-monitoring-scrape        <none>                              ~5h
allow-redis-exporter-ingress   redis_setup_type=standalone         ~10m  (Phase 4)
# Analog in onyx-test
```

### Dateien

| Datei | Typ | Beschreibung |
|-------|-----|-------------|
| `deployment/helm/values/values-common.yaml` | Geändert | Health Probes für API + Webserver |
| `deployment/helm/values/values-monitoring.yaml` | Neu | kube-prometheus-stack Values + Alert-Rules |
| `deployment/k8s/network-policies/monitoring/01-default-deny-all.yaml` | Neu | Zero-Trust Baseline |
| `deployment/k8s/network-policies/monitoring/02-allow-dns-egress.yaml` | Neu | DNS (53+8053) |
| `deployment/k8s/network-policies/monitoring/03-allow-scrape-egress.yaml` | Neu | Prometheus → onyx-dev/test:8080 |
| `deployment/k8s/network-policies/monitoring/04-allow-intra-namespace.yaml` | Neu | Intra-Namespace |
| `deployment/k8s/network-policies/monitoring/05-allow-k8s-api-egress.yaml` | Neu | K8s API (443) |
| `deployment/k8s/network-policies/monitoring/apply.sh` | Geändert | Sichere Apply-Reihenfolge (5→7 Steps + App-NS Policies) |
| `deployment/k8s/network-policies/06-allow-monitoring-scrape.yaml` | Neu | App-NS: Ingress von monitoring:8080 |
| `deployment/k8s/monitoring-exporters/pg-exporter-dev.yaml` | Neu (Phase 4) | postgres_exporter DEV (Deployment + Service) |
| `deployment/k8s/monitoring-exporters/pg-exporter-test.yaml` | Neu (Phase 4) | postgres_exporter TEST (Deployment + Service) |
| `deployment/k8s/monitoring-exporters/redis-exporter-dev.yaml` | Neu (Phase 4) | redis_exporter DEV (Deployment + Service) |
| `deployment/k8s/monitoring-exporters/redis-exporter-test.yaml` | Neu (Phase 4) | redis_exporter TEST (Deployment + Service) |
| `deployment/k8s/monitoring-exporters/pg-exporter-prod.yaml` | Neu (PROD) | postgres_exporter PROD (Deployment + Service) |
| `deployment/k8s/monitoring-exporters/redis-exporter-prod.yaml` | Neu (PROD) | redis_exporter PROD (Deployment + Service) |
| `deployment/k8s/monitoring-exporters/apply.sh` | Aktualisiert (PROD) | Deploy-Script mit Auto-Detection DEV/TEST/PROD |
| `deployment/helm/values/values-monitoring-prod.yaml` | Neu (PROD) | PROD Monitoring Values (90d, 50Gi, Sidecar-Dashboards, Teams-PROD) |
| `deployment/k8s/network-policies/monitoring/06-allow-pg-exporter-egress.yaml` | Neu (Phase 4) | PG Exporter → StackIT PG:5432 |
| `deployment/k8s/network-policies/monitoring/07-allow-redis-exporter-egress.yaml` | Neu (Phase 4) | Redis Exporter → onyx-dev/test/prod:6379 |
| `deployment/k8s/network-policies/monitoring/08-allow-alertmanager-webhook-egress.yaml` | Neu (Phase 3) | AlertManager → Teams Webhook (HTTPS:443) |
| `deployment/k8s/network-policies/monitoring/09-allow-backup-check-egress.yaml` | Neu (2026-03-15) | pg-backup-check CronJob → StackIT API (HTTPS:443) |
| `deployment/k8s/network-policies/07-allow-redis-exporter-ingress.yaml` | Neu (Phase 4) | App-NS: Ingress von Redis Exporter |
| `docs/technisches-feinkonzept/monitoring-exporter.md` | Neu (Phase 4) | Modulspezifikation v0.3 |

### Commits

#### Phase 1-3 (Monitoring-Stack)

| SHA | Nachricht |
|-----|-----------|
| `4a0d262` | `feat(helm): Monitoring-Stack vorbereiten (Health Probes + kube-prometheus-stack)` |
| `91e6987` | `fix(helm): Prometheus scrape targets auf korrekte Service-Namen anpassen` |
| `7fe7e8e` | `fix(helm): Webserver Health Probes auf tcpSocket umstellen` |
| `21dceba` | `fix(helm): HSTS-Header ergänzen (BSI TR-02102)` |
| `9cc09e2` | `fix(ci): Helm Deploy Timeout auf 15m erhöhen, --atomic durch --wait ersetzen` |
| `8d4b9a6` | `fix(helm): API Health Probe Timeouts erhöhen (Liveness killt Pod vor Startup)` |
| `784577f` | `fix(ci): Recreate-Strategie für TEST Deploy (analog DEV)` |
| `155975e` | `docs(monitoring): Deployment-Protokoll + Recreate-Fix dokumentieren` |
| `635391e` | `spec(monitoring): Modulspezifikation postgres_exporter + redis_exporter (v0.2)` |

#### Phase 4 (Exporters + Dashboards)

Commit noch ausstehend — Dateien auf Feature-Branch `feature/monitoring-exporter`.

### Zusätzliche Änderungen (gleiche Session)

| SHA | Nachricht | Bezug |
|-----|-----------|-------|
| `7947862` | `chore(stackit-infra): prevent_destroy für kritische Ressourcen` | Terraform Safety |
| `6d7592e` | `docs(ext-entwicklungsplan): ext-analytics als übersprungen markieren` | Phase 4e |

### Verifizierte Metriken (Phase 4, 2026-03-10)

| Metrik | DEV | TEST |
|--------|-----|------|
| PG Active Backends | 52 | 52 |
| PG DB Size | 17.0 MB | 17.3 MB |
| PG Cache Hit Ratio | 100% | 100% |
| Redis Memory Used | 4.4 MB | 4.5 MB |
| Redis Connected Clients | 126 | 146 |

### Grafana Dashboards

| Dashboard | Grafana UID | Quelle |
|-----------|------------|--------|
| PostgreSQL Exporter (VÖB) | `pg-exporter-dashboard` | grafana.com ID 14114 |
| Redis Dashboard for Prometheus Redis Exporter 1.x | auto-generated | grafana.com ID 763 |

**Hinweis:** Dashboards sind manuell importiert (nicht als ConfigMap persistent). Bei Grafana-Pod-Restart gehen sie verloren. Fuer PROD: Dashboards als ConfigMap provisionieren.

### Alerting-Kanal

**Entscheidung (Niko, 2026-03-10): Microsoft Teams statt SMTP.**

✅ **Konfiguriert (2026-03-11):** Teams Incoming Webhook in `values-monitoring.yaml` eingetragen. Receiver `teams-niko` mit `msteams_configs`. Alerts werden bei Trigger an den Teams-Kanal zugestellt (inkl. `send_resolved: true` für Entwarnung).

---

## 10. PROD Deployment-Protokoll (2026-03-12)

### Ablauf

| Schritt | Aktion | Ergebnis |
|---------|--------|----------|
| 1 | `values-monitoring-prod.yaml` erstellt (90d Retention, 50Gi, PROD-only Targets, Teams-PROD Webhook, Sidecar-Dashboards) | ✅ |
| 2 | `03-allow-scrape-egress.yaml` + `07-allow-redis-exporter-egress.yaml` um `onyx-prod` ergaenzt | ✅ |
| 3 | `apply.sh` (Exporters) rewrite: Auto-Detection DEV/TEST/PROD | ✅ |
| 4 | Teams PROD Webhook-URL eingetragen (separater Kanal) | ✅ |
| 5 | PROD Kubeconfig verifiziert (`~/.kube/config-prod`) — Cluster `vob-prod` erreichbar | ✅ |
| 6 | `helm install monitoring` mit `values-monitoring-prod.yaml` | ❌ Timeout: Grafana Init-Container CrashLoop |
| 7 | Root Cause: Dashboard-Download nach `/var/lib/grafana/dashboards/voeb/` — Verzeichnis `voeb/` existiert nicht | Analyse via `kubectl logs -c download-dashboards` |
| 8 | Fix: `dashboards.voeb` → `dashboards.default` in Values (Standard-Verzeichnis) | ✅ |
| 9 | `helm upgrade` — alle 7 Basis-Pods Running, Grafana 3/3 | ✅ |
| 10 | Exporter-Secrets erstellt: `pg-exporter-prod`, `redis-exporter-prod` | ✅ |
| 11 | Exporter deployed: `pg-exporter-prod` + `redis-exporter-prod` (1/1 Running) | ✅ |
| 12 | Monitoring NetworkPolicies applied (9 in monitoring NS, inkl. AlertManager-Webhook-Egress + Backup-Check-Egress) | ✅ |
| 13 | App-NS Policies applied (`allow-monitoring-scrape` + `allow-redis-exporter-ingress` in `onyx-prod`) | ❌ **PROD-App kaputt** |
| 14 | Root Cause: PROD hatte keine Basis-NetworkPolicies (kein default-deny, kein allow-intra). Monitoring-Policies erzeugten implizite Denies → External Traffic + Onyx→Redis blockiert | Analyse: API Health 503, Celery Restarts |
| 15 | **Sofort-Fix:** Alle 3 Policies aus `onyx-prod` entfernt | ✅ API Health OK, 19 Pods stabil |
| 16 | Prometheus Targets: API ✅ UP, PG ✅ UP, Redis ❌ DOWN (context deadline exceeded) | Nur Redis-Exporter betroffen |
| 17 | Root Cause Redis: `07-allow-redis-exporter-egress.yaml` hatte nur `onyx-dev` + `onyx-test`, NICHT `onyx-prod` | Fix: `onyx-prod` Namespace hinzugefuegt |
| 18 | Policy applied + Redis-Exporter Rollout Restart | ✅ |
| 19 | **Alle 3 Targets UP:** onyx-api-prod, postgres-prod, redis-prod | ✅ |

### Endstatus

```
$ KUBECONFIG=~/.kube/config-prod kubectl get pods -n monitoring
NAME                                                     READY   STATUS    AGE
alertmanager-monitoring-kube-prometheus-alertmanager-0   2/2     Running   ~86m
monitoring-grafana-5bfb9bb69-sbs4p                       3/3     Running   ~13m
monitoring-kube-prometheus-operator-78fbcc9cdb-thbdm     1/1     Running   ~86m
monitoring-kube-state-metrics-6b4845b878-9hp4z           1/1     Running   ~86m
monitoring-prometheus-node-exporter-5b8lb                1/1     Running   ~86m (Node 1)
monitoring-prometheus-node-exporter-qxf68                1/1     Running   ~86m (Node 2)
postgres-exporter-prod-9c55cb894-mjj98                   1/1     Running   ~11m
prometheus-monitoring-kube-prometheus-prometheus-0       2/2     Running   ~86m
redis-exporter-prod-5444f47bf8-kfkhc                     1/1     Running   ~2m

Prometheus Targets:
  onyx-api-prod    UP
  postgres-prod    UP
  redis-prod       UP

# Zustand PROD (onyx-prod Namespace): 20 Pods Running (Helm Rev 4)
```

### NetworkPolicies (PROD-Cluster)

| Namespace | Policies | Bemerkung |
|-----------|----------|-----------|
| `monitoring` | 9 (default-deny + 8 allow, inkl. AlertManager-Webhook-Egress + Backup-Check-Egress) | ✅ Vollstaendig, Zero-Trust |
| `onyx-prod` | 0 | ⚠️ Bewusst leer — Full Setup kommt mit DNS/TLS-Hardening |

### Lessons Learned

**11. App-NS Monitoring-Policies NICHT ohne Basis-Policies anwenden (kritisch)**

Auf DEV/TEST funktionieren `allow-monitoring-scrape` und `allow-redis-exporter-ingress` problemlos, weil dort seit SEC-03 (2026-03-05) ein vollstaendiges NetworkPolicy-Set existiert (default-deny + allow-intra + allow-dns + allow-external-egress). Die Basis-Policies erlauben normalen Betrieb, die Monitoring-Policies fuegen nur zusaetzliche Ingress-Regeln hinzu.

Auf PROD existierten noch **keine** Basis-Policies. Durch das Anwenden von `allow-monitoring-scrape` (policyTypes: [Ingress], podSelector: {}) wurde fuer ALLE Pods in `onyx-prod` ein implizites Ingress-Deny aktiv. Nur Ingress von `monitoring:8080` war erlaubt — externer Traffic zum NGINX LoadBalancer wurde blockiert. Zusaetzlich brach `allow-redis-exporter-ingress` die Onyx→Redis-Verbindung (nur Redis-Exporter-Ingress erlaubt, nicht Onyx-App-Ingress).

**Impact:** PROD-API nicht erreichbar (~5 Minuten), Celery-Worker Restarts durch Redis-Verbindungsabbruch.

**Fix:** Alle Policies aus `onyx-prod` entfernt. Monitoring in `monitoring` NS laeuft unabhaengig und scraped ueber Cross-Namespace-Egress (ohne `onyx-prod`-Policies noetig, da `onyx-prod` keine Ingress-Restriction hat).

**Regel:** App-NS NetworkPolicies muessen IMMER als vollstaendiges Set angewendet werden (Basis + Monitoring). Niemals einzelne Allow-Policies ohne Default-Deny + Allow-Intra. Fuer PROD: Full-Set kommt zusammen beim DNS/TLS-Hardening.

**12. Grafana Dashboard gnetId: Verzeichnisname muss `default` sein (niedrig)**

Grafana Helm Chart Download-Init-Container erstellt `mkdir -p /var/lib/grafana/dashboards` aber NICHT Unterverzeichnisse fuer Custom-Keys (z.B. `voeb`). Download scheitert mit `can't create ... nonexistent directory`. Fix: `dashboards.default` statt `dashboards.voeb` verwenden.

**13. Egress-Policies muessen ALLE Namespaces abdecken (mittel)**

`07-allow-redis-exporter-egress.yaml` hatte nur `onyx-dev` + `onyx-test` als Ziel-Namespaces. Auf dem PROD-Cluster (wo nur `onyx-prod` existiert) konnte der Redis-Exporter Redis nicht erreichen. Analog fehlte `onyx-prod` in `03-allow-scrape-egress.yaml`. **Regel:** Bei neuen Namespaces/Environments ALLE Egress-Policies pruefen und erweitern.

### Dateien (PROD Monitoring)

| Datei | Aktion | Beschreibung |
|-------|--------|-------------|
| `deployment/helm/values/values-monitoring-prod.yaml` | Neu | PROD Monitoring Values (90d, 50Gi, Sidecar-Dashboards, Teams-PROD) |
| `deployment/k8s/monitoring-exporters/pg-exporter-prod.yaml` | Vorhanden (2026-03-11) | postgres_exporter PROD |
| `deployment/k8s/monitoring-exporters/redis-exporter-prod.yaml` | Vorhanden (2026-03-11) | redis_exporter PROD |
| `deployment/k8s/monitoring-exporters/apply.sh` | Rewrite | Auto-Detection DEV/TEST/PROD |
| `deployment/k8s/network-policies/monitoring/03-allow-scrape-egress.yaml` | Ergaenzt | `onyx-prod` Namespace hinzugefuegt |
| `deployment/k8s/network-policies/monitoring/07-allow-redis-exporter-egress.yaml` | Ergaenzt | `onyx-prod` Namespace hinzugefuegt |

---

## Änderungshistorie

| Version | Datum | Autor | Änderung |
|---------|-------|-------|----------|
| v0.3 | 2026-03-12 | COFFEESTUDIOS | PROD-Deployment, Teams-Alerting |
| v0.3.1 | 2026-03-14 | COFFEESTUDIOS | Audit-Korrektur: NP 7→8, Kickoff-Referenz, Änderungshistorie |
| v0.4 | 2026-03-19 | COFFEESTUDIOS | OpenSearch als ueberwachte Komponente hinzugefuegt: PVC Alert (`OpenSearchStorageFull`). Vespa-Monitoring auf Alive-Check reduziert (Zombie-Mode). |
| v0.5 | 2026-03-22 | COFFEESTUDIOS | Helm Rev 3→4. Pod-Counts aktualisiert (DEV 16→17, TEST 15→0 heruntergefahren, PROD 19→20). PROD CPU Requests korrigiert (~8.750→~7.850m). Alert-Tabelle mit YAML-Realitaet abgeglichen: 20 Regeln DEV/TEST, 22 PROD. `OpenSearchClusterRed` als GEPLANT (nicht implementiert) dokumentiert. NP 8→9 (`09-allow-backup-check-egress.yaml` ergaenzt). Scrape-Egress Inline-YAML um `onyx-prod` ergaenzt. Entscheidungstabelle Vespa-Eintrag aktualisiert. |
