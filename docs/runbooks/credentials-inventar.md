# Credentials-Inventar

**Zielgruppe:** Tech Lead, Security-Review, Audit-Vorbereitung
**Stand:** 2026-04-21

Diese Datei listet **alle** Credentials, Secrets und Tokens im System — wo sie liegen, woher sie kommen, wer sie generiert, wie sie rotiert werden. Ohne diese Übersicht verliert man bei 12+ Secrets und 5 Speicherorten den Überblick.

---

## Übersicht nach Speicherort

| Speicherort | Inhalt | Zugriff | Backup |
|---|---|---|---|
| GitHub Repository Secrets | 3 globale Credentials | Tech Lead + CI/CD | GitHub-seitig, nicht wiederherstellbar |
| GitHub Environment Secrets (`dev`) | 9 Credentials | CI/CD `dev`-Runs | wie oben |
| GitHub Environment Secrets (`prod`) | 10 Credentials | CI/CD `prod`-Runs + Required Reviewer | wie oben |
| Kubernetes Secrets (`onyx-<env>`) | ~5 Secrets je NS | Namespace-RBAC | werden bei Helm-Install neu erzeugt aus GitHub Secrets |
| Terraform State (lokal) | PG-Passwörter, Kubeconfig | Dateizugriff (chmod 600) | Manuelle Sicherung |
| StackIT Portal | Service Account Key (JSON) | StackIT-Login | StackIT-seitig, neu generierbar |
| Lokale Shell / 1Password | Admin-Zugänge, MFA-Seeds | Tech Lead persönlich | Tech-Lead-Pflicht |

---

## 1. GitHub Repository Secrets (global)

Einmal pro Repo gesetzt. Werden in **allen** Workflow-Läufen benutzt.

| Secret | Herkunft | Generator | Rotation |
|---|---|---|---|
| `STACKIT_REGISTRY_USER` | Robot Account Name aus StackIT Portal | Portal → Container Registry → Robot Accounts → anlegen | halbjährlich |
| `STACKIT_REGISTRY_PASSWORD` | Robot Account Token | gleiche Stelle, **einmal angezeigt** | halbjährlich |
| `STACKIT_KUBECONFIG` | Base64-Kubeconfig (DEV) | `terraform output -raw kubeconfig \| base64` | 90 Tage (Kubeconfig-Lifetime) |

Setzung: siehe [github-setup.md §4.1](./github-setup.md).

---

## 2. GitHub Environment Secrets (`dev`)

| Secret | Herkunft | Sichtbar in | Rotation |
|---|---|---|---|
| `POSTGRES_PASSWORD` | `terraform output -raw pg_password` | K8s Secret `onyx-postgresql` | jährlich |
| `DB_READONLY_PASSWORD` | `terraform output -raw pg_readonly_password` | K8s Secret `onyx-dbreadonly` | jährlich |
| `REDIS_PASSWORD` | `openssl rand -base64 32` (selbst-generiert) | K8s Secret `onyx-redis` | bei Kompromittierung |
| `S3_ACCESS_KEY_ID` | StackIT CLI `object-storage credentials create` | K8s Secret `onyx-objectstorage` | jährlich |
| `S3_SECRET_ACCESS_KEY` | gleiche Stelle, **einmal angezeigt** | K8s Secret `onyx-objectstorage` | jährlich |
| `ENTRA_CLIENT_ID` | Kunden-IT (App Registration Application ID) | K8s Secret `onyx-oauth` | wenn App neu registriert |
| `ENTRA_CLIENT_SECRET` | Kunden-IT (App Registration Secret **Value**, nicht ID!) | K8s Secret `onyx-oauth` | halbjährlich (MS-Default: 2 Jahre) |
| `ENTRA_TENANT_ID` | Kunden-IT (Directory ID) | env-configmap | nie (statisch) |
| `USER_AUTH_SECRET` | `openssl rand -hex 32` (selbst-generiert) | K8s Secret `onyx-userauth` | bei Kompromittierung |

---

## 3. GitHub Environment Secrets (`prod`)

Gleiche 9 Secrets wie DEV (mit PROD-Werten), plus:

| Zusätzlich | Herkunft | Warum separat |
|---|---|---|
| `OPENSEARCH_PASSWORD` | `openssl rand -base64 24` (selbst-generiert) | OpenSearch-Chart-Default `StrongPassword123!` ist bekannt und unsicher — PROD-Admin-PW muss custom sein |

