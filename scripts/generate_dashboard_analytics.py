#!/usr/bin/env python3
"""
Generate dashboard analytics with historical data merging.

This script:
1. Loads data from multiple sources (historical + latest scrape)
2. Merges and deduplicates positions by URL
3. Consolidates disciplines into 8 canonical categories
4. Generates comprehensive analytics
5. Saves to dashboard locations
"""

import csv
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure src/ is importable when running as a script.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from wildlife_grad.analysis.enhanced_analysis import (
    DisciplineClassifier,
    GraduatePositionDetector,
    JobPosition,
)

# Discipline consolidation mapping
DISCIPLINE_MAPPING = {
    # Environmental Sciences (abiotic/soil/water focus)
    "Environmental Science": "Environmental Sciences",
    "Environmental Sciences": "Environmental Sciences",
    "Ecology": "Environmental Sciences",
    # Fisheries and Aquatic
    "Fisheries": "Fisheries and Aquatic",
    "Fisheries and Aquatic": "Fisheries and Aquatic",
    "Fisheries & Aquatic Science": "Fisheries and Aquatic",
    "Fisheries Management and Conservation": "Fisheries and Aquatic",
    "Marine Science": "Fisheries and Aquatic",
    # Wildlife (terrestrial organism focus)
    "Wildlife": "Wildlife",
    "Wildlife Management and Conservation": "Wildlife",
    "Wildlife Management": "Wildlife",
    "Wildlife & Natural Resources": "Wildlife",
    "Conservation": "Wildlife",
    # Entomology
    "Entomology": "Entomology",
    # Forestry and Habitat
    "Forestry": "Forestry and Habitat",
    "Forestry and Habitat": "Forestry and Habitat",
    "Natural Resource Management": "Forestry and Habitat",
    # Agriculture
    "Agriculture": "Agriculture",
    "Agricultural Science": "Agriculture",
    "Animal Science": "Agriculture",
    "Agronomy": "Agriculture",
    "Range Management": "Agriculture",
    # Human Dimensions
    "Human Dimensions": "Human Dimensions",
    # Other
    "Other": "Other",
    "Unknown": "Other",
    "Non-Graduate": "Other",
}

DISCIPLINE_DISPLAY_ORDER = [
    "Environmental Sciences",
    "Fisheries and Aquatic",
    "Wildlife",
    "Entomology",
    "Forestry and Habitat",
    "Agriculture",
    "Human Dimensions",
    "Other",
]
DISCIPLINE_ORDER_INDEX = {name: idx for idx, name in enumerate(DISCIPLINE_DISPLAY_ORDER)}
DISCIPLINE_CONFIDENCE_QUEUE_JSON = Path("data/processed/discipline_confidence_queue.json")
DISCIPLINE_CONFIDENCE_QUEUE_CSV = Path("data/processed/discipline_confidence_queue.csv")
WEB_DISCIPLINE_CONFIDENCE_QUEUE_JSON = Path("web/data/discipline_confidence_queue.json")


def normalize_discipline(disc: str) -> str:
    """Map a discipline to one of the 8 canonical categories."""
    if not disc or disc == "":
        return "Other"
    return DISCIPLINE_MAPPING.get(disc, "Other")


def discipline_sort_key(discipline: str) -> tuple[int, int, str]:
    """
    Stable discipline sort key for dashboard/report consistency.

    - Canonical categories follow DISCIPLINE_DISPLAY_ORDER
    - Non-canonical categories come after canonical categories
    - "Other" is always last
    """
    normalized = normalize_discipline(discipline)
    if normalized == "Other":
        return (2, 0, "Other")

    order_idx = DISCIPLINE_ORDER_INDEX.get(normalized)
    if order_idx is not None:
        return (0, order_idx, normalized)

    return (1, 0, normalized)


def sort_disciplines(disciplines: List[str]) -> List[str]:
    """Sort discipline names with canonical order and Other-last rule."""
    return sorted(disciplines, key=discipline_sort_key)


def _build_row_key(row: Dict[str, Any]) -> str:
    """Build a stable dedupe key for rows with and without URLs."""
    title = str(row.get("title") or "").strip().lower()
    org = str(row.get("organization") or "").strip().lower()
    location = str(row.get("location") or "").strip().lower()
    published = str(row.get("published_date") or "").strip().lower()
    if title and org:
        return f"title_org::{title}::{org}::{location}::{published}"

    url = str(row.get("url") or "").strip().lower()
    if url:
        return f"url::{url}"

    if title:
        return f"title::{title}::{published}"
    return ""


