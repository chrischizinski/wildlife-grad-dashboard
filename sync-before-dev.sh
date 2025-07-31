#!/bin/bash
# Sync with remote before development to avoid conflicts

set -e

echo "🔄 Syncing with remote repository..."

# Stash any local changes
if ! git diff --quiet; then
    echo "📦 Stashing local changes..."
    git stash push -u -m "Auto-stash before sync $(date)"
fi

# Pull latest changes
echo "⬇️ Pulling latest changes from origin/main..."
git pull origin main

# Pop stash if there was one
if git stash list | grep -q "Auto-stash before sync"; then
    echo "📤 Restoring local changes..."
    git stash pop
fi

echo "✅ Repository synced successfully!"
echo "💡 Now you can work on the latest version without conflicts."