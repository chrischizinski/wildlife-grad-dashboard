-- Wildlife Graduate Dashboard - View Updates
-- Purpose: Update database views to focus on graduate positions only
-- Author: Dashboard Migration Script
-- Date: 2025-08-04

-- Drop existing views in correct order (handle dependencies)
DROP VIEW IF EXISTS job_analytics;
DROP VIEW IF EXISTS monthly_trends;
DROP VIEW IF EXISTS discipline_analytics;
DROP VIEW IF EXISTS geographic_distribution;

-- 1. Job Analytics View - Main dashboard metrics
CREATE VIEW job_analytics AS
SELECT
    COUNT(*) as total_scraped_positions,
    COUNT(*) FILTER (WHERE is_graduate_position = true) as graduate_positions,
    COUNT(*) FILTER (WHERE is_graduate_position = true AND salary IS NOT NULL AND salary != '') as graduate_positions_with_salary,
    COUNT(DISTINCT discipline) FILTER (WHERE is_graduate_position = true AND discipline IS NOT NULL) as graduate_disciplines,
    MIN(published_date) FILTER (WHERE is_graduate_position = true) as earliest_graduate_posting,
    MAX(published_date) FILTER (WHERE is_graduate_position = true) as latest_graduate_posting,
    MAX(updated_at) as last_updated
FROM jobs;

-- 2. Monthly Trends View - Graduate positions over time
CREATE VIEW monthly_trends AS
SELECT
    EXTRACT(YEAR FROM published_date)::int as year,
    EXTRACT(MONTH FROM published_date)::int as month,
    TO_CHAR(published_date, 'YYYY-MM') as month_key,
    COUNT(*) as graduate_positions
FROM jobs
WHERE published_date IS NOT NULL
    AND is_graduate_position = true
GROUP BY year, month, month_key
ORDER BY year DESC, month DESC;

-- 3. Discipline Analytics View - Graduate positions by discipline
CREATE VIEW discipline_analytics AS
SELECT
    discipline,
    COUNT(*) as graduate_positions,
    ROUND(AVG(grad_confidence)::numeric, 3) as avg_grad_confidence,
    ROUND(AVG(discipline_confidence)::numeric, 3) as avg_discipline_confidence,
    COUNT(*) FILTER (WHERE salary IS NOT NULL AND salary != '') as graduate_positions_with_salary
FROM jobs
WHERE discipline IS NOT NULL
    AND discipline != 'Unknown'
    AND is_graduate_position = true
GROUP BY discipline
ORDER BY graduate_positions DESC;

-- 4. Geographic Distribution View - Graduate positions by location
CREATE VIEW geographic_distribution AS
SELECT
    CASE
        WHEN location ~ ',\s*[A-Z]{2}\s*$' THEN
            TRIM(SUBSTRING(location FROM ',\s*([A-Z]{2})\s*$'))
        WHEN location ~ ',\s*[A-Za-z\s]+\s*$' THEN
            TRIM(SUBSTRING(location FROM ',\s*([A-Za-z\s]+)\s*$'))
        ELSE 'Unknown'
    END as state_or_country,
    COUNT(*) as graduate_positions
FROM jobs
WHERE location IS NOT NULL
    AND location != ''
    AND is_graduate_position = true
GROUP BY state_or_country
ORDER BY graduate_positions DESC;

-- Verify views were created successfully
SELECT 'job_analytics' as view_name, COUNT(*) as record_count FROM job_analytics
UNION ALL
SELECT 'monthly_trends', COUNT(*) FROM monthly_trends
UNION ALL
SELECT 'discipline_analytics', COUNT(*) FROM discipline_analytics
UNION ALL
SELECT 'geographic_distribution', COUNT(*) FROM geographic_distribution;
