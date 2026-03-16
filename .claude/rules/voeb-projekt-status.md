# VÖB Chatbot — Projektstatus

## Projekt
- **Auftraggeber:** VÖB (Bundesverband Öffentlicher Banken Deutschlands)
- **Auftragnehmer:** CCJ / Coffee Studios (Tech Lead: Nikolaj Ivanov)
- **Cloud:** StackIT (Kubernetes, Datensouveränität, Region EU01 Frankfurt)
- **Auth:** Microsoft Entra ID (OIDC)
- **Basis:** Fork von Onyx FOSS (MIT) mit Custom Extension Layer

## Tech Stack (zusätzlich zu Onyx)
- IaC: Terraform (`deployment/terraform/`) — StackIT Provider ~> 0.80
- Helm: Value-Overlays (`deployment/helm/values/`) — Onyx Chart READ-ONLY
- CI/CD: `.github/workflows/stackit-deploy.yml` (Build → StackIT Registry → Helm Deploy)
- CI: `upstream-check.yml` (wöchentlicher Merge-Kompatibilitäts-Check)
- CI: `.github/workflows/ci-checks.yml` (Push-to-main Validierung: Helm + Docker Build)
- Docker: `deployment/docker_compose/` (.env mit EXT_-Feature Flags)
- Enterprise-Docs: `docs/` (Sicherheitskonzept, Testkonzept, Betriebskonzept, ADRs, Abnahme)

## Aktueller Status

- **Phase 0-1.5:** ✅ Grundlagen, Dev Environment, Dokumentation
- **Phase 2 (Cloud / M1 Infrastruktur):** ✅ **DEV LIVE** (2026-02-27)
  - ✅ StackIT-Zugang, CLI, Service Account, Container Registry
  - ✅ Terraform apply: SKE (g1a.4d, downgraded 2026-03-16 Kostenoptimierung), PG Flex, Object Storage
  - ✅ K8s Namespace `onyx-dev` + Image Pull Secret + Redis Operator
  - ✅ PostgreSQL: DB `onyx` angelegt, `db_readonly_user` per Terraform
  - ✅ Object Storage: Credentials erstellt, in Helm Secrets konfiguriert
  - ✅ Helm Release `onyx-dev`: Alle 16 Pods (8 Celery-Worker, Standard Mode) 1/1 Running
  - ✅ API Health OK, Login funktioniert unter `https://dev.chatbot.voeb-service.de`
  - ✅ Runbooks: stackit-projekt-setup.md, stackit-postgresql.md, helm-deploy.md
  - ✅ CI/CD Pipeline: Produktionsreif (2026-03-02) — Parallel-Build ~8 Min, SHA-gepinnte Actions, Smoke Tests, Concurrency
  - ✅ Upstream-Workflows: 21 Onyx-Workflows deaktiviert, nur StackIT Deploy + Upstream Check aktiv
  - ✅ CI/CD Run #5 (ea70a11): 10 Min, alle 10 Pods Running (historisch, jetzt 16 Pods), Health Check OK
  - ✅ EE-Crash gelöst: `LICENSE_ENFORCEMENT_ENABLED: "false"` in values-common.yaml
  - ✅ DNS: A-Records gesetzt (2026-03-05): `dev.chatbot.voeb-service.de` → `188.34.74.187`, `test.chatbot.voeb-service.de` → `188.34.118.201`
  - ✅ DNS: Cloudflare Proxy auf DNS-only umgestellt und verifiziert (2026-03-05)
  - ✅ TLS/HTTPS DEV: **LIVE** (2026-03-09) — `https://dev.chatbot.voeb-service.de`, Let's Encrypt ECDSA P-384, TLSv1.3, HTTP/2. cert-manager DNS-01 via Cloudflare, ACME-Challenge CNAME-Delegation ueber GlobVill. Details: docs/runbooks/dns-tls-setup.md
  - ✅ TLS/HTTPS TEST: **LIVE** (2026-03-09) — `https://test.chatbot.voeb-service.de`, Let's Encrypt ECDSA P-384, TLSv1.3, HTTP/2. Analog DEV, IngressClass `nginx-test`
  - ✅ LLM: 4 Chat-Modelle konfiguriert (GPT-OSS 120B, Qwen3-VL 235B, Llama 3.3 70B, Llama 3.1 8B). Gemma 3 + Mistral-Nemo nicht kompatibel (kein Tool Calling auf StackIT).
  - ✅ Embedding DEV: Qwen3-VL-Embedding 8B aktiv (umgestellt 2026-03-12).
  - 📋 Scope: DEV live, TEST live, PROD deployed (DNS/TLS offen).
