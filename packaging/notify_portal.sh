#!/bin/sh
# Asks the app portal (Gshoe2006/Apps) to rebuild now, so a new release shows there straight away.
# Run by notify-portal.yml and release.yml, with the token in PORTAL_TOKEN.
#
#   sh packaging/notify_portal.sh           exit 1 if GitHub refuses
#   sh packaging/notify_portal.sh --warn    only warn if GitHub refuses (the release is already out)
#
# The token is a fine-grained personal access token with access to Gshoe2006/Apps and
# "Contents: Read and write". If GitHub refuses it, this prints GitHub's own reason and the
# permission GitHub says it needs.
set -u
PORTAL_REPO="Gshoe2006/Apps"
API="${PORTAL_API:-https://api.github.com}"   # overridable for testing
LEVEL=error
[ "${1:-}" = "--warn" ] && LEVEL=warning

if [ -z "${PORTAL_TOKEN:-}" ]; then
  echo "::notice::PORTAL_TOKEN isn't set, so the portal will show new releases on its next scheduled run (every 3 hours)."
  exit 0
fi

BODY=$(mktemp)
HEADERS=$(mktemp)
trap 'rm -f "$BODY" "$HEADERS"' EXIT
CODE=$(curl -sS -o "$BODY" -D "$HEADERS" -w '%{http_code}' -X POST \
  -H "Authorization: Bearer $PORTAL_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "$API/repos/$PORTAL_REPO/dispatches" \
  -d '{"event_type":"app-released"}') || CODE="no response"

if [ "$CODE" = 204 ]; then
  echo "Portal rebuild requested: https://github.com/$PORTAL_REPO/actions"
  exit 0
fi

MESSAGE=$(python3 -c 'import json,sys
try: print(json.load(open(sys.argv[1])).get("message", ""))
except Exception: print(open(sys.argv[1]).read()[:300])' "$BODY" 2>/dev/null)
NEEDS=$(grep -i '^x-accepted-github-permissions:' "$HEADERS" | cut -d: -f2- | tr -d '\r' | sed 's/^ *//')
echo "::$LEVEL::GitHub refused the portal refresh (HTTP $CODE): ${MESSAGE:-no message}"
[ -n "$NEEDS" ] && echo "GitHub says this needs a token with: $NEEDS (on $PORTAL_REPO)"
case "$CODE" in
  401) echo "The token in PORTAL_TOKEN is wrong, expired or revoked. Make a new one and update the secret." ;;
  403) echo "The token works but can't do this. In its settings, Repository access must include $PORTAL_REPO and Contents must be 'Read and write'." ;;
  404) echo "The token can't see $PORTAL_REPO. In its settings, add $PORTAL_REPO under Repository access." ;;
esac
[ "$LEVEL" = warning ] && echo "The release is published either way; the portal shows it on its next scheduled run."
[ "$LEVEL" = warning ] && exit 0
exit 1
