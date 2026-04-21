# StackIT Service Accounts

**Zielgruppe:** Tech Lead beim Kunden-Klon
**Dauer:** 30 min
**Phase:** teilweise 1 (Terraform-SA) + 7 (Monitoring-SA) im [Master-Playbook](./kunden-klon-onboarding.md)

Dieses Runbook beschreibt die Service Accounts, die im Projekt benötigt werden, wie sie angelegt werden, welche Rollen sie brauchen und wie die JSON-Credentials sicher verwaltet werden.

---

## Überblick

Wir brauchen **zwei** Service Accounts:

| Service Account | Zweck | Rollen | Wo genutzt |
|---|---|---|---|
| **Terraform SA** | Infrastruktur provisionieren (SKE, PG Flex, Object Storage) | `project.admin` | Lokale Terraform-Ausführung |
| **Monitoring SA** | PG-Backup-API abfragen für pg-backup-check CronJob | `project.member` + `postgresflex.reader` | K8s Secret in monitoring-Namespace |

**Wichtig:** Der Monitoring-SA darf **nicht** die gleiche Identität wie der Terraform-SA haben — Least-Privilege-Prinzip. Ein kompromittierter Monitoring-SA soll keine Infrastruktur ändern können.

---

## Voraussetzungen

- StackIT-Portal-Zugang mit `project.admin`-Rolle
- `stackit` CLI installiert (`brew install stackitcloud/tap/stackit`)
- `jq`, `openssl` installiert

---

## 1. Terraform Service Account (Phase 1)

### 1.1 Im Portal erstellen

1. StackIT Portal → Projekt → **Service Accounts**
2. „Service Account anlegen" → Name: `<customer_short>-terraform`
3. Rolle zuweisen: **`project.admin`** (Pflicht, weil Terraform SKE-Cluster + PG + Bucket erstellt)
4. Speichern

### 1.2 Key generieren

1. Im angelegten SA → „Keys" → „Neuen Key erstellen"
2. Format: **JSON** (wichtig — Terraform-Provider verarbeitet nur JSON, nicht PEM)
3. Datei herunterladen: `<customer_short>-terraform-credentials.json`
4. **Sofort sichern** — wird nur einmal angezeigt

Struktur der JSON-Datei:
```json
{
  "id": "…",
  "publicKey": "…",
  "credentials": {
    "kid": "…",
    "iss": "stackit@sa.stackit.cloud",
    "sub": "<SA_ID>",
    "aud": "https://service-account.api.stackit.cloud",
    "privateKey": "-----BEGIN PRIVATE KEY-----\n…\n-----END PRIVATE KEY-----\n"
  }
}
```

### 1.3 Credentials speichern + schützen

```bash
# In sicheren Ordner verschieben
mkdir -p ~/.stackit/credentials
mv ~/Downloads/<customer_short>-terraform-credentials.json ~/.stackit/credentials/
chmod 600 ~/.stackit/credentials/*.json

# Terraform-Zugriff einrichten
export STACKIT_SERVICE_ACCOUNT_KEY_PATH=~/.stackit/credentials/<customer_short>-terraform-credentials.json

# Persistieren in ~/.zshrc oder ~/.bashrc
echo "export STACKIT_SERVICE_ACCOUNT_KEY_PATH=~/.stackit/credentials/<customer_short>-terraform-credentials.json" >> ~/.zshrc
```

Alternativ: Im Projekt-Root eine `.envrc` (mit `direnv`) anlegen, damit der Path nur im Repo aktiv ist:
```bash
# .envrc (gitignored)
export STACKIT_SERVICE_ACCOUNT_KEY_PATH=~/.stackit/credentials/<customer_short>-terraform-credentials.json
```

### 1.4 Validierung

```bash
cd deployment/terraform/environments/dev
terraform plan
# Erwartung: Plan läuft ohne "authentication"-Fehler
```

---

## 2. Monitoring Service Account (Phase 7)

### 2.1 Im Portal erstellen

1. StackIT Portal → Projekt → **Service Accounts**
2. „Service Account anlegen" → Name: `<customer_short>-monitoring-pg-backup`
3. Rolle zuweisen:
   - `project.member` (Basis-Zugriff)
   - `postgresflex.reader` (Read-Only auf PG-Instanzen + Backups)
4. Speichern

### 2.2 Key generieren und extrahieren

Identisch zu §1.2 — JSON herunterladen.

### 2.3 Private Key als K8s-Secret

