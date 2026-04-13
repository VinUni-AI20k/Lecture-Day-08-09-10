#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./run_tuning_experiments.sh
#   AIP_ENV=aip ./run_tuning_experiments.sh

AIP_ENV="${AIP_ENV:-aip}"
REBUILD_INDEX="${REBUILD_INDEX:-0}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_TS="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/run_tuning_${RUN_TS}.log"

cd "$SCRIPT_DIR"
mkdir -p "$LOG_DIR"
echo "[runner] Working dir: $SCRIPT_DIR"
echo "[runner] Conda env: $AIP_ENV"
echo "[runner] REBUILD_INDEX: $REBUILD_INDEX"
echo "[runner] Log file: $LOG_FILE"

REBUILD_INDEX="$REBUILD_INDEX" PYTHONUNBUFFERED=1 conda run --no-capture-output -n "$AIP_ENV" python -u run_tuning_experiments.py 2>&1 | tee "$LOG_FILE"
