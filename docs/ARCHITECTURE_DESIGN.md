# Multi-Facility RBAC Architecture Design

## Executive Summary

This document outlines the architectural design for extending the vaccination platform to support SUPER_ADMIN onboarding, multi-facility management, and facility-level analytics while maintaining backward compatibility with existing parent/child vaccination workflows.

## 1. Database Schema & ER Diagram

### 1.1 Entity Relationship Diagram

```
┌─────────────┐
│    Users    │
│─────────────│
│ id (PK)     │
│ mobile_num  │
│ full_name   │
│ login_type  │
└──────┬──────┘
       │
       │ 1:N
       │
┌──────▼──────────────┐
│  FacilityUsers      │
│─────────────────────│
│ id (PK)            │
│ user_id (FK)       │
│ facility_id (FK)    │
│ facility_role      │
│ is_active          │
└──────┬─────────────┘
       │
       │ N:1
       │
┌──────▼──────────────┐
│    Facilities       │
│─────────────────────│
│ id (PK)            │
│ facility_id (UK)   │ ← Globally unique identifier
│ name               │
│ address            │
│ registration_num   │
│ is_active          │
└──────┬─────────────┘
       │
       │ 1:N
       │
┌──────▼──────────────┐
│   Vaccinations      │
│─────────────────────│
│ id (PK)            │
│ beneficiary_id (FK)│
│ facility_id (FK)   │ ← NEW: Links to facility
│ vaccine_id (FK)    │
│ vaccination_date   │
│ status             │
└─────────────────────┘
```

### 1.2 Database Tables

#### `facilities`
```sql
CREATE TABLE facilities (
    id SERIAL PRIMARY KEY,
    facility_id VARCHAR(50) UNIQUE NOT NULL,  -- Globally unique (UUID or code)
    name VARCHAR(255) NOT NULL,
    facility_type VARCHAR(50) NOT NULL,  -- hospital, clinic, health_center
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    pincode VARCHAR(10) NOT NULL,
    country VARCHAR(100) DEFAULT 'India',
    registration_number VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(20),
    logo_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uk_facility_id UNIQUE (facility_id),
    INDEX idx_facilities_active (is_active) WHERE is_active = TRUE,
    INDEX idx_facilities_city_state (city, state)
);
```

#### `facility_users`
```sql
CREATE TABLE facility_users (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE CASCADE,
    facility_role VARCHAR(20) NOT NULL,  -- super_admin, facility_admin, doctor, staff
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    assigned_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_facility_role CHECK (facility_role IN ('super_admin', 'facility_admin', 'doctor', 'staff')),
    CONSTRAINT uk_user_facility_active UNIQUE (user_id, facility_id) WHERE is_active = TRUE AND facility_id IS NOT NULL,
    INDEX idx_facility_users_user (user_id),
    INDEX idx_facility_users_facility (facility_id),
    INDEX idx_facility_users_role (facility_role)
);
```

#### `vaccinations` (Updated)
```sql
-- Migration: Add facility_id column
ALTER TABLE vaccinations
ADD COLUMN facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL;

CREATE INDEX idx_vaccinations_facility_date 
ON vaccinations(facility_id, vaccination_date) 
WHERE facility_id IS NOT NULL;

CREATE INDEX idx_vaccinations_facility_status 
ON vaccinations(facility_id, status) 
WHERE facility_id IS NOT NULL;
```

### 1.3 Facility ID Generation Strategy

**Option 1: UUID-based (Recommended)**
```python
import uuid
facility_id = f"FAC-{uuid.uuid4().hex[:12].upper()}"
# Example: FAC-A1B2C3D4E5F6
```

**Option 2: Sequential Code**
```python
# Format: FAC-{STATE_CODE}-{SEQUENTIAL}
# Example: FAC-MH-0001, FAC-KA-0001
facility_id = f"FAC-{state_code}-{next_sequence:04d}"
```

**Option 3: Timestamp-based**
```python
from datetime import datetime
facility_id = f"FAC-{datetime.now().strftime('%Y%m%d')}-{random_string(6)}"
```

**Recommendation:** Use UUID-based for global uniqueness and security.

## 2. FastAPI API Design & Permission Matrix

### 2.1 Authentication & Signup

#### `POST /api/v1/auth/super-admin/signup`
**Purpose:** Create first SUPER_ADMIN (bootstrap)

