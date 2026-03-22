# Runbook: Alert-Antwort

> **Zweck:** Handlungsanweisungen fuer jeden Custom-Alert des VÖB Chatbot Monitorings.
> **Scope:** Nur eigene Custom-Alerts (22 Regeln). Standard kube-prometheus-stack Alerts (KubeDeploymentReplicasMismatch etc.) sind nicht abgedeckt.
> **Voraussetzung:** Kubeconfig muss fuer den jeweiligen Cluster konfiguriert sein.
> - DEV/TEST: `~/.kube/config` (Cluster `vob-devtest`)
> - PROD: `KUBECONFIG=~/.kube/config-prod` vor jedem Befehl
>
> **Grafana-Zugang:**
> ```bash
> # DEV/TEST:
> kubectl port-forward -n monitoring svc/monitoring-grafana 3001:80
> # PROD:
> KUBECONFIG=~/.kube/config-prod kubectl port-forward -n monitoring svc/monitoring-grafana 3001:80
> # → http://localhost:3001 (admin / Passwort aus K8s Secret)
> ```
> **Konzept:** `docs/referenz/monitoring-konzept.md`

---

## Übersicht

| # | Alert | Severity | Environment | Kategorie |
|---|-------|----------|-------------|-----------|
| 1 | `APIDown` | critical | DEV/TEST/PROD | API |
| 2 | `PodCrashLooping` | critical | DEV/TEST/PROD | Kubernetes |
| 3 | `HighErrorRate` | warning | DEV/TEST/PROD | API |
| 4 | `DBPoolExhausted` | warning | DEV/TEST/PROD | Datenbank |
| 5 | `HighSlowRequests` | warning | DEV/TEST/PROD | API |
| 6 | `NodeMemoryPressure` | critical | DEV/TEST/PROD | Infrastruktur |
| 7 | `NodeDiskPressure` | warning | DEV/TEST/PROD | Infrastruktur |
| 8 | `VespaStorageFull` | warning | DEV/TEST/PROD | Storage |
| 8b | `OpenSearchStorageFull` | warning (DEV/TEST) / critical (PROD) | DEV/TEST/PROD | Storage |
| 9 | `CertExpiringSoon` | warning | DEV/TEST/PROD | TLS |
| 10 | `PGExporterDown` | critical | DEV/TEST/PROD | Monitoring-Infrastruktur |
| 11 | `RedisExporterDown` | critical | DEV/TEST/PROD | Monitoring-Infrastruktur |
| 12 | `PGConnectionsHigh` | warning | DEV/TEST/PROD | Datenbank |
| 13 | `PGDeadlocks` | warning | DEV/TEST/PROD | Datenbank |
| 14 | `PGHighRollbackRate` | warning | DEV/TEST/PROD | Datenbank |
| 15 | `PGDatabaseGrowing` | warning | DEV/TEST/PROD | Datenbank |
| 16 | `RedisMemoryHigh` | warning | DEV/TEST/PROD | Redis |
| 17 | `RedisHighEvictions` | warning | DEV/TEST/PROD | Redis |
| 18 | `RedisCacheHitRateLow` | warning | DEV/TEST/PROD | Redis |
| 19 | `RedisRejectedConnections` | critical | DEV/TEST/PROD | Redis |
| 20 | `PGCacheHitRateLow` | warning | DEV/TEST/PROD | Datenbank |
| 21 | `PGBackupCheckFailed` | critical | PROD | Backup |
| 22 | `PGBackupCheckNotScheduled` | warning | PROD | Backup |

> **Hinweis OpenSearch Cluster-Health:** Ein `OpenSearchClusterRed`-Alert ist konzeptionell geplant, aber noch nicht implementiert (kein OpenSearch Prometheus Exporter deployed). Der PVC-Alert `OpenSearchStorageFull` ist aktiv.

---

## Alert: APIDown

**Severity:** critical
**Environment:** DEV/TEST/PROD
**Bedeutung:** Der Prometheus Scrape-Target fuer die Onyx API (`/metrics` auf Port 8080) antwortet seit 2 Minuten nicht. Der Alert unterscheidet nicht zwischen "API komplett down" und "nur Metrics-Endpoint blockiert".

**Diagnose:**
```bash
# DEV/TEST: Namespace anpassen (onyx-dev oder onyx-test)
kubectl get pods -n onyx-dev
kubectl describe pod -n onyx-dev -l app.kubernetes.io/name=api-server

# PROD:
KUBECONFIG=~/.kube/config-prod kubectl get pods -n onyx-prod
KUBECONFIG=~/.kube/config-prod kubectl describe pod -n onyx-prod -l app.kubernetes.io/name=api-server

# API direkt testen (DEV-Beispiel):
kubectl port-forward -n onyx-dev svc/onyx-dev-api-service 8080:8080
curl http://localhost:8080/health
curl http://localhost:8080/metrics

# Logs pruefen:
kubectl logs -n onyx-dev -l app.kubernetes.io/name=api-server --tail=50
```

**Lösung:**
1. Sind API-Pods Running? Falls nicht → `PodCrashLooping` als eigentliche Ursache behandeln.
2. Alle Pods Running, aber Scrape failt? NetworkPolicy pruefen:
   ```bash
   kubectl get networkpolicy -n onyx-dev
   # allow-monitoring-scrape muss vorhanden sein
   ```
