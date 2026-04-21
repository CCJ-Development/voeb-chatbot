# Runbook: Helm Deploy — Betriebswissen

**Zuletzt verifiziert:** 2026-04-17 (PROD Chart 0.4.36 → 0.4.44, Helm Rev 18; Monitoring Helm Rev 6 via `--force-replace --server-side=false`)
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

**PROD nutzt ein separates Kubeconfig:** `~/.kube/config-prod` (Cluster `vob-prod`, Ablauf 2026-06-22). DEV/TEST: `~/.kube/config` (Cluster `vob-chatbot`, Ablauf 2026-06-14).

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

> **HINWEIS:** TEST-Live-Infrastruktur wurde am **2026-04-21 vollstaendig abgebaut** (Helm Release uninstalled, Namespace geloescht, PG Flex + Bucket via StackIT CLI geloescht). Die folgenden TEST-Anweisungen bleiben als Blueprint fuer Kunden-Klon-Projekte und Reaktivierung. Reaktivierung benoetigt `terraform apply` (siehe `deployment/terraform/environments/test/main.tf` Header) + `helm upgrade --install`.

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
# WICHTIG: opensearch_admin_password explizit mitgeben (oder in values-prod-secrets.yaml enthalten)
helm upgrade --install onyx-prod \
  deployment/helm/charts/onyx \
  --namespace onyx-prod \
  -f deployment/helm/values/values-common.yaml \
  -f deployment/helm/values/values-prod.yaml \
  -f deployment/helm/values/values-prod-secrets.yaml \
  --set "auth.opensearch.values.opensearch_admin_password=<OPENSEARCH_PW>" \
  --wait --timeout 15m

# Nach dem helm upgrade: Recreate-Strategie setzen (verhindert DB Pool Exhaustion durch parallele Pods)
# Hintergrund: RollingUpdate laedt alte + neue Pods gleichzeitig → PostgreSQL max_connections erschoepft → Deadlock
for DEPLOYMENT in $(kubectl get deployments -n onyx-prod -o name); do
  kubectl patch "$DEPLOYMENT" -n onyx-prod -p '{"spec":{"strategy":{"type":"Recreate"}}}'
done

# Option 2: CI/CD (empfohlen)
gh workflow run stackit-deploy.yml -f environment=prod -R CCJ-Development/voeb-chatbot
```

Die `values-{env}-secrets.yaml` Dateien sind gitignored und enthalten:
- PostgreSQL Passwort
- Object Storage Credentials (S3 Access Key / Secret Key)
- DB Readonly Password
- Redis Passwort
- OpenSearch Admin-Passwort (PROD: `auth.opensearch.values.opensearch_admin_password` — via GitHub Secret `OPENSEARCH_PASSWORD` in CI/CD, lokal in `values-prod-secrets.yaml`)

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

### Recreate-Strategie (Primaeere Motivation: DB Pool Exhaustion)

**Primaeere Motivation:** Bei RollingUpdate laufen alte und neue Pods gleichzeitig. Beide Generationen oeffnen DB-Verbindungen → PostgreSQL `max_connections` erschoepft → neue Pods koennen keine Verbindung aufbauen → Deadlock. Mit Recreate werden alte Pods erst beendet, bevor neue starten.

Recreate-Strategie wird automatisch per `kubectl patch` nach jedem `helm upgrade` in CI/CD gesetzt. Manuell (alle Environments):

```bash
# DEV
for DEPLOYMENT in $(kubectl get deployments -n onyx-dev -o name); do
  kubectl patch "$DEPLOYMENT" -n onyx-dev -p '{"spec":{"strategy":{"type":"Recreate"}}}'
done

# TEST
for DEPLOYMENT in $(kubectl get deployments -n onyx-test -o name); do
  kubectl patch "$DEPLOYMENT" -n onyx-test -p '{"spec":{"strategy":{"type":"Recreate"}}}'
done

# PROD (Kubeconfig beachten)
export KUBECONFIG=~/.kube/config-prod
for DEPLOYMENT in $(kubectl get deployments -n onyx-prod -o name); do
  kubectl patch "$DEPLOYMENT" -n onyx-prod -p '{"spec":{"strategy":{"type":"Recreate"}}}'
