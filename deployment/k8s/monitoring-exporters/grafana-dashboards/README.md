# Grafana Dashboards — Manuelle ConfigMaps

Die gnetId-basierte Dashboard-Provisioning via Helm (`dashboards.default` in values-monitoring-prod.yaml)
funktioniert nicht, weil der Grafana Sidecar die JSONs nicht von grafana.com herunterladen kann
(Egress-Restriktion durch NetworkPolicies im monitoring NS).

## Fix (2026-03-25)

Dashboards werden als ConfigMaps mit Label `grafana_dashboard=1` deployed.
Der Grafana Sidecar erkennt sie automatisch und schreibt sie nach `/var/lib/grafana/dashboards/`.

### Anwendung

```bash
# PostgreSQL Dashboard (gnetId 14114)
kubectl create configmap grafana-dashboard-postgresql \
  --namespace monitoring \
  --from-file=postgresql.json=postgresql-14114.json \
  --dry-run=client -o yaml | \
  kubectl label --local -f - grafana_dashboard=1 -o yaml --dry-run=client | \
  kubectl apply -f -

# Redis Dashboard (gnetId 763)
kubectl create configmap grafana-dashboard-redis \
  --namespace monitoring \
  --from-file=redis.json=redis-763.json \
  --dry-run=client -o yaml | \
  kubectl label --local -f - grafana_dashboard=1 -o yaml --dry-run=client | \
  kubectl apply -f -
```

### Verifikation

```bash
kubectl get configmap -n monitoring -l grafana_dashboard | grep dashboard
kubectl logs -n monitoring deploy/monitoring-grafana -c grafana-sc-dashboard --tail=5
```

### Quellen

- PostgreSQL: https://grafana.com/grafana/dashboards/14114 (rev 1)
- Redis: https://grafana.com/grafana/dashboards/763 (rev 5)
- Datasource-Platzhalter (`${DS_PROMETHEUS}`) durch `Prometheus` ersetzt.
