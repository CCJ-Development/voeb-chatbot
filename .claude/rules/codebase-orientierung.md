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
  tasks/                     ← Celery-Tasks (ext-access Sync)
  _core_originals/           ← Backups vor Core-Änderungen
web/src/ext/                 ← Frontend-Extensions
  components/                ← React-Komponenten
  pages/                     ← Eigene Seiten (/ext/...)
  hooks/                     ← React Hooks
  lib/api.ts                 ← API-Client
  i18n/                      ← Deutsche Lokalisierung (ext-i18n)
    translations.ts          ← Dictionary (~250 Strings)
    useTranslation.ts        ← Hook: t() Funktion
    TranslationProvider.tsx  ← DOM-Observer (Schicht 2)
    index.ts                 ← Re-Exports
```

## Konfiguration (Lokal / Docker)
```
deployment/docker_compose/
  .env                       ← Umgebungsvariablen + EXT_-Flags
  env.template               ← Template
  docker-compose.yml         ← Docker (READ-ONLY Struktur)
  docker-compose.voeb.yml    ← VÖB-Overlay (Backend-Mounts für ext/, Core-Dateien, alembic/)
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
    values-common.yaml       ← Gemeinsame Config (PG extern, MinIO aus, OpenSearch+Vespa(Zombie)+Redis an, Health Probes)
    values-dev.yaml          ← DEV: 1 Replica, 8 Celery-Worker (Standard Mode), Auth disabled
    values-test.yaml         ← TEST: 1 Replica, 8 Celery-Worker, Auth disabled
    values-prod.yaml         ← PROD: 2xAPI HA, 2xWeb HA, 8 Celery-Worker (aktualisiert 2026-03-22, Chart 0.4.36, 20 Pods)
    values-monitoring.yaml   ← kube-prometheus-stack DEV/TEST (separater Helm Release in NS monitoring)
    values-monitoring-prod.yaml ← kube-prometheus-stack PROD (90d Retention, 50Gi, separater Teams-Kanal)
    values-loki-prod.yaml    ← Loki Log-Aggregation PROD (loki-stack 2.10.3, 30d Retention, 20Gi)
    values-dev-secrets.yaml  ← DEV Secrets: PG, Redis, S3 Credentials (gitignored)
    values-test-secrets.yaml ← TEST Secrets (gitignored)
```
Onyx: CI/CD (`gh workflow run stackit-deploy.yml`). Manuell: `helm upgrade --install -f values-common.yaml -f values-{env}.yaml`
Monitoring DEV/TEST: `helm upgrade monitoring prometheus-community/kube-prometheus-stack -n monitoring -f values-monitoring.yaml`
Monitoring PROD: `helm upgrade monitoring prometheus-community/kube-prometheus-stack -n monitoring -f values-monitoring-prod.yaml`

## Monitoring
```
deployment/k8s/monitoring-exporters/   ← Exporter + Dashboards + Datasources
  pg-exporter-dev.yaml / test / prod   ← PostgreSQL Exporter (3 Environments)
  redis-exporter-dev.yaml / test / prod ← Redis Exporter (3 Environments)
  opensearch-exporter-prod.yaml        ← OpenSearch Exporter (PROD, elasticsearch-exporter v1.9.0)
  blackbox-exporter-prod.yaml          ← Blackbox Exporter (PROD Health + Externe Deps)
  cert-manager-servicemonitor.yaml     ← ServiceMonitor fuer cert-manager Metriken
  pg-backup-check-prod.yaml            ← CronJob: PG Backup-Validierung (alle 4h)
  grafana-datasource-loki.yaml         ← Grafana Loki Datasource (automatisch provisioniert)
  grafana-dashboards/                  ← Custom Grafana Dashboards (als ConfigMap deployed, 4 Stueck)
    postgresql-14114.json              ← PG Dashboard (gnetId 14114)
    audit-log.json                     ← Audit-Log Dashboard (Loki-basiert, EXT-AUDIT Events)
    redis-763.json                     ← Redis Dashboard (gnetId 763)
    slo-overview.json                  ← SLA/SLO Dashboard (Availability, Latenz, Error Budget)
  apply.sh                             ← Deploy-Script mit Auto-Detection DEV/TEST/PROD
deployment/k8s/network-policies/
  monitoring/                ← NetworkPolicies fuer monitoring-Namespace (13 Policies)
    01-default-deny-all.yaml
    02-allow-dns-egress.yaml
    03-allow-scrape-egress.yaml        ← Prometheus → API:8080 + cert-manager:9402
    04-allow-intra-namespace.yaml
    05-allow-k8s-api-egress.yaml
    06-allow-pg-exporter-egress.yaml   ← PG Exporter → StackIT PG:5432
    07-allow-redis-exporter-egress.yaml ← Redis Exporter → Redis:6379
    08-allow-alertmanager-webhook-egress.yaml ← AlertManager → Teams Webhook
    09-allow-backup-check-egress.yaml  ← Backup-Check → StackIT API
    10-allow-blackbox-egress.yaml      ← Blackbox Exporter → externe HTTPS
    11-allow-opensearch-exporter-egress.yaml ← OS Exporter → OpenSearch:9200
    12-allow-loki-ingress.yaml         ← Promtail/Grafana → Loki:3100
    13-allow-promtail-egress.yaml      ← Promtail → Loki:3100 + K8s API
    apply.sh                 ← Sichere Apply-Reihenfolge (13 Steps + App-NS Policies)
  cert-manager/              ← NetworkPolicies fuer cert-manager-Namespace (6 Policies)
    01-default-deny-all.yaml
    02-allow-dns-egress.yaml
    03-allow-k8s-api-egress.yaml
    04-allow-acme-egress.yaml          ← Let's Encrypt + Cloudflare
    05-allow-monitoring-scrape-ingress.yaml ← Prometheus:9402
    06-allow-webhook-ingress.yaml      ← K8s Admission:443
    apply.sh
  06-allow-monitoring-scrape.yaml      ← App-NS: Ingress von monitoring:8080
  07-allow-redis-exporter-ingress.yaml ← App-NS: Ingress von Redis Exporter:6379
  08-allow-opensearch-exporter-ingress.yaml ← App-NS: Ingress von OS Exporter:9200
```
Zugriff: `kubectl port-forward -n monitoring svc/monitoring-grafana 3001:80` → `http://localhost:3001`
Loki PROD: `helm upgrade loki grafana/loki-stack -n monitoring -f values-loki-prod.yaml`
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
