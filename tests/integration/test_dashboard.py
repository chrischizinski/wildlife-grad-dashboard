#!/usr/bin/env python3
"""
Test script for the updated graduate positions dashboard
Tests database connectivity and validates the new schema views
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def test_supabase_connection():
    """Test Supabase connection and new views"""
    
    SUPABASE_URL = "https://mqbkzveymkehgkbcjgba.supabase.co"
    SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1xYmt6dmV5bWtlaGdrYmNqZ2JhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgzNjM0MzYsImV4cCI6MjA2MzkzOTQzNn0.ojHZfb5ydVEVKQShv3pmW8bqXPksBc0jmJOfPz0lqCw"
    
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json"
    }
    
    tests = []
    
    async with aiohttp.ClientSession() as session:
        
        # Test 1: Check if jobs table exists and has data
        print("🔍 Testing jobs table...")
        try:
            async with session.get(
                f"{SUPABASE_URL}/rest/v1/jobs?select=count",
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    total_jobs = len(result) if isinstance(result, list) else 0
                    print(f"✅ Jobs table accessible - Found {total_jobs} total positions")
                    tests.append(("jobs_table", True, f"{total_jobs} positions"))
                else:
                    print(f"❌ Jobs table error: {response.status}")
                    tests.append(("jobs_table", False, f"HTTP {response.status}"))
        except Exception as e:
            print(f"❌ Jobs table error: {e}")
            tests.append(("jobs_table", False, str(e)))
        
        # Test 2: Check graduate positions
        print("\n🎓 Testing graduate position filtering...")
        try:
            async with session.get(
                f"{SUPABASE_URL}/rest/v1/jobs?select=count&is_graduate_position=eq.true",
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    grad_jobs = len(result) if isinstance(result, list) else 0
                    print(f"✅ Graduate positions found: {grad_jobs}")
                    tests.append(("graduate_positions", True, f"{grad_jobs} graduate positions"))
                else:
                    print(f"❌ Graduate positions error: {response.status}")
                    tests.append(("graduate_positions", False, f"HTTP {response.status}"))
        except Exception as e:
            print(f"❌ Graduate positions error: {e}")
            tests.append(("graduate_positions", False, str(e)))
        
        # Test 3: Test job_analytics view
        print("\n📊 Testing job_analytics view...")
        try:
            async with session.get(
                f"{SUPABASE_URL}/rest/v1/job_analytics?select=*",
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if result and len(result) > 0:
                        analytics = result[0]
                        print(f"✅ Analytics view working:")
                        print(f"   - Total scraped: {analytics.get('total_scraped_positions', 'N/A')}")
                        print(f"   - Graduate positions: {analytics.get('graduate_positions', 'N/A')}")
                        print(f"   - Graduate with salary: {analytics.get('graduate_positions_with_salary', 'N/A')}")
                        tests.append(("job_analytics", True, "View accessible"))
                    else:
                        print("❌ Analytics view returned no data")
                        tests.append(("job_analytics", False, "No data"))
                else:
                    print(f"❌ Analytics view error: {response.status}")
                    tests.append(("job_analytics", False, f"HTTP {response.status}"))
        except Exception as e:
            print(f"❌ Analytics view error: {e}")
            tests.append(("job_analytics", False, str(e)))
        
        # Test 4: Test discipline_analytics view
        print("\n🔬 Testing discipline_analytics view...")
        try:
            async with session.get(
                f"{SUPABASE_URL}/rest/v1/discipline_analytics?select=*&limit=5",
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Discipline analytics: {len(result)} disciplines found")
                    for discipline in result[:3]:  # Show top 3
                        print(f"   - {discipline.get('discipline', 'Unknown')}: {discipline.get('graduate_positions', 0)} positions")
                    tests.append(("discipline_analytics", True, f"{len(result)} disciplines"))
                else:
                    print(f"❌ Discipline analytics error: {response.status}")
                    tests.append(("discipline_analytics", False, f"HTTP {response.status}"))
        except Exception as e:
            print(f"❌ Discipline analytics error: {e}")
            tests.append(("discipline_analytics", False, str(e)))
        
        # Test 5: Test geographic_distribution view
        print("\n🗺️ Testing geographic_distribution view...")
        try:
            async with session.get(
                f"{SUPABASE_URL}/rest/v1/geographic_distribution?select=*&limit=5",
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Geographic distribution: {len(result)} locations found")
                    for location in result[:3]:  # Show top 3
                        print(f"   - {location.get('state_or_country', 'Unknown')}: {location.get('graduate_positions', 0)} positions")
                    tests.append(("geographic_distribution", True, f"{len(result)} locations"))
                else:
                    print(f"❌ Geographic distribution error: {response.status}")
                    tests.append(("geographic_distribution", False, f"HTTP {response.status}"))
        except Exception as e:
            print(f"❌ Geographic distribution error: {e}")
            tests.append(("geographic_distribution", False, str(e)))
        
        # Test 6: Test monthly_trends view
        print("\n📈 Testing monthly_trends view...")
        try:
            async with session.get(
                f"{SUPABASE_URL}/rest/v1/monthly_trends?select=*&limit=5",
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Monthly trends: {len(result)} months found")
                    for month in result[:3]:  # Show recent 3
                        print(f"   - {month.get('month_key', 'Unknown')}: {month.get('graduate_positions', 0)} graduate positions")
                    tests.append(("monthly_trends", True, f"{len(result)} months"))
                else:
                    print(f"❌ Monthly trends error: {response.status}")
                    tests.append(("monthly_trends", False, f"HTTP {response.status}"))
        except Exception as e:
            print(f"❌ Monthly trends error: {e}")
            tests.append(("monthly_trends", False, str(e)))
    
    # Summary
    print("\n" + "="*60)
    print("📋 TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for test in tests if test[1])
    total = len(tests)
    
    for test_name, success, details in tests:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name:<20} - {details}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Dashboard should work correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    print("🧪 Testing Graduate Positions Dashboard")
    print("="*60)
    success = asyncio.run(test_supabase_connection())
    exit(0 if success else 1)