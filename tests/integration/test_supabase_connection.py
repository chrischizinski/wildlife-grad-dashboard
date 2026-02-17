#!/usr/bin/env python3
"""Test Supabase connection and check database status."""

import os
from dotenv import load_dotenv
from supabase import create_client

def test_supabase_connection():
    load_dotenv()
    
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_ANON_KEY')
    
    if not url or not key:
        print("❌ Missing environment variables")
        return False
        
    print(f"🔗 Connecting to {url}")
    
    try:
        supabase = create_client(url, key)
        print("✅ Supabase client created successfully")
        
        # Test job_analytics view
        print("\n📊 Testing job_analytics view...")
        try:
            result = supabase.from('job_analytics').select('*').limit(1).execute()
            if result.data:
                print("✅ job_analytics view accessible with data:")
                print(f"   Data: {result.data[0]}")
            else:
                print("⚠️  job_analytics view accessible but empty")
        except Exception as e:
            print(f"❌ job_analytics view error: {e}")
            
        # Test jobs table
        print("\n📋 Testing jobs table...")
        try:
            result = supabase.from('jobs').select('id').limit(1).execute()
            if result.data:
                print(f"✅ jobs table accessible with {len(result.data)} records")
            else:
                print("⚠️  jobs table accessible but empty")
        except Exception as e:
            print(f"❌ jobs table error: {e}")
            
        # Test discipline_analytics view
        print("\n🔬 Testing discipline_analytics view...")
        try:
            result = supabase.from('discipline_analytics').select('*').limit(1).execute()
            if result.data:
                print(f"✅ discipline_analytics view accessible with data")
            else:
                print("⚠️  discipline_analytics view accessible but empty")
        except Exception as e:
            print(f"❌ discipline_analytics view error: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_supabase_connection()