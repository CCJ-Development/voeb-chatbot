# Changelog

Alle wichtigen Änderungen am VÖB Service Chatbot werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added
- [Infra] **Monitoring-Stack deployed (kube-prometheus-stack)** (2026-03-10)
  - Self-Hosted: Prometheus + Grafana + AlertManager + kube-state-metrics + node-exporter (7 Pods)
  - Separater Helm Release `monitoring` in eigenem Namespace (nicht im Onyx Chart)
  - Prometheus: 30d Retention, 20Gi PVC, 30s Scrape-Intervall, 20 Targets (inkl. DEV + TEST API)
  - Grafana: port-forward only (kein externer Zugang, Enterprise Best Practice), admin/Passwort per K8s Secret
  - AlertManager: 20 Alert-Rules (9 Basis + 11 Exporter: APIDown, PodCrashLooping, HighErrorRate, DBPoolExhausted, HighSlowRequests, NodeMemoryPressure, NodeDiskPressure, VespaStorageFull, CertExpiringSoon, PGExporterDown, RedisExporterDown, PGConnectionsHigh, PGDeadlocks, PGHighRollbackRate, PGDatabaseGrowing, RedisMemoryHigh, RedisHighEvictions, RedisCacheHitRateLow, RedisRejectedConnections, PGCacheHitRateLow)
  - AlertManager: Microsoft Teams Webhook konfiguriert (2026-03-11), Alerts an Teams-Kanal inkl. Entwarnung (`send_resolved: true`)
  - Health Probes: API `httpGet /health:8080` + Webserver `tcpSocket :3000`
  - Lesson Learned: Next.js hat keinen `/api/health` Endpoint (Proxy laeuft ueber NGINX Ingress, nicht Next.js)
  - Lesson Learned: Onyx Service-Namen haben Suffix `-service` (`onyx-dev-api-service`, nicht `onyx-dev-api`)
  - 5 NetworkPolicies fuer `monitoring` NS (deny-all, dns, scrape-egress, intra-ns, k8s-api)
  - 1 NetworkPolicy fuer App-NS (allow-monitoring-scrape auf Port 8080)
  - Ressourcen: 1,1 vCPU Requests, 1,9 Gi RAM Requests (Cluster: 47% CPU, 32% RAM nach Monitoring)
  - StackIT-managed Komponenten deaktiviert: kubeEtcd, kubeScheduler, kubeControllerManager, kubeProxy
  - Values: `deployment/helm/values/values-monitoring.yaml`
  - Konzept: `docs/referenz/monitoring-konzept.md`
- [Feature] **Phase 4d: ext-prompts — Custom System Prompts** (2026-03-09, DEV + TEST deployed + abgenommen)
  - Backend: REST-API fuer globale System Prompts (5 Endpoints unter `/api/ext/prompts/`)
  - Datenbank: `ext_custom_prompts` Tabelle (Alembic Migration `c7f2e8a3d105`)
  - Core-Hook CORE #7 (prompt_utils.py): Prepend aktiver Prompts vor Base System Prompt
  - In-Memory-Cache mit TTL (60s), thread-safe, stale-fallback bei DB-Fehler
  - CRUD: Erstellen, Bearbeiten, Loeschen, Aktiv/Inaktiv-Toggle, Preview
  - Kategorien: Compliance, Tonalitaet, Kontext, Anweisungen, Allgemein
  - Prioritaets-Sortierung (niedrigerer Wert = wird zuerst eingefuegt)
  - Soft-Limits: 20 aktive Prompts / 50.000 Zeichen (Warnung, kein Hard-Block)
  - Frontend: Admin-Seite `/admin/ext-prompts` mit Prompt-Liste, Edit-Form, Preview
  - CORE #10 (AdminSidebar.tsx): "System Prompts"-Link mit SvgFileText-Icon
  - Feature Flag: `EXT_CUSTOM_PROMPTS_ENABLED` (AND-gated mit `EXT_ENABLED`)
  - Docker: `prompt_utils.py` Mount in `docker-compose.voeb.yml` (api_server + background)
  - Unit Tests: 29 Tests (Schemas, Service, Cache, Feature Flags, Edge Cases) — alle bestanden
