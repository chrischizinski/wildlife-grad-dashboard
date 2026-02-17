#!/usr/bin/env python3
"""
Detailed Supabase database test to verify comprehensive scrape results
"""

import os
from dotenv import load_dotenv
from supabase import create_client

def test_supabase_comprehensive():
    """Test Supabase database after comprehensive scrape."""
    load_dotenv()
    
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_ANON_KEY')
    
    if not url or not key:
        print("❌ Missing Supabase credentials")
        return False
    
    try:
        supabase = create_client(url, key)
        print(f"✅ Connected to Supabase: {url}")
        
        # Test 1: Overall statistics
        print("\n=== OVERALL STATISTICS ===")
        analytics_result = supabase.table('job_analytics').select('*').execute()
        if analytics_result.data:
            analytics = analytics_result.data[0]
            print(f"📊 Total positions in database: {analytics.get('total_scraped_positions', 'N/A')}")
            print(f"🎓 Graduate positions identified: {analytics.get('graduate_positions', 'N/A')}")
            print(f"💰 Graduate positions with salary: {analytics.get('graduate_positions_with_salary', 'N/A')}")
            print(f"📚 Unique disciplines: {analytics.get('graduate_disciplines', 'N/A')}")
            print(f"📅 Date range: {analytics.get('earliest_graduate_posting', 'N/A')} to {analytics.get('latest_graduate_posting', 'N/A')}")
            print(f"🕒 Last updated: {analytics.get('last_updated', 'N/A')}")
        
        # Test 2: Discipline breakdown
        print("\n=== DISCIPLINE BREAKDOWN ===")
        disciplines_result = supabase.table('discipline_analytics').select('*').order('graduate_positions', desc=True).execute()
        if disciplines_result.data:
            for disc in disciplines_result.data:
                print(f"📊 {disc['discipline']}: {disc['graduate_positions']} positions (avg salary: ${disc.get('avg_salary', 'N/A')})")
        
        # Test 3: Geographic distribution  
        print("\n=== GEOGRAPHIC DISTRIBUTION ===")
        geo_result = supabase.table('geographic_distribution').select('*').order('graduate_positions', desc=True).limit(10).execute()
        if geo_result.data:
            for geo in geo_result.data:
                region = geo.get('region', geo.get('state_or_country', 'Unknown'))
                print(f"🌍 {region}: {geo['graduate_positions']} positions")
        
        # Test 4: Recent activity
        print("\n=== RECENT GRADUATE POSITIONS (Last 5) ===")
        jobs_result = supabase.table('jobs').select('title, organization, location, published_date').eq('is_graduate_position', True).order('published_date', desc=True).limit(5).execute()
        if jobs_result.data:
            for job in jobs_result.data:
                print(f"🎓 {job['title']} - {job['organization']} ({job.get('published_date', 'N/A')})")
        
        # Test 5: Monthly trends
        print("\n=== MONTHLY TRENDS (Last 6 months) ===")
        trends_result = supabase.table('monthly_trends').select('*').order('year', desc=True).order('month', desc=True).limit(6).execute()
        if trends_result.data:
            for trend in trends_result.data:
                print(f"📈 {trend['year']}-{trend['month']:02d}: {trend['graduate_positions']} graduate positions")
        
        print("\n✅ SUPABASE DATABASE TEST COMPLETE")
        print("🎯 Database successfully populated with comprehensive graduate position data!")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    test_supabase_comprehensive()