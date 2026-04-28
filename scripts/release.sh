#!/bin/bash
#
# release.sh - Create a new HyperTrader Manager release
#
# Updates api/pyproject.toml and web/package.json to the given version,
# commits the changes, creates an annotated git tag (vX.Y.Z), and pushes
# both the commit and tag to origin.
#
# Releases are restricted to the main branch from a clean working state.
#
# Usage:
#   ./scripts/release.sh 1.2.3
#   ./scripts/release.sh 1.0.0rc1 -m "First release candidate"
#   ./scripts/release.sh 2.0.0 --dry-run
#   ./scripts/release.sh --help
#

set -e

# ─── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ─── Usage ───────────────────────────────────────────────────────────────────
usage() {
  cat <<EOF
Create a new HyperTrader Manager release

Usage: $0 <version> [options]

Arguments:
  version           Version string (e.g., 1.2.3, 1.0.0a1, 1.0.0rc1)
                    Format: X.Y.Z or X.Y.Z(a|b|rc)N  (PEP 440 compatible)

Options:
  -m, --message     Inline release notes for the tag annotation
  -f, --file        Read release notes from a file
  --dry-run         Show what would be done without making any changes
  --force           Overwrite an existing tag (use with caution)
  -h, --help        Show this help message

Examples:
  $0 1.0.0
  $0 1.2.3 -m "Bug fixes and performance improvements"
  $0 2.0.0 -f CHANGELOG.md
  echo "Release notes" | $0 1.0.1
  $0 1.0.0rc1 --dry-run

The script will:
  1. Validate version format (PEP 440 compatible)
  2. Verify you are on main branch with a clean working tree
  3. Update api/pyproject.toml and web/package.json
  4. Commit and push the version bump
  5. Create annotated tag vX.Y.Z and push it
EOF
}

# ─── Argument Parsing ────────────────────────────────────────────────────────
VERSION=""
DRY_RUN=false
FORCE=false
CHANGELOG_MESSAGE=""
CHANGELOG_FILE=""

while [[ $# -gt 0 ]]; do
  case $1 in
  -h | --help)
    usage
    exit 0
    ;;
  --dry-run)
    DRY_RUN=true
    shift
    ;;
  --force)
    FORCE=true
    shift
    ;;
  -m | --message)
    CHANGELOG_MESSAGE="$2"
    shift 2
    ;;
  -f | --file)
    CHANGELOG_FILE="$2"
    shift 2
    ;;
  -*)
    echo -e "${RED}Error: Unknown option: $1${NC}" >&2
    usage
    exit 1
    ;;
  *)
    VERSION="$1"
    shift
    ;;
  esac
done

# ─── Validation ──────────────────────────────────────────────────────────────

# Version required
if [[ -z "$VERSION" ]]; then
  echo -e "${RED}Error: Version argument required${NC}" >&2
  usage
  exit 1
fi

# Version format: X.Y.Z or X.Y.Z(a|b|rc)N  (PEP 440 compatible)
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+((a|b|rc)[0-9]+)?$ ]]; then
  echo -e "${RED}Error: Invalid version format: ${VERSION}${NC}" >&2
  echo "Expected: X.Y.Z  or  X.Y.Z(a|b|rc)N" >&2
  echo "Examples: 1.0.0  1.2.3  1.0.0a1  2.0.0b2  1.0.0rc1" >&2
  exit 1
fi

TAG="v${VERSION}"

# ─── Pre-flight Checks ───────────────────────────────────────────────────────

# Must be inside a git repository
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo -e "${RED}Error: Not in a git repository${NC}" >&2
  exit 1
fi

# Resolve git root so all paths are absolute
GIT_ROOT=$(git rev-parse --show-toplevel)

# Must be on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" != "main" ]]; then
  echo -e "${RED}Error: Releases must be created from the 'main' branch${NC}" >&2
  echo -e "${RED}Current branch: ${CURRENT_BRANCH}${NC}" >&2
  exit 1
fi

