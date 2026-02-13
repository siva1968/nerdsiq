#!/bin/bash
# PostgreSQL Backup Script for Danswer
# Place in danswer-poc directory and make executable: chmod +x backup-script.sh

set -e

BACKUP_DIR="/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/danswer_backup_$TIMESTAMP.sql"
DAYS_TO_KEEP=7

echo "Starting backup at $(date)"

# Create backup
pg_dump -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

echo "Backup completed: ${BACKUP_FILE}.gz"

# Delete old backups (keep last 7 days)
find $BACKUP_DIR -name "danswer_backup_*.sql.gz" -mtime +$DAYS_TO_KEEP -delete

echo "Old backups cleaned up"

# Optional: Upload to cloud storage
# rclone copy ${BACKUP_FILE}.gz remote:backups/

echo "Backup process finished at $(date)"
