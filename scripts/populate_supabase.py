#!/usr/bin/env python3
"""
Populate Supabase database with existing wildlife job data.
This script loads data from JSON files and inserts it into the Supabase database.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import re

# Install required packages: pip install supabase python-dotenv
try:
    from supabase import create_client, Client
    from dotenv import load_dotenv
except ImportError:
    print("Required packages not installed. Run:")
    print("pip install supabase python-dotenv")
    sys.exit(1)

# Load environment variables
load_dotenv()

class SupabasePopulator:
    def __init__(self):
        """Initialize Supabase client."""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            print("Error: Missing Supabase credentials in environment variables.")
            print("Please set SUPABASE_URL and SUPABASE_ANON_KEY in your .env file")
            sys.exit(1)
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        print(f"Connected to Supabase: {self.supabase_url}")

    def load_json_data(self) -> List[Dict[str, Any]]:
        """Load job data from JSON files."""
        # Prioritize the complete datasets over the smaller export files
        possible_paths = [
            Path("data/raw/all_positions_detailed.json"),  # Complete dataset
            Path("data/enhanced_data.json"),  # Enhanced dataset (may be large)
            Path("data/historical_positions.json"),  # Historical data
            Path("dashboard/data/export_data.json"),  # Small export (fallback)
            Path("data/export_data.json"),
            Path("export_data.json")
        ]
        
        for path in possible_paths:
            if path.exists():
                print(f"Loading data from: {path}")
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    print(f"Loaded {len(data)} job records")
                    
                    # Remove duplicates if they exist (based on title + organization + location)
                    if len(data) > 1:
                        seen = set()
                        unique_data = []
                        for job in data:
                            # Create a key for deduplication
                            key = (
                                job.get('title', '').strip(),
                                job.get('organization', '').strip(),
                                job.get('location', '').strip(),
                                job.get('published_date', '').strip()
                            )
                            if key not in seen:
                                seen.add(key)
                                unique_data.append(job)
                        
                        if len(unique_data) != len(data):
                            print(f"Removed {len(data) - len(unique_data)} duplicate jobs")
                            print(f"Final count: {len(unique_data)} unique jobs")
                        data = unique_data
                    
                    return data
                except Exception as e:
                    print(f"Error loading {path}: {e}")
                    continue
        
        raise FileNotFoundError("Could not find any job data files in expected locations")

    def parse_date(self, date_str: str) -> Optional[date]:
        """Parse various date formats to a date object."""
        if not date_str or date_str.lower() in ['none', 'n/a', '']:
            return None
        
        # Common date formats
        formats = [
            '%m/%d/%Y',
            '%Y-%m-%d',
            '%m-%d-%Y',
            '%d/%m/%Y',
            '%Y/%m/%d'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        # Try to extract date from text like "between 1/1/2026 and 6/15/2026"
        date_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_str)
        if date_match:
            try:
                month, day, year = date_match.groups()
                return date(int(year), int(month), int(day))
            except ValueError:
                pass
        
        print(f"Warning: Could not parse date: {date_str}")
        return None

    def transform_job_data(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Transform job data to match database schema."""
        
        # Parse discipline keywords
        discipline_keywords = job.get('discipline_keywords', [])
        if isinstance(discipline_keywords, str):
            discipline_keywords = [discipline_keywords] if discipline_keywords else []
        
        # Parse published date
        published_date = self.parse_date(job.get('published_date', ''))
        
        # Handle scraped_at timestamp
        scraped_at = job.get('scraped_at')
        if scraped_at:
            try:
                scraped_at = datetime.fromisoformat(scraped_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                scraped_at = datetime.now()
        else:
            scraped_at = datetime.now()
        
        transformed = {
            'title': job.get('title', ''),
            'organization': job.get('organization'),
            'location': job.get('location'),
            'salary': job.get('salary'),
            'starting_date': job.get('starting_date'),
            'published_date': published_date.isoformat() if published_date else None,
            'tags': job.get('tags'),
            'url': job.get('url'),
            'description': job.get('description'),
            'requirements': job.get('requirements'),
            'project_details': job.get('project_details'),
            'contact_info': job.get('contact_info'),
            'application_deadline': job.get('application_deadline'),
            
            # Graduate position info
            'is_graduate_position': job.get('is_graduate_position', False),
            'grad_confidence': job.get('grad_confidence'),
            'position_type': job.get('position_type', 'Unknown'),
            
            # Discipline info
            'discipline': job.get('discipline'),
            'discipline_confidence': job.get('discipline_confidence'),
            'discipline_keywords': discipline_keywords,
            
            # University info
            'is_big10_university': job.get('is_big10_university', False),
            'university_name': job.get('university_name'),
            
            # Metadata
            'scraped_at': scraped_at.isoformat(),
            'scrape_run_id': job.get('scrape_run_id'),
            'scraper_version': job.get('scraper_version', '2.0')
        }
        
        # Remove None values to avoid database issues
        return {k: v for k, v in transformed.items() if v is not None}

    def get_existing_job_keys(self) -> set:
        """Get existing job keys to avoid duplicates."""
        print("Fetching existing job keys for duplicate detection...")
        try:
            result = self.supabase.table('jobs').select('title,organization,location,published_date').execute()
            existing_keys = set()
            for job in result.data:
                key = (
                    job.get('title', '').strip(),
                    job.get('organization', '').strip(),
                    job.get('location', '').strip(),
                    job.get('published_date', '').strip()
                )
                existing_keys.add(key)
            print(f"Found {len(existing_keys)} existing job records")
            return existing_keys
        except Exception as e:
            print(f"Error fetching existing jobs: {e}")
            return set()

    def filter_new_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out jobs that already exist in the database."""
        existing_keys = self.get_existing_job_keys()
        new_jobs = []
        duplicates_found = 0
        
        for job in jobs:
            # Create the same key used for deduplication
            key = (
                job.get('title', '').strip(),
                job.get('organization', '').strip(),
                job.get('location', '').strip(),
                str(job.get('published_date', '')).strip()
            )
            
            if key not in existing_keys:
                new_jobs.append(job)
            else:
                duplicates_found += 1
        
        print(f"Filtered out {duplicates_found} duplicate jobs")
        print(f"Will insert {len(new_jobs)} new jobs")
        return new_jobs

    def insert_jobs(self, jobs: List[Dict[str, Any]], batch_size: int = 100):
        """Insert jobs into the database in batches, avoiding duplicates."""
        # Filter out existing jobs
        new_jobs = self.filter_new_jobs(jobs)
        
        if not new_jobs:
            print("No new jobs to insert")
            return 0, 0
            
        print(f"Inserting {len(new_jobs)} new jobs in batches of {batch_size}...")
        
        successful_inserts = 0
        failed_inserts = 0
        
        for i in range(0, len(new_jobs), batch_size):
            batch = new_jobs[i:i + batch_size]
            try:
                result = self.supabase.table('jobs').insert(batch).execute()
                successful_inserts += len(batch)
                print(f"Inserted batch {i//batch_size + 1}: {len(batch)} jobs")
            except Exception as e:
                failed_inserts += len(batch)
                print(f"Error inserting batch {i//batch_size + 1}: {e}")
                
                # Try inserting individual records in this batch
                for job in batch:
                    try:
                        self.supabase.table('jobs').insert([job]).execute()
                        successful_inserts += 1
                        failed_inserts -= 1
                    except Exception as individual_error:
                        print(f"Failed to insert job '{job.get('title', 'Unknown')}': {individual_error}")
        
        print(f"Insert summary: {successful_inserts} successful, {failed_inserts} failed")
        return successful_inserts, failed_inserts

    def verify_data(self):
        """Verify the inserted data."""
        print("\nVerifying inserted data...")
        
        # Get basic counts
        total_result = self.supabase.table('jobs').select('id', count='exact').execute()
        total_count = total_result.count
        
        grad_result = self.supabase.table('jobs').select('id', count='exact').eq('is_graduate_position', True).execute()
        grad_count = grad_result.count
        
        disciplines_result = self.supabase.table('jobs').select('discipline').not_.is_('discipline', 'null').execute()
        unique_disciplines = len(set(job['discipline'] for job in disciplines_result.data if job['discipline']))
        
        print(f"Total jobs: {total_count}")
        print(f"Graduate positions: {grad_count}")
        print(f"Unique disciplines: {unique_disciplines}")
        
        # Test analytics views
        try:
            analytics_result = self.supabase.table('job_analytics').select('*').execute()
            if analytics_result.data:
                analytics = analytics_result.data[0]
                print(f"Analytics view working: {analytics}")
        except Exception as e:
            print(f"Warning: Analytics view may need to be created: {e}")

def main():
    """Main function to populate Supabase with incremental updates."""
    try:
        populator = SupabasePopulator()
        
        # Load data
        jobs_data = populator.load_json_data()
        
        # Transform data
        print("Transforming job data...")
        transformed_jobs = []
        for job in jobs_data:
            try:
                transformed_job = populator.transform_job_data(job)
                transformed_jobs.append(transformed_job)
            except Exception as e:
                print(f"Error transforming job '{job.get('title', 'Unknown')}': {e}")
        
        print(f"Transformed {len(transformed_jobs)} jobs")
        
        # For automation: no user prompt, just append new data
        # For manual use: check if user wants to force a full reset
        import sys
        if len(sys.argv) > 1 and sys.argv[1] == '--reset':
            response = input("WARNING: This will DELETE all existing data. Continue? (y/N): ")
            if response.lower() == 'y':
                print("Clearing existing data...")
                result = populator.supabase.table('jobs').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
                print("Existing data cleared")
            else:
                print("Reset cancelled, proceeding with incremental update")
        
        # Insert jobs (will automatically filter duplicates)
        successful, failed = populator.insert_jobs(transformed_jobs)
        
        # Verify data
        populator.verify_data()
        
        print(f"\n=== SUPABASE UPDATE COMPLETE ===")
        print(f"Successfully inserted: {successful} new jobs")
        print(f"Failed to insert: {failed} jobs")
        if successful > 0:
            print(f"Database now contains updated job listings!")
        else:
            print("No new jobs were added (all jobs already exist)")
        
    except Exception as e:
        print(f"Error updating Supabase: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()