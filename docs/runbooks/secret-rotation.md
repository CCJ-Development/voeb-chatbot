# Runbook: Secret-Rotation (PROD)

**Erstellt**: 2026-03-22
**Status**: Aktiv
**Verantwortlich**: Nikolaj Ivanov (CCJ)

---

## Zweck

Dieses Runbook beschreibt die Rotation aller PROD-Secrets. Es gilt als Referenz sowohl fuer planmaessige Rotation als auch fuer den Notfall (kompromittiertes Secret).

**Scope:** PROD-Umgebung (`onyx-prod`, Cluster `vob-prod`). DEV/TEST analog, aber weniger kritisch.

**Voraussetzungen:**
- `KUBECONFIG=~/.kube/config-prod` gesetzt
- `gh` CLI authentifiziert (`gh auth status`)
- StackIT CLI authentifiziert (`stackit auth login`)

---

## Uebersicht: Alle PROD-Secrets

| Secret | GitHub Secret | Kubernetes Secret | Woher |
|--------|--------------|-------------------|-------|
| PostgreSQL Passwort | `POSTGRES_PASSWORD` | `onyx-postgresql` | StackIT Portal |
| DB Readonly Passwort | `DB_READONLY_PASSWORD` | in env-configmap | StackIT Portal |
| Redis Passwort | `REDIS_PASSWORD` | `onyx-redis-passwords` | Manuell generieren |
| OpenSearch Passwort | `OPENSEARCH_PASSWORD` | `onyx-opensearch-passwords` | Manuell generieren |
| S3 Access Key | `S3_ACCESS_KEY_ID` | in env-configmap | StackIT Portal |
| S3 Secret Key | `S3_SECRET_ACCESS_KEY` | in env-configmap | StackIT Portal |
| Kubeconfig | `STACKIT_KUBECONFIG` | — (fuer CI/CD) | `terraform apply` oder StackIT Portal |
| Let's Encrypt Certs | — | `onyx-prod-tls` | Automatisch (cert-manager) |

---

## 1. PostgreSQL Passwort rotieren

### Wann: Planmaessig (jaehrlich) oder bei Verdacht auf Kompromittierung

### Schritt-fuer-Schritt

```bash
# 1. Neues Passwort generieren (min. 32 Zeichen, alphanumerisch)
NEW_PW=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)
echo "Neues Passwort: $NEW_PW"

# 2. Passwort im StackIT Portal aendern:
# StackIT Portal → PostgreSQL Flex → Instanz vob-prod → Users → onyx_app → Reset Password
# ACHTUNG: Sobald geaendert, schlagen alle bestehenden DB-Verbindungen fehl!
# Vorgehen: Zuerst Secret aktualisieren, DANN Passwort im Portal aendern + sofort deployen

# 3. GitHub Secret aktualisieren:
gh secret set POSTGRES_PASSWORD --env prod --body "$NEW_PW" -R CCJ-Development/voeb-chatbot

# 4. Passwort in StackIT Portal aendern (jetzt, mit moeglichst kurzer Downtime):
# StackIT Portal → PG Flex vob-prod → Users → onyx_app → Change Password → $NEW_PW eingeben

# 5. Neues Secret in K8s setzen (ohne Neustart):
KUBECONFIG=~/.kube/config-prod \
kubectl create secret generic onyx-postgresql -n onyx-prod \
  --from-literal=username=onyx_app \
  --from-literal=password="$NEW_PW" \
  --dry-run=client -o yaml | \
  KUBECONFIG=~/.kube/config-prod kubectl apply -f -

# 6. Helm upgrade ausloesen (damit alle Pods das neue Secret erhalten):
gh workflow run stackit-deploy.yml -f environment=prod -R CCJ-Development/voeb-chatbot

# 7. Health verifizieren:
curl -sk https://chatbot.voeb-service.de/api/health
```

---

## 2. DB Readonly Passwort rotieren

