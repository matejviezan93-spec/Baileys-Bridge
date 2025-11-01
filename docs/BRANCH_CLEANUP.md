# Branch Cleanup Guide

This document explains how to delete all branches in the repository except `main`.

## Current Branch Status

As of this documentation, the repository has multiple branches:
- `main` (protected - will NOT be deleted)
- Various `codex/*` branches
- Various `copilot/*` branches

## Automated Cleanup Methods

### Method 1: GitHub Actions Workflow (Recommended)

A GitHub Actions workflow has been created to automate branch cleanup.

**To trigger the workflow manually:**

1. Go to the repository on GitHub
2. Navigate to **Actions** tab
3. Select **Cleanup Branches** workflow from the left sidebar
4. Click **Run workflow** button
5. Confirm and run

The workflow can also run automatically on a schedule (weekly on Sundays at midnight UTC).

**Workflow file location:** `.github/workflows/cleanup-branches.yml`

### Method 2: Using the Cleanup Script

A shell script is provided for manual branch deletion.

**Dry run (preview only):**
```bash
./scripts/cleanup-branches.sh --dry-run
```

**Actual deletion:**
```bash
./scripts/cleanup-branches.sh
```

The script will:
1. Fetch all remote branches
2. Display a list of branches to be deleted
3. Ask for confirmation
4. Delete each branch (except `main`)
5. Show a summary of results

## Manual Cleanup Methods

### Method 3: Using Git Commands

**List all branches (except main):**
```bash
git branch -r | grep -v 'HEAD' | grep -v 'main'
```

**Delete a specific branch:**
```bash
git push origin --delete <branch-name>
```

**Delete multiple branches at once:**
```bash
# Get all branch names except main
branches=$(git branch -r | grep -v 'HEAD' | grep -v 'main' | sed 's/origin\///')

# Delete each branch
for branch in $branches; do
  git push origin --delete "$branch"
done
```

### Method 4: Using GitHub Web Interface

For each branch you want to delete:
1. Go to the repository on GitHub
2. Click on the **branches** link (shows "X branches")
3. Find the branch you want to delete
4. Click the trash icon next to the branch name
5. Confirm deletion

## Important Notes

- The `main` branch is protected and will never be deleted by these methods
- You need appropriate permissions (write access) to delete branches
- Deleted branches cannot be easily recovered (though commits remain in the reflog for a period)
- Always verify you're deleting the correct branches before confirming

## Branch Protection

To prevent unwanted branches from being created in the future, consider:
1. Setting up branch protection rules in GitHub
2. Using a naming convention for temporary branches
3. Regularly running the cleanup workflow

## Troubleshooting

**"Permission denied" errors:**
- Ensure you have write access to the repository
- Check if the branch has protection rules enabled

**Workflow not appearing:**
- The workflow file must be in the `main` branch to be visible in Actions
- Check the workflow syntax is correct

**Script fails to delete branches:**
- Ensure you're authenticated with GitHub (credentials configured)
- Check your Git remote is correctly configured: `git remote -v`
