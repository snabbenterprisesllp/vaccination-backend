-- Migration: Add Birth Vaccination fields to child_profiles table
-- Date: 2024-01-XX
-- Description: Adds birth vaccination status, dates, batch numbers, and proof document reference

-- Create birth_vaccination_status enum if it doesn't exist
DO $$ BEGIN
    CREATE TYPE birthvaccinationstatus AS ENUM ('Given', 'Not Given');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Add BCG vaccination fields
ALTER TABLE child_profiles
ADD COLUMN IF NOT EXISTS bcg_status birthvaccinationstatus,
ADD COLUMN IF NOT EXISTS bcg_date DATE,
ADD COLUMN IF NOT EXISTS bcg_batch_number VARCHAR(50);

-- Add OPV-0 vaccination fields
ALTER TABLE child_profiles
ADD COLUMN IF NOT EXISTS opv0_status birthvaccinationstatus,
ADD COLUMN IF NOT EXISTS opv0_date DATE,
ADD COLUMN IF NOT EXISTS opv0_batch_number VARCHAR(50);

-- Add Hepatitis-B birth dose vaccination fields
ALTER TABLE child_profiles
ADD COLUMN IF NOT EXISTS hepatitis_b_birth_status birthvaccinationstatus,
ADD COLUMN IF NOT EXISTS hepatitis_b_birth_date DATE,
ADD COLUMN IF NOT EXISTS hepatitis_b_birth_batch_number VARCHAR(50);

-- Add birth vaccination proof document reference
ALTER TABLE child_profiles
ADD COLUMN IF NOT EXISTS birth_vaccination_proof_document_id INTEGER REFERENCES documents(id);

-- Add comments for documentation
COMMENT ON COLUMN child_profiles.bcg_status IS 'BCG vaccination status at birth';
COMMENT ON COLUMN child_profiles.bcg_date IS 'BCG vaccination date';
COMMENT ON COLUMN child_profiles.bcg_batch_number IS 'BCG vaccine batch number';
COMMENT ON COLUMN child_profiles.opv0_status IS 'OPV-0 vaccination status at birth';
COMMENT ON COLUMN child_profiles.opv0_date IS 'OPV-0 vaccination date';
COMMENT ON COLUMN child_profiles.opv0_batch_number IS 'OPV-0 vaccine batch number';
COMMENT ON COLUMN child_profiles.hepatitis_b_birth_status IS 'Hepatitis-B birth dose vaccination status';
COMMENT ON COLUMN child_profiles.hepatitis_b_birth_date IS 'Hepatitis-B birth dose vaccination date';
COMMENT ON COLUMN child_profiles.hepatitis_b_birth_batch_number IS 'Hepatitis-B birth dose vaccine batch number';
COMMENT ON COLUMN child_profiles.birth_vaccination_proof_document_id IS 'Reference to document containing hospital stamp/proof';

