#!/usr/bin/env bash
# One entry point for every TestHive script (Windows users call it through hive.cmd: .\hive <name> ...).
# Usage: bash scripts/hive.sh <script-name> [args]    e.g.  stage status SIGNUP   -> scripts/stage.sh status SIGNUP
#        bash scripts/hive.sh <path/to/file.sh> [args] e.g.  demo/phase0/run.sh
# "setup" on Windows runs scripts/setup.ps1 (winget) with the same options: --check --install --web --ocr.
cd "$(dirname "$0")/.." || exit 1
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) WIN=1; export TH_CMD="${TH_CMD:-.\\hive}";; *) WIN=0; export TH_CMD="${TH_CMD:-bash scripts/hive.sh}";; esac
if [ -z "$1" ]; then
  echo "Usage: hive <script> [args]   Scripts:"
  for f in scripts/*.sh; do n=$(basename "$f" .sh); case "$n" in hive|_py|_env) ;; *) printf '  %-16s %s\n' "$n" "$(sed -n 2p "$f" | sed 's/^# *//')";; esac; done
  echo "Docs: README.md, QUICKSTART.md, docs/TROUBLESHOOTING.md"
  exit 1
fi
case "$1" in
  *.sh) exec bash "$@" ;;
esac
if [ "$1" = setup ] && [ "$WIN" = 1 ]; then
  shift; A=()
  for a in "$@"; do case "$a" in --check) A+=(-Check);; --install) A+=(-Install);; --web) A+=(-Web);; --ocr) A+=(-Ocr);; *) A+=("$a");; esac; done
  exec powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/setup.ps1 "${A[@]}"
fi
[ -f "scripts/$1.sh" ] || { echo "Unknown script: $1 (run hive with no arguments for the list)"; exit 1; }
S="scripts/$1.sh"; shift
exec bash "$S" "$@"
