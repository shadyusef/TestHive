#!/usr/bin/env bash
# Checks and installs the tools TestHive needs (bash version; on Windows hive runs setup.ps1).
# Usage: bash scripts/setup.sh [--check | --install] [--web]
#   --check    (default) report what is missing, install nothing; writes .testhive-ready when all required tools are present
#   --install  install what is missing (asks nothing more: run it only after the user agreed)
#   --web      also check/install Playwright (web tests, in web/)
#   --ocr      also check/install Tesseract OCR with Arabic (image masking); otherwise it is reported as optional
MODE=check; WEB=0; OCR=0
for a in "$@"; do case "$a" in --check) MODE=check;; --install) MODE=install;; --web) WEB=1;; --ocr) OCR=1;; -h|--help) sed -n 2,8p "$0"; exit 0;; esac; done
OS=$(uname -s); PM=""
if [ "$OS" = Darwin ]; then command -v brew >/dev/null && PM=brew; elif command -v apt-get >/dev/null; then PM=apt; fi
SUDO=""; [ "$(id -u)" != 0 ] && command -v sudo >/dev/null && SUDO=sudo
MISSING=()
have() { command -v "$1" >/dev/null 2>&1; }
ver() { "$@" 2>&1 | head -1; }
report() { # name, ok(0/1), detail
  if [ "$2" = 0 ]; then echo "OK       $1  ($3)"; else echo "MISSING  $1"; MISSING+=("$1"); fi; }

java_ok() { have java && [ "$(java -version 2>&1 | sed -n '1s/[^"]*"\([0-9]*\).*/\1/p')" -ge 17 ] 2>/dev/null; }
# A python that really runs (on Windows `python3` can be a Store stub that exists but does nothing).
py_ok() { for c in python3 python "py -3"; do $c -c "import sys; sys.exit(sys.version_info[0] != 3)" >/dev/null 2>&1 && { PYC="$c"; PYV="$($c --version 2>&1 | head -1)"; return 0; }; done; return 1; }
PYPKGS="see requirements.txt"
pypkgs_ok() { [ -n "$PYC" ] && $PYC -c "import openpyxl, pypdf, docx, PIL, pytesseract, yaml" >/dev/null 2>&1; }
TESS=tesseract; have tesseract || { [ -x "/c/Program Files/Tesseract-OCR/tesseract.exe" ] && TESS="/c/Program Files/Tesseract-OCR/tesseract.exe"; }
UD="${LOCALAPPDATA:+$LOCALAPPDATA/TestHive/tessdata}"; [ -z "$TESSDATA_PREFIX" ] && [ -n "$UD" ] && [ -d "$UD" ] && export TESSDATA_PREFIX="$UD"
ocr_ok() { "$TESS" --list-langs 2>/dev/null | tr -d '\r' | grep -qx ara; }

check_all() {
  MISSING=()
  have git     && report git 0 "$(ver git --version)"          || report git 1
  have node    && report node 0 "$(ver node -v)"               || report node 1
  py_ok        && report python3 0 "$PYV"                      || report python3 1
  pypkgs_ok    && report python-pkgs 0 "$PYPKGS"              || report python-pkgs 1
  java_ok      && report java17 0 "$(ver java -version)"       || report java17 1
  have maestro && report maestro 0 "$(ver maestro --version)"  || report maestro 1
  have adb     && report adb 0 "$(ver adb version)"            || report adb 1
  have newman  && report newman 0 "$(ver newman -v)"           || report newman 1
  have claude  && report claude-code 0 "$(ver claude --version)" || report claude-code 1
  if ocr_ok; then report tesseract 0 "with Arabic"; elif [ "$OCR" = 1 ]; then report tesseract 1; else echo "OPTIONAL tesseract + Arabic (image masking): bash scripts/setup.sh --install --ocr"; fi
  if [ "$WEB" = 1 ]; then [ -d web/node_modules/@playwright/test ] && report playwright 0 "web/node_modules" || report playwright 1; fi
}

pm_install() { # pkg names per manager: brew_name apt_name
  case "$PM" in
    brew) brew install "$1" ;;
    apt)  $SUDO apt-get install -y $2 ;;
    *)    echo "  No package manager found (need Homebrew on macOS or apt on Linux; on Windows use scripts/setup.ps1). Install $1 manually."; return 1 ;;
  esac
}

install_one() {
  case "$1" in
    git) pm_install git git ;;
    node) pm_install node nodejs && { have npm || pm_install npm npm; } ;;
    python3) pm_install python3 python3 ;;
    python-pkgs) py_ok && $PYC -m pip install --user -r requirements.txt ;;
    tesseract) [ "$PM" = brew ] && brew install tesseract tesseract-lang || pm_install x "tesseract-ocr tesseract-ocr-ara" ;;
    java17) pm_install openjdk@17 openjdk-17-jdk && { [ "$PM" != brew ] || echo "  If java is still not found: sudo ln -sfn \"\$(brew --prefix)/opt/openjdk@17/libexec/openjdk.jdk\" /Library/Java/JavaVirtualMachines/openjdk-17.jdk"; } ;;
    maestro) curl -fsSL "https://get.maestro.mobile.dev" | bash && echo "  Add to PATH: export PATH=\"\$PATH:\$HOME/.maestro/bin\"" ;;
    adb) [ "$PM" = brew ] && brew install --cask android-platform-tools || pm_install x android-tools-adb ;;
    newman) npm install -g newman ;;
    claude-code) npm install -g @anthropic-ai/claude-code ;;
    playwright) (cd web && npm install && npx playwright install chromium) ;;
  esac
}

echo "TestHive setup ($MODE) on $OS${PM:+, using $PM}"
check_all
if [ ${#MISSING[@]} -eq 0 ]; then
  [ "$WEB" = 0 ] && date -u +%FT%TZ > .testhive-ready
  echo "All prerequisites present."
else
  if [ "$MODE" = install ]; then
    for t in "${MISSING[@]}"; do echo "Installing $t ..."; install_one "$t" || echo "  FAILED $t (see manual steps below)"; done
    echo "--- re-check (open a new terminal first if a tool is still not found) ---"; check_all
    [ ${#MISSING[@]} -eq 0 ] && [ "$WEB" = 0 ] && date -u +%FT%TZ > .testhive-ready
  else
    echo "Missing: ${MISSING[*]}"; echo "Run: bash scripts/setup.sh --install"
  fi
fi
cat <<'T'

Manual steps no script can do:
  Android: enable Developer options + USB debugging on the phone, connect by USB, accept the prompt, then run: bash scripts/check-devices.sh
  iOS (Mac only): install Xcode from the App Store, then run: xcode-select --install
  Claude Code: first start asks you to sign in.
T
[ ${#MISSING[@]} -eq 0 ]
