# Cloud Stack Security & Coherence Audit — Gesamtbewertung

**Audit-Datum:** 2026-03-24
**Auditor:** Nikolaj Ivanov (CCJ)
**Scope:** DEV (live), PROD (Repo-Analyse, Kubeconfig expired), Monitoring
**Einschraenkung:** PROD-Cluster war nicht erreichbar (Kubeconfig expired). Alle PROD-Bewertungen basieren auf Repo-Analyse und CI/CD Workflow.

---

## Compliance Scorecard

| Bereich | Score | Begruendung |
|---------|-------|------------|
| Secrets Management | **7/10** | Architektur solide (GitHub Secrets → Helm → K8s). Abzuege: kein Remote State, kein Rotation-Schedule, PROD nicht auditierbar |
| Container Security | **6/10** | SHA-getagged, private Registry, PROD Non-Root. Abzuege: busybox:latest, kein Image-Scanning, DEV laeuft als root |
| CI/CD Maturity | **6/10** | SHA-gepinnte Actions, Environment Protection, Smoke Tests. Abzuege: kein Vuln-Scan, kein SAST, kein Rollback |
| Config Coherence | **7/10** | Kein Drift DEV, Values gut dokumentiert. Abzuege: PROD NPs fehlen, PROD nicht verifizierbar |
| Dokumentation Accuracy | **5/10** | Umfangreiche Doku-Suite. Abzuege: 12+ veraltete Eintraege, SSOT stimmt in 8 Feldern nicht |
| **Gesamt** | **31/50** | **Solide Basis, aber Doku-Aktualitaet und fehlende Security-Scans druecken die Bewertung** |

---

## Kritische Findings (sofort beheben)

| # | Finding | Phase | Severity | Env | Aufwand |
|---|---------|-------|----------|-----|---------|
| C-01 | **PROD Kubeconfig expired** — kein Cluster-Zugriff, kein Audit, kein Notfall-Zugang | 1,2,4 | CRITICAL | PROD | 15m |
| C-02 | **Keine Image-Vulnerability-Scans** im CI — CVEs unerkannt in PROD-Images | 3 | CRITICAL | Alle | 1h |

---

## Wichtige Findings (innerhalb 1 Woche)

| # | Finding | Phase | Severity | Env | Aufwand |
|---|---------|-------|----------|-----|---------|
| H-01 | **PROD NetworkPolicies nicht applied** — kein Default-Deny, aller Traffic uneingeschraenkt | 4 | HIGH | PROD | 30m |
| H-02 | `busybox:latest` Init Container (OpenSearch) — nicht reproduzierbar, Supply-Chain-Risiko | 2 | HIGH | DEV+PROD | 15m |
| H-03 | Keine Dependency-Vulnerability-Checks (pip-audit, npm audit, Dependabot) | 3 | HIGH | Alle | 30m |
| H-04 | Keine SAST/Linting im CI (ruff, mypy, tsc deaktiviert) | 3 | HIGH | Alle | 1-2h |
| H-05 | `global.version: "latest"` als Default — manuelles Deploy zieht `:latest` | 2 | HIGH | Alle | 5m |
| H-06 | Kein `helm diff` / `--dry-run` vor Deploy | 3 | HIGH | Alle | 30m |
| H-07 | Kein automatischer Rollback bei Deployment-Fehler | 3 | HIGH | Alle | 30m |
| H-08 | 8+ veraltete Eintraege in technische-parameter.md (SSOT!) | 5 | HIGH | Doku | 30m |
| H-09 | Sicherheitskonzept nicht aktuell (Entra ID, TEST, NP-Count) | 5 | HIGH | Doku | 30m |

---

## Mittlere Findings (innerhalb 2 Wochen)

