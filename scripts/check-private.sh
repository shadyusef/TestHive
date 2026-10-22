#!/usr/bin/env bash
# Checks that no private name (from the git-ignored .private-names file) appears in files git would publish.
# Usage: bash scripts/check-private.sh        exit 1 and the matching lines if a name is found; exit 0 if clean or no list exists
# .private-names: one name per line (lines starting with # are ignored), matched without regard to case.
cd "$(dirname "$0")/.." || exit 1
[ -f .private-names ] || { echo "PRIVATE CHECK SKIPPED: no .private-names file (one private name per line, git-ignored)"; exit 0; }
names=$(grep -v '^#' .private-names | sed '/^[[:space:]]*$/d')
[ -n "$names" ] || { echo "PRIVATE CHECK SKIPPED: .private-names is empty"; exit 0; }
hits=$(git ls-files -co --exclude-standard -z | xargs -0 grep -I -n -i -F -f <(printf '%s\n' "$names") -- 2>/dev/null | grep -v '^\.private-names:')
if [ -n "$hits" ]; then echo "PRIVATE CHECK FAIL: private names found in files that would be published:"; echo "$hits" | cut -c1-200; exit 1; fi
echo "PRIVATE CHECK PASS ($(printf '%s\n' "$names" | wc -l | tr -d ' ') names, $(git ls-files -co --exclude-standard | wc -l | tr -d ' ') files)"
