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

## 7. Typische Fallstricke / Lessons Learned

### 1. Index-Namen muessen lowercase sein (Core #14)

**Symptom:** OpenSearch meldet beim Create-Index `Invalid index name [Qwen...], must be lowercase`. API-Server crasht in Endlosschleife, weil der Indexing-Worker den Index nicht anlegen kann.

**Ursache:** Upstream Onyx nutzt `clean_model_name()` aus `backend/onyx/natural_language_processing/search_nlp_models.py`, die den Modellnamen in den Index-Namen uebernimmt. OpenSearch erlaubt aber keine Grossbuchstaben in Index-Namen — Vespa schon. Upstream-Bug, betrifft jeden OpenSearch-User mit Modellnamen die Grossbuchstaben enthalten (z.B. Qwen3-VL-Embedding).

**Fix (unser Patch):** Core #14 `search_nlp_models.py` — `.lower()` an den Return-Value von `clean_model_name()` anhaengen. Bei jedem Upstream-Sync pruefen, ob Upstream den Fix selbst uebernommen hat (dann Patch entfernen).

**Recovery bei bereits korrumpiertem Zustand:** DB-Feld manuell korrigieren:
```sql
UPDATE search_settings SET model_name = lower(model_name) WHERE model_name != lower(model_name);
```

### 2. `yellow`-Status ist normal bei Single-Node

**Symptom:** Cluster-Health zeigt `yellow`, unassigned_shards > 0.

**Ursache:** Single-Node-Setup. Replicas koennen nicht auf den gleichen Node zugewiesen werden wie der Primary-Shard. Das ist strukturell unvermeidbar.

**Anwendung:**
- **KEIN Alert** bei `yellow` oder `unassigned_shards > 0`. Alert `OpenSearchUnassignedShards` hat seit 2026-04-16 Threshold `> 20` (nicht `> 0`), weil bei 10 Indices mit je 2 Replicas exakt 20 unassigned Shards erwartet sind.
- Bei Scale-Out auf 3+ Nodes wird `green` erwartet → Threshold runter auf `> 0` anpassen.

### 3. OpenSearch-Passwort URL-encoden

**Symptom:** API-Server crasht mit `Invalid URL: Cannot parse "https://admin:password/with/slash@..."`. Logs zeigen SQL-Parse-Fehler.

**Ursache:** OpenSearch-Passwoerter mit `/`, `@`, `:`, `#` brechen die URI, weil sie als URI-Delimiter interpretiert werden. Das betrifft jede via `openssl rand -base64` generierte Passphrase mit `/`.

**Anwendung:**
- Passwoerter per `openssl rand -base64 24 | tr -dc 'a-zA-Z0-9!@#$%' | head -c 24` generieren — keine URI-Delimiter.
- Oder bei bestehendem Passwort: In Env-Vars URL-encoden (`%2F` fuer `/`, `%40` fuer `@`, `%3A` fuer `:`). Helm macht das **nicht automatisch** — der Passwort-Wert landet unescaped in der Connection-URL.

### 4. Clean-Install PROD ohne `opensearch_admin_password` = Datenverlust

**Symptom:** Nach `helm delete + install` auf PROD kann OpenSearch nicht mehr auf bestehende Daten zugreifen. `_cat/indices` liefert 0 Indices zurueck.

**Ursache:** Ohne `--set auth.opensearch.values.opensearch_admin_password=<PW>` verwendet der Chart einen Onyx-Default. Das alte PVC ist noch da, aber OpenSearch kann sich nicht mehr authentifizieren und erstellt einen leeren neuen Cluster-State.

**Anwendung:**
- **IMMER** bei manuellem PROD-Deploy `--set "auth.opensearch.values.opensearch_admin_password=$OPENSEARCH_PASSWORD"` mitgeben.
- CI/CD in `stackit-deploy.yml` macht das automatisch via GitHub Secret.
- Bei Clean-Install-Bedarf mit Daten-Erhalt: Erst altes PVC sichern, dann Clean-Install mit richtigem Passwort.

### 5. JVM-Heap niedrig setzen ist tricky

**Symptom:** OpenSearch OOM-Killed bei ersten Indexierungs-Writes, obwohl `requests.memory: 2Gi` in values gesetzt.

**Ursache:** OpenSearch setzt JVM-Heap default auf ~50% des Container-Memory-Limits. Ohne explizite `OPENSEARCH_JAVA_OPTS` nimmt es den Default, der bei 2Gi Limit = 1Gi Heap nicht reicht fuer ernsthaften Traffic.

**Anwendung:**
- DEV/TEST: `-Xms512m -Xmx512m` (niedrig, kein Datenvolumen)
- PROD: `-Xms2g -Xmx2g` bei 4Gi-Container (50%-Regel)
- Bei OOM: Erst Heap erhoehen, dann Container-Limit erhoehen.

### 6. StatefulSet PVC ist immutable

**Symptom:** `helm upgrade` failt mit `StatefulSet forbidden: updates to statefulset spec ... forbidden`.

**Ursache:** `volumeClaimTemplates` darf in einem bestehenden StatefulSet nicht geaendert werden. Betrifft Groesse, StorageClass, AccessMode.

**Anwendung:**
- **Kein In-Place-Resize** moeglich.
- Groessenaenderung = StatefulSet loeschen (`kubectl delete sts onyx-opensearch-master`), PVC manuell loeschen (`kubectl delete pvc`), dann `helm upgrade`. **Daten gehen verloren — Re-Indexierung aller Dokumente noetig.**
- Langfristig: Groesszuegig dimensionieren (mindestens 20Gi fuer PROD).

---

## 8. Referenzen

- OpenSearch Docs: https://opensearch.org/docs/latest/
- Upstream Tracking: Onyx Upstream-Sync #4 (2026-03-22) — OpenSearch als Primary Store eingefuehrt
- Monitoring-Konzept: `docs/referenz/monitoring-konzept.md`
- Prod-Bereitstellung: `docs/referenz/prod-bereitstellung.md` (Abschnitt 2.6 Replicas)
- Verwandtes Runbook: `docs/runbooks/stackit-postgresql.md` (DB-Queries fuer Migration-Status)
