-- ============================================================================
-- Multi-Facility RBAC System Migration
-- ============================================================================
-- This migration adds:
-- 1. facilities table (extends hospital concept)
-- 2. facility_users table (maps users to facilities with roles)
-- 3. SUPER_ADMIN, FACILITY_ADMIN, DOCTOR, STAFF roles
-- 4. facility_id to vaccinations table
-- ============================================================================

-- ============================================================================
-- FACILITIES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS facilities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    facility_id VARCHAR(50) UNIQUE NOT NULL,  -- Globally unique identifier (UUID-based)
    facility_code VARCHAR(50),  -- Optional internal code
    facility_type VARCHAR(50) NOT NULL,
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    pincode VARCHAR(10) NOT NULL,
    country VARCHAR(100) DEFAULT 'India' NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    website VARCHAR(255),
    latitude FLOAT,
    longitude FLOAT,
    registration_number VARCHAR(100),
    abha_registered BOOLEAN DEFAULT FALSE,
    abha_facility_id VARCHAR(100),
    logo_url VARCHAR(500),
    services_offered JSONB,
    vaccines_available JSONB,
    operating_hours JSONB,
    verified BOOLEAN DEFAULT FALSE,
    verified_at VARCHAR(50),
    verified_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    legacy_hospital_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_facilities_name ON facilities(name);
