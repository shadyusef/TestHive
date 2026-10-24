"""TestHive automation (stage 4): the test project for the tools approved in stage 3, one placeholder test per case,
the state of each case, the check before approval, and the automation baseline.
Ready-made setups: Playwright (web/), Postman + Newman (api/), Maestro (mobile/); other approved tools are set up by hand.
Called by scripts/scaffold.sh, check-automation.sh, stage.sh (check --for-approval, baseline) and Studio.
Formats: docs/FORMATS.md (automation)."""
import sys, os, re, json, glob, time, hashlib, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analysis import read_csv, write_csv, die, stage_status
import design, tools, contract
from pyrun import lib_cmd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DIR = os.environ.get("TH_AUTOMATION", "automation")  # baselines of the approved automation
STUB = "TESTHIVE:STUB"  # in every placeholder; an engineer removes it when the test is written
KIND = {"Playwright": "web", "Postman + Newman": "api", "Maestro": "mobile"}  # approved tool -> TestHive's setup and run script
ASSERT = {"web": r"expect\(", "api": r"pm\.(test|expect)", "mobile": r"^\s*-\s*(assert\w*|extendedWaitUntil)"}


def slug(t): return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:40].strip("-") or "case"
def line(t): return re.sub("[\x00-\x1f\x7f-\x9f\u2028\u2029]+", " ", t or "").strip()  # case text stays inside one comment line (YAML also breaks on U+0085)
def tags(c): return [t for t in design.TAGS if t in design.refs(c["Tags"])]


def plan(module):
    """(approved tools by test type, the approved cases to automate with their test type and tool), or an error string."""
    if stage_status(module, "tools") != "approved": return f"the tools of {module} are not approved yet (stage 3)"
    b = tools.design_baseline(module)
    base = os.path.join(tools.DIR, "baseline", module)
    vs = sorted(int(d[1:]) for d in os.listdir(base) if re.fullmatch(r"v\d+", d)) if os.path.isdir(base) else []
    if not b or not vs: return f"no approved design or tool baseline for {module}"
    with open(os.path.join(base, f"v{vs[-1]}", "meta.json"), encoding="utf-8") as f: chosen = json.load(f)["tools"]
    out = []
    for c in b[1]:
        if not design.active(c) or c["Automation"] != "Yes" or c["Type"] not in tools.FUNCTIONAL: continue
        tts = [t for t in tools.BY_PLATFORM.get(c["Platform"], []) if t in chosen]
        if tts: out.append(dict(c, test_type=tts[0], tool=chosen[tts[0]], kind=KIND.get(chosen[tts[0]], "")))
    return chosen, out


RUN_ID = re.compile(r"R-\d{8}-\d{2,}")


def last_runs(module):
    """The latest stored run of each kind (web, api, contract, mobile) of the module: totals, and the cases that did not pass with their evidence."""
    base = os.environ.get("TH_RUNS", "runs")
    out = {}
    for d in sorted(glob.glob(os.path.join(base, "R-*")), key=lambda p: (len(os.path.basename(p)), os.path.basename(p)), reverse=True):
        if not RUN_ID.fullmatch(os.path.basename(d)): continue
        try:
            with open(os.path.join(d, "meta.json"), encoding="utf-8") as f: meta = json.load(f)
            if meta.get("module") != module or meta.get("kind") in out: continue
            with open(os.path.join(d, "results.json"), encoding="utf-8") as f: res = json.load(f)
        except (OSError, ValueError): continue
        bad = [c for c in res.get("cases", []) if c.get("status") != "passed"]
        stub = [c for c in bad if c.get("status") == "skipped" or "placeholder" in (c.get("message") or "")]  # tests not written yet
        out[meta["kind"]] = {"run": os.path.basename(d), "at": meta.get("collected_at", ""), "env": meta.get("env", ""), "target": meta.get("target", ""), "totals": meta.get("totals", {}),
                             "placeholders": len(stub), "problems": [{k: c.get(k) for k in ("id", "name", "suite", "status", "message", "evidence")} for c in bad if c not in stub][:50]}
    return out


