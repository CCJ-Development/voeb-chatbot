# Runbook: OpenSearch Troubleshooting

**Erstellt**: 2026-03-22
**Status**: Aktiv
**Verantwortlich**: Nikolaj Ivanov (CCJ)

---

## Zweck

Dieses Runbook beschreibt die haeufigsten OpenSearch-Probleme und deren Behebung im VÖB-Chatbot-Betrieb. OpenSearch ersetzt Vespa als Primary-Search-Store seit Upstream-Sync #4 (2026-03-22).

**Wann dieses Runbook verwenden:**
- OpenSearch Pod nicht bereit oder crasht
- Suche liefert keine oder falsche Ergebnisse
- Cluster Health "red" (Notfall)
- Migration-Status pruefen oder umschalten

---

## Grundinfos

### Verbindungsdaten

| Umgebung | Pod | Namespace | Passwort |
|----------|-----|-----------|---------|
| DEV | `onyx-opensearch-master-0` | `onyx-dev` | `OnyxDev1!` (hardcoded im Helm Chart) |
| PROD | `onyx-opensearch-master-0` | `onyx-prod` | GitHub Secret `OPENSEARCH_PASSWORD` |

### Kubeconfig

```bash
# DEV (Standard-Kubeconfig):
kubectl exec -n onyx-dev onyx-opensearch-master-0 -c opensearch -- \
  curl -sk -u "admin:OnyxDev1!" "https://localhost:9200/_cluster/health?pretty"

# PROD (explizite Kubeconfig noetig):
KUBECONFIG=~/.kube/config-prod kubectl exec -n onyx-prod onyx-opensearch-master-0 -c opensearch -- \
  curl -sk -u "admin:$PW" "https://localhost:9200/_cluster/health?pretty"
# $PW = Wert des GitHub Secrets OPENSEARCH_PASSWORD
```

---

## 1. Cluster Health pruefen

### Schritt 1: Health-Status abfragen

```bash
# DEV
kubectl exec -n onyx-dev onyx-opensearch-master-0 -c opensearch -- \
  curl -sk -u "admin:OnyxDev1!" "https://localhost:9200/_cluster/health?pretty"

# PROD
KUBECONFIG=~/.kube/config-prod \
kubectl exec -n onyx-prod onyx-opensearch-master-0 -c opensearch -- \
  curl -sk -u "admin:$PW" "https://localhost:9200/_cluster/health?pretty"
```

### Status-Interpretation

| Status | Bedeutung | Aktion |
|--------|-----------|--------|
| `green` | Alle Shards assigned und repliziert | Kein Handlungsbedarf |
| `yellow` | **Normal bei Single-Node.** 1 unassigned Replica (kann auf sich selbst nicht replizieren) | Kein Handlungsbedarf |
| `red` | Mind. 1 Primary-Shard nicht erreichbar | **Sofort handeln** — Abschnitt 3 |

**Erwarteter Normalzustand (Single-Node):**

```json
{
  "status" : "yellow",
  "number_of_nodes" : 1,
  "active_primary_shards" : X,
  "unassigned_shards" : X
}
```

Der `yellow`-Status ist bei Single-Node-Deployment strukturell unvermeidbar. OpenSearch kann Replicas nicht sich selbst zuweisen. Das ist kein Fehler.

### Schritt 2: Index-Status pruefen

```bash
# DEV
kubectl exec -n onyx-dev onyx-opensearch-master-0 -c opensearch -- \
  curl -sk -u "admin:OnyxDev1!" "https://localhost:9200/_cat/indices?v&h=index,health,status,pri,rep,docs.count,store.size"

# PROD
KUBECONFIG=~/.kube/config-prod \
kubectl exec -n onyx-prod onyx-opensearch-master-0 -c opensearch -- \
  curl -sk -u "admin:$PW" "https://localhost:9200/_cat/indices?v&h=index,health,status,pri,rep,docs.count,store.size"
```

---

## 2. Cluster "red" — Notfall-Prozedur

Red bedeutet: Mind. 1 Primary-Shard ist nicht zugewiesen. Suchanfragen schlagen fuer betroffene Indices fehl.

### Schritt 1: Betroffene Shards identifizieren

```bash
# DEV
kubectl exec -n onyx-dev onyx-opensearch-master-0 -c opensearch -- \
  curl -sk -u "admin:OnyxDev1!" \
  "https://localhost:9200/_cat/shards?v&h=index,shard,prirep,state,unassigned.reason"

# PROD
KUBECONFIG=~/.kube/config-prod \
kubectl exec -n onyx-prod onyx-opensearch-master-0 -c opensearch -- \
  curl -sk -u "admin:$PW" \
  "https://localhost:9200/_cat/shards?v&h=index,shard,prirep,state,unassigned.reason"
```

