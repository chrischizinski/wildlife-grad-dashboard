#!/usr/bin/env python3
"""
Import reviewed confidence-queue decisions into the gold discipline label store.

Expected queue CSV columns:
- position_key
- title
- organization
- url
- discipline_final
- discipline_model_suggested

Reviewer-added columns:
- review_status: accept_model | keep_final | override | skip
- reviewed_discipline: required only for override
- review_notes: optional
- reviewer: optional
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DISCIPLINE_MAPPING = {
    "Environmental Science": "Environmental Sciences",
    "Environmental Sciences": "Environmental Sciences",
    "Ecology": "Environmental Sciences",
    "Fisheries": "Fisheries and Aquatic",
    "Fisheries and Aquatic": "Fisheries and Aquatic",
    "Fisheries & Aquatic Science": "Fisheries and Aquatic",
    "Fisheries Management and Conservation": "Fisheries and Aquatic",
    "Marine Science": "Fisheries and Aquatic",
    "Wildlife": "Wildlife",
    "Wildlife Management and Conservation": "Wildlife",
    "Wildlife Management": "Wildlife",
    "Wildlife & Natural Resources": "Wildlife",
    "Conservation": "Wildlife",
    "Entomology": "Entomology",
    "Forestry": "Forestry and Habitat",
    "Forestry and Habitat": "Forestry and Habitat",
    "Natural Resource Management": "Forestry and Habitat",
    "Agriculture": "Agriculture",
    "Agricultural Science": "Agriculture",
    "Animal Science": "Agriculture",
    "Agronomy": "Agriculture",
    "Range Management": "Agriculture",
    "Human Dimensions": "Human Dimensions",
    "Other": "Other",
    "Unknown": "Other",
    "Non-Graduate": "Other",
}

VALID_REVIEW_STATUSES = {
    "accept_model": "accept_model",
    "model": "accept_model",
    "accept": "accept_model",
    "keep_final": "keep_final",
    "keep": "keep_final",
    "final": "keep_final",
    "override": "override",
    "set_label": "override",
    "set": "override",
    "skip": "skip",
    "": "skip",
}


def now_iso() -> str:
    return datetime.now().isoformat()


def normalize_discipline(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "Other"
    return DISCIPLINE_MAPPING.get(text, "Other")


def build_row_key(row: Dict[str, Any]) -> str:
    key = str(row.get("position_key") or "").strip().lower()
    if key:
        return key
    url = str(row.get("url") or "").strip().lower()
    if url:
        return f"url::{url}"
    title = str(row.get("title") or "").strip().lower()
    org = str(row.get("organization") or "").strip().lower()
    loc = str(row.get("location") or "").strip().lower()
    pub = str(row.get("published_date") or "").strip().lower()
    if title and org:
        return f"title_org::{title}::{org}::{loc}::{pub}"
    return f"title::{title}::{pub}" if title else ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import reviewed discipline queue decisions into gold labels."
    )
    parser.add_argument(
        "--reviews-csv",
        type=Path,
        default=Path("data/processed/discipline_confidence_queue.csv"),
    )
    parser.add_argument(
        "--gold-file",
        type=Path,
        default=Path("data/processed/discipline_labels_gold.json"),
    )
    parser.add_argument(
        "--positions-file",
        type=Path,
        default=Path("web/data/dashboard_positions.json"),
    )
    parser.add_argument(
        "--default-reviewer",
        type=str,
        default="discipline_queue_review",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
    )
    return parser.parse_args()


def ensure_gold_dataset(path: Path) -> Dict[str, Any]:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict) and isinstance(payload.get("labels"), list):
            return payload
    payload = {"version": 1, "updated_at": now_iso(), "labels": []}
    return payload


def load_rows(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Review CSV not found: {path}")
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def load_positions_map(path: Path) -> Dict[str, Dict[str, Any]]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = payload.get("positions") or payload.get("jobs") or []
    else:
        rows = []

    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = build_row_key(row)
        if not key:
            continue
        out[key] = row
    return out


def resolve_review_action(raw_status: Any) -> str:
    status = str(raw_status or "").strip().lower()
    return VALID_REVIEW_STATUSES.get(status, "invalid")


def choose_final_label(row: Dict[str, Any], action: str) -> Tuple[Optional[str], Optional[str]]:
    if action == "skip":
        return None, None
    if action == "accept_model":
        label = normalize_discipline(row.get("discipline_model_suggested"))
        if label == "Other":
            return None, "accept_model selected but model suggestion is Other"
        return label, None
    if action == "keep_final":
        label = normalize_discipline(row.get("discipline_final"))
        return label, None
    if action == "override":
        label = normalize_discipline(row.get("reviewed_discipline"))
        if not str(row.get("reviewed_discipline") or "").strip():
            return None, "override selected without reviewed_discipline"
        return label, None
    return None, f"invalid review_status: {row.get('review_status')}"


def main() -> int:
    args = parse_args()

    gold = ensure_gold_dataset(args.gold_file)
    rows = load_rows(args.reviews_csv)
    positions_map = load_positions_map(args.positions_file)

    labels = gold.get("labels") if isinstance(gold.get("labels"), list) else []
    by_key: Dict[str, Dict[str, Any]] = {}
    for item in labels:
        if not isinstance(item, dict):
            continue
        key = str(item.get("position_key") or "").strip().lower()
        if key:
            by_key[key] = item

    processed = 0
    created = 0
    updated = 0
    skipped = 0
    errors: List[str] = []
    for idx, row in enumerate(rows, start=2):
        action = resolve_review_action(row.get("review_status"))
        if action == "invalid":
            skipped += 1
            errors.append(f"row {idx}: invalid review_status '{row.get('review_status')}'")
            continue

        key = build_row_key(row)
        if not key:
            skipped += 1
            errors.append(f"row {idx}: missing position_key and insufficient fallback fields")
            continue

        chosen, err = choose_final_label(row, action)
        if err:
            skipped += 1
            errors.append(f"row {idx}: {err}")
            continue
        if chosen is None:
            skipped += 1
            continue

        processed += 1
        now = now_iso()
        reviewer = str(row.get("reviewer") or "").strip() or args.default_reviewer
        notes = str(row.get("review_notes") or "").strip()
        source_row = positions_map.get(key, {})

        existing = by_key.get(key)
        if existing is None:
            entry = {
                "position_key": key,
                "title": str(row.get("title") or source_row.get("title") or ""),
                "organization": str(
                    row.get("organization") or source_row.get("organization") or ""
                ),
                "url": str(row.get("url") or source_row.get("url") or ""),
                "description": str(source_row.get("description") or ""),
                "tags": str(source_row.get("tags") or ""),
                "discipline": chosen,
                "source": "discipline_queue_review",
                "reviewed_at": now,
                "reviewer": reviewer,
                "review_notes": notes,
            }
            labels.append(entry)
            by_key[key] = entry
            created += 1
        else:
            existing["discipline"] = chosen
            existing["source"] = "discipline_queue_review"
            existing["reviewed_at"] = now
            existing["reviewer"] = reviewer
            if notes:
                existing["review_notes"] = notes
            if not existing.get("description") and source_row.get("description"):
                existing["description"] = str(source_row.get("description"))
            if not existing.get("tags") and source_row.get("tags"):
                existing["tags"] = str(source_row.get("tags"))
            updated += 1

    gold["labels"] = labels
    gold["updated_at"] = now_iso()

    if not args.dry_run:
        args.gold_file.parent.mkdir(parents=True, exist_ok=True)
        with open(args.gold_file, "w", encoding="utf-8") as f:
            json.dump(gold, f, indent=2)

    print(f"Processed reviews: {processed}")
    print(f"Created labels: {created}")
    print(f"Updated labels: {updated}")
    print(f"Skipped rows: {skipped}")
    if errors:
        print("Review import warnings:")
        for line in errors[:25]:
            print(f"  - {line}")
        if len(errors) > 25:
            print(f"  - ... {len(errors) - 25} more")
    print(f"Gold file: {args.gold_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
