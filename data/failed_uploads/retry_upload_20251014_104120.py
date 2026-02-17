#!/usr/bin/env python3
"""
Auto-generated retry script for failed Supabase upload.
Generated: 2025-10-14T10:41:20.939402
Original error: Supabase not available
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.robust_data_pipeline import RobustDataPipeline

def retry_upload():
    pipeline = RobustDataPipeline()
    
    with open("data/failed_uploads/complete_failure_20251014_104120.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"🔄 Retrying upload of {len(data)} positions...")
    result = pipeline.upload_to_supabase(data, "20251014_104120_retry")
    
    if result["status"] == "success":
        print("✅ Retry successful! You can delete this file.")
        return True
    else:
        print("❌ Retry failed. Check Supabase status and try again later.")
        return False

if __name__ == "__main__":
    success = retry_upload()
    sys.exit(0 if success else 1)
