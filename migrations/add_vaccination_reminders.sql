-- Migration: Add Vaccination Reminders System
-- Description: Creates tables for vaccination reminders and notification preferences

-- Create vaccination_reminders table
CREATE TABLE IF NOT EXISTS vaccination_reminders (
    id SERIAL PRIMARY KEY,
    beneficiary_id INTEGER NOT NULL REFERENCES beneficiaries(id) ON DELETE CASCADE,
    vaccine_code VARCHAR(50) NOT NULL,
    vaccine_name VARCHAR(255) NOT NULL,
    dose_number INTEGER,
    dose_label VARCHAR(100),
    reminder_type VARCHAR(50) NOT NULL CHECK (reminder_type IN ('seven_days_before', 'one_day_before', 'due_date', 'follow_up_missed')),
    scheduled_date DATE NOT NULL,
    scheduled_time TIMESTAMP NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'cancelled', 'failed')),
    notification_channels VARCHAR(255) NOT NULL DEFAULT '["push", "sms", "email"]',
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    vaccination_id INTEGER REFERENCES vaccinations(id) ON DELETE SET NULL,
    is_birth_dose BOOLEAN NOT NULL DEFAULT FALSE,
    due_date_start DATE,
    due_date_end DATE,
    sent_at TIMESTAMP,
    failure_reason TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Indexes for performance
    CONSTRAINT fk_vaccination_reminders_beneficiary FOREIGN KEY (beneficiary_id) REFERENCES beneficiaries(id) ON DELETE CASCADE,
    CONSTRAINT fk_vaccination_reminders_vaccination FOREIGN KEY (vaccination_id) REFERENCES vaccinations(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_vaccination_reminders_beneficiary_id ON vaccination_reminders(beneficiary_id);
CREATE INDEX IF NOT EXISTS idx_vaccination_reminders_vaccine_code ON vaccination_reminders(vaccine_code);
CREATE INDEX IF NOT EXISTS idx_vaccination_reminders_scheduled_date ON vaccination_reminders(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_vaccination_reminders_scheduled_time ON vaccination_reminders(scheduled_time);
CREATE INDEX IF NOT EXISTS idx_vaccination_reminders_status ON vaccination_reminders(status);
CREATE INDEX IF NOT EXISTS idx_vaccination_reminders_is_enabled ON vaccination_reminders(is_enabled);

-- Create notification_preferences table
CREATE TABLE IF NOT EXISTS notification_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    beneficiary_id INTEGER NOT NULL REFERENCES beneficiaries(id) ON DELETE CASCADE,
    vaccine_code VARCHAR(50) NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    notification_channels VARCHAR(255) NOT NULL DEFAULT '["push", "sms", "email"]',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Ensure one preference per user-beneficiary-vaccine combination
    CONSTRAINT unique_user_beneficiary_vaccine UNIQUE (user_id, beneficiary_id, vaccine_code),
    CONSTRAINT fk_notification_preferences_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_notification_preferences_beneficiary FOREIGN KEY (beneficiary_id) REFERENCES beneficiaries(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_notification_preferences_user_id ON notification_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_notification_preferences_beneficiary_id ON notification_preferences(beneficiary_id);
CREATE INDEX IF NOT EXISTS idx_notification_preferences_vaccine_code ON notification_preferences(vaccine_code);

-- Add comments
COMMENT ON TABLE vaccination_reminders IS 'Stores scheduled vaccination reminders with timing and status';
COMMENT ON TABLE notification_preferences IS 'Stores user preferences for vaccine reminders and notification channels';