- [Infra] **TLS/HTTPS fuer DEV + TEST aktiviert** (2026-03-09)
  - DEV: `https://dev.chatbot.voeb-service.de` (vorher `http://188.34.74.187`)
  - TEST: `https://test.chatbot.voeb-service.de` (vorher `http://188.34.118.201`)
  - Zertifikate: Let's Encrypt ECDSA P-384 (BSI TR-02102-2 konform), Issuer E8, auto-renewal
  - Protokoll: TLSv1.3 / TLS_AES_256_GCM_SHA384, HTTP/2
  - cert-manager DNS-01 via Cloudflare API, ACME-Challenge CNAME-Delegation ueber GlobVill
  - ClusterIssuers: `onyx-dev-letsencrypt` + `onyx-test-letsencrypt` (Production ACME)
  - Ingress: DEV (IngressClass `nginx`) + TEST (IngressClass `nginx-test`)
  - Helm Values: DOMAIN/WEB_DOMAIN auf FQDN+HTTPS, ingress.enabled=true
  - Fix: Image-Repos (StackIT Registry) fest in `values-common.yaml` hinterlegt (vorher nur CI/CD `--set`)
  - Fix: Redis-Passwort in `values-dev-secrets.yaml` + `values-test-secrets.yaml` ergaenzt
  - Runbook aktualisiert: `docs/runbooks/dns-tls-setup.md`
- [Feature] **Phase 4c: ext-token — LLM Usage Tracking + Token Limits** (2026-03-09)
  - Backend: REST-API fuer Token-Usage + Per-User Limits (6 Endpoints unter `/api/ext/token/`)
  - Datenbank: `ext_token_usage` + `ext_token_user_limit` Tabellen (Alembic Migration `b3e4a7d91f08`)
  - Core-Hook CORE #2 (multi_llm.py): 3 Hooks — Enforcement vor LLM-Call, Logging nach invoke() + stream()
  - Per-User Token-Limits: Budget in Tausenden, rolling Zeitfenster, 429 mit Reset-Zeitpunkt
  - Usage-Dashboard: Aggregation nach User/Modell, Zeitreihen (Stunde/Tag), Per-User Breakdown
  - Frontend: Admin-Seite `/admin/ext-token` mit 4 Tabs (Overview, Timeline, Per-User, User Limits)
  - CORE #10 (AdminSidebar.tsx): "Token Usage"-Link mit SvgActivity-Icon
  - Feature Flag: `EXT_TOKEN_LIMITS_ENABLED` (AND-gated mit `EXT_ENABLED`)
  - Unit Tests: Schemas, Logging (fire-and-forget), Enforcement (429), Null-User
