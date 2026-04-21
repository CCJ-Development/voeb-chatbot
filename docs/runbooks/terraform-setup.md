# Terraform Initial-Setup

**Zielgruppe:** Tech Lead / DevOps beim Aufsetzen eines neuen Kunden-Projekts
**Dauer:** 2–3 h
**Phase:** 2 im [Master-Playbook](./kunden-klon-onboarding.md)

Dieses Runbook beschreibt, wie Terraform für einen neuen Kunden konfiguriert und die StackIT-Infrastruktur (SKE-Cluster, PostgreSQL Flex, Object Storage) provisioniert wird.

---

## Voraussetzungen

- Phase 1 ([stackit-projekt-setup.md](./stackit-projekt-setup.md)) abgeschlossen: CLI installiert, Service Account vorhanden, eingeloggt
- `terraform` installiert (`brew install terraform`, Version ≥ 1.6)
- Kundenspezifische Variablen bekannt (siehe [Master-Playbook §2](./kunden-klon-onboarding.md))
- StackIT Project ID vorhanden

---

## 1. Verzeichnisstruktur verstehen

```
deployment/terraform/
├── modules/
│   ├── stackit/           # Modul: SKE + PG + Bucket (DEV/PROD nutzen das)
│   └── stackit-data/      # Modul: nur PG + Bucket (ohne SKE, für optionales TEST)
└── environments/
    ├── dev/               # DEV-Environment
    │   ├── main.tf
    │   ├── backend.tf
    │   └── terraform.tfvars
    ├── prod/              # PROD-Environment
    └── test/              # Template für optionale TEST-Umgebung (inaktiv)
```

**Prinzip:** Ein Environment = ein Terraform-State. Separate `terraform init/plan/apply` pro Environment.

---

## 2. Kundenspezifische Anpassungen

### 2.1 Projekt-ID setzen

Pro Environment eine `{env}.auto.tfvars` anlegen (gitignored). Beispiel für DEV:

```bash
cat > deployment/terraform/environments/dev/dev.auto.tfvars <<EOF
# ===========================================================
# <CUSTOMER_NAME> DEV Environment — Secrets (GITIGNORED)
# ===========================================================
project_id = "<PROJECT_ID>"
EOF
```

**Wichtig:** Das Muster `*.auto.tfvars` ist bereits in `.gitignore` hinterlegt. Nicht committen.

Analog für PROD (`prod.auto.tfvars`) und ggf. TEST (`test.auto.tfvars`).

### 2.2 Environment-spezifische `main.tf` prüfen

`deployment/terraform/environments/dev/main.tf` enthält kundenspezifische Defaults:

```hcl
module "stackit" {
  source       = "../../modules/stackit"
  project_id   = var.project_id
  region       = "eu01"
  environment  = "dev"
  cluster_name = "<CLUSTER_DEV>"           # z.B. "<customer>-chatbot"
  bucket_name  = "<BUCKET_DEV>"             # z.B. "<customer>-dev"

  node_pool = {
    machine_type = "g1a.4d"                  # Machine-Typ (StackIT Preisliste prüfen!)
    minimum      = 2
    maximum      = 2
    volume_size  = 100
    volume_type  = "storage_premium_perf2"
  }

  pg_flavor = {
    cpu = 2
    ram = 4
  }
  pg_replicas        = 1
  pg_storage_size    = 20
  pg_backup_schedule = "0 2 * * *"           # DEV: 02:00 UTC

  pg_acl = [
    "<CLUSTER_EGRESS_IP>/32",                # Nach Cluster-Create bekannt
    "<ADMIN_IP>/32",                         # Tech-Lead-IP
  ]
}
```

Ersetze alle `<PLATZHALTER>` durch Kunden-Werte aus dem Master-Playbook.

### 2.3 Backend-Konfiguration

`backend.tf` definiert, wo der Terraform-State liegt. **Für Solo-Dev / initial: lokaler State.** Später ggf. Remote-Backend (StackIT Object Storage mit S3-Protokoll).

```hcl
# Initial (lokaler State, einfachster Start):
terraform {
  required_version = ">= 1.6"
  # State liegt als terraform.tfstate in diesem Verzeichnis
}
```

**Wichtig:** `terraform.tfstate` **nicht committen** (steht in `.gitignore`). Backup per Hand oder per Remote-Backend absichern.

---

## 3. SSH-Key für Cluster-Zugriff (einmalig)

