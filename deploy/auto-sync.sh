#!/bin/bash
# Finance Tracker - Automated Sync Script
# Runs SimpleFIN sync for all institutions
# Add to crontab: 0 */4 * * * /root/finance-tracker/deploy/auto-sync.sh >> /var/log/finance-sync.log 2>&1

set -e

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"

echo "$LOG_PREFIX Starting automated sync..."

# Get all institutions and sync each one
INSTITUTIONS=$(curl -s "$API_URL/api/institutions" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for inst in data:
    if inst.get('simplefin_access_url'):
        print(inst['id'])
")

if [ -z "$INSTITUTIONS" ]; then
    echo "$LOG_PREFIX No institutions with SimpleFIN configured"
    exit 0
fi

SYNC_COUNT=0
for INST_ID in $INSTITUTIONS; do
    echo "$LOG_PREFIX Syncing institution $INST_ID..."
    RESULT=$(curl -s -X POST "$API_URL/api/sync/$INST_ID")

    # Check for errors
    if echo "$RESULT" | grep -q '"error"'; then
        echo "$LOG_PREFIX ERROR syncing institution $INST_ID: $RESULT"
    else
        SYNC_COUNT=$((SYNC_COUNT + 1))
        # Extract transaction count if available
        TXN_COUNT=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('new_transactions', 0))" 2>/dev/null || echo "?")
        echo "$LOG_PREFIX Institution $INST_ID synced. New transactions: $TXN_COUNT"
    fi
done

echo "$LOG_PREFIX Automated sync complete. Synced $SYNC_COUNT institution(s)."