3. `onyx-dev-api-service` existiert?
   ```bash
   kubectl get svc -n onyx-dev | grep api
   ```
4. Wenn alle Checks gruen, aber Alert weiterhin aktiv: Prometheus Scrape-Config pruefen (Grafana → Status → Targets).
5. Letzter Ausweg: Deployment neu starten:
   ```bash
   kubectl rollout restart deployment/onyx-dev-api-server -n onyx-dev
   ```

**Eskalation:** Sofort wenn PROD betroffen (SLA). DEV/TEST: Innerhalb 1h loesen.

---

## Alert: PodCrashLooping

**Severity:** critical
**Environment:** DEV/TEST/PROD
**Bedeutung:** Ein Pod in `onyx-dev`, `onyx-test` oder `onyx-prod` hat in der letzten Stunde mehr als 3 Restarts. Haeufigste Ursachen: OOM-Kill, Startup-Fehler, fehlerhafte Config.

**Diagnose:**
```bash
# Welcher Pod crasht?
kubectl get pods -n onyx-dev --field-selector=status.phase!=Running
kubectl get events -n onyx-dev --sort-by='.lastTimestamp' | tail -20

# PROD:
KUBECONFIG=~/.kube/config-prod kubectl get pods -n onyx-prod
KUBECONFIG=~/.kube/config-prod kubectl get events -n onyx-prod --sort-by='.lastTimestamp' | tail -20

# Logs des crashenden Pods (letzter Run):
kubectl logs -n onyx-dev <pod-name> --previous

# OOM-Kill pruefen:
kubectl describe pod -n onyx-dev <pod-name> | grep -A5 "Last State"
# "OOMKilled" → RAM Limit zu niedrig
```

**Lösung:**
1. **OOMKilled:** RAM Limit in `values-common.yaml` erhoehen. Helm Upgrade.
2. **Startup-Fehler (z.B. DB-Connection):** Netz-/DB-Konnektivitaet pruefen. PG Exporter Status in Prometheus.
3. **Alembic-Migration fehlgeschlagen:** API-Logs beim Start pruefen auf `alembic.runtime.migration`. Ggf. Migration manuell ausfuehren (siehe `docs/runbooks/stackit-postgresql.md`).
4. **Celery-Worker crasht:** Redis-Verbindung pruefen (`RedisRejectedConnections` Alert?).

**Eskalation:** PROD: Sofort. DEV/TEST: Innerhalb 2h loesen oder auf den naechsten Tag verschieben.

---

## Alert: HighErrorRate

**Severity:** warning
**Environment:** DEV/TEST/PROD
**Bedeutung:** Mehr als 5% aller HTTP-Requests enden mit einem 5xx Server Error. Normaler Baseline sollte bei 0-0.5% liegen.

**Diagnose:**
```bash
# API-Logs auf Fehler pruefen:
kubectl logs -n onyx-dev -l app.kubernetes.io/name=api-server --tail=100 | grep -E "ERROR|500|502|503"

# PROD:
KUBECONFIG=~/.kube/config-prod kubectl logs -n onyx-prod -l app.kubernetes.io/name=api-server --tail=100 | grep -E "ERROR|500|502|503"

# Grafana: Onyx API Dashboard → Error Rate Panel + Request Rate Panel
# Welche Endpoints schlagen fehl? (Prometheus Query):
# rate(http_requests_total{status=~"5..",environment="prod"}[5m]) by (handler)
```

**Lösung:**
1. Handvoll einzelner Endpoints betroffen (z.B. `/api/chat`)? LLM-Provider-Status pruefen (StackIT AI Model Serving).
2. Alle Endpoints betroffen? DB-Verbindung pruefen (`DBPoolExhausted` Alert?), API-Pod-Status pruefen.
3. Bei LLM-Ausfall: Nutzer informieren, ggf. Fallback-Modell konfigurieren (Onyx Admin UI).
4. Transiente Fehler (kurzer Spike, Alert resolved sich selbst)? Kein Handlungsbedarf, aber im Grafana-Dashboard dokumentieren.

**Eskalation:** PROD: Bei anhaltender Fehlerrate (>15min) und keine LLM-Provider-Ursache → Niko benachrichtigen.

---

## Alert: DBPoolExhausted

**Severity:** warning
**Environment:** DEV/TEST/PROD
**Bedeutung:** Der SQLAlchemy Connection Pool nutzt Overflow-Connections (`onyx_db_pool_overflow > 0`). Das bedeutet: alle regulaeren Pool-Connections sind vergeben und zusaetzliche Connections werden ausserhalb des Pools geoeffnet. Haelt das an, droht `TooManyConnectionsError`.

**Diagnose:**
```bash
# DB Connection Pool Metriken (Prometheus Query in Grafana):
# onyx_db_pool_checked_out  → aktive Connections
# onyx_db_pool_overflow     → Overflow (sollte 0 sein)
# onyx_db_pool_size         → Pool-Groesse (Default: 10-20)

# PG aktive Backends pruefen:
kubectl port-forward -n monitoring svc/postgres-exporter-dev 9187:9187
curl -s http://localhost:9187/metrics | grep "pg_stat_database_numbackends{datname=\"onyx\"}"

# PROD:
KUBECONFIG=~/.kube/config-prod kubectl port-forward -n monitoring svc/postgres-exporter-prod 9187:9187
curl -s http://localhost:9187/metrics | grep "pg_stat_database_numbackends{datname=\"onyx\"}"
```

