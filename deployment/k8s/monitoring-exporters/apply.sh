#!/bin/bash
# ============================================================
# Monitoring Exporter Apply — postgres_exporter + redis_exporter
# ============================================================
# Voraussetzungen:
#   1. Secrets muessen bereits existieren (siehe unten)
#   2. NetworkPolicies muessen applied sein (monitoring/apply.sh)
#
# Secrets erstellen (einmalig):
#   PG_DEV_PW=$(kubectl get secret onyx-dbreadonly -n onyx-dev -o jsonpath='{.data.db_readonly_password}' | base64 -d)
#   PG_TEST_PW=$(kubectl get secret onyx-dbreadonly -n onyx-test -o jsonpath='{.data.db_readonly_password}' | base64 -d)
#   REDIS_DEV_PW=$(kubectl get secret onyx-redis -n onyx-dev -o jsonpath='{.data.redis_password}' | base64 -d)
#   REDIS_TEST_PW=$(kubectl get secret onyx-redis -n onyx-test -o jsonpath='{.data.redis_password}' | base64 -d)
#
#   echo -n "postgresql://db_readonly_user:${PG_DEV_PW}@be7fe911-4eac-4c9d-a7a8-6dfff674c41f.postgresql.eu01.onstackit.cloud:5432/onyx?sslmode=require" > /tmp/pg-dsn.txt
#   kubectl create secret generic pg-exporter-dev -n monitoring --from-file=DATA_SOURCE_NAME=/tmp/pg-dsn.txt
#   rm /tmp/pg-dsn.txt
#
#   echo -n "postgresql://db_readonly_user:${PG_TEST_PW}@d371f38d-2ad5-458c-af27-c84f3004f1ba.postgresql.eu01.onstackit.cloud:5432/onyx?sslmode=require" > /tmp/pg-dsn.txt
#   kubectl create secret generic pg-exporter-test -n monitoring --from-file=DATA_SOURCE_NAME=/tmp/pg-dsn.txt
#   rm /tmp/pg-dsn.txt
#
#   kubectl create secret generic redis-exporter-dev -n monitoring \
#     --from-file=REDIS_ADDR=<(echo -n "onyx-dev.onyx-dev.svc.cluster.local:6379") \
#     --from-file=REDIS_PASSWORD=<(echo -n "${REDIS_DEV_PW}")
#
#   kubectl create secret generic redis-exporter-test -n monitoring \
#     --from-file=REDIS_ADDR=<(echo -n "onyx-test.onyx-test.svc.cluster.local:6379") \
#     --from-file=REDIS_PASSWORD=<(echo -n "${REDIS_TEST_PW}")
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

# Pruefen ob Secrets existieren
echo "=== Secrets pruefen ==="
MISSING=0
for secret in pg-exporter-dev pg-exporter-test redis-exporter-dev redis-exporter-test; do
  if ! kubectl get secret "$secret" -n "$NAMESPACE" &>/dev/null; then
    echo "FEHLT: Secret '$secret' in $NAMESPACE — siehe Anleitung oben"
    MISSING=1
  else
    echo "  OK: $secret"
  fi
done

if [[ "$MISSING" -eq 1 && -z "$DRY_RUN" ]]; then
  echo ""
  echo "ERROR: Fehlende Secrets. Erstelle sie zuerst (siehe Anleitung im Script-Header)."
  exit 1
fi

echo ""
echo "=== Exporter Deployments + Services anwenden (Namespace: $NAMESPACE) ==="

echo "[1/4] postgres_exporter DEV..."
kubectl apply -f "$SCRIPT_DIR/pg-exporter-dev.yaml" $DRY_RUN

echo "[2/4] postgres_exporter TEST..."
kubectl apply -f "$SCRIPT_DIR/pg-exporter-test.yaml" $DRY_RUN

echo "[3/4] redis_exporter DEV..."
kubectl apply -f "$SCRIPT_DIR/redis-exporter-dev.yaml" $DRY_RUN

echo "[4/4] redis_exporter TEST..."
kubectl apply -f "$SCRIPT_DIR/redis-exporter-test.yaml" $DRY_RUN

echo ""
echo "=== Fertig. Status pruefen: ==="
echo "  kubectl get pods -n $NAMESPACE -l 'app in (postgres-exporter,redis-exporter)'"
echo "  kubectl get svc -n $NAMESPACE -l 'app in (postgres-exporter,redis-exporter)'"
