# ===========================================================
# Terraform State Backend — PROD
# ===========================================================
# Local State bis Remote-Backend eingerichtet ist.
#
# terraform init -backend-config="access_key=..." \
#                -backend-config="secret_key=..."
# ===========================================================

# PHASE 1: Local Backend (jetzt)
terraform {
  backend "local" {
    path = "terraform.tfstate"
  }
}

# PHASE 2: Remote Backend (nach Bucket-Erstellung)
# terraform {
#   backend "s3" {
#     bucket                      = "voeb-terraform-state"
#     key                         = "prod/terraform.tfstate"
#     region                      = "eu01"
#     endpoints = {
#       s3 = "https://object.storage.eu01.onstackit.cloud"
#     }
#     skip_credentials_validation = true
#     skip_region_validation      = true
#     skip_s3_checksum            = true
#     skip_requesting_account_id  = true
#     skip_metadata_api_check     = true
#   }
# }