**Lösung:**
1. Kurzzeitiger Spike (resolved sich selbst)? Kein Handlungsbedarf.
2. Dauerhafter Overflow:
   - Celery-Worker ueberlasten DB? Celery Queue Length in Grafana pruefen.
   - `POSTGRES_POOL_SIZE` + `POSTGRES_POOL_OVERFLOW` Umgebungsvariablen erhoehen (in `values-common.yaml` oder `deployment/docker_compose/.env`).
   - PG `max_connections` auf StackIT pruefen (Default: 100, StackIT Flex: je nach Tier).
3. Falls kritisch: Onyx-API-Pods neustarten (gibt Connections frei):
   ```bash
   kubectl rollout restart deployment/onyx-dev-api-server -n onyx-dev
   ```

**Eskalation:** PROD: Wenn Overflow >5min anhält und PGConnectionsHigh auch feuert → Niko informieren.

---

## Alert: HighSlowRequests

**Severity:** warning
**Environment:** DEV/TEST/PROD
**Bedeutung:** Mehr als 1 Slow Request pro Sekunde seit 10 Minuten. Threshold: Requests die laenger als `SLOW_REQUEST_THRESHOLD_SECONDS` dauern (Default: 1s).

**Diagnose:**
```bash
# Prometheus Query (Grafana):
# rate(onyx_api_slow_requests_total[5m])  → aktuelle Rate
# rate(onyx_api_slow_requests_total[5m]) by (handler)  → nach Endpoint aufschluesseln

# DB-Latenz pruefen (haeufigstes Slow-Request-Ursache):
# onyx_db_connection_hold_seconds_bucket → Connection Hold Time Histogram

# LLM-Requests koennten als "slow" gezaehlt werden — je nach Threshold-Konfiguration
```

**Lösung:**
1. LLM-Endpoints (z.B. `/api/chat/send-message`) sind fast immer "slow" — das ist erwartet. Pruefe ob nur diese Endpoints betroffen sind.
2. DB-Endpoints slow? `DBPoolExhausted` oder schlechte Query-Performance → Grafana PG Dashboard pruefen.
3. Falls der Alert nervig feuert bei normalem LLM-Traffic: `SLOW_REQUEST_THRESHOLD_SECONDS` Umgebungsvariable erhoehen (z.B. auf 5 Sekunden).

**Eskalation:** Wenn kombiniert mit hoher Error-Rate oder DBPoolExhausted → Prioritaet erhoehen.

---

## Alert: NodeMemoryPressure

**Severity:** critical
**Environment:** DEV/TEST/PROD
**Bedeutung:** Ein K8s-Node hat weniger als 10% freien RAM. Pods koennten OOM-killed werden.

**Diagnose:**
```bash
# Welcher Node?
kubectl top nodes
kubectl describe node <node-name> | grep -A10 "Conditions"

# PROD:
KUBECONFIG=~/.kube/config-prod kubectl top nodes
KUBECONFIG=~/.kube/config-prod kubectl describe node <node-name> | grep -A10 "Conditions"

# Welche Pods verbrauchen am meisten RAM?
kubectl top pods --all-namespaces --sort-by=memory | head -20

# PROD:
KUBECONFIG=~/.kube/config-prod kubectl top pods --all-namespaces --sort-by=memory | head -20
```

**Lösung:**
1. DEV/TEST (g1a.4d, knappe Nodes): Pruefe ob TEST-Exporter laufen koennen ohne TEST-App-Pods (kein Traffic, nur Overhead). TEST-Exporter ggf. skalieren:
   ```bash
   kubectl scale deployment postgres-exporter-test -n monitoring --replicas=0
   kubectl scale deployment redis-exporter-test -n monitoring --replicas=0
   ```
2. PROD: Sofortmassnahme — Pods mit niedrigster Priority identifizieren und ggf. skalieren.
3. Langfristig: RAM-Limits in `values-common.yaml` pruefen. Grossen Verbraucher (Vespa, Prometheus) entlasten.
4. Node-Pool upscalen wenn dauerhaft >90% RAM (Terraform, `node_count` erhoehen).

**Eskalation:** PROD: Sofort eskalieren. Wenn OOM-Kill droht und keine schnelle Loesung: Niko informieren (ggf. Node-Pool-Erweiterung authorisieren).

---

## Alert: NodeDiskPressure

**Severity:** warning
**Environment:** DEV/TEST/PROD
**Bedeutung:** Weniger als 15% freier Disk auf dem Root-Filesystem (`/`) eines Nodes. Container-Logs und Image-Pulls koennen fehlschlagen.

**Diagnose:**
```bash
# Node Disk-Nutzung:
kubectl describe node <node-name> | grep -A5 "Conditions"

# PROD:
KUBECONFIG=~/.kube/config-prod kubectl describe node <node-name> | grep -A5 "Conditions"

# Grafana: Node-Exporter Dashboard → Disk Usage Panel
# Prometheus Query:
# node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes
```

**Lösung:**
1. Container-Logs sind haeufig groesster Verbraucher. Log-Rotation aktiviert? (Standard-K8s-Log-Rotation sollte aktiv sein)
2. Unused Docker Images entfernen (automatisch via kubelet Garbage Collection, aber ggf. manuell):
   ```bash
   # Auf Node (via kubectl node debug oder SSH falls verfuegbar)
   docker image prune -a
   ```
