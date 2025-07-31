#!/usr/bin/env python3
"""
Analyze ML model improvements from human corrections.

This script demonstrates how human verification data is used to improve
the machine learning models over time.
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List


class MLImprovementAnalyzer:
    """Analyze how human corrections can improve ML models."""

    def __init__(self):
        self.training_data_file = Path("data/ml_training_data.json")
        self.archives_dir = Path("data/verification_archives")

    def analyze_correction_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in human corrections to identify ML model weaknesses."""

        # Load all correction archives
        all_corrections = []
        for archive_file in self.archives_dir.glob("applied_corrections_*.json"):
            with open(archive_file, "r") as f:
                archive = json.load(f)
                all_corrections.extend(archive.get("corrections", []))

        analysis: Dict[str, Any] = {
            "total_corrections": len(all_corrections),
            "classification_errors": defaultdict(int),
            "common_error_patterns": defaultdict(list),
            "feature_importance_signals": defaultdict(list),
        }

        # Analyze each correction
        for correction in all_corrections:
            if correction.get("action") != "corrected":
                continue

            original = correction.get("original", {})
            corrections = correction.get("corrections", {})
            reasoning = correction.get("reasoning", {})

            # Track classification error types
            for field, new_value in corrections.items():
                old_value = original.get(field)
                if old_value != new_value:
                    error_key = f"{field}: {old_value} → {new_value}"
                    analysis["classification_errors"][error_key] += 1

                    # Capture human reasoning for this error pattern
                    if field in reasoning:
                        error_pattern_key = f"{field}_errors"
                        analysis["common_error_patterns"][error_pattern_key].append(
                            {
                                "old": old_value,
                                "new": new_value,
                                "reason": reasoning[field],
                            }
                        )

        return analysis

    def generate_training_insights(self) -> Dict[str, List[str]]:
        """Generate insights for improving ML model training."""

        analysis = self.analyze_correction_patterns()
        insights: Dict[str, List[str]] = {
            "keyword_patterns": [],
            "classification_rules": [],
            "feature_engineering": [],
            "model_architecture": [],
        }

        # Analyze common error patterns
        for error_type, examples in analysis["common_error_patterns"].items():
            if "is_graduate_position" in error_type:
                insights["keyword_patterns"].extend(
                    [
                        "Add 'postdoc', 'postdoctoral' as negative indicators for graduate positions",
                        "Add 'crew lead', 'crew leader' as professional position indicators",
                        "Require explicit 'degree', 'MS', 'PhD', 'thesis' mentions for graduate classification",
                        "Fellowship without university affiliation should be professional",
                    ]
                )

                insights["classification_rules"].extend(
                    [
                        "IF contains('postdoc') OR contains('fellowship') AND NOT contains('university') THEN is_graduate_position = False",
                        "IF contains('crew lead') OR contains('leadership role') THEN position_type = 'Professional'",
                    ]
                )

            elif "discipline" in error_type:
                insights["keyword_patterns"].extend(
                    [
                        "Add 'archaeology', 'archaeological', 'cultural resource' for discipline classification",
                        "Improve keyword extraction from job descriptions and requirements",
                    ]
                )

        insights["feature_engineering"].extend(
            [
                "Extract education requirements (Bachelor's, Master's, PhD) as features",
                "Add organizational type (university, government, private) as feature",
                "Create university affiliation detection pipeline",
                "Add salary range categorization for position type classification",
            ]
        )

        insights["model_architecture"].extend(
            [
                "Implement ensemble model combining text classification and rule-based logic",
                "Add confidence calibration based on human correction patterns",
                "Create separate models for each classification type with different feature weights",
            ]
        )

        return insights

    def create_training_dataset(self) -> str:
        """Create structured training dataset from human-verified positions."""

        if not self.training_data_file.exists():
            return "No training data file found"

        with open(self.training_data_file, "r") as f:
            training_data = json.load(f)

        verified_positions = training_data.get("positions", [])

        # Create features and labels for ML training
        training_examples = []

        for position in verified_positions:
            if not position.get("human_verified"):
                continue

            # Extract text features
            text_features = {
                "title": position.get("title", ""),
                "description": position.get("description", ""),
                "requirements": position.get("requirements", ""),
                "organization": position.get("organization", ""),
                "salary": position.get("salary", ""),
                "tags": position.get("tags", ""),
            }

            # Extract labels (human-corrected)
            labels = {
                "is_graduate_position": position.get("is_graduate_position"),
                "position_type": position.get("position_type"),
                "discipline": position.get("discipline"),
                "is_big10_university": position.get("is_big10_university"),
            }

            # Extract original ML predictions for comparison
            ml_original = position.get("ml_original", {})
            human_reasoning = position.get("human_reasoning", {})

            training_examples.append(
                {
                    "features": text_features,
                    "labels": labels,
                    "ml_predictions": ml_original,
                    "human_reasoning": human_reasoning,
                    "position_id": position.get("position_id"),
                }
            )

        return f"Created {len(training_examples)} training examples from human-verified positions"

    def simulate_model_improvement(self) -> Dict[str, float]:
        """Simulate how model accuracy would improve with corrections."""

        analysis = self.analyze_correction_patterns()

        # Simulate accuracy improvements based on correction patterns
        improvements = {}

        for error_pattern, count in analysis["classification_errors"].items():
            field = error_pattern.split(":")[0]

            # Estimate accuracy improvement based on error frequency
            if count >= 3:  # Significant pattern
                improvements[f"{field}_accuracy"] = min(
                    count * 0.05, 0.25
                )  # Cap at 25% improvement
            elif count >= 1:  # Some improvement
                improvements[f"{field}_accuracy"] = count * 0.02

        return improvements


def main():
    """Demonstrate ML improvement analysis."""
    analyzer = MLImprovementAnalyzer()

    print("🤖 ML Model Improvement Analysis")
    print("=" * 50)

    # Analyze correction patterns
    analysis = analyzer.analyze_correction_patterns()
    print("\n📊 Correction Summary:")
    print(f"   Total corrections analyzed: {analysis['total_corrections']}")

    print("\n❌ Most Common Classification Errors:")
    for error, count in sorted(
        analysis["classification_errors"].items(), key=lambda x: x[1], reverse=True
    )[:5]:
        print(f"   {error}: {count} times")

    # Generate training insights
    insights = analyzer.generate_training_insights()
    print("\n💡 Key Training Insights:")
    for category, items in insights.items():
        if items:
            print(f"\n   {category.replace('_', ' ').title()}:")
            for item in items[:3]:  # Show top 3
                print(f"   - {item}")

    # Training dataset creation
    training_result = analyzer.create_training_dataset()
    print(f"\n🎯 Training Dataset: {training_result}")

    # Simulate improvements
    improvements = analyzer.simulate_model_improvement()
    if improvements:
        print("\n📈 Projected Accuracy Improvements:")
        for field, improvement in improvements.items():
            print(f"   {field}: +{improvement:.1%}")

    print("\n🔄 Next Steps for ML Improvement:")
    print("   1. Retrain models with human-verified data")
    print("   2. Implement new keyword patterns identified")
    print("   3. Add rule-based logic for common error cases")
    print("   4. Validate improvements on held-out test set")


if __name__ == "__main__":
    main()
