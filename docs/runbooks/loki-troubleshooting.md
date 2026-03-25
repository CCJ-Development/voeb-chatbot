# Runbook: Loki Log-Aggregation

> **Stack:** Grafana Loki (loki-stack 2.10.3) + Promtail (DaemonSet)
> **Namespace:** monitoring (PROD Cluster vob-prod)
> **Retention:** 30 Tage, 20Gi PVC
> **Zugang:** Grafana → Explore → Datasource: Loki

---

## Log-Suche in Grafana

### Zugang

```bash
kubectl port-forward -n monitoring svc/monitoring-grafana 3001:80
# Browser: http://localhost:3001
# Navigiere zu: Explore → Datasource: Loki
```

### Haeufige Queries

```logql
# Alle API-Server Logs (onyx-prod)
{namespace="onyx-prod", pod=~"onyx-prod-api-server.*"}

# Nur Fehler
{namespace="onyx-prod"} |= "ERROR"

# Auth/OIDC Probleme
{namespace="onyx-prod"} |~ "auth|oidc|login|401|403"

# Audit-Events
{namespace="onyx-prod"} |= "EXT-AUDIT"

# Bestimmter Zeitraum + Pod
{namespace="onyx-prod", pod="onyx-prod-api-server-78848c7cbd-59glc"} |= "ERROR"

# Celery-Worker Fehler
{namespace="onyx-prod", pod=~"onyx-prod-celery.*"} |= "ERROR"

# OpenSearch Probleme
{namespace="onyx-prod", pod=~"onyx-opensearch.*"} |~ "error|exception|warn"

# Monitoring-Stack eigene Logs
{namespace="monitoring"} |= "ERROR"
```

### Tipps

- **Zeitraum einschraenken** — Loki ist schneller mit kleinen Zeitfenstern (1h statt 7d)
- **Labels nutzen** — `namespace`, `pod`, `container` sind automatisch verfuegbar
- **Pipeline Stages** — `|=` (contains), `|~` (regex), `!=` (not contains)
- **Aggregation** — `count_over_time({...}[5m])` fuer Trends

---

## Komponenten

| Komponente | Typ | Pods | Zweck |
|-----------|-----|------|-------|
| Loki | StatefulSet | 1 (`loki-0`) | Log-Storage + Query Engine |
| Promtail | DaemonSet | 2 (je Node) | Log-Shipper (liest kubelet Logs) |

### Status pruefen

```bash
# Loki Pod
kubectl get pod -n monitoring loki-0

# Loki Ready?
kubectl exec -n monitoring deploy/monitoring-grafana -c grafana -- wget -qO- http://loki:3100/ready

# Promtail DaemonSet
kubectl get ds -n monitoring loki-promtail

# Promtail Errors (letzte 10 Min)
kubectl logs -n monitoring -l app.kubernetes.io/name=promtail --since=600s | grep -c "error"
```

---

## Troubleshooting

### Loki antwortet nicht

```bash
# Pod Status
kubectl describe pod -n monitoring loki-0

# Logs
kubectl logs -n monitoring loki-0 --tail=20

# PVC voll?
kubectl exec -n monitoring loki-0 -- df -h /data
```

**PVC voll:** Retention funktioniert nicht oder zu viele Logs.
Fix: `kubectl exec -n monitoring loki-0 -- ls -lhS /data/loki/chunks/ | head -20`
Ggf. PVC vergroessern oder Retention kuerzen.

### Promtail kann nicht zu Loki pushen

```bash
# Promtail Logs
kubectl logs -n monitoring -l app.kubernetes.io/name=promtail --tail=10

# Typische Fehler:
# "context deadline exceeded" → Loki nicht erreichbar (NetworkPolicy? Pod down?)
# "429 Too Many Requests" → Loki Rate-Limit (zu viele Logs pro Sekunde)
# "400 Bad Request" → Label-Problem (zu viele Labels)
```

**NetworkPolicy pruefen:**
```bash
kubectl get networkpolicy -n monitoring | grep -i "loki\|promtail"
# Erwartet: allow-loki-ingress + allow-promtail-egress
```

### Keine Logs fuer bestimmten Namespace

```bash
# Promtail Config pruefen — wird der Namespace gefiltert?
kubectl get configmap -n monitoring loki-promtail -o yaml | grep -A 5 "pipeline\|drop\|namespace"
```

Unsere Config filtert `kube-system` raus. Alle anderen Namespaces werden gesammelt.

### Grafana zeigt "No data"

1. Datasource pruefen: Grafana → Settings → Data Sources → Loki → Test
2. Zeitraum pruefen: Logs existieren erst seit Loki-Deployment (2026-03-25)
3. Query pruefen: Labels muessen exakt matchen (`namespace="onyx-prod"`, nicht `namespace="prod"`)

---

## Wartung

### Helm Upgrade

```bash
helm upgrade loki grafana/loki-stack --version 2.10.3 \
  -n monitoring -f deployment/helm/values/values-loki-prod.yaml
```

### Retention aendern

In `values-loki-prod.yaml`:
```yaml
loki:
  config:
    table_manager:
      retention_period: 720h  # 30 Tage (aendern nach Bedarf)
    limits_config:
      retention_period: 720h
```

### PVC vergroessern

```bash
# PVC Groesse pruefen
kubectl get pvc -n monitoring storage-loki-0

# Vergroessern (StackIT StorageClass unterstuetzt Expansion)
kubectl patch pvc storage-loki-0 -n monitoring -p '{"spec":{"resources":{"requests":{"storage":"40Gi"}}}}'
```

### Loki Neustart

```bash
kubectl rollout restart statefulset/loki -n monitoring
kubectl rollout status statefulset/loki -n monitoring
```

**Kein Datenverlust** bei Restart (PVC bleibt erhalten). Promtail puffert waehrend Loki down ist.

---

## NetworkPolicies

| Policy | Richtung | Zweck |
|--------|----------|-------|
| `allow-loki-ingress` | Ingress | Promtail + Grafana → Loki:3100 |
| `allow-promtail-egress` | Egress | Promtail → Loki:3100 + K8s API:443 |
