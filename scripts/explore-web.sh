#!/usr/bin/env bash
# Explores a web app (URL or local file) and records pages, fields, rules and messages as observed behaviour.
# Usage: bash scripts/explore-web.sh <MODULE> <url> [--max-pages N] [--submit-valid]
#   Writes analysis/exploration/<MODULE>/web/exploration.md (+ .json and screenshots) for the business analyst.
#   Forms are submitted empty and with invalid values; --submit-valid also submits valid values (creates data: test
#   environments only). Uses Microsoft Edge on Windows, Chromium elsewhere (TH_BROWSER_CHANNEL overrides).
# Behind a login? Put a test account in .env (TEST_USER, TEST_USER_PASSWORD): it logs in after recording the login page.
# Needs the web tools once: setup --install --web (Playwright library only; no browser download with Edge).
MOD="${1:?Usage: explore-web.sh <MODULE> <url> [--max-pages N] [--submit-valid]}"; URL="${2:?url}"; shift 2
cd "$(dirname "$0")/.." || exit 1
[ -d web/node_modules/@playwright/test ] || { echo "Web tools missing. Run: ${TH_CMD:-bash scripts/hive.sh} setup --install --web"; exit 1; }
case "$URL" in http*|file:*) ;; *) [ -f "$URL" ] && URL="file:///$(cd "$(dirname "$URL")" && pwd -W 2>/dev/null || pwd)/$(basename "$URL")" ;; esac
OUT="analysis/exploration/$(echo "$MOD" | tr '[:lower:]' '[:upper:]')/web"
# A test login from .env, when the product needs one: only these two values reach the explorer, and it never writes them down.
envval() {  # KEY=value or export KEY=value; quotes around the value are dropped
  [ -f .env ] || return; local v; v=$(tr -d '\r' < .env | sed -n "s/^\(export \)\{0,1\}$1=//p" | tail -1)
  v="${v#\"}"; v="${v%\"}"; v="${v#\'}"; v="${v%\'}"; printf '%s' "$v"
}
TH_LOGIN_USER="$(envval TEST_USER)"; TH_LOGIN_PASSWORD="$(envval TEST_USER_PASSWORD)"
[ "$TH_LOGIN_PASSWORD" = change-me ] && TH_LOGIN_PASSWORD=""  # the template's placeholder
export TH_LOGIN_USER TH_LOGIN_PASSWORD
node web/explore.mjs "$URL" "$OUT" "$@"
