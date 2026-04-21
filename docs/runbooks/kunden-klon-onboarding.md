# Kunden-Klon — End-to-End-Onboarding

**Zielgruppe:** Tech Lead / DevOps, der einen neuen Kunden auf Basis dieses Chatbot-Fork aufsetzt
**Dauer:** 2–4 Arbeitstage (je nach externen Wartezeiten — DNS, Entra ID)
**Stand:** 2026-04-21

Dieses Runbook ist der **Einstiegspunkt** für ein neues Kunden-Projekt. Es definiert die Reihenfolge, die kundenspezifischen Variablen und verweist auf die Detail-Runbooks. Ohne diese Master-Sicht verliert man in den 18 Einzel-Runbooks den Überblick.

---

## 1. Voraussetzungen — was der Kunde stellen muss

Bevor du anfängst, müssen folgende Dinge vom Kunden geklärt sein:

| Asset | Zuständig | Benötigt bis Phase |
|---|---|---|
| **StackIT-Konto + Projekt** | Kunde (StackIT-Vertrag) | Phase 1 (Tag 1) |
| **StackIT Service Account** (mit `project.admin`-Rolle) | Kunde bei StackIT, Credentials an Tech Lead | Phase 1 |
| **Domain + DNS-Zugriff** (z. B. `chatbot.kunde.de`) | Kunde (Domain-Inhaber) | Phase 4 (TLS) |
| **Entra ID Tenant + App Registration** | Kunden-IT | Phase 6 (Auth) |
| **StackIT AI Model Serving Token** | Kunde bei StackIT | Phase 8 (LLM) |
| **Logo (PNG/JPEG, ≤ 2 MB)** | Kunde (Marketing) | Phase 9 (Whitelabel) |
| **Team-Benennung** (Product Owner, IT-Kontakt) | Kunde | Projektstart |
| **Admin-IP** (statische IP des Tech Leads für PG-ACL) | Tech Lead | Phase 2 |
| **Microsoft Teams Webhook URL** (für Alerts) | Kunde oder CCJ | Phase 7 (Monitoring) |

---

## 2. Kundenspezifische Variablen

Alle Runbooks nutzen Platzhalter, die du durchgängig ersetzt. Lege dir eine `kunde.tfvars` und eine `.env.kunde` an — alle Werte stehen dort einmal zentral.

### 2.1 Pflicht-Variablen (zu ersetzende Strings)

| Platzhalter | Beispiel (VÖB) | Verwendung |
|---|---|---|
| `<CUSTOMER_SHORT>` | `vob` | Prefix für alle StackIT-Ressourcen: `vob-dev`, `vob-prod`, Teams-Kanal-Name |
| `<CUSTOMER_NAME>` | `voeb-service` | Container-Registry-Projekt, DNS-Zone-Name |
| `<PROJECT_ID>` | `b3d2a04e-46de-48bc-abc6-c4dfab38c2cd` | StackIT Project UUID (DEV). Wenn DEV und PROD in **einem** StackIT-Projekt leben, gilt dieser Wert auch für PROD. |
| `<PROD_PROJECT_ID>` | (nur wenn separates PROD-Projekt) | StackIT Project UUID für PROD — nur nötig, wenn DEV und PROD in getrennten StackIT-Projekten liegen (empfohlen für Compliance-strenge Kunden). Beim VÖB-Setup identisch mit `<PROJECT_ID>`. |
| `<PRIMARY_DOMAIN>` | `chatbot.voeb-service.de` | PROD-URL |
| `<DEV_DOMAIN>` | `dev.chatbot.voeb-service.de` | DEV-URL |
| `<CLUSTER_DEV>` | `vob-chatbot` | SKE-Cluster DEV (+TEST falls gewünscht) |
| `<CLUSTER_PROD>` | `vob-prod` | SKE-Cluster PROD |
| `<NAMESPACE_DEV>` | `onyx-dev` | K8s-Namespace DEV |
| `<NAMESPACE_PROD>` | `onyx-prod` | K8s-Namespace PROD |
| `<PG_INSTANCE_DEV>` | `vob-dev` | PG Flex DEV |
| `<PG_INSTANCE_PROD>` | `vob-prod` | PG Flex PROD |
| `<BUCKET_DEV>` | `vob-dev` | Object Storage DEV |
| `<BUCKET_PROD>` | `vob-prod` | Object Storage PROD |
| `<REGISTRY_PROJECT>` | `voeb-chatbot` | StackIT Container Registry |
| `<HELM_RELEASE_DEV>` | `onyx-dev` | Helm Release-Name DEV |
| `<HELM_RELEASE_PROD>` | `onyx-prod` | Helm Release-Name PROD |
| `<ADMIN_IP>` | `109.41.x.x/32` | Tech-Lead-IP für PG-ACL |
| `<ACME_EMAIL>` | `nikolaj.ivanov@coffee-studios.de` | Let's Encrypt ACME-Account |
| `<ENTRA_TENANT_ID>` | UUID von Kunden-IT | OIDC Provider URL |
| `<ENTRA_CLIENT_ID>` | UUID von Kunden-IT | OIDC App Registration |
| `<TEAMS_WEBHOOK_URL>` | Microsoft Teams Connector URL | Monitoring-Alerts |
| `<TECH_LEAD_EMAIL>` | `niko@coffee-studios.de` | Erster Admin im Chatbot, CronJob-Ownership, Eskalationskontakt |
| `<ADMIN_EMAILS>` | `"niko@…","po@…"` | SQL-IN-Liste für initiales Admin-Promoting (post-go-live.md) |