**Wichtig:** Niemals DEV-Werte in PROD-Environment ablegen. Separate Kubeconfig, separate PG-Instanz, separate Credentials.

---

## 4. Kubernetes Secrets (pro Namespace)

Werden durch Helm aus den GitHub Environment Secrets erzeugt (via `--set auth.*.values.*=${{ secrets.* }}`).

| K8s Secret | Namespace | Inhalt | Wird erstellt von |
|---|---|---|---|
| `stackit-registry` | `<NAMESPACE_<env>>` | Docker-Config-JSON für Image Pull | Manuell (einmalig): `kubectl create secret docker-registry stackit-registry --docker-server=registry.onstackit.cloud ...` |
| `onyx-postgresql` | `<NAMESPACE_<env>>` | PG `onyx_app` Credentials | Helm (bei `helm upgrade`) |
| `onyx-dbreadonly` | `<NAMESPACE_<env>>` | PG `db_readonly_user` Credentials | Helm |
| `onyx-redis` | `<NAMESPACE_<env>>` | Redis Password | Helm |
| `onyx-objectstorage` | `<NAMESPACE_<env>>` | S3 Access Key + Secret | Helm |
| `onyx-oauth` | `<NAMESPACE_<env>>` | Entra ID Client ID + Secret | Helm |
| `onyx-userauth` | `<NAMESPACE_<env>>` | JWT Signing Secret | Helm |
| `pg-exporter-<env>-credentials` | `monitoring` | PG-DSN für Exporter | Manuell (einmalig): `kubectl create secret generic ...` |
| `alertmanager-teams-webhook` | `monitoring` | Teams Webhook URL | Manuell (einmalig) |
| `grafana-pg-datasource` | `monitoring` | PG-Readonly-User für Grafana-Panels | Manuell (PROD) |

**Anzeigen:**
```bash
kubectl --context <CLUSTER> -n <NAMESPACE> get secrets
kubectl --context <CLUSTER> -n <NAMESPACE> get secret onyx-postgresql -o jsonpath='{.data.password}' | base64 -d
```

---

## 5. Terraform State

Der lokale `terraform.tfstate` enthält **im Klartext**:
- PG `onyx_app` Password
- PG `db_readonly_user` Password
- Kubeconfig (mit Client-Zertifikat)
- Objekt-Storage-Credentials (falls in Terraform erstellt; bei uns werden diese separat per StackIT CLI erzeugt)

**Schutzmaßnahmen:**
```bash
chmod 600 deployment/terraform/environments/*/terraform.tfstate*
```

**Nie committen** — ist in `.gitignore`.

**Backup-Empfehlung:**
```bash
cp deployment/terraform/environments/dev/terraform.tfstate ~/secure-backups/tfstate-dev-$(date +%Y%m%d).bak
```

Für Team-Setup: Remote-Backend mit StackIT Object Storage (siehe [terraform-setup.md §10](./terraform-setup.md)).

---

## 6. StackIT Portal

| Asset | Zweck | Speicherort | Rotation |
|---|---|---|---|
| **Service Account Key (JSON)** | Terraform-Authentifizierung, PG-Backup-Monitoring | Lokal + 1Password | jährlich |
| **User-Login + MFA** | Portal-Zugriff | Tech Lead persönlich | nach IT-Policy |
| **AI Model Serving API Token** | LLM-Zugriff aus Onyx | K8s Secret (Onyx Admin-UI hinterlegt) | jährlich |
| **Container Registry Robot Account** | CI/CD Image Push | siehe oben (§1) | halbjährlich |

Service Account anlegen: [stackit-service-accounts.md](./stackit-service-accounts.md).

---

## 7. DNS-Provider

Abhängig vom Kunden-Setup. Bei VÖB:

| Asset | Zweck | Wer verwaltet |
|---|---|---|
| GlobVill-DNS-Einträge | autoritative Nameserver für `voeb-service.de` | VÖB / Leif Rasch bei GlobVill |
| Cloudflare API Token | ACME-Challenge DNS-01 für cert-manager | CCJ Tech Lead, im K8s-Secret `cloudflare-api-token` (cert-manager NS) |

