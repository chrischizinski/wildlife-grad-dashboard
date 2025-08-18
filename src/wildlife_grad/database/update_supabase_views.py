#!/usr/bin/env python3
"""
Update Supabase views to match the new graduate positions dashboard schema
"""

import asyncio


async def update_supabase_views():
    """Update the Supabase views with new graduate-focused queries"""

    # Read the schema file with updated views
    with open("database/supabase_schema.sql", "r") as f:
        schema_content = f.read()

    print("📝 Schema file loaded successfully")
    print(
        "⚠️  NOTE: This script shows the SQL to run. You need to execute it manually in Supabase SQL Editor."
    )
    print("=" * 80)

    # Extract the view definitions
    view_sections = [
        "-- Analytics view for graduate positions dashboard",
        "-- Monthly trends view for graduate positions",
        "-- Discipline breakdown view for graduate positions only",
        "-- Geographic distribution view for graduate positions only",
    ]

    print("🔄 SQL Commands to Execute in Supabase SQL Editor:")
    print("=" * 80)

    for section in view_sections:
        start_idx = schema_content.find(section)
        if start_idx != -1:
            # Find the end of this CREATE VIEW statement
            view_start = schema_content.find("CREATE OR REPLACE VIEW", start_idx)
            next_section = schema_content.find("\n--", view_start + 1)
            if next_section == -1:
                next_section = schema_content.find("\n\n", view_start + 1)

            if view_start != -1:
                view_sql = schema_content[view_start:next_section].strip()
                print(f"\n{section}")
                print("-" * 60)
                print(view_sql)
                print()

    print("=" * 80)
    print("📋 INSTRUCTIONS:")
    print("1. Copy the SQL commands above")
    print("2. Go to your Supabase project dashboard")
    print("3. Navigate to SQL Editor")
    print("4. Paste and run each CREATE OR REPLACE VIEW command")
    print("5. Run the test script again: python test_dashboard.py")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(update_supabase_views())
