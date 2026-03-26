# Runbook: ext-analytics — Analytics Dashboard + API

## Grafana Dashboard aufrufen

```bash
# PROD
kubectl --context vob-prod port-forward -n monitoring svc/monitoring-grafana 3001:80
# Browser: http://localhost:3001
# Dashboard: VÖB Analytics Overview (Folder: VÖB Chatbot)

# DEV
kubectl --context vob-chatbot port-forward -n monitoring svc/monitoring-grafana 3001:80
```

## API-Endpoints

Alle Endpoints erfordern Admin-Auth (Entra ID Token).

```bash
# Summary: Alle KPIs
GET /api/ext/analytics/summary?from_date=2026-03-01&to_date=2026-03-31

# User-Tabelle
GET /api/ext/analytics/users?from_date=2026-03-01&to_date=2026-03-31

# Agent-Statistiken
GET /api/ext/analytics/agents?from_date=2026-03-01&to_date=2026-03-31

# CSV-Export (max 365 Tage)
GET /api/ext/analytics/export?from_date=2026-03-01&to_date=2026-03-31
```

Default-Zeitraum (ohne Parameter): Letzte 30 Tage.

## Monatlichen VÖB-Report erstellen

1. CSV exportieren: `/api/ext/analytics/export?from_date=YYYY-MM-01&to_date=YYYY-MM-DD`
2. Grafana Screenshots (Zeitbereich auf Monat setzen, "Share" > "Direct link rendered image")
3. Email an VÖB mit CSV + Screenshots

## Feature Flag

```bash
# Aktivieren
EXT_ANALYTICS_ENABLED=true  # in .env oder Helm values

# Deaktivieren (Router wird nicht registriert, kein Impact auf Onyx)
EXT_ANALYTICS_ENABLED=false
```

Das Grafana Dashboard funktioniert unabhaengig vom Feature Flag (direkte SQL-Queries auf PG).

## Troubleshooting

### Dashboard zeigt "No Data"
1. PG-Datasource pruefen: Grafana > Configuration > Data Sources > PostgreSQL > "Test"
2. Falls Timeout: NetworkPolicy pruefen (`kubectl get netpol -n monitoring`)
3. Falls "permission denied": SELECT-Grants pruefen (als `onyx_app` auf PG):
   ```sql
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO db_readonly_user;
   ```

### API 404 / Router nicht registriert
1. Feature Flag pruefen: `EXT_ENABLED=true` UND `EXT_ANALYTICS_ENABLED=true`
2. Pod-Logs pruefen: `kubectl logs deploy/onyx-*-api-server | grep "analytics"`
3. Erwarteter Log: `Extension analytics router registered`

### CSV Export leer
1. Zeitraum pruefen — eventuell keine Daten im angegebenen Zeitraum
2. Max 365 Tage erlaubt (sonst HTTP 400)

### Grafana Pod startet nicht nach Datasource-Aenderung
1. Provisioning-Fehler pruefen: `kubectl logs deploy/monitoring-grafana -c grafana | grep provisioning`
2. Haeufigste Ursache: Zwei Datasources mit `isDefault: true`
3. Fix: Alle Datasource-ConfigMaps pruefen, nur eine darf `isDefault: true` haben

## Infrastruktur-Dateien

| Datei | Zweck |
|-------|-------|
| `deployment/k8s/monitoring-exporters/grafana-datasource-postgresql.yaml` | PG-Datasource Template (Credentials via kubectl) |
| `deployment/k8s/monitoring-exporters/grafana-dashboards/analytics-overview.json` | Dashboard JSON (19 Panels) |
| `deployment/k8s/network-policies/monitoring/14-allow-grafana-pg-egress.yaml` | NetworkPolicy Grafana → PG |

## db_readonly_user Grants erneuern (nach Upstream-Sync)

Falls neue Tabellen hinzukommen (Upstream-Merge), muessen Grants erneuert werden:

```bash
kubectl exec -n onyx-<env> deploy/onyx-<env>-api-server -- python3 -c "
import psycopg2, os
conn = psycopg2.connect(
    host=os.environ['POSTGRES_HOST'], port=os.environ.get('POSTGRES_PORT','5432'),
    dbname=os.environ.get('POSTGRES_DB','onyx'),
    user=os.environ['POSTGRES_USER'], password=os.environ['POSTGRES_PASSWORD'],
    sslmode='require')
conn.autocommit = True
cur = conn.cursor()
cur.execute('GRANT SELECT ON ALL TABLES IN SCHEMA public TO db_readonly_user')
print('Grants erneuert')
conn.close()
"
```

`ALTER DEFAULT PRIVILEGES` wurde gesetzt — neue Tabellen die von `onyx_app` erstellt werden, erhalten automatisch SELECT-Grants.
