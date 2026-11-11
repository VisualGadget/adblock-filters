#!/usr/bin/env bash
# Sign the Firefox extension on addons.mozilla.org as unlisted (self-distributed), attach the signed .xpi to a GitHub
# release and add it to extension/updates.json, so installed copies update themselves.
# Needs AMO API credentials (https://addons.mozilla.org/developers/addon/api/key/) in WEB_EXT_API_KEY and
# WEB_EXT_API_SECRET, or in ~/.config/secrets/tokens.yaml as amo.api_key (JWT issuer) and amo.api_secret (JWT secret), and the gh CLI
# logged in. Bump "version" in extension/manifest.json first.
set -euo pipefail

read_token() {
  python3 -c 'import sys, yaml; print(yaml.safe_load(open(sys.argv[1]))["amo"][sys.argv[2]])' \
    "$HOME/.config/secrets/tokens.yaml" "$1"
}

if [[ -z "${WEB_EXT_API_KEY:-}" || -z "${WEB_EXT_API_SECRET:-}" ]]; then
  WEB_EXT_API_KEY=$(read_token api_key)
  WEB_EXT_API_SECRET=$(read_token api_secret)
  export WEB_EXT_API_KEY WEB_EXT_API_SECRET
fi

root=$(cd "$(dirname "$0")/.." && pwd)
ext="$root/extension"
version=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["version"])' "$ext/manifest.json")
addon_id=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["browser_specific_settings"]["gecko"]["id"])' \
  "$ext/manifest.json")
tag="extension-v$version"
xpi_name="site-fixes-$version.xpi"
repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner)

if gh release view "$tag" >/dev/null 2>&1; then
  echo "Release $tag already exists, bump the version in extension/manifest.json" >&2
  exit 1
fi

out=$(mktemp -d)
trap 'rm -rf "$out"' EXIT
npx --yes web-ext lint --self-hosted --source-dir "$ext" --ignore-files updates.json .amo-upload-uuid
npx --yes web-ext sign --channel unlisted --source-dir "$ext" --ignore-files updates.json .amo-upload-uuid --artifacts-dir "$out"
signed=$(find "$out" -name '*.xpi' -print -quit)
mv "$signed" "$out/$xpi_name"

gh release create "$tag" "$out/$xpi_name" --title "Extension $version" --notes "Signed Firefox extension $version"

python3 - "$ext/updates.json" "$addon_id" "$version" \
  "https://github.com/$repo/releases/download/$tag/$xpi_name" <<'PY'
import json
import sys
from pathlib import Path

path, addon_id, version, link = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
data = json.loads(path.read_text())
data['addons'][addon_id]['updates'].append({'version': version, 'update_link': link})
path.write_text(json.dumps(data, indent=2) + '\n')
PY
echo "Released $tag. Commit and push extension/updates.json so installed copies pick it up."