Typische `unassigned.reason`-Werte:

| Reason | Bedeutung |
|--------|-----------|
| `NODE_LEFT` | Node hat den Cluster verlassen (Pod-Restart) |
| `ALLOCATION_FAILED` | Shard konnte nicht auf einen Node zugewiesen werden (meist Disk-Probleme) |
| `INDEX_CREATED` | Neu erstellt, noch nicht zugewiesen (transient, gibt sich von selbst) |

### Schritt 2: Shard-Recovery abwarten

Nach einem Pod-Neustart geht OpenSearch kurz in `red`, waehrend die Shards wiederhergestellt werden. In der Regel normalisiert sich der Status innerhalb 1-3 Minuten. Pruefen:

```bash
# DEV — alle 30s den Status beobachten
watch -n 30 'kubectl exec -n onyx-dev onyx-opensearch-master-0 -c opensearch -- \
  curl -sk -u "admin:OnyxDev1!" "https://localhost:9200/_cluster/health" | python3 -m json.tool'
```

### Schritt 3: Manuelle Shard-Zuweisung (falls Schritt 2 nicht hilft)

```bash
# Reroute erzwingen (PROD-Beispiel):
KUBECONFIG=~/.kube/config-prod \
kubectl exec -n onyx-prod onyx-opensearch-master-0 -c opensearch -- \
  curl -sk -u "admin:$PW" -X POST \
  "https://localhost:9200/_cluster/reroute?retry_failed=true"
```

### Schritt 4: Index-Neuaufbau (letzter Ausweg)

Wenn ein Index dauerhaft `red` bleibt und nicht repariert werden kann, muss er geloescht und neu aufgebaut werden. Das loest eine Re-Indexierung aller Dokumente aus.

```bash
# 1. Kaputten Index identifizieren
# 2. Index loeschen (ACHTUNG: Alle Dokumente in diesem Index gehen verloren!)
kubectl exec -n onyx-dev onyx-opensearch-master-0 -c opensearch -- \
  curl -sk -u "admin:OnyxDev1!" -X DELETE "https://localhost:9200/<INDEX_NAME>"

# 3. Re-Indexierung triggern (ueber Onyx Admin UI → Connectors → Re-Sync)
```

---

## 3. Retrieval umschalten (OpenSearch vs. Vespa)

Die Migration zwischen Vespa und OpenSearch wird in der Datenbank gesteuert. Diese Schalter koennen ohne Neustart der Pods geaendert werden.

### Migration-Status pruefen

```bash
# DEV — in API-Server-Pod:
kubectl exec -n onyx-dev deployment/onyx-dev-api-server -- \
  python3 -c "
import psycopg2, os
conn = psycopg2.connect(os.environ['POSTGRES_URI'])
cur = conn.cursor()
cur.execute('SELECT * FROM opensearch_tenant_migration_record;')
print(cur.fetchall())
conn.close()
"

# Alternativ: Via temporaeren psql-Pod (DEV):
kubectl run pg-query --restart=Never --namespace onyx-dev \
  --image=postgres:16-alpine \
  --env="PGPASSWORD=<PG_PASSWORD>" \
  --command -- psql -h <PG_HOST> -p 5432 -U onyx_app -d onyx \
  -c "SELECT * FROM opensearch_tenant_migration_record;"
sleep 5 && kubectl logs pg-query -n onyx-dev
kubectl delete pod pg-query -n onyx-dev
```

### OpenSearch-Retrieval aktivieren

```bash
# DEV
kubectl run pg-toggle --restart=Never --namespace onyx-dev \
  --image=postgres:16-alpine \
  --env="PGPASSWORD=<PG_PASSWORD>" \
  --command -- psql -h <PG_HOST> -p 5432 -U onyx_app -d onyx \
  -c "UPDATE opensearch_tenant_migration_record SET enable_opensearch_retrieval = true WHERE tenant_id = 'public';"
sleep 5 && kubectl logs pg-toggle -n onyx-dev
kubectl delete pod pg-toggle -n onyx-dev
```

### Auf Vespa-Retrieval zurueckschalten (Fallback)

```bash
# DEV
kubectl run pg-toggle --restart=Never --namespace onyx-dev \
  --image=postgres:16-alpine \
  --env="PGPASSWORD=<PG_PASSWORD>" \
  --command -- psql -h <PG_HOST> -p 5432 -U onyx_app -d onyx \
  -c "UPDATE opensearch_tenant_migration_record SET enable_opensearch_retrieval = false WHERE tenant_id = 'public';"
sleep 5 && kubectl logs pg-toggle -n onyx-dev
kubectl delete pod pg-toggle -n onyx-dev
```

