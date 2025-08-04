#!/usr/bin/env python3
"""
Cleanup legacy local data files after successful migration to Supabase
Creates backups before removal for safety
"""

import os
import shutil
from datetime import datetime


def cleanup_legacy_files():
    """Clean up legacy data files after migration"""

    base_dir = "/Users/cchizinski2/Dev/wildlife-grad-dashboard"
    backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(base_dir, f"data/legacy_backup_{backup_timestamp}")

    print("🧹 Legacy Data Cleanup")
    print("=" * 60)

    # Create backup directory
    os.makedirs(backup_dir, exist_ok=True)
    print(f"📦 Created backup directory: {backup_dir}")

    # Files to backup and potentially remove
    legacy_files = [
        "data/enhanced_data.json",
        "data/historical_positions.json",
        "data/ml_training_data.json",
        "dashboard/data/enhanced_data.json",
        "dashboard/data/export_data.json",
        "dashboard/data/historical_positions.json",
        "dashboard/data/verified_graduate_assistantships.json",
        "dashboard/data/dashboard_analytics.json",
    ]

    # Files to keep (raw source data)
    keep_files = [
        "data/raw/all_positions_detailed.json",
        "data/raw/all_positions_detailed.csv",
        "data/processed/verified_graduate_assistantships.json",
        "data/processed/verified_graduate_assistantships.csv",
        "data/processed/enhanced_analysis.json",
        "data/processed/classification_report.json",
    ]

    backed_up = 0

    for file_path in legacy_files:
        full_path = os.path.join(base_dir, file_path)
        if os.path.exists(full_path):
            # Create backup
            backup_path = os.path.join(backup_dir, os.path.basename(file_path))
            try:
                shutil.copy2(full_path, backup_path)
                print(f"📋 Backed up: {file_path}")
                backed_up += 1

                # Get file size for reporting
                size_mb = os.path.getsize(full_path) / 1024 / 1024
                print(f"   Size: {size_mb:.1f} MB")

            except Exception as e:
                print(f"❌ Error backing up {file_path}: {e}")

    print(f"\n✅ Backed up {backed_up} files to: {backup_dir}")

    # Show what we're keeping
    print("\n📌 Keeping these source files:")
    kept_files = 0
    for file_path in keep_files:
        full_path = os.path.join(base_dir, file_path)
        if os.path.exists(full_path):
            size_mb = os.path.getsize(full_path) / 1024 / 1024
            print(f"   ✅ {file_path} ({size_mb:.1f} MB)")
            kept_files += 1
        else:
            print(f"   ⚠️ {file_path} (not found)")

    print("\n📊 CLEANUP SUMMARY:")
    print(f"   🗂️ Files backed up: {backed_up}")
    print(f"   📌 Source files kept: {kept_files}")
    print(f"   💾 Backup location: {backup_dir}")

    print("\n🎯 NEXT STEPS:")
    print("1. Verify your dashboard works correctly with Supabase")
    print("2. After 1-2 weeks of successful operation, you can safely delete:")
    print("   - The legacy backup directory")
    print("   - Any remaining JSON files in dashboard/data/")
    print("3. Your raw source data in data/raw/ and data/processed/ is preserved")

    # Create a README in the backup
    readme_content = f"""# Legacy Data Backup - {backup_timestamp}

This directory contains backups of legacy local data files that were migrated to Supabase.

## Migration Summary
- Migration completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Files backed up: {backed_up}
- Supabase project: https://mqbkzveymkehgkbcjgba.supabase.co

## Safe to Delete
After 1-2 weeks of successful dashboard operation, this backup can be safely deleted.

## Source Data Preserved
The following source files are preserved in the main project:
{chr(10).join(f'- {f}' for f in keep_files)}
"""

    with open(os.path.join(backup_dir, "README.md"), "w") as f:
        f.write(readme_content)

    print("\n📝 Created README.md in backup directory")
    print("🎉 Cleanup completed successfully!")


if __name__ == "__main__":
    cleanup_legacy_files()
