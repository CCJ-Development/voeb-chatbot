# Runbook: Helm Deploy — Betriebswissen

**Zuletzt verifiziert:** 2026-03-19
**Ausgeführt von:** Nikolaj Ivanov

---

## Zweck

**Wann dieses Runbook verwenden:**
- Manuelles Helm-Deployment oder -Update durchfuehren (ausserhalb der CI/CD Pipeline)
- Helm-Konfiguration aendern (Values, Secrets) und anwenden
- Deployment-Probleme debuggen (Pod-Fehler, Readiness, Rollout-Deadlock)

**Zielgruppe:** DevOps / Tech Lead

**Voraussetzungen:**
- SKE Cluster laeuft (`kubectl get nodes` zeigt Ready)
- `helm` und `kubectl` installiert, Kubeconfig gueltig
- Namespace mit Image Pull Secret existiert

**Geschaetzte Dauer:** 20-45 Min (Deploy + Validierung)

---

## Voraussetzungen

- SKE Cluster läuft (`kubectl get nodes` → Ready)
- Namespace `onyx-dev` existiert mit Image Pull Secret
- PostgreSQL Flex: Datenbank `onyx` existiert (siehe [PostgreSQL Runbook](./stackit-postgresql.md))
- Object Storage: Credentials erstellt (siehe unten)
- Redis Operator installiert (im `default` Namespace, verwaltet Redis-Pods in allen Namespaces):
  ```bash
  helm install redis ot-helm/redis-operator --namespace default
  ```

---

## Deploy-Befehl

**WICHTIG:** IMMER `values-{env}-secrets.yaml` mit angeben! Ohne diese Datei werden PG, Redis, S3 Credentials auf leere Strings gesetzt und alle Pods crashen.

**PROD nutzt ein separates Kubeconfig:** `~/.kube/config-prod` (Cluster `vob-prod`, Ablauf 2026-06-09). DEV/TEST: `~/.kube/config` (Cluster `vob-chatbot`, Ablauf 2026-05-28).

### Erwartete Pod-Counts

| Environment | Pods | Hinweis |
|-------------|------|---------|
| DEV | 17 | 1x API, 1x Web, 8 Celery-Worker, Vespa (Zombie), OpenSearch, Redis, 2x Model, NGINX |
| TEST | 16 | 1x API, 1x Web, 8 Celery-Worker, Vespa (Zombie), OpenSearch, Redis, Model, NGINX |
| PROD | 20 | 2x API HA, 2x Web HA, 8 Celery-Worker, Vespa (Zombie), OpenSearch, Redis, 2x Model, NGINX |

> **Vespa (Zombie-Mode):** Vespa laeuft mit minimalen Ressourcen (50m/512Mi DEV, 100m/512Mi PROD). Der Pod wird NUR fuer den v3.x Readiness Check benoetigt (`wait_for_vespa_or_shutdown`). Kein aktiver Index-Traffic. Wird in v4.0.0 entfernt.
>
> **OpenSearch:** Primaeres Document Index Backend seit v3.0.0 (Upstream-Default). Ersetzt Vespa fuer Indexing und Retrieval.

### DEV

```bash
export KUBECONFIG=~/.kube/config
helm upgrade --install onyx-dev \
  deployment/helm/charts/onyx \
  --namespace onyx-dev \
  -f deployment/helm/values/values-common.yaml \
  -f deployment/helm/values/values-dev.yaml \
  -f deployment/helm/values/values-dev-secrets.yaml \
  --wait --timeout 15m
```

### TEST

```bash
export KUBECONFIG=~/.kube/config
helm upgrade --install onyx-test \
  deployment/helm/charts/onyx \
  --namespace onyx-test \
  -f deployment/helm/values/values-common.yaml \
  -f deployment/helm/values/values-test.yaml \
  -f deployment/helm/values/values-test-secrets.yaml \
  --wait --timeout 15m
```

### PROD (eigener Cluster!)

**Hinweis:** PROD wird regulaer ueber CI/CD deployed (`gh workflow run stackit-deploy.yml -f environment=prod`). Secrets werden dort aus GitHub Environment Secrets injiziert (`--set`). Fuer manuellen Deploy muss `values-prod-secrets.yaml` lokal erstellt werden (analog `values-dev-secrets.yaml`).

