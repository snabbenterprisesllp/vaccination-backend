-- Script to assign a user to a facility
-- Usage: Run this script to assign user with mobile_number '7680972845' to facility 'FAC-B6B48A218C8E'

-- Step 1: Check if user exists
SELECT 
    id,
    mobile_number,
    full_name,
    email,
    login_type,
    role,
    created_at
FROM users
WHERE mobile_number = '7680972845';

-- Step 2: Check if facility exists
SELECT 
    id,
    name,
    facility_id,
    facility_code,
    is_active
FROM facilities
WHERE facility_id = 'FAC-B6B48A218C8E';

-- Step 3: Check if user already has facility assignment
SELECT 
    fu.id,
    fu.user_id,
    fu.facility_id,
    fu.facility_role,
    fu.is_active,
    u.mobile_number,
    f.name as facility_name
FROM facility_users fu
JOIN users u ON fu.user_id = u.id
JOIN facilities f ON fu.facility_id = f.id
WHERE u.mobile_number = '7680972845';

-- Step 4: Assign user to facility (if not already assigned)
-- This will:
-- 1. Get the user_id from users table
-- 2. Get the facility id from facilities table
-- 3. Create a FacilityUser entry with role 'doctor' (change as needed)
-- 4. Set login_type to HOSPITAL if not already set

DO $$
DECLARE
    v_user_id INTEGER;
    v_facility_id INTEGER;
    v_existing_assignment INTEGER;
BEGIN
    -- Get user_id
    SELECT id INTO v_user_id
    FROM users
    WHERE mobile_number = '7680972845';
    
    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'User with mobile number 7680972845 not found';
    END IF;
    
    -- Get facility_id
    SELECT id INTO v_facility_id
    FROM facilities
    WHERE facility_id = 'FAC-B6B48A218C8E';
    
    IF v_facility_id IS NULL THEN
        RAISE EXCEPTION 'Facility with facility_id FAC-B6B48A218C8E not found';
    END IF;
    
    -- Check if already assigned
    SELECT id INTO v_existing_assignment
    FROM facility_users
    WHERE user_id = v_user_id 
      AND facility_id = v_facility_id
      AND is_active = TRUE;
    
    IF v_existing_assignment IS NOT NULL THEN
        RAISE NOTICE 'User is already assigned to this facility (assignment_id: %)', v_existing_assignment;
    ELSE
        -- Update user login_type to HOSPITAL if not already
        UPDATE users
        SET login_type = 'hospital'
        WHERE id = v_user_id AND (login_type IS NULL OR login_type != 'hospital');
        
        -- Create facility_user assignment
        INSERT INTO facility_users (user_id, facility_id, facility_role, is_active, created_at, updated_at)
        VALUES (
            v_user_id,
            v_facility_id,
            'doctor',  -- Change to 'staff' or 'facility_admin' as needed
            TRUE,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        );
        
        RAISE NOTICE 'User % assigned to facility % with role doctor', v_user_id, v_facility_id;
    END IF;
END $$;

-- Step 5: Verify the assignment
SELECT 
    fu.id as assignment_id,
    u.mobile_number,
    u.full_name,
    f.name as facility_name,
    f.facility_id,
    fu.facility_role,
    fu.is_active,
    fu.created_at
FROM facility_users fu
JOIN users u ON fu.user_id = u.id
JOIN facilities f ON fu.facility_id = f.id
WHERE u.mobile_number = '7680972845'
  AND f.facility_id = 'FAC-B6B48A218C8E';

