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
echo "[1/5] DNS Egress..."
kubectl apply -f "$SCRIPT_DIR/02-allow-dns-egress.yaml" -n "$NAMESPACE" $DRY_RUN

echo "[2/5] Scrape Egress..."
kubectl apply -f "$SCRIPT_DIR/03-allow-scrape-egress.yaml" -n "$NAMESPACE" $DRY_RUN

echo "[3/5] Intra-Namespace..."
kubectl apply -f "$SCRIPT_DIR/04-allow-intra-namespace.yaml" -n "$NAMESPACE" $DRY_RUN

echo "[4/5] K8s API Egress..."
kubectl apply -f "$SCRIPT_DIR/05-allow-k8s-api-egress.yaml" -n "$NAMESPACE" $DRY_RUN

# 2. Default-Deny zuletzt
echo "[5/5] Default-Deny (Zero-Trust Baseline)..."
kubectl apply -f "$SCRIPT_DIR/01-default-deny-all.yaml" -n "$NAMESPACE" $DRY_RUN

echo ""
echo "=== App-Namespace Scrape-Policy anwenden ==="
echo "[+] onyx-dev..."
kubectl apply -f "$SCRIPT_DIR/../06-allow-monitoring-scrape.yaml" -n onyx-dev $DRY_RUN
echo "[+] onyx-test..."
kubectl apply -f "$SCRIPT_DIR/../06-allow-monitoring-scrape.yaml" -n onyx-test $DRY_RUN

echo ""
echo "=== Fertig. Policies pruefen: ==="
echo "  kubectl get networkpolicies -n $NAMESPACE"
echo "  kubectl get networkpolicies -n onyx-dev"
echo "  kubectl get networkpolicies -n onyx-test"
