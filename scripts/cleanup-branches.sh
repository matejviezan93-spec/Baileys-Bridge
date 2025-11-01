#!/bin/bash

# Script to delete all branches except main
# Usage: ./scripts/cleanup-branches.sh [--dry-run]

set -e

DRY_RUN=false

# Parse arguments
if [ "$1" == "--dry-run" ]; then
    DRY_RUN=true
    echo "Running in DRY RUN mode - no branches will be deleted"
fi

# Ensure we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: Not in a git repository"
    exit 1
fi

# Get all remote branches using ls-remote
echo "Fetching all remote branches..."
branches=$(git ls-remote --heads origin | awk '{print $2}' | sed 's|refs/heads/||' | grep -v '^main$' || true)

if [ -z "$branches" ]; then
    echo "No branches to delete. Only main branch exists."
    exit 0
fi

echo ""
echo "The following branches will be deleted:"
echo "========================================"
echo "$branches"
echo "========================================"
echo ""

# Count branches
if [ -n "$branches" ]; then
    branch_count=$(echo "$branches" | wc -l)
else
    branch_count=0
fi
echo "Total branches to delete: $branch_count"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "DRY RUN: No branches were deleted"
    exit 0
fi

# Ask for confirmation
read -p "Are you sure you want to delete these branches? (yes/no): " confirmation

if [ "$confirmation" != "yes" ]; then
    echo "Operation cancelled"
    exit 0
fi

# Delete each branch
success_count=0
fail_count=0

for branch in $branches; do
    echo "Deleting branch: $branch"
    if git push origin --delete "$branch" 2>/dev/null; then
        echo "✓ Successfully deleted: $branch"
        ((success_count++))
    else
        echo "✗ Failed to delete: $branch"
        ((fail_count++))
    fi
done

echo ""
echo "========================================"
echo "Branch cleanup summary:"
echo "  Successfully deleted: $success_count"
echo "  Failed to delete: $fail_count"
echo "========================================"

if [ $fail_count -eq 0 ]; then
    echo "All branches deleted successfully!"
else
    echo "Some branches could not be deleted. Check the output above for details."
    exit 1
fi
