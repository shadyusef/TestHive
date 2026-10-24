# Sourced by demo/phase4/run.sh: where phase 3 ended. SIGNUP analysis, design and tools approved (Web UI: Playwright, API: Postman + Newman).
P1="$SRC/demo/phase1/recorded"; P2="$SRC/demo/phase2"
bash scripts/init-project.sh "Nakhla Rewards" >/dev/null; cp "$P2/CONTEXT.md" CONTEXT.md
cp "$P1"/recheck-2/requirements.csv "$P1"/recheck-2/gaps.csv analysis/
bash scripts/stage.sh init SIGNUP >/dev/null
# the phase 1 API spec, with example values for the sign-up body (so the contract request can succeed)
mkdir -p requirements/sources/SIGNUP
$PY -c "import sys,yaml; s=yaml.safe_load(open(sys.argv[1],encoding='utf-8')); p=s['components']['schemas']['SignupRequest']['properties']; [p[k].update(example=v) for k,v in dict(fullName='Sara Test',mobile='0500000099',password='Pass1234',birthDate='1990-01-15',language='en').items()]; yaml.safe_dump(s,open(sys.argv[2],'w',encoding='utf-8'),sort_keys=False,allow_unicode=True)" "$SRC/demo/phase1/sources/openapi.yaml" requirements/sources/SIGNUP/openapi.yaml
for st in analysis design; do
  bash scripts/stage.sh start SIGNUP $st >/dev/null
  [ $st = design ] && cp "$P2"/recorded/recheck-1/TestCases.csv "$P2"/recorded/recheck-1/requests.csv test-cases/ && cp "$P2"/recorded/recheck-1/gaps.csv analysis/
  bash scripts/stage.sh submit SIGNUP $st >/dev/null; bash scripts/stage.sh approve SIGNUP $st --by "Sara (QA lead)" >/dev/null
done
bash scripts/stage.sh start SIGNUP tools >/dev/null
bash scripts/tool-advice.sh choose SIGNUP "Web UI" Playwright --by "Sara (QA lead)" >/dev/null
bash scripts/tool-advice.sh choose SIGNUP API "Postman + Newman" --by "Sara (QA lead)" >/dev/null
bash scripts/stage.sh submit SIGNUP tools >/dev/null; bash scripts/stage.sh approve SIGNUP tools --by "Omar (QA manager)" >/dev/null
