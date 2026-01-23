# Quick Fix: facility_id Column Error

## Error Message

```
Class <class 'app.models.vaccination.Vaccination'> does not have a mapped column named 'facility_id'
```

## Cause

The `Facility` model has a relationship to `Vaccination.facility_id`, but the database column doesn't exist yet because the migration hasn't been run.

## Solution

### Option 1: Run Migration (Recommended)

```bash
cd vaccination-backend
python scripts/run_rbac_migration.py
```

This will:
1. Create the `facilities` table
2. Create the `facility_users` table
3. Add `facility_id` column to `vaccinations` table
4. Migrate existing data

### Option 2: Temporarily Comment Relationship (Quick Fix)

If you cannot run the migration immediately, temporarily comment out the relationship in `app/models/facility.py`:

```python
# Temporarily comment this until migration runs:
# vaccinations = relationship(
#     "Vaccination", 
#     back_populates="facility", 
#     foreign_keys="Vaccination.facility_id",
#     lazy="select"
# )
```

**Then run the migration and uncomment it.**

## Verification

After migration, verify the column exists:

```sql
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'vaccinations' 
AND column_name = 'facility_id';
```

Should return: `facility_id`

## Why This Happens

SQLAlchemy validates relationships at startup. When it tries to map the `Facility` model, it checks that the `Vaccination.facility_id` column exists. Since the migration hasn't run, the column doesn't exist in the database, causing the error.

## After Migration

Once the migration completes:
1. The `facility_id` column will exist
2. SQLAlchemy can validate the relationship
3. The server will start without errors

---

**Recommendation:** Always run the migration before starting the server after adding new model relationships.