### 2.2 Pflicht-Secrets (Credentials, nicht als Strings ersetzbar)

Diese werden NICHT durchgängig als Platzhalter ersetzt — sie landen direkt in GitHub Environment Secrets / K8s Secrets. Im Master-Playbook gelistet für Vollständigkeit.

| Secret-Name | Quelle | Wo abgelegt |
|---|---|---|
| `<CLOUDFLARE_API_TOKEN>` | Kunden-DNS-Owner (bei VÖB: GlobVill/Leif) | K8s Secret `cloudflare-api-token` in `cert-manager` NS. Permissions: Zone:Zone:Read + Zone:DNS:Edit |
| `<ENTRA_CLIENT_SECRET>` | Kunden-IT (**Value**, nicht ID — häufiger Fehler!) | GitHub Environment Secret `ENTRA_CLIENT_SECRET` |
| `<STACKIT_REGISTRY_USER>` / `<STACKIT_REGISTRY_PASSWORD>` | StackIT Portal → Container Registry → Robot Account | GitHub Secret (global) + K8s Secret `stackit-registry` in beiden NS — IMMER synchron halten! |
| `<STACKIT_KUBECONFIG>` | `terraform output -raw kubeconfig`, Base64-encoded | GitHub Secret (global für DEV, Environment Secret `prod` für PROD). Ablauf 90 Tage. |
| `<POSTGRES_PASSWORD>`, `<DB_READONLY_PASSWORD>`, `<REDIS_PASSWORD>`, `<S3_ACCESS_KEY_ID>`, `<S3_SECRET_ACCESS_KEY>`, `<OPENSEARCH_PASSWORD>` | `openssl rand` bzw. StackIT CLI | GitHub Environment Secrets (pro Environment). Generierungs-Hinweis: keine URI-Delimiter (`/`, `@`, `:`, `#`) im Passwort — siehe stackit-postgresql.md Lesson 2 |

### 2.3 Generische Kontext-Aliase (in Runbooks verwendet)

Diese Platzhalter sind bewusst **kontextabhängig**: je nach Environment DEV oder PROD eingesetzt. Die Runbooks nennen am Anfang jedes Befehls, welcher Wert gemeint ist.

| Alias | Bedeutet | Beispiel |
|---|---|---|
| `<NAMESPACE>` | `<NAMESPACE_DEV>` oder `<NAMESPACE_PROD>` je nach aktuellem Environment | `kubectl get pods -n <NAMESPACE>` |
| `<CLUSTER>` | `<CLUSTER_DEV>` oder `<CLUSTER_PROD>` | `kubectl --context <CLUSTER> ...` |
| `<HELM_RELEASE>` | `<HELM_RELEASE_DEV>` oder `<HELM_RELEASE_PROD>` | `helm upgrade <HELM_RELEASE> ...` |
| `<PG_INSTANCE>` | `<PG_INSTANCE_DEV>` oder `<PG_INSTANCE_PROD>` | `stackit postgresflex instance describe <PG_INSTANCE>` |
| `<REVISION>` | Helm-Release-Revision (aus `helm history`) | `helm rollback onyx-prod <REVISION>` |
| `<IMAGE_TAG>` | Container-Image-Tag (Git-SHA oder Semver) | `--set image.tag=<IMAGE_TAG>` |
| `<NEUES_CLOUDFLARE_TOKEN>` | Neues Token bei Rotation (siehe `secret-rotation.md`) | — |
| `<PG_INSTANCE_ID>` | StackIT PG Flex UUID (aus `terraform output` oder `stackit postgresflex instance list`) — unterscheidet sich von `<PG_INSTANCE_DEV>`/`<PG_INSTANCE_PROD>` (das sind Namen) | `stackit postgresflex user list --instance-id <PG_INSTANCE_ID>` |
| `<PG_CLONE_INSTANCE_ID>` | UUID der geklonten Restore-Instanz | `stackit-postgresql.md` "Restore per Clone" |
| `<DNS_PROVIDER>` | Kunden-DNS-Owner (z.B. `GlobVill`, `Cloudflare`, `StackIT DNS`) | Siehe §2.4 |

