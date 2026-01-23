-- Preview script: Shows which facilities will be deleted
-- This script does NOT delete anything, it only shows what would be deleted
-- 
-- Usage:
--   docker-compose exec postgres psql -U postgres -d vaccination_db -f scripts/preview_facilities_to_delete.sql

-- Show facility that will be KEPT
SELECT 
    '✅ FACILITY TO KEEP' as action,
    id,
    facility_id,
    name,
    facility_type,
    city,
    state,
    is_active,
    created_at
FROM facilities 
WHERE facility_id = 'FAC-B6B48A218C8E';

-- Show facilities that will be DELETED
SELECT 
    '❌ FACILITIES TO DELETE' as action,
    id,
    facility_id,
    name,
    facility_type,
    city,
    state,
    is_active,
    created_at
FROM facilities 
WHERE facility_id != 'FAC-B6B48A218C8E'
ORDER BY id;

-- Count summary
SELECT 
    '📊 SUMMARY' as info,
    (SELECT COUNT(*) FROM facilities WHERE facility_id = 'FAC-B6B48A218C8E') as facilities_to_keep,
    (SELECT COUNT(*) FROM facilities WHERE facility_id != 'FAC-B6B48A218C8E') as facilities_to_delete,
    (SELECT COUNT(*) FROM facilities) as total_facilities;

-- Show related records that will be affected
SELECT 
    '👥 FACILITY USERS TO DELETE' as info,
    fu.id as facility_user_id,
    fu.user_id,
    u.full_name,
    u.mobile_number,
    fu.facility_role,
    f.facility_id,
    f.name as facility_name
FROM facility_users fu
JOIN facilities f ON fu.facility_id = f.id
JOIN users u ON fu.user_id = u.id
WHERE f.facility_id != 'FAC-B6B48A218C8E'
ORDER BY f.id, fu.id;

-- Count facility users
SELECT 
    '📊 FACILITY USERS COUNT' as info,
    COUNT(*) as total_facility_users_to_delete
FROM facility_users fu
JOIN facilities f ON fu.facility_id = f.id
WHERE f.facility_id != 'FAC-B6B48A218C8E';

-- Show vaccinations that will have facility_id set to NULL
SELECT 
    '💉 VACCINATIONS (facility_id will be set to NULL)' as info,
    v.id as vaccination_id,
    v.vaccine_name,
    v.vaccination_date,
    v.status,
    f.facility_id,
    f.name as facility_name
FROM vaccinations v
JOIN facilities f ON v.facility_id = f.id
WHERE f.facility_id != 'FAC-B6B48A218C8E'
ORDER BY v.vaccination_date DESC
LIMIT 50;  -- Show first 50

-- Count vaccinations
SELECT 
    '📊 VACCINATIONS COUNT' as info,
    COUNT(*) as total_vaccinations_to_update
FROM vaccinations v
JOIN facilities f ON v.facility_id = f.id
WHERE f.facility_id != 'FAC-B6B48A218C8E';


