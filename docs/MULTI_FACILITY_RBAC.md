# Multi-Facility RBAC System Documentation

## Overview

This document describes the multi-facility, hierarchical role-based access control (RBAC) system that extends the existing vaccination platform to support:

- **SUPER_ADMIN** (Global scope)
- **FACILITY_ADMIN** (Facility-scoped)
- **DOCTOR** (Facility-scoped)
- **STAFF** (Facility-scoped)
- **PARENT** (Existing - unchanged)

## Database Schema

### Tables

#### 1. `facilities`
Represents hospitals/clinics in the system.

**Key Fields:**
- `id` (Primary Key)
- `name`, `facility_code` (Unique)
- `facility_type` (hospital, clinic, health_center)
- `address`, `city`, `state`, `pincode`, `country`
- `registration_number`
- `logo_url`
- `is_active` (can be disabled by SUPER_ADMIN)
- `legacy_hospital_id` (for backward compatibility)

#### 2. `facility_users`
Maps users to facilities with roles. Supports multi-facility assignments.

**Key Fields:**
- `id` (Primary Key)
- `user_id` (Foreign Key → users.id)
- `facility_id` (Foreign Key → facilities.id, NULL for SUPER_ADMIN)
- `facility_role` (super_admin, facility_admin, doctor, staff)
- `is_active`
- `assigned_by` (user_id who created this assignment)

**Constraints:**
- One active assignment per user per facility (unique index)
- SUPER_ADMIN can have `facility_id=NULL` (global scope)

#### 3. `vaccinations` (Updated)
Added `facility_id` column to link vaccinations to facilities.

## Roles and Permissions

### SUPER_ADMIN (Global Scope)

**Permissions:**
- ✅ Create, update, disable facilities
- ✅ Assign and manage FACILITY_ADMINS for any facility
- ✅ Create additional SUPER_ADMINS
- ✅ View analytics across ALL facilities
- ✅ Read-only access to all facility data
- ✅ Manage users across all facilities

**Scope:** Global (no facility restriction)

### FACILITY_ADMIN (Facility Scope)

**Permissions:**
- ✅ Add/remove doctors for their facility
- ✅ Add/remove staff for their facility
- ✅ Add additional FACILITY_ADMINS for their facility
- ✅ Manage facility profile (address, registration, logo)
- ✅ View analytics ONLY for their facility
- ❌ Cannot access other facilities

**Scope:** Single facility (or multiple if assigned to multiple)

### DOCTOR (Facility Scope)

**Permissions:**
- ✅ View assigned children/beneficiaries
- ✅ Add/update vaccination records
- ✅ View vaccination timelines
- ✅ Upload vaccination proofs
- ❌ Cannot manage users
- ❌ Cannot manage facility settings

**Scope:** Single facility (or multiple if assigned to multiple)

### STAFF (Facility Scope)

**Permissions:**
- ✅ Assist doctors
- ✅ Add basic vaccination entries (subject to doctor approval)
- ✅ Upload documents
- ❌ No analytics access
- ❌ Cannot manage users

**Scope:** Single facility (or multiple if assigned to multiple)

### PARENT (Existing)

**Permissions:** Unchanged
- ✅ Manage own children/beneficiaries
- ✅ View vaccination records
- ✅ Receive reminders

## API Endpoints

### Facility Management (SUPER_ADMIN only)

```
POST   /api/v1/facilities              Create facility
GET    /api/v1/facilities              List all facilities
GET    /api/v1/facilities/{id}         Get facility details
PUT    /api/v1/facilities/{id}         Update facility
DELETE /api/v1/facilities/{id}         Disable facility (soft delete)
```

### Facility User Management (FACILITY_ADMIN, SUPER_ADMIN)

```
POST   /api/v1/facilities/{id}/users           Add user to facility
GET    /api/v1/facilities/{id}/users           List facility users
DELETE /api/v1/facilities/{id}/users/{user_id} Remove user from facility
```

### Analytics

```
GET    /api/v1/analytics/global                Global analytics (SUPER_ADMIN)
GET    /api/v1/analytics/facility/{id}         Facility analytics (FACILITY_ADMIN, SUPER_ADMIN)
```

## RBAC Implementation

### Dependencies

Located in `app/core/rbac.py`:

- `require_super_admin()` - Ensures user is SUPER_ADMIN
- `require_facility_role(roles, facility_id)` - Ensures user has required role
- `require_facility_admin(facility_id)` - Ensures user is FACILITY_ADMIN or SUPER_ADMIN
- `require_doctor_or_above(facility_id)` - Ensures user is DOCTOR, FACILITY_ADMIN, or SUPER_ADMIN
- `get_user_facilities(user)` - Get all facility assignments for user
- `is_super_admin(user)` - Check if user is SUPER_ADMIN