```bash
export KUBECONFIG=~/.kube/config-prod

# Option 1: Manueller Deploy mit lokaler Secrets-Datei
# → values-prod-secrets.yaml muss erst erstellt werden (siehe "Secrets-Datei erstellen" unten)
helm upgrade --install onyx-prod \
  deployment/helm/charts/onyx \
  --namespace onyx-prod \
  -f deployment/helm/values/values-common.yaml \
  -f deployment/helm/values/values-prod.yaml \
  -f deployment/helm/values/values-prod-secrets.yaml \
  --wait --timeout 15m

# Option 2: CI/CD (empfohlen)
gh workflow run stackit-deploy.yml -f environment=prod -R CCJ-Development/voeb-chatbot
```

Die `values-{env}-secrets.yaml` Dateien sind gitignored und enthalten:
- PostgreSQL Passwort
- Object Storage Credentials (S3 Access Key / Secret Key)
- DB Readonly Password
- Redis Passwort

---

## Object Storage Credentials anlegen

Credentials werden über die StackIT CLI erstellt (nicht über Terraform):

```bash
# Credentials-Gruppe anzeigen
stackit object-storage credentials-group list --project-id <PROJECT_ID>

# Credentials erstellen (Bestätigung mit "y")
echo "y" | stackit object-storage credentials create \
  --project-id <PROJECT_ID> \
  --credentials-group-id <GROUP_ID>
```

Ausgabe enthält `Access Key ID` und `Secret Access Key`. Diese in `values-dev-secrets.yaml` eintragen:

```yaml
auth:
  objectstorage:
    values:
      s3_aws_access_key_id: "<ACCESS_KEY>"
      s3_aws_secret_access_key: "<SECRET_KEY>"
```

---

## Redis: Service-Name Mismatch

Der Onyx Helm Chart generiert `REDIS_HOST: <release>-master` (Bitnami-Konvention). Der OT Container Kit Redis Operator erstellt den Service aber als `<release>` (ohne `-master`).

**Lösung:** `REDIS_HOST` explizit in `values-dev.yaml` überschreiben:

```yaml
configMap:
  REDIS_HOST: "onyx-dev"
```

**Validierung:**
```bash
# DNS prüfen (muss auflösen)
kubectl run dns-test --rm -it --restart=Never --namespace onyx-dev \
  --image=busybox -- nslookup onyx-dev.onyx-dev.svc.cluster.local

# Darf NICHT auflösen (das ist der falsche Name)
kubectl run dns-test2 --rm -it --restart=Never --namespace onyx-dev \
  --image=busybox -- nslookup onyx-dev-master.onyx-dev.svc.cluster.local
```

---

## Rolling Update Deadlock (1-Node Cluster)

### Problem

Bei `helm upgrade` erstellt Kubernetes neue ReplicaSets (Rolling Update). Auf einem 1-Node Cluster mit knappem CPU-Budget können die neuen Pods nicht schedulen, weil die alten noch laufen. Ergebnis: Deadlock — alte Pods warten auf neue, neue können nicht starten.

### Erkennung

```bash
kubectl get pods -n onyx-dev
# Symptom: Neue Pods "Pending", alte Pods "Running"
# kubectl describe pod <pending-pod> → "Insufficient cpu"
```

### Sofort-Lösung

Alte ReplicaSets manuell auf 0 skalieren:

```bash
# Alte RS identifizieren (READY > 0, aber nicht die neueste)
kubectl get rs -n onyx-dev

# Beispiel: Alte RS runterskalieren
kubectl scale rs <old-rs-name> --replicas=0 -n onyx-dev
```

### Aktuell aktiv (alle Environments)

Recreate-Strategie wird automatisch per `kubectl patch` nach jedem `helm upgrade` gesetzt (CI/CD Workflow). Akzeptabel fuer alle Environments (kein Zero-Downtime-Requirement).

---

## AUTH_TYPE Deprecation

`AUTH_TYPE=disabled` wird ab dieser Chart-Version nicht mehr unterstützt. Onyx fällt automatisch auf `basic` zurück (Email/Passwort-Login).

