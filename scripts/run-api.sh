#!/usr/bin/env bash
# Runs a module's Postman collection with Newman and stores the run.
# Usage: bash scripts/run-api.sh <module> [--tag smoke|sanity|regression|e2e]   (reads .env and .env.<TEST_ENV>; needs: npm i -g newman)
# Writes reports/api-<module>.xml, then stores the run in runs/ (scripts/collect-run.sh). NO_COLLECT=1 skips that.
. "$(dirname "$0")/_env.sh"
MOD="${1:?module}"; TAG="${TH_TAG:-}"; [ "$2" = --tag ] && TAG="${3:?tag}"
. "$(dirname "$0")/_py.sh"
mkdir -p reports; rm -f reports/api-"$MOD".xml
COL=api/collections/"$MOD".postman_collection.json
if [ -n "$TAG" ]; then  # only the requests named with @<tag>
  T="reports/.api-$MOD-tag.json"; trap 'rm -f "$T"' EXIT  # a relative path: Windows python and node do not read /tmp
  $PY -c "import json,re,sys; c=json.load(open(sys.argv[1],encoding='utf-8')); c['item']=[i for i in c['item'] if re.search('@'+re.escape(sys.argv[3])+r'\b', i.get('name',''))]; json.dump(c,open(sys.argv[2],'w',encoding='utf-8'))" "$COL" "$T" "$TAG"
  COL="$T"
fi
newman run "$COL" -e api/environments/"$MOD".postman_environment.json ${API_BASE_URL:+--env-var "API_BASE_URL=$API_BASE_URL"} \
  --reporters cli,junit --reporter-junit-export reports/api-"$MOD".xml; RC=$?
[ -n "$NO_COLLECT" ] || [ ! -f reports/api-"$MOD".xml ] || bash "$(dirname "$0")/collect-run.sh" api "$MOD" --env "${TEST_ENV:-}"
exit $RC