done
```

Akzeptabel fuer alle Environments (kein Zero-Downtime-Requirement).

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
# PROD: curl -s https://chatbot.voeb-service.de/api/health
# (TEST Live-Infrastruktur seit 2026-04-21 abgebaut)
# Erwartete Ausgabe: {"success":true,"message":"ok","data":null}

# Login-Seite
# DEV:  curl -s -o /dev/null -w "%{http_code}" https://dev.chatbot.voeb-service.de/auth/login
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

> **Historisch (erledigt 2026-03-22):** Vor DNS/TLS-Setup wurde die IP direkt als Domain verwendet (`DOMAIN: "188.34.74.187"`, `WEB_DOMAIN: "http://188.34.74.187"`). Alle Environments laufen jetzt mit FQDN + HTTPS. Diese Konfiguration ist nur noch fuer lokale Neuentwicklungen ohne TLS relevant.

Bei `WEB_DOMAIN: "https://..."` wird ein `Secure`-Cookie gesetzt, das der Browser bei HTTP-Verbindungen **nicht sendet** → Login-Loop (403 auf `/me`).

**Aktuell (alle Environments)** — FQDN + HTTPS:

```yaml
# DEV
DOMAIN: "dev.chatbot.voeb-service.de"
WEB_DOMAIN: "https://dev.chatbot.voeb-service.de"

# PROD
DOMAIN: "chatbot.voeb-service.de"
WEB_DOMAIN: "https://chatbot.voeb-service.de"
```

---

## Known Issues: Allgemein

| Issue | Beschreibung | Workaround |
|-------|-------------|------------|
| ValidatingWebhookConfiguration (x509) | Nach Clean Install (helm delete + install) kann eine stale `ValidatingWebhookConfiguration` verbleiben. Betrifft Helm-eigene Admission Webhooks. Fuehrt zu x509-Fehlern bei nachfolgenden `helm upgrade`-Aufrufen. | `kubectl delete validatingwebhookconfiguration -l app.kubernetes.io/instance=onyx-prod` (bzw. `onyx-dev`/`onyx-test`). Dann erneut `helm upgrade`. |

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
| `helm delete + install` → neue LB-IP | NGINX Ingress Controller wird neu erstellt → bekommt neue externe IP vom Load Balancer. DNS-Eintraege zeigen weiterhin auf alte IP → HTTPS blockiert. | `kubectl get svc -n onyx-{env} \| grep nginx` → neue IP ermitteln. DNS-Update bei GlobVill/Leif anfordern. Workaround: `/etc/hosts`-Eintrag lokal. **Immer `helm upgrade` statt `delete + install` bevorzugen.** |
| Alembic Migrationen nicht nachgeholt | Wenn Upstream Migrationen in die Kette einfuegt (zwischen bestehende Hashes), aber die DB bereits auf einem spaeteren Head gestempelt ist, wird `alembic upgrade head` diese Migrationen nicht ausfuehren. | Neue Migrationen identifizieren (`git diff HEAD~1 -- backend/alembic/versions/`), dann SQL manuell ausfuehren: `kubectl exec -it -n onyx-{env} $(kubectl get pod -n onyx-{env} -l app=api-server -o name \| head -1) -- psql $DATABASE_URL -c "<SQL>"`. Details: Sync #3 in Historische Syncs. |
| OpenSearch Default-Passwort auf PROD | PROD nutzt ein eigenes OpenSearch-Passwort (GitHub Secret `OPENSEARCH_PASSWORD`). Bei Clean Install ohne explizites Passwort wird ein Onyx-Default verwendet → Inkonsistenz mit vorhandenen Daten. | `--set "auth.opensearch.values.opensearch_admin_password=<PW>"` immer mitgeben (manuell) oder GitHub Secret pruefen (CI/CD). |
| DB Pool Exhaustion bei RollingUpdate | RollingUpdate startet neue Pods bevor alte gestoppt werden → doppelter DB-Connection-Pool → PostgreSQL `max_connections` erschoepft → neue Pods schlagen fehl. | Recreate-Strategie setzen (siehe Abschnitt "Recreate-Strategie"). Im Notfall: alte ReplicaSets manuell auf 0 skalieren (`kubectl scale rs <old-rs> --replicas=0 -n onyx-{env}`). |
| PROD Kubeconfig verwenden | PROD laeuft auf eigenem Cluster `vob-prod`. Fehlendes `export KUBECONFIG=~/.kube/config-prod` fuehrt dazu, dass Befehle auf DEV/TEST-Cluster landen. | `export KUBECONFIG=~/.kube/config-prod` vor allen PROD-Befehlen setzen. Ablauf: 2026-06-22 (erneuern via Terraform). |

---

## Eskalation

| Situation | Aktion | Kontakt |
|-----------|--------|---------|
| Runbook-Schritte schlagen fehl | Troubleshooting-Tabelle pruefen, ggf. Rollback | Tech Lead (CCJ) |
| PROD-Ausfall > 15 Min | Incident-Prozess starten (P1/P2) | Tech Lead (CCJ), VÖB Operations [AUSSTEHEND] |
| StackIT-Infrastruktur-Problem | StackIT Support kontaktieren | StackIT Support [AUSSTEHEND] |

> Vollstaendiger Eskalationsprozess: Siehe `docs/betriebskonzept.md` Abschnitt "Incident Management" und `docs/runbooks/rollback-verfahren.md`.

---

## Helm-Upgrade bei Ownership-Konflikten mit kubectl-replace

**Kontext:** Wenn zwischen zwei Helm-Upgrades Ressourcen per `kubectl replace` oder direktem `kubectl apply` geandert wurden, entstehen Ownership-Konflikte (PrometheusRule, Secret, ConfigMap haben dann Field-Manager `kubectl-replace` neben `helm`). Nachstes `helm upgrade` failed mit:

```
Error: UPGRADE FAILED: ... Apply failed with 1 conflict: conflict with "kubectl-replace" using ...
```

**Erstmalig live geloest 2026-04-17** beim PROD-Monitoring-Upgrade (Helm Rev 6).

### Lösung: `--force-replace` + `--server-side=false`

Die neue Helm-CLI verbietet `--force-replace` (ehemals `--force`) mit Server-Side-Apply. Beim Upgrade muss daher auf Client-Side-Apply zurueckgewechselt werden:

```bash
# 1. Fehlgeschlagene Release-Secrets identifizieren + loeschen
helm --kube-context vob-prod history monitoring -n monitoring --max 10
# Revisionen mit Status "failed" notieren

