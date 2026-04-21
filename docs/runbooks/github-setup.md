# GitHub-Setup (Environments, Secrets, Branch Protection)

**Zielgruppe:** Tech Lead beim Kunden-Klon
**Dauer:** 1 h
**Phase:** 0 im [Master-Playbook](./kunden-klon-onboarding.md) (einmalig nach Repo-Fork)

Dieses Runbook beschreibt alle GitHub-Konfigurationen, die vor dem ersten Deploy stehen müssen: Repository-Einstellungen, Environments, Secrets und Branch Protection.

---

## Voraussetzungen

- Repo per Template-Fork erstellt: `gh repo create CCJ-Development/<CUSTOMER_NAME>-chatbot --template CCJ-Development/voeb-chatbot --private`
- GitHub-Organization-Zugriff (zum Anlegen von Environments + Secrets)
- `gh` CLI installiert und eingeloggt (`gh auth login`)
- Alle Kunden-Variablen aus dem [Master-Playbook §2](./kunden-klon-onboarding.md) bekannt

---

## 1. Repository-Grundeinstellungen

### 1.1 Settings → General

- **Visibility:** Private (Pflicht — enthält Kunden-Daten in Secrets/Configs)
- **Issues:** An (für Bug-Tracking)
- **Projects:** Optional
- **Wiki:** Aus (Dokumentation liegt in `docs/`)
- **Discussions:** Aus
- **Merge Button:** „Allow merge commits" aus, „Allow squash merging" AN, „Allow rebase merging" AN
- **Automatically delete head branches:** AN (nach Merge)

Via CLI (teilweise):
```bash
gh repo edit --delete-branch-on-merge --enable-issues --enable-wiki=false
```

### 1.2 Settings → Actions → General

- **Actions permissions:** „Allow all actions and reusable workflows" (oder eingeschränkter)
- **Workflow permissions:** „Read repository contents and packages permissions" (Pflicht — wir nutzen `contents: read`)
- **Allow GitHub Actions to create and approve pull requests:** Aus

---

## 2. Branch Protection für `main`

### 2.1 Via GitHub UI

Settings → Branches → Add rule → Branch name pattern: `main`

Aktivieren:
- [x] **Require a pull request before merging** — Solo-Dev: bei Bedarf deaktiviert, bei Team-Setup aktivieren
  - [x] Require approvals: 1 (bei Team)
  - [x] Dismiss stale pull request approvals when new commits are pushed
- [x] **Require status checks to pass before merging**
  - Suche und wähle die 3 Checks:
    - `helm-validate`
    - `lint-backend`
    - `build-backend`
    - `build-frontend`
  - [x] Require branches to be up to date before merging
- [x] **Require conversation resolution before merging**
- [x] **Do not allow bypassing the above settings**

### 2.2 Via CLI (optional, strict)

```bash
gh api -X PUT repos/CCJ-Development/<CUSTOMER_NAME>-chatbot/branches/main/protection \
  --input - <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["helm-validate", "build-backend", "build-frontend"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF
```

Für **Solo-Dev-Setup** (kein PR-Requirement): `required_pull_request_reviews = null` setzen. Für Team-Setup: `{"required_approving_review_count": 1}`.

---

## 3. Environments anlegen

### 3.1 Environment `dev`

Settings → Environments → New environment → Name: `dev`

Einstellungen:
- **Deployment branches and tags:** „Selected branches and tags" → `main`
- **Required reviewers:** NEIN (DEV wird automatisch bei Push deployed)
- **Wait timer:** 0 Min
- **Environment secrets:** siehe unten

### 3.2 Environment `prod`

Settings → Environments → New environment → Name: `prod`

Einstellungen:
- **Deployment branches and tags:** „Selected branches and tags" → `main`
- **Required reviewers:** **JA** — Tech Lead (dich selbst oder ein Team-Mitglied) eintragen. Ohne diesen Gate startet kein PROD-Deploy ohne Freigabe.
- **Wait timer:** optional (0–60 Min)
- **Environment secrets:** siehe unten

> ⚠️ **Kritisch:** Ohne Required Reviewer auf PROD kann jeder `workflow_dispatch`-Trigger PROD deployen. Das ist ein Produktionsrisiko.

### 3.3 Environment `test` (optional, Template)

