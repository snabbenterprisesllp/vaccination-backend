# Multi-Facility RBAC Implementation Guide

## Quick Start

This guide provides step-by-step instructions for implementing the multi-facility RBAC system.

## Prerequisites

- Existing vaccination platform running
- Database access (PostgreSQL)
- Python 3.8+
- FastAPI backend

## Implementation Steps

### 1. Database Migration

```bash
# Run the migration script
psql -U your_user -d your_database -f migrations/add_multi_facility_rbac.sql
```

**What it does:**
- Creates `facilities` table
- Creates `facility_users` table
- Adds `facility_id` to `vaccinations` table
- Migrates existing `hospital_users` to `facility_users`
- Migrates `hospital_id` to `facility_id` in vaccinations

### 2. Create First SUPER_ADMIN

After migration, create the first SUPER_ADMIN:

```sql
-- Option 1: Use existing user
INSERT INTO facility_users (user_id, facility_id, facility_role, is_active)
VALUES (<existing_user_id>, NULL, 'super_admin', TRUE);

-- Option 2: Create new user first, then assign SUPER_ADMIN
-- (Use existing user registration flow, then run above INSERT)
```

### 3. Update Token Service

The token service has been updated to include:
- `facility_ids`: List of facility IDs user has access to
- `facility_roles`: Dict mapping facility_id to role
- `is_super_admin`: Boolean flag

**Update auth services** to populate these fields when creating tokens:

```python
from app.core.rbac import get_user_facilities, is_super_admin
from app.models.facility_user import FacilityRole

# In your auth service
facilities = await get_user_facilities(user, db)
facility_ids = [f.facility_id for f in facilities if f.facility_id]
facility_roles = {f.facility_id: f.facility_role.value for f in facilities if f.facility_id}
is_super = await is_super_admin(user, db)

tokens = TokenService.create_token_pair(
    user_id=user.id,
    mobile_number=user.mobile_number,
    role=user.role.value,
    login_type=user.login_type.value,
    facility_ids=facility_ids,
    facility_roles=facility_roles,
    is_super_admin=is_super
)
```

### 4. Update API Endpoints

Replace existing authorization dependencies:

**Before:**
```python
from app.core.authorization import require_hospital_role, HospitalRole

@router.get("/endpoint")
async def endpoint(
    user_hospital: tuple = Depends(require_hospital_role([HospitalRole.ADMIN]))
):
    user, hospital_user = user_hospital
    ...
```

**After:**
```python
from app.core.rbac import require_facility_admin

@router.get("/endpoint")
async def endpoint(
    user_facility: tuple = Depends(require_facility_admin)
):
    user, facility_user = user_facility
    ...
```

### 5. Frontend Updates

#### Web App (Next.js)

**1. Update Auth Context:**
```typescript
interface AuthUser {
  user_id: number;
  facility_ids: number[];
  facility_roles: Record<number, string>;
  is_super_admin: boolean;
}

// Check permissions
const isSuperAdmin = user?.is_super_admin;
const isFacilityAdmin = (facilityId: number) => 
  user?.facility_roles[facilityId] === 'facility_admin';
```

**2. Create SUPER_ADMIN Dashboard:**
- `/dashboard/super-admin` - Facility management
- `/dashboard/super-admin/analytics` - Global analytics
- `/dashboard/super-admin/facilities` - Facility list

**3. Create FACILITY_ADMIN Dashboard:**
- `/dashboard/facility-admin` - Facility users
- `/dashboard/facility-admin/analytics` - Facility analytics
- `/dashboard/facility-admin/settings` - Facility settings

**4. Role-based Navigation:**
```typescript
// Show/hide menu items based on role
{isSuperAdmin && <Link href="/dashboard/super-admin">Super Admin</Link>}
{isFacilityAdmin(selectedFacilityId) && <Link href="/dashboard/facility-admin">Facility Admin</Link>}
```

#### Mobile App (Flutter)

**1. Update Auth Model:**
```dart
class AuthUser {
  final int userId;
  final List<int> facilityIds;
  final Map<int, String> facilityRoles;
  final bool isSuperAdmin;
  
  bool isFacilityAdmin(int facilityId) => 
    facilityRoles[facilityId] == 'facility_admin';
  
  bool isDoctor(int facilityId) => 
    facilityRoles[facilityId] == 'doctor';
}
```