**Hinweis:** `tenant_id = 'public'` ist der Standard-Tenant im FOSS-Betrieb ohne Multi-Tenancy.

---

## 4. Pod-Probleme beheben

### Pod startet nicht

```bash
# Logs pruefen:
kubectl logs onyx-opensearch-master-0 -n onyx-dev -c opensearch

# Init-Container pruefen (Security Plugin Init):
kubectl logs onyx-opensearch-master-0 -n onyx-dev -c init-sysctl 2>/dev/null || \
kubectl logs onyx-opensearch-master-0 -n onyx-dev --previous
```

Typische Ursachen:

| Fehler im Log | Ursache | Loesung |
|---------------|---------|---------|
| `max virtual memory areas vm.max_map_count [65530] is too low` | sysctl-Wert zu niedrig | Init-Container `init-sysctl` muss `privileged: true` haben (ist im Chart so vorgesehen) |
| `PVC not found` / `no space left` | Persistentes Volume fehlt oder voll | PVC pruefen (Abschnitt 4.1) |
| `Security plugin failed to initialize` | TLS-Konfiguration fehlerhaft | OpenSearch-Secret pruefen |
| `Connection refused` auf Port 9200 | OpenSearch noch nicht bereit | Warten (Cold Start dauert 60-90s) |

### 4.1 PVC-Status pruefen

```bash
# DEV
kubectl get pvc -n onyx-dev -l app=onyx-opensearch

# PROD
KUBECONFIG=~/.kube/config-prod kubectl get pvc -n onyx-prod -l app=onyx-opensearch

# Details:
kubectl describe pvc <PVC_NAME> -n onyx-dev
```

Bei `STATUS=Pending`: PVC wurde nicht provisioniert → Storage Class oder StackIT Block-Storage-Problem.

### 4.2 Ressourcen pruefen

```bash
# DEV
kubectl top pod onyx-opensearch-master-0 -n onyx-dev

# Beschreibung (Limits, Events):
kubectl describe pod onyx-opensearch-master-0 -n onyx-dev
```

PROD-Ressourcen in `values-prod.yaml`: Request 1000m/2Gi, Limit 2000m/4Gi. Bei OOMKilled: Limits erhoehen (Minimum 4 Gi RAM fuer OpenSearch-Produktion empfohlen).

---

## 5. Monitoring und Alerts

### Verfuegbare Alerts

OpenSearch hat **keinen dedizierten Prometheus-Exporter** in unserer Konfiguration (kein opensearch-exporter Deployment). Daher gibt es keine Cluster-Health-basierten Alerts.

**Vorhandener Alert:** `OpenSearchStorageFull` — ausgeloest wenn PVC-Nutzung > 85%.

```bash
# PVC-Auslastung manuell pruefen:
kubectl exec -n onyx-dev onyx-opensearch-master-0 -c opensearch -- df -h /usr/share/opensearch/data
```

### Was NICHT durch Alerts abgedeckt wird

- Cluster Health "red" (kein Exporter → kein Alert)
- Shard-Fehler
- Slow Queries

**Empfehlung:** Bei Suchauffaelligkeiten (Benutzer melden, dass Suche keine Ergebnisse liefert) zuerst Cluster Health manuell pruefen (Abschnitt 1).

---

## 6. Passwort-Referenz

| Umgebung | Passwort-Quelle | Wert / Ort |
|----------|----------------|------------|
| DEV | Helm Chart Hardcode | `OnyxDev1!` |
| PROD | GitHub Secret | `OPENSEARCH_PASSWORD` (Environment `prod`) |
| PROD — abrufen | `gh secret list --env prod` | Wert nur beim Setzen sichtbar |

Das PROD-Passwort ist nicht im Klartext abrufbar. Bei Bedarf aus dem Kubernetes-Secret lesen:

```bash
KUBECONFIG=~/.kube/config-prod \
kubectl get secret onyx-opensearch-passwords -n onyx-prod \
  -o jsonpath='{.data.admin-password}' | base64 -d
```

---

## 7. Referenzen

- OpenSearch Docs: https://opensearch.org/docs/latest/
- Upstream Tracking: Onyx Upstream-Sync #4 (2026-03-22) — OpenSearch als Primary Store eingefuehrt
- Monitoring-Konzept: `docs/referenz/monitoring-konzept.md`
- Prod-Bereitstellung: `docs/referenz/prod-bereitstellung.md` (Abschnitt 2.6 Replicas)
- Verwandtes Runbook: `docs/runbooks/stackit-postgresql.md` (DB-Queries fuer Migration-Status)