### 2.4 Optionale Konfig-Entscheidungen

Keine Platzhalter, sondern frühe Architektur-Entscheidungen — dokumentier sie für den Kunden, sobald sie getroffen sind.

| Thema | Empfehlung | Hinweis |
|---|---|---|
| **DNS-Anbieter** (`<DNS_PROVIDER>`) | Cloudflare (wenn API-Zugriff möglich) | Wenn Kunden-DNS kein API-Access hat (VÖB → GlobVill): CNAME-Delegation auf separaten Cloudflare-Account konfigurieren. Siehe `dns-tls-setup.md` Abschnitt "DNS-Architektur". |
| **PROD-HA-Level** | 3-Node PG Flex (HA) + 2 API-Replicas, 2 Web-Replicas | Bei geringerem Ausfallanspruch: PG Flex Single (spart ~60% PG-Kosten). ADR-004 im Repo dokumentiert die Entscheidung. |
| **Log-Retention** | 30 Tage (Loki), 90 Tage (Prometheus) | Siehe `monitoring-setup.md` — fix in `values-monitoring-prod.yaml` |
| **Separate PROD-Cluster** | Ja (empfohlen) | ADR-004 dokumentiert die Trennung. Bei "klein" kann DEV+PROD auf einem Cluster laufen (spart ~280 EUR/Mo). |

---

## 3. Phasen-Übersicht

Die Phasen sind sequenziell. Jede hat ein eigenes Runbook.