def contract_status(module, chosen, runs=None):
    """None when the module has no API tool or no OpenAPI spec; else the contract's state, its last run and the endpoints that failed."""
    if "Postman + Newman" not in chosen.values(): return None
    st = contract.state(module)
    if not st: return None
    run = (last_runs(module) if runs is None else runs).get("contract")
    if run and run["at"] < st["built_at"]: run = None  # a run of an older contract
    bugs, failed = contract.known_bugs(module), sorted({p["suite"] for p in (run or {}).get("problems", []) if p.get("suite")})
    return dict(st, run=run["run"] if run else "", failed=[{"endpoint": e, "bug": bugs.get(e, "")} for e in failed])


def collection(module): return os.path.join("api", "collections", f"{module}.postman_collection.json")


FOLDER = {"web": ("web", "tests", ".spec.ts"), "mobile": ("mobile", "flows", ".yaml")}


def test_files(module):
    """{(kind, case ID): file} of the module's web specs and Maestro flows: one listing per folder, not one search per case."""
    out = {}
    for kind, (top, sub, ext) in FOLDER.items():
        d = os.path.join(top, sub, module)
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            m = re.match(r"(TC-[A-Z0-9-]+-\d{3})_.*" + re.escape(ext) + "$", f)
            if m: out.setdefault((kind, m[1]), os.path.join(d, f))
    return out


def spec_of(module, c, files=None):
    """The test file of a case (it may not exist yet)."""
    if c["kind"] in FOLDER:
        top, sub, ext = FOLDER[c["kind"]]
        return (test_files(module) if files is None else files).get((c["kind"], c["ID"])) or os.path.join(top, sub, module, f"{c['ID']}_{slug(c['Title'])}{ext}")
    return collection(module) if c["kind"] == "api" else ""


def comments(c, mark):
    return [f"{mark} {STUB} written by scaffold: write the test from these steps, then remove this line" + (" and test.fixme" if mark == "//" else ""),
            f"{mark} Requirements: {line(c['Requirements'])} | priority {line(c['Priority'])} | tags {' '.join(tags(c))}",
            f"{mark} Preconditions: {line(c['Preconditions'])}", f"{mark} Steps: {line(c['Steps'])}",
            f"{mark} Expected: {line(c['Expected Result'])}", f"{mark} Test data: {line(c['Test Data'])}"]


def name(c): return f"[{c['ID']}] {line(c['Title'])}" + "".join(f" @{t}" for t in tags(c))  # the ID and @tags are how runs pick tests


def web_stub(c):
    e2e = "e2e" in tags(c)  # a journey: shared steps, and the API for set-up and checks
    return "\n".join([f"import {{ test, expect }} from '../../fixtures/testhive';", ""] + comments(c, "//") +
                      ([f"// Journey: reuse the steps in web/pages/{line(c['Module'])}/steps.ts; set up or check data through the API with `api` (api.post(...))"] if e2e else []) +
                      [f"test.fixme({json.dumps(name(c))}, async ({{ page, data{', api' if e2e else ''} }}) => {{", "});", ""])


def mobile_stub(c):
    return "\n".join(comments(c, "#") + ["appId: ${APP_ID}", f"name: {json.dumps(name(c).replace('${', '$ {'))}", "tags:"] + [f"  - {t}" for t in tags(c)] +  # Maestro evaluates ${...} in names
                     ["---", "- runFlow: ../../subflows/launch-clean.yaml", f"- assertVisible: \"{STUB} not written yet\"  # fails until the flow is written", ""])


def api_item(c):
    return {"name": name(c), "request": {"method": "GET", "url": "{{API_BASE_URL}}/", "description": "\n".join(x[3:] for x in comments(c, "//"))},
            "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": [
                f"// {STUB}: write the request and its checks, then remove this line",
                "pm.test('not written yet', () => { throw new Error('TestHive placeholder: not written yet'); });"]}}]}


def read_json(p):
    with open(p, encoding="utf-8") as f: return json.load(f)


def write_json(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".tmp", "w", encoding="utf-8", newline="\n") as f: json.dump(data, f, indent=2, ensure_ascii=False); f.write("\n")
    os.replace(p + ".tmp", p)


def items(module):
    """Requests of the module's collection by case ID: {ID: item}."""
    p = collection(module)
    if not os.path.exists(p): return {}
    out = {}
    for it in read_json(p).get("item", []):
        m = re.match(r"\[(TC-[A-Z0-9-]+-\d{3})\]", it.get("name", ""))
        if m: out[m[1]] = it
    return out


