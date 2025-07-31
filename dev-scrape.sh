#!/bin/bash
# Development scraping script - generates data with dev_ prefix to avoid conflicts

set -e

echo "🚀 Running development scraping..."

# Run scraper and save to dev files
python wildlife_job_scraper.py

# Copy production files to dev versions for development
if [ -f "data/processed/verified_graduate_assistantships.json" ]; then
    cp "data/processed/verified_graduate_assistantships.json" "data/processed/dev_verified_graduate_assistantships.json"
    echo "✅ Created dev data file"
fi

if [ -f "data/raw/all_positions_detailed.json" ]; then
    cp "data/raw/all_positions_detailed.json" "data/raw/dev_all_positions_detailed.json"
    echo "✅ Created dev raw data file"
fi

# Generate analytics with dev data
python scripts/generate_dashboard_analytics.py

# Copy dashboard data to dev versions
if [ -f "dashboard/data/dashboard_analytics.json" ]; then
    cp "dashboard/data/dashboard_analytics.json" "dashboard/data/dev_dashboard_analytics.json"
    echo "✅ Created dev dashboard analytics"
fi

echo "📊 Development data generated successfully!"
echo "📍 Files created:"
echo "  - data/processed/dev_verified_graduate_assistantships.json"
echo "  - data/raw/dev_all_positions_detailed.json" 
echo "  - dashboard/data/dev_dashboard_analytics.json"
echo ""
echo "💡 Use these dev files for local testing without conflicts!"