# Working tree must be clean
if [[ -n $(git status --porcelain) ]]; then
  echo -e "${RED}Error: You have uncommitted changes:${NC}" >&2
  git status --short >&2
  echo "" >&2
  echo "Please commit or stash your changes before creating a release." >&2
  exit 1
fi

# Tag must not already exist (unless --force)
if git rev-parse "$TAG" >/dev/null 2>&1; then
  if [[ "$FORCE" == false ]]; then
    echo -e "${RED}Error: Tag ${TAG} already exists${NC}" >&2
    echo "Use --force to overwrite (this re-tags the same or a different commit)." >&2
    exit 1
  else
    echo -e "${YELLOW}Warning: Tag ${TAG} exists and will be overwritten${NC}"
  fi
fi

# ─── Header ──────────────────────────────────────────────────────────────────
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  HyperTrader Manager Release${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Version : ${VERSION}"
echo "Tag     : ${TAG}"
echo ""

# Show recent commits for context
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
if [[ -n "$LAST_TAG" ]]; then
  echo -e "${BLUE}Changes since ${LAST_TAG}:${NC}"
  echo ""
  git log --oneline --graph --decorate "${LAST_TAG}..HEAD"
  echo ""
else
  echo -e "${BLUE}First release — all commits:${NC}"
  echo ""
  git log --oneline --graph --decorate
  echo ""
fi

# ─── Changelog ───────────────────────────────────────────────────────────────
CHANGELOG=""

if [[ -n "$CHANGELOG_MESSAGE" ]]; then
  CHANGELOG="$CHANGELOG_MESSAGE"
  echo -e "${BLUE}Changelog: from --message flag${NC}"
elif [[ -n "$CHANGELOG_FILE" ]]; then
  if [[ ! -f "$CHANGELOG_FILE" ]]; then
    echo -e "${RED}Error: Changelog file not found: ${CHANGELOG_FILE}${NC}" >&2
    exit 1
  fi
  CHANGELOG=$(cat "$CHANGELOG_FILE")
  echo -e "${BLUE}Changelog: from file ${CHANGELOG_FILE}${NC}"
elif [[ ! -t 0 ]]; then
  CHANGELOG=$(cat)
  echo -e "${BLUE}Changelog: from stdin${NC}"
fi

if [[ -z "$CHANGELOG" ]]; then
  echo -e "${YELLOW}No changelog provided — using default message.${NC}"
  CHANGELOG="Release ${VERSION}"
fi

TAG_MESSAGE="Release ${VERSION}

${CHANGELOG}"

echo ""
echo -e "${BLUE}Tag message:${NC}"
echo "---"
echo "$TAG_MESSAGE"
echo "---"
echo ""

# ─── Dry Run ─────────────────────────────────────────────────────────────────
if [[ "$DRY_RUN" == true ]]; then
  echo -e "${YELLOW}DRY RUN — no changes will be made${NC}"
  echo ""
  echo "Would execute:"
  echo "  sed: update version in api/pyproject.toml            →  ${VERSION}"
  echo "  sed: update version in web/package.json              →  ${VERSION}"
  echo "  sed: stamp PINNED_VERSION in scripts/install.sh      →  ${TAG}"
  echo "  git add api/pyproject.toml web/package.json scripts/install.sh"
  echo "  git commit -m \"chore: bump version to ${VERSION}\""
  echo "  git push origin main"
  echo "  git tag -a ${TAG} -m \"<tag message above>\""
  echo "  git push origin ${TAG}"
  echo "  sed: reset PINNED_VERSION in scripts/install.sh      →  (empty)"
  echo "  git add scripts/install.sh"
  echo "  git commit -m \"chore: reset install.sh after ${TAG} release\""
  echo "  git push origin main"
  echo ""
  echo -e "${GREEN}Dry run complete. Remove --dry-run to create the release.${NC}"
  exit 0
fi

# ─── Version Bump ────────────────────────────────────────────────────────────
echo -e "${BLUE}Updating version files...${NC}"

# api/pyproject.toml — scope sed to [project] section only
PYPROJECT="${GIT_ROOT}/api/pyproject.toml"
if [[ ! -f "$PYPROJECT" ]]; then
  echo -e "${RED}Error: api/pyproject.toml not found at ${PYPROJECT}${NC}" >&2
  exit 1
fi
sed -i "/^\[project\]/,/^\[/ s/^version = \".*\"/version = \"${VERSION}\"/" "$PYPROJECT"
echo -e "${GREEN}✓ api/pyproject.toml → ${VERSION}${NC}"

# web/package.json — single "version" key at top level
PACKAGE_JSON="${GIT_ROOT}/web/package.json"
if [[ ! -f "$PACKAGE_JSON" ]]; then
  echo -e "${RED}Error: web/package.json not found at ${PACKAGE_JSON}${NC}" >&2
  exit 1
fi
sed -i "s/\"version\": \".*\"/\"version\": \"${VERSION}\"/" "$PACKAGE_JSON"
echo -e "${GREEN}✓ web/package.json → ${VERSION}${NC}"

# scripts/install.sh — stamp PINNED_VERSION with the release tag
INSTALL_SH="${GIT_ROOT}/scripts/install.sh"
if [[ ! -f "$INSTALL_SH" ]]; then
  echo -e "${RED}Error: scripts/install.sh not found at ${INSTALL_SH}${NC}" >&2
  exit 1
fi
sed -i "s/^PINNED_VERSION=\".*\"/PINNED_VERSION=\"${TAG}\"/" "$INSTALL_SH"
echo -e "${GREEN}✓ scripts/install.sh → PINNED_VERSION=\"${TAG}\"${NC}"

# ─── Commit ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}Committing version bump...${NC}"

cd "$GIT_ROOT"

git add api/pyproject.toml web/package.json scripts/install.sh

if git diff --cached --quiet; then
  echo -e "${YELLOW}No changes to commit (version may already be set to ${VERSION})${NC}"
else
  git commit -m "chore: bump version to ${VERSION}"
  echo -e "${GREEN}✓ Version bump committed${NC}"
fi

# ─── Push Commit ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}Pushing commit to origin...${NC}"
git push origin main
echo -e "${GREEN}✓ Commit pushed${NC}"

# ─── Tag ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}Creating tag ${TAG}...${NC}"
if [[ "$FORCE" == true ]]; then
  git tag -f -a "$TAG" -m "$TAG_MESSAGE"
else
  git tag -a "$TAG" -m "$TAG_MESSAGE"
fi
echo -e "${GREEN}✓ Tag ${TAG} created${NC}"

# ─── Push Tag ────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}Pushing tag to origin...${NC}"
if [[ "$FORCE" == true ]]; then
  git push -f origin "$TAG"
else
  git push origin "$TAG"
fi
echo -e "${GREEN}✓ Tag pushed${NC}"

# ─── Reset install.sh PINNED_VERSION on main ─────────────────────────────────
echo ""
echo -e "${BLUE}Resetting PINNED_VERSION in scripts/install.sh on main...${NC}"
sed -i 's/^PINNED_VERSION="[^"]*"/PINNED_VERSION=""/' "$INSTALL_SH"
git add scripts/install.sh
if git diff --cached --quiet; then
  echo -e "${YELLOW}No reset needed (PINNED_VERSION already empty)${NC}"
else
  git commit -m "chore: reset install.sh after ${TAG} release"
  git push origin main
  echo -e "${GREEN}✓ PINNED_VERSION reset and pushed${NC}"
fi

# ─── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}  Release Created Successfully!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Version : ${VERSION}"
echo "Tag     : ${TAG}"
echo ""
echo "What was done:"
echo "  ✓ Updated api/pyproject.toml to ${VERSION}"
echo "  ✓ Updated web/package.json to ${VERSION}"
echo "  ✓ Stamped scripts/install.sh with PINNED_VERSION=${TAG}"
echo "  ✓ Committed and pushed version bump"
echo "  ✓ Created and pushed tag ${TAG}"
echo "  ✓ Reset scripts/install.sh PINNED_VERSION on main"
echo ""
