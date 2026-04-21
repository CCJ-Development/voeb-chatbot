# VÖB Service Chatbot — Dokumentation

Enterprise-AI-Chatbot basierend auf Onyx FOSS mit Custom Extension Layer für die VÖB-Service GmbH.

## Konzept-Dokumente

| Dokument | Status | Beschreibung |
|----------|--------|-------------|
| [sicherheitskonzept.md](./sicherheitskonzept.md) | Entwurf (laufend) | Verschlüsselung, Auth, LLM-Sicherheit, DSGVO, BAIT-Orientierung |
| [sicherheitsarchitektur.md](./sicherheitsarchitektur.md) | Entwurf 0.1 | Defense-in-Depth, Trust Boundaries, Responsibility-Matrix, Compliance-Mapping (Audit-Version) |
| [testkonzept.md](./testkonzept.md) | Entwurf | Teststrategie, Testfälle, Abnahmekriterien |
| [betriebskonzept.md](./betriebskonzept.md) | Entwurf | Deployment, Monitoring, Backup, Incident Management |
| [backup-recovery-konzept.md](./backup-recovery-konzept.md) | Aktuell | Backup-Strategie, RTO/RPO, Restore-Prozess |
| [CHANGELOG.md](./CHANGELOG.md) | Aktiv | Versionshistorie (Keep a Changelog) |

## Entwürfe (VÖB-seitig zu vervollständigen)

| Dokument | Status | Inhalt |
|----------|--------|--------|
| [dsfa-entwurf.md](./dsfa-entwurf.md) | Entwurf | Datenschutz-Folgenabschätzung (Art. 35 DSGVO) |
| [vvt-entwurf.md](./vvt-entwurf.md) | Entwurf | Verzeichnis der Verarbeitungstätigkeiten (Art. 30 DSGVO) |
| [loeschkonzept-entwurf.md](./loeschkonzept-entwurf.md) | Entwurf | Löschkonzept nach Art. 17 DSGVO |
| [ki-risikobewertung-entwurf.md](./ki-risikobewertung-entwurf.md) | Entwurf | KI-Risikobewertung EU AI Act |
| [entra-id-kundenfragen.md](./entra-id-kundenfragen.md) | Entwurf | Fragenkatalog zu Microsoft Entra ID |

## Architecture Decision Records (ADR)

| ADR | Status | Thema |
|-----|--------|-------|
| [ADR-001](./adr/adr-001-onyx-foss-als-basis.md) | Akzeptiert | Onyx FOSS als Basis-Plattform |
| [ADR-002](./adr/adr-002-extension-architektur.md) | Akzeptiert | Extension-Architektur ("Extend, don't modify") |
| [ADR-003](./adr/adr-003-stackit-als-cloud-provider.md) | Akzeptiert | StackIT als Cloud Provider |
| [ADR-004](./adr/adr-004-umgebungstrennung-dev-test-prod.md) | Akzeptiert | Umgebungstrennung DEV / TEST / PROD |
| [ADR-005](./adr/adr-005-node-upgrade-g1a8d.md) | Akzeptiert | Node-Upgrade g1a.4d → g1a.8d |
| [ADR-006](./adr/adr-006-vpn-zu-https-oidc.md) | In Diskussion | VPN-Schicht vs. HTTPS+OIDC |

## Runbooks (Verifizierte Step-by-Step-Anleitungen)

| Runbook | Thema |
|---------|-------|
| [stackit-projekt-setup.md](./runbooks/stackit-projekt-setup.md) | StackIT CLI, Service Account, Container Registry |
| [stackit-postgresql.md](./runbooks/stackit-postgresql.md) | PostgreSQL Flex Setup, User-Verwaltung |
| [helm-deploy.md](./runbooks/helm-deploy.md) | Helm Values, Deploy, Troubleshooting |
| [ci-cd-pipeline.md](./runbooks/ci-cd-pipeline.md) | CI/CD Pipeline, Secrets, Debugging |
| [prod-deploy.md](./runbooks/prod-deploy.md) | 6-Schritte-Template für PROD-Rollouts |
| [dns-tls-setup.md](./runbooks/dns-tls-setup.md) | cert-manager, Let's Encrypt, Cloudflare |
| [entra-id-setup.md](./runbooks/entra-id-setup.md) | Entra ID OIDC-Einrichtung |
| [llm-konfiguration.md](./runbooks/llm-konfiguration.md) | Chat + Embedding-Modelle konfigurieren |
| [llm-provider-management.md](./runbooks/llm-provider-management.md) | LLM-Provider-Rotation, Fallbacks |
| [rollback-verfahren.md](./runbooks/rollback-verfahren.md) | Helm/DB-Rollback, Post-Mortem |
| [upstream-sync.md](./runbooks/upstream-sync.md) | Upstream-Merge-Prozess, Konflikt-Lösung |
| [secret-rotation.md](./runbooks/secret-rotation.md) | Rotation von API-Tokens, Credentials |
| [alert-antwort.md](./runbooks/alert-antwort.md) | Alert-Reaktion, Eskalation |
| [loki-troubleshooting.md](./runbooks/loki-troubleshooting.md) | Loki Log-Aggregation Debugging |
| [opensearch-troubleshooting.md](./runbooks/opensearch-troubleshooting.md) | OpenSearch Index-Probleme |
| [ext-access-aktivierung.md](./runbooks/ext-access-aktivierung.md) | ext-access (Dokument-Zugriffskontrolle) aktivieren |
| [ext-analytics-verwaltung.md](./runbooks/ext-analytics-verwaltung.md) | ext-analytics-Dashboard pflegen |
| [ip-schutz-helm.md](./runbooks/ip-schutz-helm.md) | IP-Allowlisting in Helm |