Nur anlegen, wenn tatsächlich eine TEST-Umgebung gewünscht ist. Für VÖB wurde TEST am 2026-04-21 abgebaut — das Template im Repo bleibt, aber das GitHub-Environment kann (sollte?) gelöscht werden.

---

## 4. Secrets-Inventar (Pflicht für CI/CD)

### 4.1 Repository-Scope (global für alle Environments)

Diese Secrets werden einmal auf Repo-Ebene gesetzt:

| Secret-Name | Wert | Woher |
|---|---|---|
| `STACKIT_REGISTRY_USER` | Robot Account Name | StackIT Portal → Container Registry → Robot Accounts |
| `STACKIT_REGISTRY_PASSWORD` | Robot Account Token | gleiche Quelle, **einmal anzeigen** → sofort speichern |
| `STACKIT_KUBECONFIG` | Base64-encoded Kubeconfig DEV | `terraform output -raw kubeconfig \| base64` |

**Setzen via CLI:**
```bash
gh secret set STACKIT_REGISTRY_USER
# Prompt: Wert eintippen

gh secret set STACKIT_REGISTRY_PASSWORD
# Prompt: Wert eintippen

# Kubeconfig direkt aus Terraform-Output:
cd deployment/terraform/environments/dev
terraform output -raw kubeconfig | base64 | gh secret set STACKIT_KUBECONFIG --repo CCJ-Development/<CUSTOMER_NAME>-chatbot
```

### 4.2 Environment `dev` Secrets

| Secret | Wert | Woher |
|---|---|---|
| `POSTGRES_PASSWORD` | PG `onyx_app` Passwort | `terraform output -raw pg_password` |
| `DB_READONLY_PASSWORD` | PG `db_readonly_user` Passwort | `terraform output -raw pg_readonly_password` |
| `REDIS_PASSWORD` | Selbst-generiert (zufällig) | `openssl rand -base64 32` |
| `S3_ACCESS_KEY_ID` | Object Storage Access Key | StackIT CLI `object-storage credentials create` |
| `S3_SECRET_ACCESS_KEY` | Object Storage Secret Key | gleiche Stelle, **einmal anzeigen** |
| `ENTRA_CLIENT_ID` | Entra App Registration | Kunden-IT liefert |
| `ENTRA_CLIENT_SECRET` | Entra App Registration Value | Kunden-IT liefert (Value, nicht ID!) |
| `ENTRA_TENANT_ID` | Entra Directory ID | Kunden-IT liefert |
| `USER_AUTH_SECRET` | JWT Signing Secret | `openssl rand -hex 32` |

**Setzen via CLI:**
```bash
gh secret set POSTGRES_PASSWORD --env dev
# für jedes Secret einzeln
```

Bulk-Skript (wenn alle Werte als Env-Vars vorliegen):
```bash
for SECRET in POSTGRES_PASSWORD DB_READONLY_PASSWORD REDIS_PASSWORD S3_ACCESS_KEY_ID S3_SECRET_ACCESS_KEY ENTRA_CLIENT_ID ENTRA_CLIENT_SECRET ENTRA_TENANT_ID USER_AUTH_SECRET; do
  echo "${!SECRET}" | gh secret set $SECRET --env dev
done
```

### 4.3 Environment `prod` Secrets

Gleiche Liste wie DEV, plus:

| Zusätzlich | Wert | Woher |
|---|---|---|
| `OPENSEARCH_PASSWORD` | OpenSearch Admin PW | Selbst-generiert (`openssl rand -base64 24`). **Nicht** Chart-Default `StrongPassword123!` verwenden. |

Alle DEV-Secrets müssen mit **PROD-Werten** neu gesetzt werden (eigene PG-Instanz, eigener Bucket, eigener Entra-Tenant ggf.).

### 4.4 Health-Monitor Secret (optional, für externen Health-Check)

Wenn der Workflow `health-monitor.yml` aktiviert werden soll:

| Secret | Wert | Zweck |
|---|---|---|
| `TEAMS_WEBHOOK_URL` | Microsoft Teams Incoming Webhook | Alert wenn `/api/ext/health/deep` fehlschlägt |

Repo-Scope oder Environment-Scope je nach Setup.

---

## 5. Workflow-Kontext prüfen

