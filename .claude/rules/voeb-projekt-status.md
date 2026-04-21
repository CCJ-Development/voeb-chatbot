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
  - ✅ Helm Release `onyx-dev`: Alle 16 Pods (8 Celery-Worker, Standard Mode) 1/1 Running (Helm-Neuinstallation 2026-03-18 nach Upstream-Sync)
  - ✅ DNS DEV A-Record aktualisiert auf `188.34.118.222` durch Leif/GlobVill (verifiziert 2026-03-22). DEV HTTPS LIVE.
  - ✅ Runbooks: stackit-projekt-setup.md, stackit-postgresql.md, helm-deploy.md
  - ✅ CI/CD Pipeline: Produktionsreif (2026-03-02) — Parallel-Build ~8 Min, SHA-gepinnte Actions, Smoke Tests, Concurrency
  - ✅ Upstream-Workflows: 21 Onyx-Workflows deaktiviert, nur StackIT Deploy + Upstream Check aktiv
  - ✅ CI/CD Run #5 (ea70a11): 10 Min, alle 10 Pods Running (historisch, jetzt 16 Pods), Health Check OK
  - ✅ EE-Crash gelöst: `LICENSE_ENFORCEMENT_ENABLED: "false"` in values-common.yaml
  - ✅ DNS: A-Records gesetzt (2026-03-05): `dev.chatbot.voeb-service.de` → ~~`188.34.74.187`~~ `188.34.118.222` (Update angefragt 2026-03-18), `test.chatbot.voeb-service.de` → `188.34.118.201`
  - ✅ DNS: Cloudflare Proxy auf DNS-only umgestellt und verifiziert (2026-03-05)
  - ✅ TLS/HTTPS DEV: **LIVE** (2026-03-09) — `https://dev.chatbot.voeb-service.de`, Let's Encrypt ECDSA P-384, TLSv1.3, HTTP/2. cert-manager DNS-01 via Cloudflare, ACME-Challenge CNAME-Delegation ueber GlobVill. Details: docs/runbooks/dns-tls-setup.md
  - ✅ TLS/HTTPS TEST: **LIVE** (2026-03-09) — `https://test.chatbot.voeb-service.de`, Let's Encrypt ECDSA P-384, TLSv1.3, HTTP/2. Analog DEV, IngressClass `nginx-test`
  - ✅ LLM: 4 Chat-Modelle konfiguriert (GPT-OSS 120B, Qwen3-VL 235B, Llama 3.3 70B, Llama 3.1 8B). Gemma 3 + Mistral-Nemo nicht kompatibel (kein Tool Calling auf StackIT).
  - ✅ Embedding DEV: Qwen3-VL-Embedding 8B aktiv (umgestellt 2026-03-12).
  - 📋 Scope: DEV live, TEST dauerhaft heruntergefahren (seit 2026-03-19), PROD **HTTPS LIVE** (2026-03-17).
