# Tab-based Authentication System Implementation

## Overview

This document describes the tab-based authentication system that supports:
- **Individual (Parent/Guardian)** login and registration
- **Hospital/Clinic** login and registration with role-based access (ADMIN, DOCTOR, STAFF)

## Backend Implementation

### Database Changes

1. **Users Table**
   - Added `login_type` column (INDIVIDUAL | HOSPITAL)
   - Default: INDIVIDUAL for backward compatibility

2. **Hospital Users Table** (NEW)
   - Maps users to hospitals with roles
   - Fields: `user_id`, `hospital_id`, `hospital_role` (ADMIN, DOCTOR, STAFF), `is_active`

### API Endpoints

#### Individual Authentication
- `POST /api/v1/auth/register/individual` - Register individual user
- `POST /api/v1/auth/login/individual` - Login individual user

#### Hospital Authentication
- `POST /api/v1/auth/register/hospital` - Register hospital + admin user
- `POST /api/v1/auth/login/hospital` - Login hospital user

#### Hospital User Management (ADMIN only)
- `POST /api/v1/auth/hospital/users` - Add hospital user (DOCTOR/STAFF)
- `GET /api/v1/auth/hospital/users` - Get all hospital users

#### Shared OTP Endpoint
- `POST /api/v1/auth/send-otp` - Send OTP (works for both Individual and Hospital)

### JWT Token Payload

Tokens now include:
```json
{
  "user_id": 123,
  "mobile_number": "+919876543210",
  "role": "parent",  // Backward compatibility
  "login_type": "individual" | "hospital",
  "hospital_id": 456,  // null for individual users
  "hospital_role": "admin" | "doctor" | "staff"  // null for individual users
}
```

### Authorization Middleware

New dependencies in `app/core/authorization.py`:
- `require_login_type(LoginType.INDIVIDUAL)` - Ensure user has required login type
- `require_hospital_user` - Ensure user is hospital user with active assignment
- `require_hospital_role([HospitalRole.ADMIN])` - Ensure user has required hospital role

## Frontend Implementation

### Auth Service Updates

New methods in `auth.service.ts`:
- `loginIndividual(mobile, otp)` - Individual login
- `registerIndividual(data)` - Individual registration
- `loginHospital(mobile, otp)` - Hospital login
- `registerHospital(data)` - Hospital registration
- `addHospitalUser(data)` - Add hospital user (ADMIN only)

### Login Page

Updated `login/page.tsx` with tabs:
- **Individual Tab**: Parent/Guardian login
- **Hospital Tab**: Hospital staff login

### Registration Flow

- **Individual**: Simple registration form
- **Hospital**: Hospital details + admin user creation

### Role-based Routing

After login, users are routed based on:
- **Individual** → `/dashboard` (Parent Dashboard)
- **Hospital ADMIN** → `/dashboard` (Admin Dashboard)
- **Hospital DOCTOR** → `/dashboard` (Doctor Dashboard)
- **Hospital STAFF** → `/dashboard` (Staff Dashboard)

## Migration

Run migration script:
```bash
psql -U postgres -d vaccination_db -f migrations/add_tab_auth_system.sql
```

Or use Alembic:
```bash
alembic upgrade head
```

## Backward Compatibility

- Existing users continue to work unchanged
- Existing login endpoints remain functional
- Existing QR & vaccination flows unchanged
- All existing APIs continue to work

## Security

- Hospital users cannot access parent personal data
- Parent users cannot access hospital dashboards
- Role-based checks on every protected API
- Audit logging for all role-based actions

