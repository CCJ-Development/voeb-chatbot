# Session-Uebergabe — 2026-03-14

## Was wurde in dieser Session erledigt

### 1. Schnelle Audit-Findings validiert + gefixt
- **K2/K6 (`--atomic` vs `--wait`):** Alle 7 Doku-Dateien korrigiert (Betriebskonzept, Sicherheitskonzept, ADR-004, Abnahmeprotokoll, Meilensteinplan, Rollback-Runbook, CI/CD-Runbook)
- **K5 (PROD Kubeconfig):** Bereits korrekt dokumentiert — geschlossen
- **M13 (AlertManager Egress):** Neue NetworkPolicy `08-allow-alertmanager-webhook-egress.yaml` erstellt + apply.sh aktualisiert. NICHT auf PROD applied (kommt mit vollstaendigem Set)
- **M12 (PG sslmode):** Zurueckgestellt — braucht StackIT-Klaerung

### 2. Betriebskonzept v0.6 + Sicherheitskonzept v0.6
- Betriebskonzept: PROD durchgaengig eingearbeitet (Architektur, PG HA, Monitoring, Skalierung, Wartungsfenster, Extensions)
- Sicherheitskonzept: PROD-Status, SEC-06, Extensions, Monitoring, NetworkPolicies PROD

### 3. Doku-Audit Phase 3 (6 Opus-Agenten parallel, 20+ Dokumente)
- **12 KRITISCHE + ~35 HOHE Findings** identifiziert und gefixt
- Regulatorik: BAIT als freiwillige Orientierung (nicht Pflicht), EU AI Act + DSFA + VVT eingefuegt
- Faktenkorrekturen: PR-Workflow, Migrations-Pfad, PROD Secrets, Embedding (nomic→Qwen3-VL), Extensions
- Testkonzept v0.4: PROD-Sektion real, CI-Automatisierung korrigiert, ext-token/prompts Ergebnisse
- Meilensteinplan v0.4: M3/M4/M5 an Realitaet angepasst, ext-analytics entfernt
- Runbooks: helm-deploy (3-Env Befehle, Secrets-Warnung, PROD-Kubeconfig), dns-tls-setup, rollback
- ADRs: adr-002 (Migrations), adr-003 (Buckets, SEC, --atomic), adr-004 (PROD deployed)
- Referenz-Docs: prod-bereitstellung (Phase F Checkboxen), monitoring-konzept (19 Pods), ee-foss, stackit-*

---

## Commits auf `feature/prod-bereitstellung` (NICHT auf main gemergt)

### Vorherige Session (2026-03-12)
| Hash | Beschreibung |
|------|-------------|
| `4f80c544` | feat(monitoring): Monitoring-Stack PROD deployed |
| `e68964c2` | fix(monitoring): Alert-Tuning + Exporter CPU-Limits PROD |
| `03bcab52` | docs(audit): Phase 1 — 13 Stellen korrigiert |
| `d50c6964` | docs(audit): Phase 2 — 12 Stellen korrigiert |

### Diese Session (2026-03-14)
| Hash | Beschreibung |
|------|-------------|
| TBD | docs(audit): Phase 3 — Regulatorik, Faktenkorrekturen, 20 Dokumente |
| TBD | feat(monitoring): AlertManager Webhook Egress NetworkPolicy |

Untracked (bewusst ausgelassen): `docs/referenz/compliance-research.md`

---

## Offene Findings (brauchen Nikos Entscheidung)

| # | Finding | Optionen |
|---|---------|----------|
| K1 | Teams Webhook-URLs im Git (Klartext) | A) In K8s Secret auslagern B) Risiko akzeptiert (Private Repo, write-only) |
| K3 | NetworkPolicies PROD App-NS | A) Jetzt Full-Set (01-08) applyen B) Warten auf DNS/TLS |
| K4 | DSGVO-Pflichtdokumente | VVT (Art. 30), AVV mit StackIT (Art. 28), DSFA (Art. 35) — Prio? |
| H8 | Content-Security-Policy Header | A) CSP einfuehren B) Zurueckstellen |
| H9 | Rate Limiting auf Ingress | A) NGINX limit-rps jetzt B) Erst bei echten Usern |
| M10 | CORS allow_methods=["*"] | A) Einschraenken B) Erst bei PROD-Go-Live |
| M12 | PG sslmode | Zurueckgestellt (StackIT-Klaerung noetig) |

## Fehlende Dokumentation (aus Audit identifiziert)

| Dokument | Aufwand | Status |
|----------|---------|--------|
| Monitoring-Runbook (Ops) | ~1h | Fehlt komplett |
| NetworkPolicies-Runbook | ~1h | Fehlt komplett |
| Kubeconfig-Renewal-Runbook | ~30min | Fehlt (Ablauf DEV/TEST 2026-05-28, PROD 2026-06-09) |
| ADR-006 Monitoring-Architektur | ~30min | Fehlt |
| ADR-007 Recreate-Strategie | ~30min | Fehlt |

---

## Naechste Schritte (Prioritaet)

1. **Branch auf main mergen** (6+ Commits auf feature/prod-bereitstellung)
2. **DNS PROD abwarten** (Leif/GlobVill, angefragt 2026-03-11)
3. **TLS/HTTPS PROD aktivieren** (sobald DNS steht)
4. **NetworkPolicies PROD** (Full-Set 01-08 inkl. AlertManager-Policy)
5. **CI/CD PROD Re-Run** (gruener Lauf)
6. **M1-Abnahmeprotokoll** finalisieren
7. **Fehlende Runbooks + ADRs** erstellen

## Blocker

| Blocker | Wartet auf | Impact |
|---------|-----------|--------|
| DNS PROD (A-Record + ACME-CNAME) | Leif (GlobVill), angefragt 2026-03-11 | HTTPS PROD |
| Entra ID Zugangsdaten | VoeB IT | Phase 3 |

---

## PROD-Cluster Live-Stand

- **KUBECONFIG:** `~/.kube/config-prod`
- **Cluster:** `vob-prod` (eigener, ADR-004), K8s v1.33.9
- **onyx-prod NS:** 19 Pods Running, 0 NetworkPolicies, LB `188.34.92.162`
- **monitoring NS:** 9 Pods Running, 7 NetworkPolicies, Helm Rev 3
- **Targets:** 3/3 UP (API, PG, Redis)
- **Kubeconfig:** Gueltig bis 2026-06-09
