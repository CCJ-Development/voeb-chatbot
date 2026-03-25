# Runbooks — VÖB Service Chatbot

Verifizierte Step-by-Step-Anleitungen für Setup, Deployment und Betrieb der StackIT-Infrastruktur.

> **Hinweis:** Diese Runbooks dokumentieren die **tatsächlich funktionierenden Schritte** — nicht den ursprünglichen Plan. Abweichungen vom [Implementierungsplan](../referenz/stackit-implementierungsplan.md) sind als solche gekennzeichnet.

## Reihenfolge

| # | Runbook | Status | Beschreibung |
|---|---------|--------|-------------|
| 1 | [stackit-projekt-setup.md](./stackit-projekt-setup.md) | ✅ Verifiziert | StackIT CLI, Service Account, Container Registry |
| 2 | [stackit-postgresql.md](./stackit-postgresql.md) | ✅ Verifiziert (2026-03-22) | DB anlegen, Readonly-User, Backup/Restore, Alembic |
| 3 | [helm-deploy.md](./helm-deploy.md) | ✅ Verifiziert (2026-03-22) | Helm Install/Upgrade, Secrets, OpenSearch, Troubleshooting |
| 4 | [ci-cd-pipeline.md](./ci-cd-pipeline.md) | ✅ Verifiziert (2026-03-22) | CI/CD Pipeline: Deploy, Rollback, Secrets, Troubleshooting |
| 5 | [dns-tls-setup.md](./dns-tls-setup.md) | ✅ Verifiziert (2026-03-22) | DNS, cert-manager, Let's Encrypt — DEV+PROD HTTPS LIVE |
| 6 | [llm-konfiguration.md](./llm-konfiguration.md) | ✅ Verifiziert (2026-03-22) | LLM Chat + Embedding Modelle, StackIT AI Model Serving |
| 7 | [rollback-verfahren.md](./rollback-verfahren.md) | ✅ Verifiziert (2026-03-22) | Entscheidungsbaum, Helm/DB-Rollback, Kommunikation |
| 8 | [upstream-sync.md](./upstream-sync.md) | ✅ Verifiziert (2026-03-22) | Upstream-Merge, Hook-Check, Validierung, Deploy |
| 9 | [opensearch-troubleshooting.md](./opensearch-troubleshooting.md) | ✅ Neu (2026-03-22) | Cluster Health, Retrieval-Switch, Recovery |
| 10 | [ip-schutz-helm.md](./ip-schutz-helm.md) | ✅ Neu (2026-03-22) | LB-IP bei Helm-Neuinstallation schuetzen |
| 11 | [alert-antwort.md](./alert-antwort.md) | ✅ Neu (2026-03-22) | Was tun bei Alert? Diagnose + Loesung pro Alert |
| 12 | [secret-rotation.md](./secret-rotation.md) | ✅ Neu (2026-03-22) | Rotation aller PROD Secrets + Kubeconfig + Certs |
| 13 | [entra-id-setup.md](./entra-id-setup.md) | ✅ Verifiziert (2026-03-23) | Entra ID OIDC: App Registration, Secrets, Redirect URIs, Lessons Learned |
| 14 | [ext-access-aktivierung.md](./ext-access-aktivierung.md) | ✅ Neu (2026-03-25) | ext-access: Flag, Deploy, Resync, Funktionstest, Rollback |
| 15 | [loki-troubleshooting.md](./loki-troubleshooting.md) | ✅ Neu (2026-03-25) | Loki: Log-Suche, Promtail, Retention, Troubleshooting |
| 16 | [llm-provider-management.md](./llm-provider-management.md) | ✅ Neu (2026-03-24) | LLM-Provider Verwaltung: Hinzufuegen, Entfernen, Troubleshooting |

## Konventionen

- **Voraussetzungen** stehen am Anfang jedes Runbooks
- **Validierung** steht am Ende — jeder Schritt hat ein erwartetes Ergebnis
- **Abweichungen** vom Implementierungsplan sind mit `> KORREKTUR:` markiert
- Platzhalter wie `<PROJECT_ID>` müssen durch echte Werte ersetzt werden
- Sensible Daten (Keys, Passwörter) werden **nie** in Runbooks dokumentiert

## Referenzen

- [StackIT Implementierungsplan](../referenz/stackit-implementierungsplan.md) — Ursprünglicher Plan
- [StackIT Infrastruktur-Referenz](../referenz/stackit-infrastruktur.md) — Architekturentscheidungen
- [StackIT CLI Docs](https://github.com/stackitcloud/stackit-cli)
- [StackIT Terraform Provider](https://registry.terraform.io/providers/stackitcloud/stackit/latest/docs)