- **Phase 2 PROD:** ✅ **PROD AKTUALISIERT** (2026-03-22, Helm Rev 4)
  - ✅ Terraform apply: SKE `vob-prod` (eigener Cluster, ADR-004) + PG Flex 4.8 HA (3-Node) + Bucket `vob-prod`
  - ✅ K8s v1.33.9, Flatcar 4459.2.3, 2x g1a.8d (8 vCPU, 32 GB RAM)
  - ✅ cert-manager v1.19.4 + ClusterIssuer `onyx-prod-letsencrypt` READY
  - ✅ Redis Operator + Image Pull Secret in `onyx-prod`
  - ✅ GitHub Environment `prod` + Required Reviewer + 7 Secrets (inkl. OPENSEARCH_PASSWORD)
  - ✅ Helm Release `onyx-prod`: **20 Pods Running** (2×API HA, 2×Web HA, 8 Celery-Worker, Vespa Zombie, **OpenSearch**, Redis, 2×Model, NGINX). **Chart 0.4.44, Rev 18** (aktualisiert 2026-04-17 mit Sync #5).
  - ✅ **Sync #5 + Monitoring-Optimierung PROD: LIVE** (2026-04-17) — 344 Upstream-Commits, Deep-Health-Endpoint, Readiness-Probe auf `/ext/health/deep`, Alert Fatigue Fix offiziell via Helm (Monitoring Rev 6), PostgresDown Alert, `backend/ext/auth.py` Wrapper, Core #15 (useSettings.ts).
  - ✅ **OOM-Fix PROD** (2026-04-17) — API-Server 2→4Gi, docfetching/docprocessing 4→2Gi. OOMKilled-Restart-Loop (9+7) gestoppt.
  - ✅ **Alembic-Chain-Recovery PROD** (2026-04-17) — 11 Upstream-Migrationen sauber nachgezogen (689433b0d8de→503883791c39), alembic_version wieder auf `d8a1b2c3e4f5`. 2 neue Default-Gruppen ("Admin" id 54, "Basic" id 55) erstellt, 91/95 User in "Basic" (VÖB-Gruppen unveraendert).
  - ✅ **OpenSearch PROD: LIVE** (2026-03-22) — Primary Document Index, Retrieval aktiviert, Cluster yellow (erwartet bei Single-Node), sicheres Passwort (nicht Chart-Default)
  - ✅ **Vespa: Zombie-Mode** (2026-03-22) — 100m/512Mi Requests, 4Gi Limit. Nur fuer Celery Readiness Check.
  - ✅ **ext-i18n PROD: LIVE** (2026-03-22) — ~250 Strings Deutsch, ~95% user-facing UI
  - ✅ API Health OK: `https://chatbot.voeb-service.de/api/health` → 200
  - ✅ SEC-06 Phase 2: `runAsNonRoot: true` aktiv (Vespa = dokumentierte Ausnahme)
  - ✅ PG ACL: Egress `188.34.73.72/32` + Admin
  - ✅ Maintenance-Window: 03:00-05:00 UTC (O8, eigenes Fenster)
  - ✅ Kubeconfig gueltig bis 2026-06-22 (90 Tage)
  - ✅ DNS: A-Record + ACME-CNAME gesetzt durch Leif/GlobVill (2026-03-17)
  - ✅ **TLS/HTTPS PROD: LIVE** (2026-03-17) — `https://chatbot.voeb-service.de`, Let's Encrypt ECDSA P-384, TLSv1.3, HTTP/2, HSTS 1 Jahr
  - ✅ SEC-09: Rate-Limiting 10r/s, Upload-Limit 20 MB, MAX_FILE_SIZE_BYTES Backend-Limit
  - ✅ **Monitoring PROD erweitert** (2026-03-25/26): 14 Pods (Prometheus, Grafana, AlertManager, kube-state-metrics, 2x node-exporter, PG/Redis/OpenSearch/Blackbox Exporter, Operator, Loki, 2x Promtail). 25 Targets (alle UP). 50 VÖB Rules (10 Recording + 40 Alerting). **6 Grafana Dashboards** (PG, Redis, SLO, Audit-Log, Token-Usage, **Analytics Overview**). **4 Datasources** (Prometheus, Alertmanager, Loki, **PostgreSQL**). ext-token Prometheus Counter (prompt/completion/requests pro Modell). Teams PROD-Kanal. Loki Log-Aggregation (30d Retention, 20Gi). Blackbox Probes fuer 4 externe Deps (LLM, OIDC, S3, PROD Health). **14 NetworkPolicies** monitoring NS + 6 cert-manager NS.
  - ✅ **NetworkPolicies onyx-prod: LIVE** (2026-03-24) — 7 Policies (default-deny, DNS, intra-NS, NGINX ingress, external egress, monitoring scrape, Redis exporter). Zero-Trust Baseline. Verifiziert: Health OK, externer Zugriff OK.
  - ✅ **Grafana PG-Datasource** (2026-03-26) — db_readonly_user mit SELECT-Grants (DEV + PROD), NetworkPolicy `14-allow-grafana-pg-egress`, Sidecar-Provisioning. Analytics Dashboard (19 SQL-Panels) live.
  - ✅ CI/CD: `--set opensearch_admin_password` ergaenzt (2026-03-22), GitHub Secret `OPENSEARCH_PASSWORD` gesetzt
  - ✅ **Embedding PROD: Qwen3-VL-Embedding 8B** (2026-03-24) — LiteLLM Provider, 4096 Dimensionen, Re-Index abgeschlossen
  - ✅ **LLM PROD konfiguriert** (2026-03-24) — 3 Chat-Modelle (GPT-OSS 120B, Qwen3-VL 235B, Llama 3.3 70B). Core #13 Fix (api_key + api_base + default_model_name), Upstream-Bug onyx-dot-app/onyx#9592
  - ✅ **OpenSearch lowercase Fix** (2026-03-24) — Core #14 (clean_model_name .lower()), Upstream-Bug. DB manuell korrigiert nach CrashLoop.
- **Phase 2 TEST:** **Live-Infrastruktur abgebaut, Code als Template erhalten** (2026-04-21)
  - 🗑️ **StackIT Live-Ressourcen geloescht:** Helm Release `onyx-test` + Namespace `onyx-test` + PostgreSQL Flex `vob-test` (inkl. Backups) + Object Storage Bucket `vob-test`. Durchgefuehrt via StackIT CLI + kubectl + Terraform `state rm`.
  - 💰 Einsparung: ~115 EUR/Monat (LoadBalancer + PG Flex 2.4 Single + Bucket)
  - ⏸️ War heruntergefahren seit 2026-03-19 (15 Pods zuvor aktiv)
  - ✅ TLS/HTTPS TEST war LIVE (2026-03-09) — Let's Encrypt ECDSA P-384, TLSv1.3, HTTP/2
  - 📋 **Template-Artefakte bleiben im Repo erhalten** (als Blueprint fuer Kunden-Klon-Projekte und fuer spaetere VÖB-Reaktivierung):
    - `deployment/terraform/environments/test/` (mit Reaktivierungs-Anleitung im Header)
    - `deployment/helm/values/values-test.yaml` (mit Template-Marker)
    - `.github/workflows/stackit-deploy.yml` deploy-test-Job (inaktiv, nur via workflow_dispatch triggerbar)
  - 📌 DNS-Eintrag `test.chatbot.voeb-service.de` muss bei GlobVill/Cloudflare aufgeraeumt werden (Leif)
  - 📌 GitHub Environment `test` + 5 Secrets koennen geloescht werden (optional)
- **Phase 3 (Auth):** ✅ **DEV + PROD LIVE** (2026-03-24) — Entra ID OIDC.
- **Phase 4 (Extensions):** Detailplan: `docs/referenz/ext-entwicklungsplan.md` | Lizenz-Abgrenzung: `docs/referenz/ee-foss-abgrenzung.md`
  - 4a: ✅ Extension Framework Basis (Config, Feature Flags, Router, Health Endpoint, Docker)
  - 4b: ✅ ext-branding — Whitelabel (Logo, App-Name, Login-Text, Greeting, Disclaimer, Popup, Consent). **DEV + TEST deployed und getestet (2026-03-08).** Helm Values + CI/CD build-arg konfiguriert. **Logo-Editor (2026-03-24):** Crop/Zoom-Tool, 256x256 PNG Output, DELETE Endpoint, transparenter Hintergrund optional.
  - 4c: ✅ ext-token — LLM Usage Tracking + Limits. **DEV + TEST deployed (2026-03-09).** Branch auf main gemergt.
  - 4d: ✅ ext-prompts — Custom System Prompts. **DEV + TEST deployed und abgenommen (2026-03-09).** 29 Unit Tests, CORE #7 + #10 gepatcht.
  - 4e: ✅ ext-analytics — **Plattform-Nutzungsanalysen.** Implementiert (2026-03-26). Grafana Dashboard (19 SQL-Panels, PG-Datasource, NetworkPolicy) + 4 API-Endpoints (summary, users, agents, CSV-Export). Kein Core-Patch, kein Alembic. 9 Tests. Feature Flag `EXT_ANALYTICS_ENABLED`. DEV + PROD Grafana live.
  - 4f: ✅ ext-rbac — Gruppenverwaltung. **Implementiert (2026-03-23).** 7 Endpoints, eigene Frontend-Seite `/admin/ext-groups`, **Core #10 + #11 + #12 gepatcht** (AdminSidebar-Link + persona.py + document_set.py), 29 Tests. Persona + DocumentSet Gruppen-Zuordnung funktioniert.
  - 4g: ✅ ext-access — Document Access Control. **Implementiert (2026-03-25).** Core #3 gepatcht (3 Hooks: user_groups + ACLs). Eigener Celery-Task (Ansatz C, umgeht EE-Guards). 2 Admin-Endpoints (resync, status). 11 Tests. Feature Flag `EXT_DOC_ACCESS_ENABLED`. Aktivierung: Flag + Resync.
  - 4h: ✅ ext-i18n — **Deutsche Lokalisierung.** ~250 Strings (Core-UI) + ~115 Strings (ext-Admin-Seiten), Drei-Schichten-Architektur (ext-branding + t()-Calls + DOM-Observer). Core #4 (layout.tsx) neu gepatcht. **DEV + PROD deployed (2026-03-22).** ext-Admin-Seiten (Token, Branding, Prompts) komplett auf Deutsch (2026-03-29). Text-Spacing + Kontrast-Fix.
  - 4i: ✅ ext-audit — **Audit-Logging.** Implementiert (2026-03-25). DB-Tabelle `ext_audit_log`, 15 Hooks in 5 ext-Routern, 2 Admin-Endpoints (Events + CSV-Export), DSGVO IP-Anonymisierung (90d). 13 Tests. Feature Flag `EXT_AUDIT_ENABLED`. Alembic `d8a1b2c3e4f5`.
  - **Hinweis**: Alle EE-Features werden custom nachgebaut (keine Onyx Enterprise-Lizenz vorhanden).
- **Phase 5-6:** Geplant (Testing, Production Go-Live)

## Nächster Schritt
**ext-branding User-Menu-Cleanup (2026-04-20):** Core #17 `AccountPopover.tsx` neu eingerichtet (jetzt 17 Core-Dateien, 16 gepatcht). Im User-Dropdown (Klick auf eigenen Namen unten links in der Sidebar) werden die Menu-Eintraege "Notifications" und "Help & FAQ" sowie der rote Notifications-Bubble am Sidebar-Trigger hinter `EXT_BRANDING_ENABLED` ausgeblendet. Grund: Whitelabel — VOeB nutzt Onyx' Announcement-System nicht, "Help & FAQ" verwies auf `docs.onyx.app`. Nach Fix zeigt das Menu nur noch "Benutzereinstellungen" → Trenner → "Abmelden". Branch `feature/ext-branding-user-menu-cleanup`, noch nicht gemerged. Doku komplett: `core-dateien.md` (Core #17 + Tabelle + Historie), `fork-management.md` (Merge-Stellen + 16→17 Zaehler), `CLAUDE.md`/`enterprise-grundsaetze.md`/`extension-regeln.md` (Zaehler 16→17), `.githooks/pre-commit` Whitelist, `docs/technisches-feinkonzept/ext-branding.md` (Spec-Tabelle), `CHANGELOG.md`.

**PROD-Hotfix Konsolen-Fehler (2026-04-20):** Zwei Browser-Konsolen-Probleme in PROD behoben, DEV-Deploy gruen, PROD-Deploy angestossen (GitHub Run `24688836669`, wartet auf Approval). (1) Core #15 `useSettings.ts` reduziert — `useCustomAnalyticsScript()` nicht mehr hinter `EXT_BRANDING_ENABLED` gaten (Endpoint lebt nur in `backend/ee/` → 404 → SWR-Retry-Endlos-Loop). (2) NGINX SEC-09 Rate-Limit auf `/api/*` gescopt via `map $uri $ratelimit_key` — Next.js RSC-Prefetch fuer Chat-Sidebar loeste bei 20+ Chats sonst 429-Salven auf harmlosen Seiten-Navigationen aus. Commit `4eb99469e`. Doku: `core-dateien.md` (Core #15 ERLAUBT/VERBOTEN), `CHANGELOG.md`, `sicherheitskonzept.md` (SEC-09 Scope), `runbooks/upstream-sync.md` (Incident-Hinweis fuer Sync #6+), `fork-management.md` (Merge-Stellen-Tabelle), `memory/feedback_core-15-customanalytics-gate.md`.

**PROD-Rollout Sync #5 + Monitoring-Optimierung abgeschlossen (2026-04-17).** Kompletter 6-Schritte-Rollout sauber durch in ~15 Min: OOM-Fix (kubectl patch), CI/CD Deploy (Helm Rev 18, Chart 0.4.44), Alembic-Chain-Recovery (11 Migrationen), API-Server-Restart, Helm monitoring Rev 6 (Alert Fatigue Fix + PostgresDown offiziell live), Smoke-Test (alle Checks grün: `/api/health`, `/api/ext/health/deep`, `/api/enterprise-settings`, 26 Prometheus-Targets UP, `pg_up=1`). Browser-Test abgenommen.

**Upstream-Drift (Stand 2026-04-18):** Bereits **140 neue Commits** auf `upstream/main` seit Sync #5 (2026-04-14). Kein kritischer Security-Fix dabei — Opal-UI-Refactors, Connector-Bugfixes, Dep-Bumps (authlib, mako), Multi-Model-Chat-Erweiterungen. Sync #6 in ~1-2 Wochen sinnvoll, kein Sofort-Handlungsbedarf.

**Upstream-Metrics-Stack:** Seit Sync #5 laeuft ein Upstream-eigener Metrics-Stack (`prometheus-fastapi-instrumentator` + `metrics_server.py`) auf den 7 Celery-Worker-Pods (Ports 9092-9096). Default aktiv, aber ServiceMonitors off → kein Konflikt mit Custom-Monitoring. Evaluation "Custom-Setup reduzieren?" → aufgeschoben (kein Business-Impact). Dokumentiert in `docs/referenz/monitoring-konzept.md` Abschnitt 5b.

**Offen:**
- **Kostenoptimierung:** Node-Downgrade g1a.8d → g1a.4d (~283 EUR/Mo Ersparnis, separates Terraform-Maintenance-Window)
- **2 neue Default-UserGroups** ("Admin" id 54, "Basic" id 55) — optional löschen falls VÖB nicht will
- **Rate-Limit-Retry Feature** aus Stash fertigstellen
- **Monitoring Phase 7-11** (optional): Incident-Playbook, Post-Incident-Review, Chaos-Test, On-Call-Konzept
- **Upstream-Sync #6** in 1-2 Wochen (derzeit 140 Commits Drift, kein Sofort-Handlungsbedarf)
- **M1-Abnahmeprotokoll** — wartet auf VÖB-Termin

## Blocker
| Blocker | Wartet auf | Impact |
|---------|-----------|--------|
| — | Keine aktiven Blocker | — |

## Erledigte Blocker
| Blocker | Gelöst | Datum |
|---------|--------|-------|
| Entra ID Client Secret (Value statt ID) | ✅ Neues Secret erstellt, DEV Login funktioniert | 2026-03-23 |
| Entra ID Redirect URI | ✅ Leif hat URIs eingetragen, DEV-URI korrekt (2 Tippfehler zur Bereinigung) | 2026-03-23 |
| Entra ID Zugangsdaten | ✅ VÖB hat App Registration erstellt, 3 Credentials erhalten, Niko als B2B-Gast aufgenommen | 2026-03-22 |
| DNS DEV A-Record `188.34.118.222` | ✅ Leif hat A-Record aktualisiert, DEV HTTPS LIVE | 2026-03-22 |
| DNS PROD (A-Record + ACME-CNAME) | ✅ Leif hat DNS-Eintraege gesetzt, PROD HTTPS LIVE | 2026-03-17 |
| TLS/HTTPS: ACME-Challenge CNAMEs bei GlobVill | ✅ Leif hat CNAMEs gesetzt, DEV HTTPS LIVE | 2026-03-09 |
| Cloudflare API Token Auth Error (10000) | ✅ Leif hat Permissions erweitert, ClusterIssuers READY | 2026-03-07 |
| Embedding-Wechsel blockiert (PR #7541) | ✅ Upstream PR #9005 — Search Settings Swap re-enabled | 2026-03-06 |
| LLM API Keys | ✅ StackIT AI Model Serving Token erstellt, GPT-OSS 120B konfiguriert | 2026-02-27 |
| SA `project.admin`-Rolle | ✅ Rolle erteilt | 2026-02-22 |
| StackIT Zugang | ✅ Zugang vorhanden | Feb 2026 |
