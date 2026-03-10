# Monitoring-Konzept — VÖB Service Chatbot

> **Status:** ✅ Deployed (2026-03-10) — Phase 1-3 live, Phase 4 (Dashboards) offen
> **Entscheidung:** Self-Hosted kube-prometheus-stack (Niko, 2026-03-10)
> **Scope:** DEV + TEST (Shared Cluster), PROD-Vorbereitung
> **Compliance:** BSI DER.1 (Detektion), BSI OPS.1.1.5 (Protokollierung), BAIT Kap. 5
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
| AlertManager (Alerting) | ✅ Deployed (2026-03-10) | 9 Alert-Rules, Email-Kanal konfiguriert (SMTP offen) |
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
| Metriken-Abdeckung | Nur API (externer Scrape) | Alles (API, Redis, Vespa, Celery, Nodes) | **Self-Hosted** |
| Maintenance | Null | ~30 Min/Quartal (Helm Upgrade) | Managed |
| Cluster-Ressourcen | 0 | ~1,1 vCPU, ~1,9 Gi RAM | Managed |
| K8s-native (ServiceMonitor) | Nein (externer Scrape) | Ja (CRDs) | **Self-Hosted** |

**Entscheidende Faktoren:**
1. **Kosten:** 840 EUR/Jahr gespart bei einem Projekt das auf Kosten achtet
2. **Abdeckung:** Managed sieht nur den API-Server. Self-Hosted sieht alles.
3. **Für vollständige Abdeckung mit Managed** bräuchte man trotzdem einen In-Cluster-Agent (Grafana Alloy) → dann hat man einen Pod im Cluster UND zahlt 70 EUR/Mo

### Verworfene Alternative: StackIT Managed Observability

StackIT bietet `Observability-Starter-EU01` (70 EUR/Mo) mit Prometheus + Grafana + Alerting. Terraform-native (6 Resources: `stackit_observability_instance`, `_credential`, `_scrapeconfig`, `_alertgroup`, `_logalertgroup`, `_loadbalancer_observability_credential`). Für Projekte ohne K8s-Expertise oder mit kleinem Cluster wäre das die bessere Wahl. Hier nicht gewählt wegen Kosten und eingeschränkter Abdeckung.

---

## 3. Ressourcen-Validierung

### Cluster-Budget: Passt es?

**Aktuell belegt (DEV + TEST + System):**

| | CPU Requests | RAM Requests | CPU Limits | RAM Limits |
|---|---|---|---|---|
| DEV (16 Pods) | 2.950m | 7,5 Gi | 8.750m | 24 Gi |
| TEST (15 Pods) | 2.950m | 7,5 Gi | 8.750m | 24 Gi |
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
| PROD (16 Pods) | ~4.500m | ~9 Gi | ~11.000m | ~28 Gi |
| System | ~500m | ~1 Gi | ~800m | ~2 Gi |
| Monitoring | 1.100m | 1,9 Gi | 2.250m | 3,8 Gi |
| **Gesamt PROD** | **6.100m** | **~12 Gi** | **14.050m** | **~34 Gi** |
| **Auslastung** | **39%** | **21%** | **89%** | **60%** |

**PROD: Kein Problem.** Monitoring passt komfortabel.

---

## 4. Implementierungsplan

### Phase 1: Health Probes aktivieren (0,25 PT) — ✅ DEPLOYED

**Status:** ✅ Deployed auf DEV (2026-03-10). TEST-Deploy ausstehend (`gh workflow run stackit-deploy.yml -f environment=test`).

**values-common.yaml — finale Konfiguration:**

