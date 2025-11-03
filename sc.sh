#!/usr/bin/env bash
  set -euo pipefail

  # >>> customise these <<<
  BRANCH_NAME="release/v1.2.0"
  TAG_NAME="v1.2.0"
  COMMIT_MSG="feat: prepare v1.2.0 release"
  ROOT="$(git rev-parse --show-toplevel)"
  cd "$ROOT"

  git submodule update --init --recursive

  mapfile -t REPOS < <(
    printf '.\n'
    git config --file .gitmodules --get-regexp path | awk '{print $2}'
  )

  for repo in "${REPOS[@]}"; do
    cd "$ROOT/$repo"
    echo "---- processing ${repo:-root} ----"

    git fetch origin
    git checkout main
    git pull --ff-only origin main
    git checkout -B "$BRANCH_NAME"

    if ! git diff --quiet; then
      git add -A
      git commit -m "$COMMIT_MSG"
    else
      echo "No changes to commit in ${repo:-root}"
    fi

    if ! git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
      git tag -a "$TAG_NAME" -m "$TAG_NAME"
    else
      echo "Tag $TAG_NAME already exists in ${repo:-root}; skipping tag
  creation"
    fi

    git push origin "$BRANCH_NAME"
    git push origin "$TAG_NAME" || true
  done

  echo "All repos processed."

