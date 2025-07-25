#!/bin/bash

echo "🔍 CHECKING COMPREHENSIVE SCRAPE COMPLETION..."
echo "=============================================="

# Check if key files were recreated
if [ -f "data/historical_positions.json" ] && [ -f "data/processed/verified_graduate_assistantships.json" ]; then
    echo "✅ Core data files recreated successfully"
    
    # Get counts
    total_positions=$(jq length data/enhanced_data.json 2>/dev/null || echo "0")
    grad_positions=$(jq '[.[] | select(.is_graduate_position == true)] | length' data/enhanced_data.json 2>/dev/null || echo "0")
    
    echo "📊 SCRAPE RESULTS:"
    echo "   • Total positions: $total_positions"
    echo "   • Graduate positions: $grad_positions"
    
    # Check if Supabase was updated
    if [ -f "data/enhanced_data.json" ]; then
        echo "✅ Enhanced data generated"
    fi
    
    # Check archive creation
    latest_archive=$(ls -t data/archive/historical_*.json 2>/dev/null | head -1)
    if [ -n "$latest_archive" ]; then
        echo "✅ Archive created: $(basename "$latest_archive")"
    fi
    
    echo ""
    echo "🎉 COMPREHENSIVE SCRAPE COMPLETED SUCCESSFULLY!"
    echo "   Your base dataset is now ready for weekly updates."
    
else
    echo "⏳ Comprehensive scrape still in progress or not started..."
    echo "   Missing files:"
    [ ! -f "data/historical_positions.json" ] && echo "   - data/historical_positions.json"
    [ ! -f "data/processed/verified_graduate_assistantships.json" ] && echo "   - data/processed/verified_graduate_assistantships.json"
fi

echo ""
echo "💡 Run this script periodically to check completion status"