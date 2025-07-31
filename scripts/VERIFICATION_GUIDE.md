# CLI Position Verification Guide

## Quick Start

### 1. Review Recent Positions (Recommended for weekly verification)
```bash
python scripts/verify_classifications.py --recent 20
```

### 2. Focus on Low-Confidence Classifications
```bash
python scripts/verify_classifications.py --confidence-threshold 0.8
```

### 3. Review Specific Disciplines (e.g., "Unknown" positions)
```bash
python scripts/verify_classifications.py --discipline "Unknown"
```

### 4. Check Statistics First
```bash
python scripts/verify_classifications.py --recent 50 --stats-only
```

## Interactive Commands During Verification

When reviewing each position, you have these options:

- **`[ENTER]`** - Classification is correct (approve)
- **`[c]`** - Correct the classification (interactive correction)
- **`[x]`** - Exclude this position from dataset
- **`[s]`** - Skip this position (review later)
- **`[q]`** - Quit verification session

## Correction Process

When you choose `[c]` to correct, you'll be prompted to:

1. **Graduate Position**: Is this truly a graduate assistantship/fellowship?
2. **Position Type**: Choose from Graduate/Professional/Technician/Exclude
3. **Discipline**: Select the correct discipline category
4. **Notes**: Add optional notes about your decision

## Applying Corrections

After verification session:

```bash
# Preview what will change
python scripts/apply_corrections.py --dry-run

# Apply corrections to dataset
python scripts/apply_corrections.py

# Regenerate dashboard with corrected data
python scripts/generate_dashboard_analytics.py
```

## Recommended Weekly Workflow

1. **Quick stats check**:
   ```bash
   python scripts/verify_classifications.py --recent 50 --stats-only
   ```

2. **Focus on problem areas**:
   ```bash
   # Review unknown disciplines
   python scripts/verify_classifications.py --discipline "Unknown"

   # Review low-confidence classifications
   python scripts/verify_classifications.py --confidence-threshold 0.7
   ```

3. **Apply corrections**:
   ```bash
   python scripts/apply_corrections.py
   python scripts/generate_dashboard_analytics.py
   ```

## Tips for Effective Verification

### What to Look For:

**Graduate Positions Should Have**:
- PhD, Masters, MS, PhD student mentions
- Assistantship, fellowship, graduate program
- University affiliation
- Student stipend/tuition coverage
- Research or teaching responsibilities

**Common Misclassifications**:
- Post-docs (often classified as Graduate, should be Professional)
- Internships (often classified as Graduate, should be Professional/Technician)
- Staff positions at universities (should be Professional)
- Research scientist positions (should be Professional)

**Discipline Guidelines**:
- **Wildlife & Natural Resources**: Wildlife management, conservation, ecology
- **Fisheries & Aquatic Sciences**: Fish biology, aquatic ecology, hydrology
- **Natural Resource Management**: Forestry, land management, parks
- **Environmental Science**: Pollution, climate, environmental policy
- **Conservation Biology**: Biodiversity, endangered species, habitat conservation
- **Unknown**: Genuinely unclear or interdisciplinary
- **Other**: Doesn't fit other categories

### Time Investment:
- **Quick session**: 10-15 minutes for ~20 recent positions
- **Thorough session**: 30 minutes for ~50 positions focusing on low-confidence
- **Monthly deep dive**: 1 hour reviewing broader patterns

## Files Created:

- `data/verification_corrections.json` - Your corrections (temporary)
- `data/verification_backups/` - Automatic backups before applying changes
- `data/verification_archives/` - Archive of applied corrections
- `data/ml_training_data.json` - Verified data for improving ML models

## Advanced Usage

### Filter by Date Range:
```bash
python scripts/verify_classifications.py --days 7  # Last week
python scripts/verify_classifications.py --days 30 # Last month
```

### Custom Corrections File:
```bash
python scripts/apply_corrections.py --corrections-file custom_corrections.json
```

### Skip Backup (faster, but less safe):
```bash
python scripts/apply_corrections.py --no-backup
```

## Expected Accuracy Improvements

With regular verification, you should see:
- **Immediate**: Better quality in dashboard analytics
- **1 month**: Improved ML confidence scores
- **3 months**: Fewer "Unknown" classifications
- **6 months**: Overall classification accuracy >95%

## Questions?

The verification system tracks your corrections and shows ML accuracy improvements over time. Regular verification (even 10-15 minutes weekly) will significantly improve the platform's usefulness for wildlife job seekers and researchers.
