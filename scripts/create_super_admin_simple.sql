-- Quick script to create a SUPER_ADMIN user
-- Run this in PostgreSQL to create a SUPER_ADMIN

-- Step 1: Create or use existing user
-- Replace these values with your desired credentials
DO $$
DECLARE
    v_user_id INTEGER;
    v_mobile_number VARCHAR(20) := '9876543210';  -- CHANGE THIS
    v_full_name VARCHAR(255) := 'Super Admin';      -- CHANGE THIS
    v_email VARCHAR(255) := 'admin@example.com';     -- CHANGE THIS (optional)
BEGIN
    -- Check if user exists
    SELECT id INTO v_user_id
    FROM users
    WHERE mobile_number = v_mobile_number;
    
    -- If user doesn't exist, create it
    IF v_user_id IS NULL THEN
        INSERT INTO users (
            mobile_number,
            full_name,
            email,
            role,
            login_type,
            consent_given,
            consent_timestamp,
            is_active,
            created_at,
            updated_at
        ) VALUES (
            v_mobile_number,
            v_full_name,
            v_email,
            'HOSPITAL',
            'HOSPITAL',
            'Y',
            NOW()::text,
            true,
            NOW(),
            NOW()
        )
        RETURNING id INTO v_user_id;
        
        RAISE NOTICE 'Created new user with ID: %', v_user_id;
    ELSE
        RAISE NOTICE 'Using existing user with ID: %', v_user_id;
    END IF;
    
    -- Check if SUPER_ADMIN already exists
    IF EXISTS (
        SELECT 1 FROM facility_users
        WHERE user_id = v_user_id
        AND facility_role = 'SUPER_ADMIN'
        AND is_active = true
    ) THEN
        RAISE NOTICE 'User already has SUPER_ADMIN role';
    ELSE
        -- Create SUPER_ADMIN assignment
        INSERT INTO facility_users (
            user_id,
            facility_id,
            facility_role,
            is_active,
            created_at,
            updated_at
        ) VALUES (
            v_user_id,
            NULL,  -- NULL for SUPER_ADMIN (global scope)
            'SUPER_ADMIN',
            true,
            NOW(),
            NOW()
        );
        
        RAISE NOTICE 'SUPER_ADMIN role assigned successfully!';
        RAISE NOTICE 'User ID: %', v_user_id;
        RAISE NOTICE 'Mobile: %', v_mobile_number;
        RAISE NOTICE 'Name: %', v_full_name;
    END IF;
END $$;

-- Verify the SUPER_ADMIN was created
SELECT 
    u.id,
    u.mobile_number,
    u.full_name,
    u.email,
    fu.facility_role,
    fu.is_active,
    fu.created_at
FROM users u
JOIN facility_users fu ON u.id = fu.user_id
WHERE fu.facility_role = 'SUPER_ADMIN'
AND fu.is_active = true;

