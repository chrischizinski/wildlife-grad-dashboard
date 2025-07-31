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

        # Big 10 universities for reference
        self.big10_universities = [
            "University of Illinois",
            "University of Indiana",
            "University of Iowa",
            "University of Maryland",
            "University of Michigan",
            "Michigan State University",
            "University of Minnesota",
            "University of Nebraska",
            "Northwestern University",
            "Ohio State University",
            "Pennsylvania State University",
            "Purdue University",
            "Rutgers University",
            "University of Wisconsin",
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
        """Filter positions based on CLI arguments with diverse sampling strategies."""
        filtered = self.positions.copy()

        # Exclude already human-verified positions by default
        if not args.include_verified:
            original_count = len(filtered)
            filtered = [p for p in filtered if not p.get("human_verified", False)]
            excluded_count = original_count - len(filtered)
            if excluded_count > 0:
                print(
                    f"✅ Excluded {excluded_count} already-verified positions (use --include-verified to include them)"
                )

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

        # Filter by days
        if args.days:
            cutoff = datetime.now() - timedelta(days=args.days)
            cutoff_str = cutoff.isoformat()
            filtered = [p for p in filtered if p.get("scraped_at", "") >= cutoff_str]
            print(
                f"📅 Filtered to {len(filtered)} positions from last {args.days} days"
            )

        # Apply sampling strategy
        if args.recent:
            # Sort by scraped_at date and take most recent
            filtered.sort(key=lambda x: x.get("scraped_at", ""), reverse=True)
            filtered = filtered[: args.recent]
            print(f"⏰ Showing {len(filtered)} most recent positions")
        elif args.diverse_sample:
            # Diverse sampling across the full dataset
            filtered = self._get_diverse_sample(filtered, args.diverse_sample)
            print(f"🌐 Selected {len(filtered)} diverse positions from full dataset")
        elif args.smart_sample:
            # Smart sampling prioritizing positions that need review
            filtered = self._get_smart_sample(filtered, args.smart_sample)
            print(
                f"🧠 Selected {len(filtered)} positions using smart sampling strategy"
            )

        return filtered

    def _get_diverse_sample(
        self, positions: List[Dict], sample_size: int
    ) -> List[Dict]:
        """Get a diverse sample across disciplines, confidence levels, and time periods."""
        import random

        if len(positions) <= sample_size:
            return positions

        # Separate positions by categories for balanced sampling
        by_discipline: Dict[str, List[Dict]] = {}
        by_confidence: Dict[str, List[Dict]] = {"low": [], "medium": [], "high": []}
        by_verification: Dict[str, List[Dict]] = {"unverified": [], "verified": []}

        for pos in positions:
            # Group by discipline
            disc = pos.get("discipline", "Unknown")
            if disc not in by_discipline:
                by_discipline[disc] = []
            by_discipline[disc].append(pos)

            # Group by confidence level
            confidence = pos.get("grad_confidence", 0.5)
            if confidence < 0.7:
                by_confidence["low"].append(pos)
            elif confidence < 0.9:
                by_confidence["medium"].append(pos)
            else:
                by_confidence["high"].append(pos)

            # Group by verification status
            if pos.get("human_verified", False):
                by_verification["verified"].append(pos)
            else:
                by_verification["unverified"].append(pos)

        diverse_sample = []

        # Sample from each discipline proportionally
        disciplines = list(by_discipline.keys())
        discipline_samples = max(1, sample_size // len(disciplines))

        for disc in disciplines:
            disc_positions = by_discipline[disc]
            sample_count = min(discipline_samples, len(disc_positions))
            diverse_sample.extend(random.sample(disc_positions, sample_count))

        # Fill remaining slots with random unverified positions
        remaining_slots = sample_size - len(diverse_sample)
        if remaining_slots > 0:
            unverified = [
                p
                for p in positions
                if not p.get("human_verified", False) and p not in diverse_sample
            ]
            if unverified and remaining_slots > 0:
                additional = min(remaining_slots, len(unverified))
                diverse_sample.extend(random.sample(unverified, additional))
            elif remaining_slots > 0:
                # If no unverified positions left, fill from any remaining positions
                remaining = [p for p in positions if p not in diverse_sample]
                if remaining:
                    additional = min(remaining_slots, len(remaining))
                    diverse_sample.extend(random.sample(remaining, additional))

        return diverse_sample[:sample_size]

    def _get_smart_sample(self, positions: List[Dict], sample_size: int) -> List[Dict]:
        """Get a smart sample prioritizing positions that most need human review."""
        # Score positions based on how much they need review
        scored_positions = []

        for pos in positions:
            score = 0.0

            # Higher score for unverified positions
            if not pos.get("human_verified", False):
                score += 10

            # Higher score for low confidence
            grad_conf = pos.get("grad_confidence", 1.0)
            disc_conf = pos.get("discipline_confidence", 1.0)
            score += (1.0 - grad_conf) * 5
            score += (1.0 - disc_conf) * 5

            # Higher score for "Unknown" disciplines
            if pos.get("discipline") == "Unknown":
                score += 8

            # Higher score for conflicting classifications
            if pos.get("grad_confidence", 1.0) < 0.8 and pos.get(
                "is_graduate_position", True
            ):
                score += 3

            # Add some randomness to avoid always showing the same positions
            import random

            score += random.uniform(0, 2)  # nosec B311

            scored_positions.append((score, pos))

        # Sort by score (highest first) and take top positions
        scored_positions.sort(key=lambda x: x[0], reverse=True)
        return [pos for score, pos in scored_positions[:sample_size]]

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

        # Show discipline keywords if available
        keywords = position.get("discipline_keywords", [])
        if keywords:
            print(
                f"   Keywords: {', '.join(keywords[:5])}{'...' if len(keywords) > 5 else ''}"
            )

        # Show university classification
        is_big10 = position.get("is_big10_university", False)
        university = position.get("university_name", "N/A")
        print(
            f"   University: {university} {'(Big 10)' if is_big10 else '(Non-Big 10)'}"
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
        """Get detailed corrections for ALL classifications with mandatory reasoning."""
        correction = {
            "position_id": position.get("position_id"),
            "action": "corrected",
            "original": {
                "is_graduate_position": position.get("is_graduate_position"),
                "position_type": position.get("position_type"),
                "discipline": position.get("discipline"),
                "is_big10_university": position.get("is_big10_university"),
                "university_name": position.get("university_name"),
            },
            "corrections": {},
            "reasoning": {},
            "verified_at": datetime.now().isoformat(),
        }

        has_corrections = False

        # 1. Correct graduate position classification
        print("\n🎓 Graduate Position Classification")
        print(
            f"    Current: {position.get('is_graduate_position')} (confidence: {position.get('grad_confidence', 'N/A'):.2f})"
        )
        print("    [y] Yes - Graduate assistantship/fellowship/PhD/Masters")
        print("    [n] No - Professional/staff/technician position")
        print("    [ENTER] Keep current classification")

        grad_choice = input("Graduate position? ").strip().lower()
        if grad_choice == "y" and not position.get("is_graduate_position"):
            correction["corrections"]["is_graduate_position"] = True
            reason = input("Why is this a graduate position? ").strip()
            if reason:
                correction["reasoning"]["is_graduate_position"] = reason
                has_corrections = True
        elif grad_choice == "n" and position.get("is_graduate_position"):
            correction["corrections"]["is_graduate_position"] = False
            reason = input("Why is this NOT a graduate position? ").strip()
            if reason:
                correction["reasoning"]["is_graduate_position"] = reason
                has_corrections = True

        # 2. Correct position type
        print("\n🏷️  Position Type Classification")
        print(f"    Current: {position.get('position_type')}")
        for i, pt in enumerate(self.position_types, 1):
            print(f"    [{i}] {pt}")
        print("    [ENTER] Keep current classification")

        type_choice = input("Position type (number): ").strip()
        if type_choice.isdigit() and 1 <= int(type_choice) <= len(self.position_types):
            new_type = self.position_types[int(type_choice) - 1]
            if new_type != position.get("position_type"):
                correction["corrections"]["position_type"] = new_type
                reason = input(
                    f"Why should this be '{new_type}' instead of '{position.get('position_type')}'? "
                ).strip()
                if reason:
                    correction["reasoning"]["position_type"] = reason
                    has_corrections = True

        # 3. Correct discipline
        print("\n🔬 Discipline Classification")
        print(
            f"    Current: {position.get('discipline')} (confidence: {position.get('discipline_confidence', 'N/A'):.2f})"
        )
        keywords = position.get("discipline_keywords", [])
        if keywords:
            print(f"    Keywords: {', '.join(keywords[:3])}...")
        for i, disc in enumerate(self.disciplines, 1):
            print(f"    [{i}] {disc}")
        print("    [ENTER] Keep current classification")

        disc_choice = input("Discipline (number): ").strip()
        if disc_choice.isdigit() and 1 <= int(disc_choice) <= len(self.disciplines):
            new_discipline = self.disciplines[int(disc_choice) - 1]
            if new_discipline != position.get("discipline"):
                correction["corrections"]["discipline"] = new_discipline
                reason = input(
                    f"Why should this be '{new_discipline}' instead of '{position.get('discipline')}'? "
                ).strip()
                if reason:
                    correction["reasoning"]["discipline"] = reason
                    has_corrections = True

        # 4. Correct university classification
        print("\n🏫 University Classification")
        print(
            f"    Current: {position.get('university_name', 'N/A')} {'(Big 10)' if position.get('is_big10_university') else '(Non-Big 10)'}"
        )

        # Extract university name from organization if needed
        org = position.get("organization", "")
        print(f"    Organization: {org}")

        print("    [y] This is a Big 10 university")
        print("    [n] This is NOT a Big 10 university")
        print("    [u] Update university name")
        print("    [ENTER] Keep current classification")

        univ_choice = input("University classification: ").strip().lower()

        if univ_choice == "y" and not position.get("is_big10_university"):
            correction["corrections"]["is_big10_university"] = True
            # Try to identify the university
            univ_name = input("Which Big 10 university is this? ").strip()
            if univ_name:
                correction["corrections"]["university_name"] = univ_name
                correction["reasoning"][
                    "university"
                ] = f"Identified as Big 10 university: {univ_name}"
                has_corrections = True

        elif univ_choice == "n" and position.get("is_big10_university"):
            correction["corrections"]["is_big10_university"] = False
            reason = input("Why is this NOT a Big 10 university? ").strip()
            if reason:
                correction["reasoning"]["university"] = reason
                has_corrections = True

        elif univ_choice == "u":
            new_name = input("Enter correct university name: ").strip()
            if new_name and new_name != position.get("university_name"):
                correction["corrections"]["university_name"] = new_name
                is_big10 = (
                    input("Is this a Big 10 university? [y/n]: ").strip().lower() == "y"
                )
                correction["corrections"]["is_big10_university"] = is_big10
                correction["reasoning"][
                    "university"
                ] = f"Updated university name to: {new_name}"
                has_corrections = True

        # Overall notes about the correction
        if has_corrections:
            overall_notes = input(
                "\n📝 Overall notes about this correction (optional): "
            ).strip()
            if overall_notes:
                correction["notes"] = overall_notes

        # Remove empty reasoning dict if no corrections were made
        if not has_corrections:
            correction["reasoning"] = {}

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

        # Verification status distribution
        verified = sum(1 for p in positions if p.get("human_verified", False))
        unverified = len(positions) - verified

        print("✅ Verification Status:")
        print(f"   Human Verified:   {verified:3d} positions")
        print(f"   Unverified:       {unverified:3d} positions")

        # Confidence distribution
        confidences = [p.get("grad_confidence", 0) for p in positions]
        low_conf = sum(1 for c in confidences if c < 0.7)
        medium_conf = sum(1 for c in confidences if 0.7 <= c < 0.9)
        high_conf = sum(1 for c in confidences if c >= 0.9)

        print("\n🎯 Confidence Distribution:")
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

    # Sampling strategies
    parser.add_argument(
        "--diverse-sample",
        type=int,
        help="Select N diverse positions from across the full dataset (balanced by discipline, confidence, etc.)",
    )
    parser.add_argument(
        "--smart-sample",
        type=int,
        help="Select N positions using smart sampling (prioritizes unverified, low-confidence, Unknown disciplines)",
    )

    # Options
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Show statistics only, don't start verification",
    )
    parser.add_argument(
        "--include-verified",
        action="store_true",
        help="Include already human-verified positions in sampling (default: exclude them to avoid re-review)",
    )

    args = parser.parse_args()

    # Default to smart sampling if no filter specified
    if not any(
        [
            args.recent,
            args.days,
            args.confidence_threshold,
            args.discipline,
            args.all,
            args.diverse_sample,
            args.smart_sample,
        ]
    ):
        args.smart_sample = 20
        print(
            "💡 No filter specified, defaulting to --smart-sample 20 (prioritizes positions needing review)"
        )

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