**Security:**
- Protected by environment variable: `ALLOW_SUPER_ADMIN_SIGNUP=true`
- Or secret token: `SUPER_ADMIN_BOOTSTRAP_TOKEN`

**Request:**
```json
{
  "mobile_number": "+919876543210",
  "full_name": "Super Admin",
  "email": "admin@example.com",
  "bootstrap_token": "secure-bootstrap-token-here"
}
```

**Response:**
```json
{
  "success": true,
  "user_id": 123,
  "access_token": "...",
  "refresh_token": "...",
  "is_super_admin": true
}
```

**Permission:** Public (with bootstrap token)

---

#### `POST /api/v1/auth/super-admin/create`
**Purpose:** Create additional SUPER_ADMIN (existing SUPER_ADMIN only)

**Request:**
```json
{
  "mobile_number": "+919876543211",
  "full_name": "Another Super Admin",
  "email": "admin2@example.com"
}
```

**Permission:** SUPER_ADMIN only

---

### 2.2 Facility Management APIs

#### `POST /api/v1/facilities`
**Purpose:** Create new facility

**Request:**
```json
{
  "name": "City Hospital",
  "facility_type": "hospital",
  "address": "123 Main St",
  "city": "Mumbai",
  "state": "Maharashtra",
  "pincode": "400001",
  "registration_number": "REG-12345",
  "email": "hospital@example.com",
  "phone": "+912234567890"
}
```

**Response:**
```json
{
  "id": 1,
  "facility_id": "FAC-A1B2C3D4E5F6",
  "name": "City Hospital",
  "is_active": true,
  "created_at": "2024-01-15T10:00:00Z"
}
```

**Permission:** SUPER_ADMIN only

---

#### `GET /api/v1/facilities`
**Purpose:** List all facilities

**Query Parameters:**
- `skip`: Pagination offset (default: 0)
- `limit`: Page size (default: 100, max: 1000)
- `city`: Filter by city
- `state`: Filter by state
- `is_active`: Filter by status

**Response:**
```json
{
  "facilities": [...],
  "total": 50,
  "skip": 0,
  "limit": 100
}
```

**Permission:** SUPER_ADMIN only

---

#### `GET /api/v1/facilities/{facility_id}`
**Purpose:** Get facility details

**Permission:** SUPER_ADMIN (any facility), FACILITY_ADMIN (own facility)

---

#### `PUT /api/v1/facilities/{facility_id}`
**Purpose:** Update facility

**Permission:** SUPER_ADMIN only

---

#### `DELETE /api/v1/facilities/{facility_id}`
**Purpose:** Deactivate facility (soft delete)

**Permission:** SUPER_ADMIN only

---

#### `POST /api/v1/facilities/{facility_id}/admins`
**Purpose:** Assign FACILITY_ADMIN to facility

**Request:**
```json
{
  "mobile_number": "+919876543212",
  "full_name": "Facility Admin",
  "email": "facility@example.com"
}
```

**Permission:** SUPER_ADMIN only

---

### 2.3 Analytics APIs

#### `GET /api/v1/analytics/global`
**Purpose:** Global analytics across all facilities

**Query Parameters:**
- `start_date`: Filter start date (ISO format)
- `end_date`: Filter end date (ISO format)
- `group_by`: `facility` | `date` | `vaccine_type`

**Response:**
```json
{
  "total_facilities": 10,
  "total_vaccinations": 5000,
  "vaccinations_today": 150,
  "facility_wise": [
    {
      "facility_id": "FAC-001",
      "facility_name": "City Hospital",
      "vaccinations_today": 25,
      "total_vaccinations": 500,
      "pending": 50,
      "completed": 450
    }
  ],
  "daily_trends": [
    {
      "date": "2024-01-15",
      "vaccinations": 150,
      "by_facility": {...}
    }
  ]
}
```

**Permission:** SUPER_ADMIN only

---

#### `GET /api/v1/analytics/facility/{facility_id}`
**Purpose:** Facility-specific analytics

**Query Parameters:**
- `start_date`: Filter start date
- `end_date`: Filter end date
- `group_by`: `date` | `vaccine_type` | `doctor`

