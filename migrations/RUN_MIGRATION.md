# How to Run the Beneficiary System Migration

This guide provides multiple ways to run the `add_beneficiary_system.sql` migration.

## Method 1: Using psql (Command Line) - Recommended

### Step 1: Get your database connection details
Check your `.env` file for the `DATABASE_URL`. It should look like:
```
DATABASE_URL=postgresql://username:password@localhost:5432/database_name
```

### Step 2: Run the migration

**On Windows (PowerShell):**
```powershell
# Extract connection details from DATABASE_URL
# Format: postgresql://username:password@host:port/database

# Example:
$env:PGPASSWORD="your_password"
psql -h localhost -p 5432 -U your_username -d your_database -f migrations\add_beneficiary_system.sql
```

**On Linux/Mac:**
```bash
# Set password (optional, will prompt if not set)
export PGPASSWORD="your_password"

# Run migration
psql -h localhost -p 5432 -U your_username -d your_database -f migrations/add_beneficiary_system.sql
```

**Or connect interactively:**
```bash
psql -h localhost -p 5432 -U your_username -d your_database
```
Then copy and paste the SQL from `migrations/add_beneficiary_system.sql`

## Method 2: Using Python Script (Requires Virtual Environment)

### Step 1: Activate virtual environment
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### Step 2: Run the script
```bash
python scripts/run_beneficiary_migration.py
```

## Method 3: Using Database GUI Tools

### Using pgAdmin:
1. Open pgAdmin
2. Connect to your database
3. Right-click on your database → Query Tool
4. Open `migrations/add_beneficiary_system.sql`
5. Click Execute (F5)

### Using DBeaver:
1. Connect to your PostgreSQL database
2. Open SQL Editor
3. Open `migrations/add_beneficiary_system.sql`
4. Execute the script (Ctrl+Enter)

### Using VS Code with PostgreSQL extension:
1. Install "PostgreSQL" extension in VS Code
2. Connect to your database
3. Open `migrations/add_beneficiary_system.sql`
4. Right-click → "Execute Query"

## Method 4: Using Docker (if using docker-compose)

```bash
# If database is in Docker
docker-compose exec postgres psql -U postgres -d vaccination_db -f /path/to/migrations/add_beneficiary_system.sql

# Or copy file into container and run
docker cp migrations/add_beneficiary_system.sql vaccination_postgres:/tmp/
docker-compose exec postgres psql -U postgres -d vaccination_db -f /tmp/add_beneficiary_system.sql
```

## Verification

After running the migration, verify it worked:

```sql
-- Check if beneficiaries table exists
SELECT * FROM beneficiaries LIMIT 1;

-- Check if columns were added
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'vaccinations' 
AND column_name IN ('beneficiary_id', 'recorded_by_user_id');

-- Count beneficiaries created
SELECT type, COUNT(*) 
FROM beneficiaries 
GROUP BY type;
```

## Troubleshooting

### Error: "relation already exists"
- The table already exists. The migration uses `IF NOT EXISTS`, so it's safe to run again.

### Error: "column already exists"
- The columns were already added. The migration uses `IF NOT EXISTS`, so it's safe to run again.

### Error: "permission denied"
- Make sure your database user has CREATE, ALTER, and INSERT permissions.

### Error: "connection refused"
- Check that PostgreSQL is running and the connection details are correct.

## What the Migration Does

1. **Creates `beneficiaries` table** - Stores both ADULT (parent) and CHILD beneficiaries
2. **Adds `beneficiary_id` columns** - To `vaccinations` and `vaccination_schedules` tables
3. **Makes `child_id` nullable** - For backward compatibility
4. **Migrates existing data**:
   - Creates ADULT beneficiaries from existing users
   - Creates CHILD beneficiaries from existing child_profiles
   - Links existing vaccinations to beneficiaries

## After Migration

Once the migration is complete:
1. Restart your backend server
2. The parent profile should load automatically
3. New vaccinations will use `beneficiary_id` instead of `child_id`