## Referenzdokumente

| Dokument | Beschreibung |
|----------|-------------|
| [technische-parameter.md](./referenz/technische-parameter.md) | **Single Source of Truth** für Versionen, Ressourcen, Kosten, Umgebungen |
| [stackit-infrastruktur.md](./referenz/stackit-infrastruktur.md) | StackIT-Specs, Sizing, Environments |
| [stackit-implementierungsplan.md](./referenz/stackit-implementierungsplan.md) | Step-by-Step DEV/PROD Infrastruktur (Phase 1-7) |
| [stackit-container-registry.md](./referenz/stackit-container-registry.md) | Container Registry, Auth, Robot Accounts |
| [monitoring-konzept.md](./referenz/monitoring-konzept.md) | Prometheus, Grafana, AlertManager, Exporter |
| [ee-foss-abgrenzung.md](./referenz/ee-foss-abgrenzung.md) | EE/FOSS-Lizenzabgrenzung |
| [ext-entwicklungsplan.md](./referenz/ext-entwicklungsplan.md) | Extension-Module Reihenfolge, Dependencies |
| [prod-bereitstellung.md](./referenz/prod-bereitstellung.md) | PROD-Bereitstellungsplan |
| [rbac-rollenmodell.md](./referenz/rbac-rollenmodell.md) | RBAC-Rollenmodell (ext-rbac) |
| [llm-access-control.md](./referenz/llm-access-control.md) | LLM-Zugriffskontrolle |
| [compliance-research.md](./referenz/compliance-research.md) | DSGVO, BSI, EU AI Act — Compliance-Analyse |
| [kostenoptimierung-dev-test.md](./referenz/kostenoptimierung-dev-test.md) | Historische Kostenoptimierung DEV+TEST |
| [kostenvergleich-node-upgrade.md](./referenz/kostenvergleich-node-upgrade.md) | Historische Node-Upgrade-Analyse |
| [kickoff-meeting-notizen.md](./referenz/kickoff-meeting-notizen.md) | Notizen vom Kickoff-Meeting |
| [stackit-offene-fragen.md](./referenz/stackit-offene-fragen.md) | Offene Punkte mit StackIT |
| [mail-entwurf-rbac-voeb.md](./referenz/mail-entwurf-rbac-voeb.md) | E-Mail-Entwurf zum RBAC-Rollenmodell |
| [review-antwort-node-upgrade.md](./referenz/review-antwort-node-upgrade.md) | Historische Review-Antwort |

## Technisches Feinkonzept (Modulspezifikationen)

| Dokument | Phase | Beschreibung |
|----------|-------|-------------|
| [template-modulspezifikation.md](./technisches-feinkonzept/template-modulspezifikation.md) | — | Template für neue Modulspezifikationen |
| [ext-framework.md](./technisches-feinkonzept/ext-framework.md) | 4a | Extension Framework Basis |
| [ext-auth.md](./technisches-feinkonzept/ext-auth.md) | Util | `current_admin_user`-Wrapper nach Upstream PR #9930 |
| [ext-branding.md](./technisches-feinkonzept/ext-branding.md) | 4b | Branding/Whitelabel |
| [ext-branding-logo-editor.md](./technisches-feinkonzept/ext-branding-logo-editor.md) | 4b | Logo-Editor (Crop/Zoom-Tool) |
| [ext-token.md](./technisches-feinkonzept/ext-token.md) | 4c | Token Limits + Usage Tracking |
| [ext-custom-prompts.md](./technisches-feinkonzept/ext-custom-prompts.md) | 4d | Custom System Prompts |
| [ext-analytics.md](./technisches-feinkonzept/ext-analytics.md) | 4e | Plattform-Nutzungsanalysen |
| [ext-rbac.md](./technisches-feinkonzept/ext-rbac.md) | 4f | Gruppenverwaltung |
| [ext-access.md](./technisches-feinkonzept/ext-access.md) | 4g | Dokument-Zugriffskontrolle |
| [ext-i18n.md](./technisches-feinkonzept/ext-i18n.md) | 4h | Deutsche Lokalisierung |
| [ext-audit.md](./technisches-feinkonzept/ext-audit.md) | 4i | Audit-Logging |
| [monitoring-exporter.md](./technisches-feinkonzept/monitoring-exporter.md) | — | PostgreSQL + Redis Exporter |

