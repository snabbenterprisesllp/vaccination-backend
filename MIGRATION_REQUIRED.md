# Migration Required Before Starting Server

## ⚠️ Important

**You must run the database migration BEFORE starting the server.**

The error you're seeing:
```
Class <class 'app.models.vaccination.Vaccination'> does not have a mapped column named 'facility_id'
```

This occurs because:
1. The `Facility` model has a relationship to `Vaccination.facility_id`
2. The `Vaccination` model now includes the `facility_id` column definition
3. **BUT** the database column doesn't exist yet until the migration runs

## Solution

### Step 1: Run the Migration

```bash
cd vaccination-backend
python scripts/run_rbac_migration.py
```

This will:
- Create the `facilities` table
- Create the `facility_users` table
- Add `facility_id` column to `vaccinations` table
- Migrate existing data

### Step 2: Verify Migration

```sql
-- Check if column exists
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'vaccinations' 
AND column_name = 'facility_id';

-- Should return: facility_id
```

### Step 3: Start the Server

```bash
uvicorn app.main:app --reload
```

## Alternative: Temporary Fix (Not Recommended)

If you cannot run the migration immediately, you can temporarily comment out the relationship in `app/models/facility.py`:

```python
# Temporarily comment this out until migration runs:
# vaccinations = relationship("Vaccination", back_populates="facility", foreign_keys="Vaccination.facility_id")
```

**But this is NOT recommended** - you should run the migration instead.

## Why This Happens

SQLAlchemy validates relationships at startup. When it tries to map the `Facility` model, it checks that the `Vaccination.facility_id` column exists. Since the migration hasn't run yet, the column doesn't exist in the database, causing the error.

## After Migration

Once the migration is complete, the error will be resolved and the server will start normally.

