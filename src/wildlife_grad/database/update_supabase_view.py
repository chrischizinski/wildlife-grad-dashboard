#!/usr/bin/env python3
"""Update the discipline_analytics view in Supabase to include salary statistics."""

import os

from dotenv import load_dotenv
from supabase import create_client


def update_discipline_view():
    load_dotenv()

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        print("❌ Missing environment variables")
        return False

    print(f"🔗 Connecting to {url}")

    try:
        supabase = create_client(url, key)
        print("✅ Supabase client created successfully")

        # Read the SQL file
        with open("update_discipline_view.sql", "r") as f:
            sql_content = f.read()

        print("📊 Updating discipline_analytics view...")

        # Execute the SQL using RPC (since we need to run DDL)
        supabase.rpc("exec_sql", {"sql": sql_content}).execute()

        print("✅ View updated successfully")

        # Test the updated view
        print("🧪 Testing updated view...")
        test_result = (
            supabase.table("discipline_analytics")
            .select("discipline, graduate_positions, avg_salary")
            .limit(3)
            .execute()
        )

        if test_result.data:
            print("✅ Updated view working correctly:")
            for row in test_result.data:
                print(
                    f"   {row['discipline']}: {row['graduate_positions']} positions, avg salary: ${row.get('avg_salary', 'N/A')}"
                )
        else:
            print("⚠️ View updated but no data returned")

        return True

    except Exception as e:
        print(f"❌ Update failed: {e}")
        return False


if __name__ == "__main__":
    update_discipline_view()
