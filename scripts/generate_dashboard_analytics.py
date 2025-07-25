#!/usr/bin/env python3
"""
Generate lightweight analytics summary for the dashboard.
This creates a small JSON file with only the essential aggregated data needed for visualization.

The script processes the full archived data to generate a compact analytics file suitable for
GitHub Pages deployment while keeping the full dataset archived for long-term trend analysis.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
import statistics

def load_data():
    """Load the export data from various possible locations."""
    possible_paths = [
        Path("dashboard/data/export_data.json"),
        Path("data/export_data.json"),
        Path("export_data.json")
    ]
    
    for path in possible_paths:
        if path.exists():
            print(f"Loading data from: {path}")
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    raise FileNotFoundError("Could not find export_data.json in any expected location")

def archive_data(data, analytics):
    """Archive the full dataset with timestamp for long-term analysis."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create archive directory
    archive_dir = Path("data/archive")
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    # Archive full export data
    export_archive_path = archive_dir / f"export_data_{timestamp}.json"
    with open(export_archive_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Archive analytics summary
    analytics_archive_path = archive_dir / f"analytics_{timestamp}.json"
    with open(analytics_archive_path, 'w', encoding='utf-8') as f:
        json.dump(analytics, f, indent=2, ensure_ascii=False)
    
    print(f"Archived full data: {export_archive_path}")
    print(f"Archived analytics: {analytics_archive_path}")
    
    return export_archive_path, analytics_archive_path

def calculate_analytics(data):
    """Calculate analytics from the raw job data."""
    
    # Initialize counters
    total_positions = len(data)
    grad_positions = 0
    salary_positions = 0
    disciplines = defaultdict(lambda: {
        'total_positions': 0,
        'grad_positions': 0,
        'salaries': []
    })
    
    geographic_dist = Counter()
    monthly_counts = defaultdict(int)
    discipline_monthly = defaultdict(lambda: defaultdict(int))
    
    # Process each job
    for job in data:
        # Count graduate positions
        if job.get('is_graduate_position', False):
            grad_positions += 1
        
        # Count positions with salaries
        salary = job.get('salary', '').strip().lower()
        if salary and salary != 'none' and salary != 'n/a' and '$' in salary:
            salary_positions += 1
            
            # Extract numeric salary if possible
            try:
                # Simple salary extraction - look for numbers after $
                salary_nums = []
                parts = salary.replace(',', '').split()
                for part in parts:
                    if '$' in part:
                        num_str = part.replace('$', '').replace(',', '')
                        # Handle ranges like "$25,000 to $30,000"
                        if 'to' in salary or '-' in salary:
                            # Take average of range
                            nums = [float(x.replace('$', '').replace(',', '')) for x in salary.replace(' to ', '-').replace('$', '').replace(',', '').split('-') if x.replace('.', '').isdigit()]
                            if nums:
                                salary_nums.append(sum(nums) / len(nums))
                        elif num_str.replace('.', '').isdigit():
                            salary_nums.append(float(num_str))
                
                if salary_nums:
                    avg_salary = sum(salary_nums) / len(salary_nums)
                    discipline = job.get('discipline', 'Unknown')
                    disciplines[discipline]['salaries'].append(avg_salary)
            except (ValueError, TypeError):
                pass
        
        # Count by discipline
        discipline = job.get('discipline', 'Unknown')
        disciplines[discipline]['total_positions'] += 1
        if job.get('is_graduate_position', False):
            disciplines[discipline]['grad_positions'] += 1
        
        # Geographic distribution
        location = job.get('location', '')
        if location:
            # Extract state/country from location
            location_parts = location.split(',')
            if len(location_parts) >= 2:
                state = location_parts[-1].strip()
                geographic_dist[state] += 1
        
        # Time series data
        published_date = job.get('published_date', '')
        if published_date:
            try:
                # Handle different date formats
                if '/' in published_date:
                    date_obj = datetime.strptime(published_date, '%m/%d/%Y')
                else:
                    date_obj = datetime.strptime(published_date, '%Y-%m-%d')
                
                month_key = date_obj.strftime('%Y-%m')
                monthly_counts[month_key] += 1
                discipline_monthly[discipline][month_key] += 1
            except (ValueError, TypeError):
                pass
    
    # Calculate salary statistics for each discipline
    discipline_stats = {}
    for discipline, info in disciplines.items():
        if info['salaries']:
            discipline_stats[discipline] = {
                'total_positions': info['total_positions'],
                'grad_positions': info['grad_positions'],
                'salary_stats': {
                    'count': len(info['salaries']),
                    'mean': statistics.mean(info['salaries']),
                    'median': statistics.median(info['salaries']),
                    'min': min(info['salaries']),
                    'max': max(info['salaries'])
                }
            }
        else:
            discipline_stats[discipline] = {
                'total_positions': info['total_positions'],
                'grad_positions': info['grad_positions'],
                'salary_stats': None
            }
    
    # Prepare time series data for different periods
    time_series = {
        '1_month': {
            'total_monthly': dict(sorted(monthly_counts.items())[-1:]),
            'discipline_monthly': {
                disc: dict(sorted(months.items())[-1:]) 
                for disc, months in discipline_monthly.items()
            }
        },
        '3_month': {
            'total_monthly': dict(sorted(monthly_counts.items())[-3:]),
            'discipline_monthly': {
                disc: dict(sorted(months.items())[-3:]) 
                for disc, months in discipline_monthly.items()
            }
        },
        '6_month': {
            'total_monthly': dict(sorted(monthly_counts.items())[-6:]),
            'discipline_monthly': {
                disc: dict(sorted(months.items())[-6:]) 
                for disc, months in discipline_monthly.items()
            }
        },
        '1_year': {
            'total_monthly': dict(sorted(monthly_counts.items())[-12:]),
            'discipline_monthly': {
                disc: dict(sorted(months.items())[-12:]) 
                for disc, months in discipline_monthly.items()
            }
        },
        'all_time': {
            'total_monthly': dict(sorted(monthly_counts.items())),
            'discipline_monthly': {
                disc: dict(sorted(months.items())) 
                for disc, months in discipline_monthly.items()
            }
        }
    }
    
    # Get top 10 geographic locations
    top_geographic = dict(geographic_dist.most_common(10))
    
    return {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'total_positions': total_positions
        },
        'summary_stats': {
            'total_positions': total_positions,
            'graduate_positions': grad_positions,
            'positions_with_salary': salary_positions
        },
        'top_disciplines': {k: v for k, v in sorted(discipline_stats.items(), 
                                                  key=lambda x: x[1]['grad_positions'], 
                                                  reverse=True)[:10]},
        'geographic_summary': top_geographic,
        'time_series': time_series,
        'last_updated': datetime.now().isoformat()
    }

def main():
    """Main function to generate analytics."""
    try:
        # Load data
        data = load_data()
        print(f"Loaded {len(data)} job records")
        
        # Calculate analytics
        analytics = calculate_analytics(data)
        
        # Determine output path
        output_paths = [
            Path("dashboard/data/dashboard_analytics.json"),
            Path("data/dashboard_analytics.json"),
            Path("dashboard_analytics.json")
        ]
        
        output_path = output_paths[0]  # Default to dashboard/data/
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write analytics
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analytics, f, indent=2, ensure_ascii=False)
        
        print(f"Generated analytics summary: {output_path}")
        print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")
        print(f"Total positions: {analytics['summary_stats']['total_positions']}")
        print(f"Graduate positions: {analytics['summary_stats']['graduate_positions']}")
        print(f"Top disciplines: {list(analytics['top_disciplines'].keys())[:5]}")
        
    except Exception as e:
        print(f"Error generating analytics: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()