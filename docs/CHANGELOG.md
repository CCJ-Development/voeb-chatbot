# Changelog

Alle wichtigen Änderungen am VÖB Service Chatbot werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Deployed
- [prod-rollout] **PROD-Rollout Sync #5 + Monitoring-Optimierung (2026-04-17)** — Kompletter 6-Schritte-Rollout in ~15 Min, keine Downtime
  - **Schritt 1 — OOM-Fix:** API-Server 2→4Gi, docfetching/docprocessing 4→2Gi via `kubectl patch`. OOMKilled-Restart-Loop (9+7 Restarts auf Pod-Ebene) gestoppt. Netto 0 GiB zusaetzlich (Peaks docfetching/docprocessing nur ~225 MiB).
  - **Schritt 2 — CI/CD Deploy:** `stackit-deploy.yml` (Run 24584226916), Helm Rev 17 → 18, Chart 0.4.36 → 0.4.44. Build + Deploy in ~7 Min. Deployed: Sync #5 + Deep-Health-Endpoint `/ext/health/deep` + Readiness-Probe auf Deep-Health + `backend/ext/auth.py` Wrapper + Core #15 (useSettings.ts) + values-prod.yaml Memory-Anpassungen.
  - **Schritt 3 — Alembic-Chain-Recovery:** 11 Upstream-Migrationen manuell nachgezogen (3-Phasen-Rotation: `UPDATE alembic_version = '689433b0d8de'` → `alembic upgrade 503883791c39` → `UPDATE alembic_version = 'd8a1b2c3e4f5'`). Neue Schema-Elemente live: `user.account_type`, `persona.is_listed` (ex `is_visible`), `permission_grant` Tabelle, `AccountType`-Enum. **2 neue Default-UserGroups** ("Admin" id 54, "Basic" id 55) — kein Namens-Konflikt mit 20 VÖB-Abteilungsgruppen, 91/95 User automatisch der "Basic"-Gruppe zugewiesen.
  - **Schritt 4 — API-Server Rolling-Restart:** Rollout Status OK, 2 neue Pods (0 Restarts).
  - **Schritt 5 — Helm monitoring Rev 6:** `helm upgrade --force-replace --server-side=false` loest kubectl-replace Ownership-Konflikte. Cleanup der failed Release-Secrets v5+v6+v7. Alert Fatigue Fix offiziell via Helm (repeat_interval 4h/24h, `severity: info`/`Watchdog`/`InfoInhibitor` → null) und `PostgresDown` Alert (`pg_up{job=~"postgres-.*"} == 0` for 1m, severity=critical) sind jetzt Helm-gemanaged statt nur kubectl-replace.
  - **Schritt 6 — Smoke-Test:** `/api/health` 200, `/api/ext/health/deep` 200 (postgres+redis+opensearch), `/api/enterprise-settings` VÖB-Branding aktiv, 26 Prometheus-Targets UP, `pg_up=1`, 6 Grafana-Dashboards vorhanden, 4 Blackbox-Probes success=1, Loki+Promtail stabil. Browser-Test (Login via Entra ID, Chat, Admin-Sidebar, File-Upload) abgenommen.
  - **Runbook:** Kompletter Ablauf als wiederverwendbares Template unter `docs/runbooks/prod-deploy.md` archiviert (fuer Sync #6+ nutzbar).

### Changed
- [upstream-sync] **Fuenfter Upstream-Merge (2026-04-13/14)** — 344 Commits von `upstream/main` (Chart 0.4.36 → 0.4.44)
  - **Core-Dateien-Netto:** **15** (vorher 15). Core #13 CustomModal.tsx **entfernt** (Upstream-Fix), Core #15 useSettings.ts **neu**.
  - **Core #13 entfernt:** `CustomModal.tsx` Patch ist obsolet. Upstream hat den Bug onyx-dot-app/onyx#9592 gefixt (PRs #9958, #10003, #10004, #10009).
  - **Core #15 NEU:** `web/src/hooks/useSettings.ts` — `NEXT_PUBLIC_EXT_BRANDING_ENABLED` als Client-Side-Gate fuer `useEnterpriseSettings()` ohne EE-Lizenz-Flag zu aktivieren. Upstream PR #9529 (SSR→CSR) hat den API-Call hinter EE-Gate gelegt, was unsere ext-branding Architektur brach.
  - **Konflikte (7):** 4 trivial (.gitignore, AGENTS.md, README.md, web/Dockerfile), 3 ernsthaft (layout.tsx SSR→CSR #9529, CustomModal.tsx entfernt, AdminSidebar.tsx Opal-Migration #9863/#9866/#9867/#9895/#9906).
  - **Backend:** Alle 7 Core-Hooks (main.py, multi_llm.py, access.py, persona.py, document_set.py, prompt_utils.py, search_nlp_models.py) auto-merged ohne Konflikt.
  - **ext-i18n:** 4 neue Multi-Model-Chat-Strings ins Dictionary ("Show response", "Hide response", "Add Model", "Deselect preferred response").
  - **Alembic:** 11 neue Upstream-Migrationen + 1 modifizierte. Chain: `ff7273065d0d` (ext-branding) umgehaengt von `689433b0d8de` auf neuen Upstream-Head `503883791c39`.
  - **Persona-Rename:** `is_visible` → `is_listed` (Upstream #9569). `backend/ext/services/analytics.py` Zeile 451 angepasst.
  - **Group-Permissions Phase 1:** Upstream fuehrt `AccountType`, `Permission`, `PermissionGrant` als neue Schema-Elemente ein (#9547). Additiv, keine Kollision mit ext-rbac.
  - **seed_default_groups (#9795):** Upstream-Migration `977e834c1427` legt automatisch "Admin" und "Basic" User Groups an. Bestehende Gruppen mit gleichem Namen werden zu "Admin (Custom)" umbenannt. **PROD-Check notwendig:** Existieren solche Gruppen bereits?
  - **Security-Fixes:** SCIM advisory lock (#10048), MCP OAuth hardening (#10074/#10071/#10066), License seat count excludes service accounts (#10053).
  - **Neue Features (nicht aktiviert):** Multi-Model Chat (#9855/#9854/#9929), Bifrost Gateway LLM Provider (#9616/#9617), Generic OpenAI Compatible Provider (#9968), Google Drive error resolution (#9842), Slack federated full thread replies (#9940).
  - **Upstream-Monitoring:** Prometheus Metrics fuer Celery-Worker, API/heavy ServiceMonitors, Grafana Dashboard Provisioning (#9589/#9590/#9602/#9630/#9633/#9654/#9725/#9982/#9983/#10025/#10042). Separate Pruefung ob unser Custom-Monitoring reduziert werden kann (nicht Teil dieses Syncs).
  - **Post-Merge Fix-Commits (waren erst beim DEV-Deploy sichtbar):**
    - `fix(ext): current_admin_user in ext/auth.py kapseln` — Upstream PR #9930 hat `current_admin_user` aus `onyx.auth.users` entfernt. Neuer Wrapper `backend/ext/auth.py` mit Original-Admin-Only-Semantik. 7 ext-Router-Imports umgestellt.
    - `fix(ext): _is_require_permission Sentinel` — Onyx's `check_router_auth` akzeptiert eigene Auth-Dependencies via `fn._is_require_permission = True` Sentinel. Ohne: RuntimeError beim Boot. Attribut am `current_admin_user` Wrapper gesetzt.
    - `fix(ext-branding): Core #15 useSettings.ts Gate` — Client-Side Flag eingefuehrt, ohne EE-Lizenz-Flags zu aktivieren. Sauber entkoppelt.
  - **Pre-commit Hook aktualisiert:** `.githooks/pre-commit` Whitelist auf aktuelle 14 Core-Dateien gebracht (vorher: 3 von 14 + 4 nicht-existierende Pfade). Branch-Detection `chore/upstream-sync-*` + `MERGE_HEAD` Check fuer Auto-Bypass.
  - **Registry-Credentials Drift** (separates Operations-Thema): GitHub Secret `STACKIT_REGISTRY_PASSWORD` war seit 2026-02-27 stale. K8s-Secret `stackit-registry` hatte aktuelle Credentials. Recovery: Password aus K8s in GitHub kopiert. Runbook `docs/runbooks/secret-rotation.md` → Neue Sektion "Container Registry Token (StackIT)" mit Recovery-Verfahren.

### Fixed
- [ext-i18n] **ext-Admin-Seiten komplett auf Deutsch + Spacing/Kontrast-Fix** (2026-03-29)
  - Token Usage, Branding, System Prompts: ~115 englische Strings ins Deutsche uebersetzt
  - LogoCropModal: Tippfehler "Uebernehmen" → "Uebernehmen" korrigiert
  - GroupsListPage: "Document Sets" → "Dokumentensammlungen"
  - Text-Spacing: `block` Klasse auf alle `<Text>` mit Padding/Margin (span → block display)
  - Zeitraum-Buttons: Kontrast-Fix (`bg-background-neutral-inverted-00` + `text-text-inverted-05`)
  - Tabs: Underline-Pattern statt kaum sichtbarem Hintergrund-Wechsel (`border-b-2` + `text-text-05`)
- [ext-audit] **Audit-Events wurden nicht persistiert + Logs nicht emittiert** (2026-03-29)
  - `log_audit_event()` nutzte `flush()` statt `commit()` — Audit-Eintraege wurden beim Session-Close verworfen
  - ext-Logger nutzte `logging.getLogger()` statt `setup_logger()` — kein Handler, kein Level konfiguriert
  - Globaler `LOG_LEVEL=WARNING` auf PROD unterdrueckte `logger.info("[EXT-AUDIT]...")` — Loki Dashboard leer
  - Fix: `commit()` in `audit.py`, `setup_logger("ext", log_level=logging.INFO)` in `routers/__init__.py`

### Changed
- [UI] **"Manage Actions" Button im Chat fuer Basic User ausgeblendet** (2026-03-26)
  - ActionsPopover (Core #15): Early-Return wenn User weder Admin noch Curator ist
  - Basic User koennen weiterhin alle Agent-Tools nutzen, aber nicht konfigurieren

### Added
- [ext-analytics] **Plattform-Nutzungsanalysen + Compliance-KPIs** (2026-03-26)
  - Grafana Dashboard "VÖB Analytics Overview" (19 SQL-Panels in 7 Rows): Nutzung, Agenten, Token, Qualitaet, Content, Compliance, User-Tabelle
  - PostgreSQL Datasource in Grafana konfiguriert (ConfigMap, db_readonly_user mit SELECT-Grants, NetworkPolicy)
  - 4 Admin-API-Endpoints: GET `/ext/analytics/summary` (JSON), `/users`, `/agents`, `/export` (CSV)
  - Reine SELECT-Queries auf bestehende Onyx + ext Tabellen, kein Core-Patch, kein Alembic
  - Feature Flag `EXT_ANALYTICS_ENABLED`, 9 Unit Tests
  - Feinkonzept: `docs/technisches-feinkonzept/ext-analytics.md`
  - Runbook: `docs/runbooks/ext-analytics-verwaltung.md`

- [ext-token] **Prometheus Counter fuer Token-Metriken** (2026-03-25)
  - 3 Counter: `ext_token_prompt_total`, `ext_token_completion_total`, `ext_token_requests_total` (Label: model)
  - Inkrementiert in `log_token_usage()` (gleicher Hook wie DB-Insert, kein neuer Code-Pfad)
  - 2 Alerts: `NoLLMTokenUsage` (kein Verbrauch 30min), `HighTokenUsageSpike` (>1000 Tokens/s)
  - Grafana Dashboard: Token-Verbrauch Timeline, Requests/min pro Modell, Top-Modelle Pie, Prompt/Completion Ratio

- [ext-audit] **Audit-Logging fuer Admin-Aktionen** (2026-03-25)
  - DB-Tabelle `ext_audit_log` (PostgreSQL, DSGVO-konform, IP-Anonymisierung nach 90d)
  - 15 Audit-Hooks in 5 ext-Routern (rbac, branding, prompts, token, doc-access)
  - 2 Admin-Endpoints: GET `/ext/audit/events` (Browser + Filter) + GET `/ext/audit/export` (CSV)
  - `get_audit_context` FastAPI Dependency (Client-IP via X-Forwarded-For + User-Agent)
  - `log_audit_event()` best-effort (bricht nie den Request ab)
  - Feature Flag `EXT_AUDIT_ENABLED`, 13 Unit Tests
  - Celery-Task `ext_audit_ip_anonymize` (self-scheduling, 24h) fuer DSGVO IP-Anonymisierung
  - Alembic-Migration `d8a1b2c3e4f5` (auto-run bei Deploy)
  - Feinkonzept: `docs/technisches-feinkonzept/ext-audit.md`

- [ext-access] **Document Access Control via UserGroups** (2026-03-25)
  - Gruppen-basierte Dokumentzugriffskontrolle: Dokumente nur fuer zugewiesene Gruppen sichtbar
  - Core #3 (access.py): 3 Hooks — `_get_access_for_document`, `_get_access_for_documents`, `_get_acl_for_user`
  - Architektur Ansatz C: Eigener Celery-Task (60s), umgeht 6 EE-Guards in Onyx-Sync-Pipeline
  - 2 Admin-Endpoints: POST `/ext/doc-access/resync` + GET `/ext/doc-access/status`
  - 11 Unit Tests, Feature Flag `EXT_DOC_ACCESS_ENABLED`
  - Keine neuen DB-Tabellen (nutzt bestehende FOSS M2M-Tabellen)
  - Feinkonzept: `docs/technisches-feinkonzept/ext-access.md`

- [Monitoring] **PROD Monitoring Audit + 3 Sprints + Loki** (2026-03-25)
  - Sprint 1: cert-manager ServiceMonitor (CertExpiringSoon Alert funktionsfaehig), PGBackupCheck Alert-Noise (7→1), Grafana Dashboards (PG + Redis als ConfigMap)
  - Sprint 2: SLO Dashboard (Availability, Latenz P95, Error Budget, 10 Recording Rules), Blackbox Exporter (4 Probes: PROD Health, StackIT LLM, Entra ID, S3)
  - Sprint 3: OpenSearch Exporter (elasticsearch-exporter v1.9.0, 4 Alerts), Security Alerts (Auth-Failure, 403-Rate, OIDC-Callback), cert-manager NetworkPolicies (6, Zero-Trust), Helm Cleanup (Rev 8→9)
  - Loki Log-Aggregation: loki-stack 2.10.3, Promtail DaemonSet, 30d Retention, 20Gi PVC
  - Ergebnis: 25 Targets (alle UP), 46 VÖB Rules, 3 Dashboards, 5/5 externe Deps, Zero-Trust auf 3 Namespaces

- [ext-branding] **Logo-Editor mit Crop/Zoom** (2026-03-24)
  - Interaktives Crop/Zoom-Tool auf Admin Branding-Seite (Canvas API, keine npm-Dependency)
  - Live-Vorschau in Sidebar (24px), Login (44px), Favicon (32px)
  - Transparenter Hintergrund als Option (Checkbox)
  - Output: 256x256 PNG (3x Retina, < 300 KB)
  - DELETE Endpoint: Logo entfernen + auf OnyxIcon zuruecksetzen
  - Feinkonzept: `docs/technisches-feinkonzept/ext-branding-logo-editor.md`

- [ext-rbac] **Gruppenverwaltung** (2026-03-23)
  - 7 Backend-Endpoints: CRUD + User-Zuordnung + Curator + Minimal-Liste
  - API-Pfad `/manage/admin/user-group` (kompatibel mit bestehendem Frontend)
  - CVE-2025-51479 Vermeidung: Curator-Berechtigung pro Gruppe validiert
  - Curator-Auto-Demotion: User wird BASIC wenn letzte Curator-Gruppe entfernt
  - Hartes DELETE mit Cascade (alle 7 M2M-Tabellen, FOSS-Cleanup ist EE-only)
  - Frontend: `/admin/ext-groups` mit Gruppenliste, Create-Modal, Detail-Seite
  - AdminSidebar (Core #10): "Gruppen"-Link bei `EXT_RBAC_ENABLED`
  - Core-Dateien 10→12: `persona.py` (#11) + `document_set.py` (#12) gepatcht — Persona + DocumentSet Gruppen-Zuordnung
  - 29 Unit Tests, Feature Flag `EXT_RBAC_ENABLED` + `NEXT_PUBLIC_EXT_RBAC_ENABLED`
  - Feinkonzept: `docs/technisches-feinkonzept/ext-rbac.md` (v0.7)

- [Auth] **Entra ID (OIDC) DEV Login funktioniert** (2026-03-23)
  - Microsoft Entra ID als SSO-Provider (AUTH_TYPE=oidc, PKCE deaktiviert)
  - Helm Values: auth.oauth + auth.userauth Secrets aktiviert (values-dev.yaml)
  - CI/CD: 4 neue --set Flags im deploy-dev Job + ci-checks Dummy-Werte (OpenSearch + OAuth)
  - Niko als B2B-Gast: n.ivanov@scale42.de, ADMIN-Rolle manuell gesetzt
  - Runbook: docs/runbooks/entra-id-setup.md (v1.2, Lessons Learned + PROD-Checkliste)
  - Lessons Learned: Secret ID vs Value, PKCE Cookie-Loss, fehlende Error-Logs

## [2026-03-22]

### Added
- [ext-i18n] **Deutsche Lokalisierung** der User-facing UI (~95% Abdeckung)
  - Drei-Schichten-Architektur: ext-branding (6 Strings) + t()-Calls in Core-Patches (5 Strings) + TranslationProvider DOM-Observer (~240 Strings)
  - Core #4 (layout.tsx) neu gepatcht: TranslationProvider Wrapper + `lang="de"`
  - Core #6 (constants.ts): `UNNAMED_CHAT = "Neuer Chat"`
  - Core #8 + #9 (LoginText, AuthFlowContainer): `t()`-Import fuer SSR-Uebersetzung
  - web/Dockerfile + CI/CD: Build-Arg `NEXT_PUBLIC_EXT_I18N_ENABLED`
  - Admin-Bereich bleibt bewusst Englisch (nur CCJ/Niko)
  - Feinkonzept: `docs/technisches-feinkonzept/ext-i18n.md`
  - Analyse: `docs/analyse-lokalisierung-de.md`

- [Upstream] **Sync #4** (2026-03-22): 71 Commits, Chart 0.4.35 → 0.4.36, 0 Konflikte
  - `fix(llm)`: tool_choice nicht senden wenn keine Tools vorhanden (#9224) — koennte Gemma/Mistral auf StackIT freischalten
  - `feat(opensearch)`: Shards/Replicas konfigurierbar, Hybrid Search, Keyword+Semantic Retrieval
  - `feat(hook)`: Neues Hook-System (API, Executor, DB CRUD) — Onyx baut Plugin-Architektur
  - `fix(agents)`: Agents standardmaessig privat (#9465)
  - `feat(admin)`: Groups Page mit Cards (#9453)
  - `chore`: Next.js 16.1.7, api_server Resource Limits konfigurierbar

- [Infra] **PROD Upgrade** (2026-03-22): Chart 0.4.32 → 0.4.36, Helm Rev 4, 20 Pods
  - OpenSearch PROD deployed + Retrieval aktiviert (Primary Document Index)
  - Vespa PROD auf Zombie-Mode reduziert (100m/512Mi Requests, 4Gi Limit)
  - ext-i18n PROD deployed (~250 Strings Deutsch, ~95% user-facing UI)
  - OpenSearch PROD Passwort gesichert (nicht Chart-Default), GitHub Secret `OPENSEARCH_PASSWORD` gesetzt
  - CI/CD `stackit-deploy.yml`: `--set opensearch_admin_password` fuer PROD ergaenzt (2026-03-22)

### Fixed
- [Infra] **DNS DEV A-Record Blocker geloest** (2026-03-22)
  - Leif/GlobVill hat A-Record auf `188.34.118.222` aktualisiert (anfrage 2026-03-18)
  - DEV HTTPS `https://dev.chatbot.voeb-service.de` wieder vollstaendig erreichbar
  - `/etc/hosts` Workaround kann entfernt werden
- [Infra] **values-dev.yaml WEB_DOMAIN auf HTTPS korrigiert** (2026-03-22)
  - `WEB_DOMAIN: "http://..."` → `"https://..."` — Secure-Cookies werden jetzt korrekt gesetzt
  - HSTS-Override-Block entfernt (values-common.yaml HSTS greift)
- [Docs] **Runbook-Komplettreparatur** (2026-03-22): 9 Runbooks aktualisiert, 4 neue erstellt
  - 12 veraltete Befehle/Werte korrigiert (alte DEV-IP, Node-Typ, Secrets, Pod-Counts)
  - dns-tls-setup, ci-cd-pipeline, llm-konfiguration, prod-bereitstellung: stark veraltete Abschnitte aktualisiert
  - upstream-sync, helm-deploy, rollback, postgresql, monitoring-konzept: teilweise Korrekturen
  - Neue Runbooks: opensearch-troubleshooting, ip-schutz-helm, alert-antwort, secret-rotation
  - fork-management.md: 7/10 → 8/10 Core-Patches (layout.tsx seit ext-i18n)
  - OpenSearchClusterRed Alert als "geplant, nicht implementiert" dokumentiert (kein Exporter)

### Changed
- [Infra] **TEST-Umgebung dauerhaft heruntergefahren** (2026-03-19)
  - Alle Deployments + StatefulSets auf 0 Replicas, Redis CRD geloescht
  - Scale-to-Zero CronJobs + RBAC entfernt (nicht mehr noetig)
  - Helm Release bleibt (Reaktivierung moeglich), PVCs erhalten
  - `deployment/k8s/cost-optimization/` entfernt (4 Dateien)

- [UI] **EE-Platzhalter aus Admin-Sidebar entfernt** (2026-03-19)
  - 5 ausgegraute EE-Items (Groups, SCIM, Appearance & Theming, Usage Statistics, Query History) werden ohne Enterprise-Lizenz nicht mehr angezeigt
  - CORE #10 (`AdminSidebar.tsx`): `addDisabled()` durch `if (enableEnterprise)` Guards ersetzt
  - Patch aktualisiert (`_core_originals/AdminSidebar.tsx.patch`)

- [Infra] **OpenSearch aktiviert (Upstream-Default seit v3.0.0)** (2026-03-19)
  - OpenSearch als Document Index Backend aktiviert (Dual-Write mit Vespa)
  - 6 OpenSearch-Overrides entfernt (waren Workarounds seit Upstream-Sync #3)
  - Vespa auf Zombie-Mode reduziert (minimale Ressourcen, nur fuer Readiness Check)
    - v3.x Code erfordert Vespa-Pod (`wait_for_vespa_or_shutdown` in `app_base.py:517`)
    - DEV/TEST: 50m CPU / 256Mi RAM (vorher 300m / 2Gi)
    - PROD: 100m CPU / 512Mi RAM (vorher 2000m / 4Gi)
  - OpenSearch Ressourcen: DEV/TEST 300m/1.5Gi, PROD 1000m/2Gi
  - Netto-Resource-Delta: DEV +50m CPU, PROD -900m CPU
  - Monitoring: OpenSearch PVC Alert hinzugefuegt (DEV/TEST + PROD)
  - Docker Compose: OpenSearch JVM Heap auf 512m fuer lokale Entwicklung
  - Nach Deploy: Retrieval per Admin UI auf OpenSearch umschalten (einmalig pro Env)
  - Analyse: `docs/analyse-opensearch-vs-vespa.md`
- [Docs] **Runbooks + SSOT aktualisiert fuer OpenSearch/Vespa-Wechsel** (2026-03-19)
  - `docs/runbooks/upstream-sync.md`: OpenSearch ist Default, Vespa Zombie-Mode Checkliste, StatefulSet PVC + 4Gi Memory Warnungen
  - `docs/runbooks/helm-deploy.md`: OpenSearch Pod in Pod-Listing, Known Issues (Vespa 4Gi, PVC immutable, Startup-Dauer), Pod-Counts aktualisiert
  - `docs/runbooks/dns-tls-setup.md`: DEV HTTPS temporaer deaktiviert (neue LB-IP), HSTS Override, Wiederherstellungsschritte
  - `docs/referenz/technische-parameter.md`: Document Index Sektion (OpenSearch 3.4.0 + Vespa Zombie-Mode), Pod-Counts, HTTPS DEV Status, Versionen

### Fixed
- [Infra] **Upstream-Sync #3: DB-Migrationen + Helm-Neuinstallation DEV** (2026-03-18)
  - Upstream-Merge erforderte Helm-Release-Neuinstallation auf DEV (Chart-Inkompatibilität)
  - NGINX Controller neu erstellt → neue LB-IP: `188.34.74.187` → `188.34.118.222`
  - DNS A-Record Update bei GlobVill/Leif angefragt (bis dahin kein HTTPS auf DEV)
  - 4 Alembic-Migrationen fehlten — in Chain eingefügt aber nie ausgeführt (DB war bereits auf Head gestempelt):
    - `b5c4d7e8f9a1`: `hierarchy_node_by_connector_credential_pair` Tabelle
    - `27fb147a843f`: `user.created_at` + `user.updated_at` Spalten
    - `93a2e195e25c`: `voice_provider` Tabelle + User Voice-Preferences
    - `689433b0d8de`: `hook` + `hook_execution_log` Tabellen
  - Fix: SQL manuell auf DEV-DB ausgeführt (Alembic konnte übersprungene Migrationen nicht nachholen)
  - Login-Problem: HTTP-Zugriff über IP funktioniert nicht (Cookie hat `Secure`-Flag wegen `WEB_DOMAIN=https://...`)
  - API-Server + Web-Server neugestartet, Health OK auf neuer IP verifiziert

### Added
- [Infra] **PROD HTTPS aktiviert** (2026-03-17)
  - Domain: `https://chatbot.voeb-service.de` LIVE
  - Certificate: Let's Encrypt ECDSA P-384 (secp384r1), Issuer E7
  - TLS: TLSv1.3, HTTP/2, HSTS max-age=31536000 (1 Jahr, BSI TR-02102 + OWASP)
  - DNS: A-Record + ACME-Challenge CNAME durch Leif/GlobVill gesetzt
  - cert-manager DNS-01 via Cloudflare, ClusterIssuer `onyx-prod-letsencrypt`

- [Infra] **Kostenoptimierung DEV/TEST** (2026-03-16)
  - Node-Downgrade g1a.8d → g1a.4d (4 vCPU, 16 GB RAM)
  - Resource Requests um 40-80% gesenkt (CPU Actual war 5% der Requests)
  - Redis-Operator: 500m → 50m, Prometheus: 500m → 250m, Celery: 250m → 150m
  - TEST Scale-to-Zero CronJobs (Mo-Fr 08:00-18:00 UTC) [Hinweis: CronJobs 2026-03-19 entfernt, TEST dauerhaft heruntergefahren]
  - Kosten DEV+TEST: 868,47 → 585,29 EUR/Mo (-283,18 EUR, -32,6%)
  - Kosten Gesamt: 1.832,43 → 1.549,25 EUR/Mo (-15,4%)
  - Details: `audit-output/kostenoptimierung-ergebnis.md`, `docs/infrastruktur-review.md`

- [Docs] **Dokumentations-Audit Remediation** (2026-03-15)
  - 49 Audit-Massnahmen umgesetzt (28 Sofort-Fixes, 8 ADR-Fixes, 8 Quality-Fixes, 6 Runbook-Updates)
  - 7 neue Dokumente erstellt:
    - `docs/dsfa-entwurf.md` — Datenschutz-Folgenabschaetzung (Art. 35 DSGVO), 15 Risiken, 18 Massnahmen
    - `docs/vvt-entwurf.md` — Verzeichnis von Verarbeitungstaetigkeiten (Art. 30 DSGVO), 5 Verarbeitungen
    - `docs/loeschkonzept-entwurf.md` — Loeschkonzept (DIN EN ISO/IEC 27555), 13 Datenarten, 6 Loeschprozesse
    - `docs/ki-risikobewertung-entwurf.md` — KI-Risikobewertung (EU AI Act), Limited Risk, Art. 4/50 Pflichten
    - `docs/adr/adr-006-vpn-zu-https-oidc.md` — ADR: VPN-Beschluss zu HTTPS+OIDC (Kickoff-Abweichung)
    - `docs/referenz/technische-parameter.md` — Single Source of Truth fuer alle technischen Werte
    - `docs/referenz/compliance-research.md` — Compliance-Tiefenrecherche (DSGVO, EU AI Act, BSI, BAIT)
  - Compliance-Validierung: Unabhaengige Gegenpruefung aller 5 Compliance-Anforderungen
  - Alle Entwuerfe mit Markern fuer VoeB-Abstimmung ([VÖB-DSB], [KLAERUNG], [AVV])

### Changed
- [Docs] **17 bestehende Dokumente aktualisiert** (Audit-Korrekturen):
  - `betriebskonzept.md` v0.6.1: DEV 16 Pods, NP 8, AES-256, PG Retention 30d, PROD IngressClass, Health-Pfade, Smoke-Test-Parameter
  - `sicherheitskonzept.md` v0.6.1: DSFA ENTWURF IN ARBEIT, HSTS max-age, NP 8, AES-256
  - `testkonzept.md` v0.5.2: NFR 150 User, 4 LLM-Modelle, K6 HTTPS, RTM, Entry/Exit Criteria, Sprachbereinigung, Abnahmekriterien
  - `monitoring-konzept.md` v0.3.1: NP 8, Kickoff-Referenz, Aenderungshistorie
  - `adr-002` v1.2: Core-Nummerierung, Merge-Frequenz, Tabellennamen
  - `adr-003` v1.2: BaFin→Banking-Standards, Sealed Secrets Nachtrag
  - `adr-004`: Kosten 550→868 EUR
  - `adr-005` v1.0: Sign-off-Tabelle
  - `ext-branding.md` v1.0.1: SVG aus Content-Type entfernt
  - `ext-token.md` v0.3.1: D7 total_tokens, HTTP 409
  - `ext-entwicklungsplan.md`: API-Pfad, EXT_ANALYTICS kommentiert, ext-retention geplant
  - 6 Runbooks: Zweck-Abschnitte, PROD-Info, Eskalation, Querverweise

- [Infra] **Monitoring PROD deployed** (2026-03-12)
  - Eigenstaendiger kube-prometheus-stack auf PROD-Cluster (`vob-prod`, ADR-004)
  - 9 Pods: Prometheus, Grafana (3/3 mit Sidecar), AlertManager, kube-state-metrics, 2x node-exporter, prometheus-operator, PG Exporter, Redis Exporter
  - 3 Scrape-Targets UP: `onyx-api-prod`, `postgres-prod`, `redis-prod`
  - PROD-spezifisch: 90d Retention, 50Gi Storage, separater Teams-Kanal (`teams-prod` Receiver mit `[PROD]`-Prefix)
  - Grafana Dashboards: Sidecar-Provisioning via gnetId (PostgreSQL 14114, Redis 763) — persistent ueber Pod-Restarts
  - 7 NetworkPolicies in `monitoring` NS (Zero-Trust)
  - Eigene Values-Datei: `deployment/helm/values/values-monitoring-prod.yaml`
  - Lesson Learned: App-NS Monitoring-Policies NICHT ohne Basis-Policies anwenden (implizite Denies)
  - Lesson Learned: Egress-Policies muessen alle Ziel-Namespaces enthalten (`onyx-prod` fehlte initial)

- [Infra] **PROD-Cluster deployed** (2026-03-11): SKE `vob-prod` (eigener Cluster, ADR-004), K8s v1.33.9, 2x g1a.8d, PG Flex 4.8 HA (3-Node), 19 Pods (2x API HA, 2x Web HA, 8 Celery-Worker), LB `188.34.92.162`
- GitHub Environment `prod` mit Required Reviewer + 6 Secrets (keine Secrets im Git)
- SEC-06 Phase 2: `runAsNonRoot: true` aktiv auf PROD (Vespa = dokumentierte Ausnahme)
- PG ACL PROD: Egress `188.34.73.72/32` eingeschraenkt
- Maintenance-Window PROD: 03:00-05:00 UTC

### Changed
- [Config] **Embedding DEV: Wechsel auf Qwen3-VL-Embedding 8B** (2026-03-12) — nomic-embed-text-v1 ersetzt, alle Environments jetzt auf Qwen3-VL-Embedding 8B
- [Infra] **Alert-Tuning PROD** (2026-03-12, Helm Rev 3): Mindest-Traffic Guard fuer PGHighRollbackRate (>10 tx/sec) + RedisCacheHitRateLow (>50 ops/sec) — False Positives bei Idle-System. coreDns ServiceMonitor deaktiviert (StackIT-managed). Exporter CPU-Limits erhoeht (PG: 100m/250m, Redis: 50m/150m, node-exporter: 150m/500m).
- [Infra] `03-allow-scrape-egress.yaml` um `onyx-prod` Namespace erweitert (2026-03-12)
- [Infra] `07-allow-redis-exporter-egress.yaml` um `onyx-prod` Namespace erweitert (2026-03-12)
- [Infra] `apply.sh` (Monitoring-Exporters) Rewrite: Auto-Detection DEV/TEST/PROD statt Hardcoded (2026-03-12)
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
  - Embedding DEV: Wechsel auf Qwen3-VL-Embedding 8B (2026-03-12, vorher nomic-embed-text-v1)
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
  - Embedding-Modell: nomic-embed-text-v1 initial aktiv (inzwischen auf allen Environments durch Qwen3-VL-Embedding 8B ersetzt, siehe 2026-03-08/2026-03-12).
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
- [x] Custom Prompts Release (DEV + TEST deployed + abgenommen 2026-03-09)
- [x] ~~Analytics Release~~ — UEBERSPRUNGEN (Funktionalitaet in ext-token enthalten, 2026-03-09)
- [x] RBAC Release (ext-rbac implementiert 2026-03-23, 7 Endpoints, 29 Tests)
- [x] Access Control Release (ext-access implementiert 2026-03-25, Core #3 gepatcht, 11 Tests)

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
| 0.1 | 2026-02-20 | Nikolaj Ivanov / CCJ | Initial Release |

---

**Letzte Aktualisierung**: 2026-03-12
**Gepflegt durch**: Nikolaj Ivanov / CCJ
**Nächste Überprüfung**: Vor M1-Abnahme