FIXTURE = """// Shared by every TestHive web test (written by scaffold.sh, kept when it exists): unique test data per test, and `api`
// for journeys that set up or check data through the API (requests go to API_BASE_URL, or BASE_URL when it is not set).
// scripts/run-web.sh loads .env (and .env.<TEST_ENV>), so BASE_URL and the other values are in process.env.
import { test as base, expect, APIRequestContext } from '@playwright/test';
import * as fs from 'fs';

type Data = { unique: (prefix?: string) => string; digits: (n: number) => string; env: string };
export const test = base.extend<{ data: Data; api: APIRequestContext; browserstack: void }>({
  browserstack: [async ({ page }, use, info) => {  // on a BrowserStack target: the session's link is kept with the test's evidence
    await use();
    if (!process.env.TH_BS_CAPS) return;
    try {
      const d = JSON.parse(await page.evaluate(() => {}, `browserstack_executor: ${JSON.stringify({ action: 'getSessionDetails' })}`) as string);
      fs.writeFileSync(info.outputPath('browserstack.txt'), `BrowserStack session ${d.hashed_id}: ${d.public_url || ''}
`);
    } catch { /* not at BrowserStack (a local stand-in) */ }
  }, { auto: true }],
  api: async ({ playwright }, use) => {
    const ctx = await playwright.request.newContext({ baseURL: process.env.API_BASE_URL || process.env.BASE_URL });
    await use(ctx);
    await ctx.dispose();
  },
  data: async ({}, use, info) => {
    let n = 0;
    const run = `${Date.now().toString(36)}${info.workerIndex}${info.repeatEachIndex}`;
    await use({
      unique: (prefix = 't') => `${prefix}-${run}-${++n}`,
      digits: k => (String(Date.now()) + String(info.workerIndex) + String(++n).padStart(3, '0')).slice(-k),
      env: process.env.TEST_ENV || '',
    });
  },
});
export { expect };
"""


def scaffold(module):
    """Writes what is missing: never overwrites a file or a request that exists. Returns (lines to print, error)."""
    p = plan(module)
    if isinstance(p, str): return [], p
    chosen, cases = p
    out, made = [], {"web": 0, "api": 0, "mobile": 0}
    if any(c["kind"] == "web" for c in cases) and not os.path.exists(os.path.join("web", "fixtures", "testhive.ts")):
        os.makedirs(os.path.join("web", "fixtures"), exist_ok=True)
        with open(os.path.join("web", "fixtures", "testhive.ts"), "w", encoding="utf-8", newline="\n") as f: f.write(FIXTURE)
        out.append("  web/fixtures/testhive.ts: shared fixture (unique test data)")
    files = test_files(module)
    for c in cases:
        if c["kind"] in ("web", "mobile"):
            s = spec_of(module, c, files)
            if os.path.exists(s): continue
            os.makedirs(os.path.dirname(s), exist_ok=True)
            with open(s, "w", encoding="utf-8", newline="\n") as f: f.write(web_stub(c) if c["kind"] == "web" else mobile_stub(c))
            made[c["kind"]] += 1
    api = [c for c in cases if c["kind"] == "api"]
    if api:
        p, have = collection(module), items(module)
        col = read_json(p) if os.path.exists(p) else {"info": {"name": module, "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"}, "item": []}
        new = [api_item(c) for c in api if c["ID"] not in have]
        if new: col["item"] += new; write_json(p, col); made["api"] = len(new)
        env = os.path.join("api", "environments", f"{module}.postman_environment.json")
        if not os.path.exists(env):
            write_json(env, {"name": module, "values": [{"key": "API_BASE_URL", "value": "", "enabled": True}]})
            out.append(f"  {env.replace(os.sep, '/')}: environment (run-api fills API_BASE_URL from .env)")
    for k, folder in (("web", f"web/tests/{module}/"), ("api", collection(module).replace(os.sep, "/")), ("mobile", f"mobile/flows/{module}/")):
        if made[k]: out.append(f"  {folder}: {made[k]} placeholder tests")
    if contract_status(module, chosen) and contract.state(module)["state"] != "current":
        col = contract.build(module); write_json(contract.path(module), col)
        out.append(f"  {contract.path(module).replace(os.sep, '/')}: contract tests, {len(col['item'])} endpoints from the API spec")
    for tt, tool in chosen.items():
        if tool not in KIND and any(c["test_type"] == tt for c in cases):
            out.append(f"  {tt}: {tool} has no TestHive setup: {sum(1 for c in cases if c['test_type'] == tt)} cases are automated by hand")
    rows = read_csv(design.CASE_FILE, design.CASE_COLS)  # the sheet says where each test is (gate.sh checks it exists)
    files = test_files(module)
    spec = {c["ID"]: spec_of(module, c, files).replace(os.sep, "/") for c in cases if c["kind"]}
    changed = [r for r in rows if r["ID"] in spec and not r["Automation Spec"]]
    for r in changed: r["Automation Spec"] = spec[r["ID"]]
    if changed: write_csv(design.CASE_FILE, design.CASE_COLS, rows)
    return out or ["  nothing new: every case already has its test"], None


