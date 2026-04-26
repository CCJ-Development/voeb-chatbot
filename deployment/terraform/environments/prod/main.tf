# ===========================================================
# PROD Environment — VÖB Service Chatbot
# ===========================================================
# Provisioniert:
#   - 1x SKE Cluster "vob-prod" (2 Nodes: g1a.4d, je 4 vCPU, 16 GB)
#   - 1x PostgreSQL Flex 4.8 Replica HA (4 CPU, 8 GB, 3 Nodes)
#   - 1x Object Storage Bucket (vob-prod)
#
# Eigener Cluster, getrennt von DEV/TEST (ADR-004).
# Geschaetzte Kosten: ~681 EUR/Monat (nach Downgrade 2026-04-26, ADR-005 Addendum)
# ===========================================================

module "stackit" {
  source = "../../modules/stackit"

  project_id  = var.project_id
  region      = "eu01"
  environment = "prod"

  # SKE Cluster — eigener Cluster fuer PROD (ADR-004)
  cluster_name       = "vob-prod"
  kubernetes_version = "1.33"
  availability_zones = ["eu01-3"]

  # K8s API ACL — eingeschraenkt (O4, BSI APP.4.4.A7)
  # ACHTUNG: PROD-Egress-IP ist erst nach terraform apply bekannt (A10).
  # Vorlaeufig: Admin-IP + 0.0.0.0/0 fuer ersten Apply.
  # Nach A10: Auf PROD-Egress-IP + Admin-IP + CI/CD Runner-IP einschraenken.
  cluster_acl = [
    "0.0.0.0/0", # TODO: Nach erstem Apply auf spezifische IPs einschraenken
  ]

  # Maintenance-Window: So 03:00-05:00 UTC (O8, eigenes Fenster)
  # Kein Overlap mit DEV/TEST (02:00-04:00) und PG-Backups (01:00)
  maintenance_start = "03:00:00Z"
  maintenance_end   = "05:00:00Z"

  # Kubeconfig: 90 Tage (Provider-Default ist nur 3600s = 1h!)
  kubeconfig_expiration = 7776000

  # Node Pool "prod" — 2 dedizierte Nodes (nicht shared).
  # Downgrade g1a.8d → g1a.4d am 2026-04-26 nach Sync #6 + Worker-Resource-Rebalance
  # (Cluster-Total-Requests 8.450m → 7.294m, passt jetzt auf 2x g1a.4d ~7.400m allocatable).
  # Einsparung: ~283 EUR/Mo. Rollback: machine_type = "g1a.8d" + terraform apply (~10 Min).
  node_pool_name = "prod"
  node_pool = {
    machine_type = "g1a.4d"
    minimum      = 2
    maximum      = 2
    volume_size  = 100
    volume_type  = "storage_premium_perf2"
  }

  # PostgreSQL Flex 4.8 Replica HA (3 Nodes: Primary + 2 Standby)
  pg_flavor = {
    cpu = 4
    ram = 8
  }
  pg_replicas        = 3
  pg_storage_size    = 50
  pg_backup_schedule = "0 1 * * *" # 01:00 UTC (DEV: 02:00, TEST: 03:00)
  # SEC-01: PG ACL eingeschraenkt
  # ACHTUNG: PROD-Cluster-Egress-IP ist erst nach terraform apply bekannt.
  # Schritt 1: Apply mit Admin-IP only (PG braucht keine Cluster-IP beim Erstellen)
  # Schritt 2: Nach A10 (Egress-IP ermittelt) → hier eintragen + re-apply
  pg_acl = [
    "188.34.73.72/32",   # PROD Cluster Egress (NAT Gateway)
    "109.41.112.160/32", # Admin (Nikolaj Ivanov)
  ]

  # Object Storage
  bucket_name = "vob-prod"
}

# --- Variables ---

variable "project_id" {
  description = "StackIT Project ID"
  type        = string
}

# --- Outputs ---

output "kubeconfig" {
  description = "Kubeconfig fuer kubectl"
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
  description = "PostgreSQL Passwort (onyx_app)"
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