| # | Finding | Phase | Severity | Env | Aufwand |
|---|---------|-------|----------|-----|---------|
| M-01 | DEV OpenSearch Passwort nicht via CI/CD — Herkunft unklar | 1 | MEDIUM | DEV | 15m |
| M-02 | 2 Monitoring NetworkPolicies fehlen (AlertManager-Webhook, Backup-Check) | 4 | MEDIUM | DEV | 15m |
| M-03 | Terraform State lokal — kein Backup, kein Locking, kein Multi-Dev | 1 | MEDIUM | Infra | 2h |
| M-04 | Keine Secret-Rotation-Policy (Schedule fehlt, Entra-Secret-Ablauf nicht ueberwacht) | 1 | MEDIUM | PROD | 30m |
| M-05 | Keine PSA Labels auf Namespaces (`pod-security.kubernetes.io/enforce`) | 4 | MEDIUM | Alle | 15m |
| M-06 | Kein readOnlyRootFilesystem auf Containern | 4 | MEDIUM | Alle | 2h |
| M-07 | Docker Hub ohne Rate-Limit-Mitigation (100 pulls/6h anon) | 2 | MEDIUM | Alle | 2h |
| M-08 | CI/CD pusht `:latest` Tag zusaetzlich zum SHA | 2 | MEDIUM | CI/CD | 5m |
| M-09 | Upstream-Workflows nicht deaktiviert (`build-deploy.yml` hat workflow_dispatch) | 3 | MEDIUM | CI/CD | 30m |
| M-10 | ADR-006 Status "Proposed" statt "Akzeptiert" | 5 | MEDIUM | Doku | 5m |

---

## Niedrige Findings (Backlog)

| # | Finding | Phase | Env | Aufwand |
|---|---------|-------|-----|---------|
| L-01 | NGINX Controller ohne CPU/Memory Limits | 4 | Alle | 15m |
| L-02 | DEV laeuft 11 Container als root (PROD gehaertet) | 4 | DEV | 15m |
| L-03 | redis-operator imagePullPolicy: Always | 2 | DEV | 5m |
| L-04 | TEST-Exporter laufen in Monitoring obwohl TEST down | 2 | DEV | 5m |
| L-05 | Redundante configMap Keys in env-Values | 4 | Repo | 10m |
| L-06 | redisOperator Resource Override wirkungslos | 4 | DEV | 15m |
| L-07 | TEST deploy fehlen OIDC --set Flags | 3 | CI/CD | 15m |
| L-08 | Grafana Admin-Passwort-Management undokumentiert | 1 | Monitoring | 10m |
| L-09 | ADR-004 erwaehnt TEST-Shutdown nicht | 5 | Doku | 10m |
| L-10 | Fehlende ADR fuer OIDC-Implementierung | 5 | Doku | 30m |
| L-11 | Smoke Test nur /api/health | 3 | CI/CD | 30m |
| L-12 | cancel-in-progress: true auf PROD | 3 | CI/CD | 5m |
| L-13 | imagePullSecrets nicht auf ServiceAccount-Ebene | 2 | DEV | 15m |
| L-14 | Einzelne Kubeconfig fuer alle Envs | 1 | Infra | 30m |

---

## Massnahmenplan

### Sprint 1: Kritisch (diese Woche)

| # | Massnahme | Finding | Aufwand |
|---|----------|---------|---------|
| **M-01** | **PROD Kubeconfig erneuern** (`terraform apply -target` oder StackIT Portal), lokal + GitHub Secret aktualisieren | C-01 | 15m |
| **M-02** | **PROD-Audit nachholen** — nach Kubeconfig-Erneuerung Secrets, Images, NPs, Security Context verifizieren | C-01 | 1h |
| **M-03** | **PROD NetworkPolicies anwenden** — `deployment/k8s/network-policies/` auf `onyx-prod` | H-01 | 30m |
| **M-04** | **Trivy im CI** — `trivy image --exit-code 1 --severity CRITICAL,HIGH` nach Build, vor Push | C-02 | 1h |
| **M-05** | **technische-parameter.md aktualisieren** — 8 veraltete Felder korrigieren | H-08 | 30m |

### Sprint 2: Wichtig (naechste Woche)

| # | Massnahme | Finding | Aufwand |
|---|----------|---------|---------|
| M-06 | busybox auf `1.37.0` pinnen (OpenSearch Subchart Override) | H-02 | 15m |
| M-07 | Dependabot aktivieren (`.github/dependabot.yml`) | H-03 | 30m |
| M-08 | `ruff check` + `tsc --noEmit` in ci-checks.yml | H-04 | 1-2h |
| M-09 | `global.version` Default auf `"NOT_SET"` aendern | H-05 | 5m |
| M-10 | `helm upgrade --dry-run` vor Deploy | H-06 | 30m |
| M-11 | Rollback-Logik im failure-Handler | H-07 | 30m |
| M-12 | Sicherheitskonzept v0.9 — Entra ID, TEST, NPs aktualisieren | H-09 | 30m |
| M-13 | 2 fehlende Monitoring-NPs applyen | M-02 | 15m |
| M-14 | DEV OpenSearch `--set` in CI/CD ergaenzen | M-01 | 15m |

### Sprint 3: Mittel (innerhalb 2 Wochen)

