#!/usr/bin/env bash
# Explores an Android app on a connected phone or emulator, step by step, recording each screen as observed behaviour.
# Usage: bash scripts/explore-android.sh <MODULE> <command> [args]
#   install <file.apk>        install (or update) the app
#   packages                  the apps installed on the device by a person (not the system's), to find the one just installed
#   launch <package>          start the app from a clean state (clears its data first)
#   snap <name>               record the current screen: screenshot, UI dump and a summary added to exploration.md
#   tap <id|text>             tap the element with that resource id, text or description (from the last snap)
#   type <text>               type into the focused field (ASCII only: adb cannot type Arabic)
#   back                      press Back
# Output: analysis/exploration/<MODULE>/android/ (NN-name.png, NN-name.xml, exploration.md).
# The business-analyst agent drives these commands; a human can too. Device: ANDROID_DEVICE_ID or the only one connected.
. "$(dirname "$0")/_py.sh"
MOD="${1:?Usage: explore-android.sh <MODULE> install|launch|snap|tap|type|back [args]}"; CMD="${2:?command}"; shift 2
cd "$(dirname "$0")/.." || exit 1
[ -f .env ] && { set -a; eval "$(tr -d '\r' < .env)"; set +a; }
OUT="analysis/exploration/$(echo "$MOD" | tr '[:lower:]' '[:upper:]')/android"; mkdir -p "$OUT"
command -v adb >/dev/null || { echo "adb not found. Run: ${TH_CMD:-bash scripts/hive.sh} setup --install"; exit 1; }
ADB=(adb ${ANDROID_DEVICE_ID:+-s "$ANDROID_DEVICE_ID"})
[ "$("${ADB[@]}" get-state 2>/dev/null)" = device ] || { echo "No device ready. Connect a phone with USB debugging (or start an emulator), then: ${TH_CMD:-bash scripts/hive.sh} check-devices"; exit 1; }
last_xml() { ls "$OUT"/*.xml 2>/dev/null | tail -1; }
case "$CMD" in
  install) "${ADB[@]}" install -r "${1:?apk file}" ;;
  packages) "${ADB[@]}" shell pm list packages -3 | sed 's/^package://' | tr -d '\r' | sort ;;
  launch)  P="${1:?package}"; [[ "$P" =~ ^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+$ ]] || { echo "Not a package name: $P (the phone's shell reads it)"; exit 1; }; "${ADB[@]}" shell pm clear "$P" >/dev/null; "${ADB[@]}" shell monkey -p "$P" -c android.intent.category.LAUNCHER 1 >/dev/null && echo "Started $P" ;;
  snap)
    NAME=$(echo "${1:?screen name}" | tr -c 'A-Za-z0-9_-' '_'); N=$(printf '%02d' $(( $(ls "$OUT"/*.xml 2>/dev/null | wc -l) + 1 )))
    sleep 1   # let animations settle before reading the screen
    "${ADB[@]}" exec-out screencap -p > "$OUT/$N-$NAME.png"
    "${ADB[@]}" shell uiautomator dump /sdcard/testhive-ui.xml >/dev/null && "${ADB[@]}" pull /sdcard/testhive-ui.xml "$OUT/$N-$NAME.xml" >/dev/null
    [ -f "$OUT/exploration.md" ] || printf '# Android exploration\nEverything below is OBSERVED behaviour, not confirmed requirements.\n\n' > "$OUT/exploration.md"
    { $PY "$(dirname "$0")/lib/uiscreen.py" summary "$OUT/$N-$NAME.xml" "$N $1"; printf -- '- Screenshot: %s\n\n' "$N-$NAME.png"; } >> "$OUT/exploration.md"
    $PY "$(dirname "$0")/lib/uiscreen.py" summary "$OUT/$N-$NAME.xml" "$N $1" ;;
  tap)
    X=$(last_xml); [ -n "$X" ] || { echo "Run snap first, so TestHive knows what is on the screen"; exit 1; }
    XY=$($PY "$(dirname "$0")/lib/uiscreen.py" find "$X" "${1:?id or text}") || exit 1
    "${ADB[@]}" shell input tap $XY && echo "Tapped $1 at $XY" ;;
  type) T="${1:?text}"; [[ "$T" =~ ^[A-Za-z0-9\ .,@_+-]*$ ]] || { echo "Only letters, digits, spaces and . , @ _ + - can be typed (the phone's shell reads the text)"; exit 1; }; "${ADB[@]}" shell input text "${T// /%s}" && echo "Typed" ;;
  back) "${ADB[@]}" shell input keyevent 4 && echo "Back" ;;
  *) echo "Unknown command: $CMD (install, packages, launch, snap, tap, type, back)"; exit 1 ;;
esac
