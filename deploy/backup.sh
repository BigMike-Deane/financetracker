#!/bin/bash
# Finance Tracker - Database Backup Script
# Run this periodically to backup your financial data
#
# Setup automated backups (optional):
#   crontab -e
#   0 2 * * * /root/finance-tracker/deploy/backup.sh

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-$HOME/finance-tracker-backups}"
DATA_DIR="${DATA_DIR:-$HOME/finance-tracker/data}"
KEEP_DAYS=30  # Keep backups for 30 days

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate backup filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/finance-db-$TIMESTAMP.db"

# Copy database
echo "Backing up database..."
cp "$DATA_DIR/finance.db" "$BACKUP_FILE"

# Compress backup
gzip "$BACKUP_FILE"
BACKUP_FILE="$BACKUP_FILE.gz"

echo "Backup created: $BACKUP_FILE"

# Clean up old backups
echo "Cleaning up backups older than $KEEP_DAYS days..."
find "$BACKUP_DIR" -name "finance-db-*.db.gz" -mtime +$KEEP_DAYS -delete

# Show backup status
echo ""
echo "Current backups:"
ls -lh "$BACKUP_DIR"/*.gz 2>/dev/null || echo "No backups found"

echo ""
echo "Backup complete!"
