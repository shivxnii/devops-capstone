#!/usr/bin/env bash
# Demonstrates scaling, rolling update, rollback. Usage: ./scripts/demo-k8s.sh <new-image>
set -euo pipefail
NS=taskmanager; D=taskmanager-blue; NEW=${1:-shivanii2507/taskmanager:1.0.1}
echo "== SCALE ==";   kubectl -n $NS scale deploy/$D --replicas=4; kubectl -n $NS rollout status deploy/$D; kubectl -n $NS get pods -l color=blue
echo "== ROLLING UPDATE =="; kubectl -n $NS set image deploy/$D app=$NEW; kubectl -n $NS rollout status deploy/$D
kubectl -n $NS rollout history deploy/$D
echo "== ROLLBACK ==";  kubectl -n $NS rollout undo deploy/$D; kubectl -n $NS rollout status deploy/$D
kubectl -n $NS scale deploy/$D --replicas=2
