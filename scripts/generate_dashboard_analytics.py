#!/usr/bin/env python3
"""
Generate dashboard analytics with historical data merging.

This script:
1. Loads data from multiple sources (historical + latest scrape)
2. Merges and deduplicates positions by URL
3. Consolidates disciplines into 6 main categories
4. Generates comprehensive analytics
5. Saves to dashboard locations
"""

import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Discipline consolidation mapping
DISCIPLINE_MAPPING = {
    # Environmental Science
    "Environmental Science": "Environmental Science",
    "Ecology": "Environmental Science",
    "Natural Resource Management": "Environmental Science",
    # Wildlife
    "Wildlife Management and Conservation": "Wildlife",
    "Wildlife Management": "Wildlife",
    "Wildlife & Natural Resources": "Wildlife",
    "Conservation": "Wildlife",
    # Fisheries
    "Fisheries": "Fisheries",
    "Fisheries & Aquatic Science": "Fisheries",
    "Fisheries Management and Conservation": "Fisheries",
    "Marine Science": "Fisheries",
    # Human Dimensions
    "Human Dimensions": "Human Dimensions",
    # Forestry
    "Forestry": "Forestry",
    # Other
    "Other": "Other",
    "Unknown": "Other",
}


def normalize_discipline(disc: str) -> str:
    """Map a discipline to one of the 6 main categories."""
    if not disc or disc == "":
        return "Other"
    return DISCIPLINE_MAPPING.get(disc, "Other")


