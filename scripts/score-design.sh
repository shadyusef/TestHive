#!/usr/bin/env bash
# Benchmark: how many required test conditions in a key (e.g. demo/phase2/condition-key.csv) the cases cover.
# Usage: bash scripts/score-design.sh <MODULE> <condition-key.csv>     pass mark: TH_SCORE_TARGET (default 80)
. "$(dirname "$0")/_py.sh"
$PY "$(dirname "$0")/lib/design.py" score "$@"
