-- Migration: Add Vitals fields to vaccinations table
-- Date: 2024-01-XX
-- Description: Adds vitals at time of vaccination (temperature, weight, height, pulse rate, oxygen saturation)

-- Add vitals fields to vaccinations table
ALTER TABLE vaccinations
ADD COLUMN IF NOT EXISTS temperature VARCHAR(20),
ADD COLUMN IF NOT EXISTS temperature_unit VARCHAR(2),
ADD COLUMN IF NOT EXISTS weight VARCHAR(20),
ADD COLUMN IF NOT EXISTS height_length VARCHAR(20),
ADD COLUMN IF NOT EXISTS pulse_rate INTEGER,
ADD COLUMN IF NOT EXISTS oxygen_saturation VARCHAR(10);

-- Add comments for documentation
COMMENT ON COLUMN vaccinations.temperature IS 'Body temperature at time of vaccination';
COMMENT ON COLUMN vaccinations.temperature_unit IS 'Temperature unit: C (Celsius) or F (Fahrenheit)';
COMMENT ON COLUMN vaccinations.weight IS 'Weight in kilograms at time of vaccination';
COMMENT ON COLUMN vaccinations.height_length IS 'Height/Length in cm at time of vaccination';
COMMENT ON COLUMN vaccinations.pulse_rate IS 'Pulse rate in bpm at time of vaccination';
COMMENT ON COLUMN vaccinations.oxygen_saturation IS 'Oxygen saturation (SpO2) percentage at time of vaccination';

