#!/bin/bash
# ===========================================================
# TEST Scale-to-Zero: RBAC + CronJobs anwenden
# ===========================================================
# Spart ~130-200 EUR/Mo durch Abschalten von TEST ausserhalb
# der Arbeitszeiten (Mo-Fr 08:00-18:00 UTC).
#
# Voraussetzung:
#   - kubectl Kontext zeigt auf DEV+TEST Cluster (vob-chatbot)
#   - Namespace onyx-test existiert
#
# Usage:
#   bash deployment/k8s/cost-optimization/apply.sh
#   bash deployment/k8s/cost-optimization/apply.sh --delete  # Entfernen
# ===========================================================

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAMESPACE="onyx-test"

# Pruefen ob Namespace existiert
if ! kubectl get namespace "$NAMESPACE" &>/dev/null; then
  echo "ERROR: Namespace $NAMESPACE nicht gefunden. Ist der richtige Kontext aktiv?"
  echo "  kubectl config current-context"
  exit 1
fi

if [ "${1:-}" = "--delete" ]; then
  echo "Entferne Scale-to-Zero CronJobs..."
  kubectl delete -f "$SCRIPT_DIR/test-scale-up.yaml" --ignore-not-found
  kubectl delete -f "$SCRIPT_DIR/test-scale-down.yaml" --ignore-not-found
  kubectl delete -f "$SCRIPT_DIR/rbac.yaml" --ignore-not-found
  echo "Done. TEST laeuft jetzt wieder 24/7."
  exit 0
fi

echo "=== TEST Scale-to-Zero Setup ==="
echo "Namespace: $NAMESPACE"
echo "Schedule:  Mo-Fr 08:00 UTC Scale-Up, 18:00 UTC Scale-Down"
echo "Wochenende: TEST bleibt bei 0 Replicas"
echo ""

echo "Step 1/3: RBAC (ServiceAccount + Role + RoleBinding)"
kubectl apply -f "$SCRIPT_DIR/rbac.yaml"

echo "Step 2/3: Scale-Down CronJob (Mo-Fr 18:00 UTC)"
kubectl apply -f "$SCRIPT_DIR/test-scale-down.yaml"

echo "Step 3/3: Scale-Up CronJob (Mo-Fr 08:00 UTC)"
kubectl apply -f "$SCRIPT_DIR/test-scale-up.yaml"

echo ""
echo "=== Verifizierung ==="
kubectl get cronjobs -n "$NAMESPACE" -o wide
echo ""
echo "Manuell testen:"
echo "  kubectl create job --from=cronjob/test-scale-down test-scale-down-manual -n $NAMESPACE"
echo "  kubectl create job --from=cronjob/test-scale-up test-scale-up-manual -n $NAMESPACE"
echo ""
echo "Entfernen:"
echo "  bash $0 --delete"