Der CronJob `pg-backup-check` signiert JWT-Tokens mit dem Private Key. Daher muss der Private Key als eigenständiges K8s-Secret vorliegen:

```bash
# Private Key aus JSON extrahieren
jq -r '.credentials.privateKey' ~/Downloads/<customer_short>-monitoring-pg-backup-credentials.json > /tmp/monitoring-pk.pem

# Als K8s-Secret anlegen
kubectl --context <CLUSTER_PROD> -n monitoring create secret generic stackit-sa-monitoring \
  --from-file=private_key.pem=/tmp/monitoring-pk.pem \
  --from-literal=key_id='<KID_AUS_JSON>' \
  --from-literal=issuer='stackit@sa.stackit.cloud' \
  --from-literal=subject='<SUB_AUS_JSON>'

# Privatekey-File sofort löschen (nicht rumliegen lassen)
shred -u /tmp/monitoring-pk.pem
```

> ⚠️ **Fallstrick:** Die JSON enthält sowohl `publicKey` als auch `credentials.privateKey`. Der CronJob braucht die `credentials.privateKey` (die im `credentials`-Unterobjekt). Achte auf den Pfad beim `jq`-Extract.

### 2.4 CronJob deployen

```bash
kubectl --context <CLUSTER_PROD> apply -f deployment/k8s/monitoring-exporters/pg-backup-check-prod.yaml
```

### 2.5 Validierung

```bash
# CronJob läuft
kubectl --context <CLUSTER_PROD> -n monitoring get cronjob pg-backup-check

# Manuell triggern (statt alle 4h zu warten)
kubectl --context <CLUSTER_PROD> -n monitoring create job --from=cronjob/pg-backup-check pg-backup-check-manual-$(date +%s)

# Logs prüfen
kubectl --context <CLUSTER_PROD> -n monitoring logs -l job-name=pg-backup-check-manual-... --tail=50
```

Erwartung: Token-Exchange gegen StackIT-API erfolgreich, Backup-Liste für `<PG_INSTANCE_PROD>` geliefert.

---

## 3. StackIT AI Model Serving Token

Kein Service Account, sondern ein API-Token. Wird nicht als SA geführt, weil er nur zum Authentifizieren gegen das Model-Serving-Gateway dient.

### 3.1 Token erstellen

1. StackIT Portal → **AI Model Serving** → **API Keys**
2. „Neuen Key erstellen" → Name: `<customer_short>-llm-token`
3. Gültigkeit: 1 Jahr
4. Token kopieren (wird nur einmal angezeigt)

### 3.2 Nutzung

- Direkt in der Onyx-Admin-UI bei Provider-Konfiguration eintragen
- Wird dann in `cloud_embedding_model` + `llm_provider`-Tabellen in der Postgres gespeichert
- Kein K8s-Secret nötig (Admin-UI-Flow)

Details: [llm-konfiguration.md](./llm-konfiguration.md)

---

## 4. Container Registry Robot Account

Auch kein SA im eigentlichen Sinn, sondern eine spezielle Identität nur für Registry-Zugriff.

### 4.1 Anlegen

1. StackIT Portal → **Container Registry** → Projekt `<REGISTRY_PROJECT>` → **Robot Accounts**
2. „Robot Account anlegen" → Name: `<customer_short>-github-ci`
3. Permissions: **Pull + Push** (für Build + Deploy)
4. Token speichern (einmalig angezeigt)

### 4.2 Nutzung

- `STACKIT_REGISTRY_USER` = Robot-Account-Name (GitHub Secret)
- `STACKIT_REGISTRY_PASSWORD` = Robot-Token (GitHub Secret)
- K8s Image Pull Secret `stackit-registry` in jedem Applikations-Namespace:
  ```bash
  kubectl -n <NAMESPACE> create secret docker-registry stackit-registry \
    --docker-server=registry.onstackit.cloud \
    --docker-username='<ROBOT_ACCOUNT_NAME>' \
    --docker-password='<ROBOT_TOKEN>'
  ```

---

## 5. Lessons Learned (aus VÖB-Projekt)

### 5.1 Private-Key-Pfad in der JSON

**Problem:** Beim initialen Monitoring-Setup wurde statt `credentials.privateKey` der `publicKey` ins K8s-Secret gelegt. JWT-Signierung schlug mit kryptischen Fehlern fehl.

**Lösung:** `jq -r '.credentials.privateKey'` (nicht `.publicKey` und nicht nur `.privateKey` auf Top-Level).