def state(module, c, item=None, files=None):
    """missing | stub | written-no-check | written | stable, and the bug a written test expects to fail on, if any."""
    if c["kind"] == "api":
        if not item: return "missing", ""
        text = json.dumps(item)
        if STUB in text: return "stub", ""
        text = json.dumps(item.get("event", []))  # the checks only: the description repeats the case text
    else:
        s = spec_of(module, c, files)
        if not os.path.exists(s): return "missing", ""
        with open(s, encoding="utf-8", errors="replace") as f: text = f.read()
        if STUB in text: return "stub", ""
        if c["kind"] == "web": text = re.sub(r"(?m)^\s*//.*$", "", text)  # the case text sits in comment lines: it cannot fake a check
        else: text = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#") or re.match(r"\s*#\s*BUG-", l))
    bug = re.search(r"(?:test\.fail\([^)]*?|#\s*|known bug:?\s*)(BUG-[A-Z0-9-]+)", text, re.I)  # test.fail(...BUG-1), a flow's "# BUG-1"
    if not re.search(ASSERT[c["kind"]], text, re.M): return "written-no-check", ""
    return ("stable" if os.path.exists(os.path.join("reports", f"stable-{c['ID']}.txt")) else "written"), (bug[1] if bug else "")


def status(module):
    """Per case: ID, title, priority, tags, test type, tool, file, state; or None before the tools are approved."""
    p = plan(module)
    if isinstance(p, str): return None
    chosen, cases = p
    its, files = items(module), test_files(module)
    rows = []
    for c in cases:
        st, bug = state(module, c, its.get(c["ID"]), files) if c["kind"] else ("by-hand", "")
        rows.append({"ID": c["ID"], "Title": c["Title"], "Priority": c["Priority"], "Tags": " ".join(tags(c)), "type": c["test_type"],
                     "tool": c["tool"], "kind": c["kind"], "spec": spec_of(module, c, files).replace(os.sep, "/") if c["kind"] else "", "state": st, "bug": bug})
    return {"tools": chosen, "cases": rows, "contract": contract_status(module, chosen)}


def problems(module, for_approval=False, s=None):
    """(errors, warnings); s: the status when the caller has it already."""
    p = plan(module) if s is None else None
    if isinstance(p, str): return [p], []
    s = s or status(module)
    err, warn, cs = [], [], s["cases"]
    say = lambda st, text: [f"{c['ID']}: {text} ({c['spec']})" for c in cs if c["state"] == st]
    err += say("missing", "no test yet: run scaffold") + say("stub", "still a placeholder") + say("written-no-check", "the test checks nothing (no assertion)")
    if for_approval: err += say("written", "not proven stable yet: run stable.sh until it passes 3 times in a row")
    warn += [f"{c['ID']}: expected to fail on {c['bug']} (a known bug)" for c in cs if c["bug"]]
    ct = s.get("contract")
    if ct and ct["state"] == "missing": err.append("contract tests: not built yet from the API spec: run scaffold (or contract.sh)")
    elif ct and ct["state"] == "stale": err.append("contract tests: the API spec changed since they were built: run contract.sh (or scaffold) again")
    elif ct and for_approval and not ct["run"]: err.append("contract tests: not run since they were built: run-api.sh <module> --contract")
    elif ct:
        err += [f"contract tests: {f['endpoint']} answers differently from the spec (see the last contract run)" for f in ct["failed"] if not f["bug"]]
        warn += [f"contract tests: {f['endpoint']} is expected to fail on {f['bug']} (a known bug)" for f in ct["failed"] if f["bug"]]
    hand = [c for c in cs if c["state"] == "by-hand"]
    if hand: warn.append(f"{len(hand)} cases use tools without a TestHive setup ({', '.join(sorted({c['tool'] for c in hand}))}): not checked here")
    if not cs: warn.append("no approved functional case is marked Automation Yes: nothing to automate")
    return err, warn


