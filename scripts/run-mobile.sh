#!/usr/bin/env bash
# Runs a module's Maestro flows on a device and stores the run.
# Usage: bash scripts/run-mobile.sh <module> [device-id]   (reads .env; every .env variable is passed to the flows)
#   PLATFORM=ios             use IOS_APP_ID / IOS_DEVICE_ID instead of APP_ID / ANDROID_DEVICE_ID
#   INCLUDE_TAGS=smoke       run only flows with these tags
#   EXCLUDE_TAGS=known-bug   skip flows with these tags
# Then stores the run in runs/ (scripts/collect-run.sh). NO_COLLECT=1 skips that.
set -e
[ -f .env ] && { set -a; eval "$(tr -d '\r' < .env)"; set +a; }
MOD="${1:?module}"; DEV="${2:-}"
if [ "$PLATFORM" = ios ]; then APP_ID="${IOS_APP_ID:-$APP_ID}"; DEV="${DEV:-$IOS_DEVICE_ID}"; else DEV="${DEV:-$ANDROID_DEVICE_ID}"; fi
ENVS=(-e "APP_ID=$APP_ID")
if [ -f .env ]; then
  for k in $(tr -d '\r' < .env | sed -n 's/^\([A-Za-z_][A-Za-z0-9_]*\)=.*/\1/p'); do [ "$k" = APP_ID ] || ENVS+=(-e "$k=${!k}"); done
fi
mkdir -p reports; rm -f reports/mobile-"$MOD".xml
set +e
maestro ${DEV:+--device "$DEV"} test "${ENVS[@]}" ${INCLUDE_TAGS:+--include-tags "$INCLUDE_TAGS"} ${EXCLUDE_TAGS:+--exclude-tags "$EXCLUDE_TAGS"} \
  --format junit --output reports/mobile-"$MOD".xml mobile/flows/"$MOD"; RC=$?
[ -n "$NO_COLLECT" ] || [ ! -f reports/mobile-"$MOD".xml ] || bash "$(dirname "$0")/collect-run.sh" mobile "$MOD" --env "${TEST_ENV:-}" --platform "${PLATFORM:-android}"
exit $RC
