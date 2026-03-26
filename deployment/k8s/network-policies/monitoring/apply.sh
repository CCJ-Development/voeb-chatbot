#!/bin/bash
# ============================================================
# NetworkPolicy Apply — Monitoring Namespace
# ============================================================
# Wendet alle Monitoring-NetworkPolicies in sicherer Reihenfolge an:
# 1. Allow-Policies zuerst (damit nichts kaputt geht)
# 2. Default-Deny zuletzt (Zero-Trust-Baseline)
#
# Usage:
#   ./apply.sh
#   ./apply.sh --dry-run
#
# Referenz: docs/referenz/monitoring-konzept.md
# ============================================================

set -euo pipefail

NAMESPACE="monitoring"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRY_RUN=""

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN="--dry-run=client"
  echo "=== DRY-RUN Modus ==="
fi

# Pruefen ob Namespace existiert
if ! kubectl get namespace "$NAMESPACE" &>/dev/null; then
  echo "ERROR: Namespace '$NAMESPACE' existiert nicht."
  echo "Erstelle ihn mit: kubectl create namespace $NAMESPACE"
  exit 1
fi

echo "=== Monitoring NetworkPolicies anwenden (Namespace: $NAMESPACE) ==="

# 1. Allow-Policies zuerst
echo "[1/14] DNS Egress..."
kubectl apply -f "$SCRIPT_DIR/02-allow-dns-egress.yaml" -n "$NAMESPACE" $DRY_RUN

echo "[2/14] Scrape Egress..."
kubectl apply -f "$SCRIPT_DIR/03-allow-scrape-egress.yaml" -n "$NAMESPACE" $DRY_RUN

echo "[3/14] Intra-Namespace..."
kubectl apply -f "$SCRIPT_DIR/04-allow-intra-namespace.yaml" -n "$NAMESPACE" $DRY_RUN

echo "[4/14] K8s API Egress..."
kubectl apply -f "$SCRIPT_DIR/05-allow-k8s-api-egress.yaml" -n "$NAMESPACE" $DRY_RUN

echo "[5/14] PG Exporter Egress (Port 5432)..."
kubectl apply -f "$SCRIPT_DIR/06-allow-pg-exporter-egress.yaml" -n "$NAMESPACE" $DRY_RUN

echo "[6/14] Redis Exporter Egress (Port 6379)..."
kubectl apply -f "$SCRIPT_DIR/07-allow-redis-exporter-egress.yaml" -n "$NAMESPACE" $DRY_RUN

echo "[7/14] AlertManager Webhook Egress (Port 443)..."
kubectl apply -f "$SCRIPT_DIR/08-allow-alertmanager-webhook-egress.yaml" -n "$NAMESPACE" $DRY_RUN

echo "[8/14] Backup-Check Egress (Port 443)..."
kubectl apply -f "$SCRIPT_DIR/09-allow-backup-check-egress.yaml" -n "$NAMESPACE" $DRY_RUN

echo "[9/14] Blackbox Exporter Egress (Port 443)..."
kubectl apply -f "$SCRIPT_DIR/10-allow-blackbox-egress.yaml" -n "$NAMESPACE" $DRY_RUN

echo "[10/14] OpenSearch Exporter Egress (Port 9200)..."
kubectl apply -f "$SCRIPT_DIR/11-allow-opensearch-exporter-egress.yaml" -n "$NAMESPACE" $DRY_RUN

echo "[11/14] Loki Ingress (Port 3100)..."
kubectl apply -f "$SCRIPT_DIR/12-allow-loki-ingress.yaml" -n "$NAMESPACE" $DRY_RUN

echo "[12/14] Promtail Egress (Port 3100 + K8s API)..."
kubectl apply -f "$SCRIPT_DIR/13-allow-promtail-egress.yaml" -n "$NAMESPACE" $DRY_RUN

echo "[13/14] Grafana PG Egress (Port 5432, ext-analytics)..."
kubectl apply -f "$SCRIPT_DIR/14-allow-grafana-pg-egress.yaml" -n "$NAMESPACE" $DRY_RUN

# 2. Default-Deny zuletzt
echo "[14/14] Default-Deny (Zero-Trust Baseline)..."
kubectl apply -f "$SCRIPT_DIR/01-default-deny-all.yaml" -n "$NAMESPACE" $DRY_RUN

echo ""
echo "=== App-Namespace Policies anwenden ==="
for APP_NS in onyx-dev onyx-test onyx-prod; do
  if kubectl get namespace "$APP_NS" &>/dev/null; then
    echo "[+] ${APP_NS}: Monitoring Scrape..."
    kubectl apply -f "$SCRIPT_DIR/../06-allow-monitoring-scrape.yaml" -n "$APP_NS" $DRY_RUN
    echo "[+] ${APP_NS}: Redis Exporter Ingress..."
    kubectl apply -f "$SCRIPT_DIR/../07-allow-redis-exporter-ingress.yaml" -n "$APP_NS" $DRY_RUN
    echo "[+] ${APP_NS}: OpenSearch Exporter Ingress..."
    kubectl apply -f "$SCRIPT_DIR/../08-allow-opensearch-exporter-ingress.yaml" -n "$APP_NS" $DRY_RUN
  else
    echo "[-] ${APP_NS}: Namespace existiert nicht, ueberspringe."
  fi
done

echo ""
echo "=== Fertig. Policies pruefen: ==="
echo "  kubectl get networkpolicies -n $NAMESPACE"
echo "  kubectl get networkpolicies -n onyx-dev"
echo "  kubectl get networkpolicies -n onyx-test"
echo "  kubectl get networkpolicies -n onyx-prod"
