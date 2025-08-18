#!/usr/bin/env python3
"""
Export positions for batch verification in Excel/CSV format
"""

import json
from pathlib import Path

import pandas as pd


def create_verification_export():
    """Create Excel file for batch verification"""

    # Load positions
    data_file = Path("data/processed/verified_graduate_assistantships.json")
    with open(data_file, "r") as f:
        positions = json.load(f)

    print(f"📊 Loaded {len(positions)} positions")

    # Filter to positions needing verification
    # Priority: Unknown disciplines, low confidence, unverified
    priority_positions = []

    for pos in positions:
        # High priority: Unknown discipline
        if pos.get("discipline") == "Unknown":
            priority_positions.append(
                {"priority": 1, "reason": "Unknown Discipline", **pos}
            )
        # Medium priority: Low confidence
        elif pos.get("grad_confidence", 1.0) < 0.8:
            priority_positions.append(
                {"priority": 2, "reason": "Low Confidence", **pos}
            )
        # Add some high-confidence samples for validation
        elif pos.get("grad_confidence", 1.0) >= 0.9 and len(priority_positions) < 50:
            priority_positions.append(
                {"priority": 3, "reason": "Validation Sample", **pos}
            )

    # Sort by priority
    priority_positions.sort(key=lambda x: x["priority"])

    # Take top 50 for manageable verification batch
    verification_batch = priority_positions[:50]

    print(f"🎯 Selected {len(verification_batch)} positions for verification")

    # Create verification DataFrame
    verification_data = []

    for i, pos in enumerate(verification_batch, 1):
        verification_data.append(
            {
                "Review_ID": i,
                "Position_ID": pos.get("position_id", pos.get("id")),
                "Priority": pos["priority"],
                "Reason": pos["reason"],
                "Title": pos.get("title", ""),
                "Organization": pos.get("organization", ""),
                "Location": pos.get("location", ""),
                "Salary": pos.get("salary", ""),
                "Starting_Date": pos.get("starting_date", ""),
                "Description": pos.get("description", "")[:500] + "..."
                if len(pos.get("description", "")) > 500
                else pos.get("description", ""),
                # Current ML Classifications
                "ML_Graduate_Position": pos.get("is_graduate_position", ""),
                "ML_Grad_Confidence": round(pos.get("grad_confidence", 0), 2),
                "ML_Position_Type": pos.get("position_type", ""),
                "ML_Discipline": pos.get("discipline", ""),
                "ML_Discipline_Confidence": round(
                    pos.get("discipline_confidence", 0), 2
                ),
                "ML_University": pos.get("university_name", ""),
                "ML_Big10": pos.get("is_big10_university", ""),
                # Verification Fields (to be filled)
                "Human_Graduate_Position": "",  # TRUE/FALSE
                "Human_Position_Type": "",  # Graduate/Professional/Technician/Exclude
                "Human_Discipline": "",  # Wildlife & Natural Resources/etc
                "Human_University": "",  # Correct university name
                "Human_Big10": "",  # TRUE/FALSE
                "Notes": "",  # Any notes
                "Confidence": "",  # How confident are you in this classification?
            }
        )

    # Create DataFrame and export
    df = pd.DataFrame(verification_data)

    # Export to CSV (simpler, no dependencies)
    output_file = f"position_verification_batch_{len(verification_batch)}.csv"
    df.to_csv(output_file, index=False)

    print(f"✅ Created verification file: {output_file}")
    print("📋 Priority breakdown:")

    priority_counts = {}
    for pos in verification_batch:
        reason = pos["reason"]
        priority_counts[reason] = priority_counts.get(reason, 0) + 1

    for reason, count in priority_counts.items():
        print(f"   {reason}: {count} positions")

    print("\n📝 Instructions:")
    print(f"1. Open {output_file} in Excel")
    print("2. Fill in the 'Human_*' columns with correct classifications")
    print("3. Add notes explaining your reasoning")
    print("4. Save the file")
    print("5. Run import script to apply corrections")

    return output_file


if __name__ == "__main__":
    create_verification_export()
