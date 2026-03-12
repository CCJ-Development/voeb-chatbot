# Modulspezifikation: Monitoring Exporter (postgres_exporter + redis_exporter)

> **Status:** v1.0 — Deployed (DEV+TEST 2026-03-10, PROD 2026-03-12). PROD mit erhoehten CPU-Limits
> **Typ:** Infrastruktur (kein ext/-Code, kein Feature Flag)
> **Aufwand:** ~0,5 PT (Puffer: 0,75 PT bei PG-ACL-Debugging)
> **Prioritaet:** Hoch — schliesst groesste Luecke im Monitoring-Stack
> **Abhaengigkeit:** kube-prometheus-stack (deployed 2026-03-10)
> **Feature-Branch:** `feature/monitoring-exporter`
> **Compliance:** Schliesst BSI OPS.1.1.5 + BAIT Kap. 5 Luecke (DB-Monitoring)

---

## 1. Uebersicht

### Zweck

Der bestehende Monitoring-Stack (Prometheus, Grafana, AlertManager) ueberwacht Kubernetes-Infrastruktur und die Onyx API. **PostgreSQL und Redis sind komplett blind** — wir sehen nur den DB Connection Pool von der Onyx-Seite (Application-Level), aber nicht was in der Datenbank oder im Cache passiert.

Dieses Modul ergaenzt zwei Exporter:
1. **postgres_exporter** — exponiert PostgreSQL-interne Metriken (Connections, Transactions, Table Bloat, Replication)
2. **redis_exporter** — exponiert Redis-interne Metriken (Memory, Hit/Miss Rate, Clients, Evictions)

### Was es NICHT ist

- Kein ext/-Modul (kein Python/TypeScript Code)
- Kein Feature Flag (Exporter laufen immer wenn deployed)
- Keine Core-Datei-Aenderungen
- Keine Alembic-Migrationen
- Keine API-Endpoints

### Betroffene Rollen

| Rolle | Nutzen |
|-------|--------|
| Ops / Tech Lead | DB- und Cache-Performance auf einen Blick, Alerting bei Problemen |
| VoeB IT (spaeter) | Nachweis Datenbankueberwachung (BSI OPS.1.1.5, BAIT Kap. 5) |

---

## 2. Architektur

### Ist-Zustand (ohne Exporter)

```
Prometheus ──scrape──> Onyx API :8080/metrics
                       (HTTP Requests, Latenz, DB Pool)

PostgreSQL (StackIT Managed)  ← keine Metriken
Redis (In-Cluster)            ← keine Metriken
```

### Soll-Zustand (mit Exporter)

```
Prometheus ──scrape──> Onyx API :8080/metrics
           ──scrape──> postgres_exporter :9187/metrics  ──connect──> PG DEV :5432
           ──scrape──> postgres_exporter :9187/metrics  ──connect──> PG TEST :5432
           ──scrape──> redis_exporter :9121/metrics     ──connect──> Redis DEV :6379
           ──scrape──> redis_exporter :9121/metrics     ──connect──> Redis TEST :6379
```

### Deployment-Topologie

| Komponente | Namespace | Typ | Replicas | Labels |
|------------|-----------|-----|----------|--------|
| postgres_exporter DEV | `monitoring` | Deployment | 1 | `app: postgres-exporter, environment: dev` |
| postgres_exporter TEST | `monitoring` | Deployment | 1 | `app: postgres-exporter, environment: test` |
| redis_exporter DEV | `monitoring` | Deployment | 1 | `app: redis-exporter, environment: dev` |
| redis_exporter TEST | `monitoring` | Deployment | 1 | `app: redis-exporter, environment: test` |
| postgres_exporter PROD | `monitoring` | Deployment | 1 | `app: postgres-exporter, environment: prod` |
| redis_exporter PROD | `monitoring` | Deployment | 1 | `app: redis-exporter, environment: prod` |

**Warum im `monitoring`-Namespace?** Alle Monitoring-Komponenten zentral. NetworkPolicies erlauben Egress zu `onyx-dev`, `onyx-test` und `onyx-prod`. Exporter brauchen nur zusaetzlichen Egress zu den PG-Hosts und Redis-Services.

---

## 3. PostgreSQL Exporter

### 3.1 Verbindungsdetails

