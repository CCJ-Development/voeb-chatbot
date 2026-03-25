# Phase 4: Helm & Kubernetes Coherence Check

**Audit-Datum:** 2026-03-24
**Scope:** DEV (live, Helm Rev 24), PROD (Repo-Analyse — Kubeconfig expired)

---

## 1. Values Drift

### DEV: Kein Drift
Alle Differenzen zwischen Repo-Values und Deployed Values sind durch CI/CD `--set` Overrides erklaerbar (Secrets, Image-Tag, OIDC-URL). **Kein unbeabsichtigter Drift.**

### PROD: Nicht verifizierbar (Kubeconfig expired)

---

## 2. Values-Merging Issues

| Issue | Severity | Details |
|---|---|---|
| Redundante Keys | LOW | `EXT_TOKEN_LIMITS_ENABLED` + `EXT_CUSTOM_PROMPTS_ENABLED` in common UND dev/prod |
| NGINX Deep-Merge | OK | PROD wiederholt korrekt `proxy-body-size`, `server-snippet` (dokumentiert) |
| proxy-body-size | OK | 20m konsistent in common + prod |
| SEC-06 Overrides | OK | PROD korrekt `runAsUser: 1001, runAsNonRoot: true` |
| redisOperator Resources | LOW | PROD fehlt Override — nutzt Chart-Default (500m CPU statt 50m) |
| TEST deploy OIDC | LOW | Fehlende `--set` Flags (TEST heruntergefahren) |

---

## 3. NetworkPolicies

| Namespace | Repo | Cluster | Status |
|---|---|---|---|
| onyx-dev | 7 Policies | 7 Policies | **KOMPLETT** |
| monitoring (DEV) | 9 Policies | 7 Policies | **2 FEHLEN** (AlertManager-Webhook, Backup-Check) |
| onyx-prod | 7 Policies | **UNBEKANNT** | **HIGH — laut Doku noch nicht applied** |

**FINDING H1:** PROD NetworkPolicies hoechstwahrscheinlich nicht applied — kein Default-Deny, aller Traffic uneingeschraenkt.

**FINDING M1:** 2 Monitoring-Policies fehlen:
- `08-allow-alertmanager-webhook-egress` — Alerts zu Teams blockiert
- `09-allow-backup-check-egress` — Backup-Monitoring nicht funktional

---

## 4. Resource Limits

### DEV: Alle Pods haben Requests + Limits
**Ausnahme:** NGINX Controller hat **keine CPU/Memory Limits** (Subchart-Default).

### Pods ohne Limits (DEV)

| Pod | CPU Limit | Memory Limit | Finding |
|---|---|---|---|
| nginx-controller | NONE | NONE | **MEDIUM (PROD)** / LOW (DEV) |

---

## 5. Pod Security

### Namespace PSA Labels
- onyx-dev: **NICHT GESETZT** (kein `pod-security.kubernetes.io/enforce`)
- onyx-prod: Unbekannt (Kubeconfig expired)

### Container Security Context (DEV)

| Container | runAsNonRoot | runAsUser | readOnlyFS |
|---|---|---|---|
| 7x celery-* | NOT SET | 0 (root) | NOT SET |
| 2x model-server | NOT SET | 0 (root) | NOT SET |
| api-server | NOT SET | NOT SET | NOT SET |
| web-server | NOT SET | NOT SET | NOT SET |
| vespa | NOT SET | 0 (root) | NOT SET |
| opensearch | True | 1000 | NOT SET |
| redis | NOT SET | 1000 | NOT SET |
| nginx-controller | True | 101 | False |

**11 Container laufen als root auf DEV.** PROD ist geheartet (values-prod.yaml).

**Kein Container nutzt readOnlyRootFilesystem.**

---

## 6. Ingress & TLS (DEV)

- 2 Ingress-Ressourcen: API (`/api`) + Webserver (`/`)
- TLS: cert-manager mit `onyx-dev-letsencrypt` ClusterIssuer
- 2 separate TLS-Secrets fuer gleiche Domain (akzeptabel, Lesson Learned dokumentiert)
- LoadBalancer IP: `188.34.118.222` (korrekt)

---

## 7. Zusammenfassung

| ID | Severity | Finding |
|---|---|---|
| H1 | **HIGH** | PROD NetworkPolicies nicht applied — kein Default-Deny |
| M1 | MEDIUM | 2 Monitoring NetworkPolicies fehlen (AlertManager, Backup) |
| M2 | MEDIUM | Keine PSA Labels auf Namespaces |
| M3 | MEDIUM | Kein readOnlyRootFilesystem auf Containern |
| L1 | LOW | NGINX Controller ohne Limits |
| L2 | LOW | redisOperator Resource Override wirkungslos |
| L3 | LOW | DEV laeuft 11 Container als root (PROD gehaertet) |
| L4 | LOW | Redundante configMap Keys in env-Values |