**Response:**
```json
{
  "facility_id": "FAC-001",
  "facility_name": "City Hospital",
  "vaccinations_today": 25,
  "vaccinations_this_week": 150,
  "vaccinations_this_month": 600,
  "vaccine_distribution": {
    "BCG": 50,
    "OPV": 100,
    "HepB": 75,
    "DPT": 80
  },
  "daily_trends": [
    {
      "date": "2024-01-15",
      "count": 25
    }
  ],
  "weekly_trends": [...],
  "monthly_trends": [...]
}
```

**Permission:** SUPER_ADMIN (any facility), FACILITY_ADMIN (own facility)

---

### 2.4 Permission Matrix

| Endpoint | SUPER_ADMIN | FACILITY_ADMIN | DOCTOR | STAFF | PARENT |
|----------|-------------|----------------|--------|-------|--------|
| `POST /auth/super-admin/signup` | ✅ (with token) | ❌ | ❌ | ❌ | ❌ |
| `POST /auth/super-admin/create` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `POST /facilities` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `GET /facilities` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `GET /facilities/{id}` | ✅ | ✅ (own) | ❌ | ❌ | ❌ |
| `PUT /facilities/{id}` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `DELETE /facilities/{id}` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `POST /facilities/{id}/admins` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `GET /analytics/global` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `GET /analytics/facility/{id}` | ✅ (any) | ✅ (own) | ❌ | ❌ | ❌ |
| `POST /vaccinations` | ✅ (any) | ✅ (own) | ✅ (own) | ✅ (own) | ❌ |
| `GET /vaccinations` | ✅ (any) | ✅ (own) | ✅ (own) | ✅ (own) | ✅ (own) |

## 3. Sample SQL Queries for Daily Vaccination Analytics

### 3.1 Vaccines Administered Today (Per Facility)

```sql
SELECT 
    f.facility_id,
    f.name AS facility_name,
    COUNT(v.id) AS vaccinations_today
FROM facilities f
LEFT JOIN vaccinations v ON v.facility_id = f.id
    AND v.vaccination_date = CURRENT_DATE
    AND v.status = 'completed'
WHERE f.is_active = TRUE
GROUP BY f.id, f.facility_id, f.name
ORDER BY vaccinations_today DESC;
```

### 3.2 Vaccines Administered Per Day (Date Filter)

```sql
SELECT 
    v.vaccination_date,
    f.facility_id,
    f.name AS facility_name,
    COUNT(v.id) AS vaccination_count
FROM vaccinations v
JOIN facilities f ON v.facility_id = f.id
WHERE v.vaccination_date BETWEEN :start_date AND :end_date
    AND v.status = 'completed'
    AND f.is_active = TRUE
GROUP BY v.vaccination_date, f.id, f.facility_id, f.name
ORDER BY v.vaccination_date DESC, vaccination_count DESC;
```

### 3.3 Total Vaccinations Per Facility

```sql
SELECT 
    f.facility_id,
    f.name AS facility_name,
    COUNT(CASE WHEN v.status = 'completed' THEN 1 END) AS completed,
    COUNT(CASE WHEN v.status = 'pending' THEN 1 END) AS pending,
    COUNT(CASE WHEN v.status = 'scheduled' THEN 1 END) AS scheduled,
    COUNT(v.id) AS total
FROM facilities f
LEFT JOIN vaccinations v ON v.facility_id = f.id
WHERE f.is_active = TRUE
GROUP BY f.id, f.facility_id, f.name
ORDER BY completed DESC;
```

### 3.4 Weekly Trends (Last 4 Weeks)

```sql
SELECT 
    DATE_TRUNC('week', v.vaccination_date) AS week_start,
    f.facility_id,
    COUNT(v.id) AS vaccination_count
FROM vaccinations v
JOIN facilities f ON v.facility_id = f.id
WHERE v.vaccination_date >= CURRENT_DATE - INTERVAL '4 weeks'
    AND v.status = 'completed'
    AND f.is_active = TRUE
GROUP BY DATE_TRUNC('week', v.vaccination_date), f.facility_id
ORDER BY week_start DESC, f.facility_id;
```

### 3.5 Vaccine-Type Distribution (Per Facility)

