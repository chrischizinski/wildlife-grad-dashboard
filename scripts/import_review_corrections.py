#!/usr/bin/env python3
"""
Import corrections from Excel review spreadsheet and apply them to the dataset.

This script reads the completed Excel review file and applies all corrections
to the position data, updating the verified_graduate_assistantships.json file.

Usage:
    python scripts/import_review_corrections.py position_review_20241201_123456.xlsx
    python scripts/import_review_corrections.py my_review.xlsx --backup
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import shutil

try:
    import pandas as pd
except ImportError:
    print("❌ Required packages not installed. Please run:")
    print("   pip install pandas openpyxl")
    sys.exit(1)


class ReviewImporter:
    """Import and apply corrections from Excel review spreadsheet."""

    def __init__(self):
        self.data_file = Path("data/processed/verified_graduate_assistantships.json")
        self.backup_dir = Path("data/backups")
        self.positions: List[Dict] = []
        self.corrections_applied = 0
        self.exclusions_applied = 0
        self.verifications_applied = 0

    def create_backup(self) -> None:
        """Create backup of original data file."""
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"verified_graduate_assistantships_backup_{timestamp}.json"
        
        shutil.copy2(self.data_file, backup_file)
        print(f"📦 Backup created: {backup_file}")

    def load_data(self) -> None:
        """Load position data."""
        if not self.data_file.exists():
            print(f"❌ Data file not found: {self.data_file}")
            sys.exit(1)

        with open(self.data_file, "r") as f:
            self.positions = json.load(f)

        print(f"📊 Loaded {len(self.positions)} positions from dataset")

    def load_review_file(self, excel_file: str) -> pd.DataFrame:
        """Load and validate Excel review file."""
        try:
            df = pd.read_excel(excel_file, sheet_name="Position Review")
            print(f"📋 Loaded {len(df)} positions from review file")
            return df
        except Exception as e:
            print(f"❌ Error loading Excel file: {e}")
            sys.exit(1)

    def validate_review_data(self, df: pd.DataFrame) -> bool:
        """Validate the review data structure."""
        required_columns = [
            'Position_ID', 'Review_Status', 'Corrected_Graduate_Position',
            'Corrected_Position_Type', 'Corrected_Discipline', 
            'Corrected_University_Name', 'Corrected_Big10_University'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"❌ Missing required columns: {missing_columns}")
            return False
        
        # Check for any reviews
        reviewed_count = len(df[df['Review_Status'].notna() & (df['Review_Status'] != '')])
        if reviewed_count == 0:
            print("⚠️ No positions have been reviewed (Review_Status column is empty)")
            return False
        
        print(f"✅ Found {reviewed_count} reviewed positions")
        return True

    def process_corrections(self, df: pd.DataFrame) -> None:
        """Process all corrections from the review file."""
        print("\n🔧 Processing corrections...")
        
        # Create position lookup for fast access
        position_lookup = {pos['position_id']: pos for pos in self.positions}
        
        corrections_log = []
        
        for _, row in df.iterrows():
            position_id = str(row['Position_ID'])
            review_status = row.get('Review_Status', '')
            
            if pd.isna(review_status) or review_status == '':
                continue  # Skip unreviewed positions
            
            if position_id not in position_lookup:
                print(f"⚠️ Position {position_id} not found in dataset")
                continue
            
            position = position_lookup[position_id]
            correction_entry = {
                'position_id': position_id,
                'review_status': review_status,
                'reviewer': row.get('Reviewer_Name', ''),
                'review_notes': row.get('Review_Notes', ''),
                'timestamp': datetime.now().isoformat(),
                'corrections': {}
            }
            
            # Process based on review status
            if review_status == '✅ Correct':
                # Mark as human verified
                position['human_verified'] = True
                position['human_verified_at'] = datetime.now().isoformat()
                position['verified_by'] = row.get('Reviewer_Name', 'Anonymous')
                self.verifications_applied += 1
                
            elif review_status == '🔧 Needs Correction':
                # Apply corrections
                corrections_made = self.apply_corrections(position, row, correction_entry)
                if corrections_made:
                    position['human_verified'] = True
                    position['human_verified_at'] = datetime.now().isoformat()
                    position['verified_by'] = row.get('Reviewer_Name', 'Anonymous')
                    self.corrections_applied += 1
                
            elif review_status == '❌ Exclude':
                # Mark for exclusion
                position['excluded'] = True
                position['exclusion_reason'] = row.get('Review_Notes', 'Marked for exclusion during review')
                position['excluded_at'] = datetime.now().isoformat()
                position['excluded_by'] = row.get('Reviewer_Name', 'Anonymous')
                self.exclusions_applied += 1
                
            # Skip positions marked as "⏭️ Skip" - no action needed
            
            corrections_log.append(correction_entry)
        
        # Save corrections log
        self.save_corrections_log(corrections_log)

    def apply_corrections(self, position: Dict, row: pd.Series, correction_entry: Dict) -> bool:
        """Apply individual corrections to a position."""
        corrections_made = False
        
        # Graduate position correction
        corrected_grad = row.get('Corrected_Graduate_Position', '')
        if pd.notna(corrected_grad) and corrected_grad != '':
            new_value = corrected_grad.lower() == 'yes'
            if position.get('is_graduate_position') != new_value:
                correction_entry['corrections']['is_graduate_position'] = {
                    'old': position.get('is_graduate_position'),
                    'new': new_value
                }
                position['is_graduate_position'] = new_value
                corrections_made = True
        
        # Position type correction
        corrected_type = row.get('Corrected_Position_Type', '')
        if pd.notna(corrected_type) and corrected_type != '':
            if position.get('position_type') != corrected_type:
                correction_entry['corrections']['position_type'] = {
                    'old': position.get('position_type'),
                    'new': corrected_type
                }
                position['position_type'] = corrected_type
                corrections_made = True
        
        # Discipline correction
        corrected_discipline = row.get('Corrected_Discipline', '')
        if pd.notna(corrected_discipline) and corrected_discipline != '':
            if position.get('discipline') != corrected_discipline:
                correction_entry['corrections']['discipline'] = {
                    'old': position.get('discipline'),
                    'new': corrected_discipline
                }
                position['discipline'] = corrected_discipline
                # Reset confidence when manually corrected
                position['discipline_confidence'] = 1.0
                corrections_made = True
        
        # University name correction
        corrected_university = row.get('Corrected_University_Name', '')
        if pd.notna(corrected_university) and corrected_university != '':
            if position.get('university_name') != corrected_university:
                correction_entry['corrections']['university_name'] = {
                    'old': position.get('university_name'),
                    'new': corrected_university
                }
                position['university_name'] = corrected_university
                corrections_made = True
        
        # Big 10 classification correction
        corrected_big10 = row.get('Corrected_Big10_University', '')
        if pd.notna(corrected_big10) and corrected_big10 != '':
            if corrected_big10.lower() != 'unknown':
                new_value = corrected_big10.lower() == 'yes'
                if position.get('is_big10_university') != new_value:
                    correction_entry['corrections']['is_big10_university'] = {
                        'old': position.get('is_big10_university'),
                        'new': new_value
                    }
                    position['is_big10_university'] = new_value
                    corrections_made = True
        
        return corrections_made

    def save_corrections_log(self, corrections_log: List[Dict]) -> None:
        """Save detailed corrections log."""
        log_file = Path("data/review_corrections_log.json")
        
        log_data = {
            'import_timestamp': datetime.now().isoformat(),
            'total_corrections': len(corrections_log),
            'corrections_applied': self.corrections_applied,
            'verifications_applied': self.verifications_applied,
            'exclusions_applied': self.exclusions_applied,
            'corrections': corrections_log
        }
        
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        print(f"📄 Corrections log saved: {log_file}")

    def save_updated_data(self) -> None:
        """Save the updated position data."""
        with open(self.data_file, 'w') as f:
            json.dump(self.positions, f, indent=2)
        
        print(f"💾 Updated data saved: {self.data_file}")

    def generate_summary_report(self) -> None:
        """Generate a summary report of all changes."""
        print("\n" + "="*60)
        print("📊 IMPORT SUMMARY REPORT")
        print("="*60)
        
        print(f"✅ Verifications applied: {self.verifications_applied}")
        print(f"🔧 Corrections applied: {self.corrections_applied}")
        print(f"❌ Exclusions applied: {self.exclusions_applied}")
        print(f"📝 Total changes: {self.verifications_applied + self.corrections_applied + self.exclusions_applied}")
        
        # Calculate verification statistics
        verified_count = sum(1 for pos in self.positions if pos.get('human_verified', False))
        excluded_count = sum(1 for pos in self.positions if pos.get('excluded', False))
        remaining_count = len(self.positions) - verified_count - excluded_count
        
        print(f"\n📈 Dataset Status:")
        print(f"   Human verified: {verified_count} positions")
        print(f"   Excluded: {excluded_count} positions")
        print(f"   Remaining to review: {remaining_count} positions")
        
        verification_percentage = (verified_count / len(self.positions)) * 100
        print(f"   Verification progress: {verification_percentage:.1f}%")
        
        print(f"\n💡 Next steps:")
        if remaining_count > 0:
            print(f"   - {remaining_count} positions still need review")
            print(f"   - Run: python scripts/export_for_review.py --unverified-only")
            print(f"   - Continue reviewing the remaining positions")
        else:
            print(f"   - All positions have been reviewed!")
            print(f"   - Update the dashboard: python scripts/update_dashboard_data.py")
        
        print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Import corrections from Excel review spreadsheet"
    )
    
    parser.add_argument(
        "excel_file",
        help="Path to the completed Excel review file"
    )
    
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create backup before applying changes (recommended)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true", 
        help="Show what would be changed without applying changes"
    )
    
    args = parser.parse_args()
    
    print("🚀 Wildlife Graduate Assistantships - Review Import")
    print("=" * 60)
    
    if not Path(args.excel_file).exists():
        print(f"❌ Excel file not found: {args.excel_file}")
        sys.exit(1)
    
    importer = ReviewImporter()
    
    # Create backup if requested
    if args.backup:
        importer.create_backup()
    
    # Load data
    importer.load_data()
    
    # Load and validate review file
    df = importer.load_review_file(args.excel_file)
    
    if not importer.validate_review_data(df):
        print("❌ Review file validation failed")
        sys.exit(1)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be applied")
        # Here you could add logic to show what would change
        return
    
    # Process corrections
    importer.process_corrections(df)
    
    # Save updated data
    importer.save_updated_data()
    
    # Generate summary report
    importer.generate_summary_report()
    
    print(f"\n✅ Review import complete!")
    print(f"📄 Processed file: {args.excel_file}")


if __name__ == "__main__":
    main()