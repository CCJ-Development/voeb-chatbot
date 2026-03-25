# Betriebskonzept -- VÖB Service Chatbot

**Dokumentstatus**: Entwurf (teilweise verifiziert)
**Letzte Aktualisierung**: 2026-03-22
**Version**: 0.8

---

## Einleitung und Geltungsbereich

Das Betriebskonzept beschreibt die operativen Anforderungen, Prozesse und Richtlinien für den Betrieb des VÖB Service Chatbot. Es umfasst alle drei aktiven Umgebungen (DEV, TEST, PROD).

**Basis-Software**: Enterprise-Fork von [Onyx](https://github.com/onyx-dot-app/onyx-foss) (FOSS, MIT-Lizenz) mit Custom Extension Layer (`backend/ext/`, `web/src/ext/`).

### Zielgruppe
- Operations / DevOps Team (CCJ / Coffee Studios)
- Auftraggeber (VÖB Operations)
- Stakeholder und Führungskräfte

---

## Systemübersicht

### Architektur-Diagramm

```
┌───────────────────────────────────────────────────────────────────┐
│ Internet / Benutzer                                               │
└───────────────────────────┬───────────────────────────────────────┘
                            │
                            ↓ HTTPS (TLSv1.3 — Let's Encrypt ECDSA P-384, cert-manager DNS-01)

┌───────────────────────────────────────────────────────────────────┐
│ StackIT Cloud -- Region EU01 (Frankfurt)                          │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ SKE Kubernetes Cluster "vob-chatbot" (DEV+TEST)             │ │
│  │ Node Pool "devtest": 2× g1a.4d (4 vCPU, 16 GB RAM)        │ │
│  │ Kubernetes 1.33.8, Flatcar 4459.2.1                          │ │
│  │                                                             │ │
│  │  ┌───────────────────────────────────────────────────────┐  │ │
│  │  │ Namespace: onyx-dev (DEV)                             │  │ │
│  │  │ IngressClass: nginx                                   │  │ │
│  │  │ LoadBalancer IP: 188.34.118.222                       │  │ │
│  │  │ HTTPS: LIVE (DNS A-Record auf 188.34.118.222          │  │ │
│  │  │        aktualisiert durch GlobVill, 2026-03-22)       │  │ │
│  │  │                                                       │  │ │
│  │  │  Pods (17):                                            │  │ │
│  │  │  ├── onyx-dev-web-server       (Frontend, 1 Replica)  │  │ │
│  │  │  ├── onyx-dev-api-server       (Backend, 1 Replica)   │  │ │
│  │  │  ├── onyx-dev-celery-beat      (Scheduler, 1 Replica) │  │ │
│  │  │  ├── onyx-dev-celery-worker-primary (Worker, 1 Rep.)  │  │ │
│  │  │  ├── onyx-dev-celery-worker-light    (Worker, 1 Rep.)  │  │ │
│  │  │  ├── onyx-dev-celery-worker-heavy    (Worker, 1 Rep.)  │  │ │
│  │  │  ├── onyx-dev-celery-worker-docfetching  (Worker, 1 Rep.) │  │ │
│  │  │  ├── onyx-dev-celery-worker-docprocessing (Worker, 1 Rep.)│  │ │
│  │  │  ├── onyx-dev-celery-worker-monitoring   (Worker, 1 Rep.) │  │ │
│  │  │  ├── onyx-dev-celery-worker-user-file    (Worker, 1 Rep.) │  │ │
│  │  │  ├── onyx-dev-inference-model  (Model Server, 1 Rep.) │  │ │
│  │  │  ├── onyx-dev-indexing-model   (Model Server, 1 Rep.) │  │ │
│  │  │  ├── opensearch                (Document Index, 1 Rep.)│  │ │
│  │  │  ├── vespa                     (Zombie-Mode, 1 Rep.)  │  │ │
│  │  │  ├── redis                     (Cache, 1 Replica)     │  │ │
│  │  │  └── nginx-ingress-controller  (Ingress, 1 Replica)   │  │ │
│  │  └───────────────────────────────────────────────────────┘  │ │
│  │                                                             │ │
│  │  ┌───────────────────────────────────────────────────────┐  │ │
│  │  │ Namespace: onyx-test (TEST) — HERUNTERGEFAHREN          │  │ │
│  │  │ IngressClass: nginx-test                              │  │ │
│  │  │ LoadBalancer IP: 188.34.118.201                       │  │ │
│  │  │ Status: Dauerhaft heruntergefahren (seit 2026-03-19)  │  │ │
│  │  │         0 Pods. Helm Release + PVCs + Secrets erhalten│  │ │
│  │  │         Reaktivierung: kubectl scale / helm upgrade   │  │ │
│  │  └───────────────────────────────────────────────────────┘  │ │
│  │                                                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ SKE Kubernetes Cluster "vob-prod" (PROD — eigener Cluster)  │ │
│  │ Node Pool: 2× g1a.8d (8 vCPU, 32 GB RAM, 100 GB Disk)     │ │
│  │ Kubernetes 1.33.9, Flatcar 4459.2.3                          │ │
│  │                                                             │ │
│  │  ┌───────────────────────────────────────────────────────┐  │ │
│  │  │ Namespace: onyx-prod (PROD)                           │  │ │
│  │  │ IngressClass: nginx (eigener Cluster, kein Konflikt)  │  │ │
│  │  │ LoadBalancer IP: 188.34.92.162                        │  │ │
│  │  │                                                       │  │ │
│  │  │  Pods (20):                                           │  │ │
│  │  │  ├── onyx-prod-web-server       (Frontend, 2 Replicas HA)│  │ │
│  │  │  ├── onyx-prod-api-server       (Backend, 2 Replicas HA) │  │ │
│  │  │  ├── onyx-prod-celery-beat      (Scheduler, 1 Replica)│  │ │
│  │  │  ├── onyx-prod-celery-worker-primary (Worker, 1 Rep.) │  │ │
│  │  │  ├── onyx-prod-celery-worker-light    (Worker, 1 Rep.)│  │ │
│  │  │  ├── onyx-prod-celery-worker-heavy    (Worker, 1 Rep.)│  │ │
│  │  │  ├── onyx-prod-celery-worker-docfetching  (1 Rep.)    │  │ │
│  │  │  ├── onyx-prod-celery-worker-docprocessing (1 Rep.)   │  │ │
│  │  │  ├── onyx-prod-celery-worker-monitoring   (1 Rep.)    │  │ │
│  │  │  ├── onyx-prod-celery-worker-user-file    (1 Rep.)    │  │ │
│  │  │  ├── onyx-prod-inference-model  (Model Server, 1 Rep.)│  │ │
│  │  │  ├── onyx-prod-indexing-model   (Model Server, 1 Rep.)│  │ │
│  │  │  ├── opensearch                (Document Index, 1 Rep.)│  │ │
│  │  │  ├── vespa                     (Zombie-Mode, 1 Rep.)  │  │ │
│  │  │  ├── redis                     (Cache, 1 Replica)     │  │ │
│  │  │  └── nginx-ingress-controller  (Ingress, 1 Replica)   │  │ │
│  │  └───────────────────────────────────────────────────────┘  │ │
│  │                                                             │ │
│  │  ┌───────────────────────────────────────────────────────┐  │ │
│  │  │ Namespace: monitoring (PROD)                          │  │ │
│  │  │ 9 Pods: Prometheus, Grafana, AlertManager,            │  │ │
│  │  │   kube-state-metrics, 2× node-exporter,               │  │ │
│  │  │   PG Exporter, Redis Exporter, Operator               │  │ │
│  │  │ 3 Targets UP: onyx-api-prod, postgres-prod, redis-prod│  │ │
│  │  │ Alerting: Microsoft Teams PROD-Kanal                  │  │ │
│  │  │ 8 NetworkPolicies (Zero-Trust)                        │  │ │
│  │  └───────────────────────────────────────────────────────┘  │ │
│  │                                                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│              ↓ Internal Networking                                │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Managed PostgreSQL Flex (StackIT)                           │ │
│  │                                                             │ │
│  │  DEV: vob-dev (Flex 2.4 Single, 2 CPU, 4 GB, 20 GB SSD)  │ │
│  │  TEST: vob-test (Flex 2.4 Single, 2 CPU, 4 GB, 20 GB SSD)│ │
│  │  PROD: vob-prod (Flex 4.8 HA, 3-Node Cluster)             │ │
│  │  PostgreSQL Version: 16                                     │ │
│  │  Backup: DEV 02:00 UTC, TEST 03:00 UTC, PROD managed (PITR)│ │
│  │  ACL DEV+TEST: Egress-IP 188.34.93.194/32 + Admin          │ │
│  │  ACL PROD: Egress-IP 188.34.73.72/32 + Admin               │ │
│  │  Users: onyx_app (RW), db_readonly_user (RO)               │ │
│  │                                                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ StackIT Object Storage (S3-kompatibel)                     │ │
│  │                                                             │ │
│  │  Buckets:                                                   │ │
│  │  - vob-dev (DEV File Store)                                │ │
│  │  - vob-test (TEST File Store)                              │ │
│  │  - vob-prod (PROD File Store)                              │ │
│  │  Endpoint: object.storage.eu01.onstackit.cloud             │ │
│  │                                                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ StackIT AI Model Serving (LLM)                             │ │
│  │                                                             │ │
│  │  Alle Envs: 4 Chat-Modelle konfiguriert (2026-03-08):      │ │
│  │    GPT-OSS 120B, Qwen3-VL 235B, Llama 3.3 70B, Llama 3.1 8B │ │
│  │  Embedding DEV+TEST: Qwen3-VL-Embedding 8B (aktiv)           │ │
│  │  Embedding PROD: Qwen3-VL-Embedding 8B (aktiv, OpenSearch)    │ │
│  │                                                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ StackIT Container Registry                                 │ │
│  │                                                             │ │
│  │  Projekt: voeb-chatbot                                     │ │
│  │  Images: onyx-backend, onyx-web-server                     │ │
│  │  Registry: registry.onstackit.cloud                        │ │
│  │                                                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### Document Index Backend: OpenSearch (seit 2026-03-19)

**Architektur-Aenderung**: Das primaere Document Index Backend wurde von Vespa auf **OpenSearch 3.4.0** umgestellt. Vespa laeuft weiterhin im **Zombie-Mode** (minimale Ressourcen, nur fuer Celery Readiness Check benoetigt). Dual-Write ist aktiv (Dokumente werden in beide Backends geschrieben), aber Retrieval erfolgt ausschliesslich ueber OpenSearch.

- **DEV**: OpenSearch Single-Node deployed (300m/1.5Gi), 17 Pods gesamt
- **TEST**: Dauerhaft heruntergefahren (seit 2026-03-19, 0 Pods, PVCs erhalten)
- **PROD**: OpenSearch deployed (2026-03-22), Retrieval aktiv. 20 Pods gesamt. Vespa im Zombie-Mode (100m/512Mi Requests, 4Gi Limit — nur fuer Celery Readiness Check).

**Hintergrund**: Vespa erfordert als Celery-Dependency einen laufenden Pod (Readiness Check). Ein vollstaendiges Entfernen ist ohne Upstream-Code-Aenderung nicht moeglich. Daher bleibt Vespa mit minimalen Ressourcen (50m/512Mi DEV, 100m/512Mi Requests / 4Gi Limit PROD) bestehen, waehrend OpenSearch das aktive Retrieval uebernimmt.

### Komponenten-Uebersicht

| Komponente | Technologie | Zweck | Replicas DEV/TEST | Replicas PROD |
|-----------|------------|-------|-------------------|---------------|
| Frontend (Web Server) | Next.js 16, React 19, TypeScript | Web UI | 1 | 2 (HA) |
| Backend (API Server) | Python 3.11, FastAPI 0.133.1, SQLAlchemy 2.0, Pydantic 2.11 | REST API | 1 | 2 (HA) |
| Background Worker | Celery 5.5 (Standard Mode, 8 separate Worker) | Async Tasks, Indexing | 7 Worker + 1 Beat | 7 Worker + 1 Beat |
| Model Server | Onyx Model Server v2.9.8 (Docker Hub Upstream) | Embedding, Inference | 2 (Index + Inference) | 2 (Index + Inference) |
| OpenSearch | OpenSearch 3.4.0 (In-Cluster, Single-Node) | Document Index Backend (Dual-Write, primaeres Retrieval) | 1 (DEV) | 1 (PROD, deployed 2026-03-22) |
| Vespa | Vespa 8.609.39 (In-Cluster, **Zombie-Mode**) | Nur Celery Readiness Check, minimale Ressourcen. Kein aktives Retrieval. Dual-Write aktiv. | 1 | 1 |
| Redis | Redis 7.0.15 (In-Cluster, OT Operator) | Cache, Celery Broker | 1 | 1 |
| PostgreSQL | StackIT Managed Flex (Extern) | Relationale Daten | Flex 2.4 Single | Flex 4.8 HA (3-Node) |
| Object Storage | StackIT S3-kompatibel (Extern) | File Store | Managed | Managed |
| LLM | StackIT AI Model Serving | Chat, RAG | Managed | Managed |
| Ingress | NGINX Ingress Controller | Load Balancing, Routing, Upload-Limit 20 MB (XREF-007) | 1 pro Namespace | 1 |

### Umgebungen

| Umgebung | Cluster | Namespace | LB IP | Egress IP | Status |
|----------|---------|-----------|-------|-----------|--------|
| DEV | `vob-chatbot` | `onyx-dev` | `188.34.118.222` | `188.34.93.194` | LIVE seit 2026-02-27, 17 Pods (inkl. OpenSearch). HTTPS LIVE (DNS A-Record aktualisiert 2026-03-22) |
| TEST | `vob-chatbot` | `onyx-test` | `188.34.118.201` | `188.34.93.194` | **Dauerhaft heruntergefahren** (seit 2026-03-19). 0 Pods. Helm Release + PVCs + Secrets erhalten. Reaktivierung: `kubectl scale` oder `helm upgrade`. |
| PROD | `vob-prod` | `onyx-prod` | `188.34.92.162` | `188.34.73.72` | DEPLOYED seit 2026-03-11, 20 Pods. OpenSearch deployed + Retrieval aktiv (2026-03-22). Chart 0.4.36, Image df049fa, Helm Rev 4 |

**Hinweis**: DEV und TEST teilen sich den SKE-Cluster `vob-chatbot` (Node Pool `devtest`, 2x g1a.4d). PROD laeuft laut ADR-004 auf dem separaten Cluster `vob-prod` (2x g1a.8d). DEV HTTPS LIVE seit 2026-03-22 (DNS A-Record `188.34.118.222` durch GlobVill aktualisiert). PROD HTTPS LIVE seit 2026-03-17. **TEST dauerhaft heruntergefahren seit 2026-03-19** (0 Pods, Helm Release + PVCs + Secrets bleiben erhalten, Reaktivierung jederzeit moeglich). Scale-to-Zero CronJobs wurden entfernt (nicht mehr noetig).

---

## Tech-Stack

### Backend
- **Sprache**: Python 3.11
- **Framework**: FastAPI 0.133.1
- **ORM**: SQLAlchemy 2.0.15
- **Migrations**: Alembic 1.10.4
- **Validation**: Pydantic 2.11
- **Task Queue**: Celery 5.5.1
- **LLM Integration**: LiteLLM 1.81.6
- **Dependency Management**: uv (Requirements exportiert nach `backend/requirements/`)

### Frontend
- **Framework**: Next.js 16.1.6
- **UI Library**: React 19.2.4
- **Sprache**: TypeScript 5.9
- **Styling**: Tailwind CSS 3.4
- **State Management**: Zustand 5.0, SWR 2.1
- **Testing**: Jest 29, Playwright

### Infrastructure as Code
- **Terraform**: StackIT Provider ~> 0.80
- **Helm**: v3.16.0 (Onyx Chart READ-ONLY + Value-Overlays)
- **CI/CD**: GitHub Actions

---

## Extension Framework

Das VÖB-spezifische Extension Framework erweitert Onyx FOSS um Enterprise-Features, ohne den Core-Code zu verändern ("Extend, don't modify"). Alle Extensions leben in `backend/ext/` (Backend) und `web/src/ext/` (Frontend).

### Deployed Extensions

| Modul | Beschreibung | Feature Flag | Admin UI | Status |
|-------|-------------|-------------|----------|--------|
| **ext-branding** | Whitelabel: Logo, App-Name, Login-Text, Greeting, Disclaimer, Popup, Consent | `EXT_BRANDING_ENABLED` | `/admin/ext/branding` | ✅ DEV + TEST deployed (2026-03-08) |
| **ext-token** | LLM Usage Tracking + Limits: Per-User, Per-Model, Timeline, Usage Dashboard | `EXT_TOKEN_LIMITS_ENABLED` | `/admin/ext/token-usage` | ✅ DEV + TEST deployed (2026-03-09) |
| **ext-prompts** | Custom System Prompts: Globale Anweisungen für jeden LLM-Aufruf (prepend, nicht replace) | `EXT_CUSTOM_PROMPTS_ENABLED` | `/admin/ext/system-prompts` | ✅ DEV + TEST deployed (2026-03-09) |
| **ext-i18n** | Deutsche Lokalisierung (~95% UI): ~250 Strings, Drei-Schichten-Architektur (ext-branding + t()-Calls + DOM-Observer) | `EXT_I18N_ENABLED` | — (keine Admin-UI) | ✅ DEV + PROD deployed (2026-03-22) |

### Feature Flags

Alle Flags werden in `backend/ext/config.py` definiert und über Umgebungsvariablen aktiviert:

- `EXT_ENABLED` — Master-Switch (alle Extensions)
- `EXT_BRANDING_ENABLED` — ext-branding
- `EXT_TOKEN_LIMITS_ENABLED` — ext-token
- `EXT_CUSTOM_PROMPTS_ENABLED` — ext-prompts
- `NEXT_PUBLIC_EXT_I18N_ENABLED` — ext-i18n (Frontend Build-Arg + Runtime Env)

Aktivierung in `deployment/helm/values/values-{env}.yaml` oder `deployment/docker_compose/.env`.

### Datenbank

Alle Extension-Tabellen nutzen das Prefix `ext_` (z.B. `ext_branding_config`, `ext_token_usage`, `ext_prompt_templates`, `ext_audit_log`). Migrationen liegen in `backend/alembic/versions/` (Onyx Alembic wird mitgenutzt). Alembic-Chain: `a3b8d9e2f1c4` → `ff7273065d0d` (branding) → `b3e4a7d91f08` (token) → `c7f2e8a3d105` (prompts) → `d8a1b2c3e4f5` (audit).

### Weitere Extensions

- **ext-analytics** — ⏭️ ÜBERSPRUNGEN (Funktionalität bereits in ext-token enthalten)
- **ext-rbac** — ✅ Implementiert (2026-03-23, 7 Endpoints, 29 Tests)
- **ext-access** — ✅ Implementiert (2026-03-25, Core #3 gepatcht, eigener Celery-Task, 11 Tests)

### Referenzen

- Extension-Entwicklungsplan: `docs/referenz/ext-entwicklungsplan.md`
- EE/FOSS-Abgrenzung: `docs/referenz/ee-foss-abgrenzung.md`
- Core-Dateien Regeln: `.claude/rules/core-dateien.md`

---

## Deployment-Prozess

### CI/CD Pipeline

Die Pipeline ist in `.github/workflows/stackit-deploy.yml` definiert und seit Run #5 produktionsreif verifiziert.

```
Git Push auf "main"
  ↓
GitHub Actions Workflow (automatisch)
  ├── Prepare: Image Tag bestimmen (Git SHA)
  ├── Build Backend (parallel, je ~7 Min mit Cache)
  │   └── Push: registry.onstackit.cloud/voeb-chatbot/onyx-backend:<sha>
  ├── Build Frontend (parallel, je ~7 Min mit Cache)
  │   └── Push: registry.onstackit.cloud/voeb-chatbot/onyx-web-server:<sha>
  └── Deploy DEV
      ├── helm dependency build
      ├── helm upgrade --install onyx-dev
      │   -f values-common.yaml -f values-dev.yaml
      │   --set Secrets (PG, Redis, S3, DB_READONLY)
      ├── kubectl patch: Recreate-Strategie (alle Environments)
      ├── kubectl rollout status (alle 12 Deployments)
      └── Smoke Test: curl ${WEB_DOMAIN}/api/health

Manuell (workflow_dispatch):
  ├── Environment waehlbar: dev / test / prod
  ├── TEST: --wait --timeout 15m (kein auto-Rollback, Debug moeglich)
  └── PROD: --wait --timeout 15m + Required Reviewer in GitHub Environment
      └── Eigener Cluster vob-prod (separater Kubeconfig-Kontext)
```

**Wichtige Details**:
- Model Server wird NICHT gebaut -- Upstream-Image `onyxdotapp/onyx-model-server:v2.9.8` von Docker Hub
- Secrets werden per `--set` aus GitHub Environment Secrets injiziert (nie in Git)
- Concurrency: Nur ein Deploy pro Environment gleichzeitig, laufende Builds werden bei neuem Push abgebrochen
- Alle Environments (DEV, TEST, PROD) patchen Deployments auf Recreate-Strategie (vermeidet DB Connection Pool Exhaustion bei RollingUpdate)
- Alle GitHub Actions sind SHA-gepinnt (Supply-Chain-Sicherheit)

### CI/CD-Details

#### Trigger und paths-ignore

Der Workflow wird **nicht** ausgelöst bei Änderungen an:
- `docs/**` -- reine Dokumentationsänderungen
- `*.md` -- Markdown-Dateien im Root
- `.claude/**` -- AI-Instruktionsdateien

Dadurch erzeugen Docs-only Commits kein unnötiges Build+Deploy. Code-Änderungen an `main` triggern immer einen DEV-Deploy.

#### Concurrency-Verhalten

```yaml
concurrency:
  group: deploy-${{ github.event.inputs.environment || 'dev' }}
  cancel-in-progress: true
```

- Pro Environment (dev/test/prod) läuft maximal **ein** Deploy gleichzeitig
- Ein neuer Push auf `main` bricht einen laufenden DEV-Deploy ab und startet den neueren
- TEST- und PROD-Deploys (manuell) haben eigene Concurrency-Gruppen und beeinflussen DEV nicht

#### Supply-Chain-Sicherheit (SHA-Pinning)

Alle GitHub Actions sind auf **Commit-SHA fixiert** statt auf Major-Version-Tags (z.B. `v4`). Dies verhindert Supply-Chain-Angriffe, bei denen ein kompromittiertes Action-Repository ein Tag auf einen schadhaften Commit umbiegt.

```
actions/checkout@34e114876b...            # v4
docker/login-action@c94ce9fb46...         # v3
docker/setup-buildx-action@8d2750c6...    # v3
docker/build-push-action@10e90e36...      # v6
azure/setup-helm@bf6a7d304b...            # v4
azure/setup-kubectl@c0c8b32d33...         # v4
```

Die Pipeline hat `permissions: contents: read` -- minimales Privilege, nur Lesezugriff auf das Repository.

#### Smoke Test pro Environment

Nach jedem Deploy wird ein Health Check gegen `/api/health` ausgeführt:

| Environment | Versuche | Interval | Timeout | Gesamt |
|-------------|----------|----------|---------|--------|
| DEV | 12 | 10s | 5s pro Request | ~2 Min |
| TEST | 18 | 10s | 5s pro Request | ~3 Min |
| PROD | 18 | 10s | 5s pro Request | ~3 Min |

TEST und PROD haben mehr Versuche, da HA-Deployments (mehrere Replicas) länger zum Starten brauchen können. Die Domain wird dynamisch aus der Kubernetes ConfigMap `env-configmap` gelesen.

#### Model Server Pinning

Der Model Server (`onyxdotapp/onyx-model-server`) wird **nicht** von uns gebaut. Er ist identisch mit dem Upstream Onyx Image und wird direkt von Docker Hub gepullt.

- Gepinnt auf Version `v2.9.8` (kein `:latest`)
- Definiert als Environment-Variable im Workflow (zentral änderbar)
- Für PROD: Evaluierung ob das Image in die StackIT Registry gespiegelt wird (Datensouveränität)

#### Secret-Injection

Secrets werden **nie** in Git gespeichert. Der Injektionspfad:

```
GitHub Environment Secrets (verschlüsselt, pro Environment getrennt)
  ↓ CI/CD Pipeline liest Secrets zur Laufzeit
    ↓ helm upgrade --set "auth.postgresql.values.password=${{ secrets.POSTGRES_PASSWORD }}"
      ↓ Helm erstellt Kubernetes Secrets (Base64-encoded)
        ↓ Pods mounten Secrets als Environment-Variablen
```

**Verwaltete Secrets pro Environment**:

| Secret | Verwendung |
|--------|-----------|
| `POSTGRES_PASSWORD` | PostgreSQL App-User Passwort |
| `REDIS_PASSWORD` | Redis Standalone Passwort |
| `S3_ACCESS_KEY_ID` | StackIT Object Storage Access Key |
| `S3_SECRET_ACCESS_KEY` | StackIT Object Storage Secret Key |
| `DB_READONLY_PASSWORD` | PostgreSQL Readonly-User (Knowledge Graph) |

**Globale Secrets** (Repository-weit, nicht Environment-spezifisch):

| Secret | Verwendung |
|--------|-----------|
| `STACKIT_REGISTRY_USER` | Container Registry Robot Account |
| `STACKIT_REGISTRY_PASSWORD` | Container Registry Token |
| `STACKIT_KUBECONFIG` | Base64-encoded Kubeconfig DEV+TEST (Ablauf: 2026-05-28) |

### Helm-basiertes Deployment

```
deployment/helm/
├── charts/onyx/                   ← Onyx Helm Chart (READ-ONLY, nicht verändern!)
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
└── values/
    ├── values-common.yaml         ← Gemeinsam: PG aus, MinIO aus, OpenSearch+Vespa(Zombie)+Redis an, Health Probes
    ├── values-dev.yaml            ← DEV: 1 Replica, 8 Celery-Worker (Standard Mode), eigene PG+S3
    ├── values-test.yaml           ← TEST: Analog DEV, eigene PG+S3+IngressClass
    ├── values-prod.yaml           ← PROD: 2×API HA, 2×Web HA, 8 Celery-Worker, eigene PG+S3
    ├── values-monitoring.yaml     ← Monitoring DEV/TEST (kube-prometheus-stack)
    └── values-monitoring-prod.yaml← Monitoring PROD (90d Retention, 50Gi, separater Teams-Kanal)
```

**Deployment-Kommandos** (manuell, falls noetig):

```bash
# DEV
helm upgrade --install onyx-dev deployment/helm/charts/onyx \
  --namespace onyx-dev \
  -f deployment/helm/values/values-common.yaml \
  -f deployment/helm/values/values-dev.yaml \
  --wait --timeout 15m

# TEST
helm upgrade --install onyx-test deployment/helm/charts/onyx \
  --namespace onyx-test \
  -f deployment/helm/values/values-common.yaml \
  -f deployment/helm/values/values-test.yaml \
  --wait --timeout 15m

# PROD (eigener Cluster vob-prod, eigener Kubeconfig-Kontext)
helm upgrade --install onyx-prod deployment/helm/charts/onyx \
  --namespace onyx-prod \
  -f deployment/helm/values/values-common.yaml \
  -f deployment/helm/values/values-prod.yaml \
  --wait --timeout 15m
```

**Hinweis**: Vor jedem manuellen Helm-Deploy muss `helm dependency build deployment/helm/charts/onyx` ausgeführt werden. Die Subchart-`.tgz`-Dateien sind gitignored.

### Rollback-Strategie

**Szenarien**:

1. **Fehlerhaftes Deployment (alle Environments)**
   - Alle Environments (DEV, TEST, PROD) nutzen `--wait --timeout 15m`: Kein automatischer Rollback bei Timeout — Release bleibt stehen und kann debuggt werden. Grund: 17-20 Pods mit Cold Start (Alembic Migrations, Model Server, OpenSearch) brauchen mehr Zeit.
   - Manueller Rollback: `helm rollback onyx-{env} -n onyx-{env}`
   - Helm History: Maximal 5 Revisionen (`--history-max 5`)

3. **Datenbankmigrationen**
   - Alembic-Migrationen werden vom API-Server beim Start ausgeführt
   - Vor kritischen Migrationen: PG-Backup verifizieren (managed, DEV 02:00 UTC, TEST 03:00 UTC, PROD HA mit PITR)
   - Reverse-Migration: `alembic downgrade -1`

---

## Change Management

### Branching-Strategie

Das Projekt nutzt **Simplified GitLab Flow** -- ein einziger langlebiger Branch (`main`) mit Feature- und Release-Branches.

```
feature/*  →  lokaler Merge  →  main  →  push  →  auto-deploy DEV
                                          │
                                          └→  release/X.Y  →  workflow_dispatch  →  TEST
                                │
                                └→  tag vX.Y.Z  →  workflow_dispatch  →  PROD
                                │
                                └→  merge back  →  main
```

**Branch-Typen**:

| Branch | Zweck | Lebensdauer |
|--------|-------|-------------|
| `main` | Integrationsbranch, auto-deploy DEV, Upstream-Merges | Permanent |
| `feature/*` | Feature-Entwicklung, Bugfixes, Doku | Temporär (bis auf main gemergt) |
| `release/*` | Release-Stabilisierung für TEST/PROD | Temporär (bis zurück in main gemergt) |
| `hotfix/*` | Dringende Fixes auf Release-Branch | Temporär (Stunden bis Tage) |

### Promotion-Pfad

Jede Änderung durchläuft folgende Stufen:

```
Entwicklung (Feature-Branch)
  → Lokaler Merge auf main + Push (CI-Checks auf Push-to-main)
    → Auto-Deploy auf DEV
      → Automatischer Deploy auf DEV
        → Manueller Deploy auf TEST (workflow_dispatch)
          → Manueller Deploy auf PROD (workflow_dispatch + Approval)
```

### Änderungskategorien

| Kategorie | Beschreibung | Beispiele | Prozess |
|-----------|-------------|-----------|---------|
| **Standard Change** | Geplante Feature-Entwicklung | Neues Modul, UI-Änderung, Doku | Feature-Branch → lokaler Merge auf main → Push → DEV → TEST → PROD |
| **Emergency Change** | Dringender Fix für Produktionsproblem | Security Patch, Crash Fix | Hotfix-Branch → lokaler Merge auf Release-Branch + main |
| **Upstream-Merge** | Update von Onyx FOSS | Nach Bedarf, mind. quartalsweise, oder bei Security Updates | `chore/upstream-sync-*` → Test-Merge → PR → main |
| **Infrastruktur-Change** | Terraform, Helm Values, CI/CD | Node-Skalierung, neue Secrets | Feature-Branch → lokaler Merge auf main → Push → Deploy |

### Freigabestufen pro Environment

| Environment | Trigger | Freigabe | Rollback | Helm Timeout |
|-------------|---------|----------|----------|-------------|
| **DEV** | Automatisch bei Push auf `main` | Keine manuelle Freigabe nötig | `helm rollback` (manuell) | 15 Min |
| **TEST** | Manuell (`workflow_dispatch`) | Tech Lead triggert Deploy | `helm rollback` (manuell) | 15 Min |
| **PROD** | Manuell (`workflow_dispatch`) | Tech Lead + Required Reviewer (GitHub Environment Protection) | `helm rollback` (manuell) | 15 Min |

**Hinweis**: Alle Environments nutzen `--wait --timeout 15m` (kein `--atomic`). Kein automatischer Rollback bei Timeout — Release bleibt stehen und kann debuggt werden. Grund: 17-20 Pods mit Cold Start (Alembic Migrations, Model Server, OpenSearch) brauchen mehr Zeit.

### Dokumentation von Änderungen

Jede Änderung wird an folgenden Stellen dokumentiert:

1. **Git Commit**: Konventionelles Format `<type>(<scope>): <Beschreibung>` mit Bullet-Liste im Body
2. **Git Log**: Commit-Messages dokumentieren Änderungen (PRs nur bei Upstream-Syncs)
3. **CHANGELOG.md**: Eintrag unter `[Unreleased]` mit Kategorie (Added, Changed, Fixed, Security)
4. **Modulspezifikation**: Bei Abweichung von der Spezifikation wird diese aktualisiert

### 4-Augen-Prinzip (Best Practice, orientiert an BAIT Kap. 2/7)

**Best Practice (angelehnt an BAIT)**: Keine Änderung an der Produktionsumgebung ohne dokumentierte zweite Freigabe. Der VÖB unterliegt als eingetragener Verein (e.V.) nicht direkt den BAIT — das 4-Augen-Prinzip wird als freiwillige Orientierung an BAIT Kap. 2 (IT-Governance) und Kap. 7 (IT-Projekte und Anwendungsentwicklung) umgesetzt.

**Aktueller Stand** (1-Person-Entwicklungsteam):

| Maßnahme | Status | Details |
|----------|--------|---------|
| Pull Request Pflicht | Nur für Upstream-Syncs | Feature-Branches werden lokal auf main gemergt und gepusht. CI-Checks (helm-validate, build-backend, build-frontend) laufen auf Push nach main. Nur Upstream-Syncs nutzen Pull Requests (Diff-Inspektion bei großen Merges) |
| Self-Review + PR-Checkliste | IMPLEMENTIERT | Checkliste vor jedem Commit (Tests, Lint, Types, Docs) |
| Branch Protection (`main`) | IMPLEMENTIERT (2026-03-07) | PR required, 3 Required Status Checks (helm-validate, build-backend, build-frontend), kein Review-Requirement (Solo-Dev) |
| Environment Protection (`prod`) | IMPLEMENTIERT | Required Reviewer in GitHub Environment `prod` + 6 Secrets |

**Interims-Lösung** (bis zweiter Reviewer verfügbar):
- Tech Lead führt dokumentiertes Self-Review durch (PR-Beschreibung + Checkliste)
- Commit-Freigabe erfolgt explizit durch Tech Lead nach lokaler Prüfung
- Kein Self-Merge auf `main` ohne vorherige Checkliste

**Langfristig**: VÖB-Stakeholder oder zweiter CCJ-Mitarbeiter als Required Reviewer für das GitHub Environment `prod`.

---

## Release Management

### Release-Planung

Releases sind an Projektmeilensteine (M1-M6) gebunden. Jeder Meilenstein erzeugt einen Release-Branch, der durch TEST und PROD promoviert wird.

### Versionierung

**Semantic Versioning** (SemVer): `Major.Minor.Patch`

| Segment | Wann inkrementieren | Beispiel |
|---------|---------------------|---------|
| **Major** | Breaking Changes, große Architekturänderungen | `2.0.0` |
| **Minor** | Neues Feature, neuer Meilenstein | `1.1.0` |
| **Patch** | Bugfix, Security Patch | `1.0.1` |

**Nomenklatur**:
- Release-Branch: `release/X.Y` (z.B. `release/1.0`)
- Git Tag: `vX.Y.Z` (z.B. `v1.0.0`)
- Erster Release (M1 Infrastruktur): `v1.0.0`

### Release-Checkliste

Vor jedem Release-Deploy auf TEST/PROD:

| # | Schritt | Verantwortlich | Prüfung |
|---|---------|---------------|---------|
| 1 | DEV stabil: Smoke Tests grün, keine offenen P0/P1 Bugs | Tech Lead | CI/CD Pipeline grün |
| 2 | Release-Branch von `main` schneiden | Tech Lead | `git checkout -b release/X.Y` |
| 3 | TEST-Deploy + Validierung | Tech Lead | `gh workflow run stackit-deploy.yml -f environment=test --ref release/X.Y` |
| 4 | UAT (User Acceptance Testing) durch VÖB | VÖB | Falls für Meilenstein erforderlich |
| 5 | Bugfixes auf Release-Branch, Cherry-Pick zurück nach `main` | Tech Lead | `git cherry-pick <fix-commit>` auf `main` |
| 6 | Git Tag setzen | Tech Lead | `git tag -a vX.Y.Z -m "Release vX.Y.Z — Meilenstein"` |
| 7 | PROD-Deploy | Tech Lead + Reviewer | `gh workflow run stackit-deploy.yml -f environment=prod --ref release/X.Y` |
| 8 | Release-Branch zurück nach `main` mergen | Tech Lead | `git checkout main && git merge release/X.Y` |
| 9 | CHANGELOG.md aktualisieren | Tech Lead | `[Unreleased]` → `[vX.Y.Z]` |
| 10 | Abnahmeprotokoll ausfüllen | Tech Lead + VÖB | `docs/abnahme/` |

### Hotfix-Prozess

Für dringende Fixes auf einer bereits released Version:

```
1. Hotfix-Branch von release/* erstellen
   git checkout release/X.Y
   git checkout -b hotfix/beschreibung

2. Fix implementieren + testen

3. PR gegen release/* Branch
   gh pr create --base release/X.Y

4. Nach Merge: Neuen Patch-Tag setzen (Z inkrementieren)
   git tag -a vX.Y.(Z+1) -m "Hotfix: Beschreibung"
   # Beispiel: v1.0.0 → v1.0.1

5. PROD-Deploy (workflow_dispatch)

6. Cherry-Pick nach main
   git checkout main
   git cherry-pick <fix-commit>
```

### Release-Historie

| Version | Meilenstein | Datum | Inhalt |
|---------|-------------|-------|--------|
| v1.0.0 | M1 Infrastruktur | Geplant | DEV+TEST live, CI/CD, Security Baseline |

---

## Monitoring und Alerting

### Aktueller Stand

**Self-Hosted Monitoring-Stack deployed auf allen Clustern.** kube-prometheus-stack im eigenen Namespace `monitoring` (separater Helm Release pro Cluster). Ueberwachung erfolgt ueber:

1. **Prometheus**: Scrape-Targets pro Cluster (DEV+TEST: 6 Targets, PROD: 3 Targets — onyx-api-prod, postgres-prod, redis-prod), 30s Intervall. DEV+TEST: 30d Retention, 20 Gi PVC. PROD: 90d Retention, 50 Gi PVC.
2. **Grafana**: Dashboards fuer Kubernetes, PostgreSQL (gnetId 14114), Redis (gnetId 763). PROD nutzt Sidecar-Dashboards (persistent, kein manueller Import noetig). Zugriff per `kubectl port-forward` (kein externer Ingress, Enterprise Best Practice).
3. **AlertManager**: 20 Alert-Rules pro Cluster, Zustellung via Microsoft Teams Webhook. DEV+TEST: gemeinsamer Teams-Kanal. PROD: separater Teams PROD-Kanal mit `[PROD]`-Prefix. `send_resolved: true` fuer Entwarnung.
4. **Exporters**: postgres_exporter v0.19.1 + redis_exporter v1.82.0 (DEV+TEST: 4 Pods, PROD: 2 Pods)
5. **kube-state-metrics + node-exporter**: Cluster-weite Pod/Node/Deployment-Metriken (PROD: 2x node-exporter fuer 2 Nodes)
6. **CI/CD Smoke Tests**: Jeder Deploy prueft `/api/health` (DEV: 12 Versuche a 10s = 120s, TEST/PROD: 18 Versuche a 10s = 180s)
7. **StackIT Console**: Managed-Service-Metriken fuer PostgreSQL und Object Storage
8. **NetworkPolicies (Monitoring)**: 8 Policies pro Monitoring-Namespace (Zero-Trust: Default-Deny, DNS-Egress, Scrape-Egress, Intra-Namespace, K8s-API, PG-Exporter, Redis-Exporter, AlertManager-Webhook-Egress)

**Monitoring-Pods (PROD)**: 9 Pods im Namespace `monitoring` — Prometheus, Grafana, AlertManager, kube-state-metrics, 2x node-exporter, PG Exporter, Redis Exporter, prometheus-operator.

### Health Checks (Kubernetes)

- **API Server**: `httpGet /health:8080` (Readiness: 30s+6x10s=90s, Liveness: 60s+8x15s=180s)
- **Webserver**: `tcpSocket :3000` (Readiness: 20s+6x10s=80s, Liveness: 30s+5x15s=105s)
- **Health Endpoint**: `GET /api/health` — prueft DB-Connectivity, gibt `{"success": true}` zurueck. Extern: `/api/health` (via NGINX Proxy), Intern: `/health:8080` (K8s Probes)
- **Lesson Learned**: Next.js hat keinen HTTP-Health-Endpoint — TCP Socket Probe statt httpGet

### Monitoring-Ressourcen

| Komponente | CPU Request | RAM Request |
|------------|-------------|-------------|
| Prometheus | 500m | 1 Gi |
| Grafana | 100m | 256 Mi |
| AlertManager | 100m | 128 Mi |
| kube-state-metrics | 100m | 128 Mi |
| node-exporter (x2) | 200m | 256 Mi |
| prometheus-operator | 100m | 128 Mi |
| **Summe Monitoring** | **1.100m** | **~1,9 Gi** |

### Offene Punkte

| Thema | Status | Prioritaet |
|-------|--------|-----------|
| Log-Aggregation (Loki) | Zu evaluieren | P2 |
| Grafana Dashboards als ConfigMap (DEV+TEST) | Offen (manuell importiert, nicht persistent). PROD geloest via Sidecar-Dashboards. | P3 |
| Grafana Ingress mit Auth | Geplant | P2 |
| NetworkPolicies `onyx-prod` | Offen (bewusst — vollstaendiges Set kommt mit DNS/TLS-Hardening) | P1 |

**Alert-Rules (20 Stück):**

| Metrik | Schwellwert | Aktion |
|--------|------------|--------|
| Pod Restart Count | > 3 in 1h | Critical Alert |
| Node Memory | < 10% frei | Critical Alert |
| API Error Rate | > 1% | Alert |
| Database Connections | Pool-Limit nahend | Alert |
| Disk Usage | > 85% | Alert |

---

## Backup und Recovery

> Detailliertes Konzept: `docs/backup-recovery-konzept.md` (BSI CON.3)
> StackIT-Recherche: `audit-output/stackit-backup-recherche.md`

### StackIT Service Certificate V1.1 (gueltig ab 12.09.2025)

| Parameter | Wert |
|-----------|------|
| RPO (vertraglich) | 4 Stunden |
| RTO (vertraglich) | 4 Stunden (fuer DB < 500 GB) |
| Retention | 30 Tage (Default) |
| PITR | Sekundengenau innerhalb Retention-Fenster |
| Restore-Methode | **Clone** (neue Instanz, kein In-Place Restore) |
| HA Failover | < 60 Sekunden (Patroni, synchrone Replikation) |
| Verfuegbarkeits-SLA | 99.95% (Maintenance ausgenommen) |
| Backup-Monitoring | **Kundenverantwortung** |
| Backup-Kosten | Separat abgerechnet (pro GB/Stunde) |

### Backup-Strategie

#### PostgreSQL (Managed)
- **Anbieter**: StackIT Managed PostgreSQL Flex
- **Automatische Backups**:
  - DEV: Taeglich um 02:00 UTC (konfiguriert per Terraform: `pg_backup_schedule = "0 2 * * *"`)
  - TEST: Taeglich um 03:00 UTC (1h nach DEV, kein Overlap: `pg_backup_schedule = "0 3 * * *"`)
  - PROD: Taeglich um 01:00 UTC (`pg_backup_schedule = "0 1 * * *"`) — Flex 4.8 HA (3-Node), WAL-basiert + PITR
- **Retention**: 30 Tage (StackIT Default)
- **PITR (Point-in-Time Recovery)**: PROD: Verfuegbar, sekundengenau, Restore per Clone-Funktion (Self-Service). DEV/TEST: Abhaengig vom StackIT Flex Tier (Flex 2.4 Single — PITR-Verfuegbarkeit nicht bestaetigt).
- **Lifecycle Protection**: `prevent_destroy = true` in Terraform
- **Kritisch**: Backups sind instanzgebunden — bei Loeschung der PG-Instanz sind alle Backups unwiederbringlich verloren

#### Object Storage
- **Anbieter**: StackIT Object Storage (S3-kompatibel)
- **Replikation**: Managed durch StackIT (automatisch ueber 3 AZs, 99.999999999% Durability)
- **Buckets**: `vob-dev`, `vob-test`, `vob-prod` (jeweils fuer File Store)
- **Versionierung**: Unterstuetzt, aber **nicht aktiviert** in Terraform (Audit H3 offen)
- **Verschluesselung**: AES-256 at Rest (StackIT Default), TLS 1.3 in Transit

#### Applikation
- **Code**: Git Repository (GitHub)
- **Konfiguration**: Helm Values in Git, Secrets in GitHub Environments
- **Infrastruktur**: Terraform State (lokal, Remote-Backend vorbereitet)
- **OpenSearch-Daten**: Persistent Volumes, kein separates Backup — Re-Indexierung aus Quelldaten moeglich. Primaeres Document Index Backend (Dual-Write mit Vespa aktiv).
- **Vespa-Daten (Zombie-Mode)**: Persistent Volumes (PROD: 50 GB), kein separates Backup — Re-Indexierung aus Quelldaten moeglich. Vespa laeuft nur noch fuer Celery Readiness Check, kein aktives Retrieval.

#### Redis
- **Kein Backup**: Redis dient als Cache und Celery Broker. Datenverlust hat keine Auswirkung auf persistente Daten.

### RTO/RPO Targets

[AUSSTEHEND — RTO offiziell mit VÖB vereinbaren. RPO 24h im Kickoff beschlossen.]

| Szenario | RTO (Recovery Time) | RPO (Data Loss) | Anmerkung |
|----------|---------------------|------------------|-----------|
| Einzelner Pod Fehler | 1-2 Min | 0 (stateless) | Kubernetes Restart |
| API-Server Ausfall (PROD) | 0 (kein Ausfall) | 0 | HA: zweite Replica uebernimmt |
| Helm Rollback | ~5 Min | 0 | `helm rollback` |
| PG Failover (PROD HA) | < 60 Sek | 0 | Patroni automatisches Failover |
| PG Restore aus Clone | 1-2 Stunden | Sekundengenau (PITR) | Clone-Erstellung + Umstellung |
| Cluster-Neuaufbau | 2-4 Stunden | Bis letztes PG-Backup | Terraform + Helm |

**StackIT-Garantien:** RPO 4h, RTO 4h (fuer DB < 500 GB). Unsere DB ist aktuell < 1 GB.
**Kickoff-Vereinbarung:** RPO 24h (taeglich), erster Monat Beobachtung, ggf. Anpassung.

### Disaster Recovery Prozess

1. **Detection**: Monitoring-Alert (Teams-Kanal) / CI/CD Smoke Test / manuelle Meldung
2. **Assessment**: `kubectl get pods`, `helm status`, StackIT Console pruefen
3. **Recovery**:
   - Pod-Fehler: Kubernetes-Restart oder `kubectl delete pod`
   - Deployment-Fehler: `helm rollback`
   - Datenbank-Fehler: **Self-Service Clone** per StackIT Portal (PITR, sekundengenau). Applikation auf Clone-Instanz umstellen (Connection-String aendern, Helm Re-Deploy). Siehe `docs/runbooks/stackit-postgresql.md` Abschnitt "Backup & Recovery".
   - Cluster-Fehler: Terraform + Helm Re-Deploy (Runbooks: stackit-projekt-setup, helm-deploy)
4. **Validation**: Health Check, funktionale Pruefung
5. **Notification**: VÖB informieren (P1: sofort, P2: innerhalb 1h)
6. **Post-Incident**: Root Cause Analysis dokumentieren (Template: `docs/runbooks/rollback-verfahren.md`)

---

## Update-Prozess

### Upstream Merges (Onyx Updates)

**Frequenz**: Nach Bedarf, mindestens quartalsweise, oder bei kritischen Security Updates

**Prozess**:

```
1. Fetch Upstream
   git fetch upstream main

2. Create Branch
   git checkout -b chore/upstream-sync-YYYY-MM-DD

3. Merge
   git merge upstream/main

4. Resolve Conflicts
   - Konflikte NUR in 10 Core-Dateien erwartet
   - Upstream übernehmen, dann Patches aus _core_originals/ neu anwenden
   - Andere Konflikte = Fork-Regeln wurden verletzt

5. Test
   - Full Test Suite lokal
   - Deploy auf TEST
   - Funktionale Prüfung

6. Deploy to Production
   - workflow_dispatch mit environment=prod
   - Required Reviewers Approval
```

**Warum "Extend, don't modify" funktioniert**: Max. 10 vorhersagbare Merge-Konflikte (10 Core-Dateien). Der `ext/`-Code existiert nicht in Upstream und erzeugt keine Konflikte.

### Extension Updates

**Prozess**: Standard Git Workflow
1. Feature Branch (`feature/{modulname}`)
2. Implementierung in `backend/ext/` und/oder `web/src/ext/`
3. Tests + Code Review
4. Merge auf `main`
5. Automatischer Deploy auf DEV (Push-Trigger)
6. Manueller Deploy auf TEST (workflow_dispatch)
7. Manueller Deploy auf PROD (workflow_dispatch + Approval)

### Database Migrations

**Strategie**: Alembic-Migrationen werden beim API-Server-Start automatisch ausgeführt.

- **Onyx-Migrationen**: `backend/alembic/` (READ-ONLY, kommen mit Upstream-Merges)
- **Extension-Migrationen**: `backend/alembic/versions/` (Onyx Alembic wird mitgenutzt, ext_-Prefix). Chain: a3b8d9e2f1c4 → ff7273065d0d (branding) → b3e4a7d91f08 (token) → c7f2e8a3d105 (prompts) → d8a1b2c3e4f5 (audit)
- **Managed-PG-Einschränkung**: StackIT Flex erlaubt kein `CREATEROLE` -- spezielle User (z.B. `db_readonly_user`) werden per Terraform angelegt

---

## Skalierung

### Aktuelle Konfiguration (DEV/TEST)

| Komponente | Requests | Limits |
|-----------|----------|--------|
| API Server | 250m CPU, 512Mi RAM | 500m CPU, 1Gi RAM |
| Web Server | 100m CPU, 256Mi RAM | 250m CPU, 512Mi RAM |
| Celery Primary | 250m CPU, 512Mi RAM | 500m CPU, 1Gi RAM |
| Celery Beat | 100m CPU, 256Mi RAM | 250m CPU, 512Mi RAM |
| Model Server (je) | 250m CPU, 768Mi RAM | 1000m CPU, 2Gi RAM |
| OpenSearch | 300m CPU, 1.5Gi RAM (DEV) | 1000m CPU, 2Gi RAM (PROD) |
| Vespa (Zombie-Mode) | 50m CPU, 512Mi RAM (DEV) | 100m CPU / 512Mi Req, 4Gi Limit (PROD) |
| Redis | 100m CPU, 128Mi RAM | 250m CPU, 256Mi RAM |

### Skalierungsstrategie

**DEV**: Keine Autoskalierung. 1 Replica pro Service. Standard Celery Mode (8 separate Worker). **TEST**: Dauerhaft heruntergefahren (seit 2026-03-19). 0 Pods, Helm Release + PVCs erhalten. Reaktivierung: `kubectl scale` oder `helm upgrade`.

**PROD (deployed)**:
- Eigener SKE-Cluster `vob-prod` (ADR-004), 2x g1a.8d (8 vCPU, 32 GB RAM, 100 GB Disk)
- **HA fuer API + Web**: 2 Replicas je API Server und Web Server
- Standard Celery Mode: 8 separate Worker (7 Worker + 1 Beat)
- PostgreSQL: Flex 4.8 HA (3-Node Cluster) — automatisches Failover
- **Kapazitaet**: 2x g1a.8d reicht fuer ca. 150 gleichzeitige User (~40% CPU, ~25% RAM bei Vollauslastung, extrapoliert aus DEV+TEST-Messungen)
- **Deployment-Strategie**: Recreate (kein RollingUpdate — vermeidet DB Connection Pool Exhaustion)
- HPA (HorizontalPodAutoscaler) nach Bedarf nachruestbar

### Vertikale Skalierung

- **Kubernetes Nodes DEV+TEST**: g1a.4d (4 vCPU, 16 GB) seit 2026-03-16 (Kostenoptimierung, vorher g1a.8d ADR-005)
- **Kubernetes Nodes PROD**: g1a.8d (8 vCPU, 32 GB, 100 GB Disk), 2 Nodes
- **PostgreSQL DEV+TEST**: Flex 2.4 (2 CPU, 4 GB). Upgrade auf groesseres Flavor per Terraform.
- **PostgreSQL PROD**: Flex 4.8 HA (3-Node Cluster). Vertikales Upgrade per Terraform moeglich.

### Kostenuebersicht (Stand 2026-03-19)

| Umgebung | Monatliche Kosten (ca.) | Nodes | Anmerkung |
|----------|------------------------|-------|-----------|
| DEV + TEST | ~585 EUR/Mo | 2x g1a.4d (geteilt) | TEST dauerhaft heruntergefahren (seit 2026-03-19, 0 Pods). Compute-Kosten nur DEV. PVCs + PG + Bucket bleiben (Speicherkosten minimal). |
| PROD | ~964 EUR/Mo | 2x g1a.8d (eigener Cluster) | Inkl. PG Flex 4.8 HA + Monitoring |
| **Gesamt** | **~1.549 EUR/Mo** | | |

---

## Wartungsfenster

### Kubernetes Cluster Maintenance (Managed)

Alle SKE-Cluster haben automatische Wartungsfenster (konfiguriert per Terraform):

```
DEV+TEST (Cluster vob-chatbot): 02:00-04:00 UTC (taeglich, managed durch StackIT)
PROD (Cluster vob-prod):        03:00-05:00 UTC (taeglich, managed durch StackIT)
Inhalt: Kubernetes-Version-Updates, Machine-Image-Updates
```

**Hinweis**: PROD hat ein eigenes Wartungsfenster (03:00-05:00 UTC), das sich nicht mit DEV+TEST (02:00-04:00 UTC) ueberschneidet. So wird verhindert, dass alle Environments gleichzeitig gewartet werden.

### Geplante Wartungen

[AUSSTEHEND -- Klärung mit VÖB]

| Zeitfenster | Frequenz | Aktivitäten |
|---|---|---|
| [Zu vereinbaren] | Wöchentlich | Patch Management, Security Updates |
| [Zu vereinbaren] | Monatlich | Major Updates, Upstream Merges |

**Benachrichtigungsprozess**: [AUSSTEHEND -- Klärung mit VÖB]

---

## Incident Management

### Severity Levels

| Level | Auswirkung | Response Time | Resolution Target |
|-------|-----------|---|---|
| P1 (Critical) | Produktionssystem down | [AUSSTEHEND -- Klärung mit VÖB] | [AUSSTEHEND -- Klärung mit VÖB] |
| P2 (High) | Funktionalität beeinträchtigt | [AUSSTEHEND -- Klärung mit VÖB] | [AUSSTEHEND -- Klärung mit VÖB] |
| P3 (Medium) | Geringer Impact, Workaround existiert | [AUSSTEHEND -- Klärung mit VÖB] | [AUSSTEHEND -- Klärung mit VÖB] |
| P4 (Low) | Kosmetisches Problem, kein Impact | [AUSSTEHEND -- Klärung mit VÖB] | [AUSSTEHEND -- Klärung mit VÖB] |

### Eskalationspfade

[AUSSTEHEND -- Klärung mit VÖB]

```
Incident Detection (Smoke Test fehlgeschlagen / manuelle Meldung)
  ↓
Tech Lead (CCJ) informiert
  ↓
Assessment + Fix
  ↓
Bei P1/P2: VÖB Operations informieren
  ↓
Post-Incident: Root Cause Analysis
```

### Incident Log Template

```markdown
# Incident: [Titel]

## Timeline
- **YYYY-MM-DD HH:MM UTC**: Incident erkannt
- **YYYY-MM-DD HH:MM UTC**: Assessment begonnen
- **YYYY-MM-DD HH:MM UTC**: Root Cause identifiziert
- **YYYY-MM-DD HH:MM UTC**: Fix deployt
- **YYYY-MM-DD HH:MM UTC**: Service wiederhergestellt

## Root Cause
[Analyse]

## Mitigation
[Was wurde getan]

## Prevention
[Was verhindert Wiederholung]
```

---

## SLA-Definitionen

[AUSSTEHEND -- Abhängig von Vereinbarung mit VÖB]

SLAs, Verfügbarkeitsziele und Reaktionszeiten müssen mit VÖB abgestimmt werden. Folgende Punkte sind zu klären:

- Verfügbarkeitsziel (z.B. 99.5%, 99.9%)
- Response Times pro Severity Level
- Geplante vs. ungeplante Downtime
- Ausnahmen (Wartungsfenster, externe Abhängigkeiten)
- Berichtspflichten

### Externe Abhängigkeiten (nicht unter unserer Kontrolle)

| Abhängigkeit | Anbieter | Auswirkung bei Ausfall |
|-------------|----------|----------------------|
| PostgreSQL Flex | StackIT Managed | Kein DB-Zugriff |
| Object Storage | StackIT Managed | Kein File-Upload/-Download |
| SKE Cluster | StackIT Managed | Kein Betrieb |
| AI Model Serving | StackIT Managed | Keine LLM-Antworten |
| Container Registry | StackIT | Kein Image Pull (laufende Pods nicht betroffen) |
| Microsoft Entra ID | Microsoft (geplant, Phase 3) | Kein Login |

---

## Kontaktliste

[AUSSTEHEND -- Klärung mit VÖB]

| Rolle | Name | Kontakt | Notizen |
|-------|------|---------|---------|
| **Tech Lead (CCJ)** | Nikolaj Ivanov | [AUSSTEHEND -- Klärung mit VÖB] | Geschäftszeiten |
| **StackIT Support** | -- | [AUSSTEHEND -- Klärung mit VÖB] | Managed Services |
| **VÖB Operations Lead** | [AUSSTEHEND -- Klärung mit VÖB] | [AUSSTEHEND -- Klärung mit VÖB] | |
| **VÖB CISO** | [AUSSTEHEND -- Klärung mit VÖB] | [AUSSTEHEND -- Klärung mit VÖB] | Security Incidents |

---

## Sicherheitsrelevante Betriebsaspekte

### Netzwerk-ACLs

| Ressource | ACL | Status |
|-----------|-----|--------|
| PostgreSQL Flex (DEV + TEST) | Cluster-Egress-IP `188.34.93.194/32` + Admin | SEC-01 umgesetzt |
| PostgreSQL Flex (PROD) | Cluster-Egress-IP `188.34.73.72/32` + Admin | SEC-01 umgesetzt |
| SKE Cluster API | Offen (`0.0.0.0/0`) | OPS-01 geplant |

### Secrets Management

- **GitHub Environments**: `dev`, `test` und `prod` mit je 5 Secrets (POSTGRES_PASSWORD, REDIS_PASSWORD, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, DB_READONLY_PASSWORD). PROD nutzt zusaetzlich STACKIT_KUBECONFIG als Environment-Secret (ueberschreibt das globale Repository-Secret automatisch)
- **GitHub Environment Protection (`prod`)**: Required Reviewer konfiguriert — Deployment auf PROD erfordert manuelle Freigabe
- **Globale Secrets**: STACKIT_REGISTRY_USER, STACKIT_REGISTRY_PASSWORD, STACKIT_KUBECONFIG (DEV+TEST)
- **Kubeconfig-Ablauf**: DEV+TEST 2026-05-28, PROD 2026-06-09 -- Erneuerung einplanen
- **Kubernetes Secrets**: `onyx-postgresql`, `onyx-redis`, `onyx-dbreadonly`, `onyx-objectstorage`, `stackit-registry` (pro Namespace)

### Security-Audit Findings (SEC-01 bis SEC-07)

> Autoritative Quelle: `docs/sicherheitskonzept.md`. Priorisierung: P0 = vor TEST, P1 = vor PROD, P2 = vor VÖB-Abnahme.

| ID | Finding | Priorität | Status |
|----|---------|-----------|--------|
| SEC-01 | PostgreSQL ACL auf Cluster-Egress-IP einschränken | P0 | Umgesetzt |
| SEC-02 | Node Affinity erzwingen (DEV/TEST auf eigenen Nodes) | ~~P1~~ | **Zurückgestellt** (2026-03-08) — bestehende Isolation ausreichend (siehe Sicherheitskonzept) |
| SEC-03 | Kubernetes NetworkPolicies (Namespace-Isolation) | P1 | **Umgesetzt** (2026-03-05) |
| SEC-04 | Terraform Remote State (Secrets im Klartext lokal) | ~~P1~~ → P3 | **Zurückgestellt** (2026-03-08) — Solo-Dev, FileVault, Quick Win `chmod 600` umgesetzt |
| SEC-05 | Separate Kubeconfigs pro Environment (RBAC) | ~~P1~~ → P3 | **Zurückgestellt** (2026-03-08) — PROD = eigener Cluster, opportunistisch bei Renewal |
| SEC-06 | Container SecurityContext (`privileged: true` entfernen) | ~~P2~~ → **P1** | **Phase 2 ERLEDIGT** (2026-03-11) — `runAsNonRoot: true` aktiv auf PROD (Vespa Zombie-Mode = dokumentierte Ausnahme) |
| SEC-07 | Encryption-at-Rest verifizieren (PG, S3, Volumes) | P2 | **Umgesetzt** (2026-03-08) — AES-256 (StackIT Default, verifiziert) |

### Betriebsmaßnahmen (OPS)

> Eigenständige Betriebsmaßnahmen, die nicht als SEC-Finding klassifiziert sind.

| ID | Maßnahme | Priorität | Status |
|----|----------|-----------|--------|
| OPS-01 | Cluster API ACL einschränken | P1 | OFFEN (PROD deployed, Umsetzung ausstehend) |
| OPS-02 | TLS/HTTPS aktivieren | P1 | ✅ **ALLE 3 ENVIRONMENTS ERLEDIGT.** DEV + TEST (2026-03-09), PROD (2026-03-17). ECDSA P-384, TLSv1.3, HSTS 1 Jahr |
| OPS-03 | Image Scanning (Trivy/Snyk in CI/CD) | P2 | Vor Abnahme |
| OPS-04 | Audit Logging (zentralisiert) | P2 | Vor Abnahme |

---

## Dokumentation und Runbooks

Runbooks werden in `docs/runbooks/` gepflegt. Jedes Runbook ist ein eigenständiges, verifiziertes Step-by-Step-Dokument.

**Siehe [Runbook-Index](./runbooks/README.md) für die vollständige Übersicht.**

### Vorhandene Runbooks

| # | Runbook | Status | Beschreibung |
|---|---------|--------|--------------|
| 1 | [StackIT Projekt-Setup](./runbooks/stackit-projekt-setup.md) | Verifiziert | StackIT CLI, Service Account, Container Registry |
| 2 | [StackIT PostgreSQL](./runbooks/stackit-postgresql.md) | Verifiziert | DB anlegen, Readonly-User, Managed PG Einschränkungen |
| 3 | [Helm Deploy](./runbooks/helm-deploy.md) | Verifiziert | Helm Install/Upgrade, Secrets, Redis, Troubleshooting |
| 4 | [CI/CD Pipeline](./runbooks/ci-cd-pipeline.md) | Verifiziert | Deploy, Rollback, Secrets, Troubleshooting |
| 5 | [DNS/TLS Setup](./runbooks/dns-tls-setup.md) | ✅ Verifiziert (LIVE seit 2026-03-09) | cert-manager, Let's Encrypt, Cloudflare DNS-01, BSI-konform |
| 6 | [LLM-Konfiguration](./runbooks/llm-konfiguration.md) | Verifiziert | StackIT AI Model Serving, Embedding, Admin UI Setup |
| 7 | [Rollback-Verfahren](./runbooks/rollback-verfahren.md) | Verifiziert | Entscheidungsbaum, Helm/DB-Rollback, Kommunikation, Post-Mortem |

### Geplante Runbooks

1. **Incident Response** -- P1/P2 Prozeduren (6-Phasen-Plan bereits dokumentiert in `docs/sicherheitskonzept.md`, Abschnitt "Incident Response Plan". Runbook als operatives Kurzformat ausstehend.)
2. **Upstream Merge** -- Schritt-fuer-Schritt Onyx-Update-Prozess (Anleitung bereits in `.claude/rules/fork-management.md`, operatives Runbook ausstehend)

**Hinweis**: Monitoring Setup und PROD Provisioning sind erledigt (Monitoring deployed 2026-03-12, PROD deployed 2026-03-11). Dokumentation in `docs/referenz/monitoring-konzept.md` und `docs/technisches-feinkonzept/monitoring-exporter.md`.

### Weitere Referenzdokumentation

| Dokument | Pfad | Inhalt |
|----------|------|--------|
| Implementierungsplan | `docs/referenz/stackit-implementierungsplan.md` | Schritt-fuer-Schritt DEV+TEST Setup |
| Infrastruktur-Referenz | `docs/referenz/stackit-infrastruktur.md` | Architekturentscheidungen, Specs |
| Monitoring-Konzept | `docs/referenz/monitoring-konzept.md` | Prometheus, Grafana, AlertManager, Exporters |
| Monitoring-Exporter | `docs/technisches-feinkonzept/monitoring-exporter.md` | PG + Redis Exporter Spezifikation |
| ADR-004 | `docs/adr/adr-004-umgebungstrennung-dev-test-prod.md` | Umgebungstrennung (PROD = eigener Cluster) |
| Sicherheitskonzept | `docs/sicherheitskonzept.md` | DSGVO, EU AI Act, BSI-Grundschutz, BSI C5 (StackIT), orientiert an BAIT (freiwillig) |
| Testkonzept | `docs/testkonzept.md` | Teststrategie, Abnahmekriterien |
| Changelog | `docs/CHANGELOG.md` | Versionshistorie |

---

**Dokumentstatus**: Entwurf (teilweise verifiziert)
**Letzte Aktualisierung**: 2026-03-22
**Version**: 0.8

### Versionshistorie

| Version | Datum | Autor | Aenderungen |
|---------|-------|-------|-------------|
| 0.8 | 2026-03-22 | COFFEESTUDIOS | PROD 20 Pods (OpenSearch deployed + Retrieval aktiv), Vespa PROD 100m/512Mi Req / 4Gi Limit, DEV HTTPS LIVE (DNS aktualisiert), ext-i18n deployed (DEV + PROD), Chart 0.4.36 / Image df049fa / Helm Rev 4 |
| 0.7.1 | 2026-03-19 | COFFEESTUDIOS | TEST dauerhaft heruntergefahren (0 Pods), Scale-to-Zero CronJobs entfernt |
| 0.7 | 2026-03-19 | COFFEESTUDIOS | OpenSearch aktiviert, Vespa Zombie-Mode, DEV HTTP-Workaround |
| 0.6.1 | 2026-03-14 | COFFEESTUDIOS | Audit-Korrektur: 8 Cross-Ref-Fixes (XREF-002/010/013/014/015/016/019/034) |
| 0.6 | 2026-03-12 | COFFEESTUDIOS | PROD-Cluster (vob-prod) durchgaengig eingearbeitet: Architektur, Infrastruktur, Monitoring (9 Pods, Teams PROD-Kanal, Sidecar-Dashboards), PG Flex 4.8 HA, Backup/PITR, Wartungsfenster 03:00-05:00 UTC, Skalierung/Kapazitaet (150 User), SEC-06 Phase 2, Environment Protection |
| 0.5 | 2026-03-08 | COFFEESTUDIOS | Monitoring-Stack, Health Probes, Security-Audit, Change Management |
| 0.4 | 2026-03-05 | COFFEESTUDIOS | CI/CD Details, Smoke Tests, NetworkPolicies |
| 0.3 | 2026-03-03 | COFFEESTUDIOS | TEST-Umgebung, Helm Values, Runbooks |
| 0.2 | 2026-02-27 | COFFEESTUDIOS | DEV live, erste Architektur |
| 0.1 | 2026-02-22 | COFFEESTUDIOS | Initialer Entwurf |
