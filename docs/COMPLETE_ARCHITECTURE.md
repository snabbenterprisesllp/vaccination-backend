# Complete Architecture Design - Multi-Facility RBAC System

## Executive Summary

This document provides the complete architectural design for extending the vaccination platform to support SUPER_ADMIN onboarding, multi-facility management, and facility-level analytics while maintaining 100% backward compatibility.

## 1. Database Schema & ER Diagram

### 1.1 Complete ER Diagram

```
┌─────────────┐         ┌──────────────────┐         ┌──────────────┐
│    Users    │◄───────►│  FacilityUsers   │◄───────►│  Facilities  │
│─────────────│   1:N   │──────────────────│   N:1   │──────────────│
│ id (PK)     │         │ id (PK)          │         │ id (PK)      │
│ mobile_num  │         │ user_id (FK)     │         │ facility_id  │
│ full_name   │         │ facility_id (FK) │         │ name         │
│ login_type  │         │ facility_role    │         │ address      │
└─────────────┘         │ is_active        │         │ is_active    │
       │                └──────────────────┘         └──────┬───────┘
       │                                                       │
       │ 1:N                                                   │ 1:N
       │                                                       │
┌──────▼──────────────┐                              ┌────────▼──────────┐
│   Vaccinations      │                              │  Beneficiaries    │
│─────────────────────│                              │──────────────────│
│ id (PK)            │                              │ id (PK)          │
│ beneficiary_id (FK)│◄─────────────────────────────┤ account_id (FK)  │
│ facility_id (FK)   │                              │ type             │
│ vaccine_id (FK)    │                              │ first_name       │
│ vaccination_date   │                              │ date_of_birth    │
│ status             │                              └──────────────────┘
└─────────────────────┘
```

### 1.2 Key Relationships

- **User ↔ FacilityUser**: One user can belong to multiple facilities (many-to-many)
- **Facility ↔ FacilityUser**: One facility has many users (one-to-many)
- **Facility ↔ Vaccination**: One facility has many vaccinations (one-to-many)
- **Vaccination ↔ Beneficiary**: One beneficiary has many vaccinations (one-to-many)

### 1.3 Facility ID Generation

**Strategy:** UUID-based with prefix

```python
import uuid

def generate_facility_id() -> str:
    """Generate globally unique facility ID"""
    return f"FAC-{uuid.uuid4().hex[:12].upper()}"

# Example: FAC-A1B2C3D4E5F6
```

**Properties:**
- Globally unique
- Non-sequential (security)
- Human-readable
- 18 characters total

## 2. FastAPI API Design

### 2.1 Complete API Endpoint List

#### Authentication
- `POST /api/v1/auth/super-admin/signup` - Bootstrap SUPER_ADMIN
- `POST /api/v1/auth/super-admin/create` - Create additional SUPER_ADMIN

#### Facility Management
- `POST /api/v1/facilities` - Create facility
- `GET /api/v1/facilities` - List facilities
- `GET /api/v1/facilities/{id}` - Get facility
- `PUT /api/v1/facilities/{id}` - Update facility
- `DELETE /api/v1/facilities/{id}` - Deactivate facility

#### Facility User Management
- `POST /api/v1/facilities/{id}/users` - Add user
- `GET /api/v1/facilities/{id}/users` - List users
- `DELETE /api/v1/facilities/{id}/users/{user_id}` - Remove user

#### Analytics
- `GET /api/v1/analytics/global` - Global analytics
- `GET /api/v1/analytics/global/daily` - Global daily stats
- `GET /api/v1/analytics/facility/{id}` - Facility analytics
- `GET /api/v1/analytics/facility/{id}/daily` - Daily trends
- `GET /api/v1/analytics/facility/{id}/weekly` - Weekly trends
- `GET /api/v1/analytics/facility/{id}/monthly` - Monthly trends
- `GET /api/v1/analytics/facility/{id}/vaccine-distribution` - Vaccine distribution

### 2.2 Permission Matrix

See `API_PERMISSION_MATRIX.md` for complete reference.

## 3. JWT Claim Structure

### 3.1 Complete Token Payload

```json
{
  "user_id": 123,
  "mobile_number": "+919876543210",
  "role": "parent",
  "login_type": "hospital",
  
  "is_super_admin": true,
  "facility_ids": [1, 2, 3],
  "facility_roles": {
    "1": "facility_admin",
    "2": "doctor",
    "3": "staff"
  },
  
  "exp": 1705315200,
  "iat": 1705308600,
  "type": "access"
}
```

### 3.2 Token Validation

```python
def validate_token_claims(payload: dict) -> bool:
    """Validate token claims"""
    required_fields = ["user_id", "mobile_number"]
    
    # SUPER_ADMIN validation
    if payload.get("is_super_admin"):
        return all(field in payload for field in required_fields)
    
    # Facility user validation
    if payload.get("facility_ids"):
        return (
            "facility_roles" in payload and
            len(payload["facility_ids"]) == len(payload["facility_roles"])
        )
    
    return False
```

## 4. UI Navigation Flow

### 4.1 SUPER_ADMIN Flow

```
Login → Super Admin Dashboard
  ├── Facilities Tab
  │   ├── List View (all facilities)
  │   ├── Create Button → Create Facility Form
  │   └── Facility Card → Facility Details
  │       ├── Edit Facility
  │       ├── Deactivate Facility
  │       └── View Analytics
  │
  ├── Analytics Tab
  │   ├── Global Overview
  │   │   ├── Summary Cards
  │   │   ├── Facility Performance Table
  │   │   └── Date Range Filter
  │   │
  │   └── Facility Drill-Down
  │       ├── Select Facility
  │       ├── Daily Trends Chart
  │       ├── Weekly Trends Chart
  │       ├── Monthly Trends Chart
  │       └── Vaccine Distribution Chart
  │
  └── User Management Tab
      ├── Create Super Admin
      └── Assign Facility Admins
```