```yaml
api:
  # /health ist PUBLIC_ENDPOINT (keine Auth), existiert in Onyx FOSS
  readinessProbe:
    httpGet:
      path: /health
      port: 8080
    initialDelaySeconds: 15
    periodSeconds: 10
    failureThreshold: 3
    timeoutSeconds: 5
  livenessProbe:
    httpGet:
      path: /health
      port: 8080
    initialDelaySeconds: 30
    periodSeconds: 15
    failureThreshold: 5
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
      receiver: "email-niko"
      routes:
        - match:
            severity: critical
          repeat_interval: 1h
          receiver: "email-niko"
    receivers:
      - name: "email-niko"
        email_configs:
          - to: "nikolaj.ivanov@coffee-studios.de"
            from: "alertmanager@voeb-chatbot.local"
            smarthost: "localhost:25"  # TODO: SMTP-Server konfigurieren
            require_tls: false
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

**2.3 NetworkPolicy für Monitoring-Namespace** — ✅ Applied (2026-03-10)

**Status:** 5 Policies in `monitoring` + 1 Policy in `onyx-dev` + `onyx-test` applied.

Der Monitoring-Namespace braucht:
- Egress zu `onyx-dev` und `onyx-test` (Scraping auf Port 8080)
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

**Status:** 9 Regeln aktiv in `values-monitoring.yaml` unter `additionalPrometheusRulesMap`. AlertManager konfiguriert mit Email an `nikolaj.ivanov@coffee-studios.de` (SMTP-Server noch zu konfigurieren).

**Empfohlene Alert-Rules:**

| Alert | PromQL | Severity | Beschreibung |
|-------|--------|----------|-------------|
| `APIDown` | `up{job=~"onyx-api.*"} == 0` for 2m | critical | API nicht erreichbar |
| `PodCrashLooping` | `increase(kube_pod_container_status_restarts_total{namespace=~"onyx-.*"}[1h]) > 3` for 5m | critical | Pod restartet wiederholt |
| `HighErrorRate` | `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05` for 5m | warning | >5% Server Errors |
| `DBPoolExhausted` | `onyx_db_pool_overflow > 0` for 5m | warning | DB Connection Pool Overflow |
| `HighSlowRequests` | `rate(onyx_api_slow_requests_total[5m]) > 1` for 10m | warning | >1 Slow Request/Sek |
| `NodeMemoryPressure` | `node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes < 0.1` for 5m | critical | <10% freier RAM auf Node |
| `NodeDiskPressure` | `node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes < 0.15` for 5m | warning | <15% freier Disk auf Node |
| `VespaStorageFull` | `kubelet_volume_stats_available_bytes{persistentvolumeclaim=~"vespa.*"} / kubelet_volume_stats_capacity_bytes < 0.2` for 10m | warning | Vespa PVC <20% frei |
| `CertExpiringSoon` | `certmanager_certificate_expiration_timestamp_seconds - time() < 14*24*3600` for 1h | warning | Zertifikat läuft in <14 Tagen ab |

**Alerting-Kanal:** Noch zu klären (Email, Slack, Webhook). Wird in AlertManager-Config konfiguriert.

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

PROD = eigener Cluster (ADR-004). Monitoring wird identisch deployed:

```bash
helm install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace \
  -f deployment/helm/values/values-monitoring.yaml \
  --set prometheus.prometheusSpec.additionalScrapeConfigs[0].static_configs[0].targets[0]="onyx-prod-api-service.onyx-prod.svc.cluster.local:8080" \
  --set prometheus.prometheusSpec.additionalScrapeConfigs[0].static_configs[0].labels.environment="prod"
