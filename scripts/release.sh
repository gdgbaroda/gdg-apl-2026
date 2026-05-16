#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:?Usage: $0 <version>  e.g. 0.1.1}"
VERSION="${VERSION#v}"
TAG="v$VERSION"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Working tree not clean. Commit or stash first." >&2
  exit 1
fi

if [[ -z "${APL_HOST_SECRET:-}" ]]; then
  echo "APL_HOST_SECRET must be exported before releasing (baked into build)." >&2
  exit 1
fi

if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "Tag $TAG already exists." >&2
  exit 1
fi

echo "→ Bumping version to $VERSION"
npm version "$VERSION" -m "Release %s" >/dev/null

echo "→ Building mac (arm64) DMG"
rm -rf release
npm run dist:dmg

echo "→ Building windows (x64) zip"
npm run dist:win

echo "→ Building linux (x64) AppImage + deb"
npm run dist:linux

echo "→ Pushing commit + tag"
git push --follow-tags origin main

echo "→ Creating GitHub release"
gh release create "$TAG" \
  "release/APL Host-${VERSION}-arm64.dmg" \
  "release/APL Host-${VERSION}-win.zip" \
  "release/APL Host-${VERSION}.AppImage" \
  "release/apl-host_${VERSION}_amd64.deb" \
  "release/latest-linux.yml" \
  --title "$TAG" \
  --generate-notes

URL=$(gh release view "$TAG" --json url -q .url)
echo "✓ Released $TAG"
echo "  $URL"