```sql
SELECT 
    f.facility_id,
    f.name AS facility_name,
    vm.vaccine_name,
    COUNT(v.id) AS count,
    ROUND(COUNT(v.id) * 100.0 / SUM(COUNT(v.id)) OVER (PARTITION BY f.id), 2) AS percentage
FROM vaccinations v
JOIN facilities f ON v.facility_id = f.id
JOIN vaccine_master vm ON v.vaccine_id = vm.id
WHERE v.status = 'completed'
    AND f.is_active = TRUE
    AND v.vaccination_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY f.id, f.facility_id, f.name, vm.id, vm.vaccine_name
ORDER BY f.facility_id, count DESC;
```

### 3.6 Daily Vaccination Count (Last 30 Days)

```sql
SELECT 
    v.vaccination_date,
    COUNT(v.id) AS daily_count,
    COUNT(DISTINCT v.facility_id) AS facilities_active
FROM vaccinations v
JOIN facilities f ON v.facility_id = f.id
WHERE v.vaccination_date >= CURRENT_DATE - INTERVAL '30 days'
    AND v.status = 'completed'
    AND f.is_active = TRUE
GROUP BY v.vaccination_date
ORDER BY v.vaccination_date DESC;
```

## 4. JWT Claim Structure

### 4.1 Token Payload

```json
{
  "user_id": 123,
  "mobile_number": "+919876543210",
  "role": "parent",  // Legacy compatibility
  "login_type": "individual" | "hospital",
  
  // New RBAC Claims
  "is_super_admin": true,  // Global admin flag
  "facility_ids": [1, 2, 3],  // List of facility IDs user has access to
  "facility_roles": {  // Mapping facility_id -> role
    "1": "facility_admin",
    "2": "doctor",
    "3": "staff"
  },
  
  // Token Metadata
  "exp": 1705315200,  // Expiration timestamp
  "iat": 1705308600,  // Issued at
  "type": "access"    // Token type
}
```

### 4.2 Token Generation Logic

```python
def create_token_pair(user: User, db: AsyncSession):
    # Get facility assignments
    facilities = await get_user_facilities(user, db)
    is_super = await is_super_admin(user, db)
    
    facility_ids = [f.facility_id for f in facilities if f.facility_id]
    facility_roles = {
        f.facility_id: f.facility_role.value 
        for f in facilities 
        if f.facility_id
    }
    
    token_data = {
        "user_id": user.id,
        "mobile_number": user.mobile_number,
        "role": user.role.value,  # Legacy
        "login_type": user.login_type.value,
        "is_super_admin": is_super,
        "facility_ids": facility_ids,
        "facility_roles": facility_roles
    }
    
    return create_access_token(token_data)
```

## 5. UI Navigation Flow

### 5.1 SUPER_ADMIN Navigation

```
Dashboard (Super Admin)
├── Facilities
│   ├── List All Facilities
│   ├── Create New Facility
│   ├── View Facility Details
│   └── Edit/Deactivate Facility
├── Analytics
│   ├── Global Overview
│   │   ├── Total Facilities
│   │   ├── Total Vaccinations
│   │   ├── Vaccinations Today
│   │   └── Facility Performance
│   ├── Facility-Wise Analytics
│   │   ├── Select Facility
│   │   ├── Daily Trends
│   │   ├── Weekly Trends
│   │   └── Vaccine Distribution
│   └── Date Range Filter
└── User Management
    ├── Create Super Admin
    ├── Assign Facility Admins
    └── View All Users
```

### 5.2 FACILITY_ADMIN Navigation

```
Dashboard (Facility Admin)
├── Facility Overview
│   ├── Facility Details
│   └── Facility Settings
├── Analytics (Own Facility Only)
│   ├── Daily Vaccination Count
│   ├── Weekly Trends
│   ├── Monthly Trends
│   └── Vaccine-Type Distribution
├── User Management
│   ├── List Doctors & Staff
│   ├── Add Doctor
│   ├── Add Staff
│   └── Remove Users
└── Vaccinations
    ├── View All Vaccinations
    └── Add Vaccination Record
```

### 5.3 Component Hierarchy

```
SuperAdminDashboard
├── FacilityList
│   ├── FacilityCard (xN)
│   └── CreateFacilityButton
├── GlobalAnalytics
│   ├── SummaryCards
│   ├── FacilityPerformanceTable
│   └── DateRangeFilter
└── FacilityAnalyticsModal
    ├── DailyTrendChart
    ├── WeeklyTrendChart
    └── VaccineDistributionChart

FacilityAdminDashboard
├── FacilityInfo
├── FacilityAnalytics
│   ├── DailyCount
│   ├── TrendCharts
│   └── VaccineDistribution
└── UserManagement
    ├── UserList
    └── AddUserForm
```