3. Vespa PVC oder OpenSearch PVC voll? → `VespaStorageFull` / `OpenSearchStorageFull` Alert behandeln.
4. Terraform: Node-Disk-Groesse erhoehen (`disk_size` in `variables.tf`).

**Eskalation:** Wenn <5% Disk-Restbestand → critical, Niko sofort informieren.

---

## Alert: VespaStorageFull

**Severity:** warning
**Environment:** DEV/TEST/PROD
**Bedeutung:** Die Vespa PVC hat weniger als 20% freien Speicher. Vespa laeuft aktuell im "Zombie-Mode" (kein Produktiv-Traffic, OpenSearch ist Primary). Die PVC ist aber noch aktiv.

**Diagnose:**
```bash
# PVC-Status pruefen:
kubectl get pvc -n onyx-dev | grep vespa
kubectl describe pvc -n onyx-dev <vespa-pvc-name>

# PROD:
KUBECONFIG=~/.kube/config-prod kubectl get pvc -n onyx-prod | grep vespa
KUBECONFIG=~/.kube/config-prod kubectl describe pvc -n onyx-prod <vespa-pvc-name>

# Prometheus Query:
# kubelet_volume_stats_available_bytes{persistentvolumeclaim=~"vespa.*"} / kubelet_volume_stats_capacity_bytes
```

**Lösung:**
1. Vespa ist im Zombie-Mode — kein neuer Index-Traffic geht hinein. Warum wird die PVC voller?
2. Potenzielle Ursache: Vespa schreibt interne Logs/Garbage. Pruefe ob Vespa-Pod laeuft und ob er schreibt.
3. Kurzfristig: PVC-Groesse erhoehen (PVC-Resize via StackIT oder `kubectl patch`).
4. Langfristig: Sobald OpenSearch-Migration vollstaendig, Vespa-PVC und Vespa-Deployment entfernen.

**Eskalation:** Wenn PVC >95% voll → Vespa-Pod wuerde Schreibfehler produzieren. Niko informieren (Decision: PVC-Resize oder Vespa-Deployment stoppen).

---

## Alert: OpenSearchStorageFull

**Severity:** warning (DEV/TEST) / critical (PROD)
**Environment:** DEV/TEST/PROD
**Bedeutung:** Die OpenSearch PVC hat weniger als 20% (DEV/TEST) bzw. 10% (PROD) freien Speicher. OpenSearch ist der Primary Vector Store — bei vollem PVC koennten Writes fehlschlagen.

**Diagnose:**
```bash
# PVC-Status pruefen:
kubectl get pvc -n onyx-dev | grep opensearch
kubectl describe pvc -n onyx-dev <opensearch-pvc-name>

# PROD:
KUBECONFIG=~/.kube/config-prod kubectl get pvc -n onyx-prod | grep opensearch
KUBECONFIG=~/.kube/config-prod kubectl describe pvc -n onyx-prod <opensearch-pvc-name>

# Prometheus Query:
# kubelet_volume_stats_available_bytes{persistentvolumeclaim=~"opensearch.*"} / kubelet_volume_stats_capacity_bytes
```

**Lösung:**
1. Wie schnell wächst die PVC? Trend im Grafana pruefen (letzten 7 Tage).
2. Sofortmassnahme (PROD): Index-Pruning in Onyx Admin UI pruefen. Alte/ungenutzte Connectoren deaktivieren.
3. PVC-Groesse erhoehen:
   ```bash
   # PVC-Resize (StackIT unterstuetzt Volume-Expansion bei StorageClass "standard"):
   kubectl patch pvc <opensearch-pvc-name> -n onyx-prod -p '{"spec":{"resources":{"requests":{"storage":"50Gi"}}}}'
   # Helm Values aktualisieren (Wert in values-prod.yaml anpassen), dann Helm Upgrade
   ```
4. Langfristig: OpenSearch Retention-Policy konfigurieren.

**Eskalation:** PROD: Bei <5% Restbestand sofort. Schreib-Fehler in OpenSearch = Suchfunktion degradiert.

---

## Alert: CertExpiringSoon

**Severity:** warning
**Environment:** DEV/TEST/PROD
**Bedeutung:** Ein TLS-Zertifikat (verwaltet durch cert-manager) laeuft in weniger als 14 Tagen ab.

**Diagnose:**
```bash
# Welches Zertifikat?
kubectl get certificates -n onyx-dev
kubectl describe certificate -n onyx-dev <cert-name>

# PROD:
KUBECONFIG=~/.kube/config-prod kubectl get certificates --all-namespaces
KUBECONFIG=~/.kube/config-prod kubectl describe certificate <cert-name> -n <namespace>

# cert-manager Logs:
kubectl logs -n cert-manager -l app=cert-manager --tail=50
```

