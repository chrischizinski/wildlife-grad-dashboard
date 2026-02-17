#!/usr/bin/env python3
"""
Check the most recent data in Supabase database.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    from supabase import Client, create_client
except ImportError:
    print("❌ Required packages not installed. Run:")
    print("pip install supabase python-dotenv")
    sys.exit(1)

def check_latest_data():
    """Check the most recent data in Supabase."""
    
    load_dotenv()
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Supabase credentials not configured")
        return False
    
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        
        print("🔍 Checking latest data in Supabase...")
        print("=" * 60)
        
        # Get total counts
        total_result = supabase.table("jobs").select("id", count="exact").execute()
        grad_result = supabase.table("jobs").select("id", count="exact").eq("is_graduate_position", True).execute()
        
        print(f"📊 Total positions: {total_result.count}")
        print(f"🎓 Graduate positions: {grad_result.count}")
        
        # Get most recent scrape information
        latest_scrape = supabase.table("jobs").select("scraped_at, scrape_run_id, title, organization").order("scraped_at", desc=True).limit(5).execute()
        
        if latest_scrape.data:
            print(f"\n📅 Most Recent Scrape Activity:")
            print(f"   Latest scrape: {latest_scrape.data[0]['scraped_at']}")
            
            # Group by scrape run
            scrape_runs = {}
            for job in latest_scrape.data:
                run_id = job.get('scrape_run_id', 'unknown')
                if run_id not in scrape_runs:
                    scrape_runs[run_id] = []
                scrape_runs[run_id].append(job)
            
            print(f"\n🔄 Recent Scrape Runs:")
            for run_id, jobs in scrape_runs.items():
                print(f"   Run ID: {run_id}")
                print(f"   Date: {jobs[0]['scraped_at']}")
                print(f"   Sample job: {jobs[0]['title'][:50]}...")
                print()
        
        # Check date distribution
        date_stats = supabase.table("jobs").select("scraped_at").order("scraped_at", desc=True).limit(100).execute()
        
        if date_stats.data:
            dates = [job['scraped_at'][:10] for job in date_stats.data]  # Extract date part
            unique_dates = list(set(dates))
            unique_dates.sort(reverse=True)
            
            print(f"📈 Recent Activity by Date (last 10 dates):")
            for date in unique_dates[:10]:
                count = dates.count(date)
                print(f"   {date}: {count} positions")
        
        # Check for graduate positions specifically
        recent_grad = supabase.table("jobs").select("scraped_at, title, organization").eq("is_graduate_position", True).order("scraped_at", desc=True).limit(3).execute()
        
        if recent_grad.data:
            print(f"\n🎓 Most Recent Graduate Positions:")
            for job in recent_grad.data:
                print(f"   {job['scraped_at'][:10]} - {job['title'][:40]}... ({job['organization']})")
        
        # Check data freshness
        if latest_scrape.data:
            latest_date = datetime.fromisoformat(latest_scrape.data[0]['scraped_at'].replace('Z', '+00:00'))
            days_old = (datetime.now(latest_date.tzinfo) - latest_date).days
            
            print(f"\n⏰ Data Freshness:")
            print(f"   Latest data is {days_old} days old")
            
            if days_old > 7:
                print(f"   🚨 WARNING: Data is over 7 days old - scraper may need to run")
            elif days_old > 3:
                print(f"   ⚠️  CAUTION: Data is {days_old} days old - consider running scraper soon")
            else:
                print(f"   ✅ Data is fresh (less than 3 days old)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking data: {e}")
        return False

if __name__ == "__main__":
    success = check_latest_data()
    sys.exit(0 if success else 1)