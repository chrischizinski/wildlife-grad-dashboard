#!/usr/bin/env python3
"""
Generate the correct SQL commands to fix Supabase views
Handles column name changes properly
"""


def generate_view_fix_sql():
    """Generate SQL to properly update the views"""

    print("🔧 Supabase View Fix - SQL Commands")
    print("=" * 80)
    print("Copy and paste these commands into your Supabase SQL Editor:")
    print("=" * 80)

    # Step 1: Drop existing views (to avoid column name conflicts)
    print("\n-- Step 1: Drop existing views to avoid column conflicts")
    print("DROP VIEW IF EXISTS job_analytics CASCADE;")
    print("DROP VIEW IF EXISTS monthly_trends CASCADE;")
    print("DROP VIEW IF EXISTS discipline_analytics CASCADE;")
    print("DROP VIEW IF EXISTS geographic_distribution CASCADE;")

    # Step 2: Recreate views with new column names
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
-- Discipline breakdown view for graduate positions only
CREATE VIEW discipline_analytics AS
SELECT
    discipline,
    COUNT(*) as graduate_positions,
    AVG(grad_confidence) as avg_grad_confidence,
    AVG(discipline_confidence) as avg_discipline_confidence,
    COUNT(*) FILTER (WHERE salary IS NOT NULL AND salary != '' AND salary != 'none') as graduate_positions_with_salary,
    array_agg(DISTINCT unnest(discipline_keywords)) FILTER (WHERE discipline_keywords IS NOT NULL) as all_keywords
FROM jobs
WHERE discipline IS NOT NULL AND discipline != 'Unknown' AND is_graduate_position = true
GROUP BY discipline
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
    print("4. Run: python test_dashboard.py")
    print("=" * 80)


if __name__ == "__main__":
    generate_view_fix_sql()