| Env | Host | Port | DB | User |
|-----|------|------|----|------|
| DEV | `be7fe911-4eac-4c9d-a7a8-6dfff674c41f.postgresql.eu01.onstackit.cloud` | 5432 | onyx | `db_readonly_user` |
| TEST | `d371f38d-2ad5-458c-af27-c84f3004f1ba.postgresql.eu01.onstackit.cloud` | 5432 | onyx | `db_readonly_user` |

**WICHTIG — pg_monitor-Rolle erforderlich:**

`db_readonly_user` hat aktuell nur die `login`-Rolle (Terraform: `roles = ["login"]`). Fuer den postgres_exporter ist `pg_monitor` noetig, da sonst:
- `pg_stat_activity` nur die eigene Session zeigt (nicht die Onyx-Connections)
- `PGConnectionsHigh` Alert waere nutzlos (zeigt immer nur 1 Connection)
- `pg_stat_user_tables` eingeschraenkt sichtbar ist

**Ergebnis Recherche (2026-03-10):**
StackIT PG Flex unterstuetzt nur `login` + `createdb` als Terraform-Rollen. `pg_monitor` ist ein PostgreSQL predefined Role (GRANT via SQL), nicht ueber die StackIT API verfuegbar. Managed PG erlaubt kein CREATEROLE → GRANT nicht moeglich.

**Workaround:** `pg_stat_database_numbackends` statt `pg_stat_activity_count` fuer Connection-Monitoring. Braucht kein pg_monitor und ist zuverlaessig. `PGConnectionsHigh` Alert nutzt `numbackends`. Spaeter: StackIT Support kontaktieren fuer pg_monitor (Nice-to-have, nicht Blocker).

**Passwort:** Bereits als K8s Secret vorhanden (`onyx-dbreadonly` in `onyx-dev`/`onyx-test`). Muss als Secret im `monitoring`-Namespace gespiegelt werden.

### 3.2 Exponierte Metriken (Auswahl)

| Metrik | Beschreibung | Warum relevant |
|--------|-------------|---------------|
| `pg_stat_activity_count` | Aktive Connections nach State | Naehern wir uns `max_connections`? |
| `pg_stat_database_numbackends` | Aktive Backends pro DB | Zuverlaessiger als `pg_stat_activity_count` |
| `pg_stat_database_tup_fetched` | Rows gelesen pro Sekunde | Last-Profil |
| `pg_stat_database_tup_inserted/updated/deleted` | Write-Last | Indexierung aktiv? |
| `pg_stat_database_xact_commit` | Commits/s | Transaction-Rate |
| `pg_stat_database_xact_rollback` | Rollbacks/s | Fehlerrate |
| `pg_stat_database_deadlocks` | Deadlocks | Concurrency-Probleme |
| `pg_stat_database_blks_hit` / `blks_read` | Cache Hit Ratio | PG Shared Buffers effektiv? |
| `pg_stat_user_tables_n_dead_tup` | Dead Tuples pro Tabelle | Braucht die DB VACUUM? |
| `pg_database_size_bytes` | DB-Groesse | Wachstum tracken |
| `pg_locks_count` | Locks nach Mode | Lock-Contention identifizieren |
| `pg_replication_lag_seconds` | Replication Lag (falls Replicas) | Datenaktualitaet |

**Hinweis:** `pg_replication_lag_seconds` existiert nur wenn StackIT Replicas konfiguriert hat. Falls nicht, ist die Metrik einfach nicht vorhanden (kein Fehler).

### 3.3 Image + Ressourcen

| Feld | Wert |
|------|------|
| Image | `quay.io/prometheuscommunity/postgres-exporter:v0.19.1` |
| Port | 9187 |
| CPU Request | 50m (PROD: 100m) |
| CPU Limit | 100m (PROD: 250m) |
| RAM Request | 64Mi |
| RAM Limit | 128Mi |

**Ressourcen-Impact (3x Exporter):** +200m CPU Request, +192Mi RAM Request. PROD erhoehte Limits wegen CPUThrottlingHigh (2026-03-12).

### 3.4 Konfiguration

```yaml
# Environment Variables (pro Exporter-Deployment)
DATA_SOURCE_NAME: "postgresql://db_readonly_user:<PASSWORD>@<PG_HOST>:5432/onyx?sslmode=require"
```

**Hinweis:** StackIT PG Flex erzwingt TLS (`sslmode=require`). Kein Client-Zertifikat noetig.

