# SQL Queries Reference - Daily Vaccination Analytics

## Overview

This document provides optimized SQL queries for daily vaccination analytics used in the multi-facility RBAC system.

## Index Strategy

### Critical Indexes

```sql
-- Composite index for facility + date queries
CREATE INDEX idx_vaccinations_facility_date_status 
ON vaccinations(facility_id, vaccination_date, status)
WHERE facility_id IS NOT NULL;

-- Index for date range queries
CREATE INDEX idx_vaccinations_date_facility 
ON vaccinations(vaccination_date, facility_id) 
WHERE status = 'completed' AND facility_id IS NOT NULL;

-- Index for facility status queries
CREATE INDEX idx_vaccinations_facility_status 
ON vaccinations(facility_id, status) 
WHERE facility_id IS NOT NULL;
```

## Query Examples

### 1. Vaccines Administered Today (Per Facility)

**Purpose:** Get daily vaccination count per facility for today

```sql
SELECT 
    f.facility_id,
    f.name AS facility_name,
    f.city,
    f.state,
    COUNT(v.id) AS vaccinations_today
FROM facilities f
LEFT JOIN vaccinations v ON v.facility_id = f.id
    AND v.vaccination_date = CURRENT_DATE
    AND v.status = 'completed'
WHERE f.is_active = TRUE
GROUP BY f.id, f.facility_id, f.name, f.city, f.state
ORDER BY vaccinations_today DESC;
```

**Performance:** Uses index `idx_vaccinations_facility_date_status`

---

### 2. Vaccines Administered Per Day (Date Filter)

**Purpose:** Get vaccination counts per facility for a date range

```sql
SELECT 
    v.vaccination_date,
    f.facility_id,
    f.name AS facility_name,
    COUNT(v.id) AS vaccination_count
FROM vaccinations v
JOIN facilities f ON v.facility_id = f.id
WHERE v.vaccination_date BETWEEN :start_date AND :end_date
    AND v.status = 'completed'
    AND f.is_active = TRUE
GROUP BY v.vaccination_date, f.id, f.facility_id, f.name
ORDER BY v.vaccination_date DESC, vaccination_count DESC;
```

**Parameters:**
- `start_date`: Start date (e.g., '2024-01-01')
- `end_date`: End date (e.g., '2024-01-31')

**Performance:** Uses index `idx_vaccinations_date_facility`

---

### 3. Total Vaccinations Per Facility

**Purpose:** Get summary statistics per facility

```sql
SELECT 
    f.facility_id,
    f.name AS facility_name,
    f.city,
    f.state,
    COUNT(CASE WHEN v.status = 'completed' THEN 1 END) AS completed,
    COUNT(CASE WHEN v.status = 'pending' THEN 1 END) AS pending,
    COUNT(CASE WHEN v.status = 'scheduled' THEN 1 END) AS scheduled,
    COUNT(CASE WHEN v.status = 'missed' THEN 1 END) AS missed,
    COUNT(v.id) AS total
FROM facilities f
LEFT JOIN vaccinations v ON v.facility_id = f.id
WHERE f.is_active = TRUE
GROUP BY f.id, f.facility_id, f.name, f.city, f.state
ORDER BY completed DESC;
```

---

### 4. Weekly Trends (Last N Weeks)

**Purpose:** Get weekly aggregation for trend analysis

```sql
SELECT 
    DATE_TRUNC('week', v.vaccination_date) AS week_start,
    f.facility_id,
    f.name AS facility_name,
    COUNT(v.id) AS vaccination_count
FROM vaccinations v
JOIN facilities f ON v.facility_id = f.id
WHERE v.vaccination_date >= CURRENT_DATE - INTERVAL ':weeks weeks'
    AND v.status = 'completed'
    AND f.is_active = TRUE
GROUP BY DATE_TRUNC('week', v.vaccination_date), f.facility_id, f.name
ORDER BY week_start DESC, f.facility_id;
```

**Parameters:**
- `weeks`: Number of weeks (e.g., 4)

---

### 5. Monthly Trends

**Purpose:** Get monthly aggregation

```sql
SELECT 
    DATE_TRUNC('month', v.vaccination_date) AS month_start,
    f.facility_id,
    f.name AS facility_name,
    COUNT(v.id) AS vaccination_count
FROM vaccinations v
JOIN facilities f ON v.facility_id = f.id
WHERE v.vaccination_date >= CURRENT_DATE - INTERVAL ':months months'
    AND v.status = 'completed'
    AND f.is_active = TRUE
GROUP BY DATE_TRUNC('month', v.vaccination_date), f.facility_id, f.name
ORDER BY month_start DESC, f.facility_id;
```

---

### 6. Vaccine-Type Distribution (Per Facility)

**Purpose:** Get breakdown by vaccine type

```sql
SELECT 
    f.facility_id,
    f.name AS facility_name,
    vm.vaccine_name,
    COUNT(v.id) AS count,
    ROUND(
        COUNT(v.id) * 100.0 / 
        NULLIF(SUM(COUNT(v.id)) OVER (PARTITION BY f.id), 0), 
        2
    ) AS percentage
FROM vaccinations v
JOIN facilities f ON v.facility_id = f.id
JOIN vaccine_master vm ON v.vaccine_id = vm.id
WHERE v.status = 'completed'
    AND f.is_active = TRUE
    AND v.vaccination_date >= :start_date
    AND v.vaccination_date <= :end_date
GROUP BY f.id, f.facility_id, f.name, vm.id, vm.vaccine_name
ORDER BY f.facility_id, count DESC;
```