def _row_quality_score(row: Dict[str, Any]) -> int:
    """Prefer rows with richer data when dedupe keys collide."""
    score = 0
    if str(row.get("url") or "").strip():
        score += 5
    if str(row.get("description") or "").strip():
        score += 3
    if str(row.get("discipline_primary") or row.get("discipline") or "").strip():
        score += 2
    if str(row.get("salary") or "").strip():
        score += 1
    return score


def _to_job_position(row: Dict[str, Any]) -> JobPosition:
    """Convert flexible row dictionaries to JobPosition for re-screening."""
    return JobPosition(
        title=str(row.get("title") or ""),
        organization=str(row.get("organization") or ""),
        location=str(row.get("location") or ""),
        salary=str(row.get("salary") or ""),
        starting_date=str(row.get("starting_date") or ""),
        published_date=str(row.get("published_date") or ""),
        tags=str(row.get("tags") or ""),
        description=str(row.get("description") or ""),
        discipline_primary=str(row.get("discipline_primary") or ""),
        discipline_secondary=str(row.get("discipline_secondary") or ""),
        scraped_at=str(row.get("scraped_at") or ""),
        first_seen=str(row.get("first_seen") or ""),
        last_updated=str(row.get("last_updated") or ""),
        scrape_run_id=str(row.get("scrape_run_id") or ""),
        scraper_version=str(row.get("scraper_version") or ""),
    )


def build_discipline_confidence_queue(
    rows: List[Dict[str, Any]],
    classifier: DisciplineClassifier,
) -> List[Dict[str, Any]]:
    """Build a review queue for uncertain/Other discipline assignments."""
    queue: List[Dict[str, Any]] = []
    for row in rows:
        position = _to_job_position(row)
        final_primary = normalize_discipline(
            str(row.get("discipline_primary") or row.get("discipline") or "Other")
        )
        pred = classifier.predict_with_promoted_model(position)
        model_available = bool(pred.get("available"))
        model_primary = normalize_discipline(str(pred.get("primary") or "Other"))
        model_secondary = normalize_discipline(str(pred.get("secondary") or ""))
        model_conf = float(pred.get("confidence") or 0.0)
        model_margin = float(pred.get("margin") or 0.0)
        model_id = str(pred.get("model_id") or "")

        reasons: List[str] = []
        if final_primary == "Other":
            reasons.append("final_other")
        if not model_available and final_primary == "Other":
            reasons.append("no_promoted_model")
        if model_available:
            if final_primary == "Other":
                if (
                    model_primary != "Other"
                    and model_conf >= 0.6
                    and model_margin >= 0.08
                ):
                    reasons.append("suggested_relabel")
                else:
                    reasons.append("still_other_low_signal")
            elif (
                model_primary
                and model_primary != "Other"
                and model_primary != final_primary
                and model_conf >= 0.7
                and model_margin >= 0.1
            ):
                reasons.append("model_rule_disagreement")

        if not reasons:
            continue

        severity = len(reasons)
        if "model_rule_disagreement" in reasons:
            severity += 1
        if "final_other" in reasons:
            severity += 1

        queue.append(
            {
                "severity": severity,
                "reasons": reasons,
                "position_key": _build_row_key(row),
                "discipline_final": final_primary,
                "discipline_model_suggested": model_primary,
                "discipline_model_secondary": (
                    model_secondary
                    if model_secondary
                    and model_secondary != "Other"
                    and model_secondary != model_primary
                    else ""
                ),
                "model_id": model_id,
                "model_confidence": round(model_conf, 4),
                "model_margin": round(model_margin, 4),
                "title": str(row.get("title") or ""),
                "organization": str(row.get("organization") or ""),
                "location": str(row.get("location") or ""),
                "url": str(row.get("url") or ""),
                "published_date": str(row.get("published_date") or ""),
                "discipline_refinement_source": str(
                    row.get("discipline_refinement_source") or "rule"
                ),
                "review_status": "",
                "reviewed_discipline": "",
                "review_notes": "",
                "reviewer": "",
            }
        )

    queue.sort(
        key=lambda item: (
            int(item.get("severity") or 0),
            -float(item.get("model_confidence") or 0.0),
            str(item.get("title") or ""),
        ),
        reverse=True,
    )
    return queue


