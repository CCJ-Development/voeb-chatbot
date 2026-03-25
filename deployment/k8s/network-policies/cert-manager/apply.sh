#!/bin/bash
# NetworkPolicy Apply — cert-manager Namespace
set -euo pipefail

NAMESPACE="cert-manager"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! kubectl get namespace "$NAMESPACE" &>/dev/null; then
  echo "ERROR: Namespace '$NAMESPACE' existiert nicht."
  exit 1
fi

echo "=== cert-manager NetworkPolicies anwenden (Namespace: $NAMESPACE) ==="

echo "[1/6] DNS Egress..."
kubectl apply -f "$SCRIPT_DIR/02-allow-dns-egress.yaml" -n "$NAMESPACE"

echo "[2/6] K8s API Egress..."
kubectl apply -f "$SCRIPT_DIR/03-allow-k8s-api-egress.yaml" -n "$NAMESPACE"

echo "[3/6] ACME + Cloudflare Egress..."
kubectl apply -f "$SCRIPT_DIR/04-allow-acme-egress.yaml" -n "$NAMESPACE"

echo "[4/6] Monitoring Scrape Ingress..."
kubectl apply -f "$SCRIPT_DIR/05-allow-monitoring-scrape-ingress.yaml" -n "$NAMESPACE"

echo "[5/6] Webhook Ingress..."
kubectl apply -f "$SCRIPT_DIR/06-allow-webhook-ingress.yaml" -n "$NAMESPACE"

echo "[6/6] Default-Deny (Zero-Trust Baseline)..."
kubectl apply -f "$SCRIPT_DIR/01-default-deny-all.yaml" -n "$NAMESPACE"

echo ""
echo "=== Fertig. kubectl get networkpolicies -n $NAMESPACE ==="
