#!/usr/bin/env python3
"""
Interactive CLI tool for verifying and correcting ML position classifications.

Usage:
    python scripts/verify_classifications.py --recent 20
    python scripts/verify_classifications.py --confidence-threshold 0.7
    python scripts/verify_classifications.py --discipline "Unknown"
    python scripts/verify_classifications.py --all
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Union


class ClassificationVerifier:
    """Interactive CLI tool for verifying position classifications."""

    def __init__(self):
        self.data_file = Path("data/processed/verified_graduate_assistantships.json")
        self.corrections_file = Path("data/verification_corrections.json")
        self.positions: List[Dict] = []
        self.corrections: List[Dict] = []

        # Available disciplines for correction
        self.disciplines = [
            "Wildlife & Natural Resources",
            "Natural Resource Management",
            "Environmental Science",
            "Fisheries & Aquatic Sciences",
            "Conservation Biology",
            "Unknown",
            "Other",
        ]

        # Position types
        self.position_types = [
            "Graduate",
            "Professional",
            "Technician",
            "Exclude",  # For positions that shouldn't be in the dataset
        ]

    def load_data(self) -> None:
        """Load position data for verification."""
        if not self.data_file.exists():
            print(f"❌ Data file not found: {self.data_file}")
            sys.exit(1)

        with open(self.data_file, "r") as f:
            self.positions = json.load(f)

        print(f"📊 Loaded {len(self.positions)} positions for verification")

    def load_existing_corrections(self) -> None:
        """Load any existing corrections."""
        if self.corrections_file.exists():
            with open(self.corrections_file, "r") as f:
                existing = json.load(f)
                self.corrections = existing.get("corrections", [])
            print(f"📝 Loaded {len(self.corrections)} existing corrections")

    def filter_positions(self, args) -> List[Dict]:
        """Filter positions based on CLI arguments."""
        filtered = self.positions.copy()

        # Filter by confidence threshold
        if args.confidence_threshold:
            filtered = [
                p
                for p in filtered
                if p.get("grad_confidence", 1.0) <= args.confidence_threshold
            ]
            print(
                f"🎯 Filtered to {len(filtered)} positions with confidence <= {args.confidence_threshold}"
            )

        # Filter by discipline
        if args.discipline:
            filtered = [p for p in filtered if p.get("discipline") == args.discipline]
            print(
                f"🔬 Filtered to {len(filtered)} positions with discipline '{args.discipline}'"
            )

        # Filter to recent positions
        if args.recent:
            # Sort by scraped_at date and take most recent
            filtered.sort(key=lambda x: x.get("scraped_at", ""), reverse=True)
            filtered = filtered[: args.recent]
            print(f"⏰ Showing {len(filtered)} most recent positions")

        # Filter by days
        if args.days:
            cutoff = datetime.now() - timedelta(days=args.days)
            cutoff_str = cutoff.isoformat()
            filtered = [p for p in filtered if p.get("scraped_at", "") >= cutoff_str]
            print(
                f"📅 Filtered to {len(filtered)} positions from last {args.days} days"
            )

        return filtered

    def display_position(self, position: Dict, index: int, total: int) -> None:
        """Display a position for verification."""
        print("\n" + "=" * 80)
        print(f"📋 Position {index + 1} of {total}")
        print("=" * 80)

        print(f"📰 Title: {position.get('title', 'N/A')}")
        print(f"🏢 Organization: {position.get('organization', 'N/A')}")
        print(f"📍 Location: {position.get('location', 'N/A')}")
        print(f"💰 Salary: {position.get('salary', 'N/A')}")
        print(f"📅 Starting: {position.get('starting_date', 'N/A')}")

        print("\n🤖 Current ML Classifications:")
        print(
            f"   Graduate Position: {position.get('is_graduate_position', 'N/A')} (confidence: {position.get('grad_confidence', 'N/A'):.2f})"
        )
        print(f"   Position Type: {position.get('position_type', 'N/A')}")
        print(
            f"   Discipline: {position.get('discipline', 'N/A')} (confidence: {position.get('discipline_confidence', 'N/A'):.2f})"
        )

        # Show description snippet
        description = position.get("description", "")
        if description:
            # Show first 300 characters
            desc_preview = (
                description[:300] + "..." if len(description) > 300 else description
            )
            print(f"\n📝 Description:\n{desc_preview}")

    def get_user_verification(self, position: Dict) -> Union[Dict[str, Any], str, None]:
        """Get user verification/correction for a position."""
        while True:
            print("\n" + "-" * 40)
            print("Verification Options:")
            print("  ✅ [ENTER] - Classification is correct")
            print("  🔧 [c] - Correct classification")
            print("  ❌ [x] - Exclude this position")
            print("  ⏭️  [s] - Skip (review later)")
            print("  🛑 [q] - Quit verification session")
            print("-" * 40)

            choice = input("Your choice: ").strip().lower()

            if choice == "" or choice == "y":
                # Classification is correct
                return {
                    "position_id": position.get("position_id"),
                    "action": "approved",
                    "verified_at": datetime.now().isoformat(),
                }

            elif choice == "c":
                return self.get_corrections(position)

            elif choice == "x":
                # Exclude position
                return {
                    "position_id": position.get("position_id"),
                    "action": "excluded",
                    "reason": input("Reason for exclusion (optional): ").strip(),
                    "verified_at": datetime.now().isoformat(),
                }

            elif choice == "s":
                # Skip
                return None

            elif choice == "q":
                # Quit
                return "quit"

            else:
                print("❌ Invalid choice. Please try again.")

    def get_corrections(self, position: Dict) -> Dict:
        """Get detailed corrections for a position."""
        correction = {
            "position_id": position.get("position_id"),
            "action": "corrected",
            "original": {
                "is_graduate_position": position.get("is_graduate_position"),
                "position_type": position.get("position_type"),
                "discipline": position.get("discipline"),
            },
            "corrections": {},
            "verified_at": datetime.now().isoformat(),
        }

        # Correct graduate position classification
        print(
            f"\n🎓 Is this a graduate position? Current: {position.get('is_graduate_position')}"
        )
        print("   [y] Yes - Graduate assistantship/fellowship/PhD/Masters")
        print("   [n] No - Professional/staff/technician position")
        print("   [ENTER] Keep current classification")

        grad_choice = input("Graduate position? ").strip().lower()
        if grad_choice == "y":
            correction["corrections"]["is_graduate_position"] = True
        elif grad_choice == "n":
            correction["corrections"]["is_graduate_position"] = False

        # Correct position type
        print(f"\n🏷️  Position type? Current: {position.get('position_type')}")
        for i, pt in enumerate(self.position_types, 1):
            print(f"   [{i}] {pt}")
        print("   [ENTER] Keep current classification")

        type_choice = input("Position type (number): ").strip()
        if type_choice.isdigit() and 1 <= int(type_choice) <= len(self.position_types):
            correction["corrections"]["position_type"] = self.position_types[
                int(type_choice) - 1
            ]

        # Correct discipline
        print(f"\n🔬 Discipline? Current: {position.get('discipline')}")
        for i, disc in enumerate(self.disciplines, 1):
            print(f"   [{i}] {disc}")
        print("   [ENTER] Keep current classification")

        disc_choice = input("Discipline (number): ").strip()
        if disc_choice.isdigit() and 1 <= int(disc_choice) <= len(self.disciplines):
            correction["corrections"]["discipline"] = self.disciplines[
                int(disc_choice) - 1
            ]

        # Optional notes
        notes = input("\n📝 Notes (optional): ").strip()
        if notes:
            correction["notes"] = notes

        return correction

    def save_corrections(self) -> None:
        """Save corrections to file."""
        correction_data = {
            "session_date": datetime.now().isoformat(),
            "total_corrections": len(self.corrections),
            "corrections": self.corrections,
        }

        with open(self.corrections_file, "w") as f:
            json.dump(correction_data, f, indent=2)

        print(
            f"💾 Saved {len(self.corrections)} corrections to {self.corrections_file}"
        )

    def run_verification_session(self, positions: List[Dict]) -> None:
        """Run interactive verification session."""
        if not positions:
            print("❌ No positions to verify")
            return

        print(f"\n🚀 Starting verification session with {len(positions)} positions")
        print("💡 Tip: Focus on low-confidence classifications and unknown disciplines")

        verified_count = 0
        corrected_count = 0
        excluded_count = 0

        for i, position in enumerate(positions):
            self.display_position(position, i, len(positions))

            result = self.get_user_verification(position)

            if result == "quit":
                print("\n🛑 Verification session ended by user")
                break
            elif result is None:
                continue  # Skip
            elif isinstance(result, dict):
                self.corrections.append(result)

                if result["action"] == "approved":
                    verified_count += 1
                elif result["action"] == "corrected":
                    corrected_count += 1
                elif result["action"] == "excluded":
                    excluded_count += 1

        # Session summary
        print("\n📊 Verification Session Summary:")
        print(f"   ✅ Approved: {verified_count}")
        print(f"   🔧 Corrected: {corrected_count}")
        print(f"   ❌ Excluded: {excluded_count}")
        print(f"   📝 Total processed: {len(self.corrections)}")

        if self.corrections:
            self.save_corrections()
            print(
                "\n💡 Run 'python scripts/apply_corrections.py' to apply corrections to the dataset"
            )

    def show_summary_stats(self, positions: List[Dict]) -> None:
        """Show summary statistics for positions to be verified."""
        if not positions:
            return

        print(f"\n📈 Summary Statistics for {len(positions)} positions:")

        # Confidence distribution
        confidences = [p.get("grad_confidence", 0) for p in positions]
        low_conf = sum(1 for c in confidences if c < 0.7)
        medium_conf = sum(1 for c in confidences if 0.7 <= c < 0.9)
        high_conf = sum(1 for c in confidences if c >= 0.9)

        print("🎯 Confidence Distribution:")
        print(f"   Low (< 0.7):    {low_conf:3d} positions")
        print(f"   Medium (0.7-0.9): {medium_conf:3d} positions")
        print(f"   High (≥ 0.9):    {high_conf:3d} positions")

        # Discipline distribution
        disciplines: Dict[str, int] = {}
        for p in positions:
            disc = p.get("discipline", "Unknown")
            disciplines[disc] = disciplines.get(disc, 0) + 1

        print("\n🔬 Discipline Distribution:")
        for disc, count in sorted(
            disciplines.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"   {disc:25s}: {count:3d} positions")


def main():
    parser = argparse.ArgumentParser(
        description="Interactive CLI tool for verifying position classifications"
    )

    # Filtering options
    parser.add_argument("--recent", type=int, help="Verify N most recent positions")
    parser.add_argument("--days", type=int, help="Verify positions from last N days")
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        help="Only verify positions with confidence <= threshold",
    )
    parser.add_argument(
        "--discipline", type=str, help="Only verify positions with specific discipline"
    )
    parser.add_argument("--all", action="store_true", help="Verify all positions")

    # Options
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Show statistics only, don't start verification",
    )

    args = parser.parse_args()

    # Default to recent 20 if no filter specified
    if not any(
        [args.recent, args.days, args.confidence_threshold, args.discipline, args.all]
    ):
        args.recent = 20
        print("💡 No filter specified, defaulting to --recent 20")

    verifier = ClassificationVerifier()
    verifier.load_data()
    verifier.load_existing_corrections()

    positions = verifier.filter_positions(args)
    verifier.show_summary_stats(positions)

    if args.stats_only:
        print("\n📊 Statistics only mode - verification session not started")
        return

    if not positions:
        print("\n❌ No positions match the specified criteria")
        return

    # Start verification session
    verifier.run_verification_session(positions)


if __name__ == "__main__":
    main()