**2. Facility Selection:**
```dart
// If user has multiple facilities, show selector
if (user.facilityIds.length > 1) {
  return FacilitySelectorWidget(
    facilities: user.facilityIds,
    onSelected: (facilityId) {
      // Update app state with selected facility
      setSelectedFacility(facilityId);
    }
  );
}
```

**3. Role-based UI:**
```dart
// Show different UI based on role
if (user.isDoctor(selectedFacilityId)) {
  return DoctorDashboard();
} else if (user.facilityRoles[selectedFacilityId] == 'staff') {
  return StaffDashboard();
}
```

## API Endpoint Reference

### Facility Management

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/facilities` | SUPER_ADMIN | Create facility |
| GET | `/api/v1/facilities` | SUPER_ADMIN | List facilities |
| GET | `/api/v1/facilities/{id}` | SUPER_ADMIN | Get facility |
| PUT | `/api/v1/facilities/{id}` | SUPER_ADMIN | Update facility |
| DELETE | `/api/v1/facilities/{id}` | SUPER_ADMIN | Disable facility |

### Facility User Management

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/facilities/{id}/users` | FACILITY_ADMIN, SUPER_ADMIN | Add user |
| GET | `/api/v1/facilities/{id}/users` | FACILITY_ADMIN, SUPER_ADMIN | List users |
| DELETE | `/api/v1/facilities/{id}/users/{user_id}` | FACILITY_ADMIN, SUPER_ADMIN | Remove user |

### Analytics

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/analytics/global` | SUPER_ADMIN | Global analytics |
| GET | `/api/v1/analytics/facility/{id}` | FACILITY_ADMIN, SUPER_ADMIN | Facility analytics |

## Testing

### Unit Tests

```python
# Test SUPER_ADMIN access
async def test_super_admin_can_create_facility():
    user = await create_super_admin_user()
    facility_data = {...}
    response = await client.post("/api/v1/facilities", json=facility_data, headers=get_auth_headers(user))
    assert response.status_code == 201

# Test FACILITY_ADMIN can only access their facility
async def test_facility_admin_cannot_access_other_facility():
    user = await create_facility_admin_user(facility_id=1)
    response = await client.get("/api/v1/facilities/2/users", headers=get_auth_headers(user))
    assert response.status_code == 403
```

### Integration Tests

1. Create SUPER_ADMIN
2. Create facility via SUPER_ADMIN
3. Assign FACILITY_ADMIN to facility
4. FACILITY_ADMIN adds DOCTOR
5. DOCTOR adds vaccination
6. Verify analytics show correct data

## Troubleshooting

### Issue: "User is not assigned to any facility"

**Solution:** Ensure user has active entry in `facility_users` table:
```sql
SELECT * FROM facility_users WHERE user_id = <user_id> AND is_active = TRUE;
```

### Issue: "This endpoint requires SUPER_ADMIN role"

**Solution:** Check if user has SUPER_ADMIN assignment:
```sql
SELECT * FROM facility_users 
WHERE user_id = <user_id> 
AND facility_role = 'super_admin' 
AND is_active = TRUE;
```

### Issue: "You can only manage users for your own facility"

**Solution:** Ensure FACILITY_ADMIN is assigned to the correct facility:
```sql
SELECT facility_id FROM facility_users 
WHERE user_id = <user_id> 
AND facility_role = 'facility_admin' 
AND is_active = TRUE;
```

## Rollback Plan

If issues occur, you can rollback:

1. **Keep existing tables:** `hospitals` and `hospital_users` remain intact
2. **Disable new features:** Set `is_active = FALSE` for all facilities
3. **Revert code:** Use previous version of authorization dependencies

## Next Steps

1. ✅ Run migration
2. ✅ Create first SUPER_ADMIN
3. ✅ Update token creation
4. ✅ Update API endpoints
5. ✅ Update frontend
6. ✅ Test thoroughly
7. ✅ Deploy to staging
8. ✅ Deploy to production

## Support

For questions or issues:
- Review `MULTI_FACILITY_RBAC.md` for detailed documentation
- Check migration logs
- Review audit logs for permission denials
- Verify facility assignments in database

