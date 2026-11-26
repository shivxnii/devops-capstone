#!/usr/bin/env bash
# Blue-Green cut-over: ./scripts/switch-color.sh green   (rollback: ./scripts/switch-color.sh blue)
set -euo pipefail
C=${1:?blue|green}
kubectl -n taskmanager patch svc taskmanager -p "{\"spec\":{\"selector\":{\"app\":\"taskmanager\",\"color\":\"$C\"}}}"
kubectl -n taskmanager get svc taskmanager -o jsonpath='{.spec.selector}{"\n"}'
