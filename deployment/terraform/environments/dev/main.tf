# ===========================================================
# DEV Environment — VÖB Service Chatbot
# ===========================================================
# Provisioniert:
#   - 1× SKE Cluster (2 Nodes: g1a.4d, je 4 vCPU, 16 GB)
#   - 1× PostgreSQL Flex 2.4 Single (2 CPU, 4 GB)
#   - 1× Object Storage Bucket (vob-dev)
#
# Node Pool "devtest" bedient DEV + TEST (ADR-004).
# Kostenoptimierung (2026-03-16): g1a.8d → g1a.4d nach Resource-Requests-Senkung.
# Geschätzte Kosten DEV-Anteil: ~293 EUR/Monat
# ===========================================================

module "stackit" {
  source = "../../modules/stackit"

  project_id  = var.project_id
  region      = "eu01"
  # WICHTIG: Muss "dev" bleiben, weil environment den PG-Instanznamen bestimmt
  # (vob-dev). Änderung auf "devtest" würde PG-Instanz löschen + neu erstellen!
  # Der Node Pool heißt bereits "devtest" (im Modul hardcoded).
  environment = "dev"

  # SKE Cluster
  cluster_name       = "vob-chatbot"
  kubernetes_version = "1.33"
  availability_zones = ["eu01-3"]

  # Node Pool "devtest" — 2 Nodes für DEV + TEST (ADR-004)
  # Kostenoptimierung (2026-03-16): g1a.8d → g1a.4d (4 vCPU, 16 GB)
  # Begründung: CPU Actual 5,8% auf g1a.8d. Resource Requests von ~7.760m auf ~5.760m gesenkt.
  # 2x g1a.4d allocatable: ~7.400m CPU, ~28 Gi RAM → 78% CPU, ~55% RAM. Ausreichend.
  # Einsparung: 2x (283,18 - 141,59) = 283,18 EUR/Monat.
  # Rollback: machine_type = "g1a.8d" + terraform apply (~10 Min Rolling Update).
  node_pool = {
    machine_type = "g1a.4d"
    minimum      = 2
    maximum      = 2
    volume_size  = 100
    volume_type  = "storage_premium_perf2"
  }

  # PostgreSQL Flex 2.4 Single
  pg_flavor = {
    cpu = 2
    ram = 4
  }
  pg_replicas        = 1
  pg_storage_size    = 20
  pg_backup_schedule = "0 2 * * *"
  # SEC-01: PG ACL auf Cluster-Egress-IP + Admin eingeschränkt (2026-03-03)
  # Cluster-Egress-IP: 188.34.93.194 (NAT Gateway, fest für Cluster-Lifecycle)
  # Admin-IP: 109.41.112.160 (Niko, für direkten DB-Zugriff bei Debugging)
  # ACHTUNG: Admin-IP kann sich bei ISP-Wechsel ändern → dann hier aktualisieren
  pg_acl = [
    "188.34.93.194/32",  # SKE Cluster Egress (alle Pods)
    "109.41.112.160/32", # Admin (Nikolaj Ivanov)
  ]

  # Object Storage
  bucket_name = "vob-dev"
}

# --- Variables ---

variable "project_id" {
  description = "StackIT Project ID"
  type        = string
}

# --- Outputs ---

output "kubeconfig" {
  description = "Kubeconfig für kubectl"
  value       = module.stackit.kubeconfig
  sensitive   = true
}

output "pg_host" {
  description = "PostgreSQL Host"
  value       = module.stackit.pg_host
}

output "pg_port" {
  description = "PostgreSQL Port"
  value       = module.stackit.pg_port
}

output "pg_password" {
  description = "PostgreSQL Passwort"
  value       = module.stackit.pg_password
  sensitive   = true
}

output "pg_readonly_password" {
  description = "PostgreSQL Read-Only Passwort"
  value       = module.stackit.pg_readonly_password
  sensitive   = true
}

output "bucket_name" {
  description = "S3 Bucket Name"
  value       = module.stackit.bucket_name
}
