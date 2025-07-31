#!/usr/bin/env python3
"""
Apply human verification corrections to the position dataset.

This script reads corrections from verify_classifications.py and applies them
to the main dataset, improving ML model accuracy over time.

Usage:
    python scripts/apply_corrections.py
    python scripts/apply_corrections.py --dry-run
    python scripts/apply_corrections.py --corrections-file custom_corrections.json
"""

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class CorrectionApplicator:
    """Apply human verification corrections to position dataset."""

    def __init__(self, corrections_file: str = None):
        self.data_file = Path("data/processed/verified_graduate_assistantships.json")
        self.corrections_file = Path(
            corrections_file or "data/verification_corrections.json"
        )
        self.backup_dir = Path("data/verification_backups")

        self.positions: List[Dict] = []
        self.corrections: List[Dict] = []

    def load_data(self) -> None:
        """Load position data and corrections."""
        if not self.data_file.exists():
            print(f"❌ Data file not found: {self.data_file}")
            return

        with open(self.data_file, "r") as f:
            self.positions = json.load(f)
        print(f"📊 Loaded {len(self.positions)} positions")

        if not self.corrections_file.exists():
            print(f"❌ Corrections file not found: {self.corrections_file}")
            return

        with open(self.corrections_file, "r") as f:
            correction_data = json.load(f)
            self.corrections = correction_data.get("corrections", [])
        print(f"📝 Loaded {len(self.corrections)} corrections")

    def create_backup(self) -> Path:
        """Create backup of current dataset."""
        self.backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = (
            self.backup_dir
            / f"verified_graduate_assistantships_backup_{timestamp}.json"
        )

        shutil.copy2(self.data_file, backup_file)
        print(f"💾 Created backup: {backup_file}")
        return backup_file

    def apply_corrections(self, dry_run: bool = False) -> Dict[str, int]:
        """Apply corrections to positions."""
        stats = {"approved": 0, "corrected": 0, "excluded": 0, "not_found": 0}

        # Create position lookup by ID
        position_lookup = {
            p.get("position_id"): i for i, p in enumerate(self.positions)
        }

        # Track positions to exclude
        excluded_positions = set()

        for correction in self.corrections:
            position_id = correction.get("position_id")
            action = correction.get("action")

            if position_id not in position_lookup:
                print(f"⚠️  Position not found: {position_id}")
                stats["not_found"] += 1
                continue

            pos_index = position_lookup[position_id]
            position = self.positions[pos_index]

            if action == "approved":
                # Mark as human-verified
                if not dry_run:
                    position["human_verified"] = True
                    position["verified_at"] = correction.get("verified_at")
                stats["approved"] += 1
                print(f"✅ Approved: {position.get('title', 'Unknown')[:50]}...")

            elif action == "corrected":
                # Apply corrections
                corrections = correction.get("corrections", {})
                original = correction.get("original", {})

                changes = []
                for field, new_value in corrections.items():
                    old_value = position.get(field)
                    if not dry_run:
                        position[field] = new_value
                        position["human_verified"] = True
                        position["verified_at"] = correction.get("verified_at")
                        # Store original ML prediction for analysis
                        if "ml_original" not in position:
                            position["ml_original"] = original
                    changes.append(f"{field}: {old_value} → {new_value}")

                stats["corrected"] += 1
                print(f"🔧 Corrected: {position.get('title', 'Unknown')[:40]}...")
                for change in changes:
                    print(f"    {change}")

            elif action == "excluded":
                # Mark for exclusion
                excluded_positions.add(pos_index)
                stats["excluded"] += 1
                reason = correction.get("reason", "No reason provided")
                print(
                    f"❌ Excluded: {position.get('title', 'Unknown')[:40]}... (Reason: {reason})"
                )

        # Remove excluded positions (in reverse order to maintain indices)
        if not dry_run and excluded_positions:
            for pos_index in sorted(excluded_positions, reverse=True):
                self.positions.pop(pos_index)

        return stats

    def save_updated_data(self) -> None:
        """Save updated dataset."""
        with open(self.data_file, "w") as f:
            json.dump(self.positions, f, indent=2)
        print(f"💾 Updated dataset saved to {self.data_file}")

    def archive_corrections(self) -> None:
        """Archive applied corrections."""
        archive_dir = Path("data/verification_archives")
        archive_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_file = archive_dir / f"applied_corrections_{timestamp}.json"

        shutil.move(self.corrections_file, archive_file)
        print(f"📁 Archived corrections to {archive_file}")

    def generate_ml_training_data(self) -> None:
        """Generate training data for ML model improvement."""
        verified_positions = [p for p in self.positions if p.get("human_verified")]

        if not verified_positions:
            print("ℹ️  No human-verified positions found for training data")
            return

        training_file = Path("data/ml_training_data.json")
        training_data = {
            "generated_at": datetime.now().isoformat(),
            "verified_positions": len(verified_positions),
            "positions": verified_positions,
        }

        with open(training_file, "w") as f:
            json.dump(training_data, f, indent=2)

        print(
            f"🤖 Generated training data: {training_file} ({len(verified_positions)} verified positions)"
        )

    def show_accuracy_report(self) -> None:
        """Show ML model accuracy based on human corrections."""
        corrected_positions = [p for p in self.positions if "ml_original" in p]

        if not corrected_positions:
            print("ℹ️  No corrections found for accuracy analysis")
            return

        print(
            f"\n📊 ML Model Accuracy Report ({len(corrected_positions)} corrections analyzed):"
        )

        # Analyze graduate position accuracy
        grad_correct = 0
        grad_total = 0

        # Analyze discipline accuracy
        disc_correct = 0
        disc_total = 0

        for pos in corrected_positions:
            original = pos.get("ml_original", {})

            # Graduate position accuracy
            if "is_graduate_position" in original:
                grad_total += 1
                if original["is_graduate_position"] == pos.get("is_graduate_position"):
                    grad_correct += 1

            # Discipline accuracy
            if "discipline" in original and original["discipline"] != "Unknown":
                disc_total += 1
                if original["discipline"] == pos.get("discipline"):
                    disc_correct += 1

        if grad_total > 0:
            grad_accuracy = (grad_correct / grad_total) * 100
            print(
                f"🎓 Graduate Position Classification: {grad_accuracy:.1f}% ({grad_correct}/{grad_total})"
            )

        if disc_total > 0:
            disc_accuracy = (disc_correct / disc_total) * 100
            print(
                f"🔬 Discipline Classification: {disc_accuracy:.1f}% ({disc_correct}/{disc_total})"
            )