## 6. Migration Plan (Zero Data Loss)

### 6.1 Migration Steps

#### Step 1: Pre-Migration Backup
```bash
pg_dump -U postgres vaccination_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

#### Step 2: Create New Tables
```sql
-- Run: migrations/add_multi_facility_rbac.sql
-- Creates: facilities, facility_users tables
-- Adds: facility_id to vaccinations table
```

#### Step 3: Migrate Existing Hospital Data
```sql
-- If hospitals table exists, migrate to facilities
INSERT INTO facilities (
    facility_id, name, facility_type, address, city, state, pincode,
    registration_number, is_active, legacy_hospital_id
)
SELECT 
    'FAC-' || UPPER(SUBSTRING(MD5(hospital_code::text) FROM 1 FOR 12)),
    name,
    hospital_type,
    address, city, state, pincode,
    registration_number,
    TRUE,
    id
FROM hospitals
ON CONFLICT DO NOTHING;
```

#### Step 4: Migrate Vaccination Records
```sql
-- Link existing vaccinations to facilities via hospital_id
UPDATE vaccinations v
SET facility_id = (
    SELECT f.id 
    FROM facilities f 
    WHERE f.legacy_hospital_id = v.hospital_id 
    LIMIT 1
)
WHERE v.hospital_id IS NOT NULL
  AND v.facility_id IS NULL;
```

#### Step 5: Create First SUPER_ADMIN
```sql
-- Via script or manual
INSERT INTO facility_users (user_id, facility_id, facility_role, is_active)
VALUES (<user_id>, NULL, 'super_admin', TRUE);
```

#### Step 6: Verify Migration
```sql
-- Check data integrity
SELECT 
    (SELECT COUNT(*) FROM facilities) AS facilities_count,
    (SELECT COUNT(*) FROM facility_users) AS facility_users_count,
    (SELECT COUNT(*) FROM vaccinations WHERE facility_id IS NOT NULL) AS linked_vaccinations,
    (SELECT COUNT(*) FROM vaccinations WHERE facility_id IS NULL AND hospital_id IS NOT NULL) AS unlinked_vaccinations;
```

### 6.2 Rollback Plan

```sql
-- If migration fails, rollback:
-- 1. Restore from backup
-- 2. Remove new columns (if added)
ALTER TABLE vaccinations DROP COLUMN IF EXISTS facility_id;
DROP TABLE IF EXISTS facility_users;
DROP TABLE IF EXISTS facilities;
```

### 6.3 Data Integrity Checks

```sql
-- Ensure no orphaned records
SELECT COUNT(*) FROM vaccinations 
WHERE facility_id IS NOT NULL 
  AND facility_id NOT IN (SELECT id FROM facilities);

-- Ensure all active facilities have admins
SELECT f.id, f.name 
FROM facilities f
WHERE f.is_active = TRUE
  AND NOT EXISTS (
    SELECT 1 FROM facility_users fu
    WHERE fu.facility_id = f.id
      AND fu.facility_role = 'facility_admin'
      AND fu.is_active = TRUE
  );
