---
description: Create patch/minor/major release via scripts/release.sh
---

Bump type: $ARGUMENTS  (patch | minor | major)

Current version:
!`grep '^version' api/pyproject.toml | head -1`

Last tag:
!`git describe --tags --abbrev=0 2>/dev/null || echo "none"`

Changes since last tag:
!`git log --oneline $(git describe --tags --abbrev=0 2>/dev/null)..HEAD`

Instructions:
1. Compute the new version by bumping $ARGUMENTS on the current version above.
2. Load the caveman-commit skill. Write a caveman-style changelog summarizing the changes above. Terse, no articles, fragments OK.
3. Run: `bash scripts/release.sh <new-version> -m "<caveman changelog>"`
4. Use scripts/release.sh ONLY. Never manually bump files or create tags.
