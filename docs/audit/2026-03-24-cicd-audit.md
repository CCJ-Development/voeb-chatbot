# Phase 3: CI/CD Pipeline Validierung

**Audit-Datum:** 2026-03-24
**Scope:** 3 aktive Workflows (stackit-deploy, ci-checks, upstream-check)

---

## 1. Pipeline-Flow

```
Push auf main ──→ ci-checks (parallel: helm-validate + build-backend + build-frontend)
     │
     └──→ stackit-deploy:
            prepare (Tag) → build-backend + build-frontend (parallel) → deploy-dev (auto)
            workflow_dispatch → deploy-test / deploy-prod (manuell)
```

## 2. Secrets-Referenz (13 GitHub Secrets)

| Secret | Scope | Environments |
|---|---|---|
| STACKIT_REGISTRY_USER/PASSWORD | Global | Alle |
| STACKIT_KUBECONFIG | Global | Alle |
| POSTGRES_PASSWORD | Per-Env | DEV/TEST/PROD |
| REDIS_PASSWORD | Per-Env | DEV/TEST/PROD |
| S3_ACCESS_KEY_ID/SECRET | Per-Env | DEV/TEST/PROD |
| DB_READONLY_PASSWORD | Per-Env | DEV/TEST/PROD |
| ENTRA_CLIENT_ID/SECRET/TENANT | Per-Env | DEV/PROD (nicht TEST) |
| USER_AUTH_SECRET | Per-Env | DEV/PROD (nicht TEST) |
| OPENSEARCH_PASSWORD | Per-Env | PROD only |

**Keine Klartext-Credentials in Workflows.**

## 3. Quality Gates

| Check | Vorhanden | Details |
|---|---|---|
| Helm Template Validierung | **JA** | ci-checks: DEV/TEST/PROD mit Dummy-Secrets |
| Docker Build (Backend + Frontend) | **JA** | ci-checks: Build ohne Push |
| Smoke Test nach Deploy | **JA** | HTTP /api/health (12-18 Versuche) |
| Rollout Status Check | **JA** | `kubectl rollout status` (10min Timeout) |
| SHA-gepinnte Actions | **JA** | Alle 5 Third-Party Actions |
| Least-Privilege Permissions | **JA** | `contents: read` |
| PROD Environment Protection | **JA** | Required Reviewers |
| Concurrency Control | **JA** | Per Environment, cancel-in-progress |
| **Helm Lint** | NEIN | — |
| **Helm Dry-Run** | NEIN | — |
| **Image Vulnerability Scan** | NEIN | Kein Trivy/Grype |
| **Dependency Vulnerability Check** | NEIN | Kein pip-audit/npm audit |
| **SAST/Linting** | NEIN | Kein ruff/mypy/tsc im CI |
| **Automatischer Rollback** | NEIN | — |

## 4. Findings

| ID | Severity | Finding | Aufwand | Empfehlung |
|---|---|---|---|---|
| K1 | **CRITICAL** | Keine Image-Vulnerability-Scans | 1h | Trivy nach Build, vor Push |
| H1 | HIGH | Keine Dependency-Checks | 30m | Dependabot aktivieren |
| H2 | HIGH | Keine SAST/Linting im CI | 1-2h | `ruff check` + `tsc --noEmit` |
| H3 | HIGH | Kubeconfig-Ablauf nicht ueberwacht | 30m | Pre-Deploy-Check |
| H4 | HIGH | Kein `helm diff` / `--dry-run` | 30m | Vor Deploy Step |
| H5 | HIGH | Kein automatischer Rollback | 30m | `--atomic` oder failure-Handler |
| M1 | MEDIUM | TEST fehlen OIDC-Secrets | 15m | Bei Reaktivierung ergaenzen |
| M2 | MEDIUM | Upstream-Workflows nicht deaktiviert | 30m | `if: false` einfuegen |
| M3 | MEDIUM | `:latest` Tag wird zusaetzlich gepusht | 15m | Entfernen |
| N1 | LOW | `cancel-in-progress: true` auf PROD | 5m | false fuer PROD |
| N2 | LOW | Smoke Test nur /api/health | 30m | Frontend + Auth pruefen |

## 5. Was gut ist

- SHA-gepinnte GitHub Actions (Supply-Chain-Best-Practice)
- Environment Protection auf PROD (Required Reviewers)
- Docker Build Caching (GHA Cache, scope-getrennt)
- Helm Values-Kaskade (common + env + --set Secrets)
- Security Headers (HSTS, X-Content-Type, X-Frame, Referrer-Policy)
- Rate Limiting (10r/s per IP, burst 50)
