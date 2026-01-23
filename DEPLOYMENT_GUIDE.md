# Multi-Facility RBAC Deployment Guide

## Pre-Deployment Checklist

- [ ] Database backup created
- [ ] Migration script tested on staging
- [ ] First SUPER_ADMIN user identified
- [ ] Frontend code updated
- [ ] API endpoints tested
- [ ] Documentation reviewed

## Step 1: Run Database Migration

### Option A: Using Python Script (Recommended)

```bash
cd vaccination-backend
python scripts/run_rbac_migration.py
```

### Option B: Using psql Directly

```bash
# Windows PowerShell
$env:PGPASSWORD="your_password"
psql -h localhost -p 5432 -U your_username -d your_database -f migrations\add_multi_facility_rbac.sql

# Linux/Mac
export PGPASSWORD="your_password"
psql -h localhost -p 5432 -U your_username -d your_database -f migrations/add_multi_facility_rbac.sql
```

### Option C: Using Docker

```bash
docker-compose exec postgres psql -U postgres -d vaccination_db -f /path/to/migrations/add_multi_facility_rbac.sql
```

### Verify Migration

```sql
-- Check if tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_name IN ('facilities', 'facility_users');

-- Check if facility_id column exists in vaccinations
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'vaccinations' AND column_name = 'facility_id';
```

## Step 2: Create First SUPER_ADMIN

```bash
cd vaccination-backend
python scripts/create_super_admin.py
```

Or manually:

```sql
-- Find user ID first
SELECT id, mobile_number, full_name FROM users LIMIT 10;

-- Assign SUPER_ADMIN (replace <user_id> with actual ID)
INSERT INTO facility_users (user_id, facility_id, facility_role, is_active)
VALUES (<user_id>, NULL, 'super_admin', TRUE);
```

## Step 3: Update Backend Code

The backend code has been updated. Ensure:

1. **Models are imported:**
   ```python
   from app.models.facility import Facility
   from app.models.facility_user import FacilityUser, FacilityRole
   ```

2. **RBAC dependencies are used:**
   ```python
   from app.core.rbac import require_super_admin, require_facility_admin
   ```

3. **Token service includes facility info:**
   - Tokens now include `facility_ids`, `facility_roles`, `is_super_admin`

## Step 4: Update Frontend

### Web App (Next.js)

1. **Update types** (`src/types/index.ts`):
   - Added `facility_ids`, `facility_roles`, `is_super_admin` to User interface

2. **Create RBAC utilities** (`src/utils/rbac.ts`):
   - Helper functions for role checking

3. **Create dashboards:**
   - `/dashboard/super-admin` - SUPER_ADMIN dashboard
   - `/dashboard/facility-admin` - FACILITY_ADMIN dashboard

4. **Update auth service:**
   - Ensure tokens are decoded with facility information

### Mobile App (Flutter)

1. **Update AuthUser model** to include:
   - `facilityIds: List<int>`
   - `facilityRoles: Map<int, String>`
   - `isSuperAdmin: bool`

2. **Create facility selector** if user has multiple facilities

3. **Update API calls** to include `facility_id` parameter

## Step 5: Testing

### Backend API Tests

```bash
# Test SUPER_ADMIN endpoints
curl -X GET http://localhost:8000/api/v1/facilities \
  -H "Authorization: Bearer <super_admin_token>"

# Test FACILITY_ADMIN endpoints
curl -X GET http://localhost:8000/api/v1/facilities/1/users \
  -H "Authorization: Bearer <facility_admin_token>"

# Test analytics
curl -X GET http://localhost:8000/api/v1/analytics/global \
  -H "Authorization: Bearer <super_admin_token>"
```

### Frontend Tests

1. **Login as SUPER_ADMIN:**
   - Verify SUPER_ADMIN dashboard loads
   - Verify can create facilities
   - Verify can view global analytics

2. **Login as FACILITY_ADMIN:**
   - Verify FACILITY_ADMIN dashboard loads
   - Verify can manage facility users
   - Verify cannot access other facilities

3. **Login as DOCTOR:**
   - Verify can view/add vaccinations
   - Verify cannot manage users

4. **Login as STAFF:**
   - Verify can assist with entries
   - Verify cannot view analytics

## Step 6: Deploy to Staging

### Backend Deployment

```bash
# Build Docker image
docker build -t vaccination-backend:rbac .

# Run migration on staging database
python scripts/run_rbac_migration.py

# Create SUPER_ADMIN on staging
python scripts/create_super_admin.py

# Deploy backend
# (Follow your existing deployment process)
```

### Frontend Deployment

```bash
# Build web app
cd vaccination-web-app
npm run build

# Deploy
# (Follow your existing deployment process)
```

## Step 7: Production Deployment

### Pre-Production

1. **Backup database:**
   ```bash
   pg_dump -U postgres vaccination_db > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Test migration on staging:**
   - Run migration script
   - Verify all endpoints work
   - Test with real users

3. **Prepare rollback plan:**
   - Keep backup of database
   - Document rollback steps

### Production Deployment

1. **Maintenance window** (if needed):
   - Notify users of scheduled maintenance
   - Set maintenance mode if applicable

2. **Run migration:**
   ```bash
   python scripts/run_rbac_migration.py
   ```

3. **Create SUPER_ADMIN:**
   ```bash
   python scripts/create_super_admin.py
   ```

4. **Deploy backend:**
   - Deploy updated code
   - Restart services
   - Verify health checks

5. **Deploy frontend:**
   - Deploy updated code
   - Clear CDN cache if applicable
   - Verify UI loads correctly

6. **Post-deployment verification:**
   - Test SUPER_ADMIN login
   - Test FACILITY_ADMIN login
   - Test existing PARENT users still work
   - Monitor error logs

## Rollback Procedure

If issues occur:

1. **Stop new deployments**

2. **Revert code:**
   ```bash
   git revert <commit-hash>
   ```

3. **Restore database** (if needed):
   ```bash
   psql -U postgres vaccination_db < backup_YYYYMMDD_HHMMSS.sql
   ```

4. **Restart services**

5. **Verify system works**

## Monitoring

After deployment, monitor:

- **Error rates** - Check for 403/500 errors
- **API response times** - Ensure no performance degradation
- **Database queries** - Monitor for slow queries
- **User feedback** - Watch for user-reported issues

## Support

For issues:

1. Check migration logs
2. Review audit logs for permission denials
3. Verify facility assignments in database
4. Check JWT token contents (decode at jwt.io)

## Post-Deployment Tasks

- [ ] Update user documentation
- [ ] Train SUPER_ADMIN users
- [ ] Train FACILITY_ADMIN users
- [ ] Monitor system for 24-48 hours
- [ ] Collect user feedback
- [ ] Document any issues encountered