def cmd_scaffold(a):
    if len(a) != 1: die("Usage: scaffold.sh <MODULE>")
    module = a[0].upper()
    out, err = scaffold(module)
    if err: die(f"NOT SET UP: {err}")
    if stage_status(module, "automation") == "pending":
        subprocess.run(lib_cmd("stage.py", "start", module, "automation"))
    print(f"SCAFFOLD {module}:\n" + "\n".join(out))


def cmd_check(a):
    module = next((x.upper() for x in a if not x.startswith("--")), None)
    if not module: die("Usage: check-automation.sh <MODULE> [--for-approval]")
    err, warn = problems(module, "--for-approval" in a)
    for w in warn: print("  warning: " + w)
    cs = (status(module) or {"cases": []})["cases"]
    count = ", ".join(f"{k} {n}" for k in ("stable", "written", "stub", "missing", "by-hand") if (n := sum(1 for c in cs if c["state"] == k)))
    if err: print(f"AUTOMATION NOT OK (module {module}): {count}\n" + "\n".join("- " + e for e in err[:40]) + (f"\n- … {len(err) - 40} more" if len(err) > 40 else "")); sys.exit(1)
    print(f"AUTOMATION OK (module {module}): {count or 'nothing to automate'}")


def cmd_contract(a):
    if len(a) != 1: die("Usage: contract.sh <MODULE>")
    module = a[0].upper()
    col, p = contract.build(module), contract.path(module).replace(os.sep, "/")
    if not col: die(f"NO CONTRACT: no OpenAPI spec among the sources of {module} ({contract.ingest.source_dir(module)}/)")
    if contract.state(module)["state"] == "current": return print(f"CONTRACT {module}: up to date, {len(col['item'])} endpoints -> {p}")
    write_json(contract.path(module), col)
    print(f"CONTRACT {module}: {len(col['item'])} endpoints from {', '.join(col['testhive']['specs'])} -> {p}\n"
          f"  run: bash scripts/run-api.sh {module} --contract   (known bugs: {contract.bugs_path(module).replace(os.sep, '/')}, one '<METHOD> <path> <BUG-ID>' per line)")


def cmd_baseline(a):
    if len(a) < 2: die("Usage: automate.py baseline <MODULE> <approved-by>")
    module, by = a[0].upper(), a[1]
    base = os.path.join(DIR, "baseline", module); os.makedirs(base, exist_ok=True)
    v = f"v{max((int(d[1:]) for d in os.listdir(base) if re.fullmatch(r'v\d+', d)), default=0) + 1}"
    s = status(module) or {"cases": [], "tools": {}}
    files = sorted({c["spec"] for c in s["cases"] if c["spec"] and os.path.exists(c["spec"])} |
                   {p for p in ("web/fixtures/testhive.ts", contract.path(module), contract.bugs_path(module)) if os.path.exists(p)})
    def sha(p):
        with open(p, "rb") as f: return hashlib.sha256(f.read()).hexdigest()
    try: commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except OSError: commit = ""
    os.makedirs(os.path.join(base, v))
    write_json(os.path.join(base, v, "meta.json"), {"module": module, "version": v, "approved_by": by, "approved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "git_commit": commit, "tools": s["tools"], "cases": {c["ID"]: c["state"] for c in s["cases"]}, "files": {p.replace(os.sep, "/"): sha(p) for p in files}})
    print(f"AUTOMATION BASELINE {module} {v}: {len(s['cases'])} cases, {len(files)} files -> {os.path.join(base, v).replace(os.sep, '/')}")


COMMANDS = {"scaffold": cmd_scaffold, "check": cmd_check, "contract": cmd_contract, "baseline": cmd_baseline}
if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS: die("Usage: automate.py " + "|".join(COMMANDS) + " ...")
    COMMANDS[sys.argv[1]](sys.argv[2:])