### 3.5 Security Context

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 65534        # nobody
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
```

---

## 4. Redis Exporter

### 4.1 Verbindungsdetails

| Env | Service | Port | Auth |
|-----|---------|------|------|
| DEV | `onyx-dev.onyx-dev.svc.cluster.local` | 6379 | Separate Env-Vars (siehe 4.4) |
| TEST | `onyx-test.onyx-test.svc.cluster.local` | 6379 | Separate Env-Vars (siehe 4.4) |

**Kein externer Zugriff noetig** — Redis ist In-Cluster.

### 4.2 Exponierte Metriken (Auswahl)

| Metrik | Beschreibung | Warum relevant |
|--------|-------------|---------------|
| `redis_memory_used_bytes` | RAM-Verbrauch | OOM-Risiko |
| `redis_memory_max_bytes` | maxmemory-Limit | Wie nah am Limit? |
| `redis_keyspace_hits_total` / `misses_total` | Cache Hit/Miss Rate (Counter) | Cache-Effizienz |
| `redis_connected_clients` | Aktive Clients | Last |
| `redis_config_maxclients` | Max Clients Limit | Connection-Utilization |
| `redis_evicted_keys_total` | Evicted Keys | Cache-Druck |
| `redis_rejected_connections_total` | Abgewiesene Connections | Kritisch fuer Celery |
| `redis_commands_total` | Commands/s | Throughput |
| `redis_blocked_clients` | Blockierte Clients | BLPOP/BRPOP (Celery) |
| `redis_instantaneous_ops_per_sec` | Aktuelle Ops/s | Live-Last |

### 4.3 Image + Ressourcen

| Feld | Wert |
|------|------|
| Image | `oliver006/redis_exporter:v1.82.0` |
| Port | 9121 |
| CPU Request | 25m (PROD: 50m) |
| CPU Limit | 50m (PROD: 150m) |
| RAM Request | 32Mi |
| RAM Limit | 64Mi |

**Ressourcen-Impact (3x Exporter):** +100m CPU Request, +96Mi RAM Request. PROD erhoehte Limits wegen CPUThrottlingHigh (2026-03-12).

### 4.4 Konfiguration

```yaml
# Getrennte Env-Vars (Passwort NICHT in URL — Security Best Practice)
REDIS_ADDR: "onyx-dev.onyx-dev.svc.cluster.local:6379"   # bzw. onyx-test
REDIS_PASSWORD: "<PW>"                                     # aus Secret
```

**Warum getrennt statt `redis://:<PW>@host`?** Falls `REDIS_ADDR` in Logs/Events auftaucht, ist kein Passwort exponiert.

### 4.5 Security Context

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 65534        # nobody
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
```

**PROD-Hardening:** Dedizierter Redis-ACL-User mit eingeschraenkten Commands (`+info +config|get +slowlog|get +dbsize +client|list +latency|latest`). Fuer DEV/TEST nicht noetig (operationelle Einfachheit).

---

## 5. Prometheus Scrape-Konfiguration

Ergaenzung in `values-monitoring.yaml` unter `additionalScrapeConfigs`:

```yaml
# PostgreSQL Exporter
- job_name: "postgres-dev"
  metrics_path: "/metrics"
  scrape_interval: "30s"
  scrape_timeout: "15s"       # Extern — Netzwerk-Latenz moeglich
  static_configs:
    - targets: ["postgres-exporter-dev.monitoring.svc.cluster.local:9187"]
      labels:
        environment: "dev"
        service: "postgresql"

- job_name: "postgres-test"
  metrics_path: "/metrics"
  scrape_interval: "30s"
  scrape_timeout: "15s"
  static_configs:
    - targets: ["postgres-exporter-test.monitoring.svc.cluster.local:9187"]
      labels:
        environment: "test"
        service: "postgresql"

# Redis Exporter
- job_name: "redis-dev"
  metrics_path: "/metrics"
  scrape_interval: "30s"
  static_configs:
    - targets: ["redis-exporter-dev.monitoring.svc.cluster.local:9121"]
      labels:
        environment: "dev"
        service: "redis"

- job_name: "redis-test"
  metrics_path: "/metrics"
  scrape_interval: "30s"
  static_configs:
    - targets: ["redis-exporter-test.monitoring.svc.cluster.local:9121"]
      labels:
        environment: "test"
        service: "redis"
