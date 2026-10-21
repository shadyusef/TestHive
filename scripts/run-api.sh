#!/usr/bin/env bash
# Runs a module's Postman collection with Newman and stores the run.
# Usage: bash scripts/run-api.sh <module>   (reads .env; needs: npm i -g newman)
# Writes reports/api-<module>.xml, then stores the run in runs/ (scripts/collect-run.sh). NO_COLLECT=1 skips that.
[ -f .env ] && { set -a; eval "$(tr -d '\r' < .env)"; set +a; }
MOD="${1:?module}"
mkdir -p reports; rm -f reports/api-"$MOD".xml
newman run api/collections/"$MOD".postman_collection.json -e api/environments/"$MOD".postman_environment.json \
  --reporters cli,junit --reporter-junit-export reports/api-"$MOD".xml; RC=$?
[ -n "$NO_COLLECT" ] || [ ! -f reports/api-"$MOD".xml ] || bash "$(dirname "$0")/collect-run.sh" api "$MOD" --env "${TEST_ENV:-}"
exit $RC
