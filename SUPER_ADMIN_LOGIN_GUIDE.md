# SUPER_ADMIN Login Guide

## Overview

SUPER_ADMIN users login using **OTP-based authentication** (mobile number + OTP), just like regular users. The difference is that SUPER_ADMIN users have the `is_super_admin: true` flag in their JWT token and can access global admin features.

## Step 1: Create a SUPER_ADMIN User

### Option A: Using the Script (Recommended)

Run the interactive script to create a SUPER_ADMIN:

```bash
cd vaccination-backend
python scripts/create_super_admin.py
```

The script will:
1. Ask if you want to assign SUPER_ADMIN to an existing user OR create a new user
2. Prompt for mobile number, full name, and email
3. Create the SUPER_ADMIN assignment in the database

**Example Output:**
```
Create SUPER_ADMIN User
============================================================

Option 1: Assign SUPER_ADMIN to existing user
Option 2: Create new user and assign SUPER_ADMIN

Enter option (1 or 2): 2

Enter mobile number: 9876543210
Enter full name: Super Admin
Enter email (optional): admin@example.com
✅ Created new user: 1

============================================================
✅ SUPER_ADMIN created successfully!
============================================================

User ID: 1
Mobile: 9876543210
Name: Super Admin
```

### Option B: Using the API Endpoint

**First SUPER_ADMIN (Bootstrap):**

```bash
# Set bootstrap token in .env
SUPER_ADMIN_BOOTSTRAP_TOKEN=your-secure-token-here
# OR enable signup
ALLOW_SUPER_ADMIN_SIGNUP=true
```

Then call the signup endpoint:

```bash
curl -X POST "http://localhost:8000/api/v1/auth/super-admin/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "mobile_number": "9876543210",
    "full_name": "Super Admin",
    "email": "admin@example.com",
    "bootstrap_token": "your-secure-token-here"
  }'
```

**Additional SUPER_ADMINS (requires existing SUPER_ADMIN):**

```bash
curl -X POST "http://localhost:8000/api/v1/auth/super-admin/create" \
  -H "Authorization: Bearer <existing-super-admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "mobile_number": "9876543211",
    "full_name": "Another Super Admin",
    "email": "admin2@example.com"
  }'
```

## Step 2: Login as SUPER_ADMIN

### Using the Web App

1. Go to the login page: `http://localhost:3000/login`
2. Enter the **mobile number** of the SUPER_ADMIN user
3. Click "Send OTP"
4. Enter the OTP received via SMS/console
5. Click "Verify OTP"
6. You'll be logged in and redirected to the Super Admin Dashboard

### Using the API Directly

**Step 1: Send OTP**

```bash
curl -X POST "http://localhost:8000/api/v1/auth/send-otp" \
  -H "Content-Type: application/json" \
  -d '{
    "mobile_number": "9876543210"
  }'
```

**Step 2: Verify OTP**

```bash
curl -X POST "http://localhost:8000/api/v1/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{
    "mobile_number": "9876543210",
    "otp": "123456"
  }'
```

**Response will include:**
```json
{
  "success": true,
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "is_super_admin": true,
  "facility_ids": [],
  "facility_roles": {}
}
```

## Step 3: Access Super Admin Dashboard

After login, you'll have access to:

1. **Super Admin Dashboard**: `/dashboard/super-admin`
   - View all facilities
   - Create new facilities
   - View global analytics
   - Manage facility users

2. **API Endpoints** (with SUPER_ADMIN token):
   - `GET /api/v1/facilities` - List all facilities
   - `POST /api/v1/facilities` - Create facility
   - `GET /api/v1/analytics/global` - Global analytics
   - `POST /api/v1/auth/super-admin/create` - Create additional SUPER_ADMINS

## Quick Setup Example

```bash
# 1. Create SUPER_ADMIN user
cd vaccination-backend
python scripts/create_super_admin.py
# Follow prompts: Option 2, enter mobile: 9876543210, name: Admin

# 2. Start backend server
python -m uvicorn app.main:app --reload

# 3. Start frontend
cd ../vaccination-web-app
npm run dev

# 4. Login at http://localhost:3000/login
# Mobile: 9876543210
# OTP: (check console or SMS)
```

## Check Existing SUPER_ADMIN Users

To see all SUPER_ADMIN users in the database:

```bash
docker-compose exec postgres psql -U postgres -d vaccination_db -c \
  "SELECT u.id, u.mobile_number, u.full_name, u.email, fu.created_at 
   FROM users u 
   JOIN facility_users fu ON u.id = fu.user_id 
   WHERE fu.facility_role = 'SUPER_ADMIN' AND fu.is_active = true;"
```

## Troubleshooting

### "Access denied" error
- Make sure the user has `facility_role = 'SUPER_ADMIN'` in `facility_users` table
- Check that `is_active = true` in `facility_users` table
- Verify JWT token contains `is_super_admin: true`

### OTP not received
- Check backend logs for OTP (in development, OTP is logged to console)
- Verify mobile number is correct
- Check Redis is running (OTP is stored in Redis)

### Can't access Super Admin Dashboard
- Verify JWT token has `is_super_admin: true`
- Check browser console for authentication errors
- Ensure frontend is reading facility info from JWT correctly

## Security Notes

1. **Bootstrap Token**: Use a strong, random token for `SUPER_ADMIN_BOOTSTRAP_TOKEN`
2. **First SUPER_ADMIN**: Should be created in a secure environment
3. **Additional SUPER_ADMINS**: Can only be created by existing SUPER_ADMINS
4. **OTP Security**: OTP expires after 5 minutes (configurable)
5. **Token Expiry**: Access tokens expire after 30 minutes (configurable)

## Default Test Credentials

For development/testing, you can use:

```
Mobile Number: 9876543210
Full Name: Super Admin
Email: admin@example.com
```

**Note**: OTP will be sent to the mobile number. In development, check the backend console for the OTP code.

