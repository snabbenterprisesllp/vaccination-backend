# Delete Facilities Script Instructions

This script will delete all facilities from the database except the one with `facility_id = 'FAC-B6B48A218C8E'`.

## ⚠️ WARNING

This operation will:
- **DELETE** all facilities except `FAC-B6B48A218C8E`
- **DELETE** all facility user assignments for deleted facilities
- **SET facility_id to NULL** for all vaccinations linked to deleted facilities (vaccination records are preserved)

## Method 1: Using PowerShell Script (Recommended)

```powershell
cd vaccination-backend
.\scripts\delete_facilities_except.ps1
```

The script will:
1. Check if PostgreSQL container is running
2. Copy the SQL file to the container
3. Ask for confirmation
4. Execute the deletion

## Method 2: Using Docker Compose Directly

```powershell
cd vaccination-backend

# Copy SQL file to container
docker cp scripts/delete_facilities_except.sql $(docker-compose ps -q postgres):/tmp/delete_facilities_except.sql

# Execute SQL script
docker-compose exec -T postgres psql -U postgres -d vaccination_db -f /tmp/delete_facilities_except.sql
```

## Method 3: Using psql Directly (if not using Docker)

```powershell
# Set password (if needed)
$env:PGPASSWORD="your_password"

# Execute SQL script
psql -h localhost -p 5432 -U postgres -d vaccination_db -f scripts/delete_facilities_except.sql
```

## Method 4: Manual SQL Execution

If you have access to a database client (pgAdmin, DBeaver, etc.), you can copy and paste the contents of `scripts/delete_facilities_except.sql` and execute it.

## Verification

After running the script, verify that only one facility remains:

```sql
SELECT id, facility_id, name FROM facilities;
```

You should see only the facility with `facility_id = 'FAC-B6B48A218C8E'`.

## What Happens to Related Data?

1. **Facility Users**: All `facility_users` records for deleted facilities are **DELETED**
2. **Vaccinations**: All `vaccinations` records linked to deleted facilities have their `facility_id` set to **NULL** (records are preserved)
3. **Other tables**: Check foreign key constraints - some may cascade delete, others may set to NULL

## Rollback

If you need to rollback, you should restore from a database backup:

```powershell
# Restore from backup
docker-compose exec -T postgres psql -U postgres -d vaccination_db < backup_file.sql
```

**Always backup your database before running deletion scripts!**