```

---

## 6. Alert-Rules (Ergaenzung)

Neue Regeln in `additionalPrometheusRulesMap`. Alle mit `annotations` (konsistent mit bestehenden 9 Regeln):

### 6.1 Exporter-Health (Critical)

| Alert | PromQL | for | Severity |
|-------|--------|-----|----------|
| `PGExporterDown` | `up{job=~"postgres-.*"} == 0` | 2m | critical |
| `RedisExporterDown` | `up{job=~"redis-.*"} == 0` | 2m | critical |

### 6.2 PostgreSQL

| Alert | PromQL | for | Severity |
|-------|--------|-----|----------|
| `PGConnectionsHigh` | `sum by (job,server)(pg_stat_database_numbackends{datname="onyx"}) > on(job,server) pg_settings_max_connections * 0.8` | 5m | warning |
| `PGDeadlocks` | `increase(pg_stat_database_deadlocks{datname="onyx"}[5m]) > 5` | 5m | warning |
| `PGHighRollbackRate` | `rate(pg_stat_database_xact_rollback{datname="onyx"}[5m]) / (rate(pg_stat_database_xact_rollback{datname="onyx"}[5m]) + rate(pg_stat_database_xact_commit{datname="onyx"}[5m])) > 0.05` | 10m | warning |
| `PGDatabaseGrowing` | `pg_database_size_bytes{datname="onyx"} > 10e9` | 30m | warning |

**Korrekturen gegenueber v0.1:**
- `PGDeadlocks`: `> 0` → `> 5`, `for: 1m` → `5m` (vermeidet Alarm-Fatigue bei Celery)
- `PGHighRollbackRate`: `rollback / commit` → `rollback / (rollback + commit)` (verhindert Division-by-Zero)
- `PGDatabaseGrowing`: `> 5e9` → `> 10e9`, `for: 1h` → `30m`, `datname="onyx"` Filter (realistischer Schwellwert)

### 6.3 Redis

| Alert | PromQL | for | Severity |
|-------|--------|-----|----------|
| `RedisMemoryHigh` | `redis_memory_used_bytes / redis_memory_max_bytes > 0.8 and on(instance) redis_memory_max_bytes > 0` | 5m | warning |
| `RedisHighEvictions` | `increase(redis_evicted_keys_total[5m]) > 100` | 5m | warning |
| `RedisCacheHitRateLow` | `rate(redis_keyspace_hits_total[5m]) / (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m])) < 0.8` | 10m | warning |
| `RedisRejectedConnections` | `increase(redis_rejected_connections_total[5m]) > 0` | 1m | critical |

**Korrekturen gegenueber v0.1:**
- `RedisMemoryHigh`: Guard-Clause `and on(instance) redis_memory_max_bytes > 0` (verhindert Division-by-Zero wenn maxmemory nicht gesetzt)
- `RedisCacheHitRateLow`: `rate()` statt rohe Counter (zeigt aktuelle Rate, nicht Lifetime-Durchschnitt). Schwellwert 0.9 → 0.8 (Redis ist primaer Celery-Broker, nicht Cache — niedrigere Hit Rate normal)
- `RedisRejectedConnections`: NEU — kritisch fuer Celery-Betrieb

**Hinweis:** Alle Alerts nutzen den bestehenden AlertManager-Kanal (`teams-niko`). Teams Webhook-URL konfiguriert (2026-03-11), Alerts werden an den Teams-Kanal zugestellt inkl. Entwarnung (`send_resolved: true`).

---

## 7. NetworkPolicy-Aenderungen

### 7.1 Monitoring-Namespace: Egress zu PostgreSQL (NEU)

postgres_exporter braucht Egress zum StackIT PG Flex (extern). Egress auf Port 5432 ohne Ziel-Einschraenkung, da StackIT PG-IPs sich bei Maintenance aendern koennen:

```yaml
# deployment/k8s/network-policies/monitoring/06-allow-pg-exporter-egress.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-pg-exporter-egress
  namespace: monitoring
spec:
  podSelector:
    matchLabels:
      app: postgres-exporter
  policyTypes: [Egress]
  egress:
    # Ziel bewusst nicht eingeschraenkt: StackIT PG Flex IPs koennen sich bei
    # Maintenance aendern. podSelector schraenkt auf Exporter-Pods ein.
    - ports:
        - port: 5432
          protocol: TCP