def load_and_merge_data() -> List[Dict[str, Any]]:
    """Load data from multiple sources and merge, deduplicating by URL."""
    all_positions = []

    print("Loading data from multiple sources...")

    # Source 1: Historical positions (if exists)
    hist_path = Path("data/raw/historical_positions.json")
    if hist_path.exists():
        try:
            with open(hist_path, "r", encoding="utf-8") as f:
                hist = json.load(f)
                grad_hist = [p for p in hist if p.get("is_graduate_position")]
                all_positions.extend(grad_hist)
                print(f"  ✓ Historical data: {len(grad_hist)} graduate positions")
        except Exception as e:
            print(f"  ✗ Historical data error: {e}")

    # Source 2: Latest scrape
    latest_paths = [
        Path("data/processed/verified_graduate_assistantships.json"),
        Path("data/processed/dev_verified_graduate_assistantships.json"),
    ]

    for path in latest_paths:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    latest = json.load(f)
                    all_positions.extend(latest)
                    print(f"  ✓ Latest scrape ({path.name}): {len(latest)} positions")
                break
            except Exception as e:
                print(f"  ✗ Latest scrape error: {e}")

    # Source 3: Enhanced data (if exists)
    enhanced_path = Path("web/data/enhanced_data.json")
    if enhanced_path.exists():
        try:
            with open(enhanced_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                enhanced = (
                    data.get("positions", data) if isinstance(data, dict) else data
                )
                grad_enhanced = [p for p in enhanced if p.get("is_graduate_position")]

                # Only add if not already present (check by URL)
                existing_urls = {p.get("url") for p in all_positions if p.get("url")}
                new_enhanced = [
                    p for p in grad_enhanced if p.get("url") not in existing_urls
                ]
                all_positions.extend(new_enhanced)
                print(f"  ✓ Enhanced data: {len(new_enhanced)} new positions")
        except Exception as e:
            print(f"  ✗ Enhanced data error: {e}")

    # Deduplicate by URL (keep most recent version)
    unique_positions = {}
    for p in all_positions:
        url = p.get("url")
        if url:
            unique_positions[url] = p  # Last one wins (most recent)
        else:
            # No URL, keep all
            unique_positions[str(id(p))] = p

    positions = list(unique_positions.values())
    print(f"\n📊 Merged dataset: {len(positions)} unique graduate positions\n")

    return positions


def extract_salary_number(salary_str: Any) -> Optional[float]:
    """Extract numeric salary from string."""
    if not salary_str or salary_str in ["", "N/A", "Unknown", "None"]:
        return None

    salary_str = str(salary_str).lower()
    salary_str = re.sub(r"[,$]", "", salary_str)

    match = re.search(r"(\d+\.?\d*)", salary_str)
    if match:
        num = float(match.group(1))
        # Convert hourly to annual
        if "hour" in salary_str or "hr" in salary_str:
            num = num * 2000
        # Reasonable annual salary range
        if 15000 < num < 200000:
            return num
    return None


def calculate_analytics(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate comprehensive analytics with consolidated disciplines."""

    total_positions = len(data)

    # Discipline analysis with consolidation
    discipline_data = defaultdict(lambda: {"count": 0, "salaries": []})
    for p in data:
        # Get original discipline
        original_disc = (
            p.get("discipline")
            or p.get("discipline_primary")
            or p.get("discipline_secondary")
            or "Unknown"
        )

        # Normalize to one of 6 categories
        normalized_disc = normalize_discipline(original_disc)
        discipline_data[normalized_disc]["count"] += 1

        salary = extract_salary_number(p.get("salary"))
        if salary:
            discipline_data[normalized_disc]["salaries"].append(salary)

    # Build top disciplines (should only be 6)
    top_disciplines = {}
    for discipline in [
        "Environmental Science",
        "Wildlife",
        "Fisheries",
        "Human Dimensions",
        "Forestry",
        "Other",
    ]:
        if discipline in discipline_data:
            data_dict = discipline_data[discipline]
            count = data_dict["count"]
            salaries = data_dict["salaries"]

            salary_stats = {
                "count": len(salaries),
                "mean": round(statistics.mean(salaries), 2) if salaries else 0,
                "median": round(statistics.median(salaries), 2) if salaries else 0,
                "min": round(min(salaries), 2) if salaries else 0,
                "max": round(max(salaries), 2) if salaries else 0,
            }

            top_disciplines[discipline] = {
                "total_positions": count,
                "grad_positions": count,
                "salary_stats": salary_stats,
            }

    positions_with_salary = sum(
        1 for p in data if extract_salary_number(p.get("salary"))
    )

    # Geographic summary
    location_counts = Counter()
    for p in data:
        loc = p.get("location", "")
        if loc:
            parts = [part.strip() for part in loc.split(",")]
            if parts:
                location = parts[-1] if len(parts[-1]) < 20 else parts[0]
                location_counts[location] += 1

    # Time series with normalized disciplines
    monthly_counts = defaultdict(int)
    monthly_by_discipline = defaultdict(lambda: defaultdict(int))

    for p in data:
        date_fields = ["scraped_at", "last_updated", "first_seen", "published_date"]
        date_str = None
        for field in date_fields:
            if p.get(field):
                date_str = p[field]
                break

        if date_str:
            try:
                if "T" in str(date_str):
                    month = str(date_str).split("T")[0][:7]
                elif "/" in str(date_str):
                    parts = str(date_str).split("/")
                    if len(parts) >= 3:
                        year = parts[2] if len(parts[2]) == 4 else f"20{parts[2]}"
                        month = f"{year}-{parts[0].zfill(2)}"
                    else:
                        continue
                else:
                    month = str(date_str)[:7]

                monthly_counts[month] += 1

                # Normalize discipline for time series
                original_disc = (
                    p.get("discipline") or p.get("discipline_primary") or "Unknown"
                )
                normalized_disc = normalize_discipline(original_disc)
                monthly_by_discipline[normalized_disc][month] += 1
            except:
                pass

    sorted_months = sorted(monthly_counts.keys())

    time_series = {}
    for timeframe in ["1_month", "3_month", "6_month", "12_month"]:
        time_series[timeframe] = {
            "total_monthly": {month: monthly_counts[month] for month in sorted_months},
            "discipline_monthly": {
                disc: dict(monthly_by_discipline[disc])
                for disc in monthly_by_discipline
            },
        }

    return {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_positions": total_positions,
            "source": "merged (historical + latest + enhanced)",
            "discipline_mapping": "consolidated to 6 categories",
        },
        "summary_stats": {
            "total_positions": total_positions,
            "graduate_positions": total_positions,
            "positions_with_salary": positions_with_salary,
        },
        "top_disciplines": top_disciplines,
        "geographic_summary": dict(location_counts.most_common(25)),
        "time_series": time_series,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def main():
    """Main execution."""
    try:
        # Load and merge data
        data = load_and_merge_data()

        if not data:
            print("❌ No data found!")
            sys.exit(1)

        # Calculate analytics
        print("Calculating analytics...")
        analytics = calculate_analytics(data)

        # Save analytics to multiple locations
        analytics_output_paths = [
            Path("dashboard/data/dashboard_analytics.json"),
            Path("web/data/dashboard_analytics.json"),
        ]

        for path in analytics_output_paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(analytics, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved: {path} ({path.stat().st_size / 1024:.1f} KB)")

        # Save the exact merged graduate dataset used for analytics so the
        # frontend can use one consistent source for listings/KPI calculations.
        positions_output_paths = [
            Path("dashboard/data/dashboard_positions.json"),
            Path("web/data/dashboard_positions.json"),
        ]

        for path in positions_output_paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved: {path} ({path.stat().st_size / 1024:.1f} KB)")

        # Print summary
        print("\n📊 Analytics Summary:")
        print(f"  Total positions: {analytics['summary_stats']['total_positions']}")
        print(f"  With salary: {analytics['summary_stats']['positions_with_salary']}")
        print("  Disciplines:")
        for disc, data in analytics["top_disciplines"].items():
            avg = data["salary_stats"]["mean"]
            salary_str = f"${avg:,.0f}" if avg > 0 else "N/A"
            print(
                f"    {disc:25s} {data['total_positions']:3d} positions (avg: {salary_str})"
            )

        print("\n✅ Dashboard analytics generated successfully!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
