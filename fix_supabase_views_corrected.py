#!/usr/bin/env python3
"""
Generate corrected SQL commands to fix Supabase views
Fixes the array_agg(unnest()) issue
"""


def generate_corrected_view_sql():
    """Generate corrected SQL to properly update the views"""

    print("🔧 Supabase View Fix - CORRECTED SQL Commands")
    print("=" * 80)
    print("Copy and paste these commands into your Supabase SQL Editor:")
    print("=" * 80)

    # Step 1: Drop existing views (to avoid column name conflicts)
    print("\n-- Step 1: Drop existing views to avoid column conflicts")
    print("DROP VIEW IF EXISTS job_analytics CASCADE;")
    print("DROP VIEW IF EXISTS monthly_trends CASCADE;")
    print("DROP VIEW IF EXISTS discipline_analytics CASCADE;")
    print("DROP VIEW IF EXISTS geographic_distribution CASCADE;")

    # Step 2: Recreate views with new column names and fixed SQL
    print("\n-- Step 2: Create new graduate-focused views")

    print(
        """
-- Analytics view for graduate positions dashboard
CREATE VIEW job_analytics AS
SELECT
    COUNT(*) as total_scraped_positions,
    COUNT(*) FILTER (WHERE is_graduate_position = true) as graduate_positions,
    COUNT(*) FILTER (WHERE is_graduate_position = true AND salary IS NOT NULL AND salary != '' AND salary != 'none') as graduate_positions_with_salary,
    COUNT(DISTINCT discipline) FILTER (WHERE is_graduate_position = true AND discipline IS NOT NULL) as graduate_disciplines,
    COUNT(DISTINCT EXTRACT(YEAR FROM published_date) || '-' || LPAD(EXTRACT(MONTH FROM published_date)::text, 2, '0')) FILTER (WHERE is_graduate_position = true) as months_with_graduate_data,
    MIN(published_date) FILTER (WHERE is_graduate_position = true) as earliest_graduate_posting,
    MAX(published_date) FILTER (WHERE is_graduate_position = true) as latest_graduate_posting,
    MAX(updated_at) as last_updated
FROM jobs;"""
    )

    print(
        """
-- Monthly trends view for graduate positions
CREATE VIEW monthly_trends AS
SELECT
    EXTRACT(YEAR FROM published_date) as year,
    EXTRACT(MONTH FROM published_date) as month,
    TO_CHAR(published_date, 'YYYY-MM') as month_key,
    COUNT(*) as graduate_positions,
    COUNT(*) FILTER (WHERE salary IS NOT NULL AND salary != '' AND salary != 'none') as graduate_positions_with_salary
FROM jobs
WHERE published_date IS NOT NULL AND is_graduate_position = true
GROUP BY year, month, month_key
ORDER BY year DESC, month DESC;"""
    )

    print(
        """
-- Discipline breakdown view for graduate positions only (FIXED)
CREATE VIEW discipline_analytics AS
WITH discipline_keywords_expanded AS (
    SELECT
        discipline,
        is_graduate_position,
        grad_confidence,
        discipline_confidence,
        salary,
        unnest(discipline_keywords) as keyword
    FROM jobs
    WHERE discipline IS NOT NULL
        AND discipline != 'Unknown'
        AND is_graduate_position = true
        AND discipline_keywords IS NOT NULL
)
SELECT
    discipline,
    COUNT(*) as graduate_positions,
    AVG(grad_confidence) as avg_grad_confidence,
    AVG(discipline_confidence) as avg_discipline_confidence,
    COUNT(*) FILTER (WHERE salary IS NOT NULL AND salary != '' AND salary != 'none') as graduate_positions_with_salary,
    array_agg(DISTINCT keyword) as all_keywords
FROM jobs j
LEFT JOIN discipline_keywords_expanded dke ON j.discipline = dke.discipline
WHERE j.discipline IS NOT NULL
    AND j.discipline != 'Unknown'
    AND j.is_graduate_position = true
GROUP BY j.discipline
ORDER BY graduate_positions DESC;"""
    )

    print(
        """
-- Geographic distribution view for graduate positions only
CREATE VIEW geographic_distribution AS
SELECT
    CASE
        WHEN location ~* ',\\s*([A-Z]{2})\\s*$' THEN
            regexp_replace(location, '^.*,\\s*([A-Z]{2})\\s*$', '\\1')
        WHEN location ~* ',\\s*([A-Za-z\\s]+)\\s*$' THEN
            trim(regexp_replace(location, '^.*,\\s*([A-Za-z\\s]+)\\s*$', '\\1'))
        ELSE 'Unknown'
    END as state_or_country,
    COUNT(*) as graduate_positions
FROM jobs
WHERE location IS NOT NULL AND location != '' AND is_graduate_position = true
GROUP BY state_or_country
ORDER BY graduate_positions DESC;"""
    )

    print("\n" + "=" * 80)
    print("📋 INSTRUCTIONS:")
    print("1. Copy ALL the SQL above (including DROP statements)")
    print("2. Go to Supabase Dashboard → SQL Editor")
    print("3. Paste and run the entire script")
    print("4. If discipline_analytics is still too complex, we can simplify it further")
    print("5. Run: python test_dashboard.py")
    print("=" * 80)


def generate_simple_fallback():
    """Generate a simpler version without the complex array aggregation"""

    print("\n🔄 ALTERNATIVE: Simplified Version (if above fails)")
    print("=" * 60)

    print(
        """
-- Simplified discipline view without keywords aggregation
DROP VIEW IF EXISTS discipline_analytics CASCADE;

CREATE VIEW discipline_analytics AS
SELECT
    discipline,
    COUNT(*) as graduate_positions,
    AVG(grad_confidence) as avg_grad_confidence,
    AVG(discipline_confidence) as avg_discipline_confidence,
    COUNT(*) FILTER (WHERE salary IS NOT NULL AND salary != '' AND salary != 'none') as graduate_positions_with_salary,
    NULL::text[] as all_keywords  -- Placeholder for compatibility
FROM jobs
WHERE discipline IS NOT NULL
    AND discipline != 'Unknown'
    AND is_graduate_position = true
GROUP BY discipline
ORDER BY graduate_positions DESC;"""
    )

    print("\n📝 This simplified version removes the complex keyword aggregation")
    print("   but maintains all other functionality for the dashboard.")


if __name__ == "__main__":
    generate_corrected_view_sql()
    generate_simple_fallback()
