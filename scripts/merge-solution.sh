#!/bin/bash
# Merge a completed problem solution back — squash-merge only
# Usage: bash scripts/merge-solution.sh <problem-uuid> <target-branch>
set -euo pipefail

PROBLEM_UUID="${1:?Usage: merge-solution.sh <uuid> <target>}"
TARGET_BRANCH="${2:-acorn/kernels}"
PROBLEM_BRANCH="acorn/problem-${PROBLEM_UUID}"

git fetch origin "$PROBLEM_BRANCH"
git checkout "$TARGET_BRANCH"
git merge --squash "origin/$PROBLEM_BRANCH"
git commit -m "feat(kernels): merge problem-${PROBLEM_UUID} solution

Squash-merge from ${PROBLEM_BRANCH}"

echo "[merge] Merged $PROBLEM_BRANCH → $TARGET_BRANCH"
