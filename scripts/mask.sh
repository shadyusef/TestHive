#!/usr/bin/env bash
# Anonymise documents before they are sent to Claude, and restore them afterwards. Arabic and English.
# Usage: bash scripts/mask.sh mask    <in> <out>   text: personal data -> tokens like [EMAIL_001]; image: blacked out (OCR)
#        bash scripts/mask.sh unmask  <in> <out>   put the real values back (reports kept on this PC)
#        bash scripts/mask.sh check   <in>         counts only, prints no values (safe for agents)
#        bash scripts/mask.sh review  <in>         HUMAN ONLY: each match with its context, to spot wrong ones
#        bash scripts/mask.sh suggest <in>         HUMAN ONLY: likely people's names not yet in .mask-terms
# Masks emails, phones, IBANs (mod-97 checked), card numbers and Saudi national / iqama IDs (Luhn checked),
# plus every term in .mask-terms (names, company, project; Arabic or English, one per line).
# Never masked: values in .mask-allow (one per line, or "re:<regex>"). Map of tokens: .mask-map.json.
# All three files stay on this PC (git-ignored). review and suggest print real values: agents must not run them.
. "$(dirname "$0")/_py.sh"
$PY "$(dirname "$0")/lib/mask.py" "$@"