```

Kein Cross-Cluster-Monitoring nötig. Jeder Cluster hat seinen eigenen Stack.

Für PROD zusätzlich:
- Grafana Ingress mit Auth (Entra ID oder Basic Auth)
- AlertManager mit produktivem Alerting-Kanal
- `prometheus.prometheusSpec.retention: 90d` (statt 30d)
- Storage: 50 Gi (statt 20 Gi)

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
| 1 | ~~Alerting-Kanal: Email, Slack, oder Webhook?~~ | Niko | ✅ Email konfiguriert (`nikolaj.ivanov@coffee-studios.de`). SMTP-Server fehlt noch (Platzhalter `localhost:25`). |
| 2 | Grafana-Zugang für VÖB? (port-forward reicht oder Ingress?) | Niko/VÖB | Entscheidung: port-forward für DEV/TEST (Enterprise Best Practice: kein externer Zugang). Für PROD: Ingress mit Entra ID evaluieren. |
| 3 | ~~Grafana Admin-Passwort: Wie verwalten?~~ | Niko | ✅ Per `--set grafana.adminPassword=<SECRET>` beim Install. Passwort liegt in K8s Secret `monitoring-grafana`. |
| 4 | Log-Aggregation (Loki) in Phase 2 oder später? | Niko | Offen |
| 5 | SMTP-Server für AlertManager (Email-Versand)? | Niko | Neu. Optionen: StackIT Mailservice, externer SMTP, oder Webhook statt Email. |

---

## 8. Zeitleiste

| Phase | Was | Aufwand | Status |
|-------|-----|---------|--------|
| 1 | Health Probes aktivieren + `/metrics` verifizieren | 0,25 PT | ✅ Deployed (2026-03-10) |
| 2 | kube-prometheus-stack deployen + NetworkPolicies | 0,75 PT | ✅ Deployed (2026-03-10) |
| 3 | Alert-Rules konfigurieren | 0,25 PT | ✅ Deployed (2026-03-10), SMTP offen |
| 4 | Grafana Dashboards (Standard + Onyx Custom) | 0,25 PT | ⏳ Offen |
| **Gesamt** | | **1,5 PT** | **1,25 PT erledigt** |

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
| 11 | NetworkPolicies applied via `apply.sh` | ✅ 7 Policies erstellt |
| 12 | Prometheus Targets erneut geprüft | ✅ **onyx-api-dev: UP, onyx-api-test: UP** |
| 13 | Webserver Probe Fix: httpGet → tcpSocket auf Port 3000 | ✅ Commit + Push + Redeploy |

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

### Deployed Pods

```
$ kubectl get pods -n monitoring
NAME                                                     READY   STATUS    AGE
alertmanager-monitoring-kube-prometheus-alertmanager-0   2/2     Running   ~5m
monitoring-grafana-5548f645df-cclq8                      3/3     Running   ~5m
monitoring-kube-prometheus-operator-78fbcc9cdb-pxp82     1/1     Running   ~5m
monitoring-kube-state-metrics-6b4845b878-5lznr           1/1     Running   ~5m
monitoring-prometheus-node-exporter-x2gzh                1/1     Running   ~5m (Node 1)
monitoring-prometheus-node-exporter-x2xn9                1/1     Running   ~5m (Node 2)
prometheus-monitoring-kube-prometheus-prometheus-0       2/2     Running   ~5m
```

### NetworkPolicies

```
$ kubectl get networkpolicies -n monitoring
NAME                        POD-SELECTOR                        AGE
allow-dns-egress            <none>                              ~5m
allow-intra-namespace       <none>                              ~5m
allow-k8s-api-egress        <none>                              ~5m
allow-prometheus-scrape     app.kubernetes.io/name=prometheus    ~5m
default-deny-all            <none>                              ~5m

$ kubectl get networkpolicies -n onyx-dev | grep monitoring
allow-monitoring-scrape     <none>                              ~5m
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
| `deployment/k8s/network-policies/monitoring/apply.sh` | Neu | Sichere Apply-Reihenfolge |
| `deployment/k8s/network-policies/06-allow-monitoring-scrape.yaml` | Neu | App-NS: Ingress von monitoring:8080 |

### Commits

| SHA | Nachricht |
|-----|-----------|
| `4a0d262` | `feat(helm): Monitoring-Stack vorbereiten (Health Probes + kube-prometheus-stack)` |
| `91e6987` | `fix(helm): Prometheus scrape targets auf korrekte Service-Namen anpassen` |
| `7fe7e8e` | `fix(helm): Webserver Health Probes auf tcpSocket umstellen` |
