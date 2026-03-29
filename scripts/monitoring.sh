#!/usr/bin/env bash
# VÖB Chatbot — Monitoring Port-Forward
# Startet Grafana, Prometheus und AlertManager lokal.
# Beenden: Ctrl+C (alle Port-Forwards werden sauber gestoppt)
#
# Nutzung:
#   ./scripts/monitoring.sh          → PROD (Default)
#   ./scripts/monitoring.sh dev      → DEV
#   ./scripts/monitoring.sh prod     → PROD

set -euo pipefail

ENV="${1:-prod}"
PIDS=()

cleanup() {
    echo ""
    echo "Stoppe Port-Forwards..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    echo "Fertig."
    exit 0
}
trap cleanup INT TERM

case "$ENV" in
    dev)
        KUBECONFIG_FLAG=""
        NS="monitoring"
        echo "=== DEV Monitoring ==="
        echo ""

        echo "Grafana:      http://localhost:3001"
        kubectl port-forward -n "$NS" svc/monitoring-grafana 3001:80 &
        PIDS+=($!)

        echo "Prometheus:   http://localhost:9090"
        kubectl port-forward -n "$NS" svc/monitoring-kube-prometheus-prometheus 9090:9090 &
        PIDS+=($!)

        echo "AlertManager: http://localhost:9093"
        kubectl port-forward -n "$NS" svc/monitoring-kube-prometheus-alertmanager 9093:9093 &
        PIDS+=($!)
        ;;
    prod)
        KC="$HOME/.kube/config-prod"
        NS="monitoring"

        if [ ! -f "$KC" ]; then
            echo "FEHLER: $KC nicht gefunden."
            echo "Kubeconfig fuer PROD holen: stackit ske kubeconfig create vob-prod --login"
            exit 1
        fi

        echo "=== PROD Monitoring ==="
        echo ""

        echo "Grafana:      http://localhost:3001"
        kubectl --kubeconfig "$KC" port-forward -n "$NS" svc/monitoring-grafana 3001:80 &
        PIDS+=($!)

        echo "Prometheus:   http://localhost:9090"
        kubectl --kubeconfig "$KC" port-forward -n "$NS" svc/monitoring-kube-prometheus-prometheus 9090:9090 &
        PIDS+=($!)

        echo "AlertManager: http://localhost:9093"
        kubectl --kubeconfig "$KC" port-forward -n "$NS" svc/monitoring-kube-prometheus-alertmanager 9093:9093 &
        PIDS+=($!)
        ;;
    *)
        echo "Nutzung: $0 [dev|prod]"
        exit 1
        ;;
esac

echo ""
echo "Alle Services gestartet. Ctrl+C zum Beenden."
wait