Nach dem Setup sollte der Workflow-File `stackit-deploy.yml` referenziert alle Secrets. Prüfen:

```bash
grep -o 'secrets\.[A-Z_]*' .github/workflows/stackit-deploy.yml | sort -u
```

Erwartung (12 Secrets):
- `STACKIT_REGISTRY_USER`
- `STACKIT_REGISTRY_PASSWORD`
- `STACKIT_KUBECONFIG`
- `POSTGRES_PASSWORD`
- `DB_READONLY_PASSWORD`
- `REDIS_PASSWORD`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`
- `ENTRA_CLIENT_ID`
- `ENTRA_CLIENT_SECRET`
- `ENTRA_TENANT_ID`
- `USER_AUTH_SECRET`
- `OPENSEARCH_PASSWORD` (nur PROD)

---

## 6. Validierung

### 6.1 Secrets-Status prüfen

```bash
# Global
gh secret list

# Per Environment
gh secret list --env dev
gh secret list --env prod
```

Jedes Secret sollte ein „Updated"-Timestamp haben.

### 6.2 Erste Workflow-Ausführung

```bash
# Nach erstem Push auf main startet stackit-deploy.yml automatisch
git push origin main

# Workflow-Status beobachten:
gh run watch
```

Ein grüner Durchlauf validiert: Alle Secrets vorhanden, Kubeconfig funktioniert, Registry-Login geht.

---

## 7. Typische Fehler

### „Error: Input required and not supplied: password"

Ein Secret fehlt im Environment. Prüfe mit `gh secret list --env <env>`.

### „Error: unauthorized: authentication required" (Registry)

`STACKIT_REGISTRY_USER` oder `STACKIT_REGISTRY_PASSWORD` stimmt nicht oder Robot Account wurde rotiert. Im StackIT Portal neu generieren und Secret updaten:
```bash
gh secret set STACKIT_REGISTRY_PASSWORD
```

### PROD-Deploy startet ohne Review

Required Reviewer nicht gesetzt. Settings → Environments → prod → „Required reviewers" aktivieren.

### Status-Check fehlt bei Branch Protection

Die Checks existieren erst nach dem ersten CI-Lauf. Vorgehen:
1. Push auf `main` ohne Branch Protection
2. CI läuft einmal durch (erzeugt die Check-Namen)
3. Branch Protection aktivieren und die Checks auswählen

---

## 8. Rotation-Empfehlungen

| Secret | Empfohlene Rotation |
|---|---|
| `STACKIT_REGISTRY_PASSWORD` | halbjährlich |
| `STACKIT_KUBECONFIG` | 90 Tage vor Ablauf (Kubeconfig hat 90-Tage-Lifetime) |
| `POSTGRES_PASSWORD` | jährlich |
| `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` | jährlich |
| `ENTRA_CLIENT_SECRET` | alle 6–12 Monate (Microsoft-Default-Expiry: 2 Jahre) |
| `USER_AUTH_SECRET` | bei Verdacht auf Kompromittierung |
| `OPENSEARCH_PASSWORD` | jährlich |

Details siehe [secret-rotation.md](./secret-rotation.md).

---

## 9. Checkliste

- [ ] Repo private, Issues an, Wiki aus
- [ ] Actions Permissions: `contents: read`
- [ ] Branch Protection auf `main` mit 3 Status Checks
- [ ] Environment `dev` angelegt (ohne Required Reviewer)
- [ ] Environment `prod` angelegt **mit Required Reviewer**
- [ ] 3 globale Secrets gesetzt (Registry + Kubeconfig)
- [ ] 9 Environment-Secrets für `dev` gesetzt
- [ ] 10 Environment-Secrets für `prod` gesetzt (inkl. `OPENSEARCH_PASSWORD`)
- [ ] Erster Workflow-Lauf grün
- [ ] `gh secret list` zeigt alle Secrets
- [ ] Rotations-Kalender im Team-Kalender eingetragen

---

## 10. Nächster Schritt

→ [terraform-setup.md](./terraform-setup.md) — Infrastruktur provisionieren (die Secrets entstehen teilweise erst dort; dieses Runbook sollte vor dem ersten `terraform apply` gestartet und nach den Terraform-Outputs abgeschlossen werden)
