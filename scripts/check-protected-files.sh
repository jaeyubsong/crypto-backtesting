#!/bin/bash
# Pre-commit hook to prevent modification of protected GitHub workflow files

if git diff --cached --name-only | grep -E "^\.github/workflows/(claude\.yml|claude-code-review\.yml)$"; then
    echo "❌ ERROR: GitHub workflow files must not be modified!"
    echo ""
    echo "The following files are PROTECTED and cannot be changed:"
    echo "  - .github/workflows/claude.yml"
    echo "  - .github/workflows/claude-code-review.yml"
    echo ""
    echo "These files are managed externally and contain specific formatting."
    echo ""
    echo "To unstage these files, run:"
    echo "  git reset HEAD .github/workflows/claude.yml .github/workflows/claude-code-review.yml"
    echo ""
    exit 1
fi

exit 0
