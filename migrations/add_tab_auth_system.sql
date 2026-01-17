-- ============================================================================
-- Tab-based Authentication System Migration
-- ============================================================================
-- This migration adds:
-- 1. login_type to users table (INDIVIDUAL | HOSPITAL)
-- 2. hospital_users table (maps users to hospitals with roles)
-- ============================================================================

-- Add login_type to users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS login_type VARCHAR(20) DEFAULT 'individual' NOT NULL;

-- Create enum type for login_type (PostgreSQL)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'logintype') THEN
        CREATE TYPE logintype AS ENUM ('individual', 'hospital');
    END IF;
END $$;

-- Update column to use enum (if not already)
-- Note: This may require data migration if column already exists
DO $$
BEGIN
    -- Check if column exists and is not already enum
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'login_type' 
        AND data_type != 'USER-DEFINED'
    ) THEN
        -- Convert existing data
        ALTER TABLE users 
        ALTER COLUMN login_type TYPE logintype 
        USING CASE 
            WHEN login_type = 'individual' OR login_type IS NULL THEN 'individual'::logintype
            WHEN login_type = 'hospital' THEN 'hospital'::logintype
            ELSE 'individual'::logintype
        END;
    ELSIF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = 'login_type'
    ) THEN
        -- Add new column with enum
        ALTER TABLE users 
        ADD COLUMN login_type logintype DEFAULT 'individual' NOT NULL;
    END IF;
END $$;

-- Create index on login_type
CREATE INDEX IF NOT EXISTS idx_users_login_type ON users(login_type);

-- Set login_type for existing users based on role
UPDATE users 
SET login_type = CASE 
    WHEN role = 'hospital' THEN 'hospital'::logintype
    ELSE 'individual'::logintype
END
WHERE login_type IS NULL OR login_type = 'individual';

-- ============================================================================
-- Hospital Users Mapping Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS hospital_users (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    hospital_id INTEGER NOT NULL REFERENCES hospitals(id) ON DELETE CASCADE,
    hospital_role VARCHAR(20) NOT NULL DEFAULT 'staff',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    CONSTRAINT fk_hospital_users_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_hospital_users_hospital FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE CASCADE,
    CONSTRAINT chk_hospital_role CHECK (hospital_role IN ('admin', 'doctor', 'staff'))
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_hospital_users_user_id ON hospital_users(user_id);
CREATE INDEX IF NOT EXISTS idx_hospital_users_hospital_id ON hospital_users(hospital_id);
CREATE INDEX IF NOT EXISTS idx_hospital_users_active ON hospital_users(is_active) WHERE is_active = TRUE;

-- Create unique constraint: one active assignment per user per hospital
CREATE UNIQUE INDEX IF NOT EXISTS idx_hospital_users_unique_active 
ON hospital_users(user_id, hospital_id) 
WHERE is_active = TRUE;

-- Migrate existing hospital users (if any)
-- Users with role='hospital' and hospital_id set should get hospital_user entry
DO $$
DECLARE
    rec RECORD;
    hosp_id INTEGER;
BEGIN
    FOR rec IN 
        SELECT id, hospital_id 
        FROM users 
        WHERE role = 'hospital' 
        AND hospital_id IS NOT NULL
        AND login_type = 'hospital'
    LOOP
        -- Try to find hospital by code (hospital_id is string in old schema)
        SELECT id INTO hosp_id 
        FROM hospitals 
        WHERE hospital_code = rec.hospital_id::TEXT 
        LIMIT 1;
        
        -- If hospital found, create hospital_user entry
        IF hosp_id IS NOT NULL THEN
            INSERT INTO hospital_users (user_id, hospital_id, hospital_role, is_active)
            VALUES (rec.id, hosp_id, 'admin', TRUE)
            ON CONFLICT DO NOTHING;
        END IF;
    END LOOP;
END $$;

-- ============================================================================
-- NOTES:
-- - login_type determines authentication context (INDIVIDUAL vs HOSPITAL)
-- - hospital_users table maps users to hospitals with roles (ADMIN, DOCTOR, STAFF)
-- - Existing users are set to login_type=INDIVIDUAL (except those with role=HOSPITAL)
-- - Existing hospital users (role=HOSPITAL) are migrated to hospital_users table
-- ============================================================================