## Meilensteine / Abnahme

| Dokument | Beschreibung |
|----------|-------------|
| [abnahme/meilensteinplan.md](./abnahme/meilensteinplan.md) | Meilensteinplan M1-M6 |
| [abnahme/abnahmeprotokoll-m1.md](./abnahme/abnahmeprotokoll-m1.md) | M1-Abnahmeprotokoll |
| [abnahme/plattform-uebersicht.md](./abnahme/plattform-uebersicht.md) | Technische Plattform-Übersicht (Kundenpräsentation) |

## Audit-Dokumente (historisch)

| Dokument | Datum |
|----------|-------|
| [audit/cloud-infrastruktur-audit-2026-03-04.md](./audit/cloud-infrastruktur-audit-2026-03-04.md) | 2026-03-04 |
| [audit/networkpolicy-analyse.md](./audit/networkpolicy-analyse.md) | 2026-03 |
| [audit/2026-03-24-doc-reality-gap.md](./audit/2026-03-24-doc-reality-gap.md) | 2026-03-24 |
| [audit/2026-03-24-helm-coherence-report.md](./audit/2026-03-24-helm-coherence-report.md) | 2026-03-24 |
| [audit/2026-03-24-image-audit.md](./audit/2026-03-24-image-audit.md) | 2026-03-24 |
| [audit/2026-03-24-llm-access-control-audit.md](./audit/2026-03-24-llm-access-control-audit.md) | 2026-03-24 |

## Extension-Module (Stand 2026-04-21)

Alle 9 ext-Module (Phase 4a-4i) sind deployed auf DEV + PROD. Chart-Version 0.4.44.

| Phase | Modul | Status | Feature Flag |
|-------|-------|--------|-------------|
| 4a | `ext-framework` | Deployed | `EXT_ENABLED` |
| 4b | `ext-branding` | Deployed (2026-03-08) | `EXT_BRANDING_ENABLED` + `NEXT_PUBLIC_EXT_BRANDING_ENABLED` |
| 4c | `ext-token` | Deployed (2026-03-09) | `EXT_TOKEN_LIMITS_ENABLED` |
| 4d | `ext-prompts` | Deployed (2026-03-09) | `EXT_CUSTOM_PROMPTS_ENABLED` |
| 4e | `ext-analytics` | Deployed (2026-03-26) | `EXT_ANALYTICS_ENABLED` |
| 4f | `ext-rbac` | Deployed (2026-03-23) | `EXT_RBAC_ENABLED` + `NEXT_PUBLIC_EXT_RBAC_ENABLED` |
| 4g | `ext-access` | Deployed (2026-03-25) | `EXT_DOC_ACCESS_ENABLED` |
| 4h | `ext-i18n` | Deployed (2026-03-22) | `NEXT_PUBLIC_EXT_I18N_ENABLED` |
| 4i | `ext-audit` | Deployed (2026-03-25) | `EXT_AUDIT_ENABLED` |

## Environments

| Environment | Status | URL | Cluster |
|-------------|--------|-----|---------|
| **DEV** | LIVE seit 2026-02-27 | `https://dev.chatbot.voeb-service.de` | SKE `vob-chatbot`, NS `onyx-dev` |
| **TEST** | **Abgebaut 2026-04-21** (Template-Artefakte im Repo) | — | — |
| **PROD** | **HTTPS LIVE** seit 2026-03-17 | `https://chatbot.voeb-service.de` | SKE `vob-prod`, NS `onyx-prod` |

## Kontakt

| Rolle | Organisation | Person |
|-------|-------------|--------|
| Technische Leitung / Entwicklung | CCJ Development | Nikolaj Ivanov |
| Entwicklung | CCJ Development | Benito De Michele |
| Projektmanagement (Auftraggeber) | VÖB Service | Pascal Witthoff |
| IT-Infrastruktur (Auftraggeber) | VÖB Service | Leif Rasch |

---

Letzte Aktualisierung: 2026-04-21
