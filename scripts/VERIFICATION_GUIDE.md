# CLI Position Verification Guide

## Quick Start

### 1. Smart Sampling (Recommended - Default Behavior)
```bash
# Automatically prioritizes positions needing review (unverified, low-confidence, Unknown disciplines)
python scripts/verify_classifications.py
# or explicitly:
python scripts/verify_classifications.py --smart-sample 20
```

### 2. Diverse Sampling (Best for Training ML Models)
```bash
# Balanced sample across all disciplines, confidence levels, and time periods
python scripts/verify_classifications.py --diverse-sample 25
```

### 3. Focus on Low-Confidence Classifications
```bash
python scripts/verify_classifications.py --confidence-threshold 0.8
```

### 4. Review Specific Disciplines
```bash
python scripts/verify_classifications.py --discipline "Unknown"
```

### 5. Review Recent Positions
```bash
python scripts/verify_classifications.py --recent 20
```

### 6. Check Statistics First
```bash
python scripts/verify_classifications.py --smart-sample 50 --stats-only
```

## Interactive Commands During Verification

When reviewing each position, you have these options:

- **`[ENTER]`** - Classification is correct (approve)
- **`[c]`** - Correct the classification (interactive correction)
- **`[x]`** - Exclude this position from dataset
- **`[s]`** - Skip this position (review later)
- **`[q]`** - Quit verification session

## Comprehensive Correction Process

When you choose `[c]` to correct, you'll be prompted to review **ALL** classification types:

### 1. Graduate Position Classification
- Current classification and confidence score
- **Reasoning required** if you change the classification
- Options: Yes (graduate) / No (professional/staff) / Keep current

### 2. Position Type Classification
- Current: Graduate/Professional/Technician
- **Reasoning required** for any changes
- Choose from: Graduate/Professional/Technician/Exclude

### 3. Discipline Classification
- Current discipline and confidence score
- Shows ML-identified keywords for context
- **Reasoning required** for any changes
- Options: Wildlife & Natural Resources, Environmental Science, etc.

### 4. University Classification
- Current university name and Big 10 status
- Shows organization field for context
- **Reasoning required** for any changes
- Options: Mark as Big 10, Not Big 10, Update university name

### 5. Overall Notes
- Optional general comments about the position
- Helps with future ML model improvements

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

1. **Smart sampling session (10-15 minutes)**:
   ```bash
   # Default smart sampling - automatically finds positions needing review
   python scripts/verify_classifications.py --smart-sample 20
   ```

2. **Diverse sampling for ML training (weekly)**:
   ```bash
   # Balanced sample across the full dataset for better ML training
   python scripts/verify_classifications.py --diverse-sample 15
   ```

3. **Focus on specific problem areas (as needed)**:
   ```bash
   # Review unknown disciplines
   python scripts/verify_classifications.py --discipline "Unknown"

   # Review low-confidence classifications
   python scripts/verify_classifications.py --confidence-threshold 0.7
   ```

4. **Apply corrections**:
   ```bash
   python scripts/apply_corrections.py
   python scripts/generate_dashboard_analytics.py
   ```

## Sampling Strategy Guide

### 🧠 Smart Sampling (`--smart-sample N`)
**Best for:** Daily/weekly verification sessions
- **Automatically excludes already-verified positions** (no re-review needed)
- Prioritizes unverified positions (score +10)
- Emphasizes low-confidence classifications (score +5 per low confidence)
- Targets "Unknown" disciplines (score +8)
- Identifies conflicting classifications (score +3)
- Adds randomness to avoid repetition

### 🌐 Diverse Sampling (`--diverse-sample N`)
**Best for:** ML model training and comprehensive coverage
- **Automatically excludes already-verified positions** (no re-review needed)
- Samples proportionally from each discipline
- Balances confidence levels (low/medium/high)
- Prioritizes unverified positions for sampling
- Ensures geographic and temporal spread
- Prevents bias toward recent or popular positions

### ⏰ Recent Sampling (`--recent N`)
**Best for:** Monitoring new incoming positions
- **Automatically excludes already-verified positions** (no re-review needed)
- Shows most recently scraped positions
- Good for staying current with new listings
- May miss older positions needing verification

### 🔄 **No Re-Review Policy**
**By default, all sampling strategies exclude positions that have already been human-verified:**
- ✅ **Prevents redundant verification work**
- 🎯 **Focuses effort on positions that actually need review**
- 📊 **Shows verification status in statistics**

**Override when needed:**
```bash
# Include already-verified positions (rare use case)
python scripts/verify_classifications.py --smart-sample 20 --include-verified
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
- **Immediate**: Better quality in dashboard analytics with reasoning for each correction
- **1 month**: Improved ML confidence scores across all classification types
- **3 months**: Fewer "Unknown" classifications and better university identification
- **6 months**: Overall classification accuracy >95% for all fields

## Classification Quality Tracking

The system now tracks accuracy for:
- 🎓 Graduate Position Classification
- 🏷️ Position Type Classification
- 🔬 Discipline Classification
- 🏫 Big 10 University Classification
- 🏛️ University Name Identification

Each correction includes human reasoning that helps improve future ML models.

## Questions?

The verification system tracks your corrections and shows ML accuracy improvements over time. Regular verification (even 10-15 minutes weekly) will significantly improve the platform's usefulness for wildlife job seekers and researchers.