StackIT SKE erwartet einen SSH-Public-Key für den initialen Cluster-Zugriff. Falls noch nicht vorhanden:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/stackit_<CUSTOMER_SHORT>_ed25519 -C "stackit-<CUSTOMER_SHORT>"
```

Der Public-Key wird im Terraform-Modul referenziert (aktuell automatisch via `~/.ssh/id_rsa.pub`, falls abweichend: `variables.tf` anpassen).

---

## 4. Terraform init + plan + apply

### 4.1 DEV zuerst

```bash
cd deployment/terraform/environments/dev

# Init: Provider downloaden, Backend initialisieren
terraform init

# Plan: Zeigt alle zu erstellenden Ressourcen
terraform plan -out=tfplan

# Review: Prüfe den Plan. Erwartung:
# - 1x stackit_ske_cluster
# - 1x stackit_ske_kubeconfig
# - 1x stackit_postgresflex_instance
# - 2x stackit_postgresflex_user (app + readonly)
# - 1x stackit_objectstorage_bucket
# Gesamt ca. 6 Ressourcen "to add"

# Apply: Tatsächlich erstellen (Laufzeit ca. 10–15 Min)
terraform apply tfplan
```

### 4.2 Outputs extrahieren

```bash
# Kubeconfig (base64, für GitHub Secret)
terraform output -raw kubeconfig | base64 > kubeconfig-dev.b64

# PG-Credentials
terraform output -raw pg_host
terraform output -raw pg_password                # sensitive, nur per terraform show
terraform output -raw pg_readonly_password

# Bucket-Name bestätigen
terraform output -raw bucket_name
```

### 4.3 Object-Storage-Credentials erstellen

Object Storage braucht separate Access-Keys, die **nicht** automatisch via Terraform erstellt werden:

```bash
# Credentials-Group listen oder erstellen
stackit object-storage credentials-group list --project-id=<PROJECT_ID>

# Falls keine Group existiert:
stackit object-storage credentials-group create --name default --project-id=<PROJECT_ID>

# Credentials erstellen (Laufzeit 1 Jahr)
stackit object-storage credentials create \
  --credentials-group-id=<GROUP_ID> \
  --project-id=<PROJECT_ID> \
  --expire-date=2027-04-21T23:59:59Z \
  --output-format=json
```

Access-Key und Secret-Key werden **einmalig angezeigt** — sofort in `values-dev-secrets.yaml` und GitHub Environment Secrets speichern.

### 4.4 Cluster-Egress-IP ermitteln

Nach Cluster-Create braucht die PG-ACL die **Cluster-Egress-IP**. Die ist nicht direkt in Terraform-Outputs verfügbar:

```bash
# kubeconfig setzen
export KUBECONFIG=$(mktemp)
terraform output -raw kubeconfig > $KUBECONFIG

# IP via curl aus einem Pod ermitteln
kubectl run egress-check --rm -it --image=curlimages/curl --restart=Never -- curl -s ifconfig.me
```

Die ermittelte IP in `main.tf` unter `pg_acl` eintragen und `terraform apply` erneut laufen lassen (ACL-Update):

```bash
terraform plan
terraform apply
```

### 4.5 PROD analog

```bash
cd ../prod
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

PROD hat zusätzlich:
- HA PG Flex (3 Replicas)
- Eigener Cluster (nicht shared mit DEV)
- Eigene Egress-IP
- Backup-Schedule 01:00 UTC
- Entra ID App Registration benötigt vorher (für OIDC-Secrets)

---

## 5. Terraform-Output-Verarbeitung

Folgende Outputs werden in Helm-Values und GitHub Secrets weiterverarbeitet:

| Terraform Output | Weiterverarbeitung |
|---|---|
| `kubeconfig` | Base64 in GitHub Secret `STACKIT_KUBECONFIG` |
| `pg_host` | In `values-{env}.yaml` unter `configMap.POSTGRES_HOST` |
| `pg_password` | In GitHub Environment Secret `POSTGRES_PASSWORD` |
| `pg_readonly_password` | In GitHub Environment Secret `DB_READONLY_PASSWORD` |
| `bucket_name` | In `values-{env}.yaml` unter `configMap.S3_FILE_STORE_BUCKET_NAME` |

---

## 6. State-Backup

Der lokale `terraform.tfstate` enthält **alle Ressourcen-IDs und sensible Werte** (Passwörter). Pflichtaufgaben:

1. **Nie committen** (gitignored)
2. **Lokal sichern**: Nach jedem `apply` eine Kopie: `cp terraform.tfstate ~/backups/tfstate-<ENV>-$(date +%Y%m%d).bak`
3. **Zugriff beschränken**: `chmod 600 terraform.tfstate*`
4. **Optional: Remote-Backend aktivieren** (StackIT Object Storage, siehe Abschnitt 10)