CREATE INDEX IF NOT EXISTS idx_facilities_facility_id ON facilities(facility_id);  -- Unique identifier
CREATE INDEX IF NOT EXISTS idx_facilities_code ON facilities(facility_code) WHERE facility_code IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_facilities_city ON facilities(city);
CREATE INDEX IF NOT EXISTS idx_facilities_state ON facilities(state);
CREATE INDEX IF NOT EXISTS idx_facilities_pincode ON facilities(pincode);
CREATE INDEX IF NOT EXISTS idx_facilities_active ON facilities(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_facilities_registration ON facilities(registration_number) WHERE registration_number IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_facilities_abha ON facilities(abha_facility_id) WHERE abha_facility_id IS NOT NULL;

-- ============================================================================
-- FACILITY USERS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS facility_users (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    facility_id INTEGER REFERENCES facilities(id) ON DELETE CASCADE,
    facility_role VARCHAR(20) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    assigned_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    CONSTRAINT chk_facility_role CHECK (facility_role IN ('super_admin', 'facility_admin', 'doctor', 'staff'))
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_facility_users_user_id ON facility_users(user_id);
CREATE INDEX IF NOT EXISTS idx_facility_users_facility_id ON facility_users(facility_id);
CREATE INDEX IF NOT EXISTS idx_facility_users_active ON facility_users(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_facility_users_role ON facility_users(facility_role);

-- Create unique constraint: one active assignment per user per facility
CREATE UNIQUE INDEX IF NOT EXISTS idx_facility_users_unique_active 
ON facility_users(user_id, facility_id) 
WHERE is_active = TRUE AND facility_id IS NOT NULL;

-- ============================================================================
-- ADD FACILITY_ID TO VACCINATIONS TABLE
-- ============================================================================

ALTER TABLE vaccinations
ADD COLUMN IF NOT EXISTS facility_id INTEGER REFERENCES facilities(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_vaccinations_facility_id ON vaccinations(facility_id) WHERE facility_id IS NOT NULL;

-- Migrate existing hospital_id to facility_id (if hospitals table exists)
DO $$
DECLARE
    hosp_rec RECORD;
    fac_id INTEGER;
BEGIN
    -- Check if hospitals table exists
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'hospitals') THEN
        -- Migrate hospital_id to facility_id for vaccinations
        FOR hosp_rec IN 
            SELECT DISTINCT hospital_id 
            FROM vaccinations 
            WHERE hospital_id IS NOT NULL
        LOOP
            -- Try to find or create facility from hospital
            SELECT id INTO fac_id 
            FROM facilities 
            WHERE legacy_hospital_id = hosp_rec.hospital_id 
            LIMIT 1;
            
            -- If not found, try to create from hospital
            IF fac_id IS NULL THEN
                INSERT INTO facilities (
                    name, facility_id, facility_code, facility_type, address, city, state, pincode, country,
                    legacy_hospital_id, is_active
                )
                SELECT 
                    name,
                    'FAC-' || UPPER(SUBSTRING(MD5(hospital_code::text) FROM 1 FOR 12)),  -- Generate unique facility_id
                    hospital_code || '_facility', 
                    hospital_type,
                    address, city, state, pincode,
                    'India',  -- Default country
                    id,
                    TRUE
                FROM hospitals
                WHERE id = hosp_rec.hospital_id
                RETURNING id INTO fac_id;
            END IF;
            
            -- Update vaccinations
            IF fac_id IS NOT NULL THEN
                UPDATE vaccinations
                SET facility_id = fac_id
                WHERE hospital_id = hosp_rec.hospital_id
                AND facility_id IS NULL;
            END IF;
        END LOOP;
    END IF;
END $$;

-- ============================================================================
-- MIGRATE EXISTING HOSPITAL USERS TO FACILITY USERS
-- ============================================================================

DO $$
DECLARE
    hosp_user_rec RECORD;
    fac_id INTEGER;
BEGIN
    -- Check if hospital_users table exists
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'hospital_users') THEN
        FOR hosp_user_rec IN 
            SELECT hu.*, h.id as hospital_id
            FROM hospital_users hu
            JOIN hospitals h ON hu.hospital_id = h.id
            WHERE hu.is_active = TRUE
        LOOP
            -- Find or create facility
            SELECT id INTO fac_id
            FROM facilities
            WHERE legacy_hospital_id = hosp_user_rec.hospital_id
            LIMIT 1;
            
            -- If not found, create facility from hospital
            IF fac_id IS NULL THEN
                INSERT INTO facilities (
                    name, facility_id, facility_code, facility_type, address, city, state, pincode, country,
                    legacy_hospital_id, is_active
                )
                SELECT 
                    name,
                    'FAC-' || UPPER(SUBSTRING(MD5(hospital_code::text) FROM 1 FOR 12)),  -- Generate unique facility_id
                    hospital_code || '_facility', 
                    hospital_type,
                    address, city, state, pincode,
                    'India',  -- Default country
                    id,
                    TRUE
                FROM hospitals
                WHERE id = hosp_user_rec.hospital_id
                RETURNING id INTO fac_id;
            END IF;
            
            -- Map hospital roles to facility roles
            -- admin -> facility_admin
            -- doctor -> doctor
            -- staff -> staff
            INSERT INTO facility_users (
                user_id, facility_id, facility_role, is_active, assigned_by
            )
            VALUES (
                hosp_user_rec.user_id,
                fac_id,
                (CASE hosp_user_rec.hospital_role::text
                    WHEN 'ADMIN' THEN 'FACILITY_ADMIN'
                    WHEN 'DOCTOR' THEN 'DOCTOR'
                    WHEN 'STAFF' THEN 'STAFF'
                    ELSE 'STAFF'  -- Default fallback
                END)::facilityrole,
                TRUE,
                NULL
            )
            ON CONFLICT DO NOTHING;
        END LOOP;
    END IF;
END $$;

-- ============================================================================
-- GENERATE FACILITY_ID FOR EXISTING FACILITIES (if any created without facility_id)
-- ============================================================================
-- Update any facilities that don't have facility_id
UPDATE facilities
SET facility_id = 'FAC-' || UPPER(SUBSTRING(MD5(id::text || name) FROM 1 FOR 12))
WHERE facility_id IS NULL OR facility_id = '';

-- ============================================================================
-- CREATE FIRST SUPER_ADMIN (if needed)
-- ============================================================================
-- Note: This should be done manually or via a script after migration
-- Example:
-- INSERT INTO facility_users (user_id, facility_id, facility_role, is_active)
-- VALUES (<super_admin_user_id>, NULL, 'super_admin', TRUE);

-- ============================================================================
-- NOTES:
-- - facilities table extends hospital concept for multi-facility support
-- - facility_users enables multi-facility assignments (one user, multiple facilities)
-- - SUPER_ADMIN has facility_id=NULL (global scope)
-- - FACILITY_ADMIN, DOCTOR, STAFF are facility-scoped
-- - Existing hospital_users are migrated to facility_users
-- - Existing hospital_id in vaccinations is migrated to facility_id
-- ============================================================================

