#!/usr/bin/env bash
# Publish one rendered video on the orphan branch "media" (only the latest video is kept,
# so the repository does not grow every day). Prints the public raw URL for Metricool.
# Usage: ./publish_video.sh videos/2026-11-10-something.mp4
set -euo pipefail
VIDEO="$1"; NAME="$(basename "$VIDEO")"
REPO_URL="$(git -C "$(dirname "$0")" remote get-url origin)"
TMP="$(mktemp -d)"
cp "$VIDEO" "$TMP/$NAME"
cd "$TMP"
git init -q -b media
git add "$NAME"
git -c user.name="youtube-shorts-bot" -c user.email="bot@users.noreply.github.com" commit -q -m "Media: $NAME"
git push -q -f "$REPO_URL" media:media
echo "https://raw.githubusercontent.com/Handstand9626/youtube-shorts/media/$NAME"
