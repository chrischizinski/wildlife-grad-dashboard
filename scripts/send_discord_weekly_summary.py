#!/usr/bin/env python3
"""
Send a weekly scrape summary to Discord via webhook.

Expected environment:
- DISCORD_WEBHOOK_URL: Discord webhook URL
- GITHUB_REPOSITORY: optional, used for links
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib import error, request


PROJECT_ROOT = Path(__file__).resolve().parent.parent
POSITIONS_PATH = PROJECT_ROOT / "web" / "data" / "dashboard_positions.json"
ANALYTICS_PATH = PROJECT_ROOT / "web" / "data" / "dashboard_analytics.json"
MAX_LISTED_POSTINGS = 15
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/146.0.0.0 Safari/537.36"
)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def extract_rows(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("positions", "jobs"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return rows
    return []


def latest_capture_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    with_run_ids = [row for row in rows if str(row.get("scrape_run_id") or "").strip()]
    if with_run_ids:
        latest_row = max(
            with_run_ids,
            key=lambda row: parse_iso_datetime(row.get("scraped_at")) or datetime.min,
        )
        latest_run_id = str(latest_row.get("scrape_run_id") or "").strip()
        return [row for row in with_run_ids if str(row.get("scrape_run_id") or "").strip() == latest_run_id]

    dated_rows = [row for row in rows if parse_iso_datetime(row.get("scraped_at"))]
    if not dated_rows:
        return rows

    latest_dt = max(parse_iso_datetime(row.get("scraped_at")) for row in dated_rows)
    latest_day = latest_dt.date()
    return [
        row
        for row in dated_rows
        if (parse_iso_datetime(row.get("scraped_at")) or latest_dt).date() == latest_day
    ]


def sort_capture_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            parse_iso_datetime(row.get("published_date")) or datetime.min,
            parse_iso_datetime(row.get("scraped_at")) or datetime.min,
            str(row.get("title") or ""),
        ),
        reverse=True,
    )


def format_capture_line(row: Dict[str, Any]) -> str:
    title = str(row.get("title") or "Untitled position").strip()
    organization = str(row.get("organization") or "Unknown organization").strip()
    location = str(row.get("location") or "Unknown location").strip()
    return f"- {title} | {organization} | {location}"


def build_message(rows: List[Dict[str, Any]], analytics: Dict[str, Any]) -> str:
    summary = analytics.get("summary_stats", {})
    metadata = analytics.get("metadata", {})
    capture_rows = sort_capture_rows(latest_capture_rows(rows))

    total_positions = int(summary.get("total_positions") or len(rows))
    salary_positions = int(summary.get("positions_with_salary") or 0)
    generated_at = str(metadata.get("generated_at") or "").strip() or "unknown"
    latest_scraped_at = max(
        (str(row.get("scraped_at") or "") for row in rows if row.get("scraped_at")),
        default="unknown",
    )

    repository = os.getenv("GITHUB_REPOSITORY", "").strip()
    dashboard_url = (
        f"https://{repository.split('/')[0].lower()}.github.io/{repository.split('/')[1]}/"
        if repository and "/" in repository
        else ""
    )
    repo_commits_url = f"https://github.com/{repository}/commits/main" if repository else ""

    lines = [
        "Wildlife Grad weekly scrape summary",
        f"- Graduate positions in dashboard dataset: {total_positions}",
        f"- Positions with salary parsed: {salary_positions}",
        f"- Latest scrape timestamp: {latest_scraped_at}",
        f"- Analytics regenerated: {generated_at}",
        f"- Postings in latest capture batch: {len(capture_rows)}",
    ]

    if dashboard_url:
        lines.append(f"- Live dashboard: {dashboard_url}")
    if repo_commits_url:
        lines.append(f"- Repo updates: {repo_commits_url}")

    lines.append("")
    lines.append("Latest capture postings:")

    if not capture_rows:
        lines.append("- No postings found in the latest capture batch.")
        return "\n".join(lines)

    displayed = capture_rows[:MAX_LISTED_POSTINGS]
    lines.extend(format_capture_line(row) for row in displayed)
    remaining = len(capture_rows) - len(displayed)
    if remaining > 0:
        lines.append(f"- ... and {remaining} more postings in this capture batch")

    return "\n".join(lines)


def send_discord_message(webhook_url: str, content: str) -> None:
    payload = json.dumps({"content": content}).encode("utf-8")
    req = request.Request(
        webhook_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": DEFAULT_USER_AGENT,
        },
        method="POST",
    )
    try:
        with request.urlopen(req) as response:
            if response.status not in (200, 204):
                raise RuntimeError(f"Discord webhook failed with HTTP {response.status}")
    except error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace").strip()
        details = f"HTTP {exc.code}"
        if response_body:
            details = f"{details}: {response_body}"
        if exc.code in (401, 403):
            raise RuntimeError(
                "Discord rejected the webhook. Check that the "
                "DISCORD_WEBHOOK_URL secret points to an active webhook for the "
                f"target channel. Details: {details}"
            ) from exc
        raise RuntimeError(f"Discord webhook request failed. Details: {details}") from exc


def main() -> int:
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook_url:
        print("Discord webhook not configured; skipping summary.")
        return 0

    rows = extract_rows(load_json(POSITIONS_PATH))
    analytics = load_json(ANALYTICS_PATH)
    message = build_message(rows, analytics)

    try:
        send_discord_message(webhook_url, message[:1900])
    except RuntimeError as exc:
        print(f"Discord weekly summary failed: {exc}")
        return 0

    print("Discord weekly summary sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