- **Phase 2 PROD:** ✅ **PROD DEPLOYED** (2026-03-11)
  - ✅ Terraform apply: SKE `vob-prod` (eigener Cluster, ADR-004) + PG Flex 4.8 HA (3-Node) + Bucket `vob-prod`
  - ✅ K8s v1.33.9, Flatcar 4459.2.3, 2x g1a.8d (8 vCPU, 32 GB RAM)
  - ✅ cert-manager v1.19.4 + ClusterIssuer `onyx-prod-letsencrypt` READY
  - ✅ Redis Operator + Image Pull Secret in `onyx-prod`
  - ✅ GitHub Environment `prod` + Required Reviewer + 6 Secrets
  - ✅ Helm Release `onyx-prod`: 19 Pods Running (2×API HA, 2×Web HA, 8 Celery-Worker, Vespa, Redis, 2×Model, NGINX)
  - ✅ API Health OK: `http://188.34.92.162/api/health` → 200
  - ✅ SEC-06 Phase 2: `runAsNonRoot: true` aktiv (Vespa = dokumentierte Ausnahme)
  - ✅ PG ACL: Egress `188.34.73.72/32` + Admin
  - ✅ Maintenance-Window: 03:00-05:00 UTC (O8, eigenes Fenster)
  - ✅ Kubeconfig gueltig bis 2026-06-09 (90 Tage)
  - ⏳ DNS: A-Record + ACME-CNAME bei Leif/GlobVill angefragt (2026-03-11)
  - ⏳ TLS/HTTPS: Wartet auf DNS-Eintraege
  - ✅ **Monitoring PROD deployed** (2026-03-12): 9 Pods (Prometheus, Grafana, AlertManager, kube-state-metrics, 2x node-exporter, PG Exporter, Redis Exporter, Operator). 3 Targets UP (API, PG, Redis). Teams PROD-Kanal. Sidecar-Dashboards (PG 14114, Redis 763). 7 NetworkPolicies in monitoring NS.
  - ⏳ NetworkPolicies onyx-prod: Kommt mit DNS/TLS-Hardening (Lesson: Monitoring-Policies nicht ohne Basis-Set anwenden)
