#!/bin/bash
# Script to push the Odoo upgrade skill to GitHub

# Set your GitHub repository URL here
GITHUB_REPO_URL="https://github.com/YOUR_USERNAME/odoo-upgrade-skill.git"

echo "📦 Preparing to push Odoo Upgrade Skill to GitHub..."

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "❌ Git not initialized. Initializing..."
    git init
fi

# Add remote if not exists
if ! git remote | grep -q "origin"; then
    echo "➕ Adding GitHub remote..."
    git remote add origin $GITHUB_REPO_URL
else
    echo "✅ Remote already configured"
fi

# Create branch if needed
git branch -M main

# Add any new changes
git add .

# Check if there are changes to commit
if ! git diff --cached --quiet; then
    echo "📝 Committing changes..."
    git commit -m "Update: Odoo upgrade skill enhancements

- Improved pattern detection
- Additional error fixes
- Updated documentation

🤖 Generated with Claude Code"
fi

# Push to GitHub
echo "🚀 Pushing to GitHub..."
git push -u origin main

echo "✅ Successfully pushed to GitHub!"
echo "🔗 Repository: $GITHUB_REPO_URL"
echo ""
echo "📋 Next steps:"
echo "1. Update the repository URL in this script"
echo "2. Create a GitHub repository if not exists"
echo "3. Share the skill with the Odoo community"
echo "4. Add to Claude Code Skills Marketplace"