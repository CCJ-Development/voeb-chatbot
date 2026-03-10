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
```

## StackIT Cloud-Infrastruktur
```
deployment/terraform/
  modules/stackit/
    main.tf                  ← SKE Cluster, PostgreSQL Flex, Object Storage
    variables.tf             ← Alle Variablen mit DEV-Defaults
    outputs.tf               ← Kubeconfig, PG-Credentials, Bucket-URL
    versions.tf              ← Provider stackitcloud/stackit ~> 0.80
  environments/dev/
    main.tf                  ← DEV-Umgebung (ruft Modul auf)
    backend.tf               ← State-Backend (lokal, remote vorbereitet)
    terraform.tfvars         ← Projekt-spezifische Werte
```

## Helm Value-Overlays
```
deployment/helm/
  charts/onyx/               ← Onyx Helm Chart (READ-ONLY, nicht verändern!)
  values/
    values-common.yaml       ← Gemeinsame Config (PG extern, MinIO aus, Vespa+Redis an, Health Probes)
    values-dev.yaml          ← DEV: 1 Replica, 8 Celery-Worker (Standard Mode), Auth disabled
    values-test.yaml         ← TEST: 1 Replica, 8 Celery-Worker, Auth disabled
    values-prod.yaml         ← PROD: Platzhalter (noch nicht deployed)
    values-monitoring.yaml   ← kube-prometheus-stack (separater Helm Release in NS monitoring)
```
Onyx: CI/CD (`gh workflow run stackit-deploy.yml`). Manuell: `helm upgrade --install -f values-common.yaml -f values-{env}.yaml`
Monitoring: `helm upgrade monitoring prometheus-community/kube-prometheus-stack -n monitoring -f values-monitoring.yaml`

## Monitoring
```
deployment/k8s/network-policies/
  monitoring/                ← NetworkPolicies fuer monitoring-Namespace
    01-default-deny-all.yaml
    02-allow-dns-egress.yaml
    03-allow-scrape-egress.yaml
    04-allow-intra-namespace.yaml
    05-allow-k8s-api-egress.yaml
    apply.sh                 ← Sichere Apply-Reihenfolge (Allow zuerst, Deny zuletzt)
  06-allow-monitoring-scrape.yaml  ← Ingress von monitoring auf Port 8080 (fuer App-NS)
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
