# API Permission Matrix - Complete Reference

## Overview

This document provides a complete reference for all API endpoints and their permission requirements in the multi-facility RBAC system.

## Legend

- ✅ = Allowed
- ❌ = Denied
- ✅ (own) = Allowed only for own facility
- ✅ (any) = Allowed for any facility

## Authentication Endpoints

| Endpoint | Method | SUPER_ADMIN | FACILITY_ADMIN | DOCTOR | STAFF | PARENT | Notes |
|----------|--------|-------------|----------------|--------|-------|--------|-------|
| `/auth/super-admin/signup` | POST | ✅ (with token) | ❌ | ❌ | ❌ | ❌ | Bootstrap only |
| `/auth/super-admin/create` | POST | ✅ | ❌ | ❌ | ❌ | ❌ | Create additional SUPER_ADMIN |
| `/auth/register/individual` | POST | ❌ | ❌ | ❌ | ❌ | ✅ | Parent registration |
| `/auth/login/individual` | POST | ❌ | ❌ | ❌ | ❌ | ✅ | Parent login |
| `/auth/register/hospital` | POST | ✅ | ❌ | ❌ | ❌ | ❌ | Legacy hospital registration |
| `/auth/login/hospital` | POST | ✅ | ✅ | ✅ | ✅ | ❌ | Hospital user login |

## Facility Management Endpoints

| Endpoint | Method | SUPER_ADMIN | FACILITY_ADMIN | DOCTOR | STAFF | PARENT | Notes |
|----------|--------|-------------|----------------|--------|-------|--------|-------|
| `/facilities` | POST | ✅ | ❌ | ❌ | ❌ | ❌ | Create facility |
| `/facilities` | GET | ✅ | ❌ | ❌ | ❌ | ❌ | List all facilities |
| `/facilities/{id}` | GET | ✅ | ✅ (own) | ❌ | ❌ | ❌ | Get facility details |
| `/facilities/{id}` | PUT | ✅ | ❌ | ❌ | ❌ | ❌ | Update facility |
| `/facilities/{id}` | DELETE | ✅ | ❌ | ❌ | ❌ | ❌ | Deactivate facility |
| `/facilities/{id}/users` | POST | ✅ | ✅ (own) | ❌ | ❌ | ❌ | Add user to facility |
| `/facilities/{id}/users` | GET | ✅ | ✅ (own) | ❌ | ❌ | ❌ | List facility users |
| `/facilities/{id}/users/{user_id}` | DELETE | ✅ | ✅ (own) | ❌ | ❌ | ❌ | Remove user from facility |

## Analytics Endpoints

| Endpoint | Method | SUPER_ADMIN | FACILITY_ADMIN | DOCTOR | STAFF | PARENT | Notes |
|----------|--------|-------------|----------------|--------|-------|--------|-------|
| `/analytics/global` | GET | ✅ | ❌ | ❌ | ❌ | ❌ | Global analytics |
| `/analytics/facility/{id}` | GET | ✅ (any) | ✅ (own) | ❌ | ❌ | ❌ | Facility analytics |
| `/analytics/facility/{id}/daily` | GET | ✅ (any) | ✅ (own) | ❌ | ❌ | ❌ | Daily trends |
| `/analytics/facility/{id}/weekly` | GET | ✅ (any) | ✅ (own) | ❌ | ❌ | ❌ | Weekly trends |
| `/analytics/facility/{id}/monthly` | GET | ✅ (any) | ✅ (own) | ❌ | ❌ | ❌ | Monthly trends |
| `/analytics/facility/{id}/vaccine-distribution` | GET | ✅ (any) | ✅ (own) | ❌ | ❌ | ❌ | Vaccine distribution |

## Vaccination Endpoints

| Endpoint | Method | SUPER_ADMIN | FACILITY_ADMIN | DOCTOR | STAFF | PARENT | Notes |
|----------|--------|-------------|----------------|--------|-------|--------|-------|
| `/vaccinations` | POST | ✅ (any) | ✅ (own) | ✅ (own) | ✅ (own) | ❌ | Create vaccination |
| `/vaccinations` | GET | ✅ (any) | ✅ (own) | ✅ (own) | ✅ (own) | ✅ (own) | List vaccinations |
| `/vaccinations/{id}` | GET | ✅ (any) | ✅ (own) | ✅ (own) | ✅ (own) | ✅ (own) | Get vaccination |
| `/vaccinations/{id}` | PUT | ✅ (any) | ✅ (own) | ✅ (own) | ❌ | ❌ | Update vaccination |
| `/vaccinations/{id}` | DELETE | ✅ (any) | ✅ (own) | ❌ | ❌ | ❌ | Delete vaccination |

## User Management Endpoints

| Endpoint | Method | SUPER_ADMIN | FACILITY_ADMIN | DOCTOR | STAFF | PARENT | Notes |
|----------|--------|-------------|----------------|--------|-------|--------|-------|
| `/auth/me` | GET | ✅ | ✅ | ✅ | ✅ | ✅ | Get current user |
| `/auth/me` | PUT | ✅ | ✅ | ✅ | ✅ | ✅ | Update profile |
| `/users` | GET | ✅ | ❌ | ❌ | ❌ | ❌ | List all users (admin) |
| `/users/{id}` | GET | ✅ | ✅ (own facility) | ❌ | ❌ | ❌ | Get user details |

## Permission Enforcement

### Backend Enforcement

All endpoints use FastAPI dependencies:

```python
# Example: SUPER_ADMIN only
@router.get("/facilities")
async def list_facilities(
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db)
):
    ...

# Example: FACILITY_ADMIN for own facility
@router.get("/facilities/{facility_id}/users")
async def list_facility_users(
    facility_id: int,
    user_facility: tuple = Depends(require_facility_admin),
    db: AsyncSession = Depends(get_db)
):
    current_user, facility_user = user_facility
    # Additional check: facility_user.facility_id == facility_id
    ...
```

### Frontend Enforcement

Frontend should also check permissions (defense in depth):

```typescript
// Example: Check before rendering
if (!isSuperAdmin(user)) {
  return <AccessDenied />
}

// Example: Check before API call
if (!isFacilityAdmin(user, facilityId)) {
  toast.error('Access denied')
  return
}
```

## Scope Definitions

### Global Scope (SUPER_ADMIN)
- Can access ALL facilities
- Can view ALL data
- No facility restrictions

### Facility Scope (FACILITY_ADMIN, DOCTOR, STAFF)
- Can access ONLY assigned facility
- Cannot access other facilities
- Facility ID must match in all queries

### Individual Scope (PARENT)
- Can access ONLY own data
- Cannot access facility data
- Cannot access other users' data

## Error Responses

### 403 Forbidden
```json
{
  "detail": "This endpoint requires SUPER_ADMIN role"
}
```

### 404 Not Found (Facility)
```json
{
  "detail": "Facility not found or you don't have access"
}
```

### 403 Forbidden (Cross-Facility)
```json
{
  "detail": "You can only access data for your assigned facility"
}
```

## Testing Permissions

### Test SUPER_ADMIN Access
```bash
curl -X GET http://localhost:8000/api/v1/facilities \
  -H "Authorization: Bearer <super_admin_token>"
```

### Test FACILITY_ADMIN Access
```bash
# Should succeed for own facility
curl -X GET http://localhost:8000/api/v1/facilities/1/users \
  -H "Authorization: Bearer <facility_admin_token>"

# Should fail for other facility
curl -X GET http://localhost:8000/api/v1/facilities/999/users \
  -H "Authorization: Bearer <facility_admin_token>"
```

---

**Last Updated:** 2024-01-15

