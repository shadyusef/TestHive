# Sourced by the run scripts: loads .env, then .env.<TEST_ENV> over it (a named environment: staging, uat, ...).
# TEST_ENV given on the command line wins over the one in .env. Both files stay on this PC (git-ignored).
# Only the addresses and the TEST_* values reach the tests (exported); other keys stay in this shell (run-mobile passes its own).
_TE="$TEST_ENV"
[ -f .env ] && eval "$(tr -d '\r' < .env)"
TEST_ENV="${_TE:-$TEST_ENV}"
case "$TEST_ENV" in *[!A-Za-z0-9._-]*|.*) echo "TEST_ENV may only use letters, digits, . _ - (got: $TEST_ENV)" >&2; exit 1;; esac
if [ -n "$TEST_ENV" ] && [ -f ".env.$TEST_ENV" ]; then eval "$(tr -d '\r' < ".env.$TEST_ENV")"; fi
for _k in BASE_URL API_BASE_URL APP_ID IOS_APP_ID $(compgen -v TEST_); do export "$_k"; done
