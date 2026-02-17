#!/usr/bin/env python3
"""
Test the dashboard frontend functionality
"""

import aiohttp
import asyncio

async def test_dashboard_frontend():
    """Test if the dashboard loads and basic functionality works"""
    
    dashboard_url = "http://localhost:8081/wildlife_dashboard.html"
    
    print("🌐 Testing Dashboard Frontend")
    print("="*60)
    
    async with aiohttp.ClientSession() as session:
        try:
            print(f"📱 Testing dashboard load at {dashboard_url}")
            async with session.get(dashboard_url) as response:
                if response.status == 200:
                    content = await response.text()
                    
                    # Check for key elements
                    checks = [
                        ("HTML structure", "<html" in content and "</html>" in content),
                        ("Title", "Wildlife Graduate Assistantships Dashboard" in content),
                        ("Supabase config", "supabase-config.js" in content),
                        ("Dashboard JS", "supabase-dashboard.js" in content),
                        ("Context banner", 'id="context-banner"' in content),
                        ("Graduate positions card", "Graduate Positions" in content),
                        ("Status banner", 'id="status-banner"' in content),
                        ("Chart.js", "chart.js" in content),
                        ("Bootstrap", "bootstrap" in content)
                    ]
                    
                    print("✅ Dashboard HTML loaded successfully")
                    print("\n📋 Component Check:")
                    
                    all_passed = True
                    for check_name, passed in checks:
                        status = "✅" if passed else "❌"
                        print(f"{status} {check_name}")
                        if not passed:
                            all_passed = False
                    
                    if all_passed:
                        print(f"\n🎉 Dashboard is ready! Open: {dashboard_url}")
                        print("\n📋 Manual Testing Checklist:")
                        print("1. Open the URL in your browser")
                        print("2. Check if the context banner shows '# positions analyzed, # identified as graduate'")
                        print("3. Verify all cards show graduate-specific metrics")
                        print("4. Confirm charts display graduate data only")
                        print("5. Check the connection status (should show Supabase connected)")
                        return True
                    else:
                        print("\n❌ Some components missing - check the dashboard code")
                        return False
                        
                else:
                    print(f"❌ Dashboard failed to load: HTTP {response.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error testing dashboard: {e}")
            print("🔧 Make sure the server is running:")
            print("   python -m http.server 8081 --directory dashboard")
            return False

if __name__ == "__main__":
    result = asyncio.run(test_dashboard_frontend())
    exit(0 if result else 1)