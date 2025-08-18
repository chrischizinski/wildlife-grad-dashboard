#!/usr/bin/env python3
"""
Export positions from Supabase for verification
"""

import asyncio
import json

import aiohttp


async def export_supabase_positions():
    """Export all positions from Supabase for verification"""

    SUPABASE_URL = "https://mqbkzveymkehgkbcjgba.supabase.co"
    SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1xYmt6dmV5bWtlaGdrYmNqZ2JhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgzNjM0MzYsImV4cCI6MjA2MzkzOTQzNn0.ojHZfb5ydVEVKQShv3pmW8bqXPksBc0jmJOfPz0lqCw"

    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
    }

    print("📥 Exporting positions from Supabase for verification...")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                f"{SUPABASE_URL}/rest/v1/jobs?select=*", headers=headers
            ) as response:
                if response.status == 200:
                    positions = await response.json()

                    print(f"✅ Retrieved {len(positions)} positions from Supabase")

                    # Add position_id field using the id from Supabase
                    for pos in positions:
                        pos["position_id"] = str(
                            pos.get("id", pos.get("url", "unknown"))
                        )

                    # Export to the verification file
                    output_file = "data/processed/verified_graduate_assistantships.json"
                    with open(output_file, "w") as f:
                        json.dump(positions, f, indent=2)

                    print(f"💾 Exported to {output_file}")

                    # Show summary
                    graduate_positions = [
                        p for p in positions if p.get("is_graduate_position")
                    ]
                    print("📊 Summary:")
                    print(f"   Total positions: {len(positions)}")
                    print(f"   Graduate positions: {len(graduate_positions)}")
                    print(
                        f"   Professional positions: {len(positions) - len(graduate_positions)}"
                    )

                    return True

                else:
                    print(f"❌ Failed to retrieve positions: HTTP {response.status}")
                    return False

        except Exception as e:
            print(f"❌ Error: {e}")
            return False


if __name__ == "__main__":
    success = asyncio.run(export_supabase_positions())
    if success:
        print("\n🎯 Ready for verification!")
        print("Run: python scripts/verify_classifications.py --smart-sample 20")
    else:
        print("\n❌ Export failed")
