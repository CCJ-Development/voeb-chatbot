# Runbooks — VÖB Service Chatbot

Verifizierte Step-by-Step-Anleitungen für Setup, Deployment und Betrieb der StackIT-Infrastruktur.

> **Hinweis:** Diese Runbooks dokumentieren die **tatsächlich funktionierenden Schritte** — nicht den ursprünglichen Plan. Abweichungen vom [Implementierungsplan](../referenz/stackit-implementierungsplan.md) sind als solche gekennzeichnet.

> **Für Kunden-Klon-Projekte:** Startpunkt ist [`kunden-klon-onboarding.md`](./kunden-klon-onboarding.md) — das Master-Playbook mit End-to-End-Reihenfolge, Kunden-Variablen-Tabelle und Validierungs-Checkliste.

---

## Kunden-Klon-Setup (Phase-Reihenfolge)

| # | Phase | Runbook | Dauer |
|---|---|---|---|
| — | Master-Playbook (Einstieg) | [kunden-klon-onboarding.md](./kunden-klon-onboarding.md) | Übersicht |
| 1 | StackIT CLI + Service Account + Registry | [stackit-projekt-setup.md](./stackit-projekt-setup.md) | 1 h |
| 2 | Terraform: SKE-Cluster + PG Flex + Object Storage | [terraform-setup.md](./terraform-setup.md) | 2–3 h |
| 3 | PostgreSQL: DB anlegen, Readonly-User, ACL | [stackit-postgresql.md](./stackit-postgresql.md) | 30 min |
| 4 | DNS + TLS (cert-manager, Let's Encrypt) | [dns-tls-setup.md](./dns-tls-setup.md) | 1 h + DNS-Propagation |
| 5 | Helm-Chart + Extensions initial deployen | [helm-deploy.md](./helm-deploy.md) | 1–2 h |
| 6 | Entra ID OIDC einrichten | [entra-id-setup.md](./entra-id-setup.md) | 1 h + Kunden-IT |
| 7 | Monitoring-Stack aufsetzen | [monitoring-setup.md](./monitoring-setup.md) | 2 h |
| 8 | LLM + Embedding-Modelle konfigurieren | [llm-konfiguration.md](./llm-konfiguration.md) | 1 h |
| 9 | Whitelabel (Logo, App-Name, Consent) | [whitelabel-setup.md](./whitelabel-setup.md) | 1 h |
| 10 | CI/CD Pipeline: GitHub Actions + Environments | [ci-cd-pipeline.md](./ci-cd-pipeline.md) | 1 h |
| 11 | PROD-Rollout-Prozess | [prod-deploy.md](./prod-deploy.md) | 1 h |

**Gesamt-Setup:** ca. 12–15 h aktive Arbeit + externe Wartezeiten.

---

## Betriebs-Runbooks (nach Go-Live)

| Runbook | Zweck |
|---|---|
| [upstream-sync.md](./upstream-sync.md) | Onyx-Upstream regelmäßig einziehen (alle 2–4 Wochen) |
| [secret-rotation.md](./secret-rotation.md) | PG-Passwörter, Kubeconfig, Registry-Token rotieren (halbjährlich) |
| [rollback-verfahren.md](./rollback-verfahren.md) | Helm/DB-Rollback bei Deployment-Fehlern |
| [alert-antwort.md](./alert-antwort.md) | Reaktion auf Prometheus-Alerts (pro Alert-Typ) |
| [loki-troubleshooting.md](./loki-troubleshooting.md) | Log-Suche, Promtail, Retention-Probleme |
| [opensearch-troubleshooting.md](./opensearch-troubleshooting.md) | Index-Probleme, Cluster Health, Retrieval-Switch |
| [ip-schutz-helm.md](./ip-schutz-helm.md) | LoadBalancer-IP bei Helm-Neuinstallation schützen |
| [llm-provider-management.md](./llm-provider-management.md) | LLM-Provider hinzufügen/entfernen |
| [ext-access-aktivierung.md](./ext-access-aktivierung.md) | Gruppenbasierte Dokument-ACL aktivieren |
| [ext-analytics-verwaltung.md](./ext-analytics-verwaltung.md) | Analytics-Dashboard pflegen, Endpoints verwalten |

---

## Konventionen

- **Voraussetzungen** stehen am Anfang jedes Runbooks
- **Validierung** steht am Ende — jeder Schritt hat ein erwartetes Ergebnis
- **Abweichungen** vom Implementierungsplan sind mit `> KORREKTUR:` markiert
- **Kunden-Klon-Hinweise** stehen als Banner-Block im Header kundenspezifischer Runbooks
- Platzhalter wie `<PROJECT_ID>`, `<NAMESPACE_DEV>` müssen durch echte Werte ersetzt werden
- Sensible Daten (Keys, Passwörter) werden **nie** in Runbooks dokumentiert

---

## Gesamt

**22 Runbooks:** 1 Master-Playbook + 11 Setup-Runbooks + 10 Betriebs-Runbooks.

## Referenzen

- [Master-Playbook für Kunden-Klon-Setup](./kunden-klon-onboarding.md)
- [Technische Parameter (Single Source of Truth)](../referenz/technische-parameter.md)
- [StackIT Implementierungsplan](../referenz/stackit-implementierungsplan.md)
- [StackIT Infrastruktur-Referenz](../referenz/stackit-infrastruktur.md)
- [StackIT CLI Docs](https://github.com/stackitcloud/stackit-cli)
- [StackIT Terraform Provider](https://registry.terraform.io/providers/stackitcloud/stackit/latest/docs)