```bash
# 1. Neues Passwort generieren
NEW_READONLY_PW=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)

# 2. StackIT Portal → PG Flex vob-prod → Users → db_readonly_user → Change Password

# 3. GitHub Secret aktualisieren:
gh secret set DB_READONLY_PASSWORD --env prod --body "$NEW_READONLY_PW" -R CCJ-Development/voeb-chatbot

# 4. Helm upgrade ausloesen:
gh workflow run stackit-deploy.yml -f environment=prod -R CCJ-Development/voeb-chatbot
```

---

## 3. Redis Passwort rotieren

```bash
# 1. Neues Passwort generieren
NEW_REDIS_PW=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)

# 2. GitHub Secret aktualisieren:
gh secret set REDIS_PASSWORD --env prod --body "$NEW_REDIS_PW" -R CCJ-Development/voeb-chatbot

# 3. Helm upgrade ausloesen (Redis Operator + alle Pods erhalten neues Passwort):
gh workflow run stackit-deploy.yml -f environment=prod -R CCJ-Development/voeb-chatbot

# 4. Redis Connectivity pruefen:
KUBECONFIG=~/.kube/config-prod \
kubectl exec -n onyx-prod deployment/onyx-prod-api-server -- \
  python3 -c "import redis; r = redis.from_url('redis://:${NEW_REDIS_PW}@onyx-prod.onyx-prod.svc.cluster.local:6379'); print(r.ping())"
```

---

## 4. OpenSearch Passwort rotieren

```bash
# 1. Neues Passwort generieren (OpenSearch erfordert min. 8 Zeichen, Sonderzeichen erlaubt)
NEW_OS_PW=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9!@#$%' | head -c 24)

# 2. GitHub Secret aktualisieren:
gh secret set OPENSEARCH_PASSWORD --env prod --body "$NEW_OS_PW" -R CCJ-Development/voeb-chatbot

# 3. Helm upgrade ausloesen:
gh workflow run stackit-deploy.yml -f environment=prod -R CCJ-Development/voeb-chatbot

# 4. Health pruefen:
KUBECONFIG=~/.kube/config-prod \
kubectl exec -n onyx-prod onyx-opensearch-master-0 -c opensearch -- \
  curl -sk -u "admin:$NEW_OS_PW" "https://localhost:9200/_cluster/health?pretty"
```

---

## 5. S3 Credentials rotieren

### Wann: Bei Kompromittierung oder planmaessiger Rotation

```bash
# 1. Neue Credentials in StackIT Portal erstellen:
# StackIT Portal → Object Storage → Bucket vob-prod → Credentials → Create new credential
# ODER via CLI:
stackit object-storage credentials create --project-id b3d2a04e-46de-48bc-abc6-c4dfab38c2cd

# Neue Credentials notieren (nur beim Erstellen sichtbar!):
# ACCESS_KEY_ID=<neuer_key>
# SECRET_ACCESS_KEY=<neues_secret>

# 2. GitHub Secrets aktualisieren:
gh secret set S3_ACCESS_KEY_ID --env prod --body "$ACCESS_KEY_ID" -R CCJ-Development/voeb-chatbot
gh secret set S3_SECRET_ACCESS_KEY --env prod --body "$SECRET_ACCESS_KEY" -R CCJ-Development/voeb-chatbot

# 3. Helm upgrade ausloesen:
gh workflow run stackit-deploy.yml -f environment=prod -R CCJ-Development/voeb-chatbot

# 4. Alte Credentials loeschen (erst nach erfolgreichem Deploy!):
# StackIT Portal → Object Storage → vob-prod → Credentials → Alte Credentials loeschen
# ODER via CLI:
# stackit object-storage credentials delete <ALTE_CREDENTIALS_ID> --project-id ...
```

---

## 6. Kubeconfig erneuern

### Wann: Alle 90 Tage (Expiration), bei Kompromittierung oder nach Kubeconfig-Leck

**Naechste Expiration PROD:** `2026-06-09`