### 4.2 FACILITY_ADMIN Flow

```
Login → Facility Admin Dashboard
  ├── Facility Info
  │   └── Edit Facility Settings
  │
  ├── Analytics (Own Facility)
  │   ├── Daily Count
  │   ├── Weekly Trends
  │   ├── Monthly Trends
  │   └── Vaccine Distribution
  │
  ├── User Management
  │   ├── List Users (Doctors & Staff)
  │   ├── Add Doctor → Add User Form
  │   ├── Add Staff → Add User Form
  │   └── Remove User
  │
  └── Vaccinations
      └── View Facility Vaccinations
```

## 5. Migration Plan (Zero Data Loss)

### 5.1 Pre-Migration Checklist

- [ ] Full database backup
- [ ] Verify backup integrity
- [ ] Test migration on staging
- [ ] Document rollback procedure
- [ ] Schedule maintenance window (if needed)

### 5.2 Migration Steps

#### Step 1: Backup
```bash
pg_dump -U postgres vaccination_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

#### Step 2: Create Tables
```bash
psql -U postgres -d vaccination_db -f migrations/add_multi_facility_rbac.sql
```

#### Step 3: Migrate Hospital Data (if exists)
```sql
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
ON CONFLICT (facility_id) DO NOTHING;
```

#### Step 4: Link Vaccinations
```sql
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
```bash
python scripts/create_first_super_admin.py
```

#### Step 6: Verify
```sql
-- Check data integrity
SELECT 
    (SELECT COUNT(*) FROM facilities) AS facilities,
    (SELECT COUNT(*) FROM facility_users) AS facility_users,
    (SELECT COUNT(*) FROM vaccinations WHERE facility_id IS NOT NULL) AS linked_vaccinations;
```

### 5.3 Rollback Procedure

```sql
-- 1. Restore from backup
psql -U postgres -d vaccination_db < backup_YYYYMMDD_HHMMSS.sql

-- 2. OR manually rollback
ALTER TABLE vaccinations DROP COLUMN IF EXISTS facility_id;
DROP TABLE IF EXISTS facility_users CASCADE;
DROP TABLE IF EXISTS facilities CASCADE;
```

## 6. Healthcare-Grade Security

### 6.1 Authentication Security

**Bootstrap Protection:**
```python
# Environment variable required
SUPER_ADMIN_BOOTSTRAP_TOKEN=secure-random-token-here
ALLOW_SUPER_ADMIN_SIGNUP=false  # Set to true only during bootstrap
```

**MFA Requirements:**
- OTP-based authentication for all admin users
- Session timeout: 15 minutes
- Token rotation on role change

### 6.2 Data Protection

**Encryption:**
- Database encryption at rest
- TLS 1.3 for data in transit
- Encrypted columns for PII (mobile numbers, emails)

**Access Control:**
- Role-based access at API level
- Facility-scoped queries (enforced)
- No cross-facility data access

**Audit Logging:**
```python
{
    "action": "facility_created",
    "user_id": 123,
    "facility_id": "FAC-ABC123",
    "timestamp": "2024-01-15T10:00:00Z",
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "changes": {...}
}
```

### 6.3 Compliance

**HIPAA:**
- PHI encryption
- Access logging (7-year retention)
- Breach notification procedures
- Business Associate Agreements

**ABDM:**
- ABHA integration maintained
- Consent management
- Data portability

## 7. Scalability Considerations

### 7.1 Database Optimization

**Indexes:**
```sql
-- Critical indexes
CREATE INDEX idx_vaccinations_facility_date_status 
ON vaccinations(facility_id, vaccination_date, status);

CREATE INDEX idx_facilities_active 
ON facilities(id) WHERE is_active = TRUE;
```

**Partitioning:**
```sql
-- Partition vaccinations by date (for large datasets)
CREATE TABLE vaccinations_2024_01 PARTITION OF vaccinations
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

### 7.2 Caching

**Redis Strategy:**
- Cache analytics for 5 minutes
- Invalidate on new vaccination
- Cache key: `analytics:facility:{id}:{type}:{date}`

### 7.3 API Performance

- Pagination: Default 100, max 1000
- Async operations for all DB queries
- Connection pooling
- Response compression

## 8. Testing Strategy

### 8.1 Unit Tests

```python
def test_super_admin_can_create_facility():
    # Test facility creation
    ...

def test_facility_admin_cannot_access_other_facility():
    # Test access control
    ...
```

### 8.2 Integration Tests

- End-to-end SUPER_ADMIN flow
- End-to-end FACILITY_ADMIN flow
- Multi-facility user switching
- Analytics accuracy

### 8.3 Security Tests

- Unauthorized access attempts
- Cross-facility data access
- Token manipulation
- SQL injection attempts

## 9. Deployment Checklist

### Pre-Deployment
- [ ] Database backup
- [ ] Migration tested on staging
- [ ] Security audit completed
- [ ] Performance testing done

### Deployment
- [ ] Run migration script
- [ ] Create first SUPER_ADMIN
- [ ] Deploy backend code
- [ ] Deploy frontend code
- [ ] Verify all endpoints

### Post-Deployment
- [ ] Monitor error rates
- [ ] Verify analytics accuracy
- [ ] Check performance metrics
- [ ] Collect user feedback

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
**Status:** Ready for Implementation