```

## 7. Healthcare-Grade Security Considerations

### 7.1 Authentication & Authorization

**Multi-Factor Authentication (MFA):**
- Require MFA for SUPER_ADMIN accounts
- OTP-based authentication for all admin users
- Session timeout: 15 minutes for admin accounts

**Role-Based Access Control:**
- Strict role validation at API level
- Frontend role checks (defense in depth)
- No privilege escalation possible

**Token Security:**
- Short-lived access tokens (15 minutes)
- Refresh tokens (7 days)
- Token rotation on privilege changes
- Secure token storage (httpOnly cookies recommended)

### 7.2 Data Protection

**Encryption:**
- Data at rest: Database encryption
- Data in transit: TLS 1.3
- Sensitive fields: Encrypted columns (mobile numbers, emails)

**Audit Logging:**
```python
# All admin actions logged
audit_log = {
    "action": "facility_created",
    "user_id": current_user.id,
    "facility_id": facility.id,
    "timestamp": datetime.utcnow(),
    "ip_address": request.client.host,
    "user_agent": request.headers.get("user-agent")
}
```

**Data Isolation:**
- Facility-scoped queries (enforced at DB level)
- No cross-facility data leakage
- Row-level security policies (PostgreSQL)

### 7.3 Compliance

**HIPAA Considerations:**
- PHI encryption
- Access logging
- Data retention policies
- Breach notification procedures

**ABDM Compliance:**
- ABHA integration maintained
- Consent management
- Data portability

**Audit Requirements:**
- All admin actions logged
- Immutable audit trail
- Regular security audits

### 7.4 Security Best Practices

**Input Validation:**
- Pydantic schemas for all inputs
- SQL injection prevention (ORM only)
- XSS prevention (input sanitization)

**Rate Limiting:**
- API rate limits per user
- Stricter limits for admin endpoints
- DDoS protection

**Error Handling:**
- No sensitive data in error messages
- Generic error responses
- Detailed logging (server-side only)

**Secrets Management:**
- Environment variables for secrets
- No secrets in code
- Secret rotation policies

## 8. Scalability Considerations

### 8.1 Database Optimization

**Indexing Strategy:**
```sql
-- Critical indexes for analytics
CREATE INDEX idx_vaccinations_facility_date_status 
ON vaccinations(facility_id, vaccination_date, status);

CREATE INDEX idx_vaccinations_date_facility 
ON vaccinations(vaccination_date, facility_id) 
WHERE status = 'completed';

-- Partial indexes for active records
CREATE INDEX idx_facilities_active 
ON facilities(id) WHERE is_active = TRUE;
```

**Query Optimization:**
- Use EXPLAIN ANALYZE for slow queries
- Materialized views for complex analytics
- Partitioning for large vaccination tables (by date)

### 8.2 Caching Strategy

**Redis Caching:**
```python
# Cache analytics for 5 minutes
cache_key = f"analytics:facility:{facility_id}:{date}"
analytics = await redis.get(cache_key)
if not analytics:
    analytics = await compute_analytics(facility_id, date)
    await redis.setex(cache_key, 300, json.dumps(analytics))
```

**Cache Invalidation:**
- Invalidate on new vaccination
- Invalidate on facility update
- TTL-based expiration

### 8.3 API Performance

**Pagination:**
- Default page size: 100
- Maximum page size: 1000
- Cursor-based pagination for large datasets

**Response Compression:**
- Gzip compression for large responses
- JSON minification

**Async Operations:**
- Async/await for all DB operations
- Connection pooling
- Background tasks for heavy analytics

## 9. Implementation Checklist

### Phase 1: Foundation
- [ ] Database migration script
- [ ] Facility model and schema
- [ ] FacilityUser model and schema
- [ ] Update Vaccination model
- [ ] RBAC dependencies

### Phase 2: Authentication
- [ ] SUPER_ADMIN signup endpoint
- [ ] Bootstrap token validation
- [ ] JWT token updates
- [ ] Auth service updates

### Phase 3: Facility Management
- [ ] Create facility API
- [ ] List facilities API
- [ ] Update facility API
- [ ] Deactivate facility API
- [ ] Assign FACILITY_ADMIN API

### Phase 4: Analytics
- [ ] Global analytics API
- [ ] Facility analytics API
- [ ] Daily/weekly/monthly trends
- [ ] Vaccine distribution queries
- [ ] Caching layer

### Phase 5: Frontend
- [ ] SUPER_ADMIN dashboard
- [ ] FACILITY_ADMIN dashboard
- [ ] Analytics charts
- [ ] Facility management UI
- [ ] Navigation updates

### Phase 6: Testing & Deployment
- [ ] Unit tests
- [ ] Integration tests
- [ ] Security audit
- [ ] Performance testing
- [ ] Staging deployment
- [ ] Production deployment

## 10. Monitoring & Alerting

### Key Metrics
- API response times
- Error rates (4xx, 5xx)
- Database query performance
- Cache hit rates
- Active facilities count
- Daily vaccination counts

### Alerts
- High error rates (>1%)
- Slow queries (>1 second)
- Failed authentication attempts
- Unusual admin activity
- Database connection issues

---

**Document Version:** 1.0  
**Last Updated:** 2024-01-15  
**Author:** Principal Backend + Platform Architect