| Phase | Ziel | Runbook | Dauer |
|---|---|---|---|
| 0.1 | Kosten-Kalkulation für Angebot | [kosten-kalkulation-kunde.md](./kosten-kalkulation-kunde.md) | 30 min |
| 0.2 | Git-Repo-Setup (Fork, Environments, Secrets, Branch Protection) | [github-setup.md](./github-setup.md) | 1 h |
| 1.1 | StackIT CLI + Container Registry | [stackit-projekt-setup.md](./stackit-projekt-setup.md) | 1 h |
| 1.2 | StackIT Service Accounts (Terraform-SA, Monitoring-SA) | [stackit-service-accounts.md](./stackit-service-accounts.md) | 30 min |
| 2 | Terraform: SKE-Cluster + PG Flex + Object Storage | [terraform-setup.md](./terraform-setup.md) | 2–3 h |
| 3 | PostgreSQL: DB anlegen, Readonly-User, ACL | [stackit-postgresql.md](./stackit-postgresql.md) | 30 min |
| 4 | DNS + TLS (cert-manager, Let's Encrypt) | [dns-tls-setup.md](./dns-tls-setup.md) | 1 h + DNS-Propagation |
| 5 | Helm-Chart + Extensions initial deployen | [helm-deploy.md](./helm-deploy.md) | 1–2 h |
| 6 | Entra ID OIDC: App Registration, Redirect URIs | [entra-id-setup.md](./entra-id-setup.md) | 1 h + Kunden-IT-Wartezeit |
| 7 | Monitoring-Stack: Prometheus + Grafana + Alerts | [monitoring-setup.md](./monitoring-setup.md) | 2 h |
| 8 | LLM + Embedding-Modelle konfigurieren | [llm-konfiguration.md](./llm-konfiguration.md) | 1 h |
| 9.1 | Whitelabel: Logo, App-Name, Consent | [whitelabel-setup.md](./whitelabel-setup.md) | 1 h |
| 9.2 | Extensions aktivieren (alle 9 Module) | [extensions-aktivierung.md](./extensions-aktivierung.md) | 1–2 h |
| 10 | CI/CD Pipeline: GitHub Actions + Environments | [ci-cd-pipeline.md](./ci-cd-pipeline.md) | 1 h |
| 11 | PROD-Rollout | [prod-deploy.md](./prod-deploy.md) | 1 h |
| 12 | Post-Go-Live: Admin + erste Daten + User-Rollout | [post-go-live.md](./post-go-live.md) | 2 h |

**Gesamt:** ca. 15–20 h aktive Arbeit + externe Wartezeiten (DNS-Propagation, Entra-ID-IT).

**Querverweise:**
- [credentials-inventar.md](./credentials-inventar.md) — zentrale Liste aller Credentials (Single Source of Truth für Secrets)

---

## 4. Phase 0 — Projekt-Initialisierung

### 4.1 Repository

```bash
# Neuen Fork von der CCJ-Development/voeb-chatbot Template erstellen
# Entweder via GitHub UI oder:
gh repo create CCJ-Development/<CUSTOMER_NAME>-chatbot \
  --template CCJ-Development/voeb-chatbot \
  --private

git clone git@github.com:CCJ-Development/<CUSTOMER_NAME>-chatbot.git
cd <CUSTOMER_NAME>-chatbot
```

### 4.2 Kundenspezifische Config-Dateien anlegen

- `deployment/terraform/environments/dev/dev.auto.tfvars` (gitignored): `project_id = "<PROJECT_ID>"`
- `deployment/terraform/environments/prod/prod.auto.tfvars` (gitignored): `project_id = "<PROJECT_ID>"`
- `deployment/helm/values/values-dev-secrets.yaml` (gitignored, Secrets)
- `deployment/helm/values/values-prod-secrets.yaml` (gitignored, Secrets)

### 4.3 Variablen-Ersetzung durchführen

Alle Ressourcen-Namen (`vob-*`, `voeb-*`, `onyx-*`) sind in Config-Files und Workflows fest verdrahtet. Ersetze systematisch (zum Beispiel per `sed`):

```bash
# Beispiel für Customer Short "newcust"
grep -rl "vob-" deployment/ .github/ | xargs sed -i '' 's/vob-/newcust-/g'
grep -rl "voeb-chatbot" deployment/ .github/ | xargs sed -i '' 's/voeb-chatbot/<CUSTOMER_NAME>-chatbot/g'
grep -rl "voeb-service" deployment/ docs/ | xargs sed -i '' 's/voeb-service/<CUSTOMER_NAME>/g'
```

**Prüfen** durch `git diff` und committen auf Feature-Branch.

---

## 5. End-to-End-Checkliste

Diese Checkliste prüft nach dem Onboarding, ob alles läuft.

### 5.1 Infrastruktur

- [ ] `terraform apply` läuft fehlerfrei für DEV + PROD
- [ ] SKE-Cluster DEV reachable: `kubectl --context <CLUSTER_DEV> get nodes` zeigt 2 Ready-Nodes
- [ ] SKE-Cluster PROD reachable: analog
- [ ] PG Flex DEV verbindbar: `psql` aus einem Pod
- [ ] PG Flex PROD verbindbar: analog
- [ ] Object Storage Buckets existieren: `stackit object-storage bucket list`

### 5.2 Netzwerk & TLS

- [ ] A-Record `<DEV_DOMAIN>` zeigt auf Cluster-LoadBalancer-IP
- [ ] A-Record `<PRIMARY_DOMAIN>` zeigt auf PROD-LoadBalancer-IP
- [ ] cert-manager ClusterIssuer READY
- [ ] HTTPS `https://<DEV_DOMAIN>` liefert gültiges ECDSA-P-384-Zertifikat (TLS 1.3)
- [ ] HTTPS `https://<PRIMARY_DOMAIN>` analog
- [ ] HSTS-Header: `curl -I https://<PRIMARY_DOMAIN>` enthält `Strict-Transport-Security: max-age=31536000`

### 5.3 Applikation

- [ ] Helm Release `<HELM_RELEASE_DEV>` installiert, alle Pods 1/1 Running
- [ ] Helm Release `<HELM_RELEASE_PROD>` installiert, alle Pods 1/1 Running
- [ ] `/api/health` auf DEV liefert 200 + `{"success": true}`
- [ ] `/api/ext/health/deep` auf DEV liefert 200 (DB, Redis, OpenSearch OK)
- [ ] analog für PROD

### 5.4 Auth

- [ ] Entra ID Redirect-URIs bei Kunden-IT eingetragen
- [ ] OIDC-Login auf DEV funktioniert (Browser → Entra-Login → zurück → Chat-UI)
- [ ] JIT-Provisioning: erster Login wird Administrator
- [ ] Session-Cookie: HttpOnly + Secure + SameSite=Lax

### 5.5 LLM

- [ ] LLM-Provider in Admin-UI konfiguriert (StackIT AI Model Serving)
- [ ] Mindestens 1 Chat-Modell testbar (Test-Nachricht liefert Antwort)
- [ ] Embedding-Modell konfiguriert, Re-Index läuft/ist fertig

### 5.6 Whitelabel

- [ ] Logo im Frontend sichtbar
- [ ] App-Name im Browser-Tab korrekt
- [ ] Login-Text angepasst
- [ ] `EXT_BRANDING_ENABLED=true` gesetzt

### 5.7 Monitoring

- [ ] kube-prometheus-stack in `monitoring`-Namespace läuft
- [ ] Prometheus Scrape-Targets UP
- [ ] Grafana per `kubectl port-forward` erreichbar
- [ ] AlertManager sendet Test-Alert an Teams-Webhook

### 5.8 CI/CD

- [ ] GitHub Actions Workflow `stackit-deploy.yml` läuft auf Push grün durch (DEV)
- [ ] GitHub Environment `prod` hat Required Reviewer + alle Secrets
- [ ] Smoke-Test nach Deploy grün

### 5.9 Backup

- [ ] PG Flex Backup-Schedule in Terraform gesetzt
- [ ] Mindestens 1 Backup erfolgreich (StackIT-Portal)
- [ ] Restore-Test auf DEV durchgeführt (geplant nach Onboarding)

### 5.10 Abnahme

- [ ] Kunden-Onboarding-Meeting abgehalten
- [ ] Admin-Zugang an Kunden-IT übergeben
- [ ] Dokumentation (README + Betriebskonzept) an Kunden übergeben
- [ ] Rollback-Verfahren besprochen

---

## 6. Nach dem Go-Live

| Aufgabe | Frequenz | Runbook |
|---|---|---|
| Upstream-Sync (Onyx FOSS) | alle 2–4 Wochen | [upstream-sync.md](./upstream-sync.md) |
| Restore-Test | quartalsweise | [stackit-postgresql.md](./stackit-postgresql.md) |
| Secret-Rotation | halbjährlich | [secret-rotation.md](./secret-rotation.md) |
| Kubeconfig-Erneuerung | 90 Tage vor Ablauf | Terraform `stackit_ske_kubeconfig` |
| Alert-Monitoring | kontinuierlich | [alert-antwort.md](./alert-antwort.md) |

---

## 7. Typische Stolpersteine (Lessons Learned aus VÖB)

1. **DNS-Delegation durch Dritten** — Wenn der Kunden-DNS von einem externen Provider gehalten wird (z. B. GlobVill → CNAME auf Cloudflare), muss die ACME-DNS-01-Challenge sorgfältig aufgesetzt werden. Siehe `dns-tls-setup.md`.

2. **Entra ID PKCE** — Mit Onyx-Setup deaktivieren (Cookie-Loss durch NGINX-Proxy). Siehe `entra-id-setup.md`.

3. **OpenSearch lowercase** — Index-Namen müssen lowercase sein (Core-Datei-Patch #13). Kommt beim ersten Deploy durch, wenn Embedding-Modell Großbuchstaben hat.

4. **Alembic-Chain bei Upstream-Sync** — Siehe `upstream-sync.md`.

5. **Machine-Typ `g1a` vs `c1a`** — Unsere Terraform-Vars nutzen `g1a.*`. Aktuelle StackIT-Preisliste kennt nur `c1a.*`. Bei neuen Projekten prüfen, ob `c1a.*` zu verwenden ist.

6. **Registry-Credentials-Drift** — StackIT Container Registry Robot-Account-Token vs. GitHub Secret können driften. Bei 401 in CI zuerst `kubectl get secret stackit-registry` mit `gh secret set STACKIT_REGISTRY_PASSWORD` abgleichen.

---

## 8. Weitere Runbooks (Betrieb, nicht Setup)

Diese brauchst du nicht fürs Onboarding, aber für den späteren Betrieb:

- [rollback-verfahren.md](./rollback-verfahren.md) — Helm/DB-Rollback
- [alert-antwort.md](./alert-antwort.md) — Was tun bei Alert?
- [loki-troubleshooting.md](./loki-troubleshooting.md) — Log-Probleme
- [opensearch-troubleshooting.md](./opensearch-troubleshooting.md) — Index-Probleme
- [llm-provider-management.md](./llm-provider-management.md) — LLM-Provider wechseln
- [ext-access-aktivierung.md](./ext-access-aktivierung.md) — Gruppenbasierte Dokument-ACL aktivieren
- [ext-analytics-verwaltung.md](./ext-analytics-verwaltung.md) — Analytics-Dashboard pflegen
- [ip-schutz-helm.md](./ip-schutz-helm.md) — LB-IP bei Helm-Neuinstallation schützen

---

## 9. Referenzen

- **Technische Spezifikationen:** `docs/referenz/technische-parameter.md` (Single Source of Truth)
- **Architekturentscheidungen:** `docs/adr/`
- **Modulspezifikationen:** `docs/technisches-feinkonzept/`
- **Template-Repository:** `git@github.com:CCJ-Development/voeb-chatbot.git`
