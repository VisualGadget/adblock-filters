#!/usr/bin/env bash
# Check pages for ads that pass through the filter lists. When some are found, let Claude Code update the lists,
# check again and push the change only when no ads are left.
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
reports="$HOME/.local/state/adblock-check/reports"
report="$reports/$(date +%Y%m%d-%H%M%S)"
checker="$repo/tools/check_ads.py"

cd "$repo"
git pull --quiet --ff-only

status=0
"$checker" --output "$report" || status=$?

if [[ ! -f "$report/summary.json" ]]; then
    echo "Checker failed without a report." >&2
    exit 2
fi

if [[ $status -eq 3 ]]; then
    python3 -c 'import json, sys
for p in json.load(open(sys.argv[1]))["pages"]:
    if not p["logged_in"]:
        print("Not logged in:", p["url"], "-", "; ".join(p["logged_out_reasons"]))' "$report/summary.json" >&2
    echo "Log in again with: $checker --login" >&2
    exit 3
fi

if [[ $status -eq 0 ]]; then
    echo "No ads found."
    exit 0
fi

prompt="$(sed "s|{report}|$report|g" "$repo/tools/fix_prompt.md")"
claude -p "$prompt" \
    --permission-mode acceptEdits \
    --add-dir "$report" \
    --allowedTools Read Edit Write "Bash(./tools/check_ads.py:*)" "Bash($checker:*)" \
    | tee "$report/fix.log"

if git status --porcelain --untracked-files=all | cut -c4- | grep -qvE '^([^/]+\.txt|README\.md)$'; then
    echo "Unexpected changes outside the filter lists; nothing pushed." >&2
    git status --short >&2
    exit 2
fi

if [[ -z "$(git status --porcelain)" ]]; then
    echo "No filter changes made." >&2
    exit 2
fi

if ! "$checker" --output "$report/final"; then
    echo "Ads still visible after the update; nothing pushed. Changes left in $repo." >&2
    exit 1
fi

hosts="$(python3 -c 'import json, sys, urllib.parse
pages = json.load(open(sys.argv[1]))["pages"]
print(" ".join(sorted({urllib.parse.urlsplit(p["url"]).hostname for p in pages if p["ads"]})))' "$report/summary.json")"
git add -A
git commit --quiet -m "Hide ads that got through on $hosts"
git push --quiet
echo "Pushed: $(git log --oneline -1)"