---

## 7. Lifecycle-Protection

Alle kritischen Ressourcen haben in den Modulen `prevent_destroy = true` gesetzt:

- `stackit_ske_cluster` (SKE Cluster)
- `stackit_postgresflex_instance` (PG Flex Instanz)
- `stackit_objectstorage_bucket` (Bucket)

**Konsequenz:** Ein `terraform destroy` scheitert, solange `prevent_destroy` aktiv ist. Zum gewollten Abbau:
1. Im Modul `prevent_destroy = false` setzen
2. `terraform apply` (aktiviert die Lifecycle-Änderung)
3. `terraform destroy`
4. Optional: Danach `prevent_destroy = true` wiederherstellen für spätere Wiederverwendung

---

## 8. Typische Fehler

### "Error: ProjectID is required"

`*.auto.tfvars` fehlt oder `project_id = "..."` nicht gesetzt. Beispiel:
```hcl
project_id = "b3d2a04e-46de-48bc-abc6-c4dfab38c2cd"
```

### "Error: cluster already exists"

SKE-Cluster-Namen sind projektweit eindeutig. Wähle einen anderen `cluster_name` oder importiere den existierenden:
```bash
terraform import module.stackit.stackit_ske_cluster.main <PROJECT_ID>,<CLUSTER_NAME>
```

### "Error: failed to delete user: role owns objects"

PG-User kann nicht gelöscht werden, solange Objekte (Tabellen, DBs) auf ihn gepriviligiert sind. Entweder:
- Objekte vorher löschen (`DROP DATABASE`, `REASSIGN OWNED`)
- Oder: PG-Instance direkt über StackIT CLI löschen (umgeht die User-Abhängigkeit):
  ```bash
  stackit postgresflex instance delete <PG_INSTANCE_ID> --project-id=<PROJECT_ID> --region=eu01
  ```
  Danach `terraform state rm` für die betroffenen Ressourcen.

### Kubeconfig abgelaufen (nach 90 Tagen)

```bash
terraform apply -replace=module.stackit.stackit_ske_kubeconfig.main
terraform output -raw kubeconfig | base64 > kubeconfig-<env>.b64
# Neues Secret in GitHub hochladen
```

---

## 9. Machine-Typ-Entscheidung (g1a vs. c1a)

**Achtung:** StackIT hat die AMD-General-Purpose-Instanzfamilie von `g1a.*` auf `c1a.*` umbenannt. Aktuelle Preisliste kennt nur `c1a.*`.

**Empfehlung für neue Kunden:** `c1a.*` statt `g1a.*` in `node_pool.machine_type` nutzen. Entsprechende Varianten:
- `c1a.4d` (4 vCPU, 8 GB) — DEV
- `c1a.8d` (8 vCPU, 16 GB) — PROD-Einstieg
- `c1a.16d` (16 vCPU, 32 GB) — PROD-HA

**Legacy-Kunden (VÖB):** `g1a.4d` / `g1a.8d` funktionieren noch.

---

## 10. Optional: Remote-State-Backend (StackIT Object Storage)

Wenn mehrere Personen am Projekt arbeiten oder State-Loss verhindert werden soll:

```hcl
# backend.tf
terraform {
  backend "s3" {
    bucket                      = "<CUSTOMER_SHORT>-tfstate"
    key                         = "dev/terraform.tfstate"
    region                      = "eu01"
    endpoint                    = "https://object.storage.eu01.onstackit.cloud"
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_region_validation      = true
    force_path_style            = true
  }
}
```

Access-Key/Secret-Key via `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` Umgebungsvariablen. State-Locking via DynamoDB ist bei StackIT nicht verfügbar — bei Multi-User-Setup State-Konflikte manuell managen.

---

## 11. Checkliste nach Terraform-Setup

- [ ] `terraform apply` DEV fehlerfrei
- [ ] `terraform apply` PROD fehlerfrei
- [ ] Kubeconfigs extrahiert und gespeichert
- [ ] PG-Credentials in GitHub Environment Secrets
- [ ] Bucket-Credentials erstellt und gespeichert
- [ ] Cluster-Egress-IP ermittelt und in PG-ACL ergänzt
- [ ] `terraform.tfstate` lokal gesichert (Backup)
- [ ] `prevent_destroy = true` verifiziert für kritische Ressourcen

---

## 12. Nächster Schritt

→ [stackit-postgresql.md](./stackit-postgresql.md) — Datenbank anlegen, Readonly-User einrichten