**Lösung:**
1. Unter normalen Umstaenden erneuert cert-manager Zertifikate automatisch (Let's Encrypt, 30 Tage vor Ablauf).
2. Falls Renewal fehlschlaegt → cert-manager Logs pruefen. Haeufige Ursachen:
   - DNS-01 Challenge fehlgeschlagen (Cloudflare API Token abgelaufen?)
   - Rate Limit Let's Encrypt (max 5 Certs/Domain/Woche)
   - ClusterIssuer-Status nicht Ready
3. ClusterIssuer Status pruefen:
   ```bash
   kubectl describe clusterissuer onyx-dev-letsencrypt
   # PROD:
   KUBECONFIG=~/.kube/config-prod kubectl describe clusterissuer onyx-prod-letsencrypt
   ```
4. Manuelles Renewal anstoessen:
   ```bash
   kubectl annotate certificate <cert-name> -n onyx-dev cert-manager.io/issue-once="$(date)"
   ```
5. Details: `docs/runbooks/dns-tls-setup.md`

**Eskalation:** Wenn Zertifikat in <7 Tagen ablaeuft und kein auto-Renewal moeglich → Niko informieren. HTTPS-Ausfall in <7 Tagen.

---

## Alert: PGExporterDown

**Severity:** critical
**Environment:** DEV/TEST/PROD
**Bedeutung:** Der `postgres_exporter` (in Namespace `monitoring`) antwortet nicht. Prometheus kann keine PG-Metriken scrapen. Alerts basierend auf PG-Metriken (12-15, 20) sind nicht zuverlaessig.

**Diagnose:**
```bash
# Exporter-Pod pruefen (DEV als Beispiel, analog TEST/PROD):
kubectl get pods -n monitoring | grep postgres
kubectl logs -n monitoring -l app=postgres-exporter-dev --tail=50

# PROD:
KUBECONFIG=~/.kube/config-prod kubectl get pods -n monitoring | grep postgres
KUBECONFIG=~/.kube/config-prod kubectl logs -n monitoring -l app=postgres-exporter-prod --tail=50

# Secret vorhanden?
kubectl get secret pg-exporter-dev -n monitoring
```

**Lösung:**
1. Pod nicht Running? → Deployment neustarten:
   ```bash
   kubectl rollout restart deployment/postgres-exporter-dev -n monitoring
   # PROD:
   KUBECONFIG=~/.kube/config-prod kubectl rollout restart deployment/postgres-exporter-prod -n monitoring
   ```
2. Pod Running aber Scrape failt? DB-Connection im Log pruefen. DSN korrekt?
   ```bash
   kubectl logs -n monitoring <pg-exporter-pod> | grep -E "error|failed|connection"
   ```
3. Secret `pg-exporter-dev` korrekt? Base64-decode und pruefen:
   ```bash
   kubectl get secret pg-exporter-dev -n monitoring -o jsonpath='{.data.DATA_SOURCE_NAME}' | base64 -d
   ```
4. PG selbst nicht erreichbar (StackIT outage)? → `PGBackupCheckFailed` wuerde ebenfalls feuern.

**Eskalation:** PROD: Wenn PG-Exporter laenger als 1h down → manuelle PG-Health-Pruefung erwaegen.

---

## Alert: RedisExporterDown

**Severity:** critical
**Environment:** DEV/TEST/PROD
**Bedeutung:** Der `redis_exporter` antwortet nicht. Prometheus kann keine Redis-Metriken scrapen. Alerts 16-19 sind nicht zuverlaessig.

**Diagnose:**
```bash
# Exporter-Pod pruefen:
kubectl get pods -n monitoring | grep redis
kubectl logs -n monitoring -l app=redis-exporter-dev --tail=50

# PROD:
KUBECONFIG=~/.kube/config-prod kubectl get pods -n monitoring | grep redis
KUBECONFIG=~/.kube/config-prod kubectl logs -n monitoring -l app=redis-exporter-prod --tail=50
```

**Lösung:**
1. Pod neustarten:
   ```bash
   kubectl rollout restart deployment/redis-exporter-dev -n monitoring
   # PROD:
   KUBECONFIG=~/.kube/config-prod kubectl rollout restart deployment/redis-exporter-prod -n monitoring
   ```
2. Redis-Verbindung pruefen. Redis-Passwort noch korrekt?
   ```bash
   kubectl get secret redis-exporter-dev -n monitoring -o jsonpath='{.data.REDIS_PASSWORD}' | base64 -d
   ```
3. NetworkPolicy pruefen — `07-allow-redis-exporter-egress.yaml` muss den aktuellen Namespace enthalten.

**Eskalation:** PROD: Wenn Redis-Exporter down und gleichzeitig Celery-Probleme vermutet werden → priorisieren.

---

## Alert: PGConnectionsHigh

**Severity:** warning
**Environment:** DEV/TEST/PROD
**Bedeutung:** Aktive PostgreSQL Backends ueberschreiten 80% von `max_connections`. Bei StackIT Managed PG Flex ist `max_connections` tier-abhaengig (Default meist 100-200).

**Diagnose:**
```bash
# Prometheus Query (Grafana):
# sum(pg_stat_database_numbackends{datname="onyx"}) by (job,server)
# pg_settings_max_connections

# PG Exporter Health (schnelle Methode):
kubectl port-forward -n monitoring svc/postgres-exporter-dev 9187:9187
curl -s http://localhost:9187/metrics | grep -E "numbackends|max_connections"

# PROD:
KUBECONFIG=~/.kube/config-prod kubectl port-forward -n monitoring svc/postgres-exporter-prod 9187:9187
curl -s http://localhost:9187/metrics | grep -E "numbackends|max_connections"
```

**Lösung:**
1. Kurzzeitiger Spike (z.B. nach Deployment)? Resolves sich selbst.
2. Dauerhaft hoch: Welche Pods halten Connections? `DBPoolExhausted` ebenfalls aktiv?
3. Pool-Konfiguration anpassen (`POSTGRES_POOL_SIZE` reduzieren, ggf. mehrere API-Replicas).
4. Langfristig: PgBouncer evaluieren (Connection Pooler vor PG Flex).
5. StackIT PG Flex: `max_connections` kann durch Upgrade des Tiers erhoehen.

**Eskalation:** Wenn Connections >95% → `TooManyConnectionsError` droht → Niko informieren.

---

## Alert: PGDeadlocks

**Severity:** warning
**Environment:** DEV/TEST/PROD
**Bedeutung:** Mehr als 5 PostgreSQL Deadlocks in 5 Minuten. Deadlocks koennen Transaktionen abbuerden und zu Fehler-Responses fuehren.

**Diagnose:**
```bash
# Prometheus Query (Grafana):
# increase(pg_stat_database_deadlocks{datname="onyx"}[5m])

# Trend anschauen: Wann haben sie begonnen?
# Mit welchem Deployment / Useraktivitaet korreliert?
```

**Lösung:**
1. Transiente Deadlocks (1-5, einmalig)? Onyx koennte eigene Retry-Logik haben — Logs pruefen.
2. Systematische Deadlocks (dauerhaft >5/5min): Onyx-Anwendungsfehler. Korreliert mit einem bestimmten Feature (z.B. Indexierung)?
   - API-Logs auf `DeadlockError` pruefen:
     ```bash
     kubectl logs -n onyx-dev -l app.kubernetes.io/name=api-server | grep -i deadlock
     ```
3. Upstream Onyx Issue? GitHub Issues pruefen. Ggf. Fix als Cherry-Pick oder Upstream-Sync.

**Eskalation:** Wenn Deadlocks mit Nutzer-Errors korrelieren → Niko informieren. Kein bekanntes Eskalations-SLA.

---

## Alert: PGHighRollbackRate

**Severity:** warning
**Environment:** DEV/TEST/PROD
**Bedeutung:** Mehr als 5% der PG-Transaktionen werden gerollt-back. PROD: Nur bei genuegend Traffic (>10 tx/sec), um False Positives bei Idle-System zu vermeiden.

**Diagnose:**
```bash
# Prometheus Query (Grafana):
# rate(pg_stat_database_xact_rollback{datname="onyx"}[5m])
# rate(pg_stat_database_xact_commit{datname="onyx"}[5m])

# API-Fehler korrelieren mit Rollbacks?
kubectl logs -n onyx-dev -l app.kubernetes.io/name=api-server | grep -iE "rollback|transaction|error"
```

**Lösung:**
1. Hohe Rollback-Rate oft mit hoher Error-Rate (`HighErrorRate`) kombiniert → diese Ursache zuerst behandeln.
2. Onyx benutzt Transaktionen extensiv (besonders Celery-Tasks). Celery-Restarts koennen zu Rollbacks fuehren.
3. Falls kein korreliertes Ereignis → Upstream-Issue, Niko informieren.

**Eskalation:** Wenn Rate >20% dauerhaft → aktiver Datenverlust moeglich. Niko sofort informieren.

---

## Alert: PGDatabaseGrowing

**Severity:** warning
**Environment:** DEV/TEST/PROD
**Bedeutung:** Die `onyx` Datenbank ist groesser als 10 GB. Das ist ein Kapazitaets-Fruhwarn-Alert, keine Notfallsituation.

**Diagnose:**
```bash
# Prometheus Query (Grafana):
# pg_database_size_bytes{datname="onyx"} / 1024 / 1024 / 1024  → in GB

# Groesste Tabellen (direkter DB-Zugriff noetig):
# DEV: kubectl exec -it -n onyx-dev <api-pod> -- python -c "from onyx.db.engine import get_session; ..."
# Oder per PG Exporter Metriken: pg_stat_user_tables_n_dead_tup
```

**Lösung:**
1. Chat-History ist haeufig groesster Verbraucher. Retention-Policy konfigurieren (Onyx Admin UI).
2. Vespa-Metadaten, Index-Attempts, Connector-Logs koennen gross werden.
3. PG VACUUM analysieren: Bloat durch tote Rows?
4. Kapazitaet: StackIT PG Flex hat konfiguriertes Storage-Limit. Bei 10 GB alert ist noch Headroom. Ueberwachen ob Wachstum linear oder exponentiell.

**Eskalation:** Wenn >80% des StackIT PG Flex Storage-Limits erreicht → Terraform `storage_size_gb` erhoehen.

---

## Alert: RedisMemoryHigh

**Severity:** warning
**Environment:** DEV/TEST/PROD
**Bedeutung:** Redis-Speicher ueberschreitet 80% von `maxmemory`. Wenn `maxmemory` erreicht wird, greift Eviction Policy. Celery nutzt Redis intensiv fuer Task-Queue.

**Diagnose:**
```bash
# Prometheus Query (Grafana):
# redis_memory_used_bytes / redis_memory_max_bytes

# Redis Exporter Details:
kubectl port-forward -n monitoring svc/redis-exporter-dev 9121:9121
curl -s http://localhost:9121/metrics | grep -E "memory_used|memory_max|evicted"

# PROD:
KUBECONFIG=~/.kube/config-prod kubectl port-forward -n monitoring svc/redis-exporter-prod 9121:9121
curl -s http://localhost:9121/metrics | grep -E "memory_used|memory_max|evicted"
```

**Lösung:**
1. Was belegt Redis? Celery Task-Queue, Session-Cache, Lock-Keys?
2. `maxmemory` erhoehen in Helm Values (Redis Operator Config) oder `values-common.yaml`.
3. Celery-Queue-Stau (viele queued Tasks)? → Celery-Worker-Anzahl erhoehen.
4. Wenn `RedisHighEvictions` ebenfalls aktiv → Eviction hat bereits begonnen (Items werden geloescht).

**Eskalation:** Wenn >95% + Evictions aktiv → Celery-Tasks koennen verloren gehen. Niko informieren.

---

## Alert: RedisHighEvictions

**Severity:** warning
**Environment:** DEV/TEST/PROD
**Bedeutung:** Redis hat mehr als 100 Keys in 5 Minuten evicted (durch maxmemory-Policy). Das bedeutet Datenverlust im Redis-Cache oder sogar Celery-Task-Verlust.

**Diagnose:**
```bash
# Prometheus Query:
# increase(redis_evicted_keys_total[5m])
# redis_memory_used_bytes / redis_memory_max_bytes  → wie voll ist Redis?

# Celery-Worker Logs auf Task-Fehler pruefen:
kubectl logs -n onyx-dev -l app.kubernetes.io/name=celery --tail=100 | grep -E "error|lost|retry"
```

**Lösung:**
1. Sofortmassnahme: `maxmemory` erhoehen.
2. Celery-Tasks verloren? Welche Tasks? Betrifft Indexierung (idempotent, wird beim naechsten Run wiederholt) oder kritische Tasks?
3. Connector-Sync-Status pruefen:
   ```bash
   # Onyx Admin UI → Connectors → Sync-Status
   # Fehlgeschlagene Index-Attempts sollten sich selbst wiederholen
   ```

**Eskalation:** Bei Celery-Task-Verlust fuer kritische Tasks (nicht Indexierung) → Niko sofort informieren.

---

## Alert: RedisCacheHitRateLow

**Severity:** warning
**Environment:** DEV/TEST/PROD
**Bedeutung:** Redis Cache Hit Rate unter 80%. PROD: Nur bei genuegend Traffic (>50 ops/sec). Niedrige Hit-Rate = Redis wird als Datenbank statt Cache benutzt, oder Cache-Warming fehlt.

**Diagnose:**
```bash
# Prometheus Query (Grafana):
# rate(redis_keyspace_hits_total[5m]) / (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m]))

# Ist das System normal ausgelastet? (Traffic hoch genug fuer sinnvolle Hit-Rate)
# rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m])  → Gesamtoperationen
```

**Lösung:**
1. Neues Deployment / Restart? → Cache wird neu aufgebaut, Hit-Rate erholt sich.
2. DEV/TEST: Bei wenig Traffic ist eine niedrige Hit-Rate normal und erwartet.
3. Wenn Hit-Rate dauerhaft <50% bei normalem Traffic → Onyx Cache-Konfiguration pruefen.
4. Kein direktes Incident-Potenzial — eher Performance-Optimierung.

**Eskalation:** Kein Eskalations-SLA. Nur relevant wenn kombiniert mit Latenz-Problemen.

---

## Alert: RedisRejectedConnections

**Severity:** critical
**Environment:** DEV/TEST/PROD
**Bedeutung:** Redis lehnt neue Connections ab. Ursache: `maxclients` Limit erreicht. Celery-Worker verlieren Verbindung — Tasks koennen nicht gepickt werden.

**Diagnose:**
```bash
# Prometheus Query:
# increase(redis_rejected_connections_total[5m])

# Redis Connected Clients:
# redis_connected_clients  → aktuell verbundene Clients

# Celery-Worker-Logs:
kubectl logs -n onyx-dev -l app.kubernetes.io/name=celery --tail=50 | grep -E "connection|refused|timeout"

# PROD:
KUBECONFIG=~/.kube/config-prod kubectl logs -n onyx-prod -l app.kubernetes.io/name=celery --tail=50
```

**Lösung:**
1. Sofortmassnahme: Celery-Worker neustarten (gibt Connections frei):
   ```bash
   kubectl rollout restart deployment -n onyx-dev -l app.kubernetes.io/name=celery
   # PROD:
   KUBECONFIG=~/.kube/config-prod kubectl rollout restart deployment -n onyx-prod -l app.kubernetes.io/name=celery
   ```
2. `maxclients` in Redis-Konfiguration erhoehen (Helm Values, Redis Operator).
3. Zu viele Celery-Worker fuer einen Redis-Node? Worker-Anzahl reduzieren oder Redis-Cluster.
4. Connection-Leaks? Worker-Logs auf nicht-geschlossene Connections pruefen.

**Eskalation:** PROD: Sofort. Celery-Ausfall = kein Indexing, keine Hintergrundverarbeitung.

---

## Alert: PGCacheHitRateLow

**Severity:** warning
**Environment:** DEV/TEST/PROD
**Bedeutung:** PostgreSQL Cache Hit Ratio unter 90%. Das bedeutet, Daten werden haeufiger von Disk als aus dem Shared-Buffer-Cache gelesen. Indikator fuer zu kleinen `shared_buffers`.

**Diagnose:**
```bash
# Prometheus Query (Grafana):
# rate(pg_stat_database_blks_hit{datname="onyx"}[5m]) / (rate(pg_stat_database_blks_hit{datname="onyx"}[5m]) + rate(pg_stat_database_blks_read{datname="onyx"}[5m]))

# Aktuelle Konfiguration pruefen (PG Exporter Metrics):
kubectl port-forward -n monitoring svc/postgres-exporter-dev 9187:9187
curl -s http://localhost:9187/metrics | grep "pg_settings_shared_buffers_bytes"
```

**Lösung:**
1. Auf DEV/TEST bei wenig Traffic normal — der Working Set passt in den Cache.
2. PROD bei echtem Traffic: `shared_buffers` auf StackIT PG Flex anpassen (StackIT-seitig konfiguriert, Terraform-Parameter).
3. Grosse Tabellen-Scans koennen Cache-Hit-Rate temporaer senken (z.B. Indexierung grosser Mengen Dokumente).
4. Kein Sofort-Handlungsbedarf, aber Performance-Degradation bei anhaltendem Alert.

**Eskalation:** Kein Eskalations-SLA. Kombiniert mit hoher Latenz → Niko informieren.

---

## Alert: PGBackupCheckFailed

**Severity:** critical
**Environment:** PROD (nur)
**Bedeutung:** Der `pg-backup-check` CronJob in Namespace `monitoring` ist fehlgeschlagen. Das letzte erfolgreiche Backup koennte aelter als 26 Stunden sein. Backup-Integritaet unbekannt.

**Diagnose:**
```bash
KUBECONFIG=~/.kube/config-prod kubectl get jobs -n monitoring | grep pg-backup-check
KUBECONFIG=~/.kube/config-prod kubectl logs -n monitoring job/<job-name> | tail -30

# CronJob Status:
KUBECONFIG=~/.kube/config-prod kubectl get cronjob pg-backup-check -n monitoring
KUBECONFIG=~/.kube/config-prod kubectl describe cronjob pg-backup-check -n monitoring

# Direkte StackIT API-Pruefung:
# stackit postgresql backup list --project-id <PROJECT_ID> --instance-id <INSTANCE_ID>
# stackit postgresql backup list --project-id <PROJECT_ID> --instance-id <INSTANCE_ID> --format json | jq '.[0]'
```

**Lösung:**
1. **Auth-Fehler:** Service Account Token abgelaufen? Secret `stackit-backup-check-sa` in `monitoring` pruefen.
2. **Backup zu alt (>26h):** StackIT-Portal pruefen (`postgres.stackit.cloud`). Backup-Fenster: 01:00 UTC. Hat das Backup-Fenster getriggert?
3. **StackIT API nicht erreichbar:** NetworkPolicy `09-allow-backup-check-egress.yaml` anwenden?
   ```bash
   KUBECONFIG=~/.kube/config-prod kubectl get networkpolicy allow-backup-check-egress -n monitoring
   ```
4. **CronJob selbst defekt:** CronJob neu erstellen:
   ```bash
   KUBECONFIG=~/.kube/config-prod kubectl delete cronjob pg-backup-check -n monitoring
   KUBECONFIG=~/.kube/config-prod kubectl apply -f deployment/k8s/monitoring-exporters/pg-backup-check-prod.yaml
   ```

**Eskalation:** Sofort wenn Backup >26h alt. Niko informieren, VÖB ueber potenziellen Backup-Gap informieren. Details: `docs/runbooks/stackit-postgresql.md#pgbackupcheckfailed-alert`.

---

## Alert: PGBackupCheckNotScheduled

**Severity:** warning
**Environment:** PROD (nur)
**Bedeutung:** Der `pg-backup-check` CronJob wurde seit mehr als 6 Stunden nicht gescheduled. Moegliche Ursachen: CronJob suspended, K8s-Problem, Namespace-Problem.

**Diagnose:**
```bash
KUBECONFIG=~/.kube/config-prod kubectl get cronjob pg-backup-check -n monitoring -o yaml | grep -E "suspend|schedule|lastScheduleTime"

KUBECONFIG=~/.kube/config-prod kubectl describe cronjob pg-backup-check -n monitoring

# Prometheus Query:
# time() - kube_cronjob_status_last_schedule_time{namespace="monitoring", cronjob="pg-backup-check"}
```

**Lösung:**
1. CronJob suspended?
   ```bash
   KUBECONFIG=~/.kube/config-prod kubectl patch cronjob pg-backup-check -n monitoring -p '{"spec":{"suspend":false}}'
   ```
2. K8s-Scheduler-Problem? (unwahrscheinlich bei StackIT Managed K8s)
3. Namespace `monitoring` in Ordnung?
   ```bash
   KUBECONFIG=~/.kube/config-prod kubectl get pods -n monitoring
   ```
4. Manuellen Job-Run triggern:
   ```bash
   KUBECONFIG=~/.kube/config-prod kubectl create job --from=cronjob/pg-backup-check manual-backup-check -n monitoring
   KUBECONFIG=~/.kube/config-prod kubectl logs -n monitoring job/manual-backup-check
   ```

**Eskalation:** Wenn CronJob seit >24h nicht gelaufen und kein Backup verifiziert → kritisch, Niko informieren.

---

*Dieses Runbook wird aktualisiert wenn neue Alerts hinzugefuegt werden oder sich Diagnose-Verfahren aendern.*
*Letzte Aktualisierung: 2026-03-22 (COFFEESTUDIOS)*
*Referenz: `docs/referenz/monitoring-konzept.md`*