**Empfehlung:** In `values-dev.yaml` explizit setzen:
```yaml
configMap:
  AUTH_TYPE: "basic"
```

Für Phase 3 (Entra ID): `AUTH_TYPE: "oidc"`.

---

## Startup-Reihenfolge

Onyx-Pods haben interne Readiness-Probes die auf andere Services warten:

1. **PostgreSQL** (extern) — muss erreichbar sein
2. **Redis** — celery-beat und celery-worker warten darauf
3. **Vespa** — celery-worker wartet auf Port 8081 (Vespa braucht ~2-5 Min zum Starten, laenger bei reduzierten Ressourcen im Zombie-Mode)
4. **OpenSearch** — wenn `ENABLE_OPENSEARCH_INDEXING_FOR_ONYX=true`: celery-worker wartet zusaetzlich auf Port 9200
5. **api-server** — führt `alembic upgrade head` aus, dann startet Uvicorn. Deployed das Vespa Application Package.

Bei erstmaligem Deploy dauert der api-server-Start länger (viele Alembic-Migrationen). Kann 1-2 Restarts verursachen wenn die Startup-Probe zu kurz ist.

---

## Validierung nach Deploy

```bash
# Alle Pods 1/1 Running
kubectl get pods -n onyx-{env}

# API Health
# DEV:  curl -s https://dev.chatbot.voeb-service.de/api/health
# TEST: curl -s https://test.chatbot.voeb-service.de/api/health
# PROD: curl -s https://chatbot.voeb-service.de/api/health
# Erwartete Ausgabe: {"success":true,"message":"ok","data":null}

# Login-Seite
# DEV:  curl -s -o /dev/null -w "%{http_code}" https://dev.chatbot.voeb-service.de/auth/login
# TEST: curl -s -o /dev/null -w "%{http_code}" https://test.chatbot.voeb-service.de/auth/login
# PROD: curl -s -o /dev/null -w "%{http_code}" https://chatbot.voeb-service.de/auth/login
# Erwartete Ausgabe: 200 (oder 307 redirect zu login)
```

---

## Domain / Cookie-Konfiguration

Onyx setzt `cookie_secure` basierend auf `WEB_DOMAIN`:

```python
# backend/onyx/auth/users.py:991
cookie_secure=WEB_DOMAIN.startswith("https")
```

**Solange kein DNS/TLS konfiguriert ist**, muss die Domain auf die IP mit HTTP zeigen:

```yaml
DOMAIN: "188.34.74.187"
WEB_DOMAIN: "http://188.34.74.187"
```

Bei `WEB_DOMAIN: "https://..."` wird ein `Secure`-Cookie gesetzt, das der Browser bei HTTP-Verbindungen **nicht sendet** → Login-Loop (403 auf `/me`).

**Nach DNS/TLS-Setup** auf FQDN + HTTPS umstellen:

```yaml
DOMAIN: "dev.chatbot.voeb-service.de"
WEB_DOMAIN: "https://dev.chatbot.voeb-service.de"
```

---

## Known Issues: Vespa + OpenSearch

| Issue | Beschreibung | Workaround |
|-------|-------------|------------|
| Vespa 4 Gi Memory Minimum | Vespa-Container prueft beim Start ob memory LIMIT >= 4 Gi. Pod startet nicht bei niedrigerem Limit. | `resources.limits.memory` auf mindestens `4Gi` setzen. `requests` koennen niedriger sein (z.B. `512Mi` im Zombie-Mode). |
| StatefulSet PVC immutable | Kubernetes erlaubt keine Aenderung von `volumeClaimTemplates` in bestehenden StatefulSets. Betrifft Vespa UND OpenSearch. | StatefulSet loeschen (`kubectl delete sts da-vespa`), PVC manuell loeschen, dann `helm upgrade`. Daten gehen verloren — Re-Indexierung noetig. |
| Vespa Startup ~3-5 Min (Zombie-Mode) | Mit reduzierten Ressourcen (50m CPU) startet Vespa deutlich langsamer als mit Standard-Ressourcen. | `initialDelaySeconds` auf Readiness Probe erhoehen, oder `--timeout 15m` bei Helm verwenden. |
| Vespa MUSS aktiv bleiben (v3.x) | `wait_for_vespa_or_shutdown` in `app_base.py:517` prueft Vespa-Erreichbarkeit. Ohne Vespa-Pod crashen alle Celery-Worker. | `vespa.enabled: true` MUSS in values-common.yaml stehen. Erst ab v4.0.0 entfernbar. |
| OpenSearch JVM Heap | OpenSearch benoetigt JVM Heap-Konfiguration. Zu niedrig → OOM, zu hoch → Node-Ressourcen gesprengt. | DEV/TEST: `-Xms512m -Xmx512m` (Docker Compose) / 1.5 Gi Request (Helm). PROD: 2 Gi Request. |

