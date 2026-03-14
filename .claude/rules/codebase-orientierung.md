# Codebase-Orientierung — Wo finde ich was?

## Onyx Backend
```
backend/onyx/
  main.py                    ← FastAPI App + Router-Registrierung (CORE #1)
  llm/multi_llm.py           ← LLM-Aufrufe (CORE #2)
  access/access.py           ← Permissions/Access Control (CORE #3)
  chat/prompt_utils.py       ← Prompts (CORE #7)
  db/models.py               ← SQLAlchemy Models (READ-ONLY)
  db/engine/sql_engine.py    ← DB Connection (READ-ONLY)
  configs/app_configs.py     ← Konfiguration (READ-ONLY)
  server/auth_check.py       ← Route-Auth-Prüfung (READ-ONLY, aber relevant für ext)
backend/tests/               ← Onyx-Tests (READ-ONLY)
backend/alembic/             ← Onyx-Migrationen + ext_-Migrationen (ext nutzt Onyx-Alembic mit)
backend/requirements/        ← Onyx-Dependencies (READ-ONLY)
```

## Onyx Frontend
```
web/src/
  app/layout.tsx             ← Root Layout (CORE #4)
  app/page.tsx               ← Startseite
  app/admin/                 ← Admin-Bereich
  app/chat/                  ← Chat-Interface
  components/header/         ← Header (CORE #5)
  lib/constants.ts           ← Konstanten (CORE #6)
web/package.json, tailwind.config.js
```

## Unser Extension-Code (HIER arbeiten wir)
```
backend/ext/                 ← Backend-Extensions
  config.py                  ← Feature Flags
  routers/                   ← FastAPI Router
  models/                    ← DB Models (ext_-Prefix)
  schemas/                   ← Pydantic Schemas
  services/                  ← Business Logic
  tests/                     ← Backend-Tests
  _core_originals/           ← Backups vor Core-Änderungen
web/src/ext/                 ← Frontend-Extensions
  components/                ← React-Komponenten
  pages/                     ← Eigene Seiten (/ext/...)
  hooks/                     ← React Hooks
  lib/api.ts                 ← API-Client
```

## Konfiguration (Lokal / Docker)
```
deployment/docker_compose/
  .env                       ← Umgebungsvariablen + EXT_-Flags
  env.template               ← Template
  docker-compose.yml         ← Docker (READ-ONLY Struktur)
  docker-compose.voeb.yml    ← VÖB-Overlay (Backend-Mounts für ext/, multi_llm.py, alembic/)
  .env.voeb.template         ← VÖB-spezifische ENV-Variablen Template
```

## StackIT Cloud-Infrastruktur
```
deployment/terraform/
  modules/stackit/
    main.tf                  ← SKE Cluster, PostgreSQL Flex, Object Storage
    variables.tf             ← Alle Variablen mit DEV-Defaults
    outputs.tf               ← Kubeconfig, PG-Credentials, Bucket-URL
    versions.tf              ← Provider stackitcloud/stackit ~> 0.80
  environments/
    dev/
      main.tf                ← DEV-Umgebung (ruft Modul auf)
      backend.tf             ← State-Backend (lokal, remote vorbereitet)
      terraform.tfvars       ← Projekt-spezifische Werte
    test/
      main.tf                ← TEST-Umgebung (eigene PG + Bucket)
      backend.tf
      terraform.tfvars
    prod/
      main.tf                ← PROD-Umgebung (eigener Cluster vob-prod, PG HA 3-Node)
      backend.tf
      terraform.tfvars
```

## Helm Value-Overlays
```
deployment/helm/
  charts/onyx/               ← Onyx Helm Chart (READ-ONLY, nicht verändern!)
  values/
    values-common.yaml       ← Gemeinsame Config (PG extern, MinIO aus, Vespa+Redis an, Health Probes)
    values-dev.yaml          ← DEV: 1 Replica, 8 Celery-Worker (Standard Mode), Auth disabled
    values-test.yaml         ← TEST: 1 Replica, 8 Celery-Worker, Auth disabled
    values-prod.yaml         ← PROD: 2xAPI HA, 2xWeb HA, 8 Celery-Worker (deployed 2026-03-11)
    values-monitoring.yaml   ← kube-prometheus-stack DEV/TEST (separater Helm Release in NS monitoring)
    values-monitoring-prod.yaml ← kube-prometheus-stack PROD (90d Retention, 50Gi, separater Teams-Kanal)
    values-dev-secrets.yaml  ← DEV Secrets: PG, Redis, S3 Credentials (gitignored)
    values-test-secrets.yaml ← TEST Secrets (gitignored)
```
Onyx: CI/CD (`gh workflow run stackit-deploy.yml`). Manuell: `helm upgrade --install -f values-common.yaml -f values-{env}.yaml`
Monitoring DEV/TEST: `helm upgrade monitoring prometheus-community/kube-prometheus-stack -n monitoring -f values-monitoring.yaml`
Monitoring PROD: `helm upgrade monitoring prometheus-community/kube-prometheus-stack -n monitoring -f values-monitoring-prod.yaml`

## Monitoring
```
deployment/k8s/monitoring-exporters/   ← postgres_exporter + redis_exporter (6 Deployments + Services)
  pg-exporter-dev.yaml
  pg-exporter-test.yaml
  pg-exporter-prod.yaml
  redis-exporter-dev.yaml
  redis-exporter-test.yaml
  redis-exporter-prod.yaml
  apply.sh                   ← Deploy-Script mit Auto-Detection DEV/TEST/PROD
deployment/k8s/network-policies/
  monitoring/                ← NetworkPolicies fuer monitoring-Namespace
    01-default-deny-all.yaml
    02-allow-dns-egress.yaml
    03-allow-scrape-egress.yaml
    04-allow-intra-namespace.yaml
    05-allow-k8s-api-egress.yaml
    06-allow-pg-exporter-egress.yaml    ← PG Exporter → StackIT PG:5432
    07-allow-redis-exporter-egress.yaml ← Redis Exporter → Redis:6379
    apply.sh                 ← Sichere Apply-Reihenfolge (7 Steps + App-NS Policies)
  06-allow-monitoring-scrape.yaml       ← App-NS: Ingress von monitoring:8080
  07-allow-redis-exporter-ingress.yaml  ← App-NS: Ingress von Redis Exporter:6379
```
Zugriff: `kubectl port-forward -n monitoring svc/monitoring-grafana 3001:80` → `http://localhost:3001`
Konzept: `docs/referenz/monitoring-konzept.md`

## CI/CD
```
.github/workflows/
  stackit-deploy.yml         ← Build → StackIT Registry → Helm Deploy (DEV/TEST/PROD)
  upstream-check.yml         ← Wöchentlicher Upstream-Merge-Check
  ci-checks.yml              ← Push-to-main Validierung: helm-validate + Docker Build (Backend + Frontend)
```

## Enterprise-Docs
```
docs/
  README.md                  ← Index
  sicherheitskonzept.md      ← Security
  testkonzept.md             ← Testing
  betriebskonzept.md         ← Operations
  CHANGELOG.md               ← Versionshistorie
  technisches-feinkonzept/   ← Modulspezifikationen
  adr/                       ← Architecture Decisions
  abnahme/                   ← Abnahmeprotokolle
  referenz/
    stackit-implementierungsplan.md  ← DEV-Infrastruktur Step-by-Step
    stackit-infrastruktur.md         ← StackIT Specs + Architekturentscheidungen
```
