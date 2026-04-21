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
  --from-literal=password='<PG_READONLY_PASSWORD>'

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

## 13. Checkliste

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

## 14. Nächster Schritt

→ [llm-konfiguration.md](./llm-konfiguration.md) — LLM + Embedding-Modelle konfigurieren