```

### 7.2 Monitoring-Namespace: Egress zu Redis (NEU)

redis_exporter braucht Egress zu den Redis-Services in `onyx-dev` und `onyx-test`, eingeschraenkt auf Redis-Pods:

```yaml
# deployment/k8s/network-policies/monitoring/07-allow-redis-exporter-egress.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-redis-exporter-egress
  namespace: monitoring
spec:
  podSelector:
    matchLabels:
      app: redis-exporter
  policyTypes: [Egress]
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: onyx-dev
          podSelector:
            matchLabels:
              redis_setup_type: standalone
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: onyx-test
          podSelector:
            matchLabels:
              redis_setup_type: standalone
      ports:
        - port: 6379
          protocol: TCP
```

**Hinweis:** Redis-Pod-Labels verifiziert (2026-03-10): `redis_setup_type: standalone` (konsistent auf DEV + TEST). `app.kubernetes.io/name` ist env-spezifisch (`onyx-dev` / `onyx-test`), daher nicht als Selector geeignet.

### 7.3 App-Namespaces: Ingress von redis_exporter (NEU)

Separate Policy (nicht bestehende 06 erweitern — Least Privilege):

```yaml
# deployment/k8s/network-policies/07-allow-redis-exporter-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-redis-exporter-ingress
  namespace: onyx-dev  # Analog fuer onyx-test
spec:
  podSelector:
    matchLabels:
      redis_setup_type: standalone
  policyTypes: [Ingress]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: monitoring
          podSelector:
            matchLabels:
              app: redis-exporter
      ports:
        - port: 6379
          protocol: TCP
```

### 7.4 Prometheus Scrape: Intra-Namespace (BEREITS VORHANDEN)

`04-allow-intra-namespace.yaml` erlaubt bereits Kommunikation innerhalb des `monitoring`-Namespace. Prometheus kann die Exporter auf Port 9187/9121 scrapen — keine Aenderung noetig.

### 7.5 apply.sh aktualisieren

`deployment/k8s/network-policies/monitoring/apply.sh` auf 7 Schritte erweitern (aktuell 5). Neue Policies 06 + 07 VOR `01-default-deny-all` applyen (Allow-first-Prinzip).

---

## 8. Secrets-Management

### Problem

Die Exporter laufen im `monitoring`-Namespace, aber die Credentials liegen in `onyx-dev`/`onyx-test`:

| Secret | Namespace | Benoetigt von |
|--------|-----------|---------------|
| `onyx-dbreadonly` (DB_READONLY_PASSWORD) | `onyx-dev`, `onyx-test` | postgres_exporter |
| `onyx-redis` (REDIS_PASSWORD) | `onyx-dev`, `onyx-test` | redis_exporter |

### Loesung: Dedizierte Secrets im monitoring-Namespace

Secrets per Datei erstellen (NICHT `--from-literal` — vermeidet Passwort in Shell-History):

```bash
# Passwoerter beschaffen
PG_DEV_PW=$(kubectl get secret onyx-dbreadonly -n onyx-dev -o jsonpath='{.data.db_readonly_password}' | base64 -d)
PG_TEST_PW=$(kubectl get secret onyx-dbreadonly -n onyx-test -o jsonpath='{.data.db_readonly_password}' | base64 -d)
REDIS_DEV_PW=$(kubectl get secret onyx-redis -n onyx-dev -o jsonpath='{.data.redis_password}' | base64 -d)
REDIS_TEST_PW=$(kubectl get secret onyx-redis -n onyx-test -o jsonpath='{.data.redis_password}' | base64 -d)

# PG Secrets (Connection String in Datei, nicht CLI)
echo -n "postgresql://db_readonly_user:${PG_DEV_PW}@be7fe911-4eac-4c9d-a7a8-6dfff674c41f.postgresql.eu01.onstackit.cloud:5432/onyx?sslmode=require" > /tmp/pg-dev-dsn.txt
kubectl create secret generic pg-exporter-dev -n monitoring --from-file=DATA_SOURCE_NAME=/tmp/pg-dev-dsn.txt
rm /tmp/pg-dev-dsn.txt