- [Feature] **Phase 4b: ext-branding — Whitelabel Module** (2026-03-08)
  - Backend: REST-API fuer Branding-Konfiguration (5 Endpoints: GET/PUT Config + Logo)
  - Datenbank: `ext_branding_config` Tabelle (Alembic Migration `ff7273065d0d`)
  - Konfigurierbar zur Laufzeit: App-Name, Logo (PNG/JPEG, max 2MB), Login-Text, Greeting, Disclaimer, Popup, Consent Screen
  - Core-Patches: CORE #6 (constants.ts, 1 Zeile), CORE #8 (LoginText.tsx), CORE #9 (AuthFlowContainer.tsx)
  - Public Endpoints ohne Auth (Login-Seite braucht Branding vor Login)
  - FOSS-Frontend liest automatisch von `/enterprise-settings` — kein Frontend-Patch fuer Logo/Sidebar noetig
  - "Powered by Onyx" entfernt via `NEXT_PUBLIC_DO_NOT_USE_TOGGLE_OFF_DANSWER_POWERED=true`
  - 21 Unit-Tests (Schema-Validierung, Magic-Byte-Detection, Defaults, Logo-Constraints) — alle bestanden
  - Endpoint-Tests: 5/5 funktional, 3/3 Validierung, 2/2 Routing (direkt + nginx)
  - Feature Flag: `EXT_BRANDING_ENABLED` (AND-gated mit `EXT_ENABLED`)
  - Docker: `COPY ./ext /app/ext` in Dockerfile (ext-Code im Image), `main.py` Mount in `docker-compose.voeb.yml`
  - Docker: `NEXT_PUBLIC_DO_NOT_USE_TOGGLE_OFF_DANSWER_POWERED=true` in `.env` (Build-Time, Web-Server Rebuild noetig)
  - CI/CD: `NEXT_PUBLIC_DO_NOT_USE_TOGGLE_OFF_DANSWER_POWERED=true` als Docker build-arg in `stackit-deploy.yml` (Next.js baut NEXT_PUBLIC_* zur Build-Zeit ein)
  - Helm: `EXT_ENABLED` + `EXT_BRANDING_ENABLED` in `values-common.yaml` configMap (Backend Feature Flags)
  - Deployment: DEV + TEST deployed und getestet (2026-03-08), Branding-Konfiguration funktional
  - `env.template` erweitert: Alle EXT_-Feature Flags dokumentiert
  - CORE #10 (AdminSidebar.tsx): "Upgrade Plan"/Billing ausgeblendet, "Branding"-Link unter Settings eingefuegt
  - `.claude/hooks/protect-onyx-files.sh` erweitert: 7 → 10 erlaubte Core-Dateien (CORE #8, #9, #10)
  - 8 Core-Originals + Patches in `backend/ext/_core_originals/` (4 Paare: constants.ts, LoginText.tsx, AuthFlowContainer.tsx, AdminSidebar.tsx)
  - Admin-UI Route aktiv unter `/admin/ext-branding` (Sidebar-Link + Next.js App Router)
  - Modulspezifikation: `docs/technisches-feinkonzept/ext-branding.md` v1.0
- [Config] **LLM-Modelle: 4 Chat-Modelle + Embedding-Wechsel auf TEST** (2026-03-08)
  - Chat: 4 Modelle in 1 Provider konfiguriert (GPT-OSS 120B, Qwen3-VL 235B, Llama 3.3 70B, Llama 3.1 8B)
  - Model-IDs mit StackIT-Doku verifiziert (3 Korrekturen: Llama 3.3, Mistral-Nemo, Llama 3.1 neu)
  - Embedding TEST: Wechsel von nomic-embed-text-v1 auf `Qwen/Qwen3-VL-Embedding-8B` (4096 Dim, multilingual)
  - Embedding DEV: nomic-embed-text-v1 weiterhin aktiv
  - Nicht kompatibel mit Onyx: Gemma 3 27B + Mistral-Nemo 12B (kein Tool Calling auf StackIT vLLM)
  - Runbook aktualisiert: `docs/runbooks/llm-konfiguration.md`
- [Infra] **Kubernetes v1.32 → v1.33 Upgrade** (2026-03-08)
  - Terraform apply erfolgreich (9m40s), 0 added, 1 changed, 0 destroyed
  - Nodes: v1.33.8, Flatcar 4459.2.1 (beide supported, vorherige Versionen deprecated)
  - DEV 16/16 Pods Running, TEST 15/15 Pods Running, Health OK
- [Infra] **Node-Upgrade g1a.4d → g1a.8d** (2026-03-06)
  - ADR-005: 8 vCPU, 32 GB RAM, 100 GB Disk pro Node (vorher: 4 vCPU, 16 GB RAM, 50 GB)
  - Terraform apply erfolgreich (10m11s), 0 added, 1 changed, 0 destroyed
  - Kosten DEV+TEST: ~868 EUR/Mo (vorher: ~426 EUR/Mo)
  - Grund: 8 separate Celery-Worker (Standard Mode) benoetigen mehr Ressourcen
- [Infra] **8 Celery-Worker aktiviert (Lightweight Mode entfernt)** (2026-03-06)
  - Upstream PR #9014 entfernt Lightweight Background Worker Mode
  - 8 separate Celery-Deployments: beat, primary, light, heavy, docfetching, docprocessing, monitoring, user-file-processing
  - DEV: 16 Pods Running | TEST: 15 Pods Running
  - Resource-Strategie: Reduzierte Requests + hohe Limits (Scheduling-freundlich)
- [Infra] **Upstream-Merge: 100 Commits** (2026-03-06)
  - Merged via Branch `chore/upstream-sync-2026-03-06` + PR #3 (Enterprise-Workflow)
  - 1 Konflikt (AGENTS.md, --ours), Core-Patch main.py auto-merged, ext-Hook intakt
  - Wichtige Upstream-Aenderungen: PR #9005 (Embedding-Swap re-enabled), PR #9014 (Lightweight entfernt), PR #9001 (SCIM Token Management)
- [CI/CD] **PR-Validierung vor Merge** (2026-03-06)
  - `.github/workflows/ci-checks.yml` (ehem. pr-checks.yml) mit 3 parallelen Jobs: helm-validate, build-backend, build-frontend
  - Merged via PR #4
- [Infra] **Branch Protection auf main aktiviert** (2026-03-06)
  - PR required (kein Direct Push), 3 Required Status Checks. Review-Requirement entfernt (Solo-Dev, 2026-03-07)
  - 3 Required Status Checks: helm-validate, build-backend, build-frontend
  - Force Push + Branch Delete blockiert, enforce_admins: false (Notfall-Override)
- [Docs] **Change & Release Management Dokumentation** (2026-03-05)
  - M-CM-1: Change-Management-Abschnitt im Betriebskonzept (Branching-Strategie, Promotion-Pfad, Änderungskategorien, Freigabestufen)
  - M-CM-2: 4-Augen-Prinzip dokumentiert (Betriebskonzept + Sicherheitskonzept, BAIT Kap. 8.6, Interims-Lösung + geplante GitHub Protection)
  - M-CM-3: Zugriffsmatrix im Sicherheitskonzept (GitHub, Kubernetes, Datenbanken, IaC)
  - M-CM-4: Release-Management-Prozess (Versionierung, Release-Checkliste, Hotfix-Prozess)
  - M-CM-5: Rollback-Runbook (`docs/runbooks/rollback-verfahren.md`) — Entscheidungsbaum, Helm/DB-Rollback, Kommunikation, Post-Mortem-Vorlage
  - M-CM-6: CI/CD-Dokumentation vervollständigt (paths-ignore, Concurrency, SHA-Pinning, Smoke Tests, Model Server Pinning, Secret-Injection)
  - Betriebskonzept v0.4, Sicherheitskonzept v0.4

### Security
- [Infra] **SEC-06: `privileged: true` entfernt** (2026-03-08)
  - Betroffen: Celery (8 Worker), Model Server (inference + index), Vespa — liefen als `privileged: true` + `runAsUser: 0`
  - Fix: `privileged: false` in `values-common.yaml` für `celery_shared`, `inferenceCapability`, `indexCapability`, `vespa`
  - BSI SYS.1.6.A10: "Privileged Mode SOLLTE NICHT verwendet werden"
  - Helm Template validiert: 11x `privileged: false`, 0x `true` (DEV + TEST)
  - Phase 2 (vor PROD): `runAsNonRoot: true` + `runAsUser: 1001`
- [Infra] **SEC-02/04/05 zurückgestellt, SEC-07 verifiziert** (2026-03-08)
  - SEC-02 (Node Affinity): P1 → Zurückgestellt — ADR-004: "Kein Dedicated-Node-Affinity nötig", bestehende Isolation ausreichend
  - SEC-04 (Remote State): P1 → P3 — Solo-Dev, FileVault, gitignored. Quick Win: `chmod 600` auf State-Dateien
  - SEC-05 (Kubeconfigs): P1 → P3 — PROD = eigener Cluster (ADR-004), opportunistisch bei Renewal
  - SEC-07 (Encryption-at-Rest): Verifiziert — StackIT Default (AES-256 PG, SSE S3)
- [Infra] **C5/SEC-03: NetworkPolicies auf DEV + TEST applied** (2026-03-05)
  - 5 Policies: default-deny, DNS-egress, intra-namespace, external-ingress-nginx, external-egress
  - Zero-Trust Baseline: DEV ↔ TEST Cross-Namespace-Isolation verifiziert
  - Fix: DNS-Port 8053 (StackIT/Gardener CoreDNS targetPort nach DNAT)
  - Fix: nginx-Label `ingress-nginx` → `nginx` (Onyx Helm Chart)
  - Audit-Dokumentation: `docs/audit/networkpolicy-analyse.md`
  - Apply/Rollback-Skripte: `deployment/k8s/network-policies/`
- [Infra] **C6: DB_READONLY_PASSWORD in K8s Secret verschoben** (2026-03-05)
  - Passwort war im Klartext in K8s ConfigMap — jetzt über `auth.dbreadonly` als K8s Secret (identisch zu postgresql/redis/objectstorage)
  - CI/CD Workflow in allen 3 Deploy-Jobs angepasst
- [Infra] **H8: Security-Header auf nginx** (2026-03-05)
  - `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` via `http-snippet` in values-common.yaml
- [CI/CD] **H11: image_tag Script Injection gefixt** (2026-03-05)
  - `${{ inputs.image_tag }}` → `env:` Variable (GitHub Security Lab Best Practice) + Docker-Tag-Regex-Validierung
- [Docs] **Cloud-Infrastruktur-Audit** (2026-03-04)
  - 5 Opus-Agenten: 10 CRITICAL, 18 HIGH, ~20 MEDIUM, ~12 LOW Findings
  - 5 Findings verifiziert durch separate Code-Analyse-Agenten
  - Audit-Dokument: `docs/audit/cloud-infrastruktur-audit-2026-03-04.md`
- [Infra] **SEC-01: PostgreSQL ACL eingeschränkt** (2026-03-03)
  - PG ACL von `0.0.0.0/0` auf Cluster-Egress-IP `188.34.93.194/32` + Admin-IP eingeschränkt
  - Default `pg_acl` in beiden Terraform-Modulen entfernt → erzwingt explizite Angabe pro Environment
  - Terraform Credentials-Handling: `credentials.json` Wrapper, `chmod 600`, `.envrc` in `.gitignore`
- [Security] **GitHub Actions SHA-Pinning** (2026-03-02)
  - Alle 6 Actions auf Commit-SHA fixiert statt Major-Version-Tags (Supply-Chain-Schutz)
  - `actions/checkout`, `docker/login-action`, `docker/setup-buildx-action`, `docker/build-push-action`, `azure/setup-helm`, `azure/setup-kubectl`
- [Security] **Least-Privilege Permissions** (2026-03-02)
  - `permissions: contents: read` — Workflow hat nur Lesezugriff auf Repo
- [Security] **Redis-Passwort aus Git entfernt** (2026-03-02)
  - War hardcoded in `values-dev.yaml` → jetzt über GitHub Secret `REDIS_PASSWORD`
- [Security] **Concurrency Control** (2026-03-02)
  - Max 1 Deploy pro Environment gleichzeitig, verhindert Race Conditions
- [Security] **Model Server Version gepinnt** (2026-03-02)
  - `v2.9.8` statt `:latest` — reproduzierbare Deployments

### Added
- [Infra] **TEST-Umgebung LIVE** (2026-03-03)
  - Node Pool auf 2 Nodes skaliert (DEV + TEST im shared Cluster)
  - PG Flex `vob-test` + Bucket `vob-test` provisioniert
  - Namespace `onyx-test`, GitHub Environment `test` + 5 Secrets
  - Helm Release `onyx-test`: 9 Pods Running (historisch, jetzt 15 Pods), Health Check OK
  - Erreichbar unter `https://test.chatbot.voeb-service.de` (HTTPS seit 2026-03-09)
  - Eigene IngressClass `nginx-test` (Conflict mit DEV vermieden)
  - Separate S3-Credentials für TEST erstellt (Enterprise-Trennung)
- [Infra] **TEST-Umgebung vorbereitet** (2026-03-02)
  - ADR-004: Umgebungstrennung DEV/TEST/PROD (Architekturentscheidung dokumentiert)
  - Terraform: Node Pool `devtest` auf 2 Nodes skaliert (1 pro Environment)
  - Terraform: Neues Modul `stackit-data` (PG + Bucket ohne Cluster) für TEST
  - Terraform: `environments/test/` mit eigener PG Flex Instanz + Bucket `vob-test`
  - Helm: `values-test.yaml` (analog DEV, eigene Credentials/Bucket)
  - CI/CD: Smoke Test für `deploy-test` Job ergänzt
  - Implementierungsplan: Phase 7 (TEST-Umgebung) mit 9 Schritten + Validierungstabelle
  - Infrastruktur-Referenz: Environments-Tabelle + Node Pool aktualisiert
- [Infra] **CI/CD Pipeline aktiviert** (2026-03-02)
  - GitHub Secrets konfiguriert (3 global + 4 per DEV Environment)
  - Container Registry Robot Account `github-ci` für CI/CD erstellt
  - Workflow `stackit-deploy.yml` überarbeitet: Secrets-Injection, Registry-Projektname, kubectl für alle Environments
  - Image Pull Secret auf Cluster mit Robot Account Credentials aktualisiert
  - Dokumentation: `docs/referenz/stackit-container-registry.md` (Konzepte, Auth, Secret-Mapping)
  - Implementierungsplan Phase 1.4 + 5 aktualisiert
- [Infra] **Phase 2: StackIT DEV-Infrastruktur (in Arbeit)**
  - StackIT CLI Setup + Service Account `voeb-terraform` mit API Key
  - Container Registry im Portal aktiviert
  - Terraform `init` + `plan` erfolgreich (SKE Cluster, PostgreSQL Flex, Object Storage)
  - Terraform-Code Fix: `default_region` für Provider v0.80+
  - Runbook-Struktur `docs/runbooks/` mit Index + erstem Runbook (Projekt-Setup)
  - Implementierungsplan aktualisiert mit verifizierten Befehlen
  - Blockiert: SA benötigt `project.admin`-Rolle (wartet auf Org-Admin)
- [Infra] **LLM-Konfiguration (StackIT AI Model Serving)** (2026-02-27)
  - GPT-OSS 120B als primäres Chat-Modell konfiguriert und verifiziert
  - Qwen3-VL 235B als zweites Chat-Modell konfiguriert und verifiziert
  - OpenAI-kompatible API via StackIT (Daten bleiben in DE)
  - Embedding-Modell: nomic-embed-text-v1 aktiv. Wechsel auf Qwen3-VL-Embedding 8B moeglich (Blocker aufgehoben, Upstream PR #9005).
- [Feature] **Phase 4a: Extension Framework Basis**
  - `backend/ext/` Paketstruktur mit `__init__.py`, `config.py`, `routers/`
  - Feature Flag System: `EXT_ENABLED` Master-Switch + 6 Modul-Flags (AND-gated, alle default `false`)
  - Health Endpoint `GET /api/ext/health` (authentifiziert, zeigt Status aller Module)
  - Router-Registration Hook in `backend/onyx/main.py` (einzige Core-Datei-Änderung)
  - Docker-Deployment: `docker-compose.voeb.yml` (Dev) + `Dockerfile.voeb` (Production)
  - Modulspezifikation `docs/technisches-feinkonzept/ext-framework.md`
  - 10 Unit-Tests (5× Config Flags, 5× Health Endpoint) — alle bestanden
- [Feature] Dokumentation Repository initial setup
  - README mit Dokumentationsstruktur
  - Technisches Feinkonzept Template
  - Sicherheitskonzept (Entwurf)
  - Testkonzept mit Testfallkatalog
  - Architecture Decision Records (ADR-001 bis ADR-003)
  - Betriebskonzept (Entwurf)
  - Abnahme-Protokoll und Meilensteinplan
  - Changelog

### Changed
- [Documentation] Alle Dokumente in Deutsch verfasst (Banking-Standard)
- [Infra] **CI/CD Pipeline auf Enterprise-Niveau gehärtet** (2026-03-02)
  - Backend + Frontend Build parallel (~8 Min statt ~38 Min sequentiell)
  - Model Server Build entfernt (nutzt Upstream Docker Hub Image)
  - Smoke Test nach Deploy (`/api/health` mit 120s Timeout)
  - `--atomic` für TEST/PROD (automatischer Rollback bei Fehler)
  - `--history-max 5` (Helm Release-Cleanup)
  - Fehlerbehandlung: `|| true` entfernt, echtes Error-Reporting mit `kubectl describe` + Logs
  - Verify-Steps mit `if: always()` (Pod-Status auch bei Fehler sichtbar)
  - Kubeconfig-Ablauf im Header dokumentiert (2026-05-28)
  - Runbook: `docs/runbooks/ci-cd-pipeline.md`

### Fixed
- [Bugfix] Core-Datei-Pfade in `.claude/rules/` und `.claude/hooks/` korrigiert (4 von 7 Pfade waren falsch)
- [Bugfix] **CI/CD Pipeline Helm-Fixes** (2026-03-02)
  - Run #1 fehlgeschlagen: `helm dependency build`-Step fehlte im Deploy-Job → Fix: `f3a22017f`
  - Run #2 fehlgeschlagen: Helm Repos nicht auf CI-Runner registriert → Fix: `64c9c7aca`
  - `helm repo add` für alle 6 Chart-Dependencies in allen 3 Deploy-Jobs (dev/test/prod)
  - 21 Onyx-Upstream-Workflows deaktiviert (irrelevant für Fork, erzeugten Fehler-E-Mails)
- [Bugfix] **API-Server EE-Crash behoben** (2026-03-02)
  - `LICENSE_ENFORCEMENT_ENABLED` hat in Onyx FOSS den Default `"true"` — aktiviert EE-Code-Pfade (`onyx.server.tenants`), die im FOSS-Fork nicht existieren → `ModuleNotFoundError` → CrashLoopBackOff
  - Fix: `LICENSE_ENFORCEMENT_ENABLED: "false"` explizit in `values-common.yaml` gesetzt
- [Bugfix] **Model Server ImagePullBackOff behoben** (2026-03-02)
  - Eigenes Image in StackIT Registry konnte nicht gepullt werden
  - Fix: Upstream Docker Hub Image (`docker.io/onyxdotapp/onyx-model-server:v2.9.8`) statt eigenem Build
- [Bugfix] **Helm Image-Tag-Konstruktion** (2026-03-02)
  - Repository und Tag wurden zusammen gesetzt → Helm erzeugte `repo:latest:sha` (ungültig)
  - Fix: `image.repository` und `image.tag` getrennt per `--set`
- [Bugfix] **Recreate-Strategie für Single-Node DEV** (2026-03-02)
  - RollingUpdate scheiterte auf g1a.4d (4 vCPU, inzwischen auf g1a.8d upgraded) — nicht genug CPU für alte + neue Pods gleichzeitig
  - Fix: kubectl-Patch auf Recreate-Strategie nach Helm Deploy

---

## [1.0.0] – Documentation Release

### Added
- [Documentation] Initial dokumentation package für Banking-Sektor
  - Umfassendes Technisches Feinkonzept mit Modulspezifikation-Template
  - Sicherheitskonzept mit DSGVO, BAIT, und Banking-Anforderungen
  - Testkonzept mit Testpyramide und 11 Beispiel-Testfälle
  - 3 Architecture Decision Records (Onyx FOSS, Extension Architektur, StackIT)
  - Betriebskonzept mit Deployment, Monitoring, Backup-Strategie
  - Abnahme-Protokoll-Template und Meilensteinplan (M1-M6)
  - Changelog für Versionsverfolgung

### Status
- **Dokumentation**: 100% initial draft
- **Ready for**: Review-Prozess mit Stakeholdern
- **Next Step**: Finalisierung nach Feedback

---

## Versionierungsschema

Dieses Projekt folgt [Semantic Versioning](https://semver.org/):

- **MAJOR**: Bedeutende Änderungen, Breaking Changes
- **MINOR**: Neue Features, rückwärts-kompatibel
- **PATCH**: Bug Fixes, rückwärts-kompatibel

Beispiel: `1.2.3`
- `1` = MAJOR (Breaking changes seit v0)
- `2` = MINOR (2 neue Features seit v1.0)
- `3` = PATCH (3 Bugfixes seit v1.2)

---

## Dokumentations-Releases (geplant)

### Phase 1 – Dokumentation
- [x] Initial Documentation Setup
- [ ] Stakeholder Feedback Collection
- [ ] Dokumentation finalisieren nach Feedback

### Phase 2 – Infrastruktur (M1)
- [x] Infrastruktur Go-Live (DEV 2026-02-27, TEST 2026-03-03)
- [ ] Abnahmeprotokoll unterzeichnet
- [ ] Release Notes v1.0.0-infra

### Phase 3 – Authentifizierung (M2)
- [ ] Auth Module Release Notes
- [ ] Updated Dokumentation nach Implementation

### Phase 4 – Extensions (M3-M4)
- [x] Branding/Whitelabel Release (DEV+TEST deployed 2026-03-08)
- [x] Token Limits Release (DEV+TEST deployed 2026-03-09)
- [x] Custom Prompts Release (implementiert 2026-03-09, Deploy offen)
- [ ] Analytics Release
- [ ] RBAC Release (blockiert: Entra ID)
- [ ] Access Control Release (blockiert: RBAC)

### Phase 5 – Go-Live Readiness (M5)
- [ ] Final Testing Release Notes
- [ ] Production Runbooks

### Phase 6 – Production (M6)
- [ ] Production Release v1.0.0
- [ ] Go-Live Announcement

---

## Dokumentations-Versionen

### v0.1 – Initial Draft
- Alle Basis-Dokumente erstellt
- Status: Entwurf
- Zielgruppe: Interne Review

### v0.5 – Stakeholder Review (geplant)
- Feedback von VÖB und CCJ eingearbeitet
- Status: In Überarbeitung

### v1.0 – Final Release (geplant)
- Alle Dokumente finalisiert und freigegeben
- Status: Produktionsreif

---

## Bekannte Probleme und Einschränkungen

### [ENTWURF]-Marker

Viele Abschnitte sind mit `[ENTWURF]` oder `[TBD]` gekennzeichnet. Diese werden nach finaler Konfiguration der Infrastruktur ergänzt:

- Sicherheitskonzept: Infrastruktur-Details (Secrets-Management, WAF, etc.)
- Betriebskonzept: StackIT-spezifische Konfiguration
- Testkonzept: Testumgebungen nach Setup

### Dependencies

Dokumentation hängt ab von:
- StackIT Account und Konfiguration
- Entra ID Setup durch VÖB
- LLM Provider: StackIT AI Model Serving (GPT-OSS 120B + Qwen3-VL 235B konfiguriert)

---

## Zugehörige Dateien und Verweise

### Dokumentations-Struktur
```
docs/
├── README.md                                    (Main Index)
├── CHANGELOG.md                                 (This File)
├── sicherheitskonzept.md                        (Security Concept)
├── testkonzept.md                               (Test Strategy)
├── betriebskonzept.md                           (Operations Concept)
├── entra-id-kundenfragen.md                     (Entra ID Fragenkatalog)
├── technisches-feinkonzept/
│   ├── template-modulspezifikation.md           (Template)
│   ├── ext-framework.md                         (Extension Framework Spec)
│   ├── ext-branding.md                          (Whitelabel Branding Spec)
│   ├── ext-token.md                             (Token Limits + Usage Tracking Spec)
│   └── ext-custom-prompts.md                    (Custom System Prompts Spec)
├── adr/
│   ├── adr-001-onyx-foss-als-basis.md           (Platform Choice)
│   ├── adr-002-extension-architektur.md         (Extension Architecture)
│   ├── adr-003-stackit-als-cloud-provider.md    (Cloud Provider)
│   ├── adr-004-umgebungstrennung-dev-test-prod.md (Environment Separation)
│   └── adr-005-node-upgrade-g1a8d.md              (Node-Upgrade g1a.8d)
├── abnahme/
│   ├── abnahmeprotokoll-template.md             (Acceptance Protocol)
│   ├── abnahmeprotokoll-m1.md                   (M1 Abnahmeprotokoll)
│   └── meilensteinplan.md                       (Milestone Plan)
├── runbooks/
│   ├── README.md                                (Runbook Index)
│   ├── stackit-projekt-setup.md                 (StackIT Setup)
│   ├── stackit-postgresql.md                    (PostgreSQL Setup)
│   ├── helm-deploy.md                           (Helm Deploy)
│   ├── ci-cd-pipeline.md                        (CI/CD Pipeline)
│   ├── dns-tls-setup.md                         (DNS/TLS Setup)
│   ├── llm-konfiguration.md                     (LLM-Konfiguration)
│   └── rollback-verfahren.md                    (Rollback-Verfahren)
├── audit/
│   ├── cloud-infrastruktur-audit-2026-03-04.md  (Security Audit)
│   └── networkpolicy-analyse.md                 (NetworkPolicy-Analyse)
└── referenz/
    ├── stackit-implementierungsplan.md          (DEV+TEST Step-by-Step)
    ├── stackit-infrastruktur.md                 (Infra Specs + Sizing)
    ├── stackit-container-registry.md            (Container Registry)
    ├── ee-foss-abgrenzung.md                    (EE/FOSS-Lizenzabgrenzung)
    ├── ext-entwicklungsplan.md                  (Extension-Module Reihenfolge)
    ├── rbac-rollenmodell.md                     (RBAC Rollenmodell-Entwurf)
    ├── compliance-research.md                   (Compliance-Research DSGVO/BAIT/BSI)
    └── monitoring-konzept.md                   (Monitoring Stack + Deployment-Protokoll)
```

---

## Mitwirkende

- **CCJ**: Projektleitung und Governance
- **StackIT**: Cloud-Infrastruktur
- **VÖB**: Anforderungen und Abnahme

---

## Lizenz

Diese Dokumentation ist Teil des VÖB Service Chatbot Projekts.

- **Lizenz für Dokumentation**: CC BY-SA 4.0 (Attribution-ShareAlike)
- **Lizenz für Code**: MIT (siehe Onyx FOSS Base)

---

## Kontakt und Support

Bei Fragen zur Dokumentation:

- **CCJ Projektleitung**: [AUSSTEHEND]
- **CCJ Technical Lead**: Nikolaj Ivanov

---

## Versionshistorie dieser Datei

| Version | Datum | Autor | Änderungen |
|---------|-------|-------|-----------|
| 0.1 | [AUSSTEHEND] | [AUSSTEHEND] | Initial Release |

---

**Letzte Aktualisierung**: 2026-03-08
**Wartete durch**: [AUSSTEHEND]
**Nächste Überprüfung**: [AUSSTEHEND]
