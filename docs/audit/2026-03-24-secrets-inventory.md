# Phase 1: Secrets Inventory & Klartext-Scan

**Audit-Datum:** 2026-03-24
**Scope:** DEV (onyx-dev), PROD (nicht auditierbar — Kubeconfig expired), Monitoring

---

## 1. Secret Inventory

### 1.1 DEV Cluster (onyx-dev)

| Secret Name | Type | Quelle | Rotation | Finding |
|---|---|---|---|---|
| `onyx-postgresql` | Opaque | CI/CD `--set` | Keine dokumentiert | OK |
| `onyx-redis` | Opaque | CI/CD `--set` | Keine dokumentiert | OK |
| `onyx-objectstorage` | Opaque | CI/CD `--set` | Keine dokumentiert | OK |
| `onyx-dbreadonly` | Opaque | CI/CD `--set` | Keine dokumentiert | OK |
| `onyx-oauth` | Opaque | CI/CD `--set` (Entra ID) | Secret hat Ablaufdatum | OK |
| `onyx-userauth` | Opaque | CI/CD `--set` | Keine dokumentiert | OK |
| `onyx-opensearch` | Opaque | Helm existingSecret (NICHT via `--set`) | Keine | **S-01 MEDIUM** |
| `stackit-registry` | docker-json | Manuell (`kubectl create secret`) | Registry-Token-Ablauf | OK |
| `onyx-dev-ingress-*-tls` (x2) | TLS | cert-manager (auto-renewal) | Auto (90d) | OK |
| 5x `sh.helm.release.v1.*` | helm.sh/release | Helm | N/A | OK (history-max=5) |

### 1.2 Monitoring (DEV Cluster)

| Secret Name | Type | Quelle | Finding |
|---|---|---|---|
| `pg-exporter-dev/test` | Opaque | Manuell | OK (secretKeyRef) |
| `redis-exporter-dev/test` | Opaque | Manuell | OK |
| `monitoring-grafana` | Opaque | Helm `--set` | **S-02 LOW** — Passwort-Management undokumentiert |

### 1.3 PROD (onyx-prod) — NICHT AUDITIERBAR

**S-03 HIGH:** Kubeconfig expired/unauthorized. PROD-Secrets konnten nicht inspiziert werden.

### 1.4 GitHub Actions Secrets

| Secret Name | Scope | Zweck |
|---|---|---|
| `STACKIT_REGISTRY_USER` | Global | Registry Robot Account |
| `STACKIT_REGISTRY_PASSWORD` | Global | Registry Token |
| `STACKIT_KUBECONFIG` | Global | **S-04 MEDIUM** — Einzelne Kubeconfig fuer alle Envs |
| `POSTGRES_PASSWORD` | Per-Env | PG App-User |
| `REDIS_PASSWORD` | Per-Env | Redis Standalone |
| `S3_ACCESS_KEY_ID` | Per-Env | Object Storage |
| `S3_SECRET_ACCESS_KEY` | Per-Env | Object Storage |
| `DB_READONLY_PASSWORD` | Per-Env | PG Readonly |
| `ENTRA_CLIENT_ID` | DEV+PROD | Entra ID |
| `ENTRA_CLIENT_SECRET` | DEV+PROD | Entra ID |
| `ENTRA_TENANT_ID` | DEV+PROD | Entra ID |
| `USER_AUTH_SECRET` | DEV+PROD | JWT Signing |
| `OPENSEARCH_PASSWORD` | PROD only | **S-05 MEDIUM** — fehlt in DEV deploy |

---

## 2. Klartext-Findings

| # | Datei | Severity | Beschreibung |
|---|---|---|---|
| F-01 | `docker_compose/.env` | LOW | `POSTGRES_PASSWORD=password` — Upstream-Default, `.gitignore`'d, nur lokal |
| F-02 | `docker_compose/.env` | LOW | `S3_*=minioadmin` — MinIO-Defaults, `.gitignore`'d |
| F-03 | `charts/onyx/values.yaml` | INFO | Chart-Defaults (`postgres`, `password`, `minioadmin`) — werden durch values-{env} ueberschrieben |
| F-04 | `values-common.yaml:84` | INFO | Kommentar erwaehnt "OnyxDev1!" — nur Kommentar, kein Wert |
| F-05 | `helm/README.md` | LOW | Beispiel-Passwort `StrongPassword123!` in Doku |
| F-06 | `.tfstate` Dateien | MEDIUM | 8 Terraform State Files lokal auf Disk — enthalten PG-Passwoerter, Kubeconfig |

---

## 3. Security Findings

| ID | Severity | Finding | Empfehlung |
|---|---|---|---|
| S-01 | MEDIUM | DEV OpenSearch Passwort nicht via CI/CD injiziert — Herkunft unklar (ggf. Chart-Default) | `--set opensearch_admin_password` in DEV deploy ergaenzen |
| S-02 | LOW | Grafana Admin-Passwort-Management undokumentiert | Prozess dokumentieren |
| S-03 | **HIGH** | PROD Kubeconfig expired — PROD nicht auditierbar | Sofort erneuern |
| S-04 | MEDIUM | Einzelne Kubeconfig fuer alle Envs — gemeinsamer Ablauf | Per-Env Kubeconfigs evaluieren |
| S-05 | MEDIUM | DEV+TEST fehlen OIDC/OpenSearch Secrets im CI/CD | Ergaenzen |
| S-06 | MEDIUM | Terraform State lokal — kein Backup, kein Locking | Remote State Backend migrieren |
| S-07 | INFO | Kein Sealed Secrets / External Secrets Operator | Akzeptiertes Restrisiko (Solo-Dev) |
| S-08 | MEDIUM | Keine Secret-Rotation-Policy implementiert | Rotation Schedule erstellen |

---

## 4. Checklist

- [x] Keine Passwoerter/Keys in `values-*.yaml` im Klartext
- [x] `.gitignore` korrekt (secrets, tfstate, env, kubeconfig)
- [x] GitHub Actions nutzen `${{ secrets.* }}`
- [x] Pod-Env-Vars nutzen secretKeyRef/envFrom
- [ ] **PROD-Secrets auditiert** (blockiert: Kubeconfig expired)
- [ ] **Sealed Secrets oder formelle Risikoakzeptanz** (Nachtrag in ADR-003 vorhanden)
- [ ] **Terraform Remote State** (lokal, kein Backup)
- [ ] **Secret-Rotation Schedule** (Runbook existiert, Schedule fehlt)