kubectl --context vob-prod delete secret -n monitoring \
  sh.helm.release.v1.monitoring.v6 sh.helm.release.v1.monitoring.v7

# 2. Force-Replace Upgrade mit Client-Side-Apply
helm --kube-context vob-prod upgrade monitoring prometheus-community/kube-prometheus-stack \
  --version 82.10.3 \
  -n monitoring \
  -f deployment/helm/values/values-monitoring-prod.yaml \
  --server-side=false \
  --force-replace \
  --timeout 5m
```

**Seiteneffekte:**
- Deployments koennen restarten (z.B. Grafana, Prometheus-Operator)
- StatefulSets bleiben meist unberuert (Prometheus, AlertManager behalten Daten)
- Historische Field-Manager-Eintraege (z.B. `kubectl-replace (Update)`) bleiben kosmetisch erhalten — das ist normal und nicht funktional

**Prinzip fuer die Zukunft:** Helm als einzige Source of Truth. kubectl-replace nur in echten Notfaellen (dann Field-Manager-Cleanup einplanen).

---

## OOM-Fix PROD (2026-04-17)

**Problem:** Beide API-Server-Pods OOMKilled (9 bzw. 7 Restarts), User sieht "failed to upload" bei grossen LLM-Requests (100k+ Tokens).

**Root Cause:** Memory-Limit 2 GiB zu niedrig, Bursts uebersteigen 2 Gi bei Tool-Calls mit vielen Dokumenten.

**Fix:** `values-prod.yaml` Memory-Werte angepasst + per `kubectl patch` sofort deployed:

| Deployment | Vorher Limit | Nachher Limit | Vorher Request | Nachher Request |
|------------|-------------|---------------|----------------|-----------------|
| `onyx-prod-api-server` | 2 Gi | **4 Gi** | 512 Mi | **1 Gi** |
| `onyx-prod-celery-worker-docfetching` | 4 Gi | **2 Gi** | 1 Gi | **512 Mi** |
| `onyx-prod-celery-worker-docprocessing` | 4 Gi | **2 Gi** | 1 Gi | **512 Mi** |

**Netto-Impact:** 0 GiB zusaetzliche Last (api +2Gi Limit durch docfetching/docprocessing -2Gi Limit kompensiert). 30d-Peaks der Celery-Worker lagen nur bei ~225 MiB — die 4Gi Limits waren ueberdimensioniert.

**Sofort-Deploy per kubectl (vor CI/CD-Run):**
```bash
kubectl --context vob-prod patch deploy onyx-prod-api-server -n onyx-prod \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"api-server","resources":{"limits":{"memory":"4Gi"},"requests":{"memory":"1Gi"}}}]}}}}'

