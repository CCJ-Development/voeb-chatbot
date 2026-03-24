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
  - ✅ Helm Release `onyx-prod`: **20 Pods Running** (2×API HA, 2×Web HA, 8 Celery-Worker, Vespa Zombie, **OpenSearch**, Redis, 2×Model, NGINX). Chart 0.4.36, Image `4337b8a`.
  - ✅ **OpenSearch PROD: LIVE** (2026-03-22) — Primary Document Index, Retrieval aktiviert, Cluster yellow (erwartet bei Single-Node), sicheres Passwort (nicht Chart-Default)
  - ✅ **Vespa: Zombie-Mode** (2026-03-22) — 100m/512Mi Requests, 4Gi Limit. Nur fuer Celery Readiness Check.
  - ✅ **ext-i18n PROD: LIVE** (2026-03-22) — ~250 Strings Deutsch, ~95% user-facing UI
  - ✅ API Health OK: `https://chatbot.voeb-service.de/api/health` → 200
  - ✅ SEC-06 Phase 2: `runAsNonRoot: true` aktiv (Vespa = dokumentierte Ausnahme)
  - ✅ PG ACL: Egress `188.34.73.72/32` + Admin
  - ✅ Maintenance-Window: 03:00-05:00 UTC (O8, eigenes Fenster)
  - ✅ Kubeconfig gueltig bis 2026-06-09 (90 Tage)
  - ✅ DNS: A-Record + ACME-CNAME gesetzt durch Leif/GlobVill (2026-03-17)
  - ✅ **TLS/HTTPS PROD: LIVE** (2026-03-17) — `https://chatbot.voeb-service.de`, Let's Encrypt ECDSA P-384, TLSv1.3, HTTP/2, HSTS 1 Jahr
  - ✅ SEC-09: Rate-Limiting 10r/s, Upload-Limit 20 MB, MAX_FILE_SIZE_BYTES Backend-Limit
  - ✅ **Monitoring PROD deployed** (2026-03-12): 9 Pods (Prometheus, Grafana, AlertManager, kube-state-metrics, 2x node-exporter, PG Exporter, Redis Exporter, Operator). 3 Targets UP (API, PG, Redis). Teams PROD-Kanal. Sidecar-Dashboards (PG 14114, Redis 763). 7 NetworkPolicies in monitoring NS.
  - ✅ **NetworkPolicies onyx-prod: LIVE** (2026-03-24) — 7 Policies (default-deny, DNS, intra-NS, NGINX ingress, external egress, monitoring scrape, Redis exporter). Zero-Trust Baseline. Verifiziert: Health OK, externer Zugriff OK.
  - ✅ CI/CD: `--set opensearch_admin_password` ergaenzt (2026-03-22), GitHub Secret `OPENSEARCH_PASSWORD` gesetzt
  - ✅ **Embedding PROD: Qwen3-VL-Embedding 8B** (2026-03-24) — LiteLLM Provider, 4096 Dimensionen, Re-Index abgeschlossen
  - ✅ **LLM PROD konfiguriert** (2026-03-24) — 3 Chat-Modelle (GPT-OSS 120B, Qwen3-VL 235B, Llama 3.3 70B). Core #13 Fix (api_key + api_base + default_model_name), Upstream-Bug onyx-dot-app/onyx#9592
  - ✅ **OpenSearch lowercase Fix** (2026-03-24) — Core #14 (clean_model_name .lower()), Upstream-Bug. DB manuell korrigiert nach CrashLoop.
- **Phase 2 TEST:** **DAUERHAFT HERUNTERGEFAHREN** (seit 2026-03-19)
  - ⏸️ **Status:** 0 Pods. Alle Deployments + StatefulSets auf 0 Replicas, Redis CRD geloescht. Helm Release + PVCs + Secrets bleiben erhalten. Reaktivierung jederzeit moeglich (`kubectl scale` oder `helm upgrade`).
  - ⏸️ Scale-to-Zero CronJobs + RBAC entfernt (nicht mehr noetig). `deployment/k8s/cost-optimization/` geloescht.
  - ✅ War LIVE von 2026-03-03 bis 2026-03-19 (15 Pods, 8 Celery-Worker, Standard Mode)
  - ✅ SEC-01: PG ACL eingeschränkt (188.34.93.194/32 + Admin)
  - ✅ Terraform apply TEST: PG Flex `vob-test` + Bucket `vob-test` (bleiben erhalten)
  - ✅ Namespace `onyx-test` + Image Pull Secret + DB `onyx` (bleiben erhalten)
  - ✅ GitHub Environment `test` + 5 Secrets (PG, Redis, S3)
  - ✅ TLS/HTTPS TEST war LIVE (2026-03-09) — Let's Encrypt ECDSA P-384, TLSv1.3, HTTP/2
  - ✅ Alle historischen Meilensteine (Monitoring, Upstream-Merges, K8s-Upgrade, etc.) bleiben dokumentiert
- **Phase 3 (Auth):** ✅ **DEV + PROD LIVE** (2026-03-24) — Entra ID OIDC.
- **Phase 4 (Extensions):** Detailplan: `docs/referenz/ext-entwicklungsplan.md` | Lizenz-Abgrenzung: `docs/referenz/ee-foss-abgrenzung.md`
  - 4a: ✅ Extension Framework Basis (Config, Feature Flags, Router, Health Endpoint, Docker)
  - 4b: ✅ ext-branding — Whitelabel (Logo, App-Name, Login-Text, Greeting, Disclaimer, Popup, Consent). **DEV + TEST deployed und getestet (2026-03-08).** Helm Values + CI/CD build-arg konfiguriert. **Logo-Editor (2026-03-24):** Crop/Zoom-Tool, 256x256 PNG Output, DELETE Endpoint, transparenter Hintergrund optional.
  - 4c: ✅ ext-token — LLM Usage Tracking + Limits. **DEV + TEST deployed (2026-03-09).** Branch auf main gemergt.
  - 4d: ✅ ext-prompts — Custom System Prompts. **DEV + TEST deployed und abgenommen (2026-03-09).** 29 Unit Tests, CORE #7 + #10 gepatcht.
  - 4e: ⏭️ ext-analytics — **ÜBERSPRUNGEN.** Funktionalität bereits in ext-token enthalten (Usage Dashboard, Timeline, Per-User, Per-Model). Kein Mehrwert als eigenes Modul.
  - 4f: ✅ ext-rbac — Gruppenverwaltung. **Implementiert (2026-03-23).** 7 Endpoints, eigene Frontend-Seite `/admin/ext-groups`, Core #10 + #11 gepatcht, 29 Tests. Persona + DocumentSet Gruppen-Zuordnung funktioniert (Core #11 + #12 gepatcht).
  - 4g: ⏳ ext-access — Document Access Control. **Naechster Schritt** (braucht Core #3 access.py + #11 persona.py + #12 document_set.py).
  - 4h: ✅ ext-i18n — **Deutsche Lokalisierung.** ~250 Strings, Drei-Schichten-Architektur (ext-branding + t()-Calls + DOM-Observer). Core #4 (layout.tsx) neu gepatcht. **DEV + PROD deployed (2026-03-22).**
  - **Hinweis**: Alle EE-Features werden custom nachgebaut (keine Onyx Enterprise-Lizenz vorhanden).
- **Phase 5-6:** Geplant (Testing, Production Go-Live)

## Nächster Schritt
**1. ✅ NetworkPolicies PROD (2026-03-24) → 2. M1-Abnahmeprotokoll (wartet auf VÖB-Termin).**

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
