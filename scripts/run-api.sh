#!/usr/bin/env bash
# Runs a module's Postman collection with Newman and stores the run.
# Usage: bash scripts/run-api.sh <module> [--tag smoke|sanity|regression|e2e] [--ids TC-X-001,...] | <module> --contract   (reads .env and .env.<TEST_ENV>; needs: npm i -g newman)
#   --contract  the contract tests built from the API spec (scripts/contract.sh) instead of the case tests
#   --ids       only these cases (retest.sh uses it)
# Writes reports/api-<module>.xml (contract: reports/contract-<module>.xml), then stores the run in runs/ (scripts/collect-run.sh) with
# each request and its response as evidence (Authorization, cookies and secret-looking fields masked). NO_COLLECT=1 skips that.
# TEST_API_TOKEN, when set, is the bearer token the contract requests send to endpoints the spec protects.
. "$(dirname "$0")/_env.sh"
MOD="${1:?module}"; shift; TAG="${TH_TAG:-}"; IDS=""; CONTRACT=""
while [ $# -gt 0 ]; do
  case "$1" in --tag) TAG="${2:?tag}"; shift 2;; --ids) IDS="${2:?case IDs}"; shift 2;; --contract) CONTRACT=1; shift;; *) echo "Unknown option: $1" >&2; exit 2;; esac
done
case "$IDS" in *[!A-Z0-9,-]*) echo "--ids: case IDs separated by commas" >&2; exit 2;; esac
KIND=api
. "$(dirname "$0")/_py.sh"
COL=api/collections/"$MOD".postman_collection.json
if [ -n "$CONTRACT" ]; then
  KIND=contract; TAG=""; COL=api/collections/"$MOD".contract.postman_collection.json
  [ -f "$COL" ] || { echo "No contract tests for $MOD yet: run bash scripts/contract.sh $MOD"; exit 1; }
fi
mkdir -p reports; rm -rf reports/"$KIND"-"$MOD".xml reports/"$KIND"-"$MOD".json reports/"$KIND"-"$MOD"-evidence
if [ -n "$TAG$IDS" ]; then  # only the requests named with @<tag>, or with these case IDs
  T="reports/.api-$MOD-tag.json"; trap 'rm -f "$T"' EXIT  # a relative path: Windows python and node do not read /tmp
  $PY -c "import json,re,sys; c=json.load(open(sys.argv[1],encoding='utf-8')); t,ids=sys.argv[3],[x for x in sys.argv[4].split(',') if x]; c['item']=[i for i in c['item'] if (not t or re.search('@'+re.escape(t)+r'\b', i.get('name',''))) and (not ids or any(i.get('name','').startswith('['+x+']') for x in ids))]; json.dump(c,open(sys.argv[2],'w',encoding='utf-8'))" "$COL" "$T" "$TAG" "$IDS"
  COL="$T"
fi
EF=(); [ -f api/environments/"$MOD".postman_environment.json ] && EF=(-e api/environments/"$MOD".postman_environment.json)
if [ -n "$TEST_API_TOKEN" ]; then  # a file, not the command line: other processes can read command lines
  G="reports/.api-$MOD-globals.json"; trap 'rm -f "$G" "${T:-}"' EXIT
  TEST_API_TOKEN="$TEST_API_TOKEN" $PY -c "import json,os,sys; json.dump({'values': [{'key': 'TEST_API_TOKEN', 'value': os.environ['TEST_API_TOKEN'], 'enabled': True}]}, open(sys.argv[1],'w'))" "$G"
  EF+=(-g "$G")
fi
newman run "$COL" "${EF[@]}" ${API_BASE_URL:+--env-var "API_BASE_URL=$API_BASE_URL"} \
  --reporters cli,junit,json --reporter-junit-export reports/"$KIND"-"$MOD".xml --reporter-json-export reports/"$KIND"-"$MOD".json; RC=$?
EV=(); [ -f reports/"$KIND"-"$MOD".json ] && $PY "$(dirname "$0")/lib/api_evidence.py" reports/"$KIND"-"$MOD".json reports/"$KIND"-"$MOD"-evidence && rm -f reports/"$KIND"-"$MOD".json && EV=(--evidence reports/"$KIND"-"$MOD"-evidence)
[ -n "$NO_COLLECT" ] || [ ! -f reports/"$KIND"-"$MOD".xml ] || bash "$(dirname "$0")/collect-run.sh" "$KIND" "$MOD" --env "${TEST_ENV:-}" "${EV[@]}"
exit $RC