### Usage Example

```python
from app.core.rbac import require_super_admin, require_facility_admin

@router.get("/facilities")
async def list_facilities(
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    # Only SUPER_ADMIN can access
    ...

@router.get("/facilities/{facility_id}/users")
async def list_facility_users(
    facility_id: int,
    user_facility: tuple = Depends(require_facility_admin),
    db: AsyncSession = Depends(get_db)
):
    user, facility_user = user_facility
    # FACILITY_ADMIN for their facility or SUPER_ADMIN can access
    ...
```

## JWT Token Structure

Tokens now include:

```json
{
  "user_id": 123,
  "mobile_number": "+919876543210",
  "role": "parent",  // Backward compatibility
  "login_type": "individual" | "hospital",
  "hospital_id": 456,  // Legacy
  "hospital_role": "admin",  // Legacy
  "facility_ids": [1, 2, 3],  // New RBAC
  "facility_roles": {  // New RBAC
    "1": "facility_admin",
    "2": "doctor",
    "3": "staff"
  },
  "is_super_admin": false  // New RBAC
}
```

## Migration Strategy

### Step 1: Run Migration

```bash
# Run the migration script
psql -U your_user -d your_database -f migrations/add_multi_facility_rbac.sql
```

### Step 2: Create First SUPER_ADMIN

```sql
-- Find or create a user to be SUPER_ADMIN
-- Then assign SUPER_ADMIN role:
INSERT INTO facility_users (user_id, facility_id, facility_role, is_active)
VALUES (<user_id>, NULL, 'super_admin', TRUE);
```

### Step 3: Migrate Existing Data

The migration script automatically:
- Creates facilities from existing hospitals
- Migrates hospital_users to facility_users
- Migrates hospital_id in vaccinations to facility_id

### Step 4: Update Application Code

1. Update token creation to include `facility_ids` and `facility_roles`
2. Update authorization checks to use new RBAC dependencies
3. Update frontend to use new role-based UI

## Security & Compliance

### Healthcare Safety

- ✅ **Audit Logging**: All facility/user management actions are logged
- ✅ **ABDM Compliance**: Maintains ABHA integration requirements
- ✅ **Data Isolation**: Facility-scoped roles ensure data isolation
- ✅ **Access Control**: Multi-layer permission checks (frontend + backend)

### Best Practices

1. **Principle of Least Privilege**: Users only get minimum required permissions
2. **Defense in Depth**: Check permissions at multiple layers
3. **Audit Trail**: All sensitive operations are logged
4. **Token Expiry**: Short-lived access tokens (15 minutes)
5. **Soft Deletes**: Facilities are disabled, not deleted

## Frontend Integration

### Web App (Next.js)

**SUPER_ADMIN Dashboard:**
- Facility list with management
- Global analytics
- User management across facilities

**FACILITY_ADMIN Dashboard:**
- Facility users management
- Facility analytics
- Facility settings

**Role-based UI:**
- Show/hide features based on role
- Prevent cross-facility access

### Mobile App (Flutter)

**Role-aware UI:**
- Doctor view: Vaccination management
- Staff view: Basic entry assistance
- No admin features on mobile

**Facility Selection:**
- If user belongs to multiple facilities, show facility selector
- Filter data by selected facility

## Testing Checklist

- [ ] SUPER_ADMIN can create facilities
- [ ] SUPER_ADMIN can assign FACILITY_ADMINS
- [ ] FACILITY_ADMIN can manage users for their facility only
- [ ] FACILITY_ADMIN cannot access other facilities
- [ ] DOCTOR can view/add vaccinations for their facility
- [ ] STAFF can assist but not manage users
- [ ] Multi-facility users can switch between facilities
- [ ] Analytics are scoped correctly
- [ ] JWT tokens include facility_ids
- [ ] Backward compatibility maintained

## Backward Compatibility

- ✅ Existing `hospitals` table remains (not deleted)
- ✅ Existing `hospital_users` table remains (not deleted)
- ✅ Legacy `hospital_id` in vaccinations still works
- ✅ Existing PARENT users unchanged
- ✅ Legacy JWT tokens still work (with fallback)

## Support

For questions or issues:
- Check migration logs
- Review audit logs for permission denials
- Verify facility assignments in `facility_users` table
- Ensure JWT tokens include correct `facility_ids`

