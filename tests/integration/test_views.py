#!/usr/bin/env python3
"""
Test script to verify Supabase views are working correctly
Clean, focused, single-purpose script
"""

import asyncio
import aiohttp
import sys

SUPABASE_URL = "https://mqbkzveymkehgkbcjgba.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1xYmt6dmV5bWtlaGdrYmNqZ2JhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgzNjM0MzYsImV4cCI6MjA2MzkzOTQzNn0.ojHZfb5ydVEVKQShv3pmW8bqXPksBc0jmJOfPz0lqCw"

async def test_view(session, view_name):
    """Test a single view and return results"""
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    
    try:
        async with session.get(f"{SUPABASE_URL}/rest/v1/{view_name}", headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return True, len(data), data[0] if data else None
            else:
                return False, response.status, await response.text()
    except Exception as e:
        return False, 0, str(e)

async def main():
    """Test all views"""
    views = ['jobs', 'job_analytics', 'monthly_trends', 'discipline_analytics', 'geographic_distribution']
    
    print("Testing Supabase Views")
    print("=" * 40)
    
    async with aiohttp.ClientSession() as session:
        for view_name in views:
            success, count_or_status, sample_data = await test_view(session, view_name)
            
            if success:
                print(f"✅ {view_name:<20} {count_or_status} records")
                if view_name == 'job_analytics' and sample_data:
                    print(f"   Total scraped: {sample_data.get('total_scraped_positions', 'N/A')}")
                    print(f"   Graduate: {sample_data.get('graduate_positions', 'N/A')}")
            else:
                print(f"❌ {view_name:<20} Error: {count_or_status}")
                return False
    
    print("\n✅ All views working correctly")
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)