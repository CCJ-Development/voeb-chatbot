# VÖB Service Chatbot — Dokumentation

Enterprise-AI-Chatbot basierend auf Onyx FOSS mit Custom Extension Layer für den Bundesverband Öffentlicher Banken Deutschlands.

## Dokumente

| Dokument | Status | Beschreibung |
|----------|--------|-------------|
| [sicherheitskonzept.md](./sicherheitskonzept.md) | Entwurf | Verschlüsselung, Auth, LLM-Sicherheit, DSGVO |
| [testkonzept.md](./testkonzept.md) | Entwurf | Teststrategie, Testfälle, Abnahmekriterien |
| [betriebskonzept.md](./betriebskonzept.md) | Entwurf | Deployment, Monitoring, Backup, Incident Management |
| [CHANGELOG.md](./CHANGELOG.md) | Aktiv | Versionshistorie (Keep a Changelog) |
| [entra-id-kundenfragen.md](./entra-id-kundenfragen.md) | Entwurf | Fragenkatalog zu Microsoft Entra ID für VÖB |

## Ordner

| Ordner | Inhalt |
|--------|--------|
| [technisches-feinkonzept/](./technisches-feinkonzept/) | Modulspezifikationen (Template + je eine Spec pro Feature-Modul) |
| [adr/](./adr/) | Architecture Decision Records (ADR-001 bis ADR-005) |
| [abnahme/](./abnahme/) | Abnahmeprotokoll-Template + Meilensteinplan |
| [runbooks/](./runbooks/) | Verifizierte Step-by-Step-Anleitungen (StackIT Setup, Deploy, Betrieb) |
| [referenz/](./referenz/) | Implementierungsplan, Infrastruktur-Specs, Container Registry |
| [audit/](./audit/) | Cloud-Infrastruktur-Audit, NetworkPolicy-Analyse |

## Architecture Decision Records

| ADR | Status | Beschreibung |
|-----|--------|-------------|
| [ADR-001](./adr/adr-001-onyx-foss-als-basis.md) | Akzeptiert | Onyx FOSS als Basis-Plattform |
| [ADR-002](./adr/adr-002-extension-architektur.md) | Akzeptiert | Extension-Architektur (Extend, don't modify) |
| [ADR-003](./adr/adr-003-stackit-als-cloud-provider.md) | Akzeptiert | StackIT als Cloud Provider |
| [ADR-004](./adr/adr-004-umgebungstrennung-dev-test-prod.md) | Akzeptiert | Umgebungstrennung DEV / TEST / PROD |
| [ADR-005](./adr/adr-005-node-upgrade-g1a8d.md) | Akzeptiert | Node-Upgrade g1a.4d → g1a.8d |

## Runbooks

| Runbook | Status | Beschreibung |
|---------|--------|-------------|
| [stackit-projekt-setup.md](./runbooks/stackit-projekt-setup.md) | Verifiziert | StackIT CLI, Service Account, Container Registry |
| [stackit-postgresql.md](./runbooks/stackit-postgresql.md) | Verifiziert | PostgreSQL Flex Setup, User-Verwaltung, DB anlegen |
| [helm-deploy.md](./runbooks/helm-deploy.md) | Verifiziert | Helm Values, Deploy, Troubleshooting |
| [ci-cd-pipeline.md](./runbooks/ci-cd-pipeline.md) | Verifiziert | CI/CD Pipeline Setup, Secrets, Debugging |
| [dns-tls-setup.md](./runbooks/dns-tls-setup.md) | ✅ Verifiziert (LIVE seit 2026-03-09) | DNS/TLS Setup — cert-manager, Let's Encrypt, Cloudflare |
| [llm-konfiguration.md](./runbooks/llm-konfiguration.md) | Verifiziert | LLM-Konfiguration — Chat + Embedding Modelle |
| [rollback-verfahren.md](./runbooks/rollback-verfahren.md) | Verifiziert | Rollback-Runbook — Entscheidungsbaum, Helm/DB-Rollback, Post-Mortem |

## Referenzdokumente

| Dokument | Status | Beschreibung |
|----------|--------|-------------|
| [stackit-implementierungsplan.md](./referenz/stackit-implementierungsplan.md) | Aktuell | Step-by-Step DEV+TEST Infrastruktur (Phase 1-7) |
| [stackit-infrastruktur.md](./referenz/stackit-infrastruktur.md) | Aktuell | StackIT Specs, Sizing, Environments-Tabelle |
| [stackit-container-registry.md](./referenz/stackit-container-registry.md) | Aktuell | Container Registry Konzepte, Auth, Robot Accounts |
| [ee-foss-abgrenzung.md](./referenz/ee-foss-abgrenzung.md) | Aktuell | EE/FOSS-Lizenzabgrenzung, was erlaubt/verboten ist |
| [ext-entwicklungsplan.md](./referenz/ext-entwicklungsplan.md) | Aktuell | Extension-Module Reihenfolge, Workflow, Dependencies |
| [monitoring-konzept.md](./referenz/monitoring-konzept.md) | Aktuell | Monitoring-Stack: Prometheus, Grafana, AlertManager, Exporter |
| [compliance-research.md](./referenz/compliance-research.md) | Entwurf | DSGVO, BSI, EU AI Act — Compliance-Analyse und Handlungsbedarf |
| [prod-bereitstellung.md](./referenz/prod-bereitstellung.md) | Aktuell | PROD-Bereitstellungsplan |
| [kostenvergleich-node-upgrade.md](./referenz/kostenvergleich-node-upgrade.md) | Aktuell | Kostenvergleich Node-Upgrade |

## Technisches Feinkonzept

| Dokument | Status | Beschreibung |
|----------|--------|-------------|
| [template-modulspezifikation.md](./technisches-feinkonzept/template-modulspezifikation.md) | Final | Template fuer Modulspezifikationen |
| [ext-framework.md](./technisches-feinkonzept/ext-framework.md) | Final | Extension Framework Basis (Phase 4a) |
| [ext-branding.md](./technisches-feinkonzept/ext-branding.md) | Final | Branding/Whitelabel Modul (Phase 4b) |
| [ext-token.md](./technisches-feinkonzept/ext-token.md) | Final | Token Limits + Usage Tracking (Phase 4c) |
| [ext-custom-prompts.md](./technisches-feinkonzept/ext-custom-prompts.md) | Final | Custom System Prompts (Phase 4d) |
| [monitoring-exporter.md](./technisches-feinkonzept/monitoring-exporter.md) | Final | PostgreSQL + Redis Exporter (Monitoring) |

## Environments

| Environment | Status | URL / IP | Cluster |
|-------------|--------|----------|---------|
| **DEV** | LIVE seit 2026-02-27 | `https://dev.chatbot.voeb-service.de` | SKE `vob-chatbot`, NS `onyx-dev` |
| **TEST** | LIVE seit 2026-03-03 | `https://test.chatbot.voeb-service.de` | SKE `vob-chatbot`, NS `onyx-test` |
| **PROD** | Deployed seit 2026-03-11 (DNS/TLS pending) | LB `188.34.92.162` | SKE `vob-prod`, NS `onyx-prod` |

## Kontakt

| Rolle | Organisation | Person |
|-------|-------------|--------|
| Technische Leitung | CCJ / Coffee Studios | Nikolaj Ivanov |
| Projektmanagement | CCJ / Coffee Studios | Benito-Miguel Schwankhart |
| Auftraggeber | VÖB | Luca Koenes |

Letzte Aktualisierung: 2026-03-12
