# Sicherheitskonzept -- VÖB Service Chatbot

**Dokumentstatus**: Entwurf (teilweise implementiert)
**Letzte Aktualisierung**: 2026-04-21
**Version**: 0.9.1
**Nächste Überprüfung**: 2026-07-17

> **TEST-Umgebung-Update (2026-04-21):** Die TEST-Live-Infrastruktur wurde vollständig abgebaut. Historische Erwähnungen von TEST als Live-System in diesem Dokument beschreiben den Stand bis 2026-04-20; aktuelle Live-Umgebungen sind DEV und PROD. Die Konfigurations-Artefakte bleiben als Template-Blueprint im Repo (siehe `deployment/terraform/environments/test/`).

---

## Änderungshistorie

| Version | Datum | Autor | Änderungen |
|---------|-------|-------|------------|
| 0.1 | 2026-02 | Nikolaj Ivanov | Initialer Entwurf |
| 0.2 | 2026-03-03 | Nikolaj Ivanov | Überarbeitung auf tatsächlichen Infrastruktur-Stand (DEV + TEST live), Security-Audit-Findings SEC-01 bis SEC-07 integriert, Code-Beispiele korrigiert (Python/FastAPI), Secrets Management aktualisiert |
| 0.3 | 2026-03-05 | Nikolaj Ivanov | Cloud-Infrastruktur-Audit (2026-03-04) referenziert, SEC-03 als ERLEDIGT (NetworkPolicies DEV+TEST), 3 Quick Wins dokumentiert: C6 (DB_READONLY→K8s Secret), H8 (Security-Header), H11 (Script Injection Fix), Audit-Datum korrigiert |
| 0.4 | 2026-03-05 | Nikolaj Ivanov | Zugriffsmatrix (M-CM-3) hinzugefügt, 4-Augen-Prinzip (M-CM-2) dokumentiert mit BAIT-Referenz, Interims-Lösung und geplanten GitHub-Protection-Maßnahmen |
| 0.5 | 2026-03-09 | Nikolaj Ivanov | TLS/HTTPS als IMPLEMENTIERT aktualisiert (Let's Encrypt ECDSA P-384, TLSv1.3, HTTP/2 auf DEV+TEST seit 2026-03-09), SEC-06 Phase 1 erledigt (privileged: false), SEC-07 als verifiziert (StackIT AES-256), BAIT-Compliance-Tabelle korrigiert, URLs auf HTTPS-FQDNs aktualisiert |
| 0.6 | 2026-03-12 | Nikolaj Ivanov | PROD-Umgebung eingearbeitet (19 Pods, SKE `vob-prod`, PG Flex 4.8 HA 3-Node), SEC-06 Phase 2 ERLEDIGT (`runAsNonRoot: true` auf allen Environments inkl. PROD, Vespa = dokumentierte Ausnahme), NetworkPolicies monitoring-NS PROD (8 Policies inkl. AlertManager-Webhook-Egress), Monitoring PROD (Teams PROD-Kanal), Extensions als Sicherheitsmaßnahmen dokumentiert (ext-token Kostenkontrolle, ext-prompts LLM-Steuerung), GitHub Environment `prod` (Required Reviewer + 6 Secrets), StackIT BSI C5 Type 2 referenziert |
| 0.6.1 | 2026-03-14 | COFFEESTUDIOS | Audit-Korrektur: DSFA-Status GEPLANT→ENTWURF IN ARBEIT, NP 7→8 (AlertManager-Webhook-Egress), HSTS-Details ergänzt, AES-256 explizit bei SEC-07 |
| 0.7 | 2026-03-19 | COFFEESTUDIOS | OpenSearch Security (SSL/TLS intern, Admin-Credentials im K8s Secret), Document Index Vespa→OpenSearch Migration dokumentiert, DEV HTTP-Workaround (DNS-Eintraege ausstehend, HSTS deaktiviert), PROD HTTPS LIVE aktualisiert |
| 0.8 | 2026-03-22 | COFFEESTUDIOS | DEV HTTPS LIVE (DNS A-Record von Leif auf 188.34.118.222 aktualisiert, HSTS reaktiviert), PROD 20 Pods (+OpenSearch), GitHub Environment `prod` 7 Secrets (+OPENSEARCH_PASSWORD) |

---

## Einleitung und Geltungsbereich

Das vorliegende Sicherheitskonzept beschreibt die sicherheitstechnischen Maßnahmen und Kontrollen des **VÖB Service Chatbot**, einer Enterprise-AI-Chatbot-Lösung auf Basis von Onyx FOSS für die deutsche Bankenwirtschaft.

### Geltungsbereich

Dieses Konzept gilt für:
- Alle Komponenten des VÖB Service Chatbot (Onyx Core + Extension Layer in `backend/ext/` und `web/src/ext/`)
- Die Cloud-Infrastruktur auf StackIT (SKE Kubernetes, PostgreSQL Flex, Object Storage -- Region EU01 Frankfurt)
- Integrationspunkte mit externen Services (Microsoft Entra ID, StackIT AI Model Serving)
- Entwicklungs- (DEV), Test- (TEST) und Produktionsumgebungen (PROD)

### Zielgruppe
- IT-Sicherheitsteam (CCJ / Coffee Studios)
- Auftraggeber und Stakeholder (VÖB)
- Infrastruktur-Team (StackIT)
- Interne und externe Auditor:innen

### Aktueller Implementierungsstand

| Umgebung | Status | URL | Auth |
|----------|--------|-----|------|
| DEV | LIVE seit 2026-02-27 | `https://dev.chatbot.voeb-service.de` | Entra ID OIDC (`AUTH_TYPE: oidc`, seit 2026-03-23) |
| TEST | **Abgebaut (2026-04-21)** | — | Template-Artefakte im Repo |
| PROD | HTTPS LIVE seit 2026-03-17 | `https://chatbot.voeb-service.de` | Entra ID OIDC (`AUTH_TYPE: oidc`, seit 2026-03-24) |

> **Hinweis:** Dieses Dokument trennt klar zwischen **IMPLEMENTIERT** (verifiziert in DEV/PROD) und **GEPLANT** (offen). PROD ist seit 2026-03-17 HTTPS LIVE (20 Pods, `https://chatbot.voeb-service.de`). DEV ist seit 2026-03-22 HTTPS LIVE. Entra ID OIDC ist seit 2026-03-24 auf DEV und PROD LIVE. TEST ist seit 2026-03-19 dauerhaft heruntergefahren.

---

## Schutzziele (CIA)

Die Sicherheitsarchitektur folgt den klassischen Schutzzielen:

### 1. Vertraulichkeit (Confidentiality)
**Ziel**: Sicherstellen, dass nur autorisierte Personen auf sensible Daten zugreifen können.

**Anforderungen und Status**:

| Anforderung | Status | Details |
|-------------|--------|---------|
| Verschlüsselte Datenübertragung (TLS 1.2+) | IMPLEMENTIERT (DEV + PROD) | TLSv1.3 / ECDSA P-384 auf beiden Live-Environments (DEV seit 2026-03-22, PROD seit 2026-03-17). cert-manager auto-renewal abgesichert (NetworkPolicy-Fix 2026-04-16 fuer cert-manager-cainjector). TEST dauerhaft heruntergefahren seit 2026-03-19. |
| Sichere Verwaltung von Credentials | IMPLEMENTIERT | Kubernetes Secrets + GitHub Actions Secrets (environment-getrennt) |
| Zugriffskontrollen (Authentifizierung) | IMPLEMENTIERT | Entra ID OIDC aktiv (DEV seit 2026-03-23, PROD seit 2026-03-24). TEST heruntergefahren. |
| Datenbankzugriffskontrolle | IMPLEMENTIERT | PostgreSQL ACL auf Cluster-Egress-IP eingeschränkt (SEC-01). PROD: Egress `188.34.73.72/32` + Admin-IP |
| Minimales Privilege Principle | TEILWEISE | PG-User `onyx_app` hat nur `login` + `createdb`. Kubernetes RBAC: ein globaler Kubeconfig (SEC-05 offen) |

### 2. Integrität (Integrity)
**Ziel**: Gewährleisten, dass Daten nicht unbefugt verändert werden.

**Anforderungen und Status**:

| Anforderung | Status | Details |
|-------------|--------|---------|
| Input-Validierung auf allen Ebenen | IMPLEMENTIERT | Pydantic-Modelle (FastAPI) für alle API-Endpunkte |
| Audit Logs für Änderungen | TEILWEISE | Onyx-internes Logging aktiv. Erweitertes Audit-Logging geplant |
| Supply-Chain-Integrität (CI/CD) | IMPLEMENTIERT | SHA-gepinnte GitHub Actions, Model Server Version gepinnt |
| Datenbank-Constraints | IMPLEMENTIERT | SQLAlchemy ORM + Alembic-Migrationen mit Foreign Keys, NOT NULL etc. |

### 3. Verfügbarkeit (Availability)
**Ziel**: Gewährleisten, dass Systeme und Daten autorisiertem Personal verfügbar sind.

**Anforderungen und Status**:

| Anforderung | Status | Details |
|-------------|--------|---------|
| Kubernetes-Orchestrierung | IMPLEMENTIERT | SKE Cluster mit automatischem Pod-Restart |
| Datenbank-Backups | IMPLEMENTIERT | PG Flex: taegliches Backup (DEV 02:00 UTC, TEST 03:00 UTC, PROD 01:00 UTC, StackIT Managed). PROD: PG Flex 4.8 HA (3-Node), automatische Backups + PITR sekundengenau. StackIT Service Certificate V1.1: RPO/RTO 4h/4h, 30d Retention. Restore per Self-Service Clone. Details: `docs/backup-recovery-konzept.md` |
| Monitoring und Alerting | IMPLEMENTIERT | kube-prometheus-stack deployed auf DEV/TEST (2026-03-10) und PROD (2026-03-12): Prometheus, Grafana, AlertManager, kube-state-metrics, node-exporter, PG Exporter, Redis Exporter. PROD: 9 Pods, 3 Targets UP, separater Teams PROD-Kanal mit `[PROD]`-Prefix, `send_resolved: true`. Konzept: `docs/referenz/monitoring-konzept.md` |
| DDoS-Mitigation | IMPLEMENTIERT | Upload-Limit 20 MB (XREF-007) + Request-Rate-Limiting 10 r/s per IP, burst 50 auf `/api/*` (SEC-09, 2026-03-16, auf `/api/*` gescopt 2026-04-20) + Backend `MAX_FILE_SIZE_BYTES` 20 MB (Defense-in-Depth). Keine WAF (internes Tool, 150 User). |
| Hochverfügbarkeit | IMPLEMENTIERT (PROD) | PROD: 2x API HA, 2x Web HA, PG Flex 4.8 HA (3-Node). DEV/TEST: Single-Replica |

---

## Authentifizierung und Autorisierung

### Aktueller Stand: Onyx-interne E-Mail/Passwort-Authentifizierung (DEV/TEST/PROD)

**IMPLEMENTIERT** in DEV, TEST und PROD (temporär):

Die Authentifizierung ist über die Umgebungsvariable `AUTH_TYPE` konfiguriert. `AUTH_TYPE: "basic"` bezeichnet Onyx-eigene E-Mail/Passwort-Authentifizierung (Session-Cookie-basiert), **nicht** HTTP Basic Auth nach RFC 7617. Aktuell:

```yaml
# values-dev.yaml / values-test.yaml / values-prod.yaml (temporär)
configMap:
  AUTH_TYPE: "basic"
  REQUIRE_EMAIL_VERIFICATION: "false"
```

Onyx unterstützt folgende Auth-Typen nativ (Enum `AuthType` in `backend/onyx/configs/constants.py`):
- `basic` -- E-Mail + Passwort (aktuell aktiv)
- `oidc` -- OpenID Connect (geplant für Phase 3, Entra ID)
- `google_oauth` -- Google OAuth2 (nicht relevant)
- `saml` -- SAML (nicht relevant)
- `cloud` -- Google Auth + Basic kombiniert (nicht relevant für VÖB-Deployment)

**Onyx RBAC-Rollen** (nativ, `backend/onyx/auth/schemas.py`):

| Rolle | Beschreibung |
|-------|-------------|
| `admin` | Volle Admin-Rechte (erster Login-User wird automatisch Admin) |
| `basic` | Standard-Benutzer |
| `curator` | Admin-Rechte für zugewiesene Gruppen |
| `global_curator` | Admin-Rechte für alle Gruppen |
| `limited` | Eingeschränkter API-Zugang |
| `slack_user` | Slack-Integration-Benutzer (nicht genutzt in VÖB-Deployment) |
| `ext_perm_user` | External Permission User (nicht genutzt in VÖB-Deployment) |

### Microsoft Entra ID (OIDC) -- Phase 3

**Status: IMPLEMENTIERT** auf DEV (seit 2026-03-23) und PROD (seit 2026-03-24).

```yaml
# Aktive Konfiguration (values-dev.yaml + values-prod.yaml)
configMap:
  AUTH_TYPE: "oidc"
  OPENID_CONFIG_URL: "https://login.microsoftonline.com/<TENANT_ID>/v2.0/.well-known/openid-configuration"
  OAUTH_CLIENT_ID: "<CLIENT_ID>"        # → GitHub Secret (ENTRA_CLIENT_ID)
  OAUTH_CLIENT_SECRET: "<CLIENT_SECRET>" # → GitHub Secret (ENTRA_CLIENT_SECRET)
  OIDC_PKCE_ENABLED: "false"            # Deaktiviert (Cookie-Loss durch NGINX→Next.js Proxy)
  VALID_EMAIL_DOMAINS: ""               # Leer (scale42.de + voeb-service.de muessen beide funktionieren)
```

**Aktiver Flow (OIDC Authorization Code Flow)**:
```
1. Benutzer oeffnet Chatbot → Umleitung zu Microsoft Login
2. Benutzer authentifiziert sich bei Entra ID
3. Entra ID sendet Authorization Code an /auth/oidc/callback
4. Onyx-Backend tauscht Code gegen ID Token + Access Token (mit Client Secret)
5. Onyx erstellt Session (Cookie-basiert, 7 Tage)
6. Zugriff auf geschuetzte Ressourcen
```

**JIT Provisioning:** Erster OIDC-Login = ADMIN-Rolle, alle weiteren = BASIC. Kein automatisches Claims→Roles Mapping. Rollen-Aenderung manuell durch Admin.

**Lessons Learned (Phase 3):**
- Entra ID Client Secret ID ≠ Secret Value (Secret Value muss konfiguriert werden)
- PKCE deaktiviert weil Session-Cookie durch NGINX→Next.js Proxy verloren geht
- httpx-oauth schluckt Fehler (HTTP 500 ohne Log bei falschem Secret)

Details: [Entra ID Setup Runbook](runbooks/entra-id-setup.md)

### Autorisierung (RBAC)

**IMPLEMENTIERT (Onyx-nativ)**:
Onyx bringt ein rollenbasiertes Zugangskontrollsystem mit (siehe Rollen oben). Rollen werden pro User in der PostgreSQL-Datenbank gespeichert.

**IMPLEMENTIERT (Extension Layer, Phase 4f)**:
Erweitertes RBAC ueber `ext-rbac` (`EXT_RBAC_ENABLED=true`, seit 2026-03-23):
- Gruppen-basierte Zugriffskontrolle (7 API-Endpoints, Admin-UI unter `/admin/ext-groups`)
- Persona- und DocumentSet-Zuordnung pro Gruppe (Core #11 + #12 gepatcht)
- Entra ID Gruppen-Sync: Aktuell manuell, automatischer Sync geplant

**IMPLEMENTIERT (Extension Layer, Phase 4g)**:
`ext-access`: Document Access Control pro Gruppe (`EXT_DOC_ACCESS_ENABLED=true`, seit 2026-03-25). Core #3 access.py gepatcht (3 Hooks). Eigener Celery-Task (Ansatz C, umgeht EE-Guards).

Details: [Rollenmodell](referenz/rbac-rollenmodell.md) | [Entwicklungsplan](referenz/ext-entwicklungsplan.md)

### LLM Access Control

**VERFUEGBAR (Onyx FOSS-nativ), KONFIGURATION AUSSTEHEND:**

Onyx bietet Provider-Level Access Control fuer LLM-Modelle (implementiert in `backend/onyx/db/llm.py`):

| Feature | Status | Beschreibung |
|---------|--------|-------------|
| Public/Private Provider | ✅ FOSS | `is_public`-Flag steuert Sichtbarkeit |
| User Group Restrictions | ✅ FOSS | Provider auf bestimmte Gruppen einschraenken (`llm_provider__user_group`) |
| Persona Whitelist | ✅ FOSS | Provider auf bestimmte Agents einschraenken (`llm_provider__persona`) |
| Kombinierte AND-Logik | ✅ FOSS | Gruppen + Persona muessen beide erfuellt sein |
| Graceful Fallback | ✅ FOSS | Bei fehlendem Zugriff → stiller Fallback auf Default-Provider |

**Aktueller Stand (2026-03-24):** Alle Provider sind `is_public=true` (Default). Keine Gruppen- oder Persona-Restrictions konfiguriert. Geplant: Abteilungs-basierte Modellzuweisung — jedes Modell als eigener Provider (1:1 Mapping), Gruppen = VÖB-Abteilungen, ein Basis-Modell public fuer alle, weitere Modelle nur fuer zugewiesene Abteilungen sichtbar. Externe Provider (z.B. Claude/Anthropic) mit eigener DPA nur fuer berechtigte Gruppen.

**Kosten-Kontrolle:** ext-token (`EXT_TOKEN_LIMITS_ENABLED=true`) trackt Token-Verbrauch per User und Modell. Per-User-Limits konfigurierbar.

Details: [LLM Access Control SSOT](referenz/llm-access-control.md) | [Audit](audit/2026-03-24-llm-access-control-audit.md) | [Runbook](runbooks/llm-provider-management.md)

### Zugriffsmatrix

Die folgende Matrix dokumentiert alle Zugriffsrechte auf Infrastruktur- und Anwendungsressourcen.

#### GitHub Repository & CI/CD

| Ressource | Rolle | Zugriff | Bemerkung |
|-----------|-------|---------|-----------|
| GitHub Repository | Tech Lead (Nikolaj Ivanov, CCJ) | Admin (Write, Merge, Settings) | Einziger Admin aktuell |
| GitHub Repository | VÖB | Read | Einsicht in Code, PRs, Issues |
| GitHub Environment `dev` | CI/CD Pipeline (auto) | Deploy | Automatisch bei Push auf `main` |
| GitHub Environment `test` | Tech Lead | Deploy (workflow_dispatch) | Manueller Trigger |
| GitHub Environment `prod` | Tech Lead + Reviewer | Deploy (workflow_dispatch + Approval) | Required Reviewer + 7 Secrets (implementiert 2026-03-11, +OPENSEARCH_PASSWORD 2026-03-22) |
| GitHub Actions Secrets (global) | Repository Admin | Read/Write | STACKIT_REGISTRY_*, STACKIT_KUBECONFIG |
| GitHub Actions Secrets (per env) | Environment Admin | Read/Write | PG, Redis, S3, DB_READONLY Passwörter |

#### Kubernetes Cluster

| Ressource | Rolle | Zugriff | Bemerkung |
|-----------|-------|---------|-----------|
| SKE Cluster `vob-chatbot` (DEV) | Tech Lead | Cluster-Admin (Kubeconfig) | SEC-05: Separate Kubeconfigs zurückgestellt |
| SKE Cluster `vob-chatbot` (DEV) | CI/CD Pipeline | Cluster-Admin (Kubeconfig) | Selber Kubeconfig wie Tech Lead |
| SKE Cluster `vob-prod` (PROD) | Tech Lead | Cluster-Admin (Kubeconfig) | Eigener Cluster (ADR-004), Kubeconfig gültig bis 2026-06-22 |
| SKE Cluster `vob-prod` (PROD) | CI/CD Pipeline | Cluster-Admin (Kubeconfig) | GitHub Environment `prod` mit Required Reviewer + 7 Secrets |
| Namespace `onyx-dev` | Tech Lead / CI/CD | Full Access | Deployment, Secrets, ConfigMaps |
| Namespace `onyx-prod` | Tech Lead + Reviewer | Full Access | Eigener Cluster, Required Reviewer auf GitHub Environment |
| SKE Cluster API | Alle (Internet) | Zugriff mit Kubeconfig | **OPS-01: ACL auf Cluster-Egress-IP einschränken (empfohlen)** |

#### Datenbanken & Storage

| Ressource | Rolle / User | Zugriff | Bemerkung |
|-----------|-------------|---------|-----------|
| PostgreSQL DEV (`vob-dev`) | `onyx_app` | Read/Write (login, createdb) | ACL: Cluster-Egress-IP `188.34.93.194/32` (SEC-01) |
| PostgreSQL DEV (`vob-dev`) | `db_readonly_user` | Read-Only | Knowledge Graph, Terraform-verwaltet |
| PostgreSQL PROD (`vob-prod`) | `onyx_app` | Read/Write | PG Flex 4.8 HA (3-Node), ACL: Egress `188.34.73.72/32` + Admin-IP |
| PostgreSQL PROD (`vob-prod`) | `db_readonly_user` | Read-Only | Knowledge Graph, Terraform-verwaltet |
| PostgreSQL (Admin) | Tech Lead | Full Access (via Admin-IP) | `109.41.112.160/32` in PG ACL (alle Environments) |
| Object Storage DEV (`vob-dev`) | Anwendung | Read/Write (S3 API) | Access Key in K8s Secret |
| Object Storage PROD (`vob-prod`) | Anwendung | Read/Write (S3 API) | Access Key in K8s Secret |
| Container Registry | CI/CD Robot Account | Push/Pull | `robot$voeb-chatbot+github-ci` |

#### Infrastructure as Code

| Ressource | Rolle | Zugriff | Bemerkung |
|-----------|-------|---------|-----------|
| Terraform State | Tech Lead (lokal) | Read/Write | SEC-04: Remote State geplant |
| Terraform SA (`voeb-terraform`) | Tech Lead | StackIT Project Admin | Service Account Credentials lokal |
| StackIT Console | Tech Lead | Projekt-Admin | Web-UI für Managed Services |

#### Externe Services & APIs

| Ressource | Rolle / Zugang | Zugriff | Bemerkung |
|-----------|---------------|---------|-----------|
| StackIT AI Model Serving (LLM) | Anwendung (API Token) | HTTPS API Calls | Token in Onyx Admin UI (DB), Rotation 90d empfohlen |
| StackIT Console | Tech Lead | Projekt-Admin (Web-UI) | Managed-Service-Verwaltung (PG, S3, SKE) |
| Cloudflare DNS (`voeb-service.de`) | VÖB IT (Leif Rasch) | Zone Admin | DNS-Records und API Token für cert-manager |
| cert-manager (K8s) | ClusterIssuer | Cloudflare API Token (K8s Secret in NS `cert-manager`) | Für Let's Encrypt DNS-01 Challenge |
| Docker Hub | Anwendung (public) | Pull (kein Auth) | Model Server `onyxdotapp/onyx-model-server:v2.9.8` |
| Microsoft Entra ID | VÖB IT | OIDC Provider | ✅ Phase 3 LIVE (DEV seit 2026-03-23, PROD seit 2026-03-24) |

#### Geplante Änderungen

| Maßnahme | Betrifft | Priorität | Status |
|----------|----------|-----------|--------|
| SEC-05: Namespace-scoped ServiceAccounts | Kubernetes RBAC | ~~P1~~ → P3 | **ZURÜCKGESTELLT** (2026-03-08) — PROD = eigener Cluster |
| SEC-04: Remote State Backend | Terraform | ~~P1~~ → P3 | **ZURÜCKGESTELLT** (2026-03-08) — Solo-Dev, FileVault |
| SEC-06: Container SecurityContext | Helm Values | ~~P2~~ → **P1** | **Phase 2 ERLEDIGT** (2026-03-11) — `runAsNonRoot: true` auf allen Environments inkl. PROD. Vespa-Ausnahme entfiel mit Vespa-Disable 2026-04-26. |
| Branch Protection auf `main` | GitHub | P1 (vor PROD) | **ERLEDIGT** (2026-03-07): PR required, 3 Status Checks, kein Review (Solo-Dev) |
| Environment Protection auf `prod` | GitHub | P1 (vor PROD) | **ERLEDIGT** (2026-03-11): Required Reviewer + 7 environment-getrennte Secrets (inkl. OPENSEARCH_PASSWORD seit 2026-03-22) |
| VÖB als Required Reviewer | GitHub Environment `prod` | Langfristig | Offen |

### 4-Augen-Prinzip (Best Practice, orientiert an BAIT Kap. 2/7)

**Anforderung**: Angelehnt an BAIT Kap. 2 (IT-Governance) und Kap. 7 (IT-Projekte und Anwendungsentwicklung) wird sichergestellt, dass keine Änderung an der Produktionsumgebung ohne dokumentierte zweite Freigabe erfolgt. Dies betrifft insbesondere Code-Änderungen, Konfigurationsänderungen und Infrastrukturänderungen. Der VÖB unterliegt als eingetragener Verein (e.V.) nicht direkt den BAIT — die Umsetzung erfolgt als freiwillige Best-Practice-Orientierung.

**Aktueller Stand** (1-Person-Entwicklungsteam):

Das Projekt wird aktuell von einem einzelnen Tech Lead (Nikolaj Ivanov, CCJ) entwickelt und betrieben. Eine vollständige Umsetzung des 4-Augen-Prinzips mit zwei unabhängigen Personen ist daher noch nicht möglich.

**Implementierte Maßnahmen**:

| Maßnahme | Status | Beschreibung |
|----------|--------|-------------|
| Feature-Branch Pflicht | Implementiert | Feature-Branches werden lokal auf main gemergt. Upstream-Syncs nutzen Pull Requests (Diff-Inspektion bei grossen Merges). |
| PR-Checkliste | Implementiert | Dokumentierte Checkliste vor jedem Commit (Tests, Lint, Types, Doku) |
| Explizite Commit-Freigabe | Implementiert | Tech Lead gibt jeden Commit explizit frei (Self-Review-Prozess) |
| CHANGELOG-Dokumentation | Implementiert | Jede Änderung wird im Changelog erfasst |

**Implementierte Maßnahmen**:

| Maßnahme | Konfiguration | Effekt | Status |
|----------|--------------|--------|--------|
| GitHub Branch Protection auf `main` | Require Pull Request, 3 Required Status Checks (helm-validate, build-backend, build-frontend) | Kein direkter Push auf `main` möglich. Review-Requirement entfernt (Solo-Dev, 2026-03-07). | **ERLEDIGT** |

**Implementierte Maßnahmen** (PROD):

| Maßnahme | Konfiguration | Effekt | Status |
|----------|--------------|--------|--------|
| GitHub Environment Protection auf `prod` | Required Reviewer + 7 Secrets | Kein PROD-Deploy ohne Freigabe | **ERLEDIGT** (2026-03-11, +OPENSEARCH_PASSWORD 2026-03-22) |

**Geplante Maßnahmen**:

| Maßnahme | Konfiguration | Effekt |
|----------|--------------|--------|
| VÖB als Required Reviewer | VÖB-Kontakt als zweiter Reviewer | Echtes 4-Augen-Prinzip mit externer Freigabe |
| Wait Timer auf `prod` | Optional: 10 Min Bedenkzeit | Versehentliche Freigabe verhindern |

**Langfristige Lösung**: VÖB-Stakeholder oder ein zweiter CCJ-Mitarbeiter wird als Required Reviewer für das GitHub Environment `prod` hinterlegt. Damit ist das 4-Augen-Prinzip für alle Produktionsänderungen technisch erzwungen.

> **Querverweise**: Change-Management-Prozess in `docs/betriebskonzept.md`, Abschnitt "Change Management".

---

## Datenverschlüsselung

### Verschlüsselung im Transit (In Transit)

#### TLS/HTTPS

**Status: IMPLEMENTIERT (DEV + TEST + PROD)**

- DEV: **HTTPS LIVE** — `https://dev.chatbot.voeb-service.de`. DNS A-Record von Leif auf `188.34.118.222` aktualisiert (2026-03-22). HSTS reaktiviert (`max-age=3600`).
- TEST: `https://test.chatbot.voeb-service.de` — TLSv1.3, ECDSA P-384, HTTP/2
- PROD: `https://chatbot.voeb-service.de` — TLSv1.3, ECDSA P-384, HTTP/2, HSTS 1 Jahr (LIVE seit 2026-03-17)

**Technische Details:**
- TLS-Terminierung am NGINX Ingress Controller (in-cluster)
- Let's Encrypt Zertifikate via cert-manager (v1.19.4), DNS-01 Challenge über Cloudflare API
- ACME-Challenge CNAME-Delegation über GlobVill (voeb-service.de NS bei GlobVill)
- ClusterIssuers: `onyx-dev-letsencrypt` + `onyx-test-letsencrypt` + `onyx-prod-letsencrypt` (alle READY)
- Auto-Renewal aktiv
- BSI TR-02102-2 konform: ECDSA P-384 (stärker als BSI-Mindestanforderung)

```yaml
# Aktuelle Konfiguration (TEST + PROD)
letsencrypt:
  enabled: true
```

**DNS-Status (2026-03-22)**: DEV A-Record aktualisiert (`dev.chatbot.voeb-service.de` → `188.34.118.222`, Leif 2026-03-22). TEST A-Record gesetzt (`test.chatbot.voeb-service.de` → `188.34.118.201`). PROD A-Record gesetzt (`chatbot.voeb-service.de` → `188.34.92.162`). Cloudflare Proxy auf DNS-only (graue Wolke). ACME-Challenge CNAMEs bei GlobVill gesetzt. Details: `docs/runbooks/dns-tls-setup.md`

#### Interne Kommunikation (Cluster-intern)

**Status: TEILWEISE VERSCHLÜSSELT**

Die Kommunikation zwischen Pods innerhalb des Kubernetes-Clusters (z.B. API → OpenSearch, API → Redis, API → PostgreSQL) ist teilweise verschluesselt. Das Cluster-interne Netzwerk gilt in Kubernetes-Deployments als vertrauenswuerdig.

- PostgreSQL-Verbindung: TLS wird von StackIT Managed PG Flex unterstützt, ist aber aktuell nicht erzwungen
- Redis: Passwort-geschützt, aber kein TLS
- **OpenSearch: SSL/TLS aktiviert** (inter-node + client-to-node, selbstsignierte Zertifikate via `plugins.security.ssl`). Admin-Credentials im K8s Secret `onyx-opensearch`. DEV/TEST-Passwort: `OnyxDev1!` (Standard aus Onyx Helm Chart). **PROD bekommt sicheres Passwort per GitHub Secret** (analog PG/Redis-Handling).
- Vespa: **Entfernt 2026-04-26** (Pod, PVCs und Service). Document-Index laeuft jetzt ausschliesslich auf OpenSearch.

#### StackIT AI Model Serving (LLM-API)

**IMPLEMENTIERT**: Die Verbindung zum LLM-Provider erfolgt über HTTPS:
```
API Base: https://api.openai-compat.model-serving.eu01.onstackit.cloud/v1
```

### Verschlüsselung im Ruhezustand (At Rest)

#### PostgreSQL Datenbank (StackIT Managed Flex)

- **Backup-Verschlüsselung**: StackIT Managed Service — AES-256 Encryption-at-Rest (SEC-07 verifiziert 2026-03-08)
- **Backup-Schedule**: Taeglich (DEV: 02:00 UTC, TEST: 03:00 UTC, PROD: 01:00 UTC, konfiguriert per Terraform `pg_backup_schedule`). K8s Maintenance-Window (PROD: 03:00-05:00 UTC) ist separat.
- **PROD HA**: PG Flex 4.8 HA (3-Node Cluster) — automatische Backups + PITR sekundengenau, 30d Retention, Restore per Self-Service Clone (StackIT Service Certificate V1.1: RPO/RTO 4h/4h)
- **Column-Level Encryption**: Nicht implementiert. API Keys werden von Onyx im Klartext in der DB gespeichert (Onyx-Standardverhalten)

#### OpenSearch (Document Index — Dokumenten-Chunks + Embeddings)

- Laeuft in-cluster als StatefulSet mit PersistentVolume
- Ersetzt Vespa als Document Index fuer Dokumenten-Chunks und Embeddings (Migration 2026-03-19)
- **SSL/TLS aktiviert** (inter-node + client-to-node Verschluesselung via `plugins.security.ssl`)
- Admin-Credentials im K8s Secret `onyx-opensearch` (automatisch erstellt durch Helm Chart)
- **DEV/TEST:** Passwort `OnyxDev1!` (Standard aus Onyx Helm Chart)
- **PROD:** Sicheres Passwort wird per GitHub Secret injiziert (analog PostgreSQL/Redis-Handling)
- Verschlüsselung des PersistentVolume über StackIT StorageClass (`premium-perf2-stackit`) mit AES-256 Encryption-at-Rest (SEC-07 verifiziert 2026-03-08, StackIT Default — nicht deaktivierbar)

#### Vespa — Entfernt 2026-04-26

- Vespa lief bis Sync #6 im "Zombie-Mode" (Pod war für den Worker-Boot-Check erforderlich, enthielt aber keine produktiven Daten).
- Mit `ONYX_DISABLE_VESPA=true` (Upstream PR #10330) wurde der Boot-Check abgeschaltet, Pod und PVCs (DEV 20 GiB + PROD 50 GiB) wurden gelöscht.
- Document Index läuft seither ausschließlich auf OpenSearch.

#### Object Storage (StackIT S3-kompatibel)

- Buckets: `vob-dev` (DEV), `vob-prod` (PROD); `vob-test` am 2026-04-21 geloescht
- Zugriff über Access Key / Secret Key (pro Environment getrennt, in K8s Secrets)
- SSE (Server-Side Encryption) als StackIT Default (SEC-07 verifiziert 2026-03-08)

### Geheimnismanagement

**IMPLEMENTIERT: Kubernetes Secrets + GitHub Actions Secrets**

Es wird **kein** HashiCorp Vault eingesetzt. Die Secrets-Verwaltung erfolgt über:

1. **GitHub Actions Secrets** (CI/CD-Pipeline):
   - Global (Repository-weit): `STACKIT_REGISTRY_USER`, `STACKIT_REGISTRY_PASSWORD`, `STACKIT_KUBECONFIG`
   - Per Environment (`dev`, `test`, `prod`): `POSTGRES_PASSWORD`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `DB_READONLY_PASSWORD`, `REDIS_PASSWORD`, `OPENSEARCH_PASSWORD` (PROD)
   - PROD: 7 environment-getrennte Secrets + Required Reviewer (GitHub Environment Protection)
   - Environment-Trennung stellt sicher, dass DEV-Secrets nicht in TEST/PROD verwendet werden

2. **Kubernetes Secrets** (Runtime):
   - `onyx-postgresql` (DB-Credentials)
   - `onyx-redis` (Redis-Passwort)
   - `onyx-dbreadonly` (DB Readonly-Passwort, seit C6-Fix 2026-03-05)
   - `onyx-objectstorage` (S3-Credentials)
   - `onyx-opensearch` (OpenSearch Admin-Credentials — DEV/TEST: `OnyxDev1!`, PROD: sicheres Passwort per GitHub Secret)
   - `stackit-registry` (Image Pull Secret)
   - Secrets werden per Helm `--set` aus GitHub Actions injiziert (nicht in Git)

3. **Terraform State** (Infrastruktur-Credentials):
   - **WARNUNG**: Terraform State liegt aktuell lokal auf dem Entwickler-Laptop und enthält Klartext-Passwörter (PG-Credentials)
   - Migration zu Remote State (StackIT Object Storage) geplant (SEC-04)

**Verwaltete Geheimnisse**:

| Geheimnis | Speicherort | Rotation |
|-----------|-------------|----------|
| PostgreSQL-Passwort (App) | GitHub Secret → K8s Secret | Manuell |
| PostgreSQL-Passwort (Readonly) | GitHub Secret → K8s Secret | Manuell |
| Redis-Passwort | GitHub Secret → K8s Secret | Manuell |
| S3 Access Key + Secret | GitHub Secret → K8s Secret | Manuell |
| OpenSearch Admin-Passwort | K8s Secret `onyx-opensearch` (DEV/TEST: `OnyxDev1!`, PROD: GitHub Secret) | Manuell |
| Container Registry Token | GitHub Secret | Manuell |
| Kubeconfig (DEV/TEST) | GitHub Secret (base64) | Ablauf: 2026-06-14 |
| Kubeconfig (PROD) | GitHub Secret (base64) | Ablauf: 2026-06-22 |
| StackIT AI Model Serving Token | Onyx Admin UI (in DB) | Manuell (90d empfohlen) |
| Terraform SA Key | `~/.stackit/` (lokal, chmod 600) | Manuell |

> **Offener Punkt (SEC-04):** Automatische Secret-Rotation ist nicht implementiert. Für PROD muss ein Rotationskonzept definiert werden.

---

## Netzwerksicherheit

### Kubernetes-Architektur

**IMPLEMENTIERT**:

```
Internet
  │
  ├─→ [SKE Cluster vob-chatbot (DEV)]
  │     NGINX Ingress (LoadBalancer)
  │       DEV: 188.34.118.222 (IngressClass: nginx)
  │     [onyx-dev Namespace] — 15 Pods (Vespa entfiel 2026-04-26)
  │       API Server → OpenSearch, Redis, Celery (8 Worker)
  │       Web Server (Frontend), Model Server
  │     [onyx-test Namespace] — ABGEBAUT (2026-04-21, war 15 Pods)
  │     [monitoring Namespace] — DEV Monitoring
  │
  └─→ [SKE Cluster vob-prod (PROD, eigener Cluster, 2x g1a.4d seit 2026-04-26)]
        NGINX Ingress (LoadBalancer)
          PROD: 188.34.92.162 (HTTPS LIVE seit 2026-03-17)
        [onyx-prod Namespace] — 17 Pods (Vespa entfiel 2026-04-26)
          2x API Server HA, 2x Web Server HA
          OpenSearch, Redis, Celery (8 Worker), 2x Model Server, NGINX
        [monitoring Namespace] — 9 Pods
          Prometheus, Grafana, AlertManager, kube-state-metrics
          2x node-exporter, PG Exporter, Redis Exporter, Operator

Externe Services (über Internet):
  - StackIT PostgreSQL Flex (DEV: vob-dev, TEST: vob-test, PROD: vob-prod HA 3-Node)
  - StackIT Object Storage (S3: vob-dev, vob-test, vob-prod)
  - StackIT AI Model Serving (LLM API, HTTPS)
```

**Cluster-Details**:

| Aspekt | DEV/TEST Cluster (`vob-chatbot`) | PROD Cluster (`vob-prod`) |
|--------|----------------------------------|---------------------------|
| Region | EU01 (Frankfurt) | EU01 (Frankfurt) |
| K8s Version | v1.33.8 | v1.33.9 |
| Node Pool | `devtest`: 2x g1a.4d (4 vCPU, 16 GB RAM, downgraded 2026-03-16) | 2x g1a.4d (4 vCPU, 16 GB RAM, downgraded 2026-04-26) |
| OS | Flatcar 4459.2.1 | Flatcar 4459.2.3 |
| Maintenance-Window | 02:00-04:00 UTC | 03:00-05:00 UTC |
| Egress-IP (NAT Gateway) | `188.34.93.194` | `188.34.73.72` |
| Kubeconfig Ablauf | 2026-06-14 | 2026-06-22 |

### Kubernetes Network Policies

**Status: IMPLEMENTIERT (SEC-03, 2026-03-05) — DEV + TEST App-NS + Monitoring-NS (alle Cluster)**

**App-Namespaces (onyx-dev, onyx-test)** — 5 NetworkPolicies (Zero-Trust Baseline):
- `01-default-deny-all`: Default-Deny für allen Ingress + Egress
- `02-allow-dns-egress`: DNS-Egress Port 53 + 8053 (StackIT/Gardener CoreDNS)
- `03-allow-intra-namespace`: Intra-Namespace-Kommunikation erlaubt
- `04-allow-external-ingress-nginx`: Ingress nur über NGINX Controller
- `05-allow-external-egress`: Egress für PostgreSQL (5432) und HTTPS (443)
- Cross-Namespace-Isolation verifiziert (DEV ↔ TEST). Details: `docs/audit/networkpolicy-analyse.md`

**App-Namespace PROD (onyx-prod)** — **NOCH KEINE NetworkPolicies** (bewusst):
- Full-Set kommt zusammen mit DNS/TLS-Hardening
- Lesson Learned: Einzelne Allow-Policies ohne Basis-Policies (default-deny + allow-intra + allow-dns) erzeugen implizite Denies und brechen den App-Traffic

**Monitoring-Namespaces (alle Cluster)** — 8 NetworkPolicies (inkl. AlertManager-Webhook-Egress, Zero-Trust):
- `01-default-deny-all`: Default-Deny für allen Ingress + Egress
- `02-allow-dns-egress`: DNS-Egress
- `03-allow-scrape-egress`: Egress zu allen App-Namespaces (Port 8080 für Metriken)
- `04-allow-intra-namespace`: Intra-Namespace-Kommunikation (Prometheus ↔ Grafana ↔ AlertManager)
- `05-allow-k8s-api-egress`: Egress zum K8s API Server (kube-state-metrics)
- `06-allow-pg-exporter-egress`: PG Exporter → StackIT PG:5432
- `07-allow-redis-exporter-egress`: Redis Exporter → Redis:6379
- `08-allow-alertmanager-webhook-egress`: AlertManager → Teams Webhook (HTTPS Egress)
- Zusätzlich: 3 Policies in App-NS für Monitoring-Ingress (Scrape + Redis Exporter)

### PostgreSQL Netzwerk-ACL

**IMPLEMENTIERT (SEC-01)**:

Die PostgreSQL-Instanzen sind auf Netzwerkebene eingeschränkt:

```hcl
# Terraform: pg_acl pro Environment
# DEV + TEST (Shared Cluster vob-chatbot):
pg_acl = [
  "188.34.93.194/32",   # Cluster-Egress-IP (NAT Gateway)
  "109.41.112.160/32"   # Admin-IP (Nikolaj Ivanov, Debugging)
]

# PROD (Eigener Cluster vob-prod):
pg_acl = [
  "188.34.73.72/32",    # PROD Cluster-Egress-IP
  "109.41.112.160/32"   # Admin-IP
]
```

- Die `pg_acl`-Variable hat **keinen Default** mehr -- jedes Environment muss seine erlaubten CIDRs explizit angeben
- Zugriff von außerhalb der erlaubten CIDRs wird auf Netzwerkebene abgelehnt
- PROD nutzt eine eigene Egress-IP (`188.34.73.72`) da eigener Cluster (ADR-004)

### Ingress & TLS

**IMPLEMENTIERT (mit TLS, seit 2026-03-09)**:

- NGINX Ingress Controller läuft in-cluster (Helm Subchart)
- DEV: **HTTPS LIVE** (seit 2026-03-22) — IngressClass `nginx`, LoadBalancer-IP `188.34.118.222`, TLS aktiv, HSTS reaktiviert (`max-age=3600`).
- TEST: **Dauerhaft heruntergefahren** (seit 2026-03-19, 0 Pods). Helm Release + TLS-Zertifikat bleiben erhalten. Bei Reaktivierung: IngressClass `nginx-test`, LB-IP `188.34.118.201`, TLS war aktiv.
- PROD: LoadBalancer-IP `188.34.92.162`, **HTTPS LIVE** seit 2026-03-17
- TLS: **Aktiv** (DEV + TEST + PROD) — Let's Encrypt ECDSA P-384, TLSv1.3, HTTP/2, cert-manager DNS-01 via Cloudflare.

**Implementierte Security-Header** (H8, 2026-03-05):
- `X-Content-Type-Options: nosniff` — verhindert MIME-Type-Sniffing
- `X-Frame-Options: DENY` — verhindert Clickjacking
- `Referrer-Policy: strict-origin-when-cross-origin` — beschränkt Referrer-Informationen
- `Permissions-Policy: geolocation=(), microphone=(), camera=()` — deaktiviert unnötige Browser-APIs
- Konfiguriert via `http-snippet` in `values-common.yaml`

**TLS-Details (seit 2026-03-09)**:
- cert-manager (v1.19.4) mit Let's Encrypt via Cloudflare DNS-01 Challenge
- ECDSA P-384 (BSI TR-02102-2 konform), TLSv1.3, HTTP/2
- Auto-Renewal aktiv, ClusterIssuers READY
- Details: `docs/runbooks/dns-tls-setup.md`
- SSL-Redirect

**HSTS (HTTP Strict Transport Security):** Konfiguriert via NGINX Ingress Annotation. **DEV: `max-age=3600`** (reaktiviert 2026-03-22 nach DNS-Update). TEST: `max-age=3600`. PROD: `max-age=31536000` (1 Jahr). Verhindert HTTP-Downgrade-Angriffe auf allen Environments.

### WAF (Web Application Firewall)

**Status: NICHT IMPLEMENTIERT**

Aktuell ist keine WAF im Einsatz. Für PROD muss evaluiert werden, ob StackIT eine WAF-Lösung anbietet oder ob eine Ingress-basierte Lösung (z.B. ModSecurity) eingesetzt wird.

---

## API-Sicherheit

### Input Validation

**IMPLEMENTIERT (Onyx-nativ)**:

Onyx nutzt **Pydantic-Modelle** (Python) für die Input-Validierung auf allen API-Endpunkten. FastAPI erzwingt automatisch die Schema-Validierung bei jedem Request.

```python
# Beispiel: Onyx Chat-Message Validierung (Pydantic BaseModel)
from pydantic import BaseModel, Field

class CreateChatMessageRequest(BaseModel):
    chat_session_id: uuid.UUID
    message: str
    parent_message_id: int | None = None
    # ... weitere Felder mit Typ-Validierung
```

Ungültige Requests werden mit HTTP 422 (Validation Error) abgelehnt, bevor sie die Business-Logik erreichen.

### Datei-Upload-Sicherheit (ext-branding Logo)

**IMPLEMENTIERT (ext-branding, 2026-03-08)**:

Das ext-branding-Modul erlaubt Logo-Upload ueber `PUT /api/admin/enterprise-settings/logo`. Folgende Sicherheitsmassnahmen sind implementiert:

- **Dateigrösse:** Maximal 2 MB (`LOGO_MAX_SIZE_BYTES`), serverseitig geprueft
- **Dateityp:** Nur PNG und JPEG erlaubt — Validierung ueber **Magic Bytes** (nicht MIME-Type oder Dateiendung)
  - PNG: `\x89PNG\r\n\x1a\n` (8 Bytes)
  - JPEG: `\xFF\xD8\xFF` (3 Bytes)
- **Kein SVG:** SVG ist explizit ausgeschlossen (XSS-Risiko durch eingebettetes JavaScript — kritisch im Banking-Kontext)
- **Speicherung:** Als BLOB in PostgreSQL (`ext_branding_config.logo_data`), nicht im Dateisystem (kein Path Traversal moeglich)
- **Auth:** Upload nur fuer Admin-Rolle (`Depends(current_admin_user)`)
- **Serving:** `GET /enterprise-settings/logo` ist public (Login-Seite), liefert nur Binary mit `image/png` oder `image/jpeg` Content-Type + `Cache-Control: public, max-age=3600`
- **Unit-Tests:** 5 Tests fuer Magic-Byte-Detection (PNG, JPEG, ungueltig, zu gross, leer)

### CORS (Cross-Origin Resource Sharing)

**IMPLEMENTIERT (Onyx-nativ)**:

CORS ist in `backend/onyx/main.py` konfiguriert:

```python
application.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGIN,  # Konfigurierbar via Umgebungsvariable
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

> **Bekannte Einschränkung:** Die aktuelle CORS-Konfiguration ist permissiv (`allow_methods=["*"]`, `allow_headers=["*"]`, `allow_credentials=True`). Für PROD sollte evaluiert werden, ob `allow_methods` auf die tatsächlich genutzten HTTP-Methoden (GET, POST, PUT, DELETE, PATCH) und `allow_headers` auf die benötigten Header eingeschränkt werden können. Ebenso sollte `CORS_ALLOWED_ORIGIN` auf die tatsächliche Produktions-Domain beschränkt werden (z.B. `https://chatbot.voeb-service.de`).

### Route-Auth-Prüfung

**IMPLEMENTIERT (Onyx-nativ)**:

Onyx prüft beim App-Start, dass alle API-Routen entweder eine Authentifizierung erfordern oder explizit als öffentlich markiert sind:

```python
# backend/onyx/main.py
check_router_auth(application)
```

### Rate Limiting & Upload-Limits

**Status: IMPLEMENTIERT**

**Upload-Limit (XREF-007, implementiert 2026-03-15):**
- **20 MB** maximale Request-Body-Groesse (Kickoff-Beschluss)
- Konfiguriert via NGINX Ingress Controller ConfigMap: `proxy-body-size: "20m"` in `values-common.yaml` UND `values-prod.yaml`
- **WICHTIG:** `proxy-body-size` muss in JEDEM values-File stehen das `nginx.controller.config` ueberschreibt. Helm Deep Merge ersetzt die gesamte `config`-Map, nicht einzelne Keys. `values-prod.yaml` hat eigenes `nginx.controller.config` (HSTS), daher dort separat gesetzt.
- Gilt fuer ALLE Umgebungen (DEV, TEST, PROD) und ALLE Ingress-gerouteten Requests. PROD verifiziert (2026-03-16).
- Schuetzt vor DoS durch uebergrosse Uploads (vorher: kein explizites Limit, NGINX Default 1m)
- Docker Compose (lokal): `client_max_body_size 20m` in `deployment/data/nginx/app.conf`
- **Bekannte Abweichung:** Onyx Helm Chart Template (`nginx-conf.yaml`) enthaelt `client_max_body_size 5G` fuer den internen NGINX-Proxy (Port 1024). Dieser Port ist NICHT per LoadBalancer exponiert — externer Traffic geht ueber den Ingress Controller (20 MB Limit). Chart-Template ist READ-ONLY (Upstream). Fix bei naechstem Upstream-Sync evaluieren.
- **Backend Defense-in-Depth (2026-03-16):** `MAX_FILE_SIZE_BYTES: "20971520"` (20 MB) in `values-common.yaml`. Onyx Default war 2 GB — greift bei Document-Indexing (`run_docfetching.py`). Stellt sicher, dass auch Pod-zu-Pod-Traffic (der den Ingress umgeht) das 20 MB Limit einhält.

**Request-Rate-Limiting (SEC-09, implementiert 2026-03-16, auf `/api/*` gescopt 2026-04-20):**
- **10 Requests/Sekunde** pro Client-IP (sustained rate), **Burst 50** (nodelay) — **nur auf `/api/*` wirksam**
- Konfiguriert via NGINX Ingress Controller ConfigMap: `map $uri $ratelimit_key { default ""; "~^/api/" $binary_remote_addr; }` + `limit_req_zone` auf den gemappten Key in `http-snippet` + `limit_req` in `server-snippet`
- **Scope-Aenderung 2026-04-20:** Urspruenglich global auf Server-Ebene (alle Requests). Ab 2026-04-20 per `map`-Block nur noch auf API-Pfade (`/api/*`). Grund: Next.js App Router (Frontend) laedt beim Chat-Sidebar-Render bis zu 20+ Chat-Links parallel vor (RSC-Prefetch auf `/app?chatId=xxx&_rsc=...`). Diese Seiten-Requests haben keinen LLM-Kosten-Impact, fuellten aber den Burst und loesten 429-Salven auf harmlosen Navigationen aus. NGINX-Verhalten: Leere Keys (`default ""`) werden von `limit_req_zone` nicht gezaehlt → Seiten-Requests passieren ungehindert, der DoS-/LLM-Kosten-Schutz bleibt fuer API-Pfade voll erhalten.
- Gilt fuer ALLE Umgebungen (DEV, TEST, PROD)
- HTTP 429 (Too Many Requests) bei Ueberschreitung (nur auf API-Pfaden)
- In `values-common.yaml` UND `values-prod.yaml` synchron (Helm Deep Merge: PROD hat eigenes `nginx.controller.config`, muss daher in beiden Dateien stehen)
- **Client-IP Erhaltung:** `externalTrafficPolicy: Local` auf dem NGINX Service (alle Environments). Ohne dieses Setting wuerde `$binary_remote_addr` die Node-IP statt der Client-IP zeigen — alle User wuerden ein globales Rate-Limit teilen.
- LLM-Backend (StackIT AI Model Serving) hat zusaetzlich eigene Rate Limits:
  - TPM: 200.000 Tokens/Minute (Output-Tokens 5x gewichtet)
  - RPM: 30-600 Requests/Minute (modellabhaengig)

### CSRF Protection

**TEILWEISE IMPLEMENTIERT (Onyx-nativ)**:

Onyx nutzt Cookie-basierte Sessions (via `fastapi-users`). CSRF-Schutz wird über SameSite-Cookies und Origin-Header-Prüfung realisiert.

---

## CI/CD Security

### Pipeline-Architektur

**IMPLEMENTIERT** (`.github/workflows/stackit-deploy.yml`):

```
prepare (6s)          → Git SHA als Image Tag
  ├── build-backend   → ~6 Min (parallel)  → StackIT Registry
  └── build-frontend  → ~8 Min (parallel)  → StackIT Registry
deploy-{env}          → ~2 Min (Helm upgrade + Smoke Test)
```

### Sicherheitsmaßnahmen (Enterprise-Härtung)

| Maßnahme | Status | Details |
|----------|--------|---------|
| SHA-gepinnte GitHub Actions | IMPLEMENTIERT | Alle 6 Actions auf Commit-Hash fixiert (Supply-Chain-Schutz gegen kompromittierte Action-Tags) |
| Least-Privilege Permissions | IMPLEMENTIERT | `permissions: contents: read` -- Pipeline hat nur Lesezugriff auf Repo |
| Concurrency Control | IMPLEMENTIERT | Max 1 Deploy pro Environment gleichzeitig, cancel-in-progress bei neuem Push |
| Environment-getrennte Secrets | IMPLEMENTIERT | GitHub Environments `dev`, `test`, `prod` mit jeweils eigenen Secrets |
| Gepinnte Image-Versionen | IMPLEMENTIERT | Model Server auf `v2.9.8` fixiert (nicht `:latest`) |
| Required Reviewers (PROD) | IMPLEMENTIERT | GitHub Environment `prod` mit Required Reviewer + 7 Secrets (seit 2026-03-11, +OPENSEARCH_PASSWORD 2026-03-22) |
| Container Security Scanning | OFFEN | Kein Trivy/Snyk-Scan in der Pipeline (kein SEC-Finding, aber empfohlen für PROD) |

**SHA-gepinnte Actions (verifiziert)**:

```yaml
# Alle Actions sind auf Commit-Hash gepinnt, nicht auf Tags:
actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5        # v4
docker/login-action@c94ce9fb468520275223c153574b00df6fe4bcc9     # v3
docker/setup-buildx-action@8d2750c68a42422c14e847fe6c8ac0403b4cbd6f  # v3
docker/build-push-action@10e90e3645eae34f1e60eeb005ba3a3d33f178e8    # v6
azure/setup-helm@bf6a7d304bc2fdb57e0331155b7ebf2c504acf0a        # v4
azure/setup-kubectl@c0c8b32d33a5244f1e5947304550403b63930415     # v4
```

**Input-Sanitierung** (H11, 2026-03-05):
- `inputs.image_tag` wird als Environment-Variable übergeben (nicht direkt in Shell interpoliert)
- Docker-Tag-Regex-Validierung: `[a-zA-Z0-9_][a-zA-Z0-9._-]{0,127}`
- `set -euo pipefail` in allen Shell-Schritten

### Deploy-Verhalten pro Environment

| Feature | DEV | TEST | PROD |
|---------|-----|------|------|
| Trigger | `main`-Push oder manuell | Nur manuell (`workflow_dispatch`) | Nur manuell (`workflow_dispatch`) |
| Helm Rollback | Manuell (`--wait --timeout 15m`) | Manuell (`--wait --timeout 15m`) | Manuell (`--wait --timeout 15m`) |
| Smoke Test | `/api/health` (120s Timeout) | `/api/health` (120s Timeout) | `/api/health` (180s Timeout, 18 Attempts) |
| Required Reviewers | Nein | Nein | Ja (GitHub Settings) |

### Container Registry

- **Registry**: `registry.onstackit.cloud` (StackIT, Region EU01 Frankfurt)
- **Projekt**: `voeb-chatbot`
- **Zugang**: Robot Account (`robot$voeb-chatbot+github-ci`) -- Push- und Pull-Rechte (CI/CD Push + Kubernetes Image Pull)
- **Datensouveränität**: Images werden in StackIT Registry gespeichert, nicht auf Docker Hub (Ausnahme: Model Server, siehe unten)

### Image-Strategie

| Dienst | Image-Quelle | Tag-Strategie |
|--------|-------------|---------------|
| Backend (API + Celery) | StackIT Registry | Git SHA (z.B. `ea70a11`) |
| Frontend (Web) | StackIT Registry | Git SHA |
| Model Server | Docker Hub (Upstream Onyx) | Gepinnt auf `v2.9.8` |

> **Hinweis:** Der Model Server wird nicht von uns gebaut. Er ist identisch mit Upstream Onyx und wird direkt von Docker Hub gepullt. Für PROD sollte evaluiert werden, ob das Image in die StackIT Registry gespiegelt wird (Datensouveränität).

---

## LLM-spezifische Sicherheit

### LLM-Provider: StackIT AI Model Serving

**IMPLEMENTIERT (DEV + TEST seit 2026-03-03, PROD seit 2026-03-11)**:

| Aspekt | Details |
|--------|---------|
| Provider | StackIT AI Model Serving (vLLM-Backend) |
| API-Protokoll | OpenAI-kompatible API über HTTPS |
| Region | EU01 Frankfurt (Daten bleiben in Deutschland) |
| Chat-Modelle | GPT-OSS 120B (131K Kontext), Qwen3-VL 235B (218K Kontext), Llama 3.3 70B, Llama 3.1 8B |
| Embedding-Modell | Qwen3-VL-Embedding 8B (aktiv auf DEV + TEST + PROD, 4096 Dim, multilingual) |
| Auth | Token-basiert (StackIT AI Model Serving Token) |
| Preise | 0,45 EUR / 1M Input-Tokens, 0,65 EUR / 1M Output-Tokens |

**Datensouveränität**: Die LLM-Verarbeitung findet vollständig auf StackIT-Infrastruktur in Frankfurt statt. Es werden keine Daten an OpenAI, Google oder andere externe LLM-Provider gesendet.

### Prompt Injection Prevention

**IMPLEMENTIERT (Onyx-nativ + ext-prompts)**:

Onyx bietet System-Prompt-Konfiguration über die Admin UI. Das Extension-Modul `ext-prompts` (Phase 4d, deployed seit 2026-03-09) ermöglicht Custom System Prompt Injection für VÖB-spezifische Guardrails.

Implementierte Schutzmaßnahmen:
- System Prompts werden vor User-Input platziert (Onyx-Standard)
- Input-Validierung über Pydantic-Modelle (Längenbegrenzung)
- **ext-prompts** (IMPLEMENTIERT, `EXT_CUSTOM_PROMPTS_ENABLED`): Custom System Prompt Injection über Hook in `backend/onyx/chat/prompt_utils.py` (CORE #7). Admin-konfigurierbare Prompts werden vor dem Base System Prompt eingefügt. 29 Unit Tests, auf DEV + TEST + PROD deployed.

**Geplant**:
- Output-Filterung für sensible Daten (IBAN, Kreditkartennummern etc.)

### Token Limits als Kostenschutz

**IMPLEMENTIERT (Phase 4c, deployed seit 2026-03-09)**:

Das **Token Limits Management Modul** (`ext-token`, `EXT_TOKEN_LIMITS_ENABLED`) ist auf allen Environments deployed:
- Real-Time Token-Tracking (Input + Output Tokens pro Request)
- Per-User und Per-Model Usage Tracking via LLM-Hook in `backend/onyx/llm/multi_llm.py` (CORE #2)
- Usage Dashboard mit Timeline-, Per-User- und Per-Model-Ansichten in der Admin UI
- Pre-Request Validation (Quota-Prüfung vor LLM-Aufruf)
- Hard Stops bei Quota-Überschreitung (HTTP 429)

Zusätzlich bieten die StackIT-seitigen Rate Limits (200K TPM, 30-600 RPM) einen plattformseitigen Grundschutz.

### Extension Layer als Sicherheitsmaßnahmen

Die folgenden Extension-Module (`backend/ext/` + `web/src/ext/`) sind auf DEV und PROD deployed und dienen als ergänzende Sicherheitsmaßnahmen (TEST ist seit 2026-03-19 dauerhaft heruntergefahren — bei Reaktivierung werden Extensions automatisch mit deployed). Alle Extensions sind hinter Feature Flags geschützt und beeinflussen bei Deaktivierung nicht die Onyx-Kernfunktionalität.

| Modul | Feature Flag | Sicherheitsfunktion | Status |
|-------|-------------|---------------------|--------|
| ext-branding | `EXT_BRANDING_ENABLED` | Whitelabel-Branding (Logo, App-Name, Login-Text) — verhindert Verwechslung mit Onyx-Original, stärkt Vertrauenswürdigkeit. Logo-Upload mit Magic-Byte-Validierung (kein SVG/XSS). | Deployed (2026-03-08) |
| ext-token | `EXT_TOKEN_LIMITS_ENABLED` | **Kostenkontrolle**: Real-Time Token-Tracking, Per-User Quotas, Hard Stops bei Überschreitung (HTTP 429). Verhindert unkontrollierte LLM-Kosten und Missbrauch. | Deployed (2026-03-09) |
| ext-prompts | `EXT_CUSTOM_PROMPTS_ENABLED` | **Kontrollierte LLM-Steuerung**: Admin-konfigurierbare System Prompts, die vor dem Base System Prompt injiziert werden. Ermöglicht VÖB-spezifische Guardrails und Compliance-Instruktionen. | Deployed (2026-03-09) |
| ext-rbac | `EXT_RBAC_ENABLED` | **Gruppenbasierte Zugriffskontrolle**: FOSS-Ersatz fuer EE Groups. Gruppenverwaltung mit 7 Endpoints, Persona- und DocumentSet-Zuordnung pro Gruppe (Core #10/#11/#12). | Deployed (2026-03-23) |
| ext-access | `EXT_DOC_ACCESS_ENABLED` | **Dokumentzugriffskontrolle**: Dokumentzugriff nur fuer zugewiesene Gruppen. ACL-Hooks in Core #3 (access.py), eigener Celery-Task (60s Sync-Intervall, umgeht EE-Guards). | Deployed (2026-03-25) |
| ext-audit | `EXT_AUDIT_ENABLED` | **Audit-Logging**: Protokollierung aller Admin-Aktionen (15 Hooks in 5 Routern), DSGVO-konforme IP-Anonymisierung (90d Celery-Task), CSV-Export fuer Revisoren. | Deployed (2026-03-25) |
| ext-analytics | `EXT_ANALYTICS_ENABLED` | **Nutzungsstatistiken**: Admin-only Plattform-KPIs (Nutzer, Sessions, Dokumente, Feedback). Read-Only SELECT-Queries auf bestehende Onyx-Tabellen, keine Core-Patches. | Deployed (2026-03-26) |
| ext-i18n | `EXT_I18N_ENABLED` | **Deutsche Lokalisierung**: ~250 uebersetzte Strings der Benutzeroberflaeche. Drei-Schichten-Architektur (ext-branding + t()-Calls + DOM-Observer). | Deployed (2026-03-22) |

**Architektur-Prinzip**: Alle Extensions nutzen das Hook-Pattern (try/except ImportError) in max. 16 Core-Dateien. Bei Fehler in einer Extension läuft Onyx unbeeinträchtigt weiter. Details: `.claude/rules/core-dateien.md`

---

## Datenschutz und DSGVO

### Rechtsgrundlage und Compliance

Der VÖB unterliegt als eingetragener Verein (e.V.) primär der DSGVO, dem BDSG und dem EU AI Act. Da der VÖB als Spitzenverband der öffentlichen Banken im regulatorischen Umfeld der Finanzbranche agiert, orientiert sich dieses Dokument darüber hinaus an den Anforderungen der BAIT/DORA sowie des BSI IT-Grundschutzes, um den Erwartungen der Mitgliedsinstitute und Aufsichtsbehörden zu entsprechen.

**Direkt anwendbare Regelwerke:**
- **DSGVO** (Datenschutz-Grundverordnung EU) — vollumfänglich
- **BDSG** (Bundesdatenschutzgesetz Deutschland) — nationale Ergänzung zur DSGVO
- **EU AI Act** (Verordnung (EU) 2024/1689) — VÖB ist "Deployer" eines KI-Systems (Limited Risk)

**Freiwillige Orientierung (Best Practice):**
- **BAIT** (Bankaufsichtliche Anforderungen an die IT) — freiwillige Orientierung, da VÖB kein KWG-Institut. BAIT wird am 31.12.2026 aufgehoben (DORA-Übergang).
- **DORA** (Digital Operational Resilience Act) — nicht direkt anwendbar (VÖB kein Finanzunternehmen i.S.d. Art. 2), aber als Nachfolger der BAIT orientierungsrelevant
- **BSI IT-Grundschutz** (IT-Grundschutz-Kompendium, Edition 2023) — de facto Standard im Banking-Umfeld
- **BSI C5** — StackIT als Cloud-Provider besitzt BSI C5 Type 2 Zertifizierung

**Status der Compliance**:

| Regelwerk | Verbindlichkeit | Anforderung | Status |
|-----------|----------------|-------------|--------|
| DSGVO | Direkt anwendbar | Datenverarbeitung in EU | ERFÜLLT (StackIT EU01 Frankfurt) |
| DSGVO | Direkt anwendbar | Keine Drittland-Übermittlung | ERFÜLLT (LLM auf StackIT, kein OpenAI) |
| DSGVO | Direkt anwendbar | Löschkonzept | GEPLANT (Onyx unterstützt User-Löschung nativ) |
| DSGVO | Direkt anwendbar | VVT (Verzeichnis der Verarbeitungstätigkeiten, Art. 30) | GEPLANT |
| DSGVO | Direkt anwendbar | DSFA (Datenschutz-Folgenabschätzung, Art. 35) | ENTWURF IN ARBEIT (Pflicht bei KI + PII per DSK Muss-Liste Nr. 10; finalisiert mit VÖB-DSB vor M5) |
| DSGVO | Direkt anwendbar | Datenschutzerklärung | IN ARBEIT (VÖB-seitig, wird im M5-Abnahmepaket bereitgestellt) |
| DSGVO | Direkt anwendbar | AVV mit StackIT (Art. 28) | ✅ VORHANDEN (VÖB ↔ StackIT, bestätigt 2026-03-25) |
| DSGVO | Direkt anwendbar | AVV mit CCJ (Art. 28) | ✅ VORHANDEN (VÖB ↔ CCJ, bestätigt 2026-03-25) |
| DSGVO | Direkt anwendbar | AVV mit Microsoft für Entra ID (Art. 28) | ✅ VORHANDEN (VÖB ↔ Microsoft, bestätigt 2026-03-25) |
| EU AI Act | Direkt anwendbar | KI-Kompetenz (Art. 4) — seit 02.02.2025 in Kraft | OFFEN (mit VÖB klären) |
| EU AI Act | Direkt anwendbar | Transparenzpflicht (Art. 50) — Deadline 02.08.2026 | TEILWEISE (ext-branding Disclaimer vorhanden, expliziter KI-Hinweis prüfen) |
| BAIT | Freiwillig | Verschlüsselung im Transit | IMPLEMENTIERT (TLSv1.3 ECDSA P-384 auf DEV + PROD, beide Live-Environments HTTPS LIVE; TEST dauerhaft heruntergefahren) |
| BAIT | Freiwillig | Zugangskontrolle | UMGESETZT (Entra ID OIDC auf DEV + PROD seit 2026-03-24, TEST heruntergefahren) |
| BAIT | Freiwillig | Netzwerksegmentierung | ERFÜLLT (SEC-03: 5 NetworkPolicies DEV+TEST, 7 Policies onyx-prod seit 2026-03-24, 13 Policies monitoring-NS alle Cluster inkl. AlertManager-Webhook-Egress) |
| BSI-Grundschutz | Freiwillig | Container-Härtung | **ERFÜLLT** (SEC-06 Phase 2: `runAsNonRoot: true` auf allen Environments inkl. PROD. Vespa-Ausnahme entfiel 2026-04-26 mit Vespa-Disable.) |
| BSI-Grundschutz | Freiwillig | Verschlüsselung at-rest | ERFÜLLT (SEC-07: StackIT Default AES-256, verifiziert 2026-03-08) |

**Hinweis BAIT**: BAIT (Rundschreiben 10/2017, Fassung 16.12.2024) wird am **31.12.2026 vollständig aufgehoben** (DORA-Übergang). Seit 17.01.2025 gilt DORA für CRR-Institute; BAIT gilt noch für Restgruppe bis 01.01.2027. VÖB fällt in keine dieser Kategorien — die BAIT-Orientierung ist rein freiwillig.

### Personenbezogene Daten (PII)

| Datenkategorie | Beispiele | Sensibilität | Speicherort |
|---|---|---|---|
| Identitätsdaten | Name, Email | Hoch | PostgreSQL (StackIT Managed) |
| Konversationsdaten | Chat Messages, Prompts | Mittel | PostgreSQL + OpenSearch (in-cluster) |
| Dokumente / Embeddings | Hochgeladene Dateien, Vektoren | Mittel | Object Storage + OpenSearch |
| API Keys / Tokens | LLM-Token, Session-Cookies | Kritisch | PostgreSQL (Onyx-DB) |
| Nutzungsmetriken | Login-Zeit, Features genutzt | Niedrig | PostgreSQL |

### Aufbewahrungsfristen

[AUSSTEHEND -- Klärung mit VÖB]

Aufbewahrungsfristen müssen in Abstimmung mit VÖB Compliance / Datenschutzbeauftragtem definiert werden.

### Datenverarbeitungsverträge (DPA / AVV)

[AUSSTEHEND -- Klärung mit VÖB]

Erforderlich zwischen:
- VÖB (Verantwortlicher) ↔ CCJ / Coffee Studios (Auftragsverarbeiter)
- VÖB / CCJ ↔ StackIT (Unterauftragsverarbeiter: Infrastruktur, KI-Modelle)

> **Hinweis**: Es gibt **keinen** Vertrag mit OpenAI oder anderen externen LLM-Providern. Die gesamte LLM-Verarbeitung erfolgt über StackIT AI Model Serving in Deutschland.

### EU AI Act Compliance

Der VÖB Service Chatbot wird als **Limited Risk System** eingestuft (Art. 6, Anhang III der Verordnung (EU) 2024/1689). Es handelt sich NICHT um ein Hochrisiko-System, da:
- Kein Kreditwürdigkeits-Assessment (Anhang III Nr. 5b)
- Kein Zugang zu Finanzdienstleistungen
- Kein automatisiertes Entscheidungssystem mit rechtlichen Auswirkungen
- Internes Wissensmanagement-Tool ohne autonome Entscheidungen über Personen

**Caveat**: Wenn der Chatbot jemals für kreditbezogene Entscheidungen genutzt wird, ist eine sofortige Neubewertung der Risikoklassifizierung erforderlich.

| Artikel | Pflicht | Deadline | Status |
|---------|---------|----------|--------|
| **Art. 4** (KI-Kompetenz / AI Literacy) | Mitarbeiter müssen ausreichendes KI-Verständnis haben. Schulungsmaßnahmen dokumentieren. | **BEREITS IN KRAFT** (seit 02.02.2025) | OFFEN — mit VÖB klären |
| **Art. 50** (Transparenzpflicht) | Nutzer müssen VOR Interaktion informiert werden, dass sie mit KI interagieren | 02.08.2026 | TEILWEISE — ext-branding Disclaimer vorhanden, expliziter KI-Hinweis prüfen |
| **Art. 6 Abs. 3** (Risikoklassifizierung) | Dokumentation der Risikoklassifizierung | Laufend | GEPLANT — KI-Risikobewertung erstellen |

### DSFA-Pflicht (Datenschutz-Folgenabschätzung)

**Status: ENTWURF IN ARBEIT** — DSFA-Entwurf wird erstellt (Art. 35 DSGVO). Hinweis: Die Kickoff-Einschätzung "nicht relevant" wurde durch den Dokumentations-Audit (2026-03-14) korrigiert. DSFA ist gesetzliche Pflicht (DSK Muss-Liste Nr. 10).

Eine DSFA nach Art. 35 DSGVO ist für den VÖB Service Chatbot **gesetzlich vorgeschrieben**. Drei unabhängige Trigger:

1. **DSK Muss-Liste Nr. 10** (V1.1, 17.10.2018): "Einsatz von künstlicher Intelligenz zur Verarbeitung personenbezogener Daten zur Steuerung der Interaktion mit den Betroffenen" — trifft direkt auf KI-Chatbot zu
2. **Art. 35 Abs. 1 DSGVO**: "neue Technologien" — LLMs/Generative AI qualifizieren eindeutig
3. **EDPB/WP248 Kriterien** (mindestens 2 von 9 = DSFA nötig): (a) Innovative Technologie, (b) Systematisches Monitoring (Chat-Logging), (c) Machtgefälle (Arbeitgeber-Tool)

**Rechtsgrundlage**: Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse). Gemäß Art. 35 Abs. 2 muss der VÖB-Datenschutzbeauftragte (DSB) während der DSFA konsultiert werden.

### VVT (Verzeichnis der Verarbeitungstätigkeiten)

**Status: GEPLANT**

Ein VVT nach Art. 30 DSGVO ist gesetzlich vorgeschrieben. Das VVT dokumentiert alle personenbezogenen Datenverarbeitungen des Chatbot-Systems (Identitätsdaten, Konversationsdaten, Nutzungsmetriken) mit Angabe von Verarbeitungszweck, Rechtsgrundlage, Kategorien betroffener Personen, Empfängern und Löschfristen.

---

## Logging und Audit Trail

### Aktueller Stand

**IMPLEMENTIERT (Onyx-nativ)**:

Onyx loggt auf verschiedenen Ebenen:
- API-Server-Logs (FastAPI, konfigurierbar über `LOG_LEVEL: "INFO"`)
- Celery-Worker-Logs (Background Jobs)
- Kubernetes Pod-Logs (stdout/stderr, von Kubelet verwaltet)

**NICHT IMPLEMENTIERT**:
- Zentralisiertes Log-Management (ELK Stack, Loki o.ä.)
- SIEM-Integration
- Strukturiertes Audit-Logging für Sicherheitsereignisse
- Log-Retention-Policies

### Log-Retention

Kubernetes Pod-Logs werden standardmäßig bei Pod-Restart gelöscht. Ohne zentralisierte Log-Aggregation gehen Logs bei Pod-Neustarts verloren.

**IMPLEMENTIERT** (Monitoring, 2026-03-10 DEV/TEST, 2026-03-12 PROD):
- Prometheus + Grafana für Metriken und Dashboards (deployed auf allen Environments)
- AlertManager mit Microsoft Teams Integration (separater PROD-Kanal mit `[PROD]`-Prefix)
- postgres_exporter + redis_exporter für DB/Cache-Metriken

**Geplant**:
- Evaluation einer Log-Aggregations-Lösung (zentralisiertes Logging)

---

## Schwachstellenmanagement

### Dependency Management

**TEILWEISE IMPLEMENTIERT**:

| Aspekt | Status | Details |
|--------|--------|---------|
| Python-Dependencies | Onyx-verwaltet | `backend/requirements/` (pip, gepinnte Versionen) |
| Node.js-Dependencies | Onyx-verwaltet | `web/package.json` (npm/yarn, lock-file) |
| Container-Image-Scanning | OFFEN | Kein Trivy/Snyk in CI/CD (empfohlen für PROD) |
| Automatische Updates | OFFEN | Kein Dependabot konfiguriert |
| Upstream-Sync | IMPLEMENTIERT | `.github/workflows/upstream-check.yml` -- wöchentlicher Merge-Kompatibilitäts-Check gegen Onyx FOSS |

### Patch Management

| Severity | SLA | Prozess |
|----------|-----|---------|
| Critical (CVSS >= 9.0) | 24 Stunden | Sofortiger Patch, Test, Deployment |
| High (7.0-8.9) | 7 Tage | Patch vorbereiten, in nächstem Release deployen |
| Medium (4.0-6.9) | 30 Tage | Sammeln mit anderen Updates |
| Low (0.1-3.9) | 90 Tage | Nächster Maintenance-Zyklus |

---

## Security-Audit Findings (SEC-01 bis SEC-10)

> **Quelle**: Enterprise-Audit der Infrastruktur (2026-03-04). Priorisierung: P0 = vor TEST-Deploy, P1 = vor PROD, P2 = vor VÖB-Abnahme.

| ID | Finding | Priorität | Status |
|----|---------|-----------|--------|
| SEC-01 | PostgreSQL ACL auf Cluster-Egress-IP einschränken | P0 | **ERLEDIGT** (2026-03-03) |
| SEC-02 | Node Affinity erzwingen (DEV/TEST auf eigenen Nodes) | ~~P1~~ | **ZURÜCKGESTELLT** — Begründung siehe unten |
| SEC-03 | Kubernetes NetworkPolicies (Namespace-Isolation) | P1 | **ERLEDIGT** (2026-03-05) |
| SEC-04 | Terraform Remote State (Secrets im Klartext lokal) | ~~P1~~ → P3 | **ZURÜCKGESTELLT** — Quick Win `chmod 600` umgesetzt, Remote State optional |
| SEC-05 | Separate Kubeconfigs pro Environment (RBAC) | ~~P1~~ → P3 | **ZURÜCKGESTELLT** — PROD = eigener Cluster (ADR-004), löst sich automatisch |
| SEC-06 | Container SecurityContext (`privileged: true` entfernen) | ~~P2~~ → **P1** | **Phase 2 ERLEDIGT** (2026-03-11) — `runAsNonRoot: true` auf allen Environments inkl. PROD. Vespa-Ausnahme entfiel 2026-04-26 mit Vespa-Disable. |
| SEC-07 | Encryption-at-Rest verifizieren (PG, S3, Volumes) | P2 | **ERLEDIGT** (2026-03-08) — AES-256 (StackIT Default, verifiziert SEC-07) |
| SEC-08 | CORS `allow_methods=["*"]` auf PROD einschränken | P2 | **OFFEN** — Onyx Core-Code, evaluieren ob Einschränkung ohne Seiteneffekte möglich |
| SEC-09 | Rate Limiting (DoS + LLM-Kosten-Schutz) | P2 | **IMPLEMENTIERT** (2026-03-16, auf `/api/*` gescopt 2026-04-20) — Upload-Limit 20 MB (XREF-007) + Request-Rate-Limiting 10 r/s per IP, burst 50 NUR auf `/api/*` (NGINX `map $uri $ratelimit_key` + `limit_req_zone` + `limit_req`) + Backend `MAX_FILE_SIZE_BYTES` 20 MB (Defense-in-Depth). Seiten-Routen und statische Assets nicht limitiert (verhindert 429 bei Next.js RSC-Prefetch). |
| SEC-10 | Cluster-API ACL auf Egress-IP einschränken | P3 | **OFFEN** — `cluster_acl` in Terraform von `0.0.0.0/0` einschränken (empfohlen, nicht kritisch) |

### SEC-01: PostgreSQL ACL (ERLEDIGT)

**Problem**: `pg_acl = ["0.0.0.0/0"]` -- PostgreSQL war für das gesamte Internet erreichbar.

**Lösung (implementiert 2026-03-03, erweitert auf PROD 2026-03-11)**:
- `pg_acl` Default in Terraform-Modulen entfernt (erzwingt explizite Angabe)
- DEV + TEST: `pg_acl = ["188.34.93.194/32", "109.41.112.160/32"]`
- PROD: `pg_acl = ["188.34.73.72/32", "109.41.112.160/32"]`
- `188.34.93.194` = DEV/TEST Cluster-Egress-IP (NAT Gateway, fest für Cluster-Lifecycle)
- `188.34.73.72` = PROD Cluster-Egress-IP (eigener Cluster `vob-prod`)
- `109.41.112.160` = Admin-IP (für direkten DB-Zugriff bei Debugging)

### SEC-02: Node Affinity — ZURÜCKGESTELLT (2026-03-08)

**Ursprüngliches Finding**: `nodeSelector` in Helm Values erzwingen, damit DEV- und TEST-Pods jeweils auf eigenen Nodes laufen.

**Entscheidung: Zurückgestellt — kein akuter Handlungsbedarf.** Begründung:

1. **ADR-004 sagt explizit**: "Kein Dedicated-Node-Affinity nötig — der Scheduler balanciert automatisch" (Zeile 61). Die eigene Architekturentscheidung stuft Node Affinity als unnötig ein.
2. **Bestehende Isolation ist ausreichend**: Namespace-Isolation + NetworkPolicies (SEC-03, 5 Policies pro Namespace, Cross-NS-Traffic verifiziert blockiert) + separate PG-Instanzen + separate S3-Buckets + separate Secrets + separate LoadBalancer-IPs. BAIT (freiwillige Orientierung) und BSI IT-Grundschutz empfehlen nachweisbare Umgebungstrennung, aber nicht explizit auf Node-Ebene.
3. **DEV/TEST enthalten keine Produktionsdaten** — das Restrisiko bei Pod-Kolokation (Container Escape, Resource Exhaustion) ist gering und durch Resource Limits bereits mitigiert.
4. **PROD wird ein eigener Cluster** (ADR-004) — dort ist Node Affinity irrelevant, da keine Shared-Node-Situation entsteht.
5. **Technische Einschränkung**: Der aktuelle Node Pool (`devtest`) ist ein einzelner Pool mit 2 Nodes. Persistente Labels per Terraform erfordern **separate Node Pools** (einer für DEV, einer für TEST), was eine größere Infrastrukturänderung mit Kostenimpact wäre. Manuelle `kubectl label`-Labels überleben keine Node-Replacements (Scaling, Maintenance).

**Risikobewertung**: Gering. Der Kubernetes-Scheduler verteilt Pods natürlich über verfügbare Nodes (Bin-Packing). Bei ~3,5 CPU Requests pro Environment und ~7,9 CPU Allocatable pro Node ist eine einseitige Verteilung unwahrscheinlich. Selbst im Worst Case (alle Pods auf einem Node) greifen Namespace-Isolation und NetworkPolicies.

**Wiederaufnahme-Kriterium**: Nur relevant, falls VÖB-Audit explizit Node-Level-Isolation fordert oder falls ein dritter Tenant auf denselben Cluster kommt.

### SEC-04: Terraform Remote State — ZURÜCKGESTELLT (2026-03-08)

**Ursprüngliches Finding**: Terraform State liegt lokal mit Klartext-Passwörtern. Kein Backup, kein Audit-Trail.

**Entscheidung: Herabgestuft von P1 auf P3 (Nice-to-have).** Begründung:

1. **Solo-Entwickler** — kein Risiko durch Team-Kollisionen, kein State-Locking nötig (StackIT S3 bietet ohnehin kein DynamoDB-Äquivalent)
2. **FileVault aktiv** — volle Festplattenverschlüsselung auf dem Entwickler-Laptop, State ist at-rest verschlüsselt
3. **State ist gitignored** — `*.tfstate` und `*.tfstate.*` in `.gitignore`, kein Risiko eines versehentlichen Commits
4. **CI/CD nutzt kein Terraform** — nur Helm/kubectl. Terraform wird ausschließlich lokal ausgeführt
5. **PG ACL als Defense-in-Depth** — selbst bei Passwort-Leak ist DB-Zugang auf Cluster-Egress-IP + Admin-IP beschränkt
6. **Remote State löst das Problem nicht vollständig** — S3-Credentials für den Bucket-Zugriff müssten wiederum lokal gespeichert werden
7. **Kein regulatorisches Requirement** — weder BAIT (ohnehin freiwillig) noch BSI IT-Grundschutz fordern Remote IaC State

**Quick Win umgesetzt**: `chmod 600` auf alle State-Dateien (war `644` = world-readable).

**Kosten bei Umsetzung**: 0,03 EUR/Monat (StackIT Object Storage, reine GB-Abrechnung, kein Bucket-Grundpreis). Umsetzung ~2h, kann opportunistisch bei PROD-Vorbereitung erfolgen.

**Wiederaufnahme**: Bei Teamvergrößerung (mehrere Terraform-Operatoren) oder bei expliziter Audit-Anforderung.

### SEC-05: Separate Kubeconfigs — ZURÜCKGESTELLT (2026-03-08)

**Ursprüngliches Finding**: Ein globaler `STACKIT_KUBECONFIG` GitHub Secret für alle Environments. Kompromittierter DEV-Workflow kann TEST/PROD manipulieren.

**Entscheidung: Herabgestuft von P1 auf P3 (Nice-to-have).** Begründung:

1. **PROD wird ein eigener Cluster** (ADR-004) — separates Kubeconfig ergibt sich automatisch. Die Blast-Radius-Reduktion (das einzige starke Argument) ist architektonisch gelöst.
2. **Solo-Entwickler** — derselbe Operator deployt auf alle Environments. Namespace-scoped RBAC isoliert ihn vor sich selbst, was bei einem 1-Personen-Team keinen praktischen Nutzen hat.
3. **CI/CD ist bereits gehärtet** — SHA-gepinnte Actions, `permissions: contents: read`, Environment-gated Deploys (TEST/PROD nur per `workflow_dispatch`)
4. **Kein BAIT/BSI-Requirement** für Pre-Production — das 4-Augen-Prinzip (BAIT Kap. 2/7, freiwillige Orientierung) betrifft die Produktionsumgebung, nicht DEV/TEST bei Solo-Dev
5. **DEV/TEST enthalten keine Kundendaten** — Worst Case (Cluster-Admin Leak auf DEV/TEST-Cluster) betrifft nur Testdaten

**Opportunistische Umsetzung**: Kann beim Kubeconfig-Renewal (Ablauf 2026-06-14) kostenneutral mitgemacht werden — neue ServiceAccounts + namespace-scoped RoleBindings statt erneuter Cluster-Admin-Kubeconfig.

### SEC-06: Container SecurityContext — Phase 2 ERLEDIGT (2026-03-11)

**Kritisches Finding (2026-03-08):** Analyse der Onyx Helm Chart Templates ergab, dass mehrere Komponenten mit `privileged: true` + `runAsUser: 0` laufen — die höchstmögliche Privilegierung. Ein privilegierter Container hat vollen Zugriff auf den Host-Kernel, Devices und kann Host-Filesysteme mounten.

**Betroffene Komponenten:**

| Komponente | Aktueller Zustand | Risiko |
|------------|-------------------|--------|
| Celery (alle 8 Worker) | `privileged: true`, `runAsUser: 0` | **HOCH** — Host-Kernel-Zugriff |
| Model Server (inference + index) | `privileged: true`, `runAsUser: 0` | **HOCH** — Host-Kernel-Zugriff |
| ~~Vespa~~ | Entfernt 2026-04-26 (`vespa.enabled=false`, `ONYX_DISABLE_VESPA=true`) | — |
| API Server | `runAsUser: 0` (Root, aber nicht privileged) | Mittel |
| Web Server (Next.js) | `USER nextjs` (UID 1001) | OK — bereits non-root |
| NGINX Ingress | `runAsNonRoot: true`, UID 101, no privilege escalation | OK — bereits gehärtet |

**BSI-Relevanz**: SYS.1.6.A10: "Privileged Mode SOLLTE NICHT verwendet werden." (SOLLTE = dringende Empfehlung). In einem Banking-Kontext würde dies als Finding in jedem Audit markiert.

**Umsetzung (Stufenplan):**
1. **Phase 1 (ERLEDIGT, 2026-03-08):** `privileged: false` für Celery, Model Server, Vespa via `values-common.yaml`. Eliminiert das schlimmste Finding mit minimalem Risiko.
2. **Phase 2 (ERLEDIGT, 2026-03-11):** `runAsNonRoot: true` für API, Celery, Model Server auf allen Environments inkl. PROD. Dokumentierte Ausnahme: pg-backup-check CronJob (benötigt Root für `apk add` in Alpine-Container, transient alle 4h, nur API-Calls). Kein `privileged` Mode auf keinem Container. Die zuvor dokumentierte Vespa-Ausnahme (Upstream-Limitation `vm.max_map_count`) entfiel mit dem Vespa-Disable am 2026-04-26.
3. **Phase 3 (optional, vor Abnahme):** `readOnlyRootFilesystem: true` mit vollständigem emptyDir-Mapping. Diminishing Returns für den Aufwand.

**Technischer Hinweis**: Alle Onyx Chart Templates unterstützen `securityContext`-Overrides via Values (`{{- toYaml .Values.<component>.securityContext | nindent 12 }}`). Kein Chart-Umbau nötig — Änderungen ausschließlich in `values-common.yaml`.

### SEC-07: Encryption-at-Rest (ERLEDIGT)

**Verifiziert (2026-03-08)**: StackIT Managed Services bieten Encryption-at-Rest standardmäßig — nicht deaktivierbar.

- **PostgreSQL Flex**: Verschlüsselte SSD-Volumes (AES-256)
- **Object Storage**: Server-Side Encryption (SSE) als Default
- **Status**: Kein Handlungsbedarf, Verschlüsselung ist plattformseitig garantiert

### SEC-08: CORS Einschränkung (OFFEN)

**Finding**: `allow_methods=["*"]` und `allow_headers=["*"]` in `backend/onyx/main.py`. Permissive CORS-Konfiguration auf PROD.

**Bewertung**: Niedriges Risiko — CORS schützt Browser-Clients, nicht APIs. `CORS_ALLOWED_ORIGIN` ist konfigurierbar und sollte auf die PROD-Domain beschränkt werden (`https://chatbot.voeb-service.de`). Methods/Headers einzuschränken ist empfohlen, aber erfordert Analyse welche HTTP-Methoden tatsächlich genutzt werden.

**Status**: Evaluierung vor PROD Go-Live. Core-Datei — kein Hook möglich, direkte Änderung in `main.py`.

### SEC-09: Rate Limiting (IMPLEMENTIERT)

**Finding**: Kein Rate Limiting auf Anwendungsebene. LLM-Backend hat eigene Limits (TPM: 200.000, RPM: 30-600), aber kein Schutz vor missbräuchlicher Nutzung auf unserer Ebene.

**Implementierung (2026-03-16, auf `/api/*` gescopt 2026-04-20)**:

Request-Rate-Limiting via NGINX Ingress Controller ConfigMap (`http-snippet` + `server-snippet`):
- **Pfad-Scope (map):**
  ```
  map $uri $ratelimit_key {
    default      "";
    "~^/api/"    $binary_remote_addr;
  }
  ```
  Nur `/api/*` wird mit der Client-IP als Key gezaehlt. Fuer alle anderen Pfade bleibt der Key leer — NGINX ignoriert leere Keys per Definition (`ngx_http_limit_req_module`), d.h. Seiten-Navigationen und statische Assets passieren ungehindert.
- **Zone:** `limit_req_zone $ratelimit_key zone=ratelimit:10m rate=10r/s` — 10 Requests/Sekunde pro Client-IP auf API-Pfaden, 10 MB Shared Memory (~160.000 IPs)
- **Enforcement:** `limit_req zone=ratelimit burst=50 nodelay` — Burst von 50 Requests erlaubt (deckt API-Bursts bei Page-Load ab), keine Verzoegerung innerhalb des Bursts
- **Status Code:** `limit_req_status 429` (Too Many Requests)
- **Scope:** NUR `/api/*`. Seiten-Routen (`/`, `/app?chatId=...`, `/admin/...`), statische Assets (`/_next/static/*`) und sonstige Ingress-gerouteten Pfade sind NICHT limitiert
- **Konfiguration:** `values-common.yaml` (DEV/TEST) + `values-prod.yaml` (PROD, wegen Helm Deep Merge Duplikation)
- **Client-IP Erhaltung:** `externalTrafficPolicy: Local` auf dem NGINX Ingress Controller Service (alle Environments). Ohne dieses Setting wuerde Kubernetes SNAT anwenden und `$binary_remote_addr` zeigt die interne Node-IP statt der echten Client-IP — alle User wuerden ein einziges Rate-Limit teilen. `Local` leitet Traffic nur an Nodes mit NGINX-Pod weiter und erhaelt die Quell-IP. Bei 1 NGINX-Controller-Pod aendert sich am Routing nichts.

**Scope-Begruendung (2026-04-20):**
- Urspruengliche Konfiguration 2026-03-16: Rate-Limit auf Server-Ebene, alle Requests gezaehlt.
- Problem: Next.js App Router setzt beim Sidebar-Render der Chat-History RSC-Prefetches auf alle sichtbaren Chat-Links (`/app?chatId=xxx&_rsc=seere`). Bei Nutzern mit vielen Chats (>20) entsteht ein paralleler Burst von 20+ Requests innerhalb weniger hundert Millisekunden. Das fuellte den Burst-Bucket komplett, Folge-Navigationen wurden mit HTTP 429 abgewiesen — obwohl diese Seiten-Requests kein LLM ansprechen und keinen DoS-/Kosten-Impact haben.
- Loesung: Rate-Limit nur dort anwenden wo der Schutzbedarf besteht — auf `/api/*` (LLM-Calls, Admin-APIs, Upload). Seiten-Rendering und statische Assets passieren frei.
- Sicherheits-Netto: Unveraendert. Wer einen DoS fahren will, muss trotzdem ueber `/api/*` gehen; dort gelten weiterhin 10 r/s + 50 burst pro Client-IP.

**Werte-Begruendung:**
- 150 User, internes Tool (kein oeffentliches API)
- Normaler Chat-Betrieb: ~0.5 r/s (Nachricht senden + Streaming-Response)
- Page-Load-Burst auf API-Ebene: ~20 parallele API-Calls (Settings, Personas, History, etc.) — bleibt unter Burst=50
- 10 r/s sustained + 50 burst = ein Nutzer muesste >600 Requests/Minute an die API senden um blockiert zu werden
- Konservativ gewaehlt — kann bei Bedarf verschaerft werden

**Defense-in-Depth Schichten (SEC-09 + XREF-007):**
1. NGINX Ingress: `proxy-body-size: 20m` (Request-Groesse)
2. NGINX Ingress: `limit_req 10r/s burst=50` auf `/api/*` (Request-Rate)
3. Backend: `MAX_FILE_SIZE_BYTES: 20971520` (Document-Indexing-Limit)
4. ext-token: Per-User Token-Quotas + Hard Stops (LLM-Kosten)
5. StackIT AI Model Serving: TPM 200.000 + RPM 30-600 (Provider-Limit)

### SEC-10: Cluster-API ACL (OFFEN)

**Finding**: `cluster_acl = ["0.0.0.0/0"]` — SKE Cluster-API ist für das gesamte Internet erreichbar. Zugriff erfordert gültiges Kubeconfig, aber die Angriffsfläche ist unnötig groß.

**Empfehlung**: ACL auf Cluster-Egress-IP + Admin-IP einschränken (analog SEC-01 für PostgreSQL). Umsetzung: `cluster_acl` Variable in `deployment/terraform/environments/{env}/main.tf`.

**Priorität**: P3 — Kubeconfig ist zeitlich begrenzt (90 Tage), aber Best Practice ist Einschränkung.

---

## Incident Response

### Incident Classification

| Severity | Beispiele | Response Time |
|----------|----------|---------------|
| P1 (Critical) | Data Breach, vollständiger Ausfall | 15 Minuten |
| P2 (High) | Teilausfall, Security Misconfiguration | 1 Stunde |
| P3 (Medium) | API-Fehler, Performance-Probleme | 4 Stunden |
| P4 (Low) | Minor Bug, Feature Request | 24 Stunden |

### Incident Response Plan

```
Phase 1: ERKENNUNG
├─ Automatisiert: kube-prometheus-stack (DEV/TEST 2026-03-10, PROD 2026-03-12)
│  ├─ Alert-Rules (Prometheus → AlertManager → Teams Webhook)
│  ├─ DEV/TEST: Teams-Kanal, PROD: separater Teams PROD-Kanal mit [PROD]-Prefix
│  ├─ postgres_exporter + redis_exporter (DB/Cache-Metriken, alle Environments)
│  ├─ Grafana Dashboards (Cluster, PostgreSQL, Redis) — Sidecar-Dashboards auf PROD
│  └─ send_resolved: true (Entwarnung bei Alert-Auflösung)
├─ Smoke Tests in CI/CD (implementiert, PROD: 180s Timeout, 18 Attempts)
└─ Konzept: docs/referenz/monitoring-konzept.md

Phase 2: EINDÄMMUNG
├─ Betroffene Pods isolieren (kubectl)
├─ Namespace-Level: Helm Rollback (manuell, alle Environments nutzen --wait --timeout 15m)
└─ Datenbankebene: PG ACL kann auf [] gesetzt werden

Phase 3: UNTERSUCHUNG
├─ Pod-Logs (kubectl logs)
├─ Kubernetes Events (kubectl describe)
└─ Terraform State (Infrastruktur-Änderungen)

Phase 4: BEHEBUNG
├─ Patch entwickeln und testen
├─ Deployment über CI/CD-Pipeline
└─ Verifizierung über Smoke Tests

Phase 5: KOMMUNIKATION
├─ VÖB informieren (bei P1/P2)
├─ DSGVO-Meldepflicht prüfen (72h bei Datenschutzverletzung)
└─ Dokumentation im Changelog

Phase 6: NACHBEREITUNG
├─ Root Cause Analysis
├─ Runbook aktualisieren
└─ Security-Konzept aktualisieren
```

### Incident Contact List

| Rolle | Name | Kontakt |
|------|------|---------|
| Tech Lead / CCJ | Nikolaj Ivanov | [AUSSTEHEND -- Klärung mit VÖB] |
| VÖB IT / CISO | [AUSSTEHEND -- Klärung mit VÖB] | [AUSSTEHEND -- Klärung mit VÖB] |
| StackIT Support | [AUSSTEHEND -- Klärung mit VÖB] | [AUSSTEHEND -- Klärung mit VÖB] |

---

## Infrastruktur-Übersicht

### StackIT Cloud (Datensouveränität)

| Aspekt | Details |
|--------|---------|
| Provider | StackIT (Schwarz IT, Teil der Schwarz Gruppe) |
| Zertifizierung | **BSI C5 Type 2** (Cloud Computing Compliance Criteria Catalogue) |
| Region | EU01 (Frankfurt am Main, Deutschland) |
| Datensouveränität | Daten verlassen Deutschland nicht |
| Rechenzentrum | Betrieben unter deutschem Recht |
| Container Registry | StackIT eigene Registry (`registry.onstackit.cloud`) |
| LLM-Verarbeitung | StackIT AI Model Serving (in-region) |

### Ressourcen-Übersicht

| Ressource | DEV | PROD |
|-----------|-----|------|
| SKE Cluster | `vob-chatbot` | Eigener Cluster (`vob-prod`, ADR-004) |
| K8s Version | v1.33.9 | v1.33.9 |
| Node Pool | `devtest` (2 Nodes, g1a.4d, downgraded 2026-03-16) | 2x g1a.4d (4 vCPU, 16 GB RAM, downgraded 2026-04-26) |
| Pods | 15 (Vespa entfiel 2026-04-26) | 17 (2x API HA, 2x Web HA, 8 Celery, OpenSearch, Redis, 2x Model, NGINX) |
| PostgreSQL | Flex 2.4 Single (`vob-dev`) | Flex 4.8 HA 3-Node (`vob-prod`) |
| Object Storage | `vob-dev` | `vob-prod` |
| Namespace | `onyx-dev` | `onyx-prod` |
| Monitoring | `monitoring` NS (shared im Cluster) | Eigener (`monitoring` NS, 9 Pods) |
| Container Security | `runAsNonRoot: true` | `runAsNonRoot: true` |
| Deploy-Strategie | Recreate | Recreate (DB Connection Pool Exhaustion vermeiden) |

> TEST-Live-Infrastruktur seit 2026-04-21 abgebaut (Template-Artefakte im Repo).

### Telemetrie

**DEAKTIVIERT**: Onyx-Telemetrie ist explizit ausgeschaltet:

```yaml
# values-common.yaml
configMap:
  DISABLE_TELEMETRY: "true"
```

---

## Referenzen

### Deutsche Regulatorische Standards

- **DSGVO**: https://dsgvo-gesetz.de/
- **BDSG**: https://www.gesetze-im-internet.de/bdsg_2018/
- **EU AI Act** (Verordnung (EU) 2024/1689): https://ai-act-law.eu/de/
- **BSI-Grundschutz**: https://www.bsi.bund.de/DE/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierungen/IT-Grundschutz/it-grundschutz_node.html
- **BSI C5** (StackIT Zertifizierung): https://stackit.com/en/why-stackit/benefits/certificates
- **BAIT** (Rundschreiben 10/2017, Fassung 16.12.2024): https://www.bafin.de/SharedDocs/Downloads/DE/Rundschreiben/dl_rs_1710_ba_BAIT.html
- **DORA** (Verordnung (EU) 2022/2554): https://eur-lex.europa.eu/eli/reg/2022/2554/oj?locale=de
- **BaFin KI-Orientierungshilfe** (18.12.2025): https://www.bafin.de/SharedDocs/Downloads/DE/Anlage/neu/dl_Anlage_orientierungshilfe_IKT_Risiken_bei_KI.html
- **DSK DSFA-Muss-Liste** (V1.1, 17.10.2018): https://www.datenschutzkonferenz-online.de/media/ah/20181017_ah_DSK_DSFA_Muss-Liste_Version_1.1_Deutsch.pdf
- **DSK Orientierungshilfe KI und Datenschutz** (06.05.2024): https://www.datenschutzkonferenz-online.de/media/oh/20240506_DSK_Orientierungshilfe_KI_und_Datenschutz.pdf

### Sicherheits-Frameworks

- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **CIS Benchmarks für Kubernetes**: https://www.cisecurity.org/cis-benchmarks/

### Projekt-Dokumentation

- Implementierungsplan: `docs/referenz/stackit-implementierungsplan.md`
- Technische Referenz: `docs/referenz/stackit-infrastruktur.md`
- ADR-004 (Umgebungstrennung): `docs/adr/adr-004-umgebungstrennung-dev-test-prod.md`
- CI/CD Runbook: `docs/runbooks/ci-cd-pipeline.md`
- DNS/TLS-Runbook: `docs/runbooks/dns-tls-setup.md`
- LLM-Konfiguration Runbook: `docs/runbooks/llm-konfiguration.md`
- Monitoring-Konzept: `docs/referenz/monitoring-konzept.md`
- Monitoring-Exporter Feinkonzept: `docs/technisches-feinkonzept/monitoring-exporter.md`
- Entra ID Fragenkatalog: `docs/entra-id-kundenfragen.md`

---

## Nächste Schritte

### Vor PROD Go-Live (P1)

1. **NetworkPolicies onyx-prod**: Vollständiges Set (default-deny + allow-rules) — kommt mit DNS/TLS-Hardening
2. **Entra ID**: App Registration + Credentials von VÖB IT
4. **M7**: Cluster-API-ACL (`cluster_acl`) von `0.0.0.0/0` auf Cluster-Egress-IP einschränken (empfohlen)

### Vor VÖB-Abnahme (P2)

5. **Penetration Test**: Externe Durchführung
6. **DSGVO-Assessment**: Datenschutz-Folgenabschätzung (DSFA), Auftragsverarbeitungsvertrag (AVV), Löschkonzept, VVT erstellen
7. **EU AI Act Compliance**: KI-Risikobewertung dokumentieren, Art. 4 KI-Kompetenz mit VÖB klären, Art. 50 Transparenzhinweis prüfen

### Opportunistisch (P3 — Nice-to-have)

8. **SEC-04**: Terraform Remote State (bei Teamvergrößerung oder Audit-Anforderung)
9. **SEC-05**: Separate Kubeconfigs (beim Kubeconfig-Renewal 2026-06-14)
10. **SEC-06 Phase 3**: `readOnlyRootFilesystem: true` (diminishing returns)
11. **BAIT/DORA-Compliance-Matrix**: Vollständige Prüfung gegen BAIT/DORA-Anforderungen (freiwillige Orientierung)
12. **IP-Ownership (M3)**: In ADR-001 "CCJ oder VÖB" eindeutig klären

### Dokumentations-Finalisierung

13. Incident Contact List vervollständigen
14. Aufbewahrungsfristen mit VÖB definieren
15. Dieses Dokument auf Version 1.0 bringen (nach Umsetzung aller P1-Items)

### Erledigt

| SEC-Item | Status | Datum |
|----------|--------|-------|
| **SEC-03**: Kubernetes NetworkPolicies (DEV+TEST) | ERLEDIGT | 2026-03-05 |
| **SEC-06 Phase 1**: `privileged: false` (DEV+TEST) | ERLEDIGT | 2026-03-08 |
| **SEC-06 Phase 2**: `runAsNonRoot: true` (alle Environments inkl. PROD) | ERLEDIGT | 2026-03-11 |
| **SEC-07**: Encryption-at-Rest verifiziert (StackIT Default AES-256) | ERLEDIGT | 2026-03-08 |
| **SEC-02**: Node Affinity | ZURÜCKGESTELLT (P3) | 2026-03-08 |
| **SEC-04**: Terraform Remote State | ZURÜCKGESTELLT (P3) | 2026-03-08 |
| **SEC-05**: Separate Kubeconfigs | ZURÜCKGESTELLT (P3) | 2026-03-08 |

---

**Dokumentstatus**: Entwurf (teilweise implementiert)
**Version**: 0.9
**Letzte Aktualisierung**: 2026-04-17
**Nächste Überprüfung**: 2026-07-17

### Versionshistorie

| Version | Datum | Aenderung |
|---------|-------|-----------|
| 0.9 | 2026-04-17 | **Sync #5 + Monitoring-Optimierung + PROD-Rollout dokumentiert.** Upstream PR #9930 entfernte `current_admin_user` → Wrapper in `backend/ext/auth.py` mit `_is_require_permission = True` Sentinel (Onyx Extension-API). Security-Fixes aus Sync #5: SCIM advisory lock (#10048), MCP OAuth hardening (#10074/#10071/#10066), License seat count excludes service accounts (#10053). Monitoring-Optimierung: Alert Fatigue Fix reduziert Risiko ignorierter Security-Alerts; Deep-Health-Endpoint `/api/ext/health/deep` prueft DB+Redis+OpenSearch (public, keine sensitiven Daten); cert-manager-cainjector NetworkPolicy-Fix (ipBlock statt namespaceSelector) sichert TLS-Renewal ab. Core-Dateien: **15** (Core #13 `CustomModal.tsx` entfernt wegen Upstream-Fix, Core #15 `useSettings.ts` neu als Client-Side-Gate fuer ext-branding ohne EE-Lizenz-Flag). Upstream `seed_default_groups` Migration legt 2 neue Default-UserGroups an (Admin id 54, Basic id 55) — kein Namens-Konflikt mit 20 VÖB-Abteilungsgruppen, 91/95 User automatisch in "Basic". PROD-Stand: Chart 0.4.44, Helm Rev 18. |
| 0.8 | 2026-03-22 | OpenSearch PROD, ext-i18n deployed, TLS DEV/PROD LIVE |
