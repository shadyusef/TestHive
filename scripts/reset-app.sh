#!/usr/bin/env bash
# Usage: bash scripts/reset-app.sh android <package> [device-id]
#        bash scripts/reset-app.sh ios <bundle-id>
set -e
P="${1:?platform android|ios}"; ID="${2:?app id}"; DEV="${3:-}"
if [ "$P" = "android" ]; then
  adb ${DEV:+-s $DEV} shell pm clear "$ID"
else
  xcrun simctl uninstall booted "$ID" || true
fi
