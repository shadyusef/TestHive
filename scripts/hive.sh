#!/usr/bin/env bash
# One entry point for every TestHive script (Windows users call it through hive.cmd: .\hive <name> ...).
# Usage: bash scripts/hive.sh <script-name> [args]    e.g.  stage status SIGNUP   -> scripts/stage.sh status SIGNUP
#        bash scripts/hive.sh <path/to/file.sh> [args] e.g.  demo/phase0/run.sh
cd "$(dirname "$0")/.." || exit 1
if [ -z "$1" ]; then
  echo "Usage: hive <script> [args]   Scripts:"
  for f in scripts/*.sh; do n=$(basename "$f" .sh); case "$n" in hive|_py) ;; *) printf '  %-16s %s\n' "$n" "$(sed -n 2p "$f" | sed 's/^# *//')";; esac; done
  exit 1
fi
case "$1" in
  *.sh) exec bash "$@" ;;
esac
[ -f "scripts/$1.sh" ] || { echo "Unknown script: $1 (run hive with no arguments for the list)"; exit 1; }
S="scripts/$1.sh"; shift
exec bash "$S" "$@"