kubectl --context vob-prod patch deploy onyx-prod-celery-worker-docfetching -n onyx-prod \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"celery-worker-docfetching","resources":{"limits":{"memory":"2Gi"},"requests":{"memory":"512Mi"}}}]}}}}'

kubectl --context vob-prod patch deploy onyx-prod-celery-worker-docprocessing -n onyx-prod \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"celery-worker-docprocessing","resources":{"limits":{"memory":"2Gi"},"requests":{"memory":"512Mi"}}}]}}}}'
```

**Rolling Update, keine Downtime.** Nach dem CI/CD-Deploy uebernehmen die values-prod.yaml-Werte automatisch, beide Stellen sind konsistent.

---

## Deep-Health-Endpoint als Readiness-Probe

Seit 2026-04-17 wird `/api/ext/health/deep` als Readiness-Probe genutzt (statt nur `/api/health`).

**Warum:** `/api/health` liefert 200 solange der Python-Prozess lebt — prueft DB nicht. Bei PG-Outage bleibt der Pod "ready", Traffic wird weitergeroutet, User sehen Errors. `/api/ext/health/deep` prueft DB+Redis+OpenSearch → automatischer Traffic-Drain bei Ausfall kritischer Abhaengigkeiten.

**Konfiguration in `values-prod.yaml`:**
```yaml
api_server:
  readinessProbe:
    httpGet:
      path: /api/ext/health/deep
      port: 8080
    initialDelaySeconds: 30
    periodSeconds: 10
    timeoutSeconds: 5
  livenessProbe:
    httpGet:
      path: /api/health          # bleibt auf Python-Liveness
      port: 8080
    initialDelaySeconds: 60
    periodSeconds: 30
```

**Deep-Health-Endpoint:** `backend/ext/routers/health.py` → testet PG + Redis + OpenSearch Konnektivitaet. Typische Latenz 47ms. Public (keine sensitiven Daten, aber Timeout-Guards).

**Nutzer:** Readiness-Probe (K8s), Blackbox-Probe (Prometheus), externer GitHub Actions Health-Monitor (cron 5 Min).

---

## Verwandte Runbooks

- [CI/CD Pipeline](./ci-cd-pipeline.md) — Automatisiertes Deployment ueber GitHub Actions
- [PROD-Deploy (Template)](./prod-deploy.md) — Kompletter PROD-Rollout-Workflow
- [Rollback-Verfahren](./rollback-verfahren.md) — Rollback bei fehlerhaftem Deploy + Alembic-Chain-Recovery
- [LLM-Konfiguration](./llm-konfiguration.md) — LLM/Embedding-Modelle nach Deploy konfigurieren
- [Upstream-Sync](./upstream-sync.md) — Onyx FOSS Upstream-Merges + Alembic Chain
- [DNS + TLS Setup](./dns-tls-setup.md) — Let's Encrypt, cert-manager, Cloudflare DNS-01
- [Alert-Antwort](./alert-antwort.md) — Reaktion auf Prometheus-Alerts (inkl. PostgresDown, Alert Fatigue Fix)
