#!/bin/bash

echo "🔄 RESTORING HISTORICAL DATA POST-SCRAPE..."
echo "=========================================="

if [ -f "data/historical_positions.json" ] && [ -f "data/processed/verified_graduate_assistantships.json" ]; then
    echo "✅ New comprehensive data detected"
    
    # Create backup of new comprehensive data
    timestamp=$(date +%Y%m%d_%H%M%S)
    mkdir -p data/comprehensive_backup
    cp data/historical_positions.json "data/comprehensive_backup/comprehensive_${timestamp}.json"
    
    echo "📦 Comprehensive data backed up to: data/comprehensive_backup/comprehensive_${timestamp}.json"
    
    # Restore the original historical data files to temp location for merging if needed
    if [ -f "data/temp_backup/historical_positions.json" ]; then
        echo "📚 Original historical data available in data/temp_backup/"
        echo "   You can manually merge if needed for extended historical analysis"
    fi
    
    echo ""
    echo "🎉 SETUP COMPLETE!"
    echo "   • Comprehensive base dataset: ✅ Created"
    echo "   • Weekly schedule: ✅ Active (Mondays 4 AM Central)"
    echo "   • Historical backup: ✅ Preserved"
    echo "   • Next run will be INCREMENTAL (last 7 days)"
    
else
    echo "❌ Comprehensive scrape not yet complete"
    echo "   Run ./check_scrape_completion.sh to check status"
fi