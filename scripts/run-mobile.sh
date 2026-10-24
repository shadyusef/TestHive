#!/usr/bin/env bash
# Runs a module's Maestro flows on a device and stores the run.
# Usage: bash scripts/run-mobile.sh <module> [device-id] [--tag smoke|sanity|regression|e2e] [--target <name>] [--app <apk or ipa>]
#   (reads .env and .env.<TEST_ENV>; the .env values are passed to the flows, except the BrowserStack keys)
#   --target      a target from targets.json: a local Android device, or a BrowserStack device (bs-pixel7, bs-iphone15, ...)
#   --app         the app to upload to BrowserStack (default APP_FILE, or IOS_APP_FILE for iOS, from .env)
#   PLATFORM=ios             use IOS_APP_ID / IOS_DEVICE_ID instead of APP_ID / ANDROID_DEVICE_ID
#   INCLUDE_TAGS=smoke       run only flows with these tags
#   EXCLUDE_TAGS=known-bug   skip flows with these tags (local runs)
# BrowserStack: needs BROWSERSTACK_USERNAME and BROWSERSTACK_ACCESS_KEY in .env (scripts/lib/browserstack.py).
# Then stores the run in runs/ (scripts/collect-run.sh) with its target. NO_COLLECT=1 skips that.
set -e
. "$(dirname "$0")/_env.sh"
. "$(dirname "$0")/_py.sh"
MOD="${1:?module}"; shift; DEV=""; TARGET=""; APPF=""
while [ $# -gt 0 ]; do
  case "$1" in --tag) INCLUDE_TAGS="${2:?tag}"; shift 2;; --target) TARGET="${2:?target}"; shift 2;; --app) APPF="${2:?app file}"; shift 2;;
    -*) echo "Unknown option: $1" >&2; exit 2;; *) DEV="$1"; shift;; esac
done
INCLUDE_TAGS="${INCLUDE_TAGS:-$TH_TAG}"
if [ -n "$TARGET" ]; then T=$($PY "$(dirname "$0")/lib/targets.py" shell "$TARGET" mobile) || exit 2; eval "$T"; fi
[ "$TH_TARGET_WHERE" != browserstack ] || [ -n "$BROWSERSTACK_USERNAME" -a -n "$BROWSERSTACK_ACCESS_KEY" ] || { echo "Add BROWSERSTACK_USERNAME and BROWSERSTACK_ACCESS_KEY to .env (you, in the file)."; exit 2; }
if [ "$PLATFORM" = ios ]; then APP_ID="${IOS_APP_ID:-$APP_ID}"; DEV="${DEV:-$IOS_DEVICE_ID}"; APPF="${APPF:-$IOS_APP_FILE}"; else DEV="${DEV:-$ANDROID_DEVICE_ID}"; APPF="${APPF:-$APP_FILE}"; fi
mkdir -p reports; rm -rf reports/mobile-"$MOD".xml reports/mobile-"$MOD"-evidence
set +e
EV=()
if [ "$TH_TARGET_WHERE" = browserstack ]; then  # the keys go to browserstack.py's environment only, never on a command line
  BROWSERSTACK_USERNAME="$BROWSERSTACK_USERNAME" BROWSERSTACK_ACCESS_KEY="$BROWSERSTACK_ACCESS_KEY" APP_ID="$APP_ID" \
    $PY "$(dirname "$0")/lib/browserstack.py" "$MOD" "$APPF" reports/mobile-"$MOD".xml reports/mobile-"$MOD"-evidence "$INCLUDE_TAGS"; RC=$?
  [ -d reports/mobile-"$MOD"-evidence ] && EV=(--evidence reports/mobile-"$MOD"-evidence)
else
  ENVS=(-e "APP_ID=$APP_ID")
  if [ -f .env ]; then
    for k in $(tr -d '\r' < .env | sed -n 's/^\([A-Za-z_][A-Za-z0-9_]*\)=.*/\1/p'); do case "$k" in APP_ID|BROWSERSTACK_*) ;; *) ENVS+=(-e "$k=${!k}");; esac; done
  fi
  maestro ${DEV:+--device "$DEV"} test "${ENVS[@]}" ${INCLUDE_TAGS:+--include-tags "$INCLUDE_TAGS"} ${EXCLUDE_TAGS:+--exclude-tags "$EXCLUDE_TAGS"} \
    --format junit --output reports/mobile-"$MOD".xml mobile/flows/"$MOD"; RC=$?
fi
[ -n "$NO_COLLECT" ] || [ ! -f reports/mobile-"$MOD".xml ] || bash "$(dirname "$0")/collect-run.sh" mobile "$MOD" --env "${TEST_ENV:-}" --platform "${PLATFORM:-android}" \
  ${TH_TARGET:+--target "$TH_TARGET"} "${EV[@]}"
exit $RC