Bei anderen Kunden variiert das. Siehe [dns-tls-setup.md](./dns-tls-setup.md).

---

## 8. Externe Dienste

| Dienst | Credential-Typ | Speicherort | Rotation |
|---|---|---|---|
| Microsoft Entra ID | App Registration Client ID + Secret | GitHub Env Secrets + K8s Secret `onyx-oauth` | Secret: halbjährlich |
| Let's Encrypt | ACME Account-Key (wird von cert-manager verwaltet) | K8s Secret `letsencrypt-*-key` (cert-manager NS) | Auto-Renewal |
| Cloudflare | API Token (DNS-Edit) | K8s Secret `cloudflare-api-token` (cert-manager NS) | jährlich |
| Microsoft Teams | Incoming Webhook URL | K8s Secret `alertmanager-teams-webhook` | bei Kanal-Wechsel |
| GitHub | Personal Access Token (nur Tech Lead, für `gh` CLI) | Tech Lead persönlich (`~/.config/gh/`) | halbjährlich |

---

## 9. Lokale Tech-Lead-Credentials

Nur auf der Maschine des Tech Leads:

| Credential | Zweck | Speicherort |
|---|---|---|
| StackIT CLI Session Token | `stackit auth login` | `~/.stackit/` |
| SSH Key für Cluster-Zugriff (optional) | Emergency-Debug | `~/.ssh/stackit_<customer>_ed25519` |
| `~/.kube/config` | Cluster-Zugriffe | lokal |
| 1Password / KeePass / Bitwarden | zentrale Passwort-Ablage | persönlich |

---

## 10. Rotations-Kalender (Empfehlung)

| Frequenz | Was |
|---|---|
| **Monatlich** | Backup-Check + Restore-Test-Protokoll |
| **Quartalsweise** | Restore-Test durchführen (DEV oder PROD Clone), SA-Token prüfen |
| **Halbjährlich** | Registry-Robot-Token rotieren, Entra Client Secret rotieren |
| **Jährlich** | PG-Passwörter, S3-Keys, OpenSearch Admin-PW, StackIT SA Key, Cloudflare API Token |
| **90 Tage vor Ablauf** | Kubeconfig-Erneuerung (siehe Terraform `stackit_ske_kubeconfig`) |
| **Bei Kompromittierung** | Alles Betroffene sofort |

Siehe [secret-rotation.md](./secret-rotation.md) für detaillierte Rotations-Workflows.

---

## 11. „Was habe ich in jedem Speicherort?" — Schnellreferenz

### GitHub Repository Secrets
```bash
gh secret list
```
Erwartung: `STACKIT_REGISTRY_USER`, `STACKIT_REGISTRY_PASSWORD`, `STACKIT_KUBECONFIG`, ggf. `TEAMS_WEBHOOK_URL`.

### GitHub Environment Secrets
```bash
gh secret list --env dev
gh secret list --env prod
```

### K8s Secrets (pro NS)
```bash
kubectl --context <CLUSTER> -n <NAMESPACE> get secrets
```

### Terraform State (sensibler Inhalt, nicht einfach anzeigen)
```bash
cd deployment/terraform/environments/<env>
terraform show -json | jq '.values.root_module.resources[] | select(.values.password != null) | {name, type}'
```

---

## 12. Compliance-Notiz

Für **Audit-Fähigkeit** (DSGVO Art. 32 — TOMs):
- Secret-Rotations-Log (wann wurde was rotiert?) — **aktuell nicht automatisiert**. Empfehlung: Kalender-Einträge + git-Commit beim Rotieren.
- Zugriffsprotokollierung — GitHub Audit-Log deckt CI/CD ab. Shell-Zugriffe auf `terraform.tfstate` sind OS-seitig (nicht automatisch auditierbar).
- Verschlüsselung at-rest — K8s-Secrets sind bei StackIT per default AES-256 verschlüsselt (etcd). Lokale `tfstate` ist **nicht** verschlüsselt.

Bei Audit-Anforderungen: [secret-rotation.md](./secret-rotation.md) als Prozess-Dokumentation + `docs/sicherheitskonzept.md` für die TOMs-Beschreibung.

---

## 13. Nächster Schritt

→ [stackit-service-accounts.md](./stackit-service-accounts.md) — Service Account Keys anlegen und verwalten
