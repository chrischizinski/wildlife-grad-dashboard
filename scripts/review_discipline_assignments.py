#!/usr/bin/env python3
"""
Generate a review queue for suspicious discipline assignments.

Usage:
    python scripts/review_discipline_assignments.py
    python scripts/review_discipline_assignments.py --limit 30
    python scripts/review_discipline_assignments.py --input data/processed/verified_graduate_assistantships.json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

DISCIPLINES = [
    "Fisheries",
    "Wildlife",
    "Human Dimensions",
    "Environmental Science",
    "Forestry",
]

DISCIPLINE_SIGNALS: Dict[str, List[str]] = {
    "Fisheries": [
        r"\bfisher(y|ies)\b",
        r"\baquatic\b",
        r"\bmarine\b",
        r"\bhatchery\b",
        r"\bfish\s+passage\b",
    ],
    "Wildlife": [
        r"\bwildlife\b",
        r"\bavian\b",
        r"\bmammal\b",
        r"\bherpetolog(y|ical)\b",
        r"\bconservation biology\b",
    ],
    "Human Dimensions": [
        r"\bhuman\s+dimensions\b",
        r"\bstakeholder\b",
        r"\bsocial\s+science\b",
        r"\b(questionnaire|survey|interview|focus\s+group)\b",
        r"\bhuman[-\s]?wildlife\s+conflict\b",
    ],
    "Environmental Science": [
        r"\benvironmental\s+science\b",
        r"\becolog(y|ical)\b",
        r"\becosystem\b",
        r"\bclimate\s+change\b",
        r"\bremote\s+sensing\b",
        r"\bgis\b",
    ],
    "Forestry": [
        r"\bforestry\b",
        r"\bforest\b",
        r"\bsilviculture\b",
        r"\btimber\b",
        r"\bdendrolog(y|ical)\b",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a review queue for suspicious discipline assignments."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/processed/verified_graduate_assistantships.json"),
        help="Input verified positions JSON file",
    )
    parser.add_argument(
        "--out-csv",
        type=Path,
        default=Path("data/processed/discipline_review_queue.csv"),
        help="Output CSV file for review queue",
    )
    parser.add_argument(
        "--out-summary",
        type=Path,
        default=Path("data/processed/discipline_review_summary.json"),
        help="Output JSON summary",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Number of top flagged items to print",
    )
    return parser.parse_args()


def combined_text(position: Dict[str, Any]) -> str:
    parts = [
        str(position.get("title", "")),
        str(position.get("tags", "")),
        str(position.get("organization", "")),
        str(position.get("description", "")),
    ]
    return " ".join(parts).lower()


def score_disciplines(text: str) -> Dict[str, int]:
    scores: Dict[str, int] = {}
    for discipline, patterns in DISCIPLINE_SIGNALS.items():
        score = sum(1 for pattern in patterns if re.search(pattern, text, re.IGNORECASE))
        if score > 0:
            scores[discipline] = score
    return scores


def normalize_discipline(position: Dict[str, Any]) -> str:
    primary = str(position.get("discipline_primary", "")).strip()
    legacy = str(position.get("discipline", "")).strip()
    value = primary or legacy or "Other"
    if value in {"", "Unknown", "Non-Graduate"}:
        return "Other"
    return value


def evaluate_position(position: Dict[str, Any]) -> Tuple[List[str], Dict[str, int]]:
    text = combined_text(position)
    current = normalize_discipline(position)
    scores = score_disciplines(text)
    reasons: List[str] = []

    if current == "Other":
        reasons.append("unresolved_discipline")

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_name = ranked[0][0] if ranked else ""
    top_score = ranked[0][1] if ranked else 0
    second_score = ranked[1][1] if len(ranked) > 1 else 0

    if top_score >= 2 and current != top_name:
        reasons.append(f"signal_mismatch:{top_name}")

    if top_score == 0 and current in DISCIPLINES:
        reasons.append("no_matching_signals")

    if top_score >= 2 and second_score >= 2 and (top_score - second_score) <= 1:
        reasons.append("ambiguous_multidiscipline")

    grad_conf = float(position.get("grad_confidence", 0) or 0)
    if grad_conf < 0.65:
        reasons.append("low_grad_confidence")

    return reasons, scores


def build_review_queue(positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    queue: List[Dict[str, Any]] = []

    for pos in positions:
        reasons, scores = evaluate_position(pos)
        if not reasons:
            continue

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_signal = ranked[0][0] if ranked else ""
        top_score = ranked[0][1] if ranked else 0
        severity = len(reasons) + (1 if "signal_mismatch" in ",".join(reasons) else 0)

        queue.append(
            {
                "severity": severity,
                "reasons": ";".join(reasons),
                "title": pos.get("title", ""),
                "organization": pos.get("organization", ""),
                "discipline_current": normalize_discipline(pos),
                "signal_top": top_signal,
                "signal_top_score": top_score,
                "grad_confidence": pos.get("grad_confidence", 0),
                "url": pos.get("url", ""),
                "published_date": pos.get("published_date", ""),
            }
        )

    queue.sort(key=lambda x: (x["severity"], x["signal_top_score"]), reverse=True)
    return queue


def write_csv(rows: List[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "severity",
        "reasons",
        "title",
        "organization",
        "discipline_current",
        "signal_top",
        "signal_top_score",
        "grad_confidence",
        "published_date",
        "url",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(
    positions: List[Dict[str, Any]], queue: List[Dict[str, Any]], out_path: Path
) -> Dict[str, Any]:
    reason_counter: Counter[str] = Counter()
    current_disc_counter: Counter[str] = Counter()
    signal_disc_counter: Counter[str] = Counter()

    for row in queue:
        for reason in str(row["reasons"]).split(";"):
            if reason:
                reason_counter[reason] += 1
        current_disc_counter[str(row["discipline_current"])] += 1
        signal = str(row["signal_top"])
        if signal:
            signal_disc_counter[signal] += 1

    summary = {
        "generated_at": datetime.now().isoformat(),
        "input_positions": len(positions),
        "flagged_positions": len(queue),
        "flagged_rate_pct": round((len(queue) / len(positions)) * 100, 1)
        if positions
        else 0.0,
        "reason_counts": dict(reason_counter.most_common()),
        "current_discipline_counts_flagged": dict(current_disc_counter.most_common()),
        "top_signal_counts_flagged": dict(signal_disc_counter.most_common()),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    args = parse_args()
    if not args.input.exists():
        raise SystemExit(f"Input file not found: {args.input}")

    with args.input.open("r", encoding="utf-8") as f:
        positions = json.load(f)

    if not isinstance(positions, list):
        raise SystemExit("Input JSON must be a list of position objects.")

    queue = build_review_queue(positions)
    write_csv(queue, args.out_csv)
    summary = write_summary(positions, queue, args.out_summary)

    print(f"Loaded positions: {len(positions)}")
    print(f"Flagged for review: {len(queue)} ({summary['flagged_rate_pct']}%)")
    print(f"Wrote review queue CSV: {args.out_csv}")
    print(f"Wrote summary JSON: {args.out_summary}")

    if queue:
        print("\nTop flagged rows:")
        for idx, row in enumerate(queue[: args.limit], start=1):
            print(
                f"{idx:>2}. [{row['severity']}] {row['discipline_current']} -> "
                f"{row['signal_top'] or 'n/a'} | {row['title']} | {row['reasons']}"
            )


if __name__ == "__main__":
    main()
