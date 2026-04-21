# Monitoring-Stack Initial-Setup

**Zielgruppe:** Tech Lead / DevOps beim Aufsetzen eines neuen Kunden-Projekts
**Dauer:** 2 h
**Phase:** 7 im [Master-Playbook](./kunden-klon-onboarding.md)

Dieses Runbook installiert den kompletten Monitoring-Stack (Prometheus + Grafana + AlertManager + Loki + Exporter + NetworkPolicies) erstmalig auf DEV und PROD. Für laufende Probleme siehe `alert-antwort.md`, `loki-troubleshooting.md`, `opensearch-troubleshooting.md`.

---

## Voraussetzungen

- Phase 5 abgeschlossen: Helm-Release `<HELM_RELEASE_DEV>` deployed, Namespace `<NAMESPACE_DEV>` existiert
- `kubectl`, `helm` installiert, Kubeconfigs für DEV und PROD gesetzt
- Microsoft Teams Incoming Webhook URL (für Alerts) vorhanden — siehe [Teams Webhook erstellen](#teams-webhook-erstellen)

---

## Architektur-Überblick

Pro Cluster **eigener** `monitoring`-Namespace mit:
- Prometheus (Scrape, Alert-Engine)
- Grafana (Dashboards)
- AlertManager (Alert-Routing zu Teams)
- kube-state-metrics, node-exporter (K8s-Metriken)
- Postgres Exporter (PG-Metriken)
- Redis Exporter (Redis-Metriken)
- OpenSearch Exporter (nur PROD)
- Blackbox Exporter (externe HTTP-Probes, nur PROD)
- Loki + Promtail (Log-Aggregation, nur PROD per default; DEV optional)

NetworkPolicies nach Zero-Trust-Prinzip: default-deny plus explizite Whitelist.

---

## 1. Teams Webhook erstellen

1. Microsoft Teams → Kanal → **Konnektoren** → Incoming Webhook hinzufügen
2. Name: `<CUSTOMER_SHORT>-chatbot-alerts` (oder `…-prod-alerts` / `…-dev-alerts` je nach Kanal)
3. URL kopieren und sicher speichern (wird nur einmal angezeigt)
4. Empfehlung für PROD: **separater Teams-Kanal**, damit PROD-Alerts nicht im DEV-Rauschen untergehen

---

## 2. Helm-Repos hinzufügen

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
```

---

## 3. Namespace + Teams-Secret anlegen

**Pro Cluster einmal:**

```bash
# Namespace
kubectl --context <CLUSTER_DEV> create namespace monitoring

# Teams Webhook Secret (fuer AlertManager)
kubectl --context <CLUSTER_DEV> -n monitoring create secret generic alertmanager-teams-webhook \
  --from-literal=url='<TEAMS_WEBHOOK_URL>'
```

Analog für `<CLUSTER_PROD>` mit eigenem Teams-Webhook.

---

## 4. kube-prometheus-stack installieren (DEV)

```bash
cd deployment/helm/values

helm --kube-context=<CLUSTER_DEV> upgrade --install monitoring \
  prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 82.10.3 \
  -f values-monitoring.yaml \
  --wait --timeout 10m
```

### Erwartetes Ergebnis

```bash
kubectl --context <CLUSTER_DEV> -n monitoring get pods
# NAME                                                    READY   STATUS
# monitoring-grafana-xxx                                  3/3     Running
# monitoring-kube-prometheus-operator-xxx                 1/1     Running
# monitoring-kube-state-metrics-xxx                       1/1     Running
# monitoring-prometheus-node-exporter-xxx                 1/1     Running (pro Node)
# alertmanager-monitoring-kube-prometheus-alertmanager-0  2/2     Running
# prometheus-monitoring-kube-prometheus-prometheus-0      2/2     Running
```

---

## 5. Exporter deployen (PG, Redis)

Die dedizierten Exporter stehen in `deployment/k8s/monitoring-exporters/`:

```bash
cd deployment/k8s/monitoring-exporters/

# PG-Credentials aus Terraform Output holen und als Secret ablegen
# (pro Environment einmal)
kubectl --context <CLUSTER_DEV> -n monitoring create secret generic pg-exporter-dev-credentials \
  --from-literal=DATA_SOURCE_NAME='postgresql://onyx_app:<PG_PASSWORD>@<PG_HOST>:5432/onyx?sslmode=require'

# Exporter applyen
kubectl --context <CLUSTER_DEV> apply -f pg-exporter-dev.yaml
kubectl --context <CLUSTER_DEV> apply -f redis-exporter-dev.yaml
```

Analog für PROD mit `pg-exporter-prod.yaml`, `redis-exporter-prod.yaml`, `opensearch-exporter-prod.yaml`, `blackbox-exporter-prod.yaml`.

---

## 6. NetworkPolicies anwenden (Zero-Trust)

### 6.1 Applikations-Namespace (`<NAMESPACE_DEV>`, `<NAMESPACE_PROD>`)

Ingress von `monitoring`-Namespace auf Port 8080 erlauben:

```bash
kubectl --context <CLUSTER_DEV> apply -f deployment/k8s/network-policies/06-allow-monitoring-scrape.yaml
kubectl --context <CLUSTER_DEV> apply -f deployment/k8s/network-policies/07-allow-redis-exporter-ingress.yaml
# PROD zusätzlich:
kubectl --context <CLUSTER_PROD> apply -f deployment/k8s/network-policies/08-allow-opensearch-exporter-ingress.yaml
```

### 6.2 `monitoring`-Namespace (14 Policies)

```bash
cd deployment/k8s/network-policies/monitoring/
./apply.sh
```

Das Script führt in sicherer Reihenfolge aus:
1. `01-default-deny-all.yaml` (Start mit Deny-All)
2. `02-allow-dns-egress.yaml`
3. `03-allow-scrape-egress.yaml` (Prometheus → API-Pods)
4. `04-allow-intra-namespace.yaml`
5. `05-allow-k8s-api-egress.yaml`
6. `06-allow-pg-exporter-egress.yaml` (→ StackIT PG:5432)
7. `07-allow-redis-exporter-egress.yaml` (→ Redis:6379)
8. `08-allow-alertmanager-webhook-egress.yaml` (→ Teams-Webhook)
9. `09-allow-backup-check-egress.yaml` (→ StackIT API, nur PROD)
10. `10-allow-blackbox-egress.yaml` (→ externe HTTPS, nur PROD)
11. `11-allow-opensearch-exporter-egress.yaml` (→ OpenSearch:9200, nur PROD)
12. `12-allow-loki-ingress.yaml` (nur PROD, falls Loki aktiv)
13. `13-allow-promtail-egress.yaml` (nur PROD)
14. `14-allow-grafana-pg-egress.yaml` (nur PROD, ext-analytics)

### 6.3 cert-manager-Namespace (6 Policies)

```bash
cd deployment/k8s/network-policies/cert-manager/
./apply.sh
```

---

## 7. PROD-spezifische Zusätze

### 7.1 Eigene Monitoring-Values für PROD

PROD nutzt eine separate Values-Datei mit:
- Höherer Retention (90 Tage statt 30)
- Größerem PVC (50 Gi statt 20)
- Separatem Teams-Kanal-Webhook
- PostgresDown-Alert (seit 2026-04-16)

```bash
helm --kube-context=<CLUSTER_PROD> upgrade --install monitoring \
  prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --version 82.10.3 \
  -f values-monitoring-prod.yaml \
  --wait --timeout 10m
```

### 7.2 Loki (PROD)

```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm --kube-context=<CLUSTER_PROD> upgrade --install loki \
  grafana/loki-stack \
  --namespace monitoring \
  --version 2.10.3 \
  -f values-loki-prod.yaml
```

Promtail als DaemonSet shipping zu Loki auf Port 3100.

### 7.3 Grafana PG-Datasource (optional, für ext-analytics)

```bash
kubectl --context <CLUSTER_PROD> -n monitoring create secret generic grafana-pg-datasource \
  --from-literal=user=db_readonly_user \
  --from-literal=password='<DB_READONLY_PASSWORD>'

kubectl --context <CLUSTER_PROD> apply -f deployment/k8s/monitoring-exporters/grafana-datasource-postgresql.yaml
```

---

## 8. Grafana-Dashboards importieren

### 8.1 Standard-Dashboards per gnetId

Grafana → Dashboards → Import:

| Dashboard | gnetId | Zweck |
|---|---|---|
| PostgreSQL | 14114 | PG-Connections, Query-Performance, Locks |
| Redis | 763 | Redis-Memory, Latenz, Hit-Rate |
| Kubernetes Cluster | 6417 | K8s-Übersicht |
| Kubernetes Pods | 15760 | Pod-Status |
| NGINX Ingress | 9614 | Ingress-Metriken |

### 8.2 Custom-Dashboards (als ConfigMap, PROD)

```bash
kubectl --context <CLUSTER_PROD> apply -f deployment/k8s/monitoring-exporters/grafana-dashboards/
```

Enthält: SLO-Overview, Audit-Log (Loki), Token-Usage, Analytics-Overview (ext-analytics).

---

## 9. Alert-Rules + ServiceMonitors

Das sollte automatisch über die Helm-Values passieren. Prüfen:

```bash
kubectl --context <CLUSTER_DEV> -n monitoring get prometheusrules
kubectl --context <CLUSTER_DEV> -n monitoring get servicemonitors
```

Bei PROD sollten ~46 Custom-Alert-Rules (via `values-monitoring-prod.yaml`) + ~131 kube-prometheus-stack-Default-Regeln aktiv sein.

---

## 10. Validierung

### 10.1 Targets UP

```bash
kubectl --context <CLUSTER_DEV> -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 9090:9090
```

Browser: `http://localhost:9090/targets` — alle Targets sollten „UP" zeigen.

### 10.2 Grafana erreichbar

```bash
kubectl --context <CLUSTER_DEV> -n monitoring port-forward svc/monitoring-grafana 3001:80
```

Browser: `http://localhost:3001`, Login via Default-Admin (Password aus Secret `monitoring-grafana`).

### 10.3 Test-Alert auslösen

```bash
# Einen fake Pod deployen, der 429-Code liefert → triggert HighAuthFailureRate Alert nach ~5 Min
# (Alternativ: AlertManager Silence + Test manuell)

kubectl --context <CLUSTER_PROD> -n monitoring port-forward svc/monitoring-kube-prometheus-alertmanager 9093:9093
# Browser http://localhost:9093 → Alert-Status prüfen
```

Nach ca. 5 Minuten sollte ein Test-Alert im Teams-Kanal eintreffen. Falls nicht: Webhook-URL prüfen, AlertManager-Pod-Logs ansehen.

### 10.4 Loki funktionsfähig (PROD)

```bash
# In Grafana: Explore → Datasource „Loki" → Query `{namespace="<NAMESPACE_PROD>"}`
# Erwartet: Log-Stream der Applikations-Pods
```

---

## 11. Externe Health-Monitor (GitHub Actions)

Zusätzlich zum Cluster-internen Monitoring läuft ein externer Health-Monitor:

```yaml
# .github/workflows/health-monitor.yml (existiert bereits)
# Cron: */5 * * * *
# Pingt: https://<PRIMARY_DOMAIN>/api/ext/health/deep
# Bei Fehler: Teams-Webhook
```

GitHub Secret `TEAMS_WEBHOOK_URL` muss gesetzt sein (gleicher Webhook wie PROD-Cluster oder eigener).

---

## 12. Alert-Fatigue-Mitigation

Nach dem ersten Deploy sind meist zu viele Alerts aktiv (KubeCPUOvercommit, SLO-Breaches etc.). Empfohlene Konfiguration in `values-monitoring-prod.yaml`:

```yaml
alertmanager:
  config:
    route:
      repeat_interval: 24h    # Default 4h, für non-critical 24h
      routes:
        - matchers: [severity = "info"]
          receiver: 'null'
        - matchers: [alertname = "Watchdog"]
          receiver: 'null'
        - matchers: [alertname = "InfoInhibitor"]
          receiver: 'null'
```

**Prinzip:** Stiller Teams-Kanal = alles OK. Jede Nachricht = sofort handeln.

---

## 13. Typische Fallstricke / Lessons Learned

Diese Punkte haben wir beim initialen Monitoring-Rollout hart gelernt. Beim Kunden-Klon-Setup zuerst durchlesen.

### 13.1 Grafana-Dashboards als ConfigMap statt gnetId-Provisioning

**Problem:** `grafana.dashboardProviders` mit `gnetId` (grafana.com IDs) ist unzuverlaessig — Provisioning-Sidecar schlaegt gelegentlich fehl, Dashboard taucht nicht auf.

**Loesung:** Dashboards als ConfigMap mit Label `grafana_dashboard=1` deployen. Der Sidecar liest ConfigMaps zuverlaessig.

**Pattern:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboard-postgresql
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  postgresql.json: |
    { "...": "..." }
```

Unsere 6 Custom-Dashboards (PG, Redis, SLO, Audit-Log, Token-Usage, Analytics) sind alle so deployed — siehe `deployment/k8s/monitoring-exporters/grafana-dashboards/`.

### 13.2 `kubectl replace` bei PrometheusRule erzeugt Ownership-Konflikte

**Symptom:** PrometheusRule YAML aktualisiert, Prometheus laedt Regeln aber nicht.

**Ursache:** `kubectl replace` schreibt `managedFields` neu, Operator verliert die Ownership.

**Loesung:** **IMMER `kubectl apply`**, nie `replace`. Bei Operator-CRDs (PrometheusRule, ServiceMonitor, PodMonitor) ist das besonders kritisch.

Bei bereits korrupten Helm-Releases (Ownership-Konflikt zwischen Helm und kubectl): `helm upgrade --force-replace --server-side=false` einmalig anwenden.

### 13.3 Blackbox `valid_status_codes: []` = nur 2xx, NICHT "alle"

**Symptom:** Blackbox-Probe schlaegt fehl, obwohl Target 401/403 zurueckgibt (erwartet bei Auth-geschuetzten Endpoints).

**Ursache:** Leere Liste = Prometheus-Default 2xx. Zum Akzeptieren von 401/403 muessen diese explizit gelistet werden.

**Loesung:**
```yaml
modules:
  http_2xx_or_401:
    prober: http
    http:
      valid_status_codes: [200, 401, 403]
```

Unsere Blackbox-Probe fuer `/api/ext/health/deep` nutzt `[200]` (Deep-Health ist public), die fuer Entra-geschuetzte Endpoints `[200, 401]`.

### 13.4 `kube_job_status_failed` zaehlt pro Pod-Retry, nicht pro Job

**Symptom:** `PGBackupCheckFailed` feuert, obwohl der letzte Run erfolgreich war.

**Ursache:** CronJob mit `restartPolicy: OnFailure` zaehlt jeden Pod-Retry als "failed" bis der erfolgreiche Pod durch ist. Metrik kumuliert ueber die Zeit.

**Loesung:** Alert-Rule mit Zeitfenster + Vergleich gegen `lastSuccessfulTime`:
```yaml
expr: time() - kube_cronjob_status_last_successful_time{cronjob="pg-backup-check"} > 86400
```

### 13.5 elasticsearch-exporter CLI-Flags aendern sich zwischen Versionen

**Symptom:** OpenSearch-Exporter Pod startet nicht mit `unknown flag: --es.uri`.

**Ursache:** v1.5.x nutzt `--es.uri`, v1.6.x+ nutzt `--address`, v1.8.x+ nutzt wieder andere Flags.

**Loesung:** Immer `--help` im Container-Image pruefen bevor Deployment:
```bash
docker run --rm quay.io/prometheuscommunity/elasticsearch-exporter:v1.9.0 --help
```

Aktuell in Betrieb: v1.9.0 mit `--es.uri=https://...` (wieder zurueck auf alten Flag-Namen).

### 13.6 Passwoerter in Connection-URIs URL-encoden

**Symptom:** PG-Exporter crasht mit `Invalid URL: Cannot parse...`. Log zeigt bei `/` im Passwort einen URI-Parse-Error.

**Ursache:** PostgreSQL-URIs haben Format `postgresql://user:password@host:port/db`. Passwoerter mit `/`, `@`, `:`, `#` brechen den Parser.

**Loesung:** In Secrets URL-encoden (`%2F` fuer `/`, `%40` fuer `@`, `%3A` fuer `:`). Oder Passwoerter so generieren, dass sie keine URI-Delimiter enthalten:
```bash
openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32
```

### 13.7 NetworkPolicy `namespaceSelector` matcht NICHT externe K8s-API

**Symptom:** `cert-manager-cainjector` in CrashLoopBackoff. Logs zeigen TLS-Timeout zur K8s-API.

**Ursache:** Bei StackIT SKE (Managed K8s) lebt der Control-Plane AUSSERHALB des Clusters (dedizierte IP `192.214.168.128` o.ae.). NetworkPolicy-Egress via `namespaceSelector` matcht nur In-Cluster-Pods.

**Loesung:** Fuer K8s-API-Egress `ipBlock` verwenden:
```yaml
- to:
    - ipBlock:
        cidr: 192.214.168.128/32  # StackIT SKE Control-Plane
  ports:
    - port: 443
```

IP ermitteln mit `kubectl get endpoints kubernetes -n default`.

### 13.8 PROD: Separater Teams-Kanal ist Pflicht, nicht Option

**Problem:** Gemeinsamer DEV+PROD-Kanal → DEV-Rauschen ueberdeckt echte PROD-Incidents → Alert Fatigue.

**Loesung:** PROD hat eigenen, stillen Teams-Kanal `<CUSTOMER_SHORT>-chatbot-prod-alerts`. Keine DEV-Routing-Regeln. Channel ist still → jede Nachricht = echt.

### 13.9 Alert `OpenSearchUnassignedShards` Threshold auf >20 (nicht >0)

**Problem:** Single-Node OpenSearch hat strukturell immer `unassigned_shards > 0` (Replicas koennen nicht auf selben Node assigniert werden).

**Loesung:** Alert-Expr mit Threshold `> 20` (bei ~10 Indices mit je 2 Replicas). Bei Scale-Out auf 3+ Nodes: Threshold auf `> 0` runter.

### 13.10 Next.js hat KEINEN `/api/health` — Blackbox-Probe muss NGINX-Route nutzen

**Problem:** Initial war Blackbox-Probe auf `http://<web-server>:3000/api/health` konfiguriert — dauerhaft 404, weil Next.js kein Health-Endpoint mountet. Onyx-Health lebt nur auf dem API-Server (Python FastAPI), nicht auf dem Next.js-Frontend.

**Loesung:**
- Blackbox probed IMMER die **externe Domain** (`https://<PRIMARY_DOMAIN>/api/ext/health/deep`) oder den API-Server-Service direkt, nie den Web-Server.
- NGINX-Ingress proxyed `/api/*` auf den API-Server. Next.js bekommt nur `/_next/*`, `/chat/*`, `/admin/*` etc.

**Pattern fuer Blackbox-Probes:**
```yaml
modules:
  http_2xx:
    prober: http
    http:
      valid_status_codes: [200]
static_configs:
  - targets:
      - https://<PRIMARY_DOMAIN>/api/ext/health/deep    # external
      - http://onyx-prod-api-service:8080/api/health    # internal (API-Server, nicht web-server)
```

### 13.11 Onyx Service-Name-Suffix `-service` (nicht `-api`, nicht `-web`)

**Problem:** Initial wurde ServiceMonitor auf `port: http` am Service `onyx-dev-api` konfiguriert — Port wurde gefunden, aber Service `onyx-dev-api` existiert nicht (heisst wirklich `onyx-dev-api-service`).

**Loesung:** Service-Namen aus Chart sind:
- `<HELM_RELEASE>-api-service` (API-Server, Port 8080)
- `<HELM_RELEASE>-web-service` (Web-Server, Port 3000)
- `<HELM_RELEASE>-nginx-controller` (NGINX, Port 80/443)
- `onyx-<env>.<env>.svc.cluster.local` (Redis, Port 6379)

Pruefen vor ServiceMonitor-Deployment:
```bash
kubectl --context <CLUSTER_PROD> get svc -n <NAMESPACE_PROD>
```

### 13.12 NetworkPolicy-Reihenfolge: Basis VOR App-Policies

**Problem:** App-NS-Policies (Ingress von monitoring) wurden VOR Basis-Policies angewendet — default-deny war noch nicht aktiv → NetworkPolicy hat Traffic "erlaubt", der dann aber nirgendwo routbar war, weil DNS/K8s-API-Policies fehlten. Pods crashten mit `connection refused` auf DNS.

**Loesung:** Feste Reihenfolge beim Apply:
1. `01-default-deny-all.yaml` (beide NS: monitoring + App-NS)
2. `02-allow-dns-egress.yaml` (beide NS)
3. `03-allow-k8s-api-egress.yaml` (monitoring + cert-manager NS — mit `ipBlock`, nicht `namespaceSelector`! Siehe 13.7)
4. `04-...` — App-spezifische Egress (Scrape, Exporter, Monitoring)
5. `05-...` — App-NS Ingress (Prometheus, Redis-Exporter, OpenSearch-Exporter)

Das `apply.sh`-Script in `deployment/k8s/network-policies/monitoring/` und `cert-manager/` enforced diese Reihenfolge. NIE manuell ein einzelnes Policy-File applyen — immer via Script.

### 13.13 Monitoring-Egress-Policies muessen Ziel-Namespaces explizit enthalten

**Problem:** Beim PROD-Rollout fehlte `onyx-prod` als namespaceSelector in `03-allow-scrape-egress.yaml` (nur `onyx-dev` eingetragen). Prometheus scrapete → NetworkPolicy blockte → alle App-Metriken `up=0` → PROD-Alerts gingen an Teams, obwohl App lief.

**Loesung:** Beim Klon-Projekt VOR Apply die Policy-Files durchsuchen:
```bash
grep -rn "namespaceSelector" deployment/k8s/network-policies/monitoring/
# Erwartet: onyx-<env> in 03-allow-scrape-egress, 06-allow-pg-exporter-egress,
#          07-allow-redis-exporter-egress, 11-allow-opensearch-exporter-egress, 14-allow-grafana-pg-egress
```

Wenn der Ziel-NS nicht passt: Policy anpassen, dann `apply.sh` erneut laufen lassen.

### 13.14 CronJob mit `apk add` / `curl`-Install braucht `runAsUser: 0`

**Problem:** `pg-backup-check` CronJob nutzte `alpine:3.19` + `apk add curl` im Init — schlaegt fehl mit `permission denied` wenn `runAsUser != 0` (SEC-06 PodSecurity-Policy).

**Loesung:**
- CronJob explizit mit `runAsUser: 0` markieren und in `docs/sicherheitskonzept.md` als dokumentierte SEC-06-Ausnahme listen (neben Vespa).
- Alternativ: Base-Image mit vorinstalliertem `curl`/`jq` verwenden (`curlimages/curl` statt `alpine`).

Template:
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: pg-backup-check
spec:
  jobTemplate:
    spec:
      template:
        spec:
          securityContext:
            runAsUser: 0           # Ausnahme fuer apk-Installs
            runAsNonRoot: false
```

**Dokumentierte SEC-06-Ausnahmen im VÖB-Setup:** Vespa (Upstream-Container), pg-backup-check CronJob. Weitere Ausnahmen MUESSEN in `docs/sicherheitskonzept.md` gelistet sein.

### 13.15 Alerts mit Mindest-Traffic-Guard gegen Idle-False-Positives

**Problem:** Alerts wie `HighErrorRate` (>5% 5xx) und `PGHighRollbackRate` feuern bei Idle-Systemen (DEV nach 22 Uhr) weil 1 Request × 1 Error = 100% error rate.

**Loesung:** Alle Rate-basierten Alerts bekommen einen Traffic-Guard:
```yaml
- alert: HighErrorRate
  expr: |
    (
      rate(http_requests_total{status=~"5.."}[5m])
      /
      rate(http_requests_total[5m])
    ) > 0.05
    AND
    rate(http_requests_total[5m]) > 0.5    # mindestens 30 Req/Min
  for: 5m
```

Gilt fuer: `HighErrorRate`, `HighSlowRequests`, `PGHighRollbackRate`, `RedisCacheHitRateLow`, `PGCacheHitRateLow`. Pattern dokumentiert in `alert-antwort.md`.

### 13.16 SEC-09 Rate-Limit nur auf `/api/*` scopen (nicht global)

**Problem:** Rate-Limit 10r/s global auf NGINX → Next.js RSC-Prefetch beim Laden der Chat-Sidebar (20+ Chats parallel prefetched) schlaegt die Limit-Grenze → 429-Salven in Browser-Konsole fuer harmlose Navigationen.

**Loesung:** Rate-Limit-Key nur fuer `/api/*`-Pfade aktivieren:
```nginx
# nginx.controller.config
http-snippet: |
  map $uri $ratelimit_key {
    ~^/api/  $binary_remote_addr;
    default  "";
  }
  limit_req_zone $ratelimit_key zone=api:10m rate=10r/s;
```

Upload-Limits (`MAX_FILE_SIZE_BYTES` + `proxy-body-size: 20m`) bleiben global. Pattern dokumentiert in `docs/sicherheitskonzept.md` SEC-09.

---

## 14. Checkliste

- [ ] Teams-Webhook für DEV + PROD erstellt und als K8s-Secret abgelegt
- [ ] kube-prometheus-stack deployed auf DEV
- [ ] kube-prometheus-stack deployed auf PROD (mit PROD-Values)
- [ ] PG + Redis Exporter deployed
- [ ] OpenSearch + Blackbox Exporter deployed (PROD)
- [ ] Loki deployed (PROD)
- [ ] NetworkPolicies monitoring-NS (14) applied
- [ ] NetworkPolicies cert-manager-NS (6) applied
- [ ] NetworkPolicies App-NS (Ingress von monitoring) applied
- [ ] Prometheus Targets alle UP
- [ ] Grafana erreichbar, Dashboards importiert
- [ ] Test-Alert in Teams angekommen
- [ ] Loki liefert Logs (PROD)
- [ ] Externer Health-Monitor konfiguriert (GitHub Actions)
- [ ] Alert-Fatigue-Config gesetzt (repeat_interval, info-Routes)

---

## 15. Nächster Schritt

→ [llm-konfiguration.md](./llm-konfiguration.md) — LLM + Embedding-Modelle konfigurieren
