#!/usr/bin/env bash
# Runs a module's Postman collection with Newman and stores the run.
# Usage: bash scripts/run-api.sh <module> [--tag smoke|sanity|regression|e2e | --contract]   (reads .env and .env.<TEST_ENV>; needs: npm i -g newman)
#   --contract  the contract tests built from the API spec (scripts/contract.sh) instead of the case tests
# Writes reports/api-<module>.xml (contract: reports/contract-<module>.xml), then stores the run in runs/ (scripts/collect-run.sh). NO_COLLECT=1 skips that.
# TEST_API_TOKEN, when set, is the bearer token the contract requests send to endpoints the spec protects.
. "$(dirname "$0")/_env.sh"
MOD="${1:?module}"; TAG="${TH_TAG:-}"; KIND=api; [ "$2" = --tag ] && TAG="${3:?tag}"
. "$(dirname "$0")/_py.sh"
COL=api/collections/"$MOD".postman_collection.json
if [ "$2" = --contract ]; then
  KIND=contract; TAG=""; COL=api/collections/"$MOD".contract.postman_collection.json
  [ -f "$COL" ] || { echo "No contract tests for $MOD yet: run bash scripts/contract.sh $MOD"; exit 1; }
fi
mkdir -p reports; rm -f reports/"$KIND"-"$MOD".xml
if [ -n "$TAG" ]; then  # only the requests named with @<tag>
  T="reports/.api-$MOD-tag.json"; trap 'rm -f "$T"' EXIT  # a relative path: Windows python and node do not read /tmp
  $PY -c "import json,re,sys; c=json.load(open(sys.argv[1],encoding='utf-8')); c['item']=[i for i in c['item'] if re.search('@'+re.escape(sys.argv[3])+r'\b', i.get('name',''))]; json.dump(c,open(sys.argv[2],'w',encoding='utf-8'))" "$COL" "$T" "$TAG"
  COL="$T"
fi
EF=(); [ -f api/environments/"$MOD".postman_environment.json ] && EF=(-e api/environments/"$MOD".postman_environment.json)
if [ -n "$TEST_API_TOKEN" ]; then  # a file, not the command line: other processes can read command lines
  G="reports/.api-$MOD-globals.json"; trap 'rm -f "$G" "${T:-}"' EXIT
  TEST_API_TOKEN="$TEST_API_TOKEN" $PY -c "import json,os,sys; json.dump({'values': [{'key': 'TEST_API_TOKEN', 'value': os.environ['TEST_API_TOKEN'], 'enabled': True}]}, open(sys.argv[1],'w'))" "$G"
  EF+=(-g "$G")
fi
newman run "$COL" "${EF[@]}" ${API_BASE_URL:+--env-var "API_BASE_URL=$API_BASE_URL"} ${TEST_API_TOKEN:+--env-var "TEST_API_TOKEN=$TEST_API_TOKEN"} \
  --reporters cli,junit --reporter-junit-export reports/"$KIND"-"$MOD".xml; RC=$?
[ -n "$NO_COLLECT" ] || [ ! -f reports/"$KIND"-"$MOD".xml ] || bash "$(dirname "$0")/collect-run.sh" "$KIND" "$MOD" --env "${TEST_ENV:-}"
exit $RC