# Analog fuer TEST, Redis DEV, Redis TEST
# Redis: Getrennte Keys REDIS_ADDR + REDIS_PASSWORD
kubectl create secret generic redis-exporter-dev -n monitoring \
  --from-file=REDIS_ADDR=<(echo -n "onyx-dev.onyx-dev.svc.cluster.local:6379") \
  --from-file=REDIS_PASSWORD=<(echo -n "${REDIS_DEV_PW}")
```

**Warum keine Cross-Namespace Secret References?** Kubernetes erlaubt keine Cross-NS Secret-Mounts. Alternativen (ExternalSecrets, Replicator) waeren Overengineering fuer 4 Secrets.

**Passwort-Rotation:** Bei PG/Redis Passwort-Aenderung muessen Secrets in BEIDEN Namespaces aktualisiert werden (App-NS + monitoring). `PGExporterDown`/`RedisExporterDown` Alerts warnen bei Connection-Verlust.

---

## 9. Grafana Dashboards

### Standard-Dashboards (Import via ID)

| Dashboard | Grafana ID | Zeigt | Hinweis |
|-----------|-----------|-------|---------|
| PostgreSQL Exporter | **14114** | Connections, Transactions, Cache Hit Ratio, Locks, Tuple Activity | Kompatibel mit `prometheuscommunity/postgres-exporter`. Falls Panels leer: Fallback auf ID 9628. |
| Redis Dashboard | **763** | Memory, Hit/Miss Rate, Commands/s, Clients, Keys | Offizielles Dashboard von oliver006. |

### Custom Panels (zum bestehenden "Onyx API" Dashboard ergaenzen)

| Panel | PromQL |
|-------|--------|
| PG Active Connections | `sum by (state)(pg_stat_activity_count{environment="$env", datname="onyx"})` |
| PG Cache Hit Ratio | `rate(pg_stat_database_blks_hit{datname="onyx", environment="$env"}[5m]) / (rate(pg_stat_database_blks_hit{datname="onyx", environment="$env"}[5m]) + rate(pg_stat_database_blks_read{datname="onyx", environment="$env"}[5m]))` |
| PG DB Size | `pg_database_size_bytes{datname="onyx", environment="$env"}` |
| Redis Memory Usage | `redis_memory_used_bytes{environment="$env"}` |
| Redis Hit Rate | `rate(redis_keyspace_hits_total{environment="$env"}[5m]) / (rate(redis_keyspace_hits_total{environment="$env"}[5m]) + rate(redis_keyspace_misses_total{environment="$env"}[5m]))` |

**Korrekturen gegenueber v0.1:** Cache Hit Ratio + Redis Hit Rate nutzen jetzt `rate()` statt rohe Counter-Werte. PG Connections mit `sum by (state)` fuer Aufschluesselung (idle/active/waiting).

---

## 10. Implementierungsplan

### Reihenfolge (massgeblich)

| Schritt | Aktion | Dateien | Aufwand |
|---------|--------|---------|---------|
| 1 | **pg_monitor-Rolle pruefen** (Showstopper) | Manuell: `GRANT pg_monitor TO db_readonly_user` testen | 0,05 PT |
| 2 | Passwoerter aus bestehenden Secrets beschaffen | `kubectl get secret` (siehe Abschnitt 8) | 0,05 PT |
| 3 | Secrets im monitoring-NS erstellen | Manuell per kubectl (aus Datei) | 0,05 PT |
| 4 | K8s Manifeste erstellen (4 Deployments + 4 Services) | `deployment/k8s/monitoring-exporters/` | 0,1 PT |
| 5 | NetworkPolicies erstellen + apply (inkl. App-NS) | `monitoring/06-*.yaml`, `07-*.yaml`, App-NS `07-*.yaml` | 0,05 PT |
| 6 | `apply.sh` auf 7 Schritte erweitern | `monitoring/apply.sh` | 0,02 PT |
| 7 | Scrape-Configs + Alert-Rules in `values-monitoring.yaml` | `deployment/helm/values/values-monitoring.yaml` | 0,08 PT |
| 8 | `helm upgrade monitoring` + Verifizierung (Targets UP) | Manuell | 0,05 PT |
| 9 | Grafana Dashboards importieren (14114, 763) | Manuell via Grafana UI | 0,05 PT |
| 10 | Doku aktualisieren | `docs/referenz/monitoring-konzept.md` | 0,1 PT |
| **Gesamt** | | | **~0,6 PT** |

**Puffer:** 0,75 PT falls PG-ACL-Debugging oder Redis-Label-Verifizierung noetig.

---

## 11. PROD-Strategie

PROD = eigener Cluster (ADR-004). Identisches Setup, nur 2 statt 4 Exporter (je 1 PG + 1 Redis). Secret-Werte aendern sich (PROD PG Host, PROD Redis Service).

PROD-spezifische Haertung:
- Dedizierter Redis-ACL-User mit eingeschraenkten Commands
- PG Egress NetworkPolicy mit CIDR-Einschraenkung (PROD PG IP bekannt und stabil)
- Grafana Dashboards als ConfigMap (persistent ueber Helm Upgrades)

---

## 12. Risikobewertung

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|-----------|
| **pg_monitor fehlt** (eingeschraenkte Sichtbarkeit) | Hoch | Niedrig — Workaround `numbackends` | StackIT Support kontaktieren (Nice-to-have) |
| PG Exporter erhoecht DB-Last | Niedrig (1 Query/30s, Read-Only) | Niedrig | Read-Only User, keine Write-Rechte |
| Redis Exporter erhoecht Latenz | Sehr niedrig (INFO Command) | Vernachlaessigbar | Redis verarbeitet INFO in <1ms |
| Secret-Drift (Passwort aendert sich) | Niedrig | Mittel — Exporter verliert Verbindung | Alerts `PGExporterDown` / `RedisExporterDown` feuern sofort |
| StackIT PG ACL blockiert Exporter | Niedrig | Hoch — kein Connect | Cluster-Egress-IP `188.34.93.194` ist in ACL (verifiziert) |

---

## 13. Offene Fragen

| # | Frage | Wer | Status |
|---|-------|-----|--------|
| 1 | ~~StackIT PG ACL: Erlaubt die aktuelle ACL auch Cluster-interne Pod-IPs?~~ | Niko | ✅ **Beantwortet:** Pods nutzen Cluster-Egress-IP `188.34.93.194` (SNAT). Ist in ACL. Verifizierung beim Deploy. |
| 2 | ~~pg_monitor-Rolle: Kann `onyx_app` die Rolle delegieren?~~ | Niko | ✅ **Beantwortet:** StackIT PG Flex unterstuetzt nur login+createdb. Workaround: `numbackends` statt `activity_count`. Spaeter StackIT Support fuer pg_monitor (Nice-to-have). |
| 3 | Soll Vespa Exporter gleich mit deployed werden (+0,1 PT)? | Niko | Offen |
| 4 | Grafana Dashboards als ConfigMap (persistent) oder manueller Import (einfacher)? | Niko | Offen |

---

## 14. Freigabe

| Rolle | Name | Datum | Unterschrift |
|-------|------|-------|-------------|
| Tech Lead | Nikolaj Ivanov | | |

---

## Revisions-Historie

| Version | Datum | Autor | Aenderung |
|---------|-------|-------|-----------|
| 0.1 | 2026-03-10 | Claude (CCJ) | Erster Entwurf |
| 0.2 | 2026-03-10 | Claude (CCJ) | Review-Findings eingearbeitet: Image-Versionen aktualisiert (H2), pg_monitor-Risiko dokumentiert (H1), PromQL-Bugs behoben (M1-M4), fehlende Alerts ergaenzt (M5), securityContext ergaenzt (M6), NetworkPolicies verschaerft (M7-M8), Redis-Credentials getrennt (M9), apply.sh + App-NS-Policy im Plan ergaenzt (M10-M11), PG ACL beantwortet (L1), scrape_timeout ergaenzt (L2), Dashboard-ID 9628→14114 (L3), PG Schwellwert angepasst (L4), Implementierungsreihenfolge korrigiert (L5), SMTP-Hinweis ergaenzt (L6), Passwort-Beschaffung dokumentiert (L8) |
| 0.3 | 2026-03-10 | Claude (CCJ) | Implementierung: Redis-Labels korrigiert (`redis_setup_type: standalone` statt `app.kubernetes.io/name: redis`), pg_monitor-Recherche abgeschlossen (StackIT unterstuetzt nur login+createdb), PGConnectionsHigh auf `numbackends` umgestellt, H1 von Showstopper zu Nice-to-have heruntergestuft |
