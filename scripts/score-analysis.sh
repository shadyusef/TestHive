#!/usr/bin/env bash
# Scores the analyst's gaps against an answer key of planted gaps (the TestHive benchmark).
# Usage: bash scripts/score-analysis.sh <MODULE> <answer-key.csv>   (target: TH_SCORE_TARGET, default 80 percent)
# Key columns: Key, Gap, Keywords. Keywords: groups separated by ';', alternatives by '|'; a gap matches when every
# group has a match (at the start of a word) in its kind or question. One gap counts for one planted gap at most.
. "$(dirname "$0")/_py.sh"
$PY "$(dirname "$0")/lib/analysis.py" score "$@"
