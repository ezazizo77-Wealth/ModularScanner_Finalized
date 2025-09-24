#!/bin/bash
set -e

# Resolve script directory and cd there
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Use project-local paths
LOG_DIR="$DIR/logs"
mkdir -p "$LOG_DIR"

# Use the venv's python explicitly (no PATH issues under cron)
PY="$DIR/.venv/bin/python"

TS=$(date -u +"%Y%m%d-%H%M%S")
LOG_FILE="$LOG_DIR/run_cycle_$TS.log"

HB="$LOG_DIR/heartbeat.log"
touch "$HB"

NOW_UTC="$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "[CRON START] $NOW_UTC (ts=$TS)" | tee -a "$LOG_FILE"
echo "$NOW_UTC start ts=$TS" >> "$HB"

echo "=== Run started at $TS ===" | tee -a "$LOG_FILE"

echo ">>> Running fetch at $TS..." | tee -a "$LOG_FILE"
"$PY" "$DIR/fetch_ohlcv_to_parquet_v4.0.0.py" --top-n 0 | tee -a "$LOG_FILE"

echo ">>> Running health check at $TS..." | tee -a "$LOG_FILE"
"$PY" "$DIR/post_fetch_health_check.py" | tee -a "$LOG_FILE"

END_TS=$(date -u +"%Y%m%d-%H%M%S")
END_UTC="$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "=== Run completed at $END_TS ===" | tee -a "$LOG_FILE"
echo "$END_UTC done ts=$TS" >> "$HB"

ln -sf "$(basename "$LOG_FILE")" "$LOG_DIR/latest.log"