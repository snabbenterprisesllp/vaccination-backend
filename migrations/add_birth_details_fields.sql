-- Migration: Add Head Circumference and Gestational Age fields to child_profiles table
-- Date: 2024-01-XX
-- Description: Adds head_circumference, gestational_age_type, and gestational_age_weeks columns

-- Create gestational_age_type enum if it doesn't exist
DO $$ BEGIN
    CREATE TYPE gestationalagetype AS ENUM ('Full term', 'Preterm', 'Post-term');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Add head_circumference column
ALTER TABLE child_profiles
ADD COLUMN IF NOT EXISTS head_circumference VARCHAR(20);

-- Add gestational_age_type column
ALTER TABLE child_profiles
ADD COLUMN IF NOT EXISTS gestational_age_type gestationalagetype;

-- Add gestational_age_weeks column
ALTER TABLE child_profiles
ADD COLUMN IF NOT EXISTS gestational_age_weeks INTEGER;

-- Add comments for documentation
COMMENT ON COLUMN child_profiles.head_circumference IS 'Head circumference at birth in cm';
COMMENT ON COLUMN child_profiles.gestational_age_type IS 'Type of gestational age: Full term, Preterm, or Post-term';
COMMENT ON COLUMN child_profiles.gestational_age_weeks IS 'Gestational age in weeks (typically 20-45 weeks)';