---

### 7. Daily Vaccination Count (Last 30 Days) - Global

**Purpose:** Get daily totals across all facilities

```sql
SELECT 
    v.vaccination_date,
    COUNT(v.id) AS daily_count,
    COUNT(DISTINCT v.facility_id) AS facilities_active,
    COUNT(DISTINCT v.vaccine_id) AS vaccine_types_used
FROM vaccinations v
JOIN facilities f ON v.facility_id = f.id
WHERE v.vaccination_date >= CURRENT_DATE - INTERVAL '30 days'
    AND v.status = 'completed'
    AND f.is_active = TRUE
GROUP BY v.vaccination_date
ORDER BY v.vaccination_date DESC;
```

---

### 8. Facility Performance Comparison

**Purpose:** Compare facilities by performance metrics

```sql
SELECT 
    f.facility_id,
    f.name AS facility_name,
    f.city,
    f.state,
    COUNT(CASE WHEN v.vaccination_date = CURRENT_DATE THEN 1 END) AS today,
    COUNT(CASE WHEN v.vaccination_date >= CURRENT_DATE - INTERVAL '7 days' THEN 1 END) AS this_week,
    COUNT(CASE WHEN v.vaccination_date >= DATE_TRUNC('month', CURRENT_DATE) THEN 1 END) AS this_month,
    COUNT(CASE WHEN v.status = 'completed' THEN 1 END) AS total_completed,
    COUNT(DISTINCT v.vaccine_id) AS vaccine_types_offered
FROM facilities f
LEFT JOIN vaccinations v ON v.facility_id = f.id
    AND v.status = 'completed'
WHERE f.is_active = TRUE
GROUP BY f.id, f.facility_id, f.name, f.city, f.state
ORDER BY today DESC, this_week DESC;
```

---

## Performance Optimization Tips

### 1. Use Partial Indexes

```sql
-- Only index completed vaccinations
CREATE INDEX idx_vaccinations_completed 
ON vaccinations(facility_id, vaccination_date) 
WHERE status = 'completed' AND facility_id IS NOT NULL;
```

### 2. Use Materialized Views for Complex Analytics

```sql
-- Create materialized view for daily facility stats
CREATE MATERIALIZED VIEW facility_daily_stats AS
SELECT 
    f.facility_id,
    v.vaccination_date,
    COUNT(v.id) AS vaccination_count
FROM facilities f
JOIN vaccinations v ON v.facility_id = f.id
WHERE v.status = 'completed'
GROUP BY f.facility_id, v.vaccination_date;

-- Refresh periodically (e.g., daily)
REFRESH MATERIALIZED VIEW CONCURRENTLY facility_daily_stats;
```

### 3. Query Optimization

**Before:**
```sql
-- Slow: Full table scan
SELECT COUNT(*) FROM vaccinations 
WHERE vaccination_date = CURRENT_DATE;
```

**After:**
```sql
-- Fast: Uses index
SELECT COUNT(*) FROM vaccinations 
WHERE vaccination_date = CURRENT_DATE 
  AND status = 'completed'
  AND facility_id IS NOT NULL;
```

---

## Caching Strategy

### Redis Cache Keys

```python
# Daily facility stats
cache_key = f"analytics:facility:{facility_id}:daily:{date}"
TTL = 300  # 5 minutes

# Weekly trends
cache_key = f"analytics:facility:{facility_id}:weekly:{week_start}"
TTL = 600  # 10 minutes

# Monthly trends
cache_key = f"analytics:facility:{facility_id}:monthly:{month_start}"
TTL = 3600  # 1 hour

# Global analytics
cache_key = f"analytics:global:{date}"
TTL = 300  # 5 minutes
```

### Cache Invalidation

```python
# Invalidate on new vaccination
await redis.delete(f"analytics:facility:{facility_id}:*")
await redis.delete("analytics:global:*")

# Invalidate on facility update
await redis.delete(f"analytics:facility:{facility_id}:*")
```

---

## Query Performance Benchmarks

### Expected Performance (with indexes)

| Query Type | Expected Time | Index Used |
|------------|---------------|------------|
| Daily facility stats | < 50ms | `idx_vaccinations_facility_date_status` |
| Weekly trends | < 100ms | `idx_vaccinations_date_facility` |
| Monthly trends | < 200ms | `idx_vaccinations_date_facility` |
| Vaccine distribution | < 150ms | `idx_vaccinations_facility_date_status` |
| Global daily stats | < 300ms | `idx_vaccinations_date_facility` |

### Monitoring

```sql
-- Check index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename = 'vaccinations'
ORDER BY idx_scan DESC;

-- Check slow queries
SELECT 
    query,
    calls,
    total_time,
    mean_time
FROM pg_stat_statements
WHERE query LIKE '%vaccinations%'
ORDER BY mean_time DESC
LIMIT 10;
```

---

**Last Updated:** 2024-01-15

