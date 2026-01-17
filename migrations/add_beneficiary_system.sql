-- ============================================================================
-- Beneficiary System Migration
-- ============================================================================
-- This migration introduces the beneficiary-based vaccination structure
-- - Creates beneficiaries table
-- - Migrates existing data (users -> adult beneficiaries, child_profiles -> child beneficiaries)
-- - Updates vaccinations and vaccination_schedules to use beneficiary_id
-- ============================================================================

-- Step 1: Create beneficiaries table
CREATE TABLE IF NOT EXISTS beneficiaries (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(10) NOT NULL CHECK (type IN ('ADULT', 'CHILD')),
    first_name VARCHAR(100) NOT NULL,
    middle_name VARCHAR(100),
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender VARCHAR(10) NOT NULL CHECK (gender IN ('male', 'female', 'other')),
    abha_id VARCHAR(50),
    abha_address VARCHAR(100),
    abha_linked BOOLEAN DEFAULT FALSE NOT NULL,
    abha_linked_at TIMESTAMP WITH TIME ZONE,
    qr_code_url VARCHAR(500),
    qr_code_token VARCHAR(100) UNIQUE,
    legacy_user_id INTEGER,
    legacy_child_profile_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_beneficiaries_account_id ON beneficiaries(account_id);
CREATE INDEX IF NOT EXISTS idx_beneficiaries_type ON beneficiaries(type);
CREATE INDEX IF NOT EXISTS idx_beneficiaries_qr_token ON beneficiaries(qr_code_token) WHERE qr_code_token IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_beneficiaries_abha_id ON beneficiaries(abha_id) WHERE abha_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_beneficiaries_legacy_user_id ON beneficiaries(legacy_user_id) WHERE legacy_user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_beneficiaries_legacy_child_profile_id ON beneficiaries(legacy_child_profile_id) WHERE legacy_child_profile_id IS NOT NULL;

-- Step 2: Add beneficiary_id columns to vaccinations and vaccination_schedules
ALTER TABLE vaccinations
ADD COLUMN IF NOT EXISTS beneficiary_id INTEGER REFERENCES beneficiaries(id) ON DELETE CASCADE,
ADD COLUMN IF NOT EXISTS recorded_by_user_id INTEGER REFERENCES users(id);

ALTER TABLE vaccination_schedules
ADD COLUMN IF NOT EXISTS beneficiary_id INTEGER REFERENCES beneficiaries(id) ON DELETE CASCADE;

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_vaccinations_beneficiary_id ON vaccinations(beneficiary_id) WHERE beneficiary_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_vaccinations_recorded_by_user_id ON vaccinations(recorded_by_user_id) WHERE recorded_by_user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_vaccination_schedules_beneficiary_id ON vaccination_schedules(beneficiary_id) WHERE beneficiary_id IS NOT NULL;

-- Step 3: Make child_id nullable in vaccinations and vaccination_schedules (for backward compatibility)
ALTER TABLE vaccinations
ALTER COLUMN child_id DROP NOT NULL;

ALTER TABLE vaccination_schedules
ALTER COLUMN child_id DROP NOT NULL;

-- Step 4: Migrate existing data
-- 4a. Create adult beneficiaries from users (for parents)
INSERT INTO beneficiaries (
    account_id, type, first_name, last_name, date_of_birth, gender,
    abha_id, abha_address, abha_linked, abha_linked_at, legacy_user_id, is_active, created_at, updated_at
)
SELECT 
    id as account_id,
    'ADULT' as type,
    COALESCE(SPLIT_PART(full_name, ' ', 1), 'User') as first_name,
    CASE 
        WHEN POSITION(' ' IN full_name) > 0 THEN SUBSTRING(full_name FROM POSITION(' ' IN full_name) + 1)
        ELSE 'User'
    END as last_name,
    CURRENT_DATE as date_of_birth,  -- Default, should be updated later
    'OTHER'::gender as gender,  -- Default, should be updated later
    abha_number as abha_id,
    abha_address,
    COALESCE(abha_linked, FALSE) as abha_linked,
    abha_linked_at,
    id as legacy_user_id,
    TRUE as is_active,
    created_at,
    updated_at
FROM users
WHERE login_type = 'INDIVIDUAL'  -- Only individual users (parents)
ON CONFLICT DO NOTHING;

-- 4b. Create child beneficiaries from child_profiles
INSERT INTO beneficiaries (
    account_id, type, first_name, middle_name, last_name, date_of_birth, gender,
    abha_id, abha_address, abha_linked, abha_linked_at,
    qr_code_url, qr_code_token, legacy_child_profile_id, is_active, created_at, updated_at
)
SELECT 
    parent_id as account_id,
    'CHILD' as type,
    first_name,
    middle_name,
    last_name,
    date_of_birth,
    gender::gender,
    abha_number as abha_id,
    abha_address,
    abha_linked,
    abha_linked_at,
    qr_code_url,
    qr_code_token,
    id as legacy_child_profile_id,
    is_active,
    created_at,
    updated_at
FROM child_profiles
WHERE is_active = TRUE
ON CONFLICT DO NOTHING;

-- Step 5: Update vaccinations to link to beneficiaries
-- 5a. Link vaccinations to child beneficiaries
UPDATE vaccinations v
SET beneficiary_id = b.id
FROM beneficiaries b
WHERE v.child_id = b.legacy_child_profile_id
  AND b.type = 'CHILD'
  AND v.beneficiary_id IS NULL;

-- Step 6: Update vaccination_schedules to link to beneficiaries
UPDATE vaccination_schedules vs
SET beneficiary_id = b.id
FROM beneficiaries b
WHERE vs.child_id = b.legacy_child_profile_id
  AND b.type = 'CHILD'
  AND vs.beneficiary_id IS NULL;

-- ============================================================================
-- NOTES:
-- - Legacy child_id columns remain for backward compatibility
-- - New vaccinations should use beneficiary_id
-- - QR codes for children are preserved in beneficiaries table
-- - Adult beneficiaries are created from users, but date_of_birth and gender
--   should be updated by users in their profile
-- ============================================================================