def main():
    parser = argparse.ArgumentParser(
        description="Apply human verification corrections to dataset"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without applying",
    )
    parser.add_argument(
        "--corrections-file", type=str, help="Custom corrections file path"
    )
    parser.add_argument("--no-backup", action="store_true", help="Skip creating backup")

    args = parser.parse_args()

    applicator = CorrectionApplicator(args.corrections_file)
    applicator.load_data()

    if not applicator.positions or not applicator.corrections:
        print("❌ Cannot proceed without data and corrections")
        return

    print(
        f"\n🚀 {'DRY RUN: ' if args.dry_run else ''}Applying {len(applicator.corrections)} corrections..."
    )

    if not args.dry_run and not args.no_backup:
        applicator.create_backup()

    stats = applicator.apply_corrections(dry_run=args.dry_run)

    print("\n📊 Summary:")
    print(f"   ✅ Approved: {stats['approved']}")
    print(f"   🔧 Corrected: {stats['corrected']}")
    print(f"   ❌ Excluded: {stats['excluded']}")
    print(f"   ⚠️  Not found: {stats['not_found']}")

    if args.dry_run:
        print("\n💡 This was a dry run. Use without --dry-run to apply changes.")
        return

    if stats["approved"] + stats["corrected"] + stats["excluded"] > 0:
        applicator.save_updated_data()
        applicator.generate_ml_training_data()
        applicator.show_accuracy_report()
        applicator.archive_corrections()

        print(
            f"\n✅ Successfully applied corrections to {len(applicator.positions)} positions"
        )
        print(
            "💡 Regenerate dashboard analytics with: python scripts/generate_dashboard_analytics.py"
        )
    else:
        print("\n ℹ️ No changes were applied")


if __name__ == "__main__":
    main()
