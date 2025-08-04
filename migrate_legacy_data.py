#!/usr/bin/env python3
"""
Migrate legacy local data to Supabase with duplicate detection and removal
Handles JSON files from data/raw/ and data/processed/ directories
"""

import asyncio
import hashlib
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Set

import aiohttp


class SupabaseMigrator:
    def __init__(self):
        self.SUPABASE_URL = "https://mqbkzveymkehgkbcjgba.supabase.co"
        self.SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1xYmt6dmV5bWtlaGdrYmNqZ2JhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDgzNjM0MzYsImV4cCI6MjA2MzkzOTQzNn0.ojHZfb5ydVEVKQShv3pmW8bqXPksBc0jmJOfPz0lqCw"

        self.headers = {
            "apikey": self.SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {self.SUPABASE_ANON_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

        self.duplicate_urls: Set[str] = set()
        self.processed_positions = 0
        self.skipped_duplicates = 0
        self.errors = 0

    def create_position_hash(self, position: Dict[str, Any]) -> str:
        """Create a hash for duplicate detection based on URL and title"""
        url = position.get("url", "")
        title = position.get("title", "")
        org = position.get("organization", "")

        # Normalize for comparison
        content = f"{url.strip().lower()}|{title.strip().lower()}|{org.strip().lower()}"
        return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()

    def normalize_position_data(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize position data for Supabase schema"""

        # Handle salary field - extract numeric value if possible
        salary = position.get("salary", "")
        if isinstance(salary, (int, float)):
            salary = str(salary)

        # Parse published_date
        published_date = position.get("published_date")
        if published_date:
            # Try to parse various date formats
            try:
                if "/" in str(published_date):
                    # MM/DD/YYYY format
                    dt = datetime.strptime(str(published_date), "%m/%d/%Y")
                elif "-" in str(published_date) and len(str(published_date)) == 10:
                    # YYYY-MM-DD format
                    dt = datetime.strptime(str(published_date), "%Y-%m-%d")
                else:
                    dt = None

                published_date = dt.strftime("%Y-%m-%d") if dt else None
            except (ValueError, TypeError):
                published_date = None

        # Ensure discipline_keywords is an array
        discipline_keywords = position.get("discipline_keywords", [])
        if isinstance(discipline_keywords, str):
            discipline_keywords = [discipline_keywords]
        elif not isinstance(discipline_keywords, list):
            discipline_keywords = []

        # Normalize boolean fields
        is_graduate = position.get("is_graduate_position", False)
        if isinstance(is_graduate, str):
            is_graduate = is_graduate.lower() in ["true", "1", "yes"]

        is_big10 = position.get("is_big10_university", False)
        if isinstance(is_big10, str):
            is_big10 = is_big10.lower() in ["true", "1", "yes"]

        # Handle confidence values
        grad_confidence = position.get("grad_confidence")
        if grad_confidence is not None:
            try:
                grad_confidence = float(grad_confidence)
                if grad_confidence > 1:
                    grad_confidence = (
                        grad_confidence / 100.0
                    )  # Convert percentage to decimal
            except (ValueError, TypeError):
                grad_confidence = None

        discipline_confidence = position.get("discipline_confidence")
        if discipline_confidence is not None:
            try:
                discipline_confidence = float(discipline_confidence)
                if discipline_confidence > 1:
                    discipline_confidence = discipline_confidence / 100.0
            except (ValueError, TypeError):
                discipline_confidence = None

        # Get scraped timestamp
        scraped_at = position.get("scraped_at")
        if not scraped_at:
            scraped_at = datetime.utcnow().isoformat() + "Z"

        return {
            "title": position.get("title", "").strip(),
            "organization": position.get("organization", "").strip(),
            "location": position.get("location", "").strip(),
            "salary": salary.strip() if salary else None,
            "starting_date": position.get("starting_date", "").strip() or None,
            "published_date": published_date,
            "tags": position.get("tags", "").strip() or None,
            "url": position.get("url", "").strip(),
            "description": position.get("description", "").strip() or None,
            "requirements": position.get("requirements", "").strip() or None,
            "project_details": position.get("project_details", "").strip() or None,
            "contact_info": position.get("contact_info", "").strip() or None,
            "application_deadline": position.get("application_deadline", "").strip()
            or None,
            "is_graduate_position": is_graduate,
            "grad_confidence": grad_confidence,
            "position_type": position.get("position_type", "Unknown"),
            "discipline": position.get("discipline", "").strip() or None,
            "discipline_confidence": discipline_confidence,
            "discipline_keywords": discipline_keywords,
            "is_big10_university": is_big10,
            "university_name": position.get("university_name", "").strip() or None,
            "scraped_at": scraped_at,
            "scrape_run_id": position.get(
                "scrape_run_id", f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            ),
            "scraper_version": position.get("scraper_version", "2.0"),
        }

    async def fetch_existing_urls(self, session: aiohttp.ClientSession) -> Set[str]:
        """Fetch existing URLs from Supabase to avoid duplicates"""
        print("🔍 Fetching existing URLs from Supabase...")

        try:
            async with session.get(
                f"{self.SUPABASE_URL}/rest/v1/jobs?select=url", headers=self.headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    urls = {item["url"] for item in data if item.get("url")}
                    print(f"   Found {len(urls)} existing URLs")
                    return urls
                else:
                    print(
                        f"   Warning: Could not fetch existing URLs (HTTP {response.status})"
                    )
                    return set()
        except Exception as e:
            print(f"   Warning: Error fetching existing URLs: {e}")
            return set()

    async def insert_positions_batch(
        self, session: aiohttp.ClientSession, positions: List[Dict[str, Any]]
    ) -> bool:
        """Insert a batch of positions into Supabase"""
        if not positions:
            return True

        try:
            async with session.post(
                f"{self.SUPABASE_URL}/rest/v1/jobs",
                headers=self.headers,
                json=positions,
            ) as response:
                if response.status in [200, 201]:
                    result = await response.json()
                    inserted_count = len(result) if isinstance(result, list) else 1
                    print(f"   ✅ Inserted {inserted_count} positions")
                    return True
                else:
                    error_text = await response.text()
                    print(f"   ❌ Insert failed (HTTP {response.status}): {error_text}")
                    return False
        except Exception as e:
            print(f"   ❌ Insert error: {e}")
            return False

    def load_json_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Load and validate JSON file"""
        print(f"📂 Loading {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                print(f"   Found {len(data)} positions")
                return data
            elif isinstance(data, dict):
                print("   Found single position object")
                return [data]
            else:
                print("   ❌ Invalid JSON structure")
                return []

        except FileNotFoundError:
            print(f"   ⚠️ File not found: {file_path}")
            return []
        except json.JSONDecodeError as e:
            print(f"   ❌ JSON decode error: {e}")
            return []
        except Exception as e:
            print(f"   ❌ Error loading file: {e}")
            return []

    async def migrate_file(self, session: aiohttp.ClientSession, file_path: str):
        """Migrate a single JSON file"""
        positions = self.load_json_file(file_path)
        if not positions:
            return

        batch = []
        batch_size = 100  # Supabase has row limits

        for position in positions:
            # Check for duplicates
            url = position.get("url", "").strip()
            if not url:
                print(
                    f"   ⚠️ Skipping position without URL: {position.get('title', 'Unknown')}"
                )
                continue

            if url in self.duplicate_urls:
                self.skipped_duplicates += 1
                continue

            # Normalize the position data
            try:
                normalized = self.normalize_position_data(position)
                batch.append(normalized)
                self.duplicate_urls.add(url)

                # Insert batch when it reaches batch_size
                if len(batch) >= batch_size:
                    success = await self.insert_positions_batch(session, batch)
                    if success:
                        self.processed_positions += len(batch)
                    else:
                        self.errors += len(batch)
                    batch = []

            except Exception as e:
                print(f"   ❌ Error normalizing position: {e}")
                self.errors += 1

        # Insert remaining batch
        if batch:
            success = await self.insert_positions_batch(session, batch)
            if success:
                self.processed_positions += len(batch)
            else:
                self.errors += len(batch)

    async def migrate_all_data(self):
        """Migrate all legacy data files"""
        print("🚀 Starting Legacy Data Migration")
        print("=" * 60)

        # Define files to migrate (in order of preference)
        data_files = [
            "data/raw/all_positions_detailed.json",
            "data/processed/verified_graduate_assistantships.json",
            "data/processed/enhanced_analysis.json",
            "data/historical_positions.json",  # Root level backup
        ]

        async with aiohttp.ClientSession() as session:
            # Fetch existing URLs to avoid duplicates
            self.duplicate_urls = await self.fetch_existing_urls(session)

            print(f"\n📋 Migrating {len(data_files)} data files...")

            for file_path in data_files:
                full_path = os.path.join(
                    "/Users/cchizinski2/Dev/wildlife-grad-dashboard", file_path
                )
                if os.path.exists(full_path):
                    await self.migrate_file(session, full_path)
                else:
                    print(f"⚠️ File not found: {file_path}")

        print("\n" + "=" * 60)
        print("📊 MIGRATION SUMMARY")
        print("=" * 60)
        print(f"✅ Positions processed: {self.processed_positions}")
        print(f"⏭️ Duplicates skipped: {self.skipped_duplicates}")
        print(f"❌ Errors: {self.errors}")
        print(f"📈 Total unique positions: {len(self.duplicate_urls)}")

        if self.errors == 0:
            print("\n🎉 Migration completed successfully!")
            print("Run 'python test_dashboard.py' to verify the data")
        else:
            print(f"\n⚠️ Migration completed with {self.errors} errors")
            print("Check the output above for details")


if __name__ == "__main__":
    migrator = SupabaseMigrator()
    asyncio.run(migrator.migrate_all_data())