- **Phase 2 TEST:** ✅ **TEST LIVE** (2026-03-03)
  - ✅ SEC-01: PG ACL eingeschränkt (188.34.93.194/32 + Admin)
  - ✅ Node Pool auf 2 Nodes skaliert (DEV + TEST)
  - ✅ Terraform apply TEST: PG Flex `vob-test` + Bucket `vob-test`
  - ✅ Namespace `onyx-test` + Image Pull Secret + DB `onyx` angelegt
  - ✅ GitHub Environment `test` + 5 Secrets (PG, Redis, S3)
  - ✅ Helm Release `onyx-test`: 15 Pods Running (8 Celery-Worker, Standard Mode) (+ redis-operator im default NS), Health Check OK
  - ✅ TEST erreichbar unter `https://test.chatbot.voeb-service.de`
  - ✅ Eigene IngressClass `nginx-test` (Conflict mit DEV vermieden)
  - ✅ values-test.yaml Commit + Push (2026-03-03)
  - ✅ CI/CD workflow_dispatch TEST verifiziert — Build + Deploy grün (2026-03-03)
  - ✅ LLM: 4 Chat-Modelle in TEST konfiguriert (GPT-OSS, Qwen3-VL, Llama 3.3, Llama 3.1) (2026-03-08)
  - ✅ Enterprise-Dokumentation überarbeitet: Betriebskonzept, Sicherheitskonzept, Meilensteinplan, ADR-004, README, CHANGELOG (2026-03-03)
  - ✅ Upstream-Merge: 415 Commits von onyx-foss, 0 Core-Konflikte, DEV grün (2026-03-03)
  - ✅ DNS/TLS-Runbook erstellt (docs/runbooks/dns-tls-setup.md)
  - ✅ Fork-Management Doku überarbeitet (8-Schritte-Anleitung)
  - ✅ Embedding TEST: Qwen3-VL-Embedding 8B aktiv (umgestellt 2026-03-08, 4096 Dim, multilingual). DEV: Qwen3-VL-Embedding 8B aktiv (umgestellt 2026-03-12).
  - ✅ DNS: A-Records gesetzt + Cloudflare DNS-only verifiziert (2026-03-05)
  - ✅ TLS/HTTPS DEV: **LIVE** (2026-03-09) — `https://dev.chatbot.voeb-service.de`, Let's Encrypt ECDSA P-384, TLSv1.3, HTTP/2. cert-manager DNS-01 via Cloudflare, ACME-Challenge CNAME-Delegation ueber GlobVill. Details: docs/runbooks/dns-tls-setup.md
  - ✅ TLS/HTTPS TEST: **LIVE** (2026-03-09) — `https://test.chatbot.voeb-service.de`, Let's Encrypt ECDSA P-384, TLSv1.3, HTTP/2. Analog DEV, IngressClass `nginx-test`
  - ✅ Cloud-Infrastruktur-Audit durchgeführt (2026-03-04): 10 CRITICAL, 18 HIGH, ~20 MEDIUM, ~12 LOW
  - ✅ 3 Security Quick Wins deployed (2026-03-05): C6 (DB_READONLY→Secret), H8 (Security-Header), H11 (Script Injection Fix)
  - ✅ C5/SEC-03: NetworkPolicies auf DEV + TEST applied (2026-03-05) — 5 Policies, Cross-NS-Isolation verifiziert
  - ✅ Node-Upgrade g1a.4d → g1a.8d (ADR-005, 2026-03-06), dann Downgrade g1a.8d → g1a.4d (Kostenoptimierung, 2026-03-16): 4 vCPU, 16 GB RAM, 100 GB Disk pro Node
  - ✅ Upstream-Merge: 100 Commits (PR #3), 1 Konflikt (AGENTS.md), Core-Patch intakt (2026-03-06)
  - ✅ Celery: 8 separate Worker-Deployments (Lightweight Mode entfernt, Upstream PR #9014)
  - ✅ DEV: 16 Pods Running | TEST: 15 Pods Running (redeployed 2026-03-06)
  - ✅ PR-CI-Workflow (PR #4): helm-validate + build-backend + build-frontend (2026-03-06)
  - ✅ CI-Checks: helm-validate + build-backend + build-frontend (auf Push-to-main). Kein PR-Requirement (Solo-Dev, 2026-03-09 vereinfacht)
  - ✅ K8s v1.32 → v1.33 Upgrade (2026-03-08): v1.33.8, Flatcar 4459.2.1, Terraform apply 9m40s, DEV 16/16 + TEST 15/15 Pods Running
  - ✅ **Monitoring-Stack deployed** (2026-03-10): kube-prometheus-stack (Prometheus, Grafana, AlertManager, kube-state-metrics, node-exporter). 11 Pods in `monitoring` NS, 6 Targets, 20 Alert-Rules. Details: `docs/referenz/monitoring-konzept.md`
  - ✅ Health Probes aktiviert (2026-03-10): API httpGet `/health:8080`, Webserver tcpSocket `:3000`. DEV + TEST deployed. Lesson: Next.js hat keinen HTTP-Health-Endpoint.
  - ✅ Monitoring NetworkPolicies (2026-03-10): 7 Policies in `monitoring` NS + 3 Policies in `onyx-dev`/`onyx-test`
  - ✅ **Monitoring Exporter deployed** (2026-03-10): postgres_exporter v0.19.1 + redis_exporter v1.82.0. 4 Exporter-Pods, 4 Scrape-Targets UP, 11 neue Alert-Rules. PG + Redis Metriken fließen. Grafana Dashboards importiert (ID 14114 + 763).
  - ✅ Alerting: Microsoft Teams Webhook konfiguriert (2026-03-11). 20 Alert-Rules → Teams-Kanal. `send_resolved: true` für Entwarnung.
  - ✅ **Kostenoptimierung DEV/TEST** (2026-03-16): Resource Requests um 40-80% gesenkt, Node-Downgrade g1a.8d → g1a.4d (4 vCPU, 16 GB), TEST Scale-to-Zero CronJobs (Mo-Fr 08-18 UTC). Kosten: 868 → 585 EUR/Mo (-283 EUR). Details: `audit-output/kostenoptimierung-ergebnis.md`
- **Phase 3 (Auth):** ⏳ Blockiert — wartet auf Entra ID von VÖB
- **Phase 4 (Extensions):** Detailplan: `docs/referenz/ext-entwicklungsplan.md` | Lizenz-Abgrenzung: `docs/referenz/ee-foss-abgrenzung.md`
  - 4a: ✅ Extension Framework Basis (Config, Feature Flags, Router, Health Endpoint, Docker)
  - 4b: ✅ ext-branding — Whitelabel (Logo, App-Name, Login-Text, Greeting, Disclaimer, Popup, Consent). **DEV + TEST deployed und getestet (2026-03-08).** Helm Values + CI/CD build-arg konfiguriert. Favicon offen.
  - 4c: ✅ ext-token — LLM Usage Tracking + Limits. **DEV + TEST deployed (2026-03-09).** Branch auf main gemergt.
  - 4d: ✅ ext-prompts — Custom System Prompts. **DEV + TEST deployed und abgenommen (2026-03-09).** 29 Unit Tests, CORE #7 + #10 gepatcht.
  - 4e: ⏭️ ext-analytics — **ÜBERSPRUNGEN.** Funktionalität bereits in ext-token enthalten (Usage Dashboard, Timeline, Per-User, Per-Model). Kein Mehrwert als eigenes Modul.
  - 4f: ⏳ ext-rbac — Rollen + Gruppen. **BLOCKIERT** (Entra ID).
  - 4g: ⏳ ext-access — Document Access Control. **BLOCKIERT** (braucht RBAC).
  - **Hinweis**: Alle EE-Features werden custom nachgebaut (keine Onyx Enterprise-Lizenz vorhanden).
- **Phase 5-6:** Geplant (Testing, Production Go-Live)

## Nächster Schritt
**1. DNS-Eintraege (Leif/GlobVill) abwarten → 2. TLS/HTTPS PROD aktivieren → 3. NetworkPolicies PROD (vollstaendiges Set inkl. Basis-Policies) → 4. CI/CD Re-Run (gruener Lauf) → 5. M1-Abnahmeprotokoll.** Kostenoptimierung DEV/TEST abgeschlossen (2026-03-16): g1a.4d, 585 EUR/Mo. PROD App: 19 Pods, Health OK, LB `188.34.92.162`. Entra ID weiterhin blockiert.

## Blocker
| Blocker | Wartet auf | Impact |
|---------|-----------|--------|
| Entra ID Zugangsdaten | VÖB IT | Phase 3 |
| DNS PROD (A-Record + ACME-CNAME) | Leif (GlobVill), angefragt 2026-03-11 | HTTPS PROD |

## Erledigte Blocker
| Blocker | Gelöst | Datum |
|---------|--------|-------|
| TLS/HTTPS: ACME-Challenge CNAMEs bei GlobVill | ✅ Leif hat CNAMEs gesetzt, DEV HTTPS LIVE | 2026-03-09 |
| Cloudflare API Token Auth Error (10000) | ✅ Leif hat Permissions erweitert, ClusterIssuers READY | 2026-03-07 |
| Embedding-Wechsel blockiert (PR #7541) | ✅ Upstream PR #9005 — Search Settings Swap re-enabled | 2026-03-06 |
| LLM API Keys | ✅ StackIT AI Model Serving Token erstellt, GPT-OSS 120B konfiguriert | 2026-02-27 |
| SA `project.admin`-Rolle | ✅ Rolle erteilt | 2026-02-22 |
| StackIT Zugang | ✅ Zugang vorhanden | Feb 2026 |
