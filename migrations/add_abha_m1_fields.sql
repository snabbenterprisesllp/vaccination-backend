-- ============================================================================
-- ABHA M1 Database Migration
-- ============================================================================
-- This migration adds ABHA M1 fields to users and child_profiles tables
-- M1 SCOPE: Only ABHA linking fields, NO M2/M3 fields
-- ============================================================================

-- Add ABHA M1 fields to users table (for parent linking)
ALTER TABLE users
ADD COLUMN IF NOT EXISTS abha_number VARCHAR(50),
ADD COLUMN IF NOT EXISTS abha_address VARCHAR(100),
ADD COLUMN IF NOT EXISTS abha_linked BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS abha_linked_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS guardian_person_id INTEGER;

-- Add index for ABHA number lookups
CREATE INDEX IF NOT EXISTS idx_users_abha_number ON users(abha_number) WHERE abha_number IS NOT NULL;

-- Add ABHA M1 fields to child_profiles table (for child linking)
ALTER TABLE child_profiles
ADD COLUMN IF NOT EXISTS abha_address VARCHAR(100),
ADD COLUMN IF NOT EXISTS abha_linked BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS abha_linked_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS guardian_person_id INTEGER REFERENCES users(id);

-- Add index for ABHA number lookups (abha_number already exists)
CREATE INDEX IF NOT EXISTS idx_child_profiles_abha_linked ON child_profiles(abha_linked) WHERE abha_linked = TRUE;

-- Add foreign key constraint for guardian_person_id in child_profiles
-- (if not already exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'child_profiles_guardian_person_id_fkey'
    ) THEN
        ALTER TABLE child_profiles
        ADD CONSTRAINT child_profiles_guardian_person_id_fkey
        FOREIGN KEY (guardian_person_id) REFERENCES users(id);
    END IF;
END $$;

-- ============================================================================
-- NOTES:
-- - abha_number is stored masked/encrypted (security best practice)
-- - Never store Aadhaar numbers
-- - Never store full ABDM API responses
-- - guardian_person_id tracks which parent linked ABHA for a child
-- ============================================================================

