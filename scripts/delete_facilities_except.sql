-- Script to delete all facilities except the one with facility_id 'FAC-B6B48A218C8E'
-- 
-- Usage:
--   docker-compose exec postgres psql -U postgres -d vaccination_db -f scripts/delete_facilities_except.sql
--   OR
--   psql -U postgres -d vaccination_db -f scripts/delete_facilities_except.sql

BEGIN;

-- Show facilities that will be kept
SELECT 'Facility to KEEP:' as info, id, facility_id, name 
FROM facilities 
WHERE facility_id = 'FAC-B6B48A218C8E';

-- Show facilities that will be deleted
SELECT 'Facilities to DELETE:' as info, id, facility_id, name 
FROM facilities 
WHERE facility_id != 'FAC-B6B48A218C8E';

-- Count related records
SELECT 
    'Facility Users to DELETE:' as info,
    COUNT(*) as count
FROM facility_users fu
JOIN facilities f ON fu.facility_id = f.id
WHERE f.facility_id != 'FAC-B6B48A218C8E';

SELECT 
    'Vaccinations (facility_id will be set to NULL):' as info,
    COUNT(*) as count
FROM vaccinations v
JOIN facilities f ON v.facility_id = f.id
WHERE f.facility_id != 'FAC-B6B48A218C8E';

-- Step 1: Delete facility_users for facilities to be deleted
DELETE FROM facility_users
WHERE facility_id IN (
    SELECT id FROM facilities WHERE facility_id != 'FAC-B6B48A218C8E'
);

-- Step 2: Set facility_id to NULL for vaccinations (preserve vaccination records)
UPDATE vaccinations
SET facility_id = NULL
WHERE facility_id IN (
    SELECT id FROM facilities WHERE facility_id != 'FAC-B6B48A218C8E'
);

-- Step 3: Delete facilities (except the one to keep)
DELETE FROM facilities
WHERE facility_id != 'FAC-B6B48A218C8E';

-- Show remaining facilities
SELECT 'Remaining facilities:' as info, id, facility_id, name 
FROM facilities;

COMMIT;

-- Verify deletion
SELECT 
    'Verification - Total facilities:' as info,
    COUNT(*) as count
FROM facilities;


