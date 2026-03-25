# Phase 2: Container Images & Registry Audit

**Audit-Datum:** 2026-03-24
**Scope:** DEV (live), PROD (Repo-Analyse — Kubeconfig expired), Monitoring
**Einschraenkung:** PROD-Cluster nicht erreichbar.

---

## 1. Image Inventory (DEV)

| Pod | Image | Tag | Registry | Pull Policy | Finding |
|---|---|---|---|---|---|
| api-server | onyx-backend | `6e6cdaf` | registry.onstackit.cloud | IfNotPresent | OK — SHA-Tag |
| web-server | onyx-web-server | `6e6cdaf` | registry.onstackit.cloud | IfNotPresent | OK |
| 8x celery-* | onyx-backend | `6e6cdaf` | registry.onstackit.cloud | IfNotPresent | OK |
| 2x model-server | onyx-model-server | `v2.9.8` | docker.io/onyxdotapp | IfNotPresent | OK — Semver |
| nginx-controller | ingress-nginx/controller | `v1.13.3@sha256:...` | registry.k8s.io | IfNotPresent | **BEST** — SHA256 Digest |
| vespa | vespa | `8.609.39` | vespaengine (Docker Hub) | IfNotPresent | OK — Semver |
| redis | redis | `v7.0.15` | quay.io/opstree | IfNotPresent | OK |
| opensearch | opensearch | `3.4.0` | opensearchproject (Hub) | IfNotPresent | OK |
| redis-operator | redis-operator | `v0.23.0` | quay.io/opstree | **Always** | LOW — unnoetig |
| **opensearch init** | **busybox** | **`:latest`** | **Docker Hub** | — | **HIGH — unpinned** |

## 2. Registry-Uebersicht

| Registry | Zugriff | Pull Secret | Finding |
|---|---|---|---|
| registry.onstackit.cloud | Privat | `stackit-registry` (dockerconfigjson) | OK |
| docker.io (Docker Hub) | Oeffentlich | Kein | **MEDIUM — Rate Limits** |
| quay.io | Oeffentlich | Kein | OK |
| registry.k8s.io | Oeffentlich | Kein | OK |

## 3. Kritische Findings

| ID | Severity | Finding | Empfehlung |
|---|---|---|---|
| F2-01 | **HIGH** | `busybox:latest` Init Container (OpenSearch) — nicht reproduzierbar, Supply-Chain-Risiko | Auf `busybox:1.37.0` pinnen |
| F2-02 | **HIGH** | PROD Kubeconfig expired — keine Live-Verifikation | Sofort erneuern |
| F2-03 | HIGH | `global.version: "latest"` Default in Values — manuelles Deploy zieht `:latest` | Default auf `"NOT_SET"` aendern |
| F2-04 | HIGH | CI/CD pusht `:latest` Tag zusaetzlich zum SHA | `:latest` aus Build entfernen |
| F2-05 | MEDIUM | Docker Hub ohne Rate-Limit-Mitigation | Registry-Mirror evaluieren |
| F2-06 | MEDIUM | imagePullSecrets nicht auf ServiceAccount-Ebene | ServiceAccount konfigurieren |
| F2-07 | MEDIUM | DEV Container laufen als root (SEC-06 nur auf PROD) | DEV angleichen |
| F2-08 | LOW | redis-operator imagePullPolicy: Always | IfNotPresent |
| F2-09 | LOW | TEST-Exporter laufen noch in Monitoring obwohl TEST heruntergefahren | Auf 0 skalieren |

## 4. Positiv

- Eigene Images: SHA-getagged, konsistent deployed
- GitHub Actions: SHA-gepinnte Action-Referenzen
- NGINX Controller: SHA256 Digest-Pin
- Model Server: Zentral gepinnt (`v2.9.8`)
- PROD Non-Root: SEC-06 korrekt in values-prod.yaml