| # | Massnahme | Finding | Aufwand |
|---|----------|---------|---------|
| M-15 | Secret-Rotation-Schedule erstellen (Tabelle mit Ablaufdaten) | M-04 | 30m |
| M-16 | PSA Labels auf Namespaces (`enforce: baseline`) | M-05 | 15m |
| M-17 | `:latest` Tag aus CI/CD Build entfernen | M-08 | 5m |
| M-18 | Upstream-Workflows mit `if: false` deaktivieren | M-09 | 30m |
| M-19 | ADR-006 Status → "Akzeptiert" | M-10 | 5m |

### Backlog (nach M1-Abnahme)

| # | Massnahme | Finding | Aufwand |
|---|----------|---------|---------|
| M-20 | Terraform Remote State Backend | M-03 | 2h |
| M-21 | readOnlyRootFilesystem evaluieren | M-06 | 2h |
| M-22 | Docker Hub Registry Mirror | M-07 | 2h |
| M-23 | NGINX Controller Limits setzen | L-01 | 15m |
| M-24 | DEV Security Context an PROD angleichen | L-02 | 15m |
| M-25 | TEST-Exporter herunterfahren | L-04 | 5m |

---

## Was gut ist (Positiv-Befunde)

| Bereich | Detail |
|---------|--------|
| **Secrets-Architektur** | GitHub Secrets → Helm `--set` → K8s Secrets. Keine Klartext-Credentials in Git. |
| **Supply-Chain** | Alle GitHub Actions SHA-gepinnt. Model Server Version zentral gepinnt. |
| **Image-Tagging** | Eigene Images: Git-SHA-getagged. NGINX Controller: SHA256 Digest. |
| **Environment Protection** | PROD: Required Reviewers + 7 Environment Secrets. |
| **TLS/HTTPS** | TLSv1.3, ECDSA P-384, cert-manager Auto-Renewal, HSTS. BSI TR-02102-2 konform. |
| **PROD-Haertung** | runAsNonRoot, PG HA 3-Node, 2x API/Web HA, Rate Limiting, Security Headers. |
| **Network Segmentation** | DEV: 7 NPs inkl. Default-Deny. Monitoring: 7 NPs. |
| **Monitoring** | kube-prometheus-stack, PG+Redis Exporter, Teams Alerting, 20-22 Alert-Rules. |
| **Doku-Umfang** | 60+ Dateien, ADRs, Runbooks, Konzepte. Substanz ist da — Aktualitaet fehlt. |
| **Secret-Rotation Runbook** | Ausfuehrlich dokumentiert fuer alle 7 Secret-Typen. |
| **Backup-Konzept** | PG Backups konfiguriert, Restore-Test durchgefuehrt (2026-03-15). |
| **Kosten-Transparenz** | Detaillierte Kostenaufstellung in SSOT, aktuelle Werte. |

---

## Fazit

**Gesamteindruck: Solides Fundament mit Luecken in Automatisierung und Aktualitaet.**

Die Infrastruktur ist fuer ein Solo-Dev-Enterprise-Projekt bemerkenswert gut aufgestellt. Die Architektur (eigene Registry, SHA-Tags, Environment Protection, NetworkPolicies, Non-Root PROD) ist durchdacht. Die zwei **kritischen** Handlungsbedarfe sind:

1. **PROD Kubeconfig sofort erneuern** — ohne Cluster-Zugriff ist kein Notfall-Eingriff moeglich
2. **Image-Vulnerability-Scanning einrichten** — BSI APP.4.4.A7 fordert automatisierte Audits

Danach Prioritaet auf **PROD NetworkPolicies** (Default-Deny) und **CI/CD-Haertung** (SAST, Dependency-Checks, Dry-Run, Rollback).

Die Dokumentation ist umfangreich aber in 12+ Stellen veraltet. Die SSOT (`technische-parameter.md`) muss nach jedem groesseren Change aktualisiert werden — ein Post-Deploy-Step oder Checklisten-Item koennte helfen.

---

## Referenzen

| Phase | Datei |
|-------|-------|
| 1 — Secrets | `docs/audit/2026-03-24-secrets-inventory.md` |
| 2 — Images | `docs/audit/2026-03-24-image-audit.md` |
| 3 — CI/CD | `docs/audit/2026-03-24-cicd-audit.md` |
| 4 — Helm/K8s | `docs/audit/2026-03-24-helm-coherence-report.md` |
| 5 — Doku vs. Realitaet | `docs/audit/2026-03-24-doc-reality-gap.md` |
| 6 — Zusammenfassung | dieses Dokument |