def write_discipline_confidence_queue(queue: List[Dict[str, Any]]) -> None:
    """Persist uncertainty review queue in JSON and CSV formats."""
    payload = {
        "generated_at": datetime.now().isoformat(),
        "count": len(queue),
        "items": queue,
    }

    for out_path in [DISCIPLINE_CONFIDENCE_QUEUE_JSON, WEB_DISCIPLINE_CONFIDENCE_QUEUE_JSON]:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    DISCIPLINE_CONFIDENCE_QUEUE_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "severity",
        "reasons",
        "position_key",
        "discipline_final",
        "discipline_model_suggested",
        "discipline_model_secondary",
        "model_id",
        "model_confidence",
        "model_margin",
        "discipline_refinement_source",
        "review_status",
        "reviewed_discipline",
        "review_notes",
        "reviewer",
        "title",
        "organization",
        "location",
        "published_date",
        "url",
    ]
    with open(DISCIPLINE_CONFIDENCE_QUEUE_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in queue:
            row_out = dict(row)
            row_out["reasons"] = ";".join(row.get("reasons") or [])
            writer.writerow(row_out)


def sanitize_and_classify_positions(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Apply strict graduate guardrails + canonical discipline classification.

    This prevents leakage (postdocs/professional roles) and avoids Unknown-heavy
    listings before dashboard artifacts are generated.
    """
    grad_detector = GraduatePositionDetector()
    discipline_classifier = DisciplineClassifier()

    first_pass_rows: List[Dict[str, Any]] = []
    first_pass_positions: List[JobPosition] = []
    first_pass_primary: List[str] = []
    first_pass_secondary: List[str] = []

    for row in rows:
        pos = _to_job_position(row)
        is_grad, position_type, grad_conf = grad_detector.is_graduate_position(pos)
        if not is_grad:
            continue

        predicted_primary, predicted_secondary = discipline_classifier.classify_position(pos)
        predicted_primary_norm = normalize_discipline(predicted_primary)
        predicted_secondary_norm = normalize_discipline(predicted_secondary)
        secondary_final = (
            predicted_secondary_norm
            if predicted_secondary_norm != predicted_primary_norm
            and predicted_secondary_norm != "Other"
            else ""
        )

        out = dict(row)
        out["is_graduate_position"] = True
        out["position_type"] = position_type
        out["grad_confidence"] = grad_conf
        first_pass_rows.append(out)
        first_pass_positions.append(pos)
        first_pass_primary.append(predicted_primary_norm)
        first_pass_secondary.append(secondary_final)

    if not first_pass_rows:
        return []

    refined_primary, refined_secondary = discipline_classifier.refine_other_labels_with_secondary_ml(
        first_pass_positions,
        first_pass_primary,
        first_pass_secondary,
    )

    relabeled = sum(
        1 for before, after in zip(first_pass_primary, refined_primary) if before != after
    )
    if relabeled:
        print(
            f"  ↳ Secondary ML relabeled {relabeled} first-pass 'Other' postings"
        )

    promoted_primary, promoted_secondary = (
        discipline_classifier.refine_other_labels_with_promoted_model(
            first_pass_positions,
            refined_primary,
            refined_secondary,
        )
    )
    promoted_relabeled = sum(
        1 for before, after in zip(refined_primary, promoted_primary) if before != after
    )
    if promoted_relabeled:
        print(
            f"  ↳ Promoted model relabeled {promoted_relabeled} additional 'Other' postings"
        )

    cleaned_rows: List[Dict[str, Any]] = []
    for idx, (out, primary, secondary) in enumerate(
        zip(first_pass_rows, promoted_primary, promoted_secondary)
    ):
        primary_final = normalize_discipline(primary)
        secondary_norm = normalize_discipline(secondary)
        secondary_final = (
            secondary_norm
            if secondary_norm != primary_final and secondary_norm != "Other"
            else ""
        )

        first_primary = first_pass_primary[idx]
        after_secondary = refined_primary[idx]
        if primary_final == first_primary:
            refinement_source = "rule"
        elif after_secondary != first_primary and primary_final == after_secondary:
            refinement_source = "secondary_ml"
        elif primary_final != after_secondary:
            refinement_source = "promoted_model"
        else:
            refinement_source = "rule"

        out["discipline_primary"] = primary_final
        out["discipline_secondary"] = secondary_final
        # Keep legacy field in sync for downstream consumers still reading it.
        out["discipline"] = primary_final
        out["discipline_refinement_source"] = refinement_source
        cleaned_rows.append(out)

    confidence_queue = build_discipline_confidence_queue(
        cleaned_rows, discipline_classifier
    )
    write_discipline_confidence_queue(confidence_queue)
    print(f"  ↳ Wrote discipline confidence queue: {len(confidence_queue)} items")

    return cleaned_rows


def load_and_merge_data() -> List[Dict[str, Any]]:
    """Load data from multiple sources and merge, deduplicating by URL."""
    all_positions = []

    print("Loading data from multiple sources...")

    # Source 1: Historical positions (support both legacy and raw locations).
    historical_paths = [
        Path("data/raw/historical_positions.json"),
        Path("data/historical_positions.json"),
    ]
    historical_loaded = 0
    for hist_path in historical_paths:
        if not hist_path.exists():
            continue
        try:
            with open(hist_path, "r", encoding="utf-8") as f:
                hist = json.load(f)
            grad_hist = [p for p in hist if p.get("is_graduate_position")]
            all_positions.extend(grad_hist)
            historical_loaded += len(grad_hist)
            print(f"  ✓ Historical data ({hist_path.name}): {len(grad_hist)} graduate positions")
        except Exception as e:
            print(f"  ✗ Historical data error ({hist_path.name}): {e}")
    if historical_loaded == 0:
        print("  - Historical data: none found")

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

    # Deduplicate with a stable row key.
    unique_positions: Dict[str, Dict[str, Any]] = {}
    for p in all_positions:
        key = _build_row_key(p)
        if not key:
            continue
        existing = unique_positions.get(key)
        if existing is None or _row_quality_score(p) >= _row_quality_score(existing):
            unique_positions[key] = p

    deduped_positions = list(unique_positions.values())
    sanitized_positions = sanitize_and_classify_positions(deduped_positions)
    dropped_guardrail = len(deduped_positions) - len(sanitized_positions)
    print(
        f"\n📊 Merged dataset: {len(sanitized_positions)} unique graduate positions "
        f"({len(deduped_positions)} deduped; dropped {dropped_guardrail} non-grad by guardrails)\n"
    )

    return sanitized_positions


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

        # Normalize to one of 8 canonical categories
        normalized_disc = normalize_discipline(original_disc)
        discipline_data[normalized_disc]["count"] += 1

        salary = extract_salary_number(p.get("salary"))
        if salary:
            discipline_data[normalized_disc]["salaries"].append(salary)

    # Build top disciplines in canonical display order.
    top_disciplines = {}
    for discipline in DISCIPLINE_DISPLAY_ORDER:
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
        # Prefer publication/first-seen timestamps so long-term trends reflect
        # posting chronology, not the most recent scrape timestamp.
        date_fields = ["published_date", "first_seen", "scraped_at", "last_updated"]
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
                for disc in sort_disciplines(list(monthly_by_discipline.keys()))
            },
        }

    snapshot_availability = calculate_snapshot_availability()

    return {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_positions": total_positions,
            "source": "merged (historical + latest + enhanced)",
            "discipline_mapping": "consolidated to 8 categories",
        },
        "summary_stats": {
            "total_positions": total_positions,
            "graduate_positions": total_positions,
            "positions_with_salary": positions_with_salary,
        },
        "top_disciplines": top_disciplines,
        "geographic_summary": dict(location_counts.most_common(25)),
        "time_series": time_series,
        "snapshot_availability": snapshot_availability,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _extract_rows(obj: Any) -> List[Dict[str, Any]]:
    """Extract row lists from either list JSON or dict-wrapped payloads."""
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        if isinstance(obj.get("positions"), list):
            return obj["positions"]
        if isinstance(obj.get("jobs"), list):
            return obj["jobs"]
    return []


def _parse_run_datetime(path: Path) -> Optional[datetime]:
    """Parse run timestamp from filenames like *_YYYYMMDD_HHMMSS.json."""
    match = re.search(r"_(\d{8})_(\d{6})", path.stem)
    if not match:
        return None
    try:
        return datetime.strptime(f"{match.group(1)}_{match.group(2)}", "%Y%m%d_%H%M%S")
    except ValueError:
        return None


def _parse_flexible_datetime(value: Any) -> Optional[datetime]:
    """Parse common datetime/date formats found in scraper artifacts."""
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    # ISO forms, including timezone-suffixed strings.
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        pass

    # mm/dd/yyyy
    try:
        return datetime.strptime(text, "%m/%d/%Y")
    except ValueError:
        pass

    # yyyy-mm-dd
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d")
    except ValueError:
        return None


def _is_run_aligned(rows: List[Dict[str, Any]], run_dt: datetime, max_day_delta: int = 14) -> bool:
    """
    Validate that snapshot content aligns with run timestamp.

    Some archived files are re-saves of older static datasets. For scrape-snapshot
    trends, keep only files where row-level scraped_at dates are near run date.
    """
    parsed_dates: List[datetime] = []
    for row in rows:
        raw = row.get("scraped_at")
        if not raw:
            continue
        dt = _parse_flexible_datetime(raw)
        if dt:
            parsed_dates.append(dt)

    if not parsed_dates:
        return False

    # Use the median row timestamp as representative run timestamp.
    parsed_dates.sort()
    anchor = parsed_dates[len(parsed_dates) // 2]
    delta_days = abs((anchor.date() - run_dt.date()).days)
    return delta_days <= max_day_delta


def _count_graduate_rows(rows: List[Dict[str, Any]]) -> int:
    """Count rows marked as graduate in each snapshot."""
    return sum(1 for row in rows if row.get("is_graduate_position"))


def _graduate_discipline_breakdown(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    """Build normalized discipline counts for graduate rows in a snapshot."""
    counts: Counter[str] = Counter()
    for row in rows:
        if not row.get("is_graduate_position"):
            continue
        original_disc = (
            row.get("discipline")
            or row.get("discipline_primary")
            or row.get("discipline_secondary")
            or "Unknown"
        )
        counts[normalize_discipline(original_disc)] += 1
    ordered_keys = sort_disciplines(list(counts.keys()))
    return {name: counts[name] for name in ordered_keys}


def calculate_snapshot_availability() -> Dict[str, Any]:
    """
    Build monthly active-position availability from scrape snapshots.

    Priority:
    1. data/archive/scraped_backup_*.json (raw run snapshots)
    2. data/archive/enhanced_*.json (legacy run snapshots)
    """
    source_candidates = [
        ("scraped_backup", sorted(Path("data/archive").glob("scraped_backup_*.json"))),
        ("enhanced_archive", sorted(Path("data/archive").glob("enhanced_*.json"))),
    ]

    selected_source = "none"
    snapshot_points: List[Dict[str, Any]] = []
    best_month_count = 0
    best_run_count = 0

    for source_name, files in source_candidates:
        points: List[Dict[str, Any]] = []
        for path in files:
            run_dt = _parse_run_datetime(path)
            if not run_dt:
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    obj = json.load(f)
                rows = _extract_rows(obj)
                if not _is_run_aligned(rows, run_dt):
                    continue
                grad_count = _count_graduate_rows(rows)
                points.append(
                    {
                        "run_dt": run_dt,
                        "grad_count": grad_count,
                        "discipline_breakdown": _graduate_discipline_breakdown(rows),
                    }
                )
            except Exception:
                continue
        if not points:
            continue

        month_count = len({p["run_dt"].strftime("%Y-%m") for p in points})
        run_count = len(points)
        if (month_count, run_count) > (best_month_count, best_run_count):
            selected_source = source_name
            snapshot_points = points
            best_month_count = month_count
            best_run_count = run_count

    if not snapshot_points:
        return {
            "source": "none",
            "run_count": 0,
            "daily_avg_active_grad_positions": {},
            "daily_run_count": {},
            "monthly_avg_active_grad_positions": {},
            "monthly_relative_to_peak_pct": {},
            "monthly_run_count": {},
        }

    daily_values: Dict[str, List[int]] = defaultdict(list)
    monthly_values: Dict[str, List[int]] = defaultdict(list)
    for point in snapshot_points:
        run_dt = point["run_dt"]
        grad_count = point["grad_count"]
        daily_values[run_dt.strftime("%Y-%m-%d")].append(grad_count)
        monthly_values[run_dt.strftime("%Y-%m")].append(grad_count)

    daily_avg = {
        day: round(statistics.mean(values), 2)
        for day, values in sorted(daily_values.items())
    }
    daily_runs = {day: len(values) for day, values in sorted(daily_values.items())}

    monthly_avg = {
        month: round(statistics.mean(values), 2)
        for month, values in sorted(monthly_values.items())
    }
    monthly_runs = {month: len(values) for month, values in sorted(monthly_values.items())}

    peak = max(monthly_avg.values()) if monthly_avg else 0
    monthly_relative = {
        month: round((value / peak) * 100, 1) if peak > 0 else 0
        for month, value in monthly_avg.items()
    }

    latest_point = max(snapshot_points, key=lambda p: p["run_dt"])

    return {
        "source": selected_source,
        "run_count": len(snapshot_points),
        "daily_avg_active_grad_positions": daily_avg,
        "daily_run_count": daily_runs,
        "monthly_avg_active_grad_positions": monthly_avg,
        "monthly_relative_to_peak_pct": monthly_relative,
        "monthly_run_count": monthly_runs,
        "latest_run_timestamp": latest_point["run_dt"].isoformat(),
        "latest_run_grad_positions": latest_point["grad_count"],
        "latest_run_discipline_breakdown": latest_point["discipline_breakdown"],
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