```bash
# Option A: Terraform (empfohlen — erneuert automatisch)
cd deployment/terraform/environments/prod
terraform apply -target=stackit_ske_kubeconfig.main
# → Neue Kubeconfig in terraform.tfstate

# Kubeconfig extrahieren:
terraform output -raw kubeconfig > ~/.kube/config-prod
chmod 600 ~/.kube/config-prod

# Ablaufdatum pruefen:
cat ~/.kube/config-prod | python3 -c "
import yaml, sys, datetime
kc = yaml.safe_load(sys.stdin)
# Expiry ist in den User-Credentials:
for user in kc.get('users', []):
    for k, v in (user.get('user', {}) or {}).items():
        if 'expir' in k.lower():
            print(f'{k}: {v}')
"

# Option B: StackIT Portal (falls Terraform nicht verfuegbar)
# StackIT Portal → SKE → Cluster vob-prod → Kubeconfig herunterladen → Ablauf 90 Tage waehlen

# In beiden Faellen: GitHub Secret aktualisieren
KUBECONFIG_B64=$(base64 -i ~/.kube/config-prod)
gh secret set STACKIT_KUBECONFIG --env prod --body "$KUBECONFIG_B64" -R CCJ-Development/voeb-chatbot

# Verifizieren:
KUBECONFIG=~/.kube/config-prod kubectl get pods -n onyx-prod
```

**Ablauf DEV+TEST Kubeconfig:** `2026-06-14` (erneuert 2026-03-16)

---

## 7. Let's Encrypt Zertifikate

### Automatische Erneuerung (kein manueller Eingriff noetig)

cert-manager erneuert TLS-Zertifikate automatisch 30 Tage vor Ablauf. Die aktiven Zertifikate haben eine Laufzeit von 90 Tagen (Let's Encrypt Standard).

### Status pruefen

```bash
# Alle Zertifikate und ihren Status:
kubectl get certificate -A

# Details (inkl. Ablaufdatum):
KUBECONFIG=~/.kube/config-prod \
kubectl get certificate -n onyx-prod onyx-prod-tls -o jsonpath='{.status.notAfter}'

# Certificate Request Status:
KUBECONFIG=~/.kube/config-prod \
kubectl get certificaterequest -n onyx-prod
```

### Manuelle Erneuerung erzwingen (Notfall)

```bash
# Zertifikat loeschen → cert-manager erstellt es neu:
KUBECONFIG=~/.kube/config-prod \
kubectl delete certificate onyx-prod-tls -n onyx-prod
# cert-manager erkennt den fehlenden Certificate-Secret und erstellt das Cert neu
# ACME-Challenge laeuft erneut durch (DNS-01 via Cloudflare, ~1-2 Min)

# Status verfolgen:
KUBECONFIG=~/.kube/config-prod \
kubectl describe certificate onyx-prod-tls -n onyx-prod
```

**Hinweis:** Let's Encrypt Rate Limit = 5 Zertifikate pro Domain pro Woche. Bei mehrfacher manueller Erneuerung kann das Limit erreicht werden. Im Notfall: TLS-Secret kopieren statt neu anfordern (Lesson Learned von PROD-Aktivierung 2026-03-17).

---

## 8. Notfall: Kompromittiertes Secret

Bei Verdacht auf ein kompromittiertes Secret (z.B. Secret in Git committet, Zugriff durch Dritte):

1. **Sofort** das Secret in der Quelle rotieren (StackIT Portal / OpenSSL)
2. GitHub Secret aktualisieren
3. `helm upgrade` ausloesen (alle Pods erhalten neues Secret)
4. Zugriffslogs pruefen (StackIT Portal → Audit Logs, falls verfuegbar)
5. Incident dokumentieren in `docs/incidents/YYYY-MM-DD-secret-kompromittiert.md`
6. VÖB Operations informieren (bei PROD, P1/P2 Severity)

---

## Referenzen

- Helm Deploy Runbook: `docs/runbooks/helm-deploy.md`
- Betriebskonzept (Secret Management): `docs/betriebskonzept.md`
- Sicherheitskonzept (SEC-04): `docs/sicherheitskonzept.md`
- DNS/TLS Runbook: `docs/runbooks/dns-tls-setup.md`
- GitHub Secrets verwalten: `gh secret list --env prod -R CCJ-Development/voeb-chatbot`
