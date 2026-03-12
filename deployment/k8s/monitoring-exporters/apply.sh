#!/bin/bash
# ============================================================
# Monitoring Exporter Apply — postgres_exporter + redis_exporter
# ============================================================
# Voraussetzungen:
#   1. Secrets muessen bereits existieren (siehe unten)
#   2. NetworkPolicies muessen applied sein (monitoring/apply.sh)
#
# Usage:
#   ./apply.sh              # Erkennt automatisch welche Environments verfuegbar sind
#   ./apply.sh --dry-run    # Nur anzeigen, nichts anwenden
#
# Secrets erstellen (einmalig pro Environment):
#
#   # --- DEV ---
#   PG_DEV_PW=$(kubectl get secret onyx-dbreadonly -n onyx-dev -o jsonpath='{.data.db_readonly_password}' | base64 -d)
#   echo -n "postgresql://db_readonly_user:${PG_DEV_PW}@be7fe911-4eac-4c9d-a7a8-6dfff674c41f.postgresql.eu01.onstackit.cloud:5432/onyx?sslmode=require" > /tmp/pg-dsn.txt
#   kubectl create secret generic pg-exporter-dev -n monitoring --from-file=DATA_SOURCE_NAME=/tmp/pg-dsn.txt
#   rm /tmp/pg-dsn.txt
#   REDIS_DEV_PW=$(kubectl get secret onyx-redis -n onyx-dev -o jsonpath='{.data.redis_password}' | base64 -d)
#   kubectl create secret generic redis-exporter-dev -n monitoring \
#     --from-file=REDIS_ADDR=<(echo -n "onyx-dev.onyx-dev.svc.cluster.local:6379") \
#     --from-file=REDIS_PASSWORD=<(echo -n "${REDIS_DEV_PW}")
#
#   # --- TEST ---
#   PG_TEST_PW=$(kubectl get secret onyx-dbreadonly -n onyx-test -o jsonpath='{.data.db_readonly_password}' | base64 -d)
#   echo -n "postgresql://db_readonly_user:${PG_TEST_PW}@d371f38d-2ad5-458c-af27-c84f3004f1ba.postgresql.eu01.onstackit.cloud:5432/onyx?sslmode=require" > /tmp/pg-dsn.txt
#   kubectl create secret generic pg-exporter-test -n monitoring --from-file=DATA_SOURCE_NAME=/tmp/pg-dsn.txt
#   rm /tmp/pg-dsn.txt
#   REDIS_TEST_PW=$(kubectl get secret onyx-redis -n onyx-test -o jsonpath='{.data.redis_password}' | base64 -d)
#   kubectl create secret generic redis-exporter-test -n monitoring \
#     --from-file=REDIS_ADDR=<(echo -n "onyx-test.onyx-test.svc.cluster.local:6379") \
#     --from-file=REDIS_PASSWORD=<(echo -n "${REDIS_TEST_PW}")
#
#   # --- PROD (eigener Cluster: vob-prod) ---
#   PG_PROD_PW=$(kubectl get secret onyx-dbreadonly -n onyx-prod -o jsonpath='{.data.db_readonly_password}' | base64 -d)
#   echo -n "postgresql://db_readonly_user:${PG_PROD_PW}@fdc7610c-91dc-4d0a-9652-adafe1a509cd.postgresql.eu01.onstackit.cloud:5432/onyx?sslmode=require" > /tmp/pg-dsn.txt
#   kubectl create secret generic pg-exporter-prod -n monitoring --from-file=DATA_SOURCE_NAME=/tmp/pg-dsn.txt
#   rm /tmp/pg-dsn.txt
#   REDIS_PROD_PW=$(kubectl get secret onyx-redis -n onyx-prod -o jsonpath='{.data.redis_password}' | base64 -d)
#   kubectl create secret generic redis-exporter-prod -n monitoring \
#     --from-file=REDIS_ADDR=<(echo -n "onyx-prod.onyx-prod.svc.cluster.local:6379") \
#     --from-file=REDIS_PASSWORD=<(echo -n "${REDIS_PROD_PW}")
#
# Konzept: docs/technisches-feinkonzept/monitoring-exporter.md
# ============================================================

set -euo pipefail

NAMESPACE="monitoring"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRY_RUN=""

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN="--dry-run=client"
  echo "=== DRY-RUN Modus ==="
fi

# Auto-Detect: Welche Environments sind auf diesem Cluster verfuegbar?
ENVS=()
for env in dev test prod; do
  if kubectl get namespace "onyx-${env}" &>/dev/null; then
    ENVS+=("$env")
  fi
done

if [[ ${#ENVS[@]} -eq 0 ]]; then
  echo "ERROR: Keine onyx-* Namespaces gefunden. Falscher Kubeconfig-Kontext?"
  exit 1
fi

echo "=== Erkannte Environments: ${ENVS[*]} ==="

# Namespace monitoring muss existieren
if ! kubectl get namespace "$NAMESPACE" &>/dev/null; then
  echo "ERROR: Namespace '$NAMESPACE' existiert nicht."
  echo "Erstelle ihn mit: helm install monitoring prometheus-community/kube-prometheus-stack ..."
  exit 1
fi

# Secrets pruefen
echo ""
echo "=== Secrets pruefen ==="
MISSING=0
for env in "${ENVS[@]}"; do
  for type in pg-exporter redis-exporter; do
    secret="${type}-${env}"
    if ! kubectl get secret "$secret" -n "$NAMESPACE" &>/dev/null; then
      echo "  FEHLT: Secret '$secret' in $NAMESPACE — siehe Anleitung im Script-Header"
      MISSING=1
    else
      echo "  OK: $secret"
    fi
  done
done

if [[ "$MISSING" -eq 1 && -z "$DRY_RUN" ]]; then
  echo ""
  echo "ERROR: Fehlende Secrets. Erstelle sie zuerst (siehe Anleitung im Script-Header)."
  exit 1
fi

# Exporter deployen
TOTAL=$(( ${#ENVS[@]} * 2 ))
STEP=0

echo ""
echo "=== Exporter Deployments + Services anwenden (Namespace: $NAMESPACE) ==="

for env in "${ENVS[@]}"; do
  STEP=$((STEP + 1))
  echo "[${STEP}/${TOTAL}] postgres_exporter ${env^^}..."
  kubectl apply -f "$SCRIPT_DIR/pg-exporter-${env}.yaml" $DRY_RUN

  STEP=$((STEP + 1))
  echo "[${STEP}/${TOTAL}] redis_exporter ${env^^}..."
  kubectl apply -f "$SCRIPT_DIR/redis-exporter-${env}.yaml" $DRY_RUN
done

echo ""
echo "=== Fertig. Status pruefen: ==="
echo "  kubectl get pods -n $NAMESPACE -l 'app in (postgres-exporter,redis-exporter)'"
echo "  kubectl get svc -n $NAMESPACE -l 'app in (postgres-exporter,redis-exporter)'"
