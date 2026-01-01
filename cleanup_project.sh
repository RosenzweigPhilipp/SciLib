#!/bin/bash
# SciLib Project Cleanup Script
# Removes unnecessary files, cache, and temporary data

set -e  # Exit on error

echo "🧹 Starting SciLib project cleanup..."

# 1. Remove Python cache files
echo "📦 Removing Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type f -name "*.pyd" -delete 2>/dev/null || true
echo "✓ Python cache cleaned"

# 2. Remove .DS_Store files (macOS)
echo "🍎 Removing .DS_Store files..."
find . -name ".DS_Store" -delete 2>/dev/null || true
echo "✓ .DS_Store files removed"

# 3. Clean Redis dump (optional - asks first)
if [ -f "dump.rdb" ]; then
    echo "📊 Redis dump file found (88K)"
    read -p "Remove Redis dump file? This will clear background task data. (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -f dump.rdb
        echo "✓ Redis dump removed"
    else
        echo "⊘ Keeping Redis dump"
    fi
fi

# 4. Clean log files (optional)
if [ -d "logs" ] && [ "$(ls -A logs)" ]; then
    echo "📝 Log files found"
    read -p "Clear log files? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf logs/*
        echo "✓ Logs cleared"
    else
        echo "⊘ Keeping logs"
    fi
fi

# 5. Remove test uploads (optional)
if [ -d "uploads" ] && [ "$(ls -A uploads)" ]; then
    echo "📄 Upload files found"
    read -p "Clear uploads directory? This will delete all PDFs. (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf uploads/*
        echo "✓ Uploads cleared"
    else
        echo "⊘ Keeping uploads"
    fi
fi

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "To remove test/example files (minimals/), run:"
echo "  rm -rf minimals/test_*.py minimals/example_*.py"
echo ""
echo "To clean all DEBUG console.log statements from JavaScript:"
echo "  See CLEANUP_RECOMMENDATIONS.md for details"
