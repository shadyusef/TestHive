#!/usr/bin/env bash
# Shows connected Android devices and booted iOS simulators (if on a Mac). Read-only.
echo "== Maestro =="; (maestro --version 2>/dev/null || echo "maestro not found")
echo "== Android (adb) =="; (adb devices 2>/dev/null || echo "adb not found")
if command -v xcrun >/dev/null 2>&1; then
  echo "== iOS (simctl) =="; xcrun simctl list devices booted
else
  echo "== iOS == not available on this machine (needs macOS)"
fi
