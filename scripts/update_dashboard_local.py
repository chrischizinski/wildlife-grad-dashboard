#!/usr/bin/env python3
"""
Update dashboard with local JSON data when Supabase is unavailable.
This script generates dashboard data from local files as a fallback.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

def load_local_data() -> Dict[str, Any]:
    """Load data from local JSON files."""
    
    data_dir = Path("data")
    
    # Try to load the most recent data
    data_files = {
        "raw_positions": data_dir / "raw" / "all_positions_detailed.json",
        "processed_positions": data_dir / "processed" / "verified_graduate_assistantships.json", 
        "enhanced_data": data_dir / "enhanced_data.json",
        "historical_data": data_dir / "historical_positions.json"
    }
    
    loaded_data = {}
    
    for key, file_path in data_files.items():
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    loaded_data[key] = json.load(f)
                print(f"✅ Loaded {key} from {file_path}")
            except Exception as e:
                print(f"⚠️  Failed to load {key}: {e}")
                loaded_data[key] = []
        else:
            print(f"⚠️  File not found: {file_path}")
            loaded_data[key] = []
    
    return loaded_data

def generate_dashboard_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate dashboard summary from local data."""
    
    positions = data.get("processed_positions", [])
    if not positions:
        positions = data.get("raw_positions", [])
    
    # Filter for graduate positions
    grad_positions = []
    for pos in positions:
        if isinstance(pos, dict):
            # Check various indicators for graduate positions
            is_grad = (
                pos.get("is_graduate_position", False) or
                pos.get("classification") == "Graduate" or
                any(keyword in pos.get("title", "").lower() 
                    for keyword in ["phd", "ph.d", "master", "m.s.", "ms ", "graduate", "assistantship"])
            )
            if is_grad:
                grad_positions.append(pos)
    
    # Generate summary statistics
    summary = {
        "total_positions": len(positions),
        "graduate_positions": len(grad_positions),
        "last_updated": datetime.now().isoformat(),
        "data_source": "local_files"
    }
    
    # Discipline analysis
    disciplines = {}
    for pos in grad_positions:
        discipline = pos.get("discipline", "Other")
        if discipline not in disciplines:
            disciplines[discipline] = {"count": 0, "positions": []}
        disciplines[discipline]["count"] += 1
        disciplines[discipline]["positions"].append(pos)
    
    summary["disciplines"] = disciplines
    
    # Salary analysis
    salary_positions = [pos for pos in grad_positions if pos.get("salary_min")]
    summary["positions_with_salary"] = len(salary_positions)
    
    if salary_positions:
        salaries = [pos["salary_min"] for pos in salary_positions]
        summary["avg_salary"] = sum(salaries) / len(salaries)
        summary["median_salary"] = sorted(salaries)[len(salaries) // 2]
    
    return summary

def update_web_dashboard_data(summary: Dict[str, Any]) -> bool:
    """Update the web dashboard data files."""
    
    web_data_dir = Path("web/data")
    web_data_dir.mkdir(exist_ok=True)
    
    try:
        # Create dashboard data file
        dashboard_file = web_data_dir / "dashboard_data.json"
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Updated dashboard data: {dashboard_file}")
        
        # Create a simple status file
        status_file = web_data_dir / "status.json"
        status = {
            "status": "offline_mode",
            "last_updated": summary["last_updated"],
            "message": "Using local data - Supabase unavailable"
        }
        
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=2)
            
        print(f"✅ Updated status file: {status_file}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to update web dashboard data: {e}")
        return False

def main():
    """Main function to update dashboard with local data."""
    
    print("🔄 Updating dashboard with local data...")
    print("📁 Loading local JSON files...")
    
    # Load local data
    data = load_local_data()
    
    if not any(data.values()):
        print("❌ No local data files found!")
        print("Please run the scraper first to generate data files.")
        return False
    
    # Generate dashboard summary
    print("📊 Generating dashboard summary...")
    summary = generate_dashboard_summary(data)
    
    print(f"📈 Summary: {summary['graduate_positions']} graduate positions out of {summary['total_positions']} total")
    
    # Update web dashboard
    print("🌐 Updating web dashboard files...")
    success = update_web_dashboard_data(summary)
    
    if success:
        print("✅ Dashboard updated successfully!")
        print("🚀 You can now serve the dashboard locally:")
        print("   cd web && python -m http.server 8080")
        print("   Then visit: http://localhost:8080/wildlife_dashboard.html")
    else:
        print("❌ Failed to update dashboard")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)