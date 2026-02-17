#!/usr/bin/env python3
"""Apply geographic view update to show regions instead of states."""

import os

from dotenv import load_dotenv
from supabase import create_client


def apply_geographic_update():
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

        print("📍 Checking current geographic distribution...")
        # Test current view
        try:
            current_result = (
                supabase.table("geographic_distribution").select("*").execute()
            )
            print("Current geographic data:")
            for row in current_result.data:
                print(
                    f"   {row.get('state_or_country', row.get('region', 'Unknown'))}: {row.get('graduate_positions', 0)} positions"
                )
        except Exception as e:
            print(f"⚠️ Could not read current data: {e}")

        # Since we can't execute DDL directly through the client, we'll need to apply this through the Supabase dashboard
        print("\n📝 SQL to apply in Supabase dashboard:")
        with open("update_geographic_view.sql", "r") as f:
            sql_content = f.read()
            print(sql_content)

        print("\n⚠️ Note: This SQL needs to be executed in the Supabase SQL editor")
        print("   1. Go to your Supabase dashboard")
        print("   2. Navigate to SQL Editor")
        print("   3. Paste and execute the SQL above")

        return True

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


if __name__ == "__main__":
    apply_geographic_update()
