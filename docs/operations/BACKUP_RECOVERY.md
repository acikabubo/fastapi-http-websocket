# Backup and Recovery Guide

This guide covers comprehensive backup strategies, disaster recovery procedures, and data protection for the FastAPI HTTP/WebSocket application.

## Table of Contents

- [Backup Strategy Overview](#backup-strategy-overview)
- [Database Backups](#database-backups)
- [Redis Backups](#redis-backups)
- [Configuration Backups](#configuration-backups)
- [Volume Backups](#volume-backups)
- [Automated Backup Scripts](#automated-backup-scripts)
- [Backup Verification](#backup-verification)
- [Disaster Recovery](#disaster-recovery)
- [Point-in-Time Recovery](#point-in-time-recovery)
- [Testing Recovery Procedures](#testing-recovery-procedures)

## Backup Strategy Overview

### Backup Types

| Component | Backup Type | Frequency | Retention | Priority |
|-----------|-------------|-----------|-----------|----------|
| **PostgreSQL Database** | Full + WAL | Full: Daily<br>WAL: Continuous | 30 days full<br>7 days WAL | Critical |
| **Redis Data** | Snapshot + AOF | Snapshot: Hourly<br>AOF: Continuous | 7 days | High |
| **Configuration Files** | Full copy | On change + Daily | 30 days | High |
| **Docker Volumes** | Tarball | Weekly | 4 weeks | Medium |
| **Keycloak Database** | Full dump | Daily | 30 days | Critical |
| **Application Logs** | Archive | Daily | 90 days | Medium |

### Backup Locations

**Primary Backup Storage:**
- Local: `/backups` directory (bind-mounted volume)
- Network: NFS/CIFS share for immediate access

**Secondary Backup Storage:**
- Cloud: S3-compatible storage (AWS S3, MinIO, etc.)
- Offsite: Remote backup server via rsync/restic

### RTO and RPO Targets

- **RTO (Recovery Time Objective)**: 1 hour
- **RPO (Recovery Point Objective)**: 15 minutes
- **Database corruption detection**: Within 6 hours
- **Backup restoration testing**: Monthly

## Database Backups

### PostgreSQL Backup Methods

#### 1. Logical Backups with pg_dump

**Full Database Backup:**

```bash
#!/bin/bash
# scripts/backup_db.sh

BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="fastapi_prod"
DB_USER="prod_user"

mkdir -p "$BACKUP_DIR"

# Create backup
docker exec hw-db pg_dump -U "$DB_USER" -Fc "$DB_NAME" > \
  "$BACKUP_DIR/${DB_NAME}_${DATE}.dump"

# Compress backup
gzip "$BACKUP_DIR/${DB_NAME}_${DATE}.dump"

# Create metadata
cat > "$BACKUP_DIR/${DB_NAME}_${DATE}.meta" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "database": "$DB_NAME",
  "size": "$(du -h "$BACKUP_DIR/${DB_NAME}_${DATE}.dump.gz" | cut -f1)",
  "pg_version": "$(docker exec hw-db psql -U postgres -t -c 'SELECT version();' | head -1)"
}
EOF

echo "Backup completed: ${DB_NAME}_${DATE}.dump.gz"

# Remove backups older than 30 days
find "$BACKUP_DIR" -name "*.dump.gz" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.meta" -mtime +30 -delete
```

**Per-Table Backup:**

```bash
# Backup specific table (useful for large tables)
docker exec hw-db pg_dump -U prod_user -Fc -t author fastapi_prod > \
  /backups/postgres/author_$(date +%Y%m%d).dump
```

**Schema-Only Backup:**

```bash
# Backup schema without data (useful for migrations)
docker exec hw-db pg_dump -U prod_user -Fc --schema-only fastapi_prod > \
  /backups/postgres/schema_$(date +%Y%m%d).dump
```

#### 2. Physical Backups with pg_basebackup

**Base Backup:**

```bash
#!/bin/bash
# scripts/backup_db_physical.sh

BACKUP_DIR="/backups/postgres/base"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Create base backup
docker exec hw-db pg_basebackup -U postgres -D - -Ft -z -X fetch | \
  tar -xzf - -C "$BACKUP_DIR/${DATE}"

echo "Base backup completed: $BACKUP_DIR/${DATE}"
```

**Enable WAL Archiving:**

```bash
# docker/postgres/postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'test ! -f /backups/postgres/wal/%f && cp %p /backups/postgres/wal/%f'
max_wal_senders = 3
```

#### 3. Continuous WAL Archiving

**Setup:**

```yaml
# docker-compose.yml
services:
  hw-db:
    volumes:
      - ./backups/postgres/wal:/backups/postgres/wal
      - ./docker/postgres/postgresql.conf:/etc/postgresql/postgresql.conf
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
```

**Archive WAL Files:**

```bash
#!/bin/bash
# scripts/archive_wal.sh

WAL_DIR="/backups/postgres/wal"
ARCHIVE_DIR="/backups/postgres/wal_archive"
DATE=$(date +%Y%m%d)

# Move old WAL files to archive
find "$WAL_DIR" -name "*.wal" -mtime +1 -exec mv {} "$ARCHIVE_DIR/${DATE}/" \;

# Compress archived WAL files
find "$ARCHIVE_DIR" -name "*.wal" ! -name "*.gz" -exec gzip {} \;

# Remove archives older than 7 days
find "$ARCHIVE_DIR" -type d -mtime +7 -exec rm -rf {} \;
```

### Restore PostgreSQL Database

#### From pg_dump Backup

**Complete Restore:**

```bash
#!/bin/bash
# scripts/restore_db.sh

BACKUP_FILE="$1"
DB_NAME="fastapi_prod"
DB_USER="prod_user"

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <backup_file.dump.gz>"
  exit 1
fi

echo "WARNING: This will DROP and recreate the database!"
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
  echo "Restore cancelled"
  exit 0
fi

# Stop application
docker-compose stop hw-server

# Uncompress if needed
if [[ $BACKUP_FILE == *.gz ]]; then
  gunzip -c "$BACKUP_FILE" > "${BACKUP_FILE%.gz}"
  BACKUP_FILE="${BACKUP_FILE%.gz}"
fi

# Drop existing connections
docker exec hw-db psql -U postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$DB_NAME';"

# Drop and recreate database
docker exec hw-db psql -U postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
docker exec hw-db psql -U postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

# Restore backup
docker exec -i hw-db pg_restore -U "$DB_USER" -d "$DB_NAME" -Fc < "$BACKUP_FILE"

echo "Database restored successfully"

# Restart application
docker-compose start hw-server
```

#### Point-in-Time Recovery (PITR) with WAL

```bash
#!/bin/bash
# scripts/pitr_restore.sh

BASE_BACKUP="/backups/postgres/base/20250118_120000"
WAL_ARCHIVE="/backups/postgres/wal_archive"
TARGET_TIME="2025-01-18 14:30:00"

# Stop database
docker-compose stop hw-db

# Remove current data
docker volume rm postgres-hw-data
docker volume create postgres-hw-data

# Restore base backup
docker run --rm \
  -v postgres-hw-data:/var/lib/postgresql/data \
  -v "$BASE_BACKUP:/backup" \
  postgres:13 \
  bash -c "cp -r /backup/* /var/lib/postgresql/data/"

# Create recovery.conf
cat > recovery.conf <<EOF
restore_command = 'cp $WAL_ARCHIVE/%f %p'
recovery_target_time = '$TARGET_TIME'
recovery_target_action = 'promote'
EOF

# Copy recovery.conf to data directory
docker run --rm \
  -v postgres-hw-data:/var/lib/postgresql/data \
  -v "$(pwd)/recovery.conf:/recovery.conf" \
  postgres:13 \
  bash -c "cp /recovery.conf /var/lib/postgresql/data/"

# Start database
docker-compose start hw-db

echo "Point-in-time recovery to $TARGET_TIME initiated"
```

### Keycloak Database Backup

```bash
#!/bin/bash
# scripts/backup_keycloak.sh

BACKUP_DIR="/backups/keycloak"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="keycloak_prod"
DB_USER="prod_user"

mkdir -p "$BACKUP_DIR"

# Backup Keycloak database
docker exec hw-db pg_dump -U "$DB_USER" -Fc "$DB_NAME" > \
  "$BACKUP_DIR/${DB_NAME}_${DATE}.dump"

gzip "$BACKUP_DIR/${DB_NAME}_${DATE}.dump"

echo "Keycloak database backed up: ${DB_NAME}_${DATE}.dump.gz"

# Export realm configuration
docker exec hw-keycloak /opt/keycloak/bin/kc.sh export \
  --dir /tmp/export \
  --realm production

docker cp hw-keycloak:/tmp/export "$BACKUP_DIR/realm_export_${DATE}"

echo "Keycloak realm exported: realm_export_${DATE}"
```

## Redis Backups

### Redis Backup Methods

#### 1. RDB Snapshots

**Manual Snapshot:**

```bash
# Trigger immediate snapshot
docker exec hw-redis redis-cli BGSAVE

# Wait for completion
docker exec hw-redis redis-cli LASTSAVE

# Copy snapshot
docker cp hw-redis:/data/dump.rdb /backups/redis/dump_$(date +%Y%m%d_%H%M%S).rdb
```

**Automated Snapshots:**

```bash
#!/bin/bash
# scripts/backup_redis.sh

BACKUP_DIR="/backups/redis"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Trigger snapshot
docker exec hw-redis redis-cli BGSAVE

# Wait for completion (check every second)
while [ "$(docker exec hw-redis redis-cli LASTSAVE)" == "$LAST_SAVE" ]; do
  sleep 1
done

# Copy snapshot
docker cp hw-redis:/data/dump.rdb "$BACKUP_DIR/dump_${DATE}.rdb"

echo "Redis snapshot created: dump_${DATE}.rdb"

# Remove snapshots older than 7 days
find "$BACKUP_DIR" -name "dump_*.rdb" -mtime +7 -delete
```

#### 2. AOF (Append-Only File) Backups

**Enable AOF:**

```conf
# docker/redis/redis.conf
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
```

**Backup AOF:**

```bash
# Copy AOF file
docker cp hw-redis:/data/appendonly.aof /backups/redis/appendonly_$(date +%Y%m%d_%H%M%S).aof
```

### Restore Redis Data

**From RDB Snapshot:**

```bash
#!/bin/bash
# scripts/restore_redis.sh

BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <backup_file.rdb>"
  exit 1
fi

# Stop Redis
docker-compose stop hw-redis

# Copy backup to data directory
docker cp "$BACKUP_FILE" hw-redis:/data/dump.rdb

# Start Redis
docker-compose start hw-redis

echo "Redis restored from $BACKUP_FILE"
```

**From AOF:**

```bash
# Stop Redis
docker-compose stop hw-redis

# Copy AOF file
docker cp appendonly_backup.aof hw-redis:/data/appendonly.aof

# Start Redis (will replay AOF)
docker-compose start hw-redis
```

## Configuration Backups

### Backup Configuration Files

```bash
#!/bin/bash
# scripts/backup_config.sh

BACKUP_DIR="/backups/config"
DATE=$(date +%Y%m%d_%H%M%S)
PROJECT_DIR="/app"

mkdir -p "$BACKUP_DIR"

# Create tarball of configuration files
tar -czf "$BACKUP_DIR/config_${DATE}.tar.gz" \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='.git' \
  "$PROJECT_DIR/.env.production" \
  "$PROJECT_DIR/docker/.srv_env" \
  "$PROJECT_DIR/docker/.pg_env.production" \
  "$PROJECT_DIR/docker/.kc_env.production" \
  "$PROJECT_DIR/docker/docker-compose.yml" \
  "$PROJECT_DIR/docker/traefik/" \
  "$PROJECT_DIR/docker/prometheus/" \
  "$PROJECT_DIR/docker/grafana/" \
  "$PROJECT_DIR/docker/loki/" \
  "$PROJECT_DIR/actions.json" \
  "$PROJECT_DIR/uvicorn_logging.json"

echo "Configuration backed up: config_${DATE}.tar.gz"

# Remove backups older than 30 days
find "$BACKUP_DIR" -name "config_*.tar.gz" -mtime +30 -delete
```

### Restore Configuration

```bash
#!/bin/bash
# scripts/restore_config.sh

BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <config_backup.tar.gz>"
  exit 1
fi

# Extract configuration
tar -xzf "$BACKUP_FILE" -C /

echo "Configuration restored from $BACKUP_FILE"
echo "Review configuration files before restarting services!"
```

## Volume Backups

### Backup Docker Volumes

```bash
#!/bin/bash
# scripts/backup_volumes.sh

BACKUP_DIR="/backups/volumes"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup each volume
for VOLUME in postgres-hw-data redis-hw-data grafana-data prometheus-data loki-data; do
  echo "Backing up volume: $VOLUME"

  docker run --rm \
    -v "$VOLUME:/data" \
    -v "$BACKUP_DIR:/backup" \
    alpine \
    tar czf "/backup/${VOLUME}_${DATE}.tar.gz" -C /data .

  echo "Volume backed up: ${VOLUME}_${DATE}.tar.gz"
done

# Remove backups older than 4 weeks
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +28 -delete
```

### Restore Docker Volumes

```bash
#!/bin/bash
# scripts/restore_volume.sh

VOLUME_NAME="$1"
BACKUP_FILE="$2"

if [ -z "$VOLUME_NAME" ] || [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <volume_name> <backup_file.tar.gz>"
  exit 1
fi

echo "WARNING: This will replace all data in volume $VOLUME_NAME!"
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
  echo "Restore cancelled"
  exit 0
fi

# Stop services using the volume
docker-compose stop

# Remove existing volume
docker volume rm "$VOLUME_NAME"

# Create new volume
docker volume create "$VOLUME_NAME"

# Restore data
docker run --rm \
  -v "$VOLUME_NAME:/data" \
  -v "$(dirname "$BACKUP_FILE"):/backup" \
  alpine \
  tar xzf "/backup/$(basename "$BACKUP_FILE")" -C /data

echo "Volume restored: $VOLUME_NAME"

# Restart services
docker-compose up -d
```

## Automated Backup Scripts

### Comprehensive Backup Script

```bash
#!/bin/bash
# scripts/backup_all.sh

set -e

BACKUP_ROOT="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$BACKUP_ROOT/backup_${DATE}.log"

# Function to log messages
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to handle errors
error_exit() {
  log "ERROR: $1"
  exit 1
}

log "Starting comprehensive backup"

# 1. Backup PostgreSQL
log "Backing up PostgreSQL database..."
bash /scripts/backup_db.sh || error_exit "PostgreSQL backup failed"

# 2. Backup Keycloak
log "Backing up Keycloak..."
bash /scripts/backup_keycloak.sh || error_exit "Keycloak backup failed"

# 3. Backup Redis
log "Backing up Redis..."
bash /scripts/backup_redis.sh || error_exit "Redis backup failed"

# 4. Backup configuration
log "Backing up configuration files..."
bash /scripts/backup_config.sh || error_exit "Configuration backup failed"

# 5. Backup volumes (weekly only)
if [ "$(date +%u)" -eq 7 ]; then
  log "Backing up Docker volumes (weekly)..."
  bash /scripts/backup_volumes.sh || error_exit "Volume backup failed"
fi

# 6. Upload to remote storage
log "Uploading backups to remote storage..."
bash /scripts/upload_backups.sh "$DATE" || log "WARNING: Remote upload failed"

# 7. Verify backups
log "Verifying backups..."
bash /scripts/verify_backups.sh "$DATE" || log "WARNING: Backup verification failed"

# 8. Send notification
log "Sending backup notification..."
curl -X POST "https://api.slack.com/webhooks/your-webhook" \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"Backup completed successfully: $DATE\"}" || log "WARNING: Notification failed"

log "Comprehensive backup completed successfully"
```

### Cron Schedule

```bash
# /etc/cron.d/backups

# Full backup daily at 2 AM
0 2 * * * root /scripts/backup_all.sh >> /backups/cron.log 2>&1

# Redis snapshots every hour
0 * * * * root /scripts/backup_redis.sh >> /backups/redis_cron.log 2>&1

# Configuration backup on changes (use inotify-tools)
# @reboot root /scripts/watch_config_changes.sh >> /backups/config_watch.log 2>&1
```

### Upload Backups to S3

```bash
#!/bin/bash
# scripts/upload_backups.sh

DATE="$1"
BACKUP_DIR="/backups"
S3_BUCKET="s3://my-backups/fastapi-prod"

# Requires AWS CLI configured
# apt-get install awscli
# aws configure

# Upload database backups
aws s3 sync "$BACKUP_DIR/postgres/" "$S3_BUCKET/postgres/" \
  --exclude "*" \
  --include "*${DATE}*"

# Upload Redis backups
aws s3 sync "$BACKUP_DIR/redis/" "$S3_BUCKET/redis/" \
  --exclude "*" \
  --include "*${DATE}*"

# Upload configuration
aws s3 sync "$BACKUP_DIR/config/" "$S3_BUCKET/config/" \
  --exclude "*" \
  --include "*${DATE}*"

# Set lifecycle policy (delete after 90 days)
aws s3api put-bucket-lifecycle-configuration \
  --bucket my-backups \
  --lifecycle-configuration file://s3-lifecycle.json

echo "Backups uploaded to S3"
```

**S3 Lifecycle Policy:**

```json
{
  "Rules": [
    {
      "Id": "Delete old backups",
      "Status": "Enabled",
      "Prefix": "fastapi-prod/",
      "Expiration": {
        "Days": 90
      }
    }
  ]
}
```

## Backup Verification

### Verify Database Backups

```bash
#!/bin/bash
# scripts/verify_backups.sh

BACKUP_FILE="$1"
TEST_DB="fastapi_test_restore"

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <backup_file.dump.gz>"
  exit 1
fi

echo "Verifying database backup: $BACKUP_FILE"

# Uncompress if needed
if [[ $BACKUP_FILE == *.gz ]]; then
  gunzip -c "$BACKUP_FILE" > "${BACKUP_FILE%.gz}"
  BACKUP_FILE="${BACKUP_FILE%.gz}"
fi

# Create test database
docker exec hw-db psql -U postgres -c "DROP DATABASE IF EXISTS $TEST_DB;"
docker exec hw-db psql -U postgres -c "CREATE DATABASE $TEST_DB;"

# Restore to test database
docker exec -i hw-db pg_restore -U postgres -d "$TEST_DB" -Fc < "$BACKUP_FILE"

if [ $? -eq 0 ]; then
  echo "✅ Backup verification PASSED"

  # Verify data integrity
  ROW_COUNT=$(docker exec hw-db psql -U postgres -d "$TEST_DB" -t -c "SELECT COUNT(*) FROM author;")
  echo "   Author table has $ROW_COUNT rows"

  # Drop test database
  docker exec hw-db psql -U postgres -c "DROP DATABASE $TEST_DB;"
else
  echo "❌ Backup verification FAILED"
  exit 1
fi
```

### Automated Backup Testing

```bash
#!/bin/bash
# scripts/test_restore_monthly.sh
# Run this monthly to verify restore procedures

BACKUP_DIR="/backups"
TEST_DATE=$(date +%Y%m%d)

echo "Monthly backup restore test - $TEST_DATE"

# Find most recent backup
LATEST_BACKUP=$(ls -t "$BACKUP_DIR/postgres/"*.dump.gz | head -1)

echo "Testing restore from: $LATEST_BACKUP"

# Verify backup
bash /scripts/verify_backups.sh "$LATEST_BACKUP"

if [ $? -eq 0 ]; then
  echo "✅ Monthly restore test PASSED"

  # Send success notification
  curl -X POST "https://api.slack.com/webhooks/your-webhook" \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"Monthly backup restore test PASSED: $TEST_DATE\"}"
else
  echo "❌ Monthly restore test FAILED"

  # Send failure alert
  curl -X POST "https://api.slack.com/webhooks/your-webhook" \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"🚨 Monthly backup restore test FAILED: $TEST_DATE\"}"

  exit 1
fi
```

## Disaster Recovery

### Complete System Recovery

**Recovery Steps:**

```bash
#!/bin/bash
# scripts/disaster_recovery.sh

set -e

echo "=== DISASTER RECOVERY PROCEDURE ==="
echo "This will restore the entire system from backups"
read -p "Enter backup date (YYYYMMDD_HHMMSS): " BACKUP_DATE

BACKUP_DIR="/backups"

# 1. Stop all services
echo "1. Stopping all services..."
docker-compose -f docker/docker-compose.yml down

# 2. Remove all volumes
echo "2. Removing existing volumes..."
docker volume rm postgres-hw-data redis-hw-data grafana-data prometheus-data loki-data

# 3. Recreate volumes
echo "3. Recreating volumes..."
docker volume create postgres-hw-data
docker volume create redis-hw-data
docker volume create grafana-data
docker volume create prometheus-data
docker volume create loki-data

# 4. Restore configuration
echo "4. Restoring configuration files..."
tar -xzf "$BACKUP_DIR/config/config_${BACKUP_DATE}.tar.gz" -C /

# 5. Start database services
echo "5. Starting database services..."
docker-compose -f docker/docker-compose.yml up -d hw-db hw-redis
sleep 30

# 6. Restore PostgreSQL database
echo "6. Restoring PostgreSQL database..."
LATEST_DB_BACKUP=$(ls -t "$BACKUP_DIR/postgres/"*${BACKUP_DATE}*.dump.gz | head -1)
bash /scripts/restore_db.sh "$LATEST_DB_BACKUP"

# 7. Restore Keycloak database
echo "7. Restoring Keycloak database..."
LATEST_KC_BACKUP=$(ls -t "$BACKUP_DIR/keycloak/"*${BACKUP_DATE}*.dump.gz | head -1)
gunzip -c "$LATEST_KC_BACKUP" | docker exec -i hw-db pg_restore -U prod_user -d keycloak_prod -Fc

# 8. Restore Redis data
echo "8. Restoring Redis data..."
LATEST_REDIS_BACKUP=$(ls -t "$BACKUP_DIR/redis/"*${BACKUP_DATE}*.rdb | head -1)
bash /scripts/restore_redis.sh "$LATEST_REDIS_BACKUP"

# 9. Start remaining services
echo "9. Starting application services..."
docker-compose -f docker/docker-compose.yml up -d

# 10. Wait for services to be healthy
echo "10. Waiting for services to be healthy..."
for i in {1..30}; do
  if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Application is healthy"
    break
  fi
  echo "Waiting for application to be ready... ($i/30)"
  sleep 10
done

# 11. Verify recovery
echo "11. Verifying recovery..."
curl -s http://localhost:8000/health | jq

echo "=== DISASTER RECOVERY COMPLETED ==="
echo "Please verify:"
echo "  - Application: http://localhost:8000/health"
echo "  - Grafana: http://localhost:3000"
echo "  - Keycloak: http://localhost:8080"
```

### Recovery Runbook

**Step-by-Step Manual Recovery:**

1. **Assess Damage:**
   ```bash
   # Check what's running
   docker ps -a

   # Check volumes
   docker volume ls

   # Review recent logs
   journalctl -u docker --since "1 hour ago"
   ```

2. **Identify Latest Backups:**
   ```bash
   # List available backups
   ls -lh /backups/postgres/ | tail -5
   ls -lh /backups/redis/ | tail -5
   ls -lh /backups/config/ | tail -5
   ```

3. **Stop Services:**
   ```bash
   docker-compose -f docker/docker-compose.yml down
   ```

4. **Restore Database:**
   ```bash
   # Follow database restore steps
   bash /scripts/restore_db.sh <backup_file>
   ```

5. **Restore Configuration:**
   ```bash
   tar -xzf /backups/config/config_latest.tar.gz -C /
   ```

6. **Restart Services:**
   ```bash
   docker-compose -f docker/docker-compose.yml up -d
   ```

7. **Verify Recovery:**
   ```bash
   # Check health endpoints
   curl http://localhost:8000/health
   curl http://localhost:8080/health

   # Check logs
   docker logs hw-server --tail 50
   docker logs hw-keycloak --tail 50
   ```

8. **Notify Stakeholders:**
   ```bash
   # Send recovery notification
   echo "System recovered from backup at $(date)" | \
     mail -s "System Recovery Complete" ops@example.com
   ```

## Point-in-Time Recovery

### PostgreSQL PITR

**Requirements:**
- Base backup (pg_basebackup)
- Continuous WAL archiving
- Target recovery time

**Recovery Procedure:**

```bash
#!/bin/bash
# scripts/pitr.sh

TARGET_TIME="$1"
BASE_BACKUP="/backups/postgres/base/latest"
WAL_ARCHIVE="/backups/postgres/wal_archive"

if [ -z "$TARGET_TIME" ]; then
  echo "Usage: $0 'YYYY-MM-DD HH:MM:SS'"
  exit 1
fi

echo "Point-in-Time Recovery to: $TARGET_TIME"

# Stop database
docker-compose stop hw-db

# Backup current data (safety measure)
docker run --rm \
  -v postgres-hw-data:/data \
  -v /backups/postgres:/backup \
  alpine tar czf "/backup/pre_pitr_$(date +%Y%m%d_%H%M%S).tar.gz" -C /data .

# Remove current data
docker volume rm postgres-hw-data
docker volume create postgres-hw-data

# Restore base backup
docker run --rm \
  -v postgres-hw-data:/var/lib/postgresql/data \
  -v "$BASE_BACKUP:/backup" \
  postgres:13 bash -c "cp -r /backup/* /var/lib/postgresql/data/"

# Create recovery configuration
cat > /tmp/recovery.signal <<EOF
# Trigger recovery mode
EOF

cat > /tmp/postgresql.auto.conf <<EOF
restore_command = 'cp $WAL_ARCHIVE/%f %p'
recovery_target_time = '$TARGET_TIME'
recovery_target_action = 'promote'
EOF

# Copy recovery files
docker run --rm \
  -v postgres-hw-data:/var/lib/postgresql/data \
  -v /tmp:/tmp \
  postgres:13 bash -c "cp /tmp/recovery.signal /tmp/postgresql.auto.conf /var/lib/postgresql/data/"

# Start database (recovery will begin automatically)
docker-compose start hw-db

echo "Point-in-Time Recovery initiated. Monitor logs:"
echo "  docker logs hw-db -f"
```

## Testing Recovery Procedures

### Monthly Recovery Test Checklist

**Test Schedule:** First Sunday of each month

**Test Procedure:**

1. **Prepare Test Environment:**
   ```bash
   # Use separate test docker-compose file
   cp docker/docker-compose.yml docker/docker-compose.test.yml
   # Modify ports to avoid conflicts (8001, 5433, etc.)
   ```

2. **Test Database Restore:**
   ```bash
   # Restore latest backup to test environment
   docker-compose -f docker/docker-compose.test.yml up -d hw-db-test
   bash /scripts/restore_db.sh <latest_backup>
   ```

3. **Verify Data Integrity:**
   ```bash
   # Check row counts
   docker exec hw-db-test psql -U prod_user -d fastapi_prod \
     -c "SELECT 'authors', COUNT(*) FROM author UNION ALL SELECT 'books', COUNT(*) FROM book;"

   # Check recent data
   docker exec hw-db-test psql -U prod_user -d fastapi_prod \
     -c "SELECT * FROM author ORDER BY id DESC LIMIT 5;"
   ```

4. **Test Application Startup:**
   ```bash
   # Start application with test database
   docker-compose -f docker/docker-compose.test.yml up -d hw-server-test

   # Test health endpoint
   curl http://localhost:8001/health
   ```

5. **Document Results:**
   ```bash
   # Create test report
   cat > /backups/test_reports/recovery_test_$(date +%Y%m%d).txt <<EOF
   Recovery Test Report
   Date: $(date)
   Backup Used: $BACKUP_FILE
   Database Rows: $ROW_COUNT
   Application Health: $(curl -s http://localhost:8001/health)
   Test Result: PASS/FAIL
   Notes: ...
   EOF
   ```

6. **Cleanup:**
   ```bash
   docker-compose -f docker/docker-compose.test.yml down
   docker volume rm postgres-test-data
   ```

### Automated Recovery Testing

```bash
#!/bin/bash
# scripts/automated_recovery_test.sh

REPORT_DIR="/backups/test_reports"
DATE=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="$REPORT_DIR/recovery_test_${DATE}.txt"

mkdir -p "$REPORT_DIR"

echo "=== AUTOMATED RECOVERY TEST ===" | tee "$REPORT_FILE"
echo "Date: $(date)" | tee -a "$REPORT_FILE"

# Test database restore
echo "Testing database restore..." | tee -a "$REPORT_FILE"
LATEST_BACKUP=$(ls -t /backups/postgres/*.dump.gz | head -1)
bash /scripts/verify_backups.sh "$LATEST_BACKUP" >> "$REPORT_FILE" 2>&1

if [ $? -eq 0 ]; then
  echo "✅ Database restore test: PASSED" | tee -a "$REPORT_FILE"
else
  echo "❌ Database restore test: FAILED" | tee -a "$REPORT_FILE"
  exit 1
fi

# Test Redis restore
echo "Testing Redis restore..." | tee -a "$REPORT_FILE"
LATEST_REDIS=$(ls -t /backups/redis/*.rdb | head -1)
# Add Redis restore test logic here

echo "=== TEST COMPLETED ===" | tee -a "$REPORT_FILE"

# Send report
mail -s "Recovery Test Report - $DATE" ops@example.com < "$REPORT_FILE"
```

## Backup Monitoring

### Backup Health Checks

```bash
#!/bin/bash
# scripts/check_backup_health.sh

BACKUP_DIR="/backups"
ALERT_EMAIL="ops@example.com"

# Check if daily backup exists
TODAY=$(date +%Y%m%d)
if ! ls "$BACKUP_DIR/postgres/"*${TODAY}*.dump.gz > /dev/null 2>&1; then
  echo "⚠️ WARNING: No database backup found for today" | \
    mail -s "Backup Alert: Missing Daily Backup" "$ALERT_EMAIL"
fi

# Check backup age
LATEST_BACKUP=$(ls -t "$BACKUP_DIR/postgres/"*.dump.gz | head -1)
BACKUP_AGE=$(($(date +%s) - $(stat -c %Y "$LATEST_BACKUP")))

if [ $BACKUP_AGE -gt 86400 ]; then
  echo "⚠️ WARNING: Latest backup is older than 24 hours" | \
    mail -s "Backup Alert: Backup Too Old" "$ALERT_EMAIL"
fi

# Check backup size
BACKUP_SIZE=$(du -b "$LATEST_BACKUP" | cut -f1)
MIN_SIZE=$((1024 * 1024 * 10))  # 10 MB minimum

if [ $BACKUP_SIZE -lt $MIN_SIZE ]; then
  echo "⚠️ WARNING: Backup size is suspiciously small" | \
    mail -s "Backup Alert: Small Backup Size" "$ALERT_EMAIL"
fi

echo "Backup health check completed"
```

## Additional Resources

- [PostgreSQL Backup Documentation](https://www.postgresql.org/docs/current/backup.html)
- [Redis Persistence](https://redis.io/docs/management/persistence/)
- [Docker Volume Backups](https://docs.docker.com/storage/volumes/)
- [AWS S3 Backup Best Practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/backup-best-practices.html)

## Emergency Contacts

- **On-Call Engineer**: PagerDuty rotation
- **Database Administrator**: dba@example.com
- **DevOps Team**: devops@example.com
- **Security Team**: security@example.com
