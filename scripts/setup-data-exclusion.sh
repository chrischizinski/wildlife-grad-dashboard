#!/bin/bash
# WARNING: This removes data files from version control entirely
# Use only if you want GitHub Actions to be the sole data source

echo "⚠️  WARNING: This will remove data files from version control!"
echo "📊 Data will only be managed by GitHub Actions automation."
read -p "Are you sure you want to continue? (y/N) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️  Removing data files from version control..."

    # Remove data files from tracking
    git rm --cached data/processed/*.json data/processed/*.csv data/raw/*.json data/raw/*.csv dashboard/data/*.json 2>/dev/null || true

    # Add to gitignore
    cat >> .gitignore << EOF

# Data files (managed by GitHub Actions only)
data/processed/*.json
data/processed/*.csv
data/raw/*.json
data/raw/*.csv
dashboard/data/*.json
!dashboard/data/.gitkeep
EOF

    # Create .gitkeep files to preserve directory structure
    touch data/processed/.gitkeep data/raw/.gitkeep dashboard/data/.gitkeep

    echo "✅ Data files excluded from version control"
    echo "📁 Directory structure preserved with .gitkeep files"
    echo "🤖 Data will now be managed exclusively by GitHub Actions"
else
    echo "❌ Operation cancelled"
fi