**Pattern:** Beim Extract immer die volle JSON anzeigen und prüfen, welches Feld den `-----BEGIN PRIVATE KEY-----`-Block enthält.

Referenz: Memory `backup-recovery-analyse.md`, 2026-03-16.

### 5.2 Registry-Credentials-Drift

**Problem:** Nach Token-Rotation wurde das K8s-Secret `stackit-registry` aktualisiert, aber das GitHub-Secret `STACKIT_REGISTRY_PASSWORD` blieb stehen — CI/CD-Builds liefen mit 401 Unauthorized.

**Lösung:** Bei Token-Rotation **immer beide** Stellen aktualisieren. Runbook: [secret-rotation.md](./secret-rotation.md).

Quick-Fix bei 401 in CI:
```bash
# Credentials aus aktuellem K8s-Secret extrahieren
kubectl -n <NAMESPACE> get secret stackit-registry -o jsonpath='{.data.\.dockerconfigjson}' | base64 -d | jq
# Passwort aus `auth`-Feld base64-decoden

# In GitHub Secret schreiben
gh secret set STACKIT_REGISTRY_PASSWORD
```

Referenz: CHANGELOG Sync #5 (2026-04-14).

### 5.3 Registry Race Condition bei parallelem Login

**Problem:** Frontend-Build und Backend-Build starteten parallel und loggten sich beide gleichzeitig bei der StackIT Registry ein → zweiter Login mit 401.

**Lösung:** `build-backend needs: build-frontend` in `stackit-deploy.yml` — serialisiert die Logins.

**Trade-off:** +4-5 Min Build-Zeit, dafür keine flaky CI-Reruns mehr.

Referenz: CHANGELOG 2026-04-16.

### 5.4 SA-Key Lifetime und Rotation

**Problem:** StackIT SA-Keys laufen nicht automatisch ab, aber Best Practice ist jährliche Rotation.

**Lösung:** Kalender-Eintrag setzen. Rotation via:
1. Neuen Key im Portal anlegen
2. `terraform apply` mit neuem Path
3. Alten Key im Portal löschen

**Nie beide Keys gleichzeitig aktiv halten** — das erschwert Audit.

---

## 6. Typische Fehler

### „Error: authentication failed: no service account key found"

`STACKIT_SERVICE_ACCOUNT_KEY_PATH` nicht gesetzt oder zeigt auf falsche Datei. Prüfen:
```bash
echo $STACKIT_SERVICE_ACCOUNT_KEY_PATH
cat $STACKIT_SERVICE_ACCOUNT_KEY_PATH | jq '.credentials.iss'
# Erwartung: "stackit@sa.stackit.cloud"
```

### CronJob Backup-Check liefert `401 Unauthorized`

1. JWT-Signierung schlägt fehl → Private Key falsch extrahiert (siehe §5.1)
2. Token-Lifetime abgelaufen → Ist JWT `exp` > `now()` bei Signierung? Script prüfen.
3. SA hat `postgresflex.reader`-Rolle nicht → im Portal prüfen

### `terraform apply` fordert interaktive Auth

```bash
stackit auth login
# Browser-Flow
# Danach: terraform apply re-try
```

---

## 7. Checkliste

- [ ] Terraform SA angelegt (`project.admin`)
- [ ] Terraform SA Key als JSON heruntergeladen, `chmod 600`
- [ ] `STACKIT_SERVICE_ACCOUNT_KEY_PATH` in Shell gesetzt
- [ ] `terraform plan` funktioniert ohne Auth-Prompt
- [ ] Monitoring SA angelegt (`project.member` + `postgresflex.reader`)
- [ ] Monitoring SA Private Key als K8s-Secret `stackit-sa-monitoring` in `monitoring`-Namespace
- [ ] CronJob `pg-backup-check` deployed und manuell getestet (grüne Logs)
- [ ] LLM-API-Token erstellt, in Onyx-Admin-UI bei Provider-Konfig hinterlegt
- [ ] Container Registry Robot Account erstellt
- [ ] GitHub Secrets `STACKIT_REGISTRY_USER` + `STACKIT_REGISTRY_PASSWORD` gesetzt
- [ ] K8s `stackit-registry` Image Pull Secret in Applikations-NS

---

## 8. Nächster Schritt

→ [monitoring-setup.md](./monitoring-setup.md) — Prometheus + Grafana + Alert-Stack installieren