> **Hintergrund:** Onyx migriert von Vespa zu OpenSearch (seit v3.0.0). Vespa laeuft im "Zombie-Mode" mit minimalen Ressourcen, nur fuer den Readiness Check. OpenSearch ist das primaere Document Index Backend. Vollstaendige Analyse: `docs/analyse-opensearch-vs-vespa.md`.

---

## Troubleshooting

| Problem | Ursache | Lösung |
|---------|---------|--------|
| Pods Pending: "Insufficient cpu" | Rolling Update Deadlock | Alte RS auf 0 skalieren |
| api-server CrashLoop: `database "onyx" does not exist` | DB nicht angelegt | [PostgreSQL Runbook](./stackit-postgresql.md) |
| api-server CrashLoop: `permission denied to create role` | Managed PG kein CREATEROLE | `db_readonly_user` per Terraform |
| api-server CrashLoop: `NoCredentialsError` | S3 Credentials fehlen | Object Storage Credentials anlegen |
| celery-beat: Redis probe timeout | REDIS_HOST falsch | `REDIS_HOST: "onyx-dev"` setzen |
| celery-worker: Vespa probe failed | Vespa startet langsam (besonders im Zombie-Mode mit reduzierten Ressourcen) | 3-5 Min warten, Vespa-Logs pruefen |
| celery-worker: OpenSearch probe failed | OpenSearch noch nicht bereit | OpenSearch-Logs pruefen, JVM Heap pruefen |
| Vespa Pod OOMKilled | memory LIMIT < 4 Gi | Vespa benoetigt mindestens 4 Gi memory LIMIT (Hard-Check im Container). `requests` koennen niedriger sein. |
| Helm upgrade abgelehnt: Vespa StatefulSet PVC | `volumeClaimTemplates` immutable | StatefulSet + PVC manuell loeschen, dann neu deployen. **Daten gehen verloren!** |
| 502 Bad Gateway | api-server noch nicht bereit | Warten bis Alembic + Uvicorn gestartet |
| Login-Loop: 403 auf `/me` | `WEB_DOMAIN` ist HTTPS, Zugriff per HTTP | `WEB_DOMAIN: "http://<IP>"` setzen |
| Login klappt, Verifizierung hängt | `REQUIRE_EMAIL_VERIFICATION` ohne SMTP | `REQUIRE_EMAIL_VERIFICATION: "false"` |

---

## Eskalation

| Situation | Aktion | Kontakt |
|-----------|--------|---------|
| Runbook-Schritte schlagen fehl | Troubleshooting-Tabelle pruefen, ggf. Rollback | Tech Lead (CCJ) |
| PROD-Ausfall > 15 Min | Incident-Prozess starten (P1/P2) | Tech Lead (CCJ), VÖB Operations [AUSSTEHEND] |
| StackIT-Infrastruktur-Problem | StackIT Support kontaktieren | StackIT Support [AUSSTEHEND] |

> Vollstaendiger Eskalationsprozess: Siehe `docs/betriebskonzept.md` Abschnitt "Incident Management" und `docs/runbooks/rollback-verfahren.md`.

---

## Verwandte Runbooks

- [CI/CD Pipeline](./ci-cd-pipeline.md) — Automatisiertes Deployment ueber GitHub Actions
- [Rollback-Verfahren](./rollback-verfahren.md) — Rollback bei fehlerhaftem Deploy
- [LLM-Konfiguration](./llm-konfiguration.md) — LLM/Embedding-Modelle nach Deploy konfigurieren
